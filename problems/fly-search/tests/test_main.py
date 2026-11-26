# Thiết kế: docs/TEST-DESIGN.md. Mô hình: judge/runner/suite_fly.py (độc lập với lời giải).
import time

import suite_fly as F
from njlib import BLOCKED, WA, Fail, cases, group, sample, timeout


def flights(ctx):
    return F.parse_flights(ctx.read_file("flights.txt"))


def keys(fl):
    return sorted({(f["from"], f["to"], f["date"]) for f in fl})


def model(fl, line):
    """Phản hồi mong đợi (danh sách dòng) cho một dòng lệnh; None nếu server phải đóng kết nối sau phản hồi."""
    toks = F.split_line(line)
    name, a = toks[0], toks[1:]
    if line.rstrip("\r") == "":
        return ["999 UNKNOWN ERROR"]
    if name == "SEARCH":
        return F.search_reply(fl, a) if F.valid_search_args(a) else ["201 INVALID"]
    if name == "QUIT":
        return ["100 OK"] if not a else ["201 INVALID"]
    return ["999 UNKNOWN ERROR"]


def ask(c, fl, line, timeout=2.0):
    """Gửi một lệnh rồi so với mô hình."""
    c.send_line(line)
    for want in model(fl, line):
        got = c.recv_line(timeout=timeout)
        if got != want:
            raise Fail(WA, f"{c.name}: lệnh {line!r}: mong đợi {want!r}, nhận được {got!r}")


def pipeline(c, fl, lines, batch=40):
    """Gửi các lệnh theo lô (không để hai phía cùng chặn vì bộ đệm đầy) rồi so từng phản hồi."""
    for i in range(0, len(lines), batch):
        part = lines[i:i + batch]
        c.send("".join(x + "\n" for x in part))
        for line in part:
            for want in model(fl, line):
                got = c.recv_line(timeout=3.0)
                if got != want:
                    raise Fail(WA, f"{c.name}: lệnh {line!r}: mong đợi {want!r}, nhận được {got!r}")


def rand_query(rng, fl, bad=0.0):
    ks = keys(fl)
    k = rng.choice(ks)
    pax = rng.randint(1, 9)
    cls = rng.choice(["ECO", "BUS"])
    line = f"SEARCH {k[0]} {k[1]} {k[2]} {pax} {cls}"
    if rng.random() < 0.4:
        line += " " + rng.choice(["2026-12-20", "2026-12-21", "2026-12-22", k[2], "2026-12-19", "2027-01-01"])
    if rng.random() < bad:
        line = rng.choice([line.lower(), line + " x", line.replace("SEARCH ", "SEARCH  "), line.replace(" ECO", " eco"),
                           line.replace(k[0], k[1], 1), "SEARCH", " " + line, line + " ", "PING", "", "QUIT 1"])
    return line


def first_key(fl, n=1):
    from collections import Counter
    c = Counter((f["from"], f["to"], f["date"]) for f in fl)
    return [k for k, v in c.most_common() if v >= n][0]


# ---------------- sample ----------------

@sample
def test_search_one_way(ctx):
    """SEARCH một chiều: 110 FLIGHTS k rồi k dòng"""
    fl = flights(ctx)
    c = ctx.connect()
    k = first_key(fl, 2)
    ask(c, fl, f"SEARCH {k[0]} {k[1]} {k[2]} 1 ECO")
    ask(c, fl, f"SEARCH {k[0]} {k[1]} {k[2]} 9 BUS")


@sample
def test_search_round_trip(ctx):
    """SEARCH khứ hồi: thêm 111 RETURN m và m dòng"""
    fl = flights(ctx)
    c = ctx.connect()
    for a, b in [("HAN", "SGN"), ("SGN", "HAN"), ("DAD", "PQC")]:
        ask(c, fl, f"SEARCH {a} {b} 2026-12-20 1 ECO 2026-12-22")


