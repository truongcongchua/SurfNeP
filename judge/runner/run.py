"""Chạy BÊN TRONG container chấm.

Đầu vào:  /problem (read-only) chứa meta.yaml, tests/, files/
          /sub/main.c (read-only) — bài nộp
Đầu ra:   một dòng JSON trên stdout, bắt đầu bằng 'NJRESULT '.

Các kiểu bài (meta.type):
  server    chạy bài nộp như server; tests/test_*.py đóng vai client (protocol: tcp|udp)
  client    tests/test_*.py dựng server giả và chạy bài nộp như client
  stdio     tests/*.in -> so với tests/*.out
  function  như stdio nhưng biên dịch kèm tests/harness.c (bài nộp không có main)
Biến môi trường NJ_GENOUT=1: in output thực tế của bài stdio/function (để sinh .out).
"""
import glob
import importlib.util
import json
import os
import resource
import shutil
import signal
import socket
import subprocess
import sys
import time
import traceback

import yaml

sys.path.insert(0, os.path.dirname(__file__))
import njlib  # noqa: E402
from njlib import Fail  # noqa: E402

# /judge (0700, chỉ root) — bài nộp không đọc được đề/test/đáp án. Mọi thứ của bài nộp nằm dưới /tmp/build và
# /tmp/w/runN, và chạy bằng user sandbox.
PROBLEM = "/judge/problem"
SOURCE = "/judge/sub/main.c"
BUILD = "/tmp/build"          # thư mục biên dịch (của sandbox): main.c + inc/ (harness, header của đề)
BINARY = os.path.join(BUILD, "sol")
WORK = "/tmp/w"               # root-owned 0755; mỗi test một thư mục con chown cho sandbox
SANDBOX_UID = SANDBOX_GID = 1000
OUTPUT_LIMIT = 16 << 20       # RLIMIT_FSIZE cho bài nộp: ghi quá 16 MB vào một tệp -> SIGXFSZ -> OLE
SANDBOX_KW = {"user": SANDBOX_UID, "group": SANDBOX_GID, "extra_groups": []}
CFLAGS = ["-std=gnu11", "-O2", "-Wall", "-Wextra", "-pthread"]
GENOUT = os.environ.get("NJ_GENOUT") == "1"
# Nút "Chạy thử" trên web: chỉ chạy test mẫu (không có mẫu thì chạy đúng test đầu tiên), không phải chấm đầy đủ.
SAMPLES_ONLY = os.environ.get("NJ_SAMPLES_ONLY") == "1"
# Testcase tự nhập trên web (như ô Testcase của LeetCode): /custom/case*.in, output mong đợi lấy từ
# chạy /problem/solution.c. Chỉ áp dụng cho bài stdio/function.
CUSTOM = os.environ.get("NJ_CUSTOM") == "1"
CUSTOM_DIR = "/judge/custom"
REF_DIR = "/tmp/ref"          # lời giải mẫu: thư mục riêng của root (0700)
REF_BINARY = os.path.join(REF_DIR, "ref")
# Nút "Gỡ lỗi": biên dịch -O0 -g với AddressSanitizer + UBSan, chạy như "Chạy thử" và trả kèm stderr / báo cáo sanitizer.
DEBUG = os.environ.get("NJ_DEBUG") == "1"
DEBUG_CFLAGS = ["-std=gnu11", "-O0", "-g", "-Wall", "-Wextra", "-pthread", "-fno-omit-frame-pointer",
                "-fsanitize=address,undefined"]
SAN_ENV = {**os.environ, "ASAN_OPTIONS": "detect_leaks=0:abort_on_error=0:color=never",
           "UBSAN_OPTIONS": "print_stacktrace=1:color=never"}
SHOW_IO = SAMPLES_ONLY or CUSTOM or DEBUG  # Chạy thử: trả kèm input / output / mong đợi để hiện như LeetCode


def pick_samples(items, is_sample):
    if not SAMPLES_ONLY:
        return items
    chosen = [x for x in items if is_sample(x)]
    return chosen or items[:1]


def emit(result):
    print("NJRESULT " + json.dumps(result, ensure_ascii=False), flush=True)
    sys.exit(0)


