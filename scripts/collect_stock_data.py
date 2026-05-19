"""
GitHub Actions 전용 데이터 수집 스크립트
- GitHub 서버는 yfinance/FDR 차단 없음
- 매일 장 마감 후 자동 실행
- 결과를 data/quant_scan.json 에 저장
"""
import json, os, time
import pandas as pd
import yfinance as yf
import FinanceDataReader as fdr
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

DATA_DIR    = "data"
MAX_WORKERS = 8
TOP_N       = 80
MIN_VOL_BIL = 50
os.makedirs(DATA_DIR, exist_ok=True)

KOSPI_TICKERS = [
    ("005930","삼성전자"),("000660","SK하이닉스"),("373220","LG에너지솔루션"),
    ("207940","삼성바이오로직스"),("005380","현대차"),("000270","기아"),
    ("068270","셀트리온"),("005490","POSCO홀딩스"),("051910","LG화학"),
    ("028260","삼성물산"),("012330","현대모비스"),("066570","LG전자"),
    ("003550","LG"),("017670","SK텔레콤"),("086790","하나금융지주"),
    ("055550","신한지주"),("105560","KB금융"),("316140","우리금융지주"),
    ("003490","대한항공"),("009150","삼성전기"),("034730","SK"),("030200","KT"),
    ("036570","엔씨소프트"),("035720","카카오"),("323410","카카오뱅크"),
    ("259960","크래프톤"),("006400","삼성SDI"),("000100","유한양행"),
    ("128940","한미약품"),("000720","현대건설"),("010130","고려아연"),
    ("021240","코웨이"),("009540","한국조선해양"),("042660","한화오션"),
    ("329180","현대중공업"),("267250","HD현대"),("003670","포스코퓨처엠"),
    ("247540","에코프로비엠"),("086520","에코프로"),("000810","삼성화재"),
    ("032640","LG유플러스"),("078930","GS"),("071050","한국금융지주"),
    ("139480","이마트"),("004170","신세계"),("011170","롯데케미칼"),
    ("064350","현대로템"),("012450","한화에어로스페이스"),("004020","현대제철"),
    ("000880","한화"),("001040","CJ"),("097950","CJ제일제당"),("033780","KT&G"),
    ("002790","아모레퍼시픽"),("051900","LG생활건강"),("006800","미래에셋증권"),
    ("016360","삼성증권"),("180640","한진칼"),("007310","오뚜기"),
    ("010950","S-Oil"),("096770","SK이노베이션"),("035420","NAVER"),
    ("047810","한국항공우주"),("272210","한화시스템"),("241560","두산밥캣"),
    ("034020","두산에너빌리티"),("003230","삼양식품"),("010060","OCI홀딩스"),
    ("028670","팬오션"),("011200","HMM"),("018260","삼성에스디에스"),
]
KOSDAQ_TICKERS = [
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
    ("036810","에프에스티"),("141080","리가켐바이오"),("950160","코오롱티슈진"),
]

ALL_TICKERS = (
    [{"ticker":c,"name":n,"market":"KOSPI","yf":c+".KS"} for c,n in KOSPI_TICKERS] +
    [{"ticker":c,"name":n,"market":"KOSDAQ","yf":c+".KQ"} for c,n in KOSDAQ_TICKERS]
)


