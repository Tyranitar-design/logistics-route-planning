"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

export function LoginForm({ nextPath }: { nextPath: string }) {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      const response = await fetch("/api/auth/login", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ username, password }),
      });
      const payload = await response.json().catch(() => null) as
        | { success?: boolean; error?: string }
        | null;

      if (!response.ok || !payload?.success) {
        setError(payload?.error || "登录失败");
        return;
      }

      router.push(nextPath);
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "登录服务不可用");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form className="login-form" onSubmit={onSubmit}>
      <label>
        <span>用户名</span>
        <input
          autoComplete="username"
          name="username"
          onChange={(event) => setUsername(event.target.value)}
          placeholder="请输入账号"
          required
          type="text"
          value={username}
        />
      </label>
      <label>
        <span>密码</span>
        <input
          autoComplete="current-password"
          name="password"
          onChange={(event) => setPassword(event.target.value)}
          placeholder="请输入密码"
          required
          type="password"
          value={password}
        />
      </label>
      {error ? <p className="login-error">{error}</p> : null}
      <button className="command-button login-submit" disabled={isSubmitting} type="submit">
        {isSubmitting ? "正在登录" : "登录控制台"}
      </button>
    </form>
  );
}
