# P-Brain 週間レポート完全自動化システム
## Claude Code 作業指示書

---

## 🎯 目的

毎週火曜朝7:00に自動起動し、P-Brainから固定4画面のスクショを取得 →
週間機種別ランキングレポートをHTML生成 → GitHub Pagesで公開URL化する完全自動化システム。

**現状の手動運用**：毎週ピーブレインから4画面スクショ → Claudeに添付 → HTMLレポート手動生成
**自動化後**：火曜7:00に勝手に動いて、GitHub Pagesに公開URLが生える

**参考レポート（先週手動作成）**：
https://nakamura-del.github.io/pbrain-weekly-report-20240506/

---

## 📊 レポート構造（既存運用準拠）

### 4枚スクショの正体
| # | ファイル | 部門 | 期間 | 用途 |
|---|---------|------|------|------|
| ①| `p4_lastweek.png` | 4円パチンコ | 直近月-日 | 平均値 + TOP15ランキング |
| ②| `p4_2weeksago.png` | 4円パチンコ | 先々週月-日 | 順位変動算出用 |
| ③| `s20_lastweek.png` | 20円スロット | 直近月-日 | 平均値 + TOP15ランキング |
| ④| `s20_2weeksago.png` | 20円スロット | 先々週月-日 | 順位変動算出用 |

### レポート構成
```
■ PACHINKO 4円パチンコ
   全体平均（打込/玉粗利/台粗利/台売上/玉単価/利益率）
   TOP15ランキング表
   
■ SLOT 20円スロット
   全体平均
   TOP15ランキング表
```

### ランキング表の列構成（厳守）
```
順位 | 変動 | 機種 | 発売日 | 経過週 | 打込 | 玉粗利 | 台粗利 | 
台売上 | 玉単価 | 打込シェア | 台粗利シェア | 台売上シェア | 台数シェア
```

### 順位変動の判定ロジック
- **NEW**：先々週TOP15に存在しない機種
- **▲**：先週順位 < 先々週順位（順位上昇）
- **▼**：先週順位 > 先々週順位（順位下降）
- **→**：同順位

### 期間定義
- 先週 = 直近完了週（月曜起点〜日曜終了の7日間）
- 先々週 = 先週の前週

実行日が火曜なら：
- 先週 = 8日前の月曜〜2日前の日曜
- 先々週 = 15日前の月曜〜9日前の日曜

---

## 📦 技術スタック

- Python 3.11+
- Playwright（ブラウザ自動操作・スクショ・カレンダー操作）
- Gemini API（スクショOCR・ランキング表抽出）
- Jinja2（HTMLテンプレート）
- GitHub CLI（`gh`コマンドで自動push）
- Mac LaunchAgents（火曜7:00自動起動）

---

## 📁 作業ディレクトリ

```
~/Desktop/claudecode用/pbrain-weekly-report/
```

---

## 🗂 リポジトリ構成

```
pbrain-weekly-report/
├── .env                          # 環境変数（gitignore対象）
├── .gitignore
├── README.md
├── requirements.txt
├── CLAUDE.md                     # この指示書をコピー
│
├── src/
│   ├── __init__.py
│   ├── main.py                   # エントリーポイント
│   ├── scraper.py                # Playwrightでスクショ取得
│   ├── ocr.py                    # Gemini OCRで数値抽出
│   ├── ranker.py                 # 順位変動算出
│   ├── report_builder.py         # HTMLレポート組み立て
│   ├── publisher.py              # git push + URL通知
│   └── config.py                 # 設定読み込み
│
├── templates/
│   └── weekly_report.html.j2     # Jinja2テンプレート
│
├── screenshots/                  # スクショ一時保存（gitignore）
│
├── docs/                         # GitHub Pages公開ディレクトリ
│   ├── index.html                # 過去レポート一覧
│   └── YYYY-MM-DD/
│       └── index.html            # 各週のレポート
│
├── logs/                         # 実行ログ（gitignore）
│
└── launchd/
    └── com.tlp.pbrain-weekly.plist
```

