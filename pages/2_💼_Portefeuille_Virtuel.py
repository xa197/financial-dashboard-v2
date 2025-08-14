import streamlit as st
import pandas as pd
from utils import load_data, get_available_tickers, get_eur_usd_rate
from datetime import date

st.set_page_config(layout="wide", page_title="Portefeuille Virtuel")
st.title("💼 Portefeuille Virtuel (Paper Trading)")

if 'virtual_portfolio' not in st.session_state:
    st.session_state.virtual_portfolio = []

# --- FORMULAIRE D'AJOUT ---
st.sidebar.header("Ajouter une Transaction Virtuelle")
available_tickers = get_available_tickers()

with st.sidebar.form("virtual_transaction_form", clear_on_submit=True):
    transaction_date = st.date_input("Date d'achat", value=date.today())
    ticker = st.selectbox("Actif", options=available_tickers)
    
    # --- AJOUT DU SÉLECTEUR DE DEVISE ---
    currency = st.selectbox("Devise", ["USD", "EUR"])
    amount = st.number_input(f"Montant investi ({currency})", min_value=1.0, step=10.0)
    
    submitted = st.form_submit_button("Ajouter")

    if submitted:
        amount_in_usd = amount
        # On convertit en USD si nécessaire
        if currency == "EUR":
            rate = get_eur_usd_rate()
            amount_in_usd = amount * rate
            st.sidebar.info(f"Taux EUR/USD appliqué : {rate:.4f}")

        data = load_data(ticker)
        if data is not None:
            price_on_date = data.loc[data.index.to_series().dt.date == transaction_date, 'Close']
            if not price_on_date.empty:
                buy_price = price_on_date.iloc[0]
                quantity = amount_in_usd / buy_price
                st.session_state.virtual_portfolio.append({
                    "Date": transaction_date, "Ticker": ticker, "Montant_Investi": amount,
                    "Devise": currency, "Montant_USD": amount_in_usd,
                    "Prix_Achat_USD": buy_price, "Quantite": quantity
                })
            else:
                st.sidebar.error("Pas de données de prix à cette date.")

# --- AFFICHAGE DU PORTEFEUILLE ---
if st.session_state.virtual_portfolio:
    df_virtual = pd.DataFrame(st.session_state.virtual_portfolio)
    current_values = []
    for index, row in df_virtual.iterrows():
        data = load_data(row['Ticker'])
        latest_price = data['Close'].iloc[-1]
        current_values.append(row['Quantite'] * latest_price)

    df_virtual['Valeur_Actuelle_USD'] = current_values
    
    total_investment_usd = df_virtual['Montant_USD'].sum()
    total_current_value_usd = df_virtual['Valeur_Actuelle_USD'].sum()
    pnl_usd = total_current_value_usd - total_investment_usd
    pnl_pct = (pnl_usd / total_investment_usd) * 100 if total_investment_usd > 0 else 0

    col1, col2, col3 = st.columns(3)
    col1.metric("Investissement Total (en USD)", f"${total_investment_usd:,.2f}")
    col2.metric("Valeur Actuelle (en USD)", f"${total_current_value_usd:,.2f}")
    col3.metric("Plus/Moins-Value", f"${pnl_usd:,.2f}", delta=f"{pnl_pct:.2f}%")
    
    st.dataframe(df_virtual)
else:
    st.info("Portefeuille virtuel vide.")