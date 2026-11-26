# Thiết kế: docs/TEST-DESIGN.md. Mô hình thông báo (phiên, hàng đợi, trạng thái chuyến) độc lập với lời giải.
import re
import select
import time

import suite_fly as F
from njlib import BLOCKED, WA, Fail, cases, group, sample, timeout

KEY = "admin-2026"
PW = {"an": "1234", "binh": "abcd", "chi": "pass99", "dung": "x1y2z3", "eva": "eva123"}
MIN_RE = re.compile(r"^[1-9][0-9]{0,3}$", re.ASCII)
TIME_RE = re.compile(r"^([01][0-9]|2[0-3]):[0-5][0-9]$", re.ASCII)


class Model:
    def __init__(self, ctx):
        self.fl = {f["code"]: {"status": "ON_TIME", "date": f["date"], "dep": f["dep"], "arr": f["arr"]} for f in F.parse_flights(ctx.read_file("flights.txt"))}
        self.holders = {}
        for ln in ctx.read_file("tickets.txt").splitlines():
            no, user, code, date, cls, pax, price, status = ln.split(" ")
            if status == "PAID":
                self.holders.setdefault(code, set()).add(user)
        self.sess = {}      # sid -> {"user": str|None, "admin": bool}
        self.queue = {}     # user -> [dòng]

    def open(self, sid):
        self.sess[sid] = {"user": None, "admin": False}

    def close(self, sid):
        self.sess.pop(sid, None)

    def online(self, user):
        return [s for s, v in self.sess.items() if v["user"] == user]

    def run(self, sid, line):
        """Trả về danh sách (sid nhận, dòng) theo thứ tự gửi (phản hồi cho sid đứng cuối, trừ LOGIN: sau phản hồi là hàng đợi)."""
        s = self.sess[sid]
        toks = F.split_line(line)
        name, a = toks[0], toks[1:]
        if name == "LOGIN":
            if not F.valid_account_args(a):
                return [(sid, "201 INVALID")]
            if s["user"]:
                return [(sid, "207 ALREADY LOGGED IN")]
            if PW.get(a[0]) != a[1]:
                return [(sid, "203 DENIED")]
            was_online = bool(self.online(a[0]))
            s["user"] = a[0]
            out = [(sid, f"100 OK {a[0]}")]
            if not was_online:
                out += [(sid, ln) for ln in self.queue.pop(a[0], [])]
            return out
        if name == "ADMIN":
            if len(a) != 1:
                return [(sid, "201 INVALID")]
            if a[0] != KEY:
                return [(sid, "203 DENIED")]
            s["admin"] = True
            return [(sid, "100 OK")]
        if name == "STATUS":
            if len(a) != 1:
                return [(sid, "201 INVALID")]
            f = self.fl.get(a[0])
            if f is None:
                return [(sid, "202 NOT FOUND")]
            st = f["status"]
            txt = {"ON_TIME": "ON_TIME", "CANCELLED": "CANCELLED"}.get(st) or (f"DELAYED {f['delay']}" if st == "DELAYED" else
                                                                              f"RESCHEDULED {f['date']} {f['dep']} {f['arr']}")
            return [(sid, f"100 OK {txt}")]
        if name in ("DELAY", "RESCHEDULE", "CANCELFLIGHT"):
            if not s["admin"]:
                return [(sid, "203 DENIED")]
            need = {"DELAY": 2, "RESCHEDULE": 4, "CANCELFLIGHT": 1}[name]
            if len(a) != need:
                return [(sid, "201 INVALID")]
            if name == "DELAY" and not (MIN_RE.match(a[1]) and int(a[1]) <= 1440):
                return [(sid, "201 INVALID")]
            if name == "RESCHEDULE" and not (F.valid_date(a[1]) and TIME_RE.match(a[2]) and TIME_RE.match(a[3])):
                return [(sid, "201 INVALID")]
            f = self.fl.get(a[0])
            if f is None:
                return [(sid, "202 NOT FOUND")]
            if f["status"] == "CANCELLED":
                return [(sid, "209 ALREADY CANCELLED")]
            if name == "DELAY":
                f["status"], f["delay"] = "DELAYED", int(a[1])
                msg = f"301 NOTIFY DELAY {a[0]} {int(a[1])}"
            elif name == "RESCHEDULE":
                f["status"], f["date"], f["dep"], f["arr"] = "RESCHEDULED", a[1], a[2], a[3]
                msg = f"301 NOTIFY RESCHEDULE {a[0]} {a[1]} {a[2]} {a[3]}"
            else:
                f["status"] = "CANCELLED"
                msg = f"301 NOTIFY CANCEL {a[0]}"
            out = []
            users = sorted(self.holders.get(a[0], ()))
            for u in users:
                on = self.online(u)
                if on:
                    out += [(x, msg) for x in on]
                else:
                    self.queue.setdefault(u, []).append(msg)
            return out + [(sid, f"100 OK {len(users)}")]
        if name == "QUIT" and not a:
            return [(sid, "100 OK")]
        return [(sid, "999 UNKNOWN ERROR")]


