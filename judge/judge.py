"""CLI chấm bài trên máy host.

    python judge/judge.py build                       # dựng image chấm (tag theo mã băm của Dockerfile + runner/)
    python judge/judge.py ensure                      # dựng image nếu chưa có bản khớp với runner/ hiện tại (start.ps1 gọi)
    python judge/judge.py check                       # exit 0 nếu image khớp, 1 nếu thiếu/cũ (web gọi khi khởi động)
    python judge/judge.py tag                         # in tên image mong đợi
    python judge/judge.py run <thư-mục-bài> <file.c>  # chấm một bài nộp
    python judge/judge.py runsample <thư-mục-bài> <file.c>  # như runjson nhưng chỉ chạy test mẫu (nút "Chạy thử")
    python judge/judge.py runcustom <thư-mục-bài> <file.c> <cases.json>  # chạy thử với testcase tự nhập
    python judge/judge.py rundebug <thư-mục-bài> <file.c> [cases.json]  # gỡ lỗi: -O0 -g + ASan/UBSan
    python judge/judge.py cleanup                     # xoá container chấm mồ côi (đã chạy quá 210s; web gọi khi khởi động)
    python judge/judge.py selftest [-j N] [--repeat K] [thư-mục-bài...]
                                                      # solution.c phải AC (K lần), wrong/*.c + mutants.yaml phải trượt;
                                                      # in ma trận bắt lỗi (test đầu tiên giết mỗi bản sai)
    python judge/judge.py genout <thư-mục-bài>        # sinh tests/*.out từ solution.c (bài stdio/function)
    python judge/judge.py gentests <thư-mục-bài>      # chạy tests/gen.py -> tests/g_*.in, rồi genout

Chỉ dùng thư viện chuẩn; cần Docker.
"""
import calendar
import functools
import glob
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import uuid

IMAGE_REPO = "netjudge-runner"
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

COLORS = {"AC": "\033[32m", "WA": "\033[31m", "CE": "\033[33m", "RE": "\033[35m",
          "TLE": "\033[33m", "NL": "\033[31m", "BLOCKED": "\033[31m", "LIMIT": "\033[31m",
          "CV": "\033[33m", "OLE": "\033[33m", "IE": "\033[41m"}
RESET = "\033[0m"


@functools.lru_cache(maxsize=None)
def source_digest():
    """Mã băm (12 ký tự hex) của mọi thứ đi vào image: Dockerfile + toàn bộ runner/.
    Chuẩn hoá CRLF -> LF để cùng một mã nguồn cho cùng mã băm trên Windows/Linux (git autocrlf)."""
    files = [os.path.join(HERE, "Dockerfile")]
    for base, dirs, names in os.walk(os.path.join(HERE, "runner")):
        dirs[:] = sorted(d for d in dirs if d != "__pycache__")
        files += [os.path.join(base, n) for n in sorted(names) if not n.endswith(".pyc")]
    h = hashlib.sha256()
    for path in files:
        rel = os.path.relpath(path, HERE).replace(os.sep, "/")
        with open(path, "rb") as fh:
            data = fh.read().replace(b"\r\n", b"\n")
        h.update(rel.encode() + b"\0" + str(len(data)).encode() + b"\0" + data)
    return h.hexdigest()[:12]


def image_name():
    """Tên image mong đợi cho runner/ hiện tại. Sửa runner/ thì tên đổi theo, nên không thể chấm nhầm bằng image cũ."""
    return f"{IMAGE_REPO}:{source_digest()}"


class ImageProblem(Exception):
    pass


