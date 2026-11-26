# Thiết kế: docs/TEST-DESIGN.md. Bộ chấm đóng vai server FLY và người dùng gõ phím.
import socket
import time

from njlib import WA, Fail, cases, group, sample, timeout


class Run:
    def __init__(self, ctx, welcome="100 OK WELCOME"):
        self.ctx = ctx
        srv = ctx.mock_server()
        self.cli = ctx.run_client("127.0.0.1", srv.port)
        self.conn = srv.accept(timeout=3.0)
        self.pos = 0
        if welcome is not None:
            self.conn.send_line(welcome)

    def type(self, *lines):
        for ln in lines:
            self.cli.write(ln + "\n")

    def sent(self, want, timeout=2.0):
        self.conn.expect_line(want, timeout=timeout)

    def serve(self, *lines):
        for ln in lines:
            self.conn.send_line(ln)

    def see(self, text, timeout=2.0):
        """Chờ tới khi stdout (kể từ lần `see` trước) chứa `text`; đánh dấu đã đọc tới đó."""
        deadline = time.monotonic() + timeout
        while True:
            out = self.cli.stdout()
            i = out.find(text, self.pos)
            if i >= 0:
                self.pos = i + len(text)
                return
            if time.monotonic() >= deadline:
                raise Fail(WA, f"stdout chưa có {text!r} (sau vị trí đã đọc); hiện có ...{out[self.pos:][-300:]!r}")
            time.sleep(0.02)

    def finish_quit(self):
        self.type("5")
        self.sent("QUIT")
        self.conn.send_line("100 OK")
        code = self.cli.wait(timeout=3)
        if code != 0:
            raise Fail(WA, f"client phải thoát mã 0, nhận được {code}")


def login(r, user="an", pw="1234", ok=True):
    r.type("1", user, pw)
    r.sent(f"LOGIN {user} {pw}")
    if ok:
        r.serve(f"100 OK {user}")
        r.see(f"Xin chao {user}\n")


FLIGHTS = ["VN213 VN 06:00 08:10 2500000", "VJ123 VJ 23:30 01:35 1780000", "QH777 QH 09:00 11:05 2200000"]


# ---------------- sample ----------------

@sample
def test_login_and_search(ctx):
    """Chọn 1 đăng nhập, chọn 2 tìm chuyến: client hỏi từng thông tin và gửi lệnh đúng"""
    r = Run(ctx)
    login(r)
    r.type("2", "HAN", "SGN", "2026-12-20", "2", "ECO")
    r.sent("SEARCH HAN SGN 2026-12-20 2 ECO")
    r.serve("110 FLIGHTS 3", *FLIGHTS)
    r.see("Co 3 chuyen:\n")
    r.see("1. VN213 VN 06:00-08:10 2500000\n")
    r.see("2. VJ123 VJ 23:30-01:35 1780000\n")
    r.see("3. QH777 QH 09:00-11:05 2200000\n")
    r.finish_quit()


@sample
def test_notification_while_idle(ctx):
    """Server gửi 301 NOTIFY khi client đang chờ người dùng gõ: in ngay [THONG BAO]"""
    r = Run(ctx)
    r.serve("301 NOTIFY DELAY VN100 45")
    r.see("[THONG BAO] DELAY VN100 45\n", timeout=1.0)
    r.serve("301 NOTIFY CANCEL VN200", "301 NOTIFY RESCHEDULE VN300 2026-12-21 09:00 11:00")
    r.see("[THONG BAO] CANCEL VN200\n", timeout=1.0)
    r.see("[THONG BAO] RESCHEDULE VN300 2026-12-21 09:00 11:00\n", timeout=1.0)


@sample
def test_book_and_pay_wallet(ctx):
    """Chọn 3 đặt vé rồi thanh toán bằng ví"""
    r = Run(ctx)
    login(r)
    r.type("3", "VN213", "2026-12-20", "ECO", "2")
    r.sent("BOOK VN213 2026-12-20 ECO 2")
    r.serve("100 OK HOLD K3F9QX 2500000 14:03:27")
    r.see("Giu cho thanh cong. Ma: K3F9QX So tien: 2500000 Han: 14:03:27\n")
    r.type("1")
    r.sent("PAY K3F9QX WALLET")
    r.serve("100 OK PAID K3F9QX")
    r.see("Da thanh toan K3F9QX\n")
    r.finish_quit()


# ---------------- basic ----------------

