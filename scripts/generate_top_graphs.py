#!/usr/bin/env python3
"""Analyze top/top_run.csv and generate GitHub-friendly SVG plots.

The Custom WaveView export is whitespace-delimited and can contain appended
tables. The important detail is timing:

- DATA_OUT rising edge: CP1/CP2 hold codes are valid at the edge.
- CLK_DATASAMPLE rising edge: DLF outputs need a short settle delay before
  DIFF/oref are meaningful. This script samples DLF rows 20 ns after the edge.

No third-party Python packages are required.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import csv
import html
import math
import sys


ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "top" / "top_run.csv"
OUT_DIR = ROOT / "docs" / "img"
DLF_SETTLE_NS = 20.0


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
    width: float = 1.7


@dataclass
class Panel:
    title: str
    ylabel: str
    series: list[Series]
    yrange: tuple[float, float] | None = None


def clean_columns(header_line: str) -> list[str]:
    return [token.split("|", 1)[-1] for token in header_line.split()]


def signed(value: int, bits: int) -> int:
    return value - (1 << bits) if value & (1 << (bits - 1)) else value


def bus_value(cols: list[str], parts: list[str], prefix: str) -> int:
    value = 0
    for col, raw in zip(cols, parts):
        if col.startswith(prefix + "<") and float(raw) > 0.5:
            bit = int(col.split("<", 1)[1].split(">", 1)[0])
            value |= 1 << bit
    return value


def row_from_parts(cols: list[str], index: dict[str, int], parts: list[str]) -> dict[str, float]:
    dd1 = bus_value(cols, parts, "I3.DD1_SAMPLE")
    dd2 = bus_value(cols, parts, "I3.DD2_SAMPLE")
    cp1 = bus_value(cols, parts, "CP1")
    cp2 = bus_value(cols, parts, "CP2")
    vrc1 = float(parts[index["I0.VRC1"]])
    vrc2 = float(parts[index["I0.VRC2"]])
    return {
        "t_us": float(parts[index["TIME"]]) * 1e6,
        "cp1": cp1,
        "cp2": cp2,
        "cp_delta": cp2 - cp1,
        "dd1": dd1,
        "dd2": dd2,
        "dd_delta": dd2 - dd1,
        "diff_sample": signed(bus_value(cols, parts, "I3.DIFF_SAMPLE"), 12),
        "diff": signed(bus_value(cols, parts, "I3.DIFF"), 12),
        "diff_out": signed(bus_value(cols, parts, "I3.DIFF_OUT1"), 17),
        "d_code": bus_value(cols, parts, "D"),
        "oref": float(parts[index["oref"]]),
        "osc1": float(parts[index["I0.osc1"]]),
        "osc2": float(parts[index["I0.osc2"]]),
        "osc11": float(parts[index["I0.osc11"]]),
        "osc22": float(parts[index["I0.osc22"]]),
        "vrc1": vrc1,
        "vrc2": vrc2,
        "vrc_diff": vrc1 - vrc2,
        "data_out": float(parts[index["DATA_OUT"]]),
        "clk_sample": float(parts[index["CLK_DATASAMPLE"]]),
        "clk_osc": float(parts[index["CLK_OSC"]]),
    }


def parse_top_csv(path: Path) -> tuple[list[dict[str, float]], list[dict[str, float]], list[dict[str, float]]]:
    rows: list[dict[str, float]] = []
    hold_edge_indices: list[int] = []
    dlf_edge_indices: list[int] = []

    cols: list[str] | None = None
    index: dict[str, int] = {}
    prev_data_out = 0
    prev_clk_sample = 0

    with path.open("r", encoding="utf-8", errors="replace") as f:
        for raw_line in f:
            line = raw_line.lstrip()
            if line.startswith("#format"):
                cols = None
                index = {}
                prev_data_out = 0
                prev_clk_sample = 0
                continue
            if line.startswith("#") or not line.strip():
                continue
            if line.startswith("TIME"):
                cols = clean_columns(line)
                index = {name: i for i, name in enumerate(cols)}
                prev_data_out = 0
                prev_clk_sample = 0
                continue
            if cols is None:
                continue

            parts = line.split()
            if len(parts) != len(cols):
                continue

            row = row_from_parts(cols, index, parts)
            data_out = 1 if row["data_out"] > 0.5 else 0
            clk_sample = 1 if row["clk_sample"] > 0.5 else 0

            if data_out and not prev_data_out:
                hold_edge_indices.append(len(rows))
            if clk_sample and not prev_clk_sample:
                dlf_edge_indices.append(len(rows))

            rows.append(row)
            prev_data_out = data_out
            prev_clk_sample = clk_sample

    hold_events: list[dict[str, float]] = []
    for n, edge_index in enumerate(hold_edge_indices):
        row = dict(rows[edge_index])
        row["event"] = n
        row["sample_t_us"] = row["t_us"]
        if hold_events:
            row["dt_us"] = row["t_us"] - hold_events[-1]["t_us"]
            row["freq_khz"] = 1000.0 / row["dt_us"] if row["dt_us"] else math.nan
        else:
            row["dt_us"] = math.nan
            row["freq_khz"] = math.nan
        hold_events.append(row)

    dlf_events: list[dict[str, float]] = []
    for n, edge_index in enumerate(dlf_edge_indices):
        edge_time = rows[edge_index]["t_us"]
        target_time = edge_time + DLF_SETTLE_NS / 1000.0
        sample_index = edge_index
        while sample_index + 1 < len(rows) and rows[sample_index]["t_us"] < target_time:
            sample_index += 1
        row = dict(rows[sample_index])
        row["event"] = n
        row["edge_t_us"] = edge_time
        row["sample_t_us"] = row["t_us"]
        row["settle_ns"] = (row["t_us"] - edge_time) * 1000.0
        dlf_events.append(row)

    return rows, dlf_events, hold_events


def downsample(rows: list[dict[str, float]], max_points: int = 1800) -> list[dict[str, float]]:
    if len(rows) <= max_points:
        return rows
    step = math.ceil(len(rows) / max_points)
    return rows[::step]


def filter_window(rows: list[dict[str, float]], start_us: float, stop_us: float) -> list[dict[str, float]]:
    return [row for row in rows if start_us <= row["t_us"] <= stop_us]


def values(rows: list[dict[str, float]], key: str) -> list[float]:
    return [float(row[key]) for row in rows]


def make_series(rows: list[dict[str, float]], xkey: str, ykey: str, label: str, color_index: int, width: float = 1.7) -> Series:
    return Series(label, values(rows, xkey), values(rows, ykey), COLORS[color_index % len(COLORS)], width)


def nice_range(series: list[Series], forced: tuple[float, float] | None) -> tuple[float, float]:
    if forced is not None:
        return forced
    all_values = [v for item in series for v in item.y if math.isfinite(v)]
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


def svg_plot(path: Path, title: str, panels: list[Panel], xlabel: str, width: int = 1120, panel_height: int = 220) -> None:
    margin_left = 86
    margin_right = 28
    margin_top = 76
    gap = 55
    margin_bottom = 58
    plot_width = width - margin_left - margin_right
    total_height = margin_top + len(panels) * panel_height + (len(panels) - 1) * gap + margin_bottom

    all_x = [x for panel in panels for series in panel.series for x in series.x if math.isfinite(x)]
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
        parts.append(f'<text x="{margin_left}" y="{y_top - 14}" font-family="Arial, sans-serif" font-size="15" font-weight="700" fill="#202124">{html.escape(panel.title)}</text>')
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
            parts.append(f'<text x="{x:.2f}" y="{y_top + panel_height + 21}" font-family="Arial, sans-serif" font-size="11" text-anchor="middle" fill="#6b7280">{value:.1f}</text>')

        zero_y = None
        if ymin < 0 < ymax:
            zero_y = y_top + panel_height - (0 - ymin) / (ymax - ymin) * panel_height
            parts.append(f'<line x1="{margin_left}" y1="{zero_y:.2f}" x2="{margin_left + plot_width}" y2="{zero_y:.2f}" stroke="#9aa0a6" stroke-width="1.2" stroke-dasharray="5,5"/>')

        parts.append(f'<text x="{margin_left - 60}" y="{y_top + panel_height / 2:.2f}" transform="rotate(-90 {margin_left - 60},{y_top + panel_height / 2:.2f})" font-family="Arial, sans-serif" font-size="12" text-anchor="middle" fill="#5f6368">{html.escape(panel.ylabel)}</text>')

        for series in panel.series:
            pts = points_for(series, xmin, xmax, ymin, ymax, margin_left, y_top, plot_width, panel_height)
            parts.append(f'<polyline fill="none" stroke="{series.color}" stroke-width="{series.width}" stroke-linejoin="round" stroke-linecap="round" points="{pts}"/>')
            for x, y in zip(series.x, series.y):
                if not (math.isfinite(x) and math.isfinite(y)):
                    continue
                px = margin_left + (x - xmin) / (xmax - xmin or 1.0) * plot_width
                py = y_top + panel_height - (y - ymin) / (ymax - ymin or 1.0) * panel_height
                if len(series.x) <= 120:
                    parts.append(f'<circle cx="{px:.2f}" cy="{py:.2f}" r="2.5" fill="{series.color}"/>')

        legend_x = margin_left + 8
        legend_y = y_top + 18
        for series in panel.series:
            parts.append(f'<line x1="{legend_x}" y1="{legend_y}" x2="{legend_x + 24}" y2="{legend_y}" stroke="{series.color}" stroke-width="3"/>')
            parts.append(f'<text x="{legend_x + 31}" y="{legend_y + 4}" font-family="Arial, sans-serif" font-size="12" fill="#374151">{html.escape(series.name)}</text>')
            legend_x += 98 + len(series.name) * 6

    parts.append(f'<text x="{margin_left + plot_width / 2:.2f}" y="{total_height - 20}" font-family="Arial, sans-serif" font-size="12" text-anchor="middle" fill="#5f6368">{html.escape(xlabel)}</text>')
    parts.append("</svg>")
    path.write_text("\n".join(parts), encoding="utf-8")


def write_event_csv(path: Path, dlf_events: list[dict[str, float]], hold_events: list[dict[str, float]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["type", "event", "t_us", "dd1", "dd2", "dd2_minus_dd1", "diff", "d_code", "oref", "cp1", "cp2", "cp2_minus_cp1", "dt_us", "freq_khz"])
        for row in dlf_events:
            writer.writerow(["dlf", int(row["event"]), f"{row['sample_t_us']:.3f}", int(row["dd1"]), int(row["dd2"]), int(row["dd_delta"]), int(row["diff"]), int(row["d_code"]), f"{row['oref']:.7f}", "", "", "", "", ""])
        for row in hold_events:
            writer.writerow(["hold", int(row["event"]), f"{row['t_us']:.3f}", "", "", "", "", "", f"{row['oref']:.7f}", int(row["cp1"]), int(row["cp2"]), int(row["cp_delta"]), "" if math.isnan(row["dt_us"]) else f"{row['dt_us']:.3f}", "" if math.isnan(row["freq_khz"]) else f"{row['freq_khz']:.3f}"])


def write_markdown_summary(path: Path, rows: list[dict[str, float]], dlf_events: list[dict[str, float]], hold_events: list[dict[str, float]]) -> None:
    last_dlf = dlf_events[-1]
    late_dlf = dlf_events[-12:]
    last_hold = hold_events[-1]
    late_hold = [row for row in hold_events[-20:] if math.isfinite(row["freq_khz"])]
    oref_values = values(rows, "oref")
    late_abs_error = sum(abs(row["dd_delta"]) for row in late_dlf) / len(late_dlf)
    late_max_error = max(abs(row["dd_delta"]) for row in late_dlf)
    avg_freq = sum(row["freq_khz"] for row in late_hold) / len(late_hold)
    avg_period = sum(row["dt_us"] for row in late_hold) / len(late_hold)

    lines = [
        "# Top Closed-Loop Run Summary",
        "",
        "Generated by `scripts/generate_top_graphs.py` from `top/top_run.csv`.",
        "",
        "DLF values are sampled 20 ns after `CLK_DATASAMPLE` rising edges. CP values are sampled exactly at `DATA_OUT` rising edges because CP buses reset shortly after the hold event.",
        "",
        "| Item | Value |",
        "|------|------:|",
        f"| Samples | {len(rows)} |",
        f"| Time span | {rows[0]['t_us']:.3f} us to {rows[-1]['t_us']:.3f} us |",
        f"| DATA_OUT hold events | {len(hold_events)} |",
        f"| DLF update events | {len(dlf_events)} |",
        f"| DLF settle sample offset | {DLF_SETTLE_NS:.0f} ns |",
        f"| oref min / max | {min(oref_values):.6f} V / {max(oref_values):.6f} V |",
        f"| Last DD2-DD1 | {int(last_dlf['dd_delta'])} code |",
        f"| Last DIFF | {int(last_dlf['diff'])} code |",
        f"| Last D code | {int(last_dlf['d_code'])} |",
        f"| Last oref | {last_dlf['oref']:.6f} V |",
        f"| Last CP2-CP1 at hold | {int(last_hold['cp_delta'])} code |",
        f"| Late 12-update average abs error | {late_abs_error:.2f} code |",
        f"| Late 12-update max abs error | {late_max_error:.0f} code |",
        f"| Late 20-hold average period | {avg_period:.4f} us |",
        f"| Late 20-hold average frequency | {avg_freq:.2f} kHz |",
        "",
        "Key result: the sampled DLF error converges from hundreds of codes to a few codes and ends at zero. The remaining hold-code ripple alternates around zero, which is the expected closed-loop behavior.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    if not CSV_PATH.exists():
        print(f"missing input: {CSV_PATH}", file=sys.stderr)
        return 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows, dlf_events, hold_events = parse_top_csv(CSV_PATH)
    if not rows or not dlf_events or not hold_events:
        print("missing parsed waveform/events", file=sys.stderr)
        return 1

    overview_rows = downsample(rows)
    zoom_rows = downsample(filter_window(rows, 170.0, 180.0), 1800)

    svg_plot(
        OUT_DIR / "top_loop_overview.svg",
        "Top Loop Raw Waveform Overview",
        [
            Panel("RC ramp and oref", "V", [
                make_series(overview_rows, "t_us", "vrc1", "VRC1", 0),
                make_series(overview_rows, "t_us", "vrc2", "VRC2", 1),
                make_series(overview_rows, "t_us", "oref", "oref", 2),
            ]),
            Panel("Comparator-facing oscillator nodes", "V", [
                make_series(overview_rows, "t_us", "osc1", "osc1", 0),
                make_series(overview_rows, "t_us", "osc2", "osc2", 1),
                make_series(overview_rows, "t_us", "osc11", "osc11", 2),
                make_series(overview_rows, "t_us", "osc22", "osc22", 3),
            ]),
            Panel("Loop timing controls", "logic", [
                make_series(overview_rows, "t_us", "data_out", "DATA_OUT", 4),
                make_series(overview_rows, "t_us", "clk_sample", "CLK_DATASAMPLE", 5),
                make_series(overview_rows, "t_us", "clk_osc", "CLK_OSC", 6),
            ], (-0.1, 1.1)),
        ],
        "time (us)",
    )

    svg_plot(
        OUT_DIR / "top_dlf_convergence.svg",
        "Corrected DLF Event Analysis",
        [
            Panel(f"Sampled SAR codes ({DLF_SETTLE_NS:.0f} ns after update edge)", "code", [
                make_series(dlf_events, "event", "dd1", "DD1", 0),
                make_series(dlf_events, "event", "dd2", "DD2", 1),
            ]),
            Panel("Loop error converging to zero", "code", [
                make_series(dlf_events, "event", "dd_delta", "DD2-DD1", 2),
                make_series(dlf_events, "event", "diff", "DIFF = -(DD2-DD1)", 3),
            ]),
            Panel("DLF/CDAC drive", "code", [
                make_series(dlf_events, "event", "d_code", "D<16:0>", 4),
            ]),
            Panel("oref actuator", "V", [
                make_series(dlf_events, "event", "oref", "oref", 5),
            ]),
        ],
        "DLF update index",
    )

    svg_plot(
        OUT_DIR / "top_cp_hold_codes.svg",
        "DATA_OUT Hold Event Analysis",
        [
            Panel("CP code captured at hold edge", "code", [
                make_series(hold_events, "event", "cp1", "CP1", 0),
                make_series(hold_events, "event", "cp2", "CP2", 1),
            ]),
            Panel("Hold-code balance around zero", "code", [
                make_series(hold_events, "event", "cp_delta", "CP2-CP1", 2),
            ]),
            Panel("Held analog state and oref", "V", [
                make_series(hold_events, "event", "vrc1", "VRC1", 0),
                make_series(hold_events, "event", "vrc2", "VRC2", 1),
                make_series(hold_events, "event", "oref", "oref", 2),
            ]),
        ],
        "DATA_OUT hold index",
    )

    svg_plot(
        OUT_DIR / "top_lock_summary.svg",
        "Closed-Loop Lock Summary",
        [
            Panel("DLF sampled error", "code", [
                make_series(dlf_events, "sample_t_us", "dd_delta", "DD2-DD1", 2),
            ]),
            Panel("oref settles while error collapses", "V", [
                make_series(dlf_events, "sample_t_us", "oref", "oref", 5),
            ]),
            Panel("Hold interval", "us", [
                make_series(hold_events[1:], "t_us", "dt_us", "hold interval (us)", 0),
            ]),
            Panel("Equivalent hold frequency", "kHz", [
                make_series(hold_events[1:], "t_us", "freq_khz", "freq (kHz)", 1),
            ]),
        ],
        "time (us)",
    )

    svg_plot(
        OUT_DIR / "top_late_loop_zoom.svg",
        "Late Loop Zoom: 170-180 us",
        [
            Panel("Late RC ramp and oref", "V", [
                make_series(zoom_rows, "t_us", "vrc1", "VRC1", 0),
                make_series(zoom_rows, "t_us", "vrc2", "VRC2", 1),
                make_series(zoom_rows, "t_us", "oref", "oref", 2),
            ]),
            Panel("Oscillator crossing detail", "V", [
                make_series(zoom_rows, "t_us", "osc1", "osc1", 0),
                make_series(zoom_rows, "t_us", "osc2", "osc2", 1),
                make_series(zoom_rows, "t_us", "osc11", "osc11", 2),
                make_series(zoom_rows, "t_us", "osc22", "osc22", 3),
            ]),
            Panel("Hold/update pulses", "logic", [
                make_series(zoom_rows, "t_us", "data_out", "DATA_OUT", 4),
                make_series(zoom_rows, "t_us", "clk_sample", "CLK_DATASAMPLE", 5),
                make_series(zoom_rows, "t_us", "clk_osc", "CLK_OSC", 6),
            ], (-0.1, 1.1)),
        ],
        "time (us)",
    )

    write_event_csv(ROOT / "docs" / "top_event_analysis.csv", dlf_events, hold_events)
    write_markdown_summary(ROOT / "docs" / "top_run_summary.md", rows, dlf_events, hold_events)
    print(f"parsed {len(rows)} rows")
    print(f"hold events: {len(hold_events)} at DATA_OUT rising edges")
    print(f"DLF events: {len(dlf_events)} sampled {DLF_SETTLE_NS:.0f} ns after CLK_DATASAMPLE rising edges")
    print(f"final DLF error: {int(dlf_events[-1]['dd_delta'])} code")
    print(f"wrote SVG plots to {OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
