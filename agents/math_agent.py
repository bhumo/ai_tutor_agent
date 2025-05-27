from tools.calculator_tool import evaluate_expression
from utils.generate_queries import generate_gemini_query

def handle_math_query(query):
    result = evaluate_expression(query)
    explanation = generate_gemini_query(f"Explain how to solve: {query}")
    return f"Answer: {result}\nExplanation: {explanation}"