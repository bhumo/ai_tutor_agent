import yaml
import google.generativeai as genai
import os
from pathlib import Path
def load_gemini_api_key():
    """
    Load the Gemini API key from a YAML file and set it in the environment variables.
    """
    # Load the API key from the YAML file
    filename = 'gemini_api_key.yaml'
    base_path = Path(__file__).resolve().parent.parent  # goes up to ai-tutor/
    file_path = base_path / 'api_keys' / 'gemini_api_key.yaml'
    with open(file_path, 'r') as file:
        config = yaml.safe_load(file)
        api_key = config['gemini']['api_key']
    
    return api_key
    

def set_gemini_api_key():
    """
    Set the Gemini API key in the environment variables and initialize the Gemini API client.
    """
    # Load the API key  
    api_key = load_gemini_api_key()
    # Set the API key in the environment variables
    os.environ['GOOGLE_API_KEY'] = api_key
    # Initialize the Gemini API client
    genai.configure(api_key=api_key)    
    