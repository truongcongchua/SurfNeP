import os
import threading
import time

from njlib import Fail, WA, cases, group, sample, timeout


def start(ctx):
    return ctx.run_client()


def out_bytes(cli):
    with open(os.path.join(cli.workdir, ".stdout"), "rb") as fh:
        return fh.read()


def pump(cli, data):
    """Ghi stdin ở luồng riêng để không kẹt khi dữ liệu lớn hơn bộ đệm pipe."""
    def run():
        try:
            cli.write(data)
        except Fail:
            pass
        cli.close_stdin()
    t = threading.Thread(target=run, daemon=True)
    t.start()
    return t


def finish_and_check(cli, want):
    cli.close_stdin()
    code = cli.wait(timeout=4)
    got = out_bytes(cli)
    if got != want:
        raise Fail(WA, f"stdout có {len(got)} byte {got[:60]!r}…, mong đợi {len(want)} byte {want[:60]!r}…")
    if code != 0:
        raise Fail(WA, f"chương trình phải thoát mã 0 sau EOF, nhận được {code}")


def wait_prefix(cli, want, timeout=0.8):
    """stdout phải đã có đủ `want` (byte) trong `timeout` giây, dù stdin chưa đóng."""
    deadline = time.monotonic() + timeout
    while True:
        got = out_bytes(cli)
        if got == want:
            return
        if time.monotonic() >= deadline:
            raise Fail(WA, f"sau {timeout}s stdout là {got[-80:]!r} ({len(got)} byte), mong đợi {len(want)} byte "
                           f"(có phải đang đợi đủ dòng / đủ bộ đệm / EOF mới ghi?)")
        time.sleep(0.02)


@sample
def test_basic(ctx):
    """Hai dòng rồi EOF: stdout giống hệt, thoát mã 0"""
    cli = start(ctx)
    data = b"xin chao\nthe gioi\n"
    cli.write(data)
    finish_and_check(cli, data)


@sample
def test_line_by_line(ctx):
    """Mỗi dòng phải ra stdout ngay, không đợi EOF"""
    cli = start(ctx)
    sent = b""
    for line in [b"dong 1\n", b"dong 2 co dau cach\n", b"\n", b"dong 4\n"]:
        cli.write(line)
        sent += line
        wait_prefix(cli, sent)
    finish_and_check(cli, sent)


@group("edge")
def test_empty_stdin(ctx):
    """stdin rỗng (EOF ngay): stdout rỗng, thoát mã 0"""
    cli = start(ctx)
    finish_and_check(cli, b"")


@group("edge")
def test_no_trailing_newline(ctx):
    """Dòng cuối không có \\n vẫn phải được chép"""
    cli = start(ctx)
    data = b"abc\nkhong xuong dong"
    cli.write(data)
    finish_and_check(cli, data)


@group("edge")
def test_single_byte(ctx):
    cli = start(ctx)
    cli.write(b"x")
    finish_and_check(cli, b"x")


@group("edge")
def test_only_newlines(ctx):
    cli = start(ctx)
    data = b"\n\n\n\n"
    cli.write(data)
    finish_and_check(cli, data)


@group("edge")
def test_nul_bytes(ctx):
    """Dữ liệu chứa byte 0x00 (fgets/strlen làm mất dữ liệu)"""
    cli = start(ctx)
    data = b"a\x00b\n\x00\x00\nket thuc\x00\n"
    cli.write(data)
    finish_and_check(cli, data)


@group("edge")
def test_all_byte_values(ctx):
    """Cả 256 giá trị byte, hai lần liền"""
    cli = start(ctx)
    data = bytes(range(256)) * 2
    cli.write(data)
    finish_and_check(cli, data)


@group("edge")
def test_crlf_and_blank_lines(ctx):
    """CRLF, dòng trống, dòng chỉ có dấu cách: giữ nguyên"""
    cli = start(ctx)
    data = b"a\r\n\r\n\n   \n\tb\r"
    cli.write(data)
    finish_and_check(cli, data)


