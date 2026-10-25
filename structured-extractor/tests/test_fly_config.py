"""Guard against deploying this archived copy over the live mcp-apps extractor (go-live MB-2)."""

import tomllib
from pathlib import Path

LIVE_APP = "mcp-bank-extractor"
FLY_TOML = Path(__file__).resolve().parents[1] / "fly.toml"


def test_fly_app_name_cannot_collide_with_the_live_extractor():
    config = tomllib.loads(FLY_TOML.read_text())
    assert config["app"] != LIVE_APP
    assert config["app"].endswith("-archived")
    assert LIVE_APP + ".fly.dev" not in config["env"]["BASE_URL"]


def test_code_defaults_do_not_point_at_the_live_extractor():
    src = Path(__file__).resolve().parents[1] / "src"
    for path in src.rglob("*.py"):
        assert f"https://{LIVE_APP}.fly.dev" not in path.read_text(), path
