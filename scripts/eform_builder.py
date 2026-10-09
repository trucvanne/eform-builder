# -*- coding: utf-8 -*-
"""Cấu hình Eform dạng bảng (x-table, cố định số dòng, cột nhóm nhiều tầng) trên Nền tảng khai phá dữ liệu động từ spec.json.

Hệ thống được clone cho nhiều đơn vị nên domain KHÔNG cố định: script tự lấy địa chỉ từ tab đang mở
trang danh sách Eform (/list-eform), hoặc nhận qua --base-url https://<domain-cua-don-vi>.
Trình duyệt (xem browser.py):
  --browser cdp (mặc định)  : Chrome / Edge / Cốc Cốc / Brave / Chromium đã mở bằng 'python browser.py open ...'
  --browser firefox|webkit  : Playwright tự mở cửa sổ, cần --base-url; người dùng TỰ đăng nhập.
Lệnh (Windows dùng 'python' hoặc 'py' thay cho 'python3'):
  python3 eform_builder.py build  --spec spec.json --form KEY            # dry-run: dựng xong, in kiểm tra, HỦY BỎ (không lưu)
  python3 eform_builder.py build  --spec spec.json --form KEY --save     # dựng và Lưu (Lưu nháp) + đối chiếu dữ liệu gửi lên
  python3 eform_builder.py verify --spec spec.json --form KEY            # đọc cấu hình đã lưu trên server, so với spec (không sửa)
Script không bao giờ bấm Phát hành / Phân quyền / Xóa.
"""
import argparse, json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from browser import make_driver, CHROMIUM, PLAYWRIGHT
from common import utf8_console

HELPERS = r"""
window.T=(t,s)=>[...document.querySelectorAll((s?s+' ':'')+'*')].filter(e=>(e.innerText||'').trim()===t&&e.getBoundingClientRect().height>0).sort((a,b)=>a.getBoundingClientRect().width*a.getBoundingClientRect().height-b.getBoundingClientRect().width*b.getBoundingClientRect().height)[0];
window.B=(l,i)=>[...document.querySelectorAll('button')].filter(b=>(b.getAttribute('aria-label')||b.title||b.innerText||'').trim()===l&&b.getBoundingClientRect().height>0)[i||0];
window.D=()=>[...document.querySelectorAll('[role=dialog]')].pop();
window.ROWS=()=>[...D().querySelectorAll('input[placeholder="Nhập tiêu đề..."]')].map(t=>{let r=t;while(r&&r.querySelectorAll('button').length<2)r=r.parentElement;return {t,r}});
window.RB=(j,l)=>[...ROWS()[j].r.querySelectorAll('button')].find(b=>(b.title||b.getAttribute('aria-label'))===l);
window.PIN=(j)=>[...ROWS()[j].r.querySelectorAll('button')].filter(b=>!(b.title||b.getAttribute('aria-label')))[0];
window.FBOX=()=>{const p=T('Thêm nhiều dòng','[role=dialog]');if(!p)return null;let b=p;for(let i=0;i<6;i++){b=b.parentElement;if(b.innerText.includes('Dữ liệu cố định'))break}return b};
window.DUMP=()=>ROWS().map(({t,r},j)=>{const a=r.querySelector('input[placeholder="Nhập thuộc tính..."]'),k=r.querySelector('[role=combobox]'),w=r.querySelector('input[placeholder="Auto"]');return j+' ['+r.innerText.trim().split(/\s/)[0]+'] '+t.value+' | '+(a?a.value:'')+' | '+(k?k.innerText:'Nhóm')+' | '+(w?w.value:'-')}).join('\n');
(()=>{if(window.__cap)return;window.__cap=[];const oo=XMLHttpRequest.prototype.open,os=XMLHttpRequest.prototype.send;
XMLHttpRequest.prototype.open=function(m,u){this.__u=u;this.__m=m;return oo.apply(this,arguments)};
XMLHttpRequest.prototype.send=function(b){this.addEventListener('load',()=>{if(/eform/i.test(this.__u))window.__cap.push({m:this.__m,u:this.__u,req:typeof b==='string'?b:null,s:this.status,r:this.responseText||''})});return os.apply(this,arguments)};
window.__toasts=[];new MutationObserver(()=>{document.querySelectorAll('.Toastify__toast, .MuiAlert-root').forEach(e=>{const t=e.innerText.trim();if(t&&!window.__toasts.includes(t))window.__toasts.push(t)})}).observe(document.body,{childList:true,subtree:true})})();
'ok'
"""


