import { NextResponse } from "next/server";
import { getAccessTokenCookie, setAuthCookies } from "@/lib/auth";
import { fetchFlaskApi, upstreamError } from "@/lib/server-api";
import { refreshAccessTokenFromCookie } from "@/lib/token-refresh";

interface SessionResponse {
  user?: Record<string, unknown>;
  error?: string;
  message?: string;
}

async function fetchSession(accessToken: string) {
  return fetchFlaskApi<SessionResponse>("/auth/me", {
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  });
}

export async function GET() {
  let accessToken = await getAccessTokenCookie();
  let refreshedAccessToken: string | null = null;

  if (!accessToken) {
    const refresh = await refreshAccessTokenFromCookie();
    accessToken = refresh.accessToken || null;
    refreshedAccessToken = refresh.accessToken || null;
  }

  if (!accessToken) {
    return NextResponse.json({
      authenticated: false,
      user: null,
    });
  }

  try {
    let upstream = await fetchSession(accessToken);
    if (!upstream.ok && upstream.status === 401) {
      const refresh = await refreshAccessTokenFromCookie();
      if (refresh.accessToken) {
        refreshedAccessToken = refresh.accessToken;
        upstream = await fetchSession(refresh.accessToken);
      }
    }

    if (!upstream.ok) {
      return NextResponse.json(
        {
          authenticated: false,
          user: null,
          error: upstreamError(upstream.data, "登录状态不可用"),
        },
        { status: upstream.status || 502 },
      );
    }

    const response = NextResponse.json({
      authenticated: true,
      user: upstream.data?.user || null,
    });
    if (refreshedAccessToken) {
      setAuthCookies(response, {
        accessToken: refreshedAccessToken,
      });
    }
    return response;
  } catch (error) {
    return NextResponse.json(
      {
        authenticated: false,
        user: null,
        error: error instanceof Error ? error.message : "登录状态服务不可用",
      },
      { status: 502 },
    );
  }
}
