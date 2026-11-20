import os
import socket
import time

from njlib import Fail, WA, cases, group, sample, timeout


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


@group("basic")
def test_server_closes_first(ctx):
    """Server đóng kết nối khi stdin còn mở: client thoát mã 0"""
    cli, conn = start(ctx)
    conn.send("bye\n")
    conn.close()
    cli.expect_stdout("bye\n", timeout=1.0)
    code = cli.wait(timeout=1.5)
    if code != 0:
        raise Fail(WA, f"client phải thoát mã 0 khi server đóng, nhận được {code}")


@group("concurrency")
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


@group("stress")
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
def test_stdin_eof_immediately(ctx):
    """stdin rỗng: client shutdown ngay, vẫn in tin server gửi sau đó, server đóng thì thoát 0"""
    cli, conn = start(ctx)
    cli.close_stdin()
    conn.expect_closed(timeout=1.5)
    conn.send("van nhan duoc\n")
    cli.expect_stdout("van nhan duoc\n", timeout=1.0)
    conn.close()
    if cli.wait(timeout=1.5) != 0:
        raise Fail(WA, "client phải thoát mã 0")


@group("edge")
def test_binary_both_ways(ctx):
    """Byte 0x00 và dữ liệu không có '\\n' đi qua cả hai chiều nguyên vẹn"""
    cli, conn = start(ctx)
    conn.send(b"a\x00b\x00\x00c")
    deadline = time.monotonic() + 1.0
    while time.monotonic() < deadline:
        out = open(os.path.join(cli.workdir, ".stdout"), "rb").read()
        if len(out) >= 6:
            break
        time.sleep(0.02)
    if out != b"a\x00b\x00\x00c":
        raise Fail(WA, f"stdout phải đúng từng byte server gửi, nhận {out!r}")
    cli.write(b"x\x00y\n")
    conn.expect_bytes(b"x\x00y\n", timeout=1.0)


@group("stream")
def test_server_sends_bytewise(ctx):
    """Server gửi từng byte có độ trễ: client in ngay từng phần, không đợi đủ dòng"""
    cli, conn = start(ctx)
    conn.send_slowly("tung byte mot", chunk=1, delay=0.02)
    cli.expect_stdout("tung byte mot", timeout=1.0)


@group("stream")
def test_stdin_partial_line(ctx):
    """stdin có nửa dòng (chưa có '\\n'): phần đó cũng phải được gửi ngay"""
    cli, conn = start(ctx)
    cli.write("nua dong")
    conn.expect_bytes(b"nua dong", timeout=1.0)
    cli.write(" con lai\n")
    conn.expect_line(" con lai", timeout=1.0)


@group("robust")
def test_server_reset(ctx):
    """Server mất kết nối đột ngột (RST): client thoát (không treo)"""
    cli, conn = start(ctx)
    conn.send("truoc khi mat\n")
    cli.expect_stdout("truoc khi mat\n")
    conn.reset()
    cli.wait(timeout=1.5)


@group("robust")
def test_server_closes_while_typing(ctx):
    """Server đóng trong lúc stdin vẫn đổ dữ liệu: client thoát mã 0, không chết vì SIGPIPE"""
    cli, conn = start(ctx)
    conn.close()
    for i in range(50):
        try:
            cli.write(f"go tiep {i}\n" * 50)
        except Fail:
            break
        time.sleep(0.005)
    code = cli.wait(timeout=2)
    if code != 0:
        raise Fail(WA, f"client phải thoát mã 0 khi server đóng, nhận {code}" + (" (bị SIGPIPE?)" if code and code < 0 else ""))


@group("stress")
@timeout(12)
def test_flood_from_server(ctx):
    """Server dồn 2 MB trong khi stdin im lặng"""
    cli, conn = start(ctx)
    blob = b"".join(b"%06d" % i + b"m" * 94 + b"\n" for i in range(20000))
    conn.send(blob)
    conn.close()
    cli.wait(timeout=6)
    out = open(os.path.join(cli.workdir, ".stdout"), "rb").read()
    if out != blob:
        raise Fail(WA, f"stdout có {len(out)} byte, mong đợi {len(blob)}")


@group("stress")
@timeout(12)
def test_many_turns(ctx):
    """200 lượt hỏi-đáp xen kẽ"""
    cli, conn = start(ctx)
    expect = ""
    for i in range(200):
        cli.write(f"q{i}\n")
        conn.expect_line(f"q{i}", timeout=0.7)
        conn.send(f"a{i}\n")
        expect += f"a{i}\n"
        cli.expect_stdout(f"a{i}\n", timeout=0.7)
    if cli.stdout() != expect:
        raise Fail(WA, "stdout không khớp toàn bộ chuỗi trả lời")


def cpu_seconds(pid):
    with open(f"/proc/{pid}/stat") as fh:
        f = fh.read().rsplit(")", 1)[1].split()
    return (int(f[11]) + int(f[12])) / os.sysconf("SC_CLK_TCK")


@group("robust")
@timeout(8)
def test_no_busy_loop_after_eof(ctx):
    """stdin EOF rồi server im lặng 1.5 giây: client phải ngủ trong poll, không lặp 100% CPU"""
    cli, conn = start(ctx)
    cli.close_stdin()
    conn.expect_closed(timeout=1.5)
    before = cpu_seconds(cli.proc.pid)
    time.sleep(1.5)
    used = cpu_seconds(cli.proc.pid) - before
    if used > 0.5:
        raise Fail(WA, f"client dùng {used:.2f}s CPU trong 1.5s chờ — sau EOF phải bỏ stdin khỏi poll (fd = -1)")
    conn.send("van nhan\n")
    cli.expect_stdout("van nhan\n")
    conn.close()
    cli.wait(timeout=1.5)
