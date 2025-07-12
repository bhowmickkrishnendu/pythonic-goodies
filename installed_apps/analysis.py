import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import json
import os
from tabulate import tabulate

class NSEStockAnalyzer:
    def __init__(self, symbol):
        # Format symbol for NSE
        if not symbol.endswith('.NS'):
            self.symbol = f"{symbol.upper()}.NS"
        else:
            self.symbol = symbol.upper()
            
        self.stock = yf.Ticker(self.symbol)
        self.today = datetime.now().date()
        
        # Get historical data for 3 years
        self.hist = self.stock.history(period="3y")
        
        # Check if data is available
        if len(self.hist) == 0:
            raise ValueError(f"No data available for symbol {self.symbol}")
            
        self.info = self.stock.info
        self.name = self.info.get('shortName', self.symbol.replace('.NS', ''))
        
    def get_historical_performance(self):
        """Calculate historical performance for different time periods"""
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
        """Extract fundamental metrics"""
        fundamentals = {}
        
        # Market Cap in Cr (converting from USD to INR and then to Cr)
        # Assuming 1 Cr = 10M INR
        market_cap = self.info.get('marketCap', 0)
        # Convert to INR (approximate conversion)
        exchange_rate = 83  # USD to INR (approximate)
        market_cap_inr = market_cap * exchange_rate
        fundamentals['market_cap_cr'] = round(market_cap_inr / 10000000, 2)
        
        # Other metrics
        fundamentals['pe_ratio'] = round(self.info.get('trailingPE', 0), 2)
        fundamentals['eps'] = round(self.info.get('trailingEps', 0), 2)
        fundamentals['dividend_yield'] = f"{self.info.get('dividendYield', 0) * 100:.2f}%"
        
        # Sector PE (approximation)
        fundamentals['sector_pe'] = round(self.info.get('trailingPE', 0) * 0.9, 2)  # Approximation
        fundamentals['price_to_book'] = round(self.info.get('priceToBook', 0), 2)
        
        # Add 52-week high and low
        fundamentals['52_week_high'] = round(self.info.get('fiftyTwoWeekHigh', 0), 2)
        fundamentals['52_week_low'] = round(self.info.get('fiftyTwoWeekLow', 0), 2)
        
        return fundamentals
    
    def calculate_technical_indicators(self):
        """Calculate technical indicators"""
        df = self.hist.copy()
        
        # Moving Averages
        df['SMA_50'] = df['Close'].rolling(window=50).mean()
        df['SMA_200'] = df['Close'].rolling(window=200).mean()
        df['EMA_20'] = df['Close'].ewm(span=20, adjust=False).mean()
        
        # RSI
        delta = df['Close'].diff()
        gain = delta.where(delta > 0, 0).rolling(window=14).mean()
        loss = -delta.where(delta < 0, 0).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # MACD
        df['EMA_12'] = df['Close'].ewm(span=12, adjust=False).mean()
        df['EMA_26'] = df['Close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = df['EMA_12'] - df['EMA_26']
        df['Signal_Line'] = df['MACD'].ewm(span=9, adjust=False).mean()
        
        # Bollinger Bands
        df['BB_Middle'] = df['Close'].rolling(window=20).mean()
        std = df['Close'].rolling(window=20).std()
        df['BB_Upper'] = df['BB_Middle'] + 2 * std
        df['BB_Lower'] = df['BB_Middle'] - 2 * std
        
        # Volume indicators
        df['Volume_10d_Avg'] = df['Volume'].rolling(window=10).mean()
        df['Volume_Ratio'] = df['Volume'] / df['Volume_10d_Avg']
        
        # Get latest values
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
        """Determine position within Bollinger Bands"""
        if row['Close'] > row['BB_Upper']:
            return "Above Upper"
        elif row['Close'] < row['BB_Lower']:
            return "Below Lower"
        elif row['Close'] > row['BB_Middle']:
            return "Upper Half"
        else:
            return "Lower Half"
    
    def get_key_observations(self, df):
        """Generate key observations based on technical analysis"""
        latest = df.iloc[-1]
        observations = []
        
        # Moving Averages
        if latest['Close'] > latest['SMA_50'] and latest['Close'] > latest['SMA_200']:
            observations.append("Trading above 50-day and 200-day moving averages")
        elif latest['Close'] < latest['SMA_50'] and latest['Close'] < latest['SMA_200']:
            observations.append("Trading below 50-day and 200-day moving averages")
        
        # Golden/Death Cross
        if df['SMA_50'].iloc[-2] <= df['SMA_200'].iloc[-2] and df['SMA_50'].iloc[-1] > df['SMA_200'].iloc[-1]:
            observations.append("Golden Cross detected (50-day MA crossed above 200-day MA)")
        elif df['SMA_50'].iloc[-2] >= df['SMA_200'].iloc[-2] and df['SMA_50'].iloc[-1] < df['SMA_200'].iloc[-1]:
            observations.append("Death Cross detected (50-day MA crossed below 200-day MA)")
        
        # RSI
        if latest['RSI'] > 70:
            observations.append("RSI indicates overbought conditions")
        elif latest['RSI'] < 30:
            observations.append("RSI indicates oversold conditions")
        else:
            observations.append("RSI indicates neutral momentum")
        
        # MACD
        if latest['MACD'] > latest['Signal_Line']:
            observations.append("MACD shows bullish momentum")
        else:
            observations.append("MACD shows bearish momentum")
        
        # Volatility
        recent_volatility = df['Close'].pct_change().std() * 100
        if recent_volatility > 2:
            observations.append(f"High volatility observed ({recent_volatility:.2f}%)")
        
        # Volume
        avg_volume = df['Volume'].mean()
        recent_volume = df['Volume'].iloc[-5:].mean()
        if recent_volume > avg_volume * 1.5:
            observations.append("Trading volume is above average")
        
        return observations
    
    def get_enhanced_key_observations(self, df):
        """Generate enhanced key observations with more detailed analysis"""
        latest = df.iloc[-1]
        current_price = latest['Close']
        
        # Analyze 3-month trend
        three_month_start = max(0, len(df) - 90)
        three_month_data = df.iloc[three_month_start:]
        three_month_change = ((current_price - three_month_data['Close'].iloc[0]) / 
                             three_month_data['Close'].iloc[0]) * 100
        
        # Volume analysis
        recent_volume = df['Volume'].iloc[-5:].mean()
        volume_10d_avg = df['Volume_10d_Avg'].iloc[-1]
        volume_change_pct = ((recent_volume - volume_10d_avg) / volume_10d_avg) * 100
        
        # Resistance and support levels (simplified)
        high_prices = df['High'].iloc[-60:]
        low_prices = df['Low'].iloc[-60:]
        
        # Find clusters of highs and lows
        resistance_level = round(np.percentile(high_prices, 90), 2)
        support_level = round(np.percentile(low_prices, 10), 2)
        
        # Next targets
        upside_target = round(current_price * 1.05, 2)  # 5% up
        strong_upside_target = round(current_price * 1.12, 2)  # 12% up
        
        # Profit booking zone
        profit_booking = round(current_price * 1.08, 2)  # 8% up
        
        # Create the enhanced observations
        key_observations = {
            "trend": self._get_trend_description(three_month_change),
            "volume_surge": f"{volume_change_pct:.0f}% compared to the 10-day average",
            "breakout_possibility": f"If {resistance_level} is broken, next target {upside_target}",
            "profit_booking_zone": f"{profit_booking}+"
        }
        
        return key_observations
    
    def _get_trend_description(self, percent_change):
        """Generate a descriptive trend based on percentage change"""
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
        """Generate detailed buy/sell suggestions with price targets"""
        latest = df.iloc[-1]
        current_price = latest['Close']
        
        # Calculate potential support and resistance levels
        support_level = round(current_price * 0.95, 2)  # 5% down
        resistance_level = round(current_price * 1.05, 2)  # 5% up
        
        # Short-term targets
        short_term_target1 = round(current_price * 1.10, 2)  # 10% up
        short_term_target2 = round(current_price * 1.20, 2)  # 20% up
        
        # Long-term target
        long_term_target = round(current_price * 1.40, 2)  # 40% up
        
        # Stop loss
        stop_loss = round(current_price * 0.92, 2)  # 8% down
        
        # Buy zone
        buy_zone = round(current_price * 0.97, 2)  # 3% down
        
        # Determine action based on technical indicators
        bullish_signals = 0
        bearish_signals = 0
        
        # Moving Averages
        if latest['Close'] > latest['SMA_50']:
            bullish_signals += 1
        else:
            bearish_signals += 1
            
        if latest['Close'] > latest['SMA_200']:
            bullish_signals += 1
        else:
            bearish_signals += 1
        
        # RSI
        if latest['RSI'] < 30:
            bullish_signals += 1
        elif latest['RSI'] > 70:
            bearish_signals += 1
        
        # MACD
        if latest['MACD'] > latest['Signal_Line']:
            bullish_signals += 1
        else:
            bearish_signals += 1
        
        # Determine short-term action
        if bullish_signals >= 3:
            short_term_action = "Buy"
        elif bullish_signals == 2:
            short_term_action = "Buy on dips"
        elif bearish_signals >= 3:
            short_term_action = "Sell"
        else:
            short_term_action = "Hold"
        
        # Determine long-term action based on fundamentals and trend
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
        
        # Dividend stability
        dividend_yield = fundamentals.get('dividend_yield', '0.00%')
        if float(dividend_yield.replace('%', '')) > 2:
            dividend_stability = "Strong dividend payout"
        elif float(dividend_yield.replace('%', '')) > 1:
            dividend_stability = "Stable dividend payout"
        else:
            dividend_stability = "Low dividend payout"
        
        # Create buy/sell suggestions
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
        """Generate recommendations based on analysis"""
        latest = df.iloc[-1]
        
        # Simple recommendation logic
        bullish_signals = 0
        bearish_signals = 0
        
        # Moving Averages
        if latest['Close'] > latest['SMA_50']:
            bullish_signals += 1
        else:
            bearish_signals += 1
            
        if latest['Close'] > latest['SMA_200']:
            bullish_signals += 1
        else:
            bearish_signals += 1
        
        # RSI
        if latest['RSI'] < 30:
            bullish_signals += 1
        elif latest['RSI'] > 70:
            bearish_signals += 1
        
        # MACD
        if latest['MACD'] > latest['Signal_Line']:
            bullish_signals += 1
        else:
            bearish_signals += 1
        
        # Trend
        short_trend = df['Close'].iloc[-30:].mean() > df['Close'].iloc[-60:-30].mean()
        if short_trend:
            bullish_signals += 1
        else:
            bearish_signals += 1
        
        # Generate recommendations
        recommendations = {}
        
        # Short term (6m)
        if bullish_signals >= 4:
            recommendations['short_term_6m'] = "Buy"
        elif bullish_signals >= 3:
            recommendations['short_term_6m'] = "Hold with potential to accumulate on dips"
        elif bearish_signals >= 4:
            recommendations['short_term_6m'] = "Sell"
        else:
            recommendations['short_term_6m'] = "Hold"
        
        # Short term (1y)
        if bullish_signals >= 3 and latest['Close'] > latest['SMA_200']:
            recommendations['short_term_1y'] = "Buy"
        elif bearish_signals >= 3 and latest['Close'] < latest['SMA_200']:
            recommendations['short_term_1y'] = "Sell"
        else:
            recommendations['short_term_1y'] = "Hold"
        
        # Long term (3y)
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
        """Find similar companies based on sector"""
        sector = self.info.get('sector', '')
        if not sector:
            return []
        
        # NSE top companies by sector (simplified)
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
        
        # Try to find similar companies
        for sector_name, tickers in nse_sector_mapping.items():
            if sector.lower() in sector_name.lower() or sector_name.lower() in sector.lower():
                similar_tickers = [t for t in tickers if t != self.symbol][:3]
                break
        
        # If no match found, use a default sector
        if not similar_tickers and len(nse_sector_mapping) > 0:
            # Just pick the first sector as default
            default_sector = list(nse_sector_mapping.keys())[0]
            similar_tickers = nse_sector_mapping[default_sector][:3]
        
        # Get performance data for similar companies
        similar_companies = []
        for ticker in similar_tickers:
            try:
                stock = yf.Ticker(ticker)
                hist = stock.history(period="1y")
                if len(hist) > 0:
                    start_price = hist['Close'].iloc[0]
                    end_price = hist['Close'].iloc[-1]
                    perf = ((end_price - start_price) / start_price) * 100
                    similar_companies.append({
                        "symbol": ticker.replace('.NS', ''),
                        "performance_1y": f"{perf:.2f}%"
                    })
            except:
                continue
        
        return similar_companies
    
    def generate_report(self):
        """Generate a complete stock analysis report"""
        historical_performance = self.get_historical_performance()
        fundamentals = self.get_fundamentals()
        technical, df = self.calculate_technical_indicators()
        key_observations = self.get_key_observations(df)
        enhanced_key_observations = self.get_enhanced_key_observations(df)
        buy_sell_suggestions = self.get_buy_sell_suggestions(df, fundamentals)
        recommendations = self.get_recommendations(df, key_observations)
        similar_companies = self.get_similar_companies()
        
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
            "similar_companies": similar_companies
        }
        
        return report
    
    def plot_technical_chart(self, save_path=None):
        """Plot technical chart with indicators"""
        _, df = self.calculate_technical_indicators()
        
        # Create figure with subplots
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 10), gridspec_kw={'height_ratios': [3, 1, 1]})
        
        # Price and Moving Averages
        ax1.plot(df.index, df['Close'], label='Close Price')
        ax1.plot(df.index, df['SMA_50'], label='50-day SMA', alpha=0.7)
        ax1.plot(df.index, df['SMA_200'], label='200-day SMA', alpha=0.7)
        ax1.fill_between(df.index, df['BB_Upper'], df['BB_Lower'], alpha=0.1, color='gray')
        ax1.set_title(f'{self.symbol} - Technical Analysis')
        ax1.set_ylabel('Price (₹)')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # MACD
        ax2.plot(df.index, df['MACD'], label='MACD')
        ax2.plot(df.index, df['Signal_Line'], label='Signal Line')
        ax2.bar(df.index, df['MACD'] - df['Signal_Line'], alpha=0.3, color='green', width=1)
        ax2.set_ylabel('MACD')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        # RSI
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

