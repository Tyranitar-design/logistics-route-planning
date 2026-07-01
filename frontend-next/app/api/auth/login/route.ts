import { NextResponse } from "next/server";
import { setAuthCookies } from "@/lib/auth";
import { fetchFlaskApi, upstreamError } from "@/lib/server-api";

interface LoginResponse {
  success?: boolean;
  message?: string;
  access_token?: string;
  refresh_token?: string;
  user?: Record<string, unknown>;
  error?: string;
}

export async function POST(request: Request) {
  const payload = await request.json().catch(() => null) as
    | { username?: unknown; password?: unknown }
    | null;

  if (!payload || typeof payload.username !== "string" || typeof payload.password !== "string") {
    return NextResponse.json(
      { success: false, error: "请输入用户名和密码" },
      { status: 400 },
    );
  }

  try {
    const upstream = await fetchFlaskApi<LoginResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({
        username: payload.username,
        password: payload.password,
      }),
    });

    if (!upstream.ok || !upstream.data?.access_token || !upstream.data?.refresh_token) {
      return NextResponse.json(
        {
          success: false,
          error: upstreamError(upstream.data, "登录失败"),
        },
        { status: upstream.status || 502 },
      );
    }

    const response = NextResponse.json({
      success: true,
      message: upstream.data.message || "登录成功",
      user: upstream.data.user || null,
    });
    setAuthCookies(response, {
      accessToken: upstream.data.access_token,
      refreshToken: upstream.data.refresh_token,
    });
    return response;
  } catch (error) {
    return NextResponse.json(
      {
        success: false,
        error: error instanceof Error ? error.message : "登录服务不可用",
      },
      { status: 502 },
    );
  }
}
