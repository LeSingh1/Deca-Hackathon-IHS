import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "@tabler/icons-webfont/tabler-icons.min.css";
import "./procure.css";
import "./shadowbuyer.css";
import App from "./App";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
