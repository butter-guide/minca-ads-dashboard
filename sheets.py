"""Envoie les données au Google Sheet via un Apps Script Web App.

Pas de compte de service : le script Apps Script (déployé depuis le Sheet lui-même)
reçoit un POST JSON et écrit les onglets 'Par ad' et 'Résumé'.
Voir apps_script.gs pour le code à coller côté Google.
"""
from datetime import datetime, timezone, timedelta
import requests
import config

# En-têtes de l'onglet détaillé
HEADERS = [
    "Campagne", "Ad set", "Ad", "Ad ID",
    f"Dépense ({config.CURRENCY})", "Impressions", "Clics", "Clics lien",
    "Visites site", "Purchases Meta", f"CA Meta ({config.CURRENCY})",
    "Commandes Shopify", f"CA Shopify ({config.CURRENCY})",
    "ROAS Meta", "ROAS réel (Shopify)",
    "CPC", "CTR %", "CPM", f"Coût/visite ({config.CURRENCY})",
    f"Coût/achat ({config.CURRENCY})", "Écart purchases (Meta-Shopify)",
]


def _now_paris():
    return (datetime.now(timezone.utc) + timedelta(hours=2)).strftime("%d/%m/%Y %H:%M")


def _build(meta_rows, shopify_by_ad, shopify_totals):
    par_ad = [HEADERS]
    tot = {"spend": 0.0, "impr": 0, "clicks": 0, "visits": 0,
           "meta_p": 0, "meta_v": 0.0, "shop_o": 0, "shop_r": 0.0}

    for r in sorted(meta_rows, key=lambda x: x["spend"], reverse=True):
        s = shopify_by_ad.get(r["ad_id"], {"orders": 0, "revenue": 0.0})
        real_roas = round(s["revenue"] / r["spend"], 2) if r["spend"] else 0.0
        par_ad.append([
            r["campaign_name"], r["adset_name"], r["ad_name"], r["ad_id"],
            r["spend"], r["impressions"], r["clicks"], r["link_clicks"],
            r["visits"], r["meta_purchases"], r["meta_purchase_value"],
            s["orders"], s["revenue"],
            r["meta_roas"], real_roas,
            r["cpc"], r["ctr"], r["cpm"], r["cost_per_visit"],
            r["cost_per_purchase"], r["meta_purchases"] - s["orders"],
        ])
        tot["spend"] += r["spend"]; tot["impr"] += r["impressions"]
        tot["clicks"] += r["clicks"]; tot["visits"] += r["visits"]
        tot["meta_p"] += r["meta_purchases"]; tot["meta_v"] += r["meta_purchase_value"]
        tot["shop_o"] += s["orders"]; tot["shop_r"] += s["revenue"]

    total_spend = round(tot["spend"], 2)
    resume = [
        ["Résumé — Minca Ads", ""],
        ["Dernière mise à jour", _now_paris()],
        ["Fenêtre", config.META_DATE_PRESET],
        ["", ""],
        ["MÉTRIQUE", "VALEUR"],
        [f"Dépense totale ({config.CURRENCY})", total_spend],
        ["Impressions", tot["impr"]],
        ["Clics", tot["clicks"]],
        ["Visites site", tot["visits"]],
        ["Purchases (Meta)", tot["meta_p"]],
        [f"CA attribué Meta ({config.CURRENCY})", round(tot["meta_v"], 2)],
        ["Commandes Shopify (attribuées ads)", tot["shop_o"]],
        [f"CA Shopify (attribué ads) ({config.CURRENCY})", round(tot["shop_r"], 2)],
        ["Commandes Shopify (TOTAL boutique)", shopify_totals["orders"]],
        [f"CA Shopify (TOTAL boutique) ({config.CURRENCY})", shopify_totals["revenue"]],
        ["", ""],
        ["ROAS Meta", round(tot["meta_v"] / total_spend, 2) if total_spend else 0],
        ["ROAS réel (Shopify attribué)", round(tot["shop_r"] / total_spend, 2) if total_spend else 0],
        ["Écart purchases (Meta - Shopify)", tot["meta_p"] - tot["shop_o"]],
    ]
    return par_ad, resume


def write(meta_rows, shopify_by_ad, shopify_totals):
    par_ad, resume = _build(meta_rows, shopify_by_ad, shopify_totals)
    payload = {"secret": config.SHEETS_SECRET, "par_ad": par_ad, "resume": resume}
    resp = requests.post(config.SHEETS_WEBAPP_URL, json=payload, timeout=120)
    if resp.status_code != 200 or "OK" not in resp.text:
        raise SystemExit(f"❌ Erreur écriture Sheet ({resp.status_code}): {resp.text[:300]}")
    return len(meta_rows)
