# Testes da API Refatorada

Este diretório contém os testes para a API refatorada.

## 📁 Estrutura

```
tests/
├── conftest.py              # Configuração do pytest e fixtures
├── test_simple.py           # Testes simples (sem banco de dados)
├── test_api_refactored.py   # Testes completos da API
└── README.md                # Esta documentação
```

## 🚀 Como Executar

### 1. Testes Simples (Recomendado para começar)

```bash
# Executar script de testes
python run_tests.py

# Ou executar diretamente
python tests/test_simple.py

# Ou com pytest
pytest tests/test_simple.py -v
```

### 2. Testes Completos

```bash
# Executar todos os testes
pytest tests/ -v

# Executar apenas testes unitários
pytest tests/ -m unit -v

# Executar apenas testes de integração
pytest tests/ -m integration -v

# Executar apenas testes simples
pytest tests/ -m simple -v
```

### 3. Testes Específicos

```bash
# Teste específico
pytest tests/test_simple.py::test_health_check_simple -v

# Testes com nome específico
pytest tests/ -k "health" -v
```

## 🔧 Configuração

### Variáveis de Ambiente

Os testes usam as seguintes variáveis de ambiente (configuradas automaticamente):

```env
DATABASE=postgres
ADMIN_USERNAME=jvict
ADMIN_EMAIL=admin@example.com
ADMIN_FULL_NAME=Admin User
ADMIN_PASSWORD=./secrets/admin_password.txt
DATABASE_ENDPOINT=localhost
DATABASE_URL=postgresql://test:test@localhost:5432/test_db
DATABASE_USERNAME=test
DATABASE_PASSWORD=test
DATABASE_PORT=5432
REDIS_SERVER=redis://localhost:6379
SECRET_KEY=test_secret_key_for_testing_only
ACCESS_TOKEN_EXPIRE_MINUTES=60
DEBUG=true
```

### Dependências

Certifique-se de ter as dependências instaladas:

```bash
pip install -r requirements_refactored.txt
```

## 📋 Tipos de Testes

### 1. Testes Simples (`test_simple.py`)

- **Objetivo**: Verificar se a API está funcionando
- **Requisitos**: Apenas a aplicação (sem banco de dados)
- **Execução**: `python tests/test_simple.py`

**Testes incluídos:**
- Health check
- Documentação disponível
- Schema OpenAPI

### 2. Testes Completos (`test_api_refactored.py`)

- **Objetivo**: Testar todos os endpoints
- **Requisitos**: Banco de dados configurado
- **Execução**: `pytest tests/test_api_refactored.py -v`

**Testes incluídos:**
- Autenticação
- Usuários
- Transações
- Limites
- Assinaturas
- Relatórios

## 🛠️ Fixtures Disponíveis

### Fixtures Básicas

- `client`: Cliente de teste FastAPI
- `auth_headers`: Headers de autenticação
- `setup_test_environment`: Configura ambiente de testes

### Fixtures de Dados

- `sample_user_data`: Dados de exemplo para usuários
- `sample_transaction_data`: Dados de exemplo para transações
- `sample_limit_data`: Dados de exemplo para limites
- `sample_subscription_data`: Dados de exemplo para assinaturas
- `sample_report_data`: Dados de exemplo para relatórios

## 🏷️ Marcadores

- `@pytest.mark.unit`: Testes unitários
- `@pytest.mark.integration`: Testes de integração
- `@pytest.mark.simple`: Testes simples
- `@pytest.mark.slow`: Testes lentos

## 🔍 Solução de Problemas

### Erro: "ValidationError for Settings"

Se você encontrar erros de validação do Pydantic:

1. Verifique se todas as variáveis de ambiente estão definidas
2. Execute `python run_tests.py` que configura automaticamente
3. Ou configure manualmente as variáveis de ambiente

### Erro: "ImportError"

Se você encontrar erros de importação:

1. Verifique se está no diretório correto (`api/`)
2. Instale as dependências: `pip install -r requirements_refactored.txt`
3. Verifique se todos os arquivos da refatoração estão presentes

### Erro: "Database connection"

Se você encontrar erros de conexão com banco de dados:

1. Use os testes simples primeiro: `python tests/test_simple.py`
2. Configure um banco de dados de teste
3. Ou use mocks para os testes

## 📊 Cobertura de Testes

Para verificar a cobertura de testes:

```bash
# Instalar pytest-cov
pip install pytest-cov

# Executar com cobertura
pytest tests/ --cov=. --cov-report=html

# Ver relatório
open htmlcov/index.html
```

## 🎯 Próximos Passos

1. **Implementar testes unitários** para services
2. **Adicionar testes de integração** com banco de dados real
3. **Implementar testes de performance**
4. **Adicionar testes de segurança**
5. **Configurar CI/CD** com testes automatizados

## 📚 Recursos Úteis

- [Documentação do Pytest](https://docs.pytest.org/)
- [TestClient do FastAPI](https://fastapi.tiangolo.com/tutorial/testing/)
- [Fixtures do Pytest](https://docs.pytest.org/en/stable/fixture.html) 