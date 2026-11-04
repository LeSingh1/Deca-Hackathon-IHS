import { AnimatePresence, motion, useReducedMotion } from "motion/react";

/** Split-flap board: each character flips to the new text, staggered left to right. */
export function SplitFlap({ text, width, tone }: { text: string; width: number; tone?: "trap" }) {
  const reduce = useReducedMotion();
  // Center-pad to a fixed width so the board never changes size (no layout shift).
  const t = text.slice(0, width);
  const left = Math.floor((width - t.length) / 2);
  const chars = (" ".repeat(left) + t).padEnd(width, " ").split("");
  return (
    <span className={`flap ${tone ?? ""}`} aria-label={text.trim()} role="img">
      {chars.map((ch, i) => (
        <span key={i} aria-hidden="true">
          <AnimatePresence mode="popLayout" initial={false}>
            <motion.span
              key={ch + i}
              style={{ display: "inline-block", background: "transparent", width: "auto", height: "auto" }}
              initial={reduce ? false : { rotateX: -90, opacity: 0 }}
              animate={{ rotateX: 0, opacity: 1 }}
              exit={reduce ? { opacity: 0 } : { rotateX: 90, opacity: 0 }}
              transition={{ duration: 0.22, delay: reduce ? 0 : i * 0.06, ease: "easeOut" }}
            >
              {ch === " " ? " " : ch}
            </motion.span>
          </AnimatePresence>
        </span>
      ))}
    </span>
  );
}
