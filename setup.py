#!/usr/bin/env python3
"""
Setup script for AI Tutor Agent with Authentication
"""
import os
import secrets
from pathlib import Path

def create_env_file():
    """Create .env file with secure defaults"""
    env_path = Path('.env')
    
    if env_path.exists():
        print("✅ .env file already exists")
        return
    
    # Generate a secure secret key
    secret_key = secrets.token_urlsafe(32)
    
    env_content = f"""# AI Tutor Agent Configuration
SECRET_KEY={secret_key}
GEMINI_API_KEY=your-gemini-api-key-here

# Google OAuth (Optional)
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# Database (SQLite by default)
DATABASE_URL=sqlite:///./ai_tutor.db
"""
    
    env_path.write_text(env_content)
    print("✅ Created .env file with secure secret key")
    print("📝 Please update the .env file with your Gemini API key")

def create_directories():
    """Create necessary directories"""
    directories = [
        'uploads',
        'database'
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"✅ Created directory: {directory}")

def main():
    print("🚀 Setting up AI Tutor Agent with Authentication...")
    print()
    
    create_env_file()
    create_directories()
    
    print()
    print("🎉 Setup complete!")
    print()
    print("Next steps:")
    print("1. Update .env file with your Gemini API key")
    print("2. Install dependencies: pip install -r requirements.txt")
    print("3. Run the application: uvicorn main:app --reload")
    print("4. Visit http://localhost:8000/login to create an account")
    print()

if __name__ == "__main__":
    main()
