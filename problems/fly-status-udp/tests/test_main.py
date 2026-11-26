# Thiết kế: docs/TEST-DESIGN.md (mục UDP). Mô hình độc lập với lời giải.
import re
import time

import suite_fly as F
from njlib import WA, Fail, cases, group, sample, timeout

KEY = "fly2026"
MIN_RE = re.compile(r"^[1-9][0-9]{0,3}$", re.ASCII)


class Model:
    def __init__(self, fl):
        self.fl = fl
        self.st = {(f["code"], f["date"]): "ON_TIME" for f in fl}

    def run(self, data):
        if len(data) > 1000:
            return "ERROR"
        s = data.decode("latin-1")
        if s.endswith("\n"):
            s = s[:-1]
        if s.endswith("\r"):
            s = s[:-1]
        t = s.split(" ")
        if t[0] == "STATUS" and len(t) == 3:
            return self.st.get((t[1], t[2]), "NOT_FOUND")
        if t[0] == "SET" and len(t) in (5, 6):
            if len(t) == 5 and t[4] in ("ON_TIME", "CANCELLED"):
                new = t[4]
            elif len(t) == 6 and t[4] == "DELAYED" and MIN_RE.match(t[5]) and int(t[5]) <= 1440:
                new = f"DELAYED {int(t[5])}"
            else:
                return "ERROR"
            if t[1] != KEY:
                return "DENIED"
            if (t[2], t[3]) not in self.st:
                return "NOT_FOUND"
            self.st[(t[2], t[3])] = new
            return "OK"
        return "ERROR"


def setup(ctx):
    fl = F.parse_flights(ctx.read_file("flights.txt"))
    return fl, Model(fl)


def ask(u, m, data, timeout=1.5):
    raw = data if isinstance(data, bytes) else data.encode("utf-8")
    want = m.run(raw)
    u.send(raw)
    u.expect(want + "\n", timeout=timeout)
    return want


def setcmd(f, state, key=KEY):
    return f"SET {key} {f['code']} {f['date']} {state}"


# ---------------- sample ----------------

@sample
def test_status_initial(ctx):
    """Mọi chuyến trong tệp ban đầu ON_TIME; chuyến/ngày lạ → NOT_FOUND"""
    fl, m = setup(ctx)
    u = ctx.udp()
    for f in fl[:3]:
        ask(u, m, f"STATUS {f['code']} {f['date']}")
    ask(u, m, f"STATUS {fl[0]['code']} 2027-01-01")
    ask(u, m, "STATUS XX0000 2026-12-20")


@sample
def test_set_then_status(ctx):
    """SET đổi trạng thái, STATUS thấy ngay (DELAYED / CANCELLED / ON_TIME)"""
    fl, m = setup(ctx)
    u = ctx.udp()
    f = fl[0]
    for state in ["DELAYED 45", "CANCELLED", "DELAYED 1440", "ON_TIME"]:
        ask(u, m, setcmd(f, state))
        ask(u, m, f"STATUS {f['code']} {f['date']}")


@sample
def test_denied_notfound_error(ctx):
    """Sai khóa → DENIED; không có chuyến → NOT_FOUND; sai cú pháp → ERROR"""
    fl, m = setup(ctx)
    u = ctx.udp()
    f = fl[1]
    ask(u, m, setcmd(f, "CANCELLED", key="sai"))
    ask(u, m, f"SET {KEY} ZZ9999 2026-12-20 CANCELLED")
    ask(u, m, setcmd(f, "DELAYED 0"))
    ask(u, m, "PING")
    ask(u, m, f"STATUS {f['code']} {f['date']}")


# ---------------- basic ----------------

@group("basic")
def test_all_flights_initially_on_time(ctx):
    """Cả 47 chuyến đều ON_TIME lúc đầu"""
    fl, m = setup(ctx)
    u = ctx.udp()
    for f in fl:
        ask(u, m, f"STATUS {f['code']} {f['date']}")


