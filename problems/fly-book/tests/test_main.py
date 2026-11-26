# Thiết kế: docs/TEST-DESIGN.md. Phần "tối đa N client" dùng chung: judge/runner/suites.py (maxn_suite).
import re
import time

import suite_fly as F
from njlib import BLOCKED, WA, Fail, args, cases, group, sample, timeout
from suites import maxn_suite

T_HOLD = 2  # tham số T mặc định của bài (xem meta.yaml)
globals().update(maxn_suite(welcome="100 OK WELCOME", full="500 FULL", quit=("QUIT", "100 OK"), ping=("BALANCE", None),
                            extra_args=(str(T_HOLD),)))

PW = {"an": "1234", "binh": "abcd", "chi": "pass99", "dung": "x1y2z3", "eva": "eva123"}
D = "2026-12-20"
HOLD_RE = re.compile(r"^100 OK HOLD ([A-Z0-9]{6}) ([0-9]+) ([0-9]{2}):([0-9]{2}):([0-9]{2})$")
GOOD_CARD = F.make_card("411111111111111")
FAR = "12/99"


def hello(ctx, name=None):
    c = ctx.connect(name=name)
    c.expect_line("100 OK WELCOME", timeout=1.5)
    return c


def login(ctx, user="an", name=None):
    c = hello(ctx, name or user)
    c.send_line(f"LOGIN {user} {PW[user]}")
    c.expect_line(f"100 OK {user}")
    return c


def say(c, line, want):
    c.send_line(line)
    c.expect_line(want, timeout=2.0)


def book(c, code, date, cls, pax):
    """Gửi BOOK, kiểm tra dạng phản hồi 100 OK HOLD; trả về (pnr, số tiền, hạn dạng giây-trong-ngày)."""
    c.send_line(f"BOOK {code} {date} {cls} {pax}")
    got = c.recv_line(timeout=2.0)
    m = HOLD_RE.match(got)
    if not m:
        raise Fail(WA, f"{c.name}: BOOK {code} {date} {cls} {pax}: mong đợi '100 OK HOLD <PNR> <tiền> <HH:MM:SS>', nhận {got!r}")
    return m.group(1), int(m.group(2)), int(m.group(3)) * 3600 + int(m.group(4)) * 60 + int(m.group(5))


def seats(c, code, date=D):
    c.send_line(f"SEATS {code} {date}")
    got = c.recv_line(timeout=2.0)
    m = re.match(r"^100 OK ([0-9]+) ([0-9]+)$", got)
    if not m:
        raise Fail(WA, f"{c.name}: SEATS {code} {date}: nhận {got!r}")
    return int(m.group(1)), int(m.group(2))


def expect_seats(c, code, want, date=D):
    got = seats(c, code, date)
    if got != want:
        raise Fail(WA, f"{c.name}: SEATS {code}: mong đợi {want}, nhận {got}")


def balance(c):
    c.send_line("BALANCE")
    got = c.recv_line(timeout=2.0)
    m = re.match(r"^100 OK (-?[0-9]+)$", got)
    if not m:
        raise Fail(WA, f"{c.name}: BALANCE: nhận {got!r}")
    return int(m.group(1))


def check_deadline(sec_of_day, t0, hold=T_HOLD):
    """Hạn giữ chỗ phải xấp xỉ (giờ địa phương lúc đặt + T giây); chấp nhận lệch do làm tròn giây."""
    lt = time.localtime(t0)
    now = lt.tm_hour * 3600 + lt.tm_min * 60 + lt.tm_sec
    diff = (sec_of_day - (now + hold) + 43200) % 86400 - 43200
    if not -2.0 <= diff <= 1.5:
        raise Fail(WA, f"hạn giữ chỗ lệch {diff}s so với giờ hiện tại + {hold}s")


def current_ym():
    lt = time.localtime()
    return lt.tm_year, lt.tm_mon


def shift_month(delta):
    y, m = current_ym()
    m += delta
    while m < 1:
        m += 12
        y -= 1
    while m > 12:
        m -= 12
        y += 1
    return f"{m:02d}/{y % 100:02d}"


# ---------------- sample ----------------

@sample
def test_book_and_pay_wallet(ctx):
    """BOOK giữ ghế, PAY WALLET trừ ví"""
    c = login(ctx, "an")
    t0 = time.time()
    pnr, amount, dl = book(c, "VN001", D, "ECO", 2)
    check_deadline(dl, t0)
    if amount != 2000000:
        raise Fail(WA, f"số tiền {amount}, mong đợi 2000000")
    expect_seats(c, "VN001", (1, 2))
    say(c, f"PAY {pnr} WALLET", f"100 OK PAID {pnr}")
    if balance(c) != 48000000:
        raise Fail(WA, "số dư sau khi trả 2.000.000 phải là 48000000")


@sample
def test_no_seats_and_denied(ctx):
    """Hết ghế → 205; PNR của người khác → 203"""
    a, b = login(ctx, "an"), login(ctx, "binh")
    pnr, _, _ = book(a, "VN001", D, "ECO", 2)
    say(b, f"BOOK VN001 {D} ECO 2", "205 NO SEATS")
    say(b, f"PAY {pnr} WALLET", "203 DENIED")
    expect_seats(b, "VN001", (1, 2))