def check_image():
    """Raise ImageProblem (thông báo tiếng Việt, nói rõ cách xử lý) nếu image khớp runner/ chưa sẵn sàng."""
    name = image_name()
    try:
        p = subprocess.run(["docker", "image", "inspect", name], capture_output=True, text=True,
                           encoding="utf-8", timeout=30)
    except FileNotFoundError:
        raise ImageProblem("Không tìm thấy lệnh `docker`. Hãy cài Docker Desktop.")
    except subprocess.TimeoutExpired:
        raise ImageProblem("Docker không phản hồi (quá 30 giây). Kiểm tra Docker Desktop đã chạy xong chưa.")
    if p.returncode == 0:
        return
    err = (p.stderr or p.stdout).strip()
    if "no such image" in err.lower():
        others = subprocess.run(["docker", "image", "ls", IMAGE_REPO, "--format", "{{.Tag}}"],
                                capture_output=True, text=True, encoding="utf-8").stdout.split()
        hint = f" (máy đang có bản cũ: {', '.join(others)})" if others else ""
        raise ImageProblem(f"Image máy chấm `{name}` chưa được dựng hoặc đã cũ so với thư mục judge/runner{hint}. "
                           "Chạy: python judge/judge.py build")
    raise ImageProblem("Docker chưa sẵn sàng: " + err[-300:])


def prune_old_images(keep):
    """Xoá các bản netjudge-runner có tag khác `keep` (best-effort; bỏ qua nếu đang được dùng)."""
    out = subprocess.run(["docker", "image", "ls", IMAGE_REPO, "--format", "{{.Repository}}:{{.Tag}}"],
                         capture_output=True, text=True, encoding="utf-8").stdout.split()
    for tag in out:
        if tag != keep:
            subprocess.run(["docker", "rmi", tag], capture_output=True, text=True)


def build():
    name = image_name()
    subprocess.run(["docker", "build", "-t", name, "--label", f"nj.digest={source_digest()}", HERE], check=True)
    prune_old_images(name)
    print(f"Đã dựng {name}")


def ensure_image():
    """Dựng image nếu chưa có bản khớp. Chỉ dùng cho lệnh CLI/khởi động — không gọi giữa lượt chấm (build mất vài phút)."""
    try:
        check_image()
    except ImageProblem as e:
        if "chưa được dựng" not in str(e):
            raise
        print("Chưa có image khớp, đang dựng…")
        build()


RUN_LABEL = "nj.run=1"


