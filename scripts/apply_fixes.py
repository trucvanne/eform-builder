# -*- coding: utf-8 -*-
"""Áp dụng CHỈ những phát hiện đã được người dùng duyệt từng dòng vào spec.

Dùng:  python3 apply_fixes.py spec.json findings.json approvals.json --out spec.fixed.json [--log changelog.md]

approvals.json: { "F002": "approve", "F003": "reject", "F017": {"value": "Giá trị người dùng tự nhập"} }
  - "approve"          : dùng giá trị 'suggestion' của phát hiện
  - {"value": "..."}   : dùng giá trị người dùng nhập (mục 'Other')
  - "reject" / thiếu   : giữ nguyên (mặc định an toàn: không có duyệt = không đổi)
Mỗi thay đổi kiểm tra lại giá trị hiện tại trước khi ghi; lệch thì bỏ qua và báo.
"""
import argparse, json, sys


def find_col(cols, path):
    cur = None
    for t in path:
        cur = next((c for c in cols if c['title'] == t), None)
        if cur is None:
            return None
        cols = cur.get('children') or []
    return cur


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('spec'); ap.add_argument('findings'); ap.add_argument('approvals')
    ap.add_argument('--out', required=True); ap.add_argument('--log', default='changelog.md')
    a = ap.parse_args()
    spec = json.load(open(a.spec, encoding='utf-8'))
    fnd = {x['id']: x for x in json.load(open(a.findings, encoding='utf-8'))['findings']}
    appr = json.load(open(a.approvals, encoding='utf-8'))
    log, skipped = [], []
    for fid, dec in appr.items():
        x = fnd.get(fid)
        if x is None:
            skipped.append(f'{fid}: không có trong findings'); continue
        if dec == 'reject' or dec is None:
            continue
        new = dec.get('value') if isinstance(dec, dict) else (x['suggestion'] if dec == 'approve' else None)
        if new is None:
            skipped.append(f'{fid}: duyệt nhưng không có giá trị đề xuất, cần {{"value": ...}}'); continue
        loc = x.get('loc') or {}
        form = spec['forms'].get(x['form'])
        if form is None:
            skipped.append(f'{fid}: không áp dụng tự động (phạm vi nhiều form), sửa tay sau khi người dùng xác nhận'); continue
        if loc.get('type') == 'name':
            if form['name'] != x['current']:
                skipped.append(f'{fid}: giá trị hiện tại đã khác'); continue
            form['name'] = new
        elif loc.get('type') == 'col_title':
            c = find_col(form['columns'], loc['path'])
            if not c or c['title'] != x['current']:
                skipped.append(f'{fid}: không tìm thấy cột hoặc giá trị đã khác'); continue
            c['title'] = new
        elif loc.get('type') == 'fixed':
            c = find_col(form['columns'], loc['path'])
            if not c or c['fixed'][loc['row']] != x['current']:
                skipped.append(f'{fid}: không tìm thấy dòng hoặc giá trị đã khác'); continue
            c['fixed'][loc['row']] = new
        elif loc.get('type') == 'fixed_all':
            c = find_col(form['columns'], loc['path'])
            c['fixed'] = [new] * len(c['fixed'])
        else:
            skipped.append(f'{fid}: loại vị trí chưa hỗ trợ'); continue
        log.append(f"| {fid} | {x['form']} | {x['where']} | {x['current']} | {new} |")
    json.dump(spec, open(a.out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    with open(a.log, 'w', encoding='utf-8') as f:
        f.write('| Mã | Form | Vị trí | Trước | Sau |\n|---|---|---|---|---|\n' + '\n'.join(log) + '\n')
        if skipped:
            f.write('\nBỏ qua:\n' + '\n'.join('- ' + s for s in skipped) + '\n')
    print(f'Đã áp dụng {len(log)} thay đổi được duyệt; bỏ qua {len(skipped)}. Spec mới: {a.out}. Nhật ký: {a.log}')
    for s in skipped:
        print('  bỏ qua:', s)


if __name__ == '__main__':
    main()
