"""Point d'entrée : récupère Meta + Shopify, met à jour le Google Sheet et le site chiffré."""
import meta
import shopify_client
import sheets
import site_data
import config

# Nb de jours affichés dans le Google Sheet (le site, lui, est interactif)
SHEET_DAYS = 30


def run():
    print("→ Récupération des stats Meta (par jour)…")
    daily = meta.fetch_ads_insights_daily()
    print(f"  {len(daily)} lignes jour×ad")

    print("→ Récupération des commandes Shopify (détaillées)…")
    orders = shopify_client.fetch_orders_all()
    print(f"  {len(orders)} commandes")

    print(f"→ Google Sheet (agrégé {SHEET_DAYS} j)…")
    meta_rows = meta.aggregate_window(daily, shopify_client._since_date(SHEET_DAYS))
    by_ad, totals = shopify_client.aggregate_orders(orders, SHEET_DAYS)
    sheets.write(meta_rows, by_ad, totals)

    print("→ Génération du site chiffré…")
    n_ads, n_orders = site_data.build(daily, orders)
    print(f"✅ Terminé — {n_ads} lignes ads + {n_orders} commandes ({config.SITE_FETCH_DAYS} j) dans le dashboard.")


if __name__ == "__main__":
    run()