@group("basic")
def test_states_are_independent(ctx):
    """Đổi một chuyến không ảnh hưởng chuyến khác"""
    fl, m = setup(ctx)
    u = ctx.udp()
    ask(u, m, setcmd(fl[2], "CANCELLED"))
    ask(u, m, setcmd(fl[3], "DELAYED 30"))
    for f in fl[:8]:
        ask(u, m, f"STATUS {f['code']} {f['date']}")


@group("basic")
def test_overwrite_sequence(ctx):
    """Đổi liên tiếp nhiều lần trên một chuyến"""
    fl, m = setup(ctx)
    u = ctx.udp()
    f = fl[4]
    for state in ["DELAYED 10", "DELAYED 20", "CANCELLED", "CANCELLED", "DELAYED 5", "ON_TIME", "ON_TIME", "DELAYED 1"]:
        ask(u, m, setcmd(f, state))
        ask(u, m, f"STATUS {f['code']} {f['date']}")


@group("basic")
def test_date_must_match(ctx):
    """Cùng mã chuyến nhưng ngày không có trong tệp → NOT_FOUND (cả STATUS lẫn SET)"""
    fl, m = setup(ctx)
    u = ctx.udp()
    f = fl[0]
    other = next(d for d in ("2026-12-20", "2026-12-21", "2026-12-22", "2026-12-23") if d != f["date"])
    ask(u, m, f"STATUS {f['code']} {other}")
    ask(u, m, f"SET {KEY} {f['code']} {other} CANCELLED")
    ask(u, m, f"STATUS {f['code']} {f['date']}")


@group("basic")
def test_reply_goes_to_sender(ctx):
    """Hai socket hỏi xen kẽ: mỗi phản hồi về đúng socket gửi"""
    fl, m = setup(ctx)
    a, b = ctx.udp("A"), ctx.udp("B")
    ask(a, m, setcmd(fl[0], "CANCELLED"))
    ask(b, m, f"STATUS {fl[0]['code']} {fl[0]['date']}")
    ask(b, m, setcmd(fl[1], "DELAYED 99"))
    ask(a, m, f"STATUS {fl[1]['code']} {fl[1]['date']}")
    a.expect_nothing(0.1)
    b.expect_nothing(0.1)


@group("basic")
@cases("status VN1 2026-12-20", "Status VN1 2026-12-20", "GET VN1 2026-12-20", "PING", "SET", "STATUS", "STATUS VN1",
       "STATUS VN1 2026-12-20 x", "set fly2026 VN1 2026-12-20 CANCELLED", "SET fly2026 VN1 2026-12-20 cancelled",
       "SET fly2026 VN1 2026-12-20 LATE", "SET fly2026 VN1 2026-12-20", "SET fly2026 VN1 2026-12-20 ON_TIME x",
       "SET fly2026 VN1 2026-12-20 CANCELLED 5", "SET fly2026 VN1 2026-12-20 DELAYED", "SET fly2026 VN1 2026-12-20 DELAYED 5 6",
       "SETX fly2026 VN1 2026-12-20 CANCELLED", "SE fly2026 VN1 2026-12-20 CANCELLED", "STATUSX VN1 2026-12-20",
       "STATUS  VN1 2026-12-20", " STATUS VN1 2026-12-20", "STATUS VN1 2026-12-20 ", "STATUS\tVN1 2026-12-20",
       title="Lệnh {0!r}")
def test_command_forms(ctx, line):
    fl, m = setup(ctx)
    u = ctx.udp()
    line = line.replace("VN1", fl[0]["code"]).replace("2026-12-20", fl[0]["date"])
    ask(u, m, line)
    ask(u, m, f"STATUS {fl[0]['code']} {fl[0]['date']}")


# ---------------- edge ----------------

@group("edge")
@cases("1", "2", "45", "1440", "1439", "0", "1441", "9999", "10000", "01", "001", "-5", "+5", "12a", "a12", "1.5", "1e2",
       "00", "0x10", "٣", " ", "", title="DELAYED phút = {0!r}")
def test_minutes_rules(ctx, minutes):
    fl, m = setup(ctx)
    u = ctx.udp()
    f = fl[5]
    ask(u, m, setcmd(f, f"DELAYED {minutes}"))
    ask(u, m, f"STATUS {f['code']} {f['date']}")


