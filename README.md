# Lumos Latin website

The new lumoslatin.nl: plain HTML, CSS and a little JavaScript, hosted on Vercel.
This note says how the site is built, where to change things, and what to do at launch.

## What is in the repo

- `prototype/` is the site as it is deployed: `en/` and `nl/` pages, `assets/` (style.css, app.js, photos, videos, icons), `robots.txt`, `sitemap.xml`, `vercel.json`.
- `content/` holds every text, class, price, event and studio as JSON files, English and Dutch side by side.
- `tools/build_prototype.py` is the generator. It reads `content/` and writes all the English and Dutch pages from it; the layout, CSS hooks, redirects and sitemap stay in the script. Run it with `python tools/build_prototype.py` (Python 3.8 or newer, Pillow is the only extra package). It rewrites `prototype/en/`, `prototype/nl/`, `prototype/index.html`, `assets/data.js`, `sitemap.xml` and `vercel.json`. `python tools/check_build.py` rebuilds and says whether `prototype/` changed.

## Changing texts, classes and events

Edit the JSON files in `content/`, run `python tools/build_prototype.py` and push. The HTML files are output, so a change made there by hand is lost at the next run. Texts in both languages are written as `{"en": "...", "nl": "..."}`; dates are `YYYY-MM-DD`.

- Weekly classes: one file per class in `content/classes/` (day, time, dance, level, studio, teachers, try-out date and time, Bueno id of the try-out).
- Events (socials, workshops, game nights): one file per event in `content/events/`. Past events move to "Earlier" on the events page by themselves at the next build.
- News cards on the home page: one file per card in `content/news/`, shown in the order of their `date`.
- Studios: one file per studio in `content/studios/` (address, Google Maps link and map coordinates, Bueno location ids). Teachers: `content/teachers/`.
- Prices, memberships and the reggaeton price strip: `content/prices.json`. Reviews: `content/reviews.json`. Questions on the contact page: `content/faq.json`.
- Page texts: `content/pages/`, one file per page, plus `shared.json` (menu, footer, short labels), `dances.json` (texts all three dance pages share), `finder.json` (the two questions on the home page) and `start.json` (the answer pages).
- Phone, WhatsApp, email, social links, the site address, course dates and the look settings: `content/settings.json`.

Events, news cards, the "More info" extras on the answer pages and the `notices` on a page (such as the try-out line at the top of the home page, or the sticker and the free social on a studio card) can have a `show_from` and a `hide_after` date. The build keeps an item only from the first date up to and including the second; an empty field means no limit. An event or news card always needs its own `date`. If a date or a text is not right, the build stops and names the file and the field. Dates only change the site when it is rebuilt, so rebuild after a date has passed. To see the site as it will be on another day, run `python tools/build_prototype.py --today 2026-11-05`, and run it again without `--today` before you push.

The Bueno feed in `assets/app.js` (the "Bueno feed" block) fills the next try-out date and booking link on studio cards and start pages from Bueno's public schedule for the coming 7 days. Everything else on the site is typed text, so a change in Bueno does not change the site by itself.

## Editing screen

`prototype/admin/` is an editing screen for the files in `content/` (Sveltia CMS, loaded from a CDN at a fixed version). It lives at `/admin/` on the site. Each kind of content has its own list (Events, News, Classes, Teachers, Studios, Pages, Settings, Prices, Reviews, Questions), every text has an English and a Dutch box, and dates are picked from a calendar. What it can edit, the labels and the hints are all in `prototype/admin/config.yml`. Saving writes the JSON file in `content/`; the pages still have to be built from it with the generator, as above.

To try it on your own computer, serve `prototype/` (for example `python -m http.server 8420 --bind 127.0.0.1` inside it), open http://127.0.0.1:8420/admin/ in Chrome or Edge and choose "Work with Local Repository". When asked, pick the root folder of this repo. Changes are then written straight to the files on disk, and `git diff` shows them.

On the real site, people sign in with a GitHub account that has write access to this repo. The sign-in goes through a small login service (sveltia-cms-auth) on the Lumos Cloudflare account, worker `lumos-cms-login`, using the GitHub OAuth app "Lumos Latin editing screen". Its address is `base_url` in `config.yml`. A save writes to `content/` on `main`; the GitHub action `.github/workflows/rebuild-site.yml` then rebuilds `prototype/`, commits it, and calls the Vercel deploy hook kept in the repo secret `VERCEL_DEPLOY_HOOK` (Vercel's free plan does not publish commits from anyone but the account owner, so the hook is what publishes a save). The same action runs every night, so dated items appear and disappear on time.

## Going live

1. In `content/settings.json` set `"site_url": "https://www.lumoslatin.nl"` (with www: that is the address the domain settles on, so canonicals and sitemap must say the same). Canonicals, hreflang tags, Open Graph tags, the JSON-LD and the sitemap all take their addresses from it.
2. That one setting also decides the rest. With an address on `vercel.app` the build makes the hidden copy: a `noindex` tag on every page, `Disallow: /` in robots.txt, and an `X-Robots-Tag` header in `vercel.json`. With any other address the build leaves all three out, so there is nothing else to remove.
3. Run the generator and push.

## SEO

- Every page has a self canonical, `hreflang` for en, nl and x-default, Open Graph and Twitter tags, and a share image at `/assets/og-image.jpg`.
- The home pages carry DanceSchool JSON-LD (phone, email, the three studio addresses, the social links). The events pages carry Event JSON-LD for upcoming events.
- `sitemap.xml` lists the 22 pages. The answer pages under `/start/` are left out on purpose and canonical to their home page.
- Redirects from the old addresses are in `vercel.json` (generated from `OLD_URLS` in the generator): `/salsa`, `/bachata`, `/reggaeton`, `/schedule`, `/prices`, `/locations` (now studios), `/events`, `/contact`, `/privacy-policy`, `/courses` (to prices), `/workshops` (to events) and `/blog` (to the home page) go to the matching `/en/` page for good, so the current rankings carry over. The privacy policy is its own page now (`/en/privacy/`, `/nl/privacy/`), with its text in `content/pages/privacy.json`.
- After launch: in Google Search Console, verify lumoslatin.nl (DNS record or the Vercel integration) and submit `https://www.lumoslatin.nl/sitemap.xml`. If the school already has a Search Console property, keep it and ask for access.

## Picking the highlight shape, colours and question background

Four settings in `content/settings.json` decide the look. Each one is written on the `<html>` tag of every page, and `style.css` has the CSS for every option, so nothing else needs to change.

- `hl_shape`: `A`, `B` or `C`. The stroke behind the highlighted words ("you shine!"). A has flat ends, B and C are rounder. Now `A`.
- `hl_color`: `Pink`, `Purple`, `Lilac`, `Rose`, `Orchid` or `Moving`. The colour of that stroke and of the pink accents. Moving drifts slowly from pink to purple and back. Now `Pink`.
- `btn_color`: `Pink` or `Purple`. Every button. Now `Pink`.
- `q_bg`: `White` or `Yellow`. The background of the question card on the home page. Now `White`.

Change the word, run `python tools/build_prototype.py`, done.

To compare the options in the browser, run `python tools/build_prototype.py --switches`. That puts small switches under the title on the home and start pages (drawn by `assets/feedback.js`). A pick there only lasts for the browser tab. Run the plain build again before you push, so the live site has no switches.
