# -*- coding: utf-8 -*-
"""
GROWTH INDEX データ集計 v2
- 日本60・米国60・欧州30 = 150銘柄
- 市場別バッチ取得+失敗銘柄は個別リトライ(堅牢化)
- ローソク足はスコア上位80銘柄のみ(data.json軽量化。他はミニチャート表示)
- 品質ゲート: 取得90銘柄未満なら更新中止(前回データ維持)
"""
import json, datetime
import yfinance as yf

J, U, E = "JP", "US", "EU"
UNIVERSE = [
 # ---- 日本 60 ----
 ("7203.T","トヨタ自動車",J,"¥"),("6758.T","ソニーグループ",J,"¥"),("8035.T","東京エレクトロン",J,"¥"),
 ("6861.T","キーエンス",J,"¥"),("9984.T","ソフトバンクG",J,"¥"),("6501.T","日立製作所",J,"¥"),
 ("7974.T","任天堂",J,"¥"),("6098.T","リクルートHD",J,"¥"),("8306.T","三菱UFJ",J,"¥"),
 ("4063.T","信越化学",J,"¥"),("6857.T","アドバンテスト",J,"¥"),("9983.T","ファーストリテイリング",J,"¥"),
 ("4568.T","第一三共",J,"¥"),("6902.T","デンソー",J,"¥"),("6954.T","ファナック",J,"¥"),
 ("7741.T","HOYA",J,"¥"),("4519.T","中外製薬",J,"¥"),("8058.T","三菱商事",J,"¥"),
 ("9432.T","NTT",J,"¥"),("6367.T","ダイキン工業",J,"¥"),("8316.T","三井住友FG",J,"¥"),
 ("4502.T","武田薬品",J,"¥"),("6503.T","三菱電機",J,"¥"),("6752.T","パナソニックHD",J,"¥"),
 ("6981.T","村田製作所",J,"¥"),("8001.T","伊藤忠商事",J,"¥"),("8031.T","三井物産",J,"¥"),
 ("8053.T","住友商事",J,"¥"),("8766.T","東京海上HD",J,"¥"),("9433.T","KDDI",J,"¥"),
 ("9434.T","ソフトバンク",J,"¥"),("4661.T","オリエンタルランド",J,"¥"),("6273.T","SMC",J,"¥"),
 ("6146.T","ディスコ",J,"¥"),("6920.T","レーザーテック",J,"¥"),("6526.T","ソシオネクスト",J,"¥"),
 ("7011.T","三菱重工業",J,"¥"),("7012.T","川崎重工業",J,"¥"),("7013.T","IHI",J,"¥"),
 ("8802.T","三菱地所",J,"¥"),("8801.T","三井不動産",J,"¥"),("2914.T","JT",J,"¥"),
 ("4901.T","富士フイルム",J,"¥"),("4543.T","テルモ",J,"¥"),("6301.T","コマツ",J,"¥"),
 ("6326.T","クボタ",J,"¥"),("7267.T","ホンダ",J,"¥"),("7269.T","スズキ",J,"¥"),
 ("7270.T","SUBARU",J,"¥"),("6702.T","富士通",J,"¥"),("6701.T","NEC",J,"¥"),
 ("9613.T","NTTデータG",J,"¥"),("4307.T","野村総合研究所",J,"¥"),("9022.T","JR東海",J,"¥"),
 ("9020.T","JR東日本",J,"¥"),("2802.T","味の素",J,"¥"),("4452.T","花王",J,"¥"),
 ("7751.T","キヤノン",J,"¥"),("4578.T","大塚HD",J,"¥"),("6762.T","TDK",J,"¥"),
 # ---- 米国 60 ----
 ("NVDA","NVIDIA",U,"$"),("MSFT","Microsoft",U,"$"),("AAPL","Apple",U,"$"),
 ("GOOGL","Alphabet",U,"$"),("AMZN","Amazon",U,"$"),("META","Meta Platforms",U,"$"),
 ("AVGO","Broadcom",U,"$"),("TSLA","Tesla",U,"$"),("LLY","Eli Lilly",U,"$"),
 ("V","Visa",U,"$"),("PLTR","Palantir",U,"$"),("AMD","AMD",U,"$"),
 ("NFLX","Netflix",U,"$"),("CRM","Salesforce",U,"$"),("COST","Costco",U,"$"),
 ("JPM","JPMorgan",U,"$"),("UNH","UnitedHealth",U,"$"),("ORCL","Oracle",U,"$"),
 ("ABNB","Airbnb",U,"$"),("UBER","Uber",U,"$"),("BRK-B","Berkshire Hathaway",U,"$"),
 ("JNJ","Johnson & Johnson",U,"$"),("XOM","Exxon Mobil",U,"$"),("WMT","Walmart",U,"$"),
 ("PG","P&G",U,"$"),("MA","Mastercard",U,"$"),("HD","Home Depot",U,"$"),
 ("CVX","Chevron",U,"$"),("MRK","Merck",U,"$"),("PEP","PepsiCo",U,"$"),
 ("KO","Coca-Cola",U,"$"),("BAC","Bank of America",U,"$"),("ADBE","Adobe",U,"$"),
 ("CSCO","Cisco",U,"$"),("TMO","Thermo Fisher",U,"$"),("MCD","McDonald's",U,"$"),
 ("ABT","Abbott",U,"$"),("INTC","Intel",U,"$"),("QCOM","Qualcomm",U,"$"),
 ("TXN","Texas Instruments",U,"$"),("IBM","IBM",U,"$"),("GE","GE Aerospace",U,"$"),
 ("CAT","Caterpillar",U,"$"),("BA","Boeing",U,"$"),("GS","Goldman Sachs",U,"$"),
 ("MS","Morgan Stanley",U,"$"),("AXP","American Express",U,"$"),("BKNG","Booking",U,"$"),
 ("ISRG","Intuitive Surgical",U,"$"),("NOW","ServiceNow",U,"$"),("SNOW","Snowflake",U,"$"),
 ("PYPL","PayPal",U,"$"),("MU","Micron",U,"$"),("ANET","Arista Networks",U,"$"),
 ("PANW","Palo Alto Networks",U,"$"),("CRWD","CrowdStrike",U,"$"),("VRT","Vertiv",U,"$"),
 ("SMCI","Super Micro",U,"$"),("LRCX","Lam Research",U,"$"),("AMAT","Applied Materials",U,"$"),
 # ---- 欧州 30(ユーロ建て) ----
 ("ASML.AS","ASML",E,"€"),("ADYEN.AS","Adyen",E,"€"),("INGA.AS","ING",E,"€"),
 ("PHIA.AS","Philips",E,"€"),("HEIA.AS","Heineken",E,"€"),("AD.AS","Ahold Delhaize",E,"€"),
 ("SAP.DE","SAP",E,"€"),("SIE.DE","Siemens",E,"€"),("ALV.DE","Allianz",E,"€"),
 ("DTE.DE","Deutsche Telekom",E,"€"),("BMW.DE","BMW",E,"€"),("MBG.DE","Mercedes-Benz",E,"€"),
 ("BAS.DE","BASF",E,"€"),("ADS.DE","Adidas",E,"€"),("IFX.DE","Infineon",E,"€"),
 ("MUV2.DE","Munich Re",E,"€"),("MC.PA","LVMH",E,"€"),("OR.PA","L'Oréal",E,"€"),
 ("TTE.PA","TotalEnergies",E,"€"),("AIR.PA","Airbus",E,"€"),("SU.PA","Schneider Electric",E,"€"),
 ("AI.PA","Air Liquide",E,"€"),("BNP.PA","BNP Paribas",E,"€"),("SAN.PA","Sanofi",E,"€"),
 ("CS.PA","AXA",E,"€"),("RMS.PA","Hermès",E,"€"),("KER.PA","Kering",E,"€"),
 ("EL.PA","EssilorLuxottica",E,"€"),("DG.PA","Vinci",E,"€"),("SAF.PA","Safran",E,"€"),
]

