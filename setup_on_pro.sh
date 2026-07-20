#!/usr/bin/env bash
# P-Brain週間レポート: 自宅Pro(固定機)への移行セットアップ
# 使い方(Proのターミナルで):
#   1) git clone https://github.com/nakamura-del/pbrain-weekly-report.git ~/pbrain-weekly-report
#   2) Airの .env をこのフォルダへコピー(AirDrop等。中身は秘匿情報)
#   3) bash ~/pbrain-weekly-report/setup_on_pro.sh
#
# ・ユーザー名に依存しない($HOME基準)。Desktop外に置くのでTCC権限問題は起きない。
# ・venvを作り、launchd(毎週月曜8:00)を登録する。Air側の停止はまだ行わない。
set -euo pipefail

REPO_DIR="$HOME/pbrain-weekly-report"
VENV="$REPO_DIR/.venv"
PY="$VENV/bin/python"
PLIST_LABEL="com.tlp.pbrain-weekly"
PLIST="$HOME/Library/LaunchAgents/${PLIST_LABEL}.plist"

echo "==> リポジトリ: $REPO_DIR"
cd "$REPO_DIR"

# 0) 前提コマンド確認 -------------------------------------------------
command -v python3 >/dev/null || { echo "python3 が必要です(brew install python)"; exit 1; }
command -v git     >/dev/null || { echo "git が必要です"; exit 1; }
if ! command -v gh >/dev/null; then
  echo "⚠ gh(GitHub CLI)未検出。push認証のため 'brew install gh && gh auth login' を先に実行してください。"
fi

# 1) .env の存在チェック(秘匿情報はgitに乗らないので手動配置が必須) ----
if [ ! -f "$REPO_DIR/.env" ]; then
  echo "✗ .env がありません。Airの ~/pbrain-weekly-report/.env をこのフォルダへコピーしてください。"
  echo "  必要キー: PBRAIN_URL / PBRAIN_ID / PBRAIN_PW / GEMINI_API_KEY / GITHUB_USERNAME / GITHUB_REPO"
  exit 1
fi
echo "==> .env 確認OK"

# 2) venv + 依存インストール -----------------------------------------
echo "==> venv作成 & 依存インストール"
python3 -m venv "$VENV"
"$PY" -m pip install --quiet --upgrade pip
"$PY" -m pip install --quiet playwright google-generativeai jinja2 python-dotenv pillow
"$PY" -m playwright install chromium

# 3) 最新コード取得 ---------------------------------------------------
echo "==> git pull(最新コード)"
git pull --ff-only || echo "(pull スキップ: ローカル変更あり。手動確認を)"

# 4) launchd 登録(毎週月曜 8:00) ------------------------------------
echo "==> launchd plist 生成: $PLIST"
mkdir -p "$HOME/Library/LaunchAgents" "$REPO_DIR/logs"
cat > "$PLIST" <<PLIST_EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key><string>${PLIST_LABEL}</string>
    <key>ProgramArguments</key>
    <array>
        <string>${PY}</string>
        <string>-m</string>
        <string>src.main</string>
    </array>
    <key>WorkingDirectory</key><string>${REPO_DIR}</string>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Weekday</key><integer>1</integer>
        <key>Hour</key><integer>8</integer>
        <key>Minute</key><integer>0</integer>
    </dict>
    <key>StandardOutPath</key><string>${REPO_DIR}/logs/stdout.log</string>
    <key>StandardErrorPath</key><string>${REPO_DIR}/logs/stderr.log</string>
</dict>
</plist>
PLIST_EOF

launchctl unload "$PLIST" 2>/dev/null || true
launchctl load "$PLIST"
echo "==> launchd 登録完了: $(launchctl list | grep "$PLIST_LABEL" || echo '(未検出)')"

cat <<'DONE'

======================================================================
✅ Pro側セットアップ完了

次の手順:
  A) 動作確認(営業時間外に手動実行してください):
       cd ~/pbrain-weekly-report && .venv/bin/python -m src.main
     → docs/<先週末日付>/ が生成され、GitHub Pagesに公開されればOK

  B) Pro実行が1回成功したのを確認してから、Air側のlaunchdを停止:
       (Airで) launchctl unload ~/Library/LaunchAgents/com.tlp.pbrain-weekly.plist
       (Airで) launchctl unload ~/Library/LaunchAgents/com.tlp.pbrain-weekly-desktop.plist
     ※二重生成(両機がpush)による競合を防ぐため、Pro成功後に必ず実施。

  注意: Proが月曜8:00に起動/スリープ解除されている必要があります
        (スリープ中は起床後に遅延発火)。
======================================================================
DONE
