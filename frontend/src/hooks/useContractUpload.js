import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Upload } from "antd";

import client from "../api/client";
import useContractStore from "../store/useContractStore";

export default function useContractUpload() {
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const setContract = useContractStore((s) => s.setContract);
  const navigate = useNavigate();

  const submitText = async (text, contractType = "labor", title = "manual_input") => {
    try {
      setLoading(true);
      setError("");
      const { data } = await client.post("/contract/paste", {
        text,
        title,
        contract_type: contractType,
      });
      const cid = data?.data?.contract_id;
      const jid = data?.data?.job_id;
      setContract(cid, jid);
      setMessage(`Submitted successfully. Contract ID: ${cid}`);
      // jid 为 null 说明是重复合同（已分析完），直接跳结果页
      navigate(jid ? "/analysis/loading" : "/analysis/result");
    } catch (e) {
      const serverMessage = e?.response?.data?.message;
      setError(serverMessage || "Submission failed. Please check your input or service status.");
      setMessage("");
    } finally {
      setLoading(false);
    }
  };

  const getUploadProps = (contractType = "labor") => ({
    name: "file",
    action: `${import.meta.env.VITE_API_BASE_URL || "/api"}/contract/upload`,
    withCredentials: true,
    data: { contract_type: contractType },
    accept: ".pdf,application/pdf",
    beforeUpload(file) {
      const isPdf = (file.type || "").includes("pdf") || (file.name || "").toLowerCase().endsWith(".pdf");
      if (!isPdf) {
        setError("Only PDF files are allowed.");
        setMessage("");
        return Upload.LIST_IGNORE;
      }
      const isLt10M = file.size <= 10 * 1024 * 1024;
      if (!isLt10M) {
        setError("File too large. Maximum allowed size is 10MB.");
        setMessage("");
        return Upload.LIST_IGNORE;
      }
      return true;
    },
    onChange(info) {
      if (info.file.status === "done") {
        const cid = info.file.response?.data?.contract_id;
        const jid = info.file.response?.data?.job_id;
        setContract(cid, jid);
        setMessage(`Uploaded successfully. Contract ID: ${cid}`);
        setError("");
        navigate(jid ? "/analysis/loading" : "/analysis/result");
      } else if (info.file.status === "error") {
        const serverMessage =
          info?.file?.response?.message ||
          info?.file?.response?.data?.message ||
          info?.file?.error?.message;
        setError(
          serverMessage ||
            "Upload failed. Please upload a valid PDF (max 10MB). If the PDF is scanned or encrypted, text extraction may fail."
        );
        setMessage("");
      }
    },
  });

  return { message, error, loading, submitText, getUploadProps };
}
