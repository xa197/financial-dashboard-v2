import yfinance as yf
import pandas as pd
import os
import time

# --- CONFIGURATION ---
TICKERS_TO_DOWNLOAD = [
    # Actions US
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META", "JPM", "V", "JNJ", 
    "WMT", "PG", "UNH", "MA", "HD", "DIS", "PYPL", "NFLX", "ADBE", "CRM",
    # Cryptomonnaies
    "BTC-USD", "ETH-USD", "SOL-USD", "XRP-USD", "ADA-USD"
]
DATA_DIR = "data"
START_DATE = "2018-01-01"
END_DATE = pd.to_datetime('today').strftime('%Y-%m-%d')

# --- LOGIQUE ---
def collect_all_data():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
        print(f"Dossier '{DATA_DIR}' créé.")

    success_count, error_count = 0, 0

    for i, ticker in enumerate(TICKERS_TO_DOWNLOAD):
        print(f"[{i+1}/{len(TICKERS_TO_DOWNLOAD)}] Téléchargement pour {ticker}...")
        file_path = os.path.join(DATA_DIR, f"{ticker}.csv")
        try:
            data = yf.download(ticker, start=START_DATE, end=END_DATE, progress=False)
            if not data.empty:
                data.to_csv(file_path)
                print(f"  -> Succès ! Données sauvegardées.")
                success_count += 1
            else:
                print(f"  -> Aucune donnée reçue.")
                error_count += 1
            time.sleep(0.5)
        except Exception as e:
            print(f"  -> ERREUR: {e}")
            error_count += 1

    print(f"\n--- Collecte terminée ---\nSuccès: {success_count} | Échecs: {error_count}")

if __name__ == "__main__":
    collect_all_data()