# Thiết kế: docs/TEST-DESIGN.md. Mô hình độc lập: kết quả lọc lấy từ suite_fly.search.
import re
import time
from urllib.parse import quote

import suite_fly as F
from njlib import BLOCKED, WA, Fail, cases, group, sample, timeout

HTML = "text/html; charset=utf-8"
TEXT = "text/plain; charset=utf-8"
HEADER_ROW = "<tr><th>Ma</th><th>Hang</th><th>Gio di</th><th>Gio den</th><th>Tong tien</th></tr>"
REASON = {200: "OK", 400: "Bad Request", 404: "Not Found", 405: "Method Not Allowed"}


def flights(ctx):
    return F.parse_flights(ctx.read_file("flights.txt"))


def fetch(ctx, raw, slowly=False, timeout_s=3.0):
    """Gửi yêu cầu, đọc phản hồi đến khi server đóng; trả về (mã, danh sách header, thân bytes). Kiểm tra khuôn phản hồi."""
    c = ctx.connect()
    if isinstance(raw, str):
        raw = raw.encode("latin-1")
    if slowly:
        c.send_slowly(raw, chunk=1, delay=0.001)
    else:
        c.send(raw)
    return read_response(c, timeout_s)


def read_response(c, timeout_s=3.0):
    data = c.recv_all_until_close(timeout=timeout_s)
    if b"\r\n\r\n" not in data:
        raise Fail(WA, f"phản hồi thiếu dòng trống \\r\\n\\r\\n: {data[:200]!r}")
    head, body = data.split(b"\r\n\r\n", 1)
    lines = head.decode("latin-1").split("\r\n")
    m = re.match(r"^HTTP/1\.1 ([0-9]{3}) (.+)$", lines[0])
    if not m:
        raise Fail(WA, f"dòng trạng thái sai: {lines[0]!r}")
    code = int(m.group(1))
    if len(lines) != 4 or not lines[1].startswith("Content-Type: ") or not lines[2].startswith("Content-Length: ") or lines[3] != "Connection: close":
        raise Fail(WA, f"header phải đúng 3 dòng Content-Type, Content-Length, Connection: close theo thứ tự; nhận {lines[1:]!r}")
    if lines[2] != f"Content-Length: {len(body)}":
        raise Fail(WA, f"Content-Length {lines[2]!r} nhưng thân dài {len(body)} byte")
    return code, lines, body


def expect_status(code, lines, body, want_code):
    if code != want_code:
        raise Fail(WA, f"mong đợi {want_code}, nhận {code}")
    if lines[0] != f"HTTP/1.1 {want_code} {REASON[want_code]}":
        raise Fail(WA, f"dòng trạng thái {lines[0]!r}")
    ctype = HTML if want_code == 200 else TEXT
    if lines[1] != f"Content-Type: {ctype}":
        raise Fail(WA, f"Content-Type {lines[1]!r}, mong đợi {ctype!r}")
    if want_code != 200 and body.decode("latin-1") != REASON[want_code] + "\n":
        raise Fail(WA, f"thân lỗi {body!r}")


def get(path):
    return f"GET {path} HTTP/1.1\r\nHost: localhost\r\nUser-Agent: test\r\n\r\n"


def post(path, body, extra="", clen=None):
    clen = len(body) if clen is None else clen
    return f"POST {path} HTTP/1.1\r\nHost: localhost\r\nContent-Type: application/x-www-form-urlencoded\r\nContent-Length: {clen}\r\n{extra}\r\n{body}"


def query(frm, to, d, pax, cls):
    return f"from={frm}&to={to}&date={d}&pax={pax}&class={cls}"


def check_results(ctx, body, frm, to, d, pax, cls):
    text = body.decode("latin-1")
    rows = F.search(flights(ctx), frm, to, d, str(pax), cls)
    want_rows = []
    for ln in rows:
        code, airline, dep, arr, total = ln.split(" ")
        want_rows.append(f"<tr><td>{code}</td><td>{airline}</td><td>{dep}</td><td>{arr}</td><td>{total}</td></tr>")
    if f"<h1>Co {len(rows)} chuyen</h1>" not in text:
        raise Fail(WA, f"thiếu '<h1>Co {len(rows)} chuyen</h1>'; thân {text[:200]!r}")
    got = re.findall(r"<tr>.*?</tr>", text, re.S)
    if got != [HEADER_ROW] + want_rows:
        raise Fail(WA, f"các dòng <tr> sai.\nMong đợi: {([HEADER_ROW] + want_rows)[:4]!r}\nNhận:      {got[:4]!r} (tổng {len(got)})")


