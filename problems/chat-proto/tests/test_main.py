# Thiết kế: docs/TEST-DESIGN.md. Mô hình phòng chat độc lập với lời giải.
import re
import time

from njlib import BLOCKED, WA, Fail, cases, group, sample, timeout

NICK_RE = re.compile(r"^[a-z0-9]{1,32}$", re.ASCII)


class Chat:
    """Mô hình: nick[i] là tên của client thứ i (None nếu chưa JOIN)."""

    def __init__(self, n):
        self.nick = [None] * n

    def run(self, i, line):
        """Trả về danh sách (người nhận, dòng) theo thứ tự gửi; người nhận cuối cùng là phản hồi cho i."""
        cmd, sp, arg = line.partition(" ")
        if cmd == "QUIT" and not sp:
            self.nick[i] = None
            return [(i, "100 OK")]
        if cmd == "JOIN" and sp:
            if self.nick[i] is not None:
                return [(i, "203 DENIED")]
            if not NICK_RE.match(arg):
                return [(i, "201 INVALID NICK NAME")]
            if arg in self.nick:
                return [(i, "200 NICKNAME IN USE")]
            self.nick[i] = arg
            return [(i, "100 OK")]
        if cmd == "MSG" and sp and arg:
            if self.nick[i] is None:
                return [(i, "203 DENIED")]
            out = [(j, f"[{self.nick[i]}]: {arg}") for j in range(len(self.nick)) if j != i and self.nick[j] is not None]
            return out + [(i, "100 OK")]
        if cmd == "PMSG" and sp:
            to, sp2, text = arg.partition(" ")
            if sp2 and text:
                if self.nick[i] is None:
                    return [(i, "203 DENIED")]
                for j in range(len(self.nick)):
                    if j != i and self.nick[j] == to:
                        return [(j, f"[{self.nick[i]}] (private): {text}"), (i, "100 OK")]
                return [(i, "202 UNKNOWN NICKNAME")]
        return [(i, "999 UNKNOWN ERROR")]


def make(ctx, n, join=True):
    cs = [ctx.connect(name=f"c{i}") for i in range(n)]
    m = Chat(n)
    if join:
        for i, c in enumerate(cs):
            step(cs, m, i, f"JOIN u{i}")
    return cs, m


def step(cs, m, i, line, silence=0.0):
    """Client i gửi `line`; mọi client nhận đúng các dòng mô hình dự đoán (và không dòng nào khác nếu silence > 0)."""
    exp = m.run(i, line)
    cs[i].send(line + "\n" if isinstance(line, str) else line + b"\n")
    per = {}
    for j, ln in exp:
        per.setdefault(j, []).append(ln)
    for j, lines in per.items():
        for ln in lines:
            got = cs[j].recv_line(timeout=2.0)
            if got != ln:
                raise Fail(WA, f"{cs[j].name} (sau lệnh {line!r} của c{i}): mong đợi {ln!r}, nhận {got!r}")
    if silence:
        for j, c in enumerate(cs):
            if j not in per and c.sock.fileno() >= 0:
                c.expect_silence(silence)
    return exp


# ---------------- sample ----------------

@sample
def test_join_rules(ctx):
    """JOIN: 100 OK; sai quy cách 201; tên đã dùng 200; JOIN lần hai 203"""
    cs, m = make(ctx, 3, join=False)
    for i, line in [(0, "JOIN an"), (0, "JOIN an"), (1, "JOIN An"), (1, "JOIN binh"), (2, "JOIN an"), (2, "JOIN binh"), (2, "JOIN chi")]:
        step(cs, m, i, line)


@sample
def test_msg_broadcast_not_to_sender(ctx):
    """MSG tới mọi người khác đã JOIN, không gửi lại cho người gửi, không gửi cho người chưa JOIN"""
    cs, m = make(ctx, 3, join=False)
    for i, line in [(0, "JOIN an"), (1, "JOIN binh"), (0, "MSG xin chao moi nguoi"), (2, "MSG hi"), (1, "MSG tra loi")]:
        step(cs, m, i, line, silence=0.05)


