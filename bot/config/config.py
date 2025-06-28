import logging
import json
import requests
import time
from datetime import datetime
from pymongo import MongoClient
from requests import Response
from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam
from os import getenv
from typing import Optional, List, Dict, Any


logger = logging.getLogger(__name__)

with open(getenv("SECRETS") or "", "r", encoding="utf-8") as file:
    SECRETS = json.loads(file.read())

class BotConfig:
    def __init__(self):
        self.client = OpenAI(api_key=SECRETS.get("OPENAI_API_KEY") or "")
        with open("prompt/prompt.md", "r", encoding="utf-8") as file:
            self.prompt = file.read()
        self.model = "gpt-4.1-nano"
        self.TELEGRAM_TOKEN = SECRETS.get("TELEGRAM_BOT_TOKEN") or ""
        self.CATEGORIAS = {
            "1": "Alimentação",
            "2": "Saúde",
            "3": "Salário",
            "4": "Investimentos",
            "5": "Pet",
            "6": "Contas",
            "7": "Educação",
            "8": "Lazer",
            "0": "Outros"
        }
        self.METODOS_PAGAMENTO = {
            "1": "Pix",
            "2": "Crédito",
            "3": "Débito",
            "4": "Dinheiro",
            "0": "Não informado"
        }
        # Conversation history for better context
        self.conversation_history = {}
    
    def _get_conversation_history(self, user_id: str, max_messages: int = 5) -> list:
        """Get recent conversation history for a user"""
        if user_id not in self.conversation_history:
            return []
        
        # Return last N messages
        return self.conversation_history[user_id][-max_messages:]
    
    def _add_to_conversation_history(self, user_id: str, role: str, content: str):
        """Add a message to conversation history"""
        if user_id not in self.conversation_history:
            self.conversation_history[user_id] = []
        
        self.conversation_history[user_id].append({
            "role": role,
            "content": content,
            "timestamp": datetime.now()
        })
        
        # Keep only last 10 messages to prevent memory issues
        if len(self.conversation_history[user_id]) > 10:
            self.conversation_history[user_id] = self.conversation_history[user_id][-10:]
    
    def generate_response(self, user_message: str, user_name: Optional[str] = None, user_id: Optional[str] = None) -> dict:
        logger.info(f"Generating response for user message: {user_message}")
        
        # Create system prompt with user name if provided
        system_prompt = self.prompt
        if user_name:
            system_prompt = f"{self.prompt}\n\n**Informação do usuário:** O nome do usuário é {user_name}. Use este nome para personalizar suas respostas e cumprimentos."
        
        # Add conversation context for better accuracy
        conversation_context = f"""
**CONTEXTO IMPORTANTE PARA PRECISÃO:**
- Mensagem do usuário: "{user_message}"
- Nome do usuário: {user_name or "Não informado"}
- Data atual: {datetime.now().strftime("%d/%m/%Y")}

**INSTRUÇÕES DE PRECISÃO:**
1. Analise cuidadosamente cada palavra da mensagem
2. Identifique valores monetários com precisão
3. Categorize baseado no contexto completo
4. **PARA ATUALIZAÇÕES:** NUNCA peça confirmação - apenas execute a atualização solicitada
5. **PARA ATUALIZAÇÕES:** Não pergunte se os valores estão corretos - o usuário já especificou o que quer
"""
        
        # Build messages array with conversation history
        messages: List[ChatCompletionMessageParam] = [{"role": "system", "content": system_prompt + conversation_context}]
        
        # Add conversation history if available
        if user_id:
            history = self._get_conversation_history(user_id)
            for msg in history:
                messages.append({"role": msg["role"], "content": msg["content"]})
        
        # Add current user message
        messages.append({"role": "user", "content": user_message})
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    response_format={"type": "json_object"},
                    temperature=0.1,  # Lower temperature for more consistent responses
                    max_tokens=1000
                )

                response_content = response.choices[0].message.content or "{}"
                parsed_response = json.loads(response_content)
                
                # Validate response structure
                if self._validate_response(parsed_response, user_message):
                    logger.info(f"Generated valid response on attempt {attempt + 1}")
                    
                    # Add to conversation history
                    if user_id:
                        self._add_to_conversation_history(user_id, "user", user_message)
                        self._add_to_conversation_history(user_id, "assistant", response_content)
                    
                    return parsed_response
                else:
                    logger.warning(f"Invalid response structure on attempt {attempt + 1}, retrying...")
                    if attempt == max_retries - 1:
                        fallback = self._generate_fallback_response(user_message, user_name)
                        if user_id:
                            self._add_to_conversation_history(user_id, "user", user_message)
                            self._add_to_conversation_history(user_id, "assistant", json.dumps(fallback))
                        return fallback
                        
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error on attempt {attempt + 1}: {e}")
                if attempt == max_retries - 1:
                    fallback = self._generate_fallback_response(user_message, user_name)
                    if user_id:
                        self._add_to_conversation_history(user_id, "user", user_message)
                        self._add_to_conversation_history(user_id, "assistant", json.dumps(fallback))
                    return fallback
            except Exception as e:
                logger.error(f"Error generating response on attempt {attempt + 1}: {e}")
                if attempt == max_retries - 1:
                    fallback = self._generate_fallback_response(user_message, user_name)
                    if user_id:
                        self._add_to_conversation_history(user_id, "user", user_message)
                        self._add_to_conversation_history(user_id, "assistant", json.dumps(fallback))
                    return fallback
        
        fallback = self._generate_fallback_response(user_message, user_name)
        if user_id:
            self._add_to_conversation_history(user_id, "user", user_message)
            self._add_to_conversation_history(user_id, "assistant", json.dumps(fallback))
        return fallback
    
    def _validate_response(self, response: dict, user_message: str) -> bool:
        """Validate that the response has the required structure and logical consistency"""
        try:
            # Check required fields
            if not response.get("message") or not isinstance(response["message"], str):
                logger.warning("Missing or invalid 'message' field")
                return False
            
            # If API endpoint is present, validate params
            if response.get("api_endpoint"):
                if not response.get("params") or not isinstance(response["params"], dict):
                    logger.warning("API endpoint present but missing or invalid 'params' field")
                    return False
                
                # Validate specific endpoint requirements
                endpoint = response["api_endpoint"]
                params = response["params"]
                
                if endpoint == "/transactions/create":
                    if not params.get("transaction_revenue") or not params.get("transaction_type"):
                        logger.warning("Missing required fields for transactions/create")
                        return False
                    
                    # Validate transaction_revenue is numeric
                    try:
                        float(params["transaction_revenue"])
                    except (ValueError, TypeError):
                        logger.warning("Invalid transaction_revenue value")
                        return False
                
                elif endpoint == "/reports/generate":
                    # Must have either days_before OR start_date+end_date
                    has_days = "days_before" in params
                    has_dates = "start_date" in params and "end_date" in params
                    if not (has_days or has_dates):
                        logger.warning("Missing date parameters for reports/generate")
                        return False
                    if has_days and has_dates:
                        logger.warning("Both days_before and date range specified")
                        return False
                
                elif endpoint == "/transactions/update":
                    if not params.get("transactionId"):
                        logger.warning("Missing transactionId for transactions/update")
                        return False
                    
                    # Check for confirmation requests in update messages
                    message = response.get("message", "").lower()
                    confirmation_keywords = ["confirme", "confirma", "está correto", "deseja ajustar", "está certo"]
                    if any(keyword in message for keyword in confirmation_keywords):
                        logger.warning("Update response contains confirmation request - rejecting")
                        return False
                
                elif endpoint == "/transactions/delete":
                    if not params.get("transaction_id"):
                        logger.warning("Missing transaction_id for transactions/delete")
                        return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating response: {e}")
            return False
    
    def _generate_fallback_response(self, user_message: str, user_name: Optional[str] = None) -> dict:
        """Generate a fallback response when the main generation fails"""
        logger.warning("Generating fallback response due to generation failure")
        
        # Try to extract basic information for a simple transaction
        import re
        
        # Look for monetary values
        money_pattern = r'R?\$?\s*([0-9]+(?:[.,][0-9]+)?)'
        money_match = re.search(money_pattern, user_message)
        
        # Look for common transaction keywords
        transaction_keywords = ['gastei', 'paguei', 'comprei', 'gasto', 'despesa', 'entrada', 'recebi', 'salário']
        is_expense = any(keyword in user_message.lower() for keyword in transaction_keywords[:5])
        is_income = any(keyword in user_message.lower() for keyword in transaction_keywords[5:])
        
        if money_match and (is_expense or is_income):
            try:
                value = float(money_match.group(1).replace(',', '.'))
                transaction_type = "Despesa" if is_expense else "Entrada"
                
                return {
                    "message": f"Olá {user_name or 'usuário'}! Registrei sua {transaction_type.lower()} de R$ {value:.2f}. Se precisar ajustar algo, é só me avisar! 💰",
                    "api_endpoint": "/transactions/create",
                    "params": {
                        "transaction_revenue": value,
                        "transaction_type": transaction_type,
                        "payment_description": "Transação registrada",
                        "payment_category": "0"
                    }
                }
            except ValueError:
                pass
        
        # Generic fallback
        return {
            "message": f"Olá {user_name or 'usuário'}! Desculpe, não consegui entender completamente sua mensagem. Pode reformular de forma mais clara? Por exemplo: 'Gastei R$ 50 em pizza' ou 'Quero relatório dos últimos 7 dias'. 🤔",
            "api_endpoint": "",
            "params": {}
        }

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
        endpoint = f"{self.API_URL}/auth/token"
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
    
    def send_request(self, endpoint: str, endpoint_var: str = "", method: str = "get", params: dict = {}, platform_id: Optional[str] = None) -> Response:
        endpoint = f"{self.API_URL}{endpoint}/{endpoint_var}" if endpoint_var else f"{self.API_URL}{endpoint}"
        params["platform_id"] = platform_id if params.get("platform_id") is None else params["platform_id"]

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
