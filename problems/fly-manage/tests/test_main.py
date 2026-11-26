# Thiết kế: docs/TEST-DESIGN.md. Mô hình độc lập; giờ hiện tại do tham số dòng lệnh quyết định (nhiều giá trị khác nhau).
import time
from datetime import datetime

import suite_fly as F
from njlib import BLOCKED, WA, Fail, args, cases, group, sample, timeout

PW = {"an": "1234", "binh": "abcd", "chi": "pass99"}
NOW0 = ("2026-12-01", "08:00")
FEE = 200000


def dt(date, hhmm):
    return datetime.strptime(f"{date} {hhmm}", "%Y-%m-%d %H:%M")


class Model:
    def __init__(self, ctx, now=NOW0):
        self.now = dt(*now)
        self.now_s = now
        self.fl = {f["code"]: dict(f) for f in F.parse_flights(ctx.read_file("flights.txt"))}
        self.bal = {}
        for ln in ctx.read_file("wallets.txt").splitlines():
            u, v = ln.split()
            self.bal[u] = int(v)
        self.t = []
        for ln in ctx.read_file("tickets.txt").splitlines():
            no, user, code, date, cls, pax, price, status = ln.split(" ")
            self.t.append({"no": no, "user": user, "flight": code, "cls": cls, "pax": pax, "price": int(price), "cancelled": status == "CANCELLED"})
        self.sessions = {}

    def left(self, code):
        f = self.fl[code]
        return int((dt(f["date"], f["dep"]) - self.now).total_seconds() // 60)

    def seatkey(self, cls):
        return "eco_seats" if cls == "ECO" else "bus_seats"

    def pricekey(self, cls):
        return "eco_price" if cls == "ECO" else "bus_price"

    def pick(self, sid, a, need):
        u = self.sessions.get(sid)
        if len(a) != need:
            return "201 INVALID", None
        t = next((x for x in self.t if x["no"] == a[0]), None)
        if t is None:
            return "202 NOT FOUND", None
        if t["user"] != u:
            return "203 DENIED", None
        return None, t

    def run(self, sid, line):
        """Danh sách phần tử trả lời: str = một dòng, bytes = dữ liệu thô."""
        toks = F.split_line(line)
        name, a = toks[0], toks[1:]
        u = self.sessions.get(sid)
        if name == "LOGIN":
            if not F.valid_account_args(a):
                return ["201 INVALID"]
            if u:
                return ["207 ALREADY LOGGED IN"]
            if PW.get(a[0]) != a[1]:
                return ["203 DENIED"]
            self.sessions[sid] = a[0]
            return [f"100 OK {a[0]}"]
        if name == "QUIT" and not a:
            self.sessions.pop(sid, None)
            return ["100 OK"]
        if name == "SEATS":
            if len(a) != 1:
                return ["201 INVALID"]
            f = self.fl.get(a[0])
            return [f"100 OK {f['eco_seats']} {f['bus_seats']}"] if f else ["202 NOT FOUND"]
        if name not in ("BALANCE", "MYTICKETS", "VIEW", "CANCEL", "CHANGE", "PRINT"):
            return ["999 UNKNOWN ERROR"]
        if u is None:
            return ["204 LOGIN FIRST"]
        if name == "BALANCE":
            return [f"100 OK {self.bal[u]}"] if not a else ["201 INVALID"]
        if name == "MYTICKETS":
            if a:
                return ["201 INVALID"]
            mine = [x for x in self.t if x["user"] == u]
            return [f"110 TICKETS {len(mine)}"] + [
                f"{x['no']} {x['flight']} {self.fl[x['flight']]['date']} {x['cls']} {x['pax']} {x['price']} {'CANCELLED' if x['cancelled'] else 'PAID'}"
                for x in mine]
        err, t = self.pick(sid, a, 2 if name == "CHANGE" else 1)
        if err:
            return [err]
        f = self.fl[t["flight"]]
        if name == "VIEW":
            return [f"100 OK {t['no']} {t['flight']} {f['date']} {t['cls']} {t['pax']} {t['price']} {'CANCELLED' if t['cancelled'] else 'PAID'} "
                    f"{f['dep']} {f['arr']}"]
        if name == "PRINT":
            body = (f"===== VE DIEN TU =====\nSo ve: {t['no']}\nHanh khach: {t['pax']}\nChuyen bay: {t['flight']} {f['from']} -> {f['to']}\n"
                    f"Ngay: {f['date']} {f['dep']} - {f['arr']}\nHang: {t['cls']}\nGia ve: {t['price']}\n"
                    f"Trang thai: {'CANCELLED' if t['cancelled'] else 'PAID'}\nIn luc: {self.now_s[0]} {self.now_s[1]}\n").encode()
            return [f"120 FILE {len(body)}", body]
        if name == "CANCEL":
            if t["cancelled"]:
                return ["209 ALREADY CANCELLED"]
            left = self.left(t["flight"])
            if left <= 0:
                return ["210 TOO LATE"]
            pct = 90 if left >= 72 * 60 else 70 if left >= 24 * 60 else 30
            refund = t["price"] * pct // 100
            self.bal[u] += refund
            f[self.seatkey(t["cls"])] += 1
            t["cancelled"] = True
            return [f"100 OK REFUNDED {refund}"]
        # CHANGE
        if t["cancelled"]:
            return ["209 ALREADY CANCELLED"]
        if a[1] == t["flight"]:
            return ["201 INVALID"]
        if self.left(t["flight"]) < 180:
            return ["210 TOO LATE"]
        nf = self.fl.get(a[1])
        if nf is None:
            return ["202 NOT FOUND"]
        if (nf["from"], nf["to"]) != (f["from"], f["to"]):
            return ["211 DIFFERENT ROUTE"]
        if self.left(a[1]) <= 0:
            return ["210 TOO LATE"]
        if nf[self.seatkey(t["cls"])] < 1:
            return ["205 NO SEATS"]
        delta = nf[self.pricekey(t["cls"])] - t["price"] + FEE
        if delta > self.bal[u]:
            return ["206 PAYMENT FAILED"]
        self.bal[u] -= delta
        f[self.seatkey(t["cls"])] += 1
        nf[self.seatkey(t["cls"])] -= 1
        t["flight"] = a[1]
        t["price"] = nf[self.pricekey(t["cls"])]
        return [f"100 OK CHANGED {t['no']} {delta}"]


def hello(ctx, name=None):
    return ctx.connect(name=name)


def ask(c, m, sid, line, timeout=2.0):
    want = m.run(sid, line)
    c.send_line(line)
    for w in want:
        if isinstance(w, bytes):
            c.expect_bytes(w, timeout=timeout)
        else:
            got = c.recv_line(timeout=timeout)
            if got != w:
                raise Fail(WA, f"{c.name}: lệnh {line!r}: mong đợi {w!r}, nhận được {got!r}")
    return want


def login(ctx, m, sid, user):
    c = hello(ctx, f"{user}{sid}")
    ask(c, m, sid, f"LOGIN {user} {PW[user]}")
    return c


def T(n):
    return f"73800000{n:05d}"


# ---------------- sample ----------------

@sample
def test_mytickets_and_view(ctx):
    """MYTICKETS liệt kê mọi vé của tài khoản (kể cả đã hủy); VIEW xem chi tiết; vé người khác → 203"""
    m = Model(ctx)
    c = login(ctx, m, 1, "an")
    for line in ["MYTICKETS", f"VIEW {T(1)}", f"VIEW {T(11)}", f"VIEW {T(12)}", "VIEW 123", "VIEW", "BALANCE"]:
        ask(c, m, 1, line)


@sample
def test_cancel_refund_tiers(ctx):
    """CANCEL hoàn 90% / 70% / 30% tùy thời gian còn lại; đã khởi hành → 210"""
    m = Model(ctx)
    c = login(ctx, m, 1, "an")
    for n in [1, 2, 3, 4, 5, 6, 7, 1, 11]:
        ask(c, m, 1, f"CANCEL {T(n)}")
    ask(c, m, 1, "BALANCE")
    ask(c, m, 1, "SEATS VN501")


@sample
def test_change_and_print(ctx):
    """CHANGE đổi sang chuyến cùng chặng (có phí), PRINT gửi nội dung có độ dài"""
    m = Model(ctx)
    c = login(ctx, m, 1, "an")
    for line in [f"CHANGE {T(2)} VN510", "BALANCE", "SEATS VN502", "SEATS VN510", f"PRINT {T(2)}", f"VIEW {T(2)}"]:
        ask(c, m, 1, line)


# ---------------- basic ----------------

@group("basic")
@cases(*[(n,) for n in range(1, 16)], title="CANCEL vé {0} ở giờ mặc định (2026-12-01 08:00)")
def test_cancel_every_ticket(ctx, n):
    m = Model(ctx)
    c = login(ctx, m, 1, "an")
    ask(c, m, 1, f"CANCEL {T(n)}")
    ask(c, m, 1, "BALANCE")
    code = next(x["flight"] for x in m.t if x["no"] == T(n))
    ask(c, m, 1, f"SEATS {code}")
    ask(c, m, 1, f"CANCEL {T(n)}")


@group("basic")
@cases((2, "VN510"), (2, "VN512"), (2, "VN511"), (2, "VN513"), (2, "VN514"), (2, "VN999"), (2, "VN502"), (8, "VN510"), (9, "VN510"),
       (5, "VN510"), (6, "VN510"), (10, "VN512"), (10, "VN511"), (10, "VN510"), (11, "VN510"), (1, "VN515"), (1, "VN516"), (13, "VN510"), (12, "VN512"),
       title="CHANGE vé {0} sang {1}")
def test_change_cases(ctx, n, new):
    m = Model(ctx)
    user = "binh" if n in (12, 13) else "an"
    c = login(ctx, m, 1, user)
    ask(c, m, 1, f"CHANGE {T(n)} {new}")
    ask(c, m, 1, "BALANCE")
    ask(c, m, 1, "MYTICKETS")
    for code in ("VN501", "VN502", "VN510", "VN511", "VN512", "VN515", "VN516"):
        ask(c, m, 1, f"SEATS {code}")


@group("basic")
def test_change_payment_failed_then_ok(ctx):
    """Ví không đủ → 206 (không đổi gì); đủ tiền thì thành công; hoàn tiền khi chuyến mới rẻ hơn"""
    m = Model(ctx)
    c = login(ctx, m, 1, "an")
    for line in [f"CHANGE {T(2)} VN510", f"CHANGE {T(1)} VN515", "BALANCE", f"CANCEL {T(10)}", f"CHANGE {T(1)} VN515", "BALANCE", "MYTICKETS"]:
        ask(c, m, 1, line)
    c2 = login(ctx, m, 2, "binh")
    for line in [f"CHANGE {T(12)} VN512", "BALANCE", f"CHANGE {T(13)} VN512", "BALANCE"]:
        ask(c2, m, 2, line)


@group("basic")
@cases(*[(n,) for n in range(1, 16)], title="PRINT vé {0}: 120 FILE n + đúng n byte")
def test_print_every_ticket(ctx, n):
    m = Model(ctx)
    c = login(ctx, m, 1, "an")
    ask(c, m, 1, f"PRINT {T(n)}")
    ask(c, m, 1, "BALANCE")


@group("basic")
def test_not_logged_in(ctx):
    """Lệnh cần đăng nhập → 204 (trước cả cú pháp); SEATS không cần"""
    m = Model(ctx)
    c = hello(ctx)
    for line in ["BALANCE", "BALANCE x", "MYTICKETS", "VIEW", f"VIEW {T(1)}", "CANCEL", f"CHANGE {T(1)} VN510", "PRINT x y z", "SEATS VN501",
                 "SEATS VN999", "SEATS", "PING", "", "login an 1234", f"LOGIN an 12", "LOGIN an 12345", "LOGIN chi pass99", "BALANCE"]:
        ask(c, m, 1, line)


@group("basic")
def test_two_sessions_share_tickets_and_wallet(ctx):
    """Hai phiên cùng tài khoản thấy thay đổi của nhau; phiên tài khoản khác thì không"""
    m = Model(ctx)
    a1, a2, b = login(ctx, m, 1, "an"), login(ctx, m, 2, "an"), login(ctx, m, 3, "binh")
    for c, sid, line in [(a1, 1, f"CANCEL {T(1)}"), (a2, 2, "BALANCE"), (a2, 2, f"VIEW {T(1)}"), (b, 3, f"VIEW {T(1)}"), (b, 3, "MYTICKETS"),
                         (a2, 2, f"CANCEL {T(1)}"), (a1, 1, f"CHANGE {T(2)} VN510"), (a2, 2, f"VIEW {T(2)}"), (b, 3, "SEATS VN501")]:
        ask(c, m, sid, line)


@group("basic")
def test_unknown_and_syntax(ctx):
    """Lệnh lạ 999; thiếu/thừa thành phần 201"""
    m = Model(ctx)
    c = login(ctx, m, 1, "an")
    for line in ["PING", "", " ", "view " + T(1), "VIEW  " + T(1), f"VIEW {T(1)} x", "CANCEL", f"CANCEL {T(1)} x", "CHANGE", f"CHANGE {T(2)}",
                 f"CHANGE {T(2)} VN510 x", "PRINT", f"PRINT {T(1)} x", "MYTICKETS x", "BALANCE x", "SEATS", "SEATS A B", "QUIT now", "LOGIN an 1234",
                 "BALANCE"]:
        ask(c, m, 1, line)


# ---------------- edge: nhiều giá trị giờ hiện tại ----------------

def sweep(ctx, now):
    m = Model(ctx, now)
    c = login(ctx, m, 1, "an")
    for n in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 14, 15]:
        ask(c, m, 1, f"CANCEL {T(n)}")
    ask(c, m, 1, "BALANCE")
    d = login(ctx, m, 2, "binh")
    for n in [12, 13]:
        ask(d, m, 2, f"CHANGE {T(n)} VN512")
        ask(d, m, 2, f"CANCEL {T(n)}")
    ask(d, m, 2, "BALANCE")
    ask(d, m, 2, f"PRINT {T(12)}")


