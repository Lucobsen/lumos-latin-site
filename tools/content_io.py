"""Reads and writes the JSON files in content/.

save() always writes the same layout: indent 2, UTF-8, a trailing newline and the keys in
KEY_ORDER order (keys not listed follow alphabetically), so saving a file twice changes nothing.
"""
import datetime
import json
import os

CONTENT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "content")

KEY_ORDER = []  # filled at the end of this file


def ordered(v):
    if isinstance(v, dict):
        rank = {k: i for i, k in enumerate(KEY_ORDER)}
        keys = sorted(v, key=lambda k: (rank.get(k, len(rank)), k))
        return {k: ordered(v[k]) for k in keys}
    if isinstance(v, list):
        return [ordered(x) for x in v]
    return v


def dumps(data):
    return json.dumps(ordered(data), indent=2, ensure_ascii=False) + "\n"


def path(*parts):
    return os.path.join(CONTENT, *parts)


def where(*parts):
    """A content file as it is named in messages, e.g. content/events/x.json."""
    return "/".join(("content",) + parts)


def load(*parts):
    with open(path(*parts), encoding="utf-8") as f:
        try:
            return json.load(f)
        except ValueError as e:
            raise SystemExit(f"{where(*parts)}: not valid JSON ({e})")


def load_dir(name):
    """Every item of a list folder, e.g. content/events/*.json, with its file name as "slug"."""
    folder = path(name)
    items = []
    for fn in sorted(os.listdir(folder)):
        if fn.endswith(".json"):
            item = load(name, fn)
            item["slug"] = fn[:-5]
            items.append(item)
    return items


def check(data, where, required=(), dates=(), plain=()):
    """Stops the build with a short message naming the file and field when content is wrong:
    required dates missing or not YYYY-MM-DD, optional dates not YYYY-MM-DD, a text object
    without both "en" and "nl", or a plain-text field holding "<" or a double quote."""
    def stop(field, msg):
        raise SystemExit(f"{where}: {field} {msg}")

    def walk(v, field):
        if isinstance(v, dict):
            if ("en" in v or "nl" in v) and not ({"en", "nl"} <= set(v) and all(isinstance(v[k], str) for k in ("en", "nl"))):
                stop(field, 'needs both "en" and "nl" texts')
            for k, x in v.items():
                walk(x, f"{field}.{k}" if field else k)
        elif isinstance(v, list):
            for i, x in enumerate(v):
                walk(x, f"{field}[{i}]")

    walk(data, "")
    for f in tuple(required) + tuple(dates):
        v = data.get(f, "")
        if not v and f in required:
            stop(f, "is required (YYYY-MM-DD)")
        if v:
            try:
                datetime.date.fromisoformat(v)
            except (TypeError, ValueError):
                stop(f, f"{v!r} must be YYYY-MM-DD")
    for f in plain:
        v = data.get(f, "")
        for s in (v.values() if isinstance(v, dict) else [v]):
            if isinstance(s, str) and ("<" in s or '"' in s):
                stop(f, 'must not contain "<" or a double quote')
    return data


def save(data, *parts):
    p = path(*parts)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write(dumps(data))


def all_files():
    for d, _, files in os.walk(CONTENT):
        for fn in sorted(files):
            if fn.endswith(".json"):
                yield os.path.join(d, fn)


