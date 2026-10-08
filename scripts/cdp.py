# -*- coding: utf-8 -*-
"""CDP client tối giản (stdlib) điều khiển Chrome mở với --remote-debugging-port.
Lệnh: eval <js> | runjs <file> | click x y | clickjs <expr> | type <text> | key <Key> | hover x y | nav <url> [wait] | shot <file> | viewport | daemon
Chạy 'daemon' để giữ 1 kết nối WebSocket; các lệnh khác tự gửi qua daemon (TCP 127.0.0.1:CDP_DPORT) nếu daemon đang chạy.
"""
import sys, json, socket, base64, os, struct, urllib.request, time

PORT = int(os.environ.get('CDP_PORT', 9334))
DPORT = int(os.environ.get('CDP_DPORT', 9444))


def page_ws(match):
    tabs = json.load(urllib.request.urlopen(f'http://127.0.0.1:{PORT}/json'))
    tabs = [t for t in tabs if t.get('type') == 'page' and t['url'].startswith('http') and match in t['url']]
    return tabs[0]['webSocketDebuggerUrl']


class WS:
    def __init__(self, url):
        hp, path = url[len('ws://'):].split('/', 1)
        h, p = hp.split(':')
        self.s = socket.create_connection((h, int(p)))
        key = base64.b64encode(os.urandom(16)).decode()
        self.s.sendall((f'GET /{path} HTTP/1.1\r\nHost: {hp}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n'
                        f'Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n').encode())
        buf = b''
        while b'\r\n\r\n' not in buf:
            buf += self.s.recv(4096)
        self.buf = buf.split(b'\r\n\r\n', 1)[1]
        self.i = 0

    def _read(self, n):
        while len(self.buf) < n:
            ch = self.s.recv(1 << 20)
            if not ch:
                raise ConnectionError('closed')
            self.buf += ch
        out, self.buf = self.buf[:n], self.buf[n:]
        return out

    def send(self, obj):
        data = json.dumps(obj).encode()
        hdr = bytearray([0x81]); n = len(data)
        if n < 126: hdr.append(0x80 | n)
        elif n < 65536: hdr.append(0x80 | 126); hdr += struct.pack('>H', n)
        else: hdr.append(0x80 | 127); hdr += struct.pack('>Q', n)
        mask = os.urandom(4)
        self.s.sendall(bytes(hdr) + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(data)))

    def recv(self):
        msg = b''
        while True:
            b1, b2 = self._read(2)
            n = b2 & 0x7f
            if n == 126: n = struct.unpack('>H', self._read(2))[0]
            elif n == 127: n = struct.unpack('>Q', self._read(8))[0]
            msg += self._read(n)
            if b1 & 0x80:
                return json.loads(msg)

    def call(self, method, **params):
        self.i += 1
        self.send({'id': self.i, 'method': method, 'params': params})
        while True:
            r = self.recv()
            if r.get('id') == self.i:
                if 'error' in r: raise RuntimeError(r['error'])
                return r.get('result', {})


def ev(ws, js):
    r = ws.call('Runtime.evaluate', expression=js, returnByValue=True, awaitPromise=True)
    if 'exceptionDetails' in r:
        return 'JSERROR: ' + str(r['exceptionDetails'].get('exception', {}).get('description', r['exceptionDetails']))[:800]
    return r.get('result', {}).get('value')


def mouse(ws, x, y, kind='click'):
    if kind == 'hover':
        ws.call('Input.dispatchMouseEvent', type='mouseMoved', x=x, y=y); return
    for t in ('mouseMoved', 'mousePressed', 'mouseReleased'):
        ws.call('Input.dispatchMouseEvent', type=t, x=x, y=y, button='left', clickCount=1)


