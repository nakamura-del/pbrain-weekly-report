"""4枚のOCR結果からHTMLレポートを生成する。"""
from jinja2 import Environment, FileSystemLoader
from .config import ROOT, get_week_ranges
from . import ranker


WEEKS_OFFSET = -2  # 経過週の表示補正（P-Brain側の値から2を引く既存運用）


def _adjust_elapsed_weeks(machines):
    """経過週を補正値で調整（負にはしない）"""
    for m in machines:
        w = m.get("keika_shu")
        if w is not None:
            m["keika_shu"] = max(0, w + WEEKS_OFFSET)


def build(ocr_data: dict, today_str: str) -> str:
    """4枚のOCR結果からHTMLレポートを生成"""
    for sid in ["p4_lastweek", "p4_2weeksago", "s20_lastweek", "s20_2weeksago"]:
        _adjust_elapsed_weeks(ocr_data[sid].get("ranking", []))

    p4_ranking = ranker.calc_rank_change(
        ocr_data["p4_lastweek"]["ranking"],
        ocr_data["p4_2weeksago"]["ranking"],
    )
    s20_ranking = ranker.calc_rank_change(
        ocr_data["s20_lastweek"]["ranking"],
        ocr_data["s20_2weeksago"]["ranking"],
    )

    weeks = get_week_ranges()
    last_start, last_end = weeks["lastweek"]
    two_start, two_end = weeks["twoweeksago"]

    period_label = f"{last_start.strftime('%Y/%m/%d')}〜{last_end.strftime('%Y/%m/%d')}"
    prev_period_label = f"{two_start.strftime('%Y/%m/%d')}〜{two_end.strftime('%Y/%m/%d')}"

    env = Environment(
        loader=FileSystemLoader(str(ROOT / "templates")),
        autoescape=True,
    )
    tpl = env.get_template("weekly_report.html.j2")
    return tpl.render(
        period=period_label,
        prev_period=prev_period_label,
        p4_avg=ocr_data["p4_lastweek"]["average"],
        p4_ranking=p4_ranking,
        s20_avg=ocr_data["s20_lastweek"]["average"],
        s20_ranking=s20_ranking,
    )
