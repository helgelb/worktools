#!/usr/bin/env python3
"""allocate_hours.py

Allocate per-day working hours across percentage categories using either a
sequential drift-corrected algorithm or an "optimal" discrete quota
allocation. Output is rounded to a configurable resolution (default 0.5h,
supports down to 0.01h for precise tracking).

Core idea:
  1. You supply total hours for each day (default days auto-assigned Mon..).
  2. You supply percentage splits (they may sum to <= 1.0; remainder stays
     unallocated unless you enable filling or strict mode).
  3. The tool allocates hours per category without exceeding day totals.

Arguments (CLI):
  --hours / -hr <list float>
      Required. Total hours per listed (or inferred) day. Order matters.
      Example: --hours 0 2 7.5 7.5 7.5

  --days / -d <list str>
      Optional explicit day names matching hours. Accepts full names or
      abbreviations (mon,tue,wed,thu/thur,fri,sat,sun). If omitted, days are
      assigned Monday onward.
      Example: --days mon tue wed thu fri

  --percent / -p <list float>
      Percentage category splits. Must sum <= 1.0 unless --normalize is used.
      Example: --percent 0.5 0.3 0.1   (10% remainder unallocated)

    --algorithm / -a {optimal,sequential}
      Allocation strategy.
        optimal    : Uses a largest-remainder (Hamilton) style approach in half-hour
                     units, then greedy fill per day (generally tighter to targets).
        sequential : Original algorithm allocating categories one after another
                     with drift correction on last day.
      Example: -a sequential

    --resolution / -r <float>
            Rounding granularity in hours. Must divide 1.0 evenly (e.g. 1, 0.5, 0.25, 0.2).
            Default: 0.5
            Example: --resolution 0.25 (rounds to quarter hours)

  --normalize
      Scales provided percentages so they sum exactly to 1.0 (if sum > 0). Use
      this when you want all hours distributed with no remainder.
      Example: --percent 0.5 0.3 0.3 --normalize (percentages become 0.4545,0.2727,0.2727)

  --fill-remainder
      Attempts to allocate the leftover remainder hours (if percentages < 1.0)
      into the LAST category, respecting day capacity in 0.5 hour increments.
      Example: --percent 0.5 0.3 0.1 --fill-remainder

  --strict
      Requires that no remainder hours remain. Tries to fill remainder (even if
      --fill-remainder not specified). Errors if impossible.
      Example: --percent 0.5 0.3 0.1 --strict

  --show-remainder
      Adds a "Remainder" row showing unallocated hours (if any).
      Example: --show-remainder

  --show-actual-percent
      Adds an "Actual %" row showing the achieved percentage (per category) computed
      from allocated hours vs the total allocated hours. Values are presented as
      percentages (0-100%) formatted to match the chosen resolution's decimal places.
      Example: --sum --show-actual-percent

  --sum / -s
      Adds a "Sum" row plus a Delta row showing difference between target and
      actual allocated category totals (allocated - target).
      Example: --sum

  --csv <path>
      Export the table to CSV. Does not include the Delta row details as extra columns.
      Example: --csv allocation.csv

  --json <path>
      Export structured allocation data (days, percentages, targets, remainder).
      Example: --json allocation.json

Behavior notes:
    * Rounding to the chosen resolution can cause small drift; Delta row surfaces this.
  * If percentages sum < 1.0 you will see remainder unless you fill or normalize.
  * Strict mode may fail when no day has enough slack to absorb remainder.
  * Optimal algorithm typically yields category totals closer to theoretical targets.

Comprehensive Examples:
  1) Basic default splits:
     python allocate_hours.py --hours 0 2 7.5 7.5 7.5

  2) Explicit days + custom percentages + sum row:
     python allocate_hours.py --days mon tue wed thu fri --hours 0 2 7.5 7.5 7.5 --percent 0.6 0.4 --sum

  3) Use optimal algorithm with remainder display (custom resolution):
     python allocate_hours.py --hours 0 2 7.5 7.5 7.5 --percent 0.5 0.3 0.1 --show-remainder -a optimal --resolution 0.25

  4) High-precision tracking (0.01 hour = ~36 seconds):
     python allocate_hours.py --hours 8.5 --percent 0.6 0.4 --resolution 0.01

  5) Force full allocation by normalization:
     python allocate_hours.py --hours 0 2 7.5 7.5 7.5 --percent 0.5 0.3 0.2 --normalize --sum

  6) Attempt to fill remainder into last category:
     python allocate_hours.py --hours 0 2 7.5 7.5 7.5 --percent 0.5 0.3 0.1 --fill-remainder --show-remainder

  7) Enforce zero remainder (strict mode):
     python allocate_hours.py --hours 0 2 7.5 7.5 7.5 --percent 0.5 0.3 0.1 --strict --sum

  7) Export results:
     python allocate_hours.py --hours 0 2 7.5 7.5 7.5 --percent 0.5 0.3 0.1 --csv alloc.csv --json alloc.json --sum --show-remainder

  8) Sequential algorithm for comparison:
     python allocate_hours.py --hours 0 2 7.5 7.5 7.5 --percent 0.5 0.3 0.1 -a sequential --sum

  9) Mixed options (normalize + strict to guarantee full distribution):
     python allocate_hours.py --hours 0 2 7.5 7.5 7.5 --percent 0.45 0.35 0.2 --normalize --strict --sum

Edge Cases:
  * All zero hours: allowed; all category allocations zero.
  * Single day input: behaves the same; categories allocated within that day.
  * Percentages sum > 1 without --normalize: raises ValueError.
  * Duplicate or unknown day names: raises ValueError.

CLI Summary (quick reference):
    --hours / -hr <floats>        Total hours per day (required)
    --days / -d <names>           Optional explicit day names matching hours
    --percent / -p <floats>       Category percentages (<=1 unless --normalize)
    --algorithm / -a opt|seq      Allocation strategy (optimal|sequential)
    --resolution / -r <float>     Rounding resolution (default 0.5, supports 0.01+)
    --normalize                   Scale percentages to sum to 1.0
    --fill-remainder              Fill leftover hours into last category
    --strict                      Enforce zero remainder (error if cannot fill)
    --show-remainder              Display remainder row
    --sum / -s                    Show Sum and Delta rows
    --csv <path>                  Export table to CSV
    --json <path>                 Export structured data to JSON
    --show-actual-percent         Show Actual % row (achieved percentages per category)
    -h / --help                   Show built-in argparse help
"""

