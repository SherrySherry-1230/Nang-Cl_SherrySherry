from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram import Update
from telegram.ext import CallbackContext
from task_manager import Task, TaskStatus, TaskType
from config import Config

class TelegramUI:
    def __init__(self, bot):
        self.bot = bot
    
    def create_task_message(self, task: Task) -> str:
        task_type_emoji = {
            TaskType.CLINE: "🤖",
            TaskType.TERMINAL: "💻",
            TaskType.TUI: "🖥️"
        }.get(task.task_type, "❓")
        
        task_type_name = {
            TaskType.CLINE: "Cline",
            TaskType.TERMINAL: "Terminal",
            TaskType.TUI: "Cline TUI"
        }.get(task.task_type, "Unknown")
        
        status_emoji = {
            TaskStatus.IDLE: "💤",
            TaskStatus.STARTING: "🚀",
            TaskStatus.WORKING: "⏳",
            TaskStatus.CANCELLING: "🛑",
            TaskStatus.COMPLETED: "✅",
            TaskStatus.FAILED: "❌",
            TaskStatus.CANCELLED: "🛑"
        }
        
        status_text = status_emoji.get(task.status, "❓")
        
        # Calculate duration
        duration = ""
        if task.start_time:
            if task.end_time:
                duration = f" ({task.end_time - task.start_time:.1f}s)"
            else:
                duration = f" ({__import__('time').time() - task.start_time:.1f}s)"
        
        task_type_name = {
            TaskType.CLINE: "Cline",
            TaskType.TERMINAL: "Terminal",
            TaskType.TUI: "Cline TUI"
        }.get(task.task_type, "Unknown")
        
        message = f"{task_type_emoji} {task_type_name} 작업\n\n"
        message += f"작업:\n{task.command}\n\n"
        message += f"상태:\n{status_text} {task.status.value.upper()}{duration}\n"
        
        # Add exit code if available
        if task.exit_code is not None:
            message += f"\nExit code: {task.exit_code}"
        
        # Add error if available
        if task.error:
            message += f"\n❌ Error: {task.error}"
        
        return message
    
    def create_task_keyboard(self, task: Task) -> InlineKeyboardMarkup:
        buttons = []
        
        if task.status in [TaskStatus.STARTING, TaskStatus.WORKING]:
            # Show Cancel button when task is running
            buttons.append([
                InlineKeyboardButton("⛔ Cancel", callback_data=f"cancel_{task.task_id}")
            ])
            buttons.append([
                InlineKeyboardButton("📋 Output", callback_data=f"output_{task.task_id}")
            ])
        elif task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
            # Show Retry and Output buttons when task is done
            buttons.append([
                InlineKeyboardButton("🔄 Retry", callback_data=f"retry_{task.task_id}")
            ])
            buttons.append([
                InlineKeyboardButton("📋 Output", callback_data=f"output_{task.task_id}")
            ])
        
        return InlineKeyboardMarkup(buttons)
    
    async def send_task_message(self, chat_id: int, task: Task) -> int:
        message = self.create_task_message(task)
        keyboard = self.create_task_keyboard(task)
        
        sent_message = await self.bot.send_message(
            chat_id=chat_id,
            text=message,
            reply_markup=keyboard
        )
        
        return sent_message.message_id
    
    async def update_task_message(self, chat_id: int, message_id: int, task: Task):
        message = self.create_task_message(task)
        keyboard = self.create_task_keyboard(task)
        
        try:
            await self.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=message,
                reply_markup=keyboard
            )
        except Exception as e:
            print(f"Error updating message: {e}")
    
    async def send_output_message(self, chat_id: int, task: Task):
        if not task.output:
            await self.bot.send_message(
                chat_id=chat_id,
                text="📋 No output available"
            )
            return
        
        # Truncate output if too long
        output = task.output
        if len(output) > Config.MAX_OUTPUT_LENGTH:
            output = output[-Config.MAX_OUTPUT_LENGTH:]
            output = f"... (truncated)\n\n{output}"
        
        # Split into chunks if still too long for Telegram
        max_telegram_length = 4096
        chunks = []
        current_chunk = ""
        
        for line in output.split('\n'):
            if len(current_chunk) + len(line) + 1 > max_telegram_length:
                chunks.append(current_chunk)
                current_chunk = line
            else:
                current_chunk += line + '\n'
        
        if current_chunk:
            chunks.append(current_chunk)
        
        # Send chunks
        for i, chunk in enumerate(chunks):
            prefix = f"📋 Output ({i+1}/{len(chunks)})\n\n" if len(chunks) > 1 else "📋 Output\n\n"
            await self.bot.send_message(
                chat_id=chat_id,
                text=prefix + chunk
            )
    
    async def send_completion_notification(self, chat_id: int, task: Task):
        if task.status == TaskStatus.COMPLETED:
            emoji = "🔔"
            title = "작업 완료"
        elif task.status == TaskStatus.FAILED:
            emoji = "🚨"
            title = "작업 실패"
        elif task.status == TaskStatus.CANCELLED:
            emoji = "🛑"
            title = "작업 취소됨"
        else:
            return
        
        task_type_name = {
            TaskType.CLINE: "Cline",
            TaskType.TERMINAL: "Terminal",
            TaskType.TUI: "Cline TUI"
        }.get(task.task_type, "Unknown")
        
        message = f"{emoji} {task_type_name} {title}\n\n"
        message += f"\"{task.command}\"\n"
        
        if task.exit_code is not None:
            message += f"\nExit code: {task.exit_code}"
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📋 Output", callback_data=f"output_{task.task_id}")
            ],
            [
                InlineKeyboardButton("🔄 Retry", callback_data=f"retry_{task.task_id}")
            ]
        ])
        
        await self.bot.send_message(
            chat_id=chat_id,
            text=message,
            reply_markup=keyboard
        )
    
    async def send_error_message(self, chat_id: int, error_message: str):
        await self.bot.send_message(
            chat_id=chat_id,
            text=f"❌ {error_message}"
        )
    
    async def send_busy_message(self, chat_id: int, current_task: Task):
        message = "⚠️ 현재 작업이 실행 중입니다.\n\n"
        message += f"현재 작업:\n{current_task.command}\n\n"
        message += "먼저 작업을 완료하거나 Cancel 해주세요."
        
        await self.bot.send_message(
            chat_id=chat_id,
            text=message
        )
    
    async def send_help_message(self, chat_id: int):
        help_text = """🤖 NANG-CL 명령어

🇰🇷 한글 명령어 / 🇺🇸 English Commands

시작 / start - Bot 시작
도움말 / help - 도움말
상태 / status - 현재 상태 확인
출력 / output - 작업 출력 확인
취소 / cancel - 현재 작업 취소
재시도 / retry - 마지막 작업 다시 실행
클라인 <prompt> / cline <prompt> - Cline 작업 시작
실행 <command> / run <command> - 터미널 명령 실행
프로젝트설정 <dir> / setproject <dir> - 프로젝트 디렉토리 설정
터미널시작 / tui - Cline TUI 모드 시작 (tmux 필요)

작업 중에는 ⛔ Cancel 버튼이 자동으로 표시됩니다.
"""
        await self.bot.send_message(
            chat_id=chat_id,
            text=help_text
        )
    
    async def send_status_message(self, chat_id: int, task: Task):
        if task:
            message = self.create_task_message(task)
            await self.bot.send_message(
                chat_id=chat_id,
                text=message
            )
        else:
            await self.bot.send_message(
                chat_id=chat_id,
                text="💤 현재 실행 중인 작업이 없습니다."
            )
