/* Variation switch ("vary"): <div class="vary" data-vary="NAME"><div class="vary-opt" data-label="A">…</div><div class="vary-opt" data-label="B">…</div></div>
   shows one option at a time with an A/B/C pill (the choice lasts for the tab, nothing is saved); add data-attr="NAME" (empty options) to set <html data-NAME="X"> instead (e.g. data-shape, data-color).
   Only the switches live in this file: they are open choices for the owner. */
(function () {
  function ss(k, v) { try { if (v === undefined) return sessionStorage.getItem(k); sessionStorage.setItem(k, v); } catch (e) { return null; } }
  var nearAfter = null; /* the last switch placed under the highlight, so the next one goes below it (order kept) */
  document.querySelectorAll('.vary[data-vary]').forEach(function (box) {
    var name = box.getAttribute('data-vary'), attr = box.getAttribute('data-attr');
    var opts = [].slice.call(box.querySelectorAll(':scope > .vary-opt'));
    if (opts.length < 2) return;
    /* a switch that changes an attribute (highlight shape, highlight colour) only makes sense on a page that shows it */
    if (attr) {
      var hl = document.querySelector('.hl, .mark');
      if (!hl) { box.remove(); return; }
      /* the switches sit right under the first highlighted words, not in a page corner */
      var host = nearAfter || hl.closest('h1, h2, h3, p') || hl;
      host.parentNode.insertBefore(box, host.nextSibling);
      box.classList.add('vary-near');
      if (nearAfter) nearAfter.classList.remove('vary-near-end');
      box.classList.add('vary-near-end');
      nearAfter = box;
    }
    var letters = opts.map(function (o, i) { return o.getAttribute('data-label') || String.fromCharCode(65 + i); });
    var label = box.getAttribute('data-title') || '';
    var bar = document.createElement('div');
    bar.className = 'vary-bar';
    bar.setAttribute('translate', 'no');
    bar.innerHTML = (label ? '<span class="vary-label">' + label + '</span>' : '') + '<span class="vary-pill" role="group" aria-label="Options">' + letters.map(function (l) {
      return '<button type="button" data-l="' + l + '" aria-pressed="false">' + l + '</button>';
    }).join('') + '</span>';
    box.insertBefore(bar, box.firstChild);
    /* the choice only lasts for the tab. */
    function show(l) {
      if (letters.indexOf(l) < 0) l = letters[0];
      opts.forEach(function (o, i) { o.hidden = letters[i] !== l; });
      if (attr) document.documentElement.setAttribute('data-' + attr, l);
      bar.querySelectorAll('[data-l]').forEach(function (b) { var on = b.getAttribute('data-l') === l; b.classList.toggle('on', on); b.setAttribute('aria-pressed', on); });
      ss('vary:' + name, l);
    }
    bar.addEventListener('click', function (e) {
      var b = e.target.closest('button[data-l]');
      if (!b) return;
      e.preventDefault();
      show(b.getAttribute('data-l'));
    });
    /* start on the tab's last pick, else on what the generator wrote on <html> (HL_SHAPE and the rest) */
    show(ss('vary:' + name) || (attr && document.documentElement.getAttribute('data-' + attr)) || letters[0]);
  });
})();
