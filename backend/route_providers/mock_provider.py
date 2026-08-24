import json
from pathlib import Path


FIXTURE_PATH = (
    Path(__file__).parent.parent / "fixtures" / "ekispert_route_demo.json"
)


def get_route(_origin, _destination, _arrival_at):
    """デモ用の駅すぱあと形式JSONを読み込んで返す。"""
    with FIXTURE_PATH.open(encoding="utf-8") as fixture_file:
        return json.load(fixture_file)
