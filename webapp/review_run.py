"""
Run the Budget Review (review.py) for ONE approved budget workbook, with everything written into ONE folder,
without touching Budget_Agent/reports or Budget_Agent/sample_output.

    python webapp/review_run.py --prior <approved .xlsx> --facts <facts.json> --workdir <folder> [--recalc]

review.run() already isolates the pipeline (verification.isolation) and writes the form into <workdir>/input,
the three workbooks into <workdir>/run, deliverable_recalc.xlsx and review_summary.md/json into <workdir>.

--recalc: the prior workbook was written by the tool itself (the deliverable of an earlier run, "Gen budget for
new year" on the history page). openpyxl writes formulas without cached values, so the month headers and the
year column read as empty; Excel recalculates a copy first (<workdir>/prior_recalc.xlsx) and that copy is read.

After the review, <workdir>/review_notes.json holds the import notes and what was filled on the form, so the
page can show them without re-reading the form. Exit code: review.run's own (0 = every tie holds, 1 = a tie
fails), 2 = stopped with a message (printed as "STOPPED: ...").
"""
import argparse
import json
import os
import re
import sys

SOURCE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SOURCE_DIR not in sys.path:
    sys.path.insert(0, SOURCE_DIR)

NOTES_FILE = 'review_notes.json'
RECALC_FILE = 'prior_recalc.xlsx'

YEAR_STOP = re.compile(r"Prior Budget Year' is (\d{4}), which is not before the budget year (\d{4})")


def year_hint(message):
    """Câu tiếng Việt giải thích lỗi 'Prior Budget Year ... not before the budget year ...' (file ngân sách đã duyệt thuộc
    năm từ năm của mẫu trở lên), để trang không chỉ hiện câu tiếng Anh. Chuỗi rỗng với mọi lỗi khác."""
    m = YEAR_STOP.search(message or '')
    if not m:
        return ''
    prior, budget = m.group(1), m.group(2)
    return (f'Dừng: file ngân sách đã duyệt thuộc năm {prior}, còn công cụ lập ngân sách năm {budget}. Review cần ngân '
            f'sách đã duyệt của năm TRƯỚC năm {budget} (từ năm {int(budget) - 1} trở về trước). Chọn file khác, hoặc '
            f'dùng tab Nhập liệu nếu đây là dự án mới.')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--prior', required=True)
    ap.add_argument('--facts', default=None)
    ap.add_argument('--workdir', required=True)
    ap.add_argument('--recalc', action='store_true')
    args = ap.parse_args()

    sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)
    sys.stderr.reconfigure(encoding='utf-8', line_buffering=True)
    os.chdir(SOURCE_DIR)

    import review
    import review_import as ri

    workdir = os.path.abspath(args.workdir)
    os.makedirs(workdir, exist_ok=True)
    prior = os.path.abspath(args.prior)
    try:
        if args.recalc:
            print('[0/4] Excel tính lại bản giao của lượt cũ để đọc được cột năm và 12 tháng')
            dst = os.path.join(workdir, RECALC_FILE)
            review.recalc_copy(prior, dst)
            prior = dst
        code, result = review.run(prior, facts_path=args.facts, workdir=workdir, quiet=False)
    except (ri.PriorBudgetError, review.ReviewError, ValueError, LookupError, RuntimeError) as exc:
        print(f'STOPPED: {exc}')
        hint = year_hint(str(exc))
        if hint:
            print(hint)
        return 2
    notes = [dict(kind=k, where=w, text=t) for k, w, t in result['notes']]
    with open(os.path.join(workdir, NOTES_FILE), 'w', encoding='utf-8') as fh:
        json.dump(dict(notes=notes, filled=result['filled'], exit_code=code, prior=prior),
                  fh, ensure_ascii=False, indent=1, default=str)
    return code


if __name__ == '__main__':
    sys.exit(main())
