import subprocess
import signal
import os
import threading
from abc import ABC, abstractmethod
from typing import Optional, Callable
from task_manager import Task, TaskStatus

class BaseExecutor(ABC):
    def __init__(self, task_manager, on_output: Callable, on_status_change: Callable):
        self.task_manager = task_manager
        self.on_output = on_output
        self.on_status_change = on_status_change
        self.current_process: Optional[subprocess.Popen] = None
        self.output_thread: Optional[threading.Thread] = None
        self.should_stop = False
    
    @abstractmethod
    def execute(self, task: Task) -> bool:
        pass
    
    @abstractmethod
    def cancel(self) -> bool:
        pass
    
    def _read_output(self, process: subprocess.Popen, task_id: str):
        try:
            while True:
                if self.should_stop:
                    break
                
                line = process.stdout.readline()
                if not line:
                    break
                
                self.on_output(task_id, line.decode('utf-8', errors='ignore'))
                
                if process.poll() is not None:
                    break
        except Exception as e:
            self.on_output(task_id, f"Error reading output: {str(e)}")
    
    def _terminate_process_group(self, process: subprocess.Popen):
        """Terminate process and its children (macOS compatible)"""
        try:
            # Try to get process group ID
            pgid = os.getpgid(process.pid)
            
            # Send SIGTERM to process group
            os.killpg(pgid, signal.SIGTERM)
            
            # Wait a bit for graceful shutdown
            import time
            time.sleep(0.5)
            
            # If still running, send SIGKILL
            if process.poll() is None:
                os.killpg(pgid, signal.SIGKILL)
        except ProcessLookupError:
            # Process already terminated
            pass
        except Exception as e:
            # Fallback to single process termination
            try:
                process.terminate()
                import time
                time.sleep(0.5)
                if process.poll() is None:
                    process.kill()
            except Exception as e2:
                print(f"Error terminating process: {e2}")
    
    def _wait_for_completion(self, process: subprocess.Popen, task_id: str):
        try:
            exit_code = process.wait()
            self.task_manager.update_task_status(
                task_id,
                TaskStatus.COMPLETED if exit_code == 0 else TaskStatus.FAILED,
                exit_code=exit_code
            )
            self.on_status_change(task_id)
        except Exception as e:
            self.task_manager.update_task_status(
                task_id,
                TaskStatus.FAILED,
                error=str(e)
            )
            self.on_status_change(task_id)
