import yfinance as yf
import pandas as pd
import json
import re
import requests
from bs4 import BeautifulSoup
import time

class StockSymbolFinder:
    def __init__(self):
        # Create a database of common NSE stocks
        self.nse_stocks = self._create_nse_database()
    
    def _create_nse_database(self):
        """Create a database of NSE stocks"""
        # This is a simplified database of common NSE stocks
        # In a production environment, you would fetch this from an API or database
        nse_stocks = [
            # Tata Group
            {"company_name": "Tata Consultancy Services Ltd.", "symbol": "TCS", "exchange": "NSE"},
            {"company_name": "Tata Motors Ltd.", "symbol": "TATAMOTORS", "exchange": "NSE"},
            {"company_name": "Tata Steel Ltd.", "symbol": "TATASTEEL", "exchange": "NSE"},
            {"company_name": "Tata Power Company Ltd.", "symbol": "TATAPOWER", "exchange": "NSE"},
            {"company_name": "Tata Consumer Products Ltd.", "symbol": "TATACONSUM", "exchange": "NSE"},
            {"company_name": "Tata Chemicals Ltd.", "symbol": "TATACHEM", "exchange": "NSE"},
            {"company_name": "Tata Communications Ltd.", "symbol": "TATACOMM", "exchange": "NSE"},
            {"company_name": "Tata Elxsi Ltd.", "symbol": "TATAELXSI", "exchange": "NSE"},
            {"company_name": "Tata Investment Corporation Ltd.", "symbol": "TATAINVEST", "exchange": "NSE"},
            
            # Reliance Group
            {"company_name": "Reliance Industries Ltd.", "symbol": "RELIANCE", "exchange": "NSE"},
            {"company_name": "Reliance Infrastructure Ltd.", "symbol": "RELINFRA", "exchange": "NSE"},
            {"company_name": "Reliance Power Ltd.", "symbol": "RPOWER", "exchange": "NSE"},
            
            # HDFC Group
            {"company_name": "HDFC Bank Ltd.", "symbol": "HDFCBANK", "exchange": "NSE"},
            {"company_name": "Housing Development Finance Corporation Ltd.", "symbol": "HDFC", "exchange": "NSE"},
            {"company_name": "HDFC Life Insurance Company Ltd.", "symbol": "HDFCLIFE", "exchange": "NSE"},
            {"company_name": "HDFC Asset Management Company Ltd.", "symbol": "HDFCAMC", "exchange": "NSE"},
            
            # Infosys and other IT
            {"company_name": "Infosys Ltd.", "symbol": "INFY", "exchange": "NSE"},
            {"company_name": "Wipro Ltd.", "symbol": "WIPRO", "exchange": "NSE"},
            {"company_name": "HCL Technologies Ltd.", "symbol": "HCLTECH", "exchange": "NSE"},
            {"company_name": "Tech Mahindra Ltd.", "symbol": "TECHM", "exchange": "NSE"},
            
            # Banking
            {"company_name": "State Bank of India", "symbol": "SBIN", "exchange": "NSE"},
            {"company_name": "ICICI Bank Ltd.", "symbol": "ICICIBANK", "exchange": "NSE"},
            {"company_name": "Axis Bank Ltd.", "symbol": "AXISBANK", "exchange": "NSE"},
            {"company_name": "Kotak Mahindra Bank Ltd.", "symbol": "KOTAKBANK", "exchange": "NSE"},
            
            # Automobile
            {"company_name": "Maruti Suzuki India Ltd.", "symbol": "MARUTI", "exchange": "NSE"},
            {"company_name": "Mahindra & Mahindra Ltd.", "symbol": "M&M", "exchange": "NSE"},
            {"company_name": "Hero MotoCorp Ltd.", "symbol": "HEROMOTOCO", "exchange": "NSE"},
            {"company_name": "Bajaj Auto Ltd.", "symbol": "BAJAJ-AUTO", "exchange": "NSE"},
            
            # Pharma
            {"company_name": "Sun Pharmaceutical Industries Ltd.", "symbol": "SUNPHARMA", "exchange": "NSE"},
            {"company_name": "Dr. Reddy's Laboratories Ltd.", "symbol": "DRREDDY", "exchange": "NSE"},
            {"company_name": "Cipla Ltd.", "symbol": "CIPLA", "exchange": "NSE"},
            {"company_name": "Divi's Laboratories Ltd.", "symbol": "DIVISLAB", "exchange": "NSE"},
            
            # FMCG
            {"company_name": "Hindustan Unilever Ltd.", "symbol": "HINDUNILVR", "exchange": "NSE"},
            {"company_name": "ITC Ltd.", "symbol": "ITC", "exchange": "NSE"},
            {"company_name": "Nestle India Ltd.", "symbol": "NESTLEIND", "exchange": "NSE"},
            {"company_name": "Britannia Industries Ltd.", "symbol": "BRITANNIA", "exchange": "NSE"},
            
            # Energy
            {"company_name": "Oil and Natural Gas Corporation Ltd.", "symbol": "ONGC", "exchange": "NSE"},
            {"company_name": "NTPC Ltd.", "symbol": "NTPC", "exchange": "NSE"},
            {"company_name": "Power Grid Corporation of India Ltd.", "symbol": "POWERGRID", "exchange": "NSE"},
            {"company_name": "Bharat Petroleum Corporation Ltd.", "symbol": "BPCL", "exchange": "NSE"},
            
            # Metals
            {"company_name": "Hindalco Industries Ltd.", "symbol": "HINDALCO", "exchange": "NSE"},
            {"company_name": "JSW Steel Ltd.", "symbol": "JSWSTEEL", "exchange": "NSE"},
            {"company_name": "Vedanta Ltd.", "symbol": "VEDL", "exchange": "NSE"},
            {"company_name": "Coal India Ltd.", "symbol": "COALINDIA", "exchange": "NSE"},
            
            # Cement
            {"company_name": "UltraTech Cement Ltd.", "symbol": "ULTRACEMCO", "exchange": "NSE"},
            {"company_name": "Shree Cement Ltd.", "symbol": "SHREECEM", "exchange": "NSE"},
            {"company_name": "ACC Ltd.", "symbol": "ACC", "exchange": "NSE"},
            {"company_name": "Ambuja Cements Ltd.", "symbol": "AMBUJACEM", "exchange": "NSE"},
            
            # Telecom
            {"company_name": "Bharti Airtel Ltd.", "symbol": "BHARTIARTL", "exchange": "NSE"},
            {"company_name": "Vodafone Idea Ltd.", "symbol": "IDEA", "exchange": "NSE"},
            
            # Infrastructure
            {"company_name": "Larsen & Toubro Ltd.", "symbol": "LT", "exchange": "NSE"},
            {"company_name": "Adani Ports and Special Economic Zone Ltd.", "symbol": "ADANIPORTS", "exchange": "NSE"},
            {"company_name": "DLF Ltd.", "symbol": "DLF", "exchange": "NSE"},
            
            # Adani Group
            {"company_name": "Adani Enterprises Ltd.", "symbol": "ADANIENT", "exchange": "NSE"},
            {"company_name": "Adani Green Energy Ltd.", "symbol": "ADANIGREEN", "exchange": "NSE"},
            {"company_name": "Adani Transmission Ltd.", "symbol": "ADANITRANS", "exchange": "NSE"},
            {"company_name": "Adani Total Gas Ltd.", "symbol": "ATGL", "exchange": "NSE"},
            {"company_name": "Adani Power Ltd.", "symbol": "ADANIPOWER", "exchange": "NSE"},
            
            # Others
            {"company_name": "Asian Paints Ltd.", "symbol": "ASIANPAINT", "exchange": "NSE"},
            {"company_name": "Bajaj Finance Ltd.", "symbol": "BAJFINANCE", "exchange": "NSE"},
            {"company_name": "Bajaj Finserv Ltd.", "symbol": "BAJAJFINSV", "exchange": "NSE"},
            {"company_name": "Titan Company Ltd.", "symbol": "TITAN", "exchange": "NSE"},
            {"company_name": "Grasim Industries Ltd.", "symbol": "GRASIM", "exchange": "NSE"}
        ]
        
        return nse_stocks
    
    def _fetch_nse_symbols_from_web(self):
        """Fetch NSE symbols from web (as a fallback)"""
        try:
            # This is a simplified approach - in a real scenario, you'd use a more reliable source
            url = "https://www1.nseindia.com/content/equities/EQUITY_L.csv"
            df = pd.read_csv(url)
            
            stocks = []
            for _, row in df.iterrows():
                stocks.append({
                    "company_name": row["NAME OF COMPANY"],
                    "symbol": row["SYMBOL"],
                    "exchange": "NSE"
                })
            
            return stocks
        except:
            print("Failed to fetch NSE symbols from web. Using built-in database.")
            return []
    
    def search_symbol(self, query):
        """Search for a company symbol based on a query"""
        query = query.lower()
        results = []
        
        # Search in the database
        for stock in self.nse_stocks:
            company_name = stock["company_name"].lower()
            symbol = stock["symbol"].lower()
            
            # Check if query is in company name or symbol
            if query in company_name or query in symbol:
                results.append(stock)
        
        # If no results, try to fetch from web
        if not results:
            web_stocks = self._fetch_nse_symbols_from_web()
            for stock in web_stocks:
                company_name = stock["company_name"].lower()
                symbol = stock["symbol"].lower()
                
                # Check if query is in company name or symbol
                if query in company_name or query in symbol:
                    results.append(stock)
        
        # Sort results by relevance (exact matches first, then partial matches)
        sorted_results = []
        
        # First, add exact matches
        for stock in results:
            company_name = stock["company_name"].lower()
            symbol = stock["symbol"].lower()
            
            if query == company_name or query == symbol:
                sorted_results.append(stock)
        
        # Then, add partial matches that haven't been added yet
        for stock in results:
            if stock not in sorted_results:
                sorted_results.append(stock)
        
        # Limit to top 10 results
        sorted_results = sorted_results[:10]
        
        return {
            "query": query,
            "results": sorted_results
        }

    def search_symbol_with_yfinance(self, query):
        """Search for a company symbol using yfinance (experimental)"""
        try:
            # This is experimental and may not work reliably
            tickers = yf.Tickers(f"{query}*")
            results = []
            
            for ticker in tickers.tickers:
                if ticker.endswith(".NS"):
                    info = tickers.tickers[ticker].info
                    results.append({
                        "company_name": info.get("longName", ticker),
                        "symbol": ticker.replace(".NS", ""),
                        "exchange": "NSE"
                    })
            
            return {
                "query": query,
                "results": results
            }
        except:
            print("Failed to search with yfinance. Using built-in database.")
            return self.search_symbol(query)

