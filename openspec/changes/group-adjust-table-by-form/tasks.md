## 1. Build

- [x] 1.1 `adjust.add_groups()` (chain of form groups and template row per item; off-form group); GET adjust calls it. Unit tests on a fake template map and the real template.
- [x] 1.2 Table: sort by fund and template row, nested "Cộng" rows with sums, ▾/▸ fold, "Mở mọi nhóm" / "Thu gọn mọi nhóm", group rows refreshed on edit; Vietnamese part of the group name, full name as title. Checked on the local web 28/10 (copy of a MASTERI Review run): Cộng EM = sum of EMH/EMA/EMB, Chi = sum of the top groups, folding EM hides 7 rows, 10% on ESS1 moves Cộng ESS by 1,316.7M; nothing saved.

## 2. Sign-off

- [x] 2.1 Web tests and full suite pass; `openspec validate --all --strict`; `python verification/verify.py` PASS. Done 2026-10-28: 1281 passed + 1 xfailed, openspec 47/47, verify.py PASS.
- [ ] 2.2 Release note for [Hub]; `docs/project-status.md` updated.
