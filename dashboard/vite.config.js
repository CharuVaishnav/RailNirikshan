import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import basicSsl from "@vitejs/plugin-basic-ssl";

// Requests to /api/... are forwarded to the FastAPI backend on port 8000.
//
// "npm run dev"        -> http://localhost:5173, for working on the laptop.
// "npm run dev:phone"  -> https on the laptop's Wi-Fi address, for testing on a real phone.
//                         A phone browser only allows the camera and GPS on an https:// address,
//                         so this mode adds a self-signed certificate (the phone shows a warning once).
export default defineConfig(({ mode }) => {
  const phone = mode === "phone";
  return {
    plugins: [react(), ...(phone ? [basicSsl()] : [])],
    server: {
      port: 5173,
      host: phone ? true : "localhost",
      proxy: {
        "/api": {
          target: "http://localhost:8000",
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api/, ""),
        },
      },
    },
  };
});
