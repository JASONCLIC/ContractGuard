ALLOWED_MIME = {
    "application/pdf",
    "application/x-pdf",
}
MAX_SIZE = 10 * 1024 * 1024


def validate_upload(file_storage):
    if not file_storage:
        return False, "No file uploaded. Please select a PDF file."
    filename = (file_storage.filename or "").lower().strip()
    if not filename:
        return False, "Missing filename. Please upload a valid PDF file."
    if not filename.endswith(".pdf"):
        return False, "Unsupported file extension. Only .pdf files are allowed."
    if file_storage.mimetype not in ALLOWED_MIME:
        return False, "Unsupported file type. Only PDF files are allowed."
    file_storage.stream.seek(0)
    header = file_storage.stream.read(5)
    file_storage.stream.seek(0)
    if header != b"%PDF-":
        return False, "Invalid PDF file header. Please upload a valid PDF document."
    file_storage.stream.seek(0, 2)
    size = file_storage.stream.tell()
    file_storage.stream.seek(0)
    if size > MAX_SIZE:
        return False, "File too large. Maximum allowed size is 10MB."
    return True, ""
