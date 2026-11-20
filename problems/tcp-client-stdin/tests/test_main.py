import socket
import threading
import time

from njlib import Fail, WA, cases, group, sample, timeout


@sample
def test_basic(ctx):
    """Gửi hai dòng rồi EOF: server nhận đủ, client thoát mã 0"""
    srv = ctx.mock_server()
    cli = ctx.run_client("127.0.0.1", srv.port)
    conn = srv.accept()
    cli.write("hello\nworld\n")
    cli.close_stdin()
    data = conn.recv_all_until_close()
    if data != b"hello\nworld\n":
        raise Fail(WA, f"server nhận {data!r}, mong đợi b'hello\\nworld\\n'")
    code = cli.wait()
    if code != 0:
        raise Fail(WA, f"client phải thoát mã 0 sau EOF, nhận được {code}")


@sample
def test_line_by_line(ctx):
    """Mỗi dòng phải được gửi ngay, không đợi EOF"""
    srv = ctx.mock_server()
    cli = ctx.run_client("127.0.0.1", srv.port)
    conn = srv.accept()
    for line in ["dong 1", "dong 2 co dau cach", "", "dong 4"]:
        cli.write(line + "\n")
        conn.expect_line(line, timeout=0.7)
    cli.close_stdin()
    conn.expect_closed()
    cli.wait()


@group("stress")
def test_large_input(ctx):
    """200 KB dữ liệu, không mất byte nào"""
    srv = ctx.mock_server()
    cli = ctx.run_client("127.0.0.1", srv.port)
    conn = srv.accept()
    payload = "".join(f"{i:06d} " + "x" * (i % 120) + "\n" for i in range(3000)).encode()
    cli.write(payload)
    cli.close_stdin()
    data = conn.recv_all_until_close(timeout=4)
    if data != payload:
        raise Fail(WA, f"server nhận {len(data)} byte, mong đợi {len(payload)} byte (hoặc nội dung khác)")
    if cli.wait() != 0:
        raise Fail(WA, "client phải thoát mã 0")


@group("edge")
def test_no_trailing_newline(ctx):
    """Dòng cuối không có ký tự xuống dòng vẫn phải được gửi"""
    srv = ctx.mock_server()
    cli = ctx.run_client("127.0.0.1", srv.port)
    conn = srv.accept()
    cli.write("abc\nkhong xuong dong")
    cli.close_stdin()
    data = conn.recv_all_until_close()
    if data != b"abc\nkhong xuong dong":
        raise Fail(WA, f"server nhận {data!r}")
    cli.wait()


@group("edge")
def test_connection_refused(ctx):
    """Server không mở cổng: client báo lỗi và thoát mã khác 0"""
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()  # cổng này giờ không có ai lắng nghe
    cli = ctx.run_client("127.0.0.1", port)
    code = cli.wait(timeout=2)
    if code == 0:
        raise Fail(WA, "client phải thoát với mã khác 0 khi không kết nối được")


# ======================= phần mở rộng (thiết kế lại) =======================

def start(ctx):
    srv = ctx.mock_server()
    cli = ctx.run_client("127.0.0.1", srv.port)
    return cli, srv.accept()


def pump(cli, data):
    """Ghi stdin ở luồng riêng để không kẹt khi dữ liệu lớn hơn bộ đệm pipe/socket."""
    def run():
        try:
            cli.write(data)
        except Fail:
            pass
        cli.close_stdin()
    t = threading.Thread(target=run, daemon=True)
    t.start()
    return t


def finish_and_check(cli, conn, want, timeout=3):
    cli.close_stdin()
    data = conn.recv_all_until_close(timeout=timeout)
    if data != want:
        raise Fail(WA, f"server nhận {len(data)} byte {data[:60]!r}…, mong đợi {len(want)} byte {want[:60]!r}…")
    code = cli.wait()
    if code != 0:
        raise Fail(WA, f"client phải thoát mã 0 sau EOF, nhận được {code}")


@group("edge")
def test_empty_stdin(ctx):
    """stdin rỗng (EOF ngay): kết nối rồi đóng, không gửi byte nào, thoát mã 0"""
    cli, conn = start(ctx)
    finish_and_check(cli, conn, b"")


