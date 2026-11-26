# Thiết kế: docs/TEST-DESIGN.md. Bộ chấm đóng vai server FLY, client của bài nộp ghi tệp vào thư mục chạy.
import os
import socket

from njlib import WA, Fail, cases, group, sample, timeout

OUT = "ve.bin"
TICKET = "VN000001"


def path(ctx, name=OUT):
    return os.path.join(ctx.workdir, name)


def run(ctx, user="an", pw="1234", ticket=TICKET, out=OUT):
    srv = ctx.mock_server()
    cli = ctx.run_client("127.0.0.1", srv.port, user, pw, ticket, out)
    conn = srv.accept(timeout=3.0)
    return cli, conn


def handshake(conn, user="an", pw="1234", ticket=TICKET, delay_welcome=True):
    """WELCOME → LOGIN → PRINT; trả về khi đã nhận PRINT."""
    if delay_welcome:
        conn.expect_silence(0.2)  # client không được nói trước khi server chào
    conn.send_line("100 OK WELCOME")
    conn.expect_line(f"LOGIN {user} {pw}", timeout=2.0)
    conn.send_line(f"100 OK {user}")
    conn.expect_line(f"PRINT {ticket}", timeout=2.0)


def finish_ok(ctx, cli, conn, payload, out=OUT):
    conn.expect_line("QUIT", timeout=3.0)
    conn.send_line("100 OK")
    code = cli.wait(timeout=4)
    if code != 0:
        raise Fail(WA, f"client phải thoát mã 0, nhận được {code}")
    check_file(ctx, payload, out)


def check_file(ctx, payload, out=OUT):
    p = path(ctx, out)
    if not os.path.exists(p):
        raise Fail(WA, f"không có tệp ra {out}")
    got = open(p, "rb").read()
    if got != payload:
        i = next((k for k in range(min(len(got), len(payload))) if got[k] != payload[k]), min(len(got), len(payload)))
        raise Fail(WA, f"tệp ra khác dữ liệu server gửi: dài {len(got)} so với {len(payload)} byte, khác nhau từ byte {i}")


def transfer(ctx, payload, mode="same", rng=None, **kw):
    cli, conn = run(ctx, **kw)
    handshake(conn, user=kw.get("user", "an"), pw=kw.get("pw", "1234"), ticket=kw.get("ticket", TICKET))
    header = f"120 FILE {len(payload)}\n".encode()
    if mode == "same":
        conn.send(header + payload)
    elif mode == "separate":
        conn.send(header)
        import time
        time.sleep(0.05)
        conn.send(payload)
    elif mode == "header_bytes":
        conn.send_slowly(header, chunk=1, delay=0.004)
        conn.send(payload)
    elif mode == "payload_chunks":
        conn.send(header)
        conn.send_chunks(payload, rng or ctx.rng, min_chunk=1, max_chunk=7, delay=0.0005)
    elif mode == "all_bytes":
        conn.send_slowly(header + payload, chunk=1, delay=0.002)
    elif mode == "mixed":
        conn.send(header + payload[:3])
        import time
        time.sleep(0.05)
        conn.send(payload[3:])
    finish_ok(ctx, cli, conn, payload, kw.get("out", OUT))


def binary(n, seed=1):
    import random
    r = random.Random(seed)
    return bytes(r.randrange(256) for _ in range(n))


TEXT = b"VE DIEN TU VN000001\nHAN -> SGN\nHanh khach: NGUYEN VAN AN\nGhe: 12A\n"


# ---------------- sample ----------------

@sample
def test_print_text(ctx):
    """Đăng nhập, PRINT, nhận vé, ghi đúng tệp, gửi QUIT, thoát mã 0"""
    transfer(ctx, TEXT)


@sample
def test_login_denied(ctx):
    """LOGIN bị từ chối: in 'ERROR 203 DENIED', thoát mã 1, không có tệp"""
    cli, conn = run(ctx)
    conn.send_line("100 OK WELCOME")
    conn.expect_line("LOGIN an 1234")
    conn.send_line("203 DENIED")
    code = cli.wait(timeout=3)
    out = cli.stdout()
    if code != 1 or "ERROR 203 DENIED" not in out or os.path.exists(path(ctx)):
        raise Fail(WA, f"mã thoát {code}, stdout {out!r}, tệp ra {'có' if os.path.exists(path(ctx)) else 'không có'}")


@sample
def test_ticket_not_found(ctx):
    """PRINT trả 202 NOT FOUND: in lỗi, thoát mã 1, không tạo tệp"""
    cli, conn = run(ctx)
    handshake(conn)
    conn.send_line("202 NOT FOUND")
    code = cli.wait(timeout=3)
    if code != 1 or "ERROR 202 NOT FOUND" not in cli.stdout() or os.path.exists(path(ctx)):
        raise Fail(WA, f"mã thoát {code}, stdout {cli.stdout()!r}")


