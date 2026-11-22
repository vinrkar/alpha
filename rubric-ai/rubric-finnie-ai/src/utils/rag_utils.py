RRF_K_CONSTANT = 60
MAX_RRF_CEILING = 2 / (RRF_K_CONSTANT + 1)
DEFAULT_REPORT_CHAR_LIMIT = 2500

def compute_rrf_score(ranks: list[int], k: int = RRF_K_CONSTANT) -> float:
    """Computes the raw Reciprocal Rank Fusion score from 1-based retriever ranks."""
    return sum(1.0 / (k + rank) for rank in ranks)

def normalize_rrf_score(raw_score: float) -> float:
    """Normalizes a raw RRF score onto a 0.0 to 1.0 scale."""
    return min(1.0, raw_score / MAX_RRF_CEILING)

def get_confidence_percentage(raw_score: float) -> float:
    """Converts a raw RRF score into a 0.0–100.0% confidence score."""
    return round(normalize_rrf_score(raw_score) * 100, 1)

def get_confidence_tier(confidence_pct: float) -> tuple[str, str]:
    """Maps a confidence percentage to a UI badge label and description."""
    if confidence_pct >= 85.0:
        return "🟢 High Confidence", "Exact keyword & semantic consensus"
    if confidence_pct >= 45.0:
        return "🟡 Moderate Confidence", "Partial keyword or semantic overlap"
    return "🔴 Low Confidence", "Marginal relevance"

def truncate_report_text(text: str, max_chars: int = DEFAULT_REPORT_CHAR_LIMIT) -> str:
    """Truncates long text excerpts cleanly near sentence or word boundaries."""
    if not text or len(text) <= max_chars:
        return text

    truncated = text[:max_chars]
    last_period = truncated.rfind(".")
    if last_period > int(max_chars * 0.7):
        return truncated[: last_period + 1] + " [Excerpt truncated for readability]"

    last_space = truncated.rfind(" ")
    if last_space > 0:
        return truncated[:last_space] + "... [Excerpt truncated for readability]"

    return truncated + "... [Excerpt truncated for readability]"