import argparse
import json
from typing import Any


def round_to_resolution(x: float, resolution: float) -> float:
    """Round a number to the nearest multiple of resolution."""
    if resolution <= 0:
        raise ValueError("Resolution must be positive")
    units = round(x / resolution)
    return units * resolution


def get_decimal_places(resolution: float) -> int:
    """Get the number of decimal places needed to display the resolution precisely."""
    resolution_str = f"{resolution:.10f}".rstrip("0").rstrip(".")
    if "." in resolution_str:
        return len(resolution_str.split(".")[1])
    return 0


def compute_actual_percentages(allocations: dict[str, list[float]]) -> list[float]:
    """Return actual achieved percentages for each category (excluding Total).

    allocations: mapping day -> [total, cat1, cat2, ...]
    returns list of floats in [0,1] for each category (cat1..)
    """
    if not allocations:
        return []
    cols = len(next(iter(allocations.values())))
    sums = [sum(v[i] for v in allocations.values()) for i in range(cols)]
    total = sums[0]
    if total == 0:
        return [0.0 for _ in range(cols - 1)]
    return [s / total for s in sums[1:]]


def _render_table(
    allocations: dict[str, list[float]],
    percentages: list[float],
    include_sum: bool,
    remainder: float,
    show_remainder: bool,
    targets: list[float],
    resolution: float,
    show_actual_percent: bool = False,
):
    decimal_places = get_decimal_places(resolution)
    headers = ["Day", "Input"] + [f"{int(p * 100)} %" for p in percentages]
    if include_sum:
        headers.append("Sum")
    rows = []
    for day, vals in allocations.items():
        row = [day, f"{vals[0]:.{decimal_places}f}"] + [
            f"{v:.{decimal_places}f}" for v in vals[1:]
        ]
        if include_sum:
            cat_sum = sum(vals[1:])
            row.append(f"{cat_sum:.{decimal_places}f}")
        rows.append(row)
    if include_sum:
        cols = len(next(iter(allocations.values())))
        sums = [sum(v[i] for v in allocations.values()) for i in range(cols)]
        sum_row = ["Sum", f"{sums[0]:.{decimal_places}f}"] + [
            f"{s:.{decimal_places}f}" for s in sums[1:]
        ]
        if include_sum:
            per_day_cat_sum = sum(sums[1:])
            sum_row.append(f"{per_day_cat_sum:.{decimal_places}f}")
        rows.append(sum_row)
        if show_actual_percent:
            actuals = compute_actual_percentages(allocations)
            actual_row = (
                ["Actual %"]
                + [""]
                + [f"{a * 100:.{decimal_places}f}%" for a in actuals]
            )
            if include_sum:
                actual_row.append("")
            rows.append(actual_row)
        if len(targets) == cols - 1:
            diffs = [sums[i + 1] - targets[i] for i in range(cols - 1)]
            delta_row = ["Delta"] + ["-"] + [f"{d:+.{decimal_places}f}" for d in diffs]
            if include_sum:
                delta_row.append("")
            rows.append(delta_row)
    if show_remainder and remainder > 0.0001:
        rem_row = ["Remainder", f"{remainder:.{decimal_places}f}"] + [
            "" for _ in percentages
        ]
        if include_sum:
            rem_row.append("")
        rows.append(rem_row)
    col_widths = [
        max(len(str(cell)) for cell in col) + 2
        for col in zip(headers, *rows, strict=True)
    ]

    def fmt(r):
        out = []
        for i, c in enumerate(r):
            out.append(f"{c:<{col_widths[i]}}" if i == 0 else f"{c:>{col_widths[i]}}")
        return "".join(out)

    print(fmt(headers))
    print("-" * sum(col_widths))
    for r in rows:
        print(fmt(r))


