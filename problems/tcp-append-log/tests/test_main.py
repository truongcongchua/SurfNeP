import os
import time

from njlib import Fail, WA, group, sample, timeout


def wait_log(ctx, want, timeout=1.5, poll=0.05):
    deadline = time.monotonic() + timeout
    got = None
    while time.monotonic() < deadline:
        try:
            with open(os.path.join(ctx.workdir, "log.txt"), "rb") as fh:
                got = fh.read()
        except FileNotFoundError:
            got = None
        if got == want:
            return
        time.sleep(poll)
    if got is None:
        raise Fail(WA, "log.txt chưa được tạo")
    raise Fail(WA, f"log.txt chứa {got[:200]!r} ({len(got)} byte), mong đợi {want[:200]!r} ({len(want)} byte)")


def visit(ctx, data, name=None):
    c = ctx.connect(name=name)
    if data:
        c.send(data)
    c.close()
    return c


@sample
def test_one_client(ctx):
    """Dữ liệu của client được ghi vào log"""
    c = ctx.connect()
    c.send("abc\n")
    c.send("dong thu hai\n")
    c.close()
    wait_log(ctx, b"abc\ndong thu hai\n")


@sample
def test_two_clients(ctx):
    """Hai client lần lượt: log ghi nối tiếp, không ghi đè"""
    for data in [b"client1 noi\n", b"client2 noi\n"]:
        visit(ctx, data)
        time.sleep(0.15)
    wait_log(ctx, b"client1 noi\nclient2 noi\n")


@group("basic")
def test_log_preexisting(ctx):
    """log.txt đã có sẵn nội dung thì ghi tiếp vào cuối"""
    with open(os.path.join(ctx.workdir, "log.txt"), "wb") as fh:
        fh.write(b"cu\n")
    visit(ctx, b"moi\n")
    wait_log(ctx, b"cu\nmoi\n")


@group("basic")
def test_server_sends_nothing(ctx):
    """Server không gửi gì cho client"""
    c = ctx.connect()
    c.send("abc\n")
    c.expect_silence(0.3)
    c.close()
    wait_log(ctx, b"abc\n")


@group("edge")
def test_empty_session_adds_nothing(ctx):
    """Client không gửi gì: log không được thêm byte nào"""
    with open(os.path.join(ctx.workdir, "log.txt"), "wb") as fh:
        fh.write(b"cu\n")
    for _ in range(3):
        visit(ctx, b"")
        time.sleep(0.05)
    visit(ctx, b"x")
    wait_log(ctx, b"cu\nx")


@group("edge")
def test_binary_upload(ctx):
    """Dữ liệu nhị phân có 0x00, không có xuống dòng cuối: ghi đúng từng byte"""
    blob = bytes(range(256)) * 20
    visit(ctx, blob)
    wait_log(ctx, blob)


@group("stream")
def test_fragmented_upload(ctx):
    """Dữ liệu đến thành mảnh ngẫu nhiên 1–7 byte"""
    c = ctx.connect()
    data = bytes(ctx.rng.randrange(256) for _ in range(3000))
    c.send_chunks(data, ctx.rng, 1, 7, delay=0)
    c.close()
    wait_log(ctx, data)


@group("stress")
def test_large_upload(ctx):
    """Client gửi 100 KB, log chứa đủ (phải recv trong vòng lặp)"""
    blob = b"".join(b"%05d:" % i + b"z" * 45 + b"\n" for i in range(2000))
    visit(ctx, blob)
    wait_log(ctx, blob, timeout=3)


@group("stress")
@timeout(25)
def test_300_clients_fd_leak(ctx):
    """300 client lần lượt (quên close tệp hoặc close(client) là hết 256 fd)"""
    want = b""
    for i in range(300):
        line = b"%d\n" % i
        c = visit(ctx, line, f"C{i}")
        want += line
        ctx.close_quietly(c)
        wait_log(ctx, want, timeout=2, poll=0.002)  # đợi server ghi xong client này rồi mới sang client sau
