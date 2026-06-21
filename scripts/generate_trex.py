#!/usr/bin/env python3
"""
T-Rex Contribution Game generator.

Reads a GitHub contribution calendar and produces an animated SVG in which the
Chrome dinosaur runs across your commit graph and jumps over your busiest weeks
(the "cacti"). Output is a self-contained SVG using SMIL animation, so it plays
automatically when embedded in a GitHub README (no JavaScript needed).

Usage:
    # From real contribution JSON fetched in a GitHub Action:
    python generate_trex.py --input contributions.json --output assets/dino-game.svg

    # Generate a preview with synthetic data (no token needed):
    python generate_trex.py --demo --output assets/dino-game.svg

The --input JSON is expected in the shape returned by the GitHub GraphQL
contributionsCollection -> contributionCalendar:
{
  "weeks": [
    {"contributionDays": [{"contributionCount": 3, "weekday": 0}, ...]},
    ...
  ]
}
"""

import argparse
import json
import random

# ----- Layout constants -------------------------------------------------------
CELL = 13          # contribution cell size (px)
GAP = 3            # gap between cells
STEP = CELL + GAP  # 16
ROWS = 7
MARGIN_X = 24
TOP = 56           # space reserved for the title
GROUND_PAD = 22    # gap between grid bottom and the ground line
DINO_PX = 2        # pixel scale for the dino sprite
JUMP_H = 46        # how high the dino jumps
RUN_SECONDS = 22   # one full left-to-right run

# Cyan / tokyo-night flavoured palette to match the accent colour 00E5FF
LEVEL_COLORS = ["#161b22", "#0e3a4a", "#10637d", "#1aa3c0", "#39d3e0"]
DINO_COLOR = "#e6edf3"
DINO_EYE = "#0d1117"
CACTUS_COLOR = "#2ea043"
GROUND_COLOR = "#30363d"
PANEL = "#0d1117"
PANEL_STROKE = "#1f6feb"
TITLE_COLOR = "#58a6ff"

# Classic Chrome-dino silhouette as a pixel map (faces right). '#' = filled.
# Every row MUST be exactly 16 characters wide.
DINO_BODY = [
    ".........######.",  # 0  head top
    ".........######.",  # 1  head (eye hole punched in by `eye` rect)
    ".........######.",  # 2  head
    ".........######.",  # 3  head
    ".........#####..",  # 4  jaw
    ".........###....",  # 5  snout / neck
    "#........####...",  # 6  tail tip + neck
    "##......#####...",  # 7
    "###....######...",  # 8
    "####..#######...",  # 9
    "#############...",  # 10 back
    "#############...",  # 11 body
    ".############...",  # 12 belly
    "..##########....",  # 13
    "...########.....",  # 14
    "....######......",  # 15 lower body
]
# Two leg frames (rows below the body) for the running cycle.
LEGS_A = [
    ".....#..#.......",
    ".....#..#.......",
    ".....#..##......",
]
LEGS_B = [
    ".....#..#.......",
    ".....#..#.......",
    "....##..#.......",
]


def level_of(count, thresholds):
    if count <= 0:
        return 0
    for i, t in enumerate(thresholds, start=1):
        if count <= t:
            return i
    return 4


def load_weeks(path):
    with open(path) as f:
        data = json.load(f)
    # accept either the calendar object directly or a wrapper
    cal = data.get("contributionCalendar", data)
    weeks_raw = cal["weeks"]
    counts = []
    for w in weeks_raw:
        col = [0] * ROWS
        for d in w["contributionDays"]:
            wd = d.get("weekday", 0)
            col[wd] = d.get("contributionCount", 0)
        counts.append(col)
    return counts


def demo_weeks(n=53, seed=7):
    random.seed(seed)
    weeks = []
    for c in range(n):
        col = []
        # create occasional "busy" weeks so there are cacti to jump
        busy = random.random() < 0.18
        for _ in range(ROWS):
            if busy and random.random() < 0.5:
                col.append(random.randint(8, 20))
            else:
                col.append(random.choice([0, 0, 0, 1, 2, 3, 5]))
        weeks.append(col)
    return weeks


def build_quantile_thresholds(weeks):
    flat = sorted(c for col in weeks for c in col if c > 0)
    if not flat:
        return [1, 3, 6]
    def q(p):
        return flat[min(len(flat) - 1, int(len(flat) * p))]
    return [q(0.25), q(0.5), q(0.85)]


def pixels_to_rects(pixel_rows, ox, oy, scale, color):
    rects = []
    for r, row in enumerate(pixel_rows):
        for c, ch in enumerate(row):
            if ch == "#":
                x = ox + c * scale
                y = oy + r * scale
                rects.append(
                    f'<rect x="{x:.1f}" y="{y:.1f}" width="{scale}" height="{scale}" fill="{color}"/>'
                )
    return "".join(rects)


