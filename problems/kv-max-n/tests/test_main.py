# Thiết kế: docs/TEST-DESIGN.md. Phần "tối đa N client" dùng chung: judge/runner/suites.py (maxn_suite).
import time

from njlib import BLOCKED, LIMIT, WA, Fail, args, cases, group, sample, timeout
from suites import maxn_suite


def hello(ctx, name=None):
    c = ctx.connect(name=name)
    c.expect_line("WELCOME")
    return c


class Model:
    """Mô hình chuẩn của bảng key-value (để so sánh vi sai)."""

    def __init__(self):
        self.d = {}

    def run(self, line):
        w = line.rstrip("\r").split(" ")
        w = [x for x in w if x]
        if any(len(x) > 64 for x in w[1:]):
            return "ERROR"
        if len(w) == 3 and w[0] == "SET":
            if w[1] not in self.d and len(self.d) >= 1000:
                return "ERROR"
            self.d[w[1]] = w[2]
            return "OK"
        if len(w) == 2 and w[0] == "GET":
            return f"VALUE {self.d[w[1]]}" if w[1] in self.d else "NOT_FOUND"
        if len(w) == 2 and w[0] == "DEL":
            return "OK" if self.d.pop(w[1], None) is not None else "NOT_FOUND"
        if w == ["COUNT"]:
            return f"COUNT {len(self.d)}"
        return "ERROR"


def check(c, model, cmds, timeout=2):
    c.send("".join(x + "\n" for x in cmds))
    for x in cmds:
        want = model.run(x)
        got = c.recv_line(timeout=timeout)
        if got != want:
            raise Fail(WA, f"{c.name}: lệnh {x!r} mong đợi {want!r}, nhận được {got!r}")


# ---------------- sample ----------------

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


# ---------------- basic ----------------

@group("basic")
@cases("Get a", "GETa", "DEL a b", "COUNT 1", "QUIT now", "SETa b", "  ", "\t", "SET\ta b", "GET\ta",
       title="Lệnh sai {0!r} → ERROR")
def test_more_errors(ctx, line):
    c = hello(ctx)
    c.send_line(line)
    c.expect_line("ERROR")
    c.send_line("COUNT")
    c.expect_line("COUNT 0")


@group("basic")
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


@group("basic")
def test_state_survives_disconnect(ctx):
    """Dữ liệu còn nguyên sau khi client ghi nó đã rời đi (kể cả RST)"""
    a = hello(ctx, "A")
    a.send("SET x 1\nSET y 2\n")
    a.expect_lines(["OK", "OK"])
    a.reset()
    time.sleep(0.2)
    b = hello(ctx, "B")
    b.send("GET x\nGET y\nCOUNT\n")
    b.expect_lines(["VALUE 1", "VALUE 2", "COUNT 2"])


@group("basic")
def test_special_chars_in_values(ctx):
    """Key/value chứa ký tự đặc biệt (không phải dấu cách)"""
    c = hello(ctx)
    m = Model()
    check(c, m, ["SET a=b c:d/e", "GET a=b", 'SET "q" \'v\'', 'GET "q"', "SET ~!@#$%^&*() []{}<>?",
                 "GET ~!@#$%^&*()", "SET SET GET", "GET SET", "SET COUNT QUIT", "GET COUNT", "COUNT"])


# ---------------- edge ----------------

@group("edge")
@cases((64, 1, "OK"), (65, 1, "ERROR"), (1, 64, "OK"), (1, 65, "ERROR"), (64, 64, "OK"), (100, 100, "ERROR"),
       title="Key {0} ký tự, value {1} ký tự → {2}")
def test_length_limits(ctx, klen, vlen, want):
    c = hello(ctx)
    k, v = "k" * klen, "v" * vlen
    c.send_line(f"SET {k} {v}")
    c.expect_line(want)
    c.send_line(f"GET {k}")
    c.expect_line(f"VALUE {v}" if want == "OK" else ("NOT_FOUND" if klen <= 64 else "ERROR"))


@group("edge")
@timeout(15)
def test_table_full_1000(ctx):
    """Đủ 1000 key: SET key mới → ERROR; ghi đè key cũ vẫn OK; DEL một key thì SET mới được"""
    c = hello(ctx)
    m = Model()
    check(c, m, [f"SET key{i} v{i}" for i in range(1000)], timeout=3)
    check(c, m, ["COUNT", "SET moi x", "SET key5 ghi_de", "GET key5", "COUNT", "DEL key0", "SET moi x",
                 "GET moi", "SET them y", "COUNT", "GET key999"])


