# Thiết kế: docs/TEST-DESIGN.md. Phần "tối đa N client" dùng chung: judge/runner/suites.py (maxn_suite).
import time

import suite_fly as F
from njlib import BLOCKED, WA, Fail, args, cases, group, sample, timeout
from suites import maxn_suite

globals().update(maxn_suite(welcome="WELCOME", full="FULL", quit=("QUIT", "BYE"), ping=("BALANCE", None)))

PW = {"an": "1234", "binh": "abcd", "chi": "pass99", "dung": "x1y2z3", "eva": "eva123"}
D = "2026-12-20"


def hello(ctx, name=None):
    c = ctx.connect(name=name)
    c.expect_line("WELCOME", timeout=1.5)
    return c


def login(ctx, user="an", name=None):
    c = hello(ctx, name or user)
    c.send_line(f"LOGIN {user} {PW[user]}")
    c.expect_line(f"OK {user}")
    return c


class Model:
    """Mô hình chuẩn của cả server (nhiều phiên dùng chung dữ liệu)."""

    def __init__(self, ctx):
        self.fl = F.parse_flights(ctx.read_file("flights.txt"))
        self.seats = {(f["code"], f["date"]): f["eco_seats"] for f in self.fl}
        self.price = {(f["code"], f["date"]): f["eco_price"] for f in self.fl}
        self.acc = {}
        for ln in ctx.read_file("accounts.txt").splitlines():
            u, p = ln.split()
            self.acc[u] = p
        self.bal = {}
        for ln in ctx.read_file("wallets.txt").splitlines():
            u, v = ln.split()
            self.bal[u] = int(v)
        self.tickets = {}  # id -> (user, key)
        self.next_id = 1

    def run(self, s, line):
        """s: dict phiên {'user': ...}. Trả về danh sách dòng phản hồi, hoặc None nếu đóng (sau 'BYE')."""
        t = F.split_line(line)
        name, a = t[0], t[1:]
        if name == "LOGIN" and len(a) == 2:
            if self.acc.get(a[0]) == a[1]:
                s["user"] = a[0]
                return [f"OK {a[0]}"]
            return ["FAIL"]
        if name == "SEARCH" and len(a) == 3:
            res = [f"{f['code']} {f['dep']} {f['arr']} {f['eco_price']}" for f in self.fl
                   if f["from"] == a[0] and f["to"] == a[1] and f["date"] == a[2] and self.seats[(f["code"], f["date"])] >= 1]
            return [f"FLIGHTS {len(res)}"] + res
        if name == "QUIT" and not a:
            return ["BYE"]
        if name in ("BOOK", "MYTICKETS", "CANCEL", "BALANCE") and s["user"] is None:
            return ["LOGIN_FIRST"]
        u = s["user"]
        if name == "BOOK" and len(a) == 2:
            key = (a[0], a[1])
            if key not in self.seats:
                return ["NOT_FOUND"]
            if self.seats[key] < 1:
                return ["NO_SEATS"]
            if self.bal[u] < self.price[key]:
                return ["NO_MONEY"]
            self.seats[key] -= 1
            self.bal[u] -= self.price[key]
            tid = self.next_id
            self.next_id += 1
            self.tickets[tid] = (u, key)
            return [f"TICKET T{tid:04d}"]
        if name == "MYTICKETS" and not a:
            mine = [(i, k) for i, (o, k) in sorted(self.tickets.items()) if o == u]
            return [f"TICKETS {len(mine)}"] + [f"T{i:04d} {k[0]} {k[1]}" for i, k in mine]
        if name == "CANCEL" and len(a) == 1:
            tid = None
            if len(a[0]) == 5 and a[0][0] == "T" and a[0][1:].isascii() and a[0][1:].isdigit():
                tid = int(a[0][1:])
            if tid not in self.tickets:
                return ["NOT_FOUND"]
            owner, key = self.tickets[tid]
            if owner != u:
                return ["NOT_YOURS"]
            del self.tickets[tid]
            self.seats[key] += 1
            self.bal[u] += self.price[key]
            return [f"REFUNDED {self.price[key]}"]
        if name == "BALANCE" and not a:
            return [f"BALANCE {self.bal[u]}"]
        return ["ERROR"]


def ask(c, m, s, line, timeout=2.0):
    want = m.run(s, line)
    c.send_line(line)
    for w in want:
        got = c.recv_line(timeout=timeout)
        if got != w:
            raise Fail(WA, f"{c.name}: lệnh {line!r}: mong đợi {w!r}, nhận được {got!r}")
    return want


