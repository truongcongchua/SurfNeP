"""Sinh test cho fly-compare. Chạy: python judge/judge.py gentests problems/fly-compare
Oracle (expected) viết độc lập với solution.c. Dữ liệu: files/flights.txt (cố định, có 10 chuyến hòa khóa)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "judge", "runner"))
import suite_fly as F  # noqa: E402

with open(os.path.join(HERE, "..", "files", "flights.txt"), encoding="utf-8") as _fh:
    FLIGHTS = F.parse_flights(_fh.read())
KEYS = sorted({(f["from"], f["to"], f["date"]) for f in FLIGHTS})
TIES = ("DAD", "HUI", "2026-12-25")
CRITS = ["PRICE", "DURATION", "DEPART"]


def rows(frm, to, d, pax, cls):
    out = []
    for f in FLIGHTS:
        if f["from"] == frm and f["to"] == to and f["date"] == d and F.seats(f, cls) >= int(pax):
            out.append((f, F.duration(f), F.price(f, cls) * int(pax)))
    return out


def answer(line):
    t = line.split(" ")
    if t[0] == "COMPARE" and len(t) == 7:
        frm, to, d, pax, cls, crit = t[1:]
        rs = rows(frm, to, d, pax, cls)
        if crit == "PRICE":
            rs.sort(key=lambda r: (r[2], r[1], r[0]["code"]))
        elif crit == "DURATION":
            rs.sort(key=lambda r: (r[1], r[2], r[0]["code"]))
        elif crit == "DEPART":
            rs.sort(key=lambda r: (r[0]["dep"], r[0]["code"]))
        else:
            return ["201 INVALID"]
        return [f"110 FLIGHTS {len(rs)}"] + [f"{f['code']} {f['airline']} {f['dep']} {f['arr']} {m} {tot}" for f, m, tot in rs]
    if t[0] == "BEST" and len(t) == 6:
        rs = rows(*t[1:])
        out = []
        for al in sorted({r[0]["airline"] for r in rs}):
            mine = [r for r in rs if r[0]["airline"] == al]
            cheap = min(mine, key=lambda r: (r[2], r[0]["code"]))
            fast = min(mine, key=lambda r: (r[1], r[0]["code"]))
            out.append(f"{al} CHEAPEST {cheap[0]['code']} {cheap[2]} FASTEST {fast[0]['code']} {fast[1]}")
        return [f"110 AIRLINES {len(out)}"] + out
    return ["999 UNKNOWN ERROR"]


def expected(data):
    lines = data.decode("latin-1").split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    out = []
    for ln in lines:
        if ln.endswith("\r"):
            ln = ln[:-1]
        if ln == "":
            continue
        out += answer(ln)
    return "\n".join(out) + ("\n" if out else "")


def q(key, pax, cls, crit=None, cmd="COMPARE"):
    base = f"{cmd} {key[0]} {key[1]} {key[2]} {pax} {cls}"
    return base + (f" {crit}" if crit else "")


def generate(rng):
    T = []
    for crit in CRITS:
        T.append((f"basic_every_key_{crit.lower()}", "".join(q(k, 1, "ECO", crit) + "\n" for k in KEYS)))
    T.append(("basic_every_key_best", "".join(q(k, 1, "ECO", cmd="BEST") + "\n" for k in KEYS)))
    T.append(("basic_every_key_bus_all", "".join(q(k, 1, "BUS", c) + "\n" for k in KEYS[:80] for c in CRITS)))
    T.append(("basic_random_compare", "".join(q(rng.choice(KEYS), rng.randint(1, 9), rng.choice(["ECO", "BUS"]), rng.choice(CRITS)) + "\n"
                                             for _ in range(400))))
    T.append(("basic_random_best", "".join(q(rng.choice(KEYS), rng.randint(1, 9), rng.choice(["ECO", "BUS"]), cmd="BEST") + "\n"
                                          for _ in range(300))))
    hub = ("HAN", "SGN", "2026-12-20")
    T.append(("edge_hub_all", "".join(q(hub, p, c, crit) + "\n" for p in range(1, 10) for c in ("ECO", "BUS") for crit in CRITS)
              + "".join(q(hub, p, c, cmd="BEST") + "\n" for p in range(1, 10) for c in ("ECO", "BUS"))))
    for crit in CRITS:
        T.append((f"basic_hub_{crit.lower()}_all_pax", "".join(q(hub, p, c, crit) + chr(10) for p in range(1, 10) for c in ("ECO", "BUS"))))
    T.append(("edge_ties_bus_only", "".join(q(TIES, p, "BUS", crit) + chr(10) for p in range(1, 6) for crit in CRITS)))
    T.append(("edge_ties_all_criteria", "".join(q(TIES, p, c, crit) + "\n" for p in range(1, 10) for c in ("ECO", "BUS") for crit in CRITS)))
    T.append(("edge_ties_best", "".join(q(TIES, p, c, cmd="BEST") + "\n" for p in range(1, 10) for c in ("ECO", "BUS"))))
    T.append(("edge_numeric_not_string_sort", "".join(q(TIES, 1, "ECO", "PRICE") + "\n" + q(TIES, 9, "ECO", "PRICE") + "\n" for _ in range(3))))
    T.append(("edge_overnight_duration", "".join(q(TIES, 1, "ECO", "DURATION") + "\n" for _ in range(2))
              + "".join(q((f["from"], f["to"], f["date"]), 1, "ECO", "DURATION") + "\n" for f in FLIGHTS if f["arr"] < f["dep"])))
    T.append(("edge_no_results", "".join(q(k, 1, "ECO", c) + "\n" for k in [("HAN", "SGN", "2026-12-17"), ("XXX", "SGN", "2026-12-20"),
                                                                           ("SGN", "SGN", "2026-12-20")] for c in CRITS)
              + "BEST HAN SGN 2026-12-17 1 ECO\nBEST XXX SGN 2026-12-20 1 BUS\n"))
    T.append(("edge_invalid_criterion", "".join(q(TIES, 1, "ECO", c) + "\n" for c in ["price", "Price", "LOWEST", "DEPARTURE", "DUR", "ASC"])
              + q(TIES, 1, "ECO", "PRICE") + "\n"))
    T.append(("edge_unknown_commands", "compare DAD HUI 2026-12-25 1 ECO PRICE\nSEARCH DAD HUI 2026-12-25 1 ECO\nBEST2 DAD HUI 2026-12-25 1 ECO\nHELP\nx\n"
              + q(TIES, 1, "ECO", "PRICE") + "\n"))
    T.append(("edge_best_airline_alphabetical", "".join(q(k, 1, "ECO", cmd="BEST") + "\n" for k in KEYS if len({f["airline"] for f in FLIGHTS
                                                                                                            if (f["from"], f["to"], f["date"]) == k}) >= 2)))
    T.append(("edge_empty_input", ""))
    T.append(("edge_only_blank_lines", "\n\r\n\n"))
    T.append(("edge_no_final_newline", q(TIES, 2, "ECO", "PRICE") + "\n" + q(TIES, 1, "ECO", cmd="BEST")))
    T.append(("stream_crlf", "".join(q(TIES, p, "ECO", c) + "\r\n" for p in (1, 2) for c in CRITS) + "\r\n" + q(TIES, 1, "ECO", cmd="BEST") + "\r\n"))
    T.append(("stream_blank_lines_mixed", "".join((q(rng.choice(KEYS), rng.randint(1, 9), "ECO", rng.choice(CRITS)) if rng.random() < 0.6 else "") + "\n"
                                                  for _ in range(200))))
    T.append(("robust_repeat_same_20000", (q(TIES, 1, "ECO", "PRICE") + "\n") * 5000))
    T.append(("robust_hub_repeated", "".join(q(hub, p, "ECO", c) + "\n" for _ in range(12) for p in (1, 5, 9) for c in CRITS)))
    for i in range(3):
        T.append((f"stress_random_{i}", "".join(
            q(rng.choice(KEYS + [TIES] * 30), rng.randint(1, 9), rng.choice(["ECO", "ECO", "BUS"]), rng.choice(CRITS)) + "\n" if rng.random() < 0.8 else
            q(rng.choice(KEYS + [TIES] * 30), rng.randint(1, 9), rng.choice(["ECO", "BUS"]), cmd="BEST") + "\n" for _ in range(8000))))
    return T
