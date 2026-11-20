"""Sinh test cho inet-addr. Chạy: python judge/judge.py gentests problems/inet-addr"""
import re

OCTET = r"(0|[1-9][0-9]{0,2})"
IPV4 = re.compile(rf"^{OCTET}\.{OCTET}\.{OCTET}\.{OCTET}$")


def classify(line):
    m = IPV4.match(line)
    if not m or any(int(g) > 255 for g in m.groups()):
        return "INVALID"
    o = [int(g) for g in m.groups()]
    a = (o[0] << 24) | (o[1] << 16) | (o[2] << 8) | o[3]
    if o[0] == 127:
        k = "LOOPBACK"
    elif o[0] == 10 or (o[0] == 172 and 16 <= o[1] <= 31) or (o[0] == 192 and o[1] == 168):
        k = "PRIVATE"
    elif a in (0, 0xFFFFFFFF):
        k = "SPECIAL"
    else:
        k = "PUBLIC"
    return f"VALID {'.'.join(map(str, o))} 0x{a:08X} {k}"


def expected(data):
    text = data.decode("utf-8", "replace")
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    return "".join(classify(l.split("\r")[0]) + "\n" for l in lines)


EDGES = ["126.255.255.255", "127.0.0.0", "127.255.255.255", "128.0.0.0", "9.255.255.255", "10.0.0.0",
         "10.255.255.255", "11.0.0.0", "172.15.255.255", "172.16.0.0", "172.31.255.255", "172.32.0.0",
         "171.16.0.1", "173.16.0.1", "192.167.255.255", "192.168.0.0", "192.168.255.255", "192.169.0.0",
         "191.168.0.1", "193.168.0.1", "0.0.0.0", "0.0.0.1", "0.255.255.255", "255.255.255.254",
         "255.255.255.255", "1.0.0.0", "223.255.255.255", "224.0.0.1", "100.64.0.1", "169.254.1.1"]

INVALID = ["", " ", "01.2.3.4", "1.02.3.4", "1.2.03.4", "1.2.3.04", "00.0.0.0", "000.0.0.0", "10.1", "10",
           "10.1.1", "1.2.3.4.5", "1.2.3.", ".1.2.3", "1..2.3", "1.2..3", " 1.2.3.4", "1.2.3.4 ", "1.2.3.4\t",
           "256.0.0.0", "0.256.0.0", "0.0.0.256", "999.1.1.1", "1000.1.1.1", "1.2.3.1000", "-1.2.3.4",
           "+1.2.3.4", "0x7f.0.0.1", "0x01020304", "16909060", "1.2.3.a", "a.b.c.d", "1,2,3,4", "1.2.3.4/24",
           "1.2.3.4:80", "localhost", "::1", "1.2.3.4.", "255.255.255.255.255", "1.2.3.-0", "١.2.3.4",
           "1 .2.3.4", "1. 2.3.4", "0000000001.2.3.4", "4294967295", "127.1", "..."]


def rand_valid(rng):
    return ".".join(str(rng.randint(0, 255)) for _ in range(4))


def rand_invalid(rng):
    o = [str(rng.randint(0, 255)) for _ in range(4)]
    k = rng.randrange(8)
    i = rng.randrange(4)
    if k == 0:
        o[i] = "0" + o[i]
    elif k == 1:
        o[i] = str(rng.randint(256, 999))
    elif k == 2:
        o.pop(i)
    elif k == 3:
        o.insert(i, str(rng.randint(0, 255)))
    elif k == 4:
        o[i] = ""
    elif k == 5:
        o[i] = o[i] + rng.choice("ax-+ /")
    elif k == 6:
        return rand_valid(rng) + rng.choice([" ", ".", "..", "\t"])
    else:
        o[i] = str(rng.randint(1000, 99999))
    return ".".join(o)


def in_net(rng, first, second_lo=0, second_hi=255):
    return f"{first}.{rng.randint(second_lo, second_hi)}.{rng.randint(0, 255)}.{rng.randint(0, 255)}"


def generate(rng):
    T = []
    T.append(("edge_class_boundaries", "".join(e + "\n" for e in EDGES)))
    T.append(("edge_invalid_forms", "".join(e + "\n" for e in INVALID)))
    T.append(("edge_leading_zero_each_octet", "0.0.0.0\n00.0.0.0\n0.00.0.0\n0.0.00.0\n0.0.0.00\n10.0.0.010\n"))
    T.append(("edge_max_length_addresses", "255.255.255.255\n192.168.100.200\n172.31.255.254\n"))
    T.append(("edge_empty_input", ""))
    T.append(("edge_blank_lines", "\n\n\n"))
    T.append(("edge_no_final_newline", "8.8.8.8\n1.1.1.1"))
    T.append(("stream_crlf", "127.0.0.1\r\n10.0.0.1\r\n\r\n256.0.0.1\r\n8.8.4.4\r\n"))
    T.append(("basic_private_ranges", "".join(in_net(rng, 10) + "\n" for _ in range(20))
              + "".join(in_net(rng, 172, 16, 31) + "\n" for _ in range(20))
              + "".join(in_net(rng, 192, 168, 168) + "\n" for _ in range(20))))
    T.append(("basic_near_private", "".join(in_net(rng, 172, 0, 15) + "\n" for _ in range(15))
              + "".join(in_net(rng, 172, 32, 255) + "\n" for _ in range(15))
              + "".join(in_net(rng, 192, 0, 167) + "\n" for _ in range(10))
              + "".join(in_net(rng, 192, 169, 255) + "\n" for _ in range(10))))
    T.append(("basic_loopback", "".join(in_net(rng, 127) + "\n" for _ in range(30))))
    for k in range(6):
        T.append((f"basic_random_valid_{k}", "".join(rand_valid(rng) + "\n" for _ in range(300))))
    for k in range(6):
        T.append((f"robust_random_invalid_{k}", "".join(rand_invalid(rng) + "\n" for _ in range(300))))
    for k in range(4):
        lines = [rng.choice([rand_valid, rand_invalid])(rng) if rng.random() < 0.85 else rng.choice(INVALID + EDGES)
                 for _ in range(400)]
        T.append((f"robust_random_mixed_{k}", "".join(l + rng.choice(["\n", "\n", "\r\n"]) for l in lines)))
    T.append(("stress_100k_lines", "".join((rand_valid(rng) if rng.random() < 0.7 else rand_invalid(rng)) + "\n"
                                           for _ in range(100000))))
    return T
