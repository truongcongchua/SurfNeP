# Thiết kế: docs/TEST-DESIGN.md. Phần "tối đa N client" dùng chung: judge/runner/suites.py (maxn_suite).
import time

from njlib import BLOCKED, LIMIT, WA, Fail, args, cases, group, sample, timeout
from suites import maxn_suite


def hello(ctx, name=None):
    c = ctx.connect(name=name)
    c.expect_line("WELCOME")
    return c


@sample
def test_echo_count_quit(ctx):
    """ECHO, COUNT và QUIT cơ bản"""
    c = hello(ctx)
    for cmd, want in [("hello", "ECHO hello"), ("", "ECHO "), ("a b  c", "ECHO a b  c"),
                      ("COUNT", "COUNT 1"), ("count", "ECHO count")]:
        c.send_line(cmd)
        c.expect_line(want)
    c.send_line("QUIT")
    c.expect_line("BYE")
    c.expect_closed()


@sample
@args("{port}", "2")
def test_full(ctx):
    """N=2: client thứ 3 nhận FULL và bị đóng, client cũ vẫn dùng được"""
    a, b = hello(ctx, "A"), hello(ctx, "B")
    with ctx.verdict(LIMIT):
        extra = ctx.connect(name="C")
        extra.expect_line("FULL")
        extra.expect_closed()
    a.send_line("COUNT")
    a.expect_line("COUNT 2")
    b.send_line("x")
    b.expect_line("ECHO x")


# ---------------- basic: đúng từng nhánh của giao thức ----------------

@group("basic")
@cases(("COUNT ", "ECHO COUNT "), (" COUNT", "ECHO  COUNT"), ("QUIT ", "ECHO QUIT "), ("quit", "ECHO quit"),
       ("COUNTX", "ECHO COUNTX"), ("ECHO", "ECHO ECHO"), ("BYE", "ECHO BYE"), ("\t", "ECHO \t"),
       title="Không phải lệnh: {0!r} → {1!r}")
def test_not_a_command(ctx, line, want):
    c = hello(ctx)
    c.send_line(line)
    c.expect_line(want)
    c.send_line("COUNT")
    c.expect_line("COUNT 1")


@group("basic")
def test_count_tracks_joins_and_leaves(ctx):
    """COUNT tăng khi có người vào, giảm khi có người rời (QUIT, đóng, RST)"""
    a = hello(ctx, "A")
    others = []
    for k in range(4):
        others.append(hello(ctx, f"B{k}"))
        a.send_line("COUNT")
        a.expect_line(f"COUNT {k + 2}")
    others[0].send_line("QUIT")
    others[0].expect_line("BYE")
    others[1].close()
    others[2].reset()
    time.sleep(0.3)
    a.send_line("COUNT")
    a.expect_line("COUNT 2")


# ---------------- edge ----------------

@group("edge")
@cases(1, 255, 256, 511, 512, 1000, title="Dòng dài {0} ký tự")
def test_long_line(ctx, n):
    c = hello(ctx)
    line = "".join(ctx.rng.choice("abcxyz 0123") for _ in range(n))
    c.send_line(line)
    c.expect_line("ECHO " + line)


@group("edge")
def test_crlf_and_empty(ctx):
    """'\\r\\n', dòng rỗng, dòng chỉ có '\\r'"""
    c = hello(ctx)
    c.send("COUNT\r\nQ\r\n\r\n\n\r\n")
    c.expect_lines(["COUNT 1", "ECHO Q", "ECHO ", "ECHO ", "ECHO "])
    c.send("QUIT\r\n")
    c.expect_line("BYE")


# ---------------- stream ----------------

@group("stream")
def test_fragmented_and_coalesced(ctx):
    """Dòng bị cắt vụn và nhiều dòng dính nhau"""
    c = hello(ctx)
    c.send_slowly("xin chao\r\n", chunk=1, delay=0.01)
    c.expect_line("ECHO xin chao")
    c.send("a\nb\nCOUNT\nc\n")
    c.expect_lines(["ECHO a", "ECHO b", "COUNT 1", "ECHO c"])


@group("stream")
def test_random_fragments_300_lines(ctx):
    """300 dòng ngẫu nhiên cắt thành mảnh 1–40 byte"""
    rng = ctx.rng
    c = hello(ctx)
    lines = ["".join(rng.choice("abc DEF\t123") for _ in range(rng.randint(0, 60))) for _ in range(300)]
    lines = [l for l in lines if l.rstrip("\r") not in ("COUNT", "QUIT")]
    c.send_chunks("".join(l + "\n" for l in lines), rng, 1, 40, delay=0)
    for l in lines:
        c.expect_line("ECHO " + l, timeout=2)


@group("stream")
def test_burst_1000_lines(ctx):
    """1000 dòng dính nhau trong một lần gửi"""
    c = hello(ctx)
    c.send("".join(f"dong {i}\n" for i in range(1000)))
    for i in range(1000):
        c.expect_line(f"ECHO dong {i}", timeout=2)


# ---------------- concurrency ----------------

def test_idle_client_does_not_block(ctx):
    """Một client im lặng hoặc gửi dở dòng không làm treo client khác"""
    idle = hello(ctx, "idle")
    idle.send("na")
    with ctx.verdict(BLOCKED):
        b = hello(ctx, "B")
        b.send_line("ping")
        b.expect_line("ECHO ping", timeout=0.5)
    idle.send("m\n")
    idle.expect_line("ECHO nam")


test_idle_client_does_not_block = group("concurrency")(test_idle_client_does_not_block)


@group("concurrency")
@args("{port}", "10")
def test_interleaved_random(ctx):
    """N=10: 10 client gửi xen kẽ ngẫu nhiên, mỗi client chỉ nhận đúng dòng của mình"""
    rng = ctx.rng
    cs = [hello(ctx, f"C{i}") for i in range(10)]
    with ctx.verdict(BLOCKED):
        for r in range(8):
            order = list(range(10))
            rng.shuffle(order)
            for i in order:
                cs[i].send_chunks(f"C{i} vong {r}\n", rng, 1, 6, delay=0)
            for i in order:
                cs[i].expect_line(f"ECHO C{i} vong {r}", timeout=1.5)


@group("stress")
@args("{port}", "10")
@timeout(15)
def test_count_model_random(ctx):
    """N=10: 120 lần vào/ra ngẫu nhiên, COUNT luôn đúng với mô hình"""
    rng = ctx.rng
    live, k = [], 0
    for step in range(120):
        if (rng.random() < 0.55 and len(live) < 10) or not live:
            k += 1
            live.append(hello(ctx, f"C{k}"))
        else:
            c = live.pop(rng.randrange(len(live)))
            if rng.random() < 0.5:
                c.send_line("QUIT")
                c.expect_line("BYE")
                c.expect_closed()
            else:
                (c.close if rng.random() < 0.5 else c.reset)()
                time.sleep(0.1)
        if live:
            w = rng.choice(live)
            w.send_line("COUNT")
            got = w.recv_line(timeout=1.5)
            if got != f"COUNT {len(live)}":
                raise Fail(WA, f"bước {step}: đang có {len(live)} client, {w.name} nhận {got!r}")


globals().update(maxn_suite(ping=("abc", "ECHO abc")))