@group("basic")
@cases("203 DENIED", "201 INVALID", "207 ALREADY LOGGED IN", "999 UNKNOWN ERROR", title="Đăng nhập lỗi {0}: in 'Loi: ...'")
def test_login_error(ctx, line):
    r = Run(ctx)
    r.type("1", "an", "sai")
    r.sent("LOGIN an sai")
    r.serve(line)
    r.see(f"Loi: {line}\n")
    r.type("5")
    r.sent("QUIT")


@group("basic")
def test_search_empty_and_error(ctx):
    r = Run(ctx)
    r.type("2", "HAN", "SGN", "2026-12-20", "9", "BUS")
    r.sent("SEARCH HAN SGN 2026-12-20 9 BUS")
    r.serve("110 FLIGHTS 0")
    r.see("Co 0 chuyen:\n")
    r.type("2", "HAN", "HAN", "x", "0", "eco")
    r.sent("SEARCH HAN HAN x 0 eco")
    r.serve("201 INVALID")
    r.see("Loi: 201 INVALID\n")


@group("basic")
def test_values_sent_verbatim(ctx):
    """Giá trị gõ vào được gửi nguyên văn (kể cả ký tự đặc biệt), không kiểm tra phía client"""
    r = Run(ctx)
    r.type("1", "A~b!c", "p@ss w0rd")
    r.sent("LOGIN A~b!c p@ss w0rd")
    r.serve("203 DENIED")
    r.see("Loi: 203 DENIED\n")
    r.type("3", "", "", "", "")
    r.sent("BOOK    ")
    r.serve("201 INVALID")
    r.see("Loi: 201 INVALID\n")


@group("basic")
def test_book_pay_card(ctx):
    """Thanh toán thẻ: hỏi số thẻ, hạn, CVV rồi gửi PAY ... CARD"""
    r = Run(ctx)
    r.type("3", "QH77", "2026-12-21", "BUS", "1")
    r.sent("BOOK QH77 2026-12-21 BUS 1")
    r.serve("100 OK HOLD AB12CD 3100000 09:15:00")
    r.see("Giu cho thanh cong. Ma: AB12CD So tien: 3100000 Han: 09:15:00\n")
    r.type("2", "4111111111111111", "12/99", "123")
    r.sent("PAY AB12CD CARD 4111111111111111 12/99 123")
    r.serve("206 PAYMENT FAILED")
    r.see("Loi: 206 PAYMENT FAILED\n")
    r.finish_quit()


@group("basic")
@cases("0", "x", "", "9", "3 ", title="Không thanh toán: nhập {0!r} → 'Chua thanh toan', không gửi gì")
def test_skip_payment(ctx, answer):
    r = Run(ctx)
    r.type("3", "VN1", "2026-12-20", "ECO", "1")
    r.sent("BOOK VN1 2026-12-20 ECO 1")
    r.serve("100 OK HOLD ZZ99ZZ 1000000 10:00:00")
    r.see("Giu cho thanh cong")
    r.type(answer)
    r.see("Chua thanh toan\n")
    r.conn.expect_silence(0.2)
    r.finish_quit()


@group("basic")
def test_book_error_no_payment_prompt(ctx):
    """BOOK lỗi: in 'Loi:' và quay về menu (dòng gõ tiếp theo là lựa chọn menu, không phải câu trả lời thanh toán)"""
    r = Run(ctx)
    r.type("3", "VN1", "2026-12-20", "ECO", "5")
    r.sent("BOOK VN1 2026-12-20 ECO 5")
    r.serve("205 NO SEATS")
    r.see("Loi: 205 NO SEATS\n")
    r.type("4")
    r.sent("MYTICKETS")
    r.serve("110 TICKETS 0")
    r.see("Ban co 0 ve:\n")


@group("basic")
def test_my_tickets(ctx):
    r = Run(ctx)
    r.type("4")
    r.sent("MYTICKETS")
    r.serve("110 TICKETS 3", "7380000000001 VN100 2026-12-20 ECO NGUYEN_VAN_AN 1000000 PAID",
            "7380000000002 VJ200 2026-12-22 BUS TRAN_THI_BINH 2500000 CANCELLED", "7380000000003 QH300 2026-12-25 ECO LE_VAN_C 900000 PAID")
    r.see("Ban co 3 ve:\n")
    r.see("1. 7380000000001 VN100 2026-12-20 ECO PAID\n")
    r.see("2. 7380000000002 VJ200 2026-12-22 BUS CANCELLED\n")
    r.see("3. 7380000000003 QH300 2026-12-25 ECO PAID\n")
    r.type("4")
    r.sent("MYTICKETS")
    r.serve("204 LOGIN FIRST")
    r.see("Loi: 204 LOGIN FIRST\n")


