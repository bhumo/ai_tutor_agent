from utils.generate_queries import generate_gemini_query

def classify_intent(query, categories):
    """
    The method takes two parameters: a query string and a list of categories.
    The methods uses the Gemini API to classify the query into one of the catrgories provided in the list
    :param query: The query string to classify. Query is ussually the user prompt.
    :param categories: A list of categories to classify the query into.
    :return: The category that the query belongs to, or None if no category matches
    """
    prompt = f"Classify the following question into one of these categories: {', '.join(categories)}.\n\nQuestion: '{query}'\n\nOnly respond with one of the category names."
    for _ in range(5):
        response = generate_gemini_query(prompt)
        cleaned_response = response.strip().lower()
        if cleaned_response in [cat.lower() for cat in categories]:
            return cleaned_response
    return None