class Env:
    def __init__(self, ctx):
        self.ctx = ctx
        self.m = Model(ctx)
        self.c = {}

    def connect(self, sid, user=None, admin=False):
        self.c[sid] = self.ctx.connect(name=f"s{sid}")
        self.m.open(sid)
        if user:
            self.say(sid, f"LOGIN {user} {PW[user]}")
        if admin:
            self.say(sid, f"ADMIN {KEY}")
        return self.c[sid]

    def say(self, sid, line, timeout=2.0, silence=0.0):
        exp = self.m.run(sid, line)
        self.c[sid].send_line(line)
        per = {}
        for t, ln in exp:
            per.setdefault(t, []).append(ln)
        for t, lines in per.items():
            for ln in lines:
                got = self.c[t].recv_line(timeout=timeout)
                if got != ln:
                    raise Fail(WA, f"s{t} (sau lệnh {line!r} của s{sid}): mong đợi {ln!r}, nhận {got!r}")
        if silence:
            for t, conn in self.c.items():
                if t not in per and t in self.m.sess and conn.sock.fileno() >= 0:
                    conn.expect_silence(silence)
        return exp

    def leave(self, sid, how="close"):
        conn = self.c[sid]
        if how == "quit":
            self.say(sid, "QUIT")
            conn.expect_closed()
        elif how == "rst":
            conn.reset()
        else:
            conn.close()
        self.m.close(sid)
        time.sleep(0.12)


# ---------------- sample ----------------

@sample
def test_notify_online_and_queue_offline(ctx):
    """DELAY: khách online nhận ngay, khách offline được xếp hàng và nhận ngay sau khi đăng nhập"""
    e = Env(ctx)
    e.connect(1, "an")
    e.connect(2, admin=True)
    e.say(2, "DELAY VN100 45", silence=0.05)
    e.connect(3)
    e.say(3, "LOGIN binh abcd")
    e.say(1, "STATUS VN100")


@sample
def test_admin_only_and_key(ctx):
    """Lệnh admin khi chưa ADMIN → 203; khóa sai → 203; STATUS không đổi"""
    e = Env(ctx)
    e.connect(1, "an")
    for line in ["DELAY VN100 10", "RESCHEDULE VN100 2026-12-21 09:00 11:00", "CANCELFLIGHT VN100", f"ADMIN wrong", "ADMIN", "DELAY VN100 10", "STATUS VN100"]:
        e.say(1, line, silence=0.05)


@sample
def test_reschedule_and_cancel(ctx):
    """RESCHEDULE và CANCELFLIGHT gửi đúng thông báo; chuyến đã hủy → 209"""
    e = Env(ctx)
    e.connect(1, "an")
    e.connect(2, "binh")
    e.connect(3, admin=True)
    for line in ["RESCHEDULE VN100 2026-12-21 09:00 11:05", "STATUS VN100", "CANCELFLIGHT VN100", "STATUS VN100", "DELAY VN100 5", "CANCELFLIGHT VN100"]:
        e.say(3, line)


# ---------------- basic ----------------

@group("basic")
@cases(("VN100", 2), ("VN200", 1), ("VJ300", 1), ("QH400", 1), ("BL500", 0), ("VN600", 3), title="DELAY {0}: nhận 100 OK {1} (số khách có vé PAID)")
def test_recipient_counts(ctx, code, k):
    e = Env(ctx)
    for sid, u in enumerate(["an", "binh", "chi", "dung", "eva"], 1):
        e.connect(sid, u)
    e.connect(9, admin=True)
    exp = e.say(9, f"DELAY {code} 30", silence=0.05)
    if exp[-1][1] != f"100 OK {k}":
        raise Fail(WA, f"mô hình nội bộ lệch: {exp[-1]}")


