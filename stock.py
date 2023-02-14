import streamlit as st
import streamlit.components.v1 as components
from streamlit import session_state as ss
# from streamlit_option_menu import option_menu as on
import requests
from datetime import datetime
import yfinance as yf
import datetime
from datetime import date
from prophet import Prophet
from prophet.plot import plot_plotly
from st_aggrid import AgGrid
import pandas as pd 
import plotly.graph_objects as go
import matplotlib.pyplot as plt
from pprint import pprint 
from finnews.client import News

import os 


# Page Setting
st.set_page_config(layout="wide")

#Initial UI 
ticker = st.text_input('Ticker', "NFLX").upper()
buttonClicked = st.button('Search')

# Dashboard
start_date = "2020-01-01"
today = date.today().strftime("%Y-%m-%d")

#Load dataset


def load_data(ticker):
    stock_data=yf.download(ticker, start_date , today, interval="1wk")
    stock_data.reset_index(inplace=True)
    return stock_data

#Load dataset 2nd stock
def load_2nddata(ticker):
    stock_data2=yf.download(ticker, start_date , today, interval="1wk")
    stock_data2.reset_index(inplace=True)
    return stock_data2




#Callbacks
if st.button:
      link  = f"""https://query1.finance.yahoo.com/v10/finance/quoteSummary/{ticker}?"""
      modules = f"""modules=assetProfile%2Cprice%2CfinancialData%2CearningsTrend%2CdefaultKeyStatistics"""
      requestString = link + modules
      request = requests.get(f"{requestString}", headers={"USER-AGENT": "Mozilla/5.0"})
      json = request.json()
      data = json["quoteSummary"]["result"][0]
      st.session_state.data = data
    
      if 'data' in st.session_state:
        data = st.session_state.data

          # Tradingview Graph
        st.components.v1.html(
            f"""
            <div class="tradingview-widget-container">
            <div id="tradingview_866ee"></div>
            <div class="tradingview-widget-copyright"><a href="https://www.tradingview.com/symbols/NASDAQ-{ticker}/" rel="noopener" target="_blank"><span class="blue-text">{ticker} stock chart</span></a> by TradingView</div>
            <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
            <script type="text/javascript">
            new TradingView.widget(
            {{
            "symbol": "{ticker}",
            "height":800,
            "width":1250,
            "interval": "D",
            "timezone": "Etc/UTC",
            "theme": "dark",
            "style": "1",
            "locale": "en",
            "toolbar_bg": "#f1f3f6",
            "enable_publishing": false,
            "allow_symbol_change": true,
            "studies": [
            "MACD@tv-basicstudies",
            "RSI@tv-basicstudies"
            ],
            "container_id": "tradingview_866ee"
            
            }}
            );
            </script>
            </div>
            <!-- TradingView Widget END -->
            """, 
           height=800, width=1285)


        # Collect Data from Yahoo finance API
    

        # Print Company Profile
        st.header("Company Profile")
        st.subheader(ticker)
        with st.expander("About Company"):
          st.write(data["assetProfile"]["longBusinessSummary"])
        st.metric("sector", data["assetProfile"]["sector"])
        st.metric("industry", data["assetProfile"]["industry"])
        st.metric("website", data["assetProfile"]["website"])
      
        
        # Get the metrics needed for valuation
        currentPrice = data["financialData"]["currentPrice"]["raw"]
        growth = data["earningsTrend"]["trend"][4]["growth"]["raw"] * 100
        peFWD = data["defaultKeyStatistics"]["forwardPE"]["raw"]
        epsFWD = data["defaultKeyStatistics"]["forwardEps"]["raw"]
        requiredRateOfReturn = 10.0
        yearsToProject = 10

      
        
        st.header("Stock Valuation") 

      #User Input area
        growth = st.number_input("Growth", value=growth, step=1.0)
        peFWD = st.number_input("PE", value=peFWD, step=1.0)
        requireRateOfReturn=st.number_input("Required Rate Of Return", value=requiredRateOfReturn, step=1.0)

        # Formula Setting
        df_stock = load_data(ticker)

        def pv(fv,requiredRateOfReturn,yearsToProject):
          return fv / ((1 + requiredRateOfReturn / 100) ** yearsToProject)


        def fv(pv,growth,yearsToProject):
          return pv * (1 + growth)  ** yearsToProject

      st.session_state.data = data
            

      # Fair value calculation
      futureEPS = fv(epsFWD, growth/100, yearsToProject)
      futurePrice = futureEPS * peFWD 
      stickerPrice = pv(futurePrice, requiredRateOfReturn, yearsToProject)
      upside = (stickerPrice - currentPrice)/stickerPrice * 100

      # Show result
      kpi1, kpi2, kpi3 = st.columns(3)
      kpi4, kpi5, kpi6 = st.columns(3)
      kpi1.metric("Market Cap", data["price"]["marketCap"]["fmt"])
      kpi2.metric("EPS", "{:.2f}".format(futureEPS))
      kpi3.metric("Current Price", "{:.2f}".format(currentPrice))
      kpi4.metric("Sticker Price", "{:.2f}".format(stickerPrice))
      kpi5.metric("Future Price", "{:.2f}".format(futurePrice))
      kpi6.metric("Upside", "{:.2f}".format(upside))  

      df_stock = load_data(ticker)

      #Forecast stock price 
      st.header("AI Stock Price Prediction") 
      nyears = st.slider("Predited years:", 1,5)
      period = nyears*365
      df_train = df_stock[["Date", "Close"]]
      df_train = df_train.rename(columns={"Date":"ds", "Close":"y"})
      m = Prophet(daily_seasonality=True)
      m.fit(df_train)
      future = m.make_future_dataframe(periods=period,freq='D')
      future['day'] = future['ds'].dt.weekday
      future = future[future['day']<=4]
      forecast = m.predict(future)

      st.subheader("Forecast stock")
      with st.expander("Show raw data"):
          st.subheader(f"Raw data of {ticker}")
          st.write(forecast.tail())

      fore_fig = plot_plotly(m, forecast)
      st.plotly_chart(fore_fig, use_container_width = True)
      # fore_fig2 = m.plot_components(forecast, figsize=(8,4))
      # st.write(fore_fig2)



      # Institution Holder
      st.subheader("""**Institutional Shareholder**for """+ ticker)
      stockbginfo = yf.Ticker(ticker)
      display_instholders=(stockbginfo.institutional_holders)
      AgGrid(display_instholders)

      st.bar_chart(display_instholders,y="Shares", x="Holder")
      
      # MutualFund Holder
      st.subheader("""**MutualFund Holder**for """+ ticker)
      display_mutualholders=stockbginfo.mutualfund_holders
      AgGrid(stockbginfo.mutualfund_holders)

      st.bar_chart(display_mutualholders,y="Shares", x="Holder")

      # Option Chain
      st.subheader("""**Option Chain**for """+ ticker)
      st.markdown("<h3 style='text-align: center; color: white;'>Call Option</h3>", unsafe_allow_html=True)
      stockbginfo.option_chain().calls
      st.markdown("<h3 style='text-align: center; color: ;'>Put Option</h3>", unsafe_allow_html=True)
      stockbginfo.option_chain().puts

      

      

      
