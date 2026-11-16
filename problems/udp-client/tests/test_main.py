import time

from njlib import Fail, WA, cases, group, sample, timeout


def start(ctx):
    srv = ctx.mock_udp_server()
    cli = ctx.run_client("127.0.0.1", srv.port)
    return cli, srv


def finish(cli):
    cli.close_stdin()
    code = cli.wait()
    if code != 0:
        raise Fail(WA, f"client phải thoát mã 0 sau EOF, nhận được {code}")


@sample
def test_request_reply(ctx):
    """Một dòng thành một datagram (không có \\n), phản hồi được in ra"""
    cli, srv = start(ctx)
    cli.write("12 + 30\n")
    srv.expect(b"12 + 30")
    srv.reply("42")
    cli.expect_stdout("42\n")
    finish(cli)


@sample
def test_several_lines(ctx):
    """Nhiều dòng liên tiếp, mỗi dòng đúng một datagram, in đủ phản hồi theo thứ tự"""
    cli, srv = start(ctx)
    out = ""
    for line, rep in [("-7 / 2", "-3"), ("5 % 0", "ERROR div0"), ("COUNT", "2"), ("a b c", "ERROR syntax")]:
        cli.write(line + "\n")
        srv.expect(line.encode())
        srv.reply(rep)
        out += rep + "\n"
        cli.expect_stdout(out, timeout=1.0)
    finish(cli)


@sample
def test_timeout_then_continue(ctx):
    """Server im lặng: in TIMEOUT sau khoảng 1 giây (không sớm, không treo), rồi vẫn phục vụ dòng sau"""
    cli, srv = start(ctx)
    cli.write("mat goi\n")
    srv.expect(b"mat goi")
    time.sleep(0.5)
    if "TIMEOUT" in cli.stdout():
        raise Fail(WA, "client in TIMEOUT quá sớm (chưa đợi đủ ~1 giây)")
    cli.expect_stdout("TIMEOUT\n", timeout=1.5)
    cli.write("dong sau\n")
    srv.expect(b"dong sau")
    srv.reply("tra loi")
    out = cli.expect_stdout("tra loi\n")
    if out != "TIMEOUT\ntra loi\n":
        raise Fail(WA, f"stdout mong đợi 'TIMEOUT\\ntra loi\\n', nhận được {out!r}")
    finish(cli)


@group("edge")
def test_empty_lines_skipped(ctx):
    """Dòng rỗng không được gửi và không in gì"""
    cli, srv = start(ctx)
    cli.write("\n\nx\n\n")
    srv.expect(b"x")
    srv.reply("ok")
    cli.expect_stdout("ok\n")
    srv.expect_nothing(0.3)
    out = cli.stdout()
    if out != "ok\n":
        raise Fail(WA, f"stdout mong đợi 'ok\\n', nhận được {out!r}")
    finish(cli)


@group("edge")
def test_crlf_stripped(ctx):
    """Dòng kết thúc bằng \\r\\n: datagram không chứa \\r"""
    cli, srv = start(ctx)
    cli.write("hello\r\n")
    srv.expect(b"hello")
    srv.reply("hi")
    cli.expect_stdout("hi\n")
    finish(cli)


@group("basic")
def test_long_reply(ctx):
    """Phản hồi dài 1500 byte vẫn được in đủ"""
    cli, srv = start(ctx)
    cli.write("big\n")
    srv.expect(b"big")
    body = "".join(chr(ord("a") + i % 26) for i in range(1500))
    srv.reply(body)
    cli.expect_stdout(body + "\n")
    finish(cli)


@group("basic")
def test_replies_not_mixed_up(ctx):
    """Phản hồi của dòng nào in ở dòng đó (đợi xong dòng trước mới gửi dòng sau)"""
    cli, srv = start(ctx)
    cli.write("1\n2\n3\n")
    for i in range(1, 4):
        srv.expect(str(i).encode())
        srv.reply(f"r{i}")
    out = cli.expect_stdout("r3\n")
    if out != "r1\nr2\nr3\n":
        raise Fail(WA, f"stdout mong đợi 'r1\\nr2\\nr3\\n', nhận được {out!r}")
    finish(cli)


