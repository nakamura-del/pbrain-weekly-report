"""P-Brainから4画面（P4/S20 × 先週/先々週）のスクショを取得する。"""
import asyncio
from playwright.async_api import async_playwright
from datetime import datetime
from .config import (
    PBRAIN_URL, PBRAIN_ID, PBRAIN_PW,
    SCREENSHOT_DIR, get_week_ranges,
)

# 確定済みセレクタ（probe_dom.py での実機調査結果）
SELECTORS = {
    "login_id":   "#LoginId",
    "login_pw":   "#LoginPassword",
    "login_btn":  "#btn_home_login",
    "term_start": "#ZAnalysisShareConditionTermStart",
    "term_end":   "#ZAnalysisShareConditionTermEnd",
    "search_btn": "#SearchButton",
    "table_ready": "#shareList",
}

# ブックマーク（check_bookmarks.py で確定済）
BOOKMARK_URLS = {
    "p4":  "https://www.p-brain777.com/ZAnalysisShare/index?favorite=140374",
    "s20": "https://www.p-brain777.com/ZAnalysisShare/index?favorite=140375",
}


async def login(page):
    await page.goto(PBRAIN_URL)
    await page.wait_for_load_state("networkidle")
    await page.fill(SELECTORS["login_id"], PBRAIN_ID)
    await page.fill(SELECTORS["login_pw"], PBRAIN_PW)
    await page.click(SELECTORS["login_btn"])
    await page.wait_for_load_state("networkidle")


async def _wait_ajax_idle(page, timeout_ms=60000):
    """jQuery AJAX が完了するまで待つ（blockUI オーバーレイの消失と同義）"""
    await page.wait_for_function(
        "() => !window.jQuery || window.jQuery.active === 0",
        timeout=timeout_ms,
    )


KEEP_ROWS = 20  # 平均行 + TOP15 + 余裕


async def _trim_for_capture(page):
    """OCR向けにスクショサイズを抑える: shareList の末尾行を非表示にする"""
    await page.evaluate("""(keep) => {
        const tbody = document.querySelector('#shareList tbody');
        if (!tbody) return;
        const rows = Array.from(tbody.rows);
        rows.slice(keep).forEach(r => r.style.display = 'none');
    }""", KEEP_ROWS)


async def _capture(page, out_path):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    await _trim_for_capture(page)
    await page.screenshot(path=str(out_path), full_page=True)
    return out_path


async def collect(date_str: str) -> dict:
    """先週分のスクショ2枚(P4/S20)を取得して保存パスを返す。

    ショートカット(P4/S20レポート用)は「前日までの直近7日間」設定なので、
    月曜朝に開くだけで先週(月〜日)が既定表示される。日付操作は一切しない。
    先々週は前週保存の data.json を参照するためスクレイプ不要。
    """
    out_dir = SCREENSHOT_DIR / date_str
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = {}

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1920, "height": 1080})
        page = await context.new_page()

        await login(page)

        for sid, url in [("p4", BOOKMARK_URLS["p4"]), ("s20", BOOKMARK_URLS["s20"])]:
            await page.goto(url)
            await page.wait_for_load_state("networkidle")
            await _wait_ajax_idle(page)
            await page.wait_for_selector(SELECTORS["table_ready"], state="visible")
            await page.wait_for_timeout(2000)

            start = await page.input_value(SELECTORS["term_start"])
            end = await page.input_value(SELECTORS["term_end"])
            paths[f"{sid}_lastweek"] = await _capture(page, out_dir / f"{sid}_lastweek.png")
            print(f"OK {sid} 先週 (既定期間 {start}〜{end}) -> {paths[f'{sid}_lastweek']}")

        await browser.close()

    return paths


if __name__ == "__main__":
    # スタンドアロン実行: スクショ取得のみテスト
    today = datetime.now()
    weeks = get_week_ranges(today)
    date_str = weeks["lastweek"][1].strftime("%Y-%m-%d")
    print(f"scraper standalone test: 期間末 {date_str}")
    paths = asyncio.run(collect(date_str))
    print(f"\nresult: {paths}")
