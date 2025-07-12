from flask import Flask, request, jsonify, session
from flask_cors import CORS
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import json
import re
import requests
from bs4 import BeautifulSoup
import time
from collections import defaultdict
from threading import Lock
import mysql.connector
from mysql.connector import pooling
import bcrypt
import jwt
import os
from functools import wraps

app = Flask(__name__)
# Enable CORS for all routes
CORS(app, resources={r"/*": {"origins": "*"}})

# Secret key for JWT and session
app.secret_key = os.environ.get('SECRET_KEY', '2U6GQN1O2TxEncadQ6lZql')
JWT_SECRET = os.environ.get('JWT_SECRET', 'Nkk8XFQnu7138pth')
JWT_EXPIRATION = 24 * 60 * 60  # 24 hours in seconds

# Database configuration
DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'user': os.environ.get('DB_USER', 'stock_user'),
    'password': os.environ.get('DB_PASSWORD', 'nU)755cIy42u'),
    'database': os.environ.get('DB_NAME', 'stock_analysis_db'),
}

# Create a connection pool
try:
    connection_pool = pooling.MySQLConnectionPool(
        pool_name="stock_analysis_pool",
        pool_size=5,
        **DB_CONFIG
    )
    print("Database connection pool created successfully")
except Exception as e:
    print(f"Error creating database connection pool: {str(e)}")

# Rate limiter implementation
class RateLimiter:
    def __init__(self):
        self.limits = {}  # Store different limits for different endpoints
        self.requests = defaultdict(lambda: defaultdict(list))  # nested defaultdict for endpoint-specific tracking
        self.lock = Lock()

    def add_limit(self, endpoint, max_requests, time_window):
        """Add rate limit for a specific endpoint"""
        self.limits[endpoint] = {
            'max_requests': max_requests,
            'time_window': time_window
        }

    def is_allowed(self, endpoint, ip):
        with self.lock:
            if endpoint not in self.limits:
                return True  # If no limit set for endpoint, allow request
            
            limit_info = self.limits[endpoint]
            current_time = time.time()
            
            # Remove old requests
            self.requests[endpoint][ip] = [
                req_time for req_time in self.requests[endpoint][ip]
                if current_time - req_time < limit_info['time_window']
            ]
            
            # Check if allowed
            if len(self.requests[endpoint][ip]) < limit_info['max_requests']:
                self.requests[endpoint][ip].append(current_time)
                return True
            return False

    def get_remaining_time(self, endpoint, ip):
        with self.lock:
            if endpoint not in self.limits or not self.requests[endpoint][ip]:
                return 0
            
            current_time = time.time()
            oldest_request = min(self.requests[endpoint][ip])
            return max(0, self.limits[endpoint]['time_window'] - (current_time - oldest_request))

    def get_remaining_requests(self, endpoint, ip):
        with self.lock:
            if endpoint not in self.limits:
                return None
            
            current_time = time.time()
            # Clean up old requests first
            self.requests[endpoint][ip] = [
                req_time for req_time in self.requests[endpoint][ip]
                if current_time - req_time < self.limits[endpoint]['time_window']
            ]
            return self.limits[endpoint]['max_requests'] - len(self.requests[endpoint][ip])

# Initialize rate limiter with different limits
rate_limiter = RateLimiter()
rate_limiter.add_limit('/symbol_search', max_requests=50, time_window=60)  # 50 requests per minute
rate_limiter.add_limit('/stock_analysis', max_requests=5, time_window=60)  # 5 requests per minute

# ==================== Authentication Functions ====================

def get_db_connection():
    """Get a connection from the pool"""
    try:
        connection = connection_pool.get_connection()
        return connection
    except Exception as e:
        print(f"Error getting database connection: {str(e)}")
        return None

def hash_password(password):
    """Hash a password for storing"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

def verify_password(stored_hash, provided_password):
    """Verify a stored password against one provided by user"""
    return bcrypt.checkpw(provided_password.encode('utf-8'), stored_hash.encode('utf-8'))

def generate_token(user_id, username):
    """Generate a JWT token"""
    payload = {
        'exp': datetime.utcnow() + timedelta(seconds=JWT_EXPIRATION),
        'iat': datetime.utcnow(),
        'sub': user_id,
        'username': username
    }
    return jwt.encode(payload, JWT_SECRET, algorithm='HS256')

def decode_token(token):
    """Decode a JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None  # Token has expired
    except jwt.InvalidTokenError:
        return None  # Invalid token

