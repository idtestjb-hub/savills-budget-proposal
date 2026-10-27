## Why

The adjust table of the Budget web (Review page, "Điều chỉnh ngân sách năm mới trước khi giao") is about twice as wide as
its box: measured on the server on 2026-10-27, 1,933 px in a 923 px box at a 1024 px window. The three year N-1
columns alone take 693 px because their long headers do not wrap, and the Remark column 240 px. The PM scrolls sideways
on every code and loses sight of which code a figure belongs to; the horizontal scrollbar sits at the bottom of a
long table. The PM also asked for the unit (ĐVT) on the code row.

## What Changes

- A **ĐVT** column after Hạng mục on each code row: the unit of its detail rows; "nhiều" (with the list on hover) when
  they differ; blank for a code without detail rows.
- **Short headers** that wrap: Duyệt 2025, Thực tế 01–09/2025, Dự kiến 2025 (the full label on hover).
- **Pinned columns**: the selection box, the +/- button, Mã and Hạng mục stay on the left while scrolling sideways;
  the header row stays on top while scrolling down. The table scrolls inside a box of the window's height, so the
  horizontal scrollbar is always on screen.
- **Column toggles**: buttons to hide or show the year N-1 columns and the Remark column, remembered on the PC.
- **Full screen**: a button that opens the adjust table over the whole window (Esc or the button closes it).
- No figure, file, API or saved value changes; only the page.

## Capabilities

### New Capabilities
- `budget-web-adjust-table`: the layout of the web adjust table (columns, pinned columns, toggles, full screen).

### Modified Capabilities
<!-- none -->

## Impact

- Code: `webapp/static/index.html` only.
- Release: budget-web through [Hub].
