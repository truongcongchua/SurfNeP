"use client";
// Nút "Bài ngẫu nhiên": chọn ngẫu nhiên trong danh sách đang lọc (như LeetCode).
import { useRouter } from "next/navigation";
import { Shuffle } from "lucide-react";

export function RandomButton({ ids }) {
  const router = useRouter();
  return (
    <button
      type="button" className="icon-btn" title="Bài ngẫu nhiên" aria-label="Bài ngẫu nhiên" disabled={!ids.length}
      onClick={() => router.push(`/problems/${ids[Math.floor(Math.random() * ids.length)]}`)}
    >
      <Shuffle className="size-4" />
    </button>
  );
}
