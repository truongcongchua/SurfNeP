"use client";
import { Printer } from "lucide-react";

export function PrintButton() {
  return (
    <button
      onClick={() => window.print()}
      className="flex shrink-0 items-center gap-1.5 rounded-md bg-[var(--chip)] px-3 py-1.5 text-sm text-[var(--title)] hover:bg-[var(--raised)]"
    >
      <Printer className="size-4" /> In
    </button>
  );
}