@sample
def test_invalid_unknown_quit(ctx):
    """Sai cú pháp → 201, lệnh lạ → 999, QUIT → 100 OK rồi đóng"""
    fl = flights(ctx)
    c = ctx.connect()
    ask(c, fl, "SEARCH HAN SGN 2026-12-20 0 ECO")
    ask(c, fl, "PING")
    c.send_line("QUIT")
    c.expect_line("100 OK")
    c.expect_closed()


# ---------------- basic ----------------

@group("basic")
def test_every_key_every_class(ctx):
    """Mọi (đi, đến, ngày) × hạng × số khách 1/5/9 khớp mô hình"""
    fl = flights(ctx)
    c = ctx.connect()
    lines = [f"SEARCH {k[0]} {k[1]} {k[2]} {p} {cls}" for k in keys(fl) for cls in ("ECO", "BUS") for p in (1, 5, 9)]
    pipeline(c, fl, lines)


@group("basic")
def test_round_trip_every_pair(ctx):
    """Khứ hồi: mọi cặp sân bay, ngày về sau ngày đi"""
    fl = flights(ctx)
    c = ctx.connect()
    ap = sorted({f["from"] for f in fl})
    lines = [f"SEARCH {a} {b} {d1} 2 ECO {d2}" for a in ap for b in ap if a != b
             for d1, d2 in [("2026-12-20", "2026-12-21"), ("2026-12-21", "2026-12-22"), ("2026-12-22", "2026-12-22")]]
    pipeline(c, fl, lines)


@group("basic")
@cases("PING", "search HAN SGN 2026-12-20 1 ECO", "Search HAN SGN 2026-12-20 1 ECO", "LOGIN an 1234", "REGISTER an 1234",
       "SEARCHX", "QUITT", "quit", "BOOK VN213", "HELLO", "", "\t", " ", "SEARCH\tHAN SGN 2026-12-20 1 ECO",
       title="Lệnh lạ {0!r} → 999 UNKNOWN ERROR")
def test_unknown_commands(ctx, line):
    fl = flights(ctx)
    c = ctx.connect()
    ask(c, fl, line)
    ask(c, fl, "SEARCH HAN SGN 2026-12-20 1 ECO")


@group("basic")
def test_quit_with_args_is_invalid(ctx):
    """QUIT kèm tham số → 201 INVALID và kết nối còn dùng được"""
    fl = flights(ctx)
    c = ctx.connect()
    ask(c, fl, "QUIT now")
    ask(c, fl, "QUIT ")
    ask(c, fl, "SEARCH HAN SGN 2026-12-20 1 ECO")
    c.send_line("QUIT")
    c.expect_line("100 OK")
    c.expect_closed()


@group("basic")
def test_clients_are_independent(ctx):
    """Hai client hỏi xen kẽ vẫn nhận đúng phản hồi của mình"""
    fl = flights(ctx)
    a, b = ctx.connect("A"), ctx.connect("B")
    for i in range(30):
        ask(a, fl, rand_query(ctx.rng, fl))
        ask(b, fl, rand_query(ctx.rng, fl))


# ---------------- edge ----------------

@group("edge")
def test_no_results(ctx):
    """Không có chuyến → chỉ 110 FLIGHTS 0 (và 111 RETURN 0)"""
    fl = flights(ctx)
    c = ctx.connect()
    for line in ["SEARCH HAN SGN 2026-12-19 1 ECO", "SEARCH HAN SGN 2027-12-20 1 BUS", "SEARCH XXX SGN 2026-12-20 1 ECO",
                 "SEARCH HAN SGN 2026-12-20 1 ECO 2026-12-19", "SEARCH HAN SGN 2026-12-20 1 ECO 2030-01-01",
                 "SEARCH AAA ZZZ 2026-12-20 9 BUS 2026-12-21"]:
        ask(c, fl, line)


