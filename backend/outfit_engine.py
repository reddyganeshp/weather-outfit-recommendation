"""
Outfit Recommendation Engine
Core business logic: maps weather + occasion → outfit suggestion
"""

from __future__ import annotations
import random
from dataclasses import dataclass, field, asdict
from typing import Optional


# ─────────────────────────────────────────────
#  Data classes
# ─────────────────────────────────────────────

@dataclass
class OutfitItem:
    category: str       # e.g. "top", "bottom", "outerwear"
    name: str
    description: str
    color_options: list[str]
    weather_tags: list[str]
    occasion_tags: list[str]
    gender_tags: list[str]   # ["male","female","unisex"]


@dataclass
class Recommendation:
    outfit_name: str
    items: list[dict]
    accessories: list[str]
    tips: list[str]
    comfort_score: float    # 0-10
    style_notes: str
    color_palette: list[str]


# ─────────────────────────────────────────────
#  Outfit catalogue (static knowledge base)
# ─────────────────────────────────────────────

OUTFIT_CATALOGUE: list[OutfitItem] = [
    # ── Tops ──
    OutfitItem("top", "Lightweight Linen Shirt",
               "Breathable and stylish for warm days",
               ["white", "beige", "light blue", "sage"],
               ["sunny", "hot"], ["casual", "outdoor"], ["male","unisex"]),
    OutfitItem("top", "Fitted T-Shirt",
               "Classic everyday top for mild weather",
               ["white", "black", "grey", "navy"],
               ["sunny", "cloudy"], ["casual", "sport"], ["unisex"]),
    OutfitItem("top", "Long-Sleeve Thermal Top",
               "Warm base layer for cold conditions",
               ["white", "charcoal", "dark blue"],
               ["snowy", "cold", "windy"], ["casual", "outdoor"], ["unisex"]),
    OutfitItem("top", "Silk Blouse",
               "Elegant blouse for professional settings",
               ["cream", "dusty rose", "slate blue", "white"],
               ["cloudy", "mild"], ["work", "formal"], ["female","unisex"]),
    OutfitItem("top", "Oxford Button-Down",
               "Smart casual shirt for work or going out",
               ["white", "light blue", "pale pink", "striped"],
               ["cloudy", "mild"], ["work", "formal", "casual"], ["male","unisex"]),
    OutfitItem("top", "Moisture-Wicking Sports Top",
               "Performance top for active days",
               ["black", "electric blue", "neon green"],
               ["sunny", "cloudy"], ["sport"], ["unisex"]),
    OutfitItem("top", "Chunky Knit Sweater",
               "Cosy oversized knit for cold weather",
               ["camel", "cream", "burgundy", "forest green"],
               ["snowy", "rainy", "cold", "cloudy"], ["casual"], ["unisex"]),
    OutfitItem("top", "Waterproof Jacket",
               "Essential outer layer for rainy days",
               ["navy", "olive", "red", "black"],
               ["rainy", "windy"], ["casual", "outdoor", "work"], ["unisex"]),

    # ── Bottoms ──
    OutfitItem("bottom", "Chino Trousers",
               "Versatile smart-casual trousers",
               ["khaki", "navy", "olive", "stone"],
               ["sunny", "cloudy", "mild"], ["casual", "work"], ["male","unisex"]),
    OutfitItem("bottom", "Tailored Suit Trousers",
               "Sharp formal trousers for professional occasions",
               ["charcoal", "navy", "black", "mid-grey"],
               ["cloudy", "mild"], ["formal", "work"], ["unisex"]),
    OutfitItem("bottom", "Slim-Fit Jeans",
               "Classic denim for everyday wear",
               ["indigo", "dark wash", "light wash", "black"],
               ["cloudy", "mild", "windy"], ["casual"], ["unisex"]),
    OutfitItem("bottom", "Linen Wide-Leg Trousers",
               "Relaxed summer trousers with elegant drape",
               ["white", "beige", "terracotta", "sage"],
               ["sunny", "hot"], ["casual", "outdoor"], ["female","unisex"]),
    OutfitItem("bottom", "Insulated Ski Pants",
               "Waterproof and warm for snowy conditions",
               ["black", "charcoal", "electric blue"],
               ["snowy", "cold"], ["outdoor", "sport"], ["unisex"]),
    OutfitItem("bottom", "Joggers / Track Pants",
               "Comfortable sporty bottoms",
               ["grey", "black", "navy"],
               ["cloudy", "rainy", "cold"], ["sport", "casual"], ["unisex"]),
    OutfitItem("bottom", "Flowy Midi Skirt",
               "Elegant and comfortable for warm to mild days",
               ["floral", "terracotta", "forest green", "cream"],
               ["sunny", "mild"], ["casual", "work"], ["female"]),
    OutfitItem("bottom", "Shorts",
               "Lightweight shorts for hot sunny days",
               ["white", "navy", "khaki", "pastel"],
               ["sunny", "hot"], ["casual", "sport", "outdoor"], ["unisex"]),

    # ── Outerwear ──
    OutfitItem("outerwear", "Trench Coat",
               "Timeless coat that repels light rain",
               ["camel", "beige", "black", "navy"],
               ["rainy", "cloudy", "windy"], ["work", "formal", "casual"], ["unisex"]),
    OutfitItem("outerwear", "Puffer Jacket",
               "Insulated jacket for very cold days",
               ["black", "olive", "navy", "burnt orange"],
               ["snowy", "cold"], ["casual", "outdoor"], ["unisex"]),
    OutfitItem("outerwear", "Denim Jacket",
               "Light layering piece for mild or breezy days",
               ["classic blue", "black", "light wash"],
               ["cloudy", "windy", "mild"], ["casual"], ["unisex"]),
    OutfitItem("outerwear", "Blazer",
               "Smart layer that elevates any outfit",
               ["charcoal", "navy", "beige", "black"],
               ["cloudy", "mild"], ["work", "formal"], ["unisex"]),

    # ── Footwear ──
    OutfitItem("footwear", "White Leather Trainers",
               "Clean versatile sneakers for everyday use",
               ["white", "white/grey"],
               ["sunny", "cloudy", "mild"], ["casual"], ["unisex"]),
    OutfitItem("footwear", "Chelsea Boots",
               "Sleek ankle boots for wet or cold days",
               ["black", "tan", "dark brown"],
               ["rainy", "cloudy", "windy", "cold"], ["casual", "work"], ["unisex"]),
    OutfitItem("footwear", "Running Shoes",
               "Cushioned shoes for sport and active outings",
               ["black/white", "grey/neon", "navy/red"],
               ["sunny", "cloudy"], ["sport", "outdoor"], ["unisex"]),
    OutfitItem("footwear", "Leather Oxford Shoes",
               "Classic formal footwear",
               ["black", "dark brown", "tan"],
               ["cloudy", "mild"], ["formal", "work"], ["unisex"]),
    OutfitItem("footwear", "Waterproof Hiking Boots",
               "Sturdy grip for outdoor adventures",
               ["brown", "tan", "olive/black"],
               ["rainy", "snowy", "windy", "cold"], ["outdoor"], ["unisex"]),
    OutfitItem("footwear", "Strappy Sandals",
               "Open footwear for hot sunny days",
               ["tan", "black", "white", "gold"],
               ["sunny", "hot"], ["casual", "outdoor"], ["female","unisex"]),
]


