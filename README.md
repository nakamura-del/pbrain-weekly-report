# P-Brain 週間レポート完全自動化システム

毎週火曜朝7:00（launchd）にP-Brainから4画面スクショを取得し、Gemini OCRで数値抽出 → HTMLレポート生成 → GitHub Pages公開する。

## セットアップ

```bash
pip install -r requirements.txt
playwright install chromium
cp .env.example .env  # 認証情報を記入
```

## 実行（手動）

```bash
python -m src.main
```

## 実行（火曜7:00自動）

```bash
cp launchd/com.tlp.pbrain-weekly.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.tlp.pbrain-weekly.plist
```

## 公開URL

- 各週: https://nakamura-del.github.io/pbrain-weekly-report/YYYY-MM-DD/
- 一覧: https://nakamura-del.github.io/pbrain-weekly-report/

詳細仕様は [CLAUDE.md](./CLAUDE.md) を参照。
