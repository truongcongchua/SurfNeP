"""Sinh test cho thread-args. Chạy: python judge/judge.py gentests problems/thread-args
Oracle (expected) viết độc lập với solution.c."""


def expected(data):
    toks = data.decode("latin-1").split()
    if not toks:
        return ""
    n = int(toks[0])
    vals = [int(t) for t in toks[1:1 + n]]
    return "".join(f"{v * v}\n" for v in vals)


def fmt(vals, sep="\n"):
    return f"{len(vals)}{sep}" + sep.join(str(v) for v in vals) + "\n"


def generate(rng):
    T = []
    # basic
    T.append(("basic_three", fmt([3, -4, 0])))
    T.append(("basic_squares", fmt([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])))
    T.append(("basic_negatives", fmt([-1, -2, -3, -10, -100])))
    T.append(("basic_same_value", fmt([7] * 12)))
    T.append(("basic_distinct_order", fmt([50, 40, 30, 20, 10, 60])))
    # edge
    T.append(("edge_n_zero", "0\n"))
    T.append(("edge_empty_input", ""))
    T.append(("edge_n_one", "1\n12345\n"))
    T.append(("edge_n_one_zero", "1\n0\n"))
    T.append(("edge_n_two", fmt([-3, 4])))
    T.append(("edge_max_abs", fmt([10 ** 9, -10 ** 9, 999999999, -999999999])))
    T.append(("edge_over_int", fmt([46341, 46340, -46341, 65536, 100000, 2 ** 31 - 1 if 2 ** 31 - 1 <= 10 ** 9 else 10 ** 9])))
    T.append(("edge_n_200_ascending", fmt(list(range(1, 201)))))
    T.append(("edge_n_200_descending", fmt(list(range(200, 0, -1)))))
    T.append(("edge_n_199", fmt([rng.randint(-10 ** 9, 10 ** 9) for _ in range(199)])))
    T.append(("edge_n_200_extremes", fmt([(10 ** 9 if i % 2 == 0 else -10 ** 9) for i in range(200)])))
    T.append(("edge_n_200_zeros", fmt([0] * 200)))
    T.append(("edge_n_200_ones", fmt([-1 if i % 3 == 0 else 1 for i in range(200)])))
    T.append(("edge_index_equals_value", fmt(list(range(200)))))
    # stream: định dạng khoảng trắng
    T.append(("stream_one_line", fmt([5, 6, 7, 8], sep=" ")))
    T.append(("stream_crlf", "4\r\n1\r\n-2\r\n3\r\n4\r\n"))
    T.append(("stream_no_final_newline", "3\n9\n8\n7"))
    T.append(("stream_blank_lines", "\n\n3\n\n  2  \n\n\t-3\n1\n\n"))
    T.append(("stream_leading_zeros_plus", "3\n+5\n-007\n0012\n"))
    # robust: nhiều luồng xen kẽ
    for k in range(3):
        T.append((f"robust_random_200_{k}", fmt([rng.randint(-10 ** 9, 10 ** 9) for _ in range(200)])))
    for k in range(3):
        T.append((f"robust_random_small_{k}", fmt([rng.randint(-20, 20) for _ in range(rng.randint(2, 60))])))
    # stress: nhiều lần cùng một cỡ để bắt lỗi truyền &i
    for k in range(4):
        T.append((f"stress_n200_trial_{k}", fmt([rng.randint(-10 ** 9, 10 ** 9) for _ in range(200)])))
    for k in range(3):
        T.append((f"stress_n150_small_values_{k}", fmt([rng.randint(-1000, 1000) for _ in range(150)])))
    return [(n, d.encode("latin-1")) for n, d in T]
