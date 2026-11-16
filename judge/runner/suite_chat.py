"""Bộ test chung cho chat-select / chat-poll / thread-chat (xem docs/TEST-DESIGN.md).

Giao thức: dòng đầu "id: name" -> OK id / ERROR; sau đó mỗi dòng L của id được chuyển tới mọi client KHÁC đã
đăng ký dưới dạng "id: L".
"""
import time

from njlib import BLOCKED, WA, Fail, cases, group, sample, timeout


def _collect():
    tests = {}

    def add(fn):
        tests[fn.__name__] = fn
        return fn
    return tests, add


def join(ctx, cid, name=None):
    c = ctx.connect(name=cid)
    c.send_line(f"{cid}: {name or cid.upper()}")
    c.expect_line(f"OK {cid}")
    return c


def chat_suite():
    T, add = _collect()

    # ---------------- sample ----------------
    @add
    @sample
    def test_register(ctx):
        """Đăng ký đúng cú pháp"""
        c = ctx.connect()
        c.send_line("abc: An")
        c.expect_line("OK abc")

    @add
    @sample
    def test_register_invalid(ctx):
        """Sai cú pháp thì báo ERROR và cho đăng ký lại"""
        c = ctx.connect()
        for bad in ["abc An", "abc:An", ": An", "abc: ", "abc: Nguyen An", "abc : An"]:
            c.send_line(bad)
            c.expect_line("ERROR")
        c.send_line("abc: An")
        c.expect_line("OK abc")

    @add
    @sample
    def test_broadcast(ctx):
        """Tin nhắn tới mọi người khác, không quay về người gửi"""
        a, b, d = join(ctx, "a"), join(ctx, "b"), join(ctx, "d")
        a.send_line("xin chao")
        b.expect_line("a: xin chao")
        d.expect_line("a: xin chao")
        a.expect_silence(0.2)
        d.send_line("hi all")
        a.expect_line("d: hi all")
        b.expect_line("d: hi all")

    # ---------------- basic ----------------
    @add
    @group("basic")
    def test_unregistered_gets_nothing(ctx):
        """Client chưa đăng ký (hoặc đăng ký sai) không nhận tin"""
        a, b = join(ctx, "a"), join(ctx, "b")
        lurker = ctx.connect(name="lurker")
        bad = ctx.connect(name="dang-ky-sai")
        bad.send_line("sai cu phap")
        bad.expect_line("ERROR")
        a.send_line("bi mat")
        b.expect_line("a: bi mat")
        lurker.expect_silence(0.3)
        bad.expect_silence(0.1)

    @add
    @group("basic")
    @cases("", " ", "a: b: c", "OK x", "ERROR", "x: Y", "  nhieu   dau   cach  ", "~!@#$%^&*()[]{}",
           title="Nội dung tin {0!r} được chuyển nguyên vẹn")
    def test_message_verbatim(ctx, msg):
        a, b = join(ctx, "a"), join(ctx, "b")
        a.send_line(msg)
        b.expect_line(f"a: {msg}")

    @add
    @group("basic")
    def test_order_preserved(ctx):
        """100 tin của một người đến người khác đúng thứ tự"""
        a, b, d = join(ctx, "a"), join(ctx, "b"), join(ctx, "d")
        for i in range(100):
            a.send_line(f"tin {i}")
        for c in (b, d):
            for i in range(100):
                c.expect_line(f"a: tin {i}", timeout=2)

    # ---------------- edge ----------------
    @add
    @group("edge")
    @cases(("x" * 32, "Y" * 32), ("1", "2"), ("id-with_dash.dot", "Ten"), ("Bình", "Nguyễn"),
           title="Đăng ký id={0!r:.14} name={1!r:.10}")
    def test_register_edge_ok(ctx, cid, name):
        c = ctx.connect()
        c.send_line(f"{cid}: {name}")
        c.expect_line(f"OK {cid}")

    @add
    @group("edge")
    @cases("abc:  An", "abc:", "", " abc: An", "abc: An ", "a b: c", "abc An:", "::", ": ",
           title="Dòng đăng ký sai {0!r} → ERROR")
    def test_register_edge_bad(ctx, line):
        c = ctx.connect()
        c.send_line(line)
        c.expect_line("ERROR")
        c.send_line("ok: Ten")
        c.expect_line("OK ok")

    @add
    @group("edge")
    def test_crlf(ctx):
        """Đăng ký và tin nhắn kết thúc bằng CRLF: bỏ '\\r'"""
        b = join(ctx, "b")
        a = ctx.connect(name="a")
        a.send("a: An\r\n")
        a.expect_line("OK a")
        a.send("co crlf\r\n\r\n")
        b.expect_bytes(b"a: co crlf\na: \n")

    @add
    @group("edge")
    @cases(255, 256, 1000, title="Tin nhắn dài {0} byte")
    def test_long_message(ctx, n):
        a, b = join(ctx, "a"), join(ctx, "b")
        msg = "".join(ctx.rng.choice("abc xyz") for _ in range(n))
        a.send_line(msg)
        b.expect_line(f"a: {msg}")

    @add
    @group("edge")
    def test_alone_in_room(ctx):
        """Chỉ có một người: gửi tin không nhận lại gì, server vẫn bình thường"""
        a = join(ctx, "a")
        a.send_line("co ai khong")
        a.expect_silence(0.3)
        b = join(ctx, "b")
        b.send_line("co toi")
        a.expect_line("b: co toi")

    # ---------------- stream ----------------
    @add
    @group("stream")
    def test_fragmented_line(ctx):
        """Một dòng bị cắt thành từng byte"""
        a, b = join(ctx, "a"), join(ctx, "b")
        a.send_slowly("chao ban toi la a\n", chunk=1, delay=0.005)
        b.expect_line("a: chao ban toi la a")

    @add
    @group("stream")
    def test_fragmented_register(ctx):
        """Dòng đăng ký bị cắt vụn"""
        c = ctx.connect()
        c.send_slowly("abc: An\n", chunk=2, delay=0.02)
        c.expect_line("OK abc")

    @add
    @group("stream")
    def test_coalesced_lines(ctx):
        """Nhiều dòng dính trong một lần gửi, kể cả dòng đăng ký sai và đúng"""
        b = join(ctx, "b")
        a = ctx.connect(name="a")
        a.send("sai\na: An\nmot\nhai\r\nba\n")
        a.expect_lines(["ERROR", "OK a"])
        for msg in ["mot", "hai", "ba"]:
            b.expect_line(f"a: {msg}")

    @add
    @group("stream")
    def test_random_fragments(ctx):
        """200 tin cắt thành mảnh ngẫu nhiên 1–25 byte"""
        rng = ctx.rng
        a, b = join(ctx, "a"), join(ctx, "b")
        msgs = ["".join(rng.choice("abcdef 012") for _ in range(rng.randint(0, 50))) for _ in range(200)]
        a.send_chunks("".join(m + "\n" for m in msgs), rng, 1, 25, delay=0)
        for m in msgs:
            b.expect_line(f"a: {m}", timeout=2)

    # ---------------- robust ----------------
    @add
    @group("robust")
    def test_receiver_reset(ctx):
        """Người nhận mất kết nối đột ngột (RST) mà server vẫn gửi tin cho họ: server không được chết (SIGPIPE)"""
        a, b = join(ctx, "a"), join(ctx, "b")
        for k in range(5):
            d = join(ctx, f"x{k}")
            a.send("".join(f"tin {k} {i}\n" for i in range(300)))
            d.reset()  # mất kết nối GIỮA lúc server đang phát loạt tin của a
            a.send("".join(f"tin {k} {i}\n" for i in range(300, 600)))
            for i in range(600):
                b.expect_line(f"a: tin {k} {i}", timeout=2)
            ctx.expect_alive("sau khi gửi tin cho client đã mất kết nối (SIGPIPE?)")
        c = join(ctx, "c")
        b.send_line("con day")
        a.expect_line("b: con day")
        c.expect_line("b: con day")

    @add
    @group("robust")
    def test_sender_resets_mid_line(ctx):
        """Người gửi gửi dở một dòng rồi RST: phần dở không được phát đi, người khác vẫn chat"""
        a, b = join(ctx, "a"), join(ctx, "b")
        a.send("chua xong")
        a.reset()
        time.sleep(0.2)
        b.expect_silence(0.2)
        c = join(ctx, "c")
        c.send_line("hello")
        b.expect_line("c: hello")

    @add
    @group("robust")
    def test_reconnect_must_register_again(ctx):
        """Kết nối mới (dùng lại chỗ của client cũ) phải đăng ký lại"""
        b = join(ctx, "b")
        for k in range(3):
            a = join(ctx, f"a{k}")
            a.close()
            time.sleep(0.1)
            n = ctx.connect(name=f"moi{k}")
            n.send_line("khong phai dang ky")
            n.expect_line("ERROR")
            b.send_line(f"lan {k}")
            n.expect_silence(0.15)
            n.close()
            time.sleep(0.05)

    # ---------------- concurrency ----------------
    @add
    @group("concurrency")
    def test_half_line_does_not_block(ctx):
        """Client gửi dở nửa dòng rồi im lặng không làm treo server"""
        a, b = join(ctx, "a"), join(ctx, "b")
        a.send("cau nay chua xong")
        with ctx.verdict(BLOCKED):
            newcomer = ctx.connect(name="c")
            newcomer.send_line("c: Cuong")
            newcomer.expect_line("OK c", timeout=0.5)
            b.send_line("van chat duoc")
            newcomer.expect_line("b: van chat duoc", timeout=0.5)
        a.send(" roi\n")
        b.expect_line("a: cau nay chua xong roi")

    @add
    @group("concurrency")
    def test_disconnect(ctx):
        """Client rời phòng (đóng thường / RST), những người còn lại vẫn chat được"""
        a, b, d, f = join(ctx, "a"), join(ctx, "b"), join(ctx, "d"), join(ctx, "f")
        b.close()
        f.reset()
        time.sleep(0.1)
        a.send_line("b di roi")
        d.expect_line("a: b di roi")
        e = join(ctx, "e")
        d.send_line("chao e")
        a.expect_line("d: chao e")
        e.expect_line("d: chao e")

    @add
    @group("concurrency")
    def test_many_clients(ctx):
        """30 client cùng phòng"""
        cs = [join(ctx, f"u{i}") for i in range(30)]
        cs[7].send_line("ping")
        for i, c in enumerate(cs):
            if i != 7:
                c.expect_line("u7: ping")
        cs[7].expect_silence(0.2)

    @add
    @group("concurrency")
    @timeout(15)
    def test_random_rounds_vs_model(ctx):
        """10 client, 15 vòng: mỗi vòng vài người gửi cùng lúc; ai cũng nhận đúng tập tin của người khác"""
        rng = ctx.rng
        cs = [join(ctx, f"p{i}") for i in range(10)]
        for r in range(15):
            senders = rng.sample(range(10), rng.randint(1, 5))
            for s in senders:
                cs[s].send_chunks(f"vong {r} tu p{s}\n", rng, 1, 8, delay=0)
            for i, c in enumerate(cs):
                want = sorted(f"p{s}: vong {r} tu p{s}" for s in senders if s != i)
                got = sorted(c.recv_line(timeout=1.5) for _ in want)
                if got != want:
                    raise Fail(WA, f"p{i} vòng {r}: mong đợi {want}, nhận {got}")
            for c in cs:
                c.expect_silence(0.02)

    # ---------------- stress ----------------
    @add
    @group("stress")
    @timeout(15)
    def test_1000_messages_5_receivers(ctx):
        """1000 tin dồn một lúc tới 5 người nhận"""
        a = join(ctx, "a")
        rs = [join(ctx, f"r{i}") for i in range(5)]
        a.send("".join(f"so {i}\n" for i in range(1000)))
        for r in rs:
            for i in range(1000):
                r.expect_line(f"a: so {i}", timeout=3)

    @add
    @group("stress")
    @timeout(25)
    def test_churn_fd_leak(ctx):
        """300 lượt vào phòng rồi rời đi (giới hạn 256 file descriptor)"""
        b = join(ctx, "b")
        for i in range(300):
            c = ctx.connect(name=f"t{i}")
            c.send_line(f"t{i}: T")
            c.expect_line(f"OK t{i}", timeout=2)
            (c.reset if i % 2 else c.close)()
            ctx.close_quietly(c)
        time.sleep(0.2)
        a = join(ctx, "a")
        a.send_line("cuoi cung")
        b.expect_line("a: cuoi cung")

    return T


__all__ = ["chat_suite", "join"]
