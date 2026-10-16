"""Check cross-module imports only use api.py contracts; internals stay private."""

import ast
from pathlib import Path

MIN_MODULE_PARTS = 4


violations: list[str] = []


def check_module_imports() -> None:
    """Reject cross-module imports that bypass a module's public API."""
    for path in Path("app/modules").rglob("*.py"):
        parts = path.parts
        if len(parts) < MIN_MODULE_PARTS:
            continue
        source = parts[2]
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            module = ""
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    module = alias.name
                    if module.startswith("app.modules."):
                        target = module.split(".")[2]
                        if target != source and module.rsplit(".", 1)[-1] in {
                            "models",
                            "repository",
                            "service",
                        }:
                            violations.append(f"{path}:{node.lineno}: {module}")
                continue
            if module.startswith("app.modules."):
                bits = module.split(".")
                if (
                    len(bits) >= MIN_MODULE_PARTS
                    and bits[2] != source
                    and bits[3] in {"models", "repository", "service"}
                ):
                    violations.append(f"{path}:{node.lineno}: {module}")


def check_entrypoint_imports() -> None:
    """Reject direct entrypoint imports of module repositories and models."""
    forbidden = {"models", "repository"}
    for path in Path("app/entrypoints").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            modules: list[str] = []
            if isinstance(node, ast.ImportFrom) and node.module:
                modules.append(node.module)
            elif isinstance(node, ast.Import):
                modules.extend(alias.name for alias in node.names)
            for module in modules:
                bits = module.split(".")
                if (
                    len(bits) >= MIN_MODULE_PARTS
                    and bits[:2] == ["app", "modules"]
                    and bits[3] in forbidden
                ):
                    violations.append(f"{path}:{node.lineno}: direct internal import {module}")


check_module_imports()
check_entrypoint_imports()
if violations:
    raise SystemExit("\n".join(violations))
print("cross-module API boundary scan: ok")
