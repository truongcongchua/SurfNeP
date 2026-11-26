# Thiết kế: docs/TEST-DESIGN.md. Tệp log được đọc trực tiếp từ thư mục chạy của bài nộp.
import os
import re
import time

from njlib import WA, Fail, cases, group, sample, timeout

LOG = "server.log"
LINE_RE = re.compile(rb'^\[([0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2})\] (CONNECT|RECV|SEND|DISCONNECT) '
                     rb'(127\.0\.0\.1:[0-9]+)(?: "(.*)")?$', re.S)


def raw_log(ctx):
    with open(os.path.join(ctx.workdir, LOG), "rb") as fh:
        return fh.read()


def parse_log(ctx):
    """Trả về danh sách (giây epoch, loại, địa chỉ, nội dung|None); sai định dạng thì WA."""
    data = raw_log(ctx)
    out = []
    if data and not data.endswith(b"\n"):
        raise Fail(WA, f"dòng log cuối không kết thúc bằng \\n: {data[-60:]!r}")
    for ln in data.split(b"\n")[:-1] if data else []:
        m = LINE_RE.match(ln)
        if not m:
            raise Fail(WA, f"dòng log sai định dạng: {ln[:120]!r}")
        ts = time.mktime(time.strptime(m.group(1).decode(), "%Y-%m-%d %H:%M:%S"))
        out.append((ts, m.group(2).decode(), m.group(3).decode(), m.group(4)))
    return out


def addr_of(c):
    return c.addr


def events(ctx, addr):
    return [(k, t) for (_, k, a, t) in parse_log(ctx) if a == addr]


def wait_events(ctx, c, want, wait=1.5):
    """Chờ tới khi log của client c đúng bằng `want` (danh sách (loại, nội dung bytes|None))."""
    addr = addr_of(c)
    deadline = time.monotonic() + wait
    got = None
    while time.monotonic() < deadline:
        got = events(ctx, addr)
        if got == want:
            return
        time.sleep(0.03)
    raise Fail(WA, f"log của {addr} sai.\nMong đợi: {want[:12]!r}\nThực tế:     {(got or [])[:12]!r} (tổng {len(got or [])} dòng)")


def conn(ctx, name=None):
    c = ctx.connect(name=name)
    c.addr = "127.0.0.1:%d" % c.sock.getsockname()[1]  # lưu trước: sau close()/reset() không hỏi lại được
    return c


def ev(*pairs):
    """('RECV', 'PING') -> ('RECV', b'PING')"""
    return [(k, t.encode("latin-1") if isinstance(t, str) else t) for k, t in pairs]


def full(*lines):
    """Chuỗi sự kiện đầy đủ: CONNECT, các cặp (RECV, SEND), DISCONNECT."""
    out = [("CONNECT", None)]
    for cmd, resp in lines:
        out += [("RECV", cmd.encode("latin-1") if isinstance(cmd, str) else cmd), ("SEND", resp.encode())]
    return out


# ---------------- sample ----------------

@sample
def test_ping_quit_log(ctx):
    """PING, lệnh lạ, QUIT: log đúng CONNECT / RECV / SEND / DISCONNECT"""
    c = conn(ctx)
    c.send_line("PING")
    c.expect_line("100 OK PONG")
    c.send_line("HELLO")
    c.expect_line("999 UNKNOWN ERROR")
    c.send_line("QUIT")
    c.expect_line("100 OK")
    c.expect_closed()
    wait_events(ctx, c, full(("PING", "100 OK PONG"), ("HELLO", "999 UNKNOWN ERROR"), ("QUIT", "100 OK")) + [("DISCONNECT", None)])


@sample
def test_log_before_reply(ctx):
    """Khi đã nhận phản hồi thì RECV và SEND tương ứng đã nằm trong tệp (flush trước khi gửi)"""
    c = conn(ctx)
    for i in range(5):
        c.send_line("PING")
        c.expect_line("100 OK PONG")
        ev_now = events(ctx, addr_of(c))
        if ev_now != full(*[("PING", "100 OK PONG")] * (i + 1)):
            raise Fail(WA, f"ngay sau phản hồi thứ {i + 1} log chưa đủ: {ev_now!r}")


@sample
def test_timestamp_and_address(ctx):
    """Giờ địa phương [YYYY-MM-DD HH:MM:SS] (lệch ≤ 2s) và cổng của client đúng"""
    t0 = time.time()
    c = conn(ctx)
    c.send_line("PING")
    c.expect_line("100 OK PONG")
    t1 = time.time()
    rows = [r for r in parse_log(ctx) if r[2] == addr_of(c)]
    if len(rows) != 3:
        raise Fail(WA, f"cần 3 dòng log, có {len(rows)}")
    for ts, kind, _, _ in rows:
        if not t0 - 2 <= ts <= t1 + 2:
            raise Fail(WA, f"giờ trong log lệch quá 2 giây so với giờ thật ({kind})")


# ---------------- basic ----------------