@sample
def test_card_payment(ctx):
    """Thanh toán thẻ: Luhn, hạn, CVV"""
    c = login(ctx, "binh")
    pnr, _, _ = book(c, "VN006", "2026-12-21", "ECO", 1)
    say(c, f"PAY {pnr} CARD {GOOD_CARD[:-1]}{(int(GOOD_CARD[-1]) + 1) % 10} {FAR} 123", "206 PAYMENT FAILED")
    say(c, f"PAY {pnr} CARD {GOOD_CARD} 01/20 123", "206 PAYMENT FAILED")
    say(c, f"PAY {pnr} CARD {GOOD_CARD} {FAR} 12", "206 PAYMENT FAILED")
    say(c, f"PAY {pnr} CARD {GOOD_CARD} {FAR} 123", f"100 OK PAID {pnr}")
    say(c, f"PAY {pnr} CARD {GOOD_CARD} {FAR} 123", "209 ALREADY PAID")
    if balance(c) != 1500000:
        raise Fail(WA, "thanh toán thẻ không được trừ ví")


# ---------------- basic ----------------

@group("basic")
@cases("BALANCE", "BOOK", f"BOOK VN001 {D} ECO 1", "PAY", "PAY X WALLET", "RELEASE", "RELEASE X", "BALANCE x", "BOOK x",
       title="Chưa đăng nhập: {0!r} → 204 LOGIN FIRST")
def test_login_required(ctx, line):
    c = hello(ctx)
    say(c, line, "204 LOGIN FIRST")
    say(c, f"SEATS VN001 {D}", "100 OK 3 2")


@group("basic")
def test_login_rules(ctx):
    """LOGIN: sai cú pháp 201, sai mật khẩu 203, đăng nhập lần hai 207; nhiều phiên cùng tài khoản được"""
    c = hello(ctx)
    for line, want in [("LOGIN an", "201 INVALID"), ("LOGIN an 12", "201 INVALID"), ("LOGIN an 12345", "203 DENIED"),
                       ("LOGIN nobody 1234", "203 DENIED"), ("LOGIN an 1234", "100 OK an"), ("LOGIN an 1234", "207 ALREADY LOGGED IN"),
                       ("LOGIN binh abcd", "207 ALREADY LOGGED IN")]:
        say(c, line, want)
    d = hello(ctx)
    say(d, "LOGIN an 1234", "100 OK an")


@group("basic")
def test_seats_command(ctx):
    """SEATS: không cần đăng nhập, 202 nếu không có chuyến/ngày, 201 nếu sai số thành phần"""
    c = hello(ctx)
    for line, want in [(f"SEATS VN001 {D}", "100 OK 3 2"), (f"SEATS VN002 {D}", "100 OK 1 0"), (f"SEATS VJ100 {D}", "100 OK 180 20"),
                       ("SEATS VN001 2026-12-21", "202 NOT FOUND"), ("SEATS ZZ999 2026-12-20", "202 NOT FOUND"),
                       ("SEATS VN001", "201 INVALID"), ("SEATS", "201 INVALID"), (f"SEATS VN001 {D} x", "201 INVALID")]:
        say(c, line, want)


@group("basic")
def test_book_amounts(ctx):
    """Số tiền = giá × số khách cho cả hai hạng"""
    c = login(ctx, "an")
    for code, date, cls, pax, price in [("VJ100", D, "ECO", 9, 800000), ("VJ100", D, "BUS", 5, 2500000), ("QH007", "2026-12-22", "BUS", 7, 3100000),
                                        ("VN001", D, "BUS", 1, 3000000), ("BL008", D, "ECO", 1, 650000)]:
        pnr, amount, _ = book(c, code, date, cls, pax)
        if amount != price * pax:
            raise Fail(WA, f"{code} {cls} x{pax}: số tiền {amount}, mong đợi {price * pax}")


@group("basic")
def test_hold_reduces_seats_immediately(ctx):
    """Đặt xong ghế bị trừ ngay, cho mọi client thấy"""
    a, b = login(ctx, "an"), login(ctx, "binh")
    book(a, "VN006", "2026-12-21", "ECO", 5)
    expect_seats(b, "VN006", (7, 12), "2026-12-21")
    book(b, "VN006", "2026-12-21", "BUS", 4)
    expect_seats(a, "VN006", (7, 8), "2026-12-21")


@group("basic")
def test_wallet_insufficient_then_release(ctx):
    """Ví không đủ → 206, chỗ giữ vẫn còn; RELEASE trả ghế, PNR biến mất"""
    c = login(ctx, "chi")
    pnr, _, _ = book(c, "VN001", D, "ECO", 1)
    say(c, f"PAY {pnr} WALLET", "206 PAYMENT FAILED")
    expect_seats(c, "VN001", (2, 2))
    say(c, f"RELEASE {pnr}", "100 OK")
    expect_seats(c, "VN001", (3, 2))
    say(c, f"PAY {pnr} WALLET", "202 NOT FOUND")
    say(c, f"RELEASE {pnr}", "202 NOT FOUND")
    if balance(c) != 0:
        raise Fail(WA, "số dư của chi phải còn 0")


