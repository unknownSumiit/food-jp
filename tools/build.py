#!/usr/bin/env python3
"""
「ふたりの台所」静的サイトを ../site フォルダに生成します。
Builds the Futari no Daidokoro static website into ../site.

1. Edit SETTINGS below (domain, contact email, operator name, AdSense ID).
2. Put photos at site/assets/img/recipes/<recipe-slug>.jpg  (and site/assets/img/hero.jpg)
3. Run:  python3 tools/build.py
4. Commit and push to GitHub. Azure Static Web Apps publishes the /site folder.
Python 3.8+ only, no extra packages.
"""
import html, json, os, re, sys
from datetime import date
from fractions import Fraction

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from content_recipes import CATEGORIES, RECIPES   # noqa: E402
from content_articles import ARTICLES              # noqa: E402

# ---------------------------------------------------------------------------
# SETTINGS — 公開前に変更してください
# ---------------------------------------------------------------------------
SETTINGS = {
    "site_name": "ふたりの台所",
    "tagline": "ふたり分がちょうどいい、毎日のごはん",
    "site_url": "https://www.yourdomain.com",          # 末尾にスラッシュは付けない
    "contact_email": "contact@yourdomain.com",
    "operator": "ふたりの台所 編集部",                    # 運営者名
    "adsense_client": "",                              # 例 "ca-pub-1234567890123456"
    "ga_id": "",                                       # 例 "G-XXXXXXXXXX"（Google アナリティクスを使う場合）
    "updated": date(2026, 11, 19),
    "established": "2026年11月",
    "popular_recipes": [
        "shogayaki", "nikujaga", "saba-misoni", "oyakodon",
        "buri-teriyaki", "wafu-hamburg", "tonjiru", "sukiyaki",
    ],
}
# ---------------------------------------------------------------------------

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "site")
S = SETTINGS
E = html.escape
U = S["updated"]
UPDATED_HUMAN = f"{U.year}年{U.month}月{U.day}日"
UPDATED_ISO = U.isoformat()
PAGES = []
CAT = {c["slug"]: c for c in CATEGORIES}
REC = {r["slug"]: r for r in RECIPES}

ICON_PRINT = '<svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 9V3h12v6"/><rect x="3" y="9" width="18" height="8" rx="2"/><path d="M6 14h12v7H6z"/></svg>'
ICON_SHARE = '<svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3v12"/><path d="M7 8l5-5 5 5"/><path d="M5 12v7a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-7"/></svg>'
ICON_DOWN = '<svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 4v15"/><path d="M6 13l6 6 6-6"/></svg>'

NAV = [("ホーム", "index.html", "home"), ("レシピ", "recipes/index.html", "recipes"),
       ("読みもの", "articles/index.html", "articles"), ("運営者情報", "about.html", "about"),
       ("お問い合わせ", "contact.html", "contact")]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def canonical_for(path):
    if path == "index.html":
        return S["site_url"] + "/"
    if path.endswith("/index.html"):
        return S["site_url"] + "/" + path[: -len("index.html")]
    return S["site_url"] + "/" + path


def prefix(path):
    return "../" * path.count("/")


def fmt_ja(x):
    """1.5 -> 1と1/2,  0.25 -> 1/4,  200 -> 200"""
    if x >= 10:
        return str(round(x))
    f = Fraction(x).limit_denominator(8)
    whole, rest = divmod(f.numerator, f.denominator)
    rest = Fraction(rest, f.denominator)
    if rest == 0:
        return str(whole)
    fr = f"{rest.numerator}/{rest.denominator}"
    return f"{whole}と{fr}" if whole else fr


def amount_html(a):
    """'大さじ{1.5}' -> 大さじ<span class="qty" data-qty="1.5">1と1/2</span>"""
    def rep(m):
        v = float(Fraction(m.group(1)))
        return f'<span class="qty" data-qty="{v:.6g}">{fmt_ja(v)}</span>'
    parts = re.split(r"(\{[^}]+\})", a)
    out = []
    for part in parts:
        m = re.fullmatch(r"\{([^}]+)\}", part)
        out.append(rep(m) if m else E(part))
    return "".join(out)


def amount_plain(a):
    return re.sub(r"\{([^}]+)\}", lambda m: fmt_ja(float(Fraction(m.group(1)))), a)


def fmt_minutes(m):
    if m < 60:
        return f"{m}分"
    h, r = divmod(m, 60)
    return f"{h}時間" + (f"{r}分" if r else "")


def iso_duration(m):
    h, r = divmod(m, 60)
    return "PT" + (f"{h}H" if h else "") + (f"{r}M" if r or not h else "")


def yield_unit(r):
    return r.get("yield_unit", "人分")


def total_minutes(r):
    return r["prep"] + r["cook"] + r.get("extra", 0)


def local_photo(slug):
    for ext in ("jpg", "jpeg", "webp", "png"):
        rel = f"assets/img/recipes/{slug}.{ext}"
        if os.path.exists(os.path.join(OUT, rel)):
            return rel
    return None


def hero_photo():
    for ext in ("jpg", "jpeg", "webp"):
        rel = f"assets/img/hero.{ext}"
        if os.path.exists(os.path.join(OUT, rel)):
            return rel
    return None


def photo_abs_urls(slug):
    loc = local_photo(slug)
    return [S["site_url"] + "/" + loc] if loc else []


def tile(r, p, cls="tile", eager=False, ratio=(4, 3)):
    alt = E(r["title"])
    loc = local_photo(r["slug"])
    rw, rh = ratio
    if not loc:
        return f'<div class="{cls} tile-{r["category"]} no-photo" data-emoji="{r["emoji"]}" aria-hidden="true"></div>'
    loading = "eager" if eager else "lazy"
    priority = ' fetchpriority="high"' if eager else ""
    return (f'<div class="{cls} tile-{r["category"]}"><img src="{p}{loc}" alt="{alt}" loading="{loading}"{priority} '
            f'decoding="async" width="{rw * 300}" height="{rh * 300}"></div>')


