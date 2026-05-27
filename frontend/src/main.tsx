import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import App from "./App";
import "./index.css";
import DecisionIntelligencePage from "./pages/DecisionIntelligencePage";
import HomePage from "./pages/HomePage";
import ScoringPage from "./pages/ScoringPage";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/analysis" element={<App />} />
        <Route path="/decision-intelligence" element={<DecisionIntelligencePage />} />
        <Route path="/scoring" element={<ScoringPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  </React.StrictMode>
);
