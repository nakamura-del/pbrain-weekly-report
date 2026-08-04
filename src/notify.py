"""失敗/成功をmacOS通知で知らせる最小実装（仕様書v2 §11）。

過去に「本体は成功していたがデスクトップ同期だけ失敗」を誰も気づけなかった事例が
あったため、成否をOSの通知センターに出す。osascriptが使えない環境でも本体処理は
落とさない（通知失敗は握りつぶす）。
"""
import subprocess

TITLE = "P-Brain 週間レポート"


def _san(s: str) -> str:
    """osascriptの二重引用符文字列に安全に埋め込めるよう最小限サニタイズ。"""
    return str(s).replace('"', "'").replace("\\", "/").replace("\n", " ").strip()


def _notify(message: str, title: str = TITLE) -> None:
    msg = _san(message)
    try:
        subprocess.run(
            ["osascript", "-e",
             f'display notification "{msg}" with title "{_san(title)}"'],
            check=False, timeout=10,
        )
    except Exception as e:  # 通知の失敗で本体を落とさない
        print(f"[通知失敗] {type(e).__name__}: {e}")


def notify_failure(message: str) -> None:
    print(f"[通知/失敗] {message}")
    _notify(f"❌ {message}")


def notify_success(message: str) -> None:
    print(f"[通知/成功] {message}")
    _notify(f"✅ {message}")
