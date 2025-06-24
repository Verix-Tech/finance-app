import logging
import uuid
import utils.utils as utils
from datetime import datetime
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
    response = SQLDBConfig().send_request(
        endpoint="/client-exists",
        endpoint_var="",
        method="get",
        params={"platform_id": user_id_str}
    )
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
    SQLDBConfig().send_request(
        endpoint="/create-user",
        endpoint_var="",
        method="post",
        params={"platform_id": str(user_id), "platform_name": "telegram", "phone": phone_number, "name": user_name}
    )
    
    # Invalidate cache and set user as existing
    user_cache.invalidate(str(user_id))
    user_cache.set(str(user_id), True)
    
    await update.message.reply_text("Obrigado! Recebi seu número de telefone e te cadastrei no sistema. Agora você pode me enviar mensagens.", reply_markup=ReplyKeyboardRemove())

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text or not update.effective_user:
        return

    user_id = update.effective_user.id
    if not check_user_exists(user_id):
        await update.message.reply_text("Olá, para começar, por favor, compartilhe seu número de telefone.",
                                        reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Compartilhar número de telefone", request_contact=True)]], one_time_keyboard=True, resize_keyboard=True))
        return

    user_message = update.message.text
    user_name = update.effective_user.first_name

    response = BotConfig().generate_response(user_message)
    _type = response["api_endpoint"].split("/")[1] if response["api_endpoint"] else None

    if _type == "create-transaction":
        if not response["params"].get("transaction_timestamp"):
            response["params"]["transaction_timestamp"] = datetime.now().strftime("%d/%m/%Y")
        else:
            response["params"]["transaction_timestamp"] = utils.format_date_with_year(response["params"]["transaction_timestamp"])
    elif _type == "generate-data":
        if not response["params"].get("start_date") or not response["params"].get("end_date"): 
            pass
        else:
            response["params"]["start_date"] = utils.format_date_with_year(response["params"]["start_date"])
            response["params"]["end_date"] = utils.format_date_with_year(response["params"]["end_date"])

    message_id = str(uuid.uuid4())
    # Insert messages into MongoDBdatabase
    NoSQLDBConfig().insert_messages([
        {"message_id": message_id, "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "message": user_message, "is_bot": False, "client_id": str(user_id), "metadata": {"name": user_name}},
        {"message_id": message_id, "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "message": response.get("message", "Desculpe, não consegui gerar uma resposta."), "type": _type, "is_bot": True, "client_id": str(user_id), "metadata": response}
    ])

    await update.message.reply_text(message_id + "\n" + response.get("message", "Desculpe, não consegui gerar uma resposta."))

    if response.get("api_endpoint"):
        db_response = SQLDBConfig().send_request(
            endpoint=response["api_endpoint"],
            endpoint_var="",
            method="post",
            params=response["params"],
            platform_id=str(user_id)
        )

        if _type == "create-transaction":
            if db_response.status_code == 201:
                with open("messages/inserted_transaction.txt", "r", encoding="utf-8") as file:
                    payment_method_name = response["params"]["payment_method_name"] or "Não informado"
                    await update.message.reply_text(file.read().format(
                        response["params"]["transaction_type"],
                        response["params"]["transaction_revenue"],
                        response["params"]["payment_description"],
                        response["params"]["payment_category"],
                        payment_method_name,
                        response["params"]["transaction_timestamp"],
                        db_response.json()["data"]["transaction_id"],
                        message_id
                    ))
        elif _type == "generate-data":
            status_code = 0
            while status_code != 200:
                db_response = SQLDBConfig().send_request(
                    endpoint="/task-status",
                    endpoint_var=f"{db_response.json()['data']['task_id']}",
                    method="get",
                    params={},
                    platform_id=str(user_id)
                )
                status_code = db_response.status_code

                if status_code == 200:
                    csv_buffer = db_response.content.decode("utf-8")
                    report = utils.format_report(csv_buffer, response["params"]["aggr"]["activated"])
                    await update.message.reply_photo(utils.create_table_image(report, (4, 4), "Relatório", 600), caption=open("messages/report.txt", "r", encoding="utf-8").read().format(message_id))

                    return
                elif status_code == 201:
                    continue
                else:
                    await update.message.reply_text(message_id + "\nDesculpe, não consegui processar sua solicitação. Por favor, tente novamente.")
                    return
        elif _type == "update-transaction":
            if db_response.status_code == 201:
                await update.message.reply_text(message_id + "\nTransação atualizada com sucesso!")
            else:
                await update.message.reply_text(message_id + "\nDesculpe, não consegui processar sua solicitação. Por favor, tente novamente.")
        elif _type == "delete-transaction":
            if db_response.status_code == 201:
                await update.message.reply_text(message_id + "\nTransação deletada com sucesso!")
            else:
                await update.message.reply_text(message_id + "\nDesculpe, não consegui processar sua solicitação. Por favor, tente novamente.")
        else:
            await update.message.reply_text(message_id + "\nDesculpe, não consegui processar sua solicitação. Por favor, tente novamente.")

def main():
    app = Application.builder().token(BotConfig().TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.CONTACT, handle_contact))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
    # get_csv = requests.get("http://localhost:8000/task-status/314daa7f-2a3b-4f5d-8a85-5c86e08a51b4", headers={"Authorization": f"Bearer {SQLDBConfig().authenticate()}"})
    # print(get_csv.content.decode("utf-8"))
