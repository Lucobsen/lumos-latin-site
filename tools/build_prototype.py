"""Writes the static Lumos Latin prototype into ../prototype.

The output is plain HTML, CSS and JS. Every text, class, price, event and studio comes from
the JSON files in ../content; this script holds the layout. Run: python tools/build_prototype.py
Add --switches to show the small switches under the title again, for comparing looks.
Add --today YYYY-MM-DD to build as if it were that day (dated items and notices follow it).
"""
import datetime
import urllib.parse
import json
import os
import shutil
import sys
from html import escape as esc

from content_io import check, load, load_dir, where

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "prototype")
OG_IMAGE = "/assets/og-image.jpg"  # 1200x630, cut from the school's own photo photos/hero-dance.jpg by og_image()
SITEMAP = []  # (path, {hreflang: path}) for every page written, filled by page()


def _today():
    if "--today" not in sys.argv:
        return datetime.date.today()
    try:
        return datetime.date.fromisoformat(sys.argv[sys.argv.index("--today") + 1])
    except (IndexError, ValueError):
        raise SystemExit("use --today YYYY-MM-DD")


TODAY = _today()


def day(v):
    """An ISO date from a content file, or None when the field is empty."""
    return datetime.date.fromisoformat(v) if v else None


def shown(item):
    """True while TODAY is inside the item's show_from / hide_after window (both days included)."""
    a, b = day(item.get("show_from")), day(item.get("hide_after"))
    return (a is None or a <= TODAY) and (b is None or TODAY <= b)


def in_lang(v, lang):
    """Picks one language out of content: every {"en": ..., "nl": ...} object becomes its lang value."""
    if isinstance(v, dict):
        if set(v) == {"en", "nl"}:
            return v[lang]
        return {k: in_lang(x, lang) for k, x in v.items()}
    if isinstance(v, list):
        return [in_lang(x, lang) for x in v]
    return v


def _pick(d, keys):
    """The entries of d in the order of keys (the order data.js and the pages need)."""
    return {k: d[k] for k in keys if k in d}


_PAGES = {}


def page_data(name):
    """content/pages/<name>.json, checked once, both languages."""
    if name not in _PAGES:
        w = where("pages", name + ".json")
        data = check(load("pages", name + ".json"), w)
        for key in ("notices", "night_extras", "dancer_extras"):
            for i, x in enumerate(data.get(key, [])):
                check(x, f"{w} {key}[{i}]", dates=("show_from", "hide_after"))
        _PAGES[name] = data
    return _PAGES[name]


def P(name, lang):
    """The texts of content/pages/<name>.json in one language."""
    return in_lang(page_data(name), lang)


S = check(load("settings.json"), where("settings.json"))
for _k in ("course_start", "course_end"):
    check(S[_k], f"{where('settings.json')} {_k}", required=tuple(S[_k]))
PRICES = check(load("prices.json"), where("prices.json"))
REVIEWS = check(load("reviews.json"), where("reviews.json"))["reviews"]
FAQ = check(load("faq.json"), where("faq.json"))["questions"]


def load_list(name, **rules):
    """Every file of a list folder, checked (see content_io.check)."""
    return [check(x, where(name, x["slug"] + ".json"), **rules) for x in load_dir(name)]
SITE = S["site_url"]
# The copy on vercel.app is the hidden one: kept out of Google three ways (meta robots, robots.txt,
# X-Robots-Tag header). With the real address in site_url the build leaves all three out by itself,
# so going live is only that one setting.
HIDDEN = "vercel.app" in SITE
ROBOTS_META = '<meta name="robots" content="noindex, nofollow">\n' if HIDDEN else ""
BOOK = S["book_fallback"]  # a page key ("schedule") or a full address; link_href makes it per language
BUY = S["buy_link"]
# Try-out switch: on, the try-out buttons go to each class's Bueno try-out; off (no try-out
# weeks right now), every booking button goes to the regular schedule and the try-out dates leave the pages.
TRYOUTS = bool(S.get("tryouts_on", True))
PHONE = S["phone"]
TEL = S["tel_link"]
WA = S["whatsapp_link"]
EMAIL = S["email"]
IG = S["instagram"]
TT = S["tiktok"]
FB = S["facebook"]
FOUNDED = S["founded_year"]

# The look: each value goes on the <html> tag of every page; style.css holds the CSS for every option.
HL_SHAPE = S["hl_shape"]    # A, B or C
HL_COLOR = S["hl_color"]    # Pink, Purple, Lilac, Rose, Orchid or Moving
BTN_COLOR = S["btn_color"]  # Pink or Purple
Q_BG = S["q_bg"]            # White or Yellow
GTM_ID = S["gtm_id"]        # empty drops the Tag Manager snippet
GTM_HEAD = ("<!-- Google Tag Manager -->\n<script>(function(w,d,s,l,i){w[l]=w[l]||[];w[l].push({'gtm.start':new Date().getTime(),event:'gtm.js'});"
            "var f=d.getElementsByTagName(s)[0],j=d.createElement(s),dl=l!='dataLayer'?'&l='+l:'';j.async=true;"
            "j.src='https://www.googletagmanager.com/gtm.js?id='+i+dl;f.parentNode.insertBefore(j,f);})(window,document,'script','dataLayer','"
            + GTM_ID + "');</script>\n<!-- End Google Tag Manager -->") if GTM_ID else ""
GTM_BODY = ('<noscript><iframe src="https://www.googletagmanager.com/ns.html?id=' + GTM_ID
            + '" height="0" width="0" style="display:none;visibility:hidden"></iframe></noscript>\n') if GTM_ID else ""
SHOW_SWITCHES = "--switches" in sys.argv  # True shows the small switches under the title, for picking

# ---------------------------------------------------------------- data
WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def _class(c):
    d = day(c["tryout_date"])
    return dict(id=c["id"], day=c["day"], time=c["time"], end=c["end"], dance=c["dance"], level=c["level"],
                studio=c["studio"], teachers=c["teachers"], try_=(WEEKDAYS[d.weekday()], d.day, d.month, c["tryout_time"]))


# weekly classes in schedule order: day, start time, level
_CLASS_FILES = sorted(load_list("classes", required=("tryout_date",)), key=lambda c: (WEEKDAYS.index(c["day"]), c["time"], c["level"]))
CLASSES = [_class(c) for c in _CLASS_FILES]
TRY_LINK = {c["id"]: c["bueno_tryout_id"] for c in _CLASS_FILES if c.get("bueno_tryout_id")}  # Bueno calendarEntryId


def book_url(c, lang):
    n = TRY_LINK.get(c["id"]) if TRYOUTS else None
    return f"https://www.bueno.nu/webshop/school/764/schedule-detail/{n}" if n else link_href(lang, BOOK)


COURSE_START = {k: (day(v).day, day(v).month) for k, v in S["course_start"].items()}
COURSE_END = {k: (day(v).day, day(v).month) for k, v in S["course_end"].items()}


def try_key(c):
    return (c["try_"][2], c["try_"][1], c["try_"][3])


def try_end(c):
    h, m = map(int, c["try_"][3].split(":"))
    m += 60 if c["dance"] == "reggaeton" else 55
    return f"{h + m // 60:02d}:{m % 60:02d}"


def try_label(lang, c):
    d, n, m, t = c["try_"]
    return f"{T[lang]['days'][d]} {n} {MONTHS[lang][m]}, {t}–{try_end(c)}"


def course_label(lang, c):
    t = T[lang]
    day_long = t["days_long"][c["day"]]
    if c["dance"] == "reggaeton":  # drop-in: no course dates
        return f"{t['every']} {day_long}, {c['time']}–{c['end']}"
    (a, am), (b, bm) = COURSE_START[c["day"]], COURSE_END[c["day"]]
    return f"{day_long} {c['time']}–{c['end']}, {a} {MONTHS[lang][am]} {t['date_to']} {b} {MONTHS[lang][bm]}"


STUDIOS = {}  # by key, in pin order; "area" is the Dutch name, "area_en" the English one
_STUDIO_FILES = sorted(load_list("studios"), key=lambda s: s["pin"])
for _s in _STUDIO_FILES:
    STUDIOS[_s["key"]] = dict(name=_s["name"], area=_s["area"]["nl"], area_en=_s["area"]["en"], addr=_s["address"],
                              pin=_s["pin"], dances=_s["dances"], days=_s["days"], beginners_only=_s["beginners_only"],
                              workshops_only=_s["workshops_only"], locs=_s["bueno_location_ids"])
MAPS_LINK = {s["key"]: s["maps_link"] for s in _STUDIO_FILES}
# The map embed is by coordinates (not the business), so it shows only Google's pin: no place card, no key needed.
MAPS_LATLON = {s["key"]: s["map_coordinates"] for s in _STUDIO_FILES}


def studio_map(lang, k):
    s, p = STUDIOS[k], P("studios", lang)
    title = f"{p['map_title']}: {s['name']}, {s['addr']}"
    src = f"https://www.google.com/maps?q={MAPS_LATLON[k]}&z=16&hl={lang}&output=embed"
    return (f'<div class="studio-map"><div class="sm-frame"><iframe src="{src}" title="{title}" loading="lazy" '
            f'referrerpolicy="no-referrer-when-downgrade" allowfullscreen></iframe></div>'
            f'<a class="sm-cap" href="{MAPS_LINK[k]}" target="_blank" rel="noopener">{p["map_caption"]}</a></div>')


def area(lang, s):
    return s.get("area_" + lang, s["area"])


LEVELS = {1: "Beginners", 2: "Improvers", 3: "Intermediate"}

SLUGS = {
    "nl": dict(home="", salsa="salsa", bachata="bachata", reggaeton="reggaeton", schedule="rooster",
               prices="prijzen", studios="studios", events="evenementen", teachers="docenten", contact="contact",
               privacy="privacy"),
    "en": dict(home="", salsa="salsa", bachata="bachata", reggaeton="reggaeton", schedule="schedule",
               prices="prices", studios="studios", events="events", teachers="teachers", contact="contact",
               privacy="privacy"),
}
# the current lumoslatin.nl pages and the new page each one redirects to at launch
OLD_URLS = {"salsa": "salsa", "bachata": "bachata", "reggaeton": "reggaeton", "schedule": "schedule", "prices": "prices",
            "locations": "studios", "events": "events", "contact": "contact", "privacy-policy": "privacy",
            # the old site forwarded /courses and /workshops itself and had a blog; the new site has no blog
            "courses": "prices", "workshops": "events", "blog": "home"}
ANSWERS = ["beginner-salsa", "beginner-bachata", "reggaeton", "improver-salsa", "improver-bachata",
           "dancer-salsa", "dancer-bachata", "between-salsa", "between-bachata"]


def base():
    return ""


LIST_PAGES = {"schedule": "#bueno-schedule", "studios": "#classes", "salsa": "#classes", "bachata": "#classes", "reggaeton": "#classes"}


def cta_href(lang, page):
    """Book a try-out: the class list on this page if it has one, else the chooser on the home page."""
    if not TRYOUTS:  # no try-out weeks: the button opens the schedule (its own frame on the schedule page)
        return "#bueno-schedule" if page == "schedule" else url(lang, "schedule")
    return LIST_PAGES.get(page) or home_url(lang, chooser())


def chooser():
    """Where 'Book a try-out' lands: the question flow at the top of the home page."""
    return "#start"


def home_url(lang, frag=""):
    return f"{base()}/{lang}/{frag}"


def url(lang, page, query=""):
    s = SLUGS[lang][page]
    return f"{base()}/{lang}/" + (s + "/" if s else "") + query


