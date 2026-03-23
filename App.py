# Nitish's AI Trading Bot Dashboard
# Opens as a live webpage - refresh anytime!

import streamlit as st
import yfinance as yf
import anthropic
import json
import os
from datetime import datetime

# -----------------------------------------------
# PAGE SETUP
# -----------------------------------------------
st.set_page_config(
    page_title="Nitish's Trading Bot",
    page_icon="⚡",
    layout="wide"
)

# -----------------------------------------------
# CUSTOM STYLING
# -----------------------------------------------
st.markdown("""
<style>
    .main { background-color: #070e16; }
    .stApp { background-color: #070e16; }
    
    .big-metric {
        background: #0f1923;
        border: 1px solid #1e2d3d;
        border-radius: 12px;
        padding: 20px;
        text-align: center;
    }
    .metric-label {
        font-size: 11px;
        color: #3a5a74;
        letter-spacing: 2px;
        text-transform: uppercase;
        margin-bottom: 8px;
    }
    .metric-value {
        font-size: 24px;
        font-weight: 700;
        color: #ffffff;
    }
    .green { color: #00ff88 !important; }
    .red { color: #ff4466 !important; }
    .blue { color: #4da6ff !important; }
    
    .stock-card {
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 8px;
    }
    .trade-row {
        background: #0f1923;
        border-radius: 8px;
        padding: 12px 16px;
        margin-bottom: 6px;
        display: flex;
        gap: 12px;
    }
    div[data-testid="stMetricValue"] {
        color: white;
        font-size: 22px;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------
# STOCKS LIST
# -----------------------------------------------
STOCKS = {
    "Reliance":  "RELIANCE.NS",
    "TCS":       "TCS.NS",
    "Infosys":   "INFY.NS",
    "HDFC Bank": "HDFCBANK.NS",
    "Wipro":     "WIPRO.NS"
}

# -----------------------------------------------
# LOAD PORTFOLIO
# -----------------------------------------------
def load_portfolio():
    default = {
        "cash": 100000,
        "holdings": {},
        "trades": [],
        "created": str(datetime.now().strftime('%d %b %Y'))
    }
    try:
        if os.path.exists("portfolio.json"):
            with open("portfolio.json", "r") as f:
                return json.load(f)
    except:
        pass
    return default

def save_portfolio(wallet):
    with open("portfolio.json", "w") as f:
        json.dump(wallet, f, indent=2)

# -----------------------------------------------
# FETCH PRICES
# -----------------------------------------------
@st.cache_data(ttl=60)  # Cache for 60 seconds
def fetch_prices():
    prices = {}
    for name, symbol in STOCKS.items():
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            prices[name] = {
                "symbol": symbol,
                "price": info.get("currentPrice", 0),
                "change": info.get("regularMarketChangePercent", 0),
                "high": info.get("dayHigh", 0),
                "low": info.get("dayLow", 0),
                "volume": info.get("regularMarketVolume", 0),
            }
        except:
            prices[name] = {
                "symbol": symbol,
                "price": 0, "change": 0,
                "high": 0, "low": 0, "volume": 0
            }
    return prices

# -----------------------------------------------
# GET AI DECISION
# -----------------------------------------------
def get_ai_decision(name, price, api_key):
    try:
        client = anthropic.Anthropic(api_key=api_key)
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=50,
            messages=[{
                "role": "user",
                "content": f"Indian NSE stock: {name}, Price: ₹{price}. Reply with ONLY one word: BUY or SELL or HOLD"
            }]
        )
        decision = msg.content[0].text.strip().upper()
        if "BUY" in decision: return "BUY"
        elif "SELL" in decision: return "SELL"
        return "HOLD"
    except:
        return "HOLD"

# -----------------------------------------------
# EXECUTE TRADE
# -----------------------------------------------
def execute_trade(wallet, name, symbol, price, decision):
    if decision == "BUY":
        amount = wallet["cash"] * 0.20
        shares = int(amount / price)
        if shares > 0 and wallet["cash"] >= shares * price:
            cost = shares * price
            wallet["cash"] -= cost
            if name in wallet["holdings"]:
                wallet["holdings"][name]["shares"] += shares
            else:
                wallet["holdings"][name] = {
                    "shares": shares,
                    "avg_price": price,
                    "symbol": symbol
                }
            wallet["trades"].append({
                "date": datetime.now().strftime('%d %b %Y %I:%M %p'),
                "action": "BUY",
                "stock": name,
                "shares": shares,
                "price": price,
                "total": cost
            })
            return f"✅ Bought {shares} shares @ ₹{price:,.2f}"
        return "⚠️ Not enough cash"
    
    elif decision == "SELL":
        if name in wallet["holdings"]:
            shares = wallet["holdings"][name]["shares"]
            earned = shares * price
            avg = wallet["holdings"][name]["avg_price"]
            pnl = (price - avg) * shares
            wallet["cash"] += earned
            del wallet["holdings"][name]
            wallet["trades"].append({
                "date": datetime.now().strftime('%d %b %Y %I:%M %p'),
                "action": "SELL",
                "stock": name,
                "shares": shares,
                "price": price,
                "total": earned,
                "pnl": pnl
            })
            return f"✅ Sold {shares} shares @ ₹{price:,.2f} | P&L: ₹{pnl:+,.2f}"
        return "⚠️ No shares to sell"
    
    return "⏸️ Holding"

# -----------------------------------------------
# MAIN DASHBOARD
# -----------------------------------------------

# Header
st.markdown("""
<div style='background:#08111a;padding:20px 24px;border-radius:12px;margin-bottom:24px;border:1px solid #0e1e2d'>
    <div style='display:flex;align-items:center;gap:12px'>
        <div style='background:linear-gradient(135deg,#00ff88,#4da6ff);width:44px;height:44px;border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:22px'>⚡</div>
        <div>
            <div style='font-size:20px;font-weight:700;color:#fff;font-family:monospace'>NITISH'S AI TRADING BOT</div>
            <div style='font-size:11px;color:#3a5a74;letter-spacing:2px'>AI POWERED • NSE INDIA • PAPER TRADING</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# API Key input
with st.sidebar:
    st.markdown("### ⚙️ Settings")
    api_key = st.text_input(
        "Anthropic API Key",
        type="password",
        placeholder="sk-ant-...",
        help="Get from console.anthropic.com"
    )
    st.markdown("---")
    st.markdown("### 📊 About")
    st.markdown("""
    **Paper Trading Mode**
    - Starting capital: ₹1,00,000
    - Tracks 5 NSE stocks
    - AI powered by Claude
    - Refreshes every 60s
    """)
    
    run_bot = st.button("🤖 Run AI Trading Bot", 
                         use_container_width=True,
                         type="primary")
    
    st.markdown("---")
    st.markdown(f"🕐 Last updated: {datetime.now().strftime('%I:%M %p')}")

# Load data
wallet = load_portfolio()
prices = fetch_prices()

# Calculate totals
total_invested = sum(
    wallet["holdings"][s]["shares"] * prices.get(s, {}).get("price", 0)
    for s in wallet["holdings"] if s in prices
)
total_value = wallet["cash"] + total_invested
total_pnl = total_value - 100000

# -----------------------------------------------
# PORTFOLIO SUMMARY ROW
# -----------------------------------------------
st.markdown("### 💼 Portfolio Summary")
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric("💵 Cash", f"₹{wallet['cash']:,.0f}")
with col2:
    st.metric("📦 Invested", f"₹{total_invested:,.0f}")
with col3:
    st.metric("💰 Total Value", f"₹{total_value:,.0f}")
with col4:
    st.metric(
        "📈 P&L",
        f"₹{total_pnl:+,.0f}",
        delta=f"{(total_pnl/1000):+.1f}K"
    )
with col5:
    st.metric("📋 Trades", len(wallet["trades"]))

st.markdown("---")

# -----------------------------------------------
# LIVE PRICES
# -----------------------------------------------
st.markdown("### 📡 Live NSE Prices")
cols = st.columns(5)

for i, (name, data) in enumerate(prices.items()):
    with cols[i]:
        change = data["change"]
        color = "normal" if change >= 0 else "inverse"
        st.metric(
            label=name,
            value=f"₹{data['price']:,.2f}",
            delta=f"{change:+.2f}%",
            delta_color=color
        )

st.markdown("---")

# -----------------------------------------------
# RUN BOT BUTTON
# -----------------------------------------------
if run_bot:
    if not api_key:
        st.error("⚠️ Please enter your Anthropic API key in the sidebar first!")
    else:
        st.markdown("### 🤖 Running AI Analysis...")
        results = []
        
        progress = st.progress(0)
        for i, (name, data) in enumerate(prices.items()):
            with st.spinner(f"Analyzing {name}..."):
                decision = get_ai_decision(name, data["price"], api_key)
                result = execute_trade(
                    wallet, name, data["symbol"],
                    data["price"], decision
                )
                results.append((name, data["price"], decision, result))
                progress.progress((i + 1) / len(prices))
        
        save_portfolio(wallet)
        st.success("✅ AI analysis complete! Portfolio updated.")
        
        # Show results
        for name, price, decision, result in results:
            if decision == "BUY":
                color = "🟢"
            elif decision == "SELL":
                color = "🔴"
            else:
                color = "🟡"
            st.write(f"{color} **{name}** ₹{price:,.2f} → **{decision}** — {result}")
        
        st.rerun()

# -----------------------------------------------
# AI RECOMMENDATIONS (Read only - no trading)
# -----------------------------------------------
st.markdown("### 🤖 Claude AI Recommendations")

if api_key:
    cols = st.columns(5)
    for i, (name, data) in enumerate(prices.items()):
        with cols[i]:
            decision = get_ai_decision(name, data["price"], api_key)
            if decision == "BUY":
                st.success(f"**{name}**\n\n🟢 BUY")
            elif decision == "SELL":
                st.error(f"**{name}**\n\n🔴 SELL")
            else:
                st.info(f"**{name}**\n\n🟡 HOLD")
else:
    st.info("👈 Enter your API key in the sidebar to see AI recommendations")

st.markdown("---")

# -----------------------------------------------
# HOLDINGS
# -----------------------------------------------
st.markdown("### 📦 Current Holdings")

if wallet["holdings"]:
    hold_cols = st.columns(len(wallet["holdings"]))
    for i, (stock, info) in enumerate(wallet["holdings"].items()):
        with hold_cols[i]:
            current = prices.get(stock, {}).get("price", info["avg_price"])
            value = info["shares"] * current
            pnl = (current - info["avg_price"]) * info["shares"]
            st.metric(
                label=stock,
                value=f"₹{value:,.0f}",
                delta=f"P&L: ₹{pnl:+,.0f}"
            )
            st.caption(f"{info['shares']} shares @ ₹{info['avg_price']:,.2f}")
else:
    st.info("💵 No holdings yet — click 'Run AI Trading Bot' to start!")

st.markdown("---")

# -----------------------------------------------
# TRADE HISTORY
# -----------------------------------------------
st.markdown("### 📋 Trade History")

if wallet["trades"]:
    for trade in reversed(wallet["trades"]):
        col1, col2, col3, col4, col5 = st.columns([1, 2, 2, 2, 3])
        with col1:
            if trade["action"] == "BUY":
                st.markdown("🟢 **BUY**")
            else:
                st.markdown("🔴 **SELL**")
        with col2:
            st.write(trade["stock"])
        with col3:
            st.write(f"{trade['shares']} shares")
        with col4:
            st.write(f"₹{trade['price']:,.2f}")
        with col5:
            pnl = trade.get("pnl", None)
            if pnl is not None:
                color = "🟢" if pnl >= 0 else "🔴"
                st.write(f"P&L: {color} ₹{pnl:+,.2f}")
            st.caption(trade["date"])
else:
    st.info("No trades yet!")

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align:center;color:#1e3048;font-size:11px'>"
    "NITISH'S AI TRADING BOT • PAPER TRADING MODE • NOT FINANCIAL ADVICE<br>"
    "Built with Claude AI + yFinance + Streamlit 🇮🇳"
    "</div>",
    unsafe_allow_html=True
)
