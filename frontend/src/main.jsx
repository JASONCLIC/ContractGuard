import React from "react";
import ReactDOM from "react-dom/client";
import { ConfigProvider } from "antd";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter } from "react-router-dom";

import App from "./App";
import "./styles/global.css";

const queryClient = new QueryClient();

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <ConfigProvider
      theme={{
        token: {
          colorPrimary: "#0071e3",
          borderRadius: 12,
          borderRadiusLG: 16,
          fontFamily:
            '-apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Helvetica Neue", Arial, sans-serif',
          colorBgContainer: "#ffffff",
          colorBgElevated: "#ffffff",
          colorText: "#1d1d1f",
          colorTextSecondary: "#6e6e73",
          colorBorder: "rgba(0,0,0,0.1)",
          boxShadow: "0 2px 20px rgba(0,0,0,0.07)",
        },
        components: {
          Upload: { borderRadiusLG: 16 },
        },
      }}
    >
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </QueryClientProvider>
    </ConfigProvider>
  </React.StrictMode>
);
