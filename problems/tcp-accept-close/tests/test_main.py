import time

from njlib import Fail, WA, expects_exit, group, sample


def _exits_ok(ctx):
    try:
        code = ctx.server.proc.wait(timeout=1.5)
    except Exception:
        raise Fail(WA, "server phải kết thúc sau khi đã đón một client và đóng kết nối")
    if code != 0:
        raise Fail(WA, f"server phải thoát với mã 0, nhận được {code}")


@sample
@expects_exit
def test_accept_and_close(ctx):
    """Một client kết nối: server đóng kết nối, không gửi gì, rồi thoát mã 0"""
    c = ctx.connect()
    c.expect_closed(timeout=1.5)
    _exits_ok(ctx)


@group("basic")
@expects_exit
def test_waits_in_accept(ctx):
    """Chưa có client thì server phải đứng chờ ở accept (không được thoát hay tự đóng)"""
    time.sleep(0.5)
    ctx.expect_alive("khi chưa có client nào kết nối (server phải chờ ở accept)")
    c = ctx.connect()
    c.expect_closed(timeout=1.5)
    _exits_ok(ctx)


@group("basic")
@expects_exit
def test_sends_nothing(ctx):
    """Server không gửi bất cứ dữ liệu nào cho client"""
    c = ctx.connect()
    data = c.recv_all_until_close(timeout=1.5)
    if data:
        raise Fail(WA, f"server không được gửi dữ liệu, nhưng đã gửi {data!r}")
    _exits_ok(ctx)
