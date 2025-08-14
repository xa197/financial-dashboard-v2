import yfinance as yf
import pandas as pd
import os
import time

TICKER_FILE = "tickers.txt" 
DATA_DIR = "data"
START_DATE = "2018-01-01"
END_DATE = pd.to_datetime('today').strftime('%Y-%m-%d')

def get_tickers_from_file(filepath):
    """Lit le fichier tickers.txt et retourne une liste de tous les tickers."""
    try:
        with open(filepath, 'r') as f:
            tickers = [
                line.strip().upper() for line in f
                if line.strip() and not line.strip().startswith(('#', '['))
            ]
        return tickers
    except FileNotFoundError:
        return []

# ... (Le reste du code de data_collector.py reste EXACTEMENT le même) ...
# (Je ne le remets pas en entier pour ne pas alourdir, il n'y a que la fonction ci-dessus qui change)
def collect_all_data():
    tickers_to_download = get_tickers_from_file(TICKER_FILE)
    if not tickers_to_download: print("Aucun ticker à télécharger."); return
    print(f"{len(tickers_to_download)} tickers à télécharger.")
    if not os.path.exists(DATA_DIR): os.makedirs(DATA_DIR)
    success_count, error_count = 0, 0
    for i, ticker in enumerate(tickers_to_download):
        print(f"[{i+1}/{len(tickers_to_download)}] Téléchargement pour {ticker}...")
        file_path = os.path.join(DATA_DIR, f"{ticker}.csv")
        try:
            data = yf.download(ticker, start=START_DATE, end=END_DATE, progress=False)
            if not data.empty:
                data.index.name = 'Date'
                data.to_csv(file_path)
                success_count += 1
            else: error_count += 1
            time.sleep(0.5)
        except Exception as e:
            print(f"  -> ERREUR: {e}"); error_count += 1
    print(f"\n--- Collecte terminée ---\nSuccès: {success_count} | Échecs: {error_count}")

if __name__ == "__main__":
    collect_all_data()