import time

from njlib import BLOCKED, sample


def join(ctx, cid, name=None):
    c = ctx.connect(name=cid)
    c.send_line(f"{cid}: {name or cid.upper()}")
    c.expect_line(f"OK {cid}")
    return c


@sample
def test_register(ctx):
    """Đăng ký đúng cú pháp"""
    c = ctx.connect()
    c.send_line("abc: An")
    c.expect_line("OK abc")


@sample
def test_register_invalid(ctx):
    """Sai cú pháp thì báo ERROR và cho đăng ký lại"""
    c = ctx.connect()
    for bad in ["abc An", "abc:An", ": An", "abc: ", "abc: Nguyen An", "abc : An"]:
        c.send_line(bad)
        c.expect_line("ERROR")
    c.send_line("abc: An")
    c.expect_line("OK abc")


@sample
def test_broadcast(ctx):
    """Tin nhắn tới mọi người khác, không quay về người gửi"""
    a, b, d = join(ctx, "a"), join(ctx, "b"), join(ctx, "d")
    a.send_line("xin chao")
    b.expect_line("a: xin chao")
    d.expect_line("a: xin chao")
    a.expect_silence(0.2)
    d.send_line("hi all")
    a.expect_line("d: hi all")
    b.expect_line("d: hi all")


def test_unregistered_gets_nothing(ctx):
    """Client chưa đăng ký không nhận tin"""
    a, b = join(ctx, "a"), join(ctx, "b")
    lurker = ctx.connect(name="lurker")
    a.send_line("bi mat")
    b.expect_line("a: bi mat")
    lurker.expect_silence(0.3)


def test_fragmented_line(ctx):
    """Một dòng bị cắt thành từng byte"""
    a, b = join(ctx, "a"), join(ctx, "b")
    a.send_slowly("chao ban toi la a\n", chunk=1, delay=0.005)
    b.expect_line("a: chao ban toi la a")


def test_fragmented_register(ctx):
    """Dòng đăng ký bị cắt vụn"""
    c = ctx.connect()
    c.send_slowly("abc: An\n", chunk=2, delay=0.02)
    c.expect_line("OK abc")


def test_coalesced_lines(ctx):
    """Nhiều dòng dính trong một lần gửi, kể cả dòng đăng ký"""
    b = join(ctx, "b")
    a = ctx.connect(name="a")
    a.send("a: An\nmot\nhai\r\nba\n")
    a.expect_line("OK a")
    for msg in ["mot", "hai", "ba"]:
        b.expect_line(f"a: {msg}")


def test_half_line_does_not_block(ctx):
    """Client gửi dở nửa dòng rồi im lặng không làm treo server"""
    a, b = join(ctx, "a"), join(ctx, "b")
    a.send("cau nay chua xong")
    with ctx.verdict(BLOCKED):
        newcomer = ctx.connect(name="c")
        newcomer.send_line("c: Cuong")
        newcomer.expect_line("OK c", timeout=0.5)
        b.send_line("van chat duoc")
        newcomer.expect_line("b: van chat duoc", timeout=0.5)
    a.send(" roi\n")
    b.expect_line("a: cau nay chua xong roi")


def test_disconnect(ctx):
    """Client rời phòng, những người còn lại vẫn chat được"""
    a, b, d = join(ctx, "a"), join(ctx, "b"), join(ctx, "d")
    b.close()
    time.sleep(0.1)
    a.send_line("b di roi")
    d.expect_line("a: b di roi")
    e = join(ctx, "e")
    d.send_line("chao e")
    a.expect_line("d: chao e")
    e.expect_line("d: chao e")


def test_many_clients(ctx):
    """30 client cùng phòng"""
    cs = [join(ctx, f"u{i}") for i in range(30)]
    cs[7].send_line("ping")
    for i, c in enumerate(cs):
        if i != 7:
            c.expect_line("u7: ping")
    cs[7].expect_silence(0.2)
