from njlib import Fail, WA, expects_exit, sample

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


@expects_exit
def test_byte_by_byte(ctx):
    """Gửi từng byte một"""
    c = ctx.connect()
    c.send_slowly("hello " + PHRASE, chunk=1, delay=0.01)
    _done(ctx, c)


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


@expects_exit
def test_almost(ctx):
    """Gần đúng nhưng không đủ chuỗi, client đóng thì server không gửi BYE"""
    c = ctx.connect()
    c.send("ky thuat may tinh | Ky thuatMay tinh | Ky thuat May")
    c.expect_silence(0.3)
    c.sock.shutdown(1)  # SHUT_WR: báo hết dữ liệu
    c.expect_closed(timeout=1.0)
