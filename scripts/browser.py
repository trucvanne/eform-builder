# -*- coding: utf-8 -*-
"""Lớp trình duyệt dùng chung cho eform_builder.py — chạy trên Windows, macOS, Linux.

Hai cách điều khiển:
  - CDP (không cần cài thêm): trình duyệt nhân Chromium — chrome, edge, coccoc, brave, chromium.
    Mở trình duyệt bằng lệnh 'open' bên dưới (hồ sơ riêng + cổng điều khiển), người dùng TỰ đăng nhập.
  - Playwright (cần 'pip install playwright' + 'playwright install firefox webkit'): firefox, webkit (nhân Safari).
    Script tự mở cửa sổ trình duyệt và chờ người dùng đăng nhập.

Lệnh:
  python browser.py list                                   # liệt kê trình duyệt tìm thấy trên máy
  python browser.py open --browser auto --url https://<domain-don-vi>/authenticate
  python browser.py open --browser edge --url ...          # chọn trình duyệt cụ thể
  python browser.py open --browser-path "D:\\Apps\\chrome.exe" --url ...   # cài ở chỗ khác
"""
import argparse, glob, json, os, shutil, subprocess, sys, time, urllib.request
from urllib.parse import urlparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cdp import WS, ev
from common import utf8_console

EFORM_PATHS = ('/list-eform', '/detail-eform', '/e-form/', '/quan-ly-nhom-eform')
CHROMIUM = ('chrome', 'edge', 'coccoc', 'brave', 'chromium')
PLAYWRIGHT = ('firefox', 'webkit')
PROFILE_ROOT = os.path.join(os.path.expanduser('~'), '.eform-builder')


def _candidates(name):
    if sys.platform == 'darwin':
        apps = ['/Applications', os.path.expanduser('~/Applications')]
        rel = {'chrome': ['Google Chrome.app/Contents/MacOS/Google Chrome'],
               'edge': ['Microsoft Edge.app/Contents/MacOS/Microsoft Edge'],
               'coccoc': ['CocCoc.app/Contents/MacOS/CocCoc', 'Cốc Cốc.app/Contents/MacOS/*', '*Coc*.app/Contents/MacOS/*'],
               'brave': ['Brave Browser.app/Contents/MacOS/Brave Browser'],
               'chromium': ['Chromium.app/Contents/MacOS/Chromium']}[name]
        return [p for a in apps for r in rel for p in sorted(glob.glob(os.path.join(a, r)))]
    if os.name == 'nt':
        roots = [os.environ.get(k) for k in ('PROGRAMFILES', 'PROGRAMFILES(X86)', 'LOCALAPPDATA')]
        rel = {'chrome': [r'Google\Chrome\Application\chrome.exe'],
               'edge': [r'Microsoft\Edge\Application\msedge.exe'],
               'coccoc': [r'CocCoc\Browser\Application\browser.exe'],
               'brave': [r'BraveSoftware\Brave-Browser\Application\brave.exe'],
               'chromium': [r'Chromium\Application\chrome.exe']}[name]
        return [os.path.join(r, x) for r in roots if r for x in rel]
    names = {'chrome': ['google-chrome', 'google-chrome-stable'], 'edge': ['microsoft-edge', 'microsoft-edge-stable'],
             'coccoc': ['coccoc', 'coccoc-browser'], 'brave': ['brave-browser', 'brave'],
             'chromium': ['chromium', 'chromium-browser']}[name]
    return [w for w in (shutil.which(n) for n in names) if w]


def find_browser(name):
    for p in _candidates(name):
        if os.path.isfile(p):
            return p
    return None


def detect():
    return {n: find_browser(n) for n in CHROMIUM}


def cdp_alive(port):
    try:
        return json.load(urllib.request.urlopen(f'http://127.0.0.1:{port}/json/version', timeout=2))
    except Exception:
        return None


