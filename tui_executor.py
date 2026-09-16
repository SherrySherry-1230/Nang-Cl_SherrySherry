import subprocess
import os
import time
from executor import BaseExecutor
from task_manager import Task, TaskStatus
from config import Config

class TUIExecutor(BaseExecutor):
    def __init__(self, task_manager, on_output, on_status_change):
        super().__init__(task_manager, on_output, on_status_change)
        self.session_name = None
    
    def execute(self, task: Task) -> bool:
        try:
            # 사용자별 프로젝트 디렉토리 가져오기
            project_dir = Config.get_user_project_dir(task.user_id)
            
            # 사용자별 세션 이름 생성
            self.session_name = f"cline_tui_{task.user_id}_{task.task_id[:8]}"
            
            # tmux 세션이 이미 존재하는지 확인하고 종료
            subprocess.run(["tmux", "kill-session", "-t", self.session_name], 
                         stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
            
            # Cline TUI 명령어 빌드
            cline_command = [
                Config.CLINE_CLI_PATH,
                "-i",  # TUI 모드
                "-c", project_dir,
                "-a"  # Act mode
            ]
            
            # tmux 세션 생성 및 Cline TUI 시작
            tmux_command = [
                "tmux",
                "new-session",
                "-d",
                "-s", self.session_name,
                " ".join(cline_command)
            ]
            
            process = subprocess.Popen(
                tmux_command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            self.current_process = process
            self.task_manager.set_process(task.task_id, process)
            
            # 잠시 대기 후 TUI가 시작되었는지 확인
            time.sleep(2)
            
            # TUI 세션이 활성화되었는지 확인
            check_session = subprocess.run(
                ["tmux", "has-session", "-t", self.session_name],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            if check_session.returncode != 0:
                self.on_output(task.task_id, "❌ Failed to start Cline TUI session")
                self.task_manager.update_task_status(task.task_id, TaskStatus.FAILED, error="TUI session failed to start")
                self.on_status_change(task.task_id)
                return False
            
            # Update status to working
            self.task_manager.update_task_status(task.task_id, TaskStatus.WORKING)
            self.on_status_change(task.task_id)
            
            self.on_output(task.task_id, f"🖥️ Cline TUI가 시작되었습니다.\n")
            self.on_output(task.task_id, f"세션 이름: {self.session_name}\n")
            self.on_output(task.task_id, f"로컬 터미널에서 다음 명령어로 접속할 수 있습니다:\n")
            self.on_output(task.task_id, f"tmux attach-session -t {self.session_name}\n")
            
            # TUI 감시 스레드 시작
            self.should_stop = False
            self.monitor_thread = __import__('threading').Thread(
                target=self._monitor_tui_session,
                args=(task.task_id,)
            )
            self.monitor_thread.start()
            
            return True
            
        except Exception as e:
            self.on_output(task.task_id, f"❌ Failed to start Cline TUI: {str(e)}")
            self.task_manager.update_task_status(task.task_id, TaskStatus.FAILED, error=str(e))
            self.on_status_change(task.task_id)
            return False
    
    def _monitor_tui_session(self, task_id: str):
        """TUI 세션 감시"""
        try:
            while not self.should_stop:
                # 세션이 여전히 존재하는지 확인
                check_session = subprocess.run(
                    ["tmux", "has-session", "-t", self.session_name],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                
                if check_session.returncode != 0:
                    # 세션이 종료됨
                    self.on_output(task_id, "🏁 Cline TUI 세션이 종료되었습니다.\n")
                    self.task_manager.update_task_status(task_id, TaskStatus.COMPLETED)
                    self.on_status_change(task_id)
                    break
                
                time.sleep(2)
                
        except Exception as e:
            self.on_output(task_id, f"Error monitoring TUI session: {str(e)}")
    
    def send_input(self, task_id: str, input_text: str):
        """TUI에 입력 전송"""
        try:
            if self.session_name:
                # tmux 세션에 키 입력 전송
                subprocess.run([
                    "tmux", "send-keys", "-t", self.session_name, input_text, "Enter"
                ])
                self.on_output(task_id, f"📝 입력 전송: {input_text}\n")
        except Exception as e:
            self.on_output(task_id, f"❌ Failed to send input: {str(e)}")
    
    def capture_output(self, task_id: str):
        """TUI 출력 캡처"""
        try:
            if self.session_name:
                # tmux 세션의 화면 내용 캡처
                result = subprocess.run([
                    "tmux", "capture-pane", "-t", self.session_name, "-p"
                ], capture_output=True, text=True)
                
                if result.stdout:
                    self.on_output(task_id, f"📺 TUI 출력:\n{result.stdout}\n")
        except Exception as e:
            self.on_output(task_id, f"❌ Failed to capture output: {str(e)}")
    
    def cancel(self) -> bool:
        if self.session_name:
            self.should_stop = True
            # tmux 세션 종료
            subprocess.run([
                "tmux", "kill-session", "-t", self.session_name
            ], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
            return True
        return False