import os

from njlib import LIMIT, WA, Fail, args, cases, group, sample, timeout

Q2 = "Q 2 Hàm nào chuyển cổng sang thứ tự mạng?|ntohs|htonl|htons|inet_pton"
ANSWERS = "BCBCC"


def ask(u, req, want):
    u.send(req.encode())
    u.expect(want.encode())


def player(ctx, name):
    u = ctx.udp(name)
    ask(u, f"JOIN {name}", f"WELCOME {name} 5")
    return u


@sample
def test_example(ctx):
    """Ví dụ trong đề"""
    a = player(ctx, "an")
    ask(a, "Q 2", Q2)
    ask(a, "ANS 2 C", "CORRECT")
    ask(a, "ANS 2 A", "ANSWERED")
    ask(a, "SCORE", "SCORE 1 1")
    b = ctx.udp("B")
    ask(b, "SCORE", "JOIN_FIRST")


@sample
def test_all_questions(ctx):
    """Đọc đủ 5 câu, trả lời đúng/sai"""
    a = player(ctx, "an")
    ask(a, "Q 1", "Q 1 Giao thức nào hướng luồng byte?|UDP|TCP|ICMP|ARP")
    ask(a, "Q 5", "Q 5 Tiến trình con kết thúc mà cha chưa waitpid gọi là?|orphan|daemon|zombie|thread")
    for i, x in enumerate(ANSWERS, 1):
        ask(a, f"ANS {i} {x if i % 2 else 'A'}", "CORRECT" if i % 2 else "WRONG")
    ask(a, "SCORE", "SCORE 3 5")


@group("basic")
def test_invalid_and_errors(ctx):
    """INVALID / ERROR / JOIN_FIRST / ALREADY"""
    u = ctx.udp("U")
    for req in ["Q 1", "ANS 1 A", "TOP", "LEAVE"]:
        ask(u, req, "JOIN_FIRST")
    for req in ["", "HELLO", "JOIN", "JOIN a b", "join an", "JOIN " + "x" * 33]:
        ask(u, req, "ERROR")
    ask(u, "JOIN an", "WELCOME an 5")
    ask(u, "JOIN an", "ALREADY")
    for req in ["Q 0", "Q 6", "Q x", "ANS 6 A", "ANS 1 E", "ANS 1 a", "ANS x A"]:
        ask(u, req, "INVALID")
    for req in ["Q", "ANS 1", "SCORE 1", "Q 1 2"]:
        ask(u, req, "ERROR")


@group("basic")
def test_top(ctx):
    """TOP: điểm giảm dần, cùng điểm thì tên tăng dần, tối đa 3"""
    c = player(ctx, "cuong")
    a = player(ctx, "an")
    b = player(ctx, "binh")
    for i in (1, 2, 3):
        ask(c, f"ANS {i} {ANSWERS[i - 1]}", "CORRECT")
    for i in (1, 2):
        ask(b, f"ANS {i} {ANSWERS[i - 1]}", "CORRECT")
        ask(a, f"ANS {i} {ANSWERS[i - 1]}", "CORRECT")
    ask(a, "TOP", "TOP cuong:3 an:2 binh:2")


@args("{port}", "questions.txt", "2")
@group("concurrency")
def test_limit_and_leave(ctx):
    """N=2: người thứ 3 nhận FULL; LEAVE giải phóng chỗ và xoá điểm"""
    a = player(ctx, "an")
    b = player(ctx, "binh")
    ask(a, "ANS 1 B", "CORRECT")
    with ctx.verdict(LIMIT):
        c = ctx.udp("C")
        ask(c, "JOIN cuong", "FULL")
        ask(a, "LEAVE", "BYE")
        ask(c, "JOIN cuong", "WELCOME cuong 5")
    ask(a, "SCORE", "JOIN_FIRST")
    ask(a, "JOIN an", "FULL")
    ask(b, "TOP", "TOP binh:0 cuong:0")


@group("basic")
def test_players_isolated(ctx):
    """Điểm và trạng thái đã trả lời tách biệt theo từng địa chỉ"""
    a = player(ctx, "an")
    b = player(ctx, "binh")
    ask(a, "ANS 3 B", "CORRECT")
    ask(b, "ANS 3 A", "WRONG")
    ask(b, "ANS 3 B", "ANSWERED")
    ask(a, "SCORE", "SCORE 1 1")
    ask(b, "SCORE", "SCORE 0 1")


# ======================= phần mở rộng (thiết kế lại) =======================