@group("basic")
def test_quit_flow(ctx):
    """Chọn 5: gửi QUIT, chờ 100 OK, thoát mã 0"""
    r = Run(ctx)
    r.finish_quit()


@group("basic")
@cases("0", "6", "x", "", "12", "1 ", " 1", "-1", "QUIT", title="Lựa chọn menu không hợp lệ {0!r}")
def test_invalid_menu_choice(ctx, choice):
    r = Run(ctx)
    r.type(choice)
    r.see("Lua chon khong hop le\n")
    r.conn.expect_silence(0.2)
    login(r)


@group("basic")
def test_stdin_eof_sends_quit(ctx):
    """stdin kết thúc: gửi QUIT rồi thoát mã 0"""
    r = Run(ctx)
    login(r)
    r.cli.close_stdin()
    r.sent("QUIT")
    if r.cli.wait(timeout=3) != 0:
        raise Fail(WA, "mong đợi mã thoát 0")


@group("basic")
def test_eof_in_the_middle_of_a_question(ctx):
    """stdin kết thúc giữa lúc hỏi: vẫn gửi QUIT và thoát mã 0, không gửi lệnh dở"""
    r = Run(ctx)
    r.type("1", "an")
    r.cli.close_stdin()
    r.sent("QUIT")
    if r.cli.wait(timeout=3) != 0:
        raise Fail(WA, "mong đợi mã thoát 0")


# ---------------- stream (phản hồi và gõ phím bị cắt vụn) ----------------

@group("stream")
def test_server_replies_byte_by_byte(ctx):
    r = Run(ctx, welcome=None)
    r.conn.send_slowly(b"100 OK WELCOME\n", chunk=1, delay=0.002)
    r.type("2", "HAN", "SGN", "2026-12-20", "1", "ECO")
    r.sent("SEARCH HAN SGN 2026-12-20 1 ECO")
    r.conn.send_slowly(("110 FLIGHTS 3\n" + "".join(x + "\n" for x in FLIGHTS)).encode(), chunk=1, delay=0.002)
    r.see("Co 3 chuyen:\n")
    r.see("3. QH777 QH 09:00-11:05 2200000\n")


@group("stream")
def test_multiline_reply_glued_with_notifications(ctx):
    """Phản hồi nhiều dòng dính liền thông báo trong một lần gửi: đúng thứ tự, không mất dòng nào"""
    r = Run(ctx)
    r.type("2", "HAN", "SGN", "2026-12-20", "1", "ECO")
    r.sent("SEARCH HAN SGN 2026-12-20 1 ECO")
    r.conn.send(("301 NOTIFY DELAY VN1 5\n110 FLIGHTS 2\n" + FLIGHTS[0] + "\n301 NOTIFY CANCEL VN2\n" + FLIGHTS[1] + "\n301 NOTIFY DELAY VN3 9\n").encode())
    r.see("[THONG BAO] DELAY VN1 5\n")
    r.see("Co 2 chuyen:\n")
    r.see("[THONG BAO] CANCEL VN2\n")
    r.see("2. VJ123 VJ 23:30-01:35 1780000\n")
    r.see("[THONG BAO] DELAY VN3 9\n")


@group("stream")
def test_user_types_byte_by_byte(ctx):
    """Người dùng gõ từng phím"""
    r = Run(ctx)
    for ch in "1\nan\n1234\n":
        r.cli.write(ch)
        time.sleep(0.01)
    r.sent("LOGIN an 1234")
    r.serve("100 OK an")
    r.see("Xin chao an\n")


@group("stream")
def test_crlf_replies_and_input(ctx):
    """Phản hồi kết thúc \\r\\n; người dùng gõ \\r\\n"""
    r = Run(ctx, welcome=None)
    r.conn.send(b"100 OK WELCOME\r\n")
    r.cli.write("1\r\nan\r\n1234\r\n")
    r.sent("LOGIN an 1234")
    r.conn.send(b"100 OK an\r\n")
    r.see("Xin chao an\n")


@group("stream")
def test_all_inputs_in_one_write(ctx):
    """Người dùng dán sẵn nhiều dòng một lúc (stdin có sẵn dữ liệu trong bộ đệm): client xử lý lần lượt, không bỏ sót"""
    r = Run(ctx)
    r.cli.write("1\nan\n1234\n2\nHAN\nSGN\n2026-12-20\n1\nECO\n4\n")
    r.sent("LOGIN an 1234")
    r.serve("100 OK an")
    r.sent("SEARCH HAN SGN 2026-12-20 1 ECO")
    r.serve("110 FLIGHTS 0")
    r.sent("MYTICKETS")
    r.serve("110 TICKETS 0")
    r.see("Xin chao an\n")
    r.see("Co 0 chuyen:\n")
    r.see("Ban co 0 ve:\n")