def sidebar(p, current=None):
    picks = [REC[s] for s in S["popular_recipes"] if s != current][:5]
    minis = "".join(
        f'<a class="mini" href="{p}recipes/{r["slug"]}.html">{tile(r, p, ratio=(1, 1))}'
        f'<div><strong>{E(r["title"])}</strong><span>{fmt_minutes(total_minutes(r))}</span></div></a>'
        for r in picks)
    cats = "".join(f'<li><a href="{p}category/{c["slug"]}.html">{c["emoji"]} {E(c["name"])}</a></li>' for c in CATEGORIES)
    return (f'<aside class="sidebar no-print" aria-label="おすすめ">'
            f'<div class="side-box"><h2>人気のレシピ</h2>{minis}</div>'
            f'<div class="side-box"><h2>カテゴリー</h2><ul class="side-cats">{cats}</ul></div></aside>')


def cat_card(c, p):
    first = next((r for r in RECIPES if r["category"] == c["slug"] and local_photo(r["slug"])), None)
    img = tile(first, p) if first else f'<div class="tile tile-{c["slug"]} no-photo" data-emoji="{c["emoji"]}" aria-hidden="true"></div>'
    return f'<a class="cat-card" href="{p}category/{c["slug"]}.html">{img}<span class="cat-name">{E(c["name"])}</span></a>'


def recipe_card(r, p):
    search = E(f'{r["title"]} {r["desc"]} {CAT[r["category"]]["name"]} ' + " ".join(n for n, _ in r["ingredients"] if n != "#"))
    return (f'<a class="card" href="{p}recipes/{r["slug"]}.html" data-search="{search}">{tile(r, p)}'
            f'<div class="body"><span class="tag">{E(CAT[r["category"]]["name"])}</span>'
            f'<h3>{E(r["title"])}</h3><p>{E(r["desc"])}</p>'
            f'<span class="facts">⏱ {fmt_minutes(total_minutes(r))}・{r["servings"]}{E(yield_unit(r))}</span></div></a>')


def article_card(a, p):
    return (f'<a class="card text-only" href="{p}articles/{a["slug"]}.html"><div class="body">'
            f'<span class="tag">読みもの</span><h3>{E(a["title"])}</h3><p>{E(a["desc"])}</p>'
            f'<span class="facts">約{a["minutes"]}分で読めます</span></div></a>')


def breadcrumbs(items, p):
    lis = []
    for i, (label, href) in enumerate(items):
        if href and i < len(items) - 1:
            lis.append(f'<li><a href="{p}{href}">{E(label)}</a></li>')
        else:
            lis.append(f'<li aria-current="page">{E(label)}</li>')
    return f'<nav class="breadcrumbs" aria-label="パンくずリスト"><ol>{"".join(lis)}</ol></nav>'


def org():
    return {"@type": "Organization", "name": S["site_name"], "url": S["site_url"] + "/"}


def head_scripts():
    out = []
    if S["adsense_client"]:
        out.append('<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client='
                   + E(S["adsense_client"]) + '" crossorigin="anonymous"></script>')
    else:
        out.append("<!-- AdSense code goes here -->")
    if S["ga_id"]:
        g = E(S["ga_id"])
        out.append(f'<script async src="https://www.googletagmanager.com/gtag/js?id={g}"></script>'
                   f"<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}"
                   f"gtag('js',new Date());gtag('config','{g}');</script>")
    return "\n".join(out)


def layout(path, title, description, body, active=None, og_type="website", jsonld=None,
           noindex=False, og_image=None):
    p = prefix(path)
    full_title = title if title == S["site_name"] else f"{title}｜{S['site_name']}"
    canonical = canonical_for(path)
    cur = ' aria-current="page"'
    nav = "".join(f'<li><a href="{p}{h}"{cur if k == active else ""}>{E(l)}</a></li>' for l, h, k in NAV)
    lds = jsonld if isinstance(jsonld, list) else ([jsonld] if jsonld else [])
    ld = "".join('<script type="application/ld+json">' + json.dumps(x, ensure_ascii=False) + "</script>" for x in lds)
    robots = "noindex" if noindex else "index, follow, max-image-preview:large"
    og_img = f'<meta property="og:image" content="{E(og_image)}">' if og_image else ""
    cat_links = "".join(f'<li><a href="{p}category/{c["slug"]}.html">{E(c["name"])}</a></li>' for c in CATEGORIES)
    page = f"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{E(full_title)}</title>
<meta name="description" content="{E(description)}">
<meta name="robots" content="{robots}">
<link rel="canonical" href="{E(canonical)}">
<meta property="og:type" content="{og_type}">
<meta property="og:locale" content="ja_JP">
<meta property="og:site_name" content="{E(S['site_name'])}">
<meta property="og:title" content="{E(title)}">
<meta property="og:description" content="{E(description)}">
<meta property="og:url" content="{E(canonical)}">
{og_img}
<meta name="twitter:card" content="summary_large_image">
<meta name="format-detection" content="telephone=no">
<meta name="theme-color" content="#faf6ee" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#171a1f" media="(prefers-color-scheme: dark)">
<meta name="apple-mobile-web-app-title" content="{E(S['site_name'])}">
<link rel="icon" href="{p}assets/img/favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="{p}apple-touch-icon.png">
<link rel="manifest" href="{p}site.webmanifest">
<link rel="stylesheet" href="{p}assets/css/style.css">
<script>try{{var s=localStorage.getItem("ft-text-size");if(s==="1")document.documentElement.classList.add("text-lg");if(s==="2")document.documentElement.classList.add("text-xl");}}catch(e){{}}</script>
{head_scripts()}
{ld}
</head>
<body>
<a class="skip-link" href="#main">本文へスキップ</a>
<header class="site-header">
  <div class="header-inner">
    <a class="brand" href="{p}index.html"><picture><source srcset="{p}assets/img/logo-white.svg" media="(prefers-color-scheme: dark)"><img src="{p}assets/img/logo.svg" alt="{E(S['site_name'])}" width="390" height="100"></picture></a>
    <nav class="site-nav" aria-label="メインメニュー">
      <ul>{nav}<li><button type="button" class="text-size-btn" aria-label="文字の大きさを変える"><span aria-hidden="true">あ<span style="font-size:1.3em">あ</span></span> 文字サイズ</button></li></ul>
    </nav>
  </div>