KEY_ORDER = [
    # languages, weekdays, finder options
    "en", "nl", "mon", "tue", "wed", "thu", "fri", "sat", "sun",
    "never", "few", "regular", "salsa", "bachata", "reggaeton", "no", "yes", "unsure",
    # what an item is and when it shows
    "id", "key", "slug", "order", "pin", "kind", "eyebrow",
    "date", "show_from", "hide_after", "day", "time", "end", "dance", "level", "studio", "teachers",
    "tryout_date", "tryout_time", "bueno_tryout_id",
    # names and texts
    "name", "meta_title", "meta_description", "title", "place", "when", "heading", "question", "answer",
    "role", "bio", "quote", "label", "intro", "text", "items", "note",
    "address", "area", "dances", "days", "beginners_only", "workshops_only",
    "maps_link", "map_coordinates", "bueno_location_ids",
    "price", "per", "what", "detail", "line", "ticks", "classes_a_week", "monthly", "monthly_link", "six_months", "six_months_link", "social_perk",
    "image", "badge", "photo", "big", "sticker", "button", "button_label", "button_link", "button_style", "buttons", "link",
    "classes", "cta", "second_label", "second_link", "extras",
    "who", "learn", "sub",
    # settings
    "site_url", "founded_year", "phone", "tel_link", "whatsapp_link", "email",
    "instagram", "tiktok", "facebook", "book_fallback", "buy_link",
    "hl_shape", "hl_color", "btn_color", "q_bg", "gtm_id", "google_rating", "review_count",
    "course_start", "course_end",
    # shared labels
    "nav_schedule", "nav_prices", "nav_studios", "nav_events", "nav_teachers", "nav_dances", "nav_contact",
    "menu", "days_long", "and", "every", "date_to", "teacher_tbc", "no_levels", "tryout_label", "then_course", "then_drop_in",
    "per_class","footer_about", "footer_contact", "footer_dances", "footer_classes",
    "footer_school", "footer_follow", "rights", "privacy_label",
    # home
    "dances_line", "hero_sub", "hero_sub2", "next_up_label", "notices", "trust_reviews", "trust_studios",
    "hero_note_label", "hero_note", "browse_link", "news_title", "news_all_link", "news_first_label",
    "dances_title", "dances_sub", "dance_lines", "more_about", "reviews_title", "reviews_line",
    "studios_title", "studios_text", "studios_button",
    # finder
    "step", "q1", "q1_opts", "q1_subs", "q1_reggaeton", "q2", "q2_opts", "q2_subs", "one_more", "back",
    "check", "check_opts", "compare_title", "compare", "compare_q", "restart", "restart_top", "welcome",
    "your_start", "your_next", "your_classes",
    # start pages
    "answers", "beginner_salsa", "beginner_bachata", "improver_salsa", "improver_bachata",
    "dancer_salsa", "dancer_bachata", "between_salsa", "between_bachata",
    "night_extras", "dancer_extras", "you_if", "salsa_1", "salsa_2", "salsa_3", "bachata_1", "bachata_2",
    "between_link", "first_class_title", "first_class_sub", "first_class_items",
    # dance pages
    "schedule_button", "prices_button", "classes_title", "classes_sub", "table_headings", "class", "tryout",
    "then", "course_line", "drop_in_line", "levels_title", "about_title", "you_if_label", "back_to_back",
    "levels", "card_title", "card_who", "card_learn", "tip_label", "finder_button",
    "price_title", "price_sub", "worries_title", "worries_sub", "worries", "cta_title",
    # other pages
    "filter_all", "filter_type", "filter_dance", "filter_level", "filter_studio",
    "type_tryouts", "type_courses", "type_events", "open_in_bueno",
    "classes_word", "workshops_heading", "workshops_tags", "no_weekly_classes",
    "no_workshops", "map_title", "map_caption", "directions_button",
    "first_label", "kinds", "empty_text", "earlier", "back_label", "map_hint",
    "whatsapp_title", "whatsapp_note", "phone_title", "email_title", "faq_title",
    "cards", "members_title", "members_sub", "memberships", "members_button", "members_start", "reggaeton_strip",
    # prices questionnaire
    "quiz", "placeholder", "best_for_you", "clear", "options", "value", "results",
    "tryout_single", "punch_short", "punch_months", "course_months", "course_then_member",
    "member_extra_months", "member_extra_live", "member_essential",
    "reviews", "questions",
    # privacy page
    "sections",
    # try-out switch, price per class, events up next
    "tryouts_on", "cta_off", "per_class", "alt", "pick", "empty_texts", "up_next_label", "lang",
]
