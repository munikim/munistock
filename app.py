"""
스윙매매 통합 대시보드 v1.0
=============================
실행: streamlit run app.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import json, os, time, hashlib
from datetime import datetime, timedelta
import plotly.graph_objects as go
import plotly.express as px
import requests, warnings
warnings.filterwarnings('ignore')

# ── SSL 우회 ─────────────────────────────────────────────────
import ssl
ssl._create_default_https_context = ssl._create_unverified_context
import urllib3; urllib3.disable_warnings()
_orig = requests.Session.request
def _nv(self, *a, **kw): kw.setdefault('verify', False); return _orig(self, *a, **kw)
requests.Session.request = _nv

# ── 페이지 설정 ───────────────────────────────────────────────
st.set_page_config(
    page_title="스윙 대시보드",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",  # 모바일 기본 사이드바 닫힘
)

# ── 전역 CSS ─────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;600;700;900&family=JetBrains+Mono:wght@400;600;700&display=swap');

/* ── 기본 리셋 ── */
*, *::before, *::after { box-sizing: border-box; }
html, body, [class*="css"] {
    font-family: 'Noto Sans KR', -apple-system, BlinkMacSystemFont, sans-serif;
    -webkit-font-smoothing: antialiased;
    color: #e2e8f0;
}
.main .block-container {
    padding: 0.8rem 0.8rem 3rem;
    max-width: 100%;
}

/* ── 카드 ── */
.card {
    background: #1e2535;
    border: 1px solid #2d3748;
    border-radius: 14px;
    padding: 1rem 1.2rem;
    margin: 0.35rem 0;
    box-shadow: 0 2px 12px rgba(0,0,0,0.4);
    transition: transform 0.15s, box-shadow 0.15s;
}
.card:hover { transform: translateY(-1px); box-shadow: 0 4px 20px rgba(0,0,0,0.5); }
.card-profit { border-left: 4px solid #38bdf8; }
.card-loss   { border-left: 4px solid #f87171; }
.card-info   { border-left: 4px solid #818cf8; }
.card-warn   { border-left: 4px solid #fbbf24; }

/* ── 수치 폰트 ── */
.big-num {
    font-family: 'JetBrains Mono', monospace;
    font-size: 1.9rem; font-weight: 700; letter-spacing: -0.5px;
}
.mono { font-family: 'JetBrains Mono', monospace; }
.profit-color { color: #38bdf8; }
.loss-color   { color: #f87171; }
.gold-color   { color: #fbbf24; }
.green-color  { color: #34d399; }
.label { color: #94a3b8; font-size: 0.75rem; margin-bottom: 0.15rem; letter-spacing: 0.3px; }

/* ── 알림바 ── */
.alert-red {
    background: #f8717115; border: 1px solid #f87171;
    border-radius: 10px; padding: 0.7rem 1rem;
    color: #f87171; font-weight: 600; margin: 0.25rem 0;
    animation: pulse 1.5s ease-in-out infinite;
}
.alert-yellow {
    background: #fbbf2415; border: 1px solid #fbbf24;
    border-radius: 10px; padding: 0.7rem 1rem;
    color: #fbbf24; font-weight: 600; margin: 0.25rem 0;
}
.alert-green {
    background: #34d39915; border: 1px solid #34d399;
    border-radius: 10px; padding: 0.7rem 1rem;
    color: #34d399; font-weight: 600; margin: 0.25rem 0;
}
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.55} }
@keyframes blink { 50%{background:#f8717115} }

/* ── 버튼 ── */
.stButton > button {
    background: linear-gradient(135deg, #6366f1, #4f46e5);
    color: #fff; border: none; border-radius: 10px;
    font-weight: 600; min-height: 42px;
    transition: all 0.2s; letter-spacing: 0.2px;
}
.stButton > button:hover {
    transform: translateY(-1px);
    box-shadow: 0 6px 18px rgba(99,102,241,0.5);
}
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #0ea5e9, #6366f1);
}

/* ── 사이드바 ── */
[data-testid="stSidebar"] {
    background: #131929;
    border-right: 1px solid #2d3748;
}
[data-testid="stSidebar"] .stRadio label {
    font-size: 0.9rem; padding: 0.3rem 0;
}

/* ── 입력창 ── */
.stTextInput input, .stNumberInput input, .stSelectbox select {
    background: #1e2535 !important;
    border: 1px solid #3d4a5e !important;
    border-radius: 8px !important; color: #e2e8f0 !important;
}

/* ── data_editor ── */
[data-testid="stDataEditor"] {
    border: 1px solid #2d3748; border-radius: 10px;
}

/* ── 스크롤 스무스 ── */
html { scroll-behavior: smooth; }
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: #131929; }
::-webkit-scrollbar-thumb { background: #3d4a5e; border-radius: 3px; }

/* ── 페이지 전환 깜빡임 방지 (강화) ── */
/* 배경 항상 유지 */
.main, [data-testid="stAppViewContainer"],
[data-testid="stMain"], .block-container {
    background: #0f1117 !important;
    min-height: 100vh !important;
}
/* 전환 시 빈 화면 방지 */
.element-container { transition: opacity 0.08s ease !important; }
/* 사이드바 즉각 반응 */
[data-testid="stSidebar"] .stRadio > div { transition: none !important; }

/* ── 스켈레톤 로딩 ── */
@keyframes skeleton-loading {
    0%   { background-position: -200% 0; }
    100% { background-position: 200% 0; }
}
.skeleton {
    background: linear-gradient(90deg,#1e2535 25%,#2d3748 50%,#1e2535 75%);
    background-size: 200% 100%;
    animation: skeleton-loading 1.4s ease infinite;
    border-radius: 8px;
}
.skeleton-h1 { height:1.8rem; width:40%; margin:0.5rem 0; }
.skeleton-h2 { height:1.1rem; width:70%; margin:0.3rem 0; }
.skeleton-p  { height:0.8rem; width:90%; margin:0.2rem 0; }
.skeleton-card {
    background:#1e2535; border:1px solid #2d3748;
    border-radius:14px; padding:1rem; margin:0.3rem 0;
}

/* 배경이 항상 유지되도록 */
.main, .block-container, [data-testid="stAppViewContainer"] {
    background: #0f1117 !important;
    min-height: 100vh;
}
/* 전환 시 빈 화면 방지 — 요소가 즉시 나타나도록 */
.element-container, .stMarkdown, .stButton, .stDataFrame {
    animation: none !important;
    transition: opacity 0.1s ease !important;
}
/* 스켈레톤 로딩 애니메이션 */
@keyframes skeleton-loading {
    0%   { background-position: -200% 0; }
    100% { background-position: 200% 0; }
}
.skeleton {
    background: linear-gradient(90deg, #1e2535 25%, #2d3748 50%, #1e2535 75%);
    background-size: 200% 100%;
    animation: skeleton-loading 1.4s ease infinite;
    border-radius: 8px;
    height: 1.2rem;
    margin: 0.3rem 0;
}
.skeleton-card {
    background: #1e2535;
    border: 1px solid #2d3748;
    border-radius: 14px;
    padding: 1rem;
    margin: 0.3rem 0;
}
.skeleton-title  { height: 1.1rem; width: 60%; }
.skeleton-text   { height: 0.85rem; width: 90%; }
.skeleton-number { height: 1.8rem; width: 45%; }

/* 라디오 메뉴 선택 시 즉각 반응 */
[data-testid="stSidebar"] .stRadio > div {
    transition: none !important;
}

/* ── 모바일 반응형 ── */
@media (max-width: 768px) {
    .big-num { font-size: 1.15rem; }
    .main .block-container { padding: 0.3rem 0.3rem 2rem; max-width: 100vw; overflow-x: hidden; }
    .card { padding: 0.6rem 0.7rem; border-radius: 10px; }
    .stDataFrame, [data-testid="stDataEditor"] { overflow-x: auto; font-size: 0.76rem; }
    .stButton > button { min-height: 44px; font-size: 0.85rem; }
    /* 카드 내부 grid 모바일 overflow 방지 */
    div[style*="grid-template-columns"] { min-width: 0; word-break: break-all; }
    /* 전체 너비 초과 방지 */
    * { max-width: 100%; box-sizing: border-box; }
    /* JetBrains Mono 숫자 축소 */
    .mono, [style*="JetBrains Mono"] { font-size: 0.82rem !important; }
}
@media (max-width: 480px) {
    .big-num { font-size: 0.95rem; }
    .label { font-size: 0.65rem; }
    .card { padding: 0.45rem 0.55rem; }
    .mono, [style*="JetBrains Mono"] { font-size: 0.75rem !important; }
}
</style>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════
#  데이터 저장 / 로드 (사용자별 격리)
# ════════════════════════════════════════════════════════════
# ══════════════════════════════════════════════════════
# 📌 텔레그램 설정 (st.secrets 사용)
# ──────────────────────────────────────────────────────
# [로컬 실행 시] 프로젝트 폴더에 .streamlit/secrets.toml 파일 생성:
#   [telegram]
#   token   = "여기에_봇토큰"
#   chat_id = "여기에_챗ID"
#
# [Streamlit Cloud 배포 시] 대시보드 → 앱 설정 → Secrets 메뉴에서
#   위와 동일한 내용을 붙여넣기하면 됩니다.
# ══════════════════════════════════════════════════════
def _get_tg_token() -> str:
    try:
        return st.secrets["telegram"]["token"]
    except Exception:
        return ""

def _get_tg_chat_id() -> str:
    try:
        return st.secrets["telegram"]["chat_id"]
    except Exception:
        return ""

# 데이터 저장 경로: 앱 파일 기준 상대경로 (로컬/클라우드 모두 호환)
try:
    DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "user_data")
except Exception:
    DATA_DIR = os.path.join(os.getcwd(), "user_data")
TOTAL_SEED = 2_000_000
os.makedirs(DATA_DIR, exist_ok=True)

USERS_FILE = os.path.join(DATA_DIR, "users.json")

def hash_pw(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()

def load_users() -> dict:
    try:
        if os.path.exists(USERS_FILE):
            with open(USERS_FILE, encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        pass
    default = {"admin": {"pw": hash_pw("1234"), "seed": 2_000_000}}
    save_users(default)
    return default

def save_users(users: dict):
    json.dump(users, open(USERS_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

def _init_data_dir():
    """앱 최초 실행 시 데이터 디렉토리 및 기본 파일 자동 생성"""
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        # users.json 없으면 기본 계정 생성
        users_path = os.path.join(DATA_DIR, "users.json")
        if not os.path.exists(users_path):
            default = {"admin": {"pw": hashlib.sha256("1234".encode()).hexdigest(), "seed": 2_000_000}}
            with open(users_path, "w", encoding="utf-8") as f:
                json.dump(default, f, ensure_ascii=False, indent=2)
    except Exception as e:
        pass  # 권한 문제 등 무시

def user_file(username: str, fname: str) -> str:
    try:
        d = os.path.join(DATA_DIR, username)
        os.makedirs(d, exist_ok=True)
        # watchlist.json 없으면 빈 파일 자동 생성
        path = os.path.join(d, fname)
        if fname.endswith(".json") and not os.path.exists(path):
            with open(path, "w", encoding="utf-8") as f:
                json.dump([] if "watchlist" in fname or "notifications" in fname
                          else {} if "users" in fname else [], f)
        return path
    except Exception:
        return os.path.join(os.getcwd(), fname)

def load_portfolio(username: str) -> list:
    """포트폴리오 로드 — 종목코드 6자리 문자열 정규화 포함"""
    try:
        f = user_file(username, "portfolio.json")
        if not os.path.exists(f):
            return []
        with open(f, encoding="utf-8") as fp:
            data = json.load(fp)
        if not isinstance(data, list):
            return []
        # 종목코드 타입 통일
        for item in data:
            if isinstance(item, dict) and "ticker" in item:
                item["ticker"] = str(item["ticker"]).strip().zfill(6)
        return data
    except Exception:
        return []

def save_portfolio(username: str, data: list):
    try:
        path = user_file(username, "portfolio.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.warning(f"포트폴리오 저장 오류: {e}")

def fix_portfolio_realized(username: str):
    """보유 중 종목의 잘못된 realized_pnl 강제 0 리셋 (1회성)"""
    data    = load_portfolio(username)
    changed = False
    for p in data:
        if p.get("status") != "청산" and p.get("realized_pnl", 0) != 0:
            p["realized_pnl"] = 0
            changed = True
    if changed:
        save_portfolio(username, data)
    return changed

def load_watchlist(username: str) -> list:
    """모닝체크 활성 목록 (오늘 볼 종목)"""
    f = user_file(username, "watchlist.json")
    try:
        if os.path.exists(f):
            data = json.load(open(f, encoding="utf-8"))
            return data if isinstance(data, list) else []
    except Exception:
        pass
    return []

def save_vault(username: str, data: list):
    """스윙 관심종목 보관함 전체 저장"""
    json.dump(data, open(user_file(username, "vault.json"), "w",
                         encoding="utf-8"), ensure_ascii=False, indent=2)

def load_vault(username: str) -> list:
    """스윙 관심종목 보관함 로드"""
    f = user_file(username, "vault.json")
    try:
        if os.path.exists(f):
            data = json.load(open(f, encoding="utf-8"))
            return data if isinstance(data, list) else []
    except Exception:
        pass
    return []

def save_watchlist(username: str, data: list):
    """관심종목 즉시 파일 저장 — 폴더 없으면 자동 생성"""
    path = user_file(username, "watchlist.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def add_to_watchlist(username: str, ticker: str, name: str,
                     source: str, entry: float, target: float,
                     stoploss: float, rsi="-", rr_ratio="-",
                     market: str = "", scan_date: str = "",
                     base_price: float = 0.0) -> str:
    """관심종목 추가/업데이트 — 종목코드 정규화 + 즉시 저장"""
    # 종목코드 반드시 6자리 문자열로 정규화
    ticker = str(ticker).strip().zfill(6)
    wl    = load_watchlist(username)
    today = datetime.now().strftime("%Y-%m-%d")
    item  = {
        "id":          int(time.time()),
        "ticker":      ticker,
        "name":        str(name),
        "market":      str(market),
        "source":      str(source),         # "퀀트" | "스윙" | "수동"
        "reg_date":    scan_date or today,   # 추가한 날짜
        "base_price":  float(base_price or entry),  # 추가 당시 기준가
        "entry":       int(entry),
        "target":      int(target),
        "stoploss":    int(stoploss),
        "rsi":         rsi,
        "rr_ratio":    rr_ratio,
        "is_active":   True,                # 모닝체크 포함 여부
    }
    for i, w in enumerate(wl):
        if w.get("ticker") == item["ticker"]:
            item["id"]         = w["id"]
            item["reg_date"]   = w.get("reg_date", today)
            item["base_price"] = w.get("base_price", item["base_price"])
            item["is_active"]  = w.get("is_active", True)
            wl[i] = item
            save_watchlist(username, wl)
            return "updated"
    wl.append(item)
    save_watchlist(username, wl)
    return "added"


# ── 내장 종목 리스트 (최후 보루) ──────────────────────────────

# ════════════════════════════════════════════════════════════
#  한국투자증권 KIS Open API — 데이터 수집 모듈
#  Streamlit Cloud에서 차단 없이 실시간 데이터 수집
# ════════════════════════════════════════════════════════════

# ── KIS API 설정 ─────────────────────────────────────────────
# .streamlit/secrets.toml 에 아래 형식으로 입력:
# [kis]
# app_key    = "PSxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
# app_secret = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
# account_no = "12345678-01"   # 계좌번호 (앞8자리-뒤2자리)
# is_paper   = false           # 실전: false, 모의: true

def _kis_cfg():
    """KIS 설정값 반환"""
    try:
        cfg = st.secrets.get("kis", {})
        return {
            "app_key":    cfg.get("app_key", ""),
            "app_secret": cfg.get("app_secret", ""),
            "account_no": cfg.get("account_no", ""),
            "is_paper":   bool(cfg.get("is_paper", False)),
        }
    except Exception:
        return {"app_key":"","app_secret":"","account_no":"","is_paper":False}

def _kis_base_url() -> str:
    cfg = _kis_cfg()
    return ("https://openapivts.koreainvestment.com:29443"
            if cfg["is_paper"]
            else "https://openapi.koreainvestment.com:9443")

@st.cache_data(ttl=82800)   # 23시간 캐시 — 하루 1회 발급
def _kis_get_token() -> str:
    """
    KIS Access Token 발급 (하루 1회)
    secrets.toml [kis] app_key / app_secret 필요
    """
    cfg = _kis_cfg()
    if not cfg["app_key"] or not cfg["app_secret"]:
        return ""
    try:
        url  = f"{_kis_base_url()}/oauth2/tokenP"
        body = {
            "grant_type": "client_credentials",
            "appkey":     cfg["app_key"],
            "appsecret":  cfg["app_secret"],
        }
        resp = requests.post(url, json=body, timeout=10, verify=False)
        if resp.status_code == 200:
            return resp.json().get("access_token", "")
    except Exception as e:
        print(f"[KIS 토큰 오류] {e}")
    return ""

def _kis_headers(tr_id: str) -> dict:
    """KIS API 공통 헤더"""
    cfg = _kis_cfg()
    tok = _kis_get_token()
    return {
        "Content-Type":  "application/json; charset=utf-8",
        "authorization": f"Bearer {tok}",
        "appkey":        cfg["app_key"],
        "appsecret":     cfg["app_secret"],
        "tr_id":         tr_id,
        "custtype":      "P",
    }

def _kis_available() -> bool:
    """KIS API 사용 가능 여부"""
    cfg = _kis_cfg()
    return bool(cfg["app_key"] and cfg["app_secret"] and _kis_get_token())


# ── 현재가 조회 ───────────────────────────────────────────────
@st.cache_data(ttl=60)   # 1분 캐시
def get_price(ticker: str) -> float:
    """
    현재가 조회
    1순위: KIS API (Streamlit Cloud 차단 없음)
    2순위: 네이버 금융 크롤링
    3순위: yfinance
    4순위: FDR
    """
    try:
        ticker = str(ticker).strip().zfill(6)

        # ── 1순위: KIS API ────────────────────────────────────
        if _kis_available():
            try:
                url    = f"{_kis_base_url()}/uapi/domestic-stock/v1/quotations/inquire-price"
                params = {
                    "fid_cond_mrkt_div_code": "J",
                    "fid_input_iscd":         ticker,
                }
                resp = requests.get(url, headers=_kis_headers("FHKST01010100"),
                                    params=params, timeout=8, verify=False)
                if resp.status_code == 200:
                    data = resp.json().get("output", {})
                    price = float(data.get("stck_prpr", 0) or 0)
                    if price > 0:
                        return price
            except Exception as e:
                print(f"[KIS price 오류] {ticker}: {e}")

        # ── 2순위: 네이버 금융 크롤링 ────────────────────────
        try:
            import re
            url  = f"https://finance.naver.com/item/main.naver?code={ticker}"
            resp = requests.get(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                              "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
                "Referer": "https://finance.naver.com",
            }, timeout=5, verify=False)
            if resp.status_code == 200:
                m = re.search(r'"item_code"\s*:\s*"' + ticker + r'"[^}]*?"now"\s*:\s*"([0-9,]+)"',
                              resp.text)
                if not m:
                    m = re.search(r'no_today[^"]*"[^"]*"[^>]*>.*?<span[^>]*>([0-9,]+)</span>',
                                  resp.text, re.DOTALL)
                if m:
                    p = float(m.group(1).replace(",",""))
                    if p > 0: return p
        except Exception:
            pass

        # ── 3순위: yfinance ───────────────────────────────────
        try:
            import yfinance as yf
            for sfx in [".KS",".KQ"]:
                try:
                    fi = yf.Ticker(ticker+sfx).fast_info
                    p  = getattr(fi,"last_price",None)
                    if p and float(p)>0: return float(p)
                except Exception: continue
        except Exception: pass

        # ── 4순위: FDR ────────────────────────────────────────
        try:
            import FinanceDataReader as fdr
            end   = datetime.now().strftime("%Y%m%d")
            start = (datetime.now()-timedelta(days=10)).strftime("%Y%m%d")
            df = fdr.DataReader(ticker, start, end)
            if df is not None and len(df)>0:
                df = df.sort_index(ascending=True)
                for c in df.columns:
                    if c.strip().lower() in ("close","adj close"):
                        v = df[c].iloc[-1]
                        if pd.notna(v) and float(v)>0: return float(v)
        except Exception: pass

    except Exception: pass
    return 0.0


# ── OHLCV 데이터 조회 ─────────────────────────────────────────
@st.cache_data(ttl=300)
def get_ohlcv_cached(ticker: str, days: int = 130) -> pd.DataFrame | None:
    """
    OHLCV 일봉 데이터 조회
    1순위: KIS API 일자별 시세
    2순위: yfinance
    3순위: FDR
    """
    try:
        ticker = str(ticker).strip().zfill(6)

        # ── 1순위: KIS API ────────────────────────────────────
        if _kis_available():
            try:
                url    = f"{_kis_base_url()}/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice"
                end_dt = datetime.now()
                # KIS는 100일치씩 — days가 크면 여러 번 호출
                all_rows = []
                cur_end  = end_dt

                for _ in range((days // 100) + 1):
                    params = {
                        "fid_cond_mrkt_div_code": "J",
                        "fid_input_iscd":         ticker,
                        "fid_input_date_1":       (cur_end-timedelta(days=100)).strftime("%Y%m%d"),
                        "fid_input_date_2":       cur_end.strftime("%Y%m%d"),
                        "fid_period_div_code":    "D",  # 일봉
                        "fid_org_adj_prc":        "0",  # 수정주가 미적용
                    }
                    resp = requests.get(
                        url, headers=_kis_headers("FHKST03010100"),
                        params=params, timeout=10, verify=False)
                    if resp.status_code != 200: break
                    output2 = resp.json().get("output2", [])
                    if not output2: break
                    for row in output2:
                        try:
                            all_rows.append({
                                "date":   row.get("stck_bsop_date",""),
                                "open":   float(row.get("stck_oprc",0) or 0),
                                "high":   float(row.get("stck_hgpr",0) or 0),
                                "low":    float(row.get("stck_lwpr",0) or 0),
                                "close":  float(row.get("stck_clpr",0) or 0),
                                "volume": float(row.get("acml_vol",0) or 0),
                            })
                        except Exception: continue
                    # 다음 구간
                    cur_end = cur_end - timedelta(days=100)
                    if len(all_rows) >= days: break

                if all_rows:
                    df = pd.DataFrame(all_rows)
                    df["date"] = pd.to_datetime(df["date"], format="%Y%m%d", errors="coerce")
                    df = df.dropna(subset=["date"]).set_index("date")
                    df = df.sort_index(ascending=True)
                    for col in ["open","high","low","close","volume"]:
                        df[col] = pd.to_numeric(df[col], errors="coerce")
                    return df.dropna(subset=["close"]).tail(days)
            except Exception as e:
                print(f"[KIS OHLCV 오류] {ticker}: {e}")

        # ── 2순위: yfinance ───────────────────────────────────
        try:
            import yfinance as yf
            end   = datetime.now()
            start = end - timedelta(days=days+30)
            for sfx in [".KS",".KQ"]:
                try:
                    tmp = yf.download(ticker+sfx,
                                      start=start.strftime("%Y-%m-%d"),
                                      end=end.strftime("%Y-%m-%d"),
                                      progress=False, auto_adjust=False, timeout=8)
                    if tmp is None or len(tmp)<10: continue
                    flat = []
                    for c in tmp.columns:
                        if isinstance(c,tuple):
                            ct = str(c[1]).strip() if len(c)>1 else ""
                            if ct and ct!=ticker+sfx: continue
                            flat.append(str(c[0]).strip().lower())
                        else:
                            flat.append(str(c).strip().lower())
                    if len(flat)==len(tmp.columns): tmp.columns = flat
                    tmp = tmp.sort_index(ascending=True)
                    cm = {}
                    for c in tmp.columns:
                        cl=str(c).strip().lower()
                        if cl=="open": cm[c]="open"
                        elif cl=="high": cm[c]="high"
                        elif cl=="low": cm[c]="low"
                        elif cl=="close": cm[c]="close"
                        elif cl=="volume": cm[c]="volume"
                    tmp = tmp.rename(columns=cm)
                    for col in ["open","high","low","close","volume"]:
                        if col in tmp.columns:
                            tmp[col] = pd.to_numeric(tmp[col], errors="coerce")
                    tmp = tmp.dropna(subset=["close"])
                    if len(tmp)>=10: return tmp.tail(days)
                except Exception: continue
        except Exception: pass

        # ── 3순위: FDR ────────────────────────────────────────
        try:
            import FinanceDataReader as fdr
            end   = datetime.now().strftime("%Y%m%d")
            start = (datetime.now()-timedelta(days=days+60)).strftime("%Y%m%d")
            df = fdr.DataReader(ticker, start, end)
            if df is not None and len(df)>=10:
                df = df.sort_index(ascending=True)
                for c in list(df.columns):
                    cl=str(c).strip().lower()
                    if cl in("close","adj close"): df=df.rename(columns={c:"close"})
                    elif cl=="volume": df=df.rename(columns={c:"volume"})
                    elif cl=="open": df=df.rename(columns={c:"open"})
                    elif cl=="high": df=df.rename(columns={c:"high"})
                    elif cl=="low": df=df.rename(columns={c:"low"})
                for col in ["open","high","low","close","volume"]:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors="coerce")
                return df.dropna(subset=["close"]).tail(days)
        except Exception: pass

    except Exception: pass
    return None


# ── 종목 리스트 조회 ──────────────────────────────────────────
# 내장 하드코딩 (Cloud 차단 환경 최후 보루)
_KOSPI_TICKERS = [
    ("005930","삼성전자"),("000660","SK하이닉스"),("373220","LG에너지솔루션"),
    ("207940","삼성바이오로직스"),("005380","현대차"),("000270","기아"),
    ("068270","셀트리온"),("005490","POSCO홀딩스"),("051910","LG화학"),
    ("028260","삼성물산"),("012330","현대모비스"),("066570","LG전자"),
    ("003550","LG"),("017670","SK텔레콤"),("086790","하나금융지주"),
    ("055550","신한지주"),("105560","KB금융"),("316140","우리금융지주"),
    ("003490","대한항공"),("009150","삼성전기"),("034730","SK"),
    ("030200","KT"),("036570","엔씨소프트"),("035720","카카오"),
    ("323410","카카오뱅크"),("259960","크래프톤"),("006400","삼성SDI"),
    ("000100","유한양행"),("128940","한미약품"),("000720","현대건설"),
    ("010130","고려아연"),("021240","코웨이"),("009540","한국조선해양"),
    ("042660","한화오션"),("329180","현대중공업"),("267250","HD현대"),
    ("003670","포스코퓨처엠"),("247540","에코프로비엠"),("086520","에코프로"),
    ("000810","삼성화재"),("032640","LG유플러스"),("078930","GS"),
    ("071050","한국금융지주"),("139480","이마트"),("004170","신세계"),
    ("011170","롯데케미칼"),("064350","현대로템"),("012450","한화에어로스페이스"),
    ("004020","현대제철"),("000880","한화"),("001040","CJ"),
    ("097950","CJ제일제당"),("033780","KT&G"),("002790","아모레퍼시픽"),
    ("051900","LG생활건강"),("006800","미래에셋증권"),("016360","삼성증권"),
    ("180640","한진칼"),("007310","오뚜기"),("010950","S-Oil"),
    ("096770","SK이노베이션"),("035420","NAVER"),("047810","한국항공우주"),
    ("272210","한화시스템"),("241560","두산밥캣"),("034020","두산에너빌리티"),
    ("082740","한화엔진"),("003230","삼양식품"),("010060","OCI홀딩스"),
    ("018260","삼성에스디에스"),("011200","HMM"),("028670","팬오션"),
]
_KOSDAQ_TICKERS = [
    ("091990","셀트리온헬스케어"),("145020","휴젤"),("196170","알테오젠"),
    ("214150","클래시스"),("263750","펄어비스"),("293930","카카오게임즈"),
    ("039030","이오테크닉스"),("357780","솔브레인"),("058470","리노공업"),
    ("064760","티씨케이"),("042700","한미반도체"),("089030","테크윙"),
    ("035760","CJ ENM"),("122870","와이지엔터테인먼트"),("035900","JYP Ent"),
    ("041510","에스엠"),("066970","엘앤에프"),("053800","안랩"),
    ("237690","에스티팜"),("214450","파마리서치"),("048260","오스템임플란트"),
    ("196300","에이비엘바이오"),("000250","삼천당제약"),("068760","셀트리온제약"),
    ("085660","차바이오텍"),("028300","HLB"),("047920","HLB제약"),
    ("096530","씨젠"),("145600","나노신소재"),("089590","제이시스메디칼"),
    ("007660","이수페타시스"),("108320","LX세미콘"),("095340","ISC"),
    ("131970","두산테스나"),("036930","주성엔지니어링"),("049950","미래컴퍼니"),
    ("060720","KH바텍"),("122990","와이솔"),("091580","상아프론테크"),
    ("036810","에프에스티"),("028300","HLB"),("060150","인선이엔티"),
    ("141080","리가켐바이오"),("335890","비비씨"),("950160","코오롱티슈진"),
    ("950130","엑세스바이오"),("086820","바이오솔루션"),("024840","KBI메탈"),
    ("101490","에스앤에스텍"),("080220","제주반도체"),("096190","티에스이"),
]


@st.cache_data(ttl=3600)
def get_market_tickers(market: str) -> list:
    """
    종목 리스트 — 4단계 폴백
    1) KIS 업종별 종목 조회
    2) FDR StockListing
    3) yfinance 내장 리스트
    4) 하드코딩 내장 리스트
    """
    suffix = ".KS" if market=="KOSPI" else ".KQ"
    errors = []

    # ── 1단계: KIS 업종별 조회 ────────────────────────────────
    if _kis_available():
        try:
            url    = f"{_kis_base_url()}/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice"
            # KIS 시장별 상위 종목 조회
            mkt_code = "0" if market=="KOSPI" else "1"
            url2   = f"{_kis_base_url()}/uapi/domestic-stock/v1/ranking/fluctuation"
            params = {
                "fid_cond_mrkt_div_code": "J",
                "fid_cond_scr_div_code":  "20170",
                "fid_input_iscd":         "0001" if market=="KOSPI" else "1001",
                "fid_rank_sort_cls_code":  "0",
                "fid_input_cnt_1":         "100",
                "fid_prc_cls_code":        "0",
                "fid_input_price_1":       "",
                "fid_input_price_2":       "",
                "fid_vol_cnt":             "100000",
                "fid_trgt_cls_code":       "0",
                "fid_trgt_exls_cls_code":  "0",
                "fid_div_cls_code":        "0",
                "fid_rsfl_rate1":          "",
                "fid_rsfl_rate2":          "",
            }
            resp = requests.get(url2, headers=_kis_headers("FHPST01170000"),
                                params=params, timeout=10, verify=False)
            if resp.status_code == 200:
                output = resp.json().get("output", [])
                rows = []
                for r in output:
                    code = str(r.get("stck_shrn_iscd","")).zfill(6)
                    name = r.get("hts_kor_isnm","")
                    if code.isdigit() and name:
                        rows.append({"ticker":code,"name":name,"market":market,
                                     "yf_ticker":code+suffix})
                if rows:
                    print(f"[KIS] {market}: {len(rows)}개")
                    return rows
        except Exception as e:
            errors.append(f"KIS: {e}")

    # ── 2단계: FDR ────────────────────────────────────────────
    try:
        import FinanceDataReader as fdr
        lst = fdr.StockListing(market)
        if lst is not None and len(lst)>0:
            lst.columns = [c.strip() for c in lst.columns]
            cc = next((c for c in lst.columns if c in ["Code","Symbol"]),None)
            nc = next((c for c in lst.columns if c in ["Name","종목명"]),None)
            ac = next((c for c in lst.columns if c in ["Amount","Tvalue","Marcap"]),None)
            if cc:
                lst[cc] = lst[cc].astype(str).str.zfill(6)
                sample  = lst.nlargest(120,ac) if ac else lst.head(120)
                rows    = [{"ticker":str(r[cc]).zfill(6),
                            "name":str(r.get(nc,r[cc])),
                            "market":market,
                            "yf_ticker":str(r[cc]).zfill(6)+suffix}
                           for _,r in sample.iterrows() if str(r[cc]).isdigit()]
                if rows:
                    print(f"[FDR] {market}: {len(rows)}개")
                    return rows
    except Exception as e:
        errors.append(f"FDR: {e}")

    # ── 3·4단계: 내장 리스트 ──────────────────────────────────
    base = _KOSPI_TICKERS if market=="KOSPI" else _KOSDAQ_TICKERS
    print(f"[내장] {market}: {len(base)}개 (오류: {'; '.join(str(e) for e in errors)})")
    return [{"ticker":c,"name":n,"market":market,"yf_ticker":c+suffix} for c,n in base]


@st.cache_data(ttl=3600)
def get_stock_list() -> pd.DataFrame:
    """포트폴리오 검색용 전체 종목 리스트"""
    rows = []

    # KIS → FDR → 내장 순 폴백
    for market in ["KOSPI","KOSDAQ"]:
        tickers = get_market_tickers(market)
        for t in tickers:
            rows.append({"code":t["ticker"],"name":t["name"],
                         "market":market,
                         "display":f"{t['name']} ({t['ticker']})"})

    if not rows:
        for c,n in _KOSPI_TICKERS:
            rows.append({"code":str(c).zfill(6),"name":n,"market":"KOSPI",
                         "display":f"{n} ({str(c).zfill(6)})"})
        for c,n in _KOSDAQ_TICKERS:
            rows.append({"code":str(c).zfill(6),"name":n,"market":"KOSDAQ",
                         "display":f"{n} ({str(c).zfill(6)})"})

    return (pd.DataFrame(rows)
            .drop_duplicates("code")
            .sort_values("name")
            .reset_index(drop=True))



def calc_atr_targets(ticker: str, atr_mult_stop: float = 2.0,
                      atr_mult_target: float = 6.0) -> dict:
    try:
        df = get_ohlcv_cached(ticker, days=30)
        if df is None or len(df) < 15: return {}
        import ta
        df["atr"] = ta.volatility.AverageTrueRange(
            df["high"],df["low"],df["close"],window=14).average_true_range()
        df = df.ffill().fillna(0)
        row = df.iloc[-1]
        cur = float(row["close"]); atr_val = float(row["atr"])
        if atr_val<=0 or cur<=0: return {}
        return {"cur":cur,"atr":round(atr_val,2),"atr_pct":round(atr_val/cur*100,2),
                "stoploss":round(cur-atr_val*atr_mult_stop,0),
                "target":round(cur+atr_val*atr_mult_target,0)}
    except Exception: return {}

def calc_trailing_stop(ticker: str, buy_price: float, buy_date: str,
                        atr_mult: float = 2.0, saved_high: float = 0.0) -> dict:
    try:
        df = get_ohlcv_cached(ticker, days=120)
        if df is None or len(df)<15: return {}
        import ta
        df["atr"] = ta.volatility.AverageTrueRange(
            df["high"],df["low"],df["close"],window=14).average_true_range()
        df = df.ffill().fillna(0)
        cur_price = float(df["close"].iloc[-1])
        atr_val   = float(df["atr"].iloc[-1])
        try:
            buy_dt   = pd.to_datetime(buy_date)
            df_after = df[df.index>=buy_dt]
        except Exception:
            df_after = df
        peak_high = float(df_after["high"].max()) if len(df_after)>0 and "high" in df_after.columns else buy_price
        peak_high = max(peak_high, saved_high, buy_price)
        initial_sl  = buy_price - atr_val*atr_mult
        trailing_sl = max(initial_sl, peak_high-atr_val*atr_mult)
        return {"cur":cur_price,"atr":round(atr_val,2),
                "peak_high":round(peak_high,0),"initial_sl":round(initial_sl,0),
                "trailing_sl":round(trailing_sl,0),"trail_raised":trailing_sl>initial_sl,
                "sl_triggered":cur_price<=trailing_sl,
                "pnl_pct":round((cur_price-buy_price)/buy_price*100,2) if buy_price else 0,
                "trail_pct":round((peak_high-buy_price)/(atr_val*atr_mult)*100,1) if atr_val else 0}
    except Exception: return {}


def show_login():
    try:
        st.markdown(
            '<div style="max-width:380px;margin:3rem auto;">'
            '<div class="card" style="border-top:3px solid #6366f1;padding:2rem;">'
            '<div style="text-align:center;margin-bottom:1.5rem;">'
            '<div style="font-size:2.5rem;">📈</div>'
            '<h2 style="margin:0.3rem 0;">스윙 대시보드</h2>'
            '<div style="color:#94a3b8;font-size:0.85rem;">로그인하여 시작하세요</div>'
            '</div>', unsafe_allow_html=True)
        with st.form("login_form"):
            uid = st.text_input("아이디", placeholder="admin")
            pw  = st.text_input("비밀번호", type="password", placeholder="1234")
            ok  = st.form_submit_button("🔐 로그인", use_container_width=True)
        st.markdown('</div></div>', unsafe_allow_html=True)
        if ok:
            users = load_users()
            if uid in users and users[uid].get("pw") == hash_pw(pw):
                st.session_state["user"] = uid
                st.session_state["seed"] = users[uid].get("seed", 2_000_000)
                st.rerun()
            else:
                st.error("아이디 또는 비밀번호가 틀렸습니다.")
        st.caption("기본 계정: admin / 1234")
        with st.expander("📝 회원가입"):
            with st.form("signup_form"):
                nid = st.text_input("새 아이디")
                npw = st.text_input("새 비밀번호", type="password")
                npw2= st.text_input("비밀번호 확인", type="password")
                if st.form_submit_button("가입"):
                    if npw != npw2: st.error("비밀번호 불일치")
                    elif len(nid)<2: st.error("아이디 2자 이상")
                    else:
                        users = load_users()
                        if nid in users: st.error("이미 사용 중")
                        else:
                            users[nid] = {"pw": hash_pw(npw), "seed": 2_000_000}
                            save_users(users)
                            st.success("✅ 가입 완료!")
    except Exception as e:
        st.error(f"로그인 화면 오류: {e}")


def page_dashboard(username: str):
    try:
        st.markdown("## 📊 대시보드")
        portfolio = load_portfolio(username)
        holding   = [p for p in portfolio if p.get("status") == "보유"]
        if not holding:
            st.info("포트폴리오에 종목을 추가하면 대시보드가 활성화됩니다.")
            return

        rows, total_cost, total_cur = [], 0.0, 0.0
        for p in holding:
            try:
                qty       = int(p.get("qty", 1))
                buy_price = float(p.get("buy_price", 0))
                cost      = float(p.get("total_amount", buy_price * qty))
                cur       = float(get_price(p["ticker"]) or buy_price)
                val       = cur * qty
                pnl       = val - cost
                total_cost += cost; total_cur += val
                rows.append({**p, "cur_price": cur, "pnl": pnl,
                              "pnl_pct": pnl/cost*100 if cost else 0})
            except Exception:
                continue

        unrealized = total_cur - total_cost
        realized   = sum(float(p.get("realized_pnl", 0))
                         for p in portfolio if p.get("status") == "청산")
        total_pnl  = unrealized + realized
        inv_pct    = total_pnl / total_cost * 100 if total_cost else 0

        def cc(v): return "#38bdf8" if v>=0 else "#f87171"
        def sg(v): return "+" if v>=0 else ""
        def bl(v): return f"border-left:4px solid {'#38bdf8' if v>=0 else '#f87171'};"

        k1,k2,k3,k4 = st.columns(4)
        with k1:
            st.markdown(
                f'<div class="card" style="border-left:4px solid #94a3b8;">'
                f'<div class="label">💼 투자액</div>'
                f'<div class="big-num mono">{total_cost:,.0f}원</div>'
                f'</div>', unsafe_allow_html=True)
        with k2:
            st.markdown(
                f'<div class="card" style="{bl(unrealized)}">'
                f'<div class="label">📈 미실현 손익</div>'
                f'<div class="big-num mono" style="color:{cc(unrealized)};">'
                f'{sg(unrealized)}{unrealized:,.0f}원</div>'
                f'<div style="color:{cc(unrealized)};font-size:0.75rem;">'
                f'{unrealized/total_cost*100:+.2f}%</div>'
                f'</div>', unsafe_allow_html=True)
        with k3:
            st.markdown(
                f'<div class="card" style="{bl(realized)}">'
                f'<div class="label">✅ 실현 손익</div>'
                f'<div class="big-num mono" style="color:{cc(realized)};">'
                f'{sg(realized)}{realized:,.0f}원</div>'
                f'</div>', unsafe_allow_html=True)
        with k4:
            st.markdown(
                f'<div class="card" style="{bl(inv_pct)}">'
                f'<div class="label">🎯 총 수익률</div>'
                f'<div class="big-num mono" style="color:{cc(inv_pct)};font-size:1.8rem;">'
                f'{sg(inv_pct)}{inv_pct:.2f}%</div>'
                f'<div style="color:#94a3b8;font-size:0.72rem;">투자액 기준</div>'
                f'</div>', unsafe_allow_html=True)

        # 차트
        try:
            ch1, ch2 = st.columns(2)
            with ch1:
                labels = [r["name"] for r in rows]
                values = [r["cur_price"]*int(r.get("qty",1)) for r in rows]
                colors = ["#38bdf8","#34d399","#fbbf24","#f87171","#a78bfa","#fb923c"]
                fig = go.Figure(go.Pie(labels=labels, values=values, hole=0.55,
                    marker=dict(colors=colors[:len(labels)]),
                    textfont=dict(size=11, color="#e2e8f0")))
                fig.update_layout(paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    margin=dict(t=30,b=10,l=10,r=10), height=220,
                    legend=dict(font=dict(color="#94a3b8",size=10)),
                    title=dict(text="포트폴리오 구성",font=dict(color="#94a3b8",size=12)))
                st.plotly_chart(fig, use_container_width=True)
            with ch2:
                pnls = [r["pnl"] for r in rows]
                fig2 = go.Figure(go.Bar(
                    x=[r["name"] for r in rows], y=pnls,
                    marker_color=["#38bdf8" if p>=0 else "#f87171" for p in pnls],
                    text=[f'{sg(p)}{p:,.0f}원' for p in pnls],
                    textposition="outside", textfont=dict(color="#e2e8f0",size=10)))
                fig2.update_layout(paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    yaxis=dict(gridcolor="#2d3748",color="#94a3b8",tickfont=dict(size=10)),
                    xaxis=dict(color="#94a3b8",tickfont=dict(size=10)),
                    margin=dict(t=30,b=10,l=10,r=10), height=220, showlegend=False,
                    title=dict(text="종목별 손익",font=dict(color="#94a3b8",size=12)))
                st.plotly_chart(fig2, use_container_width=True)
        except Exception as e:
            st.caption(f"차트 오류: {e}")

        st.caption(f"기준일: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    except Exception as e:
        st.error(f"대시보드 오류: {e}")


def page_portfolio(username: str):
    try:
        st.markdown("## 💼 내 포트폴리오")

        # ATR 설정 (사이드바)
        with st.sidebar:
            st.markdown("### ⚙️ ATR 설정")
            atr_stop = st.number_input("손절 ATR배수", value=2.0, step=0.5,
                                        min_value=0.5, key="pf_atrs")
            atr_tgt  = st.number_input("익절 ATR배수", value=3.0, step=0.5,
                                        min_value=1.0, key="pf_atrt")

        portfolio = load_portfolio(username)
        if fix_portfolio_realized(username):
            st.toast("📌 데이터 정상화 완료")

        # ── 매매 기록 추가 ────────────────────────────────
        with st.expander("➕ 매매 기록 추가", expanded=False):

            # 종목 검색 — st.form 없이 즉시 반응
            stock_df = get_stock_list()

            if stock_df.empty:
                # 내장 리스트로 직접 구성
                inner = (
                    [{"code":c,"name":n,"market":"KOSPI","display":f"{n} ({c})"}
                     for c,n in _KOSPI_TICKERS] +
                    [{"code":c,"name":n,"market":"KOSDAQ","display":f"{n} ({c})"}
                     for c,n in _KOSDAQ_TICKERS]
                )
                stock_df = pd.DataFrame(inner).sort_values("name").reset_index(drop=True)

            # 검색창 — 이름 또는 코드로 퍼지 검색
            search_q = st.text_input("🔍 종목명 또는 코드 검색",
                                      placeholder="예: 이수페타시스, 005930",
                                      key="pf_search_q")

            # 검색 필터링
            if search_q.strip():
                q = search_q.strip().lower()
                mask = (stock_df["name"].str.contains(search_q.strip(), na=False)) |                        (stock_df["code"].str.contains(q, na=False))
                filtered = stock_df[mask].reset_index(drop=True)
            else:
                filtered = stock_df.copy()

            if filtered.empty:
                st.warning(f"'{search_q}' 검색 결과 없음")
                sel_name = sel_ticker = sel_market = ""
            else:
                disp_list = filtered["display"].tolist()
                # 검색어 있으면 첫 번째 자동 선택
                default_idx = 0 if search_q.strip() else None
                sel = st.selectbox("종목 선택", disp_list,
                                    index=default_idx,
                                    key="pf_stock_sel",
                                    placeholder="종목을 선택하세요...")
                if sel:
                    row_sel   = filtered[filtered["display"]==sel].iloc[0]
                    sel_name   = row_sel["name"]
                    sel_ticker = row_sel["code"]
                    sel_market = row_sel["market"]
                    # 선택 확인 배지
                    st.markdown(
                        f'<div style="background:#1e2535;border:1px solid #34d399;'
                        f'border-radius:8px;padding:0.4rem 0.9rem;font-size:0.85rem;'
                        f'color:#34d399;margin:0.3rem 0;">'
                        f'✅ <b>{sel_name}</b> | {sel_ticker} | {sel_market}'
                        f'</div>', unsafe_allow_html=True)
                else:
                    sel_name = sel_ticker = sel_market = ""

            st.markdown("---")
            c1,c2,c3,c4 = st.columns([2,1,2,1])
            with c1: trade_dt     = st.date_input("거래일", value=datetime.today(), key="pf_dt")
            with c2: qty          = st.number_input("수량(주)", min_value=1, value=1,
                                                    step=1, key="pf_qty")
            with c3: total_amount = st.number_input("총 매수금액(원)", min_value=0,
                                                    value=0, step=10000, key="pf_amt")
            with c4: kind         = st.selectbox("구분", ["매수","매도"], key="pf_kind")

            avg_price = total_amount/qty if qty>0 and total_amount>0 else 0

            # ATR 미리보기
            if sel_ticker and avg_price > 0:
                try:
                    atr_info = calc_atr_targets(sel_ticker, atr_stop, atr_tgt)
                    if atr_info:
                        a1,a2,a3,a4 = st.columns(4)
                        a1.metric("평단가",         f"{avg_price:,.0f}원")
                        a2.metric("ATR",            f"{atr_info['atr']:,.0f}원 "
                                                    f"({atr_info['atr_pct']:.1f}%)")
                        a3.metric(f"🛑 손절({atr_stop}×)",
                                  f"{atr_info['stoploss']:,.0f}원",
                                  delta=f"{(atr_info['stoploss']-avg_price)/avg_price*100:.1f}%",
                                  delta_color="inverse")
                        a4.metric(f"🎯 익절({atr_tgt}×)",
                                  f"{atr_info['target']:,.0f}원",
                                  delta=f"+{(atr_info['target']-avg_price)/avg_price*100:.1f}%")
                except Exception:
                    pass

            # 저장 버튼 — 즉시 반응
            can_save = bool(sel_ticker) and avg_price > 0
            if st.button("💾 기록 저장", key="pf_save",
                         disabled=not can_save,
                         type="primary" if can_save else "secondary"):
                try:
                    sl, tg, atr_v = int(avg_price*0.93), int(avg_price*1.09), 0.0
                    try:
                        ai = calc_atr_targets(sel_ticker, atr_stop, atr_tgt)
                        if ai:
                            sl, tg, atr_v = int(ai["stoploss"]), int(ai["target"]), ai["atr"]
                    except Exception: pass

                    portfolio.append({
                        "id":           int(time.time()),
                        "kind":         kind,
                        "name":         sel_name,
                        "ticker":       str(sel_ticker).zfill(6),
                        "market":       sel_market,
                        "date":         str(trade_dt),
                        "qty":          int(qty),
                        "buy_price":    round(avg_price, 2),
                        "total_amount": int(total_amount),
                        "stoploss_atr": sl,
                        "target_atr":   tg,
                        "atr_val":      atr_v,
                        "atr_stop_mult": atr_stop,
                        "atr_tgt_mult":  atr_tgt,
                        "status":       "보유" if kind=="매수" else "청산",
                        "realized_pnl": 0,
                        "peak_high":    avg_price,
                    })
                    save_portfolio(username, portfolio)
                    st.success(f"✅ {sel_name} 저장! 손절:{sl:,} / 익절:{tg:,}")
                    # session_state 초기화 후 즉시 rerun
                    for k in ["pf_search_q","pf_stock_sel","pf_amt","pf_qty"]:
                        if k in st.session_state:
                            del st.session_state[k]
                    st.rerun()
                except Exception as e:
                    st.error(f"저장 오류: {e}")

        # ── 보유 종목 현황 ────────────────────────────────
        holding = [p for p in portfolio if p.get("status")=="보유"]
        if not holding:
            st.info("보유 중인 종목이 없습니다.")
            return

        st.markdown("### 📋 보유 종목")
        st.caption("🔺 트레일링 스탑 — 최고가 기준 자동 상향, 하락 시 고정")

        total_cost = total_cur = 0.0
        for p in holding:
            try:
                qty_n     = int(p.get("qty",1))
                buy_price = float(p.get("buy_price",0))
                cost      = float(p.get("total_amount", buy_price*qty_n))
                total_cost += cost

                # 트레일링 스탑
                saved_high = float(p.get("peak_high", buy_price))
                try:
                    trail = calc_trailing_stop(p["ticker"], buy_price,
                                               p.get("date",""), atr_stop, saved_high)
                except Exception:
                    trail = {}

                if trail:
                    cur          = trail["cur"]
                    atr_val      = trail["atr"]
                    peak_high    = trail["peak_high"]
                    initial_sl   = trail["initial_sl"]
                    trailing_sl  = trail["trailing_sl"]
                    trail_raised = trail["trail_raised"]
                    sl_triggered = trail["sl_triggered"]
                    trail_pct    = trail["trail_pct"]
                    try:
                        for item in portfolio:
                            if item["id"]==p["id"] and peak_high>item.get("peak_high",0):
                                item["peak_high"] = peak_high
                        save_portfolio(username, portfolio)
                    except Exception: pass
                else:
                    cur          = float(get_price(str(p["ticker"]).zfill(6)) or buy_price)
                    atr_val      = float(p.get("atr_val",0))
                    peak_high    = saved_high
                    initial_sl   = float(p.get("stoploss_atr", buy_price*0.93))
                    trailing_sl  = initial_sl
                    trail_raised = False
                    sl_triggered = cur <= trailing_sl
                    trail_pct    = 0.0

                val     = cur * qty_n
                pnl     = val - cost
                pnl_pct = pnl/cost*100 if cost else 0
                total_cur += val
                tg   = float(p.get("target_atr", buy_price*1.09))
                cc_  = "#38bdf8" if pnl>=0 else "#f87171"
                sg_  = "+" if pnl>=0 else ""

                if sl_triggered:    badge,bc = "🚨 손절 발동!","#f87171"
                elif cur>=tg:       badge,bc = "🎯 익절 도달!","#34d399"
                elif trail_raised:  badge,bc = "🔺 손절선 상향","#38bdf8"
                else:               badge,bc = "⏳ 보유중","#94a3b8"

                st.markdown(
                    f'<div class="card" style="border-left:4px solid {bc};">'
                    f'<div style="display:flex;justify-content:space-between;">'
                    f'<div>'
                    f'<b>{p["name"]}</b>'
                    f'<span style="color:#94a3b8;font-size:0.73rem;margin-left:0.4rem;">{p["ticker"]}</span>'
                    f'<span style="background:{bc}22;color:{bc};border-radius:5px;'
                    f'padding:1px 8px;font-size:0.7rem;margin-left:0.3rem;">{badge}</span>'
                    f'</div>'
                    f'<div style="text-align:right;">'
                    f'<div style="color:{cc_};font-family:JetBrains Mono,monospace;font-weight:900;font-size:1.1rem;">{sg_}{pnl_pct:.2f}%</div>'
                    f'<div style="color:{cc_};font-size:0.75rem;">{sg_}{pnl:,.0f}원</div>'
                    f'</div></div>'
                    f'<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:0.4rem;margin-top:0.5rem;font-size:0.78rem;">'
                    f'<div><div class="label">평단가</div><b class="mono">{buy_price:,.0f}원</b></div>'
                    f'<div><div class="label">현재가</div><b class="mono" style="color:{cc_}">{cur:,.0f}원</b></div>'
                    f'<div><div class="label">🏔 최고가</div><b class="mono" style="color:#fbbf24">{peak_high:,.0f}원</b></div>'
                    f'</div>'
                    f'<div style="border-top:1px solid #2d3748;margin:0.4rem 0;"></div>'
                    f'<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:0.4rem;font-size:0.78rem;">'
                    f'<div><div class="label">🛑 초기손절</div><b class="mono" style="color:#94a3b8">{initial_sl:,.0f}원</b></div>'
                    f'<div><div class="label" style="color:#38bdf8">🔺 트레일링손절</div><b class="mono" style="color:{"#f87171" if sl_triggered else "#38bdf8" if trail_raised else "#e2e8f0"}">{trailing_sl:,.0f}원</b></div>'
                    f'<div><div class="label">🎯 익절가</div><b class="mono" style="color:#34d399">{tg:,.0f}원</b></div>'
                    f'</div></div>', unsafe_allow_html=True)

                if trail_pct > 0:
                    bw  = min(trail_pct,100)
                    bc2 = "#34d399" if bw>=70 else ("#fbbf24" if bw>=30 else "#38bdf8")
                    st.markdown(
                        f'<div style="margin:-0.1rem 0 0.3rem;padding:0 0.2rem;">'
                        f'<div style="font-size:0.67rem;color:#94a3b8;">트레일링 {trail_pct:.0f}%</div>'
                        f'<div style="background:#2d3748;border-radius:4px;height:4px;">'
                        f'<div style="background:{bc2};width:{bw}%;height:4px;border-radius:4px;"></div>'
                        f'</div></div>', unsafe_allow_html=True)

                with st.expander(f"🔧 {p['name']} 조작", expanded=False):
                    rc1,rc2,rc3 = st.columns(3)
                    with rc1:
                        if st.button("🔄 ATR 재계산", key=f"rc_{p['id']}"):
                            try:
                                na = calc_atr_targets(p["ticker"], atr_stop, atr_tgt)
                                if na:
                                    for item in portfolio:
                                        if item["id"]==p["id"]:
                                            item.update({"stoploss_atr":int(na["stoploss"]),
                                                         "target_atr":int(na["target"]),
                                                         "atr_val":na["atr"],
                                                         "atr_stop_mult":atr_stop,
                                                         "atr_tgt_mult":atr_tgt})
                                    save_portfolio(username, portfolio)
                                    st.success("재계산 완료!")
                                    st.rerun()
                            except Exception as e:
                                st.error(f"재계산 오류: {e}")
                    with rc2:
                        if st.button("✅ 청산", key=f"sell_{p['id']}"):
                            realized = (cur - buy_price) * qty_n
                            for item in portfolio:
                                if item["id"]==p["id"]:
                                    item["status"]="청산"
                                    item["realized_pnl"]=realized
                            save_portfolio(username, portfolio)
                            st.success(f"청산 완료 ({realized:+,.0f}원)")
                            st.rerun()
                    with rc3:
                        if st.button("🗑️ 삭제", key=f"del_{p['id']}"):
                            save_portfolio(username,[x for x in portfolio if x["id"]!=p["id"]])
                            st.rerun()

            except Exception as e:
                st.warning(f"종목 렌더링 오류: {e}")
                continue

        # ── 포트폴리오 요약 ──────────────────────────────
        st.markdown("---")
        unrealized = total_cur - total_cost
        realized   = sum(float(p.get("realized_pnl",0))
                         for p in portfolio if p.get("status")=="청산")
        total_pnl  = unrealized + realized
        inv_pct    = total_pnl/total_cost*100 if total_cost else 0
        s1,s2,s3,s4 = st.columns(4)
        for col,label,val,color in [
            (s1,"💼 투자액",   f"{total_cost:,.0f}원",  "#94a3b8"),
            (s2,"📈 미실현",  f"{unrealized:+,.0f}원",  "#38bdf8" if unrealized>=0 else "#f87171"),
            (s3,"✅ 실현",    f"{realized:+,.0f}원",    "#34d399" if realized>=0  else "#f87171"),
            (s4,"🎯 수익률",  f"{inv_pct:+.2f}%",       "#38bdf8" if inv_pct>=0   else "#f87171"),
        ]:
            col.markdown(
                f'<div class="card" style="text-align:center;">'
                f'<div class="label">{label}</div>'
                f'<div style="color:{color};font-family:JetBrains Mono,monospace;'
                f'font-size:1rem;font-weight:700;">{val}</div>'
                f'</div>', unsafe_allow_html=True)

    except Exception as e:
        st.error(f"포트폴리오 오류: {e}")
        import traceback; st.code(traceback.format_exc())


def page_quant(username: str):
    try:
        st.markdown("## 🧮 퀀트 스캐너 2차 정밀")

        import os, json as _json

        data_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "data", "quant_scan.json")
        meta_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "data", "meta.json")

        if not os.path.exists(data_path):
            st.warning("📭 스캔 데이터 없음 — GitHub Actions 설정이 필요합니다.")
            with st.expander("📋 설정 방법 (1회만 하면 됩니다)", expanded=True):
                st.markdown("""
                **GitHub Actions가 매일 장 마감 후 자동으로 데이터를 수집합니다.**

                ### 1단계: 저장소에 파일 2개 추가
                아래 파일들을 GitHub에 업로드하세요:
                - `.github/workflows/collect_data.yml`
                - `scripts/collect_stock_data.py`

                ### 2단계: 첫 실행
                ```
                GitHub → Actions 탭 → "주식 데이터 수집" → Run workflow
                ```

                ### 3단계: 이후 자동화
                매일 오후 4시(KST) 자동 수집됩니다.
                """)
            return

        # 메타 정보
        updated = "알 수 없음"
        try:
            with open(meta_path, encoding="utf-8") as f:
                meta = _json.load(f)
            updated = meta.get("updated_at","알 수 없음")
            st.success(f"✅ 데이터 기준: **{updated}** | 총 {meta.get('total',0)}개 | 🔥A급 {meta.get('a_grade',0)}개")
        except Exception:
            pass

        with open(data_path, encoding="utf-8") as f:
            all_records = _json.load(f)
        if not all_records:
            st.info("📭 데이터가 비어있습니다.")
            return

        st.info(f"📊 장 마감 후 수집 데이터 | {updated} 기준 | 실시간 현재가는 별도 조회")

        # 필터 UI
        with st.expander("🔍 필터", expanded=True):
            fc1,fc2,fc3,fc4 = st.columns(4)
            with fc1: f_market   = st.selectbox("시장",["전체","KOSPI","KOSDAQ"],key="q_f_mkt")
            with fc2: f_score    = st.slider("최소 종합점수",0,100,0,key="q_f_score")
            with fc3: f_n        = st.slider("표시 종목수",10,100,30,key="q_f_n")
            with fc4: f_a        = st.checkbox("🔥 A급만",key="q_f_a")

        records = all_records.copy()
        if f_market != "전체":
            records = [r for r in records if r.get("시장")==f_market]
        if f_score > 0:
            records = [r for r in records if r.get("종합점수",0)>=f_score]
        if f_a:
            records = [r for r in records if r.get("is_a",False)]
        records = sorted(records,
            key=lambda x:(x.get("is_a",False),x.get("종합점수",0)),
            reverse=True)[:f_n]

        if not records:
            st.info("📭 필터 조건에 맞는 종목 없음")
            return

        df_show = pd.DataFrame(records)
        df_show["종목코드"] = df_show["종목코드"].astype(str).str.zfill(6)
        a_cnt = sum(1 for r in records if r.get("is_a"))
        st.markdown(f"### 📊 {len(records)}개 | 🔥A급 {a_cnt}개")

        fa,fb = st.columns([4,1])
        with fa: st.caption("종합점수 내림차순 | ATR 손절×2.0 / 익절×3.0")
        with fb:
            if st.button("🔥 전체 추가",key="q_all",type="primary"):
                added,today = 0,datetime.now().strftime("%Y-%m-%d")
                for r in records:
                    ticker = str(r["종목코드"]).zfill(6)
                    cur_p  = float(r["현재가"])
                    try:
                        ai = calc_atr_targets(ticker,2.0,3.0)
                        sl = int(ai["stoploss"]) if ai else int(cur_p*0.93)
                        tg = int(ai["target"])   if ai else int(cur_p*1.09)
                    except: sl,tg = int(cur_p*0.93),int(cur_p*1.09)
                    rv = add_to_watchlist(username=username,ticker=ticker,
                        name=r["종목명"],source="퀀트",entry=int(cur_p),
                        target=tg,stoploss=sl,market=r.get("시장",""),
                        scan_date=today,base_price=cur_p)
                    if rv in("added","updated"): added+=1
                st.success(f"✅ {added}개 추가!")
                if added>0: st.balloons()

        disp = ["종목코드","종목명","시장","현재가","종합점수","RSI",
                "이격도(%)","ATR(%)","12개월수익률(%)","거래대금(억)"]
        df_ed = df_show[[c for c in disp if c in df_show.columns]].copy()
        df_ed.insert(0,"선택",False)
        df_ed.insert(0,"등급",df_show.get("is_a",
            pd.Series([False]*len(df_show))).map({True:"🔥",False:"—"}))
        edited = st.data_editor(df_ed,
            column_config={"선택":st.column_config.CheckboxColumn("선택",default=False)},
            disabled=[c for c in df_ed.columns if c!="선택"],
            use_container_width=True,hide_index=True,key="q_editor")
        sel = edited[edited["선택"]==True]
        st.caption(f"{len(sel)}개 선택")
        if st.button(f"➕ 선택 {len(sel)}개 추가",type="primary",
                     disabled=len(sel)==0,key="q_bulk"):
            added,today = 0,datetime.now().strftime("%Y-%m-%d")
            for _,row in sel.iterrows():
                ticker  = str(row["종목코드"]).zfill(6)
                matched = next((r for r in records
                    if str(r["종목코드"]).zfill(6)==ticker),None)
                if not matched: continue
                cur_p = float(matched["현재가"])
                try:
                    ai = calc_atr_targets(ticker,2.0,3.0)
                    sl = int(ai["stoploss"]) if ai else int(cur_p*0.93)
                    tg = int(ai["target"])   if ai else int(cur_p*1.09)
                except: sl,tg = int(cur_p*0.93),int(cur_p*1.09)
                rv = add_to_watchlist(username=username,ticker=ticker,
                    name=matched["종목명"],source="퀀트",entry=int(cur_p),
                    target=tg,stoploss=sl,market=matched.get("시장",""),
                    scan_date=today,base_price=cur_p)
                if rv in("added","updated"): added+=1
            st.success(f"✅ {added}개 추가!")
        st.session_state["quant_results"] = [
            {"종목코드":str(r["종목코드"]).zfill(6),"종목명":r["종목명"]}
            for r in records]

    except Exception as e:
        st.error(f"퀀트 스캐너 오류: {e}")
        import traceback; st.code(traceback.format_exc())


def page_supply_swing(username: str):
    try:
        st.markdown("## 📡 수급 기반 스윙 스캐너")
        st.info("💡 수급 점수(외인+기관) → 스윙 타점(ATR) 2단계 분석. 수급 없는 종목 자동 제외.")

        # ── 황금 필터 — 백테스팅 검증값 고정 ─────────────────
        with st.expander("⚙️ 스캔 조건 (황금 필터)", expanded=True):
            c1,c2,c3,c4 = st.columns(4)
            with c1:
                market_s = st.selectbox("시장", ["KOSPI","KOSDAQ","전체"],
                                         index=0, key="ssw_mkt")
                top_n    = st.slider("Top N", 10, 50, 20, key="ssw_n")
            with c2:
                # 황금 필터 고정값
                rsi_min    = st.number_input("RSI 하한 (기본 50)", value=50, step=5,
                                              key="ssw_rsi_min", help="백테스팅 검증: 50 이상")
                rsi_max    = st.number_input("RSI 상한", value=85, step=5, key="ssw_rsi_max")
            with c3:
                min_score  = st.number_input("최소 수급점수 (기본 50)", value=50, step=5,
                                              key="ssw_score", help="백테스팅 검증: 50점 이상")
                min_vol_bil = st.number_input("최소 거래대금(억, 기본 200)", value=200, step=50,
                                               key="ssw_val", help="백테스팅 검증: 200억 이상")
            with c4:
                # 수급 집계 200일 고정
                days_label = st.text_input("수급 집계 기간", value="200일 (고정)",
                                            disabled=True, key="ssw_days_label")
                atr_s      = st.number_input("손절 ATR배수", value=2.0, step=0.5, key="ssw_atr_s")

        # 황금 필터 요약
        st.markdown(
            f'<div style="background:#1e2535;border:1px solid #6366f1;border-radius:8px;'
            f'padding:0.4rem 0.9rem;font-size:0.8rem;color:#94a3b8;margin-bottom:0.5rem;">'
            f'🏆 황금 필터 — RSI≥{rsi_min} | 거래대금≥{min_vol_bil}억 | 수급점수≥{min_score}점 | 수급집계 200일 고정</div>',
            unsafe_allow_html=True)

        if st.button("🔍 통합 스캔 시작", type="primary", key="ssw_scan"):
            import yfinance as yf, FinanceDataReader as fdr, ta

            prog = st.progress(0, text="종목 수집 중...")
            markets = ["KOSPI","KOSDAQ"] if market_s=="전체" else [market_s]
            pool    = []
            for mkt in markets: pool.extend(get_market_tickers(mkt))
            if not pool:
                st.error("❌ 종목 목록 없음"); return

            sfx     = {"KOSPI":".KS","KOSDAQ":".KQ"}
            total   = len(pool)
            results = []
            end_dt  = datetime.now()
            # 수급 집계 200일 고정
            sup_start = (end_dt - timedelta(days=200)).strftime("%Y-%m-%d")
            end_str   = end_dt.strftime("%Y%m%d")
            start_str = (end_dt - timedelta(days=250)).strftime("%Y%m%d")
            s_yf      = start_str[:4]+"-"+start_str[4:6]+"-"+start_str[6:]
            e_yf      = end_str[:4]+"-"+end_str[4:6]+"-"+end_str[6:]

            # ── 현재가 딕셔너리 (1:1 정밀 매핑) ──────────────
            # 수집 중 오류로 순서 밀림 방지 — ticker를 key로 매핑
            price_dict: dict = {}

            for i, t in enumerate(pool):
                if i % 5 == 0:
                    prog.progress(int(5+i/total*88),
                        text=f"분석 {i+1}/{total} | 발굴: {len(results)}개")
                try:
                    ticker = str(t["ticker"]).zfill(6)
                    yf_t   = t.get("yf_ticker", ticker+sfx.get(t["market"],".KS"))
                    tk     = yf.Ticker(yf_t)

                    # STEP1: 수급 점수 (200일 기준 고정)
                    info = {}
                    try: info = tk.info or {}
                    except Exception: pass

                    inst_pct  = float(info.get("heldPercentInstitutions",0) or 0)*100
                    insider   = float(info.get("heldPercentInsiders",0) or 0)*100
                    foreign   = max(0.0, 100-inst_pct-insider)

                    # 수급 데이터 없으면 제외
                    if inst_pct < 1 and foreign < 5: continue

                    hist = None
                    try: hist = tk.history(start=sup_start, end=e_yf, auto_adjust=False)
                    except Exception: pass
                    if hist is None or len(hist) < 3: continue

                    avg_vol   = float(hist["Volume"].mean()) if len(hist)>0 else 1
                    rec_vol   = float(hist["Volume"].iloc[-20:].mean()) if len(hist)>=20 else avg_vol
                    vol_ratio = round(rec_vol/avg_vol, 2) if avg_vol>0 else 1.0

                    inst_s = min(40, inst_pct*2)
                    for_s  = min(30, foreign*0.8)
                    vol_s  = min(20, (vol_ratio-1)*20) if vol_ratio>1 else 0
                    score  = round(inst_s+for_s+vol_s, 1)

                    # 황금 필터: 최소 수급점수 50점
                    if score < min_score: continue

                    # 태그
                    if inst_pct>=15 and foreign>=20 and vol_ratio>=1.3:   tag="🔥쌍끌이"
                    elif inst_pct>=10 and vol_ratio>=1.2:                  tag="📈기관강세"
                    elif foreign>=25 and vol_ratio>=1.2:                   tag="🌍외인강세"
                    else:                                                   tag="📊수급있음"

                    # STEP2: 스윙 차트 + 황금 필터
                    df = None
                    try:
                        tmp = yf.download(yf_t, start=s_yf, end=e_yf,
                                          progress=False, auto_adjust=False, timeout=8)
                        if tmp is not None and len(tmp) >= 60:
                            flat = []
                            for c in tmp.columns:
                                if isinstance(c, tuple):
                                    ct = str(c[1]).strip() if len(c)>1 else ""
                                    if ct and ct != yf_t: continue
                                    flat.append(str(c[0]).strip().lower())
                                else:
                                    flat.append(str(c).strip().lower())
                            if len(flat)==len(tmp.columns):
                                tmp.columns = flat
                            df = tmp.sort_index(ascending=True)
                    except Exception: pass
                    if df is None:
                        try:
                            raw = fdr.DataReader(ticker, start_str, end_str)
                            df  = raw.sort_index(ascending=True) if raw is not None else None
                        except Exception: pass
                    if df is None or len(df) < 60: continue

                    cm = {}
                    for c in df.columns:
                        cl = str(c).strip().lower()
                        if cl=="open": cm[c]="open"
                        elif cl=="high": cm[c]="high"
                        elif cl=="low": cm[c]="low"
                        elif cl == "close": cm[c]="close"
                        # adj close 제외 — 실제 종가(close) 사용
                        elif cl=="volume": cm[c]="volume"
                    df = df.rename(columns=cm)
                    for col in ["open","high","low","close","volume"]:
                        if col in df.columns:
                            df[col] = pd.to_numeric(df[col], errors="coerce")
                    df = df.dropna(subset=["close"])
                    if len(df) < 60: continue

                    # 현재가 — 네이버 크롤링 우선 (get_price 내부에 포함)
                    cur_p = float(get_price(ticker))
                    if cur_p <= 0:
                        cur_p = float(df["close"].iloc[-1])  # df fallback

                    # 거래대금 황금 필터 (200억)
                    last_vol   = float(df["volume"].iloc[-1]) if "volume" in df.columns else 0
                    tval_bil   = cur_p * last_vol / 1e8
                    if tval_bil < min_vol_bil: continue

                    # RSI 황금 필터 (50 이상)
                    try:
                        rsi_val = float(ta.momentum.RSIIndicator(df["close"],14).rsi().iloc[-1])
                        if pd.isna(rsi_val) or not(rsi_min <= rsi_val <= rsi_max): continue
                    except Exception:
                        rsi_val = 0.0

                    # 이격도 필터
                    if "close" in df.columns and len(df)>=20:
                        ma20 = df["close"].rolling(20).mean().iloc[-1]
                        disp = cur_p/ma20 if ma20 else 1
                        if disp>1.10 or disp<0.90: continue
                    else:
                        disp = 1.0

                    # ATR 기반 타점
                    atr_val = 0.0
                    try:
                        atr_val = float(ta.volatility.AverageTrueRange(
                            df["high"],df["low"],df["close"],14).average_true_range().iloc[-1])
                    except Exception: pass
                    if atr_val<=0: atr_val = cur_p*0.02

                    high20  = float(df["high"].iloc[-20:].max()) if "high" in df.columns else cur_p*1.10
                    target  = high20 if high20>cur_p else cur_p*1.10
                    ma5     = df["close"].rolling(5).mean().iloc[-2] if len(df)>1 else cur_p
                    entry   = float(ma5)*0.975 if not pd.isna(ma5) else cur_p
                    stoploss= cur_p - atr_val*atr_s
                    rr      = (target-entry)/(entry-stoploss) if entry>stoploss else 0
                    if rr < 0.8: continue

                    # 딕셔너리에 실제 현재가 저장 (1:1 key 매핑)
                    price_dict[str(ticker).zfill(6)] = cur_p

                    results.append({
                        "종목코드":        ticker,       # 6자리 문자열 보장
                        "종목명":          t["name"],
                        "시장":            t["market"],
                        "수급점수":        score,
                        "수급태그":        tag,
                        "기관보유(%)":     round(inst_pct,1),
                        "외국인추정(%)":   round(foreign,1),
                        "거래량비율":      vol_ratio,
                        "현재가":          int(cur_p),
                        "RSI":             round(rsi_val,1),
                        "이격도(%)":       round(disp*100,2),
                        "ATR(%)":          round(atr_val/cur_p*100,2),
                        "손익비":          round(rr,2),
                        "매수타점":        int(entry),
                        "목표가":          int(target),
                        "손절가(ATR)":     int(stoploss),
                    })
                except Exception: continue

            prog.progress(100, text="✅ 완료!")
            if results:
                df_out = (pd.DataFrame(results)
                          .sort_values("수급점수", ascending=False)
                          .reset_index(drop=True))
                # 종목코드 타입 최종 보장
                df_out["종목코드"] = df_out["종목코드"].astype(str).str.zfill(6)

                # ── 스캔 완료 후 현재가 정밀 재조회 (네이버 기반) ──
                # price_dict에 이미 get_price 결과 저장됨 → 재매핑
                def _safe_price(code):
                    p = price_dict.get(str(code).zfill(6), 0)
                    return int(p) if p > 0 else 0
                df_out["현재가"] = df_out["종목코드"].map(_safe_price)
                # 0인 경우만 기존 값 유지
                for idx in df_out[df_out["현재가"]==0].index:
                    pass  # 0이면 스캔 시 이미 제외됨

                df_out.index += 1
                st.session_state["ssw_records"]       = df_out.to_dict("records")
                st.session_state["swing_results"]     = df_out[["종목코드","종목명"]].to_dict("records")
                st.session_state["swing_results_full"]= df_out.to_dict("records")
                st.session_state["supply_records"]    = df_out.to_dict("records")
                double = sum(1 for r in df_out.to_dict("records") if r.get("수급태그")=="🔥쌍끌이")
                st.success(f"✅ {len(df_out)}개 | 🔥쌍끌이 {double}개 | RSI≥{rsi_min} | 거래대금≥{min_vol_bil}억 | 수급≥{min_score}점")
            else:
                st.info("📭 조건 부합 종목 없음 — 필터 조건을 완화해 보세요.")

        # ── 결과 렌더링 (data_editor 1개만) ─────────────────
        records = st.session_state.get("ssw_records", [])
        if not records:
            st.info("👆 스캔 버튼을 눌러주세요.")
            return

        df_show = pd.DataFrame(records)
        # 종목코드 타입 통일
        df_show["종목코드"] = df_show["종목코드"].astype(str).str.zfill(6)

        st.markdown(f"### 📊 발굴 종목 {len(records)}개")
        st.caption("수급 점수 내림차순 | 수급 없는 종목 자동제외 | ATR 손절×2.0 / 익절×3.0")

        # 전체 추가
        fa, fb = st.columns([4,1])
        with fa: st.caption(f"황금 필터 적용 결과")
        with fb:
            if st.button("🔥 전체 추가", key="ssw_all", type="primary"):
                added, today = 0, datetime.now().strftime("%Y-%m-%d")
                for r in records:
                    ticker = str(r["종목코드"]).zfill(6)
                    cur_p  = float(r["현재가"])
                    try:
                        ai = calc_atr_targets(ticker, atr_mult_stop=2.0, atr_mult_target=3.0)
                        sl = int(ai["stoploss"]) if ai else int(cur_p*0.93)
                        tg = int(ai["target"])   if ai else int(cur_p*1.09)
                    except Exception:
                        sl, tg = int(cur_p*0.93), int(cur_p*1.09)
                    rv = add_to_watchlist(username=username, ticker=ticker,
                        name=r["종목명"], source="수급스윙",
                        entry=int(r.get("매수타점",cur_p)), target=tg, stoploss=sl,
                        rsi=float(r.get("RSI",0)), rr_ratio=float(r.get("손익비",0)),
                        market=r.get("시장",""), scan_date=today, base_price=cur_p)
                    if rv in("added","updated"): added+=1
                st.success(f"✅ {added}개! (ATR 손절×2.0 / 익절×3.0)")
                if added>0: st.balloons()

        # ── data_editor 단일 출력 ─────────────────────────────
        disp = ["종목코드","종목명","시장","수급점수","수급태그","기관보유(%)",
                "외국인추정(%)","거래량비율","현재가","RSI","이격도(%)",
                "ATR(%)","손익비","매수타점","목표가","손절가(ATR)"]
        df_ed = df_show[[c for c in disp if c in df_show.columns]].copy()
        df_ed.insert(0, "선택", False)
        edited = st.data_editor(
            df_ed,
            column_config={"선택": st.column_config.CheckboxColumn("선택", default=False)},
            disabled=[c for c in df_ed.columns if c != "선택"],
            use_container_width=True, hide_index=True, key="ssw_editor",
        )
        sel = edited[edited["선택"]==True]
        st.caption(f"{len(sel)}개 선택")

        if st.button(f"➕ 선택 {len(sel)}개 추가", disabled=len(sel)==0,
                     type="primary", key="ssw_sel"):
            added, today = 0, datetime.now().strftime("%Y-%m-%d")
            for _, row in sel.iterrows():
                ticker  = str(row["종목코드"]).zfill(6)
                matched = next((r for r in records
                                if str(r["종목코드"]).zfill(6)==ticker), None)
                if not matched: continue
                cur_p = float(matched["현재가"])
                try:
                    ai = calc_atr_targets(ticker, atr_mult_stop=2.0, atr_mult_target=3.0)
                    sl = int(ai["stoploss"]) if ai else int(cur_p*0.93)
                    tg = int(ai["target"])   if ai else int(cur_p*1.09)
                except Exception:
                    sl, tg = int(cur_p*0.93), int(cur_p*1.09)
                rv = add_to_watchlist(username=username, ticker=ticker,
                    name=matched["종목명"], source="수급스윙",
                    entry=int(matched.get("매수타점",cur_p)), target=tg, stoploss=sl,
                    rsi=float(matched.get("RSI",0)), rr_ratio=float(matched.get("손익비",0)),
                    market=matched.get("시장",""), scan_date=today, base_price=cur_p)
                if rv in("added","updated"): added+=1
            st.success(f"✅ {added}개! (ATR 손절×2.0 / 익절×3.0)")

    except Exception as e:
        st.error(f"수급스윙 스캐너 오류: {e}")
        import traceback; st.code(traceback.format_exc())


def page_super_signal(username: str):
    st.markdown("## 🚀 슈퍼 시그널")
    st.markdown(
        '<div class="card card-warn" style="margin-bottom:1rem;">'
        '<div style="color:#fbbf24;font-weight:700;">⚡ 슈퍼 시그널이란?</div>'
        '<div style="color:#94a3b8;font-size:0.83rem;margin-top:0.3rem;line-height:1.7;">'
        '퀀트 스캐너 + 스윙 스캐너 <b style="color:#e2e8f0">두 시스템이 동시에 추천한 종목</b>만 표시합니다.<br>'
        '두 전략이 모두 선택 → <b style="color:#fbbf24">최우선 매수 후보</b>'
        '</div></div>', unsafe_allow_html=True)

    quant_list = st.session_state.get("quant_results", [])
    swing_list = st.session_state.get("swing_results", [])

    c1, c2, c3 = st.columns(3)
    with c1:
        q_ok = f"✅ {len(quant_list)}개" if quant_list else "❌ 미실행"
        q_col = "#34d399" if quant_list else "#f87171"
        st.markdown(
            f'<div class="card" style="text-align:center;">'
            f'<div class="label">🧮 퀀트 스캐너</div>'
            f'<b style="color:{q_col}">{q_ok}</b></div>',
            unsafe_allow_html=True)
    with c2:
        s_ok = f"✅ {len(swing_list)}개" if swing_list else "❌ 미실행"
        s_col = "#34d399" if swing_list else "#f87171"
        st.markdown(
            f'<div class="card" style="text-align:center;">'
            f'<div class="label">📈 스윙 스캐너</div>'
            f'<b style="color:{s_col}">{s_ok}</b></div>',
            unsafe_allow_html=True)
    with c3:
        _sup_n   = len(supply_list) if supply_list else 0
        _sup_60  = len(supply_codes) if supply_codes else 0
        sup_ok   = f"✅ {_sup_n}개 (60점↑: {_sup_60}개)" if _sup_n>0 else "❌ 미실행"
        sup_col  = "#34d399" if _sup_n>0 else "#f87171"
        st.markdown(
            f'<div class="card" style="text-align:center;">'
            f'<div class="label">📡 수급 스캐너</div>'
            f'<b style="color:{sup_col};font-size:0.85rem;">{sup_ok}</b></div>',
            unsafe_allow_html=True)

    if not quant_list or not swing_list:
        st.warning("⚠️ 퀀트 스캐너와 스윙 스캐너를 **모두** 먼저 실행해 주세요!")
        return

    # 수급 스캐너 데이터 안전하게 로드
    supply_list  = st.session_state.get("supply_records") or []
    supply_codes = {}
    for r in supply_list:
        try:
            code  = str(r.get("종목코드","")).zfill(6)
            score = float(r.get("수급점수", 0))
            if score >= 60:
                supply_codes[code] = score
        except Exception:
            pass

    # 공통 종목 탐색
    quant_codes = {str(q.get("종목코드","")).zfill(6): q.get("종목명","") for q in quant_list}
    swing_codes = {str(s.get("종목코드","")).zfill(6): s.get("종목명","") for s in swing_list}
    common      = set(quant_codes.keys()) & set(swing_codes.keys())

    # 수급 60점↑ 종목 별도 표시
    supply_bonus = common & set(supply_codes.keys())

    st.markdown("---")

    if not common:
        st.markdown(
            '<div class="card" style="text-align:center;padding:2rem;">'
            '<div style="font-size:2rem;">🔍</div>'
            '<div style="color:#94a3b8;margin-top:0.5rem;">'
            '현재 두 스캐너에 공통 종목이 없습니다.<br>'
            '<span style="font-size:0.83rem;">조건을 조정하거나 다음 거래일에 확인해 보세요.</span>'
            '</div></div>', unsafe_allow_html=True)
        return

    st.balloons()
    st.markdown(
        f'<div style="text-align:center;margin:0.8rem 0;">'
        f'<div style="font-size:2rem;">🎯</div>'
        f'<div style="font-size:1.3rem;font-weight:900;color:#fbbf24;">'
        f'슈퍼 시그널 {len(common)}개 발견!</div>'
        f'<div style="color:#94a3b8;font-size:0.85rem;">두 시스템이 동시에 선택한 최우선 후보</div>'
        f'</div>', unsafe_allow_html=True)

    swing_full = {str(r.get("종목코드","")).zfill(6): r
                  for r in st.session_state.get("swing_results_full", [])}
    skipped = []

    for code in common:
        name = quant_codes[code]

        # ── 현재가 조회 ──────────────────────────────────────
        try:
            cur = float(get_price(code) or 0)
        except Exception:
            cur = 0

        # ── 스윙 상세 데이터 (ATR 손절/저항 익절) ────────────
        sw = swing_full.get(code, {})
        entry    = sw.get("매수타점", cur)
        target   = sw.get("목표가(저항)", sw.get("목표가(+20%)", int(cur*1.12)))
        stoploss = sw.get("손절가(ATR)", sw.get("손절가(-7%)", int(cur*0.93)))
        rsi      = sw.get("RSI", "-")
        rr       = sw.get("손익비", "-")
        atr_pct  = sw.get("ATR(%)", "-")

        # ── 기술지표 재계산 (데이터 유효성 검사 포함) ─────────
        extra_info = {}
        try:
            import FinanceDataReader as fdr
            import ta
            end   = datetime.now().strftime("%Y%m%d")
            start = (datetime.now()-timedelta(days=200)).strftime("%Y%m%d")

            df = None
            # Yahoo Finance 우선
            try:
                import yfinance as yf
                suffix = ".KS"  # 기본 KOSPI
                s_yf = start[:4]+"-"+start[4:6]+"-"+start[6:]
                e_yf = end[:4]+"-"+end[4:6]+"-"+end[6:]
                yf_df = yf.download(code+suffix, start=s_yf, end=e_yf,
                                    progress=False, auto_adjust=False, timeout=8)
                if yf_df is not None and len(yf_df) >= 60:
                    yf_df.columns = [c.lower() if isinstance(c,str) else c[0].lower()
                                     for c in yf_df.columns]
                    df = yf_df
                if df is None or len(df) < 60:
                    # KOSDAQ 시도
                    yf_df2 = yf.download(code+".KQ", start=s_yf, end=e_yf,
                                         progress=False, auto_adjust=False, timeout=8)
                    if yf_df2 is not None and len(yf_df2) >= 60:
                        yf_df2.columns = [c.lower() if isinstance(c,str) else c[0].lower()
                                          for c in yf_df2.columns]
                        df = yf_df2
            except Exception:
                pass

            if df is None or len(df) < 60:
                df = fdr.DataReader(code, start, end)

            # 데이터 유효성 검사
            if df is None or df.empty or len(df) < 60:
                skipped.append(f"{name}({code}): 데이터 부족")
                continue

            # 컬럼 정규화
            col_map = {}
            for c in df.columns:
                cl = c.strip().lower()
                if cl=="open":   col_map[c]="open"
                elif cl=="high": col_map[c]="high"
                elif cl=="low":  col_map[c]="low"
                elif cl in("close","adj close"): col_map[c]="close"
                elif cl=="volume": col_map[c]="volume"
            df = df.rename(columns=col_map)
            for col in ["open","high","low","close","volume"]:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce")
            df = df.dropna(subset=["close"])

            if len(df) < 60:
                skipped.append(f"{name}({code}): 유효 데이터 부족")
                continue

            # NaN/inf 처리 후 지표 계산
            df["ma20"]  = df["close"].rolling(20).mean()
            df["ma60"]  = df["close"].rolling(60).mean()
            df["rsi_v"] = ta.momentum.RSIIndicator(df["close"], window=14).rsi()

            # ATR 계산 (NaN 방지)
            if all(c in df.columns for c in ["high","low","close"]):
                atr_ind = ta.volatility.AverageTrueRange(
                    df["high"], df["low"], df["close"], window=14)
                df["atr"] = atr_ind.average_true_range()
            else:
                df["atr"] = float("nan")

            # NaN → 0 치환
            df = df.fillna(0).replace([float("inf"), float("-inf")], 0)

            row = df.iloc[-1]
            extra_info = {
                "ma20":   float(row.get("ma20",0)),
                "ma60":   float(row.get("ma60",0)),
                "rsi_v":  float(row.get("rsi_v",0)),
                "atr_v":  float(row.get("atr",0)),
                "disp":   float(row["close"]/row["ma20"]*100) if row.get("ma20",0)>0 else 0,
                "high20": float(df["high"].iloc[-20:].max()) if "high" in df.columns else 0,
            }
            # 재계산된 값으로 업데이트
            if extra_info["atr_v"] > 0 and cur > 0:
                stoploss = int(cur - extra_info["atr_v"]*2)
            if extra_info["high20"] > cur:
                target = int(extra_info["high20"])
            rsi = round(extra_info["rsi_v"], 1)

        except Exception as err:
            skipped.append(f"{name}({code}): {type(err).__name__}")
            # 에러여도 기본 정보로 카드는 표시

        # ── 카드 렌더링 ───────────────────────────────────────
        if cur == 0: cur = entry
        diff_pct = (cur-entry)/entry*100 if entry else 0
        dc = "#34d399" if diff_pct<=0 else ("#fbbf24" if diff_pct<=5 else "#94a3b8")
        disp_txt = f"{extra_info.get('disp',0):.1f}%" if extra_info else "-"

        st.markdown(
            f'<div style="background:linear-gradient(135deg,#1e2535,#16213e);'
            f'border:2px solid #fbbf24;border-radius:16px;padding:1.2rem;'
            f'margin:0.6rem 0;box-shadow:0 0 24px rgba(251,191,36,0.2);">'

            # 헤더
            f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.8rem;">'
            f'<div>'
            f'<span style="font-size:1.1rem;font-weight:900;">{name}</span>'
            f'<span style="color:#94a3b8;font-size:0.75rem;margin-left:0.4rem;">{code}</span>'
            f'<span style="background:#fbbf2422;color:#fbbf24;border-radius:6px;'
            f'padding:2px 10px;font-size:0.75rem;margin-left:0.4rem;font-weight:700;">⚡ 슈퍼 시그널</span>'
            f'{"<span style=\'background:#f8717122;color:#f87171;border-radius:6px;padding:2px 10px;font-size:0.75rem;margin-left:0.3rem;font-weight:700;\'>🔥수급"+str(supply_codes.get(code,0))+"점</span>" if code in supply_codes else ""}'  
            f'</div>'
            f'<div style="font-family:JetBrains Mono,monospace;font-size:1.05rem;'
            f'font-weight:700;color:#38bdf8;">{cur:,.0f}원</div>'
            f'</div>'

            # 핵심 지표 3×2
            f'<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:0.5rem;font-size:0.82rem;">'
            f'<div style="background:#12172a;border-radius:8px;padding:0.5rem;text-align:center;">'
            f'<div style="color:#94a3b8;font-size:0.68rem;">💰 매수타점</div>'
            f'<b style="color:#fbbf24;font-family:JetBrains Mono,monospace;">{entry:,.0f}원</b></div>'
            f'<div style="background:#12172a;border-radius:8px;padding:0.5rem;text-align:center;">'
            f'<div style="color:#94a3b8;font-size:0.68rem;">🎯 목표(저항)</div>'
            f'<b style="color:#34d399;font-family:JetBrains Mono,monospace;">{target:,.0f}원</b></div>'
            f'<div style="background:#12172a;border-radius:8px;padding:0.5rem;text-align:center;">'
            f'<div style="color:#94a3b8;font-size:0.68rem;">🛑 손절(ATR×2)</div>'
            f'<b style="color:#f87171;font-family:JetBrains Mono,monospace;">{stoploss:,.0f}원</b></div>'
            f'<div style="background:#12172a;border-radius:8px;padding:0.5rem;text-align:center;">'
            f'<div style="color:#94a3b8;font-size:0.68rem;">📊 RSI</div>'
            f'<b style="color:#e2e8f0;">{rsi}</b></div>'
            f'<div style="background:#12172a;border-radius:8px;padding:0.5rem;text-align:center;">'
            f'<div style="color:#94a3b8;font-size:0.68rem;">📐 이격도</div>'
            f'<b style="color:#e2e8f0;">{disp_txt}</b></div>'
            f'<div style="background:#12172a;border-radius:8px;padding:0.5rem;text-align:center;">'
            f'<div style="color:#94a3b8;font-size:0.68rem;">⚖️ 타점까지</div>'
            f'<b style="color:{dc};">{diff_pct:+.1f}%</b></div>'
            f'</div>'

            # 안내
            f'<div style="margin-top:0.8rem;padding:0.5rem;background:#fbbf2411;'
            f'border-radius:8px;font-size:0.78rem;color:#fbbf24;">'
            f'💡 퀀트(모멘텀) + 스윙(기술적) 동시 추천 — 최우선 매수 검토</div>'
            f'</div>', unsafe_allow_html=True)

        # 관심종목 추가 버튼
        if st.button(f"🔖 {name} 관심종목 등록", key=f"super_{code}"):
            rv = add_to_watchlist(username=username, ticker=code, name=name,
                source="슈퍼시그널", entry=int(entry), target=int(target),
                stoploss=int(stoploss), rsi=rsi, rr_ratio=rr,
                scan_date=datetime.now().strftime("%Y-%m-%d"), base_price=float(cur))
            st.success(f"✅ {name} {'추가' if rv=='added' else '업데이트'} 완료!")

    # 스킵된 종목 안내
    if skipped:
        with st.expander(f"ℹ️ 분석 제외 종목 ({len(skipped)}개)", expanded=False):
            for s_msg in skipped:
                st.caption(f"• 데이터 부족으로 {s_msg} 분석 제외")


def page_vault(username: str):
    st.markdown("## 🗄️ 관심종목")

    wl = load_watchlist(username) or []
    if not wl:
        st.info("관심종목이 없습니다. 퀀트/스윙 스캐너에서 종목을 추가하세요.")
        return

    active_cnt = sum(1 for w in wl if w.get("is_active", w.get("morning_check", False)))

    # 상단 요약 + 소형 버튼
    sc1, sc2, sc3 = st.columns([4, 1, 1])
    with sc1:
        st.markdown(
            f'<div style="color:#94a3b8;font-size:0.85rem;padding:0.35rem 0;">'
            f'총 <b style="color:#e2e8f0">{len(wl)}개</b> &nbsp;|&nbsp; '
            f'모닝체크 감시 <b style="color:#38bdf8">{active_cnt}개</b></div>',
            unsafe_allow_html=True)
    with sc2:
        if st.button("전체 ON", key="vault_all_on", use_container_width=True):
            for w in wl: w["is_active"]=True; w["morning_check"]=True
            save_watchlist(username, wl); st.rerun()
    with sc3:
        if st.button("전체 OFF", key="vault_all_off", use_container_width=True):
            for w in wl: w["is_active"]=False; w["morning_check"]=False
            save_watchlist(username, wl); st.rerun()

    st.markdown("---")
    src_colors = {"스윙":"#34d399","퀀트":"#fbbf24","수동":"#a78bfa"}
    wl_changed = False

    for idx_w, w in enumerate(wl):
        is_act  = bool(w.get("is_active", w.get("morning_check", False)))
        src_col = src_colors.get(w.get("source","기타"), "#94a3b8")
        cur     = float(get_price(str(w.get("ticker","")).zfill(6)) or w.get("base_price", w.get("entry",0)))
        base    = float(w.get("base_price", w.get("entry", cur)))
        ret_pct = round((cur-base)/base*100, 2) if base else 0.0
        ret_col = "#38bdf8" if ret_pct >= 0 else "#f87171"
        ret_sgn = "+" if ret_pct >= 0 else ""
        tid     = w["ticker"]  # 고유 키용

        # 체크박스 + 카드 + 삭제 버튼
        col_chk, col_card, col_del = st.columns([0.5, 8.5, 1])

        with col_chk:
            # 고유 key: ticker 사용
            new_act = st.checkbox(
                "", value=is_act,
                key=f"chk_{tid}_{idx_w}",
                label_visibility="collapsed",
                help="체크 시 모닝체크 실시간 감시"
            )
            if new_act != is_act:
                for item in wl:
                    if str(item.get("ticker","")).zfill(6) == str(tid).zfill(6):
                        item["is_active"]     = new_act
                        item["morning_check"] = new_act
                wl_changed = True

        with col_card:
            badge = ('<span style="background:#38bdf822;color:#38bdf8;border-radius:4px;'
                     'padding:1px 6px;font-size:0.67rem;margin-left:0.3rem;">🔴 감시중</span>'
                     if is_act else "")
            st.markdown(
                f'<div class="card" style="border-left:4px solid {src_col};'
                f'padding:0.6rem 0.9rem;margin:0;">'
                f'<div style="display:flex;justify-content:space-between;align-items:center;">'
                f'<div style="min-width:0;flex:1;">'
                f'<b style="font-size:0.93rem;">{w["name"]}</b>'
                f'<span style="color:#94a3b8;font-size:0.7rem;margin-left:0.3rem;">{tid}</span>'
                f'<span style="background:{src_col}22;color:{src_col};border-radius:4px;'
                f'padding:1px 5px;font-size:0.67rem;margin-left:0.25rem;">{w.get("source","기타")}</span>'
                f'{badge}'
                f'</div>'
                f'<div style="text-align:right;flex-shrink:0;margin-left:0.5rem;">'
                f'<div class="mono" style="color:{ret_col};font-weight:700;font-size:0.9rem;">'
                f'{ret_sgn}{ret_pct:.2f}%</div>'
                f'<div style="color:{ret_col};font-size:0.68rem;">'
                f'{base:,.0f}→{cur:,.0f}원</div>'
                f'</div></div>'
                f'<div style="display:grid;grid-template-columns:1fr 1fr;'
                f'gap:0.2rem;margin-top:0.35rem;font-size:0.72rem;">'
                f'<div><div class="label">타점</div>'
                f'<b class="mono gold-color">{int(w.get("entry",0)):,}원</b></div>'
                f'<div><div class="label">목표가</div>'
                f'<b class="mono green-color">{int(w.get("target",0)):,}원</b></div>'
                f'<div><div class="label">손절가</div>'
                f'<b class="mono loss-color">{int(w.get("stoploss",0)):,}원</b></div>'
                f'<div><div class="label">등록일</div>'
                f'<span style="color:#94a3b8">{w.get("reg_date",w.get("add_date",""))}</span></div>'
                f'</div></div>',
                unsafe_allow_html=True)

        with col_del:
            st.markdown("<div style='margin-top:0.3rem'></div>", unsafe_allow_html=True)
            if st.button("🗑️", key=f"del_{tid}_{idx_w}", use_container_width=True):
                save_watchlist(username, [x for x in wl if x["ticker"] != tid])
                st.rerun()

    # 체크박스 변경 저장
    if wl_changed:
        save_watchlist(username, wl)
        st.rerun()

    # 수익률 요약 테이블
    st.markdown("---")
    pos = sum(1 for w in wl if float(get_price(w["ticker"]) or w.get("base_price",0)) >= float(w.get("base_price", w.get("entry",1))))
    neg = len(wl) - pos
    st.caption(f"수익 {pos}개 | 손실 {neg}개")


@st.fragment
def _morning_realtime(watchlist: list, username: str):
    """fragment: 새로고침 버튼 클릭 시에만 이 블록만 재실행 (전체 깜빡임 없음)"""
    col_r, col_i = st.columns([1, 3])
    with col_r:
        if st.button("🔄 새로고침", use_container_width=True, key="morning_refresh"):
            st.cache_data.clear()
    with col_i:
        st.markdown(
            f'<div style="color:#8892a4;font-size:0.85rem;padding:0.5rem 0;">'
            f'감시 <b style="color:white">{len(watchlist)}개</b> | {datetime.now().strftime("%Y-%m-%d %H:%M")}'
            f'</div>', unsafe_allow_html=True)

    # 데이터 수집 (중복 실행 방지 + placeholder)
    if st.session_state.get("morning_loading", False):
        st.info("데이터를 불러오는 중입니다... 잠시만 기다려 주세요.")
        return
    placeholder = st.empty()
    rows = []
    st.session_state["morning_loading"] = True
    with placeholder.container():
        with st.spinner("현재가 조회 중..."):
            for w in watchlist:
                entry    = float(w.get("entry", 0))
                target   = float(w.get("target", entry * 1.20))
                stoploss = float(w.get("stoploss", entry * 0.93))
                source   = w.get("source", "기타")
                cur      = float(get_price(str(w.get("ticker","")).zfill(6)) or entry)
                df_h     = get_ohlcv_cached(w["ticker"], days=5)
                low_t    = float(df_h["low"].iloc[-1])   if df_h is not None and len(df_h) > 0 else cur
                open_t   = float(df_h["open"].iloc[-1])  if df_h is not None and len(df_h) > 0 else cur
                prev_c   = float(df_h["close"].iloc[-2]) if df_h is not None and len(df_h) > 1 else cur
                diff_pct = (cur - entry) / entry * 100 if entry else 0
                chg_pct  = (cur - prev_c) / prev_c * 100 if prev_c else 0
                gap_pct  = (open_t - prev_c) / prev_c * 100 if prev_c else 0

                if low_t <= entry:    status, pri, sc = "✅ 타점 도달", 0, "#00d4aa"
                elif diff_pct <= 3:   status, pri, sc = "🔔 근접",     1, "#ffd766"
                elif gap_pct > 5:     status, pri, sc = "⚠️ 갭상승",   3, "#ff4b6e"
                else:                 status, pri, sc = "⏳ 대기",     2, "#8892a4"

                rows.append({
                    "pri": pri, "status": status, "sc": sc,
                    "name": w["name"], "ticker": w["ticker"], "source": source,
                    "entry": entry, "target": target, "stoploss": stoploss,
                    "cur": cur, "diff_pct": diff_pct, "chg_pct": chg_pct,
                })
    placeholder.empty()  # 스피너 제거
    st.session_state["morning_loading"] = False
    rows.sort(key=lambda x: x["pri"])

    # 상태 요약 배지
    cnt = {0:0, 1:0, 2:0, 3:0}
    for r in rows: cnt[r["pri"]] += 1
    # 모바일: 2열 2행 배치
    badge_data = [
        ("✅ 타점도달", cnt[0], "#00d4aa"),
        ("🔔 근접",    cnt[1], "#fbbf24"),
        ("⏳ 대기",    cnt[2], "#94a3b8"),
        ("⚠️ 갭상승",  cnt[3], "#f87171"),
    ]
    r1c1, r1c2 = st.columns(2)
    r2c1, r2c2 = st.columns(2)
    for col, (label, n, color) in zip([r1c1, r1c2, r2c1, r2c2], badge_data):
        col.markdown(
            f'<div style="background:{color}18;border:1px solid {color};'
            f'border-radius:12px;padding:0.8rem 0.5rem;text-align:center;margin:0.15rem 0;">'
            f'<div style="color:{color};font-size:0.8rem;font-weight:600;">{label}</div>'
            f'<div style="color:{color};font-family:JetBrains Mono,monospace;'
            f'font-size:2rem;font-weight:900;line-height:1.2;">{n}</div>'
            f'</div>', unsafe_allow_html=True)

    st.markdown("<div style='margin:0.8rem 0'></div>", unsafe_allow_html=True)

    # 텔레그램 전송
    if st.button("📨 텔레그램 전송", key="morning_tg"):
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        msg = f"<b>🌅 모닝 체크 ({now_str})</b>\n감시 {len(rows)}개 종목\n\n"
        for r in rows:
            sgn      = "+" if r["chg_pct"] >= 0 else ""
            src_icon = "🎯" if r["source"] == "스윙" else "📊"
            msg += (
                f"{src_icon} [{r['source']}] <b>{r['name']}</b> | {r['status']}\n"
                f"타점: {r['entry']:,.0f} / 목표: {r['target']:,.0f} / "
                f"손절: {r['stoploss']:,.0f} / 현재: {r['cur']:,.0f} "
                f"({sgn}{r['chg_pct']:.1f}%)\n\n"
            )
        send_telegram(msg)
        st.success("✅ 텔레그램 전송 완료!")

    # 종목 카드
    src_colors = {"스윙": "#00d4aa", "퀀트": "#ffd766"}
    for r in rows:
        bc    = r["sc"]
        cc    = "#4e9eff" if r["chg_pct"] >= 0 else "#ff4b6e"
        sgn   = "+" if r["chg_pct"] >= 0 else ""
        dc    = "#00d4aa" if r["diff_pct"] <= 0 else ("#ffd766" if r["diff_pct"] <= 3 else "#8892a4")
        sc    = src_colors.get(r["source"], "#8892a4")
        blink = "animation:pulse 1.2s ease-in-out infinite;" if r["pri"] == 0 else ""
        tgt_pct = (r["target"] - r["entry"]) / r["entry"] * 100 if r["entry"] else 0
        stp_pct = (r["stoploss"] - r["entry"]) / r["entry"] * 100 if r["entry"] else 0

        st.markdown(
            f'<div style="background:#1a1f2e;border:2px solid {bc};border-radius:14px;'
            f'padding:1rem 1.2rem;margin:0.4rem 0;{blink}">'
            f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.8rem;">'
            f'<div>'
            f'<span style="font-size:1.05rem;font-weight:700;">{r["name"]}</span>'
            f'<span style="color:#8892a4;font-size:0.75rem;margin-left:0.4rem;">{r["ticker"]}</span>'
            f'<span style="background:{sc}22;color:{sc};border-radius:5px;'
            f'padding:1px 7px;font-size:0.7rem;margin-left:0.4rem;">{r["source"]}</span>'
            f'</div>'
            f'<span style="background:{bc}22;color:{bc};border-radius:8px;'
            f'padding:4px 14px;font-size:0.95rem;font-weight:700;">{r["status"]}</span>'
            f'</div>'
            f'<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:0.4rem;margin-top:0.1rem;">'
            f'<div style="background:#12172a;border-radius:10px;padding:0.6rem 0.4rem;text-align:center;">'
            f'<div style="color:#94a3b8;font-size:0.67rem;margin-bottom:0.1rem;">💰 매수타점</div>'
            f'<div style="color:#fbbf24;font-family:JetBrains Mono,monospace;font-size:0.88rem;font-weight:700;">{r["entry"]:,.0f}</div>'
            f'</div>'
            f'<div style="background:#12172a;border-radius:10px;padding:0.6rem 0.4rem;text-align:center;">'
            f'<div style="color:#94a3b8;font-size:0.67rem;margin-bottom:0.1rem;">📊 현재가</div>'
            f'<div style="color:{cc};font-family:JetBrains Mono,monospace;font-size:0.88rem;font-weight:700;">{r["cur"]:,.0f}</div>'
            f'<div style="color:{cc};font-size:0.62rem;">{sgn}{r["chg_pct"]:.2f}%</div>'
            f'</div>'
            f'<div style="background:{bc}18;border-radius:10px;padding:0.6rem 0.4rem;text-align:center;">'
            f'<div style="color:#94a3b8;font-size:0.67rem;margin-bottom:0.1rem;">🚦 상태</div>'
            f'<div style="color:{bc};font-size:0.85rem;font-weight:700;">{r["status"]}</div>'
            f'</div>'
            f'<div style="background:#12172a;border-radius:10px;padding:0.6rem 0.4rem;text-align:center;">'
            f'<div style="color:#94a3b8;font-size:0.67rem;margin-bottom:0.1rem;">🎯 목표가</div>'
            f'<div style="color:#34d399;font-family:JetBrains Mono,monospace;font-size:0.88rem;font-weight:700;">{r["target"]:,.0f}</div>'
            f'<div style="color:#34d399;font-size:0.62rem;">+{tgt_pct:.1f}%</div>'
            f'</div>'
            f'<div style="background:#12172a;border-radius:10px;padding:0.6rem 0.4rem;text-align:center;">'
            f'<div style="color:#94a3b8;font-size:0.67rem;margin-bottom:0.1rem;">🛑 손절가</div>'
            f'<div style="color:#f87171;font-family:JetBrains Mono,monospace;font-size:0.88rem;font-weight:700;">{r["stoploss"]:,.0f}</div>'
            f'<div style="color:#f87171;font-size:0.62rem;">{stp_pct:.1f}%</div>'
            f'</div>'
            f'<div style="background:#12172a;border-radius:10px;padding:0.6rem 0.4rem;text-align:center;">'
            f'<div style="color:#94a3b8;font-size:0.67rem;margin-bottom:0.1rem;">📍 타점까지</div>'
            f'<div style="color:{dc};font-family:JetBrains Mono,monospace;font-size:0.88rem;font-weight:700;">{r["diff_pct"]:+.2f}%</div>'
            f'</div>'
            f'</div></div>',
            unsafe_allow_html=True)

    st.markdown("---")
    st.caption("💡 종목 관리는 [🗄️ 관심종목] 탭의 [🌅 모닝체크] 열에서 하세요.")


def page_morning(username: str):
    st.markdown("## 🌅 모닝 체크")
    all_wl    = load_watchlist(username) or []
    watchlist = [w for w in all_wl
                 if w and w.get("is_active", w.get("morning_check", False))]
    if not watchlist:
        st.warning("감시 중인 종목이 없습니다.")
        st.info("👉 [🗄️ 관심종목] 탭에서 [🌅 모닝체크] 열을 체크해 주세요.")
        return
    # fragment 함수 호출 — 새로고침 클릭 시 이 블록만 재실행
    _morning_realtime(watchlist, username)


# ════════════════════════════════════════════════════════════
#  메인
# ════════════════════════════════════════════════════════════


def main():
    import traceback as _tb

    if "app_initialized" not in st.session_state:
        try: _init_data_dir()
        except Exception: pass
        st.session_state["app_initialized"] = True

    if not st.session_state.get("user"):
        try: show_login()
        except Exception as e: st.error(f"로그인 오류: {e}")
        return

    username = st.session_state["user"]

    with st.sidebar:
        st.markdown(
            f'<div style="text-align:center;padding:0.6rem 0;">' 
            f'<div style="font-size:1.6rem;">📈</div>'
            f'<b style="font-size:0.95rem;">스윙 대시보드</b><br>'
            f'<span style="color:#94a3b8;font-size:0.72rem;">👤 {username}</span>'
            f'</div>', unsafe_allow_html=True)
        st.divider()
        menu = st.radio("메뉴", [
            "📊 대시보드",
            "💼 내 포트폴리오",
            "🧮 퀀트 스캐너 2차 정밀",
            "📡 수급 기반 스윙 스캐너",
            "🚀 슈퍼 시그널",
            "🗄️ 관심종목",
            "🌅 모닝 체크",
        ], label_visibility="collapsed")
        st.divider()
        if st.button("🔔 알림 초기화", use_container_width=True):
            try:
                json.dump([], open(user_file(username,"notifications.json"),"w",encoding="utf-8"))
                st.toast("알림 초기화 완료")
            except Exception: pass
        if st.button("🚪 로그아웃", use_container_width=True):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()
        st.caption(datetime.now().strftime("%Y-%m-%d %H:%M"))

    # 알림바
    try:
        if menu == "🌅 모닝 체크":
            show_notification_bar(username)
    except Exception: pass

    # 라우팅
    _pages = {
        "📊 대시보드":              page_dashboard,
        "💼 내 포트폴리오":         page_portfolio,
        "🧮 퀀트 스캐너 2차 정밀":  page_quant,
        "📡 수급 기반 스윙 스캐너": page_supply_swing,
        "🚀 슈퍼 시그널":           page_super_signal,
        "🗄️ 관심종목":              page_vault,
        "🌅 모닝 체크":             page_morning,
    }
    fn = _pages.get(menu, page_dashboard)
    try:
        fn(username)
    except Exception as _e:
        st.error(f"⚠️ [{menu}] 오류: {type(_e).__name__}: {_e}")
        st.info("새로고침 하거나 다른 메뉴를 눌러보세요.")
        with st.expander("상세 오류 (개발자용)"):
            st.code(_tb.format_exc())


if __name__ == "__main__":
    main()
