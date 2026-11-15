import os
import time

from njlib import sample


@sample
def test_text(ctx):
    """Echo một dòng chữ"""
    c = ctx.connect()
    c.send("xin chao\n")
    c.expect_line("xin chao")


@sample
def test_binary(ctx):
    """Dữ liệu nhị phân có byte 0x00"""
    c = ctx.connect()
    data = b"\x00\xffA\x00\x00B\n\r\x01"
    c.send(data)
    c.expect_bytes(data)


def test_many_messages(ctx):
    """Nhiều lần gửi liên tiếp trên một kết nối"""
    c = ctx.connect()
    for i in range(50):
        c.send(f"msg {i}\n")
        c.expect_line(f"msg {i}")


def test_large(ctx):
    """Khối dữ liệu lớn 256 KB, gửi và đọc xen kẽ"""
    c = ctx.connect()
    blob = os.urandom(256 * 1024)
    step = 16 * 1024
    for i in range(0, len(blob), step):
        c.send(blob[i:i + step])
        c.expect_bytes(blob[i:i + step], timeout=2)


def test_sequential_clients(ctx):
    """Client sau được phục vụ khi client trước đã đóng"""
    for i in range(5):
        c = ctx.connect(name=f"client{i + 1}")
        c.send(f"lan {i}\n")
        c.expect_line(f"lan {i}")
        c.close()
        time.sleep(0.05)


def test_client_closes_silently(ctx):
    """Client kết nối rồi đóng ngay không gửi gì, server vẫn sống"""
    a = ctx.connect(name="A")
    a.close()
    time.sleep(0.1)
    b = ctx.connect(name="B")
    b.send("con song khong\n")
    b.expect_line("con song khong")
