"""
String matching algorithms for finding best matches between reference and candidate strings.

The matcher is designed to be:
- deterministic and pure-Python
- explainable (each heuristic is isolated and commented)
- roughly aligned with IR concepts such as IDF weighting, coverage, and soft fuzziness.
"""

import math
import re
from collections import Counter, defaultdict
from functools import lru_cache
from difflib import SequenceMatcher
from typing import Dict, Iterable, List, Sequence, Tuple

SIM_THRESHOLD = 0.5

# Similarity required for two tokens to be considered matching
TOKEN_SIM_THRESHOLD = 0.8

# Soft penalty strength for extra / noisy tokens on the candidate side
NOISE_PENALTY_STRENGTH = 0.7  # in [0, 1]; smaller = stronger penalty

# How quickly importance decays for later tokens (earlier tokens matter more)
POSITION_DECAY = 0.3  # 0 = no decay, 1 = strong decay

# Limit for how many candidates go through the expensive fuzzy scoring.
# A cheap pre-filter keeps only the most promising ones.
MAX_HEAVY_CANDIDATES = 64

# Common low-information tokens that should keep very small but non-zero weight
STOPWORDS = {
    "ltd",
    "llc",
    "ooo",
    "zao",
    "ao",
    "company",
    "co",
    "inc",
    "corp",
    "corporation",
    "the",
    "and",
}


def tokenize(text: str) -> List[str]:
    """Tokenize text into words (alphanumeric sequences), lowercased."""
    return re.findall(r"\w+", (text or "").lower())


def shift_weight(pos_a: int, pos_b: int, max_len: int) -> float:
    """
    Positional weight based on token positions.

    Earlier tokens and aligned order should get slightly higher impact,
    but order mismatches should reduce the score smoothly instead of harshly.
    """
    if max_len <= 0:
        return 1.0
    # Original linear decay by distance, but bounded to [0, 1]
    base = max(0.0, 1.0 - abs(pos_a - pos_b) / max_len)
    # Compress the effect so that even misordered tokens still contribute
    # (0.5..1.0 instead of 0..1.0) to weaken positional harshness.
    return 0.5 + 0.5 * base


def _directional_overlap_score(
    source_tokens: Sequence[str],
    target_tokens: Sequence[str],
    len_max: int,
) -> float:
    """
    Directional positional-overlap score from source -> target.

    Each source token that appears in the target contributes via `shift_weight`,
    and we normalize by the number of source tokens to obtain a coverage-like
    value in [0, 1].
    """
    if not source_tokens or not target_tokens:
        return 0.0

    # Use dict for O(1) lookup instead of list.index() which is O(n)
    target_positions = {token: i for i, token in enumerate(target_tokens)}
    score = 0.0

    for i, token in enumerate(source_tokens):
        if token in target_positions:
            j = target_positions[token]
            score += shift_weight(i, j, len_max)

    return score / len(source_tokens)


def overlap_score(a_tokens: Sequence[str], b_tokens: Sequence[str], len_max: int) -> float:
    """
    Backwards-compatible overlap score between two tokenized strings.

    This retains the original public helper API used elsewhere in the project
    while making the score symmetric and coverage-aware.

    We compute directional coverage scores:
      - score(a -> b): how well `a` is covered inside `b`
      - score(b -> a): how well `b` is covered inside `a`

    These two are then combined with a length-aware weighting that emphasizes
    coverage of the shorter side so that short strings that fully match a part
    of a longer one can still receive a high score.
    """
    if not a_tokens or not b_tokens:
        return 0.0

    len_a = len(a_tokens)
    len_b = len(b_tokens)

    if len_a == 0 or len_b == 0:
        return 0.0

    # Directional positional overlaps
    score_a_to_b = _directional_overlap_score(a_tokens, b_tokens, len_max)
    score_b_to_a = _directional_overlap_score(b_tokens, a_tokens, len_max)

    # Length ratio in (0, 1]; smaller when strings differ a lot in length
    min_len = min(len_a, len_b)
    max_len = max(len_a, len_b)
    length_ratio = min_len / max_len if max_len > 0 else 1.0

    # Emphasize coverage of the shorter side to avoid unfairly penalizing
    # short candidates that match a contiguous part of a long reference.
    short_side_score = max(score_a_to_b, score_b_to_a)
    long_side_score = min(score_a_to_b, score_b_to_a)

    # Weight for the shorter side is in [0.85, 1.0]; when lengths are equal
    # both directions are usually similar, so using max is effectively symmetric.
    alpha = 0.85 + 0.15 * length_ratio
    beta = 1.0 - alpha

    combined = alpha * short_side_score + beta * long_side_score

    # Safety clamp to [0, 1]
    return max(0.0, min(1.0, combined))


