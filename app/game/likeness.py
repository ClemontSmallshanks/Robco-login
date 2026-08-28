"""Fallout-style likeness calculation.

Compares two words character-by-character at each position and
returns the count of exact positional matches.  Case-insensitive.
"""


def calculate_likeness(word1: str, word2: str) -> int:
    """Count characters matching at the exact same position (case-insensitive).

    Both words must be the same length; if they differ the comparison
    uses the shorter length (though callers should ensure equal length).
    """
    return sum(
        1 for a, b in zip(word1.upper(), word2.upper()) if a == b
    )
