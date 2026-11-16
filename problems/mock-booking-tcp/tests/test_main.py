# Thiết kế: docs/TEST-DESIGN.md. Phần "tối đa N client" dùng chung: judge/runner/suites.py (maxn_suite).
import time

from njlib import BLOCKED, LIMIT, Fail, WA, args, cases, group, sample, timeout
from suites import maxn_suite


def hello(ctx, name=None):
    c = ctx.connect(name=name)
    c.expect_line("WELCOME")
    return c


def ask(c, cmd, want, timeout=1.0):
    c.send_line(cmd)
    c.expect_line(want, timeout)


def user(ctx, name):
    c = hello(ctx, name)
    ask(c, f"LOGIN {name}", f"OK {name}")
    return c


@sample
@args("{port}", "2", "5")
def test_example(ctx):
    """Ví dụ trong đề"""
    a = hello(ctx, "A")
    ask(a, "LIST", "FREE 5 1 2 3 4 5")
    ask(a, "BOOK 2", "LOGIN_FIRST")
    ask(a, "LOGIN an", "OK an")
    ask(a, "BOOK 2", "BOOKED 2")
    b = hello(ctx, "B")
    ask(b, "LOGIN binh", "OK binh")
    ask(b, "BOOK 2", "TAKEN 2")
    ask(b, "CANCEL 2", "NOT_YOURS 2")
    with ctx.verdict(LIMIT):
        c = ctx.connect(name="C")
        c.expect_line("FULL")
        c.expect_closed()
    ask(a, "MINE", "MINE 1 2")


@sample
def test_list_and_cancel(ctx):
    """LIST thay đổi theo BOOK/CANCEL"""
    a = user(ctx, "an")
    ask(a, "BOOK 10", "BOOKED 10")
    ask(a, "BOOK 1", "BOOKED 1")
    ask(a, "LIST", "FREE 8 2 3 4 5 6 7 8 9")
    ask(a, "CANCEL 1", "CANCELLED 1")
    ask(a, "CANCEL 1", "NOT_YOURS 1")
    ask(a, "MINE", "MINE 1 10")
    ask(a, "LIST", "FREE 9 1 2 3 4 5 6 7 8 9")


@group("basic")
def test_errors_and_invalid(ctx):
    """ERROR / INVALID / LOGIN_FIRST"""
    a = hello(ctx)
    for cmd in ["CANCEL 1", "MINE", "BOOK 1"]:
        ask(a, cmd, "LOGIN_FIRST")
    for cmd in ["", "HELLO", "LOGIN", "LOGIN a b", "list", "LIST 1", "QUIT now"]:
        ask(a, cmd, "ERROR")
    ask(a, "LOGIN " + "x" * 33, "ERROR")
    ask(a, "LOGIN an", "OK an")
    for cmd in ["BOOK 0", "BOOK 11", "BOOK abc", "BOOK -1", "BOOK 1x", "CANCEL 99"]:
        ask(a, cmd, "INVALID")
    for cmd in ["BOOK", "BOOK 1 2", "MINE x"]:
        ask(a, cmd, "ERROR")


@group("edge")
def test_full_house(ctx):
    """Đặt hết ghế"""
    a = user(ctx, "an")
    for g in range(1, 11):
        ask(a, f"BOOK {g}", f"BOOKED {g}")
    ask(a, "LIST", "FREE 0")
    ask(a, "MINE", "MINE 10 " + " ".join(map(str, range(1, 11))))


@group("basic")
def test_ownership_by_name(ctx):
    """Ghế gắn với tên, còn giữ sau khi client rời đi"""
    a = user(ctx, "an")
    ask(a, "BOOK 3", "BOOKED 3")
    ask(a, "QUIT", "BYE")
    a.expect_closed()
    b = user(ctx, "binh")
    ask(b, "CANCEL 3", "NOT_YOURS 3")
    ask(b, "MINE", "MINE 0")
    a2 = user(ctx, "an")
    ask(a2, "MINE", "MINE 1 3")
    ask(a2, "CANCEL 3", "CANCELLED 3")


