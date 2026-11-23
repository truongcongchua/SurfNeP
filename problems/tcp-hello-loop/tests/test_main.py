import time

from njlib import group, sample, timeout


def hello(k):
    return f"Hello, client {k}!\n".encode()


def expect_hello(c, k):
    c.expect_bytes(hello(k), timeout=2)
    c.expect_closed(timeout=1.5)


@sample
def test_first_client(ctx):
    """Client đầu tiên nhận đúng câu chào số 1 rồi bị đóng kết nối"""
    c = ctx.connect()
    expect_hello(c, 1)


@sample
def test_three_clients(ctx):
    """Ba client lần lượt nhận số thứ tự 1, 2, 3"""
    for k in (1, 2, 3):
        c = ctx.connect(name=f"client{k}")
        expect_hello(c, k)
        c.close()


@group("basic")
def test_server_stays_alive(ctx):
    """Server không thoát sau client đầu tiên"""
    expect_hello(ctx.connect(), 1)
    time.sleep(0.2)
    ctx.expect_alive("sau khi chào client đầu tiên (server không được thoát)")
    expect_hello(ctx.connect(), 2)


@group("basic")
def test_clients_queue_in_order(ctx):
    """Hai client kết nối gần như cùng lúc: được chào lần lượt theo thứ tự kết nối"""
    a = ctx.connect(name="A")
    b = ctx.connect(name="B")
    expect_hello(a, 1)
    expect_hello(b, 2)


@group("edge")
def test_client_never_sends(ctx):
    """Client không gửi gì cả vẫn được chào ngay (server không chờ recv)"""
    c = ctx.connect()
    c.expect_bytes(hello(1), timeout=1)


@group("edge")
def test_client_leaves_early(ctx):
    """Ba client đóng ngay không đọc: số thứ tự vẫn tăng, client sau vẫn được chào"""
    for _ in range(3):
        ctx.connect().close()
        time.sleep(0.1)
    expect_hello(ctx.connect(name="sau"), 4)


@group("stress")
@timeout(20)
def test_300_clients_fd_leak(ctx):
    """300 client lần lượt (bài nộp chỉ có 256 file descriptor: quên close(client) là hết fd)"""
    for k in range(1, 301):
        c = ctx.connect(name=f"client{k}")
        expect_hello(c, k)
        ctx.close_quietly(c)
