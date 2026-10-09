# -*- coding: utf-8 -*-
"""Rà soát spec Eform: chính tả, viết hoa, kiểu bỏ dấu, tiền tố thừa, trùng lặp, dòng nghi vấn.

Dùng:  python3 review_spec.py spec.json [--source-title "THÁNG 8"] [--out findings.json] [--xlsx duyet.xlsx]
Đầu ra: findings.json (mỗi phát hiện = 1 dòng cần duyệt) + bảng Markdown in ra màn hình
        + phiếu duyệt Excel duyet.xlsx (cột "Quyết định" cho từng dòng; --xlsx "" để không tạo).
Script KHÔNG sửa spec. Việc sửa chỉ làm qua apply_fixes.py với approvals.json hoặc duyet.xlsx do người dùng duyệt từng dòng.
"""
import argparse, json, re, sys, os
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vn_text import nfc, suspicious_words, tone_style, to_style, sentence_case, AGENCY_HEADS
from common import utf8_console

TYPO_DICT = {  # lỗi gõ hay gặp trong danh mục hành chính -> đề xuất
    'Văn phong Ủy ban': 'Văn phòng Ủy ban', 'Văn phong Uỷ ban': 'Văn phòng Uỷ ban',
    'thủ tuc': 'thủ tục', 'hành chinh': 'hành chính',
}


def walk_columns(cols, path=()):
    for i, c in enumerate(cols):
        p = path + (c['title'],)
        yield p, c
        if c.get('children'):
            yield from walk_columns(c['children'], p)


