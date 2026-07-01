"use client";

export function LogoutButton() {
  async function logout() {
    await fetch("/api/auth/logout", {
      method: "POST",
    }).catch(() => null);
    window.location.reload();
  }

  return (
    <button className="auth-link" onClick={logout} type="button">
      退出
    </button>
  );
}
