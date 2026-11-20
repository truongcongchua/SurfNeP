# Thiết kế: docs/TEST-DESIGN.md
import re

from njlib import WA, Fail, cases, group, sample, timeout

INT_RE = re.compile(r"^-?[0-9]+$")
LO, HI = -(1 << 63), (1 << 63) - 1


class Model:
    """Mô hình chuẩn (phép chia/lấy dư làm tròn về 0 như C)."""

    def __init__(self):
        self.count = 0

    def run(self, req):
        if req == "COUNT":
            return str(self.count)
        parts = req.split(" ")
        if len(parts) != 3 or len(parts[1]) != 1 or parts[1] not in "+-*/%":
            return "ERROR syntax"
        a, op, b = parts
        if not (INT_RE.match(a) and INT_RE.match(b)):
            return "ERROR syntax"
        x, y = int(a), int(b)
        if not (LO <= x <= HI and LO <= y <= HI):
            return "ERROR syntax"
        if op in "/%" and y == 0:
            return "ERROR div0"
        if op == "+":
            r = x + y
        elif op == "-":
            r = x - y
        elif op == "*":
            r = x * y
        else:
            q = abs(x) // abs(y)
            q = q if (x >= 0) == (y >= 0) else -q
            r = q if op == "/" else x - y * q
        self.count += 1
        return str(r)


def ask(u, req, want):
    u.send(req)
    u.expect(want)


def check(u, model, reqs):
    for r in reqs:
        want = model.run(r)
        u.send(r)
        got = u.recv(timeout=1.0).decode(errors="replace")
        if got != want:
            raise Fail(WA, f"yêu cầu {r!r}: mong đợi {want!r}, nhận được {got!r}")


@sample
def test_basic_ops(ctx):
    """Năm phép toán cơ bản"""
    u = ctx.udp()
    for req, want in [("12 + 30", "42"), ("5 - 9", "-4"), ("6 * 7", "42"), ("-7 / 2", "-3"), ("-7 % 3", "-1")]:
        ask(u, req, want)


@sample
def test_errors_and_count(ctx):
    """ERROR div0 / ERROR syntax và COUNT chỉ đếm phép tính thành công"""
    u = ctx.udp()
    m = Model()
    check(u, m, ["1 + 1", "5 % 0", "5+3", "COUNT", "2 * 3", "COUNT"])


@group("basic")
@cases(("7 / 2", "3"), ("-7 / 2", "-3"), ("7 / -2", "-3"), ("-7 / -2", "3"), ("7 % 3", "1"), ("-7 % 3", "-1"),
       ("7 % -3", "1"), ("-7 % -3", "-1"), ("0 / 5", "0"), ("0 % 5", "0"), ("-1 / 2", "0"), ("-1 % 2", "-1"),
       title="Chia/lấy dư làm tròn về 0: {0!r} → {1}")
def test_c_division(ctx, req, want):
    ask(ctx.udp(), req, want)


@group("edge")
@cases("9223372036854775807 + 0", "-9223372036854775808 + 0", "-9223372036854775808 / 2",
       "9223372036854775807 % 10", "4611686018427387904 * 1", "-0 + 0", "007 * 3", "-000 - 5",
       title="Biên 64 bit / dạng số lạ hợp lệ: {0!r}")
def test_int64_edges(ctx, req):
    check(ctx.udp(), Model(), [req])


@group("edge")
@cases("9223372036854775808 + 1", "1 + -9223372036854775809", "99999999999999999999 * 2", "+5 + 1", "5 + +1",
       "--5 + 1", "0x10 + 1", "1e3 + 1", "1.5 + 1", "5 ^ 2", "5 ** 2", "5 // 2", "5  + 3", " 5 + 3", "5 + 3 ",
       "5 +", "+ 5", "5", "", "COUNT ", " COUNT", "count", "5\t+\t3", "5 + 3 + 1", "a + b", "- + -", "5 - -",
       title="Yêu cầu sai {0!r} → ERROR syntax")
def test_syntax_errors(ctx, req):
    ask(ctx.udp(), req, "ERROR syntax")


@group("edge")
@cases("5 / 0", "5 % 0", "-5 / -0", "0 / 0", "0 % 000", title="Chia cho 0: {0!r} → ERROR div0")
def test_div_zero(ctx, req):
    u = ctx.udp()
    ask(u, req, "ERROR div0")
    ask(u, "COUNT", "0")


@group("edge")
def test_long_datagram(ctx):
    """Datagram rất dài (2000 chữ số) → ERROR syntax, server vẫn chạy"""
    u = ctx.udp()
    ask(u, "1 + " + "9" * 2000, "ERROR syntax")
    ask(u, "1" * 900 + " + 1", "ERROR syntax")
    ask(u, "2 + 2", "4")


@group("basic")
def test_count_per_sender(ctx):
    """COUNT đếm riêng từng người gửi (cùng IP, khác cổng)"""
    a, b = ctx.udp("A"), ctx.udp("B")
    ma, mb = Model(), Model()
    check(a, ma, ["1 + 1", "2 + 2", "x"])
    check(b, mb, ["COUNT", "3 * 3", "COUNT"])
    check(a, ma, ["COUNT"])


@group("concurrency")
def test_many_senders_random(ctx):
    """100 người gửi, mỗi người 5 yêu cầu ngẫu nhiên xen kẽ: COUNT của từng người đúng"""
    rng = ctx.rng
    us = [ctx.udp(f"U{i}") for i in range(100)]
    ms = [Model() for _ in us]
    for _ in range(5):
        for u, m in zip(us, ms):
            check(u, m, [random_req(rng)])
    for u, m in zip(us, ms):
        check(u, m, ["COUNT"])


@group("stress")
@timeout(15)
def test_2000_random_vs_model(ctx):
    """2000 yêu cầu ngẫu nhiên (đúng, sai, biên) so với mô hình"""
    rng = ctx.rng
    u = ctx.udp()
    m = Model()
    check(u, m, [random_req(rng) for _ in range(2000)] + ["COUNT"])


def random_req(rng):
    r = rng.random()
    if r < 0.05:
        return "COUNT"
    if r < 0.75:
        a = rng.choice([rng.randint(-1000, 1000), rng.randint(-10 ** 9, 10 ** 9), 0, 1, -1])
        b = rng.choice([rng.randint(-1000, 1000), rng.randint(1, 50), 0, -1])
        op = rng.choice("+-*/%")
        return f"{a} {op} {b}"
    return rng.choice(["5+3", "5 + ", "+1 + 2", "1 + 2 ", "a * 2", "1 & 2", "", " ", "COUNT 1", "--1 - 1",
                       "1 - --1", "92233720368547758070 + 1"])
