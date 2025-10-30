# Hours Allocation Tool

Split your daily working hours across different categories (projects, tasks, etc.) based on percentages.

## What it does

Give it:

- Your daily hours (e.g., 0, 2, 7.5, 7.5, 7.5 for Mon-Fri)
- Percentage splits in decimals (e.g., 60% project A, 40% project B)

Get back:

- A table showing how many hours to spend on each category each day

## Basic Usage

```bash
python allocate_hours.py --hours 0 2 7.5 7.5 7.5 --percent 0.6 0.4
```

This splits your week: 60% to first category, 40% to second category.

## Common Options

```bash
# Show totals and differences
python allocate_hours.py --hours 0 2 7.5 7.5 7.5 --percent 0.6 0.4 --sum

# Save to file
python allocate_hours.py --hours 0 2 7.5 7.5 7.5 --percent 0.6 0.4 --csv output.csv

# Use quarter-hour blocks instead of half-hours
python allocate_hours.py --hours 0 2 7.5 7.5 7.5 --percent 0.6 0.4 --resolution 0.25

# Make percentages add to 100% automatically
python allocate_hours.py --hours 0 2 7.5 7.5 7.5 --percent 0.5 0.3 0.1 --normalize
```

## Example Output

```text
Day       Total  60 %  40 %
-------------------------
monday    0.0    0.0   0.0
tuesday   2.0    1.0   1.0
wednesday 7.5    4.5   3.0
thursday  7.5    4.5   3.0
friday    7.5    4.5   3.0
```

## Need Help?

```bash
python allocate_hours.py --help
```
