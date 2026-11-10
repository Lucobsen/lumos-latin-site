/* Lumos Latin prototype: menu, dances dropdown, question flow, schedule filter. */
(function () {
  var D = window.LUMOS;
  var lang = document.documentElement.lang;
  var L = D[lang];
  var STORE = "lumos-answer";
  var BASE = document.documentElement.getAttribute("data-base") || "";

  function store(v) {
    try { if (v) localStorage.setItem(STORE, v); else localStorage.removeItem(STORE); } catch (e) {}
  }
  function stored() {
    try { return localStorage.getItem(STORE); } catch (e) { return null; }
  }
  function h(s) {
    return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; });
  }

  /* ---------- home video loop: plays only while it is on screen ---------- */
  /* the loop sits in the hero tile with autoplay, so it also runs without JavaScript */
  var still = window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches;
  document.querySelectorAll("video.autoloop").forEach(function (v) {
    /* people who turned motion off get the poster and a play button */
    if (still) { v.autoplay = false; v.pause(); v.setAttribute("controls", ""); return; }
    var play = function () { var p = v.play(); if (p && p.catch) p.catch(function () {}); };
    if (!("IntersectionObserver" in window)) { play(); return; }
    new IntersectionObserver(function (es) {
      es.forEach(function (e) { if (e.isIntersecting) play(); else v.pause(); });
    }, { rootMargin: "200px" }).observe(v);
  });

  /* ---------- menu and dropdown ---------- */
  var menuBtn = document.querySelector(".menu-btn");
  var nav = document.getElementById("nav");
  if (menuBtn && nav) {
    menuBtn.addEventListener("click", function () {
      var open = nav.classList.toggle("open");
      menuBtn.setAttribute("aria-expanded", open);
    });
    nav.addEventListener("click", function (e) {
      if (e.target.closest("a")) { nav.classList.remove("open"); menuBtn.setAttribute("aria-expanded", false); }
    });
  }
  document.querySelectorAll(".dd-btn").forEach(function (b) {
    b.addEventListener("click", function () {
      var open = b.parentElement.classList.toggle("open");
      b.setAttribute("aria-expanded", open);
    });
  });
  document.addEventListener("click", function (e) {
    document.querySelectorAll(".dd.open").forEach(function (dd) {
      if (!dd.contains(e.target)) { dd.classList.remove("open"); dd.querySelector(".dd-btn").setAttribute("aria-expanded", false); }
    });
  });

  /* ---------- schedule filter: one choice per row (dance, level, studio), rows combine ---------- */
  var sched = document.getElementById("sched");
  if (sched) {
    var rowsEl = document.querySelectorAll(".chip-row");
    var emptyMsg = document.getElementById("sched-empty");
    var pick = {};
    var apply = function () {
      var shown = 0;
      rowsEl.forEach(function (r) {
        var v = pick[r.dataset.group] || "all";
        r.querySelectorAll(".chip").forEach(function (c) { var on = c.dataset.filter === v; c.classList.toggle("on", on); c.setAttribute("aria-pressed", on); });
      });
      sched.querySelectorAll("li").forEach(function (li) {
        var tags = li.dataset.tags.split(" ");
        var ok = Object.keys(pick).every(function (g) { return pick[g] === "all" || tags.indexOf(pick[g]) > -1; });
        li.hidden = !ok;
        if (ok) shown++;
      });
      emptyMsg.hidden = shown > 0;
      var u = new URL(location.href);
      u.searchParams.delete("filter");
      Object.keys(pick).forEach(function (g) { if (pick[g] !== "all") u.searchParams.append("filter", pick[g]); });
      history.replaceState(null, "", u.pathname + u.search);
    };
    rowsEl.forEach(function (r) {
      r.addEventListener("click", function (e) {
        var c = e.target.closest(".chip");
        if (!c) return;
        pick[r.dataset.group] = c.dataset.filter;
        apply();
      });
    });
    new URLSearchParams(location.search).getAll("filter").forEach(function (f) {
      rowsEl.forEach(function (r) { if (r.querySelector('[data-filter="' + f + '"]')) pick[r.dataset.group] = f; });
    });
    apply();
  }

  /* ---------- Bueno frame filter: chips reload the frame with Bueno's own filter ids ---------- */
  var bframe = document.getElementById("bueno-schedule");
  var bfilters = document.getElementById("bueno-filters");
  if (bframe && bfilters) {
    var brows = bfilters.querySelectorAll(".chip-row");
    var bpick = {};
    var bapply = function () {
      var u = new URL(bframe.getAttribute("src"));
      var page = new URL(location.href);
      page.searchParams.delete("filter");
      brows.forEach(function (r) {
        var key = bpick[r.dataset.param] || "all";
        var ids = "";
        r.querySelectorAll(".chip").forEach(function (c) {
          var on = c.dataset.filter === key;
          c.classList.toggle("on", on);
          c.setAttribute("aria-pressed", on);
          if (on) ids = c.dataset.ids;
        });
        u.searchParams.set(r.dataset.param, ids);
        if (key !== "all") page.searchParams.append("filter", key);
      });
      if (u.href !== bframe.src) bframe.src = u.href;
      history.replaceState(null, "", page.pathname + page.search);
    };
    brows.forEach(function (r) {
      r.addEventListener("click", function (e) {
        var c = e.target.closest(".chip");
        if (!c) return;
        bpick[r.dataset.param] = c.dataset.filter;
        bapply();
      });
    });
    new URLSearchParams(location.search).getAll("filter").forEach(function (f) {
      brows.forEach(function (r) { if (r.querySelector('[data-filter="' + f + '"]')) bpick[r.dataset.param] = f; });
    });
    bapply();
  }

  /* ---------- question flow ---------- */
  var card = document.getElementById("flow");
  if (!card) return;
  var F = L.flow;
  var byId = {};
  D.classes.forEach(function (c) { byId[c.id] = c; });

  function slugFor(s) {
    if (s.dance === "reggaeton") return "reggaeton";
    if (s.level === "never") return "beginner-" + s.dance;
    if (s.level === "few") return (s.check === "yes" ? "improver-" : s.check === "unsure" ? "between-" : "beginner-") + s.dance;
    return "dancer-" + s.dance;
  }
  /* studio area in the page's language ("Oost" / "East"); the day tiles say "West - De Veemvloer" */
  function areaOf(k) { return (lang === "en" && D.areas_en ? D.areas_en[k] : D.areas[k]) || ""; }
  function teachers(c) { return c.teachers.length ? c.teachers.join(" " + L.and_ + " ") : L.tbc; }
  function classRow(c, youIf) {
    var name = c.dance === "reggaeton" ? "Reggaeton drop-in" : c.dance.charAt(0).toUpperCase() + c.dance.slice(1) + " " + c.level;
    var lvl = c.level ? D.levels[c.level] : L.no_levels;
    var yi = youIf && c["yi_" + lang] ? '<span class="yi">' + h(c["yi_" + lang]) + "</span>" : "";
    var studio = D.studios[c.studio] + ", " + D.addrs[c.studio] + " (" + areaOf(c.studio) + ")";
    var after = c.dance === "reggaeton" ? L.then_drop : L.then_course;
    return '<li id="c-' + c.id + '"><div class="when"><small>' + h(L.try_word) + "</small>" + h(c["try_day_" + lang]) + "<span>" + h(c.try_time) + "</span></div>" +
      '<div class="what"><b>' + h(name) + " · " + h(lvl) + "</b>" + yi + "<span>" + h(studio) + " · " + h(teachers(c)) + "</span>" +
      '<span class="course">' + h(after) + ": " + h(c["course_" + lang]) + "</span>" + (c.level > 1 ? '<span class="course">' + h(L.per_class) + "</span>" : "") + "</div>" +
      '<div class="row-book"><a class="btn btn-sm btn-pink" href="' + (c.book || L.book || D.book) + '">' + h(L.book_row) + "</a></div></li>";
  }

  /* answer: one tile per try-out day; only the picked day shows its details */
  function dayTile(c, i) {
    var d = c["try_day_" + lang].split(" ");
    return '<button type="button" class="day' + (i === 0 ? " on" : "") + '" data-pick="' + i + '" aria-pressed="' + (i === 0) + '">' +
      "<small>" + h(d[0]) + "</small><b>" + h(d.slice(1).join(" ")) + "</b><span>" + h(c.try_time.split(/[–-]/)[0]) + "</span><em>" + h(areaOf(c.studio) + " - " + D.studios[c.studio]) + "</em></button>";
  }
  function dayDetail(c, i, youIf) {
    var name = c.dance === "reggaeton" ? "Reggaeton drop-in" : c.dance.charAt(0).toUpperCase() + c.dance.slice(1) + " " + c.level;
    var lvl = c.level ? D.levels[c.level] : L.no_levels;
    var yi = youIf && c["yi_" + lang] ? '<p class="yi">' + h(c["yi_" + lang]) + "</p>" : "";
    var after = c.dance === "reggaeton" ? L.then_drop : L.then_course;
    return '<div class="day-detail" data-detail="' + i + '"' + (i === 0 ? "" : " hidden") + ">" +
      '<p class="dd-name"><b>' + h(name) + " · " + h(lvl) + "</b> · " + h(c["try_day_" + lang]) + ", " + h(c.try_time) + "</p>" + yi +
      '<p class="dd-where">' + ICON_PIN + h(D.studios[c.studio]) + ", " + h(D.addrs[c.studio]) + "</p>" +
      '<p class="dd-who">' + ICON_USER + h(teachers(c)) + "</p>" +
      '<p class="dd-after">' + h(after) + ": " + h(c["course_" + lang]) + (c.level > 1 ? " " + h(L.per_class) : "") + "</p>" +
      '<a class="btn btn-pink" href="' + (c.book || L.book || D.book) + '">' + h(L.book_row) + "</a></div>";
  }
  var ICON_PIN = '<svg class="ico" aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 10c0 4.993-5.539 10.193-7.399 11.799a1 1 0 0 1-1.202 0C9.539 20.193 4 14.993 4 10a8 8 0 0 1 16 0"/><circle cx="12" cy="10" r="3"/></svg>';
  var ICON_USER = '<svg class="ico" aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/></svg>';
  function shortTick(t) { return t.split(/: |\. /)[0].replace(/\.$/, ""); }
  function firstLine(t) { var m = t.match(/^.*?[.!](\s|$)/); return m ? m[0].trim() : t; }

  function opts(map, attr, subs, cls) {
    return '<div class="q-opts' + (cls ? " " + cls : "") + '">' + Object.keys(map).map(function (k) {
      var sub = subs && subs[k] ? "<small>" + h(subs[k]) + "</small>" : "";
      return '<button class="q-opt" type="button" data-' + attr + '="' + k + '"><span>' + h(map[k]) + sub + "</span></button>";
    }).join("") + "</div>";
  }
  function back() { return '<button class="q-back" type="button" data-back>&larr; ' + h(F.back) + "</button>"; }

  function render(s, focus) {
    var html = "";
    if (s.step === "level") {
      html = '<div class="q-step">' + h(F.step.replace("{n}", 1)) + "</div><h2 class=\"q\" tabindex=\"-1\">" + h(F.q1) + "</h2>" + opts(F.q1_opts, "level", F.q1_subs);
      /* Reggaeton straight away, no level question */
      if (F.q1_reggaeton) html = html.replace(/<\/div>$/, '<button class="q-opt q-opt-reggaeton" type="button" data-dance="reggaeton"><span>' + h(F.q1_reggaeton[0]) + "<small>" + h(F.q1_reggaeton[1]) + "</small></span></button></div>");
    } else if (s.step === "dance") {
      html = '<div class="q-step"><span>' + h(F.step.replace("{n}", 2)) + "</span>" + back() + '</div><h2 class="q" tabindex="-1">' + h(F.q2) + "</h2>" +
        opts(F.q2_opts, "dance", F.q2_subs, "cols-2");
    } else if (s.step === "compare") {
      var cols = ["salsa", "bachata"].map(function (d) {
        return "<div><h3>" + d.charAt(0).toUpperCase() + d.slice(1) + "</h3><ul>" + F.compare[d].map(function (x) { return "<li>" + h(x) + "</li>"; }).join("") + "</ul></div>";
      }).join("");
      var three = { salsa: F.q2_opts.salsa, bachata: F.q2_opts.bachata, reggaeton: F.q2_opts.reggaeton };
      html = '<div class="q-step"><span>' + h(F.step.replace("{n}", 2)) + "</span>" + back() + '</div><h2 class="q" tabindex="-1">' + h(F.compare_title) + "</h2>" +
        '<div class="compare">' + cols + '</div><p class="q-note"><b>' + h(F.compare_q) + "</b></p>" + opts(three, "dance", F.q2_subs);
    } else if (s.step === "check") {
      html = '<div class="q-step"><span>' + h(F.one_more) + "</span>" + back() + '</div><h2 class="q" tabindex="-1">' + h(F.check[s.dance] || F.check.salsa) + "</h2>" + opts(F.check_opts, "check");
    } else {
      var a = L.answers[s.slug];
      var list = a.classes.slice().sort(function (x, y) { var p = byId[x].try_, q = byId[y].try_; return (p[2] - q[2]) || (p[1] - q[1]) || (p[3] < q[3] ? -1 : 1); }).map(function (id) { return byId[id]; });
      var youIf = list.length > 1 && /^(dancer|improver)/.test(s.slug);
      var more = (a.tip ? '<div class="tip">' + h(a.tip) + "</div>" : "") +
        a.extras.map(function (x) { return '<div class="extra"><b>' + h(x[0]) + "</b>" + h(x[1]) + "</div>"; }).join("") +
        '<div class="answer-actions"><a class="' + (/^http/.test(a.second.href) ? "btn" : "link") + '" href="' + (/^http/.test(a.second.href) ? "" : BASE) + a.second.href + '">' + h(a.second.label) + "</a>" +
        (L.between_link && /^beginner-(salsa|bachata)$/.test(s.slug) ? '<a class="link" href="' + BASE + L.urls.start + "between-" + s.slug.split("-")[1] + '/">' + h(L.between_link) + "</a>" : "") + "</div>";
      html = '<div class="answer answer-v2"><div class="q-step answer-top"><span>' + (s.welcome ? h(F.welcome) : "") + '</span><button class="q-back" type="button" data-restart>&larr; ' + h(F.restart_top) + "</button></div>" +
        '<h2 tabindex="-1">' + h(a.title) + "</h2>" +
        '<p class="answer-intro">' + h(firstLine(a.intro)) + "</p>" +
        (a.ticks.length ? '<ul class="chips-ok">' + a.ticks.map(function (t) { return '<li title="' + h(t) + '">' + h(shortTick(t)) + "</li>"; }).join("") + "</ul>" : "") +
        '<p class="pick-label">' + (lang === "nl" ? "Kies je dag" : "Pick your day") + "</p>" +
        '<div class="days">' + list.map(dayTile).join("") + "</div>" +
        list.map(function (c, i) { return dayDetail(c, i, youIf); }).join("") +
        '<details class="ans-more"><summary>' + (lang === "nl" ? "Meer info" : "More info") + "</summary>" + more + "</details></div>";
    }
    card.innerHTML = html;
    var hero = card.closest(".hero");
    if (hero) hero.classList.toggle("hero--answer", s.step === "answer");
    if (focus) {
      var hd = card.querySelector("[tabindex='-1']");
      if (hd) hd.focus({ preventScroll: true });
    }
  }

  function urlFor(s) {
    return s.step === "answer" ? BASE + L.urls.start + s.slug + "/" : null;
  }
  function go(s) {
    if (s.step === "answer") store(s.slug);
    var u = urlFor(s);
    if (!u && /\/start\//.test(location.pathname)) u = BASE + L.urls.home;
    history.pushState({ flow: s }, "", u || location.pathname + location.search);
    render(s, true);
  }
  function stateFromUrl() {
    var m = location.pathname.match(/\/start\/([a-z-]+)\/?$/);
    if (m && L.answers[m[1]]) return { step: "answer", slug: m[1] };
    return null;
  }

  var current = { step: "level" };
  card.addEventListener("click", function (e) {
    var b = e.target.closest("button");
    if (!b) return;
    if (b.dataset.pick) {
      card.querySelectorAll(".day").forEach(function (t) { var on = t === b; t.classList.toggle("on", on); t.setAttribute("aria-pressed", on); });
      card.querySelectorAll(".day-detail").forEach(function (d) { d.hidden = d.dataset.detail !== b.dataset.pick; });
      return;
    }
    var s = history.state && history.state.flow ? history.state.flow : current;
    var n = { level: s.level, dance: s.dance, check: s.check };
    if (b.hasAttribute("data-back")) { history.back(); return; }
    if (b.hasAttribute("data-restart")) { store(null); current = { step: "level" }; go(current); return; }
    if (b.dataset.level) { n.level = b.dataset.level; n.step = "dance"; }
    else if (b.dataset.dance) {
      n.dance = b.dataset.dance;
      if (n.dance === "unsure") { n.step = "compare"; n.dance = null; }
      else if (n.level === "few" && n.dance !== "reggaeton") n.step = "check";
      else { n.step = "answer"; n.slug = slugFor(n); }
    } else if (b.dataset.check) { n.check = b.dataset.check; n.step = "answer"; n.slug = slugFor(n); }
    else return;
    current = n;
    go(n);
  });

  window.addEventListener("popstate", function (e) {
    var s = e.state && e.state.flow ? e.state.flow : stateFromUrl() || { step: "level" };
    if (s.step === "answer") store(s.slug);
    current = s;
    render(s, true);
  });

  /* first paint: answer address, then remembered answer, then question 1 */
  var initial = card.dataset.answer;
  if (initial && L.answers[initial]) {
    current = { step: "answer", slug: initial };
    store(initial);
  } else {
    var mem = stored();
    if (mem && L.answers[mem]) current = { step: "answer", slug: mem, welcome: true };
  }
  history.replaceState({ flow: current }, "", location.pathname + location.search + location.hash);
  render(current, false);
  /* the Bueno feed (below) updated the try-out times: draw the open answer again, keeping the picked day */
  window.addEventListener("lumos:feed", function () {
    if (current.step !== "answer") return;
    var on = card.querySelector(".day.on");
    render(current, false);
    var b = on && card.querySelector('.day[data-pick="' + on.dataset.pick + '"]');
    if (b && b.dataset.pick !== "0") b.click();
  });
})();

