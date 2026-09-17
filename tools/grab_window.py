"""抓取 SquareLine Studio (Unity) 窗口截图，保存为 PNG。

用法：python tools/grab_window.py <输出png> [等待秒数]
"""
import ctypes
import ctypes.wintypes as wt
import sys
import time

from PIL import ImageGrab


def window_box():
    u32 = ctypes.windll.user32
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    hwnd = u32.FindWindowW("UnityWndClass", None)
    if not hwnd:
        raise SystemExit("找不到 UnityWndClass 窗口")
    # 若窗口被最小化（rect 会是 -32000），先还原并置前
    u32.ShowWindow(hwnd, 9)          # SW_RESTORE
    u32.SetForegroundWindow(hwnd)
    time.sleep(1.5)
    rect = wt.RECT()
    u32.GetWindowRect(hwnd, ctypes.byref(rect))
    return (rect.left, rect.top, rect.right, rect.bottom)


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "shot.png"
    wait = float(sys.argv[2]) if len(sys.argv) > 2 else 1.0
    time.sleep(wait)
    box = window_box()
    img = ImageGrab.grab(bbox=box, all_screens=True)
    img.save(out)
    print("saved %s  %dx%d  bbox=%s" % (out, img.size[0], img.size[1], box))
    return 0


if __name__ == "__main__":
    sys.exit(main())
