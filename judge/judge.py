"""CLI chấm bài trên máy host.

    python judge/judge.py build                       # dựng image chấm (1 lần)
    python judge/judge.py run <thư-mục-bài> <file.c>  # chấm một bài nộp
    python judge/judge.py selftest [thư-mục-bài...]   # solution.c phải AC, wrong_*.c phải trượt
    python judge/judge.py genout <thư-mục-bài>        # sinh tests/*.out từ solution.c (bài stdio/function)

Chỉ dùng thư viện chuẩn; cần Docker.
"""
import glob
import json
import os
import shutil
import subprocess
import sys
import tempfile

IMAGE = "netjudge-runner:1"
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

COLORS = {"AC": "\033[32m", "WA": "\033[31m", "CE": "\033[33m", "RE": "\033[35m",
          "TLE": "\033[33m", "NL": "\033[31m", "BLOCKED": "\033[31m", "LIMIT": "\033[31m",
          "CV": "\033[33m", "IE": "\033[41m"}
RESET = "\033[0m"


def build():
    subprocess.run(["docker", "build", "-t", IMAGE, HERE], check=True)


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


def judge(problem_dir, source_path, wall_timeout=180, genout=False):
    """Chấm `source_path` theo bài `problem_dir`. Trả về dict kết quả."""
    problem_dir = os.path.abspath(problem_dir)
    with tempfile.TemporaryDirectory(prefix="nj-") as sub:
        shutil.copy(source_path, os.path.join(sub, "main.c"))
        cmd = [
            "docker", "run", "--rm", "-i", *extra_hosts(problem_dir),
            *(["-e", "NJ_GENOUT=1"] if genout else []),
            "--network", "none",            # không ra Internet, chỉ có loopback
            "--pids-limit", "128",          # chặn fork bomb
            "--memory", "512m", "--cpus", "1",
            "--read-only", "--tmpfs", "/tmp:exec,size=64m",
            "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
            "-v", f"{problem_dir}:/problem:ro",
            "-v", f"{sub}:/sub:ro",
            IMAGE,
        ]
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                               timeout=wall_timeout)
        except subprocess.TimeoutExpired:
            return {"verdict": "TLE", "message": f"toàn bộ lượt chấm quá {wall_timeout}s", "tests": []}
    for line in p.stdout.splitlines():
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


def selftest(dirs):
    dirs = dirs or sorted(d for d in glob.glob(os.path.join(ROOT, "problems", "*")) if os.path.isdir(d))
    ok = True
    for d in dirs:
        name = os.path.basename(d.rstrip("/\\"))
        sol = os.path.join(d, "solution.c")
        r = judge(d, sol)
        good = r["verdict"] == "AC"
        ok &= good
        print(f"[{'OK' if good else 'FAIL'}] {name}/solution.c -> {r['verdict']}")
        if not good:
            show(r)
        for wrong in sorted(glob.glob(os.path.join(d, "wrong", "*.c"))):
            r = judge(d, wrong)
            good = r["verdict"] != "AC"
            ok &= good
            print(f"[{'OK' if good else 'FAIL'}] {name}/wrong/{os.path.basename(wrong)} -> {r['verdict']}"
                  + (f"  ({r.get('passed')}/{r.get('total')})" if "total" in r else ""))
    return ok


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    cmd = sys.argv[1]
    if cmd == "build":
        build()
    elif cmd == "runjson" and len(sys.argv) == 4:  # dùng cho web: in đúng một dòng JSON
        print(json.dumps(judge(sys.argv[2], sys.argv[3]), ensure_ascii=False))
    elif cmd == "run" and len(sys.argv) == 4:
        r = judge(sys.argv[2], sys.argv[3])
        show(r)
        sys.exit(0 if r["verdict"] == "AC" else 1)
    elif cmd == "genout" and len(sys.argv) == 3:
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
        sys.exit(0 if selftest(sys.argv[2:]) else 1)
    else:
        print(__doc__)
        sys.exit(2)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    if os.name == "nt":
        os.system("")  # bật mã màu ANSI trên Windows terminal
    main()
