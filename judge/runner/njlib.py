"""njlib — thư viện viết kịch bản chấm cho bài server/client.

Một tệp tests/test_*.py khai báo các hàm `test_*(ctx)`. Mỗi hàm nhận một server
mới khởi động (ctx.port) và dùng ctx.connect() để đóng vai client.
Docstring dòng đầu của hàm là tên test hiển thị cho người dùng.
"""
import contextlib
import hashlib
import os
import random
import select
import socket
import struct
import time

# Mã kết quả (verdict)
AC = "AC"            # Accepted
WA = "WA"            # Wrong Answer
CE = "CE"            # Compile Error
RE = "RE"            # Runtime Error (server crash / thoát bất thường)
TLE = "TLE"          # Time Limit Exceeded
OLE = "OLE"          # Output Limit Exceeded — ghi quá nhiều output
NL = "NL"            # Not Listening — server không mở cổng
BLOCKED = "BLOCKED"  # Server bị chặn bởi một client khác (không phục vụ đồng thời)
LIMIT = "LIMIT"      # Sai giới hạn số client
CV = "CV"            # Constraint Violation — dùng sai kỹ thuật đề yêu cầu
IE = "IE"            # Internal Error — lỗi của bộ chấm


class Fail(Exception):
    def __init__(self, verdict, message):
        super().__init__(message)
        self.verdict = verdict
        self.message = message


# ---------- decorator cho hàm test ----------

def args(*a):
    """Tham số dòng lệnh cho server trong test này. '{port}' được thay bằng cổng."""
    def deco(f):
        f.nj_args = list(a)
        return f
    return deco


def expects_exit(f):
    """Test này chấp nhận việc server tự kết thúc (ví dụ server một-lần)."""
    f.nj_expects_exit = True
    return f


def sample(f):
    """Test mẫu: luôn hiển thị đầy đủ input/output cho người làm."""
    f.nj_sample = True
    f.nj_group = "sample"
    return f


GROUPS = ("sample", "basic", "edge", "stream", "robust", "concurrency", "stress", "regression")


def group(name):
    """Nhóm của test (xem docs/TEST-DESIGN.md). Mặc định: basic."""
    if name not in GROUPS:
        raise ValueError(f"nhóm test không hợp lệ: {name}")

    def deco(f):
        f.nj_group = name
        return f
    return deco


def timeout(seconds):
    """Giới hạn thời gian riêng cho test này (ghi đè test_timeout của meta.yaml)."""
    def deco(f):
        f.nj_timeout = float(seconds)
        return f
    return deco


def cases(*params, title=None):
    """Tham số hoá: mỗi bộ tham số thành một test riêng, gọi fn(ctx, *tham_số).
    title: chuỗi format cho tên test, ví dụ "Key dài {0} ký tự" (mặc định: docstring + tham số)."""
    def deco(f):
        f.nj_cases = [p if isinstance(p, tuple) else (p,) for p in params]
        f.nj_case_title = title
        return f
    return deco


def expand(fn):
    """Biến một hàm test (có thể có @cases) thành danh sách (tên hiển thị, hàm 1 tham số ctx, hàm gốc)."""
    doc = (fn.__doc__ or fn.__name__).strip().splitlines()[0]
    if not getattr(fn, "nj_cases", None):
        return [(doc, fn, fn)]
    out = []
    for p in fn.nj_cases:
        if fn.nj_case_title:
            name = fn.nj_case_title.format(*p)
        else:
            name = f"{doc} [{', '.join(_short(x) for x in p)}]"
        out.append((name, (lambda ctx, p=p: fn(ctx, *p)), fn))
    return out


def _short(x):
    s = repr(x)
    return s if len(s) <= 30 else s[:27] + "..."


def buffer_boundary_sizes():
    """Độ dài hay làm lộ lỗi bộ đệm cố định (quanh 256/512/1024/2048/4096)."""
    return [255, 256, 257, 511, 512, 513, 1023, 1024, 1025, 2047, 2048, 2049, 4095, 4096, 4097]


# ---------- kết nối client ----------

def _b(data):
    return data.encode() if isinstance(data, str) else data


