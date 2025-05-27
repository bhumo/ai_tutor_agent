PHYSICS_CONSTANTS = {
    "speed of light": "3.00 × 10^8 m/s",
    "gravitational constant": "6.674 × 10^-11 N·m²/kg²",
    "planck constant": "6.626 × 10^-34 J·s",
}

def lookup_constant(query):
    query = query.lower()
    for key in PHYSICS_CONSTANTS:
        if key in query:
            return PHYSICS_CONSTANTS[key]
    return None