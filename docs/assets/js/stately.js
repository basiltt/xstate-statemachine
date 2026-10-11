/* Stately editor embeds -------------------------------------------------------
 * A page drops  <div class="stately" data-machine="<key>"></div>  and this
 * turns it into a lazy, theme-following iframe of the chart in the public
 * Stately project.  The key → machineId map is docs/_data/stately.json,
 * exposed as /assets/data/stately.json.  colorMode follows <html data-theme>
 * live, so the diagram flips with the site's light/dark toggle.
 */
(function () {
  'use strict';
  var hosts = document.querySelectorAll('.stately[data-machine]');
  if (!hosts.length) return;

  var script = document.currentScript;
  var base = (script && script.getAttribute('data-base')) || '';
  var html = document.documentElement;

  function theme() {
    return html.getAttribute('data-theme') === 'dark' ? 'dark' : 'light';
  }
  function embedUrl(project, id, mode) {
    return 'https://stately.ai/registry/editor/embed/' + project +
      '?mode=design&colorMode=' + mode + '&machineId=' + id;
  }
  function editorUrl(project, id) {
    return 'https://stately.ai/registry/editor/' + project +
      '?mode=design&machineId=' + id;
  }

  fetch(base + '/assets/data/stately.json')
    .then(function (r) { return r.json(); })
    .then(function (map) {
      var project = map.project;
      var frames = [];

      hosts.forEach(function (host) {
        var key = host.getAttribute('data-machine');
        var id = map.machines[key];
        if (!id) { host.remove(); return; }
        var height = host.getAttribute('data-height') || '420';
        var title = host.getAttribute('data-title') || key;

        host.classList.add('stately-embed');
        host.innerHTML =
          '<div class="stately-frame" style="height:' + height + 'px">' +
          '<div class="stately-placeholder">Loading diagram…</div></div>' +
          '<div class="stately-caption">' +
          '<span class="stately-name">' + title + '</span>' +
          '<a class="stately-open" target="_blank" rel="noopener" href="' +
          editorUrl(project, id) + '">Open in Stately ↗</a></div>';

        var frameBox = host.querySelector('.stately-frame');
        var state = { box: frameBox, id: id, iframe: null, mode: null };
        frames.push(state);
      });

      function mount(state) {
        var mode = theme();
        if (state.iframe && state.mode === mode) return;
        var f = document.createElement('iframe');
        f.className = 'stately-iframe';
        f.loading = 'lazy';
        f.title = 'Stately diagram';
        f.setAttribute('allow', 'fullscreen');
        f.src = embedUrl(project, state.id, mode);
        var old = state.iframe;
        f.addEventListener('load', function () {
          if (old) old.remove();
          var ph = state.box.querySelector('.stately-placeholder');
          if (ph) ph.remove();
          f.classList.add('is-ready');
        });
        state.box.appendChild(f);
        state.iframe = f;
        state.mode = mode;
      }

      // Lazy: only mount when near the viewport.
      if ('IntersectionObserver' in window) {
        var io = new IntersectionObserver(function (entries) {
          entries.forEach(function (e) {
            if (!e.isIntersecting) return;
            var st = frames.find(function (s) { return s.box === e.target; });
            if (st) { mount(st); io.unobserve(e.target); }
          });
        }, { rootMargin: '400px 0px' });
        frames.forEach(function (s) { io.observe(s.box); });
      } else {
        frames.forEach(mount);
      }

      // Follow the site theme.
      new MutationObserver(function () {
        frames.forEach(function (s) { if (s.iframe) mount(s); });
      }).observe(html, { attributes: true, attributeFilter: ['data-theme'] });
    })
    .catch(function () { /* no map → leave the page as it was */ });
})();
