// Đọc ngân hàng bài và study plan trực tiếp từ thư mục problems/ và plans/ (nguồn sự thật nằm trong git).
import fs from "node:fs";
import path from "node:path";
import YAML from "yaml";
import { ROOT } from "./db";

const PROBLEMS = path.join(ROOT, "problems");
const PLANS = path.join(ROOT, "plans");

export const DIFF_ORDER = { easy: 0, medium: 1, hard: 2 };
export const DIFF_LABEL = { easy: "Dễ", medium: "Trung bình", hard: "Khó" };

export function listProblems() {
  const out = [];
  for (const id of fs.readdirSync(PROBLEMS)) {
    const metaPath = path.join(PROBLEMS, id, "meta.yaml");
    if (!fs.existsSync(metaPath)) continue;
    const m = YAML.parse(fs.readFileSync(metaPath, "utf8"));
    out.push({
      id,
      title: m.title,
      difficulty: m.difficulty,
      chapter: m.chapter,
      topics: m.topics || [],
      prerequisites: m.prerequisites || [],
      ref: m.ref || "",
      type: m.type,
      exam: !!m.hide_details,
      examMinutes: m.exam_minutes || null,
    });
  }
  return out.sort((a, b) => a.chapter - b.chapter || DIFF_ORDER[a.difficulty] - DIFF_ORDER[b.difficulty] || a.title.localeCompare(b.title));
}

const safeId = (id) => /^[\w-]+$/.test(id);

export function getProblem(id) {
  if (!safeId(id)) return null;
  const dir = path.join(PROBLEMS, id);
  if (!fs.existsSync(path.join(dir, "meta.yaml"))) return null;
  const meta = listProblems().find((p) => p.id === id);
  const read = (f) => (fs.existsSync(path.join(dir, f)) ? fs.readFileSync(path.join(dir, f), "utf8") : "");
  return { ...meta, statement: read("statement.md"), starter: read("starter.c") };
}

// Test mẫu công khai (tests/sample*.in + .out) để hiện ở tab Testcase. Bài dạng server không có, trả về [].
export function getSamples(id) {
  if (!safeId(id)) return [];
  const dir = path.join(PROBLEMS, id, "tests");
  if (!fs.existsSync(dir)) return [];
  return fs
    .readdirSync(dir)
    .filter((f) => /^sample.*\.in$/.test(f))
    .sort()
    .map((f) => {
      const out = path.join(dir, f.replace(/\.in$/, ".out"));
      return {
        name: f.replace(/\.in$/, ""),
        input: fs.readFileSync(path.join(dir, f), "utf8"),
        output: fs.existsSync(out) ? fs.readFileSync(out, "utf8") : "",
      };
    });
}

export function problemDir(id) {
  return safeId(id) ? path.join(PROBLEMS, id) : null;
}

export function listPlans() {
  return fs
    .readdirSync(PLANS)
    .filter((f) => f.endsWith(".yaml"))
    .map((f) => YAML.parse(fs.readFileSync(path.join(PLANS, f), "utf8")));
}

export function getPlan(id) {
  return listPlans().find((p) => p.id === id) ?? null;
}

export const planProblemIds = (plan) => plan.sections.flatMap((s) => s.problems.map((p) => p.id));
