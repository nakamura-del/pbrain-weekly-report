#!/usr/bin/env python3
"""Weekly report generator for P-Brain."""

import json
import os
from datetime import datetime, timedelta

# --- Configuration ---
TODAY = datetime(2026, 3, 18)
TWO_WEEKS_AGO = TODAY - timedelta(days=14)  # 2026/03/04
SHARE_THRESHOLD = 0.2  # 0.2%以下は除外
WEEKS_OFFSET = -2  # 経過週の補正値


def load_ocr_data(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def parse_date(date_str):
    """YYYY/MM/DD → datetime"""
    if not date_str:
        return None
    return datetime.strptime(date_str.replace("/", "-"), "%Y-%m-%d")


def is_within_two_weeks(release_date_str):
    """発売日が当日より2週間以内か"""
    d = parse_date(release_date_str)
    if not d:
        return False
    return d >= TWO_WEEKS_AGO


def should_exclude(machine):
    """シェア0.2%以下の除外判定（例外: 発売2週間以内）
    判定対象: 打込シェア・台売上シェア（台粗利シェアは低利益体質の機種で
    正当に低くなるため除外判定には使用しない）
    """
    if is_within_two_weeks(machine.get("release_date")):
        return False
    shares = [
        machine.get("uchi_komi_share", 0) or 0,
        machine.get("dai_uriage_share", 0) or 0,
    ]
    return any(s <= SHARE_THRESHOLD for s in shares)


def filter_and_rank(machines, max_count=15):
    """除外ルール適用 → 再ランキング"""
    filtered = [m for m in machines if not should_exclude(m)]
    for i, m in enumerate(filtered[:max_count], 1):
        m["display_rank"] = i
    return filtered[:max_count]


def normalize_name(name):
    """機種名正規化（比較用）"""
    if not name:
        return ""
    return name.replace(" ", "").replace("　", "").replace("/", "").replace("・", "")


def compute_badges(this_week, prev_week):
    """先週 vs 先々週のランキング比較 → バッジ割当
    - NEW: 発売日が当日から2週間以内の機種
    - ▲: 先々週に不在だが発売2週間以上経過（ランクUP扱い）、または順位上昇
    - ▼: 順位下降
    - →: 順位変動なし
    """
    prev_rank_map = {}
    for m in prev_week:
        key = normalize_name(m.get("name", ""))
        prev_rank_map[key] = m.get("display_rank", 999)

    for m in this_week:
        key = normalize_name(m.get("name", ""))
        if key not in prev_rank_map:
            # 先々週にいなかった機種
            if is_within_two_weeks(m.get("release_date")):
                m["badge"] = "new"
                m["badge_text"] = "NEW"
            else:
                # 発売2週間以上経過 → ランクUP扱い
                m["badge"] = "up"
                m["badge_text"] = "▲"
        else:
            prev_r = prev_rank_map[key]
            curr_r = m["display_rank"]
            if curr_r < prev_r:
                m["badge"] = "up"
                m["badge_text"] = "▲"
            elif curr_r > prev_r:
                m["badge"] = "down"
                m["badge_text"] = "▼"
            else:
                m["badge"] = "same"
                m["badge_text"] = "→"


def adjust_elapsed_weeks(machines):
    """経過週を -2 補正"""
    for m in machines:
        w = m.get("elapsed_weeks")
        if w is not None:
            m["elapsed_weeks"] = max(0, w + WEEKS_OFFSET)


def categorize_data(ocr_results):
    """OCR結果を種別×期間で分類"""
    data = {}
    for item in ocr_results:
        h = item["header"]
        key = (h["type"], h["period_start"])
        data[key] = item
    return data


def fmt_num(val, decimals=0):
    """数値フォーマット"""
    if val is None:
        return "—"
    if decimals == 0:
        return f"{int(round(val)):,}"
    return f"{val:,.{decimals}f}"


def fmt_pct(val):
    """パーセント表示"""
    if val is None:
        return "—"
    return f"{val:.2f}%"


def generate_html(p4_this, p4_prev, s20_this, s20_prev, period_start, period_end):
    """HTMLレポート生成"""

    def machine_rows(machines):
        rows = []
        for m in machines:
            badge_html = ""
            if m.get("badge"):
                badge_html = f'<span class="badge {m["badge"]}">{m["badge_text"]}</span>'

            elapsed = m.get("elapsed_weeks", "—")
            release = m.get("release_date", "—")

            rows.append(f"""          <tr>
            <td class="rank-col">{m['display_rank']}</td>
            <td class="machine">{m['name']}{badge_html}</td>
            <td class="release">{release}</td>
            <td class="week">{elapsed}</td>
            <td class="num">{fmt_num(m.get('uchi_komi'))}</td>
            <td class="num">{fmt_num(m.get('tama_arari'), 3)}</td>
            <td class="num">{fmt_num(m.get('dai_arari'))}</td>
            <td class="num">{fmt_num(m.get('dai_uriage'))}</td>
            <td class="num">{fmt_num(m.get('tama_tanka'), 3)}</td>
            <td class="num">{fmt_pct(m.get('uchi_komi_share'))}</td>
            <td class="num">{fmt_pct(m.get('dai_arari_share'))}</td>
            <td class="num">{fmt_pct(m.get('dai_uriage_share'))}</td>
            <td class="num">{fmt_pct(m.get('dai_count_share'))}</td>
          </tr>""")
        return "\n".join(rows)

    def kpi_section(summary, section_title):
        s = summary or {}
        rieki = s.get("rieki_ritsu")
        rieki_str = f"{rieki:.2f}%" if rieki is not None else "—"
        return f"""  <div class="section">
    <h2>{section_title} 全体平均</h2>
    <div class="kpi-grid">
      <div class="kpi"><div class="label">打込</div><div class="value">{fmt_num(s.get('uchi_komi'))}</div></div>
      <div class="kpi"><div class="label">玉粗利</div><div class="value">{fmt_num(s.get('tama_arari'), 3)}</div></div>
      <div class="kpi"><div class="label">台粗利</div><div class="value">{fmt_num(s.get('dai_arari'))}</div></div>
      <div class="kpi"><div class="label">台売上</div><div class="value">{fmt_num(s.get('dai_uriage'))}</div></div>
      <div class="kpi"><div class="label">玉単価</div><div class="value">{fmt_num(s.get('tama_tanka'), 3)}</div></div>
      <div class="kpi"><div class="label">利益率</div><div class="value">{rieki_str}</div></div>
    </div>
  </div>"""

    def table_section(title, machines):
        return f"""  <div class="section">
    <h2>{title}</h2>
    <div class="scroll">
      <table>
        <thead>
          <tr>
            <th class="rank-col">順位</th>
            <th>機種</th>
            <th class="release">発売日</th>
            <th class="week">経過週</th>
            <th class="num">打込</th>
            <th class="num">玉粗利</th>
            <th class="num">台粗利</th>
            <th class="num">台売上</th>
            <th class="num">玉単価</th>
            <th class="num">打込シェア</th>
            <th class="num">台粗利シェア</th>
            <th class="num">台売上シェア</th>
            <th class="num">台数シェア</th>
          </tr>
        </thead>
        <tbody>
{machine_rows(machines)}
        </tbody>
      </table>
    </div>
  </div>"""

    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>P-Brain 週間レポート（{period_start}〜{period_end}）</title>
<style>
:root{{
  --bg:#060B16;
  --panel:#0B1222;
  --panel2:#0E1A32;
  --line:rgba(255,255,255,.10);
  --text:#EAF0FF;
  --muted:rgba(234,240,255,.72);
  --good:#7CFFB2;
  --bad:#FF7A7A;
  --warn:#FFD166;
  --same:#B8C2D8;
}}
*{{box-sizing:border-box}}
body{{
  margin:0;
  background:linear-gradient(180deg,#050914 0%,#091224 100%);
  color:var(--text);
  font-family:-apple-system,BlinkMacSystemFont,"Hiragino Sans","Noto Sans JP","Segoe UI",sans-serif;
}}
.wrap{{max-width:1420px;margin:0 auto;padding:28px 16px 40px}}
.hero{{
  background:linear-gradient(135deg,rgba(139,211,221,.16),rgba(110,168,255,.08));
  border:1px solid var(--line);
  border-radius:20px;
  padding:24px;
  box-shadow:0 16px 40px rgba(0,0,0,.28);
}}
.title{{font-size:28px;font-weight:800;letter-spacing:.02em;margin:0 0 8px}}
.sub{{font-size:14px;color:var(--muted);margin:0}}
.section{{
  background:rgba(11,18,34,.9);
  border:1px solid var(--line);
  border-radius:18px;
  padding:18px;
  box-shadow:0 10px 30px rgba(0,0,0,.2);
  margin-top:20px;
}}
.section h2{{margin:0 0 14px;font-size:22px}}
.kpi-grid{{display:grid;grid-template-columns:repeat(6,1fr);gap:10px;margin-bottom:16px}}
.kpi{{
  background:linear-gradient(180deg,rgba(255,255,255,.05),rgba(255,255,255,.025));
  border:1px solid var(--line);
  border-radius:14px;
  padding:12px 12px 10px;
  min-height:82px;
}}
.kpi .label{{font-size:12px;color:var(--muted);margin-bottom:10px}}
.kpi .value{{font-size:24px;font-weight:800;line-height:1.05}}
.scroll{{overflow-x:auto;border:1px solid var(--line);border-radius:14px}}
table{{width:100%;border-collapse:collapse;min-width:1260px;background:rgba(255,255,255,.02)}}
th,td{{padding:10px 10px;border-bottom:1px solid var(--line);font-size:13px;vertical-align:middle;white-space:nowrap}}
th{{position:sticky;top:0;background:#10203d;color:#d8e8ff;text-align:left;font-weight:700}}
tr:nth-child(even) td{{background:rgba(255,255,255,.02)}}
.rank-col{{text-align:center;width:56px}}
.machine{{font-weight:700}}
.release,.week{{text-align:center}}
.num{{text-align:right;font-variant-numeric:tabular-nums}}
.badge{{display:inline-flex;align-items:center;justify-content:center;min-width:34px;height:22px;padding:0 8px;border-radius:999px;font-size:12px;font-weight:800;margin-left:8px;vertical-align:middle}}
.badge.new{{background:rgba(255,209,102,.16);color:var(--warn);border:1px solid rgba(255,209,102,.36)}}
.badge.up{{background:rgba(124,255,178,.14);color:var(--good);border:1px solid rgba(124,255,178,.34)}}
.badge.down{{background:rgba(255,122,122,.14);color:var(--bad);border:1px solid rgba(255,122,122,.34)}}
.badge.same{{background:rgba(184,194,216,.12);color:var(--same);border:1px solid rgba(184,194,216,.24)}}
.meta{{display:flex;gap:12px;flex-wrap:wrap;margin-top:14px}}
.meta span{{font-size:12px;color:var(--muted);padding:6px 10px;border-radius:999px;background:rgba(255,255,255,.04);border:1px solid var(--line)}}
@media (max-width:760px){{
  .wrap{{padding:16px 12px 28px}}
  .title{{font-size:22px}}
  .section{{padding:14px}}
  .kpi-grid{{grid-template-columns:repeat(2,1fr)}}
  .kpi .value{{font-size:20px}}
  table{{min-width:1180px}}
}}
</style>
</head>
<body>
<div class="wrap">
  <div class="hero">
    <h1 class="title">P-Brain 週間レポート</h1>
    <p class="sub">期間：{period_start}〜{period_end}</p>
  </div>

  <div class="section" style="margin-top:20px">
    <p class="meta"><span>対象：4円パチンコ / 20円スロット</span><span>順位変動：先々週比（NEW / ▲ / ▼ / →）</span></p>
  </div>

{kpi_section(p4_this['summary'], '4円パチンコ')}

{table_section('4円パチンコ TOP' + str(len(p4_this['filtered'])), p4_this['filtered'])}

{kpi_section(s20_this['summary'], '20円スロット')}

{table_section('20円スロット TOP' + str(len(s20_this['filtered'])), s20_this['filtered'])}

</div>
</body>
</html>"""
    return html


def main():
    data_path = os.path.join(os.path.dirname(__file__), "../../data/ocr_results.json")
    ocr_results = load_ocr_data(data_path)

    # Categorize by type and period
    cat = categorize_data(ocr_results)

    # Identify this week and prev week
    p4_this_raw = cat.get(("4円パチンコ", "2026/03/09"))
    p4_prev_raw = cat.get(("4円パチンコ", "2026/03/02"))
    s20_this_raw = cat.get(("20円スロット", "2026/03/09"))
    s20_prev_raw = cat.get(("20円スロット", "2026/03/02"))

    if not all([p4_this_raw, p4_prev_raw, s20_this_raw, s20_prev_raw]):
        print("ERROR: Missing data for some categories/periods")
        for k, v in cat.items():
            print(f"  Found: {k}")
        return

    # Apply elapsed weeks offset
    for raw in [p4_this_raw, p4_prev_raw, s20_this_raw, s20_prev_raw]:
        adjust_elapsed_weeks(raw["machines"])

    # Filter and rank
    p4_this_filtered = filter_and_rank(p4_this_raw["machines"])
    p4_prev_filtered = filter_and_rank(p4_prev_raw["machines"])
    s20_this_filtered = filter_and_rank(s20_this_raw["machines"])
    s20_prev_filtered = filter_and_rank(s20_prev_raw["machines"])

    # Compute badges
    compute_badges(p4_this_filtered, p4_prev_filtered)
    compute_badges(s20_this_filtered, s20_prev_filtered)

    # Build data for template
    p4_this = {"summary": p4_this_raw["summary"], "filtered": p4_this_filtered}
    s20_this = {"summary": s20_this_raw["summary"], "filtered": s20_this_filtered}

    # Generate HTML
    html = generate_html(
        p4_this, p4_prev_filtered,
        s20_this, s20_prev_filtered,
        "2026/03/09", "2026/03/15",
    )

    output_path = os.path.join(
        os.path.dirname(__file__), "../../output/pbrain_weekly_20260315.html"
    )
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Report generated: {output_path}")

    # Print summary
    print(f"\n4円パチンコ: {len(p4_this_filtered)} machines (after filtering)")
    print(f"20円スロット: {len(s20_this_filtered)} machines (after filtering)")

    print("\n--- 4円パチンコ 除外機種 ---")
    for m in p4_this_raw["machines"]:
        if should_exclude(m):
            shares = f"打込{m.get('uchi_komi_share', 0):.2f}% / 台粗利{m.get('dai_arari_share', 0):.2f}% / 台売上{m.get('dai_uriage_share', 0):.2f}%"
            print(f"  {m['name']} | {shares} | 発売{m.get('release_date')}")

    print("\n--- 20円スロット 除外機種 ---")
    for m in s20_this_raw["machines"]:
        if should_exclude(m):
            shares = f"打込{m.get('uchi_komi_share', 0):.2f}% / 台粗利{m.get('dai_arari_share', 0):.2f}% / 台売上{m.get('dai_uriage_share', 0):.2f}%"
            print(f"  {m['name']} | {shares} | 発売{m.get('release_date')}")


if __name__ == "__main__":
    main()
