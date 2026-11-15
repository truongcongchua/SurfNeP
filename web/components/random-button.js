"use client";
// Nút "Bài ngẫu nhiên": chọn ngẫu nhiên trong danh sách đang lọc (như LeetCode).
import { useRouter } from "next/navigation";
import { Shuffle } from "lucide-react";

export function RandomButton({ ids }) {
  const router = useRouter();
  return (
    <button
      type="button" className="btn ghost" title="Bài ngẫu nhiên" aria-label="Bài ngẫu nhiên" disabled={!ids.length}
      style={{ padding: "0 10px" }}
      onClick={() => router.push(`/problems/${ids[Math.floor(Math.random() * ids.length)]}`)}
    >
      <Shuffle className="size-4" />
    </button>
  );
}
