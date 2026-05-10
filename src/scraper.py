"""P-Brainから4画面（P4/S20 × 先週/先々週）のスクショを取得する。"""
import asyncio
from playwright.async_api import async_playwright
from datetime import datetime
from .config import (
    PBRAIN_URL, PBRAIN_ID, PBRAIN_PW,
    SCREENSHOT_DIR, get_week_ranges,
)

# 既知のセレクタ（pbrain_auto_report.py の login() で実績あり）
SELECTORS = {
    "login_id": "#LoginId",
    "login_pw": "#LoginPassword",
    "login_btn": "#btn_home_login",
    # カレンダーUI関連は実画面確認後に確定する
    "calendar_start": None,    # TODO: DOM調査で確定
    "calendar_end": None,      # TODO: DOM調査で確定
    "search_btn": None,        # TODO: DOM調査で確定
    "table_ready": None,       # TODO: テーブル描画完了の目印
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


async def select_date_range(page, start_date, end_date):
    """カレンダーUIで期間を選択 → 検索ボタン押下。

    ⚠️ DOM調査でセレクタ確定後に実装する。
    """
    raise NotImplementedError("calendar selectors not yet identified")


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
        await login(page)

        # 2. P4 × 先週（デフォルト期間が直近完了週の想定）
        await page.goto(BOOKMARK_URLS["p4"])
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(2000)
        path = out_dir / "p4_lastweek.png"
        await page.screenshot(path=str(path), full_page=True)
        paths["p4_lastweek"] = path
        print(f"OK P4 先週 -> {path}")

        # 3. P4 × 先々週
        await select_date_range(page, two_start, two_end)
        path = out_dir / "p4_2weeksago.png"
        await page.screenshot(path=str(path), full_page=True)
        paths["p4_2weeksago"] = path
        print(f"OK P4 先々週 -> {path}")

        # 4. S20 × 先週
        await page.goto(BOOKMARK_URLS["s20"])
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(2000)
        path = out_dir / "s20_lastweek.png"
        await page.screenshot(path=str(path), full_page=True)
        paths["s20_lastweek"] = path
        print(f"OK S20 先週 -> {path}")

        # 5. S20 × 先々週
        await select_date_range(page, two_start, two_end)
        path = out_dir / "s20_2weeksago.png"
        await page.screenshot(path=str(path), full_page=True)
        paths["s20_2weeksago"] = path
        print(f"OK S20 先々週 -> {path}")

        await browser.close()

    return paths