@group("basic")
def test_two_clients_separate_sequences(ctx):
    """Hai client xen kẽ: log của mỗi client đúng thứ tự riêng"""
    a, b = conn(ctx, "A"), conn(ctx, "B")
    for line, c in [("PING", a), ("HELLO", b), ("PING", b), ("X", a), ("PING", a)]:
        c.send_line(line)
        c.recv_line()
    wait_events(ctx, a, full(("PING", "100 OK PONG"), ("X", "999 UNKNOWN ERROR"), ("PING", "100 OK PONG")))
    wait_events(ctx, b, full(("HELLO", "999 UNKNOWN ERROR"), ("PING", "100 OK PONG")))


@group("basic")
def test_disconnect_logged_for_each_way(ctx):
    """DISCONNECT được ghi khi QUIT, khi client đóng và khi RST"""
    cs = [conn(ctx, f"c{i}") for i in range(3)]
    cs[0].send_line("QUIT")
    cs[0].expect_line("100 OK")
    cs[1].close()
    cs[2].reset()
    for c in cs:
        want = ([("CONNECT", None), ("RECV", b"QUIT"), ("SEND", b"100 OK"), ("DISCONNECT", None)] if c is cs[0]
                else [("CONNECT", None), ("DISCONNECT", None)])
        wait_events(ctx, c, want)


@group("basic")
def test_log_only_grows(ctx):
    """Tệp log chỉ được nối thêm: nội dung cũ không bị ghi lại hay mất"""
    c = conn(ctx)
    snaps = []
    for _ in range(6):
        c.send_line("PING")
        c.expect_line("100 OK PONG")
        snaps.append(raw_log(ctx))
    for x, y in zip(snaps, snaps[1:]):
        if not y.startswith(x) or len(y) <= len(x):
            raise Fail(WA, "log không phải chỉ nối thêm")


@group("basic")
def test_existing_log_preserved(ctx):
    """Tệp log đã có sẵn 2 dòng cũ: mở chế độ nối nên 2 dòng cũ còn nguyên ở đầu tệp"""
    old = raw_log(ctx)
    if old.count(bytes([10])) != 2:
        raise Fail(WA, "tệp log ban đầu bị thay đổi ngay khi khởi động")
    c = conn(ctx)
    c.send_line("PING")
    c.expect_line("100 OK PONG")
    if not raw_log(ctx).startswith(old):
        raise Fail(WA, "nội dung cũ của tệp log bị mất (phải mở bằng chế độ nối)")


@group("basic")
def test_log_file_exists_at_start(ctx):
    """Tệp log đã được tạo khi server khởi động (trước mọi kết nối)"""
    time.sleep(0.2)
    if not os.path.exists(os.path.join(ctx.workdir, LOG)):
        raise Fail(WA, "chưa có tệp log sau khi khởi động")
    time.sleep(0.01)


# ---------------- edge ----------------

@group("edge")
@cases("", "PING ", " PING", "ping", "PING PING", "QUIT now", "hello world", '"quoted"', 'a"b"c', "tab\there", "x" * 1000, " ", "\\n",
       title="Lệnh {0!r:.40}: RECV ghi nguyên nội dung, SEND 999")
def test_text_verbatim(ctx, text):
    c = conn(ctx)
    c.send(text.encode("latin-1") + b"\n")
    c.expect_line("999 UNKNOWN ERROR")
    wait_events(ctx, c, full((text, "999 UNKNOWN ERROR")))


@group("edge")
def test_crlf_stripped_in_log(ctx):
    """\\r\\n: log không chứa \\r; chỉ bỏ MỘT \\r (\\r\\r\\n còn lại một \\r)"""
    c = conn(ctx)
    c.send("PING\r\n")
    c.expect_line("100 OK PONG")
    c.send("PING\r\r\n")
    c.expect_line("999 UNKNOWN ERROR")
    wait_events(ctx, c, full(("PING", "100 OK PONG"), (b"PING\r", "999 UNKNOWN ERROR")))


# ---------------- stream ----------------

@group("stream")
def test_byte_by_byte_single_recv_line(ctx):
    """Lệnh gửi từng byte vẫn chỉ ghi một dòng RECV"""
    c = conn(ctx)
    c.send_slowly("PING\n", chunk=1, delay=0.01)
    c.expect_line("100 OK PONG")
    c.send_slowly("HELLO THERE\n", chunk=1, delay=0.005)
    c.expect_line("999 UNKNOWN ERROR")
    wait_events(ctx, c, full(("PING", "100 OK PONG"), ("HELLO THERE", "999 UNKNOWN ERROR")))


@group("stream")
def test_many_commands_one_send(ctx):
    """60 lệnh dính nhau: 60 RECV và 60 SEND đúng thứ tự (xen kẽ RECV, SEND từng lệnh)"""
    c = conn(ctx)
    cmds = [("PING" if i % 3 == 0 else f"CMD{i}") for i in range(60)]
    c.send("".join(x + "\n" for x in cmds))
    for x in cmds:
        c.expect_line("100 OK PONG" if x == "PING" else "999 UNKNOWN ERROR")
    wait_events(ctx, c, full(*[(x, "100 OK PONG" if x == "PING" else "999 UNKNOWN ERROR") for x in cmds]))


