import re

from PyPDF2 import PdfReader

# PyPDF2 经常把整页内容拼成一行，用此正则在条款标题前补换行（中英文双语）
_HEADING_BOUNDARY = re.compile(
    r"(?<!\n)"
    r"("
    r"(?:Article|Section|Clause)\s+\d+"          # Article 1 / Section 2
    r"|第[零一二三四五六七八九十百千\d]+条"        # 第X条
    r"|[（(][一二三四五六七八九十\d]+[）)]"        # （一）(1)
    r"|(?<![0-9])[1-9][0-9]{0,1}[.、．](?!\d)"   # 1. 2、（非小数点）
    r")",
    re.IGNORECASE,
)

# PyPDF2 经常合并相邻行时丢失空格/换行，产生 "PositionThe" 这类粘连
# 检测小写字母(或句末标点)紧跟大写字母开头的单词，在中间补换行
_MISSING_LINEBREAK = re.compile(r'([a-z.!?;)\]）】])([A-Z][a-z])')


def read_pdf(file_storage) -> str:
    reader = PdfReader(file_storage)
    raw = "\n".join((page.extract_text() or "") for page in reader.pages)
    # 在条款标题前补换行，修复 PyPDF2 丢失换行的问题
    text = _HEADING_BOUNDARY.sub(r"\n\1", raw)
    # 修复行合并导致的单词粘连（如 "PositionThe" → "Position\nThe"）
    text = _MISSING_LINEBREAK.sub(r"\1\n\2", text)
    return text


def extract_text_from_upload(file_storage) -> str:
    mimetype = file_storage.mimetype
    if mimetype in {"application/pdf", "application/x-pdf"}:
        return read_pdf(file_storage.stream)
    raise ValueError("Unsupported file type. Only PDF files are accepted.")
