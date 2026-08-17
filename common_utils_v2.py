import os
import re
import zipfile
import openpyxl
import unicodedata

def norm(s: str) -> str:
    """Normalize string to NFC to handle Vietnamese characters properly."""
    if not isinstance(s, str): return ""
    return unicodedata.normalize('NFC', s)

def safe_code(text: str, max_len: int = 20) -> str:
    """Create a safe, uppercase code from text."""
    base = re.sub(r'[^A-Za-z0-9]+', '-', str(text)).strip('-').upper()
    return base[:max_len]

def project_code_from_filename(filepath: str, seq: int) -> str:
    """Generate a unique project code based on filename and sequence."""
    base = safe_code(os.path.splitext(os.path.basename(filepath))[0])
    return f"PRJ-{seq:04d}-{base}"

def repair_workbook(filepath: str) -> str:
    """
    Strips corrupted <definedNames> block if present so openpyxl can load the file.
    Returns the path to a repaired temp copy (or original if healthy).
    """
    try:
        openpyxl.load_workbook(filepath, read_only=True)
        return filepath
    except Exception:
        pass

    repaired_path = filepath.replace('.xlsx', '__repaired.xlsx')
    with zipfile.ZipFile(filepath, 'r') as zin:
        wbxml = zin.read('xl/workbook.xml').decode('utf-8')
        cleaned = re.sub(r'<definedNames>.*?</definedNames>', '', wbxml, flags=re.DOTALL)
        with zipfile.ZipFile(repaired_path, 'w', zipfile.ZIP_DEFLATED) as zout:
            for item in zin.namelist():
                data = zin.read(item)
                if item == 'xl/workbook.xml':
                    data = cleaned.encode('utf-8')
                zout.writestr(item, data)
    return repaired_path

def find_sheet_loose(wb, target: str):
    """Find a sheet name loosely matching the target string."""
    t = norm(target).strip().lower()
    for sn in wb.sheetnames:
        if t in norm(sn).strip().lower():
            return sn
    return None

def find_sheet_exact(wb, target: str):
    """Find a sheet name exactly matching the target string (after normalization)."""
    t = norm(target).strip().lower()
    for sn in wb.sheetnames:
        if t == norm(sn).strip().lower():
            return sn
    return None

def log_issues(issues: list, output_dir: str, filename: str = 'etl_issues.log'):
    """Log issues encountered during extraction."""
    if not issues:
        return
    path = os.path.join(output_dir, filename)
    mode = 'a' if os.path.exists(path) else 'w'
    with open(path, mode, encoding='utf-8') as f:
        f.write('\n'.join(issues) + '\n')

def get_dept_abbr(position_name: str) -> str:
    """Map a position name to a department abbreviation."""
    n = str(position_name).lower()
    if 'quản lý' in n or 'pm' in n or 'manager' in n or 'assistant' in n or 'apm' in n: return 'MGT'
    if 'kế toán' in n or 'acc' in n or 'account' in n: return 'ACC'
    if 'hành chính' in n or 'adm' in n or 'admin' in n: return 'ADM'
    if 'chăm sóc' in n or 'cs' in n or 'lễ tân' in n or 'concierge' in n: return 'CS'
    if 'kỹ thuật' in n or 'kỹ sư' in n or 'ce' in n or 'engineer' in n: return 'ME'
    if 'tiện ích' in n or 'amenit' in n or 'gym' in n or 'pool' in n: return 'AMN'
    if 'bảo vệ' in n or 'security' in n: return 'SEC'
    if 'vệ sinh' in n or 'clean' in n: return 'CLN'
    return 'GEN'

def get_budget_type(budget_code: str) -> str:
    c = str(budget_code).upper()
    if c.startswith('R'): return 'Revenue'
    if c.startswith('E'): return 'Expense'
    return 'Other'

def split_en_vn(text):
    """
    Splits a merged string into (English, Vietnamese) parts.
    Defaults to returning ('', text) if only one part is found, as requested.
    """
    if not text:
        return '', ''
    
    text = str(text).strip()
    
    if '\n' in text:
        parts = [p.strip() for p in text.split('\n', 1)]
    elif ' / ' in text:
        parts = [p.strip() for p in text.split(' / ', 1)]
    elif '/' in text:
        parts = [p.strip() for p in text.split('/', 1)]
    else:
        parts = [text]
        
    if len(parts) == 1:
        return '', parts[0]
        
    p1, p2 = parts[0], parts[1]
    
    # Check for Vietnamese characters to determine order.
    vietnamese_chars_set = set("àáãạảăắằẳẵặâấầẩẫậèéẹẻẽêềếểễệđìíĩỉịòóõọỏôốồổỗộơớờởỡợùúũụủưứừửữựỳỵỷỹý")
    
    def count_vn(s):
        return sum(1 for c in s.lower() if c in vietnamese_chars_set)
        
    # If part 1 has significantly more VN characters than part 2, then VN is first.
    if count_vn(p1) > count_vn(p2) and count_vn(p2) == 0:
        return p2, p1  # EN is p2, VN is p1
    else:
        return p1, p2  # EN is p1, VN is p2
