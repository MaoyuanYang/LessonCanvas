import re

STUDENT_DATA_PATTERNS = [
    re.compile(r"身份证号[:：]?\s*\d{17}[\dXx]", re.IGNORECASE),
    re.compile(r"学籍号[:：]?\s*[A-Z0-9]{10,}", re.IGNORECASE),
    re.compile(r"(学生|考生)姓名[:：]", re.IGNORECASE),
    re.compile(r"(成绩|分数)[:：].*(班级|排名)", re.IGNORECASE),
    re.compile(r"\b\d{1}[1-9]\d{4}(19|20)\d{2}(0[1-9]|1[0-2])\d{2}\d{3}[\dXx]\b"),
]


def screen_for_student_data(text: str) -> str | None:
    for pattern in STUDENT_DATA_PATTERNS:
        if pattern.search(text):
            return "source appears to contain identifiable student data"
    return None
