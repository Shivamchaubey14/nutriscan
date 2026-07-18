-- NutriScan nutrition schema (MySQL 8).
-- Seeded by load_nutrition.py from backend/db/seeds/ + backend/db/nutrition_map.yaml.
-- vision_class/portion_unit hang portions off the *class* (not the food) because two
-- classes may share a proxy food (e.g. dhokla -> Idli) with different serving sizes.

CREATE TABLE IF NOT EXISTS food (
    id INT UNSIGNED NOT NULL AUTO_INCREMENT,
    source ENUM ('IFCT', 'USDA') NOT NULL,
    source_id VARCHAR(16) NOT NULL,
    name VARCHAR(255) NOT NULL,
    food_group VARCHAR(64) NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_food_source (source, source_id)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4;

CREATE TABLE IF NOT EXISTS nutrient (
    id INT UNSIGNED NOT NULL AUTO_INCREMENT,
    key_name VARCHAR(32) NOT NULL,
    display_name VARCHAR(64) NOT NULL,
    unit VARCHAR(8) NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_nutrient_key (key_name)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4;

CREATE TABLE IF NOT EXISTS food_nutrient (
    food_id INT UNSIGNED NOT NULL,
    nutrient_id INT UNSIGNED NOT NULL,
    amount_per_100g DECIMAL(8, 2) NOT NULL,
    PRIMARY KEY (food_id, nutrient_id),
    CONSTRAINT fk_fn_food FOREIGN KEY (food_id) REFERENCES food (id) ON DELETE CASCADE,
    CONSTRAINT fk_fn_nutrient FOREIGN KEY (nutrient_id) REFERENCES nutrient (id)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4;

CREATE TABLE IF NOT EXISTS vision_class (
    id INT UNSIGNED NOT NULL AUTO_INCREMENT,
    label VARCHAR(64) NOT NULL,
    food_id INT UNSIGNED NOT NULL,
    match_quality ENUM ('exact', 'proxy') NOT NULL DEFAULT 'exact',
    note VARCHAR(255) NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_vision_class_label (label),
    CONSTRAINT fk_vc_food FOREIGN KEY (food_id) REFERENCES food (id)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4;

CREATE TABLE IF NOT EXISTS portion_unit (
    id INT UNSIGNED NOT NULL AUTO_INCREMENT,
    vision_class_id INT UNSIGNED NOT NULL,
    unit VARCHAR(32) NOT NULL,
    grams DECIMAL(7, 1) NOT NULL,
    is_default TINYINT (1) NOT NULL DEFAULT 0,
    PRIMARY KEY (id),
    UNIQUE KEY uq_portion (vision_class_id, unit),
    CONSTRAINT fk_pu_class FOREIGN KEY (vision_class_id) REFERENCES vision_class (id) ON DELETE CASCADE
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4;