NOWS = [("2026-12-03", "08:00"), ("2026-12-03", "07:59"), ("2026-12-03", "08:01"), ("2026-12-01", "08:01"), ("2026-12-01", "07:59"),
        ("2026-12-04", "08:00"), ("2026-12-04", "07:59"), ("2026-12-04", "08:01"), ("2026-11-28", "08:00"), ("2026-11-30", "23:59"),
        ("2026-12-01", "05:00"), ("2026-12-01", "00:00"), ("2026-12-02", "08:00"), ("2026-12-02", "07:59"), ("2026-12-10", "05:00"),
        ("2026-12-10", "06:00"), ("2026-12-11", "00:00"), ("2025-12-31", "23:00"), ("2024-02-29", "12:00"), ("2026-02-28", "23:59"),
        ("2026-12-31", "23:59"), ("2027-01-01", "00:00"), ("2028-02-27", "08:00"), ("2028-02-27", "07:59"), ("2028-02-29", "08:00"),
        ("2027-02-26", "08:00"), ("2027-02-26", "07:59"), ("2027-03-01", "08:00")]


def _mk(now):
    def fn(ctx):
        sweep(ctx, now)
    return fn


for _i, _now in enumerate(NOWS):
    _f = _mk(_now)
    _f.__name__ = f"test_now_args_{_i:02d}"
    _f.__doc__ = f"Server khởi động với giờ {_now[0]} {_now[1]}: hủy/đổi/in mọi vé khớp mô hình"
    _f = args("{port}", _now[0], _now[1])(_f)
    _f = group("edge")(_f)
    globals()[_f.__name__] = _f


