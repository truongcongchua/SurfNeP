import os
import time

from njlib import cases, group, sample, timeout

DATA = open(os.path.join(os.path.dirname(__file__), "..", "files", "data.txt"), "rb").read()


def set_file(ctx, data):
    with open(os.path.join(ctx.workdir, "data.txt"), "wb") as fh:
        fh.write(data)


def fetch(ctx, want, name=None, timeout=3):
    """Một client: nhận đúng `want` rồi server đóng kết nối (không thừa byte)."""
    c = ctx.connect(name=name)
    c.expect_bytes(want, timeout=timeout)
    c.expect_closed(timeout=1.5)
    return c


@sample
def test_one_client(ctx):
    """Client nhận đúng nội dung tệp rồi bị đóng kết nối"""
    fetch(ctx, DATA)


@sample
def test_two_clients(ctx):
    """Hai client lần lượt đều nhận đủ tệp"""
    for k in range(2):
        fetch(ctx, DATA, f"client{k}").close()


@group("basic")
def test_server_stays_alive(ctx):
    """Server không thoát sau client đầu tiên"""
    fetch(ctx, DATA).close()
    time.sleep(0.2)
    ctx.expect_alive("sau khi gửi tệp cho client đầu tiên")
    fetch(ctx, DATA, "sau")


@group("basic")
def test_file_changes(ctx):
    """Tệp đổi giữa hai client thì client sau nhận nội dung mới"""
    fetch(ctx, DATA, "A").close()
    new = b"Noi dung moi\n"
    # thay tệp bằng tệp mới (như khi trình soạn thảo lưu): ai giữ lại FILE* cũ sẽ vẫn thấy nội dung cũ
    tmp = os.path.join(ctx.workdir, "data.tmp")
    with open(tmp, "wb") as fh:
        fh.write(new)
    os.replace(tmp, os.path.join(ctx.workdir, "data.txt"))
    time.sleep(0.1)
    fetch(ctx, new, "B")


@group("edge")
@cases(0, 1, 4095, 4096, 4097, 8192, 100000, title="Tệp {0} byte")
def test_sizes(ctx, n):
    data = bytes(ctx.rng.randrange(256) for _ in range(n))
    set_file(ctx, data)
    c = ctx.connect()
    if n:
        c.expect_bytes(data, timeout=3)
    c.expect_closed(timeout=1.5)  # không được gửi thừa byte nào


@group("edge")
def test_nul_no_newline(ctx):
    """Tệp chứa byte 0x00 và không có xuống dòng cuối (không dùng fgets/strlen)"""
    data = b"Xin\x00chao\x00\x00\xff\xfe nhi phan"
    set_file(ctx, data)
    fetch(ctx, data)


@group("edge")
def test_client_never_sends(ctx):
    """Client không gửi gì vẫn nhận ngay tệp (server không chờ recv)"""
    c = ctx.connect()
    c.expect_bytes(DATA, timeout=1)


@group("robust")
def test_missing_file(ctx):
    """Tệp không tồn tại: đóng kết nối client, server vẫn sống và phục vụ tiếp khi tệp xuất hiện"""
    os.remove(os.path.join(ctx.workdir, "data.txt"))
    c = ctx.connect(name="thieu")
    c.expect_closed(timeout=2)
    c.close()
    ctx.expect_alive("khi tệp không tồn tại")
    set_file(ctx, DATA)
    fetch(ctx, DATA, "sau")


@group("stress")
@timeout(25)
def test_300_clients_fd_leak(ctx):
    """300 client lần lượt (quên close tệp hoặc close(client) là hết 256 fd)"""
    for i in range(300):
        c = fetch(ctx, DATA, f"C{i}")
        ctx.close_quietly(c)