def load_questions(name):
    raw = open(os.path.join(os.path.dirname(__file__), "..", "files", name), "rb").read().decode()
    qs = []
    for line in raw.replace("\r", "").split("\n"):
        if line:
            text, ans = line.rsplit("|", 1)
            qs.append((text, ans))
    return qs


Q100 = load_questions("q100.txt")
Q5 = load_questions("questions.txt")


class Model:
    def __init__(self, qs, limit):
        self.qs, self.limit, self.players = qs, limit, {}

    def run(self, who, req):
        w = [t for t in req.split(" ") if t][:4]
        nt, cmd = len(w), (w[0] if w else "")
        p = self.players.get(who)
        if cmd == "JOIN" and nt == 2 and len(w[1].encode()) <= 32:
            if p:
                return "ALREADY"
            if len(self.players) >= self.limit:
                return "FULL"
            self.players[who] = {"name": w[1], "c": 0, "a": 0, "done": set()}
            return f"WELCOME {w[1]} {len(self.qs)}"
        known = (cmd == "Q" and nt == 2) or (cmd == "ANS" and nt == 3) or (cmd in ("SCORE", "TOP", "LEAVE") and nt == 1)
        if not known:
            return "ERROR"
        if not p:
            return "JOIN_FIRST"
        if cmd in ("Q", "ANS"):
            s = w[1]
            i = int(s) if s.isascii() and s.isdigit() and len(s) <= 3 else 0
            if not 1 <= i <= len(self.qs):
                i = 0
        if cmd == "Q":
            return f"Q {i} {self.qs[i - 1][0]}" if i else "INVALID"
        if cmd == "ANS":
            x = w[2]
            if not i or len(x) != 1 or x not in "ABCD":
                return "INVALID"
            if i in p["done"]:
                return "ANSWERED"
            p["done"].add(i)
            p["a"] += 1
            ok = x == self.qs[i - 1][1]
            p["c"] += ok
            return "CORRECT" if ok else "WRONG"
        if cmd == "SCORE":
            return f"SCORE {p['c']} {p['a']}"
        if cmd == "TOP":
            rank = sorted(self.players.values(), key=lambda q: (-q["c"], q["name"].encode()))[:3]
            return " ".join(["TOP"] + [f"{q['name']}:{q['c']}" for q in rank])
        del self.players[who]
        return "BYE"


def drive(u, model, req):
    want = model.run(u.name, req)
    u.send(req.encode())
    got = u.recv(timeout=1.0).decode(errors="replace")
    if got != want:
        raise Fail(WA, f"{u.name}: {req!r} mong đợi {want!r}, nhận được {got!r}")


def random_req(rng, names, nq):
    r = rng.random()
    i = rng.choice([rng.randint(1, nq), rng.randint(1, nq), 0, nq + 1])
    if r < 0.1:
        return f"JOIN {rng.choice(names)}"
    if r < 0.35:
        return f"Q {i}"
    if r < 0.7:
        return f"ANS {i} {rng.choice('ABCDABCDx')}"
    if r < 0.8:
        return "SCORE"
    if r < 0.9:
        return "TOP"
    if r < 0.93:
        return "LEAVE"
    return rng.choice(["", "HELLO", "JOIN", "Q", "ANS 1", "SCORE 1", "TOP 3", "ans 1 A", "Q 1 2"])


@group("edge")
@args("{port}", "q100.txt", "5")
def test_hundred_questions_crlf(ctx):
    """Tệp 100 câu (CRLF, dòng trống, dòng cuối không xuống dòng, lựa chọn chứa '|'): WELCOME đếm đúng 100"""
    a = ctx.udp("A")
    ask(a, "JOIN an", "WELCOME an 100")
    for i in (1, 7, 50, 99, 100):
        ask(a, f"Q {i}", f"Q {i} {Q100[i - 1][0]}")
    ask(a, "Q 101", "INVALID")
    ask(a, f"ANS 7 {Q100[6][1]}", "CORRECT")
    ask(a, f"ANS 100 {Q100[99][1]}", "CORRECT")


@group("edge")
@cases(("x" * 32, True), ("x" * 33, False), ("a", True), ("Nguyễn", True), title="JOIN tên {0!r:.12} hợp lệ={1}")
def test_join_names(ctx, name, ok):
    u = ctx.udp()
    ask(u, f"JOIN {name}", f"WELCOME {name} 5" if ok else "ERROR")


