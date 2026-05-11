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
    try:
        f = user_file(username, "portfolio.json")
        if not os.path.exists(f):
            return []
        with open(f, encoding="utf-8") as fp:
            data = json.load(fp)
        return data if isinstance(data, list) else []
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
    """관심종목 추가/업데이트 — 출처·날짜·기준가 포함 즉시 저장"""
    wl    = load_watchlist(username)
    today = datetime.now().strftime("%Y-%m-%d")
    item  = {
        "id":          int(time.time()),
        "ticker":      str(ticker).zfill(6),
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
_KOSPI_TICKERS = [
    ("005930","삼성전자"),("000660","SK하이닉스"),("373220","LG에너지솔루션"),
    ("207940","삼성바이오로직스"),("005380","현대차"),("000270","기아"),
    ("068270","셀트리온"),("005490","POSCO홀딩스"),("035420","NAVER"),
    ("051910","LG화학"),("028260","삼성물산"),("012330","현대모비스"),
    ("066570","LG전자"),("003550","LG"),("015760","한국전력"),
    ("017670","SK텔레콤"),("086790","하나금융지주"),("055550","신한지주"),
    ("105560","KB금융"),("316140","우리금융지주"),("003490","대한항공"),
    ("009150","삼성전기"),("034730","SK"),("030200","KT"),
    ("036570","엔씨소프트"),("035720","카카오"),("323410","카카오뱅크"),
    ("259960","크래프톤"),("006400","삼성SDI"),("000100","유한양행"),
    ("128940","한미약품"),("000720","현대건설"),("010130","고려아연"),
    ("021240","코웨이"),("009540","한국조선해양"),("042660","한화오션"),
    ("329180","현대중공업"),("267250","HD현대"),("003670","포스코퓨처엠"),
    ("247540","에코프로비엠"),("086520","에코프로"),("002380","KCC"),
    ("000810","삼성화재"),("032640","LG유플러스"),("078930","GS"),
    ("071050","한국금융지주"),("139480","이마트"),("004170","신세계"),
    ("011170","롯데케미칼"),("064350","현대로템"),("012450","한화에어로스페이스"),
    ("004020","현대제철"),("000880","한화"),("001040","CJ"),
    ("097950","CJ제일제당"),("033780","KT&G"),("002790","아모레퍼시픽"),
    ("051900","LG생활건강"),("006800","미래에셋증권"),("016360","삼성증권"),
    ("180640","한진칼"),("007310","오뚜기"),("004800","효성"),
    ("028670","팬오션"),("000150","두산"),("241560","두산밥캣"),
    ("034020","두산에너빌리티"),("047810","한국항공우주"),("272210","한화시스템"),
    ("082740","한화엔진"),("010950","S-Oil"),("096770","SK이노베이션"),
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
    ("095700","제넥신"),("140410","메지온"),("085660","차바이오텍"),
    ("060310","3S"),("131970","두산테스나"),("108320","LX세미콘"),
    ("078020","이베스트투자증권"),("047920","HLB제약"),("028300","HLB"),
    ("096530","씨젠"),("145600","나노신소재"),("089590","제이시스메디칼"),
    ("060850","티에스아이"),("025320","시노펙스"),("060160","지니언스"),
    ("032540","TJ미디어"),("094970","제이엠티"),("036540","SFA반도체"),
    ("078000","텔코웨어"),("025560","미래산업"),("950160","코오롱티슈진"),
    ("183300","코미팜"),("115180","큐리언트"),("290690","성우테크론"),
    ("065620","고려신용정보"),("041190","우리기술투자"),("336370","솔루스첨단소재"),
]

@st.cache_data(ttl=1800, show_spinner=False)
def get_market_tickers(market: str) -> list:
    """
    종목 리스트 수집 — 4단계 폴백:
    1) FDR StockListing
    2) Yahoo Finance .KS/.KQ 우회
    3) pykrx
    4) 내장 하드코딩 리스트
    """
    suffix = ".KS" if market == "KOSPI" else ".KQ"
    errors = []

    # ── 1단계: FDR StockListing ──────────────────────────────
    try:
        import FinanceDataReader as fdr
        lst = fdr.StockListing(market)
        if lst is not None and len(lst) > 0:
            lst.columns = [c.strip() for c in lst.columns]
            code_col = next((c for c in lst.columns if c in ["Code","Symbol"]), None)
            name_col = next((c for c in lst.columns if c in ["Name","종목명"]), None)
            amt_col  = next((c for c in lst.columns if c in ["Amount","Tvalue","Marcap"]), None)
            if code_col:
                lst[code_col] = lst[code_col].astype(str).str.zfill(6)
                sample = lst.nlargest(120, amt_col) if amt_col else lst.head(120)
                rows = [{"ticker": str(r[code_col]).zfill(6),
                         "name":   str(r.get(name_col, r[code_col])),
                         "market": market,
                         "yf_ticker": str(r[code_col]).zfill(6) + suffix}
                        for _, r in sample.iterrows()
                        if str(r[code_col]).isdigit()]
                if rows:
                    print(f"[티커] FDR 성공: {market} {len(rows)}개")
                    return rows
    except Exception as e:
        errors.append(f"FDR: {type(e).__name__}: {str(e)[:80]}")
        print(f"[티커오류] {errors[-1]}")

    # ── 2단계: Yahoo Finance .KS/.KQ 우회 ────────────────────
    try:
        import yfinance as yf
        # Yahoo Finance에서 KOSPI/KOSDAQ 지수 구성종목 스크리닝
        # ^KS11 = KOSPI 지수, ^KQ11 = KOSDAQ 지수
        base = _KOSPI_TICKERS if market == "KOSPI" else _KOSDAQ_TICKERS
        rows = []
        for code, name in base:
            yf_ticker = f"{code}{suffix}"
            rows.append({"ticker": code, "name": name,
                         "market": market, "yf_ticker": yf_ticker})
        if rows:
            print(f"[티커] Yahoo Finance 우회 성공: {market} {len(rows)}개")
            return rows
    except Exception as e:
        errors.append(f"Yahoo: {type(e).__name__}: {str(e)[:80]}")
        print(f"[티커오류] {errors[-1]}")

    # ── 3단계: pykrx ─────────────────────────────────────────
    try:
        from pykrx import stock as krx_stock
        today = datetime.now().strftime("%Y%m%d")
        codes = krx_stock.get_market_ticker_list(today, market=market)
        rows = []
        for code in list(codes)[:120]:
            try:    name = krx_stock.get_market_ticker_name(code)
            except: name = code
            rows.append({"ticker": str(code).zfill(6), "name": name,
                         "market": market,
                         "yf_ticker": str(code).zfill(6) + suffix})
        if rows:
            print(f"[티커] pykrx 성공: {market} {len(rows)}개")
            return rows
    except Exception as e:
        errors.append(f"pykrx: {type(e).__name__}: {str(e)[:80]}")
        print(f"[티커오류] {errors[-1]}")

    # ── 4단계: 내장 하드코딩 리스트 ──────────────────────────
    print(f"[티커] 내장 리스트 사용: {market} (오류: {'; '.join(errors)})")
    base = _KOSPI_TICKERS if market == "KOSPI" else _KOSDAQ_TICKERS
    return [{"ticker": c, "name": n, "market": market,
             "yf_ticker": c + suffix} for c, n in base]


def get_stock_list() -> pd.DataFrame:
    rows = []
    try:
        import FinanceDataReader as fdr
        for market in ["KOSPI", "KOSDAQ"]:
            df = fdr.StockListing(market)
            df.columns = [c.strip() for c in df.columns]
            code_col = next((c for c in df.columns if c in ["Code","Symbol","종목코드"]), None)
            name_col = next((c for c in df.columns if c in ["Name","종목명","ISU_ABBRV"]), None)
            if not code_col or not name_col: continue
            for _, r in df.iterrows():
                code = str(r[code_col]).strip().zfill(6)
                name = str(r[name_col]).strip()
                if code.isdigit() and name:
                    rows.append({"code": code, "name": name, "market": market,
                                 "display": f"{name} ({code})"})
    except:
        pass
    return pd.DataFrame(rows).drop_duplicates("code").reset_index(drop=True)

@st.cache_data(ttl=180, show_spinner=False)
def get_price(ticker: str) -> float:
    """현재가 조회 — 휴장일/네트워크 오류 시 0.0 반환 (에러 없음)"""
    try:
        import FinanceDataReader as fdr
        end   = datetime.now().strftime("%Y%m%d")
        start = (datetime.now() - timedelta(days=10)).strftime("%Y%m%d")
        df = fdr.DataReader(ticker, start, end)
        if df is not None and len(df) > 0:
            for c in df.columns:
                if c.strip().lower() in ("close", "adj close"):
                    v = df[c].iloc[-1]
                    return float(v) if pd.notna(v) and float(v) > 0 else 0.0
    except Exception:
        pass  # 휴장일, 네트워크 오류 등 조용히 처리
    return 0.0

@st.cache_data(ttl=300, show_spinner=False)
def get_ohlcv_cached(ticker: str, days: int = 130):
    """OHLCV 조회 — 휴장일/네트워크 오류 시 None 반환"""
    try:
        import FinanceDataReader as fdr
        end   = datetime.now().strftime("%Y%m%d")
        start = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")
        df = fdr.DataReader(ticker, start, end)
        if df is None or len(df) == 0:
            return None
        col_map = {}
        for c in df.columns:
            cl = c.strip().lower()
            if cl == "open":    col_map[c] = "open"
            elif cl == "high":  col_map[c] = "high"
            elif cl == "low":   col_map[c] = "low"
            elif cl in ("close","adj close"): col_map[c] = "close"
            elif cl == "volume": col_map[c] = "volume"
        df = df.rename(columns=col_map)
        for col in ["open","high","low","close","volume"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        return df.dropna(subset=["close"])
    except Exception:
        return None  # 조용히 처리


def show_login():
    st.markdown("""
    <div style='text-align:center; padding: 3rem 0 1rem;'>
        <div style='font-size:3rem;'>📈</div>
        <h1 style='color:#4e9eff; font-size:1.8rem; margin:0.5rem 0;'>스윙 대시보드</h1>
        <p style='color:#8892a4;'>로그인하여 시작하세요</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        users = load_users()
        tab1, tab2 = st.tabs(["🔐 로그인", "📝 회원가입"])

        with tab1:
            username = st.text_input("아이디", key="login_id")
            password = st.text_input("비밀번호", type="password", key="login_pw")
            if st.button("로그인", key="btn_login"):
                if username in users and users[username]["pw"] == hash_pw(password):
                    st.session_state["user"] = username
                    st.session_state["seed"] = users[username].get("seed", 2_000_000)
                    st.rerun()
                else:
                    st.error("아이디 또는 비밀번호가 틀렸습니다.")
            st.caption("기본 계정: admin / 1234")

        with tab2:
            new_id  = st.text_input("새 아이디", key="reg_id")
            new_pw  = st.text_input("새 비밀번호", type="password", key="reg_pw")
            new_pw2 = st.text_input("비밀번호 확인", type="password", key="reg_pw2")
            if st.button("회원가입", key="btn_reg"):
                if not new_id or not new_pw:
                    st.error("아이디와 비밀번호를 입력하세요.")
                elif new_pw != new_pw2:
                    st.error("비밀번호가 일치하지 않습니다.")
                elif new_id in users:
                    st.error("이미 존재하는 아이디입니다.")
                else:
                    users[new_id] = {"pw": hash_pw(new_pw), "seed": 2_000_000}
                    save_users(users)
                    st.success("가입 완료! 로그인하세요.")

# ════════════════════════════════════════════════════════════
#  알림바
# ════════════════════════════════════════════════════════════
def calc_atr_targets(ticker: str, atr_mult_stop: float = 2.0,
                      atr_mult_target: float = 6.0) -> dict:
    """ATR 기반 손절/익절 자동 계산"""
    try:
        df = get_ohlcv_cached(ticker, days=30)
        if df is None or len(df) < 15:
            return {}
        import ta
        atr_ind = ta.volatility.AverageTrueRange(
            df["high"], df["low"], df["close"], window=14)
        df["atr"] = atr_ind.average_true_range()
        df = df.fillna(0)
        row     = df.iloc[-1]
        cur     = float(row["close"])
        atr_val = float(row["atr"])
        if atr_val <= 0 or cur <= 0:
            return {}
        return {
            "cur":        cur,
            "atr":        round(atr_val, 2),
            "atr_pct":    round(atr_val/cur*100, 2),
            "stoploss":   round(cur - atr_val * atr_mult_stop, 0),
            "target":     round(cur + atr_val * atr_mult_target, 0),
            "stop_mult":  atr_mult_stop,
            "tgt_mult":   atr_mult_target,
        }
    except Exception:
        return {}

def load_notifications(username: str) -> list:
    f = user_file(username, "notifications.json")
    try:
        if os.path.exists(f):
            data = json.load(open(f, encoding="utf-8"))
            return data if isinstance(data, list) else []
    except: pass
    return []

def add_notification(username: str, msg: str, level: str = "info"):
    """알림 추가 (최근 30개 유지)"""
    try:
        nots = load_notifications(username)
        nots.insert(0, {"msg": msg, "level": level,
                        "time": datetime.now().strftime("%H:%M")})
        nots = nots[:30]
        path = user_file(username, "notifications.json")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        json.dump(nots, open(path, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)
    except: pass

def send_telegram(message: str):
    """텔레그램 메시지 전송 (st.secrets 기반)"""
    token   = _get_tg_token()
    chat_id = _get_tg_chat_id()
    if not token or not chat_id:
        st.warning("텔레그램 설정이 없습니다. .streamlit/secrets.toml을 확인하세요.")
        return
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        resp = requests.post(url, json={
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML"
        }, timeout=10, verify=False)
        if resp.status_code != 200:
            st.warning(f"텔레그램 오류: {resp.text[:100]}")
    except Exception as e:
        st.warning(f"텔레그램 전송 실패: {e}")


def show_notification_bar(username: str):
    """알림바 — 비활성화됨 (모닝체크 카드로 대체)"""
    pass

# ════════════════════════════════════════════════════════════
#  [1] 대시보드
# ════════════════════════════════════════════════════════════
def page_dashboard(username: str):
    st.markdown("## 📊 대시보드")

    if fix_portfolio_realized(username):
        st.toast("📌 실현손익 데이터 정상화 완료")

    portfolio = load_portfolio(username)
    if not portfolio:
        st.info("포트폴리오에 종목을 추가하면 대시보드가 활성화됩니다.")
        return

    # 수치 계산
    realized   = sum(float(p.get("realized_pnl",0)) for p in portfolio if p.get("status")=="청산")
    rows, total_cost, total_cur = [], 0.0, 0.0
    for p in portfolio:
        if p.get("status") == "청산": continue
        qty       = int(p.get("qty",1))
        buy_price = float(p.get("buy_price",0))
        cost      = float(p.get("total_amount", buy_price*qty))
        cur       = float(get_price(p["ticker"]) or buy_price)
        val       = cur * qty
        pnl       = val - cost
        pnl_pct   = pnl/cost*100 if cost else 0
        total_cost += cost; total_cur += val
        rows.append({**p, "cur_price":cur, "pnl":pnl, "pnl_pct":pnl_pct})

    unrealized    = total_cur - total_cost
    total_pnl     = unrealized + realized
    total_pnl_pct = total_pnl/total_cost*100 if total_cost else 0  # 투자액 기준

    def cc(v): return "#38bdf8" if v>=0 else "#f87171"
    def sg(v): return "+" if v>=0 else ""
    def bl(v): return f"border-left:4px solid {'#38bdf8' if v>=0 else '#f87171'};"

    # 4대 KPI 카드
    k1,k2,k3,k4 = st.columns(4)
    with k1:
        st.markdown(
            f'<div class="card" style="border-left:4px solid #94a3b8;">'
            f'<div class="label">💼 투자액</div>'
            f'<div class="big-num mono" style="color:#e2e8f0;">{total_cost:,.0f}원</div>'
            f'<div style="color:#94a3b8;font-size:0.75rem;margin-top:0.2rem;">'
            f'시드 {total_cost/TOTAL_SEED*100:.1f}% 투입</div></div>',
            unsafe_allow_html=True)
    with k2:
        st.markdown(
            f'<div class="card" style="{bl(unrealized)}">'
            f'<div class="label">📈 미실현 손익</div>'
            f'<div class="big-num mono" style="color:{cc(unrealized)};">{sg(unrealized)}{unrealized:,.0f}원</div>'
            f'<div style="color:{cc(unrealized)};font-size:0.75rem;margin-top:0.2rem;">'
            f'{unrealized/total_cost*100:+.2f}% (투자 대비)</div></div>',
            unsafe_allow_html=True)
    with k3:
        st.markdown(
            f'<div class="card" style="{bl(realized)}">'
            f'<div class="label">✅ 실현 손익</div>'
            f'<div class="big-num mono" style="color:{cc(realized)};">{sg(realized)}{realized:,.0f}원</div>'
            f'<div style="color:#94a3b8;font-size:0.75rem;margin-top:0.2rem;">확정 수익</div></div>',
            unsafe_allow_html=True)
    with k4:
        st.markdown(
            f'<div class="card" style="{bl(total_pnl_pct)}">'
            f'<div class="label">🎯 총 수익률 (시드 기준)</div>'
            f'<div class="big-num mono" style="color:{cc(total_pnl_pct)};font-size:1.9rem;">'
            f'{sg(total_pnl_pct)}{total_pnl_pct:.2f}%</div>'
            f'<div style="color:#94a3b8;font-size:0.75rem;margin-top:0.2rem;">'
            f'시드 {TOTAL_SEED:,}원 기준</div></div>',
            unsafe_allow_html=True)

    st.markdown("<div style='margin:0.6rem 0'></div>", unsafe_allow_html=True)

    # 차트
    if rows:
        ch1, ch2 = st.columns(2)
        with ch1:
            labels = [r["name"] for r in rows]
            values = [r["cur_price"]*int(r.get("qty",1)) for r in rows]
            colors = ["#38bdf8","#34d399","#fbbf24","#f87171","#a78bfa","#fb923c"]
            fig_p  = go.Figure(go.Pie(
                labels=labels, values=values, hole=0.55,
                marker=dict(colors=colors[:len(labels)]),
                textfont=dict(size=11, color="#e2e8f0"),
            ))
            fig_p.update_layout(
                title=dict(text="포트폴리오 구성", font=dict(color="#94a3b8",size=13)),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                legend=dict(font=dict(color="#94a3b8",size=11)),
                margin=dict(t=40,b=10,l=10,r=10), height=230)
            st.plotly_chart(fig_p, use_container_width=True)
        with ch2:
            pnls     = [r["pnl"] for r in rows]
            bar_cols = ["#38bdf8" if p>=0 else "#f87171" for p in pnls]
            fig_b    = go.Figure(go.Bar(
                x=[r["name"] for r in rows], y=pnls, marker_color=bar_cols,
                text=[f'{sg(p)}{p:,.0f}원' for p in pnls],
                textposition="outside", textfont=dict(color="#e2e8f0", size=10),
            ))
            fig_b.update_layout(
                title=dict(text="종목별 손익", font=dict(color="#94a3b8",size=13)),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                yaxis=dict(gridcolor="#2d3748", color="#94a3b8", tickfont=dict(size=10)),
                xaxis=dict(color="#94a3b8", tickfont=dict(size=10)),
                margin=dict(t=40,b=10,l=10,r=10), height=230, showlegend=False)
            st.plotly_chart(fig_b, use_container_width=True)

    # 날짜 표시
    st.caption(f"기준일: {datetime.now().strftime('%Y-%m-%d %H:%M')}")


def page_portfolio(username: str):
    st.markdown("## 💼 내 포트폴리오")

    # ATR 배수 설정 (사이드바)
    with st.sidebar:
        st.markdown("### ⚙️ ATR 설정")
        atr_stop = st.number_input("손절 ATR 배수", value=2.0, step=0.5, min_value=0.5,
                                    help="손절가 = 현재가 - ATR × 배수")
        atr_tgt  = st.number_input("익절 ATR 배수", value=6.0, step=0.5, min_value=1.0,
                                    help="익절가 = 현재가 + ATR × 배수")

    portfolio = load_portfolio(username)
    if fix_portfolio_realized(username):
        st.toast("📌 데이터 정상화 완료")

    # ── 매매 기록 추가 ────────────────────────────────────────
    with st.expander("➕ 매매 기록 추가", expanded=False):
        with st.spinner("종목 목록 불러오는 중..."):
            stock_df = get_stock_list()

        if stock_df.empty:
            sel_name, sel_ticker = st.text_input("종목명"), st.text_input("종목코드")
        else:
            selected = st.selectbox("🔍 종목 검색", stock_df["display"].tolist(),
                                    index=None, placeholder="종목명을 입력하세요...")
            if selected:
                matched    = stock_df[stock_df["display"]==selected].iloc[0]
                sel_name   = matched["name"]
                sel_ticker = matched["code"]
                st.markdown(
                    f'<div style="background:#1e2535;border:1px solid #2d3748;'
                    f'border-radius:8px;padding:0.5rem 1rem;font-size:0.85rem;color:#38bdf8;">'
                    f'✅ <b>{sel_name}</b> | {sel_ticker} | {matched["market"]}</div>',
                    unsafe_allow_html=True)
            else:
                sel_name, sel_ticker = "", ""

        c1, c2, c3, c4 = st.columns([2,1,2,1])
        with c1: trade_dt     = st.date_input("거래일", value=datetime.today())
        with c2: qty          = st.number_input("수량(주)", min_value=1, value=1, step=1)
        with c3: total_amount = st.number_input("총 매수금액(원)", min_value=0, value=0, step=10000)
        with c4: kind         = st.selectbox("구분", ["매수","매도"])

        avg_price = total_amount / qty if qty > 0 and total_amount > 0 else 0

        # ATR 기반 자동 손절/익절 계산
        atr_info = {}
        if sel_ticker and avg_price > 0:
            with st.spinner("ATR 계산 중..."):
                atr_info = calc_atr_targets(sel_ticker, atr_stop, atr_tgt)

            if atr_info:
                a1,a2,a3,a4 = st.columns(4)
                a1.metric("평단가", f"{avg_price:,.0f}원")
                a2.metric("ATR값", f"{atr_info['atr']:,.0f}원 ({atr_info['atr_pct']:.1f}%)")
                a3.metric(f"🛑 손절({atr_stop}ATR)", f"{atr_info['stoploss']:,.0f}원",
                          delta=f"{(atr_info['stoploss']-avg_price)/avg_price*100:.1f}%",
                          delta_color="inverse")
                a4.metric(f"🎯 익절({atr_tgt}ATR)", f"{atr_info['target']:,.0f}원",
                          delta=f"+{(atr_info['target']-avg_price)/avg_price*100:.1f}%")
            else:
                if avg_price:
                    st.caption("ATR 계산 불가 — 기본값 적용 (손절-7%, 익절+20%)")

        if st.button("💾 기록 저장", disabled=(not sel_name or avg_price==0)):
            sl = int(atr_info.get("stoploss", avg_price*0.93))
            tg = int(atr_info.get("target",   avg_price*1.20))
            entry = {
                "id":           int(time.time()),
                "kind":         kind,
                "name":         sel_name,
                "ticker":       sel_ticker,
                "date":         str(trade_dt),
                "qty":          int(qty),
                "buy_price":    round(avg_price, 2),
                "total_amount": int(total_amount),
                "stoploss_atr": sl,
                "target_atr":   tg,
                "atr_val":      atr_info.get("atr", 0),
                "atr_stop_mult":atr_stop,
                "atr_tgt_mult": atr_tgt,
                "status":       "보유" if kind=="매수" else "청산",
                "realized_pnl": 0,
            }
            portfolio.append(entry)
            save_portfolio(username, portfolio)
            st.success(f"✅ {sel_name} 저장! 손절:{sl:,} / 익절:{tg:,}")
            st.rerun()

    # ── 보유 종목 현황 ────────────────────────────────────────
    holding = [p for p in portfolio if p.get("status")=="보유"]
    if not holding:
        st.info("보유 중인 종목이 없습니다.")
        return

    st.markdown("### 📋 보유 종목 현황")

    total_cost, total_cur = 0.0, 0.0
    for p in holding:
        qty_n     = int(p.get("qty",1))
        buy_price = float(p.get("buy_price",0))
        cost      = float(p.get("total_amount", buy_price*qty_n))
        cur       = float(get_price(p["ticker"]) or buy_price)
        val       = cur * qty_n
        pnl       = val - cost
        pnl_pct   = pnl/cost*100 if cost else 0
        total_cost += cost
        total_cur  += val

        # ATR 기반 손절/익절 (저장된 값 or 실시간 재계산)
        sl   = p.get("stoploss_atr", int(buy_price*0.93))
        tg   = p.get("target_atr",   int(buy_price*1.20))
        atr  = p.get("atr_val", 0)
        smul = p.get("atr_stop_mult", atr_stop)
        tmul = p.get("atr_tgt_mult",  atr_tgt)

        cc_  = "#38bdf8" if pnl>=0 else "#f87171"
        sg_  = "+" if pnl>=0 else ""

        # 상태 판정
        if cur <= sl:   badge, bc = "🚨 손절선 이탈!", "#f87171"
        elif cur >= tg: badge, bc = "🎯 익절 도달!", "#34d399"
        elif (cur-sl)/(tg-sl) > 0.7 if tg>sl else False:
            badge, bc = "📈 목표 근접", "#fbbf24"
        else:           badge, bc = "⏳ 보유중", "#94a3b8"

        st.markdown(
            f'<div class="card" style="border-left:4px solid {cc_};">'
            f'<div style="display:flex;justify-content:space-between;align-items:flex-start;">'
            f'<div>'
            f'<b style="font-size:1rem;">{p["name"]}</b>'
            f'<span style="color:#94a3b8;font-size:0.75rem;margin-left:0.4rem;">{p["ticker"]}</span>'
            f'<span style="background:{bc}22;color:{bc};border-radius:5px;'
            f'padding:2px 8px;font-size:0.72rem;margin-left:0.4rem;">{badge}</span>'
            f'</div>'
            f'<div style="text-align:right;">'
            f'<div style="color:{cc_};font-family:JetBrains Mono,monospace;'
            f'font-weight:900;font-size:1.2rem;">{sg_}{pnl_pct:.2f}%</div>'
            f'<div style="color:{cc_};font-size:0.8rem;">{sg_}{pnl:,.0f}원</div>'
            f'</div></div>'
            f'<div style="display:grid;grid-template-columns:repeat(4,1fr);'
            f'gap:0.4rem;margin-top:0.6rem;font-size:0.8rem;">'
            f'<div><div class="label">평단가</div>'
            f'<b class="mono">{buy_price:,.0f}원</b></div>'
            f'<div><div class="label">현재가</div>'
            f'<b class="mono" style="color:{cc_}">{cur:,.0f}원</b></div>'
            f'<div><div class="label">수량</div>'
            f'<b>{qty_n}주</b></div>'
            f'<div><div class="label">ATR({atr:,.0f}원)</div>'
            f'<b style="color:#94a3b8">{atr/cur*100:.1f}%</b></div>'
            f'</div>'
            f'</div>', unsafe_allow_html=True)

        # 매매 가이드 접기
        with st.expander(f"📋 {p['name']} 매매 가이드 (ATR 기반)", expanded=False):
            g1,g2,g3,g4 = st.columns(4)
            g1.metric(f"🛑 손절({smul}ATR)", f"{sl:,}원",
                      delta=f"{(sl-cur)/cur*100:.1f}%", delta_color="inverse")
            g2.metric(f"🎯 익절({tmul}ATR)", f"{tg:,}원",
                      delta=f"+{(tg-cur)/cur*100:.1f}%")
            g3.metric("현재 손익비",
                      f"{(tg-cur)/(cur-sl):.1f}배" if cur>sl else "—")
            g4.metric("ATR값", f"{atr:,.0f}원")

            rc1, rc2, rc3 = st.columns(3)
            with rc1:
                if st.button("🔄 ATR 재계산", key=f"recalc_{p['id']}"):
                    new_atr = calc_atr_targets(p["ticker"], atr_stop, atr_tgt)
                    if new_atr:
                        for item in portfolio:
                            if item["id"]==p["id"]:
                                item["stoploss_atr"]  = int(new_atr["stoploss"])
                                item["target_atr"]    = int(new_atr["target"])
                                item["atr_val"]       = new_atr["atr"]
                                item["atr_stop_mult"] = atr_stop
                                item["atr_tgt_mult"]  = atr_tgt
                        save_portfolio(username, portfolio)
                        st.success(f"재계산 완료: 손절 {new_atr['stoploss']:,.0f} / 익절 {new_atr['target']:,.0f}")
                        st.rerun()
            with rc2:
                if st.button("✅ 청산 처리", key=f"sell_{p['id']}"):
                    realized = (cur - buy_price) * qty_n
                    for item in portfolio:
                        if item["id"]==p["id"]:
                            item["status"]="청산"
                            item["realized_pnl"]=realized
                    save_portfolio(username, portfolio)
                    st.success(f"청산 완료 (실현손익: {realized:+,.0f}원)")
                    st.rerun()
            with rc3:
                if st.button("🗑️ 삭제", key=f"del_{p['id']}"):
                    save_portfolio(username, [x for x in portfolio if x["id"]!=p["id"]])
                    st.rerun()

    # ── 포트폴리오 요약 ───────────────────────────────────────
    st.markdown("---")
    unrealized = total_cur - total_cost
    realized   = sum(float(p.get("realized_pnl",0)) for p in portfolio if p.get("status")=="청산")
    total_pnl  = unrealized + realized
    inv_pct    = total_pnl/total_cost*100 if total_cost else 0

    s1,s2,s3,s4 = st.columns(4)
    for col, label, val, color in [
        (s1,"💼 투자액",    f"{total_cost:,.0f}원",    "#94a3b8"),
        (s2,"📈 미실현손익", f"{unrealized:+,.0f}원",   "#38bdf8" if unrealized>=0 else "#f87171"),
        (s3,"✅ 실현손익",  f"{realized:+,.0f}원",      "#34d399" if realized>=0 else "#f87171"),
        (s4,"🎯 수익률",   f"{inv_pct:+.2f}%",         "#38bdf8" if inv_pct>=0 else "#f87171"),
    ]:
        col.markdown(
            f'<div class="card" style="text-align:center;">'
            f'<div class="label">{label}</div>'
            f'<div style="color:{color};font-family:JetBrains Mono,monospace;'
            f'font-size:1rem;font-weight:700;">{val}</div>'
            f'</div>', unsafe_allow_html=True)


def page_quant(username: str):
    st.markdown("## 🧮 퀀트 스캐너 2차 정밀")
    st.info("💡 장 마감 후 오후 3:30 이후 실행 권장. ThreadPoolExecutor 병렬처리로 빠르게 분석합니다.")

    with st.expander("📐 A급 눌림목 기준", expanded=False):
        st.markdown("""
        - **MA 근접**: 현재가가 MA20 또는 MA60의 ±3% 이내  
        - **대량거래**: 최근 5일 내 평균 거래량 300% 이상 발생  
        - **거래감소**: 오늘 거래량 < 스파이크일 거래량 (세력 보유 신호)
        """)

    c1, c2, c3 = st.columns(3)
    with c1: market  = st.selectbox("시장", ["KOSPI","KOSDAQ","전체"])
    with c2: top_n   = st.slider("분석 상위 종목", 10, 60, 30)
    with c3: workers = st.slider("병렬 스레드", 5, 20, 10)

    if st.button("⚡ 병렬 스캔 시작", type="primary", key="quant_scan_btn"):
        import FinanceDataReader as fdr  # noqa
        from concurrent.futures import ThreadPoolExecutor, as_completed

        prog_bar = st.progress(0, text="종목 목록 수집 중...")

        # 종목 목록 수집 — 캐시된 함수 사용 (KRX 직접 접근 방지)
        markets = ["KOSPI","KOSDAQ"] if market=="전체" else [market]
        tickers = []
        for mkt in markets:
            t = get_market_tickers(mkt)
            tickers.extend(t)
        if not tickers:
            st.error("❌ 종목 목록을 가져올 수 없습니다.")
            st.info("💡 캐시 초기화 후 재시도: 브라우저 새로고침 → 다시 스캔")
            return
        st.caption(f"📋 {len(tickers)}개 종목 로드 완료 (FDR/pykrx/내장 리스트 중 하나)")

        total = len(tickers)
        prog_bar.progress(5, text=f"{total}개 종목 분석 시작...")

        # ★ 순수 계산 함수 — Streamlit API 절대 호출 없음
        def _analyze(t):
            try:
                end   = datetime.now().strftime("%Y%m%d")
                start = (datetime.now()-timedelta(days=400)).strftime("%Y%m%d")

                # Yahoo Finance(.KS/.KQ) 우선, 실패 시 FDR 폴백
                df = None
                yf_ticker = t.get("yf_ticker", t["ticker"])
                try:
                    import yfinance as yf
                    yf_df = yf.download(yf_ticker, start=start[:4]+"-"+start[4:6]+"-"+start[6:],
                                        end=end[:4]+"-"+end[4:6]+"-"+end[6:],
                                        progress=False, auto_adjust=True)
                    if yf_df is not None and len(yf_df) >= 65:
                        yf_df.columns = [c.lower() if isinstance(c,str) else c[0].lower()
                                         for c in yf_df.columns]
                        df = yf_df
                except Exception:
                    pass

                if df is None or len(df) < 65:
                    df = fdr.DataReader(t["ticker"], start, end)
                if df is None or len(df) < 65: return None
                for c in df.columns:
                    cl = c.strip().lower()
                    if cl in ("close","adj close"): df = df.rename(columns={c:"close"})
                    elif cl == "volume":            df = df.rename(columns={c:"volume"})
                df["close"]  = pd.to_numeric(df["close"],  errors="coerce")
                df["volume"] = pd.to_numeric(df.get("volume", pd.Series([0]*len(df))), errors="coerce")
                df = df.dropna(subset=["close"])
                if len(df) < 65: return None

                close = df["close"]; vol = df["volume"]
                cur   = float(close.iloc[-1])
                mom   = (close.iloc[-1]/close.iloc[0]-1)*100
                v20   = close.pct_change().rolling(20).std().iloc[-1]*100
                score = mom*0.6 - v20*0.2
                ma20  = close.rolling(20).mean().iloc[-1]
                ma60  = close.rolling(60).mean().iloc[-1] if len(close)>=60 else ma20
                nm20  = abs(cur-ma20)/ma20<=0.03 if ma20 else False
                nm60  = abs(cur-ma60)/ma60<=0.03 if ma60 else False
                near  = nm20 or nm60
                va    = vol.rolling(20).mean().iloc[-6] if len(vol)>=21 else vol.mean()
                r5    = vol.iloc[-6:-1]
                spk   = bool((r5>=va*3.0).any()) if va and va>0 else False
                tdv   = float(vol.iloc[-1]) if len(vol)>0 else 0
                dec   = tdv < float(r5.max()) if spk else False
                return {
                    "is_a_grade": near and spk and dec,
                    "종목코드": t["ticker"], "종목명": t["name"], "시장": t["market"],
                    "현재가": int(cur), "12개월수익률(%)": round(mom,2),
                    "변동성(%)": round(v20,2), "퀀트점수": round(score,2),
                    "MA20이격(%)": round((cur-ma20)/ma20*100,2) if ma20 else 0,
                    "MA60이격(%)": round((cur-ma60)/ma60*100,2) if ma60 else 0,
                    "MA근접": "✅" if near else "❌",
                    "대량거래": "✅" if spk else "❌",
                    "거래감소": "✅" if dec else "❌",
                }
            except Exception:
                return None

        # 병렬 실행 — as_completed 순서로 메인 스레드에서만 progress 업데이트
        results = []
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futs = list(ex.map(_analyze, tickers))  # map은 순서 보장, UI 안 건드림
        results = [r for r in futs if r]

        prog_bar.progress(100, text=f"완료! {len(results)}개 발굴")

        if results:
            df_all = (pd.DataFrame(results)
                      .sort_values(["is_a_grade","퀀트점수"], ascending=[False,False])
                      .head(top_n).reset_index(drop=True))
            df_all.index += 1
            st.session_state["quant_records"] = df_all.to_dict("records")
            st.session_state["quant_results"] = df_all[["종목코드","종목명"]].to_dict("records")
            a_cnt = int(df_all["is_a_grade"].sum())
            st.success(f"✅ {len(df_all)}개 | 🔥 A급 눌림목: {a_cnt}개")
        else:
            st.info("📭 조건에 맞는 종목이 없습니다.")

    # ── 결과 렌더링 (스캔 버튼 바깥) ──────────────────────────
    records = st.session_state.get("quant_records", [])
    if not records:
        return

    df_show = pd.DataFrame(records)
    a_recs  = [r for r in records if r.get("is_a_grade")]
    n_recs  = [r for r in records if not r.get("is_a_grade")]

    if a_recs:
        st.markdown(f"### 🔥 A급 눌림목 <span style='color:#fbbf24;font-size:0.85rem;'>({len(a_recs)}개)</span>", unsafe_allow_html=True)
        for r in a_recs:
            ss = "+" if r["12개월수익률(%)"]>=0 else ""
            mc = "#38bdf8" if abs(r["MA20이격(%)"])<=3 else "#94a3b8"
            st.markdown(
                f'<div class="card card-warn">'
                f'<div style="display:flex;justify-content:space-between;align-items:center;">'
                f'<div><b style="font-size:0.97rem;">🔥 {r["종목명"]}</b>'
                f'<span style="color:#94a3b8;font-size:0.72rem;margin-left:0.4rem;">{r["종목코드"]} | {r["시장"]}</span></div>'
                f'<b class="mono gold-color">점수 {r["퀀트점수"]:.1f}</b></div>'
                f'<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:0.3rem;margin-top:0.4rem;font-size:0.75rem;">'
                f'<div><div class="label">현재가</div><b class="mono">{r["현재가"]:,}원</b></div>'
                f'<div><div class="label">12개월수익</div><b class="profit-color">{ss}{r["12개월수익률(%)"]}%</b></div>'
                f'<div><div class="label">MA20이격</div><b style="color:{mc}">{r["MA20이격(%)"]:+.1f}%</b></div>'
                f'<div><div class="label">MA근접</div><b>{r["MA근접"]}</b></div>'
                f'<div><div class="label">대량거래</div><b>{r["대량거래"]}</b></div>'
                f'<div><div class="label">거래감소</div><b>{r["거래감소"]}</b></div>'
                f'</div></div>', unsafe_allow_html=True)

    if n_recs:
        st.markdown(f"### 📊 일반 종목 <span style='color:#94a3b8;font-size:0.85rem;'>({len(n_recs)}개)</span>", unsafe_allow_html=True)

    disp  = ["종목명","종목코드","시장","현재가","퀀트점수","12개월수익률(%)","MA근접","대량거래","거래감소"]
    df_ed = df_show[[c for c in disp if c in df_show.columns]].copy()
    df_ed.insert(0, "선택", False)
    df_ed.insert(0, "등급", df_show["is_a_grade"].map({True:"🔥",False:"—"}))
    edited = st.data_editor(
        df_ed,
        column_config={"선택": st.column_config.CheckboxColumn("선택", default=False)},
        disabled=[c for c in df_ed.columns if c != "선택"],
        use_container_width=True, hide_index=True, key="quant_editor",
    )
    sel = edited[edited["선택"]==True]
    st.caption(f"{len(sel)}개 선택")
    if st.button(f"➕ 선택 {len(sel)}개 관심종목 추가", type="primary",
                 disabled=len(sel)==0, key="quant_bulk_add"):
        added, today = 0, datetime.now().strftime("%Y-%m-%d")
        for _, row in sel.iterrows():
            matched = next((r for r in records if r["종목코드"]==row["종목코드"]), None)
            if not matched: continue
            cur_p = float(get_price(matched["종목코드"]) or matched["현재가"])
            rv = add_to_watchlist(username=username, ticker=matched["종목코드"],
                name=matched["종목명"], source="퀀트", entry=int(cur_p),
                target=int(cur_p*1.20), stoploss=int(cur_p*0.93),
                market=matched.get("시장",""), scan_date=today, base_price=cur_p)
            if rv in ("added","updated"): added += 1
        st.success(f"✅ {added}개 추가!")
    st.session_state["quant_results"] = [{"종목코드":r["종목코드"],"종목명":r["종목명"]} for r in records]


def page_swing(username: str):
    st.markdown("## 📈 스윙 매매 스캐너")
    st.info("💡 **최적 실행 시간**: 장 마감 후 오후 3:30 이후 권장. 기술적 지표 + 수급 분석 통합 스캐너.")

    # ── 스캔 조건 설정 ────────────────────────────────────────
    with st.expander("⚙️ 기술적 스캔 조건", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            min_chg  = st.number_input("최소 상승률 (%)", value=2.0, step=0.5) / 100
            max_chg  = st.number_input("최대 상승률 (%)", value=30.0, step=1.0) / 100
        with col2:
            min_val  = st.number_input("최소 거래대금 (억)", value=50, step=10,
                                        help="낮출수록 중소형주 포함") * 1e8
            rsi_min  = st.number_input("RSI 하한", value=45, step=5)
        with col3:
            rsi_max  = st.number_input("RSI 상한", value=80, step=5)
            market_s = st.selectbox("시장", ["KOSPI","KOSDAQ","전체"])

    # ── 수급 필터 옵션 (사이드바) ────────────────────────────
    with st.sidebar:
        st.markdown("### 📡 수급 필터")
        use_supply   = st.checkbox("수급 조건 포함", value=False,
                                   help="체크 시 외인+기관 동반 매수 종목만 표시")
        supply_days  = st.slider("수급 집계 기간(거래일)", 3, 10, 5,
                                  disabled=not use_supply)
        min_inst_pct = st.slider("최소 기관보유(%)", 0, 30, 10,
                                  disabled=not use_supply)
        min_vol_ratio= st.slider("최소 거래량비율(배)", 1.0, 3.0, 1.2, step=0.1,
                                  disabled=not use_supply)

    st.caption(f"🔍 이격도 115% 초과 과열 종목 제외 | ATR 기반 개별 손절/익절 | "
               f"{'📡 수급 필터 ON' if use_supply else '📡 수급 필터 OFF'}")

    if st.button("🔍 스윙 스캔 시작", type="primary", key="swing_scan_btn"):
        import FinanceDataReader as fdr
        import ta, yfinance as yf

        progress = st.progress(0, text="종목 수집 중...")

        markets = ["KOSPI","KOSDAQ"] if market_s=="전체" else [market_s]
        tickers_all = []
        for mkt in markets:
            tickers_all.extend(get_market_tickers(mkt))

        if not tickers_all:
            st.error("❌ 종목 목록을 가져올 수 없습니다.")
            return

        total   = len(tickers_all)
        results = []
        suffix_map = {"KOSPI":".KS","KOSDAQ":".KQ"}
        end   = datetime.now().strftime("%Y%m%d")
        start = (datetime.now()-timedelta(days=250)).strftime("%Y%m%d")

        for i, t in enumerate(tickers_all):
            if i % 5 == 0:
                pct = int(5 + i/total*88)
                progress.progress(pct,
                    text=f"분석 {i+1}/{total} | 발굴: {len(results)}개")
            try:
                yf_t = t.get("yf_ticker",
                              t["ticker"] + suffix_map.get(t["market"],".KS"))

                # ── 가격 데이터 (Yahoo 우선, FDR 폴백) ────────
                df = None
                try:
                    s_yf = start[:4]+"-"+start[4:6]+"-"+start[6:]
                    e_yf = end[:4]+"-"+end[4:6]+"-"+end[6:]
                    yf_df = yf.download(yf_t, start=s_yf, end=e_yf,
                                        progress=False, auto_adjust=True, timeout=8)
                    if yf_df is not None and len(yf_df) >= 120:
                        yf_df.columns = [c.lower() if isinstance(c,str)
                                         else c[0].lower() for c in yf_df.columns]
                        df = yf_df
                except Exception:
                    pass
                if df is None:
                    df = fdr.DataReader(t["ticker"], start, end)
                if df is None or len(df) < 120:
                    continue

                # ── 컬럼 정규화 ───────────────────────────────
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
                df = df.dropna(subset=["open","high","low","close","volume"])
                if len(df) < 120:
                    continue

                # ── 기술 지표 ─────────────────────────────────
                df["trade_value"] = df["close"] * df["volume"]
                df["ma5"]   = df["close"].rolling(5).mean()
                df["ma20"]  = df["close"].rolling(20).mean()
                df["ma60"]  = df["close"].rolling(60).mean()
                df["ma120"] = df["close"].rolling(120).mean()
                std          = df["close"].rolling(20).std()
                df["bb_upper"] = df["ma20"] + 2*std
                df["rsi"]   = ta.momentum.RSIIndicator(df["close"],window=14).rsi()
                df["prev_close"]  = df["close"].shift(1)
                df["prev_volume"] = df["volume"].shift(1)

                # ATR
                atr_ind = ta.volatility.AverageTrueRange(
                    df["high"], df["low"], df["close"], window=14)
                df["atr"] = atr_ind.average_true_range()

                row = df.iloc[-1]
                pc  = row["prev_close"]
                if pd.isna(pc) or pc == 0: continue
                chg = (row["close"] - pc) / pc

                # ── 기술적 필터 ───────────────────────────────
                if not (min_chg <= chg <= max_chg):      continue
                if row["trade_value"] < min_val:          continue
                pv = row["prev_volume"]
                if pd.isna(pv) or pv==0 or row["volume"] < pv*0.7: continue
                if row["close"] - row["open"] <= 0 and chg < min_chg: continue
                if any(pd.isna([row["ma5"],row["ma20"],row["ma60"],row["ma120"]])): continue
                if not (row["close"] > row["ma5"] > row["ma20"]): continue
                if row["close"] <= row["ma120"]:          continue
                if pd.isna(row["bb_upper"]) or row["close"] <= row["bb_upper"]: continue
                if pd.isna(row["rsi"]) or not (rsi_min <= row["rsi"] <= rsi_max): continue
                disp = row["close"] / row["ma20"]
                if disp > 1.15 or disp < 0.90:           continue

                # ── ATR 기반 손절/익절 ────────────────────────
                atr_val  = float(row["atr"]) if not pd.isna(row["atr"]) else row["close"]*0.03
                cur_p    = float(row["close"])
                stoploss = cur_p - atr_val * 2.0
                high20   = float(df["high"].iloc[-20:].max())
                target   = high20 if high20 > cur_p else cur_p * 1.12
                ma5f     = float(df["ma5"].iloc[-2]) if not pd.isna(df["ma5"].iloc[-2]) else float(row["ma5"])
                entry    = ma5f * 0.975
                rr       = (target-entry)/(entry-stoploss) if entry > stoploss else 0
                if rr < 1.0: continue

                # ── 수급 데이터 (Yahoo Finance 기관보유 지표) ─
                inst_pct   = 0.0
                vol_ratio  = 0.0
                supply_tag = ""
                try:
                    tk         = yf.Ticker(yf_t)
                    info       = tk.info or {}
                    inst_pct   = float(info.get("heldPercentInstitutions",0) or 0)*100
                    # 최근 거래량 vs 평균
                    recent_vol = float(df["volume"].iloc[-supply_days:].mean())
                    avg_vol    = float(df["volume"].iloc[-30:-supply_days].mean())
                    vol_ratio  = round(recent_vol/avg_vol, 2) if avg_vol > 0 else 1.0
                    # 쌍끌이 태그
                    if inst_pct >= 20 and vol_ratio >= 1.5:
                        supply_tag = "🔥쌍끌이"
                    elif inst_pct >= 15 and vol_ratio >= 1.2:
                        supply_tag = "📈수급양호"
                    elif vol_ratio >= 1.5:
                        supply_tag = "💧거래급증"
                except Exception:
                    pass

                # ── 수급 필터 적용 ────────────────────────────
                if use_supply and supply_tag not in ["🔥쌍끌이","📈수급양호"]:
                    continue

                results.append({
                    "종목명":       t["name"],
                    "종목코드":     t["ticker"],
                    "시장":         t["market"],
                    "현재가":       int(cur_p),
                    "등락률(%)":    round(chg*100, 2),
                    "거래대금(억)": round(row["trade_value"]/1e8, 1),
                    "RSI":          round(float(row["rsi"]), 1),
                    "이격도(%)":    round(disp*100, 2),
                    "ATR":          round(atr_val, 0),
                    "ATR(%)":       round(atr_val/cur_p*100, 2),
                    "손익비":       round(rr, 2),
                    "매수타점":     int(entry),
                    "목표가":       int(target),
                    "손절가":       int(stoploss),
                    "기관보유(%)":  round(inst_pct, 1),
                    "거래량비율":   vol_ratio,
                    "수급태그":     supply_tag,
                })
            except Exception:
                continue

        progress.progress(100, text="✅ 완료!")

        if results:
            df_out = (pd.DataFrame(results)
                      .sort_values(["수급태그","손익비"],
                                   ascending=[False, False],
                                   key=lambda x: x if x.name!="수급태그"
                                       else x.map({"🔥쌍끌이":3,"📈수급양호":2,
                                                   "💧거래급증":1,"":0}))
                      .reset_index(drop=True))
            df_out.index += 1
            st.session_state["swing_records"]      = df_out.to_dict("records")
            st.session_state["swing_results"]      = df_out[["종목코드","종목명"]].to_dict("records")
            st.session_state["swing_results_full"] = df_out.to_dict("records")
            _tmp = user_file(username, "swing_temp.json")
            with open(_tmp, "w", encoding="utf-8") as _f:
                json.dump(df_out.to_dict("records"), _f, ensure_ascii=False, indent=2)
            double_cnt = sum(1 for r in df_out.to_dict("records") if r["수급태그"]=="🔥쌍끌이")
            st.success(f"✅ {len(df_out)}개 발굴 | 🔥쌍끌이: {double_cnt}개 | ATR 손절 적용")
        else:
            st.info("📭 조건에 맞는 종목이 없습니다. 조건을 완화해 보세요.")

    # ── 결과 렌더링 ─────────────────────────────────────────
    records = st.session_state.get("swing_records", [])
    if not records:
        return

    df_show = pd.DataFrame(records)
    n = len(records)
    st.markdown(f"### 📊 발굴 종목 {n}개")
    st.caption("💡 ATR 변동성 손절 | 20일 최고가 저항선 익절 | 🔥쌍끌이=외인+기관 동반매수")

    # 전체 등록
    fa, fb = st.columns([3,1])
    with fa:
        st.markdown(
            f'<div style="background:linear-gradient(90deg,#f8717122,#fbbf2411);'
            f'border:1px solid #fbbf24;border-radius:10px;padding:0.5rem 1rem;'
            f'font-size:0.85rem;color:#fbbf24;">⚡ 전체 <b>{n}개</b> 관심종목에 저장</div>',
            unsafe_allow_html=True)
    with fb:
        if st.button("🔥 전체 추가", key="swing_all_add", type="primary"):
            added, today = 0, datetime.now().strftime("%Y-%m-%d")
            for r in records:
                rv = add_to_watchlist(username=username, ticker=r["종목코드"],
                    name=r["종목명"], source="스윙",
                    entry=int(r["매수타점"]), target=int(r["목표가"]),
                    stoploss=int(r["손절가"]), rsi=float(r.get("RSI",0)),
                    rr_ratio=float(r.get("손익비",0)), market=r.get("시장",""),
                    scan_date=today, base_price=float(r["현재가"]))
                if rv in ("added","updated"): added += 1
            st.success(f"✅ {added}개 추가!")
            if added > 0: st.balloons()

    st.markdown("---")

    # ── 4열 카드 ─────────────────────────────────────────────
    tag_colors = {
        "🔥쌍끌이":  "#f87171",
        "📈수급양호": "#34d399",
        "💧거래급증": "#38bdf8",
        "":           "#2d3748",
    }
    for row_i in range(0, len(records), 4):
        row_recs = records[row_i: row_i+4]
        cols = st.columns(4)
        for col, r in zip(cols, row_recs):
            pnl_col  = "#34d399" if r["등락률(%)"] > 0 else "#f87171"
            pnl_sgn  = "+" if r["등락률(%)"] > 0 else ""
            rr_col   = "#34d399" if r["손익비"]>=2 else ("#fbbf24" if r["손익비"]>=1.5 else "#94a3b8")
            tag      = r.get("수급태그","")
            tag_col  = tag_colors.get(tag,"#2d3748")
            inst_pct = r.get("기관보유(%)",0)
            vr       = r.get("거래량비율",1.0)
            vr_col   = "#34d399" if vr>=1.5 else ("#fbbf24" if vr>=1.2 else "#94a3b8")
            border_top = tag_col if tag else "#2d3748"

            col.markdown(
                f'<div class="card" style="border-top:3px solid {border_top};">'

                # 헤더
                f'<div style="display:flex;justify-content:space-between;align-items:flex-start;">'
                f'<div style="flex:1;min-width:0;">'
                f'<div style="font-size:0.85rem;font-weight:700;'
                f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">'
                f'{r["종목명"]}</div>'
                f'<div style="color:#94a3b8;font-size:0.65rem;">'
                f'{r["종목코드"]} | {r["시장"]}</div>'
                f'</div>'
                f'{"<div style=\"font-size:0.7rem;font-weight:700;color:"+tag_col+";white-space:nowrap;margin-left:0.3rem;\">"+tag+"</div>" if tag else ""}'
                f'</div>'

                # 현재가 + 등락
                f'<div style="margin-top:0.4rem;">'
                f'<span style="color:{pnl_col};font-family:JetBrains Mono,monospace;'
                f'font-size:0.95rem;font-weight:700;">{r["현재가"]:,}</span>'
                f'<span style="color:{pnl_col};font-size:0.7rem;margin-left:0.3rem;">'
                f'{pnl_sgn}{r["등락률(%)"]}%</span>'
                f'</div>'

                # 구분선
                f'<div style="border-top:1px solid #2d3748;margin:0.35rem 0;"></div>'

                # 타점/목표/손절
                f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:0.2rem;font-size:0.7rem;">'
                f'<div><div class="label">💰 타점</div>'
                f'<b style="color:#fbbf24;font-family:JetBrains Mono,monospace;font-size:0.78rem;">'
                f'{r["매수타점"]:,}</b></div>'
                f'<div><div class="label">🎯 목표</div>'
                f'<b style="color:#34d399;font-family:JetBrains Mono,monospace;font-size:0.78rem;">'
                f'{r["목표가"]:,}</b></div>'
                f'<div><div class="label">🛑 손절(ATR)</div>'
                f'<b style="color:#f87171;font-family:JetBrains Mono,monospace;font-size:0.78rem;">'
                f'{r["손절가"]:,}</b></div>'
                f'<div><div class="label">⚖️ 손익비</div>'
                f'<b style="color:{rr_col};">{r["손익비"]}배</b></div>'
                f'</div>'

                # 구분선
                f'<div style="border-top:1px solid #2d3748;margin:0.35rem 0;"></div>'

                # 수급 지표
                f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:0.2rem;font-size:0.7rem;">'
                f'<div><div class="label">🏦 기관보유</div>'
                f'<b style="color:#a78bfa;">{inst_pct}%</b></div>'
                f'<div><div class="label">📊 거래량비율</div>'
                f'<b style="color:{vr_col};">{vr}배</b></div>'
                f'<div><div class="label">📈 RSI</div>'
                f'<b style="color:#e2e8f0;">{r["RSI"]}</b></div>'
                f'<div><div class="label">📐 이격도</div>'
                f'<b style="color:#e2e8f0;">{r["이격도(%)"]}%</b></div>'
                f'</div>'
                f'</div>',
                unsafe_allow_html=True)

            if col.button("➕", key=f"sw_add_{r['종목코드']}_{row_i}",
                          use_container_width=True):
                add_to_watchlist(username=username, ticker=r["종목코드"],
                    name=r["종목명"], source="스윙",
                    entry=int(r["매수타점"]), target=int(r["목표가"]),
                    stoploss=int(r["손절가"]),
                    rsi=float(r.get("RSI",0)), rr_ratio=float(r.get("손익비",0)),
                    market=r.get("시장",""),
                    scan_date=datetime.now().strftime("%Y-%m-%d"),
                    base_price=float(r["현재가"]))
                st.toast(f"✅ {r['종목명']} 추가!")

    # data_editor
    st.markdown("---")
    st.markdown("#### 📋 선택 추가")
    disp  = ["종목명","종목코드","시장","현재가","등락률(%)","수급태그",
             "기관보유(%)","거래량비율","RSI","손익비","매수타점","목표가","손절가"]
    df_ed = df_show[[c for c in disp if c in df_show.columns]].copy()
    df_ed.insert(0, "선택", False)
    edited = st.data_editor(
        df_ed,
        column_config={"선택": st.column_config.CheckboxColumn("선택", default=False)},
        disabled=[c for c in df_ed.columns if c != "선택"],
        use_container_width=True, hide_index=True, key="swing_editor",
    )
    sel = edited[edited["선택"]==True]
    if st.button(f"➕ 선택 {len(sel)}개 추가", disabled=len(sel)==0,
                 type="primary", key="swing_sel_add"):
        added, today = 0, datetime.now().strftime("%Y-%m-%d")
        for _, row in sel.iterrows():
            matched = next((r for r in records if r["종목코드"]==row["종목코드"]), None)
            if not matched: continue
            rv = add_to_watchlist(username=username, ticker=matched["종목코드"],
                name=matched["종목명"], source="스윙",
                entry=int(matched["매수타점"]), target=int(matched["목표가"]),
                stoploss=int(matched["손절가"]),
                rsi=float(matched.get("RSI",0)), rr_ratio=float(matched.get("손익비",0)),
                market=matched.get("시장",""), scan_date=today,
                base_price=float(matched["현재가"]))
            if rv in ("added","updated"): added += 1
        st.success(f"✅ {added}개 추가!")
        if added > 0: st.balloons()


def page_supply(username: str):
    st.markdown("## 📡 수급 스캐너")
    st.info("💡 외국인 + 기관 **쌍끌이** 종목 발굴 — Yahoo Finance 기반, KRX 차단 환경에서도 작동")

    with st.expander("⚙️ 스캔 설정", expanded=True):
        c1, c2, c3 = st.columns(3)
        with c1: market_s = st.selectbox("시장", ["KOSPI","KOSDAQ","전체"], key="sup_mkt")
        with c2: top_n    = st.slider("Top N", 10, 50, 20, key="sup_n")
        with c3: days_sel = st.slider("집계 기간(거래일)", 3, 20, 5, key="sup_days")

    if st.button("🔍 수급 스캔 시작", type="primary", key="sup_scan"):
        prog = st.progress(0, text="종목 수집 중...")
        results = []
        today = datetime.now()

        try:
            import yfinance as yf
            markets = ["KOSPI","KOSDAQ"] if market_s=="전체" else [market_s]
            suffix_map = {"KOSPI":".KS","KOSDAQ":".KQ"}

            # 내장 종목 리스트 활용
            tickers_pool = []
            for mkt in markets:
                base = get_market_tickers(mkt)
                tickers_pool.extend(base)

            total = len(tickers_pool)
            prog.progress(5, text=f"{total}개 종목 수급 분석 시작...")

            end_dt   = today
            start_dt = today - timedelta(days=days_sel*2 + 10)
            s_str = start_dt.strftime("%Y-%m-%d")
            e_str = end_dt.strftime("%Y-%m-%d")

            for i, t in enumerate(tickers_pool):
                if i % 10 == 0:
                    pct = int(5 + i/total*90)
                    prog.progress(pct, text=f"분석 중 {i+1}/{total} | 발굴: {len(results)}개")
                try:
                    yf_t = t.get("yf_ticker", t["ticker"] + suffix_map.get(t["market"],".KS"))
                    tk   = yf.Ticker(yf_t)

                    # 기관/외국인 보유 데이터
                    inst_info = tk.institutional_holders
                    info      = tk.info or {}

                    # 기관 보유 비중
                    inst_pct  = float(info.get("heldPercentInstitutions", 0) or 0) * 100
                    insider_pct = float(info.get("heldPercentInsiders", 0) or 0) * 100

                    # 최근 거래량 변화 (수급 대리 지표)
                    hist = tk.history(start=s_str, end=e_str)
                    if hist is None or len(hist) < 3:
                        continue

                    avg_vol   = float(hist["Volume"].mean())
                    recent_vol = float(hist["Volume"].iloc[-days_sel:].mean())
                    vol_ratio  = recent_vol / avg_vol if avg_vol > 0 else 0

                    cur_price = float(hist["Close"].iloc[-1]) if len(hist) > 0 else 0
                    price_chg = float((hist["Close"].iloc[-1] - hist["Close"].iloc[-days_sel]) /
                                      hist["Close"].iloc[-days_sel] * 100) if len(hist) >= days_sel else 0

                    # 쌍끌이 판정: 기관 보유 15% 이상 + 거래량 증가
                    if inst_pct >= 15 and vol_ratio >= 1.2:
                        results.append({
                            "종목코드":    t["ticker"],
                            "종목명":      t["name"],
                            "시장":        t["market"],
                            "기관보유(%)": round(inst_pct, 1),
                            "내부자보유(%)": round(insider_pct, 1),
                            "거래량비율":  round(vol_ratio, 2),
                            "기간수익률(%)": round(price_chg, 2),
                            "현재가":      int(cur_price),
                        })
                except Exception:
                    continue

            prog.progress(100, text="✅ 완료!")

            if results:
                df_r = (pd.DataFrame(results)
                        .sort_values("기관보유(%)", ascending=False)
                        .head(top_n).reset_index(drop=True))
                st.session_state["supply_records"] = df_r.to_dict("records")
                st.success(f"✅ 수급 강세 종목 {len(df_r)}개 발굴!")
            else:
                st.info("📭 조건에 맞는 종목이 없습니다. 조건을 완화해 보세요.")
        except Exception as e:
            st.warning(f"⚠️ 수급 데이터 접근 실패: {e}")
            st.info("💡 Yahoo Finance 데이터는 실시간이 아닐 수 있습니다.")

    # ── 결과 렌더링 ──────────────────────────────────────────
    records = st.session_state.get("supply_records", [])
    if not records:
        st.info("👆 스캔 버튼을 눌러 수급 강세 종목을 찾아보세요!")
        return

    st.markdown("---")

    # 요약
    df_r = pd.DataFrame(records)
    s1,s2,s3,s4 = st.columns(4)
    for col, label, val, color in [
        (s1,"📡 발굴 종목",  f"{len(records)}개",                   "#38bdf8"),
        (s2,"🏦 평균 기관보유", f"{df_r['기관보유(%)'].mean():.1f}%", "#a78bfa"),
        (s3,"📈 평균 거래량비율", f"{df_r['거래량비율'].mean():.2f}배", "#34d399"),
        (s4,"💹 평균 수익률", f"{df_r['기간수익률(%)'].mean():.1f}%","#fbbf24"),
    ]:
        col.markdown(
            f'<div class="card" style="text-align:center;">'
            f'<div class="label">{label}</div>'
            f'<div style="color:{color};font-family:JetBrains Mono,monospace;'
            f'font-size:1.2rem;font-weight:900;">{val}</div>'
            f'</div>', unsafe_allow_html=True)

    st.markdown(f"<div style='color:#94a3b8;font-size:0.8rem;margin:0.4rem 0;'>"
                f"기관 보유비중 내림차순 | {datetime.now().strftime('%Y-%m-%d %H:%M')} 기준"
                f"</div>", unsafe_allow_html=True)

    # 4열 카드
    for row_i in range(0, len(records), 4):
        row_recs = records[row_i: row_i+4]
        cols = st.columns(4)
        for col, r in zip(cols, row_recs):
            rank    = row_i + row_recs.index(r) + 1
            ret_col = "#38bdf8" if r["기간수익률(%)"]>=0 else "#f87171"
            ret_sgn = "+" if r["기간수익률(%)"]>=0 else ""
            vr_col  = "#34d399" if r["거래량비율"]>=1.5 else "#fbbf24"

            col.markdown(
                f'<div class="card" style="border-top:3px solid #a78bfa;">'
                f'<div style="display:flex;justify-content:space-between;">'
                f'<b style="font-size:0.9rem;">#{rank} {r["종목명"]}</b>'
                f'<span style="color:#94a3b8;font-size:0.7rem;">{r["시장"]}</span>'
                f'</div>'
                f'<div style="color:#94a3b8;font-size:0.7rem;">{r["종목코드"]}</div>'
                f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:0.3rem;'
                f'margin-top:0.5rem;font-size:0.75rem;">'
                f'<div><div class="label">🏦 기관보유</div>'
                f'<b style="color:#a78bfa">{r["기관보유(%)"]}%</b></div>'
                f'<div><div class="label">📊 거래량비율</div>'
                f'<b style="color:{vr_col}">{r["거래량비율"]}배</b></div>'
                f'<div><div class="label">💹 기간수익률</div>'
                f'<b style="color:{ret_col}">{ret_sgn}{r["기간수익률(%)"]}%</b></div>'
                f'<div><div class="label">💵 현재가</div>'
                f'<b style="font-family:JetBrains Mono,monospace;">{r["현재가"]:,}원</b></div>'
                f'</div>'
                f'</div>', unsafe_allow_html=True)

            if col.button("➕", key=f"sup_add_{r['종목코드']}_{row_i}",
                          use_container_width=True, help=f"{r['종목명']} 관심종목 추가"):
                cur_p = float(r["현재가"])
                add_to_watchlist(username=username, ticker=r["종목코드"],
                    name=r["종목명"], source="수급",
                    entry=int(cur_p), target=int(cur_p*1.15),
                    stoploss=int(cur_p*0.95),
                    market=r.get("시장",""),
                    scan_date=datetime.now().strftime("%Y-%m-%d"),
                    base_price=cur_p)
                st.toast(f"✅ {r['종목명']} 관심종목 추가!")

    # 테이블
    st.markdown("---")
    st.dataframe(df_r[["종목명","종목코드","시장","기관보유(%)","거래량비율","기간수익률(%)","현재가"]],
                 use_container_width=True, hide_index=True)


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

    c1, c2 = st.columns(2)
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

    if not quant_list or not swing_list:
        st.warning("⚠️ 퀀트 스캐너와 스윙 스캐너를 **모두** 먼저 실행해 주세요!")
        return

    # 공통 종목 탐색
    quant_codes = {str(q.get("종목코드","")).zfill(6): q.get("종목명","") for q in quant_list}
    swing_codes = {str(s.get("종목코드","")).zfill(6): s.get("종목명","") for s in swing_list}
    common      = set(quant_codes.keys()) & set(swing_codes.keys())

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
                                    progress=False, auto_adjust=True, timeout=8)
                if yf_df is not None and len(yf_df) >= 60:
                    yf_df.columns = [c.lower() if isinstance(c,str) else c[0].lower()
                                     for c in yf_df.columns]
                    df = yf_df
                if df is None or len(df) < 60:
                    # KOSDAQ 시도
                    yf_df2 = yf.download(code+".KQ", start=s_yf, end=e_yf,
                                         progress=False, auto_adjust=True, timeout=8)
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

    wl = load_watchlist(username)
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
        cur     = float(get_price(w["ticker"]) or w.get("base_price", w.get("entry",0)))
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
                    if item["ticker"] == tid:
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
                cur      = float(get_price(w["ticker"]) or entry)
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
    all_wl    = load_watchlist(username)
    watchlist = [w for w in all_wl
                 if w.get("is_active", w.get("morning_check", False))]
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
    # 앱 초기화 (최초 1회)
    if "app_initialized" not in st.session_state:
        _init_data_dir()
        st.session_state["app_initialized"] = True

    # 로그인 체크
    if "user" not in st.session_state:
        show_login()
        return

    username = st.session_state["user"]

    # 사이드바
    with st.sidebar:
        st.markdown(f"""
        <div style="text-align:center; padding:1rem 0 0.5rem;">
            <div style="font-size:2rem;">📈</div>
            <div style="font-weight:700; color:#4e9eff;">스윙 대시보드</div>
            <div style="color:#8892a4; font-size:0.8rem;">👤 {username}</div>
        </div>
        """, unsafe_allow_html=True)
        st.divider()

        menu = st.radio("메뉴", [
            "📊 대시보드",
            "💼 내 포트폴리오",
            "🧮 퀀트 스캐너 2차 정밀",
            "📈 스윙 매매",
            "📡 수급 스캐너",
            "🚀 슈퍼 시그널",
            "🗄️ 관심종목",
            "🌅 모닝 체크",
        ], label_visibility="collapsed")

        st.divider()
        if st.button("🔔 알림 초기화"):
            json.dump([], open(user_file(username,"notifications.json"),"w"))
            st.rerun()
        if st.button("🚪 로그아웃"):
            del st.session_state["user"]
            st.rerun()

        st.markdown(f"""
        <div style="color:#8892a4; font-size:0.75rem; margin-top:1rem;">
            {datetime.now().strftime("%Y-%m-%d %H:%M")}
        </div>
        """, unsafe_allow_html=True)

    # 알림바 — 모닝체크/관심종목 탭에서만 표시
    if menu in ["🌅 모닝 체크"]:
        show_notification_bar(username)

    # 페이지 라우팅
    if menu == "📊 대시보드":
        page_dashboard(username)
    elif menu == "💼 내 포트폴리오":
        page_portfolio(username)
    elif menu == "🧮 퀀트 스캐너 2차 정밀":
        page_quant(username)
    elif menu == "📈 스윙 매매":
        page_swing(username)
    elif menu == "📡 수급 스캐너":
        page_supply(username)
    elif menu == "📡 수급 스캐너":
        page_supply(username)
    elif menu == "🚀 슈퍼 시그널":
        page_super_signal(username)
    elif menu == "🗄️ 관심종목":
        page_vault(username)
    elif menu == "🌅 모닝 체크":
        page_morning(username)


if __name__ == "__main__":
    main()
