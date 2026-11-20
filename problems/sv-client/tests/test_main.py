import socket
import struct
import time

from njlib import Fail, WA, cases, group, sample, timeout


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


@group("basic")
def test_byte_order(ctx):
    """Số nguyên nhiều byte theo big-endian (MSSV lớn, năm, điểm)"""
    cli, conn = start(ctx)
    cli.write(sv_input(16909060, "A", "1999-11-22", "4"))
    expect_record(conn, record(0x01020304, "A", 1999, 11, 22, 400))
    conn.send("OK\n")
    cli.expect_stdout("OK\n")
    cli.close_stdin()
    finish(cli)


@group("basic")
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


@group("edge")
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


@group("robust")
def test_error_reply_stops(ctx):
    """Server trả ERROR rồi đóng: client in ERROR, thoát mã 0 và không treo"""
    cli, conn = start(ctx)
    cli.write(sv_input(20200000, "Bad", "2002-04-10", "3.5"))
    read_record(conn)
    conn.send("ERROR\n")
    conn.close()
    cli.expect_stdout("ERROR\n")
    finish(cli)


@group("edge")
def test_connection_refused(ctx):
    """Server không mở cổng: client báo lỗi và thoát mã khác 0"""
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    cli = ctx.run_client("127.0.0.1", port)
    if cli.wait(timeout=2) == 0:
        raise Fail(WA, "client phải thoát với mã khác 0 khi không kết nối được")


# ======================= phần mở rộng (thiết kế lại) =======================

@group("edge")
@cases(("0.29", 29), ("0.57", 57), ("1.13", 113), ("2.01", 201), ("4.35", 435), ("0.01", 1), ("4.00", 400),
       ("2.5", 250), ("0.1", 10), ("1", 100), ("3.10", 310), ("0.07", 7),
       title="Điểm {0} → {1} (double nhân 100 dễ ra x.99999…)")
def test_gpa_exact(ctx, g, v):
    cli, conn = start(ctx)
    cli.write(sv_input(5, "Diem", "2001-01-01", g))
    expect_record(conn, record(5, "Diem", 2001, 1, 1, v))
    conn.send("OK\n")
    cli.expect_stdout("OK\n")
    cli.close_stdin()
    finish(cli)


@group("edge")
def test_extreme_numbers(ctx):
    """MSSV 0 và 4294967295, năm 1900/2100, tên 1 byte"""
    cli, conn = start(ctx)
    rows = [(0, "a", "1900-01-01", "0", (1900, 1, 1, 0)), (4294967295, "b", "2100-12-31", "4", (2100, 12, 31, 400))]
    for mssv, name, dob, g, (y, m, d, v) in rows:
        cli.write(sv_input(mssv, name, dob, g))
        expect_record(conn, record(mssv, name, y, m, d, v))
        conn.send("OK\n")
    cli.expect_stdout("OK\nOK\n")
    cli.close_stdin()
    finish(cli)


@group("edge")
def test_utf8_100_bytes(ctx):
    """Tên UTF-8 đúng 100 byte (34 ký tự 'ễ' 3 byte cắt còn 33 + 1 byte)"""
    cli, conn = start(ctx)
    name = "ễ" * 33 + "x"
    assert len(name.encode()) == 100
    cli.write(sv_input(9, name, "2002-02-02", "3"))
    expect_record(conn, record(9, name, 2002, 2, 2, 300))
    conn.send("OK\n")
    cli.expect_stdout("OK\n")
    cli.close_stdin()
    finish(cli)


@group("edge")
def test_crlf_input(ctx):
    """Dữ liệu nhập kết thúc dòng bằng CRLF: '\\r' không được lọt vào bản ghi"""
    cli, conn = start(ctx)
    cli.write("20201234\r\nTran Van B\r\n2002-08-18\r\n3.5\r\n")
    expect_record(conn, record(20201234, "Tran Van B", 2002, 8, 18, 350))
    conn.send("OK\n")
    cli.expect_stdout("OK\n")
    cli.close_stdin()
    finish(cli)


@group("edge")
def test_last_line_no_newline(ctx):
    """Dòng điểm cuối cùng không có xuống dòng vẫn được xử lý"""
    cli, conn = start(ctx)
    cli.write("1\nA\n2000-01-01\n3.25")
    cli.close_stdin()
    expect_record(conn, record(1, "A", 2000, 1, 1, 325))
    conn.send("OK\n")
    cli.expect_stdout("OK\n")
    finish(cli)


