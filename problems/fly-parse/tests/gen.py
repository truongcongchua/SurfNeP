"""Sinh test cho fly-parse. Chạy: python judge/judge.py gentests problems/fly-parse
Oracle (expected) viết độc lập với solution.c, dựa trên suite_fly.py."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "judge", "runner"))
import suite_fly as F  # noqa: E402


def ref(line):
    line2 = line[:-1] if line.endswith("\r") else line
    if line2 == "":
        return None
    toks = F.split_line(line)
    name, a = toks[0], toks[1:]
    if name in ("LOGIN", "REGISTER"):
        return "100 OK" if F.valid_account_args(a) else "201 INVALID"
    if name == "SEARCH":
        return "100 OK" if F.valid_search_args(a) else "201 INVALID"
    return "999 UNKNOWN ERROR"


def expected(data):
    text = data.decode("latin-1")
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    out = [r for r in (ref(ln) for ln in lines) if r is not None]
    return "\n".join(out) + ("\n" if out else "")


OK_ACC = ["LOGIN an 1234", "REGISTER binh abcd", "LOGIN a1b2c3 p@ss", "REGISTER x9 ~~~~", "LOGIN user0001 !!!!",
          "LOGIN " + "a" * 32 + " " + "p" * 32, "REGISTER 0 0000", "LOGIN 00000000000000000000000000000000 a1b2"]
OK_SEARCH = ["SEARCH HAN SGN 2026-12-20 2 ECO", "SEARCH SGN HAN 2026-12-21 1 BUS", "SEARCH HAN DAD 2026-12-20 9 ECO 2026-12-25",
             "SEARCH DAD PQC 1900-01-01 5 BUS 2100-12-31", "SEARCH AAA AAB 2024-02-29 3 ECO 2024-02-29",
             "SEARCH ZZZ AAA 2000-02-29 1 ECO 2000-03-01"]


def mutate(rng, s):
    k = rng.randint(0, 9)
    if not s:
        return s
    i = rng.randrange(len(s))
    if k == 0:
        return s[:i] + s[i + 1:]
    if k == 1:
        return s[:i] + rng.choice("aZ09-: \t~!") + s[i + 1:]
    if k == 2:
        return s[:i] + " " + s[i:]
    if k == 3:
        return s + rng.choice([" ", " x", "\t", " 1"])
    if k == 4:
        return " " + s
    if k == 5:
        return s.lower()
    if k == 6:
        parts = s.split(" ")
        if len(parts) > 1:
            parts.pop(rng.randrange(1, len(parts)))
        return " ".join(parts)
    if k == 7:
        return s.replace("-", "/", 1)
    if k == 8:
        return s.replace("2026", rng.choice(["1899", "2101", "0000", "2026x"]), 1)
    return s[:i] + chr(rng.randint(0x80, 0xFF)) + s[i + 1:]


def lines_of(items):
    return "".join(x + "\n" for x in items)


def generate(rng):
    T = []
    T.append(("basic_account_valid", lines_of(OK_ACC)))
    T.append(("basic_search_valid", lines_of(OK_SEARCH)))
    T.append(("basic_unknown_commands", "PING\nQUIT\nBOOK VN213\nHELP\nSEARCHX a\nLOGINN a b\nREGISTER2 a b\nx\n"))
    T.append(("basic_command_case", "login an 1234\nLogin an 1234\nregister an 1234\nsearch HAN SGN 2026-12-20 2 ECO\n"
              "Search HAN SGN 2026-12-20 2 ECO\n"))
    users = ["", "a", "a" * 31, "a" * 32, "a" * 33, "a" * 100, "A", "aB", "a_b", "a-b", "a.b", "a b", "\xe9", "1", "9" * 32]
    T.append(("edge_user_lengths", "".join(f"LOGIN {u} 1234\nREGISTER {u} 1234\n" for u in users)))
    pw = ["", "a", "ab", "abc", "abcd", "p" * 31, "p" * 32, "p" * 33, "p" * 64, "a\tb1", "ab\x7fc", "ab\x80c", "ab\xffcd",
          "ab\x01cd", "!!!!", "~~~~", "\"\"\"\"", "a'b'c", "a\\b\\c", "ab;cd", "ab\rcd"]
    T.append(("edge_pass_lengths_chars", "".join(f"LOGIN an {p}\n" for p in pw)))
    T.append(("edge_pass_every_printable", "".join(f"LOGIN an {chr(c) * 4}\n" for c in range(0x21, 0x7f))))
    T.append(("edge_pass_every_other_byte", "".join(
        f"LOGIN an ab{chr(c)}d\n" for c in list(range(1, 0x21)) + list(range(0x7f, 256)) if c not in (10, 32))))
    dates = ["1900-01-01", "1900-02-29", "1900-02-28", "2000-02-29", "2000-02-30", "2024-02-29", "2023-02-29", "2100-02-29",
             "2100-02-28", "2100-12-31", "2100-12-32", "2101-01-01", "1899-12-31", "0000-01-01", "2026-00-10", "2026-13-10",
             "2026-01-00", "2026-01-31", "2026-04-30", "2026-04-31", "2026-06-31", "2026-09-31", "2026-11-31", "2026-02-28",
             "2026-12-31", "2026-1-5", "26-12-20", "2026/12/20", "2026-12-2", "2026-12-200", "2026-12-20 ", "20261220",
             "2026-12-2a", "202a-12-20", "٢٠٢٦-١٢-٢٠", "2026-12-20x", "2026-W12-5",
             "-026-12-20", "2026--12-20", "2026-12--1"]
    T.append(("edge_dates", "".join(f"SEARCH HAN SGN {d} 1 ECO\n" for d in dates)))
    T.append(("edge_dates_return", "".join(f"SEARCH HAN SGN 2026-12-20 1 ECO {d}\n" for d in dates)))
    T.append(("edge_return_order", "".join(f"SEARCH HAN SGN {a} 1 ECO {b}\n" for a, b in [
        ("2026-12-20", "2026-12-19"), ("2026-12-20", "2026-12-20"), ("2026-12-20", "2026-12-21"), ("2026-12-31", "2027-01-01"),
        ("2027-01-01", "2026-12-31"), ("1900-01-01", "2100-12-31"), ("2100-12-31", "1900-01-01"), ("2026-02-28", "2026-03-01"),
        ("2026-10-01", "2026-09-30"), ("2026-09-30", "2026-10-01"), ("2024-02-29", "2024-02-28")])))
    ap = ["HAN", "han", "Han", "HA", "HANN", "H", "", "H4N", "HA-", "HA\xd1", " HAN", "HAN ", "AAA", "ZZZ", "A@Z", "[[["]
    T.append(("edge_airports", "".join(f"SEARCH {a} SGN 2026-12-20 1 ECO\nSEARCH SGN {a} 2026-12-20 1 ECO\n" for a in ap)
              + "SEARCH HAN HAN 2026-12-20 1 ECO\nSEARCH SGN SGN 2026-12-20 1 ECO\nSEARCH AAA AAB 2026-12-20 1 ECO\n"))
    T.append(("edge_pax", "".join(f"SEARCH HAN SGN 2026-12-20 {p} ECO\n" for p in
                                 ["0", "1", "5", "9", "10", "00", "01", "99", "a", "-1", "+1", "1.0", "", " ", "\xb9"])))
    T.append(("edge_class", "".join(f"SEARCH HAN SGN 2026-12-20 1 {c}\n" for c in
                                    ["ECO", "BUS", "eco", "bus", "Eco", "ECONOMY", "BUSINESS", "FIRST", "EC", "BU", "ECOO", "",
                                     "ECO ", "E CO", "EC0"])))
    T.append(("edge_token_counts",
              "SEARCH\nSEARCH HAN\nSEARCH HAN SGN\nSEARCH HAN SGN 2026-12-20\nSEARCH HAN SGN 2026-12-20 1\n"
              "SEARCH HAN SGN 2026-12-20 1 ECO\nSEARCH HAN SGN 2026-12-20 1 ECO 2026-12-21\n"
              "SEARCH HAN SGN 2026-12-20 1 ECO 2026-12-21 x\nSEARCH HAN SGN 2026-12-20 1 ECO 2026-12-21 2026-12-22\n"
              "LOGIN\nLOGIN an\nLOGIN an 1234\nLOGIN an 1234 x\nLOGIN an 1234 x y\n"
              "REGISTER\nREGISTER an\nREGISTER an 1234\nREGISTER an 1234 5678\n"))
    T.append(("edge_empty_input", ""))
    T.append(("edge_only_blank_lines", "\n\n\r\n\r\n\n"))
    T.append(("edge_no_final_newline", "LOGIN an 1234\nSEARCH HAN SGN 2026-12-20 2 ECO"))
    T.append(("edge_no_final_newline_invalid", "LOGIN an 1234\nPING"))
    T.append(("edge_single_line", "LOGIN an 1234\n"))
    T.append(("stream_crlf", "LOGIN an 1234\r\nSEARCH HAN SGN 2026-12-20 2 ECO\r\n\r\nPING\r\nLOGIN an 12\r\n"))
    T.append(("stream_double_cr", "LOGIN an 1234\r\r\nSEARCH HAN SGN 2026-12-20 2 ECO\r\r\n\r\r\n\r\n"))
    T.append(("stream_cr_only_line", "\r\n\r\r\n\rLOGIN an 1234\n"))
    T.append(("robust_extra_spaces", lines_of([
        " LOGIN an 1234", "LOGIN  an 1234", "LOGIN an  1234", "LOGIN an 1234 ", "LOGIN an 1234  ", "  ", " ",
        "LOGIN\tan 1234", "LOGIN an\t1234", "LOGIN an 1234\t", "\tLOGIN an 1234", " SEARCH HAN SGN 2026-12-20 1 ECO",
        "SEARCH  HAN SGN 2026-12-20 1 ECO", "SEARCH HAN SGN 2026-12-20 1 ECO ", "SEARCH HAN SGN 2026-12-20 1 ECO  2026-12-21",
        "SEARCH HAN SGN 2026-12-20 1 ECO 2026-12-21 ", "SEARCH HAN SGN 2026-12-20  1 ECO", "SEARCH\tHAN SGN 2026-12-20 1 ECO",
        "PING ", " PING", "  PING  "])))
    T.append(("robust_many_tokens", lines_of([
        "LOGIN " + " ".join(["a"] * 40), "SEARCH " + " ".join(["HAN"] * 40), "PING " + " ".join(["x"] * 40),
        "LOGIN " + " ".join(["a"] * 1000), "SEARCH " + " ".join(["a"] * 700), " ".join(["x"] * 2000),
        "LOGIN an 1234" + " x" * 30, "LOGIN an 1234" + " x" * 31, "LOGIN an 1234" + " x" * 32, "LOGIN an 1234" + " x" * 33,
        "LOGIN an 1234" + " " * 40, "SEARCH HAN SGN 2026-12-20 1 ECO" + " " * 30, "SEARCH HAN SGN 2026-12-20 1 ECO" + " " * 31,
        "SEARCH HAN SGN 2026-12-20 1 ECO" + " " * 32, "LOGIN" + " " * 40, "SEARCH" + " " * 40,
        " " * 40 + "LOGIN an 1234"])))
    T.append(("robust_long_lines", "LOGIN an " + "p" * 3900 + "\nSEARCH " + "H" * 3900 + " SGN 2026-12-20 1 ECO\n"
              + "x" * 3990 + "\nLOGIN an 1234\n"))
    T.append(("robust_binary_bytes", lines_of([
        "LOGIN a\xe9n 1234", "LOGIN an 12\xff4", "\x01LOGIN an 1234", "LOGIN\x01 an 1234", "SEARCH HAN SGN 2026-12-20 1 ECO\x7f",
        "SEARCH HAN SGN 2026-12-20 1 \x80ECO", "\xc3\xa9", "\x1b[31mLOGIN an 1234", "LOGIN an 1234\x0b", "LOGIN an 1234\x0c"])))
    base = OK_ACC + OK_SEARCH
    for k in range(6):
        lines = []
        for _ in range(400):
            s = rng.choice(base)
            if rng.random() < 0.15 and k >= 2:
                s = "SEARCH %s %s %04d-%02d-%02d %d %s" % (
                    "".join(rng.choice("ABC") for _ in range(3)), "".join(rng.choice("ABC") for _ in range(3)),
                    rng.choice([1900, 2000, 2024, 2026, 2100, 2101]), rng.randint(0, 13), rng.randint(0, 32),
                    rng.randint(0, 10), rng.choice(["ECO", "BUS", "eco"]))
            if rng.random() < 0.6:
                for _ in range(rng.randint(1, 2)):
                    s = mutate(rng, s)
            if rng.random() < 0.1:
                s = ""
            lines.append(s + rng.choice(["", "", "", "\r"]))
        T.append((f"stress_random_{k}", "\n".join(lines) + "\n"))
    big = []
    for _ in range(40000):
        s = rng.choice(base)
        if rng.random() < 0.5:
            s = mutate(rng, s)
        big.append(s)
    T.append(("stress_big_input", "\n".join(big) + "\n"))
    return [(n, b"".join(c.encode("latin-1") if ord(c) < 256 else c.encode("utf-8") for c in d)) for n, d in T]
