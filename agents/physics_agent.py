from tools.constant_look_up import lookup_constant
from utils.generate_queries import generate_gemini_query

def handle_physics_query(query):
    constant = lookup_constant(query)
    if constant:
        return f"Constant: {constant}"
    return generate_gemini_query(f"Answer this physics question: {query}")
