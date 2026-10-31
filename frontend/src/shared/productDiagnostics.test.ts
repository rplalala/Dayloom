import { afterEach, expect, test, vi } from "vitest";

import { installProductDiagnostics } from "./productDiagnostics";

let stop: (() => void) | undefined;
afterEach(() => { stop?.(); vi.unstubAllGlobals(); });

test("reports browser failures without error messages or query credentials", async () => {
  const fetcher = vi.fn().mockResolvedValue(new Response(null, { status: 202 }));
  vi.stubGlobal("fetch", fetcher);
  stop = installProductDiagnostics();
  window.dispatchEvent(new ErrorEvent("error", {
    error: new TypeError("password=private-value"),
    filename: "http://localhost/assets/app.js?key=private-key", lineno: 20,
  }));
  await Promise.resolve();
  expect(fetcher).toHaveBeenCalledTimes(1);
  const body = JSON.parse(fetcher.mock.calls[0][1].body);
  expect(body.kind).toBe("global_error");
  expect(body.error_type).toBe("TypeError");
  expect(body.source).toBe("app.js");
  expect(JSON.stringify(body)).not.toContain("private");
});

test("preserves failed responses and correlates reports without recursive requests", async () => {
  const response = new Response("original", { status: 503, headers: { "X-Request-ID": "4bfac526-f5d1-40f2-844b-5c4808169968" } });
  const fetcher = vi.fn().mockResolvedValueOnce(response).mockResolvedValue(new Response(null, { status: 202 }));
  vi.stubGlobal("fetch", fetcher);
  stop = installProductDiagnostics();
  const actual = await fetch("/api/trips?token=private");
  expect(actual).toBe(response);
  expect(await actual.text()).toBe("original");
  expect(fetcher).toHaveBeenCalledTimes(2);
  const body = JSON.parse(fetcher.mock.calls[1][1].body);
  expect(body.status).toBe(503);
  expect(body.request_id).toBe("4bfac526-f5d1-40f2-844b-5c4808169968");
  expect(body.path).toBe("/api/trips");
});

test("keeps original network rejection and ignores aborts", async () => {
  const error = new DOMException("cancelled", "AbortError");
  const fetcher = vi.fn().mockRejectedValue(error);
  vi.stubGlobal("fetch", fetcher);
  stop = installProductDiagnostics();
  await expect(fetch("/api/trips")).rejects.toBe(error);
  expect(fetcher).toHaveBeenCalledTimes(1);
});
