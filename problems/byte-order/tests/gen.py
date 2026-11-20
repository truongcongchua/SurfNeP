"""Sinh test cho byte-order. Chạy: python judge/judge.py gentests problems/byte-order"""

U16_EDGE = [0, 1, 2, 127, 128, 255, 256, 257, 4660, 32767, 32768, 65279, 65534, 65535]
U32_EDGE = [0, 1, 255, 256, 65535, 65536, 16777215, 16777216, 2147483647, 2147483648,
            2147483649, 3232235777, 4278190080, 4294967294, 4294967295, 128, 0x80000000]
BAD = ["u16 65536", "u32 4294967296", "u16 -0", "u16 -1", "u32 -5", "u16 +5", "u32 +0", "u16 5a", "u16 0x10",
       "u16 1e3", "u16 3.0", "u16 ", "u16", "u32", "u8 1", "u64 1", "U16 1", "u16 1 2", "u32 1 x", "x", "16 u16",
       "u16 99999999999999999999", "u32 18446744073709551616", "u32 184467440737095516160", "u16 ١٢",
       "u16\t", "u160 1", "u1 6"]


def ref(line):
    w = line.split()
    if not w:
        return None
    if len(w) != 2 or w[0] not in ("u16", "u32") or not w[1].isascii() or not w[1].isdigit():
        return "ERROR"
    v, n = int(w[1]), (2 if w[0] == "u16" else 4)
    if v >= 1 << (8 * n):
        return "ERROR"
    b = v.to_bytes(n, "big")
    return " ".join(f"{x:02X}" for x in b) + " | " + str(int.from_bytes(b, "little"))


def expected(data):
    """Oracle độc lập với solution.c."""
    out = []
    for line in data.decode("utf-8", "replace").split("\n"):
        r = ref(line.replace("\r", " "))
        if r is not None:
            out.append(r)
    return "\n".join(out) + ("\n" if out else "")


def generate(rng):
    T = []
    T.append(("edge_u16_boundaries", "".join(f"u16 {v}\n" for v in U16_EDGE)))
    T.append(("edge_u32_boundaries", "".join(f"u32 {v}\n" for v in U32_EDGE)))
    T.append(("edge_high_bit_u32", "".join(f"u32 {1 << k}\n" for k in range(32))))
    T.append(("edge_high_bit_u16", "".join(f"u16 {1 << k}\n" for k in range(16))))
    T.append(("edge_just_over", "u16 65535\nu16 65536\nu32 4294967295\nu32 4294967296\n"))
    T.append(("edge_leading_zeros", "u16 0004660\nu32 00000000000000000001\nu16 00\nu16 065535\nu16 065536\n"))
    T.append(("edge_empty_input", ""))
    T.append(("edge_only_blank_lines", "\n\n   \n\t\n\r\n"))
    T.append(("edge_no_final_newline", "u16 4660\nu32 1"))
    T.append(("edge_single_line", "u32 3232235777\n"))
    T.append(("edge_invalid_all", "".join(b + "\n" for b in BAD)))
    T.append(("edge_minus_zero", "u16 -0\nu32 -0\nu16 0\n"))
    T.append(("edge_plus_sign", "u16 +1\nu32 +4294967295\n"))
    T.append(("edge_overflow_ull", "u32 18446744073709551615\nu32 18446744073709551616\nu16 340282366920938463463374607431768211456\n"))
    T.append(("stream_crlf", "u16 4660\r\nu32 1\r\n\r\nu16 70000\r\n"))
    T.append(("stream_tabs_spaces", "  u16\t4660\nu32   \t 1   \n\tu16 1\t\n"))
    T.append(("stream_long_padding", "u16" + " " * 40 + "4660\n" + " " * 50 + "u32 7\n" + "u32 1" + " " * 50 + "\n"))
    T.append(("robust_extra_words", "u16 1 2\nu32 1 2 3 4 5\nu16 4660 #comment\n"))
    T.append(("robust_garbage_bytes", "u16 1\n\x01\x02 u16\nu16 \x7f\nzzz\nu32 2\n"))
    T.append(("robust_mixed_case", "U16 1\nu16 1\nU32 1\nu32 1\nuU16 1\n"))
    # ngẫu nhiên hợp lệ
    for k in range(4):
        lines = []
        for _ in range(200):
            if rng.random() < 0.5:
                lines.append(f"u16 {rng.randint(0, 65535)}")
            else:
                lines.append(f"u32 {rng.randint(0, 4294967295)}")
        T.append((f"basic_random_valid_{k}", "\n".join(lines) + "\n"))
    # ngẫu nhiên trộn hợp lệ / sai / dòng trống / khoảng trắng
    for k in range(6):
        lines = []
        for _ in range(300):
            r = rng.random()
            if r < 0.45:
                t = rng.choice(["u16", "u32"])
                hi = 65535 if t == "u16" else 4294967295
                v = rng.choice([rng.randint(0, hi), hi, hi + 1, 0, rng.randint(hi, hi * 3)])
                sep = rng.choice([" ", "  ", "\t", " \t "])
                lines.append(rng.choice(["", " ", "\t"]) + t + sep + str(v).zfill(rng.choice([0, 0, 0, 8])) + rng.choice(["", " ", "\r"]))
            elif r < 0.8:
                lines.append(rng.choice(BAD))
            else:
                lines.append(rng.choice(["", " ", "\t", "\r"]))
        T.append((f"robust_random_mixed_{k}", "\n".join(lines) + rng.choice(["\n", ""])))
    # lớn
    big = []
    for _ in range(100000):
        if rng.random() < 0.5:
            big.append(f"u16 {rng.randint(0, 65535)}")
        else:
            big.append(f"u32 {rng.randint(0, 4294967295)}")
    T.append(("stress_100k_lines", "\n".join(big) + "\n"))
    mixed = []
    for _ in range(50000):
        mixed.append(rng.choice([f"u32 {rng.randint(0, 1 << 33)}", rng.choice(BAD), ""]))
    T.append(("stress_50k_mixed", "\n".join(mixed) + "\n"))
    return T