def sandbox_limits():
    """preexec_fn của mọi tiến trình bài nộp (chạy sau khi đã đổi sang user sandbox)."""
    resource.setrlimit(resource.RLIMIT_FSIZE, (OUTPUT_LIMIT, OUTPUT_LIMIT))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def kill_sandbox():
    """Giết mọi tiến trình của user sandbox (kể cả tiến trình con đã setsid / mồ côi). Gọi sau mỗi test."""
    for _ in range(50):
        pids = []
        for d in os.listdir("/proc"):
            if d.isdigit():
                try:
                    if os.stat(f"/proc/{d}").st_uid == SANDBOX_UID:
                        pids.append(int(d))
                except OSError:
                    pass
        alive = False
        for pid in pids:
            try:
                with open(f"/proc/{pid}/stat") as fh:
                    if fh.read().rsplit(")", 1)[1].split()[0] == "Z":
                        continue  # zombie: tini (--init) sẽ dọn
                os.kill(pid, signal.SIGKILL)
                alive = True
            except (OSError, IndexError):
                pass
        if not alive:
            return
        time.sleep(0.01)


def setup_build_dir(meta):
    """Chép bài nộp (và harness/header của bài function) sang /tmp/build để sandbox biên dịch được."""
    os.makedirs(os.path.join(BUILD, "inc"), exist_ok=True)
    shutil.copy(SOURCE, os.path.join(BUILD, "main.c"))
    if meta.get("type") == "function":
        for f in glob.glob(os.path.join(PROBLEM, "tests", "*.[ch]")):
            shutil.copy(f, os.path.join(BUILD, "inc"))
    for base, dirs, files in os.walk(BUILD):
        for n in dirs + files:
            os.chown(os.path.join(base, n), SANDBOX_UID, SANDBOX_GID)
    os.chown(BUILD, SANDBOX_UID, SANDBOX_GID)


def compile_source(meta, reference=False):
    """Biên dịch bài nộp (bằng user sandbox, trong /tmp/build) hoặc lời giải mẫu (bằng root, trong /tmp/ref)."""
    harness = meta.get("type") == "function"
    if reference:
        files = [os.path.join(PROBLEM, "solution.c")] + ([os.path.join(PROBLEM, "tests", "harness.c")] if harness else [])
        cmd = ["gcc", *CFLAGS, "-I", os.path.join(PROBLEM, "tests"), "-o", REF_BINARY, *files, "-lm"]
        kw = {}
    else:
        files = ["main.c"] + (["inc/harness.c"] if harness else [])
        cmd = ["gcc", *(DEBUG_CFLAGS if DEBUG else CFLAGS), "-I", "inc", "-o", BINARY, *files, "-lm"]
        kw = {**SANDBOX_KW, "cwd": BUILD, "preexec_fn": sandbox_limits}
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=30, **kw)
    except subprocess.TimeoutExpired:
        kill_sandbox()
        return False, "biên dịch quá 30 giây"
    return p.returncode == 0, (p.stdout + p.stderr)[-8000:]


def sanitizer_report(text):
    """Trích phần báo cáo của ASan / UBSan từ stderr; trả (loại, nội dung) hoặc None."""
    if "ERROR: AddressSanitizer" in text:
        return "asan", text[text.index("=="):] if "==" in text else text
    if "runtime error:" in text:
        return "ubsan", text
    return None


def imported_symbols():
    p = subprocess.run(["nm", "-D", "--undefined-only", BINARY], capture_output=True, text=True)
    syms = set()
    for line in p.stdout.splitlines():
        if not line.strip():
            continue
        name = line.split()[-1].split("@")[0]
        syms.add(name)
        # _FORTIFY_SOURCE (mặc định ở -O2 trên Ubuntu) đổi poll -> __poll_chk, recv -> __recv_chk...
        if name.startswith("__") and name.endswith("_chk"):
            syms.add(name[2:-4])
    return syms


def check_constraints(meta):
    cons = meta.get("constraints") or {}
    syms = imported_symbols()
    any_of = cons.get("require_any") or []
    if any_of and not (syms & set(any_of)):
        return f"Đề yêu cầu dùng một trong: {', '.join(any_of)}"
    bad = sorted(syms & set(cons.get("forbid") or []))
    if bad:
        return f"Đề không cho phép dùng: {', '.join(bad)}"
    return None


