"""An editable, beginner-friendly dictionary of skills to look for in resumes."""

SKILLS = [
    "Python", "Java", "C++", "C#", "JavaScript", "TypeScript", "HTML", "CSS",
    "SQL", "PostgreSQL", "MySQL", "SQLite", "Git", "Docker", "React", "Node.js",
    "FastAPI", "Django", "Flask", "Pandas", "NumPy", "scikit-learn", "TensorFlow",
    "PyTorch", "Machine Learning", "Data Analysis", "Excel", "Linux", "AWS",
]


def find_skills(text: str) -> list[str]:
    """Match known skill names case-insensitively, avoiding partial-word matches."""
    import re

    found = []
    for skill in SKILLS:
        pattern = r"(?<![\w+#.])" + re.escape(skill) + r"(?![\w+#.])"
        if re.search(pattern, text, flags=re.IGNORECASE):
            found.append(skill)
    return found