</header>
<main id="main">
<div class="container">
{body}
</div>
</main>
<footer class="site-footer">
  <div class="container">
    <div class="footer-grid">
      <div>
        <h2>{E(S['site_name'])}</h2>
        <p>{E(S['tagline'])}。夫婦ふたり、ひとり暮らしの方にちょうどいい分量の家庭料理レシピをお届けします。</p>
      </div>
      <div>
        <h2>レシピ</h2>
        <ul>{cat_links}<li><a href="{p}recipes/index.html">すべてのレシピ</a></li><li><a href="{p}articles/index.html">読みもの</a></li></ul>
      </div>
      <div>
        <h2>サイトについて</h2>
        <ul>
          <li><a href="{p}about.html">運営者情報</a></li>
          <li><a href="{p}contact.html">お問い合わせ</a></li>
          <li><a href="{p}privacy-policy.html">プライバシーポリシー</a></li>
          <li><a href="{p}terms-of-use.html">利用規約</a></li>
          <li><a href="{p}disclaimer.html">免責事項</a></li>
        </ul>
      </div>
    </div>
    <div class="footer-bottom"><p>&copy; {U.year} {E(S['site_name'])}</p></div>
  </div>
</footer>
<script src="{p}assets/js/main.js" defer></script>
</body>
</html>
"""
    dest = os.path.join(OUT, path)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "w", encoding="utf-8") as f:
        f.write(page)


# ---------------------------------------------------------------------------
# Recipe pages
# ---------------------------------------------------------------------------
def build_recipes():
    for idx, r in enumerate(RECIPES):
        path = f"recipes/{r['slug']}.html"
        p = prefix(path)
        c = CAT[r["category"]]
        tot = total_minutes(r)
        yu = yield_unit(r)

        facts = [("下ごしらえ", fmt_minutes(r["prep"]))]
        if r["cook"]:
            facts.append(("調理", fmt_minutes(r["cook"])))
        if r.get("extra"):
            facts.append((r.get("extra_label", "置き時間"), fmt_minutes(r["extra"])))
        facts.append(("合計", fmt_minutes(tot)))
        facts.append(("分量", f'{r["servings"]}{yu}'))
        facts_html = "".join(f'<div class="fact"><span>{E(k)}</span><strong>{E(v)}</strong></div>' for k, v in facts)

        items, plain, n = [], [], 0
        for name, amt in r["ingredients"]:
            if name == "#":
                items.append(f'<li class="group">{E(amt)}</li>')
                continue
            n += 1
            plain.append(f"{name} {amount_plain(amt)}".strip())
            items.append(f'<li><label for="ing-{n}"><input type="checkbox" id="ing-{n}"><span>'
                         f'<span class="ing-name">{E(name)}</span><span class="ing-amt">{amount_html(amt)}</span></span></label></li>')

        steps = "".join(f"<li>{E(s)}</li>" for s in r["steps"])
        tips = "".join(f"<li>{E(t)}</li>" for t in r["tips"])
        intro = "".join(f"<p>{E(x)}</p>" for x in r["intro"])

        same = [x for x in RECIPES if x["category"] == r["category"] and x["slug"] != r["slug"]]
        others = [x for x in RECIPES if x["category"] != r["category"]]
        related = (same + others[idx % len(others):] + others[:idx % len(others)])[:3]
        rel = "".join(recipe_card(x, p) for x in related)
        b = r["servings"]
        scale_btns = "".join(
            f'<button type="button" data-scale="{m}" aria-pressed="{"true" if m == 1 else "false"}">{fmt_ja(b * m)}{E(yu)}</button>'
            for m in (0.5, 1, 2))

        body = f"""
<div class="page-layout">
<article class="recipe-page readable">
{breadcrumbs([("ホーム", "index.html"), ("レシピ", "recipes/index.html"), (c["name"], f"category/{c['slug']}.html"), (r["title"], None)], p)}
<h1>{E(r["title"])}</h1>
<p class="meta">{E(S["operator"])}・更新日 {UPDATED_HUMAN}</p>
<p class="lead">{E(r["desc"])}</p>
<div class="recipe-hero">{tile(r, p, eager=True, ratio=(16, 10))}</div>
<div class="quick-facts">{facts_html}</div>
<div class="action-row">
  <a class="btn btn-primary" href="#recipe">{ICON_DOWN} レシピへ移動</a>
  <button type="button" class="btn btn-ghost" data-print>{ICON_PRINT} 印刷</button>
  <button type="button" class="btn btn-ghost" data-share="{E(r['title'] + '｜' + S['site_name'])}">{ICON_SHARE} 共有</button>
</div>
<div class="intro">{intro}</div>

<section class="recipe-card" id="recipe" aria-labelledby="recipe-h">
  <h2 id="recipe-h">{E(r["title"])}</h2>
  <div class="recipe-tools">
    <div class="scaler">
      <span class="label">分量を変える</span>
      <div class="seg" role="group" aria-label="分量を変える" data-scaler>{scale_btns}</div>
      <span class="servings-out"><span id="servings-count" data-base="{b}">{b}</span>{E(yu)}</span>
      <p class="scale-note">分量を変えたときは、鍋の大きさや加熱時間を様子を見て調整してください。</p>
    </div>
    <label class="cook-mode"><input type="checkbox" id="cook-mode"><span class="switch" aria-hidden="true"></span><span>画面を消さない<small>調理中にスマホの画面が暗くなりません</small></span></label>
  </div>

  <h3>材料</h3>
  <ul class="ingredients" data-key="{E(r["slug"])}">{"".join(items)}</ul>

  <h3>作り方</h3>
  <ol class="steps">{steps}</ol>

  <h3>コツ・ポイント</h3>
  <ul class="tips">{tips}</ul>

  <h3>保存方法</h3>
  <div class="storage"><p>{E(r["storage"])}</p></div>
