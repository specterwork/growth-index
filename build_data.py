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

TOP_N = 100  # 実質すべて掲載(市場別の足切りを防ぐ)          # 上位何銘柄を出力するか（総合スコア順）
SPARK_POINTS = 24   # スパークラインの点数

def pct_change(series, days_ago):
    """営業日ベースで days_ago 本前の終値からの騰落率(%)"""
    if len(series) <= days_ago:
        return None
    now, then = float(series.iloc[-1]), float(series.iloc[-1 - days_ago])
    if not then:
        return None
    return round((now / then - 1) * 100, 1)

EN_NAMES = {  # 日本株の英語表示名(EN切替用)
    "7203.T":"Toyota Motor","6758.T":"Sony Group","8035.T":"Tokyo Electron",
    "6861.T":"Keyence","9984.T":"SoftBank Group","6501.T":"Hitachi",
    "7974.T":"Nintendo","6098.T":"Recruit Holdings","8306.T":"Mitsubishi UFJ",
    "4063.T":"Shin-Etsu Chemical","6857.T":"Advantest","9983.T":"Fast Retailing",
    "4568.T":"Daiichi Sankyo","6902.T":"Denso","6954.T":"Fanuc","7741.T":"HOYA",
    "4519.T":"Chugai Pharma","8058.T":"Mitsubishi Corp","9432.T":"NTT","6367.T":"Daikin",
}

def candles(df_t, rule=None, n=63):
    """日足(rule=None)または週足(rule='W')のOHLCを末尾n本、[o,h,l,c]の配列で返す"""
    o = df_t[["Open","High","Low","Close"]].dropna()
    if rule:
        o = o.resample(rule).agg({"Open":"first","High":"max","Low":"min","Close":"last"}).dropna()
    o = o.iloc[-n:]
    return [[round(float(r.Open),2),round(float(r.High),2),round(float(r.Low),2),round(float(r.Close),2)]
            for r in o.itertuples()]

def downsample(series, n):
    """終値列を n 点に間引き、先頭を100として正規化"""
    vals = [float(v) for v in series]
    if len(vals) < 2:
        return []
    idx = [round(i * (len(vals) - 1) / (n - 1)) for i in range(n)]
    pts = [vals[i] for i in idx]
    base = pts[0] or 1
    return [round(p / base * 100, 1) for p in pts]

def backtest_stats(df, universe):
    """過去データ全体で「状態→1ヶ月後リターン」の統計を集計(全銘柄プール)
       状態 = トレンド(UP/DN/MX) × 過熱(H: 1週+5%超 / N)"""
    agg = {}
    for tkr, _, _, _ in universe:
        try:
            c = df[tkr]["Close"].dropna()
            if len(c) < 120:
                continue
            r1w = c.pct_change(5) * 100
            r1m = c.pct_change(21) * 100
            r3m = c.pct_change(63) * 100
            fwd = (c.shift(-21) / c - 1) * 100
            for i in range(63, len(c) - 21):
                w, m, q, f = r1w.iloc[i], r1m.iloc[i], r3m.iloc[i], fwd.iloc[i]
                if any(x != x for x in (w, m, q, f)):  # NaN
                    continue
                trend = "UP" if (m >= 0 and q >= 0) else "DN" if (m < 0 and q < 0) else "MX"
                key = trend + ("H" if w > 5 else "N")
                a = agg.setdefault(key, [0, 0, []])
                a[0] += 1
                a[1] += 1 if f > 0 else 0
                a[2].append(f)
        except Exception:
            continue
    stats = {}
    for k, (n, wins, fs) in agg.items():
        if n < 30:   # サンプル不足の状態は出さない
            continue
        fs.sort()
        stats[k] = {"n": n, "win": round(wins / n * 100, 1), "med": round(fs[len(fs)//2], 1)}
    return stats

def main():
    tickers = [u[0] for u in UNIVERSE]
    # 3ヶ月+バッファぶんの日足を一括取得（auto_adjust=True: 分割・配当調整済み）
    df = yf.download(tickers, period="13mo", interval="1d",
                     auto_adjust=True, progress=False, group_by="ticker", threads=True)
    stocks = []
    for tkr, name, mkt, cur in UNIVERSE:
        try:
            close = df[tkr]["Close"].dropna()
            if len(close) < 45:   # データ不足はスキップ
                continue
            r1d = pct_change(close, 1)     # 前日比
            r1w = pct_change(close, 5)     # 5営業日 ≒ 1週
            r1m = pct_change(close, 21)    # 21営業日 ≒ 1ヶ月
            r3m = pct_change(close, min(63, len(close) - 1))  # 63営業日 ≒ 3ヶ月
            if None in (r1d, r1w, r1m, r3m):
                continue
            entry = {
                "t": tkr, "n": name, "m": mkt, "c": cur,
                "p": round(float(close.iloc[-1]), 2),
                "r1d": r1d, "r1w": r1w, "r1m": r1m, "r3m": r3m,
                "spark": downsample(close.iloc[-63:], SPARK_POINTS),
                "cd": candles(df[tkr], None, 63),   # 日足3ヶ月
                "cw": candles(df[tkr], "W", 52),    # 週足1年
                "_score": r1w * 0.2 + r1m * 0.5 + r3m * 0.3,
            }
            if tkr in EN_NAMES:
                entry["ne"] = EN_NAMES[tkr]
            stocks.append(entry)
        except Exception as e:
            print(f"skip {tkr}: {e}")
    if len(stocks) < 30:
        raise SystemExit(f"品質ゲート: 取得成功 {len(stocks)} 銘柄 (<30)。更新を中止し前回データを維持します。")
    mk = {}
    for s in stocks:
        mk[s["m"]] = mk.get(s["m"], 0) + 1
    print("market counts:", mk)   # 取得診断(Actionsログで確認可)
    for m in ("JP", "US", "EU"):
        if mk.get(m, 0) == 0:
            print(f"WARNING: {m} 市場の取得が0件です。ティッカーまたはデータ源を確認してください。")
    stocks.sort(key=lambda s: s["_score"], reverse=True)
    for s in stocks:
        s.pop("_score")
    # 為替(米国株の円換算表示用)
    fx = fxe = None
    try:
        fxs = yf.download(["USDJPY=X","EURJPY=X"], period="5d", interval="1d",
                          auto_adjust=True, progress=False, group_by="ticker")
        fx  = round(float(fxs["USDJPY=X"]["Close"].dropna().iloc[-1]), 2)
        fxe = round(float(fxs["EURJPY=X"]["Close"].dropna().iloc[-1]), 2)
    except Exception as e:
        print("fx skip:", e)

    out = {
        "universe": len(UNIVERSE), "fetched": len(stocks), "mk": mk,
        "stats": backtest_stats(df, UNIVERSE),
        "fx": fx, "fxe": fxe,
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
