# Thiết kế: docs/TEST-DESIGN.md
import os

from njlib import cases, group, sample, timeout


@sample
def test_basic(ctx):
    """Hai datagram gửi liền nhau thì có hai phản hồi riêng"""
    a = ctx.udp("A")
    a.send("hello")
    a.send("abc")
    a.expect("LEN 5 1")
    a.expect("LEN 3 2")


@sample
def test_empty(ctx):
    """Datagram rỗng"""
    a = ctx.udp("A")
    a.send(b"")
    a.expect("LEN 0 1")


@group("edge")
@cases(1, 2047, 2048, 4095, 4096, 8192, 16384, 32768, 60000, 65506, 65507, title="Datagram {0} byte không bị cắt cụt")
def test_sizes(ctx, n):
    a = ctx.udp("A")
    a.send(b"\x00" + os.urandom(n - 1))
    a.expect(f"LEN {n} 1")
    a.send(b"x")
    a.expect("LEN 1 2")


@group("edge")
def test_large(ctx):
    """Datagram 60000 byte và 65507 byte liên tiếp"""
    a = ctx.udp("A")
    a.send(b"x" * 60000)
    a.expect("LEN 60000 1")
    a.send(b"\x00" * 65507)
    a.expect("LEN 65507 2")


@group("basic")
def test_per_sender_counter(ctx):
    """Số thứ tự đếm riêng cho từng người gửi (cùng IP, khác cổng)"""
    a, b = ctx.udp("A"), ctx.udp("B")
    a.send("1")
    a.expect("LEN 1 1")
    b.send("22")
    b.expect("LEN 2 1")
    a.send("333")
    a.expect("LEN 3 2")
    b.send("")
    b.expect("LEN 0 2")


@group("basic")
def test_nul_bytes_counted(ctx):
    """Byte 0x00 cũng được đếm (không dùng strlen)"""
    a = ctx.udp("A")
    a.send(b"ab\x00cd\x00")
    a.expect("LEN 6 1")
    a.send(b"\x00")
    a.expect("LEN 1 2")


@group("basic")
def test_new_socket_new_counter(ctx):
    """Socket mới (cổng mới) là người gửi mới: đếm lại từ 1"""
    for k in range(3):
        u = ctx.udp(f"S{k}")
        for i in range(1, 4):
            u.send("q")
            u.expect(f"LEN 1 {i}")
        u.close()


@group("stream")
def test_burst(ctx):
    """Một người gửi bắn 50 datagram liên tục"""
    a = ctx.udp("A")
    for i in range(50):
        a.send(b"y" * i)
    for i in range(50):
        a.expect(f"LEN {i} {i + 1}")


@group("stream")
def test_random_sizes_burst(ctx):
    """60 datagram kích thước ngẫu nhiên 0–1500 gửi dồn (tổng < bộ đệm nhận, để không bị rơi gói hợp lệ)"""
    rng = ctx.rng
    a = ctx.udp("A")
    sizes = [rng.randint(0, 1500) for _ in range(60)]
    for n in sizes:
        a.send(b"r" * n)
    for i, n in enumerate(sizes, 1):
        a.expect(f"LEN {n} {i}")


@group("concurrency")
def test_many_senders(ctx):
    """100 người gửi khác nhau"""
    us = [ctx.udp(f"U{i}") for i in range(100)]
    for r in range(1, 3):
        for i, u in enumerate(us):
            u.send(b"z" * i)
        for i, u in enumerate(us):
            u.expect(f"LEN {i} {r}")


@group("concurrency")
def test_interleaved_random(ctx):
    """20 người gửi, 300 datagram xen kẽ ngẫu nhiên: bộ đếm từng người luôn đúng"""
    rng = ctx.rng
    us = [ctx.udp(f"U{i}") for i in range(20)]
    cnt = [0] * 20
    for _ in range(300):
        i = rng.randrange(20)
        n = rng.randint(0, 3000)
        us[i].send(b"k" * n)
        cnt[i] += 1
        us[i].expect(f"LEN {n} {cnt[i]}")


@group("stress")
@timeout(12)
def test_counter_large(ctx):
    """Bộ đếm vượt 1000 (không bị tràn kiểu nhỏ / cắt chuỗi)"""
    a = ctx.udp("A")
    for i in range(1, 1201):
        a.send(b"c")
        if i % 100 == 0:
            for j in range(i - 99, i + 1):
                a.expect(f"LEN 1 {j}")