@group("basic")
def test_same_user_many_tickets_one_message(ctx):
    """an có hai vé trên VN100 nhưng mỗi phiên chỉ nhận một dòng"""
    e = Env(ctx)
    e.connect(1, "an")
    e.connect(2, "an")
    e.connect(9, admin=True)
    e.say(9, "DELAY VN100 20", silence=0.1)


@group("basic")
def test_cancelled_ticket_not_notified(ctx):
    """chi chỉ có vé CANCELLED trên VN100: không nhận thông báo VN100"""
    e = Env(ctx)
    e.connect(1, "chi")
    e.connect(9, admin=True)
    e.say(9, "DELAY VN100 20", silence=0.1)
    e.say(9, "DELAY VN200 20", silence=0.1)


@group("basic")
def test_offline_queue_order_and_once(ctx):
    """Nhiều sự kiện khi offline: giao đúng thứ tự ngay sau 100 OK, chỉ một lần"""
    e = Env(ctx)
    e.connect(9, admin=True)
    for line in ["DELAY VN100 10", "DELAY VN100 20", "RESCHEDULE VN100 2026-12-22 10:00 12:00", "DELAY VN600 5", "CANCELFLIGHT VN100"]:
        e.say(9, line)
    e.connect(1)
    e.say(1, "LOGIN an 1234")
    e.connect(2)
    e.say(2, "LOGIN an 1234", silence=0.05)  # phiên thứ hai khi phiên một đang online: không nhận lại
    e.leave(1)
    e.leave(2)
    e.connect(3)
    e.say(3, "LOGIN an 1234", silence=0.1)  # hàng đợi đã rỗng


@group("basic")
def test_queue_is_per_user(ctx):
    """Hàng đợi của binh không lộ cho an; mỗi người nhận đúng phần của mình"""
    e = Env(ctx)
    e.connect(9, admin=True)
    for line in ["DELAY VN100 10", "DELAY VJ300 15", "DELAY QH400 25", "CANCELFLIGHT VN600"]:
        e.say(9, line)
    for sid, u in enumerate(["dung", "binh", "an", "chi", "eva"], 1):
        e.connect(sid)
        e.say(sid, f"LOGIN {u} {PW[u]}")


@group("basic")
def test_login_again_after_leaving_gets_new_events_only(ctx):
    """Rời đi rồi đăng nhập lại chỉ nhận sự kiện xảy ra trong lúc offline"""
    e = Env(ctx)
    e.connect(1, "binh")
    e.connect(9, admin=True)
    e.say(9, "DELAY VN100 10")
    e.leave(1, "quit")
    e.say(9, "DELAY VJ300 20")
    e.say(9, "CANCELFLIGHT VN600")
    e.connect(2)
    e.say(2, "LOGIN binh abcd")


@group("basic")
def test_admin_session_is_not_a_recipient(ctx):
    """Phiên admin không nhận thông báo trừ khi nó đăng nhập bằng tài khoản có vé"""
    e = Env(ctx)
    e.connect(9, admin=True)
    e.say(9, "DELAY VN100 10", silence=0.05)
    e.say(9, "LOGIN an 1234")
    e.say(9, "DELAY VN100 11")


@group("basic")
def test_status_transitions(ctx):
    """STATUS qua các trạng thái ON_TIME → DELAYED → RESCHEDULED → DELAYED → CANCELLED"""
    e = Env(ctx)
    e.connect(9, admin=True)
    for line in ["STATUS VN200", "DELAY VN200 90", "STATUS VN200", "RESCHEDULE VN200 2026-12-22 06:00 08:10", "STATUS VN200", "DELAY VN200 15",
                 "STATUS VN200", "CANCELFLIGHT VN200", "STATUS VN200", "STATUS ZZ1", "STATUS", "STATUS VN200 x"]:
        e.say(9, line)


@group("basic")
def test_login_rules(ctx):
    """LOGIN: 201 / 207 / 203; QUIT; lệnh lạ"""
    e = Env(ctx)
    e.connect(1)
    for line in ["LOGIN an", "LOGIN an 12345", "LOGIN nobody 1234", "LOGIN an 1234", "LOGIN an 1234", "LOGIN binh abcd", "PING", "", "login an 1234", "QUIT x"]:
        e.say(1, line)


# ---------------- edge ----------------