def remove_container(name):
    """Dừng + xoá container chấm (best-effort). Giết lệnh `docker run` không dừng container, nên phải gọi riêng."""
    try:
        subprocess.run(["docker", "rm", "-f", name], capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        pass


def cleanup_containers(min_age=210):
    """Xoá container chấm (nhãn nj.run) đã tồn tại quá `min_age` giây — chắc chắn mồ côi, vì mọi lượt chấm bị dừng
    sau 180s (judge.py) / 200s (web). Container trẻ hơn có thể là lượt đang chấm của một tiến trình web khác: giữ."""
    p = subprocess.run(["docker", "ps", "-aq", "--filter", f"label={RUN_LABEL}"],
                       capture_output=True, text=True, encoding="utf-8", timeout=60)
    ids = p.stdout.split()
    if ids:
        q = subprocess.run(["docker", "inspect", "--format", "{{.Id}} {{.Created}}", *ids],
                           capture_output=True, text=True, encoding="utf-8", timeout=60)
        now = time.time()
        old = []
        for line in q.stdout.splitlines():
            cid, created = line.split(" ", 1)
            # "2026-11-16T09:12:33.123456789Z" -> bỏ phần lẻ của giây
            ts = calendar.timegm(time.strptime(created.strip()[:19], "%Y-%m-%dT%H:%M:%S"))
            if now - ts > min_age:
                old.append(cid)
        ids = old
    if ids:
        subprocess.run(["docker", "rm", "-f", *ids], capture_output=True, text=True, timeout=120)
    return len(ids)


def extra_hosts(problem_dir):
    """hosts.txt: mỗi dòng 'tên ip' -> --add-host (cho bài phân giải tên miền)."""
    path = os.path.join(problem_dir, "hosts.txt")
    args = []
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            parts = line.split()
            if len(parts) == 2 and not line.startswith("#"):
                args += ["--add-host", f"{parts[0]}:{parts[1]}"]
    return args


def judge(problem_dir, source_path, wall_timeout=180, genout=False, samples_only=False, custom=None, debug=False,
          fail_fast=False):
    """Chấm `source_path` theo bài `problem_dir`. Trả về dict kết quả.
    samples_only: chỉ chạy test mẫu (nút "Chạy thử" của web).
    custom: danh sách input tự nhập (bài stdio/function); output mong đợi lấy từ solution.c."""
    problem_dir = os.path.abspath(problem_dir)
    try:
        check_image()  # image thiếu/cũ -> báo lỗi rõ ràng thay vì chấm bằng runner sai phiên bản
    except ImageProblem as e:
        return {"verdict": "IE", "message": str(e), "tests": []}
    with tempfile.TemporaryDirectory(prefix="nj-") as sub, tempfile.TemporaryDirectory(prefix="nj-c-") as cdir:
        shutil.copy(source_path, os.path.join(sub, "main.c"))
        for i, text in enumerate(custom or [], 1):
            with open(os.path.join(cdir, f"case{i:02d}.in"), "w", encoding="utf-8", newline="\n") as fh:
                fh.write(text if text.endswith("\n") else text + "\n")
        # Tên container: web truyền NJ_CONTAINER_NAME để tự `docker rm -f` được nếu phải giết tiến trình này.
        name = os.environ.get("NJ_CONTAINER_NAME") or f"nj-{uuid.uuid4().hex[:12]}"
        cmd = [
            "docker", "run", "--rm", "-i", "--name", name, "--label", RUN_LABEL, *extra_hosts(problem_dir),
            *(["-e", "NJ_GENOUT=1"] if genout else []),
            *(["-e", "NJ_SAMPLES_ONLY=1"] if samples_only else []),
            *(["-e", "NJ_DEBUG=1"] if debug else []),
            *(["-e", "NJ_FAIL_FAST=1"] if fail_fast else []),
            *(["-e", "NJ_CUSTOM=1", "-v", f"{cdir}:/judge/custom:ro"] if custom is not None else []),
            "--network", "none",            # không ra Internet, chỉ có loopback
            "--pids-limit", "128",          # chặn fork bomb
            "--memory", "512m", "--cpus", "1",
            "--read-only", "--tmpfs", "/tmp:exec,size=64m",
            "--init",                       # tini làm PID 1: dọn tiến trình mồ côi (zombie) của bài nộp
            # Runner là root nhưng chỉ giữ đủ quyền để hạ bài nộp xuống user sandbox, dọn/giết tiến trình của nó.
            "--cap-drop", "ALL", "--cap-add", "SETUID", "--cap-add", "SETGID", "--cap-add", "KILL",
            "--cap-add", "CHOWN", "--cap-add", "DAC_OVERRIDE", "--cap-add", "FOWNER",
            "--security-opt", "no-new-privileges",
            "-v", f"{problem_dir}:/judge/problem:ro",   # /judge là 0700: user sandbox không vào được
            "-v", f"{sub}:/judge/sub:ro",
            image_name(),
        ]
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                               timeout=wall_timeout)
        except subprocess.TimeoutExpired:
            remove_container(name)
            return {"verdict": "TLE", "message": f"toàn bộ lượt chấm quá {wall_timeout}s", "tests": []}
    # Dòng NJRESULT cuối cùng (runner in đúng một dòng, rồi thoát).
    for line in reversed(p.stdout.splitlines()):
        if line.startswith("NJRESULT "):
            return json.loads(line[len("NJRESULT "):])
    return {"verdict": "IE", "message": (p.stdout + p.stderr)[-3000:], "tests": []}


