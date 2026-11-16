import socket
import time

from njlib import Fail, WA, sample


def start(ctx):
    srv = ctx.mock_server()
    cli = ctx.run_client("127.0.0.1", srv.port)
    return cli, srv.accept()


@sample
def test_receive_while_stdin_idle(ctx):
    """Server gửi tin khi stdin im lặng: tin phải hiện ra stdout ngay"""
    cli, conn = start(ctx)
    conn.send("abc: xin chao\n")
    cli.expect_stdout("abc: xin chao\n", timeout=1.0)
    conn.send("abc: tin thu hai\n")
    out = cli.expect_stdout("tin thu hai\n", timeout=1.0)
    if out != "abc: xin chao\nabc: tin thu hai\n":
        raise Fail(WA, f"stdout phải đúng bằng dữ liệu server gửi, nhận được {out!r}")


@sample
def test_send_while_server_idle(ctx):
    """Gõ vào stdin khi server im lặng: dòng phải đến server ngay"""
    cli, conn = start(ctx)
    for line in ["dong 1", "dong 2 co dau cach", "dong 3"]:
        cli.write(line + "\n")
        conn.expect_line(line, timeout=0.7)


@sample
def test_stdin_eof_then_drain(ctx):
    """stdin EOF: server thấy EOF, tin cuối của server vẫn được in, client thoát mã 0"""
    cli, conn = start(ctx)
    cli.write("lenh cuoi\n")
    conn.expect_line("lenh cuoi")
    cli.close_stdin()
    conn.expect_closed(allow_data=True)  # server thấy client đã shutdown(SHUT_WR)
    conn.send("tam biet\n")
    conn.close()
    cli.expect_stdout("tam biet\n", timeout=1.0)
    code = cli.wait()
    if code != 0:
        raise Fail(WA, f"client phải thoát mã 0, nhận được {code}")


def test_server_closes_first(ctx):
    """Server đóng kết nối khi stdin còn mở: client thoát mã 0"""
    cli, conn = start(ctx)
    conn.send("bye\n")
    conn.close()
    cli.expect_stdout("bye\n", timeout=1.0)
    code = cli.wait(timeout=1.5)
    if code != 0:
        raise Fail(WA, f"client phải thoát mã 0 khi server đóng, nhận được {code}")


def test_interleaved(ctx):
    """Hai chiều xen kẽ nhiều lượt"""
    cli, conn = start(ctx)
    expect = ""
    for i in range(10):
        cli.write(f"gui {i}\n")
        conn.expect_line(f"gui {i}", timeout=0.7)
        msg = f"nhan {i}\n"
        conn.send(msg)
        expect += msg
        cli.expect_stdout(msg, timeout=0.7)
    out = cli.stdout()
    if out != expect:
        raise Fail(WA, f"stdout mong đợi {expect!r}, nhận được {out!r}")


def test_both_sides_at_once(ctx):
    """Server và stdin cùng gửi dữ liệu lớn, không mất byte và không kẹt"""
    cli, conn = start(ctx)
    to_server = "".join(f"c{i:05d} " + "x" * (i % 60) + "\n" for i in range(3000))
    to_client = "".join(f"s{i:05d} " + "y" * (i % 70) + "\n" for i in range(3000))
    conn.send(to_client)
    cli.write(to_server)
    cli.close_stdin()
    got = b""
    deadline = time.monotonic() + 4
    while len(got) < len(to_server) and time.monotonic() < deadline:
        conn._fill(deadline)
        got, conn.buf = got + conn.buf, b""
        if conn.eof:
            break
    if got != to_server.encode():
        raise Fail(WA, f"server nhận {len(got)} byte, mong đợi {len(to_server)} byte (hoặc nội dung khác)")
    conn.close()
    cli.wait(timeout=2)
    out = cli.stdout()
    if out != to_client:
        raise Fail(WA, f"stdout có {len(out)} byte, mong đợi {len(to_client)} byte (hoặc nội dung khác)")


def test_connection_refused(ctx):
    """Server không mở cổng: client báo lỗi và thoát mã khác 0"""
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    cli = ctx.run_client("127.0.0.1", port)
    if cli.wait(timeout=2) == 0:
        raise Fail(WA, "client phải thoát với mã khác 0 khi không kết nối được")
