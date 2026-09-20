def summarize_decisions(notes: str) -> list[str]:
    lines = []

    for line in notes.splitlines():
        stripped = line.strip()
        lower = stripped.lower()

        if any(keyword in lower for keyword in ['decided', 'decision', 'we choose', 'chosen', 'selected']):
            lines.append(stripped)

    return lines


def compact_notes(notes: str, max_chars: int = 3000) -> str:
    cleaned = '\n'.join(line.strip() for line in notes.splitlines() if line.strip())
    return cleaned[:max_chars]
