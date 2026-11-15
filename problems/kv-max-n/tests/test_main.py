import time

from njlib import BLOCKED, LIMIT, args, sample


def hello(ctx, name=None):
    c = ctx.connect(name=name)
    c.expect_line("WELCOME")
    return c


@sample
def test_basic(ctx):
    """SET / GET / DEL / COUNT cơ bản"""
    c = hello(ctx)
    for cmd, want in [("GET mssv", "NOT_FOUND"), ("SET mssv 20211234", "OK"),
                      ("GET mssv", "VALUE 20211234"), ("SET mssv 20219999", "OK"),
                      ("GET mssv", "VALUE 20219999"), ("SET ten An", "OK"), ("COUNT", "COUNT 2"),
                      ("DEL mssv", "OK"), ("DEL mssv", "NOT_FOUND"), ("COUNT", "COUNT 1")]:
        c.send_line(cmd)
        c.expect_line(want)


@sample
def test_errors(ctx):
    """Lệnh sai trả về ERROR, kết nối vẫn dùng được"""
    c = hello(ctx)
    for bad in ["HELLO", "SET a", "SET a b c", "GET", "GET a b", "DEL", "COUNT x", "set a b", ""]:
        c.send_line(bad)
        c.expect_line("ERROR")
    c.send_line("SET a b")
    c.expect_line("OK")


@sample
def test_quit(ctx):
    """QUIT trả BYE rồi đóng kết nối"""
    c = hello(ctx)
    c.send_line("QUIT")
    c.expect_line("BYE")
    c.expect_closed()

def test_idle_client_does_not_block(ctx):
    """Một client im lặng hoặc gửi dở lệnh không làm treo client khác"""
    idle = hello(ctx, "idle")
    idle.send("SET half")
    with ctx.verdict(BLOCKED):
        b = hello(ctx, "B")
        b.send_line("SET k v")
        b.expect_line("OK", timeout=0.5)
    idle.send("_done v\n")
    idle.expect_line("OK")
    b.send_line("GET half_done")
    b.expect_line("VALUE v")


def test_shared_state(ctx):
    """Dữ liệu dùng chung giữa các client"""
    a, b = hello(ctx, "A"), hello(ctx, "B")
    a.send_line("SET k1 tu_A")
    a.expect_line("OK")
    b.send_line("GET k1")
    b.expect_line("VALUE tu_A")
    b.send_line("DEL k1")
    b.expect_line("OK")
    a.send_line("GET k1")
    a.expect_line("NOT_FOUND")


def test_fragmented_and_coalesced(ctx):
    """Lệnh bị cắt vụn và nhiều lệnh dính nhau"""
    c = hello(ctx)
    c.send_slowly("SET x 1\r\n", chunk=1, delay=0.01)
    c.expect_line("OK")
    c.send("SET y 2\nGET x\nGET y\r\nCOUNT\n")
    for want in ["OK", "VALUE 1", "VALUE 2", "COUNT 2"]:
        c.expect_line(want)




@args("{port}", "3")
def test_limit(ctx):
    """N=3: client thứ 4 nhận FULL và bị đóng"""
    cs = [hello(ctx, f"C{i}") for i in range(1, 4)]
    with ctx.verdict(LIMIT):
        extra = ctx.connect(name="C4")
        extra.expect_line("FULL")
        extra.expect_closed()
    for c in cs:
        c.send_line("COUNT")
        c.expect_line("COUNT 0")


@args("{port}", "2")
def test_slot_freed(ctx):
    """Chỗ được giải phóng sau QUIT và sau khi client đóng đột ngột"""
    a, b = hello(ctx, "A"), hello(ctx, "B")
    with ctx.verdict(LIMIT):
        x = ctx.connect(name="X")
        x.expect_line("FULL")
        a.send_line("QUIT")
        a.expect_line("BYE")
        time.sleep(0.1)
        c = hello(ctx, "C")
        b.close()
        time.sleep(0.1)
        hello(ctx, "D")
        y = ctx.connect(name="Y")
        y.expect_line("FULL")
    c.send_line("COUNT")
    c.expect_line("COUNT 0")


@args("{port}", "1")
def test_n_equals_one(ctx):
    """Trường hợp biên N=1"""
    a = hello(ctx, "A")
    with ctx.verdict(LIMIT):
        b = ctx.connect(name="B")
        b.expect_line("FULL")
    a.send_line("QUIT")
    a.expect_line("BYE")
    time.sleep(0.1)
    hello(ctx, "C")


def test_pipelined_many_clients(ctx):
    """10 client, mỗi client dồn 50 lệnh một lúc"""
    cs = [hello(ctx, f"C{i}") for i in range(10)]
    for i, c in enumerate(cs):
        c.send("".join(f"SET k{i}_{j} v{j}\n" for j in range(50)))
    for c in cs:
        for _ in range(50):
            c.expect_line("OK", timeout=2)
    for i, c in enumerate(cs):
        c.send("".join(f"GET k{(i + 1) % 10}_{j}\n" for j in range(50)))
    for c in cs:
        for j in range(50):
            c.expect_line(f"VALUE v{j}", timeout=2)
    cs[0].send_line("COUNT")
    cs[0].expect_line("COUNT 500")