@group("basic")
def test_relogin(ctx):
    """LOGIN lại để đổi tên"""
    a = user(ctx, "an")
    ask(a, "BOOK 4", "BOOKED 4")
    ask(a, "LOGIN binh", "OK binh")
    ask(a, "MINE", "MINE 0")
    ask(a, "CANCEL 4", "NOT_YOURS 4")


@group("stream")
def test_framing(ctx):
    """Lệnh bị cắt vụn và dính nhau"""
    a = hello(ctx)
    a.send_slowly("LOGIN an\r\n", chunk=1, delay=0.01)
    a.expect_line("OK an")
    a.send("BOOK 5\nBOOK 6\r\nMINE\n")
    for want in ["BOOKED 5", "BOOKED 6", "MINE 2 5 6"]:
        a.expect_line(want)


@group("concurrency")
def test_idle_does_not_block(ctx):
    """Client im lặng / gửi dở không làm treo người khác"""
    idle = hello(ctx, "idle")
    idle.send("LOGIN ha")
    with ctx.verdict(BLOCKED):
        b = hello(ctx, "B")
        ask(b, "LOGIN binh", "OK binh", timeout=0.5)
    idle.send("i\n")
    idle.expect_line("OK hai")


@args("{port}", "3", "10")
@group("concurrency")
def test_limit_and_free_slot(ctx):
    """Giới hạn N và giải phóng chỗ khi client rời đi đột ngột"""
    cs = [hello(ctx, f"C{i}") for i in range(3)]
    with ctx.verdict(LIMIT):
        x = ctx.connect(name="X")
        x.expect_line("FULL")
        cs[1].close()
        time.sleep(0.15)
        hello(ctx, "D")
        y = ctx.connect(name="Y")
        y.expect_line("FULL")


@args("{port}", "20", "1")
@group("concurrency")
def test_race_single_seat(ctx):
    """20 người cùng tranh 1 ghế: đúng 1 người đặt được"""
    cs = [user(ctx, f"u{i}") for i in range(20)]
    for c in cs:
        c.send_line("BOOK 1")
    got = [c.recv_line(2) for c in cs]
    ok = [g for g in got if g == "BOOKED 1"]
    bad = [g for g in got if g not in ("BOOKED 1", "TAKEN 1")]
    if len(ok) != 1 or bad:
        raise Fail(WA, f"đúng 1 người phải BOOKED 1, số BOOKED = {len(ok)}, phản hồi khác: {bad[:3]}")


# ======================= phần mở rộng (thiết kế lại) =======================

class Model:
    """Mô hình chuẩn: ghế gắn với tên, mỗi kết nối có tên đăng nhập riêng."""

    def __init__(self, seats):
        self.seats = seats
        self.owner = {}

    def run(self, conn, line):
        if line.endswith("\r"):
            line = line[:-1]
        w = [t for t in line.split(" ") if t][:3]
        nt, cmd = len(w), (w[0] if w else "")
        if nt == 2 and cmd == "LOGIN" and len(w[1]) <= 32:
            conn["name"] = w[1]
            return f"OK {w[1]}"
        if nt == 1 and cmd == "LIST":
            free = [g for g in range(1, self.seats + 1) if g not in self.owner]
            return " ".join(["FREE", str(len(free))] + [str(g) for g in free])
        if nt == 1 and cmd == "QUIT":
            return "BYE"
        if (nt == 2 and cmd in ("BOOK", "CANCEL")) or (nt == 1 and cmd == "MINE"):
            name = conn.get("name")
            if not name:
                return "LOGIN_FIRST"
            if cmd == "MINE":
                mine = [g for g in range(1, self.seats + 1) if self.owner.get(g) == name]
                return " ".join(["MINE", str(len(mine))] + [str(g) for g in mine])
            s = w[1]
            g = int(s) if s.isdigit() and s.isascii() and len(s) <= 4 else 0
            if not 1 <= g <= self.seats:
                return "INVALID"
            if cmd == "BOOK":
                if g in self.owner:
                    return f"TAKEN {g}"
                self.owner[g] = name
                return f"BOOKED {g}"
            if self.owner.get(g) == name:
                del self.owner[g]
                return f"CANCELLED {g}"
            return f"NOT_YOURS {g}"
        return "ERROR"


