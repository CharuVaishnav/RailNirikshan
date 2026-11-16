import React from "react";
import ReactDOM from "react-dom/client";
// Anek is an open-source Indian typeface family with matching Latin and Devanagari.
// It is bundled with the app, so the dashboard looks the same without internet.
import "@fontsource-variable/anek-latin/wdth.css";
import "@fontsource-variable/anek-devanagari/wdth.css";
import "leaflet/dist/leaflet.css";
import "./styles.css";
import App from "./App.jsx";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