@group("edge")
@args("{port}", "questions.txt", "1")
def test_n_equals_one(ctx):
    """N=1: người thứ hai FULL; LEAVE xong người khác vào được; người cũ JOIN lại thì điểm về 0"""
    a = player(ctx, "an")
    ask(a, "ANS 1 B", "CORRECT")
    b = ctx.udp("B")
    with ctx.verdict(LIMIT):
        ask(b, "JOIN binh", "FULL")
    ask(a, "LEAVE", "BYE")
    with ctx.verdict(LIMIT):
        ask(b, "JOIN binh", "WELCOME binh 5")
    ask(b, "LEAVE", "BYE")
    ask(a, "JOIN an", "WELCOME an 5")
    ask(a, "SCORE", "SCORE 0 0")
    ask(a, "ANS 1 B", "CORRECT")


@group("edge")
@args("{port}", "questions.txt", "100")
@timeout(10)
def test_n_hundred(ctx):
    """N=100: đủ 100 người, người thứ 101 FULL"""
    us = [ctx.udp(f"P{i}") for i in range(100)]
    for i, u in enumerate(us):
        ask(u, f"JOIN p{i}", f"WELCOME p{i} 5")
    x = ctx.udp("X")
    with ctx.verdict(LIMIT):
        ask(x, "JOIN thua", "FULL")
    ask(us[0], "TOP", "TOP p0:0 p1:0 p10:0")


@group("basic")
def test_top_small(ctx):
    """TOP khi có ít hơn 3 người; cập nhật ngay sau mỗi câu đúng"""
    a = player(ctx, "zeta")
    ask(a, "TOP", "TOP zeta:0")
    b = player(ctx, "alpha")
    ask(a, "TOP", "TOP alpha:0 zeta:0")
    ask(a, "ANS 1 B", "CORRECT")
    ask(b, "TOP", "TOP zeta:1 alpha:0")
    ask(a, "LEAVE", "BYE")
    ask(b, "TOP", "TOP alpha:0")


@group("basic")
def test_answer_once(ctx):
    """Trả lời sai rồi trả lời lại đúng: vẫn ANSWERED, chỉ lần đầu được tính"""
    a = player(ctx, "an")
    ask(a, "ANS 4 A", "WRONG")
    ask(a, "ANS 4 C", "ANSWERED")
    ask(a, "ANS 4 B", "ANSWERED")
    ask(a, "SCORE", "SCORE 0 1")
    ask(a, "Q 4", "Q 4 " + Q5[3][0])


@group("edge")
@cases("ANS 1 AB", "ANS 1 ", "ANS 0 A", "ANS 01x A", "Q -1", "Q 1x", "Q 9999", "ANS 5 Z", title="{0!r} → INVALID hoặc ERROR")
def test_bad_indices(ctx, req):
    a = player(ctx, "an")
    m = Model(Q5, 3)
    m.run("A", "JOIN an")
    a.name = "A"
    drive(a, m, req)
    drive(a, m, "SCORE")


@group("concurrency")
@args("{port}", "q100.txt", "8")
@timeout(15)
def test_random_vs_model(ctx):
    """12 địa chỉ (N=8), 600 yêu cầu ngẫu nhiên xen kẽ (JOIN/Q/ANS/SCORE/TOP/LEAVE), so với mô hình"""
    rng = ctx.rng
    us = [ctx.udp(f"U{i}") for i in range(12)]
    m = Model(Q100, 8)
    names = ["an", "binh", "chi", "dung", "em", "giang"]
    for u in us[:6]:
        drive(u, m, f"JOIN {rng.choice(names)}")
    for _ in range(600):
        drive(rng.choice(us), m, random_req(rng, names, 100))


@group("stress")
@args("{port}", "q100.txt", "3")
@timeout(12)
def test_one_player_all_100(ctx):
    """Một người trả lời đủ 100 câu (rồi trả lời lại tất cả: ANSWERED), SCORE đúng"""
    a = ctx.udp("A")
    ask(a, "JOIN an", "WELCOME an 100")
    right = 0
    for i, (_, ans) in enumerate(Q100, 1):
        x = ans if i % 3 else "ABCD"[("ABCD".index(ans) + 1) % 4]
        right += x == ans
        ask(a, f"ANS {i} {x}", "CORRECT" if x == ans else "WRONG")
    for i in range(1, 101):
        ask(a, f"ANS {i} A", "ANSWERED")
    ask(a, "SCORE", f"SCORE {right} 100")
