# Nutrition database

MySQL 8 schema + seed data resolving every vision class in `ml/labels.yaml` to
nutrition facts and household portions.

## Contents

- `schema.sql` — tables `food`, `nutrient`, `food_nutrient`, `vision_class`,
  `portion_unit`. Portions hang off the vision class, not the food, because two
  classes can share a proxy food with different serving sizes.
- `seeds/ifct_foods.csv` — all 542 foods from IFCT 2017 (NIN Hyderabad) with
  energy (converted kJ → kcal), protein, fat, carbs, fiber per 100 g.
- `seeds/usda_foods.csv` — the 34 USDA FNDDS 2021–2023 survey foods referenced
  by the class mapping, same macro columns.
- `nutrition_map.yaml` — the 59 vision classes → food + portions. `match: proxy`
  entries name the substitution (e.g. jalebi → funnel cake) until better data
  lands.
- `load_nutrition.py` — idempotent loader (safe to re-run; upserts).

## Loading

```powershell
$env:MYSQL_PASSWORD = "..."   # required; MYSQL_HOST/PORT/USER/DATABASE optional
uv run python backend/db/load_nutrition.py
```

## Sources

- IFCT 2017, National Institute of Nutrition, Hyderabad — via the
  [`@ifct2017/compositions`](https://www.npmjs.com/package/@ifct2017/compositions)
  machine-readable corpus.
- USDA FoodData Central, FNDDS 2021–2023 survey foods (October 2024 release).
