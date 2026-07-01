import type { ReactNode } from "react";

export function Panel({
  title,
  action,
  className,
  children,
}: {
  title: string;
  action?: ReactNode;
  className?: string;
  children: ReactNode;
}) {
  return (
    <section className={className ? `panel ${className}` : "panel"}>
      <div className="panel-header">
        <h2>{title}</h2>
        {action ? <div>{action}</div> : null}
      </div>
      {children}
    </section>
  );
}
