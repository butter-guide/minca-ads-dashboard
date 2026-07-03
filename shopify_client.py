"""Récupère les commandes Shopify (détaillées) et les relie aux ads via les UTM.

(La 1re ligne active la syntaxe de type moderne même sur Python 3.9.)

Le lien commande -> ad se fait via le paramètre utm_content de l'URL d'arrivée
(order.landing_site) : utm_content = ID de l'ad Meta (voir meta.py -> 'ad_id').
"""
from __future__ import annotations

from urllib.parse import urlparse, parse_qs
from datetime import datetime, timedelta, timezone
import requests
import config


def _since_date(days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).date().isoformat()


def _created_at_min(days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


def get_access_token() -> str:
    """Échange le Client ID + Secret contre un token d'accès (client credentials grant, 24h)."""
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
    if not landing_site:
        return None
    try:
        qs = parse_qs(urlparse(landing_site).query)
    except Exception:
        return None
    vals = qs.get("utm_content")
    return vals[0] if vals else None


def _next_link(link_header: str):
    if not link_header:
        return None
    for part in link_header.split(","):
        section = part.split(";")
        if len(section) >= 2 and 'rel="next"' in section[1]:
            return section[0].strip().strip("<>")
    return None


def fetch_orders_all(days: int | None = None):
    """Renvoie la liste de TOUTES les commandes (non annulées) sur la fenêtre, détaillées.

    Chaque commande : order, date, amount, items, status, country, first_order,
    ad_id (=utm_content ou ""), is_meta_ad, products [{title, qty, price}].
    """
    days = days or config.SITE_FETCH_DAYS
    base = f"https://{config.SHOPIFY_STORE}/admin/api/{config.SHOPIFY_API_VERSION}/orders.json"
    headers = {"X-Shopify-Access-Token": get_access_token()}
    params = {
        "status": "any",
        "created_at_min": _created_at_min(days),
        "limit": 250,
        "fields": ("id,name,total_price,landing_site,created_at,financial_status,"
                   "cancelled_at,line_items,customer,shipping_address"),
    }

    orders = []
    url = base
    while url:
        resp = requests.get(url, params=params, headers=headers, timeout=90)
        if resp.status_code != 200:
            raise SystemExit(f"❌ Erreur Shopify API ({resp.status_code}): {resp.text}")
        for o in resp.json().get("orders", []):
            if o.get("cancelled_at"):
                continue
            ad_id = _extract_ad_id(o.get("landing_site", "")) or ""
            line_items = o.get("line_items", []) or []
            cust = o.get("customer") or {}
            ship = o.get("shipping_address") or {}
            order_date = (o.get("created_at") or "")[:10]
            # orders_count a été retiré de l'API REST → on déduit la 1re commande via la
            # date de création du client (créé le jour de la commande = nouveau client).
            cust_created = (cust.get("created_at") or "")[:10]
            orders.append({
                "order": o.get("name", ""),
                "date": order_date,
                "amount": round(float(o.get("total_price", 0) or 0), 2),
                "items": sum(int(li.get("quantity", 0)) for li in line_items),
                "status": o.get("financial_status", ""),
                "country": ship.get("country") or "—",
                "first_order": bool(cust_created) and cust_created == order_date,
                "ad_id": ad_id,
                "is_meta_ad": ad_id.isdigit(),
                "products": [{
                    "title": li.get("title", ""),
                    "qty": int(li.get("quantity", 0)),
                    "price": round(float(li.get("price", 0) or 0), 2),
                } for li in line_items],
            })
        url = _next_link(resp.headers.get("Link", ""))
        params = None
    return orders


def aggregate_orders(orders, days: int):
    """Agrège les commandes (depuis N jours) pour le Google Sheet.

    Renvoie (by_ad, totals) comme l'ancienne version.
    """
    since = _since_date(days)
    by_ad = {}
    totals = {"orders": 0, "revenue": 0.0, "orders_from_meta": 0, "revenue_from_meta": 0.0}
    for o in orders:
        if o["date"] < since:
            continue
        totals["orders"] += 1
        totals["revenue"] += o["amount"]
        if o["ad_id"]:
            slot = by_ad.setdefault(o["ad_id"], {"orders": 0, "revenue": 0.0})
            slot["orders"] += 1
            slot["revenue"] += o["amount"]
            totals["orders_from_meta"] += 1
            totals["revenue_from_meta"] += o["amount"]
    totals["revenue"] = round(totals["revenue"], 2)
    totals["revenue_from_meta"] = round(totals["revenue_from_meta"], 2)
    for v in by_ad.values():
        v["revenue"] = round(v["revenue"], 2)
    return by_ad, totals


if __name__ == "__main__":
    orders = fetch_orders_all()
    print(f"{len(orders)} commandes récupérées")
    with_country = sum(1 for o in orders if o["country"] != "—")
    firsts = sum(1 for o in orders if o["first_order"])
    print(f"  pays renseigné: {with_country} | 1res commandes: {firsts}")
    if orders:
        import json
        print(json.dumps(orders[0], indent=2, ensure_ascii=False))
