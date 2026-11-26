"""Sinh tệp flights.txt cố định cho các bài fly-* (chạy trên host, kết quả được commit vào problems/*/files/).

    python judge/fly_data.py

Mỗi dòng: <mã> <hãng> <đi> <đến> <ngày> <giờ đi> <giờ đến> <giá ECO> <ghế ECO> <giá BUS> <ghế BUS>
"""
import os
import random

HERE = os.path.dirname(os.path.abspath(__file__))
PROBLEMS = os.path.join(os.path.dirname(HERE), "problems")
AIRLINES = ["VN", "VJ", "QH", "BL"]


def hhmm(m):
    m %= 1440
    return f"{m // 60:02d}:{m % 60:02d}"


def make(rng, airports, dates, per_pair, hub=None, hub_count=0, code_digits=4):
    flights, used = [], set()

    def add(frm, to, d):
        while True:
            al = rng.choice(AIRLINES)
            code = f"{al}{rng.randint(1, 10 ** code_digits - 1):0{code_digits}d}"
            if code not in used:
                used.add(code)
                break
        dep = rng.randrange(0, 1440, 5)
        dur = rng.randrange(60, 205, 5)
        eco_price = rng.randrange(500, 3000) * 1000
        eco_seats = rng.choice([0, 1, 2, 3, 5, 9, 10, 40, 120, 180]) if rng.random() < 0.3 else rng.randint(4, 180)
        if rng.random() < 0.3:
            bus_price, bus_seats = 0, 0
        else:
            bus_price, bus_seats = rng.randrange(2000, 8000) * 1000, rng.choice([0, 1, 2, 9, 12, 24, rng.randint(1, 24)])
        flights.append(f"{code} {al} {frm} {to} {d} {hhmm(dep)} {hhmm(dep + dur)} {eco_price} {eco_seats} {bus_price} {bus_seats}")

    for frm in airports:
        for to in airports:
            if frm == to:
                continue
            for d in dates:
                for _ in range(rng.choice(per_pair)):
                    add(frm, to, d)
    if hub:
        for _ in range(hub_count):
            add(*hub)
    rng.shuffle(flights)
    return flights


def write(path, lines):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")
    print(path, len(lines))


def main():
    # Bộ lớn cho bài stdio (flight-filter): 7 sân bay, 7 ngày
    rng = random.Random(7001)
    big = make(rng, ["HAN", "SGN", "DAD", "PQC", "HUI", "VII", "CXR"], [f"2026-12-{d}" for d in range(18, 25)],
               [0, 0, 1, 1, 1, 2], hub=("HAN", "SGN", "2026-12-20"), hub_count=60)
    write(os.path.join(PROBLEMS, "flight-filter", "files", "flights.txt"), big)
    # Bộ nhỏ cho bài server (fly-search, fly-auth...): 4 sân bay, 3 ngày
    rng = random.Random(7002)
    small = make(rng, ["HAN", "SGN", "DAD", "PQC"], ["2026-12-20", "2026-12-21", "2026-12-22"], [0, 1, 1, 2, 3])
    write(os.path.join(PROBLEMS, "fly-search", "files", "flights.txt"), small)


if __name__ == "__main__":
    main()
