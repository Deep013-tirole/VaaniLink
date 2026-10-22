import { Component, ErrorInfo, ReactNode } from "react";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
    errorInfo: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error, errorInfo: null };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("VaaniLink ErrorBoundary caught an unhandled error:", error, errorInfo);
    this.setState({ error, errorInfo });
  }

  private handleReload = () => {
    window.location.reload();
  };

  private handleReset = () => {
    try {
      localStorage.clear();
      sessionStorage.clear();
    } catch {
      // Ignore storage errors
    }
    window.location.href = "/";
  };

  public render() {
    if (this.state.hasError) {
      return (
        <div
          role="alert"
          style={{
            minHeight: "100vh",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            backgroundColor: "#0f172a",
            color: "#f8fafc",
            padding: "2rem",
            fontFamily: "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
          }}
        >
          <div
            style={{
              maxWidth: "600px",
              width: "100%",
              backgroundColor: "#1e293b",
              border: "1px solid #334155",
              borderRadius: "12px",
              padding: "2rem",
              boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.5)",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "1rem" }}>
              <div
                style={{
                  width: "40px",
                  height: "40px",
                  borderRadius: "8px",
                  backgroundColor: "#ef4444",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: "1.25rem",
                  fontWeight: "bold",
                }}
              >
                VL
              </div>
              <div>
                <h1 style={{ fontSize: "1.25rem", fontWeight: 700, margin: 0 }}>
                  VaaniLink Startup Error
                </h1>
                <p style={{ margin: 0, fontSize: "0.875rem", color: "#94a3b8" }}>
                  An unexpected client-side error occurred during rendering.
                </p>
              </div>
            </div>

            <div
              style={{
                backgroundColor: "#0f172a",
                border: "1px solid #334155",
                borderRadius: "8px",
                padding: "1rem",
                marginBottom: "1.5rem",
                fontSize: "0.875rem",
                color: "#fca5a5",
                fontFamily: "monospace",
                overflowX: "auto",
                whiteSpace: "pre-wrap",
                wordBreak: "break-word",
              }}
            >
              {this.state.error?.message || "Unknown error"}
            </div>

            <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap", marginBottom: "1rem" }}>
              <button
                type="button"
                onClick={this.handleReload}
                style={{
                  backgroundColor: "#2563eb",
                  color: "#ffffff",
                  border: "none",
                  borderRadius: "6px",
                  padding: "0.5rem 1rem",
                  fontWeight: 600,
                  cursor: "pointer",
                  fontSize: "0.875rem",
                }}
              >
                Reload Page
              </button>
              <button
                type="button"
                onClick={this.handleReset}
                style={{
                  backgroundColor: "#334155",
                  color: "#f8fafc",
                  border: "none",
                  borderRadius: "6px",
                  padding: "0.5rem 1rem",
                  fontWeight: 600,
                  cursor: "pointer",
                  fontSize: "0.875rem",
                }}
              >
                Reset Storage & Return Home
              </button>
            </div>

            <p style={{ fontSize: "0.75rem", color: "#64748b", margin: 0 }}>
              Note for Cloudflare deployments: If this is caused by missing API configuration, verify that{" "}
              <code>VITE_API_BASE_URL</code> is properly defined in your Cloudflare Pages environment variables.
            </p>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