@group("basic")
def test_wallet_exact_balance(ctx):
    """Số dư đúng bằng số tiền thì trả được, về 0; hết tiền thì 206"""
    e = login(ctx, "eva")
    pe, amount, _ = book(e, "VN001", D, "ECO", 1)
    if amount != 1000000:
        raise Fail(WA, "số tiền phải là 1000000")
    say(e, f"PAY {pe} WALLET", f"100 OK PAID {pe}")
    if balance(e) != 0:
        raise Fail(WA, "số dư của eva phải về 0")
    p2, _, _ = book(e, "VN001", D, "ECO", 1)
    say(e, f"PAY {p2} WALLET", "206 PAYMENT FAILED")
    c = login(ctx, "dung")
    pnr, amount, _ = book(c, "VJ010", "2026-12-23", "ECO", 1)  # 450000
    say(c, f"PAY {pnr} WALLET", f"100 OK PAID {pnr}")
    if balance(c) != 999999 - 450000:
        raise Fail(WA, "số dư sai sau lần trả đầu")
    pnr2, _, _ = book(c, "BL008", D, "ECO", 1)  # 650000 > 549999
    say(c, f"PAY {pnr2} WALLET", "206 PAYMENT FAILED")
    pnr3, _, _ = book(c, "VJ010", "2026-12-23", "ECO", 1)
    say(c, f"PAY {pnr3} WALLET", f"100 OK PAID {pnr3}")
    if balance(c) != 99999:
        raise Fail(WA, "số dư sai sau lần trả thứ hai")


@group("basic")
def test_pay_check_order(ctx):
    """Thứ tự: 202 → 203 → 209 → 208 → 206"""
    a, b = login(ctx, "an"), login(ctx, "binh")
    say(a, "PAY NOPE00 CARD x", "201 INVALID")
    say(a, f"PAY NOPE00 CARD 1234567890123456 01/20 123", "202 NOT FOUND")
    pnr, _, _ = book(a, "VN006", "2026-12-21", "ECO", 1)
    say(b, f"PAY {pnr} CARD 1234567890123456 01/20 123", "203 DENIED")
    say(b, f"RELEASE {pnr}", "203 DENIED")
    say(a, f"PAY {pnr} WALLET", f"100 OK PAID {pnr}")
    say(a, f"PAY {pnr} CARD 1234567890123456 01/20 123", "209 ALREADY PAID")
    say(a, f"RELEASE {pnr}", "209 ALREADY PAID")
    say(b, f"PAY {pnr} WALLET", "203 DENIED")


@group("basic")
def test_release_returns_exact_seats(ctx):
    """RELEASE trả đúng số ghế của lần đặt (không trả hai lần)"""
    c = login(ctx, "an")
    p1, _, _ = book(c, "VN006", "2026-12-21", "ECO", 4)
    p2, _, _ = book(c, "VN006", "2026-12-21", "ECO", 3)
    expect_seats(c, "VN006", (5, 12), "2026-12-21")
    say(c, f"RELEASE {p1}", "100 OK")
    expect_seats(c, "VN006", (9, 12), "2026-12-21")
    say(c, f"RELEASE {p1}", "202 NOT FOUND")
    expect_seats(c, "VN006", (9, 12), "2026-12-21")
    say(c, f"RELEASE {p2}", "100 OK")
    expect_seats(c, "VN006", (12, 12), "2026-12-21")


@group("basic")
def test_paid_ticket_keeps_seats_after_disconnect(ctx):
    """Vé đã thanh toán giữ ghế sau khi client rời đi; chỗ giữ chưa trả thì được trả lại"""
    a = login(ctx, "an")
    paid, _, _ = book(a, "VN001", D, "ECO", 1)
    say(a, f"PAY {paid} WALLET", f"100 OK PAID {paid}")
    book(a, "VN001", D, "ECO", 1)  # giữ chưa trả
    a.send_line("QUIT")
    a.expect_line("100 OK")
    a.expect_closed()
    time.sleep(0.2)
    b = login(ctx, "binh")
    expect_seats(b, "VN001", (2, 2))
    say(b, f"PAY {paid} WALLET", "203 DENIED")
    c = login(ctx, "an", "an2")
    say(c, f"PAY {paid} WALLET", "209 ALREADY PAID")


@group("basic")
def test_unpaid_hold_released_on_rst(ctx):
    """Client mất kết nối đột ngột: chỗ giữ chưa thanh toán được trả lại; PNR cũ không còn"""
    a = login(ctx, "an")
    pnr, _, _ = book(a, "VN001", D, "ECO", 3)
    a.reset()
    time.sleep(0.3)
    b = login(ctx, "binh")
    expect_seats(b, "VN001", (3, 2))
    say(b, f"PAY {pnr} WALLET", "202 NOT FOUND")


@group("basic")
@cases("PING", "", " ", "book VN001 2026-12-20 ECO 1", "Login an 1234", "BOOKING", "PAYX", "RELEASED", "BALANCES", "SEAT VN001 2026-12-20",
       title="Lệnh lạ {0!r} → 999")
def test_unknown_commands(ctx, line):
    c = login(ctx, "an")
    say(c, line, "999 UNKNOWN ERROR")
    say(c, "BALANCE", "100 OK 50000000")


