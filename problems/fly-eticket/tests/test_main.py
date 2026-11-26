# Thiết kế: docs/TEST-DESIGN.md. Bộ chấm đóng vai máy chủ SMTP tại 127.0.0.1:2525 và kiểm tra từng byte hội thoại.
import os
import re
import select
import socket
import time

from njlib import WA, Fail, cases, group, sample, timeout, Conn

SMTP_PORT = 2525
PW = {"an": "1234", "binh": "abcd", "chi": "pass99"}
EMAIL = {"an": "an@example.com", "binh": "binh@example.com", "chi": "chi@example.org"}
CODE = {"VN": "738", "VJ": "978", "QH": "126", "BL": "550"}
START_SERIAL = 3  # tickets.txt ban đầu có 2 dòng
OK_RE = re.compile(r"^100 OK ([0-9]{13})( MAIL_FAILED)?$")


class Smtp:
    """Cổng lắng nghe SMTP giả."""

    def __init__(self, ctx):
        s = socket.socket()
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("127.0.0.1", SMTP_PORT))
        s.listen(8)
        self.sock = s
        ctx._conns.append(self)

    def accept(self, timeout=3.0):
        r, _, _ = select.select([self.sock], [], [], timeout)
        if not r:
            raise Fail(WA, f"server không kết nối tới máy chủ SMTP sau {timeout}s")
        c, _ = self.sock.accept()
        return Conn(sock=c, name="smtp")

    def has_connection(self, wait=0.3):
        r, _, _ = select.select([self.sock], [], [], wait)
        return bool(r)

    def close(self):
        try:
            self.sock.close()
        except OSError:
            pass


def crlf_line(c, timeout=3.0):
    """Đọc một dòng SMTP và kiểm tra kết thúc đúng bằng \\r\\n."""
    deadline = time.monotonic() + timeout
    while b"\r\n" not in c.buf:
        if b"\n" in c.buf.replace(b"\r\n", b""):
            raise Fail(WA, f"dòng SMTP không kết thúc bằng \\r\\n: {c.buf[:80]!r}")
        if c.eof or not c._fill(deadline):
            raise Fail(WA, f"smtp: chờ lệnh từ server nhưng nhận được {c.buf!r}")
    line, c.buf = c.buf.split(b"\r\n", 1)
    return line.decode("latin-1")


def message(email, ticket, flight, date, cls, pax):
    return (f"From: noreply@fly.local\r\nTo: {email}\r\nSubject: Ve dien tu {ticket}\r\n\r\nTicket: {ticket}\r\n"
            f"Flight: {flight} {date} {cls}\r\nPassenger: {pax}\r\n").encode()


def reply_bytes(c, data, slow=False):
    if slow:
        c.send_slowly(data, chunk=1, delay=0.002)
    else:
        c.send(data)


def serve(c, email, msg, *, greeting=b"220 mock.smtp ESMTP ready\r\n", helo=b"250 hello\r\n", mail=b"250 sender ok\r\n",
          rcpt=b"250 recipient ok\r\n", data=b"354 end data with <CR><LF>.<CR><LF>\r\n", end=b"250 queued\r\n", stop_after=None,
          slow=False, greeting_delay=0.0):
    """Đóng vai SMTP đúng thứ tự; trả về nội dung thư (bytes, các dòng kết thúc \\r\\n, không có dòng '.') nếu nhận đủ.
    stop_after: tên bước sau đó đóng kết nối ngay (greeting/helo/mail/rcpt/data/end)."""
    time.sleep(greeting_delay)
    reply_bytes(c, greeting, slow)
    if stop_after == "greeting":
        c.close()
        return None
    if not greeting.startswith(b"220"):
        return finish(c)
    for want, rep, name in [("HELO fly.local", helo, "helo"), ("MAIL FROM:<noreply@fly.local>", mail, "mail"),
                            (f"RCPT TO:<{email}>" if email else None, rcpt, "rcpt")]:
        got = crlf_line(c)
        if (want is not None and got != want) or (want is None and not (got.startswith("RCPT TO:<") and got.endswith(">"))):
            raise Fail(WA, f"smtp: mong đợi {want!r}, server gửi {got!r}")
        reply_bytes(c, rep, slow)
        if stop_after == name:
            c.close()
            return None
        if final_code(rep) != b"250":
            return finish(c)
    got = crlf_line(c)
    if got != "DATA":
        raise Fail(WA, f"smtp: mong đợi 'DATA', server gửi {got!r}")
    reply_bytes(c, data, slow)
    if stop_after == "data":
        c.close()
        return None
    if final_code(data) != b"354":
        return finish(c)
    lines = []
    while True:
        ln = crlf_line(c)
        if ln == ".":
            break
        lines.append(ln)
        if len(lines) > 50:
            raise Fail(WA, "thư quá dài hoặc thiếu dòng '.' kết thúc")
    body = b"".join(x.encode("latin-1") + b"\r\n" for x in lines)
    if msg is not None and body != msg:
        raise Fail(WA, f"nội dung thư sai.\nMong đợi: {msg!r}\nNhận:      {body!r}")
    reply_bytes(c, end, slow)
    if stop_after == "end":
        return body
    finish(c)
    return body


