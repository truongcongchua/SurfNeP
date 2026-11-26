"""Sinh test cho flight-filter. Chạy: python judge/judge.py gentests problems/flight-filter
Oracle (expected) dùng suite_fly.py, độc lập với solution.c. Dữ liệu: files/flights.txt (cố định)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "judge", "runner"))
import suite_fly as F  # noqa: E402

with open(os.path.join(HERE, "..", "files", "flights.txt"), encoding="utf-8") as _fh:
    FLIGHTS = F.parse_flights(_fh.read())
KEYS = sorted({(f["from"], f["to"], f["date"]) for f in FLIGHTS})
AIRPORTS = sorted({f["from"] for f in FLIGHTS})
DATES = sorted({f["date"] for f in FLIGHTS})


def expected(data):
    out = []
    lines = data.decode("latin-1").split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    for ln in lines:
        if ln.endswith("\r"):
            ln = ln[:-1]
        if ln == "":
            continue
        frm, to, d, pax, cls = ln.split(" ")
        res = F.search(FLIGHTS, frm, to, d, pax, cls)
        out.append(f"110 FLIGHTS {len(res)}")
        out += res
    return "\n".join(out) + ("\n" if out else "")


def q(key, pax, cls):
    return f"{key[0]} {key[1]} {key[2]} {pax} {cls}"


def generate(rng):
    T = []
    hub = ("HAN", "SGN", "2026-12-20")
    T.append(("basic_hub_all_pax", "".join(q(hub, p, c) + "\n" for p in range(1, 10) for c in ("ECO", "BUS"))))
    T.append(("basic_every_key_eco", "".join(q(k, 1, "ECO") + "\n" for k in KEYS)))
    T.append(("basic_every_key_bus", "".join(q(k, 1, "BUS") + "\n" for k in KEYS)))
    for pax, cls in [(2, "ECO"), (5, "ECO"), (9, "ECO"), (2, "BUS"), (5, "BUS"), (9, "BUS")]:
        T.append((f"basic_every_key_pax{pax}_{cls.lower()}", "".join(q(k, pax, cls) + "\n" for k in KEYS)))
    T.append(("basic_random_hits", "".join(q(rng.choice(KEYS), rng.randint(1, 9), rng.choice(["ECO", "BUS"])) + "\n" for _ in range(400))))
    lines = []
    for f in FLIGHTS:
        for cls in ("ECO", "BUS"):
            s = F.seats(f, cls)
            for p in (s, s + 1, s - 1):
                if 1 <= p <= 9:
                    lines.append(q((f["from"], f["to"], f["date"]), p, cls))
    T.append(("edge_seats_exact_boundary", "\n".join(lines) + "\n"))
    T.append(("edge_no_match", "".join(q(k, 1, "ECO") + "\n" for k in [
        ("HAN", "SGN", "2026-12-17"), ("HAN", "SGN", "2026-12-25"), ("SGN", "SGN", "2026-12-20"), ("XXX", "SGN", "2026-12-20"),
        ("HAN", "XXX", "2026-12-20"), ("SGN", "HAN", "2027-12-20"), ("HAN", "SGN", "2025-12-20"), ("han", "sgn", "2026-12-20")])))
    zero_bus = [k for k in KEYS if all(F.seats(f, "BUS") == 0 for f in FLIGHTS if (f["from"], f["to"], f["date"]) == k)]
    T.append(("edge_bus_all_zero", "".join(q(k, 1, "BUS") + "\n" for k in zero_bus[:60])))
    night = [f for f in FLIGHTS if f["arr"] < f["dep"]]
    T.append(("edge_overnight_flights", "".join(q((f["from"], f["to"], f["date"]), 1, "ECO") + "\n" for f in night)))
    first, last = FLIGHTS[0], FLIGHTS[-1]
    T.append(("edge_first_last_in_file", "".join(q((f["from"], f["to"], f["date"]), 1, c) + "\n" for f in (first, last) for c in ("ECO", "BUS"))))
    T.append(("edge_reverse_routes", "".join(q((k[1], k[0], k[2]), 2, "ECO") + "\n" for k in KEYS[:100])))
    T.append(("edge_all_airport_pairs_one_date", "".join(q((a, b, "2026-12-20"), 1, "ECO") + "\n" for a in AIRPORTS for b in AIRPORTS)))
    T.append(("edge_empty_input", ""))
    T.append(("edge_only_blank_lines", "\n\n\r\n\n"))
    T.append(("edge_single_query_no_newline", q(hub, 1, "ECO")))
    T.append(("stream_crlf", "".join(q(rng.choice(KEYS), 2, "ECO") + "\r\n" for _ in range(60)) + "\r\n" + q(hub, 3, "BUS") + "\r\n"))
    T.append(("stream_blank_lines_mixed", "".join((q(rng.choice(KEYS), rng.randint(1, 9), "ECO") if rng.random() < 0.6 else "") + "\n" for _ in range(200))))
    T.append(("stream_no_final_newline", "".join(q(rng.choice(KEYS), 1, "ECO") + "\n" for _ in range(20)) + q(hub, 2, "ECO")))
    T.append(("robust_same_query_20000", (q(("CXR", "DAD", "2026-12-20"), 1, "ECO") + "\n") * 20000))
    T.append(("robust_hub_every_pax_repeated", "".join(q(hub, p, c) + "\n" for _ in range(60) for p in range(1, 10) for c in ("ECO", "BUS"))))
    for i in range(4):
        T.append((f"stress_random_{i}", "".join(
            q(rng.choice(KEYS + [hub] * 20), rng.randint(1, 9), rng.choice(["ECO", "ECO", "BUS"])) + "\n" for _ in range(15000))))
    T.append(("stress_all_queries_every_pax", "".join(q(k, p, c) + "\n" for k in KEYS for p in range(1, 10) for c in ("ECO", "BUS"))))
    return T