</section>
<p class="small-print">大さじ1＝15ml、小さじ1＝5ml、1カップ＝200mlです。アレルギーのある方は原材料表示を必ずご確認ください。加熱時間は目安です。詳しくは<a href="{p}disclaimer.html">免責事項</a>をご覧ください。</p>
</article>
{sidebar(p, r["slug"])}
</div>
<section class="related no-print" aria-labelledby="rel-h"><h2 id="rel-h">こちらのレシピもおすすめ</h2><div class="grid">{rel}</div></section>
"""
        imgs = photo_abs_urls(r["slug"])
        ld = {
            "@context": "https://schema.org", "@type": "Recipe", "name": r["title"], "inLanguage": "ja",
            "description": r["desc"], "author": org(), "publisher": org(),
            "datePublished": UPDATED_ISO, "dateModified": UPDATED_ISO,
            "prepTime": iso_duration(r["prep"]), "totalTime": iso_duration(tot),
            "recipeYield": [str(b), f"{b}{yu}"],
            "recipeCategory": c["name"], "recipeCuisine": "和食",
            "keywords": "、".join([r["title"], "2人分", "簡単", "家庭料理", c["name"]]),
            "recipeIngredient": plain,
            "recipeInstructions": [{"@type": "HowToStep", "position": i + 1, "text": s,
                                    "url": canonical_for(path) + "#recipe"} for i, s in enumerate(r["steps"])],
            "mainEntityOfPage": canonical_for(path),
        }
        if r["cook"]:
            ld["cookTime"] = iso_duration(r["cook"])
        if imgs:
            ld["image"] = imgs
        crumbs = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "ホーム", "item": S["site_url"] + "/"},
            {"@type": "ListItem", "position": 2, "name": c["name"], "item": canonical_for(f"category/{c['slug']}.html")},
            {"@type": "ListItem", "position": 3, "name": r["title"]}]}
        layout(path, f'{r["title"]}（{b}{yu}）のレシピ', r["desc"], body, active="recipes",
               og_type="article", jsonld=[ld, crumbs], og_image=imgs[0] if imgs else None)
        PAGES.append((path, "0.8"))


def build_categories():
    for c in CATEGORIES:
        path = f"category/{c['slug']}.html"
        p = prefix(path)
        recs = [r for r in RECIPES if r["category"] == c["slug"]]
        intro = "".join(f'<p{" class=\"lead\"" if i == 0 else ""}>{E(x)}</p>' for i, x in enumerate(c["intro"]))
        others = "".join(cat_card(o, p) for o in CATEGORIES if o["slug"] != c["slug"])
        body = f"""
{breadcrumbs([("ホーム", "index.html"), ("レシピ", "recipes/index.html"), (c["name"], None)], p)}
<div class="readable"><h1>{c["emoji"]} {E(c["name"])}のレシピ</h1>{intro}</div>
<div class="grid">{"".join(recipe_card(r, p) for r in recs)}</div>
<section class="related" aria-labelledby="more-h"><h2 id="more-h">ほかのカテゴリー</h2><div class="cat-cards">{others}</div></section>
"""
        ld = {"@context": "https://schema.org", "@type": "ItemList", "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "url": canonical_for(f"recipes/{r['slug']}.html")} for i, r in enumerate(recs)]}
        layout(path, f'{c["name"]}のレシピ（2人分）', c["desc"], body, active="recipes", jsonld=ld)
        PAGES.append((path, "0.7"))


def build_recipes_index():
    path = "recipes/index.html"
    p = prefix(path)
    sections = "".join(
        f'<section data-cat-section aria-labelledby="c-{c["slug"]}"><div class="section-head">'
        f'<h2 id="c-{c["slug"]}">{c["emoji"]} {E(c["name"])}</h2>'
        f'<a href="{p}category/{c["slug"]}.html">一覧を見る →</a></div>'
        f'<div class="grid">{"".join(recipe_card(r, p) for r in RECIPES if r["category"] == c["slug"])}</div></section>'
        for c in CATEGORIES)
    body = f"""
{breadcrumbs([("ホーム", "index.html"), ("レシピ", None)], p)}
<div class="readable">
<h1>レシピ一覧</h1>
<p class="lead">ふたり分で作りやすい、毎日の家庭料理。どのレシピも「1人分・2人分・4人分」のボタンで分量を切り替えられます。</p>
<div class="search" role="search">
  <label for="recipe-search">料理名・材料でさがす</label>
  <input type="search" id="recipe-search" placeholder="例：豚肉、さば、大根" autocomplete="off" enterkeyhint="search">
</div>
<p class="no-results" id="no-results" hidden>該当するレシピが見つかりませんでした。別のことばでお試しください。</p>
</div>
{sections}
"""
    layout(path, "レシピ一覧", "肉のおかず、魚のおかず、ご飯・丼・麺、副菜・汁もの、ふたり鍋。2人分で作りやすい和食の家庭料理レシピの一覧です。", body, active="recipes")
    PAGES.append((path, "0.9"))


# ---------------------------------------------------------------------------
# Articles
# ---------------------------------------------------------------------------
def build_articles():
    for a in ARTICLES:
        path = f"articles/{a['slug']}.html"
        p = prefix(path)
        others = "".join(article_card(o, p) for o in ARTICLES if o["slug"] != a["slug"])
        body = f"""