def random_line(rng, seats, names):
    r = rng.random()
    g = rng.choice([rng.randint(1, seats), rng.randint(1, seats), 0, seats + 1, rng.randint(-3, seats + 5)])
    if r < 0.15:
        return f"LOGIN {rng.choice(names)}"
    if r < 0.45:
        return f"BOOK {g}"
    if r < 0.65:
        return f"CANCEL {g}"
    if r < 0.75:
        return "MINE"
    if r < 0.85:
        return "LIST"
    return rng.choice(["", "BOOK", "BOOK 1 2", "LOGIN", "login an", "MINE 1", "LIST x", "CANCEL", "BOOK x",
                       "BOOK 1x", "QUIT 1", "HELLO", "LOGIN " + "n" * 33, "LOGIN " + "m" * 32])


@group("edge")
@args("{port}", "2", "1")
def test_one_seat(ctx):
    """S=1: LIST/BOOK/CANCEL ở biên dưới"""
    a = user(ctx, "an")
    for cmd, want in [("LIST", "FREE 1 1"), ("BOOK 2", "INVALID"), ("BOOK 0", "INVALID"), ("BOOK 1", "BOOKED 1"),
                      ("LIST", "FREE 0"), ("BOOK 1", "TAKEN 1"), ("MINE", "MINE 1 1"), ("CANCEL 1", "CANCELLED 1"),
                      ("LIST", "FREE 1 1")]:
        ask(a, cmd, want)


@group("edge")
@args("{port}", "2", "100")
def test_hundred_seats(ctx):
    """S=100: LIST đầy đủ 100 ghế (dòng dài ~300 byte), ghế 100 hợp lệ, 101 thì INVALID"""
    a = user(ctx, "an")
    ask(a, "LIST", "FREE 100 " + " ".join(map(str, range(1, 101))))
    ask(a, "BOOK 100", "BOOKED 100")
    ask(a, "BOOK 101", "INVALID")
    ask(a, "BOOK 9999", "INVALID")
    ask(a, "BOOK 99999", "INVALID")
    for g in range(1, 100):
        a.send_line(f"BOOK {g}")
    for g in range(1, 100):
        a.expect_line(f"BOOKED {g}", timeout=2)
    ask(a, "LIST", "FREE 0")
    ask(a, "MINE", "MINE 100 " + " ".join(map(str, range(1, 101))))


@group("edge")
@cases(("x" * 32, "OK " + "x" * 32), ("x" * 33, "ERROR"), ("a", "OK a"), ("Tên-Việt_1", "OK Tên-Việt_1"),
       title="LOGIN tên dài {0!r:.12} → {1:.10}")
def test_login_names(ctx, name, want):
    a = hello(ctx)
    ask(a, f"LOGIN {name}", want)


@group("edge")
def test_crlf_everywhere(ctx):
    """Mọi lệnh kết thúc bằng CRLF"""
    a = hello(ctx)
    a.send("LOGIN an\r\nBOOK 1\r\nMINE\r\nLIST\r\nCANCEL 1\r\nQUIT\r\n")
    a.expect_lines(["OK an", "BOOKED 1", "MINE 1 1", "FREE 9 2 3 4 5 6 7 8 9 10", "CANCELLED 1", "BYE"])
    a.expect_closed()


@group("basic")
def test_two_clients_same_name(ctx):
    """Hai kết nối cùng tên: cùng sở hữu ghế, ai cũng huỷ được"""
    a, b = user(ctx, "an"), user(ctx, "an")
    ask(a, "BOOK 7", "BOOKED 7")
    ask(b, "MINE", "MINE 1 7")
    ask(b, "CANCEL 7", "CANCELLED 7")
    ask(a, "MINE", "MINE 0")


