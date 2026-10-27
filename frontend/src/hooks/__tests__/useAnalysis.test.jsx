import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";

import { makeQueryWrapper } from "../../test/queryWrapper";

vi.mock("../../api/client", () => ({
  default: { get: vi.fn() },
}));
import client from "../../api/client";
import useAnalysis from "../useAnalysis";

describe("useAnalysis", () => {
  beforeEach(() => {
    client.get.mockReset();
  });

  it("does not issue any request when contractId is falsy", async () => {
    const { Wrapper } = makeQueryWrapper();
    const { result } = renderHook(() => useAnalysis(undefined), { wrapper: Wrapper });
    expect(result.current.structure.fetchStatus).toBe("idle");
    expect(result.current.summary.fetchStatus).toBe("idle");
    expect(result.current.risks.fetchStatus).toBe("idle");
    expect(result.current.missing.fetchStatus).toBe("idle");
    expect(client.get).not.toHaveBeenCalled();
  });

  it("issues four parallel queries for the four analysis endpoints", async () => {
    client.get.mockImplementation((url) => {
      if (url.endsWith("/structure")) return Promise.resolve({ data: { data: [{ id: 1 }] } });
      if (url.endsWith("/summary")) return Promise.resolve({ data: { data: { party_a: "A" } } });
      if (url.endsWith("/risks")) return Promise.resolve({ data: { data: [{ risk_level: "high" }] } });
      if (url.endsWith("/missing")) return Promise.resolve({ data: { data: [{ item_name: "x" }] } });
      return Promise.reject(new Error(`unexpected url ${url}`));
    });
    const { Wrapper } = makeQueryWrapper();
    const { result } = renderHook(() => useAnalysis(42), { wrapper: Wrapper });

    await waitFor(() => {
      expect(result.current.structure.isSuccess).toBe(true);
      expect(result.current.summary.isSuccess).toBe(true);
      expect(result.current.risks.isSuccess).toBe(true);
      expect(result.current.missing.isSuccess).toBe(true);
    });

    expect(result.current.structure.data).toEqual([{ id: 1 }]);
    expect(result.current.summary.data).toEqual({ party_a: "A" });
    expect(result.current.risks.data[0].risk_level).toBe("high");
    expect(result.current.missing.data[0].item_name).toBe("x");

    const urls = client.get.mock.calls.map((c) => c[0]);
    expect(urls).toEqual(
      expect.arrayContaining([
        "/analysis/42/structure",
        "/analysis/42/summary",
        "/analysis/42/risks",
        "/analysis/42/missing",
      ])
    );
  });

  it("propagates errors per query without affecting siblings", async () => {
    client.get.mockImplementation((url) => {
      if (url.endsWith("/risks")) return Promise.reject(new Error("boom"));
      return Promise.resolve({ data: { data: [] } });
    });
    const { Wrapper } = makeQueryWrapper();
    const { result } = renderHook(() => useAnalysis(7), { wrapper: Wrapper });

    await waitFor(() => {
      expect(result.current.structure.isSuccess).toBe(true);
      expect(result.current.summary.isSuccess).toBe(true);
      expect(result.current.missing.isSuccess).toBe(true);
      expect(result.current.risks.isError).toBe(true);
    });
    expect(result.current.risks.error.message).toBe("boom");
  });
});
