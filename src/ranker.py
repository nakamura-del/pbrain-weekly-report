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


def normalize_kishu(name: str) -> str:
    """機種名のOCR揺れを吸収するための正規化"""
    if not name:
        return ""
    name = name.replace(" ", "").replace("　", "")
    name = name.replace("・", "").replace("／", "").replace("/", "")
    name = name.replace(".", "").replace("．", "")
    return name.lower()


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