class Conn:
    def __init__(self, port=None, name="client", timeout=1.0, sock=None, rcvbuf=None):
        self.name = name
        self.buf = b""
        self.eof = False
        if sock is not None:  # kết nối do server giả accept()
            self.sock = sock
        else:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                if rcvbuf:  # phải đặt TRƯỚC connect thì cửa sổ TCP mới nhỏ theo
                    s.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, rcvbuf)
                s.settimeout(timeout)
                s.connect(("127.0.0.1", port))
                self.sock = s
            except (ConnectionRefusedError, socket.timeout, OSError) as e:
                raise Fail(NL, f"{name}: không kết nối được tới server ({e})")
        self.sock.settimeout(None)
        self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

    def send_chunks(self, data, rng, min_chunk=1, max_chunk=7, delay=0.002):
        """Cắt `data` thành các mảnh ngẫu nhiên [min_chunk, max_chunk] byte, gửi cách nhau `delay` giây."""
        data = _b(data)
        i = 0
        while i < len(data):
            n = rng.randint(min_chunk, max_chunk)
            self.send(data[i:i + n])
            i += n
            if delay:
                time.sleep(delay)

    def reset(self):
        """Đóng đột ngột bằng RST (SO_LINGER 0) — như client bị kill / mất mạng."""
        with contextlib.suppress(OSError):
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("ii", 1, 0))
            self.sock.close()

    def shutdown_write(self):
        """Half-close: báo hết dữ liệu (FIN) nhưng vẫn đọc được phản hồi."""
        with contextlib.suppress(OSError):
            self.sock.shutdown(socket.SHUT_WR)

    def expect_lines(self, lines, timeout=1.0):
        for want in lines:
            self.expect_line(want, timeout)

    # --- gửi ---
    def send(self, data):
        try:
            self.sock.sendall(_b(data))
        except OSError as e:
            raise Fail(WA, f"{self.name}: gửi thất bại, server đã đóng kết nối? ({e})")

    def send_line(self, line):
        self.send(_b(line) + b"\n")

    def send_slowly(self, data, chunk=1, delay=0.005):
        """Gửi từng mẩu nhỏ để kiểm tra server có xử lý TCP như một luồng byte."""
        data = _b(data)
        for i in range(0, len(data), chunk):
            self.send(data[i:i + chunk])
            time.sleep(delay)

    # --- nhận ---
    def _fill(self, deadline):
        """Đọc thêm dữ liệu vào buf. Trả về False nếu hết thời gian."""
        if self.eof:
            return True
        remain = deadline - time.monotonic()
        if remain <= 0:
            return False
        r, _, _ = select.select([self.sock], [], [], remain)
        if not r:
            return False
        try:
            chunk = self.sock.recv(65536)
        except (ConnectionResetError, OSError):
            chunk = b""
        if not chunk:
            self.eof = True
        self.buf += chunk
        return True

    def recv_line(self, timeout=1.0, expecting=None):
        deadline = time.monotonic() + timeout
        while b"\n" not in self.buf:
            if self.eof:
                hint = f" (đang chờ {expecting!r})" if expecting is not None else ""
                raise Fail(WA, f"{self.name}: server đóng kết nối{hint}; dữ liệu còn lại {self.buf!r}")
            if not self._fill(deadline):
                hint = f"{expecting!r}" if expecting is not None else "một dòng"
                raise Fail(WA, f"{self.name}: chờ {timeout}s không nhận được {hint}; đã nhận {self.buf!r}")
        line, self.buf = self.buf.split(b"\n", 1)
        return line.rstrip(b"\r").decode(errors="replace")

    def recv_exact(self, n, timeout=1.0):
        deadline = time.monotonic() + timeout
        while len(self.buf) < n:
            if self.eof:
                raise Fail(WA, f"{self.name}: server đóng kết nối khi mới nhận {len(self.buf)}/{n} byte")
            if not self._fill(deadline):
                raise Fail(WA, f"{self.name}: chờ {timeout}s mới nhận {len(self.buf)}/{n} byte")
        data, self.buf = self.buf[:n], self.buf[n:]
        return data

    def expect_bytes(self, expected, timeout=1.0):
        want = _b(expected)
        got = self.recv_exact(len(want), timeout)
        if got != want:
            i = next(k for k in range(len(want)) if got[k] != want[k])
            raise Fail(WA, f"{self.name}: dữ liệu khác nhau từ byte thứ {i}: "
                           f"mong đợi {want[i:i + 40]!r}, nhận được {got[i:i + 40]!r}")
        return got

    def recv_all_until_close(self, timeout=2.0):
        deadline = time.monotonic() + timeout
        while not self.eof:
            if not self._fill(deadline):
                raise Fail(WA, f"{self.name}: đối phương không đóng kết nối sau {timeout}s")
        data, self.buf = self.buf, b""
        return data

    def expect_line(self, expected, timeout=1.0):
        got = self.recv_line(timeout, expecting=expected)
        if got != expected:
            raise Fail(WA, f"{self.name}: mong đợi {expected!r}, nhận được {got!r}")
        return got

    def expect_silence(self, duration=0.3):
        """Không được nhận thêm dữ liệu nào trong `duration` giây."""
        deadline = time.monotonic() + duration
        while time.monotonic() < deadline and not self.eof:
            self._fill(deadline)
            if self.buf:
                raise Fail(WA, f"{self.name}: không mong đợi dữ liệu nhưng nhận được {self.buf!r}")

    def expect_closed(self, timeout=1.0, allow_data=False):
        deadline = time.monotonic() + timeout
        while not self.eof:
            if not self._fill(deadline):
                raise Fail(WA, f"{self.name}: server lẽ ra phải đóng kết nối sau {timeout}s")
        if self.buf and not allow_data:
            raise Fail(WA, f"{self.name}: nhận dữ liệu thừa trước khi đóng: {self.buf!r}")

    def close(self):
        with contextlib.suppress(OSError):
            self.sock.close()


