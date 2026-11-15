from njlib import sample


def ask(u, req, want):
    u.send(req)
    u.expect(want)


@sample
def test_basic_ops(ctx):
    """Năm phép toán cơ bản"""
    u = ctx.udp()
    for req, want in [("12 + 30", "42"), ("5 - 9", "-4"), ("6 * 7", "42"), ("-7 / 2", "-3"), ("-7 % 3", "-1")]:
        ask(u, req, want)


@sample
def test_errors(ctx):
    """Chia cho 0 và sai cú pháp"""
    u = ctx.udp()
    ask(u, "5 % 0", "ERROR div0")
    ask(u, "5 / 0", "ERROR div0")
    for bad in ["5+3", "5 + ", "+ 5 3", "5 ^ 3", "abc + 1", "1 + 2 + 3", "5  + 3", "", "1.5 + 2", "count",
                "99999999999999999999 + 1"]:
        ask(u, bad, "ERROR syntax")


def test_big_numbers(ctx):
    """Số 64 bit"""
    u = ctx.udp()
    ask(u, "9223372036854775807 - 1", "9223372036854775806")
    ask(u, "-9223372036854775807 - 1", "-9223372036854775808")
    ask(u, "3000000000 * 3", "9000000000")


def test_count_per_sender(ctx):
    """COUNT đếm riêng cho từng người gửi, không tính phép lỗi"""
    a, b = ctx.udp("A"), ctx.udp("B")
    ask(a, "COUNT", "0")
    ask(a, "1 + 1", "2")
    ask(b, "2 * 2", "4")
    ask(a, "1 / 0", "ERROR div0")
    ask(a, "x", "ERROR syntax")
    ask(a, "3 - 1", "2")
    ask(a, "COUNT", "2")
    ask(b, "COUNT", "1")


def test_interleaved_many(ctx):
    """50 người gửi xen kẽ, mỗi người nhận đúng kết quả của mình"""
    us = [ctx.udp(f"U{i}") for i in range(50)]
    for i, u in enumerate(us):
        u.send(f"{i} * {i}")
    for i, u in enumerate(us):
        u.expect(str(i * i))
    for i, u in enumerate(us):
        ask(u, "COUNT", "1")
