# Thiết kế: docs/TEST-DESIGN.md
import os
import struct
import time

from njlib import WA, Fail, cases, group, sample, timeout


def frame(payload):
    return struct.pack(">I", len(payload)) + payload


def upper(payload):
    return bytes(b - 32 if 97 <= b <= 122 else b for b in payload)


def roundtrip(c, payload, timeout=1.5):
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


# ---------------- basic ----------------

@group("basic")
def test_all_byte_values(ctx):
    """Đủ 256 giá trị byte: chỉ a–z được đổi, mọi byte khác (kể cả 0x00, '\\n', byte ≥ 0x80) giữ nguyên"""
    c = ctx.connect()
    roundtrip(c, bytes(range(256)) * 3)


@group("basic")
def test_many_on_one_connection(ctx):
    """50 thông điệp hỏi-đáp liên tiếp trên một kết nối"""
    c = ctx.connect()
    for i in range(50):
        roundtrip(c, f"thong diep so {i}".encode())


@group("basic")
def test_sequential_clients(ctx):
    """5 client lần lượt"""
    for i in range(5):
        c = ctx.connect(name=f"C{i}")
        roundtrip(c, f"client {i}".encode())
        c.close()


# ---------------- edge ----------------

@group("edge")
@cases(1, 3, 4, 255, 256, 257, 1023, 1024, 4095, 4096, 4097, 65535, 65536, title="L = {0}")
def test_length(ctx, n):
    c = ctx.connect()
    roundtrip(c, os.urandom(n), timeout=3)


@group("edge")
@cases(65537, 100000, 0x01000000, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF,
       title="L = {0} (> 65536, kể cả bit cao nếu đọc nhầm thành số âm): đóng kết nối, phục vụ client sau")
def test_too_long_closes(ctx, n):
    a = ctx.connect(name="A")
    a.send(struct.pack(">I", n) + b"xx")
    a.expect_closed(timeout=1.5)
    b = ctx.connect(name="B")
    roundtrip(b, b"van song")


@group("edge")
def test_too_long_after_good(ctx):
    """Vài thông điệp đúng rồi một thông điệp quá dài: trả lời đủ phần đúng rồi mới đóng"""
    a = ctx.connect()
    a.send(frame(b"mot") + frame(b"hai") + struct.pack(">I", 70000))
    a.expect_bytes(frame(b"MOT") + frame(b"HAI"))
    a.expect_closed(timeout=1.5)


# ---------------- stream ----------------

@group("stream")
def test_header_byte_by_byte(ctx):
    """Phần độ dài và dữ liệu đến từng byte"""
    c = ctx.connect()
    msg = b"tung byte mot\nco xuong dong"
    c.send_slowly(frame(msg), chunk=1, delay=0.01)
    c.expect_bytes(frame(upper(msg)))


@group("stream")
def test_coalesced(ctx):
    """Ba thông điệp dính trong một lần gửi"""
    c = ctx.connect()
    msgs = [b"mot", b"", b"ba \x00\xff abc"]
    c.send(b"".join(frame(m) for m in msgs))
    c.expect_bytes(b"".join(frame(upper(m)) for m in msgs))


@group("stream")
def test_split_across_messages(ctx):
    """Ranh giới gửi rơi vào giữa phần độ dài và giữa dữ liệu"""
    c = ctx.connect()
    data = frame(b"abcdef") + frame(b"ghij")
    for a, b in [(0, 2), (2, 7), (7, 11), (11, 13), (13, len(data))]:
        c.send(data[a:b])
        time.sleep(0.03)
    c.expect_bytes(frame(b"ABCDEF") + frame(b"GHIJ"))


@group("stream")
def test_random_fragments(ctx):
    """200 thông điệp kích thước ngẫu nhiên 0–300, cắt thành mảnh ngẫu nhiên 1–11 byte"""
    rng = ctx.rng
    c = ctx.connect()
    msgs = [bytes(rng.randrange(256) for _ in range(rng.randint(0, 300))) for _ in range(200)]
    c.send_chunks(b"".join(frame(m) for m in msgs), rng, 1, 11, delay=0)
    c.expect_bytes(b"".join(frame(upper(m)) for m in msgs), timeout=3)