@group("edge")
def test_extra_spaces(ctx):
    """Dấu cách thừa ở đầu, cuối, giữa các từ được bỏ qua"""
    c = hello(ctx)
    m = Model()
    check(c, m, ["SET  a  1", "  GET a", "GET a   ", " SET   b    2  ", "GET b", "  COUNT  ", "DEL   a ",
                 "COUNT"])


@group("edge")
def test_crlf(ctx):
    """Dòng kết thúc bằng \\r\\n"""
    c = hello(ctx)
    c.send("SET a 1\r\nGET a\r\nCOUNT\r\nDEL a\r\n\r\n")
    c.expect_lines(["OK", "VALUE 1", "COUNT 1", "OK", "ERROR"])
    c.send("QUIT\r\n")
    c.expect_line("BYE")


@group("edge")
def test_garbage_long_line(ctx):
    """Dòng rác dài 1000 byte → ERROR, kết nối vẫn dùng được"""
    c = hello(ctx)
    c.send_line("X" * 1000)
    c.expect_line("ERROR")
    c.send_line("SET " + "y" * 500 + " z")
    c.expect_line("ERROR")
    c.send_line("COUNT")
    c.expect_line("COUNT 0")


# ---------------- stream ----------------

@group("stream")
def test_fragmented_and_coalesced(ctx):
    """Lệnh bị cắt vụn và nhiều lệnh dính nhau"""
    c = hello(ctx)
    c.send_slowly("SET x 1\r\n", chunk=1, delay=0.01)
    c.expect_line("OK")
    c.send("SET y 2\nGET x\nGET y\r\nCOUNT\n")
    c.expect_lines(["OK", "VALUE 1", "VALUE 2", "COUNT 2"])


@group("stream")
def test_random_fragments_vs_model(ctx):
    """400 lệnh ngẫu nhiên cắt thành mảnh 1–30 byte, so với mô hình"""
    rng = ctx.rng
    c = hello(ctx)
    m = Model()
    cmds = [random_cmd(rng, 20) for _ in range(400)]
    c.send_chunks("".join(x + "\n" for x in cmds), rng, 1, 30, delay=0)
    for x in cmds:
        want = m.run(x)
        got = c.recv_line(timeout=2)
        if got != want:
            raise Fail(WA, f"lệnh {x!r} mong đợi {want!r}, nhận được {got!r}")


# ---------------- concurrency ----------------

@group("concurrency")
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


@group("concurrency")
@args("{port}", "8")
@timeout(20)
def test_multi_client_random_vs_model(ctx):
    """N=8: 8 client gửi 600 lệnh ngẫu nhiên xen kẽ lên cùng một bảng, so với mô hình"""
    rng = ctx.rng
    cs = [hello(ctx, f"C{i}") for i in range(8)]
    m = Model()
    with ctx.verdict(BLOCKED):
        for _ in range(600):
            c = rng.choice(cs)
            x = random_cmd(rng, 15)
            c.send_line(x)
            want = m.run(x)
            got = c.recv_line(timeout=1.5)
            if got != want:
                raise Fail(WA, f"{c.name}: lệnh {x!r} mong đợi {want!r}, nhận được {got!r}")


@group("concurrency")
@args("{port}", "10")
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


# ---------------- stress ----------------

@group("stress")
@timeout(20)
def test_5000_random_vs_model(ctx):
    """5000 lệnh ngẫu nhiên (key từ 1500 giá trị → chạm giới hạn 1000 key), so với mô hình"""
    rng = ctx.rng
    c = hello(ctx)
    m = Model()
    cmds = [random_cmd(rng, 1500, set_bias=0.6) for _ in range(5000)]
    for i in range(0, len(cmds), 250):
        check(c, m, cmds[i:i + 250], timeout=3)


def random_cmd(rng, keyspace, set_bias=0.35):
    k = f"k{rng.randrange(keyspace)}"
    r = rng.random()
    if r < set_bias:
        return f"SET {k} v{rng.randrange(10 ** 6)}"
    if r < set_bias + 0.3:
        return f"GET {k}"
    if r < set_bias + 0.45:
        return f"DEL {k}"
    if r < set_bias + 0.55:
        return "COUNT"
    return rng.choice(["", "SET", "GET a b", "DEL", "COUNT x", "set a b", f"SET {k}", "  COUNT  ", f"GET  {k}"])


globals().update(maxn_suite(ping=("GET __ping__", "NOT_FOUND")))
