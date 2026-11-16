import socket
import struct

from njlib import Fail, WA, sample


def record(mssv, name, y, m, d, gpa100):
    nb = name.encode()
    return struct.pack(">IB", mssv, len(nb)) + nb + struct.pack(">HBBH", y, m, d, gpa100)


def sv_input(mssv, name, dob, gpa):
    return f"{mssv}\n{name}\n{dob}\n{gpa}\n"


def read_record(conn, timeout=1.0):
    head = conn.recv_exact(5, timeout)
    rest = conn.recv_exact(head[4] + 6, timeout)
    return head + rest


def expect_record(conn, want):
    got = read_record(conn)
    if got != want:
        raise Fail(WA, f"bản ghi nhận được {got.hex()} ({len(got)} byte), mong đợi {want.hex()} ({len(want)} byte)")


def start(ctx):
    srv = ctx.mock_server()
    cli = ctx.run_client("127.0.0.1", srv.port)
    return cli, srv.accept()


def finish(cli):
    code = cli.wait()
    if code != 0:
        raise Fail(WA, f"client phải thoát mã 0, nhận được {code}")


@sample
def test_one_record(ctx):
    """Một sinh viên: bản ghi nhị phân đúng từng byte, in phản hồi OK"""
    cli, conn = start(ctx)
    cli.write(sv_input(20201234, "Nguyen Van A", "2002-04-10", "3.99"))
    expect_record(conn, record(20201234, "Nguyen Van A", 2002, 4, 10, 399))
    conn.send("OK\n")
    cli.expect_stdout("OK\n")
    cli.close_stdin()
    conn.expect_closed()
    finish(cli)


@sample
def test_two_records(ctx):
    """Hai sinh viên liên tiếp trên cùng một kết nối"""
    cli, conn = start(ctx)
    cli.write(sv_input(20205678, "Tran Van B", "2002-08-18", "3.5") +
              sv_input(20190001, "Le Thi C", "2001-12-01", "2.07"))
    expect_record(conn, record(20205678, "Tran Van B", 2002, 8, 18, 350))
    conn.send("OK\n")
    expect_record(conn, record(20190001, "Le Thi C", 2001, 12, 1, 207))
    conn.send("OK\n")
    out = cli.expect_stdout("OK\nOK\n")
    if out != "OK\nOK\n":
        raise Fail(WA, f"stdout mong đợi 'OK\\nOK\\n', nhận được {out!r}")
    cli.close_stdin()
    finish(cli)


@sample
def test_utf8_name(ctx):
    """Tên tiếng Việt có dấu: name_len là số byte UTF-8, không phải số ký tự"""
    cli, conn = start(ctx)
    name = "Nguyễn Thị Hồng Ánh"
    cli.write(sv_input(20211111, name, "2003-01-31", "3.2"))
    expect_record(conn, record(20211111, name, 2003, 1, 31, 320))
    conn.send("OK\n")
    cli.expect_stdout("OK\n")
    cli.close_stdin()
    finish(cli)


def test_byte_order(ctx):
    """Số nguyên nhiều byte theo big-endian (MSSV lớn, năm, điểm)"""
    cli, conn = start(ctx)
    cli.write(sv_input(16909060, "A", "1999-11-22", "4"))
    expect_record(conn, record(0x01020304, "A", 1999, 11, 22, 400))
    conn.send("OK\n")
    cli.expect_stdout("OK\n")
    cli.close_stdin()
    finish(cli)


def test_gpa_rounding(ctx):
    """Điểm làm tròn đúng: 2.85 → 285, 3.07 → 307, 0 → 0 (không bị cắt thành 284, 306)"""
    cli, conn = start(ctx)
    cases = [("2.85", 285), ("3.07", 307), ("0", 0), ("1.15", 115), ("3.99", 399)]
    for i, (g, v) in enumerate(cases):
        cli.write(sv_input(1000 + i, f"SV{i}", "2000-01-01", g))
        expect_record(conn, record(1000 + i, f"SV{i}", 2000, 1, 1, v))
        conn.send("OK\n")
    cli.expect_stdout("OK\n" * len(cases))
    cli.close_stdin()
    finish(cli)


def test_long_name_and_spaces(ctx):
    """Tên 100 byte và tên có nhiều dấu cách"""
    cli, conn = start(ctx)
    for i, name in enumerate(["x" * 100, "Nguyen  Van   Nam"]):
        cli.write(sv_input(7000 + i, name, "2002-02-02", "3.0"))
        expect_record(conn, record(7000 + i, name, 2002, 2, 2, 300))
        conn.send("OK\n")
    cli.expect_stdout("OK\nOK\n")
    cli.close_stdin()
    finish(cli)


def test_error_reply_stops(ctx):
    """Server trả ERROR rồi đóng: client in ERROR, thoát mã 0 và không treo"""
    cli, conn = start(ctx)
    cli.write(sv_input(20200000, "Bad", "2002-04-10", "3.5"))
    read_record(conn)
    conn.send("ERROR\n")
    conn.close()
    cli.expect_stdout("ERROR\n")
    finish(cli)


def test_connection_refused(ctx):
    """Server không mở cổng: client báo lỗi và thoát mã khác 0"""
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    cli = ctx.run_client("127.0.0.1", port)
    if cli.wait(timeout=2) == 0:
        raise Fail(WA, "client phải thoát với mã khác 0 khi không kết nối được")
