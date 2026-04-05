import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go

# --- Page Config ---
st.set_page_config(page_title="Open Replay", layout="wide")

# --- Styling ---
st.markdown("""
<style>
.main { background-color: #131722; }
.stButton>button {
    width: 100%;
    border-radius: 5px;
    height: 3em;
    background-color: #2a2e39;
    color: white;
    border: 1px solid #434651;
}
.stButton>button:hover {
    border-color: #2962ff;
    color: #2962ff;
}
</style>
""", unsafe_allow_html=True)

st.title("📈 Open Replay")

# --- Helper Functions ---
def clean_dataframe(df):
    df = df.copy()

    if "Date" not in df.columns:
        df.rename(columns={df.columns[0]: "Date"}, inplace=True)

    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["Date"])

    required_cols = ["Open", "High", "Low", "Close"]
    for col in required_cols:
        if col not in df.columns:
            st.error(f"Missing required column: {col}")
            return None

    df = df.sort_values("Date").reset_index(drop=True)
    return df


def detect_timeframe(df):
    if len(df) < 2:
        return "Unknown"
    delta = df["Date"].diff().median()
    minutes = delta.total_seconds() / 60

    if minutes < 1:
        return "Seconds"
    elif minutes < 60:
        return f"{int(minutes)} min"
    elif minutes < 1440:
        return f"{int(minutes/60)} hour"
    else:
        return "Daily"


# --- Sidebar ---
with st.sidebar:
    st.header("Data Settings")

    source = st.radio("Select Data Source:", ["Download from Yahoo", "Upload CSV"])

    if source == "Download from Yahoo":
        ticker = st.text_input("Ticker Symbol", value="AAPL").upper()
        period = st.selectbox("Period", ["1mo", "3mo", "6mo", "1y", "2y", "5y", "max"])
        interval = st.selectbox("Interval", ["1d", "1h", "30m", "15m", "5m", "1m"])

        if st.button("Fetch & Load"):
            try:
                df = yf.download(ticker, period=period, interval=interval)

                if not df.empty:
                    df = df.reset_index()
                    df.columns = [col[0] if isinstance(col, tuple) else col for col in df.columns]

                    df = clean_dataframe(df)

                    if df is not None:
                        st.session_state["full_data"] = df
                        st.session_state["step"] = min(20, len(df))
                        st.rerun()

                else:
                    st.error("No data found.")

            except Exception as e:
                st.error(f"Error: {e}")

    else:
        uploaded_file = st.file_uploader("Upload CSV", type="csv")

        if uploaded_file:
            df = pd.read_csv(uploaded_file)
            df = clean_dataframe(df)

            if df is not None:
                st.session_state["full_data"] = df
                st.session_state["step"] = min(20, len(df))
                st.rerun()

    # --- Export ---
    if "full_data" in st.session_state:
        st.markdown("---")
        st.subheader("Export Data")

        df_to_save = st.session_state["full_data"].copy()
        df_to_save["Date"] = pd.to_datetime(df_to_save["Date"])

        csv_data = df_to_save.to_csv(
            index=False,
            date_format="%Y-%m-%d %H:%M:%S"
        ).encode("utf-8")

        st.download_button(
            "💾 Download CSV",
            data=csv_data,
            file_name="replay_data.csv",
            mime="text/csv"
        )

# --- Replay Engine ---
if "full_data" in st.session_state:

    data = st.session_state["full_data"]
    total_len = len(data)

    if "step" not in st.session_state:
        st.session_state["step"] = min(20, total_len)

    # Clamp step safely
    st.session_state["step"] = max(1, min(st.session_state["step"], total_len))

    # --- Controls ---
    col1, col2, col3, col4, col5 = st.columns([1,1,1,1,1])

    with col1:
        if st.button("⏮️ Start"):
            st.session_state["step"] = 1
            st.rerun()

    with col2:
        if st.button("⬅️ Prev"):
            if st.session_state["step"] > 1:
                st.session_state["step"] -= 1
                st.rerun()

    with col3:
        if st.button("Next ➡️"):
            if st.session_state["step"] < total_len:
                st.session_state["step"] += 1
                st.rerun()

    with col4:
        if st.button("⏭️ End"):
            st.session_state["step"] = total_len
            st.rerun()

    with col5:
        if st.button("🔄 Reset"):
            st.session_state["step"] = min(20, total_len)
            st.rerun()

    # --- Slice Data ---
    visible_df = data.iloc[:st.session_state["step"]].copy()
    current = visible_df.iloc[-1]

    # --- Info Bar ---
    c1, c2, c3, c4, c5 = st.columns(5)

    c1.metric("Date", str(current["Date"]).split()[0])
    c2.metric("Close", f"{current['Close']:.2f}")
    c3.metric("High", f"{current['High']:.2f}")
    c4.metric("Low", f"{current['Low']:.2f}")
    c5.metric("Timeframe", detect_timeframe(data))

    # --- Chart ---
    visible_df["Date_Str"] = visible_df["Date"].dt.strftime("%Y-%m-%d %H:%M")

    fig = go.Figure(data=[go.Candlestick(
        x=visible_df["Date_Str"],
        open=visible_df["Open"],
        high=visible_df["High"],
        low=visible_df["Low"],
        close=visible_df["Close"],
        increasing_line_color="#089981",
        decreasing_line_color="#f23645"
    )])

    fig.update_layout(
        height=700,
        template="plotly_dark",
        xaxis_rangeslider_visible=False,
        margin=dict(l=20, r=20, t=20, b=20),
        paper_bgcolor="#131722",
        plot_bgcolor="#131722",
        xaxis=dict(type="category", gridcolor="#2a2e39"),
        yaxis=dict(gridcolor="#2a2e39", side="right")
    )

    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    st.caption(f"Progress: {st.session_state['step']} / {total_len}")

else:
    st.info("👈 Load data to start replay")