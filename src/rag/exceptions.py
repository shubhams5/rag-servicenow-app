"""Domain errors for retrieval / search backends."""


class RetrievalError(Exception):
    """Raised when the search backend fails (distinct from empty results)."""
