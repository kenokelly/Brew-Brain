from flask import Blueprint, request
from core.config import get_config
import datetime
import html

labels_bp = Blueprint('labels', __name__)

# Gravity within this of the target FG counts as finished
FINISHED_MARGIN = 0.003


def _fmt_date(iso: str) -> str:
    try:
        return datetime.datetime.strptime(iso[:10], "%Y-%m-%d").strftime("%d %b %Y")
    except (TypeError, ValueError):
        return iso or ""


@labels_bp.route('', methods=['GET'])
@labels_bp.route('/', methods=['GET'])
def generate_label():
    """Printable keg label for the active batch.

    Optional query params override what's shown: name, style, abv.
    """
    from services.labels import display_name, srm_hex
    from services.status import get_status_dict

    info = get_config("label_info") or {}
    esc = lambda v: html.escape(str(v)) if v not in (None, "") else ""

    name = request.args.get("name") or display_name(get_config("batch_name"), info.get("recipe_name"))
    style = request.args.get("style") or get_config("style") or ""
    if "Unknown" in style:
        style = ""

    og = float(get_config("og") or 1.050)
    target_fg = float(get_config("target_fg") or 1.010)
    sg = None
    try:
        sg = get_status_dict().get("sg")
    except Exception:
        pass

    # Measured ABV once fermentation has finished, otherwise the recipe's
    if request.args.get("abv"):
        abv, abv_note = request.args["abv"], ""
    elif sg and sg <= target_fg + FINISHED_MARGIN:
        abv, abv_note = f"{(og - sg) * 131.25:.1f}", ""
    elif info.get("abv"):
        abv, abv_note = f"{float(info['abv']):.1f}", "target"
    else:
        abv, abv_note = f"{(og - target_fg) * 131.25:.1f}", "target"

    colour = srm_hex(info.get("srm"))
    ibu = f"{float(info['ibu']):.0f}" if info.get("ibu") is not None else None
    ebc = f"{float(info['srm']) * 1.97:.0f}" if info.get("srm") is not None else None
    carb = f"{float(info['carbonation']):.1f}" if info.get("carbonation") else None
    hops = info.get("hops") or []
    dry = set(info.get("dry_hops") or [])
    hop_text = " · ".join(f"{h} (dry hop)" if h in dry else h for h in hops)
    malts = " · ".join(info.get("malts") or [])
    yeast = get_config("yeast_strain") or ""
    if "Unknown" in yeast:
        yeast = ""

    stats = [(abv, "% ABV", abv_note)]
    if ibu:
        stats.append((ibu, "IBU", ""))
    if ebc:
        stats.append((ebc, "EBC", ""))
    if carb:
        stats.append((carb, "vols CO₂", ""))
    stats_html = "".join(
        f'<div class="stat"><div class="v">{esc(v)}</div><div class="k">{esc(k)}</div>'
        f'{f"<div class=n>{esc(n)}</div>" if n else ""}</div>'
        for v, k, n in stats
    )

    rows = [("Hops", hop_text), ("Malt", malts), ("Yeast", yeast)]
    rows_html = "".join(f"<div><b>{k}</b> {esc(v)}</div>" for k, v in rows if v)

    footer = [f"Batch #{info['batch_no']}" if info.get("batch_no") else "",
              f"Brewed {_fmt_date(get_config('start_date') or '')}",
              esc(info.get("brewer") or "")]
    footer_html = " &nbsp;·&nbsp; ".join(f for f in footer if f)

    page = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Keg Label - {esc(name)}</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,700;9..144,900&family=Inter:wght@400;600;700&display=swap">
<style>
  @page {{ size: 100mm 70mm; margin: 0; }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; padding: 24px; background: #e9e6e1; font-family: Inter, system-ui, sans-serif; color: #1c1917;
         display: flex; flex-direction: column; align-items: center; gap: 16px; }}
  .label {{ width: 100mm; height: 70mm; background: #fffdf8; border-radius: 4mm; overflow: hidden;
           display: flex; flex-direction: column; box-shadow: 0 6px 24px rgba(0,0,0,.18);
           -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
  .band {{ background: {colour}; padding: 3mm 5mm; display: flex; justify-content: space-between; align-items: center;
          font-size: 7pt; font-weight: 700; letter-spacing: .18em; text-transform: uppercase; color: rgba(0,0,0,.72); }}
  .body {{ flex: 1; padding: 3.5mm 5mm 2.5mm; display: flex; flex-direction: column; min-height: 0; }}
  h1 {{ font-family: Fraunces, Georgia, serif; font-weight: 900; font-size: 22pt; line-height: 1; margin: 0;
       letter-spacing: -.01em; overflow-wrap: anywhere; }}
  .style {{ font-size: 8.5pt; font-weight: 600; color: #78716c; margin-top: 1.2mm; }}
  .stats {{ display: flex; gap: 5mm; margin: 3mm 0 2.5mm; padding: 2mm 0; border-top: 1.5px solid #1c1917; border-bottom: 1px solid #d6d3d1; }}
  .stat .v {{ font-family: Fraunces, Georgia, serif; font-weight: 700; font-size: 15pt; line-height: 1; }}
  .stat .k {{ font-size: 6.5pt; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; color: #57534e; margin-top: .8mm; }}
  .stat .n {{ font-size: 5.5pt; color: #a8a29e; text-transform: uppercase; letter-spacing: .08em; }}
  .rows {{ font-size: 7pt; line-height: 1.45; color: #44403c; }}
  .rows b {{ font-weight: 700; color: #1c1917; margin-right: 1mm; }}
  .foot {{ margin-top: auto; font-size: 6.5pt; color: #a8a29e; }}
  .tools {{ display: flex; gap: 8px; }}
  .tools button {{ font: 600 14px Inter, sans-serif; padding: 8px 16px; border-radius: 999px; border: 0; white-space: nowrap; background: #1c1917; color: #fff; cursor: pointer; }}
  .tools p {{ margin: 0; font-size: 13px; color: #57534e; align-self: center; }}
  @media print {{
    body {{ padding: 0; background: none; display: block; }}
    .label {{ box-shadow: none; border-radius: 0; }}
    .tools {{ display: none; }}
  }}
</style>
</head>
<body>
  <div class="label">
    <div class="band"><span>Brew Brain</span><span>{f"No. {esc(info['batch_no'])}" if info.get("batch_no") else ""}</span></div>
    <div class="body">
      <h1>{esc(name)}</h1>
      {f'<div class="style">{esc(style)}</div>' if style else ''}
      <div class="stats">{stats_html}</div>
      <div class="rows">{rows_html}</div>
      <div class="foot">{footer_html}</div>
    </div>
  </div>
  <div class="tools">
    <button onclick="window.print()">Print label</button>
    <p>100 × 70 mm. Change the name in Settings &gt; Batch Profile.</p>
  </div>
</body>
</html>"""
    return page
