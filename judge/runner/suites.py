"""Bộ test dùng chung (xem docs/TEST-DESIGN.md). Trong tests/test_main.py của bài:

    from suites import echo_suite
    globals().update(echo_suite(concurrent=True, slow_reader=True))

Mỗi hàm trả về dict {tên: hàm test} theo đúng thứ tự chạy.
"""
import os
import select
import time

from njlib import BLOCKED, LIMIT, WA, Fail, args, buffer_boundary_sizes, cases, group, sample, timeout


def _collect():
    tests = {}

    def add(fn):
        tests[fn.__name__] = fn
        return fn
    return tests, add


def flood_without_reading(conn, limit=8 << 20):
    """Gửi tới khi bộ đệm hai phía đầy (client không đọc gì). Trả về số byte đã gửi."""
    conn.sock.setblocking(False)
    sent = 0
    chunk = b"x" * 65536
    deadline = time.monotonic() + 2.0
    try:
        while sent < limit and time.monotonic() < deadline:
            try:
                sent += conn.sock.send(chunk)
            except BlockingIOError:
                time.sleep(0.05)
                try:
                    sent += conn.sock.send(chunk)
                except BlockingIOError:
                    break
    finally:
        conn.sock.setblocking(True)
    return sent


def full_duplex(conn, data, limit, read_size=1 << 20):
    """Gửi `data` bằng socket non-blocking, đồng thời đọc mọi thứ server gửi về. Trả về các byte đã nhận
    (dừng khi đã nhận đủ len(data), khi server đóng, hoặc sau `limit` giây không có tiến triển)."""
    s = conn.sock
    s.setblocking(False)
    sent, got = 0, bytearray()
    last = time.monotonic()
    try:
        while len(got) < len(data):
            want_w = [s] if sent < len(data) else []
            r, w, _ = select.select([s], want_w, [], 0.2)
            progressed = False
            if w:
                try:
                    sent += s.send(data[sent:sent + 65536])
                    progressed = True
                except BlockingIOError:
                    pass
            if r:
                try:
                    chunk = s.recv(read_size)
                except BlockingIOError:
                    chunk = None
                except OSError:
                    chunk = b""
                if chunk == b"":
                    break
                if chunk:
                    got += chunk
                    progressed = True
            if progressed:
                last = time.monotonic()
            elif time.monotonic() - last > limit:
                break
    finally:
        s.setblocking(True)
    return bytes(got)


def echo_roundtrip(c, data, timeout=2.0):
    c.send(data)
    c.expect_bytes(data, timeout=timeout)


