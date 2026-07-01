import { cookies } from "next/headers";
import { ACCESS_TOKEN_COOKIE, authCookieOptions, getRefreshTokenCookie } from "./auth";
import { getApiBaseUrl } from "./api-base";

interface RefreshResponse {
  access_token?: string;
  error?: string;
  message?: string;
}

export interface RefreshAccessTokenResult {
  ok: boolean;
  accessToken?: string;
  status?: number;
  error?: string;
  cookieUpdated: boolean;
}

function safeRefreshError(data: RefreshResponse | null): string {
  if (data?.error) return data.error;
  if (data?.message) return data.message;
  return "REFRESH_FAILED";
}

async function tryPersistAccessToken(accessToken: string): Promise<boolean> {
  try {
    const cookieStore = await cookies();
    const mutableCookieStore = cookieStore as unknown as {
      set: (
        name: string,
        value: string,
        options: ReturnType<typeof authCookieOptions>,
      ) => void;
    };
    mutableCookieStore.set(ACCESS_TOKEN_COOKIE, accessToken, authCookieOptions(60 * 60));
    return true;
  } catch {
    return false;
  }
}

export async function refreshAccessTokenFromCookie(
  apiBaseUrl = getApiBaseUrl(),
): Promise<RefreshAccessTokenResult> {
  const refreshToken = await getRefreshTokenCookie().catch(() => null);
  if (!refreshToken) {
    return {
      ok: false,
      status: 401,
      error: "MISSING_REFRESH_TOKEN",
      cookieUpdated: false,
    };
  }

  try {
    const response = await fetch(`${apiBaseUrl}/auth/refresh`, {
      method: "POST",
      cache: "no-store",
      headers: {
        Accept: "application/json",
        Authorization: `Bearer ${refreshToken}`,
      },
    });
    const data = (await response.json().catch(() => null)) as RefreshResponse | null;

    if (!response.ok || !data?.access_token) {
      return {
        ok: false,
        status: response.status,
        error: safeRefreshError(data),
        cookieUpdated: false,
      };
    }

    const cookieUpdated = await tryPersistAccessToken(data.access_token);
    return {
      ok: true,
      accessToken: data.access_token,
      status: response.status,
      cookieUpdated,
    };
  } catch (error) {
    return {
      ok: false,
      status: 502,
      error: error instanceof Error ? error.message : "REFRESH_REQUEST_FAILED",
      cookieUpdated: false,
    };
  }
}