@group("edge")
@cases("fly2026", "fly202", "fly20266", "FLY2026", "Fly2026", "", "fly2026 ", "x", "fly2026\r", "fly-2026", "fly2025",
       title="Khóa {0!r}")
def test_key_exact(ctx, key):
    fl, m = setup(ctx)
    u = ctx.udp()
    f = fl[6]
    ask(u, m, setcmd(f, "CANCELLED", key=key))
    ask(u, m, f"STATUS {f['code']} {f['date']}")


@group("edge")
@cases(("fly2026", "VN1", "DELAYED 0", "ERROR"), ("bad", "VN1", "DELAYED 0", "ERROR"), ("bad", "ZZ9", "CANCELLED", "DENIED"),
       ("fly2026", "ZZ9", "CANCELLED", "NOT_FOUND"), ("fly2026", "ZZ9", "LATE", "ERROR"), ("bad", "ZZ9", "LATE", "ERROR"),
       ("bad", "VN1", "CANCELLED", "DENIED"), ("fly2026", "VN1", "CANCELLED", "OK"),
       title="Thứ tự kiểm tra SET: khóa={0!r} chuyến={1} trạng thái={2!r} → {3}")
def test_set_check_order(ctx, key, code, state, want):
    fl, m = setup(ctx)
    u = ctx.udp()
    f = fl[0]
    code = f["code"] if code == "VN1" else code
    got = ask(u, m, f"SET {key} {code} {f['date']} {state}")
    if got != want:
        raise Fail(WA, f"mô hình nội bộ lệch: {got!r} != {want!r}")
    ask(u, m, f"STATUS {f['code']} {f['date']}")


@group("edge")
@cases("\n", "\r\n", "\n\n", "\r\n\r\n", "\r", "\n\r", title="Kết thúc datagram {0!r}")
def test_line_endings(ctx, tail):
    fl, m = setup(ctx)
    u = ctx.udp()
    f = fl[0]
    ask(u, m, f"STATUS {f['code']} {f['date']}{tail}")
    ask(u, m, setcmd(f, "CANCELLED") + tail)
    ask(u, m, f"STATUS {f['code']} {f['date']}")


@group("edge")
def test_empty_datagram(ctx):
    """Datagram rỗng (0 byte) → ERROR, server vẫn sống"""
    fl, m = setup(ctx)
    u = ctx.udp()
    u.send(b"")
    u.expect("ERROR\n")
    ask(u, m, f"STATUS {fl[0]['code']} {fl[0]['date']}")


@group("edge")
@cases(990, 999, 1000, 1001, 1002, 1024, 1025, 2047, 2048, 2049, 4000, 65000, title="Datagram dài {0} byte")
def test_datagram_length(ctx, n):
    """≤ 1000 byte được xét như thường, dài hơn → ERROR; không tràn bộ đệm"""
    fl, m = setup(ctx)
    u = ctx.udp()
    pad = "X" * max(0, n - len("STATUS  2026-12-20"))
    ask(u, m, f"STATUS {pad} 2026-12-20")
    ask(u, m, f"STATUS {fl[0]['code']} {fl[0]['date']}")


# ---------------- robust ----------------

@group("robust")
def test_send_and_close_before_reply(ctx):
    """Client gửi lệnh rồi đóng socket trước khi nhận phản hồi: server không sập, lệnh vẫn được áp dụng"""
    fl, m = setup(ctx)
    for i in range(20):
        a = ctx.udp(f"gone{i}")
        line = setcmd(fl[i], "CANCELLED" if i % 2 else "DELAYED 7")
        m.run(line.encode())
        a.send(line)
        a.close()
        ctx.close_quietly(a)
    ctx.expect_alive()
    time.sleep(0.1)
    b = ctx.udp("B")
    for f in fl[:20]:
        ask(b, m, f"STATUS {f['code']} {f['date']}")


