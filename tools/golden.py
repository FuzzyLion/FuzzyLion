"""Reference model of hw/bear_dither.sv: Atkinson dithering with the same integer arithmetic.

    python3 tools/golden.py bear/bear.pgm build/bear_golden.pgm
    python3 tools/golden.py bear/bear.pgm build/bear_golden.pgm --compare build/bear_rtl.pgm

Each pixel becomes black or white. A share of 1/8 of its error goes to each of six neighbours,
so 2/8 of it is dropped, which keeps highlights and shadows clean:

             x   x+1 x+2
      y          1/8 1/8
      y+1   1/8 1/8 1/8      (x-1, x, x+1)
      y+2       1/8
"""
import argparse

NEIGHBOURS = ((1, 0), (2, 0), (-1, 1), (0, 1), (1, 1), (0, 2))


def read_pgm(path):
    data = open(path, "rb").read()
    fields, pos = [], 0
    while len(fields) < 4:  # magic, width, height, maxval
        while data[pos : pos + 1].isspace():
            pos += 1
        if data[pos : pos + 1] == b"#":
            pos = data.index(b"\n", pos) + 1
            continue
        start = pos
        while not data[pos : pos + 1].isspace():
            pos += 1
        fields.append(data[start:pos])
    pos += 1  # exactly one whitespace byte; the pixels may begin with bytes that look like whitespace
    if fields[0] != b"P5" or int(fields[3]) != 255:
        raise SystemExit(f"{path}: expected an 8-bit binary PGM")
    width, height = int(fields[1]), int(fields[2])
    pixels = data[pos : pos + width * height]
    if len(pixels) != width * height:
        raise SystemExit(f"{path}: truncated")
    return width, height, pixels


def write_pbm(path, width, height, black):
    """ASCII PBM, the format the testbench writes: 1 is black."""
    with open(path, "w") as f:
        f.write(f"P1\n{width} {height}\n")
        for y in range(height):
            f.write("".join(str(b) for b in black[y * width : (y + 1) * width]) + "\n")


def read_pbm(path):
    tokens = [line.split("#")[0] for line in open(path).read().splitlines()]
    text = " ".join(tokens).split(maxsplit=3)
    if text[0] != "P1":
        raise SystemExit(f"{path}: expected an ASCII PBM")
    width, height = int(text[1]), int(text[2])
    black = [int(ch) for ch in text[3] if ch in "01"]
    if len(black) != width * height:
        raise SystemExit(f"{path}: {len(black)} pixels, expected {width * height}")
    return width, height, black


def atkinson(width, height, pixels, keep=None):
    """Returns one bit per pixel, 1 for black. Pixels outside `keep` stay 0 and pass no error on."""
    error = [[0] * width for _ in range(height)]
    black = [0] * (width * height)
    for y in range(height):
        for x in range(width):
            if keep is not None and not keep[y * width + x]:
                continue
            old = pixels[y * width + x] + error[y][x]
            white = old >= 128
            share = (old - 255 if white else old) >> 3  # floor, like >>> on a signed value
            black[y * width + x] = 0 if white else 1
            for dx, dy in NEIGHBOURS:
                if 0 <= x + dx < width and y + dy < height:
                    error[y + dy][x + dx] += share
    return black


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("pgm")
    parser.add_argument("out", help="the model's result, as a PBM")
    parser.add_argument("--mask", help="a PGM, non-zero where the bear is")
    parser.add_argument("--compare", help="an RTL result (PBM) to check bit for bit")
    args = parser.parse_args()

    width, height, pixels = read_pgm(args.pgm)
    keep = None
    if args.mask:
        mw, mh, mask = read_pgm(args.mask)
        if (mw, mh) != (width, height):
            raise SystemExit(f"mask is {mw}x{mh}, picture is {width}x{height}")
        keep = [v > 0 for v in mask]
    out = atkinson(width, height, pixels, keep)
    write_pbm(args.out, width, height, out)
    if args.compare:
        w, h, rtl = read_pbm(args.compare)
        if (w, h) != (width, height):
            raise SystemExit(f"size differs: RTL {w}x{h}, model {width}x{height}")
        wrong = [i for i in range(width * height) if rtl[i] != out[i]]
        if wrong:
            y, x = divmod(wrong[0], width)
            raise SystemExit(f"FAIL: {len(wrong)} of {width * height} pixels differ, first at x={x} y={y}")
        print(f"PASS: RTL matches the model on all {width * height} pixels")


if __name__ == "__main__":
    main()