def search_ok(ctx, frm, to, d, pax, cls, how="get"):
    q = query(frm, to, d, pax, cls)
    raw = get(f"/search?{q}") if how == "get" else post("/search", q)
    code, lines, body = fetch(ctx, raw)
    expect_status(code, lines, body, 200)
    check_results(ctx, body, frm, to, d, pax, cls)


def keys(ctx):
    return sorted({(f["from"], f["to"], f["date"]) for f in flights(ctx)})


# ---------------- sample ----------------

@sample
def test_index_form(ctx):
    """GET / trả trang form tìm kiếm"""
    code, lines, body = fetch(ctx, get("/"))
    expect_status(code, lines, body, 200)
    text = body.decode("latin-1")
    for need in ['<form action="/search" method="get">', 'name="from"', 'name="to"', 'name="date"', 'name="pax"', 'name="class"', '<input type="submit"']:
        if need not in text:
            raise Fail(WA, f"trang chủ thiếu {need!r}")


@sample
def test_search_get(ctx):
    """GET /search?... trả bảng chuyến bay đúng thứ tự trong tệp"""
    k = keys(ctx)[0]
    search_ok(ctx, k[0], k[1], k[2], 1, "ECO")
    search_ok(ctx, "HAN", "SGN", "2026-12-20", 2, "BUS")


@sample
def test_errors_and_flight(ctx):
    """404 / 405 / 400 và trang chi tiết chuyến"""
    f = flights(ctx)[0]
    code, lines, body = fetch(ctx, get(f"/flight/{f['code']}"))
    expect_status(code, lines, body, 200)
    text = body.decode("latin-1")
    for need in [f"<h1>{f['code']}</h1>", f"<p>{f['from']} -&gt; {f['to']} {f['date']} {f['dep']}-{f['arr']}</p>",
                 f"<p>ECO {f['eco_price']} ({f['eco_seats']} ghe)</p>", f"<p>BUS {f['bus_price']} ({f['bus_seats']} ghe)</p>"]:
        if need not in text:
            raise Fail(WA, f"trang chuyến thiếu {need!r}")
    for raw, want in [(get("/khong-co"), 404), (get("/flight/ZZ9999"), 404), ("DELETE / HTTP/1.1\r\n\r\n", 405), ("GET /\r\n\r\n", 400),
                      (get("/search"), 400)]:
        c, ln, b = fetch(ctx, raw)
        expect_status(c, ln, b, want)


# ---------------- basic ----------------

@group("basic")
def test_search_every_key_and_class(ctx):
    """Mọi (đi, đến, ngày) × hạng × số khách 1/4/9 khớp mô hình"""
    for k in keys(ctx):
        for cls in ("ECO", "BUS"):
            for pax in (1, 4, 9):
                search_ok(ctx, k[0], k[1], k[2], pax, cls)


@group("basic")
def test_post_search_same_results(ctx):
    """POST /search với thân dạng query cho cùng kết quả như GET"""
    for k in keys(ctx)[:25]:
        search_ok(ctx, k[0], k[1], k[2], 2, "ECO", how="post")
    search_ok(ctx, "HAN", "SGN", "2026-12-20", 1, "BUS", how="post")


@group("basic")
def test_flight_page_for_every_flight(ctx):
    for f in flights(ctx):
        code, lines, body = fetch(ctx, get(f"/flight/{f['code']}"))
        expect_status(code, lines, body, 200)
        if f"<h1>{f['code']}</h1>".encode() not in body or f"<p>ECO {f['eco_price']} ({f['eco_seats']} ghe)</p>".encode() not in body:
            raise Fail(WA, f"trang chuyến {f['code']} sai")


@group("basic")
@cases("/", "/?x=1", "/?from=HAN", "/?", title="GET {0} → trang chủ")
def test_index_variants(ctx, path):
    code, lines, body = fetch(ctx, get(path))
    expect_status(code, lines, body, 200)
    if b'<form action="/search" method="get">' not in body:
        raise Fail(WA, "không phải trang chủ")


