"use client";
// Ảnh đại diện tròn ở góc phải thanh trên (như LeetCode), bấm để mở menu Đăng xuất.
import { LogOut } from "lucide-react";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { logoutAction } from "@/app/actions";

export function UserMenu({ name, admin }) {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button className="avatar" aria-label="Tài khoản">{name.slice(0, 1).toUpperCase()}</button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <div className="px-2 py-1.5 text-sm font-semibold">{name}</div>
        {admin && <DropdownMenuItem onSelect={() => { window.location.href = "/admin"; }}>Quản trị</DropdownMenuItem>}
        <DropdownMenuItem onSelect={() => logoutAction()}><LogOut /> Đăng xuất</DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
