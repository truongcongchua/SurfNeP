import time

from njlib import BLOCKED, LIMIT, args, sample


def hello(ctx, name=None):
    c = ctx.connect(name=name)
    c.expect_line("WELCOME")
    return c


@sample
def test_echo_count_quit(ctx):
    """ECHO, COUNT và QUIT cơ bản"""
    c = hello(ctx)
    for cmd, want in [("hello", "ECHO hello"), ("", "ECHO "), ("a b  c", "ECHO a b  c"),
                      ("COUNT", "COUNT 1"), ("count", "ECHO count")]:
        c.send_line(cmd)
        c.expect_line(want)
    c.send_line("QUIT")
    c.expect_line("BYE")
    c.expect_closed()


@sample
@args("{port}", "2")
def test_full(ctx):
    """N=2: client thứ 3 nhận FULL và bị đóng, client cũ vẫn dùng được"""
    a, b = hello(ctx, "A"), hello(ctx, "B")
    with ctx.verdict(LIMIT):
        extra = ctx.connect(name="C")
        extra.expect_line("FULL")
        extra.expect_closed()
    a.send_line("COUNT")
    a.expect_line("COUNT 2")
    b.send_line("x")
    b.expect_line("ECHO x")


def test_fragmented_and_coalesced(ctx):
    """Dòng bị cắt vụn và nhiều dòng dính nhau"""
    c = hello(ctx)
    c.send_slowly("xin chao\r\n", chunk=1, delay=0.01)
    c.expect_line("ECHO xin chao")
    c.send("a\nb\nCOUNT\nc\n")
    for want in ["ECHO a", "ECHO b", "COUNT 1", "ECHO c"]:
        c.expect_line(want)


def test_idle_client_does_not_block(ctx):
    """Một client im lặng hoặc gửi dở dòng không làm treo client khác"""
    idle = hello(ctx, "idle")
    idle.send("na")
    with ctx.verdict(BLOCKED):
        b = hello(ctx, "B")
        b.send_line("ping")
        b.expect_line("ECHO ping", timeout=0.5)
    idle.send("m\n")
    idle.expect_line("ECHO nam")


@args("{port}", "3")
def test_slot_freed_on_quit(ctx):
    """N=3: QUIT giải phóng chỗ cho client đang bị FULL"""
    cs = [hello(ctx, f"C{i}") for i in range(3)]
    with ctx.verdict(LIMIT):
        e = ctx.connect(name="E")
        e.expect_line("FULL")
        e.expect_closed()
    cs[0].send_line("QUIT")
    cs[0].expect_line("BYE")
    cs[0].expect_closed()
    with ctx.verdict(LIMIT):
        again = hello(ctx, "again")
    again.send_line("COUNT")
    again.expect_line("COUNT 3")


@args("{port}", "3")
def test_slot_freed_on_abrupt_close(ctx):
    """N=3: client đóng đột ngột (không QUIT) cũng phải giải phóng chỗ"""
    cs = [hello(ctx, f"C{i}") for i in range(3)]
    cs[1].close()
    time.sleep(0.3)  # cho server có thời gian nhận ra client đã đóng
    with ctx.verdict(LIMIT):
        c = ctx.connect(name="late")
        c.expect_line("WELCOME", timeout=1.5)
    c.send_line("COUNT")
    c.expect_line("COUNT 3")


@args("{port}", "1")
def test_n_equals_one(ctx):
    """N=1: lần lượt từng client, mỗi lần chỉ một"""
    a = hello(ctx, "A")
    with ctx.verdict(LIMIT):
        b = ctx.connect(name="B")
        b.expect_line("FULL")
        b.expect_closed()
    a.send_line("QUIT")
    a.expect_line("BYE")
    with ctx.verdict(LIMIT):
        c = hello(ctx, "C")
    c.send_line("COUNT")
    c.expect_line("COUNT 1")


@args("{port}", "10")
def test_many_clients(ctx):
    """N=10: 10 client cùng lúc, client thứ 11 bị từ chối"""
    cs = [hello(ctx, f"C{i}") for i in range(10)]
    with ctx.verdict(LIMIT):
        extra = ctx.connect(name="C10")
        extra.expect_line("FULL")
    for i, c in enumerate(cs):
        c.send_line(f"id{i}")
    for i, c in enumerate(cs):
        c.expect_line(f"ECHO id{i}")