def open_browser(name='auto', url='about:blank', port=9334, path=None, profile=None):
    """Mở trình duyệt nhân Chromium với hồ sơ riêng + cổng điều khiển. Không đụng hồ sơ trình duyệt chính."""
    v = cdp_alive(port)
    if v:
        print(f'Cổng {port} đã có trình duyệt đang chạy ({v.get("Browser")}). Dùng luôn cửa sổ đó.')
        return
    if name in PLAYWRIGHT:
        raise SystemExit(f'{name} dùng Playwright: không cần mở trước. Chạy thẳng eform_builder.py với --browser {name} --base-url ...')
    if not path:
        order = CHROMIUM if name == 'auto' else (name,)
        for n in order:
            path = find_browser(n)
            if path:
                name = n
                break
    if not path:
        raise SystemExit('Không tìm thấy trình duyệt nhân Chromium (Chrome/Edge/Cốc Cốc/Brave/Chromium). '
                         'Truyền đường dẫn bằng --browser-path, hoặc dùng --browser firefox/webkit (Playwright).')
    profile = profile or os.path.join(PROFILE_ROOT, f'{name if name != "auto" else "browser"}-profile')
    os.makedirs(profile, exist_ok=True)
    args = [path, f'--remote-debugging-port={port}', f'--user-data-dir={profile}',
            '--no-first-run', '--no-default-browser-check', url]
    kw = {'stdout': subprocess.DEVNULL, 'stderr': subprocess.DEVNULL}
    if os.name == 'nt':
        kw['creationflags'] = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kw['start_new_session'] = True
    subprocess.Popen(args, **kw)
    for _ in range(40):
        v = cdp_alive(port)
        if v:
            print(f'Đã mở {name}: {v.get("Browser")} | cổng {port} | hồ sơ {profile}')
            print('Hãy ĐĂNG NHẬP trong cửa sổ vừa mở, vào Quản lý Eform → Danh sách Eform, rồi chạy eform_builder.py.')
            return
        time.sleep(0.5)
    raise SystemExit(f'Đã chạy {path} nhưng cổng {port} không phản hồi. Đóng hết cửa sổ của trình duyệt này rồi thử lại.')


class CdpDriver:
    """Gắn vào trình duyệt nhân Chromium đang mở với --remote-debugging-port."""

    def __init__(self, port=9334, base_url=None, **_):
        if not cdp_alive(port):
            raise SystemExit(f'Không có trình duyệt nào mở cổng {port}. Chạy trước: python scripts/browser.py open --url https://<domain>/authenticate')
        tabs = [t for t in json.load(urllib.request.urlopen(f'http://127.0.0.1:{port}/json')) if t.get('type') == 'page']
        if base_url:
            host = urlparse(base_url).netloc
            tabs = [t for t in tabs if urlparse(t['url']).netloc == host]
        else:
            tabs = [t for t in tabs if any(p in t['url'] for p in EFORM_PATHS)]
        if not tabs:
            raise SystemExit('Không tìm thấy tab hệ thống Eform. Hãy đăng nhập và mở trang Danh sách Eform (…/list-eform), '
                             'hoặc truyền --base-url https://<domain>.')
        u = urlparse(tabs[0]['url'])
        self.base = f'{u.scheme}://{u.netloc}'
        self.ws = WS(tabs[0]['webSocketDebuggerUrl'])
        self.ws.call('Emulation.setFocusEmulationEnabled', enabled=True)

    def set_viewport(self, w, h):
        self.ws.call('Emulation.setDeviceMetricsOverride', width=w, height=h, deviceScaleFactor=1, mobile=False)

    def eval(self, js):
        return ev(self.ws, js)

    def click_at(self, x, y):
        for t in ('mouseMoved', 'mousePressed', 'mouseReleased'):
            self.ws.call('Input.dispatchMouseEvent', type=t, x=x, y=y, button='left', clickCount=1)

    def insert_text(self, text):
        self.ws.call('Input.insertText', text=str(text))

    def press(self, key):
        codes = {'Enter': 13, 'Escape': 27, 'Tab': 9}
        for t in ('keyDown', 'keyUp'):
            self.ws.call('Input.dispatchKeyEvent', type=t, key=key, code=key, windowsVirtualKeyCode=codes.get(key, 0))

    def goto(self, url):
        self.ws.call('Page.navigate', url=url)

    def close(self):
        pass                                   # trình duyệt là của người dùng: không đóng