@group("edge")
def test_bad_ip(ctx):
    """Địa chỉ IP sai: báo lỗi, thoát mã khác 0"""
    cli = ctx.run_client("999.1.2.3", 9)
    if cli.wait(timeout=2) == 0:
        raise Fail(WA, "client phải thoát mã khác 0 khi địa chỉ IP không hợp lệ")


# ======================= phần mở rộng (thiết kế lại) =======================

@group("edge")
def test_reply_with_nul(ctx):
    """Phản hồi chứa byte 0x00: in đủ từng byte (printf %s dừng ở 0x00)"""
    cli, srv = start(ctx)
    cli.write("nul\n")
    srv.expect(b"nul")
    srv.reply(b"a\x00b\x00c")
    cli.expect_stdout("a\x00b\x00c\n")
    finish(cli)


@group("edge")
def test_empty_reply(ctx):
    """Phản hồi là datagram rỗng: in một dòng trống (không phải TIMEOUT)"""
    cli, srv = start(ctx)
    cli.write("rong\n")
    srv.expect(b"rong")
    srv.reply(b"")
    cli.expect_stdout("\n", timeout=0.8)
    time.sleep(1.2)
    if "TIMEOUT" in cli.stdout():
        raise Fail(WA, "datagram rỗng là một phản hồi hợp lệ, không phải TIMEOUT")
    finish(cli)


@group("edge")
def test_reply_2048(ctx):
    """Phản hồi dài đúng 2048 byte"""
    cli, srv = start(ctx)
    cli.write("max\n")
    srv.expect(b"max")
    body = "".join(chr(ord("A") + i % 26) for i in range(2048))
    srv.reply(body)
    cli.expect_stdout(body + "\n")
    finish(cli)


@group("edge")
def test_long_request_line(ctx):
    """Dòng nhập dài 1500 byte: gửi trong một datagram nguyên vẹn"""
    cli, srv = start(ctx)
    line = "y" * 1500
    cli.write(line + "\n")
    srv.expect(line.encode())
    srv.reply("ok")
    cli.expect_stdout("ok\n")
    finish(cli)


@group("edge")
def test_last_line_no_newline(ctx):
    """Dòng cuối không có xuống dòng vẫn được gửi; dòng chỉ có CR coi là rỗng"""
    cli, srv = start(ctx)
    cli.write("\r\ncuoi")
    cli.close_stdin()
    srv.expect(b"cuoi")
    srv.reply("da nhan")
    cli.expect_stdout("da nhan\n")
    srv.expect_nothing(0.2)
    if cli.wait() != 0:
        raise Fail(WA, "client phải thoát mã 0")


@group("basic")
def test_spaces_preserved(ctx):
    """Dấu cách đầu/cuối dòng và tab được giữ nguyên trong datagram"""
    cli, srv = start(ctx)
    cli.write("  a\tb  \n")
    srv.expect(b"  a\tb  ")
    srv.reply(" r ")
    cli.expect_stdout(" r \n")
    finish(cli)


@group("robust")
@timeout(12)
def test_three_timeouts(ctx):
    """Ba lần liên tiếp không có phản hồi rồi mới có: TIMEOUT ×3 rồi in phản hồi"""
    cli, srv = start(ctx)
    for i in range(3):
        cli.write(f"m{i}\n")
        srv.expect(f"m{i}".encode(), timeout=2.5)
    cli.write("cuoi\n")
    srv.expect(b"cuoi", timeout=2.5)
    srv.reply("xong")
    out = cli.expect_stdout("xong\n", timeout=2)
    if out != "TIMEOUT\nTIMEOUT\nTIMEOUT\nxong\n":
        raise Fail(WA, f"stdout mong đợi 3 dòng TIMEOUT rồi 'xong', nhận {out!r}")
    finish(cli)


@group("stress")
@timeout(12)
def test_300_requests(ctx):
    """300 dòng, phản hồi ngay: đủ 300 dòng đúng thứ tự"""
    cli, srv = start(ctx)
    want = ""
    cli.write("".join(f"req {i}\n" for i in range(300)))
    for i in range(300):
        srv.expect(f"req {i}".encode())
        srv.reply(f"rep {i}")
        want += f"rep {i}\n"
    out = cli.expect_stdout(want[-12:], timeout=2)
    if out != want:
        raise Fail(WA, "stdout không đủ / sai thứ tự 300 phản hồi")
    finish(cli)
