# .env 파일 업데이트 가이드

NANG-CL로 변경하기 위해 `.env` 파일을 다음 내용으로 업데이트하세요:

```env
# NANG-CL - Telegram Cline Controller
# 공용 Bot 설정입니다. 개인 Bot Token이 필요 없습니다.

# Telegram Bot Configuration (NyangCl_bot)
TELEGRAM_BOT_TOKEN=8915229068:AAFVyNq1NAIsssDfhqB2202OESf8xQIVkE8

# 사용자별 인증 (콤마로 구분하여 여러 사용자 추가 가능)
TELEGRAM_ALLOWED_USER_IDS=1301220611

# 기본 프로젝트 디렉토리 (사용자별로 다르게 설정 가능)
DEFAULT_PROJECT_DIR=/Users/$(whoami)/Documents/MyPoopAI_UpSol_SherrySherry

# Cline CLI Configuration
CLINE_CLI_PATH=cline

# Output Configuration
MAX_OUTPUT_LENGTH=3500

# Security Configuration
ALLOW_PLAIN_TEXT_PROMPT=false

# Command Allowlist (comma-separated)
ALLOWED_COMMANDS=git,npm,npx,python,python3,pip,pytest,ls,pwd,cat,grep,find,echo,cd,mkdir,touch
```

## 업데이트 방법

터미널에서 다음 명령어로 `.env` 파일을 열어서 수정하세요:

```bash
cd /Users/heewonjung/Documents/tele_cline/telegram-cline-controller
nano .env
# 또는
vim .env
# 또는
open -e .env
```

위 내용으로 전체 교체한 후 저장하세요.

## 업데이트 후 테스트

```bash
python3 test_bot.py
```

모든 설정이 ✅로 나오면 Bot을 실행하세요:

```bash
python3 bot.py
```