class PlaywrightDriver:
    """Firefox / WebKit qua Playwright. Tự mở cửa sổ (hồ sơ riêng), chờ người dùng đăng nhập."""

    def __init__(self, browser='firefox', base_url=None, profile=None, login_timeout=600, **_):
        if not base_url:
            raise SystemExit(f'--browser {browser} cần --base-url https://<domain-don-vi>')
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            raise SystemExit('Chưa cài Playwright. Chạy: pip install playwright  rồi  playwright install firefox webkit')
        self.base = base_url.rstrip('/')
        self._pw = sync_playwright().start()
        profile = profile or os.path.join(PROFILE_ROOT, f'{browser}-profile')
        os.makedirs(profile, exist_ok=True)
        self.ctx = getattr(self._pw, browser).launch_persistent_context(
            profile, headless=False, bypass_csp=True, viewport={'width': 1440, 'height': 900})
        self.page = self.ctx.pages[0] if self.ctx.pages else self.ctx.new_page()
        if not any(p in self.page.url for p in EFORM_PATHS):
            self.page.goto(self.base + '/authenticate')
        print(f'Đã mở {browser}. Hãy ĐĂNG NHẬP trong cửa sổ đó và mở Quản lý Eform → Danh sách Eform. '
              f'Script chờ tối đa {login_timeout // 60} phút…', flush=True)
        t0 = time.time()
        while time.time() - t0 < login_timeout:
            for pg in self.ctx.pages:
                if urlparse(pg.url).netloc == urlparse(self.base).netloc and '/list-eform' in pg.url:
                    self.page = pg
                    print('Đã thấy trang Danh sách Eform, bắt đầu.')
                    pg.wait_for_timeout(2000)
                    return
            self.ctx.pages[0].wait_for_timeout(1000)   # không dùng time.sleep: Playwright chỉ cập nhật url khi được gọi
        self.close()
        raise SystemExit('Hết thời gian chờ đăng nhập.')

    def set_viewport(self, w, h):
        self.page.set_viewport_size({'width': w, 'height': h})

    def eval(self, js):
        try:                                   # eval gián tiếp = chạy ở phạm vi toàn cục như CDP Runtime.evaluate
            return self.page.evaluate('(code) => (0, eval)(code)', js)
        except Exception as e:
            return 'JSERROR: ' + str(e)[:800]

    def click_at(self, x, y):
        self.page.mouse.click(x, y)

    def insert_text(self, text):
        self.page.keyboard.insert_text(str(text))

    def press(self, key):
        self.page.keyboard.press(key)

    def goto(self, url):
        self.page.goto(url, wait_until='domcontentloaded')

    def close(self):
        try:
            self.ctx.close()
        finally:
            self._pw.stop()


def make_driver(browser='cdp', port=9334, base_url=None, profile=None):
    """browser: cdp | chrome | edge | coccoc | brave | chromium (đều gắn qua CDP) | firefox | webkit (Playwright)."""
    if browser in PLAYWRIGHT:
        return PlaywrightDriver(browser, base_url=base_url, profile=profile)
    return CdpDriver(port, base_url)


def main():
    utf8_console()
    ap = argparse.ArgumentParser(description='Tìm và mở trình duyệt có cổng điều khiển cho eform_builder.py')
    ap.add_argument('cmd', choices=['list', 'open'])
    ap.add_argument('--browser', default='auto', choices=('auto',) + CHROMIUM + PLAYWRIGHT)
    ap.add_argument('--browser-path', default=None, help='đường dẫn file chạy của trình duyệt nhân Chromium cài ở chỗ khác')
    ap.add_argument('--url', default='about:blank', help='vd https://<domain-don-vi>/authenticate')
    ap.add_argument('--port', type=int, default=9334)
    ap.add_argument('--profile', default=None, help=f'thư mục hồ sơ riêng (mặc định {PROFILE_ROOT}/<trình duyệt>-profile)')
    a = ap.parse_args()
    if a.cmd == 'list':
        for n, p in detect().items():
            print(f'{n:9s} {p or "-"}')
        try:
            import playwright  # noqa: F401
            print('firefox / webkit: có Playwright')
        except ImportError:
            print('firefox / webkit: chưa cài Playwright (pip install playwright; playwright install firefox webkit)')
        return
    open_browser(a.browser, a.url, a.port, a.browser_path, a.profile)


if __name__ == '__main__':
    main()
