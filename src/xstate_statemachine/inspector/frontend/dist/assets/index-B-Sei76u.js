function eO(e, t) {
  for (var n = 0; n < t.length; n++) {
    const r = t[n];
    if (typeof r != "string" && !Array.isArray(r)) {
      for (const i in r)
        if (i !== "default" && !(i in e)) {
          const o = Object.getOwnPropertyDescriptor(r, i);
          o && Object.defineProperty(e, i, o.get ? o : { enumerable: !0, get: () => r[i] });
        }
    }
  }
  return Object.freeze(Object.defineProperty(e, Symbol.toStringTag, { value: "Module" }));
}
(function () {
  const t = document.createElement("link").relList;
  if (t && t.supports && t.supports("modulepreload")) return;
  for (const i of document.querySelectorAll('link[rel="modulepreload"]')) r(i);
  new MutationObserver((i) => {
    for (const o of i)
      if (o.type === "childList")
        for (const s of o.addedNodes) s.tagName === "LINK" && s.rel === "modulepreload" && r(s);
  }).observe(document, { childList: !0, subtree: !0 });
  function n(i) {
    const o = {};
    return (
      i.integrity && (o.integrity = i.integrity),
      i.referrerPolicy && (o.referrerPolicy = i.referrerPolicy),
      i.crossOrigin === "use-credentials"
        ? (o.credentials = "include")
        : i.crossOrigin === "anonymous"
          ? (o.credentials = "omit")
          : (o.credentials = "same-origin"),
      o
    );
  }
  function r(i) {
    if (i.ep) return;
    i.ep = !0;
    const o = n(i);
    fetch(i.href, o);
  }
})();
var ka =
  typeof globalThis < "u"
    ? globalThis
    : typeof window < "u"
      ? window
      : typeof global < "u"
        ? global
        : typeof self < "u"
          ? self
          : {};
function ay(e) {
  return e && e.__esModule && Object.prototype.hasOwnProperty.call(e, "default") ? e.default : e;
}
var vk = { exports: {} },
  Cl = {},
  yk = { exports: {} },
  ie = {};
/**
 * @license React
 * react.production.min.js
 *
 * Copyright (c) Facebook, Inc. and its affiliates.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */ var oa = Symbol.for("react.element"),
  tO = Symbol.for("react.portal"),
  nO = Symbol.for("react.fragment"),
  rO = Symbol.for("react.strict_mode"),
  iO = Symbol.for("react.profiler"),
  oO = Symbol.for("react.provider"),
  sO = Symbol.for("react.context"),
  aO = Symbol.for("react.forward_ref"),
  uO = Symbol.for("react.suspense"),
  lO = Symbol.for("react.memo"),
  cO = Symbol.for("react.lazy"),
  Aw = Symbol.iterator;
function fO(e) {
  return e === null || typeof e != "object"
    ? null
    : ((e = (Aw && e[Aw]) || e["@@iterator"]), typeof e == "function" ? e : null);
}
var wk = {
    isMounted: function () {
      return !1;
    },
    enqueueForceUpdate: function () {},
    enqueueReplaceState: function () {},
    enqueueSetState: function () {},
  },
  xk = Object.assign,
  _k = {};
function bo(e, t, n) {
  (this.props = e), (this.context = t), (this.refs = _k), (this.updater = n || wk);
}
bo.prototype.isReactComponent = {};
bo.prototype.setState = function (e, t) {
  if (typeof e != "object" && typeof e != "function" && e != null)
    throw Error(
      "setState(...): takes an object of state variables to update or a function which returns an object of state variables.",
    );
  this.updater.enqueueSetState(this, e, t, "setState");
};
bo.prototype.forceUpdate = function (e) {
  this.updater.enqueueForceUpdate(this, e, "forceUpdate");
};
function bk() {}
bk.prototype = bo.prototype;
function uy(e, t, n) {
  (this.props = e), (this.context = t), (this.refs = _k), (this.updater = n || wk);
}
var ly = (uy.prototype = new bk());
ly.constructor = uy;
xk(ly, bo.prototype);
ly.isPureReactComponent = !0;
var Nw = Array.isArray,
  Sk = Object.prototype.hasOwnProperty,
  cy = { current: null },
  Ek = { key: !0, ref: !0, __self: !0, __source: !0 };
function Ck(e, t, n) {
  var r,
    i = {},
    o = null,
    s = null;
  if (t != null)
    for (r in (t.ref !== void 0 && (s = t.ref), t.key !== void 0 && (o = "" + t.key), t))
      Sk.call(t, r) && !Ek.hasOwnProperty(r) && (i[r] = t[r]);
  var a = arguments.length - 2;
  if (a === 1) i.children = n;
  else if (1 < a) {
    for (var u = Array(a), l = 0; l < a; l++) u[l] = arguments[l + 2];
    i.children = u;
  }
  if (e && e.defaultProps) for (r in ((a = e.defaultProps), a)) i[r] === void 0 && (i[r] = a[r]);
  return { $$typeof: oa, type: e, key: o, ref: s, props: i, _owner: cy.current };
}
function dO(e, t) {
  return { $$typeof: oa, type: e.type, key: t, ref: e.ref, props: e.props, _owner: e._owner };
}
function fy(e) {
  return typeof e == "object" && e !== null && e.$$typeof === oa;
}
function hO(e) {
  var t = { "=": "=0", ":": "=2" };
  return (
    "$" +
    e.replace(/[=:]/g, function (n) {
      return t[n];
    })
  );
}
var Mw = /\/+/g;
function Nc(e, t) {
  return typeof e == "object" && e !== null && e.key != null ? hO("" + e.key) : t.toString(36);
}
function cu(e, t, n, r, i) {
  var o = typeof e;
  (o === "undefined" || o === "boolean") && (e = null);
  var s = !1;
  if (e === null) s = !0;
  else
    switch (o) {
      case "string":
      case "number":
        s = !0;
        break;
      case "object":
        switch (e.$$typeof) {
          case oa:
          case tO:
            s = !0;
        }
    }
  if (s)
    return (
      (s = e),
      (i = i(s)),
      (e = r === "" ? "." + Nc(s, 0) : r),
      Nw(i)
        ? ((n = ""),
          e != null && (n = e.replace(Mw, "$&/") + "/"),
          cu(i, t, n, "", function (l) {
            return l;
          }))
        : i != null &&
          (fy(i) &&
            (i = dO(
              i,
              n +
                (!i.key || (s && s.key === i.key) ? "" : ("" + i.key).replace(Mw, "$&/") + "/") +
                e,
            )),
          t.push(i)),
      1
    );
  if (((s = 0), (r = r === "" ? "." : r + ":"), Nw(e)))
    for (var a = 0; a < e.length; a++) {
      o = e[a];
      var u = r + Nc(o, a);
      s += cu(o, t, n, u, i);
    }
  else if (((u = fO(e)), typeof u == "function"))
    for (e = u.call(e), a = 0; !(o = e.next()).done; )
      (o = o.value), (u = r + Nc(o, a++)), (s += cu(o, t, n, u, i));
  else if (o === "object")
    throw (
      ((t = String(e)),
      Error(
        "Objects are not valid as a React child (found: " +
          (t === "[object Object]" ? "object with keys {" + Object.keys(e).join(", ") + "}" : t) +
          "). If you meant to render a collection of children, use an array instead.",
      ))
    );
  return s;
}
function Ra(e, t, n) {
  if (e == null) return e;
  var r = [],
    i = 0;
  return (
    cu(e, r, "", "", function (o) {
      return t.call(n, o, i++);
    }),
    r
  );
}
function pO(e) {
  if (e._status === -1) {
    var t = e._result;
    (t = t()),
      t.then(
        function (n) {
          (e._status === 0 || e._status === -1) && ((e._status = 1), (e._result = n));
        },
        function (n) {
          (e._status === 0 || e._status === -1) && ((e._status = 2), (e._result = n));
        },
      ),
      e._status === -1 && ((e._status = 0), (e._result = t));
  }
  if (e._status === 1) return e._result.default;
  throw e._result;
}
var ut = { current: null },
  fu = { transition: null },
  mO = { ReactCurrentDispatcher: ut, ReactCurrentBatchConfig: fu, ReactCurrentOwner: cy };
function Tk() {
  throw Error("act(...) is not supported in production builds of React.");
}
ie.Children = {
  map: Ra,
  forEach: function (e, t, n) {
    Ra(
      e,
      function () {
        t.apply(this, arguments);
      },
      n,
    );
  },
  count: function (e) {
    var t = 0;
    return (
      Ra(e, function () {
        t++;
      }),
      t
    );
  },
  toArray: function (e) {
    return (
      Ra(e, function (t) {
        return t;
      }) || []
    );
  },
  only: function (e) {
    if (!fy(e))
      throw Error("React.Children.only expected to receive a single React element child.");
    return e;
  },
};
ie.Component = bo;
ie.Fragment = nO;
ie.Profiler = iO;
ie.PureComponent = uy;
ie.StrictMode = rO;
ie.Suspense = uO;
ie.__SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED = mO;
ie.act = Tk;
ie.cloneElement = function (e, t, n) {
  if (e == null)
    throw Error(
      "React.cloneElement(...): The argument must be a React element, but you passed " + e + ".",
    );
  var r = xk({}, e.props),
    i = e.key,
    o = e.ref,
    s = e._owner;
  if (t != null) {
    if (
      (t.ref !== void 0 && ((o = t.ref), (s = cy.current)),
      t.key !== void 0 && (i = "" + t.key),
      e.type && e.type.defaultProps)
    )
      var a = e.type.defaultProps;
    for (u in t)
      Sk.call(t, u) &&
        !Ek.hasOwnProperty(u) &&
        (r[u] = t[u] === void 0 && a !== void 0 ? a[u] : t[u]);
  }
  var u = arguments.length - 2;
  if (u === 1) r.children = n;
  else if (1 < u) {
    a = Array(u);
    for (var l = 0; l < u; l++) a[l] = arguments[l + 2];
    r.children = a;
  }
  return { $$typeof: oa, type: e.type, key: i, ref: o, props: r, _owner: s };
};
ie.createContext = function (e) {
  return (
    (e = {
      $$typeof: sO,
      _currentValue: e,
      _currentValue2: e,
      _threadCount: 0,
      Provider: null,
      Consumer: null,
      _defaultValue: null,
      _globalName: null,
    }),
    (e.Provider = { $$typeof: oO, _context: e }),
    (e.Consumer = e)
  );
};
ie.createElement = Ck;
ie.createFactory = function (e) {
  var t = Ck.bind(null, e);
  return (t.type = e), t;
};
ie.createRef = function () {
  return { current: null };
};
ie.forwardRef = function (e) {
  return { $$typeof: aO, render: e };
};
ie.isValidElement = fy;
ie.lazy = function (e) {
  return { $$typeof: cO, _payload: { _status: -1, _result: e }, _init: pO };
};
ie.memo = function (e, t) {
  return { $$typeof: lO, type: e, compare: t === void 0 ? null : t };
};
ie.startTransition = function (e) {
  var t = fu.transition;
  fu.transition = {};
  try {
    e();
  } finally {
    fu.transition = t;
  }
};
ie.unstable_act = Tk;
ie.useCallback = function (e, t) {
  return ut.current.useCallback(e, t);
};
ie.useContext = function (e) {
  return ut.current.useContext(e);
};
ie.useDebugValue = function () {};
ie.useDeferredValue = function (e) {
  return ut.current.useDeferredValue(e);
};
ie.useEffect = function (e, t) {
  return ut.current.useEffect(e, t);
};
ie.useId = function () {
  return ut.current.useId();
};
ie.useImperativeHandle = function (e, t, n) {
  return ut.current.useImperativeHandle(e, t, n);
};
ie.useInsertionEffect = function (e, t) {
  return ut.current.useInsertionEffect(e, t);
};
ie.useLayoutEffect = function (e, t) {
  return ut.current.useLayoutEffect(e, t);
};
ie.useMemo = function (e, t) {
  return ut.current.useMemo(e, t);
};
ie.useReducer = function (e, t, n) {
  return ut.current.useReducer(e, t, n);
};
ie.useRef = function (e) {
  return ut.current.useRef(e);
};
ie.useState = function (e) {
  return ut.current.useState(e);
};
ie.useSyncExternalStore = function (e, t, n) {
  return ut.current.useSyncExternalStore(e, t, n);
};
ie.useTransition = function () {
  return ut.current.useTransition();
};
ie.version = "18.3.1";
yk.exports = ie;
var _ = yk.exports;
const L = ay(_),
  kk = eO({ __proto__: null, default: L }, [_]);
/**
 * @license React
 * react-jsx-runtime.production.min.js
 *
 * Copyright (c) Facebook, Inc. and its affiliates.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */ var gO = _,
  vO = Symbol.for("react.element"),
  yO = Symbol.for("react.fragment"),
  wO = Object.prototype.hasOwnProperty,
  xO = gO.__SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED.ReactCurrentOwner,
  _O = { key: !0, ref: !0, __self: !0, __source: !0 };
function Rk(e, t, n) {
  var r,
    i = {},
    o = null,
    s = null;
  n !== void 0 && (o = "" + n),
    t.key !== void 0 && (o = "" + t.key),
    t.ref !== void 0 && (s = t.ref);
  for (r in t) wO.call(t, r) && !_O.hasOwnProperty(r) && (i[r] = t[r]);
  if (e && e.defaultProps) for (r in ((t = e.defaultProps), t)) i[r] === void 0 && (i[r] = t[r]);
  return { $$typeof: vO, type: e, key: o, ref: s, props: i, _owner: xO.current };
}
Cl.Fragment = yO;
Cl.jsx = Rk;
Cl.jsxs = Rk;
vk.exports = Cl;
var R = vk.exports,
  Ag = {},
  Pk = { exports: {} },
  Pt = {},
  Ak = { exports: {} },
  Nk = {};
/**
 * @license React
 * scheduler.production.min.js
 *
 * Copyright (c) Facebook, Inc. and its affiliates.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */ (function (e) {
  function t(N, k) {
    var D = N.length;
    N.push(k);
    e: for (; 0 < D; ) {
      var V = (D - 1) >>> 1,
        $ = N[V];
      if (0 < i($, k)) (N[V] = k), (N[D] = $), (D = V);
      else break e;
    }
  }
  function n(N) {
    return N.length === 0 ? null : N[0];
  }
  function r(N) {
    if (N.length === 0) return null;
    var k = N[0],
      D = N.pop();
    if (D !== k) {
      N[0] = D;
      e: for (var V = 0, $ = N.length, U = $ >>> 1; V < U; ) {
        var B = 2 * (V + 1) - 1,
          W = N[B],
          X = B + 1,
          ee = N[X];
        if (0 > i(W, D))
          X < $ && 0 > i(ee, W)
            ? ((N[V] = ee), (N[X] = D), (V = X))
            : ((N[V] = W), (N[B] = D), (V = B));
        else if (X < $ && 0 > i(ee, D)) (N[V] = ee), (N[X] = D), (V = X);
        else break e;
      }
    }
    return k;
  }
  function i(N, k) {
    var D = N.sortIndex - k.sortIndex;
    return D !== 0 ? D : N.id - k.id;
  }
  if (typeof performance == "object" && typeof performance.now == "function") {
    var o = performance;
    e.unstable_now = function () {
      return o.now();
    };
  } else {
    var s = Date,
      a = s.now();
    e.unstable_now = function () {
      return s.now() - a;
    };
  }
  var u = [],
    l = [],
    c = 1,
    f = null,
    d = 3,
    h = !1,
    v = !1,
    p = !1,
    y = typeof setTimeout == "function" ? setTimeout : null,
    m = typeof clearTimeout == "function" ? clearTimeout : null,
    g = typeof setImmediate < "u" ? setImmediate : null;
  typeof navigator < "u" &&
    navigator.scheduling !== void 0 &&
    navigator.scheduling.isInputPending !== void 0 &&
    navigator.scheduling.isInputPending.bind(navigator.scheduling);
  function w(N) {
    for (var k = n(l); k !== null; ) {
      if (k.callback === null) r(l);
      else if (k.startTime <= N) r(l), (k.sortIndex = k.expirationTime), t(u, k);
      else break;
      k = n(l);
    }
  }
  function x(N) {
    if (((p = !1), w(N), !v))
      if (n(u) !== null) (v = !0), A(b);
      else {
        var k = n(l);
        k !== null && F(x, k.startTime - N);
      }
  }
  function b(N, k) {
    (v = !1), p && ((p = !1), m(T), (T = -1)), (h = !0);
    var D = d;
    try {
      for (w(k), f = n(u); f !== null && (!(f.expirationTime > k) || (N && !I())); ) {
        var V = f.callback;
        if (typeof V == "function") {
          (f.callback = null), (d = f.priorityLevel);
          var $ = V(f.expirationTime <= k);
          (k = e.unstable_now()),
            typeof $ == "function" ? (f.callback = $) : f === n(u) && r(u),
            w(k);
        } else r(u);
        f = n(u);
      }
      if (f !== null) var U = !0;
      else {
        var B = n(l);
        B !== null && F(x, B.startTime - k), (U = !1);
      }
      return U;
    } finally {
      (f = null), (d = D), (h = !1);
    }
  }
  var E = !1,
    C = null,
    T = -1,
    P = 5,
    M = -1;
  function I() {
    return !(e.unstable_now() - M < P);
  }
  function j() {
    if (C !== null) {
      var N = e.unstable_now();
      M = N;
      var k = !0;
      try {
        k = C(!0, N);
      } finally {
        k ? q() : ((E = !1), (C = null));
      }
    } else E = !1;
  }
  var q;
  if (typeof g == "function")
    q = function () {
      g(j);
    };
  else if (typeof MessageChannel < "u") {
    var S = new MessageChannel(),
      O = S.port2;
    (S.port1.onmessage = j),
      (q = function () {
        O.postMessage(null);
      });
  } else
    q = function () {
      y(j, 0);
    };
  function A(N) {
    (C = N), E || ((E = !0), q());
  }
  function F(N, k) {
    T = y(function () {
      N(e.unstable_now());
    }, k);
  }
  (e.unstable_IdlePriority = 5),
    (e.unstable_ImmediatePriority = 1),
    (e.unstable_LowPriority = 4),
    (e.unstable_NormalPriority = 3),
    (e.unstable_Profiling = null),
    (e.unstable_UserBlockingPriority = 2),
    (e.unstable_cancelCallback = function (N) {
      N.callback = null;
    }),
    (e.unstable_continueExecution = function () {
      v || h || ((v = !0), A(b));
    }),
    (e.unstable_forceFrameRate = function (N) {
      0 > N || 125 < N
        ? console.error(
            "forceFrameRate takes a positive int between 0 and 125, forcing frame rates higher than 125 fps is not supported",
          )
        : (P = 0 < N ? Math.floor(1e3 / N) : 5);
    }),
    (e.unstable_getCurrentPriorityLevel = function () {
      return d;
    }),
    (e.unstable_getFirstCallbackNode = function () {
      return n(u);
    }),
    (e.unstable_next = function (N) {
      switch (d) {
        case 1:
        case 2:
        case 3:
          var k = 3;
          break;
        default:
          k = d;
      }
      var D = d;
      d = k;
      try {
        return N();
      } finally {
        d = D;
      }
    }),
    (e.unstable_pauseExecution = function () {}),
    (e.unstable_requestPaint = function () {}),
    (e.unstable_runWithPriority = function (N, k) {
      switch (N) {
        case 1:
        case 2:
        case 3:
        case 4:
        case 5:
          break;
        default:
          N = 3;
      }
      var D = d;
      d = N;
      try {
        return k();
      } finally {
        d = D;
      }
    }),
    (e.unstable_scheduleCallback = function (N, k, D) {
      var V = e.unstable_now();
      switch (
        (typeof D == "object" && D !== null
          ? ((D = D.delay), (D = typeof D == "number" && 0 < D ? V + D : V))
          : (D = V),
        N)
      ) {
        case 1:
          var $ = -1;
          break;
        case 2:
          $ = 250;
          break;
        case 5:
          $ = 1073741823;
          break;
        case 4:
          $ = 1e4;
          break;
        default:
          $ = 5e3;
      }
      return (
        ($ = D + $),
        (N = {
          id: c++,
          callback: k,
          priorityLevel: N,
          startTime: D,
          expirationTime: $,
          sortIndex: -1,
        }),
        D > V
          ? ((N.sortIndex = D),
            t(l, N),
            n(u) === null && N === n(l) && (p ? (m(T), (T = -1)) : (p = !0), F(x, D - V)))
          : ((N.sortIndex = $), t(u, N), v || h || ((v = !0), A(b))),
        N
      );
    }),
    (e.unstable_shouldYield = I),
    (e.unstable_wrapCallback = function (N) {
      var k = d;
      return function () {
        var D = d;
        d = k;
        try {
          return N.apply(this, arguments);
        } finally {
          d = D;
        }
      };
    });
})(Nk);
Ak.exports = Nk;
var bO = Ak.exports;
/**
 * @license React
 * react-dom.production.min.js
 *
 * Copyright (c) Facebook, Inc. and its affiliates.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */ var SO = _,
  Tt = bO;
function z(e) {
  for (
    var t = "https://reactjs.org/docs/error-decoder.html?invariant=" + e, n = 1;
    n < arguments.length;
    n++
  )
    t += "&args[]=" + encodeURIComponent(arguments[n]);
  return (
    "Minified React error #" +
    e +
    "; visit " +
    t +
    " for the full message or use the non-minified dev environment for full errors and additional helpful warnings."
  );
}
var Mk = new Set(),
  Ps = {};
function di(e, t) {
  ro(e, t), ro(e + "Capture", t);
}
function ro(e, t) {
  for (Ps[e] = t, e = 0; e < t.length; e++) Mk.add(t[e]);
}
var Bn = !(
    typeof window > "u" ||
    typeof window.document > "u" ||
    typeof window.document.createElement > "u"
  ),
  Ng = Object.prototype.hasOwnProperty,
  EO =
    /^[:A-Z_a-z\u00C0-\u00D6\u00D8-\u00F6\u00F8-\u02FF\u0370-\u037D\u037F-\u1FFF\u200C-\u200D\u2070-\u218F\u2C00-\u2FEF\u3001-\uD7FF\uF900-\uFDCF\uFDF0-\uFFFD][:A-Z_a-z\u00C0-\u00D6\u00D8-\u00F6\u00F8-\u02FF\u0370-\u037D\u037F-\u1FFF\u200C-\u200D\u2070-\u218F\u2C00-\u2FEF\u3001-\uD7FF\uF900-\uFDCF\uFDF0-\uFFFD\-.0-9\u00B7\u0300-\u036F\u203F-\u2040]*$/,
  Iw = {},
  Dw = {};
function CO(e) {
  return Ng.call(Dw, e) ? !0 : Ng.call(Iw, e) ? !1 : EO.test(e) ? (Dw[e] = !0) : ((Iw[e] = !0), !1);
}
function TO(e, t, n, r) {
  if (n !== null && n.type === 0) return !1;
  switch (typeof t) {
    case "function":
    case "symbol":
      return !0;
    case "boolean":
      return r
        ? !1
        : n !== null
          ? !n.acceptsBooleans
          : ((e = e.toLowerCase().slice(0, 5)), e !== "data-" && e !== "aria-");
    default:
      return !1;
  }
}
function kO(e, t, n, r) {
  if (t === null || typeof t > "u" || TO(e, t, n, r)) return !0;
  if (r) return !1;
  if (n !== null)
    switch (n.type) {
      case 3:
        return !t;
      case 4:
        return t === !1;
      case 5:
        return isNaN(t);
      case 6:
        return isNaN(t) || 1 > t;
    }
  return !1;
}
function lt(e, t, n, r, i, o, s) {
  (this.acceptsBooleans = t === 2 || t === 3 || t === 4),
    (this.attributeName = r),
    (this.attributeNamespace = i),
    (this.mustUseProperty = n),
    (this.propertyName = e),
    (this.type = t),
    (this.sanitizeURL = o),
    (this.removeEmptyString = s);
}
var Xe = {};
"children dangerouslySetInnerHTML defaultValue defaultChecked innerHTML suppressContentEditableWarning suppressHydrationWarning style"
  .split(" ")
  .forEach(function (e) {
    Xe[e] = new lt(e, 0, !1, e, null, !1, !1);
  });
[
  ["acceptCharset", "accept-charset"],
  ["className", "class"],
  ["htmlFor", "for"],
  ["httpEquiv", "http-equiv"],
].forEach(function (e) {
  var t = e[0];
  Xe[t] = new lt(t, 1, !1, e[1], null, !1, !1);
});
["contentEditable", "draggable", "spellCheck", "value"].forEach(function (e) {
  Xe[e] = new lt(e, 2, !1, e.toLowerCase(), null, !1, !1);
});
["autoReverse", "externalResourcesRequired", "focusable", "preserveAlpha"].forEach(function (e) {
  Xe[e] = new lt(e, 2, !1, e, null, !1, !1);
});
"allowFullScreen async autoFocus autoPlay controls default defer disabled disablePictureInPicture disableRemotePlayback formNoValidate hidden loop noModule noValidate open playsInline readOnly required reversed scoped seamless itemScope"
  .split(" ")
  .forEach(function (e) {
    Xe[e] = new lt(e, 3, !1, e.toLowerCase(), null, !1, !1);
  });
["checked", "multiple", "muted", "selected"].forEach(function (e) {
  Xe[e] = new lt(e, 3, !0, e, null, !1, !1);
});
["capture", "download"].forEach(function (e) {
  Xe[e] = new lt(e, 4, !1, e, null, !1, !1);
});
["cols", "rows", "size", "span"].forEach(function (e) {
  Xe[e] = new lt(e, 6, !1, e, null, !1, !1);
});
["rowSpan", "start"].forEach(function (e) {
  Xe[e] = new lt(e, 5, !1, e.toLowerCase(), null, !1, !1);
});
var dy = /[\-:]([a-z])/g;
function hy(e) {
  return e[1].toUpperCase();
}
"accent-height alignment-baseline arabic-form baseline-shift cap-height clip-path clip-rule color-interpolation color-interpolation-filters color-profile color-rendering dominant-baseline enable-background fill-opacity fill-rule flood-color flood-opacity font-family font-size font-size-adjust font-stretch font-style font-variant font-weight glyph-name glyph-orientation-horizontal glyph-orientation-vertical horiz-adv-x horiz-origin-x image-rendering letter-spacing lighting-color marker-end marker-mid marker-start overline-position overline-thickness paint-order panose-1 pointer-events rendering-intent shape-rendering stop-color stop-opacity strikethrough-position strikethrough-thickness stroke-dasharray stroke-dashoffset stroke-linecap stroke-linejoin stroke-miterlimit stroke-opacity stroke-width text-anchor text-decoration text-rendering underline-position underline-thickness unicode-bidi unicode-range units-per-em v-alphabetic v-hanging v-ideographic v-mathematical vector-effect vert-adv-y vert-origin-x vert-origin-y word-spacing writing-mode xmlns:xlink x-height"
  .split(" ")
  .forEach(function (e) {
    var t = e.replace(dy, hy);
    Xe[t] = new lt(t, 1, !1, e, null, !1, !1);
  });
"xlink:actuate xlink:arcrole xlink:role xlink:show xlink:title xlink:type"
  .split(" ")
  .forEach(function (e) {
    var t = e.replace(dy, hy);
    Xe[t] = new lt(t, 1, !1, e, "http://www.w3.org/1999/xlink", !1, !1);
  });
["xml:base", "xml:lang", "xml:space"].forEach(function (e) {
  var t = e.replace(dy, hy);
  Xe[t] = new lt(t, 1, !1, e, "http://www.w3.org/XML/1998/namespace", !1, !1);
});
["tabIndex", "crossOrigin"].forEach(function (e) {
  Xe[e] = new lt(e, 1, !1, e.toLowerCase(), null, !1, !1);
});
Xe.xlinkHref = new lt("xlinkHref", 1, !1, "xlink:href", "http://www.w3.org/1999/xlink", !0, !1);
["src", "href", "action", "formAction"].forEach(function (e) {
  Xe[e] = new lt(e, 1, !1, e.toLowerCase(), null, !0, !0);
});
function py(e, t, n, r) {
  var i = Xe.hasOwnProperty(t) ? Xe[t] : null;
  (i !== null
    ? i.type !== 0
    : r || !(2 < t.length) || (t[0] !== "o" && t[0] !== "O") || (t[1] !== "n" && t[1] !== "N")) &&
    (kO(t, n, i, r) && (n = null),
    r || i === null
      ? CO(t) && (n === null ? e.removeAttribute(t) : e.setAttribute(t, "" + n))
      : i.mustUseProperty
        ? (e[i.propertyName] = n === null ? (i.type === 3 ? !1 : "") : n)
        : ((t = i.attributeName),
          (r = i.attributeNamespace),
          n === null
            ? e.removeAttribute(t)
            : ((i = i.type),
              (n = i === 3 || (i === 4 && n === !0) ? "" : "" + n),
              r ? e.setAttributeNS(r, t, n) : e.setAttribute(t, n))));
}
var Qn = SO.__SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED,
  Pa = Symbol.for("react.element"),
  Ri = Symbol.for("react.portal"),
  Pi = Symbol.for("react.fragment"),
  my = Symbol.for("react.strict_mode"),
  Mg = Symbol.for("react.profiler"),
  Ik = Symbol.for("react.provider"),
  Dk = Symbol.for("react.context"),
  gy = Symbol.for("react.forward_ref"),
  Ig = Symbol.for("react.suspense"),
  Dg = Symbol.for("react.suspense_list"),
  vy = Symbol.for("react.memo"),
  lr = Symbol.for("react.lazy"),
  Ok = Symbol.for("react.offscreen"),
  Ow = Symbol.iterator;
function Lo(e) {
  return e === null || typeof e != "object"
    ? null
    : ((e = (Ow && e[Ow]) || e["@@iterator"]), typeof e == "function" ? e : null);
}
var Se = Object.assign,
  Mc;
function Qo(e) {
  if (Mc === void 0)
    try {
      throw Error();
    } catch (n) {
      var t = n.stack.trim().match(/\n( *(at )?)/);
      Mc = (t && t[1]) || "";
    }
  return (
    `
` +
    Mc +
    e
  );
}
var Ic = !1;
function Dc(e, t) {
  if (!e || Ic) return "";
  Ic = !0;
  var n = Error.prepareStackTrace;
  Error.prepareStackTrace = void 0;
  try {
    if (t)
      if (
        ((t = function () {
          throw Error();
        }),
        Object.defineProperty(t.prototype, "props", {
          set: function () {
            throw Error();
          },
        }),
        typeof Reflect == "object" && Reflect.construct)
      ) {
        try {
          Reflect.construct(t, []);
        } catch (l) {
          var r = l;
        }
        Reflect.construct(e, [], t);
      } else {
        try {
          t.call();
        } catch (l) {
          r = l;
        }
        e.call(t.prototype);
      }
    else {
      try {
        throw Error();
      } catch (l) {
        r = l;
      }
      e();
    }
  } catch (l) {
    if (l && r && typeof l.stack == "string") {
      for (
        var i = l.stack.split(`
`),
          o = r.stack.split(`
`),
          s = i.length - 1,
          a = o.length - 1;
        1 <= s && 0 <= a && i[s] !== o[a];

      )
        a--;
      for (; 1 <= s && 0 <= a; s--, a--)
        if (i[s] !== o[a]) {
          if (s !== 1 || a !== 1)
            do
              if ((s--, a--, 0 > a || i[s] !== o[a])) {
                var u =
                  `
` + i[s].replace(" at new ", " at ");
                return (
                  e.displayName &&
                    u.includes("<anonymous>") &&
                    (u = u.replace("<anonymous>", e.displayName)),
                  u
                );
              }
            while (1 <= s && 0 <= a);
          break;
        }
    }
  } finally {
    (Ic = !1), (Error.prepareStackTrace = n);
  }
  return (e = e ? e.displayName || e.name : "") ? Qo(e) : "";
}
function RO(e) {
  switch (e.tag) {
    case 5:
      return Qo(e.type);
    case 16:
      return Qo("Lazy");
    case 13:
      return Qo("Suspense");
    case 19:
      return Qo("SuspenseList");
    case 0:
    case 2:
    case 15:
      return (e = Dc(e.type, !1)), e;
    case 11:
      return (e = Dc(e.type.render, !1)), e;
    case 1:
      return (e = Dc(e.type, !0)), e;
    default:
      return "";
  }
}
function Og(e) {
  if (e == null) return null;
  if (typeof e == "function") return e.displayName || e.name || null;
  if (typeof e == "string") return e;
  switch (e) {
    case Pi:
      return "Fragment";
    case Ri:
      return "Portal";
    case Mg:
      return "Profiler";
    case my:
      return "StrictMode";
    case Ig:
      return "Suspense";
    case Dg:
      return "SuspenseList";
  }
  if (typeof e == "object")
    switch (e.$$typeof) {
      case Dk:
        return (e.displayName || "Context") + ".Consumer";
      case Ik:
        return (e._context.displayName || "Context") + ".Provider";
      case gy:
        var t = e.render;
        return (
          (e = e.displayName),
          e ||
            ((e = t.displayName || t.name || ""),
            (e = e !== "" ? "ForwardRef(" + e + ")" : "ForwardRef")),
          e
        );
      case vy:
        return (t = e.displayName || null), t !== null ? t : Og(e.type) || "Memo";
      case lr:
        (t = e._payload), (e = e._init);
        try {
          return Og(e(t));
        } catch {}
    }
  return null;
}
function PO(e) {
  var t = e.type;
  switch (e.tag) {
    case 24:
      return "Cache";
    case 9:
      return (t.displayName || "Context") + ".Consumer";
    case 10:
      return (t._context.displayName || "Context") + ".Provider";
    case 18:
      return "DehydratedFragment";
    case 11:
      return (
        (e = t.render),
        (e = e.displayName || e.name || ""),
        t.displayName || (e !== "" ? "ForwardRef(" + e + ")" : "ForwardRef")
      );
    case 7:
      return "Fragment";
    case 5:
      return t;
    case 4:
      return "Portal";
    case 3:
      return "Root";
    case 6:
      return "Text";
    case 16:
      return Og(t);
    case 8:
      return t === my ? "StrictMode" : "Mode";
    case 22:
      return "Offscreen";
    case 12:
      return "Profiler";
    case 21:
      return "Scope";
    case 13:
      return "Suspense";
    case 19:
      return "SuspenseList";
    case 25:
      return "TracingMarker";
    case 1:
    case 0:
    case 17:
    case 2:
    case 14:
    case 15:
      if (typeof t == "function") return t.displayName || t.name || null;
      if (typeof t == "string") return t;
  }
  return null;
}
function Pr(e) {
  switch (typeof e) {
    case "boolean":
    case "number":
    case "string":
    case "undefined":
      return e;
    case "object":
      return e;
    default:
      return "";
  }
}
function Lk(e) {
  var t = e.type;
  return (e = e.nodeName) && e.toLowerCase() === "input" && (t === "checkbox" || t === "radio");
}
function AO(e) {
  var t = Lk(e) ? "checked" : "value",
    n = Object.getOwnPropertyDescriptor(e.constructor.prototype, t),
    r = "" + e[t];
  if (
    !e.hasOwnProperty(t) &&
    typeof n < "u" &&
    typeof n.get == "function" &&
    typeof n.set == "function"
  ) {
    var i = n.get,
      o = n.set;
    return (
      Object.defineProperty(e, t, {
        configurable: !0,
        get: function () {
          return i.call(this);
        },
        set: function (s) {
          (r = "" + s), o.call(this, s);
        },
      }),
      Object.defineProperty(e, t, { enumerable: n.enumerable }),
      {
        getValue: function () {
          return r;
        },
        setValue: function (s) {
          r = "" + s;
        },
        stopTracking: function () {
          (e._valueTracker = null), delete e[t];
        },
      }
    );
  }
}
function Aa(e) {
  e._valueTracker || (e._valueTracker = AO(e));
}
function Fk(e) {
  if (!e) return !1;
  var t = e._valueTracker;
  if (!t) return !0;
  var n = t.getValue(),
    r = "";
  return (
    e && (r = Lk(e) ? (e.checked ? "true" : "false") : e.value),
    (e = r),
    e !== n ? (t.setValue(e), !0) : !1
  );
}
function Du(e) {
  if (((e = e || (typeof document < "u" ? document : void 0)), typeof e > "u")) return null;
  try {
    return e.activeElement || e.body;
  } catch {
    return e.body;
  }
}
function Lg(e, t) {
  var n = t.checked;
  return Se({}, t, {
    defaultChecked: void 0,
    defaultValue: void 0,
    value: void 0,
    checked: n ?? e._wrapperState.initialChecked,
  });
}
function Lw(e, t) {
  var n = t.defaultValue == null ? "" : t.defaultValue,
    r = t.checked != null ? t.checked : t.defaultChecked;
  (n = Pr(t.value != null ? t.value : n)),
    (e._wrapperState = {
      initialChecked: r,
      initialValue: n,
      controlled: t.type === "checkbox" || t.type === "radio" ? t.checked != null : t.value != null,
    });
}
function jk(e, t) {
  (t = t.checked), t != null && py(e, "checked", t, !1);
}
function Fg(e, t) {
  jk(e, t);
  var n = Pr(t.value),
    r = t.type;
  if (n != null)
    r === "number"
      ? ((n === 0 && e.value === "") || e.value != n) && (e.value = "" + n)
      : e.value !== "" + n && (e.value = "" + n);
  else if (r === "submit" || r === "reset") {
    e.removeAttribute("value");
    return;
  }
  t.hasOwnProperty("value")
    ? jg(e, t.type, n)
    : t.hasOwnProperty("defaultValue") && jg(e, t.type, Pr(t.defaultValue)),
    t.checked == null && t.defaultChecked != null && (e.defaultChecked = !!t.defaultChecked);
}
function Fw(e, t, n) {
  if (t.hasOwnProperty("value") || t.hasOwnProperty("defaultValue")) {
    var r = t.type;
    if (!((r !== "submit" && r !== "reset") || (t.value !== void 0 && t.value !== null))) return;
    (t = "" + e._wrapperState.initialValue),
      n || t === e.value || (e.value = t),
      (e.defaultValue = t);
  }
  (n = e.name),
    n !== "" && (e.name = ""),
    (e.defaultChecked = !!e._wrapperState.initialChecked),
    n !== "" && (e.name = n);
}
function jg(e, t, n) {
  (t !== "number" || Du(e.ownerDocument) !== e) &&
    (n == null
      ? (e.defaultValue = "" + e._wrapperState.initialValue)
      : e.defaultValue !== "" + n && (e.defaultValue = "" + n));
}
var Jo = Array.isArray;
function Gi(e, t, n, r) {
  if (((e = e.options), t)) {
    t = {};
    for (var i = 0; i < n.length; i++) t["$" + n[i]] = !0;
    for (n = 0; n < e.length; n++)
      (i = t.hasOwnProperty("$" + e[n].value)),
        e[n].selected !== i && (e[n].selected = i),
        i && r && (e[n].defaultSelected = !0);
  } else {
    for (n = "" + Pr(n), t = null, i = 0; i < e.length; i++) {
      if (e[i].value === n) {
        (e[i].selected = !0), r && (e[i].defaultSelected = !0);
        return;
      }
      t !== null || e[i].disabled || (t = e[i]);
    }
    t !== null && (t.selected = !0);
  }
}
function Vg(e, t) {
  if (t.dangerouslySetInnerHTML != null) throw Error(z(91));
  return Se({}, t, {
    value: void 0,
    defaultValue: void 0,
    children: "" + e._wrapperState.initialValue,
  });
}
function jw(e, t) {
  var n = t.value;
  if (n == null) {
    if (((n = t.children), (t = t.defaultValue), n != null)) {
      if (t != null) throw Error(z(92));
      if (Jo(n)) {
        if (1 < n.length) throw Error(z(93));
        n = n[0];
      }
      t = n;
    }
    t == null && (t = ""), (n = t);
  }
  e._wrapperState = { initialValue: Pr(n) };
}
function Vk(e, t) {
  var n = Pr(t.value),
    r = Pr(t.defaultValue);
  n != null &&
    ((n = "" + n),
    n !== e.value && (e.value = n),
    t.defaultValue == null && e.defaultValue !== n && (e.defaultValue = n)),
    r != null && (e.defaultValue = "" + r);
}
function Vw(e) {
  var t = e.textContent;
  t === e._wrapperState.initialValue && t !== "" && t !== null && (e.value = t);
}
function qk(e) {
  switch (e) {
    case "svg":
      return "http://www.w3.org/2000/svg";
    case "math":
      return "http://www.w3.org/1998/Math/MathML";
    default:
      return "http://www.w3.org/1999/xhtml";
  }
}
function qg(e, t) {
  return e == null || e === "http://www.w3.org/1999/xhtml"
    ? qk(t)
    : e === "http://www.w3.org/2000/svg" && t === "foreignObject"
      ? "http://www.w3.org/1999/xhtml"
      : e;
}
var Na,
  $k = (function (e) {
    return typeof MSApp < "u" && MSApp.execUnsafeLocalFunction
      ? function (t, n, r, i) {
          MSApp.execUnsafeLocalFunction(function () {
            return e(t, n, r, i);
          });
        }
      : e;
  })(function (e, t) {
    if (e.namespaceURI !== "http://www.w3.org/2000/svg" || "innerHTML" in e) e.innerHTML = t;
    else {
      for (
        Na = Na || document.createElement("div"),
          Na.innerHTML = "<svg>" + t.valueOf().toString() + "</svg>",
          t = Na.firstChild;
        e.firstChild;

      )
        e.removeChild(e.firstChild);
      for (; t.firstChild; ) e.appendChild(t.firstChild);
    }
  });
function As(e, t) {
  if (t) {
    var n = e.firstChild;
    if (n && n === e.lastChild && n.nodeType === 3) {
      n.nodeValue = t;
      return;
    }
  }
  e.textContent = t;
}
var ps = {
    animationIterationCount: !0,
    aspectRatio: !0,
    borderImageOutset: !0,
    borderImageSlice: !0,
    borderImageWidth: !0,
    boxFlex: !0,
    boxFlexGroup: !0,
    boxOrdinalGroup: !0,
    columnCount: !0,
    columns: !0,
    flex: !0,
    flexGrow: !0,
    flexPositive: !0,
    flexShrink: !0,
    flexNegative: !0,
    flexOrder: !0,
    gridArea: !0,
    gridRow: !0,
    gridRowEnd: !0,
    gridRowSpan: !0,
    gridRowStart: !0,
    gridColumn: !0,
    gridColumnEnd: !0,
    gridColumnSpan: !0,
    gridColumnStart: !0,
    fontWeight: !0,
    lineClamp: !0,
    lineHeight: !0,
    opacity: !0,
    order: !0,
    orphans: !0,
    tabSize: !0,
    widows: !0,
    zIndex: !0,
    zoom: !0,
    fillOpacity: !0,
    floodOpacity: !0,
    stopOpacity: !0,
    strokeDasharray: !0,
    strokeDashoffset: !0,
    strokeMiterlimit: !0,
    strokeOpacity: !0,
    strokeWidth: !0,
  },
  NO = ["Webkit", "ms", "Moz", "O"];
Object.keys(ps).forEach(function (e) {
  NO.forEach(function (t) {
    (t = t + e.charAt(0).toUpperCase() + e.substring(1)), (ps[t] = ps[e]);
  });
});
function zk(e, t, n) {
  return t == null || typeof t == "boolean" || t === ""
    ? ""
    : n || typeof t != "number" || t === 0 || (ps.hasOwnProperty(e) && ps[e])
      ? ("" + t).trim()
      : t + "px";
}
function Bk(e, t) {
  e = e.style;
  for (var n in t)
    if (t.hasOwnProperty(n)) {
      var r = n.indexOf("--") === 0,
        i = zk(n, t[n], r);
      n === "float" && (n = "cssFloat"), r ? e.setProperty(n, i) : (e[n] = i);
    }
}
var MO = Se(
  { menuitem: !0 },
  {
    area: !0,
    base: !0,
    br: !0,
    col: !0,
    embed: !0,
    hr: !0,
    img: !0,
    input: !0,
    keygen: !0,
    link: !0,
    meta: !0,
    param: !0,
    source: !0,
    track: !0,
    wbr: !0,
  },
);
function $g(e, t) {
  if (t) {
    if (MO[e] && (t.children != null || t.dangerouslySetInnerHTML != null)) throw Error(z(137, e));
    if (t.dangerouslySetInnerHTML != null) {
      if (t.children != null) throw Error(z(60));
      if (typeof t.dangerouslySetInnerHTML != "object" || !("__html" in t.dangerouslySetInnerHTML))
        throw Error(z(61));
    }
    if (t.style != null && typeof t.style != "object") throw Error(z(62));
  }
}
function zg(e, t) {
  if (e.indexOf("-") === -1) return typeof t.is == "string";
  switch (e) {
    case "annotation-xml":
    case "color-profile":
    case "font-face":
    case "font-face-src":
    case "font-face-uri":
    case "font-face-format":
    case "font-face-name":
    case "missing-glyph":
      return !1;
    default:
      return !0;
  }
}
var Bg = null;
function yy(e) {
  return (
    (e = e.target || e.srcElement || window),
    e.correspondingUseElement && (e = e.correspondingUseElement),
    e.nodeType === 3 ? e.parentNode : e
  );
}
var Ug = null,
  Wi = null,
  Ki = null;
function qw(e) {
  if ((e = ua(e))) {
    if (typeof Ug != "function") throw Error(z(280));
    var t = e.stateNode;
    t && ((t = Al(t)), Ug(e.stateNode, e.type, t));
  }
}
function Uk(e) {
  Wi ? (Ki ? Ki.push(e) : (Ki = [e])) : (Wi = e);
}
function Hk() {
  if (Wi) {
    var e = Wi,
      t = Ki;
    if (((Ki = Wi = null), qw(e), t)) for (e = 0; e < t.length; e++) qw(t[e]);
  }
}
function Gk(e, t) {
  return e(t);
}
function Wk() {}
var Oc = !1;
function Kk(e, t, n) {
  if (Oc) return e(t, n);
  Oc = !0;
  try {
    return Gk(e, t, n);
  } finally {
    (Oc = !1), (Wi !== null || Ki !== null) && (Wk(), Hk());
  }
}
function Ns(e, t) {
  var n = e.stateNode;
  if (n === null) return null;
  var r = Al(n);
  if (r === null) return null;
  n = r[t];
  e: switch (t) {
    case "onClick":
    case "onClickCapture":
    case "onDoubleClick":
    case "onDoubleClickCapture":
    case "onMouseDown":
    case "onMouseDownCapture":
    case "onMouseMove":
    case "onMouseMoveCapture":
    case "onMouseUp":
    case "onMouseUpCapture":
    case "onMouseEnter":
      (r = !r.disabled) ||
        ((e = e.type),
        (r = !(e === "button" || e === "input" || e === "select" || e === "textarea"))),
        (e = !r);
      break e;
    default:
      e = !1;
  }
  if (e) return null;
  if (n && typeof n != "function") throw Error(z(231, t, typeof n));
  return n;
}
var Hg = !1;
if (Bn)
  try {
    var Fo = {};
    Object.defineProperty(Fo, "passive", {
      get: function () {
        Hg = !0;
      },
    }),
      window.addEventListener("test", Fo, Fo),
      window.removeEventListener("test", Fo, Fo);
  } catch {
    Hg = !1;
  }
function IO(e, t, n, r, i, o, s, a, u) {
  var l = Array.prototype.slice.call(arguments, 3);
  try {
    t.apply(n, l);
  } catch (c) {
    this.onError(c);
  }
}
var ms = !1,
  Ou = null,
  Lu = !1,
  Gg = null,
  DO = {
    onError: function (e) {
      (ms = !0), (Ou = e);
    },
  };
function OO(e, t, n, r, i, o, s, a, u) {
  (ms = !1), (Ou = null), IO.apply(DO, arguments);
}
function LO(e, t, n, r, i, o, s, a, u) {
  if ((OO.apply(this, arguments), ms)) {
    if (ms) {
      var l = Ou;
      (ms = !1), (Ou = null);
    } else throw Error(z(198));
    Lu || ((Lu = !0), (Gg = l));
  }
}
function hi(e) {
  var t = e,
    n = e;
  if (e.alternate) for (; t.return; ) t = t.return;
  else {
    e = t;
    do (t = e), t.flags & 4098 && (n = t.return), (e = t.return);
    while (e);
  }
  return t.tag === 3 ? n : null;
}
function Yk(e) {
  if (e.tag === 13) {
    var t = e.memoizedState;
    if ((t === null && ((e = e.alternate), e !== null && (t = e.memoizedState)), t !== null))
      return t.dehydrated;
  }
  return null;
}
function $w(e) {
  if (hi(e) !== e) throw Error(z(188));
}
function FO(e) {
  var t = e.alternate;
  if (!t) {
    if (((t = hi(e)), t === null)) throw Error(z(188));
    return t !== e ? null : e;
  }
  for (var n = e, r = t; ; ) {
    var i = n.return;
    if (i === null) break;
    var o = i.alternate;
    if (o === null) {
      if (((r = i.return), r !== null)) {
        n = r;
        continue;
      }
      break;
    }
    if (i.child === o.child) {
      for (o = i.child; o; ) {
        if (o === n) return $w(i), e;
        if (o === r) return $w(i), t;
        o = o.sibling;
      }
      throw Error(z(188));
    }
    if (n.return !== r.return) (n = i), (r = o);
    else {
      for (var s = !1, a = i.child; a; ) {
        if (a === n) {
          (s = !0), (n = i), (r = o);
          break;
        }
        if (a === r) {
          (s = !0), (r = i), (n = o);
          break;
        }
        a = a.sibling;
      }
      if (!s) {
        for (a = o.child; a; ) {
          if (a === n) {
            (s = !0), (n = o), (r = i);
            break;
          }
          if (a === r) {
            (s = !0), (r = o), (n = i);
            break;
          }
          a = a.sibling;
        }
        if (!s) throw Error(z(189));
      }
    }
    if (n.alternate !== r) throw Error(z(190));
  }
  if (n.tag !== 3) throw Error(z(188));
  return n.stateNode.current === n ? e : t;
}
function Xk(e) {
  return (e = FO(e)), e !== null ? Zk(e) : null;
}
function Zk(e) {
  if (e.tag === 5 || e.tag === 6) return e;
  for (e = e.child; e !== null; ) {
    var t = Zk(e);
    if (t !== null) return t;
    e = e.sibling;
  }
  return null;
}
var Qk = Tt.unstable_scheduleCallback,
  zw = Tt.unstable_cancelCallback,
  jO = Tt.unstable_shouldYield,
  VO = Tt.unstable_requestPaint,
  Ne = Tt.unstable_now,
  qO = Tt.unstable_getCurrentPriorityLevel,
  wy = Tt.unstable_ImmediatePriority,
  Jk = Tt.unstable_UserBlockingPriority,
  Fu = Tt.unstable_NormalPriority,
  $O = Tt.unstable_LowPriority,
  eR = Tt.unstable_IdlePriority,
  Tl = null,
  vn = null;
function zO(e) {
  if (vn && typeof vn.onCommitFiberRoot == "function")
    try {
      vn.onCommitFiberRoot(Tl, e, void 0, (e.current.flags & 128) === 128);
    } catch {}
}
var Jt = Math.clz32 ? Math.clz32 : HO,
  BO = Math.log,
  UO = Math.LN2;
function HO(e) {
  return (e >>>= 0), e === 0 ? 32 : (31 - ((BO(e) / UO) | 0)) | 0;
}
var Ma = 64,
  Ia = 4194304;
function es(e) {
  switch (e & -e) {
    case 1:
      return 1;
    case 2:
      return 2;
    case 4:
      return 4;
    case 8:
      return 8;
    case 16:
      return 16;
    case 32:
      return 32;
    case 64:
    case 128:
    case 256:
    case 512:
    case 1024:
    case 2048:
    case 4096:
    case 8192:
    case 16384:
    case 32768:
    case 65536:
    case 131072:
    case 262144:
    case 524288:
    case 1048576:
    case 2097152:
      return e & 4194240;
    case 4194304:
    case 8388608:
    case 16777216:
    case 33554432:
    case 67108864:
      return e & 130023424;
    case 134217728:
      return 134217728;
    case 268435456:
      return 268435456;
    case 536870912:
      return 536870912;
    case 1073741824:
      return 1073741824;
    default:
      return e;
  }
}
function ju(e, t) {
  var n = e.pendingLanes;
  if (n === 0) return 0;
  var r = 0,
    i = e.suspendedLanes,
    o = e.pingedLanes,
    s = n & 268435455;
  if (s !== 0) {
    var a = s & ~i;
    a !== 0 ? (r = es(a)) : ((o &= s), o !== 0 && (r = es(o)));
  } else (s = n & ~i), s !== 0 ? (r = es(s)) : o !== 0 && (r = es(o));
  if (r === 0) return 0;
  if (
    t !== 0 &&
    t !== r &&
    !(t & i) &&
    ((i = r & -r), (o = t & -t), i >= o || (i === 16 && (o & 4194240) !== 0))
  )
    return t;
  if ((r & 4 && (r |= n & 16), (t = e.entangledLanes), t !== 0))
    for (e = e.entanglements, t &= r; 0 < t; )
      (n = 31 - Jt(t)), (i = 1 << n), (r |= e[n]), (t &= ~i);
  return r;
}
function GO(e, t) {
  switch (e) {
    case 1:
    case 2:
    case 4:
      return t + 250;
    case 8:
    case 16:
    case 32:
    case 64:
    case 128:
    case 256:
    case 512:
    case 1024:
    case 2048:
    case 4096:
    case 8192:
    case 16384:
    case 32768:
    case 65536:
    case 131072:
    case 262144:
    case 524288:
    case 1048576:
    case 2097152:
      return t + 5e3;
    case 4194304:
    case 8388608:
    case 16777216:
    case 33554432:
    case 67108864:
      return -1;
    case 134217728:
    case 268435456:
    case 536870912:
    case 1073741824:
      return -1;
    default:
      return -1;
  }
}
function WO(e, t) {
  for (
    var n = e.suspendedLanes, r = e.pingedLanes, i = e.expirationTimes, o = e.pendingLanes;
    0 < o;

  ) {
    var s = 31 - Jt(o),
      a = 1 << s,
      u = i[s];
    u === -1 ? (!(a & n) || a & r) && (i[s] = GO(a, t)) : u <= t && (e.expiredLanes |= a),
      (o &= ~a);
  }
}
function Wg(e) {
  return (e = e.pendingLanes & -1073741825), e !== 0 ? e : e & 1073741824 ? 1073741824 : 0;
}
function tR() {
  var e = Ma;
  return (Ma <<= 1), !(Ma & 4194240) && (Ma = 64), e;
}
function Lc(e) {
  for (var t = [], n = 0; 31 > n; n++) t.push(e);
  return t;
}
function sa(e, t, n) {
  (e.pendingLanes |= t),
    t !== 536870912 && ((e.suspendedLanes = 0), (e.pingedLanes = 0)),
    (e = e.eventTimes),
    (t = 31 - Jt(t)),
    (e[t] = n);
}
function KO(e, t) {
  var n = e.pendingLanes & ~t;
  (e.pendingLanes = t),
    (e.suspendedLanes = 0),
    (e.pingedLanes = 0),
    (e.expiredLanes &= t),
    (e.mutableReadLanes &= t),
    (e.entangledLanes &= t),
    (t = e.entanglements);
  var r = e.eventTimes;
  for (e = e.expirationTimes; 0 < n; ) {
    var i = 31 - Jt(n),
      o = 1 << i;
    (t[i] = 0), (r[i] = -1), (e[i] = -1), (n &= ~o);
  }
}
function xy(e, t) {
  var n = (e.entangledLanes |= t);
  for (e = e.entanglements; n; ) {
    var r = 31 - Jt(n),
      i = 1 << r;
    (i & t) | (e[r] & t) && (e[r] |= t), (n &= ~i);
  }
}
var ce = 0;
function nR(e) {
  return (e &= -e), 1 < e ? (4 < e ? (e & 268435455 ? 16 : 536870912) : 4) : 1;
}
var rR,
  _y,
  iR,
  oR,
  sR,
  Kg = !1,
  Da = [],
  wr = null,
  xr = null,
  _r = null,
  Ms = new Map(),
  Is = new Map(),
  hr = [],
  YO =
    "mousedown mouseup touchcancel touchend touchstart auxclick dblclick pointercancel pointerdown pointerup dragend dragstart drop compositionend compositionstart keydown keypress keyup input textInput copy cut paste click change contextmenu reset submit".split(
      " ",
    );
function Bw(e, t) {
  switch (e) {
    case "focusin":
    case "focusout":
      wr = null;
      break;
    case "dragenter":
    case "dragleave":
      xr = null;
      break;
    case "mouseover":
    case "mouseout":
      _r = null;
      break;
    case "pointerover":
    case "pointerout":
      Ms.delete(t.pointerId);
      break;
    case "gotpointercapture":
    case "lostpointercapture":
      Is.delete(t.pointerId);
  }
}
function jo(e, t, n, r, i, o) {
  return e === null || e.nativeEvent !== o
    ? ((e = {
        blockedOn: t,
        domEventName: n,
        eventSystemFlags: r,
        nativeEvent: o,
        targetContainers: [i],
      }),
      t !== null && ((t = ua(t)), t !== null && _y(t)),
      e)
    : ((e.eventSystemFlags |= r),
      (t = e.targetContainers),
      i !== null && t.indexOf(i) === -1 && t.push(i),
      e);
}
function XO(e, t, n, r, i) {
  switch (t) {
    case "focusin":
      return (wr = jo(wr, e, t, n, r, i)), !0;
    case "dragenter":
      return (xr = jo(xr, e, t, n, r, i)), !0;
    case "mouseover":
      return (_r = jo(_r, e, t, n, r, i)), !0;
    case "pointerover":
      var o = i.pointerId;
      return Ms.set(o, jo(Ms.get(o) || null, e, t, n, r, i)), !0;
    case "gotpointercapture":
      return (o = i.pointerId), Is.set(o, jo(Is.get(o) || null, e, t, n, r, i)), !0;
  }
  return !1;
}
function aR(e) {
  var t = Gr(e.target);
  if (t !== null) {
    var n = hi(t);
    if (n !== null) {
      if (((t = n.tag), t === 13)) {
        if (((t = Yk(n)), t !== null)) {
          (e.blockedOn = t),
            sR(e.priority, function () {
              iR(n);
            });
          return;
        }
      } else if (t === 3 && n.stateNode.current.memoizedState.isDehydrated) {
        e.blockedOn = n.tag === 3 ? n.stateNode.containerInfo : null;
        return;
      }
    }
  }
  e.blockedOn = null;
}
function du(e) {
  if (e.blockedOn !== null) return !1;
  for (var t = e.targetContainers; 0 < t.length; ) {
    var n = Yg(e.domEventName, e.eventSystemFlags, t[0], e.nativeEvent);
    if (n === null) {
      n = e.nativeEvent;
      var r = new n.constructor(n.type, n);
      (Bg = r), n.target.dispatchEvent(r), (Bg = null);
    } else return (t = ua(n)), t !== null && _y(t), (e.blockedOn = n), !1;
    t.shift();
  }
  return !0;
}
function Uw(e, t, n) {
  du(e) && n.delete(t);
}
function ZO() {
  (Kg = !1),
    wr !== null && du(wr) && (wr = null),
    xr !== null && du(xr) && (xr = null),
    _r !== null && du(_r) && (_r = null),
    Ms.forEach(Uw),
    Is.forEach(Uw);
}
function Vo(e, t) {
  e.blockedOn === t &&
    ((e.blockedOn = null),
    Kg || ((Kg = !0), Tt.unstable_scheduleCallback(Tt.unstable_NormalPriority, ZO)));
}
function Ds(e) {
  function t(i) {
    return Vo(i, e);
  }
  if (0 < Da.length) {
    Vo(Da[0], e);
    for (var n = 1; n < Da.length; n++) {
      var r = Da[n];
      r.blockedOn === e && (r.blockedOn = null);
    }
  }
  for (
    wr !== null && Vo(wr, e),
      xr !== null && Vo(xr, e),
      _r !== null && Vo(_r, e),
      Ms.forEach(t),
      Is.forEach(t),
      n = 0;
    n < hr.length;
    n++
  )
    (r = hr[n]), r.blockedOn === e && (r.blockedOn = null);
  for (; 0 < hr.length && ((n = hr[0]), n.blockedOn === null); )
    aR(n), n.blockedOn === null && hr.shift();
}
var Yi = Qn.ReactCurrentBatchConfig,
  Vu = !0;
function QO(e, t, n, r) {
  var i = ce,
    o = Yi.transition;
  Yi.transition = null;
  try {
    (ce = 1), by(e, t, n, r);
  } finally {
    (ce = i), (Yi.transition = o);
  }
}
function JO(e, t, n, r) {
  var i = ce,
    o = Yi.transition;
  Yi.transition = null;
  try {
    (ce = 4), by(e, t, n, r);
  } finally {
    (ce = i), (Yi.transition = o);
  }
}
function by(e, t, n, r) {
  if (Vu) {
    var i = Yg(e, t, n, r);
    if (i === null) Gc(e, t, r, qu, n), Bw(e, r);
    else if (XO(i, e, t, n, r)) r.stopPropagation();
    else if ((Bw(e, r), t & 4 && -1 < YO.indexOf(e))) {
      for (; i !== null; ) {
        var o = ua(i);
        if ((o !== null && rR(o), (o = Yg(e, t, n, r)), o === null && Gc(e, t, r, qu, n), o === i))
          break;
        i = o;
      }
      i !== null && r.stopPropagation();
    } else Gc(e, t, r, null, n);
  }
}
var qu = null;
function Yg(e, t, n, r) {
  if (((qu = null), (e = yy(r)), (e = Gr(e)), e !== null))
    if (((t = hi(e)), t === null)) e = null;
    else if (((n = t.tag), n === 13)) {
      if (((e = Yk(t)), e !== null)) return e;
      e = null;
    } else if (n === 3) {
      if (t.stateNode.current.memoizedState.isDehydrated)
        return t.tag === 3 ? t.stateNode.containerInfo : null;
      e = null;
    } else t !== e && (e = null);
  return (qu = e), null;
}
function uR(e) {
  switch (e) {
    case "cancel":
    case "click":
    case "close":
    case "contextmenu":
    case "copy":
    case "cut":
    case "auxclick":
    case "dblclick":
    case "dragend":
    case "dragstart":
    case "drop":
    case "focusin":
    case "focusout":
    case "input":
    case "invalid":
    case "keydown":
    case "keypress":
    case "keyup":
    case "mousedown":
    case "mouseup":
    case "paste":
    case "pause":
    case "play":
    case "pointercancel":
    case "pointerdown":
    case "pointerup":
    case "ratechange":
    case "reset":
    case "resize":
    case "seeked":
    case "submit":
    case "touchcancel":
    case "touchend":
    case "touchstart":
    case "volumechange":
    case "change":
    case "selectionchange":
    case "textInput":
    case "compositionstart":
    case "compositionend":
    case "compositionupdate":
    case "beforeblur":
    case "afterblur":
    case "beforeinput":
    case "blur":
    case "fullscreenchange":
    case "focus":
    case "hashchange":
    case "popstate":
    case "select":
    case "selectstart":
      return 1;
    case "drag":
    case "dragenter":
    case "dragexit":
    case "dragleave":
    case "dragover":
    case "mousemove":
    case "mouseout":
    case "mouseover":
    case "pointermove":
    case "pointerout":
    case "pointerover":
    case "scroll":
    case "toggle":
    case "touchmove":
    case "wheel":
    case "mouseenter":
    case "mouseleave":
    case "pointerenter":
    case "pointerleave":
      return 4;
    case "message":
      switch (qO()) {
        case wy:
          return 1;
        case Jk:
          return 4;
        case Fu:
        case $O:
          return 16;
        case eR:
          return 536870912;
        default:
          return 16;
      }
    default:
      return 16;
  }
}
var gr = null,
  Sy = null,
  hu = null;
function lR() {
  if (hu) return hu;
  var e,
    t = Sy,
    n = t.length,
    r,
    i = "value" in gr ? gr.value : gr.textContent,
    o = i.length;
  for (e = 0; e < n && t[e] === i[e]; e++);
  var s = n - e;
  for (r = 1; r <= s && t[n - r] === i[o - r]; r++);
  return (hu = i.slice(e, 1 < r ? 1 - r : void 0));
}
function pu(e) {
  var t = e.keyCode;
  return (
    "charCode" in e ? ((e = e.charCode), e === 0 && t === 13 && (e = 13)) : (e = t),
    e === 10 && (e = 13),
    32 <= e || e === 13 ? e : 0
  );
}
function Oa() {
  return !0;
}
function Hw() {
  return !1;
}
function At(e) {
  function t(n, r, i, o, s) {
    (this._reactName = n),
      (this._targetInst = i),
      (this.type = r),
      (this.nativeEvent = o),
      (this.target = s),
      (this.currentTarget = null);
    for (var a in e) e.hasOwnProperty(a) && ((n = e[a]), (this[a] = n ? n(o) : o[a]));
    return (
      (this.isDefaultPrevented = (
        o.defaultPrevented != null ? o.defaultPrevented : o.returnValue === !1
      )
        ? Oa
        : Hw),
      (this.isPropagationStopped = Hw),
      this
    );
  }
  return (
    Se(t.prototype, {
      preventDefault: function () {
        this.defaultPrevented = !0;
        var n = this.nativeEvent;
        n &&
          (n.preventDefault
            ? n.preventDefault()
            : typeof n.returnValue != "unknown" && (n.returnValue = !1),
          (this.isDefaultPrevented = Oa));
      },
      stopPropagation: function () {
        var n = this.nativeEvent;
        n &&
          (n.stopPropagation
            ? n.stopPropagation()
            : typeof n.cancelBubble != "unknown" && (n.cancelBubble = !0),
          (this.isPropagationStopped = Oa));
      },
      persist: function () {},
      isPersistent: Oa,
    }),
    t
  );
}
var So = {
    eventPhase: 0,
    bubbles: 0,
    cancelable: 0,
    timeStamp: function (e) {
      return e.timeStamp || Date.now();
    },
    defaultPrevented: 0,
    isTrusted: 0,
  },
  Ey = At(So),
  aa = Se({}, So, { view: 0, detail: 0 }),
  eL = At(aa),
  Fc,
  jc,
  qo,
  kl = Se({}, aa, {
    screenX: 0,
    screenY: 0,
    clientX: 0,
    clientY: 0,
    pageX: 0,
    pageY: 0,
    ctrlKey: 0,
    shiftKey: 0,
    altKey: 0,
    metaKey: 0,
    getModifierState: Cy,
    button: 0,
    buttons: 0,
    relatedTarget: function (e) {
      return e.relatedTarget === void 0
        ? e.fromElement === e.srcElement
          ? e.toElement
          : e.fromElement
        : e.relatedTarget;
    },
    movementX: function (e) {
      return "movementX" in e
        ? e.movementX
        : (e !== qo &&
            (qo && e.type === "mousemove"
              ? ((Fc = e.screenX - qo.screenX), (jc = e.screenY - qo.screenY))
              : (jc = Fc = 0),
            (qo = e)),
          Fc);
    },
    movementY: function (e) {
      return "movementY" in e ? e.movementY : jc;
    },
  }),
  Gw = At(kl),
  tL = Se({}, kl, { dataTransfer: 0 }),
  nL = At(tL),
  rL = Se({}, aa, { relatedTarget: 0 }),
  Vc = At(rL),
  iL = Se({}, So, { animationName: 0, elapsedTime: 0, pseudoElement: 0 }),
  oL = At(iL),
  sL = Se({}, So, {
    clipboardData: function (e) {
      return "clipboardData" in e ? e.clipboardData : window.clipboardData;
    },
  }),
  aL = At(sL),
  uL = Se({}, So, { data: 0 }),
  Ww = At(uL),
  lL = {
    Esc: "Escape",
    Spacebar: " ",
    Left: "ArrowLeft",
    Up: "ArrowUp",
    Right: "ArrowRight",
    Down: "ArrowDown",
    Del: "Delete",
    Win: "OS",
    Menu: "ContextMenu",
    Apps: "ContextMenu",
    Scroll: "ScrollLock",
    MozPrintableKey: "Unidentified",
  },
  cL = {
    8: "Backspace",
    9: "Tab",
    12: "Clear",
    13: "Enter",
    16: "Shift",
    17: "Control",
    18: "Alt",
    19: "Pause",
    20: "CapsLock",
    27: "Escape",
    32: " ",
    33: "PageUp",
    34: "PageDown",
    35: "End",
    36: "Home",
    37: "ArrowLeft",
    38: "ArrowUp",
    39: "ArrowRight",
    40: "ArrowDown",
    45: "Insert",
    46: "Delete",
    112: "F1",
    113: "F2",
    114: "F3",
    115: "F4",
    116: "F5",
    117: "F6",
    118: "F7",
    119: "F8",
    120: "F9",
    121: "F10",
    122: "F11",
    123: "F12",
    144: "NumLock",
    145: "ScrollLock",
    224: "Meta",
  },
  fL = { Alt: "altKey", Control: "ctrlKey", Meta: "metaKey", Shift: "shiftKey" };
function dL(e) {
  var t = this.nativeEvent;
  return t.getModifierState ? t.getModifierState(e) : (e = fL[e]) ? !!t[e] : !1;
}
function Cy() {
  return dL;
}
var hL = Se({}, aa, {
    key: function (e) {
      if (e.key) {
        var t = lL[e.key] || e.key;
        if (t !== "Unidentified") return t;
      }
      return e.type === "keypress"
        ? ((e = pu(e)), e === 13 ? "Enter" : String.fromCharCode(e))
        : e.type === "keydown" || e.type === "keyup"
          ? cL[e.keyCode] || "Unidentified"
          : "";
    },
    code: 0,
    location: 0,
    ctrlKey: 0,
    shiftKey: 0,
    altKey: 0,
    metaKey: 0,
    repeat: 0,
    locale: 0,
    getModifierState: Cy,
    charCode: function (e) {
      return e.type === "keypress" ? pu(e) : 0;
    },
    keyCode: function (e) {
      return e.type === "keydown" || e.type === "keyup" ? e.keyCode : 0;
    },
    which: function (e) {
      return e.type === "keypress"
        ? pu(e)
        : e.type === "keydown" || e.type === "keyup"
          ? e.keyCode
          : 0;
    },
  }),
  pL = At(hL),
  mL = Se({}, kl, {
    pointerId: 0,
    width: 0,
    height: 0,
    pressure: 0,
    tangentialPressure: 0,
    tiltX: 0,
    tiltY: 0,
    twist: 0,
    pointerType: 0,
    isPrimary: 0,
  }),
  Kw = At(mL),
  gL = Se({}, aa, {
    touches: 0,
    targetTouches: 0,
    changedTouches: 0,
    altKey: 0,
    metaKey: 0,
    ctrlKey: 0,
    shiftKey: 0,
    getModifierState: Cy,
  }),
  vL = At(gL),
  yL = Se({}, So, { propertyName: 0, elapsedTime: 0, pseudoElement: 0 }),
  wL = At(yL),
  xL = Se({}, kl, {
    deltaX: function (e) {
      return "deltaX" in e ? e.deltaX : "wheelDeltaX" in e ? -e.wheelDeltaX : 0;
    },
    deltaY: function (e) {
      return "deltaY" in e
        ? e.deltaY
        : "wheelDeltaY" in e
          ? -e.wheelDeltaY
          : "wheelDelta" in e
            ? -e.wheelDelta
            : 0;
    },
    deltaZ: 0,
    deltaMode: 0,
  }),
  _L = At(xL),
  bL = [9, 13, 27, 32],
  Ty = Bn && "CompositionEvent" in window,
  gs = null;
Bn && "documentMode" in document && (gs = document.documentMode);
var SL = Bn && "TextEvent" in window && !gs,
  cR = Bn && (!Ty || (gs && 8 < gs && 11 >= gs)),
  Yw = " ",
  Xw = !1;
function fR(e, t) {
  switch (e) {
    case "keyup":
      return bL.indexOf(t.keyCode) !== -1;
    case "keydown":
      return t.keyCode !== 229;
    case "keypress":
    case "mousedown":
    case "focusout":
      return !0;
    default:
      return !1;
  }
}
function dR(e) {
  return (e = e.detail), typeof e == "object" && "data" in e ? e.data : null;
}
var Ai = !1;
function EL(e, t) {
  switch (e) {
    case "compositionend":
      return dR(t);
    case "keypress":
      return t.which !== 32 ? null : ((Xw = !0), Yw);
    case "textInput":
      return (e = t.data), e === Yw && Xw ? null : e;
    default:
      return null;
  }
}
function CL(e, t) {
  if (Ai)
    return e === "compositionend" || (!Ty && fR(e, t))
      ? ((e = lR()), (hu = Sy = gr = null), (Ai = !1), e)
      : null;
  switch (e) {
    case "paste":
      return null;
    case "keypress":
      if (!(t.ctrlKey || t.altKey || t.metaKey) || (t.ctrlKey && t.altKey)) {
        if (t.char && 1 < t.char.length) return t.char;
        if (t.which) return String.fromCharCode(t.which);
      }
      return null;
    case "compositionend":
      return cR && t.locale !== "ko" ? null : t.data;
    default:
      return null;
  }
}
var TL = {
  color: !0,
  date: !0,
  datetime: !0,
  "datetime-local": !0,
  email: !0,
  month: !0,
  number: !0,
  password: !0,
  range: !0,
  search: !0,
  tel: !0,
  text: !0,
  time: !0,
  url: !0,
  week: !0,
};
function Zw(e) {
  var t = e && e.nodeName && e.nodeName.toLowerCase();
  return t === "input" ? !!TL[e.type] : t === "textarea";
}
function hR(e, t, n, r) {
  Uk(r),
    (t = $u(t, "onChange")),
    0 < t.length &&
      ((n = new Ey("onChange", "change", null, n, r)), e.push({ event: n, listeners: t }));
}
var vs = null,
  Os = null;
function kL(e) {
  ER(e, 0);
}
function Rl(e) {
  var t = Ii(e);
  if (Fk(t)) return e;
}
function RL(e, t) {
  if (e === "change") return t;
}
var pR = !1;
if (Bn) {
  var qc;
  if (Bn) {
    var $c = "oninput" in document;
    if (!$c) {
      var Qw = document.createElement("div");
      Qw.setAttribute("oninput", "return;"), ($c = typeof Qw.oninput == "function");
    }
    qc = $c;
  } else qc = !1;
  pR = qc && (!document.documentMode || 9 < document.documentMode);
}
function Jw() {
  vs && (vs.detachEvent("onpropertychange", mR), (Os = vs = null));
}
function mR(e) {
  if (e.propertyName === "value" && Rl(Os)) {
    var t = [];
    hR(t, Os, e, yy(e)), Kk(kL, t);
  }
}
function PL(e, t, n) {
  e === "focusin"
    ? (Jw(), (vs = t), (Os = n), vs.attachEvent("onpropertychange", mR))
    : e === "focusout" && Jw();
}
function AL(e) {
  if (e === "selectionchange" || e === "keyup" || e === "keydown") return Rl(Os);
}
function NL(e, t) {
  if (e === "click") return Rl(t);
}
function ML(e, t) {
  if (e === "input" || e === "change") return Rl(t);
}
function IL(e, t) {
  return (e === t && (e !== 0 || 1 / e === 1 / t)) || (e !== e && t !== t);
}
var nn = typeof Object.is == "function" ? Object.is : IL;
function Ls(e, t) {
  if (nn(e, t)) return !0;
  if (typeof e != "object" || e === null || typeof t != "object" || t === null) return !1;
  var n = Object.keys(e),
    r = Object.keys(t);
  if (n.length !== r.length) return !1;
  for (r = 0; r < n.length; r++) {
    var i = n[r];
    if (!Ng.call(t, i) || !nn(e[i], t[i])) return !1;
  }
  return !0;
}
function e1(e) {
  for (; e && e.firstChild; ) e = e.firstChild;
  return e;
}
function t1(e, t) {
  var n = e1(e);
  e = 0;
  for (var r; n; ) {
    if (n.nodeType === 3) {
      if (((r = e + n.textContent.length), e <= t && r >= t)) return { node: n, offset: t - e };
      e = r;
    }
    e: {
      for (; n; ) {
        if (n.nextSibling) {
          n = n.nextSibling;
          break e;
        }
        n = n.parentNode;
      }
      n = void 0;
    }
    n = e1(n);
  }
}
function gR(e, t) {
  return e && t
    ? e === t
      ? !0
      : e && e.nodeType === 3
        ? !1
        : t && t.nodeType === 3
          ? gR(e, t.parentNode)
          : "contains" in e
            ? e.contains(t)
            : e.compareDocumentPosition
              ? !!(e.compareDocumentPosition(t) & 16)
              : !1
    : !1;
}
function vR() {
  for (var e = window, t = Du(); t instanceof e.HTMLIFrameElement; ) {
    try {
      var n = typeof t.contentWindow.location.href == "string";
    } catch {
      n = !1;
    }
    if (n) e = t.contentWindow;
    else break;
    t = Du(e.document);
  }
  return t;
}
function ky(e) {
  var t = e && e.nodeName && e.nodeName.toLowerCase();
  return (
    t &&
    ((t === "input" &&
      (e.type === "text" ||
        e.type === "search" ||
        e.type === "tel" ||
        e.type === "url" ||
        e.type === "password")) ||
      t === "textarea" ||
      e.contentEditable === "true")
  );
}
function DL(e) {
  var t = vR(),
    n = e.focusedElem,
    r = e.selectionRange;
  if (t !== n && n && n.ownerDocument && gR(n.ownerDocument.documentElement, n)) {
    if (r !== null && ky(n)) {
      if (((t = r.start), (e = r.end), e === void 0 && (e = t), "selectionStart" in n))
        (n.selectionStart = t), (n.selectionEnd = Math.min(e, n.value.length));
      else if (
        ((e = ((t = n.ownerDocument || document) && t.defaultView) || window), e.getSelection)
      ) {
        e = e.getSelection();
        var i = n.textContent.length,
          o = Math.min(r.start, i);
        (r = r.end === void 0 ? o : Math.min(r.end, i)),
          !e.extend && o > r && ((i = r), (r = o), (o = i)),
          (i = t1(n, o));
        var s = t1(n, r);
        i &&
          s &&
          (e.rangeCount !== 1 ||
            e.anchorNode !== i.node ||
            e.anchorOffset !== i.offset ||
            e.focusNode !== s.node ||
            e.focusOffset !== s.offset) &&
          ((t = t.createRange()),
          t.setStart(i.node, i.offset),
          e.removeAllRanges(),
          o > r
            ? (e.addRange(t), e.extend(s.node, s.offset))
            : (t.setEnd(s.node, s.offset), e.addRange(t)));
      }
    }
    for (t = [], e = n; (e = e.parentNode); )
      e.nodeType === 1 && t.push({ element: e, left: e.scrollLeft, top: e.scrollTop });
    for (typeof n.focus == "function" && n.focus(), n = 0; n < t.length; n++)
      (e = t[n]), (e.element.scrollLeft = e.left), (e.element.scrollTop = e.top);
  }
}
var OL = Bn && "documentMode" in document && 11 >= document.documentMode,
  Ni = null,
  Xg = null,
  ys = null,
  Zg = !1;
function n1(e, t, n) {
  var r = n.window === n ? n.document : n.nodeType === 9 ? n : n.ownerDocument;
  Zg ||
    Ni == null ||
    Ni !== Du(r) ||
    ((r = Ni),
    "selectionStart" in r && ky(r)
      ? (r = { start: r.selectionStart, end: r.selectionEnd })
      : ((r = ((r.ownerDocument && r.ownerDocument.defaultView) || window).getSelection()),
        (r = {
          anchorNode: r.anchorNode,
          anchorOffset: r.anchorOffset,
          focusNode: r.focusNode,
          focusOffset: r.focusOffset,
        })),
    (ys && Ls(ys, r)) ||
      ((ys = r),
      (r = $u(Xg, "onSelect")),
      0 < r.length &&
        ((t = new Ey("onSelect", "select", null, t, n)),
        e.push({ event: t, listeners: r }),
        (t.target = Ni))));
}
function La(e, t) {
  var n = {};
  return (
    (n[e.toLowerCase()] = t.toLowerCase()),
    (n["Webkit" + e] = "webkit" + t),
    (n["Moz" + e] = "moz" + t),
    n
  );
}
var Mi = {
    animationend: La("Animation", "AnimationEnd"),
    animationiteration: La("Animation", "AnimationIteration"),
    animationstart: La("Animation", "AnimationStart"),
    transitionend: La("Transition", "TransitionEnd"),
  },
  zc = {},
  yR = {};
Bn &&
  ((yR = document.createElement("div").style),
  "AnimationEvent" in window ||
    (delete Mi.animationend.animation,
    delete Mi.animationiteration.animation,
    delete Mi.animationstart.animation),
  "TransitionEvent" in window || delete Mi.transitionend.transition);
function Pl(e) {
  if (zc[e]) return zc[e];
  if (!Mi[e]) return e;
  var t = Mi[e],
    n;
  for (n in t) if (t.hasOwnProperty(n) && n in yR) return (zc[e] = t[n]);
  return e;
}
var wR = Pl("animationend"),
  xR = Pl("animationiteration"),
  _R = Pl("animationstart"),
  bR = Pl("transitionend"),
  SR = new Map(),
  r1 =
    "abort auxClick cancel canPlay canPlayThrough click close contextMenu copy cut drag dragEnd dragEnter dragExit dragLeave dragOver dragStart drop durationChange emptied encrypted ended error gotPointerCapture input invalid keyDown keyPress keyUp load loadedData loadedMetadata loadStart lostPointerCapture mouseDown mouseMove mouseOut mouseOver mouseUp paste pause play playing pointerCancel pointerDown pointerMove pointerOut pointerOver pointerUp progress rateChange reset resize seeked seeking stalled submit suspend timeUpdate touchCancel touchEnd touchStart volumeChange scroll toggle touchMove waiting wheel".split(
      " ",
    );
function Ir(e, t) {
  SR.set(e, t), di(t, [e]);
}
for (var Bc = 0; Bc < r1.length; Bc++) {
  var Uc = r1[Bc],
    LL = Uc.toLowerCase(),
    FL = Uc[0].toUpperCase() + Uc.slice(1);
  Ir(LL, "on" + FL);
}
Ir(wR, "onAnimationEnd");
Ir(xR, "onAnimationIteration");
Ir(_R, "onAnimationStart");
Ir("dblclick", "onDoubleClick");
Ir("focusin", "onFocus");
Ir("focusout", "onBlur");
Ir(bR, "onTransitionEnd");
ro("onMouseEnter", ["mouseout", "mouseover"]);
ro("onMouseLeave", ["mouseout", "mouseover"]);
ro("onPointerEnter", ["pointerout", "pointerover"]);
ro("onPointerLeave", ["pointerout", "pointerover"]);
di("onChange", "change click focusin focusout input keydown keyup selectionchange".split(" "));
di(
  "onSelect",
  "focusout contextmenu dragend focusin keydown keyup mousedown mouseup selectionchange".split(" "),
);
di("onBeforeInput", ["compositionend", "keypress", "textInput", "paste"]);
di("onCompositionEnd", "compositionend focusout keydown keypress keyup mousedown".split(" "));
di("onCompositionStart", "compositionstart focusout keydown keypress keyup mousedown".split(" "));
di("onCompositionUpdate", "compositionupdate focusout keydown keypress keyup mousedown".split(" "));
var ts =
    "abort canplay canplaythrough durationchange emptied encrypted ended error loadeddata loadedmetadata loadstart pause play playing progress ratechange resize seeked seeking stalled suspend timeupdate volumechange waiting".split(
      " ",
    ),
  jL = new Set("cancel close invalid load scroll toggle".split(" ").concat(ts));
function i1(e, t, n) {
  var r = e.type || "unknown-event";
  (e.currentTarget = n), LO(r, t, void 0, e), (e.currentTarget = null);
}
function ER(e, t) {
  t = (t & 4) !== 0;
  for (var n = 0; n < e.length; n++) {
    var r = e[n],
      i = r.event;
    r = r.listeners;
    e: {
      var o = void 0;
      if (t)
        for (var s = r.length - 1; 0 <= s; s--) {
          var a = r[s],
            u = a.instance,
            l = a.currentTarget;
          if (((a = a.listener), u !== o && i.isPropagationStopped())) break e;
          i1(i, a, l), (o = u);
        }
      else
        for (s = 0; s < r.length; s++) {
          if (
            ((a = r[s]),
            (u = a.instance),
            (l = a.currentTarget),
            (a = a.listener),
            u !== o && i.isPropagationStopped())
          )
            break e;
          i1(i, a, l), (o = u);
        }
    }
  }
  if (Lu) throw ((e = Gg), (Lu = !1), (Gg = null), e);
}
function me(e, t) {
  var n = t[nv];
  n === void 0 && (n = t[nv] = new Set());
  var r = e + "__bubble";
  n.has(r) || (CR(t, e, 2, !1), n.add(r));
}
function Hc(e, t, n) {
  var r = 0;
  t && (r |= 4), CR(n, e, r, t);
}
var Fa = "_reactListening" + Math.random().toString(36).slice(2);
function Fs(e) {
  if (!e[Fa]) {
    (e[Fa] = !0),
      Mk.forEach(function (n) {
        n !== "selectionchange" && (jL.has(n) || Hc(n, !1, e), Hc(n, !0, e));
      });
    var t = e.nodeType === 9 ? e : e.ownerDocument;
    t === null || t[Fa] || ((t[Fa] = !0), Hc("selectionchange", !1, t));
  }
}
function CR(e, t, n, r) {
  switch (uR(t)) {
    case 1:
      var i = QO;
      break;
    case 4:
      i = JO;
      break;
    default:
      i = by;
  }
  (n = i.bind(null, t, n, e)),
    (i = void 0),
    !Hg || (t !== "touchstart" && t !== "touchmove" && t !== "wheel") || (i = !0),
    r
      ? i !== void 0
        ? e.addEventListener(t, n, { capture: !0, passive: i })
        : e.addEventListener(t, n, !0)
      : i !== void 0
        ? e.addEventListener(t, n, { passive: i })
        : e.addEventListener(t, n, !1);
}
function Gc(e, t, n, r, i) {
  var o = r;
  if (!(t & 1) && !(t & 2) && r !== null)
    e: for (;;) {
      if (r === null) return;
      var s = r.tag;
      if (s === 3 || s === 4) {
        var a = r.stateNode.containerInfo;
        if (a === i || (a.nodeType === 8 && a.parentNode === i)) break;
        if (s === 4)
          for (s = r.return; s !== null; ) {
            var u = s.tag;
            if (
              (u === 3 || u === 4) &&
              ((u = s.stateNode.containerInfo), u === i || (u.nodeType === 8 && u.parentNode === i))
            )
              return;
            s = s.return;
          }
        for (; a !== null; ) {
          if (((s = Gr(a)), s === null)) return;
          if (((u = s.tag), u === 5 || u === 6)) {
            r = o = s;
            continue e;
          }
          a = a.parentNode;
        }
      }
      r = r.return;
    }
  Kk(function () {
    var l = o,
      c = yy(n),
      f = [];
    e: {
      var d = SR.get(e);
      if (d !== void 0) {
        var h = Ey,
          v = e;
        switch (e) {
          case "keypress":
            if (pu(n) === 0) break e;
          case "keydown":
          case "keyup":
            h = pL;
            break;
          case "focusin":
            (v = "focus"), (h = Vc);
            break;
          case "focusout":
            (v = "blur"), (h = Vc);
            break;
          case "beforeblur":
          case "afterblur":
            h = Vc;
            break;
          case "click":
            if (n.button === 2) break e;
          case "auxclick":
          case "dblclick":
          case "mousedown":
          case "mousemove":
          case "mouseup":
          case "mouseout":
          case "mouseover":
          case "contextmenu":
            h = Gw;
            break;
          case "drag":
          case "dragend":
          case "dragenter":
          case "dragexit":
          case "dragleave":
          case "dragover":
          case "dragstart":
          case "drop":
            h = nL;
            break;
          case "touchcancel":
          case "touchend":
          case "touchmove":
          case "touchstart":
            h = vL;
            break;
          case wR:
          case xR:
          case _R:
            h = oL;
            break;
          case bR:
            h = wL;
            break;
          case "scroll":
            h = eL;
            break;
          case "wheel":
            h = _L;
            break;
          case "copy":
          case "cut":
          case "paste":
            h = aL;
            break;
          case "gotpointercapture":
          case "lostpointercapture":
          case "pointercancel":
          case "pointerdown":
          case "pointermove":
          case "pointerout":
          case "pointerover":
          case "pointerup":
            h = Kw;
        }
        var p = (t & 4) !== 0,
          y = !p && e === "scroll",
          m = p ? (d !== null ? d + "Capture" : null) : d;
        p = [];
        for (var g = l, w; g !== null; ) {
          w = g;
          var x = w.stateNode;
          if (
            (w.tag === 5 &&
              x !== null &&
              ((w = x), m !== null && ((x = Ns(g, m)), x != null && p.push(js(g, x, w)))),
            y)
          )
            break;
          g = g.return;
        }
        0 < p.length && ((d = new h(d, v, null, n, c)), f.push({ event: d, listeners: p }));
      }
    }
    if (!(t & 7)) {
      e: {
        if (
          ((d = e === "mouseover" || e === "pointerover"),
          (h = e === "mouseout" || e === "pointerout"),
          d && n !== Bg && (v = n.relatedTarget || n.fromElement) && (Gr(v) || v[Un]))
        )
          break e;
        if (
          (h || d) &&
          ((d =
            c.window === c ? c : (d = c.ownerDocument) ? d.defaultView || d.parentWindow : window),
          h
            ? ((v = n.relatedTarget || n.toElement),
              (h = l),
              (v = v ? Gr(v) : null),
              v !== null && ((y = hi(v)), v !== y || (v.tag !== 5 && v.tag !== 6)) && (v = null))
            : ((h = null), (v = l)),
          h !== v)
        ) {
          if (
            ((p = Gw),
            (x = "onMouseLeave"),
            (m = "onMouseEnter"),
            (g = "mouse"),
            (e === "pointerout" || e === "pointerover") &&
              ((p = Kw), (x = "onPointerLeave"), (m = "onPointerEnter"), (g = "pointer")),
            (y = h == null ? d : Ii(h)),
            (w = v == null ? d : Ii(v)),
            (d = new p(x, g + "leave", h, n, c)),
            (d.target = y),
            (d.relatedTarget = w),
            (x = null),
            Gr(c) === l &&
              ((p = new p(m, g + "enter", v, n, c)),
              (p.target = w),
              (p.relatedTarget = y),
              (x = p)),
            (y = x),
            h && v)
          )
            t: {
              for (p = h, m = v, g = 0, w = p; w; w = xi(w)) g++;
              for (w = 0, x = m; x; x = xi(x)) w++;
              for (; 0 < g - w; ) (p = xi(p)), g--;
              for (; 0 < w - g; ) (m = xi(m)), w--;
              for (; g--; ) {
                if (p === m || (m !== null && p === m.alternate)) break t;
                (p = xi(p)), (m = xi(m));
              }
              p = null;
            }
          else p = null;
          h !== null && o1(f, d, h, p, !1), v !== null && y !== null && o1(f, y, v, p, !0);
        }
      }
      e: {
        if (
          ((d = l ? Ii(l) : window),
          (h = d.nodeName && d.nodeName.toLowerCase()),
          h === "select" || (h === "input" && d.type === "file"))
        )
          var b = RL;
        else if (Zw(d))
          if (pR) b = ML;
          else {
            b = AL;
            var E = PL;
          }
        else
          (h = d.nodeName) &&
            h.toLowerCase() === "input" &&
            (d.type === "checkbox" || d.type === "radio") &&
            (b = NL);
        if (b && (b = b(e, l))) {
          hR(f, b, n, c);
          break e;
        }
        E && E(e, d, l),
          e === "focusout" &&
            (E = d._wrapperState) &&
            E.controlled &&
            d.type === "number" &&
            jg(d, "number", d.value);
      }
      switch (((E = l ? Ii(l) : window), e)) {
        case "focusin":
          (Zw(E) || E.contentEditable === "true") && ((Ni = E), (Xg = l), (ys = null));
          break;
        case "focusout":
          ys = Xg = Ni = null;
          break;
        case "mousedown":
          Zg = !0;
          break;
        case "contextmenu":
        case "mouseup":
        case "dragend":
          (Zg = !1), n1(f, n, c);
          break;
        case "selectionchange":
          if (OL) break;
        case "keydown":
        case "keyup":
          n1(f, n, c);
      }
      var C;
      if (Ty)
        e: {
          switch (e) {
            case "compositionstart":
              var T = "onCompositionStart";
              break e;
            case "compositionend":
              T = "onCompositionEnd";
              break e;
            case "compositionupdate":
              T = "onCompositionUpdate";
              break e;
          }
          T = void 0;
        }
      else
        Ai
          ? fR(e, n) && (T = "onCompositionEnd")
          : e === "keydown" && n.keyCode === 229 && (T = "onCompositionStart");
      T &&
        (cR &&
          n.locale !== "ko" &&
          (Ai || T !== "onCompositionStart"
            ? T === "onCompositionEnd" && Ai && (C = lR())
            : ((gr = c), (Sy = "value" in gr ? gr.value : gr.textContent), (Ai = !0))),
        (E = $u(l, T)),
        0 < E.length &&
          ((T = new Ww(T, e, null, n, c)),
          f.push({ event: T, listeners: E }),
          C ? (T.data = C) : ((C = dR(n)), C !== null && (T.data = C)))),
        (C = SL ? EL(e, n) : CL(e, n)) &&
          ((l = $u(l, "onBeforeInput")),
          0 < l.length &&
            ((c = new Ww("onBeforeInput", "beforeinput", null, n, c)),
            f.push({ event: c, listeners: l }),
            (c.data = C)));
    }
    ER(f, t);
  });
}
function js(e, t, n) {
  return { instance: e, listener: t, currentTarget: n };
}
function $u(e, t) {
  for (var n = t + "Capture", r = []; e !== null; ) {
    var i = e,
      o = i.stateNode;
    i.tag === 5 &&
      o !== null &&
      ((i = o),
      (o = Ns(e, n)),
      o != null && r.unshift(js(e, o, i)),
      (o = Ns(e, t)),
      o != null && r.push(js(e, o, i))),
      (e = e.return);
  }
  return r;
}
function xi(e) {
  if (e === null) return null;
  do e = e.return;
  while (e && e.tag !== 5);
  return e || null;
}
function o1(e, t, n, r, i) {
  for (var o = t._reactName, s = []; n !== null && n !== r; ) {
    var a = n,
      u = a.alternate,
      l = a.stateNode;
    if (u !== null && u === r) break;
    a.tag === 5 &&
      l !== null &&
      ((a = l),
      i
        ? ((u = Ns(n, o)), u != null && s.unshift(js(n, u, a)))
        : i || ((u = Ns(n, o)), u != null && s.push(js(n, u, a)))),
      (n = n.return);
  }
  s.length !== 0 && e.push({ event: t, listeners: s });
}
var VL = /\r\n?/g,
  qL = /\u0000|\uFFFD/g;
function s1(e) {
  return (typeof e == "string" ? e : "" + e)
    .replace(
      VL,
      `
`,
    )
    .replace(qL, "");
}
function ja(e, t, n) {
  if (((t = s1(t)), s1(e) !== t && n)) throw Error(z(425));
}
function zu() {}
var Qg = null,
  Jg = null;
function ev(e, t) {
  return (
    e === "textarea" ||
    e === "noscript" ||
    typeof t.children == "string" ||
    typeof t.children == "number" ||
    (typeof t.dangerouslySetInnerHTML == "object" &&
      t.dangerouslySetInnerHTML !== null &&
      t.dangerouslySetInnerHTML.__html != null)
  );
}
var tv = typeof setTimeout == "function" ? setTimeout : void 0,
  $L = typeof clearTimeout == "function" ? clearTimeout : void 0,
  a1 = typeof Promise == "function" ? Promise : void 0,
  zL =
    typeof queueMicrotask == "function"
      ? queueMicrotask
      : typeof a1 < "u"
        ? function (e) {
            return a1.resolve(null).then(e).catch(BL);
          }
        : tv;
function BL(e) {
  setTimeout(function () {
    throw e;
  });
}
function Wc(e, t) {
  var n = t,
    r = 0;
  do {
    var i = n.nextSibling;
    if ((e.removeChild(n), i && i.nodeType === 8))
      if (((n = i.data), n === "/$")) {
        if (r === 0) {
          e.removeChild(i), Ds(t);
          return;
        }
        r--;
      } else (n !== "$" && n !== "$?" && n !== "$!") || r++;
    n = i;
  } while (n);
  Ds(t);
}
function br(e) {
  for (; e != null; e = e.nextSibling) {
    var t = e.nodeType;
    if (t === 1 || t === 3) break;
    if (t === 8) {
      if (((t = e.data), t === "$" || t === "$!" || t === "$?")) break;
      if (t === "/$") return null;
    }
  }
  return e;
}
function u1(e) {
  e = e.previousSibling;
  for (var t = 0; e; ) {
    if (e.nodeType === 8) {
      var n = e.data;
      if (n === "$" || n === "$!" || n === "$?") {
        if (t === 0) return e;
        t--;
      } else n === "/$" && t++;
    }
    e = e.previousSibling;
  }
  return null;
}
var Eo = Math.random().toString(36).slice(2),
  pn = "__reactFiber$" + Eo,
  Vs = "__reactProps$" + Eo,
  Un = "__reactContainer$" + Eo,
  nv = "__reactEvents$" + Eo,
  UL = "__reactListeners$" + Eo,
  HL = "__reactHandles$" + Eo;
function Gr(e) {
  var t = e[pn];
  if (t) return t;
  for (var n = e.parentNode; n; ) {
    if ((t = n[Un] || n[pn])) {
      if (((n = t.alternate), t.child !== null || (n !== null && n.child !== null)))
        for (e = u1(e); e !== null; ) {
          if ((n = e[pn])) return n;
          e = u1(e);
        }
      return t;
    }
    (e = n), (n = e.parentNode);
  }
  return null;
}
function ua(e) {
  return (
    (e = e[pn] || e[Un]),
    !e || (e.tag !== 5 && e.tag !== 6 && e.tag !== 13 && e.tag !== 3) ? null : e
  );
}
function Ii(e) {
  if (e.tag === 5 || e.tag === 6) return e.stateNode;
  throw Error(z(33));
}
function Al(e) {
  return e[Vs] || null;
}
var rv = [],
  Di = -1;
function Dr(e) {
  return { current: e };
}
function ge(e) {
  0 > Di || ((e.current = rv[Di]), (rv[Di] = null), Di--);
}
function he(e, t) {
  Di++, (rv[Di] = e.current), (e.current = t);
}
var Ar = {},
  rt = Dr(Ar),
  gt = Dr(!1),
  ii = Ar;
function io(e, t) {
  var n = e.type.contextTypes;
  if (!n) return Ar;
  var r = e.stateNode;
  if (r && r.__reactInternalMemoizedUnmaskedChildContext === t)
    return r.__reactInternalMemoizedMaskedChildContext;
  var i = {},
    o;
  for (o in n) i[o] = t[o];
  return (
    r &&
      ((e = e.stateNode),
      (e.__reactInternalMemoizedUnmaskedChildContext = t),
      (e.__reactInternalMemoizedMaskedChildContext = i)),
    i
  );
}
function vt(e) {
  return (e = e.childContextTypes), e != null;
}
function Bu() {
  ge(gt), ge(rt);
}
function l1(e, t, n) {
  if (rt.current !== Ar) throw Error(z(168));
  he(rt, t), he(gt, n);
}
function TR(e, t, n) {
  var r = e.stateNode;
  if (((t = t.childContextTypes), typeof r.getChildContext != "function")) return n;
  r = r.getChildContext();
  for (var i in r) if (!(i in t)) throw Error(z(108, PO(e) || "Unknown", i));
  return Se({}, n, r);
}
function Uu(e) {
  return (
    (e = ((e = e.stateNode) && e.__reactInternalMemoizedMergedChildContext) || Ar),
    (ii = rt.current),
    he(rt, e),
    he(gt, gt.current),
    !0
  );
}
function c1(e, t, n) {
  var r = e.stateNode;
  if (!r) throw Error(z(169));
  n
    ? ((e = TR(e, t, ii)),
      (r.__reactInternalMemoizedMergedChildContext = e),
      ge(gt),
      ge(rt),
      he(rt, e))
    : ge(gt),
    he(gt, n);
}
var Mn = null,
  Nl = !1,
  Kc = !1;
function kR(e) {
  Mn === null ? (Mn = [e]) : Mn.push(e);
}
function GL(e) {
  (Nl = !0), kR(e);
}
function Or() {
  if (!Kc && Mn !== null) {
    Kc = !0;
    var e = 0,
      t = ce;
    try {
      var n = Mn;
      for (ce = 1; e < n.length; e++) {
        var r = n[e];
        do r = r(!0);
        while (r !== null);
      }
      (Mn = null), (Nl = !1);
    } catch (i) {
      throw (Mn !== null && (Mn = Mn.slice(e + 1)), Qk(wy, Or), i);
    } finally {
      (ce = t), (Kc = !1);
    }
  }
  return null;
}
var Oi = [],
  Li = 0,
  Hu = null,
  Gu = 0,
  It = [],
  Dt = 0,
  oi = null,
  Dn = 1,
  On = "";
function $r(e, t) {
  (Oi[Li++] = Gu), (Oi[Li++] = Hu), (Hu = e), (Gu = t);
}
function RR(e, t, n) {
  (It[Dt++] = Dn), (It[Dt++] = On), (It[Dt++] = oi), (oi = e);
  var r = Dn;
  e = On;
  var i = 32 - Jt(r) - 1;
  (r &= ~(1 << i)), (n += 1);
  var o = 32 - Jt(t) + i;
  if (30 < o) {
    var s = i - (i % 5);
    (o = (r & ((1 << s) - 1)).toString(32)),
      (r >>= s),
      (i -= s),
      (Dn = (1 << (32 - Jt(t) + i)) | (n << i) | r),
      (On = o + e);
  } else (Dn = (1 << o) | (n << i) | r), (On = e);
}
function Ry(e) {
  e.return !== null && ($r(e, 1), RR(e, 1, 0));
}
function Py(e) {
  for (; e === Hu; ) (Hu = Oi[--Li]), (Oi[Li] = null), (Gu = Oi[--Li]), (Oi[Li] = null);
  for (; e === oi; )
    (oi = It[--Dt]),
      (It[Dt] = null),
      (On = It[--Dt]),
      (It[Dt] = null),
      (Dn = It[--Dt]),
      (It[Dt] = null);
}
var Et = null,
  St = null,
  ye = !1,
  Zt = null;
function PR(e, t) {
  var n = Lt(5, null, null, 0);
  (n.elementType = "DELETED"),
    (n.stateNode = t),
    (n.return = e),
    (t = e.deletions),
    t === null ? ((e.deletions = [n]), (e.flags |= 16)) : t.push(n);
}
function f1(e, t) {
  switch (e.tag) {
    case 5:
      var n = e.type;
      return (
        (t = t.nodeType !== 1 || n.toLowerCase() !== t.nodeName.toLowerCase() ? null : t),
        t !== null ? ((e.stateNode = t), (Et = e), (St = br(t.firstChild)), !0) : !1
      );
    case 6:
      return (
        (t = e.pendingProps === "" || t.nodeType !== 3 ? null : t),
        t !== null ? ((e.stateNode = t), (Et = e), (St = null), !0) : !1
      );
    case 13:
      return (
        (t = t.nodeType !== 8 ? null : t),
        t !== null
          ? ((n = oi !== null ? { id: Dn, overflow: On } : null),
            (e.memoizedState = { dehydrated: t, treeContext: n, retryLane: 1073741824 }),
            (n = Lt(18, null, null, 0)),
            (n.stateNode = t),
            (n.return = e),
            (e.child = n),
            (Et = e),
            (St = null),
            !0)
          : !1
      );
    default:
      return !1;
  }
}
function iv(e) {
  return (e.mode & 1) !== 0 && (e.flags & 128) === 0;
}
function ov(e) {
  if (ye) {
    var t = St;
    if (t) {
      var n = t;
      if (!f1(e, t)) {
        if (iv(e)) throw Error(z(418));
        t = br(n.nextSibling);
        var r = Et;
        t && f1(e, t) ? PR(r, n) : ((e.flags = (e.flags & -4097) | 2), (ye = !1), (Et = e));
      }
    } else {
      if (iv(e)) throw Error(z(418));
      (e.flags = (e.flags & -4097) | 2), (ye = !1), (Et = e);
    }
  }
}
function d1(e) {
  for (e = e.return; e !== null && e.tag !== 5 && e.tag !== 3 && e.tag !== 13; ) e = e.return;
  Et = e;
}
function Va(e) {
  if (e !== Et) return !1;
  if (!ye) return d1(e), (ye = !0), !1;
  var t;
  if (
    ((t = e.tag !== 3) &&
      !(t = e.tag !== 5) &&
      ((t = e.type), (t = t !== "head" && t !== "body" && !ev(e.type, e.memoizedProps))),
    t && (t = St))
  ) {
    if (iv(e)) throw (AR(), Error(z(418)));
    for (; t; ) PR(e, t), (t = br(t.nextSibling));
  }
  if ((d1(e), e.tag === 13)) {
    if (((e = e.memoizedState), (e = e !== null ? e.dehydrated : null), !e)) throw Error(z(317));
    e: {
      for (e = e.nextSibling, t = 0; e; ) {
        if (e.nodeType === 8) {
          var n = e.data;
          if (n === "/$") {
            if (t === 0) {
              St = br(e.nextSibling);
              break e;
            }
            t--;
          } else (n !== "$" && n !== "$!" && n !== "$?") || t++;
        }
        e = e.nextSibling;
      }
      St = null;
    }
  } else St = Et ? br(e.stateNode.nextSibling) : null;
  return !0;
}
function AR() {
  for (var e = St; e; ) e = br(e.nextSibling);
}
function oo() {
  (St = Et = null), (ye = !1);
}
function Ay(e) {
  Zt === null ? (Zt = [e]) : Zt.push(e);
}
var WL = Qn.ReactCurrentBatchConfig;
function $o(e, t, n) {
  if (((e = n.ref), e !== null && typeof e != "function" && typeof e != "object")) {
    if (n._owner) {
      if (((n = n._owner), n)) {
        if (n.tag !== 1) throw Error(z(309));
        var r = n.stateNode;
      }
      if (!r) throw Error(z(147, e));
      var i = r,
        o = "" + e;
      return t !== null && t.ref !== null && typeof t.ref == "function" && t.ref._stringRef === o
        ? t.ref
        : ((t = function (s) {
            var a = i.refs;
            s === null ? delete a[o] : (a[o] = s);
          }),
          (t._stringRef = o),
          t);
    }
    if (typeof e != "string") throw Error(z(284));
    if (!n._owner) throw Error(z(290, e));
  }
  return e;
}
function qa(e, t) {
  throw (
    ((e = Object.prototype.toString.call(t)),
    Error(
      z(31, e === "[object Object]" ? "object with keys {" + Object.keys(t).join(", ") + "}" : e),
    ))
  );
}
function h1(e) {
  var t = e._init;
  return t(e._payload);
}
function NR(e) {
  function t(m, g) {
    if (e) {
      var w = m.deletions;
      w === null ? ((m.deletions = [g]), (m.flags |= 16)) : w.push(g);
    }
  }
  function n(m, g) {
    if (!e) return null;
    for (; g !== null; ) t(m, g), (g = g.sibling);
    return null;
  }
  function r(m, g) {
    for (m = new Map(); g !== null; )
      g.key !== null ? m.set(g.key, g) : m.set(g.index, g), (g = g.sibling);
    return m;
  }
  function i(m, g) {
    return (m = Tr(m, g)), (m.index = 0), (m.sibling = null), m;
  }
  function o(m, g, w) {
    return (
      (m.index = w),
      e
        ? ((w = m.alternate),
          w !== null ? ((w = w.index), w < g ? ((m.flags |= 2), g) : w) : ((m.flags |= 2), g))
        : ((m.flags |= 1048576), g)
    );
  }
  function s(m) {
    return e && m.alternate === null && (m.flags |= 2), m;
  }
  function a(m, g, w, x) {
    return g === null || g.tag !== 6
      ? ((g = tf(w, m.mode, x)), (g.return = m), g)
      : ((g = i(g, w)), (g.return = m), g);
  }
  function u(m, g, w, x) {
    var b = w.type;
    return b === Pi
      ? c(m, g, w.props.children, x, w.key)
      : g !== null &&
          (g.elementType === b ||
            (typeof b == "object" && b !== null && b.$$typeof === lr && h1(b) === g.type))
        ? ((x = i(g, w.props)), (x.ref = $o(m, g, w)), (x.return = m), x)
        : ((x = _u(w.type, w.key, w.props, null, m.mode, x)),
          (x.ref = $o(m, g, w)),
          (x.return = m),
          x);
  }
  function l(m, g, w, x) {
    return g === null ||
      g.tag !== 4 ||
      g.stateNode.containerInfo !== w.containerInfo ||
      g.stateNode.implementation !== w.implementation
      ? ((g = nf(w, m.mode, x)), (g.return = m), g)
      : ((g = i(g, w.children || [])), (g.return = m), g);
  }
  function c(m, g, w, x, b) {
    return g === null || g.tag !== 7
      ? ((g = ei(w, m.mode, x, b)), (g.return = m), g)
      : ((g = i(g, w)), (g.return = m), g);
  }
  function f(m, g, w) {
    if ((typeof g == "string" && g !== "") || typeof g == "number")
      return (g = tf("" + g, m.mode, w)), (g.return = m), g;
    if (typeof g == "object" && g !== null) {
      switch (g.$$typeof) {
        case Pa:
          return (
            (w = _u(g.type, g.key, g.props, null, m.mode, w)),
            (w.ref = $o(m, null, g)),
            (w.return = m),
            w
          );
        case Ri:
          return (g = nf(g, m.mode, w)), (g.return = m), g;
        case lr:
          var x = g._init;
          return f(m, x(g._payload), w);
      }
      if (Jo(g) || Lo(g)) return (g = ei(g, m.mode, w, null)), (g.return = m), g;
      qa(m, g);
    }
    return null;
  }
  function d(m, g, w, x) {
    var b = g !== null ? g.key : null;
    if ((typeof w == "string" && w !== "") || typeof w == "number")
      return b !== null ? null : a(m, g, "" + w, x);
    if (typeof w == "object" && w !== null) {
      switch (w.$$typeof) {
        case Pa:
          return w.key === b ? u(m, g, w, x) : null;
        case Ri:
          return w.key === b ? l(m, g, w, x) : null;
        case lr:
          return (b = w._init), d(m, g, b(w._payload), x);
      }
      if (Jo(w) || Lo(w)) return b !== null ? null : c(m, g, w, x, null);
      qa(m, w);
    }
    return null;
  }
  function h(m, g, w, x, b) {
    if ((typeof x == "string" && x !== "") || typeof x == "number")
      return (m = m.get(w) || null), a(g, m, "" + x, b);
    if (typeof x == "object" && x !== null) {
      switch (x.$$typeof) {
        case Pa:
          return (m = m.get(x.key === null ? w : x.key) || null), u(g, m, x, b);
        case Ri:
          return (m = m.get(x.key === null ? w : x.key) || null), l(g, m, x, b);
        case lr:
          var E = x._init;
          return h(m, g, w, E(x._payload), b);
      }
      if (Jo(x) || Lo(x)) return (m = m.get(w) || null), c(g, m, x, b, null);
      qa(g, x);
    }
    return null;
  }
  function v(m, g, w, x) {
    for (var b = null, E = null, C = g, T = (g = 0), P = null; C !== null && T < w.length; T++) {
      C.index > T ? ((P = C), (C = null)) : (P = C.sibling);
      var M = d(m, C, w[T], x);
      if (M === null) {
        C === null && (C = P);
        break;
      }
      e && C && M.alternate === null && t(m, C),
        (g = o(M, g, T)),
        E === null ? (b = M) : (E.sibling = M),
        (E = M),
        (C = P);
    }
    if (T === w.length) return n(m, C), ye && $r(m, T), b;
    if (C === null) {
      for (; T < w.length; T++)
        (C = f(m, w[T], x)),
          C !== null && ((g = o(C, g, T)), E === null ? (b = C) : (E.sibling = C), (E = C));
      return ye && $r(m, T), b;
    }
    for (C = r(m, C); T < w.length; T++)
      (P = h(C, m, T, w[T], x)),
        P !== null &&
          (e && P.alternate !== null && C.delete(P.key === null ? T : P.key),
          (g = o(P, g, T)),
          E === null ? (b = P) : (E.sibling = P),
          (E = P));
    return (
      e &&
        C.forEach(function (I) {
          return t(m, I);
        }),
      ye && $r(m, T),
      b
    );
  }
  function p(m, g, w, x) {
    var b = Lo(w);
    if (typeof b != "function") throw Error(z(150));
    if (((w = b.call(w)), w == null)) throw Error(z(151));
    for (
      var E = (b = null), C = g, T = (g = 0), P = null, M = w.next();
      C !== null && !M.done;
      T++, M = w.next()
    ) {
      C.index > T ? ((P = C), (C = null)) : (P = C.sibling);
      var I = d(m, C, M.value, x);
      if (I === null) {
        C === null && (C = P);
        break;
      }
      e && C && I.alternate === null && t(m, C),
        (g = o(I, g, T)),
        E === null ? (b = I) : (E.sibling = I),
        (E = I),
        (C = P);
    }
    if (M.done) return n(m, C), ye && $r(m, T), b;
    if (C === null) {
      for (; !M.done; T++, M = w.next())
        (M = f(m, M.value, x)),
          M !== null && ((g = o(M, g, T)), E === null ? (b = M) : (E.sibling = M), (E = M));
      return ye && $r(m, T), b;
    }
    for (C = r(m, C); !M.done; T++, M = w.next())
      (M = h(C, m, T, M.value, x)),
        M !== null &&
          (e && M.alternate !== null && C.delete(M.key === null ? T : M.key),
          (g = o(M, g, T)),
          E === null ? (b = M) : (E.sibling = M),
          (E = M));
    return (
      e &&
        C.forEach(function (j) {
          return t(m, j);
        }),
      ye && $r(m, T),
      b
    );
  }
  function y(m, g, w, x) {
    if (
      (typeof w == "object" &&
        w !== null &&
        w.type === Pi &&
        w.key === null &&
        (w = w.props.children),
      typeof w == "object" && w !== null)
    ) {
      switch (w.$$typeof) {
        case Pa:
          e: {
            for (var b = w.key, E = g; E !== null; ) {
              if (E.key === b) {
                if (((b = w.type), b === Pi)) {
                  if (E.tag === 7) {
                    n(m, E.sibling), (g = i(E, w.props.children)), (g.return = m), (m = g);
                    break e;
                  }
                } else if (
                  E.elementType === b ||
                  (typeof b == "object" && b !== null && b.$$typeof === lr && h1(b) === E.type)
                ) {
                  n(m, E.sibling),
                    (g = i(E, w.props)),
                    (g.ref = $o(m, E, w)),
                    (g.return = m),
                    (m = g);
                  break e;
                }
                n(m, E);
                break;
              } else t(m, E);
              E = E.sibling;
            }
            w.type === Pi
              ? ((g = ei(w.props.children, m.mode, x, w.key)), (g.return = m), (m = g))
              : ((x = _u(w.type, w.key, w.props, null, m.mode, x)),
                (x.ref = $o(m, g, w)),
                (x.return = m),
                (m = x));
          }
          return s(m);
        case Ri:
          e: {
            for (E = w.key; g !== null; ) {
              if (g.key === E)
                if (
                  g.tag === 4 &&
                  g.stateNode.containerInfo === w.containerInfo &&
                  g.stateNode.implementation === w.implementation
                ) {
                  n(m, g.sibling), (g = i(g, w.children || [])), (g.return = m), (m = g);
                  break e;
                } else {
                  n(m, g);
                  break;
                }
              else t(m, g);
              g = g.sibling;
            }
            (g = nf(w, m.mode, x)), (g.return = m), (m = g);
          }
          return s(m);
        case lr:
          return (E = w._init), y(m, g, E(w._payload), x);
      }
      if (Jo(w)) return v(m, g, w, x);
      if (Lo(w)) return p(m, g, w, x);
      qa(m, w);
    }
    return (typeof w == "string" && w !== "") || typeof w == "number"
      ? ((w = "" + w),
        g !== null && g.tag === 6
          ? (n(m, g.sibling), (g = i(g, w)), (g.return = m), (m = g))
          : (n(m, g), (g = tf(w, m.mode, x)), (g.return = m), (m = g)),
        s(m))
      : n(m, g);
  }
  return y;
}
var so = NR(!0),
  MR = NR(!1),
  Wu = Dr(null),
  Ku = null,
  Fi = null,
  Ny = null;
function My() {
  Ny = Fi = Ku = null;
}
function Iy(e) {
  var t = Wu.current;
  ge(Wu), (e._currentValue = t);
}
function sv(e, t, n) {
  for (; e !== null; ) {
    var r = e.alternate;
    if (
      ((e.childLanes & t) !== t
        ? ((e.childLanes |= t), r !== null && (r.childLanes |= t))
        : r !== null && (r.childLanes & t) !== t && (r.childLanes |= t),
      e === n)
    )
      break;
    e = e.return;
  }
}
function Xi(e, t) {
  (Ku = e),
    (Ny = Fi = null),
    (e = e.dependencies),
    e !== null && e.firstContext !== null && (e.lanes & t && (pt = !0), (e.firstContext = null));
}
function Vt(e) {
  var t = e._currentValue;
  if (Ny !== e)
    if (((e = { context: e, memoizedValue: t, next: null }), Fi === null)) {
      if (Ku === null) throw Error(z(308));
      (Fi = e), (Ku.dependencies = { lanes: 0, firstContext: e });
    } else Fi = Fi.next = e;
  return t;
}
var Wr = null;
function Dy(e) {
  Wr === null ? (Wr = [e]) : Wr.push(e);
}
function IR(e, t, n, r) {
  var i = t.interleaved;
  return (
    i === null ? ((n.next = n), Dy(t)) : ((n.next = i.next), (i.next = n)),
    (t.interleaved = n),
    Hn(e, r)
  );
}
function Hn(e, t) {
  e.lanes |= t;
  var n = e.alternate;
  for (n !== null && (n.lanes |= t), n = e, e = e.return; e !== null; )
    (e.childLanes |= t),
      (n = e.alternate),
      n !== null && (n.childLanes |= t),
      (n = e),
      (e = e.return);
  return n.tag === 3 ? n.stateNode : null;
}
var cr = !1;
function Oy(e) {
  e.updateQueue = {
    baseState: e.memoizedState,
    firstBaseUpdate: null,
    lastBaseUpdate: null,
    shared: { pending: null, interleaved: null, lanes: 0 },
    effects: null,
  };
}
function DR(e, t) {
  (e = e.updateQueue),
    t.updateQueue === e &&
      (t.updateQueue = {
        baseState: e.baseState,
        firstBaseUpdate: e.firstBaseUpdate,
        lastBaseUpdate: e.lastBaseUpdate,
        shared: e.shared,
        effects: e.effects,
      });
}
function Vn(e, t) {
  return { eventTime: e, lane: t, tag: 0, payload: null, callback: null, next: null };
}
function Sr(e, t, n) {
  var r = e.updateQueue;
  if (r === null) return null;
  if (((r = r.shared), ae & 2)) {
    var i = r.pending;
    return i === null ? (t.next = t) : ((t.next = i.next), (i.next = t)), (r.pending = t), Hn(e, n);
  }
  return (
    (i = r.interleaved),
    i === null ? ((t.next = t), Dy(r)) : ((t.next = i.next), (i.next = t)),
    (r.interleaved = t),
    Hn(e, n)
  );
}
function mu(e, t, n) {
  if (((t = t.updateQueue), t !== null && ((t = t.shared), (n & 4194240) !== 0))) {
    var r = t.lanes;
    (r &= e.pendingLanes), (n |= r), (t.lanes = n), xy(e, n);
  }
}
function p1(e, t) {
  var n = e.updateQueue,
    r = e.alternate;
  if (r !== null && ((r = r.updateQueue), n === r)) {
    var i = null,
      o = null;
    if (((n = n.firstBaseUpdate), n !== null)) {
      do {
        var s = {
          eventTime: n.eventTime,
          lane: n.lane,
          tag: n.tag,
          payload: n.payload,
          callback: n.callback,
          next: null,
        };
        o === null ? (i = o = s) : (o = o.next = s), (n = n.next);
      } while (n !== null);
      o === null ? (i = o = t) : (o = o.next = t);
    } else i = o = t;
    (n = {
      baseState: r.baseState,
      firstBaseUpdate: i,
      lastBaseUpdate: o,
      shared: r.shared,
      effects: r.effects,
    }),
      (e.updateQueue = n);
    return;
  }
  (e = n.lastBaseUpdate),
    e === null ? (n.firstBaseUpdate = t) : (e.next = t),
    (n.lastBaseUpdate = t);
}
function Yu(e, t, n, r) {
  var i = e.updateQueue;
  cr = !1;
  var o = i.firstBaseUpdate,
    s = i.lastBaseUpdate,
    a = i.shared.pending;
  if (a !== null) {
    i.shared.pending = null;
    var u = a,
      l = u.next;
    (u.next = null), s === null ? (o = l) : (s.next = l), (s = u);
    var c = e.alternate;
    c !== null &&
      ((c = c.updateQueue),
      (a = c.lastBaseUpdate),
      a !== s && (a === null ? (c.firstBaseUpdate = l) : (a.next = l), (c.lastBaseUpdate = u)));
  }
  if (o !== null) {
    var f = i.baseState;
    (s = 0), (c = l = u = null), (a = o);
    do {
      var d = a.lane,
        h = a.eventTime;
      if ((r & d) === d) {
        c !== null &&
          (c = c.next =
            {
              eventTime: h,
              lane: 0,
              tag: a.tag,
              payload: a.payload,
              callback: a.callback,
              next: null,
            });
        e: {
          var v = e,
            p = a;
          switch (((d = t), (h = n), p.tag)) {
            case 1:
              if (((v = p.payload), typeof v == "function")) {
                f = v.call(h, f, d);
                break e;
              }
              f = v;
              break e;
            case 3:
              v.flags = (v.flags & -65537) | 128;
            case 0:
              if (((v = p.payload), (d = typeof v == "function" ? v.call(h, f, d) : v), d == null))
                break e;
              f = Se({}, f, d);
              break e;
            case 2:
              cr = !0;
          }
        }
        a.callback !== null &&
          a.lane !== 0 &&
          ((e.flags |= 64), (d = i.effects), d === null ? (i.effects = [a]) : d.push(a));
      } else
        (h = {
          eventTime: h,
          lane: d,
          tag: a.tag,
          payload: a.payload,
          callback: a.callback,
          next: null,
        }),
          c === null ? ((l = c = h), (u = f)) : (c = c.next = h),
          (s |= d);
      if (((a = a.next), a === null)) {
        if (((a = i.shared.pending), a === null)) break;
        (d = a), (a = d.next), (d.next = null), (i.lastBaseUpdate = d), (i.shared.pending = null);
      }
    } while (!0);
    if (
      (c === null && (u = f),
      (i.baseState = u),
      (i.firstBaseUpdate = l),
      (i.lastBaseUpdate = c),
      (t = i.shared.interleaved),
      t !== null)
    ) {
      i = t;
      do (s |= i.lane), (i = i.next);
      while (i !== t);
    } else o === null && (i.shared.lanes = 0);
    (ai |= s), (e.lanes = s), (e.memoizedState = f);
  }
}
function m1(e, t, n) {
  if (((e = t.effects), (t.effects = null), e !== null))
    for (t = 0; t < e.length; t++) {
      var r = e[t],
        i = r.callback;
      if (i !== null) {
        if (((r.callback = null), (r = n), typeof i != "function")) throw Error(z(191, i));
        i.call(r);
      }
    }
}
var la = {},
  yn = Dr(la),
  qs = Dr(la),
  $s = Dr(la);
function Kr(e) {
  if (e === la) throw Error(z(174));
  return e;
}
function Ly(e, t) {
  switch ((he($s, t), he(qs, e), he(yn, la), (e = t.nodeType), e)) {
    case 9:
    case 11:
      t = (t = t.documentElement) ? t.namespaceURI : qg(null, "");
      break;
    default:
      (e = e === 8 ? t.parentNode : t),
        (t = e.namespaceURI || null),
        (e = e.tagName),
        (t = qg(t, e));
  }
  ge(yn), he(yn, t);
}
function ao() {
  ge(yn), ge(qs), ge($s);
}
function OR(e) {
  Kr($s.current);
  var t = Kr(yn.current),
    n = qg(t, e.type);
  t !== n && (he(qs, e), he(yn, n));
}
function Fy(e) {
  qs.current === e && (ge(yn), ge(qs));
}
var xe = Dr(0);
function Xu(e) {
  for (var t = e; t !== null; ) {
    if (t.tag === 13) {
      var n = t.memoizedState;
      if (n !== null && ((n = n.dehydrated), n === null || n.data === "$?" || n.data === "$!"))
        return t;
    } else if (t.tag === 19 && t.memoizedProps.revealOrder !== void 0) {
      if (t.flags & 128) return t;
    } else if (t.child !== null) {
      (t.child.return = t), (t = t.child);
      continue;
    }
    if (t === e) break;
    for (; t.sibling === null; ) {
      if (t.return === null || t.return === e) return null;
      t = t.return;
    }
    (t.sibling.return = t.return), (t = t.sibling);
  }
  return null;
}
var Yc = [];
function jy() {
  for (var e = 0; e < Yc.length; e++) Yc[e]._workInProgressVersionPrimary = null;
  Yc.length = 0;
}
var gu = Qn.ReactCurrentDispatcher,
  Xc = Qn.ReactCurrentBatchConfig,
  si = 0,
  be = null,
  Oe = null,
  ze = null,
  Zu = !1,
  ws = !1,
  zs = 0,
  KL = 0;
function Je() {
  throw Error(z(321));
}
function Vy(e, t) {
  if (t === null) return !1;
  for (var n = 0; n < t.length && n < e.length; n++) if (!nn(e[n], t[n])) return !1;
  return !0;
}
function qy(e, t, n, r, i, o) {
  if (
    ((si = o),
    (be = t),
    (t.memoizedState = null),
    (t.updateQueue = null),
    (t.lanes = 0),
    (gu.current = e === null || e.memoizedState === null ? QL : JL),
    (e = n(r, i)),
    ws)
  ) {
    o = 0;
    do {
      if (((ws = !1), (zs = 0), 25 <= o)) throw Error(z(301));
      (o += 1), (ze = Oe = null), (t.updateQueue = null), (gu.current = eF), (e = n(r, i));
    } while (ws);
  }
  if (
    ((gu.current = Qu),
    (t = Oe !== null && Oe.next !== null),
    (si = 0),
    (ze = Oe = be = null),
    (Zu = !1),
    t)
  )
    throw Error(z(300));
  return e;
}
function $y() {
  var e = zs !== 0;
  return (zs = 0), e;
}
function dn() {
  var e = { memoizedState: null, baseState: null, baseQueue: null, queue: null, next: null };
  return ze === null ? (be.memoizedState = ze = e) : (ze = ze.next = e), ze;
}
function qt() {
  if (Oe === null) {
    var e = be.alternate;
    e = e !== null ? e.memoizedState : null;
  } else e = Oe.next;
  var t = ze === null ? be.memoizedState : ze.next;
  if (t !== null) (ze = t), (Oe = e);
  else {
    if (e === null) throw Error(z(310));
    (Oe = e),
      (e = {
        memoizedState: Oe.memoizedState,
        baseState: Oe.baseState,
        baseQueue: Oe.baseQueue,
        queue: Oe.queue,
        next: null,
      }),
      ze === null ? (be.memoizedState = ze = e) : (ze = ze.next = e);
  }
  return ze;
}
function Bs(e, t) {
  return typeof t == "function" ? t(e) : t;
}
function Zc(e) {
  var t = qt(),
    n = t.queue;
  if (n === null) throw Error(z(311));
  n.lastRenderedReducer = e;
  var r = Oe,
    i = r.baseQueue,
    o = n.pending;
  if (o !== null) {
    if (i !== null) {
      var s = i.next;
      (i.next = o.next), (o.next = s);
    }
    (r.baseQueue = i = o), (n.pending = null);
  }
  if (i !== null) {
    (o = i.next), (r = r.baseState);
    var a = (s = null),
      u = null,
      l = o;
    do {
      var c = l.lane;
      if ((si & c) === c)
        u !== null &&
          (u = u.next =
            {
              lane: 0,
              action: l.action,
              hasEagerState: l.hasEagerState,
              eagerState: l.eagerState,
              next: null,
            }),
          (r = l.hasEagerState ? l.eagerState : e(r, l.action));
      else {
        var f = {
          lane: c,
          action: l.action,
          hasEagerState: l.hasEagerState,
          eagerState: l.eagerState,
          next: null,
        };
        u === null ? ((a = u = f), (s = r)) : (u = u.next = f), (be.lanes |= c), (ai |= c);
      }
      l = l.next;
    } while (l !== null && l !== o);
    u === null ? (s = r) : (u.next = a),
      nn(r, t.memoizedState) || (pt = !0),
      (t.memoizedState = r),
      (t.baseState = s),
      (t.baseQueue = u),
      (n.lastRenderedState = r);
  }
  if (((e = n.interleaved), e !== null)) {
    i = e;
    do (o = i.lane), (be.lanes |= o), (ai |= o), (i = i.next);
    while (i !== e);
  } else i === null && (n.lanes = 0);
  return [t.memoizedState, n.dispatch];
}
function Qc(e) {
  var t = qt(),
    n = t.queue;
  if (n === null) throw Error(z(311));
  n.lastRenderedReducer = e;
  var r = n.dispatch,
    i = n.pending,
    o = t.memoizedState;
  if (i !== null) {
    n.pending = null;
    var s = (i = i.next);
    do (o = e(o, s.action)), (s = s.next);
    while (s !== i);
    nn(o, t.memoizedState) || (pt = !0),
      (t.memoizedState = o),
      t.baseQueue === null && (t.baseState = o),
      (n.lastRenderedState = o);
  }
  return [o, r];
}
function LR() {}
function FR(e, t) {
  var n = be,
    r = qt(),
    i = t(),
    o = !nn(r.memoizedState, i);
  if (
    (o && ((r.memoizedState = i), (pt = !0)),
    (r = r.queue),
    zy(qR.bind(null, n, r, e), [e]),
    r.getSnapshot !== t || o || (ze !== null && ze.memoizedState.tag & 1))
  ) {
    if (((n.flags |= 2048), Us(9, VR.bind(null, n, r, i, t), void 0, null), Ue === null))
      throw Error(z(349));
    si & 30 || jR(n, t, i);
  }
  return i;
}
function jR(e, t, n) {
  (e.flags |= 16384),
    (e = { getSnapshot: t, value: n }),
    (t = be.updateQueue),
    t === null
      ? ((t = { lastEffect: null, stores: null }), (be.updateQueue = t), (t.stores = [e]))
      : ((n = t.stores), n === null ? (t.stores = [e]) : n.push(e));
}
function VR(e, t, n, r) {
  (t.value = n), (t.getSnapshot = r), $R(t) && zR(e);
}
function qR(e, t, n) {
  return n(function () {
    $R(t) && zR(e);
  });
}
function $R(e) {
  var t = e.getSnapshot;
  e = e.value;
  try {
    var n = t();
    return !nn(e, n);
  } catch {
    return !0;
  }
}
function zR(e) {
  var t = Hn(e, 1);
  t !== null && en(t, e, 1, -1);
}
function g1(e) {
  var t = dn();
  return (
    typeof e == "function" && (e = e()),
    (t.memoizedState = t.baseState = e),
    (e = {
      pending: null,
      interleaved: null,
      lanes: 0,
      dispatch: null,
      lastRenderedReducer: Bs,
      lastRenderedState: e,
    }),
    (t.queue = e),
    (e = e.dispatch = ZL.bind(null, be, e)),
    [t.memoizedState, e]
  );
}
function Us(e, t, n, r) {
  return (
    (e = { tag: e, create: t, destroy: n, deps: r, next: null }),
    (t = be.updateQueue),
    t === null
      ? ((t = { lastEffect: null, stores: null }),
        (be.updateQueue = t),
        (t.lastEffect = e.next = e))
      : ((n = t.lastEffect),
        n === null
          ? (t.lastEffect = e.next = e)
          : ((r = n.next), (n.next = e), (e.next = r), (t.lastEffect = e))),
    e
  );
}
function BR() {
  return qt().memoizedState;
}
function vu(e, t, n, r) {
  var i = dn();
  (be.flags |= e), (i.memoizedState = Us(1 | t, n, void 0, r === void 0 ? null : r));
}
function Ml(e, t, n, r) {
  var i = qt();
  r = r === void 0 ? null : r;
  var o = void 0;
  if (Oe !== null) {
    var s = Oe.memoizedState;
    if (((o = s.destroy), r !== null && Vy(r, s.deps))) {
      i.memoizedState = Us(t, n, o, r);
      return;
    }
  }
  (be.flags |= e), (i.memoizedState = Us(1 | t, n, o, r));
}
function v1(e, t) {
  return vu(8390656, 8, e, t);
}
function zy(e, t) {
  return Ml(2048, 8, e, t);
}
function UR(e, t) {
  return Ml(4, 2, e, t);
}
function HR(e, t) {
  return Ml(4, 4, e, t);
}
function GR(e, t) {
  if (typeof t == "function")
    return (
      (e = e()),
      t(e),
      function () {
        t(null);
      }
    );
  if (t != null)
    return (
      (e = e()),
      (t.current = e),
      function () {
        t.current = null;
      }
    );
}
function WR(e, t, n) {
  return (n = n != null ? n.concat([e]) : null), Ml(4, 4, GR.bind(null, t, e), n);
}
function By() {}
function KR(e, t) {
  var n = qt();
  t = t === void 0 ? null : t;
  var r = n.memoizedState;
  return r !== null && t !== null && Vy(t, r[1]) ? r[0] : ((n.memoizedState = [e, t]), e);
}
function YR(e, t) {
  var n = qt();
  t = t === void 0 ? null : t;
  var r = n.memoizedState;
  return r !== null && t !== null && Vy(t, r[1])
    ? r[0]
    : ((e = e()), (n.memoizedState = [e, t]), e);
}
function XR(e, t, n) {
  return si & 21
    ? (nn(n, t) || ((n = tR()), (be.lanes |= n), (ai |= n), (e.baseState = !0)), t)
    : (e.baseState && ((e.baseState = !1), (pt = !0)), (e.memoizedState = n));
}
function YL(e, t) {
  var n = ce;
  (ce = n !== 0 && 4 > n ? n : 4), e(!0);
  var r = Xc.transition;
  Xc.transition = {};
  try {
    e(!1), t();
  } finally {
    (ce = n), (Xc.transition = r);
  }
}
function ZR() {
  return qt().memoizedState;
}
function XL(e, t, n) {
  var r = Cr(e);
  if (((n = { lane: r, action: n, hasEagerState: !1, eagerState: null, next: null }), QR(e)))
    JR(t, n);
  else if (((n = IR(e, t, n, r)), n !== null)) {
    var i = at();
    en(n, e, r, i), eP(n, t, r);
  }
}
function ZL(e, t, n) {
  var r = Cr(e),
    i = { lane: r, action: n, hasEagerState: !1, eagerState: null, next: null };
  if (QR(e)) JR(t, i);
  else {
    var o = e.alternate;
    if (e.lanes === 0 && (o === null || o.lanes === 0) && ((o = t.lastRenderedReducer), o !== null))
      try {
        var s = t.lastRenderedState,
          a = o(s, n);
        if (((i.hasEagerState = !0), (i.eagerState = a), nn(a, s))) {
          var u = t.interleaved;
          u === null ? ((i.next = i), Dy(t)) : ((i.next = u.next), (u.next = i)),
            (t.interleaved = i);
          return;
        }
      } catch {
      } finally {
      }
    (n = IR(e, t, i, r)), n !== null && ((i = at()), en(n, e, r, i), eP(n, t, r));
  }
}
function QR(e) {
  var t = e.alternate;
  return e === be || (t !== null && t === be);
}
function JR(e, t) {
  ws = Zu = !0;
  var n = e.pending;
  n === null ? (t.next = t) : ((t.next = n.next), (n.next = t)), (e.pending = t);
}
function eP(e, t, n) {
  if (n & 4194240) {
    var r = t.lanes;
    (r &= e.pendingLanes), (n |= r), (t.lanes = n), xy(e, n);
  }
}
var Qu = {
    readContext: Vt,
    useCallback: Je,
    useContext: Je,
    useEffect: Je,
    useImperativeHandle: Je,
    useInsertionEffect: Je,
    useLayoutEffect: Je,
    useMemo: Je,
    useReducer: Je,
    useRef: Je,
    useState: Je,
    useDebugValue: Je,
    useDeferredValue: Je,
    useTransition: Je,
    useMutableSource: Je,
    useSyncExternalStore: Je,
    useId: Je,
    unstable_isNewReconciler: !1,
  },
  QL = {
    readContext: Vt,
    useCallback: function (e, t) {
      return (dn().memoizedState = [e, t === void 0 ? null : t]), e;
    },
    useContext: Vt,
    useEffect: v1,
    useImperativeHandle: function (e, t, n) {
      return (n = n != null ? n.concat([e]) : null), vu(4194308, 4, GR.bind(null, t, e), n);
    },
    useLayoutEffect: function (e, t) {
      return vu(4194308, 4, e, t);
    },
    useInsertionEffect: function (e, t) {
      return vu(4, 2, e, t);
    },
    useMemo: function (e, t) {
      var n = dn();
      return (t = t === void 0 ? null : t), (e = e()), (n.memoizedState = [e, t]), e;
    },
    useReducer: function (e, t, n) {
      var r = dn();
      return (
        (t = n !== void 0 ? n(t) : t),
        (r.memoizedState = r.baseState = t),
        (e = {
          pending: null,
          interleaved: null,
          lanes: 0,
          dispatch: null,
          lastRenderedReducer: e,
          lastRenderedState: t,
        }),
        (r.queue = e),
        (e = e.dispatch = XL.bind(null, be, e)),
        [r.memoizedState, e]
      );
    },
    useRef: function (e) {
      var t = dn();
      return (e = { current: e }), (t.memoizedState = e);
    },
    useState: g1,
    useDebugValue: By,
    useDeferredValue: function (e) {
      return (dn().memoizedState = e);
    },
    useTransition: function () {
      var e = g1(!1),
        t = e[0];
      return (e = YL.bind(null, e[1])), (dn().memoizedState = e), [t, e];
    },
    useMutableSource: function () {},
    useSyncExternalStore: function (e, t, n) {
      var r = be,
        i = dn();
      if (ye) {
        if (n === void 0) throw Error(z(407));
        n = n();
      } else {
        if (((n = t()), Ue === null)) throw Error(z(349));
        si & 30 || jR(r, t, n);
      }
      i.memoizedState = n;
      var o = { value: n, getSnapshot: t };
      return (
        (i.queue = o),
        v1(qR.bind(null, r, o, e), [e]),
        (r.flags |= 2048),
        Us(9, VR.bind(null, r, o, n, t), void 0, null),
        n
      );
    },
    useId: function () {
      var e = dn(),
        t = Ue.identifierPrefix;
      if (ye) {
        var n = On,
          r = Dn;
        (n = (r & ~(1 << (32 - Jt(r) - 1))).toString(32) + n),
          (t = ":" + t + "R" + n),
          (n = zs++),
          0 < n && (t += "H" + n.toString(32)),
          (t += ":");
      } else (n = KL++), (t = ":" + t + "r" + n.toString(32) + ":");
      return (e.memoizedState = t);
    },
    unstable_isNewReconciler: !1,
  },
  JL = {
    readContext: Vt,
    useCallback: KR,
    useContext: Vt,
    useEffect: zy,
    useImperativeHandle: WR,
    useInsertionEffect: UR,
    useLayoutEffect: HR,
    useMemo: YR,
    useReducer: Zc,
    useRef: BR,
    useState: function () {
      return Zc(Bs);
    },
    useDebugValue: By,
    useDeferredValue: function (e) {
      var t = qt();
      return XR(t, Oe.memoizedState, e);
    },
    useTransition: function () {
      var e = Zc(Bs)[0],
        t = qt().memoizedState;
      return [e, t];
    },
    useMutableSource: LR,
    useSyncExternalStore: FR,
    useId: ZR,
    unstable_isNewReconciler: !1,
  },
  eF = {
    readContext: Vt,
    useCallback: KR,
    useContext: Vt,
    useEffect: zy,
    useImperativeHandle: WR,
    useInsertionEffect: UR,
    useLayoutEffect: HR,
    useMemo: YR,
    useReducer: Qc,
    useRef: BR,
    useState: function () {
      return Qc(Bs);
    },
    useDebugValue: By,
    useDeferredValue: function (e) {
      var t = qt();
      return Oe === null ? (t.memoizedState = e) : XR(t, Oe.memoizedState, e);
    },
    useTransition: function () {
      var e = Qc(Bs)[0],
        t = qt().memoizedState;
      return [e, t];
    },
    useMutableSource: LR,
    useSyncExternalStore: FR,
    useId: ZR,
    unstable_isNewReconciler: !1,
  };
function Kt(e, t) {
  if (e && e.defaultProps) {
    (t = Se({}, t)), (e = e.defaultProps);
    for (var n in e) t[n] === void 0 && (t[n] = e[n]);
    return t;
  }
  return t;
}
function av(e, t, n, r) {
  (t = e.memoizedState),
    (n = n(r, t)),
    (n = n == null ? t : Se({}, t, n)),
    (e.memoizedState = n),
    e.lanes === 0 && (e.updateQueue.baseState = n);
}
var Il = {
  isMounted: function (e) {
    return (e = e._reactInternals) ? hi(e) === e : !1;
  },
  enqueueSetState: function (e, t, n) {
    e = e._reactInternals;
    var r = at(),
      i = Cr(e),
      o = Vn(r, i);
    (o.payload = t),
      n != null && (o.callback = n),
      (t = Sr(e, o, i)),
      t !== null && (en(t, e, i, r), mu(t, e, i));
  },
  enqueueReplaceState: function (e, t, n) {
    e = e._reactInternals;
    var r = at(),
      i = Cr(e),
      o = Vn(r, i);
    (o.tag = 1),
      (o.payload = t),
      n != null && (o.callback = n),
      (t = Sr(e, o, i)),
      t !== null && (en(t, e, i, r), mu(t, e, i));
  },
  enqueueForceUpdate: function (e, t) {
    e = e._reactInternals;
    var n = at(),
      r = Cr(e),
      i = Vn(n, r);
    (i.tag = 2),
      t != null && (i.callback = t),
      (t = Sr(e, i, r)),
      t !== null && (en(t, e, r, n), mu(t, e, r));
  },
};
function y1(e, t, n, r, i, o, s) {
  return (
    (e = e.stateNode),
    typeof e.shouldComponentUpdate == "function"
      ? e.shouldComponentUpdate(r, o, s)
      : t.prototype && t.prototype.isPureReactComponent
        ? !Ls(n, r) || !Ls(i, o)
        : !0
  );
}
function tP(e, t, n) {
  var r = !1,
    i = Ar,
    o = t.contextType;
  return (
    typeof o == "object" && o !== null
      ? (o = Vt(o))
      : ((i = vt(t) ? ii : rt.current),
        (r = t.contextTypes),
        (o = (r = r != null) ? io(e, i) : Ar)),
    (t = new t(n, o)),
    (e.memoizedState = t.state !== null && t.state !== void 0 ? t.state : null),
    (t.updater = Il),
    (e.stateNode = t),
    (t._reactInternals = e),
    r &&
      ((e = e.stateNode),
      (e.__reactInternalMemoizedUnmaskedChildContext = i),
      (e.__reactInternalMemoizedMaskedChildContext = o)),
    t
  );
}
function w1(e, t, n, r) {
  (e = t.state),
    typeof t.componentWillReceiveProps == "function" && t.componentWillReceiveProps(n, r),
    typeof t.UNSAFE_componentWillReceiveProps == "function" &&
      t.UNSAFE_componentWillReceiveProps(n, r),
    t.state !== e && Il.enqueueReplaceState(t, t.state, null);
}
function uv(e, t, n, r) {
  var i = e.stateNode;
  (i.props = n), (i.state = e.memoizedState), (i.refs = {}), Oy(e);
  var o = t.contextType;
  typeof o == "object" && o !== null
    ? (i.context = Vt(o))
    : ((o = vt(t) ? ii : rt.current), (i.context = io(e, o))),
    (i.state = e.memoizedState),
    (o = t.getDerivedStateFromProps),
    typeof o == "function" && (av(e, t, o, n), (i.state = e.memoizedState)),
    typeof t.getDerivedStateFromProps == "function" ||
      typeof i.getSnapshotBeforeUpdate == "function" ||
      (typeof i.UNSAFE_componentWillMount != "function" &&
        typeof i.componentWillMount != "function") ||
      ((t = i.state),
      typeof i.componentWillMount == "function" && i.componentWillMount(),
      typeof i.UNSAFE_componentWillMount == "function" && i.UNSAFE_componentWillMount(),
      t !== i.state && Il.enqueueReplaceState(i, i.state, null),
      Yu(e, n, i, r),
      (i.state = e.memoizedState)),
    typeof i.componentDidMount == "function" && (e.flags |= 4194308);
}
function uo(e, t) {
  try {
    var n = "",
      r = t;
    do (n += RO(r)), (r = r.return);
    while (r);
    var i = n;
  } catch (o) {
    i =
      `
Error generating stack: ` +
      o.message +
      `
` +
      o.stack;
  }
  return { value: e, source: t, stack: i, digest: null };
}
function Jc(e, t, n) {
  return { value: e, source: null, stack: n ?? null, digest: t ?? null };
}
function lv(e, t) {
  try {
    console.error(t.value);
  } catch (n) {
    setTimeout(function () {
      throw n;
    });
  }
}
var tF = typeof WeakMap == "function" ? WeakMap : Map;
function nP(e, t, n) {
  (n = Vn(-1, n)), (n.tag = 3), (n.payload = { element: null });
  var r = t.value;
  return (
    (n.callback = function () {
      el || ((el = !0), (wv = r)), lv(e, t);
    }),
    n
  );
}
function rP(e, t, n) {
  (n = Vn(-1, n)), (n.tag = 3);
  var r = e.type.getDerivedStateFromError;
  if (typeof r == "function") {
    var i = t.value;
    (n.payload = function () {
      return r(i);
    }),
      (n.callback = function () {
        lv(e, t);
      });
  }
  var o = e.stateNode;
  return (
    o !== null &&
      typeof o.componentDidCatch == "function" &&
      (n.callback = function () {
        lv(e, t), typeof r != "function" && (Er === null ? (Er = new Set([this])) : Er.add(this));
        var s = t.stack;
        this.componentDidCatch(t.value, { componentStack: s !== null ? s : "" });
      }),
    n
  );
}
function x1(e, t, n) {
  var r = e.pingCache;
  if (r === null) {
    r = e.pingCache = new tF();
    var i = new Set();
    r.set(t, i);
  } else (i = r.get(t)), i === void 0 && ((i = new Set()), r.set(t, i));
  i.has(n) || (i.add(n), (e = mF.bind(null, e, t, n)), t.then(e, e));
}
function _1(e) {
  do {
    var t;
    if (
      ((t = e.tag === 13) && ((t = e.memoizedState), (t = t !== null ? t.dehydrated !== null : !0)),
      t)
    )
      return e;
    e = e.return;
  } while (e !== null);
  return null;
}
function b1(e, t, n, r, i) {
  return e.mode & 1
    ? ((e.flags |= 65536), (e.lanes = i), e)
    : (e === t
        ? (e.flags |= 65536)
        : ((e.flags |= 128),
          (n.flags |= 131072),
          (n.flags &= -52805),
          n.tag === 1 &&
            (n.alternate === null ? (n.tag = 17) : ((t = Vn(-1, 1)), (t.tag = 2), Sr(n, t, 1))),
          (n.lanes |= 1)),
      e);
}
var nF = Qn.ReactCurrentOwner,
  pt = !1;
function st(e, t, n, r) {
  t.child = e === null ? MR(t, null, n, r) : so(t, e.child, n, r);
}
function S1(e, t, n, r, i) {
  n = n.render;
  var o = t.ref;
  return (
    Xi(t, i),
    (r = qy(e, t, n, r, o, i)),
    (n = $y()),
    e !== null && !pt
      ? ((t.updateQueue = e.updateQueue), (t.flags &= -2053), (e.lanes &= ~i), Gn(e, t, i))
      : (ye && n && Ry(t), (t.flags |= 1), st(e, t, r, i), t.child)
  );
}
function E1(e, t, n, r, i) {
  if (e === null) {
    var o = n.type;
    return typeof o == "function" &&
      !Zy(o) &&
      o.defaultProps === void 0 &&
      n.compare === null &&
      n.defaultProps === void 0
      ? ((t.tag = 15), (t.type = o), iP(e, t, o, r, i))
      : ((e = _u(n.type, null, r, t, t.mode, i)), (e.ref = t.ref), (e.return = t), (t.child = e));
  }
  if (((o = e.child), !(e.lanes & i))) {
    var s = o.memoizedProps;
    if (((n = n.compare), (n = n !== null ? n : Ls), n(s, r) && e.ref === t.ref))
      return Gn(e, t, i);
  }
  return (t.flags |= 1), (e = Tr(o, r)), (e.ref = t.ref), (e.return = t), (t.child = e);
}
function iP(e, t, n, r, i) {
  if (e !== null) {
    var o = e.memoizedProps;
    if (Ls(o, r) && e.ref === t.ref)
      if (((pt = !1), (t.pendingProps = r = o), (e.lanes & i) !== 0)) e.flags & 131072 && (pt = !0);
      else return (t.lanes = e.lanes), Gn(e, t, i);
  }
  return cv(e, t, n, r, i);
}
function oP(e, t, n) {
  var r = t.pendingProps,
    i = r.children,
    o = e !== null ? e.memoizedState : null;
  if (r.mode === "hidden")
    if (!(t.mode & 1))
      (t.memoizedState = { baseLanes: 0, cachePool: null, transitions: null }),
        he(Vi, _t),
        (_t |= n);
    else {
      if (!(n & 1073741824))
        return (
          (e = o !== null ? o.baseLanes | n : n),
          (t.lanes = t.childLanes = 1073741824),
          (t.memoizedState = { baseLanes: e, cachePool: null, transitions: null }),
          (t.updateQueue = null),
          he(Vi, _t),
          (_t |= e),
          null
        );
      (t.memoizedState = { baseLanes: 0, cachePool: null, transitions: null }),
        (r = o !== null ? o.baseLanes : n),
        he(Vi, _t),
        (_t |= r);
    }
  else
    o !== null ? ((r = o.baseLanes | n), (t.memoizedState = null)) : (r = n), he(Vi, _t), (_t |= r);
  return st(e, t, i, n), t.child;
}
function sP(e, t) {
  var n = t.ref;
  ((e === null && n !== null) || (e !== null && e.ref !== n)) &&
    ((t.flags |= 512), (t.flags |= 2097152));
}
function cv(e, t, n, r, i) {
  var o = vt(n) ? ii : rt.current;
  return (
    (o = io(t, o)),
    Xi(t, i),
    (n = qy(e, t, n, r, o, i)),
    (r = $y()),
    e !== null && !pt
      ? ((t.updateQueue = e.updateQueue), (t.flags &= -2053), (e.lanes &= ~i), Gn(e, t, i))
      : (ye && r && Ry(t), (t.flags |= 1), st(e, t, n, i), t.child)
  );
}
function C1(e, t, n, r, i) {
  if (vt(n)) {
    var o = !0;
    Uu(t);
  } else o = !1;
  if ((Xi(t, i), t.stateNode === null)) yu(e, t), tP(t, n, r), uv(t, n, r, i), (r = !0);
  else if (e === null) {
    var s = t.stateNode,
      a = t.memoizedProps;
    s.props = a;
    var u = s.context,
      l = n.contextType;
    typeof l == "object" && l !== null
      ? (l = Vt(l))
      : ((l = vt(n) ? ii : rt.current), (l = io(t, l)));
    var c = n.getDerivedStateFromProps,
      f = typeof c == "function" || typeof s.getSnapshotBeforeUpdate == "function";
    f ||
      (typeof s.UNSAFE_componentWillReceiveProps != "function" &&
        typeof s.componentWillReceiveProps != "function") ||
      ((a !== r || u !== l) && w1(t, s, r, l)),
      (cr = !1);
    var d = t.memoizedState;
    (s.state = d),
      Yu(t, r, s, i),
      (u = t.memoizedState),
      a !== r || d !== u || gt.current || cr
        ? (typeof c == "function" && (av(t, n, c, r), (u = t.memoizedState)),
          (a = cr || y1(t, n, a, r, d, u, l))
            ? (f ||
                (typeof s.UNSAFE_componentWillMount != "function" &&
                  typeof s.componentWillMount != "function") ||
                (typeof s.componentWillMount == "function" && s.componentWillMount(),
                typeof s.UNSAFE_componentWillMount == "function" && s.UNSAFE_componentWillMount()),
              typeof s.componentDidMount == "function" && (t.flags |= 4194308))
            : (typeof s.componentDidMount == "function" && (t.flags |= 4194308),
              (t.memoizedProps = r),
              (t.memoizedState = u)),
          (s.props = r),
          (s.state = u),
          (s.context = l),
          (r = a))
        : (typeof s.componentDidMount == "function" && (t.flags |= 4194308), (r = !1));
  } else {
    (s = t.stateNode),
      DR(e, t),
      (a = t.memoizedProps),
      (l = t.type === t.elementType ? a : Kt(t.type, a)),
      (s.props = l),
      (f = t.pendingProps),
      (d = s.context),
      (u = n.contextType),
      typeof u == "object" && u !== null
        ? (u = Vt(u))
        : ((u = vt(n) ? ii : rt.current), (u = io(t, u)));
    var h = n.getDerivedStateFromProps;
    (c = typeof h == "function" || typeof s.getSnapshotBeforeUpdate == "function") ||
      (typeof s.UNSAFE_componentWillReceiveProps != "function" &&
        typeof s.componentWillReceiveProps != "function") ||
      ((a !== f || d !== u) && w1(t, s, r, u)),
      (cr = !1),
      (d = t.memoizedState),
      (s.state = d),
      Yu(t, r, s, i);
    var v = t.memoizedState;
    a !== f || d !== v || gt.current || cr
      ? (typeof h == "function" && (av(t, n, h, r), (v = t.memoizedState)),
        (l = cr || y1(t, n, l, r, d, v, u) || !1)
          ? (c ||
              (typeof s.UNSAFE_componentWillUpdate != "function" &&
                typeof s.componentWillUpdate != "function") ||
              (typeof s.componentWillUpdate == "function" && s.componentWillUpdate(r, v, u),
              typeof s.UNSAFE_componentWillUpdate == "function" &&
                s.UNSAFE_componentWillUpdate(r, v, u)),
            typeof s.componentDidUpdate == "function" && (t.flags |= 4),
            typeof s.getSnapshotBeforeUpdate == "function" && (t.flags |= 1024))
          : (typeof s.componentDidUpdate != "function" ||
              (a === e.memoizedProps && d === e.memoizedState) ||
              (t.flags |= 4),
            typeof s.getSnapshotBeforeUpdate != "function" ||
              (a === e.memoizedProps && d === e.memoizedState) ||
              (t.flags |= 1024),
            (t.memoizedProps = r),
            (t.memoizedState = v)),
        (s.props = r),
        (s.state = v),
        (s.context = u),
        (r = l))
      : (typeof s.componentDidUpdate != "function" ||
          (a === e.memoizedProps && d === e.memoizedState) ||
          (t.flags |= 4),
        typeof s.getSnapshotBeforeUpdate != "function" ||
          (a === e.memoizedProps && d === e.memoizedState) ||
          (t.flags |= 1024),
        (r = !1));
  }
  return fv(e, t, n, r, o, i);
}
function fv(e, t, n, r, i, o) {
  sP(e, t);
  var s = (t.flags & 128) !== 0;
  if (!r && !s) return i && c1(t, n, !1), Gn(e, t, o);
  (r = t.stateNode), (nF.current = t);
  var a = s && typeof n.getDerivedStateFromError != "function" ? null : r.render();
  return (
    (t.flags |= 1),
    e !== null && s
      ? ((t.child = so(t, e.child, null, o)), (t.child = so(t, null, a, o)))
      : st(e, t, a, o),
    (t.memoizedState = r.state),
    i && c1(t, n, !0),
    t.child
  );
}
function aP(e) {
  var t = e.stateNode;
  t.pendingContext
    ? l1(e, t.pendingContext, t.pendingContext !== t.context)
    : t.context && l1(e, t.context, !1),
    Ly(e, t.containerInfo);
}
function T1(e, t, n, r, i) {
  return oo(), Ay(i), (t.flags |= 256), st(e, t, n, r), t.child;
}
var dv = { dehydrated: null, treeContext: null, retryLane: 0 };
function hv(e) {
  return { baseLanes: e, cachePool: null, transitions: null };
}
function uP(e, t, n) {
  var r = t.pendingProps,
    i = xe.current,
    o = !1,
    s = (t.flags & 128) !== 0,
    a;
  if (
    ((a = s) || (a = e !== null && e.memoizedState === null ? !1 : (i & 2) !== 0),
    a ? ((o = !0), (t.flags &= -129)) : (e === null || e.memoizedState !== null) && (i |= 1),
    he(xe, i & 1),
    e === null)
  )
    return (
      ov(t),
      (e = t.memoizedState),
      e !== null && ((e = e.dehydrated), e !== null)
        ? (t.mode & 1 ? (e.data === "$!" ? (t.lanes = 8) : (t.lanes = 1073741824)) : (t.lanes = 1),
          null)
        : ((s = r.children),
          (e = r.fallback),
          o
            ? ((r = t.mode),
              (o = t.child),
              (s = { mode: "hidden", children: s }),
              !(r & 1) && o !== null
                ? ((o.childLanes = 0), (o.pendingProps = s))
                : (o = Ll(s, r, 0, null)),
              (e = ei(e, r, n, null)),
              (o.return = t),
              (e.return = t),
              (o.sibling = e),
              (t.child = o),
              (t.child.memoizedState = hv(n)),
              (t.memoizedState = dv),
              e)
            : Uy(t, s))
    );
  if (((i = e.memoizedState), i !== null && ((a = i.dehydrated), a !== null)))
    return rF(e, t, s, r, a, i, n);
  if (o) {
    (o = r.fallback), (s = t.mode), (i = e.child), (a = i.sibling);
    var u = { mode: "hidden", children: r.children };
    return (
      !(s & 1) && t.child !== i
        ? ((r = t.child), (r.childLanes = 0), (r.pendingProps = u), (t.deletions = null))
        : ((r = Tr(i, u)), (r.subtreeFlags = i.subtreeFlags & 14680064)),
      a !== null ? (o = Tr(a, o)) : ((o = ei(o, s, n, null)), (o.flags |= 2)),
      (o.return = t),
      (r.return = t),
      (r.sibling = o),
      (t.child = r),
      (r = o),
      (o = t.child),
      (s = e.child.memoizedState),
      (s =
        s === null
          ? hv(n)
          : { baseLanes: s.baseLanes | n, cachePool: null, transitions: s.transitions }),
      (o.memoizedState = s),
      (o.childLanes = e.childLanes & ~n),
      (t.memoizedState = dv),
      r
    );
  }
  return (
    (o = e.child),
    (e = o.sibling),
    (r = Tr(o, { mode: "visible", children: r.children })),
    !(t.mode & 1) && (r.lanes = n),
    (r.return = t),
    (r.sibling = null),
    e !== null &&
      ((n = t.deletions), n === null ? ((t.deletions = [e]), (t.flags |= 16)) : n.push(e)),
    (t.child = r),
    (t.memoizedState = null),
    r
  );
}
function Uy(e, t) {
  return (t = Ll({ mode: "visible", children: t }, e.mode, 0, null)), (t.return = e), (e.child = t);
}
function $a(e, t, n, r) {
  return (
    r !== null && Ay(r),
    so(t, e.child, null, n),
    (e = Uy(t, t.pendingProps.children)),
    (e.flags |= 2),
    (t.memoizedState = null),
    e
  );
}
function rF(e, t, n, r, i, o, s) {
  if (n)
    return t.flags & 256
      ? ((t.flags &= -257), (r = Jc(Error(z(422)))), $a(e, t, s, r))
      : t.memoizedState !== null
        ? ((t.child = e.child), (t.flags |= 128), null)
        : ((o = r.fallback),
          (i = t.mode),
          (r = Ll({ mode: "visible", children: r.children }, i, 0, null)),
          (o = ei(o, i, s, null)),
          (o.flags |= 2),
          (r.return = t),
          (o.return = t),
          (r.sibling = o),
          (t.child = r),
          t.mode & 1 && so(t, e.child, null, s),
          (t.child.memoizedState = hv(s)),
          (t.memoizedState = dv),
          o);
  if (!(t.mode & 1)) return $a(e, t, s, null);
  if (i.data === "$!") {
    if (((r = i.nextSibling && i.nextSibling.dataset), r)) var a = r.dgst;
    return (r = a), (o = Error(z(419))), (r = Jc(o, r, void 0)), $a(e, t, s, r);
  }
  if (((a = (s & e.childLanes) !== 0), pt || a)) {
    if (((r = Ue), r !== null)) {
      switch (s & -s) {
        case 4:
          i = 2;
          break;
        case 16:
          i = 8;
          break;
        case 64:
        case 128:
        case 256:
        case 512:
        case 1024:
        case 2048:
        case 4096:
        case 8192:
        case 16384:
        case 32768:
        case 65536:
        case 131072:
        case 262144:
        case 524288:
        case 1048576:
        case 2097152:
        case 4194304:
        case 8388608:
        case 16777216:
        case 33554432:
        case 67108864:
          i = 32;
          break;
        case 536870912:
          i = 268435456;
          break;
        default:
          i = 0;
      }
      (i = i & (r.suspendedLanes | s) ? 0 : i),
        i !== 0 && i !== o.retryLane && ((o.retryLane = i), Hn(e, i), en(r, e, i, -1));
    }
    return Xy(), (r = Jc(Error(z(421)))), $a(e, t, s, r);
  }
  return i.data === "$?"
    ? ((t.flags |= 128), (t.child = e.child), (t = gF.bind(null, e)), (i._reactRetry = t), null)
    : ((e = o.treeContext),
      (St = br(i.nextSibling)),
      (Et = t),
      (ye = !0),
      (Zt = null),
      e !== null &&
        ((It[Dt++] = Dn),
        (It[Dt++] = On),
        (It[Dt++] = oi),
        (Dn = e.id),
        (On = e.overflow),
        (oi = t)),
      (t = Uy(t, r.children)),
      (t.flags |= 4096),
      t);
}
function k1(e, t, n) {
  e.lanes |= t;
  var r = e.alternate;
  r !== null && (r.lanes |= t), sv(e.return, t, n);
}
function ef(e, t, n, r, i) {
  var o = e.memoizedState;
  o === null
    ? (e.memoizedState = {
        isBackwards: t,
        rendering: null,
        renderingStartTime: 0,
        last: r,
        tail: n,
        tailMode: i,
      })
    : ((o.isBackwards = t),
      (o.rendering = null),
      (o.renderingStartTime = 0),
      (o.last = r),
      (o.tail = n),
      (o.tailMode = i));
}
function lP(e, t, n) {
  var r = t.pendingProps,
    i = r.revealOrder,
    o = r.tail;
  if ((st(e, t, r.children, n), (r = xe.current), r & 2)) (r = (r & 1) | 2), (t.flags |= 128);
  else {
    if (e !== null && e.flags & 128)
      e: for (e = t.child; e !== null; ) {
        if (e.tag === 13) e.memoizedState !== null && k1(e, n, t);
        else if (e.tag === 19) k1(e, n, t);
        else if (e.child !== null) {
          (e.child.return = e), (e = e.child);
          continue;
        }
        if (e === t) break e;
        for (; e.sibling === null; ) {
          if (e.return === null || e.return === t) break e;
          e = e.return;
        }
        (e.sibling.return = e.return), (e = e.sibling);
      }
    r &= 1;
  }
  if ((he(xe, r), !(t.mode & 1))) t.memoizedState = null;
  else
    switch (i) {
      case "forwards":
        for (n = t.child, i = null; n !== null; )
          (e = n.alternate), e !== null && Xu(e) === null && (i = n), (n = n.sibling);
        (n = i),
          n === null ? ((i = t.child), (t.child = null)) : ((i = n.sibling), (n.sibling = null)),
          ef(t, !1, i, n, o);
        break;
      case "backwards":
        for (n = null, i = t.child, t.child = null; i !== null; ) {
          if (((e = i.alternate), e !== null && Xu(e) === null)) {
            t.child = i;
            break;
          }
          (e = i.sibling), (i.sibling = n), (n = i), (i = e);
        }
        ef(t, !0, n, null, o);
        break;
      case "together":
        ef(t, !1, null, null, void 0);
        break;
      default:
        t.memoizedState = null;
    }
  return t.child;
}
function yu(e, t) {
  !(t.mode & 1) && e !== null && ((e.alternate = null), (t.alternate = null), (t.flags |= 2));
}
function Gn(e, t, n) {
  if ((e !== null && (t.dependencies = e.dependencies), (ai |= t.lanes), !(n & t.childLanes)))
    return null;
  if (e !== null && t.child !== e.child) throw Error(z(153));
  if (t.child !== null) {
    for (e = t.child, n = Tr(e, e.pendingProps), t.child = n, n.return = t; e.sibling !== null; )
      (e = e.sibling), (n = n.sibling = Tr(e, e.pendingProps)), (n.return = t);
    n.sibling = null;
  }
  return t.child;
}
function iF(e, t, n) {
  switch (t.tag) {
    case 3:
      aP(t), oo();
      break;
    case 5:
      OR(t);
      break;
    case 1:
      vt(t.type) && Uu(t);
      break;
    case 4:
      Ly(t, t.stateNode.containerInfo);
      break;
    case 10:
      var r = t.type._context,
        i = t.memoizedProps.value;
      he(Wu, r._currentValue), (r._currentValue = i);
      break;
    case 13:
      if (((r = t.memoizedState), r !== null))
        return r.dehydrated !== null
          ? (he(xe, xe.current & 1), (t.flags |= 128), null)
          : n & t.child.childLanes
            ? uP(e, t, n)
            : (he(xe, xe.current & 1), (e = Gn(e, t, n)), e !== null ? e.sibling : null);
      he(xe, xe.current & 1);
      break;
    case 19:
      if (((r = (n & t.childLanes) !== 0), e.flags & 128)) {
        if (r) return lP(e, t, n);
        t.flags |= 128;
      }
      if (
        ((i = t.memoizedState),
        i !== null && ((i.rendering = null), (i.tail = null), (i.lastEffect = null)),
        he(xe, xe.current),
        r)
      )
        break;
      return null;
    case 22:
    case 23:
      return (t.lanes = 0), oP(e, t, n);
  }
  return Gn(e, t, n);
}
var cP, pv, fP, dP;
cP = function (e, t) {
  for (var n = t.child; n !== null; ) {
    if (n.tag === 5 || n.tag === 6) e.appendChild(n.stateNode);
    else if (n.tag !== 4 && n.child !== null) {
      (n.child.return = n), (n = n.child);
      continue;
    }
    if (n === t) break;
    for (; n.sibling === null; ) {
      if (n.return === null || n.return === t) return;
      n = n.return;
    }
    (n.sibling.return = n.return), (n = n.sibling);
  }
};
pv = function () {};
fP = function (e, t, n, r) {
  var i = e.memoizedProps;
  if (i !== r) {
    (e = t.stateNode), Kr(yn.current);
    var o = null;
    switch (n) {
      case "input":
        (i = Lg(e, i)), (r = Lg(e, r)), (o = []);
        break;
      case "select":
        (i = Se({}, i, { value: void 0 })), (r = Se({}, r, { value: void 0 })), (o = []);
        break;
      case "textarea":
        (i = Vg(e, i)), (r = Vg(e, r)), (o = []);
        break;
      default:
        typeof i.onClick != "function" && typeof r.onClick == "function" && (e.onclick = zu);
    }
    $g(n, r);
    var s;
    n = null;
    for (l in i)
      if (!r.hasOwnProperty(l) && i.hasOwnProperty(l) && i[l] != null)
        if (l === "style") {
          var a = i[l];
          for (s in a) a.hasOwnProperty(s) && (n || (n = {}), (n[s] = ""));
        } else
          l !== "dangerouslySetInnerHTML" &&
            l !== "children" &&
            l !== "suppressContentEditableWarning" &&
            l !== "suppressHydrationWarning" &&
            l !== "autoFocus" &&
            (Ps.hasOwnProperty(l) ? o || (o = []) : (o = o || []).push(l, null));
    for (l in r) {
      var u = r[l];
      if (
        ((a = i != null ? i[l] : void 0),
        r.hasOwnProperty(l) && u !== a && (u != null || a != null))
      )
        if (l === "style")
          if (a) {
            for (s in a)
              !a.hasOwnProperty(s) || (u && u.hasOwnProperty(s)) || (n || (n = {}), (n[s] = ""));
            for (s in u) u.hasOwnProperty(s) && a[s] !== u[s] && (n || (n = {}), (n[s] = u[s]));
          } else n || (o || (o = []), o.push(l, n)), (n = u);
        else
          l === "dangerouslySetInnerHTML"
            ? ((u = u ? u.__html : void 0),
              (a = a ? a.__html : void 0),
              u != null && a !== u && (o = o || []).push(l, u))
            : l === "children"
              ? (typeof u != "string" && typeof u != "number") || (o = o || []).push(l, "" + u)
              : l !== "suppressContentEditableWarning" &&
                l !== "suppressHydrationWarning" &&
                (Ps.hasOwnProperty(l)
                  ? (u != null && l === "onScroll" && me("scroll", e), o || a === u || (o = []))
                  : (o = o || []).push(l, u));
    }
    n && (o = o || []).push("style", n);
    var l = o;
    (t.updateQueue = l) && (t.flags |= 4);
  }
};
dP = function (e, t, n, r) {
  n !== r && (t.flags |= 4);
};
function zo(e, t) {
  if (!ye)
    switch (e.tailMode) {
      case "hidden":
        t = e.tail;
        for (var n = null; t !== null; ) t.alternate !== null && (n = t), (t = t.sibling);
        n === null ? (e.tail = null) : (n.sibling = null);
        break;
      case "collapsed":
        n = e.tail;
        for (var r = null; n !== null; ) n.alternate !== null && (r = n), (n = n.sibling);
        r === null
          ? t || e.tail === null
            ? (e.tail = null)
            : (e.tail.sibling = null)
          : (r.sibling = null);
    }
}
function et(e) {
  var t = e.alternate !== null && e.alternate.child === e.child,
    n = 0,
    r = 0;
  if (t)
    for (var i = e.child; i !== null; )
      (n |= i.lanes | i.childLanes),
        (r |= i.subtreeFlags & 14680064),
        (r |= i.flags & 14680064),
        (i.return = e),
        (i = i.sibling);
  else
    for (i = e.child; i !== null; )
      (n |= i.lanes | i.childLanes),
        (r |= i.subtreeFlags),
        (r |= i.flags),
        (i.return = e),
        (i = i.sibling);
  return (e.subtreeFlags |= r), (e.childLanes = n), t;
}
function oF(e, t, n) {
  var r = t.pendingProps;
  switch ((Py(t), t.tag)) {
    case 2:
    case 16:
    case 15:
    case 0:
    case 11:
    case 7:
    case 8:
    case 12:
    case 9:
    case 14:
      return et(t), null;
    case 1:
      return vt(t.type) && Bu(), et(t), null;
    case 3:
      return (
        (r = t.stateNode),
        ao(),
        ge(gt),
        ge(rt),
        jy(),
        r.pendingContext && ((r.context = r.pendingContext), (r.pendingContext = null)),
        (e === null || e.child === null) &&
          (Va(t)
            ? (t.flags |= 4)
            : e === null ||
              (e.memoizedState.isDehydrated && !(t.flags & 256)) ||
              ((t.flags |= 1024), Zt !== null && (bv(Zt), (Zt = null)))),
        pv(e, t),
        et(t),
        null
      );
    case 5:
      Fy(t);
      var i = Kr($s.current);
      if (((n = t.type), e !== null && t.stateNode != null))
        fP(e, t, n, r, i), e.ref !== t.ref && ((t.flags |= 512), (t.flags |= 2097152));
      else {
        if (!r) {
          if (t.stateNode === null) throw Error(z(166));
          return et(t), null;
        }
        if (((e = Kr(yn.current)), Va(t))) {
          (r = t.stateNode), (n = t.type);
          var o = t.memoizedProps;
          switch (((r[pn] = t), (r[Vs] = o), (e = (t.mode & 1) !== 0), n)) {
            case "dialog":
              me("cancel", r), me("close", r);
              break;
            case "iframe":
            case "object":
            case "embed":
              me("load", r);
              break;
            case "video":
            case "audio":
              for (i = 0; i < ts.length; i++) me(ts[i], r);
              break;
            case "source":
              me("error", r);
              break;
            case "img":
            case "image":
            case "link":
              me("error", r), me("load", r);
              break;
            case "details":
              me("toggle", r);
              break;
            case "input":
              Lw(r, o), me("invalid", r);
              break;
            case "select":
              (r._wrapperState = { wasMultiple: !!o.multiple }), me("invalid", r);
              break;
            case "textarea":
              jw(r, o), me("invalid", r);
          }
          $g(n, o), (i = null);
          for (var s in o)
            if (o.hasOwnProperty(s)) {
              var a = o[s];
              s === "children"
                ? typeof a == "string"
                  ? r.textContent !== a &&
                    (o.suppressHydrationWarning !== !0 && ja(r.textContent, a, e),
                    (i = ["children", a]))
                  : typeof a == "number" &&
                    r.textContent !== "" + a &&
                    (o.suppressHydrationWarning !== !0 && ja(r.textContent, a, e),
                    (i = ["children", "" + a]))
                : Ps.hasOwnProperty(s) && a != null && s === "onScroll" && me("scroll", r);
            }
          switch (n) {
            case "input":
              Aa(r), Fw(r, o, !0);
              break;
            case "textarea":
              Aa(r), Vw(r);
              break;
            case "select":
            case "option":
              break;
            default:
              typeof o.onClick == "function" && (r.onclick = zu);
          }
          (r = i), (t.updateQueue = r), r !== null && (t.flags |= 4);
        } else {
          (s = i.nodeType === 9 ? i : i.ownerDocument),
            e === "http://www.w3.org/1999/xhtml" && (e = qk(n)),
            e === "http://www.w3.org/1999/xhtml"
              ? n === "script"
                ? ((e = s.createElement("div")),
                  (e.innerHTML = "<script></script>"),
                  (e = e.removeChild(e.firstChild)))
                : typeof r.is == "string"
                  ? (e = s.createElement(n, { is: r.is }))
                  : ((e = s.createElement(n)),
                    n === "select" &&
                      ((s = e), r.multiple ? (s.multiple = !0) : r.size && (s.size = r.size)))
              : (e = s.createElementNS(e, n)),
            (e[pn] = t),
            (e[Vs] = r),
            cP(e, t, !1, !1),
            (t.stateNode = e);
          e: {
            switch (((s = zg(n, r)), n)) {
              case "dialog":
                me("cancel", e), me("close", e), (i = r);
                break;
              case "iframe":
              case "object":
              case "embed":
                me("load", e), (i = r);
                break;
              case "video":
              case "audio":
                for (i = 0; i < ts.length; i++) me(ts[i], e);
                i = r;
                break;
              case "source":
                me("error", e), (i = r);
                break;
              case "img":
              case "image":
              case "link":
                me("error", e), me("load", e), (i = r);
                break;
              case "details":
                me("toggle", e), (i = r);
                break;
              case "input":
                Lw(e, r), (i = Lg(e, r)), me("invalid", e);
                break;
              case "option":
                i = r;
                break;
              case "select":
                (e._wrapperState = { wasMultiple: !!r.multiple }),
                  (i = Se({}, r, { value: void 0 })),
                  me("invalid", e);
                break;
              case "textarea":
                jw(e, r), (i = Vg(e, r)), me("invalid", e);
                break;
              default:
                i = r;
            }
            $g(n, i), (a = i);
            for (o in a)
              if (a.hasOwnProperty(o)) {
                var u = a[o];
                o === "style"
                  ? Bk(e, u)
                  : o === "dangerouslySetInnerHTML"
                    ? ((u = u ? u.__html : void 0), u != null && $k(e, u))
                    : o === "children"
                      ? typeof u == "string"
                        ? (n !== "textarea" || u !== "") && As(e, u)
                        : typeof u == "number" && As(e, "" + u)
                      : o !== "suppressContentEditableWarning" &&
                        o !== "suppressHydrationWarning" &&
                        o !== "autoFocus" &&
                        (Ps.hasOwnProperty(o)
                          ? u != null && o === "onScroll" && me("scroll", e)
                          : u != null && py(e, o, u, s));
              }
            switch (n) {
              case "input":
                Aa(e), Fw(e, r, !1);
                break;
              case "textarea":
                Aa(e), Vw(e);
                break;
              case "option":
                r.value != null && e.setAttribute("value", "" + Pr(r.value));
                break;
              case "select":
                (e.multiple = !!r.multiple),
                  (o = r.value),
                  o != null
                    ? Gi(e, !!r.multiple, o, !1)
                    : r.defaultValue != null && Gi(e, !!r.multiple, r.defaultValue, !0);
                break;
              default:
                typeof i.onClick == "function" && (e.onclick = zu);
            }
            switch (n) {
              case "button":
              case "input":
              case "select":
              case "textarea":
                r = !!r.autoFocus;
                break e;
              case "img":
                r = !0;
                break e;
              default:
                r = !1;
            }
          }
          r && (t.flags |= 4);
        }
        t.ref !== null && ((t.flags |= 512), (t.flags |= 2097152));
      }
      return et(t), null;
    case 6:
      if (e && t.stateNode != null) dP(e, t, e.memoizedProps, r);
      else {
        if (typeof r != "string" && t.stateNode === null) throw Error(z(166));
        if (((n = Kr($s.current)), Kr(yn.current), Va(t))) {
          if (
            ((r = t.stateNode),
            (n = t.memoizedProps),
            (r[pn] = t),
            (o = r.nodeValue !== n) && ((e = Et), e !== null))
          )
            switch (e.tag) {
              case 3:
                ja(r.nodeValue, n, (e.mode & 1) !== 0);
                break;
              case 5:
                e.memoizedProps.suppressHydrationWarning !== !0 &&
                  ja(r.nodeValue, n, (e.mode & 1) !== 0);
            }
          o && (t.flags |= 4);
        } else
          (r = (n.nodeType === 9 ? n : n.ownerDocument).createTextNode(r)),
            (r[pn] = t),
            (t.stateNode = r);
      }
      return et(t), null;
    case 13:
      if (
        (ge(xe),
        (r = t.memoizedState),
        e === null || (e.memoizedState !== null && e.memoizedState.dehydrated !== null))
      ) {
        if (ye && St !== null && t.mode & 1 && !(t.flags & 128))
          AR(), oo(), (t.flags |= 98560), (o = !1);
        else if (((o = Va(t)), r !== null && r.dehydrated !== null)) {
          if (e === null) {
            if (!o) throw Error(z(318));
            if (((o = t.memoizedState), (o = o !== null ? o.dehydrated : null), !o))
              throw Error(z(317));
            o[pn] = t;
          } else oo(), !(t.flags & 128) && (t.memoizedState = null), (t.flags |= 4);
          et(t), (o = !1);
        } else Zt !== null && (bv(Zt), (Zt = null)), (o = !0);
        if (!o) return t.flags & 65536 ? t : null;
      }
      return t.flags & 128
        ? ((t.lanes = n), t)
        : ((r = r !== null),
          r !== (e !== null && e.memoizedState !== null) &&
            r &&
            ((t.child.flags |= 8192),
            t.mode & 1 && (e === null || xe.current & 1 ? Le === 0 && (Le = 3) : Xy())),
          t.updateQueue !== null && (t.flags |= 4),
          et(t),
          null);
    case 4:
      return ao(), pv(e, t), e === null && Fs(t.stateNode.containerInfo), et(t), null;
    case 10:
      return Iy(t.type._context), et(t), null;
    case 17:
      return vt(t.type) && Bu(), et(t), null;
    case 19:
      if ((ge(xe), (o = t.memoizedState), o === null)) return et(t), null;
      if (((r = (t.flags & 128) !== 0), (s = o.rendering), s === null))
        if (r) zo(o, !1);
        else {
          if (Le !== 0 || (e !== null && e.flags & 128))
            for (e = t.child; e !== null; ) {
              if (((s = Xu(e)), s !== null)) {
                for (
                  t.flags |= 128,
                    zo(o, !1),
                    r = s.updateQueue,
                    r !== null && ((t.updateQueue = r), (t.flags |= 4)),
                    t.subtreeFlags = 0,
                    r = n,
                    n = t.child;
                  n !== null;

                )
                  (o = n),
                    (e = r),
                    (o.flags &= 14680066),
                    (s = o.alternate),
                    s === null
                      ? ((o.childLanes = 0),
                        (o.lanes = e),
                        (o.child = null),
                        (o.subtreeFlags = 0),
                        (o.memoizedProps = null),
                        (o.memoizedState = null),
                        (o.updateQueue = null),
                        (o.dependencies = null),
                        (o.stateNode = null))
                      : ((o.childLanes = s.childLanes),
                        (o.lanes = s.lanes),
                        (o.child = s.child),
                        (o.subtreeFlags = 0),
                        (o.deletions = null),
                        (o.memoizedProps = s.memoizedProps),
                        (o.memoizedState = s.memoizedState),
                        (o.updateQueue = s.updateQueue),
                        (o.type = s.type),
                        (e = s.dependencies),
                        (o.dependencies =
                          e === null ? null : { lanes: e.lanes, firstContext: e.firstContext })),
                    (n = n.sibling);
                return he(xe, (xe.current & 1) | 2), t.child;
              }
              e = e.sibling;
            }
          o.tail !== null &&
            Ne() > lo &&
            ((t.flags |= 128), (r = !0), zo(o, !1), (t.lanes = 4194304));
        }
      else {
        if (!r)
          if (((e = Xu(s)), e !== null)) {
            if (
              ((t.flags |= 128),
              (r = !0),
              (n = e.updateQueue),
              n !== null && ((t.updateQueue = n), (t.flags |= 4)),
              zo(o, !0),
              o.tail === null && o.tailMode === "hidden" && !s.alternate && !ye)
            )
              return et(t), null;
          } else
            2 * Ne() - o.renderingStartTime > lo &&
              n !== 1073741824 &&
              ((t.flags |= 128), (r = !0), zo(o, !1), (t.lanes = 4194304));
        o.isBackwards
          ? ((s.sibling = t.child), (t.child = s))
          : ((n = o.last), n !== null ? (n.sibling = s) : (t.child = s), (o.last = s));
      }
      return o.tail !== null
        ? ((t = o.tail),
          (o.rendering = t),
          (o.tail = t.sibling),
          (o.renderingStartTime = Ne()),
          (t.sibling = null),
          (n = xe.current),
          he(xe, r ? (n & 1) | 2 : n & 1),
          t)
        : (et(t), null);
    case 22:
    case 23:
      return (
        Yy(),
        (r = t.memoizedState !== null),
        e !== null && (e.memoizedState !== null) !== r && (t.flags |= 8192),
        r && t.mode & 1
          ? _t & 1073741824 && (et(t), t.subtreeFlags & 6 && (t.flags |= 8192))
          : et(t),
        null
      );
    case 24:
      return null;
    case 25:
      return null;
  }
  throw Error(z(156, t.tag));
}
function sF(e, t) {
  switch ((Py(t), t.tag)) {
    case 1:
      return (
        vt(t.type) && Bu(), (e = t.flags), e & 65536 ? ((t.flags = (e & -65537) | 128), t) : null
      );
    case 3:
      return (
        ao(),
        ge(gt),
        ge(rt),
        jy(),
        (e = t.flags),
        e & 65536 && !(e & 128) ? ((t.flags = (e & -65537) | 128), t) : null
      );
    case 5:
      return Fy(t), null;
    case 13:
      if ((ge(xe), (e = t.memoizedState), e !== null && e.dehydrated !== null)) {
        if (t.alternate === null) throw Error(z(340));
        oo();
      }
      return (e = t.flags), e & 65536 ? ((t.flags = (e & -65537) | 128), t) : null;
    case 19:
      return ge(xe), null;
    case 4:
      return ao(), null;
    case 10:
      return Iy(t.type._context), null;
    case 22:
    case 23:
      return Yy(), null;
    case 24:
      return null;
    default:
      return null;
  }
}
var za = !1,
  nt = !1,
  aF = typeof WeakSet == "function" ? WeakSet : Set,
  H = null;
function ji(e, t) {
  var n = e.ref;
  if (n !== null)
    if (typeof n == "function")
      try {
        n(null);
      } catch (r) {
        Te(e, t, r);
      }
    else n.current = null;
}
function mv(e, t, n) {
  try {
    n();
  } catch (r) {
    Te(e, t, r);
  }
}
var R1 = !1;
function uF(e, t) {
  if (((Qg = Vu), (e = vR()), ky(e))) {
    if ("selectionStart" in e) var n = { start: e.selectionStart, end: e.selectionEnd };
    else
      e: {
        n = ((n = e.ownerDocument) && n.defaultView) || window;
        var r = n.getSelection && n.getSelection();
        if (r && r.rangeCount !== 0) {
          n = r.anchorNode;
          var i = r.anchorOffset,
            o = r.focusNode;
          r = r.focusOffset;
          try {
            n.nodeType, o.nodeType;
          } catch {
            n = null;
            break e;
          }
          var s = 0,
            a = -1,
            u = -1,
            l = 0,
            c = 0,
            f = e,
            d = null;
          t: for (;;) {
            for (
              var h;
              f !== n || (i !== 0 && f.nodeType !== 3) || (a = s + i),
                f !== o || (r !== 0 && f.nodeType !== 3) || (u = s + r),
                f.nodeType === 3 && (s += f.nodeValue.length),
                (h = f.firstChild) !== null;

            )
              (d = f), (f = h);
            for (;;) {
              if (f === e) break t;
              if (
                (d === n && ++l === i && (a = s),
                d === o && ++c === r && (u = s),
                (h = f.nextSibling) !== null)
              )
                break;
              (f = d), (d = f.parentNode);
            }
            f = h;
          }
          n = a === -1 || u === -1 ? null : { start: a, end: u };
        } else n = null;
      }
    n = n || { start: 0, end: 0 };
  } else n = null;
  for (Jg = { focusedElem: e, selectionRange: n }, Vu = !1, H = t; H !== null; )
    if (((t = H), (e = t.child), (t.subtreeFlags & 1028) !== 0 && e !== null))
      (e.return = t), (H = e);
    else
      for (; H !== null; ) {
        t = H;
        try {
          var v = t.alternate;
          if (t.flags & 1024)
            switch (t.tag) {
              case 0:
              case 11:
              case 15:
                break;
              case 1:
                if (v !== null) {
                  var p = v.memoizedProps,
                    y = v.memoizedState,
                    m = t.stateNode,
                    g = m.getSnapshotBeforeUpdate(t.elementType === t.type ? p : Kt(t.type, p), y);
                  m.__reactInternalSnapshotBeforeUpdate = g;
                }
                break;
              case 3:
                var w = t.stateNode.containerInfo;
                w.nodeType === 1
                  ? (w.textContent = "")
                  : w.nodeType === 9 && w.documentElement && w.removeChild(w.documentElement);
                break;
              case 5:
              case 6:
              case 4:
              case 17:
                break;
              default:
                throw Error(z(163));
            }
        } catch (x) {
          Te(t, t.return, x);
        }
        if (((e = t.sibling), e !== null)) {
          (e.return = t.return), (H = e);
          break;
        }
        H = t.return;
      }
  return (v = R1), (R1 = !1), v;
}
function xs(e, t, n) {
  var r = t.updateQueue;
  if (((r = r !== null ? r.lastEffect : null), r !== null)) {
    var i = (r = r.next);
    do {
      if ((i.tag & e) === e) {
        var o = i.destroy;
        (i.destroy = void 0), o !== void 0 && mv(t, n, o);
      }
      i = i.next;
    } while (i !== r);
  }
}
function Dl(e, t) {
  if (((t = t.updateQueue), (t = t !== null ? t.lastEffect : null), t !== null)) {
    var n = (t = t.next);
    do {
      if ((n.tag & e) === e) {
        var r = n.create;
        n.destroy = r();
      }
      n = n.next;
    } while (n !== t);
  }
}
function gv(e) {
  var t = e.ref;
  if (t !== null) {
    var n = e.stateNode;
    switch (e.tag) {
      case 5:
        e = n;
        break;
      default:
        e = n;
    }
    typeof t == "function" ? t(e) : (t.current = e);
  }
}
function hP(e) {
  var t = e.alternate;
  t !== null && ((e.alternate = null), hP(t)),
    (e.child = null),
    (e.deletions = null),
    (e.sibling = null),
    e.tag === 5 &&
      ((t = e.stateNode),
      t !== null && (delete t[pn], delete t[Vs], delete t[nv], delete t[UL], delete t[HL])),
    (e.stateNode = null),
    (e.return = null),
    (e.dependencies = null),
    (e.memoizedProps = null),
    (e.memoizedState = null),
    (e.pendingProps = null),
    (e.stateNode = null),
    (e.updateQueue = null);
}
function pP(e) {
  return e.tag === 5 || e.tag === 3 || e.tag === 4;
}
function P1(e) {
  e: for (;;) {
    for (; e.sibling === null; ) {
      if (e.return === null || pP(e.return)) return null;
      e = e.return;
    }
    for (e.sibling.return = e.return, e = e.sibling; e.tag !== 5 && e.tag !== 6 && e.tag !== 18; ) {
      if (e.flags & 2 || e.child === null || e.tag === 4) continue e;
      (e.child.return = e), (e = e.child);
    }
    if (!(e.flags & 2)) return e.stateNode;
  }
}
function vv(e, t, n) {
  var r = e.tag;
  if (r === 5 || r === 6)
    (e = e.stateNode),
      t
        ? n.nodeType === 8
          ? n.parentNode.insertBefore(e, t)
          : n.insertBefore(e, t)
        : (n.nodeType === 8
            ? ((t = n.parentNode), t.insertBefore(e, n))
            : ((t = n), t.appendChild(e)),
          (n = n._reactRootContainer),
          n != null || t.onclick !== null || (t.onclick = zu));
  else if (r !== 4 && ((e = e.child), e !== null))
    for (vv(e, t, n), e = e.sibling; e !== null; ) vv(e, t, n), (e = e.sibling);
}
function yv(e, t, n) {
  var r = e.tag;
  if (r === 5 || r === 6) (e = e.stateNode), t ? n.insertBefore(e, t) : n.appendChild(e);
  else if (r !== 4 && ((e = e.child), e !== null))
    for (yv(e, t, n), e = e.sibling; e !== null; ) yv(e, t, n), (e = e.sibling);
}
var We = null,
  Yt = !1;
function nr(e, t, n) {
  for (n = n.child; n !== null; ) mP(e, t, n), (n = n.sibling);
}
function mP(e, t, n) {
  if (vn && typeof vn.onCommitFiberUnmount == "function")
    try {
      vn.onCommitFiberUnmount(Tl, n);
    } catch {}
  switch (n.tag) {
    case 5:
      nt || ji(n, t);
    case 6:
      var r = We,
        i = Yt;
      (We = null),
        nr(e, t, n),
        (We = r),
        (Yt = i),
        We !== null &&
          (Yt
            ? ((e = We),
              (n = n.stateNode),
              e.nodeType === 8 ? e.parentNode.removeChild(n) : e.removeChild(n))
            : We.removeChild(n.stateNode));
      break;
    case 18:
      We !== null &&
        (Yt
          ? ((e = We),
            (n = n.stateNode),
            e.nodeType === 8 ? Wc(e.parentNode, n) : e.nodeType === 1 && Wc(e, n),
            Ds(e))
          : Wc(We, n.stateNode));
      break;
    case 4:
      (r = We),
        (i = Yt),
        (We = n.stateNode.containerInfo),
        (Yt = !0),
        nr(e, t, n),
        (We = r),
        (Yt = i);
      break;
    case 0:
    case 11:
    case 14:
    case 15:
      if (!nt && ((r = n.updateQueue), r !== null && ((r = r.lastEffect), r !== null))) {
        i = r = r.next;
        do {
          var o = i,
            s = o.destroy;
          (o = o.tag), s !== void 0 && (o & 2 || o & 4) && mv(n, t, s), (i = i.next);
        } while (i !== r);
      }
      nr(e, t, n);
      break;
    case 1:
      if (!nt && (ji(n, t), (r = n.stateNode), typeof r.componentWillUnmount == "function"))
        try {
          (r.props = n.memoizedProps), (r.state = n.memoizedState), r.componentWillUnmount();
        } catch (a) {
          Te(n, t, a);
        }
      nr(e, t, n);
      break;
    case 21:
      nr(e, t, n);
      break;
    case 22:
      n.mode & 1
        ? ((nt = (r = nt) || n.memoizedState !== null), nr(e, t, n), (nt = r))
        : nr(e, t, n);
      break;
    default:
      nr(e, t, n);
  }
}
function A1(e) {
  var t = e.updateQueue;
  if (t !== null) {
    e.updateQueue = null;
    var n = e.stateNode;
    n === null && (n = e.stateNode = new aF()),
      t.forEach(function (r) {
        var i = vF.bind(null, e, r);
        n.has(r) || (n.add(r), r.then(i, i));
      });
  }
}
function Gt(e, t) {
  var n = t.deletions;
  if (n !== null)
    for (var r = 0; r < n.length; r++) {
      var i = n[r];
      try {
        var o = e,
          s = t,
          a = s;
        e: for (; a !== null; ) {
          switch (a.tag) {
            case 5:
              (We = a.stateNode), (Yt = !1);
              break e;
            case 3:
              (We = a.stateNode.containerInfo), (Yt = !0);
              break e;
            case 4:
              (We = a.stateNode.containerInfo), (Yt = !0);
              break e;
          }
          a = a.return;
        }
        if (We === null) throw Error(z(160));
        mP(o, s, i), (We = null), (Yt = !1);
        var u = i.alternate;
        u !== null && (u.return = null), (i.return = null);
      } catch (l) {
        Te(i, t, l);
      }
    }
  if (t.subtreeFlags & 12854) for (t = t.child; t !== null; ) gP(t, e), (t = t.sibling);
}
function gP(e, t) {
  var n = e.alternate,
    r = e.flags;
  switch (e.tag) {
    case 0:
    case 11:
    case 14:
    case 15:
      if ((Gt(t, e), fn(e), r & 4)) {
        try {
          xs(3, e, e.return), Dl(3, e);
        } catch (p) {
          Te(e, e.return, p);
        }
        try {
          xs(5, e, e.return);
        } catch (p) {
          Te(e, e.return, p);
        }
      }
      break;
    case 1:
      Gt(t, e), fn(e), r & 512 && n !== null && ji(n, n.return);
      break;
    case 5:
      if ((Gt(t, e), fn(e), r & 512 && n !== null && ji(n, n.return), e.flags & 32)) {
        var i = e.stateNode;
        try {
          As(i, "");
        } catch (p) {
          Te(e, e.return, p);
        }
      }
      if (r & 4 && ((i = e.stateNode), i != null)) {
        var o = e.memoizedProps,
          s = n !== null ? n.memoizedProps : o,
          a = e.type,
          u = e.updateQueue;
        if (((e.updateQueue = null), u !== null))
          try {
            a === "input" && o.type === "radio" && o.name != null && jk(i, o), zg(a, s);
            var l = zg(a, o);
            for (s = 0; s < u.length; s += 2) {
              var c = u[s],
                f = u[s + 1];
              c === "style"
                ? Bk(i, f)
                : c === "dangerouslySetInnerHTML"
                  ? $k(i, f)
                  : c === "children"
                    ? As(i, f)
                    : py(i, c, f, l);
            }
            switch (a) {
              case "input":
                Fg(i, o);
                break;
              case "textarea":
                Vk(i, o);
                break;
              case "select":
                var d = i._wrapperState.wasMultiple;
                i._wrapperState.wasMultiple = !!o.multiple;
                var h = o.value;
                h != null
                  ? Gi(i, !!o.multiple, h, !1)
                  : d !== !!o.multiple &&
                    (o.defaultValue != null
                      ? Gi(i, !!o.multiple, o.defaultValue, !0)
                      : Gi(i, !!o.multiple, o.multiple ? [] : "", !1));
            }
            i[Vs] = o;
          } catch (p) {
            Te(e, e.return, p);
          }
      }
      break;
    case 6:
      if ((Gt(t, e), fn(e), r & 4)) {
        if (e.stateNode === null) throw Error(z(162));
        (i = e.stateNode), (o = e.memoizedProps);
        try {
          i.nodeValue = o;
        } catch (p) {
          Te(e, e.return, p);
        }
      }
      break;
    case 3:
      if ((Gt(t, e), fn(e), r & 4 && n !== null && n.memoizedState.isDehydrated))
        try {
          Ds(t.containerInfo);
        } catch (p) {
          Te(e, e.return, p);
        }
      break;
    case 4:
      Gt(t, e), fn(e);
      break;
    case 13:
      Gt(t, e),
        fn(e),
        (i = e.child),
        i.flags & 8192 &&
          ((o = i.memoizedState !== null),
          (i.stateNode.isHidden = o),
          !o || (i.alternate !== null && i.alternate.memoizedState !== null) || (Wy = Ne())),
        r & 4 && A1(e);
      break;
    case 22:
      if (
        ((c = n !== null && n.memoizedState !== null),
        e.mode & 1 ? ((nt = (l = nt) || c), Gt(t, e), (nt = l)) : Gt(t, e),
        fn(e),
        r & 8192)
      ) {
        if (((l = e.memoizedState !== null), (e.stateNode.isHidden = l) && !c && e.mode & 1))
          for (H = e, c = e.child; c !== null; ) {
            for (f = H = c; H !== null; ) {
              switch (((d = H), (h = d.child), d.tag)) {
                case 0:
                case 11:
                case 14:
                case 15:
                  xs(4, d, d.return);
                  break;
                case 1:
                  ji(d, d.return);
                  var v = d.stateNode;
                  if (typeof v.componentWillUnmount == "function") {
                    (r = d), (n = d.return);
                    try {
                      (t = r),
                        (v.props = t.memoizedProps),
                        (v.state = t.memoizedState),
                        v.componentWillUnmount();
                    } catch (p) {
                      Te(r, n, p);
                    }
                  }
                  break;
                case 5:
                  ji(d, d.return);
                  break;
                case 22:
                  if (d.memoizedState !== null) {
                    M1(f);
                    continue;
                  }
              }
              h !== null ? ((h.return = d), (H = h)) : M1(f);
            }
            c = c.sibling;
          }
        e: for (c = null, f = e; ; ) {
          if (f.tag === 5) {
            if (c === null) {
              c = f;
              try {
                (i = f.stateNode),
                  l
                    ? ((o = i.style),
                      typeof o.setProperty == "function"
                        ? o.setProperty("display", "none", "important")
                        : (o.display = "none"))
                    : ((a = f.stateNode),
                      (u = f.memoizedProps.style),
                      (s = u != null && u.hasOwnProperty("display") ? u.display : null),
                      (a.style.display = zk("display", s)));
              } catch (p) {
                Te(e, e.return, p);
              }
            }
          } else if (f.tag === 6) {
            if (c === null)
              try {
                f.stateNode.nodeValue = l ? "" : f.memoizedProps;
              } catch (p) {
                Te(e, e.return, p);
              }
          } else if (
            ((f.tag !== 22 && f.tag !== 23) || f.memoizedState === null || f === e) &&
            f.child !== null
          ) {
            (f.child.return = f), (f = f.child);
            continue;
          }
          if (f === e) break e;
          for (; f.sibling === null; ) {
            if (f.return === null || f.return === e) break e;
            c === f && (c = null), (f = f.return);
          }
          c === f && (c = null), (f.sibling.return = f.return), (f = f.sibling);
        }
      }
      break;
    case 19:
      Gt(t, e), fn(e), r & 4 && A1(e);
      break;
    case 21:
      break;
    default:
      Gt(t, e), fn(e);
  }
}
function fn(e) {
  var t = e.flags;
  if (t & 2) {
    try {
      e: {
        for (var n = e.return; n !== null; ) {
          if (pP(n)) {
            var r = n;
            break e;
          }
          n = n.return;
        }
        throw Error(z(160));
      }
      switch (r.tag) {
        case 5:
          var i = r.stateNode;
          r.flags & 32 && (As(i, ""), (r.flags &= -33));
          var o = P1(e);
          yv(e, o, i);
          break;
        case 3:
        case 4:
          var s = r.stateNode.containerInfo,
            a = P1(e);
          vv(e, a, s);
          break;
        default:
          throw Error(z(161));
      }
    } catch (u) {
      Te(e, e.return, u);
    }
    e.flags &= -3;
  }
  t & 4096 && (e.flags &= -4097);
}
function lF(e, t, n) {
  (H = e), vP(e);
}
function vP(e, t, n) {
  for (var r = (e.mode & 1) !== 0; H !== null; ) {
    var i = H,
      o = i.child;
    if (i.tag === 22 && r) {
      var s = i.memoizedState !== null || za;
      if (!s) {
        var a = i.alternate,
          u = (a !== null && a.memoizedState !== null) || nt;
        a = za;
        var l = nt;
        if (((za = s), (nt = u) && !l))
          for (H = i; H !== null; )
            (s = H),
              (u = s.child),
              s.tag === 22 && s.memoizedState !== null
                ? I1(i)
                : u !== null
                  ? ((u.return = s), (H = u))
                  : I1(i);
        for (; o !== null; ) (H = o), vP(o), (o = o.sibling);
        (H = i), (za = a), (nt = l);
      }
      N1(e);
    } else i.subtreeFlags & 8772 && o !== null ? ((o.return = i), (H = o)) : N1(e);
  }
}
function N1(e) {
  for (; H !== null; ) {
    var t = H;
    if (t.flags & 8772) {
      var n = t.alternate;
      try {
        if (t.flags & 8772)
          switch (t.tag) {
            case 0:
            case 11:
            case 15:
              nt || Dl(5, t);
              break;
            case 1:
              var r = t.stateNode;
              if (t.flags & 4 && !nt)
                if (n === null) r.componentDidMount();
                else {
                  var i = t.elementType === t.type ? n.memoizedProps : Kt(t.type, n.memoizedProps);
                  r.componentDidUpdate(i, n.memoizedState, r.__reactInternalSnapshotBeforeUpdate);
                }
              var o = t.updateQueue;
              o !== null && m1(t, o, r);
              break;
            case 3:
              var s = t.updateQueue;
              if (s !== null) {
                if (((n = null), t.child !== null))
                  switch (t.child.tag) {
                    case 5:
                      n = t.child.stateNode;
                      break;
                    case 1:
                      n = t.child.stateNode;
                  }
                m1(t, s, n);
              }
              break;
            case 5:
              var a = t.stateNode;
              if (n === null && t.flags & 4) {
                n = a;
                var u = t.memoizedProps;
                switch (t.type) {
                  case "button":
                  case "input":
                  case "select":
                  case "textarea":
                    u.autoFocus && n.focus();
                    break;
                  case "img":
                    u.src && (n.src = u.src);
                }
              }
              break;
            case 6:
              break;
            case 4:
              break;
            case 12:
              break;
            case 13:
              if (t.memoizedState === null) {
                var l = t.alternate;
                if (l !== null) {
                  var c = l.memoizedState;
                  if (c !== null) {
                    var f = c.dehydrated;
                    f !== null && Ds(f);
                  }
                }
              }
              break;
            case 19:
            case 17:
            case 21:
            case 22:
            case 23:
            case 25:
              break;
            default:
              throw Error(z(163));
          }
        nt || (t.flags & 512 && gv(t));
      } catch (d) {
        Te(t, t.return, d);
      }
    }
    if (t === e) {
      H = null;
      break;
    }
    if (((n = t.sibling), n !== null)) {
      (n.return = t.return), (H = n);
      break;
    }
    H = t.return;
  }
}
function M1(e) {
  for (; H !== null; ) {
    var t = H;
    if (t === e) {
      H = null;
      break;
    }
    var n = t.sibling;
    if (n !== null) {
      (n.return = t.return), (H = n);
      break;
    }
    H = t.return;
  }
}
function I1(e) {
  for (; H !== null; ) {
    var t = H;
    try {
      switch (t.tag) {
        case 0:
        case 11:
        case 15:
          var n = t.return;
          try {
            Dl(4, t);
          } catch (u) {
            Te(t, n, u);
          }
          break;
        case 1:
          var r = t.stateNode;
          if (typeof r.componentDidMount == "function") {
            var i = t.return;
            try {
              r.componentDidMount();
            } catch (u) {
              Te(t, i, u);
            }
          }
          var o = t.return;
          try {
            gv(t);
          } catch (u) {
            Te(t, o, u);
          }
          break;
        case 5:
          var s = t.return;
          try {
            gv(t);
          } catch (u) {
            Te(t, s, u);
          }
      }
    } catch (u) {
      Te(t, t.return, u);
    }
    if (t === e) {
      H = null;
      break;
    }
    var a = t.sibling;
    if (a !== null) {
      (a.return = t.return), (H = a);
      break;
    }
    H = t.return;
  }
}
var cF = Math.ceil,
  Ju = Qn.ReactCurrentDispatcher,
  Hy = Qn.ReactCurrentOwner,
  jt = Qn.ReactCurrentBatchConfig,
  ae = 0,
  Ue = null,
  Me = null,
  Ke = 0,
  _t = 0,
  Vi = Dr(0),
  Le = 0,
  Hs = null,
  ai = 0,
  Ol = 0,
  Gy = 0,
  _s = null,
  ht = null,
  Wy = 0,
  lo = 1 / 0,
  Nn = null,
  el = !1,
  wv = null,
  Er = null,
  Ba = !1,
  vr = null,
  tl = 0,
  bs = 0,
  xv = null,
  wu = -1,
  xu = 0;
function at() {
  return ae & 6 ? Ne() : wu !== -1 ? wu : (wu = Ne());
}
function Cr(e) {
  return e.mode & 1
    ? ae & 2 && Ke !== 0
      ? Ke & -Ke
      : WL.transition !== null
        ? (xu === 0 && (xu = tR()), xu)
        : ((e = ce), e !== 0 || ((e = window.event), (e = e === void 0 ? 16 : uR(e.type))), e)
    : 1;
}
function en(e, t, n, r) {
  if (50 < bs) throw ((bs = 0), (xv = null), Error(z(185)));
  sa(e, n, r),
    (!(ae & 2) || e !== Ue) &&
      (e === Ue && (!(ae & 2) && (Ol |= n), Le === 4 && pr(e, Ke)),
      yt(e, r),
      n === 1 && ae === 0 && !(t.mode & 1) && ((lo = Ne() + 500), Nl && Or()));
}
function yt(e, t) {
  var n = e.callbackNode;
  WO(e, t);
  var r = ju(e, e === Ue ? Ke : 0);
  if (r === 0) n !== null && zw(n), (e.callbackNode = null), (e.callbackPriority = 0);
  else if (((t = r & -r), e.callbackPriority !== t)) {
    if ((n != null && zw(n), t === 1))
      e.tag === 0 ? GL(D1.bind(null, e)) : kR(D1.bind(null, e)),
        zL(function () {
          !(ae & 6) && Or();
        }),
        (n = null);
    else {
      switch (nR(r)) {
        case 1:
          n = wy;
          break;
        case 4:
          n = Jk;
          break;
        case 16:
          n = Fu;
          break;
        case 536870912:
          n = eR;
          break;
        default:
          n = Fu;
      }
      n = CP(n, yP.bind(null, e));
    }
    (e.callbackPriority = t), (e.callbackNode = n);
  }
}
function yP(e, t) {
  if (((wu = -1), (xu = 0), ae & 6)) throw Error(z(327));
  var n = e.callbackNode;
  if (Zi() && e.callbackNode !== n) return null;
  var r = ju(e, e === Ue ? Ke : 0);
  if (r === 0) return null;
  if (r & 30 || r & e.expiredLanes || t) t = nl(e, r);
  else {
    t = r;
    var i = ae;
    ae |= 2;
    var o = xP();
    (Ue !== e || Ke !== t) && ((Nn = null), (lo = Ne() + 500), Jr(e, t));
    do
      try {
        hF();
        break;
      } catch (a) {
        wP(e, a);
      }
    while (!0);
    My(), (Ju.current = o), (ae = i), Me !== null ? (t = 0) : ((Ue = null), (Ke = 0), (t = Le));
  }
  if (t !== 0) {
    if ((t === 2 && ((i = Wg(e)), i !== 0 && ((r = i), (t = _v(e, i)))), t === 1))
      throw ((n = Hs), Jr(e, 0), pr(e, r), yt(e, Ne()), n);
    if (t === 6) pr(e, r);
    else {
      if (
        ((i = e.current.alternate),
        !(r & 30) &&
          !fF(i) &&
          ((t = nl(e, r)), t === 2 && ((o = Wg(e)), o !== 0 && ((r = o), (t = _v(e, o)))), t === 1))
      )
        throw ((n = Hs), Jr(e, 0), pr(e, r), yt(e, Ne()), n);
      switch (((e.finishedWork = i), (e.finishedLanes = r), t)) {
        case 0:
        case 1:
          throw Error(z(345));
        case 2:
          zr(e, ht, Nn);
          break;
        case 3:
          if ((pr(e, r), (r & 130023424) === r && ((t = Wy + 500 - Ne()), 10 < t))) {
            if (ju(e, 0) !== 0) break;
            if (((i = e.suspendedLanes), (i & r) !== r)) {
              at(), (e.pingedLanes |= e.suspendedLanes & i);
              break;
            }
            e.timeoutHandle = tv(zr.bind(null, e, ht, Nn), t);
            break;
          }
          zr(e, ht, Nn);
          break;
        case 4:
          if ((pr(e, r), (r & 4194240) === r)) break;
          for (t = e.eventTimes, i = -1; 0 < r; ) {
            var s = 31 - Jt(r);
            (o = 1 << s), (s = t[s]), s > i && (i = s), (r &= ~o);
          }
          if (
            ((r = i),
            (r = Ne() - r),
            (r =
              (120 > r
                ? 120
                : 480 > r
                  ? 480
                  : 1080 > r
                    ? 1080
                    : 1920 > r
                      ? 1920
                      : 3e3 > r
                        ? 3e3
                        : 4320 > r
                          ? 4320
                          : 1960 * cF(r / 1960)) - r),
            10 < r)
          ) {
            e.timeoutHandle = tv(zr.bind(null, e, ht, Nn), r);
            break;
          }
          zr(e, ht, Nn);
          break;
        case 5:
          zr(e, ht, Nn);
          break;
        default:
          throw Error(z(329));
      }
    }
  }
  return yt(e, Ne()), e.callbackNode === n ? yP.bind(null, e) : null;
}
function _v(e, t) {
  var n = _s;
  return (
    e.current.memoizedState.isDehydrated && (Jr(e, t).flags |= 256),
    (e = nl(e, t)),
    e !== 2 && ((t = ht), (ht = n), t !== null && bv(t)),
    e
  );
}
function bv(e) {
  ht === null ? (ht = e) : ht.push.apply(ht, e);
}
function fF(e) {
  for (var t = e; ; ) {
    if (t.flags & 16384) {
      var n = t.updateQueue;
      if (n !== null && ((n = n.stores), n !== null))
        for (var r = 0; r < n.length; r++) {
          var i = n[r],
            o = i.getSnapshot;
          i = i.value;
          try {
            if (!nn(o(), i)) return !1;
          } catch {
            return !1;
          }
        }
    }
    if (((n = t.child), t.subtreeFlags & 16384 && n !== null)) (n.return = t), (t = n);
    else {
      if (t === e) break;
      for (; t.sibling === null; ) {
        if (t.return === null || t.return === e) return !0;
        t = t.return;
      }
      (t.sibling.return = t.return), (t = t.sibling);
    }
  }
  return !0;
}
function pr(e, t) {
  for (
    t &= ~Gy, t &= ~Ol, e.suspendedLanes |= t, e.pingedLanes &= ~t, e = e.expirationTimes;
    0 < t;

  ) {
    var n = 31 - Jt(t),
      r = 1 << n;
    (e[n] = -1), (t &= ~r);
  }
}
function D1(e) {
  if (ae & 6) throw Error(z(327));
  Zi();
  var t = ju(e, 0);
  if (!(t & 1)) return yt(e, Ne()), null;
  var n = nl(e, t);
  if (e.tag !== 0 && n === 2) {
    var r = Wg(e);
    r !== 0 && ((t = r), (n = _v(e, r)));
  }
  if (n === 1) throw ((n = Hs), Jr(e, 0), pr(e, t), yt(e, Ne()), n);
  if (n === 6) throw Error(z(345));
  return (
    (e.finishedWork = e.current.alternate), (e.finishedLanes = t), zr(e, ht, Nn), yt(e, Ne()), null
  );
}
function Ky(e, t) {
  var n = ae;
  ae |= 1;
  try {
    return e(t);
  } finally {
    (ae = n), ae === 0 && ((lo = Ne() + 500), Nl && Or());
  }
}
function ui(e) {
  vr !== null && vr.tag === 0 && !(ae & 6) && Zi();
  var t = ae;
  ae |= 1;
  var n = jt.transition,
    r = ce;
  try {
    if (((jt.transition = null), (ce = 1), e)) return e();
  } finally {
    (ce = r), (jt.transition = n), (ae = t), !(ae & 6) && Or();
  }
}
function Yy() {
  (_t = Vi.current), ge(Vi);
}
function Jr(e, t) {
  (e.finishedWork = null), (e.finishedLanes = 0);
  var n = e.timeoutHandle;
  if ((n !== -1 && ((e.timeoutHandle = -1), $L(n)), Me !== null))
    for (n = Me.return; n !== null; ) {
      var r = n;
      switch ((Py(r), r.tag)) {
        case 1:
          (r = r.type.childContextTypes), r != null && Bu();
          break;
        case 3:
          ao(), ge(gt), ge(rt), jy();
          break;
        case 5:
          Fy(r);
          break;
        case 4:
          ao();
          break;
        case 13:
          ge(xe);
          break;
        case 19:
          ge(xe);
          break;
        case 10:
          Iy(r.type._context);
          break;
        case 22:
        case 23:
          Yy();
      }
      n = n.return;
    }
  if (
    ((Ue = e),
    (Me = e = Tr(e.current, null)),
    (Ke = _t = t),
    (Le = 0),
    (Hs = null),
    (Gy = Ol = ai = 0),
    (ht = _s = null),
    Wr !== null)
  ) {
    for (t = 0; t < Wr.length; t++)
      if (((n = Wr[t]), (r = n.interleaved), r !== null)) {
        n.interleaved = null;
        var i = r.next,
          o = n.pending;
        if (o !== null) {
          var s = o.next;
          (o.next = i), (r.next = s);
        }
        n.pending = r;
      }
    Wr = null;
  }
  return e;
}
function wP(e, t) {
  do {
    var n = Me;
    try {
      if ((My(), (gu.current = Qu), Zu)) {
        for (var r = be.memoizedState; r !== null; ) {
          var i = r.queue;
          i !== null && (i.pending = null), (r = r.next);
        }
        Zu = !1;
      }
      if (
        ((si = 0),
        (ze = Oe = be = null),
        (ws = !1),
        (zs = 0),
        (Hy.current = null),
        n === null || n.return === null)
      ) {
        (Le = 1), (Hs = t), (Me = null);
        break;
      }
      e: {
        var o = e,
          s = n.return,
          a = n,
          u = t;
        if (
          ((t = Ke),
          (a.flags |= 32768),
          u !== null && typeof u == "object" && typeof u.then == "function")
        ) {
          var l = u,
            c = a,
            f = c.tag;
          if (!(c.mode & 1) && (f === 0 || f === 11 || f === 15)) {
            var d = c.alternate;
            d
              ? ((c.updateQueue = d.updateQueue),
                (c.memoizedState = d.memoizedState),
                (c.lanes = d.lanes))
              : ((c.updateQueue = null), (c.memoizedState = null));
          }
          var h = _1(s);
          if (h !== null) {
            (h.flags &= -257), b1(h, s, a, o, t), h.mode & 1 && x1(o, l, t), (t = h), (u = l);
            var v = t.updateQueue;
            if (v === null) {
              var p = new Set();
              p.add(u), (t.updateQueue = p);
            } else v.add(u);
            break e;
          } else {
            if (!(t & 1)) {
              x1(o, l, t), Xy();
              break e;
            }
            u = Error(z(426));
          }
        } else if (ye && a.mode & 1) {
          var y = _1(s);
          if (y !== null) {
            !(y.flags & 65536) && (y.flags |= 256), b1(y, s, a, o, t), Ay(uo(u, a));
            break e;
          }
        }
        (o = u = uo(u, a)), Le !== 4 && (Le = 2), _s === null ? (_s = [o]) : _s.push(o), (o = s);
        do {
          switch (o.tag) {
            case 3:
              (o.flags |= 65536), (t &= -t), (o.lanes |= t);
              var m = nP(o, u, t);
              p1(o, m);
              break e;
            case 1:
              a = u;
              var g = o.type,
                w = o.stateNode;
              if (
                !(o.flags & 128) &&
                (typeof g.getDerivedStateFromError == "function" ||
                  (w !== null &&
                    typeof w.componentDidCatch == "function" &&
                    (Er === null || !Er.has(w))))
              ) {
                (o.flags |= 65536), (t &= -t), (o.lanes |= t);
                var x = rP(o, a, t);
                p1(o, x);
                break e;
              }
          }
          o = o.return;
        } while (o !== null);
      }
      bP(n);
    } catch (b) {
      (t = b), Me === n && n !== null && (Me = n = n.return);
      continue;
    }
    break;
  } while (!0);
}
function xP() {
  var e = Ju.current;
  return (Ju.current = Qu), e === null ? Qu : e;
}
function Xy() {
  (Le === 0 || Le === 3 || Le === 2) && (Le = 4),
    Ue === null || (!(ai & 268435455) && !(Ol & 268435455)) || pr(Ue, Ke);
}
function nl(e, t) {
  var n = ae;
  ae |= 2;
  var r = xP();
  (Ue !== e || Ke !== t) && ((Nn = null), Jr(e, t));
  do
    try {
      dF();
      break;
    } catch (i) {
      wP(e, i);
    }
  while (!0);
  if ((My(), (ae = n), (Ju.current = r), Me !== null)) throw Error(z(261));
  return (Ue = null), (Ke = 0), Le;
}
function dF() {
  for (; Me !== null; ) _P(Me);
}
function hF() {
  for (; Me !== null && !jO(); ) _P(Me);
}
function _P(e) {
  var t = EP(e.alternate, e, _t);
  (e.memoizedProps = e.pendingProps), t === null ? bP(e) : (Me = t), (Hy.current = null);
}
function bP(e) {
  var t = e;
  do {
    var n = t.alternate;
    if (((e = t.return), t.flags & 32768)) {
      if (((n = sF(n, t)), n !== null)) {
        (n.flags &= 32767), (Me = n);
        return;
      }
      if (e !== null) (e.flags |= 32768), (e.subtreeFlags = 0), (e.deletions = null);
      else {
        (Le = 6), (Me = null);
        return;
      }
    } else if (((n = oF(n, t, _t)), n !== null)) {
      Me = n;
      return;
    }
    if (((t = t.sibling), t !== null)) {
      Me = t;
      return;
    }
    Me = t = e;
  } while (t !== null);
  Le === 0 && (Le = 5);
}
function zr(e, t, n) {
  var r = ce,
    i = jt.transition;
  try {
    (jt.transition = null), (ce = 1), pF(e, t, n, r);
  } finally {
    (jt.transition = i), (ce = r);
  }
  return null;
}
function pF(e, t, n, r) {
  do Zi();
  while (vr !== null);
  if (ae & 6) throw Error(z(327));
  n = e.finishedWork;
  var i = e.finishedLanes;
  if (n === null) return null;
  if (((e.finishedWork = null), (e.finishedLanes = 0), n === e.current)) throw Error(z(177));
  (e.callbackNode = null), (e.callbackPriority = 0);
  var o = n.lanes | n.childLanes;
  if (
    (KO(e, o),
    e === Ue && ((Me = Ue = null), (Ke = 0)),
    (!(n.subtreeFlags & 2064) && !(n.flags & 2064)) ||
      Ba ||
      ((Ba = !0),
      CP(Fu, function () {
        return Zi(), null;
      })),
    (o = (n.flags & 15990) !== 0),
    n.subtreeFlags & 15990 || o)
  ) {
    (o = jt.transition), (jt.transition = null);
    var s = ce;
    ce = 1;
    var a = ae;
    (ae |= 4),
      (Hy.current = null),
      uF(e, n),
      gP(n, e),
      DL(Jg),
      (Vu = !!Qg),
      (Jg = Qg = null),
      (e.current = n),
      lF(n),
      VO(),
      (ae = a),
      (ce = s),
      (jt.transition = o);
  } else e.current = n;
  if (
    (Ba && ((Ba = !1), (vr = e), (tl = i)),
    (o = e.pendingLanes),
    o === 0 && (Er = null),
    zO(n.stateNode),
    yt(e, Ne()),
    t !== null)
  )
    for (r = e.onRecoverableError, n = 0; n < t.length; n++)
      (i = t[n]), r(i.value, { componentStack: i.stack, digest: i.digest });
  if (el) throw ((el = !1), (e = wv), (wv = null), e);
  return (
    tl & 1 && e.tag !== 0 && Zi(),
    (o = e.pendingLanes),
    o & 1 ? (e === xv ? bs++ : ((bs = 0), (xv = e))) : (bs = 0),
    Or(),
    null
  );
}
function Zi() {
  if (vr !== null) {
    var e = nR(tl),
      t = jt.transition,
      n = ce;
    try {
      if (((jt.transition = null), (ce = 16 > e ? 16 : e), vr === null)) var r = !1;
      else {
        if (((e = vr), (vr = null), (tl = 0), ae & 6)) throw Error(z(331));
        var i = ae;
        for (ae |= 4, H = e.current; H !== null; ) {
          var o = H,
            s = o.child;
          if (H.flags & 16) {
            var a = o.deletions;
            if (a !== null) {
              for (var u = 0; u < a.length; u++) {
                var l = a[u];
                for (H = l; H !== null; ) {
                  var c = H;
                  switch (c.tag) {
                    case 0:
                    case 11:
                    case 15:
                      xs(8, c, o);
                  }
                  var f = c.child;
                  if (f !== null) (f.return = c), (H = f);
                  else
                    for (; H !== null; ) {
                      c = H;
                      var d = c.sibling,
                        h = c.return;
                      if ((hP(c), c === l)) {
                        H = null;
                        break;
                      }
                      if (d !== null) {
                        (d.return = h), (H = d);
                        break;
                      }
                      H = h;
                    }
                }
              }
              var v = o.alternate;
              if (v !== null) {
                var p = v.child;
                if (p !== null) {
                  v.child = null;
                  do {
                    var y = p.sibling;
                    (p.sibling = null), (p = y);
                  } while (p !== null);
                }
              }
              H = o;
            }
          }
          if (o.subtreeFlags & 2064 && s !== null) (s.return = o), (H = s);
          else
            e: for (; H !== null; ) {
              if (((o = H), o.flags & 2048))
                switch (o.tag) {
                  case 0:
                  case 11:
                  case 15:
                    xs(9, o, o.return);
                }
              var m = o.sibling;
              if (m !== null) {
                (m.return = o.return), (H = m);
                break e;
              }
              H = o.return;
            }
        }
        var g = e.current;
        for (H = g; H !== null; ) {
          s = H;
          var w = s.child;
          if (s.subtreeFlags & 2064 && w !== null) (w.return = s), (H = w);
          else
            e: for (s = g; H !== null; ) {
              if (((a = H), a.flags & 2048))
                try {
                  switch (a.tag) {
                    case 0:
                    case 11:
                    case 15:
                      Dl(9, a);
                  }
                } catch (b) {
                  Te(a, a.return, b);
                }
              if (a === s) {
                H = null;
                break e;
              }
              var x = a.sibling;
              if (x !== null) {
                (x.return = a.return), (H = x);
                break e;
              }
              H = a.return;
            }
        }
        if (((ae = i), Or(), vn && typeof vn.onPostCommitFiberRoot == "function"))
          try {
            vn.onPostCommitFiberRoot(Tl, e);
          } catch {}
        r = !0;
      }
      return r;
    } finally {
      (ce = n), (jt.transition = t);
    }
  }
  return !1;
}
function O1(e, t, n) {
  (t = uo(n, t)),
    (t = nP(e, t, 1)),
    (e = Sr(e, t, 1)),
    (t = at()),
    e !== null && (sa(e, 1, t), yt(e, t));
}
function Te(e, t, n) {
  if (e.tag === 3) O1(e, e, n);
  else
    for (; t !== null; ) {
      if (t.tag === 3) {
        O1(t, e, n);
        break;
      } else if (t.tag === 1) {
        var r = t.stateNode;
        if (
          typeof t.type.getDerivedStateFromError == "function" ||
          (typeof r.componentDidCatch == "function" && (Er === null || !Er.has(r)))
        ) {
          (e = uo(n, e)),
            (e = rP(t, e, 1)),
            (t = Sr(t, e, 1)),
            (e = at()),
            t !== null && (sa(t, 1, e), yt(t, e));
          break;
        }
      }
      t = t.return;
    }
}
function mF(e, t, n) {
  var r = e.pingCache;
  r !== null && r.delete(t),
    (t = at()),
    (e.pingedLanes |= e.suspendedLanes & n),
    Ue === e &&
      (Ke & n) === n &&
      (Le === 4 || (Le === 3 && (Ke & 130023424) === Ke && 500 > Ne() - Wy) ? Jr(e, 0) : (Gy |= n)),
    yt(e, t);
}
function SP(e, t) {
  t === 0 && (e.mode & 1 ? ((t = Ia), (Ia <<= 1), !(Ia & 130023424) && (Ia = 4194304)) : (t = 1));
  var n = at();
  (e = Hn(e, t)), e !== null && (sa(e, t, n), yt(e, n));
}
function gF(e) {
  var t = e.memoizedState,
    n = 0;
  t !== null && (n = t.retryLane), SP(e, n);
}
function vF(e, t) {
  var n = 0;
  switch (e.tag) {
    case 13:
      var r = e.stateNode,
        i = e.memoizedState;
      i !== null && (n = i.retryLane);
      break;
    case 19:
      r = e.stateNode;
      break;
    default:
      throw Error(z(314));
  }
  r !== null && r.delete(t), SP(e, n);
}
var EP;
EP = function (e, t, n) {
  if (e !== null)
    if (e.memoizedProps !== t.pendingProps || gt.current) pt = !0;
    else {
      if (!(e.lanes & n) && !(t.flags & 128)) return (pt = !1), iF(e, t, n);
      pt = !!(e.flags & 131072);
    }
  else (pt = !1), ye && t.flags & 1048576 && RR(t, Gu, t.index);
  switch (((t.lanes = 0), t.tag)) {
    case 2:
      var r = t.type;
      yu(e, t), (e = t.pendingProps);
      var i = io(t, rt.current);
      Xi(t, n), (i = qy(null, t, r, e, i, n));
      var o = $y();
      return (
        (t.flags |= 1),
        typeof i == "object" && i !== null && typeof i.render == "function" && i.$$typeof === void 0
          ? ((t.tag = 1),
            (t.memoizedState = null),
            (t.updateQueue = null),
            vt(r) ? ((o = !0), Uu(t)) : (o = !1),
            (t.memoizedState = i.state !== null && i.state !== void 0 ? i.state : null),
            Oy(t),
            (i.updater = Il),
            (t.stateNode = i),
            (i._reactInternals = t),
            uv(t, r, e, n),
            (t = fv(null, t, r, !0, o, n)))
          : ((t.tag = 0), ye && o && Ry(t), st(null, t, i, n), (t = t.child)),
        t
      );
    case 16:
      r = t.elementType;
      e: {
        switch (
          (yu(e, t),
          (e = t.pendingProps),
          (i = r._init),
          (r = i(r._payload)),
          (t.type = r),
          (i = t.tag = wF(r)),
          (e = Kt(r, e)),
          i)
        ) {
          case 0:
            t = cv(null, t, r, e, n);
            break e;
          case 1:
            t = C1(null, t, r, e, n);
            break e;
          case 11:
            t = S1(null, t, r, e, n);
            break e;
          case 14:
            t = E1(null, t, r, Kt(r.type, e), n);
            break e;
        }
        throw Error(z(306, r, ""));
      }
      return t;
    case 0:
      return (
        (r = t.type),
        (i = t.pendingProps),
        (i = t.elementType === r ? i : Kt(r, i)),
        cv(e, t, r, i, n)
      );
    case 1:
      return (
        (r = t.type),
        (i = t.pendingProps),
        (i = t.elementType === r ? i : Kt(r, i)),
        C1(e, t, r, i, n)
      );
    case 3:
      e: {
        if ((aP(t), e === null)) throw Error(z(387));
        (r = t.pendingProps), (o = t.memoizedState), (i = o.element), DR(e, t), Yu(t, r, null, n);
        var s = t.memoizedState;
        if (((r = s.element), o.isDehydrated))
          if (
            ((o = {
              element: r,
              isDehydrated: !1,
              cache: s.cache,
              pendingSuspenseBoundaries: s.pendingSuspenseBoundaries,
              transitions: s.transitions,
            }),
            (t.updateQueue.baseState = o),
            (t.memoizedState = o),
            t.flags & 256)
          ) {
            (i = uo(Error(z(423)), t)), (t = T1(e, t, r, n, i));
            break e;
          } else if (r !== i) {
            (i = uo(Error(z(424)), t)), (t = T1(e, t, r, n, i));
            break e;
          } else
            for (
              St = br(t.stateNode.containerInfo.firstChild),
                Et = t,
                ye = !0,
                Zt = null,
                n = MR(t, null, r, n),
                t.child = n;
              n;

            )
              (n.flags = (n.flags & -3) | 4096), (n = n.sibling);
        else {
          if ((oo(), r === i)) {
            t = Gn(e, t, n);
            break e;
          }
          st(e, t, r, n);
        }
        t = t.child;
      }
      return t;
    case 5:
      return (
        OR(t),
        e === null && ov(t),
        (r = t.type),
        (i = t.pendingProps),
        (o = e !== null ? e.memoizedProps : null),
        (s = i.children),
        ev(r, i) ? (s = null) : o !== null && ev(r, o) && (t.flags |= 32),
        sP(e, t),
        st(e, t, s, n),
        t.child
      );
    case 6:
      return e === null && ov(t), null;
    case 13:
      return uP(e, t, n);
    case 4:
      return (
        Ly(t, t.stateNode.containerInfo),
        (r = t.pendingProps),
        e === null ? (t.child = so(t, null, r, n)) : st(e, t, r, n),
        t.child
      );
    case 11:
      return (
        (r = t.type),
        (i = t.pendingProps),
        (i = t.elementType === r ? i : Kt(r, i)),
        S1(e, t, r, i, n)
      );
    case 7:
      return st(e, t, t.pendingProps, n), t.child;
    case 8:
      return st(e, t, t.pendingProps.children, n), t.child;
    case 12:
      return st(e, t, t.pendingProps.children, n), t.child;
    case 10:
      e: {
        if (
          ((r = t.type._context),
          (i = t.pendingProps),
          (o = t.memoizedProps),
          (s = i.value),
          he(Wu, r._currentValue),
          (r._currentValue = s),
          o !== null)
        )
          if (nn(o.value, s)) {
            if (o.children === i.children && !gt.current) {
              t = Gn(e, t, n);
              break e;
            }
          } else
            for (o = t.child, o !== null && (o.return = t); o !== null; ) {
              var a = o.dependencies;
              if (a !== null) {
                s = o.child;
                for (var u = a.firstContext; u !== null; ) {
                  if (u.context === r) {
                    if (o.tag === 1) {
                      (u = Vn(-1, n & -n)), (u.tag = 2);
                      var l = o.updateQueue;
                      if (l !== null) {
                        l = l.shared;
                        var c = l.pending;
                        c === null ? (u.next = u) : ((u.next = c.next), (c.next = u)),
                          (l.pending = u);
                      }
                    }
                    (o.lanes |= n),
                      (u = o.alternate),
                      u !== null && (u.lanes |= n),
                      sv(o.return, n, t),
                      (a.lanes |= n);
                    break;
                  }
                  u = u.next;
                }
              } else if (o.tag === 10) s = o.type === t.type ? null : o.child;
              else if (o.tag === 18) {
                if (((s = o.return), s === null)) throw Error(z(341));
                (s.lanes |= n),
                  (a = s.alternate),
                  a !== null && (a.lanes |= n),
                  sv(s, n, t),
                  (s = o.sibling);
              } else s = o.child;
              if (s !== null) s.return = o;
              else
                for (s = o; s !== null; ) {
                  if (s === t) {
                    s = null;
                    break;
                  }
                  if (((o = s.sibling), o !== null)) {
                    (o.return = s.return), (s = o);
                    break;
                  }
                  s = s.return;
                }
              o = s;
            }
        st(e, t, i.children, n), (t = t.child);
      }
      return t;
    case 9:
      return (
        (i = t.type),
        (r = t.pendingProps.children),
        Xi(t, n),
        (i = Vt(i)),
        (r = r(i)),
        (t.flags |= 1),
        st(e, t, r, n),
        t.child
      );
    case 14:
      return (r = t.type), (i = Kt(r, t.pendingProps)), (i = Kt(r.type, i)), E1(e, t, r, i, n);
    case 15:
      return iP(e, t, t.type, t.pendingProps, n);
    case 17:
      return (
        (r = t.type),
        (i = t.pendingProps),
        (i = t.elementType === r ? i : Kt(r, i)),
        yu(e, t),
        (t.tag = 1),
        vt(r) ? ((e = !0), Uu(t)) : (e = !1),
        Xi(t, n),
        tP(t, r, i),
        uv(t, r, i, n),
        fv(null, t, r, !0, e, n)
      );
    case 19:
      return lP(e, t, n);
    case 22:
      return oP(e, t, n);
  }
  throw Error(z(156, t.tag));
};
function CP(e, t) {
  return Qk(e, t);
}
function yF(e, t, n, r) {
  (this.tag = e),
    (this.key = n),
    (this.sibling =
      this.child =
      this.return =
      this.stateNode =
      this.type =
      this.elementType =
        null),
    (this.index = 0),
    (this.ref = null),
    (this.pendingProps = t),
    (this.dependencies = this.memoizedState = this.updateQueue = this.memoizedProps = null),
    (this.mode = r),
    (this.subtreeFlags = this.flags = 0),
    (this.deletions = null),
    (this.childLanes = this.lanes = 0),
    (this.alternate = null);
}
function Lt(e, t, n, r) {
  return new yF(e, t, n, r);
}
function Zy(e) {
  return (e = e.prototype), !(!e || !e.isReactComponent);
}
function wF(e) {
  if (typeof e == "function") return Zy(e) ? 1 : 0;
  if (e != null) {
    if (((e = e.$$typeof), e === gy)) return 11;
    if (e === vy) return 14;
  }
  return 2;
}
function Tr(e, t) {
  var n = e.alternate;
  return (
    n === null
      ? ((n = Lt(e.tag, t, e.key, e.mode)),
        (n.elementType = e.elementType),
        (n.type = e.type),
        (n.stateNode = e.stateNode),
        (n.alternate = e),
        (e.alternate = n))
      : ((n.pendingProps = t),
        (n.type = e.type),
        (n.flags = 0),
        (n.subtreeFlags = 0),
        (n.deletions = null)),
    (n.flags = e.flags & 14680064),
    (n.childLanes = e.childLanes),
    (n.lanes = e.lanes),
    (n.child = e.child),
    (n.memoizedProps = e.memoizedProps),
    (n.memoizedState = e.memoizedState),
    (n.updateQueue = e.updateQueue),
    (t = e.dependencies),
    (n.dependencies = t === null ? null : { lanes: t.lanes, firstContext: t.firstContext }),
    (n.sibling = e.sibling),
    (n.index = e.index),
    (n.ref = e.ref),
    n
  );
}
function _u(e, t, n, r, i, o) {
  var s = 2;
  if (((r = e), typeof e == "function")) Zy(e) && (s = 1);
  else if (typeof e == "string") s = 5;
  else
    e: switch (e) {
      case Pi:
        return ei(n.children, i, o, t);
      case my:
        (s = 8), (i |= 8);
        break;
      case Mg:
        return (e = Lt(12, n, t, i | 2)), (e.elementType = Mg), (e.lanes = o), e;
      case Ig:
        return (e = Lt(13, n, t, i)), (e.elementType = Ig), (e.lanes = o), e;
      case Dg:
        return (e = Lt(19, n, t, i)), (e.elementType = Dg), (e.lanes = o), e;
      case Ok:
        return Ll(n, i, o, t);
      default:
        if (typeof e == "object" && e !== null)
          switch (e.$$typeof) {
            case Ik:
              s = 10;
              break e;
            case Dk:
              s = 9;
              break e;
            case gy:
              s = 11;
              break e;
            case vy:
              s = 14;
              break e;
            case lr:
              (s = 16), (r = null);
              break e;
          }
        throw Error(z(130, e == null ? e : typeof e, ""));
    }
  return (t = Lt(s, n, t, i)), (t.elementType = e), (t.type = r), (t.lanes = o), t;
}
function ei(e, t, n, r) {
  return (e = Lt(7, e, r, t)), (e.lanes = n), e;
}
function Ll(e, t, n, r) {
  return (
    (e = Lt(22, e, r, t)), (e.elementType = Ok), (e.lanes = n), (e.stateNode = { isHidden: !1 }), e
  );
}
function tf(e, t, n) {
  return (e = Lt(6, e, null, t)), (e.lanes = n), e;
}
function nf(e, t, n) {
  return (
    (t = Lt(4, e.children !== null ? e.children : [], e.key, t)),
    (t.lanes = n),
    (t.stateNode = {
      containerInfo: e.containerInfo,
      pendingChildren: null,
      implementation: e.implementation,
    }),
    t
  );
}
function xF(e, t, n, r, i) {
  (this.tag = t),
    (this.containerInfo = e),
    (this.finishedWork = this.pingCache = this.current = this.pendingChildren = null),
    (this.timeoutHandle = -1),
    (this.callbackNode = this.pendingContext = this.context = null),
    (this.callbackPriority = 0),
    (this.eventTimes = Lc(0)),
    (this.expirationTimes = Lc(-1)),
    (this.entangledLanes =
      this.finishedLanes =
      this.mutableReadLanes =
      this.expiredLanes =
      this.pingedLanes =
      this.suspendedLanes =
      this.pendingLanes =
        0),
    (this.entanglements = Lc(0)),
    (this.identifierPrefix = r),
    (this.onRecoverableError = i),
    (this.mutableSourceEagerHydrationData = null);
}
function Qy(e, t, n, r, i, o, s, a, u) {
  return (
    (e = new xF(e, t, n, a, u)),
    t === 1 ? ((t = 1), o === !0 && (t |= 8)) : (t = 0),
    (o = Lt(3, null, null, t)),
    (e.current = o),
    (o.stateNode = e),
    (o.memoizedState = {
      element: r,
      isDehydrated: n,
      cache: null,
      transitions: null,
      pendingSuspenseBoundaries: null,
    }),
    Oy(o),
    e
  );
}
function _F(e, t, n) {
  var r = 3 < arguments.length && arguments[3] !== void 0 ? arguments[3] : null;
  return {
    $$typeof: Ri,
    key: r == null ? null : "" + r,
    children: e,
    containerInfo: t,
    implementation: n,
  };
}
function TP(e) {
  if (!e) return Ar;
  e = e._reactInternals;
  e: {
    if (hi(e) !== e || e.tag !== 1) throw Error(z(170));
    var t = e;
    do {
      switch (t.tag) {
        case 3:
          t = t.stateNode.context;
          break e;
        case 1:
          if (vt(t.type)) {
            t = t.stateNode.__reactInternalMemoizedMergedChildContext;
            break e;
          }
      }
      t = t.return;
    } while (t !== null);
    throw Error(z(171));
  }
  if (e.tag === 1) {
    var n = e.type;
    if (vt(n)) return TR(e, n, t);
  }
  return t;
}
function kP(e, t, n, r, i, o, s, a, u) {
  return (
    (e = Qy(n, r, !0, e, i, o, s, a, u)),
    (e.context = TP(null)),
    (n = e.current),
    (r = at()),
    (i = Cr(n)),
    (o = Vn(r, i)),
    (o.callback = t ?? null),
    Sr(n, o, i),
    (e.current.lanes = i),
    sa(e, i, r),
    yt(e, r),
    e
  );
}
function Fl(e, t, n, r) {
  var i = t.current,
    o = at(),
    s = Cr(i);
  return (
    (n = TP(n)),
    t.context === null ? (t.context = n) : (t.pendingContext = n),
    (t = Vn(o, s)),
    (t.payload = { element: e }),
    (r = r === void 0 ? null : r),
    r !== null && (t.callback = r),
    (e = Sr(i, t, s)),
    e !== null && (en(e, i, s, o), mu(e, i, s)),
    s
  );
}
function rl(e) {
  if (((e = e.current), !e.child)) return null;
  switch (e.child.tag) {
    case 5:
      return e.child.stateNode;
    default:
      return e.child.stateNode;
  }
}
function L1(e, t) {
  if (((e = e.memoizedState), e !== null && e.dehydrated !== null)) {
    var n = e.retryLane;
    e.retryLane = n !== 0 && n < t ? n : t;
  }
}
function Jy(e, t) {
  L1(e, t), (e = e.alternate) && L1(e, t);
}
function bF() {
  return null;
}
var RP =
  typeof reportError == "function"
    ? reportError
    : function (e) {
        console.error(e);
      };
function e0(e) {
  this._internalRoot = e;
}
jl.prototype.render = e0.prototype.render = function (e) {
  var t = this._internalRoot;
  if (t === null) throw Error(z(409));
  Fl(e, t, null, null);
};
jl.prototype.unmount = e0.prototype.unmount = function () {
  var e = this._internalRoot;
  if (e !== null) {
    this._internalRoot = null;
    var t = e.containerInfo;
    ui(function () {
      Fl(null, e, null, null);
    }),
      (t[Un] = null);
  }
};
function jl(e) {
  this._internalRoot = e;
}
jl.prototype.unstable_scheduleHydration = function (e) {
  if (e) {
    var t = oR();
    e = { blockedOn: null, target: e, priority: t };
    for (var n = 0; n < hr.length && t !== 0 && t < hr[n].priority; n++);
    hr.splice(n, 0, e), n === 0 && aR(e);
  }
};
function t0(e) {
  return !(!e || (e.nodeType !== 1 && e.nodeType !== 9 && e.nodeType !== 11));
}
function Vl(e) {
  return !(
    !e ||
    (e.nodeType !== 1 &&
      e.nodeType !== 9 &&
      e.nodeType !== 11 &&
      (e.nodeType !== 8 || e.nodeValue !== " react-mount-point-unstable "))
  );
}
function F1() {}
function SF(e, t, n, r, i) {
  if (i) {
    if (typeof r == "function") {
      var o = r;
      r = function () {
        var l = rl(s);
        o.call(l);
      };
    }
    var s = kP(t, r, e, 0, null, !1, !1, "", F1);
    return (
      (e._reactRootContainer = s),
      (e[Un] = s.current),
      Fs(e.nodeType === 8 ? e.parentNode : e),
      ui(),
      s
    );
  }
  for (; (i = e.lastChild); ) e.removeChild(i);
  if (typeof r == "function") {
    var a = r;
    r = function () {
      var l = rl(u);
      a.call(l);
    };
  }
  var u = Qy(e, 0, !1, null, null, !1, !1, "", F1);
  return (
    (e._reactRootContainer = u),
    (e[Un] = u.current),
    Fs(e.nodeType === 8 ? e.parentNode : e),
    ui(function () {
      Fl(t, u, n, r);
    }),
    u
  );
}
function ql(e, t, n, r, i) {
  var o = n._reactRootContainer;
  if (o) {
    var s = o;
    if (typeof i == "function") {
      var a = i;
      i = function () {
        var u = rl(s);
        a.call(u);
      };
    }
    Fl(t, s, e, i);
  } else s = SF(n, t, e, i, r);
  return rl(s);
}
rR = function (e) {
  switch (e.tag) {
    case 3:
      var t = e.stateNode;
      if (t.current.memoizedState.isDehydrated) {
        var n = es(t.pendingLanes);
        n !== 0 && (xy(t, n | 1), yt(t, Ne()), !(ae & 6) && ((lo = Ne() + 500), Or()));
      }
      break;
    case 13:
      ui(function () {
        var r = Hn(e, 1);
        if (r !== null) {
          var i = at();
          en(r, e, 1, i);
        }
      }),
        Jy(e, 1);
  }
};
_y = function (e) {
  if (e.tag === 13) {
    var t = Hn(e, 134217728);
    if (t !== null) {
      var n = at();
      en(t, e, 134217728, n);
    }
    Jy(e, 134217728);
  }
};
iR = function (e) {
  if (e.tag === 13) {
    var t = Cr(e),
      n = Hn(e, t);
    if (n !== null) {
      var r = at();
      en(n, e, t, r);
    }
    Jy(e, t);
  }
};
oR = function () {
  return ce;
};
sR = function (e, t) {
  var n = ce;
  try {
    return (ce = e), t();
  } finally {
    ce = n;
  }
};
Ug = function (e, t, n) {
  switch (t) {
    case "input":
      if ((Fg(e, n), (t = n.name), n.type === "radio" && t != null)) {
        for (n = e; n.parentNode; ) n = n.parentNode;
        for (
          n = n.querySelectorAll("input[name=" + JSON.stringify("" + t) + '][type="radio"]'), t = 0;
          t < n.length;
          t++
        ) {
          var r = n[t];
          if (r !== e && r.form === e.form) {
            var i = Al(r);
            if (!i) throw Error(z(90));
            Fk(r), Fg(r, i);
          }
        }
      }
      break;
    case "textarea":
      Vk(e, n);
      break;
    case "select":
      (t = n.value), t != null && Gi(e, !!n.multiple, t, !1);
  }
};
Gk = Ky;
Wk = ui;
var EF = { usingClientEntryPoint: !1, Events: [ua, Ii, Al, Uk, Hk, Ky] },
  Bo = {
    findFiberByHostInstance: Gr,
    bundleType: 0,
    version: "18.3.1",
    rendererPackageName: "react-dom",
  },
  CF = {
    bundleType: Bo.bundleType,
    version: Bo.version,
    rendererPackageName: Bo.rendererPackageName,
    rendererConfig: Bo.rendererConfig,
    overrideHookState: null,
    overrideHookStateDeletePath: null,
    overrideHookStateRenamePath: null,
    overrideProps: null,
    overridePropsDeletePath: null,
    overridePropsRenamePath: null,
    setErrorHandler: null,
    setSuspenseHandler: null,
    scheduleUpdate: null,
    currentDispatcherRef: Qn.ReactCurrentDispatcher,
    findHostInstanceByFiber: function (e) {
      return (e = Xk(e)), e === null ? null : e.stateNode;
    },
    findFiberByHostInstance: Bo.findFiberByHostInstance || bF,
    findHostInstancesForRefresh: null,
    scheduleRefresh: null,
    scheduleRoot: null,
    setRefreshHandler: null,
    getCurrentFiber: null,
    reconcilerVersion: "18.3.1-next-f1338f8080-20240426",
  };
if (typeof __REACT_DEVTOOLS_GLOBAL_HOOK__ < "u") {
  var Ua = __REACT_DEVTOOLS_GLOBAL_HOOK__;
  if (!Ua.isDisabled && Ua.supportsFiber)
    try {
      (Tl = Ua.inject(CF)), (vn = Ua);
    } catch {}
}
Pt.__SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED = EF;
Pt.createPortal = function (e, t) {
  var n = 2 < arguments.length && arguments[2] !== void 0 ? arguments[2] : null;
  if (!t0(t)) throw Error(z(200));
  return _F(e, t, null, n);
};
Pt.createRoot = function (e, t) {
  if (!t0(e)) throw Error(z(299));
  var n = !1,
    r = "",
    i = RP;
  return (
    t != null &&
      (t.unstable_strictMode === !0 && (n = !0),
      t.identifierPrefix !== void 0 && (r = t.identifierPrefix),
      t.onRecoverableError !== void 0 && (i = t.onRecoverableError)),
    (t = Qy(e, 1, !1, null, null, n, !1, r, i)),
    (e[Un] = t.current),
    Fs(e.nodeType === 8 ? e.parentNode : e),
    new e0(t)
  );
};
Pt.findDOMNode = function (e) {
  if (e == null) return null;
  if (e.nodeType === 1) return e;
  var t = e._reactInternals;
  if (t === void 0)
    throw typeof e.render == "function"
      ? Error(z(188))
      : ((e = Object.keys(e).join(",")), Error(z(268, e)));
  return (e = Xk(t)), (e = e === null ? null : e.stateNode), e;
};
Pt.flushSync = function (e) {
  return ui(e);
};
Pt.hydrate = function (e, t, n) {
  if (!Vl(t)) throw Error(z(200));
  return ql(null, e, t, !0, n);
};
Pt.hydrateRoot = function (e, t, n) {
  if (!t0(e)) throw Error(z(405));
  var r = (n != null && n.hydratedSources) || null,
    i = !1,
    o = "",
    s = RP;
  if (
    (n != null &&
      (n.unstable_strictMode === !0 && (i = !0),
      n.identifierPrefix !== void 0 && (o = n.identifierPrefix),
      n.onRecoverableError !== void 0 && (s = n.onRecoverableError)),
    (t = kP(t, null, e, 1, n ?? null, i, !1, o, s)),
    (e[Un] = t.current),
    Fs(e),
    r)
  )
    for (e = 0; e < r.length; e++)
      (n = r[e]),
        (i = n._getVersion),
        (i = i(n._source)),
        t.mutableSourceEagerHydrationData == null
          ? (t.mutableSourceEagerHydrationData = [n, i])
          : t.mutableSourceEagerHydrationData.push(n, i);
  return new jl(t);
};
Pt.render = function (e, t, n) {
  if (!Vl(t)) throw Error(z(200));
  return ql(null, e, t, !1, n);
};
Pt.unmountComponentAtNode = function (e) {
  if (!Vl(e)) throw Error(z(40));
  return e._reactRootContainer
    ? (ui(function () {
        ql(null, null, e, !1, function () {
          (e._reactRootContainer = null), (e[Un] = null);
        });
      }),
      !0)
    : !1;
};
Pt.unstable_batchedUpdates = Ky;
Pt.unstable_renderSubtreeIntoContainer = function (e, t, n, r) {
  if (!Vl(n)) throw Error(z(200));
  if (e == null || e._reactInternals === void 0) throw Error(z(38));
  return ql(e, t, n, !1, r);
};
Pt.version = "18.3.1-next-f1338f8080-20240426";
function PP() {
  if (
    !(
      typeof __REACT_DEVTOOLS_GLOBAL_HOOK__ > "u" ||
      typeof __REACT_DEVTOOLS_GLOBAL_HOOK__.checkDCE != "function"
    )
  )
    try {
      __REACT_DEVTOOLS_GLOBAL_HOOK__.checkDCE(PP);
    } catch (e) {
      console.error(e);
    }
}
PP(), (Pk.exports = Pt);
var $l = Pk.exports;
const TF = ay($l);
var j1 = $l;
(Ag.createRoot = j1.createRoot), (Ag.hydrateRoot = j1.hydrateRoot);
const kF = {},
  V1 = (e) => {
    let t;
    const n = new Set(),
      r = (c, f) => {
        const d = typeof c == "function" ? c(t) : c;
        if (!Object.is(d, t)) {
          const h = t;
          (t = (f ?? (typeof d != "object" || d === null)) ? d : Object.assign({}, t, d)),
            n.forEach((v) => v(t, h));
        }
      },
      i = () => t,
      u = {
        setState: r,
        getState: i,
        getInitialState: () => l,
        subscribe: (c) => (n.add(c), () => n.delete(c)),
        destroy: () => {
          (kF ? "production" : void 0) !== "production" &&
            console.warn(
              "[DEPRECATED] The `destroy` method will be unsupported in a future version. Instead use unsubscribe function returned by subscribe. Everything will be garbage-collected if store is garbage-collected.",
            ),
            n.clear();
        },
      },
      l = (t = e(r, i, u));
    return u;
  },
  AP = (e) => (e ? V1(e) : V1);
var NP = { exports: {} },
  MP = {},
  IP = { exports: {} },
  DP = {};
/**
 * @license React
 * use-sync-external-store-shim.production.js
 *
 * Copyright (c) Meta Platforms, Inc. and affiliates.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */ var co = _;
function RF(e, t) {
  return (e === t && (e !== 0 || 1 / e === 1 / t)) || (e !== e && t !== t);
}
var PF = typeof Object.is == "function" ? Object.is : RF,
  AF = co.useState,
  NF = co.useEffect,
  MF = co.useLayoutEffect,
  IF = co.useDebugValue;
function DF(e, t) {
  var n = t(),
    r = AF({ inst: { value: n, getSnapshot: t } }),
    i = r[0].inst,
    o = r[1];
  return (
    MF(
      function () {
        (i.value = n), (i.getSnapshot = t), rf(i) && o({ inst: i });
      },
      [e, n, t],
    ),
    NF(
      function () {
        return (
          rf(i) && o({ inst: i }),
          e(function () {
            rf(i) && o({ inst: i });
          })
        );
      },
      [e],
    ),
    IF(n),
    n
  );
}
function rf(e) {
  var t = e.getSnapshot;
  e = e.value;
  try {
    var n = t();
    return !PF(e, n);
  } catch {
    return !0;
  }
}
function OF(e, t) {
  return t();
}
var LF =
  typeof window > "u" || typeof window.document > "u" || typeof window.document.createElement > "u"
    ? OF
    : DF;
DP.useSyncExternalStore = co.useSyncExternalStore !== void 0 ? co.useSyncExternalStore : LF;
IP.exports = DP;
var FF = IP.exports;
/**
 * @license React
 * use-sync-external-store-shim/with-selector.production.js
 *
 * Copyright (c) Meta Platforms, Inc. and affiliates.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */ var zl = _,
  jF = FF;
function VF(e, t) {
  return (e === t && (e !== 0 || 1 / e === 1 / t)) || (e !== e && t !== t);
}
var qF = typeof Object.is == "function" ? Object.is : VF,
  $F = jF.useSyncExternalStore,
  zF = zl.useRef,
  BF = zl.useEffect,
  UF = zl.useMemo,
  HF = zl.useDebugValue;
MP.useSyncExternalStoreWithSelector = function (e, t, n, r, i) {
  var o = zF(null);
  if (o.current === null) {
    var s = { hasValue: !1, value: null };
    o.current = s;
  } else s = o.current;
  o = UF(
    function () {
      function u(h) {
        if (!l) {
          if (((l = !0), (c = h), (h = r(h)), i !== void 0 && s.hasValue)) {
            var v = s.value;
            if (i(v, h)) return (f = v);
          }
          return (f = h);
        }
        if (((v = f), qF(c, h))) return v;
        var p = r(h);
        return i !== void 0 && i(v, p) ? ((c = h), v) : ((c = h), (f = p));
      }
      var l = !1,
        c,
        f,
        d = n === void 0 ? null : n;
      return [
        function () {
          return u(t());
        },
        d === null
          ? void 0
          : function () {
              return u(d());
            },
      ];
    },
    [t, n, r, i],
  );
  var a = $F(e, o[0], o[1]);
  return (
    BF(
      function () {
        (s.hasValue = !0), (s.value = a);
      },
      [a],
    ),
    HF(a),
    a
  );
};
NP.exports = MP;
var GF = NP.exports;
const OP = ay(GF),
  LP = {},
  { useDebugValue: WF } = L,
  { useSyncExternalStoreWithSelector: KF } = OP;
let q1 = !1;
const YF = (e) => e;
function XF(e, t = YF, n) {
  (LP ? "production" : void 0) !== "production" &&
    n &&
    !q1 &&
    (console.warn(
      "[DEPRECATED] Use `createWithEqualityFn` instead of `create` or use `useStoreWithEqualityFn` instead of `useStore`. They can be imported from 'zustand/traditional'. https://github.com/pmndrs/zustand/discussions/1937",
    ),
    (q1 = !0));
  const r = KF(e.subscribe, e.getState, e.getServerState || e.getInitialState, t, n);
  return WF(r), r;
}
const $1 = (e) => {
    (LP ? "production" : void 0) !== "production" &&
      typeof e != "function" &&
      console.warn(
        "[DEPRECATED] Passing a vanilla store will be unsupported in a future version. Instead use `import { useStore } from 'zustand'`.",
      );
    const t = typeof e == "function" ? AP(e) : e,
      n = (r, i) => XF(t, r, i);
    return Object.assign(n, t), n;
  },
  ZF = (e) => (e ? $1(e) : $1),
  Bl = ZF((e, t) => ({
    ws: null,
    isConnected: !1,
    machines: {},
    connect: () => {
      if (t().ws) return;
      const n = new WebSocket("ws://127.0.0.1:8008/ws");
      (n.onopen = () => {
        console.log("Inspector WebSocket connected"), e({ isConnected: !0, ws: n });
      }),
        (n.onclose = () => {
          console.log("Inspector WebSocket disconnected. Retrying in 3 seconds..."),
            e({ isConnected: !1, ws: null }),
            setTimeout(() => t().connect(), 3e3);
        }),
        (n.onerror = (r) => {
          console.error("WebSocket Error:", r);
        }),
        (n.onmessage = (r) => {
          try {
            const i = JSON.parse(r.data),
              {
                addMachine: o,
                updateMachineTransition: s,
                addService: a,
                removeService: u,
                addLog: l,
              } = t();
            switch (i.type) {
              case "machine_registered":
                o(i.payload);
                break;
              case "transition":
                s(i.payload);
                break;
              case "service_invoked":
                a(i.payload);
                break;
              case "service_stopped":
                u(i.payload);
                break;
              default:
                t().machines[i.machine_id] &&
                  l(i.machine_id, { type: i.type, payload: i.payload, ...i });
                break;
            }
          } catch (i) {
            console.error("Failed to parse WebSocket message:", r.data, i);
          }
        }),
        e({ ws: n });
    },
    sendCommand: (n, r = {}) => {
      const i = t().ws;
      i && i.readyState === WebSocket.OPEN
        ? i.send(JSON.stringify({ command: n, ...r }))
        : console.warn("Could not send command, WebSocket is not open.", {
            command: n,
            payload: r,
          });
    },
    addMachine: (n) =>
      e((r) => ({
        machines: {
          ...r.machines,
          [n.machine_id]: {
            id: n.machine_id,
            definition: n.definition,
            currentStateIds: n.initial_state_ids,
            context: n.initial_context,
            logs: [{ type: "machine_registered", payload: n }],
            services: {},
            lastTransition: null,
          },
        },
      })),
    updateMachineTransition: (n) =>
      e((r) => {
        const i = r.machines[n.machine_id];
        if (!i) return r;
        const o = i.currentStateIds.length > 0 ? i.currentStateIds[0] : "",
          s = n.to_state_ids.length > 0 ? n.to_state_ids[0] : "";
        return {
          machines: {
            ...r.machines,
            [n.machine_id]: {
              ...i,
              currentStateIds: n.to_state_ids,
              context: n.full_context,
              lastTransition: { sourceId: o, targetId: s, event: n.event },
              logs: [...i.logs, { type: "transition", payload: n }],
            },
          },
        };
      }),
    clearLastTransition: (n) =>
      e((r) =>
        r.machines[n]
          ? { machines: { ...r.machines, [n]: { ...r.machines[n], lastTransition: null } } }
          : r,
      ),
    addService: (n) =>
      e((r) => {
        const i = r.machines[n.machine_id];
        return i
          ? {
              machines: {
                ...r.machines,
                [n.machine_id]: {
                  ...i,
                  services: { ...i.services, [n.id]: { src: n.service, status: "running" } },
                  logs: [...i.logs, { type: "service_invoked", payload: n }],
                },
              },
            }
          : r;
      }),
    removeService: (n) =>
      e((r) => {
        const i = r.machines[n.machine_id];
        if (!i) return r;
        const o = { ...i.services };
        return (
          delete o[n.id], { machines: { ...r.machines, [n.machine_id]: { ...i, services: o } } }
        );
      }),
    addLog: (n, r) =>
      e((i) => {
        const o = i.machines[n];
        return o ? { machines: { ...i.machines, [n]: { ...o, logs: [...o.logs, r] } } } : i;
      }),
  })),
  QF = () => {
    const e = Bl((t) => t.connect);
    _.useEffect(() => {
      e();
    }, [e]);
  };
function Ze(e) {
  if (typeof e == "string" || typeof e == "number") return "" + e;
  let t = "";
  if (Array.isArray(e))
    for (let n = 0, r; n < e.length; n++) (r = Ze(e[n])) !== "" && (t += (t && " ") + r);
  else for (let n in e) e[n] && (t += (t && " ") + n);
  return t;
}
const { useDebugValue: JF } = L,
  { useSyncExternalStoreWithSelector: e3 } = OP,
  t3 = (e) => e;
function FP(e, t = t3, n) {
  const r = e3(e.subscribe, e.getState, e.getServerState || e.getInitialState, t, n);
  return JF(r), r;
}
const z1 = (e, t) => {
    const n = AP(e),
      r = (i, o = t) => FP(n, i, o);
    return Object.assign(r, n), r;
  },
  n3 = (e, t) => (e ? z1(e, t) : z1);
function He(e, t) {
  if (Object.is(e, t)) return !0;
  if (typeof e != "object" || e === null || typeof t != "object" || t === null) return !1;
  if (e instanceof Map && t instanceof Map) {
    if (e.size !== t.size) return !1;
    for (const [r, i] of e) if (!Object.is(i, t.get(r))) return !1;
    return !0;
  }
  if (e instanceof Set && t instanceof Set) {
    if (e.size !== t.size) return !1;
    for (const r of e) if (!t.has(r)) return !1;
    return !0;
  }
  const n = Object.keys(e);
  if (n.length !== Object.keys(t).length) return !1;
  for (const r of n)
    if (!Object.prototype.hasOwnProperty.call(t, r) || !Object.is(e[r], t[r])) return !1;
  return !0;
}
var r3 = { value: () => {} };
function Ul() {
  for (var e = 0, t = arguments.length, n = {}, r; e < t; ++e) {
    if (!(r = arguments[e] + "") || r in n || /[\s.]/.test(r))
      throw new Error("illegal type: " + r);
    n[r] = [];
  }
  return new bu(n);
}
function bu(e) {
  this._ = e;
}
function i3(e, t) {
  return e
    .trim()
    .split(/^|\s+/)
    .map(function (n) {
      var r = "",
        i = n.indexOf(".");
      if ((i >= 0 && ((r = n.slice(i + 1)), (n = n.slice(0, i))), n && !t.hasOwnProperty(n)))
        throw new Error("unknown type: " + n);
      return { type: n, name: r };
    });
}
bu.prototype = Ul.prototype = {
  constructor: bu,
  on: function (e, t) {
    var n = this._,
      r = i3(e + "", n),
      i,
      o = -1,
      s = r.length;
    if (arguments.length < 2) {
      for (; ++o < s; ) if ((i = (e = r[o]).type) && (i = o3(n[i], e.name))) return i;
      return;
    }
    if (t != null && typeof t != "function") throw new Error("invalid callback: " + t);
    for (; ++o < s; )
      if ((i = (e = r[o]).type)) n[i] = B1(n[i], e.name, t);
      else if (t == null) for (i in n) n[i] = B1(n[i], e.name, null);
    return this;
  },
  copy: function () {
    var e = {},
      t = this._;
    for (var n in t) e[n] = t[n].slice();
    return new bu(e);
  },
  call: function (e, t) {
    if ((i = arguments.length - 2) > 0)
      for (var n = new Array(i), r = 0, i, o; r < i; ++r) n[r] = arguments[r + 2];
    if (!this._.hasOwnProperty(e)) throw new Error("unknown type: " + e);
    for (o = this._[e], r = 0, i = o.length; r < i; ++r) o[r].value.apply(t, n);
  },
  apply: function (e, t, n) {
    if (!this._.hasOwnProperty(e)) throw new Error("unknown type: " + e);
    for (var r = this._[e], i = 0, o = r.length; i < o; ++i) r[i].value.apply(t, n);
  },
};
function o3(e, t) {
  for (var n = 0, r = e.length, i; n < r; ++n) if ((i = e[n]).name === t) return i.value;
}
function B1(e, t, n) {
  for (var r = 0, i = e.length; r < i; ++r)
    if (e[r].name === t) {
      (e[r] = r3), (e = e.slice(0, r).concat(e.slice(r + 1)));
      break;
    }
  return n != null && e.push({ name: t, value: n }), e;
}
var Sv = "http://www.w3.org/1999/xhtml";
const U1 = {
  svg: "http://www.w3.org/2000/svg",
  xhtml: Sv,
  xlink: "http://www.w3.org/1999/xlink",
  xml: "http://www.w3.org/XML/1998/namespace",
  xmlns: "http://www.w3.org/2000/xmlns/",
};
function Hl(e) {
  var t = (e += ""),
    n = t.indexOf(":");
  return (
    n >= 0 && (t = e.slice(0, n)) !== "xmlns" && (e = e.slice(n + 1)),
    U1.hasOwnProperty(t) ? { space: U1[t], local: e } : e
  );
}
function s3(e) {
  return function () {
    var t = this.ownerDocument,
      n = this.namespaceURI;
    return n === Sv && t.documentElement.namespaceURI === Sv
      ? t.createElement(e)
      : t.createElementNS(n, e);
  };
}
function a3(e) {
  return function () {
    return this.ownerDocument.createElementNS(e.space, e.local);
  };
}
function jP(e) {
  var t = Hl(e);
  return (t.local ? a3 : s3)(t);
}
function u3() {}
function n0(e) {
  return e == null
    ? u3
    : function () {
        return this.querySelector(e);
      };
}
function l3(e) {
  typeof e != "function" && (e = n0(e));
  for (var t = this._groups, n = t.length, r = new Array(n), i = 0; i < n; ++i)
    for (var o = t[i], s = o.length, a = (r[i] = new Array(s)), u, l, c = 0; c < s; ++c)
      (u = o[c]) &&
        (l = e.call(u, u.__data__, c, o)) &&
        ("__data__" in u && (l.__data__ = u.__data__), (a[c] = l));
  return new kt(r, this._parents);
}
function c3(e) {
  return e == null ? [] : Array.isArray(e) ? e : Array.from(e);
}
function f3() {
  return [];
}
function VP(e) {
  return e == null
    ? f3
    : function () {
        return this.querySelectorAll(e);
      };
}
function d3(e) {
  return function () {
    return c3(e.apply(this, arguments));
  };
}
function h3(e) {
  typeof e == "function" ? (e = d3(e)) : (e = VP(e));
  for (var t = this._groups, n = t.length, r = [], i = [], o = 0; o < n; ++o)
    for (var s = t[o], a = s.length, u, l = 0; l < a; ++l)
      (u = s[l]) && (r.push(e.call(u, u.__data__, l, s)), i.push(u));
  return new kt(r, i);
}
function qP(e) {
  return function () {
    return this.matches(e);
  };
}
function $P(e) {
  return function (t) {
    return t.matches(e);
  };
}
var p3 = Array.prototype.find;
function m3(e) {
  return function () {
    return p3.call(this.children, e);
  };
}
function g3() {
  return this.firstElementChild;
}
function v3(e) {
  return this.select(e == null ? g3 : m3(typeof e == "function" ? e : $P(e)));
}
var y3 = Array.prototype.filter;
function w3() {
  return Array.from(this.children);
}
function x3(e) {
  return function () {
    return y3.call(this.children, e);
  };
}
function _3(e) {
  return this.selectAll(e == null ? w3 : x3(typeof e == "function" ? e : $P(e)));
}
function b3(e) {
  typeof e != "function" && (e = qP(e));
  for (var t = this._groups, n = t.length, r = new Array(n), i = 0; i < n; ++i)
    for (var o = t[i], s = o.length, a = (r[i] = []), u, l = 0; l < s; ++l)
      (u = o[l]) && e.call(u, u.__data__, l, o) && a.push(u);
  return new kt(r, this._parents);
}
function zP(e) {
  return new Array(e.length);
}
function S3() {
  return new kt(this._enter || this._groups.map(zP), this._parents);
}
function il(e, t) {
  (this.ownerDocument = e.ownerDocument),
    (this.namespaceURI = e.namespaceURI),
    (this._next = null),
    (this._parent = e),
    (this.__data__ = t);
}
il.prototype = {
  constructor: il,
  appendChild: function (e) {
    return this._parent.insertBefore(e, this._next);
  },
  insertBefore: function (e, t) {
    return this._parent.insertBefore(e, t);
  },
  querySelector: function (e) {
    return this._parent.querySelector(e);
  },
  querySelectorAll: function (e) {
    return this._parent.querySelectorAll(e);
  },
};
function E3(e) {
  return function () {
    return e;
  };
}
function C3(e, t, n, r, i, o) {
  for (var s = 0, a, u = t.length, l = o.length; s < l; ++s)
    (a = t[s]) ? ((a.__data__ = o[s]), (r[s] = a)) : (n[s] = new il(e, o[s]));
  for (; s < u; ++s) (a = t[s]) && (i[s] = a);
}
function T3(e, t, n, r, i, o, s) {
  var a,
    u,
    l = new Map(),
    c = t.length,
    f = o.length,
    d = new Array(c),
    h;
  for (a = 0; a < c; ++a)
    (u = t[a]) &&
      ((d[a] = h = s.call(u, u.__data__, a, t) + ""), l.has(h) ? (i[a] = u) : l.set(h, u));
  for (a = 0; a < f; ++a)
    (h = s.call(e, o[a], a, o) + ""),
      (u = l.get(h)) ? ((r[a] = u), (u.__data__ = o[a]), l.delete(h)) : (n[a] = new il(e, o[a]));
  for (a = 0; a < c; ++a) (u = t[a]) && l.get(d[a]) === u && (i[a] = u);
}
function k3(e) {
  return e.__data__;
}
function R3(e, t) {
  if (!arguments.length) return Array.from(this, k3);
  var n = t ? T3 : C3,
    r = this._parents,
    i = this._groups;
  typeof e != "function" && (e = E3(e));
  for (var o = i.length, s = new Array(o), a = new Array(o), u = new Array(o), l = 0; l < o; ++l) {
    var c = r[l],
      f = i[l],
      d = f.length,
      h = P3(e.call(c, c && c.__data__, l, r)),
      v = h.length,
      p = (a[l] = new Array(v)),
      y = (s[l] = new Array(v)),
      m = (u[l] = new Array(d));
    n(c, f, p, y, m, h, t);
    for (var g = 0, w = 0, x, b; g < v; ++g)
      if ((x = p[g])) {
        for (g >= w && (w = g + 1); !(b = y[w]) && ++w < v; );
        x._next = b || null;
      }
  }
  return (s = new kt(s, r)), (s._enter = a), (s._exit = u), s;
}
function P3(e) {
  return typeof e == "object" && "length" in e ? e : Array.from(e);
}
function A3() {
  return new kt(this._exit || this._groups.map(zP), this._parents);
}
function N3(e, t, n) {
  var r = this.enter(),
    i = this,
    o = this.exit();
  return (
    typeof e == "function" ? ((r = e(r)), r && (r = r.selection())) : (r = r.append(e + "")),
    t != null && ((i = t(i)), i && (i = i.selection())),
    n == null ? o.remove() : n(o),
    r && i ? r.merge(i).order() : i
  );
}
function M3(e) {
  for (
    var t = e.selection ? e.selection() : e,
      n = this._groups,
      r = t._groups,
      i = n.length,
      o = r.length,
      s = Math.min(i, o),
      a = new Array(i),
      u = 0;
    u < s;
    ++u
  )
    for (var l = n[u], c = r[u], f = l.length, d = (a[u] = new Array(f)), h, v = 0; v < f; ++v)
      (h = l[v] || c[v]) && (d[v] = h);
  for (; u < i; ++u) a[u] = n[u];
  return new kt(a, this._parents);
}
function I3() {
  for (var e = this._groups, t = -1, n = e.length; ++t < n; )
    for (var r = e[t], i = r.length - 1, o = r[i], s; --i >= 0; )
      (s = r[i]) &&
        (o && s.compareDocumentPosition(o) ^ 4 && o.parentNode.insertBefore(s, o), (o = s));
  return this;
}
function D3(e) {
  e || (e = O3);
  function t(f, d) {
    return f && d ? e(f.__data__, d.__data__) : !f - !d;
  }
  for (var n = this._groups, r = n.length, i = new Array(r), o = 0; o < r; ++o) {
    for (var s = n[o], a = s.length, u = (i[o] = new Array(a)), l, c = 0; c < a; ++c)
      (l = s[c]) && (u[c] = l);
    u.sort(t);
  }
  return new kt(i, this._parents).order();
}
function O3(e, t) {
  return e < t ? -1 : e > t ? 1 : e >= t ? 0 : NaN;
}
function L3() {
  var e = arguments[0];
  return (arguments[0] = this), e.apply(null, arguments), this;
}
function F3() {
  return Array.from(this);
}
function j3() {
  for (var e = this._groups, t = 0, n = e.length; t < n; ++t)
    for (var r = e[t], i = 0, o = r.length; i < o; ++i) {
      var s = r[i];
      if (s) return s;
    }
  return null;
}
function V3() {
  let e = 0;
  for (const t of this) ++e;
  return e;
}
function q3() {
  return !this.node();
}
function $3(e) {
  for (var t = this._groups, n = 0, r = t.length; n < r; ++n)
    for (var i = t[n], o = 0, s = i.length, a; o < s; ++o)
      (a = i[o]) && e.call(a, a.__data__, o, i);
  return this;
}
function z3(e) {
  return function () {
    this.removeAttribute(e);
  };
}
function B3(e) {
  return function () {
    this.removeAttributeNS(e.space, e.local);
  };
}
function U3(e, t) {
  return function () {
    this.setAttribute(e, t);
  };
}
function H3(e, t) {
  return function () {
    this.setAttributeNS(e.space, e.local, t);
  };
}
function G3(e, t) {
  return function () {
    var n = t.apply(this, arguments);
    n == null ? this.removeAttribute(e) : this.setAttribute(e, n);
  };
}
function W3(e, t) {
  return function () {
    var n = t.apply(this, arguments);
    n == null ? this.removeAttributeNS(e.space, e.local) : this.setAttributeNS(e.space, e.local, n);
  };
}
function K3(e, t) {
  var n = Hl(e);
  if (arguments.length < 2) {
    var r = this.node();
    return n.local ? r.getAttributeNS(n.space, n.local) : r.getAttribute(n);
  }
  return this.each(
    (t == null
      ? n.local
        ? B3
        : z3
      : typeof t == "function"
        ? n.local
          ? W3
          : G3
        : n.local
          ? H3
          : U3)(n, t),
  );
}
function BP(e) {
  return (e.ownerDocument && e.ownerDocument.defaultView) || (e.document && e) || e.defaultView;
}
function Y3(e) {
  return function () {
    this.style.removeProperty(e);
  };
}
function X3(e, t, n) {
  return function () {
    this.style.setProperty(e, t, n);
  };
}
function Z3(e, t, n) {
  return function () {
    var r = t.apply(this, arguments);
    r == null ? this.style.removeProperty(e) : this.style.setProperty(e, r, n);
  };
}
function Q3(e, t, n) {
  return arguments.length > 1
    ? this.each((t == null ? Y3 : typeof t == "function" ? Z3 : X3)(e, t, n ?? ""))
    : fo(this.node(), e);
}
function fo(e, t) {
  return e.style.getPropertyValue(t) || BP(e).getComputedStyle(e, null).getPropertyValue(t);
}
function J3(e) {
  return function () {
    delete this[e];
  };
}
function ej(e, t) {
  return function () {
    this[e] = t;
  };
}
function tj(e, t) {
  return function () {
    var n = t.apply(this, arguments);
    n == null ? delete this[e] : (this[e] = n);
  };
}
function nj(e, t) {
  return arguments.length > 1
    ? this.each((t == null ? J3 : typeof t == "function" ? tj : ej)(e, t))
    : this.node()[e];
}
function UP(e) {
  return e.trim().split(/^|\s+/);
}
function r0(e) {
  return e.classList || new HP(e);
}
function HP(e) {
  (this._node = e), (this._names = UP(e.getAttribute("class") || ""));
}
HP.prototype = {
  add: function (e) {
    var t = this._names.indexOf(e);
    t < 0 && (this._names.push(e), this._node.setAttribute("class", this._names.join(" ")));
  },
  remove: function (e) {
    var t = this._names.indexOf(e);
    t >= 0 && (this._names.splice(t, 1), this._node.setAttribute("class", this._names.join(" ")));
  },
  contains: function (e) {
    return this._names.indexOf(e) >= 0;
  },
};
function GP(e, t) {
  for (var n = r0(e), r = -1, i = t.length; ++r < i; ) n.add(t[r]);
}
function WP(e, t) {
  for (var n = r0(e), r = -1, i = t.length; ++r < i; ) n.remove(t[r]);
}
function rj(e) {
  return function () {
    GP(this, e);
  };
}
function ij(e) {
  return function () {
    WP(this, e);
  };
}
function oj(e, t) {
  return function () {
    (t.apply(this, arguments) ? GP : WP)(this, e);
  };
}
function sj(e, t) {
  var n = UP(e + "");
  if (arguments.length < 2) {
    for (var r = r0(this.node()), i = -1, o = n.length; ++i < o; ) if (!r.contains(n[i])) return !1;
    return !0;
  }
  return this.each((typeof t == "function" ? oj : t ? rj : ij)(n, t));
}
function aj() {
  this.textContent = "";
}
function uj(e) {
  return function () {
    this.textContent = e;
  };
}
function lj(e) {
  return function () {
    var t = e.apply(this, arguments);
    this.textContent = t ?? "";
  };
}
function cj(e) {
  return arguments.length
    ? this.each(e == null ? aj : (typeof e == "function" ? lj : uj)(e))
    : this.node().textContent;
}
function fj() {
  this.innerHTML = "";
}
function dj(e) {
  return function () {
    this.innerHTML = e;
  };
}
function hj(e) {
  return function () {
    var t = e.apply(this, arguments);
    this.innerHTML = t ?? "";
  };
}
function pj(e) {
  return arguments.length
    ? this.each(e == null ? fj : (typeof e == "function" ? hj : dj)(e))
    : this.node().innerHTML;
}
function mj() {
  this.nextSibling && this.parentNode.appendChild(this);
}
function gj() {
  return this.each(mj);
}
function vj() {
  this.previousSibling && this.parentNode.insertBefore(this, this.parentNode.firstChild);
}
function yj() {
  return this.each(vj);
}
function wj(e) {
  var t = typeof e == "function" ? e : jP(e);
  return this.select(function () {
    return this.appendChild(t.apply(this, arguments));
  });
}
function xj() {
  return null;
}
function _j(e, t) {
  var n = typeof e == "function" ? e : jP(e),
    r = t == null ? xj : typeof t == "function" ? t : n0(t);
  return this.select(function () {
    return this.insertBefore(n.apply(this, arguments), r.apply(this, arguments) || null);
  });
}
function bj() {
  var e = this.parentNode;
  e && e.removeChild(this);
}
function Sj() {
  return this.each(bj);
}
function Ej() {
  var e = this.cloneNode(!1),
    t = this.parentNode;
  return t ? t.insertBefore(e, this.nextSibling) : e;
}
function Cj() {
  var e = this.cloneNode(!0),
    t = this.parentNode;
  return t ? t.insertBefore(e, this.nextSibling) : e;
}
function Tj(e) {
  return this.select(e ? Cj : Ej);
}
function kj(e) {
  return arguments.length ? this.property("__data__", e) : this.node().__data__;
}
function Rj(e) {
  return function (t) {
    e.call(this, t, this.__data__);
  };
}
function Pj(e) {
  return e
    .trim()
    .split(/^|\s+/)
    .map(function (t) {
      var n = "",
        r = t.indexOf(".");
      return r >= 0 && ((n = t.slice(r + 1)), (t = t.slice(0, r))), { type: t, name: n };
    });
}
function Aj(e) {
  return function () {
    var t = this.__on;
    if (t) {
      for (var n = 0, r = -1, i = t.length, o; n < i; ++n)
        (o = t[n]),
          (!e.type || o.type === e.type) && o.name === e.name
            ? this.removeEventListener(o.type, o.listener, o.options)
            : (t[++r] = o);
      ++r ? (t.length = r) : delete this.__on;
    }
  };
}
function Nj(e, t, n) {
  return function () {
    var r = this.__on,
      i,
      o = Rj(t);
    if (r) {
      for (var s = 0, a = r.length; s < a; ++s)
        if ((i = r[s]).type === e.type && i.name === e.name) {
          this.removeEventListener(i.type, i.listener, i.options),
            this.addEventListener(i.type, (i.listener = o), (i.options = n)),
            (i.value = t);
          return;
        }
    }
    this.addEventListener(e.type, o, n),
      (i = { type: e.type, name: e.name, value: t, listener: o, options: n }),
      r ? r.push(i) : (this.__on = [i]);
  };
}
function Mj(e, t, n) {
  var r = Pj(e + ""),
    i,
    o = r.length,
    s;
  if (arguments.length < 2) {
    var a = this.node().__on;
    if (a) {
      for (var u = 0, l = a.length, c; u < l; ++u)
        for (i = 0, c = a[u]; i < o; ++i)
          if ((s = r[i]).type === c.type && s.name === c.name) return c.value;
    }
    return;
  }
  for (a = t ? Nj : Aj, i = 0; i < o; ++i) this.each(a(r[i], t, n));
  return this;
}
function KP(e, t, n) {
  var r = BP(e),
    i = r.CustomEvent;
  typeof i == "function"
    ? (i = new i(t, n))
    : ((i = r.document.createEvent("Event")),
      n
        ? (i.initEvent(t, n.bubbles, n.cancelable), (i.detail = n.detail))
        : i.initEvent(t, !1, !1)),
    e.dispatchEvent(i);
}
function Ij(e, t) {
  return function () {
    return KP(this, e, t);
  };
}
function Dj(e, t) {
  return function () {
    return KP(this, e, t.apply(this, arguments));
  };
}
function Oj(e, t) {
  return this.each((typeof t == "function" ? Dj : Ij)(e, t));
}
function* Lj() {
  for (var e = this._groups, t = 0, n = e.length; t < n; ++t)
    for (var r = e[t], i = 0, o = r.length, s; i < o; ++i) (s = r[i]) && (yield s);
}
var YP = [null];
function kt(e, t) {
  (this._groups = e), (this._parents = t);
}
function ca() {
  return new kt([[document.documentElement]], YP);
}
function Fj() {
  return this;
}
kt.prototype = ca.prototype = {
  constructor: kt,
  select: l3,
  selectAll: h3,
  selectChild: v3,
  selectChildren: _3,
  filter: b3,
  data: R3,
  enter: S3,
  exit: A3,
  join: N3,
  merge: M3,
  selection: Fj,
  order: I3,
  sort: D3,
  call: L3,
  nodes: F3,
  node: j3,
  size: V3,
  empty: q3,
  each: $3,
  attr: K3,
  style: Q3,
  property: nj,
  classed: sj,
  text: cj,
  html: pj,
  raise: gj,
  lower: yj,
  append: wj,
  insert: _j,
  remove: Sj,
  clone: Tj,
  datum: kj,
  on: Mj,
  dispatch: Oj,
  [Symbol.iterator]: Lj,
};
function Ot(e) {
  return typeof e == "string"
    ? new kt([[document.querySelector(e)]], [document.documentElement])
    : new kt([[e]], YP);
}
function jj(e) {
  let t;
  for (; (t = e.sourceEvent); ) e = t;
  return e;
}
function Xt(e, t) {
  if (((e = jj(e)), t === void 0 && (t = e.currentTarget), t)) {
    var n = t.ownerSVGElement || t;
    if (n.createSVGPoint) {
      var r = n.createSVGPoint();
      return (
        (r.x = e.clientX),
        (r.y = e.clientY),
        (r = r.matrixTransform(t.getScreenCTM().inverse())),
        [r.x, r.y]
      );
    }
    if (t.getBoundingClientRect) {
      var i = t.getBoundingClientRect();
      return [e.clientX - i.left - t.clientLeft, e.clientY - i.top - t.clientTop];
    }
  }
  return [e.pageX, e.pageY];
}
const Vj = { passive: !1 },
  Gs = { capture: !0, passive: !1 };
function of(e) {
  e.stopImmediatePropagation();
}
function Qi(e) {
  e.preventDefault(), e.stopImmediatePropagation();
}
function XP(e) {
  var t = e.document.documentElement,
    n = Ot(e).on("dragstart.drag", Qi, Gs);
  "onselectstart" in t
    ? n.on("selectstart.drag", Qi, Gs)
    : ((t.__noselect = t.style.MozUserSelect), (t.style.MozUserSelect = "none"));
}
function ZP(e, t) {
  var n = e.document.documentElement,
    r = Ot(e).on("dragstart.drag", null);
  t &&
    (r.on("click.drag", Qi, Gs),
    setTimeout(function () {
      r.on("click.drag", null);
    }, 0)),
    "onselectstart" in n
      ? r.on("selectstart.drag", null)
      : ((n.style.MozUserSelect = n.__noselect), delete n.__noselect);
}
const Ha = (e) => () => e;
function Ev(
  e,
  {
    sourceEvent: t,
    subject: n,
    target: r,
    identifier: i,
    active: o,
    x: s,
    y: a,
    dx: u,
    dy: l,
    dispatch: c,
  },
) {
  Object.defineProperties(this, {
    type: { value: e, enumerable: !0, configurable: !0 },
    sourceEvent: { value: t, enumerable: !0, configurable: !0 },
    subject: { value: n, enumerable: !0, configurable: !0 },
    target: { value: r, enumerable: !0, configurable: !0 },
    identifier: { value: i, enumerable: !0, configurable: !0 },
    active: { value: o, enumerable: !0, configurable: !0 },
    x: { value: s, enumerable: !0, configurable: !0 },
    y: { value: a, enumerable: !0, configurable: !0 },
    dx: { value: u, enumerable: !0, configurable: !0 },
    dy: { value: l, enumerable: !0, configurable: !0 },
    _: { value: c },
  });
}
Ev.prototype.on = function () {
  var e = this._.on.apply(this._, arguments);
  return e === this._ ? this : e;
};
function qj(e) {
  return !e.ctrlKey && !e.button;
}
function $j() {
  return this.parentNode;
}
function zj(e, t) {
  return t ?? { x: e.x, y: e.y };
}
function Bj() {
  return navigator.maxTouchPoints || "ontouchstart" in this;
}
function Uj() {
  var e = qj,
    t = $j,
    n = zj,
    r = Bj,
    i = {},
    o = Ul("start", "drag", "end"),
    s = 0,
    a,
    u,
    l,
    c,
    f = 0;
  function d(x) {
    x.on("mousedown.drag", h)
      .filter(r)
      .on("touchstart.drag", y)
      .on("touchmove.drag", m, Vj)
      .on("touchend.drag touchcancel.drag", g)
      .style("touch-action", "none")
      .style("-webkit-tap-highlight-color", "rgba(0,0,0,0)");
  }
  function h(x, b) {
    if (!(c || !e.call(this, x, b))) {
      var E = w(this, t.call(this, x, b), x, b, "mouse");
      E &&
        (Ot(x.view).on("mousemove.drag", v, Gs).on("mouseup.drag", p, Gs),
        XP(x.view),
        of(x),
        (l = !1),
        (a = x.clientX),
        (u = x.clientY),
        E("start", x));
    }
  }
  function v(x) {
    if ((Qi(x), !l)) {
      var b = x.clientX - a,
        E = x.clientY - u;
      l = b * b + E * E > f;
    }
    i.mouse("drag", x);
  }
  function p(x) {
    Ot(x.view).on("mousemove.drag mouseup.drag", null), ZP(x.view, l), Qi(x), i.mouse("end", x);
  }
  function y(x, b) {
    if (e.call(this, x, b)) {
      var E = x.changedTouches,
        C = t.call(this, x, b),
        T = E.length,
        P,
        M;
      for (P = 0; P < T; ++P)
        (M = w(this, C, x, b, E[P].identifier, E[P])) && (of(x), M("start", x, E[P]));
    }
  }
  function m(x) {
    var b = x.changedTouches,
      E = b.length,
      C,
      T;
    for (C = 0; C < E; ++C) (T = i[b[C].identifier]) && (Qi(x), T("drag", x, b[C]));
  }
  function g(x) {
    var b = x.changedTouches,
      E = b.length,
      C,
      T;
    for (
      c && clearTimeout(c),
        c = setTimeout(function () {
          c = null;
        }, 500),
        C = 0;
      C < E;
      ++C
    )
      (T = i[b[C].identifier]) && (of(x), T("end", x, b[C]));
  }
  function w(x, b, E, C, T, P) {
    var M = o.copy(),
      I = Xt(P || E, b),
      j,
      q,
      S;
    if (
      (S = n.call(
        x,
        new Ev("beforestart", {
          sourceEvent: E,
          target: d,
          identifier: T,
          active: s,
          x: I[0],
          y: I[1],
          dx: 0,
          dy: 0,
          dispatch: M,
        }),
        C,
      )) != null
    )
      return (
        (j = S.x - I[0] || 0),
        (q = S.y - I[1] || 0),
        function O(A, F, N) {
          var k = I,
            D;
          switch (A) {
            case "start":
              (i[T] = O), (D = s++);
              break;
            case "end":
              delete i[T], --s;
            case "drag":
              (I = Xt(N || F, b)), (D = s);
              break;
          }
          M.call(
            A,
            x,
            new Ev(A, {
              sourceEvent: F,
              subject: S,
              target: d,
              identifier: T,
              active: D,
              x: I[0] + j,
              y: I[1] + q,
              dx: I[0] - k[0],
              dy: I[1] - k[1],
              dispatch: M,
            }),
            C,
          );
        }
      );
  }
  return (
    (d.filter = function (x) {
      return arguments.length ? ((e = typeof x == "function" ? x : Ha(!!x)), d) : e;
    }),
    (d.container = function (x) {
      return arguments.length ? ((t = typeof x == "function" ? x : Ha(x)), d) : t;
    }),
    (d.subject = function (x) {
      return arguments.length ? ((n = typeof x == "function" ? x : Ha(x)), d) : n;
    }),
    (d.touchable = function (x) {
      return arguments.length ? ((r = typeof x == "function" ? x : Ha(!!x)), d) : r;
    }),
    (d.on = function () {
      var x = o.on.apply(o, arguments);
      return x === o ? d : x;
    }),
    (d.clickDistance = function (x) {
      return arguments.length ? ((f = (x = +x) * x), d) : Math.sqrt(f);
    }),
    d
  );
}
function i0(e, t, n) {
  (e.prototype = t.prototype = n), (n.constructor = e);
}
function QP(e, t) {
  var n = Object.create(e.prototype);
  for (var r in t) n[r] = t[r];
  return n;
}
function fa() {}
var Ws = 0.7,
  ol = 1 / Ws,
  Ji = "\\s*([+-]?\\d+)\\s*",
  Ks = "\\s*([+-]?(?:\\d*\\.)?\\d+(?:[eE][+-]?\\d+)?)\\s*",
  wn = "\\s*([+-]?(?:\\d*\\.)?\\d+(?:[eE][+-]?\\d+)?)%\\s*",
  Hj = /^#([0-9a-f]{3,8})$/,
  Gj = new RegExp(`^rgb\\(${Ji},${Ji},${Ji}\\)$`),
  Wj = new RegExp(`^rgb\\(${wn},${wn},${wn}\\)$`),
  Kj = new RegExp(`^rgba\\(${Ji},${Ji},${Ji},${Ks}\\)$`),
  Yj = new RegExp(`^rgba\\(${wn},${wn},${wn},${Ks}\\)$`),
  Xj = new RegExp(`^hsl\\(${Ks},${wn},${wn}\\)$`),
  Zj = new RegExp(`^hsla\\(${Ks},${wn},${wn},${Ks}\\)$`),
  H1 = {
    aliceblue: 15792383,
    antiquewhite: 16444375,
    aqua: 65535,
    aquamarine: 8388564,
    azure: 15794175,
    beige: 16119260,
    bisque: 16770244,
    black: 0,
    blanchedalmond: 16772045,
    blue: 255,
    blueviolet: 9055202,
    brown: 10824234,
    burlywood: 14596231,
    cadetblue: 6266528,
    chartreuse: 8388352,
    chocolate: 13789470,
    coral: 16744272,
    cornflowerblue: 6591981,
    cornsilk: 16775388,
    crimson: 14423100,
    cyan: 65535,
    darkblue: 139,
    darkcyan: 35723,
    darkgoldenrod: 12092939,
    darkgray: 11119017,
    darkgreen: 25600,
    darkgrey: 11119017,
    darkkhaki: 12433259,
    darkmagenta: 9109643,
    darkolivegreen: 5597999,
    darkorange: 16747520,
    darkorchid: 10040012,
    darkred: 9109504,
    darksalmon: 15308410,
    darkseagreen: 9419919,
    darkslateblue: 4734347,
    darkslategray: 3100495,
    darkslategrey: 3100495,
    darkturquoise: 52945,
    darkviolet: 9699539,
    deeppink: 16716947,
    deepskyblue: 49151,
    dimgray: 6908265,
    dimgrey: 6908265,
    dodgerblue: 2003199,
    firebrick: 11674146,
    floralwhite: 16775920,
    forestgreen: 2263842,
    fuchsia: 16711935,
    gainsboro: 14474460,
    ghostwhite: 16316671,
    gold: 16766720,
    goldenrod: 14329120,
    gray: 8421504,
    green: 32768,
    greenyellow: 11403055,
    grey: 8421504,
    honeydew: 15794160,
    hotpink: 16738740,
    indianred: 13458524,
    indigo: 4915330,
    ivory: 16777200,
    khaki: 15787660,
    lavender: 15132410,
    lavenderblush: 16773365,
    lawngreen: 8190976,
    lemonchiffon: 16775885,
    lightblue: 11393254,
    lightcoral: 15761536,
    lightcyan: 14745599,
    lightgoldenrodyellow: 16448210,
    lightgray: 13882323,
    lightgreen: 9498256,
    lightgrey: 13882323,
    lightpink: 16758465,
    lightsalmon: 16752762,
    lightseagreen: 2142890,
    lightskyblue: 8900346,
    lightslategray: 7833753,
    lightslategrey: 7833753,
    lightsteelblue: 11584734,
    lightyellow: 16777184,
    lime: 65280,
    limegreen: 3329330,
    linen: 16445670,
    magenta: 16711935,
    maroon: 8388608,
    mediumaquamarine: 6737322,
    mediumblue: 205,
    mediumorchid: 12211667,
    mediumpurple: 9662683,
    mediumseagreen: 3978097,
    mediumslateblue: 8087790,
    mediumspringgreen: 64154,
    mediumturquoise: 4772300,
    mediumvioletred: 13047173,
    midnightblue: 1644912,
    mintcream: 16121850,
    mistyrose: 16770273,
    moccasin: 16770229,
    navajowhite: 16768685,
    navy: 128,
    oldlace: 16643558,
    olive: 8421376,
    olivedrab: 7048739,
    orange: 16753920,
    orangered: 16729344,
    orchid: 14315734,
    palegoldenrod: 15657130,
    palegreen: 10025880,
    paleturquoise: 11529966,
    palevioletred: 14381203,
    papayawhip: 16773077,
    peachpuff: 16767673,
    peru: 13468991,
    pink: 16761035,
    plum: 14524637,
    powderblue: 11591910,
    purple: 8388736,
    rebeccapurple: 6697881,
    red: 16711680,
    rosybrown: 12357519,
    royalblue: 4286945,
    saddlebrown: 9127187,
    salmon: 16416882,
    sandybrown: 16032864,
    seagreen: 3050327,
    seashell: 16774638,
    sienna: 10506797,
    silver: 12632256,
    skyblue: 8900331,
    slateblue: 6970061,
    slategray: 7372944,
    slategrey: 7372944,
    snow: 16775930,
    springgreen: 65407,
    steelblue: 4620980,
    tan: 13808780,
    teal: 32896,
    thistle: 14204888,
    tomato: 16737095,
    turquoise: 4251856,
    violet: 15631086,
    wheat: 16113331,
    white: 16777215,
    whitesmoke: 16119285,
    yellow: 16776960,
    yellowgreen: 10145074,
  };
i0(fa, Ys, {
  copy(e) {
    return Object.assign(new this.constructor(), this, e);
  },
  displayable() {
    return this.rgb().displayable();
  },
  hex: G1,
  formatHex: G1,
  formatHex8: Qj,
  formatHsl: Jj,
  formatRgb: W1,
  toString: W1,
});
function G1() {
  return this.rgb().formatHex();
}
function Qj() {
  return this.rgb().formatHex8();
}
function Jj() {
  return JP(this).formatHsl();
}
function W1() {
  return this.rgb().formatRgb();
}
function Ys(e) {
  var t, n;
  return (
    (e = (e + "").trim().toLowerCase()),
    (t = Hj.exec(e))
      ? ((n = t[1].length),
        (t = parseInt(t[1], 16)),
        n === 6
          ? K1(t)
          : n === 3
            ? new mt(
                ((t >> 8) & 15) | ((t >> 4) & 240),
                ((t >> 4) & 15) | (t & 240),
                ((t & 15) << 4) | (t & 15),
                1,
              )
            : n === 8
              ? Ga((t >> 24) & 255, (t >> 16) & 255, (t >> 8) & 255, (t & 255) / 255)
              : n === 4
                ? Ga(
                    ((t >> 12) & 15) | ((t >> 8) & 240),
                    ((t >> 8) & 15) | ((t >> 4) & 240),
                    ((t >> 4) & 15) | (t & 240),
                    (((t & 15) << 4) | (t & 15)) / 255,
                  )
                : null)
      : (t = Gj.exec(e))
        ? new mt(t[1], t[2], t[3], 1)
        : (t = Wj.exec(e))
          ? new mt((t[1] * 255) / 100, (t[2] * 255) / 100, (t[3] * 255) / 100, 1)
          : (t = Kj.exec(e))
            ? Ga(t[1], t[2], t[3], t[4])
            : (t = Yj.exec(e))
              ? Ga((t[1] * 255) / 100, (t[2] * 255) / 100, (t[3] * 255) / 100, t[4])
              : (t = Xj.exec(e))
                ? Z1(t[1], t[2] / 100, t[3] / 100, 1)
                : (t = Zj.exec(e))
                  ? Z1(t[1], t[2] / 100, t[3] / 100, t[4])
                  : H1.hasOwnProperty(e)
                    ? K1(H1[e])
                    : e === "transparent"
                      ? new mt(NaN, NaN, NaN, 0)
                      : null
  );
}
function K1(e) {
  return new mt((e >> 16) & 255, (e >> 8) & 255, e & 255, 1);
}
function Ga(e, t, n, r) {
  return r <= 0 && (e = t = n = NaN), new mt(e, t, n, r);
}
function eV(e) {
  return (
    e instanceof fa || (e = Ys(e)), e ? ((e = e.rgb()), new mt(e.r, e.g, e.b, e.opacity)) : new mt()
  );
}
function Cv(e, t, n, r) {
  return arguments.length === 1 ? eV(e) : new mt(e, t, n, r ?? 1);
}
function mt(e, t, n, r) {
  (this.r = +e), (this.g = +t), (this.b = +n), (this.opacity = +r);
}
i0(
  mt,
  Cv,
  QP(fa, {
    brighter(e) {
      return (
        (e = e == null ? ol : Math.pow(ol, e)),
        new mt(this.r * e, this.g * e, this.b * e, this.opacity)
      );
    },
    darker(e) {
      return (
        (e = e == null ? Ws : Math.pow(Ws, e)),
        new mt(this.r * e, this.g * e, this.b * e, this.opacity)
      );
    },
    rgb() {
      return this;
    },
    clamp() {
      return new mt(ti(this.r), ti(this.g), ti(this.b), sl(this.opacity));
    },
    displayable() {
      return (
        -0.5 <= this.r &&
        this.r < 255.5 &&
        -0.5 <= this.g &&
        this.g < 255.5 &&
        -0.5 <= this.b &&
        this.b < 255.5 &&
        0 <= this.opacity &&
        this.opacity <= 1
      );
    },
    hex: Y1,
    formatHex: Y1,
    formatHex8: tV,
    formatRgb: X1,
    toString: X1,
  }),
);
function Y1() {
  return `#${Yr(this.r)}${Yr(this.g)}${Yr(this.b)}`;
}
function tV() {
  return `#${Yr(this.r)}${Yr(this.g)}${Yr(this.b)}${Yr((isNaN(this.opacity) ? 1 : this.opacity) * 255)}`;
}
function X1() {
  const e = sl(this.opacity);
  return `${e === 1 ? "rgb(" : "rgba("}${ti(this.r)}, ${ti(this.g)}, ${ti(this.b)}${e === 1 ? ")" : `, ${e})`}`;
}
function sl(e) {
  return isNaN(e) ? 1 : Math.max(0, Math.min(1, e));
}
function ti(e) {
  return Math.max(0, Math.min(255, Math.round(e) || 0));
}
function Yr(e) {
  return (e = ti(e)), (e < 16 ? "0" : "") + e.toString(16);
}
function Z1(e, t, n, r) {
  return (
    r <= 0 ? (e = t = n = NaN) : n <= 0 || n >= 1 ? (e = t = NaN) : t <= 0 && (e = NaN),
    new Qt(e, t, n, r)
  );
}
function JP(e) {
  if (e instanceof Qt) return new Qt(e.h, e.s, e.l, e.opacity);
  if ((e instanceof fa || (e = Ys(e)), !e)) return new Qt();
  if (e instanceof Qt) return e;
  e = e.rgb();
  var t = e.r / 255,
    n = e.g / 255,
    r = e.b / 255,
    i = Math.min(t, n, r),
    o = Math.max(t, n, r),
    s = NaN,
    a = o - i,
    u = (o + i) / 2;
  return (
    a
      ? (t === o
          ? (s = (n - r) / a + (n < r) * 6)
          : n === o
            ? (s = (r - t) / a + 2)
            : (s = (t - n) / a + 4),
        (a /= u < 0.5 ? o + i : 2 - o - i),
        (s *= 60))
      : (a = u > 0 && u < 1 ? 0 : s),
    new Qt(s, a, u, e.opacity)
  );
}
function nV(e, t, n, r) {
  return arguments.length === 1 ? JP(e) : new Qt(e, t, n, r ?? 1);
}
function Qt(e, t, n, r) {
  (this.h = +e), (this.s = +t), (this.l = +n), (this.opacity = +r);
}
i0(
  Qt,
  nV,
  QP(fa, {
    brighter(e) {
      return (
        (e = e == null ? ol : Math.pow(ol, e)), new Qt(this.h, this.s, this.l * e, this.opacity)
      );
    },
    darker(e) {
      return (
        (e = e == null ? Ws : Math.pow(Ws, e)), new Qt(this.h, this.s, this.l * e, this.opacity)
      );
    },
    rgb() {
      var e = (this.h % 360) + (this.h < 0) * 360,
        t = isNaN(e) || isNaN(this.s) ? 0 : this.s,
        n = this.l,
        r = n + (n < 0.5 ? n : 1 - n) * t,
        i = 2 * n - r;
      return new mt(
        sf(e >= 240 ? e - 240 : e + 120, i, r),
        sf(e, i, r),
        sf(e < 120 ? e + 240 : e - 120, i, r),
        this.opacity,
      );
    },
    clamp() {
      return new Qt(Q1(this.h), Wa(this.s), Wa(this.l), sl(this.opacity));
    },
    displayable() {
      return (
        ((0 <= this.s && this.s <= 1) || isNaN(this.s)) &&
        0 <= this.l &&
        this.l <= 1 &&
        0 <= this.opacity &&
        this.opacity <= 1
      );
    },
    formatHsl() {
      const e = sl(this.opacity);
      return `${e === 1 ? "hsl(" : "hsla("}${Q1(this.h)}, ${Wa(this.s) * 100}%, ${Wa(this.l) * 100}%${e === 1 ? ")" : `, ${e})`}`;
    },
  }),
);
function Q1(e) {
  return (e = (e || 0) % 360), e < 0 ? e + 360 : e;
}
function Wa(e) {
  return Math.max(0, Math.min(1, e || 0));
}
function sf(e, t, n) {
  return (
    (e < 60 ? t + ((n - t) * e) / 60 : e < 180 ? n : e < 240 ? t + ((n - t) * (240 - e)) / 60 : t) *
    255
  );
}
const eA = (e) => () => e;
function rV(e, t) {
  return function (n) {
    return e + n * t;
  };
}
function iV(e, t, n) {
  return (
    (e = Math.pow(e, n)),
    (t = Math.pow(t, n) - e),
    (n = 1 / n),
    function (r) {
      return Math.pow(e + r * t, n);
    }
  );
}
function oV(e) {
  return (e = +e) == 1
    ? tA
    : function (t, n) {
        return n - t ? iV(t, n, e) : eA(isNaN(t) ? n : t);
      };
}
function tA(e, t) {
  var n = t - e;
  return n ? rV(e, n) : eA(isNaN(e) ? t : e);
}
const J1 = (function e(t) {
  var n = oV(t);
  function r(i, o) {
    var s = n((i = Cv(i)).r, (o = Cv(o)).r),
      a = n(i.g, o.g),
      u = n(i.b, o.b),
      l = tA(i.opacity, o.opacity);
    return function (c) {
      return (i.r = s(c)), (i.g = a(c)), (i.b = u(c)), (i.opacity = l(c)), i + "";
    };
  }
  return (r.gamma = e), r;
})(1);
function fr(e, t) {
  return (
    (e = +e),
    (t = +t),
    function (n) {
      return e * (1 - n) + t * n;
    }
  );
}
var Tv = /[-+]?(?:\d+\.?\d*|\.?\d+)(?:[eE][-+]?\d+)?/g,
  af = new RegExp(Tv.source, "g");
function sV(e) {
  return function () {
    return e;
  };
}
function aV(e) {
  return function (t) {
    return e(t) + "";
  };
}
function uV(e, t) {
  var n = (Tv.lastIndex = af.lastIndex = 0),
    r,
    i,
    o,
    s = -1,
    a = [],
    u = [];
  for (e = e + "", t = t + ""; (r = Tv.exec(e)) && (i = af.exec(t)); )
    (o = i.index) > n && ((o = t.slice(n, o)), a[s] ? (a[s] += o) : (a[++s] = o)),
      (r = r[0]) === (i = i[0])
        ? a[s]
          ? (a[s] += i)
          : (a[++s] = i)
        : ((a[++s] = null), u.push({ i: s, x: fr(r, i) })),
      (n = af.lastIndex);
  return (
    n < t.length && ((o = t.slice(n)), a[s] ? (a[s] += o) : (a[++s] = o)),
    a.length < 2
      ? u[0]
        ? aV(u[0].x)
        : sV(t)
      : ((t = u.length),
        function (l) {
          for (var c = 0, f; c < t; ++c) a[(f = u[c]).i] = f.x(l);
          return a.join("");
        })
  );
}
var ex = 180 / Math.PI,
  kv = { translateX: 0, translateY: 0, rotate: 0, skewX: 0, scaleX: 1, scaleY: 1 };
function nA(e, t, n, r, i, o) {
  var s, a, u;
  return (
    (s = Math.sqrt(e * e + t * t)) && ((e /= s), (t /= s)),
    (u = e * n + t * r) && ((n -= e * u), (r -= t * u)),
    (a = Math.sqrt(n * n + r * r)) && ((n /= a), (r /= a), (u /= a)),
    e * r < t * n && ((e = -e), (t = -t), (u = -u), (s = -s)),
    {
      translateX: i,
      translateY: o,
      rotate: Math.atan2(t, e) * ex,
      skewX: Math.atan(u) * ex,
      scaleX: s,
      scaleY: a,
    }
  );
}
var Ka;
function lV(e) {
  const t = new (typeof DOMMatrix == "function" ? DOMMatrix : WebKitCSSMatrix)(e + "");
  return t.isIdentity ? kv : nA(t.a, t.b, t.c, t.d, t.e, t.f);
}
function cV(e) {
  return e == null ||
    (Ka || (Ka = document.createElementNS("http://www.w3.org/2000/svg", "g")),
    Ka.setAttribute("transform", e),
    !(e = Ka.transform.baseVal.consolidate()))
    ? kv
    : ((e = e.matrix), nA(e.a, e.b, e.c, e.d, e.e, e.f));
}
function rA(e, t, n, r) {
  function i(l) {
    return l.length ? l.pop() + " " : "";
  }
  function o(l, c, f, d, h, v) {
    if (l !== f || c !== d) {
      var p = h.push("translate(", null, t, null, n);
      v.push({ i: p - 4, x: fr(l, f) }, { i: p - 2, x: fr(c, d) });
    } else (f || d) && h.push("translate(" + f + t + d + n);
  }
  function s(l, c, f, d) {
    l !== c
      ? (l - c > 180 ? (c += 360) : c - l > 180 && (l += 360),
        d.push({ i: f.push(i(f) + "rotate(", null, r) - 2, x: fr(l, c) }))
      : c && f.push(i(f) + "rotate(" + c + r);
  }
  function a(l, c, f, d) {
    l !== c
      ? d.push({ i: f.push(i(f) + "skewX(", null, r) - 2, x: fr(l, c) })
      : c && f.push(i(f) + "skewX(" + c + r);
  }
  function u(l, c, f, d, h, v) {
    if (l !== f || c !== d) {
      var p = h.push(i(h) + "scale(", null, ",", null, ")");
      v.push({ i: p - 4, x: fr(l, f) }, { i: p - 2, x: fr(c, d) });
    } else (f !== 1 || d !== 1) && h.push(i(h) + "scale(" + f + "," + d + ")");
  }
  return function (l, c) {
    var f = [],
      d = [];
    return (
      (l = e(l)),
      (c = e(c)),
      o(l.translateX, l.translateY, c.translateX, c.translateY, f, d),
      s(l.rotate, c.rotate, f, d),
      a(l.skewX, c.skewX, f, d),
      u(l.scaleX, l.scaleY, c.scaleX, c.scaleY, f, d),
      (l = c = null),
      function (h) {
        for (var v = -1, p = d.length, y; ++v < p; ) f[(y = d[v]).i] = y.x(h);
        return f.join("");
      }
    );
  };
}
var fV = rA(lV, "px, ", "px)", "deg)"),
  dV = rA(cV, ", ", ")", ")"),
  hV = 1e-12;
function tx(e) {
  return ((e = Math.exp(e)) + 1 / e) / 2;
}
function pV(e) {
  return ((e = Math.exp(e)) - 1 / e) / 2;
}
function mV(e) {
  return ((e = Math.exp(2 * e)) - 1) / (e + 1);
}
const gV = (function e(t, n, r) {
  function i(o, s) {
    var a = o[0],
      u = o[1],
      l = o[2],
      c = s[0],
      f = s[1],
      d = s[2],
      h = c - a,
      v = f - u,
      p = h * h + v * v,
      y,
      m;
    if (p < hV)
      (m = Math.log(d / l) / t),
        (y = function (C) {
          return [a + C * h, u + C * v, l * Math.exp(t * C * m)];
        });
    else {
      var g = Math.sqrt(p),
        w = (d * d - l * l + r * p) / (2 * l * n * g),
        x = (d * d - l * l - r * p) / (2 * d * n * g),
        b = Math.log(Math.sqrt(w * w + 1) - w),
        E = Math.log(Math.sqrt(x * x + 1) - x);
      (m = (E - b) / t),
        (y = function (C) {
          var T = C * m,
            P = tx(b),
            M = (l / (n * g)) * (P * mV(t * T + b) - pV(b));
          return [a + M * h, u + M * v, (l * P) / tx(t * T + b)];
        });
    }
    return (y.duration = (m * 1e3 * t) / Math.SQRT2), y;
  }
  return (
    (i.rho = function (o) {
      var s = Math.max(0.001, +o),
        a = s * s,
        u = a * a;
      return e(s, a, u);
    }),
    i
  );
})(Math.SQRT2, 2, 4);
var ho = 0,
  ns = 0,
  Uo = 0,
  iA = 1e3,
  al,
  rs,
  ul = 0,
  li = 0,
  Gl = 0,
  Xs = typeof performance == "object" && performance.now ? performance : Date,
  oA =
    typeof window == "object" && window.requestAnimationFrame
      ? window.requestAnimationFrame.bind(window)
      : function (e) {
          setTimeout(e, 17);
        };
function o0() {
  return li || (oA(vV), (li = Xs.now() + Gl));
}
function vV() {
  li = 0;
}
function ll() {
  this._call = this._time = this._next = null;
}
ll.prototype = sA.prototype = {
  constructor: ll,
  restart: function (e, t, n) {
    if (typeof e != "function") throw new TypeError("callback is not a function");
    (n = (n == null ? o0() : +n) + (t == null ? 0 : +t)),
      !this._next && rs !== this && (rs ? (rs._next = this) : (al = this), (rs = this)),
      (this._call = e),
      (this._time = n),
      Rv();
  },
  stop: function () {
    this._call && ((this._call = null), (this._time = 1 / 0), Rv());
  },
};
function sA(e, t, n) {
  var r = new ll();
  return r.restart(e, t, n), r;
}
function yV() {
  o0(), ++ho;
  for (var e = al, t; e; ) (t = li - e._time) >= 0 && e._call.call(void 0, t), (e = e._next);
  --ho;
}
function nx() {
  (li = (ul = Xs.now()) + Gl), (ho = ns = 0);
  try {
    yV();
  } finally {
    (ho = 0), xV(), (li = 0);
  }
}
function wV() {
  var e = Xs.now(),
    t = e - ul;
  t > iA && ((Gl -= t), (ul = e));
}
function xV() {
  for (var e, t = al, n, r = 1 / 0; t; )
    t._call
      ? (r > t._time && (r = t._time), (e = t), (t = t._next))
      : ((n = t._next), (t._next = null), (t = e ? (e._next = n) : (al = n)));
  (rs = e), Rv(r);
}
function Rv(e) {
  if (!ho) {
    ns && (ns = clearTimeout(ns));
    var t = e - li;
    t > 24
      ? (e < 1 / 0 && (ns = setTimeout(nx, e - Xs.now() - Gl)), Uo && (Uo = clearInterval(Uo)))
      : (Uo || ((ul = Xs.now()), (Uo = setInterval(wV, iA))), (ho = 1), oA(nx));
  }
}
function rx(e, t, n) {
  var r = new ll();
  return (
    (t = t == null ? 0 : +t),
    r.restart(
      (i) => {
        r.stop(), e(i + t);
      },
      t,
      n,
    ),
    r
  );
}
var _V = Ul("start", "end", "cancel", "interrupt"),
  bV = [],
  aA = 0,
  ix = 1,
  Pv = 2,
  Su = 3,
  ox = 4,
  Av = 5,
  Eu = 6;
function Wl(e, t, n, r, i, o) {
  var s = e.__transition;
  if (!s) e.__transition = {};
  else if (n in s) return;
  SV(e, n, {
    name: t,
    index: r,
    group: i,
    on: _V,
    tween: bV,
    time: o.time,
    delay: o.delay,
    duration: o.duration,
    ease: o.ease,
    timer: null,
    state: aA,
  });
}
function s0(e, t) {
  var n = rn(e, t);
  if (n.state > aA) throw new Error("too late; already scheduled");
  return n;
}
function Sn(e, t) {
  var n = rn(e, t);
  if (n.state > Su) throw new Error("too late; already running");
  return n;
}
function rn(e, t) {
  var n = e.__transition;
  if (!n || !(n = n[t])) throw new Error("transition not found");
  return n;
}
function SV(e, t, n) {
  var r = e.__transition,
    i;
  (r[t] = n), (n.timer = sA(o, 0, n.time));
  function o(l) {
    (n.state = ix), n.timer.restart(s, n.delay, n.time), n.delay <= l && s(l - n.delay);
  }
  function s(l) {
    var c, f, d, h;
    if (n.state !== ix) return u();
    for (c in r)
      if (((h = r[c]), h.name === n.name)) {
        if (h.state === Su) return rx(s);
        h.state === ox
          ? ((h.state = Eu),
            h.timer.stop(),
            h.on.call("interrupt", e, e.__data__, h.index, h.group),
            delete r[c])
          : +c < t &&
            ((h.state = Eu),
            h.timer.stop(),
            h.on.call("cancel", e, e.__data__, h.index, h.group),
            delete r[c]);
      }
    if (
      (rx(function () {
        n.state === Su && ((n.state = ox), n.timer.restart(a, n.delay, n.time), a(l));
      }),
      (n.state = Pv),
      n.on.call("start", e, e.__data__, n.index, n.group),
      n.state === Pv)
    ) {
      for (n.state = Su, i = new Array((d = n.tween.length)), c = 0, f = -1; c < d; ++c)
        (h = n.tween[c].value.call(e, e.__data__, n.index, n.group)) && (i[++f] = h);
      i.length = f + 1;
    }
  }
  function a(l) {
    for (
      var c =
          l < n.duration
            ? n.ease.call(null, l / n.duration)
            : (n.timer.restart(u), (n.state = Av), 1),
        f = -1,
        d = i.length;
      ++f < d;

    )
      i[f].call(e, c);
    n.state === Av && (n.on.call("end", e, e.__data__, n.index, n.group), u());
  }
  function u() {
    (n.state = Eu), n.timer.stop(), delete r[t];
    for (var l in r) return;
    delete e.__transition;
  }
}
function Cu(e, t) {
  var n = e.__transition,
    r,
    i,
    o = !0,
    s;
  if (n) {
    t = t == null ? null : t + "";
    for (s in n) {
      if ((r = n[s]).name !== t) {
        o = !1;
        continue;
      }
      (i = r.state > Pv && r.state < Av),
        (r.state = Eu),
        r.timer.stop(),
        r.on.call(i ? "interrupt" : "cancel", e, e.__data__, r.index, r.group),
        delete n[s];
    }
    o && delete e.__transition;
  }
}
function EV(e) {
  return this.each(function () {
    Cu(this, e);
  });
}
function CV(e, t) {
  var n, r;
  return function () {
    var i = Sn(this, e),
      o = i.tween;
    if (o !== n) {
      r = n = o;
      for (var s = 0, a = r.length; s < a; ++s)
        if (r[s].name === t) {
          (r = r.slice()), r.splice(s, 1);
          break;
        }
    }
    i.tween = r;
  };
}
function TV(e, t, n) {
  var r, i;
  if (typeof n != "function") throw new Error();
  return function () {
    var o = Sn(this, e),
      s = o.tween;
    if (s !== r) {
      i = (r = s).slice();
      for (var a = { name: t, value: n }, u = 0, l = i.length; u < l; ++u)
        if (i[u].name === t) {
          i[u] = a;
          break;
        }
      u === l && i.push(a);
    }
    o.tween = i;
  };
}
function kV(e, t) {
  var n = this._id;
  if (((e += ""), arguments.length < 2)) {
    for (var r = rn(this.node(), n).tween, i = 0, o = r.length, s; i < o; ++i)
      if ((s = r[i]).name === e) return s.value;
    return null;
  }
  return this.each((t == null ? CV : TV)(n, e, t));
}
function a0(e, t, n) {
  var r = e._id;
  return (
    e.each(function () {
      var i = Sn(this, r);
      (i.value || (i.value = {}))[t] = n.apply(this, arguments);
    }),
    function (i) {
      return rn(i, r).value[t];
    }
  );
}
function uA(e, t) {
  var n;
  return (typeof t == "number" ? fr : t instanceof Ys ? J1 : (n = Ys(t)) ? ((t = n), J1) : uV)(
    e,
    t,
  );
}
function RV(e) {
  return function () {
    this.removeAttribute(e);
  };
}
function PV(e) {
  return function () {
    this.removeAttributeNS(e.space, e.local);
  };
}
function AV(e, t, n) {
  var r,
    i = n + "",
    o;
  return function () {
    var s = this.getAttribute(e);
    return s === i ? null : s === r ? o : (o = t((r = s), n));
  };
}
function NV(e, t, n) {
  var r,
    i = n + "",
    o;
  return function () {
    var s = this.getAttributeNS(e.space, e.local);
    return s === i ? null : s === r ? o : (o = t((r = s), n));
  };
}
function MV(e, t, n) {
  var r, i, o;
  return function () {
    var s,
      a = n(this),
      u;
    return a == null
      ? void this.removeAttribute(e)
      : ((s = this.getAttribute(e)),
        (u = a + ""),
        s === u ? null : s === r && u === i ? o : ((i = u), (o = t((r = s), a))));
  };
}
function IV(e, t, n) {
  var r, i, o;
  return function () {
    var s,
      a = n(this),
      u;
    return a == null
      ? void this.removeAttributeNS(e.space, e.local)
      : ((s = this.getAttributeNS(e.space, e.local)),
        (u = a + ""),
        s === u ? null : s === r && u === i ? o : ((i = u), (o = t((r = s), a))));
  };
}
function DV(e, t) {
  var n = Hl(e),
    r = n === "transform" ? dV : uA;
  return this.attrTween(
    e,
    typeof t == "function"
      ? (n.local ? IV : MV)(n, r, a0(this, "attr." + e, t))
      : t == null
        ? (n.local ? PV : RV)(n)
        : (n.local ? NV : AV)(n, r, t),
  );
}
function OV(e, t) {
  return function (n) {
    this.setAttribute(e, t.call(this, n));
  };
}
function LV(e, t) {
  return function (n) {
    this.setAttributeNS(e.space, e.local, t.call(this, n));
  };
}
function FV(e, t) {
  var n, r;
  function i() {
    var o = t.apply(this, arguments);
    return o !== r && (n = (r = o) && LV(e, o)), n;
  }
  return (i._value = t), i;
}
function jV(e, t) {
  var n, r;
  function i() {
    var o = t.apply(this, arguments);
    return o !== r && (n = (r = o) && OV(e, o)), n;
  }
  return (i._value = t), i;
}
function VV(e, t) {
  var n = "attr." + e;
  if (arguments.length < 2) return (n = this.tween(n)) && n._value;
  if (t == null) return this.tween(n, null);
  if (typeof t != "function") throw new Error();
  var r = Hl(e);
  return this.tween(n, (r.local ? FV : jV)(r, t));
}
function qV(e, t) {
  return function () {
    s0(this, e).delay = +t.apply(this, arguments);
  };
}
function $V(e, t) {
  return (
    (t = +t),
    function () {
      s0(this, e).delay = t;
    }
  );
}
function zV(e) {
  var t = this._id;
  return arguments.length
    ? this.each((typeof e == "function" ? qV : $V)(t, e))
    : rn(this.node(), t).delay;
}
function BV(e, t) {
  return function () {
    Sn(this, e).duration = +t.apply(this, arguments);
  };
}
function UV(e, t) {
  return (
    (t = +t),
    function () {
      Sn(this, e).duration = t;
    }
  );
}
function HV(e) {
  var t = this._id;
  return arguments.length
    ? this.each((typeof e == "function" ? BV : UV)(t, e))
    : rn(this.node(), t).duration;
}
function GV(e, t) {
  if (typeof t != "function") throw new Error();
  return function () {
    Sn(this, e).ease = t;
  };
}
function WV(e) {
  var t = this._id;
  return arguments.length ? this.each(GV(t, e)) : rn(this.node(), t).ease;
}
function KV(e, t) {
  return function () {
    var n = t.apply(this, arguments);
    if (typeof n != "function") throw new Error();
    Sn(this, e).ease = n;
  };
}
function YV(e) {
  if (typeof e != "function") throw new Error();
  return this.each(KV(this._id, e));
}
function XV(e) {
  typeof e != "function" && (e = qP(e));
  for (var t = this._groups, n = t.length, r = new Array(n), i = 0; i < n; ++i)
    for (var o = t[i], s = o.length, a = (r[i] = []), u, l = 0; l < s; ++l)
      (u = o[l]) && e.call(u, u.__data__, l, o) && a.push(u);
  return new Wn(r, this._parents, this._name, this._id);
}
function ZV(e) {
  if (e._id !== this._id) throw new Error();
  for (
    var t = this._groups,
      n = e._groups,
      r = t.length,
      i = n.length,
      o = Math.min(r, i),
      s = new Array(r),
      a = 0;
    a < o;
    ++a
  )
    for (var u = t[a], l = n[a], c = u.length, f = (s[a] = new Array(c)), d, h = 0; h < c; ++h)
      (d = u[h] || l[h]) && (f[h] = d);
  for (; a < r; ++a) s[a] = t[a];
  return new Wn(s, this._parents, this._name, this._id);
}
function QV(e) {
  return (e + "")
    .trim()
    .split(/^|\s+/)
    .every(function (t) {
      var n = t.indexOf(".");
      return n >= 0 && (t = t.slice(0, n)), !t || t === "start";
    });
}
function JV(e, t, n) {
  var r,
    i,
    o = QV(t) ? s0 : Sn;
  return function () {
    var s = o(this, e),
      a = s.on;
    a !== r && (i = (r = a).copy()).on(t, n), (s.on = i);
  };
}
function eq(e, t) {
  var n = this._id;
  return arguments.length < 2 ? rn(this.node(), n).on.on(e) : this.each(JV(n, e, t));
}
function tq(e) {
  return function () {
    var t = this.parentNode;
    for (var n in this.__transition) if (+n !== e) return;
    t && t.removeChild(this);
  };
}
function nq() {
  return this.on("end.remove", tq(this._id));
}
function rq(e) {
  var t = this._name,
    n = this._id;
  typeof e != "function" && (e = n0(e));
  for (var r = this._groups, i = r.length, o = new Array(i), s = 0; s < i; ++s)
    for (var a = r[s], u = a.length, l = (o[s] = new Array(u)), c, f, d = 0; d < u; ++d)
      (c = a[d]) &&
        (f = e.call(c, c.__data__, d, a)) &&
        ("__data__" in c && (f.__data__ = c.__data__), (l[d] = f), Wl(l[d], t, n, d, l, rn(c, n)));
  return new Wn(o, this._parents, t, n);
}
function iq(e) {
  var t = this._name,
    n = this._id;
  typeof e != "function" && (e = VP(e));
  for (var r = this._groups, i = r.length, o = [], s = [], a = 0; a < i; ++a)
    for (var u = r[a], l = u.length, c, f = 0; f < l; ++f)
      if ((c = u[f])) {
        for (var d = e.call(c, c.__data__, f, u), h, v = rn(c, n), p = 0, y = d.length; p < y; ++p)
          (h = d[p]) && Wl(h, t, n, p, d, v);
        o.push(d), s.push(c);
      }
  return new Wn(o, s, t, n);
}
var oq = ca.prototype.constructor;
function sq() {
  return new oq(this._groups, this._parents);
}
function aq(e, t) {
  var n, r, i;
  return function () {
    var o = fo(this, e),
      s = (this.style.removeProperty(e), fo(this, e));
    return o === s ? null : o === n && s === r ? i : (i = t((n = o), (r = s)));
  };
}
function lA(e) {
  return function () {
    this.style.removeProperty(e);
  };
}
function uq(e, t, n) {
  var r,
    i = n + "",
    o;
  return function () {
    var s = fo(this, e);
    return s === i ? null : s === r ? o : (o = t((r = s), n));
  };
}
function lq(e, t, n) {
  var r, i, o;
  return function () {
    var s = fo(this, e),
      a = n(this),
      u = a + "";
    return (
      a == null && (u = a = (this.style.removeProperty(e), fo(this, e))),
      s === u ? null : s === r && u === i ? o : ((i = u), (o = t((r = s), a)))
    );
  };
}
function cq(e, t) {
  var n,
    r,
    i,
    o = "style." + t,
    s = "end." + o,
    a;
  return function () {
    var u = Sn(this, e),
      l = u.on,
      c = u.value[o] == null ? a || (a = lA(t)) : void 0;
    (l !== n || i !== c) && (r = (n = l).copy()).on(s, (i = c)), (u.on = r);
  };
}
function fq(e, t, n) {
  var r = (e += "") == "transform" ? fV : uA;
  return t == null
    ? this.styleTween(e, aq(e, r)).on("end.style." + e, lA(e))
    : typeof t == "function"
      ? this.styleTween(e, lq(e, r, a0(this, "style." + e, t))).each(cq(this._id, e))
      : this.styleTween(e, uq(e, r, t), n).on("end.style." + e, null);
}
function dq(e, t, n) {
  return function (r) {
    this.style.setProperty(e, t.call(this, r), n);
  };
}
function hq(e, t, n) {
  var r, i;
  function o() {
    var s = t.apply(this, arguments);
    return s !== i && (r = (i = s) && dq(e, s, n)), r;
  }
  return (o._value = t), o;
}
function pq(e, t, n) {
  var r = "style." + (e += "");
  if (arguments.length < 2) return (r = this.tween(r)) && r._value;
  if (t == null) return this.tween(r, null);
  if (typeof t != "function") throw new Error();
  return this.tween(r, hq(e, t, n ?? ""));
}
function mq(e) {
  return function () {
    this.textContent = e;
  };
}
function gq(e) {
  return function () {
    var t = e(this);
    this.textContent = t ?? "";
  };
}
function vq(e) {
  return this.tween(
    "text",
    typeof e == "function" ? gq(a0(this, "text", e)) : mq(e == null ? "" : e + ""),
  );
}
function yq(e) {
  return function (t) {
    this.textContent = e.call(this, t);
  };
}
function wq(e) {
  var t, n;
  function r() {
    var i = e.apply(this, arguments);
    return i !== n && (t = (n = i) && yq(i)), t;
  }
  return (r._value = e), r;
}
function xq(e) {
  var t = "text";
  if (arguments.length < 1) return (t = this.tween(t)) && t._value;
  if (e == null) return this.tween(t, null);
  if (typeof e != "function") throw new Error();
  return this.tween(t, wq(e));
}
function _q() {
  for (
    var e = this._name, t = this._id, n = cA(), r = this._groups, i = r.length, o = 0;
    o < i;
    ++o
  )
    for (var s = r[o], a = s.length, u, l = 0; l < a; ++l)
      if ((u = s[l])) {
        var c = rn(u, t);
        Wl(u, e, n, l, s, {
          time: c.time + c.delay + c.duration,
          delay: 0,
          duration: c.duration,
          ease: c.ease,
        });
      }
  return new Wn(r, this._parents, e, n);
}
function bq() {
  var e,
    t,
    n = this,
    r = n._id,
    i = n.size();
  return new Promise(function (o, s) {
    var a = { value: s },
      u = {
        value: function () {
          --i === 0 && o();
        },
      };
    n.each(function () {
      var l = Sn(this, r),
        c = l.on;
      c !== e && ((t = (e = c).copy()), t._.cancel.push(a), t._.interrupt.push(a), t._.end.push(u)),
        (l.on = t);
    }),
      i === 0 && o();
  });
}
var Sq = 0;
function Wn(e, t, n, r) {
  (this._groups = e), (this._parents = t), (this._name = n), (this._id = r);
}
function cA() {
  return ++Sq;
}
var Rn = ca.prototype;
Wn.prototype = {
  constructor: Wn,
  select: rq,
  selectAll: iq,
  selectChild: Rn.selectChild,
  selectChildren: Rn.selectChildren,
  filter: XV,
  merge: ZV,
  selection: sq,
  transition: _q,
  call: Rn.call,
  nodes: Rn.nodes,
  node: Rn.node,
  size: Rn.size,
  empty: Rn.empty,
  each: Rn.each,
  on: eq,
  attr: DV,
  attrTween: VV,
  style: fq,
  styleTween: pq,
  text: vq,
  textTween: xq,
  remove: nq,
  tween: kV,
  delay: zV,
  duration: HV,
  ease: WV,
  easeVarying: YV,
  end: bq,
  [Symbol.iterator]: Rn[Symbol.iterator],
};
function Eq(e) {
  return ((e *= 2) <= 1 ? e * e * e : (e -= 2) * e * e + 2) / 2;
}
var Cq = { time: null, delay: 0, duration: 250, ease: Eq };
function Tq(e, t) {
  for (var n; !(n = e.__transition) || !(n = n[t]); )
    if (!(e = e.parentNode)) throw new Error(`transition ${t} not found`);
  return n;
}
function kq(e) {
  var t, n;
  e instanceof Wn
    ? ((t = e._id), (e = e._name))
    : ((t = cA()), ((n = Cq).time = o0()), (e = e == null ? null : e + ""));
  for (var r = this._groups, i = r.length, o = 0; o < i; ++o)
    for (var s = r[o], a = s.length, u, l = 0; l < a; ++l)
      (u = s[l]) && Wl(u, e, t, l, s, n || Tq(u, t));
  return new Wn(r, this._parents, e, t);
}
ca.prototype.interrupt = EV;
ca.prototype.transition = kq;
const Ya = (e) => () => e;
function Rq(e, { sourceEvent: t, target: n, transform: r, dispatch: i }) {
  Object.defineProperties(this, {
    type: { value: e, enumerable: !0, configurable: !0 },
    sourceEvent: { value: t, enumerable: !0, configurable: !0 },
    target: { value: n, enumerable: !0, configurable: !0 },
    transform: { value: r, enumerable: !0, configurable: !0 },
    _: { value: i },
  });
}
function Ln(e, t, n) {
  (this.k = e), (this.x = t), (this.y = n);
}
Ln.prototype = {
  constructor: Ln,
  scale: function (e) {
    return e === 1 ? this : new Ln(this.k * e, this.x, this.y);
  },
  translate: function (e, t) {
    return (e === 0) & (t === 0) ? this : new Ln(this.k, this.x + this.k * e, this.y + this.k * t);
  },
  apply: function (e) {
    return [e[0] * this.k + this.x, e[1] * this.k + this.y];
  },
  applyX: function (e) {
    return e * this.k + this.x;
  },
  applyY: function (e) {
    return e * this.k + this.y;
  },
  invert: function (e) {
    return [(e[0] - this.x) / this.k, (e[1] - this.y) / this.k];
  },
  invertX: function (e) {
    return (e - this.x) / this.k;
  },
  invertY: function (e) {
    return (e - this.y) / this.k;
  },
  rescaleX: function (e) {
    return e.copy().domain(e.range().map(this.invertX, this).map(e.invert, e));
  },
  rescaleY: function (e) {
    return e.copy().domain(e.range().map(this.invertY, this).map(e.invert, e));
  },
  toString: function () {
    return "translate(" + this.x + "," + this.y + ") scale(" + this.k + ")";
  },
};
var qn = new Ln(1, 0, 0);
Ln.prototype;
function uf(e) {
  e.stopImmediatePropagation();
}
function Ho(e) {
  e.preventDefault(), e.stopImmediatePropagation();
}
function Pq(e) {
  return (!e.ctrlKey || e.type === "wheel") && !e.button;
}
function Aq() {
  var e = this;
  return e instanceof SVGElement
    ? ((e = e.ownerSVGElement || e),
      e.hasAttribute("viewBox")
        ? ((e = e.viewBox.baseVal),
          [
            [e.x, e.y],
            [e.x + e.width, e.y + e.height],
          ])
        : [
            [0, 0],
            [e.width.baseVal.value, e.height.baseVal.value],
          ])
    : [
        [0, 0],
        [e.clientWidth, e.clientHeight],
      ];
}
function sx() {
  return this.__zoom || qn;
}
function Nq(e) {
  return -e.deltaY * (e.deltaMode === 1 ? 0.05 : e.deltaMode ? 1 : 0.002) * (e.ctrlKey ? 10 : 1);
}
function Mq() {
  return navigator.maxTouchPoints || "ontouchstart" in this;
}
function Iq(e, t, n) {
  var r = e.invertX(t[0][0]) - n[0][0],
    i = e.invertX(t[1][0]) - n[1][0],
    o = e.invertY(t[0][1]) - n[0][1],
    s = e.invertY(t[1][1]) - n[1][1];
  return e.translate(
    i > r ? (r + i) / 2 : Math.min(0, r) || Math.max(0, i),
    s > o ? (o + s) / 2 : Math.min(0, o) || Math.max(0, s),
  );
}
function fA() {
  var e = Pq,
    t = Aq,
    n = Iq,
    r = Nq,
    i = Mq,
    o = [0, 1 / 0],
    s = [
      [-1 / 0, -1 / 0],
      [1 / 0, 1 / 0],
    ],
    a = 250,
    u = gV,
    l = Ul("start", "zoom", "end"),
    c,
    f,
    d,
    h = 500,
    v = 150,
    p = 0,
    y = 10;
  function m(S) {
    S.property("__zoom", sx)
      .on("wheel.zoom", T, { passive: !1 })
      .on("mousedown.zoom", P)
      .on("dblclick.zoom", M)
      .filter(i)
      .on("touchstart.zoom", I)
      .on("touchmove.zoom", j)
      .on("touchend.zoom touchcancel.zoom", q)
      .style("-webkit-tap-highlight-color", "rgba(0,0,0,0)");
  }
  (m.transform = function (S, O, A, F) {
    var N = S.selection ? S.selection() : S;
    N.property("__zoom", sx),
      S !== N
        ? b(S, O, A, F)
        : N.interrupt().each(function () {
            E(this, arguments)
              .event(F)
              .start()
              .zoom(null, typeof O == "function" ? O.apply(this, arguments) : O)
              .end();
          });
  }),
    (m.scaleBy = function (S, O, A, F) {
      m.scaleTo(
        S,
        function () {
          var N = this.__zoom.k,
            k = typeof O == "function" ? O.apply(this, arguments) : O;
          return N * k;
        },
        A,
        F,
      );
    }),
    (m.scaleTo = function (S, O, A, F) {
      m.transform(
        S,
        function () {
          var N = t.apply(this, arguments),
            k = this.__zoom,
            D = A == null ? x(N) : typeof A == "function" ? A.apply(this, arguments) : A,
            V = k.invert(D),
            $ = typeof O == "function" ? O.apply(this, arguments) : O;
          return n(w(g(k, $), D, V), N, s);
        },
        A,
        F,
      );
    }),
    (m.translateBy = function (S, O, A, F) {
      m.transform(
        S,
        function () {
          return n(
            this.__zoom.translate(
              typeof O == "function" ? O.apply(this, arguments) : O,
              typeof A == "function" ? A.apply(this, arguments) : A,
            ),
            t.apply(this, arguments),
            s,
          );
        },
        null,
        F,
      );
    }),
    (m.translateTo = function (S, O, A, F, N) {
      m.transform(
        S,
        function () {
          var k = t.apply(this, arguments),
            D = this.__zoom,
            V = F == null ? x(k) : typeof F == "function" ? F.apply(this, arguments) : F;
          return n(
            qn
              .translate(V[0], V[1])
              .scale(D.k)
              .translate(
                typeof O == "function" ? -O.apply(this, arguments) : -O,
                typeof A == "function" ? -A.apply(this, arguments) : -A,
              ),
            k,
            s,
          );
        },
        F,
        N,
      );
    });
  function g(S, O) {
    return (O = Math.max(o[0], Math.min(o[1], O))), O === S.k ? S : new Ln(O, S.x, S.y);
  }
  function w(S, O, A) {
    var F = O[0] - A[0] * S.k,
      N = O[1] - A[1] * S.k;
    return F === S.x && N === S.y ? S : new Ln(S.k, F, N);
  }
  function x(S) {
    return [(+S[0][0] + +S[1][0]) / 2, (+S[0][1] + +S[1][1]) / 2];
  }
  function b(S, O, A, F) {
    S.on("start.zoom", function () {
      E(this, arguments).event(F).start();
    })
      .on("interrupt.zoom end.zoom", function () {
        E(this, arguments).event(F).end();
      })
      .tween("zoom", function () {
        var N = this,
          k = arguments,
          D = E(N, k).event(F),
          V = t.apply(N, k),
          $ = A == null ? x(V) : typeof A == "function" ? A.apply(N, k) : A,
          U = Math.max(V[1][0] - V[0][0], V[1][1] - V[0][1]),
          B = N.__zoom,
          W = typeof O == "function" ? O.apply(N, k) : O,
          X = u(B.invert($).concat(U / B.k), W.invert($).concat(U / W.k));
        return function (ee) {
          if (ee === 1) ee = W;
          else {
            var ue = X(ee),
              se = U / ue[2];
            ee = new Ln(se, $[0] - ue[0] * se, $[1] - ue[1] * se);
          }
          D.zoom(null, ee);
        };
      });
  }
  function E(S, O, A) {
    return (!A && S.__zooming) || new C(S, O);
  }
  function C(S, O) {
    (this.that = S),
      (this.args = O),
      (this.active = 0),
      (this.sourceEvent = null),
      (this.extent = t.apply(S, O)),
      (this.taps = 0);
  }
  C.prototype = {
    event: function (S) {
      return S && (this.sourceEvent = S), this;
    },
    start: function () {
      return ++this.active === 1 && ((this.that.__zooming = this), this.emit("start")), this;
    },
    zoom: function (S, O) {
      return (
        this.mouse && S !== "mouse" && (this.mouse[1] = O.invert(this.mouse[0])),
        this.touch0 && S !== "touch" && (this.touch0[1] = O.invert(this.touch0[0])),
        this.touch1 && S !== "touch" && (this.touch1[1] = O.invert(this.touch1[0])),
        (this.that.__zoom = O),
        this.emit("zoom"),
        this
      );
    },
    end: function () {
      return --this.active === 0 && (delete this.that.__zooming, this.emit("end")), this;
    },
    emit: function (S) {
      var O = Ot(this.that).datum();
      l.call(
        S,
        this.that,
        new Rq(S, {
          sourceEvent: this.sourceEvent,
          target: m,
          transform: this.that.__zoom,
          dispatch: l,
        }),
        O,
      );
    },
  };
  function T(S, ...O) {
    if (!e.apply(this, arguments)) return;
    var A = E(this, O).event(S),
      F = this.__zoom,
      N = Math.max(o[0], Math.min(o[1], F.k * Math.pow(2, r.apply(this, arguments)))),
      k = Xt(S);
    if (A.wheel)
      (A.mouse[0][0] !== k[0] || A.mouse[0][1] !== k[1]) &&
        (A.mouse[1] = F.invert((A.mouse[0] = k))),
        clearTimeout(A.wheel);
    else {
      if (F.k === N) return;
      (A.mouse = [k, F.invert(k)]), Cu(this), A.start();
    }
    Ho(S),
      (A.wheel = setTimeout(D, v)),
      A.zoom("mouse", n(w(g(F, N), A.mouse[0], A.mouse[1]), A.extent, s));
    function D() {
      (A.wheel = null), A.end();
    }
  }
  function P(S, ...O) {
    if (d || !e.apply(this, arguments)) return;
    var A = S.currentTarget,
      F = E(this, O, !0).event(S),
      N = Ot(S.view).on("mousemove.zoom", $, !0).on("mouseup.zoom", U, !0),
      k = Xt(S, A),
      D = S.clientX,
      V = S.clientY;
    XP(S.view), uf(S), (F.mouse = [k, this.__zoom.invert(k)]), Cu(this), F.start();
    function $(B) {
      if ((Ho(B), !F.moved)) {
        var W = B.clientX - D,
          X = B.clientY - V;
        F.moved = W * W + X * X > p;
      }
      F.event(B).zoom(
        "mouse",
        n(w(F.that.__zoom, (F.mouse[0] = Xt(B, A)), F.mouse[1]), F.extent, s),
      );
    }
    function U(B) {
      N.on("mousemove.zoom mouseup.zoom", null), ZP(B.view, F.moved), Ho(B), F.event(B).end();
    }
  }
  function M(S, ...O) {
    if (e.apply(this, arguments)) {
      var A = this.__zoom,
        F = Xt(S.changedTouches ? S.changedTouches[0] : S, this),
        N = A.invert(F),
        k = A.k * (S.shiftKey ? 0.5 : 2),
        D = n(w(g(A, k), F, N), t.apply(this, O), s);
      Ho(S),
        a > 0
          ? Ot(this).transition().duration(a).call(b, D, F, S)
          : Ot(this).call(m.transform, D, F, S);
    }
  }
  function I(S, ...O) {
    if (e.apply(this, arguments)) {
      var A = S.touches,
        F = A.length,
        N = E(this, O, S.changedTouches.length === F).event(S),
        k,
        D,
        V,
        $;
      for (uf(S), D = 0; D < F; ++D)
        (V = A[D]),
          ($ = Xt(V, this)),
          ($ = [$, this.__zoom.invert($), V.identifier]),
          N.touch0
            ? !N.touch1 && N.touch0[2] !== $[2] && ((N.touch1 = $), (N.taps = 0))
            : ((N.touch0 = $), (k = !0), (N.taps = 1 + !!c));
      c && (c = clearTimeout(c)),
        k &&
          (N.taps < 2 &&
            ((f = $[0]),
            (c = setTimeout(function () {
              c = null;
            }, h))),
          Cu(this),
          N.start());
    }
  }
  function j(S, ...O) {
    if (this.__zooming) {
      var A = E(this, O).event(S),
        F = S.changedTouches,
        N = F.length,
        k,
        D,
        V,
        $;
      for (Ho(S), k = 0; k < N; ++k)
        (D = F[k]),
          (V = Xt(D, this)),
          A.touch0 && A.touch0[2] === D.identifier
            ? (A.touch0[0] = V)
            : A.touch1 && A.touch1[2] === D.identifier && (A.touch1[0] = V);
      if (((D = A.that.__zoom), A.touch1)) {
        var U = A.touch0[0],
          B = A.touch0[1],
          W = A.touch1[0],
          X = A.touch1[1],
          ee = (ee = W[0] - U[0]) * ee + (ee = W[1] - U[1]) * ee,
          ue = (ue = X[0] - B[0]) * ue + (ue = X[1] - B[1]) * ue;
        (D = g(D, Math.sqrt(ee / ue))),
          (V = [(U[0] + W[0]) / 2, (U[1] + W[1]) / 2]),
          ($ = [(B[0] + X[0]) / 2, (B[1] + X[1]) / 2]);
      } else if (A.touch0) (V = A.touch0[0]), ($ = A.touch0[1]);
      else return;
      A.zoom("touch", n(w(D, V, $), A.extent, s));
    }
  }
  function q(S, ...O) {
    if (this.__zooming) {
      var A = E(this, O).event(S),
        F = S.changedTouches,
        N = F.length,
        k,
        D;
      for (
        uf(S),
          d && clearTimeout(d),
          d = setTimeout(function () {
            d = null;
          }, h),
          k = 0;
        k < N;
        ++k
      )
        (D = F[k]),
          A.touch0 && A.touch0[2] === D.identifier
            ? delete A.touch0
            : A.touch1 && A.touch1[2] === D.identifier && delete A.touch1;
      if ((A.touch1 && !A.touch0 && ((A.touch0 = A.touch1), delete A.touch1), A.touch0))
        A.touch0[1] = this.__zoom.invert(A.touch0[0]);
      else if (
        (A.end(), A.taps === 2 && ((D = Xt(D, this)), Math.hypot(f[0] - D[0], f[1] - D[1]) < y))
      ) {
        var V = Ot(this).on("dblclick.zoom");
        V && V.apply(this, arguments);
      }
    }
  }
  return (
    (m.wheelDelta = function (S) {
      return arguments.length ? ((r = typeof S == "function" ? S : Ya(+S)), m) : r;
    }),
    (m.filter = function (S) {
      return arguments.length ? ((e = typeof S == "function" ? S : Ya(!!S)), m) : e;
    }),
    (m.touchable = function (S) {
      return arguments.length ? ((i = typeof S == "function" ? S : Ya(!!S)), m) : i;
    }),
    (m.extent = function (S) {
      return arguments.length
        ? ((t =
            typeof S == "function"
              ? S
              : Ya([
                  [+S[0][0], +S[0][1]],
                  [+S[1][0], +S[1][1]],
                ])),
          m)
        : t;
    }),
    (m.scaleExtent = function (S) {
      return arguments.length ? ((o[0] = +S[0]), (o[1] = +S[1]), m) : [o[0], o[1]];
    }),
    (m.translateExtent = function (S) {
      return arguments.length
        ? ((s[0][0] = +S[0][0]),
          (s[1][0] = +S[1][0]),
          (s[0][1] = +S[0][1]),
          (s[1][1] = +S[1][1]),
          m)
        : [
            [s[0][0], s[0][1]],
            [s[1][0], s[1][1]],
          ];
    }),
    (m.constrain = function (S) {
      return arguments.length ? ((n = S), m) : n;
    }),
    (m.duration = function (S) {
      return arguments.length ? ((a = +S), m) : a;
    }),
    (m.interpolate = function (S) {
      return arguments.length ? ((u = S), m) : u;
    }),
    (m.on = function () {
      var S = l.on.apply(l, arguments);
      return S === l ? m : S;
    }),
    (m.clickDistance = function (S) {
      return arguments.length ? ((p = (S = +S) * S), m) : Math.sqrt(p);
    }),
    (m.tapDistance = function (S) {
      return arguments.length ? ((y = +S), m) : y;
    }),
    m
  );
}
const Kl = _.createContext(null),
  Dq = Kl.Provider,
  Kn = {
    error001: () =>
      "[React Flow]: Seems like you have not used zustand provider as an ancestor. Help: https://reactflow.dev/error#001",
    error002: () =>
      "It looks like you've created a new nodeTypes or edgeTypes object. If this wasn't on purpose please define the nodeTypes/edgeTypes outside of the component or memoize them.",
    error003: (e) => `Node type "${e}" not found. Using fallback type "default".`,
    error004: () =>
      "The React Flow parent container needs a width and a height to render the graph.",
    error005: () => "Only child nodes can use a parent extent.",
    error006: () => "Can't create edge. An edge needs a source and a target.",
    error007: (e) => `The old edge with id=${e} does not exist.`,
    error009: (e) => `Marker type "${e}" doesn't exist.`,
    error008: (e, t) =>
      `Couldn't create edge for ${e ? "target" : "source"} handle id: "${e ? t.targetHandle : t.sourceHandle}", edge id: ${t.id}.`,
    error010: () =>
      "Handle: No node id found. Make sure to only use a Handle inside a custom Node.",
    error011: (e) => `Edge type "${e}" not found. Using fallback type "default".`,
    error012: (e) =>
      `Node with id "${e}" does not exist, it may have been removed. This can happen when a node is deleted before the "onNodeClick" handler is called.`,
  },
  dA = Kn.error001();
function de(e, t) {
  const n = _.useContext(Kl);
  if (n === null) throw new Error(dA);
  return FP(n, e, t);
}
const Fe = () => {
    const e = _.useContext(Kl);
    if (e === null) throw new Error(dA);
    return _.useMemo(
      () => ({
        getState: e.getState,
        setState: e.setState,
        subscribe: e.subscribe,
        destroy: e.destroy,
      }),
      [e],
    );
  },
  Oq = (e) => (e.userSelectionActive ? "none" : "all");
function u0({ position: e, children: t, className: n, style: r, ...i }) {
  const o = de(Oq),
    s = `${e}`.split("-");
  return L.createElement(
    "div",
    { className: Ze(["react-flow__panel", n, ...s]), style: { ...r, pointerEvents: o }, ...i },
    t,
  );
}
function Lq({ proOptions: e, position: t = "bottom-right" }) {
  return e != null && e.hideAttribution
    ? null
    : L.createElement(
        u0,
        {
          position: t,
          className: "react-flow__attribution",
          "data-message":
            "Please only hide this attribution when you are subscribed to React Flow Pro: https://reactflow.dev/pro",
        },
        L.createElement(
          "a",
          {
            href: "https://reactflow.dev",
            target: "_blank",
            rel: "noopener noreferrer",
            "aria-label": "React Flow attribution",
          },
          "React Flow",
        ),
      );
}
const Fq = ({
  x: e,
  y: t,
  label: n,
  labelStyle: r = {},
  labelShowBg: i = !0,
  labelBgStyle: o = {},
  labelBgPadding: s = [2, 4],
  labelBgBorderRadius: a = 2,
  children: u,
  className: l,
  ...c
}) => {
  const f = _.useRef(null),
    [d, h] = _.useState({ x: 0, y: 0, width: 0, height: 0 }),
    v = Ze(["react-flow__edge-textwrapper", l]);
  return (
    _.useEffect(() => {
      if (f.current) {
        const p = f.current.getBBox();
        h({ x: p.x, y: p.y, width: p.width, height: p.height });
      }
    }, [n]),
    typeof n > "u" || !n
      ? null
      : L.createElement(
          "g",
          {
            transform: `translate(${e - d.width / 2} ${t - d.height / 2})`,
            className: v,
            visibility: d.width ? "visible" : "hidden",
            ...c,
          },
          i &&
            L.createElement("rect", {
              width: d.width + 2 * s[0],
              x: -s[0],
              y: -s[1],
              height: d.height + 2 * s[1],
              className: "react-flow__edge-textbg",
              style: o,
              rx: a,
              ry: a,
            }),
          L.createElement(
            "text",
            { className: "react-flow__edge-text", y: d.height / 2, dy: "0.3em", ref: f, style: r },
            n,
          ),
          u,
        )
  );
};
var jq = _.memo(Fq);
const l0 = (e) => ({ width: e.offsetWidth, height: e.offsetHeight }),
  po = (e, t = 0, n = 1) => Math.min(Math.max(e, t), n),
  c0 = (e = { x: 0, y: 0 }, t) => ({ x: po(e.x, t[0][0], t[1][0]), y: po(e.y, t[0][1], t[1][1]) }),
  ax = (e, t, n) =>
    e < t ? po(Math.abs(e - t), 1, 50) / 50 : e > n ? -po(Math.abs(e - n), 1, 50) / 50 : 0,
  hA = (e, t) => {
    const n = ax(e.x, 35, t.width - 35) * 20,
      r = ax(e.y, 35, t.height - 35) * 20;
    return [n, r];
  },
  pA = (e) => {
    var t;
    return (
      ((t = e.getRootNode) == null ? void 0 : t.call(e)) ||
      (window == null ? void 0 : window.document)
    );
  },
  mA = (e, t) => ({
    x: Math.min(e.x, t.x),
    y: Math.min(e.y, t.y),
    x2: Math.max(e.x2, t.x2),
    y2: Math.max(e.y2, t.y2),
  }),
  Zs = ({ x: e, y: t, width: n, height: r }) => ({ x: e, y: t, x2: e + n, y2: t + r }),
  gA = ({ x: e, y: t, x2: n, y2: r }) => ({ x: e, y: t, width: n - e, height: r - t }),
  ux = (e) => ({
    ...(e.positionAbsolute || { x: 0, y: 0 }),
    width: e.width || 0,
    height: e.height || 0,
  }),
  Vq = (e, t) => gA(mA(Zs(e), Zs(t))),
  Nv = (e, t) => {
    const n = Math.max(0, Math.min(e.x + e.width, t.x + t.width) - Math.max(e.x, t.x)),
      r = Math.max(0, Math.min(e.y + e.height, t.y + t.height) - Math.max(e.y, t.y));
    return Math.ceil(n * r);
  },
  qq = (e) => Ft(e.width) && Ft(e.height) && Ft(e.x) && Ft(e.y),
  Ft = (e) => !isNaN(e) && isFinite(e),
  ke = Symbol.for("internals"),
  vA = ["Enter", " ", "Escape"],
  $q = (e, t) => {},
  zq = (e) => "nativeEvent" in e;
function Mv(e) {
  var i, o;
  const t = zq(e) ? e.nativeEvent : e,
    n =
      ((o = (i = t.composedPath) == null ? void 0 : i.call(t)) == null ? void 0 : o[0]) || e.target;
  return (
    ["INPUT", "SELECT", "TEXTAREA"].includes(n == null ? void 0 : n.nodeName) ||
    (n == null ? void 0 : n.hasAttribute("contenteditable")) ||
    !!(n != null && n.closest(".nokey"))
  );
}
const yA = (e) => "clientX" in e,
  kr = (e, t) => {
    var o, s;
    const n = yA(e),
      r = n ? e.clientX : (o = e.touches) == null ? void 0 : o[0].clientX,
      i = n ? e.clientY : (s = e.touches) == null ? void 0 : s[0].clientY;
    return {
      x: r - ((t == null ? void 0 : t.left) ?? 0),
      y: i - ((t == null ? void 0 : t.top) ?? 0),
    };
  },
  cl = () => {
    var e;
    return (
      typeof navigator < "u" &&
      ((e = navigator == null ? void 0 : navigator.userAgent) == null
        ? void 0
        : e.indexOf("Mac")) >= 0
    );
  },
  Co = ({
    id: e,
    path: t,
    labelX: n,
    labelY: r,
    label: i,
    labelStyle: o,
    labelShowBg: s,
    labelBgStyle: a,
    labelBgPadding: u,
    labelBgBorderRadius: l,
    style: c,
    markerEnd: f,
    markerStart: d,
    interactionWidth: h = 20,
  }) =>
    L.createElement(
      L.Fragment,
      null,
      L.createElement("path", {
        id: e,
        style: c,
        d: t,
        fill: "none",
        className: "react-flow__edge-path",
        markerEnd: f,
        markerStart: d,
      }),
      h &&
        L.createElement("path", {
          d: t,
          fill: "none",
          strokeOpacity: 0,
          strokeWidth: h,
          className: "react-flow__edge-interaction",
        }),
      i && Ft(n) && Ft(r)
        ? L.createElement(jq, {
            x: n,
            y: r,
            label: i,
            labelStyle: o,
            labelShowBg: s,
            labelBgStyle: a,
            labelBgPadding: u,
            labelBgBorderRadius: l,
          })
        : null,
    );
Co.displayName = "BaseEdge";
function Go(e, t, n) {
  return n === void 0
    ? n
    : (r) => {
        const i = t().edges.find((o) => o.id === e);
        i && n(r, { ...i });
      };
}
function wA({ sourceX: e, sourceY: t, targetX: n, targetY: r }) {
  const i = Math.abs(n - e) / 2,
    o = n < e ? n + i : n - i,
    s = Math.abs(r - t) / 2,
    a = r < t ? r + s : r - s;
  return [o, a, i, s];
}
function xA({
  sourceX: e,
  sourceY: t,
  targetX: n,
  targetY: r,
  sourceControlX: i,
  sourceControlY: o,
  targetControlX: s,
  targetControlY: a,
}) {
  const u = e * 0.125 + i * 0.375 + s * 0.375 + n * 0.125,
    l = t * 0.125 + o * 0.375 + a * 0.375 + r * 0.125,
    c = Math.abs(u - e),
    f = Math.abs(l - t);
  return [u, l, c, f];
}
var ci;
(function (e) {
  (e.Strict = "strict"), (e.Loose = "loose");
})(ci || (ci = {}));
var Xr;
(function (e) {
  (e.Free = "free"), (e.Vertical = "vertical"), (e.Horizontal = "horizontal");
})(Xr || (Xr = {}));
var mo;
(function (e) {
  (e.Partial = "partial"), (e.Full = "full");
})(mo || (mo = {}));
var In;
(function (e) {
  (e.Bezier = "default"),
    (e.Straight = "straight"),
    (e.Step = "step"),
    (e.SmoothStep = "smoothstep"),
    (e.SimpleBezier = "simplebezier");
})(In || (In = {}));
var go;
(function (e) {
  (e.Arrow = "arrow"), (e.ArrowClosed = "arrowclosed");
})(go || (go = {}));
var Y;
(function (e) {
  (e.Left = "left"), (e.Top = "top"), (e.Right = "right"), (e.Bottom = "bottom");
})(Y || (Y = {}));
function lx({ pos: e, x1: t, y1: n, x2: r, y2: i }) {
  return e === Y.Left || e === Y.Right ? [0.5 * (t + r), n] : [t, 0.5 * (n + i)];
}
function _A({
  sourceX: e,
  sourceY: t,
  sourcePosition: n = Y.Bottom,
  targetX: r,
  targetY: i,
  targetPosition: o = Y.Top,
}) {
  const [s, a] = lx({ pos: n, x1: e, y1: t, x2: r, y2: i }),
    [u, l] = lx({ pos: o, x1: r, y1: i, x2: e, y2: t }),
    [c, f, d, h] = xA({
      sourceX: e,
      sourceY: t,
      targetX: r,
      targetY: i,
      sourceControlX: s,
      sourceControlY: a,
      targetControlX: u,
      targetControlY: l,
    });
  return [`M${e},${t} C${s},${a} ${u},${l} ${r},${i}`, c, f, d, h];
}
const f0 = _.memo(
  ({
    sourceX: e,
    sourceY: t,
    targetX: n,
    targetY: r,
    sourcePosition: i = Y.Bottom,
    targetPosition: o = Y.Top,
    label: s,
    labelStyle: a,
    labelShowBg: u,
    labelBgStyle: l,
    labelBgPadding: c,
    labelBgBorderRadius: f,
    style: d,
    markerEnd: h,
    markerStart: v,
    interactionWidth: p,
  }) => {
    const [y, m, g] = _A({
      sourceX: e,
      sourceY: t,
      sourcePosition: i,
      targetX: n,
      targetY: r,
      targetPosition: o,
    });
    return L.createElement(Co, {
      path: y,
      labelX: m,
      labelY: g,
      label: s,
      labelStyle: a,
      labelShowBg: u,
      labelBgStyle: l,
      labelBgPadding: c,
      labelBgBorderRadius: f,
      style: d,
      markerEnd: h,
      markerStart: v,
      interactionWidth: p,
    });
  },
);
f0.displayName = "SimpleBezierEdge";
const cx = {
    [Y.Left]: { x: -1, y: 0 },
    [Y.Right]: { x: 1, y: 0 },
    [Y.Top]: { x: 0, y: -1 },
    [Y.Bottom]: { x: 0, y: 1 },
  },
  Bq = ({ source: e, sourcePosition: t = Y.Bottom, target: n }) =>
    t === Y.Left || t === Y.Right
      ? e.x < n.x
        ? { x: 1, y: 0 }
        : { x: -1, y: 0 }
      : e.y < n.y
        ? { x: 0, y: 1 }
        : { x: 0, y: -1 },
  fx = (e, t) => Math.sqrt(Math.pow(t.x - e.x, 2) + Math.pow(t.y - e.y, 2));
function Uq({
  source: e,
  sourcePosition: t = Y.Bottom,
  target: n,
  targetPosition: r = Y.Top,
  center: i,
  offset: o,
}) {
  const s = cx[t],
    a = cx[r],
    u = { x: e.x + s.x * o, y: e.y + s.y * o },
    l = { x: n.x + a.x * o, y: n.y + a.y * o },
    c = Bq({ source: u, sourcePosition: t, target: l }),
    f = c.x !== 0 ? "x" : "y",
    d = c[f];
  let h = [],
    v,
    p;
  const y = { x: 0, y: 0 },
    m = { x: 0, y: 0 },
    [g, w, x, b] = wA({ sourceX: e.x, sourceY: e.y, targetX: n.x, targetY: n.y });
  if (s[f] * a[f] === -1) {
    (v = i.x ?? g), (p = i.y ?? w);
    const C = [
        { x: v, y: u.y },
        { x: v, y: l.y },
      ],
      T = [
        { x: u.x, y: p },
        { x: l.x, y: p },
      ];
    s[f] === d ? (h = f === "x" ? C : T) : (h = f === "x" ? T : C);
  } else {
    const C = [{ x: u.x, y: l.y }],
      T = [{ x: l.x, y: u.y }];
    if ((f === "x" ? (h = s.x === d ? T : C) : (h = s.y === d ? C : T), t === r)) {
      const q = Math.abs(e[f] - n[f]);
      if (q <= o) {
        const S = Math.min(o - 1, o - q);
        s[f] === d ? (y[f] = (u[f] > e[f] ? -1 : 1) * S) : (m[f] = (l[f] > n[f] ? -1 : 1) * S);
      }
    }
    if (t !== r) {
      const q = f === "x" ? "y" : "x",
        S = s[f] === a[q],
        O = u[q] > l[q],
        A = u[q] < l[q];
      ((s[f] === 1 && ((!S && O) || (S && A))) || (s[f] !== 1 && ((!S && A) || (S && O)))) &&
        (h = f === "x" ? C : T);
    }
    const P = { x: u.x + y.x, y: u.y + y.y },
      M = { x: l.x + m.x, y: l.y + m.y },
      I = Math.max(Math.abs(P.x - h[0].x), Math.abs(M.x - h[0].x)),
      j = Math.max(Math.abs(P.y - h[0].y), Math.abs(M.y - h[0].y));
    I >= j ? ((v = (P.x + M.x) / 2), (p = h[0].y)) : ((v = h[0].x), (p = (P.y + M.y) / 2));
  }
  return [[e, { x: u.x + y.x, y: u.y + y.y }, ...h, { x: l.x + m.x, y: l.y + m.y }, n], v, p, x, b];
}
function Hq(e, t, n, r) {
  const i = Math.min(fx(e, t) / 2, fx(t, n) / 2, r),
    { x: o, y: s } = t;
  if ((e.x === o && o === n.x) || (e.y === s && s === n.y)) return `L${o} ${s}`;
  if (e.y === s) {
    const l = e.x < n.x ? -1 : 1,
      c = e.y < n.y ? 1 : -1;
    return `L ${o + i * l},${s}Q ${o},${s} ${o},${s + i * c}`;
  }
  const a = e.x < n.x ? 1 : -1,
    u = e.y < n.y ? -1 : 1;
  return `L ${o},${s + i * u}Q ${o},${s} ${o + i * a},${s}`;
}
function fl({
  sourceX: e,
  sourceY: t,
  sourcePosition: n = Y.Bottom,
  targetX: r,
  targetY: i,
  targetPosition: o = Y.Top,
  borderRadius: s = 5,
  centerX: a,
  centerY: u,
  offset: l = 20,
}) {
  const [c, f, d, h, v] = Uq({
    source: { x: e, y: t },
    sourcePosition: n,
    target: { x: r, y: i },
    targetPosition: o,
    center: { x: a, y: u },
    offset: l,
  });
  return [
    c.reduce((y, m, g) => {
      let w = "";
      return (
        g > 0 && g < c.length - 1
          ? (w = Hq(c[g - 1], m, c[g + 1], s))
          : (w = `${g === 0 ? "M" : "L"}${m.x} ${m.y}`),
        (y += w),
        y
      );
    }, ""),
    f,
    d,
    h,
    v,
  ];
}
const Yl = _.memo(
  ({
    sourceX: e,
    sourceY: t,
    targetX: n,
    targetY: r,
    label: i,
    labelStyle: o,
    labelShowBg: s,
    labelBgStyle: a,
    labelBgPadding: u,
    labelBgBorderRadius: l,
    style: c,
    sourcePosition: f = Y.Bottom,
    targetPosition: d = Y.Top,
    markerEnd: h,
    markerStart: v,
    pathOptions: p,
    interactionWidth: y,
  }) => {
    const [m, g, w] = fl({
      sourceX: e,
      sourceY: t,
      sourcePosition: f,
      targetX: n,
      targetY: r,
      targetPosition: d,
      borderRadius: p == null ? void 0 : p.borderRadius,
      offset: p == null ? void 0 : p.offset,
    });
    return L.createElement(Co, {
      path: m,
      labelX: g,
      labelY: w,
      label: i,
      labelStyle: o,
      labelShowBg: s,
      labelBgStyle: a,
      labelBgPadding: u,
      labelBgBorderRadius: l,
      style: c,
      markerEnd: h,
      markerStart: v,
      interactionWidth: y,
    });
  },
);
Yl.displayName = "SmoothStepEdge";
const d0 = _.memo((e) => {
  var t;
  return L.createElement(Yl, {
    ...e,
    pathOptions: _.useMemo(() => {
      var n;
      return { borderRadius: 0, offset: (n = e.pathOptions) == null ? void 0 : n.offset };
    }, [(t = e.pathOptions) == null ? void 0 : t.offset]),
  });
});
d0.displayName = "StepEdge";
function Gq({ sourceX: e, sourceY: t, targetX: n, targetY: r }) {
  const [i, o, s, a] = wA({ sourceX: e, sourceY: t, targetX: n, targetY: r });
  return [`M ${e},${t}L ${n},${r}`, i, o, s, a];
}
const h0 = _.memo(
  ({
    sourceX: e,
    sourceY: t,
    targetX: n,
    targetY: r,
    label: i,
    labelStyle: o,
    labelShowBg: s,
    labelBgStyle: a,
    labelBgPadding: u,
    labelBgBorderRadius: l,
    style: c,
    markerEnd: f,
    markerStart: d,
    interactionWidth: h,
  }) => {
    const [v, p, y] = Gq({ sourceX: e, sourceY: t, targetX: n, targetY: r });
    return L.createElement(Co, {
      path: v,
      labelX: p,
      labelY: y,
      label: i,
      labelStyle: o,
      labelShowBg: s,
      labelBgStyle: a,
      labelBgPadding: u,
      labelBgBorderRadius: l,
      style: c,
      markerEnd: f,
      markerStart: d,
      interactionWidth: h,
    });
  },
);
h0.displayName = "StraightEdge";
function Xa(e, t) {
  return e >= 0 ? 0.5 * e : t * 25 * Math.sqrt(-e);
}
function dx({ pos: e, x1: t, y1: n, x2: r, y2: i, c: o }) {
  switch (e) {
    case Y.Left:
      return [t - Xa(t - r, o), n];
    case Y.Right:
      return [t + Xa(r - t, o), n];
    case Y.Top:
      return [t, n - Xa(n - i, o)];
    case Y.Bottom:
      return [t, n + Xa(i - n, o)];
  }
}
function bA({
  sourceX: e,
  sourceY: t,
  sourcePosition: n = Y.Bottom,
  targetX: r,
  targetY: i,
  targetPosition: o = Y.Top,
  curvature: s = 0.25,
}) {
  const [a, u] = dx({ pos: n, x1: e, y1: t, x2: r, y2: i, c: s }),
    [l, c] = dx({ pos: o, x1: r, y1: i, x2: e, y2: t, c: s }),
    [f, d, h, v] = xA({
      sourceX: e,
      sourceY: t,
      targetX: r,
      targetY: i,
      sourceControlX: a,
      sourceControlY: u,
      targetControlX: l,
      targetControlY: c,
    });
  return [`M${e},${t} C${a},${u} ${l},${c} ${r},${i}`, f, d, h, v];
}
const dl = _.memo(
  ({
    sourceX: e,
    sourceY: t,
    targetX: n,
    targetY: r,
    sourcePosition: i = Y.Bottom,
    targetPosition: o = Y.Top,
    label: s,
    labelStyle: a,
    labelShowBg: u,
    labelBgStyle: l,
    labelBgPadding: c,
    labelBgBorderRadius: f,
    style: d,
    markerEnd: h,
    markerStart: v,
    pathOptions: p,
    interactionWidth: y,
  }) => {
    const [m, g, w] = bA({
      sourceX: e,
      sourceY: t,
      sourcePosition: i,
      targetX: n,
      targetY: r,
      targetPosition: o,
      curvature: p == null ? void 0 : p.curvature,
    });
    return L.createElement(Co, {
      path: m,
      labelX: g,
      labelY: w,
      label: s,
      labelStyle: a,
      labelShowBg: u,
      labelBgStyle: l,
      labelBgPadding: c,
      labelBgBorderRadius: f,
      style: d,
      markerEnd: h,
      markerStart: v,
      interactionWidth: y,
    });
  },
);
dl.displayName = "BezierEdge";
const p0 = _.createContext(null),
  Wq = p0.Provider;
p0.Consumer;
const Kq = () => _.useContext(p0),
  Yq = (e) => "id" in e && "source" in e && "target" in e,
  Xq = ({ source: e, sourceHandle: t, target: n, targetHandle: r }) =>
    `reactflow__edge-${e}${t || ""}-${n}${r || ""}`,
  Iv = (e, t) =>
    typeof e > "u"
      ? ""
      : typeof e == "string"
        ? e
        : `${t ? `${t}__` : ""}${Object.keys(e)
            .sort()
            .map((r) => `${r}=${e[r]}`)
            .join("&")}`,
  Zq = (e, t) =>
    t.some(
      (n) =>
        n.source === e.source &&
        n.target === e.target &&
        (n.sourceHandle === e.sourceHandle || (!n.sourceHandle && !e.sourceHandle)) &&
        (n.targetHandle === e.targetHandle || (!n.targetHandle && !e.targetHandle)),
    ),
  Qq = (e, t) => {
    if (!e.source || !e.target) return t;
    let n;
    return Yq(e) ? (n = { ...e }) : (n = { ...e, id: Xq(e) }), Zq(n, t) ? t : t.concat(n);
  },
  Dv = ({ x: e, y: t }, [n, r, i], o, [s, a]) => {
    const u = { x: (e - n) / i, y: (t - r) / i };
    return o ? { x: s * Math.round(u.x / s), y: a * Math.round(u.y / a) } : u;
  },
  SA = ({ x: e, y: t }, [n, r, i]) => ({ x: e * i + n, y: t * i + r }),
  ni = (e, t = [0, 0]) => {
    if (!e) return { x: 0, y: 0, positionAbsolute: { x: 0, y: 0 } };
    const n = (e.width ?? 0) * t[0],
      r = (e.height ?? 0) * t[1],
      i = { x: e.position.x - n, y: e.position.y - r };
    return {
      ...i,
      positionAbsolute: e.positionAbsolute
        ? { x: e.positionAbsolute.x - n, y: e.positionAbsolute.y - r }
        : i,
    };
  },
  Xl = (e, t = [0, 0]) => {
    if (e.length === 0) return { x: 0, y: 0, width: 0, height: 0 };
    const n = e.reduce(
      (r, i) => {
        const { x: o, y: s } = ni(i, t).positionAbsolute;
        return mA(r, Zs({ x: o, y: s, width: i.width || 0, height: i.height || 0 }));
      },
      { x: 1 / 0, y: 1 / 0, x2: -1 / 0, y2: -1 / 0 },
    );
    return gA(n);
  },
  EA = (e, t, [n, r, i] = [0, 0, 1], o = !1, s = !1, a = [0, 0]) => {
    const u = { x: (t.x - n) / i, y: (t.y - r) / i, width: t.width / i, height: t.height / i },
      l = [];
    return (
      e.forEach((c) => {
        const { width: f, height: d, selectable: h = !0, hidden: v = !1 } = c;
        if ((s && !h) || v) return !1;
        const { positionAbsolute: p } = ni(c, a),
          y = { x: p.x, y: p.y, width: f || 0, height: d || 0 },
          m = Nv(u, y),
          g = typeof f > "u" || typeof d > "u" || f === null || d === null,
          w = o && m > 0,
          x = (f || 0) * (d || 0);
        (g || w || m >= x || c.dragging) && l.push(c);
      }),
      l
    );
  },
  CA = (e, t) => {
    const n = e.map((r) => r.id);
    return t.filter((r) => n.includes(r.source) || n.includes(r.target));
  },
  TA = (e, t, n, r, i, o = 0.1) => {
    const s = t / (e.width * (1 + o)),
      a = n / (e.height * (1 + o)),
      u = Math.min(s, a),
      l = po(u, r, i),
      c = e.x + e.width / 2,
      f = e.y + e.height / 2,
      d = t / 2 - c * l,
      h = n / 2 - f * l;
    return { x: d, y: h, zoom: l };
  },
  Br = (e, t = 0) => e.transition().duration(t);
function hx(e, t, n, r) {
  return (t[n] || []).reduce((i, o) => {
    var s, a;
    return (
      `${e.id}-${o.id}-${n}` !== r &&
        i.push({
          id: o.id || null,
          type: n,
          nodeId: e.id,
          x: (((s = e.positionAbsolute) == null ? void 0 : s.x) ?? 0) + o.x + o.width / 2,
          y: (((a = e.positionAbsolute) == null ? void 0 : a.y) ?? 0) + o.y + o.height / 2,
        }),
      i
    );
  }, []);
}
function Jq(e, t, n, r, i, o) {
  const { x: s, y: a } = kr(e),
    l = t.elementsFromPoint(s, a).find((v) => v.classList.contains("react-flow__handle"));
  if (l) {
    const v = l.getAttribute("data-nodeid");
    if (v) {
      const p = m0(void 0, l),
        y = l.getAttribute("data-handleid"),
        m = o({ nodeId: v, id: y, type: p });
      if (m) {
        const g = i.find((w) => w.nodeId === v && w.type === p && w.id === y);
        return {
          handle: {
            id: y,
            type: p,
            nodeId: v,
            x: (g == null ? void 0 : g.x) || n.x,
            y: (g == null ? void 0 : g.y) || n.y,
          },
          validHandleResult: m,
        };
      }
    }
  }
  let c = [],
    f = 1 / 0;
  if (
    (i.forEach((v) => {
      const p = Math.sqrt((v.x - n.x) ** 2 + (v.y - n.y) ** 2);
      if (p <= r) {
        const y = o(v);
        p <= f &&
          (p < f
            ? (c = [{ handle: v, validHandleResult: y }])
            : p === f && c.push({ handle: v, validHandleResult: y }),
          (f = p));
      }
    }),
    !c.length)
  )
    return { handle: null, validHandleResult: kA() };
  if (c.length === 1) return c[0];
  const d = c.some(({ validHandleResult: v }) => v.isValid),
    h = c.some(({ handle: v }) => v.type === "target");
  return (
    c.find(({ handle: v, validHandleResult: p }) =>
      h ? v.type === "target" : d ? p.isValid : !0,
    ) || c[0]
  );
}
const e$ = { source: null, target: null, sourceHandle: null, targetHandle: null },
  kA = () => ({ handleDomNode: null, isValid: !1, connection: e$, endHandle: null });
function RA(e, t, n, r, i, o, s) {
  const a = i === "target",
    u = s.querySelector(
      `.react-flow__handle[data-id="${e == null ? void 0 : e.nodeId}-${e == null ? void 0 : e.id}-${e == null ? void 0 : e.type}"]`,
    ),
    l = { ...kA(), handleDomNode: u };
  if (u) {
    const c = m0(void 0, u),
      f = u.getAttribute("data-nodeid"),
      d = u.getAttribute("data-handleid"),
      h = u.classList.contains("connectable"),
      v = u.classList.contains("connectableend"),
      p = {
        source: a ? f : n,
        sourceHandle: a ? d : r,
        target: a ? n : f,
        targetHandle: a ? r : d,
      };
    (l.connection = p),
      h &&
        v &&
        (t === ci.Strict ? (a && c === "source") || (!a && c === "target") : f !== n || d !== r) &&
        ((l.endHandle = { nodeId: f, handleId: d, type: c }), (l.isValid = o(p)));
  }
  return l;
}
function t$({ nodes: e, nodeId: t, handleId: n, handleType: r }) {
  return e.reduce((i, o) => {
    if (o[ke]) {
      const { handleBounds: s } = o[ke];
      let a = [],
        u = [];
      s && ((a = hx(o, s, "source", `${t}-${n}-${r}`)), (u = hx(o, s, "target", `${t}-${n}-${r}`))),
        i.push(...a, ...u);
    }
    return i;
  }, []);
}
function m0(e, t) {
  return (
    e ||
    (t != null && t.classList.contains("target")
      ? "target"
      : t != null && t.classList.contains("source")
        ? "source"
        : null)
  );
}
function lf(e) {
  e == null ||
    e.classList.remove(
      "valid",
      "connecting",
      "react-flow__handle-valid",
      "react-flow__handle-connecting",
    );
}
function n$(e, t) {
  let n = null;
  return t ? (n = "valid") : e && !t && (n = "invalid"), n;
}
function PA({
  event: e,
  handleId: t,
  nodeId: n,
  onConnect: r,
  isTarget: i,
  getState: o,
  setState: s,
  isValidConnection: a,
  edgeUpdaterType: u,
  onReconnectEnd: l,
}) {
  const c = pA(e.target),
    {
      connectionMode: f,
      domNode: d,
      autoPanOnConnect: h,
      connectionRadius: v,
      onConnectStart: p,
      panBy: y,
      getNodes: m,
      cancelConnection: g,
    } = o();
  let w = 0,
    x;
  const { x: b, y: E } = kr(e),
    C = c == null ? void 0 : c.elementFromPoint(b, E),
    T = m0(u, C),
    P = d == null ? void 0 : d.getBoundingClientRect();
  if (!P || !T) return;
  let M,
    I = kr(e, P),
    j = !1,
    q = null,
    S = !1,
    O = null;
  const A = t$({ nodes: m(), nodeId: n, handleId: t, handleType: T }),
    F = () => {
      if (!h) return;
      const [D, V] = hA(I, P);
      y({ x: D, y: V }), (w = requestAnimationFrame(F));
    };
  s({
    connectionPosition: I,
    connectionStatus: null,
    connectionNodeId: n,
    connectionHandleId: t,
    connectionHandleType: T,
    connectionStartHandle: { nodeId: n, handleId: t, type: T },
    connectionEndHandle: null,
  }),
    p == null || p(e, { nodeId: n, handleId: t, handleType: T });
  function N(D) {
    const { transform: V } = o();
    I = kr(D, P);
    const { handle: $, validHandleResult: U } = Jq(D, c, Dv(I, V, !1, [1, 1]), v, A, (B) =>
      RA(B, f, n, t, i ? "target" : "source", a, c),
    );
    if (
      ((x = $),
      j || (F(), (j = !0)),
      (O = U.handleDomNode),
      (q = U.connection),
      (S = U.isValid),
      s({
        connectionPosition: x && S ? SA({ x: x.x, y: x.y }, V) : I,
        connectionStatus: n$(!!x, S),
        connectionEndHandle: U.endHandle,
      }),
      !x && !S && !O)
    )
      return lf(M);
    q.source !== q.target &&
      O &&
      (lf(M),
      (M = O),
      O.classList.add("connecting", "react-flow__handle-connecting"),
      O.classList.toggle("valid", S),
      O.classList.toggle("react-flow__handle-valid", S));
  }
  function k(D) {
    var V, $;
    (x || O) && q && S && (r == null || r(q)),
      ($ = (V = o()).onConnectEnd) == null || $.call(V, D),
      u && (l == null || l(D)),
      lf(M),
      g(),
      cancelAnimationFrame(w),
      (j = !1),
      (S = !1),
      (q = null),
      (O = null),
      c.removeEventListener("mousemove", N),
      c.removeEventListener("mouseup", k),
      c.removeEventListener("touchmove", N),
      c.removeEventListener("touchend", k);
  }
  c.addEventListener("mousemove", N),
    c.addEventListener("mouseup", k),
    c.addEventListener("touchmove", N),
    c.addEventListener("touchend", k);
}
const px = () => !0,
  r$ = (e) => ({
    connectionStartHandle: e.connectionStartHandle,
    connectOnClick: e.connectOnClick,
    noPanClassName: e.noPanClassName,
  }),
  i$ = (e, t, n) => (r) => {
    const { connectionStartHandle: i, connectionEndHandle: o, connectionClickStartHandle: s } = r;
    return {
      connecting:
        ((i == null ? void 0 : i.nodeId) === e &&
          (i == null ? void 0 : i.handleId) === t &&
          (i == null ? void 0 : i.type) === n) ||
        ((o == null ? void 0 : o.nodeId) === e &&
          (o == null ? void 0 : o.handleId) === t &&
          (o == null ? void 0 : o.type) === n),
      clickConnecting:
        (s == null ? void 0 : s.nodeId) === e &&
        (s == null ? void 0 : s.handleId) === t &&
        (s == null ? void 0 : s.type) === n,
    };
  },
  AA = _.forwardRef(
    (
      {
        type: e = "source",
        position: t = Y.Top,
        isValidConnection: n,
        isConnectable: r = !0,
        isConnectableStart: i = !0,
        isConnectableEnd: o = !0,
        id: s,
        onConnect: a,
        children: u,
        className: l,
        onMouseDown: c,
        onTouchStart: f,
        ...d
      },
      h,
    ) => {
      var P, M;
      const v = s || null,
        p = e === "target",
        y = Fe(),
        m = Kq(),
        { connectOnClick: g, noPanClassName: w } = de(r$, He),
        { connecting: x, clickConnecting: b } = de(i$(m, v, e), He);
      m || (M = (P = y.getState()).onError) == null || M.call(P, "010", Kn.error010());
      const E = (I) => {
          const { defaultEdgeOptions: j, onConnect: q, hasDefaultEdges: S } = y.getState(),
            O = { ...j, ...I };
          if (S) {
            const { edges: A, setEdges: F } = y.getState();
            F(Qq(O, A));
          }
          q == null || q(O), a == null || a(O);
        },
        C = (I) => {
          if (!m) return;
          const j = yA(I);
          i &&
            ((j && I.button === 0) || !j) &&
            PA({
              event: I,
              handleId: v,
              nodeId: m,
              onConnect: E,
              isTarget: p,
              getState: y.getState,
              setState: y.setState,
              isValidConnection: n || y.getState().isValidConnection || px,
            }),
            j ? c == null || c(I) : f == null || f(I);
        },
        T = (I) => {
          const {
            onClickConnectStart: j,
            onClickConnectEnd: q,
            connectionClickStartHandle: S,
            connectionMode: O,
            isValidConnection: A,
          } = y.getState();
          if (!m || (!S && !i)) return;
          if (!S) {
            j == null || j(I, { nodeId: m, handleId: v, handleType: e }),
              y.setState({ connectionClickStartHandle: { nodeId: m, type: e, handleId: v } });
            return;
          }
          const F = pA(I.target),
            N = n || A || px,
            { connection: k, isValid: D } = RA(
              { nodeId: m, id: v, type: e },
              O,
              S.nodeId,
              S.handleId || null,
              S.type,
              N,
              F,
            );
          D && E(k), q == null || q(I), y.setState({ connectionClickStartHandle: null });
        };
      return L.createElement(
        "div",
        {
          "data-handleid": v,
          "data-nodeid": m,
          "data-handlepos": t,
          "data-id": `${m}-${v}-${e}`,
          className: Ze([
            "react-flow__handle",
            `react-flow__handle-${t}`,
            "nodrag",
            w,
            l,
            {
              source: !p,
              target: p,
              connectable: r,
              connectablestart: i,
              connectableend: o,
              connecting: b,
              connectionindicator: r && ((i && !x) || (o && x)),
            },
          ]),
          onMouseDown: C,
          onTouchStart: C,
          onClick: g ? T : void 0,
          ref: h,
          ...d,
        },
        u,
      );
    },
  );
AA.displayName = "Handle";
var yr = _.memo(AA);
const NA = ({
  data: e,
  isConnectable: t,
  targetPosition: n = Y.Top,
  sourcePosition: r = Y.Bottom,
}) =>
  L.createElement(
    L.Fragment,
    null,
    L.createElement(yr, { type: "target", position: n, isConnectable: t }),
    e == null ? void 0 : e.label,
    L.createElement(yr, { type: "source", position: r, isConnectable: t }),
  );
NA.displayName = "DefaultNode";
var Ov = _.memo(NA);
const MA = ({ data: e, isConnectable: t, sourcePosition: n = Y.Bottom }) =>
  L.createElement(
    L.Fragment,
    null,
    e == null ? void 0 : e.label,
    L.createElement(yr, { type: "source", position: n, isConnectable: t }),
  );
MA.displayName = "InputNode";
var IA = _.memo(MA);
const DA = ({ data: e, isConnectable: t, targetPosition: n = Y.Top }) =>
  L.createElement(
    L.Fragment,
    null,
    L.createElement(yr, { type: "target", position: n, isConnectable: t }),
    e == null ? void 0 : e.label,
  );
DA.displayName = "OutputNode";
var OA = _.memo(DA);
const g0 = () => null;
g0.displayName = "GroupNode";
const o$ = (e) => ({
    selectedNodes: e.getNodes().filter((t) => t.selected),
    selectedEdges: e.edges.filter((t) => t.selected).map((t) => ({ ...t })),
  }),
  Za = (e) => e.id;
function s$(e, t) {
  return (
    He(e.selectedNodes.map(Za), t.selectedNodes.map(Za)) &&
    He(e.selectedEdges.map(Za), t.selectedEdges.map(Za))
  );
}
const LA = _.memo(({ onSelectionChange: e }) => {
  const t = Fe(),
    { selectedNodes: n, selectedEdges: r } = de(o$, s$);
  return (
    _.useEffect(() => {
      const i = { nodes: n, edges: r };
      e == null || e(i), t.getState().onSelectionChange.forEach((o) => o(i));
    }, [n, r, e]),
    null
  );
});
LA.displayName = "SelectionListener";
const a$ = (e) => !!e.onSelectionChange;
function u$({ onSelectionChange: e }) {
  const t = de(a$);
  return e || t ? L.createElement(LA, { onSelectionChange: e }) : null;
}
const l$ = (e) => ({
  setNodes: e.setNodes,
  setEdges: e.setEdges,
  setDefaultNodesAndEdges: e.setDefaultNodesAndEdges,
  setMinZoom: e.setMinZoom,
  setMaxZoom: e.setMaxZoom,
  setTranslateExtent: e.setTranslateExtent,
  setNodeExtent: e.setNodeExtent,
  reset: e.reset,
});
function _i(e, t) {
  _.useEffect(() => {
    typeof e < "u" && t(e);
  }, [e]);
}
function re(e, t, n) {
  _.useEffect(() => {
    typeof t < "u" && n({ [e]: t });
  }, [t]);
}
const c$ = ({
    nodes: e,
    edges: t,
    defaultNodes: n,
    defaultEdges: r,
    onConnect: i,
    onConnectStart: o,
    onConnectEnd: s,
    onClickConnectStart: a,
    onClickConnectEnd: u,
    nodesDraggable: l,
    nodesConnectable: c,
    nodesFocusable: f,
    edgesFocusable: d,
    edgesUpdatable: h,
    elevateNodesOnSelect: v,
    minZoom: p,
    maxZoom: y,
    nodeExtent: m,
    onNodesChange: g,
    onEdgesChange: w,
    elementsSelectable: x,
    connectionMode: b,
    snapGrid: E,
    snapToGrid: C,
    translateExtent: T,
    connectOnClick: P,
    defaultEdgeOptions: M,
    fitView: I,
    fitViewOptions: j,
    onNodesDelete: q,
    onEdgesDelete: S,
    onNodeDrag: O,
    onNodeDragStart: A,
    onNodeDragStop: F,
    onSelectionDrag: N,
    onSelectionDragStart: k,
    onSelectionDragStop: D,
    noPanClassName: V,
    nodeOrigin: $,
    rfId: U,
    autoPanOnConnect: B,
    autoPanOnNodeDrag: W,
    onError: X,
    connectionRadius: ee,
    isValidConnection: ue,
    nodeDragThreshold: se,
  }) => {
    const {
        setNodes: oe,
        setEdges: De,
        setDefaultNodesAndEdges: Re,
        setMinZoom: Ge,
        setMaxZoom: je,
        setTranslateExtent: Q,
        setNodeExtent: Ve,
        reset: K,
      } = de(l$, He),
      G = Fe();
    return (
      _.useEffect(() => {
        const Ee = r == null ? void 0 : r.map((Ut) => ({ ...Ut, ...M }));
        return (
          Re(n, Ee),
          () => {
            K();
          }
        );
      }, []),
      re("defaultEdgeOptions", M, G.setState),
      re("connectionMode", b, G.setState),
      re("onConnect", i, G.setState),
      re("onConnectStart", o, G.setState),
      re("onConnectEnd", s, G.setState),
      re("onClickConnectStart", a, G.setState),
      re("onClickConnectEnd", u, G.setState),
      re("nodesDraggable", l, G.setState),
      re("nodesConnectable", c, G.setState),
      re("nodesFocusable", f, G.setState),
      re("edgesFocusable", d, G.setState),
      re("edgesUpdatable", h, G.setState),
      re("elementsSelectable", x, G.setState),
      re("elevateNodesOnSelect", v, G.setState),
      re("snapToGrid", C, G.setState),
      re("snapGrid", E, G.setState),
      re("onNodesChange", g, G.setState),
      re("onEdgesChange", w, G.setState),
      re("connectOnClick", P, G.setState),
      re("fitViewOnInit", I, G.setState),
      re("fitViewOnInitOptions", j, G.setState),
      re("onNodesDelete", q, G.setState),
      re("onEdgesDelete", S, G.setState),
      re("onNodeDrag", O, G.setState),
      re("onNodeDragStart", A, G.setState),
      re("onNodeDragStop", F, G.setState),
      re("onSelectionDrag", N, G.setState),
      re("onSelectionDragStart", k, G.setState),
      re("onSelectionDragStop", D, G.setState),
      re("noPanClassName", V, G.setState),
      re("nodeOrigin", $, G.setState),
      re("rfId", U, G.setState),
      re("autoPanOnConnect", B, G.setState),
      re("autoPanOnNodeDrag", W, G.setState),
      re("onError", X, G.setState),
      re("connectionRadius", ee, G.setState),
      re("isValidConnection", ue, G.setState),
      re("nodeDragThreshold", se, G.setState),
      _i(e, oe),
      _i(t, De),
      _i(p, Ge),
      _i(y, je),
      _i(T, Q),
      _i(m, Ve),
      null
    );
  },
  mx = { display: "none" },
  f$ = {
    position: "absolute",
    width: 1,
    height: 1,
    margin: -1,
    border: 0,
    padding: 0,
    overflow: "hidden",
    clip: "rect(0px, 0px, 0px, 0px)",
    clipPath: "inset(100%)",
  },
  FA = "react-flow__node-desc",
  jA = "react-flow__edge-desc",
  d$ = "react-flow__aria-live",
  h$ = (e) => e.ariaLiveMessage;
function p$({ rfId: e }) {
  const t = de(h$);
  return L.createElement(
    "div",
    { id: `${d$}-${e}`, "aria-live": "assertive", "aria-atomic": "true", style: f$ },
    t,
  );
}
function m$({ rfId: e, disableKeyboardA11y: t }) {
  return L.createElement(
    L.Fragment,
    null,
    L.createElement(
      "div",
      { id: `${FA}-${e}`, style: mx },
      "Press enter or space to select a node.",
      !t && "You can then use the arrow keys to move the node around.",
      " Press delete to remove it and escape to cancel.",
      " ",
    ),
    L.createElement(
      "div",
      { id: `${jA}-${e}`, style: mx },
      "Press enter or space to select an edge. You can then press delete to remove it or escape to cancel.",
    ),
    !t && L.createElement(p$, { rfId: e }),
  );
}
var Qs = (e = null, t = { actInsideInputWithModifier: !0 }) => {
  const [n, r] = _.useState(!1),
    i = _.useRef(!1),
    o = _.useRef(new Set([])),
    [s, a] = _.useMemo(() => {
      if (e !== null) {
        const l = (Array.isArray(e) ? e : [e])
            .filter((f) => typeof f == "string")
            .map((f) => f.split("+")),
          c = l.reduce((f, d) => f.concat(...d), []);
        return [l, c];
      }
      return [[], []];
    }, [e]);
  return (
    _.useEffect(() => {
      const u = typeof document < "u" ? document : null,
        l = (t == null ? void 0 : t.target) || u;
      if (e !== null) {
        const c = (h) => {
            if (
              ((i.current = h.ctrlKey || h.metaKey || h.shiftKey),
              (!i.current || (i.current && !t.actInsideInputWithModifier)) && Mv(h))
            )
              return !1;
            const p = vx(h.code, a);
            o.current.add(h[p]), gx(s, o.current, !1) && (h.preventDefault(), r(!0));
          },
          f = (h) => {
            if ((!i.current || (i.current && !t.actInsideInputWithModifier)) && Mv(h)) return !1;
            const p = vx(h.code, a);
            gx(s, o.current, !0) ? (r(!1), o.current.clear()) : o.current.delete(h[p]),
              h.key === "Meta" && o.current.clear(),
              (i.current = !1);
          },
          d = () => {
            o.current.clear(), r(!1);
          };
        return (
          l == null || l.addEventListener("keydown", c),
          l == null || l.addEventListener("keyup", f),
          window.addEventListener("blur", d),
          () => {
            l == null || l.removeEventListener("keydown", c),
              l == null || l.removeEventListener("keyup", f),
              window.removeEventListener("blur", d);
          }
        );
      }
    }, [e, r]),
    n
  );
};
function gx(e, t, n) {
  return e.filter((r) => n || r.length === t.size).some((r) => r.every((i) => t.has(i)));
}
function vx(e, t) {
  return t.includes(e) ? "code" : "key";
}
function VA(e, t, n, r) {
  var a, u;
  const i = e.parentNode || e.parentId;
  if (!i) return n;
  const o = t.get(i),
    s = ni(o, r);
  return VA(
    o,
    t,
    {
      x: (n.x ?? 0) + s.x,
      y: (n.y ?? 0) + s.y,
      z:
        (((a = o[ke]) == null ? void 0 : a.z) ?? 0) > (n.z ?? 0)
          ? (((u = o[ke]) == null ? void 0 : u.z) ?? 0)
          : (n.z ?? 0),
    },
    r,
  );
}
function qA(e, t, n) {
  e.forEach((r) => {
    var o;
    const i = r.parentNode || r.parentId;
    if (i && !e.has(i)) throw new Error(`Parent node ${i} not found`);
    if (i || (n != null && n[r.id])) {
      const {
        x: s,
        y: a,
        z: u,
      } = VA(r, e, { ...r.position, z: ((o = r[ke]) == null ? void 0 : o.z) ?? 0 }, t);
      (r.positionAbsolute = { x: s, y: a }),
        (r[ke].z = u),
        n != null && n[r.id] && (r[ke].isParent = !0);
    }
  });
}
function cf(e, t, n, r) {
  const i = new Map(),
    o = {},
    s = r ? 1e3 : 0;
  return (
    e.forEach((a) => {
      var h;
      const u = (Ft(a.zIndex) ? a.zIndex : 0) + (a.selected ? s : 0),
        l = t.get(a.id),
        c = { ...a, positionAbsolute: { x: a.position.x, y: a.position.y } },
        f = a.parentNode || a.parentId;
      f && (o[f] = !0);
      const d = (l == null ? void 0 : l.type) && (l == null ? void 0 : l.type) !== a.type;
      Object.defineProperty(c, ke, {
        enumerable: !1,
        value: {
          handleBounds: d || (h = l == null ? void 0 : l[ke]) == null ? void 0 : h.handleBounds,
          z: u,
        },
      }),
        i.set(a.id, c);
    }),
    qA(i, n, o),
    i
  );
}
function $A(e, t = {}) {
  const {
      getNodes: n,
      width: r,
      height: i,
      minZoom: o,
      maxZoom: s,
      d3Zoom: a,
      d3Selection: u,
      fitViewOnInitDone: l,
      fitViewOnInit: c,
      nodeOrigin: f,
    } = e(),
    d = t.initial && !l && c;
  if (a && u && (d || !t.initial)) {
    const v = n().filter((y) => {
        var g;
        const m = t.includeHiddenNodes ? y.width && y.height : !y.hidden;
        return (g = t.nodes) != null && g.length ? m && t.nodes.some((w) => w.id === y.id) : m;
      }),
      p = v.every((y) => y.width && y.height);
    if (v.length > 0 && p) {
      const y = Xl(v, f),
        { x: m, y: g, zoom: w } = TA(y, r, i, t.minZoom ?? o, t.maxZoom ?? s, t.padding ?? 0.1),
        x = qn.translate(m, g).scale(w);
      return (
        typeof t.duration == "number" && t.duration > 0
          ? a.transform(Br(u, t.duration), x)
          : a.transform(u, x),
        !0
      );
    }
  }
  return !1;
}
function g$(e, t) {
  return (
    e.forEach((n) => {
      const r = t.get(n.id);
      r && t.set(r.id, { ...r, [ke]: r[ke], selected: n.selected });
    }),
    new Map(t)
  );
}
function v$(e, t) {
  return t.map((n) => {
    const r = e.find((i) => i.id === n.id);
    return r && (n.selected = r.selected), n;
  });
}
function Qa({ changedNodes: e, changedEdges: t, get: n, set: r }) {
  const {
    nodeInternals: i,
    edges: o,
    onNodesChange: s,
    onEdgesChange: a,
    hasDefaultNodes: u,
    hasDefaultEdges: l,
  } = n();
  e != null && e.length && (u && r({ nodeInternals: g$(e, i) }), s == null || s(e)),
    t != null && t.length && (l && r({ edges: v$(t, o) }), a == null || a(t));
}
const bi = () => {},
  y$ = {
    zoomIn: bi,
    zoomOut: bi,
    zoomTo: bi,
    getZoom: () => 1,
    setViewport: bi,
    getViewport: () => ({ x: 0, y: 0, zoom: 1 }),
    fitView: () => !1,
    setCenter: bi,
    fitBounds: bi,
    project: (e) => e,
    screenToFlowPosition: (e) => e,
    flowToScreenPosition: (e) => e,
    viewportInitialized: !1,
  },
  w$ = (e) => ({ d3Zoom: e.d3Zoom, d3Selection: e.d3Selection }),
  x$ = () => {
    const e = Fe(),
      { d3Zoom: t, d3Selection: n } = de(w$, He);
    return _.useMemo(
      () =>
        n && t
          ? {
              zoomIn: (i) => t.scaleBy(Br(n, i == null ? void 0 : i.duration), 1.2),
              zoomOut: (i) => t.scaleBy(Br(n, i == null ? void 0 : i.duration), 1 / 1.2),
              zoomTo: (i, o) => t.scaleTo(Br(n, o == null ? void 0 : o.duration), i),
              getZoom: () => e.getState().transform[2],
              setViewport: (i, o) => {
                const [s, a, u] = e.getState().transform,
                  l = qn.translate(i.x ?? s, i.y ?? a).scale(i.zoom ?? u);
                t.transform(Br(n, o == null ? void 0 : o.duration), l);
              },
              getViewport: () => {
                const [i, o, s] = e.getState().transform;
                return { x: i, y: o, zoom: s };
              },
              fitView: (i) => $A(e.getState, i),
              setCenter: (i, o, s) => {
                const { width: a, height: u, maxZoom: l } = e.getState(),
                  c = typeof (s == null ? void 0 : s.zoom) < "u" ? s.zoom : l,
                  f = a / 2 - i * c,
                  d = u / 2 - o * c,
                  h = qn.translate(f, d).scale(c);
                t.transform(Br(n, s == null ? void 0 : s.duration), h);
              },
              fitBounds: (i, o) => {
                const { width: s, height: a, minZoom: u, maxZoom: l } = e.getState(),
                  {
                    x: c,
                    y: f,
                    zoom: d,
                  } = TA(i, s, a, u, l, (o == null ? void 0 : o.padding) ?? 0.1),
                  h = qn.translate(c, f).scale(d);
                t.transform(Br(n, o == null ? void 0 : o.duration), h);
              },
              project: (i) => {
                const { transform: o, snapToGrid: s, snapGrid: a } = e.getState();
                return (
                  console.warn(
                    "[DEPRECATED] `project` is deprecated. Instead use `screenToFlowPosition`. There is no need to subtract the react flow bounds anymore! https://reactflow.dev/api-reference/types/react-flow-instance#screen-to-flow-position",
                  ),
                  Dv(i, o, s, a)
                );
              },
              screenToFlowPosition: (i) => {
                const { transform: o, snapToGrid: s, snapGrid: a, domNode: u } = e.getState();
                if (!u) return i;
                const { x: l, y: c } = u.getBoundingClientRect(),
                  f = { x: i.x - l, y: i.y - c };
                return Dv(f, o, s, a);
              },
              flowToScreenPosition: (i) => {
                const { transform: o, domNode: s } = e.getState();
                if (!s) return i;
                const { x: a, y: u } = s.getBoundingClientRect(),
                  l = SA(i, o);
                return { x: l.x + a, y: l.y + u };
              },
              viewportInitialized: !0,
            }
          : y$,
      [t, n],
    );
  };
function Zl() {
  const e = x$(),
    t = Fe(),
    n = _.useCallback(
      () =>
        t
          .getState()
          .getNodes()
          .map((p) => ({ ...p })),
      [],
    ),
    r = _.useCallback((p) => t.getState().nodeInternals.get(p), []),
    i = _.useCallback(() => {
      const { edges: p = [] } = t.getState();
      return p.map((y) => ({ ...y }));
    }, []),
    o = _.useCallback((p) => {
      const { edges: y = [] } = t.getState();
      return y.find((m) => m.id === p);
    }, []),
    s = _.useCallback((p) => {
      const { getNodes: y, setNodes: m, hasDefaultNodes: g, onNodesChange: w } = t.getState(),
        x = y(),
        b = typeof p == "function" ? p(x) : p;
      if (g) m(b);
      else if (w) {
        const E =
          b.length === 0
            ? x.map((C) => ({ type: "remove", id: C.id }))
            : b.map((C) => ({ item: C, type: "reset" }));
        w(E);
      }
    }, []),
    a = _.useCallback((p) => {
      const { edges: y = [], setEdges: m, hasDefaultEdges: g, onEdgesChange: w } = t.getState(),
        x = typeof p == "function" ? p(y) : p;
      if (g) m(x);
      else if (w) {
        const b =
          x.length === 0
            ? y.map((E) => ({ type: "remove", id: E.id }))
            : x.map((E) => ({ item: E, type: "reset" }));
        w(b);
      }
    }, []),
    u = _.useCallback((p) => {
      const y = Array.isArray(p) ? p : [p],
        { getNodes: m, setNodes: g, hasDefaultNodes: w, onNodesChange: x } = t.getState();
      if (w) {
        const E = [...m(), ...y];
        g(E);
      } else if (x) {
        const b = y.map((E) => ({ item: E, type: "add" }));
        x(b);
      }
    }, []),
    l = _.useCallback((p) => {
      const y = Array.isArray(p) ? p : [p],
        { edges: m = [], setEdges: g, hasDefaultEdges: w, onEdgesChange: x } = t.getState();
      if (w) g([...m, ...y]);
      else if (x) {
        const b = y.map((E) => ({ item: E, type: "add" }));
        x(b);
      }
    }, []),
    c = _.useCallback(() => {
      const { getNodes: p, edges: y = [], transform: m } = t.getState(),
        [g, w, x] = m;
      return {
        nodes: p().map((b) => ({ ...b })),
        edges: y.map((b) => ({ ...b })),
        viewport: { x: g, y: w, zoom: x },
      };
    }, []),
    f = _.useCallback(({ nodes: p, edges: y }) => {
      const {
          nodeInternals: m,
          getNodes: g,
          edges: w,
          hasDefaultNodes: x,
          hasDefaultEdges: b,
          onNodesDelete: E,
          onEdgesDelete: C,
          onNodesChange: T,
          onEdgesChange: P,
        } = t.getState(),
        M = (p || []).map((O) => O.id),
        I = (y || []).map((O) => O.id),
        j = g().reduce((O, A) => {
          const F = A.parentNode || A.parentId,
            N = !M.includes(A.id) && F && O.find((D) => D.id === F);
          return (
            (typeof A.deletable == "boolean" ? A.deletable : !0) &&
              (M.includes(A.id) || N) &&
              O.push(A),
            O
          );
        }, []),
        q = w.filter((O) => (typeof O.deletable == "boolean" ? O.deletable : !0)),
        S = q.filter((O) => I.includes(O.id));
      if (j || S) {
        const O = CA(j, q),
          A = [...S, ...O],
          F = A.reduce((N, k) => (N.includes(k.id) || N.push(k.id), N), []);
        if (
          ((b || x) &&
            (b && t.setState({ edges: w.filter((N) => !F.includes(N.id)) }),
            x &&
              (j.forEach((N) => {
                m.delete(N.id);
              }),
              t.setState({ nodeInternals: new Map(m) }))),
          F.length > 0 && (C == null || C(A), P && P(F.map((N) => ({ id: N, type: "remove" })))),
          j.length > 0 && (E == null || E(j), T))
        ) {
          const N = j.map((k) => ({ id: k.id, type: "remove" }));
          T(N);
        }
      }
    }, []),
    d = _.useCallback((p) => {
      const y = qq(p),
        m = y ? null : t.getState().nodeInternals.get(p.id);
      return !y && !m ? [null, null, y] : [y ? p : ux(m), m, y];
    }, []),
    h = _.useCallback((p, y = !0, m) => {
      const [g, w, x] = d(p);
      return g
        ? (m || t.getState().getNodes()).filter((b) => {
            if (!x && (b.id === w.id || !b.positionAbsolute)) return !1;
            const E = ux(b),
              C = Nv(E, g);
            return (y && C > 0) || C >= g.width * g.height;
          })
        : [];
    }, []),
    v = _.useCallback((p, y, m = !0) => {
      const [g] = d(p);
      if (!g) return !1;
      const w = Nv(g, y);
      return (m && w > 0) || w >= g.width * g.height;
    }, []);
  return _.useMemo(
    () => ({
      ...e,
      getNodes: n,
      getNode: r,
      getEdges: i,
      getEdge: o,
      setNodes: s,
      setEdges: a,
      addNodes: u,
      addEdges: l,
      toObject: c,
      deleteElements: f,
      getIntersectingNodes: h,
      isNodeIntersecting: v,
    }),
    [e, n, r, i, o, s, a, u, l, c, f, h, v],
  );
}
const _$ = { actInsideInputWithModifier: !1 };
var b$ = ({ deleteKeyCode: e, multiSelectionKeyCode: t }) => {
  const n = Fe(),
    { deleteElements: r } = Zl(),
    i = Qs(e, _$),
    o = Qs(t);
  _.useEffect(() => {
    if (i) {
      const { edges: s, getNodes: a } = n.getState(),
        u = a().filter((c) => c.selected),
        l = s.filter((c) => c.selected);
      r({ nodes: u, edges: l }), n.setState({ nodesSelectionActive: !1 });
    }
  }, [i]),
    _.useEffect(() => {
      n.setState({ multiSelectionActive: o });
    }, [o]);
};
function S$(e) {
  const t = Fe();
  _.useEffect(() => {
    let n;
    const r = () => {
      var o, s;
      if (!e.current) return;
      const i = l0(e.current);
      (i.height === 0 || i.width === 0) &&
        ((s = (o = t.getState()).onError) == null || s.call(o, "004", Kn.error004())),
        t.setState({ width: i.width || 500, height: i.height || 500 });
    };
    return (
      r(),
      window.addEventListener("resize", r),
      e.current && ((n = new ResizeObserver(() => r())), n.observe(e.current)),
      () => {
        window.removeEventListener("resize", r), n && e.current && n.unobserve(e.current);
      }
    );
  }, []);
}
const v0 = { position: "absolute", width: "100%", height: "100%", top: 0, left: 0 },
  E$ = (e, t) => e.x !== t.x || e.y !== t.y || e.zoom !== t.k,
  Ja = (e) => ({ x: e.x, y: e.y, zoom: e.k }),
  Si = (e, t) => e.target.closest(`.${t}`),
  yx = (e, t) => t === 2 && Array.isArray(e) && e.includes(2),
  wx = (e) => {
    const t = e.ctrlKey && cl() ? 10 : 1;
    return -e.deltaY * (e.deltaMode === 1 ? 0.05 : e.deltaMode ? 1 : 0.002) * t;
  },
  C$ = (e) => ({
    d3Zoom: e.d3Zoom,
    d3Selection: e.d3Selection,
    d3ZoomHandler: e.d3ZoomHandler,
    userSelectionActive: e.userSelectionActive,
  }),
  T$ = ({
    onMove: e,
    onMoveStart: t,
    onMoveEnd: n,
    onPaneContextMenu: r,
    zoomOnScroll: i = !0,
    zoomOnPinch: o = !0,
    panOnScroll: s = !1,
    panOnScrollSpeed: a = 0.5,
    panOnScrollMode: u = Xr.Free,
    zoomOnDoubleClick: l = !0,
    elementsSelectable: c,
    panOnDrag: f = !0,
    defaultViewport: d,
    translateExtent: h,
    minZoom: v,
    maxZoom: p,
    zoomActivationKeyCode: y,
    preventScrolling: m = !0,
    children: g,
    noWheelClassName: w,
    noPanClassName: x,
  }) => {
    const b = _.useRef(),
      E = Fe(),
      C = _.useRef(!1),
      T = _.useRef(!1),
      P = _.useRef(null),
      M = _.useRef({ x: 0, y: 0, zoom: 0 }),
      { d3Zoom: I, d3Selection: j, d3ZoomHandler: q, userSelectionActive: S } = de(C$, He),
      O = Qs(y),
      A = _.useRef(0),
      F = _.useRef(!1),
      N = _.useRef();
    return (
      S$(P),
      _.useEffect(() => {
        if (P.current) {
          const k = P.current.getBoundingClientRect(),
            D = fA().scaleExtent([v, p]).translateExtent(h),
            V = Ot(P.current).call(D),
            $ = qn.translate(d.x, d.y).scale(po(d.zoom, v, p)),
            U = [
              [0, 0],
              [k.width, k.height],
            ],
            B = D.constrain()($, U, h);
          D.transform(V, B),
            D.wheelDelta(wx),
            E.setState({
              d3Zoom: D,
              d3Selection: V,
              d3ZoomHandler: V.on("wheel.zoom"),
              transform: [B.x, B.y, B.k],
              domNode: P.current.closest(".react-flow"),
            });
        }
      }, []),
      _.useEffect(() => {
        j &&
          I &&
          (s && !O && !S
            ? j.on(
                "wheel.zoom",
                (k) => {
                  if (Si(k, w)) return !1;
                  k.preventDefault(), k.stopImmediatePropagation();
                  const D = j.property("__zoom").k || 1;
                  if (k.ctrlKey && o) {
                    const ue = Xt(k),
                      se = wx(k),
                      oe = D * Math.pow(2, se);
                    I.scaleTo(j, oe, ue, k);
                    return;
                  }
                  const V = k.deltaMode === 1 ? 20 : 1;
                  let $ = u === Xr.Vertical ? 0 : k.deltaX * V,
                    U = u === Xr.Horizontal ? 0 : k.deltaY * V;
                  !cl() && k.shiftKey && u !== Xr.Vertical && (($ = k.deltaY * V), (U = 0)),
                    I.translateBy(j, -($ / D) * a, -(U / D) * a, { internal: !0 });
                  const B = Ja(j.property("__zoom")),
                    {
                      onViewportChangeStart: W,
                      onViewportChange: X,
                      onViewportChangeEnd: ee,
                    } = E.getState();
                  clearTimeout(N.current),
                    F.current || ((F.current = !0), t == null || t(k, B), W == null || W(B)),
                    F.current &&
                      (e == null || e(k, B),
                      X == null || X(B),
                      (N.current = setTimeout(() => {
                        n == null || n(k, B), ee == null || ee(B), (F.current = !1);
                      }, 150)));
                },
                { passive: !1 },
              )
            : typeof q < "u" &&
              j.on(
                "wheel.zoom",
                function (k, D) {
                  if ((!m && k.type === "wheel" && !k.ctrlKey) || Si(k, w)) return null;
                  k.preventDefault(), q.call(this, k, D);
                },
                { passive: !1 },
              ));
      }, [S, s, u, j, I, q, O, o, m, w, t, e, n]),
      _.useEffect(() => {
        I &&
          I.on("start", (k) => {
            var $, U;
            if (!k.sourceEvent || k.sourceEvent.internal) return null;
            A.current = ($ = k.sourceEvent) == null ? void 0 : $.button;
            const { onViewportChangeStart: D } = E.getState(),
              V = Ja(k.transform);
            (C.current = !0),
              (M.current = V),
              ((U = k.sourceEvent) == null ? void 0 : U.type) === "mousedown" &&
                E.setState({ paneDragging: !0 }),
              D == null || D(V),
              t == null || t(k.sourceEvent, V);
          });
      }, [I, t]),
      _.useEffect(() => {
        I &&
          (S && !C.current
            ? I.on("zoom", null)
            : S ||
              I.on("zoom", (k) => {
                var V;
                const { onViewportChange: D } = E.getState();
                if (
                  (E.setState({ transform: [k.transform.x, k.transform.y, k.transform.k] }),
                  (T.current = !!(r && yx(f, A.current ?? 0))),
                  (e || D) && !((V = k.sourceEvent) != null && V.internal))
                ) {
                  const $ = Ja(k.transform);
                  D == null || D($), e == null || e(k.sourceEvent, $);
                }
              }));
      }, [S, I, e, f, r]),
      _.useEffect(() => {
        I &&
          I.on("end", (k) => {
            if (!k.sourceEvent || k.sourceEvent.internal) return null;
            const { onViewportChangeEnd: D } = E.getState();
            if (
              ((C.current = !1),
              E.setState({ paneDragging: !1 }),
              r && yx(f, A.current ?? 0) && !T.current && r(k.sourceEvent),
              (T.current = !1),
              (n || D) && E$(M.current, k.transform))
            ) {
              const V = Ja(k.transform);
              (M.current = V),
                clearTimeout(b.current),
                (b.current = setTimeout(
                  () => {
                    D == null || D(V), n == null || n(k.sourceEvent, V);
                  },
                  s ? 150 : 0,
                ));
            }
          });
      }, [I, s, f, n, r]),
      _.useEffect(() => {
        I &&
          I.filter((k) => {
            const D = O || i,
              V = o && k.ctrlKey;
            if (
              (f === !0 || (Array.isArray(f) && f.includes(1))) &&
              k.button === 1 &&
              k.type === "mousedown" &&
              (Si(k, "react-flow__node") || Si(k, "react-flow__edge"))
            )
              return !0;
            if (
              (!f && !D && !s && !l && !o) ||
              S ||
              (!l && k.type === "dblclick") ||
              (Si(k, w) && k.type === "wheel") ||
              (Si(k, x) && (k.type !== "wheel" || (s && k.type === "wheel" && !O))) ||
              (!o && k.ctrlKey && k.type === "wheel") ||
              (!D && !s && !V && k.type === "wheel") ||
              (!f && (k.type === "mousedown" || k.type === "touchstart")) ||
              (Array.isArray(f) && !f.includes(k.button) && k.type === "mousedown")
            )
              return !1;
            const $ = (Array.isArray(f) && f.includes(k.button)) || !k.button || k.button <= 1;
            return (!k.ctrlKey || k.type === "wheel") && $;
          });
      }, [S, I, i, o, s, l, f, c, O]),
      L.createElement("div", { className: "react-flow__renderer", ref: P, style: v0 }, g)
    );
  },
  k$ = (e) => ({
    userSelectionActive: e.userSelectionActive,
    userSelectionRect: e.userSelectionRect,
  });
function R$() {
  const { userSelectionActive: e, userSelectionRect: t } = de(k$, He);
  return e && t
    ? L.createElement("div", {
        className: "react-flow__selection react-flow__container",
        style: { width: t.width, height: t.height, transform: `translate(${t.x}px, ${t.y}px)` },
      })
    : null;
}
function xx(e, t) {
  const n = t.parentNode || t.parentId,
    r = e.find((i) => i.id === n);
  if (r) {
    const i = t.position.x + t.width - r.width,
      o = t.position.y + t.height - r.height;
    if (i > 0 || o > 0 || t.position.x < 0 || t.position.y < 0) {
      if (
        ((r.style = { ...r.style }),
        (r.style.width = r.style.width ?? r.width),
        (r.style.height = r.style.height ?? r.height),
        i > 0 && (r.style.width += i),
        o > 0 && (r.style.height += o),
        t.position.x < 0)
      ) {
        const s = Math.abs(t.position.x);
        (r.position.x = r.position.x - s), (r.style.width += s), (t.position.x = 0);
      }
      if (t.position.y < 0) {
        const s = Math.abs(t.position.y);
        (r.position.y = r.position.y - s), (r.style.height += s), (t.position.y = 0);
      }
      (r.width = r.style.width), (r.height = r.style.height);
    }
  }
}
function zA(e, t) {
  if (e.some((r) => r.type === "reset"))
    return e.filter((r) => r.type === "reset").map((r) => r.item);
  const n = e.filter((r) => r.type === "add").map((r) => r.item);
  return t.reduce((r, i) => {
    const o = e.filter((a) => a.id === i.id);
    if (o.length === 0) return r.push(i), r;
    const s = { ...i };
    for (const a of o)
      if (a)
        switch (a.type) {
          case "select": {
            s.selected = a.selected;
            break;
          }
          case "position": {
            typeof a.position < "u" && (s.position = a.position),
              typeof a.positionAbsolute < "u" && (s.positionAbsolute = a.positionAbsolute),
              typeof a.dragging < "u" && (s.dragging = a.dragging),
              s.expandParent && xx(r, s);
            break;
          }
          case "dimensions": {
            typeof a.dimensions < "u" &&
              ((s.width = a.dimensions.width), (s.height = a.dimensions.height)),
              typeof a.updateStyle < "u" && (s.style = { ...(s.style || {}), ...a.dimensions }),
              typeof a.resizing == "boolean" && (s.resizing = a.resizing),
              s.expandParent && xx(r, s);
            break;
          }
          case "remove":
            return r;
        }
    return r.push(s), r;
  }, n);
}
function BA(e, t) {
  return zA(e, t);
}
function P$(e, t) {
  return zA(e, t);
}
const dr = (e, t) => ({ id: e, type: "select", selected: t });
function qi(e, t) {
  return e.reduce((n, r) => {
    const i = t.includes(r.id);
    return (
      !r.selected && i
        ? ((r.selected = !0), n.push(dr(r.id, !0)))
        : r.selected && !i && ((r.selected = !1), n.push(dr(r.id, !1))),
      n
    );
  }, []);
}
const ff = (e, t) => (n) => {
    n.target === t.current && (e == null || e(n));
  },
  A$ = (e) => ({
    userSelectionActive: e.userSelectionActive,
    elementsSelectable: e.elementsSelectable,
    dragging: e.paneDragging,
  }),
  UA = _.memo(
    ({
      isSelecting: e,
      selectionMode: t = mo.Full,
      panOnDrag: n,
      onSelectionStart: r,
      onSelectionEnd: i,
      onPaneClick: o,
      onPaneContextMenu: s,
      onPaneScroll: a,
      onPaneMouseEnter: u,
      onPaneMouseMove: l,
      onPaneMouseLeave: c,
      children: f,
    }) => {
      const d = _.useRef(null),
        h = Fe(),
        v = _.useRef(0),
        p = _.useRef(0),
        y = _.useRef(),
        { userSelectionActive: m, elementsSelectable: g, dragging: w } = de(A$, He),
        x = () => {
          h.setState({ userSelectionActive: !1, userSelectionRect: null }),
            (v.current = 0),
            (p.current = 0);
        },
        b = (q) => {
          o == null || o(q),
            h.getState().resetSelectedElements(),
            h.setState({ nodesSelectionActive: !1 });
        },
        E = (q) => {
          if (Array.isArray(n) && n != null && n.includes(2)) {
            q.preventDefault();
            return;
          }
          s == null || s(q);
        },
        C = a ? (q) => a(q) : void 0,
        T = (q) => {
          const { resetSelectedElements: S, domNode: O } = h.getState();
          if (
            ((y.current = O == null ? void 0 : O.getBoundingClientRect()),
            !g || !e || q.button !== 0 || q.target !== d.current || !y.current)
          )
            return;
          const { x: A, y: F } = kr(q, y.current);
          S(),
            h.setState({
              userSelectionRect: { width: 0, height: 0, startX: A, startY: F, x: A, y: F },
            }),
            r == null || r(q);
        },
        P = (q) => {
          const {
            userSelectionRect: S,
            nodeInternals: O,
            edges: A,
            transform: F,
            onNodesChange: N,
            onEdgesChange: k,
            nodeOrigin: D,
            getNodes: V,
          } = h.getState();
          if (!e || !y.current || !S) return;
          h.setState({ userSelectionActive: !0, nodesSelectionActive: !1 });
          const $ = kr(q, y.current),
            U = S.startX ?? 0,
            B = S.startY ?? 0,
            W = {
              ...S,
              x: $.x < U ? $.x : U,
              y: $.y < B ? $.y : B,
              width: Math.abs($.x - U),
              height: Math.abs($.y - B),
            },
            X = V(),
            ee = EA(O, W, F, t === mo.Partial, !0, D),
            ue = CA(ee, A).map((oe) => oe.id),
            se = ee.map((oe) => oe.id);
          if (v.current !== se.length) {
            v.current = se.length;
            const oe = qi(X, se);
            oe.length && (N == null || N(oe));
          }
          if (p.current !== ue.length) {
            p.current = ue.length;
            const oe = qi(A, ue);
            oe.length && (k == null || k(oe));
          }
          h.setState({ userSelectionRect: W });
        },
        M = (q) => {
          if (q.button !== 0) return;
          const { userSelectionRect: S } = h.getState();
          !m && S && q.target === d.current && (b == null || b(q)),
            h.setState({ nodesSelectionActive: v.current > 0 }),
            x(),
            i == null || i(q);
        },
        I = (q) => {
          m && (h.setState({ nodesSelectionActive: v.current > 0 }), i == null || i(q)), x();
        },
        j = g && (e || m);
      return L.createElement(
        "div",
        {
          className: Ze(["react-flow__pane", { dragging: w, selection: e }]),
          onClick: j ? void 0 : ff(b, d),
          onContextMenu: ff(E, d),
          onWheel: ff(C, d),
          onMouseEnter: j ? void 0 : u,
          onMouseDown: j ? T : void 0,
          onMouseMove: j ? P : l,
          onMouseUp: j ? M : void 0,
          onMouseLeave: j ? I : c,
          ref: d,
          style: v0,
        },
        f,
        L.createElement(R$, null),
      );
    },
  );
UA.displayName = "Pane";
function HA(e, t) {
  const n = e.parentNode || e.parentId;
  if (!n) return !1;
  const r = t.get(n);
  return r ? (r.selected ? !0 : HA(r, t)) : !1;
}
function _x(e, t, n) {
  let r = e;
  do {
    if (r != null && r.matches(t)) return !0;
    if (r === n.current) return !1;
    r = r.parentElement;
  } while (r);
  return !1;
}
function N$(e, t, n, r) {
  return Array.from(e.values())
    .filter(
      (i) =>
        (i.selected || i.id === r) &&
        (!i.parentNode || i.parentId || !HA(i, e)) &&
        (i.draggable || (t && typeof i.draggable > "u")),
    )
    .map((i) => {
      var o, s;
      return {
        id: i.id,
        position: i.position || { x: 0, y: 0 },
        positionAbsolute: i.positionAbsolute || { x: 0, y: 0 },
        distance: {
          x: n.x - (((o = i.positionAbsolute) == null ? void 0 : o.x) ?? 0),
          y: n.y - (((s = i.positionAbsolute) == null ? void 0 : s.y) ?? 0),
        },
        delta: { x: 0, y: 0 },
        extent: i.extent,
        parentNode: i.parentNode || i.parentId,
        parentId: i.parentNode || i.parentId,
        width: i.width,
        height: i.height,
        expandParent: i.expandParent,
      };
    });
}
function M$(e, t) {
  return !t || t === "parent" ? t : [t[0], [t[1][0] - (e.width || 0), t[1][1] - (e.height || 0)]];
}
function GA(e, t, n, r, i = [0, 0], o) {
  const s = M$(e, e.extent || r);
  let a = s;
  const u = e.parentNode || e.parentId;
  if (e.extent === "parent" && !e.expandParent)
    if (u && e.width && e.height) {
      const f = n.get(u),
        { x: d, y: h } = ni(f, i).positionAbsolute;
      a =
        f && Ft(d) && Ft(h) && Ft(f.width) && Ft(f.height)
          ? [
              [d + e.width * i[0], h + e.height * i[1]],
              [d + f.width - e.width + e.width * i[0], h + f.height - e.height + e.height * i[1]],
            ]
          : a;
    } else o == null || o("005", Kn.error005()), (a = s);
  else if (e.extent && u && e.extent !== "parent") {
    const f = n.get(u),
      { x: d, y: h } = ni(f, i).positionAbsolute;
    a = [
      [e.extent[0][0] + d, e.extent[0][1] + h],
      [e.extent[1][0] + d, e.extent[1][1] + h],
    ];
  }
  let l = { x: 0, y: 0 };
  if (u) {
    const f = n.get(u);
    l = ni(f, i).positionAbsolute;
  }
  const c = a && a !== "parent" ? c0(t, a) : t;
  return { position: { x: c.x - l.x, y: c.y - l.y }, positionAbsolute: c };
}
function df({ nodeId: e, dragItems: t, nodeInternals: n }) {
  const r = t.map((i) => ({
    ...n.get(i.id),
    position: i.position,
    positionAbsolute: i.positionAbsolute,
  }));
  return [e ? r.find((i) => i.id === e) : r[0], r];
}
const bx = (e, t, n, r) => {
  const i = t.querySelectorAll(e);
  if (!i || !i.length) return null;
  const o = Array.from(i),
    s = t.getBoundingClientRect(),
    a = { x: s.width * r[0], y: s.height * r[1] };
  return o.map((u) => {
    const l = u.getBoundingClientRect();
    return {
      id: u.getAttribute("data-handleid"),
      position: u.getAttribute("data-handlepos"),
      x: (l.left - s.left - a.x) / n,
      y: (l.top - s.top - a.y) / n,
      ...l0(u),
    };
  });
};
function Wo(e, t, n) {
  return n === void 0
    ? n
    : (r) => {
        const i = t().nodeInternals.get(e);
        i && n(r, { ...i });
      };
}
function Lv({ id: e, store: t, unselect: n = !1, nodeRef: r }) {
  const {
      addSelectedNodes: i,
      unselectNodesAndEdges: o,
      multiSelectionActive: s,
      nodeInternals: a,
      onError: u,
    } = t.getState(),
    l = a.get(e);
  if (!l) {
    u == null || u("012", Kn.error012(e));
    return;
  }
  t.setState({ nodesSelectionActive: !1 }),
    l.selected
      ? (n || (l.selected && s)) &&
        (o({ nodes: [l], edges: [] }),
        requestAnimationFrame(() => {
          var c;
          return (c = r == null ? void 0 : r.current) == null ? void 0 : c.blur();
        }))
      : i([e]);
}
function I$() {
  const e = Fe();
  return _.useCallback(({ sourceEvent: n }) => {
    const { transform: r, snapGrid: i, snapToGrid: o } = e.getState(),
      s = n.touches ? n.touches[0].clientX : n.clientX,
      a = n.touches ? n.touches[0].clientY : n.clientY,
      u = { x: (s - r[0]) / r[2], y: (a - r[1]) / r[2] };
    return {
      xSnapped: o ? i[0] * Math.round(u.x / i[0]) : u.x,
      ySnapped: o ? i[1] * Math.round(u.y / i[1]) : u.y,
      ...u,
    };
  }, []);
}
function hf(e) {
  return (t, n, r) => (e == null ? void 0 : e(t, r));
}
function WA({
  nodeRef: e,
  disabled: t = !1,
  noDragClassName: n,
  handleSelector: r,
  nodeId: i,
  isSelectable: o,
  selectNodesOnDrag: s,
}) {
  const a = Fe(),
    [u, l] = _.useState(!1),
    c = _.useRef([]),
    f = _.useRef({ x: null, y: null }),
    d = _.useRef(0),
    h = _.useRef(null),
    v = _.useRef({ x: 0, y: 0 }),
    p = _.useRef(null),
    y = _.useRef(!1),
    m = _.useRef(!1),
    g = _.useRef(!1),
    w = I$();
  return (
    _.useEffect(() => {
      if (e != null && e.current) {
        const x = Ot(e.current),
          b = ({ x: T, y: P }) => {
            const {
              nodeInternals: M,
              onNodeDrag: I,
              onSelectionDrag: j,
              updateNodePositions: q,
              nodeExtent: S,
              snapGrid: O,
              snapToGrid: A,
              nodeOrigin: F,
              onError: N,
            } = a.getState();
            f.current = { x: T, y: P };
            let k = !1,
              D = { x: 0, y: 0, x2: 0, y2: 0 };
            if (c.current.length > 1 && S) {
              const $ = Xl(c.current, F);
              D = Zs($);
            }
            if (
              ((c.current = c.current.map(($) => {
                const U = { x: T - $.distance.x, y: P - $.distance.y };
                A && ((U.x = O[0] * Math.round(U.x / O[0])), (U.y = O[1] * Math.round(U.y / O[1])));
                const B = [
                  [S[0][0], S[0][1]],
                  [S[1][0], S[1][1]],
                ];
                c.current.length > 1 &&
                  S &&
                  !$.extent &&
                  ((B[0][0] = $.positionAbsolute.x - D.x + S[0][0]),
                  (B[1][0] = $.positionAbsolute.x + ($.width ?? 0) - D.x2 + S[1][0]),
                  (B[0][1] = $.positionAbsolute.y - D.y + S[0][1]),
                  (B[1][1] = $.positionAbsolute.y + ($.height ?? 0) - D.y2 + S[1][1]));
                const W = GA($, U, M, B, F, N);
                return (
                  (k = k || $.position.x !== W.position.x || $.position.y !== W.position.y),
                  ($.position = W.position),
                  ($.positionAbsolute = W.positionAbsolute),
                  $
                );
              })),
              !k)
            )
              return;
            q(c.current, !0, !0), l(!0);
            const V = i ? I : hf(j);
            if (V && p.current) {
              const [$, U] = df({ nodeId: i, dragItems: c.current, nodeInternals: M });
              V(p.current, $, U);
            }
          },
          E = () => {
            if (!h.current) return;
            const [T, P] = hA(v.current, h.current);
            if (T !== 0 || P !== 0) {
              const { transform: M, panBy: I } = a.getState();
              (f.current.x = (f.current.x ?? 0) - T / M[2]),
                (f.current.y = (f.current.y ?? 0) - P / M[2]),
                I({ x: T, y: P }) && b(f.current);
            }
            d.current = requestAnimationFrame(E);
          },
          C = (T) => {
            var F;
            const {
              nodeInternals: P,
              multiSelectionActive: M,
              nodesDraggable: I,
              unselectNodesAndEdges: j,
              onNodeDragStart: q,
              onSelectionDragStart: S,
            } = a.getState();
            m.current = !0;
            const O = i ? q : hf(S);
            (!s || !o) && !M && i && (((F = P.get(i)) != null && F.selected) || j()),
              i && o && s && Lv({ id: i, store: a, nodeRef: e });
            const A = w(T);
            if (((f.current = A), (c.current = N$(P, I, A, i)), O && c.current)) {
              const [N, k] = df({ nodeId: i, dragItems: c.current, nodeInternals: P });
              O(T.sourceEvent, N, k);
            }
          };
        if (t) x.on(".drag", null);
        else {
          const T = Uj()
            .on("start", (P) => {
              const { domNode: M, nodeDragThreshold: I } = a.getState();
              I === 0 && C(P), (g.current = !1);
              const j = w(P);
              (f.current = j),
                (h.current = (M == null ? void 0 : M.getBoundingClientRect()) || null),
                (v.current = kr(P.sourceEvent, h.current));
            })
            .on("drag", (P) => {
              var q, S;
              const M = w(P),
                { autoPanOnNodeDrag: I, nodeDragThreshold: j } = a.getState();
              if (
                (P.sourceEvent.type === "touchmove" &&
                  P.sourceEvent.touches.length > 1 &&
                  (g.current = !0),
                !g.current)
              ) {
                if ((!y.current && m.current && I && ((y.current = !0), E()), !m.current)) {
                  const O =
                      M.xSnapped -
                      (((q = f == null ? void 0 : f.current) == null ? void 0 : q.x) ?? 0),
                    A =
                      M.ySnapped -
                      (((S = f == null ? void 0 : f.current) == null ? void 0 : S.y) ?? 0);
                  Math.sqrt(O * O + A * A) > j && C(P);
                }
                (f.current.x !== M.xSnapped || f.current.y !== M.ySnapped) &&
                  c.current &&
                  m.current &&
                  ((p.current = P.sourceEvent), (v.current = kr(P.sourceEvent, h.current)), b(M));
              }
            })
            .on("end", (P) => {
              if (
                !(!m.current || g.current) &&
                (l(!1),
                (y.current = !1),
                (m.current = !1),
                cancelAnimationFrame(d.current),
                c.current)
              ) {
                const {
                    updateNodePositions: M,
                    nodeInternals: I,
                    onNodeDragStop: j,
                    onSelectionDragStop: q,
                  } = a.getState(),
                  S = i ? j : hf(q);
                if ((M(c.current, !1, !1), S)) {
                  const [O, A] = df({ nodeId: i, dragItems: c.current, nodeInternals: I });
                  S(P.sourceEvent, O, A);
                }
              }
            })
            .filter((P) => {
              const M = P.target;
              return !P.button && (!n || !_x(M, `.${n}`, e)) && (!r || _x(M, r, e));
            });
          return (
            x.call(T),
            () => {
              x.on(".drag", null);
            }
          );
        }
      }
    }, [e, t, n, r, o, a, i, s, w]),
    u
  );
}
function KA() {
  const e = Fe();
  return _.useCallback((n) => {
    const {
        nodeInternals: r,
        nodeExtent: i,
        updateNodePositions: o,
        getNodes: s,
        snapToGrid: a,
        snapGrid: u,
        onError: l,
        nodesDraggable: c,
      } = e.getState(),
      f = s().filter((g) => g.selected && (g.draggable || (c && typeof g.draggable > "u"))),
      d = a ? u[0] : 5,
      h = a ? u[1] : 5,
      v = n.isShiftPressed ? 4 : 1,
      p = n.x * d * v,
      y = n.y * h * v,
      m = f.map((g) => {
        if (g.positionAbsolute) {
          const w = { x: g.positionAbsolute.x + p, y: g.positionAbsolute.y + y };
          a && ((w.x = u[0] * Math.round(w.x / u[0])), (w.y = u[1] * Math.round(w.y / u[1])));
          const { positionAbsolute: x, position: b } = GA(g, w, r, i, void 0, l);
          (g.position = b), (g.positionAbsolute = x);
        }
        return g;
      });
    o(m, !0, !1);
  }, []);
}
const eo = {
  ArrowUp: { x: 0, y: -1 },
  ArrowDown: { x: 0, y: 1 },
  ArrowLeft: { x: -1, y: 0 },
  ArrowRight: { x: 1, y: 0 },
};
var Ko = (e) => {
  const t = ({
    id: n,
    type: r,
    data: i,
    xPos: o,
    yPos: s,
    xPosOrigin: a,
    yPosOrigin: u,
    selected: l,
    onClick: c,
    onMouseEnter: f,
    onMouseMove: d,
    onMouseLeave: h,
    onContextMenu: v,
    onDoubleClick: p,
    style: y,
    className: m,
    isDraggable: g,
    isSelectable: w,
    isConnectable: x,
    isFocusable: b,
    selectNodesOnDrag: E,
    sourcePosition: C,
    targetPosition: T,
    hidden: P,
    resizeObserver: M,
    dragHandle: I,
    zIndex: j,
    isParent: q,
    noDragClassName: S,
    noPanClassName: O,
    initialized: A,
    disableKeyboardA11y: F,
    ariaLabel: N,
    rfId: k,
    hasHandleBounds: D,
  }) => {
    const V = Fe(),
      $ = _.useRef(null),
      U = _.useRef(null),
      B = _.useRef(C),
      W = _.useRef(T),
      X = _.useRef(r),
      ee = w || g || c || f || d || h,
      ue = KA(),
      se = Wo(n, V.getState, f),
      oe = Wo(n, V.getState, d),
      De = Wo(n, V.getState, h),
      Re = Wo(n, V.getState, v),
      Ge = Wo(n, V.getState, p),
      je = (K) => {
        const { nodeDragThreshold: G } = V.getState();
        if ((w && (!E || !g || G > 0) && Lv({ id: n, store: V, nodeRef: $ }), c)) {
          const Ee = V.getState().nodeInternals.get(n);
          Ee && c(K, { ...Ee });
        }
      },
      Q = (K) => {
        if (!Mv(K) && !F)
          if (vA.includes(K.key) && w) {
            const G = K.key === "Escape";
            Lv({ id: n, store: V, unselect: G, nodeRef: $ });
          } else
            g &&
              l &&
              Object.prototype.hasOwnProperty.call(eo, K.key) &&
              (V.setState({
                ariaLiveMessage: `Moved selected node ${K.key.replace("Arrow", "").toLowerCase()}. New position, x: ${~~o}, y: ${~~s}`,
              }),
              ue({ x: eo[K.key].x, y: eo[K.key].y, isShiftPressed: K.shiftKey }));
      };
    _.useEffect(
      () => () => {
        U.current && (M == null || M.unobserve(U.current), (U.current = null));
      },
      [],
    ),
      _.useEffect(() => {
        if ($.current && !P) {
          const K = $.current;
          (!A || !D || U.current !== K) &&
            (U.current && (M == null || M.unobserve(U.current)),
            M == null || M.observe(K),
            (U.current = K));
        }
      }, [P, A, D]),
      _.useEffect(() => {
        const K = X.current !== r,
          G = B.current !== C,
          Ee = W.current !== T;
        $.current &&
          (K || G || Ee) &&
          (K && (X.current = r),
          G && (B.current = C),
          Ee && (W.current = T),
          V.getState().updateNodeDimensions([{ id: n, nodeElement: $.current, forceUpdate: !0 }]));
      }, [n, r, C, T]);
    const Ve = WA({
      nodeRef: $,
      disabled: P || !g,
      noDragClassName: S,
      handleSelector: I,
      nodeId: n,
      isSelectable: w,
      selectNodesOnDrag: E,
    });
    return P
      ? null
      : L.createElement(
          "div",
          {
            className: Ze([
              "react-flow__node",
              `react-flow__node-${r}`,
              { [O]: g },
              m,
              { selected: l, selectable: w, parent: q, dragging: Ve },
            ]),
            ref: $,
            style: {
              zIndex: j,
              transform: `translate(${a}px,${u}px)`,
              pointerEvents: ee ? "all" : "none",
              visibility: A ? "visible" : "hidden",
              ...y,
            },
            "data-id": n,
            "data-testid": `rf__node-${n}`,
            onMouseEnter: se,
            onMouseMove: oe,
            onMouseLeave: De,
            onContextMenu: Re,
            onClick: je,
            onDoubleClick: Ge,
            onKeyDown: b ? Q : void 0,
            tabIndex: b ? 0 : void 0,
            role: b ? "button" : void 0,
            "aria-describedby": F ? void 0 : `${FA}-${k}`,
            "aria-label": N,
          },
          L.createElement(
            Wq,
            { value: n },
            L.createElement(e, {
              id: n,
              data: i,
              type: r,
              xPos: o,
              yPos: s,
              selected: l,
              isConnectable: x,
              sourcePosition: C,
              targetPosition: T,
              dragging: Ve,
              dragHandle: I,
              zIndex: j,
            }),
          ),
        );
  };
  return (t.displayName = "NodeWrapper"), _.memo(t);
};
const D$ = (e) => {
  const t = e.getNodes().filter((n) => n.selected);
  return {
    ...Xl(t, e.nodeOrigin),
    transformString: `translate(${e.transform[0]}px,${e.transform[1]}px) scale(${e.transform[2]})`,
    userSelectionActive: e.userSelectionActive,
  };
};
function O$({ onSelectionContextMenu: e, noPanClassName: t, disableKeyboardA11y: n }) {
  const r = Fe(),
    { width: i, height: o, x: s, y: a, transformString: u, userSelectionActive: l } = de(D$, He),
    c = KA(),
    f = _.useRef(null);
  if (
    (_.useEffect(() => {
      var v;
      n || (v = f.current) == null || v.focus({ preventScroll: !0 });
    }, [n]),
    WA({ nodeRef: f }),
    l || !i || !o)
  )
    return null;
  const d = e
      ? (v) => {
          const p = r
            .getState()
            .getNodes()
            .filter((y) => y.selected);
          e(v, p);
        }
      : void 0,
    h = (v) => {
      Object.prototype.hasOwnProperty.call(eo, v.key) &&
        c({ x: eo[v.key].x, y: eo[v.key].y, isShiftPressed: v.shiftKey });
    };
  return L.createElement(
    "div",
    {
      className: Ze(["react-flow__nodesselection", "react-flow__container", t]),
      style: { transform: u },
    },
    L.createElement("div", {
      ref: f,
      className: "react-flow__nodesselection-rect",
      onContextMenu: d,
      tabIndex: n ? void 0 : -1,
      onKeyDown: n ? void 0 : h,
      style: { width: i, height: o, top: a, left: s },
    }),
  );
}
var L$ = _.memo(O$);
const F$ = (e) => e.nodesSelectionActive,
  YA = ({
    children: e,
    onPaneClick: t,
    onPaneMouseEnter: n,
    onPaneMouseMove: r,
    onPaneMouseLeave: i,
    onPaneContextMenu: o,
    onPaneScroll: s,
    deleteKeyCode: a,
    onMove: u,
    onMoveStart: l,
    onMoveEnd: c,
    selectionKeyCode: f,
    selectionOnDrag: d,
    selectionMode: h,
    onSelectionStart: v,
    onSelectionEnd: p,
    multiSelectionKeyCode: y,
    panActivationKeyCode: m,
    zoomActivationKeyCode: g,
    elementsSelectable: w,
    zoomOnScroll: x,
    zoomOnPinch: b,
    panOnScroll: E,
    panOnScrollSpeed: C,
    panOnScrollMode: T,
    zoomOnDoubleClick: P,
    panOnDrag: M,
    defaultViewport: I,
    translateExtent: j,
    minZoom: q,
    maxZoom: S,
    preventScrolling: O,
    onSelectionContextMenu: A,
    noWheelClassName: F,
    noPanClassName: N,
    disableKeyboardA11y: k,
  }) => {
    const D = de(F$),
      V = Qs(f),
      $ = Qs(m),
      U = $ || M,
      B = $ || E,
      W = V || (d && U !== !0);
    return (
      b$({ deleteKeyCode: a, multiSelectionKeyCode: y }),
      L.createElement(
        T$,
        {
          onMove: u,
          onMoveStart: l,
          onMoveEnd: c,
          onPaneContextMenu: o,
          elementsSelectable: w,
          zoomOnScroll: x,
          zoomOnPinch: b,
          panOnScroll: B,
          panOnScrollSpeed: C,
          panOnScrollMode: T,
          zoomOnDoubleClick: P,
          panOnDrag: !V && U,
          defaultViewport: I,
          translateExtent: j,
          minZoom: q,
          maxZoom: S,
          zoomActivationKeyCode: g,
          preventScrolling: O,
          noWheelClassName: F,
          noPanClassName: N,
        },
        L.createElement(
          UA,
          {
            onSelectionStart: v,
            onSelectionEnd: p,
            onPaneClick: t,
            onPaneMouseEnter: n,
            onPaneMouseMove: r,
            onPaneMouseLeave: i,
            onPaneContextMenu: o,
            onPaneScroll: s,
            panOnDrag: U,
            isSelecting: !!W,
            selectionMode: h,
          },
          e,
          D &&
            L.createElement(L$, {
              onSelectionContextMenu: A,
              noPanClassName: N,
              disableKeyboardA11y: k,
            }),
        ),
      )
    );
  };
YA.displayName = "FlowRenderer";
var j$ = _.memo(YA);
function V$(e) {
  return de(
    _.useCallback(
      (n) =>
        e
          ? EA(n.nodeInternals, { x: 0, y: 0, width: n.width, height: n.height }, n.transform, !0)
          : n.getNodes(),
      [e],
    ),
  );
}
function q$(e) {
  const t = {
      input: Ko(e.input || IA),
      default: Ko(e.default || Ov),
      output: Ko(e.output || OA),
      group: Ko(e.group || g0),
    },
    n = {},
    r = Object.keys(e)
      .filter((i) => !["input", "default", "output", "group"].includes(i))
      .reduce((i, o) => ((i[o] = Ko(e[o] || Ov)), i), n);
  return { ...t, ...r };
}
const $$ = ({ x: e, y: t, width: n, height: r, origin: i }) =>
    !n || !r
      ? { x: e, y: t }
      : i[0] < 0 || i[1] < 0 || i[0] > 1 || i[1] > 1
        ? { x: e, y: t }
        : { x: e - n * i[0], y: t - r * i[1] },
  z$ = (e) => ({
    nodesDraggable: e.nodesDraggable,
    nodesConnectable: e.nodesConnectable,
    nodesFocusable: e.nodesFocusable,
    elementsSelectable: e.elementsSelectable,
    updateNodeDimensions: e.updateNodeDimensions,
    onError: e.onError,
  }),
  XA = (e) => {
    const {
        nodesDraggable: t,
        nodesConnectable: n,
        nodesFocusable: r,
        elementsSelectable: i,
        updateNodeDimensions: o,
        onError: s,
      } = de(z$, He),
      a = V$(e.onlyRenderVisibleElements),
      u = _.useRef(),
      l = _.useMemo(() => {
        if (typeof ResizeObserver > "u") return null;
        const c = new ResizeObserver((f) => {
          const d = f.map((h) => ({
            id: h.target.getAttribute("data-id"),
            nodeElement: h.target,
            forceUpdate: !0,
          }));
          o(d);
        });
        return (u.current = c), c;
      }, []);
    return (
      _.useEffect(
        () => () => {
          var c;
          (c = u == null ? void 0 : u.current) == null || c.disconnect();
        },
        [],
      ),
      L.createElement(
        "div",
        { className: "react-flow__nodes", style: v0 },
        a.map((c) => {
          var b, E, C;
          let f = c.type || "default";
          e.nodeTypes[f] || (s == null || s("003", Kn.error003(f)), (f = "default"));
          const d = e.nodeTypes[f] || e.nodeTypes.default,
            h = !!(c.draggable || (t && typeof c.draggable > "u")),
            v = !!(c.selectable || (i && typeof c.selectable > "u")),
            p = !!(c.connectable || (n && typeof c.connectable > "u")),
            y = !!(c.focusable || (r && typeof c.focusable > "u")),
            m = e.nodeExtent ? c0(c.positionAbsolute, e.nodeExtent) : c.positionAbsolute,
            g = (m == null ? void 0 : m.x) ?? 0,
            w = (m == null ? void 0 : m.y) ?? 0,
            x = $$({
              x: g,
              y: w,
              width: c.width ?? 0,
              height: c.height ?? 0,
              origin: e.nodeOrigin,
            });
          return L.createElement(d, {
            key: c.id,
            id: c.id,
            className: c.className,
            style: c.style,
            type: f,
            data: c.data,
            sourcePosition: c.sourcePosition || Y.Bottom,
            targetPosition: c.targetPosition || Y.Top,
            hidden: c.hidden,
            xPos: g,
            yPos: w,
            xPosOrigin: x.x,
            yPosOrigin: x.y,
            selectNodesOnDrag: e.selectNodesOnDrag,
            onClick: e.onNodeClick,
            onMouseEnter: e.onNodeMouseEnter,
            onMouseMove: e.onNodeMouseMove,
            onMouseLeave: e.onNodeMouseLeave,
            onContextMenu: e.onNodeContextMenu,
            onDoubleClick: e.onNodeDoubleClick,
            selected: !!c.selected,
            isDraggable: h,
            isSelectable: v,
            isConnectable: p,
            isFocusable: y,
            resizeObserver: l,
            dragHandle: c.dragHandle,
            zIndex: ((b = c[ke]) == null ? void 0 : b.z) ?? 0,
            isParent: !!((E = c[ke]) != null && E.isParent),
            noDragClassName: e.noDragClassName,
            noPanClassName: e.noPanClassName,
            initialized: !!c.width && !!c.height,
            rfId: e.rfId,
            disableKeyboardA11y: e.disableKeyboardA11y,
            ariaLabel: c.ariaLabel,
            hasHandleBounds: !!((C = c[ke]) != null && C.handleBounds),
          });
        }),
      )
    );
  };
XA.displayName = "NodeRenderer";
var B$ = _.memo(XA);
const U$ = (e, t, n) => (n === Y.Left ? e - t : n === Y.Right ? e + t : e),
  H$ = (e, t, n) => (n === Y.Top ? e - t : n === Y.Bottom ? e + t : e),
  Sx = "react-flow__edgeupdater",
  Ex = ({
    position: e,
    centerX: t,
    centerY: n,
    radius: r = 10,
    onMouseDown: i,
    onMouseEnter: o,
    onMouseOut: s,
    type: a,
  }) =>
    L.createElement("circle", {
      onMouseDown: i,
      onMouseEnter: o,
      onMouseOut: s,
      className: Ze([Sx, `${Sx}-${a}`]),
      cx: U$(t, r, e),
      cy: H$(n, r, e),
      r,
      stroke: "transparent",
      fill: "transparent",
    }),
  G$ = () => !0;
var Ei = (e) => {
  const t = ({
    id: n,
    className: r,
    type: i,
    data: o,
    onClick: s,
    onEdgeDoubleClick: a,
    selected: u,
    animated: l,
    label: c,
    labelStyle: f,
    labelShowBg: d,
    labelBgStyle: h,
    labelBgPadding: v,
    labelBgBorderRadius: p,
    style: y,
    source: m,
    target: g,
    sourceX: w,
    sourceY: x,
    targetX: b,
    targetY: E,
    sourcePosition: C,
    targetPosition: T,
    elementsSelectable: P,
    hidden: M,
    sourceHandleId: I,
    targetHandleId: j,
    onContextMenu: q,
    onMouseEnter: S,
    onMouseMove: O,
    onMouseLeave: A,
    reconnectRadius: F,
    onReconnect: N,
    onReconnectStart: k,
    onReconnectEnd: D,
    markerEnd: V,
    markerStart: $,
    rfId: U,
    ariaLabel: B,
    isFocusable: W,
    isReconnectable: X,
    pathOptions: ee,
    interactionWidth: ue,
    disableKeyboardA11y: se,
  }) => {
    const oe = _.useRef(null),
      [De, Re] = _.useState(!1),
      [Ge, je] = _.useState(!1),
      Q = Fe(),
      Ve = _.useMemo(() => `url('#${Iv($, U)}')`, [$, U]),
      K = _.useMemo(() => `url('#${Iv(V, U)}')`, [V, U]);
    if (M) return null;
    const G = (qe) => {
        var cn;
        const {
            edges: dt,
            addSelectedEdges: Qe,
            unselectNodesAndEdges: ot,
            multiSelectionActive: jr,
          } = Q.getState(),
          kn = dt.find((Do) => Do.id === n);
        kn &&
          (P &&
            (Q.setState({ nodesSelectionActive: !1 }),
            kn.selected && jr
              ? (ot({ nodes: [], edges: [kn] }), (cn = oe.current) == null || cn.blur())
              : Qe([n])),
          s && s(qe, kn));
      },
      Ee = Go(n, Q.getState, a),
      Ut = Go(n, Q.getState, q),
      un = Go(n, Q.getState, S),
      it = Go(n, Q.getState, O),
      Pe = Go(n, Q.getState, A),
      ft = (qe, dt) => {
        if (qe.button !== 0) return;
        const { edges: Qe, isValidConnection: ot } = Q.getState(),
          jr = dt ? g : m,
          kn = (dt ? j : I) || null,
          cn = dt ? "target" : "source",
          Do = ot || G$,
          Rc = dt,
          Oo = Qe.find((Vr) => Vr.id === n);
        je(!0), k == null || k(qe, Oo, cn);
        const Pc = (Vr) => {
          je(!1), D == null || D(Vr, Oo, cn);
        };
        PA({
          event: qe,
          handleId: kn,
          nodeId: jr,
          onConnect: (Vr) => (N == null ? void 0 : N(Oo, Vr)),
          isTarget: Rc,
          getState: Q.getState,
          setState: Q.setState,
          isValidConnection: Do,
          edgeUpdaterType: cn,
          onReconnectEnd: Pc,
        });
      },
      Ht = (qe) => ft(qe, !0),
      Cn = (qe) => ft(qe, !1),
      ln = () => Re(!0),
      xt = () => Re(!1),
      Tn = !P && !s,
      tr = (qe) => {
        var dt;
        if (!se && vA.includes(qe.key) && P) {
          const { unselectNodesAndEdges: Qe, addSelectedEdges: ot, edges: jr } = Q.getState();
          qe.key === "Escape"
            ? ((dt = oe.current) == null || dt.blur(),
              Qe({ edges: [jr.find((cn) => cn.id === n)] }))
            : ot([n]);
        }
      };
    return L.createElement(
      "g",
      {
        className: Ze([
          "react-flow__edge",
          `react-flow__edge-${i}`,
          r,
          { selected: u, animated: l, inactive: Tn, updating: De },
        ]),
        onClick: G,
        onDoubleClick: Ee,
        onContextMenu: Ut,
        onMouseEnter: un,
        onMouseMove: it,
        onMouseLeave: Pe,
        onKeyDown: W ? tr : void 0,
        tabIndex: W ? 0 : void 0,
        role: W ? "button" : "img",
        "data-testid": `rf__edge-${n}`,
        "aria-label": B === null ? void 0 : B || `Edge from ${m} to ${g}`,
        "aria-describedby": W ? `${jA}-${U}` : void 0,
        ref: oe,
      },
      !Ge &&
        L.createElement(e, {
          id: n,
          source: m,
          target: g,
          selected: u,
          animated: l,
          label: c,
          labelStyle: f,
          labelShowBg: d,
          labelBgStyle: h,
          labelBgPadding: v,
          labelBgBorderRadius: p,
          data: o,
          style: y,
          sourceX: w,
          sourceY: x,
          targetX: b,
          targetY: E,
          sourcePosition: C,
          targetPosition: T,
          sourceHandleId: I,
          targetHandleId: j,
          markerStart: Ve,
          markerEnd: K,
          pathOptions: ee,
          interactionWidth: ue,
        }),
      X &&
        L.createElement(
          L.Fragment,
          null,
          (X === "source" || X === !0) &&
            L.createElement(Ex, {
              position: C,
              centerX: w,
              centerY: x,
              radius: F,
              onMouseDown: Ht,
              onMouseEnter: ln,
              onMouseOut: xt,
              type: "source",
            }),
          (X === "target" || X === !0) &&
            L.createElement(Ex, {
              position: T,
              centerX: b,
              centerY: E,
              radius: F,
              onMouseDown: Cn,
              onMouseEnter: ln,
              onMouseOut: xt,
              type: "target",
            }),
        ),
    );
  };
  return (t.displayName = "EdgeWrapper"), _.memo(t);
};
function W$(e) {
  const t = {
      default: Ei(e.default || dl),
      straight: Ei(e.bezier || h0),
      step: Ei(e.step || d0),
      smoothstep: Ei(e.step || Yl),
      simplebezier: Ei(e.simplebezier || f0),
    },
    n = {},
    r = Object.keys(e)
      .filter((i) => !["default", "bezier"].includes(i))
      .reduce((i, o) => ((i[o] = Ei(e[o] || dl)), i), n);
  return { ...t, ...r };
}
function Cx(e, t, n = null) {
  const r = ((n == null ? void 0 : n.x) || 0) + t.x,
    i = ((n == null ? void 0 : n.y) || 0) + t.y,
    o = (n == null ? void 0 : n.width) || t.width,
    s = (n == null ? void 0 : n.height) || t.height;
  switch (e) {
    case Y.Top:
      return { x: r + o / 2, y: i };
    case Y.Right:
      return { x: r + o, y: i + s / 2 };
    case Y.Bottom:
      return { x: r + o / 2, y: i + s };
    case Y.Left:
      return { x: r, y: i + s / 2 };
  }
}
function Tx(e, t) {
  return e ? (e.length === 1 || !t ? e[0] : (t && e.find((n) => n.id === t)) || null) : null;
}
const K$ = (e, t, n, r, i, o) => {
  const s = Cx(n, e, t),
    a = Cx(o, r, i);
  return { sourceX: s.x, sourceY: s.y, targetX: a.x, targetY: a.y };
};
function Y$({
  sourcePos: e,
  targetPos: t,
  sourceWidth: n,
  sourceHeight: r,
  targetWidth: i,
  targetHeight: o,
  width: s,
  height: a,
  transform: u,
}) {
  const l = {
    x: Math.min(e.x, t.x),
    y: Math.min(e.y, t.y),
    x2: Math.max(e.x + n, t.x + i),
    y2: Math.max(e.y + r, t.y + o),
  };
  l.x === l.x2 && (l.x2 += 1), l.y === l.y2 && (l.y2 += 1);
  const c = Zs({ x: (0 - u[0]) / u[2], y: (0 - u[1]) / u[2], width: s / u[2], height: a / u[2] }),
    f = Math.max(0, Math.min(c.x2, l.x2) - Math.max(c.x, l.x)),
    d = Math.max(0, Math.min(c.y2, l.y2) - Math.max(c.y, l.y));
  return Math.ceil(f * d) > 0;
}
function kx(e) {
  var r, i, o, s, a;
  const t = ((r = e == null ? void 0 : e[ke]) == null ? void 0 : r.handleBounds) || null,
    n =
      t &&
      (e == null ? void 0 : e.width) &&
      (e == null ? void 0 : e.height) &&
      typeof ((i = e == null ? void 0 : e.positionAbsolute) == null ? void 0 : i.x) < "u" &&
      typeof ((o = e == null ? void 0 : e.positionAbsolute) == null ? void 0 : o.y) < "u";
  return [
    {
      x: ((s = e == null ? void 0 : e.positionAbsolute) == null ? void 0 : s.x) || 0,
      y: ((a = e == null ? void 0 : e.positionAbsolute) == null ? void 0 : a.y) || 0,
      width: (e == null ? void 0 : e.width) || 0,
      height: (e == null ? void 0 : e.height) || 0,
    },
    t,
    !!n,
  ];
}
const X$ = [{ level: 0, isMaxLevel: !0, edges: [] }];
function Z$(e, t, n = !1) {
  let r = -1;
  const i = e.reduce((s, a) => {
      var c, f;
      const u = Ft(a.zIndex);
      let l = u ? a.zIndex : 0;
      if (n) {
        const d = t.get(a.target),
          h = t.get(a.source),
          v = a.selected || (d == null ? void 0 : d.selected) || (h == null ? void 0 : h.selected),
          p = Math.max(
            ((c = h == null ? void 0 : h[ke]) == null ? void 0 : c.z) || 0,
            ((f = d == null ? void 0 : d[ke]) == null ? void 0 : f.z) || 0,
            1e3,
          );
        l = (u ? a.zIndex : 0) + (v ? p : 0);
      }
      return s[l] ? s[l].push(a) : (s[l] = [a]), (r = l > r ? l : r), s;
    }, {}),
    o = Object.entries(i).map(([s, a]) => {
      const u = +s;
      return { edges: a, level: u, isMaxLevel: u === r };
    });
  return o.length === 0 ? X$ : o;
}
function Q$(e, t, n) {
  const r = de(
    _.useCallback(
      (i) =>
        e
          ? i.edges.filter((o) => {
              const s = t.get(o.source),
                a = t.get(o.target);
              return (
                (s == null ? void 0 : s.width) &&
                (s == null ? void 0 : s.height) &&
                (a == null ? void 0 : a.width) &&
                (a == null ? void 0 : a.height) &&
                Y$({
                  sourcePos: s.positionAbsolute || { x: 0, y: 0 },
                  targetPos: a.positionAbsolute || { x: 0, y: 0 },
                  sourceWidth: s.width,
                  sourceHeight: s.height,
                  targetWidth: a.width,
                  targetHeight: a.height,
                  width: i.width,
                  height: i.height,
                  transform: i.transform,
                })
              );
            })
          : i.edges,
      [e, t],
    ),
  );
  return Z$(r, t, n);
}
const J$ = ({ color: e = "none", strokeWidth: t = 1 }) =>
    L.createElement("polyline", {
      style: { stroke: e, strokeWidth: t },
      strokeLinecap: "round",
      strokeLinejoin: "round",
      fill: "none",
      points: "-5,-4 0,0 -5,4",
    }),
  e4 = ({ color: e = "none", strokeWidth: t = 1 }) =>
    L.createElement("polyline", {
      style: { stroke: e, fill: e, strokeWidth: t },
      strokeLinecap: "round",
      strokeLinejoin: "round",
      points: "-5,-4 0,0 -5,4 -5,-4",
    }),
  Rx = { [go.Arrow]: J$, [go.ArrowClosed]: e4 };
function t4(e) {
  const t = Fe();
  return _.useMemo(() => {
    var i, o;
    return Object.prototype.hasOwnProperty.call(Rx, e)
      ? Rx[e]
      : ((o = (i = t.getState()).onError) == null || o.call(i, "009", Kn.error009(e)), null);
  }, [e]);
}
const n4 = ({
    id: e,
    type: t,
    color: n,
    width: r = 12.5,
    height: i = 12.5,
    markerUnits: o = "strokeWidth",
    strokeWidth: s,
    orient: a = "auto-start-reverse",
  }) => {
    const u = t4(t);
    return u
      ? L.createElement(
          "marker",
          {
            className: "react-flow__arrowhead",
            id: e,
            markerWidth: `${r}`,
            markerHeight: `${i}`,
            viewBox: "-10 -10 20 20",
            markerUnits: o,
            orient: a,
            refX: "0",
            refY: "0",
          },
          L.createElement(u, { color: n, strokeWidth: s }),
        )
      : null;
  },
  r4 =
    ({ defaultColor: e, rfId: t }) =>
    (n) => {
      const r = [];
      return n.edges
        .reduce(
          (i, o) => (
            [o.markerStart, o.markerEnd].forEach((s) => {
              if (s && typeof s == "object") {
                const a = Iv(s, t);
                r.includes(a) || (i.push({ id: a, color: s.color || e, ...s }), r.push(a));
              }
            }),
            i
          ),
          [],
        )
        .sort((i, o) => i.id.localeCompare(o.id));
    },
  ZA = ({ defaultColor: e, rfId: t }) => {
    const n = de(
      _.useCallback(r4({ defaultColor: e, rfId: t }), [e, t]),
      (r, i) => !(r.length !== i.length || r.some((o, s) => o.id !== i[s].id)),
    );
    return L.createElement(
      "defs",
      null,
      n.map((r) =>
        L.createElement(n4, {
          id: r.id,
          key: r.id,
          type: r.type,
          color: r.color,
          width: r.width,
          height: r.height,
          markerUnits: r.markerUnits,
          strokeWidth: r.strokeWidth,
          orient: r.orient,
        }),
      ),
    );
  };
ZA.displayName = "MarkerDefinitions";
var i4 = _.memo(ZA);
const o4 = (e) => ({
    nodesConnectable: e.nodesConnectable,
    edgesFocusable: e.edgesFocusable,
    edgesUpdatable: e.edgesUpdatable,
    elementsSelectable: e.elementsSelectable,
    width: e.width,
    height: e.height,
    connectionMode: e.connectionMode,
    nodeInternals: e.nodeInternals,
    onError: e.onError,
  }),
  QA = ({
    defaultMarkerColor: e,
    onlyRenderVisibleElements: t,
    elevateEdgesOnSelect: n,
    rfId: r,
    edgeTypes: i,
    noPanClassName: o,
    onEdgeContextMenu: s,
    onEdgeMouseEnter: a,
    onEdgeMouseMove: u,
    onEdgeMouseLeave: l,
    onEdgeClick: c,
    onEdgeDoubleClick: f,
    onReconnect: d,
    onReconnectStart: h,
    onReconnectEnd: v,
    reconnectRadius: p,
    children: y,
    disableKeyboardA11y: m,
  }) => {
    const {
        edgesFocusable: g,
        edgesUpdatable: w,
        elementsSelectable: x,
        width: b,
        height: E,
        connectionMode: C,
        nodeInternals: T,
        onError: P,
      } = de(o4, He),
      M = Q$(t, T, n);
    return b
      ? L.createElement(
          L.Fragment,
          null,
          M.map(({ level: I, edges: j, isMaxLevel: q }) =>
            L.createElement(
              "svg",
              {
                key: I,
                style: { zIndex: I },
                width: b,
                height: E,
                className: "react-flow__edges react-flow__container",
              },
              q && L.createElement(i4, { defaultColor: e, rfId: r }),
              L.createElement(
                "g",
                null,
                j.map((S) => {
                  const [O, A, F] = kx(T.get(S.source)),
                    [N, k, D] = kx(T.get(S.target));
                  if (!F || !D) return null;
                  let V = S.type || "default";
                  i[V] || (P == null || P("011", Kn.error011(V)), (V = "default"));
                  const $ = i[V] || i.default,
                    U = C === ci.Strict ? k.target : (k.target ?? []).concat(k.source ?? []),
                    B = Tx(A.source, S.sourceHandle),
                    W = Tx(U, S.targetHandle),
                    X = (B == null ? void 0 : B.position) || Y.Bottom,
                    ee = (W == null ? void 0 : W.position) || Y.Top,
                    ue = !!(S.focusable || (g && typeof S.focusable > "u")),
                    se = S.reconnectable || S.updatable,
                    oe = typeof d < "u" && (se || (w && typeof se > "u"));
                  if (!B || !W) return P == null || P("008", Kn.error008(B, S)), null;
                  const {
                    sourceX: De,
                    sourceY: Re,
                    targetX: Ge,
                    targetY: je,
                  } = K$(O, B, X, N, W, ee);
                  return L.createElement($, {
                    key: S.id,
                    id: S.id,
                    className: Ze([S.className, o]),
                    type: V,
                    data: S.data,
                    selected: !!S.selected,
                    animated: !!S.animated,
                    hidden: !!S.hidden,
                    label: S.label,
                    labelStyle: S.labelStyle,
                    labelShowBg: S.labelShowBg,
                    labelBgStyle: S.labelBgStyle,
                    labelBgPadding: S.labelBgPadding,
                    labelBgBorderRadius: S.labelBgBorderRadius,
                    style: S.style,
                    source: S.source,
                    target: S.target,
                    sourceHandleId: S.sourceHandle,
                    targetHandleId: S.targetHandle,
                    markerEnd: S.markerEnd,
                    markerStart: S.markerStart,
                    sourceX: De,
                    sourceY: Re,
                    targetX: Ge,
                    targetY: je,
                    sourcePosition: X,
                    targetPosition: ee,
                    elementsSelectable: x,
                    onContextMenu: s,
                    onMouseEnter: a,
                    onMouseMove: u,
                    onMouseLeave: l,
                    onClick: c,
                    onEdgeDoubleClick: f,
                    onReconnect: d,
                    onReconnectStart: h,
                    onReconnectEnd: v,
                    reconnectRadius: p,
                    rfId: r,
                    ariaLabel: S.ariaLabel,
                    isFocusable: ue,
                    isReconnectable: oe,
                    pathOptions: "pathOptions" in S ? S.pathOptions : void 0,
                    interactionWidth: S.interactionWidth,
                    disableKeyboardA11y: m,
                  });
                }),
              ),
            ),
          ),
          y,
        )
      : null;
  };
QA.displayName = "EdgeRenderer";
var s4 = _.memo(QA);
const a4 = (e) => `translate(${e.transform[0]}px,${e.transform[1]}px) scale(${e.transform[2]})`;
function u4({ children: e }) {
  const t = de(a4);
  return L.createElement(
    "div",
    { className: "react-flow__viewport react-flow__container", style: { transform: t } },
    e,
  );
}
function l4(e) {
  const t = Zl(),
    n = _.useRef(!1);
  _.useEffect(() => {
    !n.current && t.viewportInitialized && e && (setTimeout(() => e(t), 1), (n.current = !0));
  }, [e, t.viewportInitialized]);
}
const c4 = { [Y.Left]: Y.Right, [Y.Right]: Y.Left, [Y.Top]: Y.Bottom, [Y.Bottom]: Y.Top },
  JA = ({
    nodeId: e,
    handleType: t,
    style: n,
    type: r = In.Bezier,
    CustomComponent: i,
    connectionStatus: o,
  }) => {
    var E, C, T;
    const {
        fromNode: s,
        handleId: a,
        toX: u,
        toY: l,
        connectionMode: c,
      } = de(
        _.useCallback(
          (P) => ({
            fromNode: P.nodeInternals.get(e),
            handleId: P.connectionHandleId,
            toX: (P.connectionPosition.x - P.transform[0]) / P.transform[2],
            toY: (P.connectionPosition.y - P.transform[1]) / P.transform[2],
            connectionMode: P.connectionMode,
          }),
          [e],
        ),
        He,
      ),
      f = (E = s == null ? void 0 : s[ke]) == null ? void 0 : E.handleBounds;
    let d = f == null ? void 0 : f[t];
    if (
      (c === ci.Loose && (d = d || (f == null ? void 0 : f[t === "source" ? "target" : "source"])),
      !s || !d)
    )
      return null;
    const h = a ? d.find((P) => P.id === a) : d[0],
      v = h ? h.x + h.width / 2 : (s.width ?? 0) / 2,
      p = h ? h.y + h.height / 2 : (s.height ?? 0),
      y = (((C = s.positionAbsolute) == null ? void 0 : C.x) ?? 0) + v,
      m = (((T = s.positionAbsolute) == null ? void 0 : T.y) ?? 0) + p,
      g = h == null ? void 0 : h.position,
      w = g ? c4[g] : null;
    if (!g || !w) return null;
    if (i)
      return L.createElement(i, {
        connectionLineType: r,
        connectionLineStyle: n,
        fromNode: s,
        fromHandle: h,
        fromX: y,
        fromY: m,
        toX: u,
        toY: l,
        fromPosition: g,
        toPosition: w,
        connectionStatus: o,
      });
    let x = "";
    const b = {
      sourceX: y,
      sourceY: m,
      sourcePosition: g,
      targetX: u,
      targetY: l,
      targetPosition: w,
    };
    return (
      r === In.Bezier
        ? ([x] = bA(b))
        : r === In.Step
          ? ([x] = fl({ ...b, borderRadius: 0 }))
          : r === In.SmoothStep
            ? ([x] = fl(b))
            : r === In.SimpleBezier
              ? ([x] = _A(b))
              : (x = `M${y},${m} ${u},${l}`),
      L.createElement("path", {
        d: x,
        fill: "none",
        className: "react-flow__connection-path",
        style: n,
      })
    );
  };
JA.displayName = "ConnectionLine";
const f4 = (e) => ({
  nodeId: e.connectionNodeId,
  handleType: e.connectionHandleType,
  nodesConnectable: e.nodesConnectable,
  connectionStatus: e.connectionStatus,
  width: e.width,
  height: e.height,
});
function d4({ containerStyle: e, style: t, type: n, component: r }) {
  const {
    nodeId: i,
    handleType: o,
    nodesConnectable: s,
    width: a,
    height: u,
    connectionStatus: l,
  } = de(f4, He);
  return !(i && o && a && s)
    ? null
    : L.createElement(
        "svg",
        {
          style: e,
          width: a,
          height: u,
          className: "react-flow__edges react-flow__connectionline react-flow__container",
        },
        L.createElement(
          "g",
          { className: Ze(["react-flow__connection", l]) },
          L.createElement(JA, {
            nodeId: i,
            handleType: o,
            style: t,
            type: n,
            CustomComponent: r,
            connectionStatus: l,
          }),
        ),
      );
}
function Px(e, t) {
  return _.useRef(null), Fe(), _.useMemo(() => t(e), [e]);
}
const eN = ({
  nodeTypes: e,
  edgeTypes: t,
  onMove: n,
  onMoveStart: r,
  onMoveEnd: i,
  onInit: o,
  onNodeClick: s,
  onEdgeClick: a,
  onNodeDoubleClick: u,
  onEdgeDoubleClick: l,
  onNodeMouseEnter: c,
  onNodeMouseMove: f,
  onNodeMouseLeave: d,
  onNodeContextMenu: h,
  onSelectionContextMenu: v,
  onSelectionStart: p,
  onSelectionEnd: y,
  connectionLineType: m,
  connectionLineStyle: g,
  connectionLineComponent: w,
  connectionLineContainerStyle: x,
  selectionKeyCode: b,
  selectionOnDrag: E,
  selectionMode: C,
  multiSelectionKeyCode: T,
  panActivationKeyCode: P,
  zoomActivationKeyCode: M,
  deleteKeyCode: I,
  onlyRenderVisibleElements: j,
  elementsSelectable: q,
  selectNodesOnDrag: S,
  defaultViewport: O,
  translateExtent: A,
  minZoom: F,
  maxZoom: N,
  preventScrolling: k,
  defaultMarkerColor: D,
  zoomOnScroll: V,
  zoomOnPinch: $,
  panOnScroll: U,
  panOnScrollSpeed: B,
  panOnScrollMode: W,
  zoomOnDoubleClick: X,
  panOnDrag: ee,
  onPaneClick: ue,
  onPaneMouseEnter: se,
  onPaneMouseMove: oe,
  onPaneMouseLeave: De,
  onPaneScroll: Re,
  onPaneContextMenu: Ge,
  onEdgeContextMenu: je,
  onEdgeMouseEnter: Q,
  onEdgeMouseMove: Ve,
  onEdgeMouseLeave: K,
  onReconnect: G,
  onReconnectStart: Ee,
  onReconnectEnd: Ut,
  reconnectRadius: un,
  noDragClassName: it,
  noWheelClassName: Pe,
  noPanClassName: ft,
  elevateEdgesOnSelect: Ht,
  disableKeyboardA11y: Cn,
  nodeOrigin: ln,
  nodeExtent: xt,
  rfId: Tn,
}) => {
  const tr = Px(e, q$),
    qe = Px(t, W$);
  return (
    l4(o),
    L.createElement(
      j$,
      {
        onPaneClick: ue,
        onPaneMouseEnter: se,
        onPaneMouseMove: oe,
        onPaneMouseLeave: De,
        onPaneContextMenu: Ge,
        onPaneScroll: Re,
        deleteKeyCode: I,
        selectionKeyCode: b,
        selectionOnDrag: E,
        selectionMode: C,
        onSelectionStart: p,
        onSelectionEnd: y,
        multiSelectionKeyCode: T,
        panActivationKeyCode: P,
        zoomActivationKeyCode: M,
        elementsSelectable: q,
        onMove: n,
        onMoveStart: r,
        onMoveEnd: i,
        zoomOnScroll: V,
        zoomOnPinch: $,
        zoomOnDoubleClick: X,
        panOnScroll: U,
        panOnScrollSpeed: B,
        panOnScrollMode: W,
        panOnDrag: ee,
        defaultViewport: O,
        translateExtent: A,
        minZoom: F,
        maxZoom: N,
        onSelectionContextMenu: v,
        preventScrolling: k,
        noDragClassName: it,
        noWheelClassName: Pe,
        noPanClassName: ft,
        disableKeyboardA11y: Cn,
      },
      L.createElement(
        u4,
        null,
        L.createElement(
          s4,
          {
            edgeTypes: qe,
            onEdgeClick: a,
            onEdgeDoubleClick: l,
            onlyRenderVisibleElements: j,
            onEdgeContextMenu: je,
            onEdgeMouseEnter: Q,
            onEdgeMouseMove: Ve,
            onEdgeMouseLeave: K,
            onReconnect: G,
            onReconnectStart: Ee,
            onReconnectEnd: Ut,
            reconnectRadius: un,
            defaultMarkerColor: D,
            noPanClassName: ft,
            elevateEdgesOnSelect: !!Ht,
            disableKeyboardA11y: Cn,
            rfId: Tn,
          },
          L.createElement(d4, { style: g, type: m, component: w, containerStyle: x }),
        ),
        L.createElement("div", { className: "react-flow__edgelabel-renderer" }),
        L.createElement(B$, {
          nodeTypes: tr,
          onNodeClick: s,
          onNodeDoubleClick: u,
          onNodeMouseEnter: c,
          onNodeMouseMove: f,
          onNodeMouseLeave: d,
          onNodeContextMenu: h,
          selectNodesOnDrag: S,
          onlyRenderVisibleElements: j,
          noPanClassName: ft,
          noDragClassName: it,
          disableKeyboardA11y: Cn,
          nodeOrigin: ln,
          nodeExtent: xt,
          rfId: Tn,
        }),
      ),
    )
  );
};
eN.displayName = "GraphView";
var h4 = _.memo(eN);
const Fv = [
    [Number.NEGATIVE_INFINITY, Number.NEGATIVE_INFINITY],
    [Number.POSITIVE_INFINITY, Number.POSITIVE_INFINITY],
  ],
  rr = {
    rfId: "1",
    width: 0,
    height: 0,
    transform: [0, 0, 1],
    nodeInternals: new Map(),
    edges: [],
    onNodesChange: null,
    onEdgesChange: null,
    hasDefaultNodes: !1,
    hasDefaultEdges: !1,
    d3Zoom: null,
    d3Selection: null,
    d3ZoomHandler: void 0,
    minZoom: 0.5,
    maxZoom: 2,
    translateExtent: Fv,
    nodeExtent: Fv,
    nodesSelectionActive: !1,
    userSelectionActive: !1,
    userSelectionRect: null,
    connectionNodeId: null,
    connectionHandleId: null,
    connectionHandleType: "source",
    connectionPosition: { x: 0, y: 0 },
    connectionStatus: null,
    connectionMode: ci.Strict,
    domNode: null,
    paneDragging: !1,
    noPanClassName: "nopan",
    nodeOrigin: [0, 0],
    nodeDragThreshold: 0,
    snapGrid: [15, 15],
    snapToGrid: !1,
    nodesDraggable: !0,
    nodesConnectable: !0,
    nodesFocusable: !0,
    edgesFocusable: !0,
    edgesUpdatable: !0,
    elementsSelectable: !0,
    elevateNodesOnSelect: !0,
    fitViewOnInit: !1,
    fitViewOnInitDone: !1,
    fitViewOnInitOptions: void 0,
    onSelectionChange: [],
    multiSelectionActive: !1,
    connectionStartHandle: null,
    connectionEndHandle: null,
    connectionClickStartHandle: null,
    connectOnClick: !0,
    ariaLiveMessage: "",
    autoPanOnConnect: !0,
    autoPanOnNodeDrag: !0,
    connectionRadius: 20,
    onError: $q,
    isValidConnection: void 0,
  },
  p4 = () =>
    n3(
      (e, t) => ({
        ...rr,
        setNodes: (n) => {
          const { nodeInternals: r, nodeOrigin: i, elevateNodesOnSelect: o } = t();
          e({ nodeInternals: cf(n, r, i, o) });
        },
        getNodes: () => Array.from(t().nodeInternals.values()),
        setEdges: (n) => {
          const { defaultEdgeOptions: r = {} } = t();
          e({ edges: n.map((i) => ({ ...r, ...i })) });
        },
        setDefaultNodesAndEdges: (n, r) => {
          const i = typeof n < "u",
            o = typeof r < "u",
            s = i ? cf(n, new Map(), t().nodeOrigin, t().elevateNodesOnSelect) : new Map();
          e({ nodeInternals: s, edges: o ? r : [], hasDefaultNodes: i, hasDefaultEdges: o });
        },
        updateNodeDimensions: (n) => {
          const {
              onNodesChange: r,
              nodeInternals: i,
              fitViewOnInit: o,
              fitViewOnInitDone: s,
              fitViewOnInitOptions: a,
              domNode: u,
              nodeOrigin: l,
            } = t(),
            c = u == null ? void 0 : u.querySelector(".react-flow__viewport");
          if (!c) return;
          const f = window.getComputedStyle(c),
            { m22: d } = new window.DOMMatrixReadOnly(f.transform),
            h = n.reduce((p, y) => {
              const m = i.get(y.id);
              if (m != null && m.hidden)
                i.set(m.id, { ...m, [ke]: { ...m[ke], handleBounds: void 0 } });
              else if (m) {
                const g = l0(y.nodeElement);
                !!(
                  g.width &&
                  g.height &&
                  (m.width !== g.width || m.height !== g.height || y.forceUpdate)
                ) &&
                  (i.set(m.id, {
                    ...m,
                    [ke]: {
                      ...m[ke],
                      handleBounds: {
                        source: bx(".source", y.nodeElement, d, l),
                        target: bx(".target", y.nodeElement, d, l),
                      },
                    },
                    ...g,
                  }),
                  p.push({ id: m.id, type: "dimensions", dimensions: g }));
              }
              return p;
            }, []);
          qA(i, l);
          const v = s || (o && !s && $A(t, { initial: !0, ...a }));
          e({ nodeInternals: new Map(i), fitViewOnInitDone: v }),
            (h == null ? void 0 : h.length) > 0 && (r == null || r(h));
        },
        updateNodePositions: (n, r = !0, i = !1) => {
          const { triggerNodeChanges: o } = t(),
            s = n.map((a) => {
              const u = { id: a.id, type: "position", dragging: i };
              return r && ((u.positionAbsolute = a.positionAbsolute), (u.position = a.position)), u;
            });
          o(s);
        },
        triggerNodeChanges: (n) => {
          const {
            onNodesChange: r,
            nodeInternals: i,
            hasDefaultNodes: o,
            nodeOrigin: s,
            getNodes: a,
            elevateNodesOnSelect: u,
          } = t();
          if (n != null && n.length) {
            if (o) {
              const l = BA(n, a()),
                c = cf(l, i, s, u);
              e({ nodeInternals: c });
            }
            r == null || r(n);
          }
        },
        addSelectedNodes: (n) => {
          const { multiSelectionActive: r, edges: i, getNodes: o } = t();
          let s,
            a = null;
          r ? (s = n.map((u) => dr(u, !0))) : ((s = qi(o(), n)), (a = qi(i, []))),
            Qa({ changedNodes: s, changedEdges: a, get: t, set: e });
        },
        addSelectedEdges: (n) => {
          const { multiSelectionActive: r, edges: i, getNodes: o } = t();
          let s,
            a = null;
          r ? (s = n.map((u) => dr(u, !0))) : ((s = qi(i, n)), (a = qi(o(), []))),
            Qa({ changedNodes: a, changedEdges: s, get: t, set: e });
        },
        unselectNodesAndEdges: ({ nodes: n, edges: r } = {}) => {
          const { edges: i, getNodes: o } = t(),
            s = n || o(),
            a = r || i,
            u = s.map((c) => ((c.selected = !1), dr(c.id, !1))),
            l = a.map((c) => dr(c.id, !1));
          Qa({ changedNodes: u, changedEdges: l, get: t, set: e });
        },
        setMinZoom: (n) => {
          const { d3Zoom: r, maxZoom: i } = t();
          r == null || r.scaleExtent([n, i]), e({ minZoom: n });
        },
        setMaxZoom: (n) => {
          const { d3Zoom: r, minZoom: i } = t();
          r == null || r.scaleExtent([i, n]), e({ maxZoom: n });
        },
        setTranslateExtent: (n) => {
          var r;
          (r = t().d3Zoom) == null || r.translateExtent(n), e({ translateExtent: n });
        },
        resetSelectedElements: () => {
          const { edges: n, getNodes: r } = t(),
            o = r()
              .filter((a) => a.selected)
              .map((a) => dr(a.id, !1)),
            s = n.filter((a) => a.selected).map((a) => dr(a.id, !1));
          Qa({ changedNodes: o, changedEdges: s, get: t, set: e });
        },
        setNodeExtent: (n) => {
          const { nodeInternals: r } = t();
          r.forEach((i) => {
            i.positionAbsolute = c0(i.position, n);
          }),
            e({ nodeExtent: n, nodeInternals: new Map(r) });
        },
        panBy: (n) => {
          const {
            transform: r,
            width: i,
            height: o,
            d3Zoom: s,
            d3Selection: a,
            translateExtent: u,
          } = t();
          if (!s || !a || (!n.x && !n.y)) return !1;
          const l = qn.translate(r[0] + n.x, r[1] + n.y).scale(r[2]),
            c = [
              [0, 0],
              [i, o],
            ],
            f = s == null ? void 0 : s.constrain()(l, c, u);
          return s.transform(a, f), r[0] !== f.x || r[1] !== f.y || r[2] !== f.k;
        },
        cancelConnection: () =>
          e({
            connectionNodeId: rr.connectionNodeId,
            connectionHandleId: rr.connectionHandleId,
            connectionHandleType: rr.connectionHandleType,
            connectionStatus: rr.connectionStatus,
            connectionStartHandle: rr.connectionStartHandle,
            connectionEndHandle: rr.connectionEndHandle,
          }),
        reset: () => e({ ...rr }),
      }),
      Object.is,
    ),
  y0 = ({ children: e }) => {
    const t = _.useRef(null);
    return t.current || (t.current = p4()), L.createElement(Dq, { value: t.current }, e);
  };
y0.displayName = "ReactFlowProvider";
const tN = ({ children: e }) =>
  _.useContext(Kl) ? L.createElement(L.Fragment, null, e) : L.createElement(y0, null, e);
tN.displayName = "ReactFlowWrapper";
const m4 = { input: IA, default: Ov, output: OA, group: g0 },
  g4 = { default: dl, straight: h0, step: d0, smoothstep: Yl, simplebezier: f0 },
  v4 = [0, 0],
  y4 = [15, 15],
  w4 = { x: 0, y: 0, zoom: 1 },
  x4 = { width: "100%", height: "100%", overflow: "hidden", position: "relative", zIndex: 0 },
  nN = _.forwardRef(
    (
      {
        nodes: e,
        edges: t,
        defaultNodes: n,
        defaultEdges: r,
        className: i,
        nodeTypes: o = m4,
        edgeTypes: s = g4,
        onNodeClick: a,
        onEdgeClick: u,
        onInit: l,
        onMove: c,
        onMoveStart: f,
        onMoveEnd: d,
        onConnect: h,
        onConnectStart: v,
        onConnectEnd: p,
        onClickConnectStart: y,
        onClickConnectEnd: m,
        onNodeMouseEnter: g,
        onNodeMouseMove: w,
        onNodeMouseLeave: x,
        onNodeContextMenu: b,
        onNodeDoubleClick: E,
        onNodeDragStart: C,
        onNodeDrag: T,
        onNodeDragStop: P,
        onNodesDelete: M,
        onEdgesDelete: I,
        onSelectionChange: j,
        onSelectionDragStart: q,
        onSelectionDrag: S,
        onSelectionDragStop: O,
        onSelectionContextMenu: A,
        onSelectionStart: F,
        onSelectionEnd: N,
        connectionMode: k = ci.Strict,
        connectionLineType: D = In.Bezier,
        connectionLineStyle: V,
        connectionLineComponent: $,
        connectionLineContainerStyle: U,
        deleteKeyCode: B = "Backspace",
        selectionKeyCode: W = "Shift",
        selectionOnDrag: X = !1,
        selectionMode: ee = mo.Full,
        panActivationKeyCode: ue = "Space",
        multiSelectionKeyCode: se = cl() ? "Meta" : "Control",
        zoomActivationKeyCode: oe = cl() ? "Meta" : "Control",
        snapToGrid: De = !1,
        snapGrid: Re = y4,
        onlyRenderVisibleElements: Ge = !1,
        selectNodesOnDrag: je = !0,
        nodesDraggable: Q,
        nodesConnectable: Ve,
        nodesFocusable: K,
        nodeOrigin: G = v4,
        edgesFocusable: Ee,
        edgesUpdatable: Ut,
        elementsSelectable: un,
        defaultViewport: it = w4,
        minZoom: Pe = 0.5,
        maxZoom: ft = 2,
        translateExtent: Ht = Fv,
        preventScrolling: Cn = !0,
        nodeExtent: ln,
        defaultMarkerColor: xt = "#b1b1b7",
        zoomOnScroll: Tn = !0,
        zoomOnPinch: tr = !0,
        panOnScroll: qe = !1,
        panOnScrollSpeed: dt = 0.5,
        panOnScrollMode: Qe = Xr.Free,
        zoomOnDoubleClick: ot = !0,
        panOnDrag: jr = !0,
        onPaneClick: kn,
        onPaneMouseEnter: cn,
        onPaneMouseMove: Do,
        onPaneMouseLeave: Rc,
        onPaneScroll: Oo,
        onPaneContextMenu: Pc,
        children: Tw,
        onEdgeContextMenu: Vr,
        onEdgeDoubleClick: _D,
        onEdgeMouseEnter: bD,
        onEdgeMouseMove: SD,
        onEdgeMouseLeave: ED,
        onEdgeUpdate: CD,
        onEdgeUpdateStart: TD,
        onEdgeUpdateEnd: kD,
        onReconnect: RD,
        onReconnectStart: PD,
        onReconnectEnd: AD,
        reconnectRadius: ND = 10,
        edgeUpdaterRadius: MD = 10,
        onNodesChange: ID,
        onEdgesChange: DD,
        noDragClassName: OD = "nodrag",
        noWheelClassName: LD = "nowheel",
        noPanClassName: kw = "nopan",
        fitView: FD = !1,
        fitViewOptions: jD,
        connectOnClick: VD = !0,
        attributionPosition: qD,
        proOptions: $D,
        defaultEdgeOptions: zD,
        elevateNodesOnSelect: BD = !0,
        elevateEdgesOnSelect: UD = !1,
        disableKeyboardA11y: Rw = !1,
        autoPanOnConnect: HD = !0,
        autoPanOnNodeDrag: GD = !0,
        connectionRadius: WD = 20,
        isValidConnection: KD,
        onError: YD,
        style: XD,
        id: Pw,
        nodeDragThreshold: ZD,
        ...QD
      },
      JD,
    ) => {
      const Ac = Pw || "1";
      return L.createElement(
        "div",
        {
          ...QD,
          style: { ...XD, ...x4 },
          ref: JD,
          className: Ze(["react-flow", i]),
          "data-testid": "rf__wrapper",
          id: Pw,
        },
        L.createElement(
          tN,
          null,
          L.createElement(h4, {
            onInit: l,
            onMove: c,
            onMoveStart: f,
            onMoveEnd: d,
            onNodeClick: a,
            onEdgeClick: u,
            onNodeMouseEnter: g,
            onNodeMouseMove: w,
            onNodeMouseLeave: x,
            onNodeContextMenu: b,
            onNodeDoubleClick: E,
            nodeTypes: o,
            edgeTypes: s,
            connectionLineType: D,
            connectionLineStyle: V,
            connectionLineComponent: $,
            connectionLineContainerStyle: U,
            selectionKeyCode: W,
            selectionOnDrag: X,
            selectionMode: ee,
            deleteKeyCode: B,
            multiSelectionKeyCode: se,
            panActivationKeyCode: ue,
            zoomActivationKeyCode: oe,
            onlyRenderVisibleElements: Ge,
            selectNodesOnDrag: je,
            defaultViewport: it,
            translateExtent: Ht,
            minZoom: Pe,
            maxZoom: ft,
            preventScrolling: Cn,
            zoomOnScroll: Tn,
            zoomOnPinch: tr,
            zoomOnDoubleClick: ot,
            panOnScroll: qe,
            panOnScrollSpeed: dt,
            panOnScrollMode: Qe,
            panOnDrag: jr,
            onPaneClick: kn,
            onPaneMouseEnter: cn,
            onPaneMouseMove: Do,
            onPaneMouseLeave: Rc,
            onPaneScroll: Oo,
            onPaneContextMenu: Pc,
            onSelectionContextMenu: A,
            onSelectionStart: F,
            onSelectionEnd: N,
            onEdgeContextMenu: Vr,
            onEdgeDoubleClick: _D,
            onEdgeMouseEnter: bD,
            onEdgeMouseMove: SD,
            onEdgeMouseLeave: ED,
            onReconnect: RD ?? CD,
            onReconnectStart: PD ?? TD,
            onReconnectEnd: AD ?? kD,
            reconnectRadius: ND ?? MD,
            defaultMarkerColor: xt,
            noDragClassName: OD,
            noWheelClassName: LD,
            noPanClassName: kw,
            elevateEdgesOnSelect: UD,
            rfId: Ac,
            disableKeyboardA11y: Rw,
            nodeOrigin: G,
            nodeExtent: ln,
          }),
          L.createElement(c$, {
            nodes: e,
            edges: t,
            defaultNodes: n,
            defaultEdges: r,
            onConnect: h,
            onConnectStart: v,
            onConnectEnd: p,
            onClickConnectStart: y,
            onClickConnectEnd: m,
            nodesDraggable: Q,
            nodesConnectable: Ve,
            nodesFocusable: K,
            edgesFocusable: Ee,
            edgesUpdatable: Ut,
            elementsSelectable: un,
            elevateNodesOnSelect: BD,
            minZoom: Pe,
            maxZoom: ft,
            nodeExtent: ln,
            onNodesChange: ID,
            onEdgesChange: DD,
            snapToGrid: De,
            snapGrid: Re,
            connectionMode: k,
            translateExtent: Ht,
            connectOnClick: VD,
            defaultEdgeOptions: zD,
            fitView: FD,
            fitViewOptions: jD,
            onNodesDelete: M,
            onEdgesDelete: I,
            onNodeDragStart: C,
            onNodeDrag: T,
            onNodeDragStop: P,
            onSelectionDrag: S,
            onSelectionDragStart: q,
            onSelectionDragStop: O,
            noPanClassName: kw,
            nodeOrigin: G,
            rfId: Ac,
            autoPanOnConnect: HD,
            autoPanOnNodeDrag: GD,
            onError: YD,
            connectionRadius: WD,
            isValidConnection: KD,
            nodeDragThreshold: ZD,
          }),
          L.createElement(u$, { onSelectionChange: j }),
          Tw,
          L.createElement(Lq, { proOptions: $D, position: qD }),
          L.createElement(m$, { rfId: Ac, disableKeyboardA11y: Rw }),
        ),
      );
    },
  );
nN.displayName = "ReactFlow";
const _4 = (e) => {
  var t;
  return (t = e.domNode) == null ? void 0 : t.querySelector(".react-flow__edgelabel-renderer");
};
function b4({ children: e }) {
  const t = de(_4);
  return t ? $l.createPortal(e, t) : null;
}
const rN = ({
  id: e,
  x: t,
  y: n,
  width: r,
  height: i,
  style: o,
  color: s,
  strokeColor: a,
  strokeWidth: u,
  className: l,
  borderRadius: c,
  shapeRendering: f,
  onClick: d,
  selected: h,
}) => {
  const { background: v, backgroundColor: p } = o || {},
    y = s || v || p;
  return L.createElement("rect", {
    className: Ze(["react-flow__minimap-node", { selected: h }, l]),
    x: t,
    y: n,
    rx: c,
    ry: c,
    width: r,
    height: i,
    fill: y,
    stroke: a,
    strokeWidth: u,
    shapeRendering: f,
    onClick: d ? (m) => d(m, e) : void 0,
  });
};
rN.displayName = "MiniMapNode";
var S4 = _.memo(rN);
const E4 = (e) => e.nodeOrigin,
  C4 = (e) => e.getNodes().filter((t) => !t.hidden && t.width && t.height),
  pf = (e) => (e instanceof Function ? e : () => e);
function T4({
  nodeStrokeColor: e = "transparent",
  nodeColor: t = "#e2e2e2",
  nodeClassName: n = "",
  nodeBorderRadius: r = 5,
  nodeStrokeWidth: i = 2,
  nodeComponent: o = S4,
  onClick: s,
}) {
  const a = de(C4, He),
    u = de(E4),
    l = pf(t),
    c = pf(e),
    f = pf(n),
    d = typeof window > "u" || window.chrome ? "crispEdges" : "geometricPrecision";
  return L.createElement(
    L.Fragment,
    null,
    a.map((h) => {
      const { x: v, y: p } = ni(h, u).positionAbsolute;
      return L.createElement(o, {
        key: h.id,
        x: v,
        y: p,
        width: h.width,
        height: h.height,
        style: h.style,
        selected: h.selected,
        className: f(h),
        color: l(h),
        borderRadius: r,
        strokeColor: c(h),
        strokeWidth: i,
        shapeRendering: d,
        onClick: s,
        id: h.id,
      });
    }),
  );
}
var k4 = _.memo(T4);
const R4 = 200,
  P4 = 150,
  A4 = (e) => {
    const t = e.getNodes(),
      n = {
        x: -e.transform[0] / e.transform[2],
        y: -e.transform[1] / e.transform[2],
        width: e.width / e.transform[2],
        height: e.height / e.transform[2],
      };
    return { viewBB: n, boundingRect: t.length > 0 ? Vq(Xl(t, e.nodeOrigin), n) : n, rfId: e.rfId };
  },
  N4 = "react-flow__minimap-desc";
function iN({
  style: e,
  className: t,
  nodeStrokeColor: n = "transparent",
  nodeColor: r = "#e2e2e2",
  nodeClassName: i = "",
  nodeBorderRadius: o = 5,
  nodeStrokeWidth: s = 2,
  nodeComponent: a,
  maskColor: u = "rgb(240, 240, 240, 0.6)",
  maskStrokeColor: l = "none",
  maskStrokeWidth: c = 1,
  position: f = "bottom-right",
  onClick: d,
  onNodeClick: h,
  pannable: v = !1,
  zoomable: p = !1,
  ariaLabel: y = "React Flow mini map",
  inversePan: m = !1,
  zoomStep: g = 10,
  offsetScale: w = 5,
}) {
  const x = Fe(),
    b = _.useRef(null),
    { boundingRect: E, viewBB: C, rfId: T } = de(A4, He),
    P = (e == null ? void 0 : e.width) ?? R4,
    M = (e == null ? void 0 : e.height) ?? P4,
    I = E.width / P,
    j = E.height / M,
    q = Math.max(I, j),
    S = q * P,
    O = q * M,
    A = w * q,
    F = E.x - (S - E.width) / 2 - A,
    N = E.y - (O - E.height) / 2 - A,
    k = S + A * 2,
    D = O + A * 2,
    V = `${N4}-${T}`,
    $ = _.useRef(0);
  ($.current = q),
    _.useEffect(() => {
      if (b.current) {
        const W = Ot(b.current),
          X = (se) => {
            const { transform: oe, d3Selection: De, d3Zoom: Re } = x.getState();
            if (se.sourceEvent.type !== "wheel" || !De || !Re) return;
            const Ge =
                -se.sourceEvent.deltaY *
                (se.sourceEvent.deltaMode === 1 ? 0.05 : se.sourceEvent.deltaMode ? 1 : 0.002) *
                g,
              je = oe[2] * Math.pow(2, Ge);
            Re.scaleTo(De, je);
          },
          ee = (se) => {
            const {
              transform: oe,
              d3Selection: De,
              d3Zoom: Re,
              translateExtent: Ge,
              width: je,
              height: Q,
            } = x.getState();
            if (se.sourceEvent.type !== "mousemove" || !De || !Re) return;
            const Ve = $.current * Math.max(1, oe[2]) * (m ? -1 : 1),
              K = {
                x: oe[0] - se.sourceEvent.movementX * Ve,
                y: oe[1] - se.sourceEvent.movementY * Ve,
              },
              G = [
                [0, 0],
                [je, Q],
              ],
              Ee = qn.translate(K.x, K.y).scale(oe[2]),
              Ut = Re.constrain()(Ee, G, Ge);
            Re.transform(De, Ut);
          },
          ue = fA()
            .on("zoom", v ? ee : null)
            .on("zoom.wheel", p ? X : null);
        return (
          W.call(ue),
          () => {
            W.on("zoom", null);
          }
        );
      }
    }, [v, p, m, g]);
  const U = d
      ? (W) => {
          const X = Xt(W);
          d(W, { x: X[0], y: X[1] });
        }
      : void 0,
    B = h
      ? (W, X) => {
          const ee = x.getState().nodeInternals.get(X);
          h(W, ee);
        }
      : void 0;
  return L.createElement(
    u0,
    {
      position: f,
      style: e,
      className: Ze(["react-flow__minimap", t]),
      "data-testid": "rf__minimap",
    },
    L.createElement(
      "svg",
      {
        width: P,
        height: M,
        viewBox: `${F} ${N} ${k} ${D}`,
        role: "img",
        "aria-labelledby": V,
        ref: b,
        onClick: U,
      },
      y && L.createElement("title", { id: V }, y),
      L.createElement(k4, {
        onClick: B,
        nodeColor: r,
        nodeStrokeColor: n,
        nodeBorderRadius: o,
        nodeClassName: i,
        nodeStrokeWidth: s,
        nodeComponent: a,
      }),
      L.createElement("path", {
        className: "react-flow__minimap-mask",
        d: `M${F - A},${N - A}h${k + A * 2}v${D + A * 2}h${-k - A * 2}z
        M${C.x},${C.y}h${C.width}v${C.height}h${-C.width}z`,
        fill: u,
        fillRule: "evenodd",
        stroke: l,
        strokeWidth: c,
        pointerEvents: "none",
      }),
    ),
  );
}
iN.displayName = "MiniMap";
var M4 = _.memo(iN);
function I4() {
  return L.createElement(
    "svg",
    { xmlns: "http://www.w3.org/2000/svg", viewBox: "0 0 32 32" },
    L.createElement("path", {
      d: "M32 18.133H18.133V32h-4.266V18.133H0v-4.266h13.867V0h4.266v13.867H32z",
    }),
  );
}
function D4() {
  return L.createElement(
    "svg",
    { xmlns: "http://www.w3.org/2000/svg", viewBox: "0 0 32 5" },
    L.createElement("path", { d: "M0 0h32v4.2H0z" }),
  );
}
function O4() {
  return L.createElement(
    "svg",
    { xmlns: "http://www.w3.org/2000/svg", viewBox: "0 0 32 30" },
    L.createElement("path", {
      d: "M3.692 4.63c0-.53.4-.938.939-.938h5.215V0H4.708C2.13 0 0 2.054 0 4.63v5.216h3.692V4.631zM27.354 0h-5.2v3.692h5.17c.53 0 .984.4.984.939v5.215H32V4.631A4.624 4.624 0 0027.354 0zm.954 24.83c0 .532-.4.94-.939.94h-5.215v3.768h5.215c2.577 0 4.631-2.13 4.631-4.707v-5.139h-3.692v5.139zm-23.677.94c-.531 0-.939-.4-.939-.94v-5.138H0v5.139c0 2.577 2.13 4.707 4.708 4.707h5.138V25.77H4.631z",
    }),
  );
}
function L4() {
  return L.createElement(
    "svg",
    { xmlns: "http://www.w3.org/2000/svg", viewBox: "0 0 25 32" },
    L.createElement("path", {
      d: "M21.333 10.667H19.81V7.619C19.81 3.429 16.38 0 12.19 0 8 0 4.571 3.429 4.571 7.619v3.048H3.048A3.056 3.056 0 000 13.714v15.238A3.056 3.056 0 003.048 32h18.285a3.056 3.056 0 003.048-3.048V13.714a3.056 3.056 0 00-3.048-3.047zM12.19 24.533a3.056 3.056 0 01-3.047-3.047 3.056 3.056 0 013.047-3.048 3.056 3.056 0 013.048 3.048 3.056 3.056 0 01-3.048 3.047zm4.724-13.866H7.467V7.619c0-2.59 2.133-4.724 4.723-4.724 2.591 0 4.724 2.133 4.724 4.724v3.048z",
    }),
  );
}
function F4() {
  return L.createElement(
    "svg",
    { xmlns: "http://www.w3.org/2000/svg", viewBox: "0 0 25 32" },
    L.createElement("path", {
      d: "M21.333 10.667H19.81V7.619C19.81 3.429 16.38 0 12.19 0c-4.114 1.828-1.37 2.133.305 2.438 1.676.305 4.42 2.59 4.42 5.181v3.048H3.047A3.056 3.056 0 000 13.714v15.238A3.056 3.056 0 003.048 32h18.285a3.056 3.056 0 003.048-3.048V13.714a3.056 3.056 0 00-3.048-3.047zM12.19 24.533a3.056 3.056 0 01-3.047-3.047 3.056 3.056 0 013.047-3.048 3.056 3.056 0 013.048 3.048 3.056 3.056 0 01-3.048 3.047z",
    }),
  );
}
const is = ({ children: e, className: t, ...n }) =>
  L.createElement(
    "button",
    { type: "button", className: Ze(["react-flow__controls-button", t]), ...n },
    e,
  );
is.displayName = "ControlButton";
const j4 = (e) => ({
    isInteractive: e.nodesDraggable || e.nodesConnectable || e.elementsSelectable,
    minZoomReached: e.transform[2] <= e.minZoom,
    maxZoomReached: e.transform[2] >= e.maxZoom,
  }),
  oN = ({
    style: e,
    showZoom: t = !0,
    showFitView: n = !0,
    showInteractive: r = !0,
    fitViewOptions: i,
    onZoomIn: o,
    onZoomOut: s,
    onFitView: a,
    onInteractiveChange: u,
    className: l,
    children: c,
    position: f = "bottom-left",
  }) => {
    const d = Fe(),
      [h, v] = _.useState(!1),
      { isInteractive: p, minZoomReached: y, maxZoomReached: m } = de(j4, He),
      { zoomIn: g, zoomOut: w, fitView: x } = Zl();
    if (
      (_.useEffect(() => {
        v(!0);
      }, []),
      !h)
    )
      return null;
    const b = () => {
        g(), o == null || o();
      },
      E = () => {
        w(), s == null || s();
      },
      C = () => {
        x(i), a == null || a();
      },
      T = () => {
        d.setState({ nodesDraggable: !p, nodesConnectable: !p, elementsSelectable: !p }),
          u == null || u(!p);
      };
    return L.createElement(
      u0,
      {
        className: Ze(["react-flow__controls", l]),
        position: f,
        style: e,
        "data-testid": "rf__controls",
      },
      t &&
        L.createElement(
          L.Fragment,
          null,
          L.createElement(
            is,
            {
              onClick: b,
              className: "react-flow__controls-zoomin",
              title: "zoom in",
              "aria-label": "zoom in",
              disabled: m,
            },
            L.createElement(I4, null),
          ),
          L.createElement(
            is,
            {
              onClick: E,
              className: "react-flow__controls-zoomout",
              title: "zoom out",
              "aria-label": "zoom out",
              disabled: y,
            },
            L.createElement(D4, null),
          ),
        ),
      n &&
        L.createElement(
          is,
          {
            className: "react-flow__controls-fitview",
            onClick: C,
            title: "fit view",
            "aria-label": "fit view",
          },
          L.createElement(O4, null),
        ),
      r &&
        L.createElement(
          is,
          {
            className: "react-flow__controls-interactive",
            onClick: T,
            title: "toggle interactivity",
            "aria-label": "toggle interactivity",
          },
          p ? L.createElement(F4, null) : L.createElement(L4, null),
        ),
      c,
    );
  };
oN.displayName = "Controls";
var V4 = _.memo(oN),
  tn;
(function (e) {
  (e.Lines = "lines"), (e.Dots = "dots"), (e.Cross = "cross");
})(tn || (tn = {}));
function q4({ color: e, dimensions: t, lineWidth: n }) {
  return L.createElement("path", {
    stroke: e,
    strokeWidth: n,
    d: `M${t[0] / 2} 0 V${t[1]} M0 ${t[1] / 2} H${t[0]}`,
  });
}
function $4({ color: e, radius: t }) {
  return L.createElement("circle", { cx: t, cy: t, r: t, fill: e });
}
const z4 = { [tn.Dots]: "#91919a", [tn.Lines]: "#eee", [tn.Cross]: "#e2e2e2" },
  B4 = { [tn.Dots]: 1, [tn.Lines]: 1, [tn.Cross]: 6 },
  U4 = (e) => ({ transform: e.transform, patternId: `pattern-${e.rfId}` });
function sN({
  id: e,
  variant: t = tn.Dots,
  gap: n = 20,
  size: r,
  lineWidth: i = 1,
  offset: o = 2,
  color: s,
  style: a,
  className: u,
}) {
  const l = _.useRef(null),
    { transform: c, patternId: f } = de(U4, He),
    d = s || z4[t],
    h = r || B4[t],
    v = t === tn.Dots,
    p = t === tn.Cross,
    y = Array.isArray(n) ? n : [n, n],
    m = [y[0] * c[2] || 1, y[1] * c[2] || 1],
    g = h * c[2],
    w = p ? [g, g] : m,
    x = v ? [g / o, g / o] : [w[0] / o, w[1] / o];
  return L.createElement(
    "svg",
    {
      className: Ze(["react-flow__background", u]),
      style: { ...a, position: "absolute", width: "100%", height: "100%", top: 0, left: 0 },
      ref: l,
      "data-testid": "rf__background",
    },
    L.createElement(
      "pattern",
      {
        id: f + e,
        x: c[0] % m[0],
        y: c[1] % m[1],
        width: m[0],
        height: m[1],
        patternUnits: "userSpaceOnUse",
        patternTransform: `translate(-${x[0]},-${x[1]})`,
      },
      v
        ? L.createElement($4, { color: d, radius: g / o })
        : L.createElement(q4, { dimensions: w, color: d, lineWidth: i }),
    ),
    L.createElement("rect", {
      x: "0",
      y: "0",
      width: "100%",
      height: "100%",
      fill: `url(#${f + e})`,
    }),
  );
}
sN.displayName = "Background";
var H4 = _.memo(sN);
function w0(e) {
  throw new Error(
    'Could not dynamically require "' +
      e +
      '". Please configure the dynamicRequireTargets or/and ignoreDynamicRequires option of @rollup/plugin-commonjs appropriately for this require call to work.',
  );
}
var mf, Ax;
function G4() {
  if (Ax) return mf;
  Ax = 1;
  function e() {
    (this.__data__ = []), (this.size = 0);
  }
  return (mf = e), mf;
}
var gf, Nx;
function To() {
  if (Nx) return gf;
  Nx = 1;
  function e(t, n) {
    return t === n || (t !== t && n !== n);
  }
  return (gf = e), gf;
}
var vf, Mx;
function Ql() {
  if (Mx) return vf;
  Mx = 1;
  var e = To();
  function t(n, r) {
    for (var i = n.length; i--; ) if (e(n[i][0], r)) return i;
    return -1;
  }
  return (vf = t), vf;
}
var yf, Ix;
function W4() {
  if (Ix) return yf;
  Ix = 1;
  var e = Ql(),
    t = Array.prototype,
    n = t.splice;
  function r(i) {
    var o = this.__data__,
      s = e(o, i);
    if (s < 0) return !1;
    var a = o.length - 1;
    return s == a ? o.pop() : n.call(o, s, 1), --this.size, !0;
  }
  return (yf = r), yf;
}
var wf, Dx;
function K4() {
  if (Dx) return wf;
  Dx = 1;
  var e = Ql();
  function t(n) {
    var r = this.__data__,
      i = e(r, n);
    return i < 0 ? void 0 : r[i][1];
  }
  return (wf = t), wf;
}
var xf, Ox;
function Y4() {
  if (Ox) return xf;
  Ox = 1;
  var e = Ql();
  function t(n) {
    return e(this.__data__, n) > -1;
  }
  return (xf = t), xf;
}
var _f, Lx;
function X4() {
  if (Lx) return _f;
  Lx = 1;
  var e = Ql();
  function t(n, r) {
    var i = this.__data__,
      o = e(i, n);
    return o < 0 ? (++this.size, i.push([n, r])) : (i[o][1] = r), this;
  }
  return (_f = t), _f;
}
var bf, Fx;
function Jl() {
  if (Fx) return bf;
  Fx = 1;
  var e = G4(),
    t = W4(),
    n = K4(),
    r = Y4(),
    i = X4();
  function o(s) {
    var a = -1,
      u = s == null ? 0 : s.length;
    for (this.clear(); ++a < u; ) {
      var l = s[a];
      this.set(l[0], l[1]);
    }
  }
  return (
    (o.prototype.clear = e),
    (o.prototype.delete = t),
    (o.prototype.get = n),
    (o.prototype.has = r),
    (o.prototype.set = i),
    (bf = o),
    bf
  );
}
var Sf, jx;
function Z4() {
  if (jx) return Sf;
  jx = 1;
  var e = Jl();
  function t() {
    (this.__data__ = new e()), (this.size = 0);
  }
  return (Sf = t), Sf;
}
var Ef, Vx;
function Q4() {
  if (Vx) return Ef;
  Vx = 1;
  function e(t) {
    var n = this.__data__,
      r = n.delete(t);
    return (this.size = n.size), r;
  }
  return (Ef = e), Ef;
}
var Cf, qx;
function J4() {
  if (qx) return Cf;
  qx = 1;
  function e(t) {
    return this.__data__.get(t);
  }
  return (Cf = e), Cf;
}
var Tf, $x;
function ez() {
  if ($x) return Tf;
  $x = 1;
  function e(t) {
    return this.__data__.has(t);
  }
  return (Tf = e), Tf;
}
var kf, zx;
function aN() {
  if (zx) return kf;
  zx = 1;
  var e = typeof ka == "object" && ka && ka.Object === Object && ka;
  return (kf = e), kf;
}
var Rf, Bx;
function on() {
  if (Bx) return Rf;
  Bx = 1;
  var e = aN(),
    t = typeof self == "object" && self && self.Object === Object && self,
    n = e || t || Function("return this")();
  return (Rf = n), Rf;
}
var Pf, Ux;
function ko() {
  if (Ux) return Pf;
  Ux = 1;
  var e = on(),
    t = e.Symbol;
  return (Pf = t), Pf;
}
var Af, Hx;
function tz() {
  if (Hx) return Af;
  Hx = 1;
  var e = ko(),
    t = Object.prototype,
    n = t.hasOwnProperty,
    r = t.toString,
    i = e ? e.toStringTag : void 0;
  function o(s) {
    var a = n.call(s, i),
      u = s[i];
    try {
      s[i] = void 0;
      var l = !0;
    } catch {}
    var c = r.call(s);
    return l && (a ? (s[i] = u) : delete s[i]), c;
  }
  return (Af = o), Af;
}
var Nf, Gx;
function nz() {
  if (Gx) return Nf;
  Gx = 1;
  var e = Object.prototype,
    t = e.toString;
  function n(r) {
    return t.call(r);
  }
  return (Nf = n), Nf;
}
var Mf, Wx;
function pi() {
  if (Wx) return Mf;
  Wx = 1;
  var e = ko(),
    t = tz(),
    n = nz(),
    r = "[object Null]",
    i = "[object Undefined]",
    o = e ? e.toStringTag : void 0;
  function s(a) {
    return a == null ? (a === void 0 ? i : r) : o && o in Object(a) ? t(a) : n(a);
  }
  return (Mf = s), Mf;
}
var If, Kx;
function $t() {
  if (Kx) return If;
  Kx = 1;
  function e(t) {
    var n = typeof t;
    return t != null && (n == "object" || n == "function");
  }
  return (If = e), If;
}
var Df, Yx;
function da() {
  if (Yx) return Df;
  Yx = 1;
  var e = pi(),
    t = $t(),
    n = "[object AsyncFunction]",
    r = "[object Function]",
    i = "[object GeneratorFunction]",
    o = "[object Proxy]";
  function s(a) {
    if (!t(a)) return !1;
    var u = e(a);
    return u == r || u == i || u == n || u == o;
  }
  return (Df = s), Df;
}
var Of, Xx;
function rz() {
  if (Xx) return Of;
  Xx = 1;
  var e = on(),
    t = e["__core-js_shared__"];
  return (Of = t), Of;
}
var Lf, Zx;
function iz() {
  if (Zx) return Lf;
  Zx = 1;
  var e = rz(),
    t = (function () {
      var r = /[^.]+$/.exec((e && e.keys && e.keys.IE_PROTO) || "");
      return r ? "Symbol(src)_1." + r : "";
    })();
  function n(r) {
    return !!t && t in r;
  }
  return (Lf = n), Lf;
}
var Ff, Qx;
function uN() {
  if (Qx) return Ff;
  Qx = 1;
  var e = Function.prototype,
    t = e.toString;
  function n(r) {
    if (r != null) {
      try {
        return t.call(r);
      } catch {}
      try {
        return r + "";
      } catch {}
    }
    return "";
  }
  return (Ff = n), Ff;
}
var jf, Jx;
function oz() {
  if (Jx) return jf;
  Jx = 1;
  var e = da(),
    t = iz(),
    n = $t(),
    r = uN(),
    i = /[\\^$.*+?()[\]{}|]/g,
    o = /^\[object .+?Constructor\]$/,
    s = Function.prototype,
    a = Object.prototype,
    u = s.toString,
    l = a.hasOwnProperty,
    c = RegExp(
      "^" +
        u
          .call(l)
          .replace(i, "\\$&")
          .replace(/hasOwnProperty|(function).*?(?=\\\()| for .+?(?=\\\])/g, "$1.*?") +
        "$",
    );
  function f(d) {
    if (!n(d) || t(d)) return !1;
    var h = e(d) ? c : o;
    return h.test(r(d));
  }
  return (jf = f), jf;
}
var Vf, e_;
function sz() {
  if (e_) return Vf;
  e_ = 1;
  function e(t, n) {
    return t == null ? void 0 : t[n];
  }
  return (Vf = e), Vf;
}
var qf, t_;
function mi() {
  if (t_) return qf;
  t_ = 1;
  var e = oz(),
    t = sz();
  function n(r, i) {
    var o = t(r, i);
    return e(o) ? o : void 0;
  }
  return (qf = n), qf;
}
var $f, n_;
function x0() {
  if (n_) return $f;
  n_ = 1;
  var e = mi(),
    t = on(),
    n = e(t, "Map");
  return ($f = n), $f;
}
var zf, r_;
function ec() {
  if (r_) return zf;
  r_ = 1;
  var e = mi(),
    t = e(Object, "create");
  return (zf = t), zf;
}
var Bf, i_;
function az() {
  if (i_) return Bf;
  i_ = 1;
  var e = ec();
  function t() {
    (this.__data__ = e ? e(null) : {}), (this.size = 0);
  }
  return (Bf = t), Bf;
}
var Uf, o_;
function uz() {
  if (o_) return Uf;
  o_ = 1;
  function e(t) {
    var n = this.has(t) && delete this.__data__[t];
    return (this.size -= n ? 1 : 0), n;
  }
  return (Uf = e), Uf;
}
var Hf, s_;
function lz() {
  if (s_) return Hf;
  s_ = 1;
  var e = ec(),
    t = "__lodash_hash_undefined__",
    n = Object.prototype,
    r = n.hasOwnProperty;
  function i(o) {
    var s = this.__data__;
    if (e) {
      var a = s[o];
      return a === t ? void 0 : a;
    }
    return r.call(s, o) ? s[o] : void 0;
  }
  return (Hf = i), Hf;
}
var Gf, a_;
function cz() {
  if (a_) return Gf;
  a_ = 1;
  var e = ec(),
    t = Object.prototype,
    n = t.hasOwnProperty;
  function r(i) {
    var o = this.__data__;
    return e ? o[i] !== void 0 : n.call(o, i);
  }
  return (Gf = r), Gf;
}
var Wf, u_;
function fz() {
  if (u_) return Wf;
  u_ = 1;
  var e = ec(),
    t = "__lodash_hash_undefined__";
  function n(r, i) {
    var o = this.__data__;
    return (this.size += this.has(r) ? 0 : 1), (o[r] = e && i === void 0 ? t : i), this;
  }
  return (Wf = n), Wf;
}
var Kf, l_;
function dz() {
  if (l_) return Kf;
  l_ = 1;
  var e = az(),
    t = uz(),
    n = lz(),
    r = cz(),
    i = fz();
  function o(s) {
    var a = -1,
      u = s == null ? 0 : s.length;
    for (this.clear(); ++a < u; ) {
      var l = s[a];
      this.set(l[0], l[1]);
    }
  }
  return (
    (o.prototype.clear = e),
    (o.prototype.delete = t),
    (o.prototype.get = n),
    (o.prototype.has = r),
    (o.prototype.set = i),
    (Kf = o),
    Kf
  );
}
var Yf, c_;
function hz() {
  if (c_) return Yf;
  c_ = 1;
  var e = dz(),
    t = Jl(),
    n = x0();
  function r() {
    (this.size = 0), (this.__data__ = { hash: new e(), map: new (n || t)(), string: new e() });
  }
  return (Yf = r), Yf;
}
var Xf, f_;
function pz() {
  if (f_) return Xf;
  f_ = 1;
  function e(t) {
    var n = typeof t;
    return n == "string" || n == "number" || n == "symbol" || n == "boolean"
      ? t !== "__proto__"
      : t === null;
  }
  return (Xf = e), Xf;
}
var Zf, d_;
function tc() {
  if (d_) return Zf;
  d_ = 1;
  var e = pz();
  function t(n, r) {
    var i = n.__data__;
    return e(r) ? i[typeof r == "string" ? "string" : "hash"] : i.map;
  }
  return (Zf = t), Zf;
}
var Qf, h_;
function mz() {
  if (h_) return Qf;
  h_ = 1;
  var e = tc();
  function t(n) {
    var r = e(this, n).delete(n);
    return (this.size -= r ? 1 : 0), r;
  }
  return (Qf = t), Qf;
}
var Jf, p_;
function gz() {
  if (p_) return Jf;
  p_ = 1;
  var e = tc();
  function t(n) {
    return e(this, n).get(n);
  }
  return (Jf = t), Jf;
}
var ed, m_;
function vz() {
  if (m_) return ed;
  m_ = 1;
  var e = tc();
  function t(n) {
    return e(this, n).has(n);
  }
  return (ed = t), ed;
}
var td, g_;
function yz() {
  if (g_) return td;
  g_ = 1;
  var e = tc();
  function t(n, r) {
    var i = e(this, n),
      o = i.size;
    return i.set(n, r), (this.size += i.size == o ? 0 : 1), this;
  }
  return (td = t), td;
}
var nd, v_;
function _0() {
  if (v_) return nd;
  v_ = 1;
  var e = hz(),
    t = mz(),
    n = gz(),
    r = vz(),
    i = yz();
  function o(s) {
    var a = -1,
      u = s == null ? 0 : s.length;
    for (this.clear(); ++a < u; ) {
      var l = s[a];
      this.set(l[0], l[1]);
    }
  }
  return (
    (o.prototype.clear = e),
    (o.prototype.delete = t),
    (o.prototype.get = n),
    (o.prototype.has = r),
    (o.prototype.set = i),
    (nd = o),
    nd
  );
}
var rd, y_;
function wz() {
  if (y_) return rd;
  y_ = 1;
  var e = Jl(),
    t = x0(),
    n = _0(),
    r = 200;
  function i(o, s) {
    var a = this.__data__;
    if (a instanceof e) {
      var u = a.__data__;
      if (!t || u.length < r - 1) return u.push([o, s]), (this.size = ++a.size), this;
      a = this.__data__ = new n(u);
    }
    return a.set(o, s), (this.size = a.size), this;
  }
  return (rd = i), rd;
}
var id, w_;
function nc() {
  if (w_) return id;
  w_ = 1;
  var e = Jl(),
    t = Z4(),
    n = Q4(),
    r = J4(),
    i = ez(),
    o = wz();
  function s(a) {
    var u = (this.__data__ = new e(a));
    this.size = u.size;
  }
  return (
    (s.prototype.clear = t),
    (s.prototype.delete = n),
    (s.prototype.get = r),
    (s.prototype.has = i),
    (s.prototype.set = o),
    (id = s),
    id
  );
}
var od, x_;
function b0() {
  if (x_) return od;
  x_ = 1;
  function e(t, n) {
    for (var r = -1, i = t == null ? 0 : t.length; ++r < i && n(t[r], r, t) !== !1; );
    return t;
  }
  return (od = e), od;
}
var sd, __;
function lN() {
  if (__) return sd;
  __ = 1;
  var e = mi(),
    t = (function () {
      try {
        var n = e(Object, "defineProperty");
        return n({}, "", {}), n;
      } catch {}
    })();
  return (sd = t), sd;
}
var ad, b_;
function rc() {
  if (b_) return ad;
  b_ = 1;
  var e = lN();
  function t(n, r, i) {
    r == "__proto__" && e
      ? e(n, r, { configurable: !0, enumerable: !0, value: i, writable: !0 })
      : (n[r] = i);
  }
  return (ad = t), ad;
}
var ud, S_;
function ic() {
  if (S_) return ud;
  S_ = 1;
  var e = rc(),
    t = To(),
    n = Object.prototype,
    r = n.hasOwnProperty;
  function i(o, s, a) {
    var u = o[s];
    (!(r.call(o, s) && t(u, a)) || (a === void 0 && !(s in o))) && e(o, s, a);
  }
  return (ud = i), ud;
}
var ld, E_;
function ha() {
  if (E_) return ld;
  E_ = 1;
  var e = ic(),
    t = rc();
  function n(r, i, o, s) {
    var a = !o;
    o || (o = {});
    for (var u = -1, l = i.length; ++u < l; ) {
      var c = i[u],
        f = s ? s(o[c], r[c], c, o, r) : void 0;
      f === void 0 && (f = r[c]), a ? t(o, c, f) : e(o, c, f);
    }
    return o;
  }
  return (ld = n), ld;
}
var cd, C_;
function xz() {
  if (C_) return cd;
  C_ = 1;
  function e(t, n) {
    for (var r = -1, i = Array(t); ++r < t; ) i[r] = n(r);
    return i;
  }
  return (cd = e), cd;
}
var fd, T_;
function En() {
  if (T_) return fd;
  T_ = 1;
  function e(t) {
    return t != null && typeof t == "object";
  }
  return (fd = e), fd;
}
var dd, k_;
function _z() {
  if (k_) return dd;
  k_ = 1;
  var e = pi(),
    t = En(),
    n = "[object Arguments]";
  function r(i) {
    return t(i) && e(i) == n;
  }
  return (dd = r), dd;
}
var hd, R_;
function pa() {
  if (R_) return hd;
  R_ = 1;
  var e = _z(),
    t = En(),
    n = Object.prototype,
    r = n.hasOwnProperty,
    i = n.propertyIsEnumerable,
    o = e(
      (function () {
        return arguments;
      })(),
    )
      ? e
      : function (s) {
          return t(s) && r.call(s, "callee") && !i.call(s, "callee");
        };
  return (hd = o), hd;
}
var pd, P_;
function Ie() {
  if (P_) return pd;
  P_ = 1;
  var e = Array.isArray;
  return (pd = e), pd;
}
var os = { exports: {} },
  md,
  A_;
function bz() {
  if (A_) return md;
  A_ = 1;
  function e() {
    return !1;
  }
  return (md = e), md;
}
os.exports;
var N_;
function Ro() {
  return (
    N_ ||
      ((N_ = 1),
      (function (e, t) {
        var n = on(),
          r = bz(),
          i = t && !t.nodeType && t,
          o = i && !0 && e && !e.nodeType && e,
          s = o && o.exports === i,
          a = s ? n.Buffer : void 0,
          u = a ? a.isBuffer : void 0,
          l = u || r;
        e.exports = l;
      })(os, os.exports)),
    os.exports
  );
}
var gd, M_;
function oc() {
  if (M_) return gd;
  M_ = 1;
  var e = 9007199254740991,
    t = /^(?:0|[1-9]\d*)$/;
  function n(r, i) {
    var o = typeof r;
    return (
      (i = i ?? e),
      !!i && (o == "number" || (o != "symbol" && t.test(r))) && r > -1 && r % 1 == 0 && r < i
    );
  }
  return (gd = n), gd;
}
var vd, I_;
function S0() {
  if (I_) return vd;
  I_ = 1;
  var e = 9007199254740991;
  function t(n) {
    return typeof n == "number" && n > -1 && n % 1 == 0 && n <= e;
  }
  return (vd = t), vd;
}
var yd, D_;
function Sz() {
  if (D_) return yd;
  D_ = 1;
  var e = pi(),
    t = S0(),
    n = En(),
    r = "[object Arguments]",
    i = "[object Array]",
    o = "[object Boolean]",
    s = "[object Date]",
    a = "[object Error]",
    u = "[object Function]",
    l = "[object Map]",
    c = "[object Number]",
    f = "[object Object]",
    d = "[object RegExp]",
    h = "[object Set]",
    v = "[object String]",
    p = "[object WeakMap]",
    y = "[object ArrayBuffer]",
    m = "[object DataView]",
    g = "[object Float32Array]",
    w = "[object Float64Array]",
    x = "[object Int8Array]",
    b = "[object Int16Array]",
    E = "[object Int32Array]",
    C = "[object Uint8Array]",
    T = "[object Uint8ClampedArray]",
    P = "[object Uint16Array]",
    M = "[object Uint32Array]",
    I = {};
  (I[g] = I[w] = I[x] = I[b] = I[E] = I[C] = I[T] = I[P] = I[M] = !0),
    (I[r] =
      I[i] =
      I[y] =
      I[o] =
      I[m] =
      I[s] =
      I[a] =
      I[u] =
      I[l] =
      I[c] =
      I[f] =
      I[d] =
      I[h] =
      I[v] =
      I[p] =
        !1);
  function j(q) {
    return n(q) && t(q.length) && !!I[e(q)];
  }
  return (yd = j), yd;
}
var wd, O_;
function sc() {
  if (O_) return wd;
  O_ = 1;
  function e(t) {
    return function (n) {
      return t(n);
    };
  }
  return (wd = e), wd;
}
var ss = { exports: {} };
ss.exports;
var L_;
function E0() {
  return (
    L_ ||
      ((L_ = 1),
      (function (e, t) {
        var n = aN(),
          r = t && !t.nodeType && t,
          i = r && !0 && e && !e.nodeType && e,
          o = i && i.exports === r,
          s = o && n.process,
          a = (function () {
            try {
              var u = i && i.require && i.require("util").types;
              return u || (s && s.binding && s.binding("util"));
            } catch {}
          })();
        e.exports = a;
      })(ss, ss.exports)),
    ss.exports
  );
}
var xd, F_;
function ma() {
  if (F_) return xd;
  F_ = 1;
  var e = Sz(),
    t = sc(),
    n = E0(),
    r = n && n.isTypedArray,
    i = r ? t(r) : e;
  return (xd = i), xd;
}
var _d, j_;
function cN() {
  if (j_) return _d;
  j_ = 1;
  var e = xz(),
    t = pa(),
    n = Ie(),
    r = Ro(),
    i = oc(),
    o = ma(),
    s = Object.prototype,
    a = s.hasOwnProperty;
  function u(l, c) {
    var f = n(l),
      d = !f && t(l),
      h = !f && !d && r(l),
      v = !f && !d && !h && o(l),
      p = f || d || h || v,
      y = p ? e(l.length, String) : [],
      m = y.length;
    for (var g in l)
      (c || a.call(l, g)) &&
        !(
          p &&
          (g == "length" ||
            (h && (g == "offset" || g == "parent")) ||
            (v && (g == "buffer" || g == "byteLength" || g == "byteOffset")) ||
            i(g, m))
        ) &&
        y.push(g);
    return y;
  }
  return (_d = u), _d;
}
var bd, V_;
function ac() {
  if (V_) return bd;
  V_ = 1;
  var e = Object.prototype;
  function t(n) {
    var r = n && n.constructor,
      i = (typeof r == "function" && r.prototype) || e;
    return n === i;
  }
  return (bd = t), bd;
}
var Sd, q_;
function fN() {
  if (q_) return Sd;
  q_ = 1;
  function e(t, n) {
    return function (r) {
      return t(n(r));
    };
  }
  return (Sd = e), Sd;
}
var Ed, $_;
function Ez() {
  if ($_) return Ed;
  $_ = 1;
  var e = fN(),
    t = e(Object.keys, Object);
  return (Ed = t), Ed;
}
var Cd, z_;
function C0() {
  if (z_) return Cd;
  z_ = 1;
  var e = ac(),
    t = Ez(),
    n = Object.prototype,
    r = n.hasOwnProperty;
  function i(o) {
    if (!e(o)) return t(o);
    var s = [];
    for (var a in Object(o)) r.call(o, a) && a != "constructor" && s.push(a);
    return s;
  }
  return (Cd = i), Cd;
}
var Td, B_;
function Jn() {
  if (B_) return Td;
  B_ = 1;
  var e = da(),
    t = S0();
  function n(r) {
    return r != null && t(r.length) && !e(r);
  }
  return (Td = n), Td;
}
var kd, U_;
function Lr() {
  if (U_) return kd;
  U_ = 1;
  var e = cN(),
    t = C0(),
    n = Jn();
  function r(i) {
    return n(i) ? e(i) : t(i);
  }
  return (kd = r), kd;
}
var Rd, H_;
function Cz() {
  if (H_) return Rd;
  H_ = 1;
  var e = ha(),
    t = Lr();
  function n(r, i) {
    return r && e(i, t(i), r);
  }
  return (Rd = n), Rd;
}
var Pd, G_;
function Tz() {
  if (G_) return Pd;
  G_ = 1;
  function e(t) {
    var n = [];
    if (t != null) for (var r in Object(t)) n.push(r);
    return n;
  }
  return (Pd = e), Pd;
}
var Ad, W_;
function kz() {
  if (W_) return Ad;
  W_ = 1;
  var e = $t(),
    t = ac(),
    n = Tz(),
    r = Object.prototype,
    i = r.hasOwnProperty;
  function o(s) {
    if (!e(s)) return n(s);
    var a = t(s),
      u = [];
    for (var l in s) (l == "constructor" && (a || !i.call(s, l))) || u.push(l);
    return u;
  }
  return (Ad = o), Ad;
}
var Nd, K_;
function gi() {
  if (K_) return Nd;
  K_ = 1;
  var e = cN(),
    t = kz(),
    n = Jn();
  function r(i) {
    return n(i) ? e(i, !0) : t(i);
  }
  return (Nd = r), Nd;
}
var Md, Y_;
function Rz() {
  if (Y_) return Md;
  Y_ = 1;
  var e = ha(),
    t = gi();
  function n(r, i) {
    return r && e(i, t(i), r);
  }
  return (Md = n), Md;
}
var as = { exports: {} };
as.exports;
var X_;
function dN() {
  return (
    X_ ||
      ((X_ = 1),
      (function (e, t) {
        var n = on(),
          r = t && !t.nodeType && t,
          i = r && !0 && e && !e.nodeType && e,
          o = i && i.exports === r,
          s = o ? n.Buffer : void 0,
          a = s ? s.allocUnsafe : void 0;
        function u(l, c) {
          if (c) return l.slice();
          var f = l.length,
            d = a ? a(f) : new l.constructor(f);
          return l.copy(d), d;
        }
        e.exports = u;
      })(as, as.exports)),
    as.exports
  );
}
var Id, Z_;
function hN() {
  if (Z_) return Id;
  Z_ = 1;
  function e(t, n) {
    var r = -1,
      i = t.length;
    for (n || (n = Array(i)); ++r < i; ) n[r] = t[r];
    return n;
  }
  return (Id = e), Id;
}
var Dd, Q_;
function pN() {
  if (Q_) return Dd;
  Q_ = 1;
  function e(t, n) {
    for (var r = -1, i = t == null ? 0 : t.length, o = 0, s = []; ++r < i; ) {
      var a = t[r];
      n(a, r, t) && (s[o++] = a);
    }
    return s;
  }
  return (Dd = e), Dd;
}
var Od, J_;
function mN() {
  if (J_) return Od;
  J_ = 1;
  function e() {
    return [];
  }
  return (Od = e), Od;
}
var Ld, eb;
function T0() {
  if (eb) return Ld;
  eb = 1;
  var e = pN(),
    t = mN(),
    n = Object.prototype,
    r = n.propertyIsEnumerable,
    i = Object.getOwnPropertySymbols,
    o = i
      ? function (s) {
          return s == null
            ? []
            : ((s = Object(s)),
              e(i(s), function (a) {
                return r.call(s, a);
              }));
        }
      : t;
  return (Ld = o), Ld;
}
var Fd, tb;
function Pz() {
  if (tb) return Fd;
  tb = 1;
  var e = ha(),
    t = T0();
  function n(r, i) {
    return e(r, t(r), i);
  }
  return (Fd = n), Fd;
}
var jd, nb;
function k0() {
  if (nb) return jd;
  nb = 1;
  function e(t, n) {
    for (var r = -1, i = n.length, o = t.length; ++r < i; ) t[o + r] = n[r];
    return t;
  }
  return (jd = e), jd;
}
var Vd, rb;
function uc() {
  if (rb) return Vd;
  rb = 1;
  var e = fN(),
    t = e(Object.getPrototypeOf, Object);
  return (Vd = t), Vd;
}
var qd, ib;
function gN() {
  if (ib) return qd;
  ib = 1;
  var e = k0(),
    t = uc(),
    n = T0(),
    r = mN(),
    i = Object.getOwnPropertySymbols,
    o = i
      ? function (s) {
          for (var a = []; s; ) e(a, n(s)), (s = t(s));
          return a;
        }
      : r;
  return (qd = o), qd;
}
var $d, ob;
function Az() {
  if (ob) return $d;
  ob = 1;
  var e = ha(),
    t = gN();
  function n(r, i) {
    return e(r, t(r), i);
  }
  return ($d = n), $d;
}
var zd, sb;
function vN() {
  if (sb) return zd;
  sb = 1;
  var e = k0(),
    t = Ie();
  function n(r, i, o) {
    var s = i(r);
    return t(r) ? s : e(s, o(r));
  }
  return (zd = n), zd;
}
var Bd, ab;
function yN() {
  if (ab) return Bd;
  ab = 1;
  var e = vN(),
    t = T0(),
    n = Lr();
  function r(i) {
    return e(i, n, t);
  }
  return (Bd = r), Bd;
}
var Ud, ub;
function Nz() {
  if (ub) return Ud;
  ub = 1;
  var e = vN(),
    t = gN(),
    n = gi();
  function r(i) {
    return e(i, n, t);
  }
  return (Ud = r), Ud;
}
var Hd, lb;
function Mz() {
  if (lb) return Hd;
  lb = 1;
  var e = mi(),
    t = on(),
    n = e(t, "DataView");
  return (Hd = n), Hd;
}
var Gd, cb;
function Iz() {
  if (cb) return Gd;
  cb = 1;
  var e = mi(),
    t = on(),
    n = e(t, "Promise");
  return (Gd = n), Gd;
}
var Wd, fb;
function wN() {
  if (fb) return Wd;
  fb = 1;
  var e = mi(),
    t = on(),
    n = e(t, "Set");
  return (Wd = n), Wd;
}
var Kd, db;
function Dz() {
  if (db) return Kd;
  db = 1;
  var e = mi(),
    t = on(),
    n = e(t, "WeakMap");
  return (Kd = n), Kd;
}
var Yd, hb;
function Po() {
  if (hb) return Yd;
  hb = 1;
  var e = Mz(),
    t = x0(),
    n = Iz(),
    r = wN(),
    i = Dz(),
    o = pi(),
    s = uN(),
    a = "[object Map]",
    u = "[object Object]",
    l = "[object Promise]",
    c = "[object Set]",
    f = "[object WeakMap]",
    d = "[object DataView]",
    h = s(e),
    v = s(t),
    p = s(n),
    y = s(r),
    m = s(i),
    g = o;
  return (
    ((e && g(new e(new ArrayBuffer(1))) != d) ||
      (t && g(new t()) != a) ||
      (n && g(n.resolve()) != l) ||
      (r && g(new r()) != c) ||
      (i && g(new i()) != f)) &&
      (g = function (w) {
        var x = o(w),
          b = x == u ? w.constructor : void 0,
          E = b ? s(b) : "";
        if (E)
          switch (E) {
            case h:
              return d;
            case v:
              return a;
            case p:
              return l;
            case y:
              return c;
            case m:
              return f;
          }
        return x;
      }),
    (Yd = g),
    Yd
  );
}
var Xd, pb;
function Oz() {
  if (pb) return Xd;
  pb = 1;
  var e = Object.prototype,
    t = e.hasOwnProperty;
  function n(r) {
    var i = r.length,
      o = new r.constructor(i);
    return (
      i &&
        typeof r[0] == "string" &&
        t.call(r, "index") &&
        ((o.index = r.index), (o.input = r.input)),
      o
    );
  }
  return (Xd = n), Xd;
}
var Zd, mb;
function xN() {
  if (mb) return Zd;
  mb = 1;
  var e = on(),
    t = e.Uint8Array;
  return (Zd = t), Zd;
}
var Qd, gb;
function R0() {
  if (gb) return Qd;
  gb = 1;
  var e = xN();
  function t(n) {
    var r = new n.constructor(n.byteLength);
    return new e(r).set(new e(n)), r;
  }
  return (Qd = t), Qd;
}
var Jd, vb;
function Lz() {
  if (vb) return Jd;
  vb = 1;
  var e = R0();
  function t(n, r) {
    var i = r ? e(n.buffer) : n.buffer;
    return new n.constructor(i, n.byteOffset, n.byteLength);
  }
  return (Jd = t), Jd;
}
var eh, yb;
function Fz() {
  if (yb) return eh;
  yb = 1;
  var e = /\w*$/;
  function t(n) {
    var r = new n.constructor(n.source, e.exec(n));
    return (r.lastIndex = n.lastIndex), r;
  }
  return (eh = t), eh;
}
var th, wb;
function jz() {
  if (wb) return th;
  wb = 1;
  var e = ko(),
    t = e ? e.prototype : void 0,
    n = t ? t.valueOf : void 0;
  function r(i) {
    return n ? Object(n.call(i)) : {};
  }
  return (th = r), th;
}
var nh, xb;
function _N() {
  if (xb) return nh;
  xb = 1;
  var e = R0();
  function t(n, r) {
    var i = r ? e(n.buffer) : n.buffer;
    return new n.constructor(i, n.byteOffset, n.length);
  }
  return (nh = t), nh;
}
var rh, _b;
function Vz() {
  if (_b) return rh;
  _b = 1;
  var e = R0(),
    t = Lz(),
    n = Fz(),
    r = jz(),
    i = _N(),
    o = "[object Boolean]",
    s = "[object Date]",
    a = "[object Map]",
    u = "[object Number]",
    l = "[object RegExp]",
    c = "[object Set]",
    f = "[object String]",
    d = "[object Symbol]",
    h = "[object ArrayBuffer]",
    v = "[object DataView]",
    p = "[object Float32Array]",
    y = "[object Float64Array]",
    m = "[object Int8Array]",
    g = "[object Int16Array]",
    w = "[object Int32Array]",
    x = "[object Uint8Array]",
    b = "[object Uint8ClampedArray]",
    E = "[object Uint16Array]",
    C = "[object Uint32Array]";
  function T(P, M, I) {
    var j = P.constructor;
    switch (M) {
      case h:
        return e(P);
      case o:
      case s:
        return new j(+P);
      case v:
        return t(P, I);
      case p:
      case y:
      case m:
      case g:
      case w:
      case x:
      case b:
      case E:
      case C:
        return i(P, I);
      case a:
        return new j();
      case u:
      case f:
        return new j(P);
      case l:
        return n(P);
      case c:
        return new j();
      case d:
        return r(P);
    }
  }
  return (rh = T), rh;
}
var ih, bb;
function bN() {
  if (bb) return ih;
  bb = 1;
  var e = $t(),
    t = Object.create,
    n = (function () {
      function r() {}
      return function (i) {
        if (!e(i)) return {};
        if (t) return t(i);
        r.prototype = i;
        var o = new r();
        return (r.prototype = void 0), o;
      };
    })();
  return (ih = n), ih;
}
var oh, Sb;
function SN() {
  if (Sb) return oh;
  Sb = 1;
  var e = bN(),
    t = uc(),
    n = ac();
  function r(i) {
    return typeof i.constructor == "function" && !n(i) ? e(t(i)) : {};
  }
  return (oh = r), oh;
}
var sh, Eb;
function qz() {
  if (Eb) return sh;
  Eb = 1;
  var e = Po(),
    t = En(),
    n = "[object Map]";
  function r(i) {
    return t(i) && e(i) == n;
  }
  return (sh = r), sh;
}
var ah, Cb;
function $z() {
  if (Cb) return ah;
  Cb = 1;
  var e = qz(),
    t = sc(),
    n = E0(),
    r = n && n.isMap,
    i = r ? t(r) : e;
  return (ah = i), ah;
}
var uh, Tb;
function zz() {
  if (Tb) return uh;
  Tb = 1;
  var e = Po(),
    t = En(),
    n = "[object Set]";
  function r(i) {
    return t(i) && e(i) == n;
  }
  return (uh = r), uh;
}
var lh, kb;
function Bz() {
  if (kb) return lh;
  kb = 1;
  var e = zz(),
    t = sc(),
    n = E0(),
    r = n && n.isSet,
    i = r ? t(r) : e;
  return (lh = i), lh;
}
var ch, Rb;
function EN() {
  if (Rb) return ch;
  Rb = 1;
  var e = nc(),
    t = b0(),
    n = ic(),
    r = Cz(),
    i = Rz(),
    o = dN(),
    s = hN(),
    a = Pz(),
    u = Az(),
    l = yN(),
    c = Nz(),
    f = Po(),
    d = Oz(),
    h = Vz(),
    v = SN(),
    p = Ie(),
    y = Ro(),
    m = $z(),
    g = $t(),
    w = Bz(),
    x = Lr(),
    b = gi(),
    E = 1,
    C = 2,
    T = 4,
    P = "[object Arguments]",
    M = "[object Array]",
    I = "[object Boolean]",
    j = "[object Date]",
    q = "[object Error]",
    S = "[object Function]",
    O = "[object GeneratorFunction]",
    A = "[object Map]",
    F = "[object Number]",
    N = "[object Object]",
    k = "[object RegExp]",
    D = "[object Set]",
    V = "[object String]",
    $ = "[object Symbol]",
    U = "[object WeakMap]",
    B = "[object ArrayBuffer]",
    W = "[object DataView]",
    X = "[object Float32Array]",
    ee = "[object Float64Array]",
    ue = "[object Int8Array]",
    se = "[object Int16Array]",
    oe = "[object Int32Array]",
    De = "[object Uint8Array]",
    Re = "[object Uint8ClampedArray]",
    Ge = "[object Uint16Array]",
    je = "[object Uint32Array]",
    Q = {};
  (Q[P] =
    Q[M] =
    Q[B] =
    Q[W] =
    Q[I] =
    Q[j] =
    Q[X] =
    Q[ee] =
    Q[ue] =
    Q[se] =
    Q[oe] =
    Q[A] =
    Q[F] =
    Q[N] =
    Q[k] =
    Q[D] =
    Q[V] =
    Q[$] =
    Q[De] =
    Q[Re] =
    Q[Ge] =
    Q[je] =
      !0),
    (Q[q] = Q[S] = Q[U] = !1);
  function Ve(K, G, Ee, Ut, un, it) {
    var Pe,
      ft = G & E,
      Ht = G & C,
      Cn = G & T;
    if ((Ee && (Pe = un ? Ee(K, Ut, un, it) : Ee(K)), Pe !== void 0)) return Pe;
    if (!g(K)) return K;
    var ln = p(K);
    if (ln) {
      if (((Pe = d(K)), !ft)) return s(K, Pe);
    } else {
      var xt = f(K),
        Tn = xt == S || xt == O;
      if (y(K)) return o(K, ft);
      if (xt == N || xt == P || (Tn && !un)) {
        if (((Pe = Ht || Tn ? {} : v(K)), !ft)) return Ht ? u(K, i(Pe, K)) : a(K, r(Pe, K));
      } else {
        if (!Q[xt]) return un ? K : {};
        Pe = h(K, xt, ft);
      }
    }
    it || (it = new e());
    var tr = it.get(K);
    if (tr) return tr;
    it.set(K, Pe),
      w(K)
        ? K.forEach(function (Qe) {
            Pe.add(Ve(Qe, G, Ee, Qe, K, it));
          })
        : m(K) &&
          K.forEach(function (Qe, ot) {
            Pe.set(ot, Ve(Qe, G, Ee, ot, K, it));
          });
    var qe = Cn ? (Ht ? c : l) : Ht ? b : x,
      dt = ln ? void 0 : qe(K);
    return (
      t(dt || K, function (Qe, ot) {
        dt && ((ot = Qe), (Qe = K[ot])), n(Pe, ot, Ve(Qe, G, Ee, ot, K, it));
      }),
      Pe
    );
  }
  return (ch = Ve), ch;
}
var fh, Pb;
function Uz() {
  if (Pb) return fh;
  Pb = 1;
  var e = EN(),
    t = 4;
  function n(r) {
    return e(r, t);
  }
  return (fh = n), fh;
}
var dh, Ab;
function P0() {
  if (Ab) return dh;
  Ab = 1;
  function e(t) {
    return function () {
      return t;
    };
  }
  return (dh = e), dh;
}
var hh, Nb;
function Hz() {
  if (Nb) return hh;
  Nb = 1;
  function e(t) {
    return function (n, r, i) {
      for (var o = -1, s = Object(n), a = i(n), u = a.length; u--; ) {
        var l = a[t ? u : ++o];
        if (r(s[l], l, s) === !1) break;
      }
      return n;
    };
  }
  return (hh = e), hh;
}
var ph, Mb;
function A0() {
  if (Mb) return ph;
  Mb = 1;
  var e = Hz(),
    t = e();
  return (ph = t), ph;
}
var mh, Ib;
function N0() {
  if (Ib) return mh;
  Ib = 1;
  var e = A0(),
    t = Lr();
  function n(r, i) {
    return r && e(r, i, t);
  }
  return (mh = n), mh;
}
var gh, Db;
function Gz() {
  if (Db) return gh;
  Db = 1;
  var e = Jn();
  function t(n, r) {
    return function (i, o) {
      if (i == null) return i;
      if (!e(i)) return n(i, o);
      for (
        var s = i.length, a = r ? s : -1, u = Object(i);
        (r ? a-- : ++a < s) && o(u[a], a, u) !== !1;

      );
      return i;
    };
  }
  return (gh = t), gh;
}
var vh, Ob;
function lc() {
  if (Ob) return vh;
  Ob = 1;
  var e = N0(),
    t = Gz(),
    n = t(e);
  return (vh = n), vh;
}
var yh, Lb;
function vi() {
  if (Lb) return yh;
  Lb = 1;
  function e(t) {
    return t;
  }
  return (yh = e), yh;
}
var wh, Fb;
function CN() {
  if (Fb) return wh;
  Fb = 1;
  var e = vi();
  function t(n) {
    return typeof n == "function" ? n : e;
  }
  return (wh = t), wh;
}
var xh, jb;
function TN() {
  if (jb) return xh;
  jb = 1;
  var e = b0(),
    t = lc(),
    n = CN(),
    r = Ie();
  function i(o, s) {
    var a = r(o) ? e : t;
    return a(o, n(s));
  }
  return (xh = i), xh;
}
var _h, Vb;
function kN() {
  return Vb || ((Vb = 1), (_h = TN())), _h;
}
var bh, qb;
function Wz() {
  if (qb) return bh;
  qb = 1;
  var e = lc();
  function t(n, r) {
    var i = [];
    return (
      e(n, function (o, s, a) {
        r(o, s, a) && i.push(o);
      }),
      i
    );
  }
  return (bh = t), bh;
}
var Sh, $b;
function Kz() {
  if ($b) return Sh;
  $b = 1;
  var e = "__lodash_hash_undefined__";
  function t(n) {
    return this.__data__.set(n, e), this;
  }
  return (Sh = t), Sh;
}
var Eh, zb;
function Yz() {
  if (zb) return Eh;
  zb = 1;
  function e(t) {
    return this.__data__.has(t);
  }
  return (Eh = e), Eh;
}
var Ch, Bb;
function RN() {
  if (Bb) return Ch;
  Bb = 1;
  var e = _0(),
    t = Kz(),
    n = Yz();
  function r(i) {
    var o = -1,
      s = i == null ? 0 : i.length;
    for (this.__data__ = new e(); ++o < s; ) this.add(i[o]);
  }
  return (r.prototype.add = r.prototype.push = t), (r.prototype.has = n), (Ch = r), Ch;
}
var Th, Ub;
function Xz() {
  if (Ub) return Th;
  Ub = 1;
  function e(t, n) {
    for (var r = -1, i = t == null ? 0 : t.length; ++r < i; ) if (n(t[r], r, t)) return !0;
    return !1;
  }
  return (Th = e), Th;
}
var kh, Hb;
function PN() {
  if (Hb) return kh;
  Hb = 1;
  function e(t, n) {
    return t.has(n);
  }
  return (kh = e), kh;
}
var Rh, Gb;
function AN() {
  if (Gb) return Rh;
  Gb = 1;
  var e = RN(),
    t = Xz(),
    n = PN(),
    r = 1,
    i = 2;
  function o(s, a, u, l, c, f) {
    var d = u & r,
      h = s.length,
      v = a.length;
    if (h != v && !(d && v > h)) return !1;
    var p = f.get(s),
      y = f.get(a);
    if (p && y) return p == a && y == s;
    var m = -1,
      g = !0,
      w = u & i ? new e() : void 0;
    for (f.set(s, a), f.set(a, s); ++m < h; ) {
      var x = s[m],
        b = a[m];
      if (l) var E = d ? l(b, x, m, a, s, f) : l(x, b, m, s, a, f);
      if (E !== void 0) {
        if (E) continue;
        g = !1;
        break;
      }
      if (w) {
        if (
          !t(a, function (C, T) {
            if (!n(w, T) && (x === C || c(x, C, u, l, f))) return w.push(T);
          })
        ) {
          g = !1;
          break;
        }
      } else if (!(x === b || c(x, b, u, l, f))) {
        g = !1;
        break;
      }
    }
    return f.delete(s), f.delete(a), g;
  }
  return (Rh = o), Rh;
}
var Ph, Wb;
function Zz() {
  if (Wb) return Ph;
  Wb = 1;
  function e(t) {
    var n = -1,
      r = Array(t.size);
    return (
      t.forEach(function (i, o) {
        r[++n] = [o, i];
      }),
      r
    );
  }
  return (Ph = e), Ph;
}
var Ah, Kb;
function M0() {
  if (Kb) return Ah;
  Kb = 1;
  function e(t) {
    var n = -1,
      r = Array(t.size);
    return (
      t.forEach(function (i) {
        r[++n] = i;
      }),
      r
    );
  }
  return (Ah = e), Ah;
}
var Nh, Yb;
function Qz() {
  if (Yb) return Nh;
  Yb = 1;
  var e = ko(),
    t = xN(),
    n = To(),
    r = AN(),
    i = Zz(),
    o = M0(),
    s = 1,
    a = 2,
    u = "[object Boolean]",
    l = "[object Date]",
    c = "[object Error]",
    f = "[object Map]",
    d = "[object Number]",
    h = "[object RegExp]",
    v = "[object Set]",
    p = "[object String]",
    y = "[object Symbol]",
    m = "[object ArrayBuffer]",
    g = "[object DataView]",
    w = e ? e.prototype : void 0,
    x = w ? w.valueOf : void 0;
  function b(E, C, T, P, M, I, j) {
    switch (T) {
      case g:
        if (E.byteLength != C.byteLength || E.byteOffset != C.byteOffset) return !1;
        (E = E.buffer), (C = C.buffer);
      case m:
        return !(E.byteLength != C.byteLength || !I(new t(E), new t(C)));
      case u:
      case l:
      case d:
        return n(+E, +C);
      case c:
        return E.name == C.name && E.message == C.message;
      case h:
      case p:
        return E == C + "";
      case f:
        var q = i;
      case v:
        var S = P & s;
        if ((q || (q = o), E.size != C.size && !S)) return !1;
        var O = j.get(E);
        if (O) return O == C;
        (P |= a), j.set(E, C);
        var A = r(q(E), q(C), P, M, I, j);
        return j.delete(E), A;
      case y:
        if (x) return x.call(E) == x.call(C);
    }
    return !1;
  }
  return (Nh = b), Nh;
}
var Mh, Xb;
function Jz() {
  if (Xb) return Mh;
  Xb = 1;
  var e = yN(),
    t = 1,
    n = Object.prototype,
    r = n.hasOwnProperty;
  function i(o, s, a, u, l, c) {
    var f = a & t,
      d = e(o),
      h = d.length,
      v = e(s),
      p = v.length;
    if (h != p && !f) return !1;
    for (var y = h; y--; ) {
      var m = d[y];
      if (!(f ? m in s : r.call(s, m))) return !1;
    }
    var g = c.get(o),
      w = c.get(s);
    if (g && w) return g == s && w == o;
    var x = !0;
    c.set(o, s), c.set(s, o);
    for (var b = f; ++y < h; ) {
      m = d[y];
      var E = o[m],
        C = s[m];
      if (u) var T = f ? u(C, E, m, s, o, c) : u(E, C, m, o, s, c);
      if (!(T === void 0 ? E === C || l(E, C, a, u, c) : T)) {
        x = !1;
        break;
      }
      b || (b = m == "constructor");
    }
    if (x && !b) {
      var P = o.constructor,
        M = s.constructor;
      P != M &&
        "constructor" in o &&
        "constructor" in s &&
        !(typeof P == "function" && P instanceof P && typeof M == "function" && M instanceof M) &&
        (x = !1);
    }
    return c.delete(o), c.delete(s), x;
  }
  return (Mh = i), Mh;
}
var Ih, Zb;
function e5() {
  if (Zb) return Ih;
  Zb = 1;
  var e = nc(),
    t = AN(),
    n = Qz(),
    r = Jz(),
    i = Po(),
    o = Ie(),
    s = Ro(),
    a = ma(),
    u = 1,
    l = "[object Arguments]",
    c = "[object Array]",
    f = "[object Object]",
    d = Object.prototype,
    h = d.hasOwnProperty;
  function v(p, y, m, g, w, x) {
    var b = o(p),
      E = o(y),
      C = b ? c : i(p),
      T = E ? c : i(y);
    (C = C == l ? f : C), (T = T == l ? f : T);
    var P = C == f,
      M = T == f,
      I = C == T;
    if (I && s(p)) {
      if (!s(y)) return !1;
      (b = !0), (P = !1);
    }
    if (I && !P)
      return x || (x = new e()), b || a(p) ? t(p, y, m, g, w, x) : n(p, y, C, m, g, w, x);
    if (!(m & u)) {
      var j = P && h.call(p, "__wrapped__"),
        q = M && h.call(y, "__wrapped__");
      if (j || q) {
        var S = j ? p.value() : p,
          O = q ? y.value() : y;
        return x || (x = new e()), w(S, O, m, g, x);
      }
    }
    return I ? (x || (x = new e()), r(p, y, m, g, w, x)) : !1;
  }
  return (Ih = v), Ih;
}
var Dh, Qb;
function NN() {
  if (Qb) return Dh;
  Qb = 1;
  var e = e5(),
    t = En();
  function n(r, i, o, s, a) {
    return r === i
      ? !0
      : r == null || i == null || (!t(r) && !t(i))
        ? r !== r && i !== i
        : e(r, i, o, s, n, a);
  }
  return (Dh = n), Dh;
}
var Oh, Jb;
function t5() {
  if (Jb) return Oh;
  Jb = 1;
  var e = nc(),
    t = NN(),
    n = 1,
    r = 2;
  function i(o, s, a, u) {
    var l = a.length,
      c = l,
      f = !u;
    if (o == null) return !c;
    for (o = Object(o); l--; ) {
      var d = a[l];
      if (f && d[2] ? d[1] !== o[d[0]] : !(d[0] in o)) return !1;
    }
    for (; ++l < c; ) {
      d = a[l];
      var h = d[0],
        v = o[h],
        p = d[1];
      if (f && d[2]) {
        if (v === void 0 && !(h in o)) return !1;
      } else {
        var y = new e();
        if (u) var m = u(v, p, h, o, s, y);
        if (!(m === void 0 ? t(p, v, n | r, u, y) : m)) return !1;
      }
    }
    return !0;
  }
  return (Oh = i), Oh;
}
var Lh, eS;
function MN() {
  if (eS) return Lh;
  eS = 1;
  var e = $t();
  function t(n) {
    return n === n && !e(n);
  }
  return (Lh = t), Lh;
}
var Fh, tS;
function n5() {
  if (tS) return Fh;
  tS = 1;
  var e = MN(),
    t = Lr();
  function n(r) {
    for (var i = t(r), o = i.length; o--; ) {
      var s = i[o],
        a = r[s];
      i[o] = [s, a, e(a)];
    }
    return i;
  }
  return (Fh = n), Fh;
}
var jh, nS;
function IN() {
  if (nS) return jh;
  nS = 1;
  function e(t, n) {
    return function (r) {
      return r == null ? !1 : r[t] === n && (n !== void 0 || t in Object(r));
    };
  }
  return (jh = e), jh;
}
var Vh, rS;
function r5() {
  if (rS) return Vh;
  rS = 1;
  var e = t5(),
    t = n5(),
    n = IN();
  function r(i) {
    var o = t(i);
    return o.length == 1 && o[0][2]
      ? n(o[0][0], o[0][1])
      : function (s) {
          return s === i || e(s, i, o);
        };
  }
  return (Vh = r), Vh;
}
var qh, iS;
function Ao() {
  if (iS) return qh;
  iS = 1;
  var e = pi(),
    t = En(),
    n = "[object Symbol]";
  function r(i) {
    return typeof i == "symbol" || (t(i) && e(i) == n);
  }
  return (qh = r), qh;
}
var $h, oS;
function I0() {
  if (oS) return $h;
  oS = 1;
  var e = Ie(),
    t = Ao(),
    n = /\.|\[(?:[^[\]]*|(["'])(?:(?!\1)[^\\]|\\.)*?\1)\]/,
    r = /^\w*$/;
  function i(o, s) {
    if (e(o)) return !1;
    var a = typeof o;
    return a == "number" || a == "symbol" || a == "boolean" || o == null || t(o)
      ? !0
      : r.test(o) || !n.test(o) || (s != null && o in Object(s));
  }
  return ($h = i), $h;
}
var zh, sS;
function i5() {
  if (sS) return zh;
  sS = 1;
  var e = _0(),
    t = "Expected a function";
  function n(r, i) {
    if (typeof r != "function" || (i != null && typeof i != "function")) throw new TypeError(t);
    var o = function () {
      var s = arguments,
        a = i ? i.apply(this, s) : s[0],
        u = o.cache;
      if (u.has(a)) return u.get(a);
      var l = r.apply(this, s);
      return (o.cache = u.set(a, l) || u), l;
    };
    return (o.cache = new (n.Cache || e)()), o;
  }
  return (n.Cache = e), (zh = n), zh;
}
var Bh, aS;
function o5() {
  if (aS) return Bh;
  aS = 1;
  var e = i5(),
    t = 500;
  function n(r) {
    var i = e(r, function (s) {
        return o.size === t && o.clear(), s;
      }),
      o = i.cache;
    return i;
  }
  return (Bh = n), Bh;
}
var Uh, uS;
function s5() {
  if (uS) return Uh;
  uS = 1;
  var e = o5(),
    t =
      /[^.[\]]+|\[(?:(-?\d+(?:\.\d+)?)|(["'])((?:(?!\2)[^\\]|\\.)*?)\2)\]|(?=(?:\.|\[\])(?:\.|\[\]|$))/g,
    n = /\\(\\)?/g,
    r = e(function (i) {
      var o = [];
      return (
        i.charCodeAt(0) === 46 && o.push(""),
        i.replace(t, function (s, a, u, l) {
          o.push(u ? l.replace(n, "$1") : a || s);
        }),
        o
      );
    });
  return (Uh = r), Uh;
}
var Hh, lS;
function cc() {
  if (lS) return Hh;
  lS = 1;
  function e(t, n) {
    for (var r = -1, i = t == null ? 0 : t.length, o = Array(i); ++r < i; ) o[r] = n(t[r], r, t);
    return o;
  }
  return (Hh = e), Hh;
}
var Gh, cS;
function a5() {
  if (cS) return Gh;
  cS = 1;
  var e = ko(),
    t = cc(),
    n = Ie(),
    r = Ao(),
    i = e ? e.prototype : void 0,
    o = i ? i.toString : void 0;
  function s(a) {
    if (typeof a == "string") return a;
    if (n(a)) return t(a, s) + "";
    if (r(a)) return o ? o.call(a) : "";
    var u = a + "";
    return u == "0" && 1 / a == -1 / 0 ? "-0" : u;
  }
  return (Gh = s), Gh;
}
var Wh, fS;
function DN() {
  if (fS) return Wh;
  fS = 1;
  var e = a5();
  function t(n) {
    return n == null ? "" : e(n);
  }
  return (Wh = t), Wh;
}
var Kh, dS;
function fc() {
  if (dS) return Kh;
  dS = 1;
  var e = Ie(),
    t = I0(),
    n = s5(),
    r = DN();
  function i(o, s) {
    return e(o) ? o : t(o, s) ? [o] : n(r(o));
  }
  return (Kh = i), Kh;
}
var Yh, hS;
function ga() {
  if (hS) return Yh;
  hS = 1;
  var e = Ao();
  function t(n) {
    if (typeof n == "string" || e(n)) return n;
    var r = n + "";
    return r == "0" && 1 / n == -1 / 0 ? "-0" : r;
  }
  return (Yh = t), Yh;
}
var Xh, pS;
function dc() {
  if (pS) return Xh;
  pS = 1;
  var e = fc(),
    t = ga();
  function n(r, i) {
    i = e(i, r);
    for (var o = 0, s = i.length; r != null && o < s; ) r = r[t(i[o++])];
    return o && o == s ? r : void 0;
  }
  return (Xh = n), Xh;
}
var Zh, mS;
function u5() {
  if (mS) return Zh;
  mS = 1;
  var e = dc();
  function t(n, r, i) {
    var o = n == null ? void 0 : e(n, r);
    return o === void 0 ? i : o;
  }
  return (Zh = t), Zh;
}
var Qh, gS;
function l5() {
  if (gS) return Qh;
  gS = 1;
  function e(t, n) {
    return t != null && n in Object(t);
  }
  return (Qh = e), Qh;
}
var Jh, vS;
function ON() {
  if (vS) return Jh;
  vS = 1;
  var e = fc(),
    t = pa(),
    n = Ie(),
    r = oc(),
    i = S0(),
    o = ga();
  function s(a, u, l) {
    u = e(u, a);
    for (var c = -1, f = u.length, d = !1; ++c < f; ) {
      var h = o(u[c]);
      if (!(d = a != null && l(a, h))) break;
      a = a[h];
    }
    return d || ++c != f
      ? d
      : ((f = a == null ? 0 : a.length), !!f && i(f) && r(h, f) && (n(a) || t(a)));
  }
  return (Jh = s), Jh;
}
var ep, yS;
function LN() {
  if (yS) return ep;
  yS = 1;
  var e = l5(),
    t = ON();
  function n(r, i) {
    return r != null && t(r, i, e);
  }
  return (ep = n), ep;
}
var tp, wS;
function c5() {
  if (wS) return tp;
  wS = 1;
  var e = NN(),
    t = u5(),
    n = LN(),
    r = I0(),
    i = MN(),
    o = IN(),
    s = ga(),
    a = 1,
    u = 2;
  function l(c, f) {
    return r(c) && i(f)
      ? o(s(c), f)
      : function (d) {
          var h = t(d, c);
          return h === void 0 && h === f ? n(d, c) : e(f, h, a | u);
        };
  }
  return (tp = l), tp;
}
var np, xS;
function FN() {
  if (xS) return np;
  xS = 1;
  function e(t) {
    return function (n) {
      return n == null ? void 0 : n[t];
    };
  }
  return (np = e), np;
}
var rp, _S;
function f5() {
  if (_S) return rp;
  _S = 1;
  var e = dc();
  function t(n) {
    return function (r) {
      return e(r, n);
    };
  }
  return (rp = t), rp;
}
var ip, bS;
function d5() {
  if (bS) return ip;
  bS = 1;
  var e = FN(),
    t = f5(),
    n = I0(),
    r = ga();
  function i(o) {
    return n(o) ? e(r(o)) : t(o);
  }
  return (ip = i), ip;
}
var op, SS;
function er() {
  if (SS) return op;
  SS = 1;
  var e = r5(),
    t = c5(),
    n = vi(),
    r = Ie(),
    i = d5();
  function o(s) {
    return typeof s == "function"
      ? s
      : s == null
        ? n
        : typeof s == "object"
          ? r(s)
            ? t(s[0], s[1])
            : e(s)
          : i(s);
  }
  return (op = o), op;
}
var sp, ES;
function jN() {
  if (ES) return sp;
  ES = 1;
  var e = pN(),
    t = Wz(),
    n = er(),
    r = Ie();
  function i(o, s) {
    var a = r(o) ? e : t;
    return a(o, n(s, 3));
  }
  return (sp = i), sp;
}
var ap, CS;
function h5() {
  if (CS) return ap;
  CS = 1;
  var e = Object.prototype,
    t = e.hasOwnProperty;
  function n(r, i) {
    return r != null && t.call(r, i);
  }
  return (ap = n), ap;
}
var up, TS;
function VN() {
  if (TS) return up;
  TS = 1;
  var e = h5(),
    t = ON();
  function n(r, i) {
    return r != null && t(r, i, e);
  }
  return (up = n), up;
}
var lp, kS;
function p5() {
  if (kS) return lp;
  kS = 1;
  var e = C0(),
    t = Po(),
    n = pa(),
    r = Ie(),
    i = Jn(),
    o = Ro(),
    s = ac(),
    a = ma(),
    u = "[object Map]",
    l = "[object Set]",
    c = Object.prototype,
    f = c.hasOwnProperty;
  function d(h) {
    if (h == null) return !0;
    if (
      i(h) &&
      (r(h) || typeof h == "string" || typeof h.splice == "function" || o(h) || a(h) || n(h))
    )
      return !h.length;
    var v = t(h);
    if (v == u || v == l) return !h.size;
    if (s(h)) return !e(h).length;
    for (var p in h) if (f.call(h, p)) return !1;
    return !0;
  }
  return (lp = d), lp;
}
var cp, RS;
function qN() {
  if (RS) return cp;
  RS = 1;
  function e(t) {
    return t === void 0;
  }
  return (cp = e), cp;
}
var fp, PS;
function $N() {
  if (PS) return fp;
  PS = 1;
  var e = lc(),
    t = Jn();
  function n(r, i) {
    var o = -1,
      s = t(r) ? Array(r.length) : [];
    return (
      e(r, function (a, u, l) {
        s[++o] = i(a, u, l);
      }),
      s
    );
  }
  return (fp = n), fp;
}
var dp, AS;
function zN() {
  if (AS) return dp;
  AS = 1;
  var e = cc(),
    t = er(),
    n = $N(),
    r = Ie();
  function i(o, s) {
    var a = r(o) ? e : n;
    return a(o, t(s, 3));
  }
  return (dp = i), dp;
}
var hp, NS;
function m5() {
  if (NS) return hp;
  NS = 1;
  function e(t, n, r, i) {
    var o = -1,
      s = t == null ? 0 : t.length;
    for (i && s && (r = t[++o]); ++o < s; ) r = n(r, t[o], o, t);
    return r;
  }
  return (hp = e), hp;
}
var pp, MS;
function g5() {
  if (MS) return pp;
  MS = 1;
  function e(t, n, r, i, o) {
    return (
      o(t, function (s, a, u) {
        r = i ? ((i = !1), s) : n(r, s, a, u);
      }),
      r
    );
  }
  return (pp = e), pp;
}
var mp, IS;
function BN() {
  if (IS) return mp;
  IS = 1;
  var e = m5(),
    t = lc(),
    n = er(),
    r = g5(),
    i = Ie();
  function o(s, a, u) {
    var l = i(s) ? e : r,
      c = arguments.length < 3;
    return l(s, n(a, 4), u, c, t);
  }
  return (mp = o), mp;
}
var gp, DS;
function v5() {
  if (DS) return gp;
  DS = 1;
  var e = pi(),
    t = Ie(),
    n = En(),
    r = "[object String]";
  function i(o) {
    return typeof o == "string" || (!t(o) && n(o) && e(o) == r);
  }
  return (gp = i), gp;
}
var vp, OS;
function y5() {
  if (OS) return vp;
  OS = 1;
  var e = FN(),
    t = e("length");
  return (vp = t), vp;
}
var yp, LS;
function w5() {
  if (LS) return yp;
  LS = 1;
  var e = "\\ud800-\\udfff",
    t = "\\u0300-\\u036f",
    n = "\\ufe20-\\ufe2f",
    r = "\\u20d0-\\u20ff",
    i = t + n + r,
    o = "\\ufe0e\\ufe0f",
    s = "\\u200d",
    a = RegExp("[" + s + e + i + o + "]");
  function u(l) {
    return a.test(l);
  }
  return (yp = u), yp;
}
var wp, FS;
function x5() {
  if (FS) return wp;
  FS = 1;
  var e = "\\ud800-\\udfff",
    t = "\\u0300-\\u036f",
    n = "\\ufe20-\\ufe2f",
    r = "\\u20d0-\\u20ff",
    i = t + n + r,
    o = "\\ufe0e\\ufe0f",
    s = "[" + e + "]",
    a = "[" + i + "]",
    u = "\\ud83c[\\udffb-\\udfff]",
    l = "(?:" + a + "|" + u + ")",
    c = "[^" + e + "]",
    f = "(?:\\ud83c[\\udde6-\\uddff]){2}",
    d = "[\\ud800-\\udbff][\\udc00-\\udfff]",
    h = "\\u200d",
    v = l + "?",
    p = "[" + o + "]?",
    y = "(?:" + h + "(?:" + [c, f, d].join("|") + ")" + p + v + ")*",
    m = p + v + y,
    g = "(?:" + [c + a + "?", a, f, d, s].join("|") + ")",
    w = RegExp(u + "(?=" + u + ")|" + g + m, "g");
  function x(b) {
    for (var E = (w.lastIndex = 0); w.test(b); ) ++E;
    return E;
  }
  return (wp = x), wp;
}
var xp, jS;
function _5() {
  if (jS) return xp;
  jS = 1;
  var e = y5(),
    t = w5(),
    n = x5();
  function r(i) {
    return t(i) ? n(i) : e(i);
  }
  return (xp = r), xp;
}
var _p, VS;
function b5() {
  if (VS) return _p;
  VS = 1;
  var e = C0(),
    t = Po(),
    n = Jn(),
    r = v5(),
    i = _5(),
    o = "[object Map]",
    s = "[object Set]";
  function a(u) {
    if (u == null) return 0;
    if (n(u)) return r(u) ? i(u) : u.length;
    var l = t(u);
    return l == o || l == s ? u.size : e(u).length;
  }
  return (_p = a), _p;
}
var bp, qS;
function S5() {
  if (qS) return bp;
  qS = 1;
  var e = b0(),
    t = bN(),
    n = N0(),
    r = er(),
    i = uc(),
    o = Ie(),
    s = Ro(),
    a = da(),
    u = $t(),
    l = ma();
  function c(f, d, h) {
    var v = o(f),
      p = v || s(f) || l(f);
    if (((d = r(d, 4)), h == null)) {
      var y = f && f.constructor;
      p ? (h = v ? new y() : []) : u(f) ? (h = a(y) ? t(i(f)) : {}) : (h = {});
    }
    return (
      (p ? e : n)(f, function (m, g, w) {
        return d(h, m, g, w);
      }),
      h
    );
  }
  return (bp = c), bp;
}
var Sp, $S;
function E5() {
  if ($S) return Sp;
  $S = 1;
  var e = ko(),
    t = pa(),
    n = Ie(),
    r = e ? e.isConcatSpreadable : void 0;
  function i(o) {
    return n(o) || t(o) || !!(r && o && o[r]);
  }
  return (Sp = i), Sp;
}
var Ep, zS;
function D0() {
  if (zS) return Ep;
  zS = 1;
  var e = k0(),
    t = E5();
  function n(r, i, o, s, a) {
    var u = -1,
      l = r.length;
    for (o || (o = t), a || (a = []); ++u < l; ) {
      var c = r[u];
      i > 0 && o(c) ? (i > 1 ? n(c, i - 1, o, s, a) : e(a, c)) : s || (a[a.length] = c);
    }
    return a;
  }
  return (Ep = n), Ep;
}
var Cp, BS;
function C5() {
  if (BS) return Cp;
  BS = 1;
  function e(t, n, r) {
    switch (r.length) {
      case 0:
        return t.call(n);
      case 1:
        return t.call(n, r[0]);
      case 2:
        return t.call(n, r[0], r[1]);
      case 3:
        return t.call(n, r[0], r[1], r[2]);
    }
    return t.apply(n, r);
  }
  return (Cp = e), Cp;
}
var Tp, US;
function UN() {
  if (US) return Tp;
  US = 1;
  var e = C5(),
    t = Math.max;
  function n(r, i, o) {
    return (
      (i = t(i === void 0 ? r.length - 1 : i, 0)),
      function () {
        for (var s = arguments, a = -1, u = t(s.length - i, 0), l = Array(u); ++a < u; )
          l[a] = s[i + a];
        a = -1;
        for (var c = Array(i + 1); ++a < i; ) c[a] = s[a];
        return (c[i] = o(l)), e(r, this, c);
      }
    );
  }
  return (Tp = n), Tp;
}
var kp, HS;
function T5() {
  if (HS) return kp;
  HS = 1;
  var e = P0(),
    t = lN(),
    n = vi(),
    r = t
      ? function (i, o) {
          return t(i, "toString", { configurable: !0, enumerable: !1, value: e(o), writable: !0 });
        }
      : n;
  return (kp = r), kp;
}
var Rp, GS;
function k5() {
  if (GS) return Rp;
  GS = 1;
  var e = 800,
    t = 16,
    n = Date.now;
  function r(i) {
    var o = 0,
      s = 0;
    return function () {
      var a = n(),
        u = t - (a - s);
      if (((s = a), u > 0)) {
        if (++o >= e) return arguments[0];
      } else o = 0;
      return i.apply(void 0, arguments);
    };
  }
  return (Rp = r), Rp;
}
var Pp, WS;
function HN() {
  if (WS) return Pp;
  WS = 1;
  var e = T5(),
    t = k5(),
    n = t(e);
  return (Pp = n), Pp;
}
var Ap, KS;
function hc() {
  if (KS) return Ap;
  KS = 1;
  var e = vi(),
    t = UN(),
    n = HN();
  function r(i, o) {
    return n(t(i, o, e), i + "");
  }
  return (Ap = r), Ap;
}
var Np, YS;
function GN() {
  if (YS) return Np;
  YS = 1;
  function e(t, n, r, i) {
    for (var o = t.length, s = r + (i ? 1 : -1); i ? s-- : ++s < o; ) if (n(t[s], s, t)) return s;
    return -1;
  }
  return (Np = e), Np;
}
var Mp, XS;
function R5() {
  if (XS) return Mp;
  XS = 1;
  function e(t) {
    return t !== t;
  }
  return (Mp = e), Mp;
}
var Ip, ZS;
function P5() {
  if (ZS) return Ip;
  ZS = 1;
  function e(t, n, r) {
    for (var i = r - 1, o = t.length; ++i < o; ) if (t[i] === n) return i;
    return -1;
  }
  return (Ip = e), Ip;
}
var Dp, QS;
function A5() {
  if (QS) return Dp;
  QS = 1;
  var e = GN(),
    t = R5(),
    n = P5();
  function r(i, o, s) {
    return o === o ? n(i, o, s) : e(i, t, s);
  }
  return (Dp = r), Dp;
}
var Op, JS;
function N5() {
  if (JS) return Op;
  JS = 1;
  var e = A5();
  function t(n, r) {
    var i = n == null ? 0 : n.length;
    return !!i && e(n, r, 0) > -1;
  }
  return (Op = t), Op;
}
var Lp, eE;
function M5() {
  if (eE) return Lp;
  eE = 1;
  function e(t, n, r) {
    for (var i = -1, o = t == null ? 0 : t.length; ++i < o; ) if (r(n, t[i])) return !0;
    return !1;
  }
  return (Lp = e), Lp;
}
var Fp, tE;
function I5() {
  if (tE) return Fp;
  tE = 1;
  function e() {}
  return (Fp = e), Fp;
}
var jp, nE;
function D5() {
  if (nE) return jp;
  nE = 1;
  var e = wN(),
    t = I5(),
    n = M0(),
    r = 1 / 0,
    i =
      e && 1 / n(new e([, -0]))[1] == r
        ? function (o) {
            return new e(o);
          }
        : t;
  return (jp = i), jp;
}
var Vp, rE;
function O5() {
  if (rE) return Vp;
  rE = 1;
  var e = RN(),
    t = N5(),
    n = M5(),
    r = PN(),
    i = D5(),
    o = M0(),
    s = 200;
  function a(u, l, c) {
    var f = -1,
      d = t,
      h = u.length,
      v = !0,
      p = [],
      y = p;
    if (c) (v = !1), (d = n);
    else if (h >= s) {
      var m = l ? null : i(u);
      if (m) return o(m);
      (v = !1), (d = r), (y = new e());
    } else y = l ? [] : p;
    e: for (; ++f < h; ) {
      var g = u[f],
        w = l ? l(g) : g;
      if (((g = c || g !== 0 ? g : 0), v && w === w)) {
        for (var x = y.length; x--; ) if (y[x] === w) continue e;
        l && y.push(w), p.push(g);
      } else d(y, w, c) || (y !== p && y.push(w), p.push(g));
    }
    return p;
  }
  return (Vp = a), Vp;
}
var qp, iE;
function WN() {
  if (iE) return qp;
  iE = 1;
  var e = Jn(),
    t = En();
  function n(r) {
    return t(r) && e(r);
  }
  return (qp = n), qp;
}
var $p, oE;
function L5() {
  if (oE) return $p;
  oE = 1;
  var e = D0(),
    t = hc(),
    n = O5(),
    r = WN(),
    i = t(function (o) {
      return n(e(o, 1, r, !0));
    });
  return ($p = i), $p;
}
var zp, sE;
function F5() {
  if (sE) return zp;
  sE = 1;
  var e = cc();
  function t(n, r) {
    return e(r, function (i) {
      return n[i];
    });
  }
  return (zp = t), zp;
}
var Bp, aE;
function KN() {
  if (aE) return Bp;
  aE = 1;
  var e = F5(),
    t = Lr();
  function n(r) {
    return r == null ? [] : e(r, t(r));
  }
  return (Bp = n), Bp;
}
var Up, uE;
function zt() {
  if (uE) return Up;
  uE = 1;
  var e;
  if (typeof w0 == "function")
    try {
      e = {
        clone: Uz(),
        constant: P0(),
        each: kN(),
        filter: jN(),
        has: VN(),
        isArray: Ie(),
        isEmpty: p5(),
        isFunction: da(),
        isUndefined: qN(),
        keys: Lr(),
        map: zN(),
        reduce: BN(),
        size: b5(),
        transform: S5(),
        union: L5(),
        values: KN(),
      };
    } catch {}
  return e || (e = window._), (Up = e), Up;
}
var Hp, lE;
function O0() {
  if (lE) return Hp;
  lE = 1;
  var e = zt();
  Hp = i;
  var t = "\0",
    n = "\0",
    r = "";
  function i(c) {
    (this._isDirected = e.has(c, "directed") ? c.directed : !0),
      (this._isMultigraph = e.has(c, "multigraph") ? c.multigraph : !1),
      (this._isCompound = e.has(c, "compound") ? c.compound : !1),
      (this._label = void 0),
      (this._defaultNodeLabelFn = e.constant(void 0)),
      (this._defaultEdgeLabelFn = e.constant(void 0)),
      (this._nodes = {}),
      this._isCompound && ((this._parent = {}), (this._children = {}), (this._children[n] = {})),
      (this._in = {}),
      (this._preds = {}),
      (this._out = {}),
      (this._sucs = {}),
      (this._edgeObjs = {}),
      (this._edgeLabels = {});
  }
  (i.prototype._nodeCount = 0),
    (i.prototype._edgeCount = 0),
    (i.prototype.isDirected = function () {
      return this._isDirected;
    }),
    (i.prototype.isMultigraph = function () {
      return this._isMultigraph;
    }),
    (i.prototype.isCompound = function () {
      return this._isCompound;
    }),
    (i.prototype.setGraph = function (c) {
      return (this._label = c), this;
    }),
    (i.prototype.graph = function () {
      return this._label;
    }),
    (i.prototype.setDefaultNodeLabel = function (c) {
      return e.isFunction(c) || (c = e.constant(c)), (this._defaultNodeLabelFn = c), this;
    }),
    (i.prototype.nodeCount = function () {
      return this._nodeCount;
    }),
    (i.prototype.nodes = function () {
      return e.keys(this._nodes);
    }),
    (i.prototype.sources = function () {
      var c = this;
      return e.filter(this.nodes(), function (f) {
        return e.isEmpty(c._in[f]);
      });
    }),
    (i.prototype.sinks = function () {
      var c = this;
      return e.filter(this.nodes(), function (f) {
        return e.isEmpty(c._out[f]);
      });
    }),
    (i.prototype.setNodes = function (c, f) {
      var d = arguments,
        h = this;
      return (
        e.each(c, function (v) {
          d.length > 1 ? h.setNode(v, f) : h.setNode(v);
        }),
        this
      );
    }),
    (i.prototype.setNode = function (c, f) {
      return e.has(this._nodes, c)
        ? (arguments.length > 1 && (this._nodes[c] = f), this)
        : ((this._nodes[c] = arguments.length > 1 ? f : this._defaultNodeLabelFn(c)),
          this._isCompound &&
            ((this._parent[c] = n), (this._children[c] = {}), (this._children[n][c] = !0)),
          (this._in[c] = {}),
          (this._preds[c] = {}),
          (this._out[c] = {}),
          (this._sucs[c] = {}),
          ++this._nodeCount,
          this);
    }),
    (i.prototype.node = function (c) {
      return this._nodes[c];
    }),
    (i.prototype.hasNode = function (c) {
      return e.has(this._nodes, c);
    }),
    (i.prototype.removeNode = function (c) {
      var f = this;
      if (e.has(this._nodes, c)) {
        var d = function (h) {
          f.removeEdge(f._edgeObjs[h]);
        };
        delete this._nodes[c],
          this._isCompound &&
            (this._removeFromParentsChildList(c),
            delete this._parent[c],
            e.each(this.children(c), function (h) {
              f.setParent(h);
            }),
            delete this._children[c]),
          e.each(e.keys(this._in[c]), d),
          delete this._in[c],
          delete this._preds[c],
          e.each(e.keys(this._out[c]), d),
          delete this._out[c],
          delete this._sucs[c],
          --this._nodeCount;
      }
      return this;
    }),
    (i.prototype.setParent = function (c, f) {
      if (!this._isCompound) throw new Error("Cannot set parent in a non-compound graph");
      if (e.isUndefined(f)) f = n;
      else {
        f += "";
        for (var d = f; !e.isUndefined(d); d = this.parent(d))
          if (d === c)
            throw new Error("Setting " + f + " as parent of " + c + " would create a cycle");
        this.setNode(f);
      }
      return (
        this.setNode(c),
        this._removeFromParentsChildList(c),
        (this._parent[c] = f),
        (this._children[f][c] = !0),
        this
      );
    }),
    (i.prototype._removeFromParentsChildList = function (c) {
      delete this._children[this._parent[c]][c];
    }),
    (i.prototype.parent = function (c) {
      if (this._isCompound) {
        var f = this._parent[c];
        if (f !== n) return f;
      }
    }),
    (i.prototype.children = function (c) {
      if ((e.isUndefined(c) && (c = n), this._isCompound)) {
        var f = this._children[c];
        if (f) return e.keys(f);
      } else {
        if (c === n) return this.nodes();
        if (this.hasNode(c)) return [];
      }
    }),
    (i.prototype.predecessors = function (c) {
      var f = this._preds[c];
      if (f) return e.keys(f);
    }),
    (i.prototype.successors = function (c) {
      var f = this._sucs[c];
      if (f) return e.keys(f);
    }),
    (i.prototype.neighbors = function (c) {
      var f = this.predecessors(c);
      if (f) return e.union(f, this.successors(c));
    }),
    (i.prototype.isLeaf = function (c) {
      var f;
      return this.isDirected() ? (f = this.successors(c)) : (f = this.neighbors(c)), f.length === 0;
    }),
    (i.prototype.filterNodes = function (c) {
      var f = new this.constructor({
        directed: this._isDirected,
        multigraph: this._isMultigraph,
        compound: this._isCompound,
      });
      f.setGraph(this.graph());
      var d = this;
      e.each(this._nodes, function (p, y) {
        c(y) && f.setNode(y, p);
      }),
        e.each(this._edgeObjs, function (p) {
          f.hasNode(p.v) && f.hasNode(p.w) && f.setEdge(p, d.edge(p));
        });
      var h = {};
      function v(p) {
        var y = d.parent(p);
        return y === void 0 || f.hasNode(y) ? ((h[p] = y), y) : y in h ? h[y] : v(y);
      }
      return (
        this._isCompound &&
          e.each(f.nodes(), function (p) {
            f.setParent(p, v(p));
          }),
        f
      );
    }),
    (i.prototype.setDefaultEdgeLabel = function (c) {
      return e.isFunction(c) || (c = e.constant(c)), (this._defaultEdgeLabelFn = c), this;
    }),
    (i.prototype.edgeCount = function () {
      return this._edgeCount;
    }),
    (i.prototype.edges = function () {
      return e.values(this._edgeObjs);
    }),
    (i.prototype.setPath = function (c, f) {
      var d = this,
        h = arguments;
      return (
        e.reduce(c, function (v, p) {
          return h.length > 1 ? d.setEdge(v, p, f) : d.setEdge(v, p), p;
        }),
        this
      );
    }),
    (i.prototype.setEdge = function () {
      var c,
        f,
        d,
        h,
        v = !1,
        p = arguments[0];
      typeof p == "object" && p !== null && "v" in p
        ? ((c = p.v),
          (f = p.w),
          (d = p.name),
          arguments.length === 2 && ((h = arguments[1]), (v = !0)))
        : ((c = p),
          (f = arguments[1]),
          (d = arguments[3]),
          arguments.length > 2 && ((h = arguments[2]), (v = !0))),
        (c = "" + c),
        (f = "" + f),
        e.isUndefined(d) || (d = "" + d);
      var y = a(this._isDirected, c, f, d);
      if (e.has(this._edgeLabels, y)) return v && (this._edgeLabels[y] = h), this;
      if (!e.isUndefined(d) && !this._isMultigraph)
        throw new Error("Cannot set a named edge when isMultigraph = false");
      this.setNode(c),
        this.setNode(f),
        (this._edgeLabels[y] = v ? h : this._defaultEdgeLabelFn(c, f, d));
      var m = u(this._isDirected, c, f, d);
      return (
        (c = m.v),
        (f = m.w),
        Object.freeze(m),
        (this._edgeObjs[y] = m),
        o(this._preds[f], c),
        o(this._sucs[c], f),
        (this._in[f][y] = m),
        (this._out[c][y] = m),
        this._edgeCount++,
        this
      );
    }),
    (i.prototype.edge = function (c, f, d) {
      var h =
        arguments.length === 1 ? l(this._isDirected, arguments[0]) : a(this._isDirected, c, f, d);
      return this._edgeLabels[h];
    }),
    (i.prototype.hasEdge = function (c, f, d) {
      var h =
        arguments.length === 1 ? l(this._isDirected, arguments[0]) : a(this._isDirected, c, f, d);
      return e.has(this._edgeLabels, h);
    }),
    (i.prototype.removeEdge = function (c, f, d) {
      var h =
          arguments.length === 1 ? l(this._isDirected, arguments[0]) : a(this._isDirected, c, f, d),
        v = this._edgeObjs[h];
      return (
        v &&
          ((c = v.v),
          (f = v.w),
          delete this._edgeLabels[h],
          delete this._edgeObjs[h],
          s(this._preds[f], c),
          s(this._sucs[c], f),
          delete this._in[f][h],
          delete this._out[c][h],
          this._edgeCount--),
        this
      );
    }),
    (i.prototype.inEdges = function (c, f) {
      var d = this._in[c];
      if (d) {
        var h = e.values(d);
        return f
          ? e.filter(h, function (v) {
              return v.v === f;
            })
          : h;
      }
    }),
    (i.prototype.outEdges = function (c, f) {
      var d = this._out[c];
      if (d) {
        var h = e.values(d);
        return f
          ? e.filter(h, function (v) {
              return v.w === f;
            })
          : h;
      }
    }),
    (i.prototype.nodeEdges = function (c, f) {
      var d = this.inEdges(c, f);
      if (d) return d.concat(this.outEdges(c, f));
    });
  function o(c, f) {
    c[f] ? c[f]++ : (c[f] = 1);
  }
  function s(c, f) {
    --c[f] || delete c[f];
  }
  function a(c, f, d, h) {
    var v = "" + f,
      p = "" + d;
    if (!c && v > p) {
      var y = v;
      (v = p), (p = y);
    }
    return v + r + p + r + (e.isUndefined(h) ? t : h);
  }
  function u(c, f, d, h) {
    var v = "" + f,
      p = "" + d;
    if (!c && v > p) {
      var y = v;
      (v = p), (p = y);
    }
    var m = { v, w: p };
    return h && (m.name = h), m;
  }
  function l(c, f) {
    return a(c, f.v, f.w, f.name);
  }
  return Hp;
}
var Gp, cE;
function j5() {
  return cE || ((cE = 1), (Gp = "2.1.8")), Gp;
}
var Wp, fE;
function V5() {
  return fE || ((fE = 1), (Wp = { Graph: O0(), version: j5() })), Wp;
}
var Kp, dE;
function q5() {
  if (dE) return Kp;
  dE = 1;
  var e = zt(),
    t = O0();
  Kp = { write: n, read: o };
  function n(s) {
    var a = {
      options: { directed: s.isDirected(), multigraph: s.isMultigraph(), compound: s.isCompound() },
      nodes: r(s),
      edges: i(s),
    };
    return e.isUndefined(s.graph()) || (a.value = e.clone(s.graph())), a;
  }
  function r(s) {
    return e.map(s.nodes(), function (a) {
      var u = s.node(a),
        l = s.parent(a),
        c = { v: a };
      return e.isUndefined(u) || (c.value = u), e.isUndefined(l) || (c.parent = l), c;
    });
  }
  function i(s) {
    return e.map(s.edges(), function (a) {
      var u = s.edge(a),
        l = { v: a.v, w: a.w };
      return e.isUndefined(a.name) || (l.name = a.name), e.isUndefined(u) || (l.value = u), l;
    });
  }
  function o(s) {
    var a = new t(s.options).setGraph(s.value);
    return (
      e.each(s.nodes, function (u) {
        a.setNode(u.v, u.value), u.parent && a.setParent(u.v, u.parent);
      }),
      e.each(s.edges, function (u) {
        a.setEdge({ v: u.v, w: u.w, name: u.name }, u.value);
      }),
      a
    );
  }
  return Kp;
}
var Yp, hE;
function $5() {
  if (hE) return Yp;
  hE = 1;
  var e = zt();
  Yp = t;
  function t(n) {
    var r = {},
      i = [],
      o;
    function s(a) {
      e.has(r, a) ||
        ((r[a] = !0), o.push(a), e.each(n.successors(a), s), e.each(n.predecessors(a), s));
    }
    return (
      e.each(n.nodes(), function (a) {
        (o = []), s(a), o.length && i.push(o);
      }),
      i
    );
  }
  return Yp;
}
var Xp, pE;
function YN() {
  if (pE) return Xp;
  pE = 1;
  var e = zt();
  Xp = t;
  function t() {
    (this._arr = []), (this._keyIndices = {});
  }
  return (
    (t.prototype.size = function () {
      return this._arr.length;
    }),
    (t.prototype.keys = function () {
      return this._arr.map(function (n) {
        return n.key;
      });
    }),
    (t.prototype.has = function (n) {
      return e.has(this._keyIndices, n);
    }),
    (t.prototype.priority = function (n) {
      var r = this._keyIndices[n];
      if (r !== void 0) return this._arr[r].priority;
    }),
    (t.prototype.min = function () {
      if (this.size() === 0) throw new Error("Queue underflow");
      return this._arr[0].key;
    }),
    (t.prototype.add = function (n, r) {
      var i = this._keyIndices;
      if (((n = String(n)), !e.has(i, n))) {
        var o = this._arr,
          s = o.length;
        return (i[n] = s), o.push({ key: n, priority: r }), this._decrease(s), !0;
      }
      return !1;
    }),
    (t.prototype.removeMin = function () {
      this._swap(0, this._arr.length - 1);
      var n = this._arr.pop();
      return delete this._keyIndices[n.key], this._heapify(0), n.key;
    }),
    (t.prototype.decrease = function (n, r) {
      var i = this._keyIndices[n];
      if (r > this._arr[i].priority)
        throw new Error(
          "New priority is greater than current priority. Key: " +
            n +
            " Old: " +
            this._arr[i].priority +
            " New: " +
            r,
        );
      (this._arr[i].priority = r), this._decrease(i);
    }),
    (t.prototype._heapify = function (n) {
      var r = this._arr,
        i = 2 * n,
        o = i + 1,
        s = n;
      i < r.length &&
        ((s = r[i].priority < r[s].priority ? i : s),
        o < r.length && (s = r[o].priority < r[s].priority ? o : s),
        s !== n && (this._swap(n, s), this._heapify(s)));
    }),
    (t.prototype._decrease = function (n) {
      for (
        var r = this._arr, i = r[n].priority, o;
        n !== 0 && ((o = n >> 1), !(r[o].priority < i));

      )
        this._swap(n, o), (n = o);
    }),
    (t.prototype._swap = function (n, r) {
      var i = this._arr,
        o = this._keyIndices,
        s = i[n],
        a = i[r];
      (i[n] = a), (i[r] = s), (o[a.key] = n), (o[s.key] = r);
    }),
    Xp
  );
}
var Zp, mE;
function XN() {
  if (mE) return Zp;
  mE = 1;
  var e = zt(),
    t = YN();
  Zp = r;
  var n = e.constant(1);
  function r(o, s, a, u) {
    return i(
      o,
      String(s),
      a || n,
      u ||
        function (l) {
          return o.outEdges(l);
        },
    );
  }
  function i(o, s, a, u) {
    var l = {},
      c = new t(),
      f,
      d,
      h = function (v) {
        var p = v.v !== f ? v.v : v.w,
          y = l[p],
          m = a(v),
          g = d.distance + m;
        if (m < 0)
          throw new Error(
            "dijkstra does not allow negative edge weights. Bad edge: " + v + " Weight: " + m,
          );
        g < y.distance && ((y.distance = g), (y.predecessor = f), c.decrease(p, g));
      };
    for (
      o.nodes().forEach(function (v) {
        var p = v === s ? 0 : Number.POSITIVE_INFINITY;
        (l[v] = { distance: p }), c.add(v, p);
      });
      c.size() > 0 && ((f = c.removeMin()), (d = l[f]), d.distance !== Number.POSITIVE_INFINITY);

    )
      u(f).forEach(h);
    return l;
  }
  return Zp;
}
var Qp, gE;
function z5() {
  if (gE) return Qp;
  gE = 1;
  var e = XN(),
    t = zt();
  Qp = n;
  function n(r, i, o) {
    return t.transform(
      r.nodes(),
      function (s, a) {
        s[a] = e(r, a, i, o);
      },
      {},
    );
  }
  return Qp;
}
var Jp, vE;
function ZN() {
  if (vE) return Jp;
  vE = 1;
  var e = zt();
  Jp = t;
  function t(n) {
    var r = 0,
      i = [],
      o = {},
      s = [];
    function a(u) {
      var l = (o[u] = { onStack: !0, lowlink: r, index: r++ });
      if (
        (i.push(u),
        n.successors(u).forEach(function (d) {
          e.has(o, d)
            ? o[d].onStack && (l.lowlink = Math.min(l.lowlink, o[d].index))
            : (a(d), (l.lowlink = Math.min(l.lowlink, o[d].lowlink)));
        }),
        l.lowlink === l.index)
      ) {
        var c = [],
          f;
        do (f = i.pop()), (o[f].onStack = !1), c.push(f);
        while (u !== f);
        s.push(c);
      }
    }
    return (
      n.nodes().forEach(function (u) {
        e.has(o, u) || a(u);
      }),
      s
    );
  }
  return Jp;
}
var em, yE;
function B5() {
  if (yE) return em;
  yE = 1;
  var e = zt(),
    t = ZN();
  em = n;
  function n(r) {
    return e.filter(t(r), function (i) {
      return i.length > 1 || (i.length === 1 && r.hasEdge(i[0], i[0]));
    });
  }
  return em;
}
var tm, wE;
function U5() {
  if (wE) return tm;
  wE = 1;
  var e = zt();
  tm = n;
  var t = e.constant(1);
  function n(i, o, s) {
    return r(
      i,
      o || t,
      s ||
        function (a) {
          return i.outEdges(a);
        },
    );
  }
  function r(i, o, s) {
    var a = {},
      u = i.nodes();
    return (
      u.forEach(function (l) {
        (a[l] = {}),
          (a[l][l] = { distance: 0 }),
          u.forEach(function (c) {
            l !== c && (a[l][c] = { distance: Number.POSITIVE_INFINITY });
          }),
          s(l).forEach(function (c) {
            var f = c.v === l ? c.w : c.v,
              d = o(c);
            a[l][f] = { distance: d, predecessor: l };
          });
      }),
      u.forEach(function (l) {
        var c = a[l];
        u.forEach(function (f) {
          var d = a[f];
          u.forEach(function (h) {
            var v = d[l],
              p = c[h],
              y = d[h],
              m = v.distance + p.distance;
            m < y.distance && ((y.distance = m), (y.predecessor = p.predecessor));
          });
        });
      }),
      a
    );
  }
  return tm;
}
var nm, xE;
function QN() {
  if (xE) return nm;
  xE = 1;
  var e = zt();
  (nm = t), (t.CycleException = n);
  function t(r) {
    var i = {},
      o = {},
      s = [];
    function a(u) {
      if (e.has(o, u)) throw new n();
      e.has(i, u) ||
        ((o[u] = !0), (i[u] = !0), e.each(r.predecessors(u), a), delete o[u], s.push(u));
    }
    if ((e.each(r.sinks(), a), e.size(i) !== r.nodeCount())) throw new n();
    return s;
  }
  function n() {}
  return (n.prototype = new Error()), nm;
}
var rm, _E;
function H5() {
  if (_E) return rm;
  _E = 1;
  var e = QN();
  rm = t;
  function t(n) {
    try {
      e(n);
    } catch (r) {
      if (r instanceof e.CycleException) return !1;
      throw r;
    }
    return !0;
  }
  return rm;
}
var im, bE;
function JN() {
  if (bE) return im;
  bE = 1;
  var e = zt();
  im = t;
  function t(r, i, o) {
    e.isArray(i) || (i = [i]);
    var s = (r.isDirected() ? r.successors : r.neighbors).bind(r),
      a = [],
      u = {};
    return (
      e.each(i, function (l) {
        if (!r.hasNode(l)) throw new Error("Graph does not have node: " + l);
        n(r, l, o === "post", u, s, a);
      }),
      a
    );
  }
  function n(r, i, o, s, a, u) {
    e.has(s, i) ||
      ((s[i] = !0),
      o || u.push(i),
      e.each(a(i), function (l) {
        n(r, l, o, s, a, u);
      }),
      o && u.push(i));
  }
  return im;
}
var om, SE;
function G5() {
  if (SE) return om;
  SE = 1;
  var e = JN();
  om = t;
  function t(n, r) {
    return e(n, r, "post");
  }
  return om;
}
var sm, EE;
function W5() {
  if (EE) return sm;
  EE = 1;
  var e = JN();
  sm = t;
  function t(n, r) {
    return e(n, r, "pre");
  }
  return sm;
}
var am, CE;
function K5() {
  if (CE) return am;
  CE = 1;
  var e = zt(),
    t = O0(),
    n = YN();
  am = r;
  function r(i, o) {
    var s = new t(),
      a = {},
      u = new n(),
      l;
    function c(d) {
      var h = d.v === l ? d.w : d.v,
        v = u.priority(h);
      if (v !== void 0) {
        var p = o(d);
        p < v && ((a[h] = l), u.decrease(h, p));
      }
    }
    if (i.nodeCount() === 0) return s;
    e.each(i.nodes(), function (d) {
      u.add(d, Number.POSITIVE_INFINITY), s.setNode(d);
    }),
      u.decrease(i.nodes()[0], 0);
    for (var f = !1; u.size() > 0; ) {
      if (((l = u.removeMin()), e.has(a, l))) s.setEdge(l, a[l]);
      else {
        if (f) throw new Error("Input graph is not connected: " + i);
        f = !0;
      }
      i.nodeEdges(l).forEach(c);
    }
    return s;
  }
  return am;
}
var um, TE;
function Y5() {
  return (
    TE ||
      ((TE = 1),
      (um = {
        components: $5(),
        dijkstra: XN(),
        dijkstraAll: z5(),
        findCycles: B5(),
        floydWarshall: U5(),
        isAcyclic: H5(),
        postorder: G5(),
        preorder: W5(),
        prim: K5(),
        tarjan: ZN(),
        topsort: QN(),
      })),
    um
  );
}
var lm, kE;
function X5() {
  if (kE) return lm;
  kE = 1;
  var e = V5();
  return (lm = { Graph: e.Graph, json: q5(), alg: Y5(), version: e.version }), lm;
}
var hl;
if (typeof w0 == "function")
  try {
    hl = X5();
  } catch {}
hl || (hl = window.graphlib);
var sn = hl,
  cm,
  RE;
function Z5() {
  if (RE) return cm;
  RE = 1;
  var e = EN(),
    t = 1,
    n = 4;
  function r(i) {
    return e(i, t | n);
  }
  return (cm = r), cm;
}
var fm, PE;
function pc() {
  if (PE) return fm;
  PE = 1;
  var e = To(),
    t = Jn(),
    n = oc(),
    r = $t();
  function i(o, s, a) {
    if (!r(a)) return !1;
    var u = typeof s;
    return (u == "number" ? t(a) && n(s, a.length) : u == "string" && s in a) ? e(a[s], o) : !1;
  }
  return (fm = i), fm;
}
var dm, AE;
function Q5() {
  if (AE) return dm;
  AE = 1;
  var e = hc(),
    t = To(),
    n = pc(),
    r = gi(),
    i = Object.prototype,
    o = i.hasOwnProperty,
    s = e(function (a, u) {
      a = Object(a);
      var l = -1,
        c = u.length,
        f = c > 2 ? u[2] : void 0;
      for (f && n(u[0], u[1], f) && (c = 1); ++l < c; )
        for (var d = u[l], h = r(d), v = -1, p = h.length; ++v < p; ) {
          var y = h[v],
            m = a[y];
          (m === void 0 || (t(m, i[y]) && !o.call(a, y))) && (a[y] = d[y]);
        }
      return a;
    });
  return (dm = s), dm;
}
var hm, NE;
function J5() {
  if (NE) return hm;
  NE = 1;
  var e = er(),
    t = Jn(),
    n = Lr();
  function r(i) {
    return function (o, s, a) {
      var u = Object(o);
      if (!t(o)) {
        var l = e(s, 3);
        (o = n(o)),
          (s = function (f) {
            return l(u[f], f, u);
          });
      }
      var c = i(o, s, a);
      return c > -1 ? u[l ? o[c] : c] : void 0;
    };
  }
  return (hm = r), hm;
}
var pm, ME;
function eB() {
  if (ME) return pm;
  ME = 1;
  var e = /\s/;
  function t(n) {
    for (var r = n.length; r-- && e.test(n.charAt(r)); );
    return r;
  }
  return (pm = t), pm;
}
var mm, IE;
function tB() {
  if (IE) return mm;
  IE = 1;
  var e = eB(),
    t = /^\s+/;
  function n(r) {
    return r && r.slice(0, e(r) + 1).replace(t, "");
  }
  return (mm = n), mm;
}
var gm, DE;
function nB() {
  if (DE) return gm;
  DE = 1;
  var e = tB(),
    t = $t(),
    n = Ao(),
    r = NaN,
    i = /^[-+]0x[0-9a-f]+$/i,
    o = /^0b[01]+$/i,
    s = /^0o[0-7]+$/i,
    a = parseInt;
  function u(l) {
    if (typeof l == "number") return l;
    if (n(l)) return r;
    if (t(l)) {
      var c = typeof l.valueOf == "function" ? l.valueOf() : l;
      l = t(c) ? c + "" : c;
    }
    if (typeof l != "string") return l === 0 ? l : +l;
    l = e(l);
    var f = o.test(l);
    return f || s.test(l) ? a(l.slice(2), f ? 2 : 8) : i.test(l) ? r : +l;
  }
  return (gm = u), gm;
}
var vm, OE;
function e2() {
  if (OE) return vm;
  OE = 1;
  var e = nB(),
    t = 1 / 0,
    n = 17976931348623157e292;
  function r(i) {
    if (!i) return i === 0 ? i : 0;
    if (((i = e(i)), i === t || i === -t)) {
      var o = i < 0 ? -1 : 1;
      return o * n;
    }
    return i === i ? i : 0;
  }
  return (vm = r), vm;
}
var ym, LE;
function rB() {
  if (LE) return ym;
  LE = 1;
  var e = e2();
  function t(n) {
    var r = e(n),
      i = r % 1;
    return r === r ? (i ? r - i : r) : 0;
  }
  return (ym = t), ym;
}
var wm, FE;
function iB() {
  if (FE) return wm;
  FE = 1;
  var e = GN(),
    t = er(),
    n = rB(),
    r = Math.max;
  function i(o, s, a) {
    var u = o == null ? 0 : o.length;
    if (!u) return -1;
    var l = a == null ? 0 : n(a);
    return l < 0 && (l = r(u + l, 0)), e(o, t(s, 3), l);
  }
  return (wm = i), wm;
}
var xm, jE;
function oB() {
  if (jE) return xm;
  jE = 1;
  var e = J5(),
    t = iB(),
    n = e(t);
  return (xm = n), xm;
}
var _m, VE;
function t2() {
  if (VE) return _m;
  VE = 1;
  var e = D0();
  function t(n) {
    var r = n == null ? 0 : n.length;
    return r ? e(n, 1) : [];
  }
  return (_m = t), _m;
}
var bm, qE;
function sB() {
  if (qE) return bm;
  qE = 1;
  var e = A0(),
    t = CN(),
    n = gi();
  function r(i, o) {
    return i == null ? i : e(i, t(o), n);
  }
  return (bm = r), bm;
}
var Sm, $E;
function aB() {
  if ($E) return Sm;
  $E = 1;
  function e(t) {
    var n = t == null ? 0 : t.length;
    return n ? t[n - 1] : void 0;
  }
  return (Sm = e), Sm;
}
var Em, zE;
function uB() {
  if (zE) return Em;
  zE = 1;
  var e = rc(),
    t = N0(),
    n = er();
  function r(i, o) {
    var s = {};
    return (
      (o = n(o, 3)),
      t(i, function (a, u, l) {
        e(s, u, o(a, u, l));
      }),
      s
    );
  }
  return (Em = r), Em;
}
var Cm, BE;
function L0() {
  if (BE) return Cm;
  BE = 1;
  var e = Ao();
  function t(n, r, i) {
    for (var o = -1, s = n.length; ++o < s; ) {
      var a = n[o],
        u = r(a);
      if (u != null && (l === void 0 ? u === u && !e(u) : i(u, l)))
        var l = u,
          c = a;
    }
    return c;
  }
  return (Cm = t), Cm;
}
var Tm, UE;
function lB() {
  if (UE) return Tm;
  UE = 1;
  function e(t, n) {
    return t > n;
  }
  return (Tm = e), Tm;
}
var km, HE;
function cB() {
  if (HE) return km;
  HE = 1;
  var e = L0(),
    t = lB(),
    n = vi();
  function r(i) {
    return i && i.length ? e(i, n, t) : void 0;
  }
  return (km = r), km;
}
var Rm, GE;
function n2() {
  if (GE) return Rm;
  GE = 1;
  var e = rc(),
    t = To();
  function n(r, i, o) {
    ((o !== void 0 && !t(r[i], o)) || (o === void 0 && !(i in r))) && e(r, i, o);
  }
  return (Rm = n), Rm;
}
var Pm, WE;
function fB() {
  if (WE) return Pm;
  WE = 1;
  var e = pi(),
    t = uc(),
    n = En(),
    r = "[object Object]",
    i = Function.prototype,
    o = Object.prototype,
    s = i.toString,
    a = o.hasOwnProperty,
    u = s.call(Object);
  function l(c) {
    if (!n(c) || e(c) != r) return !1;
    var f = t(c);
    if (f === null) return !0;
    var d = a.call(f, "constructor") && f.constructor;
    return typeof d == "function" && d instanceof d && s.call(d) == u;
  }
  return (Pm = l), Pm;
}
var Am, KE;
function r2() {
  if (KE) return Am;
  KE = 1;
  function e(t, n) {
    if (!(n === "constructor" && typeof t[n] == "function") && n != "__proto__") return t[n];
  }
  return (Am = e), Am;
}
var Nm, YE;
function dB() {
  if (YE) return Nm;
  YE = 1;
  var e = ha(),
    t = gi();
  function n(r) {
    return e(r, t(r));
  }
  return (Nm = n), Nm;
}
var Mm, XE;
function hB() {
  if (XE) return Mm;
  XE = 1;
  var e = n2(),
    t = dN(),
    n = _N(),
    r = hN(),
    i = SN(),
    o = pa(),
    s = Ie(),
    a = WN(),
    u = Ro(),
    l = da(),
    c = $t(),
    f = fB(),
    d = ma(),
    h = r2(),
    v = dB();
  function p(y, m, g, w, x, b, E) {
    var C = h(y, g),
      T = h(m, g),
      P = E.get(T);
    if (P) {
      e(y, g, P);
      return;
    }
    var M = b ? b(C, T, g + "", y, m, E) : void 0,
      I = M === void 0;
    if (I) {
      var j = s(T),
        q = !j && u(T),
        S = !j && !q && d(T);
      (M = T),
        j || q || S
          ? s(C)
            ? (M = C)
            : a(C)
              ? (M = r(C))
              : q
                ? ((I = !1), (M = t(T, !0)))
                : S
                  ? ((I = !1), (M = n(T, !0)))
                  : (M = [])
          : f(T) || o(T)
            ? ((M = C), o(C) ? (M = v(C)) : (!c(C) || l(C)) && (M = i(T)))
            : (I = !1);
    }
    I && (E.set(T, M), x(M, T, w, b, E), E.delete(T)), e(y, g, M);
  }
  return (Mm = p), Mm;
}
var Im, ZE;
function pB() {
  if (ZE) return Im;
  ZE = 1;
  var e = nc(),
    t = n2(),
    n = A0(),
    r = hB(),
    i = $t(),
    o = gi(),
    s = r2();
  function a(u, l, c, f, d) {
    u !== l &&
      n(
        l,
        function (h, v) {
          if ((d || (d = new e()), i(h))) r(u, l, v, c, a, f, d);
          else {
            var p = f ? f(s(u, v), h, v + "", u, l, d) : void 0;
            p === void 0 && (p = h), t(u, v, p);
          }
        },
        o,
      );
  }
  return (Im = a), Im;
}
var Dm, QE;
function mB() {
  if (QE) return Dm;
  QE = 1;
  var e = hc(),
    t = pc();
  function n(r) {
    return e(function (i, o) {
      var s = -1,
        a = o.length,
        u = a > 1 ? o[a - 1] : void 0,
        l = a > 2 ? o[2] : void 0;
      for (
        u = r.length > 3 && typeof u == "function" ? (a--, u) : void 0,
          l && t(o[0], o[1], l) && ((u = a < 3 ? void 0 : u), (a = 1)),
          i = Object(i);
        ++s < a;

      ) {
        var c = o[s];
        c && r(i, c, s, u);
      }
      return i;
    });
  }
  return (Dm = n), Dm;
}
var Om, JE;
function gB() {
  if (JE) return Om;
  JE = 1;
  var e = pB(),
    t = mB(),
    n = t(function (r, i, o) {
      e(r, i, o);
    });
  return (Om = n), Om;
}
var Lm, eC;
function i2() {
  if (eC) return Lm;
  eC = 1;
  function e(t, n) {
    return t < n;
  }
  return (Lm = e), Lm;
}
var Fm, tC;
function vB() {
  if (tC) return Fm;
  tC = 1;
  var e = L0(),
    t = i2(),
    n = vi();
  function r(i) {
    return i && i.length ? e(i, n, t) : void 0;
  }
  return (Fm = r), Fm;
}
var jm, nC;
function yB() {
  if (nC) return jm;
  nC = 1;
  var e = L0(),
    t = er(),
    n = i2();
  function r(i, o) {
    return i && i.length ? e(i, t(o, 2), n) : void 0;
  }
  return (jm = r), jm;
}
var Vm, rC;
function wB() {
  if (rC) return Vm;
  rC = 1;
  var e = on(),
    t = function () {
      return e.Date.now();
    };
  return (Vm = t), Vm;
}
var qm, iC;
function xB() {
  if (iC) return qm;
  iC = 1;
  var e = ic(),
    t = fc(),
    n = oc(),
    r = $t(),
    i = ga();
  function o(s, a, u, l) {
    if (!r(s)) return s;
    a = t(a, s);
    for (var c = -1, f = a.length, d = f - 1, h = s; h != null && ++c < f; ) {
      var v = i(a[c]),
        p = u;
      if (v === "__proto__" || v === "constructor" || v === "prototype") return s;
      if (c != d) {
        var y = h[v];
        (p = l ? l(y, v, h) : void 0), p === void 0 && (p = r(y) ? y : n(a[c + 1]) ? [] : {});
      }
      e(h, v, p), (h = h[v]);
    }
    return s;
  }
  return (qm = o), qm;
}
var $m, oC;
function _B() {
  if (oC) return $m;
  oC = 1;
  var e = dc(),
    t = xB(),
    n = fc();
  function r(i, o, s) {
    for (var a = -1, u = o.length, l = {}; ++a < u; ) {
      var c = o[a],
        f = e(i, c);
      s(f, c) && t(l, n(c, i), f);
    }
    return l;
  }
  return ($m = r), $m;
}
var zm, sC;
function bB() {
  if (sC) return zm;
  sC = 1;
  var e = _B(),
    t = LN();
  function n(r, i) {
    return e(r, i, function (o, s) {
      return t(r, s);
    });
  }
  return (zm = n), zm;
}
var Bm, aC;
function SB() {
  if (aC) return Bm;
  aC = 1;
  var e = t2(),
    t = UN(),
    n = HN();
  function r(i) {
    return n(t(i, void 0, e), i + "");
  }
  return (Bm = r), Bm;
}
var Um, uC;
function EB() {
  if (uC) return Um;
  uC = 1;
  var e = bB(),
    t = SB(),
    n = t(function (r, i) {
      return r == null ? {} : e(r, i);
    });
  return (Um = n), Um;
}
var Hm, lC;
function CB() {
  if (lC) return Hm;
  lC = 1;
  var e = Math.ceil,
    t = Math.max;
  function n(r, i, o, s) {
    for (var a = -1, u = t(e((i - r) / (o || 1)), 0), l = Array(u); u--; )
      (l[s ? u : ++a] = r), (r += o);
    return l;
  }
  return (Hm = n), Hm;
}
var Gm, cC;
function TB() {
  if (cC) return Gm;
  cC = 1;
  var e = CB(),
    t = pc(),
    n = e2();
  function r(i) {
    return function (o, s, a) {
      return (
        a && typeof a != "number" && t(o, s, a) && (s = a = void 0),
        (o = n(o)),
        s === void 0 ? ((s = o), (o = 0)) : (s = n(s)),
        (a = a === void 0 ? (o < s ? 1 : -1) : n(a)),
        e(o, s, a, i)
      );
    };
  }
  return (Gm = r), Gm;
}
var Wm, fC;
function kB() {
  if (fC) return Wm;
  fC = 1;
  var e = TB(),
    t = e();
  return (Wm = t), Wm;
}
var Km, dC;
function RB() {
  if (dC) return Km;
  dC = 1;
  function e(t, n) {
    var r = t.length;
    for (t.sort(n); r--; ) t[r] = t[r].value;
    return t;
  }
  return (Km = e), Km;
}
var Ym, hC;
function PB() {
  if (hC) return Ym;
  hC = 1;
  var e = Ao();
  function t(n, r) {
    if (n !== r) {
      var i = n !== void 0,
        o = n === null,
        s = n === n,
        a = e(n),
        u = r !== void 0,
        l = r === null,
        c = r === r,
        f = e(r);
      if (
        (!l && !f && !a && n > r) ||
        (a && u && c && !l && !f) ||
        (o && u && c) ||
        (!i && c) ||
        !s
      )
        return 1;
      if (
        (!o && !a && !f && n < r) ||
        (f && i && s && !o && !a) ||
        (l && i && s) ||
        (!u && s) ||
        !c
      )
        return -1;
    }
    return 0;
  }
  return (Ym = t), Ym;
}
var Xm, pC;
function AB() {
  if (pC) return Xm;
  pC = 1;
  var e = PB();
  function t(n, r, i) {
    for (var o = -1, s = n.criteria, a = r.criteria, u = s.length, l = i.length; ++o < u; ) {
      var c = e(s[o], a[o]);
      if (c) {
        if (o >= l) return c;
        var f = i[o];
        return c * (f == "desc" ? -1 : 1);
      }
    }
    return n.index - r.index;
  }
  return (Xm = t), Xm;
}
var Zm, mC;
function NB() {
  if (mC) return Zm;
  mC = 1;
  var e = cc(),
    t = dc(),
    n = er(),
    r = $N(),
    i = RB(),
    o = sc(),
    s = AB(),
    a = vi(),
    u = Ie();
  function l(c, f, d) {
    f.length
      ? (f = e(f, function (p) {
          return u(p)
            ? function (y) {
                return t(y, p.length === 1 ? p[0] : p);
              }
            : p;
        }))
      : (f = [a]);
    var h = -1;
    f = e(f, o(n));
    var v = r(c, function (p, y, m) {
      var g = e(f, function (w) {
        return w(p);
      });
      return { criteria: g, index: ++h, value: p };
    });
    return i(v, function (p, y) {
      return s(p, y, d);
    });
  }
  return (Zm = l), Zm;
}
var Qm, gC;
function MB() {
  if (gC) return Qm;
  gC = 1;
  var e = D0(),
    t = NB(),
    n = hc(),
    r = pc(),
    i = n(function (o, s) {
      if (o == null) return [];
      var a = s.length;
      return (
        a > 1 && r(o, s[0], s[1]) ? (s = []) : a > 2 && r(s[0], s[1], s[2]) && (s = [s[0]]),
        t(o, e(s, 1), [])
      );
    });
  return (Qm = i), Qm;
}
var Jm, vC;
function IB() {
  if (vC) return Jm;
  vC = 1;
  var e = DN(),
    t = 0;
  function n(r) {
    var i = ++t;
    return e(r) + i;
  }
  return (Jm = n), Jm;
}
var eg, yC;
function DB() {
  if (yC) return eg;
  yC = 1;
  function e(t, n, r) {
    for (var i = -1, o = t.length, s = n.length, a = {}; ++i < o; ) {
      var u = i < s ? n[i] : void 0;
      r(a, t[i], u);
    }
    return a;
  }
  return (eg = e), eg;
}
var tg, wC;
function OB() {
  if (wC) return tg;
  wC = 1;
  var e = ic(),
    t = DB();
  function n(r, i) {
    return t(r || [], i || [], e);
  }
  return (tg = n), tg;
}
var pl;
if (typeof w0 == "function")
  try {
    pl = {
      cloneDeep: Z5(),
      constant: P0(),
      defaults: Q5(),
      each: kN(),
      filter: jN(),
      find: oB(),
      flatten: t2(),
      forEach: TN(),
      forIn: sB(),
      has: VN(),
      isUndefined: qN(),
      last: aB(),
      map: zN(),
      mapValues: uB(),
      max: cB(),
      merge: gB(),
      min: vB(),
      minBy: yB(),
      now: wB(),
      pick: EB(),
      range: kB(),
      reduce: BN(),
      sortBy: MB(),
      uniqueId: IB(),
      values: KN(),
      zipObject: OB(),
    };
  } catch {}
pl || (pl = window._);
var we = pl,
  LB = mc;
function mc() {
  var e = {};
  (e._next = e._prev = e), (this._sentinel = e);
}
mc.prototype.dequeue = function () {
  var e = this._sentinel,
    t = e._prev;
  if (t !== e) return o2(t), t;
};
mc.prototype.enqueue = function (e) {
  var t = this._sentinel;
  e._prev && e._next && o2(e),
    (e._next = t._next),
    (t._next._prev = e),
    (t._next = e),
    (e._prev = t);
};
mc.prototype.toString = function () {
  for (var e = [], t = this._sentinel, n = t._prev; n !== t; )
    e.push(JSON.stringify(n, FB)), (n = n._prev);
  return "[" + e.join(", ") + "]";
};
function o2(e) {
  (e._prev._next = e._next), (e._next._prev = e._prev), delete e._next, delete e._prev;
}
function FB(e, t) {
  if (e !== "_next" && e !== "_prev") return t;
}
var Fn = we,
  jB = sn.Graph,
  VB = LB,
  qB = zB,
  $B = Fn.constant(1);
function zB(e, t) {
  if (e.nodeCount() <= 1) return [];
  var n = UB(e, t || $B),
    r = BB(n.graph, n.buckets, n.zeroIdx);
  return Fn.flatten(
    Fn.map(r, function (i) {
      return e.outEdges(i.v, i.w);
    }),
    !0,
  );
}
function BB(e, t, n) {
  for (var r = [], i = t[t.length - 1], o = t[0], s; e.nodeCount(); ) {
    for (; (s = o.dequeue()); ) ng(e, t, n, s);
    for (; (s = i.dequeue()); ) ng(e, t, n, s);
    if (e.nodeCount()) {
      for (var a = t.length - 2; a > 0; --a)
        if (((s = t[a].dequeue()), s)) {
          r = r.concat(ng(e, t, n, s, !0));
          break;
        }
    }
  }
  return r;
}
function ng(e, t, n, r, i) {
  var o = i ? [] : void 0;
  return (
    Fn.forEach(e.inEdges(r.v), function (s) {
      var a = e.edge(s),
        u = e.node(s.v);
      i && o.push({ v: s.v, w: s.w }), (u.out -= a), jv(t, n, u);
    }),
    Fn.forEach(e.outEdges(r.v), function (s) {
      var a = e.edge(s),
        u = s.w,
        l = e.node(u);
      (l.in -= a), jv(t, n, l);
    }),
    e.removeNode(r.v),
    o
  );
}
function UB(e, t) {
  var n = new jB(),
    r = 0,
    i = 0;
  Fn.forEach(e.nodes(), function (a) {
    n.setNode(a, { v: a, in: 0, out: 0 });
  }),
    Fn.forEach(e.edges(), function (a) {
      var u = n.edge(a.v, a.w) || 0,
        l = t(a),
        c = u + l;
      n.setEdge(a.v, a.w, c),
        (i = Math.max(i, (n.node(a.v).out += l))),
        (r = Math.max(r, (n.node(a.w).in += l)));
    });
  var o = Fn.range(i + r + 3).map(function () {
      return new VB();
    }),
    s = r + 1;
  return (
    Fn.forEach(n.nodes(), function (a) {
      jv(o, s, n.node(a));
    }),
    { graph: n, buckets: o, zeroIdx: s }
  );
}
function jv(e, t, n) {
  n.out ? (n.in ? e[n.out - n.in + t].enqueue(n) : e[e.length - 1].enqueue(n)) : e[0].enqueue(n);
}
var Zr = we,
  HB = qB,
  GB = { run: WB, undo: YB };
function WB(e) {
  var t = e.graph().acyclicer === "greedy" ? HB(e, n(e)) : KB(e);
  Zr.forEach(t, function (r) {
    var i = e.edge(r);
    e.removeEdge(r),
      (i.forwardName = r.name),
      (i.reversed = !0),
      e.setEdge(r.w, r.v, i, Zr.uniqueId("rev"));
  });
  function n(r) {
    return function (i) {
      return r.edge(i).weight;
    };
  }
}
function KB(e) {
  var t = [],
    n = {},
    r = {};
  function i(o) {
    Zr.has(r, o) ||
      ((r[o] = !0),
      (n[o] = !0),
      Zr.forEach(e.outEdges(o), function (s) {
        Zr.has(n, s.w) ? t.push(s) : i(s.w);
      }),
      delete n[o]);
  }
  return Zr.forEach(e.nodes(), i), t;
}
function YB(e) {
  Zr.forEach(e.edges(), function (t) {
    var n = e.edge(t);
    if (n.reversed) {
      e.removeEdge(t);
      var r = n.forwardName;
      delete n.reversed, delete n.forwardName, e.setEdge(t.w, t.v, n, r);
    }
  });
}
var le = we,
  s2 = sn.Graph,
  wt = {
    addDummyNode: a2,
    simplify: XB,
    asNonCompoundGraph: ZB,
    successorWeights: QB,
    predecessorWeights: JB,
    intersectRect: e8,
    buildLayerMatrix: t8,
    normalizeRanks: n8,
    removeEmptyRanks: r8,
    addBorderNode: i8,
    maxRank: u2,
    partition: o8,
    time: s8,
    notime: a8,
  };
function a2(e, t, n, r) {
  var i;
  do i = le.uniqueId(r);
  while (e.hasNode(i));
  return (n.dummy = t), e.setNode(i, n), i;
}
function XB(e) {
  var t = new s2().setGraph(e.graph());
  return (
    le.forEach(e.nodes(), function (n) {
      t.setNode(n, e.node(n));
    }),
    le.forEach(e.edges(), function (n) {
      var r = t.edge(n.v, n.w) || { weight: 0, minlen: 1 },
        i = e.edge(n);
      t.setEdge(n.v, n.w, { weight: r.weight + i.weight, minlen: Math.max(r.minlen, i.minlen) });
    }),
    t
  );
}
function ZB(e) {
  var t = new s2({ multigraph: e.isMultigraph() }).setGraph(e.graph());
  return (
    le.forEach(e.nodes(), function (n) {
      e.children(n).length || t.setNode(n, e.node(n));
    }),
    le.forEach(e.edges(), function (n) {
      t.setEdge(n, e.edge(n));
    }),
    t
  );
}
function QB(e) {
  var t = le.map(e.nodes(), function (n) {
    var r = {};
    return (
      le.forEach(e.outEdges(n), function (i) {
        r[i.w] = (r[i.w] || 0) + e.edge(i).weight;
      }),
      r
    );
  });
  return le.zipObject(e.nodes(), t);
}
function JB(e) {
  var t = le.map(e.nodes(), function (n) {
    var r = {};
    return (
      le.forEach(e.inEdges(n), function (i) {
        r[i.v] = (r[i.v] || 0) + e.edge(i).weight;
      }),
      r
    );
  });
  return le.zipObject(e.nodes(), t);
}
function e8(e, t) {
  var n = e.x,
    r = e.y,
    i = t.x - n,
    o = t.y - r,
    s = e.width / 2,
    a = e.height / 2;
  if (!i && !o) throw new Error("Not possible to find intersection inside of the rectangle");
  var u, l;
  return (
    Math.abs(o) * s > Math.abs(i) * a
      ? (o < 0 && (a = -a), (u = (a * i) / o), (l = a))
      : (i < 0 && (s = -s), (u = s), (l = (s * o) / i)),
    { x: n + u, y: r + l }
  );
}
function t8(e) {
  var t = le.map(le.range(u2(e) + 1), function () {
    return [];
  });
  return (
    le.forEach(e.nodes(), function (n) {
      var r = e.node(n),
        i = r.rank;
      le.isUndefined(i) || (t[i][r.order] = n);
    }),
    t
  );
}
function n8(e) {
  var t = le.min(
    le.map(e.nodes(), function (n) {
      return e.node(n).rank;
    }),
  );
  le.forEach(e.nodes(), function (n) {
    var r = e.node(n);
    le.has(r, "rank") && (r.rank -= t);
  });
}
function r8(e) {
  var t = le.min(
      le.map(e.nodes(), function (o) {
        return e.node(o).rank;
      }),
    ),
    n = [];
  le.forEach(e.nodes(), function (o) {
    var s = e.node(o).rank - t;
    n[s] || (n[s] = []), n[s].push(o);
  });
  var r = 0,
    i = e.graph().nodeRankFactor;
  le.forEach(n, function (o, s) {
    le.isUndefined(o) && s % i !== 0
      ? --r
      : r &&
        le.forEach(o, function (a) {
          e.node(a).rank += r;
        });
  });
}
function i8(e, t, n, r) {
  var i = { width: 0, height: 0 };
  return arguments.length >= 4 && ((i.rank = n), (i.order = r)), a2(e, "border", i, t);
}
function u2(e) {
  return le.max(
    le.map(e.nodes(), function (t) {
      var n = e.node(t).rank;
      if (!le.isUndefined(n)) return n;
    }),
  );
}
function o8(e, t) {
  var n = { lhs: [], rhs: [] };
  return (
    le.forEach(e, function (r) {
      t(r) ? n.lhs.push(r) : n.rhs.push(r);
    }),
    n
  );
}
function s8(e, t) {
  var n = le.now();
  try {
    return t();
  } finally {
    console.log(e + " time: " + (le.now() - n) + "ms");
  }
}
function a8(e, t) {
  return t();
}
var l2 = we,
  u8 = wt,
  l8 = { run: c8, undo: d8 };
function c8(e) {
  (e.graph().dummyChains = []),
    l2.forEach(e.edges(), function (t) {
      f8(e, t);
    });
}
function f8(e, t) {
  var n = t.v,
    r = e.node(n).rank,
    i = t.w,
    o = e.node(i).rank,
    s = t.name,
    a = e.edge(t),
    u = a.labelRank;
  if (o !== r + 1) {
    e.removeEdge(t);
    var l, c, f;
    for (f = 0, ++r; r < o; ++f, ++r)
      (a.points = []),
        (c = { width: 0, height: 0, edgeLabel: a, edgeObj: t, rank: r }),
        (l = u8.addDummyNode(e, "edge", c, "_d")),
        r === u &&
          ((c.width = a.width),
          (c.height = a.height),
          (c.dummy = "edge-label"),
          (c.labelpos = a.labelpos)),
        e.setEdge(n, l, { weight: a.weight }, s),
        f === 0 && e.graph().dummyChains.push(l),
        (n = l);
    e.setEdge(n, i, { weight: a.weight }, s);
  }
}
function d8(e) {
  l2.forEach(e.graph().dummyChains, function (t) {
    var n = e.node(t),
      r = n.edgeLabel,
      i;
    for (e.setEdge(n.edgeObj, r); n.dummy; )
      (i = e.successors(t)[0]),
        e.removeNode(t),
        r.points.push({ x: n.x, y: n.y }),
        n.dummy === "edge-label" &&
          ((r.x = n.x), (r.y = n.y), (r.width = n.width), (r.height = n.height)),
        (t = i),
        (n = e.node(t));
  });
}
var eu = we,
  gc = { longestPath: h8, slack: p8 };
function h8(e) {
  var t = {};
  function n(r) {
    var i = e.node(r);
    if (eu.has(t, r)) return i.rank;
    t[r] = !0;
    var o = eu.min(
      eu.map(e.outEdges(r), function (s) {
        return n(s.w) - e.edge(s).minlen;
      }),
    );
    return (o === Number.POSITIVE_INFINITY || o === void 0 || o === null) && (o = 0), (i.rank = o);
  }
  eu.forEach(e.sources(), n);
}
function p8(e, t) {
  return e.node(t.w).rank - e.node(t.v).rank - e.edge(t).minlen;
}
var ml = we,
  m8 = sn.Graph,
  gl = gc.slack,
  c2 = g8;
function g8(e) {
  var t = new m8({ directed: !1 }),
    n = e.nodes()[0],
    r = e.nodeCount();
  t.setNode(n, {});
  for (var i, o; v8(t, e) < r; )
    (i = y8(t, e)), (o = t.hasNode(i.v) ? gl(e, i) : -gl(e, i)), w8(t, e, o);
  return t;
}
function v8(e, t) {
  function n(r) {
    ml.forEach(t.nodeEdges(r), function (i) {
      var o = i.v,
        s = r === o ? i.w : o;
      !e.hasNode(s) && !gl(t, i) && (e.setNode(s, {}), e.setEdge(r, s, {}), n(s));
    });
  }
  return ml.forEach(e.nodes(), n), e.nodeCount();
}
function y8(e, t) {
  return ml.minBy(t.edges(), function (n) {
    if (e.hasNode(n.v) !== e.hasNode(n.w)) return gl(t, n);
  });
}
function w8(e, t, n) {
  ml.forEach(e.nodes(), function (r) {
    t.node(r).rank += n;
  });
}
var Yn = we,
  x8 = c2,
  _8 = gc.slack,
  b8 = gc.longestPath,
  S8 = sn.alg.preorder,
  E8 = sn.alg.postorder,
  C8 = wt.simplify,
  T8 = yi;
yi.initLowLimValues = j0;
yi.initCutValues = F0;
yi.calcCutValue = f2;
yi.leaveEdge = h2;
yi.enterEdge = p2;
yi.exchangeEdges = m2;
function yi(e) {
  (e = C8(e)), b8(e);
  var t = x8(e);
  j0(t), F0(t, e);
  for (var n, r; (n = h2(t)); ) (r = p2(t, e, n)), m2(t, e, n, r);
}
function F0(e, t) {
  var n = E8(e, e.nodes());
  (n = n.slice(0, n.length - 1)),
    Yn.forEach(n, function (r) {
      k8(e, t, r);
    });
}
function k8(e, t, n) {
  var r = e.node(n),
    i = r.parent;
  e.edge(n, i).cutvalue = f2(e, t, n);
}
function f2(e, t, n) {
  var r = e.node(n),
    i = r.parent,
    o = !0,
    s = t.edge(n, i),
    a = 0;
  return (
    s || ((o = !1), (s = t.edge(i, n))),
    (a = s.weight),
    Yn.forEach(t.nodeEdges(n), function (u) {
      var l = u.v === n,
        c = l ? u.w : u.v;
      if (c !== i) {
        var f = l === o,
          d = t.edge(u).weight;
        if (((a += f ? d : -d), P8(e, n, c))) {
          var h = e.edge(n, c).cutvalue;
          a += f ? -h : h;
        }
      }
    }),
    a
  );
}
function j0(e, t) {
  arguments.length < 2 && (t = e.nodes()[0]), d2(e, {}, 1, t);
}
function d2(e, t, n, r, i) {
  var o = n,
    s = e.node(r);
  return (
    (t[r] = !0),
    Yn.forEach(e.neighbors(r), function (a) {
      Yn.has(t, a) || (n = d2(e, t, n, a, r));
    }),
    (s.low = o),
    (s.lim = n++),
    i ? (s.parent = i) : delete s.parent,
    n
  );
}
function h2(e) {
  return Yn.find(e.edges(), function (t) {
    return e.edge(t).cutvalue < 0;
  });
}
function p2(e, t, n) {
  var r = n.v,
    i = n.w;
  t.hasEdge(r, i) || ((r = n.w), (i = n.v));
  var o = e.node(r),
    s = e.node(i),
    a = o,
    u = !1;
  o.lim > s.lim && ((a = s), (u = !0));
  var l = Yn.filter(t.edges(), function (c) {
    return u === xC(e, e.node(c.v), a) && u !== xC(e, e.node(c.w), a);
  });
  return Yn.minBy(l, function (c) {
    return _8(t, c);
  });
}
function m2(e, t, n, r) {
  var i = n.v,
    o = n.w;
  e.removeEdge(i, o), e.setEdge(r.v, r.w, {}), j0(e), F0(e, t), R8(e, t);
}
function R8(e, t) {
  var n = Yn.find(e.nodes(), function (i) {
      return !t.node(i).parent;
    }),
    r = S8(e, n);
  (r = r.slice(1)),
    Yn.forEach(r, function (i) {
      var o = e.node(i).parent,
        s = t.edge(i, o),
        a = !1;
      s || ((s = t.edge(o, i)), (a = !0)),
        (t.node(i).rank = t.node(o).rank + (a ? s.minlen : -s.minlen));
    });
}
function P8(e, t, n) {
  return e.hasEdge(t, n);
}
function xC(e, t, n) {
  return n.low <= t.lim && t.lim <= n.lim;
}
var A8 = gc,
  g2 = A8.longestPath,
  N8 = c2,
  M8 = T8,
  I8 = D8;
function D8(e) {
  switch (e.graph().ranker) {
    case "network-simplex":
      _C(e);
      break;
    case "tight-tree":
      L8(e);
      break;
    case "longest-path":
      O8(e);
      break;
    default:
      _C(e);
  }
}
var O8 = g2;
function L8(e) {
  g2(e), N8(e);
}
function _C(e) {
  M8(e);
}
var Vv = we,
  F8 = j8;
function j8(e) {
  var t = q8(e);
  Vv.forEach(e.graph().dummyChains, function (n) {
    for (
      var r = e.node(n),
        i = r.edgeObj,
        o = V8(e, t, i.v, i.w),
        s = o.path,
        a = o.lca,
        u = 0,
        l = s[u],
        c = !0;
      n !== i.w;

    ) {
      if (((r = e.node(n)), c)) {
        for (; (l = s[u]) !== a && e.node(l).maxRank < r.rank; ) u++;
        l === a && (c = !1);
      }
      if (!c) {
        for (; u < s.length - 1 && e.node((l = s[u + 1])).minRank <= r.rank; ) u++;
        l = s[u];
      }
      e.setParent(n, l), (n = e.successors(n)[0]);
    }
  });
}
function V8(e, t, n, r) {
  var i = [],
    o = [],
    s = Math.min(t[n].low, t[r].low),
    a = Math.max(t[n].lim, t[r].lim),
    u,
    l;
  u = n;
  do (u = e.parent(u)), i.push(u);
  while (u && (t[u].low > s || a > t[u].lim));
  for (l = u, u = r; (u = e.parent(u)) !== l; ) o.push(u);
  return { path: i.concat(o.reverse()), lca: l };
}
function q8(e) {
  var t = {},
    n = 0;
  function r(i) {
    var o = n;
    Vv.forEach(e.children(i), r), (t[i] = { low: o, lim: n++ });
  }
  return Vv.forEach(e.children(), r), t;
}
var jn = we,
  qv = wt,
  $8 = { run: z8, cleanup: H8 };
function z8(e) {
  var t = qv.addDummyNode(e, "root", {}, "_root"),
    n = B8(e),
    r = jn.max(jn.values(n)) - 1,
    i = 2 * r + 1;
  (e.graph().nestingRoot = t),
    jn.forEach(e.edges(), function (s) {
      e.edge(s).minlen *= i;
    });
  var o = U8(e) + 1;
  jn.forEach(e.children(), function (s) {
    v2(e, t, i, o, r, n, s);
  }),
    (e.graph().nodeRankFactor = i);
}
function v2(e, t, n, r, i, o, s) {
  var a = e.children(s);
  if (!a.length) {
    s !== t && e.setEdge(t, s, { weight: 0, minlen: n });
    return;
  }
  var u = qv.addBorderNode(e, "_bt"),
    l = qv.addBorderNode(e, "_bb"),
    c = e.node(s);
  e.setParent(u, s),
    (c.borderTop = u),
    e.setParent(l, s),
    (c.borderBottom = l),
    jn.forEach(a, function (f) {
      v2(e, t, n, r, i, o, f);
      var d = e.node(f),
        h = d.borderTop ? d.borderTop : f,
        v = d.borderBottom ? d.borderBottom : f,
        p = d.borderTop ? r : 2 * r,
        y = h !== v ? 1 : i - o[s] + 1;
      e.setEdge(u, h, { weight: p, minlen: y, nestingEdge: !0 }),
        e.setEdge(v, l, { weight: p, minlen: y, nestingEdge: !0 });
    }),
    e.parent(s) || e.setEdge(t, u, { weight: 0, minlen: i + o[s] });
}
function B8(e) {
  var t = {};
  function n(r, i) {
    var o = e.children(r);
    o &&
      o.length &&
      jn.forEach(o, function (s) {
        n(s, i + 1);
      }),
      (t[r] = i);
  }
  return (
    jn.forEach(e.children(), function (r) {
      n(r, 1);
    }),
    t
  );
}
function U8(e) {
  return jn.reduce(
    e.edges(),
    function (t, n) {
      return t + e.edge(n).weight;
    },
    0,
  );
}
function H8(e) {
  var t = e.graph();
  e.removeNode(t.nestingRoot),
    delete t.nestingRoot,
    jn.forEach(e.edges(), function (n) {
      var r = e.edge(n);
      r.nestingEdge && e.removeEdge(n);
    });
}
var rg = we,
  G8 = wt,
  W8 = K8;
function K8(e) {
  function t(n) {
    var r = e.children(n),
      i = e.node(n);
    if ((r.length && rg.forEach(r, t), rg.has(i, "minRank"))) {
      (i.borderLeft = []), (i.borderRight = []);
      for (var o = i.minRank, s = i.maxRank + 1; o < s; ++o)
        bC(e, "borderLeft", "_bl", n, i, o), bC(e, "borderRight", "_br", n, i, o);
    }
  }
  rg.forEach(e.children(), t);
}
function bC(e, t, n, r, i, o) {
  var s = { width: 0, height: 0, rank: o, borderType: t },
    a = i[t][o - 1],
    u = G8.addDummyNode(e, "border", s, n);
  (i[t][o] = u), e.setParent(u, r), a && e.setEdge(a, u, { weight: 1 });
}
var gn = we,
  Y8 = { adjust: X8, undo: Z8 };
function X8(e) {
  var t = e.graph().rankdir.toLowerCase();
  (t === "lr" || t === "rl") && y2(e);
}
function Z8(e) {
  var t = e.graph().rankdir.toLowerCase();
  (t === "bt" || t === "rl") && Q8(e), (t === "lr" || t === "rl") && (J8(e), y2(e));
}
function y2(e) {
  gn.forEach(e.nodes(), function (t) {
    SC(e.node(t));
  }),
    gn.forEach(e.edges(), function (t) {
      SC(e.edge(t));
    });
}
function SC(e) {
  var t = e.width;
  (e.width = e.height), (e.height = t);
}
function Q8(e) {
  gn.forEach(e.nodes(), function (t) {
    ig(e.node(t));
  }),
    gn.forEach(e.edges(), function (t) {
      var n = e.edge(t);
      gn.forEach(n.points, ig), gn.has(n, "y") && ig(n);
    });
}
function ig(e) {
  e.y = -e.y;
}
function J8(e) {
  gn.forEach(e.nodes(), function (t) {
    og(e.node(t));
  }),
    gn.forEach(e.edges(), function (t) {
      var n = e.edge(t);
      gn.forEach(n.points, og), gn.has(n, "x") && og(n);
    });
}
function og(e) {
  var t = e.x;
  (e.x = e.y), (e.y = t);
}
var Pn = we,
  e6 = t6;
function t6(e) {
  var t = {},
    n = Pn.filter(e.nodes(), function (a) {
      return !e.children(a).length;
    }),
    r = Pn.max(
      Pn.map(n, function (a) {
        return e.node(a).rank;
      }),
    ),
    i = Pn.map(Pn.range(r + 1), function () {
      return [];
    });
  function o(a) {
    if (!Pn.has(t, a)) {
      t[a] = !0;
      var u = e.node(a);
      i[u.rank].push(a), Pn.forEach(e.successors(a), o);
    }
  }
  var s = Pn.sortBy(n, function (a) {
    return e.node(a).rank;
  });
  return Pn.forEach(s, o), i;
}
var ir = we,
  n6 = r6;
function r6(e, t) {
  for (var n = 0, r = 1; r < t.length; ++r) n += i6(e, t[r - 1], t[r]);
  return n;
}
function i6(e, t, n) {
  for (
    var r = ir.zipObject(
        n,
        ir.map(n, function (l, c) {
          return c;
        }),
      ),
      i = ir.flatten(
        ir.map(t, function (l) {
          return ir.sortBy(
            ir.map(e.outEdges(l), function (c) {
              return { pos: r[c.w], weight: e.edge(c).weight };
            }),
            "pos",
          );
        }),
        !0,
      ),
      o = 1;
    o < n.length;

  )
    o <<= 1;
  var s = 2 * o - 1;
  o -= 1;
  var a = ir.map(new Array(s), function () {
      return 0;
    }),
    u = 0;
  return (
    ir.forEach(
      i.forEach(function (l) {
        var c = l.pos + o;
        a[c] += l.weight;
        for (var f = 0; c > 0; ) c % 2 && (f += a[c + 1]), (c = (c - 1) >> 1), (a[c] += l.weight);
        u += l.weight * f;
      }),
    ),
    u
  );
}
var EC = we,
  o6 = s6;
function s6(e, t) {
  return EC.map(t, function (n) {
    var r = e.inEdges(n);
    if (r.length) {
      var i = EC.reduce(
        r,
        function (o, s) {
          var a = e.edge(s),
            u = e.node(s.v);
          return { sum: o.sum + a.weight * u.order, weight: o.weight + a.weight };
        },
        { sum: 0, weight: 0 },
      );
      return { v: n, barycenter: i.sum / i.weight, weight: i.weight };
    } else return { v: n };
  });
}
var bt = we,
  a6 = u6;
function u6(e, t) {
  var n = {};
  bt.forEach(e, function (i, o) {
    var s = (n[i.v] = { indegree: 0, in: [], out: [], vs: [i.v], i: o });
    bt.isUndefined(i.barycenter) || ((s.barycenter = i.barycenter), (s.weight = i.weight));
  }),
    bt.forEach(t.edges(), function (i) {
      var o = n[i.v],
        s = n[i.w];
      !bt.isUndefined(o) && !bt.isUndefined(s) && (s.indegree++, o.out.push(n[i.w]));
    });
  var r = bt.filter(n, function (i) {
    return !i.indegree;
  });
  return l6(r);
}
function l6(e) {
  var t = [];
  function n(o) {
    return function (s) {
      s.merged ||
        ((bt.isUndefined(s.barycenter) ||
          bt.isUndefined(o.barycenter) ||
          s.barycenter >= o.barycenter) &&
          c6(o, s));
    };
  }
  function r(o) {
    return function (s) {
      s.in.push(o), --s.indegree === 0 && e.push(s);
    };
  }
  for (; e.length; ) {
    var i = e.pop();
    t.push(i), bt.forEach(i.in.reverse(), n(i)), bt.forEach(i.out, r(i));
  }
  return bt.map(
    bt.filter(t, function (o) {
      return !o.merged;
    }),
    function (o) {
      return bt.pick(o, ["vs", "i", "barycenter", "weight"]);
    },
  );
}
function c6(e, t) {
  var n = 0,
    r = 0;
  e.weight && ((n += e.barycenter * e.weight), (r += e.weight)),
    t.weight && ((n += t.barycenter * t.weight), (r += t.weight)),
    (e.vs = t.vs.concat(e.vs)),
    (e.barycenter = n / r),
    (e.weight = r),
    (e.i = Math.min(t.i, e.i)),
    (t.merged = !0);
}
var us = we,
  f6 = wt,
  d6 = h6;
function h6(e, t) {
  var n = f6.partition(e, function (c) {
      return us.has(c, "barycenter");
    }),
    r = n.lhs,
    i = us.sortBy(n.rhs, function (c) {
      return -c.i;
    }),
    o = [],
    s = 0,
    a = 0,
    u = 0;
  r.sort(p6(!!t)),
    (u = CC(o, i, u)),
    us.forEach(r, function (c) {
      (u += c.vs.length),
        o.push(c.vs),
        (s += c.barycenter * c.weight),
        (a += c.weight),
        (u = CC(o, i, u));
    });
  var l = { vs: us.flatten(o, !0) };
  return a && ((l.barycenter = s / a), (l.weight = a)), l;
}
function CC(e, t, n) {
  for (var r; t.length && (r = us.last(t)).i <= n; ) t.pop(), e.push(r.vs), n++;
  return n;
}
function p6(e) {
  return function (t, n) {
    return t.barycenter < n.barycenter
      ? -1
      : t.barycenter > n.barycenter
        ? 1
        : e
          ? n.i - t.i
          : t.i - n.i;
  };
}
var mr = we,
  m6 = o6,
  g6 = a6,
  v6 = d6,
  y6 = w2;
function w2(e, t, n, r) {
  var i = e.children(t),
    o = e.node(t),
    s = o ? o.borderLeft : void 0,
    a = o ? o.borderRight : void 0,
    u = {};
  s &&
    (i = mr.filter(i, function (v) {
      return v !== s && v !== a;
    }));
  var l = m6(e, i);
  mr.forEach(l, function (v) {
    if (e.children(v.v).length) {
      var p = w2(e, v.v, n, r);
      (u[v.v] = p), mr.has(p, "barycenter") && x6(v, p);
    }
  });
  var c = g6(l, n);
  w6(c, u);
  var f = v6(c, r);
  if (s && ((f.vs = mr.flatten([s, f.vs, a], !0)), e.predecessors(s).length)) {
    var d = e.node(e.predecessors(s)[0]),
      h = e.node(e.predecessors(a)[0]);
    mr.has(f, "barycenter") || ((f.barycenter = 0), (f.weight = 0)),
      (f.barycenter = (f.barycenter * f.weight + d.order + h.order) / (f.weight + 2)),
      (f.weight += 2);
  }
  return f;
}
function w6(e, t) {
  mr.forEach(e, function (n) {
    n.vs = mr.flatten(
      n.vs.map(function (r) {
        return t[r] ? t[r].vs : r;
      }),
      !0,
    );
  });
}
function x6(e, t) {
  mr.isUndefined(e.barycenter)
    ? ((e.barycenter = t.barycenter), (e.weight = t.weight))
    : ((e.barycenter = (e.barycenter * e.weight + t.barycenter * t.weight) / (e.weight + t.weight)),
      (e.weight += t.weight));
}
var ls = we,
  _6 = sn.Graph,
  b6 = S6;
function S6(e, t, n) {
  var r = E6(e),
    i = new _6({ compound: !0 }).setGraph({ root: r }).setDefaultNodeLabel(function (o) {
      return e.node(o);
    });
  return (
    ls.forEach(e.nodes(), function (o) {
      var s = e.node(o),
        a = e.parent(o);
      (s.rank === t || (s.minRank <= t && t <= s.maxRank)) &&
        (i.setNode(o),
        i.setParent(o, a || r),
        ls.forEach(e[n](o), function (u) {
          var l = u.v === o ? u.w : u.v,
            c = i.edge(l, o),
            f = ls.isUndefined(c) ? 0 : c.weight;
          i.setEdge(l, o, { weight: e.edge(u).weight + f });
        }),
        ls.has(s, "minRank") &&
          i.setNode(o, { borderLeft: s.borderLeft[t], borderRight: s.borderRight[t] }));
    }),
    i
  );
}
function E6(e) {
  for (var t; e.hasNode((t = ls.uniqueId("_root"))); );
  return t;
}
var C6 = we,
  T6 = k6;
function k6(e, t, n) {
  var r = {},
    i;
  C6.forEach(n, function (o) {
    for (var s = e.parent(o), a, u; s; ) {
      if (((a = e.parent(s)), a ? ((u = r[a]), (r[a] = s)) : ((u = i), (i = s)), u && u !== s)) {
        t.setEdge(u, s);
        return;
      }
      s = a;
    }
  });
}
var Rr = we,
  R6 = e6,
  P6 = n6,
  A6 = y6,
  N6 = b6,
  M6 = T6,
  I6 = sn.Graph,
  TC = wt,
  D6 = O6;
function O6(e) {
  var t = TC.maxRank(e),
    n = kC(e, Rr.range(1, t + 1), "inEdges"),
    r = kC(e, Rr.range(t - 1, -1, -1), "outEdges"),
    i = R6(e);
  RC(e, i);
  for (var o = Number.POSITIVE_INFINITY, s, a = 0, u = 0; u < 4; ++a, ++u) {
    L6(a % 2 ? n : r, a % 4 >= 2), (i = TC.buildLayerMatrix(e));
    var l = P6(e, i);
    l < o && ((u = 0), (s = Rr.cloneDeep(i)), (o = l));
  }
  RC(e, s);
}
function kC(e, t, n) {
  return Rr.map(t, function (r) {
    return N6(e, r, n);
  });
}
function L6(e, t) {
  var n = new I6();
  Rr.forEach(e, function (r) {
    var i = r.graph().root,
      o = A6(r, i, n, t);
    Rr.forEach(o.vs, function (s, a) {
      r.node(s).order = a;
    }),
      M6(r, n, o.vs);
  });
}
function RC(e, t) {
  Rr.forEach(t, function (n) {
    Rr.forEach(n, function (r, i) {
      e.node(r).order = i;
    });
  });
}
var J = we,
  F6 = sn.Graph,
  j6 = wt,
  V6 = { positionX: X6 };
function q6(e, t) {
  var n = {};
  function r(i, o) {
    var s = 0,
      a = 0,
      u = i.length,
      l = J.last(o);
    return (
      J.forEach(o, function (c, f) {
        var d = z6(e, c),
          h = d ? e.node(d).order : u;
        (d || c === l) &&
          (J.forEach(o.slice(a, f + 1), function (v) {
            J.forEach(e.predecessors(v), function (p) {
              var y = e.node(p),
                m = y.order;
              (m < s || h < m) && !(y.dummy && e.node(v).dummy) && x2(n, p, v);
            });
          }),
          (a = f + 1),
          (s = h));
      }),
      o
    );
  }
  return J.reduce(t, r), n;
}
function $6(e, t) {
  var n = {};
  function r(o, s, a, u, l) {
    var c;
    J.forEach(J.range(s, a), function (f) {
      (c = o[f]),
        e.node(c).dummy &&
          J.forEach(e.predecessors(c), function (d) {
            var h = e.node(d);
            h.dummy && (h.order < u || h.order > l) && x2(n, d, c);
          });
    });
  }
  function i(o, s) {
    var a = -1,
      u,
      l = 0;
    return (
      J.forEach(s, function (c, f) {
        if (e.node(c).dummy === "border") {
          var d = e.predecessors(c);
          d.length && ((u = e.node(d[0]).order), r(s, l, f, a, u), (l = f), (a = u));
        }
        r(s, l, s.length, u, o.length);
      }),
      s
    );
  }
  return J.reduce(t, i), n;
}
function z6(e, t) {
  if (e.node(t).dummy)
    return J.find(e.predecessors(t), function (n) {
      return e.node(n).dummy;
    });
}
function x2(e, t, n) {
  if (t > n) {
    var r = t;
    (t = n), (n = r);
  }
  var i = e[t];
  i || (e[t] = i = {}), (i[n] = !0);
}
function B6(e, t, n) {
  if (t > n) {
    var r = t;
    (t = n), (n = r);
  }
  return J.has(e[t], n);
}
function U6(e, t, n, r) {
  var i = {},
    o = {},
    s = {};
  return (
    J.forEach(t, function (a) {
      J.forEach(a, function (u, l) {
        (i[u] = u), (o[u] = u), (s[u] = l);
      });
    }),
    J.forEach(t, function (a) {
      var u = -1;
      J.forEach(a, function (l) {
        var c = r(l);
        if (c.length) {
          c = J.sortBy(c, function (p) {
            return s[p];
          });
          for (var f = (c.length - 1) / 2, d = Math.floor(f), h = Math.ceil(f); d <= h; ++d) {
            var v = c[d];
            o[l] === l &&
              u < s[v] &&
              !B6(n, l, v) &&
              ((o[v] = l), (o[l] = i[l] = i[v]), (u = s[v]));
          }
        }
      });
    }),
    { root: i, align: o }
  );
}
function H6(e, t, n, r, i) {
  var o = {},
    s = G6(e, t, n, i),
    a = i ? "borderLeft" : "borderRight";
  function u(f, d) {
    for (var h = s.nodes(), v = h.pop(), p = {}; v; )
      p[v] ? f(v) : ((p[v] = !0), h.push(v), (h = h.concat(d(v)))), (v = h.pop());
  }
  function l(f) {
    o[f] = s.inEdges(f).reduce(function (d, h) {
      return Math.max(d, o[h.v] + s.edge(h));
    }, 0);
  }
  function c(f) {
    var d = s.outEdges(f).reduce(function (v, p) {
        return Math.min(v, o[p.w] - s.edge(p));
      }, Number.POSITIVE_INFINITY),
      h = e.node(f);
    d !== Number.POSITIVE_INFINITY && h.borderType !== a && (o[f] = Math.max(o[f], d));
  }
  return (
    u(l, s.predecessors.bind(s)),
    u(c, s.successors.bind(s)),
    J.forEach(r, function (f) {
      o[f] = o[n[f]];
    }),
    o
  );
}
function G6(e, t, n, r) {
  var i = new F6(),
    o = e.graph(),
    s = Z6(o.nodesep, o.edgesep, r);
  return (
    J.forEach(t, function (a) {
      var u;
      J.forEach(a, function (l) {
        var c = n[l];
        if ((i.setNode(c), u)) {
          var f = n[u],
            d = i.edge(f, c);
          i.setEdge(f, c, Math.max(s(e, l, u), d || 0));
        }
        u = l;
      });
    }),
    i
  );
}
function W6(e, t) {
  return J.minBy(J.values(t), function (n) {
    var r = Number.NEGATIVE_INFINITY,
      i = Number.POSITIVE_INFINITY;
    return (
      J.forIn(n, function (o, s) {
        var a = Q6(e, s) / 2;
        (r = Math.max(o + a, r)), (i = Math.min(o - a, i));
      }),
      r - i
    );
  });
}
function K6(e, t) {
  var n = J.values(t),
    r = J.min(n),
    i = J.max(n);
  J.forEach(["u", "d"], function (o) {
    J.forEach(["l", "r"], function (s) {
      var a = o + s,
        u = e[a],
        l;
      if (u !== t) {
        var c = J.values(u);
        (l = s === "l" ? r - J.min(c) : i - J.max(c)),
          l &&
            (e[a] = J.mapValues(u, function (f) {
              return f + l;
            }));
      }
    });
  });
}
function Y6(e, t) {
  return J.mapValues(e.ul, function (n, r) {
    if (t) return e[t.toLowerCase()][r];
    var i = J.sortBy(J.map(e, r));
    return (i[1] + i[2]) / 2;
  });
}
function X6(e) {
  var t = j6.buildLayerMatrix(e),
    n = J.merge(q6(e, t), $6(e, t)),
    r = {},
    i;
  J.forEach(["u", "d"], function (s) {
    (i = s === "u" ? t : J.values(t).reverse()),
      J.forEach(["l", "r"], function (a) {
        a === "r" &&
          (i = J.map(i, function (f) {
            return J.values(f).reverse();
          }));
        var u = (s === "u" ? e.predecessors : e.successors).bind(e),
          l = U6(e, i, n, u),
          c = H6(e, i, l.root, l.align, a === "r");
        a === "r" &&
          (c = J.mapValues(c, function (f) {
            return -f;
          })),
          (r[s + a] = c);
      });
  });
  var o = W6(e, r);
  return K6(r, o), Y6(r, e.graph().align);
}
function Z6(e, t, n) {
  return function (r, i, o) {
    var s = r.node(i),
      a = r.node(o),
      u = 0,
      l;
    if (((u += s.width / 2), J.has(s, "labelpos")))
      switch (s.labelpos.toLowerCase()) {
        case "l":
          l = -s.width / 2;
          break;
        case "r":
          l = s.width / 2;
          break;
      }
    if (
      (l && (u += n ? l : -l),
      (l = 0),
      (u += (s.dummy ? t : e) / 2),
      (u += (a.dummy ? t : e) / 2),
      (u += a.width / 2),
      J.has(a, "labelpos"))
    )
      switch (a.labelpos.toLowerCase()) {
        case "l":
          l = a.width / 2;
          break;
        case "r":
          l = -a.width / 2;
          break;
      }
    return l && (u += n ? l : -l), (l = 0), u;
  };
}
function Q6(e, t) {
  return e.node(t).width;
}
var cs = we,
  _2 = wt,
  J6 = V6.positionX,
  eU = tU;
function tU(e) {
  (e = _2.asNonCompoundGraph(e)),
    nU(e),
    cs.forEach(J6(e), function (t, n) {
      e.node(n).x = t;
    });
}
function nU(e) {
  var t = _2.buildLayerMatrix(e),
    n = e.graph().ranksep,
    r = 0;
  cs.forEach(t, function (i) {
    var o = cs.max(
      cs.map(i, function (s) {
        return e.node(s).height;
      }),
    );
    cs.forEach(i, function (s) {
      e.node(s).y = r + o / 2;
    }),
      (r += o + n);
  });
}
var ne = we,
  PC = GB,
  AC = l8,
  rU = I8,
  iU = wt.normalizeRanks,
  oU = F8,
  sU = wt.removeEmptyRanks,
  NC = $8,
  aU = W8,
  MC = Y8,
  uU = D6,
  lU = eU,
  Nr = wt,
  cU = sn.Graph,
  fU = dU;
function dU(e, t) {
  var n = t && t.debugTiming ? Nr.time : Nr.notime;
  n("layout", function () {
    var r = n("  buildLayoutGraph", function () {
      return SU(e);
    });
    n("  runLayout", function () {
      hU(r, n);
    }),
      n("  updateInputGraph", function () {
        pU(e, r);
      });
  });
}
function hU(e, t) {
  t("    makeSpaceForEdgeLabels", function () {
    EU(e);
  }),
    t("    removeSelfEdges", function () {
      IU(e);
    }),
    t("    acyclic", function () {
      PC.run(e);
    }),
    t("    nestingGraph.run", function () {
      NC.run(e);
    }),
    t("    rank", function () {
      rU(Nr.asNonCompoundGraph(e));
    }),
    t("    injectEdgeLabelProxies", function () {
      CU(e);
    }),
    t("    removeEmptyRanks", function () {
      sU(e);
    }),
    t("    nestingGraph.cleanup", function () {
      NC.cleanup(e);
    }),
    t("    normalizeRanks", function () {
      iU(e);
    }),
    t("    assignRankMinMax", function () {
      TU(e);
    }),
    t("    removeEdgeLabelProxies", function () {
      kU(e);
    }),
    t("    normalize.run", function () {
      AC.run(e);
    }),
    t("    parentDummyChains", function () {
      oU(e);
    }),
    t("    addBorderSegments", function () {
      aU(e);
    }),
    t("    order", function () {
      uU(e);
    }),
    t("    insertSelfEdges", function () {
      DU(e);
    }),
    t("    adjustCoordinateSystem", function () {
      MC.adjust(e);
    }),
    t("    position", function () {
      lU(e);
    }),
    t("    positionSelfEdges", function () {
      OU(e);
    }),
    t("    removeBorderNodes", function () {
      MU(e);
    }),
    t("    normalize.undo", function () {
      AC.undo(e);
    }),
    t("    fixupEdgeLabelCoords", function () {
      AU(e);
    }),
    t("    undoCoordinateSystem", function () {
      MC.undo(e);
    }),
    t("    translateGraph", function () {
      RU(e);
    }),
    t("    assignNodeIntersects", function () {
      PU(e);
    }),
    t("    reversePoints", function () {
      NU(e);
    }),
    t("    acyclic.undo", function () {
      PC.undo(e);
    });
}
function pU(e, t) {
  ne.forEach(e.nodes(), function (n) {
    var r = e.node(n),
      i = t.node(n);
    r &&
      ((r.x = i.x),
      (r.y = i.y),
      t.children(n).length && ((r.width = i.width), (r.height = i.height)));
  }),
    ne.forEach(e.edges(), function (n) {
      var r = e.edge(n),
        i = t.edge(n);
      (r.points = i.points), ne.has(i, "x") && ((r.x = i.x), (r.y = i.y));
    }),
    (e.graph().width = t.graph().width),
    (e.graph().height = t.graph().height);
}
var mU = ["nodesep", "edgesep", "ranksep", "marginx", "marginy"],
  gU = { ranksep: 50, edgesep: 20, nodesep: 50, rankdir: "tb" },
  vU = ["acyclicer", "ranker", "rankdir", "align"],
  yU = ["width", "height"],
  wU = { width: 0, height: 0 },
  xU = ["minlen", "weight", "width", "height", "labeloffset"],
  _U = { minlen: 1, weight: 1, width: 0, height: 0, labeloffset: 10, labelpos: "r" },
  bU = ["labelpos"];
function SU(e) {
  var t = new cU({ multigraph: !0, compound: !0 }),
    n = ag(e.graph());
  return (
    t.setGraph(ne.merge({}, gU, sg(n, mU), ne.pick(n, vU))),
    ne.forEach(e.nodes(), function (r) {
      var i = ag(e.node(r));
      t.setNode(r, ne.defaults(sg(i, yU), wU)), t.setParent(r, e.parent(r));
    }),
    ne.forEach(e.edges(), function (r) {
      var i = ag(e.edge(r));
      t.setEdge(r, ne.merge({}, _U, sg(i, xU), ne.pick(i, bU)));
    }),
    t
  );
}
function EU(e) {
  var t = e.graph();
  (t.ranksep /= 2),
    ne.forEach(e.edges(), function (n) {
      var r = e.edge(n);
      (r.minlen *= 2),
        r.labelpos.toLowerCase() !== "c" &&
          (t.rankdir === "TB" || t.rankdir === "BT"
            ? (r.width += r.labeloffset)
            : (r.height += r.labeloffset));
    });
}
function CU(e) {
  ne.forEach(e.edges(), function (t) {
    var n = e.edge(t);
    if (n.width && n.height) {
      var r = e.node(t.v),
        i = e.node(t.w),
        o = { rank: (i.rank - r.rank) / 2 + r.rank, e: t };
      Nr.addDummyNode(e, "edge-proxy", o, "_ep");
    }
  });
}
function TU(e) {
  var t = 0;
  ne.forEach(e.nodes(), function (n) {
    var r = e.node(n);
    r.borderTop &&
      ((r.minRank = e.node(r.borderTop).rank),
      (r.maxRank = e.node(r.borderBottom).rank),
      (t = ne.max(t, r.maxRank)));
  }),
    (e.graph().maxRank = t);
}
function kU(e) {
  ne.forEach(e.nodes(), function (t) {
    var n = e.node(t);
    n.dummy === "edge-proxy" && ((e.edge(n.e).labelRank = n.rank), e.removeNode(t));
  });
}
function RU(e) {
  var t = Number.POSITIVE_INFINITY,
    n = 0,
    r = Number.POSITIVE_INFINITY,
    i = 0,
    o = e.graph(),
    s = o.marginx || 0,
    a = o.marginy || 0;
  function u(l) {
    var c = l.x,
      f = l.y,
      d = l.width,
      h = l.height;
    (t = Math.min(t, c - d / 2)),
      (n = Math.max(n, c + d / 2)),
      (r = Math.min(r, f - h / 2)),
      (i = Math.max(i, f + h / 2));
  }
  ne.forEach(e.nodes(), function (l) {
    u(e.node(l));
  }),
    ne.forEach(e.edges(), function (l) {
      var c = e.edge(l);
      ne.has(c, "x") && u(c);
    }),
    (t -= s),
    (r -= a),
    ne.forEach(e.nodes(), function (l) {
      var c = e.node(l);
      (c.x -= t), (c.y -= r);
    }),
    ne.forEach(e.edges(), function (l) {
      var c = e.edge(l);
      ne.forEach(c.points, function (f) {
        (f.x -= t), (f.y -= r);
      }),
        ne.has(c, "x") && (c.x -= t),
        ne.has(c, "y") && (c.y -= r);
    }),
    (o.width = n - t + s),
    (o.height = i - r + a);
}
function PU(e) {
  ne.forEach(e.edges(), function (t) {
    var n = e.edge(t),
      r = e.node(t.v),
      i = e.node(t.w),
      o,
      s;
    n.points
      ? ((o = n.points[0]), (s = n.points[n.points.length - 1]))
      : ((n.points = []), (o = i), (s = r)),
      n.points.unshift(Nr.intersectRect(r, o)),
      n.points.push(Nr.intersectRect(i, s));
  });
}
function AU(e) {
  ne.forEach(e.edges(), function (t) {
    var n = e.edge(t);
    if (ne.has(n, "x"))
      switch (
        ((n.labelpos === "l" || n.labelpos === "r") && (n.width -= n.labeloffset), n.labelpos)
      ) {
        case "l":
          n.x -= n.width / 2 + n.labeloffset;
          break;
        case "r":
          n.x += n.width / 2 + n.labeloffset;
          break;
      }
  });
}
function NU(e) {
  ne.forEach(e.edges(), function (t) {
    var n = e.edge(t);
    n.reversed && n.points.reverse();
  });
}
function MU(e) {
  ne.forEach(e.nodes(), function (t) {
    if (e.children(t).length) {
      var n = e.node(t),
        r = e.node(n.borderTop),
        i = e.node(n.borderBottom),
        o = e.node(ne.last(n.borderLeft)),
        s = e.node(ne.last(n.borderRight));
      (n.width = Math.abs(s.x - o.x)),
        (n.height = Math.abs(i.y - r.y)),
        (n.x = o.x + n.width / 2),
        (n.y = r.y + n.height / 2);
    }
  }),
    ne.forEach(e.nodes(), function (t) {
      e.node(t).dummy === "border" && e.removeNode(t);
    });
}
function IU(e) {
  ne.forEach(e.edges(), function (t) {
    if (t.v === t.w) {
      var n = e.node(t.v);
      n.selfEdges || (n.selfEdges = []),
        n.selfEdges.push({ e: t, label: e.edge(t) }),
        e.removeEdge(t);
    }
  });
}
function DU(e) {
  var t = Nr.buildLayerMatrix(e);
  ne.forEach(t, function (n) {
    var r = 0;
    ne.forEach(n, function (i, o) {
      var s = e.node(i);
      (s.order = o + r),
        ne.forEach(s.selfEdges, function (a) {
          Nr.addDummyNode(
            e,
            "selfedge",
            {
              width: a.label.width,
              height: a.label.height,
              rank: s.rank,
              order: o + ++r,
              e: a.e,
              label: a.label,
            },
            "_se",
          );
        }),
        delete s.selfEdges;
    });
  });
}
function OU(e) {
  ne.forEach(e.nodes(), function (t) {
    var n = e.node(t);
    if (n.dummy === "selfedge") {
      var r = e.node(n.e.v),
        i = r.x + r.width / 2,
        o = r.y,
        s = n.x - i,
        a = r.height / 2;
      e.setEdge(n.e, n.label),
        e.removeNode(t),
        (n.label.points = [
          { x: i + (2 * s) / 3, y: o - a },
          { x: i + (5 * s) / 6, y: o - a },
          { x: i + s, y: o },
          { x: i + (5 * s) / 6, y: o + a },
          { x: i + (2 * s) / 3, y: o + a },
        ]),
        (n.label.x = n.x),
        (n.label.y = n.y);
    }
  });
}
function sg(e, t) {
  return ne.mapValues(ne.pick(e, t), Number);
}
function ag(e) {
  var t = {};
  return (
    ne.forEach(e, function (n, r) {
      t[r.toLowerCase()] = n;
    }),
    t
  );
}
var tu = we,
  LU = wt,
  FU = sn.Graph,
  jU = { debugOrdering: VU };
function VU(e) {
  var t = LU.buildLayerMatrix(e),
    n = new FU({ compound: !0, multigraph: !0 }).setGraph({});
  return (
    tu.forEach(e.nodes(), function (r) {
      n.setNode(r, { label: r }), n.setParent(r, "layer" + e.node(r).rank);
    }),
    tu.forEach(e.edges(), function (r) {
      n.setEdge(r.v, r.w, {}, r.name);
    }),
    tu.forEach(t, function (r, i) {
      var o = "layer" + i;
      n.setNode(o, { rank: "same" }),
        tu.reduce(r, function (s, a) {
          return n.setEdge(s, a, { style: "invis" }), a;
        });
    }),
    n
  );
}
var qU = "0.8.5",
  b2 = {
    graphlib: sn,
    layout: fU,
    debug: jU,
    util: { time: wt.time, notime: wt.notime },
    version: qU,
  };
const hn = new b2.graphlib.Graph({ compound: !0 });
hn.setDefaultEdgeLabel(() => ({}));
hn.setGraph({ rankdir: "TB", nodesep: 40, ranksep: 60 });
const IC = 250,
  DC = 60,
  $U = (e, t = {}) => {
    const n = [],
      r = [],
      i = e.id;
    function o(c, f, d) {
      const h = d ? `${d}.${c}` : c,
        v = !!f.states,
        p = d ? (v ? "compoundStateNode" : "stateNode") : "rootNode";
      if (
        (n.push({
          id: h,
          type: p,
          data: { label: c, definition: f, machineId: i, ...(d ? {} : { context: t }) },
          position: { x: 0, y: 0 },
          ...(d && { parentNode: d, extent: "parent" }),
        }),
        hn.setNode(h, { width: IC, height: DC }),
        d && hn.setParent(h, d),
        f.on)
      ) {
        const y = Array.isArray(f.on) ? f.on : Object.entries(f.on);
        for (const [m, g] of y) {
          const w = Array.isArray(g) ? g : [g];
          for (const x of w) {
            const b = typeof x == "string" ? x : x.target;
            if (b) {
              const E = b.startsWith(".")
                ? d + b
                : `${i}${b.startsWith("#") ? "" : "."}${b.replace("#", "")}`;
              r.push({
                id: `e-${h}-${E}-${m}`,
                source: h,
                target: E,
                type: "transitionEdge",
                data: { label: m, actions: x.actions },
                markerEnd: { type: go.ArrowClosed, color: "#a1a1aa" },
              }),
                hn.setEdge(h, E);
            }
          }
        }
      }
      if (f.initial) {
        const y = `${h}.__initial__`,
          m = `${h}.${f.initial}`;
        n.push({
          id: y,
          type: "initialNode",
          position: { x: 0, y: 0 },
          parentNode: h,
          data: { label: "" },
        }),
          r.push({
            id: `e-${y}-${m}`,
            source: y,
            target: m,
            type: "transitionEdge",
            data: { label: "" },
          }),
          hn.setNode(y, { width: 24, height: 24 }),
          hn.setEdge(y, m);
      }
      if (f.states) for (const y in f.states) o(y, f.states[y], h);
    }
    o(e.id, e),
      b2.layout(hn),
      n.forEach((c) => {
        const f = hn.node(c.id);
        f && (c.position = { x: f.x - f.width / 2, y: f.y - f.height / 2 });
      });
    const s = i,
      a = 40,
      u = n.find((c) => c.id === s),
      l = n.filter((c) => c.parentNode === s);
    if (u && l.length > 0) {
      let c = 1 / 0,
        f = 1 / 0,
        d = -1 / 0,
        h = -1 / 0;
      l.forEach((v) => {
        const p = hn.node(v.id),
          y = (p == null ? void 0 : p.width) ?? IC,
          m = (p == null ? void 0 : p.height) ?? DC;
        (c = Math.min(c, v.position.x)),
          (f = Math.min(f, v.position.y)),
          (d = Math.max(d, v.position.x + y)),
          (h = Math.max(h, v.position.y + m));
      }),
        (u.position = { x: c - a / 2, y: f - a / 2 }),
        (u.style = { width: d - c + a, height: h - f + a }),
        l.forEach((v) => {
          (v.position.x -= u.position.x), (v.position.y -= u.position.y);
        });
    }
    return { nodes: n, edges: r };
  };
function S2(e) {
  var t,
    n,
    r = "";
  if (typeof e == "string" || typeof e == "number") r += e;
  else if (typeof e == "object")
    if (Array.isArray(e)) {
      var i = e.length;
      for (t = 0; t < i; t++) e[t] && (n = S2(e[t])) && (r && (r += " "), (r += n));
    } else for (n in e) e[n] && (r && (r += " "), (r += n));
  return r;
}
function E2() {
  for (var e, t, n = 0, r = "", i = arguments.length; n < i; n++)
    (e = arguments[n]) && (t = S2(e)) && (r && (r += " "), (r += t));
  return r;
}
const V0 = "-",
  zU = (e) => {
    const t = UU(e),
      { conflictingClassGroups: n, conflictingClassGroupModifiers: r } = e;
    return {
      getClassGroupId: (s) => {
        const a = s.split(V0);
        return a[0] === "" && a.length !== 1 && a.shift(), C2(a, t) || BU(s);
      },
      getConflictingClassGroupIds: (s, a) => {
        const u = n[s] || [];
        return a && r[s] ? [...u, ...r[s]] : u;
      },
    };
  },
  C2 = (e, t) => {
    var s;
    if (e.length === 0) return t.classGroupId;
    const n = e[0],
      r = t.nextPart.get(n),
      i = r ? C2(e.slice(1), r) : void 0;
    if (i) return i;
    if (t.validators.length === 0) return;
    const o = e.join(V0);
    return (s = t.validators.find(({ validator: a }) => a(o))) == null ? void 0 : s.classGroupId;
  },
  OC = /^\[(.+)\]$/,
  BU = (e) => {
    if (OC.test(e)) {
      const t = OC.exec(e)[1],
        n = t == null ? void 0 : t.substring(0, t.indexOf(":"));
      if (n) return "arbitrary.." + n;
    }
  },
  UU = (e) => {
    const { theme: t, prefix: n } = e,
      r = { nextPart: new Map(), validators: [] };
    return (
      GU(Object.entries(e.classGroups), n).forEach(([o, s]) => {
        $v(s, r, o, t);
      }),
      r
    );
  },
  $v = (e, t, n, r) => {
    e.forEach((i) => {
      if (typeof i == "string") {
        const o = i === "" ? t : LC(t, i);
        o.classGroupId = n;
        return;
      }
      if (typeof i == "function") {
        if (HU(i)) {
          $v(i(r), t, n, r);
          return;
        }
        t.validators.push({ validator: i, classGroupId: n });
        return;
      }
      Object.entries(i).forEach(([o, s]) => {
        $v(s, LC(t, o), n, r);
      });
    });
  },
  LC = (e, t) => {
    let n = e;
    return (
      t.split(V0).forEach((r) => {
        n.nextPart.has(r) || n.nextPart.set(r, { nextPart: new Map(), validators: [] }),
          (n = n.nextPart.get(r));
      }),
      n
    );
  },
  HU = (e) => e.isThemeGetter,
  GU = (e, t) =>
    t
      ? e.map(([n, r]) => {
          const i = r.map((o) =>
            typeof o == "string"
              ? t + o
              : typeof o == "object"
                ? Object.fromEntries(Object.entries(o).map(([s, a]) => [t + s, a]))
                : o,
          );
          return [n, i];
        })
      : e,
  WU = (e) => {
    if (e < 1) return { get: () => {}, set: () => {} };
    let t = 0,
      n = new Map(),
      r = new Map();
    const i = (o, s) => {
      n.set(o, s), t++, t > e && ((t = 0), (r = n), (n = new Map()));
    };
    return {
      get(o) {
        let s = n.get(o);
        if (s !== void 0) return s;
        if ((s = r.get(o)) !== void 0) return i(o, s), s;
      },
      set(o, s) {
        n.has(o) ? n.set(o, s) : i(o, s);
      },
    };
  },
  T2 = "!",
  KU = (e) => {
    const { separator: t, experimentalParseClassName: n } = e,
      r = t.length === 1,
      i = t[0],
      o = t.length,
      s = (a) => {
        const u = [];
        let l = 0,
          c = 0,
          f;
        for (let y = 0; y < a.length; y++) {
          let m = a[y];
          if (l === 0) {
            if (m === i && (r || a.slice(y, y + o) === t)) {
              u.push(a.slice(c, y)), (c = y + o);
              continue;
            }
            if (m === "/") {
              f = y;
              continue;
            }
          }
          m === "[" ? l++ : m === "]" && l--;
        }
        const d = u.length === 0 ? a : a.substring(c),
          h = d.startsWith(T2),
          v = h ? d.substring(1) : d,
          p = f && f > c ? f - c : void 0;
        return {
          modifiers: u,
          hasImportantModifier: h,
          baseClassName: v,
          maybePostfixModifierPosition: p,
        };
      };
    return n ? (a) => n({ className: a, parseClassName: s }) : s;
  },
  YU = (e) => {
    if (e.length <= 1) return e;
    const t = [];
    let n = [];
    return (
      e.forEach((r) => {
        r[0] === "[" ? (t.push(...n.sort(), r), (n = [])) : n.push(r);
      }),
      t.push(...n.sort()),
      t
    );
  },
  XU = (e) => ({ cache: WU(e.cacheSize), parseClassName: KU(e), ...zU(e) }),
  ZU = /\s+/,
  QU = (e, t) => {
    const { parseClassName: n, getClassGroupId: r, getConflictingClassGroupIds: i } = t,
      o = [],
      s = e.trim().split(ZU);
    let a = "";
    for (let u = s.length - 1; u >= 0; u -= 1) {
      const l = s[u],
        {
          modifiers: c,
          hasImportantModifier: f,
          baseClassName: d,
          maybePostfixModifierPosition: h,
        } = n(l);
      let v = !!h,
        p = r(v ? d.substring(0, h) : d);
      if (!p) {
        if (!v) {
          a = l + (a.length > 0 ? " " + a : a);
          continue;
        }
        if (((p = r(d)), !p)) {
          a = l + (a.length > 0 ? " " + a : a);
          continue;
        }
        v = !1;
      }
      const y = YU(c).join(":"),
        m = f ? y + T2 : y,
        g = m + p;
      if (o.includes(g)) continue;
      o.push(g);
      const w = i(p, v);
      for (let x = 0; x < w.length; ++x) {
        const b = w[x];
        o.push(m + b);
      }
      a = l + (a.length > 0 ? " " + a : a);
    }
    return a;
  };
function JU() {
  let e = 0,
    t,
    n,
    r = "";
  for (; e < arguments.length; ) (t = arguments[e++]) && (n = k2(t)) && (r && (r += " "), (r += n));
  return r;
}
const k2 = (e) => {
  if (typeof e == "string") return e;
  let t,
    n = "";
  for (let r = 0; r < e.length; r++) e[r] && (t = k2(e[r])) && (n && (n += " "), (n += t));
  return n;
};
function eH(e, ...t) {
  let n,
    r,
    i,
    o = s;
  function s(u) {
    const l = t.reduce((c, f) => f(c), e());
    return (n = XU(l)), (r = n.cache.get), (i = n.cache.set), (o = a), a(u);
  }
  function a(u) {
    const l = r(u);
    if (l) return l;
    const c = QU(u, n);
    return i(u, c), c;
  }
  return function () {
    return o(JU.apply(null, arguments));
  };
}
const pe = (e) => {
    const t = (n) => n[e] || [];
    return (t.isThemeGetter = !0), t;
  },
  R2 = /^\[(?:([a-z-]+):)?(.+)\]$/i,
  tH = /^\d+\/\d+$/,
  nH = new Set(["px", "full", "screen"]),
  rH = /^(\d+(\.\d+)?)?(xs|sm|md|lg|xl)$/,
  iH =
    /\d+(%|px|r?em|[sdl]?v([hwib]|min|max)|pt|pc|in|cm|mm|cap|ch|ex|r?lh|cq(w|h|i|b|min|max))|\b(calc|min|max|clamp)\(.+\)|^0$/,
  oH = /^(rgba?|hsla?|hwb|(ok)?(lab|lch))\(.+\)$/,
  sH = /^(inset_)?-?((\d+)?\.?(\d+)[a-z]+|0)_-?((\d+)?\.?(\d+)[a-z]+|0)/,
  aH =
    /^(url|image|image-set|cross-fade|element|(repeating-)?(linear|radial|conic)-gradient)\(.+\)$/,
  An = (e) => to(e) || nH.has(e) || tH.test(e),
  or = (e) => No(e, "length", mH),
  to = (e) => !!e && !Number.isNaN(Number(e)),
  ug = (e) => No(e, "number", to),
  Yo = (e) => !!e && Number.isInteger(Number(e)),
  uH = (e) => e.endsWith("%") && to(e.slice(0, -1)),
  te = (e) => R2.test(e),
  sr = (e) => rH.test(e),
  lH = new Set(["length", "size", "percentage"]),
  cH = (e) => No(e, lH, P2),
  fH = (e) => No(e, "position", P2),
  dH = new Set(["image", "url"]),
  hH = (e) => No(e, dH, vH),
  pH = (e) => No(e, "", gH),
  Xo = () => !0,
  No = (e, t, n) => {
    const r = R2.exec(e);
    return r ? (r[1] ? (typeof t == "string" ? r[1] === t : t.has(r[1])) : n(r[2])) : !1;
  },
  mH = (e) => iH.test(e) && !oH.test(e),
  P2 = () => !1,
  gH = (e) => sH.test(e),
  vH = (e) => aH.test(e),
  yH = () => {
    const e = pe("colors"),
      t = pe("spacing"),
      n = pe("blur"),
      r = pe("brightness"),
      i = pe("borderColor"),
      o = pe("borderRadius"),
      s = pe("borderSpacing"),
      a = pe("borderWidth"),
      u = pe("contrast"),
      l = pe("grayscale"),
      c = pe("hueRotate"),
      f = pe("invert"),
      d = pe("gap"),
      h = pe("gradientColorStops"),
      v = pe("gradientColorStopPositions"),
      p = pe("inset"),
      y = pe("margin"),
      m = pe("opacity"),
      g = pe("padding"),
      w = pe("saturate"),
      x = pe("scale"),
      b = pe("sepia"),
      E = pe("skew"),
      C = pe("space"),
      T = pe("translate"),
      P = () => ["auto", "contain", "none"],
      M = () => ["auto", "hidden", "clip", "visible", "scroll"],
      I = () => ["auto", te, t],
      j = () => [te, t],
      q = () => ["", An, or],
      S = () => ["auto", to, te],
      O = () => [
        "bottom",
        "center",
        "left",
        "left-bottom",
        "left-top",
        "right",
        "right-bottom",
        "right-top",
        "top",
      ],
      A = () => ["solid", "dashed", "dotted", "double", "none"],
      F = () => [
        "normal",
        "multiply",
        "screen",
        "overlay",
        "darken",
        "lighten",
        "color-dodge",
        "color-burn",
        "hard-light",
        "soft-light",
        "difference",
        "exclusion",
        "hue",
        "saturation",
        "color",
        "luminosity",
      ],
      N = () => ["start", "end", "center", "between", "around", "evenly", "stretch"],
      k = () => ["", "0", te],
      D = () => ["auto", "avoid", "all", "avoid-page", "page", "left", "right", "column"],
      V = () => [to, te];
    return {
      cacheSize: 500,
      separator: ":",
      theme: {
        colors: [Xo],
        spacing: [An, or],
        blur: ["none", "", sr, te],
        brightness: V(),
        borderColor: [e],
        borderRadius: ["none", "", "full", sr, te],
        borderSpacing: j(),
        borderWidth: q(),
        contrast: V(),
        grayscale: k(),
        hueRotate: V(),
        invert: k(),
        gap: j(),
        gradientColorStops: [e],
        gradientColorStopPositions: [uH, or],
        inset: I(),
        margin: I(),
        opacity: V(),
        padding: j(),
        saturate: V(),
        scale: V(),
        sepia: k(),
        skew: V(),
        space: j(),
        translate: j(),
      },
      classGroups: {
        aspect: [{ aspect: ["auto", "square", "video", te] }],
        container: ["container"],
        columns: [{ columns: [sr] }],
        "break-after": [{ "break-after": D() }],
        "break-before": [{ "break-before": D() }],
        "break-inside": [{ "break-inside": ["auto", "avoid", "avoid-page", "avoid-column"] }],
        "box-decoration": [{ "box-decoration": ["slice", "clone"] }],
        box: [{ box: ["border", "content"] }],
        display: [
          "block",
          "inline-block",
          "inline",
          "flex",
          "inline-flex",
          "table",
          "inline-table",
          "table-caption",
          "table-cell",
          "table-column",
          "table-column-group",
          "table-footer-group",
          "table-header-group",
          "table-row-group",
          "table-row",
          "flow-root",
          "grid",
          "inline-grid",
          "contents",
          "list-item",
          "hidden",
        ],
        float: [{ float: ["right", "left", "none", "start", "end"] }],
        clear: [{ clear: ["left", "right", "both", "none", "start", "end"] }],
        isolation: ["isolate", "isolation-auto"],
        "object-fit": [{ object: ["contain", "cover", "fill", "none", "scale-down"] }],
        "object-position": [{ object: [...O(), te] }],
        overflow: [{ overflow: M() }],
        "overflow-x": [{ "overflow-x": M() }],
        "overflow-y": [{ "overflow-y": M() }],
        overscroll: [{ overscroll: P() }],
        "overscroll-x": [{ "overscroll-x": P() }],
        "overscroll-y": [{ "overscroll-y": P() }],
        position: ["static", "fixed", "absolute", "relative", "sticky"],
        inset: [{ inset: [p] }],
        "inset-x": [{ "inset-x": [p] }],
        "inset-y": [{ "inset-y": [p] }],
        start: [{ start: [p] }],
        end: [{ end: [p] }],
        top: [{ top: [p] }],
        right: [{ right: [p] }],
        bottom: [{ bottom: [p] }],
        left: [{ left: [p] }],
        visibility: ["visible", "invisible", "collapse"],
        z: [{ z: ["auto", Yo, te] }],
        basis: [{ basis: I() }],
        "flex-direction": [{ flex: ["row", "row-reverse", "col", "col-reverse"] }],
        "flex-wrap": [{ flex: ["wrap", "wrap-reverse", "nowrap"] }],
        flex: [{ flex: ["1", "auto", "initial", "none", te] }],
        grow: [{ grow: k() }],
        shrink: [{ shrink: k() }],
        order: [{ order: ["first", "last", "none", Yo, te] }],
        "grid-cols": [{ "grid-cols": [Xo] }],
        "col-start-end": [{ col: ["auto", { span: ["full", Yo, te] }, te] }],
        "col-start": [{ "col-start": S() }],
        "col-end": [{ "col-end": S() }],
        "grid-rows": [{ "grid-rows": [Xo] }],
        "row-start-end": [{ row: ["auto", { span: [Yo, te] }, te] }],
        "row-start": [{ "row-start": S() }],
        "row-end": [{ "row-end": S() }],
        "grid-flow": [{ "grid-flow": ["row", "col", "dense", "row-dense", "col-dense"] }],
        "auto-cols": [{ "auto-cols": ["auto", "min", "max", "fr", te] }],
        "auto-rows": [{ "auto-rows": ["auto", "min", "max", "fr", te] }],
        gap: [{ gap: [d] }],
        "gap-x": [{ "gap-x": [d] }],
        "gap-y": [{ "gap-y": [d] }],
        "justify-content": [{ justify: ["normal", ...N()] }],
        "justify-items": [{ "justify-items": ["start", "end", "center", "stretch"] }],
        "justify-self": [{ "justify-self": ["auto", "start", "end", "center", "stretch"] }],
        "align-content": [{ content: ["normal", ...N(), "baseline"] }],
        "align-items": [{ items: ["start", "end", "center", "baseline", "stretch"] }],
        "align-self": [{ self: ["auto", "start", "end", "center", "stretch", "baseline"] }],
        "place-content": [{ "place-content": [...N(), "baseline"] }],
        "place-items": [{ "place-items": ["start", "end", "center", "baseline", "stretch"] }],
        "place-self": [{ "place-self": ["auto", "start", "end", "center", "stretch"] }],
        p: [{ p: [g] }],
        px: [{ px: [g] }],
        py: [{ py: [g] }],
        ps: [{ ps: [g] }],
        pe: [{ pe: [g] }],
        pt: [{ pt: [g] }],
        pr: [{ pr: [g] }],
        pb: [{ pb: [g] }],
        pl: [{ pl: [g] }],
        m: [{ m: [y] }],
        mx: [{ mx: [y] }],
        my: [{ my: [y] }],
        ms: [{ ms: [y] }],
        me: [{ me: [y] }],
        mt: [{ mt: [y] }],
        mr: [{ mr: [y] }],
        mb: [{ mb: [y] }],
        ml: [{ ml: [y] }],
        "space-x": [{ "space-x": [C] }],
        "space-x-reverse": ["space-x-reverse"],
        "space-y": [{ "space-y": [C] }],
        "space-y-reverse": ["space-y-reverse"],
        w: [{ w: ["auto", "min", "max", "fit", "svw", "lvw", "dvw", te, t] }],
        "min-w": [{ "min-w": [te, t, "min", "max", "fit"] }],
        "max-w": [
          { "max-w": [te, t, "none", "full", "min", "max", "fit", "prose", { screen: [sr] }, sr] },
        ],
        h: [{ h: [te, t, "auto", "min", "max", "fit", "svh", "lvh", "dvh"] }],
        "min-h": [{ "min-h": [te, t, "min", "max", "fit", "svh", "lvh", "dvh"] }],
        "max-h": [{ "max-h": [te, t, "min", "max", "fit", "svh", "lvh", "dvh"] }],
        size: [{ size: [te, t, "auto", "min", "max", "fit"] }],
        "font-size": [{ text: ["base", sr, or] }],
        "font-smoothing": ["antialiased", "subpixel-antialiased"],
        "font-style": ["italic", "not-italic"],
        "font-weight": [
          {
            font: [
              "thin",
              "extralight",
              "light",
              "normal",
              "medium",
              "semibold",
              "bold",
              "extrabold",
              "black",
              ug,
            ],
          },
        ],
        "font-family": [{ font: [Xo] }],
        "fvn-normal": ["normal-nums"],
        "fvn-ordinal": ["ordinal"],
        "fvn-slashed-zero": ["slashed-zero"],
        "fvn-figure": ["lining-nums", "oldstyle-nums"],
        "fvn-spacing": ["proportional-nums", "tabular-nums"],
        "fvn-fraction": ["diagonal-fractions", "stacked-fractions"],
        tracking: [{ tracking: ["tighter", "tight", "normal", "wide", "wider", "widest", te] }],
        "line-clamp": [{ "line-clamp": ["none", to, ug] }],
        leading: [{ leading: ["none", "tight", "snug", "normal", "relaxed", "loose", An, te] }],
        "list-image": [{ "list-image": ["none", te] }],
        "list-style-type": [{ list: ["none", "disc", "decimal", te] }],
        "list-style-position": [{ list: ["inside", "outside"] }],
        "placeholder-color": [{ placeholder: [e] }],
        "placeholder-opacity": [{ "placeholder-opacity": [m] }],
        "text-alignment": [{ text: ["left", "center", "right", "justify", "start", "end"] }],
        "text-color": [{ text: [e] }],
        "text-opacity": [{ "text-opacity": [m] }],
        "text-decoration": ["underline", "overline", "line-through", "no-underline"],
        "text-decoration-style": [{ decoration: [...A(), "wavy"] }],
        "text-decoration-thickness": [{ decoration: ["auto", "from-font", An, or] }],
        "underline-offset": [{ "underline-offset": ["auto", An, te] }],
        "text-decoration-color": [{ decoration: [e] }],
        "text-transform": ["uppercase", "lowercase", "capitalize", "normal-case"],
        "text-overflow": ["truncate", "text-ellipsis", "text-clip"],
        "text-wrap": [{ text: ["wrap", "nowrap", "balance", "pretty"] }],
        indent: [{ indent: j() }],
        "vertical-align": [
          {
            align: [
              "baseline",
              "top",
              "middle",
              "bottom",
              "text-top",
              "text-bottom",
              "sub",
              "super",
              te,
            ],
          },
        ],
        whitespace: [
          { whitespace: ["normal", "nowrap", "pre", "pre-line", "pre-wrap", "break-spaces"] },
        ],
        break: [{ break: ["normal", "words", "all", "keep"] }],
        hyphens: [{ hyphens: ["none", "manual", "auto"] }],
        content: [{ content: ["none", te] }],
        "bg-attachment": [{ bg: ["fixed", "local", "scroll"] }],
        "bg-clip": [{ "bg-clip": ["border", "padding", "content", "text"] }],
        "bg-opacity": [{ "bg-opacity": [m] }],
        "bg-origin": [{ "bg-origin": ["border", "padding", "content"] }],
        "bg-position": [{ bg: [...O(), fH] }],
        "bg-repeat": [{ bg: ["no-repeat", { repeat: ["", "x", "y", "round", "space"] }] }],
        "bg-size": [{ bg: ["auto", "cover", "contain", cH] }],
        "bg-image": [
          { bg: ["none", { "gradient-to": ["t", "tr", "r", "br", "b", "bl", "l", "tl"] }, hH] },
        ],
        "bg-color": [{ bg: [e] }],
        "gradient-from-pos": [{ from: [v] }],
        "gradient-via-pos": [{ via: [v] }],
        "gradient-to-pos": [{ to: [v] }],
        "gradient-from": [{ from: [h] }],
        "gradient-via": [{ via: [h] }],
        "gradient-to": [{ to: [h] }],
        rounded: [{ rounded: [o] }],
        "rounded-s": [{ "rounded-s": [o] }],
        "rounded-e": [{ "rounded-e": [o] }],
        "rounded-t": [{ "rounded-t": [o] }],
        "rounded-r": [{ "rounded-r": [o] }],
        "rounded-b": [{ "rounded-b": [o] }],
        "rounded-l": [{ "rounded-l": [o] }],
        "rounded-ss": [{ "rounded-ss": [o] }],
        "rounded-se": [{ "rounded-se": [o] }],
        "rounded-ee": [{ "rounded-ee": [o] }],
        "rounded-es": [{ "rounded-es": [o] }],
        "rounded-tl": [{ "rounded-tl": [o] }],
        "rounded-tr": [{ "rounded-tr": [o] }],
        "rounded-br": [{ "rounded-br": [o] }],
        "rounded-bl": [{ "rounded-bl": [o] }],
        "border-w": [{ border: [a] }],
        "border-w-x": [{ "border-x": [a] }],
        "border-w-y": [{ "border-y": [a] }],
        "border-w-s": [{ "border-s": [a] }],
        "border-w-e": [{ "border-e": [a] }],
        "border-w-t": [{ "border-t": [a] }],
        "border-w-r": [{ "border-r": [a] }],
        "border-w-b": [{ "border-b": [a] }],
        "border-w-l": [{ "border-l": [a] }],
        "border-opacity": [{ "border-opacity": [m] }],
        "border-style": [{ border: [...A(), "hidden"] }],
        "divide-x": [{ "divide-x": [a] }],
        "divide-x-reverse": ["divide-x-reverse"],
        "divide-y": [{ "divide-y": [a] }],
        "divide-y-reverse": ["divide-y-reverse"],
        "divide-opacity": [{ "divide-opacity": [m] }],
        "divide-style": [{ divide: A() }],
        "border-color": [{ border: [i] }],
        "border-color-x": [{ "border-x": [i] }],
        "border-color-y": [{ "border-y": [i] }],
        "border-color-s": [{ "border-s": [i] }],
        "border-color-e": [{ "border-e": [i] }],
        "border-color-t": [{ "border-t": [i] }],
        "border-color-r": [{ "border-r": [i] }],
        "border-color-b": [{ "border-b": [i] }],
        "border-color-l": [{ "border-l": [i] }],
        "divide-color": [{ divide: [i] }],
        "outline-style": [{ outline: ["", ...A()] }],
        "outline-offset": [{ "outline-offset": [An, te] }],
        "outline-w": [{ outline: [An, or] }],
        "outline-color": [{ outline: [e] }],
        "ring-w": [{ ring: q() }],
        "ring-w-inset": ["ring-inset"],
        "ring-color": [{ ring: [e] }],
        "ring-opacity": [{ "ring-opacity": [m] }],
        "ring-offset-w": [{ "ring-offset": [An, or] }],
        "ring-offset-color": [{ "ring-offset": [e] }],
        shadow: [{ shadow: ["", "inner", "none", sr, pH] }],
        "shadow-color": [{ shadow: [Xo] }],
        opacity: [{ opacity: [m] }],
        "mix-blend": [{ "mix-blend": [...F(), "plus-lighter", "plus-darker"] }],
        "bg-blend": [{ "bg-blend": F() }],
        filter: [{ filter: ["", "none"] }],
        blur: [{ blur: [n] }],
        brightness: [{ brightness: [r] }],
        contrast: [{ contrast: [u] }],
        "drop-shadow": [{ "drop-shadow": ["", "none", sr, te] }],
        grayscale: [{ grayscale: [l] }],
        "hue-rotate": [{ "hue-rotate": [c] }],
        invert: [{ invert: [f] }],
        saturate: [{ saturate: [w] }],
        sepia: [{ sepia: [b] }],
        "backdrop-filter": [{ "backdrop-filter": ["", "none"] }],
        "backdrop-blur": [{ "backdrop-blur": [n] }],
        "backdrop-brightness": [{ "backdrop-brightness": [r] }],
        "backdrop-contrast": [{ "backdrop-contrast": [u] }],
        "backdrop-grayscale": [{ "backdrop-grayscale": [l] }],
        "backdrop-hue-rotate": [{ "backdrop-hue-rotate": [c] }],
        "backdrop-invert": [{ "backdrop-invert": [f] }],
        "backdrop-opacity": [{ "backdrop-opacity": [m] }],
        "backdrop-saturate": [{ "backdrop-saturate": [w] }],
        "backdrop-sepia": [{ "backdrop-sepia": [b] }],
        "border-collapse": [{ border: ["collapse", "separate"] }],
        "border-spacing": [{ "border-spacing": [s] }],
        "border-spacing-x": [{ "border-spacing-x": [s] }],
        "border-spacing-y": [{ "border-spacing-y": [s] }],
        "table-layout": [{ table: ["auto", "fixed"] }],
        caption: [{ caption: ["top", "bottom"] }],
        transition: [
          { transition: ["none", "all", "", "colors", "opacity", "shadow", "transform", te] },
        ],
        duration: [{ duration: V() }],
        ease: [{ ease: ["linear", "in", "out", "in-out", te] }],
        delay: [{ delay: V() }],
        animate: [{ animate: ["none", "spin", "ping", "pulse", "bounce", te] }],
        transform: [{ transform: ["", "gpu", "none"] }],
        scale: [{ scale: [x] }],
        "scale-x": [{ "scale-x": [x] }],
        "scale-y": [{ "scale-y": [x] }],
        rotate: [{ rotate: [Yo, te] }],
        "translate-x": [{ "translate-x": [T] }],
        "translate-y": [{ "translate-y": [T] }],
        "skew-x": [{ "skew-x": [E] }],
        "skew-y": [{ "skew-y": [E] }],
        "transform-origin": [
          {
            origin: [
              "center",
              "top",
              "top-right",
              "right",
              "bottom-right",
              "bottom",
              "bottom-left",
              "left",
              "top-left",
              te,
            ],
          },
        ],
        accent: [{ accent: ["auto", e] }],
        appearance: [{ appearance: ["none", "auto"] }],
        cursor: [
          {
            cursor: [
              "auto",
              "default",
              "pointer",
              "wait",
              "text",
              "move",
              "help",
              "not-allowed",
              "none",
              "context-menu",
              "progress",
              "cell",
              "crosshair",
              "vertical-text",
              "alias",
              "copy",
              "no-drop",
              "grab",
              "grabbing",
              "all-scroll",
              "col-resize",
              "row-resize",
              "n-resize",
              "e-resize",
              "s-resize",
              "w-resize",
              "ne-resize",
              "nw-resize",
              "se-resize",
              "sw-resize",
              "ew-resize",
              "ns-resize",
              "nesw-resize",
              "nwse-resize",
              "zoom-in",
              "zoom-out",
              te,
            ],
          },
        ],
        "caret-color": [{ caret: [e] }],
        "pointer-events": [{ "pointer-events": ["none", "auto"] }],
        resize: [{ resize: ["none", "y", "x", ""] }],
        "scroll-behavior": [{ scroll: ["auto", "smooth"] }],
        "scroll-m": [{ "scroll-m": j() }],
        "scroll-mx": [{ "scroll-mx": j() }],
        "scroll-my": [{ "scroll-my": j() }],
        "scroll-ms": [{ "scroll-ms": j() }],
        "scroll-me": [{ "scroll-me": j() }],
        "scroll-mt": [{ "scroll-mt": j() }],
        "scroll-mr": [{ "scroll-mr": j() }],
        "scroll-mb": [{ "scroll-mb": j() }],
        "scroll-ml": [{ "scroll-ml": j() }],
        "scroll-p": [{ "scroll-p": j() }],
        "scroll-px": [{ "scroll-px": j() }],
        "scroll-py": [{ "scroll-py": j() }],
        "scroll-ps": [{ "scroll-ps": j() }],
        "scroll-pe": [{ "scroll-pe": j() }],
        "scroll-pt": [{ "scroll-pt": j() }],
        "scroll-pr": [{ "scroll-pr": j() }],
        "scroll-pb": [{ "scroll-pb": j() }],
        "scroll-pl": [{ "scroll-pl": j() }],
        "snap-align": [{ snap: ["start", "end", "center", "align-none"] }],
        "snap-stop": [{ snap: ["normal", "always"] }],
        "snap-type": [{ snap: ["none", "x", "y", "both"] }],
        "snap-strictness": [{ snap: ["mandatory", "proximity"] }],
        touch: [{ touch: ["auto", "none", "manipulation"] }],
        "touch-x": [{ "touch-pan": ["x", "left", "right"] }],
        "touch-y": [{ "touch-pan": ["y", "up", "down"] }],
        "touch-pz": ["touch-pinch-zoom"],
        select: [{ select: ["none", "text", "all", "auto"] }],
        "will-change": [{ "will-change": ["auto", "scroll", "contents", "transform", te] }],
        fill: [{ fill: [e, "none"] }],
        "stroke-w": [{ stroke: [An, or, ug] }],
        stroke: [{ stroke: [e, "none"] }],
        sr: ["sr-only", "not-sr-only"],
        "forced-color-adjust": [{ "forced-color-adjust": ["auto", "none"] }],
      },
      conflictingClassGroups: {
        overflow: ["overflow-x", "overflow-y"],
        overscroll: ["overscroll-x", "overscroll-y"],
        inset: ["inset-x", "inset-y", "start", "end", "top", "right", "bottom", "left"],
        "inset-x": ["right", "left"],
        "inset-y": ["top", "bottom"],
        flex: ["basis", "grow", "shrink"],
        gap: ["gap-x", "gap-y"],
        p: ["px", "py", "ps", "pe", "pt", "pr", "pb", "pl"],
        px: ["pr", "pl"],
        py: ["pt", "pb"],
        m: ["mx", "my", "ms", "me", "mt", "mr", "mb", "ml"],
        mx: ["mr", "ml"],
        my: ["mt", "mb"],
        size: ["w", "h"],
        "font-size": ["leading"],
        "fvn-normal": [
          "fvn-ordinal",
          "fvn-slashed-zero",
          "fvn-figure",
          "fvn-spacing",
          "fvn-fraction",
        ],
        "fvn-ordinal": ["fvn-normal"],
        "fvn-slashed-zero": ["fvn-normal"],
        "fvn-figure": ["fvn-normal"],
        "fvn-spacing": ["fvn-normal"],
        "fvn-fraction": ["fvn-normal"],
        "line-clamp": ["display", "overflow"],
        rounded: [
          "rounded-s",
          "rounded-e",
          "rounded-t",
          "rounded-r",
          "rounded-b",
          "rounded-l",
          "rounded-ss",
          "rounded-se",
          "rounded-ee",
          "rounded-es",
          "rounded-tl",
          "rounded-tr",
          "rounded-br",
          "rounded-bl",
        ],
        "rounded-s": ["rounded-ss", "rounded-es"],
        "rounded-e": ["rounded-se", "rounded-ee"],
        "rounded-t": ["rounded-tl", "rounded-tr"],
        "rounded-r": ["rounded-tr", "rounded-br"],
        "rounded-b": ["rounded-br", "rounded-bl"],
        "rounded-l": ["rounded-tl", "rounded-bl"],
        "border-spacing": ["border-spacing-x", "border-spacing-y"],
        "border-w": [
          "border-w-s",
          "border-w-e",
          "border-w-t",
          "border-w-r",
          "border-w-b",
          "border-w-l",
        ],
        "border-w-x": ["border-w-r", "border-w-l"],
        "border-w-y": ["border-w-t", "border-w-b"],
        "border-color": [
          "border-color-s",
          "border-color-e",
          "border-color-t",
          "border-color-r",
          "border-color-b",
          "border-color-l",
        ],
        "border-color-x": ["border-color-r", "border-color-l"],
        "border-color-y": ["border-color-t", "border-color-b"],
        "scroll-m": [
          "scroll-mx",
          "scroll-my",
          "scroll-ms",
          "scroll-me",
          "scroll-mt",
          "scroll-mr",
          "scroll-mb",
          "scroll-ml",
        ],
        "scroll-mx": ["scroll-mr", "scroll-ml"],
        "scroll-my": ["scroll-mt", "scroll-mb"],
        "scroll-p": [
          "scroll-px",
          "scroll-py",
          "scroll-ps",
          "scroll-pe",
          "scroll-pt",
          "scroll-pr",
          "scroll-pb",
          "scroll-pl",
        ],
        "scroll-px": ["scroll-pr", "scroll-pl"],
        "scroll-py": ["scroll-pt", "scroll-pb"],
        touch: ["touch-x", "touch-y", "touch-pz"],
        "touch-x": ["touch"],
        "touch-y": ["touch"],
        "touch-pz": ["touch"],
      },
      conflictingClassGroupModifiers: { "font-size": ["leading"] },
    };
  },
  wH = eH(yH);
function ve(...e) {
  return wH(E2(e));
}
const va = _.forwardRef(({ className: e, ...t }, n) =>
  R.jsx("div", {
    ref: n,
    className: ve("rounded-lg border bg-card text-card-foreground shadow-sm", e),
    ...t,
  }),
);
va.displayName = "Card";
const ya = _.forwardRef(({ className: e, ...t }, n) =>
  R.jsx("div", { ref: n, className: ve("flex flex-col space-y-1.5 p-6", e), ...t }),
);
ya.displayName = "CardHeader";
const wa = _.forwardRef(({ className: e, ...t }, n) =>
  R.jsx("div", {
    ref: n,
    className: ve("text-2xl font-semibold leading-none tracking-tight", e),
    ...t,
  }),
);
wa.displayName = "CardTitle";
const xH = _.forwardRef(({ className: e, ...t }, n) =>
  R.jsx("div", { ref: n, className: ve("text-sm text-muted-foreground", e), ...t }),
);
xH.displayName = "CardDescription";
const xa = _.forwardRef(({ className: e, ...t }, n) =>
  R.jsx("div", { ref: n, className: ve("p-6 pt-0", e), ...t }),
);
xa.displayName = "CardContent";
const _H = _.forwardRef(({ className: e, ...t }, n) =>
  R.jsx("div", { ref: n, className: ve("flex items-center p-6 pt-0", e), ...t }),
);
_H.displayName = "CardFooter";
/**
 * @license lucide-react v0.379.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */ const bH = (e) => e.replace(/([a-z0-9])([A-Z])/g, "$1-$2").toLowerCase(),
  A2 = (...e) => e.filter((t, n, r) => !!t && r.indexOf(t) === n).join(" ");
/**
 * @license lucide-react v0.379.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */ var SH = {
  xmlns: "http://www.w3.org/2000/svg",
  width: 24,
  height: 24,
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 2,
  strokeLinecap: "round",
  strokeLinejoin: "round",
};
/**
 * @license lucide-react v0.379.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */ const EH = _.forwardRef(
  (
    {
      color: e = "currentColor",
      size: t = 24,
      strokeWidth: n = 2,
      absoluteStrokeWidth: r,
      className: i = "",
      children: o,
      iconNode: s,
      ...a
    },
    u,
  ) =>
    _.createElement(
      "svg",
      {
        ref: u,
        ...SH,
        width: t,
        height: t,
        stroke: e,
        strokeWidth: r ? (Number(n) * 24) / Number(t) : n,
        className: A2("lucide", i),
        ...a,
      },
      [...s.map(([l, c]) => _.createElement(l, c)), ...(Array.isArray(o) ? o : [o])],
    ),
);
/**
 * @license lucide-react v0.379.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */ const Bt = (e, t) => {
  const n = _.forwardRef(({ className: r, ...i }, o) =>
    _.createElement(EH, { ref: o, iconNode: t, className: A2(`lucide-${bH(e)}`, r), ...i }),
  );
  return (n.displayName = `${e}`), n;
};
/**
 * @license lucide-react v0.379.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */ const CH = Bt("Bot", [
  ["path", { d: "M12 8V4H8", key: "hb8ula" }],
  ["rect", { width: "16", height: "12", x: "4", y: "8", rx: "2", key: "enze0r" }],
  ["path", { d: "M2 14h2", key: "vft8re" }],
  ["path", { d: "M20 14h2", key: "4cs60a" }],
  ["path", { d: "M15 13v2", key: "1xurst" }],
  ["path", { d: "M9 13v2", key: "rq6x2g" }],
]);
/**
 * @license lucide-react v0.379.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */ const TH = Bt("FileJson", [
  ["path", { d: "M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z", key: "1rqfz7" }],
  ["path", { d: "M14 2v4a2 2 0 0 0 2 2h4", key: "tnqrlb" }],
  [
    "path",
    { d: "M10 12a1 1 0 0 0-1 1v1a1 1 0 0 1-1 1 1 1 0 0 1 1 1v1a1 1 0 0 0 1 1", key: "1oajmo" },
  ],
  [
    "path",
    { d: "M14 18a1 1 0 0 0 1-1v-1a1 1 0 0 1 1-1 1 1 0 0 1-1-1v-1a1 1 0 0 0-1-1", key: "mpwhp6" },
  ],
]);
/**
 * @license lucide-react v0.379.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */ const kH = Bt("History", [
  ["path", { d: "M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8", key: "1357e3" }],
  ["path", { d: "M3 3v5h5", key: "1xhq8a" }],
  ["path", { d: "M12 7v5l4 2", key: "1fdv2h" }],
]);
/**
 * @license lucide-react v0.379.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */ const RH = Bt("Moon", [["path", { d: "M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z", key: "a7tn18" }]]);
/**
 * @license lucide-react v0.379.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */ const PH = Bt("Pause", [
  ["rect", { x: "14", y: "4", width: "4", height: "16", rx: "1", key: "zuxfzm" }],
  ["rect", { x: "6", y: "4", width: "4", height: "16", rx: "1", key: "1okwgv" }],
]);
/**
 * @license lucide-react v0.379.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */ const AH = Bt("Play", [["polygon", { points: "6 3 20 12 6 21 6 3", key: "1oa8hb" }]]);
/**
 * @license lucide-react v0.379.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */ const NH = Bt("RadioTower", [
  ["path", { d: "M4.9 16.1C1 12.2 1 5.8 4.9 1.9", key: "s0qx1y" }],
  ["path", { d: "M7.8 4.7a6.14 6.14 0 0 0-.8 7.5", key: "1idnkw" }],
  ["circle", { cx: "12", cy: "9", r: "2", key: "1092wv" }],
  ["path", { d: "M16.2 4.8c2 2 2.26 5.11.8 7.47", key: "ojru2q" }],
  ["path", { d: "M19.1 1.9a9.96 9.96 0 0 1 0 14.1", key: "rhi7fg" }],
  ["path", { d: "M9.5 18h5", key: "mfy3pd" }],
  ["path", { d: "m8 22 4-11 4 11", key: "25yftu" }],
]);
/**
 * @license lucide-react v0.379.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */ const MH = Bt("Send", [
  ["path", { d: "m22 2-7 20-4-9-9-4Z", key: "1q3vgg" }],
  ["path", { d: "M22 2 11 13", key: "nzbqef" }],
]);
/**
 * @license lucide-react v0.379.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */ const IH = Bt("SquareActivity", [
  ["rect", { width: "18", height: "18", x: "3", y: "3", rx: "2", key: "afitv7" }],
  ["path", { d: "M17 12h-2l-2 5-2-10-2 5H7", key: "15hlnc" }],
]);
/**
 * @license lucide-react v0.379.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */ const DH = Bt("Sun", [
  ["circle", { cx: "12", cy: "12", r: "4", key: "4exip2" }],
  ["path", { d: "M12 2v2", key: "tus03m" }],
  ["path", { d: "M12 20v2", key: "1lh1kg" }],
  ["path", { d: "m4.93 4.93 1.41 1.41", key: "149t6j" }],
  ["path", { d: "m17.66 17.66 1.41 1.41", key: "ptbguv" }],
  ["path", { d: "M2 12h2", key: "1t8f8n" }],
  ["path", { d: "M20 12h2", key: "1q8mjw" }],
  ["path", { d: "m6.34 17.66-1.41 1.41", key: "1m8zz5" }],
  ["path", { d: "m19.07 4.93-1.41 1.41", key: "1shlcs" }],
]);
/**
 * @license lucide-react v0.379.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */ const OH = Bt("X", [
  ["path", { d: "M18 6 6 18", key: "1bl5f8" }],
  ["path", { d: "m6 6 12 12", key: "d8bk6v" }],
]);
/**
 * @license lucide-react v0.379.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */ const N2 = Bt("Zap", [
    [
      "path",
      {
        d: "M4 14a1 1 0 0 1-.78-1.63l9.9-10.2a.5.5 0 0 1 .86.46l-1.92 6.02A1 1 0 0 0 13 10h7a1 1 0 0 1 .78 1.63l-9.9 10.2a.5.5 0 0 1-.86-.46l1.92-6.02A1 1 0 0 0 11 14z",
        key: "1xq2db",
      },
    ],
  ]),
  FC = (e) => (e ? (Array.isArray(e) ? e : [e]) : []),
  jC = ({ title: e, items: t, icon: n, colorClass: r }) =>
    t != null && t.length
      ? R.jsxs("div", {
          className: "mb-2 last:mb-0",
          children: [
            R.jsx("h4", {
              className:
                "text-[10px] font-semibold text-muted-foreground mb-1 tracking-wide uppercase",
              children: e,
            }),
            t.map((i, o) =>
              R.jsxs(
                "div",
                {
                  className: "flex items-center gap-2 text-[12px] leading-5",
                  children: [
                    R.jsx(n, { className: ve("w-3.5 h-3.5 shrink-0", r) }),
                    R.jsx("span", { className: "truncate", children: i.type ?? i.src ?? i }),
                  ],
                },
                o,
              ),
            ),
          ],
        })
      : null,
  LH = ({ data: e, selected: t }) => {
    var o, s;
    const n = FC((o = e.definition) == null ? void 0 : o.entry),
      r = FC((s = e.definition) == null ? void 0 : s.invoke),
      i = n.length > 0 || r.length > 0;
    return R.jsxs(va, {
      className: ve(
        "w-[240px] rounded-lg border shadow-sm bg-card/90",
        t ? "ring-2 ring-primary ring-offset-2 ring-offset-background" : "border-border",
      ),
      children: [
        R.jsx(yr, { type: "target", position: Y.Top, className: "!bg-transparent opacity-0" }),
        R.jsx(ya, {
          className: "p-2.5 drag-handle cursor-move bg-muted/60 rounded-t-lg border-b",
          children: R.jsx(wa, {
            className: "text-[13px] font-semibold tracking-wide",
            children: e.label,
          }),
        }),
        i &&
          R.jsxs(xa, {
            className: "p-3",
            children: [
              R.jsx(jC, { title: "Entry", items: n, icon: N2, colorClass: "text-yellow-500" }),
              R.jsx(jC, { title: "Invoke", items: r, icon: NH, colorClass: "text-blue-500" }),
            ],
          }),
        R.jsx(yr, { type: "source", position: Y.Bottom, className: "!bg-transparent opacity-0" }),
        R.jsx(yr, { type: "source", position: Y.Left, className: "!bg-transparent opacity-0" }),
        R.jsx(yr, { type: "source", position: Y.Right, className: "!bg-transparent opacity-0" }),
      ],
    });
  },
  FH = (e) =>
    R.jsx("div", {
      className: ve(
        "rounded-lg border-2 bg-secondary/20",
        e.selected ? "border-primary/60" : "border-border",
      ),
      children: R.jsx("div", {
        className:
          "p-2 text-[12px] font-bold text-muted-foreground drag-handle cursor-move border-b bg-secondary/30 rounded-t-lg",
        children: e.data.label,
      }),
    }),
  jH = ({ data: e }) => {
    const t = Object.entries(e.context ?? {}).map(([n, r]) => ({ key: n, type: typeof r }));
    return R.jsxs(va, {
      className: "bg-card/80",
      children: [
        R.jsx(ya, {
          className: "p-3 border-b",
          children: R.jsx(wa, { className: "text-sm", children: e.label }),
        }),
        t.length > 0 &&
          R.jsxs(xa, {
            className: "p-3",
            children: [
              R.jsx("h4", {
                className:
                  "text-[10px] font-semibold text-muted-foreground mb-1 tracking-wide uppercase",
                children: "Context",
              }),
              t.map(({ key: n, type: r }) =>
                R.jsxs(
                  "div",
                  {
                    className: "text-[12px] leading-5",
                    children: [
                      R.jsx("span", { className: "font-mono font-medium", children: n }),
                      ": ",
                      r,
                    ],
                  },
                  n,
                ),
              ),
            ],
          }),
      ],
    });
  },
  VH = () =>
    R.jsx("div", {
      className:
        "w-0 h-0 border-t-4 border-b-4 border-l-8 border-t-transparent border-b-transparent border-l-foreground",
    }),
  qH = (e) => (e ? (Array.isArray(e) ? e : [e]) : []),
  $H = ({ id: e, sourceX: t, sourceY: n, targetX: r, targetY: i, markerEnd: o, data: s }) => {
    const [a, u, l] = fl({ sourceX: t, sourceY: n, targetX: r, targetY: i, borderRadius: 16 }),
      c = qH(s == null ? void 0 : s.actions);
    return R.jsxs(R.Fragment, {
      children: [
        R.jsx(Co, { id: e, path: a, markerEnd: o, style: { strokeWidth: 1.5 } }),
        R.jsx(b4, {
          children: R.jsxs("div", {
            style: { transform: `translate(-50%, -50%) translate(${u}px, ${l}px)` },
            className:
              "nodrag nopan absolute rounded-full border bg-background/95 px-2.5 py-0.5 text-xs font-medium shadow",
            children: [
              R.jsx("div", { className: "text-center", children: s == null ? void 0 : s.label }),
              c.length > 0 && R.jsx("hr", { className: "my-1" }),
              c.map((f, d) =>
                R.jsxs(
                  "div",
                  {
                    className: "flex items-center gap-1 text-[10px] text-muted-foreground",
                    children: [
                      R.jsx(N2, { className: "w-3 h-3 text-yellow-500" }),
                      R.jsx("span", { children: f.type ?? f }),
                    ],
                  },
                  d,
                ),
              ),
            ],
          }),
        }),
      ],
    });
  },
  zH = { rootNode: jH, stateNode: LH, compoundStateNode: FH, initialNode: VH },
  BH = { transitionEdge: $H },
  UH = ({ machine: e, activeStateIds: t }) => {
    const n = _.useMemo(() => $U(e.definition, e.context), [e.definition, e.context]),
      [r, i] = _.useState(() =>
        n.nodes.map((c) => ({ ...c, dragHandle: ".drag-handle", selected: t.includes(c.id) })),
      ),
      [o, s] = _.useState(n.edges),
      { fitView: a } = Zl();
    _.useEffect(() => {
      i(n.nodes.map((f) => ({ ...f, dragHandle: ".drag-handle", selected: t.includes(f.id) }))),
        s(n.edges);
      const c = setTimeout(() => a({ duration: 400, padding: 0.1 }), 50);
      return () => clearTimeout(c);
    }, [n, t, a]),
      _.useEffect(() => {
        i((c) => c.map((f) => ({ ...f, selected: t.includes(f.id) })));
      }, [t]);
    const u = _.useCallback((c) => i((f) => BA(c, f)), []),
      l = _.useCallback((c) => s((f) => P$(c, f)), []);
    return R.jsxs(nN, {
      nodes: r,
      edges: o,
      onNodesChange: u,
      onEdgesChange: l,
      nodeTypes: zH,
      edgeTypes: BH,
      proOptions: { hideAttribution: !0 },
      nodesDraggable: !0,
      nodesConnectable: !1,
      elementsSelectable: !0,
      selectionOnDrag: !0,
      panOnDrag: !1,
      selectionMode: mo.Partial,
      connectionLineType: In.SmoothStep,
      defaultEdgeOptions: { type: "transitionEdge", markerEnd: { type: go.ArrowClosed } },
      fitView: !0,
      minZoom: 0.2,
      maxZoom: 1.5,
      className: "bg-muted/40",
      children: [
        R.jsx(V4, {}),
        R.jsx(M4, {
          nodeColor: (c) => (c.selected ? "hsl(var(--primary))" : "hsl(var(--border))"),
          nodeStrokeWidth: 3,
        }),
        R.jsx(H4, {}),
      ],
    });
  },
  HH = (e) => R.jsx(y0, { children: R.jsx(UH, { ...e }) });
function VC(e, t) {
  if (typeof e == "function") return e(t);
  e != null && (e.current = t);
}
function M2(...e) {
  return (t) => {
    let n = !1;
    const r = e.map((i) => {
      const o = VC(i, t);
      return !n && typeof o == "function" && (n = !0), o;
    });
    if (n)
      return () => {
        for (let i = 0; i < r.length; i++) {
          const o = r[i];
          typeof o == "function" ? o() : VC(e[i], null);
        }
      };
  };
}
function bn(...e) {
  return _.useCallback(M2(...e), e);
}
function Js(e) {
  const t = WH(e),
    n = _.forwardRef((r, i) => {
      const { children: o, ...s } = r,
        a = _.Children.toArray(o),
        u = a.find(YH);
      if (u) {
        const l = u.props.children,
          c = a.map((f) =>
            f === u
              ? _.Children.count(l) > 1
                ? _.Children.only(null)
                : _.isValidElement(l)
                  ? l.props.children
                  : null
              : f,
          );
        return R.jsx(t, {
          ...s,
          ref: i,
          children: _.isValidElement(l) ? _.cloneElement(l, void 0, c) : null,
        });
      }
      return R.jsx(t, { ...s, ref: i, children: o });
    });
  return (n.displayName = `${e}.Slot`), n;
}
var GH = Js("Slot");
function WH(e) {
  const t = _.forwardRef((n, r) => {
    const { children: i, ...o } = n;
    if (_.isValidElement(i)) {
      const s = ZH(i),
        a = XH(o, i.props);
      return i.type !== _.Fragment && (a.ref = r ? M2(r, s) : s), _.cloneElement(i, a);
    }
    return _.Children.count(i) > 1 ? _.Children.only(null) : null;
  });
  return (t.displayName = `${e}.SlotClone`), t;
}
var KH = Symbol("radix.slottable");
function YH(e) {
  return (
    _.isValidElement(e) &&
    typeof e.type == "function" &&
    "__radixId" in e.type &&
    e.type.__radixId === KH
  );
}
function XH(e, t) {
  const n = { ...t };
  for (const r in t) {
    const i = e[r],
      o = t[r];
    /^on[A-Z]/.test(r)
      ? i && o
        ? (n[r] = (...a) => {
            const u = o(...a);
            return i(...a), u;
          })
        : i && (n[r] = i)
      : r === "style"
        ? (n[r] = { ...i, ...o })
        : r === "className" && (n[r] = [i, o].filter(Boolean).join(" "));
  }
  return { ...e, ...n };
}
function ZH(e) {
  var r, i;
  let t = (r = Object.getOwnPropertyDescriptor(e.props, "ref")) == null ? void 0 : r.get,
    n = t && "isReactWarning" in t && t.isReactWarning;
  return n
    ? e.ref
    : ((t = (i = Object.getOwnPropertyDescriptor(e, "ref")) == null ? void 0 : i.get),
      (n = t && "isReactWarning" in t && t.isReactWarning),
      n ? e.props.ref : e.props.ref || e.ref);
}
const qC = (e) => (typeof e == "boolean" ? `${e}` : e === 0 ? "0" : e),
  $C = E2,
  I2 = (e, t) => (n) => {
    var r;
    if ((t == null ? void 0 : t.variants) == null)
      return $C(e, n == null ? void 0 : n.class, n == null ? void 0 : n.className);
    const { variants: i, defaultVariants: o } = t,
      s = Object.keys(i).map((l) => {
        const c = n == null ? void 0 : n[l],
          f = o == null ? void 0 : o[l];
        if (c === null) return null;
        const d = qC(c) || qC(f);
        return i[l][d];
      }),
      a =
        n &&
        Object.entries(n).reduce((l, c) => {
          let [f, d] = c;
          return d === void 0 || (l[f] = d), l;
        }, {}),
      u =
        t == null || (r = t.compoundVariants) === null || r === void 0
          ? void 0
          : r.reduce((l, c) => {
              let { class: f, className: d, ...h } = c;
              return Object.entries(h).every((v) => {
                let [p, y] = v;
                return Array.isArray(y) ? y.includes({ ...o, ...a }[p]) : { ...o, ...a }[p] === y;
              })
                ? [...l, f, d]
                : l;
            }, []);
    return $C(e, s, u, n == null ? void 0 : n.class, n == null ? void 0 : n.className);
  },
  QH = I2(
    "inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50",
    {
      variants: {
        variant: {
          default: "bg-primary text-primary-foreground hover:bg-primary/90",
          destructive: "bg-destructive text-destructive-foreground hover:bg-destructive/90",
          outline: "border border-input bg-background hover:bg-accent hover:text-accent-foreground",
          secondary: "bg-secondary text-secondary-foreground hover:bg-secondary/80",
          ghost: "hover:bg-accent hover:text-accent-foreground",
          link: "text-primary underline-offset-4 hover:underline",
        },
        size: {
          default: "h-10 px-4 py-2",
          sm: "h-9 rounded-md px-3",
          lg: "h-11 rounded-md px-8",
          icon: "h-10 w-10",
        },
      },
      defaultVariants: { variant: "default", size: "default" },
    },
  ),
  q0 = _.forwardRef(({ className: e, variant: t, size: n, asChild: r = !1, ...i }, o) => {
    const s = r ? GH : "button";
    return R.jsx(s, { className: ve(QH({ variant: t, size: n, className: e })), ref: o, ...i });
  });
q0.displayName = "Button";
function Ye(e, t, { checkForDefaultPrevented: n = !0 } = {}) {
  return function (i) {
    if ((e == null || e(i), n === !1 || !i.defaultPrevented)) return t == null ? void 0 : t(i);
  };
}
function JH(e, t) {
  const n = _.createContext(t),
    r = (o) => {
      const { children: s, ...a } = o,
        u = _.useMemo(() => a, Object.values(a));
      return R.jsx(n.Provider, { value: u, children: s });
    };
  r.displayName = e + "Provider";
  function i(o) {
    const s = _.useContext(n);
    if (s) return s;
    if (t !== void 0) return t;
    throw new Error(`\`${o}\` must be used within \`${e}\``);
  }
  return [r, i];
}
function vc(e, t = []) {
  let n = [];
  function r(o, s) {
    const a = _.createContext(s),
      u = n.length;
    n = [...n, s];
    const l = (f) => {
      var m;
      const { scope: d, children: h, ...v } = f,
        p = ((m = d == null ? void 0 : d[e]) == null ? void 0 : m[u]) || a,
        y = _.useMemo(() => v, Object.values(v));
      return R.jsx(p.Provider, { value: y, children: h });
    };
    l.displayName = o + "Provider";
    function c(f, d) {
      var p;
      const h = ((p = d == null ? void 0 : d[e]) == null ? void 0 : p[u]) || a,
        v = _.useContext(h);
      if (v) return v;
      if (s !== void 0) return s;
      throw new Error(`\`${f}\` must be used within \`${o}\``);
    }
    return [l, c];
  }
  const i = () => {
    const o = n.map((s) => _.createContext(s));
    return function (a) {
      const u = (a == null ? void 0 : a[e]) || o;
      return _.useMemo(() => ({ [`__scope${e}`]: { ...a, [e]: u } }), [a, u]);
    };
  };
  return (i.scopeName = e), [r, e9(i, ...t)];
}
function e9(...e) {
  const t = e[0];
  if (e.length === 1) return t;
  const n = () => {
    const r = e.map((i) => ({ useScope: i(), scopeName: i.scopeName }));
    return function (o) {
      const s = r.reduce((a, { useScope: u, scopeName: l }) => {
        const f = u(o)[`__scope${l}`];
        return { ...a, ...f };
      }, {});
      return _.useMemo(() => ({ [`__scope${t.scopeName}`]: s }), [s]);
    };
  };
  return (n.scopeName = t.scopeName), n;
}
function t9(e) {
  const t = e + "CollectionProvider",
    [n, r] = vc(t),
    [i, o] = n(t, { collectionRef: { current: null }, itemMap: new Map() }),
    s = (p) => {
      const { scope: y, children: m } = p,
        g = L.useRef(null),
        w = L.useRef(new Map()).current;
      return R.jsx(i, { scope: y, itemMap: w, collectionRef: g, children: m });
    };
  s.displayName = t;
  const a = e + "CollectionSlot",
    u = Js(a),
    l = L.forwardRef((p, y) => {
      const { scope: m, children: g } = p,
        w = o(a, m),
        x = bn(y, w.collectionRef);
      return R.jsx(u, { ref: x, children: g });
    });
  l.displayName = a;
  const c = e + "CollectionItemSlot",
    f = "data-radix-collection-item",
    d = Js(c),
    h = L.forwardRef((p, y) => {
      const { scope: m, children: g, ...w } = p,
        x = L.useRef(null),
        b = bn(y, x),
        E = o(c, m);
      return (
        L.useEffect(() => (E.itemMap.set(x, { ref: x, ...w }), () => void E.itemMap.delete(x))),
        R.jsx(d, { [f]: "", ref: b, children: g })
      );
    });
  h.displayName = c;
  function v(p) {
    const y = o(e + "CollectionConsumer", p);
    return L.useCallback(() => {
      const g = y.collectionRef.current;
      if (!g) return [];
      const w = Array.from(g.querySelectorAll(`[${f}]`));
      return Array.from(y.itemMap.values()).sort(
        (E, C) => w.indexOf(E.ref.current) - w.indexOf(C.ref.current),
      );
    }, [y.collectionRef, y.itemMap]);
  }
  return [{ Provider: s, Slot: l, ItemSlot: h }, v, r];
}
var ea = globalThis != null && globalThis.document ? _.useLayoutEffect : () => {},
  n9 = kk[" useId ".trim().toString()] || (() => {}),
  r9 = 0;
function Ss(e) {
  const [t, n] = _.useState(n9());
  return (
    ea(() => {
      n((r) => r ?? String(r9++));
    }, [e]),
    t ? `radix-${t}` : ""
  );
}
var i9 = [
    "a",
    "button",
    "div",
    "form",
    "h2",
    "h3",
    "img",
    "input",
    "label",
    "li",
    "nav",
    "ol",
    "p",
    "select",
    "span",
    "svg",
    "ul",
  ],
  ct = i9.reduce((e, t) => {
    const n = Js(`Primitive.${t}`),
      r = _.forwardRef((i, o) => {
        const { asChild: s, ...a } = i,
          u = s ? n : t;
        return (
          typeof window < "u" && (window[Symbol.for("radix-ui")] = !0), R.jsx(u, { ...a, ref: o })
        );
      });
    return (r.displayName = `Primitive.${t}`), { ...e, [t]: r };
  }, {});
function o9(e, t) {
  e && $l.flushSync(() => e.dispatchEvent(t));
}
function vo(e) {
  const t = _.useRef(e);
  return (
    _.useEffect(() => {
      t.current = e;
    }),
    _.useMemo(
      () =>
        (...n) => {
          var r;
          return (r = t.current) == null ? void 0 : r.call(t, ...n);
        },
      [],
    )
  );
}
var s9 = kk[" useInsertionEffect ".trim().toString()] || ea;
function $0({ prop: e, defaultProp: t, onChange: n = () => {}, caller: r }) {
  const [i, o, s] = a9({ defaultProp: t, onChange: n }),
    a = e !== void 0,
    u = a ? e : i;
  {
    const c = _.useRef(e !== void 0);
    _.useEffect(() => {
      const f = c.current;
      f !== a &&
        console.warn(
          `${r} is changing from ${f ? "controlled" : "uncontrolled"} to ${a ? "controlled" : "uncontrolled"}. Components should not switch from controlled to uncontrolled (or vice versa). Decide between using a controlled or uncontrolled value for the lifetime of the component.`,
        ),
        (c.current = a);
    }, [a, r]);
  }
  const l = _.useCallback(
    (c) => {
      var f;
      if (a) {
        const d = u9(c) ? c(e) : c;
        d !== e && ((f = s.current) == null || f.call(s, d));
      } else o(c);
    },
    [a, e, o, s],
  );
  return [u, l];
}
function a9({ defaultProp: e, onChange: t }) {
  const [n, r] = _.useState(e),
    i = _.useRef(n),
    o = _.useRef(t);
  return (
    s9(() => {
      o.current = t;
    }, [t]),
    _.useEffect(() => {
      var s;
      i.current !== n && ((s = o.current) == null || s.call(o, n), (i.current = n));
    }, [n, i]),
    [n, r, o]
  );
}
function u9(e) {
  return typeof e == "function";
}
var l9 = _.createContext(void 0);
function D2(e) {
  const t = _.useContext(l9);
  return e || t || "ltr";
}
var lg = "rovingFocusGroup.onEntryFocus",
  c9 = { bubbles: !1, cancelable: !0 },
  _a = "RovingFocusGroup",
  [zv, O2, f9] = t9(_a),
  [d9, L2] = vc(_a, [f9]),
  [h9, p9] = d9(_a),
  F2 = _.forwardRef((e, t) =>
    R.jsx(zv.Provider, {
      scope: e.__scopeRovingFocusGroup,
      children: R.jsx(zv.Slot, {
        scope: e.__scopeRovingFocusGroup,
        children: R.jsx(m9, { ...e, ref: t }),
      }),
    }),
  );
F2.displayName = _a;
var m9 = _.forwardRef((e, t) => {
    const {
        __scopeRovingFocusGroup: n,
        orientation: r,
        loop: i = !1,
        dir: o,
        currentTabStopId: s,
        defaultCurrentTabStopId: a,
        onCurrentTabStopIdChange: u,
        onEntryFocus: l,
        preventScrollOnEntryFocus: c = !1,
        ...f
      } = e,
      d = _.useRef(null),
      h = bn(t, d),
      v = D2(o),
      [p, y] = $0({ prop: s, defaultProp: a ?? null, onChange: u, caller: _a }),
      [m, g] = _.useState(!1),
      w = vo(l),
      x = O2(n),
      b = _.useRef(!1),
      [E, C] = _.useState(0);
    return (
      _.useEffect(() => {
        const T = d.current;
        if (T) return T.addEventListener(lg, w), () => T.removeEventListener(lg, w);
      }, [w]),
      R.jsx(h9, {
        scope: n,
        orientation: r,
        dir: v,
        loop: i,
        currentTabStopId: p,
        onItemFocus: _.useCallback((T) => y(T), [y]),
        onItemShiftTab: _.useCallback(() => g(!0), []),
        onFocusableItemAdd: _.useCallback(() => C((T) => T + 1), []),
        onFocusableItemRemove: _.useCallback(() => C((T) => T - 1), []),
        children: R.jsx(ct.div, {
          tabIndex: m || E === 0 ? -1 : 0,
          "data-orientation": r,
          ...f,
          ref: h,
          style: { outline: "none", ...e.style },
          onMouseDown: Ye(e.onMouseDown, () => {
            b.current = !0;
          }),
          onFocus: Ye(e.onFocus, (T) => {
            const P = !b.current;
            if (T.target === T.currentTarget && P && !m) {
              const M = new CustomEvent(lg, c9);
              if ((T.currentTarget.dispatchEvent(M), !M.defaultPrevented)) {
                const I = x().filter((A) => A.focusable),
                  j = I.find((A) => A.active),
                  q = I.find((A) => A.id === p),
                  O = [j, q, ...I].filter(Boolean).map((A) => A.ref.current);
                q2(O, c);
              }
            }
            b.current = !1;
          }),
          onBlur: Ye(e.onBlur, () => g(!1)),
        }),
      })
    );
  }),
  j2 = "RovingFocusGroupItem",
  V2 = _.forwardRef((e, t) => {
    const {
        __scopeRovingFocusGroup: n,
        focusable: r = !0,
        active: i = !1,
        tabStopId: o,
        children: s,
        ...a
      } = e,
      u = Ss(),
      l = o || u,
      c = p9(j2, n),
      f = c.currentTabStopId === l,
      d = O2(n),
      { onFocusableItemAdd: h, onFocusableItemRemove: v, currentTabStopId: p } = c;
    return (
      _.useEffect(() => {
        if (r) return h(), () => v();
      }, [r, h, v]),
      R.jsx(zv.ItemSlot, {
        scope: n,
        id: l,
        focusable: r,
        active: i,
        children: R.jsx(ct.span, {
          tabIndex: f ? 0 : -1,
          "data-orientation": c.orientation,
          ...a,
          ref: t,
          onMouseDown: Ye(e.onMouseDown, (y) => {
            r ? c.onItemFocus(l) : y.preventDefault();
          }),
          onFocus: Ye(e.onFocus, () => c.onItemFocus(l)),
          onKeyDown: Ye(e.onKeyDown, (y) => {
            if (y.key === "Tab" && y.shiftKey) {
              c.onItemShiftTab();
              return;
            }
            if (y.target !== y.currentTarget) return;
            const m = y9(y, c.orientation, c.dir);
            if (m !== void 0) {
              if (y.metaKey || y.ctrlKey || y.altKey || y.shiftKey) return;
              y.preventDefault();
              let w = d()
                .filter((x) => x.focusable)
                .map((x) => x.ref.current);
              if (m === "last") w.reverse();
              else if (m === "prev" || m === "next") {
                m === "prev" && w.reverse();
                const x = w.indexOf(y.currentTarget);
                w = c.loop ? w9(w, x + 1) : w.slice(x + 1);
              }
              setTimeout(() => q2(w));
            }
          }),
          children: typeof s == "function" ? s({ isCurrentTabStop: f, hasTabStop: p != null }) : s,
        }),
      })
    );
  });
V2.displayName = j2;
var g9 = {
  ArrowLeft: "prev",
  ArrowUp: "prev",
  ArrowRight: "next",
  ArrowDown: "next",
  PageUp: "first",
  Home: "first",
  PageDown: "last",
  End: "last",
};
function v9(e, t) {
  return t !== "rtl" ? e : e === "ArrowLeft" ? "ArrowRight" : e === "ArrowRight" ? "ArrowLeft" : e;
}
function y9(e, t, n) {
  const r = v9(e.key, n);
  if (
    !(t === "vertical" && ["ArrowLeft", "ArrowRight"].includes(r)) &&
    !(t === "horizontal" && ["ArrowUp", "ArrowDown"].includes(r))
  )
    return g9[r];
}
function q2(e, t = !1) {
  const n = document.activeElement;
  for (const r of e)
    if (r === n || (r.focus({ preventScroll: t }), document.activeElement !== n)) return;
}
function w9(e, t) {
  return e.map((n, r) => e[(t + r) % e.length]);
}
var x9 = F2,
  _9 = V2;
function b9(e, t) {
  return _.useReducer((n, r) => t[n][r] ?? n, e);
}
var ba = (e) => {
  const { present: t, children: n } = e,
    r = S9(t),
    i = typeof n == "function" ? n({ present: r.isPresent }) : _.Children.only(n),
    o = bn(r.ref, E9(i));
  return typeof n == "function" || r.isPresent ? _.cloneElement(i, { ref: o }) : null;
};
ba.displayName = "Presence";
function S9(e) {
  const [t, n] = _.useState(),
    r = _.useRef(null),
    i = _.useRef(e),
    o = _.useRef("none"),
    s = e ? "mounted" : "unmounted",
    [a, u] = b9(s, {
      mounted: { UNMOUNT: "unmounted", ANIMATION_OUT: "unmountSuspended" },
      unmountSuspended: { MOUNT: "mounted", ANIMATION_END: "unmounted" },
      unmounted: { MOUNT: "mounted" },
    });
  return (
    _.useEffect(() => {
      const l = nu(r.current);
      o.current = a === "mounted" ? l : "none";
    }, [a]),
    ea(() => {
      const l = r.current,
        c = i.current;
      if (c !== e) {
        const d = o.current,
          h = nu(l);
        e
          ? u("MOUNT")
          : h === "none" || (l == null ? void 0 : l.display) === "none"
            ? u("UNMOUNT")
            : u(c && d !== h ? "ANIMATION_OUT" : "UNMOUNT"),
          (i.current = e);
      }
    }, [e, u]),
    ea(() => {
      if (t) {
        let l;
        const c = t.ownerDocument.defaultView ?? window,
          f = (h) => {
            const p = nu(r.current).includes(CSS.escape(h.animationName));
            if (h.target === t && p && (u("ANIMATION_END"), !i.current)) {
              const y = t.style.animationFillMode;
              (t.style.animationFillMode = "forwards"),
                (l = c.setTimeout(() => {
                  t.style.animationFillMode === "forwards" && (t.style.animationFillMode = y);
                }));
            }
          },
          d = (h) => {
            h.target === t && (o.current = nu(r.current));
          };
        return (
          t.addEventListener("animationstart", d),
          t.addEventListener("animationcancel", f),
          t.addEventListener("animationend", f),
          () => {
            c.clearTimeout(l),
              t.removeEventListener("animationstart", d),
              t.removeEventListener("animationcancel", f),
              t.removeEventListener("animationend", f);
          }
        );
      } else u("ANIMATION_END");
    }, [t, u]),
    {
      isPresent: ["mounted", "unmountSuspended"].includes(a),
      ref: _.useCallback((l) => {
        (r.current = l ? getComputedStyle(l) : null), n(l);
      }, []),
    }
  );
}
function nu(e) {
  return (e == null ? void 0 : e.animationName) || "none";
}
function E9(e) {
  var r, i;
  let t = (r = Object.getOwnPropertyDescriptor(e.props, "ref")) == null ? void 0 : r.get,
    n = t && "isReactWarning" in t && t.isReactWarning;
  return n
    ? e.ref
    : ((t = (i = Object.getOwnPropertyDescriptor(e, "ref")) == null ? void 0 : i.get),
      (n = t && "isReactWarning" in t && t.isReactWarning),
      n ? e.props.ref : e.props.ref || e.ref);
}
var yc = "Tabs",
  [C9, NX] = vc(yc, [L2]),
  $2 = L2(),
  [T9, z0] = C9(yc),
  z2 = _.forwardRef((e, t) => {
    const {
        __scopeTabs: n,
        value: r,
        onValueChange: i,
        defaultValue: o,
        orientation: s = "horizontal",
        dir: a,
        activationMode: u = "automatic",
        ...l
      } = e,
      c = D2(a),
      [f, d] = $0({ prop: r, onChange: i, defaultProp: o ?? "", caller: yc });
    return R.jsx(T9, {
      scope: n,
      baseId: Ss(),
      value: f,
      onValueChange: d,
      orientation: s,
      dir: c,
      activationMode: u,
      children: R.jsx(ct.div, { dir: c, "data-orientation": s, ...l, ref: t }),
    });
  });
z2.displayName = yc;
var B2 = "TabsList",
  U2 = _.forwardRef((e, t) => {
    const { __scopeTabs: n, loop: r = !0, ...i } = e,
      o = z0(B2, n),
      s = $2(n);
    return R.jsx(x9, {
      asChild: !0,
      ...s,
      orientation: o.orientation,
      dir: o.dir,
      loop: r,
      children: R.jsx(ct.div, { role: "tablist", "aria-orientation": o.orientation, ...i, ref: t }),
    });
  });
U2.displayName = B2;
var H2 = "TabsTrigger",
  G2 = _.forwardRef((e, t) => {
    const { __scopeTabs: n, value: r, disabled: i = !1, ...o } = e,
      s = z0(H2, n),
      a = $2(n),
      u = Y2(s.baseId, r),
      l = X2(s.baseId, r),
      c = r === s.value;
    return R.jsx(_9, {
      asChild: !0,
      ...a,
      focusable: !i,
      active: c,
      children: R.jsx(ct.button, {
        type: "button",
        role: "tab",
        "aria-selected": c,
        "aria-controls": l,
        "data-state": c ? "active" : "inactive",
        "data-disabled": i ? "" : void 0,
        disabled: i,
        id: u,
        ...o,
        ref: t,
        onMouseDown: Ye(e.onMouseDown, (f) => {
          !i && f.button === 0 && f.ctrlKey === !1 ? s.onValueChange(r) : f.preventDefault();
        }),
        onKeyDown: Ye(e.onKeyDown, (f) => {
          [" ", "Enter"].includes(f.key) && s.onValueChange(r);
        }),
        onFocus: Ye(e.onFocus, () => {
          const f = s.activationMode !== "manual";
          !c && !i && f && s.onValueChange(r);
        }),
      }),
    });
  });
G2.displayName = H2;
var W2 = "TabsContent",
  K2 = _.forwardRef((e, t) => {
    const { __scopeTabs: n, value: r, forceMount: i, children: o, ...s } = e,
      a = z0(W2, n),
      u = Y2(a.baseId, r),
      l = X2(a.baseId, r),
      c = r === a.value,
      f = _.useRef(c);
    return (
      _.useEffect(() => {
        const d = requestAnimationFrame(() => (f.current = !1));
        return () => cancelAnimationFrame(d);
      }, []),
      R.jsx(ba, {
        present: i || c,
        children: ({ present: d }) =>
          R.jsx(ct.div, {
            "data-state": c ? "active" : "inactive",
            "data-orientation": a.orientation,
            role: "tabpanel",
            "aria-labelledby": u,
            hidden: !d,
            id: l,
            tabIndex: 0,
            ...s,
            ref: t,
            style: { ...e.style, animationDuration: f.current ? "0s" : void 0 },
            children: d && o,
          }),
      })
    );
  });
K2.displayName = W2;
function Y2(e, t) {
  return `${e}-trigger-${t}`;
}
function X2(e, t) {
  return `${e}-content-${t}`;
}
var k9 = z2,
  Z2 = U2,
  Q2 = G2,
  J2 = K2;
const R9 = k9,
  eM = _.forwardRef(({ className: e, ...t }, n) =>
    R.jsx(Z2, {
      ref: n,
      className: ve(
        "inline-flex h-10 items-center justify-center rounded-md bg-muted p-1 text-muted-foreground",
        e,
      ),
      ...t,
    }),
  );
eM.displayName = Z2.displayName;
const Tu = _.forwardRef(({ className: e, ...t }, n) =>
  R.jsx(Q2, {
    ref: n,
    className: ve(
      "inline-flex items-center justify-center whitespace-nowrap rounded-sm px-3 py-1.5 text-sm font-medium ring-offset-background transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 data-[state=active]:bg-background data-[state=active]:text-foreground data-[state=active]:shadow-sm",
      e,
    ),
    ...t,
  }),
);
Tu.displayName = Q2.displayName;
const ku = _.forwardRef(({ className: e, ...t }, n) =>
  R.jsx(J2, {
    ref: n,
    className: ve(
      "mt-2 ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
      e,
    ),
    ...t,
  }),
);
ku.displayName = J2.displayName;
function P9(e, t = globalThis == null ? void 0 : globalThis.document) {
  const n = vo(e);
  _.useEffect(() => {
    const r = (i) => {
      i.key === "Escape" && n(i);
    };
    return (
      t.addEventListener("keydown", r, { capture: !0 }),
      () => t.removeEventListener("keydown", r, { capture: !0 })
    );
  }, [n, t]);
}
var A9 = "DismissableLayer",
  Bv = "dismissableLayer.update",
  N9 = "dismissableLayer.pointerDownOutside",
  M9 = "dismissableLayer.focusOutside",
  zC,
  tM = _.createContext({
    layers: new Set(),
    layersWithOutsidePointerEventsDisabled: new Set(),
    branches: new Set(),
  }),
  nM = _.forwardRef((e, t) => {
    const {
        disableOutsidePointerEvents: n = !1,
        onEscapeKeyDown: r,
        onPointerDownOutside: i,
        onFocusOutside: o,
        onInteractOutside: s,
        onDismiss: a,
        ...u
      } = e,
      l = _.useContext(tM),
      [c, f] = _.useState(null),
      d =
        (c == null ? void 0 : c.ownerDocument) ??
        (globalThis == null ? void 0 : globalThis.document),
      [, h] = _.useState({}),
      v = bn(t, (C) => f(C)),
      p = Array.from(l.layers),
      [y] = [...l.layersWithOutsidePointerEventsDisabled].slice(-1),
      m = p.indexOf(y),
      g = c ? p.indexOf(c) : -1,
      w = l.layersWithOutsidePointerEventsDisabled.size > 0,
      x = g >= m,
      b = O9((C) => {
        const T = C.target,
          P = [...l.branches].some((M) => M.contains(T));
        !x || P || (i == null || i(C), s == null || s(C), C.defaultPrevented || a == null || a());
      }, d),
      E = L9((C) => {
        const T = C.target;
        [...l.branches].some((M) => M.contains(T)) ||
          (o == null || o(C), s == null || s(C), C.defaultPrevented || a == null || a());
      }, d);
    return (
      P9((C) => {
        g === l.layers.size - 1 &&
          (r == null || r(C), !C.defaultPrevented && a && (C.preventDefault(), a()));
      }, d),
      _.useEffect(() => {
        if (c)
          return (
            n &&
              (l.layersWithOutsidePointerEventsDisabled.size === 0 &&
                ((zC = d.body.style.pointerEvents), (d.body.style.pointerEvents = "none")),
              l.layersWithOutsidePointerEventsDisabled.add(c)),
            l.layers.add(c),
            BC(),
            () => {
              n &&
                l.layersWithOutsidePointerEventsDisabled.size === 1 &&
                (d.body.style.pointerEvents = zC);
            }
          );
      }, [c, d, n, l]),
      _.useEffect(
        () => () => {
          c && (l.layers.delete(c), l.layersWithOutsidePointerEventsDisabled.delete(c), BC());
        },
        [c, l],
      ),
      _.useEffect(() => {
        const C = () => h({});
        return document.addEventListener(Bv, C), () => document.removeEventListener(Bv, C);
      }, []),
      R.jsx(ct.div, {
        ...u,
        ref: v,
        style: { pointerEvents: w ? (x ? "auto" : "none") : void 0, ...e.style },
        onFocusCapture: Ye(e.onFocusCapture, E.onFocusCapture),
        onBlurCapture: Ye(e.onBlurCapture, E.onBlurCapture),
        onPointerDownCapture: Ye(e.onPointerDownCapture, b.onPointerDownCapture),
      })
    );
  });
nM.displayName = A9;
var I9 = "DismissableLayerBranch",
  D9 = _.forwardRef((e, t) => {
    const n = _.useContext(tM),
      r = _.useRef(null),
      i = bn(t, r);
    return (
      _.useEffect(() => {
        const o = r.current;
        if (o)
          return (
            n.branches.add(o),
            () => {
              n.branches.delete(o);
            }
          );
      }, [n.branches]),
      R.jsx(ct.div, { ...e, ref: i })
    );
  });
D9.displayName = I9;
function O9(e, t = globalThis == null ? void 0 : globalThis.document) {
  const n = vo(e),
    r = _.useRef(!1),
    i = _.useRef(() => {});
  return (
    _.useEffect(() => {
      const o = (a) => {
          if (a.target && !r.current) {
            let u = function () {
              rM(N9, n, l, { discrete: !0 });
            };
            const l = { originalEvent: a };
            a.pointerType === "touch"
              ? (t.removeEventListener("click", i.current),
                (i.current = u),
                t.addEventListener("click", i.current, { once: !0 }))
              : u();
          } else t.removeEventListener("click", i.current);
          r.current = !1;
        },
        s = window.setTimeout(() => {
          t.addEventListener("pointerdown", o);
        }, 0);
      return () => {
        window.clearTimeout(s),
          t.removeEventListener("pointerdown", o),
          t.removeEventListener("click", i.current);
      };
    }, [t, n]),
    { onPointerDownCapture: () => (r.current = !0) }
  );
}
function L9(e, t = globalThis == null ? void 0 : globalThis.document) {
  const n = vo(e),
    r = _.useRef(!1);
  return (
    _.useEffect(() => {
      const i = (o) => {
        o.target && !r.current && rM(M9, n, { originalEvent: o }, { discrete: !1 });
      };
      return t.addEventListener("focusin", i), () => t.removeEventListener("focusin", i);
    }, [t, n]),
    { onFocusCapture: () => (r.current = !0), onBlurCapture: () => (r.current = !1) }
  );
}
function BC() {
  const e = new CustomEvent(Bv);
  document.dispatchEvent(e);
}
function rM(e, t, n, { discrete: r }) {
  const i = n.originalEvent.target,
    o = new CustomEvent(e, { bubbles: !1, cancelable: !0, detail: n });
  t && i.addEventListener(e, t, { once: !0 }), r ? o9(i, o) : i.dispatchEvent(o);
}
var cg = "focusScope.autoFocusOnMount",
  fg = "focusScope.autoFocusOnUnmount",
  UC = { bubbles: !1, cancelable: !0 },
  F9 = "FocusScope",
  iM = _.forwardRef((e, t) => {
    const { loop: n = !1, trapped: r = !1, onMountAutoFocus: i, onUnmountAutoFocus: o, ...s } = e,
      [a, u] = _.useState(null),
      l = vo(i),
      c = vo(o),
      f = _.useRef(null),
      d = bn(t, (p) => u(p)),
      h = _.useRef({
        paused: !1,
        pause() {
          this.paused = !0;
        },
        resume() {
          this.paused = !1;
        },
      }).current;
    _.useEffect(() => {
      if (r) {
        let p = function (w) {
            if (h.paused || !a) return;
            const x = w.target;
            a.contains(x) ? (f.current = x) : ar(f.current, { select: !0 });
          },
          y = function (w) {
            if (h.paused || !a) return;
            const x = w.relatedTarget;
            x !== null && (a.contains(x) || ar(f.current, { select: !0 }));
          },
          m = function (w) {
            if (document.activeElement === document.body)
              for (const b of w) b.removedNodes.length > 0 && ar(a);
          };
        document.addEventListener("focusin", p), document.addEventListener("focusout", y);
        const g = new MutationObserver(m);
        return (
          a && g.observe(a, { childList: !0, subtree: !0 }),
          () => {
            document.removeEventListener("focusin", p),
              document.removeEventListener("focusout", y),
              g.disconnect();
          }
        );
      }
    }, [r, a, h.paused]),
      _.useEffect(() => {
        if (a) {
          GC.add(h);
          const p = document.activeElement;
          if (!a.contains(p)) {
            const m = new CustomEvent(cg, UC);
            a.addEventListener(cg, l),
              a.dispatchEvent(m),
              m.defaultPrevented ||
                (j9(B9(oM(a)), { select: !0 }), document.activeElement === p && ar(a));
          }
          return () => {
            a.removeEventListener(cg, l),
              setTimeout(() => {
                const m = new CustomEvent(fg, UC);
                a.addEventListener(fg, c),
                  a.dispatchEvent(m),
                  m.defaultPrevented || ar(p ?? document.body, { select: !0 }),
                  a.removeEventListener(fg, c),
                  GC.remove(h);
              }, 0);
          };
        }
      }, [a, l, c, h]);
    const v = _.useCallback(
      (p) => {
        if ((!n && !r) || h.paused) return;
        const y = p.key === "Tab" && !p.altKey && !p.ctrlKey && !p.metaKey,
          m = document.activeElement;
        if (y && m) {
          const g = p.currentTarget,
            [w, x] = V9(g);
          w && x
            ? !p.shiftKey && m === x
              ? (p.preventDefault(), n && ar(w, { select: !0 }))
              : p.shiftKey && m === w && (p.preventDefault(), n && ar(x, { select: !0 }))
            : m === g && p.preventDefault();
        }
      },
      [n, r, h.paused],
    );
    return R.jsx(ct.div, { tabIndex: -1, ...s, ref: d, onKeyDown: v });
  });
iM.displayName = F9;
function j9(e, { select: t = !1 } = {}) {
  const n = document.activeElement;
  for (const r of e) if ((ar(r, { select: t }), document.activeElement !== n)) return;
}
function V9(e) {
  const t = oM(e),
    n = HC(t, e),
    r = HC(t.reverse(), e);
  return [n, r];
}
function oM(e) {
  const t = [],
    n = document.createTreeWalker(e, NodeFilter.SHOW_ELEMENT, {
      acceptNode: (r) => {
        const i = r.tagName === "INPUT" && r.type === "hidden";
        return r.disabled || r.hidden || i
          ? NodeFilter.FILTER_SKIP
          : r.tabIndex >= 0
            ? NodeFilter.FILTER_ACCEPT
            : NodeFilter.FILTER_SKIP;
      },
    });
  for (; n.nextNode(); ) t.push(n.currentNode);
  return t;
}
function HC(e, t) {
  for (const n of e) if (!q9(n, { upTo: t })) return n;
}
function q9(e, { upTo: t }) {
  if (getComputedStyle(e).visibility === "hidden") return !0;
  for (; e; ) {
    if (t !== void 0 && e === t) return !1;
    if (getComputedStyle(e).display === "none") return !0;
    e = e.parentElement;
  }
  return !1;
}
function $9(e) {
  return e instanceof HTMLInputElement && "select" in e;
}
function ar(e, { select: t = !1 } = {}) {
  if (e && e.focus) {
    const n = document.activeElement;
    e.focus({ preventScroll: !0 }), e !== n && $9(e) && t && e.select();
  }
}
var GC = z9();
function z9() {
  let e = [];
  return {
    add(t) {
      const n = e[0];
      t !== n && (n == null || n.pause()), (e = WC(e, t)), e.unshift(t);
    },
    remove(t) {
      var n;
      (e = WC(e, t)), (n = e[0]) == null || n.resume();
    },
  };
}
function WC(e, t) {
  const n = [...e],
    r = n.indexOf(t);
  return r !== -1 && n.splice(r, 1), n;
}
function B9(e) {
  return e.filter((t) => t.tagName !== "A");
}
var U9 = "Portal",
  sM = _.forwardRef((e, t) => {
    var a;
    const { container: n, ...r } = e,
      [i, o] = _.useState(!1);
    ea(() => o(!0), []);
    const s =
      n ||
      (i && ((a = globalThis == null ? void 0 : globalThis.document) == null ? void 0 : a.body));
    return s ? TF.createPortal(R.jsx(ct.div, { ...r, ref: t }), s) : null;
  });
sM.displayName = U9;
var dg = 0;
function H9() {
  _.useEffect(() => {
    const e = document.querySelectorAll("[data-radix-focus-guard]");
    return (
      document.body.insertAdjacentElement("afterbegin", e[0] ?? KC()),
      document.body.insertAdjacentElement("beforeend", e[1] ?? KC()),
      dg++,
      () => {
        dg === 1 &&
          document.querySelectorAll("[data-radix-focus-guard]").forEach((t) => t.remove()),
          dg--;
      }
    );
  }, []);
}
function KC() {
  const e = document.createElement("span");
  return (
    e.setAttribute("data-radix-focus-guard", ""),
    (e.tabIndex = 0),
    (e.style.outline = "none"),
    (e.style.opacity = "0"),
    (e.style.position = "fixed"),
    (e.style.pointerEvents = "none"),
    e
  );
}
var mn = function () {
  return (
    (mn =
      Object.assign ||
      function (t) {
        for (var n, r = 1, i = arguments.length; r < i; r++) {
          n = arguments[r];
          for (var o in n) Object.prototype.hasOwnProperty.call(n, o) && (t[o] = n[o]);
        }
        return t;
      }),
    mn.apply(this, arguments)
  );
};
function aM(e, t) {
  var n = {};
  for (var r in e) Object.prototype.hasOwnProperty.call(e, r) && t.indexOf(r) < 0 && (n[r] = e[r]);
  if (e != null && typeof Object.getOwnPropertySymbols == "function")
    for (var i = 0, r = Object.getOwnPropertySymbols(e); i < r.length; i++)
      t.indexOf(r[i]) < 0 &&
        Object.prototype.propertyIsEnumerable.call(e, r[i]) &&
        (n[r[i]] = e[r[i]]);
  return n;
}
function G9(e, t, n) {
  if (n || arguments.length === 2)
    for (var r = 0, i = t.length, o; r < i; r++)
      (o || !(r in t)) && (o || (o = Array.prototype.slice.call(t, 0, r)), (o[r] = t[r]));
  return e.concat(o || Array.prototype.slice.call(t));
}
var Ru = "right-scroll-bar-position",
  Pu = "width-before-scroll-bar",
  W9 = "with-scroll-bars-hidden",
  K9 = "--removed-body-scroll-bar-size";
function hg(e, t) {
  return typeof e == "function" ? e(t) : e && (e.current = t), e;
}
function Y9(e, t) {
  var n = _.useState(function () {
    return {
      value: e,
      callback: t,
      facade: {
        get current() {
          return n.value;
        },
        set current(r) {
          var i = n.value;
          i !== r && ((n.value = r), n.callback(r, i));
        },
      },
    };
  })[0];
  return (n.callback = t), n.facade;
}
var X9 = typeof window < "u" ? _.useLayoutEffect : _.useEffect,
  YC = new WeakMap();
function Z9(e, t) {
  var n = Y9(null, function (r) {
    return e.forEach(function (i) {
      return hg(i, r);
    });
  });
  return (
    X9(
      function () {
        var r = YC.get(n);
        if (r) {
          var i = new Set(r),
            o = new Set(e),
            s = n.current;
          i.forEach(function (a) {
            o.has(a) || hg(a, null);
          }),
            o.forEach(function (a) {
              i.has(a) || hg(a, s);
            });
        }
        YC.set(n, e);
      },
      [e],
    ),
    n
  );
}
function Q9(e) {
  return e;
}
function J9(e, t) {
  t === void 0 && (t = Q9);
  var n = [],
    r = !1,
    i = {
      read: function () {
        if (r)
          throw new Error(
            "Sidecar: could not `read` from an `assigned` medium. `read` could be used only with `useMedium`.",
          );
        return n.length ? n[n.length - 1] : e;
      },
      useMedium: function (o) {
        var s = t(o, r);
        return (
          n.push(s),
          function () {
            n = n.filter(function (a) {
              return a !== s;
            });
          }
        );
      },
      assignSyncMedium: function (o) {
        for (r = !0; n.length; ) {
          var s = n;
          (n = []), s.forEach(o);
        }
        n = {
          push: function (a) {
            return o(a);
          },
          filter: function () {
            return n;
          },
        };
      },
      assignMedium: function (o) {
        r = !0;
        var s = [];
        if (n.length) {
          var a = n;
          (n = []), a.forEach(o), (s = n);
        }
        var u = function () {
            var c = s;
            (s = []), c.forEach(o);
          },
          l = function () {
            return Promise.resolve().then(u);
          };
        l(),
          (n = {
            push: function (c) {
              s.push(c), l();
            },
            filter: function (c) {
              return (s = s.filter(c)), n;
            },
          });
      },
    };
  return i;
}
function eG(e) {
  e === void 0 && (e = {});
  var t = J9(null);
  return (t.options = mn({ async: !0, ssr: !1 }, e)), t;
}
var uM = function (e) {
  var t = e.sideCar,
    n = aM(e, ["sideCar"]);
  if (!t) throw new Error("Sidecar: please provide `sideCar` property to import the right car");
  var r = t.read();
  if (!r) throw new Error("Sidecar medium not found");
  return _.createElement(r, mn({}, n));
};
uM.isSideCarExport = !0;
function tG(e, t) {
  return e.useMedium(t), uM;
}
var lM = eG(),
  pg = function () {},
  wc = _.forwardRef(function (e, t) {
    var n = _.useRef(null),
      r = _.useState({ onScrollCapture: pg, onWheelCapture: pg, onTouchMoveCapture: pg }),
      i = r[0],
      o = r[1],
      s = e.forwardProps,
      a = e.children,
      u = e.className,
      l = e.removeScrollBar,
      c = e.enabled,
      f = e.shards,
      d = e.sideCar,
      h = e.noRelative,
      v = e.noIsolation,
      p = e.inert,
      y = e.allowPinchZoom,
      m = e.as,
      g = m === void 0 ? "div" : m,
      w = e.gapMode,
      x = aM(e, [
        "forwardProps",
        "children",
        "className",
        "removeScrollBar",
        "enabled",
        "shards",
        "sideCar",
        "noRelative",
        "noIsolation",
        "inert",
        "allowPinchZoom",
        "as",
        "gapMode",
      ]),
      b = d,
      E = Z9([n, t]),
      C = mn(mn({}, x), i);
    return _.createElement(
      _.Fragment,
      null,
      c &&
        _.createElement(b, {
          sideCar: lM,
          removeScrollBar: l,
          shards: f,
          noRelative: h,
          noIsolation: v,
          inert: p,
          setCallbacks: o,
          allowPinchZoom: !!y,
          lockRef: n,
          gapMode: w,
        }),
      s
        ? _.cloneElement(_.Children.only(a), mn(mn({}, C), { ref: E }))
        : _.createElement(g, mn({}, C, { className: u, ref: E }), a),
    );
  });
wc.defaultProps = { enabled: !0, removeScrollBar: !0, inert: !1 };
wc.classNames = { fullWidth: Pu, zeroRight: Ru };
var nG = function () {
  if (typeof __webpack_nonce__ < "u") return __webpack_nonce__;
};
function rG() {
  if (!document) return null;
  var e = document.createElement("style");
  e.type = "text/css";
  var t = nG();
  return t && e.setAttribute("nonce", t), e;
}
function iG(e, t) {
  e.styleSheet ? (e.styleSheet.cssText = t) : e.appendChild(document.createTextNode(t));
}
function oG(e) {
  var t = document.head || document.getElementsByTagName("head")[0];
  t.appendChild(e);
}
var sG = function () {
    var e = 0,
      t = null;
    return {
      add: function (n) {
        e == 0 && (t = rG()) && (iG(t, n), oG(t)), e++;
      },
      remove: function () {
        e--, !e && t && (t.parentNode && t.parentNode.removeChild(t), (t = null));
      },
    };
  },
  aG = function () {
    var e = sG();
    return function (t, n) {
      _.useEffect(
        function () {
          return (
            e.add(t),
            function () {
              e.remove();
            }
          );
        },
        [t && n],
      );
    };
  },
  cM = function () {
    var e = aG(),
      t = function (n) {
        var r = n.styles,
          i = n.dynamic;
        return e(r, i), null;
      };
    return t;
  },
  uG = { left: 0, top: 0, right: 0, gap: 0 },
  mg = function (e) {
    return parseInt(e || "", 10) || 0;
  },
  lG = function (e) {
    var t = window.getComputedStyle(document.body),
      n = t[e === "padding" ? "paddingLeft" : "marginLeft"],
      r = t[e === "padding" ? "paddingTop" : "marginTop"],
      i = t[e === "padding" ? "paddingRight" : "marginRight"];
    return [mg(n), mg(r), mg(i)];
  },
  cG = function (e) {
    if ((e === void 0 && (e = "margin"), typeof window > "u")) return uG;
    var t = lG(e),
      n = document.documentElement.clientWidth,
      r = window.innerWidth;
    return { left: t[0], top: t[1], right: t[2], gap: Math.max(0, r - n + t[2] - t[0]) };
  },
  fG = cM(),
  no = "data-scroll-locked",
  dG = function (e, t, n, r) {
    var i = e.left,
      o = e.top,
      s = e.right,
      a = e.gap;
    return (
      n === void 0 && (n = "margin"),
      `
  .`
        .concat(
          W9,
          ` {
   overflow: hidden `,
        )
        .concat(
          r,
          `;
   padding-right: `,
        )
        .concat(a, "px ")
        .concat(
          r,
          `;
  }
  body[`,
        )
        .concat(
          no,
          `] {
    overflow: hidden `,
        )
        .concat(
          r,
          `;
    overscroll-behavior: contain;
    `,
        )
        .concat(
          [
            t && "position: relative ".concat(r, ";"),
            n === "margin" &&
              `
    padding-left: `
                .concat(
                  i,
                  `px;
    padding-top: `,
                )
                .concat(
                  o,
                  `px;
    padding-right: `,
                )
                .concat(
                  s,
                  `px;
    margin-left:0;
    margin-top:0;
    margin-right: `,
                )
                .concat(a, "px ")
                .concat(
                  r,
                  `;
    `,
                ),
            n === "padding" && "padding-right: ".concat(a, "px ").concat(r, ";"),
          ]
            .filter(Boolean)
            .join(""),
          `
  }

  .`,
        )
        .concat(
          Ru,
          ` {
    right: `,
        )
        .concat(a, "px ")
        .concat(
          r,
          `;
  }

  .`,
        )
        .concat(
          Pu,
          ` {
    margin-right: `,
        )
        .concat(a, "px ")
        .concat(
          r,
          `;
  }

  .`,
        )
        .concat(Ru, " .")
        .concat(
          Ru,
          ` {
    right: 0 `,
        )
        .concat(
          r,
          `;
  }

  .`,
        )
        .concat(Pu, " .")
        .concat(
          Pu,
          ` {
    margin-right: 0 `,
        )
        .concat(
          r,
          `;
  }

  body[`,
        )
        .concat(
          no,
          `] {
    `,
        )
        .concat(K9, ": ")
        .concat(
          a,
          `px;
  }
`,
        )
    );
  },
  XC = function () {
    var e = parseInt(document.body.getAttribute(no) || "0", 10);
    return isFinite(e) ? e : 0;
  },
  hG = function () {
    _.useEffect(function () {
      return (
        document.body.setAttribute(no, (XC() + 1).toString()),
        function () {
          var e = XC() - 1;
          e <= 0 ? document.body.removeAttribute(no) : document.body.setAttribute(no, e.toString());
        }
      );
    }, []);
  },
  pG = function (e) {
    var t = e.noRelative,
      n = e.noImportant,
      r = e.gapMode,
      i = r === void 0 ? "margin" : r;
    hG();
    var o = _.useMemo(
      function () {
        return cG(i);
      },
      [i],
    );
    return _.createElement(fG, { styles: dG(o, !t, i, n ? "" : "!important") });
  },
  Uv = !1;
if (typeof window < "u")
  try {
    var ru = Object.defineProperty({}, "passive", {
      get: function () {
        return (Uv = !0), !0;
      },
    });
    window.addEventListener("test", ru, ru), window.removeEventListener("test", ru, ru);
  } catch {
    Uv = !1;
  }
var Ci = Uv ? { passive: !1 } : !1,
  mG = function (e) {
    return e.tagName === "TEXTAREA";
  },
  fM = function (e, t) {
    if (!(e instanceof Element)) return !1;
    var n = window.getComputedStyle(e);
    return n[t] !== "hidden" && !(n.overflowY === n.overflowX && !mG(e) && n[t] === "visible");
  },
  gG = function (e) {
    return fM(e, "overflowY");
  },
  vG = function (e) {
    return fM(e, "overflowX");
  },
  ZC = function (e, t) {
    var n = t.ownerDocument,
      r = t;
    do {
      typeof ShadowRoot < "u" && r instanceof ShadowRoot && (r = r.host);
      var i = dM(e, r);
      if (i) {
        var o = hM(e, r),
          s = o[1],
          a = o[2];
        if (s > a) return !0;
      }
      r = r.parentNode;
    } while (r && r !== n.body);
    return !1;
  },
  yG = function (e) {
    var t = e.scrollTop,
      n = e.scrollHeight,
      r = e.clientHeight;
    return [t, n, r];
  },
  wG = function (e) {
    var t = e.scrollLeft,
      n = e.scrollWidth,
      r = e.clientWidth;
    return [t, n, r];
  },
  dM = function (e, t) {
    return e === "v" ? gG(t) : vG(t);
  },
  hM = function (e, t) {
    return e === "v" ? yG(t) : wG(t);
  },
  xG = function (e, t) {
    return e === "h" && t === "rtl" ? -1 : 1;
  },
  _G = function (e, t, n, r, i) {
    var o = xG(e, window.getComputedStyle(t).direction),
      s = o * r,
      a = n.target,
      u = t.contains(a),
      l = !1,
      c = s > 0,
      f = 0,
      d = 0;
    do {
      if (!a) break;
      var h = hM(e, a),
        v = h[0],
        p = h[1],
        y = h[2],
        m = p - y - o * v;
      (v || m) && dM(e, a) && ((f += m), (d += v));
      var g = a.parentNode;
      a = g && g.nodeType === Node.DOCUMENT_FRAGMENT_NODE ? g.host : g;
    } while ((!u && a !== document.body) || (u && (t.contains(a) || t === a)));
    return ((c && Math.abs(f) < 1) || (!c && Math.abs(d) < 1)) && (l = !0), l;
  },
  iu = function (e) {
    return "changedTouches" in e
      ? [e.changedTouches[0].clientX, e.changedTouches[0].clientY]
      : [0, 0];
  },
  QC = function (e) {
    return [e.deltaX, e.deltaY];
  },
  JC = function (e) {
    return e && "current" in e ? e.current : e;
  },
  bG = function (e, t) {
    return e[0] === t[0] && e[1] === t[1];
  },
  SG = function (e) {
    return `
  .block-interactivity-`
      .concat(
        e,
        ` {pointer-events: none;}
  .allow-interactivity-`,
      )
      .concat(
        e,
        ` {pointer-events: all;}
`,
      );
  },
  EG = 0,
  Ti = [];
function CG(e) {
  var t = _.useRef([]),
    n = _.useRef([0, 0]),
    r = _.useRef(),
    i = _.useState(EG++)[0],
    o = _.useState(cM)[0],
    s = _.useRef(e);
  _.useEffect(
    function () {
      s.current = e;
    },
    [e],
  ),
    _.useEffect(
      function () {
        if (e.inert) {
          document.body.classList.add("block-interactivity-".concat(i));
          var p = G9([e.lockRef.current], (e.shards || []).map(JC), !0).filter(Boolean);
          return (
            p.forEach(function (y) {
              return y.classList.add("allow-interactivity-".concat(i));
            }),
            function () {
              document.body.classList.remove("block-interactivity-".concat(i)),
                p.forEach(function (y) {
                  return y.classList.remove("allow-interactivity-".concat(i));
                });
            }
          );
        }
      },
      [e.inert, e.lockRef.current, e.shards],
    );
  var a = _.useCallback(function (p, y) {
      if (("touches" in p && p.touches.length === 2) || (p.type === "wheel" && p.ctrlKey))
        return !s.current.allowPinchZoom;
      var m = iu(p),
        g = n.current,
        w = "deltaX" in p ? p.deltaX : g[0] - m[0],
        x = "deltaY" in p ? p.deltaY : g[1] - m[1],
        b,
        E = p.target,
        C = Math.abs(w) > Math.abs(x) ? "h" : "v";
      if ("touches" in p && C === "h" && E.type === "range") return !1;
      var T = ZC(C, E);
      if (!T) return !0;
      if ((T ? (b = C) : ((b = C === "v" ? "h" : "v"), (T = ZC(C, E))), !T)) return !1;
      if ((!r.current && "changedTouches" in p && (w || x) && (r.current = b), !b)) return !0;
      var P = r.current || b;
      return _G(P, y, p, P === "h" ? w : x);
    }, []),
    u = _.useCallback(function (p) {
      var y = p;
      if (!(!Ti.length || Ti[Ti.length - 1] !== o)) {
        var m = "deltaY" in y ? QC(y) : iu(y),
          g = t.current.filter(function (b) {
            return (
              b.name === y.type &&
              (b.target === y.target || y.target === b.shadowParent) &&
              bG(b.delta, m)
            );
          })[0];
        if (g && g.should) {
          y.cancelable && y.preventDefault();
          return;
        }
        if (!g) {
          var w = (s.current.shards || [])
              .map(JC)
              .filter(Boolean)
              .filter(function (b) {
                return b.contains(y.target);
              }),
            x = w.length > 0 ? a(y, w[0]) : !s.current.noIsolation;
          x && y.cancelable && y.preventDefault();
        }
      }
    }, []),
    l = _.useCallback(function (p, y, m, g) {
      var w = { name: p, delta: y, target: m, should: g, shadowParent: TG(m) };
      t.current.push(w),
        setTimeout(function () {
          t.current = t.current.filter(function (x) {
            return x !== w;
          });
        }, 1);
    }, []),
    c = _.useCallback(function (p) {
      (n.current = iu(p)), (r.current = void 0);
    }, []),
    f = _.useCallback(function (p) {
      l(p.type, QC(p), p.target, a(p, e.lockRef.current));
    }, []),
    d = _.useCallback(function (p) {
      l(p.type, iu(p), p.target, a(p, e.lockRef.current));
    }, []);
  _.useEffect(function () {
    return (
      Ti.push(o),
      e.setCallbacks({ onScrollCapture: f, onWheelCapture: f, onTouchMoveCapture: d }),
      document.addEventListener("wheel", u, Ci),
      document.addEventListener("touchmove", u, Ci),
      document.addEventListener("touchstart", c, Ci),
      function () {
        (Ti = Ti.filter(function (p) {
          return p !== o;
        })),
          document.removeEventListener("wheel", u, Ci),
          document.removeEventListener("touchmove", u, Ci),
          document.removeEventListener("touchstart", c, Ci);
      }
    );
  }, []);
  var h = e.removeScrollBar,
    v = e.inert;
  return _.createElement(
    _.Fragment,
    null,
    v ? _.createElement(o, { styles: SG(i) }) : null,
    h ? _.createElement(pG, { noRelative: e.noRelative, gapMode: e.gapMode }) : null,
  );
}
function TG(e) {
  for (var t = null; e !== null; )
    e instanceof ShadowRoot && ((t = e.host), (e = e.host)), (e = e.parentNode);
  return t;
}
const kG = tG(lM, CG);
var pM = _.forwardRef(function (e, t) {
  return _.createElement(wc, mn({}, e, { ref: t, sideCar: kG }));
});
pM.classNames = wc.classNames;
var RG = function (e) {
    if (typeof document > "u") return null;
    var t = Array.isArray(e) ? e[0] : e;
    return t.ownerDocument.body;
  },
  ki = new WeakMap(),
  ou = new WeakMap(),
  su = {},
  gg = 0,
  mM = function (e) {
    return e && (e.host || mM(e.parentNode));
  },
  PG = function (e, t) {
    return t
      .map(function (n) {
        if (e.contains(n)) return n;
        var r = mM(n);
        return r && e.contains(r)
          ? r
          : (console.error("aria-hidden", n, "in not contained inside", e, ". Doing nothing"),
            null);
      })
      .filter(function (n) {
        return !!n;
      });
  },
  AG = function (e, t, n, r) {
    var i = PG(t, Array.isArray(e) ? e : [e]);
    su[n] || (su[n] = new WeakMap());
    var o = su[n],
      s = [],
      a = new Set(),
      u = new Set(i),
      l = function (f) {
        !f || a.has(f) || (a.add(f), l(f.parentNode));
      };
    i.forEach(l);
    var c = function (f) {
      !f ||
        u.has(f) ||
        Array.prototype.forEach.call(f.children, function (d) {
          if (a.has(d)) c(d);
          else
            try {
              var h = d.getAttribute(r),
                v = h !== null && h !== "false",
                p = (ki.get(d) || 0) + 1,
                y = (o.get(d) || 0) + 1;
              ki.set(d, p),
                o.set(d, y),
                s.push(d),
                p === 1 && v && ou.set(d, !0),
                y === 1 && d.setAttribute(n, "true"),
                v || d.setAttribute(r, "true");
            } catch (m) {
              console.error("aria-hidden: cannot operate on ", d, m);
            }
        });
    };
    return (
      c(t),
      a.clear(),
      gg++,
      function () {
        s.forEach(function (f) {
          var d = ki.get(f) - 1,
            h = o.get(f) - 1;
          ki.set(f, d),
            o.set(f, h),
            d || (ou.has(f) || f.removeAttribute(r), ou.delete(f)),
            h || f.removeAttribute(n);
        }),
          gg--,
          gg || ((ki = new WeakMap()), (ki = new WeakMap()), (ou = new WeakMap()), (su = {}));
      }
    );
  },
  NG = function (e, t, n) {
    n === void 0 && (n = "data-aria-hidden");
    var r = Array.from(Array.isArray(e) ? e : [e]),
      i = RG(e);
    return i
      ? (r.push.apply(r, Array.from(i.querySelectorAll("[aria-live], script"))),
        AG(r, i, n, "aria-hidden"))
      : function () {
          return null;
        };
  },
  xc = "Dialog",
  [gM, MX] = vc(xc),
  [MG, an] = gM(xc),
  vM = (e) => {
    const {
        __scopeDialog: t,
        children: n,
        open: r,
        defaultOpen: i,
        onOpenChange: o,
        modal: s = !0,
      } = e,
      a = _.useRef(null),
      u = _.useRef(null),
      [l, c] = $0({ prop: r, defaultProp: i ?? !1, onChange: o, caller: xc });
    return R.jsx(MG, {
      scope: t,
      triggerRef: a,
      contentRef: u,
      contentId: Ss(),
      titleId: Ss(),
      descriptionId: Ss(),
      open: l,
      onOpenChange: c,
      onOpenToggle: _.useCallback(() => c((f) => !f), [c]),
      modal: s,
      children: n,
    });
  };
vM.displayName = xc;
var yM = "DialogTrigger",
  IG = _.forwardRef((e, t) => {
    const { __scopeDialog: n, ...r } = e,
      i = an(yM, n),
      o = bn(t, i.triggerRef);
    return R.jsx(ct.button, {
      type: "button",
      "aria-haspopup": "dialog",
      "aria-expanded": i.open,
      "aria-controls": i.contentId,
      "data-state": H0(i.open),
      ...r,
      ref: o,
      onClick: Ye(e.onClick, i.onOpenToggle),
    });
  });
IG.displayName = yM;
var B0 = "DialogPortal",
  [DG, wM] = gM(B0, { forceMount: void 0 }),
  xM = (e) => {
    const { __scopeDialog: t, forceMount: n, children: r, container: i } = e,
      o = an(B0, t);
    return R.jsx(DG, {
      scope: t,
      forceMount: n,
      children: _.Children.map(r, (s) =>
        R.jsx(ba, {
          present: n || o.open,
          children: R.jsx(sM, { asChild: !0, container: i, children: s }),
        }),
      ),
    });
  };
xM.displayName = B0;
var vl = "DialogOverlay",
  _M = _.forwardRef((e, t) => {
    const n = wM(vl, e.__scopeDialog),
      { forceMount: r = n.forceMount, ...i } = e,
      o = an(vl, e.__scopeDialog);
    return o.modal
      ? R.jsx(ba, { present: r || o.open, children: R.jsx(LG, { ...i, ref: t }) })
      : null;
  });
_M.displayName = vl;
var OG = Js("DialogOverlay.RemoveScroll"),
  LG = _.forwardRef((e, t) => {
    const { __scopeDialog: n, ...r } = e,
      i = an(vl, n);
    return R.jsx(pM, {
      as: OG,
      allowPinchZoom: !0,
      shards: [i.contentRef],
      children: R.jsx(ct.div, {
        "data-state": H0(i.open),
        ...r,
        ref: t,
        style: { pointerEvents: "auto", ...r.style },
      }),
    });
  }),
  fi = "DialogContent",
  bM = _.forwardRef((e, t) => {
    const n = wM(fi, e.__scopeDialog),
      { forceMount: r = n.forceMount, ...i } = e,
      o = an(fi, e.__scopeDialog);
    return R.jsx(ba, {
      present: r || o.open,
      children: o.modal ? R.jsx(FG, { ...i, ref: t }) : R.jsx(jG, { ...i, ref: t }),
    });
  });
bM.displayName = fi;
var FG = _.forwardRef((e, t) => {
    const n = an(fi, e.__scopeDialog),
      r = _.useRef(null),
      i = bn(t, n.contentRef, r);
    return (
      _.useEffect(() => {
        const o = r.current;
        if (o) return NG(o);
      }, []),
      R.jsx(SM, {
        ...e,
        ref: i,
        trapFocus: n.open,
        disableOutsidePointerEvents: !0,
        onCloseAutoFocus: Ye(e.onCloseAutoFocus, (o) => {
          var s;
          o.preventDefault(), (s = n.triggerRef.current) == null || s.focus();
        }),
        onPointerDownOutside: Ye(e.onPointerDownOutside, (o) => {
          const s = o.detail.originalEvent,
            a = s.button === 0 && s.ctrlKey === !0;
          (s.button === 2 || a) && o.preventDefault();
        }),
        onFocusOutside: Ye(e.onFocusOutside, (o) => o.preventDefault()),
      })
    );
  }),
  jG = _.forwardRef((e, t) => {
    const n = an(fi, e.__scopeDialog),
      r = _.useRef(!1),
      i = _.useRef(!1);
    return R.jsx(SM, {
      ...e,
      ref: t,
      trapFocus: !1,
      disableOutsidePointerEvents: !1,
      onCloseAutoFocus: (o) => {
        var s, a;
        (s = e.onCloseAutoFocus) == null || s.call(e, o),
          o.defaultPrevented ||
            (r.current || (a = n.triggerRef.current) == null || a.focus(), o.preventDefault()),
          (r.current = !1),
          (i.current = !1);
      },
      onInteractOutside: (o) => {
        var u, l;
        (u = e.onInteractOutside) == null || u.call(e, o),
          o.defaultPrevented ||
            ((r.current = !0), o.detail.originalEvent.type === "pointerdown" && (i.current = !0));
        const s = o.target;
        ((l = n.triggerRef.current) == null ? void 0 : l.contains(s)) && o.preventDefault(),
          o.detail.originalEvent.type === "focusin" && i.current && o.preventDefault();
      },
    });
  }),
  SM = _.forwardRef((e, t) => {
    const { __scopeDialog: n, trapFocus: r, onOpenAutoFocus: i, onCloseAutoFocus: o, ...s } = e,
      a = an(fi, n),
      u = _.useRef(null),
      l = bn(t, u);
    return (
      H9(),
      R.jsxs(R.Fragment, {
        children: [
          R.jsx(iM, {
            asChild: !0,
            loop: !0,
            trapped: r,
            onMountAutoFocus: i,
            onUnmountAutoFocus: o,
            children: R.jsx(nM, {
              role: "dialog",
              id: a.contentId,
              "aria-describedby": a.descriptionId,
              "aria-labelledby": a.titleId,
              "data-state": H0(a.open),
              ...s,
              ref: l,
              onDismiss: () => a.onOpenChange(!1),
            }),
          }),
          R.jsxs(R.Fragment, {
            children: [
              R.jsx(VG, { titleId: a.titleId }),
              R.jsx($G, { contentRef: u, descriptionId: a.descriptionId }),
            ],
          }),
        ],
      })
    );
  }),
  U0 = "DialogTitle",
  EM = _.forwardRef((e, t) => {
    const { __scopeDialog: n, ...r } = e,
      i = an(U0, n);
    return R.jsx(ct.h2, { id: i.titleId, ...r, ref: t });
  });
EM.displayName = U0;
var CM = "DialogDescription",
  TM = _.forwardRef((e, t) => {
    const { __scopeDialog: n, ...r } = e,
      i = an(CM, n);
    return R.jsx(ct.p, { id: i.descriptionId, ...r, ref: t });
  });
TM.displayName = CM;
var kM = "DialogClose",
  RM = _.forwardRef((e, t) => {
    const { __scopeDialog: n, ...r } = e,
      i = an(kM, n);
    return R.jsx(ct.button, {
      type: "button",
      ...r,
      ref: t,
      onClick: Ye(e.onClick, () => i.onOpenChange(!1)),
    });
  });
RM.displayName = kM;
function H0(e) {
  return e ? "open" : "closed";
}
var PM = "DialogTitleWarning",
  [IX, AM] = JH(PM, { contentName: fi, titleName: U0, docsSlug: "dialog" }),
  VG = ({ titleId: e }) => {
    const t = AM(PM),
      n = `\`${t.contentName}\` requires a \`${t.titleName}\` for the component to be accessible for screen reader users.

If you want to hide the \`${t.titleName}\`, you can wrap it with our VisuallyHidden component.

For more information, see https://radix-ui.com/primitives/docs/components/${t.docsSlug}`;
    return (
      _.useEffect(() => {
        e && (document.getElementById(e) || console.error(n));
      }, [n, e]),
      null
    );
  },
  qG = "DialogDescriptionWarning",
  $G = ({ contentRef: e, descriptionId: t }) => {
    const r = `Warning: Missing \`Description\` or \`aria-describedby={undefined}\` for {${AM(qG).contentName}}.`;
    return (
      _.useEffect(() => {
        var o;
        const i = (o = e.current) == null ? void 0 : o.getAttribute("aria-describedby");
        t && i && (document.getElementById(t) || console.warn(r));
      }, [r, e, t]),
      null
    );
  },
  zG = vM,
  BG = xM,
  NM = _M,
  MM = bM,
  IM = EM,
  DM = TM,
  UG = RM;
const HG = zG,
  GG = BG,
  OM = _.forwardRef(({ className: e, ...t }, n) =>
    R.jsx(NM, {
      ref: n,
      className: ve(
        "fixed inset-0 z-50 bg-black/80 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0",
        e,
      ),
      ...t,
    }),
  );
OM.displayName = NM.displayName;
const LM = _.forwardRef(({ className: e, children: t, ...n }, r) =>
  R.jsxs(GG, {
    children: [
      R.jsx(OM, {}),
      R.jsxs(MM, {
        ref: r,
        className: ve(
          "fixed left-[50%] top-[50%] z-50 grid w-full max-w-lg translate-x-[-50%] translate-y-[-50%] gap-4 border bg-background p-6 shadow-lg duration-200 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95 data-[state=closed]:slide-out-to-left-1/2 data-[state=closed]:slide-out-to-top-[48%] data-[state=open]:slide-in-from-left-1/2 data-[state=open]:slide-in-from-top-[48%] sm:rounded-lg",
          e,
        ),
        ...n,
        children: [
          t,
          R.jsxs(UG, {
            className:
              "absolute right-4 top-4 rounded-sm opacity-70 ring-offset-background transition-opacity hover:opacity-100 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:pointer-events-none data-[state=open]:bg-accent data-[state=open]:text-muted-foreground",
            children: [
              R.jsx(OH, { className: "h-4 w-4" }),
              R.jsx("span", { className: "sr-only", children: "Close" }),
            ],
          }),
        ],
      }),
    ],
  }),
);
LM.displayName = MM.displayName;
const FM = ({ className: e, ...t }) =>
  R.jsx("div", { className: ve("flex flex-col space-y-1.5 text-center sm:text-left", e), ...t });
FM.displayName = "DialogHeader";
const jM = ({ className: e, ...t }) =>
  R.jsx("div", {
    className: ve("flex flex-col-reverse sm:flex-row sm:justify-end sm:space-x-2", e),
    ...t,
  });
jM.displayName = "DialogFooter";
const VM = _.forwardRef(({ className: e, ...t }, n) =>
  R.jsx(IM, {
    ref: n,
    className: ve("text-lg font-semibold leading-none tracking-tight", e),
    ...t,
  }),
);
VM.displayName = IM.displayName;
const WG = _.forwardRef(({ className: e, ...t }, n) =>
  R.jsx(DM, { ref: n, className: ve("text-sm text-muted-foreground", e), ...t }),
);
WG.displayName = DM.displayName;
const qM = _.forwardRef(({ className: e, type: t, ...n }, r) =>
  R.jsx("input", {
    type: t,
    className: ve(
      "flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-base ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium file:text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 md:text-sm",
      e,
    ),
    ref: r,
    ...n,
  }),
);
qM.displayName = "Input";
const $M = _.forwardRef(({ className: e, ...t }, n) =>
  R.jsx("textarea", {
    className: ve(
      "flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-base ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 md:text-sm",
      e,
    ),
    ref: n,
    ...t,
  }),
);
$M.displayName = "Textarea";
const zM = _.createContext({});
function G0(e) {
  const t = _.useRef(null);
  return t.current === null && (t.current = e()), t.current;
}
const W0 = _.createContext(null),
  _c = _.createContext({ transformPagePoint: (e) => e, isStatic: !1, reducedMotion: "never" });
function KG(e = !0) {
  const t = _.useContext(W0);
  if (t === null) return [!0, null];
  const { isPresent: n, onExitComplete: r, register: i } = t,
    o = _.useId();
  _.useEffect(() => {
    e && i(o);
  }, [e]);
  const s = _.useCallback(() => e && r && r(o), [o, r, e]);
  return !n && r ? [!1, s] : [!0];
}
const K0 = typeof window < "u",
  Y0 = K0 ? _.useLayoutEffect : _.useEffect,
  Ct = (e) => e;
let BM = Ct;
function X0(e) {
  let t;
  return () => (t === void 0 && (t = e()), t);
}
const yo = (e, t, n) => {
    const r = t - e;
    return r === 0 ? 1 : (n - e) / r;
  },
  $n = (e) => e * 1e3,
  zn = (e) => e / 1e3,
  YG = { useManualTiming: !1 };
function XG(e) {
  let t = new Set(),
    n = new Set(),
    r = !1,
    i = !1;
  const o = new WeakSet();
  let s = { delta: 0, timestamp: 0, isProcessing: !1 };
  function a(l) {
    o.has(l) && (u.schedule(l), e()), l(s);
  }
  const u = {
    schedule: (l, c = !1, f = !1) => {
      const h = f && r ? t : n;
      return c && o.add(l), h.has(l) || h.add(l), l;
    },
    cancel: (l) => {
      n.delete(l), o.delete(l);
    },
    process: (l) => {
      if (((s = l), r)) {
        i = !0;
        return;
      }
      (r = !0), ([t, n] = [n, t]), t.forEach(a), t.clear(), (r = !1), i && ((i = !1), u.process(l));
    },
  };
  return u;
}
const au = ["read", "resolveKeyframes", "update", "preRender", "render", "postRender"],
  ZG = 40;
function UM(e, t) {
  let n = !1,
    r = !0;
  const i = { delta: 0, timestamp: 0, isProcessing: !1 },
    o = () => (n = !0),
    s = au.reduce((m, g) => ((m[g] = XG(o)), m), {}),
    { read: a, resolveKeyframes: u, update: l, preRender: c, render: f, postRender: d } = s,
    h = () => {
      const m = performance.now();
      (n = !1),
        (i.delta = r ? 1e3 / 60 : Math.max(Math.min(m - i.timestamp, ZG), 1)),
        (i.timestamp = m),
        (i.isProcessing = !0),
        a.process(i),
        u.process(i),
        l.process(i),
        c.process(i),
        f.process(i),
        d.process(i),
        (i.isProcessing = !1),
        n && t && ((r = !1), e(h));
    },
    v = () => {
      (n = !0), (r = !0), i.isProcessing || e(h);
    };
  return {
    schedule: au.reduce((m, g) => {
      const w = s[g];
      return (m[g] = (x, b = !1, E = !1) => (n || v(), w.schedule(x, b, E))), m;
    }, {}),
    cancel: (m) => {
      for (let g = 0; g < au.length; g++) s[au[g]].cancel(m);
    },
    state: i,
    steps: s,
  };
}
const {
    schedule: fe,
    cancel: Xn,
    state: $e,
    steps: vg,
  } = UM(typeof requestAnimationFrame < "u" ? requestAnimationFrame : Ct, !0),
  HM = _.createContext({ strict: !1 }),
  eT = {
    animation: [
      "animate",
      "variants",
      "whileHover",
      "whileTap",
      "exit",
      "whileInView",
      "whileFocus",
      "whileDrag",
    ],
    exit: ["exit"],
    drag: ["drag", "dragControls"],
    focus: ["whileFocus"],
    hover: ["whileHover", "onHoverStart", "onHoverEnd"],
    tap: ["whileTap", "onTap", "onTapStart", "onTapCancel"],
    pan: ["onPan", "onPanStart", "onPanSessionStart", "onPanEnd"],
    inView: ["whileInView", "onViewportEnter", "onViewportLeave"],
    layout: ["layout", "layoutId"],
  },
  wo = {};
for (const e in eT) wo[e] = { isEnabled: (t) => eT[e].some((n) => !!t[n]) };
function QG(e) {
  for (const t in e) wo[t] = { ...wo[t], ...e[t] };
}
const JG = new Set([
  "animate",
  "exit",
  "variants",
  "initial",
  "style",
  "values",
  "variants",
  "transition",
  "transformTemplate",
  "custom",
  "inherit",
  "onBeforeLayoutMeasure",
  "onAnimationStart",
  "onAnimationComplete",
  "onUpdate",
  "onDragStart",
  "onDrag",
  "onDragEnd",
  "onMeasureDragConstraints",
  "onDirectionLock",
  "onDragTransitionEnd",
  "_dragX",
  "_dragY",
  "onHoverStart",
  "onHoverEnd",
  "onViewportEnter",
  "onViewportLeave",
  "globalTapTarget",
  "ignoreStrict",
  "viewport",
]);
function yl(e) {
  return (
    e.startsWith("while") ||
    (e.startsWith("drag") && e !== "draggable") ||
    e.startsWith("layout") ||
    e.startsWith("onTap") ||
    e.startsWith("onPan") ||
    e.startsWith("onLayout") ||
    JG.has(e)
  );
}
let GM = (e) => !yl(e);
function eW(e) {
  e && (GM = (t) => (t.startsWith("on") ? !yl(t) : e(t)));
}
try {
  eW(require("@emotion/is-prop-valid").default);
} catch {}
function tW(e, t, n) {
  const r = {};
  for (const i in e)
    (i === "values" && typeof e.values == "object") ||
      ((GM(i) ||
        (n === !0 && yl(i)) ||
        (!t && !yl(i)) ||
        (e.draggable && i.startsWith("onDrag"))) &&
        (r[i] = e[i]));
  return r;
}
function nW(e) {
  if (typeof Proxy > "u") return e;
  const t = new Map(),
    n = (...r) => e(...r);
  return new Proxy(n, {
    get: (r, i) => (i === "create" ? e : (t.has(i) || t.set(i, e(i)), t.get(i))),
  });
}
const bc = _.createContext({});
function ta(e) {
  return typeof e == "string" || Array.isArray(e);
}
function Sc(e) {
  return e !== null && typeof e == "object" && typeof e.start == "function";
}
const Z0 = ["animate", "whileInView", "whileFocus", "whileHover", "whileTap", "whileDrag", "exit"],
  Q0 = ["initial", ...Z0];
function Ec(e) {
  return Sc(e.animate) || Q0.some((t) => ta(e[t]));
}
function WM(e) {
  return !!(Ec(e) || e.variants);
}
function rW(e, t) {
  if (Ec(e)) {
    const { initial: n, animate: r } = e;
    return { initial: n === !1 || ta(n) ? n : void 0, animate: ta(r) ? r : void 0 };
  }
  return e.inherit !== !1 ? t : {};
}
function iW(e) {
  const { initial: t, animate: n } = rW(e, _.useContext(bc));
  return _.useMemo(() => ({ initial: t, animate: n }), [tT(t), tT(n)]);
}
function tT(e) {
  return Array.isArray(e) ? e.join(" ") : e;
}
const oW = Symbol.for("motionComponentSymbol");
function $i(e) {
  return e && typeof e == "object" && Object.prototype.hasOwnProperty.call(e, "current");
}
function sW(e, t, n) {
  return _.useCallback(
    (r) => {
      r && e.onMount && e.onMount(r),
        t && (r ? t.mount(r) : t.unmount()),
        n && (typeof n == "function" ? n(r) : $i(n) && (n.current = r));
    },
    [t],
  );
}
const J0 = (e) => e.replace(/([a-z])([A-Z])/gu, "$1-$2").toLowerCase(),
  aW = "framerAppearId",
  KM = "data-" + J0(aW),
  { schedule: ew } = UM(queueMicrotask, !1),
  YM = _.createContext({});
function uW(e, t, n, r, i) {
  var o, s;
  const { visualElement: a } = _.useContext(bc),
    u = _.useContext(HM),
    l = _.useContext(W0),
    c = _.useContext(_c).reducedMotion,
    f = _.useRef(null);
  (r = r || u.renderer),
    !f.current &&
      r &&
      (f.current = r(e, {
        visualState: t,
        parent: a,
        props: n,
        presenceContext: l,
        blockInitialAnimation: l ? l.initial === !1 : !1,
        reducedMotionConfig: c,
      }));
  const d = f.current,
    h = _.useContext(YM);
  d && !d.projection && i && (d.type === "html" || d.type === "svg") && lW(f.current, n, i, h);
  const v = _.useRef(!1);
  _.useInsertionEffect(() => {
    d && v.current && d.update(n, l);
  });
  const p = n[KM],
    y = _.useRef(
      !!p &&
        !(!((o = window.MotionHandoffIsComplete) === null || o === void 0) && o.call(window, p)) &&
        ((s = window.MotionHasOptimisedAnimation) === null || s === void 0
          ? void 0
          : s.call(window, p)),
    );
  return (
    Y0(() => {
      d &&
        ((v.current = !0),
        (window.MotionIsMounted = !0),
        d.updateFeatures(),
        ew.render(d.render),
        y.current && d.animationState && d.animationState.animateChanges());
    }),
    _.useEffect(() => {
      d &&
        (!y.current && d.animationState && d.animationState.animateChanges(),
        y.current &&
          (queueMicrotask(() => {
            var m;
            (m = window.MotionHandoffMarkAsComplete) === null || m === void 0 || m.call(window, p);
          }),
          (y.current = !1)));
    }),
    d
  );
}
function lW(e, t, n, r) {
  const { layoutId: i, layout: o, drag: s, dragConstraints: a, layoutScroll: u, layoutRoot: l } = t;
  (e.projection = new n(e.latestValues, t["data-framer-portal-id"] ? void 0 : XM(e.parent))),
    e.projection.setOptions({
      layoutId: i,
      layout: o,
      alwaysMeasureLayout: !!s || (a && $i(a)),
      visualElement: e,
      animationType: typeof o == "string" ? o : "both",
      initialPromotionConfig: r,
      layoutScroll: u,
      layoutRoot: l,
    });
}
function XM(e) {
  if (e) return e.options.allowProjection !== !1 ? e.projection : XM(e.parent);
}
function cW({
  preloadedFeatures: e,
  createVisualElement: t,
  useRender: n,
  useVisualState: r,
  Component: i,
}) {
  var o, s;
  e && QG(e);
  function a(l, c) {
    let f;
    const d = { ..._.useContext(_c), ...l, layoutId: fW(l) },
      { isStatic: h } = d,
      v = iW(l),
      p = r(l, h);
    if (!h && K0) {
      dW();
      const y = hW(d);
      (f = y.MeasureLayout), (v.visualElement = uW(i, p, d, t, y.ProjectionNode));
    }
    return R.jsxs(bc.Provider, {
      value: v,
      children: [
        f && v.visualElement ? R.jsx(f, { visualElement: v.visualElement, ...d }) : null,
        n(i, l, sW(p, v.visualElement, c), p, h, v.visualElement),
      ],
    });
  }
  a.displayName = `motion.${typeof i == "string" ? i : `create(${(s = (o = i.displayName) !== null && o !== void 0 ? o : i.name) !== null && s !== void 0 ? s : ""})`}`;
  const u = _.forwardRef(a);
  return (u[oW] = i), u;
}
function fW({ layoutId: e }) {
  const t = _.useContext(zM).id;
  return t && e !== void 0 ? t + "-" + e : e;
}
function dW(e, t) {
  _.useContext(HM).strict;
}
function hW(e) {
  const { drag: t, layout: n } = wo;
  if (!t && !n) return {};
  const r = { ...t, ...n };
  return {
    MeasureLayout:
      (t != null && t.isEnabled(e)) || (n != null && n.isEnabled(e)) ? r.MeasureLayout : void 0,
    ProjectionNode: r.ProjectionNode,
  };
}
const pW = [
  "animate",
  "circle",
  "defs",
  "desc",
  "ellipse",
  "g",
  "image",
  "line",
  "filter",
  "marker",
  "mask",
  "metadata",
  "path",
  "pattern",
  "polygon",
  "polyline",
  "rect",
  "stop",
  "switch",
  "symbol",
  "svg",
  "text",
  "tspan",
  "use",
  "view",
];
function tw(e) {
  return typeof e != "string" || e.includes("-") ? !1 : !!(pW.indexOf(e) > -1 || /[A-Z]/u.test(e));
}
function nT(e) {
  const t = [{}, {}];
  return (
    e == null ||
      e.values.forEach((n, r) => {
        (t[0][r] = n.get()), (t[1][r] = n.getVelocity());
      }),
    t
  );
}
function nw(e, t, n, r) {
  if (typeof t == "function") {
    const [i, o] = nT(r);
    t = t(n !== void 0 ? n : e.custom, i, o);
  }
  if ((typeof t == "string" && (t = e.variants && e.variants[t]), typeof t == "function")) {
    const [i, o] = nT(r);
    t = t(n !== void 0 ? n : e.custom, i, o);
  }
  return t;
}
const Hv = (e) => Array.isArray(e),
  mW = (e) => !!(e && typeof e == "object" && e.mix && e.toValue),
  gW = (e) => (Hv(e) ? e[e.length - 1] || 0 : e),
  Be = (e) => !!(e && e.getVelocity);
function Au(e) {
  const t = Be(e) ? e.get() : e;
  return mW(t) ? t.toValue() : t;
}
function vW({ scrapeMotionValuesFromProps: e, createRenderState: t, onUpdate: n }, r, i, o) {
  const s = { latestValues: yW(r, i, o, e), renderState: t() };
  return (
    n && ((s.onMount = (a) => n({ props: r, current: a, ...s })), (s.onUpdate = (a) => n(a))), s
  );
}
const ZM = (e) => (t, n) => {
  const r = _.useContext(bc),
    i = _.useContext(W0),
    o = () => vW(e, t, r, i);
  return n ? o() : G0(o);
};
function yW(e, t, n, r) {
  const i = {},
    o = r(e, {});
  for (const d in o) i[d] = Au(o[d]);
  let { initial: s, animate: a } = e;
  const u = Ec(e),
    l = WM(e);
  t &&
    l &&
    !u &&
    e.inherit !== !1 &&
    (s === void 0 && (s = t.initial), a === void 0 && (a = t.animate));
  let c = n ? n.initial === !1 : !1;
  c = c || s === !1;
  const f = c ? a : s;
  if (f && typeof f != "boolean" && !Sc(f)) {
    const d = Array.isArray(f) ? f : [f];
    for (let h = 0; h < d.length; h++) {
      const v = nw(e, d[h]);
      if (v) {
        const { transitionEnd: p, transition: y, ...m } = v;
        for (const g in m) {
          let w = m[g];
          if (Array.isArray(w)) {
            const x = c ? w.length - 1 : 0;
            w = w[x];
          }
          w !== null && (i[g] = w);
        }
        for (const g in p) i[g] = p[g];
      }
    }
  }
  return i;
}
const Mo = [
    "transformPerspective",
    "x",
    "y",
    "z",
    "translateX",
    "translateY",
    "translateZ",
    "scale",
    "scaleX",
    "scaleY",
    "rotate",
    "rotateX",
    "rotateY",
    "rotateZ",
    "skew",
    "skewX",
    "skewY",
  ],
  wi = new Set(Mo),
  QM = (e) => (t) => typeof t == "string" && t.startsWith(e),
  JM = QM("--"),
  wW = QM("var(--"),
  rw = (e) => (wW(e) ? xW.test(e.split("/*")[0].trim()) : !1),
  xW = /var\(--(?:[\w-]+\s*|[\w-]+\s*,(?:\s*[^)(\s]|\s*\((?:[^)(]|\([^)(]*\))*\))+\s*)\)$/iu,
  eI = (e, t) => (t && typeof e == "number" ? t.transform(e) : e),
  Zn = (e, t, n) => (n > t ? t : n < e ? e : n),
  Io = { test: (e) => typeof e == "number", parse: parseFloat, transform: (e) => e },
  na = { ...Io, transform: (e) => Zn(0, 1, e) },
  uu = { ...Io, default: 1 },
  Sa = (e) => ({
    test: (t) => typeof t == "string" && t.endsWith(e) && t.split(" ").length === 1,
    parse: parseFloat,
    transform: (t) => `${t}${e}`,
  }),
  ur = Sa("deg"),
  xn = Sa("%"),
  Z = Sa("px"),
  _W = Sa("vh"),
  bW = Sa("vw"),
  rT = { ...xn, parse: (e) => xn.parse(e) / 100, transform: (e) => xn.transform(e * 100) },
  SW = {
    borderWidth: Z,
    borderTopWidth: Z,
    borderRightWidth: Z,
    borderBottomWidth: Z,
    borderLeftWidth: Z,
    borderRadius: Z,
    radius: Z,
    borderTopLeftRadius: Z,
    borderTopRightRadius: Z,
    borderBottomRightRadius: Z,
    borderBottomLeftRadius: Z,
    width: Z,
    maxWidth: Z,
    height: Z,
    maxHeight: Z,
    top: Z,
    right: Z,
    bottom: Z,
    left: Z,
    padding: Z,
    paddingTop: Z,
    paddingRight: Z,
    paddingBottom: Z,
    paddingLeft: Z,
    margin: Z,
    marginTop: Z,
    marginRight: Z,
    marginBottom: Z,
    marginLeft: Z,
    backgroundPositionX: Z,
    backgroundPositionY: Z,
  },
  EW = {
    rotate: ur,
    rotateX: ur,
    rotateY: ur,
    rotateZ: ur,
    scale: uu,
    scaleX: uu,
    scaleY: uu,
    scaleZ: uu,
    skew: ur,
    skewX: ur,
    skewY: ur,
    distance: Z,
    translateX: Z,
    translateY: Z,
    translateZ: Z,
    x: Z,
    y: Z,
    z: Z,
    perspective: Z,
    transformPerspective: Z,
    opacity: na,
    originX: rT,
    originY: rT,
    originZ: Z,
  },
  iT = { ...Io, transform: Math.round },
  iw = { ...SW, ...EW, zIndex: iT, size: Z, fillOpacity: na, strokeOpacity: na, numOctaves: iT },
  CW = { x: "translateX", y: "translateY", z: "translateZ", transformPerspective: "perspective" },
  TW = Mo.length;
function kW(e, t, n) {
  let r = "",
    i = !0;
  for (let o = 0; o < TW; o++) {
    const s = Mo[o],
      a = e[s];
    if (a === void 0) continue;
    let u = !0;
    if (
      (typeof a == "number"
        ? (u = a === (s.startsWith("scale") ? 1 : 0))
        : (u = parseFloat(a) === 0),
      !u || n)
    ) {
      const l = eI(a, iw[s]);
      if (!u) {
        i = !1;
        const c = CW[s] || s;
        r += `${c}(${l}) `;
      }
      n && (t[s] = l);
    }
  }
  return (r = r.trim()), n ? (r = n(t, i ? "" : r)) : i && (r = "none"), r;
}
function ow(e, t, n) {
  const { style: r, vars: i, transformOrigin: o } = e;
  let s = !1,
    a = !1;
  for (const u in t) {
    const l = t[u];
    if (wi.has(u)) {
      s = !0;
      continue;
    } else if (JM(u)) {
      i[u] = l;
      continue;
    } else {
      const c = eI(l, iw[u]);
      u.startsWith("origin") ? ((a = !0), (o[u] = c)) : (r[u] = c);
    }
  }
  if (
    (t.transform ||
      (s || n ? (r.transform = kW(t, e.transform, n)) : r.transform && (r.transform = "none")),
    a)
  ) {
    const { originX: u = "50%", originY: l = "50%", originZ: c = 0 } = o;
    r.transformOrigin = `${u} ${l} ${c}`;
  }
}
const RW = { offset: "stroke-dashoffset", array: "stroke-dasharray" },
  PW = { offset: "strokeDashoffset", array: "strokeDasharray" };
function AW(e, t, n = 1, r = 0, i = !0) {
  e.pathLength = 1;
  const o = i ? RW : PW;
  e[o.offset] = Z.transform(-r);
  const s = Z.transform(t),
    a = Z.transform(n);
  e[o.array] = `${s} ${a}`;
}
function oT(e, t, n) {
  return typeof e == "string" ? e : Z.transform(t + n * e);
}
function NW(e, t, n) {
  const r = oT(t, e.x, e.width),
    i = oT(n, e.y, e.height);
  return `${r} ${i}`;
}
function sw(
  e,
  {
    attrX: t,
    attrY: n,
    attrScale: r,
    originX: i,
    originY: o,
    pathLength: s,
    pathSpacing: a = 1,
    pathOffset: u = 0,
    ...l
  },
  c,
  f,
) {
  if ((ow(e, l, f), c)) {
    e.style.viewBox && (e.attrs.viewBox = e.style.viewBox);
    return;
  }
  (e.attrs = e.style), (e.style = {});
  const { attrs: d, style: h, dimensions: v } = e;
  d.transform && (v && (h.transform = d.transform), delete d.transform),
    v &&
      (i !== void 0 || o !== void 0 || h.transform) &&
      (h.transformOrigin = NW(v, i !== void 0 ? i : 0.5, o !== void 0 ? o : 0.5)),
    t !== void 0 && (d.x = t),
    n !== void 0 && (d.y = n),
    r !== void 0 && (d.scale = r),
    s !== void 0 && AW(d, s, a, u, !1);
}
const aw = () => ({ style: {}, transform: {}, transformOrigin: {}, vars: {} }),
  tI = () => ({ ...aw(), attrs: {} }),
  uw = (e) => typeof e == "string" && e.toLowerCase() === "svg";
function nI(e, { style: t, vars: n }, r, i) {
  Object.assign(e.style, t, i && i.getProjectionStyles(r));
  for (const o in n) e.style.setProperty(o, n[o]);
}
const rI = new Set([
  "baseFrequency",
  "diffuseConstant",
  "kernelMatrix",
  "kernelUnitLength",
  "keySplines",
  "keyTimes",
  "limitingConeAngle",
  "markerHeight",
  "markerWidth",
  "numOctaves",
  "targetX",
  "targetY",
  "surfaceScale",
  "specularConstant",
  "specularExponent",
  "stdDeviation",
  "tableValues",
  "viewBox",
  "gradientTransform",
  "pathLength",
  "startOffset",
  "textLength",
  "lengthAdjust",
]);
function iI(e, t, n, r) {
  nI(e, t, void 0, r);
  for (const i in t.attrs) e.setAttribute(rI.has(i) ? i : J0(i), t.attrs[i]);
}
const wl = {};
function MW(e) {
  Object.assign(wl, e);
}
function oI(e, { layout: t, layoutId: n }) {
  return (
    wi.has(e) || e.startsWith("origin") || ((t || n !== void 0) && (!!wl[e] || e === "opacity"))
  );
}
function lw(e, t, n) {
  var r;
  const { style: i } = e,
    o = {};
  for (const s in i)
    (Be(i[s]) ||
      (t.style && Be(t.style[s])) ||
      oI(s, e) ||
      ((r = n == null ? void 0 : n.getValue(s)) === null || r === void 0 ? void 0 : r.liveStyle) !==
        void 0) &&
      (o[s] = i[s]);
  return o;
}
function sI(e, t, n) {
  const r = lw(e, t, n);
  for (const i in e)
    if (Be(e[i]) || Be(t[i])) {
      const o = Mo.indexOf(i) !== -1 ? "attr" + i.charAt(0).toUpperCase() + i.substring(1) : i;
      r[o] = e[i];
    }
  return r;
}
function IW(e, t) {
  try {
    t.dimensions = typeof e.getBBox == "function" ? e.getBBox() : e.getBoundingClientRect();
  } catch {
    t.dimensions = { x: 0, y: 0, width: 0, height: 0 };
  }
}
const sT = ["x", "y", "width", "height", "cx", "cy", "r"],
  DW = {
    useVisualState: ZM({
      scrapeMotionValuesFromProps: sI,
      createRenderState: tI,
      onUpdate: ({ props: e, prevProps: t, current: n, renderState: r, latestValues: i }) => {
        if (!n) return;
        let o = !!e.drag;
        if (!o) {
          for (const a in i)
            if (wi.has(a)) {
              o = !0;
              break;
            }
        }
        if (!o) return;
        let s = !t;
        if (t)
          for (let a = 0; a < sT.length; a++) {
            const u = sT[a];
            e[u] !== t[u] && (s = !0);
          }
        s &&
          fe.read(() => {
            IW(n, r),
              fe.render(() => {
                sw(r, i, uw(n.tagName), e.transformTemplate), iI(n, r);
              });
          });
      },
    }),
  },
  OW = { useVisualState: ZM({ scrapeMotionValuesFromProps: lw, createRenderState: aw }) };
function aI(e, t, n) {
  for (const r in t) !Be(t[r]) && !oI(r, n) && (e[r] = t[r]);
}
function LW({ transformTemplate: e }, t) {
  return _.useMemo(() => {
    const n = aw();
    return ow(n, t, e), Object.assign({}, n.vars, n.style);
  }, [t]);
}
function FW(e, t) {
  const n = e.style || {},
    r = {};
  return aI(r, n, e), Object.assign(r, LW(e, t)), r;
}
function jW(e, t) {
  const n = {},
    r = FW(e, t);
  return (
    e.drag &&
      e.dragListener !== !1 &&
      ((n.draggable = !1),
      (r.userSelect = r.WebkitUserSelect = r.WebkitTouchCallout = "none"),
      (r.touchAction = e.drag === !0 ? "none" : `pan-${e.drag === "x" ? "y" : "x"}`)),
    e.tabIndex === void 0 && (e.onTap || e.onTapStart || e.whileTap) && (n.tabIndex = 0),
    (n.style = r),
    n
  );
}
function VW(e, t, n, r) {
  const i = _.useMemo(() => {
    const o = tI();
    return sw(o, t, uw(r), e.transformTemplate), { ...o.attrs, style: { ...o.style } };
  }, [t]);
  if (e.style) {
    const o = {};
    aI(o, e.style, e), (i.style = { ...o, ...i.style });
  }
  return i;
}
function qW(e = !1) {
  return (n, r, i, { latestValues: o }, s) => {
    const u = (tw(n) ? VW : jW)(r, o, s, n),
      l = tW(r, typeof n == "string", e),
      c = n !== _.Fragment ? { ...l, ...u, ref: i } : {},
      { children: f } = r,
      d = _.useMemo(() => (Be(f) ? f.get() : f), [f]);
    return _.createElement(n, { ...c, children: d });
  };
}
function $W(e, t) {
  return function (r, { forwardMotionProps: i } = { forwardMotionProps: !1 }) {
    const s = {
      ...(tw(r) ? DW : OW),
      preloadedFeatures: e,
      useRender: qW(i),
      createVisualElement: t,
      Component: r,
    };
    return cW(s);
  };
}
function uI(e, t) {
  if (!Array.isArray(t)) return !1;
  const n = t.length;
  if (n !== e.length) return !1;
  for (let r = 0; r < n; r++) if (t[r] !== e[r]) return !1;
  return !0;
}
function Cc(e, t, n) {
  const r = e.getProps();
  return nw(r, t, n !== void 0 ? n : r.custom, e);
}
const zW = X0(() => window.ScrollTimeline !== void 0);
class BW {
  constructor(t) {
    (this.stop = () => this.runAll("stop")), (this.animations = t.filter(Boolean));
  }
  get finished() {
    return Promise.all(this.animations.map((t) => ("finished" in t ? t.finished : t)));
  }
  getAll(t) {
    return this.animations[0][t];
  }
  setAll(t, n) {
    for (let r = 0; r < this.animations.length; r++) this.animations[r][t] = n;
  }
  attachTimeline(t, n) {
    const r = this.animations.map((i) => {
      if (zW() && i.attachTimeline) return i.attachTimeline(t);
      if (typeof n == "function") return n(i);
    });
    return () => {
      r.forEach((i, o) => {
        i && i(), this.animations[o].stop();
      });
    };
  }
  get time() {
    return this.getAll("time");
  }
  set time(t) {
    this.setAll("time", t);
  }
  get speed() {
    return this.getAll("speed");
  }
  set speed(t) {
    this.setAll("speed", t);
  }
  get startTime() {
    return this.getAll("startTime");
  }
  get duration() {
    let t = 0;
    for (let n = 0; n < this.animations.length; n++) t = Math.max(t, this.animations[n].duration);
    return t;
  }
  runAll(t) {
    this.animations.forEach((n) => n[t]());
  }
  flatten() {
    this.runAll("flatten");
  }
  play() {
    this.runAll("play");
  }
  pause() {
    this.runAll("pause");
  }
  cancel() {
    this.runAll("cancel");
  }
  complete() {
    this.runAll("complete");
  }
}
class UW extends BW {
  then(t, n) {
    return Promise.all(this.animations).then(t).catch(n);
  }
}
function cw(e, t) {
  return e ? e[t] || e.default || e : void 0;
}
const Gv = 2e4;
function lI(e) {
  let t = 0;
  const n = 50;
  let r = e.next(t);
  for (; !r.done && t < Gv; ) (t += n), (r = e.next(t));
  return t >= Gv ? 1 / 0 : t;
}
function fw(e) {
  return typeof e == "function";
}
function aT(e, t) {
  (e.timeline = t), (e.onfinish = null);
}
const dw = (e) => Array.isArray(e) && typeof e[0] == "number",
  HW = { linearEasing: void 0 };
function GW(e, t) {
  const n = X0(e);
  return () => {
    var r;
    return (r = HW[t]) !== null && r !== void 0 ? r : n();
  };
}
const xl = GW(() => {
    try {
      document.createElement("div").animate({ opacity: 0 }, { easing: "linear(0, 1)" });
    } catch {
      return !1;
    }
    return !0;
  }, "linearEasing"),
  cI = (e, t, n = 10) => {
    let r = "";
    const i = Math.max(Math.round(t / n), 2);
    for (let o = 0; o < i; o++) r += e(yo(0, i - 1, o)) + ", ";
    return `linear(${r.substring(0, r.length - 2)})`;
  };
function fI(e) {
  return !!(
    (typeof e == "function" && xl()) ||
    !e ||
    (typeof e == "string" && (e in Wv || xl())) ||
    dw(e) ||
    (Array.isArray(e) && e.every(fI))
  );
}
const fs = ([e, t, n, r]) => `cubic-bezier(${e}, ${t}, ${n}, ${r})`,
  Wv = {
    linear: "linear",
    ease: "ease",
    easeIn: "ease-in",
    easeOut: "ease-out",
    easeInOut: "ease-in-out",
    circIn: fs([0, 0.65, 0.55, 1]),
    circOut: fs([0.55, 0, 1, 0.45]),
    backIn: fs([0.31, 0.01, 0.66, -0.59]),
    backOut: fs([0.33, 1.53, 0.69, 0.99]),
  };
function dI(e, t) {
  if (e)
    return typeof e == "function" && xl()
      ? cI(e, t)
      : dw(e)
        ? fs(e)
        : Array.isArray(e)
          ? e.map((n) => dI(n, t) || Wv.easeOut)
          : Wv[e];
}
const Wt = { x: !1, y: !1 };
function hI() {
  return Wt.x || Wt.y;
}
function WW(e, t, n) {
  var r;
  if (e instanceof Element) return [e];
  if (typeof e == "string") {
    let i = document;
    const o = (r = void 0) !== null && r !== void 0 ? r : i.querySelectorAll(e);
    return o ? Array.from(o) : [];
  }
  return Array.from(e);
}
function pI(e, t) {
  const n = WW(e),
    r = new AbortController(),
    i = { passive: !0, ...t, signal: r.signal };
  return [n, i, () => r.abort()];
}
function uT(e) {
  return (t) => {
    t.pointerType === "touch" || hI() || e(t);
  };
}
function KW(e, t, n = {}) {
  const [r, i, o] = pI(e, n),
    s = uT((a) => {
      const { target: u } = a,
        l = t(a);
      if (typeof l != "function" || !u) return;
      const c = uT((f) => {
        l(f), u.removeEventListener("pointerleave", c);
      });
      u.addEventListener("pointerleave", c, i);
    });
  return (
    r.forEach((a) => {
      a.addEventListener("pointerenter", s, i);
    }),
    o
  );
}
const mI = (e, t) => (t ? (e === t ? !0 : mI(e, t.parentElement)) : !1),
  hw = (e) =>
    e.pointerType === "mouse" ? typeof e.button != "number" || e.button <= 0 : e.isPrimary !== !1,
  YW = new Set(["BUTTON", "INPUT", "SELECT", "TEXTAREA", "A"]);
function XW(e) {
  return YW.has(e.tagName) || e.tabIndex !== -1;
}
const ds = new WeakSet();
function lT(e) {
  return (t) => {
    t.key === "Enter" && e(t);
  };
}
function yg(e, t) {
  e.dispatchEvent(new PointerEvent("pointer" + t, { isPrimary: !0, bubbles: !0 }));
}
const ZW = (e, t) => {
  const n = e.currentTarget;
  if (!n) return;
  const r = lT(() => {
    if (ds.has(n)) return;
    yg(n, "down");
    const i = lT(() => {
        yg(n, "up");
      }),
      o = () => yg(n, "cancel");
    n.addEventListener("keyup", i, t), n.addEventListener("blur", o, t);
  });
  n.addEventListener("keydown", r, t),
    n.addEventListener("blur", () => n.removeEventListener("keydown", r), t);
};
function cT(e) {
  return hw(e) && !hI();
}
function QW(e, t, n = {}) {
  const [r, i, o] = pI(e, n),
    s = (a) => {
      const u = a.currentTarget;
      if (!cT(a) || ds.has(u)) return;
      ds.add(u);
      const l = t(a),
        c = (h, v) => {
          window.removeEventListener("pointerup", f),
            window.removeEventListener("pointercancel", d),
            !(!cT(h) || !ds.has(u)) &&
              (ds.delete(u), typeof l == "function" && l(h, { success: v }));
        },
        f = (h) => {
          c(h, n.useGlobalTarget || mI(u, h.target));
        },
        d = (h) => {
          c(h, !1);
        };
      window.addEventListener("pointerup", f, i), window.addEventListener("pointercancel", d, i);
    };
  return (
    r.forEach((a) => {
      !XW(a) && a.getAttribute("tabindex") === null && (a.tabIndex = 0),
        (n.useGlobalTarget ? window : a).addEventListener("pointerdown", s, i),
        a.addEventListener("focus", (l) => ZW(l, i), i);
    }),
    o
  );
}
function JW(e) {
  return e === "x" || e === "y"
    ? Wt[e]
      ? null
      : ((Wt[e] = !0),
        () => {
          Wt[e] = !1;
        })
    : Wt.x || Wt.y
      ? null
      : ((Wt.x = Wt.y = !0),
        () => {
          Wt.x = Wt.y = !1;
        });
}
const gI = new Set(["width", "height", "top", "left", "right", "bottom", ...Mo]);
let Nu;
function e7() {
  Nu = void 0;
}
const _n = {
  now: () => (
    Nu === void 0 &&
      _n.set($e.isProcessing || YG.useManualTiming ? $e.timestamp : performance.now()),
    Nu
  ),
  set: (e) => {
    (Nu = e), queueMicrotask(e7);
  },
};
function pw(e, t) {
  e.indexOf(t) === -1 && e.push(t);
}
function mw(e, t) {
  const n = e.indexOf(t);
  n > -1 && e.splice(n, 1);
}
class gw {
  constructor() {
    this.subscriptions = [];
  }
  add(t) {
    return pw(this.subscriptions, t), () => mw(this.subscriptions, t);
  }
  notify(t, n, r) {
    const i = this.subscriptions.length;
    if (i)
      if (i === 1) this.subscriptions[0](t, n, r);
      else
        for (let o = 0; o < i; o++) {
          const s = this.subscriptions[o];
          s && s(t, n, r);
        }
  }
  getSize() {
    return this.subscriptions.length;
  }
  clear() {
    this.subscriptions.length = 0;
  }
}
function vI(e, t) {
  return t ? e * (1e3 / t) : 0;
}
const fT = 30,
  t7 = (e) => !isNaN(parseFloat(e)),
  Es = { current: void 0 };
class n7 {
  constructor(t, n = {}) {
    (this.version = "11.18.2"),
      (this.canTrackVelocity = null),
      (this.events = {}),
      (this.updateAndNotify = (r, i = !0) => {
        const o = _n.now();
        this.updatedAt !== o && this.setPrevFrameValue(),
          (this.prev = this.current),
          this.setCurrent(r),
          this.current !== this.prev &&
            this.events.change &&
            this.events.change.notify(this.current),
          i && this.events.renderRequest && this.events.renderRequest.notify(this.current);
      }),
      (this.hasAnimated = !1),
      this.setCurrent(t),
      (this.owner = n.owner);
  }
  setCurrent(t) {
    (this.current = t),
      (this.updatedAt = _n.now()),
      this.canTrackVelocity === null && t !== void 0 && (this.canTrackVelocity = t7(this.current));
  }
  setPrevFrameValue(t = this.current) {
    (this.prevFrameValue = t), (this.prevUpdatedAt = this.updatedAt);
  }
  onChange(t) {
    return this.on("change", t);
  }
  on(t, n) {
    this.events[t] || (this.events[t] = new gw());
    const r = this.events[t].add(n);
    return t === "change"
      ? () => {
          r(),
            fe.read(() => {
              this.events.change.getSize() || this.stop();
            });
        }
      : r;
  }
  clearListeners() {
    for (const t in this.events) this.events[t].clear();
  }
  attach(t, n) {
    (this.passiveEffect = t), (this.stopPassiveEffect = n);
  }
  set(t, n = !0) {
    !n || !this.passiveEffect
      ? this.updateAndNotify(t, n)
      : this.passiveEffect(t, this.updateAndNotify);
  }
  setWithVelocity(t, n, r) {
    this.set(n),
      (this.prev = void 0),
      (this.prevFrameValue = t),
      (this.prevUpdatedAt = this.updatedAt - r);
  }
  jump(t, n = !0) {
    this.updateAndNotify(t),
      (this.prev = t),
      (this.prevUpdatedAt = this.prevFrameValue = void 0),
      n && this.stop(),
      this.stopPassiveEffect && this.stopPassiveEffect();
  }
  get() {
    return Es.current && Es.current.push(this), this.current;
  }
  getPrevious() {
    return this.prev;
  }
  getVelocity() {
    const t = _n.now();
    if (!this.canTrackVelocity || this.prevFrameValue === void 0 || t - this.updatedAt > fT)
      return 0;
    const n = Math.min(this.updatedAt - this.prevUpdatedAt, fT);
    return vI(parseFloat(this.current) - parseFloat(this.prevFrameValue), n);
  }
  start(t) {
    return (
      this.stop(),
      new Promise((n) => {
        (this.hasAnimated = !0),
          (this.animation = t(n)),
          this.events.animationStart && this.events.animationStart.notify();
      }).then(() => {
        this.events.animationComplete && this.events.animationComplete.notify(),
          this.clearAnimation();
      })
    );
  }
  stop() {
    this.animation &&
      (this.animation.stop(), this.events.animationCancel && this.events.animationCancel.notify()),
      this.clearAnimation();
  }
  isAnimating() {
    return !!this.animation;
  }
  clearAnimation() {
    delete this.animation;
  }
  destroy() {
    this.clearListeners(), this.stop(), this.stopPassiveEffect && this.stopPassiveEffect();
  }
}
function xo(e, t) {
  return new n7(e, t);
}
function r7(e, t, n) {
  e.hasValue(t) ? e.getValue(t).set(n) : e.addValue(t, xo(n));
}
function i7(e, t) {
  const n = Cc(e, t);
  let { transitionEnd: r = {}, transition: i = {}, ...o } = n || {};
  o = { ...o, ...r };
  for (const s in o) {
    const a = gW(o[s]);
    r7(e, s, a);
  }
}
function o7(e) {
  return !!(Be(e) && e.add);
}
function Kv(e, t) {
  const n = e.getValue("willChange");
  if (o7(n)) return n.add(t);
}
function yI(e) {
  return e.props[KM];
}
const wI = (e, t, n) => (((1 - 3 * n + 3 * t) * e + (3 * n - 6 * t)) * e + 3 * t) * e,
  s7 = 1e-7,
  a7 = 12;
function u7(e, t, n, r, i) {
  let o,
    s,
    a = 0;
  do (s = t + (n - t) / 2), (o = wI(s, r, i) - e), o > 0 ? (n = s) : (t = s);
  while (Math.abs(o) > s7 && ++a < a7);
  return s;
}
function Ea(e, t, n, r) {
  if (e === t && n === r) return Ct;
  const i = (o) => u7(o, 0, 1, e, n);
  return (o) => (o === 0 || o === 1 ? o : wI(i(o), t, r));
}
const xI = (e) => (t) => (t <= 0.5 ? e(2 * t) / 2 : (2 - e(2 * (1 - t))) / 2),
  _I = (e) => (t) => 1 - e(1 - t),
  bI = Ea(0.33, 1.53, 0.69, 0.99),
  vw = _I(bI),
  SI = xI(vw),
  EI = (e) => ((e *= 2) < 1 ? 0.5 * vw(e) : 0.5 * (2 - Math.pow(2, -10 * (e - 1)))),
  yw = (e) => 1 - Math.sin(Math.acos(e)),
  CI = _I(yw),
  TI = xI(yw),
  kI = (e) => /^0[^.\s]+$/u.test(e);
function l7(e) {
  return typeof e == "number" ? e === 0 : e !== null ? e === "none" || e === "0" || kI(e) : !0;
}
const Cs = (e) => Math.round(e * 1e5) / 1e5,
  ww = /-?(?:\d+(?:\.\d+)?|\.\d+)/gu;
function c7(e) {
  return e == null;
}
const f7 =
    /^(?:#[\da-f]{3,8}|(?:rgb|hsl)a?\((?:-?[\d.]+%?[,\s]+){2}-?[\d.]+%?\s*(?:[,/]\s*)?(?:\b\d+(?:\.\d+)?|\.\d+)?%?\))$/iu,
  xw = (e, t) => (n) =>
    !!(
      (typeof n == "string" && f7.test(n) && n.startsWith(e)) ||
      (t && !c7(n) && Object.prototype.hasOwnProperty.call(n, t))
    ),
  RI = (e, t, n) => (r) => {
    if (typeof r != "string") return r;
    const [i, o, s, a] = r.match(ww);
    return {
      [e]: parseFloat(i),
      [t]: parseFloat(o),
      [n]: parseFloat(s),
      alpha: a !== void 0 ? parseFloat(a) : 1,
    };
  },
  d7 = (e) => Zn(0, 255, e),
  wg = { ...Io, transform: (e) => Math.round(d7(e)) },
  Qr = {
    test: xw("rgb", "red"),
    parse: RI("red", "green", "blue"),
    transform: ({ red: e, green: t, blue: n, alpha: r = 1 }) =>
      "rgba(" +
      wg.transform(e) +
      ", " +
      wg.transform(t) +
      ", " +
      wg.transform(n) +
      ", " +
      Cs(na.transform(r)) +
      ")",
  };
function h7(e) {
  let t = "",
    n = "",
    r = "",
    i = "";
  return (
    e.length > 5
      ? ((t = e.substring(1, 3)),
        (n = e.substring(3, 5)),
        (r = e.substring(5, 7)),
        (i = e.substring(7, 9)))
      : ((t = e.substring(1, 2)),
        (n = e.substring(2, 3)),
        (r = e.substring(3, 4)),
        (i = e.substring(4, 5)),
        (t += t),
        (n += n),
        (r += r),
        (i += i)),
    {
      red: parseInt(t, 16),
      green: parseInt(n, 16),
      blue: parseInt(r, 16),
      alpha: i ? parseInt(i, 16) / 255 : 1,
    }
  );
}
const Yv = { test: xw("#"), parse: h7, transform: Qr.transform },
  zi = {
    test: xw("hsl", "hue"),
    parse: RI("hue", "saturation", "lightness"),
    transform: ({ hue: e, saturation: t, lightness: n, alpha: r = 1 }) =>
      "hsla(" +
      Math.round(e) +
      ", " +
      xn.transform(Cs(t)) +
      ", " +
      xn.transform(Cs(n)) +
      ", " +
      Cs(na.transform(r)) +
      ")",
  },
  tt = {
    test: (e) => Qr.test(e) || Yv.test(e) || zi.test(e),
    parse: (e) => (Qr.test(e) ? Qr.parse(e) : zi.test(e) ? zi.parse(e) : Yv.parse(e)),
    transform: (e) =>
      typeof e == "string" ? e : e.hasOwnProperty("red") ? Qr.transform(e) : zi.transform(e),
  },
  p7 =
    /(?:#[\da-f]{3,8}|(?:rgb|hsl)a?\((?:-?[\d.]+%?[,\s]+){2}-?[\d.]+%?\s*(?:[,/]\s*)?(?:\b\d+(?:\.\d+)?|\.\d+)?%?\))/giu;
function m7(e) {
  var t, n;
  return (
    isNaN(e) &&
    typeof e == "string" &&
    (((t = e.match(ww)) === null || t === void 0 ? void 0 : t.length) || 0) +
      (((n = e.match(p7)) === null || n === void 0 ? void 0 : n.length) || 0) >
      0
  );
}
const PI = "number",
  AI = "color",
  g7 = "var",
  v7 = "var(",
  dT = "${}",
  y7 =
    /var\s*\(\s*--(?:[\w-]+\s*|[\w-]+\s*,(?:\s*[^)(\s]|\s*\((?:[^)(]|\([^)(]*\))*\))+\s*)\)|#[\da-f]{3,8}|(?:rgb|hsl)a?\((?:-?[\d.]+%?[,\s]+){2}-?[\d.]+%?\s*(?:[,/]\s*)?(?:\b\d+(?:\.\d+)?|\.\d+)?%?\)|-?(?:\d+(?:\.\d+)?|\.\d+)/giu;
function ra(e) {
  const t = e.toString(),
    n = [],
    r = { color: [], number: [], var: [] },
    i = [];
  let o = 0;
  const a = t
    .replace(
      y7,
      (u) => (
        tt.test(u)
          ? (r.color.push(o), i.push(AI), n.push(tt.parse(u)))
          : u.startsWith(v7)
            ? (r.var.push(o), i.push(g7), n.push(u))
            : (r.number.push(o), i.push(PI), n.push(parseFloat(u))),
        ++o,
        dT
      ),
    )
    .split(dT);
  return { values: n, split: a, indexes: r, types: i };
}
function NI(e) {
  return ra(e).values;
}
function MI(e) {
  const { split: t, types: n } = ra(e),
    r = t.length;
  return (i) => {
    let o = "";
    for (let s = 0; s < r; s++)
      if (((o += t[s]), i[s] !== void 0)) {
        const a = n[s];
        a === PI ? (o += Cs(i[s])) : a === AI ? (o += tt.transform(i[s])) : (o += i[s]);
      }
    return o;
  };
}
const w7 = (e) => (typeof e == "number" ? 0 : e);
function x7(e) {
  const t = NI(e);
  return MI(e)(t.map(w7));
}
const Mr = { test: m7, parse: NI, createTransformer: MI, getAnimatableNone: x7 },
  _7 = new Set(["brightness", "contrast", "saturate", "opacity"]);
function b7(e) {
  const [t, n] = e.slice(0, -1).split("(");
  if (t === "drop-shadow") return e;
  const [r] = n.match(ww) || [];
  if (!r) return e;
  const i = n.replace(r, "");
  let o = _7.has(t) ? 1 : 0;
  return r !== n && (o *= 100), t + "(" + o + i + ")";
}
const S7 = /\b([a-z-]*)\(.*?\)/gu,
  Xv = {
    ...Mr,
    getAnimatableNone: (e) => {
      const t = e.match(S7);
      return t ? t.map(b7).join(" ") : e;
    },
  },
  E7 = {
    ...iw,
    color: tt,
    backgroundColor: tt,
    outlineColor: tt,
    fill: tt,
    stroke: tt,
    borderColor: tt,
    borderTopColor: tt,
    borderRightColor: tt,
    borderBottomColor: tt,
    borderLeftColor: tt,
    filter: Xv,
    WebkitFilter: Xv,
  },
  _w = (e) => E7[e];
function II(e, t) {
  let n = _w(e);
  return n !== Xv && (n = Mr), n.getAnimatableNone ? n.getAnimatableNone(t) : void 0;
}
const C7 = new Set(["auto", "none", "0"]);
function T7(e, t, n) {
  let r = 0,
    i;
  for (; r < e.length && !i; ) {
    const o = e[r];
    typeof o == "string" && !C7.has(o) && ra(o).values.length && (i = e[r]), r++;
  }
  if (i && n) for (const o of t) e[o] = II(n, i);
}
const hT = (e) => e === Io || e === Z,
  pT = (e, t) => parseFloat(e.split(", ")[t]),
  mT =
    (e, t) =>
    (n, { transform: r }) => {
      if (r === "none" || !r) return 0;
      const i = r.match(/^matrix3d\((.+)\)$/u);
      if (i) return pT(i[1], t);
      {
        const o = r.match(/^matrix\((.+)\)$/u);
        return o ? pT(o[1], e) : 0;
      }
    },
  k7 = new Set(["x", "y", "z"]),
  R7 = Mo.filter((e) => !k7.has(e));
function P7(e) {
  const t = [];
  return (
    R7.forEach((n) => {
      const r = e.getValue(n);
      r !== void 0 && (t.push([n, r.get()]), r.set(n.startsWith("scale") ? 1 : 0));
    }),
    t
  );
}
const _o = {
  width: ({ x: e }, { paddingLeft: t = "0", paddingRight: n = "0" }) =>
    e.max - e.min - parseFloat(t) - parseFloat(n),
  height: ({ y: e }, { paddingTop: t = "0", paddingBottom: n = "0" }) =>
    e.max - e.min - parseFloat(t) - parseFloat(n),
  top: (e, { top: t }) => parseFloat(t),
  left: (e, { left: t }) => parseFloat(t),
  bottom: ({ y: e }, { top: t }) => parseFloat(t) + (e.max - e.min),
  right: ({ x: e }, { left: t }) => parseFloat(t) + (e.max - e.min),
  x: mT(4, 13),
  y: mT(5, 14),
};
_o.translateX = _o.x;
_o.translateY = _o.y;
const ri = new Set();
let Zv = !1,
  Qv = !1;
function DI() {
  if (Qv) {
    const e = Array.from(ri).filter((r) => r.needsMeasurement),
      t = new Set(e.map((r) => r.element)),
      n = new Map();
    t.forEach((r) => {
      const i = P7(r);
      i.length && (n.set(r, i), r.render());
    }),
      e.forEach((r) => r.measureInitialState()),
      t.forEach((r) => {
        r.render();
        const i = n.get(r);
        i &&
          i.forEach(([o, s]) => {
            var a;
            (a = r.getValue(o)) === null || a === void 0 || a.set(s);
          });
      }),
      e.forEach((r) => r.measureEndState()),
      e.forEach((r) => {
        r.suspendedScrollY !== void 0 && window.scrollTo(0, r.suspendedScrollY);
      });
  }
  (Qv = !1), (Zv = !1), ri.forEach((e) => e.complete()), ri.clear();
}
function OI() {
  ri.forEach((e) => {
    e.readKeyframes(), e.needsMeasurement && (Qv = !0);
  });
}
function A7() {
  OI(), DI();
}
class bw {
  constructor(t, n, r, i, o, s = !1) {
    (this.isComplete = !1),
      (this.isAsync = !1),
      (this.needsMeasurement = !1),
      (this.isScheduled = !1),
      (this.unresolvedKeyframes = [...t]),
      (this.onComplete = n),
      (this.name = r),
      (this.motionValue = i),
      (this.element = o),
      (this.isAsync = s);
  }
  scheduleResolve() {
    (this.isScheduled = !0),
      this.isAsync
        ? (ri.add(this), Zv || ((Zv = !0), fe.read(OI), fe.resolveKeyframes(DI)))
        : (this.readKeyframes(), this.complete());
  }
  readKeyframes() {
    const { unresolvedKeyframes: t, name: n, element: r, motionValue: i } = this;
    for (let o = 0; o < t.length; o++)
      if (t[o] === null)
        if (o === 0) {
          const s = i == null ? void 0 : i.get(),
            a = t[t.length - 1];
          if (s !== void 0) t[0] = s;
          else if (r && n) {
            const u = r.readValue(n, a);
            u != null && (t[0] = u);
          }
          t[0] === void 0 && (t[0] = a), i && s === void 0 && i.set(t[0]);
        } else t[o] = t[o - 1];
  }
  setFinalKeyframe() {}
  measureInitialState() {}
  renderEndStyles() {}
  measureEndState() {}
  complete() {
    (this.isComplete = !0),
      this.onComplete(this.unresolvedKeyframes, this.finalKeyframe),
      ri.delete(this);
  }
  cancel() {
    this.isComplete || ((this.isScheduled = !1), ri.delete(this));
  }
  resume() {
    this.isComplete || this.scheduleResolve();
  }
}
const LI = (e) => /^-?(?:\d+(?:\.\d+)?|\.\d+)$/u.test(e),
  N7 = /^var\(--(?:([\w-]+)|([\w-]+), ?([a-zA-Z\d ()%#.,-]+))\)/u;
function M7(e) {
  const t = N7.exec(e);
  if (!t) return [,];
  const [, n, r, i] = t;
  return [`--${n ?? r}`, i];
}
function FI(e, t, n = 1) {
  const [r, i] = M7(e);
  if (!r) return;
  const o = window.getComputedStyle(t).getPropertyValue(r);
  if (o) {
    const s = o.trim();
    return LI(s) ? parseFloat(s) : s;
  }
  return rw(i) ? FI(i, t, n + 1) : i;
}
const jI = (e) => (t) => t.test(e),
  I7 = { test: (e) => e === "auto", parse: (e) => e },
  VI = [Io, Z, xn, ur, bW, _W, I7],
  gT = (e) => VI.find(jI(e));
class qI extends bw {
  constructor(t, n, r, i, o) {
    super(t, n, r, i, o, !0);
  }
  readKeyframes() {
    const { unresolvedKeyframes: t, element: n, name: r } = this;
    if (!n || !n.current) return;
    super.readKeyframes();
    for (let u = 0; u < t.length; u++) {
      let l = t[u];
      if (typeof l == "string" && ((l = l.trim()), rw(l))) {
        const c = FI(l, n.current);
        c !== void 0 && (t[u] = c), u === t.length - 1 && (this.finalKeyframe = l);
      }
    }
    if ((this.resolveNoneKeyframes(), !gI.has(r) || t.length !== 2)) return;
    const [i, o] = t,
      s = gT(i),
      a = gT(o);
    if (s !== a)
      if (hT(s) && hT(a))
        for (let u = 0; u < t.length; u++) {
          const l = t[u];
          typeof l == "string" && (t[u] = parseFloat(l));
        }
      else this.needsMeasurement = !0;
  }
  resolveNoneKeyframes() {
    const { unresolvedKeyframes: t, name: n } = this,
      r = [];
    for (let i = 0; i < t.length; i++) l7(t[i]) && r.push(i);
    r.length && T7(t, r, n);
  }
  measureInitialState() {
    const { element: t, unresolvedKeyframes: n, name: r } = this;
    if (!t || !t.current) return;
    r === "height" && (this.suspendedScrollY = window.pageYOffset),
      (this.measuredOrigin = _o[r](t.measureViewportBox(), window.getComputedStyle(t.current))),
      (n[0] = this.measuredOrigin);
    const i = n[n.length - 1];
    i !== void 0 && t.getValue(r, i).jump(i, !1);
  }
  measureEndState() {
    var t;
    const { element: n, name: r, unresolvedKeyframes: i } = this;
    if (!n || !n.current) return;
    const o = n.getValue(r);
    o && o.jump(this.measuredOrigin, !1);
    const s = i.length - 1,
      a = i[s];
    (i[s] = _o[r](n.measureViewportBox(), window.getComputedStyle(n.current))),
      a !== null && this.finalKeyframe === void 0 && (this.finalKeyframe = a),
      !((t = this.removedTransforms) === null || t === void 0) &&
        t.length &&
        this.removedTransforms.forEach(([u, l]) => {
          n.getValue(u).set(l);
        }),
      this.resolveNoneKeyframes();
  }
}
const vT = (e, t) =>
  t === "zIndex"
    ? !1
    : !!(
        typeof e == "number" ||
        Array.isArray(e) ||
        (typeof e == "string" && (Mr.test(e) || e === "0") && !e.startsWith("url("))
      );
function D7(e) {
  const t = e[0];
  if (e.length === 1) return !0;
  for (let n = 0; n < e.length; n++) if (e[n] !== t) return !0;
}
function O7(e, t, n, r) {
  const i = e[0];
  if (i === null) return !1;
  if (t === "display" || t === "visibility") return !0;
  const o = e[e.length - 1],
    s = vT(i, t),
    a = vT(o, t);
  return !s || !a ? !1 : D7(e) || ((n === "spring" || fw(n)) && r);
}
const L7 = (e) => e !== null;
function Tc(e, { repeat: t, repeatType: n = "loop" }, r) {
  const i = e.filter(L7),
    o = t && n !== "loop" && t % 2 === 1 ? 0 : i.length - 1;
  return !o || r === void 0 ? i[o] : r;
}
const F7 = 40;
class $I {
  constructor({
    autoplay: t = !0,
    delay: n = 0,
    type: r = "keyframes",
    repeat: i = 0,
    repeatDelay: o = 0,
    repeatType: s = "loop",
    ...a
  }) {
    (this.isStopped = !1),
      (this.hasAttemptedResolve = !1),
      (this.createdAt = _n.now()),
      (this.options = {
        autoplay: t,
        delay: n,
        type: r,
        repeat: i,
        repeatDelay: o,
        repeatType: s,
        ...a,
      }),
      this.updateFinishedPromise();
  }
  calcStartTime() {
    return this.resolvedAt
      ? this.resolvedAt - this.createdAt > F7
        ? this.resolvedAt
        : this.createdAt
      : this.createdAt;
  }
  get resolved() {
    return !this._resolved && !this.hasAttemptedResolve && A7(), this._resolved;
  }
  onKeyframesResolved(t, n) {
    (this.resolvedAt = _n.now()), (this.hasAttemptedResolve = !0);
    const {
      name: r,
      type: i,
      velocity: o,
      delay: s,
      onComplete: a,
      onUpdate: u,
      isGenerator: l,
    } = this.options;
    if (!l && !O7(t, r, i, o))
      if (s) this.options.duration = 0;
      else {
        u && u(Tc(t, this.options, n)), a && a(), this.resolveFinishedPromise();
        return;
      }
    const c = this.initPlayback(t, n);
    c !== !1 &&
      ((this._resolved = { keyframes: t, finalKeyframe: n, ...c }), this.onPostResolved());
  }
  onPostResolved() {}
  then(t, n) {
    return this.currentFinishedPromise.then(t, n);
  }
  flatten() {
    (this.options.type = "keyframes"), (this.options.ease = "linear");
  }
  updateFinishedPromise() {
    this.currentFinishedPromise = new Promise((t) => {
      this.resolveFinishedPromise = t;
    });
  }
}
const _e = (e, t, n) => e + (t - e) * n;
function xg(e, t, n) {
  return (
    n < 0 && (n += 1),
    n > 1 && (n -= 1),
    n < 1 / 6 ? e + (t - e) * 6 * n : n < 1 / 2 ? t : n < 2 / 3 ? e + (t - e) * (2 / 3 - n) * 6 : e
  );
}
function j7({ hue: e, saturation: t, lightness: n, alpha: r }) {
  (e /= 360), (t /= 100), (n /= 100);
  let i = 0,
    o = 0,
    s = 0;
  if (!t) i = o = s = n;
  else {
    const a = n < 0.5 ? n * (1 + t) : n + t - n * t,
      u = 2 * n - a;
    (i = xg(u, a, e + 1 / 3)), (o = xg(u, a, e)), (s = xg(u, a, e - 1 / 3));
  }
  return {
    red: Math.round(i * 255),
    green: Math.round(o * 255),
    blue: Math.round(s * 255),
    alpha: r,
  };
}
function _l(e, t) {
  return (n) => (n > 0 ? t : e);
}
const _g = (e, t, n) => {
    const r = e * e,
      i = n * (t * t - r) + r;
    return i < 0 ? 0 : Math.sqrt(i);
  },
  V7 = [Yv, Qr, zi],
  q7 = (e) => V7.find((t) => t.test(e));
function yT(e) {
  const t = q7(e);
  if (!t) return !1;
  let n = t.parse(e);
  return t === zi && (n = j7(n)), n;
}
const wT = (e, t) => {
    const n = yT(e),
      r = yT(t);
    if (!n || !r) return _l(e, t);
    const i = { ...n };
    return (o) => (
      (i.red = _g(n.red, r.red, o)),
      (i.green = _g(n.green, r.green, o)),
      (i.blue = _g(n.blue, r.blue, o)),
      (i.alpha = _e(n.alpha, r.alpha, o)),
      Qr.transform(i)
    );
  },
  $7 = (e, t) => (n) => t(e(n)),
  Ca = (...e) => e.reduce($7),
  Jv = new Set(["none", "hidden"]);
function z7(e, t) {
  return Jv.has(e) ? (n) => (n <= 0 ? e : t) : (n) => (n >= 1 ? t : e);
}
function B7(e, t) {
  return (n) => _e(e, t, n);
}
function Sw(e) {
  return typeof e == "number"
    ? B7
    : typeof e == "string"
      ? rw(e)
        ? _l
        : tt.test(e)
          ? wT
          : G7
      : Array.isArray(e)
        ? zI
        : typeof e == "object"
          ? tt.test(e)
            ? wT
            : U7
          : _l;
}
function zI(e, t) {
  const n = [...e],
    r = n.length,
    i = e.map((o, s) => Sw(o)(o, t[s]));
  return (o) => {
    for (let s = 0; s < r; s++) n[s] = i[s](o);
    return n;
  };
}
function U7(e, t) {
  const n = { ...e, ...t },
    r = {};
  for (const i in n) e[i] !== void 0 && t[i] !== void 0 && (r[i] = Sw(e[i])(e[i], t[i]));
  return (i) => {
    for (const o in r) n[o] = r[o](i);
    return n;
  };
}
function H7(e, t) {
  var n;
  const r = [],
    i = { color: 0, var: 0, number: 0 };
  for (let o = 0; o < t.values.length; o++) {
    const s = t.types[o],
      a = e.indexes[s][i[s]],
      u = (n = e.values[a]) !== null && n !== void 0 ? n : 0;
    (r[o] = u), i[s]++;
  }
  return r;
}
const G7 = (e, t) => {
  const n = Mr.createTransformer(t),
    r = ra(e),
    i = ra(t);
  return r.indexes.var.length === i.indexes.var.length &&
    r.indexes.color.length === i.indexes.color.length &&
    r.indexes.number.length >= i.indexes.number.length
    ? (Jv.has(e) && !i.values.length) || (Jv.has(t) && !r.values.length)
      ? z7(e, t)
      : Ca(zI(H7(r, i), i.values), n)
    : _l(e, t);
};
function BI(e, t, n) {
  return typeof e == "number" && typeof t == "number" && typeof n == "number"
    ? _e(e, t, n)
    : Sw(e)(e, t);
}
const W7 = 5;
function UI(e, t, n) {
  const r = Math.max(t - W7, 0);
  return vI(n - e(r), t - r);
}
const Ce = {
    stiffness: 100,
    damping: 10,
    mass: 1,
    velocity: 0,
    duration: 800,
    bounce: 0.3,
    visualDuration: 0.3,
    restSpeed: { granular: 0.01, default: 2 },
    restDelta: { granular: 0.005, default: 0.5 },
    minDuration: 0.01,
    maxDuration: 10,
    minDamping: 0.05,
    maxDamping: 1,
  },
  bg = 0.001;
function K7({
  duration: e = Ce.duration,
  bounce: t = Ce.bounce,
  velocity: n = Ce.velocity,
  mass: r = Ce.mass,
}) {
  let i,
    o,
    s = 1 - t;
  (s = Zn(Ce.minDamping, Ce.maxDamping, s)),
    (e = Zn(Ce.minDuration, Ce.maxDuration, zn(e))),
    s < 1
      ? ((i = (l) => {
          const c = l * s,
            f = c * e,
            d = c - n,
            h = ey(l, s),
            v = Math.exp(-f);
          return bg - (d / h) * v;
        }),
        (o = (l) => {
          const f = l * s * e,
            d = f * n + n,
            h = Math.pow(s, 2) * Math.pow(l, 2) * e,
            v = Math.exp(-f),
            p = ey(Math.pow(l, 2), s);
          return ((-i(l) + bg > 0 ? -1 : 1) * ((d - h) * v)) / p;
        }))
      : ((i = (l) => {
          const c = Math.exp(-l * e),
            f = (l - n) * e + 1;
          return -bg + c * f;
        }),
        (o = (l) => {
          const c = Math.exp(-l * e),
            f = (n - l) * (e * e);
          return c * f;
        }));
  const a = 5 / e,
    u = X7(i, o, a);
  if (((e = $n(e)), isNaN(u))) return { stiffness: Ce.stiffness, damping: Ce.damping, duration: e };
  {
    const l = Math.pow(u, 2) * r;
    return { stiffness: l, damping: s * 2 * Math.sqrt(r * l), duration: e };
  }
}
const Y7 = 12;
function X7(e, t, n) {
  let r = n;
  for (let i = 1; i < Y7; i++) r = r - e(r) / t(r);
  return r;
}
function ey(e, t) {
  return e * Math.sqrt(1 - t * t);
}
const Z7 = ["duration", "bounce"],
  Q7 = ["stiffness", "damping", "mass"];
function xT(e, t) {
  return t.some((n) => e[n] !== void 0);
}
function J7(e) {
  let t = {
    velocity: Ce.velocity,
    stiffness: Ce.stiffness,
    damping: Ce.damping,
    mass: Ce.mass,
    isResolvedFromDuration: !1,
    ...e,
  };
  if (!xT(e, Q7) && xT(e, Z7))
    if (e.visualDuration) {
      const n = e.visualDuration,
        r = (2 * Math.PI) / (n * 1.2),
        i = r * r,
        o = 2 * Zn(0.05, 1, 1 - (e.bounce || 0)) * Math.sqrt(i);
      t = { ...t, mass: Ce.mass, stiffness: i, damping: o };
    } else {
      const n = K7(e);
      (t = { ...t, ...n, mass: Ce.mass }), (t.isResolvedFromDuration = !0);
    }
  return t;
}
function HI(e = Ce.visualDuration, t = Ce.bounce) {
  const n = typeof e != "object" ? { visualDuration: e, keyframes: [0, 1], bounce: t } : e;
  let { restSpeed: r, restDelta: i } = n;
  const o = n.keyframes[0],
    s = n.keyframes[n.keyframes.length - 1],
    a = { done: !1, value: o },
    {
      stiffness: u,
      damping: l,
      mass: c,
      duration: f,
      velocity: d,
      isResolvedFromDuration: h,
    } = J7({ ...n, velocity: -zn(n.velocity || 0) }),
    v = d || 0,
    p = l / (2 * Math.sqrt(u * c)),
    y = s - o,
    m = zn(Math.sqrt(u / c)),
    g = Math.abs(y) < 5;
  r || (r = g ? Ce.restSpeed.granular : Ce.restSpeed.default),
    i || (i = g ? Ce.restDelta.granular : Ce.restDelta.default);
  let w;
  if (p < 1) {
    const b = ey(m, p);
    w = (E) => {
      const C = Math.exp(-p * m * E);
      return s - C * (((v + p * m * y) / b) * Math.sin(b * E) + y * Math.cos(b * E));
    };
  } else if (p === 1) w = (b) => s - Math.exp(-m * b) * (y + (v + m * y) * b);
  else {
    const b = m * Math.sqrt(p * p - 1);
    w = (E) => {
      const C = Math.exp(-p * m * E),
        T = Math.min(b * E, 300);
      return s - (C * ((v + p * m * y) * Math.sinh(T) + b * y * Math.cosh(T))) / b;
    };
  }
  const x = {
    calculatedDuration: (h && f) || null,
    next: (b) => {
      const E = w(b);
      if (h) a.done = b >= f;
      else {
        let C = 0;
        p < 1 && (C = b === 0 ? $n(v) : UI(w, b, E));
        const T = Math.abs(C) <= r,
          P = Math.abs(s - E) <= i;
        a.done = T && P;
      }
      return (a.value = a.done ? s : E), a;
    },
    toString: () => {
      const b = Math.min(lI(x), Gv),
        E = cI((C) => x.next(b * C).value, b, 30);
      return b + "ms " + E;
    },
  };
  return x;
}
function _T({
  keyframes: e,
  velocity: t = 0,
  power: n = 0.8,
  timeConstant: r = 325,
  bounceDamping: i = 10,
  bounceStiffness: o = 500,
  modifyTarget: s,
  min: a,
  max: u,
  restDelta: l = 0.5,
  restSpeed: c,
}) {
  const f = e[0],
    d = { done: !1, value: f },
    h = (T) => (a !== void 0 && T < a) || (u !== void 0 && T > u),
    v = (T) => (a === void 0 ? u : u === void 0 || Math.abs(a - T) < Math.abs(u - T) ? a : u);
  let p = n * t;
  const y = f + p,
    m = s === void 0 ? y : s(y);
  m !== y && (p = m - f);
  const g = (T) => -p * Math.exp(-T / r),
    w = (T) => m + g(T),
    x = (T) => {
      const P = g(T),
        M = w(T);
      (d.done = Math.abs(P) <= l), (d.value = d.done ? m : M);
    };
  let b, E;
  const C = (T) => {
    h(d.value) &&
      ((b = T),
      (E = HI({
        keyframes: [d.value, v(d.value)],
        velocity: UI(w, T, d.value),
        damping: i,
        stiffness: o,
        restDelta: l,
        restSpeed: c,
      })));
  };
  return (
    C(0),
    {
      calculatedDuration: null,
      next: (T) => {
        let P = !1;
        return (
          !E && b === void 0 && ((P = !0), x(T), C(T)),
          b !== void 0 && T >= b ? E.next(T - b) : (!P && x(T), d)
        );
      },
    }
  );
}
const eK = Ea(0.42, 0, 1, 1),
  tK = Ea(0, 0, 0.58, 1),
  GI = Ea(0.42, 0, 0.58, 1),
  nK = (e) => Array.isArray(e) && typeof e[0] != "number",
  rK = {
    linear: Ct,
    easeIn: eK,
    easeInOut: GI,
    easeOut: tK,
    circIn: yw,
    circInOut: TI,
    circOut: CI,
    backIn: vw,
    backInOut: SI,
    backOut: bI,
    anticipate: EI,
  },
  bT = (e) => {
    if (dw(e)) {
      BM(e.length === 4);
      const [t, n, r, i] = e;
      return Ea(t, n, r, i);
    } else if (typeof e == "string") return rK[e];
    return e;
  };
function iK(e, t, n) {
  const r = [],
    i = n || BI,
    o = e.length - 1;
  for (let s = 0; s < o; s++) {
    let a = i(e[s], e[s + 1]);
    if (t) {
      const u = Array.isArray(t) ? t[s] || Ct : t;
      a = Ca(u, a);
    }
    r.push(a);
  }
  return r;
}
function WI(e, t, { clamp: n = !0, ease: r, mixer: i } = {}) {
  const o = e.length;
  if ((BM(o === t.length), o === 1)) return () => t[0];
  if (o === 2 && t[0] === t[1]) return () => t[1];
  const s = e[0] === e[1];
  e[0] > e[o - 1] && ((e = [...e].reverse()), (t = [...t].reverse()));
  const a = iK(t, r, i),
    u = a.length,
    l = (c) => {
      if (s && c < e[0]) return t[0];
      let f = 0;
      if (u > 1) for (; f < e.length - 2 && !(c < e[f + 1]); f++);
      const d = yo(e[f], e[f + 1], c);
      return a[f](d);
    };
  return n ? (c) => l(Zn(e[0], e[o - 1], c)) : l;
}
function oK(e, t) {
  const n = e[e.length - 1];
  for (let r = 1; r <= t; r++) {
    const i = yo(0, t, r);
    e.push(_e(n, 1, i));
  }
}
function sK(e) {
  const t = [0];
  return oK(t, e.length - 1), t;
}
function aK(e, t) {
  return e.map((n) => n * t);
}
function uK(e, t) {
  return e.map(() => t || GI).splice(0, e.length - 1);
}
function bl({ duration: e = 300, keyframes: t, times: n, ease: r = "easeInOut" }) {
  const i = nK(r) ? r.map(bT) : bT(r),
    o = { done: !1, value: t[0] },
    s = aK(n && n.length === t.length ? n : sK(t), e),
    a = WI(s, t, { ease: Array.isArray(i) ? i : uK(t, i) });
  return { calculatedDuration: e, next: (u) => ((o.value = a(u)), (o.done = u >= e), o) };
}
const lK = (e) => {
    const t = ({ timestamp: n }) => e(n);
    return {
      start: () => fe.update(t, !0),
      stop: () => Xn(t),
      now: () => ($e.isProcessing ? $e.timestamp : _n.now()),
    };
  },
  cK = { decay: _T, inertia: _T, tween: bl, keyframes: bl, spring: HI },
  fK = (e) => e / 100;
class kc extends $I {
  constructor(t) {
    super(t),
      (this.holdTime = null),
      (this.cancelTime = null),
      (this.currentTime = 0),
      (this.playbackSpeed = 1),
      (this.pendingPlayState = "running"),
      (this.startTime = null),
      (this.state = "idle"),
      (this.stop = () => {
        if ((this.resolver.cancel(), (this.isStopped = !0), this.state === "idle")) return;
        this.teardown();
        const { onStop: u } = this.options;
        u && u();
      });
    const { name: n, motionValue: r, element: i, keyframes: o } = this.options,
      s = (i == null ? void 0 : i.KeyframeResolver) || bw,
      a = (u, l) => this.onKeyframesResolved(u, l);
    (this.resolver = new s(o, a, n, r, i)), this.resolver.scheduleResolve();
  }
  flatten() {
    super.flatten(),
      this._resolved && Object.assign(this._resolved, this.initPlayback(this._resolved.keyframes));
  }
  initPlayback(t) {
    const {
        type: n = "keyframes",
        repeat: r = 0,
        repeatDelay: i = 0,
        repeatType: o,
        velocity: s = 0,
      } = this.options,
      a = fw(n) ? n : cK[n] || bl;
    let u, l;
    a !== bl && typeof t[0] != "number" && ((u = Ca(fK, BI(t[0], t[1]))), (t = [0, 100]));
    const c = a({ ...this.options, keyframes: t });
    o === "mirror" && (l = a({ ...this.options, keyframes: [...t].reverse(), velocity: -s })),
      c.calculatedDuration === null && (c.calculatedDuration = lI(c));
    const { calculatedDuration: f } = c,
      d = f + i,
      h = d * (r + 1) - i;
    return {
      generator: c,
      mirroredGenerator: l,
      mapPercentToKeyframes: u,
      calculatedDuration: f,
      resolvedDuration: d,
      totalDuration: h,
    };
  }
  onPostResolved() {
    const { autoplay: t = !0 } = this.options;
    this.play(),
      this.pendingPlayState === "paused" || !t
        ? this.pause()
        : (this.state = this.pendingPlayState);
  }
  tick(t, n = !1) {
    const { resolved: r } = this;
    if (!r) {
      const { keyframes: T } = this.options;
      return { done: !0, value: T[T.length - 1] };
    }
    const {
      finalKeyframe: i,
      generator: o,
      mirroredGenerator: s,
      mapPercentToKeyframes: a,
      keyframes: u,
      calculatedDuration: l,
      totalDuration: c,
      resolvedDuration: f,
    } = r;
    if (this.startTime === null) return o.next(0);
    const { delay: d, repeat: h, repeatType: v, repeatDelay: p, onUpdate: y } = this.options;
    this.speed > 0
      ? (this.startTime = Math.min(this.startTime, t))
      : this.speed < 0 && (this.startTime = Math.min(t - c / this.speed, this.startTime)),
      n
        ? (this.currentTime = t)
        : this.holdTime !== null
          ? (this.currentTime = this.holdTime)
          : (this.currentTime = Math.round(t - this.startTime) * this.speed);
    const m = this.currentTime - d * (this.speed >= 0 ? 1 : -1),
      g = this.speed >= 0 ? m < 0 : m > c;
    (this.currentTime = Math.max(m, 0)),
      this.state === "finished" && this.holdTime === null && (this.currentTime = c);
    let w = this.currentTime,
      x = o;
    if (h) {
      const T = Math.min(this.currentTime, c) / f;
      let P = Math.floor(T),
        M = T % 1;
      !M && T >= 1 && (M = 1),
        M === 1 && P--,
        (P = Math.min(P, h + 1)),
        !!(P % 2) &&
          (v === "reverse" ? ((M = 1 - M), p && (M -= p / f)) : v === "mirror" && (x = s)),
        (w = Zn(0, 1, M) * f);
    }
    const b = g ? { done: !1, value: u[0] } : x.next(w);
    a && (b.value = a(b.value));
    let { done: E } = b;
    !g && l !== null && (E = this.speed >= 0 ? this.currentTime >= c : this.currentTime <= 0);
    const C =
      this.holdTime === null && (this.state === "finished" || (this.state === "running" && E));
    return (
      C && i !== void 0 && (b.value = Tc(u, this.options, i)),
      y && y(b.value),
      C && this.finish(),
      b
    );
  }
  get duration() {
    const { resolved: t } = this;
    return t ? zn(t.calculatedDuration) : 0;
  }
  get time() {
    return zn(this.currentTime);
  }
  set time(t) {
    (t = $n(t)),
      (this.currentTime = t),
      this.holdTime !== null || this.speed === 0
        ? (this.holdTime = t)
        : this.driver && (this.startTime = this.driver.now() - t / this.speed);
  }
  get speed() {
    return this.playbackSpeed;
  }
  set speed(t) {
    const n = this.playbackSpeed !== t;
    (this.playbackSpeed = t), n && (this.time = zn(this.currentTime));
  }
  play() {
    if ((this.resolver.isScheduled || this.resolver.resume(), !this._resolved)) {
      this.pendingPlayState = "running";
      return;
    }
    if (this.isStopped) return;
    const { driver: t = lK, onPlay: n, startTime: r } = this.options;
    this.driver || (this.driver = t((o) => this.tick(o))), n && n();
    const i = this.driver.now();
    this.holdTime !== null
      ? (this.startTime = i - this.holdTime)
      : this.startTime
        ? this.state === "finished" && (this.startTime = i)
        : (this.startTime = r ?? this.calcStartTime()),
      this.state === "finished" && this.updateFinishedPromise(),
      (this.cancelTime = this.startTime),
      (this.holdTime = null),
      (this.state = "running"),
      this.driver.start();
  }
  pause() {
    var t;
    if (!this._resolved) {
      this.pendingPlayState = "paused";
      return;
    }
    (this.state = "paused"),
      (this.holdTime = (t = this.currentTime) !== null && t !== void 0 ? t : 0);
  }
  complete() {
    this.state !== "running" && this.play(),
      (this.pendingPlayState = this.state = "finished"),
      (this.holdTime = null);
  }
  finish() {
    this.teardown(), (this.state = "finished");
    const { onComplete: t } = this.options;
    t && t();
  }
  cancel() {
    this.cancelTime !== null && this.tick(this.cancelTime),
      this.teardown(),
      this.updateFinishedPromise();
  }
  teardown() {
    (this.state = "idle"),
      this.stopDriver(),
      this.resolveFinishedPromise(),
      this.updateFinishedPromise(),
      (this.startTime = this.cancelTime = null),
      this.resolver.cancel();
  }
  stopDriver() {
    this.driver && (this.driver.stop(), (this.driver = void 0));
  }
  sample(t) {
    return (this.startTime = 0), this.tick(t, !0);
  }
}
function dK(e) {
  return new kc(e);
}
const hK = new Set(["opacity", "clipPath", "filter", "transform"]);
function pK(
  e,
  t,
  n,
  {
    delay: r = 0,
    duration: i = 300,
    repeat: o = 0,
    repeatType: s = "loop",
    ease: a = "easeInOut",
    times: u,
  } = {},
) {
  const l = { [t]: n };
  u && (l.offset = u);
  const c = dI(a, i);
  return (
    Array.isArray(c) && (l.easing = c),
    e.animate(l, {
      delay: r,
      duration: i,
      easing: Array.isArray(c) ? "linear" : c,
      fill: "both",
      iterations: o + 1,
      direction: s === "reverse" ? "alternate" : "normal",
    })
  );
}
const mK = X0(() => Object.hasOwnProperty.call(Element.prototype, "animate")),
  Sl = 10,
  gK = 2e4;
function vK(e) {
  return fw(e.type) || e.type === "spring" || !fI(e.ease);
}
function yK(e, t) {
  const n = new kc({ ...t, keyframes: e, repeat: 0, delay: 0, isGenerator: !0 });
  let r = { done: !1, value: e[0] };
  const i = [];
  let o = 0;
  for (; !r.done && o < gK; ) (r = n.sample(o)), i.push(r.value), (o += Sl);
  return { times: void 0, keyframes: i, duration: o - Sl, ease: "linear" };
}
const KI = { anticipate: EI, backInOut: SI, circInOut: TI };
function wK(e) {
  return e in KI;
}
class ST extends $I {
  constructor(t) {
    super(t);
    const { name: n, motionValue: r, element: i, keyframes: o } = this.options;
    (this.resolver = new qI(o, (s, a) => this.onKeyframesResolved(s, a), n, r, i)),
      this.resolver.scheduleResolve();
  }
  initPlayback(t, n) {
    let {
      duration: r = 300,
      times: i,
      ease: o,
      type: s,
      motionValue: a,
      name: u,
      startTime: l,
    } = this.options;
    if (!a.owner || !a.owner.current) return !1;
    if ((typeof o == "string" && xl() && wK(o) && (o = KI[o]), vK(this.options))) {
      const { onComplete: f, onUpdate: d, motionValue: h, element: v, ...p } = this.options,
        y = yK(t, p);
      (t = y.keyframes),
        t.length === 1 && (t[1] = t[0]),
        (r = y.duration),
        (i = y.times),
        (o = y.ease),
        (s = "keyframes");
    }
    const c = pK(a.owner.current, u, t, { ...this.options, duration: r, times: i, ease: o });
    return (
      (c.startTime = l ?? this.calcStartTime()),
      this.pendingTimeline
        ? (aT(c, this.pendingTimeline), (this.pendingTimeline = void 0))
        : (c.onfinish = () => {
            const { onComplete: f } = this.options;
            a.set(Tc(t, this.options, n)), f && f(), this.cancel(), this.resolveFinishedPromise();
          }),
      { animation: c, duration: r, times: i, type: s, ease: o, keyframes: t }
    );
  }
  get duration() {
    const { resolved: t } = this;
    if (!t) return 0;
    const { duration: n } = t;
    return zn(n);
  }
  get time() {
    const { resolved: t } = this;
    if (!t) return 0;
    const { animation: n } = t;
    return zn(n.currentTime || 0);
  }
  set time(t) {
    const { resolved: n } = this;
    if (!n) return;
    const { animation: r } = n;
    r.currentTime = $n(t);
  }
  get speed() {
    const { resolved: t } = this;
    if (!t) return 1;
    const { animation: n } = t;
    return n.playbackRate;
  }
  set speed(t) {
    const { resolved: n } = this;
    if (!n) return;
    const { animation: r } = n;
    r.playbackRate = t;
  }
  get state() {
    const { resolved: t } = this;
    if (!t) return "idle";
    const { animation: n } = t;
    return n.playState;
  }
  get startTime() {
    const { resolved: t } = this;
    if (!t) return null;
    const { animation: n } = t;
    return n.startTime;
  }
  attachTimeline(t) {
    if (!this._resolved) this.pendingTimeline = t;
    else {
      const { resolved: n } = this;
      if (!n) return Ct;
      const { animation: r } = n;
      aT(r, t);
    }
    return Ct;
  }
  play() {
    if (this.isStopped) return;
    const { resolved: t } = this;
    if (!t) return;
    const { animation: n } = t;
    n.playState === "finished" && this.updateFinishedPromise(), n.play();
  }
  pause() {
    const { resolved: t } = this;
    if (!t) return;
    const { animation: n } = t;
    n.pause();
  }
  stop() {
    if ((this.resolver.cancel(), (this.isStopped = !0), this.state === "idle")) return;
    this.resolveFinishedPromise(), this.updateFinishedPromise();
    const { resolved: t } = this;
    if (!t) return;
    const { animation: n, keyframes: r, duration: i, type: o, ease: s, times: a } = t;
    if (n.playState === "idle" || n.playState === "finished") return;
    if (this.time) {
      const { motionValue: l, onUpdate: c, onComplete: f, element: d, ...h } = this.options,
        v = new kc({
          ...h,
          keyframes: r,
          duration: i,
          type: o,
          ease: s,
          times: a,
          isGenerator: !0,
        }),
        p = $n(this.time);
      l.setWithVelocity(v.sample(p - Sl).value, v.sample(p).value, Sl);
    }
    const { onStop: u } = this.options;
    u && u(), this.cancel();
  }
  complete() {
    const { resolved: t } = this;
    t && t.animation.finish();
  }
  cancel() {
    const { resolved: t } = this;
    t && t.animation.cancel();
  }
  static supports(t) {
    const { motionValue: n, name: r, repeatDelay: i, repeatType: o, damping: s, type: a } = t;
    if (!n || !n.owner || !(n.owner.current instanceof HTMLElement)) return !1;
    const { onUpdate: u, transformTemplate: l } = n.owner.getProps();
    return mK() && r && hK.has(r) && !u && !l && !i && o !== "mirror" && s !== 0 && a !== "inertia";
  }
}
const xK = { type: "spring", stiffness: 500, damping: 25, restSpeed: 10 },
  _K = (e) => ({
    type: "spring",
    stiffness: 550,
    damping: e === 0 ? 2 * Math.sqrt(550) : 30,
    restSpeed: 10,
  }),
  bK = { type: "keyframes", duration: 0.8 },
  SK = { type: "keyframes", ease: [0.25, 0.1, 0.35, 1], duration: 0.3 },
  EK = (e, { keyframes: t }) =>
    t.length > 2 ? bK : wi.has(e) ? (e.startsWith("scale") ? _K(t[1]) : xK) : SK;
function CK({
  when: e,
  delay: t,
  delayChildren: n,
  staggerChildren: r,
  staggerDirection: i,
  repeat: o,
  repeatType: s,
  repeatDelay: a,
  from: u,
  elapsed: l,
  ...c
}) {
  return !!Object.keys(c).length;
}
const Ew =
  (e, t, n, r = {}, i, o) =>
  (s) => {
    const a = cw(r, e) || {},
      u = a.delay || r.delay || 0;
    let { elapsed: l = 0 } = r;
    l = l - $n(u);
    let c = {
      keyframes: Array.isArray(n) ? n : [null, n],
      ease: "easeOut",
      velocity: t.getVelocity(),
      ...a,
      delay: -l,
      onUpdate: (d) => {
        t.set(d), a.onUpdate && a.onUpdate(d);
      },
      onComplete: () => {
        s(), a.onComplete && a.onComplete();
      },
      name: e,
      motionValue: t,
      element: o ? void 0 : i,
    };
    CK(a) || (c = { ...c, ...EK(e, c) }),
      c.duration && (c.duration = $n(c.duration)),
      c.repeatDelay && (c.repeatDelay = $n(c.repeatDelay)),
      c.from !== void 0 && (c.keyframes[0] = c.from);
    let f = !1;
    if (
      ((c.type === !1 || (c.duration === 0 && !c.repeatDelay)) &&
        ((c.duration = 0), c.delay === 0 && (f = !0)),
      f && !o && t.get() !== void 0)
    ) {
      const d = Tc(c.keyframes, a);
      if (d !== void 0)
        return (
          fe.update(() => {
            c.onUpdate(d), c.onComplete();
          }),
          new UW([])
        );
    }
    return !o && ST.supports(c) ? new ST(c) : new kc(c);
  };
function TK({ protectedKeys: e, needsAnimating: t }, n) {
  const r = e.hasOwnProperty(n) && t[n] !== !0;
  return (t[n] = !1), r;
}
function YI(e, t, { delay: n = 0, transitionOverride: r, type: i } = {}) {
  var o;
  let { transition: s = e.getDefaultTransition(), transitionEnd: a, ...u } = t;
  r && (s = r);
  const l = [],
    c = i && e.animationState && e.animationState.getState()[i];
  for (const f in u) {
    const d = e.getValue(f, (o = e.latestValues[f]) !== null && o !== void 0 ? o : null),
      h = u[f];
    if (h === void 0 || (c && TK(c, f))) continue;
    const v = { delay: n, ...cw(s || {}, f) };
    let p = !1;
    if (window.MotionHandoffAnimation) {
      const m = yI(e);
      if (m) {
        const g = window.MotionHandoffAnimation(m, f, fe);
        g !== null && ((v.startTime = g), (p = !0));
      }
    }
    Kv(e, f), d.start(Ew(f, d, h, e.shouldReduceMotion && gI.has(f) ? { type: !1 } : v, e, p));
    const y = d.animation;
    y && l.push(y);
  }
  return (
    a &&
      Promise.all(l).then(() => {
        fe.update(() => {
          a && i7(e, a);
        });
      }),
    l
  );
}
function ty(e, t, n = {}) {
  var r;
  const i = Cc(
    e,
    t,
    n.type === "exit"
      ? (r = e.presenceContext) === null || r === void 0
        ? void 0
        : r.custom
      : void 0,
  );
  let { transition: o = e.getDefaultTransition() || {} } = i || {};
  n.transitionOverride && (o = n.transitionOverride);
  const s = i ? () => Promise.all(YI(e, i, n)) : () => Promise.resolve(),
    a =
      e.variantChildren && e.variantChildren.size
        ? (l = 0) => {
            const { delayChildren: c = 0, staggerChildren: f, staggerDirection: d } = o;
            return kK(e, t, c + l, f, d, n);
          }
        : () => Promise.resolve(),
    { when: u } = o;
  if (u) {
    const [l, c] = u === "beforeChildren" ? [s, a] : [a, s];
    return l().then(() => c());
  } else return Promise.all([s(), a(n.delay)]);
}
function kK(e, t, n = 0, r = 0, i = 1, o) {
  const s = [],
    a = (e.variantChildren.size - 1) * r,
    u = i === 1 ? (l = 0) => l * r : (l = 0) => a - l * r;
  return (
    Array.from(e.variantChildren)
      .sort(RK)
      .forEach((l, c) => {
        l.notify("AnimationStart", t),
          s.push(ty(l, t, { ...o, delay: n + u(c) }).then(() => l.notify("AnimationComplete", t)));
      }),
    Promise.all(s)
  );
}
function RK(e, t) {
  return e.sortNodePosition(t);
}
function PK(e, t, n = {}) {
  e.notify("AnimationStart", t);
  let r;
  if (Array.isArray(t)) {
    const i = t.map((o) => ty(e, o, n));
    r = Promise.all(i);
  } else if (typeof t == "string") r = ty(e, t, n);
  else {
    const i = typeof t == "function" ? Cc(e, t, n.custom) : t;
    r = Promise.all(YI(e, i, n));
  }
  return r.then(() => {
    e.notify("AnimationComplete", t);
  });
}
const AK = Q0.length;
function XI(e) {
  if (!e) return;
  if (!e.isControllingVariants) {
    const n = e.parent ? XI(e.parent) || {} : {};
    return e.props.initial !== void 0 && (n.initial = e.props.initial), n;
  }
  const t = {};
  for (let n = 0; n < AK; n++) {
    const r = Q0[n],
      i = e.props[r];
    (ta(i) || i === !1) && (t[r] = i);
  }
  return t;
}
const NK = [...Z0].reverse(),
  MK = Z0.length;
function IK(e) {
  return (t) => Promise.all(t.map(({ animation: n, options: r }) => PK(e, n, r)));
}
function DK(e) {
  let t = IK(e),
    n = ET(),
    r = !0;
  const i = (u) => (l, c) => {
    var f;
    const d = Cc(
      e,
      c,
      u === "exit"
        ? (f = e.presenceContext) === null || f === void 0
          ? void 0
          : f.custom
        : void 0,
    );
    if (d) {
      const { transition: h, transitionEnd: v, ...p } = d;
      l = { ...l, ...p, ...v };
    }
    return l;
  };
  function o(u) {
    t = u(e);
  }
  function s(u) {
    const { props: l } = e,
      c = XI(e.parent) || {},
      f = [],
      d = new Set();
    let h = {},
      v = 1 / 0;
    for (let y = 0; y < MK; y++) {
      const m = NK[y],
        g = n[m],
        w = l[m] !== void 0 ? l[m] : c[m],
        x = ta(w),
        b = m === u ? g.isActive : null;
      b === !1 && (v = y);
      let E = w === c[m] && w !== l[m] && x;
      if (
        (E && r && e.manuallyAnimateOnMount && (E = !1),
        (g.protectedKeys = { ...h }),
        (!g.isActive && b === null) || (!w && !g.prevProp) || Sc(w) || typeof w == "boolean")
      )
        continue;
      const C = OK(g.prevProp, w);
      let T = C || (m === u && g.isActive && !E && x) || (y > v && x),
        P = !1;
      const M = Array.isArray(w) ? w : [w];
      let I = M.reduce(i(m), {});
      b === !1 && (I = {});
      const { prevResolvedValues: j = {} } = g,
        q = { ...j, ...I },
        S = (F) => {
          (T = !0), d.has(F) && ((P = !0), d.delete(F)), (g.needsAnimating[F] = !0);
          const N = e.getValue(F);
          N && (N.liveStyle = !1);
        };
      for (const F in q) {
        const N = I[F],
          k = j[F];
        if (h.hasOwnProperty(F)) continue;
        let D = !1;
        Hv(N) && Hv(k) ? (D = !uI(N, k)) : (D = N !== k),
          D
            ? N != null
              ? S(F)
              : d.add(F)
            : N !== void 0 && d.has(F)
              ? S(F)
              : (g.protectedKeys[F] = !0);
      }
      (g.prevProp = w),
        (g.prevResolvedValues = I),
        g.isActive && (h = { ...h, ...I }),
        r && e.blockInitialAnimation && (T = !1),
        T && (!(E && C) || P) && f.push(...M.map((F) => ({ animation: F, options: { type: m } })));
    }
    if (d.size) {
      const y = {};
      d.forEach((m) => {
        const g = e.getBaseTarget(m),
          w = e.getValue(m);
        w && (w.liveStyle = !0), (y[m] = g ?? null);
      }),
        f.push({ animation: y });
    }
    let p = !!f.length;
    return (
      r && (l.initial === !1 || l.initial === l.animate) && !e.manuallyAnimateOnMount && (p = !1),
      (r = !1),
      p ? t(f) : Promise.resolve()
    );
  }
  function a(u, l) {
    var c;
    if (n[u].isActive === l) return Promise.resolve();
    (c = e.variantChildren) === null ||
      c === void 0 ||
      c.forEach((d) => {
        var h;
        return (h = d.animationState) === null || h === void 0 ? void 0 : h.setActive(u, l);
      }),
      (n[u].isActive = l);
    const f = s(u);
    for (const d in n) n[d].protectedKeys = {};
    return f;
  }
  return {
    animateChanges: s,
    setActive: a,
    setAnimateFunction: o,
    getState: () => n,
    reset: () => {
      (n = ET()), (r = !0);
    },
  };
}
function OK(e, t) {
  return typeof t == "string" ? t !== e : Array.isArray(t) ? !uI(t, e) : !1;
}
function qr(e = !1) {
  return { isActive: e, protectedKeys: {}, needsAnimating: {}, prevResolvedValues: {} };
}
function ET() {
  return {
    animate: qr(!0),
    whileInView: qr(),
    whileHover: qr(),
    whileTap: qr(),
    whileDrag: qr(),
    whileFocus: qr(),
    exit: qr(),
  };
}
class Fr {
  constructor(t) {
    (this.isMounted = !1), (this.node = t);
  }
  update() {}
}
class LK extends Fr {
  constructor(t) {
    super(t), t.animationState || (t.animationState = DK(t));
  }
  updateAnimationControlsSubscription() {
    const { animate: t } = this.node.getProps();
    Sc(t) && (this.unmountControls = t.subscribe(this.node));
  }
  mount() {
    this.updateAnimationControlsSubscription();
  }
  update() {
    const { animate: t } = this.node.getProps(),
      { animate: n } = this.node.prevProps || {};
    t !== n && this.updateAnimationControlsSubscription();
  }
  unmount() {
    var t;
    this.node.animationState.reset(),
      (t = this.unmountControls) === null || t === void 0 || t.call(this);
  }
}
let FK = 0;
class jK extends Fr {
  constructor() {
    super(...arguments), (this.id = FK++);
  }
  update() {
    if (!this.node.presenceContext) return;
    const { isPresent: t, onExitComplete: n } = this.node.presenceContext,
      { isPresent: r } = this.node.prevPresenceContext || {};
    if (!this.node.animationState || t === r) return;
    const i = this.node.animationState.setActive("exit", !t);
    n && !t && i.then(() => n(this.id));
  }
  mount() {
    const { register: t } = this.node.presenceContext || {};
    t && (this.unmount = t(this.id));
  }
  unmount() {}
}
const VK = { animation: { Feature: LK }, exit: { Feature: jK } };
function ia(e, t, n, r = { passive: !0 }) {
  return e.addEventListener(t, n, r), () => e.removeEventListener(t, n);
}
function Ta(e) {
  return { point: { x: e.pageX, y: e.pageY } };
}
const qK = (e) => (t) => hw(t) && e(t, Ta(t));
function Ts(e, t, n, r) {
  return ia(e, t, qK(n), r);
}
const CT = (e, t) => Math.abs(e - t);
function $K(e, t) {
  const n = CT(e.x, t.x),
    r = CT(e.y, t.y);
  return Math.sqrt(n ** 2 + r ** 2);
}
class ZI {
  constructor(t, n, { transformPagePoint: r, contextWindow: i, dragSnapToOrigin: o = !1 } = {}) {
    if (
      ((this.startEvent = null),
      (this.lastMoveEvent = null),
      (this.lastMoveEventInfo = null),
      (this.handlers = {}),
      (this.contextWindow = window),
      (this.updatePoint = () => {
        if (!(this.lastMoveEvent && this.lastMoveEventInfo)) return;
        const f = Eg(this.lastMoveEventInfo, this.history),
          d = this.startEvent !== null,
          h = $K(f.offset, { x: 0, y: 0 }) >= 3;
        if (!d && !h) return;
        const { point: v } = f,
          { timestamp: p } = $e;
        this.history.push({ ...v, timestamp: p });
        const { onStart: y, onMove: m } = this.handlers;
        d || (y && y(this.lastMoveEvent, f), (this.startEvent = this.lastMoveEvent)),
          m && m(this.lastMoveEvent, f);
      }),
      (this.handlePointerMove = (f, d) => {
        (this.lastMoveEvent = f),
          (this.lastMoveEventInfo = Sg(d, this.transformPagePoint)),
          fe.update(this.updatePoint, !0);
      }),
      (this.handlePointerUp = (f, d) => {
        this.end();
        const { onEnd: h, onSessionEnd: v, resumeAnimation: p } = this.handlers;
        if ((this.dragSnapToOrigin && p && p(), !(this.lastMoveEvent && this.lastMoveEventInfo)))
          return;
        const y = Eg(
          f.type === "pointercancel" ? this.lastMoveEventInfo : Sg(d, this.transformPagePoint),
          this.history,
        );
        this.startEvent && h && h(f, y), v && v(f, y);
      }),
      !hw(t))
    )
      return;
    (this.dragSnapToOrigin = o),
      (this.handlers = n),
      (this.transformPagePoint = r),
      (this.contextWindow = i || window);
    const s = Ta(t),
      a = Sg(s, this.transformPagePoint),
      { point: u } = a,
      { timestamp: l } = $e;
    this.history = [{ ...u, timestamp: l }];
    const { onSessionStart: c } = n;
    c && c(t, Eg(a, this.history)),
      (this.removeListeners = Ca(
        Ts(this.contextWindow, "pointermove", this.handlePointerMove),
        Ts(this.contextWindow, "pointerup", this.handlePointerUp),
        Ts(this.contextWindow, "pointercancel", this.handlePointerUp),
      ));
  }
  updateHandlers(t) {
    this.handlers = t;
  }
  end() {
    this.removeListeners && this.removeListeners(), Xn(this.updatePoint);
  }
}
function Sg(e, t) {
  return t ? { point: t(e.point) } : e;
}
function TT(e, t) {
  return { x: e.x - t.x, y: e.y - t.y };
}
function Eg({ point: e }, t) {
  return { point: e, delta: TT(e, QI(t)), offset: TT(e, zK(t)), velocity: BK(t, 0.1) };
}
function zK(e) {
  return e[0];
}
function QI(e) {
  return e[e.length - 1];
}
function BK(e, t) {
  if (e.length < 2) return { x: 0, y: 0 };
  let n = e.length - 1,
    r = null;
  const i = QI(e);
  for (; n >= 0 && ((r = e[n]), !(i.timestamp - r.timestamp > $n(t))); ) n--;
  if (!r) return { x: 0, y: 0 };
  const o = zn(i.timestamp - r.timestamp);
  if (o === 0) return { x: 0, y: 0 };
  const s = { x: (i.x - r.x) / o, y: (i.y - r.y) / o };
  return s.x === 1 / 0 && (s.x = 0), s.y === 1 / 0 && (s.y = 0), s;
}
const JI = 1e-4,
  UK = 1 - JI,
  HK = 1 + JI,
  eD = 0.01,
  GK = 0 - eD,
  WK = 0 + eD;
function Rt(e) {
  return e.max - e.min;
}
function KK(e, t, n) {
  return Math.abs(e - t) <= n;
}
function kT(e, t, n, r = 0.5) {
  (e.origin = r),
    (e.originPoint = _e(t.min, t.max, e.origin)),
    (e.scale = Rt(n) / Rt(t)),
    (e.translate = _e(n.min, n.max, e.origin) - e.originPoint),
    ((e.scale >= UK && e.scale <= HK) || isNaN(e.scale)) && (e.scale = 1),
    ((e.translate >= GK && e.translate <= WK) || isNaN(e.translate)) && (e.translate = 0);
}
function ks(e, t, n, r) {
  kT(e.x, t.x, n.x, r ? r.originX : void 0), kT(e.y, t.y, n.y, r ? r.originY : void 0);
}
function RT(e, t, n) {
  (e.min = n.min + t.min), (e.max = e.min + Rt(t));
}
function YK(e, t, n) {
  RT(e.x, t.x, n.x), RT(e.y, t.y, n.y);
}
function PT(e, t, n) {
  (e.min = t.min - n.min), (e.max = e.min + Rt(t));
}
function Rs(e, t, n) {
  PT(e.x, t.x, n.x), PT(e.y, t.y, n.y);
}
function XK(e, { min: t, max: n }, r) {
  return (
    t !== void 0 && e < t
      ? (e = r ? _e(t, e, r.min) : Math.max(e, t))
      : n !== void 0 && e > n && (e = r ? _e(n, e, r.max) : Math.min(e, n)),
    e
  );
}
function AT(e, t, n) {
  return {
    min: t !== void 0 ? e.min + t : void 0,
    max: n !== void 0 ? e.max + n - (e.max - e.min) : void 0,
  };
}
function ZK(e, { top: t, left: n, bottom: r, right: i }) {
  return { x: AT(e.x, n, i), y: AT(e.y, t, r) };
}
function NT(e, t) {
  let n = t.min - e.min,
    r = t.max - e.max;
  return t.max - t.min < e.max - e.min && ([n, r] = [r, n]), { min: n, max: r };
}
function QK(e, t) {
  return { x: NT(e.x, t.x), y: NT(e.y, t.y) };
}
function JK(e, t) {
  let n = 0.5;
  const r = Rt(e),
    i = Rt(t);
  return (
    i > r ? (n = yo(t.min, t.max - r, e.min)) : r > i && (n = yo(e.min, e.max - i, t.min)),
    Zn(0, 1, n)
  );
}
function eY(e, t) {
  const n = {};
  return (
    t.min !== void 0 && (n.min = t.min - e.min), t.max !== void 0 && (n.max = t.max - e.min), n
  );
}
const ny = 0.35;
function tY(e = ny) {
  return (
    e === !1 ? (e = 0) : e === !0 && (e = ny),
    { x: MT(e, "left", "right"), y: MT(e, "top", "bottom") }
  );
}
function MT(e, t, n) {
  return { min: IT(e, t), max: IT(e, n) };
}
function IT(e, t) {
  return typeof e == "number" ? e : e[t] || 0;
}
const DT = () => ({ translate: 0, scale: 1, origin: 0, originPoint: 0 }),
  Bi = () => ({ x: DT(), y: DT() }),
  OT = () => ({ min: 0, max: 0 }),
  Ae = () => ({ x: OT(), y: OT() });
function Mt(e) {
  return [e("x"), e("y")];
}
function tD({ top: e, left: t, right: n, bottom: r }) {
  return { x: { min: t, max: n }, y: { min: e, max: r } };
}
function nY({ x: e, y: t }) {
  return { top: t.min, right: e.max, bottom: t.max, left: e.min };
}
function rY(e, t) {
  if (!t) return e;
  const n = t({ x: e.left, y: e.top }),
    r = t({ x: e.right, y: e.bottom });
  return { top: n.y, left: n.x, bottom: r.y, right: r.x };
}
function Cg(e) {
  return e === void 0 || e === 1;
}
function ry({ scale: e, scaleX: t, scaleY: n }) {
  return !Cg(e) || !Cg(t) || !Cg(n);
}
function Ur(e) {
  return ry(e) || nD(e) || e.z || e.rotate || e.rotateX || e.rotateY || e.skewX || e.skewY;
}
function nD(e) {
  return LT(e.x) || LT(e.y);
}
function LT(e) {
  return e && e !== "0%";
}
function El(e, t, n) {
  const r = e - n,
    i = t * r;
  return n + i;
}
function FT(e, t, n, r, i) {
  return i !== void 0 && (e = El(e, i, r)), El(e, n, r) + t;
}
function iy(e, t = 0, n = 1, r, i) {
  (e.min = FT(e.min, t, n, r, i)), (e.max = FT(e.max, t, n, r, i));
}
function rD(e, { x: t, y: n }) {
  iy(e.x, t.translate, t.scale, t.originPoint), iy(e.y, n.translate, n.scale, n.originPoint);
}
const jT = 0.999999999999,
  VT = 1.0000000000001;
function iY(e, t, n, r = !1) {
  const i = n.length;
  if (!i) return;
  t.x = t.y = 1;
  let o, s;
  for (let a = 0; a < i; a++) {
    (o = n[a]), (s = o.projectionDelta);
    const { visualElement: u } = o.options;
    (u && u.props.style && u.props.style.display === "contents") ||
      (r &&
        o.options.layoutScroll &&
        o.scroll &&
        o !== o.root &&
        Hi(e, { x: -o.scroll.offset.x, y: -o.scroll.offset.y }),
      s && ((t.x *= s.x.scale), (t.y *= s.y.scale), rD(e, s)),
      r && Ur(o.latestValues) && Hi(e, o.latestValues));
  }
  t.x < VT && t.x > jT && (t.x = 1), t.y < VT && t.y > jT && (t.y = 1);
}
function Ui(e, t) {
  (e.min = e.min + t), (e.max = e.max + t);
}
function qT(e, t, n, r, i = 0.5) {
  const o = _e(e.min, e.max, i);
  iy(e, t, n, o, r);
}
function Hi(e, t) {
  qT(e.x, t.x, t.scaleX, t.scale, t.originX), qT(e.y, t.y, t.scaleY, t.scale, t.originY);
}
function iD(e, t) {
  return tD(rY(e.getBoundingClientRect(), t));
}
function oY(e, t, n) {
  const r = iD(e, n),
    { scroll: i } = t;
  return i && (Ui(r.x, i.offset.x), Ui(r.y, i.offset.y)), r;
}
const oD = ({ current: e }) => (e ? e.ownerDocument.defaultView : null),
  sY = new WeakMap();
class aY {
  constructor(t) {
    (this.openDragLock = null),
      (this.isDragging = !1),
      (this.currentDirection = null),
      (this.originPoint = { x: 0, y: 0 }),
      (this.constraints = !1),
      (this.hasMutatedConstraints = !1),
      (this.elastic = Ae()),
      (this.visualElement = t);
  }
  start(t, { snapToCursor: n = !1 } = {}) {
    const { presenceContext: r } = this.visualElement;
    if (r && r.isPresent === !1) return;
    const i = (c) => {
        const { dragSnapToOrigin: f } = this.getProps();
        f ? this.pauseAnimation() : this.stopAnimation(), n && this.snapToCursor(Ta(c).point);
      },
      o = (c, f) => {
        const { drag: d, dragPropagation: h, onDragStart: v } = this.getProps();
        if (
          d &&
          !h &&
          (this.openDragLock && this.openDragLock(),
          (this.openDragLock = JW(d)),
          !this.openDragLock)
        )
          return;
        (this.isDragging = !0),
          (this.currentDirection = null),
          this.resolveConstraints(),
          this.visualElement.projection &&
            ((this.visualElement.projection.isAnimationBlocked = !0),
            (this.visualElement.projection.target = void 0)),
          Mt((y) => {
            let m = this.getAxisMotionValue(y).get() || 0;
            if (xn.test(m)) {
              const { projection: g } = this.visualElement;
              if (g && g.layout) {
                const w = g.layout.layoutBox[y];
                w && (m = Rt(w) * (parseFloat(m) / 100));
              }
            }
            this.originPoint[y] = m;
          }),
          v && fe.postRender(() => v(c, f)),
          Kv(this.visualElement, "transform");
        const { animationState: p } = this.visualElement;
        p && p.setActive("whileDrag", !0);
      },
      s = (c, f) => {
        const {
          dragPropagation: d,
          dragDirectionLock: h,
          onDirectionLock: v,
          onDrag: p,
        } = this.getProps();
        if (!d && !this.openDragLock) return;
        const { offset: y } = f;
        if (h && this.currentDirection === null) {
          (this.currentDirection = uY(y)),
            this.currentDirection !== null && v && v(this.currentDirection);
          return;
        }
        this.updateAxis("x", f.point, y),
          this.updateAxis("y", f.point, y),
          this.visualElement.render(),
          p && p(c, f);
      },
      a = (c, f) => this.stop(c, f),
      u = () =>
        Mt((c) => {
          var f;
          return (
            this.getAnimationState(c) === "paused" &&
            ((f = this.getAxisMotionValue(c).animation) === null || f === void 0
              ? void 0
              : f.play())
          );
        }),
      { dragSnapToOrigin: l } = this.getProps();
    this.panSession = new ZI(
      t,
      { onSessionStart: i, onStart: o, onMove: s, onSessionEnd: a, resumeAnimation: u },
      {
        transformPagePoint: this.visualElement.getTransformPagePoint(),
        dragSnapToOrigin: l,
        contextWindow: oD(this.visualElement),
      },
    );
  }
  stop(t, n) {
    const r = this.isDragging;
    if ((this.cancel(), !r)) return;
    const { velocity: i } = n;
    this.startAnimation(i);
    const { onDragEnd: o } = this.getProps();
    o && fe.postRender(() => o(t, n));
  }
  cancel() {
    this.isDragging = !1;
    const { projection: t, animationState: n } = this.visualElement;
    t && (t.isAnimationBlocked = !1),
      this.panSession && this.panSession.end(),
      (this.panSession = void 0);
    const { dragPropagation: r } = this.getProps();
    !r && this.openDragLock && (this.openDragLock(), (this.openDragLock = null)),
      n && n.setActive("whileDrag", !1);
  }
  updateAxis(t, n, r) {
    const { drag: i } = this.getProps();
    if (!r || !lu(t, i, this.currentDirection)) return;
    const o = this.getAxisMotionValue(t);
    let s = this.originPoint[t] + r[t];
    this.constraints && this.constraints[t] && (s = XK(s, this.constraints[t], this.elastic[t])),
      o.set(s);
  }
  resolveConstraints() {
    var t;
    const { dragConstraints: n, dragElastic: r } = this.getProps(),
      i =
        this.visualElement.projection && !this.visualElement.projection.layout
          ? this.visualElement.projection.measure(!1)
          : (t = this.visualElement.projection) === null || t === void 0
            ? void 0
            : t.layout,
      o = this.constraints;
    n && $i(n)
      ? this.constraints || (this.constraints = this.resolveRefConstraints())
      : n && i
        ? (this.constraints = ZK(i.layoutBox, n))
        : (this.constraints = !1),
      (this.elastic = tY(r)),
      o !== this.constraints &&
        i &&
        this.constraints &&
        !this.hasMutatedConstraints &&
        Mt((s) => {
          this.constraints !== !1 &&
            this.getAxisMotionValue(s) &&
            (this.constraints[s] = eY(i.layoutBox[s], this.constraints[s]));
        });
  }
  resolveRefConstraints() {
    const { dragConstraints: t, onMeasureDragConstraints: n } = this.getProps();
    if (!t || !$i(t)) return !1;
    const r = t.current,
      { projection: i } = this.visualElement;
    if (!i || !i.layout) return !1;
    const o = oY(r, i.root, this.visualElement.getTransformPagePoint());
    let s = QK(i.layout.layoutBox, o);
    if (n) {
      const a = n(nY(s));
      (this.hasMutatedConstraints = !!a), a && (s = tD(a));
    }
    return s;
  }
  startAnimation(t) {
    const {
        drag: n,
        dragMomentum: r,
        dragElastic: i,
        dragTransition: o,
        dragSnapToOrigin: s,
        onDragTransitionEnd: a,
      } = this.getProps(),
      u = this.constraints || {},
      l = Mt((c) => {
        if (!lu(c, n, this.currentDirection)) return;
        let f = (u && u[c]) || {};
        s && (f = { min: 0, max: 0 });
        const d = i ? 200 : 1e6,
          h = i ? 40 : 1e7,
          v = {
            type: "inertia",
            velocity: r ? t[c] : 0,
            bounceStiffness: d,
            bounceDamping: h,
            timeConstant: 750,
            restDelta: 1,
            restSpeed: 10,
            ...o,
            ...f,
          };
        return this.startAxisValueAnimation(c, v);
      });
    return Promise.all(l).then(a);
  }
  startAxisValueAnimation(t, n) {
    const r = this.getAxisMotionValue(t);
    return Kv(this.visualElement, t), r.start(Ew(t, r, 0, n, this.visualElement, !1));
  }
  stopAnimation() {
    Mt((t) => this.getAxisMotionValue(t).stop());
  }
  pauseAnimation() {
    Mt((t) => {
      var n;
      return (n = this.getAxisMotionValue(t).animation) === null || n === void 0
        ? void 0
        : n.pause();
    });
  }
  getAnimationState(t) {
    var n;
    return (n = this.getAxisMotionValue(t).animation) === null || n === void 0 ? void 0 : n.state;
  }
  getAxisMotionValue(t) {
    const n = `_drag${t.toUpperCase()}`,
      r = this.visualElement.getProps(),
      i = r[n];
    return i || this.visualElement.getValue(t, (r.initial ? r.initial[t] : void 0) || 0);
  }
  snapToCursor(t) {
    Mt((n) => {
      const { drag: r } = this.getProps();
      if (!lu(n, r, this.currentDirection)) return;
      const { projection: i } = this.visualElement,
        o = this.getAxisMotionValue(n);
      if (i && i.layout) {
        const { min: s, max: a } = i.layout.layoutBox[n];
        o.set(t[n] - _e(s, a, 0.5));
      }
    });
  }
  scalePositionWithinConstraints() {
    if (!this.visualElement.current) return;
    const { drag: t, dragConstraints: n } = this.getProps(),
      { projection: r } = this.visualElement;
    if (!$i(n) || !r || !this.constraints) return;
    this.stopAnimation();
    const i = { x: 0, y: 0 };
    Mt((s) => {
      const a = this.getAxisMotionValue(s);
      if (a && this.constraints !== !1) {
        const u = a.get();
        i[s] = JK({ min: u, max: u }, this.constraints[s]);
      }
    });
    const { transformTemplate: o } = this.visualElement.getProps();
    (this.visualElement.current.style.transform = o ? o({}, "") : "none"),
      r.root && r.root.updateScroll(),
      r.updateLayout(),
      this.resolveConstraints(),
      Mt((s) => {
        if (!lu(s, t, null)) return;
        const a = this.getAxisMotionValue(s),
          { min: u, max: l } = this.constraints[s];
        a.set(_e(u, l, i[s]));
      });
  }
  addListeners() {
    if (!this.visualElement.current) return;
    sY.set(this.visualElement, this);
    const t = this.visualElement.current,
      n = Ts(t, "pointerdown", (u) => {
        const { drag: l, dragListener: c = !0 } = this.getProps();
        l && c && this.start(u);
      }),
      r = () => {
        const { dragConstraints: u } = this.getProps();
        $i(u) && u.current && (this.constraints = this.resolveRefConstraints());
      },
      { projection: i } = this.visualElement,
      o = i.addEventListener("measure", r);
    i && !i.layout && (i.root && i.root.updateScroll(), i.updateLayout()), fe.read(r);
    const s = ia(window, "resize", () => this.scalePositionWithinConstraints()),
      a = i.addEventListener("didUpdate", ({ delta: u, hasLayoutChanged: l }) => {
        this.isDragging &&
          l &&
          (Mt((c) => {
            const f = this.getAxisMotionValue(c);
            f && ((this.originPoint[c] += u[c].translate), f.set(f.get() + u[c].translate));
          }),
          this.visualElement.render());
      });
    return () => {
      s(), n(), o(), a && a();
    };
  }
  getProps() {
    const t = this.visualElement.getProps(),
      {
        drag: n = !1,
        dragDirectionLock: r = !1,
        dragPropagation: i = !1,
        dragConstraints: o = !1,
        dragElastic: s = ny,
        dragMomentum: a = !0,
      } = t;
    return {
      ...t,
      drag: n,
      dragDirectionLock: r,
      dragPropagation: i,
      dragConstraints: o,
      dragElastic: s,
      dragMomentum: a,
    };
  }
}
function lu(e, t, n) {
  return (t === !0 || t === e) && (n === null || n === e);
}
function uY(e, t = 10) {
  let n = null;
  return Math.abs(e.y) > t ? (n = "y") : Math.abs(e.x) > t && (n = "x"), n;
}
class lY extends Fr {
  constructor(t) {
    super(t),
      (this.removeGroupControls = Ct),
      (this.removeListeners = Ct),
      (this.controls = new aY(t));
  }
  mount() {
    const { dragControls: t } = this.node.getProps();
    t && (this.removeGroupControls = t.subscribe(this.controls)),
      (this.removeListeners = this.controls.addListeners() || Ct);
  }
  unmount() {
    this.removeGroupControls(), this.removeListeners();
  }
}
const $T = (e) => (t, n) => {
  e && fe.postRender(() => e(t, n));
};
class cY extends Fr {
  constructor() {
    super(...arguments), (this.removePointerDownListener = Ct);
  }
  onPointerDown(t) {
    this.session = new ZI(t, this.createPanHandlers(), {
      transformPagePoint: this.node.getTransformPagePoint(),
      contextWindow: oD(this.node),
    });
  }
  createPanHandlers() {
    const { onPanSessionStart: t, onPanStart: n, onPan: r, onPanEnd: i } = this.node.getProps();
    return {
      onSessionStart: $T(t),
      onStart: $T(n),
      onMove: r,
      onEnd: (o, s) => {
        delete this.session, i && fe.postRender(() => i(o, s));
      },
    };
  }
  mount() {
    this.removePointerDownListener = Ts(this.node.current, "pointerdown", (t) =>
      this.onPointerDown(t),
    );
  }
  update() {
    this.session && this.session.updateHandlers(this.createPanHandlers());
  }
  unmount() {
    this.removePointerDownListener(), this.session && this.session.end();
  }
}
const Mu = { hasAnimatedSinceResize: !0, hasEverUpdated: !1 };
function zT(e, t) {
  return t.max === t.min ? 0 : (e / (t.max - t.min)) * 100;
}
const Zo = {
    correct: (e, t) => {
      if (!t.target) return e;
      if (typeof e == "string")
        if (Z.test(e)) e = parseFloat(e);
        else return e;
      const n = zT(e, t.target.x),
        r = zT(e, t.target.y);
      return `${n}% ${r}%`;
    },
  },
  fY = {
    correct: (e, { treeScale: t, projectionDelta: n }) => {
      const r = e,
        i = Mr.parse(e);
      if (i.length > 5) return r;
      const o = Mr.createTransformer(e),
        s = typeof i[0] != "number" ? 1 : 0,
        a = n.x.scale * t.x,
        u = n.y.scale * t.y;
      (i[0 + s] /= a), (i[1 + s] /= u);
      const l = _e(a, u, 0.5);
      return (
        typeof i[2 + s] == "number" && (i[2 + s] /= l),
        typeof i[3 + s] == "number" && (i[3 + s] /= l),
        o(i)
      );
    },
  };
class dY extends _.Component {
  componentDidMount() {
    const { visualElement: t, layoutGroup: n, switchLayoutGroup: r, layoutId: i } = this.props,
      { projection: o } = t;
    MW(hY),
      o &&
        (n.group && n.group.add(o),
        r && r.register && i && r.register(o),
        o.root.didUpdate(),
        o.addEventListener("animationComplete", () => {
          this.safeToRemove();
        }),
        o.setOptions({ ...o.options, onExitComplete: () => this.safeToRemove() })),
      (Mu.hasEverUpdated = !0);
  }
  getSnapshotBeforeUpdate(t) {
    const { layoutDependency: n, visualElement: r, drag: i, isPresent: o } = this.props,
      s = r.projection;
    return (
      s &&
        ((s.isPresent = o),
        i || t.layoutDependency !== n || n === void 0 ? s.willUpdate() : this.safeToRemove(),
        t.isPresent !== o &&
          (o
            ? s.promote()
            : s.relegate() ||
              fe.postRender(() => {
                const a = s.getStack();
                (!a || !a.members.length) && this.safeToRemove();
              }))),
      null
    );
  }
  componentDidUpdate() {
    const { projection: t } = this.props.visualElement;
    t &&
      (t.root.didUpdate(),
      ew.postRender(() => {
        !t.currentAnimation && t.isLead() && this.safeToRemove();
      }));
  }
  componentWillUnmount() {
    const { visualElement: t, layoutGroup: n, switchLayoutGroup: r } = this.props,
      { projection: i } = t;
    i &&
      (i.scheduleCheckAfterUnmount(),
      n && n.group && n.group.remove(i),
      r && r.deregister && r.deregister(i));
  }
  safeToRemove() {
    const { safeToRemove: t } = this.props;
    t && t();
  }
  render() {
    return null;
  }
}
function sD(e) {
  const [t, n] = KG(),
    r = _.useContext(zM);
  return R.jsx(dY, {
    ...e,
    layoutGroup: r,
    switchLayoutGroup: _.useContext(YM),
    isPresent: t,
    safeToRemove: n,
  });
}
const hY = {
  borderRadius: {
    ...Zo,
    applyTo: [
      "borderTopLeftRadius",
      "borderTopRightRadius",
      "borderBottomLeftRadius",
      "borderBottomRightRadius",
    ],
  },
  borderTopLeftRadius: Zo,
  borderTopRightRadius: Zo,
  borderBottomLeftRadius: Zo,
  borderBottomRightRadius: Zo,
  boxShadow: fY,
};
function pY(e, t, n) {
  const r = Be(e) ? e : xo(e);
  return r.start(Ew("", r, t, n)), r.animation;
}
function mY(e) {
  return e instanceof SVGElement && e.tagName !== "svg";
}
const gY = (e, t) => e.depth - t.depth;
class vY {
  constructor() {
    (this.children = []), (this.isDirty = !1);
  }
  add(t) {
    pw(this.children, t), (this.isDirty = !0);
  }
  remove(t) {
    mw(this.children, t), (this.isDirty = !0);
  }
  forEach(t) {
    this.isDirty && this.children.sort(gY), (this.isDirty = !1), this.children.forEach(t);
  }
}
function yY(e, t) {
  const n = _n.now(),
    r = ({ timestamp: i }) => {
      const o = i - n;
      o >= t && (Xn(r), e(o - t));
    };
  return fe.read(r, !0), () => Xn(r);
}
const aD = ["TopLeft", "TopRight", "BottomLeft", "BottomRight"],
  wY = aD.length,
  BT = (e) => (typeof e == "string" ? parseFloat(e) : e),
  UT = (e) => typeof e == "number" || Z.test(e);
function xY(e, t, n, r, i, o) {
  i
    ? ((e.opacity = _e(0, n.opacity !== void 0 ? n.opacity : 1, _Y(r))),
      (e.opacityExit = _e(t.opacity !== void 0 ? t.opacity : 1, 0, bY(r))))
    : o &&
      (e.opacity = _e(
        t.opacity !== void 0 ? t.opacity : 1,
        n.opacity !== void 0 ? n.opacity : 1,
        r,
      ));
  for (let s = 0; s < wY; s++) {
    const a = `border${aD[s]}Radius`;
    let u = HT(t, a),
      l = HT(n, a);
    if (u === void 0 && l === void 0) continue;
    u || (u = 0),
      l || (l = 0),
      u === 0 || l === 0 || UT(u) === UT(l)
        ? ((e[a] = Math.max(_e(BT(u), BT(l), r), 0)), (xn.test(l) || xn.test(u)) && (e[a] += "%"))
        : (e[a] = l);
  }
  (t.rotate || n.rotate) && (e.rotate = _e(t.rotate || 0, n.rotate || 0, r));
}
function HT(e, t) {
  return e[t] !== void 0 ? e[t] : e.borderRadius;
}
const _Y = uD(0, 0.5, CI),
  bY = uD(0.5, 0.95, Ct);
function uD(e, t, n) {
  return (r) => (r < e ? 0 : r > t ? 1 : n(yo(e, t, r)));
}
function GT(e, t) {
  (e.min = t.min), (e.max = t.max);
}
function Nt(e, t) {
  GT(e.x, t.x), GT(e.y, t.y);
}
function WT(e, t) {
  (e.translate = t.translate),
    (e.scale = t.scale),
    (e.originPoint = t.originPoint),
    (e.origin = t.origin);
}
function KT(e, t, n, r, i) {
  return (e -= t), (e = El(e, 1 / n, r)), i !== void 0 && (e = El(e, 1 / i, r)), e;
}
function SY(e, t = 0, n = 1, r = 0.5, i, o = e, s = e) {
  if (
    (xn.test(t) && ((t = parseFloat(t)), (t = _e(s.min, s.max, t / 100) - s.min)),
    typeof t != "number")
  )
    return;
  let a = _e(o.min, o.max, r);
  e === o && (a -= t), (e.min = KT(e.min, t, n, a, i)), (e.max = KT(e.max, t, n, a, i));
}
function YT(e, t, [n, r, i], o, s) {
  SY(e, t[n], t[r], t[i], t.scale, o, s);
}
const EY = ["x", "scaleX", "originX"],
  CY = ["y", "scaleY", "originY"];
function XT(e, t, n, r) {
  YT(e.x, t, EY, n ? n.x : void 0, r ? r.x : void 0),
    YT(e.y, t, CY, n ? n.y : void 0, r ? r.y : void 0);
}
function ZT(e) {
  return e.translate === 0 && e.scale === 1;
}
function lD(e) {
  return ZT(e.x) && ZT(e.y);
}
function QT(e, t) {
  return e.min === t.min && e.max === t.max;
}
function TY(e, t) {
  return QT(e.x, t.x) && QT(e.y, t.y);
}
function JT(e, t) {
  return Math.round(e.min) === Math.round(t.min) && Math.round(e.max) === Math.round(t.max);
}
function cD(e, t) {
  return JT(e.x, t.x) && JT(e.y, t.y);
}
function ek(e) {
  return Rt(e.x) / Rt(e.y);
}
function tk(e, t) {
  return e.translate === t.translate && e.scale === t.scale && e.originPoint === t.originPoint;
}
class kY {
  constructor() {
    this.members = [];
  }
  add(t) {
    pw(this.members, t), t.scheduleRender();
  }
  remove(t) {
    if ((mw(this.members, t), t === this.prevLead && (this.prevLead = void 0), t === this.lead)) {
      const n = this.members[this.members.length - 1];
      n && this.promote(n);
    }
  }
  relegate(t) {
    const n = this.members.findIndex((i) => t === i);
    if (n === 0) return !1;
    let r;
    for (let i = n; i >= 0; i--) {
      const o = this.members[i];
      if (o.isPresent !== !1) {
        r = o;
        break;
      }
    }
    return r ? (this.promote(r), !0) : !1;
  }
  promote(t, n) {
    const r = this.lead;
    if (t !== r && ((this.prevLead = r), (this.lead = t), t.show(), r)) {
      r.instance && r.scheduleRender(),
        t.scheduleRender(),
        (t.resumeFrom = r),
        n && (t.resumeFrom.preserveOpacity = !0),
        r.snapshot &&
          ((t.snapshot = r.snapshot),
          (t.snapshot.latestValues = r.animationValues || r.latestValues)),
        t.root && t.root.isUpdating && (t.isLayoutDirty = !0);
      const { crossfade: i } = t.options;
      i === !1 && r.hide();
    }
  }
  exitAnimationComplete() {
    this.members.forEach((t) => {
      const { options: n, resumingFrom: r } = t;
      n.onExitComplete && n.onExitComplete(),
        r && r.options.onExitComplete && r.options.onExitComplete();
    });
  }
  scheduleRender() {
    this.members.forEach((t) => {
      t.instance && t.scheduleRender(!1);
    });
  }
  removeLeadSnapshot() {
    this.lead && this.lead.snapshot && (this.lead.snapshot = void 0);
  }
}
function RY(e, t, n) {
  let r = "";
  const i = e.x.translate / t.x,
    o = e.y.translate / t.y,
    s = (n == null ? void 0 : n.z) || 0;
  if (
    ((i || o || s) && (r = `translate3d(${i}px, ${o}px, ${s}px) `),
    (t.x !== 1 || t.y !== 1) && (r += `scale(${1 / t.x}, ${1 / t.y}) `),
    n)
  ) {
    const { transformPerspective: l, rotate: c, rotateX: f, rotateY: d, skewX: h, skewY: v } = n;
    l && (r = `perspective(${l}px) ${r}`),
      c && (r += `rotate(${c}deg) `),
      f && (r += `rotateX(${f}deg) `),
      d && (r += `rotateY(${d}deg) `),
      h && (r += `skewX(${h}deg) `),
      v && (r += `skewY(${v}deg) `);
  }
  const a = e.x.scale * t.x,
    u = e.y.scale * t.y;
  return (a !== 1 || u !== 1) && (r += `scale(${a}, ${u})`), r || "none";
}
const Hr = {
    type: "projectionFrame",
    totalNodes: 0,
    resolvedTargetDeltas: 0,
    recalculatedProjection: 0,
  },
  hs = typeof window < "u" && window.MotionDebug !== void 0,
  Tg = ["", "X", "Y", "Z"],
  PY = { visibility: "hidden" },
  nk = 1e3;
let AY = 0;
function kg(e, t, n, r) {
  const { latestValues: i } = t;
  i[e] && ((n[e] = i[e]), t.setStaticValue(e, 0), r && (r[e] = 0));
}
function fD(e) {
  if (((e.hasCheckedOptimisedAppear = !0), e.root === e)) return;
  const { visualElement: t } = e.options;
  if (!t) return;
  const n = yI(t);
  if (window.MotionHasOptimisedAnimation(n, "transform")) {
    const { layout: i, layoutId: o } = e.options;
    window.MotionCancelOptimisedAnimation(n, "transform", fe, !(i || o));
  }
  const { parent: r } = e;
  r && !r.hasCheckedOptimisedAppear && fD(r);
}
function dD({
  attachResizeListener: e,
  defaultParent: t,
  measureScroll: n,
  checkIsScrollRoot: r,
  resetTransform: i,
}) {
  return class {
    constructor(s = {}, a = t == null ? void 0 : t()) {
      (this.id = AY++),
        (this.animationId = 0),
        (this.children = new Set()),
        (this.options = {}),
        (this.isTreeAnimating = !1),
        (this.isAnimationBlocked = !1),
        (this.isLayoutDirty = !1),
        (this.isProjectionDirty = !1),
        (this.isSharedProjectionDirty = !1),
        (this.isTransformDirty = !1),
        (this.updateManuallyBlocked = !1),
        (this.updateBlockedByResize = !1),
        (this.isUpdating = !1),
        (this.isSVG = !1),
        (this.needsReset = !1),
        (this.shouldResetTransform = !1),
        (this.hasCheckedOptimisedAppear = !1),
        (this.treeScale = { x: 1, y: 1 }),
        (this.eventHandlers = new Map()),
        (this.hasTreeAnimated = !1),
        (this.updateScheduled = !1),
        (this.scheduleUpdate = () => this.update()),
        (this.projectionUpdateScheduled = !1),
        (this.checkUpdateFailed = () => {
          this.isUpdating && ((this.isUpdating = !1), this.clearAllSnapshots());
        }),
        (this.updateProjection = () => {
          (this.projectionUpdateScheduled = !1),
            hs && (Hr.totalNodes = Hr.resolvedTargetDeltas = Hr.recalculatedProjection = 0),
            this.nodes.forEach(IY),
            this.nodes.forEach(jY),
            this.nodes.forEach(VY),
            this.nodes.forEach(DY),
            hs && window.MotionDebug.record(Hr);
        }),
        (this.resolvedRelativeTargetAt = 0),
        (this.hasProjected = !1),
        (this.isVisible = !0),
        (this.animationProgress = 0),
        (this.sharedNodes = new Map()),
        (this.latestValues = s),
        (this.root = a ? a.root || a : this),
        (this.path = a ? [...a.path, a] : []),
        (this.parent = a),
        (this.depth = a ? a.depth + 1 : 0);
      for (let u = 0; u < this.path.length; u++) this.path[u].shouldResetTransform = !0;
      this.root === this && (this.nodes = new vY());
    }
    addEventListener(s, a) {
      return (
        this.eventHandlers.has(s) || this.eventHandlers.set(s, new gw()),
        this.eventHandlers.get(s).add(a)
      );
    }
    notifyListeners(s, ...a) {
      const u = this.eventHandlers.get(s);
      u && u.notify(...a);
    }
    hasListeners(s) {
      return this.eventHandlers.has(s);
    }
    mount(s, a = this.root.hasTreeAnimated) {
      if (this.instance) return;
      (this.isSVG = mY(s)), (this.instance = s);
      const { layoutId: u, layout: l, visualElement: c } = this.options;
      if (
        (c && !c.current && c.mount(s),
        this.root.nodes.add(this),
        this.parent && this.parent.children.add(this),
        a && (l || u) && (this.isLayoutDirty = !0),
        e)
      ) {
        let f;
        const d = () => (this.root.updateBlockedByResize = !1);
        e(s, () => {
          (this.root.updateBlockedByResize = !0),
            f && f(),
            (f = yY(d, 250)),
            Mu.hasAnimatedSinceResize && ((Mu.hasAnimatedSinceResize = !1), this.nodes.forEach(ik));
        });
      }
      u && this.root.registerSharedNode(u, this),
        this.options.animate !== !1 &&
          c &&
          (u || l) &&
          this.addEventListener(
            "didUpdate",
            ({ delta: f, hasLayoutChanged: d, hasRelativeTargetChanged: h, layout: v }) => {
              if (this.isTreeAnimationBlocked()) {
                (this.target = void 0), (this.relativeTarget = void 0);
                return;
              }
              const p = this.options.transition || c.getDefaultTransition() || UY,
                { onLayoutAnimationStart: y, onLayoutAnimationComplete: m } = c.getProps(),
                g = !this.targetLayout || !cD(this.targetLayout, v) || h,
                w = !d && h;
              if (
                this.options.layoutRoot ||
                (this.resumeFrom && this.resumeFrom.instance) ||
                w ||
                (d && (g || !this.currentAnimation))
              ) {
                this.resumeFrom &&
                  ((this.resumingFrom = this.resumeFrom),
                  (this.resumingFrom.resumingFrom = void 0)),
                  this.setAnimationOrigin(f, w);
                const x = { ...cw(p, "layout"), onPlay: y, onComplete: m };
                (c.shouldReduceMotion || this.options.layoutRoot) && ((x.delay = 0), (x.type = !1)),
                  this.startAnimation(x);
              } else
                d || ik(this),
                  this.isLead() && this.options.onExitComplete && this.options.onExitComplete();
              this.targetLayout = v;
            },
          );
    }
    unmount() {
      this.options.layoutId && this.willUpdate(), this.root.nodes.remove(this);
      const s = this.getStack();
      s && s.remove(this),
        this.parent && this.parent.children.delete(this),
        (this.instance = void 0),
        Xn(this.updateProjection);
    }
    blockUpdate() {
      this.updateManuallyBlocked = !0;
    }
    unblockUpdate() {
      this.updateManuallyBlocked = !1;
    }
    isUpdateBlocked() {
      return this.updateManuallyBlocked || this.updateBlockedByResize;
    }
    isTreeAnimationBlocked() {
      return this.isAnimationBlocked || (this.parent && this.parent.isTreeAnimationBlocked()) || !1;
    }
    startUpdate() {
      this.isUpdateBlocked() ||
        ((this.isUpdating = !0), this.nodes && this.nodes.forEach(qY), this.animationId++);
    }
    getTransformTemplate() {
      const { visualElement: s } = this.options;
      return s && s.getProps().transformTemplate;
    }
    willUpdate(s = !0) {
      if (((this.root.hasTreeAnimated = !0), this.root.isUpdateBlocked())) {
        this.options.onExitComplete && this.options.onExitComplete();
        return;
      }
      if (
        (window.MotionCancelOptimisedAnimation && !this.hasCheckedOptimisedAppear && fD(this),
        !this.root.isUpdating && this.root.startUpdate(),
        this.isLayoutDirty)
      )
        return;
      this.isLayoutDirty = !0;
      for (let c = 0; c < this.path.length; c++) {
        const f = this.path[c];
        (f.shouldResetTransform = !0),
          f.updateScroll("snapshot"),
          f.options.layoutRoot && f.willUpdate(!1);
      }
      const { layoutId: a, layout: u } = this.options;
      if (a === void 0 && !u) return;
      const l = this.getTransformTemplate();
      (this.prevTransformTemplateValue = l ? l(this.latestValues, "") : void 0),
        this.updateSnapshot(),
        s && this.notifyListeners("willUpdate");
    }
    update() {
      if (((this.updateScheduled = !1), this.isUpdateBlocked())) {
        this.unblockUpdate(), this.clearAllSnapshots(), this.nodes.forEach(rk);
        return;
      }
      this.isUpdating || this.nodes.forEach(LY),
        (this.isUpdating = !1),
        this.nodes.forEach(FY),
        this.nodes.forEach(NY),
        this.nodes.forEach(MY),
        this.clearAllSnapshots();
      const a = _n.now();
      ($e.delta = Zn(0, 1e3 / 60, a - $e.timestamp)),
        ($e.timestamp = a),
        ($e.isProcessing = !0),
        vg.update.process($e),
        vg.preRender.process($e),
        vg.render.process($e),
        ($e.isProcessing = !1);
    }
    didUpdate() {
      this.updateScheduled || ((this.updateScheduled = !0), ew.read(this.scheduleUpdate));
    }
    clearAllSnapshots() {
      this.nodes.forEach(OY), this.sharedNodes.forEach($Y);
    }
    scheduleUpdateProjection() {
      this.projectionUpdateScheduled ||
        ((this.projectionUpdateScheduled = !0), fe.preRender(this.updateProjection, !1, !0));
    }
    scheduleCheckAfterUnmount() {
      fe.postRender(() => {
        this.isLayoutDirty ? this.root.didUpdate() : this.root.checkUpdateFailed();
      });
    }
    updateSnapshot() {
      this.snapshot || !this.instance || (this.snapshot = this.measure());
    }
    updateLayout() {
      if (
        !this.instance ||
        (this.updateScroll(),
        !(this.options.alwaysMeasureLayout && this.isLead()) && !this.isLayoutDirty)
      )
        return;
      if (this.resumeFrom && !this.resumeFrom.instance)
        for (let u = 0; u < this.path.length; u++) this.path[u].updateScroll();
      const s = this.layout;
      (this.layout = this.measure(!1)),
        (this.layoutCorrected = Ae()),
        (this.isLayoutDirty = !1),
        (this.projectionDelta = void 0),
        this.notifyListeners("measure", this.layout.layoutBox);
      const { visualElement: a } = this.options;
      a && a.notify("LayoutMeasure", this.layout.layoutBox, s ? s.layoutBox : void 0);
    }
    updateScroll(s = "measure") {
      let a = !!(this.options.layoutScroll && this.instance);
      if (
        (this.scroll &&
          this.scroll.animationId === this.root.animationId &&
          this.scroll.phase === s &&
          (a = !1),
        a)
      ) {
        const u = r(this.instance);
        this.scroll = {
          animationId: this.root.animationId,
          phase: s,
          isRoot: u,
          offset: n(this.instance),
          wasRoot: this.scroll ? this.scroll.isRoot : u,
        };
      }
    }
    resetTransform() {
      if (!i) return;
      const s = this.isLayoutDirty || this.shouldResetTransform || this.options.alwaysMeasureLayout,
        a = this.projectionDelta && !lD(this.projectionDelta),
        u = this.getTransformTemplate(),
        l = u ? u(this.latestValues, "") : void 0,
        c = l !== this.prevTransformTemplateValue;
      s &&
        (a || Ur(this.latestValues) || c) &&
        (i(this.instance, l), (this.shouldResetTransform = !1), this.scheduleRender());
    }
    measure(s = !0) {
      const a = this.measurePageBox();
      let u = this.removeElementScroll(a);
      return (
        s && (u = this.removeTransform(u)),
        HY(u),
        {
          animationId: this.root.animationId,
          measuredBox: a,
          layoutBox: u,
          latestValues: {},
          source: this.id,
        }
      );
    }
    measurePageBox() {
      var s;
      const { visualElement: a } = this.options;
      if (!a) return Ae();
      const u = a.measureViewportBox();
      if (
        !(((s = this.scroll) === null || s === void 0 ? void 0 : s.wasRoot) || this.path.some(GY))
      ) {
        const { scroll: c } = this.root;
        c && (Ui(u.x, c.offset.x), Ui(u.y, c.offset.y));
      }
      return u;
    }
    removeElementScroll(s) {
      var a;
      const u = Ae();
      if ((Nt(u, s), !((a = this.scroll) === null || a === void 0) && a.wasRoot)) return u;
      for (let l = 0; l < this.path.length; l++) {
        const c = this.path[l],
          { scroll: f, options: d } = c;
        c !== this.root &&
          f &&
          d.layoutScroll &&
          (f.wasRoot && Nt(u, s), Ui(u.x, f.offset.x), Ui(u.y, f.offset.y));
      }
      return u;
    }
    applyTransform(s, a = !1) {
      const u = Ae();
      Nt(u, s);
      for (let l = 0; l < this.path.length; l++) {
        const c = this.path[l];
        !a &&
          c.options.layoutScroll &&
          c.scroll &&
          c !== c.root &&
          Hi(u, { x: -c.scroll.offset.x, y: -c.scroll.offset.y }),
          Ur(c.latestValues) && Hi(u, c.latestValues);
      }
      return Ur(this.latestValues) && Hi(u, this.latestValues), u;
    }
    removeTransform(s) {
      const a = Ae();
      Nt(a, s);
      for (let u = 0; u < this.path.length; u++) {
        const l = this.path[u];
        if (!l.instance || !Ur(l.latestValues)) continue;
        ry(l.latestValues) && l.updateSnapshot();
        const c = Ae(),
          f = l.measurePageBox();
        Nt(c, f), XT(a, l.latestValues, l.snapshot ? l.snapshot.layoutBox : void 0, c);
      }
      return Ur(this.latestValues) && XT(a, this.latestValues), a;
    }
    setTargetDelta(s) {
      (this.targetDelta = s), this.root.scheduleUpdateProjection(), (this.isProjectionDirty = !0);
    }
    setOptions(s) {
      this.options = {
        ...this.options,
        ...s,
        crossfade: s.crossfade !== void 0 ? s.crossfade : !0,
      };
    }
    clearMeasurements() {
      (this.scroll = void 0),
        (this.layout = void 0),
        (this.snapshot = void 0),
        (this.prevTransformTemplateValue = void 0),
        (this.targetDelta = void 0),
        (this.target = void 0),
        (this.isLayoutDirty = !1);
    }
    forceRelativeParentToResolveTarget() {
      this.relativeParent &&
        this.relativeParent.resolvedRelativeTargetAt !== $e.timestamp &&
        this.relativeParent.resolveTargetDelta(!0);
    }
    resolveTargetDelta(s = !1) {
      var a;
      const u = this.getLead();
      this.isProjectionDirty || (this.isProjectionDirty = u.isProjectionDirty),
        this.isTransformDirty || (this.isTransformDirty = u.isTransformDirty),
        this.isSharedProjectionDirty || (this.isSharedProjectionDirty = u.isSharedProjectionDirty);
      const l = !!this.resumingFrom || this !== u;
      if (
        !(
          s ||
          (l && this.isSharedProjectionDirty) ||
          this.isProjectionDirty ||
          (!((a = this.parent) === null || a === void 0) && a.isProjectionDirty) ||
          this.attemptToResolveRelativeTarget ||
          this.root.updateBlockedByResize
        )
      )
        return;
      const { layout: f, layoutId: d } = this.options;
      if (!(!this.layout || !(f || d))) {
        if (
          ((this.resolvedRelativeTargetAt = $e.timestamp),
          !this.targetDelta && !this.relativeTarget)
        ) {
          const h = this.getClosestProjectingParent();
          h && h.layout && this.animationProgress !== 1
            ? ((this.relativeParent = h),
              this.forceRelativeParentToResolveTarget(),
              (this.relativeTarget = Ae()),
              (this.relativeTargetOrigin = Ae()),
              Rs(this.relativeTargetOrigin, this.layout.layoutBox, h.layout.layoutBox),
              Nt(this.relativeTarget, this.relativeTargetOrigin))
            : (this.relativeParent = this.relativeTarget = void 0);
        }
        if (!(!this.relativeTarget && !this.targetDelta)) {
          if (
            (this.target || ((this.target = Ae()), (this.targetWithTransforms = Ae())),
            this.relativeTarget &&
            this.relativeTargetOrigin &&
            this.relativeParent &&
            this.relativeParent.target
              ? (this.forceRelativeParentToResolveTarget(),
                YK(this.target, this.relativeTarget, this.relativeParent.target))
              : this.targetDelta
                ? (this.resumingFrom
                    ? (this.target = this.applyTransform(this.layout.layoutBox))
                    : Nt(this.target, this.layout.layoutBox),
                  rD(this.target, this.targetDelta))
                : Nt(this.target, this.layout.layoutBox),
            this.attemptToResolveRelativeTarget)
          ) {
            this.attemptToResolveRelativeTarget = !1;
            const h = this.getClosestProjectingParent();
            h &&
            !!h.resumingFrom == !!this.resumingFrom &&
            !h.options.layoutScroll &&
            h.target &&
            this.animationProgress !== 1
              ? ((this.relativeParent = h),
                this.forceRelativeParentToResolveTarget(),
                (this.relativeTarget = Ae()),
                (this.relativeTargetOrigin = Ae()),
                Rs(this.relativeTargetOrigin, this.target, h.target),
                Nt(this.relativeTarget, this.relativeTargetOrigin))
              : (this.relativeParent = this.relativeTarget = void 0);
          }
          hs && Hr.resolvedTargetDeltas++;
        }
      }
    }
    getClosestProjectingParent() {
      if (!(!this.parent || ry(this.parent.latestValues) || nD(this.parent.latestValues)))
        return this.parent.isProjecting() ? this.parent : this.parent.getClosestProjectingParent();
    }
    isProjecting() {
      return !!(
        (this.relativeTarget || this.targetDelta || this.options.layoutRoot) &&
        this.layout
      );
    }
    calcProjection() {
      var s;
      const a = this.getLead(),
        u = !!this.resumingFrom || this !== a;
      let l = !0;
      if (
        ((this.isProjectionDirty ||
          (!((s = this.parent) === null || s === void 0) && s.isProjectionDirty)) &&
          (l = !1),
        u && (this.isSharedProjectionDirty || this.isTransformDirty) && (l = !1),
        this.resolvedRelativeTargetAt === $e.timestamp && (l = !1),
        l)
      )
        return;
      const { layout: c, layoutId: f } = this.options;
      if (
        ((this.isTreeAnimating = !!(
          (this.parent && this.parent.isTreeAnimating) ||
          this.currentAnimation ||
          this.pendingAnimation
        )),
        this.isTreeAnimating || (this.targetDelta = this.relativeTarget = void 0),
        !this.layout || !(c || f))
      )
        return;
      Nt(this.layoutCorrected, this.layout.layoutBox);
      const d = this.treeScale.x,
        h = this.treeScale.y;
      iY(this.layoutCorrected, this.treeScale, this.path, u),
        a.layout &&
          !a.target &&
          (this.treeScale.x !== 1 || this.treeScale.y !== 1) &&
          ((a.target = a.layout.layoutBox), (a.targetWithTransforms = Ae()));
      const { target: v } = a;
      if (!v) {
        this.prevProjectionDelta && (this.createProjectionDeltas(), this.scheduleRender());
        return;
      }
      !this.projectionDelta || !this.prevProjectionDelta
        ? this.createProjectionDeltas()
        : (WT(this.prevProjectionDelta.x, this.projectionDelta.x),
          WT(this.prevProjectionDelta.y, this.projectionDelta.y)),
        ks(this.projectionDelta, this.layoutCorrected, v, this.latestValues),
        (this.treeScale.x !== d ||
          this.treeScale.y !== h ||
          !tk(this.projectionDelta.x, this.prevProjectionDelta.x) ||
          !tk(this.projectionDelta.y, this.prevProjectionDelta.y)) &&
          ((this.hasProjected = !0),
          this.scheduleRender(),
          this.notifyListeners("projectionUpdate", v)),
        hs && Hr.recalculatedProjection++;
    }
    hide() {
      this.isVisible = !1;
    }
    show() {
      this.isVisible = !0;
    }
    scheduleRender(s = !0) {
      var a;
      if (((a = this.options.visualElement) === null || a === void 0 || a.scheduleRender(), s)) {
        const u = this.getStack();
        u && u.scheduleRender();
      }
      this.resumingFrom && !this.resumingFrom.instance && (this.resumingFrom = void 0);
    }
    createProjectionDeltas() {
      (this.prevProjectionDelta = Bi()),
        (this.projectionDelta = Bi()),
        (this.projectionDeltaWithTransform = Bi());
    }
    setAnimationOrigin(s, a = !1) {
      const u = this.snapshot,
        l = u ? u.latestValues : {},
        c = { ...this.latestValues },
        f = Bi();
      (!this.relativeParent || !this.relativeParent.options.layoutRoot) &&
        (this.relativeTarget = this.relativeTargetOrigin = void 0),
        (this.attemptToResolveRelativeTarget = !a);
      const d = Ae(),
        h = u ? u.source : void 0,
        v = this.layout ? this.layout.source : void 0,
        p = h !== v,
        y = this.getStack(),
        m = !y || y.members.length <= 1,
        g = !!(p && !m && this.options.crossfade === !0 && !this.path.some(BY));
      this.animationProgress = 0;
      let w;
      (this.mixTargetDelta = (x) => {
        const b = x / 1e3;
        ok(f.x, s.x, b),
          ok(f.y, s.y, b),
          this.setTargetDelta(f),
          this.relativeTarget &&
            this.relativeTargetOrigin &&
            this.layout &&
            this.relativeParent &&
            this.relativeParent.layout &&
            (Rs(d, this.layout.layoutBox, this.relativeParent.layout.layoutBox),
            zY(this.relativeTarget, this.relativeTargetOrigin, d, b),
            w && TY(this.relativeTarget, w) && (this.isProjectionDirty = !1),
            w || (w = Ae()),
            Nt(w, this.relativeTarget)),
          p && ((this.animationValues = c), xY(c, l, this.latestValues, b, g, m)),
          this.root.scheduleUpdateProjection(),
          this.scheduleRender(),
          (this.animationProgress = b);
      }),
        this.mixTargetDelta(this.options.layoutRoot ? 1e3 : 0);
    }
    startAnimation(s) {
      this.notifyListeners("animationStart"),
        this.currentAnimation && this.currentAnimation.stop(),
        this.resumingFrom &&
          this.resumingFrom.currentAnimation &&
          this.resumingFrom.currentAnimation.stop(),
        this.pendingAnimation && (Xn(this.pendingAnimation), (this.pendingAnimation = void 0)),
        (this.pendingAnimation = fe.update(() => {
          (Mu.hasAnimatedSinceResize = !0),
            (this.currentAnimation = pY(0, nk, {
              ...s,
              onUpdate: (a) => {
                this.mixTargetDelta(a), s.onUpdate && s.onUpdate(a);
              },
              onComplete: () => {
                s.onComplete && s.onComplete(), this.completeAnimation();
              },
            })),
            this.resumingFrom && (this.resumingFrom.currentAnimation = this.currentAnimation),
            (this.pendingAnimation = void 0);
        }));
    }
    completeAnimation() {
      this.resumingFrom &&
        ((this.resumingFrom.currentAnimation = void 0),
        (this.resumingFrom.preserveOpacity = void 0));
      const s = this.getStack();
      s && s.exitAnimationComplete(),
        (this.resumingFrom = this.currentAnimation = this.animationValues = void 0),
        this.notifyListeners("animationComplete");
    }
    finishAnimation() {
      this.currentAnimation &&
        (this.mixTargetDelta && this.mixTargetDelta(nk), this.currentAnimation.stop()),
        this.completeAnimation();
    }
    applyTransformsToTarget() {
      const s = this.getLead();
      let { targetWithTransforms: a, target: u, layout: l, latestValues: c } = s;
      if (!(!a || !u || !l)) {
        if (
          this !== s &&
          this.layout &&
          l &&
          hD(this.options.animationType, this.layout.layoutBox, l.layoutBox)
        ) {
          u = this.target || Ae();
          const f = Rt(this.layout.layoutBox.x);
          (u.x.min = s.target.x.min), (u.x.max = u.x.min + f);
          const d = Rt(this.layout.layoutBox.y);
          (u.y.min = s.target.y.min), (u.y.max = u.y.min + d);
        }
        Nt(a, u), Hi(a, c), ks(this.projectionDeltaWithTransform, this.layoutCorrected, a, c);
      }
    }
    registerSharedNode(s, a) {
      this.sharedNodes.has(s) || this.sharedNodes.set(s, new kY()), this.sharedNodes.get(s).add(a);
      const l = a.options.initialPromotionConfig;
      a.promote({
        transition: l ? l.transition : void 0,
        preserveFollowOpacity:
          l && l.shouldPreserveFollowOpacity ? l.shouldPreserveFollowOpacity(a) : void 0,
      });
    }
    isLead() {
      const s = this.getStack();
      return s ? s.lead === this : !0;
    }
    getLead() {
      var s;
      const { layoutId: a } = this.options;
      return a ? ((s = this.getStack()) === null || s === void 0 ? void 0 : s.lead) || this : this;
    }
    getPrevLead() {
      var s;
      const { layoutId: a } = this.options;
      return a ? ((s = this.getStack()) === null || s === void 0 ? void 0 : s.prevLead) : void 0;
    }
    getStack() {
      const { layoutId: s } = this.options;
      if (s) return this.root.sharedNodes.get(s);
    }
    promote({ needsReset: s, transition: a, preserveFollowOpacity: u } = {}) {
      const l = this.getStack();
      l && l.promote(this, u),
        s && ((this.projectionDelta = void 0), (this.needsReset = !0)),
        a && this.setOptions({ transition: a });
    }
    relegate() {
      const s = this.getStack();
      return s ? s.relegate(this) : !1;
    }
    resetSkewAndRotation() {
      const { visualElement: s } = this.options;
      if (!s) return;
      let a = !1;
      const { latestValues: u } = s;
      if (
        ((u.z || u.rotate || u.rotateX || u.rotateY || u.rotateZ || u.skewX || u.skewY) && (a = !0),
        !a)
      )
        return;
      const l = {};
      u.z && kg("z", s, l, this.animationValues);
      for (let c = 0; c < Tg.length; c++)
        kg(`rotate${Tg[c]}`, s, l, this.animationValues),
          kg(`skew${Tg[c]}`, s, l, this.animationValues);
      s.render();
      for (const c in l)
        s.setStaticValue(c, l[c]), this.animationValues && (this.animationValues[c] = l[c]);
      s.scheduleRender();
    }
    getProjectionStyles(s) {
      var a, u;
      if (!this.instance || this.isSVG) return;
      if (!this.isVisible) return PY;
      const l = { visibility: "" },
        c = this.getTransformTemplate();
      if (this.needsReset)
        return (
          (this.needsReset = !1),
          (l.opacity = ""),
          (l.pointerEvents = Au(s == null ? void 0 : s.pointerEvents) || ""),
          (l.transform = c ? c(this.latestValues, "") : "none"),
          l
        );
      const f = this.getLead();
      if (!this.projectionDelta || !this.layout || !f.target) {
        const p = {};
        return (
          this.options.layoutId &&
            ((p.opacity = this.latestValues.opacity !== void 0 ? this.latestValues.opacity : 1),
            (p.pointerEvents = Au(s == null ? void 0 : s.pointerEvents) || "")),
          this.hasProjected &&
            !Ur(this.latestValues) &&
            ((p.transform = c ? c({}, "") : "none"), (this.hasProjected = !1)),
          p
        );
      }
      const d = f.animationValues || f.latestValues;
      this.applyTransformsToTarget(),
        (l.transform = RY(this.projectionDeltaWithTransform, this.treeScale, d)),
        c && (l.transform = c(d, l.transform));
      const { x: h, y: v } = this.projectionDelta;
      (l.transformOrigin = `${h.origin * 100}% ${v.origin * 100}% 0`),
        f.animationValues
          ? (l.opacity =
              f === this
                ? (u = (a = d.opacity) !== null && a !== void 0 ? a : this.latestValues.opacity) !==
                    null && u !== void 0
                  ? u
                  : 1
                : this.preserveOpacity
                  ? this.latestValues.opacity
                  : d.opacityExit)
          : (l.opacity =
              f === this
                ? d.opacity !== void 0
                  ? d.opacity
                  : ""
                : d.opacityExit !== void 0
                  ? d.opacityExit
                  : 0);
      for (const p in wl) {
        if (d[p] === void 0) continue;
        const { correct: y, applyTo: m } = wl[p],
          g = l.transform === "none" ? d[p] : y(d[p], f);
        if (m) {
          const w = m.length;
          for (let x = 0; x < w; x++) l[m[x]] = g;
        } else l[p] = g;
      }
      return (
        this.options.layoutId &&
          (l.pointerEvents = f === this ? Au(s == null ? void 0 : s.pointerEvents) || "" : "none"),
        l
      );
    }
    clearSnapshot() {
      this.resumeFrom = this.snapshot = void 0;
    }
    resetTree() {
      this.root.nodes.forEach((s) => {
        var a;
        return (a = s.currentAnimation) === null || a === void 0 ? void 0 : a.stop();
      }),
        this.root.nodes.forEach(rk),
        this.root.sharedNodes.clear();
    }
  };
}
function NY(e) {
  e.updateLayout();
}
function MY(e) {
  var t;
  const n = ((t = e.resumeFrom) === null || t === void 0 ? void 0 : t.snapshot) || e.snapshot;
  if (e.isLead() && e.layout && n && e.hasListeners("didUpdate")) {
    const { layoutBox: r, measuredBox: i } = e.layout,
      { animationType: o } = e.options,
      s = n.source !== e.layout.source;
    o === "size"
      ? Mt((f) => {
          const d = s ? n.measuredBox[f] : n.layoutBox[f],
            h = Rt(d);
          (d.min = r[f].min), (d.max = d.min + h);
        })
      : hD(o, n.layoutBox, r) &&
        Mt((f) => {
          const d = s ? n.measuredBox[f] : n.layoutBox[f],
            h = Rt(r[f]);
          (d.max = d.min + h),
            e.relativeTarget &&
              !e.currentAnimation &&
              ((e.isProjectionDirty = !0), (e.relativeTarget[f].max = e.relativeTarget[f].min + h));
        });
    const a = Bi();
    ks(a, r, n.layoutBox);
    const u = Bi();
    s ? ks(u, e.applyTransform(i, !0), n.measuredBox) : ks(u, r, n.layoutBox);
    const l = !lD(a);
    let c = !1;
    if (!e.resumeFrom) {
      const f = e.getClosestProjectingParent();
      if (f && !f.resumeFrom) {
        const { snapshot: d, layout: h } = f;
        if (d && h) {
          const v = Ae();
          Rs(v, n.layoutBox, d.layoutBox);
          const p = Ae();
          Rs(p, r, h.layoutBox),
            cD(v, p) || (c = !0),
            f.options.layoutRoot &&
              ((e.relativeTarget = p), (e.relativeTargetOrigin = v), (e.relativeParent = f));
        }
      }
    }
    e.notifyListeners("didUpdate", {
      layout: r,
      snapshot: n,
      delta: u,
      layoutDelta: a,
      hasLayoutChanged: l,
      hasRelativeTargetChanged: c,
    });
  } else if (e.isLead()) {
    const { onExitComplete: r } = e.options;
    r && r();
  }
  e.options.transition = void 0;
}
function IY(e) {
  hs && Hr.totalNodes++,
    e.parent &&
      (e.isProjecting() || (e.isProjectionDirty = e.parent.isProjectionDirty),
      e.isSharedProjectionDirty ||
        (e.isSharedProjectionDirty = !!(
          e.isProjectionDirty ||
          e.parent.isProjectionDirty ||
          e.parent.isSharedProjectionDirty
        )),
      e.isTransformDirty || (e.isTransformDirty = e.parent.isTransformDirty));
}
function DY(e) {
  e.isProjectionDirty = e.isSharedProjectionDirty = e.isTransformDirty = !1;
}
function OY(e) {
  e.clearSnapshot();
}
function rk(e) {
  e.clearMeasurements();
}
function LY(e) {
  e.isLayoutDirty = !1;
}
function FY(e) {
  const { visualElement: t } = e.options;
  t && t.getProps().onBeforeLayoutMeasure && t.notify("BeforeLayoutMeasure"), e.resetTransform();
}
function ik(e) {
  e.finishAnimation(),
    (e.targetDelta = e.relativeTarget = e.target = void 0),
    (e.isProjectionDirty = !0);
}
function jY(e) {
  e.resolveTargetDelta();
}
function VY(e) {
  e.calcProjection();
}
function qY(e) {
  e.resetSkewAndRotation();
}
function $Y(e) {
  e.removeLeadSnapshot();
}
function ok(e, t, n) {
  (e.translate = _e(t.translate, 0, n)),
    (e.scale = _e(t.scale, 1, n)),
    (e.origin = t.origin),
    (e.originPoint = t.originPoint);
}
function sk(e, t, n, r) {
  (e.min = _e(t.min, n.min, r)), (e.max = _e(t.max, n.max, r));
}
function zY(e, t, n, r) {
  sk(e.x, t.x, n.x, r), sk(e.y, t.y, n.y, r);
}
function BY(e) {
  return e.animationValues && e.animationValues.opacityExit !== void 0;
}
const UY = { duration: 0.45, ease: [0.4, 0, 0.1, 1] },
  ak = (e) =>
    typeof navigator < "u" && navigator.userAgent && navigator.userAgent.toLowerCase().includes(e),
  uk = ak("applewebkit/") && !ak("chrome/") ? Math.round : Ct;
function lk(e) {
  (e.min = uk(e.min)), (e.max = uk(e.max));
}
function HY(e) {
  lk(e.x), lk(e.y);
}
function hD(e, t, n) {
  return e === "position" || (e === "preserve-aspect" && !KK(ek(t), ek(n), 0.2));
}
function GY(e) {
  var t;
  return e !== e.root && ((t = e.scroll) === null || t === void 0 ? void 0 : t.wasRoot);
}
const WY = dD({
    attachResizeListener: (e, t) => ia(e, "resize", t),
    measureScroll: () => ({
      x: document.documentElement.scrollLeft || document.body.scrollLeft,
      y: document.documentElement.scrollTop || document.body.scrollTop,
    }),
    checkIsScrollRoot: () => !0,
  }),
  Rg = { current: void 0 },
  pD = dD({
    measureScroll: (e) => ({ x: e.scrollLeft, y: e.scrollTop }),
    defaultParent: () => {
      if (!Rg.current) {
        const e = new WY({});
        e.mount(window), e.setOptions({ layoutScroll: !0 }), (Rg.current = e);
      }
      return Rg.current;
    },
    resetTransform: (e, t) => {
      e.style.transform = t !== void 0 ? t : "none";
    },
    checkIsScrollRoot: (e) => window.getComputedStyle(e).position === "fixed",
  }),
  KY = { pan: { Feature: cY }, drag: { Feature: lY, ProjectionNode: pD, MeasureLayout: sD } };
function ck(e, t, n) {
  const { props: r } = e;
  e.animationState && r.whileHover && e.animationState.setActive("whileHover", n === "Start");
  const i = "onHover" + n,
    o = r[i];
  o && fe.postRender(() => o(t, Ta(t)));
}
class YY extends Fr {
  mount() {
    const { current: t } = this.node;
    t && (this.unmount = KW(t, (n) => (ck(this.node, n, "Start"), (r) => ck(this.node, r, "End"))));
  }
  unmount() {}
}
class XY extends Fr {
  constructor() {
    super(...arguments), (this.isActive = !1);
  }
  onFocus() {
    let t = !1;
    try {
      t = this.node.current.matches(":focus-visible");
    } catch {
      t = !0;
    }
    !t ||
      !this.node.animationState ||
      (this.node.animationState.setActive("whileFocus", !0), (this.isActive = !0));
  }
  onBlur() {
    !this.isActive ||
      !this.node.animationState ||
      (this.node.animationState.setActive("whileFocus", !1), (this.isActive = !1));
  }
  mount() {
    this.unmount = Ca(
      ia(this.node.current, "focus", () => this.onFocus()),
      ia(this.node.current, "blur", () => this.onBlur()),
    );
  }
  unmount() {}
}
function fk(e, t, n) {
  const { props: r } = e;
  e.animationState && r.whileTap && e.animationState.setActive("whileTap", n === "Start");
  const i = "onTap" + (n === "End" ? "" : n),
    o = r[i];
  o && fe.postRender(() => o(t, Ta(t)));
}
class ZY extends Fr {
  mount() {
    const { current: t } = this.node;
    t &&
      (this.unmount = QW(
        t,
        (n) => (
          fk(this.node, n, "Start"), (r, { success: i }) => fk(this.node, r, i ? "End" : "Cancel")
        ),
        { useGlobalTarget: this.node.props.globalTapTarget },
      ));
  }
  unmount() {}
}
const oy = new WeakMap(),
  Pg = new WeakMap(),
  QY = (e) => {
    const t = oy.get(e.target);
    t && t(e);
  },
  JY = (e) => {
    e.forEach(QY);
  };
function eX({ root: e, ...t }) {
  const n = e || document;
  Pg.has(n) || Pg.set(n, {});
  const r = Pg.get(n),
    i = JSON.stringify(t);
  return r[i] || (r[i] = new IntersectionObserver(JY, { root: e, ...t })), r[i];
}
function tX(e, t, n) {
  const r = eX(t);
  return (
    oy.set(e, n),
    r.observe(e),
    () => {
      oy.delete(e), r.unobserve(e);
    }
  );
}
const nX = { some: 0, all: 1 };
class rX extends Fr {
  constructor() {
    super(...arguments), (this.hasEnteredView = !1), (this.isInView = !1);
  }
  startObserver() {
    this.unmount();
    const { viewport: t = {} } = this.node.getProps(),
      { root: n, margin: r, amount: i = "some", once: o } = t,
      s = {
        root: n ? n.current : void 0,
        rootMargin: r,
        threshold: typeof i == "number" ? i : nX[i],
      },
      a = (u) => {
        const { isIntersecting: l } = u;
        if (this.isInView === l || ((this.isInView = l), o && !l && this.hasEnteredView)) return;
        l && (this.hasEnteredView = !0),
          this.node.animationState && this.node.animationState.setActive("whileInView", l);
        const { onViewportEnter: c, onViewportLeave: f } = this.node.getProps(),
          d = l ? c : f;
        d && d(u);
      };
    return tX(this.node.current, s, a);
  }
  mount() {
    this.startObserver();
  }
  update() {
    if (typeof IntersectionObserver > "u") return;
    const { props: t, prevProps: n } = this.node;
    ["amount", "margin", "root"].some(iX(t, n)) && this.startObserver();
  }
  unmount() {}
}
function iX({ viewport: e = {} }, { viewport: t = {} } = {}) {
  return (n) => e[n] !== t[n];
}
const oX = {
    inView: { Feature: rX },
    tap: { Feature: ZY },
    focus: { Feature: XY },
    hover: { Feature: YY },
  },
  sX = { layout: { ProjectionNode: pD, MeasureLayout: sD } },
  sy = { current: null },
  mD = { current: !1 };
function aX() {
  if (((mD.current = !0), !!K0))
    if (window.matchMedia) {
      const e = window.matchMedia("(prefers-reduced-motion)"),
        t = () => (sy.current = e.matches);
      e.addListener(t), t();
    } else sy.current = !1;
}
const uX = [...VI, tt, Mr],
  lX = (e) => uX.find(jI(e)),
  dk = new WeakMap();
function cX(e, t, n) {
  for (const r in t) {
    const i = t[r],
      o = n[r];
    if (Be(i)) e.addValue(r, i);
    else if (Be(o)) e.addValue(r, xo(i, { owner: e }));
    else if (o !== i)
      if (e.hasValue(r)) {
        const s = e.getValue(r);
        s.liveStyle === !0 ? s.jump(i) : s.hasAnimated || s.set(i);
      } else {
        const s = e.getStaticValue(r);
        e.addValue(r, xo(s !== void 0 ? s : i, { owner: e }));
      }
  }
  for (const r in n) t[r] === void 0 && e.removeValue(r);
  return t;
}
const hk = [
  "AnimationStart",
  "AnimationComplete",
  "Update",
  "BeforeLayoutMeasure",
  "LayoutMeasure",
  "LayoutAnimationStart",
  "LayoutAnimationComplete",
];
class fX {
  scrapeMotionValuesFromProps(t, n, r) {
    return {};
  }
  constructor(
    {
      parent: t,
      props: n,
      presenceContext: r,
      reducedMotionConfig: i,
      blockInitialAnimation: o,
      visualState: s,
    },
    a = {},
  ) {
    (this.current = null),
      (this.children = new Set()),
      (this.isVariantNode = !1),
      (this.isControllingVariants = !1),
      (this.shouldReduceMotion = null),
      (this.values = new Map()),
      (this.KeyframeResolver = bw),
      (this.features = {}),
      (this.valueSubscriptions = new Map()),
      (this.prevMotionValues = {}),
      (this.events = {}),
      (this.propEventSubscriptions = {}),
      (this.notifyUpdate = () => this.notify("Update", this.latestValues)),
      (this.render = () => {
        this.current &&
          (this.triggerBuild(),
          this.renderInstance(this.current, this.renderState, this.props.style, this.projection));
      }),
      (this.renderScheduledAt = 0),
      (this.scheduleRender = () => {
        const h = _n.now();
        this.renderScheduledAt < h &&
          ((this.renderScheduledAt = h), fe.render(this.render, !1, !0));
      });
    const { latestValues: u, renderState: l, onUpdate: c } = s;
    (this.onUpdate = c),
      (this.latestValues = u),
      (this.baseTarget = { ...u }),
      (this.initialValues = n.initial ? { ...u } : {}),
      (this.renderState = l),
      (this.parent = t),
      (this.props = n),
      (this.presenceContext = r),
      (this.depth = t ? t.depth + 1 : 0),
      (this.reducedMotionConfig = i),
      (this.options = a),
      (this.blockInitialAnimation = !!o),
      (this.isControllingVariants = Ec(n)),
      (this.isVariantNode = WM(n)),
      this.isVariantNode && (this.variantChildren = new Set()),
      (this.manuallyAnimateOnMount = !!(t && t.current));
    const { willChange: f, ...d } = this.scrapeMotionValuesFromProps(n, {}, this);
    for (const h in d) {
      const v = d[h];
      u[h] !== void 0 && Be(v) && v.set(u[h], !1);
    }
  }
  mount(t) {
    (this.current = t),
      dk.set(t, this),
      this.projection && !this.projection.instance && this.projection.mount(t),
      this.parent &&
        this.isVariantNode &&
        !this.isControllingVariants &&
        (this.removeFromVariantTree = this.parent.addVariantChild(this)),
      this.values.forEach((n, r) => this.bindToMotionValue(r, n)),
      mD.current || aX(),
      (this.shouldReduceMotion =
        this.reducedMotionConfig === "never"
          ? !1
          : this.reducedMotionConfig === "always"
            ? !0
            : sy.current),
      this.parent && this.parent.children.add(this),
      this.update(this.props, this.presenceContext);
  }
  unmount() {
    dk.delete(this.current),
      this.projection && this.projection.unmount(),
      Xn(this.notifyUpdate),
      Xn(this.render),
      this.valueSubscriptions.forEach((t) => t()),
      this.valueSubscriptions.clear(),
      this.removeFromVariantTree && this.removeFromVariantTree(),
      this.parent && this.parent.children.delete(this);
    for (const t in this.events) this.events[t].clear();
    for (const t in this.features) {
      const n = this.features[t];
      n && (n.unmount(), (n.isMounted = !1));
    }
    this.current = null;
  }
  bindToMotionValue(t, n) {
    this.valueSubscriptions.has(t) && this.valueSubscriptions.get(t)();
    const r = wi.has(t),
      i = n.on("change", (a) => {
        (this.latestValues[t] = a),
          this.props.onUpdate && fe.preRender(this.notifyUpdate),
          r && this.projection && (this.projection.isTransformDirty = !0);
      }),
      o = n.on("renderRequest", this.scheduleRender);
    let s;
    window.MotionCheckAppearSync && (s = window.MotionCheckAppearSync(this, t, n)),
      this.valueSubscriptions.set(t, () => {
        i(), o(), s && s(), n.owner && n.stop();
      });
  }
  sortNodePosition(t) {
    return !this.current || !this.sortInstanceNodePosition || this.type !== t.type
      ? 0
      : this.sortInstanceNodePosition(this.current, t.current);
  }
  updateFeatures() {
    let t = "animation";
    for (t in wo) {
      const n = wo[t];
      if (!n) continue;
      const { isEnabled: r, Feature: i } = n;
      if (
        (!this.features[t] && i && r(this.props) && (this.features[t] = new i(this)),
        this.features[t])
      ) {
        const o = this.features[t];
        o.isMounted ? o.update() : (o.mount(), (o.isMounted = !0));
      }
    }
  }
  triggerBuild() {
    this.build(this.renderState, this.latestValues, this.props);
  }
  measureViewportBox() {
    return this.current ? this.measureInstanceViewportBox(this.current, this.props) : Ae();
  }
  getStaticValue(t) {
    return this.latestValues[t];
  }
  setStaticValue(t, n) {
    this.latestValues[t] = n;
  }
  update(t, n) {
    (t.transformTemplate || this.props.transformTemplate) && this.scheduleRender(),
      (this.prevProps = this.props),
      (this.props = t),
      (this.prevPresenceContext = this.presenceContext),
      (this.presenceContext = n);
    for (let r = 0; r < hk.length; r++) {
      const i = hk[r];
      this.propEventSubscriptions[i] &&
        (this.propEventSubscriptions[i](), delete this.propEventSubscriptions[i]);
      const o = "on" + i,
        s = t[o];
      s && (this.propEventSubscriptions[i] = this.on(i, s));
    }
    (this.prevMotionValues = cX(
      this,
      this.scrapeMotionValuesFromProps(t, this.prevProps, this),
      this.prevMotionValues,
    )),
      this.handleChildMotionValue && this.handleChildMotionValue(),
      this.onUpdate && this.onUpdate(this);
  }
  getProps() {
    return this.props;
  }
  getVariant(t) {
    return this.props.variants ? this.props.variants[t] : void 0;
  }
  getDefaultTransition() {
    return this.props.transition;
  }
  getTransformPagePoint() {
    return this.props.transformPagePoint;
  }
  getClosestVariantNode() {
    return this.isVariantNode ? this : this.parent ? this.parent.getClosestVariantNode() : void 0;
  }
  addVariantChild(t) {
    const n = this.getClosestVariantNode();
    if (n) return n.variantChildren && n.variantChildren.add(t), () => n.variantChildren.delete(t);
  }
  addValue(t, n) {
    const r = this.values.get(t);
    n !== r &&
      (r && this.removeValue(t),
      this.bindToMotionValue(t, n),
      this.values.set(t, n),
      (this.latestValues[t] = n.get()));
  }
  removeValue(t) {
    this.values.delete(t);
    const n = this.valueSubscriptions.get(t);
    n && (n(), this.valueSubscriptions.delete(t)),
      delete this.latestValues[t],
      this.removeValueFromRenderState(t, this.renderState);
  }
  hasValue(t) {
    return this.values.has(t);
  }
  getValue(t, n) {
    if (this.props.values && this.props.values[t]) return this.props.values[t];
    let r = this.values.get(t);
    return (
      r === void 0 &&
        n !== void 0 &&
        ((r = xo(n === null ? void 0 : n, { owner: this })), this.addValue(t, r)),
      r
    );
  }
  readValue(t, n) {
    var r;
    let i =
      this.latestValues[t] !== void 0 || !this.current
        ? this.latestValues[t]
        : (r = this.getBaseTargetFromProps(this.props, t)) !== null && r !== void 0
          ? r
          : this.readValueFromInstance(this.current, t, this.options);
    return (
      i != null &&
        (typeof i == "string" && (LI(i) || kI(i))
          ? (i = parseFloat(i))
          : !lX(i) && Mr.test(n) && (i = II(t, n)),
        this.setBaseTarget(t, Be(i) ? i.get() : i)),
      Be(i) ? i.get() : i
    );
  }
  setBaseTarget(t, n) {
    this.baseTarget[t] = n;
  }
  getBaseTarget(t) {
    var n;
    const { initial: r } = this.props;
    let i;
    if (typeof r == "string" || typeof r == "object") {
      const s = nw(
        this.props,
        r,
        (n = this.presenceContext) === null || n === void 0 ? void 0 : n.custom,
      );
      s && (i = s[t]);
    }
    if (r && i !== void 0) return i;
    const o = this.getBaseTargetFromProps(this.props, t);
    return o !== void 0 && !Be(o)
      ? o
      : this.initialValues[t] !== void 0 && i === void 0
        ? void 0
        : this.baseTarget[t];
  }
  on(t, n) {
    return this.events[t] || (this.events[t] = new gw()), this.events[t].add(n);
  }
  notify(t, ...n) {
    this.events[t] && this.events[t].notify(...n);
  }
}
class gD extends fX {
  constructor() {
    super(...arguments), (this.KeyframeResolver = qI);
  }
  sortInstanceNodePosition(t, n) {
    return t.compareDocumentPosition(n) & 2 ? 1 : -1;
  }
  getBaseTargetFromProps(t, n) {
    return t.style ? t.style[n] : void 0;
  }
  removeValueFromRenderState(t, { vars: n, style: r }) {
    delete n[t], delete r[t];
  }
  handleChildMotionValue() {
    this.childSubscription && (this.childSubscription(), delete this.childSubscription);
    const { children: t } = this.props;
    Be(t) &&
      (this.childSubscription = t.on("change", (n) => {
        this.current && (this.current.textContent = `${n}`);
      }));
  }
}
function dX(e) {
  return window.getComputedStyle(e);
}
class hX extends gD {
  constructor() {
    super(...arguments), (this.type = "html"), (this.renderInstance = nI);
  }
  readValueFromInstance(t, n) {
    if (wi.has(n)) {
      const r = _w(n);
      return (r && r.default) || 0;
    } else {
      const r = dX(t),
        i = (JM(n) ? r.getPropertyValue(n) : r[n]) || 0;
      return typeof i == "string" ? i.trim() : i;
    }
  }
  measureInstanceViewportBox(t, { transformPagePoint: n }) {
    return iD(t, n);
  }
  build(t, n, r) {
    ow(t, n, r.transformTemplate);
  }
  scrapeMotionValuesFromProps(t, n, r) {
    return lw(t, n, r);
  }
}
class pX extends gD {
  constructor() {
    super(...arguments),
      (this.type = "svg"),
      (this.isSVGTag = !1),
      (this.measureInstanceViewportBox = Ae);
  }
  getBaseTargetFromProps(t, n) {
    return t[n];
  }
  readValueFromInstance(t, n) {
    if (wi.has(n)) {
      const r = _w(n);
      return (r && r.default) || 0;
    }
    return (n = rI.has(n) ? n : J0(n)), t.getAttribute(n);
  }
  scrapeMotionValuesFromProps(t, n, r) {
    return sI(t, n, r);
  }
  build(t, n, r) {
    sw(t, n, this.isSVGTag, r.transformTemplate);
  }
  renderInstance(t, n, r, i) {
    iI(t, n, r, i);
  }
  mount(t) {
    (this.isSVGTag = uw(t.tagName)), super.mount(t);
  }
}
const mX = (e, t) => (tw(e) ? new pX(t) : new hX(t, { allowProjection: e !== _.Fragment })),
  gX = $W({ ...VK, ...oX, ...KY, ...sX }, mX),
  vD = nW(gX);
function Cw(e) {
  const t = G0(() => xo(e)),
    { isStatic: n } = _.useContext(_c);
  if (n) {
    const [, r] = _.useState(e);
    _.useEffect(() => t.on("change", r), []);
  }
  return t;
}
function yD(e, t) {
  const n = Cw(t()),
    r = () => n.set(t());
  return (
    r(),
    Y0(() => {
      const i = () => fe.preRender(r, !1, !0),
        o = e.map((s) => s.on("change", i));
      return () => {
        o.forEach((s) => s()), Xn(r);
      };
    }),
    n
  );
}
function pk(e) {
  return typeof e == "number" ? e : parseFloat(e);
}
function vX(e, t = {}) {
  const { isStatic: n } = _.useContext(_c),
    r = _.useRef(null),
    i = Cw(Be(e) ? pk(e.get()) : e),
    o = _.useRef(i.get()),
    s = _.useRef(() => {}),
    a = () => {
      const l = r.current;
      l && l.time === 0 && l.sample($e.delta),
        u(),
        (r.current = dK({
          keyframes: [i.get(), o.current],
          velocity: i.getVelocity(),
          type: "spring",
          restDelta: 0.001,
          restSpeed: 0.01,
          ...t,
          onUpdate: s.current,
        }));
    },
    u = () => {
      r.current && r.current.stop();
    };
  return (
    _.useInsertionEffect(
      () =>
        i.attach(
          (l, c) => (n ? c(l) : ((o.current = l), (s.current = c), fe.update(a), i.get())),
          u,
        ),
      [JSON.stringify(t)],
    ),
    Y0(() => {
      if (Be(e)) return e.on("change", (l) => i.set(pk(l)));
    }, [i]),
    i
  );
}
const yX = (e) => e && typeof e == "object" && e.mix,
  wX = (e) => (yX(e) ? e.mix : void 0);
function xX(...e) {
  const t = !Array.isArray(e[0]),
    n = t ? 0 : -1,
    r = e[0 + n],
    i = e[1 + n],
    o = e[2 + n],
    s = e[3 + n],
    a = WI(i, o, { mixer: wX(o[0]), ...s });
  return t ? a(r) : a;
}
function _X(e) {
  (Es.current = []), e();
  const t = yD(Es.current, e);
  return (Es.current = void 0), t;
}
function mk(e, t, n, r) {
  if (typeof e == "function") return _X(e);
  const i = typeof t == "function" ? t : xX(t, n, r);
  return Array.isArray(e) ? gk(e, i) : gk([e], ([o]) => i(o));
}
function gk(e, t) {
  const n = G0(() => []);
  return yD(e, () => {
    n.length = 0;
    const r = e.length;
    for (let i = 0; i < r; i++) n[i] = e[i].get();
    return t(n);
  });
}
const bX = I2(
    "flex h-full w-max items-end gap-2 rounded-lg p-2 transition-all duration-300 ease-out",
  ),
  wD = L.forwardRef(({ className: e, children: t, ...n }, r) => {
    const i = Cw(1 / 0);
    return R.jsx(vD.div, {
      ref: r,
      onMouseMove: (o) => i.set(o.pageX),
      onMouseLeave: () => i.set(1 / 0),
      ...n,
      className: ve(bX({ className: e }), "z-50"),
      children: L.Children.map(t, (o) => L.cloneElement(o, { mouseX: i })),
    });
  });
wD.displayName = "Dock";
const Iu = ({ mouseX: e, className: t, children: n, ...r }) => {
  const i = _.useRef(null),
    o = mk(e, (u) => {
      var c;
      const l = ((c = i.current) == null ? void 0 : c.getBoundingClientRect()) ?? {
        x: 0,
        width: 0,
      };
      return u - l.x - l.width / 2;
    }),
    s = mk(o, [-150, 0, 150], [40, 80, 40]),
    a = vX(s, { mass: 0.1, stiffness: 150, damping: 12 });
  return R.jsx(vD.div, {
    ref: i,
    style: { width: a },
    className: ve(
      "flex aspect-square items-center justify-center rounded-full bg-neutral-100/50 dark:bg-neutral-800/50",
      t,
    ),
    ...r,
    children: n,
  });
};
Iu.displayName = "DockIcon";
const xD = L.forwardRef(
  (
    {
      shimmerColor: e = "#ffffff",
      shimmerSize: t = "0.1em",
      shimmerDuration: n = "1.5s",
      borderRadius: r = "100px",
      background: i = "rgba(0, 0, 0, 1)",
      className: o,
      children: s,
      ...a
    },
    u,
  ) =>
    R.jsxs("button", {
      style: {
        "--shimmer-color": e,
        "--shimmer-size": t,
        "--shimmer-duration": n,
        "--background": i,
        borderRadius: r,
      },
      className: ve(
        "group relative z-0 flex cursor-pointer items-center justify-center overflow-hidden whitespace-nowrap border border-white/10 px-6 py-3 text-white [background:var(--background)] [border-radius:var(--border-radius)]",
        "transform-gpu transition-transform duration-300 ease-in-out hover:scale-105",
        o,
      ),
      ref: u,
      ...a,
      children: [
        R.jsx("div", {
          className: "absolute inset-0 z-0 overflow-hidden rounded-[inherit]",
          children: R.jsx("div", {
            className: ve(
              "absolute inset-0 z-0 h-full w-full animate-[shimmer_var(--shimmer-duration)_infinite] bg-gradient-to-r from-transparent via-transparent to-[var(--shimmer-color)] opacity-0 transition-opacity duration-500 group-hover:opacity-100",
              "[--shimmer-angle:-45deg]",
            ),
          }),
        }),
        R.jsx("div", { className: "relative z-10", children: s }),
      ],
    }),
);
xD.displayName = "ShimmerButton";
function SX() {
  QF();
  const e = Bl((a) => a.machines),
    [t, n] = _.useState(null),
    [r, i] = _.useState(!1);
  _.useEffect(() => {
    const a = Object.keys(e);
    (!t || !e[t]) && a.length > 0 && n(a[0]);
  }, [e, t]),
    _.useEffect(() => {
      const a = document.documentElement.classList.contains("dark");
      i(a);
    }, []);
  const o = () => {
      const a = !document.documentElement.classList.contains("dark");
      i(a),
        localStorage.setItem("theme", a ? "dark" : "light"),
        document.documentElement.classList.toggle("dark", a);
    },
    s = t ? e[t] : null;
  return R.jsxs("div", {
    className: "flex h-screen w-full flex-col bg-background font-sans text-foreground",
    children: [
      R.jsx(EX, { onToggleTheme: o, isDark: r }),
      R.jsxs("div", {
        className: "flex flex-1 overflow-hidden",
        children: [
          R.jsx(CX, { machines: e, selectedMachineId: t, onSelectMachine: n }),
          R.jsx("main", {
            className: "flex-1 flex flex-col overflow-hidden",
            children: s ? R.jsx(TX, { machine: s }, s.id) : R.jsx(AX, {}),
          }),
        ],
      }),
    ],
  });
}
const EX = ({ onToggleTheme: e, isDark: t }) =>
    R.jsxs("header", {
      className: "flex h-14 items-center justify-between border-b bg-card px-4 lg:px-6",
      children: [
        R.jsxs("div", {
          className: "flex items-center gap-2 font-bold",
          children: [
            R.jsx(CH, { className: "h-6 w-6 text-primary" }),
            R.jsx("span", { children: "XState Inspector" }),
          ],
        }),
        R.jsxs(q0, {
          variant: "ghost",
          size: "icon",
          onClick: e,
          children: [
            R.jsx(DH, {
              className: "h-5 w-5 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0",
            }),
            R.jsx(RH, {
              className:
                "absolute h-5 w-5 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100",
            }),
            R.jsx("span", { className: "sr-only", children: "Toggle theme" }),
          ],
        }),
      ],
    }),
  CX = ({ machines: e, selectedMachineId: t, onSelectMachine: n }) =>
    R.jsxs("aside", {
      className: "hidden w-72 flex-col border-r bg-card p-4 sm:flex",
      children: [
        R.jsx("h2", {
          className: "text-base font-semibold tracking-tight",
          children: "Live Machines",
        }),
        R.jsx("nav", {
          className: "mt-4 flex flex-col gap-1",
          children: Object.values(e).map((r) =>
            R.jsx(
              "div",
              {
                children: R.jsx(q0, {
                  variant: t === r.id ? "secondary" : "ghost",
                  className: "w-full justify-start",
                  onClick: () => n(r.id),
                  children: r.id,
                }),
              },
              r.id,
            ),
          ),
        }),
      ],
    }),
  TX = ({ machine: e }) =>
    R.jsxs("div", {
      className: "grid h-full grid-cols-1 lg:grid-cols-3 gap-4 p-4",
      children: [
        R.jsxs("div", {
          className: "lg:col-span-2 flex flex-col gap-4 relative",
          children: [
            R.jsxs(va, {
              className: "flex-1 flex flex-col",
              children: [
                R.jsxs(ya, {
                  children: [
                    R.jsx(wa, { children: e.id }),
                    R.jsxs("p", {
                      className: "text-sm text-muted-foreground",
                      children: [
                        "Current State:",
                        " ",
                        R.jsx("span", {
                          className: "font-mono text-primary",
                          children: e.currentStateIds.join(", "),
                        }),
                      ],
                    }),
                  ],
                }),
                R.jsx(xa, {
                  className: "flex-1 relative",
                  children: R.jsx(HH, { machine: e, activeStateIds: e.currentStateIds }),
                }),
              ],
            }),
            R.jsx(RX, { machineId: e.id }),
          ],
        }),
        R.jsx("div", { className: "flex flex-col", children: R.jsx(kX, { machine: e }) }),
      ],
    }),
  kX = ({ machine: e }) =>
    R.jsxs(R9, {
      defaultValue: "events",
      className: "flex-1 flex flex-col overflow-hidden",
      children: [
        R.jsxs(eM, {
          className: "grid w-full grid-cols-3",
          children: [
            R.jsxs(Tu, {
              value: "events",
              children: [R.jsx(kH, { className: "w-4 h-4 mr-2" }), "Event Log"],
            }),
            R.jsxs(Tu, {
              value: "context",
              children: [R.jsx(IH, { className: "w-4 h-4 mr-2" }), "Context"],
            }),
            R.jsxs(Tu, {
              value: "json",
              children: [R.jsx(TH, { className: "w-4 h-4 mr-2" }), "Definition"],
            }),
          ],
        }),
        R.jsx(ku, {
          value: "events",
          className: "flex-1 overflow-y-auto mt-0",
          children: R.jsx("div", {
            className: "font-mono text-xs space-y-2 p-4",
            children: e.logs
              .slice()
              .reverse()
              .map((t, n) =>
                R.jsxs(
                  "div",
                  {
                    className: "p-2 rounded bg-muted",
                    children: [
                      R.jsx("p", { className: "font-bold text-primary", children: t.type }),
                      R.jsx("pre", {
                        className:
                          "text-muted-foreground whitespace-pre-wrap break-all text-[11px]",
                        children: JSON.stringify(t.payload, null, 2),
                      }),
                    ],
                  },
                  n,
                ),
              ),
          }),
        }),
        R.jsx(ku, {
          value: "context",
          className: "flex-1 overflow-y-auto mt-0",
          children: R.jsx("pre", {
            className: "font-mono text-xs p-4",
            children: JSON.stringify(e.context, null, 2),
          }),
        }),
        R.jsx(ku, {
          value: "json",
          className: "flex-1 overflow-y-auto mt-0",
          children: R.jsx("pre", {
            className: "font-mono text-xs p-4",
            children: JSON.stringify(e.definition, null, 2),
          }),
        }),
      ],
    }),
  RX = ({ machineId: e }) => {
    const [t, n] = _.useState(!1),
      r = Bl((i) => i.sendCommand);
    return R.jsxs(R.Fragment, {
      children: [
        R.jsx("div", {
          className: "absolute bottom-4 left-1/2 -translate-x-1/2",
          children: R.jsxs(wD, {
            children: [
              R.jsx(Iu, {
                onClick: () => r("resume", { machine_id: e }),
                children: R.jsx(AH, { className: "h-4 w-4" }),
              }),
              R.jsx(Iu, {
                onClick: () => r("pause", { machine_id: e }),
                children: R.jsx(PH, { className: "h-4 w-4" }),
              }),
              R.jsx(Iu, { onClick: () => n(!0), children: R.jsx(MH, { className: "h-4 w-4" }) }),
            ],
          }),
        }),
        R.jsx(PX, { open: t, onOpenChange: n, machineId: e }),
      ],
    });
  },
  PX = ({ open: e, onOpenChange: t, machineId: n }) => {
    const [r, i] = _.useState(""),
      [o, s] = _.useState(""),
      a = Bl((l) => l.sendCommand),
      u = () => {
        if (!r) return;
        let l = {};
        try {
          o.trim() && (l = JSON.parse(o));
        } catch {
          alert("Invalid JSON in payload.");
          return;
        }
        a("send_event", { machine_id: n, event: { type: r, payload: l } }), t(!1), i(""), s("");
      };
    return R.jsx(HG, {
      open: e,
      onOpenChange: t,
      children: R.jsxs(LM, {
        children: [
          R.jsx(FM, { children: R.jsxs(VM, { children: ["Send Event to ", n] }) }),
          R.jsxs("div", {
            className: "grid gap-4 py-4",
            children: [
              R.jsx(qM, {
                placeholder: "Event Type (e.g., ENABLE)",
                value: r,
                onChange: (l) => i(l.target.value),
              }),
              R.jsx($M, {
                placeholder: 'Payload (JSON), e.g., {"value": 42}',
                value: o,
                onChange: (l) => s(l.target.value),
              }),
            ],
          }),
          R.jsx(jM, {
            children: R.jsx(xD, {
              className: "w-full",
              onClick: u,
              children: R.jsx("span", {
                className:
                  "whitespace-pre-wrap text-center text-sm font-medium leading-none tracking-tight text-white dark:from-white dark:to-slate-900/10 lg:text-lg",
                children: "Send Event",
              }),
            }),
          }),
        ],
      }),
    });
  },
  AX = () =>
    R.jsx("div", {
      className: "flex h-full items-center justify-center m-4",
      children: R.jsxs(va, {
        className: "w-full max-w-md",
        children: [
          R.jsx(ya, {
            children: R.jsx(wa, { className: "text-2xl", children: "No Live Machines Detected" }),
          }),
          R.jsx(xa, {
            children: R.jsx("p", {
              className: "text-muted-foreground",
              children: "Run a Python script with the InspectorPlugin to begin debugging.",
            }),
          }),
        ],
      }),
    });
Ag.createRoot(document.getElementById("root")).render(
  R.jsx(L.StrictMode, { children: R.jsx(SX, {}) }),
);
