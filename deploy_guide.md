# 🚀 로컬 실행 가이드 (실시간 데이터 수집)

## 1단계: Python 설치 확인
```bash
python --version  # 3.9 이상이면 OK
```

## 2단계: 필요 패키지 설치
```bash
pip install streamlit pandas numpy plotly finance-datareader yfinance ta requests openpyxl
```

## 3단계: GitHub에서 코드 받기
```bash
git clone https://github.com/munikim/munistock.git
cd munistock
```

## 4단계: 앱 실행
```bash
streamlit run app.py
```
→ 브라우저에서 http://localhost:8501 자동 열림

## 5단계: 텔레그램 secrets 설정 (선택)
프로젝트 폴더에 `.streamlit/secrets.toml` 생성:
```toml
[telegram]
token   = "봇토큰"
chat_id = "챗ID"
```

## ✅ 로컬에서 되는 것들
- 퀀트 스캐너 실시간 (yfinance 차단 없음)
- 수급 기반 스윙 스캐너 실시간
- 네이버 금융 현재가 크롤링
- FDR 전체 종목 리스트

## 📱 폰에서도 쓰고 싶다면
같은 와이파이에서:
```
http://PC의IP주소:8501
```
PC IP 확인: Windows → `ipconfig`, Mac → `ifconfig`
