/* Stately editor embeds ---------------------------------------------------
 * A page drops  <div class="stately" data-machine="<key>"></div>  and this
 * turns it into a lazy, theme-following iframe of the chart in the public
 * Stately project.  The key → machineId map is docs/_data/stately.json,
 * exposed as /assets/data/stately.json.  colorMode follows <html data-theme>
 * live, so the diagram flips with the site's light/dark toggle. A separate
 * iframe powers the in-page fullscreen dialog without moving the inline one.
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
    return 'https://stately.ai/registry/editor/embed/' +
      encodeURIComponent(project) + '?mode=design&colorMode=' + mode +
      '&machineId=' + encodeURIComponent(id);
  }
  function editorUrl(project, id) {
    return 'https://stately.ai/registry/editor/' +
      encodeURIComponent(project) + '?mode=design&machineId=' +
      encodeURIComponent(id);
  }
  function element(tag, className, text) {
    var node = document.createElement(tag);
    node.className = className;
    if (text) node.textContent = text;
    return node;
  }
  function expandIcon() {
    var ns = 'http://www.w3.org/2000/svg';
    var icon = document.createElementNS(ns, 'svg');
    icon.setAttribute('viewBox', '0 0 24 24');
    icon.setAttribute('aria-hidden', 'true');
    icon.setAttribute('focusable', 'false');
    icon.setAttribute('fill', 'none');
    icon.setAttribute('stroke', 'currentColor');
    icon.setAttribute('stroke-width', '1.5');
    var path = document.createElementNS(ns, 'path');
    path.setAttribute('d', 'M3 8V3h5M3 3l6 6M16 3h5v5m0-5-6 6' +
      'M3 16v5h5m-5 0 6-6m7 6h5v-5m0 5-6-6');
    icon.appendChild(path);
    return icon;
  }

  fetch(base + '/assets/data/stately.json')
    .then(function (r) {
      if (!r.ok) throw new Error('Stately map unavailable');
      return r.json();
    })
    .then(function (map) {
      if (!map || typeof map.project !== 'string' || !map.machines ||
          typeof map.machines !== 'object') return;
      var project = map.project;
      var frames = [];
      var viewer = null;
      var active = null;
      var frameRequest = 0;

      function editorLink(id) {
        var link = element('a', 'stately-open stately-editor-link',
          'Open in Stately ↗');
        link.target = '_blank';
        link.rel = 'noopener noreferrer';
        if (id) link.href = editorUrl(project, id);
        return link;
      }

      function placeholder(box, text) {
        var ph = box.querySelector('.stately-placeholder');
        if (!ph) {
          ph = element('div', 'stately-placeholder');
          box.appendChild(ph);
        }
        ph.textContent = text;
      }

      hosts.forEach(function (host) {
        var key = host.getAttribute('data-machine');
        var id = map.machines[key];
        if (typeof id !== 'string' || !id) { host.remove(); return; }
        var height = Number(host.getAttribute('data-height') || 420);
        if (!Number.isFinite(height) || height <= 0) height = 420;
        var title = host.getAttribute('data-title') || key;
        var frameBox = element('div', 'stately-frame');
        frameBox.style.height = height + 'px';
        placeholder(frameBox, 'Loading diagram…');
        var caption = element('div', 'stately-caption');
        var actions = element('div', 'stately-actions');
        caption.appendChild(element('span', 'stately-name', title));
        actions.appendChild(editorLink(id));
        caption.appendChild(actions);

        host.classList.add('stately-embed');
        host.textContent = '';
        host.appendChild(frameBox);
        host.appendChild(caption);
        frames.push({
          box: frameBox, id: id, title: title, actions: actions,
          iframe: null, mode: null
        });
      });
      if (!frames.length) return;

      function disposeFrame(state) {
        if (state.iframe) {
          // Detached or obsolete loads must never update a new viewer.
          state.iframe.onload = null;
          state.iframe.onerror = null;
          state.iframe.remove();
        }
        state.iframe = null;
        state.mode = null;
      }

      function mount(state) {
        var mode = theme();
        if (state.iframe && state.mode === mode) return;
        disposeFrame(state);
        placeholder(state.box, 'Loading diagram…');
        if (state.status) {
          state.status.textContent =
            'Loading Stately… If it takes too long, use Open in Stately.';
        }
        var f = document.createElement('iframe');
        f.className = 'stately-iframe';
        f.loading = state.fullscreen ? 'eager' : 'lazy';
        f.title = 'Stately diagram: ' + state.title;
        f.setAttribute('allow', 'fullscreen');
        f.onload = function () {
          if (state.iframe !== f) return;
          var ph = state.box.querySelector('.stately-placeholder');
          if (ph) ph.remove();
          f.classList.add('is-ready');
          // Cross-origin load does not prove the chart rendered successfully.
          if (state.status) {
            state.status.textContent =
              'Pan and zoom to explore. If blank, use Open in Stately.';
          }
        };
        f.onerror = function () {
          if (state.iframe !== f) return;
          placeholder(state.box,
            'Diagram could not be loaded. Use Open in Stately.');
          if (state.status) {
            state.status.textContent =
              'Stately could not be loaded here. Try Open in Stately.';
          }
        };
        state.iframe = f;
        state.mode = mode;
        f.src = embedUrl(project, state.id, mode);
        state.box.appendChild(f);
      }

      function finishClose() {
        if (!active) return;
        if (frameRequest) cancelAnimationFrame(frameRequest);
        frameRequest = 0;
        var previous = active;
        active = null;
        disposeFrame(previous);
        viewer.box.textContent = '';
        viewer.status.textContent = '';
        if (previous.ownsScrollLock) {
          document.body.classList.remove('diagram-open');
        }
        if (previous.opener.isConnected) {
          previous.opener.focus({ preventScroll: true });
        }
        // Bypass the site's smooth scrolling when returning to the page.
        window.scrollTo({
          left: previous.scrollX, top: previous.scrollY, behavior: 'instant'
        });
      }

      function closeFullscreen() {
        if (viewer.dialog.open) viewer.dialog.close();
        finishClose();
      }

      function createFullscreen() {
        var dialog = element('dialog', 'stately-fullscreen');
        // Older browsers still get the inline chart and the external link.
        if (typeof dialog.showModal !== 'function' ||
            typeof dialog.close !== 'function') return null;
        dialog.id = 'statelyFullscreen';
        dialog.setAttribute('aria-labelledby', 'statelyFullscreenTitle');
        var toolbar = element('div', 'stately-fullscreen-toolbar');
        var title = element('h2', 'stately-fullscreen-title');
        title.id = 'statelyFullscreenTitle';
        var actions = element('div', 'stately-fullscreen-actions');
        var link = editorLink();
        var close = element('button', 'stately-fullscreen-close', 'Close');
        close.type = 'button';
        close.autofocus = true;
        close.setAttribute('aria-label', 'Close fullscreen diagram');
        close.addEventListener('click', closeFullscreen);
        actions.appendChild(link);
        actions.appendChild(close);
        toolbar.appendChild(title);
        toolbar.appendChild(actions);
        var box = element('div', 'stately-fullscreen-frame');
        var returnControl = element('button', 'stately-fullscreen-return',
          'Back to viewer controls');
        returnControl.type = 'button';
        returnControl.addEventListener('click', function () {
          close.focus({ preventScroll: true });
        });
        var status = element('p', 'stately-fullscreen-status');
        status.setAttribute('role', 'status');
        dialog.appendChild(toolbar);
        dialog.appendChild(box);
        dialog.appendChild(returnControl);
        dialog.appendChild(status);
        dialog.addEventListener('cancel', function (event) {
          event.preventDefault();
          closeFullscreen();
        });
        dialog.addEventListener('close', function () {
          // A queued close from a previous opening must not close a new one.
          if (!dialog.open) finishClose();
        });
        document.body.appendChild(dialog);
        return {
          dialog: dialog, title: title, link: link, close: close,
          box: box, status: status
        };
      }

      function scheduleFullscreenMount() {
        if (frameRequest) cancelAnimationFrame(frameRequest);
        var state = active;
        frameRequest = requestAnimationFrame(function () {
          frameRequest = 0;
          if (!state || state !== active || !viewer.dialog.open) return;
          // Stately measures its canvas on startup; show the layout first.
          var rect = state.box.getBoundingClientRect();
          if (rect.width <= 0 || rect.height <= 0) {
            state.status.textContent =
              'The viewer has no display area. Use Open in Stately.';
            return;
          }
          mount(state);
        });
      }

      function openFullscreen(state, opener) {
        if (active) closeFullscreen();
        active = {
          box: viewer.box, id: state.id, title: state.title,
          iframe: null, mode: null, fullscreen: true, status: viewer.status,
          opener: opener, scrollX: window.scrollX, scrollY: window.scrollY,
          ownsScrollLock: !document.body.classList.contains('diagram-open')
        };
        viewer.title.textContent = state.title;
        viewer.link.href = editorUrl(project, state.id);
        viewer.status.textContent = 'Loading Stately…';
        if (active.ownsScrollLock) {
          document.body.classList.add('diagram-open');
        }
        try {
          viewer.dialog.showModal();
        } catch (error) {
          // Keep the inline viewer usable if the native dialog cannot open.
          finishClose();
          return;
        }
        viewer.close.focus({ preventScroll: true });
        scheduleFullscreenMount();
      }

      viewer = createFullscreen();
      if (viewer) {
        frames.forEach(function (state) {
          var button = element('button', 'stately-expand', 'Fullscreen');
          button.insertBefore(expandIcon(), button.firstChild);
          button.type = 'button';
          button.setAttribute('aria-haspopup', 'dialog');
          button.setAttribute('aria-controls', 'statelyFullscreen');
          button.setAttribute('aria-label',
            'View ' + state.title + ' fullscreen');
          button.addEventListener('click', function () {
            openFullscreen(state, button);
          });
          state.actions.insertBefore(button, state.actions.firstChild);
        });
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
        if (active && viewer.dialog.open) scheduleFullscreenMount();
      }).observe(html, { attributes: true, attributeFilter: ['data-theme'] });
    })
    .catch(function () { /* no map → leave the page as it was */ });
})();
