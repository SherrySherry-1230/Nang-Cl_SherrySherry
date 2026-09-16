import subprocess
import os
from executor import BaseExecutor
from task_manager import Task, TaskStatus
from config import Config

class TerminalExecutor(BaseExecutor):
    def __init__(self, task_manager, on_output, on_status_change):
        super().__init__(task_manager, on_output, on_status_change)
    
    def execute(self, task: Task) -> bool:
        try:
            # Security check
            command_parts = task.command.split()
            if command_parts:
                base_command = command_parts[0]
                if base_command not in Config.ALLOWED_COMMANDS:
                    self.on_output(task.task_id, f"❌ Command '{base_command}' is not in allowlist")
                    self.task_manager.update_task_status(task.task_id, TaskStatus.FAILED, error="Command not allowed")
                    self.on_status_change(task.task_id)
                    return False
            
            # 사용자별 프로젝트 디렉토리 가져오기
            project_dir = Config.get_user_project_dir(task.user_id)
            
            # Create process group for macOS
            def preexec_fn():
                os.setsid()
            
            process = subprocess.Popen(
                task.command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                cwd=project_dir,
                preexec_fn=preexec_fn
            )
            
            self.current_process = process
            self.task_manager.set_process(task.task_id, process)
            
            # Start output reading thread
            self.should_stop = False
            self.output_thread = __import__('threading').Thread(
                target=self._read_output,
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
            self.on_output(task.task_id, f"❌ Failed to start terminal command: {str(e)}")
            self.task_manager.update_task_status(task.task_id, TaskStatus.FAILED, error=str(e))
            self.on_status_change(task.task_id)
            return False
    
    def cancel(self) -> bool:
        if self.current_process:
            self.should_stop = True
            self._terminate_process_group(self.current_process)
            return True
        return False
