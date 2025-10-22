import streamlit as st
import yfinance as yf
import pandas as pd
import streamlit as st
import base64
import plotly.express as px
import io # Used to read text input and create downloadable files
import time # For retry logic and showing refresh time

# --- CORE FUNCTIONS ---

def parse_portfolio_input(uploaded_file):
    """
    Parses the user uploaded CSV file into a structured DataFrame.
    Expected format (header optional): TICKER,SHARES,AVG_COST
    """
    if uploaded_file is None:
        return pd.DataFrame()
        
    try:
        # Read the uploaded file object (Streamlit handles the file)
        # Use pandas to read the CSV content directly
        df = pd.read_csv(uploaded_file, 
                         header=None, # Assume no header unless explicitly needed
                         names=['Ticker', 'Shares', 'Avg_Cost'], 
                         dtype={'Shares': float, 'Avg_Cost': float})
        
        # Basic validation and cleanup
        df = df[df['Shares'] > 0]
        df['Ticker'] = df['Ticker'].str.upper().str.strip()
        
        # Ensure Ticker is the index for merging later
        return df.set_index('Ticker')
        
    except Exception as e:
        st.error(f"Error parsing uploaded file. Ensure the format is TICKER,SHARES,AVG_COST on each line. Error: {e}")
        return pd.DataFrame()


def get_realtime_data(portfolio_df):
    """
    Fetches real-time stock data (current price, previous close) 
    by looping through each ticker for robust results.
    """
    if portfolio_df.empty:
        return None
        
    results = []
    
    # Iterate through the portfolio to fetch data and calculate metrics
    for ticker, row in portfolio_df.iterrows():
        shares = row['Shares']
        avg_cost = row['Avg_Cost']
        
        try:
            # Use yf.Ticker().info for the most direct and reliable current data
            ticker_info = yf.Ticker(ticker).info
            current_price = ticker_info.get('currentPrice') or ticker_info.get('regularMarketPrice')
            prev_close = ticker_info.get('previousClose')

            if pd.notna(current_price) and pd.notna(prev_close):
                current_value = current_price * shares
                total_cost = avg_cost * shares
                
                # Daily performance
                daily_change_value = current_price - prev_close
                daily_gain_loss = daily_change_value * shares
                daily_percent_change = (daily_change_value / prev_close) * 100
                
                # Total performance
                total_pl = current_value - total_cost
                total_pl_percent = (total_pl / total_cost) * 100 if total_cost > 0 else 0
                
                results.append({
                    'Ticker': ticker,
                    'Shares': shares,
                    'Avg_Cost': avg_cost,
                    'Current Price': current_price,
                    'Previous Close': prev_close,
                    'Current Value': current_value,
                    'Total Cost': total_cost,
                    'Daily Gain/Loss $': daily_gain_loss,
                    'Daily % Change': daily_percent_change,
                    'Total P/L $': total_pl,
                    'Total P/L %': total_pl_percent,
                })
            else:
                st.warning(f"Skipping {ticker}: Could not retrieve current price or previous close.")

        except Exception as e:
            st.warning(f"Skipping {ticker}: Error fetching data. Ensure the ticker is valid. ({e})")
            
    if not results:
        return None

    return pd.DataFrame(results)


@st.cache_data(ttl=3600) # Cache historical data for 1 hour
def get_historical_prices(tickers, days=30):
    """Fetches historical close prices for the last N days."""
    if not tickers:
        return pd.DataFrame()
    
    # Use yf.download for multiple tickers for historical data
    try:
        hist_data = yf.download(tickers, period=f"{days}d", progress=False)
        # Handle the case where only one ticker is returned (no multi-index)
        if len(tickers) == 1:
            return hist_data['Close'].to_frame()
        # Return the Close column from the multi-index DataFrame
        return hist_data['Close']
    except Exception as e:
        st.error(f"Error fetching historical data: {e}")
        return pd.DataFrame()

# --- UTILITIES ---

def to_excel(df):
    """Converts a DataFrame to an Excel binary file."""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Portfolio_Summary')
    processed_data = output.getvalue()
    return processed_data


# --- STREAMLIT APP LAYOUT ---

