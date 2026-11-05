import { animate, useMotionValue, useMotionValueEvent, useReducedMotion } from "motion/react";
import { useEffect, useState, type ReactNode } from "react";

export type Variant = "green" | "amber" | "blue" | "gray" | "red";

export function Badge({ variant = "gray", children }: { variant?: Variant; children: ReactNode }) {
  return <span className={`badge badge-${variant}`}>{children}</span>;
}

export function StatusDot({ variant = "gray", label }: { variant?: "green" | "amber" | "gray"; label: string }) {
  return (
    <span className="status-cell">
      <span className={`dot dot-${variant}`} />
      <span className="td-dim">{label}</span>
    </span>
  );
}

export function Btn({
  primary,
  icon,
  children,
  onClick,
  disabled,
  type = "button",
  className = "",
}: {
  primary?: boolean;
  icon?: string;
  children?: ReactNode;
  onClick?: () => void;
  disabled?: boolean;
  type?: "button" | "submit";
  className?: string;
}) {
  return (
    <button type={type} className={`btn ${primary ? "btn-primary" : ""} ${className}`} onClick={onClick} disabled={disabled}>
      {icon && <i className={`ti ${icon}`} aria-hidden="true" />}
      {children}
    </button>
  );
}

export function Metric({
  label,
  tone = "",
  sub,
  className = "",
  children,
}: {
  label: string;
  tone?: "" | "warn" | "lime" | "red";
  sub?: ReactNode;
  className?: string;
  children: ReactNode;
}) {
  return (
    <div className={`metric ${className}`}>
      <div className="metric-label">{label}</div>
      <div className={`metric-value num ${tone}`}>{children}</div>
      {sub && <div className="metric-sub">{sub}</div>}
    </div>
  );
}

export function Empty({ children }: { children: ReactNode }) {
  return <div className="neg-empty">{children}</div>;
}

/** Live/mock label for a stage or service, worded as in the original Sponsor health screen. */
export function ModeBadge({ live, label }: { live?: boolean; label?: string }) {
  return <Badge variant={live ? "green" : "amber"}>{label ?? (live ? "Live" : "Mock")}</Badge>;
}

/** A number that eases to its new value. Instant under reduced motion. */
export function Num({ value, format }: { value: number; format: (n: number) => string }) {
  const reduce = useReducedMotion();
  const mv = useMotionValue(value);
  const [text, setText] = useState(() => format(value));
  useMotionValueEvent(mv, "change", (v) => setText(format(v)));
  useEffect(() => {
    if (reduce) {
      mv.set(value);
      setText(format(value));
      return;
    }
    const c = animate(mv, value, { type: "spring", stiffness: 70, damping: 18, restDelta: 0.001 });
    return () => c.stop();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value, reduce]);
  return <span className="num">{text}</span>;
}
