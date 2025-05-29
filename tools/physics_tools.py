from  langchain.tools  import tool
import json
import difflib  
import os
from pathlib import Path
@tool
def physics_constant_lookup(name: str) -> str:
    """Look up a physics constant by its name or symbol. Example: 'speed of light', 'c', 'h' or 'Planck's constant'"""
    try:
        base_path = Path(__file__).parent
        full_path = base_path / "data" / "physics_constants.json"
        # print(f"Full path: {full_path}")
        with open(full_path, "r") as f:
            data = json.load(f)
        
        target = name.strip().lower()
        if not target:
            return "Please provide a valid constant name or symbol."
        print(f"Looking up constant for: {target}")
        best_match_score = 0
        best_match = None
        # print(data)
        # print(data.get("constants", []))
        for constant in data.get("constants", []):
            for key in [constant["quantity"].lower(), constant["symbol"].lower()]:
                score = difflib.SequenceMatcher(None, target, key).ratio()
                if score > best_match_score:
                    best_match_score = score
                    best_match = constant
        
        if best_match and best_match_score >= 0.6:
            return f"{best_match['quantity']} ({best_match['symbol']}) f{best_match['value']} {best_match['unit']} (uncertainty: {best_match['uncertainty']})"
        else:
            return f"No close match found for '{name}'. Try using an exact name or symbol."
    except Exception as e:
        return f"Constant not found {name} and gave the following error: {e}"


@tool
def unit_converter(value: float, from_unit: str, to_unit: str) -> str:
    """Convert between common physics units. It takes a value, the unit to convert from and the unit to convert into. The units are in m. km, in, ft, kg, g and so on."""
   

    conversions = {
        "m": 1.0, "meter": 1.0, "meters": 1.0,
        "cm": 0.01, "centimeter": 0.01, "centimeters": 0.01,
        "mm": 0.001, "millimeter": 0.001, "millimeters": 0.001,
        "km": 1000, "kilometer": 1000, "kilometers": 1000,
        "in": 0.0254, "inch": 0.0254, "inches": 0.0254,
        "ft": 0.3048, "foot": 0.3048, "feet": 0.3048,
       "s": 1.0, "second": 1.0, "seconds": 1.0,
        "min": 60, "minute": 60, "minutes": 60,
        "hr": 3600, "hour": 3600, "hours": 3600,
        "j": 1.0, "joule": 1.0, "joules": 1.0,
        "kj": 1000, "kilojoule": 1000, "kilojoules": 1000,
        "cal": 4.184, "calorie": 4.184, "calories": 4.184,
        "ev": 1.602e-19, "electronvolt": 1.602e-19, "electronvolts": 1.602e-19,
        "kg": 1.0, "kilogram": 1.0, "kilograms": 1.0,
        "g": 0.001, "gram": 0.001, "grams": 0.001,
        "lb": 0.453592, "pound": 0.453592, "pounds": 0.453592,    
    }

    try:
        def fuzzy_match(unit):
            unit = unit.strip().lower()
            if unit in conversions:
                return unit
            close_matches = difflib.get_close_matches(unit, conversions.keys(), n=1, cutoff=0.7)
            return close_matches[0] if close_matches else None

        from_unit_key = fuzzy_match(from_unit)
        to_unit_key = fuzzy_match(to_unit)

        if from_unit_key and to_unit_key:
            base_value = value * conversions[from_unit_key]
            result = base_value / conversions[to_unit_key]
            return f"{value} {from_unit} = {result} {to_unit}"
        else:
            return f"Conversion from '{from_unit}' to '{to_unit}' not supported."
    except Exception as e:
        return f"Error: {str(e)}"
