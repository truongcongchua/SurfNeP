// Mark: a swell riding under a signal node — surfing the network.
export function Logo({ size = 16, strokeWidth = 2, color = "currentColor", ...props }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke={color}
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      {...props}
    >
      <circle cx="12" cy="6.5" r="1.6" fill={color} stroke="none" />
      <path d="M12 8.7v2.3" />
      <path d="M2 16.5c1.5 0 2.5-2.5 4-2.5s2.5 2.5 4 2.5 2.5-2.5 4-2.5 2.5 2.5 4 2.5 2.5-2.5 4-2.5" />
    </svg>
  );
}
