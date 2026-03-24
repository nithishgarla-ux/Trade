import streamlit as st
import yfinance as yf
import anthropic
import json
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

st.set_page_config(
    page_title="Nitish's Trading Bot",
    page_icon="⚡",
    layout="wide"
)

st.markdown("""
<style>
.stApp { background-color: #070e16; color: #c8dde8; }
div[data-testid="stMetricValue"] { color: white; font-size: 22px; }
</style>
""", unsafe_allow_html=True)

STOCKS = {
    "Reliance": "RELIANCE.NS",
    "TCS": "TCS.NS",
    "Infosys": "INFY.NS",
    "HDFC Bank": "HDFCBANK.NS",
    "Wipro": "WIPRO.NS"
}

def load_portfolio():
    default = {
        "cash": 100000,
        "holdings": {},
        "trades": [],
        "created": datetime.now().strftime('%d %b %Y')
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

def send_email(gmail, app_password, subject, body):
    try:
        msg = MIMEMultipart()
        msg["From"] = gmail
        msg["To"] = gmail
        msg["Subject"] = f"⚡ Trading Bot: {subject}"
        msg.attach(MIMEText(body, "plain"))
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(gmail, app_password)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        st.warning(f"Email failed: {e}")
        return False

@st.cache_data(ttl=60)
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
            }
        except:
            prices[name] = {"symbol": symbol, "price": 0, "change": 0}
    return prices

def get_ai_decision(name, price, api_key):
    try:
        client = anthropic.Anthropic(api_key=api_key)
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=50,
            messages=[{
                "role": "user",
                "content": f"Indian NSE stock: {name}, Price: ₹{price}. Reply ONLY: BUY or SELL or HOLD"
            }]
        )
        decision = msg.content[0].text.strip().upper()
        if "BUY" in decision:
            return "BUY"
        elif "SELL" in decision:
            return "SELL"
        return "HOLD"
    except:
        return "HOLD"

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
            return f"Bought {shares} shares @ ₹{price:,.2f}"
        return "Not enough cash"
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
            return f"Sold {shares} shares @ ₹{price:,.2f} | P&L: ₹{pnl:+,.2f}"
        return "No shares to sell"
    return "Holding"

# SIDEBAR
api_key = st.secrets.get("ANTHROPIC_API_KEY", "")
gmail = st.secrets.get("GMAIL", "")
app_password = st.secrets.get("APP_PASSWORD", "")
email_enabled = bool(gmail and app_password)

with st.sidebar:
    st.markdown("### ⚙️ Settings")
    if api_key:
        st.success("✅ AI Connected")
    else:
        api_key = st.text_input("🤖 Anthropic API Key", type="password", placeholder="sk-ant-...")
    if email_enabled:
        st.success("✅ Email Connected")
    else:
        st.warning("⚠️ Add secrets in Streamlit settings")
        gmail = st.text_input("Gmail", placeholder="yourname@gmail.com")
        app_password = st.text_input("App Password", type="password")
        email_enabled = bool(gmail and app_password)
    st.markdown("---")
    run_bot = st.button("🤖 Run AI Trading Bot", key="run_bot_btn", use_container_width=True, type="primary")
    test_email = st.button("📧 Send Test Email", key="test_email_btn", use_container_width=True)
    st.markdown("---")
    st.markdown("### 📊 Info")
    st.markdown("- Starting capital: ₹1,00,000\n- Tracks 5 NSE stocks\n- AI powered by Claude\n- Refreshes every 60s")
    st.caption(f"🕐 {datetime.now().strftime('%d %b %Y, %I:%M %p')}")

# LOAD DATA
wallet = load_portfolio()
prices = fetch_prices()

total_invested = sum(
    wallet["holdings"][s]["shares"] * prices.get(s, {}).get("price", 0)
    for s in wallet["holdings"] if s in prices
)
total_value = wallet["cash"] + total_invested
total_pnl = total_value - 100000

# HEADER
st.markdown("""
<div style='background:#08111a;padding:20px;border-radius:12px;margin-bottom:24px;border:1px solid #0e1e2d'>
<div style='display:flex;align-items:center;gap:12px'>
<div style='background:linear-gradient(135deg,#00ff88,#4da6ff);width:44px;height:44px;border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:22px'>⚡</div>
<div>
<div style='font-size:20px;font-weight:700;color:#fff;font-family:monospace'>NITISH'S AI TRADING BOT</div>
<div style='font-size:11px;color:#3a5a74;letter-spacing:2px'>AI POWERED • NSE INDIA • PAPER TRADING</div>
</div></div></div>
""", unsafe_allow_html=True)

# TEST EMAIL
if test_email:
    if not email_enabled:
        st.error("⚠️ Add Gmail details first!")
    else:
        with st.spinner("Sending test email..."):
            sent = send_email(gmail, app_password, "Bot is alive! 🎉", f"""
Your AI Trading Bot is live!
📅 {datetime.now().strftime('%d %b %Y, %I:%M %p')}
💵 Cash: ₹{wallet['cash']:,.2f}
💰 Total Value: ₹{total_value:,.2f}
📈 P&L: ₹{total_pnl:+,.2f}
📋 Trades: {len(wallet['trades'])}
🌐 Dashboard: tw3zdrzpbk6rqdemq3hqno.streamlit.app
            """)
        if sent:
            st.success("✅ Test email sent!")
        else:
            st.error("❌ Email failed")

# PORTFOLIO SUMMARY
st.markdown("### 💼 Portfolio Summary")
c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    st.metric("💵 Cash", f"₹{wallet['cash']:,.0f}")
with c2:
    st.metric("📦 Invested", f"₹{total_invested:,.0f}")