@group("basic")
def test_param_order_extra_and_duplicates(ctx):
    """Thứ tự tham số tùy ý, khóa lạ bị bỏ qua, khóa lặp lấy lần đầu"""
    k = keys(ctx)[3]
    qs = [f"class=ECO&pax=1&date={k[2]}&to={k[1]}&from={k[0]}", f"from={k[0]}&to={k[1]}&date={k[2]}&pax=1&class=ECO&utm=1&x=%zz",
          f"from={k[0]}&from=XXX&to={k[1]}&to=ZZ&date={k[2]}&pax=1&pax=99&class=ECO&class=FIRST", f"&&from={k[0]}&&to={k[1]}&date={k[2]}&pax=1&class=ECO&"]
    for q in qs:
        code, lines, body = fetch(ctx, get(f"/search?{q}"))
        if "x=%zz" in q:
            expect_status(code, lines, body, 400)  # % hỏng ở khóa/giá trị bị đọc là 400 dù khóa lạ
            continue
        expect_status(code, lines, body, 200)
        check_results(ctx, body, k[0], k[1], k[2], 1, "ECO")


@group("basic")
def test_http10_and_headers_ignored(ctx):
    """HTTP/1.0, nhiều header, tên header tùy ý hoa/thường"""
    k = keys(ctx)[1]
    raw = f"GET /search?{query(k[0], k[1], k[2], 1, 'ECO')} HTTP/1.0\r\nhost: x\r\nX-Foo: bar\r\nAccept: */*\r\n\r\n"
    code, lines, body = fetch(ctx, raw)
    expect_status(code, lines, body, 200)
    check_results(ctx, body, k[0], k[1], k[2], 1, "ECO")


# ---------------- edge ----------------

@group("edge")
@cases("from=HAN&to=SGN&date=2026-12-20&pax=1", "from=HAN&to=SGN&date=2026-12-20&class=ECO", "from=HAN&to=SGN&pax=1&class=ECO",
       "from=HAN&date=2026-12-20&pax=1&class=ECO", "to=SGN&date=2026-12-20&pax=1&class=ECO", "", "from=&to=SGN&date=2026-12-20&pax=1&class=ECO",
       "from=han&to=SGN&date=2026-12-20&pax=1&class=ECO", "from=HAN&to=HAN&date=2026-12-20&pax=1&class=ECO", "from=HANN&to=SGN&date=2026-12-20&pax=1&class=ECO",
       "from=HAN&to=SGN&date=2026-02-30&pax=1&class=ECO", "from=HAN&to=SGN&date=2026-12-2&pax=1&class=ECO", "from=HAN&to=SGN&date=2026-12-20&pax=0&class=ECO",
       "from=HAN&to=SGN&date=2026-12-20&pax=10&class=ECO", "from=HAN&to=SGN&date=2026-12-20&pax=01&class=ECO", "from=HAN&to=SGN&date=2026-12-20&pax=a&class=ECO",
       "from=HAN&to=SGN&date=2026-12-20&pax=1&class=eco", "from=HAN&to=SGN&date=2026-12-20&pax=1&class=FIRST", "from=HAN&to=SGN&date=2026-12-20&pax=1&class=",
       "from=H%GAN&to=SGN&date=2026-12-20&pax=1&class=ECO", "from=HAN&to=SGN&date=2026-12-20&pax=1&class=EC%", "from=HAN&to=SGN&date=2026-12-20&pax=1&class=ECO%1",
       "from=HAN&to=SGN&date=2100-02-29&pax=1&class=ECO", "from=HAN&to=SGN&date=1899-12-31&pax=1&class=ECO", title="Query sai {0!r:.60} → 400")
def test_bad_queries(ctx, q):
    for raw in (get(f"/search?{q}"), post("/search", q)):
        code, lines, body = fetch(ctx, raw)
        expect_status(code, lines, body, 400)


@group("edge")
@cases(("from=H%41N&to=S%47N&date=2026%2D12%2D20&pax=%31&class=E%43O", "ECO"), ("from=HAN&to=SGN&date=2026-12-20&pax=1&class=BUS", "BUS"),
       ("from=%48%41%4e&to=%53%47%4E&date=2026-12-20&pax=2&class=ECO", "ECO"), title="Giải mã phần trăm {0!r:.60}")
def test_percent_decoding(ctx, q, cls):
    code, lines, body = fetch(ctx, get(f"/search?{q}"))
    expect_status(code, lines, body, 200)
    pax = 2 if "pax=2" in q else 1
    check_results(ctx, body, "HAN", "SGN", "2026-12-20", pax, cls)


