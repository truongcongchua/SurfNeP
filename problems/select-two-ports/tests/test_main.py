import time

from njlib import WA, Conn, Fail, group, sample, timeout, cases, BLOCKED

ONE = b"ONE\n"
TWO = b"TWO\n"


def connect(ctx, which, name=None):
    """which = 1 (cổng chính) hoặc 2 (cổng + 1)."""
    name = name or f"cong{which}"
    if which == 1:
        return ctx.connect(name=name)
    c = Conn(ctx.port + 1, name, 1.0)
    ctx._conns.append(c)
    return c


def expect(c, which, timeout=1.5):
    c.expect_bytes(ONE if which == 1 else TWO, timeout=timeout)
    c.expect_closed(timeout=1.0)


def blocked_on(ctx, which, other):
    """Client ở cổng `which` phải được phục vụ dù chưa có client nào ở cổng `other`."""
    c = connect(ctx, which)
    with ctx.verdict(BLOCKED):
        c.expect_bytes(ONE if which == 1 else TWO, timeout=1.0)
    c.expect_closed(timeout=1.0)


@sample
def test_first_port(ctx):
    """Client ở cổng chính nhận ONE\\n rồi bị đóng"""
    expect(connect(ctx, 1), 1)


@sample
def test_second_port(ctx):
    """Client ở cổng + 1 nhận TWO\\n rồi bị đóng"""
    expect(connect(ctx, 2), 2)


@group("basic")
def test_alternate_ports(ctx):
    """Lần lượt cổng 1, 2, 1, 2, 1, 2: mỗi client đúng lời chào của cổng mình"""
    for i in range(6):
        w = 1 + i % 2
        expect(connect(ctx, w, f"lan{i}"), w)


@group("basic")
def test_both_open_read_second_first(ctx):
    """Hai client mở cùng lúc ở hai cổng, đọc cổng 2 trước rồi cổng 1"""
    a = connect(ctx, 1, "A")
    b = connect(ctx, 2, "B")
    expect(b, 2)
    expect(a, 1)


@group("basic")
def test_exact_four_bytes(ctx):
    """Lời chào đúng 4 byte, không byte thừa, rồi đóng (cả hai cổng)"""
    for w, want in ((1, ONE), (2, TWO)):
        data = connect(ctx, w).recv_all_until_close(timeout=1.5)
        if data != want:
            raise Fail(WA, f"cổng {w}: nhận {data!r}, mong đợi {want!r}")


@group("basic")
def test_server_stays_alive(ctx):
    """Phục vụ xong một client ở mỗi cổng, server vẫn sống và nhận tiếp"""
    expect(connect(ctx, 1), 1)
    expect(connect(ctx, 2), 2)
    ctx.expect_alive("sau hai client")
    expect(connect(ctx, 1), 1)


@group("edge")
def test_only_second_port_used(ctx):
    """Chỉ có client ở cổng 2 (cổng 1 không ai tới): vẫn được phục vụ ngay"""
    blocked_on(ctx, 2, 1)


@group("edge")
def test_only_first_port_used(ctx):
    """Chỉ có client ở cổng 1 (cổng 2 không ai tới): vẫn được phục vụ ngay"""
    blocked_on(ctx, 1, 2)


@group("edge")
@cases((2,), (1,), title="{0} client liền ở cổng này rồi cổng kia")
def test_many_same_port_then_other(ctx, first):
    other = 3 - first
    for i in range(8):
        expect(connect(ctx, first, f"a{i}"), first)
    for i in range(8):
        expect(connect(ctx, other, f"b{i}"), other)


@group("edge")
def test_client_leaves_immediately(ctx):
    """Client đóng ngay khi vừa kết nối (cả hai cổng): server sống, client sau vẫn được chào"""
    connect(ctx, 1, "roi1").close()
    connect(ctx, 2, "roi2").close()
    time.sleep(0.2)
    ctx.expect_alive("sau khi client rời đi sớm")
    expect(connect(ctx, 2, "sau2"), 2)
    expect(connect(ctx, 1, "sau1"), 1)


@group("robust")
def test_idle_first_port_client_does_not_block_second(ctx):
    """Client ở cổng 1 mở kết nối nhưng không đọc: client ở cổng 2 vẫn được phục vụ"""
    idle = connect(ctx, 1, "im-lang")
    expect(connect(ctx, 2), 2)
    idle.close()


@group("robust")
def test_idle_second_port_client_does_not_block_first(ctx):
    """Client ở cổng 2 mở kết nối nhưng không đọc: client ở cổng 1 vẫn được phục vụ"""
    idle = connect(ctx, 2, "im-lang")
    expect(connect(ctx, 1), 1)
    idle.close()


@group("concurrency")
def test_30_clients_each_port(ctx):
    """30 client ở mỗi cổng cùng lúc: tất cả được chào đúng lời của cổng mình"""
    cs = []
    for i in range(30):
        cs.append((1, connect(ctx, 1, f"a{i}")))
        cs.append((2, connect(ctx, 2, f"b{i}")))
    for w, c in cs:
        expect(c, w, timeout=2.0)


@group("concurrency")
def test_random_interleaving(ctx):
    """100 client, cổng chọn ngẫu nhiên, mở theo từng nhóm rồi mới đọc"""
    rng = ctx.rng
    for _ in range(10):
        batch = []
        for i in range(10):
            w = rng.choice((1, 2))
            batch.append((w, connect(ctx, w, f"r{i}")))
        rng.shuffle(batch)
        for w, c in batch:
            expect(c, w, timeout=2.0)
            ctx.close_quietly(c)


@group("stress")
@timeout(20)
def test_300_clients_fd_leak(ctx):
    """300 client lần lượt luân phiên hai cổng (bài nộp chỉ có 256 fd: quên close(client) là hết fd)"""
    for i in range(300):
        w = 1 + i % 2
        c = connect(ctx, w, f"c{i}")
        expect(c, w)
        ctx.close_quietly(c)


@group("stress")
@timeout(20)
def test_300_clients_one_port_only_then_other(ctx):
    """150 client chỉ ở cổng 2, rồi 150 client chỉ ở cổng 1"""
    for w in (2, 1):
        for i in range(150):
            c = connect(ctx, w, f"c{w}-{i}")
            expect(c, w)
            ctx.close_quietly(c)
