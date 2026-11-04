import { STAGES, type RunState } from "../lib/runState";

export function StageRail({ s }: { s: RunState }) {
  return (
    <nav className="rail" aria-label="Swarm progress">
      {STAGES.map((st) => {
        const state = s.stages[st.key];
        return (
          <a
            key={st.key}
            href={`#panel-${st.key}`}
            className={`step ${state.status}`}
            style={{ color: "inherit", textDecoration: "none" }}
            aria-current={state.status === "active" ? "step" : undefined}
          >
            <b>{st.title}</b>
            <small>
              <span className={`dot ${state.live ? "live" : ""}`} aria-hidden="true" />
              {state.model ? state.model.replace(/claude-/g, "").replace(/ \/ /g, "/") : st.who}
            </small>
          </a>
        );
      })}
    </nav>
  );
}
