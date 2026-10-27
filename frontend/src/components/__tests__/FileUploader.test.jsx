import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import FileUploader from "../FileUploader";

describe("<FileUploader />", () => {
  it("renders the dragger area with hint text", () => {
    render(<FileUploader uploadProps={{ name: "file" }} />);
    expect(
      screen.getByText(/Click or drag a file to this area/i)
    ).toBeInTheDocument();
    expect(screen.getByText(/PDF format only \(max 10MB\)/i)).toBeInTheDocument();
  });

  it("forwards uploadProps to the underlying Ant Upload.Dragger", () => {
    // The dragger renders an <input type="file"> with `accept` mirrored from props.
    render(
      <FileUploader
        uploadProps={{
          name: "file",
          accept: ".pdf,application/pdf",
          beforeUpload: () => false,
        }}
      />
    );
    const input = document.querySelector("input[type='file']");
    expect(input).not.toBeNull();
    expect(input.getAttribute("accept")).toBe(".pdf,application/pdf");
  });
});
