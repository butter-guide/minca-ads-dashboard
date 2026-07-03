"""Centralise toute la configuration lue depuis les variables d'environnement.

En local : les variables sont chargées depuis un fichier .env (voir .env.example).
Sur GitHub Actions : elles viennent des "Secrets" du dépôt.
"""
import os
from pathlib import Path

# Charge .env en local si présent (sans planter si python-dotenv n'est pas là)
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass


def _require(name: str) -> str:
    val = os.environ.get(name)
    if not val:
        raise SystemExit(
            f"❌ Variable manquante : {name}. "
            f"Ajoute-la dans ton fichier .env (local) ou dans les Secrets GitHub."
        )
    return val


# --- Meta / Facebook Ads ---
META_ACCESS_TOKEN = _require("META_ACCESS_TOKEN")
# Doit être au format act_1234567890
META_AD_ACCOUNT_ID = _require("META_AD_ACCOUNT_ID")
META_API_VERSION = os.environ.get("META_API_VERSION", "v21.0")
# Fenêtre affichée par défaut dans le Google Sheet
META_DATE_PRESET = os.environ.get("META_DATE_PRESET", "last_30d")
# Fenêtre RÉCUPÉRÉE pour le site (détail par jour) — la période est ensuite choisie dans le navigateur
SITE_FETCH_PRESET = os.environ.get("SITE_FETCH_PRESET", "last_90d")
SITE_FETCH_DAYS = int(os.environ.get("SITE_FETCH_DAYS", "90"))

# --- Shopify (app Dev Dashboard, client credentials grant) ---
SHOPIFY_STORE = _require("SHOPIFY_STORE")          # ex: mincaparis.myshopify.com
SHOPIFY_CLIENT_ID = _require("SHOPIFY_CLIENT_ID")
SHOPIFY_CLIENT_SECRET = _require("SHOPIFY_CLIENT_SECRET")
SHOPIFY_API_VERSION = os.environ.get("SHOPIFY_API_VERSION", "2025-01")

# --- Google Sheets (via Apps Script Web App, pas de compte de service) ---
# URL de déploiement du script (…/exec) + un secret partagé pour sécuriser l'écriture
SHEETS_WEBAPP_URL = _require("SHEETS_WEBAPP_URL")
SHEETS_SECRET = os.environ.get("SHEETS_SECRET", "")

# --- Site web chiffré (GitHub Pages) ---
# Mot de passe qui chiffre les données du dashboard (déchiffré côté navigateur)
SITE_PASSWORD = _require("SITE_PASSWORD")

# Devise (pour l'affichage) — Meta et Shopify sont supposés dans la même devise
CURRENCY = os.environ.get("CURRENCY", "EUR")
