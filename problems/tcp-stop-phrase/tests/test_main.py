import time

from njlib import Fail, WA, cases, expects_exit, group, sample, timeout

PHRASE = "Ky thuat May tinh"


def _done(ctx, c):
    c.expect_line("BYE")
    c.expect_closed()
    try:
        code = ctx.server.proc.wait(timeout=1)
    except Exception:
        raise Fail(WA, "server phải kết thúc sau khi gửi BYE")
    if code != 0:
        raise Fail(WA, f"server phải thoát với mã 0, nhận được {code}")


@sample
@expects_exit
def test_whole(ctx):
    """Chuỗi dừng đến trong một lần gửi"""
    c = ctx.connect()
    c.send(PHRASE)
    _done(ctx, c)


@sample
@expects_exit
def test_two_pieces(ctx):
    """Chuỗi dừng bị cắt làm hai"""
    c = ctx.connect()
    c.send("Ky th")
    c.expect_silence(0.2)
    c.send("uat May tinh")
    _done(ctx, c)


@group("stream")
@expects_exit
def test_byte_by_byte(ctx):
    """Gửi từng byte một"""
    c = ctx.connect()
    c.send_slowly("hello " + PHRASE, chunk=1, delay=0.01)
    _done(ctx, c)


@group("basic")
@expects_exit
def test_noise_before(ctx):
    """Có dữ liệu khác trước chuỗi dừng, không được trả lời sớm"""
    c = ctx.connect()
    # Lưu ý: các mảnh ghép lại cũng KHÔNG được chứa chuỗi dừng ("Ky thuat\nMay tinh" ≠ PHRASE).
    for piece in ["xin chao\n", "Ky thuat\n", "May tinh la nganh hay\n", "Ky thuat May"]:
        c.send(piece)
        c.expect_silence(0.1)
    c.send(" tinh")
    _done(ctx, c)


@group("edge")
@expects_exit
def test_after_large_data(ctx):
    """Chuỗi dừng nằm sau 20 KB dữ liệu và vắt qua ranh giới bộ đệm"""
    c = ctx.connect()
    filler = ("abcdefghij" * 2000) + "Ky thuat May tin"
    for i in range(0, len(filler), 1000):
        c.send(filler[i:i + 1000])
    c.expect_silence(0.2)
    c.send("h")
    _done(ctx, c)


@group("basic")
@expects_exit
def test_almost(ctx):
    """Gần đúng nhưng không đủ chuỗi, client đóng thì server không gửi BYE"""
    c = ctx.connect()
    c.send("ky thuat may tinh | Ky thuatMay tinh | Ky thuat May")
    c.expect_silence(0.3)
    c.sock.shutdown(1)  # SHUT_WR: báo hết dữ liệu
    c.expect_closed(timeout=1.0)


# ======================= phần mở rộng (thiết kế lại) =======================

@group("stream")
@expects_exit
@cases(*range(1, len(PHRASE)), title="Chuỗi dừng bị cắt sau ký tự thứ {0}")
def test_split_everywhere(ctx, k):
    c = ctx.connect()
    c.send("abc " + PHRASE[:k])
    c.expect_silence(0.08)
    c.send(PHRASE[k:])
    _done(ctx, c)


@group("edge")
@expects_exit
@cases("Ky thuat Ky thuat May tinh", "KKy thuat May tinh", "Ky thuat May Ky thuat May tinh",
       "Ky thuat May tinKy thuat May tinh", "Ky Ky Ky thuat May tinh",
       title="Tiền tố chồng lấn: {0!r}")
def test_overlapping_prefix(ctx, text):
    c = ctx.connect()
    c.send_slowly(text, chunk=3, delay=0.005)
    _done(ctx, c)


@group("edge")
@expects_exit
def test_nul_bytes_before(ctx):
    """Có byte 0x00 trước chuỗi dừng (strstr dừng ở 0x00)"""
    c = ctx.connect()
    c.send(b"rac\x00\x00nhi phan\xff\x00")
    c.expect_silence(0.1)
    c.send(PHRASE.encode())
    _done(ctx, c)


@group("edge")
@expects_exit
def test_nul_inside_almost(ctx):
    """Chuỗi bị chèn byte 0x00 ở giữa thì KHÔNG phải chuỗi dừng"""
    c = ctx.connect()
    c.send(b"Ky thuat\x00May tinh")
    c.expect_silence(0.2)
    c.shutdown_write()
    c.expect_closed(timeout=1.0)


@group("edge")
@expects_exit
def test_data_after_phrase(ctx):
    """Chuỗi dừng có dữ liệu khác dính phía sau trong cùng lần gửi: vẫn chỉ một BYE"""
    c = ctx.connect()
    c.send(PHRASE + " va con nua\n" + PHRASE)
    _done(ctx, c)


@group("edge")
@expects_exit
@cases("ky thuat may tinh", "Ky thuat May tinh"[:-1], "Ky  thuat May tinh", "Ky thuat May\ttinh", "KY THUAT MAY TINH",
       title="Gần đúng {0!r}: không có BYE")
def test_near_misses(ctx, text):
    c = ctx.connect()
    c.send(text)
    c.expect_silence(0.2)
    c.shutdown_write()
    c.expect_closed(timeout=1.0)


@group("robust")
@expects_exit
def test_reset_without_phrase(ctx):
    """Client RST khi chưa gửi chuỗi dừng: server đóng và thoát bình thường (không treo, không crash)"""
    c = ctx.connect()
    c.send("chua du")
    time.sleep(0.05)
    c.reset()
    try:
        ctx.server.proc.wait(timeout=1.5)
    except Exception:
        raise Fail(WA, "client đã RST nhưng server vẫn chưa kết thúc")
    if ctx.server.proc.returncode < 0:
        raise Fail(WA, f"server bị dừng bởi tín hiệu {-ctx.server.proc.returncode}")


@group("stress")
@expects_exit
@timeout(12)
def test_phrase_after_2mb(ctx):
    """Chuỗi dừng nằm sau 2 MB dữ liệu (bộ đệm cố định gom hết dữ liệu sẽ tràn)"""
    c = ctx.connect()
    filler = (b"Ky thuat May tin" + b"x" * 47) * (2 * 1024 * 1024 // 63)
    for i in range(0, len(filler), 65536):
        c.send(filler[i:i + 65536])
    c.expect_silence(0.2)
    c.send(b"Ky thuat May tinh")
    _done(ctx, c)


@group("stress")
@expects_exit
@timeout(12)
def test_random_fragments_long(ctx):
    """200 KB dữ liệu gần giống (nhiều tiền tố) cắt mảnh ngẫu nhiên, rồi chuỗi dừng cũng bị cắt ngẫu nhiên"""
    rng = ctx.rng
    c = ctx.connect()
    noise = "".join(rng.choice(["Ky ", "thuat ", "May ", "tin", "Ky thuat May ", "h", " "]) for _ in range(40000))
    noise = noise.replace(PHRASE, "Ky thuat May_tinh")
    while PHRASE in noise + PHRASE[:-1]:
        noise = noise.replace(PHRASE, "Ky thuat May_tinh")
        break
    c.send_chunks(noise, rng, 1, 400, delay=0)
    c.expect_silence(0.2)
    c.send_chunks(PHRASE, rng, 1, 4, delay=0.01)
    _done(ctx, c)