# ---------------- edge ----------------

@group("edge")
@cases(f"BOOK VN001 {D} ECO", f"BOOK VN001 {D} ECO 0", f"BOOK VN001 {D} ECO 10", f"BOOK VN001 {D} ECO 01", f"BOOK VN001 {D} ECO a",
       f"BOOK VN001 {D} eco 1", f"BOOK VN001 {D} FIRST 1", "BOOK VN001 2026-02-30 ECO 1", "BOOK VN001 2026-12-2 ECO 1",
       f"BOOK VN001 {D} ECO 1 x", f"BOOK  VN001 {D} ECO 1", f"BOOK VN001 {D} ECO  1", f"BOOK VN001 {D} ECO 1 ", f"BOOK VN001 {D}",
       "BOOK VN001", title="BOOK sai cú pháp {0!r} → 201, ghế không đổi")
def test_book_syntax(ctx, line):
    c = login(ctx, "an")
    say(c, line, "201 INVALID")
    expect_seats(c, "VN001", (3, 2))


@group("edge")
@cases((f"BOOK ZZ999 {D} ECO 1", "202 NOT FOUND"), ("BOOK VN001 2026-12-21 ECO 1", "202 NOT FOUND"), (f"BOOK vn001 {D} ECO 1", "202 NOT FOUND"),
       (f"BOOK VN001 {D} ECO 4", "205 NO SEATS"), (f"BOOK VN001 {D} BUS 3", "205 NO SEATS"), (f"BOOK VN002 {D} BUS 1", "205 NO SEATS"),
       (f"BOOK VN002 {D} ECO 2", "205 NO SEATS"), (f"BOOK VJ100 {D} ECO 9", "HOLD"), (f"BOOK VN001 {D} ECO 3", "HOLD"),
       (f"BOOK VN001 {D} BUS 2", "HOLD"), (f"BOOK VN002 {D} ECO 1", "HOLD"), (f"BOOK BL300 2026-12-22 BUS 1", "HOLD"),
       title="BOOK biên: {0!r} → {1}")
def test_book_boundaries(ctx, line, want):
    c = login(ctx, "an")
    if want == "HOLD":
        c.send_line(line)
        got = c.recv_line(timeout=2.0)
        if not HOLD_RE.match(got):
            raise Fail(WA, f"{line!r}: nhận {got!r}")
    else:
        say(c, line, want)


@group("edge")
def test_book_all_seats_then_none(ctx):
    """Đặt đúng hết số ghế còn lại thì ghế = 0, đặt thêm 1 → 205; trả một chỗ giữ thì đặt lại được"""
    c = login(ctx, "an")
    p, _, _ = book(c, "VN001", D, "ECO", 3)
    expect_seats(c, "VN001", (0, 2))
    say(c, f"BOOK VN001 {D} ECO 1", "205 NO SEATS")
    say(c, f"RELEASE {p}", "100 OK")
    book(c, "VN001", D, "ECO", 1)
    expect_seats(c, "VN001", (2, 2))


@group("edge")
def test_rejected_book_changes_nothing(ctx):
    """BOOK bị từ chối (205) không đổi số ghế"""
    c = login(ctx, "an")
    for _ in range(5):
        say(c, f"BOOK VN001 {D} ECO 4", "205 NO SEATS")
        say(c, f"BOOK VN001 {D} BUS 3", "205 NO SEATS")
    expect_seats(c, "VN001", (3, 2))


@group("edge")
def test_pnr_format_and_unique(ctx):
    """300 PNR liên tiếp: đúng 6 ký tự A-Z0-9, không trùng, không phải dãy tuần tự"""
    c = login(ctx, "an")
    seen = []
    for _ in range(300):
        p, _, _ = book(c, "VJ100", D, "ECO", 1)
        seen.append(p)
        say(c, f"RELEASE {p}", "100 OK")
    if len(set(seen)) != 300:
        raise Fail(WA, "có PNR bị cấp trùng")
    if len({p[0] for p in seen}) < 6 or seen == sorted(seen) or len({p[-1] for p in seen}) < 6:
        raise Fail(WA, "PNR không có vẻ ngẫu nhiên (ký tự đầu/cuối ít biến thiên hoặc tăng dần)")


@group("edge")
def test_pnr_unique_even_after_release(ctx):
    """PNR đã cấp (kể cả đã trả/giải phóng) không được cấp lại"""
    a, b = login(ctx, "an"), login(ctx, "binh")
    seen = set()
    for i in range(150):
        c = a if i % 2 else b
        p, _, _ = book(c, "VJ100", D, "ECO", 1)
        if p in seen:
            raise Fail(WA, f"PNR {p} bị cấp lại")
        seen.add(p)
        if i % 3:
            say(c, f"RELEASE {p}", "100 OK")


