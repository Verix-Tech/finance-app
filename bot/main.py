import logging
import time
from config.config import SQLDBConfig, BotConfig, NoSQLDBConfig, UserCache
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from typing import Optional


def configure_logging():
    """Configure application logging."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("logs/bot.log"),
            logging.StreamHandler()
        ]
    )

configure_logging()
logger = logging.getLogger(__name__)

# Global user cache instance
user_cache = UserCache()

def check_user_exists(user_id: int) -> bool:
    """Check if user exists, using cache to avoid repeated API calls"""
    user_id_str = str(user_id)
    # Check cache first
    cached_result = user_cache.get(user_id_str)
    if cached_result is not None:
        logger.info(f"User {user_id} existence status found in cache: {cached_result}")
        return cached_result
    
    # If not in cache, make API request
    logger.info(f"User {user_id} not in cache, checking API")
    response = SQLDBConfig().send_request("/client-exists", "get", {"client_id": user_id_str})
    exists = response.status_code not in (502, 404)
    
    # Cache the result
    user_cache.set(user_id_str, exists)
    logger.info(f"Cached user {user_id} existence status: {exists}")
    
    return exists

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not update.message:
        return
    
    user_id = update.effective_user.id
    logger.info(f"Received start command from {update.effective_user.username if update.effective_user else 'unknown'}")
    
    if check_user_exists(user_id):
        await update.message.reply_text("Olá! Você já está registrado. Podemos começar a organizar suas finanças!")
    else:
        await update.message.reply_text("Olá, sou o seu assistente financeiro. Para começar, por favor, compartilhe seu número de telefone comigo.",
                                        reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Compartilhar número de telefone", request_contact=True)]], one_time_keyboard=True, resize_keyboard=True))

async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.contact or not update.effective_user:
        return

    user_id = update.effective_user.id
    phone_number = update.message.contact.phone_number
    user_name = update.effective_user.first_name

    logger.info(f"Received phone number {phone_number} from user {user_id}")
    SQLDBConfig().send_request("/create-user", "post", {"client_id": str(user_id), "phone": phone_number, "name": user_name})
    
    # Invalidate cache and set user as existing
    user_cache.invalidate(str(user_id))
    user_cache.set(str(user_id), True)
    
    await update.message.reply_text("Obrigado! Recebi seu número de telefone e te cadastrei no sistema. Agora você pode me enviar mensagens.", reply_markup=ReplyKeyboardRemove())

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text or not update.effective_user:
        return

    user_id = update.effective_user.id
    if not check_user_exists(user_id):
        await update.message.reply_text("Por favor, compartilhe seu número de telefone primeiro.",
                                        reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Compartilhar número de telefone", request_contact=True)]], one_time_keyboard=True, resize_keyboard=True))
        return

    user_message = update.message.text
    user_name = update.effective_user.first_name

    response = BotConfig().generate_response(user_message, user_name)

    NoSQLDBConfig().insert_messages([
        {"message": user_message, "is_bot": False, "client_id": str(user_id), "metadata": {"name": user_name}},
        {"message": response.get("message", "Desculpe, não consegui gerar uma resposta."), "is_bot": True, "client_id": str(user_id), "metadata": response}
    ])

    if response.get("api_endpoint"):
        SQLDBConfig().send_request(response["api_endpoint"], "post", response["params"], str(user_id))

    await update.message.reply_text(response.get("message", "Desculpe, não consegui gerar uma resposta."))


def main():
    app = Application.builder().token(BotConfig().TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.CONTACT, handle_contact))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
    # authenticate = AIAssistant().authenticate()
    # request = AIAssistant().send_request("/create-transaction", {"transaction_revenue": 10.0, "payment_method_name": None, "payment_location": "pizza", "payment_product": None, "transaction_timestamp": None}, "1")
    # request = Config().send_request("/create-user", "post", {"client_id": "21331242134", "phone": "8197833543", "name": "joao"})
    # print(Config().API_USERNAME)
    # print(request.status_code)
    # print(request)
    # print(authenticate)
    # gpt = AIAssistant()
    # pprint.pprint(gpt.generate_response("Pizza 10"))
    # print(Config().send_request("/client-exists", "get", {"client_id": "5581973355856"}))