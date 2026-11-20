"""Turn the dithered bear (a PBM from the testbench) into two PNGs for the README, one per GitHub theme.

    python3 tools/render.py build/bear_rtl.pbm bear/bear-light.png bear/bear-dark.png \
        --mask bear/bear-mask.pgm --outline light --scale 4

Light theme: ink where the bear is black. Dark theme: ink where the bear is white, so its dark parts
melt into the page. Outside the mask everything is transparent. With --outline, a one-cell contour
around the mask gives the white face an edge on a white page.
Standard library only: a small palette PNG writer with a tRNS chunk.
"""
import argparse
import struct
import zlib

from golden import read_pbm, read_pgm

LIGHT_INK = (0x1F, 0x23, 0x28)  # GitHub's light-theme text colour
DARK_INK = (0xE6, 0xED, 0xF3)  # GitHub's dark-theme text colour


def chunk(kind, data):
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))


def write_png(path, rows, palette, alpha):
    """rows: palette indices per pixel. Index 0 is meant to be transparent (alpha[0] = 0)."""
    width, height = len(rows[0]), len(rows)
    depth = 1 if len(palette) <= 2 else 2
    per_byte = 8 // depth
    raw = bytearray()
    for row in rows:
        raw.append(0)  # filter: none
        for i in range(0, width, per_byte):
            byte = 0
            for j, index in enumerate(row[i : i + per_byte]):
                byte |= index << (8 - depth * (j + 1))
            raw.append(byte)
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, depth, 3, 0, 0, 0))
    png += chunk(b"PLTE", b"".join(bytes(c) for c in palette))
    png += chunk(b"tRNS", bytes(alpha))
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += chunk(b"IEND", b"")
    open(path, "wb").write(png)


def contour(width, height, keep):
    """Cells just outside the mask that touch it, including diagonally."""
    edge = [False] * (width * height)
    for y in range(height):
        for x in range(width):
            if keep[y * width + x]:
                continue
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < width and 0 <= ny < height and keep[ny * width + nx]:
                        edge[y * width + x] = True
    return edge


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("pbm")
    parser.add_argument("light")
    parser.add_argument("dark")
    parser.add_argument("--mask", help="a PGM, non-zero where the bear is; outside it stays transparent")
    parser.add_argument("--outline", choices=("none", "light", "both"), default="none")
    parser.add_argument("--scale", type=int, default=4, help="pixels per dithered pixel, nearest neighbour")
    args = parser.parse_args()

    width, height, black = read_pbm(args.pbm)
    keep = [True] * (width * height)
    if args.mask:
        keep = [v > 0 for v in read_pgm(args.mask)[2]]
    edge = contour(width, height, keep) if args.mask and args.outline != "none" else [False] * (width * height)

    s = args.scale
    for path, ink, theme in ((args.light, LIGHT_INK, "light"), (args.dark, DARK_INK, "dark")):
        outline = args.outline in (theme, "both")
        rows = []
        for y in range(height):
            row = []
            for x in range(width):
                i = y * width + x
                if keep[i]:
                    on = black[i] if theme == "light" else not black[i]
                else:
                    on = outline and edge[i]
                row += [1 if on else 0] * s
            rows += [row] * s
        write_png(path, rows, [(0, 0, 0), ink], [0, 255])


if __name__ == "__main__":
    main()
