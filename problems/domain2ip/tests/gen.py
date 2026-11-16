"""Sinh test cho domain2ip. Chạy: python judge/judge.py gentests problems/domain2ip
Không có oracle (kết quả phụ thuộc /etc/hosts của máy chấm, xem hosts.txt)."""

LONG = "a" * 63 + "." + "b" * 63 + "." + "c" * 60 + ".test"   # 193 ký tự, có trong hosts.txt
KNOWN = ["may.soict.test", "web.hust.test", "multi.lab.test", "many.lab.test", "dual.lab.test",
         "x1.lab.test", "x2.lab.test", "x3.lab.test", LONG]
MISSING = ["khong.ton.tai", "v6only.lab.test", "x.invalid", "may.soict", "soict.test", "lab.test",
           "-bad-.test", "a..b.test", "nope" + "z" * 200 + ".test"]


def generate(rng):
    T = []
    T.append(("basic_many_addresses", "many.lab.test\n"))
    T.append(("basic_dual_stack_only_v4", "dual.lab.test\nv6only.lab.test\n"))
    T.append(("basic_numeric", "8.8.8.8\n10.0.0.1\n255.255.255.255\n0.0.0.0\n"))
    T.append(("edge_long_name_253", LONG + "\n" + LONG.upper() + "\n"))
    T.append(("edge_long_missing", MISSING[-1] + "\n"))
    T.append(("edge_empty_input", ""))
    T.append(("edge_only_blank", "\n\n\r\n\n"))
    T.append(("edge_no_final_newline", "may.soict.test\nmulti.lab.test"))
    T.append(("stream_crlf", "may.soict.test\r\nmany.lab.test\r\n\r\nkhong.ton.tai\r\n"))
    T.append(("robust_missing_mix", "".join(m + "\n" for m in MISSING)))
    T.append(("robust_case_mix", "MAY.SOICT.TEST\nMany.Lab.Test\nDUAL.lab.TEST\n"))
    for k in range(10):
        names = [rng.choice(KNOWN + MISSING) for _ in range(40)]
        T.append((f"basic_random_{k}", "".join(n + rng.choice(["\n", "\n", "\r\n"]) for n in names)))
    T.append(("stress_1000_lookups", "".join(rng.choice(KNOWN + MISSING[:3]) + "\n" for _ in range(1000))))
    return T
