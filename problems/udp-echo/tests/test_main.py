import os

from njlib import sample


@sample
def test_ping(ctx):
    """Echo một datagram"""
    u = ctx.udp()
    u.send("ping")
    u.expect("ping")


@sample
def test_two_clients(ctx):
    """Trả lời đúng người gửi"""
    a, b = ctx.udp("A"), ctx.udp("B")
    a.send("tu A")
    b.send("tu B")
    a.expect("tu A")
    b.expect("tu B")
    a.expect_nothing(0.2)


def test_binary(ctx):
    """Dữ liệu nhị phân 2048 byte có byte 0"""
    u = ctx.udp()
    blob = os.urandom(2047) + b"\x00"
    u.send(blob)
    u.expect(blob)


def test_empty_datagram(ctx):
    """Datagram rỗng: trả lời datagram rỗng và server vẫn chạy tiếp"""
    u = ctx.udp()
    u.send(b"")
    u.expect(b"")
    u.send("sau rong")
    u.expect("sau rong")


def test_many(ctx):
    """100 datagram liên tiếp từ 5 client"""
    us = [ctx.udp(f"U{i}") for i in range(5)]
    for k in range(20):
        for i, u in enumerate(us):
            u.send(f"{i}-{k}")
        for i, u in enumerate(us):
            u.expect(f"{i}-{k}")