_STATE = {}
def handle(ws, cmd, args):
    W, H = int(os.environ.get('CDP_W', 1920)), int(os.environ.get('CDP_H', 1080))
    DSF = float(os.environ.get('CDP_DSF', 1))
    if _STATE.get('m') != (W, H, DSF):
        ws.call('Emulation.setDeviceMetricsOverride', width=W, height=H, deviceScaleFactor=DSF, mobile=False)
        ws.call('Emulation.setFocusEmulationEnabled', enabled=True)
        _STATE['m'] = (W, H, DSF); time.sleep(0.3)
    if cmd == 'eval':
        print(json.dumps(ev(ws, args[0]), ensure_ascii=False)[:30000])
    elif cmd == 'runjs':
        print(json.dumps(ev(ws, open(args[0], encoding='utf-8').read()), ensure_ascii=False)[:30000])
    elif cmd == 'click':
        mouse(ws, float(args[0]), float(args[1])); print('clicked')
    elif cmd == 'hover':
        mouse(ws, float(args[0]), float(args[1]), 'hover'); print('hover')
    elif cmd == 'clickjs':
        r = ev(ws, '(()=>{const e=(%s);if(!e)return null;e.scrollIntoView({block:"nearest"});const r=e.getBoundingClientRect();return [r.x+r.width/2,r.y+r.height/2]})()' % args[0])
        if not isinstance(r, list): print('NOTFOUND', r); return
        mouse(ws, r[0], r[1]); print('clicked', [round(v) for v in r])
    elif cmd == 'type':
        ws.call('Input.insertText', text=args[0]); print('typed')
    elif cmd == 'key':
        codes = {'Enter': 13, 'Escape': 27, 'Tab': 9, 'Backspace': 8, 'ArrowDown': 40, 'ArrowUp': 38}
        for t in ('keyDown', 'keyUp'):
            ws.call('Input.dispatchKeyEvent', type=t, key=args[0], code=args[0], windowsVirtualKeyCode=codes.get(args[0], 0))
        print('key', args[0])
    elif cmd == 'nav':
        ws.call('Page.navigate', url=args[0]); time.sleep(float(args[1]) if len(args) > 1 else 3); print('ok')
    elif cmd == 'shot':
        r = ws.call('Page.captureScreenshot', format='png')
        open(args[0], 'wb').write(base64.b64decode(r['data'])); print('saved', args[0])
    elif cmd == 'viewport':
        print('ok')
    else:
        print('unknown', cmd)


def daemon():
    import io, contextlib, traceback
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1); srv.bind(('127.0.0.1', DPORT)); srv.listen(4)
    ws = None; cur = None
    print('daemon ready', flush=True)
    while True:
        c, _ = srv.accept()
        f = c.makefile('rb'); req = json.loads(f.readline()); out = io.StringIO()
        try:
            os.environ.update(req['env']); os.chdir(req['cwd'])
            match = req['env'].get('CDP_MATCH', '/list-eform')
            if ws is None or cur != match:
                ws = WS(page_ws(match)); cur = match; _STATE.clear()
            with contextlib.redirect_stdout(out):
                handle(ws, req['argv'][0], req['argv'][1:])
        except Exception:
            out.write(traceback.format_exc()); ws = None
        c.sendall(out.getvalue().encode()); f.close(); c.shutdown(socket.SHUT_RDWR); c.close()


def main():
    if sys.argv[1] == 'daemon':
        return daemon()
    try:
        c = socket.create_connection(('127.0.0.1', DPORT), timeout=2); c.settimeout(None)
    except OSError:
        c = None
    if c and not os.environ.get('CDP_DIRECT'):
        env = {k: v for k, v in os.environ.items() if k.startswith('CDP_')}
        c.sendall(json.dumps({'argv': sys.argv[1:], 'env': env, 'cwd': os.getcwd()}).encode() + b'\n')
        buf = b''
        while True:
            ch = c.recv(65536)
            if not ch: break
            buf += ch
        sys.stdout.write(buf.decode()); return
    ws = WS(page_ws(os.environ.get('CDP_MATCH', '/list-eform')))
    handle(ws, sys.argv[1], sys.argv[2:])


if __name__ == '__main__':
    main()