def echo_suite(concurrent=True, slow_reader=False, max_clients=50, zombie_check=False):
    T, add = _collect()

    # ---------------- sample ----------------
    @add
    @sample
    def test_echo(ctx):
        """Echo một dòng chữ"""
        c = ctx.connect()
        c.send("xin chao\n")
        c.expect_line("xin chao")

    if concurrent:
        @add
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

    # ---------------- basic ----------------
    @add
    @group("basic")
    def test_binary_all_bytes(ctx):
        """Dữ liệu nhị phân đủ 256 giá trị byte, kể cả 0x00"""
        c = ctx.connect()
        echo_roundtrip(c, bytes(range(256)) * 4)

    @add
    @group("basic")
    def test_nul_first(ctx):
        """Thông điệp bắt đầu bằng byte 0x00 (strlen = 0)"""
        c = ctx.connect()
        echo_roundtrip(c, b"\x00\x00abc\x00\n")

    @add
    @group("basic")
    def test_request_response_100(ctx):
        """100 lượt gửi-nhận liên tiếp trên một kết nối"""
        c = ctx.connect()
        for i in range(100):
            c.send(f"tin nhan {i}\n")
            c.expect_line(f"tin nhan {i}")

    @add
    @group("basic")
    def test_sequential_clients(ctx):
        """Client sau được phục vụ khi client trước đã đóng"""
        for i in range(5):
            c = ctx.connect(name=f"client{i + 1}")
            c.send(f"lan {i}\n")
            c.expect_line(f"lan {i}")
            c.close()
            time.sleep(0.02)

    # ---------------- edge ----------------
    @add
    @group("edge")
    def test_single_byte(ctx):
        """Một byte duy nhất, không có xuống dòng"""
        c = ctx.connect()
        echo_roundtrip(c, b"z")

    @add
    @group("edge")
    def test_connect_close_no_data(ctx):
        """Ba client kết nối rồi đóng ngay không gửi gì; client sau vẫn được phục vụ"""
        for _ in range(3):
            ctx.connect().close()
        time.sleep(0.1)
        c = ctx.connect(name="sau")
        echo_roundtrip(c, b"con song khong\n")

    @add
    @group("edge")
    @cases(*buffer_boundary_sizes(), 8191, 8192, 8193, 65536, title="Khối {0} byte gửi một lần (ranh giới bộ đệm)")
    def test_boundary_size(ctx, n):
        c = ctx.connect()
        echo_roundtrip(c, bytes(ctx.rng.randrange(256) for _ in range(n)), timeout=3)

    # ---------------- stream ----------------
    @add
    @group("stream")
    def test_random_fragments(ctx):
        """20 KB cắt thành mảnh ngẫu nhiên 1–64 byte"""
        c = ctx.connect()
        data = bytes(ctx.rng.randrange(256) for _ in range(20000))
        c.send_chunks(data, ctx.rng, 1, 64, delay=0)
        c.expect_bytes(data, timeout=3)

    @add
    @group("stream")
    def test_byte_by_byte(ctx):
        """Gửi từng byte có độ trễ: phải echo đủ, không chờ đủ 'một dòng'"""
        c = ctx.connect()
        c.send_slowly("tung byte mot", chunk=1, delay=0.01)
        c.expect_bytes("tung byte mot")

    @add
    @group("stream")
    def test_burst_500_lines(ctx):
        """500 dòng dính nhau trong một lần gửi"""
        c = ctx.connect()
        data = "".join(f"dong {i}\n" for i in range(500)).encode()
        echo_roundtrip(c, data, timeout=3)

    # ---------------- robust ----------------
    @add
    @group("robust")
    def test_half_close(ctx):
        """Client gửi 30 KB rồi shutdown(SHUT_WR): server echo đủ rồi mới đóng"""
        c = ctx.connect()
        data = os.urandom(30000)
        c.send(data)
        c.shutdown_write()
        got = c.recv_all_until_close(timeout=3)
        if got != data:
            raise Fail(WA, f"nhận {len(got)}/{len(data)} byte trước khi server đóng (hoặc sai nội dung)")

    @add
    @group("robust")
    def test_reset_with_pending_data(ctx):
        """Client gửi 512 KB rồi đóng đột ngột (RST): server không được chết (SIGPIPE) và vẫn phục vụ tiếp"""
        for k in range(3):
            c = ctx.connect(name=f"rst{k}")
            flood_without_reading(c, limit=512 << 10)
            c.reset()
            time.sleep(0.15)
            ctx.expect_alive("sau khi client đóng đột ngột (quên bỏ qua SIGPIPE / không kiểm tra lỗi send?)")
        c = ctx.connect(name="sau")
        echo_roundtrip(c, b"van phuc vu\n")

    @add
    @group("robust")
    def test_reset_storm(ctx):
        """20 client gửi dữ liệu rồi RST liên tiếp"""
        for k in range(20):
            c = ctx.connect(name=f"rst{k}")
            c.send(os.urandom(20000))
            c.reset()
        time.sleep(0.3)
        ctx.expect_alive("sau 20 lần client đóng đột ngột")
        c = ctx.connect(name="sau")
        echo_roundtrip(c, b"ok\n")

    if slow_reader:
        @add
        @group("robust")
        def test_slow_reader_does_not_block(ctx):
            """Client gửi liên tục nhưng không đọc phản hồi: client khác vẫn được phục vụ"""
            slow = ctx.connect(name="khong-doc", rcvbuf=4096)
            flood_without_reading(slow)
            with ctx.verdict(BLOCKED):
                b = ctx.connect(name="B")
                b.send("B van duoc phuc vu\n")
                b.expect_line("B van duoc phuc vu", timeout=1.0)

    # ---------------- concurrency ----------------
    if concurrent:
        @add
        @group("concurrency")
        def test_interleaved_random(ctx):
            """20 client, 5 vòng, thứ tự gửi và đọc ngẫu nhiên"""
            rng = ctx.rng
            cs = [ctx.connect(name=f"C{i}") for i in range(20)]
            with ctx.verdict(BLOCKED):
                for r in range(5):
                    order = list(range(20))
                    rng.shuffle(order)
                    for i in order:
                        cs[i].send(f"{i}:{r}:" + "x" * rng.randint(0, 300) + "\n")
                    rng.shuffle(order)
                    for i in order:
                        line = cs[i].recv_line(timeout=1.5)
                        if not line.startswith(f"{i}:{r}:"):
                            raise Fail(WA, f"C{i}: nhận {line[:40]!r}, mong đợi dòng của chính nó ({i}:{r}:...)")

        @add
        @group("concurrency")
        def test_max_clients(ctx):
            cs = [ctx.connect(name=f"C{i}") for i in range(max_clients)]
            for i, c in enumerate(cs):
                c.send(f"hello {i}\n")
            for i, c in enumerate(cs):
                c.expect_line(f"hello {i}", timeout=2)
        test_max_clients.__doc__ = f"{max_clients} client kết nối cùng lúc"

        @add
        @group("concurrency")
        def test_disconnect_others_continue(ctx):
            """Client ở giữa danh sách rời đi (đóng thường và RST), các client khác không bị ảnh hưởng"""
            cs = [ctx.connect(name=f"C{i}") for i in range(6)]
            cs[2].close()
            cs[4].reset()
            time.sleep(0.1)
            for i in (0, 1, 3, 5):
                echo_roundtrip(cs[i], f"C{i} van o day\n".encode())
            d = ctx.connect(name="D")
            echo_roundtrip(d, b"d moi vao\n")

        @add
        @group("concurrency")
        @timeout(15)
        def test_parallel_large(ctx):
            """4 client cùng gửi 256 KB xen kẽ từng khối"""
            cs = [ctx.connect(name=f"big{i}") for i in range(4)]
            blobs = [os.urandom(256 * 1024) for _ in cs]
            step = 16 * 1024
            for off in range(0, 256 * 1024, step):
                for c, b in zip(cs, blobs):
                    c.send(b[off:off + step])
                for c, b in zip(cs, blobs):
                    c.expect_bytes(b[off:off + step], timeout=3)

        @add
        @group("concurrency")
        @timeout(15)
        def test_churn_while_active(ctx):
            """5 client giữ kết nối trong khi 100 client khác vào-ra"""
            keep = [ctx.connect(name=f"K{i}") for i in range(5)]
            for i in range(100):
                c = ctx.connect(name=f"tam{i}")
                echo_roundtrip(c, f"{i}\n".encode())
                (c.reset if i % 3 == 0 else c.close)()
                if i % 20 == 0:
                    for k, kc in enumerate(keep):
                        echo_roundtrip(kc, f"K{k} lan {i}\n".encode())
            for k, kc in enumerate(keep):
                echo_roundtrip(kc, f"K{k} cuoi\n".encode())

    # ---------------- stress ----------------
    @add
    @group("stress")
    @timeout(15)
    def test_1mb(ctx):
        """1 MB ngẫu nhiên, gửi và đọc xen kẽ 64 KB"""
        c = ctx.connect()
        blob = os.urandom(1 << 20)
        step = 64 * 1024
        for i in range(0, len(blob), step):
            c.send(blob[i:i + step])
            c.expect_bytes(blob[i:i + step], timeout=3)

    @add
    @group("stress")
    @timeout(15)
    def test_full_duplex_1mb(ctx):
        """Gửi 1 MB không chờ, vừa gửi vừa đọc chậm (bộ đệm gửi của server sẽ đầy: phải gửi tiếp, không được bỏ dữ liệu)"""
        c = ctx.connect(rcvbuf=4096)
        data = os.urandom(1 << 20)
        got = full_duplex(c, data, 5.0, read_size=4096)
        if got != data:
            k = next((i for i in range(min(len(got), len(data))) if got[i] != data[i]), min(len(got), len(data)))
            raise Fail(WA, f"nhận {len(got)}/{len(data)} byte, sai/thiếu từ byte {k}")

    @add
    @group("stress")
    @timeout(15)
    def test_flood_then_drain(ctx):
        """Client gửi tới khi đầy bộ đệm mà chưa đọc gì, rồi mới đọc: server phải chờ gửi tiếp, không bỏ client"""
        c = ctx.connect(rcvbuf=8192)
        sent = flood_without_reading(c, limit=4 << 20)
        got = c.recv_exact(sent, timeout=5)
        if got != b"x" * sent:
            raise Fail(WA, "dữ liệu echo sai nội dung")

    @add
    @group("stress")
    @timeout(20)
    def test_fd_leak_300(ctx):
        """300 lượt kết nối-ngắt liên tiếp (bài nộp chỉ có 256 file descriptor: quên close() là hết)"""
        for i in range(300):
            c = ctx.connect(name=f"lan{i}")
            c.send(b"p\n")
            c.expect_line("p", timeout=2)
            c.close()
            ctx.close_quietly(c)
        c = ctx.connect(name="cuoi")
        echo_roundtrip(c, b"van con fd\n")

    if zombie_check:
        @add
        @group("stress")
        @timeout(15)
        def test_no_zombies(ctx):
            """Tiến trình con kết thúc phải được thu dọn (không còn zombie)"""
            for i in range(15):
                c = ctx.connect(name=f"C{i}")
                echo_roundtrip(c, b"x\n")
                c.close() if i % 2 else c.reset()
            time.sleep(0.8)
            z = ctx.zombies()
            if z:
                raise Fail(WA, f"còn {z} tiến trình zombie — cần waitpid() (ví dụ trong handler SIGCHLD)")
            c = ctx.connect(name="after")
            echo_roundtrip(c, b"van chay\n")

        @add
        @group("stress")
        @timeout(15)
        def test_simultaneous_exit_no_zombies(ctx):
            """30 client cùng ngắt một lúc: nhiều SIGCHLD bị gộp làm một, handler phải waitpid trong vòng lặp"""
            cs = [ctx.connect(name=f"C{i}") for i in range(30)]
            for c in cs:
                echo_roundtrip(c, b"z\n")
            for c in cs:
                c.reset()
            time.sleep(1.0)
            z = ctx.zombies()
            if z:
                raise Fail(WA, f"còn {z} zombie sau khi 30 tiến trình con kết thúc gần như cùng lúc — "
                               "handler SIGCHLD phải gọi waitpid(-1, ..., WNOHANG) trong vòng lặp while")
            c = ctx.connect(name="after")
            echo_roundtrip(c, b"van chay\n")

        @add
        @group("stress")
        @timeout(20)
        def test_many_children_over_time(ctx):
            """150 client lần lượt (vượt giới hạn 128 tiến trình nếu không thu dọn con)"""
            for i in range(150):
                c = ctx.connect(name=f"C{i}")
                echo_roundtrip(c, b"y\n")
                c.close()
                ctx.close_quietly(c)
            time.sleep(0.3)
            c = ctx.connect(name="cuoi")
            echo_roundtrip(c, b"cuoi\n")

    return T


