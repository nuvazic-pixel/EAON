import re


def extract_error_lines(log_text: str) -> list[str]:
    patterns = [
        'error',
        'exception',
        'traceback',
        'failed',
        'not found',
        'attribute',
        'import',
    ]

    lines = []
    for line in log_text.splitlines():
        lower = line.lower()
        if any(pattern in lower for pattern in patterns):
            lines.append(line)

    return lines


def detect_python_missing_attribute(log_text: str) -> str | None:
    match = re.search(r'Attribute "([^"]+)" not found in module "([^"]+)"', log_text)
    if not match:
        return None

    attr, module = match.groups()
    return f'Module {module} exists, but it does not expose expected attribute: {attr}'