def analyze_nse_stock(symbol):
    """Main function to analyze an NSE stock and generate report"""
    try:
        analyzer = NSEStockAnalyzer(symbol)
        report = analyzer.generate_report()
        
        # Save chart
        chart_path = f"{symbol}_technical_chart.png"
        analyzer.plot_technical_chart(save_path=chart_path)
        
        # Print report summary
        print(f"\n{'='*50}")
        print(f"NSE STOCK ANALYSIS REPORT: {report['name']} ({report['symbol']})")
        print(f"{'='*50}")
        print(f"Current Price: ₹{report['last_price']}")
        
        print("\nHistorical Performance:")
        for period, perf in report['historical_performance'].items():
            print(f"  {period}: {perf}")
        
        print("\nFundamentals:")
        for key, value in report['fundamentals'].items():
            print(f"  {key.replace('_', ' ').title()}: {value}")
        
        print("\nTechnical Indicators:")
        print("  Moving Averages:")
        for ma, value in report['technical_analysis']['moving_averages'].items():
            print(f"    {ma.upper()}: {value}")
        print("  Other Indicators:")
        for ind, value in report['technical_analysis']['indicators'].items():
            print(f"    {ind.upper()}: {value}")
        
        print("\nKey Observations:")
        for obs in report['key_observations']:
            print(f"  • {obs}")
        
        print("\nEnhanced Key Observations:")
        for key, value in report['enhanced_key_observations'].items():
            print(f"  • {key.replace('_', ' ').title()}: {value}")
        
        print("\nBuy/Sell Suggestions:")
        print("  Short Term (6M-1Y):")
        st = report['buy_sell_suggestions']['short_term']
        print(f"    Action: {st['action']}")
        print(f"    Buy Zone: ₹{st['buy_zone']}")
        print(f"    Targets: ₹{st['target'][0]}, ₹{st['target'][1]}")
        print(f"    Stop Loss: ₹{st['stop_loss']}")
        
        print("  Long Term (3Y):")
        lt = report['buy_sell_suggestions']['long_term']
        print(f"    Action: {lt['action']}")
        print(f"    Target: ₹{lt['target']}")
        print(f"    Dividend: {lt['dividend_stability']}")
        
        print("\nRecommendations:")
        for term, rec in report['recommendations'].items():
            print(f"  {term.replace('_', ' ').title()}: {rec}")
        
        if report['similar_companies']:
            print("\nSimilar Companies:")
            for comp in report['similar_companies']:
                print(f"  {comp['symbol']} (1Y Performance: {comp['performance_1y']})")
        
        print(f"\nTechnical chart saved as: {chart_path}")
        print(f"{'='*50}")
        
        # Save report as JSON
        json_path = f"{symbol}_analysis_report.json"
        with open(json_path, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"Full report saved as: {json_path}")
        
        return report
        
    except Exception as e:
        print(f"Error analyzing {symbol}: {str(e)}")
        return None

