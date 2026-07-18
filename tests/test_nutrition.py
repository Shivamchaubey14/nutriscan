"""Consistency checks between labels.yaml, nutrition_map.yaml and the seed CSVs.

These run in CI without a database: they guarantee every vision class the model
can predict resolves to a real food row with sane macros and a usable portion.
"""

import csv
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).parent.parent
DB_DIR = ROOT / "backend" / "db"

labels: list[str] = yaml.safe_load((ROOT / "ml" / "labels.yaml").read_text(encoding="utf-8"))[
    "classes"
]
mapping: dict[str, dict[str, Any]] = yaml.safe_load(
    (DB_DIR / "nutrition_map.yaml").read_text(encoding="utf-8")
)["classes"]


def _seed_ids(name: str) -> dict[str, dict[str, str]]:
    with open(DB_DIR / "seeds" / name, encoding="utf-8") as f:
        return {r["source_id"]: r for r in csv.DictReader(f)}


seeds = {"IFCT": _seed_ids("ifct_foods.csv"), "USDA": _seed_ids("usda_foods.csv")}


def test_labels_are_frozen_and_unique() -> None:
    assert len(labels) == len(set(labels)) == 59


def test_every_label_is_mapped_and_nothing_extra() -> None:
    assert set(mapping) == set(labels)


def test_mapped_foods_exist_in_seeds() -> None:
    for label, m in mapping.items():
        assert str(m["source_id"]) in seeds[m["source"]], f"{label}: missing seed food"


def test_match_quality_valid() -> None:
    assert all(m["match"] in ("exact", "proxy") for m in mapping.values())


def test_portions_sane() -> None:
    for label, m in mapping.items():
        portions = m["portions"]
        assert portions, f"{label}: no portions"
        defaults = [p for p in portions if p.get("default")]
        assert len(defaults) == 1, f"{label}: needs exactly one default portion"
        for p in portions:
            assert 5 <= p["grams"] <= 500, f"{label}: implausible portion {p}"


def test_seed_macros_sane() -> None:
    for source, rows in seeds.items():
        for sid, r in rows.items():
            energy = float(r["energy_kcal"])
            assert 0 <= energy <= 900, f"{source}:{sid} energy {energy}"
            for key in ("protein_g", "fat_g", "carb_g", "fiber_g"):
                # 101: IFCT sugars round to just over 100 g/100 g
                assert 0 <= float(r[key]) <= 101, f"{source}:{sid} {key}={r[key]}"
