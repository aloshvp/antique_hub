"""
Comment sanitization, length validation, and profanity filtering utilities for Antique Hub.
Module 9 - Comments.
"""

import re
from django.utils.html import strip_tags
from orders.models import Purchase


MAX_COMMENT_LENGTH = 1000
MIN_COMMENT_LENGTH = 3

# Standard prohibited/profane words list for demo sandbox moderation
PROFANITY_WORDS = [
    'abuse', 'abusive', 'scam', 'fraudster', 'bastard', 'asshole', 'bitch',
    'bullshit', 'shit', 'fuck', 'fucking', 'damn', 'crap', 'idiot',
    'moron', 'cheat', 'counterfeit', 'swindler', 'douche',
]

# Compile regex with word boundaries for fast matching
PROFANITY_REGEX = re.compile(
    r'\b(' + '|'.join(re.escape(w) for w in PROFANITY_WORDS) + r')\b',
    re.IGNORECASE
)


def mask_profanity_match(match) -> str:
    """
    Masks a matched profane word, keeping only the first letter.
    e.g. 'idiot' -> 'i****'
    """
    word = match.group(0)
    if len(word) <= 2:
        return '*' * len(word)
    return word[0] + '*' * (len(word) - 1)


def sanitize_comment_text(raw_text: str) -> tuple[str, bool, str]:
    """
    Sanitizes, checks length, and filters profanity from comment text.
    Returns:
        (clean_text, is_flagged, error_message)
    """
    if not raw_text:
        return "", False, "Commentary text cannot be blank."

    # 1. Strip HTML tags to prevent XSS injection
    sanitized = strip_tags(raw_text).strip()

    # 2. Length limits
    if len(sanitized) < MIN_COMMENT_LENGTH:
        return "", False, f"Commentary is too short (minimum {MIN_COMMENT_LENGTH} characters required)."

    if len(sanitized) > MAX_COMMENT_LENGTH:
        return "", False, f"Commentary exceeds the maximum allowed limit of {MAX_COMMENT_LENGTH} characters (currently {len(sanitized)})."

    # 3. Profanity scanning and masking
    flagged = bool(PROFANITY_REGEX.search(sanitized))
    clean_text = PROFANITY_REGEX.sub(mask_profanity_match, sanitized)

    return clean_text, flagged, None


def has_user_purchased_item(user, item) -> bool:
    """
    Checks if an authenticated user has purchased this antique item
    in an order marked as 'Paid' (DFD 1.3/DFD 1.4 verification).
    """
    if not user or not user.is_authenticated:
        return False

    return Purchase.objects.filter(
        purchase_master__buyer=user,
        purchase_master__pay_status='Paid',
        item=item
    ).exists()
