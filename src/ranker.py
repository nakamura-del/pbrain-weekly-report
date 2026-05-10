"""先々週との順位比較で NEW/▲/▼/→ を割り当てる。"""


def normalize_kishu(name: str) -> str:
    """機種名のOCR揺れを吸収するための正規化"""
    name = name.replace(" ", "").replace("　", "")
    name = name.replace("・", "").replace("／", "/")
    return name.lower()


def calc_rank_change(current_ranking: list, previous_ranking: list) -> list:
    """先週ランキングに先々週との比較で順位変動列を追加"""
    prev_map = {
        normalize_kishu(r["kishu"]): r["rank"]
        for r in previous_ranking
    }
    for row in current_ranking:
        key = normalize_kishu(row["kishu"])
        current_rank = row["rank"]
        if key not in prev_map:
            row["change"] = "NEW"
        else:
            prev_rank = prev_map[key]
            if current_rank < prev_rank:
                row["change"] = "▲"
            elif current_rank > prev_rank:
                row["change"] = "▼"
            else:
                row["change"] = "→"
    return current_ranking
