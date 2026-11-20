"""Turn the resized bear (a 24-bit BMP from sips) into the 8-bit grayscale PGM that the RTL reads.

    python3 tools/prep.py build/bear.bmp bear/bear.pgm [--gamma 1.0]

Standard library only. The Makefile's `prep` target runs sips first (macOS).
"""
import argparse
import struct


def read_bmp(path):
    data = open(path, "rb").read()
    if data[:2] != b"BM":
        raise SystemExit(f"{path}: not a BMP file")
    offset = struct.unpack_from("<I", data, 10)[0]
    width, height = struct.unpack_from("<ii", data, 18)
    bpp, = struct.unpack_from("<H", data, 28)
    compression, = struct.unpack_from("<I", data, 30)
    if bpp not in (24, 32) or compression not in (0, 3):
        raise SystemExit(f"{path}: only uncompressed 24- or 32-bit BMP is supported")
    top_down = height < 0
    height = abs(height)
    stride = (bpp * width + 31) // 32 * 4
    step = bpp // 8
    pixels = []
    for row in range(height):
        y = row if top_down else height - 1 - row
        base = offset + y * stride
        for x in range(width):
            b, g, r = data[base + x * step : base + x * step + 3]
            pixels.append((r, g, b))
    return width, height, pixels


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("bmp")
    parser.add_argument("pgm")
    parser.add_argument("--black", type=float, default=0, help="this grey and darker becomes black")
    parser.add_argument("--white", type=float, default=255, help="this grey and lighter becomes white")
    parser.add_argument("--gamma", type=float, default=1.0, help="below 1 lifts the midtones")
    args = parser.parse_args()

    width, height, pixels = read_bmp(args.bmp)
    gray = bytearray()
    for r, g, b in pixels:
        y = (299 * r + 587 * g + 114 * b) / 1000
        y = min(max((y - args.black) / (args.white - args.black), 0.0), 1.0)
        gray.append(round(255 * y ** args.gamma))
    with open(args.pgm, "wb") as f:
        f.write(f"P5\n{width} {height}\n255\n".encode())
        f.write(gray)


if __name__ == "__main__":
    main()