@group("edge")
@cases("DELAY", "DELAY VN100", "DELAY VN100 0", "DELAY VN100 1", "DELAY VN100 1440", "DELAY VN100 1441", "DELAY VN100 01", "DELAY VN100 -5",
       "DELAY VN100 +5", "DELAY VN100 9999", "DELAY VN100 12345", "DELAY VN100 4.5", "DELAY VN100 abc", "DELAY VN100 10 x", "DELAY  VN100 10",
       "DELAY ZZ9 10", "delay VN100 10", "DELAY VN100  10", title="Admin gửi {0!r}")
def test_delay_syntax(ctx, line):
    e = Env(ctx)
    e.connect(1, "an")
    e.connect(9, admin=True)
    e.say(9, line, silence=0.05)
    e.say(9, "STATUS VN100")


@group("edge")
@cases("RESCHEDULE", "RESCHEDULE VN100", "RESCHEDULE VN100 2026-12-21", "RESCHEDULE VN100 2026-12-21 09:00", "RESCHEDULE VN100 2026-12-21 09:00 11:00",
       "RESCHEDULE VN100 2026-12-21 09:00 11:00 x", "RESCHEDULE VN100 2026-02-30 09:00 11:00", "RESCHEDULE VN100 2100-02-29 09:00 11:00",
       "RESCHEDULE VN100 2024-02-29 00:00 23:59", "RESCHEDULE VN100 2026-12-21 24:00 11:00", "RESCHEDULE VN100 2026-12-21 09:60 11:00",
       "RESCHEDULE VN100 2026-12-21 9:00 11:00", "RESCHEDULE VN100 2026-12-21 09:00 11:0", "RESCHEDULE VN100 2026-12-21 23:30 01:15",
       "RESCHEDULE VN100 2026-12-21 09:00 09:00", "RESCHEDULE ZZ9 2026-12-21 09:00 11:00", "RESCHEDULE VN100 2026/12/21 09:00 11:00",
       title="Admin gửi {0!r}")
def test_reschedule_syntax(ctx, line):
    e = Env(ctx)
    e.connect(1, "binh")
    e.connect(9, admin=True)
    e.say(9, line, silence=0.05)
    e.say(9, "STATUS VN100")


@group("edge")
@cases("CANCELFLIGHT", "CANCELFLIGHT VN100 x", "CANCELFLIGHT ZZ9", "CANCELFLIGHT  VN100", "cancelflight VN100", "CANCELFLIGHT VN100", title="Admin gửi {0!r}")
def test_cancel_syntax(ctx, line):
    e = Env(ctx)
    e.connect(1, "an")
    e.connect(9, admin=True)
    e.say(9, line, silence=0.05)
    e.say(9, "STATUS VN100")


@group("edge")
def test_check_order_for_admin_commands(ctx):
    """Thứ tự: chưa admin 203 → cú pháp 201 → không có chuyến 202 → đã hủy 209"""
    e = Env(ctx)
    e.connect(1, "an")
    e.connect(9)
    for line in ["DELAY", "DELAY ZZ9 0", "CANCELFLIGHT"]:
        e.say(9, line)
    e.say(9, f"ADMIN {KEY}")
    for line in ["DELAY", "DELAY ZZ9 0", "DELAY ZZ9 5", "CANCELFLIGHT VJ300", "DELAY VJ300 0", "DELAY VJ300 5", "RESCHEDULE VJ300 2026-12-30 08:00 09:00",
                 "RESCHEDULE VJ300 bad 08:00 09:00", "CANCELFLIGHT VJ300"]:
        e.say(9, line, silence=0.03)


@group("edge")
def test_admin_key_variants(ctx):
    """Khóa phân biệt hoa thường, không khớp tiền tố; ADMIN gọi lại vẫn 100 OK"""
    e = Env(ctx)
    e.connect(1)
    for line in ["ADMIN admin-2026x", "ADMIN admin-202", "ADMIN ADMIN-2026", "ADMIN  admin-2026", "ADMIN admin-2026 x", f"ADMIN {KEY}", f"ADMIN {KEY}", "DELAY VN100 5"]:
        e.say(1, line)


# ---------------- stream ----------------

@group("stream")
def test_byte_by_byte(ctx):
    """Lệnh gửi từng byte một"""
    e = Env(ctx)
    e.connect(1, "an")
    e.connect(9)
    for line in [f"ADMIN {KEY}", "DELAY VN100 33"]:
        exp = e.m.run(9, line)
        e.c[9].send_slowly(line + "\n", chunk=1, delay=0.001)
        got = {}
        for t, ln in exp:
            e.c[t].expect_line(ln, timeout=2.0)


