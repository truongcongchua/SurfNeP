import os
import time

from njlib import Fail, WA, sample

GREETING = open(os.path.join(os.path.dirname(__file__), "..", "files", "greeting.txt"), "rb").read()


def wait_log(ctx, want, timeout=1.5):
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
        time.sleep(0.05)
    if got is None:
        raise Fail(WA, "log.txt chưa được tạo")
    raise Fail(WA, f"log.txt chứa {got[:200]!r}, mong đợi {want[:200]!r}")


@sample
def test_greeting(ctx):
    """Client nhận đúng toàn bộ câu chào"""
    c = ctx.connect()
    c.expect_bytes(GREETING)


@sample
def test_log_one_client(ctx):
    """Dữ liệu của client được ghi vào log"""
    c = ctx.connect()
    c.expect_bytes(GREETING)
    c.send("abc\n")
    c.send("dong thu hai\n")
    c.close()
    wait_log(ctx, b"abc\ndong thu hai\n")


def test_append_two_clients(ctx):
    """Hai client lần lượt: log ghi nối tiếp, không ghi đè"""
    for data in [b"client1 noi\n", b"client2 noi\n"]:
        c = ctx.connect()
        c.expect_bytes(GREETING)
        c.send(data)
        c.close()
        time.sleep(0.15)
    wait_log(ctx, b"client1 noi\nclient2 noi\n")


def test_greeting_reread(ctx):
    """Tệp câu chào thay đổi giữa hai client thì client sau nhận câu chào mới"""
    a = ctx.connect(name="A")
    a.expect_bytes(GREETING)
    a.close()
    new = "Cau chao moi\n".encode()
    with open(os.path.join(ctx.workdir, "greeting.txt"), "wb") as fh:
        fh.write(new)
    time.sleep(0.1)
    b = ctx.connect(name="B")
    b.expect_bytes(new)


def test_large_upload(ctx):
    """Client gửi 100 KB, log chứa đủ"""
    c = ctx.connect()
    c.expect_bytes(GREETING)
    blob = b"".join(b"%05d:" % i + b"z" * 45 + b"\n" for i in range(2000))
    c.send(blob)
    c.close()
    wait_log(ctx, blob, timeout=3)


def test_log_preexisting(ctx):
    """log.txt đã có sẵn nội dung thì ghi tiếp vào cuối"""
    with open(os.path.join(ctx.workdir, "log.txt"), "wb") as fh:
        fh.write(b"cu\n")
    c = ctx.connect()
    c.expect_bytes(GREETING)
    c.send("moi\n")
    c.close()
    wait_log(ctx, b"cu\nmoi\n")
