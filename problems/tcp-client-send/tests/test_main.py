import select
import socket

from njlib import Fail, WA, cases, group, sample


def start(ctx, msg):
    srv = ctx.mock_server()
    cli = ctx.run_client("127.0.0.1", srv.port, msg)
    conn = srv.accept()
    return cli, conn


def exchange(ctx, msg):
    """Server nhận đúng msg + '\\n', không thừa byte; client đóng kết nối rồi thoát mã 0."""
    cli, conn = start(ctx, msg)
    conn.expect_bytes(msg.encode() + b"\n", timeout=2.0)
    rest = conn.recv_all_until_close(timeout=2.0)
    if rest:
        raise Fail(WA, f"server nhận thừa {len(rest)} byte sau thông điệp: {rest[:40]!r}")
    code = cli.wait(timeout=3)
    if code != 0:
        raise Fail(WA, f"client phải thoát mã 0 sau khi gửi xong, nhận được {code}")


@sample
def test_basic(ctx):
    """Client gửi 'xin chao\\n' rồi đóng, thoát mã 0"""
    exchange(ctx, "xin chao")


@sample
def test_spaces_and_symbols(ctx):
    """Thông điệp là MỘT tham số có dấu cách và ký tự đặc biệt"""
    exchange(ctx, "SET a=1; echo $HOME \"q\" 'r' * ?  ")


@group("edge")
def test_empty_message(ctx):
    """Thông điệp rỗng: server chỉ nhận một '\\n'"""
    exchange(ctx, "")


@group("edge")
def test_single_char(ctx):
    exchange(ctx, "z")


@group("edge")
@cases(1023, 1024, 1025, 4095, 4096, 4097, 50000, title="Thông điệp dài {0} ký tự")
def test_message_sizes(ctx, n):
    exchange(ctx, "".join(chr(97 + (i * 7) % 26) for i in range(n)))


@group("edge")
def test_connection_refused(ctx):
    """Server không mở cổng: client báo lỗi và thoát mã khác 0"""
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    cli = ctx.run_client("127.0.0.1", port, "xin chao")
    code = cli.wait(timeout=3)
    if code <= 0:
        raise Fail(WA, f"không kết nối được mà client thoát mã {code}: phải thoát mã dương khác 0")


@group("edge")
@cases("999.1.2.3", "abc", "1.2.3", "", title="Địa chỉ IP sai {0!r}: báo lỗi, thoát mã khác 0")
def test_bad_ip(ctx, ip):
    cli = ctx.run_client(ip, 9, "xin chao")
    code = cli.wait(timeout=3)
    if code <= 0:
        raise Fail(WA, f"client phải thoát mã dương khác 0 khi địa chỉ IP không hợp lệ, nhận được {code}")


@group("edge")
@cases(0, 1, 2, 4, title="Sai số tham số: {0} tham số")
def test_wrong_argc(ctx, k):
    """Sai số tham số: Usage ra stderr, không kết nối, thoát mã 1"""
    srv = ctx.mock_server()
    full = ["127.0.0.1", str(srv.port), "tin", "thua"]
    a = full[:k] if k < 3 else full
    cli = ctx.run_client(*a)
    code = cli.wait(timeout=3)
    if code != 1:
        raise Fail(WA, f"sai số tham số phải thoát mã 1, nhận được {code}")
    if select.select([srv.sock], [], [], 0.05)[0]:
        raise Fail(WA, "sai số tham số mà client vẫn kết nối tới server")
