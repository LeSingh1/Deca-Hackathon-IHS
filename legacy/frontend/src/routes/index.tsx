import { createFileRoute } from "@tanstack/react-router";
// @ts-expect-error - JS module imported from ported app
import App from "../procure/App.jsx";
import "../procure/procure.css";

export const Route = createFileRoute("/")({
  component: Index,
});

function Index() {
  return (
    <div className="procure-root">
      <App />
    </div>
  );
}