# ---------------- stream ----------------

@group("stream")
def test_byte_by_byte(ctx):
    """Lệnh gửi từng byte; nội dung vé được đọc đủ"""
    m = Model(ctx)
    c = hello(ctx)
    for line in ["LOGIN an 1234", f"PRINT {T(1)}", f"CANCEL {T(1)}"]:
        want = m.run(1, line)
        c.send_slowly(line + "\n", chunk=1, delay=0.001)
        for w in want:
            c.expect_bytes(w, timeout=2.0) if isinstance(w, bytes) else c.expect_line(w, timeout=2.0)


@group("stream")
def test_many_commands_one_send(ctx):
    """Hàng chục lệnh dính nhau trong một lần gửi, gồm cả PRINT"""
    m = Model(ctx)
    c = hello(ctx)
    lines = ["LOGIN an 1234"] + [f"PRINT {T(1)}", "BALANCE", f"VIEW {T(2)}", "MYTICKETS", f"CANCEL {T(1)}", f"PRINT {T(1)}"] * 4
    c.send("".join(x + "\n" for x in lines))
    for line in lines:
        for w in m.run(1, line):
            c.expect_bytes(w, timeout=3.0) if isinstance(w, bytes) else c.expect_line(w, timeout=3.0)


@group("stream")
def test_crlf_and_chunks(ctx):
    """\\r\\n và cắt ngẫu nhiên 1–7 byte"""
    m = Model(ctx)
    c = hello(ctx)
    for line in ["LOGIN an 1234", f"VIEW {T(3)}", f"CHANGE {T(2)} VN512", "BALANCE", ""]:
        want = m.run(1, line)
        if ctx.rng.random() < 0.5:
            c.send(line + "\r\n")
        else:
            c.send_chunks(line + "\n", ctx.rng, delay=0)
        for w in want:
            c.expect_bytes(w, timeout=2.0) if isinstance(w, bytes) else c.expect_line(w, timeout=2.0)