def final_code(rep):
    return rep.rstrip(b"\r\n").split(b"\r\n")[-1][:3]


def finish(c):
    """Sau lỗi hoặc xong việc: có thể nhận QUIT (không bắt buộc); đóng kết nối."""
    try:
        c.recv_line(timeout=0.4)
    except Fail:
        pass
    c.close()


def login(ctx, user="an", name=None):
    c = ctx.connect(name=name or user)
    c.send_line(f"LOGIN {user} {PW[user]}")
    c.expect_line(f"100 OK {user}")
    return c


def issue_line(flight="VN213", date="2026-12-20", cls="ECO", pax="NGUYEN_VAN_AN"):
    return f"ISSUE {flight} {date} {cls} {pax}"


def ticket_no(flight, serial):
    return CODE.get(flight[:2], "000") + f"{serial:010d}"


def do_issue(ctx, smtp, c, user="an", flight="VN213", date="2026-12-20", cls="ECO", pax="NGUYEN_VAN_AN", serial=START_SERIAL, **smtp_kw):
    """Gửi ISSUE, đóng vai SMTP, đọc phản hồi. Trả về (số vé, mail_failed)."""
    tno = ticket_no(flight, serial)
    c.send_line(issue_line(flight, date, cls, pax))
    msg = message(EMAIL[user], tno, flight, date, cls, pax)
    sc = smtp.accept()
    serve(sc, EMAIL[user], msg, **smtp_kw)
    got = c.recv_line(timeout=4.0)
    m = OK_RE.match(got)
    if not m or m.group(1) != tno:
        raise Fail(WA, f"{c.name}: ISSUE trả {got!r}, mong đợi 100 OK {tno}")
    return tno, bool(m.group(2))


def tickets(ctx):
    return ctx.read_file("tickets.txt").splitlines()


def check_ticket_file(ctx, expected_new):
    got = tickets(ctx)
    base = ["7380000000001 an VN100 2026-12-01 ECO NGUYEN_VAN_AN", "9780000000002 binh VJ200 2026-12-02 BUS TRAN_THI_BINH"]
    if got != base + expected_new:
        raise Fail(WA, f"tickets.txt sai.\nMong đợi thêm: {expected_new!r}\nThực tế: {got[2:]!r}")


def check_eml(ctx, user, tno, msg):
    p = os.path.join(ctx.workdir, "outbox", user, tno + ".eml")
    if not os.path.exists(p):
        raise Fail(WA, f"không có bản sao thư outbox/{user}/{tno}.eml")
    if open(p, "rb").read() != msg:
        raise Fail(WA, f"outbox/{user}/{tno}.eml sai nội dung: {open(p, 'rb').read()[:120]!r}")


# ---------------- sample ----------------

@sample
def test_issue_sends_mail_and_replies(ctx):
    """ISSUE: ghi tickets.txt, nói chuyện SMTP đúng từng byte, lưu .eml, trả '100 OK <số vé>'"""
    smtp = Smtp(ctx)
    c = login(ctx)
    tno, failed = do_issue(ctx, smtp, c)
    if failed or tno != "7380000000003":
        raise Fail(WA, f"{tno} {failed}")
    check_ticket_file(ctx, ["7380000000003 an VN213 2026-12-20 ECO NGUYEN_VAN_AN"])
    check_eml(ctx, "an", tno, message(EMAIL["an"], tno, "VN213", "2026-12-20", "ECO", "NGUYEN_VAN_AN"))