@group("robust")
def test_binary_garbage(ctx):
    """Byte lạ (không NUL) trong datagram"""
    fl, m = setup(ctx)
    u = ctx.udp()
    for junk in [b"\x01\x02\x03", b"\xff" * 30, b"STATUS \xff\xfe 2026-12-20", b"SET fly2026 \x80 \x81 CANCELLED", b"\x7f", b"\x1b[2J",
                 b"STATUS " + fl[0]["code"].encode() + b" " + fl[0]["date"].encode() + b"\xff"]:
        ask(u, m, junk)
    ask(u, m, f"STATUS {fl[0]['code']} {fl[0]['date']}")


@group("robust")
def test_flood_does_not_block_others(ctx):
    """Một client gửi dồn 300 lệnh mà không đọc phản hồi; client khác vẫn được phục vụ"""
    fl, m = setup(ctx)
    flood = ctx.udp("flood")
    for i in range(300):
        flood.send(f"STATUS {fl[i % len(fl)]['code']} {fl[i % len(fl)]['date']}")
    other = ctx.udp("other")
    ask(other, m, setcmd(fl[0], "CANCELLED"), timeout=2.0)
    ask(other, m, f"STATUS {fl[0]['code']} {fl[0]['date']}", timeout=2.0)


# ---------------- concurrency ----------------

@group("concurrency")
@timeout(15)
def test_five_clients_interleaved(ctx):
    """5 socket xen kẽ ngẫu nhiên SET/STATUS: thay đổi của một client thấy ngay ở client khác"""
    fl, m = setup(ctx)
    us = [ctx.udp(f"u{i}") for i in range(5)]
    for _ in range(400):
        u = ctx.rng.choice(us)
        f = ctx.rng.choice(fl[:12])
        if ctx.rng.random() < 0.4:
            line = setcmd(f, ctx.rng.choice(["ON_TIME", "CANCELLED", f"DELAYED {ctx.rng.randint(1, 1440)}"]))
        else:
            line = f"STATUS {f['code']} {f['date']}"
        ask(u, m, line)
    for u in us:
        u.expect_nothing(0.05)


# ---------------- stress ----------------

@group("stress")
@timeout(25)
def test_random_vs_model_3000(ctx):
    """3000 lệnh ngẫu nhiên (cả sai cú pháp) so với mô hình"""
    fl, m = setup(ctx)
    u = ctx.udp()
    rng = ctx.rng
    for _ in range(3000):
        f = rng.choice(fl)
        r = rng.random()
        if r < 0.35:
            line = f"STATUS {f['code']} {f['date']}"
        elif r < 0.7:
            line = setcmd(f, rng.choice(["ON_TIME", "CANCELLED", f"DELAYED {rng.randint(1, 1440)}"]))
        elif r < 0.8:
            line = setcmd(f, rng.choice(["DELAYED 0", "DELAYED 1441", "DELAYED 01", "LATE", "DELAYED", "ON_TIME x"]))
        elif r < 0.9:
            line = setcmd(f, "CANCELLED", key=rng.choice(["x", "fly202", "FLY2026", ""]))
        else:
            line = rng.choice(["PING", "", "STATUS", "STATUS a", "STATUS ZZ 2026-12-20", "SET", f"STATUS {f['code']} 2099-01-01"])
        ask(u, m, line)


@group("stress")
@timeout(25)
def test_pipelined_batches(ctx):
    """Gửi lô 20 datagram liền nhau rồi đọc 20 phản hồi (đúng thứ tự trên loopback)"""
    fl, m = setup(ctx)
    u = ctx.udp()
    rng = ctx.rng
    for _ in range(40):
        lines = []
        for _ in range(20):
            f = rng.choice(fl)
            lines.append(setcmd(f, rng.choice(["ON_TIME", "CANCELLED", f"DELAYED {rng.randint(1, 1440)}"])) if rng.random() < 0.5
                         else f"STATUS {f['code']} {f['date']}")
        wants = [m.run(x.encode()) for x in lines]
        for x in lines:
            u.send(x)
        for w in wants:
            got = u.recv(timeout=1.5).decode()
            if got != w + "\n":
                raise Fail(WA, f"mong đợi {w!r}, nhận được {got!r}")