class UdpConn:
    """Một client UDP gửi tới server đang test."""

    def __init__(self, port, name="udp"):
        self.name = name
        self.addr = ("127.0.0.1", port)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("127.0.0.1", 0))

    def send(self, data):
        self.sock.sendto(_b(data), self.addr)

    def recv(self, timeout=1.0, expecting=None):
        r, _, _ = select.select([self.sock], [], [], timeout)
        if not r:
            hint = f" {expecting!r}" if expecting is not None else " datagram nào"
            raise Fail(WA, f"{self.name}: chờ {timeout}s không nhận được{hint}")
        data, src = self.sock.recvfrom(70000)
        if src != self.addr:
            raise Fail(WA, f"{self.name}: nhận datagram từ {src}, không phải từ server")
        return data

    def expect(self, expected, timeout=1.0):
        got = self.recv(timeout, expecting=expected)
        want = _b(expected)
        if got != want:
            show = lambda b: repr(b[:200].decode(errors="replace"))  # noqa: E731
            raise Fail(WA, f"{self.name}: mong đợi {show(want)} ({len(want)} byte), "
                           f"nhận được {show(got)} ({len(got)} byte)")
        return got

    def expect_nothing(self, duration=0.3):
        r, _, _ = select.select([self.sock], [], [], duration)
        if r:
            data = self.sock.recv(70000)
            raise Fail(WA, f"{self.name}: không mong đợi phản hồi nhưng nhận được {data[:200]!r}")

    def close(self):
        with contextlib.suppress(OSError):
            self.sock.close()


class MockServer:
    """Server giả do bộ chấm dựng để chấm chương trình client."""

    def __init__(self):
        self.sock = socket.socket()
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("127.0.0.1", 0))
        self.sock.listen(16)
        self.port = self.sock.getsockname()[1]

    def accept(self, timeout=2.0, name="client"):
        r, _, _ = select.select([self.sock], [], [], timeout)
        if not r:
            raise Fail(WA, f"client không kết nối tới server sau {timeout}s")
        s, _ = self.sock.accept()
        return Conn(sock=s, name=name)

    def close(self):
        with contextlib.suppress(OSError):
            self.sock.close()


class MockUdpServer:
    """Server UDP giả do bộ chấm dựng để chấm chương trình client UDP."""

    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("127.0.0.1", 0))
        self.port = self.sock.getsockname()[1]
        self.peer = None

    def recv(self, timeout=2.0):
        """Nhận một datagram từ client, nhớ địa chỉ client để reply()."""
        r, _, _ = select.select([self.sock], [], [], timeout)
        if not r:
            raise Fail(WA, f"server giả: chờ {timeout}s không nhận được datagram nào từ client")
        data, self.peer = self.sock.recvfrom(70000)
        return data

    def expect(self, expected, timeout=2.0):
        got = self.recv(timeout)
        want = _b(expected)
        if got != want:
            raise Fail(WA, f"server giả: mong đợi datagram {want!r}, nhận được {got!r}")
        return got

    def reply(self, data):
        self.sock.sendto(_b(data), self.peer)

    def expect_nothing(self, duration=0.3):
        r, _, _ = select.select([self.sock], [], [], duration)
        if r:
            data = self.sock.recv(70000)
            raise Fail(WA, f"server giả: không mong đợi datagram nhưng nhận được {data[:200]!r}")

    def close(self):
        with contextlib.suppress(OSError):
            self.sock.close()