EN_NAMES = {
 "7203.T":"Toyota Motor","6758.T":"Sony Group","8035.T":"Tokyo Electron","6861.T":"Keyence",
 "9984.T":"SoftBank Group","6501.T":"Hitachi","7974.T":"Nintendo","6098.T":"Recruit Holdings",
 "8306.T":"Mitsubishi UFJ","4063.T":"Shin-Etsu Chemical","6857.T":"Advantest","9983.T":"Fast Retailing",
 "4568.T":"Daiichi Sankyo","6902.T":"Denso","6954.T":"Fanuc","7741.T":"HOYA","4519.T":"Chugai Pharma",
 "8058.T":"Mitsubishi Corp","9432.T":"NTT","6367.T":"Daikin","8316.T":"SMFG","4502.T":"Takeda Pharma",
 "6503.T":"Mitsubishi Electric","6752.T":"Panasonic","6981.T":"Murata Mfg","8001.T":"Itochu",
 "8031.T":"Mitsui & Co","8053.T":"Sumitomo Corp","8766.T":"Tokio Marine","9433.T":"KDDI",
 "9434.T":"SoftBank Corp","4661.T":"Oriental Land","6273.T":"SMC","6146.T":"Disco",
 "6920.T":"Lasertec","6526.T":"Socionext","7011.T":"Mitsubishi Heavy","7012.T":"Kawasaki Heavy",
 "7013.T":"IHI","8802.T":"Mitsubishi Estate","8801.T":"Mitsui Fudosan","2914.T":"Japan Tobacco",
 "4901.T":"Fujifilm","4543.T":"Terumo","6301.T":"Komatsu","6326.T":"Kubota","7267.T":"Honda",
 "7269.T":"Suzuki","7270.T":"Subaru","6702.T":"Fujitsu","6701.T":"NEC","9613.T":"NTT Data",
 "4307.T":"Nomura Research","9022.T":"JR Central","9020.T":"JR East","2802.T":"Ajinomoto",
 "4452.T":"Kao","7751.T":"Canon","4578.T":"Otsuka Holdings","6762.T":"TDK",
}

