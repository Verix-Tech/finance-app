# Deploy no Fly.io (multi-serviço)

Este diretório contém manifests para Fly.io convertidos a partir do `docker-compose.yml`.

Apps:
- API: `fly-finance-api.toml`
- Celery: `fly-celery.toml`
- Redis: `fly-redis.toml`
- Bot: `fly-bot.toml`

Passo-a-passo:
1) Instale o Fly CLI e faça login:
```
curl -L https://fly.io/install.sh | sh
fly auth login
```

2) Crie os apps (ajuste nomes/region). Ex.: `finance-redis`, `findash-api`, `findash-celery`, `finance-bot`:
```
cd fly
fly apps create finance-redis
fly apps create findash-api
fly apps create findash-celery
fly apps create finance-bot
```

3) Opcional: use Postgres gerenciado pelo Fly (recomendado produção):
```
fly postgres create --name finance-postgres-CHANGE_ME --regions iad --vm-size shared-cpu-1x --initial-cluster-size 1
# Obtenha host interno e credenciais e preencha em fly-finance-api.toml e fly-celery.toml
```

4) Defina os secrets necessários:
```
# API e Celery
fly secrets set POSTGRES_PASSWORD_VALUE='SENHA_DB' SECRET_KEY_VALUE='chave-secreta' ADMIN_PASSWORD_VALUE='senha-admin' -a findash-api
fly secrets set POSTGRES_PASSWORD_VALUE='SENHA_DB' SECRET_KEY_VALUE='chave-secreta' ADMIN_PASSWORD_VALUE='senha-admin' -a findash-celery

# Bot (conteúdo JSON inteiro do bot/secrets/secret.json)
fly -a finance-bot-CHANGE_ME secrets set BOT_CREDENTIALS_JSON='{"token":"..."}'
```

5) Deploy de cada app (comandos atualizados):
```
# Redis (somente deploy com arquivo de config)
fly deploy -c fly-redis.toml -a finance-redis --copy-config --no-public-ips

# API
fly deploy -c fly-finance-api.toml -a findash-api --copy-config

# Celery
fly deploy -c fly-celery.toml -a findash-celery --copy-config

# Bot
fly deploy -c fly-bot.toml -a finance-bot --copy-config
```

Notas de migração do Compose:
- Secrets do Compose eram arquivos; aqui gravamos arquivos em `/run/secrets/*` a partir de secrets do Fly via script de entrada no processo.
- Redis no Compose era exposto; em Fly recomenda-se manter interno (remova a publicação da porta caso não precise público).
- Postgres local do Compose foi substituído por Postgres gerenciado do Fly (ou outro Postgres externo, ex. Supabase). Para Supabase, `DATABASE` adiciona `?sslmode=require` no `fly-finance-api.toml`.
- `DATABASE_PASSWORD` no código espera um caminho de arquivo; por isso `DATABASE_PASSWORD="/run/secrets/postgres_pass"` permanece e o conteúdo é escrito no startup.