# ---------------- robust ----------------

@group("robust")
def test_binary_garbage(ctx):
    """Byte lạ không làm hỏng server"""
    m = Model(ctx)
    c = login(ctx, m, 1, "an")
    for junk in [b"\x01\x02", b"VIEW \xff\xfe", b"CANCEL \x80", b"\x7f", b"CHANGE \xff \xfe"]:
        c.send(junk + b"\n")
        got = c.recv_line()
        if got not in ("201 INVALID", "202 NOT FOUND", "999 UNKNOWN ERROR"):
            raise Fail(WA, f"byte lạ {junk!r}: nhận {got!r}")
    ask(c, m, 1, "BALANCE")


@group("robust")
@timeout(25)
def test_300_sessions(ctx):
    """300 phiên đăng nhập rồi đóng/RST sau khi đọc hết phản hồi: không rò fd; dữ liệu còn nguyên"""
    m = Model(ctx)
    for i in range(300):
        c = hello(ctx, f"c{i}")
        c.send_line("LOGIN an 1234")
        c.expect_line("100 OK an")
        c.send_line("BALANCE")
        c.expect_line("100 OK 1000000")
        c.reset() if i % 2 else c.close()
        ctx.close_quietly(c)
        time.sleep(0.003)
    c = login(ctx, m, 1, "an")
    ask(c, m, 1, "MYTICKETS")


