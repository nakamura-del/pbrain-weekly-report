"""先々週との順位比較で NEW/▲/▼/→ を割り当てる。

判定ルール（既存運用準拠）:
- 先々週TOP15に不在:
    - 発売日が ref_date から2週間以内 → NEW
    - そうでない                    → ▲（新規参入だが発売2週以上経過＝ランクUP扱い）
- 先々週TOP15に存在:
    - 順位上昇 → ▲
    - 順位下降 → ▼
    - 同順位   → →
"""
from datetime import datetime, timedelta


OCR_CORRECTIONS = {
    "慶極推理": "虚構推理",
    "袋炎ノ消防隊": "炎炎ノ消防隊",
    "恐襲ノ": "最恐領域",
    "ポッチーと一発おだてて": "ポチッと一発おだて",
    "女神カフェテラスJL2": "女神のカフェテラスJLZ",
}


def normalize_kishu(name: str) -> str:
    """機種名のOCR揺れを吸収するための正規化"""
    if not name:
        return ""
    for wrong, right in OCR_CORRECTIONS.items():
        name = name.replace(wrong, right)
    name = name.replace(" ", "").replace("　", "")
    name = name.replace("・", "").replace("／", "").replace("/", "")
    name = name.replace(".", "").replace("．", "")
    return name.lower()


def _is_zero_share(value) -> bool:
    """台数シェアが実質 0.00% かを判定（丸め誤差を吸収）"""
    try:
        return abs(float(value)) < 0.005
    except (TypeError, ValueError):
        return False


def filter_and_renumber(ranking: list, top_n: int = 15) -> list:
    """台数シェア0.00%かつ経過週2週以上の機種を除外し、上位top_nに詰めて再採番する。

    - 経過週=1の機種は台数シェア0.00%でも残す
    - 除外判定には P-Brain 画面の元の経過週（生値）を使う
    - 除外で空いた分は16位以降を繰り上げ、常にtop_n機種に揃える
    - rank は詰めて 1〜top_n に再採番する
    """
    kept = []
    for row in ranking:
        keika = row.get("keika_shu")
        if keika is not None and keika >= 2 and _is_zero_share(row.get("daisuu_share")):
            continue
        kept.append(row)
    kept = kept[:top_n]
    for i, row in enumerate(kept, start=1):
        row["rank"] = i
    return kept


def apply_keika_display(ranking: list) -> None:
    """表示用に経過週を-1する。ただし元が1週なら1のまま（0にしない）。"""
    for row in ranking:
        keika = row.get("keika_shu")
        if keika is None:
            continue
        row["keika_shu"] = keika if keika <= 1 else keika - 1


def _is_new_release(release_date_str, ref_date: datetime) -> bool:
    """発売日が ref_date から2週間以内なら True"""
    if not release_date_str:
        return False
    s = release_date_str.replace("-", "/")
    try:
        d = datetime.strptime(s, "%Y/%m/%d")
    except ValueError:
        return False
    diff = (ref_date - d).days
    return 0 <= diff <= 14


def calc_rank_change(current_ranking: list, previous_ranking: list, ref_date: datetime = None) -> list:
    """先週ランキングに先々週との比較で順位変動列を追加

    ref_date: 発売日が「2週以内」かを判定する基準日（既定: 今日）
    """
    if ref_date is None:
        ref_date = datetime.now()
    prev_map = {
        normalize_kishu(r["kishu"]): r["rank"]
        for r in previous_ranking
    }
    for row in current_ranking:
        key = normalize_kishu(row["kishu"])
        current_rank = row["rank"]
        if key not in prev_map:
            if _is_new_release(row.get("hatsubaibi"), ref_date):
                row["change"] = "NEW"
            else:
                row["change"] = "▲"
        else:
            prev_rank = prev_map[key]
            if current_rank < prev_rank:
                row["change"] = "▲"
            elif current_rank > prev_rank:
                row["change"] = "▼"
            else:
                row["change"] = "→"
    return current_ranking
