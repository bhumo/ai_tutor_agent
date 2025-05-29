# from langchain.agents import tool
# from sympy import sympify
# from utils.generate_queries import generate_gemini_query

# @tool
# def calculator(query):
#     result = evaluate_expression(query)
#     explanation = generate_gemini_query(f"Explain how to solve: {query}")
#     return f"Answer: {result}\nExplanation: {explanation}"

# def evaluate_expression(expr):
#     print(f"Evaluating expression: {expr}")
#     try:
#         return eval(expr)
#     except Exception:
#         try:
#             # Attempt to use sympy for more complex expressions
#             return sympify(expr)
#         except Exception:
#             return "Unable to evaluate the expression."