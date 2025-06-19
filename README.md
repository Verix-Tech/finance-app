# Finance Bot

Bot de WhatsApp/Telegram para gerenciamento de pedidos e relatórios financeiros.

## Estrutura do Projeto

```
finance-app/
├── api/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── models/
│   │   ├── __init__.py
│   │   └── models.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── schemas.py
│   ├── routers/
│   │   ├── __init__.py
│   │   └── orders.py
│   └── services/
│       ├── __init__.py
│       ├── bot_service.py
│       └── report_service.py
├── bots/
│   ├── __init__.py
│   ├── telegram_bot.py
│   └── whatsapp_bot.py
├── database/
│   ├── __init__.py
│   └── session.py
├── migrations/
│   └── versions/
├── reports/
│   ├── __init__.py
│   └── generators.py
├── tasks/
│   ├── __init__.py
│   └── celery_tasks.py
├── tests/
│   └── __init__.py
├── .env
├── .gitignore
├── docker-compose.yml
├── requirements.txt
└── README.md
```

## Configuração do Ambiente

1. Clone o repositório
2. Crie um ambiente virtual:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux/Mac
   # ou
   .venv\Scripts\activate  # Windows
   ```

3. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure as variáveis de ambiente no arquivo `.env`

5. Inicie os serviços com Docker:
   ```bash
   docker-compose up -d
   ```

## Funcionalidades

- Recebimento de pedidos via WhatsApp/Telegram
- Armazenamento de pedidos no banco de dados
- Geração de relatórios por período
- Análise de dados e visualizações
- Envio automático de relatórios

## Tecnologias Utilizadas

- FastAPI
- SQLAlchemy
- PostgreSQL
- Python-Telegram-Bot
- WhatsApp Web.js
- Pandas
- Celery
- Redis 