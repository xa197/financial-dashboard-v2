import yfinance as yf
import pandas as pd
import os
import time

# --- CONFIGURATION ---
# Le nom de notre fichier de configuration
TICKER_FILE = "tickers.txt" 
DATA_DIR = "data"
START_DATE = "2018-01-01"
END_DATE = pd.to_datetime('today').strftime('%Y-%-m-%d')

# --- FONCTIONS ---
def get_tickers_from_file(filepath):
    """
    Lit un fichier texte et retourne une liste de tickers propres.
    Ignore les lignes vides et les commentaires (#).
    """
    try:
        with open(filepath, 'r') as f:
            # List comprehension pour lire et nettoyer les tickers
            tickers = [
                line.strip().upper() for line in f
                if line.strip() and not line.strip().startswith('#')
            ]
        return tickers
    except FileNotFoundError:
        print(f"ERREUR: Le fichier '{filepath}' est introuvable. Veuillez le créer.")
        return []

# --- LOGIQUE DE COLLECTE ---
def collect_all_data():
    """
    Télécharge les données pour chaque ticker trouvé dans le fichier de configuration.
    """
    tickers_to_download = get_tickers_from_file(TICKER_FILE)

    if not tickers_to_download:
        print("Aucun ticker à télécharger. Vérifiez votre fichier tickers.txt.")
        return

    print(f"{len(tickers_to_download)} tickers à télécharger depuis '{TICKER_FILE}'.")

    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
        print(f"Dossier '{DATA_DIR}' créé.")

    success_count, error_count = 0, 0

    for i, ticker in enumerate(tickers_to_download):
        print(f"[{i+1}/{len(tickers_to_download)}] Téléchargement pour {ticker}...")
        file_path = os.path.join(DATA_DIR, f"{ticker}.csv")
        try:
            data = yf.download(ticker, start=START_DATE, end=END_DATE, progress=False)
            if not data.empty:
                data.index.name = 'Date'
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