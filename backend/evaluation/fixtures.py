"""TEST FIXTURES ONLY.

These product documents are made up to exercise and measure the recommender. They are not Rainchem
documentation and must never be loaded into a real database. Real documents are added by an admin
in Admin > Product Knowledge and verified by a Head Admin."""

PRODUCTS = [
    # name, category, price
    ("TEST Moto 4T 10W-40", "Oils & Fluids", 450),
    ("TEST Moto 4T 20W-50", "Oils & Fluids", 430),
    ("TEST Auto 5W-30", "Oils & Fluids", 780),
    ("TEST Diesel 15W-40", "Oils & Fluids", 950),
    ("TEST 2T Motor Oil", "Oils & Fluids", 220),
    ("TEST Coolant Long Life", "Coolant", 350),
    ("TEST Gear Oil 80W-90", "Oils & Fluids", 520),
    ("TEST Brake Fluid DOT 4", "Brakes", 260),
    ("TEST Unverified Oil 10W-40", "Oils & Fluids", 400),
    ("TEST Unauthorised Oil 10W-40", "Oils & Fluids", 410),
    ("TEST Mystery Oil", "Oils & Fluids", 100),
]

# product name -> (title, type, version, source, content, facts, verified, authorized)
DOCUMENTS = {
    "TEST Moto 4T 10W-40": (
        "TDS Moto 4T 10W-40", "technical_data_sheet", "2024-03", "Test datasheet A",
        "Semi-synthetic engine oil for 4-stroke motorcycle and scooter engines.\n\nMeets API SN and JASO MA2. Suitable for wet clutch systems.\n\nNot intended for 2-stroke engines or diesel engines.",
        {"viscosity_grades": ["10W-40"], "standards": ["API SN", "JASO MA2"], "applications": ["engine oil", "4-stroke motorcycle engines", "scooters"],
         "equipment": ["motorcycle", "scooter"], "engine_types": ["4-stroke", "gasoline"], "compatible_with": ["wet clutch"],
         "not_for": ["2-stroke", "diesel"], "warnings": ["Do not mix with 2-stroke oil."]}, True, True),
    "TEST Moto 4T 20W-50": (
        "TDS Moto 4T 20W-50", "technical_data_sheet", "2023-11", "Test datasheet B",
        "Mineral engine oil for air-cooled 4-stroke motorcycle engines in hot climates.\n\nMeets API SL and JASO MA. Wet clutch safe.",
        {"viscosity_grades": ["20W-50"], "standards": ["API SL", "JASO MA"], "applications": ["engine oil", "air-cooled 4-stroke motorcycle engines"],
         "equipment": ["motorcycle"], "engine_types": ["4-stroke", "gasoline"], "compatible_with": ["wet clutch"], "not_for": ["2-stroke"]}, True, True),
    "TEST Auto 5W-30": (
        "TDS Auto 5W-30", "technical_data_sheet", "2024-06", "Test datasheet C",
        "Fully synthetic engine oil for modern gasoline passenger car engines.\n\nMeets API SP and ACEA C3. Not for motorcycles with wet clutches.",
        {"viscosity_grades": ["5W-30"], "standards": ["API SP", "ACEA C3"], "applications": ["engine oil", "gasoline passenger car engines"],
         "equipment": ["car"], "engine_types": ["gasoline"], "not_for": ["motorcycle"]}, True, True),
    "TEST Diesel 15W-40": (
        "TDS Diesel 15W-40", "technical_data_sheet", "2022-09", "Test datasheet D",
        "Heavy duty engine oil for turbocharged diesel engines in trucks and buses.\n\nMeets API CK-4.",
        {"viscosity_grades": ["15W-40"], "standards": ["API CK-4"], "applications": ["engine oil", "heavy duty diesel engines"],
         "equipment": ["truck"], "engine_types": ["diesel"], "compatible_with": ["turbo"], "not_for": ["motorcycle"]}, True, True),
    "TEST 2T Motor Oil": (
        "TDS 2T Motor Oil", "technical_data_sheet", "2023-02", "Test datasheet E",
        "Low smoke engine oil for 2-stroke motorcycle engines. Meets JASO FD. Mix with fuel as the manufacturer recommends.",
        {"standards": ["JASO FD"], "applications": ["engine oil", "2-stroke motorcycle engines"], "equipment": ["motorcycle"],
         "engine_types": ["2-stroke"], "not_for": ["4-stroke"]}, True, True),
    "TEST Coolant Long Life": (
        "TDS Coolant Long Life", "technical_data_sheet", "2024-01", "Test datasheet F",
        "Ethylene glycol coolant for liquid cooled engines in cars and motorcycles. Mix 50/50 with distilled water. Meets ASTM D3306.",
        {"standards": ["ASTM D3306"], "applications": ["coolant", "liquid cooled engines"], "equipment": ["car", "motorcycle"]}, True, True),
    "TEST Gear Oil 80W-90": (
        "TDS Gear Oil 80W-90", "technical_data_sheet", "2023-07", "Test datasheet G",
        "Hypoid gear oil for manual transmissions and differentials in cars and trucks. Meets API GL-5.",
        {"viscosity_grades": ["80W-90"], "standards": ["API GL-5"], "applications": ["gear oil", "differentials", "manual gearboxes"], "equipment": ["car", "truck"]}, True, True),
    "TEST Brake Fluid DOT 4": (
        "TDS Brake Fluid DOT 4", "technical_data_sheet", "2024-02", "Test datasheet H",
        "Glycol based brake fluid for disc and drum brake systems in cars and motorcycles. Meets DOT 4.",
        {"standards": ["DOT 4"], "applications": ["brake fluid", "hydraulic brake systems"], "equipment": ["car", "motorcycle"]}, True, True),
    "TEST Unverified Oil 10W-40": (
        "Draft sheet Unverified Oil", "technical_data_sheet", "draft", "Not checked",
        "Engine oil for 4-stroke motorcycles. Meets API SN and JASO MA2.",
        {"viscosity_grades": ["10W-40"], "standards": ["API SN", "JASO MA2"], "applications": ["engine oil"], "equipment": ["motorcycle"], "engine_types": ["4-stroke"]}, False, False),
    "TEST Unauthorised Oil 10W-40": (
        "Sheet Unauthorised Oil", "technical_data_sheet", "1", "Checked but not for chatbot use",
        "Engine oil for 4-stroke motorcycles. Meets API SN and JASO MA2.",
        {"viscosity_grades": ["10W-40"], "standards": ["API SN", "JASO MA2"], "applications": ["engine oil"], "equipment": ["motorcycle"], "engine_types": ["4-stroke"]}, True, False),
}
