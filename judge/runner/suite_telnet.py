"""Bộ test chung cho telnet-select / telnet-fork (xem docs/TEST-DESIGN.md).

    from suite_telnet import telnet_suite
    globals().update(telnet_suite(fork=False))

Giao thức: dòng đăng nhập "<user> <pass>" -> LOGIN OK/FAIL; sau đó mỗi dòng là lệnh shell -> "OUTPUT <n>\\n" + n byte;
"exit" -> BYE rồi đóng. Tài khoản (files/accounts.txt): admin admin / guest nopass / sv20201234 matkhau123.
"""
import time

from njlib import BLOCKED, WA, Fail, cases, group, sample, timeout


def _collect():
    tests = {}

    def add(fn):
        tests[fn.__name__] = fn
        return fn
    return tests, add


def login(ctx, user="admin", pw="admin", name=None):
    c = ctx.connect(name=name)
    c.send_line(f"{user} {pw}")
    c.expect_line("LOGIN OK")
    return c


def read_output(c, timeout=2.0, cmd=None):
    head = c.recv_line(timeout, expecting="OUTPUT <n>")
    parts = head.split(" ")
    if len(parts) != 2 or parts[0] != "OUTPUT" or not parts[1].isdigit():
        hint = f" (lệnh {cmd!r})" if cmd else ""
        raise Fail(WA, f"{c.name}: mong đợi dòng 'OUTPUT <n>'{hint}, nhận được {head!r}")
    return c.recv_exact(int(parts[1]), timeout)


def run(c, cmd, timeout=2.0):
    c.send_line(cmd)
    return read_output(c, timeout, cmd)


def expect_output(c, cmd, want, timeout=2.0):
    want = want.encode() if isinstance(want, str) else want
    got = run(c, cmd, timeout)
    if got != want:
        raise Fail(WA, f"{c.name}: lệnh {cmd!r}: mong đợi {want[:120]!r} ({len(want)} byte), "
                       f"nhận được {got[:120]!r} ({len(got)} byte)")


