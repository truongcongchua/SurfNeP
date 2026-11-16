// Hàng đợi chấm bài trong tiến trình web: chạy song song tối đa state.workers lượt chấm (mỗi lượt một container Docker,
// mạng loopback riêng nên không đụng cổng nhau). "Chạy thử" được ưu tiên hơn bài nộp khi có chỗ trống.
import { spawn } from "node:child_process";
import crypto from "node:crypto";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { db, ROOT } from "./db";
import { problemDir } from "./content";

// Mỗi container giới hạn 1 CPU / 512 MB → số lượt song song = min(6, số CPU của Docker − 1, 75% RAM của Docker / 512 MB).
// Docker Desktop chạy trong VM nên tài nguyên có thể ít hơn máy thật: lúc khởi động đọc `docker info` để tính lại
// (trước đó tạm dùng số lõi của máy). Đặt NJ_WORKERS để cố định (NJ_WORKERS=1: chấm tuần tự).
const FIXED_WORKERS = Number(process.env.NJ_WORKERS) || 0;
const CONTAINER_MEM = 512 * 1024 * 1024;
const workersFor = (cpus, mem = Infinity) =>
  Math.max(1, Math.min(6, cpus - 1, Math.floor((mem * 0.75) / CONTAINER_MEM)));
const MAX_SAMPLE_WAIT = 8; // số lượt "Chạy thử" tối đa được xếp hàng chờ chỗ trống

const g = globalThis;
if (!g.__nj_queue2) g.__nj_queue2 = { active: 0, waiters: [], workers: FIXED_WORKERS || workersFor(os.cpus().length) };
const state = g.__nj_queue2;

export const queueInfo = () => ({ workers: state.workers, active: state.active });

// Vị trí của bài nộp trong hàng đợi (1 = tiếp theo), đếm các bài 'queued' có id nhỏ hơn.
export function queuePosition(id) {
  return Number(db.prepare("SELECT COUNT(*) n FROM submissions WHERE status='queued' AND id<=?").get(id).n);
}

export function enqueue() {
  pump();
}

// Một chỗ trống vừa có: ưu tiên "Chạy thử" đang chờ, rồi mới lấy bài nộp từ DB.
function pump() {
  while (state.active < state.workers) {
    const w = state.waiters.shift();
    if (w) { state.active++; w(); continue; }
    const job = claim();
    if (!job) break;
    state.active++;
    runSubmission(job);
  }
}

// Nhận job nguyên tử: chỉ một bên chuyển được 'queued' → 'running'.
function claim() {
  return db
    .prepare(
      `UPDATE submissions SET status='running'
       WHERE id = (SELECT id FROM submissions WHERE status='queued' ORDER BY id LIMIT 1) AND status='queued'
       RETURNING id, problem_id, code`
    )
    .get();
}

async function runSubmission(job) {
  let result;
  try {
    result = await runJudge(job.problem_id, job.code);
  } catch (e) {
    result = { verdict: "IE", message: String(e), tests: [] };
  }
  try {
    db.prepare("UPDATE submissions SET status='done', verdict=?, passed=?, total=?, result=? WHERE id=?").run(
      result.verdict, result.passed ?? 0, result.total ?? 0, JSON.stringify(result), job.id);
  } finally {
    state.active--;
    pump();
  }
}

// "Chạy thử": chỉ chạy test mẫu, không lưu vào Lịch sử nộp. Chờ chỗ trống nếu cần; trả null khi hàng chờ chạy thử đã đầy.
// cases: mảng input tự nhập (bài stdio/function) — khi có thì chạy "runcustom" thay vì test mẫu.
export async function runSample(problemId, code, cases = null, debug = false) {
  if (state.active >= state.workers) {
    if (state.waiters.length >= MAX_SAMPLE_WAIT) return null;
    await new Promise((resolve) => state.waiters.push(resolve)); // pump() đã tăng state.active cho ta
  } else {
    state.active++;
  }
  try {
    return await runJudge(problemId, code, debug ? "rundebug" : cases ? "runcustom" : "runsample", cases);
  } catch (e) {
    return { verdict: "IE", message: String(e), tests: [] };
  } finally {
    state.active--;
    pump();
  }
}