def leaves(cols):
    return [(p, c) for p, c in walk_columns(cols) if not c.get('children')]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('spec')
    ap.add_argument('--source-title', default='', help='Tiêu đề/tên file nguồn, vd "BIỂU MẪU BC THÁNG 8" để đối chiếu kỳ báo cáo')
    ap.add_argument('--out', default='findings.json')
    ap.add_argument('--xlsx', default='duyet.xlsx', help='phiếu duyệt Excel cho người dùng; "" để không tạo')
    utf8_console()
    a = ap.parse_args()
    spec = json.load(open(a.spec, encoding='utf-8'))

    # kiểu bỏ dấu chiếm đa số trong toàn bộ dữ liệu -> dùng làm chuẩn
    all_text = []
    for f in spec['forms'].values():
        all_text += [f['name']] + [c['title'] for _, c in walk_columns(f['columns'])]
        for _, c in walk_columns(f['columns']):
            all_text += c.get('fixed') or []
    old = sum(tone_style(t)[0] for t in all_text); new = sum(tone_style(t)[1] for t in all_text)
    style = 'new' if new >= old else 'old'

    findings = []
    rank = {'low': 0, 'medium': 1, 'high': 2}
    def add(form, where, current, suggestion, reasons, kind='fix', severity='medium', loc=None):
        # gom mọi phát hiện của cùng một ô dữ liệu thành 1 dòng duyệt
        for x in findings:
            if x['form'] == form and x['where'] == where and x['current'] == current:
                x['reasons'] += [r for r in reasons if r not in x['reasons']]
                if suggestion and not x['suggestion']:
                    x['suggestion'] = suggestion
                x['kind'] = 'fix' if x['suggestion'] else 'question'
                if rank[severity] > rank[x['severity']]:
                    x['severity'] = severity
                return
        findings.append({'id': f'F{len(findings)+1:03d}', 'form': form, 'where': where, 'current': current,
                         'suggestion': suggestion, 'reasons': reasons, 'kind': kind, 'severity': severity, 'loc': loc})

    def check_text(form, where, text, list_ctx=None, loc=None):
        reasons, sug = [], nfc(text)
        if text != nfc(text):
            reasons.append('Chuỗi chưa chuẩn hóa Unicode NFC (dễ lệch khi tìm kiếm/so khớp)')
        s2 = re.sub(r'\s+', ' ', sug).strip()
        if s2 != sug:
            reasons.append('Khoảng trắng thừa'); sug = s2
        for k, v in TYPO_DICT.items():
            if k in sug and k != v:
                sug = sug.replace(k, v); reasons.append(f'Nghi lỗi gõ: "{k}" → "{v}"')
        o, n = tone_style(sug)
        if (style == 'new' and o) or (style == 'old' and n):
            sug = to_style(sug, style)
            reasons.append('Kiểu bỏ dấu không thống nhất (hòa/hoà, thủy/thuỷ); chuẩn theo kiểu chiếm đa số: ' + ('mới (òa, ủy)' if style == 'new' else 'cũ (oà, uỷ)'))
        if list_ctx:
            pre = list_ctx.get('prefix')
            if pre and sug.startswith(pre):
                sug = sug[len(pre):].strip()
                reasons.append(f'Tiền tố "{pre.strip()}" chỉ có ở {list_ctx["prefix_n"]}/{list_ctx["n"]} dòng và trùng nghĩa tên cột; bỏ cho thống nhất')
        if not sug.startswith(AGENCY_HEADS):
            sc = sentence_case(sug)
            if sc != sug:
                reasons.append('Viết hoa giữa cụm từ không phải danh từ riêng; chuẩn viết hoa chữ đầu')
                sug = sc
        else:
            # tên cơ quan viết hoa mọi âm tiết, vd "Sở Quy Hoạch Kiến Trúc"
            ws = sug.split()
            if len(ws) >= 4 and all(w[:1].isupper() for w in ws if w.isalpha()):
                reasons.append('Tên cơ quan viết hoa mọi âm tiết; nên viết hoa chữ đầu của từ chỉ loại cơ quan và từ đầu của tên riêng [cần người dùng xác nhận]')
                sug = ws[0] + ' ' + ws[1] + ' ' + ' '.join(w.lower() if i % 2 == 1 else w for i, w in enumerate(ws[2:], 1))
        bad = suspicious_words(sug)
        if bad:
            reasons.append('Có từ không giống âm tiết tiếng Việt (nghi lỗi chính tả): ' + ', '.join(bad))
        if reasons:
            add(form, where, text, sug if sug != text else None, reasons, 'fix' if sug != text else 'question', loc=loc)

    for key, f in spec['forms'].items():
        check_text(key, 'Tên E-Form', f['name'], loc={'type': 'name'})
        titles = [(p, c) for p, c in walk_columns(f['columns'])]
        for p, c in titles:
            check_text(key, 'Tiêu đề cột: ' + ' > '.join(p), c['title'], loc={'type': 'col_title', 'path': list(p)})
        # trùng tiêu đề giữa các cột cùng cấp
        def sib_dups(cols, path=()):
            cnt = Counter(c['title'] for c in cols)
            for t, n in cnt.items():
                if n > 1:
                    add(key, 'Cột cùng cấp: ' + (' > '.join(path) or '(gốc)'), t, None, [f'{n} cột cùng cấp trùng tiêu đề'], 'question', 'high')
            for c in cols:
                if c.get('children'):
                    sib_dups(c['children'], path + (c['title'],))
        sib_dups(f['columns'])
        attrs = Counter(c['attr'] for _, c in leaves(f['columns']))
        for at, n in attrs.items():
            if n > 1:
                add(key, 'Thuộc tính cột lá', at, None, [f'{n} cột lá dùng chung THUỘC TÍNH → nguy cơ đè dữ liệu'], 'question', 'high')
        # dữ liệu cố định
        for p, c in walk_columns(f['columns']):
            vals = c.get('fixed')
            if not vals:
                continue
            col = ' > '.join(p)
            words0 = Counter(' '.join(v.split()[:2]) + ' ' for v in vals if len(v.split()) > 2)
            ctx = {'n': len(vals)}
            for pre, k in words0.most_common(3):
                if pre.strip() and pre.strip().lower() in c['title'].lower() and 0 < k < len(vals) * 0.6:
                    ctx.update(prefix=pre, prefix_n=k)
                    break
            dup = [v for v, k in Counter(vals).items() if k > 1]
            if dup and len(set(vals)) > 1:
                for v in dup:
                    add(key, f'Dữ liệu cố định "{col}"', v, None, [f'Giá trị lặp {vals.count(v)} lần trong danh sách'], 'question', 'high')
            for i, v in enumerate(vals):
                check_text(key, f'Dữ liệu cố định "{col}" dòng {i+1}', v, ctx, loc={'type': 'fixed', 'path': list(p), 'row': i})
                if 'lĩnh vực' in c['title'].lower() and v.startswith(AGENCY_HEADS):
                    add(key, f'Dữ liệu cố định "{col}" dòng {i+1}', v, None,
                        ['Giá trị là tên cơ quan, không phải tên lĩnh vực; cần xác nhận giữ nguyên hay đổi'], 'question', 'medium',
                        loc={'type': 'fixed', 'path': list(p), 'row': i})
            # kỳ báo cáo so với tên nguồn
            if c['title'].lower() in ('tháng', 'kỳ báo cáo') and a.source_title:
                m = re.search(r'TH[ÁA]NG\s*(\d{1,2})', a.source_title.upper())
                if m and set(vals) != {m.group(1)} and set(vals) != {'Tháng ' + m.group(1)}:
                    add(key, f'Dữ liệu cố định "{col}"', ', '.join(sorted(set(vals))), None,
                        [f'Nguồn ghi tháng {m.group(1)} nhưng dữ liệu là {", ".join(sorted(set(vals)))}'], 'question', 'medium',
                        loc={'type': 'fixed_all', 'path': list(p)})
    # tên các form không thống nhất cấu trúc
    names = [f['name'] for f in spec['forms'].values()]
    heads = Counter(n.split(',')[0].split()[0] for n in names)
    if len(heads) > 1:
        add('*', 'Tên E-Form (so sánh giữa các form)', ' | '.join(names), None,
            ['Các tên E-Form bắt đầu khác nhau: ' + ', '.join(heads)], 'question', 'low')

    json.dump({'style': style, 'findings': findings}, open(a.out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'| No. | Mã | Form | Vị trí | Hiện tại | Đề xuất | Lý do |')
    print('|---|---|---|---|---|---|---|')
    for i, x in enumerate(findings, 1):
        print(f"| {i} | {x['id']} | {x['form']} | {x['where']} | {x['current']} | {x['suggestion'] or '(cần xác nhận)'} | {'; '.join(x['reasons'])} |")
    print(f'\nTổng: {len(findings)} phát hiện ({sum(1 for x in findings if x["kind"]=="fix")} có đề xuất sửa, {sum(1 for x in findings if x["kind"]=="question")} cần xác nhận). Kết quả: {a.out}')
    if a.xlsx:
        from approval_sheet import write_sheet
        write_sheet(findings, a.xlsx)
        print(f'Phiếu duyệt từng dòng: {a.xlsx} (chọn cột "Quyết định" cho từng dòng rồi chạy apply_fixes.py)')


if __name__ == '__main__':
    main()
