# -*- coding: utf-8 -*-
"""
GROWTH INDEX データ集計スクリプト
- 日米の銘柄リストの株価を取得し、1週/1ヶ月/3ヶ月騰落率とスパークラインを計算
- 出力: data.json（growth-index.html と同じ場所に置く）
- 実行: pip install yfinance && python build_data.py
- GitHub Actions (update.yml) が毎日自動実行する
- EU対応: UNIVERSE に追加するだけ（例: ("ASML.AS","ASML","EU","€")）
  ※フロント側は m の値ごとにタブを足せば表示される
"""
import json, math, datetime
import yfinance as yf

# ============ 銘柄ユニバース（自由に追加・削除してよい） ============
# (ticker, 表示名, 市場, 通貨記号)
UNIVERSE = [
    # ---- 日本（.T = 東証） ----
    ("7203.T","トヨタ自動車","JP","¥"), ("6758.T","ソニーグループ","JP","¥"),
    ("8035.T","東京エレクトロン","JP","¥"), ("6861.T","キーエンス","JP","¥"),
    ("9984.T","ソフトバンクG","JP","¥"), ("6501.T","日立製作所","JP","¥"),
    ("7974.T","任天堂","JP","¥"), ("6098.T","リクルートHD","JP","¥"),
    ("8306.T","三菱UFJ","JP","¥"), ("4063.T","信越化学","JP","¥"),
    ("6857.T","アドバンテスト","JP","¥"), ("9983.T","ファーストリテイリング","JP","¥"),
    ("4568.T","第一三共","JP","¥"), ("6902.T","デンソー","JP","¥"),
    ("6954.T","ファナック","JP","¥"), ("7741.T","HOYA","JP","¥"),
    ("4519.T","中外製薬","JP","¥"), ("8058.T","三菱商事","JP","¥"),
    ("9432.T","NTT","JP","¥"), ("6367.T","ダイキン工業","JP","¥"),
    # ---- 米国 ----
    ("NVDA","NVIDIA","US","$"), ("MSFT","Microsoft","US","$"),
    ("AAPL","Apple","US","$"), ("GOOGL","Alphabet","US","$"),
    ("AMZN","Amazon","US","$"), ("META","Meta Platforms","US","$"),
    ("AVGO","Broadcom","US","$"), ("TSLA","Tesla","US","$"),
    ("LLY","Eli Lilly","US","$"), ("V","Visa","US","$"),
    ("PLTR","Palantir","US","$"), ("AMD","AMD","US","$"),
    ("NFLX","Netflix","US","$"), ("CRM","Salesforce","US","$"),
    ("COST","Costco","US","$"), ("JPM","JPMorgan","US","$"),
    ("UNH","UnitedHealth","US","$"), ("ORCL","Oracle","US","$"),
    ("ABNB","Airbnb","US","$"), ("UBER","Uber","US","$"),
    # ---- EU（後日ここに追加） ----
    # ("ASML.AS","ASML","EU","€"), ("SAP.DE","SAP","EU","€"),
]

TOP_N = 30          # 上位何銘柄を出力するか（総合スコア順）
SPARK_POINTS = 24   # スパークラインの点数

def pct_change(series, days_ago):
    """営業日ベースで days_ago 本前の終値からの騰落率(%)"""
    if len(series) <= days_ago:
        return None
    now, then = float(series.iloc[-1]), float(series.iloc[-1 - days_ago])
    if not then:
        return None
    return round((now / then - 1) * 100, 1)

def downsample(series, n):
    """終値列を n 点に間引き、先頭を100として正規化"""
    vals = [float(v) for v in series]
    if len(vals) < 2:
        return []
    idx = [round(i * (len(vals) - 1) / (n - 1)) for i in range(n)]
    pts = [vals[i] for i in idx]
    base = pts[0] or 1
    return [round(p / base * 100, 1) for p in pts]

def main():
    tickers = [u[0] for u in UNIVERSE]
    # 3ヶ月+バッファぶんの日足を一括取得（auto_adjust=True: 分割・配当調整済み）
    df = yf.download(tickers, period="4mo", interval="1d",
                     auto_adjust=True, progress=False, group_by="ticker", threads=True)
    stocks = []
    for tkr, name, mkt, cur in UNIVERSE:
        try:
            close = df[tkr]["Close"].dropna()
            if len(close) < 45:   # データ不足はスキップ
                continue
            r1w = pct_change(close, 5)     # 5営業日 ≒ 1週
            r1m = pct_change(close, 21)    # 21営業日 ≒ 1ヶ月
            r3m = pct_change(close, min(63, len(close) - 1))  # 63営業日 ≒ 3ヶ月
            if None in (r1w, r1m, r3m):
                continue
            stocks.append({
                "t": tkr, "n": name, "m": mkt, "c": cur,
                "p": round(float(close.iloc[-1]), 2),
                "r1w": r1w, "r1m": r1m, "r3m": r3m,
                "spark": downsample(close.iloc[-63:], SPARK_POINTS),
                "_score": r1w * 0.2 + r1m * 0.5 + r3m * 0.3,
            })
        except Exception as e:
            print(f"skip {tkr}: {e}")
    stocks.sort(key=lambda s: s["_score"], reverse=True)
    for s in stocks:
        s.pop("_score")
    out = {
        "updated": datetime.datetime.now(
            datetime.timezone(datetime.timedelta(hours=9))).isoformat(timespec="minutes"),
        "demo": False,
        "stocks": stocks[:TOP_N],
    }
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    print(f"data.json written: {len(out['stocks'])} stocks / updated {out['updated']}")

if __name__ == "__main__":
    main()
