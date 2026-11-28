import time

from njlib import BLOCKED, WA, Fail, cases, group, sample, timeout

HELLO = b"Hello!\n"


def get_greeting(c, t0, lo=0.85, hi=2.0):
    """Client c (kết nối lúc t0) phải nhận đúng HELLO trong khoảng [lo, hi] giây sau t0, rồi bị đóng kết nối."""
    left = max(0.05, t0 + hi - time.monotonic())
    try:
        c.expect_bytes(HELLO, timeout=left)
    except Fail as f:
        if time.monotonic() - t0 >= hi - 0.05:
            raise Fail(BLOCKED, f"{c.name} chưa được chào sau {hi}s "
                                f"(server phục vụ lần lượt, hay truyền &client cho luồng?): {f.message}")
        raise
    took = time.monotonic() - t0
    if took < lo:
        raise Fail(WA, f"{c.name} được chào sau {took:.2f}s, đề yêu cầu đợi 1 giây (sleep(1)) trước khi gửi")
    c.expect_closed(timeout=1.0)


def connect_many(ctx, k, prefix="client"):
    t0 = time.monotonic()
    return t0, [ctx.connect(name=f"{prefix}{i + 1}") for i in range(k)]


@sample
def test_one_client(ctx):
    """Một client: sau khoảng 1 giây nhận Hello!\\n rồi bị đóng kết nối"""
    t0 = time.monotonic()
    c = ctx.connect()
    get_greeting(c, t0)


@sample
def test_two_clients_together(ctx):
    """Hai client cùng lúc: cả hai được chào sau khoảng 1 giây (không phải 1 rồi 2 giây)"""
    t0, cs = connect_many(ctx, 2)
    for c in cs:
        get_greeting(c, t0)


@group("basic")
def test_exactly_seven_bytes(ctx):
    """Lời chào đúng 7 byte, không có byte 0x00 hay byte thừa, rồi đóng"""
    t0 = time.monotonic()
    c = ctx.connect()
    data = c.recv_all_until_close(timeout=2.5)
    if data != HELLO:
        raise Fail(WA, f"nhận {data!r}, mong đợi {HELLO!r}")


@group("basic")
def test_five_clients(ctx):
    """Năm client cùng lúc đều được chào đúng hạn"""
    t0, cs = connect_many(ctx, 5)
    for c in cs:
        get_greeting(c, t0)


@group("basic")
def test_not_greeted_early(ctx):
    """Không được chào trước khi hết 1 giây"""
    c = ctx.connect()
    c.expect_silence(0.7)
    c.expect_bytes(HELLO, timeout=1.5)


@group("basic")
def test_server_stays_alive(ctx):
    """Phục vụ xong client đầu, server vẫn nhận client sau"""
    t0 = time.monotonic()
    get_greeting(ctx.connect(name="dau"), t0)
    ctx.expect_alive("sau khi chào client đầu tiên")
    t1 = time.monotonic()
    get_greeting(ctx.connect(name="sau"), t1)


@group("edge")
@cases((1,), (2,), (10,), (50,), title="{0} client cùng lúc")
def test_n_clients_together(ctx, k):
    t0, cs = connect_many(ctx, k)
    for c in cs:
        get_greeting(c, t0, hi=2.5)


@group("edge")
def test_client_leaves_before_greeting(ctx):
    """Client đóng kết nối ngay khi vừa kết nối: server vẫn sống, client sau vẫn được chào"""
    ctx.connect(name="roi-som").close()
    time.sleep(1.4)
    ctx.expect_alive("sau khi một client rời đi sớm")
    t0 = time.monotonic()
    get_greeting(ctx.connect(name="sau"), t0)


@group("edge")
def test_client_half_close(ctx):
    """Client shutdown chiều gửi ngay sau khi kết nối vẫn nhận được lời chào"""
    t0 = time.monotonic()
    c = ctx.connect()
    c.shutdown_write()
    get_greeting(c, t0)


