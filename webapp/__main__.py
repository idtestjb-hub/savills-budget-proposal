"""
    cd source_code
    python -m webapp

Biến môi trường (đều có mặc định): BUDGET_WEB_HOST (127.0.0.1), BUDGET_WEB_PORT (8090),
BUDGET_WEB_PREFIX (/budget), BUDGET_WEB_RUNS (..\\reports\\web_runs). Chỉ bind đúng host đó.
Log ra stdout/stderr.
"""
import os
import sys

import uvicorn

from webapp.server import HOST, PORT, PREFIX, RUNS_DIR, app


def main():
    sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)
    sys.stderr.reconfigure(encoding='utf-8', line_buffering=True)
    os.makedirs(RUNS_DIR, exist_ok=True)
    print(f'Budget web: http://{HOST}:{PORT}/  (prefix {PREFIX or "/"}; runs: {RUNS_DIR})', flush=True)
    uvicorn.run(app, host=HOST, port=PORT, log_level='info')


if __name__ == '__main__':
    main()