@sample
def test_pmsg_private(ctx):
    """PMSG chỉ tới đúng người nhận; không có người đó → 202"""
    cs, m = make(ctx, 3)
    for i, line in [(1, "PMSG u0 chao ban"), (1, "PMSG ai-do hi"), (1, "PMSG u1 tu nhan"), (0, "PMSG u2 hello"), (2, "PMSG u0 ok")]:
        step(cs, m, i, line, silence=0.05)


# ---------------- basic ----------------

@group("basic")
@cases(("a", True), ("0", True), ("an123", True), ("z" * 32, True), ("a" * 33, False), ("", False), ("An", False), ("a_b", False),
       ("a-b", False), ("a b", False), ("a.b", False), ("\xe9", False), ("ab\tc", False), ("1" * 32, True), ("A", False),
       title="Tên {0!r:.40} hợp lệ: {1}")
def test_nick_rules(ctx, nick, ok):
    cs, m = make(ctx, 1, join=False)
    exp = step(cs, m, 0, "JOIN " + nick)
    if (exp[0][1] == "100 OK") != ok:
        raise Fail(WA, "mô hình nội bộ lệch")


@group("basic")
def test_unjoined_cannot_talk(ctx):
    """Chưa JOIN: MSG / PMSG → 203, và không ai nhận được gì"""
    cs, m = make(ctx, 3, join=False)
    step(cs, m, 1, "JOIN binh")
    for line in ["MSG hi", "PMSG binh hi", "PMSG nobody hi"]:
        step(cs, m, 0, line, silence=0.05)


@group("basic")
def test_check_order_pmsg(ctx):
    """PMSG: cú pháp (999) trước, rồi đã JOIN (203), rồi người nhận (202)"""
    cs, m = make(ctx, 2, join=False)
    for line in ["PMSG", "PMSG x", "PMSG x ", "PMSG  hi", "PMSG x hi"]:
        step(cs, m, 0, line)
    step(cs, m, 0, "JOIN an")
    for line in ["PMSG", "PMSG x", "PMSG x ", "PMSG  hi", "PMSG x hi", "PMSG an hi"]:
        step(cs, m, 0, line)


@group("basic")
@cases("MSG", "MSG ", "PMSG", "JOIN", "QUIT now", "quit", "msg hi", "Msg hi", "LOGIN an", "", " ", "HELLO world", "MSGS hi", "JOINX an",
       title="Lệnh {0!r} → 999 UNKNOWN ERROR")
def test_unknown_commands(ctx, line):
    cs, m = make(ctx, 2)
    step(cs, m, 0, line, silence=0.05)
    step(cs, m, 0, "MSG van song")


@group("basic")
def test_text_is_verbatim(ctx):
    """Phần sau dấu cách đầu tiên được giữ nguyên (dấu cách thừa, nháy, byte lạ)"""
    cs, m = make(ctx, 2)
    for text in ["a  b", " dau cach", "cuoi cach ", '"quoted"', "[x]: y", "tab\there", "\xc3\xa9\xc3\xa9", "  ", "MSG MSG"]:
        step(cs, m, 0, "MSG " + text)
        step(cs, m, 1, "PMSG u0 " + text)


@group("basic")
def test_name_freed_on_leave(ctx):
    """Tên được giải phóng khi client QUIT, đóng, hay RST"""
    cs, m = make(ctx, 4, join=False)
    for i in range(3):
        step(cs, m, i, f"JOIN n{i}")
    step(cs, m, 0, "QUIT")
    cs[0].expect_closed()
    cs[1].close()
    m.nick[1] = None
    cs[2].reset()
    m.nick[2] = None
    time.sleep(0.3)
    for name in ["n0", "n1", "n2"]:
        step(cs, m, 3, f"JOIN {name}")
        m.nick[3] = None
        cs[3].send("QUIT\n")
        cs[3].expect_line("100 OK")
        cs[3].expect_closed()
        cs[3] = ctx.connect(name="c3")