@group("stream")
def test_partial_line_not_logged(ctx):
    """Phần dở dang (không có \\n) khi client rời đi không được ghi thành RECV"""
    c = conn(ctx)
    c.send_line("PING")
    c.expect_line("100 OK PONG")
    c.send("PIN")
    time.sleep(0.1)
    c.close()
    wait_events(ctx, c, full(("PING", "100 OK PONG")) + [("DISCONNECT", None)])


@group("stream")
def test_random_chunks(ctx):
    """Cắt ngẫu nhiên 1–7 byte"""
    c = conn(ctx)
    want = []
    for i in range(30):
        text = "PING" if i % 2 else f"WORD {i}"
        c.send_chunks(text + "\n", ctx.rng, delay=0)
        c.expect_line("100 OK PONG" if text == "PING" else "999 UNKNOWN ERROR", timeout=2.0)
        want.append((text, "100 OK PONG" if text == "PING" else "999 UNKNOWN ERROR"))
    wait_events(ctx, c, full(*want))


# ---------------- robust ----------------

@group("robust")
def test_binary_bytes_logged_raw(ctx):
    """Byte lạ trong lệnh được ghi nguyên trong RECV"""
    c = conn(ctx)
    junk = bytes([0x01, 0x80, 0xFF, 0x7F, 0xC3, 0xA9]) + b"abc"
    c.send(junk + b"\n")
    c.expect_line("999 UNKNOWN ERROR")
    wait_events(ctx, c, full((junk, "999 UNKNOWN ERROR")))


@group("robust")
def test_connect_and_leave_silently(ctx):
    """Kết nối rồi đóng ngay không gửi gì: CONNECT rồi DISCONNECT"""
    cs = [conn(ctx, f"c{i}") for i in range(5)]
    for c in cs:
        c.close()
    for c in cs:
        wait_events(ctx, c, [("CONNECT", None), ("DISCONNECT", None)])


@group("robust")
@timeout(25)
def test_300_connections_fd(ctx):
    """300 lượt kết nối-ngắt: không rò file descriptor, log có đủ 300 × (CONNECT, DISCONNECT)"""
    addrs = []
    for i in range(300):
        c = conn(ctx, f"c{i}")
        addrs.append(addr_of(c))
        c.send_line("PING")
        c.expect_line("100 OK PONG")
        c.reset() if i % 2 else c.close()
        ctx.close_quietly(c)
    time.sleep(0.5)
    rows = parse_log(ctx)
    for a in addrs:
        got = [k for (_, k, ad, _) in rows if ad == a]
        if got != ["CONNECT", "RECV", "SEND", "DISCONNECT"]:
            raise Fail(WA, f"{a}: {got!r}")


# ---------------- concurrency ----------------

@group("concurrency")
@timeout(15)
def test_20_clients_interleaved(ctx):
    """20 client xen kẽ ngẫu nhiên: mỗi client đúng thứ tự riêng, mọi dòng nguyên vẹn"""
    cs = [conn(ctx, f"c{i}") for i in range(20)]
    want = {id(c): [] for c in cs}
    for _ in range(300):
        c = ctx.rng.choice(cs)
        text = ctx.rng.choice(["PING", "HELLO", "X Y Z", "", "PING"])
        c.send(text + "\n")
        resp = "100 OK PONG" if text == "PING" else "999 UNKNOWN ERROR"
        c.expect_line(resp)
        want[id(c)].append((text, resp))
    for c in cs:
        wait_events(ctx, c, full(*want[id(c)]))
    for c in cs:
        c.close()


@group("concurrency")
def test_idle_client_does_not_block(ctx):
    """Client im lặng/gửi dở lệnh không chặn client khác"""
    idle = [conn(ctx, f"idle{i}") for i in range(4)]
    idle[0].send("HEL")
    a = conn(ctx, "active")
    a.send_line("PING")
    a.expect_line("100 OK PONG")
    idle[0].send("LO\n")
    idle[0].expect_line("999 UNKNOWN ERROR")
    wait_events(ctx, idle[0], full(("HELLO", "999 UNKNOWN ERROR")))


# ---------------- stress ----------------

@group("stress")
@timeout(25)
def test_3000_commands(ctx):
    """3000 lệnh trên một kết nối: đủ 6002 dòng log đúng thứ tự"""
    c = conn(ctx)
    want = []
    for i in range(0, 3000, 50):
        batch = [("PING" if (i + j) % 4 else f"C{i + j}") for j in range(50)]
        c.send("".join(x + "\n" for x in batch))
        for x in batch:
            resp = "100 OK PONG" if x == "PING" else "999 UNKNOWN ERROR"
            c.expect_line(resp, timeout=3.0)
            want.append((x, resp))
    c.send_line("QUIT")
    c.expect_line("100 OK")
    want.append(("QUIT", "100 OK"))
    wait_events(ctx, c, full(*want) + [("DISCONNECT", None)], wait=3.0)
