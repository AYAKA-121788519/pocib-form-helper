# -*- coding: utf-8 -*-
"""POCIB 识图服务 —— 在本机开个小接口，让填单助手网页自己去截窗口取数。

启动后不用再复制粘贴、不用生成 json 文件：网页里点「📷 截图识别」就直接出结果。

  python serve.py            启动服务（端口从 17861 起，被占用就往后找）
  python serve.py --open     启动并顺便打开填单助手网页
  python serve.py --port 17861

接口（都只对本机 127.0.0.1 开放）：
  /ping      服务是否在跑
  /windows   可识别的窗口列表
  /capture   截取 → 识别 → 解析，直接返回字段
  /lastshot  上一次截图的预览图
"""
import argparse
import json
import os
import sys
import threading
import time
import traceback
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ocrlib as O
import extract as EX

APP_SIG = "pocib-ocr"
PORT_BASE = 17861
PORT_TRIES = 20

STATE = {"shot": None, "shot_time": 0, "port": 0, "captures": 0}
LOCK = threading.Lock()


def find_app_html():
    """找到填单助手网页：发布包和开发目录两种放法都认。"""
    cands = [
        os.path.join(HERE, "..", "POCIB填单助手.html"),
        os.path.join(HERE, "..", "index.html"),
        os.path.join(HERE, "..", "..", "app", "index.html"),
        os.path.join(HERE, "..", "..", "dist", "POCIB填单助手.html"),
    ]
    for p in cands:
        p = os.path.abspath(p)
        if os.path.isfile(p):
            return p
    return None


def engine_name():
    if STATE.get("engine") in ("rapid", "win"):
        return STATE["engine"]
    return "rapid" if O.rapid_available() else "win"


