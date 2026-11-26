"""Mô hình Python của giao thức FLY dùng chung cho các bài fly-* (xem docs/THIET-KE-BTL-VE-MAY-BAY.md).

Các test đọc `flights.txt` thật trong thư mục chạy (ctx.read_file) rồi so với mô hình ở đây,
nên mô hình độc lập với lời giải C.
"""
import re
from datetime import date as _date

AIRPORT_RE = re.compile(r"^[A-Z]{3}$", re.ASCII)
DATE_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$", re.ASCII)
USER_RE = re.compile(r"^[a-z0-9]{1,32}$", re.ASCII)
PASS_RE = re.compile(r"^[\x21-\x7e]{4,32}$", re.ASCII)
CLASSES = ("ECO", "BUS")


def valid_date(s):
    """YYYY-MM-DD là ngày có thật, năm 1900..2100."""
    if not DATE_RE.match(s):
        return False
    y, m, d = int(s[:4]), int(s[5:7]), int(s[8:])
    if not 1900 <= y <= 2100:
        return False
    try:
        _date(y, m, d)
    except ValueError:
        return False
    return True


def valid_pax(s):
    return len(s) == 1 and "1" <= s <= "9"


def split_line(line):
    """Bỏ '\\n' do người gọi; bỏ đúng một '\\r' cuối dòng; tách theo ĐÚNG một dấu cách."""
    if line.endswith("\r"):
        line = line[:-1]
    return line.split(" ")


def valid_search_args(a):
    """a = các thành phần sau chữ SEARCH."""
    if len(a) not in (5, 6):
        return False
    frm, to, d, pax, cls = a[:5]
    if not (AIRPORT_RE.match(frm) and AIRPORT_RE.match(to)) or frm == to:
        return False
    if not valid_date(d) or not valid_pax(pax) or cls not in CLASSES:
        return False
    if len(a) == 6 and not (valid_date(a[5]) and a[5] >= d):
        return False
    return True


def valid_account_args(a):
    return len(a) == 2 and bool(USER_RE.match(a[0])) and bool(PASS_RE.match(a[1]))


def parse_flights(text):
    out = []
    for ln in text.splitlines():
        w = ln.split()
        if len(w) != 11:
            continue
        out.append({"code": w[0], "airline": w[1], "from": w[2], "to": w[3], "date": w[4], "dep": w[5],
                    "arr": w[6], "eco_price": int(w[7]), "eco_seats": int(w[8]),
                    "bus_price": int(w[9]), "bus_seats": int(w[10])})
    return out


def minutes(hhmm):
    return int(hhmm[:2]) * 60 + int(hhmm[3:])


def duration(f):
    """Thời gian bay (phút); giờ đến nhỏ hơn giờ đi nghĩa là hạ cánh sang ngày hôm sau."""
    d = minutes(f["arr"]) - minutes(f["dep"])
    return d if d > 0 else d + 1440


def price(f, cls):
    return f["eco_price"] if cls == "ECO" else f["bus_price"]


def seats(f, cls):
    return f["eco_seats"] if cls == "ECO" else f["bus_seats"]


def search(flights, frm, to, d, pax, cls):
    """Các chuyến theo thứ tự trong tệp, còn đủ ghế; mỗi dòng '<mã> <hãng> <giờ đi> <giờ đến> <tổng giá>'."""
    return [f"{f['code']} {f['airline']} {f['dep']} {f['arr']} {price(f, cls) * int(pax)}"
            for f in flights
            if f["from"] == frm and f["to"] == to and f["date"] == d and seats(f, cls) >= int(pax)]


def search_reply(flights, a):
    """Phản hồi (danh sách dòng) cho SEARCH với các thành phần a đã hợp lệ."""
    frm, to, d, pax, cls = a[:5]
    out = search(flights, frm, to, d, pax, cls)
    res = [f"110 FLIGHTS {len(out)}"] + out
    if len(a) == 6:
        back = search(flights, to, frm, a[5], pax, cls)
        res += [f"111 RETURN {len(back)}"] + back
    return res


def luhn_ok(digits):
    if not re.match(r"^[0-9]{16}$", digits, re.ASCII):
        return False
    s = 0
    for i, ch in enumerate(reversed(digits)):
        n = int(ch)
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        s += n
    return s % 10 == 0


def make_card(prefix, rng=None):
    """Sinh số thẻ 16 chữ số đúng Luhn từ tiền tố 15 chữ số (thêm chữ số kiểm tra)."""
    assert len(prefix) == 15
    for d in "0123456789":
        if luhn_ok(prefix + d):
            return prefix + d
    raise AssertionError