@group("edge")
def test_seats_exact_boundary(ctx):
    """Chuyến còn đúng s ghế: hỏi s khách thì có, s+1 khách thì không"""
    fl = flights(ctx)
    c = ctx.connect()
    lines = []
    for f in fl:
        for cls in ("ECO", "BUS"):
            s = F.seats(f, cls)
            for p in (s - 1, s, s + 1):
                if 1 <= p <= 9:
                    lines.append(f"SEARCH {f['from']} {f['to']} {f['date']} {p} {cls}")
    pipeline(c, fl, lines)


@group("edge")
def test_overnight_and_zero_bus(ctx):
    """Chuyến qua nửa đêm in nguyên giờ; hạng BUS hết ghế không xuất hiện"""
    fl = flights(ctx)
    c = ctx.connect()
    lines = [f"SEARCH {f['from']} {f['to']} {f['date']} 1 {cls}" for f in fl if f["arr"] < f["dep"] or f["bus_seats"] == 0
             for cls in ("ECO", "BUS")]
    pipeline(c, fl, lines)


@group("edge")
@cases(*[("SEARCH HAN SGN 2026-02-29 1 ECO",), ("SEARCH HAN SGN 2024-02-29 1 ECO",), ("SEARCH HAN SGN 2100-02-29 1 ECO",),
         ("SEARCH HAN SGN 2000-02-29 1 ECO",), ("SEARCH HAN SGN 1899-12-31 1 ECO",), ("SEARCH HAN SGN 2101-01-01 1 ECO",),
         ("SEARCH HAN HAN 2026-12-20 1 ECO",), ("SEARCH han SGN 2026-12-20 1 ECO",), ("SEARCH HAN SGN 2026-12-20 10 ECO",),
         ("SEARCH HAN SGN 2026-12-20 0 ECO",), ("SEARCH HAN SGN 2026-12-20 1 FIRST",),
         ("SEARCH HAN SGN 2026-12-20 1 ECO 2026-12-19",), ("SEARCH HAN SGN 2026-12-20 1 ECO 2026-12-20",),
         ("SEARCH HAN SGN 2026-12-20 1 ECO 2026-13-01",), ("SEARCH HAN SGN 2026-12-20 1 ECO x",),
         ("SEARCH HAN SGN 2026-12-20 1",), ("SEARCH HAN SGN 2026-12-20 1 ECO 2026-12-21 2026-12-22",),
         ("SEARCH HAN SGN 2026-12-20  1 ECO",), ("SEARCH HAN SGN 2026-12-20 1 ECO ",), ("SEARCH",),
         ("SEARCH HAN SGN 2026-12-00 1 ECO",), ("SEARCH HAN SGN 2026-00-10 1 ECO",), ("SEARCH HAN SGN 2026-12-20 1 ECOX",),
         ("SEARCH HAN SGN 2026-12-20 1 BUSS",), ("SEARCH HAN SGN 2026-12-20 1 EC",)],
       title="Luật cú pháp: {0!r}")
def test_syntax_rules(ctx, line):
    fl = flights(ctx)
    c = ctx.connect()
    ask(c, fl, line)
    ask(c, fl, "SEARCH HAN SGN 2026-12-20 1 ECO")


@group("edge")
@cases(255, 256, 511, 512, 999, title="Dòng lệnh dài {0} byte → 201, kết nối còn dùng được")
def test_long_line(ctx, n):
    fl = flights(ctx)
    c = ctx.connect()
    c.send("SEARCH " + "A" * (n - 7) + "\n")
    c.expect_line("201 INVALID", timeout=2.0)
    ask(c, fl, "SEARCH HAN SGN 2026-12-20 1 ECO")


# ---------------- stream ----------------

@group("stream")
def test_byte_by_byte(ctx):
    """Gửi từng byte một"""
    fl = flights(ctx)
    c = ctx.connect()
    for line in ["SEARCH HAN SGN 2026-12-20 2 ECO 2026-12-21", "PING", "SEARCH DAD PQC 2026-12-21 1 BUS"]:
        c.send_slowly(line + "\n", chunk=1, delay=0.001)
        for want in model(fl, line):
            c.expect_line(want)


