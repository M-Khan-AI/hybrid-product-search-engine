"""Step 1: create products.db and fill it with 200 realistic electronics products."""
import random
import sqlite3

from config import DB_PATH, NUM_PRODUCTS, RANDOM_SEED

# category -> brands, product lines, price range (USD), spec options, description template
CATALOG = {
    "Smartphones": {
        "brands": ["Samsung", "Apple", "Xiaomi", "Google", "OnePlus", "Oppo", "Infinix"],
        "lines": ["Galaxy", "Note", "Pixel", "Nova", "Edge", "Spark"],
        "price": (150, 1300),
        "specs": ["128GB", "256GB", "512GB"],
        "desc": "A {adj} smartphone with a {screen} display, {spec} storage and a {cam} camera. "
                "Features 5G connectivity and all-day battery life, ideal for photos, gaming and social media.",
        "extra": {"screen": ['6.1-inch OLED', '6.7-inch AMOLED', '6.4-inch LCD'],
                  "cam": ["50MP", "108MP", "64MP"]},
    },
    "Laptops": {
        "brands": ["Dell", "HP", "Lenovo", "Asus", "Acer", "Apple", "MSI"],
        "lines": ["Inspiron", "ThinkPad", "ZenBook", "Aspire", "Pavilion", "MacBook", "Vivobook"],
        "price": (350, 2500),
        "specs": ["8GB RAM", "16GB RAM", "32GB RAM"],
        "desc": "A {adj} laptop with a {screen} screen and {spec}. Includes fast SSD storage and long battery life, "
                "great for students, office work, programming and light video editing.",
        "extra": {"screen": ['14-inch FHD', '15.6-inch FHD', '16-inch QHD', '13.3-inch OLED']},
    },
    "Headphones": {
        "brands": ["Sony", "Bose", "JBL", "Anker", "Sennheiser", "Beats", "Audio-Technica"],
        "lines": ["WH", "QuietComfort", "Tune", "Soundcore", "Momentum", "Studio"],
        "price": (25, 400),
        "specs": ["30-hour battery", "40-hour battery", "60-hour battery"],
        "desc": "A {adj} pair of wireless over-ear headphones with active noise cancellation and a {spec}. "
                "Delivers rich bass and clear vocals for music, calls and travel.",
        "extra": {},
    },
    "Earbuds": {
        "brands": ["Apple", "Samsung", "Nothing", "Realme", "Jabra", "QCY", "Xiaomi"],
        "lines": ["Buds", "Pods", "Ear", "Air", "Elite", "Liberty"],
        "price": (15, 250),
        "specs": ["IPX4 water resistance", "IPX5 sweatproof", "IP57 waterproof"],
        "desc": "{adj} true wireless earbuds with {spec}, Bluetooth 5.3 and a compact charging case. "
                "Comfortable for workouts, commuting and phone calls.",
        "extra": {},
    },
    "Smartwatches": {
        "brands": ["Apple", "Samsung", "Garmin", "Amazfit", "Huawei", "Fitbit", "Xiaomi"],
        "lines": ["Watch", "Fit", "Band", "Forerunner", "GTR", "Versa"],
        "price": (40, 700),
        "specs": ["GPS", "GPS + LTE", "AMOLED display"],
        "desc": "A {adj} smartwatch with {spec}, heart-rate and sleep tracking, and 100+ sport modes. "
                "Shows phone notifications and lasts several days per charge.",
        "extra": {},
    },
    "Tablets": {
        "brands": ["Apple", "Samsung", "Lenovo", "Xiaomi", "Huawei", "Amazon"],
        "lines": ["iPad", "Galaxy Tab", "Tab", "Pad", "MatePad", "Fire"],
        "price": (80, 1200),
        "specs": ["64GB", "128GB", "256GB"],
        "desc": "A {adj} tablet with a {screen} touchscreen and {spec} storage. "
                "Perfect for reading, streaming, drawing and online classes.",
        "extra": {"screen": ['10.1-inch', '10.9-inch', '11-inch', '12.9-inch']},
    },
    "Cameras": {
        "brands": ["Canon", "Nikon", "Sony", "Fujifilm", "GoPro", "Panasonic"],
        "lines": ["EOS", "Alpha", "Z", "X-T", "Hero", "Lumix"],
        "price": (150, 2800),
        "specs": ["24MP", "33MP", "45MP", "4K video"],
        "desc": "A {adj} camera with {spec} sensor performance, fast autofocus and Wi-Fi sharing. "
                "Suited to travel photography, vlogging and professional shoots.",
        "extra": {},
    },
    "Speakers": {
        "brands": ["JBL", "Sony", "Bose", "Marshall", "Anker", "Ultimate Ears"],
        "lines": ["Flip", "Charge", "SoundLink", "Emberton", "Boom", "Go"],
        "price": (20, 450),
        "specs": ["IP67 waterproof", "20-hour playtime", "360-degree sound"],
        "desc": "A {adj} portable Bluetooth speaker with {spec} and deep bass. "
                "Great for parties, camping, the beach and the home.",
        "extra": {},
    },
    "Monitors": {
        "brands": ["LG", "Samsung", "Dell", "Asus", "BenQ", "AOC"],
        "lines": ["UltraGear", "Odyssey", "UltraSharp", "ProArt", "MobiuZ", "Gaming"],
        "price": (90, 1100),
        "specs": ["24-inch 1080p", "27-inch 1440p", "32-inch 4K"],
        "desc": "A {adj} {spec} monitor with a fast refresh rate, IPS panel and adjustable stand. "
                "Excellent for gaming, design work and productivity.",
        "extra": {},
    },
    "Accessories": {
        "brands": ["Anker", "Logitech", "Belkin", "Razer", "SanDisk", "Baseus"],
        "lines": ["PowerCore", "MX", "Boost", "DeathAdder", "Extreme", "Nano"],
        "price": (8, 180),
        "specs": ["20000mAh power bank", "wireless mouse", "mechanical keyboard",
                  "65W fast charger", "1TB portable SSD"],
        "desc": "A reliable {adj} {spec}. Built with durable materials and designed for everyday use "
                "with phones, laptops and other devices.",
        "extra": {},
    },
}