# ---------------- basic ----------------

@group("edge")
@cases(0, 1, 2, 100, 4095, 4096, 4097, 65535, 65536, 65537, 300000, title="Vé {0} byte")
def test_sizes(ctx, n):
    transfer(ctx, binary(n, n), mode="same")


@group("edge")
def test_every_byte_value(ctx):
    """Nội dung chứa đủ 256 giá trị byte, kể cả 0x00 và \\r\\n"""
    transfer(ctx, bytes(range(256)) * 20)


@group("basic")
def test_payload_looks_like_protocol(ctx):
    """Nội dung chứa các dòng giống phản hồi giao thức: vẫn là dữ liệu"""
    payload = b"100 OK\n120 FILE 5\nabcde\r\n203 DENIED\nQUIT\n100 OK WELCOME\n\n\n"
    transfer(ctx, payload)


@group("basic")
def test_overwrites_existing_file(ctx):
    """Tệp ra đã tồn tại thì bị ghi đè hoàn toàn (kể cả khi vé ngắn hơn)"""
    with open(path(ctx), "wb") as fh:
        fh.write(b"X" * 5000)
    transfer(ctx, TEXT)


@group("basic")
def test_args_passed_verbatim(ctx):
    """user/pass/mã vé được ghép nguyên văn vào lệnh"""
    transfer(ctx, TEXT, user="binh99", pw="p@ss~!w0rd", ticket="QH-123_ABC", out="in.dat")


@group("basic")
def test_quit_sent_after_download(ctx):
    """Sau khi nhận đủ vé, client gửi QUIT và đóng kết nối"""
    cli, conn = run(ctx)
    handshake(conn)
    conn.send(b"120 FILE 3\nabc")
    conn.expect_line("QUIT", timeout=3.0)
    conn.send_line("100 OK")
    conn.expect_closed(timeout=3.0)
    if cli.wait(timeout=3) != 0:
        raise Fail(WA, "client phải thoát mã 0")
    check_file(ctx, b"abc")


# ---------------- stream ----------------

@group("stream")
@cases("separate", "header_bytes", "payload_chunks", "all_bytes", "mixed", title="Cách gửi: {0}")
def test_delivery_modes(ctx, mode):
    transfer(ctx, binary(3000, 7) + b"\n120 FILE 1\nx", mode=mode)


@group("stream")
def test_welcome_and_replies_in_pieces(ctx):
    """Mọi dòng phản hồi bị cắt từng byte"""
    cli, conn = run(ctx)
    conn.expect_silence(0.2)
    conn.send_slowly(b"100 OK WELCOME\n", chunk=1, delay=0.004)
    conn.expect_line("LOGIN an 1234", timeout=2.0)
    conn.send_slowly(b"100 OK an\n", chunk=1, delay=0.004)
    conn.expect_line(f"PRINT {TICKET}", timeout=2.0)
    conn.send_slowly(b"120 FILE 4\n", chunk=1, delay=0.004)
    conn.send(b"data")
    finish_ok(ctx, cli, conn, b"data")


@group("stream")
def test_crlf_headers(ctx):
    """Các dòng phản hồi kết thúc bằng \\r\\n"""
    cli, conn = run(ctx)
    conn.expect_silence(0.2)
    conn.send(b"100 OK WELCOME\r\n")
    conn.expect_line("LOGIN an 1234", timeout=2.0)
    conn.send(b"100 OK an\r\n")
    conn.expect_line(f"PRINT {TICKET}", timeout=2.0)
    conn.send(b"120 FILE 6\r\nabc\r\n\n")
    finish_ok(ctx, cli, conn, b"abc\r\n\n"[:6])


@group("stream")
def test_header_and_payload_in_one_segment_with_login_reply(ctx):
    """Phản hồi LOGIN không thể dính với phần sau vì client chỉ gửi PRINT sau khi đọc xong; nhưng 120 FILE + dữ liệu dính nhau"""
    cli, conn = run(ctx)
    handshake(conn)
    payload = binary(200000, 3)
    conn.send(b"120 FILE %d\n" % len(payload) + payload)
    finish_ok(ctx, cli, conn, payload)


# ---------------- robust ----------------

@group("robust")
@timeout(20)
def test_large_ticket_5mb(ctx):
    """5 000 000 byte nhị phân"""
    transfer(ctx, binary(5_000_000, 11), mode="same")


@group("robust")
def test_truncated_transfer_leaves_no_file(ctx):
    """Server đóng kết nối trước khi gửi đủ n byte: thoát mã 1, không để lại tệp"""
    cli, conn = run(ctx)
    handshake(conn)
    conn.send(b"120 FILE 100000\n" + b"x" * 5000)
    conn.close()
    code = cli.wait(timeout=4)
    if code != 1 or os.path.exists(path(ctx)):
        raise Fail(WA, f"mã thoát {code}, tệp ra {'còn' if os.path.exists(path(ctx)) else 'không còn'}")