def token_required(f):
    """Decorator to protect routes with JWT authentication"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        auth_header = request.headers.get('Authorization')
        
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
        
        if not token:
            return jsonify({'message': 'Authentication token is missing!'}), 401
        
        try:
            payload = decode_token(token)
            if payload is None:
                return jsonify({'message': 'Invalid or expired token!'}), 401
            
            # Add user info to request
            request.user = {
                'id': payload['sub'],
                'username': payload['username']
            }
            
        except Exception as e:
            return jsonify({'message': f'Authentication error: {str(e)}'}), 401
            
        return f(*args, **kwargs)
    
    return decorated

# ==================== Authentication Endpoints ====================

@app.route('/api/login', methods=['POST', 'OPTIONS'])
def login():
    if request.method == 'OPTIONS':
        return handle_options()
    
    data = request.get_json()
    if not data:
        return jsonify({'message': 'No input data provided'}), 400
    
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'message': 'Username and password are required'}), 400
    
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'message': 'Database connection error'}), 500
        
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, username, password_hash FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        cursor.close()
        
        if not user or not verify_password(user['password_hash'], password):
            conn.close()
            return jsonify({'message': 'Invalid username or password'}), 401
        
        # Update last login time
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET last_login = NOW() WHERE id = %s", (user['id'],))
        conn.commit()
        cursor.close()
        conn.close()
        
        # Generate token
        token = generate_token(user['id'], user['username'])
        
        return jsonify({
            'message': 'Login successful',
            'token': token,
            'user': {
                'id': user['id'],
                'username': user['username']
            }
        })
    
    except Exception as e:
        if 'conn' in locals() and conn:
            conn.close()
        return jsonify({'message': f'Login error: {str(e)}'}), 500

@app.route('/api/logout', methods=['POST', 'OPTIONS'])
@token_required
def logout():
    if request.method == 'OPTIONS':
        return handle_options()
    
    # JWT tokens are stateless, so we don't need to do anything server-side
    # The client should discard the token
    
    return jsonify({'message': 'Logout successful'})

@app.route('/api/check-auth', methods=['GET', 'OPTIONS'])
@token_required
def check_auth():
    if request.method == 'OPTIONS':
        return handle_options()
    
    # If we got here, the token is valid
    return jsonify({
        'authenticated': True,
        'user': {
            'id': request.user['id'],
            'username': request.user['username']
        }
    })

class NSEStockAnalyzer:
    def __init__(self, symbol):
        # Clean and standardize the symbol
        symbol = symbol.upper().strip()
        self.today = datetime.now().date()
        
        # Handle different formats
        if symbol.endswith('.NS') or symbol.endswith('.BO'):
            self.symbol = symbol
        else:
            # Default to NSE format
            self.symbol = f"{symbol}.NS"
        
        try:
            print(f"Fetching data for: {self.symbol}")
            self.stock = yf.Ticker(self.symbol)
            self.hist = self.stock.history(period="3y")
            
            if len(self.hist) == 0:
                # Try alternative exchange if NSE fails
                if self.symbol.endswith('.NS'):
                    alt_symbol = self.symbol.replace('.NS', '.BO')
                    print(f"NSE data not found, trying BSE: {alt_symbol}")
                    self.symbol = alt_symbol
                    self.stock = yf.Ticker(self.symbol)
                    self.hist = self.stock.history(period="3y")
            
            # If still no data, raise error
            if len(self.hist) == 0:
                clean_symbol = symbol.replace('.NS', '').replace('.BO', '')
                raise ValueError(f"No data available for {clean_symbol}. This stock may be delisted or not available.")
            
            # Get stock info
            try:
                self.info = self.stock.info
            except Exception as e:
                print(f"Error getting info: {str(e)}")
                self.info = {}
                
            # Set name
            clean_symbol = symbol.replace('.NS', '').replace('.BO', '')
            self.name = self.info.get('shortName', clean_symbol)
            
        except ValueError as ve:
            # Re-raise ValueError for clear error messages
            raise ve
        except Exception as e:
            # Convert other exceptions to ValueError with clear message
            clean_symbol = symbol.replace('.NS', '').replace('.BO', '')
            raise ValueError(f"Error fetching data for {clean_symbol}: {str(e)}")('.BO', '')
            self.name = self.info.get('shortName', clean_symbol)
            
        except ValueError as ve:
            # Re-raise ValueError for clear error messages
            raise ve
        except Exception as e:
            # Convert other exceptions to ValueError with clear message
            clean_symbol = symbol.replace('.NS', '').replace('.BO', '')
            raise ValueError(f"Error fetching data for {clean_symbol}: {str(e)}")
        
    def get_historical_performance(self):
        periods = {
            "1d": 1,
            "1w": 7,
            "1m": 30,
            "3m": 90,
            "1y": 365,
            "3y": 1095
        }
        
        performance = {}
        current_price = self.hist['Close'].iloc[-1]
        
        for period_name, days in periods.items():
            try:
                if len(self.hist) > days:
                    past_price = self.hist['Close'].iloc[-min(days, len(self.hist))]
                    perf = ((current_price - past_price) / past_price) * 100
                    performance[period_name] = f"{perf:.2f}%"
                else:
                    performance[period_name] = "N/A"
            except:
                performance[period_name] = "N/A"
                
        return performance
    
    def get_fundamentals(self):
        fundamentals = {}
        market_cap = self.info.get('marketCap', 0)
        exchange_rate = 83  # USD to INR (approximate)
        market_cap_inr = market_cap * exchange_rate
        fundamentals['market_cap_cr'] = round(market_cap_inr / 10000000, 2)
        fundamentals['pe_ratio'] = round(self.info.get('trailingPE', 0), 2)
        fundamentals['eps'] = round(self.info.get('trailingEps', 0), 2)
        fundamentals['dividend_yield'] = f"{self.info.get('dividendYield', 0) * 100:.2f}%"
        fundamentals['sector_pe'] = round(self.info.get('trailingPE', 0) * 0.9, 2)
        fundamentals['price_to_book'] = round(self.info.get('priceToBook', 0), 2)
        fundamentals['52_week_high'] = round(self.info.get('fiftyTwoWeekHigh', 0), 2)
        fundamentals['52_week_low'] = round(self.info.get('fiftyTwoWeekLow', 0), 2)
        
        return fundamentals
    
    def calculate_technical_indicators(self):
        df = self.hist.copy()
        df['SMA_50'] = df['Close'].rolling(window=50).mean()
        df['SMA_200'] = df['Close'].rolling(window=200).mean()
        df['EMA_20'] = df['Close'].ewm(span=20, adjust=False).mean()
        
        delta = df['Close'].diff()
        gain = delta.where(delta > 0, 0).rolling(window=14).mean()
        loss = -delta.where(delta < 0, 0).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        df['EMA_12'] = df['Close'].ewm(span=12, adjust=False).mean()
        df['EMA_26'] = df['Close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = df['EMA_12'] - df['EMA_26']
        df['Signal_Line'] = df['MACD'].ewm(span=9, adjust=False).mean()
        
        df['BB_Middle'] = df['Close'].rolling(window=20).mean()
        std = df['Close'].rolling(window=20).std()
        df['BB_Upper'] = df['BB_Middle'] + 2 * std
        df['BB_Lower'] = df['BB_Middle'] - 2 * std
        
        df['Volume_10d_Avg'] = df['Volume'].rolling(window=10).mean()
        df['Volume_Ratio'] = df['Volume'] / df['Volume_10d_Avg']
        
        latest = df.iloc[-1]
        
        technical = {
            'moving_averages': {
                'sma_50': round(latest['SMA_50'], 2),
                'sma_200': round(latest['SMA_200'], 2),
                'ema_20': round(latest['EMA_20'], 2)
            },
            'indicators': {
                'rsi': round(latest['RSI'], 2),
                'macd': 'Bullish' if latest['MACD'] > latest['Signal_Line'] else 'Bearish',
                'bollinger_bands': self._get_bb_position(latest)
            }
        }
        
        return technical, df
    
    def _get_bb_position(self, row):
        if row['Close'] > row['BB_Upper']:
            return "Above Upper"
        elif row['Close'] < row['BB_Lower']:
            return "Below Lower"
        elif row['Close'] > row['BB_Middle']:
            return "Upper Half"
        else:
            return "Lower Half"
    
    def get_key_observations(self, df):
        latest = df.iloc[-1]
        observations = []
        
        if latest['Close'] > latest['SMA_50'] and latest['Close'] > latest['SMA_200']:
            observations.append("Trading above 50-day and 200-day moving averages")
        elif latest['Close'] < latest['SMA_50'] and latest['Close'] < latest['SMA_200']:
            observations.append("Trading below 50-day and 200-day moving averages")
        
        if df['SMA_50'].iloc[-2] <= df['SMA_200'].iloc[-2] and df['SMA_50'].iloc[-1] > df['SMA_200'].iloc[-1]:
            observations.append("Golden Cross detected (50-day MA crossed above 200-day MA)")
        elif df['SMA_50'].iloc[-2] >= df['SMA_200'].iloc[-2] and df['SMA_50'].iloc[-1] < df['SMA_200'].iloc[-1]:
            observations.append("Death Cross detected (50-day MA crossed below 200-day MA)")
        
        if latest['RSI'] > 70:
            observations.append("RSI indicates overbought conditions")
        elif latest['RSI'] < 30:
            observations.append("RSI indicates oversold conditions")
        else:
            observations.append("RSI indicates neutral momentum")
        
        if latest['MACD'] > latest['Signal_Line']:
            observations.append("MACD shows bullish momentum")
        else:
            observations.append("MACD shows bearish momentum")
        
        recent_volatility = df['Close'].pct_change().std() * 100
        if recent_volatility > 2:
            observations.append(f"High volatility observed ({recent_volatility:.2f}%)")
        
        avg_volume = df['Volume'].mean()
        recent_volume = df['Volume'].iloc[-5:].mean()
        if recent_volume > avg_volume * 1.5:
            observations.append("Trading volume is above average")
        
        return observations
    
    def get_enhanced_key_observations(self, df):
        latest = df.iloc[-1]
        current_price = latest['Close']
        
        three_month_start = max(0, len(df) - 90)
        three_month_data = df.iloc[three_month_start:]
        three_month_change = ((current_price - three_month_data['Close'].iloc[0]) / 
                             three_month_data['Close'].iloc[0]) * 100
        
        recent_volume = df['Volume'].iloc[-5:].mean()
        volume_10d_avg = df['Volume_10d_Avg'].iloc[-1]
        volume_change_pct = ((recent_volume - volume_10d_avg) / volume_10d_avg) * 100
        
        high_prices = df['High'].iloc[-60:]
        low_prices = df['Low'].iloc[-60:]
        
        resistance_level = round(np.percentile(high_prices, 90), 2)
        support_level = round(np.percentile(low_prices, 10), 2)
        
        upside_target = round(current_price * 1.05, 2)
        strong_upside_target = round(current_price * 1.12, 2)
        
        profit_booking = round(current_price * 1.08, 2)
        
        key_observations = {
            "trend": self._get_trend_description(three_month_change),
            "volume_surge": f"{volume_change_pct:.0f}% compared to the 10-day average",
            "breakout_possibility": f"If {resistance_level} is broken, next target {upside_target}",
            "profit_booking_zone": f"{profit_booking}+"
        }
        
        return key_observations
    
    def _get_trend_description(self, percent_change):
        if percent_change > 20:
            return "Strong bullish momentum in the last 3 months"
        elif percent_change > 10:
            return "Bullish momentum in the last 3 months"
        elif percent_change > 5:
            return "Moderately bullish in the last 3 months"
        elif percent_change > -5:
            return "Sideways movement in the last 3 months"
        elif percent_change > -10:
            return "Moderately bearish in the last 3 months"
        elif percent_change > -20:
            return "Bearish momentum in the last 3 months"
        else:
            return "Strong bearish momentum in the last 3 months"
    
    def get_buy_sell_suggestions(self, df, fundamentals):
        latest = df.iloc[-1]
        current_price = latest['Close']
        
        support_level = round(current_price * 0.95, 2)
        resistance_level = round(current_price * 1.05, 2)
        
        short_term_target1 = round(current_price * 1.10, 2)
        short_term_target2 = round(current_price * 1.20, 2)
        
        long_term_target = round(current_price * 1.40, 2)
        
        stop_loss = round(current_price * 0.92, 2)
        
        buy_zone = round(current_price * 0.97, 2)
        
        bullish_signals = 0
        bearish_signals = 0
        
        if latest['Close'] > latest['SMA_50']:
            bullish_signals += 1
        else:
            bearish_signals += 1
            
        if latest['Close'] > latest['SMA_200']:
            bullish_signals += 1
        else:
            bearish_signals += 1
        
        if latest['RSI'] < 30:
            bullish_signals += 1
        elif latest['RSI'] > 70:
            bearish_signals += 1
        
        if latest['MACD'] > latest['Signal_Line']:
            bullish_signals += 1
        else:
            bearish_signals += 1
        
        if bullish_signals >= 3:
            short_term_action = "Buy"
        elif bullish_signals == 2:
            short_term_action = "Buy on dips"
        elif bearish_signals >= 3:
            short_term_action = "Sell"
        else:
            short_term_action = "Hold"
        
        pe_ratio = fundamentals.get('pe_ratio', 0)
        sector_pe = fundamentals.get('sector_pe', 0)
        
        if latest['Close'] > latest['SMA_200'] and pe_ratio > 0 and pe_ratio < sector_pe * 1.2:
            long_term_action = "Strong Buy"
        elif latest['Close'] > latest['SMA_200']:
            long_term_action = "Buy"
        elif latest['Close'] < latest['SMA_200'] * 0.8:
            long_term_action = "Sell"
        else:
            long_term_action = "Hold"
        
        dividend_yield = fundamentals.get('dividend_yield', '0.00%')
        if float(dividend_yield.replace('%', '')) > 2:
            dividend_stability = "Strong dividend payout"
        elif float(dividend_yield.replace('%', '')) > 1:
            dividend_stability = "Stable dividend payout"
        else:
            dividend_stability = "Low dividend payout"
        
        buy_sell_suggestions = {
            "short_term": {
                "duration": "6M - 1Y",
                "action": short_term_action,
                "buy_zone": buy_zone,
                "target": [short_term_target1, short_term_target2],
                "stop_loss": stop_loss
            },
            "long_term": {
                "duration": "3Y",
                "action": long_term_action,
                "target": long_term_target,
                "dividend_stability": dividend_stability
            }
        }
        
        return buy_sell_suggestions
    
    def get_recommendations(self, df, observations):
        latest = df.iloc[-1]
        
        bullish_signals = 0
        bearish_signals = 0
        
        if latest['Close'] > latest['SMA_50']:
            bullish_signals += 1
        else:
            bearish_signals += 1
            
        if latest['Close'] > latest['SMA_200']:
            bullish_signals += 1
        else:
            bearish_signals += 1
        
        if latest['RSI'] < 30:
            bullish_signals += 1
        elif latest['RSI'] > 70:
            bearish_signals += 1
        
        if latest['MACD'] > latest['Signal_Line']:
            bullish_signals += 1
        else:
            bearish_signals += 1
        
        short_trend = df['Close'].iloc[-30:].mean() > df['Close'].iloc[-60:-30].mean()
        if short_trend:
            bullish_signals += 1
        else:
            bearish_signals += 1
        
        recommendations = {}
        
        if bullish_signals >= 4:
            recommendations['short_term_6m'] = "Buy"
        elif bullish_signals >= 3:
            recommendations['short_term_6m'] = "Hold with potential to accumulate on dips"
        elif bearish_signals >= 4:
            recommendations['short_term_6m'] = "Sell"
        else:
            recommendations['short_term_6m'] = "Hold"
        
        if bullish_signals >= 3 and latest['Close'] > latest['SMA_200']:
            recommendations['short_term_1y'] = "Buy"
        elif bearish_signals >= 3 and latest['Close'] < latest['SMA_200']:
            recommendations['short_term_1y'] = "Sell"
        else:
            recommendations['short_term_1y'] = "Hold"
        
        pe_ratio = self.info.get('trailingPE', 0)
        if latest['Close'] > latest['SMA_200'] and pe_ratio > 0 and pe_ratio < 30:
            recommendations['long_term_3y'] = "Strong Buy"
        elif latest['Close'] > latest['SMA_200']:
            recommendations['long_term_3y'] = "Buy"
        elif latest['Close'] < latest['SMA_200'] * 0.8:
            recommendations['long_term_3y'] = "Sell"
        else:
            recommendations['long_term_3y'] = "Hold"
        
        return recommendations
    
    def get_similar_companies(self):
        sector = self.info.get('sector', '')
        if not sector:
            return []
        
        nse_sector_mapping = {
            'Technology': ['TCS.NS', 'INFY.NS', 'WIPRO.NS', 'HCLTECH.NS', 'TECHM.NS'],
            'Financial Services': ['HDFCBANK.NS', 'ICICIBANK.NS', 'SBIN.NS', 'AXISBANK.NS', 'KOTAKBANK.NS'],
            'Energy': ['RELIANCE.NS', 'ONGC.NS', 'NTPC.NS', 'POWERGRID.NS', 'BPCL.NS'],
            'Consumer Goods': ['HINDUNILVR.NS', 'ITC.NS', 'NESTLEIND.NS', 'BRITANNIA.NS', 'DABUR.NS'],
            'Automobile': ['MARUTI.NS', 'TATAMOTORS.NS', 'M&M.NS', 'HEROMOTOCO.NS', 'BAJAJ-AUTO.NS'],
            'Pharmaceutical': ['SUNPHARMA.NS', 'DRREDDY.NS', 'CIPLA.NS', 'DIVISLAB.NS', 'BIOCON.NS'],
            'Metals': ['TATASTEEL.NS', 'HINDALCO.NS', 'JSWSTEEL.NS', 'VEDL.NS', 'COALINDIA.NS'],
            'Cement': ['ULTRACEMCO.NS', 'SHREECEM.NS', 'ACC.NS', 'AMBUJACEM.NS', 'RAMCOCEM.NS'],
            'Telecom': ['BHARTIARTL.NS', 'IDEA.NS'],
            'Infrastructure': ['LT.NS', 'ADANIPORTS.NS', 'DLF.NS', 'GODREJPROP.NS', 'OBEROIRLTY.NS']
        }
        
        similar_tickers = []
        
        for sector_name, tickers in nse_sector_mapping.items():
            if sector.lower() in sector_name.lower() or sector_name.lower() in sector.lower():
                similar_tickers = [t for t in tickers if t != self.symbol][:3]
                break
        
        if not similar_tickers and len(nse_sector_mapping) > 0:
            default_sector = list(nse_sector_mapping.keys())[0]
            similar_tickers = nse_sector_mapping[default_sector][:3]
        
        similar_companies = []
        for ticker in similar_tickers:
            try:
                stock = yf.Ticker(ticker)
                hist = stock.history(period="1y")
                if len(hist) > 0:
                    start_price = hist['Close'].iloc[0]
                    end_price = hist['Close'].iloc[-1]
                    perf = ((end_price - start_price) / start_price) * 100
                    company_name = stock.info.get('shortName', ticker.replace('.NS', ''))
                    similar_companies.append({
                        "symbol": ticker.replace('.NS', ''),
                        "name": company_name,
                        "performance_1y": f"{perf:.2f}%"
                    })
            except:
                continue
        
        return similar_companies
        
    def calculate_investment_returns(self, investment_amount=10000):
        """Calculate potential returns based on current trend for different time periods"""
        if investment_amount < 1:
            investment_amount = 10000  # Default to 10,000 if invalid amount
            
        # Get historical data to calculate trends
        current_price = self.hist['Close'].iloc[-1]
        
        # Calculate historical returns for different periods
        periods = {
            "1m": 30,  # 1 month
            "6m": 180,  # 6 months
            "1y": 365,  # 1 year
            "3y": 1095  # 3 years
        }
        
        returns = {}
        
        for period_name, days in periods.items():
            try:
                if len(self.hist) > days:
                    # Calculate the rate of return for this period
                    past_price = self.hist['Close'].iloc[-min(days, len(self.hist))]
                    rate_of_return = (current_price - past_price) / past_price
                    
                    # Annualize the rate of return
                    annual_factor = 365 / days
                    annual_rate = ((1 + rate_of_return) ** annual_factor) - 1
                    
                    # Calculate projected returns for each period
                    if period_name == "1m":
                        projected_return = investment_amount * (1 + (annual_rate / 12))
                    elif period_name == "6m":
                        projected_return = investment_amount * (1 + (annual_rate / 2))
                    elif period_name == "1y":
                        projected_return = investment_amount * (1 + annual_rate)
                    elif period_name == "3y":
                        projected_return = investment_amount * ((1 + annual_rate) ** 3)
                    
                    # Calculate absolute and percentage returns
                    absolute_return = projected_return - investment_amount
                    percentage_return = (absolute_return / investment_amount) * 100
                    
                    returns[period_name] = {
                        "projected_amount": round(projected_return, 2),
                        "absolute_return": round(absolute_return, 2),
                        "percentage_return": f"{percentage_return:.2f}%"
                    }
                else:
                    returns[period_name] = {
                        "projected_amount": "N/A",
                        "absolute_return": "N/A",
                        "percentage_return": "N/A"
                    }
            except Exception as e:
                returns[period_name] = {
                    "projected_amount": "N/A",
                    "absolute_return": "N/A",
                    "percentage_return": "N/A",
                    "error": str(e)
                }
        
        return returns
    
    def generate_report(self):
        historical_performance = self.get_historical_performance()
        fundamentals = self.get_fundamentals()
        technical, df = self.calculate_technical_indicators()
        key_observations = self.get_key_observations(df)
        enhanced_key_observations = self.get_enhanced_key_observations(df)
        buy_sell_suggestions = self.get_buy_sell_suggestions(df, fundamentals)
        recommendations = self.get_recommendations(df, key_observations)
        similar_companies = self.get_similar_companies()
        investment_returns = self.calculate_investment_returns(10000)  # Default 10,000 INR investment
        
        report = {
            "symbol": self.symbol.replace('.NS', ''),
            "name": self.name,
            "last_price": round(self.hist['Close'].iloc[-1], 2),
            "historical_performance": historical_performance,
            "fundamentals": fundamentals,
            "technical_analysis": technical,
            "key_observations": key_observations,
            "enhanced_key_observations": enhanced_key_observations,
            "buy_sell_suggestions": buy_sell_suggestions,
            "recommendations": recommendations,
            "similar_companies": similar_companies,
            "investment_returns": investment_returns
        }
        
        return report
    
    def plot_technical_chart(self, save_path=None):
        _, df = self.calculate_technical_indicators()
        
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 10), gridspec_kw={'height_ratios': [3, 1, 1]})
        
        ax1.plot(df.index, df['Close'], label='Close Price')
        ax1.plot(df.index, df['SMA_50'], label='50-day SMA', alpha=0.7)
        ax1.plot(df.index, df['SMA_200'], label='200-day SMA', alpha=0.7)
        ax1.fill_between(df.index, df['BB_Upper'], df['BB_Lower'], alpha=0.1, color='gray')
        ax1.set_title(f'{self.symbol} - Technical Analysis')
        ax1.set_ylabel('Price (â‚¹)')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        ax2.plot(df.index, df['MACD'], label='MACD')
        ax2.plot(df.index, df['Signal_Line'], label='Signal Line')
        ax2.bar(df.index, df['MACD'] - df['Signal_Line'], alpha=0.3, color='green', width=1)
        ax2.set_ylabel('MACD')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        ax3.plot(df.index, df['RSI'], color='purple')
        ax3.axhline(y=70, color='r', linestyle='-', alpha=0.3)
        ax3.axhline(y=30, color='g', linestyle='-', alpha=0.3)
        ax3.fill_between(df.index, df['RSI'], 70, where=(df['RSI'] >= 70), color='r', alpha=0.3)
        ax3.fill_between(df.index, df['RSI'], 30, where=(df['RSI'] <= 30), color='g', alpha=0.3)
        ax3.set_ylabel('RSI')
        ax3.set_xlabel('Date')
        ax3.set_ylim(0, 100)
        ax3.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path)
            return save_path
        else:
            plt.show()
            return None

# ==================== Symbol Search Code ====================

class StockSymbolFinder:
    def __init__(self):
        self.nse_stocks = self._fetch_nse_symbols()
        self.last_fetch_time = time.time()
        self.fetch_interval = 24 * 60 * 60  # 24 hours in seconds

    def _fetch_nse_symbols(self):
        try:
            # Using NSE API to get list of stocks
            url = "https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Connection': 'keep-alive',
            }

            response = requests.get(url, headers=headers)
            all_stocks = []
            
            if response.status_code == 200:
                # Save the CSV content to a temporary file
                with open('temp.csv', 'wb') as f:
                    f.write(response.content)
                
                # Read the CSV file
                df = pd.read_csv('temp.csv')
                
                # Process each row in the DataFrame
                for _, row in df.iterrows():
                    stock = {
                        "company_name": row["NAME OF COMPANY"],
                        "symbol": row["SYMBOL"],
                        "exchange": "NSE"
                    }
                    all_stocks.append(stock)
                
                # Remove temporary file
                import os
                os.remove('temp.csv')
            
            # Add additional stocks that might not be in the CSV
            additional_stocks = [
                {"company_name": "Nifty 50", "symbol": "NIFTY50", "exchange": "NSE"},
                {"company_name": "Nifty Bank", "symbol": "BANKNIFTY", "exchange": "NSE"},
                {"company_name": "Adani Wilmar Ltd", "symbol": "AWL", "exchange": "NSE"},
                {"company_name": "Life Insurance Corporation of India", "symbol": "LICI", "exchange": "NSE"},
                {"company_name": "Tata Technologies Limited", "symbol": "TATATECH", "exchange": "NSE"},
                {"company_name": "JSW Infrastructure Limited", "symbol": "JSWINFRA", "exchange": "NSE"},
                {"company_name": "Jio Financial Services Limited", "symbol": "JIOFIN", "exchange": "NSE"},
                {"company_name": "Mankind Pharma Limited", "symbol": "MANKIND", "exchange": "NSE"}
            ]

            # Add commonly searched stocks
            common_stocks = [
                {"company_name": "Punjab National Bank", "symbol": "PNB", "exchange": "NSE"},
                {"company_name": "State Bank of India", "symbol": "SBIN", "exchange": "NSE"},
                {"company_name": "Indian Railway Catering and Tourism Corporation", "symbol": "IRCTC", "exchange": "NSE"},
                {"company_name": "Rail Vikas Nigam Limited", "symbol": "RVNL", "exchange": "NSE"},
                {"company_name": "Indian Railway Finance Corporation", "symbol": "IRFC", "exchange": "NSE"},
                {"company_name": "Container Corporation of India", "symbol": "CONCOR", "exchange": "NSE"},
                {"company_name": "Bank of Baroda", "symbol": "BANKBARODA", "exchange": "NSE"},
                {"company_name": "Union Bank of India", "symbol": "UNIONBANK", "exchange": "NSE"},
                {"company_name": "Bank of India", "symbol": "BANKINDIA", "exchange": "NSE"},
                {"company_name": "Indian Bank", "symbol": "INDIANB", "exchange": "NSE"},
                {"company_name": "Canara Bank", "symbol": "CANBK", "exchange": "NSE"},
                {"company_name": "UCO Bank", "symbol": "UCOBANK", "exchange": "NSE"},
                {"company_name": "Central Bank of India", "symbol": "CENTRALBK", "exchange": "NSE"},
                {"company_name": "Bank of Maharashtra", "symbol": "MAHABANK", "exchange": "NSE"},
                {"company_name": "Indian Overseas Bank", "symbol": "IOB", "exchange": "NSE"},
                {"company_name": "Yes Bank Limited", "symbol": "YESBANK", "exchange": "NSE"},
                {"company_name": "IDBI Bank Limited", "symbol": "IDBI", "exchange": "NSE"},
                {"company_name": "Federal Bank Limited", "symbol": "FEDERALBNK", "exchange": "NSE"},
                {"company_name": "RBL Bank Limited", "symbol": "RBLBANK", "exchange": "NSE"},
                {"company_name": "South Indian Bank Limited", "symbol": "SOUTHBANK", "exchange": "NSE"},
                {"company_name": "Karnataka Bank Limited", "symbol": "KTKBANK", "exchange": "NSE"},
                {"company_name": "City Union Bank Limited", "symbol": "CUB", "exchange": "NSE"},
                {"company_name": "Dhanlaxmi Bank Limited", "symbol": "DHANBANK", "exchange": "NSE"},
                {"company_name": "Jammu & Kashmir Bank Limited", "symbol": "J&KBANK", "exchange": "NSE"},
                {"company_name": "Karur Vysya Bank Limited", "symbol": "KARURVYSYA", "exchange": "NSE"},
                {"company_name": "Lakshmi Vilas Bank Limited", "symbol": "LAKSHVILAS", "exchange": "NSE"},
                {"company_name": "Tata Motors Limited", "symbol": "TATAMOTORS", "exchange": "NSE"},
                {"company_name": "Maruti Suzuki India Limited", "symbol": "MARUTI", "exchange": "NSE"},
                {"company_name": "Mahindra & Mahindra Limited", "symbol": "M&M", "exchange": "NSE"},
                {"company_name": "TVS Motor Company Limited", "symbol": "TVSMOTOR", "exchange": "NSE"},
                {"company_name": "Hero MotoCorp Limited", "symbol": "HEROMOTOCO", "exchange": "NSE"},
                {"company_name": "Bajaj Auto Limited", "symbol": "BAJAJ-AUTO", "exchange": "NSE"},
                {"company_name": "Eicher Motors Limited", "symbol": "EICHERMOT", "exchange": "NSE"},
                {"company_name": "Ashok Leyland Limited", "symbol": "ASHOKLEY", "exchange": "NSE"},
                {"company_name": "Force Motors Limited", "symbol": "FORCEMOT", "exchange": "NSE"},
                {"company_name": "MRF Limited", "symbol": "MRF", "exchange": "NSE"},
                {"company_name": "Apollo Tyres Limited", "symbol": "APOLLOTYRE", "exchange": "NSE"},
                {"company_name": "CEAT Limited", "symbol": "CEATLTD", "exchange": "NSE"},
                {"company_name": "JK Tyre & Industries Limited", "symbol": "JKTYRE", "exchange": "NSE"},
                {"company_name": "Motherson Sumi Systems Limited", "symbol": "MOTHERSON", "exchange": "NSE"}
            ]

            # Add additional and common stocks if they're not already in the list
            for stock in additional_stocks + common_stocks:
                if stock not in all_stocks:
                    all_stocks.append(stock)

            return all_stocks

        except Exception as e:
            print(f"Error fetching NSE symbols: {str(e)}")
            # Return a comprehensive default list if fetch fails
            default_stocks = [
                # Banks
                {"company_name": "Punjab National Bank", "symbol": "PNB", "exchange": "NSE"},
                {"company_name": "State Bank of India", "symbol": "SBIN", "exchange": "NSE"},
                {"company_name": "Bank of Baroda", "symbol": "BANKBARODA", "exchange": "NSE"},
                {"company_name": "HDFC Bank Ltd.", "symbol": "HDFCBANK", "exchange": "NSE"},
                {"company_name": "ICICI Bank Ltd.", "symbol": "ICICIBANK", "exchange": "NSE"},
                {"company_name": "Axis Bank Ltd.", "symbol": "AXISBANK", "exchange": "NSE"},
                
                # Railways
                {"company_name": "Indian Railway Catering and Tourism Corporation", "symbol": "IRCTC", "exchange": "NSE"},
                {"company_name": "Rail Vikas Nigam Limited", "symbol": "RVNL", "exchange": "NSE"},
                {"company_name": "Indian Railway Finance Corporation", "symbol": "IRFC", "exchange": "NSE"},
                {"company_name": "Container Corporation of India", "symbol": "CONCOR", "exchange": "NSE"},
                
                # IT
                {"company_name": "Tata Consultancy Services Ltd.", "symbol": "TCS", "exchange": "NSE"},
                {"company_name": "Infosys Ltd.", "symbol": "INFY", "exchange": "NSE"},
                {"company_name": "Wipro Ltd.", "symbol": "WIPRO", "exchange": "NSE"},
                {"company_name": "HCL Technologies Ltd.", "symbol": "HCLTECH", "exchange": "NSE"},
                
                # Auto
                {"company_name": "Tata Motors Ltd.", "symbol": "TATAMOTORS", "exchange": "NSE"},
                {"company_name": "Maruti Suzuki India Ltd.", "symbol": "MARUTI", "exchange": "NSE"},
                {"company_name": "Mahindra & Mahindra Ltd.", "symbol": "M&M", "exchange": "NSE"},
                
                # Others
                {"company_name": "Reliance Industries Ltd.", "symbol": "RELIANCE", "exchange": "NSE"},
                {"company_name": "Adani Enterprises Ltd.", "symbol": "ADANIENT", "exchange": "NSE"},
                {"company_name": "ITC Ltd.", "symbol": "ITC", "exchange": "NSE"}
            ]
            return default_stocks
            

    def refresh_symbols_if_needed(self):
        current_time = time.time()
        if current_time - self.last_fetch_time > self.fetch_interval:
            self.nse_stocks = self._fetch_nse_symbols()
            self.last_fetch_time = current_time

    def search_symbol(self, query):
        self.refresh_symbols_if_needed()
        query = query.lower().strip()
        if not query:
            return {"query": query, "results": []}

        results = []
        exact_matches = []
        starts_with_matches = []
        contains_matches = []

        for stock in self.nse_stocks:
            company_name = stock["company_name"].lower()
            symbol = stock["symbol"].lower()
            
            # Check for exact matches
            if query == company_name or query == symbol:
                exact_matches.append(stock)
            # Check for matches at start of company name or symbol
            elif company_name.startswith(query) or symbol.startswith(query):
                starts_with_matches.append(stock)
            # Check for matches anywhere in company name or symbol
            elif query in company_name or query in symbol:
                contains_matches.append(stock)

        # Combine results in order of relevance
        results = exact_matches + starts_with_matches + contains_matches
        
        # Limit results to top 10 matches
        results = results[:10]
        
        return {
            "query": query,
            "results": results
        }

@app.route('/symbol_search', methods=['GET', 'OPTIONS'])
@token_required
def symbol_search():
    if request.method == 'OPTIONS':
        return handle_options()
    
    # Get client IP
    client_ip = request.remote_addr
    
    # Check rate limit
    if not rate_limiter.is_allowed('/symbol_search', client_ip):
        remaining_time = int(rate_limiter.get_remaining_time('/symbol_search', client_ip))
        remaining_requests = rate_limiter.get_remaining_requests('/symbol_search', client_ip)
        response = jsonify({
            "error": "Rate limit exceeded",
            "message": f"Please wait {remaining_time} seconds before trying again",
            "remaining_time": remaining_time,
            "limit": "50 requests per minute",
            "remaining_requests": remaining_requests
        })
        return add_cors_headers(response), 429
        
    query = request.args.get('query', '').strip()
    if not query:
        response = jsonify({"error": "Query is required"})
        return add_cors_headers(response), 400
        
    finder = StockSymbolFinder()
    search_results = finder.search_symbol(query)
@app.route('/stock_analysis', methods=['GET', 'OPTIONS'])
@token_required
def stock_analysis():
    if request.method == 'OPTIONS':
        return handle_options()
    
    # Get client IP
    client_ip = request.remote_addr
    
    # Check rate limit
    if not rate_limiter.is_allowed('/stock_analysis', client_ip):
        remaining_time = int(rate_limiter.get_remaining_time('/stock_analysis', client_ip))
        remaining_requests = rate_limiter.get_remaining_requests('/stock_analysis', client_ip)
        response = jsonify({
            "error": "Rate limit exceeded",
            "message": f"Please wait {remaining_time} seconds before trying again",
            "remaining_time": remaining_time,
            "limit": "5 requests per minute",
            "remaining_requests": remaining_requests
        })
        return add_cors_headers(response), 429
        
    symbol = request.args.get('symbol', '').strip()
    if not symbol:
        response = jsonify({"error": "Symbol is required"})
        return add_cors_headers(response), 400
    
    # Get investment amount if provided
    try:
        investment_amount = float(request.args.get('amount', 10000))
    except ValueError:
        investment_amount = 10000  # Default to 10,000 if invalid amount
        
    try:
        print(f"Analyzing stock: {symbol}")
        analyzer = NSEStockAnalyzer(symbol)
        report = analyzer.generate_report()
        
        # If investment amount is different from default, recalculate returns
        if investment_amount != 10000:
            report['investment_returns'] = analyzer.calculate_investment_returns(investment_amount)
        
        # Add rate limit info to response headers
        response = jsonify(report)
        remaining_requests = rate_limiter.get_remaining_requests('/stock_analysis', client_ip)
        response.headers['X-RateLimit-Limit'] = '5'
        response.headers['X-RateLimit-Remaining'] = str(remaining_requests)
        
        return add_cors_headers(response)
    except ValueError as e:
        # Handle specific ValueError from NSEStockAnalyzer
        response = jsonify({"error": str(e)})
        return add_cors_headers(response), 400
    except Exception as e:
        # Handle other exceptions
        response = jsonify({"error": f"Error analyzing stock: {str(e)}"})
    except ValueError as e:
        # Handle specific ValueError from NSEStockAnalyzer
        print(f"ValueError in stock_analysis: {str(e)}")
        response = jsonify({"error": str(e)})
        return add_cors_headers(response), 400
    except Exception as e:
        # Handle other exceptions
        print(f"Exception in stock_analysis: {str(e)}")
        response = jsonify({"error": f"Error analyzing stock {symbol}: {str(e)}"})
        return add_cors_headers(response), 400

@app.route('/search', methods=['GET', 'OPTIONS'])
@token_required
def search():
    if request.method == 'OPTIONS':
        return handle_options()
    
    # Get client IP
    client_ip = request.remote_addr
    
    # Check rate limit - use symbol_search limit since it's the same functionality
    if not rate_limiter.is_allowed('/symbol_search', client_ip):
        remaining_time = int(rate_limiter.get_remaining_time('/symbol_search', client_ip))
        remaining_requests = rate_limiter.get_remaining_requests('/symbol_search', client_ip)
        response = jsonify({
            "error": "Rate limit exceeded",
            "message": f"Please wait {remaining_time} seconds before trying again",
            "remaining_time": remaining_time,
            "limit": "50 requests per minute",
            "remaining_requests": remaining_requests
        })
        return add_cors_headers(response), 429
        
    query = request.args.get('query', '').strip()
    if not query:
        response = jsonify({"error": "Query is required"})
        return add_cors_headers(response), 400
        
    finder = StockSymbolFinder()
    search_results = finder.search_symbol(query)
    
    # Add rate limit info to response headers
    response = jsonify(search_results)
    remaining_requests = rate_limiter.get_remaining_requests('/symbol_search', client_ip)
    response.headers['X-RateLimit-Limit'] = '50'
    response.headers['X-RateLimit-Remaining'] = str(remaining_requests)
    
    return add_cors_headers(response)

def add_cors_headers(response):
    """Add CORS headers to the response"""
    # CORS is now handled by Flask-CORS
    return response

def handle_options():
    """Handle OPTIONS requests for CORS preflight"""
    response = jsonify({})
    # CORS is now handled by Flask-CORS
    return response

@app.route('/api/stock', methods=['POST', 'OPTIONS'])
@token_required
def stock_api():
    if request.method == 'OPTIONS':
        return handle_options()
        
    # Get client IP
    client_ip = request.remote_addr
    
    # Check rate limit - use stock_analysis limit since it's more restrictive
    if not rate_limiter.is_allowed('/stock_analysis', client_ip):
        remaining_time = int(rate_limiter.get_remaining_time('/stock_analysis', client_ip))
        remaining_requests = rate_limiter.get_remaining_requests('/stock_analysis', client_ip)
        response = jsonify({
            "error": "Rate limit exceeded",
            "message": f"Please wait {remaining_time} seconds before trying again",
            "remaining_time": remaining_time,
            "limit": "5 requests per minute",
            "remaining_requests": remaining_requests
        })
        return add_cors_headers(response), 429
    
    data = request.get_json()
    query = data.get('query', '').strip()
    
    # Get investment amount if provided
    try:
        investment_amount = float(data.get('amount', 10000))
    except (ValueError, TypeError):
        investment_amount = 10000  # Default to 10,000 if invalid amount
    
    if not query:
        response = jsonify({"error": "Query is required"})
        return add_cors_headers(response), 400
    
    try:
        # First, try to get stock analysis directly if it looks like a symbol
        if query.upper() in ['NIFTY50', 'BANKNIFTY'] or '.' not in query or query.upper().endswith('.NS') or query.upper().endswith('.BO'):
            try:
                print(f"Analyzing stock from API: {query}")
                analyzer = NSEStockAnalyzer(query)
                report = analyzer.generate_report()
                
                # If investment amount is different from default, recalculate returns
                if investment_amount != 10000:
                    report['investment_returns'] = analyzer.calculate_investment_returns(investment_amount)
                
                response = jsonify({
                    "type": "analysis",
                    "data": report
                })
                remaining_requests = rate_limiter.get_remaining_requests('/stock_analysis', client_ip)
                response.headers['X-RateLimit-Limit'] = '5'
                response.headers['X-RateLimit-Remaining'] = str(remaining_requests)
                return add_cors_headers(response)
            except ValueError as symbol_error:
                # If direct analysis fails with a specific error, return that error
                response = jsonify({
                    "type": "error",
                    "message": str(symbol_error)
                })
                return add_cors_headers(response), 400
            except Exception:
                # For other errors, proceed with symbol search
                pass
        
        # If not a direct symbol or analysis failed, search for symbols
        finder = StockSymbolFinder()
        search_results = finder.search_symbol(query)
        
        if not search_results['results']:
            response = jsonify({
                "type": "error",
                "message": f"No stocks found matching '{query}'"
            })
            return add_cors_headers(response), 404
        
        # If we have exactly one match and it's an exact match, return analysis
        exact_matches = [s for s in search_results['results'] 
                        if s['symbol'].lower() == query.lower() or 
                        s['company_name'].lower() == query.lower()]
        
        if len(exact_matches) == 1:
            try:
                print(f"Analyzing exact match: {exact_matches[0]['symbol']}")
                analyzer = NSEStockAnalyzer(exact_matches[0]['symbol'])
                report = analyzer.generate_report()
                
                # If investment amount is different from default, recalculate returns
                if investment_amount != 10000:
                    report['investment_returns'] = analyzer.calculate_investment_returns(investment_amount)
                
                response = jsonify({
                    "type": "analysis",
                    "data": report
                })
                remaining_requests = rate_limiter.get_remaining_requests('/stock_analysis', client_ip)
                response.headers['X-RateLimit-Limit'] = '5'
                response.headers['X-RateLimit-Remaining'] = str(remaining_requests)
                return add_cors_headers(response)
            except ValueError as exact_match_error:
                # Return the specific error
                response = jsonify({
                    "type": "error",
                    "message": str(exact_match_error)
                })
                return add_cors_headers(response), 400
        
        # Otherwise return search results
        response = jsonify({
            "type": "search",
            "data": search_results['results']
        })
        remaining_requests = rate_limiter.get_remaining_requests('/symbol_search', client_ip)
        response.headers['X-RateLimit-Limit'] = '50'
        response.headers['X-RateLimit-Remaining'] = str(remaining_requests)
        return add_cors_headers(response)
        
    except Exception as e:
        response = jsonify({
            "type": "error",
            "message": str(e)
        })sponse.headers['X-RateLimit-Limit'] = '50'
        response.headers['X-RateLimit-Remaining'] = str(remaining_requests)
        return add_cors_headers(response)
        
    except Exception as e:
        print(f"General error in stock_api: {str(e)}")
        response = jsonify({
            "type": "error",
            "message": str(e)
        })
        return add_cors_headers(response), 500

@app.route('/similar_company_analysis', methods=['GET', 'OPTIONS'])
@token_required
def similar_company_analysis():
    if request.method == 'OPTIONS':
        return handle_options()
    
    # Get client IP
    client_ip = request.remote_addr
    
    # Check rate limit - use stock_analysis limit since it's similar functionality
    if not rate_limiter.is_allowed('/stock_analysis', client_ip):
        remaining_time = int(rate_limiter.get_remaining_time('/stock_analysis', client_ip))
        remaining_requests = rate_limiter.get_remaining_requests('/stock_analysis', client_ip)
        response = jsonify({
            "error": "Rate limit exceeded",
            "message": f"Please wait {remaining_time} seconds before trying again",
            "remaining_time": remaining_time,
            "limit": "5 requests per minute",
            "remaining_requests": remaining_requests
        })
        return add_cors_headers(response), 429
        
    symbol = request.args.get('symbol', '').strip()
    if not symbol:
        response = jsonify({"error": "Symbol is required"})
        return add_cors_headers(response), 400
        
    try:
        analyzer = NSEStockAnalyzer(symbol)
        report = analyzer.generate_report()
        
        # Add rate limit info to response headers
        response = jsonify(report)
        remaining_requests = rate_limiter.get_remaining_requests('/stock_analysis', client_ip)
        response.headers['X-RateLimit-Limit'] = '5'
        response.headers['X-RateLimit-Remaining'] = str(remaining_requests)
        
        return add_cors_headers(response)
    except Exception as e:
        response = jsonify({"error": str(e)})
        return add_cors_headers(response), 400

@app.route('/calculate_investment_returns', methods=['GET', 'OPTIONS'])
@token_required
def calculate_investment_returns():
    if request.method == 'OPTIONS':
        return handle_options()
    
    # Get client IP
    client_ip = request.remote_addr
    
    # Check rate limit
    if not rate_limiter.is_allowed('/stock_analysis', client_ip):
        remaining_time = int(rate_limiter.get_remaining_time('/stock_analysis', client_ip))
        remaining_requests = rate_limiter.get_remaining_requests('/stock_analysis', client_ip)
        response = jsonify({
            "error": "Rate limit exceeded",
            "message": f"Please wait {remaining_time} seconds before trying again",
            "remaining_time": remaining_time,
            "limit": "5 requests per minute",
            "remaining_requests": remaining_requests
        })
        return add_cors_headers(response), 429
        
    symbol = request.args.get('symbol', '').strip()
    if not symbol:
        response = jsonify({"error": "Symbol is required"})
        return add_cors_headers(response), 400
    
    try:
        investment_amount = float(request.args.get('amount', 10000))
    except ValueError:
        investment_amount = 10000  # Default to 10,000 if invalid amount
    
    try:
        analyzer = NSEStockAnalyzer(symbol)
        returns = analyzer.calculate_investment_returns(investment_amount)
        
        # Add rate limit info to response headers
        response = jsonify({
            "symbol": symbol,
            "investment_amount": investment_amount,
            "returns": returns
        })
        remaining_requests = rate_limiter.get_remaining_requests('/stock_analysis', client_ip)
        response.headers['X-RateLimit-Limit'] = '5'
        response.headers['X-RateLimit-Remaining'] = str(remaining_requests)
        
        return add_cors_headers(response)
    except Exception as e:
        response = jsonify({"error": str(e)})
        return add_cors_headers(response), 400

if __name__ == '__main__':
    print("Starting Stock Analysis API server on http://localhost:5000")
    print("Authentication is enabled - use /api/login endpoint to get a token")
    app.run(host='0.0.0.0', port=5000, debug=True)
