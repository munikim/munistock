# 🚀 Streamlit Cloud 배포 가이드

## 1. GitHub 저장소 준비

```
swing-dashboard/
├── app.py
├── requirements.txt
└── .gitignore          ← 반드시 생성!
```

### .gitignore 내용
```
.streamlit/secrets.toml
user_data/
__pycache__/
*.pyc
```

## 2. 로컬 텔레그램 설정

`.streamlit/secrets.toml` 파일 생성:
```toml
[telegram]
token   = "8754838258:AAGCArF6VjcYQSOHRf4mpgjmWZ30YAGwMd0"
chat_id = "8720367426"
```

## 3. Streamlit Cloud 배포

1. [share.streamlit.io](https://share.streamlit.io) 접속
2. GitHub 계정 연결 → New app
3. 저장소/브랜치/파일 선택
4. **Advanced settings → Secrets** 에 secrets.toml 내용 붙여넣기:
```toml
[telegram]
token = "봇토큰"
chat_id = "챗ID"
```
5. Deploy 클릭 → 약 2~3분 후 완료

## 4. 모바일 홈화면 추가 (앱처럼 사용)

**iOS**: Safari → 공유 버튼 → 홈 화면에 추가
**Android**: Chrome → 메뉴 → 앱 설치 / 홈 화면에 추가

## 5. 데이터 파일 경로

Streamlit Cloud는 배포마다 파일이 초기화됩니다.
- `watchlist.json` 등은 재배포 시 초기화될 수 있습니다.
- 중요 데이터는 주기적으로 백업하거나 DB 연동을 고려하세요.
