# -*- coding: utf-8 -*-
"""用 ctypes 直接操作 Win32 窗口：激活、取窗口矩形、鼠标点击、键盘输入。
仅依赖 Python 标准库。"""
import ctypes, ctypes.wintypes as wt, time, sys

u32 = ctypes.WinDLL("user32", use_last_error=True)
u32.SetProcessDPIAware()

SW_RESTORE = 9
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010


class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]


def find_window(title_part):
    res = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)
    def cb(hwnd, _):
        n = u32.GetWindowTextLengthW(hwnd)
        if n:
            buf = ctypes.create_unicode_buffer(n + 1)
            u32.GetWindowTextW(hwnd, buf, n + 1)
            if title_part.lower() in buf.value.lower():
                r = RECT()
                u32.GetWindowRect(hwnd, ctypes.byref(r))
                res.append({"hwnd": hwnd, "title": buf.value,
                            "rect": (r.left, r.top, r.right, r.bottom)})
        return True

    u32.EnumWindows(cb, 0)
    return res


def activate(hwnd):
    u32.ShowWindow(hwnd, SW_RESTORE)
    u32.SetForegroundWindow(hwnd)
    time.sleep(0.35)


def rect_of(hwnd):
    r = RECT()
    u32.GetWindowRect(hwnd, ctypes.byref(r))
    return (r.left, r.top, r.right, r.bottom)


def click(x, y, double=False, right=False):
    u32.SetCursorPos(int(x), int(y))
    time.sleep(0.12)
    down = MOUSEEVENTF_RIGHTDOWN if right else MOUSEEVENTF_LEFTDOWN
    up = MOUSEEVENTF_RIGHTUP if right else MOUSEEVENTF_LEFTUP
    u32.mouse_event(down, 0, 0, 0, 0)
    u32.mouse_event(up, 0, 0, 0, 0)
    if double:
        time.sleep(0.08)
        u32.mouse_event(down, 0, 0, 0, 0)
        u32.mouse_event(up, 0, 0, 0, 0)
    time.sleep(0.6)


if __name__ == "__main__":
    for w in find_window("POCIB" if len(sys.argv) < 2 else sys.argv[1]):
        print(w)


KEYEVENTF_KEYUP = 0x0002


def key(vk, up=True):
    u32.keybd_event(vk, 0, 0, 0)
    time.sleep(0.05)
    if up:
        u32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)
    time.sleep(0.15)


VK = {"enter": 0x0D, "esc": 0x1B, "tab": 0x09, "space": 0x20,
      "left": 0x25, "up": 0x26, "right": 0x27, "down": 0x28}