def show(result):
    v = result["verdict"]
    head = f"{COLORS.get(v, '')}{v}{RESET}"
    if "total" in result:
        head += f"  ({result['passed']}/{result['total']} test)"
    print(head)
    if v == "CE":
        print(result.get("compile_log", ""))
    if result.get("message"):
        print("  " + result["message"])
    for t in result.get("tests", []):
        tv = t["verdict"]
        print(f"  {COLORS.get(tv, '')}{tv:7}{RESET} {t['time_ms']:5}ms  {t['name']}")
        if tv != "AC" and t.get("message"):
            for line in t["message"].splitlines():
                print("            " + line)


def load_mutants(problem_dir):
    """mutants.yaml -> [(id, why, mã nguồn đã biến đổi)]. Mỗi chuỗi `cũ` phải xuất hiện đúng một lần trong solution.c."""
    path = os.path.join(problem_dir, "mutants.yaml")
    if not os.path.exists(path):
        return []
    import yaml  # chỉ cần cho lệnh dành cho người soạn đề
    with open(path, encoding="utf-8") as fh:
        items = yaml.safe_load(fh) or []
    with open(os.path.join(problem_dir, "solution.c"), encoding="utf-8") as fh:
        base = fh.read()
    out = []
    for m in items:
        src = base
        for old, new in m["replace"]:
            n = src.count(old)
            if n != 1:
                raise ValueError(f"{os.path.basename(problem_dir)}: mutant {m['id']}: chuỗi {old!r} xuất hiện {n} lần (cần đúng 1)")
            src = src.replace(old, new)
        out.append((m["id"], m.get("why", ""), src))
    return out


def first_failure(r):
    bad = next((t for t in r.get("tests", []) if t["verdict"] != "AC"), None)
    if bad is None:
        return (r.get("message") or "")[:80]
    return f"[{bad.get('group', '?')}] {bad['name']}"