def free_port(kind=socket.SOCK_STREAM):
    s = socket.socket(socket.AF_INET, kind)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def is_listening(port, proto):
    want = f":{port:04X}"
    state = "0A" if proto == "tcp" else "07"
    for path in (f"/proc/net/{proto}", f"/proc/net/{proto}6"):
        try:
            with open(path) as fh:
                next(fh)
                for line in fh:
                    parts = line.split()
                    if parts[1].endswith(want) and parts[3] == state:
                        return True
        except OSError:
            pass
    return False


SIGNAMES = {getattr(signal, n): n for n in dir(signal) if n.startswith("SIG") and not n.startswith("SIG_")}


def describe_exit(code):
    if code is None:
        return "đang chạy"
    if code == -signal.SIGXFSZ:
        return f"ghi quá {OUTPUT_LIMIT >> 20} MB output (SIGXFSZ)"
    if code < 0:
        return f"bị dừng bởi tín hiệu {SIGNAMES.get(-code, -code)}"
    return f"thoát với mã {code}"


class Proc:
    """Tiến trình bài nộp (server hoặc client), stdout+stderr ghi vào workdir/.stdout."""

    def __init__(self, argv, workdir, stdin=subprocess.DEVNULL):
        self.out = open(os.path.join(workdir, ".stdout"), "wb")
        self.proc = subprocess.Popen([BINARY, *argv], cwd=workdir, stdin=stdin,
                                     stdout=self.out, stderr=subprocess.STDOUT,
                                     start_new_session=True, preexec_fn=sandbox_limits,
                                     env=SAN_ENV if DEBUG else None, **SANDBOX_KW)

    def wait_listening(self, port, proto, timeout):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.proc.poll() is not None:
                raise Fail(njlib.RE if self.proc.returncode < 0 else njlib.NL,
                           f"server {describe_exit(self.proc.returncode)} trước khi mở cổng")
            if is_listening(port, proto):
                return
            time.sleep(0.02)
        raise Fail(njlib.NL, f"server không mở cổng {proto.upper()} {port} sau {timeout}s")

    def stop(self):
        if self.proc.poll() is None:
            try:
                os.killpg(self.proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            self.proc.wait()
        else:  # tiến trình con (fork) có thể còn sống
            try:
                os.killpg(self.proc.pid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass
        self.out.close()


def signal_verdict(code):
    """Verdict cho tiến trình bị dừng bởi tín hiệu: SIGXFSZ (vượt giới hạn output) -> OLE, còn lại -> RE."""
    return njlib.OLE if code == -signal.SIGXFSZ else njlib.RE


class Timeout(Exception):
    pass


def _alarm(signum, frame):
    raise Timeout()


def load_tests():
    tests = []
    for path in sorted(glob.glob(os.path.join(PROBLEM, "tests", "test_*.py"))):
        name = os.path.splitext(os.path.basename(path))[0]
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        for key, val in vars(mod).items():
            if key.startswith("test_") and callable(val):
                tests.append(val)
    return tests


def prepare_workdir(i):
    """Thư mục chạy của test i (của user sandbox). Thư mục của test trước được xoá để tmpfs không đầy dần."""
    for old in glob.glob(os.path.join(WORK, "run*")):
        shutil.rmtree(old, ignore_errors=True)
    wd = os.path.join(WORK, f"run{i}")
    src = os.path.join(PROBLEM, "files")
    if os.path.isdir(src):
        shutil.copytree(src, wd)
    else:
        os.makedirs(wd)
    for base, dirs, files in os.walk(wd):
        for n in dirs + files:
            os.chown(os.path.join(base, n), SANDBOX_UID, SANDBOX_GID)
    os.chown(wd, SANDBOX_UID, SANDBOX_GID)
    return wd


def run_scripted_tests(meta):
    """Bài server hoặc client: mỗi test_* chạy với một tiến trình bài nộp mới."""
    kind = meta.get("type", "server")
    proto = meta.get("protocol", "tcp")
    results = []
    per_test = float(meta.get("test_timeout", 5))
    signal.signal(signal.SIGALRM, _alarm)
    for i, fn in enumerate(pick_samples(load_tests(), lambda f: getattr(f, "nj_sample", False)), 1):
        title = (fn.__doc__ or fn.__name__).strip().splitlines()[0]
        wd = prepare_workdir(i)
        procs = []
        port = None
        server = None
        if kind == "server":
            port = free_port(socket.SOCK_DGRAM if proto == "udp" else socket.SOCK_STREAM)
            argv = [a.replace("{port}", str(port)) for a in getattr(fn, "nj_args", meta.get("args", ["{port}"]))]
            server = Proc(argv, wd)
            procs.append(server)

        def launcher(argv, wd=wd, procs=procs):
            p = Proc(argv, wd, stdin=subprocess.PIPE)
            procs.append(p)
            return p.proc

        ctx = njlib.Ctx(port, server, wd, launcher)
        verdict, msg = njlib.AC, ""
        t0 = time.monotonic()
        signal.setitimer(signal.ITIMER_REAL, per_test)
        try:
            if server:
                server.wait_listening(port, proto, float(meta.get("listen_timeout", 2)))
            fn(ctx)
            if server:
                code = server.proc.poll()
                if code is not None and not getattr(fn, "nj_expects_exit", False):
                    verdict, msg = signal_verdict(code), f"server {describe_exit(code)} giữa chừng"
        except Timeout:
            verdict, msg = njlib.TLE, f"test chạy quá {per_test}s"
        except Fail as f:
            verdict, msg = f.verdict, f.message
            for p in procs:
                code = p.proc.poll()
                if code is not None and code < 0:
                    verdict, msg = signal_verdict(code), f"chương trình {describe_exit(code)} — {msg}"
            if server and verdict not in (njlib.RE, njlib.OLE) and not getattr(fn, "nj_expects_exit", False):
                code = server.proc.poll()
                if code is not None:
                    verdict, msg = njlib.RE, f"server {describe_exit(code)} giữa chừng — {msg}"
        except Exception:
            verdict, msg = njlib.IE, traceback.format_exc(limit=3)
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            ctx.close_all()
            for p in procs:
                p.stop()
            kill_sandbox()  # tiến trình con đã setsid / mồ côi không được sống sang test sau
        r = {
            "name": title, "verdict": verdict, "message": msg,
            "sample": getattr(fn, "nj_sample", False),
            "time_ms": int((time.monotonic() - t0) * 1000),
        }
        if DEBUG:
            try:
                log = open(os.path.join(wd, ".stdout"), "rb").read().decode(errors="replace")
            except OSError:
                log = ""
            rep = sanitizer_report(log)
            if rep:
                r["sanitizer"] = rep[0]
                if verdict == njlib.AC:
                    r["verdict"] = njlib.RE
                    r["message"] = "Sanitizer phát hiện lỗi bộ nhớ / hành vi không xác định"
            r["debug_log"] = log[-6000:].replace(BUILD + "/", "")
        results.append(r)
    return results


def read_capped(path, limit=OUTPUT_LIMIT):
    try:
        with open(path, "rb") as fh:
            return fh.read(limit).decode(errors="replace")
    except OSError:
        return ""


def normalize(text):
    return "\n".join(line.rstrip() for line in text.strip().splitlines())


def reference_output(data, limit, wd):
    try:
        p = subprocess.run([REF_BINARY], input=data, capture_output=True, timeout=limit * 2, cwd=wd)
        return p.stdout.decode(errors="replace")
    except subprocess.TimeoutExpired:
        return "(lời giải mẫu chạy quá thời gian với input này)"


def run_stdio_tests(meta):
    results = []
    limit = float(meta.get("test_timeout", 2))
    if CUSTOM:
        inputs = sorted(glob.glob(os.path.join(CUSTOM_DIR, "*.in")))
    else:
        inputs = pick_samples(sorted(glob.glob(os.path.join(PROBLEM, "tests", "*.in"))),
                              lambda p: os.path.basename(p).startswith("sample"))
    for i, inp in enumerate(inputs, 1):
        name = f"Case {i}" if CUSTOM else os.path.splitext(os.path.basename(inp))[0]
        with open(inp, "rb") as fh:
            data = fh.read()
        wd = prepare_workdir(i)
        if CUSTOM:
            want = reference_output(data, limit, wd)
        else:
            out_path = inp[:-3] + ".out"
            want = open(out_path, encoding="utf-8").read() if os.path.exists(out_path) else ""
        t0 = time.monotonic()
        verdict, msg, san = njlib.AC, "", None
        # stdout/stderr ghi ra tệp (giới hạn bởi RLIMIT_FSIZE) thay vì pipe: không phình RAM của runner, và tiến trình
        # con (fork) còn giữ pipe cũng không làm treo lượt chấm sau khi quá giờ.
        out_path, err_path = os.path.join(wd, ".stdout"), os.path.join(wd, ".stderr")
        with open(inp, "rb") as fin, open(out_path, "wb") as fout, open(err_path, "wb") as ferr:
            proc = subprocess.Popen([BINARY], stdin=fin, stdout=fout, stderr=ferr, cwd=wd,
                                    start_new_session=True, preexec_fn=sandbox_limits,
                                    env=SAN_ENV if DEBUG else None, **SANDBOX_KW)
            try:
                code = proc.wait(timeout=limit)
            except subprocess.TimeoutExpired:
                code = None
            kill_sandbox()
            proc.wait()
        elapsed = int((time.monotonic() - t0) * 1000)
        got = read_capped(out_path)
        err_text = read_capped(err_path, 64 << 10)
        san = sanitizer_report(err_text) if DEBUG and code is not None else None
        if code is None:
            verdict, msg = njlib.TLE, f"quá {limit}s"
        elif san:
            verdict, msg = njlib.RE, "Sanitizer phát hiện lỗi bộ nhớ / hành vi không xác định"
        elif code < 0:
            verdict, msg = signal_verdict(code), describe_exit(code)
        elif normalize(got) != normalize(want):
            verdict = njlib.WA
            msg = (f"input:\n{data.decode(errors='replace')[:600]}\n--- mong đợi:\n{want[:600]}"
                   f"\n--- nhận được:\n{got[:600]}")
        r = {"name": name, "verdict": verdict, "message": msg,
             "sample": CUSTOM or name.startswith("sample"),
             "time_ms": elapsed}
        if DEBUG:
            r["debug_log"] = err_text[-6000:].replace(BUILD + "/", "")
            if san:
                r["sanitizer"] = san[0]
        if GENOUT:
            r["output"] = got
        if SHOW_IO:
            r["io"] = {"input": data.decode(errors="replace")[:4000], "output": got[:4000], "expected": want[:4000]}
        results.append(r)
    return results


def main():
    with open(os.path.join(PROBLEM, "meta.yaml"), encoding="utf-8") as fh:
        meta = yaml.safe_load(fh)
    # Script test chạy bằng root và có thể tạo tệp trong thư mục chạy (ví dụ log.txt có sẵn nội dung) mà bài nộp
    # phải ghi tiếp được -> umask 0. Thư mục riêng của root vẫn đặt mode tường minh (0700) nên không bị lộ.
    os.umask(0)
    os.makedirs(WORK, mode=0o755, exist_ok=True)
    os.makedirs(REF_DIR, mode=0o700, exist_ok=True)
    setup_build_dir(meta)
    ok, log = compile_source(meta)
    if not ok:
        emit({"verdict": njlib.CE, "compile_log": log, "tests": []})
    violation = None if DEBUG else check_constraints(meta)
    if violation:
        emit({"verdict": njlib.CV, "compile_log": log, "message": violation, "tests": []})
    kind = meta.get("type", "server")
    if CUSTOM:
        if kind not in ("stdio", "function"):
            emit({"verdict": njlib.IE, "message": "Bài này không hỗ trợ testcase tự nhập", "tests": []})
        ok, ref_log = compile_source(meta, reference=True)
        if not ok:
            emit({"verdict": njlib.IE, "message": "Không biên dịch được lời giải mẫu:\n" + ref_log, "tests": []})
    tests = run_stdio_tests(meta) if kind in ("stdio", "function") else run_scripted_tests(meta)
    if meta.get("hide_details"):  # đề thi: chỉ test mẫu mới hiện chi tiết
        for t in tests:
            if not t["sample"] and t["verdict"] != njlib.AC:
                t["message"] = "(test ẩn — không hiển thị chi tiết)"
    first_bad = next((t for t in tests if t["verdict"] != njlib.AC), None)
    emit({
        "verdict": first_bad["verdict"] if first_bad else njlib.AC,
        "passed": sum(t["verdict"] == njlib.AC for t in tests),
        "total": len(tests),
        "compile_log": log,
        "tests": tests,
    })


if __name__ == "__main__":
    main()
