import os
import time

from njlib import Fail, WA


def _zombies_of(ppid):
    n = 0
    for pid in os.listdir("/proc"):
        if not pid.isdigit():
            continue
        try:
            with open(f"/proc/{pid}/stat") as fh:
                parts = fh.read().rsplit(")", 1)[1].split()
        except OSError:
            continue
        if parts[0] == "Z" and int(parts[1]) == ppid:
            n += 1
    return n


def test_no_zombies(ctx):
    """Tiến trình con kết thúc thì phải được thu dọn (không còn zombie)"""
    for i in range(10):
        c = ctx.connect(name=f"C{i}")
        c.send("x\n")
        c.expect_line("x")
        c.close()
    time.sleep(0.6)
    z = _zombies_of(ctx.server.proc.pid)
    if z:
        raise Fail(WA, f"còn {z} tiến trình zombie — cần waitpid() (ví dụ trong handler SIGCHLD)")
    c = ctx.connect(name="after")
    c.send("van chay\n")
    c.expect_line("van chay")