def maxn_suite(welcome="WELCOME", full="FULL", quit=("QUIT", "BYE"), ping=("COUNT", None), max_n=50, extra_args=()):
    """Test chung cho dạng đề "server TCP phục vụ tối đa N client" (tham số dòng lệnh: <cổng> <N>).
    ping = (lệnh, phản hồi) dùng để kiểm tra một client còn được phục vụ; phản hồi None = chấp nhận mọi dòng."""
    T, add = _collect()
    qcmd, bye = quit
    pcmd, pwant = ping

    def hello(ctx, name):
        c = ctx.connect(name=name)
        c.expect_line(welcome, timeout=1.5)
        return c

    def rejected(ctx, name):
        c = ctx.connect(name=name)
        c.expect_line(full, timeout=1.5)
        c.expect_closed(timeout=1.5)

    def alive(c):
        c.send_line(pcmd)
        got = c.recv_line(timeout=1.5)
        if pwant is not None and got != pwant:
            raise Fail(WA, f"{c.name}: gửi {pcmd!r} mong đợi {pwant!r}, nhận được {got!r}")

    @add
    @group("edge")
    @args("{port}", "1", *extra_args)
    def test_maxn_n1_cycle(ctx):
        """N=1: FULL khi đã có 1 client; chỗ được trả lại sau QUIT, sau khi đóng, sau RST"""
        a = hello(ctx, "A")
        with ctx.verdict(LIMIT):
            rejected(ctx, "B")
        a.send_line(qcmd)
        a.expect_line(bye)
        a.expect_closed()
        time.sleep(0.1)
        with ctx.verdict(LIMIT):
            c = hello(ctx, "C")
        c.close()
        time.sleep(0.2)
        with ctx.verdict(LIMIT):
            d = hello(ctx, "D")
        d.reset()
        time.sleep(0.2)
        with ctx.verdict(LIMIT):
            e = hello(ctx, "E")
            rejected(ctx, "F")
        alive(e)

    @add
    @group("edge")
    @args("{port}", str(max_n), *extra_args)
    @timeout(12)
    def test_maxn_upper_bound(ctx):
        cs = [hello(ctx, f"C{i}") for i in range(max_n)]
        with ctx.verdict(LIMIT):
            rejected(ctx, "thua")
        for c in cs:
            alive(c)
    test_maxn_upper_bound.__doc__ = f"N={max_n}: đủ {max_n} client cùng lúc, client thứ {max_n + 1} bị FULL"

    @add
    @group("edge")
    @args("{port}", "3", *extra_args)
    def test_maxn_full_does_not_count(ctx):
        """N=3: các kết nối bị FULL không chiếm chỗ (10 lần bị từ chối, rồi 1 client rời đi là có chỗ)"""
        cs = [hello(ctx, f"C{i}") for i in range(3)]
        for k in range(10):
            with ctx.verdict(LIMIT):
                rejected(ctx, f"X{k}")
        cs[1].send_line(qcmd)
        cs[1].expect_line(bye)
        time.sleep(0.1)
        with ctx.verdict(LIMIT):
            n = hello(ctx, "moi")
            rejected(ctx, "lai-thua")
        alive(n)

    @add
    @group("concurrency")
    @args("{port}", "4", *extra_args)
    def test_maxn_slot_freed_by_rst(ctx):
        """N=4: hai client bị RST (mất mạng) phải trả lại chỗ"""
        cs = [hello(ctx, f"C{i}") for i in range(4)]
        cs[0].reset()
        cs[3].reset()
        time.sleep(0.3)
        with ctx.verdict(LIMIT):
            a, b = hello(ctx, "A"), hello(ctx, "B")
            rejected(ctx, "thua")
        for c in (cs[1], cs[2], a, b):
            alive(c)

    @add
    @group("concurrency")
    @args("{port}", "5", *extra_args)
    def test_maxn_partial_line_does_not_block(ctx):
        """Client gửi dở một dòng rồi im lặng: client khác vẫn được phục vụ, phần dở được ghép đúng"""
        idle = hello(ctx, "do-dang")
        idle.send(pcmd[:1])
        with ctx.verdict(BLOCKED):
            b = hello(ctx, "B")
            alive(b)
        idle.send(pcmd[1:] + "\n")
        got = idle.recv_line(timeout=1.5)
        if pwant is not None and got != pwant:
            raise Fail(WA, f"dòng bị cắt đôi {pcmd[:1]!r} + {pcmd[1:]!r}: mong đợi {pwant!r}, nhận {got!r}")

    @add
    @group("robust")
    @args("{port}", "1", *extra_args)
    @timeout(20)
    def test_maxn_full_storm_fd_leak(ctx):
        """N=1: 300 kết nối liên tiếp bị FULL (quên close() socket bị từ chối là hết 256 fd)"""
        a = hello(ctx, "giu-cho")
        for k in range(300):
            c = ctx.connect(name=f"X{k}")
            with ctx.verdict(LIMIT):
                c.expect_line(full, timeout=1.5)
            c.close()
            ctx.close_quietly(c)
        a.send_line(qcmd)
        a.expect_line(bye)
        time.sleep(0.1)
        with ctx.verdict(LIMIT):
            b = hello(ctx, "sau")
        alive(b)

    @add
    @group("stress")
    @args("{port}", "2", *extra_args)
    @timeout(20)
    def test_maxn_churn_fd_leak(ctx):
        """N=2: 300 client lần lượt vào rồi ra (xen kẽ QUIT / đóng / RST)"""
        for k in range(300):
            c = hello(ctx, f"C{k}")
            if k % 3 == 0:
                c.send_line(qcmd)
                c.expect_line(bye)
            elif k % 3 == 1:
                c.close()
            else:
                c.reset()
            ctx.close_quietly(c)
            if k % 3:
                time.sleep(0.005)
        time.sleep(0.2)
        with ctx.verdict(LIMIT):
            a, b = hello(ctx, "A"), hello(ctx, "B")
            rejected(ctx, "thua")
        alive(a)
        alive(b)

    @add
    @group("robust")
    @args("{port}", "5", *extra_args)
    def test_maxn_pipeline_then_rst(ctx):
        """Client dồn 300 lệnh rồi RST ngay: server không chết (SIGPIPE), chỗ được trả lại"""
        for k in range(3):
            c = hello(ctx, f"rst{k}")
            c.send((pcmd + "\n") * 300)
            c.reset()
        time.sleep(0.3)
        ctx.expect_alive("sau khi client dồn lệnh rồi đóng đột ngột")
        with ctx.verdict(LIMIT):
            cs = [hello(ctx, f"C{i}") for i in range(5)]
        for c in cs:
            alive(c)

    @add
    @group("robust")
    @args("{port}", "5", *extra_args)
    def test_maxn_quit_mid_batch(ctx):
        """QUIT nằm giữa một khối lệnh dính nhau: xử lý các lệnh trước, BYE, đóng; bỏ phần sau"""
        c = hello(ctx, "A")
        c.send((pcmd + "\n") * 3 + qcmd + "\n" + (pcmd + "\n") * 3)
        for _ in range(3):
            got = c.recv_line(timeout=1.5)
            if pwant is not None and got != pwant:
                raise Fail(WA, f"mong đợi {pwant!r}, nhận {got!r}")
        c.expect_line(bye)
        c.expect_closed(timeout=1.5)

    @add
    @group("concurrency")
    @args("{port}", "4", *extra_args)
    @timeout(20)
    def test_maxn_random_model(ctx):
        """N=4: 150 thao tác ngẫu nhiên (vào / QUIT / đóng / RST / lệnh), so với mô hình số chỗ"""
        rng = ctx.rng
        live = []
        k = 0
        for step in range(150):
            r = rng.random()
            if r < 0.35:
                k += 1
                if len(live) < 4:
                    with ctx.verdict(LIMIT):
                        live.append(hello(ctx, f"C{k}"))
                else:
                    with ctx.verdict(LIMIT):
                        rejected(ctx, f"C{k}")
            elif r < 0.6 and live:
                c = live.pop(rng.randrange(len(live)))
                how = rng.choice(["quit", "close", "rst"])
                if how == "quit":
                    c.send_line(qcmd)
                    c.expect_line(bye)
                    c.expect_closed(timeout=1.5)
                elif how == "close":
                    c.close()
                else:
                    c.reset()
                time.sleep(0.12)
            elif live:
                alive(rng.choice(live))

    return T


__all__ = ["echo_suite", "maxn_suite", "flood_without_reading", "full_duplex", "echo_roundtrip"]
