# Thiết kế: docs/TEST-DESIGN.md. Phần "tối đa N client" dùng chung: judge/runner/suites.py (maxn_suite).
import time

import suite_fly as F
from njlib import BLOCKED, WA, Fail, cases, group, sample, timeout
from suites import maxn_suite

globals().update(maxn_suite(welcome="100 OK WELCOME", full="500 FULL", quit=("QUIT", "100 OK"), ping=("WHOAMI", None)))


def hello(ctx, name=None):
    c = ctx.connect(name=name)
    c.expect_line("100 OK WELCOME", timeout=1.5)
    return c


def parse_accounts(text):
    out = {}
    for ln in text.splitlines():
        w = ln.split(" ")
        if len(w) == 2:
            out[w[0]] = w[1]
    return out


class Model:
    """Mô hình chuẩn: bảng tài khoản + phiên (cid -> user đang đăng nhập)."""

    def __init__(self, accounts):
        self.acc = dict(accounts)
        self.order = list(accounts)
        self.cur = {}

    def run(self, cid, line):
        toks = F.split_line(line)
        name, a = toks[0], toks[1:]
        if name == "REGISTER":
            if not F.valid_account_args(a):
                return "201 INVALID"
            if a[0] in self.acc:
                return "200 USERNAME IN USE"
            self.acc[a[0]] = a[1]
            self.order.append(a[0])
            return "100 OK"
        if name == "LOGIN":
            if not F.valid_account_args(a):
                return "201 INVALID"
            if self.cur.get(cid):
                return "207 ALREADY LOGGED IN"
            if self.acc.get(a[0]) != a[1]:
                return "203 DENIED"
            if a[0] in self.cur.values():
                return "207 ALREADY LOGGED IN"
            self.cur[cid] = a[0]
            return f"100 OK {a[0]}"
        if name in ("LOGOUT", "WHOAMI", "QUIT") and a:
            return "201 INVALID"
        if name == "LOGOUT":
            if not self.cur.get(cid):
                return "204 LOGIN FIRST"
            del self.cur[cid]
            return "100 OK"
        if name == "WHOAMI":
            return f"100 OK {self.cur[cid]}" if self.cur.get(cid) else "204 LOGIN FIRST"
        if name == "QUIT":
            self.cur.pop(cid, None)
            return "100 OK"
        return "999 UNKNOWN ERROR"

    def drop(self, cid):
        self.cur.pop(cid, None)

    def file_text(self):
        return "".join(f"{u} {self.acc[u]}\n" for u in self.order)


def initial(ctx):
    return parse_accounts(ctx.read_file("accounts.txt"))


def ask(c, m, cid, line, timeout=2.0):
    want = m.run(cid, line)
    c.send_line(line)
    got = c.recv_line(timeout=timeout)
    if got != want:
        raise Fail(WA, f"{c.name}: lệnh {line!r}: mong đợi {want!r}, nhận được {got!r}")
    return want


def check_file(ctx, m):
    got = ctx.read_file("accounts.txt")
    want = m.file_text()
    if got != want:
        raise Fail(WA, f"accounts.txt sai.\nMong đợi:\n{want[-300:]!r}\nThực tế:\n{got[-300:]!r}")


def settle():
    time.sleep(0.06)


# ---------------- sample ----------------

@sample
def test_register_login_flow(ctx):
    """REGISTER rồi LOGIN, WHOAMI, LOGOUT"""
    m = Model(initial(ctx))
    c = hello(ctx)
    for line in ["WHOAMI", "REGISTER hoa mk1234", "LOGIN hoa mk1234", "WHOAMI", "LOGOUT", "WHOAMI", "LOGIN hoa mk1234"]:
        ask(c, m, 1, line)
    check_file(ctx, m)


@sample
def test_login_errors(ctx):
    """Sai mật khẩu / tên → 203; sai cú pháp → 201; đã đăng nhập → 207"""
    m = Model(initial(ctx))
    c = hello(ctx)
    for line in ["LOGIN an 12345", "LOGIN nobody 1234", "LOGIN AN 1234", "LOGIN an 1", "LOGIN an", "LOGIN an 1234",
                 "LOGIN an 1234", "LOGIN binh abcd"]:
        ask(c, m, 1, line)


