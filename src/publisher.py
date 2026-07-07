"""レポートHTMLを docs/YYYY-MM-DD/ に保存し、git push して公開URLを返す。"""
import json
import subprocess
from pathlib import Path
from .config import GITHUB_USERNAME, GITHUB_REPO, DOCS_DIR


def load_prev_data(prev_date_str: str) -> dict:
    """前週(=先々週)の確定ランキングを読み込む。無ければ空(初回・欠落時)。"""
    p = DOCS_DIR / prev_date_str / "data.json"
    if not p.exists():
        print(f"注意: 前週データ {p} が無いため、順位変動は全て新規扱いになります")
        return {"p4": [], "s20": []}
    return json.loads(p.read_text(encoding="utf-8"))


def publish(report_html: str, date_str: str, snapshot: dict = None) -> str:
    out_dir = DOCS_DIR / date_str
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "index.html").write_text(report_html, encoding="utf-8")

    # 来週の「先々週」参照用に確定ランキングを保存
    if snapshot is not None:
        (out_dir / "data.json").write_text(
            json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    update_index_page()

    subprocess.run(["git", "add", "docs/"], check=True)
    subprocess.run(["git", "commit", "-m", f"weekly report {date_str}"], check=True)
    subprocess.run(["git", "push"], check=True)

    url = f"https://{GITHUB_USERNAME}.github.io/{GITHUB_REPO}/{date_str}/"
    print(f"Published: {url}")
    return url


# これ以前のレポートは一覧に出さない（6/28以前は不要）
MIN_REPORT_DATE = "2026-07-05"


def _report_dirs():
    """一覧対象の日付ディレクトリ（MIN_REPORT_DATE以降、新しい順）"""
    return sorted(
        [
            d.name for d in DOCS_DIR.iterdir()
            if d.is_dir() and d.name >= MIN_REPORT_DATE and (d / "index.html").exists()
        ],
        reverse=True,
    )


def update_index_page():
    """トップ(index.html)＝最新レポートへ直接リダイレクト、
    過去分選択画面(archive.html)＝7/5以降の一覧 を生成する。"""
    dirs = _report_dirs()
    latest = dirs[0] if dirs else None

    # 1) トップ: 最新レポートへ即リダイレクト（開いたら最新が直接表示される）
    if latest:
        redirect = (
            '<!DOCTYPE html><html lang="ja"><head><meta charset="UTF-8">'
            f'<meta http-equiv="refresh" content="0; url=./{latest}/">'
            '<title>P-Brain 週間レポート</title>'
            f'<script>location.replace("./{latest}/");</script>'
            '</head><body style="font-family:sans-serif;background:#0f1117;color:#e2e8f0;">'
            f'最新レポートへ移動中… <a href="./{latest}/" style="color:#4f9cf9;">こちら</a>'
            '</body></html>'
        )
        (DOCS_DIR / "index.html").write_text(redirect, encoding="utf-8")

    # 2) 過去分選択画面（ダークテーマ・7/5以降のみ）
    items = "\n".join(
        f'    <li><a href="./{d}/">{d}</a></li>' for d in dirs
    ) or "    <li>レポートはまだありません</li>"
    archive = f"""<!DOCTYPE html>
<html lang="ja"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>P-Brain 週間レポート 過去一覧</title>
<style>
  body {{ background:#0f1117; color:#e2e8f0; font-family:'Hiragino Kaku Gothic ProN','Noto Sans JP',sans-serif; max-width:640px; margin:0 auto; padding:32px 20px 64px; }}
  h1 {{ font-size:20px; border-bottom:2px solid #2e3347; padding-bottom:12px; margin-bottom:8px; }}
  p.sub {{ color:#8892a4; font-size:13px; margin-bottom:24px; }}
  ul {{ list-style:none; padding:0; }}
  li {{ margin:0 0 10px; }}
  li a {{ display:block; padding:14px 18px; background:#1a1d27; border:1px solid #2e3347; border-radius:10px; color:#4f9cf9; text-decoration:none; font-size:16px; font-weight:600; transition:background .1s; }}
  li a:hover {{ background:#22263a; }}
</style>
</head><body>
  <h1>📊 P-Brain 週間レポート 過去一覧</h1>
  <p class="sub">週末日付（先週の日曜）で表示。新しい順。</p>
  <ul>
{items}
  </ul>
</body></html>"""
    (DOCS_DIR / "archive.html").write_text(archive, encoding="utf-8")