@group("edge")
def test_plus_is_space_invalid(ctx):
    """'+' giải mã thành dấu cách nên giá trị không còn hợp lệ → 400"""
    code, lines, body = fetch(ctx, get("/search?from=HAN&to=SGN&date=2026-12-20&pax=1&class=E+O"))
    expect_status(code, lines, body, 400)


@group("edge")
@cases(("GET /search?from=HAN HTTP/2\r\n\r\n", 400), ("GET / HTTP/1.2\r\n\r\n", 400), ("GET / http/1.1\r\n\r\n", 400), ("GET /\r\n\r\n", 400),
       ("GET\r\n\r\n", 400), ("\r\n\r\n", 400), ("GET  / HTTP/1.1\r\n\r\n", 400), ("GET / HTTP/1.1 x\r\n\r\n", 400), ("get / HTTP/1.1\r\n\r\n", 405),
       ("HEAD / HTTP/1.1\r\n\r\n", 405), ("PUT /search HTTP/1.1\r\n\r\n", 405), ("DELETE / HTTP/1.1\r\n\r\n", 405), ("OPTIONS * HTTP/1.1\r\n\r\n", 405),
       ("GET /index.html HTTP/1.1\r\n\r\n", 404), ("GET /search/ HTTP/1.1\r\n\r\n", 404), ("GET /flight HTTP/1.1\r\n\r\n", 404), ("GET /flight/ HTTP/1.1\r\n\r\n", 404),
       ("GET /Flight/VN1 HTTP/1.1\r\n\r\n", 404), ("GET //search HTTP/1.1\r\n\r\n", 404), ("POST /khac HTTP/1.1\r\nContent-Length: 0\r\n\r\n", 404),
       ("POST / HTTP/1.1\r\nContent-Length: 0\r\n\r\n", 404), title="Yêu cầu {0!r:.50} → {1}")
def test_status_codes(ctx, raw, want):
    code, lines, body = fetch(ctx, raw)
    expect_status(code, lines, body, want)


@group("edge")
@cases("", "Content-Length: abc\r\n", "Content-Length: -1\r\n", "Content-Length: 4097\r\n", "Content-Length:\r\n", title="POST /search Content-Length lạ {0!r} → 400")
def test_post_bad_content_length(ctx, hdr):
    q = query("HAN", "SGN", "2026-12-20", 1, "ECO")
    raw = f"POST /search HTTP/1.1\r\nHost: x\r\n{hdr}\r\n{q}"
    code, lines, body = fetch(ctx, raw)
    expect_status(code, lines, body, 400)


@group("edge")
def test_post_header_case_and_spacing(ctx):
    q = query("HAN", "SGN", "2026-12-20", 2, "ECO")
    for hdr in [f"content-length: {len(q)}", f"CONTENT-LENGTH:{len(q)}", f"Content-length:   {len(q)}"]:
        raw = f"POST /search HTTP/1.1\r\nHost: x\r\n{hdr}\r\n\r\n{q}"
        code, lines, body = fetch(ctx, raw)
        expect_status(code, lines, body, 200)
        check_results(ctx, body, "HAN", "SGN", "2026-12-20", 2, "ECO")


@group("edge")
def test_post_uses_body_not_target_query(ctx):
    """POST: tham số lấy từ thân; query trong target bị bỏ qua"""
    q = query("HAN", "SGN", "2026-12-20", 1, "ECO")
    code, lines, body = fetch(ctx, post("/search?from=XXX", q))
    expect_status(code, lines, body, 200)
    check_results(ctx, body, "HAN", "SGN", "2026-12-20", 1, "ECO")


@group("edge")
def test_post_body_longer_than_content_length(ctx):
    """Dữ liệu thừa sau Content-Length bị bỏ qua"""
    q = query("HAN", "SGN", "2026-12-20", 1, "ECO")
    code, lines, body = fetch(ctx, post("/search", q + "&x=%G1", clen=len(q)))
    expect_status(code, lines, body, 200)
    check_results(ctx, body, "HAN", "SGN", "2026-12-20", 1, "ECO")


@group("edge")
def test_post_4096_body(ctx):
    """Thân 4096 byte (đệm bằng khóa lạ) vẫn được đọc đủ"""
    q = query("HAN", "SGN", "2026-12-20", 1, "ECO")
    q += "&pad=" + "x" * (4096 - len(q) - 5)
    code, lines, body = fetch(ctx, post("/search", q))
    expect_status(code, lines, body, 200)
    check_results(ctx, body, "HAN", "SGN", "2026-12-20", 1, "ECO")


