import type { ReactNode } from "react";

export function Panel({
  id,
  title,
  who,
  tag,
  children,
}: {
  id: string;
  title: string;
  who?: string;
  tag?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className="panel" id={`panel-${id}`} aria-labelledby={`h-${id}`}>
      <div className="panel-h">
        <h2 id={`h-${id}`}>{title}</h2>
        {who && <span className="who">{who}</span>}
        {tag && <span className="tag-slot" style={{ marginLeft: "auto" }}>{tag}</span>}
      </div>
      {children}
    </section>
  );
}

export function Skeleton({ rows = 4, h = 18 }: { rows?: number; h?: number }) {
  return (
    <div aria-hidden="true" style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className="skel" style={{ height: h, width: `${92 - ((i * 17) % 35)}%` }} />
      ))}
    </div>
  );
}

export function ModeTag({ live, label }: { live?: boolean; label?: string }) {
  return <span className={`tag ${live ? "money" : "muted"}`}>{label ?? (live ? "live" : "mock")}</span>;
}
