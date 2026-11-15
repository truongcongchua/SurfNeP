import os
import struct
import time

from njlib import sample


def frame(payload):
    return struct.pack(">I", len(payload)) + payload


def upper(payload):
    return bytes(b - 32 if 97 <= b <= 122 else b for b in payload)


def roundtrip(c, payload, timeout=1.0):
    c.send(frame(payload))
    c.expect_bytes(frame(upper(payload)), timeout)


@sample
def test_hello(ctx):
    """Một thông điệp đơn giản"""
    c = ctx.connect()
    roundtrip(c, b"hello")


@sample
def test_empty(ctx):
    """Thông điệp rỗng L = 0"""
    c = ctx.connect()
    roundtrip(c, b"")
    roundtrip(c, b"sau rong")


def test_header_byte_by_byte(ctx):
    """Phần độ dài và dữ liệu đến từng byte"""
    c = ctx.connect()
    msg = b"tung byte mot\nco xuong dong"
    c.send_slowly(frame(msg), chunk=1, delay=0.01)
    c.expect_bytes(frame(upper(msg)))


def test_coalesced(ctx):
    """Ba thông điệp dính trong một lần gửi"""
    c = ctx.connect()
    msgs = [b"mot", b"", b"ba \x00\xff abc"]
    c.send(b"".join(frame(m) for m in msgs))
    c.expect_bytes(b"".join(frame(upper(m)) for m in msgs))


def test_max_binary(ctx):
    """Thông điệp 65536 byte nhị phân"""
    c = ctx.connect()
    blob = os.urandom(65536)
    c.send(frame(blob))
    c.expect_bytes(frame(upper(blob)), timeout=3)


def test_split_across_messages(ctx):
    """Ranh giới gửi rơi vào giữa thông điệp"""
    c = ctx.connect()
    data = frame(b"abcdef") + frame(b"ghij")
    c.send(data[:7])
    time.sleep(0.05)
    c.send(data[7:13])
    time.sleep(0.05)
    c.send(data[13:])
    c.expect_bytes(frame(b"ABCDEF") + frame(b"GHIJ"))


def test_too_long_closes(ctx):
    """L > 65536 thì đóng kết nối, client sau vẫn được phục vụ"""
    a = ctx.connect(name="A")
    a.send(struct.pack(">I", 65537) + b"xx")
    a.expect_closed(timeout=1.5)
    b = ctx.connect(name="B")
    roundtrip(b, b"van song")
