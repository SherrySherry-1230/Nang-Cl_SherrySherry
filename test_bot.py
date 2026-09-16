#!/usr/bin/env python3
"""
NANG-CL 설정 테스트 스크립트
.env 파일이 올바르게 설정되었는지 확인합니다.
"""

import os
import sys
import getpass

def test_config():
    print("🔍 NANG-CL 설정 테스트")
    print("=" * 40)
    
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        # 필수 설정 확인
        telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
        user_ids_str = os.getenv("TELEGRAM_ALLOWED_USER_IDS")
        default_project_dir = os.getenv("DEFAULT_PROJECT_DIR")
        cline_path = os.getenv("CLINE_CLI_PATH")
        
        # Telegram Bot Token
        if telegram_token and telegram_token != "your_bot_token_here":
            print("✅ TELEGRAM_BOT_TOKEN: 설정됨")
        else:
            print("❌ TELEGRAM_BOT_TOKEN: 설정되지 않음")
            print("   → Bot Token을 설정하세요")
        
        # User IDs
        if user_ids_str:
            user_ids = [int(uid.strip()) for uid in user_ids_str.split(",")]
            print(f"✅ TELEGRAM_ALLOWED_USER_IDS: {user_ids}")
        else:
            print("❌ TELEGRAM_ALLOWED_USER_IDS: 설정되지 않음")
            print("   → 허용할 사용자 ID를 설정하세요")
        
        # Default Project Directory
        expanded_dir = default_project_dir.replace("$(whoami)", getpass.getuser()) if default_project_dir else ""
        if expanded_dir and os.path.exists(expanded_dir):
            print(f"✅ DEFAULT_PROJECT_DIR: {expanded_dir}")
        else:
            print(f"⚠️  DEFAULT_PROJECT_DIR: {expanded_dir if expanded_dir else '설정되지 않음'}")
            print("   → 사용자가 개별적으로 프로젝트 디렉토리를 설정해야 합니다")
        
        # Cline CLI Path
        if cline_path:
            # Check if it's a simple command or full path
            if os.path.exists(cline_path):
                print(f"✅ CLINE_CLI_PATH: {cline_path}")
            else:
                # Try to find it in PATH
                import shutil
                if shutil.which(cline_path):
                    print(f"✅ CLINE_CLI_PATH: {cline_path} (found in PATH)")
                else:
                    print(f"❌ CLINE_CLI_PATH: {cline_path} (not found)")
                    print("   → Cline CLI를 설치하세요: npm install -g cline")
        else:
            print("❌ CLINE_CLI_PATH: 설정되지 않음")
        
        # 선택적 설정
        max_output = os.getenv("MAX_OUTPUT_LENGTH", "3500")
        print(f"ℹ️  MAX_OUTPUT_LENGTH: {max_output}")
        
        allow_plain = os.getenv("ALLOW_PLAIN_TEXT_PROMPT", "false")
        print(f"ℹ️  ALLOW_PLAIN_TEXT_PROMPT: {allow_plain}")
        
        allowed_commands = os.getenv("ALLOWED_COMMANDS", "")
        print(f"ℹ️  ALLOWED_COMMANDS: {allowed_commands[:50]}...")
        
        print("=" * 40)
        
        # 전체 테스트 결과
        all_good = (
            telegram_token and telegram_token != "your_bot_token_here" and
            user_ids_str and
            cline_path
        )
        
        if all_good:
            print("✅ 모든 필수 설정이 완료되었습니다!")
            print("🚀 Bot을 실행할 수 있습니다:")
            print("   source .venv/bin/activate")
            print("   python3 bot.py")
            return True
        else:
            print("❌ 일부 필수 설정이 누락되었습니다.")
            print("📝 .env 파일을 수정하여 설정을 완료하세요.")
            return False
            
    except Exception as e:
        print(f"❌ 설정 테스트 중 오류 발생: {e}")
        return False

if __name__ == "__main__":
    success = test_config()
    sys.exit(0 if success else 1)