<div class="page-layout">
<article class="prose">
{breadcrumbs([("ホーム", "index.html"), ("読みもの", "articles/index.html"), (a["title"], None)], p)}
<h1>{E(a["title"])}</h1>
<p class="meta">{E(S["operator"])}・更新日 {UPDATED_HUMAN}・約{a["minutes"]}分で読めます</p>
{a["body"].replace("{p}", p)}
</article>
{sidebar(p)}
</div>
<section class="related no-print" aria-labelledby="rel-h"><h2 id="rel-h">ほかの読みもの</h2><div class="grid">{others}</div></section>
"""
        ld = {"@context": "https://schema.org", "@type": "Article", "headline": a["title"], "description": a["desc"],
              "inLanguage": "ja", "datePublished": UPDATED_ISO, "dateModified": UPDATED_ISO, "author": org(),
              "publisher": org(), "mainEntityOfPage": canonical_for(path)}
        layout(path, a["title"], a["desc"], body, active="articles", og_type="article", jsonld=ld)
        PAGES.append((path, "0.7"))


def build_articles_index():
    path = "articles/index.html"
    p = prefix(path)
    body = f"""
{breadcrumbs([("ホーム", "index.html"), ("読みもの", None)], p)}
<div class="readable"><h1>読みもの</h1>
<p class="lead">ふたり分の料理のコツ、冷凍保存、計量の基本、食中毒の予防、だしのとり方など、毎日の台所で役立つ知恵をまとめました。</p></div>
<div class="grid">{"".join(article_card(a, p) for a in ARTICLES)}</div>
"""
    layout(path, "読みもの", "ふたり分の料理のコツ、冷凍保存の基本、計量の基本、食中毒予防、だしのとり方など、台所で役立つ読みもの。", body, active="articles")
    PAGES.append((path, "0.7"))


# ---------------------------------------------------------------------------
# Home
# ---------------------------------------------------------------------------
def build_home():
    path, p = "index.html", ""
    cats = "".join(cat_card(c, p) for c in CATEGORIES)
    popular = "".join(recipe_card(REC[s], p) for s in S["popular_recipes"])
    nabe = "".join(recipe_card(r, p) for r in RECIPES if r["category"] == "nabe")
    hp = hero_photo()
    hero_img = (f'<img src="{hp}" alt="ふたり分の和食の食卓" fetchpriority="high" decoding="async" width="1600" height="900">'
                if hp else "")
    body = f"""
<section class="hero-photo{'' if hp else ' hero-plain'}">
  <div class="tile">{hero_img}</div>
  <div class="hero-text">
    <p class="eyebrow">夫婦ふたり・ひとり暮らしに</p>
    <h1>ふたり分が、ちょうどいい。<br>毎日の和のおかず</h1>
    <p>作りすぎない、余らせない。定番の家庭料理を、2人分の分量でわかりやすくご紹介します。</p>
    <a class="btn btn-primary" href="recipes/index.html">レシピを見る</a>
  </div>
</section>
<div class="wave" aria-hidden="true"></div>

<section aria-labelledby="pop-h">
  <div class="section-head"><h2 id="pop-h">人気のレシピ</h2><a href="recipes/index.html">すべてのレシピ →</a></div>
  <div class="grid">{popular}</div>
</section>

<section aria-labelledby="cats-h">
  <h2 id="cats-h">今日は何をつくりますか？</h2>
  <div class="cat-cards">{cats}</div>
</section>

<section aria-labelledby="nabe-h">
  <div class="section-head"><h2 id="nabe-h">寒い日は、ふたり鍋</h2><a href="category/nabe.html">もっと見る →</a></div>
  <div class="grid">{nabe}</div>
</section>

<section aria-labelledby="guides-h">
  <div class="section-head"><h2 id="guides-h">台所の読みもの</h2><a href="articles/index.html">すべての読みもの →</a></div>
  <div class="grid">{"".join(article_card(a, p) for a in ARTICLES)}</div>
</section>

<section class="readable" aria-labelledby="welcome-h">
  <h2 id="welcome-h">「{E(S["site_name"])}」へようこそ</h2>
  <p>子どもが独立して、夫婦ふたりの食卓に。長年家族の人数分を作ってきたけれど、ふたり分となると、つい作りすぎてしまう……。「{E(S["site_name"])}」は、そんな方のためのレシピサイトです。</p>
  <p>生姜焼きや肉じゃが、さばの味噌煮、すき焼きなど、昔から親しまれてきた家庭料理を、2人分の分量でご紹介しています。分量はボタンひとつで1人分・4人分にも切り替えられます。</p>
  <p>文字が小さくて読みにくいときは、画面上の<strong>「文字サイズ」</strong>ボタンで大きくできます。レシピのページでは<strong>「画面を消さない」</strong>をオンにすると、調理中にスマートフォンの画面が暗くなりません。</p>
  <p><a href="about.html">運営者情報</a>／<a href="contact.html">お問い合わせ</a></p>
</section>
"""
    ld = {"@context": "https://schema.org", "@type": "WebSite", "name": S["site_name"], "url": S["site_url"] + "/",
          "inLanguage": "ja", "description": S["tagline"], "publisher": org()}
    layout(path, S["site_name"], "夫婦ふたり・シニア世代のための、2人分の和食レシピサイト。生姜焼き、肉じゃが、さばの味噌煮、ふたり鍋など、作りすぎない定番の家庭料理をわかりやすくご紹介します。",
           body, active="home", jsonld=ld, og_image=(S["site_url"] + "/" + hp) if hp else None)
    PAGES.append((path, "1.0"))


# ---------------------------------------------------------------------------
# 運営者情報・お問い合わせ・プライバシーポリシー・利用規約・免責事項
# ---------------------------------------------------------------------------
def info_page(path, title, desc, inner, active=None, updated=True, priority="0.4"):
    p = prefix(path)
    upd = f'<p class="meta">最終更新日：{UPDATED_HUMAN}</p>' if updated else ""
    body = f'<article class="prose">{breadcrumbs([("ホーム", "index.html"), (title, None)], p)}<h1>{E(title)}</h1>{upd}{inner}</article>'
    layout(path, title, desc, body, active=active)
    PAGES.append((path, priority))


def build_info_pages():
    name, url = E(S["site_name"]), E(S["site_url"])
    email = E(S["contact_email"])
    mail = f'<a href="mailto:{email}">{email}</a>'
    op = E(S["operator"])

    info_page("about.html", "運営者情報", f"{S['site_name']}の運営者情報とサイトの目的、レシピづくりの方針について。", f"""