@group("robust")
def test_leavers_do_not_disturb_stayers(ctx):
    """10 client bỏ đi ngay, 10 client ở lại: 10 client ở lại vẫn được chào đúng hạn"""
    t0 = time.monotonic()
    stay = []
    for i in range(10):
        ctx.connect(name=f"di{i}").close()
        stay.append(ctx.connect(name=f"o{i}"))
    for c in stay:
        get_greeting(c, t0, hi=2.5)
    ctx.expect_alive("sau khi 10 client rời đi sớm")


@group("robust")
def test_silent_client_does_not_block(ctx):
    """Client im lặng, không bao giờ đọc: client khác vẫn được chào đúng hạn"""
    silent = ctx.connect(name="im-lang")
    t0 = time.monotonic()
    other = ctx.connect(name="khac")
    get_greeting(other, t0)
    silent.close()


@group("concurrency")
def test_second_not_blocked_by_first(ctx):
    """A kết nối lúc 0s, B lúc 0,5s: A nhận ở ~1,0s, B nhận ở ~1,5s (B không phải chờ A xong rồi mới bắt đầu đếm)"""
    t0 = time.monotonic()
    a = ctx.connect(name="A")
    time.sleep(0.5)
    t1 = time.monotonic()
    b = ctx.connect(name="B")
    get_greeting(a, t0, hi=1.8)
    get_greeting(b, t1, hi=1.8)


@group("concurrency")
def test_staggered_five(ctx):
    """Năm client đến cách nhau 0,25 giây: mỗi client nhận sau ~1 giây kể từ lúc của nó"""
    cs = []
    for i in range(5):
        cs.append((time.monotonic(), ctx.connect(name=f"k{i + 1}")))
        time.sleep(0.25)
    for t, c in cs:
        get_greeting(c, t, hi=1.8)


@group("concurrency")
def test_each_gets_exactly_one_greeting(ctx):
    """30 client: mỗi client nhận đúng một lời chào của mình (không thiếu, không gấp đôi)"""
    t0, cs = connect_many(ctx, 30)
    for c in cs:
        data = c.recv_all_until_close(timeout=max(0.2, t0 + 2.5 - time.monotonic()))
        if data != HELLO:
            raise Fail(WA, f"{c.name} nhận {data!r}, mong đợi đúng một {HELLO!r} "
                           f"(các luồng có đang dùng chung một biến fd không?)")


@group("concurrency")
def test_fifty_clients(ctx):
    """50 client cùng lúc: tất cả được chào trong chưa đầy 2,5 giây"""
    t0, cs = connect_many(ctx, 50)
    for c in cs:
        get_greeting(c, t0, hi=2.5)


@group("concurrency")
def test_overlapping_waves(ctx):
    """4 đợt 10 client, mỗi đợt cách nhau 0,3 giây (các đợt chồng lên nhau)"""
    waves = []
    for w in range(4):
        t, cs = connect_many(ctx, 10, prefix=f"w{w + 1}c")
        waves.append((t, cs))
        time.sleep(0.3)
    for t, cs in waves:
        for c in cs:
            get_greeting(c, t, hi=2.0)


@group("stress")
@timeout(20)
def test_300_clients_fd_leak(ctx):
    """300 client (6 đợt x 50, mỗi đợt xong mới sang đợt sau). Bài nộp chỉ có 256 fd: quên close(client) là hết fd"""
    for r in range(6):
        t0, cs = connect_many(ctx, 50, prefix=f"d{r + 1}c")
        for c in cs:
            get_greeting(c, t0, hi=2.5)
            ctx.close_quietly(c)


@group("stress")
@timeout(15)
def test_random_arrivals(ctx):
    """60 client đến ngẫu nhiên trong 2 giây: mỗi client nhận sau ~1 giây kể từ lúc của nó"""
    rng = ctx.rng
    times = sorted(rng.uniform(0, 2.0) for _ in range(60))
    start = time.monotonic()
    cs = []
    for dt in times:
        wait = start + dt - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        cs.append((time.monotonic(), ctx.connect(name=f"r{len(cs) + 1}")))
    for t, c in cs:
        get_greeting(c, t, hi=2.0)