def search_nse_symbol(query):
    """Main function to search for NSE symbols"""
    finder = StockSymbolFinder()
    results = finder.search_symbol(query)
    
    # Print results
    print(f"Search results for '{query}':")
    print("-" * 50)
    
    if not results["results"]:
        print("No results found.")
    else:
        for i, result in enumerate(results["results"], 1):
            print(f"{i}. {result['company_name']} ({result['symbol']})")
    
    print("-" * 50)
    
    # Return results as JSON
    return json.dumps(results, indent=2)

# Example usage
print("NSE Stock Symbol Finder")
print("======================")
print("This script helps you find NSE stock symbols based on company names.")
print("Example searches: 'Tata', 'Reliance', 'HDFC', 'Adani', etc.")
print()

# Test with 'Tata'
tata_results = search_nse_symbol("Tata")
print("\nJSON Output:")
print(tata_results)

# Test with 'Reliance'
reliance_results = search_nse_symbol("Reliance")
print("\nJSON Output:")
print(reliance_results)

# Test with 'Adani'
adani_results = search_nse_symbol("Adani")
print("\nJSON Output:")
print(adani_results)

print("\nHow to use this function:")
print("1. Call search_nse_symbol('QUERY') with any company name or partial symbol")
print("2. The function returns a JSON string with search results")
print("\nExample usage in Python:")
print("results_json = search_nse_symbol('HDFC')")
print("results = json.loads(results_json)")