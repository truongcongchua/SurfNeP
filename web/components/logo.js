// Logo SurfNeP: ô vuông bo góc màu cam (màu thương hiệu), hai lớp sóng trắng ở dưới và một cụm nút mạng nổi trên sóng,
// nghĩa là "lướt trên mạng". Giữ nguyên chữ ký cũ để các chỗ đang dùng không phải sửa; `color` không còn ảnh hưởng
// vì đây là logo nhiều màu. File app/icon.svg là bản tĩnh của cùng hình này (favicon).
import { useId } from "react";

export function Logo({ size = 16, strokeWidth, color, ...props }) {
  const id = useId().replace(/:/g, "");
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" role="img" aria-label="SurfNeP" {...props}>
      <defs>
        <linearGradient id={`g${id}`} x1="4" y1="2" x2="28" y2="30" gradientUnits="userSpaceOnUse">
          <stop offset="0" stopColor="#ffbe3d" />
          <stop offset="1" stopColor="#ff6f1f" />
        </linearGradient>
        <clipPath id={`c${id}`}><rect width="32" height="32" rx="9" /></clipPath>
      </defs>
      <rect width="32" height="32" rx="9" fill={`url(#g${id})`} />
      <g clipPath={`url(#c${id})`}>
        <path d="M0 20c4 0 5-3.5 9-3.5s5 3.5 9 3.5 5-3.5 9-3.5 4 1.5 5 2V32H0z" fill="#fff" opacity=".42" />
        <path d="M0 25c4 0 5-3.5 9-3.5s5 3.5 9 3.5 5-3.5 9-3.5 4 1.5 5 2V32H0z" fill="#fff" />
      </g>
      <g stroke="#fff" strokeWidth="1.6" strokeLinecap="round" fill="none">
        <path d="M8 12.5 16 7l8 5.5" />
      </g>
      <circle cx="8" cy="12.5" r="2.2" fill="#fff" />
      <circle cx="24" cy="12.5" r="2.2" fill="#fff" />
      <circle cx="16" cy="7" r="2.9" fill="#fff" />
      <circle cx="16" cy="7" r="1.2" fill="#ff8a1f" />
    </svg>
  );
}
