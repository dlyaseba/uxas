"""
String matching algorithms for finding best matches between reference and candidate strings.
"""

import re

SIM_THRESHOLD = 0.5


def tokenize(text):
    """Tokenize text into words (alphanumeric sequences)."""
    return re.findall(r'\w+', text.lower())


def shift_weight(pos_a, pos_b, max_len):
    """Calculate positional weight based on token positions."""
    return max(0, 1 - abs(pos_a - pos_b) / max_len)


def overlap_score(a_tokens, b_tokens, len_max):
    """
    Calculate overlap score between two tokenized strings.
    
    Args:
        a_tokens: List of tokens from first string
        b_tokens: List of tokens from second string
        len_max: Maximum length for weight calculation
        
    Returns:
        Float score between 0 and 1
    """
    if not a_tokens or not b_tokens:
        return 0

    # Use dict for O(1) lookup instead of list.index() which is O(n)
    b_token_positions = {token: i for i, token in enumerate(b_tokens)}
    score = 0

    for i, token in enumerate(a_tokens):
        if token in b_token_positions:
            j = b_token_positions[token]
            score += shift_weight(i, j, len_max)

    return score / len(a_tokens)


def best_match(ref, candidates, threshold=None):
    """
    Find the best matching candidate for a reference string.
    
    Args:
        ref: Reference string to match against
        candidates: List of candidate strings
        threshold: Minimum similarity threshold (0-1), defaults to SIM_THRESHOLD
        
    Returns:
        Tuple of (best_match, score) or (None, None) if no match above threshold
    """
    if threshold is None:
        threshold = SIM_THRESHOLD
    
    if not candidates:
        return None, None
    
    ref_tokens = tokenize(ref)
    if not ref_tokens:
        return None, None
    
    len_max = len(ref_tokens)
    best_score = 0
    best_candidate = None
    
    # Pre-tokenize all candidates for better performance
    candidates_tokens = [(c, tokenize(c)) for c in candidates]
    
    for candidate, cand_tokens in candidates_tokens:
        if not cand_tokens:
            continue
        len_max_curr = max(len_max, len(cand_tokens))
        score = overlap_score(ref_tokens, cand_tokens, len_max_curr)
        if score > best_score:
            best_score = score
            best_candidate = candidate
    
    if best_score < threshold:
        return None, None

    return best_candidate, round(best_score, 4)
