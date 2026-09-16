# NANG-CL

**NyangCl_bot** - Telegram을 통해 Cline AI 코딩 작업을 원격으로 제어하는 공용 Bot입니다.

## ⚠️ 플랫폼 지원

- **현재**: macOS 전용
- **계획**: Linux 및 Windows 지준 예정

## 🤖 Telegram Bot 정보

- **Bot 이름**: NyangCl_bot
- **Bot 사용자명**: @NyangCl_bot
- **Bot 링크**: https://t.me/NyangCl_bot
- **공용 Bot**: 개인 Bot Token이 필요 없습니다!

## 🎯 특징

- 🤖 Cline CLI를 통한 AI 코딩 작업 원격 실행
- 💻 일반 터미널 명령 실행
- ⛔ 작업 중 실시간 Cancel 버튼
- 🔄 작업 Retry 기능
- 📋 실시간 작업 출력 확인
- 🔔 작업 완료/실패/취소 알림
- 🔒 다중 사용자 지원 및 개인 작업 분리
- 👥 사용자별 프로젝트 디렉토리 설정

## 🚀 빠른 시작

### 1. Bot 사용

Telegram에서 **@NyangCl_bot**을 찾아서 `/start` 명령어를 입력하세요.

**Bot 정보**:
- 🤖 **Bot 이름**: NyangCl_bot
- 📱 **Bot 사용자명**: @NyangCl_bot
- 🔗 **Bot 링크**: https://t.me/NyangCl_bot
- ✅ **공용 Bot**: 개인 Bot Token이 필요 없습니다!

### 2. 프로젝트 디렉토리 설정

```bash
/setproject /path/to/your/project
```

### 3. 작업 실행

```bash
/cline 로그인 버튼 버그 수정해줘
/run git status
```

## 📱 Telegram 명령어

- `/start` - Bot 시작 및 도움말
- `/help` - 도움말
- `/status` - 현재 작업 상태 확인
- `/output` - 작업 출력 확인
- `/cancel` - 현재 작업 취소
- `/retry` - 마지막 작업 다시 실행
- `/cline <prompt>` - Cline 작업 시작
- `/run <command>` - 터미널 명령 실행
- `/setproject <directory>` - 프로젝트 디렉토리 설정

## 🛠️ 로컬 설치 (개발용)

> **⚠️ 현재 macOS 전용입니다. Linux 및 Windows 지원은 계획 중입니다.**

### 1. Python 가상환경 생성

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. 의존성 설치

```bash
pip install -r requirements.txt
```

### 3. Cline CLI 설치

```bash
npm install -g cline
```

### 4. 환경변수 설정

`.env.example`을 복사하여 `.env`를 생성하고 설정을 입력하세요:

```bash
cp .env.example .env
```

### 5. Bot 실행

```bash
python3 bot.py
```

## 💡 사용 예시

### Cline 작업 실행

```
/cline 로그인 버튼의 클릭 이벤트 버그를 수정해줘
```

### 터미널 명령 실행

```
/run git status
/run npm run build
/run python test.py
```

### 작업 중 제어

작업이 실행 중일 때 자동으로 Cancel 버튼이 표시됩니다:

```
⏳ Working

"로그인 버튼 버그 수정"

[ ⛔ Cancel ]
[ 📋 Output ]
```

작업 완료 후:

```
✅ Completed

"로그인 버튼 버그 수정"

[ 🔄 Retry ]
[ 📋 Output ]
```

## 🔒 보안

- **사용자 인증**: 허용된 사용자만 Bot 사용 가능
- **명령어 Allowlist**: 안전한 명령어만 실행 가능
- **프로젝트 디렉토리 제한**: 사용자별 개인 프로젝트 디렉토리
- **작업 분리**: 사용자별 작업이 완전히 분리됨
- **개인 정보 보호**: 사용자 간 작업 내용이 절대 공유되지 않음

## ⚠️ 제한사항

- **플랫폼**: 현재 macOS 전용 (Linux/Windows 지원 계획 중)
- Cline CLI의 JSON 스트림을 통해서만 Cline과 통신 가능
- VS Code Extension의 직접 제어는 불가능 (공식 API 없음)
- 한 번에 하나의 작업만 실행 가능

## 🏗️ 아키텍처

```
📱 Telegram (NyangCl_bot)
│
│ 명령 / 버튼 / 상태
▼
🐍 Python Telegram Bot
│
├── 다중 사용자 관리
├── Task Manager (사용자별 작업 상태)
├── Cline Executor (Cline CLI 실행)
├── Terminal Executor (터미널 명령 실행)
└── Telegram UI (메시지/버튼 관리)
│
▼
💻 Cline CLI / Terminal
```

## 🤝 기여

이 프로젝트는 오픈소스입니다. 기여를 환영합니다!

## 📄 라이선스

MIT License

## 🙏 감사

- Cline: AI 코딩 어시스턴트
- python-telegram-bot: Telegram Bot 라이브러리
