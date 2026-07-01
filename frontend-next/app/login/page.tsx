import Link from "next/link";
import { LoginForm } from "./login-form";

export const dynamic = "force-dynamic";

function sanitizeNextPath(value?: string): string {
  if (!value || !value.startsWith("/") || value.startsWith("//")) return "/";
  return value;
}

export default async function LoginPage({
  searchParams,
}: {
  searchParams?: Promise<{ next?: string }>;
}) {
  const params = await searchParams;
  const nextPath = sanitizeNextPath(params?.next);

  return (
    <main className="login-shell">
      <section className="login-panel">
        <div className="brand-block login-brand">
          <span className="brand-mark">LC</span>
          <div>
            <h1>物流决策控制台</h1>
            <p>Logistics Decision Console</p>
          </div>
        </div>
        <div className="login-copy">
          <p className="section-label">安全入口</p>
          <h2>登录后访问真实调度、地图和 provider 接口</h2>
          <p>
            Next.js 只保存 httpOnly 会话 cookie，浏览器脚本不会直接接触 access token 或 refresh token。
          </p>
        </div>
        <LoginForm nextPath={nextPath} />
        <Link className="login-back" href="/">
          返回总览
        </Link>
      </section>
      <section className="login-aside" aria-label="登录说明">
        <article>
          <span>数据底座</span>
          <strong>PostgreSQL shipment_facts</strong>
          <p>登录后可让 SSR 请求携带真实 Bearer，会继续保留 data_source 与 fallback_reason。</p>
        </article>
        <article>
          <span>路径 provider</span>
          <strong>AMap / Tianditu / Local graph</strong>
          <p>高德、天地图与本地图算法对比仍走后端统一代理，不在前端保存第三方 key。</p>
        </article>
        <article>
          <span>调度求解</span>
          <strong>Gurobi / OR-Tools / ALNS</strong>
          <p>受保护的调度预览、方案历史和 provider 诊断可以复用同一登录状态。</p>
        </article>
      </section>
    </main>
  );
}