# ---------------- stream ----------------

@group("stream")
def test_byte_by_byte_get(ctx):
    k = keys(ctx)[2]
    code, lines, body = fetch(ctx, get(f"/search?{query(k[0], k[1], k[2], 1, 'ECO')}"), slowly=True)
    expect_status(code, lines, body, 200)
    check_results(ctx, body, k[0], k[1], k[2], 1, "ECO")


@group("stream")
def test_split_inside_blank_line(ctx):
    """Yêu cầu bị cắt giữa \\r\\n\\r\\n"""
    c = ctx.connect()
    c.send("GET / HTTP/1.1\r\nHost: a\r\n\r")
    time.sleep(0.1)
    c.send("\n")
    code, lines, body = read_response(c)
    expect_status(code, lines, body, 200)


@group("stream")
def test_post_body_arrives_later(ctx):
    """Header POST đến trước, thân đến sau (từng mảnh nhỏ)"""
    q = query("HAN", "SGN", "2026-12-20", 3, "ECO")
    c = ctx.connect()
    c.send(f"POST /search HTTP/1.1\r\nHost: x\r\nContent-Length: {len(q)}\r\n\r\n")
    time.sleep(0.15)
    c.send_chunks(q, ctx.rng, min_chunk=1, max_chunk=5, delay=0.003)
    code, lines, body = read_response(c)
    expect_status(code, lines, body, 200)
    check_results(ctx, body, "HAN", "SGN", "2026-12-20", 3, "ECO")


@group("stream")
def test_post_body_in_same_segment_as_header(ctx):
    q = query("SGN", "HAN", "2026-12-21", 1, "ECO")
    code, lines, body = fetch(ctx, post("/search", q))
    expect_status(code, lines, body, 200)
    check_results(ctx, body, "SGN", "HAN", "2026-12-21", 1, "ECO")


@group("stream")
def test_random_chunks(ctx):
    k = keys(ctx)[5]
    c = ctx.connect()
    c.send_chunks(get(f"/search?{query(k[0], k[1], k[2], 2, 'BUS')}"), ctx.rng, delay=0.001)
    code, lines, body = read_response(c)
    expect_status(code, lines, body, 200)
    check_results(ctx, body, k[0], k[1], k[2], 2, "BUS")


# ---------------- robust ----------------

@group("robust")
def test_close_before_request_complete(ctx):
    """Client đóng/RST khi chưa gửi xong: server vẫn sống"""
    for how in ("close", "reset"):
        c = ctx.connect()
        c.send("GET /search?from=HA")
        c.close() if how == "close" else c.reset()
    c = ctx.connect()
    c.send("POST /search HTTP/1.1\r\nContent-Length: 100\r\n\r\nfrom=H")
    c.reset()
    time.sleep(0.2)
    ctx.expect_alive()
    code, lines, body = fetch(ctx, get("/"))
    expect_status(code, lines, body, 200)


@group("robust")
@timeout(20)
def test_client_closes_before_reply(ctx):
    """Client gửi đủ yêu cầu rồi đóng ngay, không đọc: server gửi vào kết nối đã đóng mà không chết (30 lần)"""
    k = keys(ctx)[0]
    for i in range(30):
        c = ctx.connect(f"c{i}")
        c.send(get(f"/search?{query(k[0], k[1], k[2], 1, 'ECO')}") * (1 if i % 2 else 1))
        c.close()
        ctx.close_quietly(c)
        time.sleep(0.01)
    time.sleep(0.3)
    ctx.expect_alive()
    search_ok(ctx, k[0], k[1], k[2], 1, "ECO")


@group("robust")
def test_oversized_header(ctx):
    """Quá 8 KB mà chưa có \\r\\n\\r\\n → 400"""
    c = ctx.connect()
    c.send("GET / HTTP/1.1\r\nX-Pad: " + "a" * 9000)
    code, lines, body = read_response(c)
    expect_status(code, lines, body, 400)