@group("robust")
def test_client_leaves_during_print(ctx):
    """Client đóng ngay sau lệnh PRINT (chưa đọc nội dung): server không sập"""
    m = Model(ctx)
    c = login(ctx, m, 1, "an")
    c.send(f"PRINT {T(1)}\n" * 5)
    c.reset()
    time.sleep(0.3)
    ctx.expect_alive()
    d = login(ctx, m, 2, "binh")
    ask(d, m, 2, "BALANCE")


# ---------------- concurrency ----------------

@group("concurrency")
def test_race_cancel_same_ticket(ctx):
    """Hai phiên cùng CANCEL một vé: hoàn tiền và trả ghế đúng một lần"""
    m = Model(ctx)
    a1, a2 = login(ctx, m, 1, "an"), login(ctx, m, 2, "an")
    a1.send_line(f"CANCEL {T(1)}")
    a2.send_line(f"CANCEL {T(1)}")
    got = sorted([a1.recv_line(timeout=2.0), a2.recv_line(timeout=2.0)])
    if got != ["100 OK REFUNDED 900000", "209 ALREADY CANCELLED"]:
        raise Fail(WA, f"hai CANCEL đồng thời cho {got!r}")
    m.run(1, f"CANCEL {T(1)}")
    ask(a1, m, 1, "BALANCE")
    ask(a1, m, 1, "SEATS VN501")


