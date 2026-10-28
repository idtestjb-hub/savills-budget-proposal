## Context

`webapp/static/index.html` renders the adjust table (`renderAdjust`, `groupHead`, `subTable`) inside a box with
`overflow-x:auto`. `refreshRow` finds the cells it updates by counting from the row's end, so a column added before
them does not move them. The user chose on 2026-10-27: ĐVT on the code row, and all four ways to scroll less
(short headers, pinned columns, column toggles, full screen).

## Decisions

1. **ĐVT from the detail rows already sent** (`subs[].unit`): no API change.
2. **Short headers** derived from the labels the API already sends (`measure_labels`): "Duyệt NS 2025 (năm trước, quy
   đổi)" → "Duyệt 2025", "Thực tế 01–09/2025 (9 tháng, quy đổi)" → "Thực tế 01–09/2025", "Dự kiến cả năm 2025 (quy
   đổi)" → "Dự kiến 2025"; the full label goes in `title`. Header cells wrap.
3. **Pinning with `position: sticky`** on the first four cells of code rows and the header; fixed widths (32, 32, 70,
   200 px) give the left offsets. The box scrolls both ways with `max-height` of the window minus the page header, so
   the header sticks inside it and the scrollbar stays on screen. Below 700 px only the first three cells pin (Hạng
   mục scrolls) so a phone keeps room for figures. Group rows pin their first cell; detail sub-tables do not pin.
4. **Toggles** add a class on the table (`hide-m`, `hide-rm`) that hides cells marked `adj-mc` / `adj-rm`; the values
   stay in `adj.items`, so saving is unchanged. The choice is kept in `localStorage`.
5. **Full screen** is a fixed overlay on the section (class `adj-full`), not the browser Fullscreen API (no permission
   prompt, works the same in every browser); Esc closes it.

## Risks / Trade-offs

- [Sticky cells need an opaque background] → each pinned cell takes its row's background (plain, edited, saved, group).
- [Very narrow windows] → only three cells pin below 700 px.
