# ふたりの台所 (Futari no Daidokoro) — Japanese recipe website

Easy Japanese home cooking **for two**, written for readers aged 55+ in Japan.
Static HTML, iPhone-first, AdSense-ready, deploys to **Azure Static Web Apps** from GitHub.

- 20 recipes (2 servings each, one-tap 1人分 / 2人分 / 4人分 scaling)
- 5 categories: 肉のおかず・魚のおかず・ご飯・丼・麺・副菜・汁もの・ふたり鍋
- 5 articles (読みもの): cooking for two, freezing, measuring, food poisoning prevention, dashi
- Japan-specific policy pages: 運営者情報, お問い合わせ, プライバシーポリシー (with the
  外部送信 disclosure required by 電気通信事業法 Art. 27-12, and APPI wording), 利用規約, 免責事項
- Recipe + Breadcrumb JSON-LD, sitemap.xml, robots.txt, ads.txt, web manifest, icons
- Reader features: 文字サイズ (text size), 画面を消さない (screen wake lock), ingredient check-off, print card, share, search

## 1. Before you publish
Edit `SETTINGS` at the top of `tools/build.py`:

| Setting | What to put |
|---|---|
| `site_url` | Your real domain, e.g. `https://www.futari-daidokoro.jp` |
| `contact_email` | The address readers should write to (a separate inbox is a good idea) |
| `operator` | Operator name shown on 運営者情報 / プライバシーポリシー |
| `adsense_client` | `ca-pub-…` once AdSense gives it to you |
| `ga_id` | Optional `G-…` Google Analytics ID (the privacy policy table updates automatically) |

Then run `python3 tools/build.py` (Python 3.8+, no packages needed).

## 2. Photos
Photos are self-hosted (PAKUTASO does not allow hotlinking). Put one JPG per recipe at
`site/assets/img/recipes/<slug>.jpg` and a wide hero photo at `site/assets/img/hero.jpg`, then rebuild.
Recipes without a photo show a coloured emoji tile, so the site works either way.
Recommended: 1200×900 px, under 250 KB. Sources used are listed in `PHOTO-CREDITS.md`.

Recipe slugs: shogayaki, nikujaga, tori-teriyaki, wafu-hamburg, karaage, sake-hoiruyaki, saba-misoni,
buri-teriyaki, oyakodon, gyudon, curry-rice, kinoko-takikomi, nikomi-udon, dashimaki-tamago, tonjiru,
horenso-gomaae, kinpira-gobou, sukiyaki, yosenabe, oden.

## 3. Deploy to Azure via GitHub
1. Create a GitHub repo and push this folder.
2. Azure Portal → Create **Static Web App** (Free plan) → Source: GitHub → pick the repo/branch.
   Build presets: **Custom**, App location `site`, Output location empty.
3. Azure adds the `AZURE_STATIC_WEB_APPS_API_TOKEN` secret; the included workflow
   (`.github/workflows/azure-static-web-apps.yml`) publishes on every push.
4. Add your custom domain in the Static Web App → Custom domains.
5. Submit `https://yourdomain/sitemap.xml` in Google Search Console.

## 4. AdSense
Apply after the site is live on your own domain with the policy pages linked in the footer (they are).
When approved: set `adsense_client`, rebuild, push. `ads.txt` fills in automatically.

## 5. Google Ads targeting (Japan, 55+, iPhone)
- Locations: **Japan**; Language: **Japanese**
- Demographics → Age: **55–64** and **65+** (exclude the rest)
- Devices: Mobile; optionally Operating system **iOS**
- Audiences: In-market / affinity "Cooking enthusiasts", "Food & dining"; custom segments with
  keywords like 2人分 レシピ, 夫婦ふたり 献立, シニア 簡単 料理, 作り置き 少量
- Ad copy ideas: 「ふたり分がちょうどいい」「作りすぎない晩ごはん」「さばの味噌煮も10分で下ごしらえ」

## Folder layout
```
site/            ← published website (generated + assets)
tools/build.py   ← generator & settings
tools/content_recipes.py, content_articles.py  ← all Japanese text
brand/           ← logo source (make_logo.py) and PNG/SVG logo files
```
