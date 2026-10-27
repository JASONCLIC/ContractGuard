import { useQuery } from "@tanstack/react-query";

import client from "../api/client";

/**
 * 轮询 job 状态。
 * pending / running 时每 2s 请求一次；success / failed 时停止轮询。
 */
export default function useJobPolling(jobId) {
  return useQuery({
    queryKey: ["job", jobId],
    queryFn: () => client.get(`/jobs/${jobId}`).then((r) => r.data.data),
    enabled: Boolean(jobId),
    staleTime: 0,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === "success" || status === "failed") return false;
      return 2000;
    },
  });
}
