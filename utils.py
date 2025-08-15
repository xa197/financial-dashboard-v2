import streamlit as st
import pandas as pd
import os
import yfinance as yf
import json
from datetime import datetime
import pandas_ta as ta

# --- Constantes ---
DATA_DIR = "data"
TICKER_FILE = "tickers.txt"
VIRTUAL_PORTFOLIO_FILE = "virtual_portfolio.json"
AI_PORTFOLIO_FILE = "ai_portfolio.json"

# --- Fonctions de base ---
def get_tickers_by_category():
    categories = {}; current_category = "SANS CATÉGORIE"
    try:
        with open(TICKER_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'): continue
                if line.startswith('[') and line.endswith(']'):
                    current_category = line[1:-1].strip().upper(); categories[current_category] = []
                else:
                    if current_category not in categories: categories[current_category] = []
                    categories[current_category].append(line.upper())
        return categories
    except FileNotFoundError: st.error(f"Fichier '{TICKER_FILE}' introuvable."); return {"ERREUR": []}

def get_available_tickers():
    categories = get_tickers_by_category()
    all_tickers = [ticker for ticker_list in categories.values() for ticker in ticker_list]
    return sorted(list(set(all_tickers)))

def load_data(ticker):
    csv_path = os.path.join(DATA_DIR, f"{ticker.upper()}.csv")
    if not os.path.exists(csv_path): st.error(f"Fichier de données introuvable pour {ticker}."); return pd.DataFrame()
    try:
        df = pd.read_csv(csv_path, index_col='Date', parse_dates=True)
        return df if not df.empty else pd.DataFrame()
    except Exception as e: st.error(f"Erreur de lecture du fichier {csv_path}: {e}"); return pd.DataFrame()

@st.cache_data(ttl=3600)
def get_eur_usd_rate():
    try:
        eur_usd = yf.Ticker("EURUSD=X"); history = eur_usd.history(period="5d")
        return history['Close'].iloc[-1] if not history.empty else 1.0
    except Exception: return 1.0

# --- Fonctions du Portefeuille Virtuel ---
def load_virtual_portfolio():
    try:
        with open(VIRTUAL_PORTFOLIO_FILE, 'r') as f:
            data = json.load(f)
            for pos in data.get('positions_ouvertes', []): pos['Date Achat'] = datetime.fromisoformat(pos['Date Achat'])
            for transac in data.get('historique_transactions', []):
                transac['Date Transaction'] = datetime.fromisoformat(transac['Date Transaction'])
                if 'Date Achat' in transac: transac['Date Achat'] = datetime.fromisoformat(transac['Date Achat'])
            return data
    except (FileNotFoundError, json.JSONDecodeError):
        return {"capital_disponible_eur": 10000.0, "positions_ouvertes": [], "historique_transactions": []}

def save_virtual_portfolio(portfolio_data):
    data_to_save = {"capital_disponible_eur": portfolio_data["capital_disponible_eur"],
                    "positions_ouvertes": [{**p, 'Date Achat': p['Date Achat'].isoformat()} for p in portfolio_data.get('positions_ouvertes', [])],
                    "historique_transactions": [{**t, 'Date Transaction': t['Date Transaction'].isoformat(), 'Date Achat': t.get('Date Achat', datetime.now()).isoformat()} for t in portfolio_data.get('historique_transactions', [])]}
    with open(VIRTUAL_PORTFOLIO_FILE, 'w') as f: json.dump(data_to_save, f, indent=4)

def add_virtual_transaction(ticker, amount_eur):
    portfolio = load_virtual_portfolio()
    if amount_eur > portfolio['capital_disponible_eur']: return False, "Fonds insuffisants !"
    rate = get_eur_usd_rate(); data = load_data(ticker)
    if data.empty: return False, f"Données pour {ticker} indisponibles."
    buy_price_usd = data['Close'].iloc[-1]; quantity = (amount_eur * rate) / buy_price_usd
    portfolio['capital_disponible_eur'] -= amount_eur
    new_position = {"Date Achat": datetime.now(), "Ticker": ticker, "Montant Investi EUR": amount_eur, "Prix Achat USD": buy_price_usd, "Prix Pic USD": buy_price_usd, "Quantite": quantity, "Taux EURUSD Achat": rate}
    portfolio['positions_ouvertes'].append(new_position)
    log_entry = {**new_position, "Type": "ACHAT", "Date Transaction": datetime.now()}
    portfolio['historique_transactions'].append(log_entry)
    save_virtual_portfolio(portfolio)
    return True, f"Achat de {ticker} pour {amount_eur:.2f}€ réussi !"

# --- Fonctions du Portefeuille IA ---
@st.cache_data(ttl=3600)
def get_ai_advisor_signal(data):
    if len(data) < 200: return 0, "Données Insuffisantes"
    score = 0; data.ta.sma(length=50, append=True); data.ta.sma(length=200, append=True)
    if data['SMA_50'].iloc[-1] > data['SMA_200'].iloc[-1]: score += 2
    else: score -= 2
    data.ta.rsi(length=14, append=True); rsi = data['RSI_14'].iloc[-1]
    if rsi > 70: score -= 1
    elif rsi < 30: score += 1
    macd = data.ta.macd(fast=12, slow=26, signal=9, append=True)
    if macd['MACD_12_26_9'].iloc[-1] > macd['MACDs_12_26_9'].iloc[-1]: score += 1
    else: score -= 1
    bollinger = data.ta.bbands(length=20, std=2, append=True)
    if data['Close'].iloc[-1] > bollinger['BBU_20_2.0'].iloc[-1]: score -= 1
    elif data['Close'].iloc[-1] < bollinger['BBL_20_2.0'].iloc[-1]: score += 1
    if score >= 3: recommandation = "🟢 Renforcer"
    elif score <= -3: recommandation = "🔴 Vendre"
    else: recommandation = "⚪ Conserver"
    return score, recommandation

def get_adaptive_atr_multiplier(natr_percentage):
    if natr_percentage < 2.0: return 2.0
    elif natr_percentage < 4.0: return 2.5
    else: return 3.5

def get_best_buy_candidates(num_candidates=5):
    tickers_by_cat = get_tickers_by_category()
    candidates = tickers_by_cat.get("TECHNOLOGIE", get_available_tickers())
    return candidates[:num_candidates]

def run_ai_portfolio_turn():
    try:
        with open(AI_PORTFOLIO_FILE, 'r') as f: portfolio = json.load(f)
        for pos in portfolio['positions_ouvertes']: pos['date_achat'] = datetime.fromisoformat(pos['date_achat'])
    except (FileNotFoundError, json.JSONDecodeError):
        portfolio = {"capital_disponible_eur": 10000.0, "positions_ouvertes": [], "historique_transactions": []}

    actions_log = []; rate_eur_usd_actuel = get_eur_usd_rate()
    positions_a_garder = []
    for pos in portfolio['positions_ouvertes']:
        data = load_data(pos['Ticker'])
        if data.empty: positions_a_garder.append(pos); continue
        latest_price_usd = data['Close'].iloc[-1]
        data.ta.atr(length=14, append=True); latest_atr_usd = data['ATRr_14'].iloc[-1]
        atr_multiplier = get_adaptive_atr_multiplier((latest_atr_usd / latest_price_usd) * 100)
        peak_price_usd = max(pos.get('prix_pic_usd', pos['prix_achat_usd']), latest_price_usd)
        pos['prix_pic_usd'] = peak_price_usd
        stop_loss_price = peak_price_usd - (atr_multiplier * latest_atr_usd)
        take_profit_price = pos.get('take_profit_usd', pos['prix_achat_usd'] * 1.20) # Simple take profit à +20%
        raison_vente = None
        if latest_price_usd < stop_loss_price: raison_vente = "Stop-Loss atteint"
        elif latest_price_usd > take_profit_price: raison_vente = "Take-Profit atteint"
        if raison_vente:
            valeur_vente_eur = (pos['quantite'] * latest_price_usd) / rate_eur_usd_actuel
            portfolio['capital_disponible_eur'] += valeur_vente_eur
            log_entry = {**pos, "type": "VENTE", "date_transaction": datetime.now(), "raison": raison_vente, "montant_vente_eur": valeur_vente_eur}
            portfolio['historique_transactions'].append(log_entry)
            actions_log.append(f"🔴 VENTE de {pos['Ticker']} ({raison_vente}). Gain/Perte: {valeur_vente_eur - pos['montant_investi_eur']:.2f}€")
        else: positions_a_garder.append(pos)
    portfolio['positions_ouvertes'] = positions_a_garder

    if len(portfolio['positions_ouvertes']) < 5:
        capital_a_investir_par_position = portfolio['capital_disponible_eur'] * 0.25
        if capital_a_investir_par_position > 100:
            for ticker in get_best_buy_candidates():
                if any(p['Ticker'] == ticker for p in portfolio['positions_ouvertes']): continue
                data = load_data(ticker)
                if data.empty: continue
                score, recommandation = get_ai_advisor_signal(data)
                if recommandation == "🟢 Renforcer":
                    buy_price_usd = data['Close'].iloc[-1]
                    quantity = (capital_a_investir_par_position * rate_eur_usd_actuel) / buy_price_usd
                    portfolio['capital_disponible_eur'] -= capital_a_investir_par_position
                    new_position = {"date_achat": datetime.now(), "Ticker": ticker, "montant_investi_eur": capital_a_investir_par_position, "prix_achat_usd": buy_price_usd, "prix_pic_usd": buy_price_usd, "quantite": quantity}
                    portfolio['positions_ouvertes'].append(new_position)
                    log_entry = {**new_position, "type": "ACHAT", "date_transaction": datetime.now()}
                    portfolio['historique_transactions'].append(log_entry)
                    actions_log.append(f"🟢 ACHAT de {ticker} pour {capital_a_investir_par_position:.2f}€.")
                    break
    
    # --- LA CORRECTION EST ICI ---
    # On vérifie que la date est bien un objet datetime avant de la convertir
    portfolio_to_save = portfolio.copy()
    for pos in portfolio_to_save['positions_ouvertes']:
        if isinstance(pos.get('date_achat'), datetime):
            pos['date_achat'] = pos['date_achat'].isoformat()
    for transac in portfolio_to_save['historique_transactions']:
        if isinstance(transac.get('date_transaction'), datetime):
            transac['date_transaction'] = transac['date_transaction'].isoformat()
        if 'date_achat' in transac and isinstance(transac.get('date_achat'), datetime):
            transac['date_achat'] = transac['date_achat'].isoformat()
    # --- FIN DE LA CORRECTION ---
    
    with open(AI_PORTFOLIO_FILE, 'w') as f:
        json.dump(portfolio_to_save, f, indent=4)
        
    return actions_log