# Thiết kế: docs/TEST-DESIGN.md
import os
import time

from njlib import WA, Fail, cases, group, sample, timeout


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


@group("basic")
def test_binary(ctx):
    """Dữ liệu nhị phân 2048 byte có byte 0"""
    u = ctx.udp()
    blob = os.urandom(2047) + b"\x00"
    u.send(blob)
    u.expect(blob)


@group("basic")
def test_nul_first(ctx):
    """Datagram bắt đầu bằng 0x00 (strlen = 0) và datagram toàn 0x00"""
    u = ctx.udp()
    for d in (b"\x00abc", b"\x00" * 100, b"a\x00b\x00"):
        u.send(d)
        u.expect(d)


@group("basic")
def test_order_and_boundaries(ctx):
    """10 datagram gửi liền: 10 phản hồi riêng, đúng thứ tự, không gộp"""
    u = ctx.udp()
    msgs = [f"m{i}".encode() * (i + 1) for i in range(10)]
    for m in msgs:
        u.send(m)
    for m in msgs:
        u.expect(m)


@group("edge")
@cases(0, 1, 2, 255, 256, 1023, 1024, 1025, 2047, 2048, title="Datagram {0} byte")
def test_sizes(ctx, n):
    u = ctx.udp()
    d = bytes(ctx.rng.randrange(256) for _ in range(n))
    u.send(d)
    u.expect(d)


@group("edge")
def test_empty_datagram(ctx):
    """Datagram rỗng: trả lời datagram rỗng và server vẫn chạy tiếp"""
    u = ctx.udp()
    for _ in range(3):
        u.send(b"")
        u.expect(b"")
    u.send("sau rong")
    u.expect("sau rong")


@group("robust")
def test_sender_gone(ctx):
    """Người gửi đóng socket trước khi nhận phản hồi: server không bị ảnh hưởng"""
    for k in range(5):
        g = ctx.udp(f"di{k}")
        g.send(b"x" * 1000)
        g.close()
    time.sleep(0.2)
    ctx.expect_alive("sau khi người gửi biến mất")
    u = ctx.udp("sau")
    u.send("con song")
    u.expect("con song")


@group("concurrency")
def test_many_interleaved(ctx):
    """30 client gửi xen kẽ ngẫu nhiên: mỗi client chỉ nhận đúng datagram của mình"""
    rng = ctx.rng
    us = [ctx.udp(f"U{i}") for i in range(30)]
    for k in range(10):
        order = list(range(30))
        rng.shuffle(order)
        for i in order:
            us[i].send(f"{i}-{k}")
        for i in order:
            us[i].expect(f"{i}-{k}")
    for u in us:
        u.expect_nothing(0.01)


@group("concurrency")
def test_new_client_after_others(ctx):
    """Client mới xuất hiện sau khi các client khác đã biến mất vẫn được trả lời đúng địa chỉ"""
    for i in range(5):
        u = ctx.udp(f"cu{i}")
        u.send(f"cu {i}")
        u.expect(f"cu {i}")
        u.close()
    n = ctx.udp("moi")
    n.send("moi")
    n.expect("moi")


@group("stress")
@timeout(10)
def test_burst_200(ctx):
    """200 datagram bắn liên tục rồi mới đọc"""
    u = ctx.udp()
    msgs = [os.urandom(ctx.rng.randint(0, 500)) for _ in range(200)]
    for m in msgs:
        u.send(m)
    for m in msgs:
        u.expect(m)


@group("stress")
@timeout(12)
def test_5000_roundtrips(ctx):
    """5000 lượt gửi-nhận từ 5 client"""
    us = [ctx.udp(f"U{i}") for i in range(5)]
    for k in range(1000):
        for i, u in enumerate(us):
            u.send(f"{i}-{k}")
        for i, u in enumerate(us):
            got = u.recv(timeout=1.0)
            if got != f"{i}-{k}".encode():
                raise Fail(WA, f"U{i}: mong đợi {i}-{k}, nhận {got[:40]!r}")
