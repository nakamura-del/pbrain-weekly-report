"""エントリーポイント: 4スクショ取得 → OCR → HTML → 公開 を一気通貫で実行。"""
import asyncio
from datetime import datetime
from . import scraper, ocr, report_builder, publisher
from .config import get_week_ranges


async def run():
    today = datetime.now()
    weeks = get_week_ranges(today)
    last_end = weeks["lastweek"][1]
    date_str = last_end.strftime("%Y-%m-%d")
    print(f"P-Brain週間レポート生成開始: 期間末 {date_str}")

    paths = await scraper.collect(date_str)

    print("OCR処理中...")
    data = {sid: ocr.extract(path) for sid, path in paths.items()}

    print("レポート組み立て中...")
    html = report_builder.build(data, date_str)

    print("GitHubへpush...")
    url = publisher.publish(html, date_str)

    print(f"\n完了\n公開URL: {url}")


if __name__ == "__main__":
    asyncio.run(run())
