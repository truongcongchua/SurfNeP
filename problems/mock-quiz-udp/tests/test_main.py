from njlib import LIMIT, args, sample

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


def test_players_isolated(ctx):
    """Điểm và trạng thái đã trả lời tách biệt theo từng địa chỉ"""
    a = player(ctx, "an")
    b = player(ctx, "binh")
    ask(a, "ANS 3 B", "CORRECT")
    ask(b, "ANS 3 A", "WRONG")
    ask(b, "ANS 3 B", "ANSWERED")
    ask(a, "SCORE", "SCORE 1 1")
    ask(b, "SCORE", "SCORE 0 1")