def _compute_document_frequencies(
    candidates_tokens: Sequence[Sequence[str]],
) -> Tuple[Dict[str, int], int]:
    """
    Compute document frequency df(token) over all candidate strings.

    Each candidate contributes at most 1 to a token's df, regardless of
    how many times it appears in that candidate.
    """
    df: Dict[str, int] = defaultdict(int)
    doc_count = 0

    for tokens in candidates_tokens:
        if not tokens:
            continue
        doc_count += 1
        unique_tokens = set(tokens)
        for t in unique_tokens:
            df[t] += 1

    return df, doc_count


def _token_idf(token: str, df: Dict[str, int], doc_count: int) -> float:
    """
    IDF-style weight for a token.

    We use a simple smooth formulation:
        idf = log(1 + N / df)
    where N is the number of documents (candidates) that have at least one token.

    Stopwords get a strongly reduced but non-zero weight so they never dominate.
    """
    if doc_count <= 0:
        return 1.0

    df_t = df.get(token, 1)
    base_idf = math.log(1.0 + doc_count / df_t)

    if token in STOPWORDS:
        # Strongly down-weight stopwords but do not drop them completely
        return max(base_idf * 0.1, 0.01)

    return base_idf


def _token_position_weight(index: int, length: int) -> float:
    """
    Weight earlier tokens slightly more than later tokens.

    This is independent of cross-string alignment and only depends on the
    token's own position within its string.
    """
    if length <= 1 or POSITION_DECAY <= 0:
        return 1.0
    rel_pos = index / (length - 1)  # 0 for first token, 1 for last
    # Linear decay from 1.0 to (1 - POSITION_DECAY)
    return 1.0 - POSITION_DECAY * rel_pos


@lru_cache(maxsize=10_000)
def _token_similarity(a: str, b: str) -> float:
    """
    Soft character-level similarity between two tokens.

    - Exact match -> 1.0
    - Prefix/substring matches are boosted
    - General fuzziness via SequenceMatcher ratio
    """
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0

    # Fast path: strong prefix / substring matches without SequenceMatcher
    if a.startswith(b) or b.startswith(a) or a in b or b in a:
        return 0.9

    # If token lengths differ too much, they cannot reach high similarity.
    max_len = max(len(a), len(b))
    if max_len == 0:
        return 0.0
    length_diff = abs(len(a) - len(b))
    # Upper bound on similarity ~ (max_len - length_diff) / max_len
    if (max_len - length_diff) / max_len < TOKEN_SIM_THRESHOLD:
        return 0.0

    # Base similarity from character-level alignment
    sim = SequenceMatcher(None, a, b).ratio()

    # Clamp to [0, 1]
    return max(0.0, min(1.0, sim))