@group("stream")
def test_many_commands_one_send(ctx):
    """Admin gửi 20 lệnh dính nhau; khách nhận đủ thông báo theo thứ tự"""
    e = Env(ctx)
    e.connect(1, "an")
    e.connect(9)
    lines = [f"ADMIN {KEY}"] + [f"DELAY VN100 {i + 1}" for i in range(20)]
    exp = []
    for ln in lines:
        exp += e.m.run(9, ln)
    e.c[9].send("".join(x + "\n" for x in lines))
    for t, ln in exp:
        e.c[t].expect_line(ln, timeout=3.0)


@group("stream")
def test_crlf_and_chunks(ctx):
    """\\r\\n và cắt ngẫu nhiên 1–7 byte"""
    e = Env(ctx)
    e.connect(1, "binh")
    e.connect(9)
    for line in [f"ADMIN {KEY}", "DELAY VJ300 7", "STATUS VJ300", "CANCELFLIGHT VJ300", ""]:
        exp = e.m.run(9, line)
        if ctx.rng.random() < 0.5:
            e.c[9].send(line + "\r\n")
        else:
            e.c[9].send_chunks(line + "\n", ctx.rng, delay=0)
        for t, ln in exp:
            e.c[t].expect_line(ln, timeout=2.0)


# ---------------- robust ----------------

@group("robust")
@timeout(20)
def test_dead_session_does_not_kill_server(ctx):
    """Phiên của khách đã đóng ngay trước sự kiện: server không chết, các phiên còn lại vẫn nhận đủ"""
    e = Env(ctx)
    e.connect(1, "an")
    e.connect(2, "an")
    e.connect(9, admin=True)
    e.c[2].close()
    for i in range(4):
        exp = e.m.run(9, f"DELAY VN100 {i + 1}")
        e.c[9].send_line(f"DELAY VN100 {i + 1}")
        e.c[1].expect_line(f"301 NOTIFY DELAY VN100 {i + 1}", timeout=3.0)
        e.c[9].expect_line("100 OK 2", timeout=3.0)
        time.sleep(0.05)
    ctx.expect_alive()


@group("robust")
@timeout(25)
def test_burst_to_session_closed_just_before(ctx):
    """Phiên cùng tài khoản đóng ngay trước một loạt sự kiện dồn trong một lần gửi: server không chết (5 vòng)"""
    admin = ctx.connect("admin")
    admin.send_line(f"ADMIN {KEY}")
    admin.expect_line("100 OK")
    for rnd in range(5):
        a1 = ctx.connect(f"a1-{rnd}")
        a1.send_line("LOGIN an 1234")
        a1.expect_line("100 OK an")
        a2 = ctx.connect(f"a2-{rnd}")
        a2.send_line("LOGIN an 1234")
        a2.expect_line("100 OK an")
        a2.close()
        admin.send("".join(f"DELAY VN100 {k}\n" for k in range(1, 7)))
        for k in range(1, 7):
            a1.expect_line(f"301 NOTIFY DELAY VN100 {k}", timeout=3.0)
            admin.expect_line("100 OK 2", timeout=3.0)
        a1.close()
        time.sleep(0.1)
    ctx.expect_alive()


@group("robust")
@cases("quit", "rst", title="Admin rời đi ({0}) rồi kết nối mới dùng lại chỗ: không thừa quyền admin")
def test_admin_flag_not_inherited(ctx, how):
    e = Env(ctx)
    e.connect(9, admin=True)
    e.say(9, "STATUS VN100")
    e.leave(9, how)
    e.connect(10)
    e.say(10, "DELAY VN100 5")
    e.say(10, "STATUS VN100")


@group("robust")
def test_binary_garbage(ctx):
    """Byte lạ không làm hỏng server"""
    e = Env(ctx)
    e.connect(1, "an", admin=True)
    for junk in [b"\x01\x02", b"DELAY \xff\xfe \x80", b"RESCHEDULE \xff", b"ADMIN \xc3\xa9", b"\x7f"]:
        e.c[1].send(junk + b"\n")
        got = e.c[1].recv_line()
        if got not in ("201 INVALID", "202 NOT FOUND", "203 DENIED", "999 UNKNOWN ERROR"):
            raise Fail(WA, f"byte lạ {junk!r}: nhận {got!r}")
    e.say(1, "STATUS VN100")


