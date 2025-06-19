# Finance App API

A FastAPI-based financial management application that handles user authentication, transactions, subscription management, and background data processing with Celery workers.

## Features

- User authentication and authorization using JWT tokens
- Transaction management (create, update, delete)
- User subscription management
- Database health monitoring
- Secure password handling
- Docker containerization
- PostgreSQL database integration
- **Background task processing with Celery**
- **Redis message broker integration**
- **Asynchronous data generation and extraction**
- **Task status monitoring and tracking**
- **Comprehensive error handling and logging**
- **Automated testing suite**
- **Development and production build automation**

## Tech Stack

- **Backend Framework**: FastAPI
- **Database**: PostgreSQL
- **ORM**: SQLAlchemy
- **Authentication**: JWT (JSON Web Tokens)
- **Containerization**: Docker & Docker Compose
- **Password Hashing**: Passlib with bcrypt
- **Environment Management**: Python-dotenv
- **Background Tasks**: Celery
- **Message Broker**: Redis
- **Data Processing**: Pandas
- **Testing**: Python unittest framework
- **Build Automation**: Make

## Prerequisites

- Docker and Docker Compose
- Python 3.8+
- PostgreSQL (if running locally)
- Redis (for background task processing)

## Project Structure

```
finance-app/
├── api/
│   ├── auth/                 # Authentication related code
│   ├── database_manager/     # Database connection and management
│   │   ├── models/          # SQLAlchemy models
│   │   ├── connector.py     # Database connection management
│   │   ├── inserter.py      # Data insertion utilities
│   │   └── manage_tables.py # Table management scripts
│   ├── errors/              # Custom error definitions
│   ├── workers/             # Celery background task workers
│   │   └── main.py         # Celery task definitions
│   ├── tests/              # Test suite
│   │   ├── test_redis_connection.py
│   │   └── test_tasks.py
│   ├── data/               # Generated data files
│   ├── logs/               # Application logs
│   ├── secrets/            # Secret files (not tracked in git)
│   ├── sql/                # Database initialization scripts
│   ├── main.py            # Main application file
│   ├── Makefile           # Build and development automation
│   ├── Makefile.dev       # Development-specific commands
│   ├── requirements.txt   # Python dependencies
│   └── .env-template      # Environment variables template
├── FinanceAPI.Dockerfile  # API container configuration
├── Celery.Dockerfile      # Celery worker container configuration
├── docker-compose.yml     # Multi-service orchestration
└── requirements.txt       # Root dependencies
```

## Setup and Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd finance-app
   ```

2. Create necessary secret files:
   - Create `api/sql/secrets/user_credentials.txt` with PostgreSQL password
   - Create `api/secrets/secret_key.txt` with JWT secret key
   - Create `api/secrets/admin_password.txt` with admin password

3. Set up environment variables:
   ```bash
   cp api/.env-template api/.env
   # Edit api/.env with your configuration
   ```

4. Build and run using Docker Compose:
   ```bash
   docker-compose up --build
   ```

## API Endpoints

### Authentication
- `POST /token` - Get access token (login)

### Users
- `POST /create-user` - Create or update user

### Transactions
- `POST /create-transaction` - Create new transaction
- `POST /update-transaction` - Update existing transaction
- `POST /delete-transaction` - Delete transaction

### Data Generation & Background Tasks
- `POST /generate-data` - Start background data generation task
- `GET /task-status/{task_id}` - Check task status and results

### Subscription Management
- `POST /grant-subscription` - Grant subscription to user
- `POST /revoke-subscription` - Revoke user subscription

### Health Check
- `GET /health` - Check API health status

## Background Task Processing

The application now supports asynchronous background task processing using Celery and Redis:

### Data Generation Features
- **Flexible date ranges**: Support for start_date/end_date or days_before parameters
- **Detailed mode**: Generate detailed extracts with additional transaction information
- **Multiple aggregation levels**: Day, week, month, or year grouping
- **CSV export**: Automatic generation of CSV files with transaction data
- **Task monitoring**: Real-time task status tracking and progress monitoring

### Task Configuration
- **Task timeout**: 30 minutes maximum execution time
- **Soft timeout**: 25 minutes with graceful shutdown
- **Worker concurrency**: Configurable worker processes
- **Task persistence**: Redis backend for task result storage

## Environment Variables

The application requires the following environment variables:

- `DATABASE_ENDPOINT`: Database host
- `DATABASE_URL`: Database connection URL
- `DATABASE_USERNAME`: Database username
- `DATABASE_PASSWORD`: Database password
- `DATABASE_PORT`: Database port
- `SECRET_KEY`: JWT secret key
- `ADMIN_USERNAME`: Admin username
- `ADMIN_PASSWORD`: Admin password
- `ADMIN_EMAIL`: Admin email
- `ADMIN_FULL_NAME`: Admin full name
- `REDIS_SERVER`: Redis connection URL (e.g., redis://redis:6379)

## Development

### Using Make Commands
The project includes comprehensive Make automation:

```bash
# Database operations
make create_tables      # Create database tables
make drop_tables        # Drop database tables
make create_user        # Create database users

