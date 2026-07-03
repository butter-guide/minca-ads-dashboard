"""Construit le JSON du dashboard, le chiffre (AES-GCM) et l'écrit dans site/data.enc.

Le chiffrement est compatible avec l'API WebCrypto du navigateur (PBKDF2-SHA256
puis AES-256-GCM), pour que index.html puisse déchiffrer avec le mot de passe.
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


def _payload(meta_rows, by_ad, totals, orders_detail):
    """Assemble l'objet de données lisible (avant chiffrement)."""
    # Lookup ad_id -> (ad_name, campaign_name) pour enrichir commandes et par-ad
    lookup = {r["ad_id"]: (r["ad_name"], r["campaign_name"]) for r in meta_rows}

    ads = []
    tot = {"spend": 0.0, "impr": 0, "clicks": 0, "visits": 0,
           "meta_p": 0, "meta_v": 0.0, "shop_o": 0, "shop_r": 0.0}
    for r in sorted(meta_rows, key=lambda x: x["spend"], reverse=True):
        s = by_ad.get(r["ad_id"], {"orders": 0, "revenue": 0.0})
        ads.append({
            "campaign": r["campaign_name"], "adset": r["adset_name"],
            "ad": r["ad_name"], "ad_id": r["ad_id"],
            "spend": r["spend"], "impressions": r["impressions"],
            "clicks": r["clicks"], "link_clicks": r["link_clicks"],
            "visits": r["visits"], "meta_purchases": r["meta_purchases"],
            "meta_value": r["meta_purchase_value"],
            "shop_orders": s["orders"], "shop_revenue": s["revenue"],
            "meta_roas": r["meta_roas"],
            "real_roas": round(s["revenue"] / r["spend"], 2) if r["spend"] else 0.0,
            "cpc": r["cpc"], "ctr": r["ctr"], "cpm": r["cpm"],
            "cost_per_visit": r["cost_per_visit"], "cost_per_purchase": r["cost_per_purchase"],
        })
        tot["spend"] += r["spend"]; tot["impr"] += r["impressions"]
        tot["clicks"] += r["clicks"]; tot["visits"] += r["visits"]
        tot["meta_p"] += r["meta_purchases"]; tot["meta_v"] += r["meta_purchase_value"]
        tot["shop_o"] += s["orders"]; tot["shop_r"] += s["revenue"]

    # Enrichit chaque commande avec le nom d'ad / campagne si connu
    orders = []
    for o in sorted(orders_detail, key=lambda x: x["date"], reverse=True):
        name, camp = lookup.get(o["utm_content"], (None, None))
        if o["is_meta_ad"]:
            source = name or f"Ad {o['utm_content']}"
        else:
            source = o["utm_content"]  # ex: link_in_bio, Facebook_UA
        orders.append({
            "order": o["order"], "date": o["date"],
            "source": source, "campaign": camp or ("Meta (ad archivée)" if o["is_meta_ad"] else "—"),
            "is_meta_ad": o["is_meta_ad"],
            "items": o["items"], "amount": o["amount"],
            "status": o["status"], "products": o["products"],
        })

    spend = round(tot["spend"], 2)
    return {
        "updated": _now_paris(),
        "window": config.META_DATE_PRESET,
        "currency": config.CURRENCY,
        "summary": {
            "spend": spend, "impressions": tot["impr"], "clicks": tot["clicks"],
            "visits": tot["visits"], "meta_purchases": tot["meta_p"],
            "meta_value": round(tot["meta_v"], 2),
            "shop_orders_ads": tot["shop_o"], "shop_revenue_ads": round(tot["shop_r"], 2),
            "shop_orders_total": totals["orders"], "shop_revenue_total": totals["revenue"],
            "meta_roas": round(tot["meta_v"] / spend, 2) if spend else 0,
            "real_roas": round(tot["shop_r"] / spend, 2) if spend else 0,
        },
        "ads": ads,
        "orders": orders,
    }


def build(meta_rows, by_ad, totals, orders_detail):
    """Chiffre le payload et écrit site/data.enc."""
    data = _payload(meta_rows, by_ad, totals, orders_detail)
    plaintext = json.dumps(data, ensure_ascii=False).encode("utf-8")

    salt = os.urandom(16)
    iv = os.urandom(12)
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=PBKDF2_ITER)
    key = kdf.derive(config.SITE_PASSWORD.encode("utf-8"))
    ct = AESGCM(key).encrypt(iv, plaintext, None)  # tag inclus à la fin (compatible WebCrypto)

    enc = {
        "salt": _b64(salt), "iv": _b64(iv), "iter": PBKDF2_ITER, "ct": _b64(ct),
        "updated": data["updated"],  # visible sans mot de passe (juste l'heure)
    }
    os.makedirs(SITE_DIR, exist_ok=True)
    with open(os.path.join(SITE_DIR, "data.enc"), "w", encoding="utf-8") as f:
        json.dump(enc, f)
    return len(data["ads"]), len(data["orders"])