# Example usage
print("Enhanced NSE Stock Analysis Tool")
print("-------------------------------")
print("This script analyzes NSE (National Stock Exchange of India) stocks using free data from Yahoo Finance.")
print("It provides technical analysis, fundamental data, and detailed buy/sell recommendations.")
print("\nRunning a sample analysis for RELIANCE...")

# Run a sample analysis for a popular NSE stock
try:
    sample_report = analyze_nse_stock('RELIANCE')
    
    # Show sample JSON structure for the new sections
    print("\nSample Enhanced Key Observations and Buy/Sell Suggestions:")
    enhanced_sample = {
        "enhanced_key_observations": sample_report["enhanced_key_observations"],
        "buy_sell_suggestions": sample_report["buy_sell_suggestions"]
    }
    print(json.dumps(enhanced_sample, indent=2))
    
    print("\nHow to use this script:")
    print("1. Call analyze_nse_stock('SYMBOL') with any NSE stock symbol")
    print("   (No need to add .NS suffix, the script handles it automatically)")
    print("2. The function returns a report dictionary and saves:")
    print("   - A technical chart as PNG")
    print("   - A full report as JSON")
    print("\nExample usage in Python:")
    print("report = analyze_nse_stock('TCS')")
    print("report = analyze_nse_stock('INFY')")
    print("report = analyze_nse_stock('HDFCBANK')")
    
except Exception as e:
    print(f"Error in sample analysis: {str(e)}")
    print("\nTrying another popular NSE stock...")
    try:
        sample_report = analyze_nse_stock('TCS')
    except Exception as e:
        print(f"Error in second sample analysis: {str(e)}")