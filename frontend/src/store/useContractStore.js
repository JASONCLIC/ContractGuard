import { create } from "zustand";

const useContractStore = create((set) => ({
  contractId: null,
  jobId: null,
  setContractId: (contractId) => set({ contractId }),
  setJobId: (jobId) => set({ jobId }),
  setContract: (contractId, jobId) => set({ contractId, jobId }),
}));

export default useContractStore;