<table class="info-table">
  <tr><th>サイト名</th><td>{name}</td></tr>
  <tr><th>URL</th><td>{url}</td></tr>
  <tr><th>運営者</th><td>{op}</td></tr>
  <tr><th>開設</th><td>{E(S["established"])}</td></tr>
  <tr><th>お問い合わせ</th><td><a href="contact.html">お問い合わせページ</a>をご覧ください</td></tr>
</table>
<h2>サイトについて</h2>
<p>「{name}」は、夫婦ふたりやひとり暮らしの方のための家庭料理レシピサイトです。子どもが独立したり、家族の人数が変わったりすると、長年の習慣でつい作りすぎてしまいがちです。ふたり分にちょうどよい分量で、昔ながらの定番料理をおいしく作っていただけるよう、わかりやすいレシピをお届けしています。</p>
<h2>レシピづくりの方針</h2>
<ul>
  <li><strong>2人分が基本：</strong>すべてのレシピは2人分を基本にしています（炊き込みご飯など一部を除く）。ボタンひとつで1人分・4人分にも切り替えられます。</li>
  <li><strong>手に入りやすい材料：</strong>近所のスーパーでそろう材料と、家庭にある調味料で作れるレシピです。</li>
  <li><strong>計量は正確に：</strong>大さじ1＝15ml、小さじ1＝5ml、1カップ＝200mlで表記しています。</li>
  <li><strong>食の安全を大切に：</strong>加熱や保存については、厚生労働省などの公的機関の情報を参考にしています。</li>
  <li><strong>読みやすさ：</strong>大きな文字と見やすい配色を心がけ、「文字サイズ」ボタンでさらに大きくできます。</li>
</ul>
<h2>広告について</h2>
<p>当サイトは、運営費をまかなうためにGoogle アドセンスなどの第三者配信の広告サービスを利用しています。広告主がレシピや記事の内容に影響を与えることはありません。詳しくは<a href="privacy-policy.html">プライバシーポリシー</a>をご覧ください。</p>
<h2>写真について</h2>
<p>当サイトの料理写真の一部には、フリー写真素材サイト「<a href="https://www.pakutaso.com/" rel="noopener">ぱくたそ</a>」の素材を利用規約に従って使用しています。</p>
""", active="about", updated=False, priority="0.5")

    info_page("contact.html", "お問い合わせ", f"{S['site_name']}へのお問い合わせ方法。レシピについてのご質問、内容の誤りのご指摘などはこちらから。", f"""
<p class="lead">レシピについてのご質問、ご感想、内容の誤りのご指摘など、お気軽にお寄せください。</p>
<div class="contact-card"><p><strong>メールでのお問い合わせ</strong></p><p class="email">{mail}</p><p>通常、3営業日以内にご返信いたします。内容によってはお時間をいただく場合や、お返事を差し上げられない場合がございます。あらかじめご了承ください。</p></div>
<h2>お問い合わせの例</h2>
<ul>
  <li><strong>レシピについて：</strong>作ったレシピ名と、どのような点でお困りかをお知らせください。</li>
  <li><strong>内容の誤り：</strong>分量や手順の誤りにお気づきの際は、ページ名と内容をお知らせください。</li>
  <li><strong>リクエスト：</strong>「こんな料理のふたり分レシピが知りたい」というご要望も歓迎です。</li>
  <li><strong>読みやすさ：</strong>文字の大きさや見づらい箇所など、サイトの使いにくい点もお寄せください。</li>
</ul>
<h2>個人情報の取り扱い</h2>
<p>お問い合わせでいただいたメールアドレスなどの個人情報は、ご返信のためにのみ利用し、ご本人の同意なく第三者に提供することはありません。詳しくは<a href="privacy-policy.html">プライバシーポリシー</a>をご覧ください。</p>
""", active="contact", updated=False, priority="0.5")

    ga_row = """
  <tr><td>Google LLC<br>（Google アナリティクス）</td><td>閲覧したページのURL、参照元、IPアドレス、ブラウザ・端末の種類、閲覧日時、Cookie ID などの識別子</td><td>サイトの利用状況の分析・改善</td><td><a href="https://policies.google.com/privacy?hl=ja" rel="noopener">プライバシーポリシー</a><br><a href="https://tools.google.com/dlpage/gaoptout?hl=ja" rel="noopener">オプトアウト</a></td></tr>""" if S["ga_id"] else ""
    ga_text = "" if S["ga_id"] else "<p>※ 現在、当サイトではアクセス解析ツールは使用していません。導入する場合は、本ポリシーを更新してお知らせします。</p>"

    info_page("privacy-policy.html", "プライバシーポリシー", f"{S['site_name']}における個人情報の取り扱い、Cookie、広告配信、外部送信（電気通信事業法）についての方針。", f"""
<p>{name}（以下「当サイト」）は、利用者の個人情報を適切に取り扱うことが重要であると考え、個人情報の保護に関する法律（個人情報保護法）その他の関係法令を遵守し、以下のとおりプライバシーポリシーを定めます。</p>

<h2>1. 取得する情報</h2>
<p>当サイトは、会員登録などを行わずにどなたでもご利用いただけます。当サイトが取得する情報は次のとおりです。</p>
<ul>
  <li><strong>お問い合わせの際にご提供いただく情報：</strong>メールアドレス、お名前（任意）、お問い合わせ内容</li>
  <li><strong>自動的に取得される情報：</strong>IPアドレス、ブラウザ・端末の種類、閲覧したページ、閲覧日時などのアクセス情報、Cookie などの識別子</li>
</ul>

<h2>2. 利用目的</h2>
<ul>
  <li>お問い合わせへの回答のため</li>
  <li>当サイトの運営、維持、改善のため</li>
  <li>広告の配信および効果測定のため</li>
  <li>不正アクセスなどの防止、セキュリティ確保のため</li>
  <li>法令に基づく対応のため</li>