def sess():
    return {"user": None}


# ---------------- sample ----------------

@sample
@args("{port}", "2")
def test_example(ctx):
    """Ví dụ trong đề"""
    m = Model(ctx)
    a, b = hello(ctx, "A"), hello(ctx, "B")
    sa, sb = sess(), sess()
    ask(a, m, sa, f"BOOK VN001 {D}")
    ask(a, m, sa, "LOGIN an 1234")
    ask(a, m, sa, f"SEARCH HAN SGN {D}")
    ask(a, m, sa, f"BOOK VN001 {D}")
    ask(b, m, sb, "LOGIN an 1234")
    ask(b, m, sb, "MYTICKETS")
    from njlib import LIMIT
    with ctx.verdict(LIMIT):
        ctx.connect(name="C").expect_line("FULL")
    ask(a, m, sa, "CANCEL T0001")
    ask(b, m, sb, "MYTICKETS")


@sample
def test_errors(ctx):
    """LOGIN_FIRST, NOT_FOUND, NO_SEATS, NO_MONEY, ERROR"""
    m = Model(ctx)
    c = hello(ctx)
    s = sess()
    for line in ["BALANCE", "MYTICKETS", "CANCEL T0001", f"BOOK VN002 {D}", "LOGIN an 12", "LOGIN chi pass99", "BOOK ZZ9 2026-12-20",
                 f"BOOK VN002 {D}", f"BOOK VN002 {D}", f"BOOK VN001 2026-12-21", "PING", "CANCEL T0009"]:
        ask(c, m, s, line)
    ask(c, m, s, "LOGIN an 1234")
    for line in [f"BOOK VN002 {D}", f"BOOK VN002 {D}", "BOOK ZZ9 2026-12-20", "CANCEL T0099", "BOOK x"]:
        ask(c, m, s, line)


@sample
def test_cancel_and_tickets(ctx):
    """BOOK, MYTICKETS, CANCEL hoàn tiền và trả ghế"""
    m = Model(ctx)
    c = hello(ctx)
    s = sess()
    for line in ["LOGIN binh abcd", f"BOOK VN001 {D}", f"BOOK VJ100 {D}", "MYTICKETS", "BALANCE", "CANCEL T0001", "CANCEL T0001",
                 "MYTICKETS", "BALANCE", f"SEARCH HAN SGN {D}", f"BOOK VN001 {D}", "MYTICKETS"]:
        ask(c, m, s, line)


# ---------------- basic ----------------

@group("basic")
def test_search_every_key(ctx):
    """SEARCH mọi (đi, đến, ngày): chỉ chuyến còn ghế ECO, đúng thứ tự tệp"""
    m = Model(ctx)
    c = hello(ctx)
    s = sess()
    for key in sorted({(f["from"], f["to"], f["date"]) for f in m.fl}):
        ask(c, m, s, f"SEARCH {key[0]} {key[1]} {key[2]}")
    ask(c, m, s, f"SEARCH HAN SGN 2026-12-19")
    ask(c, m, s, f"SEARCH SGN HAN {D}")


@group("basic")
def test_ticket_ids_are_global_and_sequential(ctx):
    """id vé đánh số toàn server theo thứ tự mua; MYTICKETS chỉ liệt kê của tài khoản"""
    m = Model(ctx)
    a, b = hello(ctx, "A"), hello(ctx, "B")
    sa, sb = sess(), sess()
    for c, s, line in [(a, sa, "LOGIN an 1234"), (b, sb, "LOGIN binh abcd"), (a, sa, f"BOOK VJ100 {D}"), (b, sb, f"BOOK VJ100 {D}"),
                       (a, sa, f"BOOK VJ100 {D}"), (b, sb, "MYTICKETS"), (a, sa, "MYTICKETS"), (b, sb, f"BOOK VN006 2026-12-21"),
                       (b, sb, "MYTICKETS")]:
        ask(c, m, s, line)


@group("basic")
def test_ids_never_reused(ctx):
    """Sau CANCEL, id không được cấp lại"""
    m = Model(ctx)
    c = hello(ctx)
    s = sess()
    for line in ["LOGIN an 1234", f"BOOK VJ100 {D}", "CANCEL T0001", f"BOOK VJ100 {D}", f"BOOK VJ100 {D}", "CANCEL T0003",
                 f"BOOK VJ100 {D}", "MYTICKETS"]:
        ask(c, m, s, line)