@group("robust")
@timeout(25)
def test_300_login_cycles(ctx):
    """300 lượt đăng nhập–thoát (đóng/RST) rồi sự kiện: không rò fd, hàng đợi đúng"""
    e = Env(ctx)
    for i in range(300):
        c = ctx.connect(name=f"c{i}")
        c.send_line("LOGIN binh abcd")
        c.expect_line("100 OK binh")
        c.reset() if i % 2 else c.close()
        ctx.close_quietly(c)
        time.sleep(0.003)
    time.sleep(0.2)
    e.connect(9, admin=True)
    e.say(9, "DELAY VJ300 9")
    e.connect(1)
    e.say(1, "LOGIN binh abcd")


@group("robust")
@timeout(25)
def test_queue_of_300_events(ctx):
    """300 sự kiện khi offline được giao đủ, đúng thứ tự"""
    e = Env(ctx)
    e.connect(9, admin=True)
    for i in range(300):
        e.say(9, f"DELAY VJ300 {(i % 1440) + 1}")
    e.connect(1)
    e.c[1].send_line("LOGIN binh abcd")
    e.c[1].expect_line("100 OK binh", timeout=3.0)
    for i in range(300):
        e.c[1].expect_line(f"301 NOTIFY DELAY VJ300 {(i % 1440) + 1}", timeout=3.0)
    e.c[1].expect_silence(0.1)


# ---------------- concurrency ----------------

@group("concurrency")
@timeout(20)
def test_20_sessions_all_receive_in_order(ctx):
    """20 phiên (an/binh) cùng nhận 15 thông báo đúng thứ tự"""
    e = Env(ctx)
    for sid in range(1, 21):
        e.connect(sid, "an" if sid % 2 else "binh")
    e.connect(99, admin=True)
    for i in range(15):
        e.say(99, f"DELAY VN100 {i + 1}")


@group("concurrency")
def test_idle_client_does_not_block(ctx):
    """Client im lặng/gửi dở lệnh không chặn client khác"""
    e = Env(ctx)
    idle = [ctx.connect(f"idle{i}") for i in range(4)]
    idle[0].send("LOGIN an 12")
    e.connect(1, "an")
    e.connect(9, admin=True)
    with ctx.verdict(BLOCKED):
        e.say(9, "DELAY VN100 8")
    idle[0].send("34\n")
    idle[0].expect_line("100 OK an")


# ---------------- stress ----------------

@group("stress")
@timeout(60)
def test_random_ops_vs_model(ctx):
    """800 thao tác ngẫu nhiên: đăng nhập, rời đi (QUIT/đóng/RST), sự kiện admin, STATUS; so với mô hình"""
    rng = ctx.rng
    e = Env(ctx)
    nxt = [0]
    users = list(PW)
    codes = ["VN100", "VN200", "VJ300", "QH400", "BL500", "VN600"]

    def new_session(user=None):
        nxt[0] += 1
        sid = nxt[0]
        e.connect(sid)
        if user:
            e.say(sid, f"LOGIN {user} {PW[user]}")
        return sid

    admin = new_session()
    e.say(admin, f"ADMIN {KEY}")
    live = [new_session(rng.choice(users)) for _ in range(3)]
    for step in range(800):
        r = rng.random()
        if r < 0.35:
            code = rng.choice(codes)
            line = rng.choice([f"DELAY {code} {rng.randint(1, 1440)}", f"DELAY {code} {rng.randint(1, 1440)}",
                               f"RESCHEDULE {code} 2026-12-{rng.randint(10, 30)} 0{rng.randint(0, 9)}:{rng.randint(10, 59)} 1{rng.randint(0, 9)}:10",
                               f"CANCELFLIGHT {code}" if rng.random() < 0.15 else f"DELAY {code} 1"])
            e.say(admin, line)
        elif r < 0.55 and len(live) < 8:
            live.append(new_session(rng.choice(users) if rng.random() < 0.7 else None))
        elif r < 0.7 and live:
            sid = rng.choice(live)
            if e.m.sess[sid]["user"] is None:
                u = rng.choice(users)
                e.say(sid, f"LOGIN {u} {PW[u]}")
            else:
                e.say(sid, rng.choice(["LOGIN an 1234", "STATUS " + rng.choice(codes), "PING"]))
        elif r < 0.85 and live:
            sid = live.pop(rng.randrange(len(live)))
            e.leave(sid, rng.choice(["close", "rst", "quit"]))
        else:
            e.say(admin, rng.choice(["STATUS " + rng.choice(codes), "DELAY VN100 0", "DELAY ZZ9 5", "CANCELFLIGHT"]))
        if not live:
            live.append(new_session(rng.choice(users)))
