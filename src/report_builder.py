"""4枚のOCR結果からHTMLレポートを生成する。"""
from jinja2 import Environment, FileSystemLoader
from .config import ROOT, get_week_ranges
from . import ranker


def _snapshot(ranking: list) -> list:
    """来週の「先々週」参照用に、順位比較に必要な最小データだけ残す。"""
    return [{"rank": r["rank"], "kishu": r["kishu"]} for r in ranking]


def build(cur_ocr: dict, prev_rankings: dict, ref_date=None):
    """今週(先週データ)のOCRと前週保存ランキングからHTMLを生成。

    cur_ocr:       {"p4": <OCR結果>, "s20": <OCR結果>}  … 今回スクレイプした先週分
    prev_rankings: {"p4": [ {rank,kishu}... ], "s20": [...] } … 前週保存(=先々週)
    戻り値: (html, snapshot)
        snapshot は今週の確定ランキング。docs/<date>/data.json に保存し、
        来週の prev_rankings として渡す。
    返す順位変動は snapshot(前週比)で算出する。
    """
    weeks = get_week_ranges(ref_date)
    last_start, last_end = weeks["lastweek"]
    two_start, two_end = weeks["twoweeksago"]

    # 1) 台数シェア0.00%かつ経過週2週以上を除外し、16位以降で補充して常に15機種に揃える
    #    （除外判定は元の経過週の生値を使うため、経過週の表示補正より前に行う）
    p4_last = ranker.filter_and_renumber(cur_ocr["p4"].get("ranking", []))
    s20_last = ranker.filter_and_renumber(cur_ocr["s20"].get("ranking", []))

    # 2) 前週保存ランキング（=先々週）と比較して変動（NEW/▲/▼/→）を付与
    p4_prev = prev_rankings.get("p4", [])
    s20_prev = prev_rankings.get("s20", [])
    p4_ranking = ranker.calc_rank_change(p4_last, p4_prev, last_start, last_end)
    s20_ranking = ranker.calc_rank_change(s20_last, s20_prev, last_start, last_end)

    # 3) 来週用スナップショット（経過週補正の前＝順位・機種名の確定状態）
    snapshot = {"p4": _snapshot(p4_ranking), "s20": _snapshot(s20_ranking)}

    # 4) 表示用に経過週を-1（元が1週なら1のまま）
    ranker.apply_keika_display(p4_ranking, last_start, last_end)
    ranker.apply_keika_display(s20_ranking, last_start, last_end)

    period_label = f"{last_start.strftime('%Y/%m/%d')}〜{last_end.strftime('%Y/%m/%d')}"
    prev_period_label = f"{two_start.strftime('%Y/%m/%d')}〜{two_end.strftime('%Y/%m/%d')}"

    env = Environment(
        loader=FileSystemLoader(str(ROOT / "templates")),
        autoescape=True,
    )
    tpl = env.get_template("weekly_report.html.j2")
    html = tpl.render(
        period=period_label,
        prev_period=prev_period_label,
        p4_avg=cur_ocr["p4"]["average"],
        p4_ranking=p4_ranking,
        s20_avg=cur_ocr["s20"]["average"],
        s20_ranking=s20_ranking,
    )
    return html, snapshot