@group("stream")
@timeout(12)
def test_random_fragments_vs_model(ctx):
    """300 lệnh ngẫu nhiên cắt thành mảnh 1–20 byte, so với mô hình"""
    rng = ctx.rng
    m = Model(10)
    conn = {}
    a = hello(ctx)
    cmds = [random_line(rng, 10, ["an", "binh"]) for _ in range(300)]
    a.send_chunks("".join(x + "\n" for x in cmds), rng, 1, 20, delay=0)
    for x in cmds:
        want = m.run(conn, x)
        got = a.recv_line(timeout=2)
        if got != want:
            raise Fail(WA, f"lệnh {x!r} mong đợi {want!r}, nhận được {got!r}")


@group("concurrency")
@args("{port}", "10", "30")
@timeout(15)
def test_multi_client_random_vs_model(ctx):
    """10 client (4 tên, có trùng tên) gửi 700 lệnh xen kẽ, so với mô hình"""
    rng = ctx.rng
    m = Model(30)
    names = ["an", "binh", "chi", "dung"]
    cs = [(hello(ctx, f"C{i}"), {}) for i in range(10)]
    for _ in range(700):
        c, conn = rng.choice(cs)
        x = random_line(rng, 30, names)
        c.send_line(x)
        want = m.run(conn, x)
        got = c.recv_line(timeout=1.5)
        if got != want:
            raise Fail(WA, f"{c.name}: lệnh {x!r} mong đợi {want!r}, nhận được {got!r}")


@group("concurrency")
@args("{port}", "12", "40")
@timeout(12)
def test_race_all_seats(ctx):
    """12 người dồn lệnh BOOK cả 40 ghế (thứ tự ngẫu nhiên) cùng lúc: mỗi ghế đúng một chủ"""
    rng = ctx.rng
    cs = [user(ctx, f"u{i}") for i in range(12)]
    orders = []
    for c in cs:
        o = list(range(1, 41))
        rng.shuffle(o)
        orders.append(o)
        c.send("".join(f"BOOK {g}\n" for g in o))
    winners = {}
    for i, (c, o) in enumerate(zip(cs, orders)):
        for g in o:
            got = c.recv_line(timeout=2)
            if got == f"BOOKED {g}":
                if g in winners:
                    raise Fail(WA, f"ghế {g} được đặt hai lần (u{winners[g]} và u{i})")
                winners[g] = i
            elif got != f"TAKEN {g}":
                raise Fail(WA, f"u{i}: BOOK {g} nhận {got!r}")
    if len(winners) != 40:
        raise Fail(WA, f"chỉ {len(winners)}/40 ghế có chủ")
    for i, c in enumerate(cs):
        mine = sorted(g for g, w in winners.items() if w == i)
        ask(c, "MINE", " ".join(["MINE", str(len(mine))] + [str(g) for g in mine]))
    ask(cs[0], "LIST", "FREE 0")


@group("robust")
def test_seats_kept_after_rst(ctx):
    """Client đặt ghế rồi mất kết nối (RST): ghế vẫn giữ, chỗ kết nối được trả lại"""
    a = user(ctx, "an")
    a.send("BOOK 1\nBOOK 2\n")
    a.expect_lines(["BOOKED 1", "BOOKED 2"])
    a.reset()
    time.sleep(0.2)
    b = user(ctx, "an")
    ask(b, "MINE", "MINE 2 1 2")


@group("regression")
def test_new_connection_not_logged_in(ctx):
    """Kết nối mới (dùng lại chỗ của client cũ đã đăng nhập) phải chưa LOGIN"""
    for k in range(3):
        a = user(ctx, f"cu{k}")
        ask(a, "QUIT", "BYE")
        a.expect_closed()
        time.sleep(0.05)
        b = hello(ctx, f"moi{k}")
        ask(b, "MINE", "LOGIN_FIRST")
        ask(b, "BOOK 1", "LOGIN_FIRST")
        b.close()
        time.sleep(0.1)


globals().update(maxn_suite(ping=("MINE", "LOGIN_FIRST"), extra_args=("10",)))