function runJudge(problemId, code, cmd = "runjson", cases = null) {
  return new Promise((resolve, reject) => {
    const dir = problemDir(problemId);
    if (!dir) return reject(new Error("bài không tồn tại"));
    const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "nj-web-"));
    const file = path.join(tmp, "main.c");
    fs.writeFileSync(file, code);
    const args = [path.join(ROOT, "judge", "judge.py"), cmd, dir, file];
    if (cases) {
      const casesFile = path.join(tmp, "cases.json");
      fs.writeFileSync(casesFile, JSON.stringify(cases));
      args.push(casesFile);
    }
    const py = process.env.PYTHON || "python";
    // Đặt sẵn tên container: nếu phải giết python (Windows không giết theo được tiến trình docker con),
    // vẫn `docker rm -f` được container, không để nó chạy mồ côi chiếm CPU/RAM.
    const container = `nj-${crypto.randomBytes(6).toString("hex")}`;
    const child = spawn(py, args, { cwd: ROOT, env: { ...process.env, NJ_CONTAINER_NAME: container } });
    let out = "", err = "";
    child.stdout.setEncoding("utf8"); // ghép theo ký tự, không cắt đôi ký tự UTF-8 nằm giữa hai chunk
    child.stderr.setEncoding("utf8");
    child.stdout.on("data", (d) => (out += d));
    child.stderr.on("data", (d) => (err += d));
    let killed = false;
    const timer = setTimeout(() => {
      killed = true;
      child.kill();
      spawn("docker", ["rm", "-f", container], { stdio: "ignore" }).on("error", () => {});
    }, 200_000);
    child.on("close", () => {
      clearTimeout(timer);
      if (killed) {
        fs.rmSync(tmp, { recursive: true, force: true });
        return resolve({ verdict: "TLE", message: "lượt chấm quá 200s, đã dừng", tests: [] });
      }
      fs.rmSync(tmp, { recursive: true, force: true });
      const line = out.trim().split("\n").pop();
      try {
        resolve(JSON.parse(line));
      } catch {
        resolve({ verdict: "IE", message: (out + err).slice(-2000), tests: [] });
      }
    });
    child.on("error", (e) => { clearTimeout(timer); fs.rmSync(tmp, { recursive: true, force: true }); reject(e); });
  });
}

// Khi server khởi động lại: kiểm tra image máy chấm có khớp thư mục judge/runner không (ghi cảnh báo rõ vào log nếu
// thiếu/cũ — các lượt chấm khi đó sẽ trả "Internal Error" kèm cách xử lý), dọn container chấm còn sót từ lần chạy
// trước, rồi mới tiếp tục các bài còn dang dở.
if (!g.__nj_queue_started) {
  g.__nj_queue_started = true;
  const py = process.env.PYTHON || "python";
  const startQueue = () => setTimeout(enqueue, 100);
  if (!FIXED_WORKERS) {
    let info = "";
    const di = spawn("docker", ["info", "--format", "{{.NCPU}} {{.MemTotal}}"]);
    di.stdout.setEncoding("utf8");
    di.stdout.on("data", (d) => (info += d));
    di.on("error", () => {});
    di.on("close", () => {
      const [cpus, mem] = info.trim().split(/\s+/).map(Number);
      if (cpus > 0 && mem > 0) {
        state.workers = workersFor(cpus, mem);
        console.log(`[netjudge] Docker có ${cpus} CPU / ${(mem / 2 ** 30).toFixed(1)} GB → ${state.workers} lượt chấm song song`);
        pump();
      }
    });
  }
  const clean = spawn(py, [path.join(ROOT, "judge", "judge.py"), "cleanup"], { cwd: ROOT });
  clean.stdout.setEncoding("utf8");
  clean.stdout.on("data", (d) => { if (!d.includes(" 0 ")) console.log(`[netjudge] ${d.trim()}`); });
  clean.on("error", startQueue);
  clean.on("close", startQueue);
  const chk = spawn(py, [path.join(ROOT, "judge", "judge.py"), "check"], { cwd: ROOT });
  let msg = "";
  chk.stdout.on("data", (d) => (msg += d));
  chk.stderr.on("data", (d) => (msg += d));
  chk.on("error", (e) => console.error(`[netjudge] không chạy được ${py}: ${e.message}`));
  chk.on("close", (code) => {
    if (code === 0) console.log(`[netjudge] máy chấm sẵn sàng: ${msg.trim()}`);
    else console.error(`[netjudge] CẢNH BÁO máy chấm chưa sẵn sàng — ${msg.trim()}`);
  });
}