class ClientProc:
    """Chương trình client của người làm bài, chạy với stdin là pipe."""

    def __init__(self, proc, workdir):
        self.proc = proc
        self.workdir = workdir

    def write(self, data):
        try:
            self.proc.stdin.write(_b(data))
            self.proc.stdin.flush()
        except (BrokenPipeError, OSError):
            raise Fail(WA, "client đã thoát trong khi còn dữ liệu stdin")

    def close_stdin(self):
        with contextlib.suppress(OSError):
            self.proc.stdin.close()

    def wait(self, timeout=2.0):
        import subprocess
        try:
            return self.proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            raise Fail(WA, f"client không kết thúc sau {timeout}s")

    def stdout(self):
        with open(os.path.join(self.workdir, ".stdout"), "rb") as fh:
            return fh.read().decode(errors="replace")

    def expect_stdout(self, text, timeout=1.0):
        """Đợi tới khi stdout của client chứa `text` (kiểm tra client in ra KỊP THỜI, không đợi lúc thoát)."""
        deadline = time.monotonic() + timeout
        while True:
            out = self.stdout()
            if text in out:
                return out
            if time.monotonic() >= deadline:
                raise Fail(WA, f"client: sau {timeout}s stdout chưa có {text!r}; hiện có {out[-200:]!r}")
            time.sleep(0.02)


# ---------- ngữ cảnh của một test ----------

SANDBOX_UID = 1000


def sandbox_procs():
    """Các tiến trình của bài nộp: danh sách (pid, trạng thái, ppid). Trạng thái 'Z' = zombie."""
    out = []
    for d in os.listdir("/proc"):
        if not d.isdigit():
            continue
        try:
            if os.stat(f"/proc/{d}").st_uid != SANDBOX_UID:
                continue
            with open(f"/proc/{d}/stat") as fh:
                rest = fh.read().rsplit(")", 1)[1].split()
            out.append((int(d), rest[0], int(rest[1])))
        except (OSError, IndexError, ValueError):
            pass
    return out


class Ctx:
    def __init__(self, port, server, workdir, launcher=None, seed="njudge"):
        self.port = port
        self.server = server
        self.workdir = workdir
        self._conns = []
        self._launcher = launcher
        self.client = None
        # Seed cố định theo tên test: test ngẫu nhiên nhưng tái lập được giữa các lần chấm.
        self.rng = random.Random(int(hashlib.sha256(seed.encode()).hexdigest()[:16], 16))

    def connect(self, name=None, timeout=1.0, rcvbuf=None):
        c = Conn(self.port, name or f"client{len(self._conns) + 1}", timeout, rcvbuf=rcvbuf)
        self._conns.append(c)
        return c

    def expect_alive(self, what=""):
        """Server phải còn sống (không crash vì SIGPIPE, không tự thoát)."""
        if self.server is None:
            return
        code = self.server.proc.poll()
        if code is not None:
            sig = f"tín hiệu {-code}" if code < 0 else f"mã {code}"
            raise Fail(RE, f"server đã kết thúc ({sig}){' ' + what if what else ''}")

    def zombies(self):
        """Số tiến trình con zombie của server (chưa được waitpid)."""
        if self.server is None:
            return 0
        pid = self.server.proc.pid
        return sum(1 for _, st, ppid in sandbox_procs() if st == "Z" and ppid == pid)

    def close_quietly(self, conn):
        conn.close()
        with contextlib.suppress(ValueError):
            self._conns.remove(conn)

    def udp(self, name=None):
        c = UdpConn(self.port, name or f"udp{len(self._conns) + 1}")
        self._conns.append(c)
        return c

    def mock_server(self):
        m = MockServer()
        self._conns.append(m)
        return m

    def mock_udp_server(self):
        m = MockUdpServer()
        self._conns.append(m)
        return m

    def run_client(self, *argv):
        """Chạy chương trình client với tham số argv (bài type: client)."""
        self.client = ClientProc(self._launcher([str(a) for a in argv]), self.workdir)
        return self.client

    @contextlib.contextmanager
    def verdict(self, kind):
        """Đổi mọi lỗi trong khối thành verdict `kind` (ví dụ BLOCKED, LIMIT)."""
        try:
            yield
        except Fail as f:
            raise Fail(kind, f.message)

    def server_stdout(self):
        with open(os.path.join(self.workdir, ".stdout"), "rb") as fh:
            return fh.read().decode(errors="replace")

    def read_file(self, name):
        with open(os.path.join(self.workdir, name), "rb") as fh:
            return fh.read().decode(errors="replace")

    def close_all(self):
        for c in self._conns:
            c.close()