def analyze(t):
    end   = datetime.now()
    start = (end - timedelta(days=400)).strftime("%Y-%m-%d")
    end_s = end.strftime("%Y-%m-%d")
    try:
        # yfinance (GitHub Actions에서는 차단 없음)
        tmp = yf.download(t["yf"], start=start, end=end_s,
                          progress=False, auto_adjust=False, timeout=10)
        if tmp is None or len(tmp) < 60: return None

        flat = []
        for c in tmp.columns:
            if isinstance(c, tuple):
                ct = str(c[1]).strip() if len(c)>1 else ""
                if ct and ct != t["yf"]: continue
                flat.append(str(c[0]).strip().lower())
            else:
                flat.append(str(c).strip().lower())
        if len(flat)==len(tmp.columns): tmp.columns = flat
        df = tmp.sort_index(ascending=True)

        cm = {}
        for c in df.columns:
            cl=str(c).strip().lower()
            if cl=="open": cm[c]="open"
            elif cl=="high": cm[c]="high"
            elif cl=="low": cm[c]="low"
            elif cl=="close": cm[c]="close"
            elif cl=="volume": cm[c]="volume"
        df = df.rename(columns=cm)
        for col in ["open","high","low","close","volume"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        df = df.dropna(subset=["close"])
        if len(df) < 60: return None

        cur_p = float(df["close"].iloc[-1])
        if cur_p <= 0: return None

        tval = cur_p * float(df["volume"].iloc[-1]) / 1e8 if "volume" in df.columns else 0
        if tval < MIN_VOL_BIL: return None

        df["ma5"]  = df["close"].rolling(5).mean()
        df["ma20"] = df["close"].rolling(20).mean()
        df["ma60"] = df["close"].rolling(60).mean() if len(df)>=60 else df["ma20"]
        df["ma120"]= df["close"].rolling(120).mean() if len(df)>=120 else df["ma60"]
        row = df.iloc[-1]
        if any(pd.isna([row.get("ma5",float("nan")),row.get("ma20",float("nan"))])): return None

        ma20 = float(row["ma20"])
        disp = cur_p/ma20 if ma20>0 else 1
        if disp>1.10 or disp<0.85: return None
        if not(row["close"]>row["ma5"]>row["ma20"]): return None

        try:
            import ta
            rsi_val = float(ta.momentum.RSIIndicator(df["close"],14).rsi().iloc[-1])
            if pd.isna(rsi_val) or not(40<=rsi_val<=80): return None
        except: rsi_val = 50.0

        momentum = (df["close"].iloc[-1]/df["close"].iloc[0]-1)*100

        atr_val = 0.0
        try:
            import ta
            if all(c in df.columns for c in ["high","low","close"]):
                atr_val = float(ta.volatility.AverageTrueRange(
                    df["high"],df["low"],df["close"],14
                ).average_true_range().iloc[-1])
        except: pass

        is_a = False
        if "volume" in df.columns and len(df)>=21:
            ma60_v = float(row.get("ma60",ma20))
            near   = (abs(cur_p-ma20)/ma20<=0.05) or \
                     (abs(cur_p-ma60_v)/ma60_v<=0.05 if ma60_v>0 else False)
            va     = df["volume"].rolling(20).mean().iloc[-6]
            r5     = df["volume"].iloc[-6:-1]
            spk    = bool((r5>=va*2.5).any()) if va and va>0 else False
            dec    = float(df["volume"].iloc[-1])<float(r5.max()) if spk else False
            is_a   = near and spk and dec

        mom_s  = min(40,max(0,momentum*0.5))
        rsi_s  = 20 if 50<=rsi_val<=70 else (10 if 40<=rsi_val<=80 else 0)
        disp_s = min(20,max(0,(1.10-disp)*200))
        a_s    = 20 if is_a else 0
        score  = round(mom_s+rsi_s+disp_s+a_s,1)

        high20 = float(df["high"].iloc[-20:].max()) if "high" in df.columns else cur_p*1.10

        return {
            "is_a":is_a,"종목코드":t["ticker"],"종목명":t["name"],"시장":t["market"],
            "현재가":int(cur_p),"종합점수":score,"RSI":round(rsi_val,1),
            "이격도(%)":round(disp*100,2),"ATR(%)":round(atr_val/cur_p*100,2) if cur_p>0 else 0,
            "ATR값":round(atr_val,0),"12개월수익률(%)":round(momentum,2),
            "거래대금(억)":round(tval,1),"20일고가":int(high20),
            "수집시각":datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
    except Exception as e:
        print(f"[오류] {t['name']}: {e}")
        return None


def main():
    print(f"[{datetime.now():%Y-%m-%d %H:%M}] 수집 시작 — {len(ALL_TICKERS)}개 종목")
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        results = [r for r in ex.map(analyze, ALL_TICKERS) if r]

    if not results:
        print("결과 없음")
        return

    df = (pd.DataFrame(results)
          .sort_values(["is_a","종합점수"],ascending=[False,False])
          .head(TOP_N).reset_index(drop=True))
    df["종목코드"] = df["종목코드"].astype(str).str.zfill(6)

    df.to_json(f"{DATA_DIR}/quant_scan.json", orient="records",
               force_ascii=False, indent=2)

    meta = {"updated_at":datetime.now().strftime("%Y-%m-%d %H:%M"),
            "total":len(df),"a_grade":int(df["is_a"].sum())}
    with open(f"{DATA_DIR}/meta.json","w",encoding="utf-8") as f:
        json.dump(meta,f,ensure_ascii=False,indent=2)

    print(f"완료: {len(df)}개 (🔥A급 {meta['a_grade']}개)")

if __name__=="__main__":
    main()