TOP_CANDLES = 80    # ローソク足を持たせる上位数(軽量化)
SPARK_POINTS = 24

def pct_change(series, days_ago):
    if len(series) <= days_ago: return None
    now, then = float(series.iloc[-1]), float(series.iloc[-1 - days_ago])
    return round((now / then - 1) * 100, 1) if then else None

def downsample(series, n):
    vals = [float(v) for v in series]
    if len(vals) < 2: return []
    idx = [round(i * (len(vals) - 1) / (n - 1)) for i in range(n)]
    base = vals[idx[0]] or 1
    return [round(vals[i] / base * 100, 1) for i in idx]

def candles(o, rule=None, n=63):
    if rule:
        o = o.resample(rule).agg({"Open":"first","High":"max","Low":"min","Close":"last"}).dropna()
    o = o.iloc[-n:]
    return [[round(float(r.Open),2),round(float(r.High),2),round(float(r.Low),2),round(float(r.Close),2)]
            for r in o.itertuples()]

def fetch_market(tickers):
    """市場単位でバッチ取得。失敗銘柄は個別リトライ。{ticker: OHLC DataFrame}を返す"""
    out = {}
    try:
        df = yf.download(tickers, period="13mo", interval="1d", auto_adjust=True,
                         progress=False, group_by="ticker", threads=True)
        for t in tickers:
            try:
                sub = df[t][["Open","High","Low","Close"]].dropna()
                if len(sub) >= 45: out[t] = sub
            except Exception:
                pass
    except Exception as e:
        print("batch fail:", e)
    # 個別リトライ
    for t in tickers:
        if t in out: continue
        try:
            hi = yf.Ticker(t).history(period="13mo", interval="1d", auto_adjust=True)
            sub = hi[["Open","High","Low","Close"]].dropna()
            if len(sub) >= 45:
                out[t] = sub
                print("retry ok:", t)
            else:
                print("retry insufficient:", t, len(sub))
        except Exception as e:
            print("retry fail:", t, e)
    return out