---

## 🚀 STEP 1：環境構築

```bash
mkdir -p ~/Desktop/claudecode用/pbrain-weekly-report
cd ~/Desktop/claudecode用/pbrain-weekly-report

pip install playwright google-generativeai jinja2 python-dotenv pillow
playwright install chromium

which gh || brew install gh
gh auth status || gh auth login
```

### .env

```
PBRAIN_URL=https://www.p-brain777.com/home/index
PBRAIN_ID=（実際のID）
PBRAIN_PW=（実際のPW）
GEMINI_API_KEY=AIza...
GITHUB_USERNAME=nakamura-del
GITHUB_REPO=pbrain-weekly-report
```

### .gitignore

```
.env
screenshots/
logs/
__pycache__/
*.pyc
.DS_Store
.venv/
```

---

## 🎯 STEP 2：GitHubリポジトリ作成（Public）

```bash
cd ~/Desktop/claudecode用/pbrain-weekly-report
git init
git branch -M main

gh repo create pbrain-weekly-report --public --source=. --push

gh api -X POST /repos/:owner/pbrain-weekly-report/pages \
  -f "source[branch]=main" \
  -f "source[path]=/docs"
```

公開URL：`https://nakamura-del.github.io/pbrain-weekly-report/`

⚠️ **データ性質確認済み**：全国集計データ（業界平均値）であり、個別店舗名・社名なし。Public運用問題なし。

---

## 🔍 STEP 3：P-Brainの操作フロー

### 確定済みフロー

```
1. ログイン（PBRAIN_URL → ID/PASS入力）
   ↓
2. 画面上のブックマーク「P4」クリック
   → デフォルトで先週データ表示
   → スクショ① p4_lastweek.png
   ↓
3. カレンダーUIで先々週の期間を選択 → 検索
   → スクショ② p4_2weeksago.png
   ↓
4. 画面上のブックマーク「S20」クリック
   → デフォルトで先週データ表示
   → スクショ③ s20_lastweek.png
   ↓
5. カレンダーUIで先々週の期間を選択 → 検索
   → スクショ④ s20_2weeksago.png
```

### Playwright実装での重要ポイント

**カレンダーUI操作**：
- jQuery UI Datepicker等の典型的なカレンダーUIを想定
- 開始日と終了日の2つの日付ピッカーがある可能性
- 月送りボタン（前月/次月）→ 該当日クリック の手順
- **実画面を見ながらClaude Codeでセレクタを確定すること**

**待機処理**：
- ログイン後：`page.wait_for_load_state("networkidle")`
- ブックマーククリック後：データテーブルの最終行が表示されるまで待つ
- カレンダー検索後：テーブル再描画完了まで待機

---

## 💻 STEP 4：実装ファイル詳細

### 4-1. `src/config.py`

```python
import os
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

PBRAIN_URL = os.getenv("PBRAIN_URL")
PBRAIN_ID = os.getenv("PBRAIN_ID")
PBRAIN_PW = os.getenv("PBRAIN_PW")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GITHUB_USERNAME = os.getenv("GITHUB_USERNAME")
GITHUB_REPO = os.getenv("GITHUB_REPO")

ROOT = Path(__file__).resolve().parent.parent
SCREENSHOT_DIR = ROOT / "screenshots"
DOCS_DIR = ROOT / "docs"


def get_week_ranges(today: datetime = None):
    """直近完了週（月-日）と先々週を返す"""
    if today is None:
        today = datetime.now()
    this_monday = today - timedelta(days=today.weekday())
    last_monday = this_monday - timedelta(days=7)
    last_sunday = this_monday - timedelta(days=1)
    two_weeks_monday = this_monday - timedelta(days=14)
    two_weeks_sunday = this_monday - timedelta(days=8)
    return {
        "lastweek": (last_monday, last_sunday),
        "twoweeksago": (two_weeks_monday, two_weeks_sunday),
    }
```

