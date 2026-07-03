# Dashboard Pareo Ads (Meta + Shopify → Google Sheets)

Un script qui récupère toutes les 30 min les stats de tes ads Meta et les vraies
commandes Shopify, et remplit un Google Sheet auto-actualisé.

## Ce que tu obtiens (par ad)
Dépense · Impressions · Clics · Visites site · Purchases Meta + CA Meta ·
Commandes Shopify + CA Shopify réel · ROAS Meta vs ROAS réel · CPC · CTR · CPM ·
Coût/visite · Coût/achat · Écart d'attribution Meta vs Shopify.
Plus un onglet **Résumé** avec les totaux et l'heure de dernière mise à jour.

---

## 🔑 Les 4 accès à créer (une seule fois)

### 1. Meta — token + ID de compte
- **ID du compte pub** : Gestionnaire de publicités → en haut, format `act_1234567890`.
- **Token `ads_read` durable** (System User) :
  1. https://developers.facebook.com → *Mes apps* → créer une app type **Business**.
     Note l'**App ID** et l'**App Secret**.
  2. https://business.facebook.com → *Paramètres d'entreprise* → *Utilisateurs* →
     **Utilisateurs système** → *Ajouter*.
  3. Assigne-lui ton compte publicitaire avec l'accès **Lecture**.
  4. *Générer un token* → choisis ton app → coche **`ads_read`** → génère.
     ⚠️ Copie-le tout de suite (il ne réapparaît pas). Les tokens system-user
     peuvent ne jamais expirer → parfait pour l'automatisation.

### 2. Shopify — token Admin API
1. Admin Shopify → *Paramètres* → *Applications et canaux de vente* →
   **Développer des applications** → *Créer une application*.
2. *Configurer les scopes Admin API* → coche **`read_orders`**.
3. *Installer l'application* → révèle le **jeton d'accès Admin API** (`shpat_…`).
- Note aussi ton domaine : `xxxxx.myshopify.com`.

### 3. Google Sheets — compte de service
1. https://console.cloud.google.com → crée un projet.
2. *API et services* → active **Google Sheets API**.
3. *Identifiants* → **Créer un compte de service** → une fois créé, onglet *Clés* →
   *Ajouter une clé* → **JSON** → télécharge le fichier.
4. Crée un Google Sheet vide. Note son **ID** (dans l'URL, entre `/d/` et `/edit`).
5. **Partage le Sheet** avec l'email du compte de service
   (`xxx@xxx.iam.gserviceaccount.com`) en tant qu'**Éditeur**.

### 4. UTM sur tes ads (pour relier Shopify à chaque ad)
Dans chaque ad Meta → section *Suivi* → **Paramètres d'URL** :
```
utm_source=facebook&utm_medium=paid&utm_campaign={{campaign.name}}&utm_content={{ad.id}}
```
`utm_content = {{ad.id}}` est la clé qui permet de matcher une commande à une ad.

---

## 🧪 Test en local
```bash
cd ~/pareo-ads-dashboard
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # puis remplis .env
# place le JSON du compte de service ici sous le nom service_account.json
python main.py
```

## ☁️ Déploiement GitHub Actions (auto toutes les 30 min)
1. Crée un dépôt **privé** sur GitHub et pousse ce dossier.
2. Dépôt → *Settings* → *Secrets and variables* → *Actions* → ajoute ces secrets :
   `META_ACCESS_TOKEN`, `META_AD_ACCOUNT_ID`, `META_DATE_PRESET`,
   `SHOPIFY_STORE`, `SHOPIFY_ACCESS_TOKEN`,
   `GOOGLE_SHEET_ID`, `GOOGLE_SA_JSON` (colle **tout** le contenu du fichier JSON),
   `CURRENCY`.
3. Onglet *Actions* → lance le workflow à la main une fois pour vérifier, puis il
   tournera tout seul toutes les 30 min.
