# -*- coding: utf-8 -*-
"""POCIB 识图取数 · 底层库（纯标准库 + Windows 自带 OCR，无需 pip 安装任何东西）

能力：
  Img            图像对象（RGB，每行一个 bytes），支持 crop / scale / save
  capture(...)   截取 POCIB 窗口（PrintWindow，后台渲染，不抢焦点）或屏幕区域
  read_png(...)  读入用户自己截的图（Win+Shift+S 保存的 PNG）
  ocr(...)       调 Windows.Media.Ocr 批量识别，返回带坐标的行/词
"""
import ctypes
import ctypes.wintypes as wt
import json
import os
import struct
import subprocess
import sys
import tempfile
import time
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
PS1 = os.path.join(HERE, "ocr.ps1")

u32 = ctypes.WinDLL("user32", use_last_error=True)
g32 = ctypes.WinDLL("gdi32", use_last_error=True)

try:
    u32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))  # PER_MONITOR_AWARE_V2
except Exception:
    pass

PW_RENDERFULLCONTENT = 0x00000002
SRCCOPY = 0x00CC0020
DIB_RGB_COLORS = 0


# ---------------------------------------------------------------- 窗口 / 截图
class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [("biSize", wt.DWORD), ("biWidth", ctypes.c_long),
                ("biHeight", ctypes.c_long), ("biPlanes", wt.WORD),
                ("biBitCount", wt.WORD), ("biCompression", wt.DWORD),
                ("biSizeImage", wt.DWORD), ("biXPelsPerMeter", ctypes.c_long),
                ("biYPelsPerMeter", ctypes.c_long), ("biClrUsed", wt.DWORD),
                ("biClrImportant", wt.DWORD)]


class BITMAPINFO(ctypes.Structure):
    _fields_ = [("bmiHeader", BITMAPINFOHEADER), ("bmiColors", wt.DWORD * 3)]


def list_windows():
    out = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)
    def cb(hwnd, _):
        if not u32.IsWindowVisible(hwnd):
            return True
        n = u32.GetWindowTextLengthW(hwnd)
        if n:
            buf = ctypes.create_unicode_buffer(n + 1)
            u32.GetWindowTextW(hwnd, buf, n + 1)
            r = RECT()
            u32.GetWindowRect(hwnd, ctypes.byref(r))
            out.append({"hwnd": hwnd, "title": buf.value,
                        "rect": (r.left, r.top, r.right, r.bottom)})
        return True

    u32.EnumWindows(cb, 0)
    return out


def find_window(title_part):
    return [w for w in list_windows() if title_part.lower() in w["title"].lower()]