### 4-2. `src/scraper.py`

```python
from playwright.async_api import async_playwright
from datetime import datetime
from .config import (
    PBRAIN_URL, PBRAIN_ID, PBRAIN_PW,
    SCREENSHOT_DIR, get_week_ranges,
)

# ⚠️ 以下のセレクタはClaude Codeで実画面を見ながら確定すること
SELECTORS = {
    "login_id": "（IDフィールドのセレクタ）",
    "login_pw": "（PWフィールドのセレクタ）",
    "login_btn": "（ログインボタンのセレクタ）",
    "bookmark_p4": "（ブックマークP4のセレクタ）",
    "bookmark_s20": "（ブックマークS20のセレクタ）",
    "calendar_start": "（開始日入力欄/カレンダー起動ボタン）",
    "calendar_end": "（終了日入力欄/カレンダー起動ボタン）",
    "search_btn": "（検索ボタンのセレクタ）",
    "table_ready": "（テーブル描画完了の目印になるセレクタ）",
}


async def select_date_range(page, start_date, end_date):
    """カレンダーUIで期間を選択 → 検索ボタン押下"""
    # ⚠️ カレンダーUIの仕様に応じてClaude Codeで構築
    await page.click(SELECTORS["calendar_start"])
    # 月送りボタンを必要回数クリック
    # → 該当日のセルをクリック
    # 終了日も同様
    await page.click(SELECTORS["calendar_end"])
    # ...
    await page.click(SELECTORS["search_btn"])
    await page.wait_for_load_state("networkidle")
    await page.wait_for_selector(SELECTORS["table_ready"])
    await page.wait_for_timeout(2000)


async def collect(date_str: str) -> dict:
    """4枚のスクショを取得して保存パスを返す"""
    out_dir = SCREENSHOT_DIR / date_str
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = {}

    weeks = get_week_ranges()
    two_start, two_end = weeks["twoweeksago"]

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1920, "height": 1080})
        page = await context.new_page()

        # 1. ログイン
        await page.goto(PBRAIN_URL)
        await page.fill(SELECTORS["login_id"], PBRAIN_ID)
        await page.fill(SELECTORS["login_pw"], PBRAIN_PW)
        await page.click(SELECTORS["login_btn"])
        await page.wait_for_load_state("networkidle")

        # 2. P4 × 先週（デフォルト）
        await page.click(SELECTORS["bookmark_p4"])
        await page.wait_for_selector(SELECTORS["table_ready"])
        await page.wait_for_timeout(2000)
        path = out_dir / "p4_lastweek.png"
        await page.screenshot(path=path, full_page=True)
        paths["p4_lastweek"] = path
        print(f"✅ P4 先週 → {path}")

        # 3. P4 × 先々週
        await select_date_range(page, two_start, two_end)
        path = out_dir / "p4_2weeksago.png"
        await page.screenshot(path=path, full_page=True)
        paths["p4_2weeksago"] = path
        print(f"✅ P4 先々週 → {path}")

        # 4. S20 × 先週
        await page.click(SELECTORS["bookmark_s20"])
        await page.wait_for_selector(SELECTORS["table_ready"])
        await page.wait_for_timeout(2000)
        path = out_dir / "s20_lastweek.png"
        await page.screenshot(path=path, full_page=True)
        paths["s20_lastweek"] = path
        print(f"✅ S20 先週 → {path}")

        # 5. S20 × 先々週
        await select_date_range(page, two_start, two_end)
        path = out_dir / "s20_2weeksago.png"
        await page.screenshot(path=path, full_page=True)
        paths["s20_2weeksago"] = path
        print(f"✅ S20 先々週 → {path}")

        await browser.close()

    return paths
```

### 4-3. `src/ocr.py`