@group("basic")
def test_tickets_belong_to_account_not_session(ctx):
    """Vé gắn với tài khoản: đăng nhập lại ở kết nối khác thấy đủ và hủy được"""
    m = Model(ctx)
    a = hello(ctx, "A")
    sa = sess()
    for line in ["LOGIN an 1234", f"BOOK VJ100 {D}", f"BOOK VN006 2026-12-21", "QUIT"]:
        ask(a, m, sa, line)
    a.expect_closed()
    time.sleep(0.1)
    b = hello(ctx, "B")
    sb = sess()
    for line in ["LOGIN an 1234", "MYTICKETS", "CANCEL T0002", "MYTICKETS", "BALANCE"]:
        ask(b, m, sb, line)


@group("basic")
def test_not_yours(ctx):
    """CANCEL vé của tài khoản khác → NOT_YOURS, không đổi gì"""
    m = Model(ctx)
    a, b = hello(ctx, "A"), hello(ctx, "B")
    sa, sb = sess(), sess()
    for c, s, line in [(a, sa, "LOGIN an 1234"), (a, sa, f"BOOK VJ100 {D}"), (b, sb, "LOGIN binh abcd"), (b, sb, "CANCEL T0001"),
                       (b, sb, "BALANCE"), (a, sa, "MYTICKETS"), (a, sa, "CANCEL T0001"), (b, sb, "CANCEL T0001")]:
        ask(c, m, s, line)


@group("basic")
def test_relogin_switches_account_and_failed_login_keeps_state(ctx):
    """LOGIN lại đổi tài khoản; LOGIN sai giữ nguyên trạng thái cũ"""
    m = Model(ctx)
    c = hello(ctx)
    s = sess()
    for line in ["LOGIN an 1234", f"BOOK VJ100 {D}", "LOGIN binh wrong", "BALANCE", "MYTICKETS", "LOGIN binh abcd", "MYTICKETS", "BALANCE",
                 "LOGIN an 1234", "MYTICKETS", "LOGIN nobody 1234", "BALANCE"]:
        ask(c, m, s, line)


@group("basic")
def test_two_sessions_same_account(ctx):
    """Một tài khoản dùng ở hai kết nối: số dư và vé dùng chung"""
    m = Model(ctx)
    a, b = hello(ctx, "A"), hello(ctx, "B")
    sa, sb = sess(), sess()
    for c, s, line in [(a, sa, "LOGIN dung x1y2z3"), (b, sb, "LOGIN dung x1y2z3"), (a, sa, f"BOOK VJ010 2026-12-23"), (b, sb, "BALANCE"),
                       (b, sb, f"BOOK VJ010 2026-12-23"), (a, sa, "BALANCE"), (a, sa, "MYTICKETS"), (b, sb, "CANCEL T0001"), (a, sa, "MYTICKETS")]:
        ask(c, m, s, line)


@group("basic")
@cases("PING", "", " ", "login an 1234", "Search HAN SGN 2026-12-20", "BOOKING", "HELP", "QUIT now", "LOGIN", "LOGIN an", "LOGIN an 1234 x",
       "SEARCH", "SEARCH HAN SGN", "SEARCH HAN SGN 2026-12-20 x", "BOOK", "BOOK VN001", f"BOOK VN001 {D} x", "MYTICKETS x", "CANCEL", "CANCEL T0001 x",
       "BALANCE x", "SEARCH  HAN SGN 2026-12-20", f"BOOK VN001  {D}", title="Lệnh {0!r} khi đã đăng nhập")
def test_bad_commands_logged_in(ctx, line):
    m = Model(ctx)
    c = hello(ctx)
    s = sess()
    ask(c, m, s, "LOGIN an 1234")
    ask(c, m, s, line)
    ask(c, m, s, "BALANCE")


@group("basic")
@cases("BOOK VN001 2026-12-20", "BOOK", "BOOK x y z", "MYTICKETS", "MYTICKETS x", "CANCEL T0001", "CANCEL", "BALANCE", "BALANCE x",
       title="Chưa đăng nhập {0!r} → LOGIN_FIRST (kiểm tra trước cú pháp)")
def test_login_first_precedes_syntax(ctx, line):
    m = Model(ctx)
    c = hello(ctx)
    ask(c, m, sess(), line)


# ---------------- edge ----------------