class Page:
    def __init__(self, a):
        self.d = make_driver(a.browser, a.port, a.base_url, a.profile)
        self.base = self.d.base
        print('Hệ thống:', self.base)
        self.d.set_viewport(2100, 1260)

    def js(self, expr):
        return self.d.eval(expr)

    def helpers(self):
        return self.js(HELPERS)

    def wait(self, expr, timeout=10, step=0.25):
        t0 = time.time()
        while time.time() - t0 < timeout:
            v = self.js('!!(%s)' % expr)
            if v is True:
                return v
            time.sleep(step)
        raise TimeoutError('wait: ' + expr[:120])

    def jsclick(self, expr, pause=0.5):
        r = self.js('(()=>{const e=(%s);if(!e)return "NF";e.click();return "ok"})()' % expr)
        if r != 'ok':
            raise RuntimeError('không tìm thấy để bấm: ' + expr[:120])
        time.sleep(pause)

    def mclick(self, expr, pause=0.5):
        r = self.js('(()=>{const e=(%s);if(!e)return null;e.scrollIntoView({block:"nearest"});const b=e.getBoundingClientRect();return [b.x+b.width/2,b.y+b.height/2]})()' % expr)
        if not isinstance(r, list):
            raise RuntimeError('không tìm thấy để bấm chuột: ' + expr[:120])
        self.d.click_at(r[0], r[1])
        time.sleep(pause)

    def type_into(self, expr, text):
        r = self.js('(()=>{const i=(%s);if(!i)return "NF";i.focus();i.select&&i.select();return "ok"})()' % expr)
        if r != 'ok':
            raise RuntimeError('không tìm thấy ô nhập: ' + expr[:120])
        self.d.insert_text(text)

    def choose_option(self, combo_expr, label):
        self.mclick(combo_expr, 0.5)
        self.mclick('[...document.querySelectorAll("[role=option]")].find(o=>o.innerText.trim()==%s)' % json.dumps(label), 0.4)

    def nav(self, url, wait=3):
        self.d.goto(url); time.sleep(wait); self.helpers()


def size(col):
    return 1 + sum(size(c) for c in col.get('children') or [])


def fill_col(p, j, col):
    p.type_into('ROWS()[%d].t' % j, col['title'])
    p.type_into('ROWS()[%d].r.querySelector(\'input[placeholder="Nhập thuộc tính..."]\')' % j, col.get('attr') or col['title'])
    if col.get('children'):
        return
    kind = col.get('type', 'Text')
    combo = 'ROWS()[%d].r.querySelector("[role=combobox]")' % j
    if kind == 'Text':                     # cột mới mặc định kiểu null: chọn kiểu khác rồi chọn lại Text
        p.choose_option(combo, 'Date')
    p.choose_option(combo, kind)
    if col.get('width'):
        p.type_into('ROWS()[%d].r.querySelector(\'input[placeholder="Auto"]\')' % j, col['width'])


def build_list(p, cols, first):
    """cols: các cột cùng cấp; cột đầu tiên đã có sẵn tại chỉ số 'first'."""
    idx = first
    for k, col in enumerate(cols):
        if k > 0:
            prev = idx
            p.jsclick('RB(%d,"Thêm cột cùng cấp")' % prev)
            idx = prev + size(cols[k - 1])
        fill_col(p, idx, col)
        if col.get('children'):
            p.jsclick('RB(%d,"Thêm cột con (nhóm)")' % idx)
            build_list(p, col['children'], idx + 1)


def leaves_with_index(cols, start=0):
    out, i = [], start
    for c in cols:
        if c.get('children'):
            out += leaves_with_index(c['children'], i + 1)
        else:
            out.append((i, c))
        i += size(c)
    return out