@sample
def test_push_to_other_sessions(ctx):
    """Tin nhắn '300 TICKET' tới phiên khác cùng tài khoản, trước phản hồi của phiên đang ISSUE"""
    smtp = Smtp(ctx)
    a, b, other = login(ctx, "an", "a1"), login(ctx, "an", "a2"), login(ctx, "binh")
    tno, _ = do_issue(ctx, smtp, a)
    if not select.select([b.sock], [], [], 0.05)[0]:
        raise Fail(WA, "phiên A đã nhận 100 OK nhưng phiên B chưa có tin nhắn: phải đẩy tin TRƯỚC khi trả lời phiên ISSUE")
    b.expect_line(f"300 TICKET {tno}", timeout=2.0)
    other.expect_silence(0.2)
    a.expect_silence(0.2)


@sample
def test_mail_failure_still_issues(ctx):
    """RCPT TO bị từ chối (550): vé vẫn được phát hành, phản hồi có MAIL_FAILED"""
    smtp = Smtp(ctx)
    c = login(ctx)
    tno, failed = do_issue(ctx, smtp, c, rcpt=b"550 no such user\r\n")
    if not failed:
        raise Fail(WA, "thiếu MAIL_FAILED")
    check_ticket_file(ctx, [f"{tno} an VN213 2026-12-20 ECO NGUYEN_VAN_AN"])


# ---------------- basic ----------------

@group("basic")
def test_ticket_numbers_by_airline(ctx):
    """Mã hãng 738/978/126/550/000 theo hai chữ cái đầu; số thứ tự tăng dần toàn server"""
    smtp = Smtp(ctx)
    c = login(ctx)
    new = []
    for i, fl in enumerate(["VN1", "VJ22", "QH333", "BL4444", "AB5", "VN9"]):
        tno, _ = do_issue(ctx, smtp, c, flight=fl, serial=START_SERIAL + i)
        new.append(f"{tno} an {fl} 2026-12-20 ECO NGUYEN_VAN_AN")
    check_ticket_file(ctx, new)


@group("basic")
def test_mail_goes_to_the_users_address(ctx):
    """Email gửi tới địa chỉ của đúng tài khoản"""
    smtp = Smtp(ctx)
    for i, user in enumerate(["binh", "chi", "an"]):
        c = login(ctx, user)
        do_issue(ctx, smtp, c, user=user, serial=START_SERIAL + i, pax=user.upper() + "_X")


@group("basic")
@cases(b"250 hello" + bytes([13, 10]), b"250-mail.example" + bytes([13, 10]) + b"250-PIPELINING" + bytes([13, 10]) + b"250-SIZE 35882577" + bytes([13, 10]) + b"250 8BITMIME" + bytes([13, 10]),
       b"250-a" + bytes([13, 10]) + b"250 b" + bytes([13, 10]),
       title="HELO trả lời nhiều dòng: {0!r:.40}")
def test_multiline_replies(ctx, helo):
    smtp = Smtp(ctx)
    c = login(ctx)
    tno, failed = do_issue(ctx, smtp, c, helo=helo, mail=b"250-ok\r\n250 ok2\r\n", rcpt=b"250-ok\r\n250-x\r\n250 y\r\n",
                           greeting=b"220-mock ESMTP\r\n220 ready\r\n")
    if failed:
        raise Fail(WA, "phản hồi nhiều dòng bị coi là lỗi")


@group("basic")
def test_push_only_same_account(ctx):
    """Tin nhắn chỉ tới các phiên của cùng tài khoản; không tới phiên đang ISSUE, phiên chưa đăng nhập, hay tài khoản khác"""
    smtp = Smtp(ctx)
    a = login(ctx, "an", "a1")
    others = [login(ctx, "an", "a2"), login(ctx, "an", "a3")]
    stranger = login(ctx, "binh")
    anon = ctx.connect("anon")
    tno, _ = do_issue(ctx, smtp, a)
    for o in others:
        o.expect_line(f"300 TICKET {tno}", timeout=2.0)
    stranger.expect_silence(0.2)
    anon.expect_silence(0.2)
    a.expect_silence(0.2)