@group("basic")
def test_quit_does_not_notify(ctx):
    """QUIT chỉ trả 100 OK cho người đó; người khác không nhận gì"""
    cs, m = make(ctx, 3)
    step(cs, m, 1, "QUIT", silence=0.1)


# ---------------- edge ----------------

@group("edge")
@cases(1, 100, 500, 900, title="Tin dài {0} byte")
def test_long_message(ctx, n):
    cs, m = make(ctx, 2)
    step(cs, m, 0, "MSG " + "x" * n)
    step(cs, m, 1, "PMSG u0 " + "y" * n)


@group("edge")
def test_pmsg_to_self_is_unknown(ctx):
    """PMSG cho chính mình → 202"""
    cs, m = make(ctx, 2)
    step(cs, m, 0, "PMSG u0 hi", silence=0.05)


@group("edge")
def test_same_name_after_other_leaves_mid_chat(ctx):
    """Tên được dùng lại ngay và tin nhắn đi tới người mới, không tới người cũ"""
    cs, m = make(ctx, 3)
    step(cs, m, 0, "QUIT")
    cs[0].expect_closed()
    cs[0] = ctx.connect(name="c0b")
    step(cs, m, 0, "JOIN u0")
    step(cs, m, 1, "PMSG u0 chao nguoi moi")
    step(cs, m, 2, "MSG ca phong nghe")


# ---------------- stream ----------------

@group("stream")
def test_byte_by_byte(ctx):
    """Gửi từng byte một"""
    cs, m = make(ctx, 2, join=False)
    for i, line in [(0, "JOIN an"), (1, "JOIN binh"), (0, "MSG tung byte mot"), (1, "PMSG an rieng tu")]:
        exp = m.run(i, line)
        cs[i].send_slowly(line + "\n", chunk=1, delay=0.001)
        for j, ln in exp:
            cs[j].expect_line(ln, timeout=2.0)


@group("stream")
def test_many_commands_one_send(ctx):
    """Hàng chục lệnh dính nhau trong một lần gửi"""
    cs, m = make(ctx, 3, join=False)
    for i in range(3):
        step(cs, m, i, f"JOIN u{i}")
    lines = [f"MSG tin {k}" for k in range(20)] + [f"PMSG u2 rieng {k}" for k in range(20)]
    cs[0].send("".join(x + "\n" for x in lines))
    for ln in [f"[u0]: tin {k}" for k in range(20)]:
        cs[1].expect_line(ln)
    for k in range(20):
        cs[2].expect_line(f"[u0]: tin {k}")
    for k in range(20):
        cs[2].expect_line(f"[u0] (private): rieng {k}")
    for _ in range(40):
        cs[0].expect_line("100 OK")


@group("stream")
def test_crlf_and_chunks(ctx):
    """\\r\\n và cắt ngẫu nhiên 1–7 byte"""
    cs, m = make(ctx, 2, join=False)
    for i, line in [(0, "JOIN an"), (1, "JOIN binh"), (0, "MSG xin chao"), (1, "PMSG an rieng"), (0, "PING")]:
        exp = m.run(i, line)
        if ctx.rng.random() < 0.5:
            cs[i].send(line + "\r\n")
        else:
            cs[i].send_chunks(line + "\n", ctx.rng, delay=0)
        for j, ln in exp:
            cs[j].expect_line(ln, timeout=2.0)


@group("stream")
def test_split_command_across_sends(ctx):
    """Lệnh MSG bị cắt giữa chừng; người nhận chỉ thấy tin khi đủ dòng"""
    cs, m = make(ctx, 2)
    cs[0].send("MSG nua ")
    time.sleep(0.1)
    cs[1].expect_silence(0.15)
    cs[0].send("con lai\n")
    cs[1].expect_line("[u0]: nua con lai")
    cs[0].expect_line("100 OK")


# ---------------- robust ----------------

