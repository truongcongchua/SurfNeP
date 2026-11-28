import time

from njlib import WA, Fail, cases, group, sample, timeout

SETTLE = 0.15


def online(ctx, want, name=None):
    """Kết nối mới phải nhận đúng `ONLINE want`. Trả về Conn."""
    c = ctx.connect(name=name or f"client{want}")
    c.expect_line(f"ONLINE {want}", timeout=1.5)
    return c


@sample
def test_first_client(ctx):
    """Client đầu tiên nhận ONLINE 1"""
    online(ctx, 1)


@sample
def test_two_clients(ctx):
    """Hai client lần lượt nhận ONLINE 1 và ONLINE 2"""
    online(ctx, 1)
    online(ctx, 2)


@group("basic")
def test_three_clients(ctx):
    """Ba client giữ kết nối: ONLINE 1, 2, 3"""
    for n in (1, 2, 3):
        online(ctx, n)


@group("basic")
def test_count_goes_down(ctx):
    """A, B vào; A đóng; C vào nhận ONLINE 2"""
    a = online(ctx, 1, "A")
    online(ctx, 2, "B")
    a.close()
    time.sleep(SETTLE)
    online(ctx, 2, "C")


@group("basic")
def test_everyone_leaves(ctx):
    """Tất cả đóng hết thì client mới lại nhận ONLINE 1"""
    cs = [online(ctx, n) for n in (1, 2, 3, 4)]
    for c in cs:
        c.close()
    time.sleep(SETTLE * 2)
    online(ctx, 1, "moi")


@group("basic")
def test_client_data_ignored(ctx):
    """Client gửi dữ liệu: server không trả lời gì và số client không đổi"""
    a = online(ctx, 1, "A")
    a.send(b"xin chao server\nkhong ai tra loi\n")
    a.expect_silence(0.4)
    online(ctx, 2, "B")


@group("basic")
def test_greeting_is_one_line_only(ctx):
    """Chỉ có đúng một dòng chào, không dữ liệu thừa sau đó"""
    a = online(ctx, 1)
    a.expect_silence(0.4)


@group("edge")
@cases((0,), (1,), (4,), title="Đóng client ở vị trí {0} trong 5 client rồi vào thêm một client")
def test_leave_position(ctx, pos):
    cs = [online(ctx, n + 1) for n in range(5)]
    cs[pos].close()
    time.sleep(SETTLE)
    online(ctx, 5, "moi")


@group("edge")
def test_half_close_counts_as_leaving(ctx):
    """Client shutdown chiều gửi: server đóng socket đó và không tính nữa"""
    a = online(ctx, 1, "A")
    a.shutdown_write()
    a.expect_closed(timeout=1.0)
    time.sleep(SETTLE)
    online(ctx, 1, "B")


@group("edge")
def test_leave_immediately_after_greeting(ctx):
    """Client đóng ngay sau khi nhận chào: không còn được tính"""
    for _ in range(3):
        online(ctx, 1).close()
        time.sleep(SETTLE)


@group("edge")
def test_50_clients(ctx):
    """50 client cùng lúc: ONLINE 1 … ONLINE 50"""
    for n in range(1, 51):
        online(ctx, n)


@group("stream")
def test_send_byte_by_byte(ctx):
    """Client gửi từng byte một, có \\r\\n và 0x00: không có phản hồi, vẫn đếm đúng"""
    a = online(ctx, 1, "A")
    a.send_slowly(b"a\x00b\r\n\xff", chunk=1, delay=0.01)
    a.expect_silence(0.3)
    online(ctx, 2, "B")


@group("stream")
def test_big_upload_discarded(ctx):
    """Client gửi 300 KB: server đọc hết, không gửi lại, client khác vẫn được phục vụ"""
    a = online(ctx, 1, "A")
    a.send(b"z" * 300000)
    b = online(ctx, 2, "B")
    a.expect_silence(0.3)
    b.expect_silence(0.1)


@group("robust")
def test_reset_clients(ctx):
    """5 client bị reset (RST): server đóng, không tính nữa, vẫn sống"""
    cs = [online(ctx, n) for n in range(1, 6)]
    for c in cs:
        c.reset()
    time.sleep(SETTLE * 2)
    ctx.expect_alive("sau 5 client reset")
    online(ctx, 1, "moi")


@group("robust")
def test_silent_clients_do_not_block(ctx):
    """Nhiều client im lặng giữ kết nối: client mới vẫn được chào ngay"""
    for n in range(1, 21):
        online(ctx, n)


@group("concurrency")
def test_many_open_at_once_then_close_all(ctx):
    """30 client mở cùng lúc (rồi mới đọc chào), đóng hết, rồi 30 client nữa"""
    for _ in range(2):
        cs = [ctx.connect(name=f"c{i}") for i in range(30)]
        got = sorted(int(c.recv_line(timeout=2.0).split()[1]) for c in cs)
        if got != list(range(1, 31)):
            raise Fail(WA, f"30 client cùng lúc: các số n nhận được là {got}, mong đợi 1..30")
        for c in cs:
            c.close()
        time.sleep(SETTLE * 3)


@group("concurrency")
@timeout(20)
def test_random_churn_vs_model(ctx):
    """120 thao tác ngẫu nhiên mở/đóng so với mô hình đếm"""
    rng = ctx.rng
    live = []
    for step in range(120):
        if live and (len(live) >= 40 or rng.random() < 0.45):
            c = live.pop(rng.randrange(len(live)))
            ctx.close_quietly(c)
            time.sleep(SETTLE)
        else:
            live.append(online(ctx, len(live) + 1, f"s{step}"))


@group("stress")
@timeout(25)
def test_300_clients_fd_leak(ctx):
    """300 client lần lượt (bài nộp chỉ có 256 fd): luôn ONLINE 1, quên close() là hết fd"""
    for i in range(300):
        c = online(ctx, 1, f"c{i}")
        ctx.close_quietly(c)
        time.sleep(0.02)


@group("stress")
@timeout(25)
def test_fill_and_empty_three_times(ctx):
    """50 client vào, đóng hết, 3 lần liên tiếp (mảng client phải được dọn đúng)"""
    for _ in range(3):
        cs = [online(ctx, n, f"c{n}") for n in range(1, 51)]
        for c in cs:
            ctx.close_quietly(c)
        time.sleep(0.4)
