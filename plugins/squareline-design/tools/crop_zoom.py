"""从截图中裁剪指定区域并放大，便于肉眼核对。

用法：python tools/crop_zoom.py <src.png> <out.png> x0 y0 x1 y1 [scale]
"""
import sys

from PIL import Image


def main():
    src, out = sys.argv[1], sys.argv[2]
    x0, y0, x1, y1 = (int(v) for v in sys.argv[3:7])
    scale = int(sys.argv[7]) if len(sys.argv) > 7 else 3
    img = Image.open(src).crop((x0, y0, x1, y1))
    img = img.resize((img.width * scale, img.height * scale), Image.LANCZOS)
    img.save(out)
    print("saved %s  %dx%d (from %dx%d, scale %d)"
          % (out, img.width, img.height, x1 - x0, y1 - y0, scale))
    return 0


if __name__ == "__main__":
    sys.exit(main())