# ---------------------------------------------------------------- 图像对象
class Img:
    def __init__(self, w, h, rows):
        self.w = w
        self.h = h
        self.rows = rows  # list[bytes]，每行 w*3 字节 RGB

    def crop(self, x0, y0, x1, y1):
        x0 = max(0, min(self.w, int(x0)))
        x1 = max(x0 + 1, min(self.w, int(x1)))
        y0 = max(0, min(self.h, int(y0)))
        y1 = max(y0 + 1, min(self.h, int(y1)))
        rows = [self.rows[y][x0 * 3:x1 * 3] for y in range(y0, y1)]
        return Img(x1 - x0, y1 - y0, rows)

    def pad(self, l, t, r, b, color=(255, 255, 255)):
        fill = bytes(color) * (self.w + l + r)
        rows = [fill] * t + [bytes(color) * l + row + bytes(color) * r for row in self.rows] + [fill] * b
        return Img(self.w + l + r, self.h + t + b, rows)

    def scale(self, f):
        """双线性放大，f 可为小数。"""
        if abs(f - 1) < 1e-6:
            return self
        nw, nh = int(self.w * f + 0.5), int(self.h * f + 0.5)
        src, sw, sh = self.rows, self.w, self.h
        rows = []
        for oy in range(nh):
            sy = (oy + 0.5) / f - 0.5
            y0 = int(sy // 1)
            fy = sy - y0
            y0 = min(max(y0, 0), sh - 1)
            y1 = min(y0 + 1, sh - 1)
            r0, r1 = src[y0], src[y1]
            out = bytearray(nw * 3)
            for ox in range(nw):
                sx = (ox + 0.5) / f - 0.5
                x0 = int(sx // 1)
                fx = sx - x0
                x0 = min(max(x0, 0), sw - 1)
                x1 = min(x0 + 1, sw - 1)
                b0, b1 = x0 * 3, x1 * 3
                for c in range(3):
                    v = (r0[b0 + c] * (1 - fx) + r0[b1 + c] * fx) * (1 - fy) + \
                        (r1[b0 + c] * (1 - fx) + r1[b1 + c] * fx) * fy
                    out[ox * 3 + c] = 0 if v < 0 else (255 if v > 255 else int(v))
            rows.append(bytes(out))
        return Img(nw, nh, rows)

    def save(self, path):
        raw = bytearray()
        for row in self.rows:
            raw.append(0)
            raw += row

        def chunk(tag, data):
            return (struct.pack(">I", len(data)) + tag + data +
                    struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

        data = (b"\x89PNG\r\n\x1a\n"
                + chunk(b"IHDR", struct.pack(">IIBBBBB", self.w, self.h, 8, 2, 0, 0, 0))
                + chunk(b"IDAT", zlib.compress(bytes(raw), 6))
                + chunk(b"IEND", b""))
        with open(path, "wb") as f:
            f.write(data)
        return path


def _from_dib(hdc_mem, hbmp, w, h):
    bi = BITMAPINFO()
    bi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    bi.bmiHeader.biWidth = w
    bi.bmiHeader.biHeight = -h
    bi.bmiHeader.biPlanes = 1
    bi.bmiHeader.biBitCount = 32
    buf = ctypes.create_string_buffer(w * h * 4)
    g32.GetDIBits(hdc_mem, hbmp, 0, h, buf, ctypes.byref(bi), DIB_RGB_COLORS)
    mv = memoryview(buf)
    rows = []
    for y in range(h):
        line = mv[y * w * 4:(y + 1) * w * 4]
        out = bytearray(w * 3)
        out[0::3] = line[2::4]
        out[1::3] = line[1::4]
        out[2::3] = line[0::4]
        rows.append(bytes(out))
    return rows


def _blank(img):
    for row in img.rows[::13]:
        if row.count(0) < len(row):
            return False
    return True


def capture_window(hwnd):
    r = RECT()
    u32.GetWindowRect(hwnd, ctypes.byref(r))
    w, h = r.right - r.left, r.bottom - r.top
    if w <= 0 or h <= 0:
        raise RuntimeError("窗口尺寸异常，可能已最小化到托盘，请先把窗口打开")

    # 1) PrintWindow：后台渲染，不动用户鼠标键盘，被遮住也能截
    hdc = u32.GetWindowDC(hwnd)
    mem = g32.CreateCompatibleDC(hdc)
    hbmp = g32.CreateCompatibleBitmap(hdc, w, h)
    old = g32.SelectObject(mem, hbmp)
    ok = u32.PrintWindow(hwnd, mem, PW_RENDERFULLCONTENT)
    img = None
    if ok:
        img = Img(w, h, _from_dib(mem, hbmp, w, h))
    g32.SelectObject(mem, old)
    g32.DeleteObject(hbmp)
    g32.DeleteDC(mem)
    u32.ReleaseDC(hwnd, hdc)
    if img and not _blank(img):
        return img

    # 2) 兜底：屏幕取像（窗口必须可见且未被遮挡）
    hdc_scr = u32.GetDC(0)
    mem = g32.CreateCompatibleDC(hdc_scr)
    hbmp = g32.CreateCompatibleBitmap(hdc_scr, w, h)
    old = g32.SelectObject(mem, hbmp)
    g32.BitBlt(mem, 0, 0, w, h, hdc_scr, r.left, r.top, SRCCOPY)
    img = Img(w, h, _from_dib(mem, hbmp, w, h))
    g32.SelectObject(mem, old)
    g32.DeleteObject(hbmp)
    g32.DeleteDC(mem)
    u32.ReleaseDC(0, hdc_scr)
    return img


def capture_screen(rect=None):
    if rect:
        x, y, w, h = rect
    else:
        x, y, w, h = 0, 0, u32.GetSystemMetrics(0), u32.GetSystemMetrics(1)
    hdc_scr = u32.GetDC(0)
    mem = g32.CreateCompatibleDC(hdc_scr)
    hbmp = g32.CreateCompatibleBitmap(hdc_scr, w, h)
    old = g32.SelectObject(mem, hbmp)
    g32.BitBlt(mem, 0, 0, w, h, hdc_scr, x, y, SRCCOPY)
    img = Img(w, h, _from_dib(mem, hbmp, w, h))
    g32.SelectObject(mem, old)
    g32.DeleteObject(hbmp)
    g32.DeleteDC(mem)
    u32.ReleaseDC(0, hdc_scr)
    return img


# ---------------------------------------------------------------- PNG 读取
def read_png(path):
    with open(path, "rb") as f:
        data = f.read()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise RuntimeError("不是 PNG 文件：%s（请另存为 PNG）" % path)
    pos = 8
    idat = bytearray()
    w = h = bd = ct = 0
    while pos < len(data):
        ln = struct.unpack(">I", data[pos:pos + 4])[0]
        tag = data[pos + 4:pos + 8]
        body = data[pos + 8:pos + 8 + ln]
        pos += 12 + ln
        if tag == b"IHDR":
            w, h, bd, ct, _, _, il = struct.unpack(">IIBBBBB", body)
            if bd != 8 or il != 0 or ct not in (0, 2, 4, 6):
                raise RuntimeError("暂不支持该 PNG 格式（位深%d 类型%d 隔行%d），请用 Win+Shift+S 重新截图"
                                   % (bd, ct, il))
        elif tag == b"IDAT":
            idat += body
        elif tag == b"IEND":
            break
    bpp = {0: 1, 2: 3, 4: 2, 6: 4}[ct]
    raw = zlib.decompress(bytes(idat))
    stride = w * bpp
    prev = bytearray(stride)
    rows = []
    p = 0
    for y in range(h):
        ft = raw[p]
        p += 1
        line = bytearray(raw[p:p + stride])
        p += stride
        if ft == 1:
            for i in range(bpp, stride):
                line[i] = (line[i] + line[i - bpp]) & 0xFF
        elif ft == 2:
            for i in range(stride):
                line[i] = (line[i] + prev[i]) & 0xFF
        elif ft == 3:
            for i in range(stride):
                a = line[i - bpp] if i >= bpp else 0
                line[i] = (line[i] + ((a + prev[i]) >> 1)) & 0xFF
        elif ft == 4:
            for i in range(stride):
                a = line[i - bpp] if i >= bpp else 0
                b = prev[i]
                c = prev[i - bpp] if i >= bpp else 0
                pa, pb, pc = abs(b - c), abs(a - c), abs(a + b - 2 * c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                line[i] = (line[i] + pr) & 0xFF
        prev = line
        if bpp == 3:
            rows.append(bytes(line))
        elif bpp == 4:
            out = bytearray(w * 3)
            out[0::3] = line[0::4]
            out[1::3] = line[1::4]
            out[2::3] = line[2::4]
            rows.append(bytes(out))
        elif bpp == 1:
            out = bytearray(w * 3)
            for i in range(w):
                v = line[i]
                out[i * 3] = out[i * 3 + 1] = out[i * 3 + 2] = v
            rows.append(bytes(out))
        else:  # gray+alpha
            out = bytearray(w * 3)
            out[0::3] = line[0::2]
            out[1::3] = line[0::2]
            out[2::3] = line[0::2]
            rows.append(bytes(out))
    return Img(w, h, rows)


# ---------------------------------------------------------------- OCR
def ocr(images, lang="zh-Hans-CN", keep=False):
    """images: [(id, path), ...] 或 [path, ...]。返回 {id: result}"""
    items = []
    for i, it in enumerate(images):
        if isinstance(it, (list, tuple)):
            _id, path = it
        else:
            _id, path = i, it
        items.append({"id": str(_id), "path": os.path.abspath(path), "lang": lang})

    tmpdir = tempfile.mkdtemp(prefix="pocib_ocr_")
    manifest = os.path.join(tmpdir, "m.json")
    out = os.path.join(tmpdir, "r.json")
    with open(manifest, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False)

    cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
           "-File", PS1, "-Manifest", manifest, "-Out", out]
    subprocess.run(cmd, check=False,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                   creationflags=0x08000000)  # CREATE_NO_WINDOW
    if not os.path.exists(out):
        raise RuntimeError("OCR 调用失败：没有产生结果文件。请确认系统 OCR 可用"
                           "（设置 → 时间和语言 → 语言 → 中文(简体) 的可选功能）")
    with open(out, "r", encoding="utf-8-sig") as f:
        data = json.load(f)
    res = {r.get("id"): r for r in data.get("results", [])}
    if not keep:
        for p in [manifest, out] + [it["path"] for it in items]:
            try:
                os.remove(p)
            except OSError:
                pass
        try:
            os.rmdir(tmpdir)
        except OSError:
            pass
    return res


def ocr_image(img, lang="zh-Hans-CN", tag="x"):
    tmpdir = tempfile.mkdtemp(prefix="pocib_c_")
    p = img.save(os.path.join(tmpdir, "%s.png" % tag))
    try:
        return ocr([(tag, p)], lang=lang).get(tag)
    finally:
        try:
            os.remove(p)
            os.rmdir(tmpdir)
        except OSError:
            pass


# ---------------------------------------------------------------- RapidOCR 主引擎
_RAPID = None


def rapid_available():
    try:
        import rapidocr_onnxruntime  # noqa: F401
        return True
    except Exception:
        return False


def _rapid_engine():
    global _RAPID
    if _RAPID is None:
        from rapidocr_onnxruntime import RapidOCR
        _RAPID = RapidOCR()
    return _RAPID


def _norm_rapid(raw, w, h):
    lines = []
    for item in raw or []:
        box, text, score = item[0], item[1], item[2]
        try:
            score = float(score)
        except Exception:
            score = 1.0
        xs = [p[0] for p in box]
        ys = [p[1] for p in box]
        x, y = min(xs), min(ys)
        lines.append({"text": text, "x": int(x), "y": int(y),
                      "w": int(max(xs) - x), "h": int(max(ys) - y),
                      "score": round(score, 3), "words": []})
    lines.sort(key=lambda l: (l["y"], l["x"]))
    return {"ok": True, "engine": "rapid", "width": w, "height": h, "lines": lines}


def ocr_rapid(img_or_path, w=None, h=None, scale=1.0, **kw):
    """用 RapidOCR（PP-OCR 中文模型）识别。img_or_path 可以是 Img 或文件路径。"""
    tmpdir = None
    target = img_or_path
    if isinstance(img_or_path, Img):
        if scale and abs(scale - 1) > 1e-6:
            target = img_or_path.scale(scale)
        tmpdir = tempfile.mkdtemp(prefix="pocib_r_")
        path = target.save(os.path.join(tmpdir, "r.png"))
        w, h = img_or_path.w, img_or_path.h
    else:
        path = img_or_path
    try:
        raw, _elapse = _rapid_engine()(path, **kw)
        if w is None:
            try:
                im = read_png(path)
                w, h = im.w, im.h
            except Exception:
                w = h = 0
        res = _norm_rapid(raw, w or 0, h or 0)
        if scale and abs(scale - 1) > 1e-6:
            for l in res["lines"]:
                l["x"] = int(l["x"] / scale)
                l["y"] = int(l["y"] / scale)
                l["w"] = int(l["w"] / scale)
                l["h"] = int(l["h"] / scale)
        return res
    finally:
        if tmpdir:
            try:
                os.remove(path)
                os.rmdir(tmpdir)
            except OSError:
                pass


def _iou(a, b):
    ax, ay, aw, ah = a["x"], a["y"], a["w"], a["h"]
    bx, by, bw, bh = b["x"], b["y"], b["w"], b["h"]
    x0, y0 = max(ax, bx), max(ay, by)
    x1, y1 = min(ax + aw, bx + bw), min(ay + ah, by + bh)
    if x1 <= x0 or y1 <= y0:
        return 0.0
    inter = (x1 - x0) * (y1 - y0)
    union = aw * ah + bw * bh - inter
    return inter / union if union > 0 else 0.0


def ocr_best(img):
    """双通道识别取并集：原图放宽阈值（找小字/浅色）+ 1.6 倍放大（找细节），
    再按位置去重，取文字更完整的那个。"""
    base = ocr_rapid(img, box_thresh=0.25, text_score=0.25)
    up = ocr_rapid(img, scale=1.6, box_thresh=0.3, text_score=0.35)

    out = list(base["lines"])
    for bl in up["lines"]:
        hit = None
        for i, al in enumerate(out):
            if _iou(al, bl) > 0.32 or (al["text"] == bl["text"] and abs(al["y"] - bl["y"]) < 6):
                hit = i
                break
        if hit is None:
            out.append(bl)
        else:
            al = out[hit]
            if len(bl["text"]) > len(al["text"]) + 1:
                out[hit] = bl
    out.sort(key=lambda l: (l["y"], l["x"]))
    return {"ok": True, "engine": "rapid-x2", "width": img.w, "height": img.h, "lines": out}

