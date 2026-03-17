#!/bin/bash
set -e

# P-Brain 週間レポート ワンコマンド実行スクリプト
# 使い方: input/screenshots/ に4枚のスクショを格納後、./run.sh を実行

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# --- 1. スクショ確認 ---
PNG_COUNT=$(ls input/screenshots/*.png 2>/dev/null | wc -l | tr -d ' ')
if [ "$PNG_COUNT" -ne 4 ]; then
  echo "❌ input/screenshots/ にPNGファイルが${PNG_COUNT}枚あります（4枚必要）"
  exit 1
fi
echo "✅ スクショ4枚確認"

# --- 2. Gemini OCR ---
echo "🔍 Gemini OCR 実行中..."
python3 src/ocr/gemini_ocr.py
echo "✅ OCR完了"

# --- 3. レポート生成 ---
echo "📊 レポート生成中..."
python3 src/report/weekly_report.py
echo "✅ レポート生成完了"

# --- 4. 生成されたHTMLファイルを特定 ---
REPORT_FILE=$(ls -t output/pbrain_weekly_*.html 2>/dev/null | head -1)
if [ -z "$REPORT_FILE" ]; then
  echo "❌ レポートファイルが見つかりません"
  exit 1
fi
REPORT_NAME=$(basename "$REPORT_FILE" .html)
echo "📄 ${REPORT_FILE}"

# --- 5. GitHub Pages 公開 ---
echo "🚀 GitHub Pages 公開中..."

# gh-pagesブランチにデプロイ
REPO_NAME="pbrain-weekly-report"
DATE_SUFFIX=$(echo "$REPORT_NAME" | grep -o '[0-9]*$')

# リポジトリが存在するか確認、なければ作成
if ! gh repo view "nakamura-del/${REPO_NAME}" &>/dev/null; then
  gh repo create "${REPO_NAME}" --public --description "P-Brain 週間レポート"
  git remote add origin "https://github.com/nakamura-del/${REPO_NAME}.git"
else
  # remoteが未設定なら追加
  if ! git remote get-url origin &>/dev/null; then
    git remote add origin "https://github.com/nakamura-del/${REPO_NAME}.git"
  fi
fi

# mainブランチにレポートをコミット&プッシュ
git add -A
git commit -m "Weekly report ${DATE_SUFFIX}" 2>/dev/null || true

# output/のHTMLをルートにindex.htmlとしてコピー
cp "$REPORT_FILE" output/index.html

# gh-pagesブランチにデプロイ
git stash --include-untracked 2>/dev/null || true
git checkout --orphan gh-pages-tmp 2>/dev/null || git checkout gh-pages-tmp
git rm -rf . 2>/dev/null || true
git stash pop 2>/dev/null || true
cp "$REPORT_FILE" index.html
git add index.html
git commit -m "Deploy weekly report ${DATE_SUFFIX}"
git push origin gh-pages-tmp:gh-pages --force

# mainに戻る
git checkout main 2>/dev/null || git checkout -b main
git stash pop 2>/dev/null || true

# GitHub Pages有効化
gh api repos/nakamura-del/${REPO_NAME}/pages \
  --method POST \
  --field source='{"branch":"gh-pages","path":"/"}' 2>/dev/null || true

PAGES_URL="https://nakamura-del.github.io/${REPO_NAME}/"
echo ""
echo "============================================"
echo "✅ レポート公開完了！"
echo "🔗 ${PAGES_URL}"
echo "============================================"
