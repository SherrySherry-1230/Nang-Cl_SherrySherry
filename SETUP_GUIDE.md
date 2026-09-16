# NANG-CL 설정 가이드

## 🎯 공용 Bot 사용 (추천)

Telegram에서 **@NyangCl_bot**을 찾아서 바로 사용하세요!

1. `/start` - Bot 시작
2. `/setproject /path/to/project` - 프로젝트 디렉토리 설정
3. `/cline <prompt>` - Cline 작업 시작

## 🛠️ 로컬 설치 (개발용)

.env 파일을 직접 수정하여 다음 값을 설정하세요:

## 필수 설정

### 1. Telegram Bot Token
NyangCl_bot Token (이미 설정됨):
```
TELEGRAM_BOT_TOKEN=8915229068:AAFVyNq1NAIsssDfhqB2202OESf8xQIVkE8
```

### 2. Telegram User IDs
허용할 사용자 ID 목록 (콤마로 구분):
```
TELEGRAM_ALLOWED_USER_IDS=1301220611
```

@userinfobot에서 User ID를 확인할 수 있습니다.

### 3. Default Project Directory
기본 프로젝트 디렉토리:
```
DEFAULT_PROJECT_DIR=/Users/$(whoami)/Documents/MyPoopAI_UpSol_SherrySherry
```

### 4. Cline CLI Path
Cline CLI 경로:
```
CLINE_CLI_PATH=cline
```

## 선택 설정

### Output Length
Telegram 메시지 최대 길이:
```
MAX_OUTPUT_LENGTH=3500
```

### Plain Text Prompt
일반 텍스트를 자동으로 Cline prompt로 사용할지:
```
ALLOW_PLAIN_TEXT_PROMPT=false
```

### Command Allowlist
허용할 터미널 명령어 (콤마로 구분):
```
ALLOWED_COMMANDS=git,npm,npx,python,python3,pip,pytest,ls,pwd,cat,grep,find,echo,cd,mkdir,touch
```

## 설정 완료 후

```bash
# Bot 실행
source .venv/bin/activate
python3 bot.py
```

## Telegram에서 테스트

```
/start      # Bot 시작
/help       # 도움말
/setproject /path/to/project  # 프로젝트 설정
/run pwd    # 터미널 명령 테스트
/cline echo hello  # Cline 작업 테스트
```
