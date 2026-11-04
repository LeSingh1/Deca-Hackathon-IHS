import React from "react";
import ReactDOM from "react-dom/client";
// @ts-expect-error - JS module imported from ported app
import App from "./procure/App.jsx";
import "./procure/procure.css";

const rootEl = document.getElementById("root");
if (!rootEl) throw new Error("#root not found");
ReactDOM.createRoot(rootEl).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