@sample
def test_one_session_per_account(ctx):
    """Một tài khoản chỉ đăng nhập ở một phiên; REGISTER trùng → 200"""
    m = Model(initial(ctx))
    a, b = hello(ctx, "A"), hello(ctx, "B")
    for c, cid, line in [(a, 1, "LOGIN an 1234"), (b, 2, "LOGIN an 1234"), (b, 2, "REGISTER an 9999"),
                         (b, 2, "REGISTER hoa mk1234"), (a, 1, "QUIT")]:
        ask(c, m, cid, line)
    a.expect_closed()
    settle()
    ask(b, m, 2, "LOGIN an 1234")


# ---------------- basic ----------------

@group("basic")
def test_initial_accounts_all_login(ctx):
    """Mọi tài khoản có sẵn trong accounts.txt đều đăng nhập được (mỗi phiên một lần)"""
    acc = initial(ctx)
    m = Model(acc)
    c = hello(ctx)
    for u, p in acc.items():
        ask(c, m, 1, f"LOGIN {u} {p}")
        ask(c, m, 1, "WHOAMI")
        ask(c, m, 1, "LOGOUT")


@group("basic")
def test_register_appends_exact_lines(ctx):
    """REGISTER ghi đúng 'user pass\\n' vào cuối accounts.txt, theo thứ tự đăng ký, ngay lập tức"""
    m = Model(initial(ctx))
    c = hello(ctx)
    for line in ["REGISTER hoa mk1234", "REGISTER lan p@ss~!", "REGISTER hoa khac1234", "REGISTER an zzzz", "REGISTER x9 9999"]:
        ask(c, m, 1, line)
        check_file(ctx, m)


@group("basic")
def test_registered_account_usable_from_other_connection(ctx):
    """Tài khoản vừa đăng ký ở phiên A đăng nhập được ở phiên B ngay"""
    m = Model(initial(ctx))
    a, b = hello(ctx, "A"), hello(ctx, "B")
    ask(a, m, 1, "REGISTER hoa mk1234")
    ask(b, m, 2, "LOGIN hoa mk1234")
    ask(a, m, 1, "LOGIN hoa mk1234")


@group("basic")
def test_register_does_not_login(ctx):
    """REGISTER không tự đăng nhập; được REGISTER khi đang đăng nhập"""
    m = Model(initial(ctx))
    c = hello(ctx)
    for line in ["REGISTER hoa mk1234", "WHOAMI", "LOGIN an 1234", "REGISTER lan mk1234", "WHOAMI", "LOGIN hoa mk1234"]:
        ask(c, m, 1, line)


@group("basic")
def test_session_state_is_per_connection(ctx):
    """Trạng thái đăng nhập của phiên này không lộ sang phiên khác"""
    m = Model(initial(ctx))
    a, b = hello(ctx, "A"), hello(ctx, "B")
    ask(a, m, 1, "LOGIN an 1234")
    ask(b, m, 2, "WHOAMI")
    ask(b, m, 2, "LOGOUT")
    ask(a, m, 1, "WHOAMI")
    ask(b, m, 2, "LOGIN binh abcd")
    ask(a, m, 1, "WHOAMI")
    ask(b, m, 2, "WHOAMI")


@group("basic")
def test_logout_frees_account(ctx):
    """LOGOUT trả tài khoản cho phiên khác"""
    m = Model(initial(ctx))
    a, b = hello(ctx, "A"), hello(ctx, "B")
    for c, cid, line in [(a, 1, "LOGIN an 1234"), (b, 2, "LOGIN an 1234"), (a, 1, "LOGOUT"), (b, 2, "LOGIN an 1234"),
                         (a, 1, "LOGIN an 1234"), (a, 1, "LOGIN binh abcd")]:
        ask(c, m, cid, line)


@group("basic")
@cases("close", "rst", "quit", title="Phiên đóng bằng {0}: tài khoản được giải phóng")
def test_disconnect_frees_account(ctx, how):
    m = Model(initial(ctx))
    a = hello(ctx, "A")
    ask(a, m, 1, "LOGIN an 1234")
    if how == "quit":
        ask(a, m, 1, "QUIT")
        a.expect_closed()
    elif how == "close":
        a.close()
        m.drop(1)
    else:
        a.reset()
        m.drop(1)
    settle()
    b = hello(ctx, "B")
    ask(b, m, 2, "LOGIN an 1234")