/* ---------- Bueno feed.
   The studios page and the answer pages under /start/ show the typed times from the generator; this reads
   Bueno's public week feed once per page load, cached 30 minutes per tab, and puts
   Bueno's own try-out dates, times and booking links in their place. If the feed fails or takes longer than
   5 seconds, the typed times simply stay. Bueno's times are UTC; they are shown in Amsterdam time. ---------- */
(function () {
  var D = window.LUMOS;
  var folds = document.querySelectorAll(".studio-fold[data-locs]");
  var onAnswer = /\/start\/[a-z-]+\/?$/.test(location.pathname) || document.getElementById("flow");
  if (!D || (!folds.length && !onAnswer) || !window.fetch) return;
  var lang = document.documentElement.lang === "nl" ? "nl" : "en";
  var TZ = "Europe/Amsterdam";
  var DAYS = { en: ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"], nl: ["Zo", "Ma", "Di", "Wo", "Do", "Vr", "Za"] };
  var MON = { en: ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], nl: ["jan", "feb", "mrt", "apr", "mei", "jun", "jul", "aug", "sep", "okt", "nov", "dec"] };
  var LOC = { 1484: "veem", 1813: "veem", 1739: "flow", 1815: "ceintuur", 1814: "tg" };
  var DETAIL = "https://www.bueno.nu/webshop/school/764/schedule-detail/";

  function pad(n) { return (n < 10 ? "0" : "") + n; }
  function ddmmyyyy(d) { return pad(d.getUTCDate()) + "-" + pad(d.getUTCMonth() + 1) + "-" + d.getUTCFullYear(); }
  /* "26-10-2026 18:00" (UTC) -> the same moment in Amsterdam, as numbers */
  function local(s) {
    var m = /^(\d\d)-(\d\d)-(\d{4}) (\d\d):(\d\d)/.exec(s || "");
    if (!m) return null;
    var t = new Date(Date.UTC(+m[3], +m[2] - 1, +m[1], +m[4], +m[5]));
    var p = {};
    new Intl.DateTimeFormat("en-GB", { timeZone: TZ, year: "numeric", month: "numeric", day: "numeric", hour: "2-digit", minute: "2-digit", hourCycle: "h23", weekday: "short" })
      .formatToParts(t).forEach(function (x) { p[x.type] = x.value; });
    var wd = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].indexOf(p.weekday);
    return { t: t, y: +p.year, mo: +p.month, d: +p.day, wd: wd, hm: pad(+p.hour % 24) + ":" + p.minute };
  }
  function dayLabel(a) { return DAYS[lang][a.wd] + " " + a.d + " " + MON[lang][a.mo - 1]; }
  function levelNo(e) { var m = /^(\d)/.exec((e.level && e.level.level) || ""); return m ? +m[1] : 0; }
  function genre(e) { return ((e.genre && e.genre.genre) || "").trim().toLowerCase(); }

  function getWeek() {
    var now = new Date(), end = new Date(now.getTime() + 6 * 864e5);
    var url = "https://api.bueno.nu/webshop/school/764/schedule?calendarEntryId=0&startDateTime=" + ddmmyyyy(now) + "&endDateTime=" + ddmmyyyy(end);
    var key = "bueno-feed:" + ddmmyyyy(now);
    try {
      var c = JSON.parse(sessionStorage.getItem(key) || "null");
      if (c && Date.now() - c.at < 30 * 60 * 1000) return Promise.resolve(c.entries);
    } catch (e) {}
    var ctl = window.AbortController ? new AbortController() : null;
    var timer = setTimeout(function () { if (ctl) ctl.abort(); }, 5000);
    return fetch(url, ctl ? { signal: ctl.signal } : {}).then(function (r) {
      clearTimeout(timer);
      if (!r.ok) throw new Error(r.status);
      return r.json();
    }).then(function (d) {
      var entries = (d && d.calendarEntries) || [];
      try { sessionStorage.setItem(key, JSON.stringify({ at: Date.now(), entries: entries })); } catch (e) {}
      return entries;
    });
  }

  function apply(entries) {
    var list = entries.map(function (e) {
      return { e: e, a: local(e.startDateTime), b: local(e.endDateTime), studio: LOC[e.location && e.location.schoolLocationId], g: genre(e), lv: levelNo(e) };
    }).filter(function (x) { return x.a && x.b && x.studio; }).sort(function (x, y) { return x.a.t - y.a.t; });
    var used = [];
    /* answer pages: the classes the flow draws (window.LUMOS.classes) get Bueno's try-out */
    D.classes.forEach(function (c) {
      if (D.tryouts === false) return;  /* try-out weeks switched off in the settings: tiles keep the weekly class */
      var hit = list.filter(function (x) {
        return x.e.calendarEntryType === "TRY_OUT" && x.studio === c.studio && x.g === c.dance && (c.dance === "reggaeton" || x.lv === c.level);
      })[0];
      if (!hit) return;
      used.push(hit);
      c.try_day_en = DAYS.en[hit.a.wd] + " " + hit.a.d + " " + MON.en[hit.a.mo - 1];
      c.try_day_nl = DAYS.nl[hit.a.wd] + " " + hit.a.d + " " + MON.nl[hit.a.mo - 1];
      c.try_time = hit.a.hm + "–" + hit.b.hm;
      c.try_ = [c.try_[0], hit.a.d, hit.a.mo, hit.a.hm];
      c.book = DETAIL + hit.e.calendarEntryId;
      c.live = true;
    });
    /* studios page: the matching class row shows Bueno's try-out; anything else this week at that studio
       (workshops, events, a try-out with no typed row) is listed on top of the fold */
    var shown = 0;
    folds.forEach(function (fold) {
      var k = fold.getAttribute("data-studio"), extra = [];
      list.filter(function (x) { return x.studio === k; }).forEach(function (x) {
        var row = null, type = x.e.calendarEntryType;
        var typed = fold.querySelector('.sd-typed li[data-genre="' + x.g + '"]' + (x.g === "reggaeton" ? "" : '[data-level="' + x.lv + '"]'));
        if (type === "COURSE" && typed) return; /* a regular class: already in the typed list */
        if (type === "TRY_OUT" && D.tryouts !== false) row = typed;
        if (row && !row.classList.contains("is-live")) {
          row.classList.add("is-live");
          var tr = row.querySelector(".sd-try");
          if (tr) tr.textContent = (lang === "nl" ? "Proefles €5" : "€5 try-out") + ": " + dayLabel(x.a) + ", " + x.a.hm + "–" + x.b.hm;
          var bt = row.querySelector(".btn");
          if (bt) bt.href = DETAIL + x.e.calendarEntryId;
          shown++;
        } else if (!row) {
          extra.push(x);
        }
      });
      var ul = fold.querySelector(".sd-feed");
      if (!ul || !extra.length) return;
      ul.innerHTML = '<li class="sd-day">' + (lang === "nl" ? "Deze week in Bueno" : "This week in Bueno") + "</li>" + extra.map(function (x) {
        var title = (x.e.formattedTitle || x.e.title || "").replace(/\s+/g, " ").trim();
        return '<li class="is-live"><div class="sd-time">' + dayLabel(x.a) + '</div><div class="sd-what"><b>' + esc(title) + "</b><span>" + x.a.hm + "–" + x.b.hm + "</span></div>" +
          '<a class="btn btn-sm btn-pink" href="' + DETAIL + x.e.calendarEntryId + '">' + (lang === "nl" ? "Boek" : "Book") + "</a></li>";
      }).join("");
      ul.hidden = false;
      shown += extra.length;
    });
    document.documentElement.setAttribute("data-bueno", "live");
    document.documentElement.setAttribute("data-bueno-rows", String(shown + used.length));
    try { window.dispatchEvent(new CustomEvent("lumos:feed")); } catch (e) {}
  }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }

  getWeek().then(apply).catch(function () { document.documentElement.setAttribute("data-bueno", "fallback"); });
})();

