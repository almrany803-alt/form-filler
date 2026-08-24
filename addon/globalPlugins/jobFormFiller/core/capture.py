"""Capture just one control's pixels, for the optional vision step.

Grabs the screen rectangle of a single focused control (from its NVDA location)
and returns PNG bytes. Only that one control is ever captured, never the page or
the other fields, so the user's filled-in name and answers are never in the
image. Dependency-free: a small GDI grab plus a minimal pure-Python PNG encoder,
so nothing needs bundling into the add-on.

The GDI grab is Windows-only and can't run in CI, so it's isolated at the bottom.
The PNG encoder is pure and is unit-tested, since a malformed image would silently
break every vision call.
"""

import zlib
import struct


def rgb_to_png(width, height, rgb_bytes):
    """Encode raw top-to-bottom RGB bytes (width*height*3) into PNG bytes. Pure
    Python; used so we never bundle an imaging library."""
    if width <= 0 or height <= 0:
        raise ValueError("bad dimensions")
    if len(rgb_bytes) != width * height * 3:
        raise ValueError("rgb_bytes length %d != %d" % (
            len(rgb_bytes), width * height * 3))

    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xffffffff))

    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)  # 8-bit RGB
    row = width * 3
    # each scanline is prefixed with a filter-type byte (0 = none)
    raw = bytearray()
    for y in range(height):
        raw.append(0)
        raw.extend(rgb_bytes[y * row:(y + 1) * row])
    idat = zlib.compress(bytes(raw), 6)
    return sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")


def _bgra_to_rgb(bgra, width, height, flip_vertical):
    """GDI hands back bottom-up BGRA rows; convert to top-down RGB for PNG."""
    row = width * 4
    out = bytearray(width * height * 3)
    for y in range(height):
        src_y = (height - 1 - y) if flip_vertical else y
        s = src_y * row
        d = y * width * 3
        for x in range(width):
            b = bgra[s + x * 4]
            g = bgra[s + x * 4 + 1]
            r = bgra[s + x * 4 + 2]
            out[d + x * 3] = r
            out[d + x * 3 + 1] = g
            out[d + x * 3 + 2] = b
    return bytes(out)


def capture_rect_png(left, top, width, height):
    """Capture a screen rectangle and return PNG bytes. Windows/GDI only; returns
    None on any failure so the caller falls back to today's behaviour. Never
    raises into the fill path."""
    try:
        import ctypes
        from ctypes import wintypes
    except Exception:
        return None
    if width <= 0 or height <= 0:
        return None
    gdi32 = ctypes.windll.gdi32
    user32 = ctypes.windll.user32
    screen_dc = user32.GetDC(0)
    mem_dc = gdi32.CreateCompatibleDC(screen_dc)
    bmp = gdi32.CreateCompatibleBitmap(screen_dc, width, height)
    old = gdi32.SelectObject(mem_dc, bmp)
    SRCCOPY = 0x00CC0020
    try:
        gdi32.BitBlt(mem_dc, 0, 0, width, height, screen_dc, left, top, SRCCOPY)

        class BITMAPINFOHEADER(ctypes.Structure):
            _fields_ = [("biSize", wintypes.DWORD),
                        ("biWidth", wintypes.LONG),
                        ("biHeight", wintypes.LONG),
                        ("biPlanes", wintypes.WORD),
                        ("biBitCount", wintypes.WORD),
                        ("biCompression", wintypes.DWORD),
                        ("biSizeImage", wintypes.DWORD),
                        ("biXPelsPerMeter", wintypes.LONG),
                        ("biYPelsPerMeter", wintypes.LONG),
                        ("biClrUsed", wintypes.DWORD),
                        ("biClrImportant", wintypes.DWORD)]

        bmi = BITMAPINFOHEADER()
        bmi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bmi.biWidth = width
        bmi.biHeight = height  # positive = bottom-up rows
        bmi.biPlanes = 1
        bmi.biBitCount = 32
        bmi.biCompression = 0  # BI_RGB
        buf_len = width * height * 4
        buf = (ctypes.c_char * buf_len)()
        DIB_RGB_COLORS = 0
        got = gdi32.GetDIBits(mem_dc, bmp, 0, height, buf,
                              ctypes.byref(bmi), DIB_RGB_COLORS)
        if not got:
            return None
        rgb = _bgra_to_rgb(bytes(buf), width, height, flip_vertical=True)
        return rgb_to_png(width, height, rgb)
    except Exception:
        return None
    finally:
        gdi32.SelectObject(mem_dc, old)
        gdi32.DeleteObject(bmp)
        gdi32.DeleteDC(mem_dc)
        user32.ReleaseDC(0, screen_dc)
