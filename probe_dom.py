"""DOM調査用スクリプト（一時利用）。

ヘッドフルでP-Brainにログイン → P4/S20両画面を訪問し、
HTML・スクショ・カレンダー候補要素のサマリを probe/ に保存する。

使い方:
    cd ~/Desktop/claudecode用/pbrain-weekly-report
    python3 probe_dom.py
"""
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright
from src.config import PBRAIN_URL, PBRAIN_ID, PBRAIN_PW
from src.scraper import BOOKMARK_URLS, SELECTORS

OUT = Path(__file__).parent / "probe"
OUT.mkdir(exist_ok=True)


async def dump(page, name: str):
    """現在のページのHTML/スクショ/カレンダー候補を保存"""
    html = await page.content()
    (OUT / f"{name}.html").write_text(html, encoding="utf-8")
    await page.screenshot(path=str(OUT / f"{name}.png"), full_page=True)
    print(f"  saved: probe/{name}.html, probe/{name}.png")

    # カレンダー候補の抽出
    candidates = await page.evaluate("""() => {
        const result = {tables: [], dateInputs: [], buttons: [], selects: []};

        document.querySelectorAll('table').forEach((t, i) => {
            result.tables.push({
                index: i, id: t.id, class: t.className,
                rows: t.rows.length,
                headers: Array.from(t.querySelectorAll('thead th, tr:first-child th, tr:first-child td'))
                    .slice(0, 16).map(th => th.textContent.trim().slice(0, 20)),
            });
        });

        document.querySelectorAll('input').forEach(el => {
            const idClass = (el.id + ' ' + el.className + ' ' + (el.name || '')).toLowerCase();
            const placeholder = (el.placeholder || '');
            if (el.type === 'date' || idClass.match(/date|period|calendar|from|to|start|end|kikan|begin|year|month|day|ymd|datepicker/i) || placeholder.match(/年|月|日|期間|から|まで/)) {
                result.dateInputs.push({
                    type: el.type, id: el.id, name: el.name, class: el.className,
                    value: (el.value || '').slice(0, 40),
                    placeholder: placeholder.slice(0, 40),
                });
            }
        });

        document.querySelectorAll('button, a, input[type=button], input[type=submit]').forEach(el => {
            const text = (el.textContent || el.value || '').trim();
            const idClass = (el.id + ' ' + el.className).toLowerCase();
            if (text.match(/検索|表示|期間|更新|search|update|filter/i) || idClass.match(/search|filter|btn_search|btn_disp|kensaku/i)) {
                result.buttons.push({
                    tag: el.tagName, id: el.id, class: el.className,
                    text: text.slice(0, 40),
                });
            }
        });

        document.querySelectorAll('select').forEach(el => {
            const idClass = (el.id + ' ' + el.className + ' ' + (el.name || '')).toLowerCase();
            if (idClass.match(/period|kikan|date|year|month|term/i)) {
                result.selects.push({
                    id: el.id, name: el.name, class: el.className,
                    options: Array.from(el.options).slice(0, 8).map(o => o.textContent.trim()),
                });
            }
        });

        return result;
    }""")

    summary_path = OUT / f"{name}.summary.json"
    summary_path.write_text(json.dumps(candidates, ensure_ascii=False, indent=2))

    print(f"  tables: {len(candidates['tables'])}")
    for t in candidates["tables"][:5]:
        print(f"    [{t['index']}] id={t['id']!r} rows={t['rows']} class={t['class'][:40]!r}")
        if t["headers"]:
            print(f"        headers: {t['headers']}")
    print(f"  date inputs: {len(candidates['dateInputs'])}")
    for d in candidates["dateInputs"][:10]:
        print(f"    {d}")
    print(f"  search buttons: {len(candidates['buttons'])}")
    for b in candidates["buttons"][:8]:
        print(f"    {b}")
    print(f"  selects: {len(candidates['selects'])}")
    for s in candidates["selects"][:8]:
        print(f"    {s}")


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        ctx = await browser.new_context(viewport={"width": 1920, "height": 1080})
        page = await ctx.new_page()

        print("[1] login...")
        await page.goto(PBRAIN_URL)
        await page.wait_for_load_state("networkidle")
        await page.fill(SELECTORS["login_id"], PBRAIN_ID)
        await page.fill(SELECTORS["login_pw"], PBRAIN_PW)
        await page.click(SELECTORS["login_btn"])
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(2)
        print(f"  url after login: {page.url}")

        for name, url in BOOKMARK_URLS.items():
            print(f"\n[2] visit {name}: {url}")
            await page.goto(url)
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(4)  # テーブル描画完了待ち
            await dump(page, name)

        print("\n[3] visual inspection: keeping browser open 30s...")
        await asyncio.sleep(30)
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
