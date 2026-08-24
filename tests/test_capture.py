"""Tests for the pure PNG encoder in the capture helper (the GDI grab needs a
real screen and is tested on the user's machine)."""
import os
import sys
import struct
import zlib
import unittest

sys.path.insert(0, os.path.join(
    os.path.dirname(__file__), "..", "addon", "globalPlugins", "jobFormFiller"))

from core import capture  # noqa: E402


class TestPngEncoder(unittest.TestCase):
    def _decode_ihdr(self, png):
        self.assertEqual(png[:8], b"\x89PNG\r\n\x1a\n")
        # first chunk after signature is IHDR
        length = struct.unpack(">I", png[8:12])[0]
        self.assertEqual(png[12:16], b"IHDR")
        w, h, depth, color = struct.unpack(">IIBB", png[16:16 + 10])
        return w, h, depth, color

    def test_produces_valid_png_header(self):
        w, h = 4, 3
        png = capture.rgb_to_png(w, h, bytes([128]) * (w * h * 3))
        dw, dh, depth, color = self._decode_ihdr(png)
        self.assertEqual((dw, dh), (w, h))
        self.assertEqual(depth, 8)
        self.assertEqual(color, 2)  # RGB
        self.assertTrue(png.endswith(b"IEND" + struct.pack(
            ">I", zlib.crc32(b"IEND") & 0xffffffff)))

    def test_pixels_round_trip_through_idat(self):
        # a 2x1 image: red then green
        w, h = 2, 1
        rgb = bytes([255, 0, 0, 0, 255, 0])
        png = capture.rgb_to_png(w, h, rgb)
        # pull IDAT, decompress, drop per-row filter byte, compare
        i = png.find(b"IDAT")
        length = struct.unpack(">I", png[i - 4:i])[0]
        idat = png[i + 4:i + 4 + length]
        raw = zlib.decompress(idat)
        self.assertEqual(raw[0], 0)          # filter byte
        self.assertEqual(raw[1:], rgb)

    def test_rejects_wrong_length(self):
        with self.assertRaises(ValueError):
            capture.rgb_to_png(4, 4, b"tooshort")

    def test_rejects_bad_dimensions(self):
        with self.assertRaises(ValueError):
            capture.rgb_to_png(0, 5, b"")

    def test_bgra_to_rgb_swaps_and_flips(self):
        # one bottom-up BGRA pixel: B=1,G=2,R=3 -> RGB 3,2,1
        out = capture._bgra_to_rgb(bytes([1, 2, 3, 255]), 1, 1,
                                   flip_vertical=True)
        self.assertEqual(out, bytes([3, 2, 1]))


if __name__ == "__main__":
    unittest.main()