@group("edge")
def test_last_seat_and_hidden_flight(ctx):
    """Chuyến chỉ còn 1 ghế: người đầu mua được, người sau NO_SEATS; chuyến 0 ghế không hiện trong SEARCH"""
    m = Model(ctx)
    a, b = hello(ctx, "A"), hello(ctx, "B")
    sa, sb = sess(), sess()
    for c, s, line in [(a, sa, "LOGIN an 1234"), (b, sb, "LOGIN binh abcd"), (a, sa, f"SEARCH HAN SGN {D}"), (a, sa, f"BOOK VN002 {D}"),
                       (b, sb, f"BOOK VN002 {D}"), (b, sb, f"SEARCH HAN SGN {D}"), (b, sb, f"BOOK QH999 {D}"), (a, sa, "CANCEL T0001"),
                       (b, sb, f"BOOK VN002 {D}"), (a, sa, f"SEARCH HAN SGN {D}")]:
        ask(c, m, s, line)


@group("edge")
def test_money_boundaries(ctx):
    """Số dư đúng bằng giá thì mua được (về 0); thiếu 1 đồng thì NO_MONEY; ví 0"""
    m = Model(ctx)
    c = hello(ctx)
    s = sess()
    for line in ["LOGIN eva eva123", f"BOOK VN001 {D}", "BALANCE", f"BOOK VJ010 2026-12-23", "CANCEL T0001", "BALANCE", f"BOOK VN001 {D}",
                 "LOGIN chi pass99", f"BOOK VJ010 2026-12-23", "BALANCE", "LOGIN dung x1y2z3", f"BOOK BL008 {D}", f"BOOK VJ010 2026-12-23",
                 f"BOOK VJ010 2026-12-23", "BALANCE"]:
        ask(c, m, s, line)


@group("edge")
def test_exact_date_match(ctx):
    """(mã, ngày) phải khớp cả hai; SEARCH khớp đi/đến/ngày chính xác"""
    m = Model(ctx)
    c = hello(ctx)
    s = sess()
    for line in ["LOGIN an 1234", "BOOK VN001 2026-12-21", f"BOOK vn001 {D}", "BOOK VN001 2026-12-2", "BOOK VN001 20261220",
                 f"SEARCH HAN SGN 2026-12-2", f"SEARCH han sgn {D}", f"SEARCH HAN  SGN {D}", f"SEARCH SGN HAN 2026-12-21"]:
        ask(c, m, s, line)


@group("edge")
@cases("T0001", "T0002", "t0001", "T1", "T00001", "T000", "0001", "TXXXX", "T-001", "T0001 ", "T 0001", "T0100", "T9999", "T0000",
       title="CANCEL id {0!r}")
def test_cancel_id_forms(ctx, tid):
    m = Model(ctx)
    c = hello(ctx)
    s = sess()
    for line in ["LOGIN an 1234", f"BOOK VJ100 {D}", f"CANCEL {tid}", "MYTICKETS", "BALANCE"]:
        ask(c, m, s, line)


@group("edge")
@timeout(20)
def test_many_tickets_listing(ctx):
    """Mua rồi hủy xen kẽ 150 vé: MYTICKETS liệt kê đúng, id tăng dần"""
    m = Model(ctx)
    c = hello(ctx)
    s = sess()
    ask(c, m, s, "LOGIN an 1234")
    for i in range(150):
        ask(c, m, s, f"BOOK VJ100 {D}" if i % 2 == 0 else f"BOOK QH007 2026-12-22")
        if i % 7 == 6:
            ask(c, m, s, f"CANCEL T{i - 3:04d}")
    ask(c, m, s, "MYTICKETS")
    ask(c, m, s, "BALANCE")


@group("edge")
@timeout(20)
def test_ids_keep_growing_after_cancel(ctx):
    """Mua rồi hủy 150 lần: id không dùng lại nên tới T0150; vé cuối cùng vẫn đúng"""
    m = Model(ctx)
    c = hello(ctx)
    s = sess()
    ask(c, m, s, "LOGIN an 1234")
    for i in range(150):
        ask(c, m, s, f"BOOK VJ010 2026-12-23")
        ask(c, m, s, f"CANCEL T{i + 1:04d}")
    ask(c, m, s, f"BOOK VJ010 2026-12-23")
    ask(c, m, s, "MYTICKETS")
    ask(c, m, s, "BALANCE")


# ---------------- stream ----------------

