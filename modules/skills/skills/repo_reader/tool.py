from pathlib import Path


IGNORED_DIRS = {
    '.git',
    '.venv',
    'venv',
    '__pycache__',
    'node_modules',
    'dist',
    'build',
    '.mypy_cache',
    '.pytest_cache',
}


def build_tree(root: str, max_depth: int = 3) -> str:
    root_path = Path(root).resolve()
    lines = [str(root_path)]

    def walk(path: Path, depth: int) -> None:
        if depth > max_depth:
            return

        for child in sorted(path.iterdir(), key=lambda p: (p.is_file(), p.name.lower())):
            if child.name in IGNORED_DIRS:
                continue

            indent = '  ' * depth
            marker = '├── '
            lines.append(f'{indent}{marker}{child.name}')

            if child.is_dir():
                walk(child, depth + 1)

    walk(root_path, 1)
    return '\n'.join(lines)


def read_text_file(path: str, max_chars: int = 12000) -> str:
    file_path = Path(path).resolve()

    if not file_path.exists():
        return f'File not found: {file_path}'

    if not file_path.is_file():
        return f'Not a file: {file_path}'

    text = file_path.read_text(encoding='utf-8', errors='replace')
    return text[:max_chars]
