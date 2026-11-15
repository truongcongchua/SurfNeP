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

PROBLEM = "/problem"
SOURCE = "/sub/main.c"
BINARY = "/tmp/sol"
CFLAGS = ["-std=gnu11", "-O2", "-Wall", "-Wextra", "-pthread"]
GENOUT = os.environ.get("NJ_GENOUT") == "1"
# Nút "Chạy thử" trên web: chỉ chạy test mẫu (không có mẫu thì chạy đúng test đầu tiên), không phải chấm đầy đủ.
SAMPLES_ONLY = os.environ.get("NJ_SAMPLES_ONLY") == "1"


def pick_samples(items, is_sample):
    if not SAMPLES_ONLY:
        return items
    chosen = [x for x in items if is_sample(x)]
    return chosen or items[:1]


def emit(result):
    print("NJRESULT " + json.dumps(result, ensure_ascii=False), flush=True)
    sys.exit(0)


def compile_source(meta):
    files = [SOURCE]
    if meta.get("type") == "function":
        files.append(os.path.join(PROBLEM, "tests", "harness.c"))
    p = subprocess.run(["gcc", *CFLAGS, "-I", os.path.join(PROBLEM, "tests"), "-o", BINARY, *files, "-lm"],
                       capture_output=True, text=True, timeout=30)
    return p.returncode == 0, (p.stdout + p.stderr)[-8000:]


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
    if code < 0:
        return f"bị dừng bởi tín hiệu {SIGNAMES.get(-code, -code)}"
    return f"thoát với mã {code}"


class Proc:
    """Tiến trình bài nộp (server hoặc client), stdout+stderr ghi vào workdir/.stdout."""

    def __init__(self, argv, workdir, stdin=subprocess.DEVNULL):
        self.out = open(os.path.join(workdir, ".stdout"), "wb")
        self.proc = subprocess.Popen([BINARY, *argv], cwd=workdir, stdin=stdin,
                                     stdout=self.out, stderr=subprocess.STDOUT,
                                     start_new_session=True)

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
    wd = f"/tmp/run{i}"
    shutil.rmtree(wd, ignore_errors=True)
    src = os.path.join(PROBLEM, "files")
    if os.path.isdir(src):
        shutil.copytree(src, wd)
    else:
        os.makedirs(wd)
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
                    verdict, msg = njlib.RE, f"server {describe_exit(code)} giữa chừng"
        except Timeout:
            verdict, msg = njlib.TLE, f"test chạy quá {per_test}s"
        except Fail as f:
            verdict, msg = f.verdict, f.message
            for p in procs:
                code = p.proc.poll()
                if code is not None and code < 0:
                    verdict, msg = njlib.RE, f"chương trình {describe_exit(code)} — {msg}"
            if server and verdict != njlib.RE and not getattr(fn, "nj_expects_exit", False):
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
        results.append({
            "name": title, "verdict": verdict, "message": msg,
            "sample": getattr(fn, "nj_sample", False),
            "time_ms": int((time.monotonic() - t0) * 1000),
        })
    return results


def normalize(text):
    return "\n".join(line.rstrip() for line in text.strip().splitlines())


def run_stdio_tests(meta):
    results = []
    limit = float(meta.get("test_timeout", 2))
    inputs = pick_samples(sorted(glob.glob(os.path.join(PROBLEM, "tests", "*.in"))),
                          lambda p: os.path.basename(p).startswith("sample"))
    for i, inp in enumerate(inputs, 1):
        name = os.path.splitext(os.path.basename(inp))[0]
        with open(inp, "rb") as fh:
            data = fh.read()
        out_path = inp[:-3] + ".out"
        want = open(out_path, encoding="utf-8").read() if os.path.exists(out_path) else ""
        wd = prepare_workdir(i)
        t0 = time.monotonic()
        verdict, msg, got = njlib.AC, "", ""
        try:
            p = subprocess.run([BINARY], input=data, capture_output=True, timeout=limit, cwd=wd)
            got = p.stdout.decode(errors="replace")
            if p.returncode < 0:
                verdict, msg = njlib.RE, describe_exit(p.returncode)
            elif normalize(got) != normalize(want):
                verdict = njlib.WA
                msg = (f"input:\n{data.decode(errors='replace')[:600]}\n--- mong đợi:\n{want[:600]}"
                       f"\n--- nhận được:\n{got[:600]}")
        except subprocess.TimeoutExpired:
            verdict, msg = njlib.TLE, f"quá {limit}s"
        r = {"name": name, "verdict": verdict, "message": msg,
             "sample": name.startswith("sample"),
             "time_ms": int((time.monotonic() - t0) * 1000)}
        if GENOUT:
            r["output"] = got
        results.append(r)
    return results


def main():
    with open(os.path.join(PROBLEM, "meta.yaml"), encoding="utf-8") as fh:
        meta = yaml.safe_load(fh)
    ok, log = compile_source(meta)
    if not ok:
        emit({"verdict": njlib.CE, "compile_log": log, "tests": []})
    violation = check_constraints(meta)
    if violation:
        emit({"verdict": njlib.CV, "compile_log": log, "message": violation, "tests": []})
    kind = meta.get("type", "server")
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
