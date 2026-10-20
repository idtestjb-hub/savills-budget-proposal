"""
Lưu điều chỉnh của trang web vào bản giao của một lượt, rồi cho Excel tính lại để đo thu / chi / thặng dư mới.

    python webapp/adjust_run.py --deliverable <bản giao> --edits <edits.json> --workdir <thư mục lượt>
                                [--baseline-recalc <bản giao đã tính lại trước đó>]

Người dùng chọn 20/10/2026: GHI ĐÈ bản giao, giữ bản backup có ngày bên cạnh
('<tên>_BACKUP_<yyyymmdd-hhmmss>.xlsx', không khớp mẫu tên bản giao nên không bị nhận nhầm là kết quả).

Các bước:
1. Bản giao đang mở trong Excel (có file khoá '~$<tên>') thì dừng, không ghi.
2. Số trước điều chỉnh (chỉ lần lưu đầu): tổng R / E của hai sheet quỹ trên bản giao gốc, đo bằng Excel
   (review.tool_lines). Lượt review có sẵn deliverable_recalc.xlsx của bản gốc thì dùng lại. Lưu vào adjust_state.json.
3. Backup, ghi các ô nhập của sheet '4. Điều chỉnh' (webapp.adjust.apply_edits), lưu đè bản giao.
4. Excel tính lại một bản sao (adjust_recalc.xlsx): tổng R / E / thặng dư mỗi quỹ, thành tiền mới từng mã đã chỉnh,
   ô lỗi (#REF!, #DIV/0!, #VALUE!...) trên sheet 4, hai sheet quỹ và 1. Summary.
5. Ghi adjust_result.json (đọc bởi trang web) và nối vào lịch sử lưu trong adjust_state.json.

Mã thoát: 0 = xong, 2 = dừng có thông báo ("STOPPED: ...").
"""
import argparse
import datetime
import json
import os
import shutil
import sys

SOURCE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SOURCE_DIR not in sys.path:
    sys.path.insert(0, SOURCE_DIR)

STATE_FILE = 'adjust_state.json'
RESULT_FILE = 'adjust_result.json'
RECALC_FILE = 'adjust_recalc.xlsx'
BASELINE_FILE = 'adjust_baseline_recalc.xlsx'
ERROR_TEXTS = ('#REF!', '#DIV/0!', '#VALUE!', '#NAME?', '#N/A', '#NUM!', '#NULL!')
CHECK_SHEETS = ('4. Điều chỉnh', '2. Budget-Management Fund', '2.2 Common area Fund', '1. Summary')


def _totals(tool):
    out = {}
    for fund, v in tool.items():
        r, e = v['totals'].get('R'), v['totals'].get('E')
        out[fund] = dict(R=r, E=e, S=(r - e) if r is not None and e is not None else None)
    return out


def _errors(recalc_path):
    import openpyxl
    wb = openpyxl.load_workbook(recalc_path, read_only=True, data_only=True)
    found = []
    try:
        for name in CHECK_SHEETS:
            if name not in wb.sheetnames:
                continue
            for row in wb[name].iter_rows():
                for c in row:
                    if isinstance(c.value, str) and c.value.strip() in ERROR_TEXTS:
                        found.append(f'{name}!{c.coordinate} {c.value.strip()}')
    finally:
        wb.close()
    return found


