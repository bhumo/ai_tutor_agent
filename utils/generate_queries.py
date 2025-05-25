import google.generativeai as genai

def generate_gemini_query(prompt):
    """
    Generate a query using the Gemini API.
    Args:
        prompt (str): The prompt to generate a query for.
    Returns:
        str: The generated query.
    """  
    print("Generating query with Gemini API")
    # for model in genai.list_models():
    #     print(model.name, model.supported_generation_methods)
    # print("printing model")
    model = genai.GenerativeModel("gemini-2.5-flash-preview-05-20")
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Gemini API error: {str(e)}"