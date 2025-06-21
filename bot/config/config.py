import logging
import json
import requests
import time
from datetime import datetime
from pymongo import MongoClient
from requests import Response
from openai import OpenAI
from os import getenv
from typing import Optional


logger = logging.getLogger(__name__)

with open(getenv("SECRETS") or "", "r", encoding="utf-8") as file:
    SECRETS = json.loads(file.read())

class BotConfig:
    def __init__(self):
        self.client = OpenAI(api_key=SECRETS.get("OPENAI_API_KEY") or "")
        with open("prompt/prompt.txt", "r", encoding="utf-8") as file:
            self.prompt = file.read()
        self.model = "gpt-4.1-nano"
        self.TELEGRAM_TOKEN = SECRETS.get("TELEGRAM_BOT_TOKEN") or ""
    
    def generate_response(self, user_message: str, user_name: str = "unknown") -> dict:
        logger.info(f"Generating response for user message: {user_message}")
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.prompt},
                {"role": "user", "content": user_name + " " + user_message}
            ],
            response_format={"type": "json_object"}
        )

        return json.loads(response.choices[0].message.content or "{}")

class SQLDBConfig:
    def __init__(self):
        # API Credentials
        self.API_USERNAME = SECRETS.get("API_USERNAME") or ""
        self.API_PASSWORD = SECRETS.get("API_PASSWORD") or ""
        self.API_URL = SECRETS.get("API_URL") or ""
        
        # Token management
        self._token_data = None
        self._token_file = "secrets/token.json"

    def _load_token(self) -> Optional[dict]:
        """Load token from file if it exists and is not expired"""
        try:
            with open(self._token_file, "r", encoding="utf-8") as file:
                token_data = json.loads(file.read())
                
            # Check if token is expired (with 60 second buffer)
            current_time = time.time()
            if token_data.get("expires_at", 0) > current_time + 60:
                return token_data
            else:
                logger.info("Token is expired or will expire soon, will re-authenticate")
                return None
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            logger.info("No valid token file found, will authenticate")
            return None

    def _save_token(self, token_data: dict):
        """Save token data to file with expiration time"""
        try:
            # Calculate expiration time (assuming token expires in 1 hour if not specified)
            expires_in = token_data.get("expires_in", 3600)  # default 1 hour
            token_data["expires_at"] = time.time() + expires_in
            
            with open(self._token_file, "w", encoding="utf-8") as file:
                json.dump(token_data, file)
            
            logger.info(f"Token saved, expires at {token_data['expires_at']}")
        except Exception as e:
            logger.error(f"Failed to save token: {e}")

    def _get_valid_token(self) -> str:
        """Get a valid token, re-authenticating if necessary"""
        token_data = self._load_token()
        
        if token_data is None:
            logger.info("Authenticating to get new token")
            token_data = self._authenticate()
            self._save_token(token_data)
        
        return token_data["access_token"]
    
    def _authenticate(self) -> dict:
        """Internal authentication method that returns the full response"""
        endpoint = f"{self.API_URL}/token"
        response = requests.post(endpoint, data={"username": self.API_USERNAME, "password": self.API_PASSWORD})
        
        if response.status_code != 200:
            raise Exception(f"Authentication failed: {response.status_code} - {response.text}")
        
        token_data = response.json()
        logger.info("Authentication successful")
        return token_data
    
    def authenticate(self) -> str:
        """Public method for manual authentication (for backward compatibility)"""
        token_data = self._authenticate()
        self._save_token(token_data)
        return token_data["access_token"]
    
    def send_request(self, endpoint: str, method: str, params: dict, client_id: Optional[str] = None) -> Response:
        endpoint = f"{self.API_URL}{endpoint}"
        params["client_id"] = client_id if params.get("client_id") is None else params["client_id"]
        params["id_type"] = "telegram_id"

        # Get a valid token (will re-authenticate if expired)
        token = self._get_valid_token()

        logger.info(f"Sending request to {endpoint} with params: {params}")

        response = requests.get(
            endpoint, data=json.dumps(params), headers={"Authorization": f"Bearer {token}"}
        ) if method == "get" else requests.post(
            endpoint, data=json.dumps(params), headers={"Authorization": f"Bearer {token}"}
        )
        
        # If we get a 401 (Unauthorized), the token might be expired
        # Try to re-authenticate and retry the request once
        if response.status_code == 401:
            logger.warning("Received 401, token may be expired. Re-authenticating and retrying...")
            try:
                # Force re-authentication
                token_data = self._authenticate()
                self._save_token(token_data)
                token = token_data["access_token"]
                
                # Retry the request
                response = requests.get(
                    endpoint, data=json.dumps(params), headers={"Authorization": f"Bearer {token}"}
                ) if method == "get" else requests.post(
                    endpoint, data=json.dumps(params), headers={"Authorization": f"Bearer {token}"}
                )
            except Exception as e:
                logger.error(f"Failed to re-authenticate: {e}")
        
        return response

class NoSQLDBConfig:
    def __init__(self):
        mongodb_url = SECRETS.get("MONGODB_URL") or ""
        mongodb_user = SECRETS.get("MONGODB_USER") or ""
        mongodb_password = SECRETS.get("MONGODB_PASSWORD") or ""
        mongodb_database = SECRETS.get("MONGODB_DATABASE") or ""

        self.client = MongoClient(mongodb_url, username=mongodb_user, password=mongodb_password)
        self.db = self.client[mongodb_database]
        self.collection = self.db["messages"]

    def insert_message(self, message: str, is_bot: bool, client_id: str, metadata: dict = {}):
        message_data = {
            "client_id": client_id,
            "message": message,
            "is_bot": is_bot,
            "timestamp": datetime.now(),
            "metadata": metadata                        
        }

        result = self.collection.insert_one(message_data)
        return result.inserted_id
    
    def insert_messages(self, messages: list[dict]):
        result = self.collection.insert_many(messages)
        return result.inserted_ids

class UserCache:
    """Simple in-memory cache for user existence status"""
    def __init__(self, ttl_seconds=300):  # 5 minutes TTL
        self.cache = {}
        self.ttl = ttl_seconds
    
    def get(self, user_id: str) -> Optional[bool]:
        """Get user existence status from cache"""
        if user_id in self.cache:
            timestamp, exists = self.cache[user_id]
            if time.time() - timestamp < self.ttl:
                return exists
            else:
                # Expired, remove from cache
                del self.cache[user_id]
        return None
    
    def set(self, user_id: str, exists: bool):
        """Set user existence status in cache"""
        self.cache[user_id] = (time.time(), exists)
    
    def invalidate(self, user_id: str):
        """Remove user from cache (useful when user is created)"""
        if user_id in self.cache:
            del self.cache[user_id]
