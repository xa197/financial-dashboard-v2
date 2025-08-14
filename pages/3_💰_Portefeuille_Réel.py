import streamlit as st
import pandas as pd
from utils import load_data, get_available_tickers, get_eur_usd_rate
from datetime import date
import os

st.set_page_config(layout="wide", page_title="Portefeuille Réel")
st.title("💰 Portefeuille Réel")

TRANSACTIONS_FILE = "transactions_reelles.csv"

def load_transactions():
    if os.path.exists(TRANSACTIONS_FILE) and os.path.getsize(TRANSACTIONS_FILE) > 0:
        return pd.read_csv(TRANSACTIONS_FILE)
    return pd.DataFrame()

def save_transactions(df):
    df.to_csv(TRANSACTIONS_FILE, index=False)

df_real = load_transactions()

st.sidebar.header("Ajouter une Transaction Réelle")
available_tickers = get_available_tickers()

with st.sidebar.form("real_transaction_form", clear_on_submit=True):
    transaction_date = st.date_input("Date d'achat", value=date.today())
    ticker = st.selectbox("Actif", options=available_tickers)
    
    currency = st.selectbox("Devise", ["USD", "EUR"])
    amount = st.number_input(f"Montant investi ({currency})", min_value=1.0, step=10.0)
    
    submitted = st.form_submit_button("Ajouter")

    if submitted:
        amount_in_usd = amount
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
                new_transaction = pd.DataFrame([{
                    "Date": transaction_date.strftime('%Y-%m-%d'), "Ticker": ticker,
                    "Montant_Investi": amount, "Devise": currency, "Montant_USD": amount_in_usd,
                    "Prix_Achat_USD": buy_price, "Quantite": quantity
                }])
                df_real = pd.concat([df_real, new_transaction], ignore_index=True)
                save_transactions(df_real)
                st.sidebar.success("Transaction ajoutée !")
            else:
                st.sidebar.error("Pas de données de prix à cette date.")

if not df_real.empty:
    portfolio_summary = df_real.groupby('Ticker').agg(
        Montant_Total_USD=('Montant_USD', 'sum'),
        Quantite_Totale=('Quantite', 'sum')
    ).reset_index()
    
    current_values = []
    for index, row in portfolio_summary.iterrows():
        data = load_data(row['Ticker'])
        latest_price = data['Close'].iloc[-1] if data is not None else 0
        current_values.append(row['Quantite_Totale'] * latest_price)

    portfolio_summary['Valeur_Actuelle_USD'] = current_values
    
    total_investment_usd = portfolio_summary['Montant_Total_USD'].sum()
    total_current_value_usd = portfolio_summary['Valeur_Actuelle_USD'].sum()
    pnl_usd = total_current_value_usd - total_investment_usd
    pnl_pct = (pnl_usd / total_investment_usd) * 100 if total_investment_usd > 0 else 0

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Investi (en USD)", f"${total_investment_usd:,.2f}")
    col2.metric("Valeur Actuelle (en USD)", f"${total_current_value_usd:,.2f}")
    col3.metric("Plus/Moins-Value (USD)", f"${pnl_usd:,.2f}", delta=f"{pnl_pct:.2f}%")
    
    st.subheader("Positions Consolidées")
    st.dataframe(portfolio_summary)

    st.subheader("Historique Complet des Transactions")
    st.dataframe(df_real)
else:
    st.info("Portefeuille réel vide.")