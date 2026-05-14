"""Embedded static travel data — used as fallback when Amadeus API is unavailable."""

from __future__ import annotations

try:
    from ..models import Activity, Flight, Hotel
except ImportError:
    from models import Activity, Flight, Hotel

# Paris hotels intentionally exceed $1 500/night to exercise the backtracking path.
STATIC_DATA: dict[str, dict] = {
    "Tokyo": {
        "flights": [
            Flight(id="f1", destination="Tokyo", price=650,  airline="ANA",  duration_hours=14, style_tags=["adventure", "culture"]),
            Flight(id="f2", destination="Tokyo", price=820,  airline="JAL",  duration_hours=12, style_tags=["luxury",    "culture"]),
        ],
        "hotels": [
            Hotel(id="h1", destination="Tokyo", name="Shinjuku Inn",     price_per_night=120, stars=3, style_tags=["budget",  "culture"]),
            Hotel(id="h2", destination="Tokyo", name="Park Hyatt Tokyo", price_per_night=450, stars=5, style_tags=["luxury"]),
        ],
        "activities": [
            Activity(id="a1", destination="Tokyo", name="Tsukiji Market Tour", price=30,  style_tags=["culture", "food"]),
            Activity(id="a2", destination="Tokyo", name="Mt. Fuji Day Trip",   price=80,  style_tags=["adventure", "nature"]),
            Activity(id="a3", destination="Tokyo", name="Akihabara Walk",      price=0,   style_tags=["culture"]),
        ],
    },
    "Paris": {
        "flights": [
            Flight(id="f3", destination="Paris", price=400, airline="Air France", duration_hours=8, style_tags=["romance", "culture"]),
            Flight(id="f4", destination="Paris", price=550, airline="Lufthansa",  duration_hours=9, style_tags=["luxury",  "romance"]),
        ],
        "hotels": [
            Hotel(id="h3", destination="Paris", name="Le Grand Hotel", price_per_night=1800, stars=5, style_tags=["luxury", "romance"]),
            Hotel(id="h4", destination="Paris", name="Hotel Lumiere",  price_per_night=1600, stars=4, style_tags=["romance"]),
        ],
        "activities": [
            Activity(id="a4", destination="Paris", name="Eiffel Tower Visit", price=25, style_tags=["romance", "culture"]),
            Activity(id="a5", destination="Paris", name="Louvre Museum",      price=17, style_tags=["culture", "art"]),
            Activity(id="a6", destination="Paris", name="Seine River Cruise", price=15, style_tags=["romance"]),
        ],
    },
    "Bali": {
        "flights": [
            Flight(id="f5", destination="Bali", price=700, airline="Garuda",    duration_hours=18, style_tags=["adventure", "nature"]),
            Flight(id="f6", destination="Bali", price=850, airline="Singapore", duration_hours=16, style_tags=["luxury",    "nature"]),
        ],
        "hotels": [
            Hotel(id="h5", destination="Bali", name="Ubud Jungle Resort",   price_per_night=90,  stars=3, style_tags=["nature", "adventure"]),
            Hotel(id="h6", destination="Bali", name="Seminyak Beach Villa", price_per_night=200, stars=4, style_tags=["luxury", "nature"]),
        ],
        "activities": [
            Activity(id="a7", destination="Bali", name="Rice Terrace Trek", price=20, style_tags=["adventure", "nature"]),
            Activity(id="a8", destination="Bali", name="Temple Ceremony",   price=10, style_tags=["culture",   "nature"]),
            Activity(id="a9", destination="Bali", name="Surf Lesson",       price=45, style_tags=["adventure"]),
        ],
    },
    "New York": {
        "flights": [
            Flight(id="f7", destination="New York", price=300, airline="Delta",   duration_hours=6, style_tags=["culture", "food"]),
            Flight(id="f8", destination="New York", price=420, airline="JetBlue", duration_hours=6, style_tags=["luxury",  "culture"]),
        ],
        "hotels": [
            Hotel(id="h7", destination="New York", name="Times Square Hotel", price_per_night=180, stars=3, style_tags=["culture", "food"]),
            Hotel(id="h8", destination="New York", name="The Plaza",          price_per_night=600, stars=5, style_tags=["luxury"]),
        ],
        "activities": [
            Activity(id="a10", destination="New York", name="Central Park Walk", price=0,   style_tags=["nature",  "culture"]),
            Activity(id="a11", destination="New York", name="Broadway Show",     price=120, style_tags=["culture", "art"]),
            Activity(id="a12", destination="New York", name="Food Tour",         price=65,  style_tags=["food",    "culture"]),
        ],
    },
}


