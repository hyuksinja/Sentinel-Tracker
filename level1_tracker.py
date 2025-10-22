import yfinance as yf
import pandas as pd
from math import floor

# --- CONFIGURATION: YOUR PORTFOLIO ---
# Define your holdings: Ticker, Shares owned, and Average Cost Per Share (in USD)
PORTFOLIO = {
    'AAPL': {'shares': 10, 'avg_cost': 170.00},
    'TSLA': {'shares': 5, 'avg_cost': 220.00},
    'MSFT': {'shares': 8, 'avg_cost': 300.00},
    'GOOGL': {'shares': 3, 'avg_cost': 145.00},
}
# ----------------------------------------


def get_portfolio_summary(portfolio):
    """
    Fetches real-time stock data, calculates performance metrics,
    and returns a summary DataFrame.
    """
    tickers = list(portfolio.keys())
    
    # 1. Fetch real-time data using yfinance
    # The ticker.info dictionary contains hundreds of data points
    stock_data = [yf.Ticker(t).info for t in tickers]

    # Extract relevant fields and match with portfolio
    data = []
    for info in stock_data:
        ticker = info.get('symbol')
        # We need the current price and the previous day's closing price
        current_price = info.get('regularMarketPrice', info.get('currentPrice'))
        previous_close = info.get('previousClose')
        
        # Merge portfolio data
        holdings = portfolio.get(ticker, {})
        shares = holdings.get('shares', 0)
        avg_cost = holdings.get('avg_cost', 0)
        
        if current_price and previous_close and shares > 0:
            # 2. Calculate Metrics
            current_value = current_price * shares
            total_cost = avg_cost * shares
            
            # Daily change calculation
            daily_change_value = current_price - previous_close
            daily_change_percent = (daily_change_value / previous_close) * 100
            
            # Total P/L calculation
            profit_loss = current_value - total_cost
            
            data.append({
                'Ticker': ticker,
                'Shares': shares,
                'Current Price': current_price,
                'Prev Close': previous_close,
                'Current Value': current_value,
                'Total Cost': total_cost,
                'Daily Change $': daily_change_value * shares,
                'Daily % Change': daily_change_percent,
                'Total P/L $': profit_loss,
                'Total P/L %': (profit_loss / total_cost) * 100 if total_cost > 0 else 0
            })
        else:
            print(f"Warning: Could not fetch complete data for {ticker}. Skipping...")

    if not data:
        return None

    df = pd.DataFrame(data)
    return df


def display_summary(df):
    """
    Prints the calculated portfolio performance in a clean, readable format.
    """
    if df is None:
        print("\n--- Portfolio Summary ---")
        print("No valid stock data was processed.")
        return
        
    # --- Individual Stock Summary ---
    print("\n--- Individual Holdings Performance ---")
    for index, row in df.iterrows():
        daily_percent = f"{row['Daily % Change']:.2f}%"
        # Determine color for daily change (for visual clarity in terminal)
        daily_color = '\033[92m' if row['Daily Change $'] >= 0 else '\033[91m' # Green/Red ANSI codes
        
        print(
            f"{row['Ticker']:<5} | "
            f"Price: ${row['Current Price']:<9.2f} | "
            f"Daily: {daily_color}{'+' if row['Daily Change $'] >= 0 else ''}{daily_percent:<6}\033[0m | " # \033[0m resets color
            f"Total P/L: ${row['Total P/L $']:,.2f}"
        )

    # --- Aggregate Portfolio Summary ---
    
    # Sum up the columns for portfolio totals
    total_value = df['Current Value'].sum()
    total_cost = df['Total Cost'].sum()
    total_daily_gain = df['Daily Change $'].sum()
    
    # Calculate overall daily percentage change based on previous day's total value
    # We need the sum of previous day's close * shares for an accurate comparison
    df['Prev Day Value'] = df['Prev Close'] * df['Shares']
    total_prev_value = df['Prev Day Value'].sum()
    
    # Calculate Portfolio Daily % Change
    if total_prev_value > 0:
        portfolio_daily_percent = (total_daily_gain / total_prev_value) * 100
    else:
        portfolio_daily_percent = 0.0
        
    # Calculate Overall Total P/L
    total_profit_loss = total_value - total_cost
    
    # Formatting for final output
    total_daily_gain_fmt = f"{'+' if total_daily_gain >= 0 else ''}{total_daily_gain:,.2f}"
    portfolio_daily_percent_fmt = f"{'+' if portfolio_daily_percent >= 0 else ''}{portfolio_daily_percent:.2f}%"
    
    daily_color = '\033[92m' if total_daily_gain >= 0 else '\033[91m'

    print("\n" + "="*40)
    print(f"--- AGGREGATE PORTFOLIO PERFORMANCE ---")
    print(f"Current Market Value: ${total_value:,.2f}")
    print(f"Total Daily Change: {daily_color}{total_daily_gain_fmt} ({portfolio_daily_percent_fmt})\033[0m")
    print(f"Overall Lifetime P/L: ${total_profit_loss:,.2f}")
    print("="*40 + "\n")


if __name__ == '__main__':
    # Execute the main function
    try:
        portfolio_data = get_portfolio_summary(PORTFOLIO)
        display_summary(portfolio_data)
    except Exception as e:
        print(f"An error occurred during execution: {e}")
        print("Please check your internet connection or stock tickers.")
