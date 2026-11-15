import socket

from njlib import Fail, WA, sample


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
