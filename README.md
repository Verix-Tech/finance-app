# Finance App

A comprehensive financial management application with FastAPI backend, background task processing, and multi-service architecture for handling transactions, user management, and data analytics.

## Project Overview

This application provides a robust financial management system with:
- **RESTful API** for transaction and user management
- **Background task processing** for data generation and analytics
- **Multi-service architecture** with Docker containerization
- **Real-time task monitoring** and status tracking
- **Comprehensive testing suite** and development automation

## Project Structure

```
finance-app/
├── api/                          # Main API application
│   ├── auth/                     # Authentication and authorization
│   ├── database_manager/         # Database connection and management
│   │   ├── models/              # SQLAlchemy models
│   │   ├── connector.py         # Database connection management
│   │   ├── inserter.py          # Data insertion utilities
│   │   └── manage_tables.py     # Table management scripts
│   ├── errors/                  # Custom error definitions
│   ├── workers/                 # Celery background task workers
│   │   └── main.py             # Celery task definitions
│   ├── tests/                  # Test suite
│   │   ├── test_redis_connection.py
│   │   └── test_tasks.py
│   ├── data/                   # Generated data files
│   ├── logs/                   # Application logs
│   ├── secrets/                # Secret files (not tracked in git)
│   ├── sql/                    # Database initialization scripts
│   ├── main.py                # Main FastAPI application
│   ├── Makefile               # Build and development automation
│   ├── Makefile.dev           # Development-specific commands
│   ├── requirements.txt       # Python dependencies
│   ├── .env-template          # Environment variables template
│   └── README.md              # API-specific documentation
├── FinanceAPI.Dockerfile      # API container configuration
├── Celery.Dockerfile          # Celery worker container configuration
├── docker-compose.yml         # Multi-service orchestration
├── requirements.txt           # Root dependencies
├── .gitignore                # Git ignore patterns
├── .dockerignore             # Docker ignore patterns
└── README.md                 # This file
```

## Features

### Core Functionality
- **User Authentication**: JWT-based authentication and authorization
- **Transaction Management**: Create, update, delete, and query transactions
- **Subscription Management**: Grant and revoke user subscriptions
- **Database Health Monitoring**: Real-time database connection monitoring

### Advanced Features
- **Background Task Processing**: Asynchronous data generation using Celery
- **Data Analytics**: Generate detailed financial extracts and reports
- **Task Monitoring**: Real-time task status tracking and progress monitoring
- **Flexible Data Export**: CSV generation with configurable aggregation levels
- **Comprehensive Logging**: Structured logging with multiple output handlers

### Development & Operations
- **Automated Testing**: Redis connection tests and task validation
- **Build Automation**: Make-based development and deployment automation
- **Health Checks**: Service health monitoring across all components
- **Error Handling**: Robust error handling with detailed logging

## Technology Stack

### Backend
- **FastAPI**: Modern, fast web framework for building APIs
- **SQLAlchemy**: SQL toolkit and ORM for database operations
- **PostgreSQL**: Robust, open-source relational database
- **Celery**: Distributed task queue for background processing
- **Redis**: In-memory data structure store (message broker)

### Development & Deployment
- **Docker**: Containerization for consistent deployment
- **Docker Compose**: Multi-service orchestration
- **Make**: Build automation and development workflow
- **Python 3.8+**: Modern Python with type hints

### Security & Authentication
- **JWT**: JSON Web Tokens for secure authentication
- **Passlib**: Password hashing with bcrypt
- **Environment Variables**: Secure configuration management
- **Docker Secrets**: Secure credential management

### Data Processing
- **Pandas**: Data manipulation and analysis
- **NumPy**: Numerical computing
- **Python-dateutil**: Date and time utilities

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Python 3.8+ (for local development)
- Git

### 1. Clone the Repository
```bash
git clone <repository-url>
cd finance-app
```

### 2. Set Up Environment
```bash
# Copy environment template
cp api/.env-template api/.env

# Create necessary secret files
mkdir -p api/sql/secrets api/secrets
echo "your_postgres_password" > api/sql/secrets/user_credentials.txt
echo "your_jwt_secret_key" > api/secrets/secret_key.txt
echo "your_admin_password" > api/secrets/admin_password.txt
```

### 3. Start Services
```bash
# Build and start all services
docker-compose up --build -d

# Check service status
docker-compose ps
```

### 4. Verify Installation
```bash
# Check API health
curl http://localhost:8000/health

# Check service logs
docker-compose logs finance-api
```

## API Endpoints

### Authentication
- `POST /token` - Get access token (login)

### User Management
- `POST /create-user` - Create or update user

### Transaction Management
- `POST /create-transaction` - Create new transaction
- `POST /update-transaction` - Update existing transaction
- `POST /delete-transaction` - Delete transaction

### Data Generation & Analytics
- `POST /generate-data` - Start background data generation task
- `GET /task-status/{task_id}` - Check task status and results

