"""Récupère les stats par ad depuis l'API Meta Marketing."""
import requests
import config

# Types d'action Meta qui correspondent à "visite du site" et "achat".
# Meta renvoie plusieurs variantes selon le pixel/CAPI ; on prend la plus fiable dispo.
VISIT_ACTIONS = ["landing_page_view"]
PURCHASE_ACTIONS = [
    "offsite_conversion.fb_pixel_purchase",
    "omni_purchase",
    "purchase",
]


def _pick_action(actions, wanted_types):
    """Dans la liste 'actions' de Meta, renvoie la valeur du 1er type trouvé (par priorité)."""
    if not actions:
        return 0.0
    by_type = {a["action_type"]: float(a.get("value", 0)) for a in actions}
    for t in wanted_types:
        if t in by_type:
            return by_type[t]
    return 0.0


def fetch_ads_insights():
    """Renvoie une liste de dicts, un par ad, avec toutes les métriques Meta."""
    url = f"https://graph.facebook.com/{config.META_API_VERSION}/{config.META_AD_ACCOUNT_ID}/insights"
    params = {
        "access_token": config.META_ACCESS_TOKEN,
        "level": "ad",
        "date_preset": config.META_DATE_PRESET,
        "fields": ",".join([
            "ad_id", "ad_name", "adset_name", "campaign_name",
            "spend", "impressions", "clicks", "inline_link_clicks",
            "cpc", "ctr", "cpm", "actions", "action_values",
        ]),
        "limit": 500,
    }

    rows = []
    while url:
        resp = requests.get(url, params=params, timeout=60)
        if resp.status_code != 200:
            raise SystemExit(f"❌ Erreur Meta API ({resp.status_code}): {resp.text}")
        payload = resp.json()
        for d in payload.get("data", []):
            spend = float(d.get("spend", 0))
            visits = _pick_action(d.get("actions"), VISIT_ACTIONS)
            purchases = _pick_action(d.get("actions"), PURCHASE_ACTIONS)
            purchase_value = _pick_action(d.get("action_values"), PURCHASE_ACTIONS)
            link_clicks = float(d.get("inline_link_clicks", 0))
            rows.append({
                "campaign_name": d.get("campaign_name", ""),
                "adset_name": d.get("adset_name", ""),
                "ad_name": d.get("ad_name", ""),
                "ad_id": d.get("ad_id", ""),
                "spend": round(spend, 2),
                "impressions": int(float(d.get("impressions", 0))),
                "clicks": int(float(d.get("clicks", 0))),
                "link_clicks": int(link_clicks),
                "visits": int(visits),
                "meta_purchases": int(purchases),
                "meta_purchase_value": round(purchase_value, 2),
                "cpc": round(float(d.get("cpc", 0) or 0), 2),
                "ctr": round(float(d.get("ctr", 0) or 0), 2),
                "cpm": round(float(d.get("cpm", 0) or 0), 2),
                # Métriques dérivées
                "cost_per_visit": round(spend / visits, 2) if visits else 0.0,
                "cost_per_purchase": round(spend / purchases, 2) if purchases else 0.0,
                "meta_roas": round(purchase_value / spend, 2) if spend else 0.0,
            })
        # pagination
        url = payload.get("paging", {}).get("next")
        params = None  # l'URL 'next' contient déjà tous les paramètres

    return rows


if __name__ == "__main__":
    import json
    data = fetch_ads_insights()
    print(f"{len(data)} ads récupérées")
    print(json.dumps(data[:2], indent=2, ensure_ascii=False))
