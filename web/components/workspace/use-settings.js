"use client";
// Cài đặt trang làm bài (như Settings của LeetCode), lưu trong localStorage của trình duyệt.
import { useCallback, useEffect, useState } from "react";
import { C_ASSIST_DEFAULTS } from "@/lib/c-intellisense";

const KEY = "nj-settings";
export const DEFAULTS = {
  ...C_ASSIST_DEFAULTS,     // gợi ý code: acAuto, acFunctions, acSnippets, sigHelp, hover, ...
  layout: "default",        // default | leet
  fontSize: 13,
  tabSize: 4,
  wordWrap: true,
  relativeLines: false,
  noCursorBlink: false,
  ligatures: false,
  runShortcut: true,        // Ctrl + '
  submitShortcut: true,     // Ctrl + Enter
};

export function useSettings() {
  const [s, setS] = useState(DEFAULTS);
  useEffect(() => {
    try { setS({ ...DEFAULTS, ...JSON.parse(localStorage.getItem(KEY) || "{}") }); } catch {}
  }, []);
  const set = useCallback((patch) => {
    setS((cur) => {
      const next = { ...cur, ...patch };
      try { localStorage.setItem(KEY, JSON.stringify(next)); } catch {}
      return next;
    });
  }, []);
  return [s, set];
}

// Giá trị lưu theo từng bài (ghi chú, testcase, like/sao...).
export function useLocal(key, initial) {
  const [v, setV] = useState(initial);
  useEffect(() => {
    try { const raw = localStorage.getItem(key); if (raw != null) setV(JSON.parse(raw)); } catch {}
  }, [key]);
  const set = useCallback((next) => {
    setV((cur) => {
      const val = typeof next === "function" ? next(cur) : next;
      try { localStorage.setItem(key, JSON.stringify(val)); } catch {}
      return val;
    });
  }, [key]);
  return [v, set];
}