@group("edge")
@cases(4095, 4096, 4097, 8192, 65536, 200000, title="Một dòng dài {0} byte")
def test_long_line(ctx, n):
    cli = start(ctx)
    data = b"q" * n + b"\n"
    t = pump(cli, data)
    code = cli.wait(timeout=5)
    t.join(2)
    got = out_bytes(cli)
    if got != data:
        raise Fail(WA, f"stdout có {len(got)} byte, mong đợi {len(data)}")
    if code != 0:
        raise Fail(WA, "phải thoát mã 0")


@group("stream")
def test_partial_line_no_newline(ctx):
    """Mảnh dữ liệu chưa có \\n cũng phải ra stdout ngay (read trả về ngay khi có dữ liệu)"""
    cli = start(ctx)
    cli.write(b"chua xong dong")
    wait_prefix(cli, b"chua xong dong")
    cli.write(b" ... xong\n")
    wait_prefix(cli, b"chua xong dong ... xong\n")
    finish_and_check(cli, b"chua xong dong ... xong\n")


@group("stream")
def test_pause_then_data(ctx):
    """stdin im lặng 0,6 giây rồi mới có dữ liệu: chương trình không được thoát sớm"""
    cli = start(ctx)
    time.sleep(0.6)
    if cli.proc.poll() is not None:
        raise Fail(WA, f"chương trình đã thoát (mã {cli.proc.poll()}) khi stdin chưa kết thúc")
    cli.write(b"muon\n")
    wait_prefix(cli, b"muon\n")
    finish_and_check(cli, b"muon\n")


@group("stream")
def test_random_chunks(ctx):
    """50 KB nhị phân ghi vào stdin thành mảnh ngẫu nhiên"""
    rng = ctx.rng
    cli = start(ctx)
    data = bytes(rng.randrange(256) for _ in range(50000))
    i = 0
    while i < len(data):
        k = rng.randint(1, 3000)
        cli.write(data[i:i + k])
        i += k
    finish_and_check(cli, data)


@group("stream")
def test_byte_by_byte(ctx):
    """Từng byte một, có độ trễ nhỏ"""
    cli = start(ctx)
    data = b"tung byte mot\x00\r\n"
    for b in data:
        cli.write(bytes([b]))
        time.sleep(0.01)
    finish_and_check(cli, data)


@group("stress")
@timeout(14)
def test_2mb(ctx):
    """2 MB dữ liệu"""
    cli = start(ctx)
    data = b"".join(b"%07d " % i + b"z" * (i % 200) + b"\n" for i in range(20000))
    t = pump(cli, data)
    code = cli.wait(timeout=8)
    t.join(2)
    got = out_bytes(cli)
    if got != data:
        raise Fail(WA, f"stdout có {len(got)} byte, mong đợi {len(data)}")
    if code != 0:
        raise Fail(WA, "phải thoát mã 0")


@group("stress")
@timeout(14)
def test_300_lines_timely(ctx):
    """300 dòng, dòng nào cũng phải ra stdout trước khi dòng sau được gõ"""
    cli = start(ctx)
    sent = b""
    for i in range(300):
        line = f"dong {i}\n".encode()
        cli.write(line)
        sent += line
        wait_prefix(cli, sent, timeout=0.7)
    finish_and_check(cli, sent)


@group("stress")
@timeout(14)
def test_binary_1mb_random(ctx):
    """1 MB nhị phân ngẫu nhiên"""
    cli = start(ctx)
    data = bytes(ctx.rng.randrange(256) for _ in range(1 << 20))
    t = pump(cli, data)
    code = cli.wait(timeout=8)
    t.join(2)
    got = out_bytes(cli)
    if got != data:
        raise Fail(WA, f"stdout có {len(got)} byte, mong đợi {len(data)}")
    if code != 0:
        raise Fail(WA, "phải thoát mã 0")


@group("robust")
@cases(b"\x00", b"\x00\x00\x00\n", b"\n\x00", b"\xff\xfe\x00\x01", title="Byte lạ {0!r}")
def test_odd_bytes(ctx, data):
    cli = start(ctx)
    cli.write(data)
    finish_and_check(cli, data)
