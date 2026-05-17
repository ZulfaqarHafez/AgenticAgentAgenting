from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
AGENTS_DIR = ROOT / "frontend" / "public" / "agents"


@pytest.mark.parametrize(
    "filename",
    [
        "hive.svg",
        "user.svg",
        "planner.svg",
        "research.svg",
        "verifier.svg",
        "executor.svg",
        "critic.svg",
    ],
)
def test_agent_artwork_assets_exist_and_are_svg(filename: str) -> None:
    file_path = AGENTS_DIR / filename
    assert file_path.exists(), f"Missing artwork asset: {filename}"
    content = file_path.read_text(encoding="utf-8")
    assert "<svg" in content
    assert "</svg>" in content