def link_href(lang, v):
    """A link from a content file: a full address or "#anchor" stays as it is, "buy_link" is the shop,
    and a page key with an optional query or anchor ("schedule?filter=beginners", "home#start") becomes that page."""
    if v == "buy_link":  # the shop; when that is our own prices page, the one in the visitor's language
        return url(lang, "prices") if BUY.rstrip("/").endswith("lumoslatin.nl/prices") else BUY
    if v == "tryout_link":  # the try-out schedule in try-out weeks, else the regular schedule
        return url(lang, "schedule", "?filter=tryouts" if TRYOUTS else "")
    if not v or v.startswith(("http", "#", "/", "mailto:", "tel:")):
        return v
    cut = min([v.index(ch) for ch in "?#" if ch in v] or [len(v)])
    return url(lang, v[:cut], v[cut:])


def _labels(lang):
    sh, home = P("shared", lang), P("home", lang)
    return dict(
        nav_dances=sh["nav_dances"], nav_schedule=sh["nav_schedule"], nav_prices=sh["nav_prices"], nav_events=sh["nav_events"],
        nav_studios=sh["nav_studios"], nav_teachers=sh["nav_teachers"], cta=sh["cta"] if TRYOUTS else sh["cta_off"], menu=sh["menu"],
        hero_sub=home["hero_sub"], hero_sub2=home["hero_sub2"],
        days=_pick(sh["days"], WEEKDAYS), days_long=_pick(sh["days_long"], WEEKDAYS), and_=sh["and"], tbc=sh["teacher_tbc"], no_levels=sh["no_levels"],
        foot_about=sh["footer_about"], foot_contact=sh["footer_contact"], foot_dances=sh["footer_dances"],
        foot_classes=sh["footer_classes"], foot_school=sh["footer_school"], foot_follow=sh["footer_follow"],
        privacy=sh["privacy_label"], studios_word=sh["nav_studios"], contact_word=sh["nav_contact"], rights=sh["rights"],
        try_word=sh["tryout_label"], then_course=sh["then_course"], then_drop=sh["then_drop_in"], per_class=sh["per_class"],
        every=sh["every"], date_to=sh["date_to"],
    )


T = {lang: _labels(lang) for lang in ("nl", "en")}


def teachers(lang, c):
    t = c["teachers"]
    if not t:
        return T[lang]["tbc"]
    return f" {T[lang]['and_']} ".join(t)


def class_name(c):
    if c["dance"] == "reggaeton":
        return "Reggaeton drop-in"
    return f"{c['dance'].capitalize()} {c['level']}"


def level_name(lang, c):
    return LEVELS.get(c["level"], T[lang]["no_levels"])


# ---------------------------------------------------------------- finder and answer pages (also written to data.js)
def _flow(lang):
    f = P("finder", lang)
    dances = ("salsa", "bachata")
    return dict(
        q1=f["q1"], q1_opts=_pick(f["q1_opts"], ("never", "few", "regular")),
        q1_subs=_pick(f["q1_subs"], ("never", "few", "regular")),
        q1_reggaeton=(f["q1_reggaeton"]["title"], f["q1_reggaeton"]["sub"]),  # the Reggaeton option skips the questions
        q2=f["q2"], q2_opts=_pick(f["q2_opts"], ("salsa", "bachata", "reggaeton", "unsure")),
        q2_subs=_pick(f["q2_subs"], ("salsa", "bachata", "reggaeton", "unsure")),
        step=f["step"], one_more=f["one_more"], back=f["back"],
        check=_pick(f["check"], dances), check_opts=_pick(f["check_opts"], ("no", "yes", "unsure")),
        compare_title=f["compare_title"], compare=_pick(f["compare"], dances), compare_q=f["compare_q"],
        restart=f["restart"], restart_top=f["restart_top"], welcome=f["welcome"],
        your_start=f["your_start"], your_next=f["your_next"], your_classes=f["your_classes"],
    )


FLOW = {lang: _flow(lang) for lang in ("nl", "en")}


def _answers(lang):
    out = {}
    for slug in ANSWERS:
        a = P("start", lang)["answers"][slug.replace("-", "_")]
        out[slug] = dict(eyebrow=a["eyebrow"], title=a["title"], intro=a["intro"], classes=a["classes"], ticks=a["ticks"],
                         cta=a["cta"] if TRYOUTS else P("shared", lang)["cta_off"],
                         second=(a["second_label"], a["second_link"]), extras=a["extras"])
    return out


ANSWER_COPY = {lang: _answers(lang) for lang in ("nl", "en")}
_START = page_data("start")
YOU_IF = {lang: {(k.rsplit("_", 1)[0], int(k.rsplit("_", 1)[1])): v[lang] for k, v in _START["you_if"].items()} for lang in ("nl", "en")}
# Answer extras ("More info"): an item stays while TODAY is inside its show_from / hide_after window.
NIGHT_EXTRA = _START["night_extras"]
DANCER_EXTRAS = _START["dancer_extras"]


def dated_extras(items, lang):
    return [(x["heading"][lang], x["text"][lang]) for x in items if shown(x)]


TIP_STARTS = ("Twijfel", "Ooit lessen", "Not sure", "Torn between", "Had classes")


def split_tip(ticks):
    """The 'try two levels back to back' line is shown as its own box, above the classes."""
    tips = [x for x in ticks if x.startswith(TIP_STARTS)]
    return (tips[0] if tips else ""), [x for x in ticks if not x.startswith(TIP_STARTS)]


import re as _re
_DANCE_WORD = _re.compile(r"\b(salsa|bachata|reggaeton)")


def cap(v):
    """Salsa, Bachata and Reggaeton always with a capital letter in running text
    (also at the start of Dutch compounds: Salsales, Bachataniveau). Works on strings, lists, tuples and dict values."""
    if isinstance(v, str):
        return _DANCE_WORD.sub(lambda m: m.group(1).capitalize(), v)
    if isinstance(v, list):
        return [cap(x) for x in v]
    if isinstance(v, tuple):
        return tuple(cap(x) for x in v)
    if isinstance(v, dict):
        return {k: cap(x) for k, x in v.items()}
    return v


_TAG_SPLIT = _re.compile(r"(<script\b.*?</script>|<style\b.*?</style>|<[^>]+>)", _re.S | _re.I)


def cap_html(html):
    """cap() on the visible text of a page only: tags, attributes (links, ids, classes) and scripts stay as they are."""
    return "".join(p if p.startswith("<") else cap(p) for p in _TAG_SPLIT.split(html))


def _class_when(c):
    """What the answer tiles show for a class: its try-out day and time while try-outs are on, else the weekly
    class ("Every Monday", 20:10-21:10), sorted by weekday."""
    if TRYOUTS:
        return dict(book=book_url(c, "en") if TRY_LINK.get(c["id"]) else "",
                    try_day_nl=f"{T['nl']['days'][c['try_'][0]]} {c['try_'][1]} {MONTHS['nl'][c['try_'][2]]}",
                    try_day_en=f"{T['en']['days'][c['try_'][0]]} {c['try_'][1]} {MONTHS['en'][c['try_'][2]]}",
                    try_time=f"{c['try_'][3]}–{try_end(c)}")
    return dict(book="", try_=[c["day"], WEEKDAYS.index(c["day"]) + 1, 0, c["time"]],
                try_day_nl=cap(f"{T['nl']['every']} {T['nl']['days_long'][c['day']]}"),
                try_day_en=cap(f"{T['en']['every']} {T['en']['days_long'][c['day']]}"),
                try_time=f"{c['time']}–{c['end']}")


def write_data_js():
    data = {"areas": {k: v["area"] for k, v in STUDIOS.items()}, "areas_en": {k: area("en", v) for k, v in STUDIOS.items()}, "addrs": {k: v["addr"] for k, v in STUDIOS.items()}, "classes": [dict(c, try_nl=try_label("nl", c), try_en=try_label("en", c), course_nl=course_label("nl", c), course_en=course_label("en", c),
                             **_class_when(c),
                             yi_nl=cap(YOU_IF["nl"].get((c["dance"], c["level"]), "")), yi_en=cap(YOU_IF["en"].get((c["dance"], c["level"]), ""))) for c in CLASSES], "studios": {k: v["name"] for k, v in STUDIOS.items()}, "levels": LEVELS, "book": link_href("en", BOOK), "tryouts": TRYOUTS}
    for lang in ("nl", "en"):
        answers = {}
        for slug, a in ANSWER_COPY[lang].items():
            label, link = a["second"]
            tip, ticks = split_tip(a["ticks"])
            answers[slug] = cap(dict(eyebrow=FLOW[lang][a["eyebrow"]], title=a["title"], intro=a["intro"],
                                 ticks=ticks, tip=tip, extras=dated_extras(DANCER_EXTRAS if a["extras"] == "dancer" else NIGHT_EXTRA, lang),
                                 cta=a["cta"], second=dict(label=label)))
            answers[slug].update(classes=a["classes"])
            answers[slug]["second"]["href"] = link_href(lang, link)
        t = T[lang]
        data[lang] = dict(flow=cap(FLOW[lang]), answers=answers, days=t["days"], and_=t["and_"], tbc=t["tbc"],
                          no_levels=t["no_levels"], try_word=t["try_word"] if TRYOUTS else "", then_course=t["then_course"], then_drop=t["then_drop"],
                          pick_note="", per_class=t["per_class"], book_row=t["cta"], between_link=P("start", lang)["between_link"],
                          book=link_href(lang, BOOK),
                          urls=dict(home=f"/{lang}/", start=f"/{lang}/start/", skip=f"/{lang}/#overview"))
    with open(os.path.join(ROOT, "assets", "data.js"), "w", encoding="utf-8") as f:
        f.write("/* Written by tools/build_prototype.py */\nwindow.LUMOS = " + json.dumps(data, ensure_ascii=False, indent=1) + ";\n")


# ---------------------------------------------------------------- events and news cards
def _filled(v):
    """A text that may be empty: None when there is nothing in either language."""
    if isinstance(v, dict):
        return v if v.get("en") or v.get("nl") else None
    return v or None


def _event(e):
    return dict(kind=e.get("kind", ""), slug=e["slug"], date=day(e["date"]), title=e.get("title", ""), img=e.get("image", ""),
                time=e.get("time", ""), place=e.get("place", ""), link=e.get("link", ""),
                btn=_filled(e.get("button")), text=e.get("text", ""))


def _news(n):
    return dict(when=n.get("when", ""), title=n.get("title", ""), img=n.get("image", ""), text=n.get("text", ""),
                btn=_filled(n.get("button")), link=n.get("link", ""), big=bool(n.get("big")),
                sticker=_filled(n.get("sticker")), badge=_filled(n.get("badge")))


DATED = dict(required=("date",), dates=("show_from", "hide_after"))
# Events and news cards outside their show_from / hide_after window are left out of the whole build.
EVENT_ITEMS = [_event(e) for e in sorted(load_list("events", plain=("title", "time", "place", "button"), **DATED),
                                         key=lambda e: (e["date"], e["slug"])) if shown(e)]
# Home page news cards, in the order of their "date" field.
NEWS_ITEMS = [_news(n) for n in sorted(load_list("news", plain=("title", "sticker", "badge", "button"), **DATED),
                                       key=lambda n: (n["date"], n["slug"])) if shown(n)]
