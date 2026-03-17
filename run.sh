#!/bin/bash
set -e

# P-Brain 週間レポート ワンコマンド実行
# 使い方: input/screenshots/ に4枚のスクショを格納後、./run.sh

cd "$(dirname "$0")"

REPO_NAME="pbrain-weekly-report"
PAGES_URL="https://nakamura-del.github.io/${REPO_NAME}/"

# --- 1. スクショ確認 ---
PNG_COUNT=$(ls input/screenshots/*.png 2>/dev/null | wc -l | tr -d ' ')
if [ "$PNG_COUNT" -ne 4 ]; then
  echo "❌ スクショが${PNG_COUNT}枚です（4枚必要）"
  exit 1
fi
echo "✅ スクショ4枚確認"

# --- 2. OCR ---
echo "🔍 Gemini OCR 実行中..."
python3 src/ocr/gemini_ocr.py

# --- 3. レポート生成 ---
echo "📊 レポート生成中..."
python3 src/report/weekly_report.py

# --- 4. HTMLファイル特定 ---
REPORT_FILE=$(ls -t output/pbrain_weekly_*.html 2>/dev/null | head -1)
if [ -z "$REPORT_FILE" ]; then
  echo "❌ レポートファイルが見つかりません"
  exit 1
fi
DATE_SUFFIX=$(basename "$REPORT_FILE" .html | grep -o '[0-9]*$')
echo "✅ $(basename "$REPORT_FILE")"

# --- 5. mainにコミット ---
git add -A
git commit -m "Weekly report ${DATE_SUFFIX}" 2>/dev/null || true
git push origin main 2>/dev/null || true

# --- 6. gh-pagesにデプロイ ---
echo "🚀 GitHub Pages デプロイ中..."

# 一時ディレクトリでgh-pages用ファイルを準備
TMPDIR=$(mktemp -d)
cp "$REPORT_FILE" "${TMPDIR}/index.html"

# gh-pagesブランチをチェックアウトしてデプロイ
git stash --include-untracked 2>/dev/null || true
if git rev-parse --verify gh-pages >/dev/null 2>&1; then
  git checkout gh-pages
else
  git checkout --orphan gh-pages
  git rm -rf . 2>/dev/null || true
fi

cp "${TMPDIR}/index.html" index.html
git add index.html
git commit -m "Deploy weekly report ${DATE_SUFFIX}" --allow-empty
git push origin gh-pages --force

# mainに戻る
git checkout main
git stash pop 2>/dev/null || true
rm -rf "$TMPDIR"

# --- 7. 完了 ---
echo ""
echo "============================================"
echo "✅ レポート公開完了！"
echo "🔗 ${PAGES_URL}"
echo "============================================"