def backtest_stats(closes):
    agg = {}
    for c in closes.values():
        r1w = c.pct_change(5)*100; r1m = c.pct_change(21)*100
        r3m = c.pct_change(63)*100; fwd = (c.shift(-21)/c - 1)*100
        for i in range(63, len(c)-21):
            w,m,q,f = r1w.iloc[i], r1m.iloc[i], r3m.iloc[i], fwd.iloc[i]
            if any(x != x for x in (w,m,q,f)): continue
            trend = "UP" if (m>=0 and q>=0) else "DN" if (m<0 and q<0) else "MX"
            key = trend + ("H" if w > 5 else "N")
            a = agg.setdefault(key, [0,0,[]])
            a[0]+=1; a[1]+= 1 if f>0 else 0; a[2].append(f)
    stats = {}
    for k,(n,wins,fs) in agg.items():
        if n < 30: continue
        fs.sort()
        stats[k] = {"n":n, "win":round(wins/n*100,1), "med":round(fs[len(fs)//2],1)}
    return stats

def main():
    data, closes = {}, {}
    for m in ("JP","US","EU"):
        tk = [u[0] for u in UNIVERSE if u[2]==m]
        got = fetch_market(tk)
        print(f"{m}: {len(got)}/{len(tk)} fetched")
        data.update(got)
    stocks = []
    for tkr, name, mkt, cur in UNIVERSE:
        sub = data.get(tkr)
        if sub is None: continue
        close = sub["Close"]
        r1d, r1w = pct_change(close,1), pct_change(close,5)
        r1m = pct_change(close,21)
        r3m = pct_change(close, min(63, len(close)-1))
        if None in (r1d, r1w, r1m, r3m): continue
        closes[tkr] = close
        entry = {"t":tkr, "n":name, "m":mkt, "c":cur,
                 "p":round(float(close.iloc[-1]),2),
                 "r1d":r1d, "r1w":r1w, "r1m":r1m, "r3m":r3m,
                 "spark":downsample(close.iloc[-63:], SPARK_POINTS),
                 "_score":r1w*0.2 + r1m*0.5 + r3m*0.3, "_sub":sub}
        if tkr in EN_NAMES: entry["ne"] = EN_NAMES[tkr]
        stocks.append(entry)

    mk = {}
    for s in stocks: mk[s["m"]] = mk.get(s["m"],0)+1
    print("market counts:", mk)
    if len(stocks) < 90:
        raise SystemExit(f"品質ゲート: {len(stocks)}銘柄 (<90)。更新中止・前回データ維持。")

    stocks.sort(key=lambda s: s["_score"], reverse=True)
    for i, s in enumerate(stocks):
        if i < TOP_CANDLES:
            s["cd"] = candles(s["_sub"], None, 63)
            s["cw"] = candles(s["_sub"], "W", 52)
        s.pop("_sub"); s.pop("_score")

    fx = fxe = None
    try:
        f = yf.download(["USDJPY=X","EURJPY=X"], period="5d", interval="1d",
                        auto_adjust=True, progress=False, group_by="ticker")
        fx  = round(float(f["USDJPY=X"]["Close"].dropna().iloc[-1]),2)
        fxe = round(float(f["EURJPY=X"]["Close"].dropna().iloc[-1]),2)
    except Exception as e:
        print("fx skip:", e)

    out = {"universe":len(UNIVERSE), "fetched":len(stocks), "mk":mk,
           "stats":backtest_stats(closes), "fx":fx, "fxe":fxe,
           "updated":datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat(timespec="minutes"),
           "demo":False, "stocks":stocks}
    with open("data.json","w",encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",",":"))
    print(f"data.json: {len(stocks)} stocks / updated {out['updated']}")

if __name__ == "__main__":
    main()
