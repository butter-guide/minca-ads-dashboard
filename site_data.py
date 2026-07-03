"""Construit le JSON du dashboard, le chiffre (AES-GCM) et l'écrit dans site/data.enc.

On envoie les données BRUTES (stats ads par jour + commandes datées détaillées) ;
le navigateur ré-agrège selon la période choisie par l'utilisatrice.
Chiffrement compatible WebCrypto : PBKDF2-SHA256 puis AES-256-GCM.
"""
import os
import json
import base64
from datetime import datetime, timezone, timedelta

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

import config

PBKDF2_ITER = 200_000
SITE_DIR = os.path.join(os.path.dirname(__file__), "site")


def _now_paris():
    return (datetime.now(timezone.utc) + timedelta(hours=2)).strftime("%d/%m/%Y %H:%M")


def _b64(b: bytes) -> str:
    return base64.b64encode(b).decode()


def build(daily_rows, orders):
    """Chiffre le payload et écrit site/data.enc."""
    today = (datetime.now(timezone.utc) + timedelta(hours=2)).date().isoformat()
    data = {
        "updated": _now_paris(),
        "today": today,
        "currency": config.CURRENCY,
        "fetch_days": config.SITE_FETCH_DAYS,
        "ads_daily": [{
            "ad_id": r["ad_id"], "ad": r["ad_name"], "campaign": r["campaign_name"],
            "adset": r["adset_name"], "date": r["date"],
            "spend": r["spend"], "impressions": r["impressions"],
            "clicks": r["clicks"], "link_clicks": r["link_clicks"],
            "visits": r["visits"], "mp": r["meta_purchases"], "mv": r["meta_value"],
        } for r in daily_rows],
        "orders": orders,  # déjà au bon format (voir shopify_client.fetch_orders_all)
    }
    plaintext = json.dumps(data, ensure_ascii=False).encode("utf-8")

    salt = os.urandom(16)
    iv = os.urandom(12)
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=PBKDF2_ITER)
    key = kdf.derive(config.SITE_PASSWORD.encode("utf-8"))
    ct = AESGCM(key).encrypt(iv, plaintext, None)

    enc = {"salt": _b64(salt), "iv": _b64(iv), "iter": PBKDF2_ITER,
           "ct": _b64(ct), "updated": data["updated"]}
    os.makedirs(SITE_DIR, exist_ok=True)
    with open(os.path.join(SITE_DIR, "data.enc"), "w", encoding="utf-8") as f:
        json.dump(enc, f)
    return len(data["ads_daily"]), len(orders)