WEEKDAY = dict(nl=["maandag", "dinsdag", "woensdag", "donderdag", "vrijdag", "zaterdag", "zondag"],
               en=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"])
MONTH_NAME = dict(nl=["januari", "februari", "maart", "april", "mei", "juni", "juli", "augustus", "september", "oktober", "november", "december"],
                  en=["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"])
MONTH_SHORT = dict(nl=["jan", "feb", "mrt", "apr", "mei", "jun", "jul", "aug", "sep", "okt", "nov", "dec"],
                   en=["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
MONTHS = {lang: {i + 1: m for i, m in enumerate(v)} for lang, v in MONTH_SHORT.items()}  # month number: short name


def tr(v, lang):
    return v[lang] if isinstance(v, dict) else v


def paras(v, lang):
    """A text with blank lines (or line breaks) typed in the editing screen becomes several paragraphs."""
    parts = [p.strip() for p in tr(v, lang).replace("\r", "").split("\n") if p.strip()]
    return "".join(f"<p>{p}</p>" for p in parts)


def long_date(lang, d):
    return f"{WEEKDAY[lang][d.weekday()]} {d.day} {MONTH_NAME[lang][d.month - 1]}"


def upcoming_events():
    return sorted([e for e in EVENT_ITEMS if e["date"] >= TODAY], key=lambda e: e["date"])


def notices(name, lang, place):
    """The notices of a page for one place, in file order, while TODAY is inside their window."""
    return [x for x in P(name, lang).get("notices", []) if x["place"] == place and shown(x)]


def next_up(lang):
    """The first thing on the home page: a "next_up" notice while one is shown, else the first upcoming event."""
    p = P("home", lang)
    label = p["next_up_label"]
    promo = notices("home", lang, "next_up")
    if promo:
        x = promo[0]
        return (f'<a class="next-up next-up--promo" href="{link_href(lang, x["link"])}"><i>{label}</i>'
                f'<span><b>{x["text"]}</b></span></a>')
    ev = upcoming_events()
    if not ev:
        return ""
    e = ev[0]
    when = long_date(lang, e["date"])
    when = when[0].upper() + when[1:] + (f", {e['time'].replace('–', ' - ')}" if e["time"] else "")
    return f'<a class="next-up" href="{url(lang, "events")}#{e["kind"]}"><i>{label}</i><span><b>{tr(e["title"], lang)}</b> · {when}</span></a>'


def news_section(lang):
    p = P("home", lang)
    cards = []
    for i, n in enumerate(NEWS_ITEMS):
        img = (f'<div class="nc-img" style="background-image:url(/assets/photos/{n["img"]})" role="img" aria-label="{tr(n["title"], lang)}"></div>' if n["img"]
               else f'<div class="nc-img nc-price" aria-hidden="true"><span>{esc(tr(n["badge"], lang))}</span></div>'
               if n["badge"] and tr(n["badge"], lang) else "")
        href = link_href(lang, n["link"])
        btn = tr(n["btn"], lang) if n["btn"] else T[lang]["cta"]
        first = ' first" data-first="' + p["news_first_label"] if i == 0 else ""
        big = " nc-big" if n["big"] else ""
        sticker = f'<span class="fun-sticker">{tr(n["sticker"], lang)}</span>' if n["sticker"] else ""
        dfirst = f' data-first="{p["news_first_label"]}"' if i == 0 else ""  # the CSS label reads it from here
        cards.append(f"""<article class="news-card{big}{first}">{img}<div class="nc-body"><div class="nc-when"{dfirst}>{ICONS['calendar']}{tr(n['when'], lang)}</div>
  <h3>{tr(n['title'], lang)}</h3>{paras(n['text'], lang)}
  <div class="nc-actions"><a class="btn btn-pink" href="{href}">{btn}</a>{sticker}</div></div></article>""")
    return f"""<section class="sec news" id="news"><div class="wrap">
  <div class="sec-title sec-title-row"><h2><span class="hl">{p['news_title']}</span></h2><a class="more-link" href="{url(lang, 'events')}">{p['news_all_link']}</a></div>
  <div class="news-grid">{''.join(cards)}</div>
</div></section>"""


def event_url(lang, e):
    """Every event has a page of its own: /en/events/<file name>/."""
    return url(lang, "events") + e["slug"] + "/"


def maps_link(lang, place):
    """The place of an event opens in Google Maps; a pin icon marks the link."""
    hint = P("events", lang)["map_hint"]
    q = urllib.parse.quote(place)
    return f'<a class="ev-map" href="https://www.google.com/maps/search/?api=1&query={q}" target="_blank" rel="noopener" title="{esc(hint)}">{ICONS["pin"]}{place}</a>'


def event_item(lang, e, single=False):
    d = e["date"]
    past = d < TODAY
    meta = [x for x in ((lambda x: x[0].upper() + x[1:])(long_date(lang, d)) if single else "", e["time"], maps_link(lang, e["place"]) if e["place"] else "") if x]
    btn = (f'<div class="answer-actions"><a class="btn{" btn-yellow" if e["kind"] == "socials" else ""}" href="{e["link"]}">{tr(e["btn"], lang)}</a></div>'
           if e["btn"] and not past else "")
    title = f'<h1>{tr(e["title"], lang)}</h1>' if single else f'<h3><a href="{event_url(lang, e)}">{tr(e["title"], lang)}</a></h3>'
    return f"""<article class="ev-item{' past' if past else ''}{' ev-single' if single else ''}"><div class="date-box"><div class="m">{MONTH_SHORT[lang][d.month - 1]}</div><div class="d">{d.day}</div><div class="w">{WEEKDAY[lang][d.weekday()]}</div></div>
  <div>{title}<ul class="meta">{''.join(f'<li>{m}</li>' for m in meta)}</ul>{paras(e['text'], lang)}{btn}</div>
  <div class="ev-img" style="background-image:url(/assets/photos/{e['img']})" role="img" aria-label="{tr(e['title'], lang)}"></div></article>"""


def shown_events():
    """The events that are on the site: every upcoming one, plus the latest past one of each kind.
    Older past events leave the site by themselves (one earlier event stays, the rest disappear)."""
    out = [e for e in EVENT_ITEMS if e["date"] >= TODAY]
    for k in {e["kind"] for e in EVENT_ITEMS}:
        past = sorted([e for e in EVENT_ITEMS if e["kind"] == k and e["date"] < TODAY], key=lambda e: e["date"])
        if past:
            out.append(past[-1])
    return out


def event_page(lang, e):
    p = P("events", lang)
    kind = next((x["label"] for x in p["kinds"] if x["kind"] == e["kind"]), "")
    crumbs = f'<a href="{url(lang, "events")}">{T[lang]["nav_events"]}</a> › <a href="{url(lang, "events")}#{e["kind"]}">{kind}</a>'
    # a past event's own page says so, since people still reach it from Google or an old link
    past = f'<p class="ev-empty ev-past">{p["past_note"]}</p>' if e["date"] < TODAY and p.get("past_note") else ""
    body = f"""<section class="sec ev-page"><div class="wrap"><div class="crumbs">{crumbs}</div>
  {past}{event_item(lang, e, single=True)}
  <p class="ev-back"><a class="link" href="{url(lang, "events")}#{e["kind"]}">{p["back_label"]}</a></p>
</div></section>"""
    desc = tr(e["text"], lang)[:150]
    title = f"{tr(e['title'], lang)}, {long_date(lang, e['date'])} | Lumos Latin"
    page(lang, "events", title, desc, body, head=events_ld(lang, [e]), sub=e["slug"])


def events(lang):
    """One section per kind of event: upcoming ones first, then the earlier ones."""
    nl = lang == "nl"
    p = P("events", lang)
    intro = p["intro"]
    jump = "".join(f'<a class="btn" href="#{x["kind"]}">{x["label"]}</a>' for x in p["kinds"])
    secs = []
    for x in p["kinds"]:
        k = x["kind"]
        items = [e for e in EVENT_ITEMS if e["kind"] == k]
        up = sorted([e for e in items if e["date"] >= TODAY], key=lambda e: e["date"])
        # only the latest past event stays under Earlier; older ones are gone
        past = sorted([e for e in items if e["date"] < TODAY], key=lambda e: e["date"], reverse=True)[:1]
        none = ""
        if not up:
            # an empty section says what is up next on the calendar
            none = f'<p class="ev-empty">{p.get("empty_texts", {}).get(k) or p["empty_text"]}</p>'
            nxt = upcoming_events()
            if nxt:
                none += f'<p class="ev-upnext"><b>{p["up_next_label"]}:</b></p><div class="ev-list">{event_item(lang, nxt[0])}</div>'
        earlier = (f'<h3 class="ev-earlier">{p["earlier"]}</h3><div class="ev-list">{"".join(event_item(lang, e) for e in past)}</div>' if past else "")
        secs.append(f"""<section class="sec ev-sec{' sec-soft' if len(secs) % 2 else ''}" id="{k}"><div class="wrap">
  <div class="sec-title"><h2><span class="hl">{x['label']}</span></h2></div>
  <div class="ev-list">{''.join(event_item(lang, e) for e in up)}</div>{none}
  {earlier}
</div></section>""")
    first = upcoming_events()
    lead = ""
    if first:
        e = first[0]
        d = e["date"]
        short = f"{d.day} {MONTH_SHORT[lang][d.month - 1]}" if nl else f"{MONTH_SHORT[lang][d.month - 1]} {d.day}"
        lead = f'<p class="ev-lead"><b>{p["first_label"]}:</b> {tr(e["title"], lang)}, {short}</p>'
    body = page_head(T[lang]["nav_events"], intro, extra=lead + f'<div class="ev-nav">{jump}</div>') + "".join(secs)
    page(lang, "events", f"{P('events', lang)['meta_title']} | Lumos Latin", intro, body, head=events_ld(lang))
    for e in shown_events():
        event_page(lang, e)


# Footer icons: brand marks from Simple Icons (CC0), phone and mail from Lucide (ISC).
ICONS = {'whatsapp': '<svg class="ico" aria-hidden="true" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path fill="currentColor" d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413Z"/></svg>', 'instagram': '<svg class="ico" aria-hidden="true" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path fill="currentColor" d="M7.0301.084c-1.2768.0602-2.1487.264-2.911.5634-.7888.3075-1.4575.72-2.1228 1.3877-.6652.6677-1.075 1.3368-1.3802 2.127-.2954.7638-.4956 1.6365-.552 2.914-.0564 1.2775-.0689 1.6882-.0626 4.947.0062 3.2586.0206 3.6671.0825 4.9473.061 1.2765.264 2.1482.5635 2.9107.308.7889.72 1.4573 1.388 2.1228.6679.6655 1.3365 1.0743 2.1285 1.38.7632.295 1.6361.4961 2.9134.552 1.2773.056 1.6884.069 4.9462.0627 3.2578-.0062 3.668-.0207 4.9478-.0814 1.28-.0607 2.147-.2652 2.9098-.5633.7889-.3086 1.4578-.72 2.1228-1.3881.665-.6682 1.0745-1.3378 1.3795-2.1284.2957-.7632.4966-1.636.552-2.9124.056-1.2809.0692-1.6898.063-4.948-.0063-3.2583-.021-3.6668-.0817-4.9465-.0607-1.2797-.264-2.1487-.5633-2.9117-.3084-.7889-.72-1.4568-1.3876-2.1228C21.2982 1.33 20.628.9208 19.8378.6165 19.074.321 18.2017.1197 16.9244.0645 15.6471.0093 15.236-.005 11.977.0014 8.718.0076 8.31.0215 7.0301.0839m.1402 21.6932c-1.17-.0509-1.8053-.2453-2.2287-.408-.5606-.216-.96-.4771-1.3819-.895-.422-.4178-.6811-.8186-.9-1.378-.1644-.4234-.3624-1.058-.4171-2.228-.0595-1.2645-.072-1.6442-.079-4.848-.007-3.2037.0053-3.583.0607-4.848.05-1.169.2456-1.805.408-2.2282.216-.5613.4762-.96.895-1.3816.4188-.4217.8184-.6814 1.3783-.9003.423-.1651 1.0575-.3614 2.227-.4171 1.2655-.06 1.6447-.072 4.848-.079 3.2033-.007 3.5835.005 4.8495.0608 1.169.0508 1.8053.2445 2.228.408.5608.216.96.4754 1.3816.895.4217.4194.6816.8176.9005 1.3787.1653.4217.3617 1.056.4169 2.2263.0602 1.2655.0739 1.645.0796 4.848.0058 3.203-.0055 3.5834-.061 4.848-.051 1.17-.245 1.8055-.408 2.2294-.216.5604-.4763.96-.8954 1.3814-.419.4215-.8181.6811-1.3783.9-.4224.1649-1.0577.3617-2.2262.4174-1.2656.0595-1.6448.072-4.8493.079-3.2045.007-3.5825-.006-4.848-.0608M16.953 5.5864A1.44 1.44 0 1 0 18.39 4.144a1.44 1.44 0 0 0-1.437 1.4424M5.8385 12.012c.0067 3.4032 2.7706 6.1557 6.173 6.1493 3.4026-.0065 6.157-2.7701 6.1506-6.1733-.0065-3.4032-2.771-6.1565-6.174-6.1498-3.403.0067-6.156 2.771-6.1496 6.1738M8 12.0077a4 4 0 1 1 4.008 3.9921A3.9996 3.9996 0 0 1 8 12.0077"/></svg>', 'tiktok': '<svg class="ico" aria-hidden="true" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path fill="currentColor" d="M12.525.02c1.31-.02 2.61-.01 3.91-.02.08 1.53.63 3.09 1.75 4.17 1.12 1.11 2.7 1.62 4.24 1.79v4.03c-1.44-.05-2.89-.35-4.2-.97-.57-.26-1.1-.59-1.62-.93-.01 2.92.01 5.84-.02 8.75-.08 1.4-.54 2.79-1.35 3.94-1.31 1.92-3.58 3.17-5.91 3.21-1.43.08-2.86-.31-4.08-1.03-2.02-1.19-3.44-3.37-3.65-5.71-.02-.5-.03-1-.01-1.49.18-1.9 1.12-3.72 2.58-4.96 1.66-1.44 3.98-2.13 6.15-1.72.02 1.48-.04 2.96-.04 4.44-.99-.32-2.15-.23-3.02.37-.63.41-1.11 1.04-1.36 1.75-.21.51-.15 1.07-.14 1.61.24 1.64 1.82 3.02 3.5 2.87 1.12-.01 2.19-.66 2.77-1.61.19-.33.4-.67.41-1.06.1-1.79.06-3.57.07-5.36.01-4.03-.01-8.05.02-12.07z"/></svg>', 'facebook': '<svg class="ico" aria-hidden="true" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path fill="currentColor" d="M9.101 23.691v-7.98H6.627v-3.667h2.474v-1.58c0-4.085 1.848-5.978 5.858-5.978.401 0 .955.042 1.468.103a8.68 8.68 0 0 1 1.141.195v3.325a8.623 8.623 0 0 0-.653-.036 26.805 26.805 0 0 0-.733-.009c-.707 0-1.259.096-1.675.309a1.686 1.686 0 0 0-.679.622c-.258.42-.374.995-.374 1.752v1.297h3.919l-.386 2.103-.287 1.564h-3.246v8.245C19.396 23.238 24 18.179 24 12.044c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.628 3.874 10.35 9.101 11.647Z"/></svg>', 'phone': '<svg class="ico" aria-hidden="true" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" > <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z" /> </svg>', 'mail': '<svg class="ico" aria-hidden="true" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" > <rect width="20" height="16" x="2" y="4" rx="2" /> <path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7" /> </svg>'}


# ---------------------------------------------------------------- shared layout
FLAG_NL = ('<svg viewBox="0 0 9 6" preserveAspectRatio="xMidYMid slice" aria-hidden="true"><rect fill="#21468B" width="9" height="6"/>'
           '<rect fill="#fff" width="9" height="4"/><rect fill="#AE1C28" width="9" height="2"/></svg>')
FLAG_UK = ('<svg viewBox="0 0 60 30" preserveAspectRatio="xMidYMid slice" aria-hidden="true"><rect width="60" height="30" fill="#012169"/>'
           '<path d="M0,0 L60,30 M60,0 L0,30" stroke="#fff" stroke-width="6"/><path d="M0,0 L60,30 M60,0 L0,30" stroke="#C8102E" stroke-width="3"/>'
           '<path d="M30,0 v30 M0,15 h60" stroke="#fff" stroke-width="10"/><path d="M30,0 v30 M0,15 h60" stroke="#C8102E" stroke-width="6"/></svg>')


DANCE_ICONS = {
    "salsa": '<ellipse class="floor" cx="24" cy="41" rx="15" ry="3.2"/><path class="swish" d="M36 7a10 10 0 0 1 4 7"/><g class="ln"><circle class="hd" cx="17" cy="9" r="2.1"/><circle class="hd" cx="30.5" cy="11" r="2"/><path d="M17 11.5C16.4 16 16 21 16 25M16 25l-3 15M16 25l3.2 15M17 14.5L22.5 7l1.5-2M17 15.5l-4.5 6M30.5 13.5c.3 3.5.6 7 .3 10.5M30.5 15.5L26 7.5l-2-2.5M30.6 16.5l4 4.5M27.5 24c-2 3-3 6-2.6 9l11.8-1.8c-.8-3-2-5.8-3.7-7.7M29 33l-1 7M33 32.5l1.8 6.8"/></g>',
    "bachata": '<ellipse class="floor" cx="24" cy="41" rx="15" ry="3.2"/><path class="swish" d="M8 20c2-3 4-3 6 0"/><g class="ln"><circle class="hd" cx="20" cy="9.5" r="2.1"/><circle class="hd" cx="27.5" cy="10" r="2"/><path d="M20 12c-.8 5 0 9.5 1.3 13M27.5 12.5c.8 5 0 9-1.3 12.5M21.3 25l-3.2 15M21.3 25l1.6 15M26.2 25l-.6 15M26.2 25l3.6 15M20 15.5l6.8 3M27.5 15.5l-6.3-1.5"/></g>',
    "reggaeton": '<ellipse class="floor" cx="24" cy="41" rx="15" ry="3.2"/><g class="ln"><circle class="hd" cx="23.5" cy="7.5" r="2.1"/><path d="M23.5 10c1 4.5-1.8 9 1.6 15M25.1 25l-4 7 .9 8M25.1 25l4.4 15M23.8 13l6-3.6.8-6M23.8 14l-4.8 3.6 4 4.4M32 21.5h3.4M32.4 25h4"/></g>',
}
LINE = '<svg class="ico" aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">{}</svg>'
ICONS["calendar"] = LINE.format('<rect width="18" height="18" x="3" y="4" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/>')
ICONS["pin"] = LINE.format('<path d="M20 10c0 4.993-5.539 10.193-7.399 11.799a1 1 0 0 1-1.202 0C9.539 20.193 4 14.993 4 10a8 8 0 0 1 16 0"/><circle cx="12" cy="10" r="3"/>')


def dance_icon(d):
    # data-dance: app.js animates the icon;
    # this markup stays the still pose, so the card looks the same with JS off or reduced motion.
    return f'<svg class="dance-ico" data-dance="{d}" aria-hidden="true" viewBox="0 0 48 48">{DANCE_ICONS[d]}</svg>'


def header(lang, page, other_href):
    t = T[lang]
    other = "en" if lang == "nl" else "nl"
    on = lambda p: ' class="on"' if p == page else ""
    nl_link = f'href="{other_href if other == "nl" else url("nl", page)}"' if lang == "en" else 'href="#" aria-current="true"'
    en_link = f'href="{other_href if other == "en" else url("en", page)}"' if lang == "nl" else 'href="#" aria-current="true"'
    return f"""
<header class="site-header">
  <div class="wrap hdr">
    <a class="logo" href="{home_url(lang)}"><img src="/assets/lumos-logo.png" alt="Lumos Latin Dance School" width="331" height="275"></a>
    <nav class="main-nav" id="nav" aria-label="Menu">
      <a href="{url(lang, 'salsa')}"{on('salsa')}>Salsa</a>
      <a href="{url(lang, 'bachata')}"{on('bachata')}>Bachata</a>
      <a href="{url(lang, 'reggaeton')}"{on('reggaeton')}>Reggaeton</a>
      <a href="{url(lang, 'schedule')}"{on('schedule')}>{t['nav_schedule']}</a>
      <a href="{url(lang, 'prices')}"{on('prices')}>{t['nav_prices']}</a>
      <a href="{url(lang, 'teachers')}"{on('teachers')}>{t['nav_teachers']}</a>
      <a href="{url(lang, 'events')}"{on('events')}>{t['nav_events']}</a>
      <a href="{url(lang, 'studios')}"{on('studios')}>{t['nav_studios']}</a>
    </nav>
    <div class="hdr-right">
      <div class="lang notranslate" translate="no" aria-label="Language"><a {nl_link} lang="nl" title="Nederlands" aria-label="Nederlands"{' class="on"' if lang == 'nl' else ''}>{FLAG_NL}</a><a {en_link} lang="en" title="English" aria-label="English"{' class="on"' if lang == 'en' else ''}>{FLAG_UK}</a></div>
      <a class="btn btn-pink hdr-cta" href="{cta_href(lang, page)}">{t['cta']}</a>
      <button class="menu-btn" type="button" aria-controls="nav" aria-expanded="false"><i></i>{t['menu']}</button>
    </div>
  </div>
</header>"""


def footer(lang, page=None):
    t = T[lang]
    return f"""
<footer class="site-footer"><div class="zigzag" aria-hidden="true"></div>
  <div class="wrap">
    <div class="foot-grid">
      <div>
        <a class="logo" href="{home_url(lang)}"><img src="/assets/lumos-logo.png" alt="Lumos Latin Dance School" width="331" height="275"></a>
      </div>
      <div><h2 class="foot-h">{t['foot_contact']}</h2><ul>
        <li><a class="ico-link" href="{WA}">{ICONS['whatsapp']}WhatsApp</a></li>
        <li><a class="ico-link" href="{TEL}">{ICONS['phone']}{PHONE}</a></li>
        <li><a class="ico-link" href="mailto:{EMAIL}">{ICONS['mail']}{EMAIL}</a></li></ul></div>
      <div><h2 class="foot-h">{t['foot_dances']}</h2><ul>
        <li><a href="{url(lang, 'salsa')}">Salsa</a></li>
        <li><a href="{url(lang, 'bachata')}">Bachata</a></li>
        <li><a href="{url(lang, 'reggaeton')}">Reggaeton</a></li></ul></div>
      <div><h2 class="foot-h">{t['foot_classes']}</h2><ul>
        <li><a href="{url(lang, 'schedule')}">{t['nav_schedule']}</a></li>
        <li><a href="{url(lang, 'prices')}">{t['nav_prices']}</a></li>
        <li><a href="{url(lang, 'studios')}">{t['studios_word']}</a></li></ul></div>
      <div><h2 class="foot-h">{t['foot_school']}</h2><ul>
        <li><a href="{url(lang, 'events')}">{t['nav_events']}</a></li>
        <li><a href="{url(lang, 'teachers')}">{t['nav_teachers']}</a></li>
        <li><a href="{url(lang, 'contact')}">{t['contact_word']}</a></li></ul></div>
      <div><h2 class="foot-h">{t['foot_follow']}</h2><ul>
        <li><a class="ico-link" href="{IG}">{ICONS['instagram']}Instagram</a></li>
        <li><a class="ico-link" href="{TT}">{ICONS['tiktok']}TikTok</a></li>
        <li><a class="ico-link" href="{FB}">{ICONS['facebook']}Facebook</a></li></ul></div>
    </div>
    <div class="foot-bottom"><span>{t['foot_about']}</span><span>{t['rights']} {FOUNDED}-{TODAY.year} · <a href="{url(lang, 'privacy')}">{t['privacy']}</a></span></div>
  </div>
</footer>
"""


def jsonld(data):
    """A JSON-LD block for the head; '</' is escaped so the text can never close the script tag."""
    return '<script type="application/ld+json">' + json.dumps(data, ensure_ascii=False).replace("</", "<\\/") + "</script>\n"


def school_ld():
    """The school as a DanceSchool, only with facts already used on the pages."""
    return {"@context": "https://schema.org", "@type": "DanceSchool", "name": "Lumos Latin",
            "url": SITE + "/", "logo": SITE + "/assets/lumos-logo.png", "image": SITE + OG_IMAGE,
            "telephone": TEL.replace("tel:", ""), "email": EMAIL,
            "address": [{"@type": "PostalAddress", "name": s["name"], "streetAddress": s["addr"],
                         "addressLocality": "Amsterdam", "addressCountry": "NL"} for s in STUDIOS.values()],
            "sameAs": [IG, TT, FB]}


def events_ld(lang, items=None):
    """Upcoming events with a real date and place (EVENT_ITEMS); past ones are left out. items: just these events."""
    out = []
    for e in sorted(upcoming_events() if items is None else items, key=lambda e: e["date"]):
        item = {"@context": "https://schema.org", "@type": "Event", "name": tr(e["title"], lang),
                "startDate": e["date"].isoformat(), "description": tr(e["text"], lang),
                "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
                "eventStatus": "https://schema.org/EventScheduled",
                "location": {"@type": "Place", "name": e["place"].split(",")[0],
                             "address": {"@type": "PostalAddress", "streetAddress": e["place"], "addressCountry": "NL"}},
                "organizer": {"@type": "DanceSchool", "name": "Lumos Latin", "url": SITE + "/"},
                "url": SITE + event_url(lang, e)}
        if e.get("img"):
            item["image"] = SITE + "/assets/photos/" + e["img"]
        if e.get("link", "").startswith("http"):
            item["offers"] = {"@type": "Offer", "url": e["link"]}
        out.append(item)
    return jsonld(out) if out else ""


def og_image():
    """Cut the share image (1200x630) from the school's own photo. Needs Pillow; without it an existing file is kept."""
    src = os.path.join(ROOT, "assets", "photos", "hero-dance.jpg")
    dst = os.path.join(ROOT, OG_IMAGE.lstrip("/"))
    if os.path.exists(dst) and os.path.getmtime(dst) >= os.path.getmtime(src):
        return
    try:
        from PIL import Image
    except ImportError:
        print("Pillow missing: og-image.jpg not (re)made")
        return
    im = Image.open(src).convert("RGB")
    w = round(im.width * 630 / im.height)
    im = im.resize((w, 630), Image.LANCZOS)
    left = (w - 1200) // 2
    im.crop((left, 0, left + 1200, 630)).save(dst, "JPEG", quality=85, optimize=True, progressive=True)


def page(lang, key, title, desc, body, other_href=None, nav_page=None, path=None, head="", sub=None):
    """sub: a page of its own under the key's page, e.g. sub="2026-11-03-salsa-bachata-social" under events."""
    other = "en" if lang == "nl" else "nl"
    tail = sub + "/" if sub else ""
    other_href = other_href or url(other, key) + tail
    self_href = f"{base()}/{path}" if path else url(lang, key) + tail
    alts = {lang: self_href, other: other_href}
    # answer pages (/start/<answer>/) are thin variants of the home page: canonical to home, not in the sitemap
    canonical = url(lang, "home") if path else self_href
    if not path:
        SITEMAP.append((self_href, alts))
    og_locale = dict(en="en_GB", nl="nl_NL")
    title, desc = cap(title), cap(desc)
    html = f"""<!doctype html>
<html lang="{lang}" data-base="{base()}" data-shape="{HL_SHAPE}" data-color="{HL_COLOR}" data-btn="{BTN_COLOR}" data-qbg="{Q_BG}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
{GTM_HEAD}
{ROBOTS_META}<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{SITE}{canonical}">
<link rel="alternate" hreflang="en" href="{SITE}{alts['en']}">
<link rel="alternate" hreflang="nl" href="{SITE}{alts['nl']}">
<link rel="alternate" hreflang="x-default" href="{SITE}{alts['en']}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Lumos Latin">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{SITE}{self_href}">
<meta property="og:locale" content="{og_locale[lang]}">
<meta property="og:locale:alternate" content="{og_locale[other]}">
<meta property="og:image" content="{SITE}{OG_IMAGE}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
{head}<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:opsz,wght@9..40,400;9..40,500;9..40,600;9..40,700&family=Oswald:wght@500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/assets/style.css">
<link rel="icon" href="/assets/lumos-gem-icon.svg" type="image/svg+xml">
</head>
<body class="pg-{key if not path else 'start'}">
{GTM_BODY}{header(lang, nav_page or key, other_href)}
<main>
{body}
</main>
{footer(lang, nav_page or key)}
<a class="wa-float{' wa-float--up' if HIDDEN else ''}" href="{WA}" target="_blank" rel="noopener" aria-label="WhatsApp">{ICONS['whatsapp']}</a>
<script src="/assets/data.js"></script>
<script src="/assets/app.js"></script>
{FEEDBACK_JS}</body>
</html>
"""
    html = cap_html(html)
    out = os.path.join(ROOT, base().strip("/"), path or (lang + "/" + (SLUGS[lang][key] + "/" if SLUGS[lang][key] else "") + tail), "index.html")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    if lang == "en" and key == "home" and not path:
        # English opens first: the site root is the English home page.
        with open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8") as f:
            # canonical stays on /en/ (the root is a copy of it); og:url follows the canonical
            f.write(html)


# The school's whole home video as one muted loop in a 16:9 tile under the intro text (written here, so it shows without JavaScript).
# app.js gives it a play button instead when motion is turned off.
HERO_VIDEO = ('<div class="hero-video"><video class="autoloop" autoplay muted loop playsinline poster="/assets/photos/video-poster.jpg" aria-hidden="true">'
              '<source src="/assets/loops/lumos-loop-1920.mp4" type="video/mp4"></video></div>')

# Switches under the first highlighted words (only with --switches): highlight shape and
# highlight colour. feedback.js moves them under the highlight and changes data-shape and data-color on <html>;
# style.css reads those attributes. Pages without a highlight drop them.
FADE_VARY = ('<div class="vary vary-fade" data-vary="hl-shape" data-attr="shape" data-title="Highlight shape">'
             '<div class="vary-opt" data-label="A"></div><div class="vary-opt" data-label="B"></div><div class="vary-opt" data-label="C"></div></div>'
             '<div class="vary vary-fade" data-vary="hl-color" data-attr="color" data-title="Highlight colour">'
             '<div class="vary-opt" data-label="Pink"></div><div class="vary-opt" data-label="Purple"></div>'
             '<div class="vary-opt" data-label="Lilac"></div><div class="vary-opt" data-label="Rose"></div><div class="vary-opt" data-label="Orchid"></div><div class="vary-opt" data-label="Moving"></div></div>'
             # Two more switches: button colour and the questions background.
             # feedback.js sets <html data-btn="Pink|Purple"> and <html data-qbg="White|Yellow">; style.css reads them.
             '<div class="vary vary-fade" data-vary="btn-color" data-attr="btn" data-title="Button colour">'
             '<div class="vary-opt" data-label="Pink"></div><div class="vary-opt" data-label="Purple"></div></div>'
             '<div class="vary vary-fade" data-vary="q-bg" data-attr="qbg" data-title="Questions background">'
             '<div class="vary-opt" data-label="White"></div><div class="vary-opt" data-label="Yellow"></div></div>')
FEEDBACK_JS = '<script src="/assets/feedback.js"></script>\n'
# Without --switches the boxes and their script are left out; content/settings.json decides the look.
if not SHOW_SWITCHES:
    FADE_VARY = FEEDBACK_JS = ""


def page_head(title, intro, crumbs=None, extra=""):
    c = f'<div class="crumbs">{crumbs}</div>' if crumbs else ""
    p = f"<p>{intro}</p>" if intro else ""
    # no intro (teachers page): title only, no line under it, the content starts higher
    cls = "page-head" if intro else "page-head no-line"
    return f'<section class="{cls}">{FADE_VARY}<div class="wrap">{c}<h1>{title}</h1>{p}{extra}</div></section>'


def reggaeton_prices(lang):
    p = P("reggaeton", lang)
    cells = "".join(f'<li><span class="ps-n">{i}</span><div><b>{x["name"]}</b> <span class="ps-p">{x["price"]}</span><small>{x["detail"]}</small></div></li>'
                    for i, x in enumerate(in_lang(PRICES["reggaeton_strip"], lang), 1))
    return f"""<section class="sec sec-soft"><div class="wrap">
  <div class="sec-title"><h2><span class="hl">{p['price_title']}</span></h2><p>{p['price_sub']}</p></div>
  <ol class="price-strip">{cells}</ol>
</div></section>"""


# ---------------------------------------------------------------- shared home blocks
def rating(lang):
    return S["google_rating"].replace(".", ",") if lang == "nl" else S["google_rating"]


def with_count(text):
    return text.replace("{count}", str(S["review_count"]))


def trust_line(lang):
    p = P("home", lang)
    return (f'<div class="trust"><span class="stars" aria-hidden="true">★★★★★</span>'
            f'<span><b>{rating(lang)}</b> {with_count(p["trust_reviews"])}</span>'
            f'<a href="{url(lang, "studios")}">{p["trust_studios"]}</a>'
            '</div>')


def first_class_section(lang):
    p = P("start", lang)
    items = "".join(f"<li><b>{x['title']}</b><span>{x['text']}</span></li>" for x in p["first_class_items"])
    return f"""<section class="sec sec-soft"><div class="wrap">
  <div class="sec-title"><h2><span class="hl">{p['first_class_title']}</span></h2><p>{p['first_class_sub']}</p></div>
  <ul class="first-list">{items}</ul>
</div></section>"""


def faq_items(lang):
    return [(x["question"], x["answer"]) for x in in_lang(FAQ, lang)]


WORRY_ICONS = [  # partner, experience, shoes: in the order of the "worries" list in content/pages/dances.json
    '<svg viewBox="0 0 28 28" fill="none" stroke="#1f1b16" stroke-width="2" stroke-linecap="round"><circle cx="10" cy="8" r="3.5"/><circle cx="19" cy="9" r="3"/><path d="M3.5 24c.5-5 3-8 6.5-8s6 3 6.5 8M15 17c1-1.3 2.4-2 4-2 3 0 5 2.6 5.5 7"/><path d="M8 3c4-2 8-2 12 0" stroke="#ffdb6e" stroke-width="2.6"/></svg>',
    '<svg viewBox="0 0 28 28" fill="none" stroke="#1f1b16" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 3v4M14 21v4M3 14h4M21 14h4M6.5 6.5l2.8 2.8M18.7 18.7l2.8 2.8M6.5 21.5l2.8-2.8M18.7 9.3l2.8-2.8"/><circle cx="14" cy="14" r="3.5" fill="#ffdb6e"/></svg>',
    '<svg viewBox="0 0 28 28" fill="none" stroke="#1f1b16" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 19c0-3 1-7 2-9h5c0 2 2 3 4 3.5 4 .8 9 1.5 10 4.5v2H3z" fill="#ffdb6e"/><path d="M3 22h21"/></svg>',
]


def worries_section(lang, dance=None):
    """Three worries beginners have, on the dance pages. A dance page can have its own (reggaeton)."""
    p = P("dances", lang)
    own = P(dance, lang).get("worries") if dance else None
    worry_cards = "".join(f'<div class="card worry"><h3>{WORRY_ICONS[i % len(WORRY_ICONS)]}{x["title"]}</h3><p>{x["text"]}</p></div>'
                          for i, x in enumerate(own or p["worries"]))
    return f"""<section class="sec sec-soft"><div class="wrap">
  <div class="sec-title"><h2><span class="hl">{p['worries_title']}</span></h2><p>{p['worries_sub']}</p></div>
  <div class="grid g3">{worry_cards}</div>
</div></section>"""


def teacher_classes(lang, name):
    """What a teacher teaches, from the class files: one line per dance, day and studio with the levels joined,
    e.g. "Salsa 1, 2 and 3 · Monday · De Veemvloer", the dance part linked to its dance page."""
    t, groups = T[lang], {}
    for c in CLASSES:  # schedule order
        if name in c["teachers"]:
            groups.setdefault((c["dance"], c["day"], c["studio"]), []).append(c)
    lines = []
    for (dance, wd, st), cs in groups.items():
        if dance == "reggaeton":
            what = class_name(cs[0])
        else:
            lv = [str(c["level"]) for c in cs]
            what = dance.capitalize() + " " + (", ".join(lv[:-1]) + f" {t['and_']} " + lv[-1] if len(lv) > 1 else lv[0])
        lines.append(f'<li><a class="link" href="{url(lang, dance)}">{what}</a> · {t["days_long"][wd].capitalize()} · {STUDIOS[st]["name"]}</li>')
    return f'<ul class="t-classes">{"".join(lines)}</ul>' if lines else ""


def teachers_page(lang):
    cards = []
    for x in sorted(load_list("teachers"), key=lambda x: (x.get("order", 99), x["name"])):
        n, r, bio, photo = x["name"], tr(x.get("role", ""), lang), tr(x.get("bio", ""), lang), x.get("photo", "")
        if photo and not os.path.exists(os.path.join(ROOT, "assets", "photos", photo)):
            raise SystemExit(f"{where('teachers', x['slug'] + '.json')}: photo {photo!r} is not in prototype/assets/photos")
        pic = (f'<img class="t-photo" src="/assets/photos/{esc(photo)}" alt="{esc(n)}" width="400" height="500" loading="lazy">' if photo
               else f'<div class="ph" aria-hidden="true">{n[0]}</div>')
        taught = teacher_classes(lang, n)
        cards.append(f'<div class="card teacher">{pic}<div class="t-text"><h2 class="card-h">{n}</h2><div class="role">{r}</div>'
                     + (f'<p class="line">{bio}</p>' if bio else "")
                     + (f'<div class="t-foot"><div class="t-label">{T[lang]["foot_classes"]}</div>{taught}</div>' if taught else "") + '</div></div>')
    sec = f'<section class="sec"><div class="wrap"><div class="grid team">{"".join(cards)}</div></div></section>'
    title = T[lang]["nav_teachers"]
    # Google description from the data: the teachers' names and the dances (no intro on the page)
    names = [x["name"] for x in sorted(load_list("teachers"), key=lambda x: (x.get("order", 99), x["name"]))]
    who = ", ".join(names[:-1]) + f" {T[lang]['and_']} " + names[-1] if len(names) > 1 else names[0]
    desc = (f"{who} geven salsa, bachata en reggaeton bij Lumos Latin in Amsterdam." if lang == "nl"
            else f"{who} teach salsa, bachata and reggaeton at Lumos Latin in Amsterdam.")
    page(lang, "teachers", f"{P('teachers', lang)['meta_title']} | Lumos Latin", desc, page_head(title, "") + sec)


# ---------------------------------------------------------------- home
def home(lang, answer=None):
    t, f, p = T[lang], FLOW[lang], P("home", lang)
    opts = "".join(f'<button class="q-opt" type="button" data-level="{k}"><span>{v}<small>{f["q1_subs"][k]}</small></span></button>' for k, v in f["q1_opts"].items())
    # Reggaeton straight away: skips the level question, app.js opens /start/reggaeton/
    r_label, r_sub = f["q1_reggaeton"]
    opts += f'<button class="q-opt q-opt-reggaeton" type="button" data-dance="reggaeton"><span>{r_label}<small>{r_sub}</small></span></button>'
    hero = f"""
<section class="hero{' hero--answer' if answer else ''}" id="start">
  {FADE_VARY}
  <div class="wrap hero-in">
    <div class="hero-text">
      <h1>{p['title']}</h1>
      <p class="hero-dances">{p['dances_line']}</p>
      <p class="hero-sub">{t['hero_sub']}<span class="hero-sub2">{t['hero_sub2']}</span></p>
      {HERO_VIDEO}
      {next_up(lang)}
      <div class="hero1-trust">{trust_line(lang)}</div>
    </div>
    <div class="hero-flow">
      <div class="q-card" id="flow" data-answer="{answer or ''}" aria-live="polite">
        <div class="q-step">{f['step'].replace('{n}', '1')}</div>
        <h2 class="q">{f['q1']}</h2>
        <div class="q-opts">{opts}</div>
      </div>
      <p class="hero-note small"><b>{p['hero_note_label']}:</b> {p['hero_note']} <a class="link note-link" href="{url(lang, 'schedule')}">{p['browse_link']}</a></p>
    </div>
  </div>
</section>"""

    dance_cards = "".join(
        f'<a class="card dance-card" href="{url(lang, d)}">{dance_icon(d)}<h3>{d.capitalize()}</h3><p>{p["dance_lines"][d]}</p><span class="go">{p["more_about"]} {d}</span></a>'
        for d in ("salsa", "bachata", "reggaeton"))
    dances = f"""<section class="sec" id="overview"><div class="wrap">
  <div class="sec-title"><h2><span class="hl">{p['dances_title']}</span></h2><p>{p['dances_sub']}</p></div>
  <div class="grid g3">{dance_cards}</div>
</div></section>"""

    q_cards = "".join(f'<div class="card quote"><blockquote lang="{x.get("lang", "en")}">{x["quote"]}</blockquote><cite>{x["name"]} <span>· Google</span></cite></div>' for x in REVIEWS)
    reviews = f"""<section class="sec sec-soft"><div class="wrap">
  <div class="sec-title"><h2><span class="hl">{p['reviews_title']}</span></h2></div>
  <div class="rating"><span class="big">{rating(lang)}</span><div><div class="stars" aria-hidden="true">★★★★★</div><div>{with_count(p['reviews_line'])}</div></div></div>
  <div class="grid g3">{q_cards}</div>
</div></section>"""

    studios = f"""<section class="sec studios-line"><div class="wrap"><p>{ICONS['pin']}<b>{p['studios_title']}:</b> {p['studios_text']}</p>
  <a class="btn" href="{url(lang, 'studios')}">{p['studios_button']}</a></div></section>"""

    if answer:
        body = hero + (first_class_section(lang) if answer.startswith("beginner") else "") + reviews
    else:
        body = hero + news_section(lang) + dances + reviews + studios
    if answer:
        a = ANSWER_COPY[lang][answer]
        title = f"{a['title']} | Lumos Latin"
        other = "en" if lang == "nl" else "nl"
        page(lang, "home", title, a["intro"], body, other_href=f"{base()}/{other}/start/{answer}/", nav_page="start",
             path=f"{lang}/start/{answer}/")
    else:
        page(lang, "home", p["meta_title"], p["meta_description"], body, nav_page="home", head=jsonld(school_ld()))


# ---------------------------------------------------------------- dance pages
def dance_page(lang, dance):
    t, p, dp = T[lang], P(dance, lang), P("dances", lang)
    intro = p["intro"]
    levels = p.get("levels", [])

    cs_all = sorted([x for x in CLASSES if x["dance"] == dance], key=lambda x: (x["level"], try_key(x)))
    h = dp["table_headings"]
    # no try-out weeks: the try-out column leaves the table
    th = [h["class"], h["tryout"], h["then"], h["studio"], ""] if TRYOUTS else [h["class"], h.get("when") or h["then"], h["studio"], ""]
    trs = []
    for c in cs_all:
        d_, n_, m_, tt_ = c["try_"]
        st = STUDIOS[c["studio"]]
        if dance == "reggaeton":
            then = dp["drop_in_line"] + f"{c['time']}–{c['end']}"
        else:  # the course dates on their own line, easier to read
            when, _, dates = course_label(lang, c).rpartition(", ")
            then = dp["course_line"] + when + f"<small>{dates}</small>"
        if c["level"] > 1:
            then += f'<small>{t["per_class"]}</small>'
        try_td = f'<td data-label="{th[1]}">{t["days"][d_]} {n_} {MONTHS[lang][m_]}, {tt_}–{try_end(c)}</td>\n  ' if TRYOUTS else ""
        trs.append(f"""<tr><th>{class_name(c)}<small>{level_name(lang, c)}</small></th>
  {try_td}<td data-label="{th[-3]}">{then}</td>
  <td data-label="{th[-2]}">{st['name']}<small>{st['addr']} ({st['area']}) · {teachers(lang, c)}</small></td>
  <td class="ct-book"><a class="btn btn-sm btn-pink" href="{book_url(c, lang)}">{t['cta']}</a></td></tr>""")
    overview = ("<div class='table-wrap'><table class='ctable'><thead><tr>" + "".join(f"<th>{x}</th>" for x in th) + "</tr></thead><tbody>"
                + "".join(trs) + "</tbody></table></div>")
    you_if = dp["you_if_label"]
    cards = []
    if dance == "reggaeton":
        cards.append(f"""<div class="card lvl-card"><div class="level-badge"><div class="n">Drop-in</div></div><h3>{p['card_title']}</h3>
  <div class="you-if"><b>{you_if}</b> {p['card_who']}</div>
  <p class="learn">{p['card_learn']}</p></div>""")
    for x in levels:
        n = x["level"]
        cards.append(f"""<div class="card lvl-card" id="level-{n}"><div class="level-badge"><div class="n">{dance.capitalize()[0]}{n}</div></div><h3>{dance.capitalize()} {n} · {LEVELS[n]}</h3>
  <div class="you-if"><b>{you_if}</b> {x['who']}</div>
  <p class="learn">{x['learn']}</p></div>""")
    lad_title = dp["levels_title"] if levels else p["about_title"]
    tip = p.get("back_to_back", "")
    tip_html = f'<div class="tip"><b>{dp["tip_label"]}</b> {tip}</div>' if tip else ""
    actions = (f'<div class="page-actions"><a class="btn btn-pink" href="{link_href(lang, BOOK)}">{t["cta"]}</a>'
               f'<a class="btn" href="{url(lang, "schedule", "?filter=" + dance)}">{dp["schedule_button"]}</a>'
               f'<a class="btn" href="{url(lang, "prices")}">{dp["prices_button"]}</a></div>')
    crumbs = f'<a href="{home_url(lang)}">Home</a> · {t["nav_dances"]}'
    body = page_head(p["title"], intro, crumbs, actions) + f"""
<section class="sec"><div class="wrap">
  <div class="sec-title" id="classes"><h2><span class="hl">{dp['classes_title']}</span></h2><p>{p['classes_sub']}</p></div>
  {overview}
</div></section>
<section class="sec sec-soft"><div class="wrap">
  <div class="sec-title"><h2><span class="hl">{lad_title}</span></h2></div>
  {tip_html}
  <div class="grid {'g3' if len(cards) == 3 else 'g2'} lvl-grid">{''.join(cards)}</div>
  <div class="page-actions" style="margin-top:18px"><a class="btn" href="{home_url(lang, chooser())}">{dp['finder_button']}</a></div>
</div></section>""" + (reggaeton_prices(lang) if dance == "reggaeton" else "") + worries_section(lang, dance) + f"""
<section class="sec cta-band"><div class="wrap"><h2>{dp['cta_title']}</h2>{actions}</div></section>"""
    page(lang, dance, f"{p['meta_title']} | Lumos Latin", intro[:150], body)


# ---------------------------------------------------------------- schedule
def schedule(lang):
    t, p = T[lang], P("schedule", lang)
    intro = p["intro"]
    # The live Bueno schedule frame: no border, full width, grows to its content with iframe-resizer.
    bueno_src = ("https://www.bueno.nu/webshop/school/764/schedule?currentDate=&skipEmptyWeeksOnFirstLoad=YES"
                 "&calendarEntryTypes=&locations=&genres=&levels=&employees=&backgroundColor=ffffff")
    # Filter chips above the frame. Each chip carries Bueno's own id for that option (from
    # api.bueno.nu/organiser/school/764/filters?isWebshop=true); app.js
    # reloads the frame with those ids in its address, so Bueno does the filtering.
    bueno_groups = [
        ("calendarEntryTypes", p["filter_type"], [("1", "tryouts", p["type_tryouts"]), ("2", "courses", p["type_courses"]), ("4", "events", p["type_events"])]),
        ("genres", p["filter_dance"], [("5206", "salsa", "Salsa"), ("5207", "bachata", "Bachata"), ("5205", "reggaeton", "Reggaeton")]),
        ("levels", p["filter_level"], [("5230", "beginners", "Beginners"), ("5231", "improvers", "Improvers"), ("5232", "intermediate", "Intermediate")]),
        ("locations", p["filter_studio"], [(s["locs"], k, s["name"]) for k, s in STUDIOS.items()]),
    ]
    bueno_chips = "".join(
        f'<div class="chip-row" role="group" aria-label="{label}" data-param="{param}"><span class="chip-label">{label}</span>'
        f'<button type="button" class="chip on" data-ids="" data-filter="all" aria-pressed="true">{p["filter_all"]}</button>'
        + "".join(f'<button type="button" class="chip" data-ids="{ids}" data-filter="{key}" aria-pressed="false">{name}</button>' for ids, key, name in opts) + '</div>'
        for param, label, opts in bueno_groups)
    body = page_head(t["nav_schedule"], intro) + f"""
<section class="sec sec-tight"><div class="wrap">
  <div class="chips chips-grouped bueno-filters" id="bueno-filters">{bueno_chips}</div>
  <div class="bueno-wrap">
    <iframe id="bueno-schedule" class="bueno-frame" src="{bueno_src}" title="{t['nav_schedule']}" loading="lazy"></iframe>
  </div>
  <p class="note-line"><a class="link" href="{bueno_src}" target="_blank" rel="noopener">{p['open_in_bueno']}</a></p>
</div></section>
<script src="https://cdnjs.cloudflare.com/ajax/libs/iframe-resizer/4.3.2/iframeResizer.min.js"></script>
<script>
/* When a class is opened inside the frame, Bueno asks the page to scroll to the frame. Two fixes here:
   the frame top lands under the sticky header, so scroll to just below it; and the trim that hides "Powered by Bueno"
   on the week view cut off the buy links of the class view (that view has no footer), so the trim goes once the
   visitor moves inside the frame. */
if(window.iFrameResize){{iFrameResize({{log:false,heightCalculationMethod:'lowestElement',checkOrigin:false,onScroll:function(){{
  var f=document.getElementById('bueno-schedule');f.style.marginBottom='0';
  var hh=parseInt(getComputedStyle(document.documentElement).getPropertyValue('--hh'))||0;
  window.scrollTo({{top:f.getBoundingClientRect().top+window.scrollY-hh-12,behavior:'smooth'}});return false;}}}},'#bueno-schedule');}}
</script>"""
    page(lang, "schedule", f"{P('schedule', lang)['meta_title']} | Lumos Latin", intro, body)


# ---------------------------------------------------------------- prices questionnaire
# which price card each outcome lights up
QUIZ_CARD = {"tryout": "tryout", "tryout_single": "tryout", "punch_short": "punch", "punch_months": "punch",
             "course_months": "course", "course_then_member": "course", "member_extra_months": "membership",
             "member_extra_live": "membership", "member_essential": "membership"}

# the rules: which outcome fits which answers (the answer codes are in content/pages/prices.json)
QUIZ_JS = r"""
(function(){
var D=JSON.parse(document.getElementById('qz-data').textContent);
var a={}, res=document.getElementById('qz-result'), board=document.getElementById('qz-board');
function esc(t){return String(t).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}
function match(a){
  if(a.often==='once') return 'tryout';
  if(a.stay==='weeks') return a.exp==='never' ? 'tryout_single' : 'punch_short';
  if(a.stay==='months'){
    if(a.often==='more') return 'member_extra_months';
    return a.exp==='regular' ? 'punch_months' : 'course_months';
  }
  if(a.often==='more') return 'member_extra_live';
  return a.exp==='never' ? 'course_then_member' : 'member_essential';
}
function mark(id){
  document.querySelectorAll('.price-card').forEach(function(c){c.classList.remove('match');var t=c.querySelector('.match-tag');if(t)t.remove();});
  var c=id&&document.getElementById('pc-'+D.card[id]); if(!c) return;
  c.classList.add('match'); var t=document.createElement('span'); t.className='match-tag'; t.textContent=D.best; c.appendChild(t);
}
function clear(){
  a={}; mark(null);
  board.querySelectorAll('.chip').forEach(function(x){x.classList.remove('on');x.setAttribute('aria-pressed','false');});
  res.className='qz-result empty'; res.textContent=D.placeholder;
}
board.querySelectorAll('.chip').forEach(function(c){c.addEventListener('click',function(){
  var g=c.parentNode;
  g.querySelectorAll('.chip').forEach(function(x){x.classList.remove('on');x.setAttribute('aria-pressed','false');});
  c.classList.add('on'); c.setAttribute('aria-pressed','true'); a[g.dataset.k]=c.dataset.v;
  if(Object.keys(a).length<D.count) return;
  var id=match(a), r=D.res[id]; mark(id); res.className='qz-result';
  res.innerHTML='<div class="qz-eyebrow">'+esc(D.best)+'</div><div class="qz-name">'+esc(r.name)+'</div><div class="qz-price">'+esc(r.price)+
    (r.per?'<small>'+(r.per.charAt(0)==='/'?'':' ')+esc(r.per)+'</small>':'')+'</div><p class="qz-line">'+esc(r.line)+
    '</p><div class="qz-actions"><a class="btn btn-pink" href="'+esc(r.href)+'">'+esc(r.btn)+'</a><button class="qz-reset" type="button">'+esc(D.clear)+'</button></div>'+
    (r.alt?'<p class="qz-alt"><a class="link" href="'+esc(r.alt.href)+'">'+esc(r.alt.text)+'</a></p>':'');
  res.querySelector('.qz-reset').addEventListener('click',clear);
});});
})();
"""


def price_quiz(lang):
    """Three questions above the price cards; the answers light up one card and show its price."""
    q = P("prices", lang)["quiz"]
    rows = []
    for item in q["questions"]:
        chips = "".join(f'<button class="chip" type="button" data-v="{esc(o["value"])}" aria-pressed="false">{esc(o["label"])}</button>'
                        for o in item["options"])
        rows.append(f'<div class="qz-row" role="group" aria-label="{esc(item["question"])}"><b>{esc(item["question"])}</b>'
                    f'<div class="chips" data-k="{esc(item["key"])}">{chips}</div></div>')
    data = {"best": q["best_for_you"], "clear": q["clear"], "placeholder": q["placeholder"], "count": len(q["questions"]),
            "card": QUIZ_CARD,
            "res": {k: {"name": r["name"], "price": r["price"], "per": r["per"], "line": r["line"],
                        "btn": r["button_label"], "href": link_href(lang, r["button_link"]),
                        # a membership answer also offers the punch card
                        "alt": {"text": r["alt"]["text"], "href": link_href(lang, r["alt"]["link"])} if r.get("alt") else None}
                    for k, r in q["results"].items()}}
    blob = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    rg = q.get("reggaeton")
    # "Here for the Reggaeton?" with the two choices that fit, the same buttons as the questions above
    rg_box = ("<div class=\"qz-rg qz-row\"><b>" + esc(rg["title"]) + "</b><div class=\"chips\">" + "".join(
        f'<a class="chip" href="{link_href(lang, o["link"])}">{esc(o["label"])} <small>→ {esc(o["pick"])}</small></a>'
        for o in rg["options"]) + "</div></div>") if rg else ""
    return f"""
<section class="sec sec-soft"><div class="wrap">
  <div class="sec-title"><h2><span class="hl">{q['title']}</span></h2></div>
  <div class="qz" id="qz-board"><div class="qz-rows">{''.join(rows)}</div>
  <div class="qz-result empty" id="qz-result" aria-live="polite">{q['placeholder']}</div></div>
  {rg_box}
</div></section>
<script type="application/json" id="qz-data">{blob}</script>
<script>{QUIZ_JS}</script>"""


# ---------------------------------------------------------------- prices
def card_buttons(lang, c, bc):
    """A price card's buttons: its list of buttons (each to its own Bueno page) when it has one, else the one button."""
    if c.get("buttons"):
        return '<div class="card-btns">' + "".join(
            f'<a class="btn {bc}" href="{link_href(lang, b["link"])}">{b["label"]}</a>' for b in c["buttons"]) + "</div>"
    return f'<a class="btn {bc}" href="{link_href(lang, c["button_link"])}">{c["button_label"]}</a>'


def start_price(lang, price, link, word):
    """A membership price in the table, with a small Start button to its Bueno page when it has a link."""
    if not link:
        return price
    return f'<span class="mprice">{price} <a class="btn btn-sm" href="{link_href(lang, link)}">{word}</a></span>'


def prices(lang):
    p, pr = P("prices", lang), in_lang(PRICES, lang)
    html = []
    # the questionnaire points at a card by id; which card is which comes from the English name
    card_ids = {"try-out": "tryout", "course": "course", "punch card": "punch", "membership": "membership"}
    for c, c_en in zip(pr["cards"], PRICES["cards"]):
        badge = c["badge"]
        bdg = f'<span class="badge">{badge}</span>' if badge else ""
        bc = "btn-pink" if c["button_style"] == "pink" else ""
        cid = card_ids[c_en["name"]["en"].lower()]
        html.append(f"""<div id="pc-{cid}" class="card price-card{' pop' if badge else ''}">{bdg}<h3>{c['name']}</h3>
  <div class="price">{c['price']}<small>{c['per']}</small></div><div class="what">{c['what']}</div>
  <ul>{''.join(f'<li>{x}</li>' for x in c['ticks'])}</ul>{card_buttons(lang, c, bc)}</div>""")
    h = p["table_headings"]
    # a column with the price per class (over a real month)
    th = ["", h["classes_a_week"], h["monthly"], h["six_months"], h["per_class"], h["social_perk"]]
    table = ("<div class='table-wrap'><table class='mtable'><thead><tr>" + "".join(f"<th>{x}</th>" for x in th) + "</tr></thead><tbody>" +
             "".join(f"<tr><th>{r['name']}</th><td data-label='{th[1]}'>{r['classes_a_week']}</td><td data-label='{th[2]}'>{start_price(lang, r['monthly'], r.get('monthly_link'), p['members_start'])}</td><td data-label='{th[3]}'>{start_price(lang, r['six_months'], r.get('six_months_link'), p['members_start'])}</td><td data-label='{th[4]}'>{r.get('per_class', '').replace(' · ', '<br>')}</td><td data-label='{th[5]}'>{r['social_perk']}</td></tr>" for r in pr["memberships"]) +
             "</tbody></table></div>")
    intro = p["intro"]
    body = page_head(T[lang]["nav_prices"], intro) + price_quiz(lang) + f"""
<section class="sec"><div class="wrap">
  <div class="grid g4 price-ladder" style="padding-top:12px">{''.join(html)}</div>
  <p class="note-line">{p['note']}</p>
</div></section>
<section class="sec sec-soft" id="members"><div class="wrap">
  <div class="sec-title"><h2><span class="hl">{p['members_title']}</span></h2><p>{p['members_sub']}</p></div>
  {table}
</div></section>"""
    page(lang, "prices", f"{P('prices', lang)['meta_title']} | Lumos Latin", intro, body)


# ---------------------------------------------------------------- studios
def studios(lang):
    """All classes per studio, each in its own fold with a map."""
    t, p = T[lang], P("studios", lang)
    and_ = f" {t['and_']} "
    blocks = []
    for k in STUDIOS:
        s = STUDIOS[k]
        cs = sorted([c for c in CLASSES if c["studio"] == k], key=lambda c: (WEEKDAYS.index(c["day"]), c["time"]))
        maps = MAPS_LINK[k]
        dances = " · ".join(d.capitalize() for d in s["dances"])
        if s["beginners_only"]:
            dances += " · " + p["beginners_only"]
        days = and_.join(t["days_long"][d] for d in s["days"])
        count = f'{len(cs)} {p["classes_word"]}'
        rows = []
        for wd in s["days"]:
            rows.append(f'<li class="sd-day">{t["days_long"][wd].capitalize()}</li>')
            for c in [c for c in cs if c["day"] == wd]:
                d_, n_, m_, tt_ = c["try_"]
                # data-genre / data-level: the Bueno feed block in app.js matches its try-outs to this row
                rows.append(f"""<li data-class="{c['id']}" data-genre="{c['dance']}" data-level="{c['level']}"><div class="sd-time">{c['time']}–{c['end']}</div>
  <div class="sd-what"><b>{class_name(c)} · {level_name(lang, c)}</b><span>{teachers(lang, c)}</span>
  {f'<span class="sd-try">{p["tryout_label"]}: {t["days"][d_]} {n_} {MONTHS[lang][m_]}, {tt_}–{try_end(c)}</span>' if TRYOUTS else ''}</div>
  <a class="btn btn-sm btn-pink" href="{book_url(c, lang)}">{t['cta']}</a></li>""")
            # timed extra rows (e.g. a free social), without a sign-up button
            for x in notices("studios", lang, "row"):
                if x["studio"] == k and x["day"] == wd:
                    rows.append(f"""<li class="sd-social"><div class="sd-time">{x['time']}</div>
  <div class="sd-what"><b>{x['title']}</b><span>{x['text']}</span>
  <span class="sd-free">{x['note']}</span></div></li>""")
        if s["workshops_only"]:
            # a studio without weekly classes lists its upcoming workshops from the events
            ws = [e for e in upcoming_events() if e["place"].startswith(s["name"])]
            rows.append(f'<li class="sd-day">{p["workshops_heading"]}</li>')
            for e in ws:
                rows.append(f"""<li><div class="sd-time">{e['date'].day} {MONTHS[lang][e['date'].month]}</div>
  <div class="sd-what"><b>{tr(e['title'], lang)}</b><span>{e['time']}</span></div>
  <a class="btn btn-sm btn-pink" href="{e['link']}">{tr(e['btn'], lang)}</a></li>""")
            if not ws:
                rows.append(f'<li class="sd-empty">{p["no_workshops"]}</li>')
            days = ""
            dances, count = p["workshops_tags"], p["no_weekly_classes"]
        sticker = "".join(f'<span class="fun-sticker fun-sticker--sm">{x["text"]}</span>'
                          for x in notices("studios", lang, "sticker") if x["studio"] == k)
        # all folds open, so every studio shows its map; they can still be folded
        blocks.append(f"""<details class="studio-fold" data-studio="{k}" data-locs="{s['locs']}" open>
  <summary><span class="pin-num">{s['pin']}</span><span class="sf-main"><b>{s['name']}</b>{sticker}<span>{s['addr']}, Amsterdam {area(lang, s)}{' · ' + days if days else ''}</span><span class="sf-tags">{dances} · {count}</span></span></summary>
  <div class="sf-body">{studio_map(lang, k)}<ul class="sd-list sd-feed" hidden></ul><ul class="sd-list sd-typed">{''.join(rows)}</ul>
  <a class="btn btn-sm" href="{maps}" target="_blank" rel="noopener">{p['directions_button']}</a></div>
</details>""")
    intro = p["intro"]
    body = page_head(t["studios_word"], intro) + f"""
<section class="sec"><div class="wrap">
  <div class="studio-page studio-page--maps" id="classes">
    <div class="studio-folds">{''.join(blocks)}</div>
  </div>
</div></section>"""
    page(lang, "studios", f"{P('studios', lang)['meta_title']} | Lumos Latin", intro, body)


# ---------------------------------------------------------------- contact
def contact(lang):
    p = P("contact", lang)
    intro = p["intro"]
    cards = [(p["whatsapp_title"], WA, PHONE, p["whatsapp_note"]),
             (p["phone_title"], TEL, PHONE, ""),
             (p["email_title"], f"mailto:{EMAIL}", EMAIL, "")]
    c_html = "".join(f'<div class="card contact-card"><h2 class="card-h">{h}</h2><a class="big" href="{href}">{v}</a>{f"<p class=muted>{n}</p>" if n else ""}</div>'
                     for h, href, v, n in cards)
    f_html = "".join(f"<details><summary>{q}</summary><p>{a}</p></details>" for q, a in faq_items(lang))
    title = T[lang]["contact_word"]
    body = page_head(title, intro) + f"""
<section class="sec"><div class="wrap">
  <div class="grid g3">{c_html}</div>
</div></section>
<section class="sec sec-soft"><div class="wrap" style="max-width:820px">
  <div class="sec-title"><h2><span class="hl">{p['faq_title']}</span></h2></div>
  <div class="faq">{f_html}</div>
</div></section>"""
    page(lang, "contact", f"{P('contact', lang)['meta_title']} | Lumos Latin", intro, body)


# ---------------------------------------------------------------- privacy
def privacy(lang):
    """The privacy and cookie policy, taken word for word from the old lumoslatin.nl/privacy-policy (English),
    with a Dutch translation. Each section: heading, an optional text, an optional list of items, an optional note."""
    p = P("privacy", lang)

    def item(x):
        x = x.strip()
        if "@" in x and " " not in x:
            return f'<a class="link" href="mailto:{x}">{x}</a>'
        if x.startswith("+") and x.replace(" ", "")[1:].isdigit():
            return f'<a class="link" href="tel:{x.replace(" ", "")}">{x}</a>'
        return x

    secs = []
    for s in p["sections"]:
        h = f'<h2>{s["heading"]}</h2>'
        t = f'<p>{s["text"]}</p>' if s.get("text") else ""
        li = "".join(f"<li>{item(x)}</li>" for x in s.get("items", []) if x)
        ul = f"<ul>{li}</ul>" if li else ""
        n = f'<p>{s["note"]}</p>' if s.get("note") else ""
        secs.append(f'<section class="policy-sec">{h}{t}{ul}{n}</section>')
    body = page_head(p["title"], p["intro"]) + f"""
<section class="sec"><div class="wrap policy" style="max-width:820px">{"".join(secs)}</div></section>"""
    page(lang, "privacy", f"{p['title']} | Lumos Latin", p["intro"], body)


def root_files():
    with open(os.path.join(ROOT, "robots.txt"), "w", encoding="utf-8") as f:
        f.write(f"User-agent: *\nDisallow:{' /' if HIDDEN else ''}\n\nSitemap: {SITE}/sitemap.xml\n")
    # every page written by page() this run (root index.html is a copy of /en/ and is left out)
    rows = []
    for loc, alts in SITEMAP:
        links = "".join(f'\n    <xhtml:link rel="alternate" hreflang="{h}" href="{esc(SITE + alts[h])}"/>' for h in ("en", "nl"))
        links += f'\n    <xhtml:link rel="alternate" hreflang="x-default" href="{esc(SITE + alts["en"])}"/>'
        rows.append(f"  <url>\n    <loc>{esc(SITE + loc)}</loc>\n    <lastmod>{datetime.date.today().isoformat()}</lastmod>{links}\n  </url>")
    with open(os.path.join(ROOT, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n'
                '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
                + "\n".join(rows) + "\n</urlset>\n")
    # Old lumoslatin.nl addresses (the current site, English) go to the matching new page for good (308),
    # so Google keeps the rankings at launch. Both with and without the slash, because trailingSlash
    # would otherwise add it first.
    redirects = [{"source": src, "destination": f"/en/{SLUGS['en'][page]}/" if SLUGS["en"][page] else "/en/", "permanent": True}
                 for old, page in OLD_URLS.items() for src in (f"/{old}", f"/{old}/")]
    # /en/start/ and /nl/start/ only hold the answer pages: the folder itself opens the questions on the home page
    redirects += [{"source": src, "destination": f"/{lang}/#start", "permanent": True}
                  for lang in ("en", "nl") for src in (f"/{lang}/start", f"/{lang}/start/")]
    # browsers that ask for /favicon.ico get the same icon the pages name
    redirects.append({"source": "/favicon.ico", "destination": "/assets/lumos-gem-icon.svg", "permanent": True})
    vercel = {"cleanUrls": False, "trailingSlash": True, "redirects": redirects}
    if HIDDEN:
        vercel["headers"] = [{"source": "/(.*)", "headers": [{"key": "X-Robots-Tag", "value": "noindex, nofollow, noarchive"}]}]
    with open(os.path.join(ROOT, "vercel.json"), "w", encoding="utf-8") as f:
        json.dump(vercel, f, indent=2)
        f.write("\n")


def main():
    for d in ("nl", "en", "l2", "l3", "l4"):
        if os.path.isdir(os.path.join(ROOT, d)):
            shutil.rmtree(os.path.join(ROOT, d))
    for old in ("l2.css", "l3.css", "l4.css"):
        if os.path.exists(os.path.join(ROOT, "assets", old)):
            os.remove(os.path.join(ROOT, "assets", old))
    os.makedirs(os.path.join(ROOT, "assets"), exist_ok=True)
    write_data_js()
    og_image()
    for lang in ("en", "nl"):
        home(lang)
        for a in ANSWERS:
            home(lang, a)
        for d in ("salsa", "bachata", "reggaeton"):
            dance_page(lang, d)
        schedule(lang)
        prices(lang)
        studios(lang)
        events(lang)
        teachers_page(lang)
        contact(lang)
        privacy(lang)
    root_files()  # after the pages, so the sitemap lists them all
    print("written to", os.path.normpath(ROOT))


if __name__ == "__main__":
    main()