def _new_amounts(recalc_path, keys):
    """{key: thành tiền mới (cột M) của dòng Tổng} đo bằng Excel, cho các mã trong `keys`."""
    import openpyxl
    from webapp import adjust
    wb = openpyxl.load_workbook(recalc_path, data_only=True)
    out = {}
    try:
        ws = wb[adjust.SHEET]
        for prow, _ in adjust._scan(ws):
            code = adjust._text(ws.cell(row=prow, column=adjust.C['code']).value)
            fund_sheet = adjust._text(ws.cell(row=prow, column=adjust.C['fund_sheet']).value)
            key = adjust.key_of(code, fund_sheet)
            if key in keys:
                out[key] = dict(amount=adjust._num(ws.cell(row=prow, column=adjust.C['amount']).value),
                                new_amount=adjust._num(ws.cell(row=prow, column=adjust.C['new_amount']).value))
    finally:
        wb.close()
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--deliverable', required=True)
    ap.add_argument('--edits', required=True)
    ap.add_argument('--workdir', required=True)
    ap.add_argument('--baseline-recalc', default=None)
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)
    sys.stderr.reconfigure(encoding='utf-8', line_buffering=True)
    os.chdir(SOURCE_DIR)

    import openpyxl
    import review
    from webapp import adjust

    deliverable = os.path.abspath(args.deliverable)
    workdir = os.path.abspath(args.workdir)
    folder, name = os.path.split(deliverable)
    state_path = os.path.join(workdir, STATE_FILE)
    state = json.load(open(state_path, encoding='utf-8')) if os.path.exists(state_path) else {}
    with open(args.edits, encoding='utf-8') as fh:
        edits = json.load(fh)
    if os.path.exists(os.path.join(workdir, RESULT_FILE)):
        os.remove(os.path.join(workdir, RESULT_FILE))      # kết quả cũ không được hiện như của lần này
    try:
        if os.path.exists(os.path.join(folder, '~$' + name)):
            raise adjust.AdjustError(f"Bản giao '{name}' đang mở trong Excel trên máy chủ. Đóng file rồi lưu lại.")
        print(f'[1/3] Kiểm tra {len(edits)} mã điều chỉnh')
        wb = openpyxl.load_workbook(deliverable)
        written = adjust.apply_edits(wb, edits)       # kiểm tra hết trước khi ghi bất cứ gì xuống đĩa

        if not state.get('baseline'):
            base = args.baseline_recalc if args.baseline_recalc and os.path.exists(args.baseline_recalc) else None
            if base is None:
                print('    Excel đo số trước điều chỉnh (lần lưu đầu)')
                base = os.path.join(workdir, BASELINE_FILE)
                review.recalc_copy(deliverable, base)
            state['baseline'] = _totals(review.tool_lines(deliverable, base))
            state['baseline_source'] = os.path.basename(base)

        stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
        stem, ext = os.path.splitext(name)
        backup = os.path.join(folder, f'{stem}_BACKUP_{stamp}{ext}')
        shutil.copy2(deliverable, backup)
        print(f'[2/3] Backup: {os.path.basename(backup)}; ghi {len(written)} mã vào bản giao')
        wb.save(deliverable)
        wb.close()

        print('[3/3] Excel tính lại bản giao đã điều chỉnh')
        recalc = os.path.join(workdir, RECALC_FILE)
        review.recalc_copy(deliverable, recalc)
        after = _totals(review.tool_lines(deliverable, recalc))
        keys = {adjust._text(e.get('key')) for e in edits}
        measured = _new_amounts(recalc, keys)
        errors = _errors(recalc)
    except (adjust.AdjustError, review.ReviewError, OSError) as exc:
        print(f'STOPPED: {exc}')
        return 2

    result = dict(saved_at=datetime.datetime.now().isoformat(timespec='seconds'), deliverable=name,
                  backup=os.path.basename(backup), written=written, baseline=state['baseline'], after=after,
                  items={k: v for k, v in measured.items()}, errors=errors[:50], error_count=len(errors))
    state.setdefault('saves', []).append(dict(saved_at=result['saved_at'], backup=result['backup'],
                                              written=written, after=after))
    with open(state_path, 'w', encoding='utf-8') as fh:
        json.dump(state, fh, ensure_ascii=False, indent=1)
    with open(os.path.join(workdir, RESULT_FILE), 'w', encoding='utf-8') as fh:
        json.dump(result, fh, ensure_ascii=False, indent=1)
    for fund, t in after.items():
        b = state['baseline'].get(fund, {})
        print(f"    {adjust.FUND_VI.get(fund, fund)}: thu {b.get('R') or 0:,.0f} → {t['R'] or 0:,.0f}; "
              f"chi {b.get('E') or 0:,.0f} → {t['E'] or 0:,.0f}")
    print(f'    ô lỗi sau tính lại: {len(errors)}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
