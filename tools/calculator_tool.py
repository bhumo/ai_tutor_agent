def extract_expression(text):
    """
    From a given text, extract the mathematical expression.
    Args:
        text (str): The input text containing a mathematical expression."""


def evaluate_expression(expr):
    print(f"Evaluating expression: {expr}")
    try:
        return eval(expr)
    except Exception:

        return "Unable to evaluate the expression."