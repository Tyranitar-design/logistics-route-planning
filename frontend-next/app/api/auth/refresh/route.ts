import { NextResponse } from "next/server";
import { getRefreshTokenCookie, setAuthCookies } from "@/lib/auth";
import { fetchFlaskApi, upstreamError } from "@/lib/server-api";

interface RefreshResponse {
  access_token?: string;
  error?: string;
  message?: string;
}

export async function POST() {
  const refreshToken = await getRefreshTokenCookie();
  if (!refreshToken) {
    return NextResponse.json(
      { success: false, error: "缺少刷新令牌" },
      { status: 401 },
    );
  }

  try {
    const upstream = await fetchFlaskApi<RefreshResponse>("/auth/refresh", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${refreshToken}`,
      },
    });

    if (!upstream.ok || !upstream.data?.access_token) {
      return NextResponse.json(
        {
          success: false,
          error: upstreamError(upstream.data, "刷新登录状态失败"),
        },
        { status: upstream.status || 502 },
      );
    }

    const response = NextResponse.json({
      success: true,
      message: "登录状态已刷新",
    });
    setAuthCookies(response, {
      accessToken: upstream.data.access_token,
    });
    return response;
  } catch (error) {
    return NextResponse.json(
      {
        success: false,
        error: error instanceof Error ? error.message : "刷新服务不可用",
      },
      { status: 502 },
    );
  }
}
