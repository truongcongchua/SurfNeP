import os
import time

from njlib import Fail, WA, expects_exit, group, sample


def _exits_ok(ctx):
    try:
        code = ctx.server.proc.wait(timeout=1.5)
    except Exception:
        raise Fail(WA, "server phải kết thúc sau khi echo xong và đóng kết nối")
    if code != 0:
        raise Fail(WA, f"server phải thoát với mã 0, nhận được {code}")


def roundtrip(ctx, data, name="client"):
    c = ctx.connect(name=name)
    c.send(data)
    c.expect_bytes(data, timeout=1.5)
    c.expect_closed(timeout=1.5)
    _exits_ok(ctx)


@sample
@expects_exit
def test_echo_line(ctx):
    """Echo một dòng chữ, rồi server đóng kết nối và thoát mã 0"""
    roundtrip(ctx, b"xin chao\n")


@sample
@expects_exit
def test_binary(ctx):
    """3 byte nhị phân 00 FF 41 (có 0x00): phải gửi lại đúng từng byte"""
    roundtrip(ctx, b"\x00\xff\x41")


@group("basic")
@expects_exit
def test_single_byte(ctx):
    """Một byte duy nhất"""
    roundtrip(ctx, b"z")


@group("basic")
@expects_exit
def test_all_byte_values(ctx):
    """Đủ 256 giá trị byte (0x00 .. 0xFF)"""
    roundtrip(ctx, bytes(range(256)))


@group("edge")
@expects_exit
def test_near_buffer_size(ctx):
    """1000 byte ngẫu nhiên gửi một lần (gần cỡ bộ đệm 1024)"""
    roundtrip(ctx, os.urandom(1000))


@group("edge")
@expects_exit
def test_starts_with_nul(ctx):
    """Dữ liệu bắt đầu bằng byte 0x00 (strlen = 0)"""
    roundtrip(ctx, b"\x00\x00abc\x00\n")


@group("basic")
@expects_exit
def test_waits_for_data(ctx):
    """Client chưa gửi ngay: server chờ ở recv, không gửi gì trước khi nhận"""
    c = ctx.connect()
    c.expect_silence(0.4)
    ctx.expect_alive("khi đang chờ client gửi dữ liệu (server phải chờ ở recv)")
    c.send(b"den roi\n")
    c.expect_bytes(b"den roi\n", timeout=1.5)
    c.expect_closed(timeout=1.5)
    _exits_ok(ctx)


@group("edge")
@expects_exit
def test_client_sends_nothing(ctx):
    """Client kết nối rồi đóng luôn không gửi gì (recv trả 0): server không treo, thoát mã 0"""
    ctx.connect().close()
    _exits_ok(ctx)