@group("robust")
def test_huge_declared_size_not_allocated(ctx):
    """Server khai báo 5 000 000 byte nhưng chỉ gửi 10 rồi đóng: client không cấp phát theo n, thoát mã 1"""
    cli, conn = run(ctx)
    handshake(conn)
    conn.send(b"120 FILE 5000000\n0123456789")
    conn.close()
    code = cli.wait(timeout=4)
    if code != 1:
        raise Fail(WA, f"thoát mã {code} (mong đợi 1)")
    if os.path.exists(path(ctx)):
        raise Fail(WA, "không được để lại tệp dở")


@group("robust")
@cases("120 FILE", "120 FILE abc", "120 FILE -5", "120 FILE 5000001", "120 FILE 99999999999", "120 FILE 0x10", "120 FILE 1 2",
       "120 FILE  5", "120 FILE 05x", "100 OK", "120 file 5", "FILE 5", "", title="Tiêu đề sai {0!r}: lỗi, mã 1, không có tệp")
def test_bad_header(ctx, line):
    cli, conn = run(ctx)
    handshake(conn)
    conn.send(line.encode() + b"\nabcde")
    code = cli.wait(timeout=4)
    if code != 1 or os.path.exists(path(ctx)):
        raise Fail(WA, f"mã thoát {code}, tệp ra {'có' if os.path.exists(path(ctx)) else 'không có'}")


@group("robust")
@cases(("203 DENIED", "LOGIN"), ("500 FULL", "WELCOME"), ("204 LOGIN FIRST", "PRINT"), ("203 DENIED", "PRINT"), ("202 NOT FOUND", "PRINT"),
       ("999 UNKNOWN ERROR", "PRINT"), ("201 INVALID", "LOGIN"), title="Server trả {0} ở bước {1}: in ERROR, mã 1, tệp cũ giữ nguyên")
def test_server_errors(ctx, line, step):
    with open(path(ctx), "wb") as fh:
        fh.write(b"OLD DATA")
    cli, conn = run(ctx)
    if step == "WELCOME":
        conn.send_line(line)
    else:
        conn.send_line("100 OK WELCOME")
        conn.expect_line("LOGIN an 1234")
        if step == "LOGIN":
            conn.send_line(line)
        else:
            conn.send_line("100 OK an")
            conn.expect_line(f"PRINT {TICKET}")
            conn.send_line(line)
    code = cli.wait(timeout=4)
    out = cli.stdout()
    if code != 1 or f"ERROR {line}" not in out:
        raise Fail(WA, f"mã thoát {code}, stdout {out!r}")
    if open(path(ctx), "rb").read() != b"OLD DATA":
        raise Fail(WA, "tệp cũ bị thay đổi khi có lỗi")


@group("robust")
def test_server_closes_immediately(ctx):
    """Server đóng kết nối ngay khi client vừa kết nối"""
    cli, conn = run(ctx)
    conn.close()
    if cli.wait(timeout=4) != 1:
        raise Fail(WA, "mong đợi mã thoát 1")


@group("robust")
def test_connection_refused(ctx):
    """Không kết nối được: thoát mã 1"""
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    cli = ctx.run_client("127.0.0.1", port, "an", "1234", TICKET, OUT)
    if cli.wait(timeout=4) != 1:
        raise Fail(WA, "mong đợi mã thoát 1")


@group("robust")
@cases(0, 3, 5, 7, title="Sai số tham số: {0} tham số → mã 1, không kết nối")
def test_wrong_argc(ctx, k):
    import select
    srv = ctx.mock_server()
    full = ["127.0.0.1", str(srv.port), "an", "1234", TICKET, OUT, "thua"]
    cli = ctx.run_client(*full[:k])
    if cli.wait(timeout=3) != 1:
        raise Fail(WA, "sai số tham số phải thoát mã 1")
    if select.select([srv.sock], [], [], 0.05)[0]:
        raise Fail(WA, "sai số tham số mà client vẫn kết nối")


# ---------------- stress ----------------

@group("stress")
@timeout(25)
def test_random_sizes_and_modes(ctx):
    """20 lần chạy với kích thước ngẫu nhiên (0–200 KB) và cách gửi ngẫu nhiên"""
    rng = ctx.rng
    for i in range(20):
        n = rng.choice([0, 1, rng.randrange(1, 200000), rng.randrange(1, 5000)])
        mode = rng.choice(["same", "separate", "payload_chunks", "mixed", "header_bytes"])
        payload = binary(n, i)
        if i:
            os.path.exists(path(ctx)) and os.remove(path(ctx))
        transfer(ctx, payload, mode=mode if n < 20000 or mode != "payload_chunks" else "same")
