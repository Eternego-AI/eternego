"""Base — the ability decorator."""


def ability(description: str, scopes: list[str], order: int = 99):
    """Mark a function as a reasoning ability with a model-facing description, allowed scopes, and sort order."""
    def decorator(fn):
        fn.ability = description
        fn.ability_order = order
        fn.ability_scopes = scopes
        return fn
    return decorator