```python
import google.generativeai as genai
import json
import re
from .config import GEMINI_API_KEY

genai.configure(api_key=GEMINI_API_KEY)

PROMPT = """
このパチンコホール業界の週間ランキング表から、データを正確にJSON形式で抽出してください。

【抽出対象】
1. 全体平均値（表上部に表示）
   - 打込、玉粗利、台粗利、台売上、玉単価、利益率

2. 機種ランキングTOP15（表本体）
   各行について以下を取得：
   - 順位、機種名（フル）、発売日（YYYY/MM/DD）、経過週
   - 打込、玉粗利、台粗利、台売上、玉単価
   - 打込シェア（%）、台粗利シェア（%）、台売上シェア（%）、台数シェア（%）

【出力形式】
コードフェンス・前後説明文・コメント禁止。下記JSONのみ。

{
  "average": {
    "uchikomi": 12167,
    "tama_arari": 0.370,
    "dai_arari": 4498,
    "dai_uriage": 25374,
    "tama_tanka": 2.086,
    "rieki_ritsu": 17.73
  },
  "ranking": [
    {
      "rank": 1,
      "kishu": "eフィーバーキン肉マン スマパチ",
      "hatsubaibi": "2026/04/19",
      "keika_shu": 2,
      "uchikomi": 34164,
      "tama_arari": 0.472,
      "dai_arari": 16116,
      "dai_uriage": 81305,
      "tama_tanka": 2.380,
      "uchikomi_share": 6.76,
      "dai_arari_share": 7.71,
      "dai_uriage_share": 8.62,
      "daisuu_share": 2.41
    }
  ]
}

数値はカンマ・%記号を除いた数値のみ。マイナス値は負号付きで。
"""


def extract(image_path) -> dict:
    """スクショ画像から平均値とランキングを抽出"""
    model = genai.GenerativeModel("gemini-2.0-flash-exp")
    img = genai.upload_file(str(image_path))
    response = model.generate_content([PROMPT, img])
    text = response.text.strip()
    text = re.sub(r"^```json\s*|\s*```$", "", text, flags=re.MULTILINE)
    return json.loads(text)
```

### 4-4. `src/ranker.py`

```python
def normalize_kishu(name: str) -> str:
    """機種名のOCR揺れを吸収するための正規化"""
    name = name.replace(" ", "").replace("　", "")
    name = name.replace("・", "").replace("／", "/")
    return name.lower()


def calc_rank_change(current_ranking: list, previous_ranking: list) -> list:
    """
    先週ランキングに先々週との比較で順位変動列を追加
    """
    prev_map = {
        normalize_kishu(r["kishu"]): r["rank"]
        for r in previous_ranking
    }
    
    for row in current_ranking:
        key = normalize_kishu(row["kishu"])
        current_rank = row["rank"]
        if key not in prev_map:
            row["change"] = "NEW"
        else:
            prev_rank = prev_map[key]
            if current_rank < prev_rank:
                row["change"] = "▲"
            elif current_rank > prev_rank:
                row["change"] = "▼"
            else:
                row["change"] = "→"
    return current_ranking
```

### 4-5. `src/report_builder.py`

```python
from jinja2 import Environment, FileSystemLoader
from .config import ROOT, get_week_ranges
from . import ranker


def build(ocr_data: dict, today_str: str) -> str:
    """4枚のOCR結果からHTMLレポートを生成"""
    p4_ranking = ranker.calc_rank_change(
        ocr_data["p4_lastweek"]["ranking"],
        ocr_data["p4_2weeksago"]["ranking"],
    )
    s20_ranking = ranker.calc_rank_change(
        ocr_data["s20_lastweek"]["ranking"],
        ocr_data["s20_2weeksago"]["ranking"],
    )

    weeks = get_week_ranges()
    last_start, last_end = weeks["lastweek"]
    two_start, two_end = weeks["twoweeksago"]

    period_label = f"{last_start.strftime('%Y/%m/%d')}〜{last_end.strftime('%Y/%m/%d')}"
    prev_period_label = f"{two_start.strftime('%Y/%m/%d')}〜{two_end.strftime('%Y/%m/%d')}"

    env = Environment(
        loader=FileSystemLoader(str(ROOT / "templates")),
        autoescape=True,
    )
    tpl = env.get_template("weekly_report.html.j2")
    return tpl.render(
        period=period_label,
        prev_period=prev_period_label,
        p4_avg=ocr_data["p4_lastweek"]["average"],
        p4_ranking=p4_ranking,
        s20_avg=ocr_data["s20_lastweek"]["average"],
        s20_ranking=s20_ranking,
    )
```

