# Bộ test dùng chung cho các bài "echo đồng thời": nonblock-accept, fork-echo, thread-echo, select-echo.
import time

from njlib import BLOCKED, sample


@sample
def test_echo(ctx):
    """Echo cơ bản"""
    c = ctx.connect()
    c.send("xin chao\n")
    c.expect_line("xin chao")


@sample
def test_idle_client_does_not_block(ctx):
    """Client A kết nối nhưng im lặng, client B vẫn được phục vụ ngay"""
    a = ctx.connect(name="A")
    with ctx.verdict(BLOCKED):
        b = ctx.connect(name="B")
        b.send("B day\n")
        b.expect_line("B day", timeout=0.5)
    a.send("A day\n")
    a.expect_line("A day")


def test_interleaved(ctx):
    """20 client gửi xen kẽ"""
    cs = [ctx.connect(name=f"C{i}") for i in range(20)]
    with ctx.verdict(BLOCKED):
        for r in range(3):
            for i, c in enumerate(cs):
                c.send(f"{i}:{r}\n")
            for i, c in enumerate(cs):
                c.expect_line(f"{i}:{r}", timeout=1.0)


def test_disconnect_others_continue(ctx):
    """Một client rời đi, các client khác không bị ảnh hưởng"""
    a, b, c = ctx.connect(name="A"), ctx.connect(name="B"), ctx.connect(name="C")
    a.send("a\n")
    a.expect_line("a")
    b.close()
    time.sleep(0.1)
    c.send("c van o day\n")
    c.expect_line("c van o day")
    a.send("a lan 2\n")
    a.expect_line("a lan 2")
    d = ctx.connect(name="D")
    d.send("d moi vao\n")
    d.expect_line("d moi vao")


def test_binary_and_large(ctx):
    """Echo 64 KB nhị phân trong khi client khác đang kết nối"""
    other = ctx.connect(name="other")
    c = ctx.connect(name="big")
    blob = bytes(range(256)) * 256
    for i in range(0, len(blob), 8192):
        c.send(blob[i:i + 8192])
        c.expect_bytes(blob[i:i + 8192], timeout=2)
    other.send("van song\n")
    other.expect_line("van song")


def test_many_clients(ctx):
    """50 client kết nối cùng lúc"""
    cs = [ctx.connect(name=f"C{i}") for i in range(50)]
    for i, c in enumerate(cs):
        c.send(f"hello {i}\n")
    for i, c in enumerate(cs):
        c.expect_line(f"hello {i}", timeout=1.5)
