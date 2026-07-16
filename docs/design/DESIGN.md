# NutriScan — Design Reference

The three PNG screen-card sheets in this folder are the **canonical design**. They supersede
the color palette in SRS §8.2 (the blue palette is dropped in favor of this warm
sage-green & cream system). Typography, spacing, radii, and component rules from SRS §8
still apply unless the screens show otherwise.

## Screens (v1)

| # | Screen | Notes |
|---|---|---|
| 01 | Splash | Sage background, logo mark, "Point. Scan. Know." |
| 02 | Login | Phone/email + OTP, Google/Apple OAuth, guest mode (7-day local history) |
| 03 | OTP | 4-digit code entry, resend timer |
| 04 | Home | Greeting, calorie ring (consumed vs goal) with protein/carbs/fat bars, today's meals, "Scan your next meal" CTA |
| 05 | Scan | Dark-olive camera view, Food / Barcode / Label mode toggle, framing corners |
| 06 | Scan result | Bottom sheet: detected items, kcal range, macros, confidence chip, data-source badge, portion slider (household units), meal picker (Breakfast/Lunch/Dinner/Snack), total range, "Log to Breakfast" |
| 07 | Low-confidence confirm | "Not quite sure — is this…" top-3 candidates with confidence bars, manual-search fallback (FR-3) |
| 08 | History | Weekly bar chart (within goal = sage, over goal = tan), grouped daily entries with kcal + delete |
| 09 | Plan | Per-meal calorie budget (breakfast/lunch/snacks/dinner %), dinner ideas fitting remaining budget |
| 10 | Food detail | Scanned photo, kcal range, macro chips, data source (IFCT/USDA), "Was this identification right?" feedback (FR-15) |
| 11 | Profile | Avatar card, daily calorie goal stepper, portion units (Household/Grams), dark mode, training-data consent toggle (NFR-5) |

## Navigation

Bottom bar with **5 slots**: Home · History · **Scan (center FAB, sage circle)** · Plan · Profile.
(This adds a Plan tab over the 4-tab layout in SRS §8.5.)

## Palette (approximate hex, sampled from the screen cards)

The PNGs are the source of truth — treat these values as a starting point and refine when
building the mobile theme file.

| Token | Approx. | Used for |
|---|---|---|
| Sage / Primary | `#8A9B7D` | Primary buttons, FAB, progress ring, "within goal" bars, high-confidence chip |
| Sage light | `#AEBB9C` | Splash background, secondary fills |
| Olive dark | `#3B4433` | Camera screen background, dark surfaces |
| Cream / Background | `#F4EEE1` | Page background |
| Card | `#FFFDF6` | Cards, sheets, inputs (warm white) |
| Heading text | `#35392E` | Titles, primary text |
| Body text | `#6B6A5E` | Secondary text |
| Caption / Muted | `#A8A395` | Captions, placeholders, inactive icons |
| Tan / Accent | `#C9A16B` | "Over goal" bars, medium-confidence chip, warnings |
| Border | `#E8E1D2` | Card borders, dividers |
| Error / Low confidence | `#C97B5D` | Failed states, low-confidence chip (muted terracotta) |

## Semantic mapping

- Confidence: **High** = sage, **Medium** = tan, **Low** = terracotta.
- Calorie progress ring: sage; over-goal segments: tan.
- Meal-type badges (B/L/D/S) use tinted sage/tan circles on cards.
- Nutrition is always a **range** (e.g. "180–230 kcal") with a confidence chip — never an
  exact value (SRS §2.4).

## Keep from SRS §8

- Inter typeface and the type scale (§8.1).
- Spacing tokens XS 4 … Section 48 (§8.7).
- Radii: chips 12 / buttons 16 / cards 20 / bottom sheet 28 / search 18 / inputs 16 (§8.7).
- Shadow levels (§8.7), WCAG AA contrast (NFR-7).
