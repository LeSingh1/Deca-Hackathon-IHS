import { motion } from "motion/react";
import { STAGES, type RunState } from "../lib/runState";

export function Pipeline({ s, className = "" }: { s: RunState; className?: string }) {
  return (
    <div className={`swarm-pipeline ${className}`} aria-label="Swarm progress">
      {STAGES.map((st, i) => {
        const status = s.stages[st.key].status;
        const state = status === "pending" ? "idle" : status;
        return (
          <span key={st.key} className="swarm-pipe">
            <motion.span
              className={`swarm-step ${state}`}
              aria-current={status === "active" ? "step" : undefined}
              animate={status === "active" ? { scale: [1, 1.03, 1] } : { scale: 1 }}
              transition={status === "active" ? { duration: 1.4, repeat: Infinity, ease: "easeInOut" } : { duration: 0.2 }}
            >
              <span className="swarm-step-dot" />
              {st.title}
            </motion.span>
            {i < STAGES.length - 1 && <span className="swarm-pipe-arrow">→</span>}
          </span>
        );
      })}
    </div>
  );
}
