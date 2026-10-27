import { Upload } from "antd";
import { InboxOutlined } from "@ant-design/icons";

export default function FileUploader({ uploadProps }) {
  return (
    <Upload.Dragger
      {...uploadProps}
      style={{ borderRadius: "var(--r-lg)", border: "2px dashed rgba(0,0,0,0.1)" }}
    >
      <div style={{ padding: "28px 0" }}>
        <InboxOutlined
          style={{ fontSize: 40, color: "var(--blue)", display: "block", marginBottom: 12 }}
        />
        <p style={{ fontSize: 15, fontWeight: 500, color: "var(--dark)", marginBottom: 6 }}>
          Click or drag a file to this area
        </p>
        <p style={{ fontSize: 13, color: "var(--gray)" }}>
          Supports PDF format only (max 10MB)
        </p>
      </div>
    </Upload.Dragger>
  );
}