</ul>

<h2>3. 第三者提供</h2>
<p>当サイトは、法令に基づく場合を除き、ご本人の同意なく個人情報を第三者に提供することはありません。</p>

<h2>4. 端末に保存される設定</h2>
<p>「文字サイズ」の設定はお使いのブラウザのローカルストレージに、レシピでチェックした材料はセッションストレージに保存されます。これらの情報はお使いの端末内にのみ保存され、当サイトに送信されることはありません。「画面を消さない」機能はブラウザの画面スリープ防止機能（Screen Wake Lock）を利用しており、情報を取得することはありません。</p>

<h2>5. Cookie（クッキー）について</h2>
<p>Cookie とは、ウェブサイトを閲覧した際にブラウザに保存される小さなテキストファイルです。当サイトおよび広告配信事業者は、Cookie などの技術を利用することがあります。Cookie はブラウザの設定で無効にしたり削除したりできます。iPhone・iPad の場合は「設定」→「アプリ」→「Safari」（古いバージョンでは「設定」→「Safari」）から管理できます。</p>

<h2>6. 広告の配信について（Google アドセンス）</h2>
<p>当サイトは、第三者配信の広告サービス「Google アドセンス」を利用しています（または利用を予定しています）。</p>
<ul>
  <li>Google などの第三者配信事業者は、Cookie を使用して、利用者が当サイトや他のウェブサイトに過去にアクセスした際の情報に基づいて広告を配信します。</li>
  <li>Google が広告 Cookie を使用することにより、利用者が当サイトや他のサイトにアクセスした際の情報に基づいて、Google やそのパートナーが適切な広告を表示できます。</li>
  <li>利用者は、<a href="https://myadcenter.google.com/?hl=ja" rel="noopener">Google マイ アドセンター</a>（広告設定）でパーソナライズ広告を無効にできます。</li>
  <li>また、<a href="https://www.aboutads.info/choices/" rel="noopener">www.aboutads.info</a> にアクセスすれば、パーソナライズ広告に使われる第三者配信事業者の Cookie を無効にできます。</li>
  <li>詳しくは「<a href="https://policies.google.com/technologies/partner-sites?hl=ja" rel="noopener">Google のサービスを使用するサイトやアプリから収集した情報の Google による使用</a>」をご覧ください。</li>
</ul>

<h2>7. 外部送信について（電気通信事業法第27条の12に基づく公表）</h2>
<p>当サイトでは、利用者の端末から以下の事業者に情報が送信されます。送信される情報、送信先、利用目的は次のとおりです。</p>
<div class="table-wrap"><table class="info-table">
  <tr><th>送信先</th><th>送信される情報</th><th>利用目的</th><th>詳細・オプトアウト</th></tr>
  <tr><td>Google LLC<br>（Google アドセンス）</td><td>閲覧したページのURL、IPアドレス、ブラウザ・端末の種類、閲覧日時、Cookie ID・広告識別子などの識別子</td><td>広告の配信、広告の表示回数・クリックの測定、不正クリックの防止</td><td><a href="https://policies.google.com/privacy?hl=ja" rel="noopener">プライバシーポリシー</a><br><a href="https://myadcenter.google.com/?hl=ja" rel="noopener">広告設定（オプトアウト）</a></td></tr>{ga_row}
  <tr><td>Microsoft Corporation<br>（Azure：サイトの配信）</td><td>IPアドレス、ブラウザ・端末の種類、リクエストされたURL、日時</td><td>ウェブサイトの配信、セキュリティの確保、障害対応</td><td><a href="https://privacy.microsoft.com/ja-jp/privacystatement" rel="noopener">プライバシーに関する声明</a></td></tr>
</table></div>
{ga_text}

<h2>8. 安全管理</h2>
<p>当サイトは、通信の暗号化（HTTPS）など、個人情報の漏えい、滅失、毀損を防ぐための合理的な安全管理措置を講じます。</p>

<h2>9. 開示・訂正・利用停止などのご請求</h2>
<p>ご本人から保有個人データの開示、訂正、追加、削除、利用停止などのご請求があった場合は、ご本人であることを確認したうえで、法令に従い遅滞なく対応いたします。ご請求は{mail}までご連絡ください。</p>

<h2>10. 未成年の方の利用</h2>
<p>当サイトは一般の成人の方を対象としています。</p>

<h2>11. 本ポリシーの変更</h2>
<p>当サイトは、法令の改正などに応じて、本ポリシーを予告なく変更することがあります。変更後のポリシーは、本ページに掲載した時点から効力を生じます。</p>

<h2>12. お問い合わせ窓口</h2>
<p>運営者：{op}<br>連絡先：{mail}</p>
""", priority="0.3")

    info_page("terms-of-use.html", "利用規約", f"{S['site_name']}の利用規約。", f"""
<p>この利用規約（以下「本規約」）は、{name}（以下「当サイト」）の利用条件を定めるものです。当サイトをご利用いただいた時点で、本規約に同意いただいたものとみなします。</p>
<h2>第1条（利用について）</h2>
<p>当サイトのレシピ、記事などのコンテンツは、個人的・非商用の目的でご利用いただけます。</p>
<h2>第2条（著作権）</h2>
<p>当サイトに掲載している文章、レシピの手順、デザインなどの著作権は、当サイトまたは正当な権利者に帰属します。ご家庭でのご利用のためにレシピを印刷すること、当サイトのページへのリンクを共有することは自由です。ただし、文章や写真を許可なく他のウェブサイトや出版物などに転載することはお断りします。</p>
<h2>第3条（禁止事項）</h2>
<ul>
  <li>法令または公序良俗に反する行為</li>
  <li>当サイトのコンテンツを大量に複製・取得する行為</li>
  <li>当サイトの運営やセキュリティを妨げる行為</li>
  <li>自動化された手段により広告をクリックするなど、広告の表示や効果を不正に操作する行為</li>
  <li>その他、当サイトが不適切と判断する行為</li>
