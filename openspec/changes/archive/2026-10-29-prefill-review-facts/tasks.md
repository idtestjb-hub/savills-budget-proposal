## 1. Server

- [x] 1.1 `webapp/facts_prefill.py`: name folding, master lookup (unique match, zero = none, floors only for one tower,
      pool from PoolCount), earlier-run facts from the run's input form, Info bays, merge by priority with the other
      sources' differing values
- [x] 1.2 `GET /api/library/{id}/facts` in `webapp/server.py`; the workbook is opened read-only and closed
- [x] 1.3 Tests `tests/test_facts_prefill.py` (folding, duplicate master names, priority, zero, floors, pool)

## 2. Page

- [x] 2.1 Fill section 2 when a library row is picked; a source label per field and a "khác:" line when sources differ;
      a master city not on the province list is not used
- [x] 2.2 Check in the browser on the local web (pick HAGV, Masteri An Phú, a project without master row). Done 2026-10-28 on port 8095 with the client store:
      Masteri fills 7 fields (earlier run > Info > master, "khác:" lines), floors left with the per-tower note, a typed
      value shows "Đã sửa tay"; a project with no master row fills nothing; 35 of 53 selectable rows match the master

## 3. Verify and ship

- [x] 3.1 Full tests + `verification/verify.py` PASS. Done 2026-10-28: 7 prefill tests + full suite 1288 passed + 1 xfailed; verify.py PASS
- [x] 3.2 Release note for [Hub]. Done 2026-10-29: deployed with 57fa053 (8b9a6a1f3e2c); server route checked by [Hub], three Reviews run from it

## 4. Master tower count not filled (user's choice 2026-10-29)

- [x] 4.1 `master_facts` leaves TowerCount out and adds a note "master ghi N tháp; số tháp để PM kiểm và nhập"; the page
      appends a note after a filled field's source instead of replacing it; tests updated
- [x] 4.2 Full tests + verify.py PASS; release note for [Hub]. Done 2026-10-29: 1295 passed + 1 xfailed, verify.py PASS;
      note `releases\2026-10-29-budget-web-bo-so-thap-master.txt` (3cc71cd)