@group("stream")
def test_big_message_slow_chunks(ctx):
    """65536 byte đến thành mảnh 1000 byte có độ trễ"""
    c = ctx.connect()
    blob = os.urandom(65536)
    data = frame(blob)
    for i in range(0, len(data), 1000):
        c.send(data[i:i + 1000])
        time.sleep(0.002)
    c.expect_bytes(frame(upper(blob)), timeout=3)


# ---------------- robust ----------------

@group("robust")
def test_partial_header_then_close(ctx):
    """Client gửi 2/4 byte độ dài rồi đóng; client khác gửi đủ độ dài nhưng thiếu dữ liệu rồi đóng"""
    a = ctx.connect(name="A")
    a.send(b"\x00\x00")
    a.close()
    b = ctx.connect(name="B")
    b.send(struct.pack(">I", 1000) + b"chi co 10b")
    b.shutdown_write()
    b.expect_closed(timeout=1.5)
    c = ctx.connect(name="C")
    roundtrip(c, b"van phuc vu")


@group("robust")
def test_half_close(ctx):
    """Gửi 5 thông điệp rồi shutdown(SHUT_WR): nhận đủ 5 phản hồi rồi server đóng"""
    c = ctx.connect()
    msgs = [f"m{i}".encode() * (i + 1) for i in range(5)]
    c.send(b"".join(frame(m) for m in msgs))
    c.shutdown_write()
    got = c.recv_all_until_close(timeout=2)
    want = b"".join(frame(upper(m)) for m in msgs)
    if got != want:
        raise Fail(WA, f"nhận {len(got)} byte, mong đợi {len(want)}")


@group("robust")
def test_reset_with_pending(ctx):
    """Client dồn nhiều thông điệp lớn rồi RST: server không chết (SIGPIPE)"""
    for k in range(3):
        c = ctx.connect(name=f"rst{k}")
        c.send(frame(os.urandom(60000)) * 8)
        c.reset()
        time.sleep(0.1)
    time.sleep(0.2)
    ctx.expect_alive("sau khi client đóng đột ngột")
    d = ctx.connect(name="sau")
    roundtrip(d, b"ok")


# ---------------- stress ----------------

@group("stress")
@timeout(15)
def test_1000_pipelined(ctx):
    """1000 thông điệp nhỏ dồn trong một lần gửi"""
    rng = ctx.rng
    c = ctx.connect()
    msgs = [bytes(rng.choice(b"abcXYZ019 ") for _ in range(rng.randint(0, 40))) for _ in range(1000)]
    c.send(b"".join(frame(m) for m in msgs))
    c.expect_bytes(b"".join(frame(upper(m)) for m in msgs), timeout=4)


@group("stress")
@timeout(15)
def test_twenty_max_messages(ctx):
    """20 thông điệp 65536 byte liên tiếp (1.3 MB)"""
    c = ctx.connect()
    for _ in range(20):
        roundtrip(c, os.urandom(65536), timeout=3)


@group("stress")
@timeout(15)
def test_flood_then_drain(ctx):
    """Gửi dồn tới khi đầy bộ đệm rồi mới đọc: server phải gửi đủ"""
    c = ctx.connect(rcvbuf=8192)
    msg = frame(b"x" * 60000)
    sent = 0
    c.sock.setblocking(False)
    try:
        for _ in range(60):
            try:
                c.sock.sendall(msg)
                sent += 1
            except BlockingIOError:
                break
    finally:
        c.sock.setblocking(True)
    # thông điệp cuối có thể chỉ gửi được một phần: server chờ phần còn lại, ta chỉ kiểm các thông điệp trọn vẹn
    got = c.recv_exact(sent * len(msg), timeout=5) if sent else b""
    if got != frame(b"X" * 60000) * sent:
        raise Fail(WA, "phản hồi sai nội dung")


@group("stress")
@timeout(20)
def test_fd_leak_300(ctx):
    """300 client lần lượt (giới hạn 256 file descriptor)"""
    for i in range(300):
        c = ctx.connect(name=f"C{i}")
        roundtrip(c, b"p")
        c.close()
        ctx.close_quietly(c)
    c = ctx.connect(name="cuoi")
    roundtrip(c, b"cuoi")
