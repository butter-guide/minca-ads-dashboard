"""Point d'entrée : récupère Meta + Shopify, met à jour le Google Sheet et le site chiffré."""
import meta
import shopify_client
import sheets
import site_data


def run():
    print("→ Récupération des stats Meta…")
    meta_rows = meta.fetch_ads_insights()
    print(f"  {len(meta_rows)} ads récupérées")

    print("→ Récupération des commandes Shopify…")
    by_ad, totals, orders_detail = shopify_client.fetch_orders_by_ad()
    print(f"  {totals['orders']} commandes ({totals['orders_from_meta']} attribuées, "
          f"{len(orders_detail)} détaillées)")

    print("→ Écriture dans Google Sheets…")
    sheets.write(meta_rows, by_ad, totals)

    print("→ Génération du site chiffré…")
    n_ads, n_orders = site_data.build(meta_rows, by_ad, totals, orders_detail)
    print(f"✅ Terminé — {n_ads} ads + {n_orders} commandes dans le dashboard.")


if __name__ == "__main__":
    run()