@group("stream")
def test_byte_by_byte(ctx):
    """Gửi từng byte một"""
    m = Model(ctx)
    c = hello(ctx)
    s = sess()
    for line in ["LOGIN an 1234", f"SEARCH HAN SGN {D}", f"BOOK VN001 {D}", "MYTICKETS"]:
        want = m.run(s, line)
        c.send_slowly(line + "\n", chunk=1, delay=0.001)
        for w in want:
            c.expect_line(w, timeout=2.0)


@group("stream")
def test_many_commands_one_send(ctx):
    """Hàng chục lệnh dính nhau trong một lần gửi"""
    m = Model(ctx)
    c = hello(ctx)
    s = sess()
    lines = ["LOGIN an 1234"] + [f"BOOK VJ100 {D}", "BALANCE", "MYTICKETS", f"SEARCH HAN SGN {D}", "CANCEL T0001"] * 10
    c.send("".join(x + "\n" for x in lines))
    for line in lines:
        for w in m.run(s, line):
            c.expect_line(w, timeout=3.0)


@group("stream")
def test_crlf_and_chunks(ctx):
    """\\r\\n và cắt ngẫu nhiên 1–7 byte"""
    m = Model(ctx)
    c = hello(ctx)
    s = sess()
    for line in ["LOGIN an 1234", f"BOOK VJ100 {D}", "MYTICKETS", "", "BALANCE"]:
        want = m.run(s, line)
        if ctx.rng.random() < 0.5:
            c.send(line + "\r\n")
        else:
            c.send_chunks(line + "\n", ctx.rng, delay=0)
        for w in want:
            c.expect_line(w, timeout=2.0)


@group("stream")
def test_quit_in_middle_of_batch(ctx):
    """QUIT giữa một khối lệnh dính nhau: lệnh trước được xử lý, lệnh sau bị bỏ"""
    c = login(ctx, "an")
    c.send(f"BOOK VJ100 {D}\nQUIT\nBOOK VJ100 {D}\nBALANCE\n")
    c.expect_line("TICKET T0001")
    c.expect_line("BYE")
    c.expect_closed(timeout=1.5)
    d = login(ctx, "an", "d")
    d.send_line("MYTICKETS")
    d.expect_line("TICKETS 1")
    d.expect_line(f"T0001 VJ100 {D}")


# ---------------- robust ----------------

@group("robust")
def test_binary_garbage(ctx):
    """Byte lạ không làm hỏng server"""
    c = login(ctx, "an")
    for junk in [b"\x01\x02", b"BOOK \xff\xfe \x80", b"LOGIN \xff \xfe", b"\x7f", b"CANCEL \xc3\xa9"]:
        c.send(junk + b"\n")
        got = c.recv_line()
        if got not in ("ERROR", "NOT_FOUND", "FAIL"):
            raise Fail(WA, f"byte lạ {junk!r}: nhận {got!r}")
    c.send_line("BALANCE")
    c.expect_line("BALANCE 50000000")


@group("robust")
def test_new_connection_is_logged_out(ctx):
    """Kết nối mới dùng lại chỗ của client cũ luôn ở trạng thái chưa LOGIN"""
    for i in range(6):
        c = login(ctx, "an", f"c{i}")
        c.reset() if i % 2 else c.close()
        time.sleep(0.15)
        d = hello(ctx, f"d{i}")
        d.send_line("BALANCE")
        d.expect_line("LOGIN_FIRST")
        d.close()
        time.sleep(0.05)


@group("robust")
@timeout(20)
def test_300_sessions_with_purchases(ctx):
    """300 phiên đăng nhập (mỗi phiên thứ 5 mua 1 vé) rồi đóng/RST: vé còn nguyên, không rò fd"""
    bought = 0
    for i in range(300):
        c = login(ctx, "an", f"c{i}")
        if i % 5 == 0:
            c.send_line(f"BOOK VJ100 {D}")
            bought += 1
            c.expect_line(f"TICKET T{bought:04d}")
        if i % 2:
            c.reset()
        else:
            c.close()
        ctx.close_quietly(c)
        time.sleep(0.003)
    time.sleep(0.2)
    d = login(ctx, "an", "d")
    d.send_line("MYTICKETS")
    d.expect_line(f"TICKETS {bought}")


@group("robust")
def test_dies_mid_command(ctx):
    """Gửi dở BOOK rồi RST: không mua gì"""
    c = login(ctx, "an")
    c.send(f"BOOK VN001 {D[:6]}")
    c.reset()
    time.sleep(0.3)
    ctx.expect_alive()
    d = login(ctx, "an", "d")
    d.send_line("MYTICKETS")
    d.expect_line("TICKETS 0")


