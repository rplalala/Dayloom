import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { App } from "./app/App";
import { installProductDiagnostics, reportRenderError } from "./shared/productDiagnostics";
import "./styles/global.css";

const rootElement = document.getElementById("root");

if (!rootElement) {
  throw new Error("Application root element was not found");
}

installProductDiagnostics();

createRoot(rootElement, { onUncaughtError: reportRenderError, onCaughtError: reportRenderError }).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