# ---------------- thông báo xen kẽ ----------------

@group("edge")
def test_notification_between_questions(ctx):
    """Thông báo đến giữa 'User: ' và 'Pass: ': in ngay, các dòng đã gõ không bị hỏng"""
    r = Run(ctx)
    r.type("1", "an")
    r.serve("301 NOTIFY DELAY VN9 12")
    r.see("[THONG BAO] DELAY VN9 12\n", timeout=1.0)
    r.type("1234")
    r.sent("LOGIN an 1234")
    r.serve("100 OK an")
    r.see("Xin chao an\n")


@group("edge")
def test_notification_before_first_answer(ctx):
    """Thông báo đến ngay sau khi chọn 3, trước câu trả lời đầu"""
    r = Run(ctx)
    r.type("3")
    r.serve("301 NOTIFY CANCEL VN7")
    r.see("[THONG BAO] CANCEL VN7\n", timeout=1.0)
    r.type("VN1", "2026-12-20", "ECO", "1")
    r.sent("BOOK VN1 2026-12-20 ECO 1")
    r.serve("205 NO SEATS")
    r.see("Loi: 205 NO SEATS\n")


@group("edge")
def test_notification_between_command_and_reply(ctx):
    """Thông báo nằm xen giữa lệnh và phản hồi của nó: in thông báo, rồi vẫn xử lý đúng phản hồi"""
    r = Run(ctx)
    r.type("1", "an", "1234")
    r.sent("LOGIN an 1234")
    r.serve("301 NOTIFY DELAY VN9 12", "301 NOTIFY CANCEL VN8")
    r.see("[THONG BAO] DELAY VN9 12\n", timeout=1.0)
    r.see("[THONG BAO] CANCEL VN8\n", timeout=1.0)
    r.serve("100 OK an")
    r.see("Xin chao an\n")


@group("edge")
def test_notification_at_payment_prompt(ctx):
    """Thông báo đến lúc client đang chờ câu trả lời thanh toán"""
    r = Run(ctx)
    r.type("3", "VN1", "2026-12-20", "ECO", "1")
    r.sent("BOOK VN1 2026-12-20 ECO 1")
    r.serve("100 OK HOLD AA11BB 1000000 10:00:00")
    r.see("Giu cho thanh cong")
    r.serve("301 NOTIFY RESCHEDULE VN1 2026-12-21 09:00 11:00")
    r.see("[THONG BAO] RESCHEDULE VN1 2026-12-21 09:00 11:00\n", timeout=1.0)
    r.type("1")
    r.sent("PAY AA11BB WALLET")
    r.serve("100 OK PAID AA11BB")
    r.see("Da thanh toan AA11BB\n")


@group("edge")
def test_many_notifications_while_idle(ctx):
    """200 thông báo liên tiếp khi người dùng không gõ gì: đủ 200 dòng đúng thứ tự"""
    r = Run(ctx)
    r.conn.send("".join(f"301 NOTIFY DELAY VN{i} {i % 1440 + 1}\n" for i in range(200)).encode())
    for i in range(200):
        r.see(f"[THONG BAO] DELAY VN{i} {i % 1440 + 1}\n", timeout=2.0)


@group("edge")
def test_notification_split_in_pieces(ctx):
    r = Run(ctx)
    r.conn.send_slowly(b"301 NOTIFY RESCHEDULE VN5 2026-12-30 08:00 10:00\n", chunk=3, delay=0.01)
    r.see("[THONG BAO] RESCHEDULE VN5 2026-12-30 08:00 10:00\n")


@group("edge")
def test_long_flight_list(ctx):
    """500 chuyến trong một phản hồi"""
    r = Run(ctx)
    r.type("2", "HAN", "SGN", "2026-12-20", "1", "ECO")
    r.sent("SEARCH HAN SGN 2026-12-20 1 ECO")
    r.conn.send(("110 FLIGHTS 500\n" + "".join(f"VN{i:04d} VN 06:00 08:10 {1000000 + i}\n" for i in range(500))).encode())
    r.see("Co 500 chuyen:\n")
    r.see("500. VN0499 VN 06:00-08:10 1000499\n", timeout=3.0)
    r.finish_quit()


# ---------------- robust ----------------

@group("robust")
def test_connection_refused(ctx):
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    cli = ctx.run_client("127.0.0.1", port)
    if cli.wait(timeout=4) != 1 or "Khong ket noi duoc" not in cli.stdout():
        raise Fail(WA, f"mã thoát sai hoặc thiếu thông báo; stdout {cli.stdout()!r}")


