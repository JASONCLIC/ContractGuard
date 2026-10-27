import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";

import useContractStore from "../../store/useContractStore";

vi.mock("../../api/client", () => ({
  default: { post: vi.fn() },
}));
import client from "../../api/client";

const navigateMock = vi.fn();
vi.mock("react-router-dom", () => ({
  useNavigate: () => navigateMock,
}));

import useContractUpload from "../useContractUpload";

describe("useContractUpload — submitText", () => {
  beforeEach(() => {
    client.post.mockReset();
    navigateMock.mockReset();
    useContractStore.setState({ contractId: null, jobId: null });
  });

  it("calls /contract/paste, stores ids, navigates to /analysis/loading when job_id present", async () => {
    client.post.mockResolvedValue({
      data: { data: { contract_id: 11, job_id: 22 } },
    });
    const { result } = renderHook(() => useContractUpload());

    await act(async () => {
      await result.current.submitText("Article 1.", "labor", "demo");
    });

    expect(client.post).toHaveBeenCalledWith("/contract/paste", {
      text: "Article 1.",
      title: "demo",
      contract_type: "labor",
    });
    expect(useContractStore.getState()).toMatchObject({ contractId: 11, jobId: 22 });
    expect(navigateMock).toHaveBeenCalledWith("/analysis/loading");
    expect(result.current.message).toContain("Contract ID: 11");
    expect(result.current.error).toBe("");
    expect(result.current.loading).toBe(false);
  });

  it("navigates to /analysis/result when job_id is null (duplicated contract)", async () => {
    client.post.mockResolvedValue({
      data: { data: { contract_id: 99, job_id: null, duplicated: true } },
    });
    const { result } = renderHook(() => useContractUpload());

    await act(async () => {
      await result.current.submitText("Article 1.");
    });

    expect(navigateMock).toHaveBeenCalledWith("/analysis/result");
    expect(useContractStore.getState()).toMatchObject({ contractId: 99, jobId: null });
  });

  it("captures server error message on failure and does not navigate", async () => {
    client.post.mockRejectedValue({
      response: { data: { message: "text too long" } },
    });
    const { result } = renderHook(() => useContractUpload());

    await act(async () => {
      await result.current.submitText("x".repeat(50001));
    });

    expect(result.current.error).toBe("text too long");
    expect(result.current.message).toBe("");
    expect(navigateMock).not.toHaveBeenCalled();
    expect(result.current.loading).toBe(false);
  });

  it("falls back to a generic message when the error has no server payload", async () => {
    client.post.mockRejectedValue(new Error("network"));
    const { result } = renderHook(() => useContractUpload());

    await act(async () => {
      await result.current.submitText("abc");
    });

    expect(result.current.error).toMatch(/Submission failed/i);
  });
});

describe("useContractUpload — getUploadProps", () => {
  beforeEach(() => {
    client.post.mockReset();
    navigateMock.mockReset();
    useContractStore.setState({ contractId: null, jobId: null });
  });

  it("returns Ant Upload props with PDF accept + withCredentials", () => {
    const { result } = renderHook(() => useContractUpload());
    const props = result.current.getUploadProps("labor");
    expect(props.name).toBe("file");
    expect(props.accept).toBe(".pdf,application/pdf");
    expect(props.withCredentials).toBe(true);
    expect(props.data).toEqual({ contract_type: "labor" });
    expect(props.action).toContain("/contract/upload");
  });

  it("beforeUpload accepts a valid PDF file under 10MB", () => {
    const { result } = renderHook(() => useContractUpload());
    let ok;
    act(() => {
      ok = result.current.getUploadProps().beforeUpload({
        type: "application/pdf",
        name: "doc.pdf",
        size: 1024,
      });
    });
    expect(ok).toBe(true);
  });

  it("beforeUpload rejects non-PDF files and sets error", () => {
    const { result } = renderHook(() => useContractUpload());
    let out;
    act(() => {
      out = result.current.getUploadProps().beforeUpload({
        type: "image/png",
        name: "doc.png",
        size: 1024,
      });
    });
    expect(out).not.toBe(true);
    expect(result.current.error).toMatch(/Only PDF/i);
  });

  it("beforeUpload rejects files larger than 10MB", () => {
    const { result } = renderHook(() => useContractUpload());
    let out;
    act(() => {
      out = result.current.getUploadProps().beforeUpload({
        type: "application/pdf",
        name: "huge.pdf",
        size: 11 * 1024 * 1024,
      });
    });
    expect(out).not.toBe(true);
    expect(result.current.error).toMatch(/too large/i);
  });

  it("onChange success → setContract + navigate to /analysis/loading", () => {
    const { result } = renderHook(() => useContractUpload());
    act(() => {
      result.current.getUploadProps().onChange({
        file: {
          status: "done",
          response: { data: { contract_id: 7, job_id: 8 } },
        },
      });
    });
    expect(useContractStore.getState()).toMatchObject({ contractId: 7, jobId: 8 });
    expect(navigateMock).toHaveBeenCalledWith("/analysis/loading");
    expect(result.current.message).toContain("Contract ID: 7");
  });

  it("onChange success with null job_id → navigate to /analysis/result", () => {
    const { result } = renderHook(() => useContractUpload());
    act(() => {
      result.current.getUploadProps().onChange({
        file: { status: "done", response: { data: { contract_id: 12, job_id: null } } },
      });
    });
    expect(navigateMock).toHaveBeenCalledWith("/analysis/result");
  });

  it("onChange error → records server message", () => {
    const { result } = renderHook(() => useContractUpload());
    act(() => {
      result.current.getUploadProps().onChange({
        file: {
          status: "error",
          response: { message: "Invalid PDF file header." },
        },
      });
    });
    expect(result.current.error).toBe("Invalid PDF file header.");
  });

  it("onChange error → falls back to generic message when payload missing", () => {
    const { result } = renderHook(() => useContractUpload());
    act(() => {
      result.current.getUploadProps().onChange({ file: { status: "error" } });
    });
    expect(result.current.error).toMatch(/Upload failed/i);
  });

  it("onChange ignores intermediate statuses like 'uploading'", () => {
    const { result } = renderHook(() => useContractUpload());
    act(() => {
      result.current.getUploadProps().onChange({ file: { status: "uploading" } });
    });
    expect(navigateMock).not.toHaveBeenCalled();
    expect(result.current.error).toBe("");
  });
});
