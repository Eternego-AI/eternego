"""Transcripts — conversation transcript formatting and extraction."""


def as_list(text: str) -> list[dict]:
    """Parse a numbered transcript into a list of entries with index and content."""
    entries = []
    for line in text.splitlines():
        if line.startswith("["):
            try:
                bracket_end = line.index("]")
                entries.append({
                    "index": int(line[1:bracket_end]),
                    "content": line[bracket_end + 2:],
                })
            except (ValueError, IndexError):
                continue
    return entries


def extract(text: str, indices: list[int]) -> str:
    """Extract entries from a numbered transcript by their indices."""
    index_set = set(indices)
    lines = []
    for line in text.splitlines():
        if not line.startswith("["):
            continue
        try:
            bracket_end = line.index("]")
            if int(line[1:bracket_end]) in index_set:
                lines.append(line[bracket_end + 2:])
        except (ValueError, IndexError):
            continue
    return "\n".join(lines)