def allocate_sequential(
    days: dict[str, float], percentages: list[float], resolution: float
) -> tuple[dict[str, list[float]], list[float], float]:
    total = sum(days.values())
    quotas = [p * total for p in percentages]
    remaining = quotas.copy()
    n = len(percentages)
    out = {d: [h] + [0] * n for d, h in days.items()}
    for i in range(n):
        for d, h in days.items():
            available = h - sum(out[d][1:])
            alloc = min(available, max(0, remaining[i]))
            alloc = round_to_resolution(alloc, resolution)
            remaining[i] -= alloc
            out[d][i + 1] = alloc
        used = sum(v[i + 1] for v in out.values())
        drift = round_to_resolution(quotas[i] - used, resolution)
        last_day = list(out.keys())[-1]
        out[last_day][i + 1] = round_to_resolution(
            out[last_day][i + 1] + drift, resolution
        )
    adjust_per_day_residuals(out, days, resolution, n)
    allocated_sum = sum(sum(v[1:]) for v in out.values())
    remainder = max(0.0, round_to_resolution(total - allocated_sum, resolution))
    return out, quotas, remainder


def adjust_per_day_residuals(
    allocations: dict[str, list[float]],
    days: dict[str, float],
    resolution: float,
    n_categories: int,
) -> None:
    """Adjust per-day residuals by applying any rounding differences to the last category.

    After distributing across categories, ensure each day's category allocations
    sum to the day's total by applying any per-day residual (due to rounding)
    to the last category for that day (if possible). This preserves per-day totals
    and keeps adjustments within resolution granularity.

    Args:
        allocations: Dictionary mapping day -> [total, cat1, cat2, ...]
        days: Dictionary mapping day -> total hours
        resolution: Rounding resolution in hours
        n_categories: Number of categories
    """
    for d, h in days.items():
        cat_sum = sum(allocations[d][1:])
        residual = round_to_resolution(h - cat_sum, resolution)
        if abs(residual) >= resolution - 1e-9:
            last_idx = n_categories
            allocations[d][last_idx] = round_to_resolution(
                allocations[d][last_idx] + residual, resolution
            )
        else:
            # For tiny floating differences smaller than resolution, snap to zero
            pass  # (no change needed)


