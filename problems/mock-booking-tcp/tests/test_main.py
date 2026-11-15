import time

from njlib import BLOCKED, LIMIT, Fail, WA, args, sample


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


def test_full_house(ctx):
    """Đặt hết ghế"""
    a = user(ctx, "an")
    for g in range(1, 11):
        ask(a, f"BOOK {g}", f"BOOKED {g}")
    ask(a, "LIST", "FREE 0")
    ask(a, "MINE", "MINE 10 " + " ".join(map(str, range(1, 11))))


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


def test_relogin(ctx):
    """LOGIN lại để đổi tên"""
    a = user(ctx, "an")
    ask(a, "BOOK 4", "BOOKED 4")
    ask(a, "LOGIN binh", "OK binh")
    ask(a, "MINE", "MINE 0")
    ask(a, "CANCEL 4", "NOT_YOURS 4")


def test_framing(ctx):
    """Lệnh bị cắt vụn và dính nhau"""
    a = hello(ctx)
    a.send_slowly("LOGIN an\r\n", chunk=1, delay=0.01)
    a.expect_line("OK an")
    a.send("BOOK 5\nBOOK 6\r\nMINE\n")
    for want in ["BOOKED 5", "BOOKED 6", "MINE 2 5 6"]:
        a.expect_line(want)


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
