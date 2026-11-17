"""Summary image (1080 x 1350) from data/results_all.json and data/scoring.json.
Every figure is read from those files and rounded here. Rendered with headless Chrome
(set FILL_CHROME to override the path).   python3 -I code/charts.py
"""
import json
import os
import subprocess

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
CHROME = os.environ.get("FILL_CHROME", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
INK, SOFT, GRID = "#1c1c1c", "#555555", "#e3e3e3"
GREY, ORANGE, BLUE, GREY_TEXT = "#9aa3ad", "#d9822b", "#2a6fb0", "#4a535c"


def text(x, y, s, size=27, fill=INK, anchor="start", weight="normal"):
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" text-anchor="{anchor}" font-weight="{weight}">{s}</text>'


def values():
    d = json.load(open(os.path.join(ROOT, "data", "results_all.json")))
    s = json.load(open(os.path.join(ROOT, "data", "scoring.json")))
    ks = s["kind_shares"]
    return {"markets": d["counts"]["markets"], "mm": round(100 * ks["mm"]), "mixed": round(100 * ks["compmm"]),
            "comp": round(100 * ks["comp"]),
            "n1": int(100 * (d["summary"]["N1/C"]["median"] - 1)),  # 10.5 shown as 10, as in the post
            "w": round(100 * (d["summary"]["W/C"]["median"] - 1)),
            "v_n": s["V_markets"], "v_n1": s["V_within_5pct_of"]["V/N1"], "v_c": s["V_within_5pct_of"]["V/C"],
            "v_om": s["V_within_5pct_of"]["V/OM"], "v_om_x": round(d["groups"]["full_enumerated"]["V"]["V/OM"]["median"], 1)}


def build(v):
    w, h, m = 1080, 1350, 60
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" font-family="Helvetica, Arial, sans-serif">',
         f'<rect width="{w}" height="{h}" fill="white"/>',
         text(m, 110, "Three ways to count", 62, INK, weight="bold"), text(m, 182, "Polymarket volume", 62, INK, weight="bold"),
         text(m, 236, f"{v['markets']} markets closed in October 2026, checked against receipts", 26, SOFT),
         text(m, 270, "Medians across markets; 25 of the 60 markets sampled", 26, SOFT),
         text(m, 345, "Most matches create or destroy shares", 44, INK, weight="bold")]
    x, bw = m, w - 2 * m
    for a, b, color, key in [("both sides buy", "or both sell", ORANGE, "mm"), ("buyer vs", "seller", GREY, "comp"), ("mixed", "", BLUE, "mixed")]:
        wd = bw * v[key] / 100
        p.append(f'<rect x="{x:.1f}" y="355" width="{wd:.1f}" height="110" fill="{color}"/>')
        if v[key] >= 15:
            p.append(text(x + wd / 2, 425, f"{v[key]}%", 50, "white", "middle", "bold"))
        tc = GREY_TEXT if color == GREY else color
        if key == "mixed":
            a, b = f"mixed {v[key]}%", ""
            x -= 20  # keep the label inside the page
        p += [text(x + 8, 505, a, 27, tc, weight="bold"), text(x + 8, 537, b, 27, tc, weight="bold")]
        if key == "mixed":
            x += 20
        x += wd
    p.append(text(m, 650, "Adding up fills against cash that moved", 44, INK, weight="bold"))
    for cx, big, color, l1, l2 in [(m, f"+{v['n1']}%", BLUE, "every fill added up,", "counted at both ends"),
                                   (m + 500, f"+{v['w']}%", ORANGE, "reading fills wallet", "by wallet counts cash twice")]:
        p += [text(cx, 760, big, 96, color, weight="bold"), text(cx, 808, l1, 27, INK), text(cx, 842, l2, 27, INK)]
    p.append(text(m, 960, "What the venue's volume matches", 44, INK, weight="bold"))
    for cx, big, l1, l2 in [(m, f"{v['v_n1']} and {v['v_c']}", "of 35 markets within 5% of", "fill total / cash moved"),
                            (m + 500, f"{v['v_om']} of {v['v_n']}", "within 5% of the", "one-sided count")]:
        p += [text(cx, 1070, big, 76, ORANGE if cx == m else GREY_TEXT, weight="bold"), text(cx, 1118, l1, 27, INK), text(cx, 1152, l2, 27, INK)]
    p.append(f'<text x="{m}" y="1220" font-size="38" fill="{INK}">Venue figure is about '
             f'<tspan font-weight="bold" fill="{ORANGE}">{v["v_om_x"]}x</tspan> the one-sided count</text>')
    p.append(f'<line x1="{m}" x2="{w - m}" y1="1262" y2="1262" stroke="{GRID}" stroke-width="2"/>')
    p.append(text(m, 1310, "Marco Amendola · data and code: github.com/x-pertknight/polymarket-fill-counting", 26, SOFT))
    p.append("</svg>")
    return "\n".join(p)


def main():
    v = values()
    svg = os.path.join(ROOT, "charts", "summary.svg")
    os.makedirs(os.path.dirname(svg), exist_ok=True)
    open(svg, "w").write(build(v))
    png = svg.replace(".svg", ".png")
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--window-size=1080,1350",
                    f"--screenshot={os.path.abspath(png)}", "file://" + os.path.abspath(svg)], check=True, capture_output=True)
    print(v)


if __name__ == "__main__":
    main()