@group("basic")
def test_two_tickets_two_pushes(ctx):
    """Hai ISSUE liên tiếp: hai tin nhắn đúng thứ tự"""
    smtp = Smtp(ctx)
    a, b = login(ctx, "an", "a1"), login(ctx, "an", "a2")
    t1, _ = do_issue(ctx, smtp, a, serial=START_SERIAL)
    t2, _ = do_issue(ctx, smtp, a, flight="VJ77", serial=START_SERIAL + 1)
    b.expect_lines([f"300 TICKET {t1}", f"300 TICKET {t2}"], timeout=2.0)


@group("basic")
def test_eml_copy_saved(ctx):
    """outbox/<user>/<số vé>.eml là đúng các byte của thư (CRLF), kể cả khi gửi mail thất bại"""
    smtp = Smtp(ctx)
    c = login(ctx, "binh")
    t1, _ = do_issue(ctx, smtp, c, user="binh", serial=START_SERIAL, flight="VJ5", cls="BUS", pax="Tran_Binh")
    check_eml(ctx, "binh", t1, message(EMAIL["binh"], t1, "VJ5", "2026-12-20", "BUS", "Tran_Binh"))
    t2, failed = do_issue(ctx, smtp, c, user="binh", serial=START_SERIAL + 1, rcpt=b"550 no\r\n")
    if not failed:
        raise Fail(WA, "mong đợi MAIL_FAILED")
    check_eml(ctx, "binh", t2, message(EMAIL["binh"], t2, "VN213", "2026-12-20", "ECO", "NGUYEN_VAN_AN"))


@group("basic")
def test_login_rules(ctx):
    """LOGIN: 201 / 207 / 203, nhiều phiên cùng tài khoản; ISSUE chưa đăng nhập → 204; QUIT"""
    c = ctx.connect()
    for line, want in [("ISSUE VN1 2026-12-20 ECO A", "204 LOGIN FIRST"), ("ISSUE", "204 LOGIN FIRST"), ("LOGIN an", "201 INVALID"),
                       ("LOGIN an 12345", "203 DENIED"), ("LOGIN zzz 1234", "203 DENIED"), ("LOGIN an 1234", "100 OK an"),
                       ("LOGIN an 1234", "207 ALREADY LOGGED IN"), ("PING", "999 UNKNOWN ERROR"), ("", "999 UNKNOWN ERROR")]:
        c.send_line(line)
        c.expect_line(want)
    d = ctx.connect()
    d.send_line("LOGIN an 1234")
    d.expect_line("100 OK an")
    d.send_line("QUIT")
    d.expect_line("100 OK")
    d.expect_closed()


# ---------------- edge ----------------

@group("edge")
@cases("ISSUE", "ISSUE VN1", "ISSUE VN1 2026-12-20", "ISSUE VN1 2026-12-20 ECO", "ISSUE VN1 2026-12-20 ECO A B", "ISSUE vn1 2026-12-20 ECO A",
       "ISSUE V1 2026-12-20 ECO A", "ISSUE VN 2026-12-20 ECO A", "ISSUE VN12345 2026-12-20 ECO A", "ISSUE VN1A 2026-12-20 ECO A",
       "ISSUE VN1 2026-02-30 ECO A", "ISSUE VN1 2026-12-2 ECO A", "ISSUE VN1 2100-02-29 ECO A", "ISSUE VN1 2026-12-20 eco A",
       "ISSUE VN1 2026-12-20 FIRST A", "ISSUE VN1 2026-12-20 ECO A-B", "ISSUE VN1 2026-12-20 ECO A1", "ISSUE VN1 2026-12-20 ECO " + "A" * 41,
       "ISSUE  VN1 2026-12-20 ECO A", "ISSUE VN1 2026-12-20 ECO A ", "ISSUE VN1 2026-12-20  ECO A", title="ISSUE sai {0!r:.50} → 201, không SMTP, không vé")
