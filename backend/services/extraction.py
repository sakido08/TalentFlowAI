"""Hybrid extraction: regular expressions, section headings, and skill keywords."""

import re

from .preprocessing import preprocess_text
from .skills import find_skills

EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)
PHONE_RE = re.compile(r"(?<!\w)(?:\+?\d[\d ().-]{7,}\d)(?!\w)")
DATE_RE = re.compile(
    r"\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|"
    r"Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?\.?\s+)?(?:19|20)\d{2}\b",
    re.I,
)

HEADINGS = {
    "summary": {"summary", "professional summary", "profile", "objective", "about me"},
    "skills": {"skills", "technical skills", "core competencies", "technologies"},
    "education": {"education", "academic background", "educational background"},
    "experience": {"experience", "work experience", "employment history", "professional experience"},
    "certifications": {"certifications", "certificates", "licenses and certifications"},
}


def split_sections(text: str) -> dict[str, str]:
    """Group lines under familiar headings; text before headings is stored as header."""
    result = {"header": ""}
    for key in HEADINGS:
        result[key] = ""
    active = "header"
    for line in preprocess_text(text).splitlines():
        heading = re.sub(r"[\s:|]+$", "", line.strip()).lower()
        matched = next((key for key, aliases in HEADINGS.items() if heading in aliases), None)
        if matched:
            active = matched
        elif line.strip():
            result[active] += line.strip() + "\n"
    return {key: value.strip() for key, value in result.items()}


def _guess_name(header: str, email: str, phone: str) -> str:
    for line in header.splitlines():
        clean = line.strip(" |,;:-")
        if not clean or email.lower() in clean.lower() or (phone and phone in clean):
            continue
        if "@" in clean or re.search(r"https?://|www\.|linkedin", clean, re.I):
            continue
        # Names are usually short and contain letters, spaces, apostrophes, or hyphens.
        if len(clean) <= 80 and re.fullmatch(r"[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ .'-]+", clean):
            return clean
    return ""


def _education_records(section: str) -> list[dict[str, str]]:
    lines = [line.strip(" •-*\t") for line in section.splitlines() if line.strip()]
    if not lines:
        return []
    degree_re = re.compile(r"\b(B\.?S\.?|B\.?A\.?|M\.?S\.?|M\.?A\.?|Ph\.?D\.?|Bachelor|Master|Associate|Diploma)\b", re.I)
    # Many student resumes use one pipe-separated line for degree, school, and dates.
    parts = [part.strip() for line in lines for part in re.split(r"\s*[|•]\s*", line) if part.strip()]
    degree_line = next((part for part in parts if degree_re.search(part)), "")
    date_hits = DATE_RE.findall(" ".join(lines))
    institution = next((part for part in parts if part != degree_line and not DATE_RE.search(part)), "")
    return [{
        "institution": institution[:200],
        "degree": degree_line[:160],
        "field": "",
        "start_date": date_hits[0] if date_hits else "",
        "end_date": date_hits[-1] if len(date_hits) > 1 else "",
    }]


def _experience_records(section: str) -> list[dict[str, str]]:
    lines = [line.strip(" •-*\t") for line in section.splitlines() if line.strip()]
    if not lines:
        return []
    date_hits = DATE_RE.findall(" ".join(lines))
    parts = [part.strip() for line in lines for part in re.split(r"\s*[|•]\s*", line) if part.strip()]
    # Keep the full section as editable description so no extracted details are lost.
    return [{
        "company": parts[0][:200],
        "position": parts[1][:160] if len(parts) > 1 else "",
        "description": "\n".join(lines),
        "start_date": date_hits[0] if date_hits else "",
        "end_date": date_hits[-1] if len(date_hits) > 1 else "",
    }]


def extract_information(text: str) -> dict:
    """Extract fields for human review; guesses are intentionally conservative."""
    clean = preprocess_text(text)
    sections = split_sections(clean)
    email = next(iter(EMAIL_RE.findall(clean)), "")
    phone_match = next(iter(PHONE_RE.findall(clean)), "")
    phone = re.sub(r"\s+", " ", phone_match).strip()
    address_match = re.search(r"(?im)^\s*(?:address\s*[:\-]\s*)(.+)$", clean)
    summary_lines = [line.strip() for line in sections["summary"].splitlines() if line.strip()]
    certifications = [line.strip(" •-*\t") for line in sections["certifications"].splitlines() if line.strip()]
    return {
        "full_name": _guess_name(sections["header"], email, phone),
        "email": email,
        "phone": phone,
        "address": address_match.group(1).strip() if address_match else "",
        "summary": " ".join(summary_lines),
        "skills": find_skills(clean),
        "education": _education_records(sections["education"]),
        "experience": _experience_records(sections["experience"]),
        "certifications": certifications,
        "sections": sections,
    }
