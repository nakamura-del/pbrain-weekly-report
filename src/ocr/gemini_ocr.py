#!/usr/bin/env python3
"""Gemini OCR for P-Brain screenshots using REST API."""

import os
import sys
import json
import glob
import base64
import requests

API_KEY = os.environ.get("GEMINI_API_KEY", "")
MODEL = "gemini-2.5-flash"
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={API_KEY}"

PROMPT = """
この画像はパチンコ・パチスロ業界のデータ分析ツール「P-Brain」のスクリーンショットです。
以下の情報をJSON形式で正確に抽出してください。

## 抽出項目

1. **header** (ヘッダー情報):
   - `period_start`: 期間の開始日 (YYYY/MM/DD形式)
   - `period_end`: 期間の終了日 (YYYY/MM/DD形式)
   - `type`: 種別 ("4円パチンコ" or "20円スロット") — 種別欄で「4~」にチェックなら"4円パチンコ"、「20~」にチェックなら"20円スロット"

2. **summary** (平均/合計 行のデータ、テーブル右側の数値列を左から順に):
   - `uchi_komi`: 打込 (整数)
   - `tama_tanka`: 玉単価 (小数) ※打込の右隣
   - `tama_arari`: 玉粗利 (小数) ※玉単価の右隣
   - `dai_uriage`: 台売上 (整数)
   - `dai_arari`: 台粗利 (整数)
   - `rieki_ritsu`: 利益率 (小数、%の数値部分のみ。例: 16.41)

3. **machines** (機種データの配列、上から順に全行):
   各機種について:
   - `rank`: 表示順位 (1始まり)
   - `type`: 機種タイプ (ハイミドル、ミドル、ライトミドル、ライト、甘デジ、海、スマスロART/AT、ジャガー等)
   - `name`: 機種名 (正確に。φ○×☆・等の特殊記号もそのまま保持)
   - `release_date`: 発売日 (YYYY/MM/DD形式)
   - `elapsed_weeks`: 経過週 (整数)
   - `uchi_komi`: 打込 (整数)
   - `tama_tanka`: 玉単価 (小数) ※打込の右隣
   - `tama_arari`: 玉粗利 (小数) ※玉単価の右隣
   - `dai_uriage`: 台売上 (整数)
   - `dai_arari`: 台粗利 (整数)
   - シェア列（右側4列）: **必ず左から順に以下の通り読み取ること**
     - `uchi_komi_share`: 打込シェア（右側4列の1列目）
     - `dai_uriage_share`: 台売上シェア（右側4列の2列目）
     - `dai_arari_share`: 台粗利シェア（右側4列の3列目）
     - `dai_count_share`: 台数シェア（右側4列の4列目＝最右列）

## ★★ シェア列の読み取り順序（最重要）★★
P-Brainのテーブル右側にある4つのシェア列は、左から順に：
  1列目 = 打込シェア (uchi_komi_share)
  2列目 = 台売上シェア (dai_uriage_share)
  3列目 = 台粗利シェア (dai_arari_share)
  4列目 = 台数シェア (dai_count_share)
この順序を絶対に間違えないこと。台売上シェアが台粗利シェアより左にある。

## 注意事項
- 数値のカンマ区切りは除去して数値として返すこと
- シェアや利益率の%記号は除去して数値のみ返すこと
- 機種名の特殊記号(φ、○、×、☆、・等)はそのまま保持すること
- 読み取れない値はnullとすること
- 全ての行を漏れなく抽出すること（表示されている全機種）
- 機種名は画像のテキストを1文字ずつ正確に読み取ること。パチンコ・パチスロの実在する機種名であることを考慮し、類似文字の誤認識に注意すること（例: 「えとたま」を「とあるまえ」と読み間違えない）

JSONのみを返してください。説明文は不要です。
"""


def ocr_screenshot(image_path):
    """Process a single screenshot with Gemini OCR via REST API."""
    with open(image_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode("utf-8")

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": PROMPT},
                    {
                        "inline_data": {
                            "mime_type": "image/png",
                            "data": image_data,
                        }
                    },
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.1,
            "responseMimeType": "application/json",
        },
    }

    resp = requests.post(API_URL, json=payload, timeout=120)
    resp.raise_for_status()
    result = resp.json()

    text = result["candidates"][0]["content"]["parts"][0]["text"]
    return json.loads(text)


# 機種名の既知の誤認識を修正するマッピング
NAME_CORRECTIONS = {
    "Pとあるまえ2SE": "Pえとたま2SE",
    "Pとあるまえと2SE": "Pえとたま2SE",
}


def postprocess(data):
    """OCR結果の後処理: 既知の誤認識を修正"""
    for m in data.get("machines", []):
        name = m.get("name", "")
        if name in NAME_CORRECTIONS:
            corrected = NAME_CORRECTIONS[name]
            print(f"  [fix] {name} → {corrected}")
            m["name"] = corrected
    return data


def process_all_screenshots(screenshots_dir):
    """Process all screenshots in directory."""
    files = sorted(glob.glob(os.path.join(screenshots_dir, "*.png")))
    if not files:
        print("No PNG files found in", screenshots_dir)
        sys.exit(1)

    results = []
    for f in files:
        print(f"Processing: {os.path.basename(f)}")
        data = ocr_screenshot(f)
        data["_source_file"] = os.path.basename(f)
        data = postprocess(data)
        header = data.get("header", {})
        print(f"  → {header.get('type', '?')} | {header.get('period_start', '?')}〜{header.get('period_end', '?')}")
        machine_count = len(data.get("machines", []))
        print(f"  → {machine_count} machines extracted")
        results.append(data)

    return results


if __name__ == "__main__":
    screenshots_dir = os.path.join(os.path.dirname(__file__), "../../input/screenshots")
    results = process_all_screenshots(screenshots_dir)

    output_path = os.path.join(os.path.dirname(__file__), "../../data/ocr_results.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\nSaved to {output_path}")
