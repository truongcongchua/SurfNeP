from njlib import sample


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


def test_large(ctx):
    """Datagram 60000 byte và 65507 byte không bị cắt cụt"""
    a = ctx.udp("A")
    a.send(b"x" * 60000)
    a.expect("LEN 60000 1")
    a.send(b"\x00" * 65507)
    a.expect("LEN 65507 2")


def test_per_sender_counter(ctx):
    """Số thứ tự đếm riêng cho từng người gửi"""
    a, b = ctx.udp("A"), ctx.udp("B")
    a.send("1")
    a.expect("LEN 1 1")
    b.send("22")
    b.expect("LEN 2 1")
    a.send("333")
    a.expect("LEN 3 2")
    b.send("")
    b.expect("LEN 0 2")


def test_burst(ctx):
    """Một người gửi bắn 50 datagram liên tục"""
    a = ctx.udp("A")
    for i in range(50):
        a.send(b"y" * i)
    for i in range(50):
        a.expect(f"LEN {i} {i + 1}")


def test_many_senders(ctx):
    """100 người gửi khác nhau"""
    us = [ctx.udp(f"U{i}") for i in range(100)]
    for r in range(1, 3):
        for i, u in enumerate(us):
            u.send(b"z" * i)
        for i, u in enumerate(us):
            u.expect(f"LEN {i} {r}")
