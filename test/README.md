# Stock Analysis API with Authentication

This is a Flask-based web application that provides stock analysis for Indian stocks listed on the National Stock Exchange (NSE). The application includes authentication to protect API endpoints.

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Up MySQL Database

Create a MySQL database and users table:

```sql
-- Create database
CREATE DATABASE stock_analysis_db;

-- Use the database
USE stock_analysis_db;

-- Create users table
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP NULL
);
```

### 3. Configure Environment Variables

Set the following environment variables or update the default values in the code:

```bash
export DB_HOST=localhost
export DB_USER=your_mysql_username
export DB_PASSWORD=your_mysql_password
export DB_NAME=stock_analysis_db
export SECRET_KEY=your_secret_key_for_session
export JWT_SECRET=your_jwt_secret_key
```

### 4. Add Users

Run the add_user.py script to add users to the database:

```bash
python add_user.py
```

### 5. Run the Application

```bash
python app.py
```

## API Endpoints

### Authentication

- **POST /api/login**: Login with username and password
  - Request body: `{"username": "your_username", "password": "your_password"}`
  - Response: `{"message": "Login successful", "token": "your_jwt_token", "user": {"id": 1, "username": "your_username"}}`

- **POST /api/logout**: Logout (requires authentication)
  - Headers: `Authorization: Bearer your_jwt_token`
  - Response: `{"message": "Logout successful"}`

- **GET /api/check-auth**: Check if authenticated
  - Headers: `Authorization: Bearer your_jwt_token`
  - Response: `{"authenticated": true, "user": {"id": 1, "username": "your_username"}}`

### Stock Analysis (All require authentication)

- **GET /symbol_search**: Search for stock symbols
  - Headers: `Authorization: Bearer your_jwt_token`
  - Query parameters: `query=your_search_query`

- **GET /stock_analysis**: Get detailed analysis for a specific stock
  - Headers: `Authorization: Bearer your_jwt_token`
  - Query parameters: `symbol=stock_symbol`

- **POST /api/stock**: Combined endpoint for search and analysis
  - Headers: `Authorization: Bearer your_jwt_token`
  - Request body: `{"query": "your_search_query", "amount": 10000}`

## Authentication Flow

1. Client sends login credentials to `/api/login`
2. Server validates credentials and returns a JWT token
3. Client includes the token in the Authorization header for subsequent requests
4. Server validates the token for each protected endpoint

## Notes

- JWT tokens expire after 24 hours
- All API endpoints except `/api/login` require authentication
- Rate limiting is still applied to authenticated requests