### 4-6. `templates/weekly_report.html.j2`

参考レポートのスタイルを踏襲。

```html
<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>P-Brain 週間レポート（{{ period }}）</title>
<style>
  body { font-family: -apple-system, "Hiragino Sans", "Yu Gothic", sans-serif; max-width: 1200px; margin: 2em auto; padding: 0 1em; color: #222; line-height: 1.6; }
  h1 { border-bottom: 3px solid #1a5490; padding-bottom: 0.3em; }
  h2 { margin-top: 2em; padding: 0.4em 0.6em; border-left: 6px solid #c0392b; background: #fcf3f3; }
  h2.slot { border-left-color: #2980b9; background: #f3f7fc; }
  .meta { color: #666; font-size: 14px; margin-bottom: 1em; }
  .avg-block { background: #f7f9fc; padding: 1em 1.4em; border-radius: 6px; margin: 1em 0; display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 12px; }
  .avg-item .lbl { font-size: 12px; color: #666; }
  .avg-item .val { font-size: 20px; font-weight: 600; color: #1a5490; }
  table { border-collapse: collapse; width: 100%; margin: 1em 0; font-size: 13px; }
  th, td { border: 1px solid #ddd; padding: 6px 8px; text-align: right; white-space: nowrap; }
  th { background: #1a5490; color: #fff; font-weight: 500; }
  td.kishu { text-align: left; white-space: normal; min-width: 180px; }
  tr:nth-child(even) { background: #f7f9fc; }
  .change { text-align: center; font-weight: bold; }
  .change.up { color: #c0392b; }
  .change.down { color: #2980b9; }
  .change.new { color: #27ae60; }
  .legend { font-size: 12px; color: #666; margin-top: 1em; padding: 0.6em; background: #fafafa; border-radius: 4px; }
  .footer { margin-top: 3em; padding-top: 1em; border-top: 1px solid #eee; color: #999; font-size: 12px; }
</style>
</head>
<body>
<h1>📊 P-Brain 週間レポート</h1>
<div class="meta">
  期間：{{ period }}<br>
  対象：4円パチンコ / 20円スロット<br>
  順位変動：先々週比（NEW / ▲ / ▼ / →）
</div>

<h2>PACHINKO 4円パチンコ 全体平均</h2>
<div class="avg-block">
  <div class="avg-item"><div class="lbl">打込</div><div class="val">{{ "{:,}".format(p4_avg.uchikomi) }}</div></div>
  <div class="avg-item"><div class="lbl">玉粗利</div><div class="val">{{ "%.3f"|format(p4_avg.tama_arari) }}</div></div>
  <div class="avg-item"><div class="lbl">台粗利</div><div class="val">{{ "{:,}".format(p4_avg.dai_arari) }}</div></div>
  <div class="avg-item"><div class="lbl">台売上</div><div class="val">{{ "{:,}".format(p4_avg.dai_uriage) }}</div></div>
  <div class="avg-item"><div class="lbl">玉単価</div><div class="val">{{ "%.3f"|format(p4_avg.tama_tanka) }}</div></div>
  <div class="avg-item"><div class="lbl">利益率</div><div class="val">{{ "%.2f"|format(p4_avg.rieki_ritsu) }}%</div></div>
</div>

<table>
<thead><tr>
<th>順位</th><th>変動</th><th>機種</th><th>発売日</th><th>経過週</th>
<th>打込</th><th>玉粗利</th><th>台粗利</th><th>台売上</th><th>玉単価</th>
<th>打込シェア</th><th>台粗利シェア</th><th>台売上シェア</th><th>台数シェア</th>
</tr></thead>
<tbody>
{% for r in p4_ranking %}
<tr>
  <td>{{ r.rank }}</td>
  <td class="change {% if r.change == '▲' %}up{% elif r.change == '▼' %}down{% elif r.change == 'NEW' %}new{% endif %}">{{ r.change }}</td>
  <td class="kishu">{{ r.kishu }}</td>
  <td>{{ r.hatsubaibi }}</td>
  <td>{{ r.keika_shu }}</td>
  <td>{{ "{:,}".format(r.uchikomi) }}</td>
  <td>{{ "%.3f"|format(r.tama_arari) }}</td>
  <td>{{ "{:,}".format(r.dai_arari) }}</td>
  <td>{{ "{:,}".format(r.dai_uriage) }}</td>
  <td>{{ "%.3f"|format(r.tama_tanka) }}</td>
  <td>{{ "%.2f"|format(r.uchikomi_share) }}%</td>
  <td>{{ "%.2f"|format(r.dai_arari_share) }}%</td>
  <td>{{ "%.2f"|format(r.dai_uriage_share) }}%</td>
  <td>{{ "%.2f"|format(r.daisuu_share) }}%</td>
</tr>
{% endfor %}
</tbody>
</table>

<h2 class="slot">SLOT 20円スロット 全体平均</h2>
<div class="avg-block">
  <div class="avg-item"><div class="lbl">打込</div><div class="val">{{ "{:,}".format(s20_avg.uchikomi) }}</div></div>
  <div class="avg-item"><div class="lbl">玉粗利</div><div class="val">{{ "%.3f"|format(s20_avg.tama_arari) }}</div></div>
  <div class="avg-item"><div class="lbl">台粗利</div><div class="val">{{ "{:,}".format(s20_avg.dai_arari) }}</div></div>
  <div class="avg-item"><div class="lbl">台売上</div><div class="val">{{ "{:,}".format(s20_avg.dai_uriage) }}</div></div>
  <div class="avg-item"><div class="lbl">玉単価</div><div class="val">{{ "%.3f"|format(s20_avg.tama_tanka) }}</div></div>
  <div class="avg-item"><div class="lbl">利益率</div><div class="val">{{ "%.2f"|format(s20_avg.rieki_ritsu) }}%</div></div>
</div>

<table>
<thead><tr>
<th>順位</th><th>変動</th><th>機種</th><th>発売日</th><th>経過週</th>
<th>打込</th><th>玉粗利</th><th>台粗利</th><th>台売上</th><th>玉単価</th>
<th>打込シェア</th><th>台粗利シェア</th><th>台売上シェア</th><th>台数シェア</th>
</tr></thead>
<tbody>
{% for r in s20_ranking %}
<tr>
  <td>{{ r.rank }}</td>
  <td class="change {% if r.change == '▲' %}up{% elif r.change == '▼' %}down{% elif r.change == 'NEW' %}new{% endif %}">{{ r.change }}</td>
  <td class="kishu">{{ r.kishu }}</td>
  <td>{{ r.hatsubaibi }}</td>
  <td>{{ r.keika_shu }}</td>
  <td>{{ "{:,}".format(r.uchikomi) }}</td>
  <td>{{ "%.3f"|format(r.tama_arari) }}</td>
  <td>{{ "{:,}".format(r.dai_arari) }}</td>
  <td>{{ "{:,}".format(r.dai_uriage) }}</td>
  <td>{{ "%.3f"|format(r.tama_tanka) }}</td>
  <td>{{ "%.2f"|format(r.uchikomi_share) }}%</td>
  <td>{{ "%.2f"|format(r.dai_arari_share) }}%</td>
  <td>{{ "%.2f"|format(r.dai_uriage_share) }}%</td>
  <td>{{ "%.2f"|format(r.daisuu_share) }}%</td>
</tr>
{% endfor %}
</tbody>
</table>

<div class="legend">
NEW 初登場 ▲ 順位上昇 ▼ 順位下降 → 順位変わらず<br>
順位変動は前週（{{ prev_period }}）との比較
</div>

<div class="footer">
Auto-generated by Trust Link Partner / P-Brain Weekly Report Bot<br>
生成期間：{{ period }}
</div>
</body>
</html>
```

