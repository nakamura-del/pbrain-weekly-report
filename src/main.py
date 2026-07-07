"""エントリーポイント: 4スクショ取得 → OCR → HTML → 公開 を一気通貫で実行。"""
import asyncio
from datetime import datetime
from . import scraper, ocr, report_builder, publisher
from .config import get_week_ranges


async def run():
    today = datetime.now()
    weeks = get_week_ranges(today)
    last_end = weeks["lastweek"][1]
    prev_end = weeks["twoweeksago"][1]
    date_str = last_end.strftime("%Y-%m-%d")
    prev_date_str = prev_end.strftime("%Y-%m-%d")
    print(f"P-Brain週間レポート生成開始: 期間末 {date_str} / 先々週参照 {prev_date_str}")

    # 1) 先週分のスクショ2枚（ショートカット既定＝月〜日、日付操作なし）
    paths = await scraper.collect(date_str)

    print("OCR処理中...")
    cur = {
        "p4": ocr.extract(paths["p4_lastweek"]),
        "s20": ocr.extract(paths["s20_lastweek"]),
    }

    # 2) 先々週は前週保存の data.json を参照（スクレイプしない）
    prev = publisher.load_prev_data(prev_date_str)

    print("レポート組み立て中...")
    html, snapshot = report_builder.build(cur, prev, ref_date=today)

    print("GitHubへpush...")
    url = publisher.publish(html, date_str, snapshot=snapshot)

    print(f"\n完了\n公開URL: {url}")


if __name__ == "__main__":
    asyncio.run(run())