def fill_fixed(p, j, values):
    p.jsclick('PIN(%d)' % j, 0.8)
    p.wait('FBOX()')
    box = 'FBOX()'
    have = p.js('%s.querySelectorAll(\'input[placeholder="Nhập nội dung..."]\').length' % box)
    while have < len(values):
        k = min(50, len(values) - have)
        p.type_into('%s.querySelector("input[type=number]")' % box, k)
        p.jsclick('[...%s.querySelectorAll("button")].find(b=>b.innerText.trim()=="Thêm")' % box, 0.8)
        have = p.js('%s.querySelectorAll(\'input[placeholder="Nhập nội dung..."]\').length' % box)
    for i, v in enumerate(values):
        p.type_into('%s.querySelectorAll(\'input[placeholder="Nhập nội dung..."]\')[%d]' % (box, i), v)
    got = p.js('document.activeElement.blur(),[...%s.querySelectorAll(\'input[placeholder="Nhập nội dung..."]\')].map(i=>i.value)' % box)
    p.jsclick('PIN(%d)' % j, 0.6)
    if got != values:
        raise RuntimeError('Dữ liệu cố định cột %d không khớp sau khi nhập' % j)


def tree_of(fields):
    return [{'title': f.get('description'), 'attr': f.get('fieldName'),
             **({'children': tree_of(f['children'])} if f.get('children') else {'type': (f.get('typeControl') or f.get('type') or 'null'), 'fixed': f.get('fixedRowValues')})}
            for f in sorted(fields, key=lambda f: f.get('orderIndex') or 0)]


def norm_spec(cols):
    return [{'title': c['title'], 'attr': c.get('attr') or c['title'],
             **({'children': norm_spec(c['children'])} if c.get('children') else {'type': c.get('type', 'Text').lower(), 'fixed': c.get('fixed')})}
            for c in cols]


def compare(spec_form, meta):
    want, got = norm_spec(spec_form['columns']), tree_of(meta['fields'])
    ok = want == got
    if not ok:
        print('  KHÁC spec:\n  spec  =', json.dumps(want, ensure_ascii=False)[:1500], '\n  thực tế=', json.dumps(got, ensure_ascii=False)[:1500])
    return ok


def cmd_build(p, a, form):
    p.nav(p.base + '/list-eform', 3.5)
    p.jsclick('B("Thêm mới")', 3)
    p.helpers()
    p.wait('document.querySelector(\'input[placeholder="Nhập tên E-Form"]\')')
    p.type_into('document.querySelector(\'input[placeholder="Nhập tên E-Form"]\')', form['name'])
    if form.get('group'):
        p.mclick('T("Chọn nhóm")', 1)
        p.mclick('T(%s,".MuiPopover-root")' % json.dumps(form['group']), 0.6)
    p.choose_option('document.querySelectorAll("tbody [role=combobox]")[0]', 'x-table')
    R = '[...document.querySelectorAll("tbody tr")][0].querySelectorAll("input[type=text]")'
    p.type_into(R + '[0]', form['attr'])
    p.type_into(R + '[1]', form.get('title') or form['name'])
    p.type_into(R + '[2]', form.get('title') or form['name'])
    p.jsclick('[...document.querySelectorAll("tbody tr")][0].querySelector(\'button[title="Chỉnh sửa"], button[aria-label="Chỉnh sửa"]\')', 1.5)
    p.wait('D() && D().querySelector(\'input[placeholder="Nhập tiêu đề..."]\')')
    sw = '(()=>{let e=T("Cố định số dòng","[role=dialog]");while(e&&!e.querySelector("input[type=checkbox]"))e=e.parentElement;return e.querySelector("input[type=checkbox]")})()'
    if bool(form.get('fixed_row', True)) != bool(p.js(sw + '.checked')):
        p.mclick(sw, 0.6)
    build_list(p, form['columns'], 0)
    for j, c in leaves_with_index(form['columns']):
        if c.get('fixed'):
            fill_fixed(p, j, c['fixed'])
    print(p.js('document.activeElement.blur(),DUMP()'))
    p.jsclick('[...D().querySelectorAll("button")].find(b=>b.innerText.trim()=="Lưu")', 1.2)
    # nội dung: tiêu đề + bảng
    ed = 'document.querySelector(".ck-editor__editable").ckeditorInstance'
    p.mclick('document.querySelector(".ck-editor__editable")', 0.4)
    p.d.insert_text(form.get('heading') or form['name'].upper())
    p.js('(()=>{const ed=%s;const root=ed.model.document.getRoot();ed.model.change(w=>w.setSelection(root.getChild(0),"in"));ed.execute("bold");ed.execute("alignment",{value:"center"});ed.execute("fontSize",{value:"16px"});ed.model.change(w=>{const q=w.createElement("paragraph");w.insert(q,root,"end");w.setSelection(q,"in")});ed.editing.view.focus();return 1})()' % ed)
    p.d.insert_text('[[' + form['attr'][:-1]); time.sleep(1)
    p.d.press('Enter')
    time.sleep(1)
    html = p.js('%s.getData()' % ed)
    assert ('[[%s]]' % form['attr']) in html, 'chưa chèn được thuộc tính vào nội dung'
    p.js('document.activeElement.blur(),1'); time.sleep(1.2)
    pv = p.js('(()=>{const t=[...document.querySelectorAll("table")].pop();return {head:t.querySelectorAll("thead tr").length,rows:t.querySelectorAll("tbody tr").length}})()')
    print('Xem trước:', pv)
    if not a.save:
        p.jsclick('B("Hủy bỏ")', 1)
        p.jsclick('[...document.querySelectorAll("[role=dialog] button")].find(b=>b.innerText.trim()=="Đồng ý"&&b.getBoundingClientRect().height>0)', 2)
        print('DRY-RUN: đã hủy bỏ, không lưu gì lên hệ thống.')
        return
    p.js('window.__cap=[],window.__toasts=[],window.scrollTo(0,0),1')
    p.jsclick('B("Lưu")', 3)
    print('Thông báo:', p.js('window.__toasts'))
    req = p.js('(()=>{const c=window.__cap.find(x=>x.m!="GET"&&/\\/eform\\/(create|update)/.test(x.u));return c?c.req:null})()')
    meta = json.loads(req)['metadata'][0]
    print('Đối chiếu dữ liệu gửi lên:', 'KHỚP' if compare(form, meta) else 'LỆCH')