def test_issue_invalid(ctx, line):
    smtp = Smtp(ctx)
    c = login(ctx)
    c.send_line(line)
    c.expect_line("201 INVALID")
    if smtp.has_connection(0.3):
        raise Fail(WA, "ISSUE sai cú pháp mà server vẫn mở kết nối SMTP")
    check_ticket_file(ctx, [])
    do_issue(ctx, smtp, c)


@group("edge")
@cases(("VN1", "2024-02-29", "ECO", "A"), ("QH1234", "1900-01-01", "BUS", "a"), ("BL9999", "2100-12-31", "ECO", "A" * 40),
       ("ZZ0", "2026-12-20", "BUS", "x_y_z"), title="ISSUE biên hợp lệ {0} {1} {2} {3:.20}")
def test_issue_valid_boundaries(ctx, flight, date, cls, pax):
    smtp = Smtp(ctx)
    c = login(ctx)
    do_issue(ctx, smtp, c, flight=flight, date=date, cls=cls, pax=pax)


@group("edge")
@cases((dict(greeting=b"421 service not available\r\n"), "lời chào 421"),
       (dict(helo=b"500 syntax error\r\n"), "HELO 500"), (dict(mail=b"550 sender rejected\r\n"), "MAIL 550"),
       (dict(rcpt=b"553 mailbox name not allowed\r\n"), "RCPT 553"), (dict(data=b"554 transaction failed\r\n"), "DATA 554"),
       (dict(end=b"452 insufficient storage\r\n"), "kết thư 452"), (dict(stop_after="greeting"), "đóng sau lời chào"),
       (dict(stop_after="rcpt"), "đóng sau RCPT"), (dict(stop_after="data"), "đóng sau 354"),
       (dict(rcpt=b"250-ok\r\n550 oops\r\n"), "nhiều dòng rồi lỗi"), title="Máy chủ mail lỗi: {1} → MAIL_FAILED, vé vẫn phát hành")
def test_mail_failures(ctx, kw, label):
    smtp = Smtp(ctx)
    c = login(ctx)
    b = login(ctx, "an", "b")
    tno, failed = do_issue(ctx, smtp, c, **kw)
    if not failed:
        raise Fail(WA, f"{label}: phản hồi thiếu MAIL_FAILED")
    b.expect_line(f"300 TICKET {tno}", timeout=2.0)
    check_ticket_file(ctx, [f"{tno} an VN213 2026-12-20 ECO NGUYEN_VAN_AN"])
    check_eml(ctx, "an", tno, message(EMAIL["an"], tno, "VN213", "2026-12-20", "ECO", "NGUYEN_VAN_AN"))
    tno2, failed2 = do_issue(ctx, smtp, c, serial=START_SERIAL + 1)
    if failed2:
        raise Fail(WA, "lỗi mail lần trước làm hỏng lần sau")


@group("edge")
def test_smtp_not_running(ctx):
    """Không có máy chủ SMTP (kết nối bị từ chối): vẫn phát hành vé và trả MAIL_FAILED nhanh"""
    c = login(ctx)
    c.send_line(issue_line())
    t0 = time.monotonic()
    got = c.recv_line(timeout=4.0)
    if got != "100 OK 7380000000003 MAIL_FAILED" or time.monotonic() - t0 > 3.0:
        raise Fail(WA, f"nhận {got!r} sau {time.monotonic() - t0:.1f}s")
    check_ticket_file(ctx, ["7380000000003 an VN213 2026-12-20 ECO NGUYEN_VAN_AN"])


# ---------------- stream ----------------

@group("stream")
def test_byte_by_byte_and_slow_smtp(ctx):
    """Lệnh gửi từng byte; máy chủ SMTP trả lời từng byte một"""
    smtp = Smtp(ctx)
    c = ctx.connect()
    c.send_slowly(f"LOGIN an 1234\n", chunk=1, delay=0.001)
    c.expect_line("100 OK an")
    c.send_slowly(issue_line() + "\n", chunk=1, delay=0.001)
    sc = smtp.accept()
    serve(sc, EMAIL["an"], message(EMAIL["an"], "7380000000003", "VN213", "2026-12-20", "ECO", "NGUYEN_VAN_AN"), slow=True)
    c.expect_line("100 OK 7380000000003", timeout=4.0)