# ---------------- concurrency ----------------

@group("concurrency")
@args("{port}", "20")
@timeout(15)
def test_race_for_last_seats(ctx):
    """12 client cùng mua 3 ghế cuối của VN001: đúng 3 vé với 3 id khác nhau T0001–T0003"""
    cs = [login(ctx, ["an", "binh", "eva", "dung"][i % 4], f"c{i}") for i in range(12)]
    for c in cs:
        c.send_line(f"BOOK VN001 {D}")
    ids = []
    for c in cs:
        got = c.recv_line(timeout=3.0)
        if got.startswith("TICKET "):
            ids.append(got[7:])
        elif got not in ("NO_SEATS", "NO_MONEY"):
            raise Fail(WA, f"{c.name}: nhận {got!r}")
    if len(ids) != 3 or sorted(ids) != ["T0001", "T0002", "T0003"]:
        raise Fail(WA, f"bán được {ids!r} (mong đợi 3 vé T0001–T0003; ví của 'dung' có thể thiếu tiền nên chỉ tính vé được bán)")


@group("concurrency")
@args("{port}", "20")
@timeout(15)
def test_race_cancel_same_ticket(ctx):
    """Hai kết nối cùng tài khoản cùng CANCEL một vé: một REFUNDED, một NOT_FOUND; hoàn tiền một lần"""
    a, b = login(ctx, "an", "a"), login(ctx, "an", "b")
    a.send_line(f"BOOK VJ100 {D}")
    a.expect_line("TICKET T0001")
    a.send_line("CANCEL T0001")
    b.send_line("CANCEL T0001")
    got = sorted([a.recv_line(timeout=2.0), b.recv_line(timeout=2.0)])
    if got != ["NOT_FOUND", "REFUNDED 800000"]:
        raise Fail(WA, f"hai CANCEL đồng thời cho {got!r}")
    a.send_line("BALANCE")
    a.expect_line("BALANCE 50000000")
    a.send_line(f"SEARCH HAN SGN {D}")
    got = [a.recv_line() for _ in range(4)]
    if got[0] != "FLIGHTS 3":
        raise Fail(WA, f"ghế bị hoàn hai lần hoặc mất: {got!r}")


@group("concurrency")
def test_idle_client_does_not_block(ctx):
    """Client im lặng/gửi dở lệnh không chặn client khác"""
    idle = [hello(ctx, f"idle{i}") for i in range(3)]
    idle[0].send("LOGIN an 12")
    with ctx.verdict(BLOCKED):
        c = login(ctx, "binh")
        c.send_line(f"BOOK VN001 {D}")
        c.expect_line("TICKET T0001")
    idle[0].send("34\n")
    idle[0].expect_line("OK an")


# ---------------- stress ----------------

@group("stress")
@args("{port}", "10")
@timeout(40)
def test_random_ops_vs_model(ctx):
    """1000 thao tác ngẫu nhiên của 4 phiên (đăng nhập, mua, hủy, tìm, xem) so với mô hình"""
    rng = ctx.rng
    m = Model(ctx)
    users = ["an", "binh", "chi", "dung", "eva"]
    cs = [hello(ctx, f"s{i}") for i in range(4)]
    ss = [sess() for _ in cs]
    keys = [(f["code"], f["date"]) for f in m.fl]
    routes = sorted({(f["from"], f["to"], f["date"]) for f in m.fl})
    for step in range(1000):
        i = rng.randrange(4)
        r = rng.random()
        if r < 0.1:
            u = rng.choice(users)
            line = f"LOGIN {u} {PW[u] if rng.random() < 0.85 else 'nope'}"
        elif r < 0.4:
            line = "BOOK %s %s" % rng.choice(keys)
        elif r < 0.55:
            line = f"CANCEL T{rng.randint(1, max(1, m.next_id + 1)):04d}"
        elif r < 0.7:
            line = "MYTICKETS"
        elif r < 0.85:
            line = "SEARCH %s %s %s" % rng.choice(routes)
        elif r < 0.92:
            line = "BALANCE"
        else:
            line = rng.choice(["PING", "", "BOOK x", "LOGIN an", "CANCEL x", f"BOOK VN001  {D}"])
        ask(cs[i], m, ss[i], line, timeout=2.5)
