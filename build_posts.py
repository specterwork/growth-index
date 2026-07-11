# -*- coding: utf-8 -*-
"""
GROWTH INDEX 投稿ネタ自動生成
- data.json を読み、その日のX投稿文＋ショート動画台本を機械生成する（AI不要）
- 出力: posts/latest.md（毎朝これをコピペ/撮影するだけ）
- 実行: python build_posts.py（build_data.py の後に実行。Actionsが自動でやる）
"""
import json, os, shutil, datetime

SITE_URL = "https://example.com/"   # ← 公開後のGitHub Pages URLに変更
HASHTAGS = "#米国株 #日本株 #投資初心者"
DISCLAIMER = "※過去データの機械集計です。投資助言ではありません。売買は自己責任で。"

def pct(v): return f"{'+' if v >= 0 else ''}{v:.1f}%"
def flag(m): return {"JP": "🇯🇵", "US": "🇺🇸", "EU": "🇪🇺"}.get(m, "")

def main():
    with open("data.json", encoding="utf-8") as f:
        data = json.load(f)
    stocks = data["stocks"]
    d = datetime.datetime.fromisoformat(data["updated"])
    date_s = f"{d.month}/{d.day}"

    top5_1w = sorted(stocks, key=lambda s: s["r1w"], reverse=True)[:5]
    top5_1m = sorted(stocks, key=lambda s: s["r1m"], reverse=True)[:5]
    king = max(stocks, key=lambda s: s["r3m"])          # 3ヶ月王者
    hot  = max(stocks, key=lambda s: s["r1w"])          # 今週の急騰

    tenbagger = round(100000 * (1 + king["r3m"] / 100), -2)  # 10万円換算

    md = []
    md.append(f"# 本日の投稿ネタ（{date_s} 自動生成）\n")

    # ---------- X投稿 ----------
    md.append("## X投稿①（ランキング型・そのままコピペ）\n```")
    md.append(f"【{date_s} 直近1週間で伸びた企業TOP5】{flag('JP')}{flag('US')}")
    for i, s in enumerate(top5_1w, 1):
        md.append(f"{i}位 {s['n']} {pct(s['r1w'])}")
    md.append("")
    md.append(f"1ヶ月・3ヶ月ランキングはこちら（毎朝自動更新）")
    md.append(f"→ {SITE_URL}")
    md.append(HASHTAGS)
    md.append("```\n")

    md.append("## X投稿②（問題提起型）\n```")
    md.append(f"有名企業ばかり見てない？")
    md.append(f"直近1ヶ月、データ上いちばん伸びたのは {top5_1m[0]['n']}（{pct(top5_1m[0]['r1m'])}）でした。")
    md.append(f"2位以下と3ヶ月ランキングはここで毎朝更新中")
    md.append(f"→ {SITE_URL}")
    md.append(f"{DISCLAIMER}")
    md.append(HASHTAGS)
    md.append("```\n")

    # ---------- ショート台本 ----------
    md.append("## ショート台本A（ランキング型・約30秒）\n```")
    md.append("[0-3秒 フック]")
    md.append(f"「この1週間で株価が伸びた会社TOP5、言えますか？」")
    md.append("[3-22秒 本体：5位→1位の順に画面にデカ文字で]")
    for i, s in enumerate(reversed(top5_1w), 0):
        md.append(f"  {5-i}位 {s['n']}（{flag(s['m'])}）… {pct(s['r1w'])}")
    md.append("[22-28秒 まとめ]")
    md.append(f"「1位は{top5_1w[0]['n']}。1ヶ月・3ヶ月版はプロフのサイトで毎朝更新してます」")
    md.append("[画面下に常時] " + DISCLAIMER)
    md.append("```\n")

    md.append("## ショート台本B（問題提起・1銘柄フォーカス型・約25秒）\n```")
    md.append("[0-3秒 フック]")
    md.append(f"「3ヶ月で{pct(king['r3m'])}。この会社、知ってますか？」")
    md.append("[3-18秒 本体]")
    md.append(f"「{king['n']}（{flag(king['m'])}）。株価は現在{king['c']}{king['p']:,}。")
    md.append(f"  1週間{pct(king['r1w'])}、1ヶ月{pct(king['r1m'])}、3ヶ月{pct(king['r3m'])}」")
    md.append("[18-25秒 CTA]")
    md.append("「こういう“いま動いてる会社”を毎朝ランキングにしてます。プロフから」")
    md.append("[画面下に常時] " + DISCLAIMER)
    md.append("```\n")

    md.append("## ショート台本C（ビフォーアフター型・約25秒）\n```")
    md.append("[0-3秒 フック]")
    md.append(f"「3ヶ月前の10万円 → いまいくら？」")
    md.append("[3-18秒 本体]")
    md.append(f"「{king['n']}に3ヶ月前10万円分なら、データ上いま約{tenbagger:,.0f}円相当（{pct(king['r3m'])}）。")
    md.append("  ただし逆もある。下落ランキングも同じサイトに載せてます」")
    md.append("[18-25秒 CTA]")
    md.append("「毎朝自動更新。ブックマークはプロフから」")
    md.append("[画面下に常時] " + DISCLAIMER)
    md.append("```\n")

    md.append("## 今週の急騰メモ（リプ・引用用の小ネタ）\n```")
    md.append(f"{hot['n']}、今週だけで{pct(hot['r1w'])}。出来すぎな時ほど冷静に。{SITE_URL}")
    md.append("```\n")

    # 当日データを恒久アーカイブ(コードは真似できても歴史は真似できない)
    os.makedirs("posts/history", exist_ok=True)
    shutil.copy("data.json", f"posts/history/{d.strftime('%Y-%m-%d')}.json")

    os.makedirs("posts", exist_ok=True)
    text = "\n".join(md)
    with open("posts/latest.md", "w", encoding="utf-8") as f:
        f.write(text)
    with open(f"posts/{d.strftime('%Y-%m-%d')}.md", "w", encoding="utf-8") as f:
        f.write(text)
    print(f"posts/latest.md written ({len(text)} chars)")

if __name__ == "__main__":
    main()
