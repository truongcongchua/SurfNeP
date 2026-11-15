"use client";
import { useTheme } from "next-themes";
import { Sun, Moon, Monitor } from "lucide-react";
import { DropdownMenu, DropdownMenuTrigger, DropdownMenuContent, DropdownMenuItem } from "@/components/ui/dropdown-menu";

export function ThemeToggle() {
  const { setTheme } = useTheme();
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button aria-label="Đổi giao diện sáng/tối"
          className="relative inline-flex size-7 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-[var(--chip)] hover:text-foreground">
          <Sun className="size-4 scale-100 dark:scale-0 transition-transform" />
          <Moon className="absolute size-4 scale-0 dark:scale-100 transition-transform" />
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuItem onClick={() => setTheme("light")}><Sun /> Sáng</DropdownMenuItem>
        <DropdownMenuItem onClick={() => setTheme("dark")}><Moon /> Tối</DropdownMenuItem>
        <DropdownMenuItem onClick={() => setTheme("system")}><Monitor /> Theo hệ thống</DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