@group("robust")
def test_server_full(ctx):
    """Dòng chào 500 FULL: in 'Server day: ...' và thoát mã 1"""
    r = Run(ctx, welcome="500 FULL")
    if r.cli.wait(timeout=3) != 1 or "Server day: 500 FULL\n" not in r.cli.stdout():
        raise Fail(WA, f"mã thoát sai hoặc thiếu thông báo; stdout {r.cli.stdout()!r}")


@group("robust")
@cases("idle", "waiting_reply", title="Server đóng kết nối ({0}): in 'Mat ket noi', thoát mã 1")
def test_server_closes(ctx, when):
    r = Run(ctx)
    if when == "waiting_reply":
        r.type("4")
        r.sent("MYTICKETS")
    r.conn.close()
    code = r.cli.wait(timeout=3)
    if code != 1 or "Mat ket noi\n" not in r.cli.stdout():
        raise Fail(WA, f"mã thoát {code}, stdout {r.cli.stdout()[-120:]!r}")


@group("robust")
@cases(0, 1, 3, title="Sai số tham số: {0} tham số → mã 1")
def test_wrong_argc(ctx, k):
    srv = ctx.mock_server()
    full = ["127.0.0.1", str(srv.port), "thua"]
    cli = ctx.run_client(*full[:k] if k < 3 else full)
    if cli.wait(timeout=3) != 1:
        raise Fail(WA, "sai số tham số phải thoát mã 1")


# ---------------- stress ----------------

@group("stress")
@timeout(30)
def test_random_session(ctx):
    """150 thao tác ngẫu nhiên (đăng nhập, tìm, đặt+thanh toán, xem vé, lựa chọn sai) xen thông báo ngẫu nhiên"""
    rng = ctx.rng
    r = Run(ctx)
    for step in range(150):
        if rng.random() < 0.3:
            n = rng.randint(1, 3)
            for k in range(n):
                tag = f"VN{step}-{k}"
                r.serve(f"301 NOTIFY DELAY {tag} {rng.randint(1, 1440)}")
                r.see(f"[THONG BAO] DELAY {tag} ")
        pick = rng.choice(["login", "search", "book_wallet", "book_card", "book_skip", "tickets", "bad"])
        if pick == "login":
            login(r, rng.choice(["an", "binh"]), rng.choice(["1234", "abcd"]))
        elif pick == "search":
            k = rng.randint(0, 4)
            r.type("2", "HAN", "SGN", "2026-12-20", str(rng.randint(1, 9)), "ECO")
            got = r.conn.recv_line(timeout=2.0)
            if not got.startswith("SEARCH HAN SGN 2026-12-20 "):
                raise Fail(WA, f"lệnh tìm sai: {got!r}")
            r.serve(f"110 FLIGHTS {k}", *[f"VN{i} VN 06:00 08:10 {1000 + i}" for i in range(k)])
            r.see(f"Co {k} chuyen:\n")
            for i in range(k):
                r.see(f"{i + 1}. VN{i} VN 06:00-08:10 {1000 + i}\n")
        elif pick.startswith("book"):
            r.type("3", f"VN{step}", "2026-12-20", "ECO", "2")
            r.sent(f"BOOK VN{step} 2026-12-20 ECO 2")
            r.serve(f"100 OK HOLD P{step:05d} 2000000 10:00:00")
            r.see(f"Ma: P{step:05d} So tien: 2000000 Han: 10:00:00\n")
            if pick == "book_wallet":
                r.type("1")
                r.sent(f"PAY P{step:05d} WALLET")
                r.serve(f"100 OK PAID P{step:05d}")
                r.see(f"Da thanh toan P{step:05d}\n")
            elif pick == "book_card":
                r.type("2", "4111111111111111", "12/99", "123")
                r.sent(f"PAY P{step:05d} CARD 4111111111111111 12/99 123")
                r.serve("206 PAYMENT FAILED")
                r.see("Loi: 206 PAYMENT FAILED\n")
            else:
                r.type("0")
                r.see("Chua thanh toan\n")
        elif pick == "tickets":
            r.type("4")
            r.sent("MYTICKETS")
            r.serve("110 TICKETS 1", "7380000000001 VN1 2026-12-20 ECO A 1000 PAID")
            r.see("1. 7380000000001 VN1 2026-12-20 ECO PAID\n")
        else:
            r.type(rng.choice(["0", "9", "abc", ""]))
            r.see("Lua chon khong hop le\n")
    r.finish_quit()