@group("stream")
def test_many_commands_one_send(ctx):
    """LOGIN + ISSUE dính nhau trong một lần gửi"""
    smtp = Smtp(ctx)
    c = ctx.connect()
    c.send(f"LOGIN an 1234\n{issue_line()}\nWHAT\n")
    c.expect_line("100 OK an")
    sc = smtp.accept()
    serve(sc, EMAIL["an"], message(EMAIL["an"], "7380000000003", "VN213", "2026-12-20", "ECO", "NGUYEN_VAN_AN"))
    c.expect_line("100 OK 7380000000003", timeout=4.0)
    c.expect_line("999 UNKNOWN ERROR")


@group("stream")
def test_crlf_commands(ctx):
    """Lệnh kết thúc bằng \\r\\n"""
    smtp = Smtp(ctx)
    c = ctx.connect()
    c.send("LOGIN an 1234\r\n")
    c.expect_line("100 OK an")
    c.send(issue_line() + "\r\n")
    sc = smtp.accept()
    serve(sc, EMAIL["an"], message(EMAIL["an"], "7380000000003", "VN213", "2026-12-20", "ECO", "NGUYEN_VAN_AN"))
    c.expect_line("100 OK 7380000000003", timeout=4.0)


# ---------------- robust ----------------

@group("robust")
@timeout(15)
def test_silent_smtp_times_out(ctx):
    """Máy chủ SMTP kết nối rồi im lặng: sau ~2 giây trả MAIL_FAILED (không treo mãi)"""
    smtp = Smtp(ctx)
    c = login(ctx)
    c.send_line(issue_line())
    sc = smtp.accept()
    t0 = time.monotonic()
    got = c.recv_line(timeout=6.0)
    dt = time.monotonic() - t0
    if got != "100 OK 7380000000003 MAIL_FAILED":
        raise Fail(WA, f"nhận {got!r}")
    if not 1.5 <= dt <= 4.5:
        raise Fail(WA, f"chờ máy chủ mail {dt:.1f}s (mong đợi khoảng 2 giây)")
    sc.close()


@group("robust")
@timeout(15)
def test_silent_midway_times_out(ctx):
    """Máy chủ SMTP trả lời 220, HELO rồi im lặng ở MAIL: MAIL_FAILED sau ~2 giây"""
    smtp = Smtp(ctx)
    c = login(ctx)
    c.send_line(issue_line())
    sc = smtp.accept()
    sc.send(b"220 hi\r\n")
    crlf_line(sc)
    sc.send(b"250 ok\r\n")
    crlf_line(sc)  # MAIL FROM ... không trả lời
    t0 = time.monotonic()
    got = c.recv_line(timeout=6.0)
    if got != "100 OK 7380000000003 MAIL_FAILED" or not 1.5 <= time.monotonic() - t0 <= 4.5:
        raise Fail(WA, f"nhận {got!r} sau {time.monotonic() - t0:.1f}s")


@group("robust")
@timeout(15)
def test_dead_peer_push_does_not_kill_server(ctx):
    """Phiên cùng tài khoản đã đóng ngay trước khi server đẩy tin: server không chết, ISSUE sau vẫn chạy"""
    smtp = Smtp(ctx)
    a = login(ctx, "an", "a")
    b = login(ctx, "an", "b")
    b.close()
    for i in range(3):
        a.send_line(issue_line(flight=f"VN{i + 1}"))
        sc = smtp.accept()
        serve(sc, EMAIL["an"], None, greeting_delay=0.15)
        a.expect_line(f"100 OK {ticket_no('VN1', START_SERIAL + i)}", timeout=4.0)
    ctx.expect_alive()


@group("robust")
def test_binary_garbage(ctx):
    """Byte lạ không làm hỏng server"""
    smtp = Smtp(ctx)
    c = login(ctx)
    for junk in [b"\x01\x02", b"ISSUE \xff\xfe 2026-12-20 ECO A", b"\x7f"]:
        c.send(junk + b"\n")
        got = c.recv_line()
        if got not in ("201 INVALID", "999 UNKNOWN ERROR"):
            raise Fail(WA, f"byte lạ {junk!r}: nhận {got!r}")
    do_issue(ctx, smtp, c)