@group("edge")
@cases(*[(f"{GOOD_CARD[:-1]}{(int(GOOD_CARD[-1]) + 1) % 10}", FAR, "123", False), (GOOD_CARD[:-1], FAR, "123", False),
         (GOOD_CARD + "0", FAR, "123", False), ("411111111111111a", FAR, "123", False), ("4111-1111-1111-1111", FAR, "123", False),
         (GOOD_CARD, "01/20", "123", False), (GOOD_CARD, "13/30", "123", False), (GOOD_CARD, "00/30", "123", False),
         (GOOD_CARD, "1/30", "123", False), (GOOD_CARD, "12/9", "123", False), (GOOD_CARD, "12-30", "123", False),
         (GOOD_CARD, "12/030", "123", False), (GOOD_CARD, "aa/bb", "123", False), (GOOD_CARD, FAR, "12", False),
         (GOOD_CARD, FAR, "1234", False), (GOOD_CARD, FAR, "abc", False), (GOOD_CARD, FAR, "12a", False),
         (GOOD_CARD, FAR, "000", True), (GOOD_CARD, "01/99", "999", True), ("0000000000000000", FAR, "123", True),
         (F.make_card("555555555555444"), "06/45", "321", True), (F.make_card("378282246310005"), FAR, "007", True)],
       title="Thẻ {0} hạn {1} CVV {2} → {3}")
def test_card_rules(ctx, num, exp, cvv, ok):
    c = login(ctx, "an")
    pnr, _, _ = book(c, "VN006", "2026-12-21", "ECO", 1)
    say(c, f"PAY {pnr} CARD {num} {exp} {cvv}", f"100 OK PAID {pnr}" if ok else "206 PAYMENT FAILED")
    if not ok:
        say(c, f"PAY {pnr} CARD {GOOD_CARD} {FAR} 123", f"100 OK PAID {pnr}")  # chỗ giữ vẫn còn để thử lại


@group("edge")
@cases((0, True), (1, True), (-1, False), (-12, False), (12, True), title="Hạn thẻ lệch {0} tháng so với hiện tại → hợp lệ: {1}")
def test_card_expiry_month_boundary(ctx, delta, ok):
    c = login(ctx, "an")
    pnr, _, _ = book(c, "VN006", "2026-12-21", "ECO", 1)
    say(c, f"PAY {pnr} CARD {GOOD_CARD} {shift_month(delta)} 123", f"100 OK PAID {pnr}" if ok else "206 PAYMENT FAILED")


@group("edge")
@cases("PAY", "PAY X", "PAY X WALLET extra", "PAY X CARD", f"PAY X CARD {GOOD_CARD}", f"PAY X CARD {GOOD_CARD} {FAR}",
       f"PAY X CARD {GOOD_CARD} {FAR} 123 9", "PAY X BITCOIN", "PAY X wallet", "PAY X Card 1 2 3", "RELEASE", "RELEASE X Y", "PAY  X WALLET",
       title="Cú pháp {0!r} → 201")
def test_pay_release_syntax(ctx, line):
    c = login(ctx, "an")
    say(c, line, "201 INVALID")


@group("edge")
def test_balance_syntax(ctx):
    c = login(ctx, "an")
    say(c, "BALANCE x", "201 INVALID")
    say(c, "BALANCE", "100 OK 50000000")


# ---------------- hết hạn giữ chỗ ----------------

@group("edge")
@timeout(12)
def test_hold_expires_without_commands(ctx):
    """Hết hạn: không ai gửi lệnh trong lúc chờ, lệnh đầu tiên sau đó đã thấy ghế được trả"""
    a = login(ctx, "an")
    pnr, _, _ = book(a, "VN001", D, "ECO", 3)
    expect_seats(a, "VN001", (0, 2))
    time.sleep(T_HOLD + 1.5)
    b = login(ctx, "binh")
    expect_seats(b, "VN001", (3, 2))
    say(a, f"PAY {pnr} WALLET", "208 EXPIRED")
    say(a, f"RELEASE {pnr}", "208 EXPIRED")
    expect_seats(b, "VN001", (3, 2))
    if balance(a) != 50000000:
        raise Fail(WA, "PAY chỗ giữ đã hết hạn không được trừ ví")
    book(b, "VN001", D, "ECO", 3)


@group("edge")
@timeout(12)
def test_pay_before_expiry_ok_and_paid_never_expires(ctx):
    """Trả tiền trước hạn thì vé không bao giờ hết hạn; chỗ không trả thì hết hạn"""
    a = login(ctx, "an")
    paid, _, _ = book(a, "VN001", D, "ECO", 1)
    unpaid, _, _ = book(a, "VN001", D, "ECO", 1)
    time.sleep(0.3)
    say(a, f"PAY {paid} WALLET", f"100 OK PAID {paid}")
    time.sleep(T_HOLD + 1.5)
    expect_seats(a, "VN001", (2, 2))
    say(a, f"PAY {paid} WALLET", "209 ALREADY PAID")
    say(a, f"PAY {unpaid} WALLET", "208 EXPIRED")


@group("edge")
@timeout(12)
def test_expired_seats_bookable_by_others(ctx):
    """Ghế hết hạn được người khác đặt lại ngay; PNR cũ vẫn là EXPIRED với chủ cũ"""
    a, b = login(ctx, "an"), login(ctx, "binh")
    old, _, _ = book(a, "VN002", D, "ECO", 1)
    say(b, f"BOOK VN002 {D} ECO 1", "205 NO SEATS")
    time.sleep(T_HOLD + 1.5)
    new, _, _ = book(b, "VN002", D, "ECO", 1)
    say(a, f"PAY {old} WALLET", "208 EXPIRED")
    say(b, f"PAY {old} WALLET", "203 DENIED")
    say(b, f"PAY {new} WALLET", f"100 OK PAID {new}")