class Api(BaseHTTPRequestHandler):
    server_version = "PocibOcr/2.0"
    protocol_version = "HTTP/1.1"

    # ---- 小工具
    def log_message(self, fmt, *args):
        pass

    def _send(self, body, ctype="application/json; charset=utf-8", code=200):
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _json(self, obj, code=200):
        self._send(json.dumps(obj, ensure_ascii=False), code=code)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Max-Age", "86400")
        self.send_header("Content-Length", "0")
        self.end_headers()

    # ---- 代取网页：浏览器从 file:// 打开时读不了别的站，让本机服务去抓
    def _fetch(self, q):
        """GET /fetch?url=<encoded>
        只做「取回 HTML」，解析交给网页自己（规则改了不用重启服务）。
        学校 POCIB 服务器多在 192.168.x.x 内网，这里不限制目标地址。"""
        import urllib.request, ssl
        url = (q.get("url") or [""])[0].strip()
        if not url.lower().startswith(("http://", "https://")):
            return self._json({"ok": False, "error": "只支持 http:// 或 https:// 开头的网址"}, 400)
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
        })
        try:
            with urllib.request.urlopen(req, timeout=30, context=ctx) as r:
                raw = r.read()
                enc = (r.headers.get_content_charset() or "").lower()
                final = r.geturl()
        except Exception as e:
            return self._json({"ok": False, "error": "抓取失败：%s" % e}, 200)
        text = ""
        for e in [enc, "utf-8", "gb18030", "latin-1"]:
            if not e:
                continue
            try:
                text = raw.decode(e)
                break
            except Exception:
                continue
        if not text:
            text = raw.decode("utf-8", "replace")
        return self._json({"ok": True, "url": final, "bytes": len(raw),
                           "charset": enc or "utf-8", "html": text[:1200000]})

    def _tariff(self, q):
        """GET /tariff?base=<服务器>&q=<HS或品名>
        POCIB 税率查询是 ASP.NET WebForms：先取表单页里的 __VIEWSTATE，再 POST 查询，
        这一步浏览器跨域做不了，放到本机服务里做。返回结果页 HTML 给前端解析。"""
        import re, urllib.request, urllib.parse, ssl
        base = ((q.get("base") or [""])[0] or "http://192.168.150.135:5015").rstrip("/")
        kw = (q.get("q") or [""])[0].strip()
        if not kw:
            return self._json({"ok": False, "error": "缺少查询关键词"}, 400)
        form = base + "/institutions/company/14/SearchHSCodeForm.aspx"
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        hdr = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
               "Referer": form, "Accept": "text/html,application/xhtml+xml"}

        def grab(url, data=None):
            req = urllib.request.Request(url, data=data, headers=hdr)
            with urllib.request.urlopen(req, timeout=30, context=ctx) as r:
                raw = r.read()
                enc = (r.headers.get_content_charset() or "utf-8")
            try:
                return raw.decode(enc)
            except Exception:
                return raw.decode("utf-8", "replace")

        try:
            page = grab(form)
        except Exception as e:
            return self._json({"ok": False, "error": "连不上 %s：%s" % (base, e)})
        def hid(k):
            m = re.search(r'(?:name|id)="%s"[^>]*value="([^"]*)"' % k, page)
            return m.group(1) if m else ""
        is_code = kw.isdigit()
        payload = {
            "__VIEWSTATE": hid("__VIEWSTATE"),
            "__VIEWSTATEGENERATOR": hid("__VIEWSTATEGENERATOR"),
            "__EVENTVALIDATION": hid("__EVENTVALIDATION"),
            "curPageNo": "1", "totalCount": "0", "perPageCount": "20",
            "hscode": kw if is_code else "", "goodsname": "" if is_code else kw,
            "bSearch": "true",
        }
        try:
            html = grab(form, urllib.parse.urlencode(payload).encode())
        except Exception as e:
            return self._json({"ok": False, "error": "查询失败：%s" % e})
        return self._json({"ok": True, "base": base, "q": kw, "bytes": len(html), "html": html})

    # ---- 路由
    def do_GET(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)
        path = u.path.rstrip("/") or "/"
        try:
            if path == "/ping":
                return self._json({"ok": True, "app": APP_SIG, "v": 2,
                                   "port": STATE["port"], "engine": engine_name(),
                                   "captures": STATE["captures"]})
            if path == "/windows":
                return self._json({"ok": True, "wins": self._wins()})
            if path == "/capture":
                return self._capture(q)
            if path in ("/lastshot", "/lastshot.png"):
                return self._lastshot()
            if path == "/fetch":
                return self._fetch(q)
            if path == "/tariff":
                return self._tariff(q)
            if path == "/":
                return self._json({"ok": True, "app": APP_SIG,
                                   "hint": "在本机识别服务里：/ping /windows /capture /lastshot"})
            return self._json({"ok": False, "error": "没有这个接口：%s" % path}, 404)
        except BrokenPipeError:
            pass
        except Exception as e:
            traceback.print_exc()
            return self._json({"ok": False, "error": str(e) or e.__class__.__name__})

    # ---- 具体实现
    def _wins(self):
        wins = EX.candidate_windows()
        scored = [w for w in wins if w["score"] > 0]
        use = scored if scored else wins
        out = []
        for w in use[:8]:
            item = {k: w[k] for k in ("hwnd", "title", "w", "h", "kind")}
            out.append(item)
        # candidate_windows 已按「最近用过」排序（z 序），第一个就是默认目标
        if out:
            out[0]["recent"] = True
        return out

    def _capture(self, q):
        def one(k, default=""):
            v = q.get(k) or [default]
            return v[0]

        hwnd = one("hwnd")
        hwnd = int(hwnd) if hwnd.isdigit() else 0
        title = one("title")
        kind = one("kind", "auto")
        if kind not in ("auto", "company", "goods"):
            kind = "auto"
        engine = one("engine", "") or (STATE.get("engine") or "auto")
        if not hwnd and kind != "auto":
            # 从「公司」入口进来就优先找公司页，从「商品」进来就优先找商品页
            for w in EX.candidate_windows():
                if w["kind"] == kind:
                    hwnd = w["hwnd"]
                    break

        t0 = time.time()
        with LOCK:
            try:
                r = EX.pipeline(hwnd=hwnd or None, title=title or None, kind=kind,
                                engine=engine, interactive=False, want_png=True)
            except RuntimeError as e:
                msg = str(e)
                hint = ""
                if "没找到 POCIB 窗口" in msg:
                    hint = "把 POCIB 客户端窗口打开、别最小化，再点一次"
                return self._json({"ok": False, "error": msg, "hint": hint,
                                   "wins": self._wins()})
            if r["png"]:
                STATE["shot"] = r["png"]
                STATE["shot_time"] = time.time()
            STATE["captures"] += 1
            payload = dict(r["payload"])
            payload["ok"] = True
            payload["elapse"] = round(time.time() - t0, 2)
            payload["shot"] = "/lastshot.png?t=%d" % int(STATE["shot_time"] * 1000)
            payload["log"] = r["log"]
            return self._json(payload)

    def _lastshot(self):
        png = STATE["shot"]
        if not png:
            return self._send("", "image/png", 404)
        return self._send(png, "image/png")

    def do_POST(self):
        # 前端一律用 GET（file:// 下 POST 会触发预检被浏览器拦住），这里只作兜底
        u = urlparse(self.path)
        if u.path.rstrip("/") == "/capture":
            return self._capture(parse_qs(u.query))
        return self._json({"ok": False, "error": "请用 GET"}, 405)


