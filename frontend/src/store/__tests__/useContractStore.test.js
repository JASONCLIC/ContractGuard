import { describe, it, expect, beforeEach } from "vitest";
import useContractStore from "../useContractStore";

describe("useContractStore", () => {
  beforeEach(() => {
    useContractStore.setState({ contractId: null, jobId: null });
  });

  it("initial state is { contractId: null, jobId: null }", () => {
    expect(useContractStore.getState()).toMatchObject({ contractId: null, jobId: null });
  });

  it("setContractId only updates contractId", () => {
    useContractStore.getState().setContractId(7);
    expect(useContractStore.getState().contractId).toBe(7);
    expect(useContractStore.getState().jobId).toBeNull();
  });

  it("setJobId only updates jobId", () => {
    useContractStore.getState().setJobId(42);
    expect(useContractStore.getState().jobId).toBe(42);
    expect(useContractStore.getState().contractId).toBeNull();
  });

  it("setContract sets both atomically", () => {
    useContractStore.getState().setContract(11, 22);
    expect(useContractStore.getState()).toMatchObject({ contractId: 11, jobId: 22 });
  });

  it("setContract accepts null jobId (duplicated contract case)", () => {
    useContractStore.getState().setContract(99, null);
    expect(useContractStore.getState()).toMatchObject({ contractId: 99, jobId: null });
  });
});
