import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import CompareApp from "./revision/CompareApp";
import "./styles.css";

// The comparison view is a separate mount: it must not initialize the single-
// version workbench state or any AI consent flow.
const revisionCompare = window.location.pathname.replace(/\/+$/, "") === "/compare";

createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    {revisionCompare ? <CompareApp /> : <App />}
  </React.StrictMode>
);