@group("basic")
@cases("login an 1234", "Login an 1234", "register hoa mk1234", "PING", "", " ", "\t", "LOGINN an 1234", "WHO", "whoami", "LOGOUT2",
       "HELLO", "SEARCH HAN SGN 2026-12-20 1 ECO", "BOOK VN213", title="Lệnh lạ {0!r} → 999")
def test_unknown_commands(ctx, line):
    m = Model(initial(ctx))
    c = hello(ctx)
    ask(c, m, 1, line)
    ask(c, m, 1, "LOGIN an 1234")


@group("basic")
@cases("LOGOUT now", "WHOAMI x", "QUIT now", "LOGOUT ", "WHOAMI  ", title="Lệnh {0!r} kèm tham số → 201")
def test_args_not_allowed(ctx, line):
    m = Model(initial(ctx))
    c = hello(ctx)
    ask(c, m, 1, "LOGIN an 1234")
    ask(c, m, 1, line)
    ask(c, m, 1, "WHOAMI")


# ---------------- edge ----------------

@group("edge")
@cases(("a", 4), ("a" * 32, 32), ("a" * 33, 4), ("", 4), ("A", 4), ("a_b", 4), ("a b", 4), ("\xc3\xa9", 4), ("0", 4), ("9" * 32, 4),
       title="REGISTER tên {0!r:.40} (mk {1} ký tự)")
def test_register_user_rules(ctx, user, plen):
    m = Model(initial(ctx))
    c = hello(ctx)
    ask(c, m, 1, f"REGISTER {user} {'p' * plen}")
    ask(c, m, 1, f"LOGIN {user} {'p' * plen}")
    check_file(ctx, m)


@group("edge")
@cases(("pppp",), ("p" * 32,), ("ppp",), ("p" * 33,), ("~~~~",), ("!!!!",), ("a\x7fbc",), ("a\x01bc",), ("a\tbc",),
       title="REGISTER mật khẩu {0!r:.40}")
def test_register_pass_rules(ctx, pw):
    m = Model(initial(ctx))
    c = hello(ctx)
    ask(c, m, 1, f"REGISTER hoa {pw}")
    ask(c, m, 1, f"LOGIN hoa {pw}")
    check_file(ctx, m)


@group("edge")
def test_rejected_register_writes_nothing(ctx):
    """REGISTER bị từ chối (201/200) không ghi gì vào accounts.txt"""
    before = ctx.read_file("accounts.txt")
    m = Model(initial(ctx))
    c = hello(ctx)
    for line in ["REGISTER an 9999", "REGISTER", "REGISTER x", "REGISTER x 1", "REGISTER X abcd", "REGISTER x  abcd",
                 "REGISTER x abcd y", "register x abcd", "REGISTER " + "a" * 40 + " abcd", "REGISTER binh abcd"]:
        ask(c, m, 1, line)
    if ctx.read_file("accounts.txt") != before:
        raise Fail(WA, "accounts.txt bị thay đổi dù không có REGISTER hợp lệ nào")


@group("edge")
def test_password_is_case_and_exact(ctx):
    """Mật khẩu và tên phân biệt hoa thường; không khớp tiền tố/hậu tố"""
    m = Model(initial(ctx))
    c = hello(ctx)
    for line in ["LOGIN an 123", "LOGIN an 12345", "LOGIN an 1234x", "LOGIN a 1234", "LOGIN ann 1234", "LOGIN chi P@ssw0rd",
                 "LOGIN chi p@ssw0rd"]:
        ask(c, m, 1, line)


# ---------------- stream ----------------

@group("stream")
def test_byte_by_byte(ctx):
    """Gửi từng byte một"""
    m = Model(initial(ctx))
    c = hello(ctx)
    for line in ["REGISTER hoa mk1234", "LOGIN hoa mk1234", "WHOAMI"]:
        want = m.run(1, line)
        c.send_slowly(line + "\n", chunk=1, delay=0.001)
        c.expect_line(want)
    check_file(ctx, m)


@group("stream")
def test_many_commands_one_send(ctx):
    """Hàng chục lệnh dính nhau trong một lần gửi"""
    m = Model(initial(ctx))
    c = hello(ctx)
    lines = ["REGISTER hoa mk1234", "LOGIN hoa mk1234", "WHOAMI", "LOGOUT", "REGISTER lan abcd1", "LOGIN lan abcd1", "WHOAMI"] * 5
    c.send("".join(x + "\n" for x in lines))
    for line in lines:
        c.expect_line(m.run(1, line))
    check_file(ctx, m)


