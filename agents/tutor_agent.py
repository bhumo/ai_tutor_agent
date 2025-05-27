from tools.classify_intent import classify_intent
from agents.math_agent import handle_math_query
from agents.physics_agent import handle_physics_query

def tutor_agent(query):
    categories = ["math", "physics"]
    subject = classify_intent(query, categories)

    if subject == "math":
        print("Detected subject: math")
        return handle_math_query(query)

    elif subject == "physics":
        print("Detected subject: physics")
        return handle_physics_query(query)

    return "Sorry, I can't help with that topic yet."