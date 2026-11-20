import os
import time

from njlib import Fail, WA, cases, group, sample, timeout

WWW = os.path.join(os.path.dirname(__file__), "..", "files", "www")


def http(ctx, raw, slowly=False):
    c = ctx.connect()
    if slowly:
        c.send_slowly(raw, chunk=3, delay=0.01)
    else:
        c.send(raw)
    data = c.recv_all_until_close(timeout=2)
    if b"\r\n\r\n" not in data:
        raise Fail(WA, f"phản hồi không có dòng trống \\r\\n\\r\\n ngăn header và thân: {data[:200]!r}")
    head, body = data.split(b"\r\n\r\n", 1)
    lines = head.decode(errors="replace").split("\r\n")
    return lines, body


def expect(ctx, raw, status, ctype, body, slowly=False):
    lines, got_body = http(ctx, raw, slowly)
    want = [f"HTTP/1.1 {status}", f"Content-Type: {ctype}", f"Content-Length: {len(body)}", "Connection: close"]
    if lines != want:
        raise Fail(WA, f"header mong đợi {want}, nhận được {lines}")
    if got_body != body:
        raise Fail(WA, f"thân phản hồi sai: mong đợi {body[:80]!r}…, nhận được {got_body[:80]!r}…")


def file(path):
    return open(os.path.join(WWW, path), "rb").read()


HTML = "text/html; charset=utf-8"
TEXT = "text/plain; charset=utf-8"


@sample
def test_index(ctx):
    """GET / trả về index.html"""
    expect(ctx, "GET / HTTP/1.1\r\nHost: localhost\r\n\r\n", "200 OK", HTML, file("index.html"))


@sample
def test_not_found(ctx):
    """Tệp không tồn tại thì trả 404"""
    expect(ctx, "GET /khong-co.html HTTP/1.1\r\n\r\n", "404 Not Found", TEXT, b"Not Found\n")


@group("basic")
def test_nested_and_query(ctx):
    """Tệp trong thư mục con, có query string"""
    expect(ctx, "GET /docs/note.txt?x=1&y=2 HTTP/1.1\r\nHost: a\r\nUser-Agent: t\r\n\r\n",
           "200 OK", TEXT, file("docs/note.txt"))


@group("basic")
def test_dir_index(ctx):
    """Thư mục con có dấu / ở cuối thì phục vụ index.html của thư mục đó"""
    expect(ctx, "GET /docs/ HTTP/1.1\r\n\r\n", "200 OK", HTML, file("docs/index.html"))


@group("basic")
def test_binary(ctx):
    """Tệp nhị phân .png"""
    expect(ctx, "GET /logo.png HTTP/1.1\r\n\r\n", "200 OK", "image/png", file("logo.png"))


@group("basic")
def test_errors(ctx):
    """403 khi có '..', 405 khi không phải GET, 400 khi sai dòng đầu, 404 khi là thư mục"""
    expect(ctx, "GET /../secret.txt HTTP/1.1\r\n\r\n", "403 Forbidden", TEXT, b"Forbidden\n")
    expect(ctx, "POST / HTTP/1.1\r\nContent-Length: 0\r\n\r\n", "405 Method Not Allowed", TEXT,
           b"Method Not Allowed\n")
    expect(ctx, "HELLO\r\n\r\n", "400 Bad Request", TEXT, b"Bad Request\n")
    expect(ctx, "GET /docs HTTP/1.1\r\n\r\n", "404 Not Found", TEXT, b"Not Found\n")


@group("stream")
def test_fragmented_request(ctx):
    """Yêu cầu đến thành nhiều mảnh nhỏ"""
    expect(ctx, "GET /docs/note.txt HTTP/1.1\r\nHost: localhost\r\nAccept: */*\r\n\r\n",
           "200 OK", TEXT, file("docs/note.txt"), slowly=True)


@group("basic")
def test_sequential(ctx):
    """10 yêu cầu liên tiếp trên 10 kết nối"""
    for i in range(10):
        expect(ctx, f"GET /?lan={i} HTTP/1.1\r\n\r\n", "200 OK", HTML, file("index.html"))
        time.sleep(0.02)


# ======================= phần mở rộng (thiết kế lại) =======================
NOT_FOUND = ("404 Not Found", TEXT, b"Not Found\n")
FORBIDDEN = ("403 Forbidden", TEXT, b"Forbidden\n")
BAD = ("400 Bad Request", TEXT, b"Bad Request\n")
NOT_ALLOWED = ("405 Method Not Allowed", TEXT, b"Method Not Allowed\n")