def _directional_similarity(
    source_tokens: Sequence[str],
    target_tokens: Sequence[str],
    df: Dict[str, int],
    doc_count: int,
) -> float:
    """
    Compute coverage-based similarity from source -> target.

    - For each source token we find the best-matching target token (if any)
    - Each source token can match at most one target token (best-match-per-token)
    - Contribution is IDF-weighted and scaled by both token similarity and position
    - Coverage = matched_weight / total_weight
    - A soft noise penalty is applied for unmatched tokens on the target side
    """
    if not source_tokens or not target_tokens:
        return 0.0

    src_len = len(source_tokens)
    tgt_len = len(target_tokens)

    # Pre-compute per-token base weights for the source side
    src_token_weights: List[float] = []
    for i, tok in enumerate(source_tokens):
        idf = _token_idf(tok, df, doc_count)
        pos_w = _token_position_weight(i, src_len)
        src_token_weights.append(idf * pos_w)

    total_weight = sum(src_token_weights)
    if total_weight <= 0:
        return 0.0

    # Track which target indices have already been "consumed" by best matches
    used_target_indices = set()

    matched_weight = 0.0

    for i, (src_tok, base_weight) in enumerate(zip(source_tokens, src_token_weights)):
        best_idx = None
        best_contrib = 0.0

        for j, tgt_tok in enumerate(target_tokens):
            # We allow multiple source tokens to consider the same target token,
            # but select the best target per source token only.
            sim = _token_similarity(src_tok, tgt_tok)
            if sim < TOKEN_SIM_THRESHOLD:
                continue

            # Positional influence between this source and target token
            pos_align = shift_weight(i, j, max(src_len, tgt_len))

            # Combine character similarity and positional alignment smoothly
            #  - sim in [0.8, 1]
            #  - pos_align in [0.5, 1]
            combined = sim * pos_align

            if combined > best_contrib:
                best_contrib = combined
                best_idx = j

        if best_idx is not None:
            used_target_indices.add(best_idx)
            # Weight contribution scaled by how good the best match is
            matched_weight += base_weight * best_contrib

    coverage = matched_weight / total_weight

    # Compute a soft penalty for extra / noisy tokens in the target
    # that were not used in any best match.
    if NOISE_PENALTY_STRENGTH > 0 and tgt_len > 0:
        # For each unused target token, estimate its weight (IDF + position)
        extra_weights = []
        for j, tok in enumerate(target_tokens):
            if j in used_target_indices:
                continue
            idf = _token_idf(tok, df, doc_count)
            pos_w = _token_position_weight(j, tgt_len)
            extra_weights.append(idf * pos_w)

        total_extra = sum(extra_weights)

        if total_extra > 0 and matched_weight > 0:
            # Relative amount of "noise" compared to matched signal
            noise_ratio = total_extra / (matched_weight + total_extra)

            # Scale the impact of noise by how long the *source* is compared to
            # the combined length. When the source is much shorter than the target
            # (e.g., short candidate vs long reference), we down-weight this
            # penalty very aggressively so that covering the short side well is
            # strongly rewarded, and unmatched tail tokens in the longer string
            # do not dominate the score.
            length_ratio = src_len / (src_len + tgt_len) if (src_len + tgt_len) > 0 else 0.5
            # Square the ratio so that for very short sources the effective noise
            # becomes tiny (e.g., 0.2 -> 0.04), while remaining closer to 1.0
            # when lengths are comparable.
            effective_noise = noise_ratio * (length_ratio ** 2)

            # Smooth penalty factor in (0, 1]; more effective noise -> smaller factor
            noise_penalty = 1.0 - NOISE_PENALTY_STRENGTH * effective_noise
        else:
            noise_penalty = 1.0
    else:
        noise_penalty = 1.0

    directional_score = coverage * noise_penalty
    # Safety clamp to [0, 1]
    return max(0.0, min(1.0, directional_score))


