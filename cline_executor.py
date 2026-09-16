import subprocess
import os
import json
from executor import BaseExecutor
from task_manager import Task, TaskStatus
from config import Config

class ClineExecutor(BaseExecutor):
    def __init__(self, task_manager, on_output, on_status_change):
        super().__init__(task_manager, on_output, on_status_change)
    
    def execute(self, task: Task) -> bool:
        try:
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
                elif content_type == "reasoning":
                    reasoning = agent_event.get("reasoning", "")
                    if reasoning:
                        self.on_output(task_id, f"🧠 {reasoning}\n")
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
            
            elif event_subtype == "done":
                reason = agent_event.get("reason")
                text = agent_event.get("text", "")
                if reason == "completed":
                    self.on_output(task_id, f"✅ Cline completed: {text}\n")
                elif reason == "failed":
                    self.on_output(task_id, f"❌ Cline failed: {text}\n")
        
        elif event_type == "hook_event":
            hook_name = event.get("hookEventName")
            if hook_name == "agent_start":
                self.on_output(task_id, "🚀 Cline task started\n")
            elif hook_name == "agent_end":
                self.on_output(task_id, "🏁 Cline task ended\n")
    
    def cancel(self) -> bool:
        if self.current_process:
            self.should_stop = True
            self._terminate_process_group(self.current_process)
            return True
        return False