@group("robust")
def test_binary_text(ctx):
    """Byte lạ (không phải 0x00) trong tin"""
    cs, m = make(ctx, 2)
    cs[0].send(b"MSG \x01\x80\xff\x7f end\n")
    got = cs[1].recv_exact(len(b"[u0]: \x01\x80\xff\x7f end\n"))
    if got != b"[u0]: \x01\x80\xff\x7f end\n":
        raise Fail(WA, f"nhận {got!r}")
    cs[0].expect_line("100 OK")


@group("robust")
@timeout(25)
def test_300_join_leave_cycles(ctx):
    """300 lượt vào–ra (QUIT / đóng / RST sau khi đọc hết phản hồi), cùng một tên mỗi lần"""
    for i in range(300):
        c = ctx.connect(name=f"c{i}")
        c.send_line("JOIN nick")
        c.expect_line("100 OK")
        if i % 3 == 0:
            c.send_line("QUIT")
            c.expect_line("100 OK")
        elif i % 3 == 1:
            c.close()
        else:
            c.reset()
        ctx.close_quietly(c)
        time.sleep(0.004 if i % 3 else 0)
        if i % 3 == 2:
            time.sleep(0.01)


@group("robust")
def test_sender_leaves_after_message(ctx):
    """Người gửi đóng ngay sau khi gửi tin: người nhận vẫn nhận đủ, server sống"""
    cs, m = make(ctx, 3)
    cs[0].send("MSG lan cuoi\n")
    cs[0].expect_line("100 OK")
    cs[0].reset()
    m.nick[0] = None
    cs[1].expect_line("[u0]: lan cuoi")
    cs[2].expect_line("[u0]: lan cuoi")
    time.sleep(0.2)
    step(cs, m, 1, "MSG con lai hai nguoi", silence=0.05)


# ---------------- concurrency ----------------

@group("concurrency")
def test_idle_clients_do_not_block(ctx):
    """Client im lặng/gửi dở lệnh không chặn client khác"""
    cs, m = make(ctx, 4)
    cs[3].send("MSG chua xong")
    with ctx.verdict(BLOCKED):
        step(cs, m, 0, "PMSG u1 van chay")
    cs[3].send("\n")
    m.run(3, "MSG chua xong")
    for j in range(3):
        cs[j].expect_line("[u3]: chua xong")
    cs[3].expect_line("100 OK")


@group("concurrency")
@timeout(20)
def test_20_clients_random(ctx):
    """20 client, 300 thao tác ngẫu nhiên (MSG / PMSG / lệnh sai) so với mô hình"""
    n = 20
    cs, m = make(ctx, n)
    rng = ctx.rng
    for _ in range(300):
        i = rng.randrange(n)
        r = rng.random()
        if r < 0.5:
            line = "MSG " + rng.choice(["hi", "a b c", "x" * 50, "!@#"])
        elif r < 0.9:
            line = f"PMSG u{rng.randrange(n + 2)} " + rng.choice(["rieng", "hello there"])
        else:
            line = rng.choice(["JOIN u1", "PING", "MSG", "PMSG u1"])
        step(cs, m, i, line)


# ---------------- stress ----------------

@group("stress")
@timeout(40)
def test_random_ops_vs_model(ctx):
    """1200 thao tác ngẫu nhiên của 6 client (JOIN, MSG, PMSG, rời đi và vào lại) so với mô hình"""
    n = 6
    rng = ctx.rng
    cs, m = make(ctx, n, join=False)
    names = [f"n{k}" for k in range(8)] + ["Bad", "", "a b"]
    for _ in range(1200):
        i = rng.randrange(n)
        r = rng.random()
        if r < 0.15:
            line = "JOIN " + rng.choice(names)
        elif r < 0.5:
            line = "MSG " + rng.choice(["hi", "x y", "hello world"])
        elif r < 0.8:
            line = f"PMSG {rng.choice(names)} " + rng.choice(["p", "rieng tu"])
        elif r < 0.9:
            line = rng.choice(["PING", "MSG", "PMSG a", "JOIN"])
        else:
            step(cs, m, i, "QUIT")
            cs[i].expect_closed()
            cs[i] = ctx.connect(name=f"c{i}")
            continue
        step(cs, m, i, line)
