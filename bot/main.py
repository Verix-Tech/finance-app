import logging
import uuid
import time
import utils.utils as utils
from datetime import datetime
from config.config import SQLDBConfig, BotConfig, NoSQLDBConfig
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from typing import Optional

from bot.core.logging_config import configure_logging
from bot.core.cache import user_cache
from bot.services.user_service import check_user_exists


## TODO:
# - [ ] Refatorar o código

configure_logging()
logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not update.message:
        return
    
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    logger.info(f"Received start command from {update.effective_user.username if update.effective_user else 'unknown'}")
    
    if check_user_exists(user_id):
        response = BotConfig().generate_response("Olá, já estou registrado", user_name)
        await update.message.reply_text(response.get("message", "Olá! Você já está registrado. Podemos começar a organizar suas finanças!"))
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
        endpoint="/users/create",
        endpoint_var="",
        method="post",
        params={"platform_id": str(user_id), "platform_name": "telegram", "phone": phone_number, "name": user_name}
    )
    
    # Invalidate cache and set user as existing
    user_cache.invalidate(str(user_id))
    user_cache.set(str(user_id), True)
    
    response = BotConfig().generate_response("Acabei de me registrar", user_name)
    await update.message.reply_text(response.get("message", "Obrigado! Recebi seu número de telefone e te cadastrei no sistema. Agora você pode me enviar mensagens."), reply_markup=ReplyKeyboardRemove())

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

    response = BotConfig().generate_response(user_message, user_name, str(user_id))
    endpoint = response.get("api_endpoint", "") if response.get("api_endpoint") else None

    if endpoint == "/transactions/create":
        response["params"]["payment_category_id"] = response.get("params", {}).get("payment_category_id", "0")
        response["params"]["payment_method_id"] = response.get("params", {}).get("payment_method_id", "0")

        if not response["params"].get("transaction_timestamp"):
            response["params"]["transaction_timestamp"] = datetime.now().strftime("%d/%m/%Y")
        else:
            response["params"]["transaction_timestamp"] = utils.format_date_with_year(response["params"]["transaction_timestamp"])
    elif endpoint == "/transactions/update":
        if response["params"].get("transaction_timestamp"):
                response["params"]["transaction_timestamp"] = utils.format_date_with_year(response["params"]["transaction_timestamp"]) 
    elif endpoint == "/reports/generate":
        if not response["params"].get("start_date") or not response["params"].get("end_date"): 
            pass
        else:
            response["params"]["start_date"] = utils.format_date_with_year(response["params"]["start_date"])
            response["params"]["end_date"] = utils.format_date_with_year(response["params"]["end_date"])

    message_id = str(uuid.uuid4())

    # Insert messages into MongoDBdatabase
    NoSQLDBConfig().insert_messages([
        {"message_id": message_id, "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "message": user_message, "is_bot": False, "client_id": str(user_id), "metadata": {"name": user_name}},
        {"message_id": message_id, "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "message": response.get("message", "Desculpe, não consegui gerar uma resposta."), "type": endpoint, "is_bot": True, "client_id": str(user_id), "metadata": response}
    ])

    await update.message.reply_text(response.get("message", "Desculpe, não consegui gerar uma resposta."))

    if response.get("api_endpoint"):
        db_response = SQLDBConfig().send_request(
            endpoint=response["api_endpoint"],
            endpoint_var="",
            method="post", 
            params=response["params"],
            platform_id=str(user_id)
        )

        if endpoint == "/transactions/create":
            if db_response.status_code == 200:
                with open("messages/inserted_transaction.txt", "r", encoding="utf-8") as file:
                    await update.message.reply_text(file.read().format(
                        response["params"]["transaction_type"],
                        response["params"]["transaction_revenue"],
                        response["params"]["payment_description"],
                        BotConfig().CATEGORIAS[response["params"]["payment_category_id"]],
                        response.get("params", {}).get("card_id", None),
                        BotConfig().METODOS_PAGAMENTO[response["params"]["payment_method_id"]],
                        response["params"]["transaction_timestamp"],
                        db_response.json()["data"]["transaction_id"],
                        message_id
                    ))
                
                limit_response = SQLDBConfig().send_request(
                    endpoint="/limits/check",
                    endpoint_var="",
                    method="post",
                    params={"category_id": response["params"]["payment_category_id"]},
                    platform_id=str(user_id)
                )
            
                if limit_response.status_code == 200:
                    if limit_response.json()["data"]["limit_exceeded"] == True:
                        await update.message.reply_text(f"\nVocê atingiu o seu limite de gastos de '{BotConfig().CATEGORIAS[response['params']['payment_category_id']]}' deste mês. 🚫")
                    elif limit_response.json()["data"]["total_revenue"] >= utils.get_limit_percentage(limit_response.json()["data"]["limit_value"]) and \
                        limit_response.json()["data"]["total_revenue"] < limit_response.json()["data"]["limit_value"]:
                        await update.message.reply_text(f"\nVocê atingiu 90% do seu limite de gastos de '{BotConfig().CATEGORIAS[response['params']['payment_category_id']]}' deste mês. 🚫")
                
        elif endpoint == "/reports/generate":
            status_code = 0
            while status_code != 200:
                status_code = db_response.status_code

                if status_code == 200:
                    try:
                        csv_buffer = db_response.content.decode("utf-8")
                        report = utils.format_report(csv_buffer, response.get("params", {}).get("aggr", {}).get("activated", False))
                        await update.message.reply_photo(utils.create_table_image(report, (4, 4), "Relatório", 600), caption=open("messages/report.txt", "r", encoding="utf-8").read().format(message_id))
                    except IndexError:
                        await update.message.reply_text("\nVocê não possui transações para gerar relatório no período selecionado.")
                        return

                    return
                elif status_code == 201:
                    time.sleep(1)
                    continue
                else:
                    await update.message.reply_text("\n" + "\nDesculpe, não consegui processar sua solicitação. Por favor, tente novamente.")
                    return
                
        elif endpoint == "/transactions/update":
            if db_response.status_code == 200:
                await update.message.reply_text("\nTransação atualizada com sucesso!")
            elif db_response.status_code == 400:
                await update.message.reply_text("\nDesculpe, não é possível atualizar transações com parcelamento. Por favor, tente deletar a transação e criar uma nova.")
            elif db_response.status_code == 404:
                await update.message.reply_text("\nDesculpe, não consegui encontrar a transação. Por favor, tente novamente.")
            else:
                await update.message.reply_text("\nDesculpe, não consegui processar sua solicitação. Por favor, tente novamente.")

        elif endpoint == "/transactions/delete":
            if db_response.status_code == 200:
                await update.message.reply_text("\nTransação(ões) deletada(s) com sucesso!")
            elif db_response.status_code == 404:
                await update.message.reply_text("\nDesculpe, não consegui encontrar a transação. Por favor, tente novamente.")
            else:
                await update.message.reply_text("\nDesculpe, não consegui processar sua solicitação. Por favor, tente novamente.")

        elif endpoint == "/limits/create":
            if db_response.status_code == 200:
                await update.message.reply_text("\nLimite criado com sucesso!")
            else:
                await update.message.reply_text("\nDesculpe, não consegui processar sua solicitação. Por favor, tente novamente.")

        elif endpoint == "/limits/check":
            if db_response.status_code == 200:
                data = db_response.json().get("data", {})
                category_id = str(data.get("category_id", "0"))
                category_name = BotConfig().CATEGORIAS.get(category_id, "Categoria")
                valor = data.get("total_revenue", 0)
                limite = data.get("limit_value", 0)

                if data.get("limit_exceeded"):
                    await update.message.reply_text(f"\nVocê utilizou R$ {valor:.2f} de R$ {limite:.2f} no limite da categoria '{category_name}'.\nVocê excedeu o limite da categoria '{category_name}' deste mês. 🚫")
                else:
                    await update.message.reply_text(f"\nVocê utilizou R$ {valor:.2f} de R$ {limite:.2f} no limite da categoria '{category_name}'. 💡")
            else:
                await update.message.reply_text("\nDesculpe, não consegui processar sua solicitação. Por favor, tente novamente.")

        elif endpoint == "/limits/check-all":
            if db_response.status_code == 200:
                data = db_response.json().get("data", {})["data"]
                lines = []
                for item in data:
                    category_id = str(item.get("payment_category_id", "0"))
                    category_name = BotConfig().CATEGORIAS.get(category_id, "Categoria")
                    if item.get("limit_exceeded"):
                        status_limite = "🚫 Excedido"
                    else:
                        total = item.get("total_revenue", 0)
                        limite = item.get("limit_value", 0)
                        status_limite = f"R$ {total:.2f} / R$ {limite:.2f} - {total/limite*100:.2f}% 🟩" if total/limite*100 < 100 else f"R$ {total:.2f} / R$ {limite:.2f} - {total/limite*100:.2f}% 🟥"
                    lines.append(f"- {category_name}: {status_limite}")

                mensagem_limites = "\n".join(lines) if lines else f"Nenhum limite encontrado."
                await update.message.reply_text("\n" + open("messages/limits.txt", "r", encoding="utf-8").read().format(mensagem_limites))
            else:
                await update.message.reply_text("\nDesculpe, não consegui processar sua solicitação. Por favor, tente novamente.")

        elif endpoint == "/reports/check":
            if db_response.status_code == 200:
                data = db_response.json().get("data", {})
                installment_payment = "Sim" if data.get("installment_payment", False) else "Não"
                transaction_date = datetime.strptime(data.get("transaction_timestamp", ""), "%Y-%m-%dT%H:%M:%S-03:00").strftime("%d/%m/%Y")
                
                await update.message.reply_text(open("messages/check_transaction.txt", "r", encoding="utf-8").read().format(
                    data.get("transaction_id", ""),
                    data.get("transaction_type", ""),
                    data.get("transaction_revenue", ""),
                    data.get("payment_description", ""),
                    data.get("payment_category_name", ""),
                    data.get("payment_method_name", ""),
                    data.get("card_name", ""),
                    transaction_date,
                    installment_payment,
                    data.get("installment_number", "")
                ))
            else:
                await update.message.reply_text("\nDesculpe, não consegui processar sua solicitação. Por favor, tente novamente.")

        else:
            await update.message.reply_text("\nDesculpe, não consegui processar sua solicitação. Por favor, tente novamente.")

def main():
    app = Application.builder().token(BotConfig().TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.CONTACT, handle_contact))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
