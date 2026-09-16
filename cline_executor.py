import subprocess
import os
import json
from executor import BaseExecutor
from task_manager import Task, TaskStatus
from config import Config

class ClineExecutor(BaseExecutor):
    def __init__(self, task_manager, on_output, on_status_change):
        super().__init__(task_manager, on_output, on_status_change)
        self.current_task = None  # 현재 작업 추적
    
    def execute(self, task: Task) -> bool:
        try:
            # 원래 명령어 저장
            if not task.original_command:
                task.original_command = task.command
            
            # 사용자별 프로젝트 디렉토리 가져오기
            project_dir = Config.get_user_project_dir(task.user_id)
            
            # Build Cline CLI command with JSON output
            command = [
                Config.CLINE_CLI_PATH,
                "--json",
                "--auto-approve", "true",
                "-c", project_dir,
                task.command
            ]
            
            # Create process group for macOS
            def preexec_fn():
                os.setsid()
            
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                preexec_fn=preexec_fn
            )
            
            self.current_process = process
            self.current_task = task
            self.task_manager.set_process(task.task_id, process)
            
            # Start JSON stream parsing thread
            self.should_stop = False
            self.output_thread = __import__('threading').Thread(
                target=self._parse_json_stream,
                args=(process, task.task_id)
            )
            self.output_thread.start()
            
            # Update status to working
            self.task_manager.update_task_status(task.task_id, TaskStatus.WORKING)
            self.on_status_change(task.task_id)
            
            # Wait for completion in separate thread
            completion_thread = __import__('threading').Thread(
                target=self._wait_for_completion,
                args=(process, task.task_id)
            )
            completion_thread.start()
            
            return True
            
        except Exception as e:
            self.on_output(task.task_id, f"❌ Failed to start Cline: {str(e)}")
            self.task_manager.update_task_status(task.task_id, TaskStatus.FAILED, error=str(e))
            self.on_status_change(task.task_id)
            return False
    
    def _parse_json_stream(self, process: subprocess.Popen, task_id: str):
        try:
            buffer = ""
            while True:
                if self.should_stop:
                    break
                
                char = process.stdout.read(1)
                if not char:
                    break
                
                buffer += char.decode('utf-8', errors='ignore')
                
                # Try to parse complete JSON objects
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        event = json.loads(line)
                        self._process_event(event, task_id)
                    except json.JSONDecodeError:
                        # Not a complete JSON yet, keep accumulating
                        pass
                
                if process.poll() is not None:
                    break
            
            # Process remaining buffer
            if buffer.strip():
                try:
                    event = json.loads(buffer.strip())
                    self._process_event(event, task_id)
                except json.JSONDecodeError:
                    pass
                    
        except Exception as e:
            self.on_output(task_id, f"Error parsing JSON stream: {str(e)}")
    
    def _process_event(self, event: dict, task_id: str):
        event_type = event.get("type")
        
        if event_type == "agent_event":
            agent_event = event.get("event", {})
            event_subtype = agent_event.get("type")
            
            if event_subtype == "content_start":
                content_type = agent_event.get("contentType")
                if content_type == "text":
                    text = agent_event.get("text", "")
                    if text:
                        self.on_output(task_id, f"🤖 {text}\n")
                        # 토큰 초과 감지
                        if self._is_token_limit_error(text):
                            self.on_output(task_id, "⚠️ 토큰 초과 감지됨\n")
                            self._handle_token_limit(task_id)
                elif content_type == "reasoning":
                    reasoning = agent_event.get("reasoning", "")
                    if reasoning:
                        self.on_output(task_id, f"🧠 {reasoning}\n")
                        # 토큰 초과 감지
                        if self._is_token_limit_error(reasoning):
                            self.on_output(task_id, "⚠️ 토큰 초과 감지됨\n")
                            self._handle_token_limit(task_id)
                elif content_type == "tool":
                    tool_name = agent_event.get("toolName", "")
                    tool_input = agent_event.get("input", {})
                    self.on_output(task_id, f"🔧 Running: {tool_name}\n")
            
            elif event_subtype == "content_update":
                content_type = agent_event.get("contentType")
                if content_type == "tool":
                    update = agent_event.get("update", {})
                    stream = update.get("stream")
                    chunk = update.get("chunk", "")
                    if stream == "stdout" and chunk:
                        self.on_output(task_id, chunk)
                        # 토큰 초과 감지
                        if self._is_token_limit_error(chunk):
                            self.on_output(task_id, "⚠️ 토큰 초과 감지됨\n")
                            self._handle_token_limit(task_id)
            
            elif event_subtype == "content_end":
                content_type = agent_event.get("contentType")
                if content_type == "tool":
                    tool_name = agent_event.get("toolName", "")
                    output = agent_event.get("output", [])
                    if output:
                        for result in output:
                            if result.get("success"):
                                self.on_output(task_id, f"✅ {tool_name} completed\n")
                            else:
                                self.on_output(task_id, f"❌ {tool_name} failed\n")
                                # 토큰 초과 감지
                                error_output = result.get("result", "")
                                if self._is_token_limit_error(error_output):
                                    self.on_output(task_id, "⚠️ 토큰 초과 감지됨\n")
                                    self._handle_token_limit(task_id)
            
            elif event_subtype == "done":
                reason = agent_event.get("reason")
                text = agent_event.get("text", "")
                if reason == "completed":
                    self.on_output(task_id, f"✅ Cline completed: {text}\n")
                elif reason == "failed":
                    self.on_output(task_id, f"❌ Cline failed: {text}\n")
                    # 토큰 초과 감지
                    if self._is_token_limit_error(text):
                        self.on_output(task_id, "⚠️ 토큰 초과 감지됨\n")
                        self._handle_token_limit(task_id)
        
        elif event_type == "hook_event":
            hook_name = event.get("hookEventName")
            if hook_name == "agent_start":
                self.on_output(task_id, "🚀 Cline task started\n")
            elif hook_name == "agent_end":
                self.on_output(task_id, "🏁 Cline task ended\n")
    
    def _is_token_limit_error(self, text: str) -> bool:
        """토큰 초과 에러 감지"""
        token_limit_keywords = [
            "token limit",
            "rate limit",
            "quota exceeded",
            "too many requests",
            "429",
            "insufficient quota",
            "토큰 초과",
            "한도 초과"
        ]
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in token_limit_keywords)
    
    def _handle_token_limit(self, task_id: str):
        """토큰 초과 처리"""
        if not Config.AUTO_RETRY_ON_TOKEN_LIMIT:
            return
        
        task = self.task_manager.get_task(task_id)
        if not task:
            return
        
        # 최대 재시도 횟수 확인
        if task.retry_count >= Config.MAX_AUTO_RETRIES:
            self.on_output(task_id, f"❌ 최대 재시도 횟수 ({Config.MAX_AUTO_RETRIES}) 초과\n")
            self.task_manager.update_task_status(task_id, TaskStatus.FAILED, error="Token limit exceeded")
            self.on_status_change(task_id)
            return
        
        # 현재 작업 취소
        self.cancel()
        
        # 재시도 정보 저장
        self.on_output(task_id, f"⏳ {Config.RETRY_DELAY_SECONDS}초 후 자동 재시작...\n")
        
        # 재시도 예약 (별도 스레드에서)
        import threading
        retry_thread = threading.Thread(
            target=self._retry_after_delay,
            args=(task, task_id)
        )
        retry_thread.daemon = True
        retry_thread.start()
    
    def _retry_after_delay(self, original_task: Task, original_task_id: str):
        """지연 후 재시작"""
        import time
        time.sleep(Config.RETRY_DELAY_SECONDS)
        
        # 재시도 카운트 증가
        original_task.retry_count += 1
        
        # 원래 명령어 저장
        if not original_task.original_command:
            original_task.original_command = original_task.command
        
        # 새 작업 생성
        new_task = self.task_manager.create_task(
            original_task.task_type, 
            original_task.original_command, 
            original_task.user_id
        )
        new_task.original_command = original_task.original_command
        new_task.retry_count = original_task.retry_count
        
        self.on_output(original_task_id, f"🔄 자동 재시작 ({original_task.retry_count}/{Config.MAX_AUTO_RETRIES})\n")
        
        # 새 작업 실행
        if original_task.task_type == TaskType.CLINE:
            self.execute(new_task)
    
    def cancel(self) -> bool:
        if self.current_process:
            self.should_stop = True
            self._terminate_process_group(self.current_process)
            return True
        return False