@group("edge")
@timeout(12)
def test_deadline_matches_hold_time(ctx):
    """'Hạn' là giờ địa phương hiện tại + T giây, dạng HH:MM:SS"""
    c = login(ctx, "an")
    for _ in range(3):
        t0 = time.time()
        p, _, dl = book(c, "VJ100", D, "ECO", 1)
        check_deadline(dl, t0)
        say(c, f"RELEASE {p}", "100 OK")
        time.sleep(0.4)


@group("edge")
@args("{port}", "20", "5")
@timeout(12)
def test_longer_hold_time(ctx):
    """T = 5: sau 3 giây chỗ giữ vẫn còn hiệu lực và trả tiền được; hạn lệch đúng 5 giây"""
    c = login(ctx, "an")
    t0 = time.time()
    p, _, dl = book(c, "VN001", D, "ECO", 2)
    check_deadline(dl, t0, hold=5)
    time.sleep(3.0)
    expect_seats(c, "VN001", (1, 2))
    say(c, f"PAY {p} WALLET", f"100 OK PAID {p}")


# ---------------- stream ----------------

@group("stream")
def test_byte_by_byte(ctx):
    """Gửi từng byte một: LOGIN, BOOK, PAY"""
    c = hello(ctx)
    c.send_slowly(f"LOGIN an 1234\n", chunk=1, delay=0.001)
    c.expect_line("100 OK an")
    c.send_slowly(f"BOOK VN006 2026-12-21 ECO 2\n", chunk=1, delay=0.001)
    m = HOLD_RE.match(c.recv_line(timeout=2.0))
    if not m:
        raise Fail(WA, "BOOK từng byte không cho HOLD")
    c.send_slowly(f"PAY {m.group(1)} WALLET\n", chunk=1, delay=0.001)
    c.expect_line(f"100 OK PAID {m.group(1)}")


@group("stream")
def test_many_commands_one_send(ctx):
    """Hàng chục lệnh dính nhau trong một lần gửi"""
    c = hello(ctx)
    c.send("LOGIN an 1234\n" + "SEATS VN001 2026-12-20\n" * 20 + "BALANCE\n" + "BOOK VN001 2026-12-20 ECO 1\n" * 5)
    c.expect_line("100 OK an")
    for _ in range(20):
        c.expect_line("100 OK 3 2")
    c.expect_line("100 OK 50000000")
    got = [c.recv_line(timeout=2.0) for _ in range(5)]
    holds = sum(1 for g in got if HOLD_RE.match(g))
    if holds != 3 or got[3:] != ["205 NO SEATS", "205 NO SEATS"]:
        raise Fail(WA, f"5 lệnh BOOK dính nhau cho {got!r}")


@group("stream")
def test_crlf_and_random_chunks(ctx):
    """\\r\\n và cắt ngẫu nhiên 1–7 byte"""
    c = hello(ctx)
    c.send("LOGIN an 1234\r\n")
    c.expect_line("100 OK an")
    c.send_chunks("SEATS VN001 2026-12-20\n", ctx.rng, delay=0)
    c.expect_line("100 OK 3 2", timeout=2.0)
    c.send_chunks("BALANCE\r\n", ctx.rng, delay=0)
    c.expect_line("100 OK 50000000", timeout=2.0)
    c.send("\r\n")
    c.expect_line("999 UNKNOWN ERROR")


@group("stream")
def test_quit_in_middle_of_batch(ctx):
    """Sau QUIT các lệnh dính phía sau bị bỏ (không BOOK nào được thực hiện)"""
    c = login(ctx, "an")
    c.send("QUIT\nBOOK VN001 2026-12-20 ECO 3\n")
    c.expect_line("100 OK")
    c.expect_closed(timeout=1.5)
    time.sleep(0.2)
    expect_seats(login(ctx, "binh"), "VN001", (3, 2))


# ---------------- robust ----------------

@group("robust")
def test_binary_garbage(ctx):
    """Byte lạ không làm hỏng server"""
    c = login(ctx, "an")
    for junk in [b"\x01\x02", b"BOOK \xff\xfe \x80 ECO 1", b"PAY \xff WALLET", b"\x7f", b"SEATS \xc3\xa9 \xc3\xa9"]:
        c.send(junk + b"\n")
        got = c.recv_line()
        if got not in ("201 INVALID", "999 UNKNOWN ERROR", "202 NOT FOUND"):
            raise Fail(WA, f"byte lạ {junk!r}: nhận {got!r}")
    expect_seats(c, "VN001", (3, 2))


@group("robust")
@timeout(25)
def test_300_sessions_each_holding_seats(ctx):
    """300 phiên lần lượt đặt chỗ rồi RST/đóng: không rò ghế, không rò fd"""
    for i in range(300):
        c = login(ctx, "an", f"c{i}")
        book(c, "VJ100", D, "ECO", 1)
        if i % 2:
            c.reset()
        else:
            c.close()
        ctx.close_quietly(c)
        time.sleep(0.004)
    time.sleep(0.3)
    expect_seats(login(ctx, "binh"), "VJ100", (180, 20))