@group("edge")
def test_nul_bytes(ctx):
    """Dữ liệu nhập chứa byte 0x00 (fgets + strlen làm mất dữ liệu)"""
    cli, conn = start(ctx)
    data = b"a\x00b\n\x00\x00\nket thuc\x00\n"
    cli.write(data)
    finish_and_check(cli, conn, data)


@group("edge")
def test_crlf_and_blank_lines(ctx):
    """CRLF, dòng trống, dòng chỉ có dấu cách: gửi giữ nguyên"""
    cli, conn = start(ctx)
    data = b"a\r\n\r\n\n   \n\tb\n"
    cli.write(data)
    finish_and_check(cli, conn, data)


@group("edge")
@cases(4095, 4096, 4097, 65536, 200000, title="Một dòng dài {0} byte")
def test_long_line(ctx, n):
    cli, conn = start(ctx)
    data = b"q" * n + b"\n"
    t = pump(cli, data)
    got = conn.recv_all_until_close(timeout=4)
    t.join(2)
    if got != data:
        raise Fail(WA, f"server nhận {len(got)} byte, mong đợi {len(data)}")
    if cli.wait() != 0:
        raise Fail(WA, "client phải thoát mã 0")


@group("stream")
def test_partial_lines_slow(ctx):
    """stdin đến từng mảnh nhỏ có độ trễ: mỗi dòng hoàn chỉnh phải tới server kịp thời"""
    cli, conn = start(ctx)
    for i in range(5):
        cli.write(f"phan {i} ")
        time.sleep(0.05)
        cli.write("cuoi dong\n")
        conn.expect_line(f"phan {i} cuoi dong", timeout=0.7)
    finish_and_check(cli, conn, b"")


@group("stream")
def test_random_chunks(ctx):
    """50 KB nhị phân ghi vào stdin thành mảnh ngẫu nhiên"""
    rng = ctx.rng
    cli, conn = start(ctx)
    data = bytes(rng.randrange(256) for _ in range(50000))
    i = 0
    while i < len(data):
        k = rng.randint(1, 3000)
        cli.write(data[i:i + k])
        i += k
    finish_and_check(cli, conn, data)


@group("stress")
@timeout(12)
def test_2mb(ctx):
    """2 MB dữ liệu"""
    cli, conn = start(ctx)
    data = b"".join(b"%07d " % i + b"z" * (i % 200) + b"\n" for i in range(20000))
    t = pump(cli, data)
    got = conn.recv_all_until_close(timeout=6)
    t.join(2)
    if got != data:
        raise Fail(WA, f"server nhận {len(got)} byte, mong đợi {len(data)}")
    if cli.wait() != 0:
        raise Fail(WA, "client phải thoát mã 0")


@group("stress")
@timeout(12)
def test_300_lines_timely(ctx):
    """300 dòng, dòng nào cũng phải tới server trước khi dòng sau được gõ"""
    cli, conn = start(ctx)
    for i in range(300):
        cli.write(f"dong {i}\n")
        conn.expect_line(f"dong {i}", timeout=0.7)
    finish_and_check(cli, conn, b"")


@group("edge")
@cases("999.1.2.3", "abc", "1.2.3", "", title="Địa chỉ IP sai {0!r}: báo lỗi, thoát mã khác 0")
def test_bad_ip(ctx, ip):
    cli = ctx.run_client(ip, 9)
    if cli.wait(timeout=2) == 0:
        raise Fail(WA, "client phải thoát mã khác 0 khi địa chỉ IP không hợp lệ")


@group("robust")
@timeout(12)
def test_slow_server(ctx):
    """Server ngừng đọc 1 giây trong khi stdin đổ 3 MB: client phải chờ gửi tiếp (không bỏ dữ liệu)"""
    cli, conn = start(ctx)
    data = bytes(ctx.rng.randrange(256) for _ in range(4096)) * 768
    t = pump(cli, data)
    time.sleep(1.0)
    got = conn.recv_all_until_close(timeout=6)
    t.join(2)
    if got != data:
        raise Fail(WA, f"server nhận {len(got)} byte, mong đợi {len(data)} (mất dữ liệu khi bộ đệm gửi đầy?)")
    if cli.wait() != 0:
        raise Fail(WA, "client phải thoát mã 0")
