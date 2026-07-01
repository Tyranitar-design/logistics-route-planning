import { NextResponse } from "next/server";
import { clearAuthCookies } from "@/lib/auth";

export async function POST() {
  const response = NextResponse.json({
    success: true,
    message: "已退出登录",
  });
  clearAuthCookies(response);
  return response;
}