@group("stream")
def test_random_chunks(ctx):
    """Cắt ngẫu nhiên 1–7 byte"""
    fl = flights(ctx)
    c = ctx.connect()
    lines = [rand_query(ctx.rng, fl, bad=0.2) for _ in range(40)]
    for line in lines:
        c.send_chunks(line + "\n", ctx.rng, delay=0)
        for want in model(fl, line):
            c.expect_line(want, timeout=2.0)


@group("stream")
def test_many_commands_one_send(ctx):
    """Hàng chục lệnh dính nhau trong một lần gửi"""
    fl = flights(ctx)
    c = ctx.connect()
    lines = [rand_query(ctx.rng, fl, bad=0.2) for _ in range(60)]
    c.send("".join(x + "\n" for x in lines))
    for line in lines:
        for want in model(fl, line):
            c.expect_line(want, timeout=2.0)


@group("stream")
def test_crlf(ctx):
    """Dòng kết thúc bằng \\r\\n"""
    fl = flights(ctx)
    c = ctx.connect()
    for line in ["SEARCH HAN SGN 2026-12-20 1 ECO", "SEARCH HAN SGN 2026-12-20 1 ECO 2026-12-21", "PING", "QUIT x", ""]:
        c.send(line + "\r\n")
        for want in model(fl, line):
            c.expect_line(want)
    c.send("QUIT\r\n")
    c.expect_line("100 OK")


@group("stream")
def test_split_at_newline(ctx):
    """Lệnh nằm ở hai mảnh: phần tên lệnh, rồi phần còn lại cùng ký tự xuống dòng"""
    fl = flights(ctx)
    c = ctx.connect()
    c.send("SEARCH HAN ")
    time.sleep(0.05)
    c.send("SGN 2026-12-20 1 ECO")
    time.sleep(0.05)
    c.expect_silence(0.1)
    c.send("\nSEARCH SGN HA")
    for want in model(fl, "SEARCH HAN SGN 2026-12-20 1 ECO"):
        c.expect_line(want)
    c.send("N 2026-12-20 1 ECO\n")
    for want in model(fl, "SEARCH SGN HAN 2026-12-20 1 ECO"):
        c.expect_line(want)


# ---------------- robust ----------------

@group("robust")
def test_reset_mid_command(ctx):
    """Client gửi dở lệnh rồi RST: server vẫn phục vụ client khác"""
    fl = flights(ctx)
    a = ctx.connect("A")
    a.send("SEARCH HAN SGN 2026-")
    a.reset()
    time.sleep(0.2)
    ctx.expect_alive()
    ask(ctx.connect("B"), fl, "SEARCH HAN SGN 2026-12-20 1 ECO 2026-12-21")


@group("robust")
def test_half_close_still_answered(ctx):
    """Client gửi lệnh rồi shutdown(SHUT_WR): vẫn phải nhận đủ phản hồi"""
    fl = flights(ctx)
    c = ctx.connect()
    c.send("SEARCH HAN SGN 2026-12-20 1 ECO 2026-12-21\n")
    c.shutdown_write()
    for want in model(fl, "SEARCH HAN SGN 2026-12-20 1 ECO 2026-12-21"):
        c.expect_line(want)
    c.expect_closed(timeout=2.0)


@group("robust")
def test_binary_garbage(ctx):
    """Byte lạ trong lệnh không làm server hỏng"""
    fl = flights(ctx)
    c = ctx.connect()
    for junk in [b"\x01\x02\x03", b"SEARCH \xff\xfe", b"\x80" * 50, b"SEARCH HAN SGN 2026-12-20 1 \xc3\xa9", b"\x7f"]:
        c.send(junk + b"\n")
        got = c.recv_line()
        if got not in ("201 INVALID", "999 UNKNOWN ERROR"):
            raise Fail(WA, f"byte lạ {junk!r}: nhận được {got!r}")
    ask(c, fl, "SEARCH HAN SGN 2026-12-20 1 ECO")


