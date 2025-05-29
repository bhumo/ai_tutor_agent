from langchain.tools import tool
from sympy import sympify


@tool
def calculator(expression: str) -> str:
    """ Evaluate simple math expressions. """
    print(f"Evaluating using Calculator: {expression}")
    try:
        result = sympify(expression).evalf()
        print(f"Result using calculator tool: {result}")
        return str(result)
    except Exception as e:
        return f"Error: {str(e)}"