@group("concurrency")
def test_race_change_last_seat(ctx):
    """Hai tài khoản cùng CHANGE sang chuyến chỉ còn 1 ghế (VN515): đúng một người thành công"""
    m = Model(ctx)
    a, b = login(ctx, m, 1, "an"), login(ctx, m, 2, "binh")
    a.send_line(f"CHANGE {T(1)} VN515")
    b.send_line(f"CHANGE {T(13)} VN515")
    got = [a.recv_line(timeout=2.0), b.recv_line(timeout=2.0)]
    oks = [g for g in got if g.startswith("100 OK CHANGED")]
    if len(oks) != 1 or "205 NO SEATS" not in got:
        raise Fail(WA, f"hai CHANGE đồng thời cho {got!r}")
    a.send_line("SEATS VN515")
    a.expect_line("100 OK 0 0")


@group("concurrency")
def test_idle_client_does_not_block(ctx):
    """Client im lặng/gửi dở lệnh không chặn client khác"""
    m = Model(ctx)
    idle = [hello(ctx, f"idle{i}") for i in range(4)]
    idle[0].send("LOGIN an 12")
    with ctx.verdict(BLOCKED):
        c = login(ctx, m, 1, "binh")
        ask(c, m, 1, f"PRINT {T(12)}")
    idle[0].send("34\n")
    idle[0].expect_line("100 OK an")


# ---------------- stress ----------------

@group("stress")
@timeout(40)
def test_random_ops_vs_model(ctx):
    """1000 thao tác ngẫu nhiên của 3 phiên (xem, hủy, đổi, in, hỏi ghế) so với mô hình"""
    rng = ctx.rng
    m = Model(ctx)
    users = {1: "an", 2: "binh", 3: "an"}
    cs = {sid: login(ctx, m, sid, u) for sid, u in users.items()}
    nos = [T(n) for n in range(1, 16)] + [T(99), "x"]
    flights = sorted(m.fl)
    for step in range(1000):
        sid = rng.choice(list(users))
        r = rng.random()
        no = rng.choice(nos)
        if r < 0.2:
            line = f"CANCEL {no}"
        elif r < 0.45:
            line = f"CHANGE {no} {rng.choice(flights + ['VN999'])}"
        elif r < 0.6:
            line = f"PRINT {no}"
        elif r < 0.75:
            line = f"VIEW {no}"
        elif r < 0.85:
            line = "MYTICKETS"
        elif r < 0.92:
            line = "BALANCE"
        elif r < 0.97:
            line = f"SEATS {rng.choice(flights)}"
        else:
            line = rng.choice(["PING", "VIEW", "CANCEL a b", ""])
        ask(cs[sid], m, sid, line, timeout=2.5)
