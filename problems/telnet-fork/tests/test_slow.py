import time

from njlib import BLOCKED, Fail, WA, group


@group("concurrency")
def test_slow_command_does_not_block(ctx):
    """Một client chạy lệnh chậm (sleep 1.5) không làm chậm client khác"""
    a = ctx.connect(name="A")
    a.send_line("admin admin")
    a.expect_line("LOGIN OK")
    with ctx.verdict(BLOCKED):
        b = ctx.connect(name="B")
        b.send_line("guest nopass")
        b.expect_line("LOGIN OK")
    a.send_line("sleep 1.5; echo xong")
    time.sleep(0.1)
    with ctx.verdict(BLOCKED):
        b.send_line("echo nhanh")
        b.expect_line("OUTPUT 6", timeout=0.6)
        if b.recv_exact(6) != b"nhanh\n":
            raise Fail(WA, "B nhận sai kết quả")
    a.expect_line("OUTPUT 5", timeout=3)
    if a.recv_exact(5) != b"xong\n":
        raise Fail(WA, "A nhận sai kết quả")
