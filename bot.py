import asyncio
import threading
import time
import sys
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from config import Config
from task_manager import TaskManager, TaskType, TaskStatus
from terminal_executor import TerminalExecutor
from cline_executor import ClineExecutor
from telegram_ui import TelegramUI

# Force stdout to be unbuffered
sys.stdout.reconfigure(line_buffering=True)

class TelegramClineBot:
    def __init__(self):
        self.task_manager = TaskManager()
        self.telegram_ui = None
        self.status_check_interval = 2.0  # Check task status every 2 seconds
        self.running = True
        self.user_executors = {}  # 사용자별 executor 인스턴스
    
    def on_output(self, task_id: str, output: str):
        """Handle output from executors"""
        self.task_manager.append_output(task_id, output)
        print(f"[{task_id}] {output.strip()}")
    
    def on_status_change(self, task_id: str):
        """Handle status changes from executors"""
        task = self.task_manager.get_task(task_id)
        if task:
            print(f"[{task_id}] Status changed to: {task.status.value}")
    
    def run_status_monitor(self):
        """Run status monitor in a separate thread"""
        while self.running:
            try:
                # Get the current event loop
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                # Run the async status check for all users
                for user_id in Config.TELEGRAM_ALLOWED_USER_IDS:
                    loop.run_until_complete(self._check_and_update_status(user_id))
                
                time.sleep(self.status_check_interval)
            except Exception as e:
                print(f"Error in status monitor: {e}")
                time.sleep(self.status_check_interval)
    
    async def _check_and_update_status(self, user_id: int):
        """Check and update task status for a specific user"""
        task = self.task_manager.get_current_task(user_id)
        if task and task.telegram_message_id:
            try:
                await self.telegram_ui.update_task_message(
                    user_id,
                    task.telegram_message_id,
                    task
                )
                
                # Check if task completed and send notification
                if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                    # Only send notification once (when status first changes)
                    if not hasattr(task, 'notification_sent'):
                        await self.telegram_ui.send_completion_notification(
                            user_id,
                            task
                        )
                        task.notification_sent = True
            except Exception as e:
                print(f"Error in status check for user {user_id}: {e}")
    
    async def start(self, update: Update, context):
        """Handle /start command"""
        user_id = update.effective_user.id
        
        # 사용자 인증 확인
        if not Config.is_user_allowed(user_id):
            await update.message.reply_text("❌ 이 Bot을 사용할 권한이 없습니다.")
            return
        
        await self.telegram_ui.send_help_message(update.effective_chat.id)
    
    async def help_command(self, update: Update, context):
        """Handle /help command"""
        user_id = update.effective_user.id
        
        if not Config.is_user_allowed(user_id):
            await update.message.reply_text("❌ 이 Bot을 사용할 권한이 없습니다.")
            return
        
        await self.telegram_ui.send_help_message(update.effective_chat.id)
    
    async def status(self, update: Update, context):
        """Handle /status command"""
        user_id = update.effective_user.id
        
        if not Config.is_user_allowed(user_id):
            await update.message.reply_text("❌ 이 Bot을 사용할 권한이 없습니다.")
            return
        
        task = self.task_manager.get_current_task(user_id)
        await self.telegram_ui.send_status_message(update.effective_chat.id, task)
    
    async def output(self, update: Update, context):
        """Handle /output command"""
        user_id = update.effective_user.id
        
        if not Config.is_user_allowed(user_id):
            await update.message.reply_text("❌ 이 Bot을 사용할 권한이 없습니다.")
            return
        
        task = self.task_manager.get_current_task(user_id)
        if task:
            await self.telegram_ui.send_output_message(update.effective_chat.id, task)
        else:
            last_task = self.task_manager.get_last_task(user_id)
            if last_task:
                await self.telegram_ui.send_output_message(update.effective_chat.id, last_task)
            else:
                await update.message.reply_text("📋 No output available")
    
    async def cancel(self, update: Update, context):
        """Handle /cancel command"""
        user_id = update.effective_user.id
        
        if not Config.is_user_allowed(user_id):
            await update.message.reply_text("❌ 이 Bot을 사용할 권한이 없습니다.")
            return
        
        task = self.task_manager.get_current_task(user_id)
        if not task:
            await update.message.reply_text("💤 No running task to cancel")
            return
        
        # Update status to cancelling
        self.task_manager.update_task_status(task.task_id, TaskStatus.CANCELLING)
        await self.telegram_ui.update_task_message(
            update.effective_chat.id,
            task.telegram_message_id,
            task
        )
        
        # 사용자별 executor 가져오기
        terminal_executor = self.user_executors.get(user_id, {}).get('terminal')
        cline_executor = self.user_executors.get(user_id, {}).get('cline')
        
        # Cancel the appropriate executor
        if task.task_type == TaskType.CLINE and cline_executor:
            success = cline_executor.cancel()
        elif task.task_type == TaskType.TERMINAL and terminal_executor:
            success = terminal_executor.cancel()
        else:
            success = False
        
        if success:
            await update.message.reply_text("🛑 Cancel 요청 중...")
        else:
            await update.message.reply_text("❌ Failed to cancel task")
    
    async def retry(self, update: Update, context):
        """Handle /retry command"""
        user_id = update.effective_user.id
        
        if not Config.is_user_allowed(user_id):
            await update.message.reply_text("❌ 이 Bot을 사용할 권한이 없습니다.")
            return
        
        last_task = self.task_manager.get_last_task(user_id)
        if not last_task:
            await update.message.reply_text("📋 No previous task to retry")
            return
        
        # Create new task with same command
        new_task = self.task_manager.create_task(last_task.task_type, last_task.command, user_id)
        
        # Start the task
        if await self._execute_task(update.effective_chat.id, new_task):
            await update.message.reply_text(f"🔄 Retrying: {last_task.command}")
        else:
            await update.message.reply_text("❌ Failed to start retry")
    
    async def cline_command(self, update: Update, context):
        """Handle /cline command"""
        user_id = update.effective_user.id
        
        if not Config.is_user_allowed(user_id):
            await update.message.reply_text("❌ 이 Bot을 사용할 권한이 없습니다.")
            return
        
        if not context.args:
            await update.message.reply_text("Usage: /cline <prompt> 또는 /클라인 <prompt>")
            return
        
        prompt = " ".join(context.args)
        await self._start_cline_task(update.effective_chat.id, prompt, user_id)
    
    async def run_command(self, update: Update, context):
        """Handle /run command"""
        user_id = update.effective_user.id
        
        if not Config.is_user_allowed(user_id):
            await update.message.reply_text("❌ 이 Bot을 사용할 권한이 없습니다.")
            return
        
        if not context.args:
            await update.message.reply_text("Usage: /run <command> 또는 /실행 <command>")
            return
        
        command = " ".join(context.args)
        await self._start_terminal_task(update.effective_chat.id, command, user_id)
    
    async def set_project_dir(self, update: Update, context):
        """Handle /setproject command"""
        user_id = update.effective_user.id
        
        if not Config.is_user_allowed(user_id):
            await update.message.reply_text("❌ 이 Bot을 사용할 권한이 없습니다.")
            return
        
        if not context.args:
            await update.message.reply_text("Usage: /setproject <directory>")
            return
        
        project_dir = " ".join(context.args)
        
        # 디렉토리 존재 확인
        import os
        if not os.path.exists(project_dir):
            await update.message.reply_text(f"❌ Directory does not exist: {project_dir}")
            return
        
        Config.set_user_project_dir(user_id, project_dir)
        await update.message.reply_text(f"✅ Project directory set to: {project_dir}")
    
    async def handle_message(self, update: Update, context):
        """Handle regular text messages and Korean commands"""
        user_id = update.effective_user.id
        
        if not Config.is_user_allowed(user_id):
            await update.message.reply_text("❌ 이 Bot을 사용할 권한이 없습니다.")
            return
        
        text = update.message.text.strip()
        
        # Korean command mapping
        korean_commands = {
            "/시작": "/start",
            "/도움말": "/help", 
            "/상태": "/status",
            "/출력": "/output",
            "/취소": "/cancel",
            "/재시도": "/retry",
            "/클라인": "/cline",
            "/실행": "/run",
            "/프로젝트설정": "/setproject"
        }
        
        # Check if it's a Korean command
        if text in korean_commands:
            english_command = korean_commands[text]
            # Simulate the English command
            if english_command == "/start":
                await self.start(update, context)
            elif english_command == "/help":
                await self.help_command(update, context)
            elif english_command == "/status":
                await self.status(update, context)
            elif english_command == "/output":
                await self.output(update, context)
            elif english_command == "/cancel":
                await self.cancel(update, context)
            elif english_command == "/retry":
                await self.retry(update, context)
            elif english_command == "/cline":
                # Extract prompt after Korean command
                if text.startswith("/클라인 "):
                    prompt = text[len("/클라인 "):].strip()
                    if prompt:
                        await self._start_cline_task(update.effective_chat.id, prompt, user_id)
                    else:
                        await update.message.reply_text("Usage: /클라인 <prompt>")
                else:
                    await update.message.reply_text("Usage: /클라인 <prompt>")
            elif english_command == "/run":
                # Extract command after Korean command
                if text.startswith("/실행 "):
                    command = text[len("/실행 "):].strip()
                    if command:
                        await self._start_terminal_task(update.effective_chat.id, command, user_id)
                    else:
                        await update.message.reply_text("Usage: /실행 <command>")
                else:
                    await update.message.reply_text("Usage: /실행 <command>")
            elif english_command == "/setproject":
                # Extract directory after Korean command
                if text.startswith("/프로젝트설정 "):
                    directory = text[len("/프로젝트설정 "):].strip()
                    if directory:
                        # Set context.args for the set_project function
                        context.args = [directory]
                        await self.set_project_dir(update, context)
                    else:
                        await update.message.reply_text("Usage: /프로젝트설정 <directory>")
                else:
                    await update.message.reply_text("Usage: /프로젝트설정 <directory>")
            return
        
        # Handle plain text prompt if enabled
        if Config.ALLOW_PLAIN_TEXT_PROMPT:
            await self._start_cline_task(update.effective_chat.id, text, user_id)
        else:
            await update.message.reply_text("Please use commands. Type /help for available commands.")
    
    async def handle_callback_query(self, update: Update, context):
        """Handle inline button callbacks"""
        query = update.callback_query
        user_id = query.from_user.id
        
        if not Config.is_user_allowed(user_id):
            await query.answer("❌ 이 Bot을 사용할 권한이 없습니다.")
            return
        
        await query.answer()
        
        callback_data = query.data
        parts = callback_data.split("_", 1)
        
        if len(parts) != 2:
            return
        
        action, task_id = parts
        
        if action == "cancel":
            await self._handle_cancel_callback(query, task_id, user_id)
        elif action == "output":
            await self._handle_output_callback(query, task_id, user_id)
        elif action == "retry":
            await self._handle_retry_callback(query, task_id, user_id)
    
    async def _handle_cancel_callback(self, query, task_id: str, user_id: int):
        """Handle Cancel button callback"""
        task = self.task_manager.get_current_task(user_id)
        if not task or task.task_id != task_id:
            await query.edit_message_text("❌ Task not found or already completed")
            return
        
        # Update status to cancelling
        self.task_manager.update_task_status(task.task_id, TaskStatus.CANCELLING)
        await self.telegram_ui.update_task_message(
            query.message.chat_id,
            task.telegram_message_id,
            task
        )
        
        # 사용자별 executor 가져오기
        terminal_executor = self.user_executors.get(user_id, {}).get('terminal')
        cline_executor = self.user_executors.get(user_id, {}).get('cline')
        
        # Cancel the appropriate executor
        if task.task_type == TaskType.CLINE and cline_executor:
            success = cline_executor.cancel()
        elif task.task_type == TaskType.TERMINAL and terminal_executor:
            success = terminal_executor.cancel()
        else:
            success = False
        
        if success:
            await query.edit_message_text("🛑 Cancel 요청 중...")
        else:
            await query.edit_message_text("❌ Failed to cancel task")
    
    async def _handle_output_callback(self, query, task_id: str, user_id: int):
        """Handle Output button callback"""
        task = self.task_manager.get_current_task(user_id)
        if task and task.task_id == task_id:
            await self.telegram_ui.send_output_message(query.message.chat_id, task)
        else:
            # Check last task
            last_task = self.task_manager.get_last_task(user_id)
            if last_task and last_task.task_id == task_id:
                await self.telegram_ui.send_output_message(query.message.chat_id, last_task)
            else:
                await query.edit_message_text("❌ Task not found")
    
    async def _handle_retry_callback(self, query, task_id: str, user_id: int):
        """Handle Retry button callback"""
        # Find the task to retry
        task = self.task_manager.get_current_task(user_id)
        if task and task.task_id == task_id:
            source_task = task
        else:
            source_task = self.task_manager.get_last_task(user_id)
        
        if not source_task or source_task.task_id != task_id:
            await query.edit_message_text("❌ Task not found")
            return
        
        # Create new task with same command
        new_task = self.task_manager.create_task(source_task.task_type, source_task.command, user_id)
        
        # Start the task
        if await self._execute_task(query.message.chat_id, new_task):
            await query.edit_message_text(f"🔄 Retrying: {source_task.command}")
        else:
            await query.edit_message_text("❌ Failed to start retry")
    
    async def _start_cline_task(self, chat_id: int, prompt: str, user_id: int):
        """Start a Cline task"""
        if self.task_manager.is_task_running(user_id):
            current_task = self.task_manager.get_current_task(user_id)
            await self.telegram_ui.send_busy_message(chat_id, current_task)
            return
        
        task = self.task_manager.create_task(TaskType.CLINE, prompt, user_id)
        await self._execute_task(chat_id, task)
    
    async def _start_terminal_task(self, chat_id: int, command: str, user_id: int):
        """Start a terminal task"""
        if self.task_manager.is_task_running(user_id):
            current_task = self.task_manager.get_current_task(user_id)
            await self.telegram_ui.send_busy_message(chat_id, current_task)
            return
        
        task = self.task_manager.create_task(TaskType.TERMINAL, command, user_id)
        await self._execute_task(chat_id, task)
    
    async def _execute_task(self, chat_id: int, task) -> bool:
        """Execute a task and update Telegram UI"""
        user_id = task.user_id
        
        if not self.task_manager.start_task(task):
            return False
        
        # 사용자별 executor 초기화
        if user_id not in self.user_executors:
            self.user_executors[user_id] = {}
        
        # Send initial message to Telegram
        message_id = await self.telegram_ui.send_task_message(chat_id, task)
        self.task_manager.set_telegram_message_id(task.task_id, message_id)
        
        # Execute with appropriate executor
        if task.task_type == TaskType.CLINE:
            cline_executor = ClineExecutor(self.task_manager, self.on_output, self.on_status_change)
            self.user_executors[user_id]['cline'] = cline_executor
            success = cline_executor.execute(task)
        else:
            terminal_executor = TerminalExecutor(self.task_manager, self.on_output, self.on_status_change)
            self.user_executors[user_id]['terminal'] = terminal_executor
            success = terminal_executor.execute(task)
        
        return success
    
    def run(self):
        """Run the bot"""
        # Validate configuration
        Config.validate()
        
        # Create Telegram application
        application = Application.builder().token(Config.TELEGRAM_BOT_TOKEN).build()
        
        # Initialize UI
        self.telegram_ui = TelegramUI(application.bot)
        
        # Register handlers (English commands only - Telegram API limitation)
        application.add_handler(CommandHandler("start", self.start))
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(CommandHandler("status", self.status))
        application.add_handler(CommandHandler("output", self.output))
        application.add_handler(CommandHandler("cancel", self.cancel))
        application.add_handler(CommandHandler("retry", self.retry))
        application.add_handler(CommandHandler("cline", self.cline_command))
        application.add_handler(CommandHandler("run", self.run_command))
        application.add_handler(CommandHandler("setproject", self.set_project_dir))
        application.add_handler(CallbackQueryHandler(self.handle_callback_query))
        
        # Always handle text messages for Korean commands
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        # Start status monitoring thread
        monitor_thread = threading.Thread(target=self.run_status_monitor, daemon=True)
        monitor_thread.start()
        
        # Start the bot
        print("🤖 NANG-CL started")
        print(f"📱 Allowed user IDs: {Config.TELEGRAM_ALLOWED_USER_IDS}")
        print(f"📁 Default project directory: {Config.DEFAULT_PROJECT_DIR}")
        
        # Use the synchronous run_polling method
        application.run_polling()

if __name__ == "__main__":
    bot = TelegramClineBot()
    bot.run()
