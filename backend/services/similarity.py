"""Explainable weighted resume-to-job scoring from the project model slide."""

from functools import lru_cache
import os
from collections.abc import Iterable

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .skills import find_skills


def compare_text(resume_text: str, job_text: str) -> float:
    """Return cosine similarity in the range 0..1 for TF-IDF text vectors."""
    if not resume_text.strip() or not job_text.strip():
        return 0.0
    # Convert the two documents into TF-IDF vectors so their word overlap can be measured.
    try:
        vectors = TfidfVectorizer(stop_words="english").fit_transform([resume_text, job_text])
        # Cosine similarity compares vector direction; it is a match score, not a probability.
        return float(cosine_similarity(vectors[0:1], vectors[1:2])[0][0])
    except ValueError:
        # This can happen when both documents contain only punctuation or stop words.
        return 0.0


def skill_comparison(resume_skills: str | Iterable[str], required_skills: str) -> tuple[list[str], list[str]]:
    """Compare job requirements to the candidate's extracted, human-reviewable skill list."""
    required = list(dict.fromkeys(skill.strip() for skill in required_skills.split(",") if skill.strip()))
    available = find_skills(resume_skills) if isinstance(resume_skills, str) else list(resume_skills)
    available_lower = {skill.strip().casefold() for skill in available if skill.strip()}
    matched, missing = [], []
    for skill in required:
        (matched if skill.casefold() in available_lower else missing).append(skill)
    return matched, missing


def experience_signal(records: Iterable[dict]) -> float:
    """Return 1 when at least one experience period has a detected date range, otherwise 0.

    This checks whether dates were found. It does not decide whether the experience is
    relevant or meets a job's required years.
    """
    return float(any(record.get("start_date", "").strip() and record.get("end_date", "").strip()
                     for record in records))


def education_signal(records: Iterable[dict]) -> float:
    """Return 1 when any education details were detected, otherwise 0."""
    return float(any(record.get("degree", "").strip() or record.get("institution", "").strip()
                     for record in records))


def combine_scores(tfidf: float, skills: float, experience: float, education: float,
                   semantic: float | None = None) -> dict:
    """Apply the slide's weights and return the total plus an explainable breakdown."""
    if semantic is None:
        weights = {"tfidf": 0.55, "skills": 0.30, "experience": 0.10, "education": 0.05}
    else:
        weights = {"semantic": 0.40, "skills": 0.30, "tfidf": 0.15, "experience": 0.10, "education": 0.05}

    scores = {"tfidf": tfidf, "skills": skills, "experience": experience, "education": education}
    if semantic is not None:
        scores["semantic"] = semantic

    labels = {
        "semantic": "Semantic similarity (SBERT)",
        "skills": "Required-skill coverage",
        "tfidf": "TF-IDF text similarity",
        "experience": "Experience dates detected",
        "education": "Education details detected",
    }
    components = []
    total = 0.0
    for key, weight in weights.items():
        raw_score = max(0.0, min(1.0, scores[key]))
        contribution = raw_score * weight
        total += contribution
        components.append({
            "key": key,
            "label": labels[key],
            "score": round(raw_score * 100, 1),
            "weight": round(weight * 100),
            "contribution": round(contribution * 100, 1),
        })
    return {"overall_score": round(total * 100, 1), "components": components,
            "formula": "0.55 × TF-IDF + 0.30 × skills + 0.10 × experience + 0.05 × education"
            if semantic is None else
            "0.40 × SBERT + 0.30 × skills + 0.15 × TF-IDF + 0.10 × experience + 0.05 × education"}


@lru_cache(maxsize=1)
def _load_sentence_model(model_name: str):
    # Import only when SBERT is explicitly configured; the required app works without it.
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(model_name)


def semantic_similarity(resume_text: str, job_text: str, model_name: str) -> float:
    """Compare normalized SBERT embeddings. The optional package/model loads on first use."""
    model = _load_sentence_model(model_name)
    vectors = model.encode([resume_text, job_text], normalize_embeddings=True)
    # Normalized vectors' dot product is cosine similarity.
    return max(0.0, min(1.0, float(vectors[0] @ vectors[1])))


def calculate_match(resume_text: str, job_text: str, candidate_skills: Iterable[str],
                    required_skills: str, experience_records: Iterable[dict],
                    education_records: Iterable[dict]) -> dict:
    """Calculate every score component and fall back to the deck's default if SBERT fails."""
    tfidf = compare_text(resume_text, job_text)
    matched, missing = skill_comparison(candidate_skills, required_skills)
    requirements = [item.strip() for item in required_skills.split(",") if item.strip()]
    skill_score = len(matched) / len(requirements) if requirements else 0.0

    configured_model = os.getenv("SBERT_MODEL", "").strip()
    semantic = None
    semantic_error = ""
    if configured_model:
        try:
            semantic = semantic_similarity(resume_text, job_text, configured_model)
        except Exception:
            # Optional model setup or inference problems must not break baseline matching.
            semantic_error = "SBERT could not be loaded; the default TF-IDF weights were used."

    result = combine_scores(tfidf, skill_score, experience_signal(experience_records),
                             education_signal(education_records), semantic)
    result.update({
        "tfidf_score": round(tfidf * 100, 1),
        "semantic_score": round(semantic * 100, 1) if semantic is not None else None,
        "matched_skills": matched,
        "missing_skills": missing,
        "semantic_error": semantic_error,
    })
    return result
