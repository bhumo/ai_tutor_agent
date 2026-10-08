"""
Simple test script to verify authentication setup
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.models import create_tables, SessionLocal, User
from auth.service import AuthService
from auth.schemas import UserCreate

def test_auth_system():
    print("🧪 Testing Authentication System...")
    
    # Create tables
    create_tables()
    print("✅ Database tables created")
    
    # Test user creation
    db = SessionLocal()
    try:
        # Create a test user
        test_user = UserCreate(
            email="test@example.com",
            password="testpassword123",
            full_name="Test User"
        )
        
        # Check if user already exists
        existing_user = AuthService.get_user_by_email(db, "test@example.com")
        if existing_user:
            print("✅ Test user already exists")
        else:
            user = AuthService.create_user(db, test_user)
            print(f"✅ Created test user: {user.email}")
        
        # Test authentication
        auth_user = AuthService.authenticate_user(db, "test@example.com", "testpassword123")
        if auth_user:
            print("✅ Authentication successful")
        else:
            print("❌ Authentication failed")
        
        print("🎉 Authentication system test completed!")
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    test_auth_system()
