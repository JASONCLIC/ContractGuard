import { useQuery } from "@tanstack/react-query";

import client from "../api/client";

function fetcher(url) {
  return client.get(url).then((res) => res.data.data);
}

export default function useAnalysis(contractId) {
  const enabled = Boolean(contractId);

  const structure = useQuery({
    queryKey: ["analysis-structure", contractId],
    queryFn: () => fetcher(`/analysis/${contractId}/structure`),
    enabled,
  });

  const summary = useQuery({
    queryKey: ["analysis-summary", contractId],
    queryFn: () => fetcher(`/analysis/${contractId}/summary`),
    enabled,
  });

  const risks = useQuery({
    queryKey: ["analysis-risks", contractId],
    queryFn: () => fetcher(`/analysis/${contractId}/risks`),
    enabled,
  });

  const missing = useQuery({
    queryKey: ["analysis-missing", contractId],
    queryFn: () => fetcher(`/analysis/${contractId}/missing`),
    enabled,
  });

  return { structure, summary, risks, missing };
}