def allocate_optimal(
    days: dict[str, float], percentages: list[float], resolution: float
) -> tuple[dict[str, list[float]], list[float], float]:
    factor = int(round(1 / resolution))
    if abs(factor * resolution - 1.0) > 1e-9:
        raise ValueError("Resolution must evenly divide 1.0 (e.g. 1, 0.5, 0.25, 0.2)")
    units_per_day = {d: int(round(h * factor)) for d, h in days.items()}
    total_units = sum(units_per_day.values())
    raw_targets = [p * total_units for p in percentages]
    floors = [int(t) for t in raw_targets]
    remainders = [(i, raw_targets[i] - floors[i]) for i in range(len(percentages))]
    assigned = sum(floors)
    target_sum = sum(raw_targets)
    free_for_targets = min(total_units - assigned, int(round(target_sum - assigned)))
    target_units = floors[:]
    for i, _r in sorted(remainders, key=lambda x: x[1], reverse=True):
        if free_for_targets <= 0:
            break
        target_units[i] += 1
        free_for_targets -= 1
    alloc_units = {d: [units_per_day[d]] + [0] * len(percentages) for d in days.keys()}
    remaining_units = target_units[:]
    for day in days.keys():
        cap = units_per_day[day]
        used = 0
        while used < cap and sum(remaining_units) > 0:
            idx = max(
                (i for i, v in enumerate(remaining_units) if v > 0),
                key=lambda i: remaining_units[i],
                default=None,
            )
            if idx is None:
                break
            alloc_units[day][idx + 1] += 1
            remaining_units[idx] -= 1
            used += 1
    allocations = {
        d: [vals[0] / factor] + [v / factor for v in vals[1:]]
        for d, vals in alloc_units.items()
    }
    target_hours = [u / factor for u in target_units]
    remainder_units = total_units - sum(target_units)
    remainder_hours = remainder_units / factor
    # Sanity check
    for d, vals in allocations.items():
        if sum(vals[1:]) - vals[0] > 1e-6:
            raise RuntimeError(f"Allocation exceeded day total for {d}")
    return allocations, target_hours, remainder_hours


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Allocate weekly hours between multiple percentage categories sequentially."
    )
    parser.add_argument(
        "--hours",
        "-hr",
        nargs="+",
        type=float,
        required=True,
        help="List of total hours per weekday, e.g. --hours 0 2 7.5 7.5 7.5",
    )
    parser.add_argument(
        "--days",
        "-d",
        nargs="+",
        help="Optional list of day names matching the hours (e.g. --days monday tuesday ...)",
    )
    parser.add_argument(
        "--percent",
        "-p",
        nargs="+",
        type=float,
        dest="percentages",
        default=[0.75, 0.25],
        help="Percentage splits (must sum to 1.0 or less). Example: --p 0.75 0.25 or --p 0.5 0.3 0.2",
    )
    parser.add_argument(
        "--sum",
        "-s",
        action="store_true",
        help="Include sum row in output",
    )
    parser.add_argument(
        "--algorithm",
        "-a",
        choices=["optimal", "sequential"],
        default="optimal",
        help="Allocation strategy: optimal (discrete half-hour) or sequential (original drift-corrected).",
    )
    parser.add_argument(
        "--normalize",
        action="store_true",
        help="Scale input percentages so they sum to 1.0 (if their sum > 0).",
    )
    parser.add_argument(
        "--resolution",
        "-r",
        type=float,
        default=0.5,
        help="Rounding resolution in hours (e.g. 1, 0.5, 0.25, 0.1, 0.01). Default 0.5",
    )
    parser.add_argument(
        "--fill-remainder",
        action="store_true",
        help="Attempt to allocate remainder hours (if any) into the last category without exceeding day totals.",
    )
    parser.add_argument(
        "--show-remainder",
        action="store_true",
        help="Show unallocated remainder row.",
    )
    parser.add_argument(
        "--csv",
        metavar="PATH",
        help="Export allocation table (excluding Delta) to CSV file at PATH.",
    )
    parser.add_argument(
        "--json",
        metavar="PATH",
        help="Export detailed allocation (per day, totals, targets, remainder) to JSON file at PATH.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Require zero remainder; attempt to fill and error if impossible.",
    )
    parser.add_argument(
        "--show-actual-percent",
        action="store_true",
        help="Show actual achieved percentages per category in the table.",
    )

    args = parser.parse_args()

    percentages = args.percentages if args.percentages else [1.0]
    if args.normalize and sum(percentages) > 0:
        total_p = sum(percentages)
        percentages = [p / total_p for p in percentages]
    if args.days and len(args.days) != len(args.hours):
        raise ValueError("Number of days must match number of hours")
    if sum(percentages) > 1.0 and not args.normalize:
        raise ValueError("Percentages must sum to 1.0 or less (or use --normalize)")
    abbrev_map = {
        "mon": "monday",
        "tue": "tuesday",
        "wed": "wednesday",
        "thu": "thursday",
        "thur": "thursday",
        "fri": "friday",
        "sat": "saturday",
        "sun": "sunday",
    }
    valid_days = {
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
    }

    def canon_days(days_list):
        seen = set()
        out = []
        for d in days_list:
            key = abbrev_map.get(d.lower(), d.lower())
            if key not in valid_days:
                raise ValueError(f"Unknown day name: {d}")
            if key in seen:
                raise ValueError(f"Duplicate day: {key}")
            seen.add(key)
            out.append(key)
        return out

    if args.days:
        canonical = canon_days(args.days)
        if len(canonical) != len(args.hours):
            raise ValueError(
                "Number of days must match number of hours after canonicalization"
            )
        day_dict = dict(zip(canonical, args.hours, strict=True))
    else:
        all_days = [
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
        ]
        day_dict = dict(zip(all_days[: len(args.hours)], args.hours, strict=True))

    resolution = args.resolution
    if resolution <= 0:
        raise ValueError("Resolution must be positive")
    if abs(round(1 / resolution) * resolution - 1.0) > 1e-9:
        raise ValueError("Resolution must evenly divide 1.0 (e.g. 1, 0.5, 0.25, 0.2)")

    if args.algorithm == "sequential":
        allocations, targets, remainder = allocate_sequential(
            day_dict, percentages, resolution
        )
    else:
        allocations, targets, remainder = allocate_optimal(
            day_dict, percentages, resolution
        )

    if args.fill_remainder and remainder > 0.0001:
        last_idx = len(percentages)
        remaining_to_fill = remainder
        while remaining_to_fill + 1e-9 >= resolution:
            progress = False
            for _d, vals in allocations.items():
                day_total = vals[0]
                used = sum(vals[1:])
                slack = day_total - used
                if slack + 1e-9 >= resolution:
                    vals[last_idx] += resolution
                    remaining_to_fill -= resolution
                    progress = True
                    if remaining_to_fill < resolution:
                        break
            if not progress:
                break
        remainder = remaining_to_fill
        targets[-1] += remainder - remaining_to_fill

    if args.strict and remainder > 0.0001:
        last_idx = len(percentages)
        remaining_to_fill = remainder
        while remaining_to_fill + 1e-9 >= resolution:
            progress = False
            for _d, vals in allocations.items():
                day_total = vals[0]
                used = sum(vals[1:])
                slack = day_total - used
                if slack + 1e-9 >= resolution:
                    vals[last_idx] += resolution
                    remaining_to_fill -= resolution
                    progress = True
                    if remaining_to_fill < resolution:
                        break
            if not progress:
                break
        remainder = remaining_to_fill
        if remainder > 0.0001:
            raise ValueError(
                f"Strict mode: unable to allocate remainder ({remainder:.2f}h)"
            )

    _render_table(
        allocations,
        percentages,
        bool(args.sum),
        remainder,
        args.show_remainder,
        targets,
        resolution,
        show_actual_percent=bool(args.show_actual_percent),
    )

    if args.csv:
        try:
            import csv

            with open(args.csv, "w", newline="") as f:
                writer = csv.writer(f)
                header = ["Day", "Total"] + [f"{int(p * 100)} %" for p in percentages]
                writer.writerow(header)
                for d, vals in allocations.items():
                    writer.writerow(
                        [d] + [f"{vals[0]:.2f}"] + [f"{v:.2f}" for v in vals[1:]]
                    )
                if args.sum:
                    sample_cols = (
                        len(next(iter(allocations.values()))) if allocations else 1
                    )
                    sums = [
                        sum(v[i] for v in allocations.values())
                        for i in range(sample_cols)
                    ]
                    writer.writerow(["Sum"] + [f"{s:.2f}" for s in sums])
                if args.show_remainder and remainder > 0.0001:
                    writer.writerow(
                        ["Remainder", f"{remainder:.2f}"] + ["" for _ in percentages]
                    )
        except Exception as e:
            print(f"CSV export failed: {e}")

    if args.json:
        try:
            payload: dict[str, Any] = {
                "days": list(day_dict.keys()),
                "percentages": percentages,
                "allocations": {
                    d: {"total": vals[0], "categories": vals[1:]}
                    for d, vals in allocations.items()
                },
                "targets": targets,
                "allocated_category_totals": [
                    sum(allocations[d][i + 1] for d in allocations.keys())
                    for i in range(len(percentages))
                ],
                "remainder_hours": remainder,
                "normalized": args.normalize,
                "algorithm": args.algorithm,
            }
            with open(args.json, "w") as f:
                json.dump(payload, f, indent=2)
        except Exception as e:
            print(f"JSON export failed: {e}")
