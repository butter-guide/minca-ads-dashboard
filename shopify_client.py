"""Récupère les vraies commandes Shopify et les relie aux ads via les UTM.

(La 1re ligne active la syntaxe de type moderne même sur Python 3.9.)

Le lien commande -> ad se fait via le paramètre utm_content de l'URL d'arrivée
(order.landing_site). Pour que ça marche, tes ads Meta doivent avoir dans
'Paramètres d'URL' :

    utm_source=facebook&utm_medium=paid&utm_campaign={{campaign.name}}&utm_content={{ad.id}}

Ainsi utm_content = l'ID de l'ad Meta, qu'on retrouve dans meta.py -> 'ad_id'.
"""
from __future__ import annotations

from urllib.parse import urlparse, parse_qs
from datetime import datetime, timedelta, timezone
import requests
import config

# Combien de jours de commandes on remonte (aligné grosso modo sur la fenêtre Meta)
PRESET_DAYS = {
    "today": 1, "yesterday": 2, "last_7d": 7, "last_14d": 14,
    "last_30d": 30, "last_90d": 90, "maximum": 365,
}


def _created_at_min():
    days = PRESET_DAYS.get(config.META_DATE_PRESET, 30)
    since = datetime.now(timezone.utc) - timedelta(days=days)
    return since.isoformat()


def get_access_token() -> str:
    """Échange le Client ID + Secret contre un token d'accès (client credentials grant).

    Valable 24h — on en redemande un frais à chaque exécution, donc rien à renouveler
    à la main. Doc : https://shopify.dev/docs/apps/build/dev-dashboard/get-api-access-tokens
    """
    url = f"https://{config.SHOPIFY_STORE}/admin/oauth/access_token"
    resp = requests.post(url, json={
        "client_id": config.SHOPIFY_CLIENT_ID,
        "client_secret": config.SHOPIFY_CLIENT_SECRET,
        "grant_type": "client_credentials",
    }, timeout=60)
    if resp.status_code != 200:
        raise SystemExit(f"❌ Erreur token Shopify ({resp.status_code}): {resp.text}")
    return resp.json()["access_token"]


def _extract_ad_id(landing_site: str) -> str | None:
    """Extrait utm_content (= ad_id Meta) depuis l'URL d'arrivée d'une commande."""
    if not landing_site:
        return None
    try:
        qs = parse_qs(urlparse(landing_site).query)
    except Exception:
        return None
    vals = qs.get("utm_content")
    return vals[0] if vals else None


def fetch_orders_by_ad():
    """Renvoie (par_ad, totaux).

    par_ad : dict { ad_id -> {"orders": n, "revenue": float} }
    totaux : dict global { "orders", "revenue", "orders_from_meta", "revenue_from_meta" }
    """
    base = f"https://{config.SHOPIFY_STORE}/admin/api/{config.SHOPIFY_API_VERSION}/orders.json"
    headers = {"X-Shopify-Access-Token": get_access_token()}
    params = {
        "status": "any",
        "created_at_min": _created_at_min(),
        "limit": 250,
        "fields": "id,total_price,landing_site,created_at,financial_status,cancelled_at",
    }

    by_ad = {}
    totals = {"orders": 0, "revenue": 0.0, "orders_from_meta": 0, "revenue_from_meta": 0.0}
    url = base

    while url:
        resp = requests.get(url, params=params, headers=headers, timeout=60)
        if resp.status_code != 200:
            raise SystemExit(f"❌ Erreur Shopify API ({resp.status_code}): {resp.text}")
        orders = resp.json().get("orders", [])
        for o in orders:
            # On ignore les commandes annulées
            if o.get("cancelled_at"):
                continue
            revenue = float(o.get("total_price", 0) or 0)
            totals["orders"] += 1
            totals["revenue"] += revenue

            ad_id = _extract_ad_id(o.get("landing_site", ""))
            if ad_id:
                slot = by_ad.setdefault(ad_id, {"orders": 0, "revenue": 0.0})
                slot["orders"] += 1
                slot["revenue"] += revenue
                totals["orders_from_meta"] += 1
                totals["revenue_from_meta"] += revenue

        # Pagination Shopify via l'en-tête Link (rel="next")
        url = _next_link(resp.headers.get("Link", ""))
        params = None  # l'URL next contient déjà tout

    # Arrondis
    totals["revenue"] = round(totals["revenue"], 2)
    totals["revenue_from_meta"] = round(totals["revenue_from_meta"], 2)
    for v in by_ad.values():
        v["revenue"] = round(v["revenue"], 2)

    return by_ad, totals


def _next_link(link_header: str):
    """Parse l'en-tête Link de Shopify pour trouver l'URL de la page suivante."""
    if not link_header:
        return None
    for part in link_header.split(","):
        section = part.split(";")
        if len(section) < 2:
            continue
        if 'rel="next"' in section[1]:
            return section[0].strip().strip("<>")
    return None


if __name__ == "__main__":
    by_ad, totals = fetch_orders_by_ad()
    print("Totaux :", totals)
    print(f"{len(by_ad)} ads avec commandes attribuées")
