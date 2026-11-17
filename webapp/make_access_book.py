"""
Tạo file Excel phân quyền theo dự án mẫu cho Budget web (change budget-web-project-access).

    python webapp/make_access_book.py --out <đường dẫn .xlsx> [--sample]

Không ghi đè file đã có (đổi tên hoặc xoá trước). `--sample` thêm vài dòng TEST DATA với tên và email giả để thử; file
dùng thật thì xoá các dòng đó và điền dự án, người dùng thật.
"""
import argparse
import os
import sys

HEADERS = {
    'Du an': ['Ma', 'Ten', 'Ten khac'],
    'Nguoi dung': ['Email', 'Ma du an'],
}
SAMPLE = {
    'Du an': [['P001', 'Du an thu nghiem A (TEST DATA)', 'Thu nghiem A; TN-A'],
              ['P002', 'Du an thu nghiem B (TEST DATA)', '']],
    'Nguoi dung': [['pm.a@example.com', 'P001'],
                   ['pm.ab@example.com', 'P001; P002'],
                   ['office@example.com', 'ALL']],
}
GUIDE = [
    'Hướng dẫn',
    'Sheet "Du an": mỗi dòng một dự án. Ma = mã ngắn không dấu (ví dụ P012). Ten = tên hiển thị trên web. '
    'Ten khac = các tên khác của dự án trong file ngân sách cũ, cách nhau bằng dấu chấm phẩy.',
    'Sheet "Nguoi dung": mỗi dòng một email. Ma du an = các mã được xem, cách nhau bằng dấu chấm phẩy; ALL = xem tất '
    'cả như văn phòng.',
    'Email không có trong sheet thì không xem được gì. Lưu file là có hiệu lực sau vài phút.',
]


def build(out, sample=False):
    import openpyxl
    from openpyxl.styles import Font
    if os.path.exists(out):
        raise FileExistsError(f'{out} đã có; không ghi đè.')
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for name, header in HEADERS.items():
        ws = wb.create_sheet(name)
        ws.append(header)
        for c in ws[1]:
            c.font = Font(bold=True)
        for row in (SAMPLE[name] if sample else []):
            ws.append(row)
        ws.freeze_panes = 'A2'
        for col, width in zip('ABC', (34, 44, 50)):
            ws.column_dimensions[col].width = width
    ws = wb.create_sheet('Huong dan')
    for line in GUIDE:
        ws.append([line])
    ws['A1'].font = Font(bold=True)
    ws.column_dimensions['A'].width = 120
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    wb.save(out)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--sample', action='store_true')
    args = ap.parse_args()
    print(build(args.out, args.sample))


if __name__ == '__main__':
    sys.exit(main())
