"""Gemini OCRでスクショから平均値とランキングを抽出する。"""
import google.generativeai as genai
import json
import re
from PIL import Image
from .config import GEMINI_API_KEY

genai.configure(api_key=GEMINI_API_KEY)


OCR_TEXT_CORRECTIONS = {
    "慶極推理": "虚構推理",
    "袋炎ノ消防隊": "炎炎ノ消防隊",
    "恐襲ノ": "最恐領域",
    "ポッチーと一発おだてて": "ポチッと一発おだて",
    "女神カフェテラスJL2": "女神のカフェテラスJLZ",
    "ワンパンマン2～正義執行 LM10": "P大海物語5スペシャルELTA",
}


def apply_corrections(data):
    for row in data.get("ranking", []):
        kishu = row.get("kishu", "")
        for wrong, correct in OCR_TEXT_CORRECTIONS.items():
            if wrong in kishu:
                kishu = kishu.replace(wrong, correct)
        row["kishu"] = kishu
    return data


PROMPT = """
あなたはパチンコ・パチスロ業界の週間ランキング表を読み取る専門OCRエンジンです。
以下の手順で厳密に処理してください。

【処理手順】
1. まず画像全体を確認し、表の上部にある「全体平均」エリアと
   下部のランキング表を識別する
2. 全体平均から6項目（打込/玉粗利/台粗利/台売上/玉単価/利益率）を抽出
3. ランキング表の上位20行（存在する分だけ、最大20行）を行ごとに以下を抽出：
   順位、機種名、発売日、経過週、打込、玉粗利、台粗利、台売上、玉単価、
   打込シェア、台粗利シェア、台売上シェア、台数シェア
   ※台数シェアが 0.00% の行も飛ばさず必ず抽出すること（後段の除外判定で使う）。

★★ シェア列の読み取り順序（最重要）★★
P-Brainのテーブル右側にある4つのシェア列は、左から順に：
  1列目 = 打込シェア (uchikomi_share)
  2列目 = 台売上シェア (dai_uriage_share)
  3列目 = 台粗利シェア (dai_arari_share)
  4列目 = 台数シェア (daisuu_share)
台売上シェアが台粗利シェアより左にある。この順序を絶対に間違えないこと。

【機種名抽出の厳格ルール】
パチンコ・パチスロ機種名は実在する正式名称が決まっています。
以下のような誤認識を絶対に避けてください：

✗誤: 慶極推理 → ✓正: 虚構推理
✗誤: 袋炎ノ消防隊 → ✓正: 炎炎ノ消防隊
✗誤: 恐襲ノ → ✓正: 最恐領域
✗誤: ポッチーと一発おだてて → ✓正: ポチッと一発おだて
✗誤: 女神カフェテラスJL2 → ✓正: 女神のカフェテラスJLZ

【既知の正式機種名リスト（一部）】
パチンコ:
- eリコリス・リコイル
- eフィーバーキン肉マン
- eエイティシックス
- eリング 最恐領域
- e仮面ライダー電王
- e転生したらスライムだった件
- e東京喰種
- e女神のカフェテラス
- e新世紀エヴァンゲリオン
- e大海物語5スペシャル
- eワンパンマン2
- P大海物語5
- P野生の王国5
- Pポチッと一発おだてブタ

スロット:
- L/ミリオンゴッド/CX
- L甲鉄城のカバネリ 海門決戦
- L虚構推理
- L/真打吉宗/
- Lうみねこのなく頃に
- Lアニマルスロットドッチ
- SBニューキングハナハナ
- SマイジャグラーV
- Lスマスロ攻殻機動隊
- L機動戦士ガンダムユニコーン
- S/沖ドキ！BLACK/
- L東京喰種
- Sドラゴンハナハナ
- LB異世界かるてっと
- L炎炎ノ消防隊

機種名の前のアルファベット記号（e/P/L/S/SB/LB）と末尾の型番は重要なので
省略しないこと。読み取れない部分があっても、上記リストの正式名称と
照合して最も近いものを採用してください。

【数値抽出ルール】
- カンマ・%記号・¥記号は除いた数値のみ
- マイナス値は負号付きで（例: -1204）
- 小数点を持つ値は小数のまま（例: 0.413, 17.73）

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
      "kishu": "...",
      "hatsubaibi": "YYYY/MM/DD",
      "keika_shu": 0,
      "uchikomi": 0,
      "tama_arari": 0.0,
      "dai_arari": 0,
      "dai_uriage": 0,
      "tama_tanka": 0.0,
      "uchikomi_share": 0.0,
      "dai_arari_share": 0.0,
      "dai_uriage_share": 0.0,
      "daisuu_share": 0.0
    }
  ]
}
"""


MODEL_NAME = "gemini-2.5-pro"


def preprocess_image(image_path):
    img = Image.open(image_path)
    w, h = img.size
    img = img.resize((w * 2, h * 2), Image.LANCZOS)
    out_path = str(image_path).replace(".png", "_hires.png")
    img.save(out_path, "PNG")
    return out_path


def _parse_json_response(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"^```json\s*|\s*```$", "", text, flags=re.MULTILINE)
    return json.loads(text)


import time
from google.api_core.exceptions import DeadlineExceeded, ServiceUnavailable, InternalServerError

# 2.5-proは大きな表のJSON生成に時間がかかり、既定デッドラインだと504になる。
# 明示タイムアウトを付け、瞬間的な504/503はバックオフ再試行で吸収する。
REQUEST_TIMEOUT = 300
MAX_RETRIES = 3


def call_gemini(image_path, prompt: str) -> dict:
    model = genai.GenerativeModel(MODEL_NAME)
    img = genai.upload_file(str(image_path))
    last_err = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = model.generate_content(
                [prompt, img],
                request_options={"timeout": REQUEST_TIMEOUT},
            )
            return _parse_json_response(response.text)
        except (DeadlineExceeded, ServiceUnavailable, InternalServerError) as e:
            last_err = e
            if attempt == MAX_RETRIES:
                break
            wait = 3 ** attempt  # 3 → 9 → 27秒（safe-data-fetch 指数バックオフ準拠）
            print(f"  OCR再試行 {attempt}/{MAX_RETRIES}（{type(e).__name__}）… {wait}s待機")
            time.sleep(wait)
    raise last_err


def extract_with_verification(image_path) -> dict:
    img_path = preprocess_image(image_path)
    first_result = call_gemini(img_path, PROMPT)
    verify_prompt = (
        "以下のJSON結果を、添付画像のランキング表と照合してください。\n"
        "特に機種名の漢字・カタカナ・型番が正確かを確認し、\n"
        "間違いがあれば訂正したJSONを出力してください。\n"
        "既知の正式機種名リストを優先してください。\n\n"
        "元の抽出結果:\n"
        f"{json.dumps(first_result, ensure_ascii=False, indent=2)}\n\n"
        "訂正版JSONのみ出力（コードフェンス禁止）："
    )
    return call_gemini(img_path, verify_prompt)


def extract(image_path) -> dict:
    """スクショ画像から平均値とランキングを抽出"""
    result = extract_with_verification(image_path)
    return apply_corrections(result)