</ul>
<h2>第4条（広告・外部リンク）</h2>
<p>当サイトには第三者による広告や外部サイトへのリンクが含まれます。広告主や外部サイトとの取引、外部サイトの内容について、当サイトは責任を負いません。</p>
<h2>第5条（免責）</h2>
<p>当サイトのご利用によって生じた損害について、当サイトは一切の責任を負いません。詳しくは<a href="disclaimer.html">免責事項</a>をご覧ください。</p>
<h2>第6条（本規約の変更）</h2>
<p>当サイトは、必要に応じて本規約を変更することがあります。変更後の規約は、本ページに掲載した時点から効力を生じます。</p>
<h2>第7条（準拠法・管轄）</h2>
<p>本規約の解釈には日本法を準拠法とします。</p>
""", priority="0.3")

    info_page("disclaimer.html", "免責事項", f"{S['site_name']}のレシピ・記事についての免責事項（アレルギー、加熱、食品衛生など）。", f"""
<h2>掲載内容について</h2>
<p>当サイトに掲載しているレシピや記事は、一般的な情報の提供を目的としています。内容には十分注意を払っていますが、その正確性や完全性を保証するものではありません。調理時間や加熱時間は目安です。お使いの調理器具や食材の状態によって異なりますので、様子を見ながら調整してください。</p>
<h2>加熱と食品衛生について</h2>
<p>肉や魚、卵を使う料理は、中心部までしっかり加熱してください。厚生労働省では、食中毒予防のため、食品の中心部を75℃で1分以上加熱することを目安としています。半熟卵などの加熱が不十分な料理は、体調のすぐれない方やご高齢の方は控えるなど、ご自身の判断でお召し上がりください。詳しくは<a href="https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/kenkou_iryou/shokuhin/syokuchu/index.html" rel="noopener">厚生労働省「食中毒」</a>のページもご覧ください。</p>
<h2>アレルギーについて</h2>
<p>当サイトのレシピには、卵、乳、小麦、えび、かに、そば、落花生（ピーナッツ）、くるみなどのアレルギー物質を含む食材が使われていることがあります。食物アレルギーのある方は、材料の原材料表示を必ずご確認ください。</p>
<h2>健康・栄養について</h2>
<p>当サイトの情報は、医療や栄養指導に代わるものではありません。減塩や糖質制限など、持病のために食事の制限がある方や、服用中のお薬と食品の飲み合わせが気になる方は、医師や管理栄養士にご相談ください。</p>
<h2>広告について</h2>
<p>当サイトに表示される広告は、Google アドセンスなどの広告配信事業者によって配信されています。広告の商品やサービスについて、当サイトは責任を負いません。</p>
<h2>外部リンクについて</h2>
<p>当サイトからリンクしている外部サイトの内容について、当サイトは責任を負いません。</p>
<h2>損害について</h2>
<p>当サイトの情報を利用したことにより生じたいかなる損害についても、当サイトは責任を負いかねます。あらかじめご了承ください。</p>
""", priority="0.3")


def build_404():
    path = "404.html"
    cats = "".join(f'<a class="cat-link" href="/category/{c["slug"]}.html"><span class="em" aria-hidden="true">{c["emoji"]}</span>{E(c["name"])}</a>' for c in CATEGORIES)
    body = f"""
<div class="readable"><h1>ページが見つかりません</h1>
<p class="lead">お探しのページは移動したか、アドレスが間違っている可能性があります。</p>
<p><a class="btn btn-primary" href="/recipes/index.html">レシピ一覧を見る</a></p>
<h2>カテゴリー</h2></div>
<div class="cat-grid">{cats}</div>
"""
    layout(path, "ページが見つかりません", "お探しのページは見つかりませんでした。", body, noindex=True)
    f = os.path.join(OUT, path)
    txt = open(f, encoding="utf-8").read()
    txt = re.sub(r'(href|src|srcset)="(?!/|https?:|mailto:|#)([^"]+)"', r'\1="/\2"', txt)
    open(f, "w", encoding="utf-8").write(txt)


def build_support_files():
    urls = "".join(f"  <url><loc>{E(canonical_for(pth))}</loc><lastmod>{UPDATED_ISO}</lastmod><priority>{pri}</priority></url>\n" for pth, pri in PAGES)
    with open(os.path.join(OUT, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write(f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{urls}</urlset>\n')
    with open(os.path.join(OUT, "robots.txt"), "w", encoding="utf-8") as f:
        f.write(f"User-agent: *\nAllow: /\nDisallow: /404.html\n\nSitemap: {S['site_url']}/sitemap.xml\n")
    pub = S["adsense_client"].replace("ca-", "") if S["adsense_client"] else "pub-0000000000000000"
    note = "" if S["adsense_client"] else "# Replace pub-0000000000000000 with your AdSense publisher ID once approved.\n"
    with open(os.path.join(OUT, "ads.txt"), "w", encoding="utf-8") as f:
        f.write(f"{note}google.com, {pub}, DIRECT, f08c47fec0942fa0\n")
    manifest = {"name": S["site_name"], "short_name": S["site_name"], "lang": "ja", "start_url": "/", "display": "browser",
                "background_color": "#faf6ee", "theme_color": "#2c4a6e",
                "icons": [{"src": "/assets/img/icon-192.png", "sizes": "192x192", "type": "image/png"},
                          {"src": "/assets/img/icon-512.png", "sizes": "512x512", "type": "image/png"}]}
    with open(os.path.join(OUT, "site.webmanifest"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)


def main():
    build_home()
    build_recipes_index()
    build_categories()
    build_recipes()
    build_articles_index()
    build_articles()
    build_info_pages()
    build_404()
    build_support_files()
    photos = sum(1 for r in RECIPES if local_photo(r["slug"]))
    print(f"Built {len(PAGES) + 1} pages into {OUT}. Recipe photos found: {photos} of {len(RECIPES)}.")


if __name__ == "__main__":
    main()
