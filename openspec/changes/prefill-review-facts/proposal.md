## Why

On the Review tab a PM picks an approved budget from the library and then types section 2, "Dữ kiện file ngân sách
không có" (city, district, towers, floors, gates, pool, parking), by hand every time, although the tool already holds
most of these facts: the PM's own earlier run of the same project, the file's `0. Info` sheet and the master list
`Dim_Property_Residential.csv`. The user asked (2026-10-28) to fill section 2 automatically when a file is picked.

## What Changes

- New `GET /api/library/{id}/facts`: for the picked library entry, the facts of section 2 with, per field, the value
  chosen, its source, and the other sources' values when they differ.
  - Sources by priority: (1) the latest earlier run (review or new) of the same project, from its input form;
    (2) the file's `0. Info` sheet (car and motorbike bays); (3) the master list.
  - Same project = the same name after folding: accents removed, đ → d, lower case, every character that is not a
    letter or a digit dropped ("HOANG ANH RIVER VIEW" = "Hoang Anh Riverview"). No near matches.
  - A master name that folds to two or more rows is not used ("master có N dòng trùng tên").
  - A zero or blank is "no value" in every source (the form writes a blank as 0).
  - Master columns: City_Province, District, FloorCount (only when TowerCount is 1: the master gives the floors of
    one tower, the form wants all towers), GateCount, CarParkingSlots, BikeParkingSlots, PoolCount (> 0 →
    "Có").
- The Review tab fills section 2 from it when a library row is picked; each field shows its source, and a line
  "khác: <nguồn> <số>" when another source disagrees. A master city that is not a province on the list is not used.
- The PM's figure still wins: the page sends what the fields hold, and those facts overwrite the Info values
  (`review_import.write_form`), as today.

User's choices on 2026-10-28: all three sources, priority earlier run > Info > master; exact match after folding; a
master zero is "no value"; master floors only for a one-tower project. 2026-10-29, after the server reruns (ONE VERANDAH: master 22 towers): the
master's tower count is never filled, only shown as a note.

## Capabilities

### New Capabilities
- `budget-web-review-facts`: section 2 of the Review tab is filled from the earlier run, the Info sheet and the master
  list, with the source of each value.

### Modified Capabilities

## Impact

- New `webapp/facts_prefill.py`; `webapp/server.py` (route); `webapp/static/index.html` (fill on pick, source labels);
  tests `tests/test_facts_prefill.py`.
- No change to the run, the form written or any figure; the server reads the master list and the picked file read-only.