@group("stream")
def test_reply_split(ctx):
    """Phản hồi 'OK\\n' đến thành từng byte: phải đọc đủ một dòng rồi mới in"""
    cli, conn = start(ctx)
    cli.write(sv_input(1, "A", "2000-01-01", "1") + sv_input(2, "B", "2000-01-01", "2"))
    read_record(conn)
    conn.send_slowly("OK\n", chunk=1, delay=0.05)
    read_record(conn)
    conn.send_slowly("OK\n", chunk=1, delay=0.05)
    out = cli.expect_stdout("OK\nOK\n")
    if out != "OK\nOK\n":
        raise Fail(WA, f"stdout mong đợi 'OK\\nOK\\n', nhận được {out!r}")
    cli.close_stdin()
    finish(cli)


@group("stream")
def test_input_trickles(ctx):
    """stdin đến từng mảnh nhỏ (bản ghi bị chia nhiều lần ghi): bản ghi vẫn đúng"""
    cli, conn = start(ctx)
    text = sv_input(31337, "Cham Tung Chut", "1999-09-09", "3.33")
    for i in range(0, len(text), 3):
        cli.write(text[i:i + 3])
        time.sleep(0.01)
    expect_record(conn, record(31337, "Cham Tung Chut", 1999, 9, 9, 333))
    conn.send("OK\n")
    cli.expect_stdout("OK\n")
    cli.close_stdin()
    finish(cli)


@group("basic")
def test_waits_for_each_reply(ctx):
    """Client gửi bản ghi sau chỉ khi đã nhận phản hồi của bản ghi trước"""
    cli, conn = start(ctx)
    cli.write(sv_input(1, "A", "2000-01-01", "1") + sv_input(2, "B", "2000-01-01", "2"))
    read_record(conn)
    conn.expect_silence(0.3)
    conn.send("OK\n")
    expect_record(conn, record(2, "B", 2000, 1, 1, 200))
    conn.send("OK\n")
    cli.expect_stdout("OK\nOK\n")
    cli.close_stdin()
    finish(cli)


@group("robust")
def test_error_mid_batch(ctx):
    """ERROR ở bản ghi thứ 2 (trong 4): client in OK rồi ERROR, không gửi tiếp, thoát mã 0"""
    cli, conn = start(ctx)
    cli.write("".join(sv_input(i, f"S{i}", "2000-01-01", "1") for i in range(4)))
    read_record(conn)
    conn.send("OK\n")
    read_record(conn)
    conn.send("ERROR\n")
    conn.expect_silence(0.3)
    conn.close()
    out = cli.expect_stdout("OK\nERROR\n")
    finish(cli)
    if out != "OK\nERROR\n":
        raise Fail(WA, f"stdout mong đợi 'OK\\nERROR\\n', nhận được {out!r}")


@group("robust")
def test_server_closes_without_reply(ctx):
    """Server đóng kết nối ngay sau khi nhận bản ghi (không trả lời): client không treo, không chết vì SIGPIPE"""
    cli, conn = start(ctx)
    cli.write("".join(sv_input(i, f"S{i}", "2000-01-01", "1") for i in range(3)))
    read_record(conn)
    conn.close()
    code = cli.wait(timeout=2)
    if code is not None and code < 0:
        raise Fail(WA, f"client bị dừng bởi tín hiệu {-code} (SIGPIPE?)")


@group("stress")
@timeout(15)
def test_200_records(ctx):
    """200 sinh viên ngẫu nhiên, so từng byte"""
    rng = ctx.rng
    cli, conn = start(ctx)
    rows = []
    for i in range(200):
        g100 = rng.randint(0, 400)
        name = "".join(rng.choice("abc XYZ") for _ in range(rng.randint(1, 40))).strip() or "N"
        rows.append((rng.randrange(1 << 32), name, rng.randint(1950, 2020), rng.randint(1, 12), rng.randint(1, 28), g100))
    cli.write("".join(sv_input(m, n, f"{y}-{mo:02d}-{d:02d}", f"{g // 100}.{g % 100:02d}") for m, n, y, mo, d, g in rows))
    for r in rows:
        expect_record(conn, record(*r))
        conn.send("OK\n")
    cli.expect_stdout("OK\n" * 200, timeout=3)
    cli.close_stdin()
    finish(cli)
