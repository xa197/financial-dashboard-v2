# espion.py
import yfinance as yf

print("--- Lancement de l'espion sur yfinance ---")

# On demande les données pour AAPL
print("Téléchargement des données pour AAPL...")
data = yf.download("AAPL", period="1y", interval="1d")

# On affiche ce qu'on a VRAIMENT reçu
print("\n--- Contenu Brut de la variable 'data' ---")
print(data)

print("\n--- Les 5 premières lignes (data.head()) ---")
print(data.head())

print("\n--- Fin de l'espionnage ---")