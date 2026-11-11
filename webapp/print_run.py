"""
Xuất PDF sheet '2. Budget-Management Fund' của một bản giao (change add-budget-print-layout).

    python webapp/print_run.py --deliverable <bản giao> --paper A4|A3 --out <file pdf>

Excel làm trên một bản sao: tính lại, ẩn dòng "Not Use" theo cột B, ẩn hàng kiểm và 4 cột phụ, đặt vùng in
(A4: X:AO, A3: X:BB), giữ khối chữ ký trên một trang, xuất PDF. Bản giao không bị mở để ghi.

Mã thoát: 0 = xong, 2 = dừng có thông báo ("STOPPED: ...").
"""
import argparse
import os
import sys

SOURCE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SOURCE_DIR not in sys.path:
    sys.path.insert(0, SOURCE_DIR)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--deliverable', required=True)
    ap.add_argument('--paper', required=True)
    ap.add_argument('--out', required=True)
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)
    os.chdir(SOURCE_DIR)

    import print_layout
    try:
        pages = print_layout.export_pdf(os.path.abspath(args.deliverable), args.paper.upper(), os.path.abspath(args.out))
    except print_layout.PrintError as exc:
        print(f'STOPPED: {exc}')
        return 2
    print(f'PDF {args.paper.upper()}: {os.path.basename(args.out)}' + (f' ({pages} trang)' if pages else ''))
    return 0


if __name__ == '__main__':
    sys.exit(main())
