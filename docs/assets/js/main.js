// =============================================================================
// XState-StateMachine Documentation — Interactive Features
// Vanilla JS · IIFE · No globals · Graceful degradation
// =============================================================================

(function () {
  'use strict';

  // ---------------------------------------------------------------------------
  // Utility helpers
  // ---------------------------------------------------------------------------

  /** Safely query a single element (returns null when missing). */
  function qs(selector, root) {
    return (root || document).querySelector(selector);
  }

  /** Safely query all elements (returns empty NodeList when missing). */
  function qsa(selector, root) {
    return (root || document).querySelectorAll(selector);
  }

  /** Throttle via requestAnimationFrame — returns a wrapped callback. */
  function rafThrottle(fn) {
    var scheduled = false;
    return function () {
      if (scheduled) return;
      scheduled = true;
      requestAnimationFrame(function () {
        fn();
        scheduled = false;
      });
    };
  }

  /** Capitalize first letter of a string. */
  function capitalize(str) {
    return str.charAt(0).toUpperCase() + str.slice(1);
  }

  /** Pretty-print a URL slug: "my-page" -> "My Page" */
  function slugToTitle(slug) {
    return slug
      .replace(/[-_]/g, ' ')
      .replace(/\b\w/g, function (c) { return c.toUpperCase(); });
  }

  /** Check if user prefers reduced motion. */
  function prefersReducedMotion() {
    return window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  }

  /** Scroll behavior respecting reduced motion preference. */
  function getScrollBehavior() {
    return prefersReducedMotion() ? 'auto' : 'smooth';
  }

  /** Safe localStorage wrapper (some browsers block it in private mode). */
  var storage = {
    get: function (key) {
      try { return localStorage.getItem(key); } catch (_) { return null; }
    },
    set: function (key, val) {
      try { localStorage.setItem(key, val); } catch (_) { /* noop */ }
    },
    remove: function (key) {
      try { localStorage.removeItem(key); } catch (_) { /* noop */ }
    }
  };

  // ---------------------------------------------------------------------------
  // 1. Dark Mode Toggle
  //    Uses the existing #themeToggle button from default.html
  // ---------------------------------------------------------------------------

  (function initDarkMode() {
    var STORAGE_KEY = 'theme';
    var html = document.documentElement;
    var userChose = false; // Track if user manually toggled

    /**
     * Resolve the initial theme:
     *   1. Stored preference
     *   2. System preference
     *   3. Default to "light"
     */
    function resolveTheme() {
      var stored = storage.get(STORAGE_KEY);
      if (stored === 'dark' || stored === 'light') {
        userChose = true;
        return stored;
      }
      if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) return 'dark';
      return 'light';
    }

    function applyTheme(theme) {
      html.setAttribute('data-theme', theme);
      storage.set(STORAGE_KEY, theme);

      // Update the existing toggle button's icon visibility via CSS classes
      var toggleBtn = qs('#themeToggle');
      if (toggleBtn) {
        toggleBtn.setAttribute('aria-label', theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode');
      }
    }

    // Apply immediately
    applyTheme(resolveTheme());

    // Wire up the existing #themeToggle button
    var toggleBtn = qs('#themeToggle');
    if (toggleBtn) {
      toggleBtn.addEventListener('click', function () {
        userChose = true;
        var current = html.getAttribute('data-theme') || 'light';
        applyTheme(current === 'dark' ? 'light' : 'dark');
      });
    }

    // Listen for system-preference changes while page is open
    if (window.matchMedia) {
      window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function (e) {
        // Only follow system if user hasn't manually chosen
        if (!userChose) {
          applyTheme(e.matches ? 'dark' : 'light');
        }
      });
    }
  })();

  // ---------------------------------------------------------------------------
  // 2. Scrolled Nav Shadow
  // ---------------------------------------------------------------------------

  (function initNavShadow() {
    var nav = document.getElementById('topNav');
    if (!nav) return;

    var onScroll = rafThrottle(function () {
      nav.classList.toggle('scrolled', window.scrollY > 10);
    });

    window.addEventListener('scroll', onScroll, { passive: true });
  })();

  // ---------------------------------------------------------------------------
  // 3. Mobile Nav Toggle
  // ---------------------------------------------------------------------------

  (function initMobileNav() {
    var navToggle = document.getElementById('navToggle');
    var navLinks = document.getElementById('navLinks');
    if (!navToggle || !navLinks) return;

    navToggle.addEventListener('click', function () {
      var isOpen = navLinks.classList.toggle('open');
      navToggle.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
    });

    // Close on Escape
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && navLinks.classList.contains('open')) {
        navLinks.classList.remove('open');
        navToggle.setAttribute('aria-expanded', 'false');
        navToggle.focus();
      }
    });

    // Close when clicking a nav link (on mobile)
    qsa('.nav-link', navLinks).forEach(function (link) {
      link.addEventListener('click', function () {
        if (window.innerWidth <= 1024) {
          navLinks.classList.remove('open');
          navToggle.setAttribute('aria-expanded', 'false');
        }
      });
    });
  })();

  // ---------------------------------------------------------------------------
  // 4. Code Tabs
  // ---------------------------------------------------------------------------

  (function initCodeTabs() {
    document.addEventListener('click', function (e) {
      var btn = e.target.closest('.code-tab-btn');
      if (!btn) return;

      var tabGroup = btn.closest('.code-tabs');
      if (!tabGroup) return;

      var tabName = btn.getAttribute('data-tab');

      qsa('.code-tab-btn', tabGroup).forEach(function (b) {
        b.classList.remove('active');
        b.setAttribute('aria-selected', 'false');
      });
      qsa('.code-tab-panel', tabGroup).forEach(function (p) {
        p.classList.remove('active');
      });

      btn.classList.add('active');
      btn.setAttribute('aria-selected', 'true');
      var panel = qs('.code-tab-panel[data-tab="' + tabName + '"]', tabGroup);
      if (panel) panel.classList.add('active');
    });
  })();

  // ---------------------------------------------------------------------------
  // 5. Active Sidebar Link
  // ---------------------------------------------------------------------------

  (function initActiveSidebarLink() {
    var currentPath = window.location.pathname;
    qsa('.sidebar-link').forEach(function (link) {
      var href = link.getAttribute('href');
      // Exact match (or trailing slash match) to avoid substring false positives
      if (href && (currentPath === href || currentPath === href.replace(/\/$/, '') || currentPath + '/' === href)) {
        link.classList.add('active');
      }
    });
  })();

  // ---------------------------------------------------------------------------
  // 6. Sidebar Toggle for Mobile
  // ---------------------------------------------------------------------------

  (function initSidebarToggle() {
    var sidebar = document.getElementById('sidebar');
    if (!sidebar) return;

    var sidebarToggle = document.createElement('button');
    sidebarToggle.className = 'sidebar-toggle';
    sidebarToggle.type = 'button';
    sidebarToggle.innerHTML = '&#9776; Menu';
    sidebarToggle.setAttribute('aria-label', 'Toggle sidebar navigation');
    sidebarToggle.setAttribute('aria-expanded', 'false');
    document.body.appendChild(sidebarToggle);

    function checkMobile() {
      if (window.innerWidth <= 1024) {
        sidebarToggle.classList.add('visible');
      } else {
        sidebarToggle.classList.remove('visible');
        sidebar.classList.remove('open');
        sidebarToggle.setAttribute('aria-expanded', 'false');
      }
    }

    checkMobile();
    window.addEventListener('resize', checkMobile);

    sidebarToggle.addEventListener('click', function () {
      var isOpen = sidebar.classList.toggle('open');
      sidebarToggle.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
    });

    // Close sidebar when clicking outside
    document.addEventListener('click', function (e) {
      if (
        sidebar.classList.contains('open') &&
        !sidebar.contains(e.target) &&
        e.target !== sidebarToggle
      ) {
        sidebar.classList.remove('open');
        sidebarToggle.setAttribute('aria-expanded', 'false');
      }
    });
  })();

  // ---------------------------------------------------------------------------
  // 7. Smooth Anchor Scrolling
  // ---------------------------------------------------------------------------

  (function initSmoothScroll() {
    document.addEventListener('click', function (e) {
      var anchor = e.target.closest('a[href^="#"]');
      if (!anchor) return;

      var href = anchor.getAttribute('href');
      if (!href || href === '#') return;

      var target;
      try { target = document.querySelector(href); } catch (_) { return; }
      if (!target) return;

      e.preventDefault();
      target.scrollIntoView({ behavior: getScrollBehavior() });

      // Update URL hash without jumping
      if (history.pushState) {
        history.pushState(null, '', href);
      }
    });
  })();

  // ---------------------------------------------------------------------------
  // 7b. Auto-classify blockquote callouts
  //     Adds CSS classes based on first bold word (Tip, Warning, Note)
  // ---------------------------------------------------------------------------

  (function initCallouts() {
    qsa('.content blockquote').forEach(function (bq) {
      var firstP = qs('p:first-child', bq);
      if (!firstP) return;
      var firstStrong = qs('strong', firstP);
      if (!firstStrong) return;
      var text = (firstStrong.textContent || '').toLowerCase().replace(':', '');
      if (text === 'tip') bq.classList.add('callout-tip');
      else if (text === 'warning') bq.classList.add('callout-warning');
      else if (text === 'note') bq.classList.add('callout-note');
    });
  })();

  // ---------------------------------------------------------------------------
  // 8. Enhanced Copy Button for Code Blocks + Language Labels
  // ---------------------------------------------------------------------------

  (function initCodeBlocks() {
    // Language display-name map
    var LANG_NAMES = {
      js: 'JavaScript', javascript: 'JavaScript',
      ts: 'TypeScript', typescript: 'TypeScript',
      py: 'Python', python: 'Python',
      rb: 'Ruby', ruby: 'Ruby',
      sh: 'Shell', bash: 'Bash', zsh: 'Zsh', shell: 'Shell',
      html: 'HTML', css: 'CSS', scss: 'SCSS', sass: 'Sass',
      json: 'JSON', yaml: 'YAML', yml: 'YAML',
      xml: 'XML', sql: 'SQL', graphql: 'GraphQL',
      java: 'Java', kotlin: 'Kotlin', swift: 'Swift',
      go: 'Go', rust: 'Rust', c: 'C', cpp: 'C++',
      cs: 'C#', csharp: 'C#', php: 'PHP',
      dockerfile: 'Dockerfile', toml: 'TOML', ini: 'INI',
      markdown: 'Markdown', md: 'Markdown', text: 'Text', txt: 'Text',
      jsx: 'JSX', tsx: 'TSX', vue: 'Vue',
      lua: 'Lua', r: 'R', perl: 'Perl', elixir: 'Elixir', erlang: 'Erlang',
      haskell: 'Haskell', scala: 'Scala', clojure: 'Clojure', dart: 'Dart',
      powershell: 'PowerShell', ps1: 'PowerShell'
    };

    // Target ALL pre>code blocks across the entire page:
    //   - .content pre          (guide/doc pages)
    //   - .code-tab-panel pre   (homepage code showcase tabs)
    //   - .why-card pre         (homepage "Why" comparison blocks)
    //   - any other pre>code    (catch-all for future sections)
    qsa('pre').forEach(function (pre) {
      // Only process <pre> blocks that contain a <code> element
      var code = qs('code', pre);
      if (!code) return;

      // Guard against duplicate initialization
      if (pre.querySelector('.code-copy-btn')) return;

      // Ensure the pre is positioned so the button can be placed absolutely
      var prePosition = window.getComputedStyle(pre).position;
      if (prePosition === 'static') {
        pre.style.position = 'relative';
      }

      // --- Language Label (only for .content pre, not homepage showcase) ---
      var isContentPre = pre.closest('.content');
      if (isContentPre) {
        var langClass = Array.from(code.classList).find(function (cls) {
          return cls.startsWith('language-');
        });
        if (langClass) {
          var langKey = langClass.replace('language-', '').toLowerCase();
          var langName = LANG_NAMES[langKey] || capitalize(langKey);

          var label = document.createElement('span');
          label.className = 'code-label';
          label.textContent = langName;
          pre.insertBefore(label, pre.firstChild);
        }
      }

      // --- Copy Button ---
      var btn = document.createElement('button');
      btn.className = 'code-copy-btn';
      btn.type = 'button';
      btn.textContent = 'Copy';
      btn.setAttribute('aria-label', 'Copy code to clipboard');
      pre.appendChild(btn);

      btn.addEventListener('click', function () {
        var codeEl = qs('code', pre);
        if (!codeEl) return;

        navigator.clipboard.writeText(codeEl.textContent).then(function () {
          btn.textContent = 'Copied!';
          btn.classList.add('copied');
          setTimeout(function () {
            btn.textContent = 'Copy';
            btn.classList.remove('copied');
          }, 2000);
        }).catch(function () {
          // Fallback for older browsers / insecure contexts
          var range = document.createRange();
          range.selectNodeContents(codeEl);
          var sel = window.getSelection();
          sel.removeAllRanges();
          sel.addRange(range);
          try {
            document.execCommand('copy');
            btn.textContent = 'Copied!';
            btn.classList.add('copied');
            setTimeout(function () {
              btn.textContent = 'Copy';
              btn.classList.remove('copied');
            }, 2000);
          } catch (_) { /* silently fail */ }
          sel.removeAllRanges();
        });
      });
    });
  })();

  // ---------------------------------------------------------------------------
  // 9. Heading Anchor Links
  // ---------------------------------------------------------------------------

  (function initHeadingAnchors() {
    var content = qs('.content');
    if (!content) return;

    // Generate IDs for headings that lack them
    qsa('h2, h3, h4', content).forEach(function (heading) {
      if (!heading.id) {
        heading.id = heading.textContent
          .toLowerCase()
          .trim()
          .replace(/[^a-z0-9\s-]/g, '')
          .replace(/\s+/g, '-')
          .replace(/-+/g, '-');
      }

      var link = document.createElement('a');
      link.className = 'heading-anchor';
      link.href = '#' + heading.id;
      link.setAttribute('aria-label', 'Link to "' + heading.textContent.trim() + '"');
      link.textContent = '#';

      link.addEventListener('click', function (e) {
        e.preventDefault();

        // Compensate for sticky header offset
        var headerHeight = 70;
        var targetPos = heading.getBoundingClientRect().top + window.scrollY - headerHeight;
        window.scrollTo({ top: targetPos, behavior: getScrollBehavior() });

        // Copy link to clipboard (with user feedback)
        var url = window.location.origin + window.location.pathname + '#' + heading.id;
        navigator.clipboard.writeText(url).then(function () {
          link.textContent = '✓';
          setTimeout(function () { link.textContent = '#'; }, 1500);
        }).catch(function () {
          // Silently degrade
        });

        if (history.pushState) {
          history.pushState(null, '', '#' + heading.id);
        }
      });

      heading.appendChild(link);
    });
  })();

  // ---------------------------------------------------------------------------
  // 10. Table of Contents Generator
  //     Uses the existing #tocSidebar / #tocList from default.html
  // ---------------------------------------------------------------------------

  (function initTOC() {
    var tocList = qs('#tocList');
    if (!tocList) return;

    var content = qs('.content');
    if (!content) return;

    var headings = qsa('h2[id], h3[id], h4[id]', content);
    if (!headings.length) {
      // Hide TOC sidebar if no headings found
      var tocSidebar = qs('#tocSidebar');
      if (tocSidebar) tocSidebar.style.display = 'none';
      return;
    }

    // Build nested TOC structure
    var frag = document.createDocumentFragment();
    var currentH2Item = null;  // The current H2 <li>
    var currentH2List = null;  // <ul> for h3s under current H2
    var currentH3Item = null;  // The current H3 <li>
    var currentH3List = null;  // <ul> for h4s under current H3

    headings.forEach(function (heading) {
      var li = document.createElement('li');
      li.className = 'toc-item';

      var a = document.createElement('a');
      a.className = 'toc-link';
      a.href = '#' + heading.id;
      // Get only the direct text, excluding the anchor '#' we appended
      var text = heading.textContent.replace(/#$/, '').trim();
      a.textContent = text;
      a.setAttribute('data-target', heading.id);
      li.appendChild(a);

      var tag = heading.tagName;

      if (tag === 'H2') {
        // Top-level item
        currentH2Item = li;
        currentH2List = document.createElement('ul');
        currentH2List.className = 'toc-sublist';
        li.appendChild(currentH2List);
        currentH3Item = null;
        currentH3List = null;
        frag.appendChild(li);
      } else if (tag === 'H3') {
        currentH3Item = li;
        currentH3List = document.createElement('ul');
        currentH3List.className = 'toc-sublist';
        li.appendChild(currentH3List);
        if (currentH2List) {
          currentH2List.appendChild(li);
        } else {
          frag.appendChild(li);
        }
      } else if (tag === 'H4') {
        // Nest under current H3 if available, else H2, else top-level
        if (currentH3List) {
          currentH3List.appendChild(li);
        } else if (currentH2List) {
          currentH2List.appendChild(li);
        } else {
          frag.appendChild(li);
        }
      }
    });

    tocList.appendChild(frag);

    // Highlight active section using Intersection Observer
    var tocLinks = qsa('.toc-link', tocList);
    var lastActiveId = null;

    if ('IntersectionObserver' in window) {
      var observer = new IntersectionObserver(function (entries) {
        // Find the topmost intersecting entry
        var topEntry = null;
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            if (!topEntry || entry.boundingClientRect.top < topEntry.boundingClientRect.top) {
              topEntry = entry;
            }
          }
        });

        if (topEntry) {
          var id = topEntry.target.id;
          if (id !== lastActiveId) {
            lastActiveId = id;
            tocLinks.forEach(function (l) { l.classList.remove('active'); });
            var link = qs('.toc-link[data-target="' + id + '"]', tocList);
            if (link) {
              link.classList.add('active');
              // Scroll TOC to keep active link visible
              link.scrollIntoView({ block: 'nearest', behavior: 'auto' });
            }
          }
        }
      }, {
        rootMargin: '-80px 0px -60% 0px',
        threshold: 0
      });

      headings.forEach(function (heading) {
        observer.observe(heading);
      });
    }
  })();

  // ---------------------------------------------------------------------------
  // 11. Search Modal (Ctrl+K / Cmd+K)
  //     Uses the existing #searchModal from default.html
  // ---------------------------------------------------------------------------

  (function initSearch() {
    var searchModal = qs('#searchModal');
    var searchOverlay = qs('#searchOverlay');
    var searchInput = qs('#searchInput');
    var searchResults = qs('#searchResults');
    var searchBtn = qs('#searchBtn');

    if (!searchModal || !searchInput || !searchResults) return;

    var searchIndex = null;
    var searchReady = false;
    var activeIndex = -1; // For keyboard navigation of results

    // Determine base URL for fetch (handles subpath deployments)
    var baseUrl = '';
    var baseTag = qs('base');
    if (baseTag) {
      baseUrl = baseTag.getAttribute('href') || '';
    } else {
      // Try to infer from canonical or known path patterns
      var path = window.location.pathname;
      var guideIdx = path.indexOf('/guide/');
      var apiIdx = path.indexOf('/api/');
      if (guideIdx > 0) {
        baseUrl = path.substring(0, guideIdx);
      } else if (apiIdx > 0) {
        baseUrl = path.substring(0, apiIdx);
      }
    }

    // Load search index
    var searchUrl = (baseUrl || '') + '/assets/js/search-index.json';
    fetch(searchUrl)
      .then(function (res) {
        if (!res.ok) throw new Error('Not found');
        return res.json();
      })
      .then(function (data) {
        searchIndex = data;
        searchReady = true;
      })
      .catch(function () {
        searchIndex = null;
        searchReady = false;
      });

    // Set aria-modal on the existing modal
    searchModal.setAttribute('aria-modal', 'true');

    function openSearch() {
      searchModal.classList.add('active');
      searchModal.setAttribute('aria-hidden', 'false');
      document.body.classList.add('search-open');
      searchInput.value = '';
      searchResults.innerHTML = '<div class="search-empty">Type to search the documentation...</div>';
      activeIndex = -1;
      // Slight delay to ensure modal is visible before focusing
      setTimeout(function () { searchInput.focus(); }, 50);
    }

    function closeSearch() {
      searchModal.classList.remove('active');
      searchModal.setAttribute('aria-hidden', 'true');
      document.body.classList.remove('search-open');
      // Return focus to search button
      if (searchBtn) searchBtn.focus();
    }

    function performSearch(query) {
      searchResults.innerHTML = '';
      activeIndex = -1;

      if (!searchReady || !searchIndex) {
        var msg = document.createElement('div');
        msg.className = 'search-empty';
        msg.textContent = 'Search index is loading. Please try again in a moment.';
        searchResults.appendChild(msg);
        return;
      }

      var q = query.toLowerCase().trim();
      if (!q) {
        searchResults.innerHTML = '<div class="search-empty">Type to search the documentation...</div>';
        return;
      }

      // Score and filter results for relevance ranking
      var scored = [];
      searchIndex.forEach(function (item) {
        var title = (item.title || '').toLowerCase();
        var desc = (item.description || '').toLowerCase();
        var section = (item.section || '').toLowerCase();
        var score = 0;

        // Exact title match gets highest priority
        if (title === q) score += 100;
        else if (title.indexOf(q) === 0) score += 60;
        else if (title.indexOf(q) !== -1) score += 40;

        // Description match
        if (desc.indexOf(q) !== -1) score += 20;

        // Section match
        if (section.indexOf(q) !== -1) score += 10;

        // Word boundary bonus
        var words = q.split(/\s+/);
        words.forEach(function (word) {
          if (word && title.indexOf(word) !== -1) score += 5;
          if (word && desc.indexOf(word) !== -1) score += 2;
        });

        if (score > 0) {
          scored.push({ item: item, score: score });
        }
      });

      // Sort by score descending
      scored.sort(function (a, b) { return b.score - a.score; });

      if (!scored.length) {
        var empty = document.createElement('div');
        empty.className = 'search-empty';
        empty.textContent = 'No results found for "' + query + '"';
        searchResults.appendChild(empty);
        return;
      }

      // Highlight helper — wraps matching substrings with <mark>
      function highlightText(text, query) {
        if (!text || !query) return text;
        var lowerText = text.toLowerCase();
        var idx = lowerText.indexOf(query.toLowerCase());
        if (idx === -1) return text;
        return text.substring(0, idx) +
          '<mark class="search-highlight">' +
          text.substring(idx, idx + query.length) +
          '</mark>' +
          text.substring(idx + query.length);
      }

      scored.slice(0, 15).forEach(function (entry, i) {
        var item = entry.item;
        var a = document.createElement('a');
        a.className = 'search-result-item';
        a.href = (baseUrl || '') + item.url;
        a.setAttribute('data-index', i);

        var titleEl = document.createElement('span');
        titleEl.className = 'search-result-title';
        titleEl.innerHTML = highlightText(item.title || 'Untitled', q);

        var descEl = document.createElement('span');
        descEl.className = 'search-result-desc';
        descEl.innerHTML = highlightText(item.description || '', q);

        var sectionEl = document.createElement('span');
        sectionEl.className = 'search-result-section';
        sectionEl.textContent = item.section || '';

        a.appendChild(titleEl);
        a.appendChild(descEl);
        a.appendChild(sectionEl);
        searchResults.appendChild(a);

        a.addEventListener('click', function () {
          closeSearch();
        });
      });
    }

    // Keyboard navigation within results
    function updateActiveResult(newIndex) {
      var items = qsa('.search-result-item', searchResults);
      if (!items.length) return;

      if (newIndex < 0) newIndex = items.length - 1;
      if (newIndex >= items.length) newIndex = 0;

      items.forEach(function (item) { item.classList.remove('active'); });
      items[newIndex].classList.add('active');
      items[newIndex].scrollIntoView({ block: 'nearest', behavior: 'auto' });
      activeIndex = newIndex;
    }

    // Events
    searchInput.addEventListener('input', function () {
      performSearch(this.value);
    });

    searchInput.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        updateActiveResult(activeIndex + 1);
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        updateActiveResult(activeIndex - 1);
      } else if (e.key === 'Enter') {
        var items = qsa('.search-result-item', searchResults);
        if (activeIndex >= 0 && activeIndex < items.length) {
          e.preventDefault();
          items[activeIndex].click();
        }
      }
    });

    if (searchOverlay) {
      searchOverlay.addEventListener('click', closeSearch);
    }

    if (searchBtn) {
      searchBtn.addEventListener('click', function (e) {
        e.preventDefault();
        openSearch();
      });
    }

    // Focus trap within search modal
    searchModal.addEventListener('keydown', function (e) {
      if (e.key === 'Tab') {
        // Keep focus within modal
        var focusable = searchModal.querySelectorAll('input, button, a[href]');
        if (!focusable.length) return;

        var first = focusable[0];
        var last = focusable[focusable.length - 1];

        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    });

    // Global keyboard shortcut: Ctrl+K / Cmd+K
    document.addEventListener('keydown', function (e) {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        if (searchModal.classList.contains('active')) {
          closeSearch();
        } else {
          openSearch();
        }
      }

      if (e.key === 'Escape' && searchModal.classList.contains('active')) {
        closeSearch();
      }
    });

    // Expose openSearch for the "/" shortcut
    window.__docSearchOpen = openSearch;
    window.__docSearchIsOpen = function () {
      return searchModal.classList.contains('active');
    };
  })();

  // ---------------------------------------------------------------------------
  // 12. Scroll Progress Bar
  //     Uses the existing #scrollProgress from default.html
  // ---------------------------------------------------------------------------

  (function initScrollProgress() {
    var bar = qs('#scrollProgress');
    if (!bar) return;

    bar.setAttribute('role', 'progressbar');
    bar.setAttribute('aria-label', 'Page scroll progress');

    var update = rafThrottle(function () {
      var scrollTop = window.scrollY || document.documentElement.scrollTop;
      var docHeight = document.documentElement.scrollHeight - document.documentElement.clientHeight;
      var progress = docHeight > 0 ? Math.min(Math.max((scrollTop / docHeight) * 100, 0), 100) : 0;
      bar.style.width = progress + '%';
      bar.setAttribute('aria-valuenow', Math.round(progress));
    });

    window.addEventListener('scroll', update, { passive: true });
    update(); // initial
  })();

  // ---------------------------------------------------------------------------
  // 13. Back to Top Button
  // ---------------------------------------------------------------------------

  (function initBackToTop() {
    var btn = document.createElement('button');
    btn.className = 'back-to-top';
    btn.type = 'button';
    btn.setAttribute('aria-label', 'Back to top');
    btn.innerHTML =
      '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none"' +
      ' stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
      '<polyline points="18 15 12 9 6 15"/></svg>';

    document.body.appendChild(btn);

    var toggle = rafThrottle(function () {
      btn.classList.toggle('visible', window.scrollY > 400);
    });

    window.addEventListener('scroll', toggle, { passive: true });

    btn.addEventListener('click', function () {
      window.scrollTo({ top: 0, behavior: getScrollBehavior() });
    });
  })();

  // ---------------------------------------------------------------------------
  // 14. Keyboard Navigation & Shortcuts Help
  // ---------------------------------------------------------------------------

  (function initKeyboardNav() {
    // Build the help modal
    var helpOverlay = document.createElement('div');
    helpOverlay.className = 'shortcuts-overlay';

    var helpModal = document.createElement('div');
    helpModal.className = 'shortcuts-modal';
    helpModal.setAttribute('role', 'dialog');
    helpModal.setAttribute('aria-modal', 'true');
    helpModal.setAttribute('aria-label', 'Keyboard shortcuts');

    helpModal.innerHTML =
      '<div class="shortcuts-header">' +
        '<h3>Keyboard Shortcuts</h3>' +
        '<button class="shortcuts-close" type="button" aria-label="Close">&times;</button>' +
      '</div>' +
      '<div class="shortcuts-body">' +
        '<dl class="shortcuts-list">' +
          '<div class="shortcut-row"><dt><kbd>Ctrl</kbd>+<kbd>K</kbd> / <kbd>\u2318</kbd>+<kbd>K</kbd></dt><dd>Open search</dd></div>' +
          '<div class="shortcut-row"><dt><kbd>/</kbd></dt><dd>Focus search</dd></div>' +
          '<div class="shortcut-row"><dt><kbd>Esc</kbd></dt><dd>Close dialogs</dd></div>' +
          '<div class="shortcut-row"><dt><kbd>?</kbd></dt><dd>Show this help</dd></div>' +
        '</dl>' +
      '</div>';

    document.body.appendChild(helpOverlay);
    document.body.appendChild(helpModal);

    var triggerElement = null; // Track what opened the modal for focus return

    function openHelp() {
      triggerElement = document.activeElement;
      helpOverlay.classList.add('active');
      helpModal.classList.add('active');
      // Focus the close button
      var closeBtn = qs('.shortcuts-close', helpModal);
      if (closeBtn) closeBtn.focus();
    }

    function closeHelp() {
      helpOverlay.classList.remove('active');
      helpModal.classList.remove('active');
      // Return focus to trigger
      if (triggerElement && triggerElement.focus) {
        triggerElement.focus();
      }
    }

    helpOverlay.addEventListener('click', closeHelp);

    var closeBtn = qs('.shortcuts-close', helpModal);
    if (closeBtn) {
      closeBtn.addEventListener('click', closeHelp);
    }

    // Focus trap within help modal
    helpModal.addEventListener('keydown', function (e) {
      if (e.key === 'Tab') {
        var focusable = helpModal.querySelectorAll('button, a[href]');
        if (!focusable.length) return;

        var first = focusable[0];
        var last = focusable[focusable.length - 1];

        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    });

    document.addEventListener('keydown', function (e) {
      // Ignore when typing in input/textarea/contenteditable
      var tag = (e.target.tagName || '').toLowerCase();
      var isEditable = tag === 'input' || tag === 'textarea' || tag === 'select' || e.target.isContentEditable;

      if (e.key === 'Escape') {
        if (helpModal.classList.contains('active')) {
          closeHelp();
          return;
        }
      }

      if (isEditable) return;

      // "?" — show keyboard shortcuts
      if (e.key === '?') {
        e.preventDefault();
        if (helpModal.classList.contains('active')) {
          closeHelp();
        } else {
          openHelp();
        }
        return;
      }

      // "/" — focus search
      if (e.key === '/') {
        if (window.__docSearchIsOpen && window.__docSearchIsOpen()) return;
        e.preventDefault();
        if (window.__docSearchOpen) window.__docSearchOpen();
      }
    });
  })();

  // ---------------------------------------------------------------------------
  // 15. Mobile TOC Drawer
  //     Clones desktop TOC links into a slide-out drawer for mobile/tablet
  // ---------------------------------------------------------------------------

  (function initMobileToc() {
    var toggleBtn = qs('#mobileTocToggle');
    var overlay = qs('#mobileTocOverlay');
    var drawer = qs('#mobileTocDrawer');
    var closeBtn = qs('#mobileTocClose');
    var mobileList = qs('#mobileTocList');
    var desktopList = qs('#tocList');

    if (!toggleBtn || !drawer || !mobileList || !desktopList) return;

    function syncTocContent() {
      mobileList.innerHTML = desktopList.innerHTML;
      // Add click listeners to close drawer on link click
      var links = mobileList.querySelectorAll('a');
      for (var i = 0; i < links.length; i++) {
        links[i].addEventListener('click', closeMobileToc);
      }
    }

    function openMobileToc() {
      syncTocContent();
      if (overlay) overlay.classList.add('active');
      drawer.classList.add('active');
      drawer.setAttribute('aria-hidden', 'false');
      document.body.style.overflow = 'hidden';
      if (closeBtn) closeBtn.focus();
    }

    function closeMobileToc() {
      if (overlay) overlay.classList.remove('active');
      drawer.classList.remove('active');
      drawer.setAttribute('aria-hidden', 'true');
      document.body.style.overflow = '';
      toggleBtn.focus();
    }

    toggleBtn.addEventListener('click', openMobileToc);
    if (overlay) overlay.addEventListener('click', closeMobileToc);
    if (closeBtn) closeBtn.addEventListener('click', closeMobileToc);

    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && drawer.classList.contains('active')) {
        closeMobileToc();
      }
    });
  })();

})();
