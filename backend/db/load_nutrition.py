"""Seed the NutriScan nutrition database (MySQL 8).

Creates the schema from schema.sql, then loads IFCT 2017 + USDA FNDDS foods with
their macros from seeds/, and the vision-class mapping with household portions
from nutrition_map.yaml.

Connection comes from env vars: MYSQL_HOST (localhost), MYSQL_PORT (3306),
MYSQL_USER (root), MYSQL_PASSWORD (required), MYSQL_DATABASE (nutriscan).

Run:  uv run python backend/db/load_nutrition.py
"""

import csv
import os
import sys
from pathlib import Path
from typing import Any

import pymysql
import yaml

DB_DIR = Path(__file__).parent
NUTRIENTS = [
    ("energy_kcal", "Energy", "kcal"),
    ("protein_g", "Protein", "g"),
    ("fat_g", "Total fat", "g"),
    ("carb_g", "Carbohydrate", "g"),
    ("fiber_g", "Dietary fiber", "g"),
]


def connect() -> pymysql.connections.Connection:
    password = os.environ.get("MYSQL_PASSWORD")
    if not password:
        sys.exit("MYSQL_PASSWORD is not set — refusing to guess credentials.")
    return pymysql.connect(
        host=os.environ.get("MYSQL_HOST", "localhost"),
        port=int(os.environ.get("MYSQL_PORT", "3306")),
        user=os.environ.get("MYSQL_USER", "root"),
        password=password,
        charset="utf8mb4",
        autocommit=False,
    )


def load_seed_foods(source: str, csv_name: str) -> list[dict[str, str]]:
    with open(DB_DIR / "seeds" / csv_name, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["source"] = source
    return rows


def main() -> None:
    database = os.environ.get("MYSQL_DATABASE", "nutriscan")
    foods = load_seed_foods("IFCT", "ifct_foods.csv") + load_seed_foods("USDA", "usda_foods.csv")
    mapping: dict[str, Any] = yaml.safe_load(
        (DB_DIR / "nutrition_map.yaml").read_text(encoding="utf-8")
    )["classes"]

    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"CREATE DATABASE IF NOT EXISTS `{database}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci"
            )
            cur.execute(f"USE `{database}`")
            for stmt in (DB_DIR / "schema.sql").read_text(encoding="utf-8").split(";"):
                if stmt.strip():
                    cur.execute(stmt)

            cur.executemany(
                "INSERT INTO nutrient (key_name, display_name, unit) VALUES (%s, %s, %s) "
                "ON DUPLICATE KEY UPDATE display_name = VALUES(display_name)",
                NUTRIENTS,
            )
            cur.execute("SELECT key_name, id FROM nutrient")
            nutrient_ids = dict(cur.fetchall())

            cur.executemany(
                "INSERT INTO food (source, source_id, name, food_group) "
                "VALUES (%s, %s, %s, %s) "
                "ON DUPLICATE KEY UPDATE name = VALUES(name), food_group = VALUES(food_group)",
                [(f["source"], f["source_id"], f["name"], f["food_group"]) for f in foods],
            )
            cur.execute("SELECT source, source_id, id FROM food")
            food_ids = {(src, sid): fid for src, sid, fid in cur.fetchall()}

            fn_rows = [
                (food_ids[(f["source"], f["source_id"])], nutrient_ids[key], f[key])
                for f in foods
                for key, _, _ in NUTRIENTS
                if f[key] != ""
            ]
            cur.executemany(
                "INSERT INTO food_nutrient (food_id, nutrient_id, amount_per_100g) "
                "VALUES (%s, %s, %s) "
                "ON DUPLICATE KEY UPDATE amount_per_100g = VALUES(amount_per_100g)",
                fn_rows,
            )

            for label, m in mapping.items():
                food_id = food_ids[(m["source"], str(m["source_id"]))]
                cur.execute(
                    "INSERT INTO vision_class (label, food_id, match_quality, note) "
                    "VALUES (%s, %s, %s, %s) "
                    "ON DUPLICATE KEY UPDATE food_id = VALUES(food_id), "
                    "match_quality = VALUES(match_quality), note = VALUES(note)",
                    (label, food_id, m["match"], m.get("note")),
                )
                cur.execute("SELECT id FROM vision_class WHERE label = %s", (label,))
                row = cur.fetchone()
                assert row is not None
                class_id = row[0]
                cur.executemany(
                    "INSERT INTO portion_unit (vision_class_id, unit, grams, is_default) "
                    "VALUES (%s, %s, %s, %s) "
                    "ON DUPLICATE KEY UPDATE grams = VALUES(grams), "
                    "is_default = VALUES(is_default)",
                    [
                        (class_id, p["unit"], p["grams"], int(bool(p.get("default"))))
                        for p in m["portions"]
                    ],
                )

        conn.commit()
        with conn.cursor() as cur:
            for table in ("food", "nutrient", "food_nutrient", "vision_class", "portion_unit"):
                cur.execute(f"SELECT COUNT(*) FROM {table}")  # noqa: S608 - fixed names
                row = cur.fetchone()
                assert row is not None
                print(f"{table}: {row[0]} rows")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