with c3:
    st.metric("💰 Total Value", f"₹{total_value:,.0f}")
with c4:
    st.metric("📈 P&L", f"₹{total_pnl:+,.0f}")
with c5:
    st.metric("📋 Trades", len(wallet["trades"]))

st.markdown("---")

# LIVE PRICES
st.markdown("### 📡 Live NSE Prices")
cols = st.columns(5)
for i, (name, data) in enumerate(prices.items()):
    with cols[i]:
        st.metric(
            label=name,
            value=f"₹{data['price']:,.2f}",
            delta=f"{data['change']:+.2f}%",
            delta_color="normal" if data['change'] >= 0 else "inverse"
        )

st.markdown("---")

# RUN BOT
if run_bot:
    if not api_key:
        st.error("⚠️ No API key found!")
    else:
        st.markdown("### 🤖 AI Bot Running...")
        results = []
        actions_taken = []
        progress = st.progress(0)
        for i, (name, data) in enumerate(prices.items()):
            with st.spinner(f"Analyzing {name}..."):
                decision = get_ai_decision(name, data["price"], api_key)
                result = execute_trade(wallet, name, data["symbol"], data["price"], decision)
                results.append((name, data["price"], decision, result))
                if decision != "HOLD":
                    actions_taken.append(f"{decision} {name} @ ₹{data['price']:,.2f}")
                progress.progress((i + 1) / len(prices))
        save_portfolio(wallet)
        st.markdown("#### Results:")
        for name, price, decision, result in results:
            icon = "🟢" if decision == "BUY" else "🔴" if decision == "SELL" else "🟡"
            st.write(f"{icon} **{name}** ₹{price:,.2f} → **{decision}** — {result}")
        if email_enabled:
            holdings_text = ""
            for stock, info in wallet["holdings"].items():
                if stock in prices:
                    val = info["shares"] * prices[stock]["price"]
                    pnl = (prices[stock]["price"] - info["avg_price"]) * info["shares"]
                    holdings_text += f"\n  • {stock}: {info['shares']} shares = ₹{val:,.2f} (P&L: ₹{pnl:+,.2f})"
            new_total = wallet["cash"] + sum(
                wallet["holdings"][s]["shares"] * prices.get(s, {}).get("price", 0)
                for s in wallet["holdings"] if s in prices
            )
            subject = f"Trades: {', '.join(actions_taken[:2])}" if actions_taken else "Daily Report — HOLD"
            body = f"""
🤖 AI TRADING BOT REPORT
{'='*40}
📅 {datetime.now().strftime('%A, %d %B %Y, %I:%M %p')}
💵 Cash: ₹{wallet['cash']:,.2f}
💰 Total Value: ₹{new_total:,.2f}
📈 P&L: ₹{(new_total - 100000):+,.2f}
📦 Holdings:{holdings_text if holdings_text else chr(10)+'  No holdings'}
{'⚡ Trades: ' + chr(10).join(actions_taken) if actions_taken else '⏸️ No trades today — HOLD'}
📋 Total trades: {len(wallet['trades'])}
{'='*40}
🌐 tw3zdrzpbk6rqdemq3hqno.streamlit.app
            """
            with st.spinner("Sending email..."):
                sent = send_email(gmail, app_password, subject, body)
            if sent:
                st.success("📧 Email report sent!")
        st.success("✅ Bot run complete!")
        st.rerun()

# AI RECOMMENDATIONS
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
    st.info("👈 Enter API key in sidebar to see AI recommendations")

st.markdown("---")

# HOLDINGS
st.markdown("### 📦 Current Holdings")
if wallet["holdings"]:
    cols = st.columns(len(wallet["holdings"]))
    for i, (stock, info) in enumerate(wallet["holdings"].items()):
        with cols[i]:
            current = prices.get(stock, {}).get("price", info["avg_price"])
            value = info["shares"] * current
            pnl = (current - info["avg_price"]) * info["shares"]
            st.metric(label=stock, value=f"₹{value:,.0f}", delta=f"P&L ₹{pnl:+,.0f}")
            st.caption(f"{info['shares']} shares @ ₹{info['avg_price']:,.2f}")
else:
    st.info("💵 No holdings yet — run the bot to start trading!")

st.markdown("---")

# TRADE HISTORY
st.markdown("### 📋 Trade History")
if wallet["trades"]:
    for trade in reversed(wallet["trades"]):
        c1, c2, c3, c4, c5 = st.columns([1, 2, 2, 2, 3])
        with c1:
            st.markdown("🟢 **BUY**" if trade["action"] == "BUY" else "🔴 **SELL**")
        with c2:
            st.write(trade["stock"])
        with c3:
            st.write(f"{trade['shares']} shares")
        with c4:
            st.write(f"₹{trade['price']:,.2f}")
        with c5:
            pnl = trade.get("pnl", None)
            if pnl is not None:
                icon = "🟢" if pnl >= 0 else "🔴"
                st.write(f"P&L: {icon} ₹{pnl:+,.2f}")
            st.caption(trade["date"])
else:
    st.info("No trades yet!")

st.markdown("---")
st.markdown(
    "<div style='text-align:center;color:#1e3048;font-size:11px'>"
    "NITISH'S AI TRADING BOT • PAPER TRADING • NOT FINANCIAL ADVICE"
    "<br>Built with Claude AI + yFinance + Streamlit 🇮🇳⚡"
    "</div>",
    unsafe_allow_html=True
)