### Subscription Management
- `POST /grant-subscription` - Grant subscription to user
- `POST /revoke-subscription` - Revoke user subscription

### Health & Monitoring
- `GET /health` - Check API health status

## Development

### Using Make Commands
The project includes comprehensive automation:

```bash
# Database operations
make -C api create_tables      # Create database tables
make -C api drop_tables        # Drop database tables
make -C api create_user        # Create database users

# Development tasks
make -C api start_api          # Start API with auto-reload
make -C api start_celery       # Start Celery worker with auto-restart
make -C api test_celery_redis_connection  # Test Redis/Celery connectivity

# Debugging
make -C api generate_data      # Test data generation locally
```

### Local Development Setup
```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Start Redis (required for Celery)
docker run -d -p 6379:6379 redis:latest

# Start API server
cd api
uvicorn main:app --reload

# Start Celery worker (in separate terminal)
cd api
celery -A workers.main.app worker --loglevel=INFO
```

## Docker Services

The application runs as a multi-service Docker environment:

### Services Overview
- **PostgreSQL** (`postgres`): Primary database with health checks
- **Redis** (`redis`): Message broker for Celery tasks
- **Finance API** (`finance-api`): Main FastAPI application
- **Celery Worker** (`celery`): Background task processing

### Service Configuration
- **Health Checks**: All services include health monitoring
- **Dependency Management**: Proper startup order with health checks
- **Secret Management**: Docker secrets for sensitive data
- **Network Isolation**: Custom bridge network for secure communication
- **Volume Persistence**: Database data persistence across restarts

## Testing

### Test Suite
```bash
# Test Redis connection
cd api
python tests/test_redis_connection.py

# Test Celery tasks
python tests/test_tasks.py
```

### Test Coverage
- **Redis Connectivity**: Verify Redis connection and configuration
- **Task Functionality**: Validate Celery task execution
- **Integration Tests**: End-to-end API testing

## Configuration

### Environment Variables
Key environment variables required:

```bash
# Database Configuration
DATABASE_ENDPOINT=postgres
DATABASE_URL=postgresql://jvict:password@postgres:5432/postgres
DATABASE_USERNAME=jvict
DATABASE_PASSWORD=your_password
DATABASE_PORT=5432

# Security
SECRET_KEY=your_jwt_secret_key
ADMIN_USERNAME=jvict
ADMIN_PASSWORD=your_admin_password
ADMIN_EMAIL=admin@example.com
ADMIN_FULL_NAME=Admin User

# Redis Configuration
REDIS_SERVER=redis://redis:6379
```

### Secret Files
Required secret files (not tracked in git):
- `api/sql/secrets/user_credentials.txt` - PostgreSQL password
- `api/secrets/secret_key.txt` - JWT secret key
- `api/secrets/admin_password.txt` - Admin password

## Monitoring & Logging

### Logging Configuration
- **Log Level**: INFO
- **Log File**: `api/logs/app.log`
- **Console Output**: Enabled
- **Structured Logging**: JSON-formatted entries

### Health Monitoring
- **Database Health**: Connection monitoring and health checks
- **Service Health**: All services include health endpoints
- **Task Monitoring**: Real-time Celery task status tracking

## Security Features

- **JWT Authentication**: Secure token-based authentication
- **Password Hashing**: bcrypt-based password security
- **Input Validation**: Comprehensive request validation
- **Error Handling**: Secure error responses without information leakage
- **Docker Secrets**: Secure credential management
- **Network Isolation**: Service-to-service communication security

## Performance & Scalability

- **Asynchronous Processing**: Background task execution
- **Connection Pooling**: Database connection optimization
- **Task Queuing**: Redis-based message queuing
- **Horizontal Scaling**: Multiple Celery workers support
- **Resource Management**: Automatic cleanup and resource disposal

## Troubleshooting

### Common Issues

**Redis Connection Errors**
```bash
# Check Redis service status
docker-compose ps redis

# View Redis logs
docker-compose logs redis

# Test Redis connectivity
make -C api test_celery_redis_connection
```

**Database Connection Issues**
```bash
# Check PostgreSQL service status
docker-compose ps postgres

# View database logs
docker-compose logs postgres

# Test database connection
docker-compose exec finance-api python -c "from database_manager.connector import DatabaseManager; db = DatabaseManager(); db.check_connection()"
```

**Task Execution Failures**
```bash
# Check Celery worker logs
docker-compose logs celery

# Restart Celery service
docker-compose restart celery
```

### Debug Commands
```bash
# Check all service status
docker-compose ps

# View logs for specific service
docker-compose logs [service-name]

# Restart specific service
docker-compose restart [service-name]

# Access service shell
docker-compose exec [service-name] bash
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Add tests for new functionality
4. Ensure all tests pass
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

### Development Guidelines
- Follow PEP 8 coding standards
- Add comprehensive tests for new features
- Update documentation for API changes
- Use descriptive commit messages
- Ensure Docker builds successfully

## License

This project is licensed under the MIT License - see the LICENSE file for details.