### 4-7. `src/publisher.py`

```python
import subprocess
from pathlib import Path
from .config import GITHUB_USERNAME, GITHUB_REPO, DOCS_DIR


def publish(report_html: str, date_str: str) -> str:
    out_dir = DOCS_DIR / date_str
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "index.html").write_text(report_html, encoding="utf-8")

    update_index_page()

    subprocess.run(["git", "add", "docs/"], check=True)
    subprocess.run(["git", "commit", "-m", f"weekly report {date_str}"], check=True)
    subprocess.run(["git", "push"], check=True)

    url = f"https://{GITHUB_USERNAME}.github.io/{GITHUB_REPO}/{date_str}/"
    print(f"📡 Published: {url}")
    return url


def update_index_page():
    """docs/直下の日付ディレクトリを一覧化"""
    dirs = sorted(
        [d.name for d in DOCS_DIR.iterdir() if d.is_dir()],
        reverse=True,
    )
    items = "\n".join(f'<li><a href="{d}/">{d}</a></li>' for d in dirs)
    html = f"""<!DOCTYPE html>
<html lang="ja"><head><meta charset="UTF-8">
<title>P-Brain 週間レポート一覧</title>
<style>body{{font-family:sans-serif;max-width:600px;margin:2em auto;}}</style>
</head><body><h1>P-Brain 週間レポート一覧</h1>
<ul>{items}</ul></body></html>"""
    (DOCS_DIR / "index.html").write_text(html, encoding="utf-8")
```

