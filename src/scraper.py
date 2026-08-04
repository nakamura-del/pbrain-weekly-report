"""P-Brainから2画面（P4/S20 × 先週）のスクショを取得する。

サーバー負荷を抑えるため safe-data-fetch ルールに準拠する:
- 同時接続1（逐次実行のみ・並列禁止）
- リクエスト間隔 最低3秒
- ページ遷移タイムアウト30秒
- 失敗時は最大3回・指数バックオフ(3,9,27秒)で再試行
- HTTP 429/503 を検知したら即停止（自動リトライで押し切らない）
- 実行後にリクエスト数・所要時間などを報告
"""
import asyncio
import re
import time
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

# ── safe-data-fetch 準拠パラメータ ─────────────────────────────
NAV_TIMEOUT_MS = 30000        # タイムアウト30秒
MAX_RETRY = 3                 # 最大3回
REQUEST_INTERVAL_SEC = 3      # リクエスト間隔 最低3秒
STOP_STATUSES = {429, 503}    # 過負荷応答 → 即停止

# 実行後報告用メトリクス
_metrics = {"requests": 0, "errors": 0, "durations": []}
_last_request_at = 0.0


class ServerOverloadError(RuntimeError):
    """HTTP 429/503。safe-data-fetch規定により再試行せず即停止する。"""


class PeriodMismatchError(RuntimeError):
    """画面の既定期間が想定集計週と一致しない（仕様書v2 §2-4/§10）。

    月曜以外の実行や、P-Brain側の既定期間仕様変更で発生しうる。
    誤った週のデータを正しい週として公開しないよう、組み立て前に中断する。
    """


def _norm_date(s) -> str:
    """日付表記のゆれ(/,-,空白)を除去して数字8桁で比較できるようにする。"""
    return re.sub(r"\D", "", str(s or ""))


async def _pace():
    """前回リクエストから最低 REQUEST_INTERVAL_SEC 秒空ける（sleep必須）。"""
    global _last_request_at
    wait = REQUEST_INTERVAL_SEC - (time.monotonic() - _last_request_at)
    if wait > 0:
        await asyncio.sleep(wait)
    _last_request_at = time.monotonic()


async def _safe_goto(page, url):
    """safe-data-fetch 準拠のページ遷移。

    3秒間隔を空け、30秒タイムアウト、失敗は指数バックオフ(3,9,27秒)で最大3回。
    HTTP 429/503 は即停止（自動リトライで押し切らない）。
    """
    for attempt in range(1, MAX_RETRY + 1):
        await _pace()
        t0 = time.monotonic()
        try:
            resp = await page.goto(url, timeout=NAV_TIMEOUT_MS, wait_until="load")
            _metrics["requests"] += 1
            _metrics["durations"].append(time.monotonic() - t0)
            status = resp.status if resp else None
            if status in STOP_STATUSES:
                _metrics["errors"] += 1
                raise ServerOverloadError(
                    f"サーバー過負荷応答 HTTP {status} を検知。"
                    f"safe-data-fetch規定により即停止: {url}"
                )
            return resp
        except ServerOverloadError:
            raise  # 429/503 は再試行しない
        except Exception as e:
            _metrics["errors"] += 1
            if attempt == MAX_RETRY:
                raise RuntimeError(
                    f"{MAX_RETRY}回失敗のため中断: {url} ({type(e).__name__}: {e})"
                ) from e
            wait = 3 ** attempt  # 3 → 9 → 27秒
            print(f"  遷移失敗 {attempt}/{MAX_RETRY}（{type(e).__name__}）… {wait}s待機して再試行")
            await asyncio.sleep(wait)


async def login(page):
    await _safe_goto(page, PBRAIN_URL)
    await page.wait_for_load_state("networkidle", timeout=NAV_TIMEOUT_MS)
    await page.fill(SELECTORS["login_id"], PBRAIN_ID)
    await page.fill(SELECTORS["login_pw"], PBRAIN_PW)
    await _pace()  # ログインPOST前にも3秒間隔を確保
    t0 = time.monotonic()
    await page.click(SELECTORS["login_btn"])
    await page.wait_for_load_state("networkidle", timeout=NAV_TIMEOUT_MS)
    _metrics["requests"] += 1
    _metrics["durations"].append(time.monotonic() - t0)


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


def _report():
    """safe-data-fetch: 実行後にリクエスト数・所要時間などを報告する。"""
    durs = _metrics["durations"]
    avg = sum(durs) / len(durs) if durs else 0.0
    total = sum(durs)
    print(
        f"[データ取得サマリ] 総リクエスト={_metrics['requests']} / "
        f"エラー={_metrics['errors']} / 合計応答={total:.1f}s / "
        f"平均応答={avg:.1f}s / 次回再開=不要(固定2画面・差分は前週data.json参照)"
    )


async def collect(date_str: str) -> dict:
    """先週分のスクショ2枚(P4/S20)を取得して保存パスを返す。

    ショートカット(P4/S20レポート用)は「前日までの直近7日間」設定なので、
    月曜朝に開くだけで先週(月〜日)が既定表示される。日付操作は一切しない。
    先々週は前週保存の data.json を参照するためスクレイプ不要。
    """
    out_dir = SCREENSHOT_DIR / date_str
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = {}

    # 想定集計週（直近完了週の月〜日）。画面既定期間がこれと一致するか照合する。
    weeks = get_week_ranges()
    last_monday, last_sunday = weeks["lastweek"]
    exp_start_h = last_monday.strftime("%Y/%m/%d")
    exp_end_h = last_sunday.strftime("%Y/%m/%d")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1920, "height": 1080})
        page = await context.new_page()
        page.set_default_timeout(NAV_TIMEOUT_MS)

        try:
            await login(page)

            for sid, url in [("p4", BOOKMARK_URLS["p4"]), ("s20", BOOKMARK_URLS["s20"])]:
                await _safe_goto(page, url)  # 3秒間隔・30秒TO・再試行・429/503即停止を内包
                await page.wait_for_load_state("networkidle", timeout=NAV_TIMEOUT_MS)
                await _wait_ajax_idle(page)
                await page.wait_for_selector(SELECTORS["table_ready"], state="visible")
                await page.wait_for_timeout(2000)

                start = await page.input_value(SELECTORS["term_start"])
                end = await page.input_value(SELECTORS["term_end"])

                # 仕様§2-4/§10: 画面の既定期間が想定集計週と一致するか検証。
                # 不一致（月曜以外の実行・既定期間仕様変更など）は組み立て前に中断する。
                if (_norm_date(start), _norm_date(end)) != (
                    last_monday.strftime("%Y%m%d"), last_sunday.strftime("%Y%m%d")
                ):
                    raise PeriodMismatchError(
                        f"{sid}: 画面期間 {start}〜{end} が想定 {exp_start_h}〜{exp_end_h} と不一致。"
                        "月曜実行か、P-Brain既定期間の仕様変更を確認してください。"
                    )

                paths[f"{sid}_lastweek"] = await _capture(page, out_dir / f"{sid}_lastweek.png")
                print(f"OK {sid} 先週 (既定期間 {start}〜{end}) -> {paths[f'{sid}_lastweek']}")
        finally:
            await browser.close()
            _report()

    return paths


if __name__ == "__main__":
    # スタンドアロン実行: スクショ取得のみテスト
    today = datetime.now()
    weeks = get_week_ranges(today)
    date_str = weeks["lastweek"][1].strftime("%Y-%m-%d")
    print(f"scraper standalone test: 期間末 {date_str}")
    paths = asyncio.run(collect(date_str))
    print(f"\nresult: {paths}")
