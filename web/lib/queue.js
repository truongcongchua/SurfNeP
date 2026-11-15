// Hàng đợi chấm bài trong tiến trình web: mỗi lần chạy đúng một bài (Docker chạy tuần tự, kết quả ổn định).
import { spawn } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { db, ROOT } from "./db";
import { problemDir } from "./content";

const g = globalThis;
if (!g.__nj_queue) g.__nj_queue = { busy: false };
const state = g.__nj_queue;

export function enqueue() {
  if (!state.busy && !state.running) pump();
}

async function pump() {
  state.busy = true;
  try {
    for (;;) {
      const job = db.prepare("SELECT id, problem_id, code FROM submissions WHERE status='queued' ORDER BY id LIMIT 1").get();
      if (!job) break;
      db.prepare("UPDATE submissions SET status='running' WHERE id=?").run(job.id);
      let result;
      try {
        result = await runJudge(job.problem_id, job.code);
      } catch (e) {
        result = { verdict: "IE", message: String(e), tests: [] };
      }
      db.prepare("UPDATE submissions SET status='done', verdict=?, passed=?, total=?, result=? WHERE id=?").run(
        result.verdict, result.passed ?? 0, result.total ?? 0, JSON.stringify(result), job.id);
    }
  } finally {
    state.busy = false;
  }
}

// "Chạy thử": chỉ chạy test mẫu, không lưu vào Lịch sử nộp. Dùng chung khóa với hàng đợi để Docker vẫn chạy tuần tự.
// Trả về null nếu đang bận (hàng đợi đang chấm hoặc đã có lượt chạy thử khác).
export async function runSample(problemId, code) {
  if (state.busy || state.running) return null;
  state.running = true;
  try {
    return await runJudge(problemId, code, "runsample");
  } catch (e) {
    return { verdict: "IE", message: String(e), tests: [] };
  } finally {
    state.running = false;
    enqueue(); // bài nộp xếp hàng trong lúc chạy thử thì chấm tiếp
  }
}

function runJudge(problemId, code, cmd = "runjson") {
  return new Promise((resolve, reject) => {
    const dir = problemDir(problemId);
    if (!dir) return reject(new Error("bài không tồn tại"));
    const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "nj-web-"));
    const file = path.join(tmp, "main.c");
    fs.writeFileSync(file, code);
    const py = process.env.PYTHON || "python";
    const child = spawn(py, [path.join(ROOT, "judge", "judge.py"), cmd, dir, file], { cwd: ROOT });
    let out = "", err = "";
    child.stdout.on("data", (d) => (out += d));
    child.stderr.on("data", (d) => (err += d));
    const timer = setTimeout(() => child.kill(), 200_000);
    child.on("close", () => {
      clearTimeout(timer);
      fs.rmSync(tmp, { recursive: true, force: true });
      const line = out.trim().split("\n").pop();
      try {
        resolve(JSON.parse(line));
      } catch {
        resolve({ verdict: "IE", message: (out + err).slice(-2000), tests: [] });
      }
    });
    child.on("error", reject);
  });
}

// Khi server khởi động lại, tiếp tục các bài còn dang dở.
if (!g.__nj_queue_started) {
  g.__nj_queue_started = true;
  setTimeout(enqueue, 500);
}