### 4-8. `src/main.py`

```python
import asyncio
from datetime import datetime
from . import scraper, ocr, report_builder, publisher
from .config import get_week_ranges


async def run():
    today = datetime.now()
    weeks = get_week_ranges(today)
    last_end = weeks["lastweek"][1]
    date_str = last_end.strftime("%Y-%m-%d")  # 先週末日付がディレクトリ名
    print(f"🚀 P-Brain週間レポート生成開始: 期間末 {date_str}")

    # 1. スクショ取得
    paths = await scraper.collect(date_str)

    # 2. OCR（4枚）
    print("🔍 OCR処理中...")
    data = {sid: ocr.extract(path) for sid, path in paths.items()}

    # 3. HTMLレポート生成
    print("📝 レポート組み立て中...")
    html = report_builder.build(data, date_str)

    # 4. GitHub Pagesへ公開
    print("📡 GitHubへpush...")
    url = publisher.publish(html, date_str)

    print(f"\n✅ 完了\n公開URL: {url}")


if __name__ == "__main__":
    asyncio.run(run())
```

---

## ⏰ STEP 5：LaunchAgent設定（火曜7:00自動起動）

### `launchd/com.tlp.pbrain-weekly.plist`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.tlp.pbrain-weekly</string>

    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/env</string>
        <string>python3</string>
        <string>-m</string>
        <string>src.main</string>
    </array>

    <key>WorkingDirectory</key>
    <string>/Users/USERNAME/Desktop/claudecode用/pbrain-weekly-report</string>

    <key>StartCalendarInterval</key>
    <dict>
        <key>Weekday</key>
        <integer>2</integer>
        <key>Hour</key>
        <integer>7</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>

    <key>StandardOutPath</key>
    <string>/Users/USERNAME/Desktop/claudecode用/pbrain-weekly-report/logs/stdout.log</string>

    <key>StandardErrorPath</key>
    <string>/Users/USERNAME/Desktop/claudecode用/pbrain-weekly-report/logs/stderr.log</string>
