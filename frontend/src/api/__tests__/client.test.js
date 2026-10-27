import { describe, it, expect, vi, beforeEach } from "vitest";

// Capture the config passed to axios.create so we can assert on its defaults.
const createMock = vi.fn(() => ({
  interceptors: {
    response: { use: vi.fn() },
    request: { use: vi.fn() },
  },
}));

vi.mock("axios", () => ({
  default: { create: (...args) => createMock(...args) },
}));

describe("api/client", () => {
  beforeEach(() => {
    vi.resetModules();
    createMock.mockClear();
  });

  it("uses /api as the default baseURL when VITE_API_BASE_URL is not set", async () => {
    vi.stubEnv("VITE_API_BASE_URL", "");
    await import("../client");
    expect(createMock).toHaveBeenCalledTimes(1);
    const cfg = createMock.mock.calls[0][0];
    expect(cfg.baseURL).toBe("/api");
    expect(cfg.timeout).toBe(30000);
    expect(cfg.withCredentials).toBe(true);
  });

  it("respects VITE_API_BASE_URL when present", async () => {
    vi.stubEnv("VITE_API_BASE_URL", "http://localhost:5000/api");
    await import("../client");
    const cfg = createMock.mock.calls[0][0];
    expect(cfg.baseURL).toBe("http://localhost:5000/api");
  });

  it("registers a response interceptor", async () => {
    vi.stubEnv("VITE_API_BASE_URL", "");
    const captured = { use: vi.fn() };
    createMock.mockReturnValueOnce({
      interceptors: { response: captured, request: { use: vi.fn() } },
    });
    await import("../client");
    expect(captured.use).toHaveBeenCalledTimes(1);
    const [onSuccess, onError] = captured.use.mock.calls[0];
    // Success handler must pass-through the response unchanged.
    const res = { status: 200, data: { ok: true } };
    expect(onSuccess(res)).toBe(res);
    // Error handler returns a rejected promise of the same error.
    const err = new Error("boom");
    return expect(onError(err)).rejects.toBe(err);
  });
});
