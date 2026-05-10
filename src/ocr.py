"""Gemini OCRでスクショから平均値とランキングを抽出する。"""
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