def app():
    # Set the cache TTL based on a user selection in the sidebar
    refresh_options = {
        "Manual Refresh Only": 99999, # Effectively disable auto-refresh
        "5 Minutes": 300,
        "1 Minute": 60,
    }
    # Set page config (your existing code)
    st.set_page_config(layout="wide", page_title="My Portfolio Tracker")

    # --- ADD THE LOGO TO THE SIDEBAR HERE ---
    with st.sidebar:
       
        st.image(
            'logo sential wealth.png',
            caption='Sentinel Wealth', 
            width=200 # Optional: Adjust the size (usually recommended to specify a width)
        )
        
        # --- Your existing sidebar code would go below the logo ---
        st.markdown(
            """
            *Your Personal Portfolio Tracker*
            """,
            unsafe_allow_html=True
        )


    st.title("Sentinel Wealth")
    st.markdown("The advanced features of **Sentinel Wealth** allow for multi-asset tracking and real-time performance updates.")
    
    # --- Sidebar Configuration ---
    st.sidebar.header("Data Management")
    
    # 1. CSV File Uploader
    st.sidebar.markdown("**1. Upload Holdings (CSV)**")
    uploaded_file = st.sidebar.file_uploader(
        "Upload a CSV file (TICKER,SHARES,AVG_COST)",
        type=["csv"]
    )

    if uploaded_file is None:
        st.sidebar.info("Please upload your portfolio CSV file.")
        
    portfolio_df_config = parse_portfolio_input(uploaded_file)

    if portfolio_df_config.empty:
        st.info("Upload a CSV in the sidebar to begin tracking.")
        return

    # 2. Refresh Settings
    st.sidebar.markdown("---")
    st.sidebar.markdown("**2. Real-time Refresh**")
    
    # User selects refresh interval
    refresh_label = st.sidebar.selectbox(
        "Auto-Refresh Interval",
        options=list(refresh_options.keys())
    )
    refresh_ttl = refresh_options[refresh_label]

    # --- Data Processing and Caching (Uses selected TTL) ---
    
    @st.cache_data(ttl=refresh_ttl, show_spinner="Fetching latest market data...") 
    def cached_realtime_fetch(config_df):
        return get_realtime_data(config_df)

    realtime_df = cached_realtime_fetch(portfolio_df_config)
    
    if realtime_df is None or realtime_df.empty:
        st.error("Dashboard failed to load or has no valid assets to display.")
        st.stop()
        
    # Manual Refresh Button
    if st.sidebar.button("Manual Refresh"):
        # Clear cache and force rerun (streamlit's cache is cleared automatically when ttl expires)
        st.cache_data.clear()
        st.rerun()


    # --- Global Metrics Calculation ---
    total_value = realtime_df['Current Value'].sum()
    total_cost = realtime_df['Total Cost'].sum()
    total_daily_gain = realtime_df['Daily Gain/Loss $'].sum()
    total_pl = realtime_df['Total P/L $'].sum()
    total_prev_value = (realtime_df['Previous Close'] * realtime_df['Shares']).sum()
    
    portfolio_daily_percent = (total_daily_gain / total_prev_value) * 100 if total_prev_value > 0 else 0
        
    # --- Dashboard Metrics Layout ---
    st.header("Real-Time Performance")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            label="Total Portfolio Value", 
            value=f"${total_value:,.2f}", 
            delta=f"${total_daily_gain:,.2f} ({portfolio_daily_percent:.2f}%)"
        )
        
    with col2:
        st.metric(
            label="Total Invested Cost", 
            value=f"${total_cost:,.2f}"
        )
        
    with col3:
        total_pl_delta = total_pl / total_cost * 100 if total_cost > 0 else 0
        st.metric(
            label="Overall Lifetime P/L", 
            value=f"${total_pl:,.2f}",
            delta=f"{total_pl_delta:.2f}%"
        )
        
    st.markdown("---")
    
    # --- Visualizations ---
    
    col_vis1, col_vis2 = st.columns([2, 1])

    # 1. Historical Line Chart (Last 30 days)
    with col_vis1:
        st.subheader("Last 30 Days Price Trend (Historical)")
        
        tickers = realtime_df['Ticker'].tolist()
        history_df = get_historical_prices(tickers, days=30)
        
        if not history_df.empty:
            plot_data = history_df.reset_index().melt(
                id_vars='Date', 
                var_name='Ticker', 
                value_name='Close Price'
            )
            fig = px.line(
                plot_data, 
                x='Date', 
                y='Close Price', 
                color='Ticker', 
                title='Historical Closing Prices',
                template='plotly_white'
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Historical price data not available for charting.")

    # 2. Portfolio Distribution Pie Chart
    with col_vis2:
        st.subheader("Asset Distribution")
        pie_data = realtime_df[realtime_df['Current Value'] > 0]
        
        if not pie_data.empty:
            fig_pie = px.pie(
                pie_data, 
                values='Current Value', 
                names='Ticker', 
                title='Portfolio Value Distribution',
                hole=.3, 
                color_discrete_sequence=px.colors.sequential.RdBu 
            )
            fig_pie.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
             st.info("No assets to display in the pie chart.")
             
    st.markdown("---")

    # 3. Detailed Holdings Table and Export
    st.subheader("Detailed Holdings")
    
    # Prepare the DataFrame for display and export
    export_df = realtime_df.copy()
    
    # Format columns for display only
    display_df = export_df.copy()
    display_df['Current Price'] = display_df['Current Price'].map('${:,.2f}'.format)
    display_df['Current Value'] = display_df['Current Value'].map('${:,.2f}'.format)
    display_df['Daily % Change'] = display_df['Daily % Change'].map('{:.2f}%'.format)
    display_df['Total P/L $'] = display_df['Total P/L $'].map('${:,.2f}'.format)
    display_df['Total P/L %'] = display_df['Total P/L %'].map('{:.2f}%'.format)
    
    # Select columns for final table display
    final_table_df = display_df[[
        'Ticker', 'Shares', 'Current Price', 'Current Value', 
        'Daily % Change', 'Total P/L $', 'Total P/L %'
    ]]
    
    st.dataframe(final_table_df, use_container_width=True, hide_index=True)

    # Export Button (placed after the table)
    st.download_button(
        label="Download Full Data as Excel",
        data=to_excel(export_df),
        file_name='pro_portfolio_summary.xlsx',
        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

    # ... (All your main Streamlit content goes here) ...

    # Add a horizontal line to separate the main content from the footer
    st.markdown("---") 

    # --- FOOTER CONTENT ---

    # Define your profile URLs
    GITHUB_URL = "YOUR_GITHUB_REPOSITORY_LINK" # e.g., "https://github.com/yourusername/yourrepo"
    LINKEDIN_URL = "YOUR_LINKEDIN_PROFILE_LINK" # e.g., "https://www.linkedin.com/in/yourname/"
    
    # Define image URLs for logos (using external sources or hosting your own)
    # Using generic favicon services or simple images for demonstration:
    GITHUB_LOGO_URL = "https://cdn-icons-png.flaticon.com/32/733/733609.png" # Simple GitHub icon
    LINKEDIN_LOGO_URL = "https://cdn-icons-png.flaticon.com/32/174/174857.png" # Simple LinkedIn icon

    # Use a two-column layout: Left for the main text, Right for the icons
    col_left, col_right = st.columns([5, 1]) 
    
    with col_left:
        st.markdown(
            f"""
            **Made with Streamlit** | Built by Gopika
            """,
            unsafe_allow_html=True
        )

    with col_right:
        st.markdown(
            f"""
            <div style="display: flex; gap: 10px;">
                <a href="https://www.linkedin.com/in/gopika-b-0151a7275/" target="_blank">
                    <img src="https://img.icons8.com/ios-filled/50/linkedin.png" alt="LinkedIn" style="height: 24px; width: 24px;">
                </a>
                <a href="https://github.com/hyuksinja" target="_blank">
                    <img src="https://img.icons8.com/ios-glyphs/30/github.png" alt="GitHub" style="height: 24px; width: 24px;">
                </a>
            </div>
            """, 
            unsafe_allow_html=True
        )

# Call the app function (if you aren't using a multi-page app structure)
# if __name__ == '__main__':
#     app()

if __name__ == '__main__':
    app()

