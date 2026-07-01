import Link from "next/link";
import { hasAccessTokenCookie } from "@/lib/auth";
import { LogoutButton } from "./logout-button";

export async function AuthStatus({ currentPath }: { currentPath: string }) {
  const isSignedIn = await hasAccessTokenCookie();

  if (isSignedIn) {
    return (
      <div className="auth-status">
        <span>已登录</span>
        <LogoutButton />
      </div>
    );
  }

  const nextPath = currentPath === "/login" ? "/" : currentPath;
  return (
    <div className="auth-status">
      <span>未登录</span>
      <Link className="auth-link" href={`/login?next=${encodeURIComponent(nextPath)}`}>
        登录
      </Link>
    </div>
  );
}