def cmd_verify(p, a, form):
    p.nav(p.base + '/list-eform', 3.5)
    p.js('window.__cap=[],1')
    p.jsclick('[...document.querySelectorAll("tbody tr")].find(r=>r.querySelectorAll("td")[1].innerText.trim()==%s).querySelector(\'button[title="Chỉnh sửa eform"], button[aria-label="Chỉnh sửa eform"]\')' % json.dumps(form['name']), 3.5)
    raw = p.js('(()=>{const c=window.__cap.filter(x=>x.u.includes("find-by-id")).pop();return c?c.r:null})()')
    x = json.loads(raw); x = x.get('data', x)
    print(x['name'], '|', x['status'], '|', x.get('groupName'))
    print('Đối chiếu server với spec:', 'KHỚP' if compare(form, x['metadata'][0]) else 'LỆCH')
    p.helpers()
    p.jsclick('B("Hủy bỏ")', 1)
    p.jsclick('[...document.querySelectorAll("[role=dialog] button")].find(b=>b.innerText.trim()=="Đồng ý"&&b.getBoundingClientRect().height>0)', 2)


def main():
    utf8_console()
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['build', 'verify'])
    ap.add_argument('--spec', required=True); ap.add_argument('--form', required=True)
    ap.add_argument('--save', action='store_true'); ap.add_argument('--port', type=int, default=9334)
    ap.add_argument('--base-url', default=None, help='vd https://<domain-cua-don-vi>; bỏ trống để tự lấy từ tab đang mở (chỉ với CDP)')
    ap.add_argument('--browser', default='cdp', choices=('cdp',) + CHROMIUM + PLAYWRIGHT,
                    help='cdp/chrome/edge/coccoc/brave/chromium: gắn vào trình duyệt đã mở; firefox/webkit: Playwright')
    ap.add_argument('--profile', default=None, help='thư mục hồ sơ riêng cho firefox/webkit')
    a = ap.parse_args()
    spec = json.load(open(a.spec, encoding='utf-8'))
    form = spec['forms'][a.form]
    p = Page(a)
    try:
        (cmd_build if a.cmd == 'build' else cmd_verify)(p, a, form)
    finally:
        p.d.close()


if __name__ == '__main__':
    main()