@group("stream")
def test_crlf(ctx):
    """Dòng kết thúc bằng \\r\\n"""
    m = Model(initial(ctx))
    c = hello(ctx)
    for line in ["REGISTER hoa mk1234", "LOGIN hoa mk1234", "WHOAMI", "", "LOGOUT"]:
        c.send(line + "\r\n")
        c.expect_line(m.run(1, line))
    check_file(ctx, m)


@group("stream")
def test_random_chunks(ctx):
    """Cắt ngẫu nhiên 1–7 byte"""
    m = Model(initial(ctx))
    c = hello(ctx)
    for line in ["REGISTER hoa mk1234", "LOGIN hoa mk1234", "WHOAMI", "LOGOUT", "LOGIN an 1234", "QUIT x", "REGISTER an a"]:
        want = m.run(1, line)
        c.send_chunks(line + "\n", ctx.rng, delay=0)
        c.expect_line(want, timeout=2.0)


@group("stream")
def test_quit_in_middle_of_batch(ctx):
    """Sau QUIT các lệnh dính phía sau bị bỏ, kể cả REGISTER"""
    before = ctx.read_file("accounts.txt")
    c = hello(ctx)
    c.send("WHOAMI\nQUIT\nREGISTER hoa mk1234\nWHOAMI\n")
    c.expect_line("204 LOGIN FIRST")
    c.expect_line("100 OK")
    c.expect_closed(timeout=1.5)
    time.sleep(0.1)
    if ctx.read_file("accounts.txt") != before:
        raise Fail(WA, "REGISTER sau QUIT vẫn được thực hiện")


# ---------------- robust ----------------

@group("robust")
def test_binary_garbage(ctx):
    """Byte lạ không làm hỏng server hay accounts.txt"""
    before = ctx.read_file("accounts.txt")
    c = hello(ctx)
    for junk in [b"\x01\x02", b"LOGIN \xff\xfe \xfd\xfc", b"REGISTER \x80 \x81\x82\x83\x84", b"\x7f", b"REGISTER hoa \xc3\xa9\xc3\xa9"]:
        c.send(junk + b"\n")
        got = c.recv_line()
        if got not in ("201 INVALID", "999 UNKNOWN ERROR"):
            raise Fail(WA, f"byte lạ {junk!r}: nhận được {got!r}")
    c.send_line("LOGIN an 1234")
    c.expect_line("100 OK an")
    if ctx.read_file("accounts.txt") != before:
        raise Fail(WA, "accounts.txt bị thay đổi")


@group("robust")
@timeout(20)
def test_register_200_accounts(ctx):
    """Đăng ký 200 tài khoản rồi đăng nhập lại từng cái; accounts.txt đúng thứ tự"""
    m = Model(initial(ctx))
    c = hello(ctx)
    for i in range(200):
        ask(c, m, 1, f"REGISTER u{i:03d} pw{i:03d}")
    check_file(ctx, m)
    d = hello(ctx, "D")
    for i in range(200):
        ask(d, m, 2, f"LOGIN u{i:03d} pw{i:03d}")
        ask(d, m, 2, "LOGOUT")


@group("robust")
@timeout(20)
def test_connect_disconnect_300_with_login(ctx):
    """300 lượt kết nối có đăng nhập rồi đóng/RST: không rò fd, tài khoản luôn được giải phóng"""
    for i in range(300):
        c = hello(ctx, f"c{i}")
        c.send_line("LOGIN an 1234")
        c.expect_line("100 OK an")
        if i % 2:
            c.reset()
        else:
            c.close()
        ctx.close_quietly(c)
        time.sleep(0.004)
    settle()
    m = Model(initial(ctx))
    ask(hello(ctx, "last"), m, 1, "LOGIN an 1234")


@group("robust")
def test_client_dies_mid_register(ctx):
    """Client gửi dở REGISTER rồi RST: không ghi gì, server vẫn sống"""
    before = ctx.read_file("accounts.txt")
    c = hello(ctx)
    c.send("REGISTER hoa mk12")
    c.reset()
    settle()
    ctx.expect_alive()
    d = hello(ctx, "D")
    d.send_line("WHOAMI")
    d.expect_line("204 LOGIN FIRST")
    if ctx.read_file("accounts.txt") != before:
        raise Fail(WA, "lệnh REGISTER dở dang vẫn được ghi")


