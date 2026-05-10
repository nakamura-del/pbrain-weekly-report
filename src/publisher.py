"""レポートHTMLを docs/YYYY-MM-DD/ に保存し、git push して公開URLを返す。"""
import subprocess
from pathlib import Path
from .config import GITHUB_USERNAME, GITHUB_REPO, DOCS_DIR


def publish(report_html: str, date_str: str) -> str:
    out_dir = DOCS_DIR / date_str
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "index.html").write_text(report_html, encoding="utf-8")

    update_index_page()

    subprocess.run(["git", "add", "docs/"], check=True)
    subprocess.run(["git", "commit", "-m", f"weekly report {date_str}"], check=True)
    subprocess.run(["git", "push"], check=True)

    url = f"https://{GITHUB_USERNAME}.github.io/{GITHUB_REPO}/{date_str}/"
    print(f"Published: {url}")
    return url


def update_index_page():
    """docs/直下の日付ディレクトリを一覧化"""
    dirs = sorted(
        [d.name for d in DOCS_DIR.iterdir() if d.is_dir()],
        reverse=True,
    )
    items = "\n".join(f'<li><a href="{d}/">{d}</a></li>' for d in dirs)
    html = f"""<!DOCTYPE html>
<html lang="ja"><head><meta charset="UTF-8">
<title>P-Brain 週間レポート一覧</title>
<style>body{{font-family:sans-serif;max-width:600px;margin:2em auto;}}</style>
</head><body><h1>P-Brain 週間レポート一覧</h1>
<ul>{items}</ul></body></html>"""
    (DOCS_DIR / "index.html").write_text(html, encoding="utf-8")
