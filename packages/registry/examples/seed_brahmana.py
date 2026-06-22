"""Seed a menu.json for the Brahmana Naivedyam client using the live menu.

Run from the package root:

    uv run python examples/seed_brahmana.py

Produces ``examples/brahmana-menu.json`` — the catalog your API/frontend reads.
"""

from pathlib import Path

from createcart_registry import MenuRegistry
from createcart_registry.storage import JSONFileStore

OUT = Path(__file__).parent / "brahmana-menu.json"

ITEMS = [
    # name, telugu, price, icon, tags, description
    ("Upma Pesarattu", "ఉప్మా పెసరట్టు", "70", "🌿", ["SPECIAL"],
     "Crisp green moong dal crepe layered with soft rava upma."),
    ("Plain Pesarattu", "ప్లేన్ పెసరట్టు", "60", "🌱", [],
     "Light, protein-rich moong dal crepe with ginger chutney."),
    ("Ghee Upma Pesarattu", "ఘీ ఉప్మా పెసరట్టు", "80", "🧈", [],
     "Upma pesarattu finished with pure ghee."),
    ("Upma Dosa", "ఉప్మా దోశ", "70", "🥞", [],
     "Golden dosa rolled with seasoned rava upma."),
    ("Plain Dosa", "ప్లేన్ దోశ", "60", "🫓", [],
     "Classic thin, crisp dosa with coconut chutney and sambar."),
    ("Masala Dosa", "మసాలా దోశ", "70", "🥔", [],
     "Crisp dosa wrapped around a spiced potato filling."),
    ("Ghee Masala Dosa", "ఘీ మసాలా దోశ", "80", "🧈", [],
     "Masala dosa roasted in pure ghee until deeply golden."),
    ("Pulihora Dosa", "పులిహోర దోశ", "70", "🍋", [],
     "Tangy tamarind pulihora tucked inside a crisp dosa."),
    ("Pulihora", "పులిహోర", "50", "🍚", ["SPECIAL"],
     "Tamarind rice tempered with mustard, curry leaves and cashews."),
    ("Daddojanam", "దద్దోజనం", "50", "🥛", ["SPECIAL"],
     "Curd rice — cool, creamy, tempered with mustard and pomegranate."),
    ("Katte Pongali", "కట్టె పొంగలి", "50", "🥣", ["SPECIAL"],
     "Savory pongal of rice and moong with black pepper and ghee."),
    ("Seemiya Payasam", "సేమియా పాయసం", "50", "🍮", ["SWEET"],
     "Vermicelli kheer with milk, cashews and cardamom."),
    ("Upma", "ఉప్మా", "50", "🌾", ["SPECIAL"],
     "Coarse rava upma tempered with mustard, chilli and curry leaves."),
]


def main() -> None:
    if OUT.exists():
        OUT.unlink()
    reg = MenuRegistry(store=JSONFileStore(OUT), tenant="brahmana-naivedyam")

    for order, (name, te, price, icon, tags, desc) in enumerate(ITEMS):
        reg.add_item(
            name=name,
            name_localized=te,
            price=price,
            icon=icon,
            tags=tags,
            description=desc,
            sort_order=order,
        )

    reg.add_combo(
        name="Combo 1", price="100",
        description="Katte Pongali + Upma + Pulihora — any three rice items.",
        sort_order=0,
    )
    reg.add_combo(
        name="Combo 2", price="70",
        description="Any two rice items combination.",
        sort_order=1,
    )

    print(f"Seeded {reg.count()} items and {len(reg.list_combos())} combos -> {OUT}")


if __name__ == "__main__":
    main()
