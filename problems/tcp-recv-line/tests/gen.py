"""Sinh test cho tcp-recv-line. Chạy: python judge/judge.py gentests problems/tcp-recv-line
Dòng đầu: "cap chunk delay_ms [seed]" (chunk = 0: mảnh ngẫu nhiên 1..32 byte), sau đó là dữ liệu thô."""


def show(b):
    return "".join("\\n" if c == 10 else "\\r" if c == 13 else "\\0" if c == 0 else chr(c) for c in b)


def expected(data):
    head, _, body = data.partition(b"\n")
    cap = int(head.split()[0])
    out, i, calls = [], 0, 0
    while calls < 100000:
        calls += 1
        if i >= len(body):
            out.append("0 []")
            break
        j = i
        while j < len(body) and j - i < cap - 1:
            j += 1
            if body[j - 1] == 10:
                break
        piece = body[i:j]
        i = j
        out.append(f"{len(piece)} [{show(piece)}]")
    return "\n".join(out) + "\n"


def case(cap, chunk, delay, body, seed=None):
    head = f"{cap} {chunk} {delay}" + (f" {seed}" if seed is not None else "")
    return head.encode() + b"\n" + (body if isinstance(body, bytes) else body.encode())


def lines(rng, n, lo, hi, alphabet="abcdefghijklmnopqrstuvwxyz 0123456789"):
    return "".join("".join(rng.choice(alphabet) for _ in range(rng.randint(lo, hi))) + "\n" for _ in range(n))


def generate(rng):
    T = []
    # biên của cap
    for cap in (2, 3, 4, 5, 8):
        T.append((f"edge_cap_{cap}", case(cap, 100, 0, "ab\nabc\nabcd\n\nx")))
    T.append(("edge_line_exactly_cap_minus_1", case(6, 100, 0, "abcde\nabcd\nabcdef\n")))
    T.append(("edge_line_exactly_cap", case(6, 3, 0, "abcde\n" * 4)))
    T.append(("edge_only_newlines", case(4, 1, 0, "\n" * 10)))
    T.append(("edge_no_final_newline", case(64, 4, 1, "dong 1\ndong cuoi khong co xuong dong")))
    T.append(("edge_single_byte", case(64, 1, 0, "x")))
    T.append(("edge_empty_lines_crlf", case(16, 2, 0, "\r\n\r\n\n\r\r\n")))
    # luồng: mảnh ngẫu nhiên, dính nhiều dòng, có độ trễ
    T.append(("stream_coalesced_lines", case(64, 4096, 0, lines(rng, 50, 0, 20))))
    for k, seed in enumerate((7, 99, 12345, 2026)):
        T.append((f"stream_random_chunks_{k}", case(rng.choice([8, 16, 33, 64]), 0, 1, lines(rng, 40, 0, 50), seed)))
    T.append(("stream_split_at_newline", case(32, 5, 3, "1234\n6789\nabcd\n")))
    T.append(("stream_slow_byte_by_byte", case(16, 1, 2, "cham\ntung\nbyte\n")))
    # nhị phân / byte 0
    T.append(("robust_nul_bytes", case(16, 3, 0, b"a\x00b\n\x00\x00\x00\n\x00\nend")))
    T.append(("robust_nul_at_cap_edge", case(5, 2, 0, b"\x00\x00\x00\x00\x00\x00\n")))
    T.append(("robust_all_bytes", case(64, 0, 0, bytes(range(128)) * 4, 5)))
    T.append(("robust_cr_only", case(10, 4, 0, "a\rb\rc\rd\r\n")))
    # dòng dài hơn cap nhiều lần
    T.append(("edge_long_line_small_cap", case(7, 13, 0, "x" * 1000 + "\n" + "y" * 13 + "\n")))
    T.append(("edge_long_line_big_cap", case(4096, 0, 0, "z" * 10000 + "\nshort\n", 77)))
    # ngẫu nhiên tổng hợp
    for k in range(6):
        cap = rng.choice([2, 3, 5, 10, 31, 32, 33, 100, 256])
        body = bytes(rng.choice(b"ab\n\r\x00 ") for _ in range(rng.randint(100, 3000)))
        T.append((f"robust_random_{k}", case(cap, rng.choice([0, 1, 3, 64]), 0, body, rng.randint(1, 10 ** 6))))
    # lớn
    T.append(("stress_300kb_random_chunks", case(128, 0, 0, lines(rng, 6000, 0, 90), 31337)))
    T.append(("stress_many_tiny_lines", case(64, 4096, 0, "a\n" * 40000)))
    return T