def probe(port, timeout=0.35):
    """看看这个端口上是不是我们自己的服务。"""
    try:
        import urllib.request
        with urllib.request.urlopen("http://127.0.0.1:%d/ping" % port, timeout=timeout) as r:
            d = json.loads(r.read().decode("utf-8"))
            return d if d.get("app") == APP_SIG else None
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--port", type=int, default=0)
    ap.add_argument("--open", action="store_true", help="打开填单助手网页")
    ap.add_argument("--no-open", action="store_true")
    ap.add_argument("--engine", choices=["auto", "rapid", "win"], default="auto",
                    help="auto=有 PP-OCR 就用，否则退回系统自带")
    a = ap.parse_args()
    STATE["engine"] = a.engine

    httpd = None
    ports = [a.port] if a.port else list(range(PORT_BASE, PORT_BASE + PORT_TRIES))
    for p in ports:
        if not a.port:
            alive = probe(p)
            if alive:
                print("服务已经在运行（端口 %d），不用重复启动。" % p)
                if not a.no_open:
                    open_app()
                return
        try:
            httpd = ThreadingHTTPServer(("127.0.0.1", p), Api)
            STATE["port"] = p
            break
        except OSError:
            continue
    if httpd is None:
        print("端口都被占用了，试试 python serve.py --port 18861")
        return
    httpd.daemon_threads = True

    print("=" * 52)
    print(" POCIB 识图服务已启动   127.0.0.1:%d" % STATE["port"])
    print("=" * 52)
    print(" 识别引擎：%s" % ("PP-OCR 中文模型" if engine_name() == "rapid"
                            else "系统自带 OCR（中文精度较低）"))
    print("")
    print(" 打开填单助手网页，点「📷 截图识别」，会自动截取 POCIB 窗口。")
    print(" 要停服务，直接关掉这个黑窗口。")
    print("")

    def warm():
        if engine_name() == "rapid" and O.rapid_available():
            t = time.time()
            try:
                O._rapid_engine()
                print(" 模型已就绪（预热 %.1fs），第一次点也会很快。" % (time.time() - t))
            except Exception:
                pass
    threading.Thread(target=warm, daemon=True).start()

    if not a.no_open and a.open:
        open_app()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止。")


def open_app():
    path = find_app_html()
    if not path:
        print("没找到填单助手网页（POCIB填单助手.html），请手动打开它。")
        return
    url = "file:///" + path.replace("\\", "/")
    print(" 打开网页：%s" % path)
    try:
        webbrowser.open(url)
    except Exception as e:
        print(" 打开失败：%s" % e)


if __name__ == "__main__":
    main()