</dict>
</plist>
```

⚠️ `USERNAME` をMacのユーザー名に置換すること。

### 登録コマンド

```bash
mkdir -p logs
cp launchd/com.tlp.pbrain-weekly.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.tlp.pbrain-weekly.plist

# 動作確認（手動トリガー）
launchctl start com.tlp.pbrain-weekly

# 停止する時
launchctl unload ~/Library/LaunchAgents/com.tlp.pbrain-weekly.plist
```

---

## ✅ STEP 6：開発・テスト手順（推奨順序）

```bash
cd ~/Desktop/claudecode用/pbrain-weekly-report

# 【段階1】手動でスクショ4枚を保存してOCRだけ先にテスト
#   screenshots/manual/p4_lastweek.png 等を手動配置
python -c "from src.ocr import extract; print(extract('screenshots/manual/p4_lastweek.png'))"

# 【段階2】OCR結果からHTMLレポート組み立てテスト
#   ranker.py・report_builder.pyの動作確認

# 【段階3】Playwright実装
#   ⚠️ Claude Codeで `headless=False` にして実画面を見ながらセレクタ確定
#   ログイン → ブックマーク → カレンダー操作の順に1ステップずつ作る

# 【段階4】エンドツーエンド実行
python -m src.main

# 【段階5】publisher動作確認 → 実際に公開URL生成
# 【段階6】LaunchAgent登録 → 火曜まで待って実走確認

tail -f logs/stdout.log logs/stderr.log
```

---

## 🐛 想定トラブルと対処

| 症状 | 原因 | 対処 |
|------|------|------|
| ログイン失敗 | セレクタ変更 | DevToolsで再取得→config.py更新 |
| カレンダー操作ハマる | UIの仕様未把握 | `headless=False`で実画面見ながら手作り |
| OCRで順位ずれ | テーブル領域外も認識 | `clip` パラメータでスクショ範囲限定 |
| 機種名の表記揺れ | 全角/半角・空白差 | ranker.py の normalize_kishu で吸収済み |
| Pagesが404 | 反映待ち | 初回〜10分はかかる、Settings→Pages確認 |
| LaunchAgent動かない | 権限・パス | `launchctl list \| grep tlp` で状態確認 |
| Macスリープ中起動失敗 | スリープ抑止未設定 | システム設定でスケジュール起動 or `caffeinate` |

---

## 📝 重要メモ（必読）

### Geminiモデル選定

- 第一選択：`gemini-2.0-flash-exp`（速い・安い・十分な精度）
- ランキング表が複雑で精度不足なら：`gemini-2.5-pro` に切替
- スクショをフルページ取得後、テーブル部分のみ Pillow で crop してOCR渡しすると精度が上がる

### カレンダー操作の手作り推奨

カレンダーUIはサイトごとに個性が強い領域で、Playwrightの汎用コードで書きにくい。
**Claude Codeでブラウザを `headless=False` で立ち上げ、実際の操作を1ステップずつ見ながら**
コードを書いていくのが最速。最初にこの方針で詰めること。

### 公開URLの命名規則

参考レポートは `pbrain-weekly-report-20240506` のように先週末日付を含めて
**リポジトリ名自体に日付を埋め込んでいた**が、自動化版では：

- リポジトリ名：`pbrain-weekly-report`（固定）
- 各週URL：`/docs/YYYY-MM-DD/index.html`（先週末日付）
- トップURL：`/docs/index.html`（過去レポ一覧）

の構成にする。リポジトリは1個で過去レポを永続的に蓄積。

### 既存リポとの統合

中村さんは過去にも `pbrain-weekly-report-20240506` のような
週次専用リポジトリを作成している実績あり。
新規 `pbrain-weekly-report` リポジトリに過去レポを取り込むかは別途判断。
当面は新規リポで運用開始 → 必要なら手動マージで蓄積。