def telnet_suite(fork=False):
    T, add = _collect()

    # ---------------- sample ----------------
    @add
    @sample
    def test_login_and_echo(ctx):
        """Đăng nhập đúng rồi chạy lệnh echo"""
        c = login(ctx)
        expect_output(c, "echo hello", "hello\n")

    @add
    @sample
    def test_login_fail_then_retry(ctx):
        """Sai mật khẩu báo LOGIN FAIL, cho thử lại"""
        c = ctx.connect()
        for bad in ["admin sai", "khongco admin", "admin", "admin admin admin", "guest  nopass"]:
            c.send_line(bad)
            c.expect_line("LOGIN FAIL")
        c.send_line("guest nopass")
        c.expect_line("LOGIN OK")

    # ---------------- basic ----------------
    @add
    @group("basic")
    def test_cat_file(ctx):
        """Kết quả nhiều dòng của lệnh cat"""
        c = login(ctx, "sv20201234", "matkhau123")
        expect_output(c, "cat data.txt", "dong mot\ndong hai\n")

    @add
    @group("basic")
    def test_empty_and_stderr(ctx):
        """Lệnh không in gì -> OUTPUT 0; thông báo lỗi (stderr) cũng được gửi về"""
        c = login(ctx)
        expect_output(c, "true", "")
        out = run(c, "cat khong_ton_tai.txt")
        if b"khong_ton_tai.txt" not in out:
            raise Fail(WA, f"thông báo lỗi của lệnh phải được gửi về (chuyển hướng 2>&1), nhận được {out!r}")

    @add
    @group("basic")
    def test_stdout_and_stderr_mixed(ctx):
        """Lệnh in cả stdout lẫn stderr: gom đủ cả hai"""
        c = login(ctx)
        out = run(c, "echo ra; echo loi 1>&2; echo ra2")
        for part in (b"ra\n", b"loi\n", b"ra2\n"):
            if part not in out:
                raise Fail(WA, f"thiếu {part!r} trong kết quả {out!r}")

    @add
    @group("basic")
    @cases(("printf abc", "abc"), ("echo a | tr a b", "b\n"), ('echo "x   y"', "x   y\n"),
           ("echo a; echo b", "a\nb\n"), ("printf '%s\\n' 1 2 3", "1\n2\n3\n"), ("echo $((6*7))", "42\n"),
           title="Lệnh shell {0!r}")
    def test_shell_features(ctx, cmd, want):
        c = login(ctx)
        expect_output(c, cmd, want)

    @add
    @group("basic")
    def test_several_commands_and_exit(ctx):
        """Nhiều lệnh liên tiếp, exit trả BYE và đóng"""
        c = login(ctx)
        for i in range(5):
            expect_output(c, f"echo lan{i}", f"lan{i}\n")
        c.send_line("exit")
        c.expect_line("BYE")
        c.expect_closed()

    @add
    @group("basic")
    def test_not_logged_in(ctx):
        """Chưa đăng nhập thì mọi dòng (kể cả lệnh, kể cả exit) là lần đăng nhập sai"""
        c = ctx.connect()
        for line in ["echo hack", "exit", "cat accounts.txt"]:
            c.send_line(line)
            c.expect_line("LOGIN FAIL")
        c.send_line("admin admin")
        c.expect_line("LOGIN OK")

    # ---------------- edge ----------------
    @add
    @group("edge")
    @cases(("admin admin ", "FAIL"), (" admin admin", "FAIL"), ("ADMIN admin", "FAIL"), ("admin ADMIN", "FAIL"),
           ("admin adm", "FAIL"), ("admi admin", "FAIL"), ("adminadmin", "FAIL"), ("guest nopas", "FAIL"),
           ("guest nopass2", "FAIL"), ("sv20201234 matkhau1234", "FAIL"), ("admin\tadmin", "FAIL"), ("", "FAIL"),
           ("admin guest", "FAIL"), ("guest admin", "FAIL"), ("sv20201234 matkhau123", "OK"),
           title="Đăng nhập bằng {0!r} → LOGIN {1}")
    def test_login_exact_match(ctx, line, want):
        c = ctx.connect()
        c.send_line(line)
        c.expect_line(f"LOGIN {want}")

    @add
    @group("edge")
    def test_login_crlf(ctx):
        """Dòng đăng nhập và lệnh kết thúc bằng CRLF"""
        c = ctx.connect()
        c.send("guest nopass\r\n")
        c.expect_line("LOGIN OK")
        c.send("echo crlf\r\n")
        got = read_output(c)
        if got != b"crlf\n":
            raise Fail(WA, f"'\\r' phải được bỏ trước khi chạy lệnh: mong đợi b'crlf\\n', nhận {got!r}")
        c.send("exit\r\n")
        c.expect_line("BYE")

    @add
    @group("edge")
    def test_output_with_nul_bytes(ctx):
        """Kết quả chứa byte 0x00: n phải là số byte thật (không dùng strlen)"""
        c = login(ctx)
        expect_output(c, "printf 'a\\000b\\000\\000c'", b"a\x00b\x00\x00c")
        expect_output(c, "printf '\\000'", b"\x00")

    @add
    @group("edge")
    @cases(4095, 4096, 4097, 8191, 8192, 8193, 65536, title="Kết quả đúng {0} byte (ranh giới bộ đệm)")
    def test_output_boundary(ctx, n):
        c = login(ctx)
        expect_output(c, f"head -c {n} /dev/zero | tr '\\000' x", b"x" * n)

    @add
    @group("edge")
    @cases(100, 500, 1000, title="Dòng lệnh dài {0} byte")
    def test_long_command_line(ctx, n):
        c = login(ctx)
        word = "".join(ctx.rng.choice("abcdefgh") for _ in range(n - 5))
        expect_output(c, "echo " + word, word + "\n")

    @add
    @group("edge")
    def test_empty_command_line(ctx):
        """Dòng lệnh rỗng sau khi đăng nhập → OUTPUT 0"""
        c = login(ctx)
        expect_output(c, "", "")
        expect_output(c, "echo sau", "sau\n")

    @add
    @group("edge")
    def test_exit_is_exact(ctx):
        """Chỉ đúng dòng 'exit' mới thoát: 'EXIT' là một lệnh shell bình thường"""
        c = login(ctx)
        out = run(c, "EXIT")
        if b"not found" not in out:
            raise Fail(WA, f"'EXIT' phải được chạy như lệnh shell (báo not found), nhận {out!r}")
        expect_output(c, "echo con", "con\n")

    @add
    @group("edge")
    @cases("exit 3", "exitnow", "exit;echo x", "exit ", title="Dòng {0!r} không phải đúng 'exit': chạy như lệnh shell")
    def test_exit_lookalikes_are_commands(ctx, cmd):
        c = login(ctx)
        run(c, cmd)
        expect_output(c, "echo con song", "con song\n")

    @add
    @group("edge")
    def test_credentials_after_login_are_commands(ctx):
        """Đã đăng nhập rồi thì 'admin admin' chỉ là một lệnh shell (không phải LOGIN OK lần nữa)"""
        c = login(ctx)
        for line in ("admin admin", "guest nopass"):
            out = run(c, line)
            if b"not found" not in out:
                raise Fail(WA, f"sau khi đăng nhập, {line!r} phải chạy như lệnh shell (báo not found), nhận {out!r}")
        expect_output(c, "echo con song", "con song\n")

    # ---------------- stream ----------------
    @add
    @group("stream")
    def test_exit_mid_batch(ctx):
        """'exit' nằm giữa khối lệnh dính nhau: chạy lệnh trước, BYE, đóng; bỏ lệnh phía sau"""
        c = ctx.connect()
        c.send("admin admin\necho truoc\nexit\necho sau\necho sau2\n")
        c.expect_line("LOGIN OK")
        got = read_output(c, 3)
        if got != b"truoc\n":
            raise Fail(WA, f"lệnh trước exit: mong đợi b'truoc\\n', nhận {got!r}")
        c.expect_line("BYE")
        c.expect_closed(timeout=1.5)

    @add
    @group("stream")
    def test_byte_by_byte(ctx):
        """Dòng đăng nhập và lệnh đến từng byte một"""
        c = ctx.connect()
        c.send_slowly("admin admin\n", chunk=1, delay=0.005)
        c.expect_line("LOGIN OK")
        c.send_slowly("echo tung byte\n", chunk=1, delay=0.005)
        got = read_output(c)
        if got != b"tung byte\n":
            raise Fail(WA, f"nhận {got!r}")

    @add
    @group("stream")
    def test_pipelined_commands(ctx):
        """Đăng nhập + 20 lệnh dính nhau trong một lần gửi: chạy đủ, đúng thứ tự"""
        c = ctx.connect()
        c.send("admin admin\n" + "".join(f"echo so{i}\n" for i in range(20)) + "exit\n")
        c.expect_line("LOGIN OK")
        for i in range(20):
            got = read_output(c, 3)
            if got != f"so{i}\n".encode():
                raise Fail(WA, f"lệnh thứ {i}: mong đợi {f'so{i}' + chr(10)!r}, nhận {got!r}")
        c.expect_line("BYE")
        c.expect_closed()

    @add
    @group("stream")
    def test_random_fragments(ctx):
        """10 lệnh cắt thành mảnh ngẫu nhiên 1–9 byte"""
        c = login(ctx)
        cmds = [f"echo manh{i} {'z' * ctx.rng.randint(1, 40)}" for i in range(10)]
        c.send_chunks("".join(x + "\n" for x in cmds), ctx.rng, 1, 9, delay=0.001)
        for x in cmds:
            got = read_output(c, 3)
            if got != (x[5:] + "\n").encode():
                raise Fail(WA, f"lệnh {x!r}: nhận {got!r}")

    # ---------------- robust ----------------
    @add
    @group("robust")
    def test_close_mid_line(ctx):
        """Client gửi dở dòng rồi đóng / RST ở cả hai giai đoạn (trước và sau đăng nhập)"""
        ctx.connect(name="a").send("admin ad")
        c = ctx.connect(name="b")
        c.send("admin admin\nech")
        c.expect_line("LOGIN OK")
        c.reset()
        time.sleep(0.2)
        d = login(ctx, name="d")
        expect_output(d, "echo van song", "van song\n")

    # ---------------- concurrency ----------------
    @add
    @group("concurrency")
    def test_two_users_isolated(ctx):
        """Hai người dùng cùng lúc, kết quả không lẫn nhau"""
        a = login(ctx, name="A")
        with ctx.verdict(BLOCKED):
            b = login(ctx, "guest", "nopass", name="B")
        for i in range(5):
            a.send_line(f"echo A{i}")
            b.send_line(f"echo B{i}")
            for c, tag in ((a, "A"), (b, "B")):
                body = read_output(c)
                if body != f"{tag}{i}\n".encode():
                    raise Fail(WA, f"{c.name} nhận {body!r}, mong đợi {tag}{i}\\n — kết quả bị lẫn giữa các client?")

    @add
    @group("concurrency")
    def test_idle_unauthenticated_does_not_block(ctx):
        """Client kết nối rồi gửi dở dòng đăng nhập và im lặng: client khác vẫn đăng nhập được"""
        idle = ctx.connect(name="im-lang")
        idle.send("adm")
        with ctx.verdict(BLOCKED):
            b = ctx.connect(name="B")
            b.send_line("guest nopass")
            b.expect_line("LOGIN OK", timeout=1.0)
        idle.send("in admin\n")
        idle.expect_line("LOGIN OK")

    @add
    @group("concurrency")
    @timeout(15)
    def test_ten_clients_interleaved(ctx):
        """10 client, mỗi client 5 lệnh xen kẽ (có kết quả lớn): không lẫn tệp tạm giữa các client"""
        cs = [login(ctx, name=f"C{i}") for i in range(10)]
        for r in range(5):
            for i, c in enumerate(cs):
                c.send_line(f"seq {i * 1000} {i * 1000 + 300 + r}")
            for i, c in enumerate(cs):
                want = "".join(f"{k}\n" for k in range(i * 1000, i * 1000 + 301 + r)).encode()
                got = read_output(c, 3)
                if got != want:
                    raise Fail(WA, f"{c.name} vòng {r}: kết quả sai/lẫn ({len(got)} byte, mong đợi {len(want)})")

    # ---------------- stress ----------------
    @add
    @group("stress")
    @timeout(15)
    def test_large_output(ctx):
        """Kết quả lớn ~1.3 MB (seq 1 200000)"""
        c = login(ctx)
        expect_output(c, "seq 1 200000", "".join(f"{i}\n" for i in range(1, 200001)), timeout=5)

    @add
    @group("stress")
    @timeout(20)
    def test_failed_logins_fd_leak(ctx):
        """300 lần đăng nhập sai trên một kết nối (quên fclose accounts.txt là hết 256 fd)"""
        c = ctx.connect()
        c.send("".join(f"admin sai{i}\n" for i in range(300)))
        for _ in range(300):
            c.expect_line("LOGIN FAIL", timeout=2)
        c.send_line("admin admin")
        c.expect_line("LOGIN OK")
        expect_output(c, "echo con fd", "con fd\n")

    @add
    @group("stress")
    @timeout(25)
    def test_session_churn_fd_leak(ctx):
        """300 phiên đăng nhập → exit liên tiếp (rò rỉ fd / tệp tạm)"""
        for i in range(300):
            c = ctx.connect(name=f"S{i}")
            c.send("guest nopass\nexit\n")
            c.expect_line("LOGIN OK", timeout=2)
            c.expect_line("BYE", timeout=2)
            c.close()
            ctx.close_quietly(c)
        c = login(ctx, name="cuoi")
        expect_output(c, "echo van con fd", "van con fd\n")

    if fork:
        @add
        @group("stress")
        @timeout(15)
        def test_no_zombies(ctx):
            """20 phiên kết thúc (exit / đóng / RST): cha phải thu dọn hết tiến trình con"""
            for i in range(20):
                c = login(ctx, name=f"Z{i}")
                expect_output(c, "true", "")
                if i % 3 == 0:
                    c.send_line("exit")
                    c.expect_line("BYE")
                (c.close if i % 3 == 1 else c.reset)()
            time.sleep(1.0)
            z = ctx.zombies()
            if z:
                raise Fail(WA, f"còn {z} tiến trình zombie — cần waitpid() trong handler SIGCHLD")
            c = login(ctx, name="sau")
            expect_output(c, "echo ok", "ok\n")

        @add
        @group("stress")
        @timeout(15)
        def test_simultaneous_exit_no_zombies(ctx):
            """30 phiên kết thúc cùng một lúc (SIGCHLD bị gộp): handler phải waitpid trong vòng lặp"""
            cs = [login(ctx, name=f"C{i}") for i in range(30)]
            for c in cs:
                c.reset()
            time.sleep(1.0)
            z = ctx.zombies()
            if z:
                raise Fail(WA, f"còn {z} zombie sau khi 30 phiên kết thúc gần như cùng lúc — "
                               "handler SIGCHLD phải gọi waitpid(-1, ..., WNOHANG) trong vòng lặp while")
            c = login(ctx, name="sau")
            expect_output(c, "echo ok", "ok\n")

    return T


__all__ = ["telnet_suite", "login", "run", "read_output", "expect_output"]
