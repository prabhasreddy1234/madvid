"""Local project analysis for MADVID."""

from __future__ import annotations

import json
from pathlib import Path

from .models import ProductContext


def _read_json(path: Path) -> dict:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError, TypeError):
        return {}


def detect_project_type(project_root: str) -> str:
    if not project_root:
        return "web"
    root = Path(project_root)
    if (root / "build.gradle").exists() or (root / "settings.gradle").exists():
        return "android"
    if (root / "Package.swift").exists() or (root / ".xcodeproj").exists() or (root / "Podfile").exists():
        return "ios"
    if (root / "package.json").exists() or (root / "src").exists() or (root / "app").exists():
        return "web"
    return "desktop"


def infer_product_name(project_root: str) -> str:
    root = Path(project_root)
    package = _read_json(root / "package.json")
    if package.get("name"):
        return str(package["name"]).replace("-", " ").title()
    if (root / "build.gradle").exists():
        text = (root / "build.gradle").read_text(encoding="utf-8", errors="ignore")
        for line in text.splitlines():
            if "applicationId" in line or "namespace" in line:
                return line.split("=")[-1].strip().strip('"\'')
    if (root / "README.md").exists():
        text = (root / "README.md").read_text(encoding="utf-8", errors="ignore")
        first_heading = next((line.strip("# ") for line in text.splitlines() if line.startswith("# ")), None)
        if first_heading:
            return first_heading
    return "Project Product"


def analyze_project(project_root: str = ".") -> ProductContext:
    root = Path(project_root)
    project_type = detect_project_type(str(root))
    product_name = infer_product_name(str(root))
    features = [
        "Primary workflow",
        "Key user actions",
        "Shared product insights",
    ]
    readme_path = root / "README.md"
    readme_text = readme_path.read_text(encoding="utf-8", errors="ignore") if readme_path.exists() else ""
    for line in readme_text.splitlines():
        if line.startswith("- ") and len(line) > 3:
            features.append(line[2:].strip())
            if len(features) >= 5:
                break
    important_screens = [
        "Landing experience",
        "Core workflow",
        "Result and summary",
    ]
    if project_type == "android":
        important_screens = ["Home screen", "Main workflow", "Profile or account"]
    elif project_type == "ios":
        important_screens = ["App home", "Detail flow", "Result view"]

    return ProductContext(
        product_name=product_name,
        product_category=project_type.title() + " app",
        target_user="Product users",
        value_proposition="Simplify workflows and help users get results faster.",
        primary_workflow="Core user journey",
        features=features[:5],
        visual_identity="Clean, modern product experience",
        important_screens=important_screens,
        cta="Explore the product",
        source_type="PROJECT",
        metadata={"project_type": project_type, "project_root": str(root)},
    )