def _extend_catalog() -> None:
    """Add richer demo data while keeping the original required destinations."""
    STATIC_DATA["Tokyo"]["flights"].extend([
        Flight(id="f9", destination="Tokyo", price=540, airline="Peach Aviation", duration_hours=15.5, style_tags=["budget", "adventure"]),
        Flight(id="f10", destination="Tokyo", price=720, airline="Cathay Pacific", duration_hours=13.5, style_tags=["culture", "food"]),
        Flight(id="f11", destination="Tokyo", price=980, airline="Singapore Airlines", duration_hours=11.5, style_tags=["luxury", "culture"]),
        Flight(id="f12", destination="Tokyo", price=610, airline="Korean Air", duration_hours=14.2, style_tags=["budget", "culture"]),
        Flight(id="f13", destination="Tokyo", price=1150, airline="Emirates", duration_hours=12.8, style_tags=["luxury", "food"]),
        Flight(id="f14", destination="Tokyo", price=760, airline="Turkish Airlines", duration_hours=16.0, style_tags=["adventure", "budget"]),
    ])
    STATIC_DATA["Tokyo"]["hotels"].extend([
        Hotel(id="h9", destination="Tokyo", name="Asakusa Riverside Hotel", price_per_night=95, stars=3, style_tags=["budget", "culture"]),
        Hotel(id="h10", destination="Tokyo", name="Ginza Boutique Stay", price_per_night=210, stars=4, style_tags=["luxury", "food"]),
        Hotel(id="h11", destination="Tokyo", name="Ueno Garden Guesthouse", price_per_night=70, stars=2, style_tags=["budget", "nature"]),
        Hotel(id="h12", destination="Tokyo", name="Shibuya Nightlife Hotel", price_per_night=260, stars=4, style_tags=["culture", "food"]),
        Hotel(id="h13", destination="Tokyo", name="Aman Tokyo", price_per_night=780, stars=5, style_tags=["luxury"]),
        Hotel(id="h14", destination="Tokyo", name="Ryokan Yanaka", price_per_night=160, stars=3, style_tags=["culture", "romance"]),
    ])
    STATIC_DATA["Tokyo"]["activities"].extend([
        Activity(id="a13", destination="Tokyo", name="Sushi Making Class", price=75, style_tags=["food", "culture"]),
        Activity(id="a14", destination="Tokyo", name="TeamLab Planets", price=35, style_tags=["culture", "art"]),
        Activity(id="a15", destination="Tokyo", name="Imperial Palace Bike Tour", price=45, style_tags=["adventure", "culture"]),
        Activity(id="a16", destination="Tokyo", name="Shinjuku Izakaya Crawl", price=90, style_tags=["food", "culture"]),
        Activity(id="a17", destination="Tokyo", name="Hakone Onsen Day Trip", price=140, style_tags=["nature", "romance"]),
        Activity(id="a18", destination="Tokyo", name="Meiji Shrine Morning Walk", price=0, style_tags=["culture", "nature"]),
        Activity(id="a19", destination="Tokyo", name="Private Wagyu Dinner", price=180, style_tags=["luxury", "food"]),
    ])

    STATIC_DATA["Paris"]["flights"].extend([
        Flight(id="f15", destination="Paris", price=360, airline="Transavia", duration_hours=9.5, style_tags=["budget", "romance"]),
        Flight(id="f16", destination="Paris", price=480, airline="KLM", duration_hours=8.8, style_tags=["culture", "food"]),
        Flight(id="f17", destination="Paris", price=720, airline="British Airways", duration_hours=7.9, style_tags=["luxury", "culture"]),
        Flight(id="f18", destination="Paris", price=610, airline="Iberia", duration_hours=8.4, style_tags=["romance", "food"]),
        Flight(id="f19", destination="Paris", price=920, airline="La Compagnie", duration_hours=7.5, style_tags=["luxury", "romance"]),
    ])
    STATIC_DATA["Paris"]["hotels"].extend([
        Hotel(id="h15", destination="Paris", name="Ritz Paris", price_per_night=2200, stars=5, style_tags=["luxury", "romance"]),
        Hotel(id="h16", destination="Paris", name="Cheval Blanc Paris", price_per_night=2500, stars=5, style_tags=["luxury", "food"]),
        Hotel(id="h17", destination="Paris", name="Saint-Germain Palace", price_per_night=1750, stars=5, style_tags=["culture", "romance"]),
        Hotel(id="h18", destination="Paris", name="Montmartre View Maison", price_per_night=1650, stars=4, style_tags=["romance", "culture"]),
        Hotel(id="h19", destination="Paris", name="Opera Prestige Suites", price_per_night=1900, stars=5, style_tags=["luxury", "culture"]),
    ])
    STATIC_DATA["Paris"]["activities"].extend([
        Activity(id="a20", destination="Paris", name="Montmartre Art Walk", price=35, style_tags=["culture", "art", "romance"]),
        Activity(id="a21", destination="Paris", name="French Pastry Workshop", price=95, style_tags=["food", "culture"]),
        Activity(id="a22", destination="Paris", name="Versailles Garden Tour", price=85, style_tags=["culture", "nature"]),
        Activity(id="a23", destination="Paris", name="Champagne Tasting", price=120, style_tags=["luxury", "romance", "food"]),
        Activity(id="a24", destination="Paris", name="Latin Quarter Bookshop Walk", price=18, style_tags=["culture", "romance"]),
        Activity(id="a25", destination="Paris", name="Private Louvre Highlights", price=160, style_tags=["luxury", "art", "culture"]),
    ])

    STATIC_DATA["Bali"]["flights"].extend([
        Flight(id="f20", destination="Bali", price=620, airline="AirAsia", duration_hours=20, style_tags=["budget", "adventure"]),
        Flight(id="f21", destination="Bali", price=760, airline="Qatar Airways", duration_hours=17.5, style_tags=["luxury", "nature"]),
        Flight(id="f22", destination="Bali", price=690, airline="Thai Airways", duration_hours=18.5, style_tags=["culture", "nature"]),
        Flight(id="f23", destination="Bali", price=930, airline="Emirates", duration_hours=16.5, style_tags=["luxury", "romance"]),
        Flight(id="f24", destination="Bali", price=580, airline="Scoot", duration_hours=21, style_tags=["budget", "adventure"]),
    ])
    STATIC_DATA["Bali"]["hotels"].extend([
        Hotel(id="h20", destination="Bali", name="Canggu Surf House", price_per_night=65, stars=3, style_tags=["budget", "adventure"]),
        Hotel(id="h21", destination="Bali", name="Uluwatu Cliff Villas", price_per_night=320, stars=5, style_tags=["luxury", "romance", "nature"]),
        Hotel(id="h22", destination="Bali", name="Sanur Family Resort", price_per_night=140, stars=4, style_tags=["nature", "culture"]),
        Hotel(id="h23", destination="Bali", name="Munduk Mountain Lodge", price_per_night=110, stars=3, style_tags=["nature", "adventure"]),
        Hotel(id="h24", destination="Bali", name="Nusa Dua Spa Palace", price_per_night=260, stars=5, style_tags=["luxury", "romance"]),
        Hotel(id="h25", destination="Bali", name="Kuta Budget Inn", price_per_night=45, stars=2, style_tags=["budget", "food"]),
    ])
    STATIC_DATA["Bali"]["activities"].extend([
        Activity(id="a26", destination="Bali", name="Ubud Cooking Class", price=55, style_tags=["food", "culture"]),
        Activity(id="a27", destination="Bali", name="Mount Batur Sunrise Hike", price=70, style_tags=["adventure", "nature"]),
        Activity(id="a28", destination="Bali", name="Uluwatu Sunset Kecak Dance", price=30, style_tags=["culture", "romance"]),
        Activity(id="a29", destination="Bali", name="Nusa Penida Snorkeling", price=110, style_tags=["adventure", "nature"]),
        Activity(id="a30", destination="Bali", name="Balinese Spa Ritual", price=85, style_tags=["luxury", "romance"]),
        Activity(id="a31", destination="Bali", name="Canggu Street Food Ride", price=40, style_tags=["food", "adventure"]),
        Activity(id="a32", destination="Bali", name="Waterfall Photography Tour", price=65, style_tags=["nature", "culture"]),
    ])

    STATIC_DATA["New York"]["flights"].extend([
        Flight(id="f25", destination="New York", price=250, airline="Spirit", duration_hours=6.5, style_tags=["budget"]),
        Flight(id="f26", destination="New York", price=360, airline="United", duration_hours=6.2, style_tags=["culture", "food"]),
        Flight(id="f27", destination="New York", price=520, airline="American Airlines", duration_hours=5.8, style_tags=["luxury", "culture"]),
        Flight(id="f28", destination="New York", price=610, airline="Delta One", duration_hours=5.6, style_tags=["luxury", "food"]),
        Flight(id="f29", destination="New York", price=330, airline="Southwest", duration_hours=6.8, style_tags=["budget", "culture"]),
    ])
    STATIC_DATA["New York"]["hotels"].extend([
        Hotel(id="h26", destination="New York", name="Pod Times Square", price_per_night=135, stars=3, style_tags=["budget", "culture"]),
        Hotel(id="h27", destination="New York", name="SoHo Grand", price_per_night=320, stars=4, style_tags=["luxury", "food", "culture"]),
        Hotel(id="h28", destination="New York", name="Brooklyn Art Loft Hotel", price_per_night=190, stars=3, style_tags=["culture", "art"]),
        Hotel(id="h29", destination="New York", name="Central Park West Suites", price_per_night=420, stars=4, style_tags=["luxury", "nature"]),
        Hotel(id="h30", destination="New York", name="Chelsea Market Inn", price_per_night=210, stars=3, style_tags=["food", "culture"]),
        Hotel(id="h31", destination="New York", name="Bowery Budget Stay", price_per_night=95, stars=2, style_tags=["budget", "food"]),
    ])
    STATIC_DATA["New York"]["activities"].extend([
        Activity(id="a33", destination="New York", name="Statue of Liberty Ferry", price=25, style_tags=["culture"]),
        Activity(id="a34", destination="New York", name="Brooklyn Pizza Crawl", price=70, style_tags=["food", "culture"]),
        Activity(id="a35", destination="New York", name="MoMA Highlights Tour", price=45, style_tags=["art", "culture"]),
        Activity(id="a36", destination="New York", name="Harlem Jazz Night", price=95, style_tags=["culture", "romance"]),
        Activity(id="a37", destination="New York", name="Hudson River Bike Ride", price=30, style_tags=["adventure", "nature"]),
        Activity(id="a38", destination="New York", name="Rooftop Fine Dining", price=160, style_tags=["luxury", "food"]),
        Activity(id="a39", destination="New York", name="DUMBO Photo Walk", price=0, style_tags=["culture", "art"]),
    ])

    STATIC_DATA.update({
        "Japan": {
            "flights": [
                Flight(id="f30", destination="Japan", price=680, airline="ANA", duration_hours=14.0, style_tags=["culture", "food"]),
                Flight(id="f31", destination="Japan", price=790, airline="Japan Airlines", duration_hours=12.5, style_tags=["luxury", "culture"]),
                Flight(id="f32", destination="Japan", price=560, airline="Korean Air", duration_hours=15.0, style_tags=["budget", "adventure"]),
                Flight(id="f33", destination="Japan", price=980, airline="Singapore Airlines", duration_hours=13.0, style_tags=["luxury", "food"]),
            ],
            "hotels": [
                Hotel(id="h32", destination="Japan", name="Kyoto Machiya Stay", price_per_night=130, stars=3, style_tags=["culture", "romance"]),
                Hotel(id="h33", destination="Japan", name="Osaka Namba Hotel", price_per_night=105, stars=3, style_tags=["budget", "food"]),
                Hotel(id="h34", destination="Japan", name="Hakone Ryokan Retreat", price_per_night=260, stars=4, style_tags=["nature", "romance"]),
                Hotel(id="h35", destination="Japan", name="Tokyo Luxury Tower", price_per_night=520, stars=5, style_tags=["luxury", "culture"]),
            ],
            "activities": [
                Activity(id="a40", destination="Japan", name="Kyoto Temple Walk", price=25, style_tags=["culture", "nature"]),
                Activity(id="a41", destination="Japan", name="Osaka Street Food Night", price=70, style_tags=["food", "culture"]),
                Activity(id="a42", destination="Japan", name="Nara Deer Park Day Trip", price=45, style_tags=["nature", "culture"]),
                Activity(id="a43", destination="Japan", name="Snow Monkey Onsen Tour", price=120, style_tags=["adventure", "nature"]),
                Activity(id="a44", destination="Japan", name="Kobe Beef Dinner", price=180, style_tags=["luxury", "food"]),
            ],
        },
        "France": {
            "flights": [
                Flight(id="f34", destination="France", price=430, airline="Air France", duration_hours=8.0, style_tags=["romance", "culture"]),
                Flight(id="f35", destination="France", price=390, airline="French Bee", duration_hours=9.0, style_tags=["budget", "romance"]),
                Flight(id="f36", destination="France", price=620, airline="KLM", duration_hours=8.5, style_tags=["food", "culture"]),
                Flight(id="f37", destination="France", price=880, airline="La Compagnie", duration_hours=7.8, style_tags=["luxury", "romance"]),
            ],
            "hotels": [
                Hotel(id="h36", destination="France", name="Nice Seafront Hotel", price_per_night=180, stars=4, style_tags=["romance", "nature"]),
                Hotel(id="h37", destination="France", name="Lyon Food Quarter Inn", price_per_night=125, stars=3, style_tags=["food", "culture"]),
                Hotel(id="h38", destination="France", name="Loire Chateau Stay", price_per_night=340, stars=5, style_tags=["luxury", "romance"]),
                Hotel(id="h39", destination="France", name="Marseille Budget Rooms", price_per_night=80, stars=2, style_tags=["budget", "food"]),
            ],
            "activities": [
                Activity(id="a45", destination="France", name="Provence Lavender Tour", price=90, style_tags=["nature", "romance"]),
                Activity(id="a46", destination="France", name="Lyon Market Tasting", price=65, style_tags=["food", "culture"]),
                Activity(id="a47", destination="France", name="French Riviera Boat Day", price=140, style_tags=["luxury", "nature"]),
                Activity(id="a48", destination="France", name="Loire Valley Castle Route", price=110, style_tags=["culture", "romance"]),
                Activity(id="a49", destination="France", name="Marseille Street Art Walk", price=20, style_tags=["culture", "art"]),
            ],
        },
        "Italy": {
            "flights": [
                Flight(id="f38", destination="Italy", price=470, airline="ITA Airways", duration_hours=9.0, style_tags=["culture", "food"]),
                Flight(id="f39", destination="Italy", price=420, airline="Norse Atlantic", duration_hours=10.5, style_tags=["budget", "adventure"]),
                Flight(id="f40", destination="Italy", price=700, airline="Lufthansa", duration_hours=9.5, style_tags=["luxury", "culture"]),
                Flight(id="f41", destination="Italy", price=560, airline="Turkish Airlines", duration_hours=11.0, style_tags=["food", "romance"]),
            ],
            "hotels": [
                Hotel(id="h40", destination="Italy", name="Rome Trastevere Hotel", price_per_night=140, stars=3, style_tags=["culture", "food"]),
                Hotel(id="h41", destination="Italy", name="Florence Art Residence", price_per_night=190, stars=4, style_tags=["culture", "romance"]),
                Hotel(id="h42", destination="Italy", name="Amalfi Cliff Resort", price_per_night=430, stars=5, style_tags=["luxury", "romance", "nature"]),
                Hotel(id="h43", destination="Italy", name="Naples Budget Stay", price_per_night=75, stars=2, style_tags=["budget", "food"]),
            ],
            "activities": [
                Activity(id="a50", destination="Italy", name="Rome Ancient Sites Walk", price=35, style_tags=["culture"]),
                Activity(id="a51", destination="Italy", name="Florence Uffizi Highlights", price=55, style_tags=["art", "culture"]),
                Activity(id="a52", destination="Italy", name="Tuscan Cooking Class", price=95, style_tags=["food", "romance"]),
                Activity(id="a53", destination="Italy", name="Amalfi Boat Excursion", price=130, style_tags=["luxury", "nature"]),
                Activity(id="a54", destination="Italy", name="Naples Pizza Tour", price=60, style_tags=["food", "culture"]),
            ],
        },
        "Greece": {
            "flights": [
                Flight(id="f42", destination="Greece", price=520, airline="Aegean Airlines", duration_hours=10.0, style_tags=["culture", "romance"]),
                Flight(id="f43", destination="Greece", price=460, airline="Norse Atlantic", duration_hours=11.5, style_tags=["budget", "nature"]),
                Flight(id="f44", destination="Greece", price=740, airline="Emirates", duration_hours=10.5, style_tags=["luxury", "romance"]),
                Flight(id="f45", destination="Greece", price=610, airline="Turkish Airlines", duration_hours=11.0, style_tags=["food", "culture"]),
            ],
            "hotels": [
                Hotel(id="h44", destination="Greece", name="Athens Plaka Hotel", price_per_night=120, stars=3, style_tags=["culture", "budget"]),
                Hotel(id="h45", destination="Greece", name="Santorini Caldera Suites", price_per_night=380, stars=5, style_tags=["luxury", "romance"]),
                Hotel(id="h46", destination="Greece", name="Crete Beach Resort", price_per_night=170, stars=4, style_tags=["nature", "food"]),
                Hotel(id="h47", destination="Greece", name="Meteora Mountain Guesthouse", price_per_night=90, stars=3, style_tags=["nature", "adventure"]),
            ],
            "activities": [
                Activity(id="a55", destination="Greece", name="Acropolis Guided Walk", price=35, style_tags=["culture"]),
                Activity(id="a56", destination="Greece", name="Santorini Sunset Cruise", price=120, style_tags=["romance", "luxury"]),
                Activity(id="a57", destination="Greece", name="Crete Food Village Tour", price=75, style_tags=["food", "culture"]),
                Activity(id="a58", destination="Greece", name="Meteora Monastery Hike", price=60, style_tags=["adventure", "nature"]),
                Activity(id="a59", destination="Greece", name="Mykonos Beach Day", price=45, style_tags=["nature", "romance"]),
            ],
        },
        "Thailand": {
            "flights": [
                Flight(id="f46", destination="Thailand", price=590, airline="Thai Airways", duration_hours=17.0, style_tags=["culture", "food"]),
                Flight(id="f47", destination="Thailand", price=510, airline="AirAsia", duration_hours=19.0, style_tags=["budget", "adventure"]),
                Flight(id="f48", destination="Thailand", price=780, airline="Singapore Airlines", duration_hours=16.0, style_tags=["luxury", "food"]),
                Flight(id="f49", destination="Thailand", price=650, airline="Qatar Airways", duration_hours=18.0, style_tags=["nature", "culture"]),
            ],
            "hotels": [
                Hotel(id="h48", destination="Thailand", name="Bangkok Riverside Hotel", price_per_night=95, stars=3, style_tags=["budget", "food"]),
                Hotel(id="h49", destination="Thailand", name="Chiang Mai Garden Lodge", price_per_night=70, stars=3, style_tags=["nature", "culture"]),
                Hotel(id="h50", destination="Thailand", name="Phuket Beach Villa", price_per_night=240, stars=4, style_tags=["romance", "nature"]),
                Hotel(id="h51", destination="Thailand", name="Koh Samui Luxury Resort", price_per_night=410, stars=5, style_tags=["luxury", "romance"]),
            ],
            "activities": [
                Activity(id="a60", destination="Thailand", name="Bangkok Street Food Crawl", price=45, style_tags=["food", "culture"]),
                Activity(id="a61", destination="Thailand", name="Elephant Sanctuary Visit", price=95, style_tags=["nature", "culture"]),
                Activity(id="a62", destination="Thailand", name="Phi Phi Island Boat Trip", price=110, style_tags=["adventure", "nature"]),
                Activity(id="a63", destination="Thailand", name="Thai Cooking Class", price=55, style_tags=["food", "culture"]),
                Activity(id="a64", destination="Thailand", name="Temple Sunrise Tour", price=25, style_tags=["culture", "romance"]),
            ],
        },
        "Spain": {
            "flights": [
                Flight(id="f50", destination="Spain", price=390, airline="Iberia", duration_hours=8.5, style_tags=["culture", "food"]),
                Flight(id="f51", destination="Spain", price=340, airline="LEVEL", duration_hours=9.2, style_tags=["budget", "culture"]),
                Flight(id="f52", destination="Spain", price=620, airline="British Airways", duration_hours=8.0, style_tags=["luxury", "food"]),
                Flight(id="f53", destination="Spain", price=520, airline="Air Europa", duration_hours=8.8, style_tags=["romance", "culture"]),
            ],
            "hotels": [
                Hotel(id="h52", destination="Spain", name="Barcelona Gothic Quarter Hotel", price_per_night=145, stars=3, style_tags=["culture", "food"]),
                Hotel(id="h53", destination="Spain", name="Madrid Museum District Stay", price_per_night=130, stars=3, style_tags=["art", "culture"]),
                Hotel(id="h54", destination="Spain", name="Seville Courtyard Palace", price_per_night=210, stars=4, style_tags=["romance", "culture"]),
                Hotel(id="h55", destination="Spain", name="Mallorca Sea Resort", price_per_night=300, stars=5, style_tags=["luxury", "nature"]),
            ],
            "activities": [
                Activity(id="a65", destination="Spain", name="Barcelona Tapas Tour", price=70, style_tags=["food", "culture"]),
                Activity(id="a66", destination="Spain", name="Sagrada Familia Visit", price=45, style_tags=["art", "culture"]),
                Activity(id="a67", destination="Spain", name="Flamenco Night", price=85, style_tags=["romance", "culture"]),
                Activity(id="a68", destination="Spain", name="Madrid Prado Highlights", price=40, style_tags=["art", "culture"]),
                Activity(id="a69", destination="Spain", name="Mallorca Cove Kayaking", price=75, style_tags=["adventure", "nature"]),
            ],
        },
        "United Kingdom": {
            "flights": [
                Flight(id="f54", destination="United Kingdom", price=420, airline="British Airways", duration_hours=7.0, style_tags=["culture", "luxury"]),
                Flight(id="f55", destination="United Kingdom", price=350, airline="Norse Atlantic", duration_hours=7.5, style_tags=["budget", "culture"]),
                Flight(id="f56", destination="United Kingdom", price=510, airline="Virgin Atlantic", duration_hours=6.8, style_tags=["food", "luxury"]),
                Flight(id="f57", destination="United Kingdom", price=460, airline="Aer Lingus", duration_hours=8.0, style_tags=["nature", "culture"]),
            ],
            "hotels": [
                Hotel(id="h56", destination="United Kingdom", name="London Covent Garden Hotel", price_per_night=210, stars=4, style_tags=["culture", "food"]),
                Hotel(id="h57", destination="United Kingdom", name="Edinburgh Old Town Inn", price_per_night=150, stars=3, style_tags=["culture", "romance"]),
                Hotel(id="h58", destination="United Kingdom", name="Cotswolds Country Manor", price_per_night=260, stars=4, style_tags=["nature", "romance"]),
                Hotel(id="h59", destination="United Kingdom", name="Manchester Budget Rooms", price_per_night=85, stars=2, style_tags=["budget", "culture"]),
            ],
            "activities": [
                Activity(id="a70", destination="United Kingdom", name="London Theatre Night", price=95, style_tags=["culture", "romance"]),
                Activity(id="a71", destination="United Kingdom", name="British Museum Highlights", price=0, style_tags=["culture", "art"]),
                Activity(id="a72", destination="United Kingdom", name="Edinburgh Castle Walk", price=35, style_tags=["culture", "adventure"]),
                Activity(id="a73", destination="United Kingdom", name="Cotswolds Village Day", price=85, style_tags=["nature", "romance"]),
                Activity(id="a74", destination="United Kingdom", name="London Food Market Crawl", price=65, style_tags=["food", "culture"]),
            ],
        },
        "Mexico": {
            "flights": [
                Flight(id="f58", destination="Mexico", price=320, airline="Aeromexico", duration_hours=5.0, style_tags=["culture", "food"]),
                Flight(id="f59", destination="Mexico", price=280, airline="Viva Aerobus", duration_hours=5.5, style_tags=["budget", "adventure"]),
                Flight(id="f60", destination="Mexico", price=480, airline="Delta", duration_hours=5.2, style_tags=["luxury", "food"]),
                Flight(id="f61", destination="Mexico", price=390, airline="United", duration_hours=5.8, style_tags=["nature", "culture"]),
            ],
            "hotels": [
                Hotel(id="h60", destination="Mexico", name="Mexico City Roma Hotel", price_per_night=110, stars=3, style_tags=["food", "culture"]),
                Hotel(id="h61", destination="Mexico", name="Cancun Beach Resort", price_per_night=240, stars=4, style_tags=["nature", "romance"]),
                Hotel(id="h62", destination="Mexico", name="Oaxaca Art Guesthouse", price_per_night=75, stars=3, style_tags=["budget", "culture"]),
                Hotel(id="h63", destination="Mexico", name="Tulum Jungle Villa", price_per_night=300, stars=5, style_tags=["luxury", "nature"]),
            ],
            "activities": [
                Activity(id="a75", destination="Mexico", name="Mexico City Taco Tour", price=45, style_tags=["food", "culture"]),
                Activity(id="a76", destination="Mexico", name="Teotihuacan Pyramids", price=65, style_tags=["culture", "adventure"]),
                Activity(id="a77", destination="Mexico", name="Oaxaca Cooking Workshop", price=70, style_tags=["food", "culture"]),
                Activity(id="a78", destination="Mexico", name="Cenote Swim Day", price=80, style_tags=["nature", "adventure"]),
                Activity(id="a79", destination="Mexico", name="Tulum Beach Club", price=120, style_tags=["luxury", "romance"]),
            ],
        },
        "Israel": {
            "flights": [
                Flight(id="f62", destination="Israel", price=520, airline="El Al", duration_hours=11.0, style_tags=["culture", "food"]),
                Flight(id="f63", destination="Israel", price=470, airline="Arkia", duration_hours=11.5, style_tags=["budget", "culture"]),
                Flight(id="f64", destination="Israel", price=680, airline="United", duration_hours=10.8, style_tags=["luxury", "culture"]),
                Flight(id="f65", destination="Israel", price=590, airline="Turkish Airlines", duration_hours=12.0, style_tags=["food", "romance"]),
            ],
            "hotels": [
                Hotel(id="h64", destination="Israel", name="Tel Aviv Beach Hotel", price_per_night=180, stars=4, style_tags=["food", "romance"]),
                Hotel(id="h65", destination="Israel", name="Jerusalem Old City Inn", price_per_night=130, stars=3, style_tags=["culture", "budget"]),
                Hotel(id="h66", destination="Israel", name="Dead Sea Spa Resort", price_per_night=260, stars=5, style_tags=["luxury", "nature"]),
                Hotel(id="h67", destination="Israel", name="Galilee Nature Lodge", price_per_night=115, stars=3, style_tags=["nature", "adventure"]),
            ],
            "activities": [
                Activity(id="a80", destination="Israel", name="Jerusalem Old City Tour", price=45, style_tags=["culture"]),
                Activity(id="a81", destination="Israel", name="Tel Aviv Food Market", price=60, style_tags=["food", "culture"]),
                Activity(id="a82", destination="Israel", name="Dead Sea Float Day", price=90, style_tags=["nature", "luxury"]),
                Activity(id="a83", destination="Israel", name="Galilee Winery Route", price=110, style_tags=["food", "romance", "nature"]),
                Activity(id="a84", destination="Israel", name="Negev Desert Jeep Tour", price=120, style_tags=["adventure", "nature"]),
            ],
        },
    })


def _rename_country_catalog_to_cities() -> None:
    """Keep the richer catalog, but expose destinations as cities only."""
    country_to_city = {
        "Japan": "Kyoto",
        "France": "Nice",
        "Italy": "Rome",
        "Greece": "Athens",
        "Thailand": "Bangkok",
        "Spain": "Barcelona",
        "United Kingdom": "London",
        "Mexico": "Mexico City",
        "Israel": "Tel Aviv",
    }

    for country, city in country_to_city.items():
        data = STATIC_DATA.pop(country, None)
        if data is None:
            continue
        for category in ("flights", "hotels", "activities"):
            for item in data.get(category, []):
                item.destination = city
        STATIC_DATA[city] = data


_extend_catalog()
_rename_country_catalog_to_cities()