# ─────────────────────────────────────────────
#  Temperature bands
# ─────────────────────────────────────────────

def _temp_band(temp: float) -> str:
    if temp >= 28:   return "hot"
    if temp >= 20:   return "warm"
    if temp >= 12:   return "mild"
    if temp >= 4:    return "cold"
    return "freezing"


def _comfort_score(temp: float, humidity: float, wind: float) -> float:
    """Simple heat-index-inspired comfort score (0–10, higher = more comfortable)."""
    score = 10.0
    # Penalise extremes
    if temp > 32 or temp < 0:
        score -= 3
    elif temp > 28 or temp < 5:
        score -= 1.5
    # Penalise high humidity in heat
    if temp > 22 and humidity > 75:
        score -= 2
    # Penalise wind chill
    if wind > 40:
        score -= 2
    elif wind > 20:
        score -= 1
    return max(0.0, min(10.0, round(score, 1)))


# ─────────────────────────────────────────────
#  Engine class
# ─────────────────────────────────────────────

class OutfitEngine:

    def recommend(
        self,
        temperature: float,
        weather_condition: str,
        humidity: float = 50,
        wind_speed: float = 0,
        occasion: str = "casual",
        gender: str = "unisex",
        preferred_colors: list[str] | None = None
    ) -> dict:

        band = _temp_band(temperature)
        weather = weather_condition.lower()
        occ = occasion.lower()
        gen = gender.lower()

        # Effective weather tags to match against catalogue
        weather_tags = {weather, band}
        if band in ("cold", "freezing"):
            weather_tags.add("cold")
        if band in ("hot", "warm"):
            weather_tags.add("hot")

        def _matches(item: OutfitItem) -> bool:
            w_ok = bool(set(item.weather_tags) & weather_tags)
            o_ok = occ in item.occasion_tags or "casual" in item.occasion_tags
            g_ok = gen in item.gender_tags or "unisex" in item.gender_tags
            return w_ok and o_ok and g_ok

        matched = [i for i in OUTFIT_CATALOGUE if _matches(i)]

        # Select one item per category
        categories = ["top", "bottom", "outerwear", "footwear"]
        chosen: list[dict] = []
        for cat in categories:
            pool = [i for i in matched if i.category == cat]
            if not pool:
                # Fall back to any item in that category
                pool = [i for i in OUTFIT_CATALOGUE if i.category == cat]
            if pool:
                item = random.choice(pool)
                # Pick color (prefer user's preferences)
                if preferred_colors:
                    color = next(
                        (c for c in preferred_colors
                         if any(c.lower() in opt.lower() for opt in item.color_options)),
                        random.choice(item.color_options)
                    )
                else:
                    color = random.choice(item.color_options)

                chosen.append({
                    "category": item.category,
                    "name": item.name,
                    "description": item.description,
                    "chosen_color": color,
                    "all_colors": item.color_options
                })

        # Skip outerwear when it's hot
        if band == "hot" and weather not in ("windy", "rainy"):
            chosen = [c for c in chosen if c["category"] != "outerwear"]

        # Accessories
        accessories = self._accessories(weather, band, occ)

        # Style tips
        tips = self._tips(temperature, weather, humidity, wind_speed, band, occ)

        # Outfit name
        outfit_name = self._outfit_name(band, weather, occ)

        # Color palette
        palette = list({c["chosen_color"] for c in chosen})

        return {
            "outfit_name": outfit_name,
            "items": chosen,
            "accessories": accessories,
            "tips": tips,
            "comfort_score": _comfort_score(temperature, humidity, wind_speed),
            "style_notes": self._style_notes(band, occ),
            "color_palette": palette
        }

    # ── helpers ──

    def _accessories(self, weather: str, band: str, occasion: str) -> list[str]:
        acc: list[str] = []
        if weather == "rainy":
            acc += ["Compact umbrella", "Waterproof bag"]
        if weather == "sunny" and band in ("hot", "warm"):
            acc += ["Sunglasses", "SPF lip balm", "Light tote bag"]
        if band in ("cold", "freezing"):
            acc += ["Wool scarf", "Insulated gloves", "Knit beanie"]
        if weather == "windy":
            acc.append("Windproof hat or ear muffs")
        if occasion == "formal":
            acc += ["Classic watch", "Leather belt"]
        elif occasion == "work":
            acc.append("Structured tote or briefcase")
        elif occasion == "sport":
            acc += ["Sports water bottle", "Fitness tracker"]
        if not acc:
            acc.append("Minimal jewellery or a casual watch")
        return acc

    def _tips(self, temp, weather, humidity, wind, band, occasion) -> list[str]:
        tips: list[str] = []
        if band == "hot":
            tips.append("Choose natural fabrics like cotton or linen to stay cool.")
        if band in ("cold", "freezing"):
            tips.append("Layer up — trapping air between layers keeps you warmer.")
        if weather == "rainy":
            tips.append("Tuck your trousers into boots or wear water-resistant shoes.")
        if humidity > 80 and band in ("warm", "hot"):
            tips.append("High humidity today — avoid synthetic fabrics that trap sweat.")
        if wind > 30:
            tips.append("Strong winds forecast — secure loose layers and accessories.")
        if occasion == "formal":
            tips.append("Stick to a classic two- or three-colour palette for polish.")
        if occasion == "work":
            tips.append("Smart layers let you adapt from the commute to the office.")
        if not tips:
            tips.append("Comfortable conditions — dress for the occasion and enjoy!")
        return tips

    def _outfit_name(self, band: str, weather: str, occasion: str) -> str:
        names = {
            ("hot", "sunny", "casual"):    "Sun-Ready Casual",
            ("warm", "cloudy", "work"):    "Office-Ready Look",
            ("mild", "rainy", "casual"):   "Rainy Day Chic",
            ("cold", "snowy", "outdoor"):  "Winter Explorer",
            ("freezing", "snowy", "casual"): "Arctic Comfort",
        }
        return names.get((band, weather, occasion),
                         f"{band.title()} {occasion.title()} Ensemble")

    def _style_notes(self, band: str, occasion: str) -> str:
        if band == "hot":
            return ("Keep it light and breezy. Loose silhouettes and breathable "
                    "fabrics are your best friends on a hot day.")
        if band in ("cold", "freezing"):
            return ("Embrace the layered look. Proportions matter — try a slim "
                    "base layer under a relaxed outer piece.")
        if occasion == "formal":
            return ("Precision is everything in formal dressing. Ensure your "
                    "clothes are pressed and your shoes are polished.")
        return ("Balance comfort with style. A well-fitted outfit in a "
                "coordinated palette always looks put-together.")

    def get_catalogue(
        self,
        occasion: str | None = None,
        weather: str | None = None,
        gender: str = "unisex"
    ) -> list[dict]:
        items = OUTFIT_CATALOGUE
        if occasion:
            items = [i for i in items if occasion in i.occasion_tags]
        if weather:
            items = [i for i in items if weather in i.weather_tags]
        items = [i for i in items
                 if gender in i.gender_tags or "unisex" in i.gender_tags]
        return [asdict(i) for i in items]
