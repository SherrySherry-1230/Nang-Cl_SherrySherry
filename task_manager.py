import threading
import time
from enum import Enum
from typing import Optional, Dict, Any
from dataclasses import dataclass, field

class TaskStatus(Enum):
    IDLE = "idle"
    STARTING = "starting"
    WORKING = "working"
    CANCELLING = "cancelling"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class TaskType(Enum):
    CLINE = "cline"
    TERMINAL = "terminal"
    TUI = "tui"

@dataclass
class Task:
    task_id: str
    task_type: TaskType
    command: str
    user_id: int  # 사용자 ID 추가
    status: TaskStatus = TaskStatus.IDLE
    telegram_message_id: Optional[int] = None
    output: str = ""
    error: Optional[str] = None
    exit_code: Optional[int] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    process: Optional[Any] = None
    extra_data: Dict[str, Any] = field(default_factory=dict)
    retry_count: int = 0  # 재시도 횟수 추적
    original_command: Optional[str] = None  # 원래 명령어 저장

class TaskManager:
    def __init__(self):
        # 사용자별 작업 관리
        self.user_tasks: Dict[int, Dict[str, Task]] = {}  # {user_id: {task_id: task}}
        self.user_current_tasks: Dict[int, Optional[Task]] = {}  # {user_id: current_task}
        self.user_last_tasks: Dict[int, Optional[Task]] = {}  # {user_id: last_task}
        self.lock = threading.Lock()
    
    def create_task(self, task_type: TaskType, command: str, user_id: int) -> Task:
        import uuid
        task_id = str(uuid.uuid4())
        return Task(
            task_id=task_id,
            task_type=task_type,
            command=command,
            user_id=user_id
        )
    
    def start_task(self, task: Task) -> bool:
        with self.lock:
            user_id = task.user_id
            
            # 사용자별 작업 확인
            if user_id in self.user_current_tasks:
                current_task = self.user_current_tasks[user_id]
                if current_task and current_task.status in [TaskStatus.STARTING, TaskStatus.WORKING]:
                    return False
                
                # 이전 작업을 last_task로 이동
                if current_task:
                    self.user_last_tasks[user_id] = current_task
            
            # 사용자 작업 저장소 초기화
            if user_id not in self.user_tasks:
                self.user_tasks[user_id] = {}
            
            # 새 작업 저장
            self.user_tasks[user_id][task.task_id] = task
            self.user_current_tasks[user_id] = task
            task.status = TaskStatus.STARTING
            task.start_time = time.time()
            return True
    
    def update_task_status(self, task_id: str, status: TaskStatus, **kwargs):
        with self.lock:
            # 모든 사용자의 작업에서 해당 task_id 찾기
            for user_id, tasks in self.user_tasks.items():
                if task_id in tasks:
                    task = tasks[task_id]
                    task.status = status
                    for key, value in kwargs.items():
                        setattr(task, key, value)
                    
                    if status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                        task.end_time = time.time()
                    break
    
    def append_output(self, task_id: str, output: str):
        with self.lock:
            # 모든 사용자의 작업에서 해당 task_id 찾기
            for user_id, tasks in self.user_tasks.items():
                if task_id in tasks:
                    task = tasks[task_id]
                    task.output += output
                    # Limit output size
                    max_length = 100000  # 100KB internal buffer
                    if len(task.output) > max_length:
                        task.output = task.output[-max_length:]
                    break
    
    def get_current_task(self, user_id: int) -> Optional[Task]:
        with self.lock:
            return self.user_current_tasks.get(user_id)
    
    def get_last_task(self, user_id: int) -> Optional[Task]:
        with self.lock:
            return self.user_last_tasks.get(user_id)
    
    def get_task(self, task_id: str) -> Optional[Task]:
        with self.lock:
            for user_id, tasks in self.user_tasks.items():
                if task_id in tasks:
                    return tasks[task_id]
            return None
    
    def set_process(self, task_id: str, process):
        with self.lock:
            for user_id, tasks in self.user_tasks.items():
                if task_id in tasks:
                    tasks[task_id].process = process
                    break
    
    def set_telegram_message_id(self, task_id: str, message_id: int):
        with self.lock:
            for user_id, tasks in self.user_tasks.items():
                if task_id in tasks:
                    tasks[task_id].telegram_message_id = message_id
                    break
    
    def is_task_running(self, user_id: int) -> bool:
        with self.lock:
            current_task = self.user_current_tasks.get(user_id)
            return current_task and current_task.status in [TaskStatus.STARTING, TaskStatus.WORKING]
    
    def get_task_summary(self, task: Task) -> str:
        duration = ""
        if task.start_time and task.end_time:
            duration = f" ({task.end_time - task.start_time:.1f}s)"
        elif task.start_time:
            duration = f" ({time.time() - task.start_time:.1f}s)"
        
        status_emoji = {
            TaskStatus.IDLE: "💤",
            TaskStatus.STARTING: "🚀",
            TaskStatus.WORKING: "⏳",
            TaskStatus.CANCELLING: "🛑",
            TaskStatus.COMPLETED: "✅",
            TaskStatus.FAILED: "❌",
            TaskStatus.CANCELLED: "🛑"
        }
        
        return f"{status_emoji.get(task.status, '❓')} {task.status.value.upper()}{duration}"