@group("robust")
def test_dies_mid_command(ctx):
    """Gửi dở lệnh BOOK rồi RST: không có chỗ giữ nào được tạo"""
    c = login(ctx, "an")
    c.send("BOOK VN001 2026-12-20 ECO")
    c.reset()
    time.sleep(0.3)
    ctx.expect_alive()
    expect_seats(login(ctx, "binh"), "VN001", (3, 2))


@group("robust")
@args("{port}", "50", "3600")
@timeout(20)
def test_client_ids_not_reused_for_bookings(ctx):
    """Kết nối mới dùng lại chỗ của kết nối cũ không thừa hưởng chỗ giữ hay đăng nhập"""
    a = login(ctx, "an")
    p, _, _ = book(a, "VN001", D, "ECO", 1)
    a.close()
    time.sleep(0.2)
    b = hello(ctx, "b")
    say(b, "BALANCE", "204 LOGIN FIRST")
    c = login(ctx, "an", "c")
    say(c, f"PAY {p} WALLET", "202 NOT FOUND")
    expect_seats(c, "VN001", (3, 2))


# ---------------- concurrency ----------------

@group("concurrency")
@timeout(15)
def test_race_for_last_seats(ctx):
    """12 client cùng tranh 3 ghế ECO: đúng 3 người được giữ chỗ, 9 người nhận 205; ghế về 0"""
    cs = [login(ctx, ["an", "binh", "chi", "dung"][i % 4], f"c{i}") for i in range(12)]
    for c in cs:
        c.send_line(f"BOOK VN001 {D} ECO 1")
    holds, pnrs = 0, []
    for c in cs:
        got = c.recv_line(timeout=3.0)
        m = HOLD_RE.match(got)
        if m:
            holds += 1
            pnrs.append(m.group(1))
        elif got != "205 NO SEATS":
            raise Fail(WA, f"{c.name}: nhận {got!r}")
    if holds != 3 or len(set(pnrs)) != 3:
        raise Fail(WA, f"{holds} người giữ được 3 ghế cuối (mong đợi 3, PNR khác nhau)")
    expect_seats(cs[0], "VN001", (0, 2))


@group("concurrency")
@timeout(15)
def test_race_multi_pax(ctx):
    """9 client tranh VN006 (12 ghế) với 2/3/4 khách mỗi người: tổng khách được giữ không vượt 12"""
    cs = [login(ctx, ["an", "binh", "chi", "dung"][i % 4], f"c{i}") for i in range(9)]
    asks = [2, 3, 4, 2, 3, 4, 2, 3, 4]
    for c, p in zip(cs, asks):
        c.send_line(f"BOOK VN006 2026-12-21 ECO {p}")
    total = 0
    for c, p in zip(cs, asks):
        got = c.recv_line(timeout=3.0)
        if HOLD_RE.match(got):
            total += p
        elif got != "205 NO SEATS":
            raise Fail(WA, f"{c.name}: nhận {got!r}")
    left = seats(cs[0], "VN006", "2026-12-21")[0]
    if total > 12 or left != 12 - total or total < 9:
        raise Fail(WA, f"tổng khách giữ được {total}, ghế còn {left}")


@group("concurrency")
def test_double_pay_race(ctx):
    """Hai phiên của cùng tài khoản cùng PAY một PNR: đúng một lần được trừ tiền"""
    a, b = login(ctx, "an", "a1"), login(ctx, "an", "a2")
    p, amount, _ = book(a, "VN001", D, "ECO", 1)
    a.send_line(f"PAY {p} WALLET")
    b.send_line(f"PAY {p} WALLET")
    got = sorted([a.recv_line(timeout=2.0), b.recv_line(timeout=2.0)])
    if got != sorted([f"100 OK PAID {p}", "209 ALREADY PAID"]):
        raise Fail(WA, f"hai PAY đồng thời cho {got!r}")
    if balance(a) != 50000000 - amount:
        raise Fail(WA, "bị trừ tiền hai lần")


@group("concurrency")
def test_idle_client_does_not_block(ctx):
    """Client im lặng/gửi dở lệnh không chặn client khác"""
    idle = [hello(ctx, f"idle{i}") for i in range(5)]
    idle[0].send("LOGIN an 12")
    with ctx.verdict(BLOCKED):
        c = login(ctx, "binh")
        book(c, "VN001", D, "ECO", 1)
    idle[0].send("34\n")
    idle[0].expect_line("100 OK an")


# ---------------- stress ----------------