@group("robust")
@timeout(20)
def test_connect_disconnect_300(ctx):
    """300 lượt kết nối-ngắt (kiểu đóng khác nhau) không làm hết file descriptor"""
    fl = flights(ctx)
    for i in range(300):
        c = ctx.connect(f"c{i}")
        if i % 3 == 0:
            c.close()
        elif i % 3 == 1:
            c.reset()
        else:
            c.send_line("QUIT")
            c.expect_line("100 OK")
            c.close()
        ctx.close_quietly(c)
    ask(ctx.connect("last"), fl, "SEARCH HAN SGN 2026-12-20 1 ECO")


@group("robust")
def test_connect_and_say_nothing(ctx):
    """Client kết nối rồi im lặng/đóng không gửi gì"""
    fl = flights(ctx)
    for _ in range(5):
        ctx.connect().close()
    ask(ctx.connect(), fl, "SEARCH HAN SGN 2026-12-20 1 ECO")


# ---------------- concurrency ----------------

@group("concurrency")
def test_silent_client_does_not_block(ctx):
    """Client kết nối nhưng không gửi gì không chặn client khác"""
    fl = flights(ctx)
    idle = [ctx.connect(f"idle{i}") for i in range(5)]
    partial = ctx.connect("partial")
    partial.send("SEARCH HAN SG")
    with ctx.verdict(BLOCKED):
        ask(ctx.connect("active"), fl, "SEARCH HAN SGN 2026-12-20 1 ECO 2026-12-21")
    partial.send("N 2026-12-20 1 ECO\n")
    for want in model(fl, "SEARCH HAN SGN 2026-12-20 1 ECO"):
        partial.expect_line(want)
    del idle


@group("concurrency")
def test_30_clients_interleaved(ctx):
    """30 client cùng lúc, lệnh xen kẽ ngẫu nhiên, mỗi client nhận đúng phản hồi của mình"""
    fl = flights(ctx)
    cs = [ctx.connect(f"c{i}") for i in range(30)]
    pending = []
    for step in range(120):
        c = ctx.rng.choice(cs)
        line = rand_query(ctx.rng, fl, bad=0.1)
        if line.strip() == "QUIT":
            line = "PING"
        c.send_line(line)
        pending.append((c, line))
        if len(pending) >= 25:
            for cc, ll in pending:
                for want in model(fl, ll):
                    cc.expect_line(want, timeout=3.0)
            pending = []
    for cc, ll in pending:
        for want in model(fl, ll):
            cc.expect_line(want, timeout=3.0)


# ---------------- stress ----------------

@group("stress")
@timeout(25)
def test_random_vs_model_2000(ctx):
    """2000 lệnh ngẫu nhiên (cả sai cú pháp) so với mô hình"""
    fl = flights(ctx)
    c = ctx.connect()
    lines = [rand_query(ctx.rng, fl, bad=0.2) for _ in range(2000)]
    lines = [x if x.strip() != "QUIT" else "PING" for x in lines]
    pipeline(c, fl, lines, batch=50)


@group("stress")
@timeout(25)
def test_three_clients_parallel(ctx):
    """3 client mỗi bên 600 lệnh gửi theo lô xen kẽ"""
    fl = flights(ctx)
    cs = [ctx.connect(f"c{i}") for i in range(3)]
    plans = [[x if x.strip() != "QUIT" else "PING" for x in (rand_query(ctx.rng, fl, bad=0.1) for _ in range(600))] for _ in cs]
    for i in range(0, 600, 30):
        for c, plan in zip(cs, plans):
            c.send("".join(x + "\n" for x in plan[i:i + 30]))
        for c, plan in zip(cs, plans):
            for line in plan[i:i + 30]:
                for want in model(fl, line):
                    c.expect_line(want, timeout=3.0)
