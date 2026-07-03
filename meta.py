"""Récupère les stats par ad depuis l'API Meta Marketing (détail par jour)."""
import requests
import config

VISIT_ACTIONS = ["landing_page_view"]
PURCHASE_ACTIONS = [
    "offsite_conversion.fb_pixel_purchase",
    "omni_purchase",
    "purchase",
]


def _pick_action(actions, wanted_types):
    if not actions:
        return 0.0
    by_type = {a["action_type"]: float(a.get("value", 0)) for a in actions}
    for t in wanted_types:
        if t in by_type:
            return by_type[t]
    return 0.0


def fetch_ads_insights_daily(date_preset=None):
    """Renvoie une ligne PAR AD ET PAR JOUR (time_increment=1) sur la fenêtre demandée.

    Chaque dict : ad_id, ad_name, adset_name, campaign_name, date, + métriques brutes.
    Le navigateur ré-agrège ensuite sur la période choisie par l'utilisatrice.
    """
    preset = date_preset or config.SITE_FETCH_PRESET
    url = f"https://graph.facebook.com/{config.META_API_VERSION}/{config.META_AD_ACCOUNT_ID}/insights"
    params = {
        "access_token": config.META_ACCESS_TOKEN,
        "level": "ad",
        "date_preset": preset,
        "time_increment": 1,
        "fields": ",".join([
            "ad_id", "ad_name", "adset_name", "campaign_name",
            "spend", "impressions", "clicks", "inline_link_clicks",
            "actions", "action_values",
        ]),
        "limit": 500,
    }

    rows = []
    while url:
        resp = requests.get(url, params=params, timeout=90)
        if resp.status_code != 200:
            raise SystemExit(f"❌ Erreur Meta API ({resp.status_code}): {resp.text}")
        payload = resp.json()
        for d in payload.get("data", []):
            rows.append({
                "campaign_name": d.get("campaign_name", ""),
                "adset_name": d.get("adset_name", ""),
                "ad_name": d.get("ad_name", ""),
                "ad_id": d.get("ad_id", ""),
                "date": d.get("date_start", ""),
                "spend": round(float(d.get("spend", 0)), 2),
                "impressions": int(float(d.get("impressions", 0))),
                "clicks": int(float(d.get("clicks", 0))),
                "link_clicks": int(float(d.get("inline_link_clicks", 0))),
                "visits": int(_pick_action(d.get("actions"), VISIT_ACTIONS)),
                "meta_purchases": int(_pick_action(d.get("actions"), PURCHASE_ACTIONS)),
                "meta_value": round(_pick_action(d.get("action_values"), PURCHASE_ACTIONS), 2),
            })
        url = payload.get("paging", {}).get("next")
        params = None

    return rows


def aggregate_window(daily_rows, since_date=None):
    """Agrège les lignes quotidiennes par ad (optionnellement depuis since_date 'YYYY-MM-DD').

    Renvoie la même structure que l'ancien fetch_ads_insights (pour le Google Sheet).
    """
    agg = {}
    for r in daily_rows:
        if since_date and r["date"] < since_date:
            continue
        a = agg.setdefault(r["ad_id"], {
            "campaign_name": r["campaign_name"], "adset_name": r["adset_name"],
            "ad_name": r["ad_name"], "ad_id": r["ad_id"],
            "spend": 0.0, "impressions": 0, "clicks": 0, "link_clicks": 0,
            "visits": 0, "meta_purchases": 0, "meta_purchase_value": 0.0,
        })
        a["spend"] += r["spend"]; a["impressions"] += r["impressions"]
        a["clicks"] += r["clicks"]; a["link_clicks"] += r["link_clicks"]
        a["visits"] += r["visits"]; a["meta_purchases"] += r["meta_purchases"]
        a["meta_purchase_value"] += r["meta_value"]

    out = []
    for a in agg.values():
        spend = round(a["spend"], 2); v = a["visits"]; p = a["meta_purchases"]
        out.append({**a,
            "spend": spend,
            "meta_purchase_value": round(a["meta_purchase_value"], 2),
            "cpc": round(spend / a["clicks"], 2) if a["clicks"] else 0.0,
            "ctr": round(a["clicks"] / a["impressions"] * 100, 2) if a["impressions"] else 0.0,
            "cpm": round(spend / a["impressions"] * 1000, 2) if a["impressions"] else 0.0,
            "cost_per_visit": round(spend / v, 2) if v else 0.0,
            "cost_per_purchase": round(spend / p, 2) if p else 0.0,
            "meta_roas": round(a["meta_purchase_value"] / spend, 2) if spend else 0.0,
        })
    return out


if __name__ == "__main__":
    daily = fetch_ads_insights_daily()
    print(f"{len(daily)} lignes jour×ad")
    print(f"{len(aggregate_window(daily))} ads au total")
