# Finance App API

A FastAPI-based financial management application that handles user authentication, transactions, and subscription management.

## Features

- User authentication and authorization using JWT tokens
- Transaction management (create, update, delete)
- User subscription management
- Database health monitoring
- Secure password handling
- Docker containerization
- PostgreSQL database integration

## Tech Stack

- **Backend Framework**: FastAPI
- **Database**: PostgreSQL
- **ORM**: SQLAlchemy
- **Authentication**: JWT (JSON Web Tokens)
- **Containerization**: Docker & Docker Compose
- **Password Hashing**: Passlib with bcrypt
- **Environment Management**: Python-dotenv

## Prerequisites

- Docker and Docker Compose
- Python 3.8+
- PostgreSQL (if running locally)

## Project Structure

```
finance-app/
├── auth/                 # Authentication related code
├── database_manager/     # Database connection and management
├── errors/              # Custom error definitions
├── secrets/             # Secret files (not tracked in git)
├── sql/                 # Database initialization scripts
├── main.py             # Main application file
├── requirements.txt     # Python dependencies
├── Dockerfile          # Docker configuration
└── docker-compose.yml  # Docker Compose configuration
```

## Setup and Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd finance-app
   ```

2. Create necessary secret files:
   - Create `sql/secrets/user_credentials.txt` with PostgreSQL password
   - Create `secrets/secret_key.txt` with JWT secret key
   - Create `secrets/admin_password.txt` with admin password

3. Build and run using Docker Compose:
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

### Subscription Management
- `POST /grant-subscription` - Grant subscription to user
- `POST /revoke-subscription` - Revoke user subscription

### Health Check
- `GET /health` - Check API health status

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

## Development

1. Create a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux/Mac
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the development server:
   ```bash
   uvicorn main:app --reload
   ```

## Docker Deployment

The application is containerized using Docker and Docker Compose. The setup includes:

- PostgreSQL database container
- Finance API container
- Network configuration
- Volume management for database persistence
- Secret management for sensitive data

To deploy:

```bash
docker-compose up -d
```

## Security

- JWT-based authentication
- Password hashing using bcrypt
- Environment variables for sensitive data
- Docker secrets for secure credential management
- Database connection pooling
- Input validation and sanitization

## Logging

The application uses Python's logging module with the following configuration:
- Log level: INFO
- Log file: app.log
- Console output enabled
- SQLAlchemy and psycopg2 logging reduced to ERROR level

## Error Handling

The application implements custom error handling for:
- Database errors
- Authentication errors
- Subscription errors
- Client validation errors
- Transaction validation errors

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request