class Model:
    """Mô hình chuẩn (không có hết hạn: dùng với T = 3600)."""

    def __init__(self, fl, wallets):
        self.seats = {(f["code"], f["date"]): [f["eco_seats"], f["bus_seats"]] for f in fl}
        self.price = {(f["code"], f["date"]): [f["eco_price"], f["bus_price"]] for f in fl}
        self.bal = dict(wallets)
        self.bk = {}

    def run(self, user, line):
        t = F.split_line(line)
        name, a = t[0], t[1:]
        if name == "BALANCE":
            return f"100 OK {self.bal[user]}" if not a else "201 INVALID"
        if name == "SEATS":
            if len(a) != 2:
                return "201 INVALID"
            s = self.seats.get((a[0], a[1]))
            return f"100 OK {s[0]} {s[1]}" if s else "202 NOT FOUND"
        if name == "BOOK":
            if len(a) != 4 or not F.valid_date(a[1]) or a[2] not in F.CLASSES or not F.valid_pax(a[3]):
                return "201 INVALID"
            key = (a[0], a[1])
            if key not in self.seats:
                return "202 NOT FOUND"
            cls, pax = F.CLASSES.index(a[2]), int(a[3])
            if self.seats[key][cls] < pax:
                return "205 NO SEATS"
            self.seats[key][cls] -= pax
            return ("HOLD", user, key, cls, pax, self.price[key][cls] * pax)
        if name in ("PAY", "RELEASE"):
            pay = name == "PAY"
            wallet = pay and len(a) == 2 and a[1] == "WALLET"
            card = pay and len(a) == 5 and a[1] == "CARD"
            if (pay and not (wallet or card)) or (not pay and len(a) != 1):
                return "201 INVALID"
            b = self.bk.get(a[0])
            if b is None:
                return "202 NOT FOUND"
            if b["user"] != user:
                return "203 DENIED"
            if b["state"] == "PAID":
                return "209 ALREADY PAID"
            if not pay:
                self.seats[b["key"]][b["cls"]] += b["pax"]
                del self.bk[a[0]]
                return "100 OK"
            if wallet:
                if self.bal[user] < b["amount"]:
                    return "206 PAYMENT FAILED"
                self.bal[user] -= b["amount"]
            else:
                if not card_ok(a[2], a[3], a[4]):
                    return "206 PAYMENT FAILED"
            b["state"] = "PAID"
            return f"100 OK PAID {a[0]}"
        raise AssertionError(line)


def card_ok(num, exp, cvv):
    if not F.luhn_ok(num) or not re.match(r"^[0-9]{3}$", cvv, re.ASCII):
        return False
    m = re.match(r"^([0-9]{2})/([0-9]{2})$", exp, re.ASCII)
    if not m or not 1 <= int(m.group(1)) <= 12:
        return False
    return (2000 + int(m.group(2)), int(m.group(1))) >= current_ym()


@group("stress")
@args("{port}", "10", "3600")
@timeout(40)
def test_random_ops_vs_model(ctx):
    """800 thao tác ngẫu nhiên của 3 phiên (đặt, trả ví/thẻ, giải phóng, hỏi ghế/số dư) so với mô hình"""
    rng = ctx.rng
    fl = F.parse_flights(ctx.read_file("flights.txt"))
    wallets = {}
    for ln in ctx.read_file("wallets.txt").splitlines():
        u, v = ln.split()
        wallets[u] = int(v)
    m = Model(fl, wallets)
    users = ["an", "binh", "dung"]
    cs = {u: login(ctx, u) for u in users}
    keys = [(f["code"], f["date"]) for f in fl]
    mine = {u: [] for u in users}
    allp = []
    for step in range(800):
        u = rng.choice(users)
        c = cs[u]
        r = rng.random()
        if r < 0.3:
            code, date = rng.choice(keys)
            line = f"BOOK {code} {date} {rng.choice(['ECO', 'ECO', 'BUS'])} {rng.choice([1, 1, 2, 3, 9])}"
        elif r < 0.6 and allp:
            p = rng.choice(mine[u] if mine[u] and rng.random() < 0.8 else allp)
            how = rng.choice(["WALLET", "WALLET", "CARD ok", "CARD bad"])
            if how == "WALLET":
                line = f"PAY {p} WALLET"
            elif how == "CARD ok":
                line = f"PAY {p} CARD {GOOD_CARD} {FAR} 123"
            else:
                line = f"PAY {p} CARD {GOOD_CARD} 01/20 123"
        elif r < 0.72 and allp:
            line = f"RELEASE {rng.choice(mine[u] if mine[u] else allp)}"
        elif r < 0.85:
            code, date = rng.choice(keys)
            line = f"SEATS {code} {date}"
        elif r < 0.9:
            line = "BALANCE"
        else:
            line = rng.choice(["PAY ZZZZZZ WALLET", "RELEASE ZZZZZZ", "BOOK x", "PAY", "BALANCE x", f"BOOK VN001 {D} ECO 10"])
        want = m.run(u, line)
        c.send_line(line)
        got = c.recv_line(timeout=2.0)
        if isinstance(want, tuple):
            mt = HOLD_RE.match(got)
            if not mt or int(mt.group(2)) != want[5]:
                raise Fail(WA, f"{u}: {line!r}: mong đợi HOLD với số tiền {want[5]}, nhận {got!r}")
            pnr = mt.group(1)
            if pnr in m.bk:
                raise Fail(WA, f"PNR {pnr} trùng")
            m.bk[pnr] = {"user": u, "state": "HOLD", "key": want[2], "cls": want[3], "pax": want[4], "amount": want[5]}
            mine[u].append(pnr)
            allp.append(pnr)
        elif got != want:
            raise Fail(WA, f"{u}: {line!r}: mong đợi {want!r}, nhận {got!r}")