# ---------------- concurrency ----------------

@group("concurrency")
@timeout(15)
def test_race_register_same_name(ctx):
    """20 client cùng REGISTER một tên: đúng một người 100 OK, accounts.txt có đúng một dòng mới"""
    cs = [hello(ctx, f"c{i}") for i in range(9)]
    for c in cs:
        c.send_line("REGISTER dua mk1234")
    oks = 0
    for c in cs:
        got = c.recv_line(timeout=2.0)
        if got == "100 OK":
            oks += 1
        elif got != "200 USERNAME IN USE":
            raise Fail(WA, f"{c.name}: nhận {got!r}")
    if oks != 1:
        raise Fail(WA, f"{oks} client đăng ký thành công cùng một tên")
    lines = [ln for ln in ctx.read_file("accounts.txt").splitlines() if ln.startswith("dua ")]
    if lines != ["dua mk1234"]:
        raise Fail(WA, f"accounts.txt có {lines!r}")


@group("concurrency")
@timeout(15)
def test_race_login_same_account(ctx):
    """9 client cùng LOGIN một tài khoản: đúng một người 100 OK, còn lại 207"""
    cs = [hello(ctx, f"c{i}") for i in range(9)]
    for c in cs:
        c.send_line("LOGIN an 1234")
    oks = 0
    for c in cs:
        got = c.recv_line(timeout=2.0)
        if got == "100 OK an":
            oks += 1
        elif got != "207 ALREADY LOGGED IN":
            raise Fail(WA, f"{c.name}: nhận {got!r}")
    if oks != 1:
        raise Fail(WA, f"{oks} phiên cùng đăng nhập một tài khoản")


@group("concurrency")
def test_idle_client_does_not_block(ctx):
    """Client im lặng/gửi dở lệnh không chặn client khác"""
    m = Model(initial(ctx))
    idle = [hello(ctx, f"idle{i}") for i in range(4)]
    idle[0].send("REGISTER ho")
    with ctx.verdict(BLOCKED):
        ask(hello(ctx, "active"), m, 9, "LOGIN an 1234")
    idle[0].send("a mk1234\n")
    idle[0].expect_line("100 OK")


# ---------------- stress ----------------

@group("stress")
@timeout(30)
def test_random_ops_vs_model(ctx):
    """600 thao tác ngẫu nhiên của 4 phiên (đăng ký, đăng nhập, rời đi, nối lại) so với mô hình; kiểm tra accounts.txt"""
    rng = ctx.rng
    acc0 = initial(ctx)
    m = Model(acc0)
    users = list(acc0) + [f"u{i}" for i in range(15)]
    conns = {}
    nxt = [0]

    def open_conn():
        nxt[0] += 1
        cid = nxt[0]
        conns[cid] = hello(ctx, f"s{cid}")
        return cid

    for _ in range(4):
        open_conn()
    for step in range(600):
        cid = rng.choice(list(conns))
        c = conns[cid]
        r = rng.random()
        u = rng.choice(users)
        pw = m.acc.get(u, "") if rng.random() < 0.7 else rng.choice(["wrongpw", "abcd", "1234"])
        if r < 0.25:
            line = f"LOGIN {u} {pw or 'abcd1'}"
        elif r < 0.45:
            line = f"REGISTER {u} {pw if len(pw) >= 4 else 'pass1'}"
        elif r < 0.6:
            line = "WHOAMI"
        elif r < 0.72:
            line = "LOGOUT"
        elif r < 0.78:
            line = rng.choice(["PING", "", "LOGIN", "LOGIN a", "REGISTER x", "WHOAMI 1", "login an 1234", "REGISTER  hoa abcd"])
        elif r < 0.9:
            ask(c, m, cid, "QUIT")
            c.expect_closed(timeout=1.5)
            del conns[cid]
            open_conn()
            settle()
            continue
        else:
            c.reset()
            m.drop(cid)
            del conns[cid]
            settle()
            open_conn()
            continue
        ask(c, m, cid, line)
    check_file(ctx, m)
