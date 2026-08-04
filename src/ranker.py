"""前週レポート(TOP15)との比較で NEW/▲/▼/→ を割り当てる（仕様書v2 §5準拠）。

判定ルール:
- 発売日が集計期間内（新台）        → NEW
- 前週TOP15にあり 順位上昇          → ▲
- 前週TOP15にあり 順位下降          → ▼
- 前週TOP15にあり 同順位            → →
- 前週TOP15に不在（圏外からの復帰） → ▲
NEW は新台のみ。既存機種の圏外復帰には使わない。
"""
from datetime import datetime


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


# 変則販売（発売週の月曜が祝日→実質火曜新台）で、-1補正だと実態より1週少なく
# 表示される機種の恒久オフセット。絶対値でなく加算にすることで週が進んでも追従する。
KEIKA_OFFSET_RAW = {
    "eベルセルク無双2HM4": 1,   # 発売2026/07/20の週は月曜が祝日
    "L東京喰種FT": 1,           # 同上
}


def apply_keika_display(ranking: list, period_start=None, period_end=None) -> None:
    """表示用に経過週を-1する（月曜起点運用のため-1が正しい。仕様§5の-2は古い記述）。

    仕様書v2 §5「導入初週」:
    - 発売日が集計期間内の機種は、計算結果に関わらず 1 に固定する
    - どの機種も 0 にはしない（最小 1）
    変則販売機種は KEIKA_OFFSET_RAW で +1 補正する。
    """
    offset_map = {normalize_kishu(k): v for k, v in KEIKA_OFFSET_RAW.items()}
    for row in ranking:
        keika = row.get("keika_shu")
        if keika is None:
            continue
        if _is_in_period(row.get("hatsubaibi"), period_start, period_end):
            base = 1
        else:
            base = keika - 1 if keika > 1 else 1
        row["keika_shu"] = base + offset_map.get(normalize_kishu(row.get("kishu", "")), 0)


def _parse_hatsubaibi(release_date_str):
    """発売日文字列(YYYY/MM/DD または YYYY-MM-DD)を date に。失敗時 None。"""
    if not release_date_str:
        return None
    s = str(release_date_str).replace("-", "/")
    try:
        return datetime.strptime(s, "%Y/%m/%d").date()
    except ValueError:
        return None


def _is_in_period(release_date_str, period_start, period_end) -> bool:
    """発売日が集計期間 [period_start, period_end] 内なら True（新台判定）。"""
    if period_start is None or period_end is None:
        return False
    d = _parse_hatsubaibi(release_date_str)
    if d is None:
        return False
    return period_start.date() <= d <= period_end.date()


def calc_rank_change(current_ranking: list, previous_ranking: list,
                     period_start=None, period_end=None) -> list:
    """前週レポートのTOP15と比較して変動記号を付与（仕様書v2 §5）。

    period_start/period_end: 今回の集計期間。発売日がこの範囲内なら新台=NEW。
    """
    prev_map = {
        normalize_kishu(r["kishu"]): r["rank"]
        for r in previous_ranking
    }
    for row in current_ranking:
        # 新台（発売日が集計期間内）は無条件 NEW。圏外復帰の▲より優先。
        if _is_in_period(row.get("hatsubaibi"), period_start, period_end):
            row["change"] = "NEW"
            continue
        key = normalize_kishu(row["kishu"])
        current_rank = row["rank"]
        if key not in prev_map:
            row["change"] = "▲"  # 前週TOP15外からの復帰
        else:
            prev_rank = prev_map[key]
            if current_rank < prev_rank:
                row["change"] = "▲"
            elif current_rank > prev_rank:
                row["change"] = "▼"
            else:
                row["change"] = "→"
    return current_ranking
