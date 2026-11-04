import { animate, useMotionValue, useMotionValueEvent, useReducedMotion } from "motion/react";
import { useEffect, useState } from "react";

/** A number that springs to its new value. Tabular numerals; instant under reduced motion. */
export function Num({
  value,
  format,
  className = "num",
}: {
  value: number;
  format: (n: number) => string;
  className?: string;
}) {
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
  return <span className={className}>{text}</span>;
}
