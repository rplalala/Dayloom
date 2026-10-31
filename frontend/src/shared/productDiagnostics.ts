/** Bounded, anonymous browser diagnostics; no messages, bodies, cookies or query text. */
const endpoint = "/api/diagnostics/client-errors";
const errorTypes = new Set(["Error", "TypeError", "RangeError", "ReferenceError", "SyntaxError", "URIError", "NetworkError"]);
type Kind = "global_error" | "unhandled_rejection" | "render_error" | "request_failed" | "product_action";
type Action = "json_download_requested" | "text_download_requested" | "summary_copied" | "summary_copy_fallback";
type Report = { kind: Kind; error_type?: string; path?: string; source?: string; line?: number; column?: number; method?: string; status?: number; request_id?: string; action?: Action; resource_id?: string };
let activeReport: ((report: Report) => void) | undefined;

function safePath(value: string): string {
  return value.split("?", 1)[0].split("#", 1)[0].split("/")
    .map(part => /^[a-zA-Z][a-zA-Z_-]{0,40}$/.test(part) || part === "" ? part : ":id").join("/").slice(0, 256);
}

export function reportRenderError(error: unknown): void {
  activeReport?.({ kind: "render_error", error_type: error instanceof Error && errorTypes.has(error.name) ? error.name : "Unknown" });
}

export function reportProductAction(action: Action, resourceId: string): void {
  activeReport?.({ kind: "product_action", action,
    resource_id: /^[0-9a-f-]{36}$/i.test(resourceId) ? resourceId : undefined });
}

export function installProductDiagnostics(): () => void {
  if (activeReport || import.meta.env.VITE_PRODUCT_DIAGNOSTICS === "false") return () => {};
  const originalFetch = window.fetch;
  const send = originalFetch.bind(window);
  const seen = new Map<string, number>();
  let windowStart = Date.now(), count = 0;
  const report = (input: Report) => {
    if (activeReport !== report || window.location.pathname.startsWith("/dev")) return;
    const now = Date.now();
    if (now - windowStart >= 60_000) { windowStart = now; count = 0; seen.clear(); }
    const value = { ...input, path: safePath(input.path || window.location.pathname) };
    const key = JSON.stringify(value);
    if (count >= 10 || seen.has(key)) return;
    count++; seen.set(key, now);
    try {
      void send(endpoint, { method: "POST", credentials: "same-origin", keepalive: true,
        headers: { "Content-Type": "application/json" }, body: JSON.stringify(value) }).catch(() => {});
    } catch { /* Collection failures must never affect the application. */ }
  };
  activeReport = report;
  const onError = (event: ErrorEvent) => {
    let source: string | undefined;
    try { source = new URL(event.filename, window.location.href).pathname.split("/").pop(); } catch { /* unknown source */ }
    report({ kind: "global_error", error_type: event.error instanceof Error && errorTypes.has(event.error.name) ? event.error.name : "Unknown",
      source: source && /^[a-zA-Z0-9_.-]{1,100}\.(?:js|tsx?|jsx)$/.test(source) ? source : undefined,
      line: event.lineno, column: event.colno });
  };
  const onRejection = (event: PromiseRejectionEvent) => {
    if (event.reason instanceof DOMException && event.reason.name === "AbortError") return;
    report({ kind: "unhandled_rejection", error_type: event.reason instanceof Error && errorTypes.has(event.reason.name) ? event.reason.name : "Unknown" });
  };
  const wrapped: typeof fetch = async (input, init) => {
    let url: URL | undefined;
    try { url = new URL(input instanceof Request ? input.url : String(input), window.location.href); } catch { /* fetch owns validation */ }
    const eligible = url?.origin === window.location.origin && url.pathname.startsWith("/api/") && url.pathname !== endpoint;
    const method = (init?.method || (input instanceof Request ? input.method : "GET")).toUpperCase();
    try {
      const response = await send(input, init);
      if (eligible && response.status >= 400) {
        const id = response.headers.get("x-request-id");
        report({ kind: "request_failed", path: url!.pathname, method, status: response.status,
          request_id: id && /^[0-9a-f-]{36}$/i.test(id) ? id : undefined });
      }
      return response;
    } catch (error) {
      if (eligible && !(error instanceof DOMException && error.name === "AbortError"))
        report({ kind: "request_failed", error_type: "NetworkError", path: url!.pathname, method, status: 0 });
      throw error;
    }
  };
  window.fetch = wrapped;
  window.addEventListener("error", onError);
  window.addEventListener("unhandledrejection", onRejection);
  return () => {
    if (window.fetch === wrapped) window.fetch = originalFetch;
    window.removeEventListener("error", onError);
    window.removeEventListener("unhandledrejection", onRejection);
    if (activeReport === report) activeReport = undefined;
  };
}