def selftest(dirs, jobs=1, repeat=1):
    from concurrent.futures import ThreadPoolExecutor
    dirs = dirs or sorted(d for d in glob.glob(os.path.join(ROOT, "problems", "*")) if os.path.isdir(d))
    tmp = tempfile.mkdtemp(prefix="nj-mut-")
    work = []  # (bài, nhãn, đường dẫn .c, phải_AC)
    try:
        for d in dirs:
            name = os.path.basename(d.rstrip("/\\"))
            for k in range(repeat):
                work.append((d, "solution.c" + (f" #{k + 1}" if repeat > 1 else ""), os.path.join(d, "solution.c"), True))
            for wrong in sorted(glob.glob(os.path.join(d, "wrong", "*.c"))):
                work.append((d, "wrong/" + os.path.basename(wrong), wrong, False))
            try:
                mutants = load_mutants(d)
            except ValueError as e:
                print(f"[FAIL] {e}")
                return False
            for mid, why, src in mutants:
                path = os.path.join(tmp, f"{name}--{mid}.c")
                with open(path, "w", encoding="utf-8", newline="\n") as fh:
                    fh.write(src)
                work.append((d, f"mutant:{mid}", path, False))

        def run(item):
            d, label, path, want_ac = item
            t0 = time.monotonic()
            r = judge(d, path, fail_fast=not want_ac)
            return item, r, time.monotonic() - t0

        ok = True
        printed = set()
        survivors = []
        with ThreadPoolExecutor(max_workers=max(1, jobs)) as ex:
            for (d, label, path, want_ac), r, secs in ex.map(run, work):
                name = os.path.basename(d.rstrip("/\\"))
                if name not in printed:
                    printed.add(name)
                    print(f"── {name}", flush=True)
                v = r["verdict"]
                # bản sai phải biên dịch được và trượt vì hành vi sai (CE/IE không tính là "đã bắt được")
                good = (v == "AC") if want_ac else (v not in ("AC", "IE", "CE"))
                ok &= good
                if want_ac:
                    groups = {}
                    for t in r.get("tests", []):
                        g = t.get("group", "?")
                        groups[g] = groups.get(g, 0) + 1
                    summary = " ".join(f"{g}:{n}" for g, n in groups.items())
                    print(f"  [{'OK' if good else 'FAIL'}] {label:30} {v:4} {r.get('passed', 0)}/{r.get('total', 0)}"
                          f" {secs:5.1f}s  {summary}", flush=True)
                    if not good:
                        show(r)
                    elif secs > 90:
                        print(f"  [WARN] lời giải mẫu chấm mất {secs:.0f}s (> 90s)")
                else:
                    killer = first_failure(r) if v != "AC" else "SỐNG SÓT — cần thêm test!"
                    if v == "CE":
                        killer = "KHÔNG BIÊN DỊCH ĐƯỢC: " + (r.get("compile_log") or "").strip().splitlines()[-1][:160] \
                            if (r.get("compile_log") or "").strip() else "KHÔNG BIÊN DỊCH ĐƯỢC"
                    if v == "AC":
                        survivors.append(f"{name}/{label}")
                    if v == "IE":
                        bad = next((t for t in r.get("tests", []) if t["verdict"] == "IE"), {})
                        lines = ((r.get("message") or "") + "\n" + bad.get("message", "")).strip().splitlines()
                        killer = f"Internal Error {bad.get('name', '')}: " + (lines[-1][:200] if lines else "")
                    print(f"  [{'OK' if good else 'FAIL'}] {label:30} {v:4} <- {killer}", flush=True)
        if survivors:
            print("Bản sai sống sót: " + ", ".join(survivors))
        return ok
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def gentests(d):
    """tests/gen.py (chạy trên host, chỉ thư viện chuẩn): generate(rng) -> [(tên, input str|bytes)].
    Ghi tests/g_<số>_<tên>.in (xoá các g_* cũ); .out sinh sau bằng solution.c (genout)."""
    import importlib.util
    import random
    spec = importlib.util.spec_from_file_location("gen", os.path.join(d, "tests", "gen.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    for old in glob.glob(os.path.join(d, "tests", "g_*.in")) + glob.glob(os.path.join(d, "tests", "g_*.out")):
        os.remove(old)
    cases = mod.generate(random.Random(20261215))
    for i, (name, data) in enumerate(cases, 1):
        raw = data.encode() if isinstance(data, str) else data
        with open(os.path.join(d, "tests", f"g_{i:03d}_{name}.in"), "wb") as fh:
            fh.write(raw)
    print(f"Đã ghi {len(cases)} tệp tests/g_*.in")
    return mod


def normalize_out(text):
    return "\n".join(line.rstrip() for line in text.strip().splitlines())


def write_outputs(d, oracle=None):
    """Chạy solution.c trên mọi tests/*.in, ghi .out. Nếu có oracle (hàm Python input bytes -> output str),
    đối chiếu từng test: hai lời giải độc lập phải cho cùng kết quả, lệch là dừng (không ghi .out sai)."""
    r = judge(d, os.path.join(d, "solution.c"), genout=True)
    if r["verdict"] == "CE" or not r.get("tests"):
        show(r)
        return False
    bad = []
    for t in r["tests"]:
        if t["verdict"] == "TLE":
            bad.append(f"{t['name']}: solution.c quá thời gian")
        if oracle is not None:
            with open(os.path.join(d, "tests", t["name"] + ".in"), "rb") as fh:
                want = oracle(fh.read())
            if normalize_out(want) != normalize_out(t["output"]):
                a, b = normalize_out(want).splitlines(), normalize_out(t["output"]).splitlines()
                k = next((i for i in range(min(len(a), len(b))) if a[i] != b[i]), min(len(a), len(b)))
                bad.append(f"{t['name']}: dòng {k + 1}: oracle={a[k] if k < len(a) else '<hết>'!r} "
                           f"solution.c={b[k] if k < len(b) else '<hết>'!r}")
    if bad:
        print("Oracle và solution.c KHÔNG khớp — không ghi .out:")
        for b in bad[:20]:
            print("  " + b)
        return False
    for t in r["tests"]:
        with open(os.path.join(d, "tests", t["name"] + ".out"), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(t["output"])
    print(f"Đã ghi {len(r['tests'])} tệp .out" + (" (đã đối chiếu với oracle)" if oracle else ""))
    return True


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    cmd = sys.argv[1]
    if cmd == "build":
        build()
    elif cmd == "tag":
        print(image_name())
    elif cmd == "check":
        try:
            check_image()
        except ImageProblem as e:
            print(e)
            sys.exit(1)
        print(f"OK {image_name()}")
    elif cmd == "cleanup":
        try:
            print(f"Đã xoá {cleanup_containers()} container chấm mồ côi")
        except (OSError, subprocess.TimeoutExpired) as e:
            print(f"Không dọn được container: {e}")
            sys.exit(1)
    elif cmd == "ensure":
        try:
            ensure_image()
        except ImageProblem as e:
            print(e)
            sys.exit(1)
        print(f"OK {image_name()}")
    elif cmd == "runjson" and len(sys.argv) == 4:  # dùng cho web: in đúng một dòng JSON
        print(json.dumps(judge(sys.argv[2], sys.argv[3]), ensure_ascii=False))
    elif cmd == "runsample" and len(sys.argv) == 4:  # như runjson nhưng chỉ chạy test mẫu
        print(json.dumps(judge(sys.argv[2], sys.argv[3], samples_only=True), ensure_ascii=False))
    elif cmd == "runcustom" and len(sys.argv) == 5:  # testcase tự nhập: argv[4] = file JSON mảng chuỗi input
        with open(sys.argv[4], encoding="utf-8") as fh:
            cases = [str(c) for c in json.load(fh)][:10]
        print(json.dumps(judge(sys.argv[2], sys.argv[3], custom=cases), ensure_ascii=False))
    elif cmd == "rundebug" and len(sys.argv) in (4, 5):  # nút Gỡ lỗi: ASan+UBSan; argv[4] (tuỳ chọn) = JSON input tự nhập
        cases = None
        if len(sys.argv) == 5:
            with open(sys.argv[4], encoding="utf-8") as fh:
                cases = [str(c) for c in json.load(fh)][:10]
        print(json.dumps(judge(sys.argv[2], sys.argv[3], samples_only=cases is None, custom=cases, debug=True), ensure_ascii=False))
    elif cmd == "run" and len(sys.argv) == 4:
        ensure_image()  # CLI tương tác: được phép tự dựng nếu thiếu
        r = judge(sys.argv[2], sys.argv[3])
        show(r)
        sys.exit(0 if r["verdict"] == "AC" else 1)
    elif cmd == "genout" and len(sys.argv) == 3:
        ensure_image()
        d = sys.argv[2]
        r = judge(d, os.path.join(d, "solution.c"), genout=True)
        if r["verdict"] == "CE":
            show(r)
            sys.exit(1)
        for t in r["tests"]:
            with open(os.path.join(d, "tests", t["name"] + ".out"), "w", encoding="utf-8", newline="\n") as fh:
                fh.write(t["output"])
            print(f"tests/{t['name']}.out  ({len(t['output'])} byte)")
    elif cmd == "selftest":
        ensure_image()
        rest, jobs, repeat = sys.argv[2:], 1, 1
        while rest and rest[0].startswith("-"):
            if rest[0] == "-j":
                jobs, rest = int(rest[1]), rest[2:]
            elif rest[0] == "--repeat":
                repeat, rest = int(rest[1]), rest[2:]
            else:
                print(__doc__)
                sys.exit(2)
        sys.exit(0 if selftest(rest, jobs, repeat) else 1)
    elif cmd == "gentests" and len(sys.argv) == 3:
        ensure_image()
        mod = gentests(sys.argv[2])
        sys.exit(0 if write_outputs(sys.argv[2], getattr(mod, "expected", None)) else 1)
    else:
        print(__doc__)
        sys.exit(2)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    if os.name == "nt":
        os.system("")  # bật mã màu ANSI trên Windows terminal
    main()