# Development tasks
make start_api          # Start API with auto-reload
make start_celery       # Start Celery worker with auto-restart
make test_celery_redis_connection  # Test Redis/Celery connectivity

# Debugging
make generate_data      # Test data generation locally
```

### Manual Development Setup
1. Create a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux/Mac
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Start Redis server:
   ```bash
   docker run -d -p 6379:6379 redis:latest
   ```

4. Start the development server:
   ```bash
   uvicorn main:app --reload
   ```

5. Start Celery worker (in separate terminal):
   ```bash
   celery -A workers.main.app worker --loglevel=INFO
   ```

## Docker Deployment

The application is containerized using Docker and Docker Compose with the following services:

- **PostgreSQL**: Database with health checks and volume persistence
- **Redis**: Message broker for Celery tasks with health monitoring
- **Finance API**: Main FastAPI application
- **Celery Worker**: Background task processing service

### Service Architecture
- **Health checks**: All services include health monitoring
- **Dependency management**: Proper service startup order
- **Secret management**: Docker secrets for sensitive data
- **Network isolation**: Custom bridge network for service communication
- **Volume persistence**: Database data persistence across restarts

To deploy:
```bash
docker-compose up -d
```

## Testing

The project includes a comprehensive testing suite:

### Test Coverage
- **Redis Connection Tests**: Verify Redis connectivity and configuration
- **Task Tests**: Validate Celery task functionality
- **Integration Tests**: End-to-end API testing

### Running Tests
```bash
# Test Redis connection
python tests/test_redis_connection.py

# Test Celery tasks
python tests/test_tasks.py
```

## Security

- JWT-based authentication with configurable expiration
- Password hashing using bcrypt
- Environment variables for sensitive data
- Docker secrets for secure credential management
- Database connection pooling and connection monitoring
- Input validation and sanitization
- Comprehensive error handling without information leakage

## Logging and Monitoring

The application implements comprehensive logging:

- **Structured logging**: JSON-formatted log entries
- **Multiple handlers**: File and console output
- **Log levels**: Configurable logging levels per component
- **Error tracking**: Detailed error logging with stack traces
- **Performance monitoring**: Task execution time tracking
- **Health monitoring**: Database and service health checks

### Log Configuration
- Log level: INFO
- Log file: `logs/app.log`
- Console output enabled
- SQLAlchemy and psycopg2 logging reduced to ERROR level

## Error Handling

The application implements robust error handling for:

- **Database errors**: Connection issues, query failures, constraint violations
- **Authentication errors**: Invalid credentials, expired tokens
- **Subscription errors**: Access control and permission issues
- **Client validation errors**: Invalid input data and parameters
- **Transaction validation errors**: Business logic validation
- **Background task errors**: Task execution failures and timeouts
- **Network errors**: Redis and database connectivity issues

## Performance and Scalability

- **Asynchronous processing**: Background task execution
- **Connection pooling**: Database connection optimization
- **Task queuing**: Redis-based message queuing
- **Horizontal scaling**: Multiple Celery workers support
- **Resource management**: Automatic cleanup and resource disposal
- **Caching**: Redis-based caching for improved performance

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Commit your changes with descriptive messages
6. Push to the branch
7. Create a Pull Request

## Troubleshooting

### Common Issues
- **Redis connection errors**: Ensure Redis server is running and accessible
- **Database connection issues**: Check PostgreSQL service health and credentials
- **Task execution failures**: Monitor Celery worker logs for detailed error information
- **Permission errors**: Verify file permissions for logs and data directories

### Debug Commands
```bash
# Check service status
docker-compose ps

# View service logs
docker-compose logs [service-name]

# Test Redis connectivity
make test_celery_redis_connection

# Restart specific service
docker-compose restart [service-name]
```