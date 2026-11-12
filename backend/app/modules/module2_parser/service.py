import ast
import os


def parse_python_file(file_path: str) -> list[dict]:
    """Parse one .py file and extract its functions, classes, and imports."""
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            source = f.read()
        tree = ast.parse(source, filename=file_path)
    except (SyntaxError, OSError, UnicodeDecodeError):
        return []

    symbols = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
            symbols.append({
                "symbol_type": "function",
                "name": node.name,
                "lineno": node.lineno,
                "docstring": ast.get_docstring(node),
            })
        elif isinstance(node, ast.ClassDef):
            symbols.append({
                "symbol_type": "class",
                "name": node.name,
                "lineno": node.lineno,
                "docstring": ast.get_docstring(node),
            })
        elif isinstance(node, ast.Import):
            for alias in node.names:
                symbols.append({
                    "symbol_type": "import",
                    "name": alias.name,
                    "lineno": node.lineno,
                    "docstring": None,
                })
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for alias in node.names:
                symbols.append({
                    "symbol_type": "import",
                    "name": f"{module}.{alias.name}" if module else alias.name,
                    "lineno": node.lineno,
                    "docstring": None,
                })
    return symbols


def parse_repo_files(local_repo_path: str, file_records: list[dict]) -> dict[str, list[dict]]:
    """
    Parse every Python file recorded for a repo.
    file_records: list of {"id", "relative_path", "extension", ...} (from Module 1's RepoFile rows)
    Returns {repo_file_id: [symbols...]}
    """
    results = {}
    for rec in file_records:
        if rec["extension"] != ".py":
            continue
        full_path = os.path.join(local_repo_path, rec["relative_path"])
        symbols = parse_python_file(full_path)
        if symbols:
            results[rec["id"]] = symbols
    return results