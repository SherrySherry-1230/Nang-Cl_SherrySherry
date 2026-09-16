import os
import getpass
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Telegram Configuration
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_ALLOWED_USER_IDS = []
    
    # Project Directory
    DEFAULT_PROJECT_DIR = os.getenv("DEFAULT_PROJECT_DIR", os.getcwd())
    
    # Cline CLI Configuration
    CLINE_CLI_PATH = os.getenv("CLINE_CLI_PATH", "cline")
    
    # Output Configuration
    MAX_OUTPUT_LENGTH = int(os.getenv("MAX_OUTPUT_LENGTH", "3500"))
    
    # Security Configuration
    ALLOW_PLAIN_TEXT_PROMPT = os.getenv("ALLOW_PLAIN_TEXT_PROMPT", "false").lower() == "true"
    
    # Command Allowlist
    ALLOWED_COMMANDS = os.getenv("ALLOWED_COMMANDS", "").split(",") if os.getenv("ALLOWED_COMMANDS") else []
    
    # TUI Configuration
    TUI_SESSION_NAME = "cline_tui"
    
    # 사용자별 설정 저장소
    USER_SETTINGS = {}
    
    @classmethod
    def load_allowed_user_ids(cls):
        """허용된 사용자 ID 목록 로드"""
        user_ids_str = os.getenv("TELEGRAM_ALLOWED_USER_IDS", "")
        if user_ids_str:
            cls.TELEGRAM_ALLOWED_USER_IDS = [int(uid.strip()) for uid in user_ids_str.split(",")]
    
    @classmethod
    def is_user_allowed(cls, user_id: int) -> bool:
        """사용자가 허용되었는지 확인"""
        return user_id in cls.TELEGRAM_ALLOWED_USER_IDS
    
    @classmethod
    def get_user_project_dir(cls, user_id: int) -> str:
        """사용자별 프로젝트 디렉토리 반환"""
        if user_id in cls.USER_SETTINGS and "project_dir" in cls.USER_SETTINGS[user_id]:
            return cls.USER_SETTINGS[user_id]["project_dir"]
        return cls.DEFAULT_PROJECT_DIR
    
    @classmethod
    def set_user_project_dir(cls, user_id: int, project_dir: str):
        """사용자별 프로젝트 디렉토리 설정"""
        if user_id not in cls.USER_SETTINGS:
            cls.USER_SETTINGS[user_id] = {}
        cls.USER_SETTINGS[user_id]["project_dir"] = project_dir
    
    @classmethod
    def validate(cls):
        if not cls.TELEGRAM_BOT_TOKEN:
            raise ValueError("TELEGRAM_BOT_TOKEN is required")
        
        cls.load_allowed_user_ids()
        if not cls.TELEGRAM_ALLOWED_USER_IDS:
            raise ValueError("TELEGRAM_ALLOWED_USER_IDS is required")
        
        # 기본 프로젝트 디렉토리 확인
        default_dir = cls.DEFAULT_PROJECT_DIR.replace("$(whoami)", getpass.getuser())
        if not os.path.exists(default_dir):
            print(f"Warning: Default project directory does not exist: {default_dir}")
            print(f"Users will need to set their own project directory")
