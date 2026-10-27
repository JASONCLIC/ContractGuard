def validate_text_input(text: str):
    if text is None:
        return False, "text is required"
    if not text.strip():
        return False, "text is empty"
    if len(text) > 50000:
        return False, "text too long"
    return True, ""
