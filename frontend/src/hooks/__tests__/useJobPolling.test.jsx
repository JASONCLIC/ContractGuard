import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";

import { makeQueryWrapper } from "../../test/queryWrapper";

vi.mock("../../api/client", () => ({
  default: { get: vi.fn() },
}));
import client from "../../api/client";
import useJobPolling from "../useJobPolling";

describe("useJobPolling", () => {
  beforeEach(() => {
    client.get.mockReset();
  });

  it("does not query when jobId is falsy", () => {
    const { Wrapper } = makeQueryWrapper();
    const { result } = renderHook(() => useJobPolling(null), { wrapper: Wrapper });
    expect(result.current.fetchStatus).toBe("idle");
    expect(client.get).not.toHaveBeenCalled();
  });

  it("fetches /jobs/<id> on mount and unwraps res.data.data", async () => {
    client.get.mockResolvedValue({
      data: { data: { job_id: 99, status: "running", progress_percent: 30 } },
    });
    const { Wrapper } = makeQueryWrapper();
    const { result } = renderHook(() => useJobPolling(99), { wrapper: Wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(client.get).toHaveBeenCalledWith("/jobs/99");
    expect(result.current.data).toMatchObject({ job_id: 99, status: "running" });
  });

  it("keeps polling every 2s while status is running", async () => {
    vi.useFakeTimers({ toFake: ["setInterval", "clearInterval", "setTimeout", "clearTimeout"] });
    try {
      client.get.mockResolvedValue({
        data: { data: { job_id: 1, status: "running" } },
      });
      const { Wrapper } = makeQueryWrapper();
      renderHook(() => useJobPolling(1), { wrapper: Wrapper });

      await act(async () => {
        await vi.advanceTimersByTimeAsync(0);
      });
      expect(client.get).toHaveBeenCalledTimes(1);

      await act(async () => {
        await vi.advanceTimersByTimeAsync(2000);
      });
      expect(client.get).toHaveBeenCalledTimes(2);

      await act(async () => {
        await vi.advanceTimersByTimeAsync(2000);
      });
      expect(client.get).toHaveBeenCalledTimes(3);
    } finally {
      vi.useRealTimers();
    }
  });

  it("stops polling once status becomes success", async () => {
    vi.useFakeTimers({ toFake: ["setInterval", "clearInterval", "setTimeout", "clearTimeout"] });
    try {
      client.get
        .mockResolvedValueOnce({ data: { data: { job_id: 1, status: "running" } } })
        .mockResolvedValue({ data: { data: { job_id: 1, status: "success" } } });

      const { Wrapper } = makeQueryWrapper();
      renderHook(() => useJobPolling(1), { wrapper: Wrapper });

      await act(async () => {
        await vi.advanceTimersByTimeAsync(0);
      });
      expect(client.get).toHaveBeenCalledTimes(1);

      await act(async () => {
        await vi.advanceTimersByTimeAsync(2000);
      });
      expect(client.get).toHaveBeenCalledTimes(2);

      // Hook has now seen status=success — polling must halt.
      await act(async () => {
        await vi.advanceTimersByTimeAsync(10_000);
      });
      expect(client.get).toHaveBeenCalledTimes(2);
    } finally {
      vi.useRealTimers();
    }
  });

  it("stops polling once status becomes failed", async () => {
    vi.useFakeTimers({ toFake: ["setInterval", "clearInterval", "setTimeout", "clearTimeout"] });
    try {
      client.get
        .mockResolvedValueOnce({ data: { data: { job_id: 5, status: "running" } } })
        .mockResolvedValue({
          data: { data: { job_id: 5, status: "failed", error_message: "boom" } },
        });

      const { Wrapper } = makeQueryWrapper();
      renderHook(() => useJobPolling(5), { wrapper: Wrapper });

      await act(async () => {
        await vi.advanceTimersByTimeAsync(0);
      });
      expect(client.get).toHaveBeenCalledTimes(1);

      await act(async () => {
        await vi.advanceTimersByTimeAsync(2000);
      });
      expect(client.get).toHaveBeenCalledTimes(2);

      await act(async () => {
        await vi.advanceTimersByTimeAsync(10_000);
      });
      expect(client.get).toHaveBeenCalledTimes(2);
    } finally {
      vi.useRealTimers();
    }
  });
});
