# Bộ test chung cho telnet-select và telnet-fork (bài fork có thêm test_concurrent.py).
from njlib import BLOCKED, Fail, WA, sample


def login(ctx, user="admin", pw="admin", name=None):
    c = ctx.connect(name=name)
    c.send_line(f"{user} {pw}")
    c.expect_line("LOGIN OK")
    return c


def run(c, cmd, timeout=2.0):
    c.send_line(cmd)
    head = c.recv_line(timeout, expecting="OUTPUT <n>")
    parts = head.split(" ")
    if len(parts) != 2 or parts[0] != "OUTPUT" or not parts[1].isdigit():
        raise Fail(WA, f"{c.name}: mong đợi dòng 'OUTPUT <n>', nhận được {head!r}")
    return c.recv_exact(int(parts[1]), timeout).decode(errors="replace")


def expect_output(c, cmd, want):
    got = run(c, cmd)
    if got != want:
        raise Fail(WA, f"lệnh {cmd!r}: mong đợi {want!r}, nhận được {got!r}")


@sample
def test_login_and_echo(ctx):
    """Đăng nhập đúng rồi chạy lệnh echo"""
    c = login(ctx)
    expect_output(c, "echo hello", "hello\n")


@sample
def test_login_fail_then_retry(ctx):
    """Sai mật khẩu báo LOGIN FAIL, cho thử lại"""
    c = ctx.connect()
    for bad in ["admin sai", "khongco admin", "admin", "admin admin admin", "guest  nopass"]:
        c.send_line(bad)
        c.expect_line("LOGIN FAIL")
    c.send_line("guest nopass")
    c.expect_line("LOGIN OK")


def test_cat_file(ctx):
    """Kết quả nhiều dòng của lệnh cat"""
    c = login(ctx, "sv20201234", "matkhau123")
    expect_output(c, "cat data.txt", "dong mot\ndong hai\n")


def test_empty_and_stderr(ctx):
    """Lệnh không in gì -> OUTPUT 0; thông báo lỗi (stderr) cũng được gửi về"""
    c = login(ctx)
    expect_output(c, "true", "")
    out = run(c, "cat khong_ton_tai.txt")
    if "khong_ton_tai.txt" not in out:
        raise Fail(WA, f"thông báo lỗi của lệnh phải được gửi về (chuyển hướng 2>&1), nhận được {out!r}")


def test_large_output(ctx):
    """Kết quả lớn (seq 1 20000)"""
    c = login(ctx)
    expect_output(c, "seq 1 20000", "".join(f"{i}\n" for i in range(1, 20001)))


def test_several_commands_and_exit(ctx):
    """Nhiều lệnh liên tiếp, exit trả BYE và đóng"""
    c = login(ctx)
    for i in range(5):
        expect_output(c, f"echo lan{i}", f"lan{i}\n")
    c.send_line("exit")
    c.expect_line("BYE")
    c.expect_closed()


def test_two_users_isolated(ctx):
    """Hai người dùng cùng lúc, kết quả không lẫn nhau"""
    a = login(ctx, name="A")
    with ctx.verdict(BLOCKED):
        b = login(ctx, "guest", "nopass", name="B")
    for i in range(5):
        a.send_line(f"echo A{i}")
        b.send_line(f"echo B{i}")
        for c, tag in ((a, "A"), (b, "B")):
            head = c.recv_line(2)
            body = c.recv_exact(int(head.split()[1]), 2).decode()
            if body != f"{tag}{i}\n":
                raise Fail(WA, f"{c.name} nhận {body!r}, mong đợi {tag}{i}\\n — kết quả bị lẫn giữa các client?")


def test_not_logged_in(ctx):
    """Chưa đăng nhập thì lệnh được coi là lần đăng nhập sai"""
    c = ctx.connect()
    c.send_line("echo hack")
    c.expect_line("LOGIN FAIL")