def best_match(ref: str, candidates: Iterable[str], threshold: float = None):
    """
    Find the best matching candidate for a reference string.

    Args:
        ref: Reference string to match against
        candidates: Iterable of candidate strings
        threshold: Minimum similarity threshold (0-1), defaults to SIM_THRESHOLD

    Returns:
        Tuple of (best_match, score) or (None, None) if no match above threshold.

    The score is guaranteed to be in [0.0, 1.0] and is symmetric:
      score(ref, cand) ≈ score(cand, ref)
    """
    if threshold is None:
        threshold = SIM_THRESHOLD

    # Materialize the candidates once so we can compute document frequencies
    # and apply a cheap pre-filter. For many reference rows with the same
    # candidate set, this step will be relatively lightweight.
    candidates_list = list(candidates or [])
    if not candidates_list:
        return None, None

    ref_tokens = tokenize(ref)
    if not ref_tokens:
        return None, None

    # Pre-tokenize all candidates
    tokenized_candidates: List[Tuple[str, List[str]]] = [
        (cand, tokenize(cand)) for cand in candidates_list
    ]

    # Cheap pre-filter: keep only candidates that either share tokens with the
    # reference or have a strong prefix similarity on the first token. This
    # drastically reduces how many candidates go through the expensive fuzzy
    # scoring without sacrificing recall for realistic data.
    ref_token_set = set(ref_tokens)

    def _first_token_prefix_ratio(src_tokens: Sequence[str], tgt_tokens: Sequence[str]) -> float:
        if not src_tokens or not tgt_tokens:
            return 0.0
        a = src_tokens[0]
        b = tgt_tokens[0]
        if not a or not b:
            return 0.0
        max_len = max(len(a), len(b))
        if max_len == 0:
            return 0.0
        common = 0
        for ca, cb in zip(a, b):
            if ca != cb:
                break
            common += 1
        return common / max_len

    scored_candidates: List[Tuple[float, str, List[str]]] = []
    for cand_text, cand_tokens in tokenized_candidates:
        cand_set = set(cand_tokens)
        overlap = len(ref_token_set & cand_set) / len(ref_token_set) if ref_token_set else 0.0
        prefix_ratio = _first_token_prefix_ratio(ref_tokens, cand_tokens)

        if overlap > 0.0 or prefix_ratio >= 0.6:
            cheap_score = max(overlap, prefix_ratio)
            scored_candidates.append((cheap_score, cand_text, cand_tokens))

    if scored_candidates:
        scored_candidates.sort(key=lambda x: x[0], reverse=True)
        limited_candidates: List[Tuple[str, List[str]]] = [
            (text, tokens) for _, text, tokens in scored_candidates[:MAX_HEAVY_CANDIDATES]
        ]
    else:
        # Fallback: if everything was filtered out (e.g. very noisy data),
        # still limit expensive scoring to the first K candidates deterministically.
        limited_candidates = tokenized_candidates[:MAX_HEAVY_CANDIDATES]

    # Document frequencies are computed only from the (possibly reduced)
    # candidate side, as requested.
    df_map, doc_count = _compute_document_frequencies(
        [tokens for _, tokens in limited_candidates]
    )

    best_score = 0.0
    best_candidate = None

    for cand_text, cand_tokens in limited_candidates:
        if not cand_tokens:
            continue

        # Directional similarities
        score_ref_to_cand = _directional_similarity(
            ref_tokens, cand_tokens, df_map, doc_count
        )
        score_cand_to_ref = _directional_similarity(
            cand_tokens, ref_tokens, df_map, doc_count
        )
        # Make similarity symmetric and coverage-aware. We compute both
        # directions:
        #   - ref -> cand : how well the reference is covered by the candidate
        #   - cand -> ref : how well the candidate is covered by the reference
        #
        # For very short candidates that fit inside a long reference, we want
        # a high score when the short side is well covered, without overly
        # penalizing the unmatched tail of the longer string.
        min_len = min(len(ref_tokens), len(cand_tokens))
        max_len = max(len(ref_tokens), len(cand_tokens))
        length_ratio = min_len / max_len if max_len > 0 else 1.0

        # Emphasize the better-covered (typically shorter) direction.
        short_side_score = max(score_ref_to_cand, score_cand_to_ref)
        long_side_score = min(score_ref_to_cand, score_cand_to_ref)

        # Weight for the shorter side is in [0.85, 1.0]; when strings have
        # similar length, both directions tend to be close, so this remains
        # effectively symmetric while still being robust for short candidates.
        alpha = 0.85 + 0.15 * length_ratio
        beta = 1.0 - alpha

        score = alpha * short_side_score + beta * long_side_score

        # Normalization safety (should already be true)
        score = max(0.0, min(1.0, score))

        if score > best_score:
            best_score = score
            best_candidate = cand_text

    if best_score < threshold or best_candidate is None:
        return None, None

    return best_candidate, round(best_score, 4)