@group("robust")
def test_binary_garbage(ctx):
    for junk in [b"\x01\x02\x03\r\n\r\n", b"\xff\xfe GET\r\n\r\n", b"GET /\x01 HTTP/1.1\r\n\r\n"]:
        c = ctx.connect()
        c.send(junk)
        try:
            data = c.recv_all_until_close(timeout=2.0)
        except Fail:
            raise
        if data and not data.startswith(b"HTTP/1.1 4"):
            raise Fail(WA, f"byte lạ {junk!r}: nhận {data[:60]!r}")
    ctx.expect_alive()


@group("robust")
@timeout(25)
def test_300_requests(ctx):
    """300 yêu cầu liên tiếp (xen kẽ trang chủ, tìm kiếm, 404, đóng sớm): không rò fd"""
    for i in range(300):
        if i % 5 == 4:
            c = ctx.connect()
            c.send("GET /")
            c.close()
            ctx.close_quietly(c)
            continue
        raw = [get("/"), get("/khong"), get("/search?" + query("HAN", "SGN", "2026-12-20", 1, "ECO")), get("/flight/ZZ")][i % 4]
        code, lines, body = fetch(ctx, raw)
        if code not in (200, 404):
            raise Fail(WA, f"mã {code}")
    code, lines, body = fetch(ctx, get("/"))
    expect_status(code, lines, body, 200)


# ---------------- concurrency ----------------

@group("concurrency")
def test_silent_and_slow_clients_do_not_block(ctx):
    """Kết nối im lặng, gửi dở, gửi chậm không làm client khác chờ"""
    idle = [ctx.connect(f"idle{i}") for i in range(5)]
    idle[0].send("GET /search?from=HA")
    slow = ctx.connect("slow")
    slow.send("POST /search HTTP/1.1\r\nContent-Length: 60\r\n\r\nfrom=HAN")
    with ctx.verdict(BLOCKED):
        k = keys(ctx)[0]
        search_ok(ctx, k[0], k[1], k[2], 1, "ECO")
        code, lines, body = fetch(ctx, get("/"))
        expect_status(code, lines, body, 200)
    idle[0].send("N&to=SGN HTTP/1.1\r\n\r\n")
    code, lines, body = read_response(idle[0])
    expect_status(code, lines, body, 400)


@group("concurrency")
@timeout(20)
def test_30_parallel_requests(ctx):
    """30 kết nối cùng lúc, gửi yêu cầu rồi mới đọc: mỗi bên nhận đúng phản hồi của mình"""
    cs, wants = [], []
    ks = keys(ctx)
    for i in range(30):
        c = ctx.connect(f"c{i}")
        k = ks[i % len(ks)]
        c.send(get(f"/search?{query(k[0], k[1], k[2], 1 + i % 3, 'ECO')}"))
        cs.append(c)
        wants.append((k, 1 + i % 3))
    for c, (k, pax) in zip(cs, wants):
        code, lines, body = read_response(c)
        expect_status(code, lines, body, 200)
        check_results(ctx, body, k[0], k[1], k[2], pax, "ECO")


# ---------------- stress ----------------

@group("stress")
@timeout(40)
def test_random_requests_vs_model(ctx):
    """600 yêu cầu ngẫu nhiên (GET/POST, hợp lệ/sai, trang chi tiết) so với mô hình"""
    rng = ctx.rng
    ks = keys(ctx)
    fl = flights(ctx)
    for _ in range(600):
        r = rng.random()
        if r < 0.5:
            k = rng.choice(ks)
            pax, cls = rng.randint(1, 9), rng.choice(["ECO", "BUS"])
            search_ok(ctx, k[0], k[1], k[2], pax, cls, how=rng.choice(["get", "post"]))
        elif r < 0.65:
            q = rng.choice(["from=HAN&to=SGN", query("HAN", "HAN", "2026-12-20", 1, "ECO"), query("HAN", "SGN", "2026-12-20", 0, "ECO"),
                            query("HAN", "SGN", "2026-13-20", 1, "ECO"), query("HAN", "SGN", "2026-12-20", 1, "ECO") + "&x=%G1"])
            code, lines, body = fetch(ctx, get("/search?" + q))
            expect_status(code, lines, body, 400)
        elif r < 0.85:
            f = rng.choice(fl)
            code, lines, body = fetch(ctx, get(f"/flight/{f['code']}"))
            expect_status(code, lines, body, 200)
        else:
            code, lines, body = fetch(ctx, get(rng.choice(["/x", "/flight/Q", "/search/a", "/flight/" + quote("a b")])))
            expect_status(code, lines, body, 404)