/* ---------- dance card icons: each icon dances (Salsa: an LA basic, then one right turn;
   Bachata: its basic step, then the body roll; Reggaeton: a torso roll). Movement only, never a colour change.
   The generated SVG is the still pose; this rebuilds the same strokes and moves them. Same shapes,
   widths and colours. No motion with reduced motion; paused off screen and in hidden tabs. ---------- */
(function () {
  var icons = document.querySelectorAll(".dance-ico[data-dance]");
  if (!icons.length || !window.requestAnimationFrame) return;
  var mq = window.matchMedia ? matchMedia("(prefers-reduced-motion: reduce)") : null;
  if (mq && mq.matches) return;

  var PI = Math.PI, sin = Math.sin, cos = Math.cos, Z = [0, 0];
  function fx(n) { return String(Math.round(n * 100) / 100); }
  function pt(p) { return fx(p[0]) + " " + fx(p[1]); }
  function pl() { var a = [].slice.call(arguments); return "M" + a.map(pt).join("L"); }
  function cb(a, b, c, d) { return "M" + pt(a) + "C" + pt(b) + " " + pt(c) + " " + pt(d); }
  function add(p, d) { return [p[0] + d[0], p[1] + d[1]]; }
  function sub(p, d) { return [p[0] - d[0], p[1] - d[1]]; }
  function scl(p, k) { return [p[0] * k, p[1] * k]; }
  function lerp(a, b, t) { return a + (b - a) * t; }
  function lp(p, q, t) { return [lerp(p[0], q[0], t), lerp(p[1], q[1], t)]; }
  function clamp(x, a, b) { a = a === undefined ? 0 : a; b = b === undefined ? 1 : b; return Math.min(b, Math.max(a, x)); }
  function ss(t) { return t * t * t * (t * (6 * t - 15) + 10); }
  function inout(t) { return 0.5 - 0.5 * cos(PI * t); }
  function seg(p, a, b) { return clamp((p - a) / (b - a)); }
  function rot(p, c, deg) { var r = deg * PI / 180, s = sin(r), k = cos(r), x = p[0] - c[0], y = p[1] - c[1]; return [c[0] + x * k - y * s, c[1] + x * s + y * k]; }
  function dist(a, b) { return Math.hypot(a[0] - b[0], a[1] - b[1]); }
  function ikRaw(H, F, a, b, sg) {
    var vx = F[0] - H[0], vy = F[1] - H[1], d = Math.hypot(vx, vy), dd = Math.min(d, a + b - 1e-6);
    var al = (a * a - b * b + dd * dd) / (2 * dd), h = Math.sqrt(Math.max(0, a * a - al * al));
    var ux = vx / d, uy = vy / d;
    return [H[0] + ux * al - uy * h * sg, H[1] + uy * al + ux * h * sg];
  }
  /* knee for a moved hip, as an offset from the drawn knee, so the still pose is exact */
  function knee(Hr, Kr, Fr, H, F, sg) {
    var a = dist(Hr, Kr), b = dist(Kr, Fr);
    return add(Kr, sub(ikRaw(H, F, a, b, sg), ikRaw(Hr, Fr, a, b, sg)));
  }
  /* map point p from segment A0-B0 onto segment A1-B1 (rotate and scale) */
  function simil(p, A0, B0, A1, B1) {
    var vx = B0[0] - A0[0], vy = B0[1] - A0[1], wx = B1[0] - A1[0], wy = B1[1] - A1[1];
    var d2 = vx * vx + vy * vy, cr = (vx * wx + vy * wy) / d2, sr = (vx * wy - vy * wx) / d2;
    var px = p[0] - A0[0], py = p[1] - A0[1];
    return [A1[0] + px * cr - py * sr, A1[1] + px * sr + py * cr];
  }

  /* ----- salsa: he leads a double turn, the joined hands circle twice over her head ----- */
  var SA = {
    Lh: [17, 9], Lt: [[17, 11.5], [16.4, 16], [16, 21], [16, 25]], Lf1: [13, 40], Lf2: [19.2, 40],
    LaS: [17, 14.5], LaE: [22.5, 7], H: [24, 5], LbS: [17, 15.5], LbH: [12.5, 21.5],
    Fh: [30.5, 11], Ft: [[30.5, 13.5], [30.8, 17], [31.1, 20.5], [30.8, 24]], FaS: [30.5, 15.5], FaE: [26, 7.5],
    FbS: [30.6, 16.5], FbH: [34.6, 21],
    sk: [[27.5, 24], [25.5, 27], [24.5, 30], [24.9, 33], [36.7, 31.2], [35.9, 28.2], [34.7, 25.4], [33, 23.5]],
    Fl1: [[29, 33], [28, 40]], Fl2: [[33, 32.5], [34.8, 39.3]]
  };
  var TILT = 3.2 / 15, SKW = [0, 0.3, 0.7, 1, 1, 0.7, 0.3, 0];
  var LaM = lp(SA.LaS, SA.LaE, 0.62), FaM = lp(SA.FaS, SA.FaE, 0.66);
  function skirt(ax, m, fl, lift, shift) {
    return SA.sk.map(function (p, i) {
      var pr = SA.sk[7 - i], mir = [2 * ax - pr[0], pr[1]];
      var x = lerp(p[0], mir[0], m), y = lerp(p[1], mir[1], m);
      x = ax + (x - ax) * (1 + 0.22 * fl * SKW[i]);
      y -= 0.9 * fl * SKW[i] + lift;
      return [x + shift, y];
    });
  }
  function skD(s) { return "M" + pt(s[0]) + "C" + pt(s[1]) + " " + pt(s[2]) + " " + pt(s[3]) + "L" + pt(s[4]) + "C" + pt(s[5]) + " " + pt(s[6]) + " " + pt(s[7]); }
  function arm(Sr, Mr, Er, Hr, S, H, sg) {
    var a = dist(Sr, Mr), b = dist(Mr, Hr), k = Math.max(1, dist(S, H) / dist(Sr, Hr));
    var Mik = add(ikRaw(S, H, a * k, b * k, sg), sub(Mr, ikRaw(Sr, Hr, a, b, sg)));
    var M = lp(simil(Mr, Sr, Hr, S, H), Mik, 0.35);
    return [S, M, simil(Er, Mr, Hr, M, H), H];
  }
  function figPt(p, ax, th, cx, dy, lift) {
    var u = p[0] - ax, foot = p[1] >= 39;
    return [cx + u * cos(th), p[1] + dy - (foot ? 0 : lift) - TILT * u * sin(th)];
  }
  function hold(x, a) { return ss(seg(x, 0, a)) * (1 - ss(seg(x, 1 - a, 1))); }
  /* First half: the LA basic (he steps forward on 1 while she steps back, then back on 5 while she steps forward),
     the joined hands come down to a hold. Second half: one right turn under his raised hand. */
  var SPB = 0.46;
  function salsa(p) { return p < SPB ? salsaBasic(p / SPB) : salsaTurn((p - SPB) / (1 - SPB)); }
  /* the hands in a low hold: shoulder, elbow bent down, hand; blended in from the drawn raised arm */
  function holdArm(A, k) {
    if (k <= 0) return A;
    var S = A[0], H = A[3], e1 = ikRaw(S, H, 5.6, 5.6, 1), e2 = ikRaw(S, H, 5.6, 5.6, -1), E = e1[1] > e2[1] ? e1 : e2;
    var B = [S, lp(S, E, 0.6), E, H];
    return A.map(function (p, i) { return lp(p, B[i], k); });
  }
  function salsaBasic(u) {
    var s = sin(2 * PI * u), hh = hold(u, 0.2), hx = 1.9 * s;
    var L = function (q) { return [q[0] + hx + 0.5 * s * clamp((40 - q[1]) / 30), q[1]]; };
    var T = function (q) { return [q[0] + hx - 0.4 * s * clamp((40 - q[1]) / 30), q[1]]; };
    var Lt = SA.Lt.map(L), LaS = L(SA.LaS), LbS = L(SA.LbS), LbH = L(rot(SA.LbH, SA.LbS, 12 * s));
    var Lf1 = [SA.Lf1[0] + 3.2 * Math.min(s, 0), 40], Lf2 = [SA.Lf2[0] + 3.2 * Math.max(s, 0), 40];
    var Ft = SA.Ft.map(T), FaS = T(SA.FaS), FbS = T(SA.FbS), FbH = T(rot(SA.FbH, SA.FbS, -12 * s));
    var Fl1 = [T(SA.Fl1[0]), [SA.Fl1[1][0] + 3.2 * Math.min(s, 0), SA.Fl1[1][1]]];
    var Fl2 = [T(SA.Fl2[0]), [SA.Fl2[1][0] + 3.2 * Math.max(s, 0), SA.Fl2[1][1]]];
    var H = lp(SA.H, [24.2 + hx, 17.5], hh);
    var La = holdArm(arm(SA.LaS, LaM, SA.LaE, SA.H, LaS, H, 1), hh), Fa = holdArm(arm(SA.FaS, FaM, SA.FaE, SA.H, FaS, H, 1), hh);
    return {
      heads: [L(SA.Lh).concat(2.1), T(SA.Fh).concat(2)],
      paths: [cb(Lt[0], Lt[1], Lt[2], Lt[3]), pl(Lt[3], Lf1), pl(Lt[3], Lf2), pl(La[0], La[1], La[2], La[3]), pl(LbS, LbH),
        cb(Ft[0], Ft[1], Ft[2], Ft[3]), pl(Fa[0], Fa[1], Fa[2], Fa[3]), pl(FbS, FbH), skD(skirt(30.6, 0, 0.6 * Math.abs(s), 0, hx)),
        pl(Fl1[0], Fl1[1]), pl(Fl2[0], Fl2[1])],
      swish: Math.abs(hx) < 1e-4 ? "" : "translate(" + fx(hx) + " 0)"
    };
  }
  function salsaTurn(p) {
    var e = seg(p, 0.04, 0.8), hb = hold(e, 0.16);
    var tq = seg(e, 0.15, 0.85), th = 2 * PI * inout(tq);
    var hA = hold(clamp(e * 1.08), 0.16), hB = hold(clamp(e * 1.08 - 0.08), 0.16);
    var cx = 30.6 - 3.2 * hb, lift = 0.9 * sin(PI * tq), fl = 2 * sin(PI * tq);
    var prep = sin(PI * seg(p, 0, 0.08)), settle = sin(PI * seg(p, 0.8, 0.95));
    var lean = 1.8 * hb - 0.4 * prep - 0.3 * settle;
    var L = function (q) { return [q[0] + lean * clamp((40 - q[1]) / 30), q[1]]; };
    var T = function (q) { return figPt(q, 30.6, th, cx, 0, lift); };
    var Lt = SA.Lt.map(L), LaS = L(SA.LaS), LbS = L(SA.LbS), LbH = L(rot(SA.LbH, SA.LbS, -20 * hb));
    var Ft = SA.Ft.map(T), FaS = T(SA.FaS), FbS = T(SA.FbS), FbH = T(rot(SA.FbH, SA.FbS, -28 * fl));
    var Fl1 = [T(SA.Fl1[0]), figPt(SA.Fl1[1], 30.6, th, 30.6 - 3.2 * hA, 0, 0)];
    var Fl2 = [T(SA.Fl2[0]), figPt(SA.Fl2[1], 30.6, th, 30.6 - 3.2 * hB, 0, 0)];
    var C = [cx - 2.3, 4.2], halo = [2 * sin(th), -TILT * 2 * (1 - cos(th))];
    var H = add(lp(SA.H, add(C, halo), hb), [-0.2 * prep, 0.3 * prep + 0.3 * settle]);
    var La = arm(SA.LaS, LaM, SA.LaE, SA.H, LaS, H, 1), Fa = arm(SA.FaS, FaM, SA.FaE, SA.H, FaS, H, 1);
    var c = cos(th), tx = 30.6 * (1 - c) + cx - 30.6;
    return {
      heads: [L(SA.Lh).concat(2.1), T(SA.Fh).concat(2)],
      paths: [cb(Lt[0], Lt[1], Lt[2], Lt[3]), pl(Lt[3], SA.Lf1), pl(Lt[3], SA.Lf2), pl(La[0], La[1], La[2], La[3]), pl(LbS, LbH),
        cb(Ft[0], Ft[1], Ft[2], Ft[3]), pl(Fa[0], Fa[1], Fa[2], Fa[3]), pl(FbS, FbH), skD(skirt(30.6, (1 - c) / 2, fl, lift, cx - 30.6)),
        pl(Fl1[0], Fl1[1]), pl(Fl2[0], Fl2[1])],
      swish: (Math.abs(c - 1) < 1e-6 && Math.abs(tx) < 1e-4 && lift < 1e-4) ? "" : "matrix(" + c.toFixed(4) + " 0 0 1 " + fx(tx) + " " + fx(-lift) + ")"
    };
  }

  /* ----- bachata: both roll a body wave chest to hips, gentle sway ----- */
  var BL = { h: [20, 9.5], t: [[20, 12], [19.2, 17], [20, 21.5], [21.3, 25]], f: [[18.1, 40], [22.9, 40]], aS: [20, 15.5], aH: [26.8, 18.5] };
  var BF = { h: [27.5, 10], t: [[27.5, 12.5], [28.3, 17.5], [27.5, 21.5], [26.2, 25]], f: [[25.6, 40], [29.8, 40]], aS: [27.5, 15.5], aH: [21.2, 14] };
  function wave(y, w, A) {
    var k = 0.9, s = clamp((y - 8) / 17), u = w * (1 + k) - k * s;
    return (u > 0 && u < 1) ? A * sin(2 * PI * u) * sin(PI * u) : 0;
  }
  function mkD(w, A, bx) { return function (y) { var v = wave(y, w, A); return [v + bx, 0.25 * Math.abs(v) * clamp((y - 8) / 17)]; }; }
  function pose(f, D) { return { h: add(f.h, D(f.h[1])), t: f.t.map(function (q) { return add(q, D(q[1])); }), aS: add(f.aS, D(f.aS[1])) }; }
  /* First half: the bachata basic together, side, close, side, tap with a hip pop, and back the other way.
     Second half: the body wave. */
  var BPB = 0.5;
  /* where the screen-left foot (FA) and screen-right foot (FB) of both dancers stand after each of the 8 counts:
     side, close, side, tap, then back the other way. The body sits between the feet. */
  var FA = [0, -2.5, -2.5, -5, -5, -5, -2.5, -2.5, 0], FB = [0, 0, -2.5, -2.5, -5, -2.5, -2.5, 0, 0];
  function bachata(p) {
    var X = 0, pop = 0, fA = 0, fB = 0, w = 0, sway = 0, tap = 0, lA = 0, lB = 0;
    if (p < BPB) {
      var c = 8 * p / BPB, k = Math.min(7, Math.floor(c)), f = ss(c - k), up = sin(PI * (c - k));
      fA = lerp(FA[k], FA[k + 1], f); fB = lerp(FB[k], FB[k + 1], f);
      if (FA[k] !== FA[k + 1]) lA = -1.1 * up;
      if (FB[k] !== FB[k + 1]) lB = -1.1 * up;
      X = (fA + fB) / 2;
      /* counts 4 and 8 are the taps: the hips pop out to the side */
      if (k === 3 || k === 7) { pop = up * (k === 3 ? -1 : 1); tap = up; }
    } else {
      w = seg((p - BPB) / (1 - BPB), 0.04, 0.9);
      sway = 0.8 * sin(2 * PI * (p - BPB) / (1 - BPB));
      X = 0; fA = 0; fB = 0;
    }
    var hipW = function (y) { return clamp((y - 14) / 11); };
    var DL0 = mkD(w, 2.2, sway + X), DF0 = mkD(w, 2.8, sway + X);
    var DL = function (y) { var d = DL0(y); return [d[0] + 1.6 * pop * hipW(y), d[1] - 0.4 * tap * hipW(y)]; };
    var DF = function (y) { var d = DF0(y); return [d[0] + 1.6 * pop * hipW(y), d[1] - 0.4 * tap * hipW(y)]; };
    var A = pose(BL, DL), B = pose(BF, DF);
    return {
      heads: [A.h.concat(2.1), B.h.concat(2)],
      paths: [cb(A.t[0], A.t[1], A.t[2], A.t[3]), cb(B.t[0], B.t[1], B.t[2], B.t[3]),
        pl(A.t[3], add(BL.f[0], [fA + sway, lA])), pl(A.t[3], add(BL.f[1], [fB + sway, lB])),
        pl(B.t[3], add(BF.f[0], [fA + sway, lA])), pl(B.t[3], add(BF.f[1], [fB + sway, lB])),
        pl(A.aS, add(BL.aH, DF(18.5))), pl(B.aS, add(BF.aH, DL(14)))],
      swish: Math.abs(sway + X) < 1e-4 ? "" : "translate(" + fx(sway + X) + " 0)"
    };
  }

  /* ----- reggaeton: torso rolls down to the hips, knees bent ----- */
  var RE = {
    h: [23.5, 7.5], t: [[23.5, 10], [24.5, 14.5], [21.7, 19], [25.1, 25]],
    k1: [21.1, 32], f1: [22, 40], k2: [27.3, 32.5], f2: [29.5, 40],
    aS: [23.8, 13], aE: [29.8, 9.4], aH: [30.6, 3.4], bS: [23.8, 14], bE: [19, 17.6], bH: [23, 22],
    m1: [[32, 21.5], [35.4, 21.5]], m2: [[32.4, 25], [36.4, 25]]
  };
  function circ(ph0, ph, ax, ay) { return [ax * (sin(ph - ph0) + sin(ph0)), ay * (cos(ph0) - cos(ph - ph0))]; }
  function reggaeton(p) {
    /* bigger movements: every amplitude about 1.7 times the first version */
    var G = 1.7, ph = 4 * PI * p, dip = G * 0.35 * (1 - cos(2 * ph)) / 2;
    var hip = [G * (0.8 - 0.8 * cos(ph)), G * 0.4 * sin(ph) + dip], top = circ(0, ph, -0.5 * G, 0.3 * G);
    var r1 = circ(0.8, ph, -0.8 * G, 0.4 * G), r2 = circ(1.6, ph, -0.8 * G, 0.4 * G), mo = [hip[0], hip[1] * 0.5];
    var a1 = 6 * G * sin(ph), a2 = -5 * G * sin(ph - 0.6) - 5 * G * sin(0.6);
    var t = [add(RE.t[0], top), add(add(RE.t[1], lp(top, hip, 1 / 3)), r1), add(add(RE.t[2], lp(top, hip, 2 / 3)), r2), add(RE.t[3], hip)];
    var h = add(add(RE.h, top), circ(-0.4, ph, -0.25, 0.15));
    var dA = add(lp(top, hip, 0.2), scl(r1, 0.6)), dB = add(lp(top, hip, 0.27), scl(r1, 0.7));
    var aS = add(RE.aS, dA), aE = rot(add(RE.aE, dA), aS, a1), aH = rot(rot(add(RE.aH, dA), aS, a1), aE, a2);
    var bS = add(RE.bS, dB), dH = add(lp(top, hip, 0.8), scl(r2, 0.5)), bH = add(RE.bH, dH), bE = add(RE.bE, scl(add(dB, dH), 0.5));
    var k1 = knee(RE.t[3], RE.k1, RE.f1, t[3], RE.f1, 1);
    var k2 = lp(lp(t[3], RE.f2, 0.5), knee(RE.t[3], RE.k2, RE.f2, t[3], RE.f2, 1), 0.5);
    return {
      heads: [h.concat(2.1)],
      paths: [cb(t[0], t[1], t[2], t[3]), pl(t[3], k1, RE.f1), pl(t[3], k2, RE.f2), pl(aS, aE, aH), pl(bS, bE, bH),
        pl(add(RE.m1[0], mo), add(RE.m1[1], mo)), pl(add(RE.m2[0], mo), add(RE.m2[1], mo))],
      swish: ""
    };
  }

  var SPEC = { salsa: { dur: 5.6, build: salsa }, bachata: { dur: 5.2, build: bachata }, reggaeton: { dur: 2.6, build: reggaeton } };
  var NS = "http://www.w3.org/2000/svg", list = [];
  Array.prototype.forEach.call(icons, function (svg) {
    var spec = SPEC[svg.getAttribute("data-dance")], g = svg.querySelector(".ln");
    if (!spec || !g) return;
    var out = spec.build(0), inst = { svg: svg, spec: spec, heads: [], paths: [], sw: svg.querySelector(".swish"), on: false };
    while (g.firstChild) g.removeChild(g.firstChild);
    out.heads.forEach(function () { var c = document.createElementNS(NS, "circle"); c.setAttribute("class", "hd"); g.appendChild(c); inst.heads.push(c); });
    out.paths.forEach(function () { var pa = document.createElementNS(NS, "path"); g.appendChild(pa); inst.paths.push(pa); });
    draw(inst, out);
    list.push(inst);
  });
  if (!list.length) return;

  function draw(inst, out) {
    out.heads.forEach(function (hd, i) { var c = inst.heads[i]; c.setAttribute("cx", fx(hd[0])); c.setAttribute("cy", fx(hd[1])); c.setAttribute("r", hd[2]); });
    out.paths.forEach(function (d, i) { inst.paths[i].setAttribute("d", d); });
    if (inst.sw) { if (out.swish) inst.sw.setAttribute("transform", out.swish); else inst.sw.removeAttribute("transform"); }
  }

  /* one clock that only runs while an icon is on screen and the tab is visible, so a paused icon resumes where it stopped */
  var clock = 0, last = null, raf = 0;
  function anyOn() { return !document.hidden && !(mq && mq.matches) && list.some(function (i) { return i.on; }); }
  function frame(now) {
    raf = 0;
    if (last !== null) clock += Math.min(0.1, (now - last) / 1000);
    last = now;
    list.forEach(function (i) { if (i.on) draw(i, i.spec.build((clock % i.spec.dur) / i.spec.dur)); });
    if (anyOn()) raf = requestAnimationFrame(frame); else last = null;
  }
  function wake() { if (!raf && anyOn()) { last = null; raf = requestAnimationFrame(frame); } }
  if ("IntersectionObserver" in window) {
    var io = new IntersectionObserver(function (es) {
      es.forEach(function (e) { list.forEach(function (i) { if (i.svg === e.target) i.on = e.isIntersecting; }); });
      wake();
    }, { rootMargin: "100px" });
    list.forEach(function (i) { io.observe(i.svg); });
  } else {
    list.forEach(function (i) { i.on = true; });
    wake();
  }
  document.addEventListener("visibilitychange", wake);
  /* if someone switches reduced motion on while the page is open, stop and show the still pose */
  if (mq) {
    var off = function () {
      if (!mq.matches) return;
      list.forEach(function (i) { i.on = false; draw(i, i.spec.build(0)); });
      if (raf) { cancelAnimationFrame(raf); raf = 0; }
    };
    if (mq.addEventListener) mq.addEventListener("change", off); else if (mq.addListener) mq.addListener(off);
  }
})();