@group("robust")
@timeout(25)
def test_client_resets_during_smtp(ctx):
    """Client RST trong lúc server đang nói chuyện SMTP: server vẫn sống, vé vẫn được phát hành"""
    smtp = Smtp(ctx)
    c = login(ctx)
    c.send_line(issue_line())
    sc = smtp.accept()
    c.reset()
    serve(sc, EMAIL["an"], None)
    time.sleep(0.3)
    ctx.expect_alive()
    d = login(ctx, "binh")
    tno, _ = do_issue(ctx, smtp, d, user="binh", serial=START_SERIAL + 1)
    if len(tickets(ctx)) != 4:
        raise Fail(WA, f"tickets.txt có {len(tickets(ctx))} dòng, mong đợi 4")


# ---------------- concurrency ----------------

@group("concurrency")
@timeout(20)
def test_two_sessions_issue_concurrently(ctx):
    """Hai phiên cùng ISSUE: số thứ tự không trùng và đủ hai dòng trong tickets.txt"""
    smtp = Smtp(ctx)
    a, b = login(ctx, "an", "a"), login(ctx, "binh", "b")
    a.send_line(issue_line(flight="VN1"))
    b.send_line(issue_line(flight="VJ2", pax="BINH_X"))
    for _ in range(2):
        serve(smtp.accept(), None, None)
    ra, rb = a.recv_line(timeout=4.0), b.recv_line(timeout=4.0)
    ma, mb = OK_RE.match(ra), OK_RE.match(rb)
    if not ma or not mb or ma.group(2) or mb.group(2):
        raise Fail(WA, f"phản hồi {ra!r} / {rb!r}")
    if sorted([int(ma.group(1)[3:]), int(mb.group(1)[3:])]) != [3, 4]:
        raise Fail(WA, f"số thứ tự không phải 3 và 4: {ra!r} {rb!r}")
    if len(tickets(ctx)) != 4:
        raise Fail(WA, "tickets.txt thiếu dòng")


@group("concurrency")
def test_idle_client_does_not_block(ctx):
    """Client im lặng/gửi dở lệnh không chặn client khác (khi không có ISSUE đang chờ SMTP)"""
    idle = [ctx.connect(f"idle{i}") for i in range(4)]
    idle[0].send("LOGIN an 12")
    c = login(ctx, "binh")
    c.send_line("WHOAMI")
    c.expect_line("999 UNKNOWN ERROR")
    idle[0].send("34\n")
    idle[0].expect_line("100 OK an")


# ---------------- stress ----------------

@group("stress")
@timeout(60)
def test_40_issues_mixed_outcomes(ctx):
    """40 lần ISSUE (xen kẽ thành công / lỗi SMTP / hai phiên nhận tin): số vé, tickets.txt, .eml, tin nhắn đều đúng"""
    smtp = Smtp(ctx)
    a, b = login(ctx, "an", "a"), login(ctx, "an", "b")
    new, pushes = [], []
    rng = ctx.rng
    for i in range(40):
        fl = rng.choice(["VN", "VJ", "QH", "BL", "XY"]) + str(rng.randint(1, 9999))
        cls = rng.choice(["ECO", "BUS"])
        pax = "P" + "x" * rng.randint(0, 30)
        kw = rng.choice([{}, {}, {"rcpt": b"550 no\r\n"}, {"stop_after": "mail"}, {"helo": b"250-a\r\n250 b\r\n"}])
        tno, failed = do_issue(ctx, smtp, a, flight=fl, cls=cls, pax=pax, serial=START_SERIAL + i, **kw)
        if bool(failed) != bool(kw.get("rcpt") or kw.get("stop_after")):
            raise Fail(WA, f"lần {i}: MAIL_FAILED = {failed}, kw = {kw}")
        new.append(f"{tno} an {fl} 2026-12-20 {cls} {pax}")
        pushes.append(f"300 TICKET {tno}")
    b.expect_lines(pushes, timeout=3.0)
    check_ticket_file(ctx, new)
