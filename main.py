"""Point d'entrée : récupère Meta + Shopify et met à jour le Google Sheet."""
import meta
import shopify_client
import sheets


def run():
    print("→ Récupération des stats Meta…")
    meta_rows = meta.fetch_ads_insights()
    print(f"  {len(meta_rows)} ads récupérées")

    print("→ Récupération des commandes Shopify…")
    shop_by_ad, shop_totals = shopify_client.fetch_orders_by_ad()
    print(f"  {shop_totals['orders']} commandes ({shop_totals['orders_from_meta']} attribuées à une ad)")

    print("→ Écriture dans Google Sheets…")
    n = sheets.write(meta_rows, shop_by_ad, shop_totals)
    print(f"✅ Terminé — {n} ads écrites dans le Sheet.")


if __name__ == "__main__":
    run()
