import Link from "next/link";
import type { ReactNode } from "react";
import { AuthStatus } from "./auth-status";
import { RefreshButton } from "./refresh-button";

const navItems = [
  { href: "/", label: "总览" },
  { href: "/ai-prediction", label: "AI预测" },
  { href: "/anomaly-detection", label: "异常检测" },
  { href: "/dispatch", label: "智能调度" },
  { href: "/network-design", label: "网络设计" },
  { href: "/map-view", label: "地图视图" },
  { href: "/route-compare", label: "路径对比" },
  { href: null, label: "真实性" },
];

export function ConsoleShell({
  activePath,
  apiBaseUrl,
  generatedAt,
  eyebrow,
  title,
  children,
}: {
  activePath: string;
  apiBaseUrl: string;
  generatedAt: string;
  eyebrow: string;
  title: string;
  children: ReactNode;
}) {
  return (
    <main className="console-shell">
      <aside className="side-nav">
        <div className="brand-block">
          <span className="brand-mark">LC</span>
          <div>
            <h1>物流决策控制台</h1>
            <p>Logistics Decision Console</p>
          </div>
        </div>
        <nav aria-label="主导航">
          {navItems.map((item) =>
            item.href ? (
              <Link
                className={item.href === activePath ? "active" : ""}
                href={item.href}
                key={item.label}
              >
                {item.label}
              </Link>
            ) : (
              <span className="disabled-link" key={item.label}>
                {item.label}
              </span>
            ),
          )}
        </nav>
        <div className="nav-footer">
          <span>API</span>
          <strong>{apiBaseUrl}</strong>
        </div>
      </aside>

      <section className="workspace">
        <header className="topbar">
          <div>
            <p className="section-label">{eyebrow}</p>
            <h2>{title}</h2>
          </div>
          <div className="topbar-actions">
            <span>{new Date(generatedAt).toLocaleString("zh-CN")}</span>
            <AuthStatus currentPath={activePath} />
            <RefreshButton />
          </div>
        </header>
        {children}
      </section>
    </main>
  );
}
