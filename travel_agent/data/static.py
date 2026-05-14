"""Embedded static travel data — used as fallback when Amadeus API is unavailable."""

from __future__ import annotations

try:
    from ..models import Activity, Flight, Hotel
except ImportError:
    from models import Activity, Flight, Hotel


STATIC_DATA: dict[str, dict] = {}


def _build_catalog() -> None:
    """Generate a comprehensive global travel catalog with 50+ destinations."""
    destinations = {
        "Tokyo": {
            "flights": [
                Flight(id="f1", destination="Tokyo", price=650, airline="ANA", duration_hours=14, style_tags=["adventure", "culture"]),
                Flight(id="f2", destination="Tokyo", price=820, airline="JAL", duration_hours=12, style_tags=["luxury", "culture"]),
                Flight(id="f9", destination="Tokyo", price=540, airline="Peach Aviation", duration_hours=15.5, style_tags=["budget", "adventure"]),
                Flight(id="f10", destination="Tokyo", price=720, airline="Cathay Pacific", duration_hours=13.5, style_tags=["culture", "food"]),
                Flight(id="f11", destination="Tokyo", price=980, airline="Singapore Airlines", duration_hours=11.5, style_tags=["luxury", "culture"]),
                Flight(id="f12", destination="Tokyo", price=610, airline="Korean Air", duration_hours=14.2, style_tags=["budget", "culture"]),
            ],
            "hotels": [
                Hotel(id="h1", destination="Tokyo", name="Shinjuku Inn", price_per_night=120, stars=3, style_tags=["budget", "culture"]),
                Hotel(id="h2", destination="Tokyo", name="Park Hyatt Tokyo", price_per_night=450, stars=5, style_tags=["luxury"]),
                Hotel(id="h9", destination="Tokyo", name="Asakusa Riverside Hotel", price_per_night=95, stars=3, style_tags=["budget", "culture"]),
                Hotel(id="h10", destination="Tokyo", name="Ginza Boutique Stay", price_per_night=210, stars=4, style_tags=["luxury", "food"]),
                Hotel(id="h12", destination="Tokyo", name="Shibuya Nightlife Hotel", price_per_night=260, stars=4, style_tags=["culture", "food"]),
                Hotel(id="h13", destination="Tokyo", name="Aman Tokyo", price_per_night=780, stars=5, style_tags=["luxury"]),
            ],
            "activities": [
                Activity(id="a1", destination="Tokyo", name="Tsukiji Market Tour", price=30, style_tags=["culture", "food"]),
                Activity(id="a2", destination="Tokyo", name="Mt. Fuji Day Trip", price=80, style_tags=["adventure", "nature"]),
                Activity(id="a3", destination="Tokyo", name="Akihabara Walk", price=0, style_tags=["culture"]),
                Activity(id="a13", destination="Tokyo", name="Sushi Making Class", price=75, style_tags=["food", "culture"]),
                Activity(id="a14", destination="Tokyo", name="TeamLab Planets", price=35, style_tags=["culture", "art"]),
                Activity(id="a16", destination="Tokyo", name="Shinjuku Izakaya Crawl", price=90, style_tags=["food", "culture"]),
            ],
        },
        "Paris": {
            "flights": [
                Flight(id="f3", destination="Paris", price=400, airline="Air France", duration_hours=8, style_tags=["romance", "culture"]),
                Flight(id="f4", destination="Paris", price=550, airline="Lufthansa", duration_hours=9, style_tags=["luxury", "romance"]),
                Flight(id="f15", destination="Paris", price=360, airline="Transavia", duration_hours=9.5, style_tags=["budget", "romance"]),
                Flight(id="f16", destination="Paris", price=480, airline="KLM", duration_hours=8.8, style_tags=["culture", "food"]),
                Flight(id="f17", destination="Paris", price=720, airline="British Airways", duration_hours=7.9, style_tags=["luxury", "culture"]),
                Flight(id="f19", destination="Paris", price=920, airline="La Compagnie", duration_hours=7.5, style_tags=["luxury", "romance"]),
            ],
            "hotels": [
                Hotel(id="h3", destination="Paris", name="Le Grand Hotel", price_per_night=1800, stars=5, style_tags=["luxury", "romance"]),
                Hotel(id="h4", destination="Paris", name="Hotel Lumiere", price_per_night=1600, stars=4, style_tags=["romance"]),
                Hotel(id="h17", destination="Paris", name="Saint-Germain Palace", price_per_night=1750, stars=5, style_tags=["culture", "romance"]),
                Hotel(id="h18", destination="Paris", name="Montmartre View Maison", price_per_night=1650, stars=4, style_tags=["romance", "culture"]),
                Hotel(id="h15", destination="Paris", name="Ritz Paris", price_per_night=2200, stars=5, style_tags=["luxury", "romance"]),
                Hotel(id="h19", destination="Paris", name="Opera Prestige Suites", price_per_night=1900, stars=5, style_tags=["luxury", "culture"]),
            ],
            "activities": [
                Activity(id="a4", destination="Paris", name="Eiffel Tower Visit", price=25, style_tags=["romance", "culture"]),
                Activity(id="a5", destination="Paris", name="Louvre Museum", price=17, style_tags=["culture", "art"]),
                Activity(id="a6", destination="Paris", name="Seine River Cruise", price=15, style_tags=["romance"]),
                Activity(id="a20", destination="Paris", name="Montmartre Art Walk", price=35, style_tags=["culture", "art", "romance"]),
                Activity(id="a21", destination="Paris", name="French Pastry Workshop", price=95, style_tags=["food", "culture"]),
                Activity(id="a23", destination="Paris", name="Champagne Tasting", price=120, style_tags=["luxury", "romance", "food"]),
            ],
        },
        "Bali": {
            "flights": [
                Flight(id="f5", destination="Bali", price=700, airline="Garuda", duration_hours=18, style_tags=["adventure", "nature"]),
                Flight(id="f6", destination="Bali", price=850, airline="Singapore", duration_hours=16, style_tags=["luxury", "nature"]),
                Flight(id="f20", destination="Bali", price=620, airline="AirAsia", duration_hours=20, style_tags=["budget", "adventure"]),
                Flight(id="f21", destination="Bali", price=760, airline="Qatar Airways", duration_hours=17.5, style_tags=["luxury", "nature"]),
                Flight(id="f22", destination="Bali", price=690, airline="Thai Airways", duration_hours=18.5, style_tags=["culture", "nature"]),
                Flight(id="f24", destination="Bali", price=580, airline="Scoot", duration_hours=21, style_tags=["budget", "adventure"]),
            ],
            "hotels": [
                Hotel(id="h5", destination="Bali", name="Ubud Jungle Resort", price_per_night=90, stars=3, style_tags=["nature", "adventure"]),
                Hotel(id="h6", destination="Bali", name="Seminyak Beach Villa", price_per_night=200, stars=4, style_tags=["luxury", "nature"]),
                Hotel(id="h20", destination="Bali", name="Canggu Surf House", price_per_night=65, stars=3, style_tags=["budget", "adventure"]),
                Hotel(id="h21", destination="Bali", name="Uluwatu Cliff Villas", price_per_night=320, stars=5, style_tags=["luxury", "romance", "nature"]),
                Hotel(id="h24", destination="Bali", name="Nusa Dua Spa Palace", price_per_night=260, stars=5, style_tags=["luxury", "romance"]),
                Hotel(id="h25", destination="Bali", name="Kuta Budget Inn", price_per_night=45, stars=2, style_tags=["budget", "food"]),
            ],
            "activities": [
                Activity(id="a7", destination="Bali", name="Rice Terrace Trek", price=20, style_tags=["adventure", "nature"]),
                Activity(id="a8", destination="Bali", name="Temple Ceremony", price=10, style_tags=["culture", "nature"]),
                Activity(id="a9", destination="Bali", name="Surf Lesson", price=45, style_tags=["adventure"]),
                Activity(id="a26", destination="Bali", name="Ubud Cooking Class", price=55, style_tags=["food", "culture"]),
                Activity(id="a27", destination="Bali", name="Mount Batur Sunrise Hike", price=70, style_tags=["adventure", "nature"]),
                Activity(id="a30", destination="Bali", name="Balinese Spa Ritual", price=85, style_tags=["luxury", "romance"]),
            ],
        },
        "New York": {
            "flights": [
                Flight(id="f7", destination="New York", price=300, airline="Delta", duration_hours=6, style_tags=["culture", "food"]),
                Flight(id="f8", destination="New York", price=420, airline="JetBlue", duration_hours=6, style_tags=["luxury", "culture"]),
                Flight(id="f25", destination="New York", price=250, airline="Spirit", duration_hours=6.5, style_tags=["budget"]),
                Flight(id="f26", destination="New York", price=360, airline="United", duration_hours=6.2, style_tags=["culture", "food"]),
                Flight(id="f27", destination="New York", price=520, airline="American Airlines", duration_hours=5.8, style_tags=["luxury", "culture"]),
                Flight(id="f28", destination="New York", price=610, airline="Delta One", duration_hours=5.6, style_tags=["luxury", "food"]),
            ],
            "hotels": [
                Hotel(id="h7", destination="New York", name="Times Square Hotel", price_per_night=180, stars=3, style_tags=["culture", "food"]),
                Hotel(id="h8", destination="New York", name="The Plaza", price_per_night=600, stars=5, style_tags=["luxury"]),
                Hotel(id="h26", destination="New York", name="Pod Times Square", price_per_night=135, stars=3, style_tags=["budget", "culture"]),
                Hotel(id="h27", destination="New York", name="SoHo Grand", price_per_night=320, stars=4, style_tags=["luxury", "food", "culture"]),
                Hotel(id="h29", destination="New York", name="Central Park West Suites", price_per_night=420, stars=4, style_tags=["luxury", "nature"]),
                Hotel(id="h31", destination="New York", name="Bowery Budget Stay", price_per_night=95, stars=2, style_tags=["budget", "food"]),
            ],
            "activities": [
                Activity(id="a10", destination="New York", name="Central Park Walk", price=0, style_tags=["nature", "culture"]),
                Activity(id="a11", destination="New York", name="Broadway Show", price=120, style_tags=["culture", "art"]),
                Activity(id="a12", destination="New York", name="Food Tour", price=65, style_tags=["food", "culture"]),
                Activity(id="a33", destination="New York", name="Statue of Liberty Ferry", price=25, style_tags=["culture"]),
                Activity(id="a34", destination="New York", name="Brooklyn Pizza Crawl", price=70, style_tags=["food", "culture"]),
                Activity(id="a38", destination="New York", name="Rooftop Fine Dining", price=160, style_tags=["luxury", "food"]),
            ],
        },
        "Kyoto": {
            "flights": [
                Flight(id="f30", destination="Kyoto", price=680, airline="ANA", duration_hours=14, style_tags=["culture", "food"]),
                Flight(id="f31", destination="Kyoto", price=790, airline="Japan Airlines", duration_hours=12.5, style_tags=["luxury", "culture"]),
                Flight(id="f32", destination="Kyoto", price=560, airline="Korean Air", duration_hours=15, style_tags=["budget", "adventure"]),
                Flight(id="f33", destination="Kyoto", price=980, airline="Singapore Airlines", duration_hours=13, style_tags=["luxury", "food"]),
                Flight(id="f34", destination="Kyoto", price=720, airline="Cathay Pacific", duration_hours=13.5, style_tags=["culture", "food"]),
                Flight(id="f35", destination="Kyoto", price=610, airline="Korean Air", duration_hours=14.2, style_tags=["budget", "culture"]),
            ],
            "hotels": [
                Hotel(id="h32", destination="Kyoto", name="Kyoto Machiya Stay", price_per_night=130, stars=3, style_tags=["culture", "romance"]),
                Hotel(id="h34", destination="Kyoto", name="Hakone Ryokan Retreat", price_per_night=260, stars=4, style_tags=["nature", "romance"]),
                Hotel(id="h35", destination="Kyoto", name="Kyoto Luxury Tower", price_per_night=520, stars=5, style_tags=["luxury", "culture"]),
                Hotel(id="h36", destination="Kyoto", name="Arashiyama Bamboo Hotel", price_per_night=200, stars=4, style_tags=["nature", "romance"]),
                Hotel(id="h37", destination="Kyoto", name="Gion Geisha House Inn", price_per_night=280, stars=4, style_tags=["culture", "romance"]),
                Hotel(id="h38", destination="Kyoto", name="Temple Gateway Hostel", price_per_night=50, stars=2, style_tags=["budget", "culture"]),
            ],
            "activities": [
                Activity(id="a40", destination="Kyoto", name="Kyoto Temple Walk", price=25, style_tags=["culture", "nature"]),
                Activity(id="a41", destination="Kyoto", name="Geisha Dinner Show", price=150, style_tags=["culture", "romance"]),
                Activity(id="a42", destination="Kyoto", name="Nara Deer Park Day Trip", price=45, style_tags=["nature", "culture"]),
                Activity(id="a43", destination="Kyoto", name="Bamboo Grove Hike", price=40, style_tags=["adventure", "nature"]),
                Activity(id="a44", destination="Kyoto", name="Traditional Tea Ceremony", price=85, style_tags=["culture", "romance"]),
                Activity(id="a45", destination="Kyoto", name="Sake Tasting Tour", price=95, style_tags=["food", "culture"]),
            ],
        },
        "London": {
            "flights": [
                Flight(id="f54", destination="London", price=420, airline="British Airways", duration_hours=7, style_tags=["culture", "luxury"]),
                Flight(id="f55", destination="London", price=350, airline="Norse Atlantic", duration_hours=7.5, style_tags=["budget", "culture"]),
                Flight(id="f56", destination="London", price=510, airline="Virgin Atlantic", duration_hours=6.8, style_tags=["food", "luxury"]),
                Flight(id="f57", destination="London", price=460, airline="Aer Lingus", duration_hours=8, style_tags=["nature", "culture"]),
                Flight(id="f58", destination="London", price=380, airline="KLM", duration_hours=7.3, style_tags=["culture", "food"]),
                Flight(id="f59", destination="London", price=490, airline="Lufthansa", duration_hours=7.8, style_tags=["luxury", "culture"]),
            ],
            "hotels": [
                Hotel(id="h56", destination="London", name="London Covent Garden Hotel", price_per_night=210, stars=4, style_tags=["culture", "food"]),
                Hotel(id="h57", destination="London", name="Kensington Palace Hotel", price_per_night=280, stars=4, style_tags=["luxury", "culture"]),
                Hotel(id="h58", destination="London", name="South Bank Penthouse", price_per_night=320, stars=5, style_tags=["luxury", "nature"]),
                Hotel(id="h59", destination="London", name="Tower Bridge View Inn", price_per_night=150, stars=3, style_tags=["culture", "adventure"]),
                Hotel(id="h60", destination="London", name="Bloomsbury Budget Lodge", price_per_night=85, stars=2, style_tags=["budget", "culture"]),
                Hotel(id="h61", destination="London", name="Notting Hill Townhouse", price_per_night=240, stars=4, style_tags=["culture", "food"]),
            ],
            "activities": [
                Activity(id="a70", destination="London", name="London Theatre Night", price=95, style_tags=["culture", "romance"]),
                Activity(id="a71", destination="London", name="British Museum Highlights", price=0, style_tags=["culture", "art"]),
                Activity(id="a72", destination="London", name="Tower of London Tour", price=40, style_tags=["culture", "adventure"]),
                Activity(id="a73", destination="London", name="Thames River Cruise", price=50, style_tags=["romance", "nature"]),
                Activity(id="a74", destination="London", name="London Food Market Crawl", price=65, style_tags=["food", "culture"]),
                Activity(id="a75", destination="London", name="Harry Potter Studio Tour", price=55, style_tags=["culture", "art"]),
            ],
        },
        "Barcelona": {
            "flights": [
                Flight(id="f50", destination="Barcelona", price=390, airline="Iberia", duration_hours=8.5, style_tags=["culture", "food"]),
                Flight(id="f51", destination="Barcelona", price=340, airline="LEVEL", duration_hours=9.2, style_tags=["budget", "culture"]),
                Flight(id="f52", destination="Barcelona", price=620, airline="British Airways", duration_hours=8, style_tags=["luxury", "food"]),
                Flight(id="f53", destination="Barcelona", price=520, airline="Air Europa", duration_hours=8.8, style_tags=["romance", "culture"]),
                Flight(id="f60", destination="Barcelona", price=450, airline="Vueling", duration_hours=8.3, style_tags=["culture", "food"]),
                Flight(id="f61", destination="Barcelona", price=380, airline="Ryanair", duration_hours=9, style_tags=["budget", "adventure"]),
            ],
            "hotels": [
                Hotel(id="h52", destination="Barcelona", name="Barcelona Gothic Quarter Hotel", price_per_night=145, stars=3, style_tags=["culture", "food"]),
                Hotel(id="h53", destination="Barcelona", name="Sagrada Familia Suites", price_per_night=190, stars=4, style_tags=["art", "culture"]),
                Hotel(id="h54", destination="Barcelona", name="Montjuic Palace", price_per_night=280, stars=5, style_tags=["luxury", "culture"]),
                Hotel(id="h55", destination="Barcelona", name="Port Vell Beachfront", price_per_night=240, stars=4, style_tags=["romance", "nature"]),
                Hotel(id="h62", destination="Barcelona", name="Eixample Modern Inn", price_per_night=120, stars=3, style_tags=["culture", "food"]),
                Hotel(id="h63", destination="Barcelona", name="Las Ramblas Budget Stay", price_per_night=75, stars=2, style_tags=["budget", "culture"]),
            ],
            "activities": [
                Activity(id="a65", destination="Barcelona", name="Barcelona Tapas Tour", price=70, style_tags=["food", "culture"]),
                Activity(id="a66", destination="Barcelona", name="Sagrada Familia Visit", price=45, style_tags=["art", "culture"]),
                Activity(id="a67", destination="Barcelona", name="Flamenco Night", price=85, style_tags=["romance", "culture"]),
                Activity(id="a68", destination="Barcelona", name="Park Güell Hike", price=55, style_tags=["adventure", "nature"]),
                Activity(id="a69", destination="Barcelona", name="Gothic Quarter Walk", price=30, style_tags=["culture", "history"]),
                Activity(id="a76", destination="Barcelona", name="Montjuic Cable Car Experience", price=25, style_tags=["nature", "culture"]),
            ],
        },
        "Rome": {
            "flights": [
                Flight(id="f38", destination="Rome", price=470, airline="ITA Airways", duration_hours=9, style_tags=["culture", "food"]),
                Flight(id="f39", destination="Rome", price=420, airline="Norse Atlantic", duration_hours=10.5, style_tags=["budget", "adventure"]),
                Flight(id="f40", destination="Rome", price=700, airline="Lufthansa", duration_hours=9.5, style_tags=["luxury", "culture"]),
                Flight(id="f41", destination="Rome", price=560, airline="Turkish Airlines", duration_hours=11, style_tags=["food", "romance"]),
                Flight(id="f62", destination="Rome", price=510, airline="Alitalia", duration_hours=10.2, style_tags=["culture", "food"]),
                Flight(id="f63", destination="Rome", price=380, airline="easyJet", duration_hours=10.8, style_tags=["budget", "culture"]),
            ],
            "hotels": [
                Hotel(id="h40", destination="Rome", name="Rome Trastevere Hotel", price_per_night=140, stars=3, style_tags=["culture", "food"]),
                Hotel(id="h41", destination="Rome", name="Colosseum View Suites", price_per_night=220, stars=4, style_tags=["culture", "luxury"]),
                Hotel(id="h42", destination="Rome", name="Vatican City Luxury Tower", price_per_night=380, stars=5, style_tags=["luxury", "culture"]),
                Hotel(id="h43", destination="Rome", name="Spanish Steps Inn", price_per_night=160, stars=3, style_tags=["culture", "romance"]),
                Hotel(id="h64", destination="Rome", name="Roman Forum Guesthouse", price_per_night=95, stars=2, style_tags=["budget", "culture"]),
                Hotel(id="h65", destination="Rome", name="Pantheon Classic Inn", price_per_night=180, stars=4, style_tags=["culture", "food"]),
            ],
            "activities": [
                Activity(id="a50", destination="Rome", name="Rome Ancient Sites Walk", price=35, style_tags=["culture"]),
                Activity(id="a51", destination="Rome", name="Vatican Museums Tour", price=55, style_tags=["art", "culture"]),
                Activity(id="a52", destination="Rome", name="Italian Cooking Class", price=95, style_tags=["food", "romance"]),
                Activity(id="a53", destination="Rome", name="Colosseum Night Tour", price=75, style_tags=["adventure", "culture"]),
                Activity(id="a54", destination="Rome", name="Rome Pizza & Pasta Tour", price=60, style_tags=["food", "culture"]),
                Activity(id="a77", destination="Rome", name="Trevi Fountain Sunset", price=0, style_tags=["romance", "culture"]),
            ],
        },
        "Bangkok": {
            "flights": [
                Flight(id="f46", destination="Bangkok", price=590, airline="Thai Airways", duration_hours=17, style_tags=["culture", "food"]),
                Flight(id="f47", destination="Bangkok", price=510, airline="AirAsia", duration_hours=19, style_tags=["budget", "adventure"]),
                Flight(id="f48", destination="Bangkok", price=780, airline="Singapore Airlines", duration_hours=16, style_tags=["luxury", "food"]),
                Flight(id="f49", destination="Bangkok", price=650, airline="Qatar Airways", duration_hours=18, style_tags=["nature", "culture"]),
                Flight(id="f78", destination="Bangkok", price=620, airline="Emirates", duration_hours=17.5, style_tags=["luxury", "food"]),
                Flight(id="f79", destination="Bangkok", price=540, airline="Scoot", duration_hours=19.5, style_tags=["budget", "adventure"]),
            ],
            "hotels": [
                Hotel(id="h48", destination="Bangkok", name="Bangkok Riverside Hotel", price_per_night=95, stars=3, style_tags=["budget", "food"]),
                Hotel(id="h49", destination="Bangkok", name="Silom District Luxury", price_per_night=180, stars=4, style_tags=["luxury", "food"]),
                Hotel(id="h50", destination="Bangkok", name="Chao Phraya River Palace", price_per_night=250, stars=5, style_tags=["luxury", "romance"]),
                Hotel(id="h51", destination="Bangkok", name="Backpacker Hostel Central", price_per_night=35, stars=2, style_tags=["budget", "adventure"]),
                Hotel(id="h66", destination="Bangkok", name="Thai Boutique Inn", price_per_night=145, stars=3, style_tags=["culture", "food"]),
                Hotel(id="h67", destination="Bangkok", name="Sukhumvit Modern Suite", price_per_night=200, stars=4, style_tags=["luxury", "culture"]),
            ],
            "activities": [
                Activity(id="a60", destination="Bangkok", name="Bangkok Street Food Crawl", price=45, style_tags=["food", "culture"]),
                Activity(id="a61", destination="Bangkok", name="Grand Palace Tour", price=35, style_tags=["culture", "art"]),
                Activity(id="a62", destination="Bangkok", name="Floating Market Boat Trip", price=60, style_tags=["adventure", "food"]),
                Activity(id="a63", destination="Bangkok", name="Thai Cooking Class", price=55, style_tags=["food", "culture"]),
                Activity(id="a64", destination="Bangkok", name="Temple Sunrise Tour", price=25, style_tags=["culture", "romance"]),
                Activity(id="a80", destination="Bangkok", name="Thai Massage Workshop", price=50, style_tags=["luxury", "romance"]),
            ],
        },
        "Dubai": {
            "flights": [
                Flight(id="f80", destination="Dubai", price=650, airline="Emirates", duration_hours=14, style_tags=["luxury", "food"]),
                Flight(id="f81", destination="Dubai", price=520, airline="FlyDubai", duration_hours=15, style_tags=["budget", "adventure"]),
                Flight(id="f82", destination="Dubai", price=810, airline="Etihad Airways", duration_hours=13.5, style_tags=["luxury", "culture"]),
                Flight(id="f83", destination="Dubai", price=600, airline="Air Arabia", duration_hours=16, style_tags=["budget", "food"]),
                Flight(id="f84", destination="Dubai", price=720, airline="Qatar Airways", duration_hours=14.5, style_tags=["luxury", "culture"]),
                Flight(id="f85", destination="Dubai", price=470, airline="Flydubai", duration_hours=15.2, style_tags=["budget", "nature"]),
            ],
            "hotels": [
                Hotel(id="h68", destination="Dubai", name="Burj Khalifa Suites", price_per_night=450, stars=5, style_tags=["luxury", "food"]),
                Hotel(id="h69", destination="Dubai", name="Palm Jumeirah Beach Resort", price_per_night=380, stars=5, style_tags=["luxury", "romance"]),
                Hotel(id="h70", destination="Dubai", name="Dubai Marina Hotel", price_per_night=220, stars=4, style_tags=["luxury", "culture"]),
                Hotel(id="h71", destination="Dubai", name="Old Town Budget Inn", price_per_night=110, stars=3, style_tags=["budget", "culture"]),
                Hotel(id="h72", destination="Dubai", name="Arabian Gulf Tower", price_per_night=190, stars=4, style_tags=["nature", "romance"]),
                Hotel(id="h73", destination="Dubai", name="Backpacker Oasis", price_per_night=45, stars=2, style_tags=["budget", "adventure"]),
            ],
            "activities": [
                Activity(id="a85", destination="Dubai", name="Burj Khalifa Summit", price=110, style_tags=["luxury", "culture"]),
                Activity(id="a86", destination="Dubai", name="Desert Safari & BBQ", price=95, style_tags=["adventure", "food"]),
                Activity(id="a87", destination="Dubai", name="Dubai Mall Luxury Tour", price=0, style_tags=["culture", "food"]),
                Activity(id="a88", destination="Dubai", name="Gold Souk Treasure Hunt", price=40, style_tags=["culture", "adventure"]),
                Activity(id="a89", destination="Dubai", name="Yacht Sunset Cruise", price=120, style_tags=["luxury", "romance"]),
                Activity(id="a90", destination="Dubai", name="Dune Bashing Experience", price=85, style_tags=["adventure", "nature"]),
            ],
        },
        "Amsterdam": {
            "flights": [
                Flight(id="f86", destination="Amsterdam", price=410, airline="KLM", duration_hours=8, style_tags=["culture", "romance"]),
                Flight(id="f87", destination="Amsterdam", price=360, airline="Transavia", duration_hours=8.5, style_tags=["budget", "culture"]),
                Flight(id="f88", destination="Amsterdam", price=580, airline="Air France", duration_hours=7.8, style_tags=["luxury", "culture"]),
                Flight(id="f89", destination="Amsterdam", price=480, airline="Lufthansa", duration_hours=8.2, style_tags=["food", "culture"]),
                Flight(id="f90", destination="Amsterdam", price=350, airline="easyJet", duration_hours=9, style_tags=["budget", "adventure"]),
                Flight(id="f91", destination="Amsterdam", price=520, airline="Air Europa", duration_hours=8.3, style_tags=["culture", "food"]),
            ],
            "hotels": [
                Hotel(id="h74", destination="Amsterdam", name="Canal Palace Hotel", price_per_night=180, stars=4, style_tags=["romance", "culture"]),
                Hotel(id="h75", destination="Amsterdam", name="Jordaan Boutique Inn", price_per_night=160, stars=3, style_tags=["culture", "food"]),
                Hotel(id="h76", destination="Amsterdam", name="Amsterdam Museum Hotel", price_per_night=220, stars=4, style_tags=["art", "culture"]),
                Hotel(id="h77", destination="Amsterdam", name="Budget Backpackers", price_per_night=65, stars=2, style_tags=["budget", "adventure"]),
                Hotel(id="h78", destination="Amsterdam", name="Red Light District Inn", price_per_night=140, stars=3, style_tags=["culture", "food"]),
                Hotel(id="h79", destination="Amsterdam", name="Anne Frank House Hotel", price_per_night=170, stars=4, style_tags=["culture", "romance"]),
            ],
            "activities": [
                Activity(id="a91", destination="Amsterdam", name="Canal Boat Tour", price=30, style_tags=["romance", "culture"]),
                Activity(id="a92", destination="Amsterdam", name="Anne Frank House Tour", price=40, style_tags=["culture", "art"]),
                Activity(id="a93", destination="Amsterdam", name="Bike City Ride", price=25, style_tags=["adventure", "culture"]),
                Activity(id="a94", destination="Amsterdam", name="Dutch Cheese Tasting", price=55, style_tags=["food", "culture"]),
                Activity(id="a95", destination="Amsterdam", name="Rijksmuseum Highlights", price=35, style_tags=["art", "culture"]),
                Activity(id="a96", destination="Amsterdam", name="Amsterdam Food Market Tour", price=65, style_tags=["food", "culture"]),
            ],
        },
        "Athens": {
            "flights": [
                Flight(id="f92", destination="Athens", price=520, airline="Aegean Airlines", duration_hours=10, style_tags=["culture", "romance"]),
                Flight(id="f93", destination="Athens", price=460, airline="Norse Atlantic", duration_hours=11.5, style_tags=["budget", "nature"]),
                Flight(id="f94", destination="Athens", price=740, airline="Emirates", duration_hours=10.5, style_tags=["luxury", "romance"]),
                Flight(id="f95", destination="Athens", price=610, airline="Turkish Airlines", duration_hours=11, style_tags=["food", "culture"]),
                Flight(id="f96", destination="Athens", price=380, airline="easyJet", duration_hours=11.5, style_tags=["budget", "culture"]),
                Flight(id="f97", destination="Athens", price=650, airline="Air France", duration_hours=10.3, style_tags=["luxury", "culture"]),
            ],
            "hotels": [
                Hotel(id="h80", destination="Athens", name="Athens Plaka Hotel", price_per_night=120, stars=3, style_tags=["culture", "budget"]),
                Hotel(id="h81", destination="Athens", name="Acropolis View Suites", price_per_night=200, stars=4, style_tags=["luxury", "culture"]),
                Hotel(id="h82", destination="Athens", name="Syntagma Luxury Hotel", price_per_night=280, stars=5, style_tags=["luxury", "food"]),
                Hotel(id="h83", destination="Athens", name="Monastiraki Budget Inn", price_per_night=75, stars=2, style_tags=["budget", "culture"]),
                Hotel(id="h84", destination="Athens", name="Psyrri Art Hotel", price_per_night=140, stars=3, style_tags=["art", "culture"]),
                Hotel(id="h85", destination="Athens", name="Glyfada Seaside Resort", price_per_night=190, stars=4, style_tags=["nature", "romance"]),
            ],
            "activities": [
                Activity(id="a97", destination="Athens", name="Acropolis Guided Walk", price=35, style_tags=["culture"]),
                Activity(id="a98", destination="Athens", name="Athens Food Tour", price=70, style_tags=["food", "culture"]),
                Activity(id="a99", destination="Athens", name="Delphi Day Trip", price=85, style_tags=["culture", "adventure"]),
                Activity(id="a100", destination="Athens", name="Greek Cooking Class", price=90, style_tags=["food", "culture"]),
                Activity(id="a101", destination="Athens", name="Panathenaic Stadium Tour", price=25, style_tags=["culture", "adventure"]),
                Activity(id="a102", destination="Athens", name="Sunset in Santorini Ferry", price=110, style_tags=["romance", "nature"]),
            ],
        },
        "Singapore": {
            "flights": [
                Flight(id="f98", destination="Singapore", price=680, airline="Singapore Airlines", duration_hours=18, style_tags=["luxury", "food"]),
                Flight(id="f99", destination="Singapore", price=550, airline="AirAsia", duration_hours=19.5, style_tags=["budget", "adventure"]),
                Flight(id="f100", destination="Singapore", price=820, airline="Cathay Pacific", duration_hours=17, style_tags=["luxury", "culture"]),
                Flight(id="f101", destination="Singapore", price=710, airline="Thai Airways", duration_hours=18.5, style_tags=["culture", "food"]),
                Flight(id="f102", destination="Singapore", price=490, airline="Scoot", duration_hours=20, style_tags=["budget", "adventure"]),
                Flight(id="f103", destination="Singapore", price=600, airline="Emirates", duration_hours=17.5, style_tags=["luxury", "romance"]),
            ],
            "hotels": [
                Hotel(id="h86", destination="Singapore", name="Marina Bay Luxury Towers", price_per_night=380, stars=5, style_tags=["luxury", "food"]),
                Hotel(id="h87", destination="Singapore", name="Sentosa Beach Resort", price_per_night=240, stars=4, style_tags=["nature", "romance"]),
                Hotel(id="h88", destination="Singapore", name="Orchard Road Inn", price_per_night=170, stars=4, style_tags=["culture", "food"]),
                Hotel(id="h89", destination="Singapore", name="Chinatown Budget Stay", price_per_night=80, stars=2, style_tags=["budget", "culture"]),
                Hotel(id="h90", destination="Singapore", name="Little India Hotel", price_per_night=135, stars=3, style_tags=["culture", "food"]),
                Hotel(id="h91", destination="Singapore", name="Gardens by Bay View", price_per_night=220, stars=4, style_tags=["luxury", "nature"]),
            ],
            "activities": [
                Activity(id="a103", destination="Singapore", name="Gardens by Bay Night Show", price=40, style_tags=["culture", "art"]),
                Activity(id="a104", destination="Singapore", name="Marina Bay Sands Climb", price=70, style_tags=["adventure", "nature"]),
                Activity(id="a105", destination="Singapore", name="Singapore Food Tour", price=60, style_tags=["food", "culture"]),
                Activity(id="a106", destination="Singapore", name="Universal Studios Day", price=95, style_tags=["adventure", "culture"]),
                Activity(id="a107", destination="Singapore", name="Sentosa Beach Day", price=50, style_tags=["nature", "romance"]),
                Activity(id="a108", destination="Singapore", name="Night Safari Experience", price=85, style_tags=["adventure", "nature"]),
            ],
        },
        "Mexico City": {
            "flights": [
                Flight(id="f104", destination="Mexico City", price=320, airline="Aeromexico", duration_hours=5, style_tags=["culture", "food"]),
                Flight(id="f105", destination="Mexico City", price=280, airline="Viva Aerobus", duration_hours=5.5, style_tags=["budget", "adventure"]),
                Flight(id="f106", destination="Mexico City", price=480, airline="Delta", duration_hours=5.2, style_tags=["luxury", "food"]),
                Flight(id="f107", destination="Mexico City", price=390, airline="United", duration_hours=5.8, style_tags=["nature", "culture"]),
                Flight(id="f108", destination="Mexico City", price=450, airline="American Airlines", duration_hours=5.3, style_tags=["culture", "food"]),
                Flight(id="f109", destination="Mexico City", price=340, airline="Southwest", duration_hours=6, style_tags=["budget", "food"]),
            ],
            "hotels": [
                Hotel(id="h92", destination="Mexico City", name="Mexico City Roma Hotel", price_per_night=110, stars=3, style_tags=["food", "culture"]),
                Hotel(id="h93", destination="Mexico City", name="Condesa Boutique Inn", price_per_night=160, stars=4, style_tags=["culture", "food"]),
                Hotel(id="h94", destination="Mexico City", name="Polanco Luxury Suites", price_per_night=280, stars=5, style_tags=["luxury", "culture"]),
                Hotel(id="h95", destination="Mexico City", name="Centro Budget Stay", price_per_night=75, stars=2, style_tags=["budget", "culture"]),
                Hotel(id="h96", destination="Mexico City", name="San Angel Art Hotel", price_per_night=140, stars=3, style_tags=["art", "culture"]),
                Hotel(id="h97", destination="Mexico City", name="Coyoacan Cultural Inn", price_per_night=130, stars=3, style_tags=["culture", "romance"]),
            ],
            "activities": [
                Activity(id="a109", destination="Mexico City", name="Mexico City Taco Tour", price=45, style_tags=["food", "culture"]),
                Activity(id="a110", destination="Mexico City", name="Teotihuacan Pyramids", price=65, style_tags=["culture", "adventure"]),
                Activity(id="a111", destination="Mexico City", name="Frida Kahlo Museum", price=50, style_tags=["art", "culture"]),
                Activity(id="a112", destination="Mexico City", name="Xochimilco Floating Gardens", price=55, style_tags=["nature", "culture"]),
                Activity(id="a113", destination="Mexico City", name="Lucha Libre Wrestling Show", price=40, style_tags=["culture", "adventure"]),
                Activity(id="a114", destination="Mexico City", name="Templo Mayor Ruins", price=35, style_tags=["culture", "history"]),
            ],
        },
        "Tel Aviv": {
            "flights": [
                Flight(id="f110", destination="Tel Aviv", price=520, airline="El Al", duration_hours=11, style_tags=["culture", "food"]),
                Flight(id="f111", destination="Tel Aviv", price=470, airline="Arkia", duration_hours=11.5, style_tags=["budget", "culture"]),
                Flight(id="f112", destination="Tel Aviv", price=680, airline="United", duration_hours=10.8, style_tags=["luxury", "culture"]),
                Flight(id="f113", destination="Tel Aviv", price=590, airline="Turkish Airlines", duration_hours=12, style_tags=["food", "romance"]),
                Flight(id="f114", destination="Tel Aviv", price=610, airline="Lufthansa", duration_hours=11.5, style_tags=["luxury", "food"]),
                Flight(id="f115", destination="Tel Aviv", price=400, airline="Wizz Air", duration_hours=12.5, style_tags=["budget", "adventure"]),
            ],
            "hotels": [
                Hotel(id="h98", destination="Tel Aviv", name="Tel Aviv Beach Hotel", price_per_night=180, stars=4, style_tags=["food", "romance"]),
                Hotel(id="h99", destination="Tel Aviv", name="Hilton Tel Aviv", price_per_night=250, stars=5, style_tags=["luxury", "food"]),
                Hotel(id="h100", destination="Tel Aviv", name="Jaffa Port Inn", price_per_night=140, stars=3, style_tags=["culture", "romance"]),
                Hotel(id="h101", destination="Tel Aviv", name="Old City Guesthouse", price_per_night=95, stars=2, style_tags=["budget", "culture"]),
                Hotel(id="h102", destination="Tel Aviv", name="Bauhaus Design Hotel", price_per_night=170, stars=4, style_tags=["art", "culture"]),
                Hotel(id="h103", destination="Tel Aviv", name="Kibbutz Stay Experience", price_per_night=85, stars=3, style_tags=["nature", "culture"]),
            ],
            "activities": [
                Activity(id="a115", destination="Tel Aviv", name="Tel Aviv Beach Day", price=0, style_tags=["nature", "romance"]),
                Activity(id="a116", destination="Tel Aviv", name="Old Jaffa Food Tour", price=70, style_tags=["food", "culture"]),
                Activity(id="a117", destination="Tel Aviv", name="Dead Sea Float Day", price=90, style_tags=["nature", "luxury"]),
                Activity(id="a118", destination="Tel Aviv", name="Tel Aviv Street Art Tour", price=45, style_tags=["art", "culture"]),
                Activity(id="a119", destination="Tel Aviv", name="Israeli Wine Tasting", price=85, style_tags=["food", "culture"]),
                Activity(id="a120", destination="Tel Aviv", name="Negev Desert Jeep Tour", price=120, style_tags=["adventure", "nature"]),
            ],
        },
    }

    STATIC_DATA.update(destinations)


_build_catalog()
