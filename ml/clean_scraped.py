"""Quarantine scraped images whose content does not match their class.

Web-scraped folders contain some fraction of query-unrelated junk (screenshots,
products, animals, cars). This pass runs zero-shot CLIP over every image in
ml/data/raw/scraped/ and moves images to ml/data/quarantine/<class>/ when a
junk prompt outscores every food prompt for that class. Quarantined files are
kept (not deleted) so misfires can be reviewed and restored by hand.

Run:  uv run python ml/clean_scraped.py
"""

import shutil
from pathlib import Path

import open_clip  # type: ignore[import-untyped]
import torch
import yaml
from PIL import Image

ML_DIR = Path(__file__).parent
SCRAPED = ML_DIR / "data" / "raw" / "scraped"
QUARANTINE = ML_DIR / "data" / "quarantine"

# Human descriptions to build "a photo of ..." food prompts per class.
FOOD_PROMPTS: dict[str, str] = {
    "poha": "poha, an indian flattened rice dish",
    "kachori": "kachori, a fried indian pastry snack",
    "pani_puri": "pani puri, crispy indian street food shells",
    "dal_tadka": "dal, an indian yellow lentil curry",
    "chana_masala": "chana masala, an indian chickpea curry",
    "palak_paneer": "palak paneer, indian spinach curry with cheese cubes",
    "paneer_butter_masala": "paneer butter masala, indian cheese curry in creamy gravy",
    "aloo_gobi": "aloo gobi, indian potato and cauliflower dish",
    "bhindi_masala": "bhindi masala, indian fried okra dish",
    "butter_chicken": "butter chicken, indian chicken curry in creamy gravy",
    "chicken_biryani": "chicken biryani, indian spiced rice with chicken",
    "gulab_jamun": "gulab jamun, indian fried dough balls in syrup",
    "rasgulla": "rasgulla, white indian cheese balls in syrup",
    "gajar_halwa": "gajar halwa, indian grated carrot dessert",
    "lassi": "lassi, an indian yogurt drink in a glass",
}

JUNK_PROMPTS = [
    "a car or vehicle",
    "a cartoon, drawing or digital art",
    "a website screenshot with text",
    "a book cover or poster with text",
    "a portrait of a person",
    "a product package or gadget",
    "an animal",
    "an abstract wallpaper pattern",
]


def main() -> None:
    device = "cpu"
    model, _, preprocess = open_clip.create_model_and_transforms(
        "ViT-B-32", pretrained="laion2b_s34b_b79k", device=device
    )
    tokenizer = open_clip.get_tokenizer("ViT-B-32")

    backfill: list[str] = yaml.safe_load((ML_DIR / "labels.yaml").read_text(encoding="utf-8"))[
        "backfill"
    ]

    for cls in backfill:
        food_texts = [
            f"a photo of {FOOD_PROMPTS[cls]}",
            "a photo of indian food on a plate",
        ]
        texts = tokenizer(food_texts + JUNK_PROMPTS).to(device)
        with torch.no_grad():
            text_features = model.encode_text(texts)
            text_features /= text_features.norm(dim=-1, keepdim=True)

        src = SCRAPED / cls
        moved = kept = 0
        for f in sorted(src.glob("*.jpg")):
            try:
                with Image.open(f) as im:
                    image = preprocess(im.convert("RGB")).unsqueeze(0).to(device)
            except Exception:
                f.unlink()
                continue
            with torch.no_grad():
                feat = model.encode_image(image)
                feat /= feat.norm(dim=-1, keepdim=True)
                sims = (feat @ text_features.T).squeeze(0)
            if int(sims.argmax()) >= len(food_texts):
                dest = QUARANTINE / cls
                dest.mkdir(parents=True, exist_ok=True)
                shutil.move(str(f), dest / f.name)
                moved += 1
            else:
                kept += 1
        print(f"{cls}: kept {kept}, quarantined {moved}", flush=True)


if __name__ == "__main__":
    main()