def generate(weeks, output):
    cols = len(weeks)
    thresholds = build_quantile_thresholds(weeks)

    grid_w = cols * STEP - GAP
    grid_h = ROWS * STEP - GAP
    ground_y = TOP + grid_h + GROUND_PAD
    width = MARGIN_X * 2 + grid_w
    height = ground_y + 30

    dino_h_px = len(DINO_BODY) + len(LEGS_A)
    dino_w = len(DINO_BODY[0]) * DINO_PX
    dino_h = dino_h_px * DINO_PX

    # ---- contribution grid ----
    cells = []
    for c, col in enumerate(weeks):
        for r in range(ROWS):
            lvl = level_of(col[r], thresholds)
            x = MARGIN_X + c * STEP
            y = TOP + r * STEP
            cells.append(
                f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="3" '
                f'fill="{LEVEL_COLORS[lvl]}"/>'
            )

    # ---- obstacles (cacti) on busy weeks ----
    obstacle_fracs = []
    cacti = []
    start_x = -dino_w - 10
    end_x = width + dino_w + 10
    travel = end_x - start_x
    for c, col in enumerate(weeks):
        if max(col) >= thresholds[-1] and max(col) > 0:
            cx = MARGIN_X + c * STEP + CELL / 2
            # draw a small cactus standing on the ground line
            cw, ch = 6, 22
            cactus = (
                f'<g transform="translate({cx - cw/2:.1f},{ground_y - ch})">'
                f'<rect x="0" y="0" width="{cw}" height="{ch}" rx="2" fill="{CACTUS_COLOR}"/>'
                f'<rect x="-4" y="6" width="4" height="8" rx="2" fill="{CACTUS_COLOR}"/>'
                f'<rect x="{cw}" y="3" width="4" height="9" rx="2" fill="{CACTUS_COLOR}"/>'
                f"</g>"
            )
            cacti.append(cactus)
            # fraction of the run when the dino centre is over this column
            dino_center_offset = dino_w / 2
            f = (cx - dino_center_offset - start_x) / travel
            if 0.02 < f < 0.98:
                obstacle_fracs.append(f)

    obstacle_fracs.sort()

    # ---- build the jump (translateY) keyframes synced to obstacles ----
    half = 0.022  # half-width of a jump in run-fraction
    values = [0.0]
    times = [0.0]
    last_t = 0.0
    for f in obstacle_fracs:
        a, peak, b = f - half, f, f + half
        if a <= last_t + 0.004:  # too close to previous jump, skip
            continue
        values += [0.0, -JUMP_H, 0.0]
        times += [round(a, 4), round(peak, 4), round(b, 4)]
        last_t = b
    values.append(0.0)
    times.append(1.0)
    jump_values = ";".join(f"{v:.1f}" for v in values)
    jump_times = ";".join(f"{t:.4f}" for t in times)

    # ---- dino sprite (legs toggle for the run cycle) ----
    body = pixels_to_rects(DINO_BODY, 0, 0, DINO_PX, DINO_COLOR)
    legs_a = pixels_to_rects(LEGS_A, 0, len(DINO_BODY) * DINO_PX, DINO_PX, DINO_COLOR)
    legs_b = pixels_to_rects(LEGS_B, 0, len(DINO_BODY) * DINO_PX, DINO_PX, DINO_COLOR)
    # eye knocked out of the head
    eye = f'<rect x="{13*DINO_PX}" y="{1*DINO_PX}" width="{DINO_PX}" height="{DINO_PX}" fill="{DINO_EYE}"/>'

    dino_sprite = f"""
      <g>{body}{eye}</g>
      <g opacity="1">{legs_a}
        <animate attributeName="opacity" values="1;0;1" dur="0.28s" repeatCount="indefinite"/>
      </g>
      <g opacity="0">{legs_b}
        <animate attributeName="opacity" values="0;1;0" dur="0.28s" repeatCount="indefinite"/>
      </g>
    """

    # outer group = horizontal run; inner group = vertical jump
    dino_rest_y = ground_y - dino_h
    dino = f"""
    <g transform="translate({start_x:.1f},{dino_rest_y:.1f})">
      <animateTransform attributeName="transform" type="translate"
        values="{start_x:.1f},{dino_rest_y:.1f};{end_x:.1f},{dino_rest_y:.1f}"
        dur="{RUN_SECONDS}s" repeatCount="indefinite" calcMode="linear"/>
      <g>
        <animateTransform attributeName="transform" type="translate"
          values="{';'.join(f'0,{v:.1f}' for v in values)}"
          keyTimes="{jump_times}"
          dur="{RUN_SECONDS}s" repeatCount="indefinite" calcMode="spline"
          keySplines="{' ; '.join(['0.3 0 0.7 1'] * (len(values)-1))}"/>
        {dino_sprite}
      </g>
    </g>
    """

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" role="img" aria-label="T-Rex running across the contribution graph">
  <rect x="0.5" y="0.5" width="{width-1}" height="{height-1}" rx="12" fill="{PANEL}" stroke="{PANEL_STROKE}" stroke-opacity="0.35"/>
  <text x="{MARGIN_X}" y="34" font-family="'JetBrains Mono','Segoe UI',monospace" font-size="18" font-weight="700" fill="{TITLE_COLOR}">&#129430; T-Rex Commit Run</text>
  <text x="{width-MARGIN_X}" y="34" text-anchor="end" font-family="'JetBrains Mono',monospace" font-size="11" fill="#6e7681">jumping every busy week</text>
  <g>{''.join(cells)}</g>
  <line x1="{MARGIN_X-6}" y1="{ground_y}" x2="{width-MARGIN_X+6}" y2="{ground_y}" stroke="{GROUND_COLOR}" stroke-width="2"/>
  <g>{''.join(cacti)}</g>
  {dino}
</svg>
"""
    with open(output, "w") as f:
        f.write(svg)
    print(f"Wrote {output}  ({width}x{height}, {len(cacti)} cacti, {len(obstacle_fracs)} synced jumps)")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input")
    p.add_argument("--output", required=True)
    p.add_argument("--demo", action="store_true")
    args = p.parse_args()

    if args.demo or not args.input:
        weeks = demo_weeks()
    else:
        weeks = load_weeks(args.input)
    generate(weeks, args.output)


if __name__ == "__main__":
    main()
