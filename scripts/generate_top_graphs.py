#!/usr/bin/env python3
"""Generate GitHub-friendly SVG plots from top/top_run.csv.

The Custom WaveView export used here is whitespace-delimited and may contain
multiple appended tables. This script parses all tables, reconstructs bus
values, detects loop update edges, and writes static SVG plots under docs/img.
It intentionally uses only the Python standard library so it can run in a
minimal environment.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import html
import math
import sys
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "top" / "top_run.csv"
OUT_DIR = ROOT / "docs" / "img"


COLORS = [
    "#005f73",
    "#ae2012",
    "#0a9396",
    "#ca6702",
    "#3a0ca3",
    "#2b9348",
    "#9b2226",
    "#4361ee",
]


@dataclass
class Series:
    name: str
    x: list[float]
    y: list[float]
    color: str
    width: float = 1.6


@dataclass
class Panel:
    title: str
    ylabel: str
    series: list[Series]
    yrange: tuple[float, float] | None = None


def clean_columns(header_line: str) -> list[str]:
    return [token.split("|", 1)[-1] for token in header_line.split()]


def signed(value: int, bits: int) -> int:
    sign = 1 << (bits - 1)
    full = 1 << bits
    return value - full if value & sign else value


def parse_top_csv(path: Path) -> tuple[list[dict[str, float]], list[dict[str, float]], list[dict[str, float]]]:
    rows: list[dict[str, float]] = []
    dlf_events: list[dict[str, float]] = []
    hold_events: list[dict[str, float]] = []

    cols: list[str] | None = None
    index: dict[str, int] = {}
    prev_clk_sample = 0
    prev_data_out = 0

    def bus_value(parts: list[str], prefix: str) -> int:
        value = 0
        for col, raw in zip(cols or [], parts):
            if col.startswith(prefix + "<"):
                bit = int(col.split("<", 1)[1].split(">", 1)[0])
                if float(raw) > 0.5:
                    value |= 1 << bit
        return value

    with path.open("r", encoding="utf-8", errors="replace") as f:
        for raw_line in f:
            line = raw_line.lstrip()
            if line.startswith("#format"):
                cols = None
                index = {}
                prev_clk_sample = 0
                prev_data_out = 0
                continue
            if line.startswith("#") or not line.strip():
                continue
            if line.startswith("TIME"):
                cols = clean_columns(line)
                index = {name: i for i, name in enumerate(cols)}
                prev_clk_sample = 0
                prev_data_out = 0
                continue
            if cols is None:
                continue

            parts = line.split()
            if len(parts) != len(cols):
                continue

            t_us = float(parts[index["TIME"]]) * 1e6
            data_out = 1 if float(parts[index["DATA_OUT"]]) > 0.5 else 0
            clk_sample = 1 if float(parts[index["CLK_DATASAMPLE"]]) > 0.5 else 0

            row = {
                "t_us": t_us,
                "oref": float(parts[index["oref"]]),
                "osc1": float(parts[index["I0.osc1"]]),
                "osc2": float(parts[index["I0.osc2"]]),
                "osc11": float(parts[index["I0.osc11"]]),
                "osc22": float(parts[index["I0.osc22"]]),
                "vrc1": float(parts[index["I0.VRC1"]]),
                "vrc2": float(parts[index["I0.VRC2"]]),
                "data_out": float(parts[index["DATA_OUT"]]),
                "clk_sample": float(parts[index["CLK_DATASAMPLE"]]),
                "clk_osc": float(parts[index["CLK_OSC"]]),
            }
            rows.append(row)

            if data_out and not prev_data_out:
                cp1 = bus_value(parts, "CP1")
                cp2 = bus_value(parts, "CP2")
                hold_events.append(
                    {
                        "t_us": t_us,
                        "cp1": cp1,
                        "cp2": cp2,
                        "cp_delta": cp2 - cp1,
                        "oref": row["oref"],
                        "vrc1": row["vrc1"],
                        "vrc2": row["vrc2"],
                    }
                )

            if clk_sample and not prev_clk_sample:
                dd1 = bus_value(parts, "I3.DD1_SAMPLE")
                dd2 = bus_value(parts, "I3.DD2_SAMPLE")
                diff_sample = signed(bus_value(parts, "I3.DIFF_SAMPLE"), 12)
                diff = signed(bus_value(parts, "I3.DIFF"), 12)
                diff_out = signed(bus_value(parts, "I3.DIFF_OUT1"), 17)
                d_code = bus_value(parts, "D")
                dlf_events.append(
                    {
                        "t_us": t_us,
                        "dd1": dd1,
                        "dd2": dd2,
                        "dd_delta": dd2 - dd1,
                        "diff_sample": diff_sample,
                        "diff": diff,
                        "diff_out": diff_out,
                        "d_code": d_code,
                        "oref": row["oref"],
                    }
                )

            prev_data_out = data_out
            prev_clk_sample = clk_sample

    return rows, dlf_events, hold_events


def downsample(rows: list[dict[str, float]], max_points: int = 1800) -> list[dict[str, float]]:
    if len(rows) <= max_points:
        return rows
    step = math.ceil(len(rows) / max_points)
    return rows[::step]


def filter_window(rows: Iterable[dict[str, float]], start_us: float, stop_us: float) -> list[dict[str, float]]:
    return [row for row in rows if start_us <= row["t_us"] <= stop_us]


def values(rows: list[dict[str, float]], key: str) -> list[float]:
    return [float(row[key]) for row in rows]


def make_series(rows: list[dict[str, float]], key: str, label: str, color_index: int, width: float = 1.6) -> Series:
    return Series(label, values(rows, "t_us"), values(rows, key), COLORS[color_index % len(COLORS)], width)


def nice_range(series: list[Series], forced: tuple[float, float] | None) -> tuple[float, float]:
    if forced is not None:
        return forced
    all_values = [v for s in series for v in s.y if math.isfinite(v)]
    if not all_values:
        return 0.0, 1.0
    low = min(all_values)
    high = max(all_values)
    if low == high:
        pad = max(abs(low) * 0.05, 1.0)
        return low - pad, high + pad
    pad = (high - low) * 0.08
    return low - pad, high + pad


def points_for(series: Series, xmin: float, xmax: float, ymin: float, ymax: float, x0: float, y0: float, width: float, height: float) -> str:
    if xmax == xmin:
        xmax = xmin + 1.0
    if ymax == ymin:
        ymax = ymin + 1.0
    pts = []
    for x, y in zip(series.x, series.y):
        if not (math.isfinite(x) and math.isfinite(y)):
            continue
        px = x0 + (x - xmin) / (xmax - xmin) * width
        py = y0 + height - (y - ymin) / (ymax - ymin) * height
        pts.append(f"{px:.2f},{py:.2f}")
    return " ".join(pts)


def svg_plot(path: Path, title: str, panels: list[Panel], width: int = 1120, panel_height: int = 230) -> None:
    margin_left = 82
    margin_right = 26
    margin_top = 74
    gap = 56
    margin_bottom = 58
    plot_width = width - margin_left - margin_right
    total_height = margin_top + len(panels) * panel_height + (len(panels) - 1) * gap + margin_bottom

    all_x = [x for panel in panels for s in panel.series for x in s.x if math.isfinite(x)]
    xmin = min(all_x) if all_x else 0.0
    xmax = max(all_x) if all_x else 1.0

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{total_height}" viewBox="0 0 {width} {total_height}">',
        '<rect width="100%" height="100%" fill="#fbfbf8"/>',
        f'<text x="{margin_left}" y="34" font-family="Arial, sans-serif" font-size="22" font-weight="700" fill="#202124">{html.escape(title)}</text>',
        f'<text x="{margin_left}" y="58" font-family="Arial, sans-serif" font-size="13" fill="#5f6368">source: top/top_run.csv</text>',
    ]

    for panel_index, panel in enumerate(panels):
        y_top = margin_top + panel_index * (panel_height + gap)
        ymin, ymax = nice_range(panel.series, panel.yrange)
        parts.append(f'<text x="{margin_left}" y="{y_top - 15}" font-family="Arial, sans-serif" font-size="15" font-weight="700" fill="#202124">{html.escape(panel.title)}</text>')
        parts.append(f'<rect x="{margin_left}" y="{y_top}" width="{plot_width}" height="{panel_height}" fill="#ffffff" stroke="#dadce0" stroke-width="1"/>')

        for frac in (0.0, 0.25, 0.5, 0.75, 1.0):
            y = y_top + panel_height - frac * panel_height
            value = ymin + frac * (ymax - ymin)
            parts.append(f'<line x1="{margin_left}" y1="{y:.2f}" x2="{margin_left + plot_width}" y2="{y:.2f}" stroke="#eceff1" stroke-width="1"/>')
            parts.append(f'<text x="{margin_left - 10}" y="{y + 4:.2f}" font-family="Arial, sans-serif" font-size="11" text-anchor="end" fill="#6b7280">{value:.3g}</text>')

        for frac in (0.0, 0.25, 0.5, 0.75, 1.0):
            x = margin_left + frac * plot_width
            value = xmin + frac * (xmax - xmin)
            parts.append(f'<line x1="{x:.2f}" y1="{y_top}" x2="{x:.2f}" y2="{y_top + panel_height}" stroke="#f1f3f4" stroke-width="1"/>')
            parts.append(f'<text x="{x:.2f}" y="{y_top + panel_height + 22}" font-family="Arial, sans-serif" font-size="11" text-anchor="middle" fill="#6b7280">{value:.1f}</text>')

        parts.append(f'<text x="{margin_left - 58}" y="{y_top + panel_height / 2:.2f}" transform="rotate(-90 {margin_left - 58},{y_top + panel_height / 2:.2f})" font-family="Arial, sans-serif" font-size="12" text-anchor="middle" fill="#5f6368">{html.escape(panel.ylabel)}</text>')

        for series in panel.series:
            pts = points_for(series, xmin, xmax, ymin, ymax, margin_left, y_top, plot_width, panel_height)
            parts.append(f'<polyline fill="none" stroke="{series.color}" stroke-width="{series.width}" stroke-linejoin="round" stroke-linecap="round" points="{pts}"/>')

        legend_x = margin_left + 8
        legend_y = y_top + 18
        for series in panel.series:
            parts.append(f'<line x1="{legend_x}" y1="{legend_y}" x2="{legend_x + 24}" y2="{legend_y}" stroke="{series.color}" stroke-width="3"/>')
            parts.append(f'<text x="{legend_x + 31}" y="{legend_y + 4}" font-family="Arial, sans-serif" font-size="12" fill="#374151">{html.escape(series.name)}</text>')
            legend_x += 98 + len(series.name) * 6

    parts.append(f'<text x="{margin_left + plot_width / 2:.2f}" y="{total_height - 20}" font-family="Arial, sans-serif" font-size="12" text-anchor="middle" fill="#5f6368">time (us)</text>')
    parts.append("</svg>")
    path.write_text("\n".join(parts), encoding="utf-8")


def write_markdown_summary(path: Path, rows: list[dict[str, float]], dlf_events: list[dict[str, float]], hold_events: list[dict[str, float]]) -> None:
    def fmt(value: float, digits: int = 3) -> str:
        return f"{value:.{digits}f}"

    last_dlf = dlf_events[-1] if dlf_events else {}
    last_hold = hold_events[-1] if hold_events else {}
    oref_values = values(rows, "oref")
    lines = [
        "# Top Closed-Loop Run Summary",
        "",
        "Generated by `scripts/generate_top_graphs.py` from `top/top_run.csv`.",
        "",
        "| Item | Value |",
        "|------|------:|",
        f"| Samples | {len(rows)} |",
        f"| Time span | {fmt(rows[0]['t_us'])} us to {fmt(rows[-1]['t_us'])} us |" if rows else "| Time span | n/a |",
        f"| DATA_OUT hold events | {len(hold_events)} |",
        f"| DLF update events | {len(dlf_events)} |",
        f"| oref min / max | {min(oref_values):.6f} V / {max(oref_values):.6f} V |" if oref_values else "| oref min / max | n/a |",
        f"| Last DD2-DD1 | {last_dlf.get('dd_delta', 'n/a')} code |",
        f"| Last DLF diff bus | {last_dlf.get('diff', 'n/a')} code |",
        f"| Last D code | {last_dlf.get('d_code', 'n/a')} |",
        f"| Last oref | {last_dlf.get('oref', float('nan')):.6f} V |" if last_dlf else "| Last oref | n/a |",
        f"| Last CP2-CP1 at hold | {last_hold.get('cp_delta', 'n/a')} code |",
        "",
        "The exported waveform contains the startup transient and the later low-error region. "
        "Use the SVG plots in `docs/img/` for visual inspection.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    if not CSV_PATH.exists():
        print(f"missing input: {CSV_PATH}", file=sys.stderr)
        return 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows, dlf_events, hold_events = parse_top_csv(CSV_PATH)
    if not rows:
        print("no rows parsed", file=sys.stderr)
        return 1

    overview_rows = downsample(rows)
    zoom_rows = downsample(filter_window(rows, 170.0, 180.0), 1800)

    svg_plot(
        OUT_DIR / "top_loop_overview.svg",
        "Top Loop Overview",
        [
            Panel("RC ramp and oref", "V", [
                make_series(overview_rows, "vrc1", "VRC1", 0),
                make_series(overview_rows, "vrc2", "VRC2", 1),
                make_series(overview_rows, "oref", "oref", 2),
            ]),
            Panel("Comparator-facing oscillator nodes", "V", [
                make_series(overview_rows, "osc1", "osc1", 0),
                make_series(overview_rows, "osc2", "osc2", 1),
                make_series(overview_rows, "osc11", "osc11", 2),
                make_series(overview_rows, "osc22", "osc22", 3),
            ]),
            Panel("Loop timing controls", "logic", [
                make_series(overview_rows, "data_out", "DATA_OUT", 4),
                make_series(overview_rows, "clk_sample", "CLK_DATASAMPLE", 5),
                make_series(overview_rows, "clk_osc", "CLK_OSC", 6),
            ], (-0.1, 1.1)),
        ],
    )

    svg_plot(
        OUT_DIR / "top_dlf_convergence.svg",
        "DLF Convergence at CLK_DATASAMPLE Edges",
        [
            Panel("Sampled SAR codes", "code", [
                make_series(dlf_events, "dd1", "DD1", 0),
                make_series(dlf_events, "dd2", "DD2", 1),
            ]),
            Panel("Error toward zero", "code", [
                make_series(dlf_events, "dd_delta", "DD2-DD1", 2),
                make_series(dlf_events, "diff", "DIFF", 3),
            ]),
            Panel("DLF DAC drive", "code", [
                make_series(dlf_events, "d_code", "D<16:0>", 4),
            ]),
            Panel("oref actuator voltage", "V", [
                make_series(dlf_events, "oref", "oref", 5),
            ]),
        ],
    )

    svg_plot(
        OUT_DIR / "top_cp_hold_codes.svg",
        "CP Code Captured at DATA_OUT Hold Edges",
        [
            Panel("Hold-time CP codes", "code", [
                make_series(hold_events, "cp1", "CP1", 0),
                make_series(hold_events, "cp2", "CP2", 1),
            ]),
            Panel("Hold-time CP difference", "code", [
                make_series(hold_events, "cp_delta", "CP2-CP1", 2),
            ]),
            Panel("oref and held ramp voltages", "V", [
                make_series(hold_events, "vrc1", "VRC1", 0),
                make_series(hold_events, "vrc2", "VRC2", 1),
                make_series(hold_events, "oref", "oref", 2),
            ]),
        ],
    )

    svg_plot(
        OUT_DIR / "top_late_loop_zoom.svg",
        "Late Loop Zoom: Comparator Timing Window",
        [
            Panel("Late RC ramp and oref", "V", [
                make_series(zoom_rows, "vrc1", "VRC1", 0),
                make_series(zoom_rows, "vrc2", "VRC2", 1),
                make_series(zoom_rows, "oref", "oref", 2),
            ]),
            Panel("170-180 us oscillator crossing detail", "V", [
                make_series(zoom_rows, "osc1", "osc1", 0),
                make_series(zoom_rows, "osc2", "osc2", 1),
                make_series(zoom_rows, "osc11", "osc11", 2),
                make_series(zoom_rows, "osc22", "osc22", 3),
            ]),
            Panel("Hold/update pulses", "logic", [
                make_series(zoom_rows, "data_out", "DATA_OUT", 4),
                make_series(zoom_rows, "clk_sample", "CLK_DATASAMPLE", 5),
                make_series(zoom_rows, "clk_osc", "CLK_OSC", 6),
            ], (-0.1, 1.1)),
        ],
    )

    write_markdown_summary(ROOT / "docs" / "top_run_summary.md", rows, dlf_events, hold_events)
    print(f"parsed {len(rows)} rows, {len(hold_events)} hold events, {len(dlf_events)} DLF updates")
    print(f"wrote SVG plots to {OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
