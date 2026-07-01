import { cookies } from "next/headers";
import type { NextResponse } from "next/server";

export const ACCESS_TOKEN_COOKIE = "access_token";
export const REFRESH_TOKEN_COOKIE = "refresh_token";

const AUTH_COOKIE_NAMES = [ACCESS_TOKEN_COOKIE, REFRESH_TOKEN_COOKIE] as const;

function shouldUseSecureCookies(): boolean {
  const configured = process.env.NEXT_AUTH_COOKIE_SECURE;
  if (configured !== undefined) {
    return ["1", "true", "yes"].includes(configured.toLowerCase());
  }
  return process.env.NODE_ENV === "production";
}

export function authCookieOptions(maxAge: number) {
  return {
    httpOnly: true,
    sameSite: "lax" as const,
    secure: shouldUseSecureCookies(),
    path: "/",
    maxAge,
  };
}

export async function hasAccessTokenCookie(): Promise<boolean> {
  const cookieStore = await cookies();
  return Boolean(cookieStore.get(ACCESS_TOKEN_COOKIE)?.value);
}

export async function getAccessTokenCookie(): Promise<string | null> {
  const cookieStore = await cookies();
  return cookieStore.get(ACCESS_TOKEN_COOKIE)?.value || null;
}

export async function getRefreshTokenCookie(): Promise<string | null> {
  const cookieStore = await cookies();
  return cookieStore.get(REFRESH_TOKEN_COOKIE)?.value || null;
}

export function setAuthCookies(
  response: NextResponse,
  {
    accessToken,
    refreshToken,
  }: {
    accessToken?: string | null;
    refreshToken?: string | null;
  },
) {
  if (accessToken) {
    response.cookies.set(ACCESS_TOKEN_COOKIE, accessToken, authCookieOptions(60 * 60));
  }
  if (refreshToken) {
    response.cookies.set(REFRESH_TOKEN_COOKIE, refreshToken, authCookieOptions(60 * 60 * 24 * 7));
  }
}

export function clearAuthCookies(response: NextResponse) {
  for (const name of AUTH_COOKIE_NAMES) {
    response.cookies.set(name, "", {
      ...authCookieOptions(0),
      maxAge: 0,
    });
  }
}