def put(ctx, rel, data):
    """Tạo tệp trong thư mục gốc của server (thư mục chạy là bản sao của files/)."""
    path = os.path.join(ctx.workdir, "www", rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(data)
    os.chmod(path, 0o644)


@group("edge")
@cases(("GET /a..b.txt HTTP/1.1", FORBIDDEN), ("GET /docs/../index.html HTTP/1.1", FORBIDDEN),
       ("GET /.. HTTP/1.1", FORBIDDEN), ("GET /x?q=.. HTTP/1.1", NOT_FOUND),
       ("get / HTTP/1.1", NOT_ALLOWED), ("HEAD / HTTP/1.1", NOT_ALLOWED), ("DELETE /index.html HTTP/1.1", NOT_ALLOWED),
       ("GET /", BAD), ("GET", BAD), ("", BAD), ("GET / HTTP/1.1 thua", BAD),
       ("GET /docs/khong-co/ HTTP/1.1", NOT_FOUND), ("GET /index.html/ HTTP/1.1", NOT_FOUND),
       ("GET /docs/note.txt/x HTTP/1.1", NOT_FOUND),
       title="Dòng đầu {0!r} → {1[0]}")
def test_status_codes(ctx, line, want):
    expect(ctx, line + "\r\nHost: x\r\n\r\n", *want)


@group("edge")
@cases(("noext", "application/octet-stream"), ("a.htm", "application/octet-stream"),
       ("b.HTML", "application/octet-stream"), ("c.txt.html", "text/html; charset=utf-8"),
       ("d.html.txt", "text/plain; charset=utf-8"), ("e.png", "image/png"), ("f.", "application/octet-stream"),
       ("dir.html/g", "application/octet-stream"),
       title="Kiểu nội dung của tệp {0!r}")
def test_mime_types(ctx, name, ctype):
    data = b"noi dung " + name.encode()
    put(ctx, "m/" + name, data)
    expect(ctx, f"GET /m/{name} HTTP/1.1\r\n\r\n", "200 OK", ctype, data)


@group("edge")
@cases(0, 1, 4095, 4096, 4097, 65536, 1000000, title="Tệp {0} byte nhị phân (có 0x00)")
def test_file_sizes(ctx, n):
    data = bytes(ctx.rng.randrange(256) for _ in range(min(n, 5000))) * (n // 5000 + 1)
    data = data[:n]
    put(ctx, "big.bin", data)
    expect(ctx, "GET /big.bin HTTP/1.1\r\n\r\n", "200 OK", "application/octet-stream", data)


@group("edge")
def test_query_variants(ctx):
    """Query rỗng, query có '/' và '#'"""
    for q in ["?", "?a=1/2", "?x=y#z", "??"]:
        expect(ctx, f"GET /docs/note.txt{q} HTTP/1.1\r\n\r\n", "200 OK", TEXT, file("docs/note.txt"))


@group("edge")
def test_long_headers(ctx):
    """Yêu cầu có header dài gần 8 KB"""
    raw = "GET /docs/ HTTP/1.1\r\n" + "".join(f"X-Pad-{i}: " + "p" * 70 + "\r\n" for i in range(95)) + "\r\n"
    assert len(raw) < 8192
    expect(ctx, raw, "200 OK", HTML, file("docs/index.html"))


@group("edge")
def test_long_request_line(ctx):
    """Dòng đầu dài ~3000 byte (query rất dài) kèm header: vẫn phục vụ đúng tệp"""
    q = "x=" + "q" * 3000
    raw = f"GET /docs/note.txt?{q} HTTP/1.1\r\nHost: a\r\n\r\n"
    expect(ctx, raw, "200 OK", TEXT, file("docs/note.txt"))


@group("stream")
def test_terminator_split(ctx):
    """'\\r\\n\\r\\n' bị cắt giữa hai lần gửi (\\r\\n\\r | \\n)"""
    c = ctx.connect()
    c.send("GET / HTTP/1.1\r\nHost: a\r\n\r")
    time.sleep(0.1)
    c.send("\n")
    data = c.recv_all_until_close(timeout=2)
    if not data.startswith(b"HTTP/1.1 200 OK\r\n"):
        raise Fail(WA, f"phản hồi sai: {data[:80]!r}")


@group("stream")
def test_random_fragments(ctx):
    """Yêu cầu cắt thành mảnh ngẫu nhiên 1–5 byte"""
    c = ctx.connect()
    c.send_chunks("GET /docs/note.txt?k=v HTTP/1.1\r\nHost: localhost\r\nUser-Agent: t\r\n\r\n", ctx.rng, 1, 5, 0.003)
    data = c.recv_all_until_close(timeout=2)
    body = file("docs/note.txt")
    if not data.endswith(b"\r\n\r\n" + body):
        raise Fail(WA, f"phản hồi sai: {data[:120]!r}")


@group("robust")
def test_client_resets(ctx):
    """Client gửi yêu cầu tệp 1 MB rồi RST ngay / đóng khi chưa gửi xong header: server sống, phục vụ tiếp"""
    put(ctx, "big.bin", b"\x00" * 1000000)
    for k in range(3):
        c = ctx.connect(name=f"rst{k}")
        c.send("GET /big.bin HTTP/1.1\r\n\r\n")
        c.reset()
    d = ctx.connect(name="dang-do")
    d.send("GET / HTTP/1.1\r\nHo")
    d.close()
    time.sleep(0.3)
    ctx.expect_alive("sau khi client đóng đột ngột")
    expect(ctx, "GET / HTTP/1.1\r\n\r\n", "200 OK", HTML, file("index.html"))


@group("robust")
def test_body_after_headers_ignored(ctx):
    """Dữ liệu sau dòng trống (thân yêu cầu) bị bỏ qua; mỗi kết nối chỉ một phản hồi"""
    c = ctx.connect()
    c.send("GET /docs/note.txt HTTP/1.1\r\n\r\nGET / HTTP/1.1\r\n\r\n")
    data = c.recv_all_until_close(timeout=2)
    if data.count(b"HTTP/1.1 ") != 1:
        raise Fail(WA, f"mỗi kết nối chỉ được trả lời đúng một yêu cầu, nhận {data.count(b'HTTP/1.1 ')} phản hồi")


@group("stress")
@timeout(25)
def test_300_requests_fd_leak(ctx):
    """300 yêu cầu liên tiếp (quên fclose tệp hoặc close socket là hết 256 fd)"""
    body = file("docs/note.txt")
    for i in range(300):
        c = ctx.connect(name=f"R{i}")
        c.send(f"GET /docs/note.txt?i={i} HTTP/1.1\r\n\r\n")
        data = c.recv_all_until_close(timeout=2)
        if not data.endswith(body):
            raise Fail(WA, f"yêu cầu thứ {i}: phản hồi sai {data[:80]!r}")
        c.close()
        ctx.close_quietly(c)
