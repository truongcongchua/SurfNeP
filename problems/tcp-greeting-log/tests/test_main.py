import os
import time

from njlib import Fail, WA, cases, group, sample, timeout

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


@group("basic")
def test_append_two_clients(ctx):
    """Hai client lần lượt: log ghi nối tiếp, không ghi đè"""
    for data in [b"client1 noi\n", b"client2 noi\n"]:
        c = ctx.connect()
        c.expect_bytes(GREETING)
        c.send(data)
        c.close()
        time.sleep(0.15)
    wait_log(ctx, b"client1 noi\nclient2 noi\n")


@group("basic")
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


@group("stress")
def test_large_upload(ctx):
    """Client gửi 100 KB, log chứa đủ"""
    c = ctx.connect()
    c.expect_bytes(GREETING)
    blob = b"".join(b"%05d:" % i + b"z" * 45 + b"\n" for i in range(2000))
    c.send(blob)
    c.close()
    wait_log(ctx, blob, timeout=3)


@group("basic")
def test_log_preexisting(ctx):
    """log.txt đã có sẵn nội dung thì ghi tiếp vào cuối"""
    with open(os.path.join(ctx.workdir, "log.txt"), "wb") as fh:
        fh.write(b"cu\n")
    c = ctx.connect()
    c.expect_bytes(GREETING)
    c.send("moi\n")
    c.close()
    wait_log(ctx, b"cu\nmoi\n")


# ======================= phần mở rộng (thiết kế lại) =======================

def set_greeting(ctx, data):
    with open(os.path.join(ctx.workdir, "greeting.txt"), "wb") as fh:
        fh.write(data)


def visit(ctx, data, greeting, name=None):
    c = ctx.connect(name=name)
    c.expect_bytes(greeting, timeout=3)
    if data:
        c.send(data)
    c.close()
    return c


@group("edge")
@cases(0, 1, 4095, 4096, 4097, 8192, 100000, title="Câu chào {0} byte (đọc lại từ tệp cho client mới)")
def test_greeting_sizes(ctx, n):
    data = bytes(ctx.rng.randrange(256) for _ in range(n))
    # client đầu tiên nhận câu chào gốc; đổi tệp rồi client sau phải nhận đúng n byte mới
    visit(ctx, b"", GREETING, "dau")
    set_greeting(ctx, data)
    time.sleep(0.05)
    c = ctx.connect(name="sau")
    if n:
        c.expect_bytes(data, timeout=3)
    c.expect_silence(0.15)  # không được gửi thừa byte nào
    c.send(b"z")
    c.close()
    wait_log(ctx, b"z")


@group("edge")
def test_greeting_with_nul(ctx):
    """Câu chào chứa byte 0x00 và không có xuống dòng cuối (không dùng fgets/strlen)"""
    data = b"Xin\x00chao\x00\x00\xff\xfe nhi phan"
    set_greeting(ctx, data)
    c = ctx.connect()
    c.expect_bytes(data)


@group("edge")
def test_empty_session_adds_nothing(ctx):
    """Client không gửi gì: log không được thêm byte nào"""
    with open(os.path.join(ctx.workdir, "log.txt"), "wb") as fh:
        fh.write(b"cu\n")
    for _ in range(3):
        visit(ctx, b"", GREETING)
        time.sleep(0.05)
    visit(ctx, b"x", GREETING)
    wait_log(ctx, b"cu\nx")


@group("edge")
def test_binary_upload(ctx):
    """Dữ liệu client gửi là nhị phân có 0x00, không có xuống dòng cuối: ghi đúng từng byte"""
    blob = bytes(range(256)) * 20
    visit(ctx, blob, GREETING)
    wait_log(ctx, blob)


@group("stream")
def test_fragmented_upload(ctx):
    """Dữ liệu đến thành mảnh ngẫu nhiên 1–7 byte"""
    rng = ctx.rng
    c = ctx.connect()
    c.expect_bytes(GREETING)
    data = bytes(rng.randrange(256) for _ in range(3000))
    c.send_chunks(data, rng, 1, 7, delay=0)
    c.close()
    wait_log(ctx, data)


@group("stream")
def test_send_before_reading_greeting(ctx):
    """Client gửi dữ liệu ngay khi kết nối, chưa đọc câu chào"""
    c = ctx.connect()
    c.send(b"gui truoc\n")
    c.expect_bytes(GREETING)
    c.send(b"gui sau\n")
    c.close()
    wait_log(ctx, b"gui truoc\ngui sau\n")


@group("robust")
def test_reset_clients(ctx):
    """Client nhận câu chào, gửi một ít rồi RST (mất kết nối): server sống, phục vụ client sau"""
    set_greeting(ctx, b"G" * 300000)
    for k in range(3):
        c = ctx.connect(name=f"rst{k}")
        c.expect_bytes(b"G" * 300000, timeout=3)
        c.send(b"mot it\n")
        time.sleep(0.05)
        c.reset()
        time.sleep(0.1)
    time.sleep(0.2)
    ctx.expect_alive("sau khi client đóng đột ngột")
    set_greeting(ctx, b"hi\n")
    c = ctx.connect(name="sau")
    c.expect_bytes(b"hi\n")


@group("stress")
@timeout(25)
def test_300_clients_fd_leak(ctx):
    """300 client lần lượt (mở tệp mà quên đóng là hết 256 fd)"""
    want = b""
    for i in range(300):
        line = b"%d\n" % i
        visit(ctx, line, GREETING, f"C{i}")
        want += line
        ctx.close_quietly(ctx._conns[-1])
    wait_log(ctx, want, timeout=3)
