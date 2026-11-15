import os
import time

from njlib import Fail, WA, sample

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


def test_nested_and_query(ctx):
    """Tệp trong thư mục con, có query string"""
    expect(ctx, "GET /docs/note.txt?x=1&y=2 HTTP/1.1\r\nHost: a\r\nUser-Agent: t\r\n\r\n",
           "200 OK", TEXT, file("docs/note.txt"))


def test_dir_index(ctx):
    """Thư mục con có dấu / ở cuối thì phục vụ index.html của thư mục đó"""
    expect(ctx, "GET /docs/ HTTP/1.1\r\n\r\n", "200 OK", HTML, file("docs/index.html"))


def test_binary(ctx):
    """Tệp nhị phân .png"""
    expect(ctx, "GET /logo.png HTTP/1.1\r\n\r\n", "200 OK", "image/png", file("logo.png"))


def test_errors(ctx):
    """403 khi có '..', 405 khi không phải GET, 400 khi sai dòng đầu, 404 khi là thư mục"""
    expect(ctx, "GET /../secret.txt HTTP/1.1\r\n\r\n", "403 Forbidden", TEXT, b"Forbidden\n")
    expect(ctx, "POST / HTTP/1.1\r\nContent-Length: 0\r\n\r\n", "405 Method Not Allowed", TEXT,
           b"Method Not Allowed\n")
    expect(ctx, "HELLO\r\n\r\n", "400 Bad Request", TEXT, b"Bad Request\n")
    expect(ctx, "GET /docs HTTP/1.1\r\n\r\n", "404 Not Found", TEXT, b"Not Found\n")


def test_fragmented_request(ctx):
    """Yêu cầu đến thành nhiều mảnh nhỏ"""
    expect(ctx, "GET /docs/note.txt HTTP/1.1\r\nHost: localhost\r\nAccept: */*\r\n\r\n",
           "200 OK", TEXT, file("docs/note.txt"), slowly=True)


def test_sequential(ctx):
    """10 yêu cầu liên tiếp trên 10 kết nối"""
    for i in range(10):
        expect(ctx, f"GET /?lan={i} HTTP/1.1\r\n\r\n", "200 OK", HTML, file("index.html"))
        time.sleep(0.02)