ADJECTIVES = ["premium", "budget-friendly", "lightweight", "high-performance", "sleek",
              "powerful", "compact", "versatile", "reliable", "next-generation"]


def build_products():
    rng = random.Random(RANDOM_SEED)
    categories = list(CATALOG)
    products, seen = [], set()
    i = 0
    while len(products) < NUM_PRODUCTS:
        category = categories[i % len(categories)]  # spread evenly across categories
        i += 1
        c = CATALOG[category]
        brand = rng.choice(c["brands"])
        spec = rng.choice(c["specs"])
        model = f"{rng.choice(c['lines'])} {rng.randint(2, 99)}"
        title = f"{brand} {model} {spec}"
        if title in seen:
            continue
        seen.add(title)
        fields = {k: rng.choice(v) for k, v in c["extra"].items()}
        description = c["desc"].format(adj=rng.choice(ADJECTIVES), spec=spec, **fields)
        price = round(rng.uniform(*c["price"]), 2)
        products.append((title, description, brand, category, price,
                         round(rng.uniform(3.4, 5.0), 1), rng.randint(0, 300)))
    return products


def main():
    if DB_PATH.exists():
        DB_PATH.unlink()  # always rebuild from scratch
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE products (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            title       TEXT NOT NULL,
            description TEXT NOT NULL,
            brand       TEXT NOT NULL,
            category    TEXT NOT NULL,
            price       REAL NOT NULL,
            rating      REAL,
            stock       INTEGER DEFAULT 0
        )""")
    conn.executemany(
        "INSERT INTO products (title, description, brand, category, price, rating, stock) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)", build_products())
    conn.commit()
    count = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    conn.close()
    print(f"[generate_products] Inserted {count} products into {DB_PATH.name}")


if __name__ == "__main__":
    main()