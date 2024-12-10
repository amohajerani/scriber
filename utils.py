import openai
import re
from werkzeug.security import generate_password_hash
from typing import Tuple
import os
import hmac
import hashlib
from datetime import datetime


def create_user(email: str, password: str, db) -> Tuple[bool, str]:
    """
    Create a new provider with email and password in MongoDB.
    Returns a tuple of (success: bool, message: str)
    """
    # Check if provider already exists
    if db.providers.find_one({"email": email}):
        return False, "Email already exists"

    # Basic email validation
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return False, "Invalid email format"

    # Basic password validation (at least 8 characters)
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"

    try:
        # Hash the password
        hashed_password = hash_password(password)

        # Insert the new provider into MongoDB
        db.providers.insert_one({
            "email": email,
            "password": hashed_password,
            "created_at": datetime.now()
        })

        return True, "Provider account created successfully!"

    except Exception as e:
        return False, f"Error creating provider account: {str(e)}"


def hash_password(password: str) -> str:
    """Hash a password using SHA-256"""
    salt = os.getenv('PASSWORD_SALT', 'default_salt')
    return hmac.new(salt.encode(), password.encode(), hashlib.sha256).hexdigest()


def verify_user(email: str, password: str, db) -> str:
    """Verify provider credentials and return provider_id if successful"""
    provider = db.providers.find_one({"email": email})
    if not provider:
        return None

    hashed_password = hash_password(password)
    if hmac.compare_digest(provider['password'], hashed_password):
        return str(provider['_id'])
    return None


def get_summary(transcript, system_prompt):
    response = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": transcript}
        ]
    )
    return response.choices[0].message.content
