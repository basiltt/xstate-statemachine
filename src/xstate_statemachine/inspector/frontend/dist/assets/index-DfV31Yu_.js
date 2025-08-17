function SC(e, t) {
  for (var n = 0; n < t.length; n++) {
    const r = t[n];
    if (typeof r != "string" && !Array.isArray(r)) {
      for (const o in r)
        if (o !== "default" && !(o in e)) {
          const i = Object.getOwnPropertyDescriptor(r, o);
          i && Object.defineProperty(e, o, i.get ? i : { enumerable: !0, get: () => r[o] });
        }
    }
  }
  return Object.freeze(Object.defineProperty(e, Symbol.toStringTag, { value: "Module" }));
}
(function () {
  const t = document.createElement("link").relList;
  if (t && t.supports && t.supports("modulepreload")) return;
  for (const o of document.querySelectorAll('link[rel="modulepreload"]')) r(o);
  new MutationObserver((o) => {
    for (const i of o)
      if (i.type === "childList")
        for (const s of i.addedNodes) s.tagName === "LINK" && s.rel === "modulepreload" && r(s);
  }).observe(document, { childList: !0, subtree: !0 });
  function n(o) {
    const i = {};
    return (
      o.integrity && (i.integrity = o.integrity),
      o.referrerPolicy && (i.referrerPolicy = o.referrerPolicy),
      o.crossOrigin === "use-credentials"
        ? (i.credentials = "include")
        : o.crossOrigin === "anonymous"
          ? (i.credentials = "omit")
          : (i.credentials = "same-origin"),
      i
    );
  }
  function r(o) {
    if (o.ep) return;
    o.ep = !0;
    const i = n(o);
    fetch(o.href, i);
  }
})();
function ld(e) {
  return e && e.__esModule && Object.prototype.hasOwnProperty.call(e, "default") ? e.default : e;
}
var Qy = { exports: {} },
  $l = {},
  qy = { exports: {} },
  ee = {};
/**
 * @license React
 * react.production.min.js
 *
 * Copyright (c) Facebook, Inc. and its affiliates.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */ var ks = Symbol.for("react.element"),
  EC = Symbol.for("react.portal"),
  CC = Symbol.for("react.fragment"),
  bC = Symbol.for("react.strict_mode"),
  kC = Symbol.for("react.profiler"),
  _C = Symbol.for("react.provider"),
  TC = Symbol.for("react.context"),
  NC = Symbol.for("react.forward_ref"),
  PC = Symbol.for("react.suspense"),
  MC = Symbol.for("react.memo"),
  AC = Symbol.for("react.lazy"),
  dp = Symbol.iterator;
function RC(e) {
  return e === null || typeof e != "object"
    ? null
    : ((e = (dp && e[dp]) || e["@@iterator"]), typeof e == "function" ? e : null);
}
var Jy = {
    isMounted: function () {
      return !1;
    },
    enqueueForceUpdate: function () {},
    enqueueReplaceState: function () {},
    enqueueSetState: function () {},
  },
  e0 = Object.assign,
  t0 = {};
function Ko(e, t, n) {
  (this.props = e), (this.context = t), (this.refs = t0), (this.updater = n || Jy);
}
Ko.prototype.isReactComponent = {};
Ko.prototype.setState = function (e, t) {
  if (typeof e != "object" && typeof e != "function" && e != null)
    throw Error(
      "setState(...): takes an object of state variables to update or a function which returns an object of state variables.",
    );
  this.updater.enqueueSetState(this, e, t, "setState");
};
Ko.prototype.forceUpdate = function (e) {
  this.updater.enqueueForceUpdate(this, e, "forceUpdate");
};
function n0() {}
n0.prototype = Ko.prototype;
function ud(e, t, n) {
  (this.props = e), (this.context = t), (this.refs = t0), (this.updater = n || Jy);
}
var cd = (ud.prototype = new n0());
cd.constructor = ud;
e0(cd, Ko.prototype);
cd.isPureReactComponent = !0;
var hp = Array.isArray,
  r0 = Object.prototype.hasOwnProperty,
  fd = { current: null },
  o0 = { key: !0, ref: !0, __self: !0, __source: !0 };
function i0(e, t, n) {
  var r,
    o = {},
    i = null,
    s = null;
  if (t != null)
    for (r in (t.ref !== void 0 && (s = t.ref), t.key !== void 0 && (i = "" + t.key), t))
      r0.call(t, r) && !o0.hasOwnProperty(r) && (o[r] = t[r]);
  var a = arguments.length - 2;
  if (a === 1) o.children = n;
  else if (1 < a) {
    for (var l = Array(a), u = 0; u < a; u++) l[u] = arguments[u + 2];
    o.children = l;
  }
  if (e && e.defaultProps) for (r in ((a = e.defaultProps), a)) o[r] === void 0 && (o[r] = a[r]);
  return { $$typeof: ks, type: e, key: i, ref: s, props: o, _owner: fd.current };
}
function DC(e, t) {
  return { $$typeof: ks, type: e.type, key: t, ref: e.ref, props: e.props, _owner: e._owner };
}
function dd(e) {
  return typeof e == "object" && e !== null && e.$$typeof === ks;
}
function IC(e) {
  var t = { "=": "=0", ":": "=2" };
  return (
    "$" +
    e.replace(/[=:]/g, function (n) {
      return t[n];
    })
  );
}
var pp = /\/+/g;
function ku(e, t) {
  return typeof e == "object" && e !== null && e.key != null ? IC("" + e.key) : t.toString(36);
}
function ka(e, t, n, r, o) {
  var i = typeof e;
  (i === "undefined" || i === "boolean") && (e = null);
  var s = !1;
  if (e === null) s = !0;
  else
    switch (i) {
      case "string":
      case "number":
        s = !0;
        break;
      case "object":
        switch (e.$$typeof) {
          case ks:
          case EC:
            s = !0;
        }
    }
  if (s)
    return (
      (s = e),
      (o = o(s)),
      (e = r === "" ? "." + ku(s, 0) : r),
      hp(o)
        ? ((n = ""),
          e != null && (n = e.replace(pp, "$&/") + "/"),
          ka(o, t, n, "", function (u) {
            return u;
          }))
        : o != null &&
          (dd(o) &&
            (o = DC(
              o,
              n +
                (!o.key || (s && s.key === o.key) ? "" : ("" + o.key).replace(pp, "$&/") + "/") +
                e,
            )),
          t.push(o)),
      1
    );
  if (((s = 0), (r = r === "" ? "." : r + ":"), hp(e)))
    for (var a = 0; a < e.length; a++) {
      i = e[a];
      var l = r + ku(i, a);
      s += ka(i, t, n, l, o);
    }
  else if (((l = RC(e)), typeof l == "function"))
    for (e = l.call(e), a = 0; !(i = e.next()).done; )
      (i = i.value), (l = r + ku(i, a++)), (s += ka(i, t, n, l, o));
  else if (i === "object")
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
function Bs(e, t, n) {
  if (e == null) return e;
  var r = [],
    o = 0;
  return (
    ka(e, r, "", "", function (i) {
      return t.call(n, i, o++);
    }),
    r
  );
}
function LC(e) {
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
var qe = { current: null },
  _a = { transition: null },
  VC = { ReactCurrentDispatcher: qe, ReactCurrentBatchConfig: _a, ReactCurrentOwner: fd };
function s0() {
  throw Error("act(...) is not supported in production builds of React.");
}
ee.Children = {
  map: Bs,
  forEach: function (e, t, n) {
    Bs(
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
      Bs(e, function () {
        t++;
      }),
      t
    );
  },
  toArray: function (e) {
    return (
      Bs(e, function (t) {
        return t;
      }) || []
    );
  },
  only: function (e) {
    if (!dd(e))
      throw Error("React.Children.only expected to receive a single React element child.");
    return e;
  },
};
ee.Component = Ko;
ee.Fragment = CC;
ee.Profiler = kC;
ee.PureComponent = ud;
ee.StrictMode = bC;
ee.Suspense = PC;
ee.__SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED = VC;
ee.act = s0;
ee.cloneElement = function (e, t, n) {
  if (e == null)
    throw Error(
      "React.cloneElement(...): The argument must be a React element, but you passed " + e + ".",
    );
  var r = e0({}, e.props),
    o = e.key,
    i = e.ref,
    s = e._owner;
  if (t != null) {
    if (
      (t.ref !== void 0 && ((i = t.ref), (s = fd.current)),
      t.key !== void 0 && (o = "" + t.key),
      e.type && e.type.defaultProps)
    )
      var a = e.type.defaultProps;
    for (l in t)
      r0.call(t, l) &&
        !o0.hasOwnProperty(l) &&
        (r[l] = t[l] === void 0 && a !== void 0 ? a[l] : t[l]);
  }
  var l = arguments.length - 2;
  if (l === 1) r.children = n;
  else if (1 < l) {
    a = Array(l);
    for (var u = 0; u < l; u++) a[u] = arguments[u + 2];
    r.children = a;
  }
  return { $$typeof: ks, type: e.type, key: o, ref: i, props: r, _owner: s };
};
ee.createContext = function (e) {
  return (
    (e = {
      $$typeof: TC,
      _currentValue: e,
      _currentValue2: e,
      _threadCount: 0,
      Provider: null,
      Consumer: null,
      _defaultValue: null,
      _globalName: null,
    }),
    (e.Provider = { $$typeof: _C, _context: e }),
    (e.Consumer = e)
  );
};
ee.createElement = i0;
ee.createFactory = function (e) {
  var t = i0.bind(null, e);
  return (t.type = e), t;
};
ee.createRef = function () {
  return { current: null };
};
ee.forwardRef = function (e) {
  return { $$typeof: NC, render: e };
};
ee.isValidElement = dd;
ee.lazy = function (e) {
  return { $$typeof: AC, _payload: { _status: -1, _result: e }, _init: LC };
};
ee.memo = function (e, t) {
  return { $$typeof: MC, type: e, compare: t === void 0 ? null : t };
};
ee.startTransition = function (e) {
  var t = _a.transition;
  _a.transition = {};
  try {
    e();
  } finally {
    _a.transition = t;
  }
};
ee.unstable_act = s0;
ee.useCallback = function (e, t) {
  return qe.current.useCallback(e, t);
};
ee.useContext = function (e) {
  return qe.current.useContext(e);
};
ee.useDebugValue = function () {};
ee.useDeferredValue = function (e) {
  return qe.current.useDeferredValue(e);
};
ee.useEffect = function (e, t) {
  return qe.current.useEffect(e, t);
};
ee.useId = function () {
  return qe.current.useId();
};
ee.useImperativeHandle = function (e, t, n) {
  return qe.current.useImperativeHandle(e, t, n);
};
ee.useInsertionEffect = function (e, t) {
  return qe.current.useInsertionEffect(e, t);
};
ee.useLayoutEffect = function (e, t) {
  return qe.current.useLayoutEffect(e, t);
};
ee.useMemo = function (e, t) {
  return qe.current.useMemo(e, t);
};
ee.useReducer = function (e, t, n) {
  return qe.current.useReducer(e, t, n);
};
ee.useRef = function (e) {
  return qe.current.useRef(e);
};
ee.useState = function (e) {
  return qe.current.useState(e);
};
ee.useSyncExternalStore = function (e, t, n) {
  return qe.current.useSyncExternalStore(e, t, n);
};
ee.useTransition = function () {
  return qe.current.useTransition();
};
ee.version = "18.3.1";
qy.exports = ee;
var v = qy.exports;
const L = ld(v),
  a0 = SC({ __proto__: null, default: L }, [v]);
/**
 * @license React
 * react-jsx-runtime.production.min.js
 *
 * Copyright (c) Facebook, Inc. and its affiliates.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */ var OC = v,
  FC = Symbol.for("react.element"),
  zC = Symbol.for("react.fragment"),
  $C = Object.prototype.hasOwnProperty,
  jC = OC.__SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED.ReactCurrentOwner,
  BC = { key: !0, ref: !0, __self: !0, __source: !0 };
function l0(e, t, n) {
  var r,
    o = {},
    i = null,
    s = null;
  n !== void 0 && (i = "" + n),
    t.key !== void 0 && (i = "" + t.key),
    t.ref !== void 0 && (s = t.ref);
  for (r in t) $C.call(t, r) && !BC.hasOwnProperty(r) && (o[r] = t[r]);
  if (e && e.defaultProps) for (r in ((t = e.defaultProps), t)) o[r] === void 0 && (o[r] = t[r]);
  return { $$typeof: FC, type: e, key: i, ref: s, props: o, _owner: jC.current };
}
$l.Fragment = zC;
$l.jsx = l0;
$l.jsxs = l0;
Qy.exports = $l;
var N = Qy.exports,
  Mc = {},
  u0 = { exports: {} },
  gt = {},
  c0 = { exports: {} },
  f0 = {};
/**
 * @license React
 * scheduler.production.min.js
 *
 * Copyright (c) Facebook, Inc. and its affiliates.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */ (function (e) {
  function t(P, T) {
    var D = P.length;
    P.push(T);
    e: for (; 0 < D; ) {
      var O = (D - 1) >>> 1,
        $ = P[O];
      if (0 < o($, T)) (P[O] = T), (P[D] = $), (D = O);
      else break e;
    }
  }
  function n(P) {
    return P.length === 0 ? null : P[0];
  }
  function r(P) {
    if (P.length === 0) return null;
    var T = P[0],
      D = P.pop();
    if (D !== T) {
      P[0] = D;
      e: for (var O = 0, $ = P.length, H = $ >>> 1; O < H; ) {
        var U = 2 * (O + 1) - 1,
          K = P[U],
          Z = U + 1,
          q = P[Z];
        if (0 > o(K, D))
          Z < $ && 0 > o(q, K)
            ? ((P[O] = q), (P[Z] = D), (O = Z))
            : ((P[O] = K), (P[U] = D), (O = U));
        else if (Z < $ && 0 > o(q, D)) (P[O] = q), (P[Z] = D), (O = Z);
        else break e;
      }
    }
    return T;
  }
  function o(P, T) {
    var D = P.sortIndex - T.sortIndex;
    return D !== 0 ? D : P.id - T.id;
  }
  if (typeof performance == "object" && typeof performance.now == "function") {
    var i = performance;
    e.unstable_now = function () {
      return i.now();
    };
  } else {
    var s = Date,
      a = s.now();
    e.unstable_now = function () {
      return s.now() - a;
    };
  }
  var l = [],
    u = [],
    c = 1,
    f = null,
    d = 3,
    p = !1,
    y = !1,
    m = !1,
    w = typeof setTimeout == "function" ? setTimeout : null,
    h = typeof clearTimeout == "function" ? clearTimeout : null,
    g = typeof setImmediate < "u" ? setImmediate : null;
  typeof navigator < "u" &&
    navigator.scheduling !== void 0 &&
    navigator.scheduling.isInputPending !== void 0 &&
    navigator.scheduling.isInputPending.bind(navigator.scheduling);
  function x(P) {
    for (var T = n(u); T !== null; ) {
      if (T.callback === null) r(u);
      else if (T.startTime <= P) r(u), (T.sortIndex = T.expirationTime), t(l, T);
      else break;
      T = n(u);
    }
  }
  function S(P) {
    if (((m = !1), x(P), !y))
      if (n(l) !== null) (y = !0), M(E);
      else {
        var T = n(u);
        T !== null && V(S, T.startTime - P);
      }
  }
  function E(P, T) {
    (y = !1), m && ((m = !1), h(_), (_ = -1)), (p = !0);
    var D = d;
    try {
      for (x(T), f = n(l); f !== null && (!(f.expirationTime > T) || (P && !z())); ) {
        var O = f.callback;
        if (typeof O == "function") {
          (f.callback = null), (d = f.priorityLevel);
          var $ = O(f.expirationTime <= T);
          (T = e.unstable_now()),
            typeof $ == "function" ? (f.callback = $) : f === n(l) && r(l),
            x(T);
        } else r(l);
        f = n(l);
      }
      if (f !== null) var H = !0;
      else {
        var U = n(u);
        U !== null && V(S, U.startTime - T), (H = !1);
      }
      return H;
    } finally {
      (f = null), (d = D), (p = !1);
    }
  }
  var C = !1,
    b = null,
    _ = -1,
    A = 5,
    R = -1;
  function z() {
    return !(e.unstable_now() - R < A);
  }
  function F() {
    if (b !== null) {
      var P = e.unstable_now();
      R = P;
      var T = !0;
      try {
        T = b(!0, P);
      } finally {
        T ? j() : ((C = !1), (b = null));
      }
    } else C = !1;
  }
  var j;
  if (typeof g == "function")
    j = function () {
      g(F);
    };
  else if (typeof MessageChannel < "u") {
    var k = new MessageChannel(),
      I = k.port2;
    (k.port1.onmessage = F),
      (j = function () {
        I.postMessage(null);
      });
  } else
    j = function () {
      w(F, 0);
    };
  function M(P) {
    (b = P), C || ((C = !0), j());
  }
  function V(P, T) {
    _ = w(function () {
      P(e.unstable_now());
    }, T);
  }
  (e.unstable_IdlePriority = 5),
    (e.unstable_ImmediatePriority = 1),
    (e.unstable_LowPriority = 4),
    (e.unstable_NormalPriority = 3),
    (e.unstable_Profiling = null),
    (e.unstable_UserBlockingPriority = 2),
    (e.unstable_cancelCallback = function (P) {
      P.callback = null;
    }),
    (e.unstable_continueExecution = function () {
      y || p || ((y = !0), M(E));
    }),
    (e.unstable_forceFrameRate = function (P) {
      0 > P || 125 < P
        ? console.error(
            "forceFrameRate takes a positive int between 0 and 125, forcing frame rates higher than 125 fps is not supported",
          )
        : (A = 0 < P ? Math.floor(1e3 / P) : 5);
    }),
    (e.unstable_getCurrentPriorityLevel = function () {
      return d;
    }),
    (e.unstable_getFirstCallbackNode = function () {
      return n(l);
    }),
    (e.unstable_next = function (P) {
      switch (d) {
        case 1:
        case 2:
        case 3:
          var T = 3;
          break;
        default:
          T = d;
      }
      var D = d;
      d = T;
      try {
        return P();
      } finally {
        d = D;
      }
    }),
    (e.unstable_pauseExecution = function () {}),
    (e.unstable_requestPaint = function () {}),
    (e.unstable_runWithPriority = function (P, T) {
      switch (P) {
        case 1:
        case 2:
        case 3:
        case 4:
        case 5:
          break;
        default:
          P = 3;
      }
      var D = d;
      d = P;
      try {
        return T();
      } finally {
        d = D;
      }
    }),
    (e.unstable_scheduleCallback = function (P, T, D) {
      var O = e.unstable_now();
      switch (
        (typeof D == "object" && D !== null
          ? ((D = D.delay), (D = typeof D == "number" && 0 < D ? O + D : O))
          : (D = O),
        P)
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
        (P = {
          id: c++,
          callback: T,
          priorityLevel: P,
          startTime: D,
          expirationTime: $,
          sortIndex: -1,
        }),
        D > O
          ? ((P.sortIndex = D),
            t(u, P),
            n(l) === null && P === n(u) && (m ? (h(_), (_ = -1)) : (m = !0), V(S, D - O)))
          : ((P.sortIndex = $), t(l, P), y || p || ((y = !0), M(E))),
        P
      );
    }),
    (e.unstable_shouldYield = z),
    (e.unstable_wrapCallback = function (P) {
      var T = d;
      return function () {
        var D = d;
        d = T;
        try {
          return P.apply(this, arguments);
        } finally {
          d = D;
        }
      };
    });
})(f0);
c0.exports = f0;
var UC = c0.exports;
/**
 * @license React
 * react-dom.production.min.js
 *
 * Copyright (c) Facebook, Inc. and its affiliates.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */ var HC = v,
  ht = UC;
function B(e) {
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
var d0 = new Set(),
  Wi = {};
function Or(e, t) {
  Ao(e, t), Ao(e + "Capture", t);
}
function Ao(e, t) {
  for (Wi[e] = t, e = 0; e < t.length; e++) d0.add(t[e]);
}
var xn = !(
    typeof window > "u" ||
    typeof window.document > "u" ||
    typeof window.document.createElement > "u"
  ),
  Ac = Object.prototype.hasOwnProperty,
  WC =
    /^[:A-Z_a-z\u00C0-\u00D6\u00D8-\u00F6\u00F8-\u02FF\u0370-\u037D\u037F-\u1FFF\u200C-\u200D\u2070-\u218F\u2C00-\u2FEF\u3001-\uD7FF\uF900-\uFDCF\uFDF0-\uFFFD][:A-Z_a-z\u00C0-\u00D6\u00D8-\u00F6\u00F8-\u02FF\u0370-\u037D\u037F-\u1FFF\u200C-\u200D\u2070-\u218F\u2C00-\u2FEF\u3001-\uD7FF\uF900-\uFDCF\uFDF0-\uFFFD\-.0-9\u00B7\u0300-\u036F\u203F-\u2040]*$/,
  mp = {},
  gp = {};
function GC(e) {
  return Ac.call(gp, e) ? !0 : Ac.call(mp, e) ? !1 : WC.test(e) ? (gp[e] = !0) : ((mp[e] = !0), !1);
}
function KC(e, t, n, r) {
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
function YC(e, t, n, r) {
  if (t === null || typeof t > "u" || KC(e, t, n, r)) return !0;
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
function Je(e, t, n, r, o, i, s) {
  (this.acceptsBooleans = t === 2 || t === 3 || t === 4),
    (this.attributeName = r),
    (this.attributeNamespace = o),
    (this.mustUseProperty = n),
    (this.propertyName = e),
    (this.type = t),
    (this.sanitizeURL = i),
    (this.removeEmptyString = s);
}
var ze = {};
"children dangerouslySetInnerHTML defaultValue defaultChecked innerHTML suppressContentEditableWarning suppressHydrationWarning style"
  .split(" ")
  .forEach(function (e) {
    ze[e] = new Je(e, 0, !1, e, null, !1, !1);
  });
[
  ["acceptCharset", "accept-charset"],
  ["className", "class"],
  ["htmlFor", "for"],
  ["httpEquiv", "http-equiv"],
].forEach(function (e) {
  var t = e[0];
  ze[t] = new Je(t, 1, !1, e[1], null, !1, !1);
});
["contentEditable", "draggable", "spellCheck", "value"].forEach(function (e) {
  ze[e] = new Je(e, 2, !1, e.toLowerCase(), null, !1, !1);
});
["autoReverse", "externalResourcesRequired", "focusable", "preserveAlpha"].forEach(function (e) {
  ze[e] = new Je(e, 2, !1, e, null, !1, !1);
});
"allowFullScreen async autoFocus autoPlay controls default defer disabled disablePictureInPicture disableRemotePlayback formNoValidate hidden loop noModule noValidate open playsInline readOnly required reversed scoped seamless itemScope"
  .split(" ")
  .forEach(function (e) {
    ze[e] = new Je(e, 3, !1, e.toLowerCase(), null, !1, !1);
  });
["checked", "multiple", "muted", "selected"].forEach(function (e) {
  ze[e] = new Je(e, 3, !0, e, null, !1, !1);
});
["capture", "download"].forEach(function (e) {
  ze[e] = new Je(e, 4, !1, e, null, !1, !1);
});
["cols", "rows", "size", "span"].forEach(function (e) {
  ze[e] = new Je(e, 6, !1, e, null, !1, !1);
});
["rowSpan", "start"].forEach(function (e) {
  ze[e] = new Je(e, 5, !1, e.toLowerCase(), null, !1, !1);
});
var hd = /[\-:]([a-z])/g;
function pd(e) {
  return e[1].toUpperCase();
}
"accent-height alignment-baseline arabic-form baseline-shift cap-height clip-path clip-rule color-interpolation color-interpolation-filters color-profile color-rendering dominant-baseline enable-background fill-opacity fill-rule flood-color flood-opacity font-family font-size font-size-adjust font-stretch font-style font-variant font-weight glyph-name glyph-orientation-horizontal glyph-orientation-vertical horiz-adv-x horiz-origin-x image-rendering letter-spacing lighting-color marker-end marker-mid marker-start overline-position overline-thickness paint-order panose-1 pointer-events rendering-intent shape-rendering stop-color stop-opacity strikethrough-position strikethrough-thickness stroke-dasharray stroke-dashoffset stroke-linecap stroke-linejoin stroke-miterlimit stroke-opacity stroke-width text-anchor text-decoration text-rendering underline-position underline-thickness unicode-bidi unicode-range units-per-em v-alphabetic v-hanging v-ideographic v-mathematical vector-effect vert-adv-y vert-origin-x vert-origin-y word-spacing writing-mode xmlns:xlink x-height"
  .split(" ")
  .forEach(function (e) {
    var t = e.replace(hd, pd);
    ze[t] = new Je(t, 1, !1, e, null, !1, !1);
  });
"xlink:actuate xlink:arcrole xlink:role xlink:show xlink:title xlink:type"
  .split(" ")
  .forEach(function (e) {
    var t = e.replace(hd, pd);
    ze[t] = new Je(t, 1, !1, e, "http://www.w3.org/1999/xlink", !1, !1);
  });
["xml:base", "xml:lang", "xml:space"].forEach(function (e) {
  var t = e.replace(hd, pd);
  ze[t] = new Je(t, 1, !1, e, "http://www.w3.org/XML/1998/namespace", !1, !1);
});
["tabIndex", "crossOrigin"].forEach(function (e) {
  ze[e] = new Je(e, 1, !1, e.toLowerCase(), null, !1, !1);
});
ze.xlinkHref = new Je("xlinkHref", 1, !1, "xlink:href", "http://www.w3.org/1999/xlink", !0, !1);
["src", "href", "action", "formAction"].forEach(function (e) {
  ze[e] = new Je(e, 1, !1, e.toLowerCase(), null, !0, !0);
});
function md(e, t, n, r) {
  var o = ze.hasOwnProperty(t) ? ze[t] : null;
  (o !== null
    ? o.type !== 0
    : r || !(2 < t.length) || (t[0] !== "o" && t[0] !== "O") || (t[1] !== "n" && t[1] !== "N")) &&
    (YC(t, n, o, r) && (n = null),
    r || o === null
      ? GC(t) && (n === null ? e.removeAttribute(t) : e.setAttribute(t, "" + n))
      : o.mustUseProperty
        ? (e[o.propertyName] = n === null ? (o.type === 3 ? !1 : "") : n)
        : ((t = o.attributeName),
          (r = o.attributeNamespace),
          n === null
            ? e.removeAttribute(t)
            : ((o = o.type),
              (n = o === 3 || (o === 4 && n === !0) ? "" : "" + n),
              r ? e.setAttributeNS(r, t, n) : e.setAttribute(t, n))));
}
var Tn = HC.__SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED,
  Us = Symbol.for("react.element"),
  Jr = Symbol.for("react.portal"),
  eo = Symbol.for("react.fragment"),
  gd = Symbol.for("react.strict_mode"),
  Rc = Symbol.for("react.profiler"),
  h0 = Symbol.for("react.provider"),
  p0 = Symbol.for("react.context"),
  yd = Symbol.for("react.forward_ref"),
  Dc = Symbol.for("react.suspense"),
  Ic = Symbol.for("react.suspense_list"),
  vd = Symbol.for("react.memo"),
  In = Symbol.for("react.lazy"),
  m0 = Symbol.for("react.offscreen"),
  yp = Symbol.iterator;
function oi(e) {
  return e === null || typeof e != "object"
    ? null
    : ((e = (yp && e[yp]) || e["@@iterator"]), typeof e == "function" ? e : null);
}
var ve = Object.assign,
  _u;
function wi(e) {
  if (_u === void 0)
    try {
      throw Error();
    } catch (n) {
      var t = n.stack.trim().match(/\n( *(at )?)/);
      _u = (t && t[1]) || "";
    }
  return (
    `
` +
    _u +
    e
  );
}
var Tu = !1;
function Nu(e, t) {
  if (!e || Tu) return "";
  Tu = !0;
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
        } catch (u) {
          var r = u;
        }
        Reflect.construct(e, [], t);
      } else {
        try {
          t.call();
        } catch (u) {
          r = u;
        }
        e.call(t.prototype);
      }
    else {
      try {
        throw Error();
      } catch (u) {
        r = u;
      }
      e();
    }
  } catch (u) {
    if (u && r && typeof u.stack == "string") {
      for (
        var o = u.stack.split(`
`),
          i = r.stack.split(`
`),
          s = o.length - 1,
          a = i.length - 1;
        1 <= s && 0 <= a && o[s] !== i[a];

      )
        a--;
      for (; 1 <= s && 0 <= a; s--, a--)
        if (o[s] !== i[a]) {
          if (s !== 1 || a !== 1)
            do
              if ((s--, a--, 0 > a || o[s] !== i[a])) {
                var l =
                  `
` + o[s].replace(" at new ", " at ");
                return (
                  e.displayName &&
                    l.includes("<anonymous>") &&
                    (l = l.replace("<anonymous>", e.displayName)),
                  l
                );
              }
            while (1 <= s && 0 <= a);
          break;
        }
    }
  } finally {
    (Tu = !1), (Error.prepareStackTrace = n);
  }
  return (e = e ? e.displayName || e.name : "") ? wi(e) : "";
}
function XC(e) {
  switch (e.tag) {
    case 5:
      return wi(e.type);
    case 16:
      return wi("Lazy");
    case 13:
      return wi("Suspense");
    case 19:
      return wi("SuspenseList");
    case 0:
    case 2:
    case 15:
      return (e = Nu(e.type, !1)), e;
    case 11:
      return (e = Nu(e.type.render, !1)), e;
    case 1:
      return (e = Nu(e.type, !0)), e;
    default:
      return "";
  }
}
function Lc(e) {
  if (e == null) return null;
  if (typeof e == "function") return e.displayName || e.name || null;
  if (typeof e == "string") return e;
  switch (e) {
    case eo:
      return "Fragment";
    case Jr:
      return "Portal";
    case Rc:
      return "Profiler";
    case gd:
      return "StrictMode";
    case Dc:
      return "Suspense";
    case Ic:
      return "SuspenseList";
  }
  if (typeof e == "object")
    switch (e.$$typeof) {
      case p0:
        return (e.displayName || "Context") + ".Consumer";
      case h0:
        return (e._context.displayName || "Context") + ".Provider";
      case yd:
        var t = e.render;
        return (
          (e = e.displayName),
          e ||
            ((e = t.displayName || t.name || ""),
            (e = e !== "" ? "ForwardRef(" + e + ")" : "ForwardRef")),
          e
        );
      case vd:
        return (t = e.displayName || null), t !== null ? t : Lc(e.type) || "Memo";
      case In:
        (t = e._payload), (e = e._init);
        try {
          return Lc(e(t));
        } catch {}
    }
  return null;
}
function ZC(e) {
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
      return Lc(t);
    case 8:
      return t === gd ? "StrictMode" : "Mode";
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
function Qn(e) {
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
function g0(e) {
  var t = e.type;
  return (e = e.nodeName) && e.toLowerCase() === "input" && (t === "checkbox" || t === "radio");
}
function QC(e) {
  var t = g0(e) ? "checked" : "value",
    n = Object.getOwnPropertyDescriptor(e.constructor.prototype, t),
    r = "" + e[t];
  if (
    !e.hasOwnProperty(t) &&
    typeof n < "u" &&
    typeof n.get == "function" &&
    typeof n.set == "function"
  ) {
    var o = n.get,
      i = n.set;
    return (
      Object.defineProperty(e, t, {
        configurable: !0,
        get: function () {
          return o.call(this);
        },
        set: function (s) {
          (r = "" + s), i.call(this, s);
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
function Hs(e) {
  e._valueTracker || (e._valueTracker = QC(e));
}
function y0(e) {
  if (!e) return !1;
  var t = e._valueTracker;
  if (!t) return !0;
  var n = t.getValue(),
    r = "";
  return (
    e && (r = g0(e) ? (e.checked ? "true" : "false") : e.value),
    (e = r),
    e !== n ? (t.setValue(e), !0) : !1
  );
}
function Xa(e) {
  if (((e = e || (typeof document < "u" ? document : void 0)), typeof e > "u")) return null;
  try {
    return e.activeElement || e.body;
  } catch {
    return e.body;
  }
}
function Vc(e, t) {
  var n = t.checked;
  return ve({}, t, {
    defaultChecked: void 0,
    defaultValue: void 0,
    value: void 0,
    checked: n ?? e._wrapperState.initialChecked,
  });
}
function vp(e, t) {
  var n = t.defaultValue == null ? "" : t.defaultValue,
    r = t.checked != null ? t.checked : t.defaultChecked;
  (n = Qn(t.value != null ? t.value : n)),
    (e._wrapperState = {
      initialChecked: r,
      initialValue: n,
      controlled: t.type === "checkbox" || t.type === "radio" ? t.checked != null : t.value != null,
    });
}
function v0(e, t) {
  (t = t.checked), t != null && md(e, "checked", t, !1);
}
function Oc(e, t) {
  v0(e, t);
  var n = Qn(t.value),
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
    ? Fc(e, t.type, n)
    : t.hasOwnProperty("defaultValue") && Fc(e, t.type, Qn(t.defaultValue)),
    t.checked == null && t.defaultChecked != null && (e.defaultChecked = !!t.defaultChecked);
}
function xp(e, t, n) {
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
function Fc(e, t, n) {
  (t !== "number" || Xa(e.ownerDocument) !== e) &&
    (n == null
      ? (e.defaultValue = "" + e._wrapperState.initialValue)
      : e.defaultValue !== "" + n && (e.defaultValue = "" + n));
}
var Si = Array.isArray;
function xo(e, t, n, r) {
  if (((e = e.options), t)) {
    t = {};
    for (var o = 0; o < n.length; o++) t["$" + n[o]] = !0;
    for (n = 0; n < e.length; n++)
      (o = t.hasOwnProperty("$" + e[n].value)),
        e[n].selected !== o && (e[n].selected = o),
        o && r && (e[n].defaultSelected = !0);
  } else {
    for (n = "" + Qn(n), t = null, o = 0; o < e.length; o++) {
      if (e[o].value === n) {
        (e[o].selected = !0), r && (e[o].defaultSelected = !0);
        return;
      }
      t !== null || e[o].disabled || (t = e[o]);
    }
    t !== null && (t.selected = !0);
  }
}
function zc(e, t) {
  if (t.dangerouslySetInnerHTML != null) throw Error(B(91));
  return ve({}, t, {
    value: void 0,
    defaultValue: void 0,
    children: "" + e._wrapperState.initialValue,
  });
}
function wp(e, t) {
  var n = t.value;
  if (n == null) {
    if (((n = t.children), (t = t.defaultValue), n != null)) {
      if (t != null) throw Error(B(92));
      if (Si(n)) {
        if (1 < n.length) throw Error(B(93));
        n = n[0];
      }
      t = n;
    }
    t == null && (t = ""), (n = t);
  }
  e._wrapperState = { initialValue: Qn(n) };
}
function x0(e, t) {
  var n = Qn(t.value),
    r = Qn(t.defaultValue);
  n != null &&
    ((n = "" + n),
    n !== e.value && (e.value = n),
    t.defaultValue == null && e.defaultValue !== n && (e.defaultValue = n)),
    r != null && (e.defaultValue = "" + r);
}
function Sp(e) {
  var t = e.textContent;
  t === e._wrapperState.initialValue && t !== "" && t !== null && (e.value = t);
}
function w0(e) {
  switch (e) {
    case "svg":
      return "http://www.w3.org/2000/svg";
    case "math":
      return "http://www.w3.org/1998/Math/MathML";
    default:
      return "http://www.w3.org/1999/xhtml";
  }
}
function $c(e, t) {
  return e == null || e === "http://www.w3.org/1999/xhtml"
    ? w0(t)
    : e === "http://www.w3.org/2000/svg" && t === "foreignObject"
      ? "http://www.w3.org/1999/xhtml"
      : e;
}
var Ws,
  S0 = (function (e) {
    return typeof MSApp < "u" && MSApp.execUnsafeLocalFunction
      ? function (t, n, r, o) {
          MSApp.execUnsafeLocalFunction(function () {
            return e(t, n, r, o);
          });
        }
      : e;
  })(function (e, t) {
    if (e.namespaceURI !== "http://www.w3.org/2000/svg" || "innerHTML" in e) e.innerHTML = t;
    else {
      for (
        Ws = Ws || document.createElement("div"),
          Ws.innerHTML = "<svg>" + t.valueOf().toString() + "</svg>",
          t = Ws.firstChild;
        e.firstChild;

      )
        e.removeChild(e.firstChild);
      for (; t.firstChild; ) e.appendChild(t.firstChild);
    }
  });
function Gi(e, t) {
  if (t) {
    var n = e.firstChild;
    if (n && n === e.lastChild && n.nodeType === 3) {
      n.nodeValue = t;
      return;
    }
  }
  e.textContent = t;
}
var Mi = {
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
  qC = ["Webkit", "ms", "Moz", "O"];
Object.keys(Mi).forEach(function (e) {
  qC.forEach(function (t) {
    (t = t + e.charAt(0).toUpperCase() + e.substring(1)), (Mi[t] = Mi[e]);
  });
});
function E0(e, t, n) {
  return t == null || typeof t == "boolean" || t === ""
    ? ""
    : n || typeof t != "number" || t === 0 || (Mi.hasOwnProperty(e) && Mi[e])
      ? ("" + t).trim()
      : t + "px";
}
function C0(e, t) {
  e = e.style;
  for (var n in t)
    if (t.hasOwnProperty(n)) {
      var r = n.indexOf("--") === 0,
        o = E0(n, t[n], r);
      n === "float" && (n = "cssFloat"), r ? e.setProperty(n, o) : (e[n] = o);
    }
}
var JC = ve(
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
function jc(e, t) {
  if (t) {
    if (JC[e] && (t.children != null || t.dangerouslySetInnerHTML != null)) throw Error(B(137, e));
    if (t.dangerouslySetInnerHTML != null) {
      if (t.children != null) throw Error(B(60));
      if (typeof t.dangerouslySetInnerHTML != "object" || !("__html" in t.dangerouslySetInnerHTML))
        throw Error(B(61));
    }
    if (t.style != null && typeof t.style != "object") throw Error(B(62));
  }
}
function Bc(e, t) {
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
var Uc = null;
function xd(e) {
  return (
    (e = e.target || e.srcElement || window),
    e.correspondingUseElement && (e = e.correspondingUseElement),
    e.nodeType === 3 ? e.parentNode : e
  );
}
var Hc = null,
  wo = null,
  So = null;
function Ep(e) {
  if ((e = Ns(e))) {
    if (typeof Hc != "function") throw Error(B(280));
    var t = e.stateNode;
    t && ((t = Wl(t)), Hc(e.stateNode, e.type, t));
  }
}
function b0(e) {
  wo ? (So ? So.push(e) : (So = [e])) : (wo = e);
}
function k0() {
  if (wo) {
    var e = wo,
      t = So;
    if (((So = wo = null), Ep(e), t)) for (e = 0; e < t.length; e++) Ep(t[e]);
  }
}
function _0(e, t) {
  return e(t);
}
function T0() {}
var Pu = !1;
function N0(e, t, n) {
  if (Pu) return e(t, n);
  Pu = !0;
  try {
    return _0(e, t, n);
  } finally {
    (Pu = !1), (wo !== null || So !== null) && (T0(), k0());
  }
}
function Ki(e, t) {
  var n = e.stateNode;
  if (n === null) return null;
  var r = Wl(n);
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
  if (n && typeof n != "function") throw Error(B(231, t, typeof n));
  return n;
}
var Wc = !1;
if (xn)
  try {
    var ii = {};
    Object.defineProperty(ii, "passive", {
      get: function () {
        Wc = !0;
      },
    }),
      window.addEventListener("test", ii, ii),
      window.removeEventListener("test", ii, ii);
  } catch {
    Wc = !1;
  }
function eb(e, t, n, r, o, i, s, a, l) {
  var u = Array.prototype.slice.call(arguments, 3);
  try {
    t.apply(n, u);
  } catch (c) {
    this.onError(c);
  }
}
var Ai = !1,
  Za = null,
  Qa = !1,
  Gc = null,
  tb = {
    onError: function (e) {
      (Ai = !0), (Za = e);
    },
  };
function nb(e, t, n, r, o, i, s, a, l) {
  (Ai = !1), (Za = null), eb.apply(tb, arguments);
}
function rb(e, t, n, r, o, i, s, a, l) {
  if ((nb.apply(this, arguments), Ai)) {
    if (Ai) {
      var u = Za;
      (Ai = !1), (Za = null);
    } else throw Error(B(198));
    Qa || ((Qa = !0), (Gc = u));
  }
}
function Fr(e) {
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
function P0(e) {
  if (e.tag === 13) {
    var t = e.memoizedState;
    if ((t === null && ((e = e.alternate), e !== null && (t = e.memoizedState)), t !== null))
      return t.dehydrated;
  }
  return null;
}
function Cp(e) {
  if (Fr(e) !== e) throw Error(B(188));
}
function ob(e) {
  var t = e.alternate;
  if (!t) {
    if (((t = Fr(e)), t === null)) throw Error(B(188));
    return t !== e ? null : e;
  }
  for (var n = e, r = t; ; ) {
    var o = n.return;
    if (o === null) break;
    var i = o.alternate;
    if (i === null) {
      if (((r = o.return), r !== null)) {
        n = r;
        continue;
      }
      break;
    }
    if (o.child === i.child) {
      for (i = o.child; i; ) {
        if (i === n) return Cp(o), e;
        if (i === r) return Cp(o), t;
        i = i.sibling;
      }
      throw Error(B(188));
    }
    if (n.return !== r.return) (n = o), (r = i);
    else {
      for (var s = !1, a = o.child; a; ) {
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
      if (!s) {
        for (a = i.child; a; ) {
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
        if (!s) throw Error(B(189));
      }
    }
    if (n.alternate !== r) throw Error(B(190));
  }
  if (n.tag !== 3) throw Error(B(188));
  return n.stateNode.current === n ? e : t;
}
function M0(e) {
  return (e = ob(e)), e !== null ? A0(e) : null;
}
function A0(e) {
  if (e.tag === 5 || e.tag === 6) return e;
  for (e = e.child; e !== null; ) {
    var t = A0(e);
    if (t !== null) return t;
    e = e.sibling;
  }
  return null;
}
var R0 = ht.unstable_scheduleCallback,
  bp = ht.unstable_cancelCallback,
  ib = ht.unstable_shouldYield,
  sb = ht.unstable_requestPaint,
  be = ht.unstable_now,
  ab = ht.unstable_getCurrentPriorityLevel,
  wd = ht.unstable_ImmediatePriority,
  D0 = ht.unstable_UserBlockingPriority,
  qa = ht.unstable_NormalPriority,
  lb = ht.unstable_LowPriority,
  I0 = ht.unstable_IdlePriority,
  jl = null,
  Zt = null;
function ub(e) {
  if (Zt && typeof Zt.onCommitFiberRoot == "function")
    try {
      Zt.onCommitFiberRoot(jl, e, void 0, (e.current.flags & 128) === 128);
    } catch {}
}
var Ot = Math.clz32 ? Math.clz32 : db,
  cb = Math.log,
  fb = Math.LN2;
function db(e) {
  return (e >>>= 0), e === 0 ? 32 : (31 - ((cb(e) / fb) | 0)) | 0;
}
var Gs = 64,
  Ks = 4194304;
function Ei(e) {
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
function Ja(e, t) {
  var n = e.pendingLanes;
  if (n === 0) return 0;
  var r = 0,
    o = e.suspendedLanes,
    i = e.pingedLanes,
    s = n & 268435455;
  if (s !== 0) {
    var a = s & ~o;
    a !== 0 ? (r = Ei(a)) : ((i &= s), i !== 0 && (r = Ei(i)));
  } else (s = n & ~o), s !== 0 ? (r = Ei(s)) : i !== 0 && (r = Ei(i));
  if (r === 0) return 0;
  if (
    t !== 0 &&
    t !== r &&
    !(t & o) &&
    ((o = r & -r), (i = t & -t), o >= i || (o === 16 && (i & 4194240) !== 0))
  )
    return t;
  if ((r & 4 && (r |= n & 16), (t = e.entangledLanes), t !== 0))
    for (e = e.entanglements, t &= r; 0 < t; )
      (n = 31 - Ot(t)), (o = 1 << n), (r |= e[n]), (t &= ~o);
  return r;
}
function hb(e, t) {
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
function pb(e, t) {
  for (
    var n = e.suspendedLanes, r = e.pingedLanes, o = e.expirationTimes, i = e.pendingLanes;
    0 < i;

  ) {
    var s = 31 - Ot(i),
      a = 1 << s,
      l = o[s];
    l === -1 ? (!(a & n) || a & r) && (o[s] = hb(a, t)) : l <= t && (e.expiredLanes |= a),
      (i &= ~a);
  }
}
function Kc(e) {
  return (e = e.pendingLanes & -1073741825), e !== 0 ? e : e & 1073741824 ? 1073741824 : 0;
}
function L0() {
  var e = Gs;
  return (Gs <<= 1), !(Gs & 4194240) && (Gs = 64), e;
}
function Mu(e) {
  for (var t = [], n = 0; 31 > n; n++) t.push(e);
  return t;
}
function _s(e, t, n) {
  (e.pendingLanes |= t),
    t !== 536870912 && ((e.suspendedLanes = 0), (e.pingedLanes = 0)),
    (e = e.eventTimes),
    (t = 31 - Ot(t)),
    (e[t] = n);
}
function mb(e, t) {
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
    var o = 31 - Ot(n),
      i = 1 << o;
    (t[o] = 0), (r[o] = -1), (e[o] = -1), (n &= ~i);
  }
}
function Sd(e, t) {
  var n = (e.entangledLanes |= t);
  for (e = e.entanglements; n; ) {
    var r = 31 - Ot(n),
      o = 1 << r;
    (o & t) | (e[r] & t) && (e[r] |= t), (n &= ~o);
  }
}
var ie = 0;
function V0(e) {
  return (e &= -e), 1 < e ? (4 < e ? (e & 268435455 ? 16 : 536870912) : 4) : 1;
}
var O0,
  Ed,
  F0,
  z0,
  $0,
  Yc = !1,
  Ys = [],
  Bn = null,
  Un = null,
  Hn = null,
  Yi = new Map(),
  Xi = new Map(),
  Fn = [],
  gb =
    "mousedown mouseup touchcancel touchend touchstart auxclick dblclick pointercancel pointerdown pointerup dragend dragstart drop compositionend compositionstart keydown keypress keyup input textInput copy cut paste click change contextmenu reset submit".split(
      " ",
    );
function kp(e, t) {
  switch (e) {
    case "focusin":
    case "focusout":
      Bn = null;
      break;
    case "dragenter":
    case "dragleave":
      Un = null;
      break;
    case "mouseover":
    case "mouseout":
      Hn = null;
      break;
    case "pointerover":
    case "pointerout":
      Yi.delete(t.pointerId);
      break;
    case "gotpointercapture":
    case "lostpointercapture":
      Xi.delete(t.pointerId);
  }
}
function si(e, t, n, r, o, i) {
  return e === null || e.nativeEvent !== i
    ? ((e = {
        blockedOn: t,
        domEventName: n,
        eventSystemFlags: r,
        nativeEvent: i,
        targetContainers: [o],
      }),
      t !== null && ((t = Ns(t)), t !== null && Ed(t)),
      e)
    : ((e.eventSystemFlags |= r),
      (t = e.targetContainers),
      o !== null && t.indexOf(o) === -1 && t.push(o),
      e);
}
function yb(e, t, n, r, o) {
  switch (t) {
    case "focusin":
      return (Bn = si(Bn, e, t, n, r, o)), !0;
    case "dragenter":
      return (Un = si(Un, e, t, n, r, o)), !0;
    case "mouseover":
      return (Hn = si(Hn, e, t, n, r, o)), !0;
    case "pointerover":
      var i = o.pointerId;
      return Yi.set(i, si(Yi.get(i) || null, e, t, n, r, o)), !0;
    case "gotpointercapture":
      return (i = o.pointerId), Xi.set(i, si(Xi.get(i) || null, e, t, n, r, o)), !0;
  }
  return !1;
}
function j0(e) {
  var t = yr(e.target);
  if (t !== null) {
    var n = Fr(t);
    if (n !== null) {
      if (((t = n.tag), t === 13)) {
        if (((t = P0(n)), t !== null)) {
          (e.blockedOn = t),
            $0(e.priority, function () {
              F0(n);
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
function Ta(e) {
  if (e.blockedOn !== null) return !1;
  for (var t = e.targetContainers; 0 < t.length; ) {
    var n = Xc(e.domEventName, e.eventSystemFlags, t[0], e.nativeEvent);
    if (n === null) {
      n = e.nativeEvent;
      var r = new n.constructor(n.type, n);
      (Uc = r), n.target.dispatchEvent(r), (Uc = null);
    } else return (t = Ns(n)), t !== null && Ed(t), (e.blockedOn = n), !1;
    t.shift();
  }
  return !0;
}
function _p(e, t, n) {
  Ta(e) && n.delete(t);
}
function vb() {
  (Yc = !1),
    Bn !== null && Ta(Bn) && (Bn = null),
    Un !== null && Ta(Un) && (Un = null),
    Hn !== null && Ta(Hn) && (Hn = null),
    Yi.forEach(_p),
    Xi.forEach(_p);
}
function ai(e, t) {
  e.blockedOn === t &&
    ((e.blockedOn = null),
    Yc || ((Yc = !0), ht.unstable_scheduleCallback(ht.unstable_NormalPriority, vb)));
}
function Zi(e) {
  function t(o) {
    return ai(o, e);
  }
  if (0 < Ys.length) {
    ai(Ys[0], e);
    for (var n = 1; n < Ys.length; n++) {
      var r = Ys[n];
      r.blockedOn === e && (r.blockedOn = null);
    }
  }
  for (
    Bn !== null && ai(Bn, e),
      Un !== null && ai(Un, e),
      Hn !== null && ai(Hn, e),
      Yi.forEach(t),
      Xi.forEach(t),
      n = 0;
    n < Fn.length;
    n++
  )
    (r = Fn[n]), r.blockedOn === e && (r.blockedOn = null);
  for (; 0 < Fn.length && ((n = Fn[0]), n.blockedOn === null); )
    j0(n), n.blockedOn === null && Fn.shift();
}
var Eo = Tn.ReactCurrentBatchConfig,
  el = !0;
function xb(e, t, n, r) {
  var o = ie,
    i = Eo.transition;
  Eo.transition = null;
  try {
    (ie = 1), Cd(e, t, n, r);
  } finally {
    (ie = o), (Eo.transition = i);
  }
}
function wb(e, t, n, r) {
  var o = ie,
    i = Eo.transition;
  Eo.transition = null;
  try {
    (ie = 4), Cd(e, t, n, r);
  } finally {
    (ie = o), (Eo.transition = i);
  }
}
function Cd(e, t, n, r) {
  if (el) {
    var o = Xc(e, t, n, r);
    if (o === null) $u(e, t, r, tl, n), kp(e, r);
    else if (yb(o, e, t, n, r)) r.stopPropagation();
    else if ((kp(e, r), t & 4 && -1 < gb.indexOf(e))) {
      for (; o !== null; ) {
        var i = Ns(o);
        if ((i !== null && O0(i), (i = Xc(e, t, n, r)), i === null && $u(e, t, r, tl, n), i === o))
          break;
        o = i;
      }
      o !== null && r.stopPropagation();
    } else $u(e, t, r, null, n);
  }
}
var tl = null;
function Xc(e, t, n, r) {
  if (((tl = null), (e = xd(r)), (e = yr(e)), e !== null))
    if (((t = Fr(e)), t === null)) e = null;
    else if (((n = t.tag), n === 13)) {
      if (((e = P0(t)), e !== null)) return e;
      e = null;
    } else if (n === 3) {
      if (t.stateNode.current.memoizedState.isDehydrated)
        return t.tag === 3 ? t.stateNode.containerInfo : null;
      e = null;
    } else t !== e && (e = null);
  return (tl = e), null;
}
function B0(e) {
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
      switch (ab()) {
        case wd:
          return 1;
        case D0:
          return 4;
        case qa:
        case lb:
          return 16;
        case I0:
          return 536870912;
        default:
          return 16;
      }
    default:
      return 16;
  }
}
var $n = null,
  bd = null,
  Na = null;
function U0() {
  if (Na) return Na;
  var e,
    t = bd,
    n = t.length,
    r,
    o = "value" in $n ? $n.value : $n.textContent,
    i = o.length;
  for (e = 0; e < n && t[e] === o[e]; e++);
  var s = n - e;
  for (r = 1; r <= s && t[n - r] === o[i - r]; r++);
  return (Na = o.slice(e, 1 < r ? 1 - r : void 0));
}
function Pa(e) {
  var t = e.keyCode;
  return (
    "charCode" in e ? ((e = e.charCode), e === 0 && t === 13 && (e = 13)) : (e = t),
    e === 10 && (e = 13),
    32 <= e || e === 13 ? e : 0
  );
}
function Xs() {
  return !0;
}
function Tp() {
  return !1;
}
function yt(e) {
  function t(n, r, o, i, s) {
    (this._reactName = n),
      (this._targetInst = o),
      (this.type = r),
      (this.nativeEvent = i),
      (this.target = s),
      (this.currentTarget = null);
    for (var a in e) e.hasOwnProperty(a) && ((n = e[a]), (this[a] = n ? n(i) : i[a]));
    return (
      (this.isDefaultPrevented = (
        i.defaultPrevented != null ? i.defaultPrevented : i.returnValue === !1
      )
        ? Xs
        : Tp),
      (this.isPropagationStopped = Tp),
      this
    );
  }
  return (
    ve(t.prototype, {
      preventDefault: function () {
        this.defaultPrevented = !0;
        var n = this.nativeEvent;
        n &&
          (n.preventDefault
            ? n.preventDefault()
            : typeof n.returnValue != "unknown" && (n.returnValue = !1),
          (this.isDefaultPrevented = Xs));
      },
      stopPropagation: function () {
        var n = this.nativeEvent;
        n &&
          (n.stopPropagation
            ? n.stopPropagation()
            : typeof n.cancelBubble != "unknown" && (n.cancelBubble = !0),
          (this.isPropagationStopped = Xs));
      },
      persist: function () {},
      isPersistent: Xs,
    }),
    t
  );
}
var Yo = {
    eventPhase: 0,
    bubbles: 0,
    cancelable: 0,
    timeStamp: function (e) {
      return e.timeStamp || Date.now();
    },
    defaultPrevented: 0,
    isTrusted: 0,
  },
  kd = yt(Yo),
  Ts = ve({}, Yo, { view: 0, detail: 0 }),
  Sb = yt(Ts),
  Au,
  Ru,
  li,
  Bl = ve({}, Ts, {
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
    getModifierState: _d,
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
        : (e !== li &&
            (li && e.type === "mousemove"
              ? ((Au = e.screenX - li.screenX), (Ru = e.screenY - li.screenY))
              : (Ru = Au = 0),
            (li = e)),
          Au);
    },
    movementY: function (e) {
      return "movementY" in e ? e.movementY : Ru;
    },
  }),
  Np = yt(Bl),
  Eb = ve({}, Bl, { dataTransfer: 0 }),
  Cb = yt(Eb),
  bb = ve({}, Ts, { relatedTarget: 0 }),
  Du = yt(bb),
  kb = ve({}, Yo, { animationName: 0, elapsedTime: 0, pseudoElement: 0 }),
  _b = yt(kb),
  Tb = ve({}, Yo, {
    clipboardData: function (e) {
      return "clipboardData" in e ? e.clipboardData : window.clipboardData;
    },
  }),
  Nb = yt(Tb),
  Pb = ve({}, Yo, { data: 0 }),
  Pp = yt(Pb),
  Mb = {
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
  Ab = {
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
  Rb = { Alt: "altKey", Control: "ctrlKey", Meta: "metaKey", Shift: "shiftKey" };
function Db(e) {
  var t = this.nativeEvent;
  return t.getModifierState ? t.getModifierState(e) : (e = Rb[e]) ? !!t[e] : !1;
}
function _d() {
  return Db;
}
var Ib = ve({}, Ts, {
    key: function (e) {
      if (e.key) {
        var t = Mb[e.key] || e.key;
        if (t !== "Unidentified") return t;
      }
      return e.type === "keypress"
        ? ((e = Pa(e)), e === 13 ? "Enter" : String.fromCharCode(e))
        : e.type === "keydown" || e.type === "keyup"
          ? Ab[e.keyCode] || "Unidentified"
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
    getModifierState: _d,
    charCode: function (e) {
      return e.type === "keypress" ? Pa(e) : 0;
    },
    keyCode: function (e) {
      return e.type === "keydown" || e.type === "keyup" ? e.keyCode : 0;
    },
    which: function (e) {
      return e.type === "keypress"
        ? Pa(e)
        : e.type === "keydown" || e.type === "keyup"
          ? e.keyCode
          : 0;
    },
  }),
  Lb = yt(Ib),
  Vb = ve({}, Bl, {
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
  Mp = yt(Vb),
  Ob = ve({}, Ts, {
    touches: 0,
    targetTouches: 0,
    changedTouches: 0,
    altKey: 0,
    metaKey: 0,
    ctrlKey: 0,
    shiftKey: 0,
    getModifierState: _d,
  }),
  Fb = yt(Ob),
  zb = ve({}, Yo, { propertyName: 0, elapsedTime: 0, pseudoElement: 0 }),
  $b = yt(zb),
  jb = ve({}, Bl, {
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
  Bb = yt(jb),
  Ub = [9, 13, 27, 32],
  Td = xn && "CompositionEvent" in window,
  Ri = null;
xn && "documentMode" in document && (Ri = document.documentMode);
var Hb = xn && "TextEvent" in window && !Ri,
  H0 = xn && (!Td || (Ri && 8 < Ri && 11 >= Ri)),
  Ap = " ",
  Rp = !1;
function W0(e, t) {
  switch (e) {
    case "keyup":
      return Ub.indexOf(t.keyCode) !== -1;
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
function G0(e) {
  return (e = e.detail), typeof e == "object" && "data" in e ? e.data : null;
}
var to = !1;
function Wb(e, t) {
  switch (e) {
    case "compositionend":
      return G0(t);
    case "keypress":
      return t.which !== 32 ? null : ((Rp = !0), Ap);
    case "textInput":
      return (e = t.data), e === Ap && Rp ? null : e;
    default:
      return null;
  }
}
function Gb(e, t) {
  if (to)
    return e === "compositionend" || (!Td && W0(e, t))
      ? ((e = U0()), (Na = bd = $n = null), (to = !1), e)
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
      return H0 && t.locale !== "ko" ? null : t.data;
    default:
      return null;
  }
}
var Kb = {
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
function Dp(e) {
  var t = e && e.nodeName && e.nodeName.toLowerCase();
  return t === "input" ? !!Kb[e.type] : t === "textarea";
}
function K0(e, t, n, r) {
  b0(r),
    (t = nl(t, "onChange")),
    0 < t.length &&
      ((n = new kd("onChange", "change", null, n, r)), e.push({ event: n, listeners: t }));
}
var Di = null,
  Qi = null;
function Yb(e) {
  ov(e, 0);
}
function Ul(e) {
  var t = oo(e);
  if (y0(t)) return e;
}
function Xb(e, t) {
  if (e === "change") return t;
}
var Y0 = !1;
if (xn) {
  var Iu;
  if (xn) {
    var Lu = "oninput" in document;
    if (!Lu) {
      var Ip = document.createElement("div");
      Ip.setAttribute("oninput", "return;"), (Lu = typeof Ip.oninput == "function");
    }
    Iu = Lu;
  } else Iu = !1;
  Y0 = Iu && (!document.documentMode || 9 < document.documentMode);
}
function Lp() {
  Di && (Di.detachEvent("onpropertychange", X0), (Qi = Di = null));
}
function X0(e) {
  if (e.propertyName === "value" && Ul(Qi)) {
    var t = [];
    K0(t, Qi, e, xd(e)), N0(Yb, t);
  }
}
function Zb(e, t, n) {
  e === "focusin"
    ? (Lp(), (Di = t), (Qi = n), Di.attachEvent("onpropertychange", X0))
    : e === "focusout" && Lp();
}
function Qb(e) {
  if (e === "selectionchange" || e === "keyup" || e === "keydown") return Ul(Qi);
}
function qb(e, t) {
  if (e === "click") return Ul(t);
}
function Jb(e, t) {
  if (e === "input" || e === "change") return Ul(t);
}
function ek(e, t) {
  return (e === t && (e !== 0 || 1 / e === 1 / t)) || (e !== e && t !== t);
}
var $t = typeof Object.is == "function" ? Object.is : ek;
function qi(e, t) {
  if ($t(e, t)) return !0;
  if (typeof e != "object" || e === null || typeof t != "object" || t === null) return !1;
  var n = Object.keys(e),
    r = Object.keys(t);
  if (n.length !== r.length) return !1;
  for (r = 0; r < n.length; r++) {
    var o = n[r];
    if (!Ac.call(t, o) || !$t(e[o], t[o])) return !1;
  }
  return !0;
}
function Vp(e) {
  for (; e && e.firstChild; ) e = e.firstChild;
  return e;
}
function Op(e, t) {
  var n = Vp(e);
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
    n = Vp(n);
  }
}
function Z0(e, t) {
  return e && t
    ? e === t
      ? !0
      : e && e.nodeType === 3
        ? !1
        : t && t.nodeType === 3
          ? Z0(e, t.parentNode)
          : "contains" in e
            ? e.contains(t)
            : e.compareDocumentPosition
              ? !!(e.compareDocumentPosition(t) & 16)
              : !1
    : !1;
}
function Q0() {
  for (var e = window, t = Xa(); t instanceof e.HTMLIFrameElement; ) {
    try {
      var n = typeof t.contentWindow.location.href == "string";
    } catch {
      n = !1;
    }
    if (n) e = t.contentWindow;
    else break;
    t = Xa(e.document);
  }
  return t;
}
function Nd(e) {
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
function tk(e) {
  var t = Q0(),
    n = e.focusedElem,
    r = e.selectionRange;
  if (t !== n && n && n.ownerDocument && Z0(n.ownerDocument.documentElement, n)) {
    if (r !== null && Nd(n)) {
      if (((t = r.start), (e = r.end), e === void 0 && (e = t), "selectionStart" in n))
        (n.selectionStart = t), (n.selectionEnd = Math.min(e, n.value.length));
      else if (
        ((e = ((t = n.ownerDocument || document) && t.defaultView) || window), e.getSelection)
      ) {
        e = e.getSelection();
        var o = n.textContent.length,
          i = Math.min(r.start, o);
        (r = r.end === void 0 ? i : Math.min(r.end, o)),
          !e.extend && i > r && ((o = r), (r = i), (i = o)),
          (o = Op(n, i));
        var s = Op(n, r);
        o &&
          s &&
          (e.rangeCount !== 1 ||
            e.anchorNode !== o.node ||
            e.anchorOffset !== o.offset ||
            e.focusNode !== s.node ||
            e.focusOffset !== s.offset) &&
          ((t = t.createRange()),
          t.setStart(o.node, o.offset),
          e.removeAllRanges(),
          i > r
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
var nk = xn && "documentMode" in document && 11 >= document.documentMode,
  no = null,
  Zc = null,
  Ii = null,
  Qc = !1;
function Fp(e, t, n) {
  var r = n.window === n ? n.document : n.nodeType === 9 ? n : n.ownerDocument;
  Qc ||
    no == null ||
    no !== Xa(r) ||
    ((r = no),
    "selectionStart" in r && Nd(r)
      ? (r = { start: r.selectionStart, end: r.selectionEnd })
      : ((r = ((r.ownerDocument && r.ownerDocument.defaultView) || window).getSelection()),
        (r = {
          anchorNode: r.anchorNode,
          anchorOffset: r.anchorOffset,
          focusNode: r.focusNode,
          focusOffset: r.focusOffset,
        })),
    (Ii && qi(Ii, r)) ||
      ((Ii = r),
      (r = nl(Zc, "onSelect")),
      0 < r.length &&
        ((t = new kd("onSelect", "select", null, t, n)),
        e.push({ event: t, listeners: r }),
        (t.target = no))));
}
function Zs(e, t) {
  var n = {};
  return (
    (n[e.toLowerCase()] = t.toLowerCase()),
    (n["Webkit" + e] = "webkit" + t),
    (n["Moz" + e] = "moz" + t),
    n
  );
}
var ro = {
    animationend: Zs("Animation", "AnimationEnd"),
    animationiteration: Zs("Animation", "AnimationIteration"),
    animationstart: Zs("Animation", "AnimationStart"),
    transitionend: Zs("Transition", "TransitionEnd"),
  },
  Vu = {},
  q0 = {};
xn &&
  ((q0 = document.createElement("div").style),
  "AnimationEvent" in window ||
    (delete ro.animationend.animation,
    delete ro.animationiteration.animation,
    delete ro.animationstart.animation),
  "TransitionEvent" in window || delete ro.transitionend.transition);
function Hl(e) {
  if (Vu[e]) return Vu[e];
  if (!ro[e]) return e;
  var t = ro[e],
    n;
  for (n in t) if (t.hasOwnProperty(n) && n in q0) return (Vu[e] = t[n]);
  return e;
}
var J0 = Hl("animationend"),
  ev = Hl("animationiteration"),
  tv = Hl("animationstart"),
  nv = Hl("transitionend"),
  rv = new Map(),
  zp =
    "abort auxClick cancel canPlay canPlayThrough click close contextMenu copy cut drag dragEnd dragEnter dragExit dragLeave dragOver dragStart drop durationChange emptied encrypted ended error gotPointerCapture input invalid keyDown keyPress keyUp load loadedData loadedMetadata loadStart lostPointerCapture mouseDown mouseMove mouseOut mouseOver mouseUp paste pause play playing pointerCancel pointerDown pointerMove pointerOut pointerOver pointerUp progress rateChange reset resize seeked seeking stalled submit suspend timeUpdate touchCancel touchEnd touchStart volumeChange scroll toggle touchMove waiting wheel".split(
      " ",
    );
function tr(e, t) {
  rv.set(e, t), Or(t, [e]);
}
for (var Ou = 0; Ou < zp.length; Ou++) {
  var Fu = zp[Ou],
    rk = Fu.toLowerCase(),
    ok = Fu[0].toUpperCase() + Fu.slice(1);
  tr(rk, "on" + ok);
}
tr(J0, "onAnimationEnd");
tr(ev, "onAnimationIteration");
tr(tv, "onAnimationStart");
tr("dblclick", "onDoubleClick");
tr("focusin", "onFocus");
tr("focusout", "onBlur");
tr(nv, "onTransitionEnd");
Ao("onMouseEnter", ["mouseout", "mouseover"]);
Ao("onMouseLeave", ["mouseout", "mouseover"]);
Ao("onPointerEnter", ["pointerout", "pointerover"]);
Ao("onPointerLeave", ["pointerout", "pointerover"]);
Or("onChange", "change click focusin focusout input keydown keyup selectionchange".split(" "));
Or(
  "onSelect",
  "focusout contextmenu dragend focusin keydown keyup mousedown mouseup selectionchange".split(" "),
);
Or("onBeforeInput", ["compositionend", "keypress", "textInput", "paste"]);
Or("onCompositionEnd", "compositionend focusout keydown keypress keyup mousedown".split(" "));
Or("onCompositionStart", "compositionstart focusout keydown keypress keyup mousedown".split(" "));
Or("onCompositionUpdate", "compositionupdate focusout keydown keypress keyup mousedown".split(" "));
var Ci =
    "abort canplay canplaythrough durationchange emptied encrypted ended error loadeddata loadedmetadata loadstart pause play playing progress ratechange resize seeked seeking stalled suspend timeupdate volumechange waiting".split(
      " ",
    ),
  ik = new Set("cancel close invalid load scroll toggle".split(" ").concat(Ci));
function $p(e, t, n) {
  var r = e.type || "unknown-event";
  (e.currentTarget = n), rb(r, t, void 0, e), (e.currentTarget = null);
}
function ov(e, t) {
  t = (t & 4) !== 0;
  for (var n = 0; n < e.length; n++) {
    var r = e[n],
      o = r.event;
    r = r.listeners;
    e: {
      var i = void 0;
      if (t)
        for (var s = r.length - 1; 0 <= s; s--) {
          var a = r[s],
            l = a.instance,
            u = a.currentTarget;
          if (((a = a.listener), l !== i && o.isPropagationStopped())) break e;
          $p(o, a, u), (i = l);
        }
      else
        for (s = 0; s < r.length; s++) {
          if (
            ((a = r[s]),
            (l = a.instance),
            (u = a.currentTarget),
            (a = a.listener),
            l !== i && o.isPropagationStopped())
          )
            break e;
          $p(o, a, u), (i = l);
        }
    }
  }
  if (Qa) throw ((e = Gc), (Qa = !1), (Gc = null), e);
}
function de(e, t) {
  var n = t[nf];
  n === void 0 && (n = t[nf] = new Set());
  var r = e + "__bubble";
  n.has(r) || (iv(t, e, 2, !1), n.add(r));
}
function zu(e, t, n) {
  var r = 0;
  t && (r |= 4), iv(n, e, r, t);
}
var Qs = "_reactListening" + Math.random().toString(36).slice(2);
function Ji(e) {
  if (!e[Qs]) {
    (e[Qs] = !0),
      d0.forEach(function (n) {
        n !== "selectionchange" && (ik.has(n) || zu(n, !1, e), zu(n, !0, e));
      });
    var t = e.nodeType === 9 ? e : e.ownerDocument;
    t === null || t[Qs] || ((t[Qs] = !0), zu("selectionchange", !1, t));
  }
}
function iv(e, t, n, r) {
  switch (B0(t)) {
    case 1:
      var o = xb;
      break;
    case 4:
      o = wb;
      break;
    default:
      o = Cd;
  }
  (n = o.bind(null, t, n, e)),
    (o = void 0),
    !Wc || (t !== "touchstart" && t !== "touchmove" && t !== "wheel") || (o = !0),
    r
      ? o !== void 0
        ? e.addEventListener(t, n, { capture: !0, passive: o })
        : e.addEventListener(t, n, !0)
      : o !== void 0
        ? e.addEventListener(t, n, { passive: o })
        : e.addEventListener(t, n, !1);
}
function $u(e, t, n, r, o) {
  var i = r;
  if (!(t & 1) && !(t & 2) && r !== null)
    e: for (;;) {
      if (r === null) return;
      var s = r.tag;
      if (s === 3 || s === 4) {
        var a = r.stateNode.containerInfo;
        if (a === o || (a.nodeType === 8 && a.parentNode === o)) break;
        if (s === 4)
          for (s = r.return; s !== null; ) {
            var l = s.tag;
            if (
              (l === 3 || l === 4) &&
              ((l = s.stateNode.containerInfo), l === o || (l.nodeType === 8 && l.parentNode === o))
            )
              return;
            s = s.return;
          }
        for (; a !== null; ) {
          if (((s = yr(a)), s === null)) return;
          if (((l = s.tag), l === 5 || l === 6)) {
            r = i = s;
            continue e;
          }
          a = a.parentNode;
        }
      }
      r = r.return;
    }
  N0(function () {
    var u = i,
      c = xd(n),
      f = [];
    e: {
      var d = rv.get(e);
      if (d !== void 0) {
        var p = kd,
          y = e;
        switch (e) {
          case "keypress":
            if (Pa(n) === 0) break e;
          case "keydown":
          case "keyup":
            p = Lb;
            break;
          case "focusin":
            (y = "focus"), (p = Du);
            break;
          case "focusout":
            (y = "blur"), (p = Du);
            break;
          case "beforeblur":
          case "afterblur":
            p = Du;
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
            p = Np;
            break;
          case "drag":
          case "dragend":
          case "dragenter":
          case "dragexit":
          case "dragleave":
          case "dragover":
          case "dragstart":
          case "drop":
            p = Cb;
            break;
          case "touchcancel":
          case "touchend":
          case "touchmove":
          case "touchstart":
            p = Fb;
            break;
          case J0:
          case ev:
          case tv:
            p = _b;
            break;
          case nv:
            p = $b;
            break;
          case "scroll":
            p = Sb;
            break;
          case "wheel":
            p = Bb;
            break;
          case "copy":
          case "cut":
          case "paste":
            p = Nb;
            break;
          case "gotpointercapture":
          case "lostpointercapture":
          case "pointercancel":
          case "pointerdown":
          case "pointermove":
          case "pointerout":
          case "pointerover":
          case "pointerup":
            p = Mp;
        }
        var m = (t & 4) !== 0,
          w = !m && e === "scroll",
          h = m ? (d !== null ? d + "Capture" : null) : d;
        m = [];
        for (var g = u, x; g !== null; ) {
          x = g;
          var S = x.stateNode;
          if (
            (x.tag === 5 &&
              S !== null &&
              ((x = S), h !== null && ((S = Ki(g, h)), S != null && m.push(es(g, S, x)))),
            w)
          )
            break;
          g = g.return;
        }
        0 < m.length && ((d = new p(d, y, null, n, c)), f.push({ event: d, listeners: m }));
      }
    }
    if (!(t & 7)) {
      e: {
        if (
          ((d = e === "mouseover" || e === "pointerover"),
          (p = e === "mouseout" || e === "pointerout"),
          d && n !== Uc && (y = n.relatedTarget || n.fromElement) && (yr(y) || y[wn]))
        )
          break e;
        if (
          (p || d) &&
          ((d =
            c.window === c ? c : (d = c.ownerDocument) ? d.defaultView || d.parentWindow : window),
          p
            ? ((y = n.relatedTarget || n.toElement),
              (p = u),
              (y = y ? yr(y) : null),
              y !== null && ((w = Fr(y)), y !== w || (y.tag !== 5 && y.tag !== 6)) && (y = null))
            : ((p = null), (y = u)),
          p !== y)
        ) {
          if (
            ((m = Np),
            (S = "onMouseLeave"),
            (h = "onMouseEnter"),
            (g = "mouse"),
            (e === "pointerout" || e === "pointerover") &&
              ((m = Mp), (S = "onPointerLeave"), (h = "onPointerEnter"), (g = "pointer")),
            (w = p == null ? d : oo(p)),
            (x = y == null ? d : oo(y)),
            (d = new m(S, g + "leave", p, n, c)),
            (d.target = w),
            (d.relatedTarget = x),
            (S = null),
            yr(c) === u &&
              ((m = new m(h, g + "enter", y, n, c)),
              (m.target = x),
              (m.relatedTarget = w),
              (S = m)),
            (w = S),
            p && y)
          )
            t: {
              for (m = p, h = y, g = 0, x = m; x; x = Wr(x)) g++;
              for (x = 0, S = h; S; S = Wr(S)) x++;
              for (; 0 < g - x; ) (m = Wr(m)), g--;
              for (; 0 < x - g; ) (h = Wr(h)), x--;
              for (; g--; ) {
                if (m === h || (h !== null && m === h.alternate)) break t;
                (m = Wr(m)), (h = Wr(h));
              }
              m = null;
            }
          else m = null;
          p !== null && jp(f, d, p, m, !1), y !== null && w !== null && jp(f, w, y, m, !0);
        }
      }
      e: {
        if (
          ((d = u ? oo(u) : window),
          (p = d.nodeName && d.nodeName.toLowerCase()),
          p === "select" || (p === "input" && d.type === "file"))
        )
          var E = Xb;
        else if (Dp(d))
          if (Y0) E = Jb;
          else {
            E = Qb;
            var C = Zb;
          }
        else
          (p = d.nodeName) &&
            p.toLowerCase() === "input" &&
            (d.type === "checkbox" || d.type === "radio") &&
            (E = qb);
        if (E && (E = E(e, u))) {
          K0(f, E, n, c);
          break e;
        }
        C && C(e, d, u),
          e === "focusout" &&
            (C = d._wrapperState) &&
            C.controlled &&
            d.type === "number" &&
            Fc(d, "number", d.value);
      }
      switch (((C = u ? oo(u) : window), e)) {
        case "focusin":
          (Dp(C) || C.contentEditable === "true") && ((no = C), (Zc = u), (Ii = null));
          break;
        case "focusout":
          Ii = Zc = no = null;
          break;
        case "mousedown":
          Qc = !0;
          break;
        case "contextmenu":
        case "mouseup":
        case "dragend":
          (Qc = !1), Fp(f, n, c);
          break;
        case "selectionchange":
          if (nk) break;
        case "keydown":
        case "keyup":
          Fp(f, n, c);
      }
      var b;
      if (Td)
        e: {
          switch (e) {
            case "compositionstart":
              var _ = "onCompositionStart";
              break e;
            case "compositionend":
              _ = "onCompositionEnd";
              break e;
            case "compositionupdate":
              _ = "onCompositionUpdate";
              break e;
          }
          _ = void 0;
        }
      else
        to
          ? W0(e, n) && (_ = "onCompositionEnd")
          : e === "keydown" && n.keyCode === 229 && (_ = "onCompositionStart");
      _ &&
        (H0 &&
          n.locale !== "ko" &&
          (to || _ !== "onCompositionStart"
            ? _ === "onCompositionEnd" && to && (b = U0())
            : (($n = c), (bd = "value" in $n ? $n.value : $n.textContent), (to = !0))),
        (C = nl(u, _)),
        0 < C.length &&
          ((_ = new Pp(_, e, null, n, c)),
          f.push({ event: _, listeners: C }),
          b ? (_.data = b) : ((b = G0(n)), b !== null && (_.data = b)))),
        (b = Hb ? Wb(e, n) : Gb(e, n)) &&
          ((u = nl(u, "onBeforeInput")),
          0 < u.length &&
            ((c = new Pp("onBeforeInput", "beforeinput", null, n, c)),
            f.push({ event: c, listeners: u }),
            (c.data = b)));
    }
    ov(f, t);
  });
}
function es(e, t, n) {
  return { instance: e, listener: t, currentTarget: n };
}
function nl(e, t) {
  for (var n = t + "Capture", r = []; e !== null; ) {
    var o = e,
      i = o.stateNode;
    o.tag === 5 &&
      i !== null &&
      ((o = i),
      (i = Ki(e, n)),
      i != null && r.unshift(es(e, i, o)),
      (i = Ki(e, t)),
      i != null && r.push(es(e, i, o))),
      (e = e.return);
  }
  return r;
}
function Wr(e) {
  if (e === null) return null;
  do e = e.return;
  while (e && e.tag !== 5);
  return e || null;
}
function jp(e, t, n, r, o) {
  for (var i = t._reactName, s = []; n !== null && n !== r; ) {
    var a = n,
      l = a.alternate,
      u = a.stateNode;
    if (l !== null && l === r) break;
    a.tag === 5 &&
      u !== null &&
      ((a = u),
      o
        ? ((l = Ki(n, i)), l != null && s.unshift(es(n, l, a)))
        : o || ((l = Ki(n, i)), l != null && s.push(es(n, l, a)))),
      (n = n.return);
  }
  s.length !== 0 && e.push({ event: t, listeners: s });
}
var sk = /\r\n?/g,
  ak = /\u0000|\uFFFD/g;
function Bp(e) {
  return (typeof e == "string" ? e : "" + e)
    .replace(
      sk,
      `
`,
    )
    .replace(ak, "");
}
function qs(e, t, n) {
  if (((t = Bp(t)), Bp(e) !== t && n)) throw Error(B(425));
}
function rl() {}
var qc = null,
  Jc = null;
function ef(e, t) {
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
var tf = typeof setTimeout == "function" ? setTimeout : void 0,
  lk = typeof clearTimeout == "function" ? clearTimeout : void 0,
  Up = typeof Promise == "function" ? Promise : void 0,
  uk =
    typeof queueMicrotask == "function"
      ? queueMicrotask
      : typeof Up < "u"
        ? function (e) {
            return Up.resolve(null).then(e).catch(ck);
          }
        : tf;
function ck(e) {
  setTimeout(function () {
    throw e;
  });
}
function ju(e, t) {
  var n = t,
    r = 0;
  do {
    var o = n.nextSibling;
    if ((e.removeChild(n), o && o.nodeType === 8))
      if (((n = o.data), n === "/$")) {
        if (r === 0) {
          e.removeChild(o), Zi(t);
          return;
        }
        r--;
      } else (n !== "$" && n !== "$?" && n !== "$!") || r++;
    n = o;
  } while (n);
  Zi(t);
}
function Wn(e) {
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
function Hp(e) {
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
var Xo = Math.random().toString(36).slice(2),
  Kt = "__reactFiber$" + Xo,
  ts = "__reactProps$" + Xo,
  wn = "__reactContainer$" + Xo,
  nf = "__reactEvents$" + Xo,
  fk = "__reactListeners$" + Xo,
  dk = "__reactHandles$" + Xo;
function yr(e) {
  var t = e[Kt];
  if (t) return t;
  for (var n = e.parentNode; n; ) {
    if ((t = n[wn] || n[Kt])) {
      if (((n = t.alternate), t.child !== null || (n !== null && n.child !== null)))
        for (e = Hp(e); e !== null; ) {
          if ((n = e[Kt])) return n;
          e = Hp(e);
        }
      return t;
    }
    (e = n), (n = e.parentNode);
  }
  return null;
}
function Ns(e) {
  return (
    (e = e[Kt] || e[wn]),
    !e || (e.tag !== 5 && e.tag !== 6 && e.tag !== 13 && e.tag !== 3) ? null : e
  );
}
function oo(e) {
  if (e.tag === 5 || e.tag === 6) return e.stateNode;
  throw Error(B(33));
}
function Wl(e) {
  return e[ts] || null;
}
var rf = [],
  io = -1;
function nr(e) {
  return { current: e };
}
function he(e) {
  0 > io || ((e.current = rf[io]), (rf[io] = null), io--);
}
function ue(e, t) {
  io++, (rf[io] = e.current), (e.current = t);
}
var qn = {},
  Ke = nr(qn),
  ot = nr(!1),
  Pr = qn;
function Ro(e, t) {
  var n = e.type.contextTypes;
  if (!n) return qn;
  var r = e.stateNode;
  if (r && r.__reactInternalMemoizedUnmaskedChildContext === t)
    return r.__reactInternalMemoizedMaskedChildContext;
  var o = {},
    i;
  for (i in n) o[i] = t[i];
  return (
    r &&
      ((e = e.stateNode),
      (e.__reactInternalMemoizedUnmaskedChildContext = t),
      (e.__reactInternalMemoizedMaskedChildContext = o)),
    o
  );
}
function it(e) {
  return (e = e.childContextTypes), e != null;
}
function ol() {
  he(ot), he(Ke);
}
function Wp(e, t, n) {
  if (Ke.current !== qn) throw Error(B(168));
  ue(Ke, t), ue(ot, n);
}
function sv(e, t, n) {
  var r = e.stateNode;
  if (((t = t.childContextTypes), typeof r.getChildContext != "function")) return n;
  r = r.getChildContext();
  for (var o in r) if (!(o in t)) throw Error(B(108, ZC(e) || "Unknown", o));
  return ve({}, n, r);
}
function il(e) {
  return (
    (e = ((e = e.stateNode) && e.__reactInternalMemoizedMergedChildContext) || qn),
    (Pr = Ke.current),
    ue(Ke, e),
    ue(ot, ot.current),
    !0
  );
}
function Gp(e, t, n) {
  var r = e.stateNode;
  if (!r) throw Error(B(169));
  n
    ? ((e = sv(e, t, Pr)),
      (r.__reactInternalMemoizedMergedChildContext = e),
      he(ot),
      he(Ke),
      ue(Ke, e))
    : he(ot),
    ue(ot, n);
}
var cn = null,
  Gl = !1,
  Bu = !1;
function av(e) {
  cn === null ? (cn = [e]) : cn.push(e);
}
function hk(e) {
  (Gl = !0), av(e);
}
function rr() {
  if (!Bu && cn !== null) {
    Bu = !0;
    var e = 0,
      t = ie;
    try {
      var n = cn;
      for (ie = 1; e < n.length; e++) {
        var r = n[e];
        do r = r(!0);
        while (r !== null);
      }
      (cn = null), (Gl = !1);
    } catch (o) {
      throw (cn !== null && (cn = cn.slice(e + 1)), R0(wd, rr), o);
    } finally {
      (ie = t), (Bu = !1);
    }
  }
  return null;
}
var so = [],
  ao = 0,
  sl = null,
  al = 0,
  wt = [],
  St = 0,
  Mr = null,
  dn = 1,
  hn = "";
function dr(e, t) {
  (so[ao++] = al), (so[ao++] = sl), (sl = e), (al = t);
}
function lv(e, t, n) {
  (wt[St++] = dn), (wt[St++] = hn), (wt[St++] = Mr), (Mr = e);
  var r = dn;
  e = hn;
  var o = 32 - Ot(r) - 1;
  (r &= ~(1 << o)), (n += 1);
  var i = 32 - Ot(t) + o;
  if (30 < i) {
    var s = o - (o % 5);
    (i = (r & ((1 << s) - 1)).toString(32)),
      (r >>= s),
      (o -= s),
      (dn = (1 << (32 - Ot(t) + o)) | (n << o) | r),
      (hn = i + e);
  } else (dn = (1 << i) | (n << o) | r), (hn = e);
}
function Pd(e) {
  e.return !== null && (dr(e, 1), lv(e, 1, 0));
}
function Md(e) {
  for (; e === sl; ) (sl = so[--ao]), (so[ao] = null), (al = so[--ao]), (so[ao] = null);
  for (; e === Mr; )
    (Mr = wt[--St]),
      (wt[St] = null),
      (hn = wt[--St]),
      (wt[St] = null),
      (dn = wt[--St]),
      (wt[St] = null);
}
var ft = null,
  ct = null,
  pe = !1,
  Lt = null;
function uv(e, t) {
  var n = bt(5, null, null, 0);
  (n.elementType = "DELETED"),
    (n.stateNode = t),
    (n.return = e),
    (t = e.deletions),
    t === null ? ((e.deletions = [n]), (e.flags |= 16)) : t.push(n);
}
function Kp(e, t) {
  switch (e.tag) {
    case 5:
      var n = e.type;
      return (
        (t = t.nodeType !== 1 || n.toLowerCase() !== t.nodeName.toLowerCase() ? null : t),
        t !== null ? ((e.stateNode = t), (ft = e), (ct = Wn(t.firstChild)), !0) : !1
      );
    case 6:
      return (
        (t = e.pendingProps === "" || t.nodeType !== 3 ? null : t),
        t !== null ? ((e.stateNode = t), (ft = e), (ct = null), !0) : !1
      );
    case 13:
      return (
        (t = t.nodeType !== 8 ? null : t),
        t !== null
          ? ((n = Mr !== null ? { id: dn, overflow: hn } : null),
            (e.memoizedState = { dehydrated: t, treeContext: n, retryLane: 1073741824 }),
            (n = bt(18, null, null, 0)),
            (n.stateNode = t),
            (n.return = e),
            (e.child = n),
            (ft = e),
            (ct = null),
            !0)
          : !1
      );
    default:
      return !1;
  }
}
function of(e) {
  return (e.mode & 1) !== 0 && (e.flags & 128) === 0;
}
function sf(e) {
  if (pe) {
    var t = ct;
    if (t) {
      var n = t;
      if (!Kp(e, t)) {
        if (of(e)) throw Error(B(418));
        t = Wn(n.nextSibling);
        var r = ft;
        t && Kp(e, t) ? uv(r, n) : ((e.flags = (e.flags & -4097) | 2), (pe = !1), (ft = e));
      }
    } else {
      if (of(e)) throw Error(B(418));
      (e.flags = (e.flags & -4097) | 2), (pe = !1), (ft = e);
    }
  }
}
function Yp(e) {
  for (e = e.return; e !== null && e.tag !== 5 && e.tag !== 3 && e.tag !== 13; ) e = e.return;
  ft = e;
}
function Js(e) {
  if (e !== ft) return !1;
  if (!pe) return Yp(e), (pe = !0), !1;
  var t;
  if (
    ((t = e.tag !== 3) &&
      !(t = e.tag !== 5) &&
      ((t = e.type), (t = t !== "head" && t !== "body" && !ef(e.type, e.memoizedProps))),
    t && (t = ct))
  ) {
    if (of(e)) throw (cv(), Error(B(418)));
    for (; t; ) uv(e, t), (t = Wn(t.nextSibling));
  }
  if ((Yp(e), e.tag === 13)) {
    if (((e = e.memoizedState), (e = e !== null ? e.dehydrated : null), !e)) throw Error(B(317));
    e: {
      for (e = e.nextSibling, t = 0; e; ) {
        if (e.nodeType === 8) {
          var n = e.data;
          if (n === "/$") {
            if (t === 0) {
              ct = Wn(e.nextSibling);
              break e;
            }
            t--;
          } else (n !== "$" && n !== "$!" && n !== "$?") || t++;
        }
        e = e.nextSibling;
      }
      ct = null;
    }
  } else ct = ft ? Wn(e.stateNode.nextSibling) : null;
  return !0;
}
function cv() {
  for (var e = ct; e; ) e = Wn(e.nextSibling);
}
function Do() {
  (ct = ft = null), (pe = !1);
}
function Ad(e) {
  Lt === null ? (Lt = [e]) : Lt.push(e);
}
var pk = Tn.ReactCurrentBatchConfig;
function ui(e, t, n) {
  if (((e = n.ref), e !== null && typeof e != "function" && typeof e != "object")) {
    if (n._owner) {
      if (((n = n._owner), n)) {
        if (n.tag !== 1) throw Error(B(309));
        var r = n.stateNode;
      }
      if (!r) throw Error(B(147, e));
      var o = r,
        i = "" + e;
      return t !== null && t.ref !== null && typeof t.ref == "function" && t.ref._stringRef === i
        ? t.ref
        : ((t = function (s) {
            var a = o.refs;
            s === null ? delete a[i] : (a[i] = s);
          }),
          (t._stringRef = i),
          t);
    }
    if (typeof e != "string") throw Error(B(284));
    if (!n._owner) throw Error(B(290, e));
  }
  return e;
}
function ea(e, t) {
  throw (
    ((e = Object.prototype.toString.call(t)),
    Error(
      B(31, e === "[object Object]" ? "object with keys {" + Object.keys(t).join(", ") + "}" : e),
    ))
  );
}
function Xp(e) {
  var t = e._init;
  return t(e._payload);
}
function fv(e) {
  function t(h, g) {
    if (e) {
      var x = h.deletions;
      x === null ? ((h.deletions = [g]), (h.flags |= 16)) : x.push(g);
    }
  }
  function n(h, g) {
    if (!e) return null;
    for (; g !== null; ) t(h, g), (g = g.sibling);
    return null;
  }
  function r(h, g) {
    for (h = new Map(); g !== null; )
      g.key !== null ? h.set(g.key, g) : h.set(g.index, g), (g = g.sibling);
    return h;
  }
  function o(h, g) {
    return (h = Xn(h, g)), (h.index = 0), (h.sibling = null), h;
  }
  function i(h, g, x) {
    return (
      (h.index = x),
      e
        ? ((x = h.alternate),
          x !== null ? ((x = x.index), x < g ? ((h.flags |= 2), g) : x) : ((h.flags |= 2), g))
        : ((h.flags |= 1048576), g)
    );
  }
  function s(h) {
    return e && h.alternate === null && (h.flags |= 2), h;
  }
  function a(h, g, x, S) {
    return g === null || g.tag !== 6
      ? ((g = Xu(x, h.mode, S)), (g.return = h), g)
      : ((g = o(g, x)), (g.return = h), g);
  }
  function l(h, g, x, S) {
    var E = x.type;
    return E === eo
      ? c(h, g, x.props.children, S, x.key)
      : g !== null &&
          (g.elementType === E ||
            (typeof E == "object" && E !== null && E.$$typeof === In && Xp(E) === g.type))
        ? ((S = o(g, x.props)), (S.ref = ui(h, g, x)), (S.return = h), S)
        : ((S = Va(x.type, x.key, x.props, null, h.mode, S)),
          (S.ref = ui(h, g, x)),
          (S.return = h),
          S);
  }
  function u(h, g, x, S) {
    return g === null ||
      g.tag !== 4 ||
      g.stateNode.containerInfo !== x.containerInfo ||
      g.stateNode.implementation !== x.implementation
      ? ((g = Zu(x, h.mode, S)), (g.return = h), g)
      : ((g = o(g, x.children || [])), (g.return = h), g);
  }
  function c(h, g, x, S, E) {
    return g === null || g.tag !== 7
      ? ((g = kr(x, h.mode, S, E)), (g.return = h), g)
      : ((g = o(g, x)), (g.return = h), g);
  }
  function f(h, g, x) {
    if ((typeof g == "string" && g !== "") || typeof g == "number")
      return (g = Xu("" + g, h.mode, x)), (g.return = h), g;
    if (typeof g == "object" && g !== null) {
      switch (g.$$typeof) {
        case Us:
          return (
            (x = Va(g.type, g.key, g.props, null, h.mode, x)),
            (x.ref = ui(h, null, g)),
            (x.return = h),
            x
          );
        case Jr:
          return (g = Zu(g, h.mode, x)), (g.return = h), g;
        case In:
          var S = g._init;
          return f(h, S(g._payload), x);
      }
      if (Si(g) || oi(g)) return (g = kr(g, h.mode, x, null)), (g.return = h), g;
      ea(h, g);
    }
    return null;
  }
  function d(h, g, x, S) {
    var E = g !== null ? g.key : null;
    if ((typeof x == "string" && x !== "") || typeof x == "number")
      return E !== null ? null : a(h, g, "" + x, S);
    if (typeof x == "object" && x !== null) {
      switch (x.$$typeof) {
        case Us:
          return x.key === E ? l(h, g, x, S) : null;
        case Jr:
          return x.key === E ? u(h, g, x, S) : null;
        case In:
          return (E = x._init), d(h, g, E(x._payload), S);
      }
      if (Si(x) || oi(x)) return E !== null ? null : c(h, g, x, S, null);
      ea(h, x);
    }
    return null;
  }
  function p(h, g, x, S, E) {
    if ((typeof S == "string" && S !== "") || typeof S == "number")
      return (h = h.get(x) || null), a(g, h, "" + S, E);
    if (typeof S == "object" && S !== null) {
      switch (S.$$typeof) {
        case Us:
          return (h = h.get(S.key === null ? x : S.key) || null), l(g, h, S, E);
        case Jr:
          return (h = h.get(S.key === null ? x : S.key) || null), u(g, h, S, E);
        case In:
          var C = S._init;
          return p(h, g, x, C(S._payload), E);
      }
      if (Si(S) || oi(S)) return (h = h.get(x) || null), c(g, h, S, E, null);
      ea(g, S);
    }
    return null;
  }
  function y(h, g, x, S) {
    for (var E = null, C = null, b = g, _ = (g = 0), A = null; b !== null && _ < x.length; _++) {
      b.index > _ ? ((A = b), (b = null)) : (A = b.sibling);
      var R = d(h, b, x[_], S);
      if (R === null) {
        b === null && (b = A);
        break;
      }
      e && b && R.alternate === null && t(h, b),
        (g = i(R, g, _)),
        C === null ? (E = R) : (C.sibling = R),
        (C = R),
        (b = A);
    }
    if (_ === x.length) return n(h, b), pe && dr(h, _), E;
    if (b === null) {
      for (; _ < x.length; _++)
        (b = f(h, x[_], S)),
          b !== null && ((g = i(b, g, _)), C === null ? (E = b) : (C.sibling = b), (C = b));
      return pe && dr(h, _), E;
    }
    for (b = r(h, b); _ < x.length; _++)
      (A = p(b, h, _, x[_], S)),
        A !== null &&
          (e && A.alternate !== null && b.delete(A.key === null ? _ : A.key),
          (g = i(A, g, _)),
          C === null ? (E = A) : (C.sibling = A),
          (C = A));
    return (
      e &&
        b.forEach(function (z) {
          return t(h, z);
        }),
      pe && dr(h, _),
      E
    );
  }
  function m(h, g, x, S) {
    var E = oi(x);
    if (typeof E != "function") throw Error(B(150));
    if (((x = E.call(x)), x == null)) throw Error(B(151));
    for (
      var C = (E = null), b = g, _ = (g = 0), A = null, R = x.next();
      b !== null && !R.done;
      _++, R = x.next()
    ) {
      b.index > _ ? ((A = b), (b = null)) : (A = b.sibling);
      var z = d(h, b, R.value, S);
      if (z === null) {
        b === null && (b = A);
        break;
      }
      e && b && z.alternate === null && t(h, b),
        (g = i(z, g, _)),
        C === null ? (E = z) : (C.sibling = z),
        (C = z),
        (b = A);
    }
    if (R.done) return n(h, b), pe && dr(h, _), E;
    if (b === null) {
      for (; !R.done; _++, R = x.next())
        (R = f(h, R.value, S)),
          R !== null && ((g = i(R, g, _)), C === null ? (E = R) : (C.sibling = R), (C = R));
      return pe && dr(h, _), E;
    }
    for (b = r(h, b); !R.done; _++, R = x.next())
      (R = p(b, h, _, R.value, S)),
        R !== null &&
          (e && R.alternate !== null && b.delete(R.key === null ? _ : R.key),
          (g = i(R, g, _)),
          C === null ? (E = R) : (C.sibling = R),
          (C = R));
    return (
      e &&
        b.forEach(function (F) {
          return t(h, F);
        }),
      pe && dr(h, _),
      E
    );
  }
  function w(h, g, x, S) {
    if (
      (typeof x == "object" &&
        x !== null &&
        x.type === eo &&
        x.key === null &&
        (x = x.props.children),
      typeof x == "object" && x !== null)
    ) {
      switch (x.$$typeof) {
        case Us:
          e: {
            for (var E = x.key, C = g; C !== null; ) {
              if (C.key === E) {
                if (((E = x.type), E === eo)) {
                  if (C.tag === 7) {
                    n(h, C.sibling), (g = o(C, x.props.children)), (g.return = h), (h = g);
                    break e;
                  }
                } else if (
                  C.elementType === E ||
                  (typeof E == "object" && E !== null && E.$$typeof === In && Xp(E) === C.type)
                ) {
                  n(h, C.sibling),
                    (g = o(C, x.props)),
                    (g.ref = ui(h, C, x)),
                    (g.return = h),
                    (h = g);
                  break e;
                }
                n(h, C);
                break;
              } else t(h, C);
              C = C.sibling;
            }
            x.type === eo
              ? ((g = kr(x.props.children, h.mode, S, x.key)), (g.return = h), (h = g))
              : ((S = Va(x.type, x.key, x.props, null, h.mode, S)),
                (S.ref = ui(h, g, x)),
                (S.return = h),
                (h = S));
          }
          return s(h);
        case Jr:
          e: {
            for (C = x.key; g !== null; ) {
              if (g.key === C)
                if (
                  g.tag === 4 &&
                  g.stateNode.containerInfo === x.containerInfo &&
                  g.stateNode.implementation === x.implementation
                ) {
                  n(h, g.sibling), (g = o(g, x.children || [])), (g.return = h), (h = g);
                  break e;
                } else {
                  n(h, g);
                  break;
                }
              else t(h, g);
              g = g.sibling;
            }
            (g = Zu(x, h.mode, S)), (g.return = h), (h = g);
          }
          return s(h);
        case In:
          return (C = x._init), w(h, g, C(x._payload), S);
      }
      if (Si(x)) return y(h, g, x, S);
      if (oi(x)) return m(h, g, x, S);
      ea(h, x);
    }
    return (typeof x == "string" && x !== "") || typeof x == "number"
      ? ((x = "" + x),
        g !== null && g.tag === 6
          ? (n(h, g.sibling), (g = o(g, x)), (g.return = h), (h = g))
          : (n(h, g), (g = Xu(x, h.mode, S)), (g.return = h), (h = g)),
        s(h))
      : n(h, g);
  }
  return w;
}
var Io = fv(!0),
  dv = fv(!1),
  ll = nr(null),
  ul = null,
  lo = null,
  Rd = null;
function Dd() {
  Rd = lo = ul = null;
}
function Id(e) {
  var t = ll.current;
  he(ll), (e._currentValue = t);
}
function af(e, t, n) {
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
function Co(e, t) {
  (ul = e),
    (Rd = lo = null),
    (e = e.dependencies),
    e !== null && e.firstContext !== null && (e.lanes & t && (nt = !0), (e.firstContext = null));
}
function Tt(e) {
  var t = e._currentValue;
  if (Rd !== e)
    if (((e = { context: e, memoizedValue: t, next: null }), lo === null)) {
      if (ul === null) throw Error(B(308));
      (lo = e), (ul.dependencies = { lanes: 0, firstContext: e });
    } else lo = lo.next = e;
  return t;
}
var vr = null;
function Ld(e) {
  vr === null ? (vr = [e]) : vr.push(e);
}
function hv(e, t, n, r) {
  var o = t.interleaved;
  return (
    o === null ? ((n.next = n), Ld(t)) : ((n.next = o.next), (o.next = n)),
    (t.interleaved = n),
    Sn(e, r)
  );
}
function Sn(e, t) {
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
var Ln = !1;
function Vd(e) {
  e.updateQueue = {
    baseState: e.memoizedState,
    firstBaseUpdate: null,
    lastBaseUpdate: null,
    shared: { pending: null, interleaved: null, lanes: 0 },
    effects: null,
  };
}
function pv(e, t) {
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
function mn(e, t) {
  return { eventTime: e, lane: t, tag: 0, payload: null, callback: null, next: null };
}
function Gn(e, t, n) {
  var r = e.updateQueue;
  if (r === null) return null;
  if (((r = r.shared), te & 2)) {
    var o = r.pending;
    return o === null ? (t.next = t) : ((t.next = o.next), (o.next = t)), (r.pending = t), Sn(e, n);
  }
  return (
    (o = r.interleaved),
    o === null ? ((t.next = t), Ld(r)) : ((t.next = o.next), (o.next = t)),
    (r.interleaved = t),
    Sn(e, n)
  );
}
function Ma(e, t, n) {
  if (((t = t.updateQueue), t !== null && ((t = t.shared), (n & 4194240) !== 0))) {
    var r = t.lanes;
    (r &= e.pendingLanes), (n |= r), (t.lanes = n), Sd(e, n);
  }
}
function Zp(e, t) {
  var n = e.updateQueue,
    r = e.alternate;
  if (r !== null && ((r = r.updateQueue), n === r)) {
    var o = null,
      i = null;
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
        i === null ? (o = i = s) : (i = i.next = s), (n = n.next);
      } while (n !== null);
      i === null ? (o = i = t) : (i = i.next = t);
    } else o = i = t;
    (n = {
      baseState: r.baseState,
      firstBaseUpdate: o,
      lastBaseUpdate: i,
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
function cl(e, t, n, r) {
  var o = e.updateQueue;
  Ln = !1;
  var i = o.firstBaseUpdate,
    s = o.lastBaseUpdate,
    a = o.shared.pending;
  if (a !== null) {
    o.shared.pending = null;
    var l = a,
      u = l.next;
    (l.next = null), s === null ? (i = u) : (s.next = u), (s = l);
    var c = e.alternate;
    c !== null &&
      ((c = c.updateQueue),
      (a = c.lastBaseUpdate),
      a !== s && (a === null ? (c.firstBaseUpdate = u) : (a.next = u), (c.lastBaseUpdate = l)));
  }
  if (i !== null) {
    var f = o.baseState;
    (s = 0), (c = u = l = null), (a = i);
    do {
      var d = a.lane,
        p = a.eventTime;
      if ((r & d) === d) {
        c !== null &&
          (c = c.next =
            {
              eventTime: p,
              lane: 0,
              tag: a.tag,
              payload: a.payload,
              callback: a.callback,
              next: null,
            });
        e: {
          var y = e,
            m = a;
          switch (((d = t), (p = n), m.tag)) {
            case 1:
              if (((y = m.payload), typeof y == "function")) {
                f = y.call(p, f, d);
                break e;
              }
              f = y;
              break e;
            case 3:
              y.flags = (y.flags & -65537) | 128;
            case 0:
              if (((y = m.payload), (d = typeof y == "function" ? y.call(p, f, d) : y), d == null))
                break e;
              f = ve({}, f, d);
              break e;
            case 2:
              Ln = !0;
          }
        }
        a.callback !== null &&
          a.lane !== 0 &&
          ((e.flags |= 64), (d = o.effects), d === null ? (o.effects = [a]) : d.push(a));
      } else
        (p = {
          eventTime: p,
          lane: d,
          tag: a.tag,
          payload: a.payload,
          callback: a.callback,
          next: null,
        }),
          c === null ? ((u = c = p), (l = f)) : (c = c.next = p),
          (s |= d);
      if (((a = a.next), a === null)) {
        if (((a = o.shared.pending), a === null)) break;
        (d = a), (a = d.next), (d.next = null), (o.lastBaseUpdate = d), (o.shared.pending = null);
      }
    } while (!0);
    if (
      (c === null && (l = f),
      (o.baseState = l),
      (o.firstBaseUpdate = u),
      (o.lastBaseUpdate = c),
      (t = o.shared.interleaved),
      t !== null)
    ) {
      o = t;
      do (s |= o.lane), (o = o.next);
      while (o !== t);
    } else i === null && (o.shared.lanes = 0);
    (Rr |= s), (e.lanes = s), (e.memoizedState = f);
  }
}
function Qp(e, t, n) {
  if (((e = t.effects), (t.effects = null), e !== null))
    for (t = 0; t < e.length; t++) {
      var r = e[t],
        o = r.callback;
      if (o !== null) {
        if (((r.callback = null), (r = n), typeof o != "function")) throw Error(B(191, o));
        o.call(r);
      }
    }
}
var Ps = {},
  Qt = nr(Ps),
  ns = nr(Ps),
  rs = nr(Ps);
function xr(e) {
  if (e === Ps) throw Error(B(174));
  return e;
}
function Od(e, t) {
  switch ((ue(rs, t), ue(ns, e), ue(Qt, Ps), (e = t.nodeType), e)) {
    case 9:
    case 11:
      t = (t = t.documentElement) ? t.namespaceURI : $c(null, "");
      break;
    default:
      (e = e === 8 ? t.parentNode : t),
        (t = e.namespaceURI || null),
        (e = e.tagName),
        (t = $c(t, e));
  }
  he(Qt), ue(Qt, t);
}
function Lo() {
  he(Qt), he(ns), he(rs);
}
function mv(e) {
  xr(rs.current);
  var t = xr(Qt.current),
    n = $c(t, e.type);
  t !== n && (ue(ns, e), ue(Qt, n));
}
function Fd(e) {
  ns.current === e && (he(Qt), he(ns));
}
var me = nr(0);
function fl(e) {
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
var Uu = [];
function zd() {
  for (var e = 0; e < Uu.length; e++) Uu[e]._workInProgressVersionPrimary = null;
  Uu.length = 0;
}
var Aa = Tn.ReactCurrentDispatcher,
  Hu = Tn.ReactCurrentBatchConfig,
  Ar = 0,
  ye = null,
  Ne = null,
  Ae = null,
  dl = !1,
  Li = !1,
  os = 0,
  mk = 0;
function Ue() {
  throw Error(B(321));
}
function $d(e, t) {
  if (t === null) return !1;
  for (var n = 0; n < t.length && n < e.length; n++) if (!$t(e[n], t[n])) return !1;
  return !0;
}
function jd(e, t, n, r, o, i) {
  if (
    ((Ar = i),
    (ye = t),
    (t.memoizedState = null),
    (t.updateQueue = null),
    (t.lanes = 0),
    (Aa.current = e === null || e.memoizedState === null ? xk : wk),
    (e = n(r, o)),
    Li)
  ) {
    i = 0;
    do {
      if (((Li = !1), (os = 0), 25 <= i)) throw Error(B(301));
      (i += 1), (Ae = Ne = null), (t.updateQueue = null), (Aa.current = Sk), (e = n(r, o));
    } while (Li);
  }
  if (
    ((Aa.current = hl),
    (t = Ne !== null && Ne.next !== null),
    (Ar = 0),
    (Ae = Ne = ye = null),
    (dl = !1),
    t)
  )
    throw Error(B(300));
  return e;
}
function Bd() {
  var e = os !== 0;
  return (os = 0), e;
}
function Wt() {
  var e = { memoizedState: null, baseState: null, baseQueue: null, queue: null, next: null };
  return Ae === null ? (ye.memoizedState = Ae = e) : (Ae = Ae.next = e), Ae;
}
function Nt() {
  if (Ne === null) {
    var e = ye.alternate;
    e = e !== null ? e.memoizedState : null;
  } else e = Ne.next;
  var t = Ae === null ? ye.memoizedState : Ae.next;
  if (t !== null) (Ae = t), (Ne = e);
  else {
    if (e === null) throw Error(B(310));
    (Ne = e),
      (e = {
        memoizedState: Ne.memoizedState,
        baseState: Ne.baseState,
        baseQueue: Ne.baseQueue,
        queue: Ne.queue,
        next: null,
      }),
      Ae === null ? (ye.memoizedState = Ae = e) : (Ae = Ae.next = e);
  }
  return Ae;
}
function is(e, t) {
  return typeof t == "function" ? t(e) : t;
}
function Wu(e) {
  var t = Nt(),
    n = t.queue;
  if (n === null) throw Error(B(311));
  n.lastRenderedReducer = e;
  var r = Ne,
    o = r.baseQueue,
    i = n.pending;
  if (i !== null) {
    if (o !== null) {
      var s = o.next;
      (o.next = i.next), (i.next = s);
    }
    (r.baseQueue = o = i), (n.pending = null);
  }
  if (o !== null) {
    (i = o.next), (r = r.baseState);
    var a = (s = null),
      l = null,
      u = i;
    do {
      var c = u.lane;
      if ((Ar & c) === c)
        l !== null &&
          (l = l.next =
            {
              lane: 0,
              action: u.action,
              hasEagerState: u.hasEagerState,
              eagerState: u.eagerState,
              next: null,
            }),
          (r = u.hasEagerState ? u.eagerState : e(r, u.action));
      else {
        var f = {
          lane: c,
          action: u.action,
          hasEagerState: u.hasEagerState,
          eagerState: u.eagerState,
          next: null,
        };
        l === null ? ((a = l = f), (s = r)) : (l = l.next = f), (ye.lanes |= c), (Rr |= c);
      }
      u = u.next;
    } while (u !== null && u !== i);
    l === null ? (s = r) : (l.next = a),
      $t(r, t.memoizedState) || (nt = !0),
      (t.memoizedState = r),
      (t.baseState = s),
      (t.baseQueue = l),
      (n.lastRenderedState = r);
  }
  if (((e = n.interleaved), e !== null)) {
    o = e;
    do (i = o.lane), (ye.lanes |= i), (Rr |= i), (o = o.next);
    while (o !== e);
  } else o === null && (n.lanes = 0);
  return [t.memoizedState, n.dispatch];
}
function Gu(e) {
  var t = Nt(),
    n = t.queue;
  if (n === null) throw Error(B(311));
  n.lastRenderedReducer = e;
  var r = n.dispatch,
    o = n.pending,
    i = t.memoizedState;
  if (o !== null) {
    n.pending = null;
    var s = (o = o.next);
    do (i = e(i, s.action)), (s = s.next);
    while (s !== o);
    $t(i, t.memoizedState) || (nt = !0),
      (t.memoizedState = i),
      t.baseQueue === null && (t.baseState = i),
      (n.lastRenderedState = i);
  }
  return [i, r];
}
function gv() {}
function yv(e, t) {
  var n = ye,
    r = Nt(),
    o = t(),
    i = !$t(r.memoizedState, o);
  if (
    (i && ((r.memoizedState = o), (nt = !0)),
    (r = r.queue),
    Ud(wv.bind(null, n, r, e), [e]),
    r.getSnapshot !== t || i || (Ae !== null && Ae.memoizedState.tag & 1))
  ) {
    if (((n.flags |= 2048), ss(9, xv.bind(null, n, r, o, t), void 0, null), De === null))
      throw Error(B(349));
    Ar & 30 || vv(n, t, o);
  }
  return o;
}
function vv(e, t, n) {
  (e.flags |= 16384),
    (e = { getSnapshot: t, value: n }),
    (t = ye.updateQueue),
    t === null
      ? ((t = { lastEffect: null, stores: null }), (ye.updateQueue = t), (t.stores = [e]))
      : ((n = t.stores), n === null ? (t.stores = [e]) : n.push(e));
}
function xv(e, t, n, r) {
  (t.value = n), (t.getSnapshot = r), Sv(t) && Ev(e);
}
function wv(e, t, n) {
  return n(function () {
    Sv(t) && Ev(e);
  });
}
function Sv(e) {
  var t = e.getSnapshot;
  e = e.value;
  try {
    var n = t();
    return !$t(e, n);
  } catch {
    return !0;
  }
}
function Ev(e) {
  var t = Sn(e, 1);
  t !== null && Ft(t, e, 1, -1);
}
function qp(e) {
  var t = Wt();
  return (
    typeof e == "function" && (e = e()),
    (t.memoizedState = t.baseState = e),
    (e = {
      pending: null,
      interleaved: null,
      lanes: 0,
      dispatch: null,
      lastRenderedReducer: is,
      lastRenderedState: e,
    }),
    (t.queue = e),
    (e = e.dispatch = vk.bind(null, ye, e)),
    [t.memoizedState, e]
  );
}
function ss(e, t, n, r) {
  return (
    (e = { tag: e, create: t, destroy: n, deps: r, next: null }),
    (t = ye.updateQueue),
    t === null
      ? ((t = { lastEffect: null, stores: null }),
        (ye.updateQueue = t),
        (t.lastEffect = e.next = e))
      : ((n = t.lastEffect),
        n === null
          ? (t.lastEffect = e.next = e)
          : ((r = n.next), (n.next = e), (e.next = r), (t.lastEffect = e))),
    e
  );
}
function Cv() {
  return Nt().memoizedState;
}
function Ra(e, t, n, r) {
  var o = Wt();
  (ye.flags |= e), (o.memoizedState = ss(1 | t, n, void 0, r === void 0 ? null : r));
}
function Kl(e, t, n, r) {
  var o = Nt();
  r = r === void 0 ? null : r;
  var i = void 0;
  if (Ne !== null) {
    var s = Ne.memoizedState;
    if (((i = s.destroy), r !== null && $d(r, s.deps))) {
      o.memoizedState = ss(t, n, i, r);
      return;
    }
  }
  (ye.flags |= e), (o.memoizedState = ss(1 | t, n, i, r));
}
function Jp(e, t) {
  return Ra(8390656, 8, e, t);
}
function Ud(e, t) {
  return Kl(2048, 8, e, t);
}
function bv(e, t) {
  return Kl(4, 2, e, t);
}
function kv(e, t) {
  return Kl(4, 4, e, t);
}
function _v(e, t) {
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
function Tv(e, t, n) {
  return (n = n != null ? n.concat([e]) : null), Kl(4, 4, _v.bind(null, t, e), n);
}
function Hd() {}
function Nv(e, t) {
  var n = Nt();
  t = t === void 0 ? null : t;
  var r = n.memoizedState;
  return r !== null && t !== null && $d(t, r[1]) ? r[0] : ((n.memoizedState = [e, t]), e);
}
function Pv(e, t) {
  var n = Nt();
  t = t === void 0 ? null : t;
  var r = n.memoizedState;
  return r !== null && t !== null && $d(t, r[1])
    ? r[0]
    : ((e = e()), (n.memoizedState = [e, t]), e);
}
function Mv(e, t, n) {
  return Ar & 21
    ? ($t(n, t) || ((n = L0()), (ye.lanes |= n), (Rr |= n), (e.baseState = !0)), t)
    : (e.baseState && ((e.baseState = !1), (nt = !0)), (e.memoizedState = n));
}
function gk(e, t) {
  var n = ie;
  (ie = n !== 0 && 4 > n ? n : 4), e(!0);
  var r = Hu.transition;
  Hu.transition = {};
  try {
    e(!1), t();
  } finally {
    (ie = n), (Hu.transition = r);
  }
}
function Av() {
  return Nt().memoizedState;
}
function yk(e, t, n) {
  var r = Yn(e);
  if (((n = { lane: r, action: n, hasEagerState: !1, eagerState: null, next: null }), Rv(e)))
    Dv(t, n);
  else if (((n = hv(e, t, n, r)), n !== null)) {
    var o = Qe();
    Ft(n, e, r, o), Iv(n, t, r);
  }
}
function vk(e, t, n) {
  var r = Yn(e),
    o = { lane: r, action: n, hasEagerState: !1, eagerState: null, next: null };
  if (Rv(e)) Dv(t, o);
  else {
    var i = e.alternate;
    if (e.lanes === 0 && (i === null || i.lanes === 0) && ((i = t.lastRenderedReducer), i !== null))
      try {
        var s = t.lastRenderedState,
          a = i(s, n);
        if (((o.hasEagerState = !0), (o.eagerState = a), $t(a, s))) {
          var l = t.interleaved;
          l === null ? ((o.next = o), Ld(t)) : ((o.next = l.next), (l.next = o)),
            (t.interleaved = o);
          return;
        }
      } catch {
      } finally {
      }
    (n = hv(e, t, o, r)), n !== null && ((o = Qe()), Ft(n, e, r, o), Iv(n, t, r));
  }
}
function Rv(e) {
  var t = e.alternate;
  return e === ye || (t !== null && t === ye);
}
function Dv(e, t) {
  Li = dl = !0;
  var n = e.pending;
  n === null ? (t.next = t) : ((t.next = n.next), (n.next = t)), (e.pending = t);
}
function Iv(e, t, n) {
  if (n & 4194240) {
    var r = t.lanes;
    (r &= e.pendingLanes), (n |= r), (t.lanes = n), Sd(e, n);
  }
}
var hl = {
    readContext: Tt,
    useCallback: Ue,
    useContext: Ue,
    useEffect: Ue,
    useImperativeHandle: Ue,
    useInsertionEffect: Ue,
    useLayoutEffect: Ue,
    useMemo: Ue,
    useReducer: Ue,
    useRef: Ue,
    useState: Ue,
    useDebugValue: Ue,
    useDeferredValue: Ue,
    useTransition: Ue,
    useMutableSource: Ue,
    useSyncExternalStore: Ue,
    useId: Ue,
    unstable_isNewReconciler: !1,
  },
  xk = {
    readContext: Tt,
    useCallback: function (e, t) {
      return (Wt().memoizedState = [e, t === void 0 ? null : t]), e;
    },
    useContext: Tt,
    useEffect: Jp,
    useImperativeHandle: function (e, t, n) {
      return (n = n != null ? n.concat([e]) : null), Ra(4194308, 4, _v.bind(null, t, e), n);
    },
    useLayoutEffect: function (e, t) {
      return Ra(4194308, 4, e, t);
    },
    useInsertionEffect: function (e, t) {
      return Ra(4, 2, e, t);
    },
    useMemo: function (e, t) {
      var n = Wt();
      return (t = t === void 0 ? null : t), (e = e()), (n.memoizedState = [e, t]), e;
    },
    useReducer: function (e, t, n) {
      var r = Wt();
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
        (e = e.dispatch = yk.bind(null, ye, e)),
        [r.memoizedState, e]
      );
    },
    useRef: function (e) {
      var t = Wt();
      return (e = { current: e }), (t.memoizedState = e);
    },
    useState: qp,
    useDebugValue: Hd,
    useDeferredValue: function (e) {
      return (Wt().memoizedState = e);
    },
    useTransition: function () {
      var e = qp(!1),
        t = e[0];
      return (e = gk.bind(null, e[1])), (Wt().memoizedState = e), [t, e];
    },
    useMutableSource: function () {},
    useSyncExternalStore: function (e, t, n) {
      var r = ye,
        o = Wt();
      if (pe) {
        if (n === void 0) throw Error(B(407));
        n = n();
      } else {
        if (((n = t()), De === null)) throw Error(B(349));
        Ar & 30 || vv(r, t, n);
      }
      o.memoizedState = n;
      var i = { value: n, getSnapshot: t };
      return (
        (o.queue = i),
        Jp(wv.bind(null, r, i, e), [e]),
        (r.flags |= 2048),
        ss(9, xv.bind(null, r, i, n, t), void 0, null),
        n
      );
    },
    useId: function () {
      var e = Wt(),
        t = De.identifierPrefix;
      if (pe) {
        var n = hn,
          r = dn;
        (n = (r & ~(1 << (32 - Ot(r) - 1))).toString(32) + n),
          (t = ":" + t + "R" + n),
          (n = os++),
          0 < n && (t += "H" + n.toString(32)),
          (t += ":");
      } else (n = mk++), (t = ":" + t + "r" + n.toString(32) + ":");
      return (e.memoizedState = t);
    },
    unstable_isNewReconciler: !1,
  },
  wk = {
    readContext: Tt,
    useCallback: Nv,
    useContext: Tt,
    useEffect: Ud,
    useImperativeHandle: Tv,
    useInsertionEffect: bv,
    useLayoutEffect: kv,
    useMemo: Pv,
    useReducer: Wu,
    useRef: Cv,
    useState: function () {
      return Wu(is);
    },
    useDebugValue: Hd,
    useDeferredValue: function (e) {
      var t = Nt();
      return Mv(t, Ne.memoizedState, e);
    },
    useTransition: function () {
      var e = Wu(is)[0],
        t = Nt().memoizedState;
      return [e, t];
    },
    useMutableSource: gv,
    useSyncExternalStore: yv,
    useId: Av,
    unstable_isNewReconciler: !1,
  },
  Sk = {
    readContext: Tt,
    useCallback: Nv,
    useContext: Tt,
    useEffect: Ud,
    useImperativeHandle: Tv,
    useInsertionEffect: bv,
    useLayoutEffect: kv,
    useMemo: Pv,
    useReducer: Gu,
    useRef: Cv,
    useState: function () {
      return Gu(is);
    },
    useDebugValue: Hd,
    useDeferredValue: function (e) {
      var t = Nt();
      return Ne === null ? (t.memoizedState = e) : Mv(t, Ne.memoizedState, e);
    },
    useTransition: function () {
      var e = Gu(is)[0],
        t = Nt().memoizedState;
      return [e, t];
    },
    useMutableSource: gv,
    useSyncExternalStore: yv,
    useId: Av,
    unstable_isNewReconciler: !1,
  };
function Rt(e, t) {
  if (e && e.defaultProps) {
    (t = ve({}, t)), (e = e.defaultProps);
    for (var n in e) t[n] === void 0 && (t[n] = e[n]);
    return t;
  }
  return t;
}
function lf(e, t, n, r) {
  (t = e.memoizedState),
    (n = n(r, t)),
    (n = n == null ? t : ve({}, t, n)),
    (e.memoizedState = n),
    e.lanes === 0 && (e.updateQueue.baseState = n);
}
var Yl = {
  isMounted: function (e) {
    return (e = e._reactInternals) ? Fr(e) === e : !1;
  },
  enqueueSetState: function (e, t, n) {
    e = e._reactInternals;
    var r = Qe(),
      o = Yn(e),
      i = mn(r, o);
    (i.payload = t),
      n != null && (i.callback = n),
      (t = Gn(e, i, o)),
      t !== null && (Ft(t, e, o, r), Ma(t, e, o));
  },
  enqueueReplaceState: function (e, t, n) {
    e = e._reactInternals;
    var r = Qe(),
      o = Yn(e),
      i = mn(r, o);
    (i.tag = 1),
      (i.payload = t),
      n != null && (i.callback = n),
      (t = Gn(e, i, o)),
      t !== null && (Ft(t, e, o, r), Ma(t, e, o));
  },
  enqueueForceUpdate: function (e, t) {
    e = e._reactInternals;
    var n = Qe(),
      r = Yn(e),
      o = mn(n, r);
    (o.tag = 2),
      t != null && (o.callback = t),
      (t = Gn(e, o, r)),
      t !== null && (Ft(t, e, r, n), Ma(t, e, r));
  },
};
function em(e, t, n, r, o, i, s) {
  return (
    (e = e.stateNode),
    typeof e.shouldComponentUpdate == "function"
      ? e.shouldComponentUpdate(r, i, s)
      : t.prototype && t.prototype.isPureReactComponent
        ? !qi(n, r) || !qi(o, i)
        : !0
  );
}
function Lv(e, t, n) {
  var r = !1,
    o = qn,
    i = t.contextType;
  return (
    typeof i == "object" && i !== null
      ? (i = Tt(i))
      : ((o = it(t) ? Pr : Ke.current),
        (r = t.contextTypes),
        (i = (r = r != null) ? Ro(e, o) : qn)),
    (t = new t(n, i)),
    (e.memoizedState = t.state !== null && t.state !== void 0 ? t.state : null),
    (t.updater = Yl),
    (e.stateNode = t),
    (t._reactInternals = e),
    r &&
      ((e = e.stateNode),
      (e.__reactInternalMemoizedUnmaskedChildContext = o),
      (e.__reactInternalMemoizedMaskedChildContext = i)),
    t
  );
}
function tm(e, t, n, r) {
  (e = t.state),
    typeof t.componentWillReceiveProps == "function" && t.componentWillReceiveProps(n, r),
    typeof t.UNSAFE_componentWillReceiveProps == "function" &&
      t.UNSAFE_componentWillReceiveProps(n, r),
    t.state !== e && Yl.enqueueReplaceState(t, t.state, null);
}
function uf(e, t, n, r) {
  var o = e.stateNode;
  (o.props = n), (o.state = e.memoizedState), (o.refs = {}), Vd(e);
  var i = t.contextType;
  typeof i == "object" && i !== null
    ? (o.context = Tt(i))
    : ((i = it(t) ? Pr : Ke.current), (o.context = Ro(e, i))),
    (o.state = e.memoizedState),
    (i = t.getDerivedStateFromProps),
    typeof i == "function" && (lf(e, t, i, n), (o.state = e.memoizedState)),
    typeof t.getDerivedStateFromProps == "function" ||
      typeof o.getSnapshotBeforeUpdate == "function" ||
      (typeof o.UNSAFE_componentWillMount != "function" &&
        typeof o.componentWillMount != "function") ||
      ((t = o.state),
      typeof o.componentWillMount == "function" && o.componentWillMount(),
      typeof o.UNSAFE_componentWillMount == "function" && o.UNSAFE_componentWillMount(),
      t !== o.state && Yl.enqueueReplaceState(o, o.state, null),
      cl(e, n, o, r),
      (o.state = e.memoizedState)),
    typeof o.componentDidMount == "function" && (e.flags |= 4194308);
}
function Vo(e, t) {
  try {
    var n = "",
      r = t;
    do (n += XC(r)), (r = r.return);
    while (r);
    var o = n;
  } catch (i) {
    o =
      `
Error generating stack: ` +
      i.message +
      `
` +
      i.stack;
  }
  return { value: e, source: t, stack: o, digest: null };
}
function Ku(e, t, n) {
  return { value: e, source: null, stack: n ?? null, digest: t ?? null };
}
function cf(e, t) {
  try {
    console.error(t.value);
  } catch (n) {
    setTimeout(function () {
      throw n;
    });
  }
}
var Ek = typeof WeakMap == "function" ? WeakMap : Map;
function Vv(e, t, n) {
  (n = mn(-1, n)), (n.tag = 3), (n.payload = { element: null });
  var r = t.value;
  return (
    (n.callback = function () {
      ml || ((ml = !0), (wf = r)), cf(e, t);
    }),
    n
  );
}
function Ov(e, t, n) {
  (n = mn(-1, n)), (n.tag = 3);
  var r = e.type.getDerivedStateFromError;
  if (typeof r == "function") {
    var o = t.value;
    (n.payload = function () {
      return r(o);
    }),
      (n.callback = function () {
        cf(e, t);
      });
  }
  var i = e.stateNode;
  return (
    i !== null &&
      typeof i.componentDidCatch == "function" &&
      (n.callback = function () {
        cf(e, t), typeof r != "function" && (Kn === null ? (Kn = new Set([this])) : Kn.add(this));
        var s = t.stack;
        this.componentDidCatch(t.value, { componentStack: s !== null ? s : "" });
      }),
    n
  );
}
function nm(e, t, n) {
  var r = e.pingCache;
  if (r === null) {
    r = e.pingCache = new Ek();
    var o = new Set();
    r.set(t, o);
  } else (o = r.get(t)), o === void 0 && ((o = new Set()), r.set(t, o));
  o.has(n) || (o.add(n), (e = Vk.bind(null, e, t, n)), t.then(e, e));
}
function rm(e) {
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
function om(e, t, n, r, o) {
  return e.mode & 1
    ? ((e.flags |= 65536), (e.lanes = o), e)
    : (e === t
        ? (e.flags |= 65536)
        : ((e.flags |= 128),
          (n.flags |= 131072),
          (n.flags &= -52805),
          n.tag === 1 &&
            (n.alternate === null ? (n.tag = 17) : ((t = mn(-1, 1)), (t.tag = 2), Gn(n, t, 1))),
          (n.lanes |= 1)),
      e);
}
var Ck = Tn.ReactCurrentOwner,
  nt = !1;
function Ze(e, t, n, r) {
  t.child = e === null ? dv(t, null, n, r) : Io(t, e.child, n, r);
}
function im(e, t, n, r, o) {
  n = n.render;
  var i = t.ref;
  return (
    Co(t, o),
    (r = jd(e, t, n, r, i, o)),
    (n = Bd()),
    e !== null && !nt
      ? ((t.updateQueue = e.updateQueue), (t.flags &= -2053), (e.lanes &= ~o), En(e, t, o))
      : (pe && n && Pd(t), (t.flags |= 1), Ze(e, t, r, o), t.child)
  );
}
function sm(e, t, n, r, o) {
  if (e === null) {
    var i = n.type;
    return typeof i == "function" &&
      !qd(i) &&
      i.defaultProps === void 0 &&
      n.compare === null &&
      n.defaultProps === void 0
      ? ((t.tag = 15), (t.type = i), Fv(e, t, i, r, o))
      : ((e = Va(n.type, null, r, t, t.mode, o)), (e.ref = t.ref), (e.return = t), (t.child = e));
  }
  if (((i = e.child), !(e.lanes & o))) {
    var s = i.memoizedProps;
    if (((n = n.compare), (n = n !== null ? n : qi), n(s, r) && e.ref === t.ref))
      return En(e, t, o);
  }
  return (t.flags |= 1), (e = Xn(i, r)), (e.ref = t.ref), (e.return = t), (t.child = e);
}
function Fv(e, t, n, r, o) {
  if (e !== null) {
    var i = e.memoizedProps;
    if (qi(i, r) && e.ref === t.ref)
      if (((nt = !1), (t.pendingProps = r = i), (e.lanes & o) !== 0)) e.flags & 131072 && (nt = !0);
      else return (t.lanes = e.lanes), En(e, t, o);
  }
  return ff(e, t, n, r, o);
}
function zv(e, t, n) {
  var r = t.pendingProps,
    o = r.children,
    i = e !== null ? e.memoizedState : null;
  if (r.mode === "hidden")
    if (!(t.mode & 1))
      (t.memoizedState = { baseLanes: 0, cachePool: null, transitions: null }),
        ue(co, ut),
        (ut |= n);
    else {
      if (!(n & 1073741824))
        return (
          (e = i !== null ? i.baseLanes | n : n),
          (t.lanes = t.childLanes = 1073741824),
          (t.memoizedState = { baseLanes: e, cachePool: null, transitions: null }),
          (t.updateQueue = null),
          ue(co, ut),
          (ut |= e),
          null
        );
      (t.memoizedState = { baseLanes: 0, cachePool: null, transitions: null }),
        (r = i !== null ? i.baseLanes : n),
        ue(co, ut),
        (ut |= r);
    }
  else
    i !== null ? ((r = i.baseLanes | n), (t.memoizedState = null)) : (r = n), ue(co, ut), (ut |= r);
  return Ze(e, t, o, n), t.child;
}
function $v(e, t) {
  var n = t.ref;
  ((e === null && n !== null) || (e !== null && e.ref !== n)) &&
    ((t.flags |= 512), (t.flags |= 2097152));
}
function ff(e, t, n, r, o) {
  var i = it(n) ? Pr : Ke.current;
  return (
    (i = Ro(t, i)),
    Co(t, o),
    (n = jd(e, t, n, r, i, o)),
    (r = Bd()),
    e !== null && !nt
      ? ((t.updateQueue = e.updateQueue), (t.flags &= -2053), (e.lanes &= ~o), En(e, t, o))
      : (pe && r && Pd(t), (t.flags |= 1), Ze(e, t, n, o), t.child)
  );
}
function am(e, t, n, r, o) {
  if (it(n)) {
    var i = !0;
    il(t);
  } else i = !1;
  if ((Co(t, o), t.stateNode === null)) Da(e, t), Lv(t, n, r), uf(t, n, r, o), (r = !0);
  else if (e === null) {
    var s = t.stateNode,
      a = t.memoizedProps;
    s.props = a;
    var l = s.context,
      u = n.contextType;
    typeof u == "object" && u !== null
      ? (u = Tt(u))
      : ((u = it(n) ? Pr : Ke.current), (u = Ro(t, u)));
    var c = n.getDerivedStateFromProps,
      f = typeof c == "function" || typeof s.getSnapshotBeforeUpdate == "function";
    f ||
      (typeof s.UNSAFE_componentWillReceiveProps != "function" &&
        typeof s.componentWillReceiveProps != "function") ||
      ((a !== r || l !== u) && tm(t, s, r, u)),
      (Ln = !1);
    var d = t.memoizedState;
    (s.state = d),
      cl(t, r, s, o),
      (l = t.memoizedState),
      a !== r || d !== l || ot.current || Ln
        ? (typeof c == "function" && (lf(t, n, c, r), (l = t.memoizedState)),
          (a = Ln || em(t, n, a, r, d, l, u))
            ? (f ||
                (typeof s.UNSAFE_componentWillMount != "function" &&
                  typeof s.componentWillMount != "function") ||
                (typeof s.componentWillMount == "function" && s.componentWillMount(),
                typeof s.UNSAFE_componentWillMount == "function" && s.UNSAFE_componentWillMount()),
              typeof s.componentDidMount == "function" && (t.flags |= 4194308))
            : (typeof s.componentDidMount == "function" && (t.flags |= 4194308),
              (t.memoizedProps = r),
              (t.memoizedState = l)),
          (s.props = r),
          (s.state = l),
          (s.context = u),
          (r = a))
        : (typeof s.componentDidMount == "function" && (t.flags |= 4194308), (r = !1));
  } else {
    (s = t.stateNode),
      pv(e, t),
      (a = t.memoizedProps),
      (u = t.type === t.elementType ? a : Rt(t.type, a)),
      (s.props = u),
      (f = t.pendingProps),
      (d = s.context),
      (l = n.contextType),
      typeof l == "object" && l !== null
        ? (l = Tt(l))
        : ((l = it(n) ? Pr : Ke.current), (l = Ro(t, l)));
    var p = n.getDerivedStateFromProps;
    (c = typeof p == "function" || typeof s.getSnapshotBeforeUpdate == "function") ||
      (typeof s.UNSAFE_componentWillReceiveProps != "function" &&
        typeof s.componentWillReceiveProps != "function") ||
      ((a !== f || d !== l) && tm(t, s, r, l)),
      (Ln = !1),
      (d = t.memoizedState),
      (s.state = d),
      cl(t, r, s, o);
    var y = t.memoizedState;
    a !== f || d !== y || ot.current || Ln
      ? (typeof p == "function" && (lf(t, n, p, r), (y = t.memoizedState)),
        (u = Ln || em(t, n, u, r, d, y, l) || !1)
          ? (c ||
              (typeof s.UNSAFE_componentWillUpdate != "function" &&
                typeof s.componentWillUpdate != "function") ||
              (typeof s.componentWillUpdate == "function" && s.componentWillUpdate(r, y, l),
              typeof s.UNSAFE_componentWillUpdate == "function" &&
                s.UNSAFE_componentWillUpdate(r, y, l)),
            typeof s.componentDidUpdate == "function" && (t.flags |= 4),
            typeof s.getSnapshotBeforeUpdate == "function" && (t.flags |= 1024))
          : (typeof s.componentDidUpdate != "function" ||
              (a === e.memoizedProps && d === e.memoizedState) ||
              (t.flags |= 4),
            typeof s.getSnapshotBeforeUpdate != "function" ||
              (a === e.memoizedProps && d === e.memoizedState) ||
              (t.flags |= 1024),
            (t.memoizedProps = r),
            (t.memoizedState = y)),
        (s.props = r),
        (s.state = y),
        (s.context = l),
        (r = u))
      : (typeof s.componentDidUpdate != "function" ||
          (a === e.memoizedProps && d === e.memoizedState) ||
          (t.flags |= 4),
        typeof s.getSnapshotBeforeUpdate != "function" ||
          (a === e.memoizedProps && d === e.memoizedState) ||
          (t.flags |= 1024),
        (r = !1));
  }
  return df(e, t, n, r, i, o);
}
function df(e, t, n, r, o, i) {
  $v(e, t);
  var s = (t.flags & 128) !== 0;
  if (!r && !s) return o && Gp(t, n, !1), En(e, t, i);
  (r = t.stateNode), (Ck.current = t);
  var a = s && typeof n.getDerivedStateFromError != "function" ? null : r.render();
  return (
    (t.flags |= 1),
    e !== null && s
      ? ((t.child = Io(t, e.child, null, i)), (t.child = Io(t, null, a, i)))
      : Ze(e, t, a, i),
    (t.memoizedState = r.state),
    o && Gp(t, n, !0),
    t.child
  );
}
function jv(e) {
  var t = e.stateNode;
  t.pendingContext
    ? Wp(e, t.pendingContext, t.pendingContext !== t.context)
    : t.context && Wp(e, t.context, !1),
    Od(e, t.containerInfo);
}
function lm(e, t, n, r, o) {
  return Do(), Ad(o), (t.flags |= 256), Ze(e, t, n, r), t.child;
}
var hf = { dehydrated: null, treeContext: null, retryLane: 0 };
function pf(e) {
  return { baseLanes: e, cachePool: null, transitions: null };
}
function Bv(e, t, n) {
  var r = t.pendingProps,
    o = me.current,
    i = !1,
    s = (t.flags & 128) !== 0,
    a;
  if (
    ((a = s) || (a = e !== null && e.memoizedState === null ? !1 : (o & 2) !== 0),
    a ? ((i = !0), (t.flags &= -129)) : (e === null || e.memoizedState !== null) && (o |= 1),
    ue(me, o & 1),
    e === null)
  )
    return (
      sf(t),
      (e = t.memoizedState),
      e !== null && ((e = e.dehydrated), e !== null)
        ? (t.mode & 1 ? (e.data === "$!" ? (t.lanes = 8) : (t.lanes = 1073741824)) : (t.lanes = 1),
          null)
        : ((s = r.children),
          (e = r.fallback),
          i
            ? ((r = t.mode),
              (i = t.child),
              (s = { mode: "hidden", children: s }),
              !(r & 1) && i !== null
                ? ((i.childLanes = 0), (i.pendingProps = s))
                : (i = Ql(s, r, 0, null)),
              (e = kr(e, r, n, null)),
              (i.return = t),
              (e.return = t),
              (i.sibling = e),
              (t.child = i),
              (t.child.memoizedState = pf(n)),
              (t.memoizedState = hf),
              e)
            : Wd(t, s))
    );
  if (((o = e.memoizedState), o !== null && ((a = o.dehydrated), a !== null)))
    return bk(e, t, s, r, a, o, n);
  if (i) {
    (i = r.fallback), (s = t.mode), (o = e.child), (a = o.sibling);
    var l = { mode: "hidden", children: r.children };
    return (
      !(s & 1) && t.child !== o
        ? ((r = t.child), (r.childLanes = 0), (r.pendingProps = l), (t.deletions = null))
        : ((r = Xn(o, l)), (r.subtreeFlags = o.subtreeFlags & 14680064)),
      a !== null ? (i = Xn(a, i)) : ((i = kr(i, s, n, null)), (i.flags |= 2)),
      (i.return = t),
      (r.return = t),
      (r.sibling = i),
      (t.child = r),
      (r = i),
      (i = t.child),
      (s = e.child.memoizedState),
      (s =
        s === null
          ? pf(n)
          : { baseLanes: s.baseLanes | n, cachePool: null, transitions: s.transitions }),
      (i.memoizedState = s),
      (i.childLanes = e.childLanes & ~n),
      (t.memoizedState = hf),
      r
    );
  }
  return (
    (i = e.child),
    (e = i.sibling),
    (r = Xn(i, { mode: "visible", children: r.children })),
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
function Wd(e, t) {
  return (t = Ql({ mode: "visible", children: t }, e.mode, 0, null)), (t.return = e), (e.child = t);
}
function ta(e, t, n, r) {
  return (
    r !== null && Ad(r),
    Io(t, e.child, null, n),
    (e = Wd(t, t.pendingProps.children)),
    (e.flags |= 2),
    (t.memoizedState = null),
    e
  );
}
function bk(e, t, n, r, o, i, s) {
  if (n)
    return t.flags & 256
      ? ((t.flags &= -257), (r = Ku(Error(B(422)))), ta(e, t, s, r))
      : t.memoizedState !== null
        ? ((t.child = e.child), (t.flags |= 128), null)
        : ((i = r.fallback),
          (o = t.mode),
          (r = Ql({ mode: "visible", children: r.children }, o, 0, null)),
          (i = kr(i, o, s, null)),
          (i.flags |= 2),
          (r.return = t),
          (i.return = t),
          (r.sibling = i),
          (t.child = r),
          t.mode & 1 && Io(t, e.child, null, s),
          (t.child.memoizedState = pf(s)),
          (t.memoizedState = hf),
          i);
  if (!(t.mode & 1)) return ta(e, t, s, null);
  if (o.data === "$!") {
    if (((r = o.nextSibling && o.nextSibling.dataset), r)) var a = r.dgst;
    return (r = a), (i = Error(B(419))), (r = Ku(i, r, void 0)), ta(e, t, s, r);
  }
  if (((a = (s & e.childLanes) !== 0), nt || a)) {
    if (((r = De), r !== null)) {
      switch (s & -s) {
        case 4:
          o = 2;
          break;
        case 16:
          o = 8;
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
          o = 32;
          break;
        case 536870912:
          o = 268435456;
          break;
        default:
          o = 0;
      }
      (o = o & (r.suspendedLanes | s) ? 0 : o),
        o !== 0 && o !== i.retryLane && ((i.retryLane = o), Sn(e, o), Ft(r, e, o, -1));
    }
    return Qd(), (r = Ku(Error(B(421)))), ta(e, t, s, r);
  }
  return o.data === "$?"
    ? ((t.flags |= 128), (t.child = e.child), (t = Ok.bind(null, e)), (o._reactRetry = t), null)
    : ((e = i.treeContext),
      (ct = Wn(o.nextSibling)),
      (ft = t),
      (pe = !0),
      (Lt = null),
      e !== null &&
        ((wt[St++] = dn),
        (wt[St++] = hn),
        (wt[St++] = Mr),
        (dn = e.id),
        (hn = e.overflow),
        (Mr = t)),
      (t = Wd(t, r.children)),
      (t.flags |= 4096),
      t);
}
function um(e, t, n) {
  e.lanes |= t;
  var r = e.alternate;
  r !== null && (r.lanes |= t), af(e.return, t, n);
}
function Yu(e, t, n, r, o) {
  var i = e.memoizedState;
  i === null
    ? (e.memoizedState = {
        isBackwards: t,
        rendering: null,
        renderingStartTime: 0,
        last: r,
        tail: n,
        tailMode: o,
      })
    : ((i.isBackwards = t),
      (i.rendering = null),
      (i.renderingStartTime = 0),
      (i.last = r),
      (i.tail = n),
      (i.tailMode = o));
}
function Uv(e, t, n) {
  var r = t.pendingProps,
    o = r.revealOrder,
    i = r.tail;
  if ((Ze(e, t, r.children, n), (r = me.current), r & 2)) (r = (r & 1) | 2), (t.flags |= 128);
  else {
    if (e !== null && e.flags & 128)
      e: for (e = t.child; e !== null; ) {
        if (e.tag === 13) e.memoizedState !== null && um(e, n, t);
        else if (e.tag === 19) um(e, n, t);
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
  if ((ue(me, r), !(t.mode & 1))) t.memoizedState = null;
  else
    switch (o) {
      case "forwards":
        for (n = t.child, o = null; n !== null; )
          (e = n.alternate), e !== null && fl(e) === null && (o = n), (n = n.sibling);
        (n = o),
          n === null ? ((o = t.child), (t.child = null)) : ((o = n.sibling), (n.sibling = null)),
          Yu(t, !1, o, n, i);
        break;
      case "backwards":
        for (n = null, o = t.child, t.child = null; o !== null; ) {
          if (((e = o.alternate), e !== null && fl(e) === null)) {
            t.child = o;
            break;
          }
          (e = o.sibling), (o.sibling = n), (n = o), (o = e);
        }
        Yu(t, !0, n, null, i);
        break;
      case "together":
        Yu(t, !1, null, null, void 0);
        break;
      default:
        t.memoizedState = null;
    }
  return t.child;
}
function Da(e, t) {
  !(t.mode & 1) && e !== null && ((e.alternate = null), (t.alternate = null), (t.flags |= 2));
}
function En(e, t, n) {
  if ((e !== null && (t.dependencies = e.dependencies), (Rr |= t.lanes), !(n & t.childLanes)))
    return null;
  if (e !== null && t.child !== e.child) throw Error(B(153));
  if (t.child !== null) {
    for (e = t.child, n = Xn(e, e.pendingProps), t.child = n, n.return = t; e.sibling !== null; )
      (e = e.sibling), (n = n.sibling = Xn(e, e.pendingProps)), (n.return = t);
    n.sibling = null;
  }
  return t.child;
}
function kk(e, t, n) {
  switch (t.tag) {
    case 3:
      jv(t), Do();
      break;
    case 5:
      mv(t);
      break;
    case 1:
      it(t.type) && il(t);
      break;
    case 4:
      Od(t, t.stateNode.containerInfo);
      break;
    case 10:
      var r = t.type._context,
        o = t.memoizedProps.value;
      ue(ll, r._currentValue), (r._currentValue = o);
      break;
    case 13:
      if (((r = t.memoizedState), r !== null))
        return r.dehydrated !== null
          ? (ue(me, me.current & 1), (t.flags |= 128), null)
          : n & t.child.childLanes
            ? Bv(e, t, n)
            : (ue(me, me.current & 1), (e = En(e, t, n)), e !== null ? e.sibling : null);
      ue(me, me.current & 1);
      break;
    case 19:
      if (((r = (n & t.childLanes) !== 0), e.flags & 128)) {
        if (r) return Uv(e, t, n);
        t.flags |= 128;
      }
      if (
        ((o = t.memoizedState),
        o !== null && ((o.rendering = null), (o.tail = null), (o.lastEffect = null)),
        ue(me, me.current),
        r)
      )
        break;
      return null;
    case 22:
    case 23:
      return (t.lanes = 0), zv(e, t, n);
  }
  return En(e, t, n);
}
var Hv, mf, Wv, Gv;
Hv = function (e, t) {
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
mf = function () {};
Wv = function (e, t, n, r) {
  var o = e.memoizedProps;
  if (o !== r) {
    (e = t.stateNode), xr(Qt.current);
    var i = null;
    switch (n) {
      case "input":
        (o = Vc(e, o)), (r = Vc(e, r)), (i = []);
        break;
      case "select":
        (o = ve({}, o, { value: void 0 })), (r = ve({}, r, { value: void 0 })), (i = []);
        break;
      case "textarea":
        (o = zc(e, o)), (r = zc(e, r)), (i = []);
        break;
      default:
        typeof o.onClick != "function" && typeof r.onClick == "function" && (e.onclick = rl);
    }
    jc(n, r);
    var s;
    n = null;
    for (u in o)
      if (!r.hasOwnProperty(u) && o.hasOwnProperty(u) && o[u] != null)
        if (u === "style") {
          var a = o[u];
          for (s in a) a.hasOwnProperty(s) && (n || (n = {}), (n[s] = ""));
        } else
          u !== "dangerouslySetInnerHTML" &&
            u !== "children" &&
            u !== "suppressContentEditableWarning" &&
            u !== "suppressHydrationWarning" &&
            u !== "autoFocus" &&
            (Wi.hasOwnProperty(u) ? i || (i = []) : (i = i || []).push(u, null));
    for (u in r) {
      var l = r[u];
      if (
        ((a = o != null ? o[u] : void 0),
        r.hasOwnProperty(u) && l !== a && (l != null || a != null))
      )
        if (u === "style")
          if (a) {
            for (s in a)
              !a.hasOwnProperty(s) || (l && l.hasOwnProperty(s)) || (n || (n = {}), (n[s] = ""));
            for (s in l) l.hasOwnProperty(s) && a[s] !== l[s] && (n || (n = {}), (n[s] = l[s]));
          } else n || (i || (i = []), i.push(u, n)), (n = l);
        else
          u === "dangerouslySetInnerHTML"
            ? ((l = l ? l.__html : void 0),
              (a = a ? a.__html : void 0),
              l != null && a !== l && (i = i || []).push(u, l))
            : u === "children"
              ? (typeof l != "string" && typeof l != "number") || (i = i || []).push(u, "" + l)
              : u !== "suppressContentEditableWarning" &&
                u !== "suppressHydrationWarning" &&
                (Wi.hasOwnProperty(u)
                  ? (l != null && u === "onScroll" && de("scroll", e), i || a === l || (i = []))
                  : (i = i || []).push(u, l));
    }
    n && (i = i || []).push("style", n);
    var u = i;
    (t.updateQueue = u) && (t.flags |= 4);
  }
};
Gv = function (e, t, n, r) {
  n !== r && (t.flags |= 4);
};
function ci(e, t) {
  if (!pe)
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
function He(e) {
  var t = e.alternate !== null && e.alternate.child === e.child,
    n = 0,
    r = 0;
  if (t)
    for (var o = e.child; o !== null; )
      (n |= o.lanes | o.childLanes),
        (r |= o.subtreeFlags & 14680064),
        (r |= o.flags & 14680064),
        (o.return = e),
        (o = o.sibling);
  else
    for (o = e.child; o !== null; )
      (n |= o.lanes | o.childLanes),
        (r |= o.subtreeFlags),
        (r |= o.flags),
        (o.return = e),
        (o = o.sibling);
  return (e.subtreeFlags |= r), (e.childLanes = n), t;
}
function _k(e, t, n) {
  var r = t.pendingProps;
  switch ((Md(t), t.tag)) {
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
      return He(t), null;
    case 1:
      return it(t.type) && ol(), He(t), null;
    case 3:
      return (
        (r = t.stateNode),
        Lo(),
        he(ot),
        he(Ke),
        zd(),
        r.pendingContext && ((r.context = r.pendingContext), (r.pendingContext = null)),
        (e === null || e.child === null) &&
          (Js(t)
            ? (t.flags |= 4)
            : e === null ||
              (e.memoizedState.isDehydrated && !(t.flags & 256)) ||
              ((t.flags |= 1024), Lt !== null && (Cf(Lt), (Lt = null)))),
        mf(e, t),
        He(t),
        null
      );
    case 5:
      Fd(t);
      var o = xr(rs.current);
      if (((n = t.type), e !== null && t.stateNode != null))
        Wv(e, t, n, r, o), e.ref !== t.ref && ((t.flags |= 512), (t.flags |= 2097152));
      else {
        if (!r) {
          if (t.stateNode === null) throw Error(B(166));
          return He(t), null;
        }
        if (((e = xr(Qt.current)), Js(t))) {
          (r = t.stateNode), (n = t.type);
          var i = t.memoizedProps;
          switch (((r[Kt] = t), (r[ts] = i), (e = (t.mode & 1) !== 0), n)) {
            case "dialog":
              de("cancel", r), de("close", r);
              break;
            case "iframe":
            case "object":
            case "embed":
              de("load", r);
              break;
            case "video":
            case "audio":
              for (o = 0; o < Ci.length; o++) de(Ci[o], r);
              break;
            case "source":
              de("error", r);
              break;
            case "img":
            case "image":
            case "link":
              de("error", r), de("load", r);
              break;
            case "details":
              de("toggle", r);
              break;
            case "input":
              vp(r, i), de("invalid", r);
              break;
            case "select":
              (r._wrapperState = { wasMultiple: !!i.multiple }), de("invalid", r);
              break;
            case "textarea":
              wp(r, i), de("invalid", r);
          }
          jc(n, i), (o = null);
          for (var s in i)
            if (i.hasOwnProperty(s)) {
              var a = i[s];
              s === "children"
                ? typeof a == "string"
                  ? r.textContent !== a &&
                    (i.suppressHydrationWarning !== !0 && qs(r.textContent, a, e),
                    (o = ["children", a]))
                  : typeof a == "number" &&
                    r.textContent !== "" + a &&
                    (i.suppressHydrationWarning !== !0 && qs(r.textContent, a, e),
                    (o = ["children", "" + a]))
                : Wi.hasOwnProperty(s) && a != null && s === "onScroll" && de("scroll", r);
            }
          switch (n) {
            case "input":
              Hs(r), xp(r, i, !0);
              break;
            case "textarea":
              Hs(r), Sp(r);
              break;
            case "select":
            case "option":
              break;
            default:
              typeof i.onClick == "function" && (r.onclick = rl);
          }
          (r = o), (t.updateQueue = r), r !== null && (t.flags |= 4);
        } else {
          (s = o.nodeType === 9 ? o : o.ownerDocument),
            e === "http://www.w3.org/1999/xhtml" && (e = w0(n)),
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
            (e[Kt] = t),
            (e[ts] = r),
            Hv(e, t, !1, !1),
            (t.stateNode = e);
          e: {
            switch (((s = Bc(n, r)), n)) {
              case "dialog":
                de("cancel", e), de("close", e), (o = r);
                break;
              case "iframe":
              case "object":
              case "embed":
                de("load", e), (o = r);
                break;
              case "video":
              case "audio":
                for (o = 0; o < Ci.length; o++) de(Ci[o], e);
                o = r;
                break;
              case "source":
                de("error", e), (o = r);
                break;
              case "img":
              case "image":
              case "link":
                de("error", e), de("load", e), (o = r);
                break;
              case "details":
                de("toggle", e), (o = r);
                break;
              case "input":
                vp(e, r), (o = Vc(e, r)), de("invalid", e);
                break;
              case "option":
                o = r;
                break;
              case "select":
                (e._wrapperState = { wasMultiple: !!r.multiple }),
                  (o = ve({}, r, { value: void 0 })),
                  de("invalid", e);
                break;
              case "textarea":
                wp(e, r), (o = zc(e, r)), de("invalid", e);
                break;
              default:
                o = r;
            }
            jc(n, o), (a = o);
            for (i in a)
              if (a.hasOwnProperty(i)) {
                var l = a[i];
                i === "style"
                  ? C0(e, l)
                  : i === "dangerouslySetInnerHTML"
                    ? ((l = l ? l.__html : void 0), l != null && S0(e, l))
                    : i === "children"
                      ? typeof l == "string"
                        ? (n !== "textarea" || l !== "") && Gi(e, l)
                        : typeof l == "number" && Gi(e, "" + l)
                      : i !== "suppressContentEditableWarning" &&
                        i !== "suppressHydrationWarning" &&
                        i !== "autoFocus" &&
                        (Wi.hasOwnProperty(i)
                          ? l != null && i === "onScroll" && de("scroll", e)
                          : l != null && md(e, i, l, s));
              }
            switch (n) {
              case "input":
                Hs(e), xp(e, r, !1);
                break;
              case "textarea":
                Hs(e), Sp(e);
                break;
              case "option":
                r.value != null && e.setAttribute("value", "" + Qn(r.value));
                break;
              case "select":
                (e.multiple = !!r.multiple),
                  (i = r.value),
                  i != null
                    ? xo(e, !!r.multiple, i, !1)
                    : r.defaultValue != null && xo(e, !!r.multiple, r.defaultValue, !0);
                break;
              default:
                typeof o.onClick == "function" && (e.onclick = rl);
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
      return He(t), null;
    case 6:
      if (e && t.stateNode != null) Gv(e, t, e.memoizedProps, r);
      else {
        if (typeof r != "string" && t.stateNode === null) throw Error(B(166));
        if (((n = xr(rs.current)), xr(Qt.current), Js(t))) {
          if (
            ((r = t.stateNode),
            (n = t.memoizedProps),
            (r[Kt] = t),
            (i = r.nodeValue !== n) && ((e = ft), e !== null))
          )
            switch (e.tag) {
              case 3:
                qs(r.nodeValue, n, (e.mode & 1) !== 0);
                break;
              case 5:
                e.memoizedProps.suppressHydrationWarning !== !0 &&
                  qs(r.nodeValue, n, (e.mode & 1) !== 0);
            }
          i && (t.flags |= 4);
        } else
          (r = (n.nodeType === 9 ? n : n.ownerDocument).createTextNode(r)),
            (r[Kt] = t),
            (t.stateNode = r);
      }
      return He(t), null;
    case 13:
      if (
        (he(me),
        (r = t.memoizedState),
        e === null || (e.memoizedState !== null && e.memoizedState.dehydrated !== null))
      ) {
        if (pe && ct !== null && t.mode & 1 && !(t.flags & 128))
          cv(), Do(), (t.flags |= 98560), (i = !1);
        else if (((i = Js(t)), r !== null && r.dehydrated !== null)) {
          if (e === null) {
            if (!i) throw Error(B(318));
            if (((i = t.memoizedState), (i = i !== null ? i.dehydrated : null), !i))
              throw Error(B(317));
            i[Kt] = t;
          } else Do(), !(t.flags & 128) && (t.memoizedState = null), (t.flags |= 4);
          He(t), (i = !1);
        } else Lt !== null && (Cf(Lt), (Lt = null)), (i = !0);
        if (!i) return t.flags & 65536 ? t : null;
      }
      return t.flags & 128
        ? ((t.lanes = n), t)
        : ((r = r !== null),
          r !== (e !== null && e.memoizedState !== null) &&
            r &&
            ((t.child.flags |= 8192),
            t.mode & 1 && (e === null || me.current & 1 ? Pe === 0 && (Pe = 3) : Qd())),
          t.updateQueue !== null && (t.flags |= 4),
          He(t),
          null);
    case 4:
      return Lo(), mf(e, t), e === null && Ji(t.stateNode.containerInfo), He(t), null;
    case 10:
      return Id(t.type._context), He(t), null;
    case 17:
      return it(t.type) && ol(), He(t), null;
    case 19:
      if ((he(me), (i = t.memoizedState), i === null)) return He(t), null;
      if (((r = (t.flags & 128) !== 0), (s = i.rendering), s === null))
        if (r) ci(i, !1);
        else {
          if (Pe !== 0 || (e !== null && e.flags & 128))
            for (e = t.child; e !== null; ) {
              if (((s = fl(e)), s !== null)) {
                for (
                  t.flags |= 128,
                    ci(i, !1),
                    r = s.updateQueue,
                    r !== null && ((t.updateQueue = r), (t.flags |= 4)),
                    t.subtreeFlags = 0,
                    r = n,
                    n = t.child;
                  n !== null;

                )
                  (i = n),
                    (e = r),
                    (i.flags &= 14680066),
                    (s = i.alternate),
                    s === null
                      ? ((i.childLanes = 0),
                        (i.lanes = e),
                        (i.child = null),
                        (i.subtreeFlags = 0),
                        (i.memoizedProps = null),
                        (i.memoizedState = null),
                        (i.updateQueue = null),
                        (i.dependencies = null),
                        (i.stateNode = null))
                      : ((i.childLanes = s.childLanes),
                        (i.lanes = s.lanes),
                        (i.child = s.child),
                        (i.subtreeFlags = 0),
                        (i.deletions = null),
                        (i.memoizedProps = s.memoizedProps),
                        (i.memoizedState = s.memoizedState),
                        (i.updateQueue = s.updateQueue),
                        (i.type = s.type),
                        (e = s.dependencies),
                        (i.dependencies =
                          e === null ? null : { lanes: e.lanes, firstContext: e.firstContext })),
                    (n = n.sibling);
                return ue(me, (me.current & 1) | 2), t.child;
              }
              e = e.sibling;
            }
          i.tail !== null &&
            be() > Oo &&
            ((t.flags |= 128), (r = !0), ci(i, !1), (t.lanes = 4194304));
        }
      else {
        if (!r)
          if (((e = fl(s)), e !== null)) {
            if (
              ((t.flags |= 128),
              (r = !0),
              (n = e.updateQueue),
              n !== null && ((t.updateQueue = n), (t.flags |= 4)),
              ci(i, !0),
              i.tail === null && i.tailMode === "hidden" && !s.alternate && !pe)
            )
              return He(t), null;
          } else
            2 * be() - i.renderingStartTime > Oo &&
              n !== 1073741824 &&
              ((t.flags |= 128), (r = !0), ci(i, !1), (t.lanes = 4194304));
        i.isBackwards
          ? ((s.sibling = t.child), (t.child = s))
          : ((n = i.last), n !== null ? (n.sibling = s) : (t.child = s), (i.last = s));
      }
      return i.tail !== null
        ? ((t = i.tail),
          (i.rendering = t),
          (i.tail = t.sibling),
          (i.renderingStartTime = be()),
          (t.sibling = null),
          (n = me.current),
          ue(me, r ? (n & 1) | 2 : n & 1),
          t)
        : (He(t), null);
    case 22:
    case 23:
      return (
        Zd(),
        (r = t.memoizedState !== null),
        e !== null && (e.memoizedState !== null) !== r && (t.flags |= 8192),
        r && t.mode & 1
          ? ut & 1073741824 && (He(t), t.subtreeFlags & 6 && (t.flags |= 8192))
          : He(t),
        null
      );
    case 24:
      return null;
    case 25:
      return null;
  }
  throw Error(B(156, t.tag));
}
function Tk(e, t) {
  switch ((Md(t), t.tag)) {
    case 1:
      return (
        it(t.type) && ol(), (e = t.flags), e & 65536 ? ((t.flags = (e & -65537) | 128), t) : null
      );
    case 3:
      return (
        Lo(),
        he(ot),
        he(Ke),
        zd(),
        (e = t.flags),
        e & 65536 && !(e & 128) ? ((t.flags = (e & -65537) | 128), t) : null
      );
    case 5:
      return Fd(t), null;
    case 13:
      if ((he(me), (e = t.memoizedState), e !== null && e.dehydrated !== null)) {
        if (t.alternate === null) throw Error(B(340));
        Do();
      }
      return (e = t.flags), e & 65536 ? ((t.flags = (e & -65537) | 128), t) : null;
    case 19:
      return he(me), null;
    case 4:
      return Lo(), null;
    case 10:
      return Id(t.type._context), null;
    case 22:
    case 23:
      return Zd(), null;
    case 24:
      return null;
    default:
      return null;
  }
}
var na = !1,
  Ge = !1,
  Nk = typeof WeakSet == "function" ? WeakSet : Set,
  W = null;
function uo(e, t) {
  var n = e.ref;
  if (n !== null)
    if (typeof n == "function")
      try {
        n(null);
      } catch (r) {
        we(e, t, r);
      }
    else n.current = null;
}
function gf(e, t, n) {
  try {
    n();
  } catch (r) {
    we(e, t, r);
  }
}
var cm = !1;
function Pk(e, t) {
  if (((qc = el), (e = Q0()), Nd(e))) {
    if ("selectionStart" in e) var n = { start: e.selectionStart, end: e.selectionEnd };
    else
      e: {
        n = ((n = e.ownerDocument) && n.defaultView) || window;
        var r = n.getSelection && n.getSelection();
        if (r && r.rangeCount !== 0) {
          n = r.anchorNode;
          var o = r.anchorOffset,
            i = r.focusNode;
          r = r.focusOffset;
          try {
            n.nodeType, i.nodeType;
          } catch {
            n = null;
            break e;
          }
          var s = 0,
            a = -1,
            l = -1,
            u = 0,
            c = 0,
            f = e,
            d = null;
          t: for (;;) {
            for (
              var p;
              f !== n || (o !== 0 && f.nodeType !== 3) || (a = s + o),
                f !== i || (r !== 0 && f.nodeType !== 3) || (l = s + r),
                f.nodeType === 3 && (s += f.nodeValue.length),
                (p = f.firstChild) !== null;

            )
              (d = f), (f = p);
            for (;;) {
              if (f === e) break t;
              if (
                (d === n && ++u === o && (a = s),
                d === i && ++c === r && (l = s),
                (p = f.nextSibling) !== null)
              )
                break;
              (f = d), (d = f.parentNode);
            }
            f = p;
          }
          n = a === -1 || l === -1 ? null : { start: a, end: l };
        } else n = null;
      }
    n = n || { start: 0, end: 0 };
  } else n = null;
  for (Jc = { focusedElem: e, selectionRange: n }, el = !1, W = t; W !== null; )
    if (((t = W), (e = t.child), (t.subtreeFlags & 1028) !== 0 && e !== null))
      (e.return = t), (W = e);
    else
      for (; W !== null; ) {
        t = W;
        try {
          var y = t.alternate;
          if (t.flags & 1024)
            switch (t.tag) {
              case 0:
              case 11:
              case 15:
                break;
              case 1:
                if (y !== null) {
                  var m = y.memoizedProps,
                    w = y.memoizedState,
                    h = t.stateNode,
                    g = h.getSnapshotBeforeUpdate(t.elementType === t.type ? m : Rt(t.type, m), w);
                  h.__reactInternalSnapshotBeforeUpdate = g;
                }
                break;
              case 3:
                var x = t.stateNode.containerInfo;
                x.nodeType === 1
                  ? (x.textContent = "")
                  : x.nodeType === 9 && x.documentElement && x.removeChild(x.documentElement);
                break;
              case 5:
              case 6:
              case 4:
              case 17:
                break;
              default:
                throw Error(B(163));
            }
        } catch (S) {
          we(t, t.return, S);
        }
        if (((e = t.sibling), e !== null)) {
          (e.return = t.return), (W = e);
          break;
        }
        W = t.return;
      }
  return (y = cm), (cm = !1), y;
}
function Vi(e, t, n) {
  var r = t.updateQueue;
  if (((r = r !== null ? r.lastEffect : null), r !== null)) {
    var o = (r = r.next);
    do {
      if ((o.tag & e) === e) {
        var i = o.destroy;
        (o.destroy = void 0), i !== void 0 && gf(t, n, i);
      }
      o = o.next;
    } while (o !== r);
  }
}
function Xl(e, t) {
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
function yf(e) {
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
function Kv(e) {
  var t = e.alternate;
  t !== null && ((e.alternate = null), Kv(t)),
    (e.child = null),
    (e.deletions = null),
    (e.sibling = null),
    e.tag === 5 &&
      ((t = e.stateNode),
      t !== null && (delete t[Kt], delete t[ts], delete t[nf], delete t[fk], delete t[dk])),
    (e.stateNode = null),
    (e.return = null),
    (e.dependencies = null),
    (e.memoizedProps = null),
    (e.memoizedState = null),
    (e.pendingProps = null),
    (e.stateNode = null),
    (e.updateQueue = null);
}
function Yv(e) {
  return e.tag === 5 || e.tag === 3 || e.tag === 4;
}
function fm(e) {
  e: for (;;) {
    for (; e.sibling === null; ) {
      if (e.return === null || Yv(e.return)) return null;
      e = e.return;
    }
    for (e.sibling.return = e.return, e = e.sibling; e.tag !== 5 && e.tag !== 6 && e.tag !== 18; ) {
      if (e.flags & 2 || e.child === null || e.tag === 4) continue e;
      (e.child.return = e), (e = e.child);
    }
    if (!(e.flags & 2)) return e.stateNode;
  }
}
function vf(e, t, n) {
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
          n != null || t.onclick !== null || (t.onclick = rl));
  else if (r !== 4 && ((e = e.child), e !== null))
    for (vf(e, t, n), e = e.sibling; e !== null; ) vf(e, t, n), (e = e.sibling);
}
function xf(e, t, n) {
  var r = e.tag;
  if (r === 5 || r === 6) (e = e.stateNode), t ? n.insertBefore(e, t) : n.appendChild(e);
  else if (r !== 4 && ((e = e.child), e !== null))
    for (xf(e, t, n), e = e.sibling; e !== null; ) xf(e, t, n), (e = e.sibling);
}
var Ve = null,
  Dt = !1;
function Nn(e, t, n) {
  for (n = n.child; n !== null; ) Xv(e, t, n), (n = n.sibling);
}
function Xv(e, t, n) {
  if (Zt && typeof Zt.onCommitFiberUnmount == "function")
    try {
      Zt.onCommitFiberUnmount(jl, n);
    } catch {}
  switch (n.tag) {
    case 5:
      Ge || uo(n, t);
    case 6:
      var r = Ve,
        o = Dt;
      (Ve = null),
        Nn(e, t, n),
        (Ve = r),
        (Dt = o),
        Ve !== null &&
          (Dt
            ? ((e = Ve),
              (n = n.stateNode),
              e.nodeType === 8 ? e.parentNode.removeChild(n) : e.removeChild(n))
            : Ve.removeChild(n.stateNode));
      break;
    case 18:
      Ve !== null &&
        (Dt
          ? ((e = Ve),
            (n = n.stateNode),
            e.nodeType === 8 ? ju(e.parentNode, n) : e.nodeType === 1 && ju(e, n),
            Zi(e))
          : ju(Ve, n.stateNode));
      break;
    case 4:
      (r = Ve),
        (o = Dt),
        (Ve = n.stateNode.containerInfo),
        (Dt = !0),
        Nn(e, t, n),
        (Ve = r),
        (Dt = o);
      break;
    case 0:
    case 11:
    case 14:
    case 15:
      if (!Ge && ((r = n.updateQueue), r !== null && ((r = r.lastEffect), r !== null))) {
        o = r = r.next;
        do {
          var i = o,
            s = i.destroy;
          (i = i.tag), s !== void 0 && (i & 2 || i & 4) && gf(n, t, s), (o = o.next);
        } while (o !== r);
      }
      Nn(e, t, n);
      break;
    case 1:
      if (!Ge && (uo(n, t), (r = n.stateNode), typeof r.componentWillUnmount == "function"))
        try {
          (r.props = n.memoizedProps), (r.state = n.memoizedState), r.componentWillUnmount();
        } catch (a) {
          we(n, t, a);
        }
      Nn(e, t, n);
      break;
    case 21:
      Nn(e, t, n);
      break;
    case 22:
      n.mode & 1
        ? ((Ge = (r = Ge) || n.memoizedState !== null), Nn(e, t, n), (Ge = r))
        : Nn(e, t, n);
      break;
    default:
      Nn(e, t, n);
  }
}
function dm(e) {
  var t = e.updateQueue;
  if (t !== null) {
    e.updateQueue = null;
    var n = e.stateNode;
    n === null && (n = e.stateNode = new Nk()),
      t.forEach(function (r) {
        var o = Fk.bind(null, e, r);
        n.has(r) || (n.add(r), r.then(o, o));
      });
  }
}
function Mt(e, t) {
  var n = t.deletions;
  if (n !== null)
    for (var r = 0; r < n.length; r++) {
      var o = n[r];
      try {
        var i = e,
          s = t,
          a = s;
        e: for (; a !== null; ) {
          switch (a.tag) {
            case 5:
              (Ve = a.stateNode), (Dt = !1);
              break e;
            case 3:
              (Ve = a.stateNode.containerInfo), (Dt = !0);
              break e;
            case 4:
              (Ve = a.stateNode.containerInfo), (Dt = !0);
              break e;
          }
          a = a.return;
        }
        if (Ve === null) throw Error(B(160));
        Xv(i, s, o), (Ve = null), (Dt = !1);
        var l = o.alternate;
        l !== null && (l.return = null), (o.return = null);
      } catch (u) {
        we(o, t, u);
      }
    }
  if (t.subtreeFlags & 12854) for (t = t.child; t !== null; ) Zv(t, e), (t = t.sibling);
}
function Zv(e, t) {
  var n = e.alternate,
    r = e.flags;
  switch (e.tag) {
    case 0:
    case 11:
    case 14:
    case 15:
      if ((Mt(t, e), Ht(e), r & 4)) {
        try {
          Vi(3, e, e.return), Xl(3, e);
        } catch (m) {
          we(e, e.return, m);
        }
        try {
          Vi(5, e, e.return);
        } catch (m) {
          we(e, e.return, m);
        }
      }
      break;
    case 1:
      Mt(t, e), Ht(e), r & 512 && n !== null && uo(n, n.return);
      break;
    case 5:
      if ((Mt(t, e), Ht(e), r & 512 && n !== null && uo(n, n.return), e.flags & 32)) {
        var o = e.stateNode;
        try {
          Gi(o, "");
        } catch (m) {
          we(e, e.return, m);
        }
      }
      if (r & 4 && ((o = e.stateNode), o != null)) {
        var i = e.memoizedProps,
          s = n !== null ? n.memoizedProps : i,
          a = e.type,
          l = e.updateQueue;
        if (((e.updateQueue = null), l !== null))
          try {
            a === "input" && i.type === "radio" && i.name != null && v0(o, i), Bc(a, s);
            var u = Bc(a, i);
            for (s = 0; s < l.length; s += 2) {
              var c = l[s],
                f = l[s + 1];
              c === "style"
                ? C0(o, f)
                : c === "dangerouslySetInnerHTML"
                  ? S0(o, f)
                  : c === "children"
                    ? Gi(o, f)
                    : md(o, c, f, u);
            }
            switch (a) {
              case "input":
                Oc(o, i);
                break;
              case "textarea":
                x0(o, i);
                break;
              case "select":
                var d = o._wrapperState.wasMultiple;
                o._wrapperState.wasMultiple = !!i.multiple;
                var p = i.value;
                p != null
                  ? xo(o, !!i.multiple, p, !1)
                  : d !== !!i.multiple &&
                    (i.defaultValue != null
                      ? xo(o, !!i.multiple, i.defaultValue, !0)
                      : xo(o, !!i.multiple, i.multiple ? [] : "", !1));
            }
            o[ts] = i;
          } catch (m) {
            we(e, e.return, m);
          }
      }
      break;
    case 6:
      if ((Mt(t, e), Ht(e), r & 4)) {
        if (e.stateNode === null) throw Error(B(162));
        (o = e.stateNode), (i = e.memoizedProps);
        try {
          o.nodeValue = i;
        } catch (m) {
          we(e, e.return, m);
        }
      }
      break;
    case 3:
      if ((Mt(t, e), Ht(e), r & 4 && n !== null && n.memoizedState.isDehydrated))
        try {
          Zi(t.containerInfo);
        } catch (m) {
          we(e, e.return, m);
        }
      break;
    case 4:
      Mt(t, e), Ht(e);
      break;
    case 13:
      Mt(t, e),
        Ht(e),
        (o = e.child),
        o.flags & 8192 &&
          ((i = o.memoizedState !== null),
          (o.stateNode.isHidden = i),
          !i || (o.alternate !== null && o.alternate.memoizedState !== null) || (Yd = be())),
        r & 4 && dm(e);
      break;
    case 22:
      if (
        ((c = n !== null && n.memoizedState !== null),
        e.mode & 1 ? ((Ge = (u = Ge) || c), Mt(t, e), (Ge = u)) : Mt(t, e),
        Ht(e),
        r & 8192)
      ) {
        if (((u = e.memoizedState !== null), (e.stateNode.isHidden = u) && !c && e.mode & 1))
          for (W = e, c = e.child; c !== null; ) {
            for (f = W = c; W !== null; ) {
              switch (((d = W), (p = d.child), d.tag)) {
                case 0:
                case 11:
                case 14:
                case 15:
                  Vi(4, d, d.return);
                  break;
                case 1:
                  uo(d, d.return);
                  var y = d.stateNode;
                  if (typeof y.componentWillUnmount == "function") {
                    (r = d), (n = d.return);
                    try {
                      (t = r),
                        (y.props = t.memoizedProps),
                        (y.state = t.memoizedState),
                        y.componentWillUnmount();
                    } catch (m) {
                      we(r, n, m);
                    }
                  }
                  break;
                case 5:
                  uo(d, d.return);
                  break;
                case 22:
                  if (d.memoizedState !== null) {
                    pm(f);
                    continue;
                  }
              }
              p !== null ? ((p.return = d), (W = p)) : pm(f);
            }
            c = c.sibling;
          }
        e: for (c = null, f = e; ; ) {
          if (f.tag === 5) {
            if (c === null) {
              c = f;
              try {
                (o = f.stateNode),
                  u
                    ? ((i = o.style),
                      typeof i.setProperty == "function"
                        ? i.setProperty("display", "none", "important")
                        : (i.display = "none"))
                    : ((a = f.stateNode),
                      (l = f.memoizedProps.style),
                      (s = l != null && l.hasOwnProperty("display") ? l.display : null),
                      (a.style.display = E0("display", s)));
              } catch (m) {
                we(e, e.return, m);
              }
            }
          } else if (f.tag === 6) {
            if (c === null)
              try {
                f.stateNode.nodeValue = u ? "" : f.memoizedProps;
              } catch (m) {
                we(e, e.return, m);
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
      Mt(t, e), Ht(e), r & 4 && dm(e);
      break;
    case 21:
      break;
    default:
      Mt(t, e), Ht(e);
  }
}
function Ht(e) {
  var t = e.flags;
  if (t & 2) {
    try {
      e: {
        for (var n = e.return; n !== null; ) {
          if (Yv(n)) {
            var r = n;
            break e;
          }
          n = n.return;
        }
        throw Error(B(160));
      }
      switch (r.tag) {
        case 5:
          var o = r.stateNode;
          r.flags & 32 && (Gi(o, ""), (r.flags &= -33));
          var i = fm(e);
          xf(e, i, o);
          break;
        case 3:
        case 4:
          var s = r.stateNode.containerInfo,
            a = fm(e);
          vf(e, a, s);
          break;
        default:
          throw Error(B(161));
      }
    } catch (l) {
      we(e, e.return, l);
    }
    e.flags &= -3;
  }
  t & 4096 && (e.flags &= -4097);
}
function Mk(e, t, n) {
  (W = e), Qv(e);
}
function Qv(e, t, n) {
  for (var r = (e.mode & 1) !== 0; W !== null; ) {
    var o = W,
      i = o.child;
    if (o.tag === 22 && r) {
      var s = o.memoizedState !== null || na;
      if (!s) {
        var a = o.alternate,
          l = (a !== null && a.memoizedState !== null) || Ge;
        a = na;
        var u = Ge;
        if (((na = s), (Ge = l) && !u))
          for (W = o; W !== null; )
            (s = W),
              (l = s.child),
              s.tag === 22 && s.memoizedState !== null
                ? mm(o)
                : l !== null
                  ? ((l.return = s), (W = l))
                  : mm(o);
        for (; i !== null; ) (W = i), Qv(i), (i = i.sibling);
        (W = o), (na = a), (Ge = u);
      }
      hm(e);
    } else o.subtreeFlags & 8772 && i !== null ? ((i.return = o), (W = i)) : hm(e);
  }
}
function hm(e) {
  for (; W !== null; ) {
    var t = W;
    if (t.flags & 8772) {
      var n = t.alternate;
      try {
        if (t.flags & 8772)
          switch (t.tag) {
            case 0:
            case 11:
            case 15:
              Ge || Xl(5, t);
              break;
            case 1:
              var r = t.stateNode;
              if (t.flags & 4 && !Ge)
                if (n === null) r.componentDidMount();
                else {
                  var o = t.elementType === t.type ? n.memoizedProps : Rt(t.type, n.memoizedProps);
                  r.componentDidUpdate(o, n.memoizedState, r.__reactInternalSnapshotBeforeUpdate);
                }
              var i = t.updateQueue;
              i !== null && Qp(t, i, r);
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
                Qp(t, s, n);
              }
              break;
            case 5:
              var a = t.stateNode;
              if (n === null && t.flags & 4) {
                n = a;
                var l = t.memoizedProps;
                switch (t.type) {
                  case "button":
                  case "input":
                  case "select":
                  case "textarea":
                    l.autoFocus && n.focus();
                    break;
                  case "img":
                    l.src && (n.src = l.src);
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
                var u = t.alternate;
                if (u !== null) {
                  var c = u.memoizedState;
                  if (c !== null) {
                    var f = c.dehydrated;
                    f !== null && Zi(f);
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
              throw Error(B(163));
          }
        Ge || (t.flags & 512 && yf(t));
      } catch (d) {
        we(t, t.return, d);
      }
    }
    if (t === e) {
      W = null;
      break;
    }
    if (((n = t.sibling), n !== null)) {
      (n.return = t.return), (W = n);
      break;
    }
    W = t.return;
  }
}
function pm(e) {
  for (; W !== null; ) {
    var t = W;
    if (t === e) {
      W = null;
      break;
    }
    var n = t.sibling;
    if (n !== null) {
      (n.return = t.return), (W = n);
      break;
    }
    W = t.return;
  }
}
function mm(e) {
  for (; W !== null; ) {
    var t = W;
    try {
      switch (t.tag) {
        case 0:
        case 11:
        case 15:
          var n = t.return;
          try {
            Xl(4, t);
          } catch (l) {
            we(t, n, l);
          }
          break;
        case 1:
          var r = t.stateNode;
          if (typeof r.componentDidMount == "function") {
            var o = t.return;
            try {
              r.componentDidMount();
            } catch (l) {
              we(t, o, l);
            }
          }
          var i = t.return;
          try {
            yf(t);
          } catch (l) {
            we(t, i, l);
          }
          break;
        case 5:
          var s = t.return;
          try {
            yf(t);
          } catch (l) {
            we(t, s, l);
          }
      }
    } catch (l) {
      we(t, t.return, l);
    }
    if (t === e) {
      W = null;
      break;
    }
    var a = t.sibling;
    if (a !== null) {
      (a.return = t.return), (W = a);
      break;
    }
    W = t.return;
  }
}
var Ak = Math.ceil,
  pl = Tn.ReactCurrentDispatcher,
  Gd = Tn.ReactCurrentOwner,
  _t = Tn.ReactCurrentBatchConfig,
  te = 0,
  De = null,
  ke = null,
  Oe = 0,
  ut = 0,
  co = nr(0),
  Pe = 0,
  as = null,
  Rr = 0,
  Zl = 0,
  Kd = 0,
  Oi = null,
  tt = null,
  Yd = 0,
  Oo = 1 / 0,
  un = null,
  ml = !1,
  wf = null,
  Kn = null,
  ra = !1,
  jn = null,
  gl = 0,
  Fi = 0,
  Sf = null,
  Ia = -1,
  La = 0;
function Qe() {
  return te & 6 ? be() : Ia !== -1 ? Ia : (Ia = be());
}
function Yn(e) {
  return e.mode & 1
    ? te & 2 && Oe !== 0
      ? Oe & -Oe
      : pk.transition !== null
        ? (La === 0 && (La = L0()), La)
        : ((e = ie), e !== 0 || ((e = window.event), (e = e === void 0 ? 16 : B0(e.type))), e)
    : 1;
}
function Ft(e, t, n, r) {
  if (50 < Fi) throw ((Fi = 0), (Sf = null), Error(B(185)));
  _s(e, n, r),
    (!(te & 2) || e !== De) &&
      (e === De && (!(te & 2) && (Zl |= n), Pe === 4 && zn(e, Oe)),
      st(e, r),
      n === 1 && te === 0 && !(t.mode & 1) && ((Oo = be() + 500), Gl && rr()));
}
function st(e, t) {
  var n = e.callbackNode;
  pb(e, t);
  var r = Ja(e, e === De ? Oe : 0);
  if (r === 0) n !== null && bp(n), (e.callbackNode = null), (e.callbackPriority = 0);
  else if (((t = r & -r), e.callbackPriority !== t)) {
    if ((n != null && bp(n), t === 1))
      e.tag === 0 ? hk(gm.bind(null, e)) : av(gm.bind(null, e)),
        uk(function () {
          !(te & 6) && rr();
        }),
        (n = null);
    else {
      switch (V0(r)) {
        case 1:
          n = wd;
          break;
        case 4:
          n = D0;
          break;
        case 16:
          n = qa;
          break;
        case 536870912:
          n = I0;
          break;
        default:
          n = qa;
      }
      n = ix(n, qv.bind(null, e));
    }
    (e.callbackPriority = t), (e.callbackNode = n);
  }
}
function qv(e, t) {
  if (((Ia = -1), (La = 0), te & 6)) throw Error(B(327));
  var n = e.callbackNode;
  if (bo() && e.callbackNode !== n) return null;
  var r = Ja(e, e === De ? Oe : 0);
  if (r === 0) return null;
  if (r & 30 || r & e.expiredLanes || t) t = yl(e, r);
  else {
    t = r;
    var o = te;
    te |= 2;
    var i = ex();
    (De !== e || Oe !== t) && ((un = null), (Oo = be() + 500), br(e, t));
    do
      try {
        Ik();
        break;
      } catch (a) {
        Jv(e, a);
      }
    while (!0);
    Dd(), (pl.current = i), (te = o), ke !== null ? (t = 0) : ((De = null), (Oe = 0), (t = Pe));
  }
  if (t !== 0) {
    if ((t === 2 && ((o = Kc(e)), o !== 0 && ((r = o), (t = Ef(e, o)))), t === 1))
      throw ((n = as), br(e, 0), zn(e, r), st(e, be()), n);
    if (t === 6) zn(e, r);
    else {
      if (
        ((o = e.current.alternate),
        !(r & 30) &&
          !Rk(o) &&
          ((t = yl(e, r)), t === 2 && ((i = Kc(e)), i !== 0 && ((r = i), (t = Ef(e, i)))), t === 1))
      )
        throw ((n = as), br(e, 0), zn(e, r), st(e, be()), n);
      switch (((e.finishedWork = o), (e.finishedLanes = r), t)) {
        case 0:
        case 1:
          throw Error(B(345));
        case 2:
          hr(e, tt, un);
          break;
        case 3:
          if ((zn(e, r), (r & 130023424) === r && ((t = Yd + 500 - be()), 10 < t))) {
            if (Ja(e, 0) !== 0) break;
            if (((o = e.suspendedLanes), (o & r) !== r)) {
              Qe(), (e.pingedLanes |= e.suspendedLanes & o);
              break;
            }
            e.timeoutHandle = tf(hr.bind(null, e, tt, un), t);
            break;
          }
          hr(e, tt, un);
          break;
        case 4:
          if ((zn(e, r), (r & 4194240) === r)) break;
          for (t = e.eventTimes, o = -1; 0 < r; ) {
            var s = 31 - Ot(r);
            (i = 1 << s), (s = t[s]), s > o && (o = s), (r &= ~i);
          }
          if (
            ((r = o),
            (r = be() - r),
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
                          : 1960 * Ak(r / 1960)) - r),
            10 < r)
          ) {
            e.timeoutHandle = tf(hr.bind(null, e, tt, un), r);
            break;
          }
          hr(e, tt, un);
          break;
        case 5:
          hr(e, tt, un);
          break;
        default:
          throw Error(B(329));
      }
    }
  }
  return st(e, be()), e.callbackNode === n ? qv.bind(null, e) : null;
}
function Ef(e, t) {
  var n = Oi;
  return (
    e.current.memoizedState.isDehydrated && (br(e, t).flags |= 256),
    (e = yl(e, t)),
    e !== 2 && ((t = tt), (tt = n), t !== null && Cf(t)),
    e
  );
}
function Cf(e) {
  tt === null ? (tt = e) : tt.push.apply(tt, e);
}
function Rk(e) {
  for (var t = e; ; ) {
    if (t.flags & 16384) {
      var n = t.updateQueue;
      if (n !== null && ((n = n.stores), n !== null))
        for (var r = 0; r < n.length; r++) {
          var o = n[r],
            i = o.getSnapshot;
          o = o.value;
          try {
            if (!$t(i(), o)) return !1;
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
function zn(e, t) {
  for (
    t &= ~Kd, t &= ~Zl, e.suspendedLanes |= t, e.pingedLanes &= ~t, e = e.expirationTimes;
    0 < t;

  ) {
    var n = 31 - Ot(t),
      r = 1 << n;
    (e[n] = -1), (t &= ~r);
  }
}
function gm(e) {
  if (te & 6) throw Error(B(327));
  bo();
  var t = Ja(e, 0);
  if (!(t & 1)) return st(e, be()), null;
  var n = yl(e, t);
  if (e.tag !== 0 && n === 2) {
    var r = Kc(e);
    r !== 0 && ((t = r), (n = Ef(e, r)));
  }
  if (n === 1) throw ((n = as), br(e, 0), zn(e, t), st(e, be()), n);
  if (n === 6) throw Error(B(345));
  return (
    (e.finishedWork = e.current.alternate), (e.finishedLanes = t), hr(e, tt, un), st(e, be()), null
  );
}
function Xd(e, t) {
  var n = te;
  te |= 1;
  try {
    return e(t);
  } finally {
    (te = n), te === 0 && ((Oo = be() + 500), Gl && rr());
  }
}
function Dr(e) {
  jn !== null && jn.tag === 0 && !(te & 6) && bo();
  var t = te;
  te |= 1;
  var n = _t.transition,
    r = ie;
  try {
    if (((_t.transition = null), (ie = 1), e)) return e();
  } finally {
    (ie = r), (_t.transition = n), (te = t), !(te & 6) && rr();
  }
}
function Zd() {
  (ut = co.current), he(co);
}
function br(e, t) {
  (e.finishedWork = null), (e.finishedLanes = 0);
  var n = e.timeoutHandle;
  if ((n !== -1 && ((e.timeoutHandle = -1), lk(n)), ke !== null))
    for (n = ke.return; n !== null; ) {
      var r = n;
      switch ((Md(r), r.tag)) {
        case 1:
          (r = r.type.childContextTypes), r != null && ol();
          break;
        case 3:
          Lo(), he(ot), he(Ke), zd();
          break;
        case 5:
          Fd(r);
          break;
        case 4:
          Lo();
          break;
        case 13:
          he(me);
          break;
        case 19:
          he(me);
          break;
        case 10:
          Id(r.type._context);
          break;
        case 22:
        case 23:
          Zd();
      }
      n = n.return;
    }
  if (
    ((De = e),
    (ke = e = Xn(e.current, null)),
    (Oe = ut = t),
    (Pe = 0),
    (as = null),
    (Kd = Zl = Rr = 0),
    (tt = Oi = null),
    vr !== null)
  ) {
    for (t = 0; t < vr.length; t++)
      if (((n = vr[t]), (r = n.interleaved), r !== null)) {
        n.interleaved = null;
        var o = r.next,
          i = n.pending;
        if (i !== null) {
          var s = i.next;
          (i.next = o), (r.next = s);
        }
        n.pending = r;
      }
    vr = null;
  }
  return e;
}
function Jv(e, t) {
  do {
    var n = ke;
    try {
      if ((Dd(), (Aa.current = hl), dl)) {
        for (var r = ye.memoizedState; r !== null; ) {
          var o = r.queue;
          o !== null && (o.pending = null), (r = r.next);
        }
        dl = !1;
      }
      if (
        ((Ar = 0),
        (Ae = Ne = ye = null),
        (Li = !1),
        (os = 0),
        (Gd.current = null),
        n === null || n.return === null)
      ) {
        (Pe = 1), (as = t), (ke = null);
        break;
      }
      e: {
        var i = e,
          s = n.return,
          a = n,
          l = t;
        if (
          ((t = Oe),
          (a.flags |= 32768),
          l !== null && typeof l == "object" && typeof l.then == "function")
        ) {
          var u = l,
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
          var p = rm(s);
          if (p !== null) {
            (p.flags &= -257), om(p, s, a, i, t), p.mode & 1 && nm(i, u, t), (t = p), (l = u);
            var y = t.updateQueue;
            if (y === null) {
              var m = new Set();
              m.add(l), (t.updateQueue = m);
            } else y.add(l);
            break e;
          } else {
            if (!(t & 1)) {
              nm(i, u, t), Qd();
              break e;
            }
            l = Error(B(426));
          }
        } else if (pe && a.mode & 1) {
          var w = rm(s);
          if (w !== null) {
            !(w.flags & 65536) && (w.flags |= 256), om(w, s, a, i, t), Ad(Vo(l, a));
            break e;
          }
        }
        (i = l = Vo(l, a)), Pe !== 4 && (Pe = 2), Oi === null ? (Oi = [i]) : Oi.push(i), (i = s);
        do {
          switch (i.tag) {
            case 3:
              (i.flags |= 65536), (t &= -t), (i.lanes |= t);
              var h = Vv(i, l, t);
              Zp(i, h);
              break e;
            case 1:
              a = l;
              var g = i.type,
                x = i.stateNode;
              if (
                !(i.flags & 128) &&
                (typeof g.getDerivedStateFromError == "function" ||
                  (x !== null &&
                    typeof x.componentDidCatch == "function" &&
                    (Kn === null || !Kn.has(x))))
              ) {
                (i.flags |= 65536), (t &= -t), (i.lanes |= t);
                var S = Ov(i, a, t);
                Zp(i, S);
                break e;
              }
          }
          i = i.return;
        } while (i !== null);
      }
      nx(n);
    } catch (E) {
      (t = E), ke === n && n !== null && (ke = n = n.return);
      continue;
    }
    break;
  } while (!0);
}
function ex() {
  var e = pl.current;
  return (pl.current = hl), e === null ? hl : e;
}
function Qd() {
  (Pe === 0 || Pe === 3 || Pe === 2) && (Pe = 4),
    De === null || (!(Rr & 268435455) && !(Zl & 268435455)) || zn(De, Oe);
}
function yl(e, t) {
  var n = te;
  te |= 2;
  var r = ex();
  (De !== e || Oe !== t) && ((un = null), br(e, t));
  do
    try {
      Dk();
      break;
    } catch (o) {
      Jv(e, o);
    }
  while (!0);
  if ((Dd(), (te = n), (pl.current = r), ke !== null)) throw Error(B(261));
  return (De = null), (Oe = 0), Pe;
}
function Dk() {
  for (; ke !== null; ) tx(ke);
}
function Ik() {
  for (; ke !== null && !ib(); ) tx(ke);
}
function tx(e) {
  var t = ox(e.alternate, e, ut);
  (e.memoizedProps = e.pendingProps), t === null ? nx(e) : (ke = t), (Gd.current = null);
}
function nx(e) {
  var t = e;
  do {
    var n = t.alternate;
    if (((e = t.return), t.flags & 32768)) {
      if (((n = Tk(n, t)), n !== null)) {
        (n.flags &= 32767), (ke = n);
        return;
      }
      if (e !== null) (e.flags |= 32768), (e.subtreeFlags = 0), (e.deletions = null);
      else {
        (Pe = 6), (ke = null);
        return;
      }
    } else if (((n = _k(n, t, ut)), n !== null)) {
      ke = n;
      return;
    }
    if (((t = t.sibling), t !== null)) {
      ke = t;
      return;
    }
    ke = t = e;
  } while (t !== null);
  Pe === 0 && (Pe = 5);
}
function hr(e, t, n) {
  var r = ie,
    o = _t.transition;
  try {
    (_t.transition = null), (ie = 1), Lk(e, t, n, r);
  } finally {
    (_t.transition = o), (ie = r);
  }
  return null;
}
function Lk(e, t, n, r) {
  do bo();
  while (jn !== null);
  if (te & 6) throw Error(B(327));
  n = e.finishedWork;
  var o = e.finishedLanes;
  if (n === null) return null;
  if (((e.finishedWork = null), (e.finishedLanes = 0), n === e.current)) throw Error(B(177));
  (e.callbackNode = null), (e.callbackPriority = 0);
  var i = n.lanes | n.childLanes;
  if (
    (mb(e, i),
    e === De && ((ke = De = null), (Oe = 0)),
    (!(n.subtreeFlags & 2064) && !(n.flags & 2064)) ||
      ra ||
      ((ra = !0),
      ix(qa, function () {
        return bo(), null;
      })),
    (i = (n.flags & 15990) !== 0),
    n.subtreeFlags & 15990 || i)
  ) {
    (i = _t.transition), (_t.transition = null);
    var s = ie;
    ie = 1;
    var a = te;
    (te |= 4),
      (Gd.current = null),
      Pk(e, n),
      Zv(n, e),
      tk(Jc),
      (el = !!qc),
      (Jc = qc = null),
      (e.current = n),
      Mk(n),
      sb(),
      (te = a),
      (ie = s),
      (_t.transition = i);
  } else e.current = n;
  if (
    (ra && ((ra = !1), (jn = e), (gl = o)),
    (i = e.pendingLanes),
    i === 0 && (Kn = null),
    ub(n.stateNode),
    st(e, be()),
    t !== null)
  )
    for (r = e.onRecoverableError, n = 0; n < t.length; n++)
      (o = t[n]), r(o.value, { componentStack: o.stack, digest: o.digest });
  if (ml) throw ((ml = !1), (e = wf), (wf = null), e);
  return (
    gl & 1 && e.tag !== 0 && bo(),
    (i = e.pendingLanes),
    i & 1 ? (e === Sf ? Fi++ : ((Fi = 0), (Sf = e))) : (Fi = 0),
    rr(),
    null
  );
}
function bo() {
  if (jn !== null) {
    var e = V0(gl),
      t = _t.transition,
      n = ie;
    try {
      if (((_t.transition = null), (ie = 16 > e ? 16 : e), jn === null)) var r = !1;
      else {
        if (((e = jn), (jn = null), (gl = 0), te & 6)) throw Error(B(331));
        var o = te;
        for (te |= 4, W = e.current; W !== null; ) {
          var i = W,
            s = i.child;
          if (W.flags & 16) {
            var a = i.deletions;
            if (a !== null) {
              for (var l = 0; l < a.length; l++) {
                var u = a[l];
                for (W = u; W !== null; ) {
                  var c = W;
                  switch (c.tag) {
                    case 0:
                    case 11:
                    case 15:
                      Vi(8, c, i);
                  }
                  var f = c.child;
                  if (f !== null) (f.return = c), (W = f);
                  else
                    for (; W !== null; ) {
                      c = W;
                      var d = c.sibling,
                        p = c.return;
                      if ((Kv(c), c === u)) {
                        W = null;
                        break;
                      }
                      if (d !== null) {
                        (d.return = p), (W = d);
                        break;
                      }
                      W = p;
                    }
                }
              }
              var y = i.alternate;
              if (y !== null) {
                var m = y.child;
                if (m !== null) {
                  y.child = null;
                  do {
                    var w = m.sibling;
                    (m.sibling = null), (m = w);
                  } while (m !== null);
                }
              }
              W = i;
            }
          }
          if (i.subtreeFlags & 2064 && s !== null) (s.return = i), (W = s);
          else
            e: for (; W !== null; ) {
              if (((i = W), i.flags & 2048))
                switch (i.tag) {
                  case 0:
                  case 11:
                  case 15:
                    Vi(9, i, i.return);
                }
              var h = i.sibling;
              if (h !== null) {
                (h.return = i.return), (W = h);
                break e;
              }
              W = i.return;
            }
        }
        var g = e.current;
        for (W = g; W !== null; ) {
          s = W;
          var x = s.child;
          if (s.subtreeFlags & 2064 && x !== null) (x.return = s), (W = x);
          else
            e: for (s = g; W !== null; ) {
              if (((a = W), a.flags & 2048))
                try {
                  switch (a.tag) {
                    case 0:
                    case 11:
                    case 15:
                      Xl(9, a);
                  }
                } catch (E) {
                  we(a, a.return, E);
                }
              if (a === s) {
                W = null;
                break e;
              }
              var S = a.sibling;
              if (S !== null) {
                (S.return = a.return), (W = S);
                break e;
              }
              W = a.return;
            }
        }
        if (((te = o), rr(), Zt && typeof Zt.onPostCommitFiberRoot == "function"))
          try {
            Zt.onPostCommitFiberRoot(jl, e);
          } catch {}
        r = !0;
      }
      return r;
    } finally {
      (ie = n), (_t.transition = t);
    }
  }
  return !1;
}
function ym(e, t, n) {
  (t = Vo(n, t)),
    (t = Vv(e, t, 1)),
    (e = Gn(e, t, 1)),
    (t = Qe()),
    e !== null && (_s(e, 1, t), st(e, t));
}
function we(e, t, n) {
  if (e.tag === 3) ym(e, e, n);
  else
    for (; t !== null; ) {
      if (t.tag === 3) {
        ym(t, e, n);
        break;
      } else if (t.tag === 1) {
        var r = t.stateNode;
        if (
          typeof t.type.getDerivedStateFromError == "function" ||
          (typeof r.componentDidCatch == "function" && (Kn === null || !Kn.has(r)))
        ) {
          (e = Vo(n, e)),
            (e = Ov(t, e, 1)),
            (t = Gn(t, e, 1)),
            (e = Qe()),
            t !== null && (_s(t, 1, e), st(t, e));
          break;
        }
      }
      t = t.return;
    }
}
function Vk(e, t, n) {
  var r = e.pingCache;
  r !== null && r.delete(t),
    (t = Qe()),
    (e.pingedLanes |= e.suspendedLanes & n),
    De === e &&
      (Oe & n) === n &&
      (Pe === 4 || (Pe === 3 && (Oe & 130023424) === Oe && 500 > be() - Yd) ? br(e, 0) : (Kd |= n)),
    st(e, t);
}
function rx(e, t) {
  t === 0 && (e.mode & 1 ? ((t = Ks), (Ks <<= 1), !(Ks & 130023424) && (Ks = 4194304)) : (t = 1));
  var n = Qe();
  (e = Sn(e, t)), e !== null && (_s(e, t, n), st(e, n));
}
function Ok(e) {
  var t = e.memoizedState,
    n = 0;
  t !== null && (n = t.retryLane), rx(e, n);
}
function Fk(e, t) {
  var n = 0;
  switch (e.tag) {
    case 13:
      var r = e.stateNode,
        o = e.memoizedState;
      o !== null && (n = o.retryLane);
      break;
    case 19:
      r = e.stateNode;
      break;
    default:
      throw Error(B(314));
  }
  r !== null && r.delete(t), rx(e, n);
}
var ox;
ox = function (e, t, n) {
  if (e !== null)
    if (e.memoizedProps !== t.pendingProps || ot.current) nt = !0;
    else {
      if (!(e.lanes & n) && !(t.flags & 128)) return (nt = !1), kk(e, t, n);
      nt = !!(e.flags & 131072);
    }
  else (nt = !1), pe && t.flags & 1048576 && lv(t, al, t.index);
  switch (((t.lanes = 0), t.tag)) {
    case 2:
      var r = t.type;
      Da(e, t), (e = t.pendingProps);
      var o = Ro(t, Ke.current);
      Co(t, n), (o = jd(null, t, r, e, o, n));
      var i = Bd();
      return (
        (t.flags |= 1),
        typeof o == "object" && o !== null && typeof o.render == "function" && o.$$typeof === void 0
          ? ((t.tag = 1),
            (t.memoizedState = null),
            (t.updateQueue = null),
            it(r) ? ((i = !0), il(t)) : (i = !1),
            (t.memoizedState = o.state !== null && o.state !== void 0 ? o.state : null),
            Vd(t),
            (o.updater = Yl),
            (t.stateNode = o),
            (o._reactInternals = t),
            uf(t, r, e, n),
            (t = df(null, t, r, !0, i, n)))
          : ((t.tag = 0), pe && i && Pd(t), Ze(null, t, o, n), (t = t.child)),
        t
      );
    case 16:
      r = t.elementType;
      e: {
        switch (
          (Da(e, t),
          (e = t.pendingProps),
          (o = r._init),
          (r = o(r._payload)),
          (t.type = r),
          (o = t.tag = $k(r)),
          (e = Rt(r, e)),
          o)
        ) {
          case 0:
            t = ff(null, t, r, e, n);
            break e;
          case 1:
            t = am(null, t, r, e, n);
            break e;
          case 11:
            t = im(null, t, r, e, n);
            break e;
          case 14:
            t = sm(null, t, r, Rt(r.type, e), n);
            break e;
        }
        throw Error(B(306, r, ""));
      }
      return t;
    case 0:
      return (
        (r = t.type),
        (o = t.pendingProps),
        (o = t.elementType === r ? o : Rt(r, o)),
        ff(e, t, r, o, n)
      );
    case 1:
      return (
        (r = t.type),
        (o = t.pendingProps),
        (o = t.elementType === r ? o : Rt(r, o)),
        am(e, t, r, o, n)
      );
    case 3:
      e: {
        if ((jv(t), e === null)) throw Error(B(387));
        (r = t.pendingProps), (i = t.memoizedState), (o = i.element), pv(e, t), cl(t, r, null, n);
        var s = t.memoizedState;
        if (((r = s.element), i.isDehydrated))
          if (
            ((i = {
              element: r,
              isDehydrated: !1,
              cache: s.cache,
              pendingSuspenseBoundaries: s.pendingSuspenseBoundaries,
              transitions: s.transitions,
            }),
            (t.updateQueue.baseState = i),
            (t.memoizedState = i),
            t.flags & 256)
          ) {
            (o = Vo(Error(B(423)), t)), (t = lm(e, t, r, n, o));
            break e;
          } else if (r !== o) {
            (o = Vo(Error(B(424)), t)), (t = lm(e, t, r, n, o));
            break e;
          } else
            for (
              ct = Wn(t.stateNode.containerInfo.firstChild),
                ft = t,
                pe = !0,
                Lt = null,
                n = dv(t, null, r, n),
                t.child = n;
              n;

            )
              (n.flags = (n.flags & -3) | 4096), (n = n.sibling);
        else {
          if ((Do(), r === o)) {
            t = En(e, t, n);
            break e;
          }
          Ze(e, t, r, n);
        }
        t = t.child;
      }
      return t;
    case 5:
      return (
        mv(t),
        e === null && sf(t),
        (r = t.type),
        (o = t.pendingProps),
        (i = e !== null ? e.memoizedProps : null),
        (s = o.children),
        ef(r, o) ? (s = null) : i !== null && ef(r, i) && (t.flags |= 32),
        $v(e, t),
        Ze(e, t, s, n),
        t.child
      );
    case 6:
      return e === null && sf(t), null;
    case 13:
      return Bv(e, t, n);
    case 4:
      return (
        Od(t, t.stateNode.containerInfo),
        (r = t.pendingProps),
        e === null ? (t.child = Io(t, null, r, n)) : Ze(e, t, r, n),
        t.child
      );
    case 11:
      return (
        (r = t.type),
        (o = t.pendingProps),
        (o = t.elementType === r ? o : Rt(r, o)),
        im(e, t, r, o, n)
      );
    case 7:
      return Ze(e, t, t.pendingProps, n), t.child;
    case 8:
      return Ze(e, t, t.pendingProps.children, n), t.child;
    case 12:
      return Ze(e, t, t.pendingProps.children, n), t.child;
    case 10:
      e: {
        if (
          ((r = t.type._context),
          (o = t.pendingProps),
          (i = t.memoizedProps),
          (s = o.value),
          ue(ll, r._currentValue),
          (r._currentValue = s),
          i !== null)
        )
          if ($t(i.value, s)) {
            if (i.children === o.children && !ot.current) {
              t = En(e, t, n);
              break e;
            }
          } else
            for (i = t.child, i !== null && (i.return = t); i !== null; ) {
              var a = i.dependencies;
              if (a !== null) {
                s = i.child;
                for (var l = a.firstContext; l !== null; ) {
                  if (l.context === r) {
                    if (i.tag === 1) {
                      (l = mn(-1, n & -n)), (l.tag = 2);
                      var u = i.updateQueue;
                      if (u !== null) {
                        u = u.shared;
                        var c = u.pending;
                        c === null ? (l.next = l) : ((l.next = c.next), (c.next = l)),
                          (u.pending = l);
                      }
                    }
                    (i.lanes |= n),
                      (l = i.alternate),
                      l !== null && (l.lanes |= n),
                      af(i.return, n, t),
                      (a.lanes |= n);
                    break;
                  }
                  l = l.next;
                }
              } else if (i.tag === 10) s = i.type === t.type ? null : i.child;
              else if (i.tag === 18) {
                if (((s = i.return), s === null)) throw Error(B(341));
                (s.lanes |= n),
                  (a = s.alternate),
                  a !== null && (a.lanes |= n),
                  af(s, n, t),
                  (s = i.sibling);
              } else s = i.child;
              if (s !== null) s.return = i;
              else
                for (s = i; s !== null; ) {
                  if (s === t) {
                    s = null;
                    break;
                  }
                  if (((i = s.sibling), i !== null)) {
                    (i.return = s.return), (s = i);
                    break;
                  }
                  s = s.return;
                }
              i = s;
            }
        Ze(e, t, o.children, n), (t = t.child);
      }
      return t;
    case 9:
      return (
        (o = t.type),
        (r = t.pendingProps.children),
        Co(t, n),
        (o = Tt(o)),
        (r = r(o)),
        (t.flags |= 1),
        Ze(e, t, r, n),
        t.child
      );
    case 14:
      return (r = t.type), (o = Rt(r, t.pendingProps)), (o = Rt(r.type, o)), sm(e, t, r, o, n);
    case 15:
      return Fv(e, t, t.type, t.pendingProps, n);
    case 17:
      return (
        (r = t.type),
        (o = t.pendingProps),
        (o = t.elementType === r ? o : Rt(r, o)),
        Da(e, t),
        (t.tag = 1),
        it(r) ? ((e = !0), il(t)) : (e = !1),
        Co(t, n),
        Lv(t, r, o),
        uf(t, r, o, n),
        df(null, t, r, !0, e, n)
      );
    case 19:
      return Uv(e, t, n);
    case 22:
      return zv(e, t, n);
  }
  throw Error(B(156, t.tag));
};
function ix(e, t) {
  return R0(e, t);
}
function zk(e, t, n, r) {
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
function bt(e, t, n, r) {
  return new zk(e, t, n, r);
}
function qd(e) {
  return (e = e.prototype), !(!e || !e.isReactComponent);
}
function $k(e) {
  if (typeof e == "function") return qd(e) ? 1 : 0;
  if (e != null) {
    if (((e = e.$$typeof), e === yd)) return 11;
    if (e === vd) return 14;
  }
  return 2;
}
function Xn(e, t) {
  var n = e.alternate;
  return (
    n === null
      ? ((n = bt(e.tag, t, e.key, e.mode)),
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
function Va(e, t, n, r, o, i) {
  var s = 2;
  if (((r = e), typeof e == "function")) qd(e) && (s = 1);
  else if (typeof e == "string") s = 5;
  else
    e: switch (e) {
      case eo:
        return kr(n.children, o, i, t);
      case gd:
        (s = 8), (o |= 8);
        break;
      case Rc:
        return (e = bt(12, n, t, o | 2)), (e.elementType = Rc), (e.lanes = i), e;
      case Dc:
        return (e = bt(13, n, t, o)), (e.elementType = Dc), (e.lanes = i), e;
      case Ic:
        return (e = bt(19, n, t, o)), (e.elementType = Ic), (e.lanes = i), e;
      case m0:
        return Ql(n, o, i, t);
      default:
        if (typeof e == "object" && e !== null)
          switch (e.$$typeof) {
            case h0:
              s = 10;
              break e;
            case p0:
              s = 9;
              break e;
            case yd:
              s = 11;
              break e;
            case vd:
              s = 14;
              break e;
            case In:
              (s = 16), (r = null);
              break e;
          }
        throw Error(B(130, e == null ? e : typeof e, ""));
    }
  return (t = bt(s, n, t, o)), (t.elementType = e), (t.type = r), (t.lanes = i), t;
}
function kr(e, t, n, r) {
  return (e = bt(7, e, r, t)), (e.lanes = n), e;
}
function Ql(e, t, n, r) {
  return (
    (e = bt(22, e, r, t)), (e.elementType = m0), (e.lanes = n), (e.stateNode = { isHidden: !1 }), e
  );
}
function Xu(e, t, n) {
  return (e = bt(6, e, null, t)), (e.lanes = n), e;
}
function Zu(e, t, n) {
  return (
    (t = bt(4, e.children !== null ? e.children : [], e.key, t)),
    (t.lanes = n),
    (t.stateNode = {
      containerInfo: e.containerInfo,
      pendingChildren: null,
      implementation: e.implementation,
    }),
    t
  );
}
function jk(e, t, n, r, o) {
  (this.tag = t),
    (this.containerInfo = e),
    (this.finishedWork = this.pingCache = this.current = this.pendingChildren = null),
    (this.timeoutHandle = -1),
    (this.callbackNode = this.pendingContext = this.context = null),
    (this.callbackPriority = 0),
    (this.eventTimes = Mu(0)),
    (this.expirationTimes = Mu(-1)),
    (this.entangledLanes =
      this.finishedLanes =
      this.mutableReadLanes =
      this.expiredLanes =
      this.pingedLanes =
      this.suspendedLanes =
      this.pendingLanes =
        0),
    (this.entanglements = Mu(0)),
    (this.identifierPrefix = r),
    (this.onRecoverableError = o),
    (this.mutableSourceEagerHydrationData = null);
}
function Jd(e, t, n, r, o, i, s, a, l) {
  return (
    (e = new jk(e, t, n, a, l)),
    t === 1 ? ((t = 1), i === !0 && (t |= 8)) : (t = 0),
    (i = bt(3, null, null, t)),
    (e.current = i),
    (i.stateNode = e),
    (i.memoizedState = {
      element: r,
      isDehydrated: n,
      cache: null,
      transitions: null,
      pendingSuspenseBoundaries: null,
    }),
    Vd(i),
    e
  );
}
function Bk(e, t, n) {
  var r = 3 < arguments.length && arguments[3] !== void 0 ? arguments[3] : null;
  return {
    $$typeof: Jr,
    key: r == null ? null : "" + r,
    children: e,
    containerInfo: t,
    implementation: n,
  };
}
function sx(e) {
  if (!e) return qn;
  e = e._reactInternals;
  e: {
    if (Fr(e) !== e || e.tag !== 1) throw Error(B(170));
    var t = e;
    do {
      switch (t.tag) {
        case 3:
          t = t.stateNode.context;
          break e;
        case 1:
          if (it(t.type)) {
            t = t.stateNode.__reactInternalMemoizedMergedChildContext;
            break e;
          }
      }
      t = t.return;
    } while (t !== null);
    throw Error(B(171));
  }
  if (e.tag === 1) {
    var n = e.type;
    if (it(n)) return sv(e, n, t);
  }
  return t;
}
function ax(e, t, n, r, o, i, s, a, l) {
  return (
    (e = Jd(n, r, !0, e, o, i, s, a, l)),
    (e.context = sx(null)),
    (n = e.current),
    (r = Qe()),
    (o = Yn(n)),
    (i = mn(r, o)),
    (i.callback = t ?? null),
    Gn(n, i, o),
    (e.current.lanes = o),
    _s(e, o, r),
    st(e, r),
    e
  );
}
function ql(e, t, n, r) {
  var o = t.current,
    i = Qe(),
    s = Yn(o);
  return (
    (n = sx(n)),
    t.context === null ? (t.context = n) : (t.pendingContext = n),
    (t = mn(i, s)),
    (t.payload = { element: e }),
    (r = r === void 0 ? null : r),
    r !== null && (t.callback = r),
    (e = Gn(o, t, s)),
    e !== null && (Ft(e, o, s, i), Ma(e, o, s)),
    s
  );
}
function vl(e) {
  if (((e = e.current), !e.child)) return null;
  switch (e.child.tag) {
    case 5:
      return e.child.stateNode;
    default:
      return e.child.stateNode;
  }
}
function vm(e, t) {
  if (((e = e.memoizedState), e !== null && e.dehydrated !== null)) {
    var n = e.retryLane;
    e.retryLane = n !== 0 && n < t ? n : t;
  }
}
function eh(e, t) {
  vm(e, t), (e = e.alternate) && vm(e, t);
}
function Uk() {
  return null;
}
var lx =
  typeof reportError == "function"
    ? reportError
    : function (e) {
        console.error(e);
      };
function th(e) {
  this._internalRoot = e;
}
Jl.prototype.render = th.prototype.render = function (e) {
  var t = this._internalRoot;
  if (t === null) throw Error(B(409));
  ql(e, t, null, null);
};
Jl.prototype.unmount = th.prototype.unmount = function () {
  var e = this._internalRoot;
  if (e !== null) {
    this._internalRoot = null;
    var t = e.containerInfo;
    Dr(function () {
      ql(null, e, null, null);
    }),
      (t[wn] = null);
  }
};
function Jl(e) {
  this._internalRoot = e;
}
Jl.prototype.unstable_scheduleHydration = function (e) {
  if (e) {
    var t = z0();
    e = { blockedOn: null, target: e, priority: t };
    for (var n = 0; n < Fn.length && t !== 0 && t < Fn[n].priority; n++);
    Fn.splice(n, 0, e), n === 0 && j0(e);
  }
};
function nh(e) {
  return !(!e || (e.nodeType !== 1 && e.nodeType !== 9 && e.nodeType !== 11));
}
function eu(e) {
  return !(
    !e ||
    (e.nodeType !== 1 &&
      e.nodeType !== 9 &&
      e.nodeType !== 11 &&
      (e.nodeType !== 8 || e.nodeValue !== " react-mount-point-unstable "))
  );
}
function xm() {}
function Hk(e, t, n, r, o) {
  if (o) {
    if (typeof r == "function") {
      var i = r;
      r = function () {
        var u = vl(s);
        i.call(u);
      };
    }
    var s = ax(t, r, e, 0, null, !1, !1, "", xm);
    return (
      (e._reactRootContainer = s),
      (e[wn] = s.current),
      Ji(e.nodeType === 8 ? e.parentNode : e),
      Dr(),
      s
    );
  }
  for (; (o = e.lastChild); ) e.removeChild(o);
  if (typeof r == "function") {
    var a = r;
    r = function () {
      var u = vl(l);
      a.call(u);
    };
  }
  var l = Jd(e, 0, !1, null, null, !1, !1, "", xm);
  return (
    (e._reactRootContainer = l),
    (e[wn] = l.current),
    Ji(e.nodeType === 8 ? e.parentNode : e),
    Dr(function () {
      ql(t, l, n, r);
    }),
    l
  );
}
function tu(e, t, n, r, o) {
  var i = n._reactRootContainer;
  if (i) {
    var s = i;
    if (typeof o == "function") {
      var a = o;
      o = function () {
        var l = vl(s);
        a.call(l);
      };
    }
    ql(t, s, e, o);
  } else s = Hk(n, t, e, o, r);
  return vl(s);
}
O0 = function (e) {
  switch (e.tag) {
    case 3:
      var t = e.stateNode;
      if (t.current.memoizedState.isDehydrated) {
        var n = Ei(t.pendingLanes);
        n !== 0 && (Sd(t, n | 1), st(t, be()), !(te & 6) && ((Oo = be() + 500), rr()));
      }
      break;
    case 13:
      Dr(function () {
        var r = Sn(e, 1);
        if (r !== null) {
          var o = Qe();
          Ft(r, e, 1, o);
        }
      }),
        eh(e, 1);
  }
};
Ed = function (e) {
  if (e.tag === 13) {
    var t = Sn(e, 134217728);
    if (t !== null) {
      var n = Qe();
      Ft(t, e, 134217728, n);
    }
    eh(e, 134217728);
  }
};
F0 = function (e) {
  if (e.tag === 13) {
    var t = Yn(e),
      n = Sn(e, t);
    if (n !== null) {
      var r = Qe();
      Ft(n, e, t, r);
    }
    eh(e, t);
  }
};
z0 = function () {
  return ie;
};
$0 = function (e, t) {
  var n = ie;
  try {
    return (ie = e), t();
  } finally {
    ie = n;
  }
};
Hc = function (e, t, n) {
  switch (t) {
    case "input":
      if ((Oc(e, n), (t = n.name), n.type === "radio" && t != null)) {
        for (n = e; n.parentNode; ) n = n.parentNode;
        for (
          n = n.querySelectorAll("input[name=" + JSON.stringify("" + t) + '][type="radio"]'), t = 0;
          t < n.length;
          t++
        ) {
          var r = n[t];
          if (r !== e && r.form === e.form) {
            var o = Wl(r);
            if (!o) throw Error(B(90));
            y0(r), Oc(r, o);
          }
        }
      }
      break;
    case "textarea":
      x0(e, n);
      break;
    case "select":
      (t = n.value), t != null && xo(e, !!n.multiple, t, !1);
  }
};
_0 = Xd;
T0 = Dr;
var Wk = { usingClientEntryPoint: !1, Events: [Ns, oo, Wl, b0, k0, Xd] },
  fi = {
    findFiberByHostInstance: yr,
    bundleType: 0,
    version: "18.3.1",
    rendererPackageName: "react-dom",
  },
  Gk = {
    bundleType: fi.bundleType,
    version: fi.version,
    rendererPackageName: fi.rendererPackageName,
    rendererConfig: fi.rendererConfig,
    overrideHookState: null,
    overrideHookStateDeletePath: null,
    overrideHookStateRenamePath: null,
    overrideProps: null,
    overridePropsDeletePath: null,
    overridePropsRenamePath: null,
    setErrorHandler: null,
    setSuspenseHandler: null,
    scheduleUpdate: null,
    currentDispatcherRef: Tn.ReactCurrentDispatcher,
    findHostInstanceByFiber: function (e) {
      return (e = M0(e)), e === null ? null : e.stateNode;
    },
    findFiberByHostInstance: fi.findFiberByHostInstance || Uk,
    findHostInstancesForRefresh: null,
    scheduleRefresh: null,
    scheduleRoot: null,
    setRefreshHandler: null,
    getCurrentFiber: null,
    reconcilerVersion: "18.3.1-next-f1338f8080-20240426",
  };
if (typeof __REACT_DEVTOOLS_GLOBAL_HOOK__ < "u") {
  var oa = __REACT_DEVTOOLS_GLOBAL_HOOK__;
  if (!oa.isDisabled && oa.supportsFiber)
    try {
      (jl = oa.inject(Gk)), (Zt = oa);
    } catch {}
}
gt.__SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED = Wk;
gt.createPortal = function (e, t) {
  var n = 2 < arguments.length && arguments[2] !== void 0 ? arguments[2] : null;
  if (!nh(t)) throw Error(B(200));
  return Bk(e, t, null, n);
};
gt.createRoot = function (e, t) {
  if (!nh(e)) throw Error(B(299));
  var n = !1,
    r = "",
    o = lx;
  return (
    t != null &&
      (t.unstable_strictMode === !0 && (n = !0),
      t.identifierPrefix !== void 0 && (r = t.identifierPrefix),
      t.onRecoverableError !== void 0 && (o = t.onRecoverableError)),
    (t = Jd(e, 1, !1, null, null, n, !1, r, o)),
    (e[wn] = t.current),
    Ji(e.nodeType === 8 ? e.parentNode : e),
    new th(t)
  );
};
gt.findDOMNode = function (e) {
  if (e == null) return null;
  if (e.nodeType === 1) return e;
  var t = e._reactInternals;
  if (t === void 0)
    throw typeof e.render == "function"
      ? Error(B(188))
      : ((e = Object.keys(e).join(",")), Error(B(268, e)));
  return (e = M0(t)), (e = e === null ? null : e.stateNode), e;
};
gt.flushSync = function (e) {
  return Dr(e);
};
gt.hydrate = function (e, t, n) {
  if (!eu(t)) throw Error(B(200));
  return tu(null, e, t, !0, n);
};
gt.hydrateRoot = function (e, t, n) {
  if (!nh(e)) throw Error(B(405));
  var r = (n != null && n.hydratedSources) || null,
    o = !1,
    i = "",
    s = lx;
  if (
    (n != null &&
      (n.unstable_strictMode === !0 && (o = !0),
      n.identifierPrefix !== void 0 && (i = n.identifierPrefix),
      n.onRecoverableError !== void 0 && (s = n.onRecoverableError)),
    (t = ax(t, null, e, 1, n ?? null, o, !1, i, s)),
    (e[wn] = t.current),
    Ji(e),
    r)
  )
    for (e = 0; e < r.length; e++)
      (n = r[e]),
        (o = n._getVersion),
        (o = o(n._source)),
        t.mutableSourceEagerHydrationData == null
          ? (t.mutableSourceEagerHydrationData = [n, o])
          : t.mutableSourceEagerHydrationData.push(n, o);
  return new Jl(t);
};
gt.render = function (e, t, n) {
  if (!eu(t)) throw Error(B(200));
  return tu(null, e, t, !1, n);
};
gt.unmountComponentAtNode = function (e) {
  if (!eu(e)) throw Error(B(40));
  return e._reactRootContainer
    ? (Dr(function () {
        tu(null, null, e, !1, function () {
          (e._reactRootContainer = null), (e[wn] = null);
        });
      }),
      !0)
    : !1;
};
gt.unstable_batchedUpdates = Xd;
gt.unstable_renderSubtreeIntoContainer = function (e, t, n, r) {
  if (!eu(n)) throw Error(B(200));
  if (e == null || e._reactInternals === void 0) throw Error(B(38));
  return tu(e, t, n, !1, r);
};
gt.version = "18.3.1-next-f1338f8080-20240426";
function ux() {
  if (
    !(
      typeof __REACT_DEVTOOLS_GLOBAL_HOOK__ > "u" ||
      typeof __REACT_DEVTOOLS_GLOBAL_HOOK__.checkDCE != "function"
    )
  )
    try {
      __REACT_DEVTOOLS_GLOBAL_HOOK__.checkDCE(ux);
    } catch (e) {
      console.error(e);
    }
}
ux(), (u0.exports = gt);
var rh = u0.exports;
const Kk = ld(rh);
var wm = rh;
(Mc.createRoot = wm.createRoot), (Mc.hydrateRoot = wm.hydrateRoot);
const Yk = {},
  Sm = (e) => {
    let t;
    const n = new Set(),
      r = (c, f) => {
        const d = typeof c == "function" ? c(t) : c;
        if (!Object.is(d, t)) {
          const p = t;
          (t = (f ?? (typeof d != "object" || d === null)) ? d : Object.assign({}, t, d)),
            n.forEach((y) => y(t, p));
        }
      },
      o = () => t,
      l = {
        setState: r,
        getState: o,
        getInitialState: () => u,
        subscribe: (c) => (n.add(c), () => n.delete(c)),
        destroy: () => {
          (Yk ? "production" : void 0) !== "production" &&
            console.warn(
              "[DEPRECATED] The `destroy` method will be unsupported in a future version. Instead use unsubscribe function returned by subscribe. Everything will be garbage-collected if store is garbage-collected.",
            ),
            n.clear();
        },
      },
      u = (t = e(r, o, l));
    return l;
  },
  cx = (e) => (e ? Sm(e) : Sm);
var fx = { exports: {} },
  dx = {},
  hx = { exports: {} },
  px = {};
/**
 * @license React
 * use-sync-external-store-shim.production.js
 *
 * Copyright (c) Meta Platforms, Inc. and affiliates.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */ var Fo = v;
function Xk(e, t) {
  return (e === t && (e !== 0 || 1 / e === 1 / t)) || (e !== e && t !== t);
}
var Zk = typeof Object.is == "function" ? Object.is : Xk,
  Qk = Fo.useState,
  qk = Fo.useEffect,
  Jk = Fo.useLayoutEffect,
  e_ = Fo.useDebugValue;
function t_(e, t) {
  var n = t(),
    r = Qk({ inst: { value: n, getSnapshot: t } }),
    o = r[0].inst,
    i = r[1];
  return (
    Jk(
      function () {
        (o.value = n), (o.getSnapshot = t), Qu(o) && i({ inst: o });
      },
      [e, n, t],
    ),
    qk(
      function () {
        return (
          Qu(o) && i({ inst: o }),
          e(function () {
            Qu(o) && i({ inst: o });
          })
        );
      },
      [e],
    ),
    e_(n),
    n
  );
}
function Qu(e) {
  var t = e.getSnapshot;
  e = e.value;
  try {
    var n = t();
    return !Zk(e, n);
  } catch {
    return !0;
  }
}
function n_(e, t) {
  return t();
}
var r_ =
  typeof window > "u" || typeof window.document > "u" || typeof window.document.createElement > "u"
    ? n_
    : t_;
px.useSyncExternalStore = Fo.useSyncExternalStore !== void 0 ? Fo.useSyncExternalStore : r_;
hx.exports = px;
var o_ = hx.exports;
/**
 * @license React
 * use-sync-external-store-shim/with-selector.production.js
 *
 * Copyright (c) Meta Platforms, Inc. and affiliates.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */ var nu = v,
  i_ = o_;
function s_(e, t) {
  return (e === t && (e !== 0 || 1 / e === 1 / t)) || (e !== e && t !== t);
}
var a_ = typeof Object.is == "function" ? Object.is : s_,
  l_ = i_.useSyncExternalStore,
  u_ = nu.useRef,
  c_ = nu.useEffect,
  f_ = nu.useMemo,
  d_ = nu.useDebugValue;
dx.useSyncExternalStoreWithSelector = function (e, t, n, r, o) {
  var i = u_(null);
  if (i.current === null) {
    var s = { hasValue: !1, value: null };
    i.current = s;
  } else s = i.current;
  i = f_(
    function () {
      function l(p) {
        if (!u) {
          if (((u = !0), (c = p), (p = r(p)), o !== void 0 && s.hasValue)) {
            var y = s.value;
            if (o(y, p)) return (f = y);
          }
          return (f = p);
        }
        if (((y = f), a_(c, p))) return y;
        var m = r(p);
        return o !== void 0 && o(y, m) ? ((c = p), y) : ((c = p), (f = m));
      }
      var u = !1,
        c,
        f,
        d = n === void 0 ? null : n;
      return [
        function () {
          return l(t());
        },
        d === null
          ? void 0
          : function () {
              return l(d());
            },
      ];
    },
    [t, n, r, o],
  );
  var a = l_(e, i[0], i[1]);
  return (
    c_(
      function () {
        (s.hasValue = !0), (s.value = a);
      },
      [a],
    ),
    d_(a),
    a
  );
};
fx.exports = dx;
var h_ = fx.exports;
const mx = ld(h_),
  gx = {},
  { useDebugValue: p_ } = L,
  { useSyncExternalStoreWithSelector: m_ } = mx;
let Em = !1;
const g_ = (e) => e;
function y_(e, t = g_, n) {
  (gx ? "production" : void 0) !== "production" &&
    n &&
    !Em &&
    (console.warn(
      "[DEPRECATED] Use `createWithEqualityFn` instead of `create` or use `useStoreWithEqualityFn` instead of `useStore`. They can be imported from 'zustand/traditional'. https://github.com/pmndrs/zustand/discussions/1937",
    ),
    (Em = !0));
  const r = m_(e.subscribe, e.getState, e.getServerState || e.getInitialState, t, n);
  return p_(r), r;
}
const Cm = (e) => {
    (gx ? "production" : void 0) !== "production" &&
      typeof e != "function" &&
      console.warn(
        "[DEPRECATED] Passing a vanilla store will be unsupported in a future version. Instead use `import { useStore } from 'zustand'`.",
      );
    const t = typeof e == "function" ? cx(e) : e,
      n = (r, o) => y_(t, r, o);
    return Object.assign(n, t), n;
  },
  v_ = (e) => (e ? Cm(e) : Cm),
  ls = v_((e, t) => ({
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
            const o = JSON.parse(r.data),
              {
                addMachine: i,
                updateMachineTransition: s,
                addService: a,
                removeService: l,
                addLog: u,
              } = t();
            switch (o.type) {
              case "machine_registered":
                i(o.payload);
                break;
              case "transition":
                s(o.payload);
                break;
              case "service_invoked":
                a(o.payload);
                break;
              case "service_stopped":
                l(o.payload);
                break;
              default:
                t().machines[o.machine_id] &&
                  u(o.machine_id, { type: o.type, payload: o.payload, ...o });
                break;
            }
          } catch (o) {
            console.error("Failed to parse WebSocket message:", r.data, o);
          }
        }),
        e({ ws: n });
    },
    sendCommand: (n, r = {}) => {
      const o = t().ws;
      o && o.readyState === WebSocket.OPEN
        ? o.send(JSON.stringify({ command: n, ...r }))
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
        const o = r.machines[n.machine_id];
        if (!o) return r;
        const i = o.currentStateIds.length > 0 ? o.currentStateIds[0] : "",
          s = n.to_state_ids.length > 0 ? n.to_state_ids[0] : "";
        return {
          machines: {
            ...r.machines,
            [n.machine_id]: {
              ...o,
              currentStateIds: n.to_state_ids,
              context: n.full_context,
              lastTransition: { sourceId: i, targetId: s, event: n.event },
              logs: [...o.logs, { type: "transition", payload: n }],
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
        const o = r.machines[n.machine_id];
        return o
          ? {
              machines: {
                ...r.machines,
                [n.machine_id]: {
                  ...o,
                  services: { ...o.services, [n.id]: { src: n.service, status: "running" } },
                  logs: [...o.logs, { type: "service_invoked", payload: n }],
                },
              },
            }
          : r;
      }),
    removeService: (n) =>
      e((r) => {
        const o = r.machines[n.machine_id];
        if (!o) return r;
        const i = { ...o.services };
        return (
          delete i[n.id], { machines: { ...r.machines, [n.machine_id]: { ...o, services: i } } }
        );
      }),
    addLog: (n, r) =>
      e((o) => {
        const i = o.machines[n];
        return i ? { machines: { ...o.machines, [n]: { ...i, logs: [...i.logs, r] } } } : o;
      }),
  })),
  x_ = () => {
    const e = ls((t) => t.connect);
    v.useEffect(() => {
      e();
    }, [e]);
  };
/**
 * @license lucide-react v0.379.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */ const w_ = (e) => e.replace(/([a-z0-9])([A-Z])/g, "$1-$2").toLowerCase(),
  yx = (...e) => e.filter((t, n, r) => !!t && r.indexOf(t) === n).join(" ");
/**
 * @license lucide-react v0.379.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */ var S_ = {
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
 */ const E_ = v.forwardRef(
  (
    {
      color: e = "currentColor",
      size: t = 24,
      strokeWidth: n = 2,
      absoluteStrokeWidth: r,
      className: o = "",
      children: i,
      iconNode: s,
      ...a
    },
    l,
  ) =>
    v.createElement(
      "svg",
      {
        ref: l,
        ...S_,
        width: t,
        height: t,
        stroke: e,
        strokeWidth: r ? (Number(n) * 24) / Number(t) : n,
        className: yx("lucide", o),
        ...a,
      },
      [...s.map(([u, c]) => v.createElement(u, c)), ...(Array.isArray(i) ? i : [i])],
    ),
);
/**
 * @license lucide-react v0.379.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */ const at = (e, t) => {
  const n = v.forwardRef(({ className: r, ...o }, i) =>
    v.createElement(E_, { ref: i, iconNode: t, className: yx(`lucide-${w_(e)}`, r), ...o }),
  );
  return (n.displayName = `${e}`), n;
};
/**
 * @license lucide-react v0.379.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */ const C_ = at("Bot", [
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
 */ const b_ = at("FileJson", [
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
 */ const k_ = at("History", [
  ["path", { d: "M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8", key: "1357e3" }],
  ["path", { d: "M3 3v5h5", key: "1xhq8a" }],
  ["path", { d: "M12 7v5l4 2", key: "1fdv2h" }],
]);
/**
 * @license lucide-react v0.379.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */ const __ = at("Moon", [["path", { d: "M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z", key: "a7tn18" }]]);
/**
 * @license lucide-react v0.379.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */ const T_ = at("Pause", [
  ["rect", { x: "14", y: "4", width: "4", height: "16", rx: "1", key: "zuxfzm" }],
  ["rect", { x: "6", y: "4", width: "4", height: "16", rx: "1", key: "1okwgv" }],
]);
/**
 * @license lucide-react v0.379.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */ const N_ = at("Play", [["polygon", { points: "6 3 20 12 6 21 6 3", key: "1oa8hb" }]]);
/**
 * @license lucide-react v0.379.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */ const P_ = at("RadioTower", [
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
 */ const M_ = at("Send", [
  ["path", { d: "m22 2-7 20-4-9-9-4Z", key: "1q3vgg" }],
  ["path", { d: "M22 2 11 13", key: "nzbqef" }],
]);
/**
 * @license lucide-react v0.379.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */ const A_ = at("SquareActivity", [
  ["rect", { width: "18", height: "18", x: "3", y: "3", rx: "2", key: "afitv7" }],
  ["path", { d: "M17 12h-2l-2 5-2-10-2 5H7", key: "15hlnc" }],
]);
/**
 * @license lucide-react v0.379.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */ const R_ = at("Sun", [
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
 */ const D_ = at("WifiOff", [
  ["path", { d: "M12 20h.01", key: "zekei9" }],
  ["path", { d: "M8.5 16.429a5 5 0 0 1 7 0", key: "1bycff" }],
  ["path", { d: "M5 12.859a10 10 0 0 1 5.17-2.69", key: "1dl1wf" }],
  ["path", { d: "M19 12.859a10 10 0 0 0-2.007-1.523", key: "4k23kn" }],
  ["path", { d: "M2 8.82a15 15 0 0 1 4.177-2.643", key: "1grhjp" }],
  ["path", { d: "M22 8.82a15 15 0 0 0-11.288-3.764", key: "z3jwby" }],
  ["path", { d: "m2 2 20 20", key: "1ooewy" }],
]);
/**
 * @license lucide-react v0.379.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */ const I_ = at("Wifi", [
  ["path", { d: "M12 20h.01", key: "zekei9" }],
  ["path", { d: "M2 8.82a15 15 0 0 1 20 0", key: "dnpr2z" }],
  ["path", { d: "M5 12.859a10 10 0 0 1 14 0", key: "1x1e6c" }],
  ["path", { d: "M8.5 16.429a5 5 0 0 1 7 0", key: "1bycff" }],
]);
/**
 * @license lucide-react v0.379.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */ const L_ = at("X", [
  ["path", { d: "M18 6 6 18", key: "1bl5f8" }],
  ["path", { d: "m6 6 12 12", key: "d8bk6v" }],
]);
/**
 * @license lucide-react v0.379.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */ const V_ = at("Zap", [
  [
    "path",
    {
      d: "M4 14a1 1 0 0 1-.78-1.63l9.9-10.2a.5.5 0 0 1 .86.46l-1.92 6.02A1 1 0 0 0 13 10h7a1 1 0 0 1 .78 1.63l-9.9 10.2a.5.5 0 0 1-.86-.46l1.92-6.02A1 1 0 0 0 11 14z",
      key: "1xq2db",
    },
  ],
]);
function bm(e, t) {
  if (typeof e == "function") return e(t);
  e != null && (e.current = t);
}
function vx(...e) {
  return (t) => {
    let n = !1;
    const r = e.map((o) => {
      const i = bm(o, t);
      return !n && typeof i == "function" && (n = !0), i;
    });
    if (n)
      return () => {
        for (let o = 0; o < r.length; o++) {
          const i = r[o];
          typeof i == "function" ? i() : bm(e[o], null);
        }
      };
  };
}
function tn(...e) {
  return v.useCallback(vx(...e), e);
}
function us(e) {
  const t = F_(e),
    n = v.forwardRef((r, o) => {
      const { children: i, ...s } = r,
        a = v.Children.toArray(i),
        l = a.find($_);
      if (l) {
        const u = l.props.children,
          c = a.map((f) =>
            f === l
              ? v.Children.count(u) > 1
                ? v.Children.only(null)
                : v.isValidElement(u)
                  ? u.props.children
                  : null
              : f,
          );
        return N.jsx(t, {
          ...s,
          ref: o,
          children: v.isValidElement(u) ? v.cloneElement(u, void 0, c) : null,
        });
      }
      return N.jsx(t, { ...s, ref: o, children: i });
    });
  return (n.displayName = `${e}.Slot`), n;
}
var O_ = us("Slot");
function F_(e) {
  const t = v.forwardRef((n, r) => {
    const { children: o, ...i } = n;
    if (v.isValidElement(o)) {
      const s = B_(o),
        a = j_(i, o.props);
      return o.type !== v.Fragment && (a.ref = r ? vx(r, s) : s), v.cloneElement(o, a);
    }
    return v.Children.count(o) > 1 ? v.Children.only(null) : null;
  });
  return (t.displayName = `${e}.SlotClone`), t;
}
var z_ = Symbol("radix.slottable");
function $_(e) {
  return (
    v.isValidElement(e) &&
    typeof e.type == "function" &&
    "__radixId" in e.type &&
    e.type.__radixId === z_
  );
}
function j_(e, t) {
  const n = { ...t };
  for (const r in t) {
    const o = e[r],
      i = t[r];
    /^on[A-Z]/.test(r)
      ? o && i
        ? (n[r] = (...a) => {
            const l = i(...a);
            return o(...a), l;
          })
        : o && (n[r] = o)
      : r === "style"
        ? (n[r] = { ...o, ...i })
        : r === "className" && (n[r] = [o, i].filter(Boolean).join(" "));
  }
  return { ...e, ...n };
}
function B_(e) {
  var r, o;
  let t = (r = Object.getOwnPropertyDescriptor(e.props, "ref")) == null ? void 0 : r.get,
    n = t && "isReactWarning" in t && t.isReactWarning;
  return n
    ? e.ref
    : ((t = (o = Object.getOwnPropertyDescriptor(e, "ref")) == null ? void 0 : o.get),
      (n = t && "isReactWarning" in t && t.isReactWarning),
      n ? e.props.ref : e.props.ref || e.ref);
}
function xx(e) {
  var t,
    n,
    r = "";
  if (typeof e == "string" || typeof e == "number") r += e;
  else if (typeof e == "object")
    if (Array.isArray(e)) {
      var o = e.length;
      for (t = 0; t < o; t++) e[t] && (n = xx(e[t])) && (r && (r += " "), (r += n));
    } else for (n in e) e[n] && (r && (r += " "), (r += n));
  return r;
}
function wx() {
  for (var e, t, n = 0, r = "", o = arguments.length; n < o; n++)
    (e = arguments[n]) && (t = xx(e)) && (r && (r += " "), (r += t));
  return r;
}
const km = (e) => (typeof e == "boolean" ? `${e}` : e === 0 ? "0" : e),
  _m = wx,
  Sx = (e, t) => (n) => {
    var r;
    if ((t == null ? void 0 : t.variants) == null)
      return _m(e, n == null ? void 0 : n.class, n == null ? void 0 : n.className);
    const { variants: o, defaultVariants: i } = t,
      s = Object.keys(o).map((u) => {
        const c = n == null ? void 0 : n[u],
          f = i == null ? void 0 : i[u];
        if (c === null) return null;
        const d = km(c) || km(f);
        return o[u][d];
      }),
      a =
        n &&
        Object.entries(n).reduce((u, c) => {
          let [f, d] = c;
          return d === void 0 || (u[f] = d), u;
        }, {}),
      l =
        t == null || (r = t.compoundVariants) === null || r === void 0
          ? void 0
          : r.reduce((u, c) => {
              let { class: f, className: d, ...p } = c;
              return Object.entries(p).every((y) => {
                let [m, w] = y;
                return Array.isArray(w) ? w.includes({ ...i, ...a }[m]) : { ...i, ...a }[m] === w;
              })
                ? [...u, f, d]
                : u;
            }, []);
    return _m(e, s, l, n == null ? void 0 : n.class, n == null ? void 0 : n.className);
  },
  oh = "-",
  U_ = (e) => {
    const t = W_(e),
      { conflictingClassGroups: n, conflictingClassGroupModifiers: r } = e;
    return {
      getClassGroupId: (s) => {
        const a = s.split(oh);
        return a[0] === "" && a.length !== 1 && a.shift(), Ex(a, t) || H_(s);
      },
      getConflictingClassGroupIds: (s, a) => {
        const l = n[s] || [];
        return a && r[s] ? [...l, ...r[s]] : l;
      },
    };
  },
  Ex = (e, t) => {
    var s;
    if (e.length === 0) return t.classGroupId;
    const n = e[0],
      r = t.nextPart.get(n),
      o = r ? Ex(e.slice(1), r) : void 0;
    if (o) return o;
    if (t.validators.length === 0) return;
    const i = e.join(oh);
    return (s = t.validators.find(({ validator: a }) => a(i))) == null ? void 0 : s.classGroupId;
  },
  Tm = /^\[(.+)\]$/,
  H_ = (e) => {
    if (Tm.test(e)) {
      const t = Tm.exec(e)[1],
        n = t == null ? void 0 : t.substring(0, t.indexOf(":"));
      if (n) return "arbitrary.." + n;
    }
  },
  W_ = (e) => {
    const { theme: t, prefix: n } = e,
      r = { nextPart: new Map(), validators: [] };
    return (
      K_(Object.entries(e.classGroups), n).forEach(([i, s]) => {
        bf(s, r, i, t);
      }),
      r
    );
  },
  bf = (e, t, n, r) => {
    e.forEach((o) => {
      if (typeof o == "string") {
        const i = o === "" ? t : Nm(t, o);
        i.classGroupId = n;
        return;
      }
      if (typeof o == "function") {
        if (G_(o)) {
          bf(o(r), t, n, r);
          return;
        }
        t.validators.push({ validator: o, classGroupId: n });
        return;
      }
      Object.entries(o).forEach(([i, s]) => {
        bf(s, Nm(t, i), n, r);
      });
    });
  },
  Nm = (e, t) => {
    let n = e;
    return (
      t.split(oh).forEach((r) => {
        n.nextPart.has(r) || n.nextPart.set(r, { nextPart: new Map(), validators: [] }),
          (n = n.nextPart.get(r));
      }),
      n
    );
  },
  G_ = (e) => e.isThemeGetter,
  K_ = (e, t) =>
    t
      ? e.map(([n, r]) => {
          const o = r.map((i) =>
            typeof i == "string"
              ? t + i
              : typeof i == "object"
                ? Object.fromEntries(Object.entries(i).map(([s, a]) => [t + s, a]))
                : i,
          );
          return [n, o];
        })
      : e,
  Y_ = (e) => {
    if (e < 1) return { get: () => {}, set: () => {} };
    let t = 0,
      n = new Map(),
      r = new Map();
    const o = (i, s) => {
      n.set(i, s), t++, t > e && ((t = 0), (r = n), (n = new Map()));
    };
    return {
      get(i) {
        let s = n.get(i);
        if (s !== void 0) return s;
        if ((s = r.get(i)) !== void 0) return o(i, s), s;
      },
      set(i, s) {
        n.has(i) ? n.set(i, s) : o(i, s);
      },
    };
  },
  Cx = "!",
  X_ = (e) => {
    const { separator: t, experimentalParseClassName: n } = e,
      r = t.length === 1,
      o = t[0],
      i = t.length,
      s = (a) => {
        const l = [];
        let u = 0,
          c = 0,
          f;
        for (let w = 0; w < a.length; w++) {
          let h = a[w];
          if (u === 0) {
            if (h === o && (r || a.slice(w, w + i) === t)) {
              l.push(a.slice(c, w)), (c = w + i);
              continue;
            }
            if (h === "/") {
              f = w;
              continue;
            }
          }
          h === "[" ? u++ : h === "]" && u--;
        }
        const d = l.length === 0 ? a : a.substring(c),
          p = d.startsWith(Cx),
          y = p ? d.substring(1) : d,
          m = f && f > c ? f - c : void 0;
        return {
          modifiers: l,
          hasImportantModifier: p,
          baseClassName: y,
          maybePostfixModifierPosition: m,
        };
      };
    return n ? (a) => n({ className: a, parseClassName: s }) : s;
  },
  Z_ = (e) => {
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
  Q_ = (e) => ({ cache: Y_(e.cacheSize), parseClassName: X_(e), ...U_(e) }),
  q_ = /\s+/,
  J_ = (e, t) => {
    const { parseClassName: n, getClassGroupId: r, getConflictingClassGroupIds: o } = t,
      i = [],
      s = e.trim().split(q_);
    let a = "";
    for (let l = s.length - 1; l >= 0; l -= 1) {
      const u = s[l],
        {
          modifiers: c,
          hasImportantModifier: f,
          baseClassName: d,
          maybePostfixModifierPosition: p,
        } = n(u);
      let y = !!p,
        m = r(y ? d.substring(0, p) : d);
      if (!m) {
        if (!y) {
          a = u + (a.length > 0 ? " " + a : a);
          continue;
        }
        if (((m = r(d)), !m)) {
          a = u + (a.length > 0 ? " " + a : a);
          continue;
        }
        y = !1;
      }
      const w = Z_(c).join(":"),
        h = f ? w + Cx : w,
        g = h + m;
      if (i.includes(g)) continue;
      i.push(g);
      const x = o(m, y);
      for (let S = 0; S < x.length; ++S) {
        const E = x[S];
        i.push(h + E);
      }
      a = u + (a.length > 0 ? " " + a : a);
    }
    return a;
  };
function eT() {
  let e = 0,
    t,
    n,
    r = "";
  for (; e < arguments.length; ) (t = arguments[e++]) && (n = bx(t)) && (r && (r += " "), (r += n));
  return r;
}
const bx = (e) => {
  if (typeof e == "string") return e;
  let t,
    n = "";
  for (let r = 0; r < e.length; r++) e[r] && (t = bx(e[r])) && (n && (n += " "), (n += t));
  return n;
};
function tT(e, ...t) {
  let n,
    r,
    o,
    i = s;
  function s(l) {
    const u = t.reduce((c, f) => f(c), e());
    return (n = Q_(u)), (r = n.cache.get), (o = n.cache.set), (i = a), a(l);
  }
  function a(l) {
    const u = r(l);
    if (u) return u;
    const c = J_(l, n);
    return o(l, c), c;
  }
  return function () {
    return i(eT.apply(null, arguments));
  };
}
const fe = (e) => {
    const t = (n) => n[e] || [];
    return (t.isThemeGetter = !0), t;
  },
  kx = /^\[(?:([a-z-]+):)?(.+)\]$/i,
  nT = /^\d+\/\d+$/,
  rT = new Set(["px", "full", "screen"]),
  oT = /^(\d+(\.\d+)?)?(xs|sm|md|lg|xl)$/,
  iT =
    /\d+(%|px|r?em|[sdl]?v([hwib]|min|max)|pt|pc|in|cm|mm|cap|ch|ex|r?lh|cq(w|h|i|b|min|max))|\b(calc|min|max|clamp)\(.+\)|^0$/,
  sT = /^(rgba?|hsla?|hwb|(ok)?(lab|lch))\(.+\)$/,
  aT = /^(inset_)?-?((\d+)?\.?(\d+)[a-z]+|0)_-?((\d+)?\.?(\d+)[a-z]+|0)/,
  lT =
    /^(url|image|image-set|cross-fade|element|(repeating-)?(linear|radial|conic)-gradient)\(.+\)$/,
  an = (e) => ko(e) || rT.has(e) || nT.test(e),
  Pn = (e) => Zo(e, "length", gT),
  ko = (e) => !!e && !Number.isNaN(Number(e)),
  qu = (e) => Zo(e, "number", ko),
  di = (e) => !!e && Number.isInteger(Number(e)),
  uT = (e) => e.endsWith("%") && ko(e.slice(0, -1)),
  Q = (e) => kx.test(e),
  Mn = (e) => oT.test(e),
  cT = new Set(["length", "size", "percentage"]),
  fT = (e) => Zo(e, cT, _x),
  dT = (e) => Zo(e, "position", _x),
  hT = new Set(["image", "url"]),
  pT = (e) => Zo(e, hT, vT),
  mT = (e) => Zo(e, "", yT),
  hi = () => !0,
  Zo = (e, t, n) => {
    const r = kx.exec(e);
    return r ? (r[1] ? (typeof t == "string" ? r[1] === t : t.has(r[1])) : n(r[2])) : !1;
  },
  gT = (e) => iT.test(e) && !sT.test(e),
  _x = () => !1,
  yT = (e) => aT.test(e),
  vT = (e) => lT.test(e),
  xT = () => {
    const e = fe("colors"),
      t = fe("spacing"),
      n = fe("blur"),
      r = fe("brightness"),
      o = fe("borderColor"),
      i = fe("borderRadius"),
      s = fe("borderSpacing"),
      a = fe("borderWidth"),
      l = fe("contrast"),
      u = fe("grayscale"),
      c = fe("hueRotate"),
      f = fe("invert"),
      d = fe("gap"),
      p = fe("gradientColorStops"),
      y = fe("gradientColorStopPositions"),
      m = fe("inset"),
      w = fe("margin"),
      h = fe("opacity"),
      g = fe("padding"),
      x = fe("saturate"),
      S = fe("scale"),
      E = fe("sepia"),
      C = fe("skew"),
      b = fe("space"),
      _ = fe("translate"),
      A = () => ["auto", "contain", "none"],
      R = () => ["auto", "hidden", "clip", "visible", "scroll"],
      z = () => ["auto", Q, t],
      F = () => [Q, t],
      j = () => ["", an, Pn],
      k = () => ["auto", ko, Q],
      I = () => [
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
      M = () => ["solid", "dashed", "dotted", "double", "none"],
      V = () => [
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
      P = () => ["start", "end", "center", "between", "around", "evenly", "stretch"],
      T = () => ["", "0", Q],
      D = () => ["auto", "avoid", "all", "avoid-page", "page", "left", "right", "column"],
      O = () => [ko, Q];
    return {
      cacheSize: 500,
      separator: ":",
      theme: {
        colors: [hi],
        spacing: [an, Pn],
        blur: ["none", "", Mn, Q],
        brightness: O(),
        borderColor: [e],
        borderRadius: ["none", "", "full", Mn, Q],
        borderSpacing: F(),
        borderWidth: j(),
        contrast: O(),
        grayscale: T(),
        hueRotate: O(),
        invert: T(),
        gap: F(),
        gradientColorStops: [e],
        gradientColorStopPositions: [uT, Pn],
        inset: z(),
        margin: z(),
        opacity: O(),
        padding: F(),
        saturate: O(),
        scale: O(),
        sepia: T(),
        skew: O(),
        space: F(),
        translate: F(),
      },
      classGroups: {
        aspect: [{ aspect: ["auto", "square", "video", Q] }],
        container: ["container"],
        columns: [{ columns: [Mn] }],
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
        "object-position": [{ object: [...I(), Q] }],
        overflow: [{ overflow: R() }],
        "overflow-x": [{ "overflow-x": R() }],
        "overflow-y": [{ "overflow-y": R() }],
        overscroll: [{ overscroll: A() }],
        "overscroll-x": [{ "overscroll-x": A() }],
        "overscroll-y": [{ "overscroll-y": A() }],
        position: ["static", "fixed", "absolute", "relative", "sticky"],
        inset: [{ inset: [m] }],
        "inset-x": [{ "inset-x": [m] }],
        "inset-y": [{ "inset-y": [m] }],
        start: [{ start: [m] }],
        end: [{ end: [m] }],
        top: [{ top: [m] }],
        right: [{ right: [m] }],
        bottom: [{ bottom: [m] }],
        left: [{ left: [m] }],
        visibility: ["visible", "invisible", "collapse"],
        z: [{ z: ["auto", di, Q] }],
        basis: [{ basis: z() }],
        "flex-direction": [{ flex: ["row", "row-reverse", "col", "col-reverse"] }],
        "flex-wrap": [{ flex: ["wrap", "wrap-reverse", "nowrap"] }],
        flex: [{ flex: ["1", "auto", "initial", "none", Q] }],
        grow: [{ grow: T() }],
        shrink: [{ shrink: T() }],
        order: [{ order: ["first", "last", "none", di, Q] }],
        "grid-cols": [{ "grid-cols": [hi] }],
        "col-start-end": [{ col: ["auto", { span: ["full", di, Q] }, Q] }],
        "col-start": [{ "col-start": k() }],
        "col-end": [{ "col-end": k() }],
        "grid-rows": [{ "grid-rows": [hi] }],
        "row-start-end": [{ row: ["auto", { span: [di, Q] }, Q] }],
        "row-start": [{ "row-start": k() }],
        "row-end": [{ "row-end": k() }],
        "grid-flow": [{ "grid-flow": ["row", "col", "dense", "row-dense", "col-dense"] }],
        "auto-cols": [{ "auto-cols": ["auto", "min", "max", "fr", Q] }],
        "auto-rows": [{ "auto-rows": ["auto", "min", "max", "fr", Q] }],
        gap: [{ gap: [d] }],
        "gap-x": [{ "gap-x": [d] }],
        "gap-y": [{ "gap-y": [d] }],
        "justify-content": [{ justify: ["normal", ...P()] }],
        "justify-items": [{ "justify-items": ["start", "end", "center", "stretch"] }],
        "justify-self": [{ "justify-self": ["auto", "start", "end", "center", "stretch"] }],
        "align-content": [{ content: ["normal", ...P(), "baseline"] }],
        "align-items": [{ items: ["start", "end", "center", "baseline", "stretch"] }],
        "align-self": [{ self: ["auto", "start", "end", "center", "stretch", "baseline"] }],
        "place-content": [{ "place-content": [...P(), "baseline"] }],
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
        m: [{ m: [w] }],
        mx: [{ mx: [w] }],
        my: [{ my: [w] }],
        ms: [{ ms: [w] }],
        me: [{ me: [w] }],
        mt: [{ mt: [w] }],
        mr: [{ mr: [w] }],
        mb: [{ mb: [w] }],
        ml: [{ ml: [w] }],
        "space-x": [{ "space-x": [b] }],
        "space-x-reverse": ["space-x-reverse"],
        "space-y": [{ "space-y": [b] }],
        "space-y-reverse": ["space-y-reverse"],
        w: [{ w: ["auto", "min", "max", "fit", "svw", "lvw", "dvw", Q, t] }],
        "min-w": [{ "min-w": [Q, t, "min", "max", "fit"] }],
        "max-w": [
          { "max-w": [Q, t, "none", "full", "min", "max", "fit", "prose", { screen: [Mn] }, Mn] },
        ],
        h: [{ h: [Q, t, "auto", "min", "max", "fit", "svh", "lvh", "dvh"] }],
        "min-h": [{ "min-h": [Q, t, "min", "max", "fit", "svh", "lvh", "dvh"] }],
        "max-h": [{ "max-h": [Q, t, "min", "max", "fit", "svh", "lvh", "dvh"] }],
        size: [{ size: [Q, t, "auto", "min", "max", "fit"] }],
        "font-size": [{ text: ["base", Mn, Pn] }],
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
              qu,
            ],
          },
        ],
        "font-family": [{ font: [hi] }],
        "fvn-normal": ["normal-nums"],
        "fvn-ordinal": ["ordinal"],
        "fvn-slashed-zero": ["slashed-zero"],
        "fvn-figure": ["lining-nums", "oldstyle-nums"],
        "fvn-spacing": ["proportional-nums", "tabular-nums"],
        "fvn-fraction": ["diagonal-fractions", "stacked-fractions"],
        tracking: [{ tracking: ["tighter", "tight", "normal", "wide", "wider", "widest", Q] }],
        "line-clamp": [{ "line-clamp": ["none", ko, qu] }],
        leading: [{ leading: ["none", "tight", "snug", "normal", "relaxed", "loose", an, Q] }],
        "list-image": [{ "list-image": ["none", Q] }],
        "list-style-type": [{ list: ["none", "disc", "decimal", Q] }],
        "list-style-position": [{ list: ["inside", "outside"] }],
        "placeholder-color": [{ placeholder: [e] }],
        "placeholder-opacity": [{ "placeholder-opacity": [h] }],
        "text-alignment": [{ text: ["left", "center", "right", "justify", "start", "end"] }],
        "text-color": [{ text: [e] }],
        "text-opacity": [{ "text-opacity": [h] }],
        "text-decoration": ["underline", "overline", "line-through", "no-underline"],
        "text-decoration-style": [{ decoration: [...M(), "wavy"] }],
        "text-decoration-thickness": [{ decoration: ["auto", "from-font", an, Pn] }],
        "underline-offset": [{ "underline-offset": ["auto", an, Q] }],
        "text-decoration-color": [{ decoration: [e] }],
        "text-transform": ["uppercase", "lowercase", "capitalize", "normal-case"],
        "text-overflow": ["truncate", "text-ellipsis", "text-clip"],
        "text-wrap": [{ text: ["wrap", "nowrap", "balance", "pretty"] }],
        indent: [{ indent: F() }],
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
              Q,
            ],
          },
        ],
        whitespace: [
          { whitespace: ["normal", "nowrap", "pre", "pre-line", "pre-wrap", "break-spaces"] },
        ],
        break: [{ break: ["normal", "words", "all", "keep"] }],
        hyphens: [{ hyphens: ["none", "manual", "auto"] }],
        content: [{ content: ["none", Q] }],
        "bg-attachment": [{ bg: ["fixed", "local", "scroll"] }],
        "bg-clip": [{ "bg-clip": ["border", "padding", "content", "text"] }],
        "bg-opacity": [{ "bg-opacity": [h] }],
        "bg-origin": [{ "bg-origin": ["border", "padding", "content"] }],
        "bg-position": [{ bg: [...I(), dT] }],
        "bg-repeat": [{ bg: ["no-repeat", { repeat: ["", "x", "y", "round", "space"] }] }],
        "bg-size": [{ bg: ["auto", "cover", "contain", fT] }],
        "bg-image": [
          { bg: ["none", { "gradient-to": ["t", "tr", "r", "br", "b", "bl", "l", "tl"] }, pT] },
        ],
        "bg-color": [{ bg: [e] }],
        "gradient-from-pos": [{ from: [y] }],
        "gradient-via-pos": [{ via: [y] }],
        "gradient-to-pos": [{ to: [y] }],
        "gradient-from": [{ from: [p] }],
        "gradient-via": [{ via: [p] }],
        "gradient-to": [{ to: [p] }],
        rounded: [{ rounded: [i] }],
        "rounded-s": [{ "rounded-s": [i] }],
        "rounded-e": [{ "rounded-e": [i] }],
        "rounded-t": [{ "rounded-t": [i] }],
        "rounded-r": [{ "rounded-r": [i] }],
        "rounded-b": [{ "rounded-b": [i] }],
        "rounded-l": [{ "rounded-l": [i] }],
        "rounded-ss": [{ "rounded-ss": [i] }],
        "rounded-se": [{ "rounded-se": [i] }],
        "rounded-ee": [{ "rounded-ee": [i] }],
        "rounded-es": [{ "rounded-es": [i] }],
        "rounded-tl": [{ "rounded-tl": [i] }],
        "rounded-tr": [{ "rounded-tr": [i] }],
        "rounded-br": [{ "rounded-br": [i] }],
        "rounded-bl": [{ "rounded-bl": [i] }],
        "border-w": [{ border: [a] }],
        "border-w-x": [{ "border-x": [a] }],
        "border-w-y": [{ "border-y": [a] }],
        "border-w-s": [{ "border-s": [a] }],
        "border-w-e": [{ "border-e": [a] }],
        "border-w-t": [{ "border-t": [a] }],
        "border-w-r": [{ "border-r": [a] }],
        "border-w-b": [{ "border-b": [a] }],
        "border-w-l": [{ "border-l": [a] }],
        "border-opacity": [{ "border-opacity": [h] }],
        "border-style": [{ border: [...M(), "hidden"] }],
        "divide-x": [{ "divide-x": [a] }],
        "divide-x-reverse": ["divide-x-reverse"],
        "divide-y": [{ "divide-y": [a] }],
        "divide-y-reverse": ["divide-y-reverse"],
        "divide-opacity": [{ "divide-opacity": [h] }],
        "divide-style": [{ divide: M() }],
        "border-color": [{ border: [o] }],
        "border-color-x": [{ "border-x": [o] }],
        "border-color-y": [{ "border-y": [o] }],
        "border-color-s": [{ "border-s": [o] }],
        "border-color-e": [{ "border-e": [o] }],
        "border-color-t": [{ "border-t": [o] }],
        "border-color-r": [{ "border-r": [o] }],
        "border-color-b": [{ "border-b": [o] }],
        "border-color-l": [{ "border-l": [o] }],
        "divide-color": [{ divide: [o] }],
        "outline-style": [{ outline: ["", ...M()] }],
        "outline-offset": [{ "outline-offset": [an, Q] }],
        "outline-w": [{ outline: [an, Pn] }],
        "outline-color": [{ outline: [e] }],
        "ring-w": [{ ring: j() }],
        "ring-w-inset": ["ring-inset"],
        "ring-color": [{ ring: [e] }],
        "ring-opacity": [{ "ring-opacity": [h] }],
        "ring-offset-w": [{ "ring-offset": [an, Pn] }],
        "ring-offset-color": [{ "ring-offset": [e] }],
        shadow: [{ shadow: ["", "inner", "none", Mn, mT] }],
        "shadow-color": [{ shadow: [hi] }],
        opacity: [{ opacity: [h] }],
        "mix-blend": [{ "mix-blend": [...V(), "plus-lighter", "plus-darker"] }],
        "bg-blend": [{ "bg-blend": V() }],
        filter: [{ filter: ["", "none"] }],
        blur: [{ blur: [n] }],
        brightness: [{ brightness: [r] }],
        contrast: [{ contrast: [l] }],
        "drop-shadow": [{ "drop-shadow": ["", "none", Mn, Q] }],
        grayscale: [{ grayscale: [u] }],
        "hue-rotate": [{ "hue-rotate": [c] }],
        invert: [{ invert: [f] }],
        saturate: [{ saturate: [x] }],
        sepia: [{ sepia: [E] }],
        "backdrop-filter": [{ "backdrop-filter": ["", "none"] }],
        "backdrop-blur": [{ "backdrop-blur": [n] }],
        "backdrop-brightness": [{ "backdrop-brightness": [r] }],
        "backdrop-contrast": [{ "backdrop-contrast": [l] }],
        "backdrop-grayscale": [{ "backdrop-grayscale": [u] }],
        "backdrop-hue-rotate": [{ "backdrop-hue-rotate": [c] }],
        "backdrop-invert": [{ "backdrop-invert": [f] }],
        "backdrop-opacity": [{ "backdrop-opacity": [h] }],
        "backdrop-saturate": [{ "backdrop-saturate": [x] }],
        "backdrop-sepia": [{ "backdrop-sepia": [E] }],
        "border-collapse": [{ border: ["collapse", "separate"] }],
        "border-spacing": [{ "border-spacing": [s] }],
        "border-spacing-x": [{ "border-spacing-x": [s] }],
        "border-spacing-y": [{ "border-spacing-y": [s] }],
        "table-layout": [{ table: ["auto", "fixed"] }],
        caption: [{ caption: ["top", "bottom"] }],
        transition: [
          { transition: ["none", "all", "", "colors", "opacity", "shadow", "transform", Q] },
        ],
        duration: [{ duration: O() }],
        ease: [{ ease: ["linear", "in", "out", "in-out", Q] }],
        delay: [{ delay: O() }],
        animate: [{ animate: ["none", "spin", "ping", "pulse", "bounce", Q] }],
        transform: [{ transform: ["", "gpu", "none"] }],
        scale: [{ scale: [S] }],
        "scale-x": [{ "scale-x": [S] }],
        "scale-y": [{ "scale-y": [S] }],
        rotate: [{ rotate: [di, Q] }],
        "translate-x": [{ "translate-x": [_] }],
        "translate-y": [{ "translate-y": [_] }],
        "skew-x": [{ "skew-x": [C] }],
        "skew-y": [{ "skew-y": [C] }],
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
              Q,
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
              Q,
            ],
          },
        ],
        "caret-color": [{ caret: [e] }],
        "pointer-events": [{ "pointer-events": ["none", "auto"] }],
        resize: [{ resize: ["none", "y", "x", ""] }],
        "scroll-behavior": [{ scroll: ["auto", "smooth"] }],
        "scroll-m": [{ "scroll-m": F() }],
        "scroll-mx": [{ "scroll-mx": F() }],
        "scroll-my": [{ "scroll-my": F() }],
        "scroll-ms": [{ "scroll-ms": F() }],
        "scroll-me": [{ "scroll-me": F() }],
        "scroll-mt": [{ "scroll-mt": F() }],
        "scroll-mr": [{ "scroll-mr": F() }],
        "scroll-mb": [{ "scroll-mb": F() }],
        "scroll-ml": [{ "scroll-ml": F() }],
        "scroll-p": [{ "scroll-p": F() }],
        "scroll-px": [{ "scroll-px": F() }],
        "scroll-py": [{ "scroll-py": F() }],
        "scroll-ps": [{ "scroll-ps": F() }],
        "scroll-pe": [{ "scroll-pe": F() }],
        "scroll-pt": [{ "scroll-pt": F() }],
        "scroll-pr": [{ "scroll-pr": F() }],
        "scroll-pb": [{ "scroll-pb": F() }],
        "scroll-pl": [{ "scroll-pl": F() }],
        "snap-align": [{ snap: ["start", "end", "center", "align-none"] }],
        "snap-stop": [{ snap: ["normal", "always"] }],
        "snap-type": [{ snap: ["none", "x", "y", "both"] }],
        "snap-strictness": [{ snap: ["mandatory", "proximity"] }],
        touch: [{ touch: ["auto", "none", "manipulation"] }],
        "touch-x": [{ "touch-pan": ["x", "left", "right"] }],
        "touch-y": [{ "touch-pan": ["y", "up", "down"] }],
        "touch-pz": ["touch-pinch-zoom"],
        select: [{ select: ["none", "text", "all", "auto"] }],
        "will-change": [{ "will-change": ["auto", "scroll", "contents", "transform", Q] }],
        fill: [{ fill: [e, "none"] }],
        "stroke-w": [{ stroke: [an, Pn, qu] }],
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
  wT = tT(xT);
function le(...e) {
  return wT(wx(e));
}
const ST = Sx(
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
  ih = v.forwardRef(({ className: e, variant: t, size: n, asChild: r = !1, ...o }, i) => {
    const s = r ? O_ : "button";
    return N.jsx(s, { className: le(ST({ variant: t, size: n, className: e })), ref: i, ...o });
  });
ih.displayName = "Button";
const Ms = v.forwardRef(({ className: e, ...t }, n) =>
  N.jsx("div", {
    ref: n,
    className: le("rounded-lg border bg-card text-card-foreground shadow-sm", e),
    ...t,
  }),
);
Ms.displayName = "Card";
const As = v.forwardRef(({ className: e, ...t }, n) =>
  N.jsx("div", { ref: n, className: le("flex flex-col space-y-1.5 p-6", e), ...t }),
);
As.displayName = "CardHeader";
const Rs = v.forwardRef(({ className: e, ...t }, n) =>
  N.jsx("div", {
    ref: n,
    className: le("text-2xl font-semibold leading-none tracking-tight", e),
    ...t,
  }),
);
Rs.displayName = "CardTitle";
const ET = v.forwardRef(({ className: e, ...t }, n) =>
  N.jsx("div", { ref: n, className: le("text-sm text-muted-foreground", e), ...t }),
);
ET.displayName = "CardDescription";
const Ds = v.forwardRef(({ className: e, ...t }, n) =>
  N.jsx("div", { ref: n, className: le("p-6 pt-0", e), ...t }),
);
Ds.displayName = "CardContent";
const CT = v.forwardRef(({ className: e, ...t }, n) =>
  N.jsx("div", { ref: n, className: le("flex items-center p-6 pt-0", e), ...t }),
);
CT.displayName = "CardFooter";
function Fe(e, t, { checkForDefaultPrevented: n = !0 } = {}) {
  return function (o) {
    if ((e == null || e(o), n === !1 || !o.defaultPrevented)) return t == null ? void 0 : t(o);
  };
}
function bT(e, t) {
  const n = v.createContext(t),
    r = (i) => {
      const { children: s, ...a } = i,
        l = v.useMemo(() => a, Object.values(a));
      return N.jsx(n.Provider, { value: l, children: s });
    };
  r.displayName = e + "Provider";
  function o(i) {
    const s = v.useContext(n);
    if (s) return s;
    if (t !== void 0) return t;
    throw new Error(`\`${i}\` must be used within \`${e}\``);
  }
  return [r, o];
}
function ru(e, t = []) {
  let n = [];
  function r(i, s) {
    const a = v.createContext(s),
      l = n.length;
    n = [...n, s];
    const u = (f) => {
      var h;
      const { scope: d, children: p, ...y } = f,
        m = ((h = d == null ? void 0 : d[e]) == null ? void 0 : h[l]) || a,
        w = v.useMemo(() => y, Object.values(y));
      return N.jsx(m.Provider, { value: w, children: p });
    };
    u.displayName = i + "Provider";
    function c(f, d) {
      var m;
      const p = ((m = d == null ? void 0 : d[e]) == null ? void 0 : m[l]) || a,
        y = v.useContext(p);
      if (y) return y;
      if (s !== void 0) return s;
      throw new Error(`\`${f}\` must be used within \`${i}\``);
    }
    return [u, c];
  }
  const o = () => {
    const i = n.map((s) => v.createContext(s));
    return function (a) {
      const l = (a == null ? void 0 : a[e]) || i;
      return v.useMemo(() => ({ [`__scope${e}`]: { ...a, [e]: l } }), [a, l]);
    };
  };
  return (o.scopeName = e), [r, kT(o, ...t)];
}
function kT(...e) {
  const t = e[0];
  if (e.length === 1) return t;
  const n = () => {
    const r = e.map((o) => ({ useScope: o(), scopeName: o.scopeName }));
    return function (i) {
      const s = r.reduce((a, { useScope: l, scopeName: u }) => {
        const f = l(i)[`__scope${u}`];
        return { ...a, ...f };
      }, {});
      return v.useMemo(() => ({ [`__scope${t.scopeName}`]: s }), [s]);
    };
  };
  return (n.scopeName = t.scopeName), n;
}
function _T(e) {
  const t = e + "CollectionProvider",
    [n, r] = ru(t),
    [o, i] = n(t, { collectionRef: { current: null }, itemMap: new Map() }),
    s = (m) => {
      const { scope: w, children: h } = m,
        g = L.useRef(null),
        x = L.useRef(new Map()).current;
      return N.jsx(o, { scope: w, itemMap: x, collectionRef: g, children: h });
    };
  s.displayName = t;
  const a = e + "CollectionSlot",
    l = us(a),
    u = L.forwardRef((m, w) => {
      const { scope: h, children: g } = m,
        x = i(a, h),
        S = tn(w, x.collectionRef);
      return N.jsx(l, { ref: S, children: g });
    });
  u.displayName = a;
  const c = e + "CollectionItemSlot",
    f = "data-radix-collection-item",
    d = us(c),
    p = L.forwardRef((m, w) => {
      const { scope: h, children: g, ...x } = m,
        S = L.useRef(null),
        E = tn(w, S),
        C = i(c, h);
      return (
        L.useEffect(() => (C.itemMap.set(S, { ref: S, ...x }), () => void C.itemMap.delete(S))),
        N.jsx(d, { [f]: "", ref: E, children: g })
      );
    });
  p.displayName = c;
  function y(m) {
    const w = i(e + "CollectionConsumer", m);
    return L.useCallback(() => {
      const g = w.collectionRef.current;
      if (!g) return [];
      const x = Array.from(g.querySelectorAll(`[${f}]`));
      return Array.from(w.itemMap.values()).sort(
        (C, b) => x.indexOf(C.ref.current) - x.indexOf(b.ref.current),
      );
    }, [w.collectionRef, w.itemMap]);
  }
  return [{ Provider: s, Slot: u, ItemSlot: p }, y, r];
}
var cs = globalThis != null && globalThis.document ? v.useLayoutEffect : () => {},
  TT = a0[" useId ".trim().toString()] || (() => {}),
  NT = 0;
function zi(e) {
  const [t, n] = v.useState(TT());
  return (
    cs(() => {
      n((r) => r ?? String(NT++));
    }, [e]),
    t ? `radix-${t}` : ""
  );
}
var PT = [
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
  et = PT.reduce((e, t) => {
    const n = us(`Primitive.${t}`),
      r = v.forwardRef((o, i) => {
        const { asChild: s, ...a } = o,
          l = s ? n : t;
        return (
          typeof window < "u" && (window[Symbol.for("radix-ui")] = !0), N.jsx(l, { ...a, ref: i })
        );
      });
    return (r.displayName = `Primitive.${t}`), { ...e, [t]: r };
  }, {});
function MT(e, t) {
  e && rh.flushSync(() => e.dispatchEvent(t));
}
function zo(e) {
  const t = v.useRef(e);
  return (
    v.useEffect(() => {
      t.current = e;
    }),
    v.useMemo(
      () =>
        (...n) => {
          var r;
          return (r = t.current) == null ? void 0 : r.call(t, ...n);
        },
      [],
    )
  );
}
var AT = a0[" useInsertionEffect ".trim().toString()] || cs;
function sh({ prop: e, defaultProp: t, onChange: n = () => {}, caller: r }) {
  const [o, i, s] = RT({ defaultProp: t, onChange: n }),
    a = e !== void 0,
    l = a ? e : o;
  {
    const c = v.useRef(e !== void 0);
    v.useEffect(() => {
      const f = c.current;
      f !== a &&
        console.warn(
          `${r} is changing from ${f ? "controlled" : "uncontrolled"} to ${a ? "controlled" : "uncontrolled"}. Components should not switch from controlled to uncontrolled (or vice versa). Decide between using a controlled or uncontrolled value for the lifetime of the component.`,
        ),
        (c.current = a);
    }, [a, r]);
  }
  const u = v.useCallback(
    (c) => {
      var f;
      if (a) {
        const d = DT(c) ? c(e) : c;
        d !== e && ((f = s.current) == null || f.call(s, d));
      } else i(c);
    },
    [a, e, i, s],
  );
  return [l, u];
}
function RT({ defaultProp: e, onChange: t }) {
  const [n, r] = v.useState(e),
    o = v.useRef(n),
    i = v.useRef(t);
  return (
    AT(() => {
      i.current = t;
    }, [t]),
    v.useEffect(() => {
      var s;
      o.current !== n && ((s = i.current) == null || s.call(i, n), (o.current = n));
    }, [n, o]),
    [n, r, i]
  );
}
function DT(e) {
  return typeof e == "function";
}
var IT = v.createContext(void 0);
function Tx(e) {
  const t = v.useContext(IT);
  return e || t || "ltr";
}
var Ju = "rovingFocusGroup.onEntryFocus",
  LT = { bubbles: !1, cancelable: !0 },
  Is = "RovingFocusGroup",
  [kf, Nx, VT] = _T(Is),
  [OT, Px] = ru(Is, [VT]),
  [FT, zT] = OT(Is),
  Mx = v.forwardRef((e, t) =>
    N.jsx(kf.Provider, {
      scope: e.__scopeRovingFocusGroup,
      children: N.jsx(kf.Slot, {
        scope: e.__scopeRovingFocusGroup,
        children: N.jsx($T, { ...e, ref: t }),
      }),
    }),
  );
Mx.displayName = Is;
var $T = v.forwardRef((e, t) => {
    const {
        __scopeRovingFocusGroup: n,
        orientation: r,
        loop: o = !1,
        dir: i,
        currentTabStopId: s,
        defaultCurrentTabStopId: a,
        onCurrentTabStopIdChange: l,
        onEntryFocus: u,
        preventScrollOnEntryFocus: c = !1,
        ...f
      } = e,
      d = v.useRef(null),
      p = tn(t, d),
      y = Tx(i),
      [m, w] = sh({ prop: s, defaultProp: a ?? null, onChange: l, caller: Is }),
      [h, g] = v.useState(!1),
      x = zo(u),
      S = Nx(n),
      E = v.useRef(!1),
      [C, b] = v.useState(0);
    return (
      v.useEffect(() => {
        const _ = d.current;
        if (_) return _.addEventListener(Ju, x), () => _.removeEventListener(Ju, x);
      }, [x]),
      N.jsx(FT, {
        scope: n,
        orientation: r,
        dir: y,
        loop: o,
        currentTabStopId: m,
        onItemFocus: v.useCallback((_) => w(_), [w]),
        onItemShiftTab: v.useCallback(() => g(!0), []),
        onFocusableItemAdd: v.useCallback(() => b((_) => _ + 1), []),
        onFocusableItemRemove: v.useCallback(() => b((_) => _ - 1), []),
        children: N.jsx(et.div, {
          tabIndex: h || C === 0 ? -1 : 0,
          "data-orientation": r,
          ...f,
          ref: p,
          style: { outline: "none", ...e.style },
          onMouseDown: Fe(e.onMouseDown, () => {
            E.current = !0;
          }),
          onFocus: Fe(e.onFocus, (_) => {
            const A = !E.current;
            if (_.target === _.currentTarget && A && !h) {
              const R = new CustomEvent(Ju, LT);
              if ((_.currentTarget.dispatchEvent(R), !R.defaultPrevented)) {
                const z = S().filter((M) => M.focusable),
                  F = z.find((M) => M.active),
                  j = z.find((M) => M.id === m),
                  I = [F, j, ...z].filter(Boolean).map((M) => M.ref.current);
                Dx(I, c);
              }
            }
            E.current = !1;
          }),
          onBlur: Fe(e.onBlur, () => g(!1)),
        }),
      })
    );
  }),
  Ax = "RovingFocusGroupItem",
  Rx = v.forwardRef((e, t) => {
    const {
        __scopeRovingFocusGroup: n,
        focusable: r = !0,
        active: o = !1,
        tabStopId: i,
        children: s,
        ...a
      } = e,
      l = zi(),
      u = i || l,
      c = zT(Ax, n),
      f = c.currentTabStopId === u,
      d = Nx(n),
      { onFocusableItemAdd: p, onFocusableItemRemove: y, currentTabStopId: m } = c;
    return (
      v.useEffect(() => {
        if (r) return p(), () => y();
      }, [r, p, y]),
      N.jsx(kf.ItemSlot, {
        scope: n,
        id: u,
        focusable: r,
        active: o,
        children: N.jsx(et.span, {
          tabIndex: f ? 0 : -1,
          "data-orientation": c.orientation,
          ...a,
          ref: t,
          onMouseDown: Fe(e.onMouseDown, (w) => {
            r ? c.onItemFocus(u) : w.preventDefault();
          }),
          onFocus: Fe(e.onFocus, () => c.onItemFocus(u)),
          onKeyDown: Fe(e.onKeyDown, (w) => {
            if (w.key === "Tab" && w.shiftKey) {
              c.onItemShiftTab();
              return;
            }
            if (w.target !== w.currentTarget) return;
            const h = UT(w, c.orientation, c.dir);
            if (h !== void 0) {
              if (w.metaKey || w.ctrlKey || w.altKey || w.shiftKey) return;
              w.preventDefault();
              let x = d()
                .filter((S) => S.focusable)
                .map((S) => S.ref.current);
              if (h === "last") x.reverse();
              else if (h === "prev" || h === "next") {
                h === "prev" && x.reverse();
                const S = x.indexOf(w.currentTarget);
                x = c.loop ? HT(x, S + 1) : x.slice(S + 1);
              }
              setTimeout(() => Dx(x));
            }
          }),
          children: typeof s == "function" ? s({ isCurrentTabStop: f, hasTabStop: m != null }) : s,
        }),
      })
    );
  });
Rx.displayName = Ax;
var jT = {
  ArrowLeft: "prev",
  ArrowUp: "prev",
  ArrowRight: "next",
  ArrowDown: "next",
  PageUp: "first",
  Home: "first",
  PageDown: "last",
  End: "last",
};
function BT(e, t) {
  return t !== "rtl" ? e : e === "ArrowLeft" ? "ArrowRight" : e === "ArrowRight" ? "ArrowLeft" : e;
}
function UT(e, t, n) {
  const r = BT(e.key, n);
  if (
    !(t === "vertical" && ["ArrowLeft", "ArrowRight"].includes(r)) &&
    !(t === "horizontal" && ["ArrowUp", "ArrowDown"].includes(r))
  )
    return jT[r];
}
function Dx(e, t = !1) {
  const n = document.activeElement;
  for (const r of e)
    if (r === n || (r.focus({ preventScroll: t }), document.activeElement !== n)) return;
}
function HT(e, t) {
  return e.map((n, r) => e[(t + r) % e.length]);
}
var WT = Mx,
  GT = Rx;
function KT(e, t) {
  return v.useReducer((n, r) => t[n][r] ?? n, e);
}
var Ls = (e) => {
  const { present: t, children: n } = e,
    r = YT(t),
    o = typeof n == "function" ? n({ present: r.isPresent }) : v.Children.only(n),
    i = tn(r.ref, XT(o));
  return typeof n == "function" || r.isPresent ? v.cloneElement(o, { ref: i }) : null;
};
Ls.displayName = "Presence";
function YT(e) {
  const [t, n] = v.useState(),
    r = v.useRef(null),
    o = v.useRef(e),
    i = v.useRef("none"),
    s = e ? "mounted" : "unmounted",
    [a, l] = KT(s, {
      mounted: { UNMOUNT: "unmounted", ANIMATION_OUT: "unmountSuspended" },
      unmountSuspended: { MOUNT: "mounted", ANIMATION_END: "unmounted" },
      unmounted: { MOUNT: "mounted" },
    });
  return (
    v.useEffect(() => {
      const u = ia(r.current);
      i.current = a === "mounted" ? u : "none";
    }, [a]),
    cs(() => {
      const u = r.current,
        c = o.current;
      if (c !== e) {
        const d = i.current,
          p = ia(u);
        e
          ? l("MOUNT")
          : p === "none" || (u == null ? void 0 : u.display) === "none"
            ? l("UNMOUNT")
            : l(c && d !== p ? "ANIMATION_OUT" : "UNMOUNT"),
          (o.current = e);
      }
    }, [e, l]),
    cs(() => {
      if (t) {
        let u;
        const c = t.ownerDocument.defaultView ?? window,
          f = (p) => {
            const m = ia(r.current).includes(CSS.escape(p.animationName));
            if (p.target === t && m && (l("ANIMATION_END"), !o.current)) {
              const w = t.style.animationFillMode;
              (t.style.animationFillMode = "forwards"),
                (u = c.setTimeout(() => {
                  t.style.animationFillMode === "forwards" && (t.style.animationFillMode = w);
                }));
            }
          },
          d = (p) => {
            p.target === t && (i.current = ia(r.current));
          };
        return (
          t.addEventListener("animationstart", d),
          t.addEventListener("animationcancel", f),
          t.addEventListener("animationend", f),
          () => {
            c.clearTimeout(u),
              t.removeEventListener("animationstart", d),
              t.removeEventListener("animationcancel", f),
              t.removeEventListener("animationend", f);
          }
        );
      } else l("ANIMATION_END");
    }, [t, l]),
    {
      isPresent: ["mounted", "unmountSuspended"].includes(a),
      ref: v.useCallback((u) => {
        (r.current = u ? getComputedStyle(u) : null), n(u);
      }, []),
    }
  );
}
function ia(e) {
  return (e == null ? void 0 : e.animationName) || "none";
}
function XT(e) {
  var r, o;
  let t = (r = Object.getOwnPropertyDescriptor(e.props, "ref")) == null ? void 0 : r.get,
    n = t && "isReactWarning" in t && t.isReactWarning;
  return n
    ? e.ref
    : ((t = (o = Object.getOwnPropertyDescriptor(e, "ref")) == null ? void 0 : o.get),
      (n = t && "isReactWarning" in t && t.isReactWarning),
      n ? e.props.ref : e.props.ref || e.ref);
}
var ou = "Tabs",
  [ZT, yO] = ru(ou, [Px]),
  Ix = Px(),
  [QT, ah] = ZT(ou),
  Lx = v.forwardRef((e, t) => {
    const {
        __scopeTabs: n,
        value: r,
        onValueChange: o,
        defaultValue: i,
        orientation: s = "horizontal",
        dir: a,
        activationMode: l = "automatic",
        ...u
      } = e,
      c = Tx(a),
      [f, d] = sh({ prop: r, onChange: o, defaultProp: i ?? "", caller: ou });
    return N.jsx(QT, {
      scope: n,
      baseId: zi(),
      value: f,
      onValueChange: d,
      orientation: s,
      dir: c,
      activationMode: l,
      children: N.jsx(et.div, { dir: c, "data-orientation": s, ...u, ref: t }),
    });
  });
Lx.displayName = ou;
var Vx = "TabsList",
  Ox = v.forwardRef((e, t) => {
    const { __scopeTabs: n, loop: r = !0, ...o } = e,
      i = ah(Vx, n),
      s = Ix(n);
    return N.jsx(WT, {
      asChild: !0,
      ...s,
      orientation: i.orientation,
      dir: i.dir,
      loop: r,
      children: N.jsx(et.div, { role: "tablist", "aria-orientation": i.orientation, ...o, ref: t }),
    });
  });
Ox.displayName = Vx;
var Fx = "TabsTrigger",
  zx = v.forwardRef((e, t) => {
    const { __scopeTabs: n, value: r, disabled: o = !1, ...i } = e,
      s = ah(Fx, n),
      a = Ix(n),
      l = Bx(s.baseId, r),
      u = Ux(s.baseId, r),
      c = r === s.value;
    return N.jsx(GT, {
      asChild: !0,
      ...a,
      focusable: !o,
      active: c,
      children: N.jsx(et.button, {
        type: "button",
        role: "tab",
        "aria-selected": c,
        "aria-controls": u,
        "data-state": c ? "active" : "inactive",
        "data-disabled": o ? "" : void 0,
        disabled: o,
        id: l,
        ...i,
        ref: t,
        onMouseDown: Fe(e.onMouseDown, (f) => {
          !o && f.button === 0 && f.ctrlKey === !1 ? s.onValueChange(r) : f.preventDefault();
        }),
        onKeyDown: Fe(e.onKeyDown, (f) => {
          [" ", "Enter"].includes(f.key) && s.onValueChange(r);
        }),
        onFocus: Fe(e.onFocus, () => {
          const f = s.activationMode !== "manual";
          !c && !o && f && s.onValueChange(r);
        }),
      }),
    });
  });
zx.displayName = Fx;
var $x = "TabsContent",
  jx = v.forwardRef((e, t) => {
    const { __scopeTabs: n, value: r, forceMount: o, children: i, ...s } = e,
      a = ah($x, n),
      l = Bx(a.baseId, r),
      u = Ux(a.baseId, r),
      c = r === a.value,
      f = v.useRef(c);
    return (
      v.useEffect(() => {
        const d = requestAnimationFrame(() => (f.current = !1));
        return () => cancelAnimationFrame(d);
      }, []),
      N.jsx(Ls, {
        present: o || c,
        children: ({ present: d }) =>
          N.jsx(et.div, {
            "data-state": c ? "active" : "inactive",
            "data-orientation": a.orientation,
            role: "tabpanel",
            "aria-labelledby": l,
            hidden: !d,
            id: u,
            tabIndex: 0,
            ...s,
            ref: t,
            style: { ...e.style, animationDuration: f.current ? "0s" : void 0 },
            children: d && i,
          }),
      })
    );
  });
jx.displayName = $x;
function Bx(e, t) {
  return `${e}-trigger-${t}`;
}
function Ux(e, t) {
  return `${e}-content-${t}`;
}
var qT = Lx,
  Hx = Ox,
  Wx = zx,
  Gx = jx;
const JT = qT,
  Kx = v.forwardRef(({ className: e, ...t }, n) =>
    N.jsx(Hx, {
      ref: n,
      className: le(
        "inline-flex h-10 items-center justify-center rounded-md bg-muted p-1 text-muted-foreground",
        e,
      ),
      ...t,
    }),
  );
Kx.displayName = Hx.displayName;
const Oa = v.forwardRef(({ className: e, ...t }, n) =>
  N.jsx(Wx, {
    ref: n,
    className: le(
      "inline-flex items-center justify-center whitespace-nowrap rounded-sm px-3 py-1.5 text-sm font-medium ring-offset-background transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 data-[state=active]:bg-background data-[state=active]:text-foreground data-[state=active]:shadow-sm",
      e,
    ),
    ...t,
  }),
);
Oa.displayName = Wx.displayName;
const Fa = v.forwardRef(({ className: e, ...t }, n) =>
  N.jsx(Gx, {
    ref: n,
    className: le(
      "mt-2 ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
      e,
    ),
    ...t,
  }),
);
Fa.displayName = Gx.displayName;
function e2(e, t = globalThis == null ? void 0 : globalThis.document) {
  const n = zo(e);
  v.useEffect(() => {
    const r = (o) => {
      o.key === "Escape" && n(o);
    };
    return (
      t.addEventListener("keydown", r, { capture: !0 }),
      () => t.removeEventListener("keydown", r, { capture: !0 })
    );
  }, [n, t]);
}
var t2 = "DismissableLayer",
  _f = "dismissableLayer.update",
  n2 = "dismissableLayer.pointerDownOutside",
  r2 = "dismissableLayer.focusOutside",
  Pm,
  Yx = v.createContext({
    layers: new Set(),
    layersWithOutsidePointerEventsDisabled: new Set(),
    branches: new Set(),
  }),
  Xx = v.forwardRef((e, t) => {
    const {
        disableOutsidePointerEvents: n = !1,
        onEscapeKeyDown: r,
        onPointerDownOutside: o,
        onFocusOutside: i,
        onInteractOutside: s,
        onDismiss: a,
        ...l
      } = e,
      u = v.useContext(Yx),
      [c, f] = v.useState(null),
      d =
        (c == null ? void 0 : c.ownerDocument) ??
        (globalThis == null ? void 0 : globalThis.document),
      [, p] = v.useState({}),
      y = tn(t, (b) => f(b)),
      m = Array.from(u.layers),
      [w] = [...u.layersWithOutsidePointerEventsDisabled].slice(-1),
      h = m.indexOf(w),
      g = c ? m.indexOf(c) : -1,
      x = u.layersWithOutsidePointerEventsDisabled.size > 0,
      S = g >= h,
      E = s2((b) => {
        const _ = b.target,
          A = [...u.branches].some((R) => R.contains(_));
        !S || A || (o == null || o(b), s == null || s(b), b.defaultPrevented || a == null || a());
      }, d),
      C = a2((b) => {
        const _ = b.target;
        [...u.branches].some((R) => R.contains(_)) ||
          (i == null || i(b), s == null || s(b), b.defaultPrevented || a == null || a());
      }, d);
    return (
      e2((b) => {
        g === u.layers.size - 1 &&
          (r == null || r(b), !b.defaultPrevented && a && (b.preventDefault(), a()));
      }, d),
      v.useEffect(() => {
        if (c)
          return (
            n &&
              (u.layersWithOutsidePointerEventsDisabled.size === 0 &&
                ((Pm = d.body.style.pointerEvents), (d.body.style.pointerEvents = "none")),
              u.layersWithOutsidePointerEventsDisabled.add(c)),
            u.layers.add(c),
            Mm(),
            () => {
              n &&
                u.layersWithOutsidePointerEventsDisabled.size === 1 &&
                (d.body.style.pointerEvents = Pm);
            }
          );
      }, [c, d, n, u]),
      v.useEffect(
        () => () => {
          c && (u.layers.delete(c), u.layersWithOutsidePointerEventsDisabled.delete(c), Mm());
        },
        [c, u],
      ),
      v.useEffect(() => {
        const b = () => p({});
        return document.addEventListener(_f, b), () => document.removeEventListener(_f, b);
      }, []),
      N.jsx(et.div, {
        ...l,
        ref: y,
        style: { pointerEvents: x ? (S ? "auto" : "none") : void 0, ...e.style },
        onFocusCapture: Fe(e.onFocusCapture, C.onFocusCapture),
        onBlurCapture: Fe(e.onBlurCapture, C.onBlurCapture),
        onPointerDownCapture: Fe(e.onPointerDownCapture, E.onPointerDownCapture),
      })
    );
  });
Xx.displayName = t2;
var o2 = "DismissableLayerBranch",
  i2 = v.forwardRef((e, t) => {
    const n = v.useContext(Yx),
      r = v.useRef(null),
      o = tn(t, r);
    return (
      v.useEffect(() => {
        const i = r.current;
        if (i)
          return (
            n.branches.add(i),
            () => {
              n.branches.delete(i);
            }
          );
      }, [n.branches]),
      N.jsx(et.div, { ...e, ref: o })
    );
  });
i2.displayName = o2;
function s2(e, t = globalThis == null ? void 0 : globalThis.document) {
  const n = zo(e),
    r = v.useRef(!1),
    o = v.useRef(() => {});
  return (
    v.useEffect(() => {
      const i = (a) => {
          if (a.target && !r.current) {
            let l = function () {
              Zx(n2, n, u, { discrete: !0 });
            };
            const u = { originalEvent: a };
            a.pointerType === "touch"
              ? (t.removeEventListener("click", o.current),
                (o.current = l),
                t.addEventListener("click", o.current, { once: !0 }))
              : l();
          } else t.removeEventListener("click", o.current);
          r.current = !1;
        },
        s = window.setTimeout(() => {
          t.addEventListener("pointerdown", i);
        }, 0);
      return () => {
        window.clearTimeout(s),
          t.removeEventListener("pointerdown", i),
          t.removeEventListener("click", o.current);
      };
    }, [t, n]),
    { onPointerDownCapture: () => (r.current = !0) }
  );
}
function a2(e, t = globalThis == null ? void 0 : globalThis.document) {
  const n = zo(e),
    r = v.useRef(!1);
  return (
    v.useEffect(() => {
      const o = (i) => {
        i.target && !r.current && Zx(r2, n, { originalEvent: i }, { discrete: !1 });
      };
      return t.addEventListener("focusin", o), () => t.removeEventListener("focusin", o);
    }, [t, n]),
    { onFocusCapture: () => (r.current = !0), onBlurCapture: () => (r.current = !1) }
  );
}
function Mm() {
  const e = new CustomEvent(_f);
  document.dispatchEvent(e);
}
function Zx(e, t, n, { discrete: r }) {
  const o = n.originalEvent.target,
    i = new CustomEvent(e, { bubbles: !1, cancelable: !0, detail: n });
  t && o.addEventListener(e, t, { once: !0 }), r ? MT(o, i) : o.dispatchEvent(i);
}
var ec = "focusScope.autoFocusOnMount",
  tc = "focusScope.autoFocusOnUnmount",
  Am = { bubbles: !1, cancelable: !0 },
  l2 = "FocusScope",
  Qx = v.forwardRef((e, t) => {
    const { loop: n = !1, trapped: r = !1, onMountAutoFocus: o, onUnmountAutoFocus: i, ...s } = e,
      [a, l] = v.useState(null),
      u = zo(o),
      c = zo(i),
      f = v.useRef(null),
      d = tn(t, (m) => l(m)),
      p = v.useRef({
        paused: !1,
        pause() {
          this.paused = !0;
        },
        resume() {
          this.paused = !1;
        },
      }).current;
    v.useEffect(() => {
      if (r) {
        let m = function (x) {
            if (p.paused || !a) return;
            const S = x.target;
            a.contains(S) ? (f.current = S) : Rn(f.current, { select: !0 });
          },
          w = function (x) {
            if (p.paused || !a) return;
            const S = x.relatedTarget;
            S !== null && (a.contains(S) || Rn(f.current, { select: !0 }));
          },
          h = function (x) {
            if (document.activeElement === document.body)
              for (const E of x) E.removedNodes.length > 0 && Rn(a);
          };
        document.addEventListener("focusin", m), document.addEventListener("focusout", w);
        const g = new MutationObserver(h);
        return (
          a && g.observe(a, { childList: !0, subtree: !0 }),
          () => {
            document.removeEventListener("focusin", m),
              document.removeEventListener("focusout", w),
              g.disconnect();
          }
        );
      }
    }, [r, a, p.paused]),
      v.useEffect(() => {
        if (a) {
          Dm.add(p);
          const m = document.activeElement;
          if (!a.contains(m)) {
            const h = new CustomEvent(ec, Am);
            a.addEventListener(ec, u),
              a.dispatchEvent(h),
              h.defaultPrevented ||
                (u2(p2(qx(a)), { select: !0 }), document.activeElement === m && Rn(a));
          }
          return () => {
            a.removeEventListener(ec, u),
              setTimeout(() => {
                const h = new CustomEvent(tc, Am);
                a.addEventListener(tc, c),
                  a.dispatchEvent(h),
                  h.defaultPrevented || Rn(m ?? document.body, { select: !0 }),
                  a.removeEventListener(tc, c),
                  Dm.remove(p);
              }, 0);
          };
        }
      }, [a, u, c, p]);
    const y = v.useCallback(
      (m) => {
        if ((!n && !r) || p.paused) return;
        const w = m.key === "Tab" && !m.altKey && !m.ctrlKey && !m.metaKey,
          h = document.activeElement;
        if (w && h) {
          const g = m.currentTarget,
            [x, S] = c2(g);
          x && S
            ? !m.shiftKey && h === S
              ? (m.preventDefault(), n && Rn(x, { select: !0 }))
              : m.shiftKey && h === x && (m.preventDefault(), n && Rn(S, { select: !0 }))
            : h === g && m.preventDefault();
        }
      },
      [n, r, p.paused],
    );
    return N.jsx(et.div, { tabIndex: -1, ...s, ref: d, onKeyDown: y });
  });
Qx.displayName = l2;
function u2(e, { select: t = !1 } = {}) {
  const n = document.activeElement;
  for (const r of e) if ((Rn(r, { select: t }), document.activeElement !== n)) return;
}
function c2(e) {
  const t = qx(e),
    n = Rm(t, e),
    r = Rm(t.reverse(), e);
  return [n, r];
}
function qx(e) {
  const t = [],
    n = document.createTreeWalker(e, NodeFilter.SHOW_ELEMENT, {
      acceptNode: (r) => {
        const o = r.tagName === "INPUT" && r.type === "hidden";
        return r.disabled || r.hidden || o
          ? NodeFilter.FILTER_SKIP
          : r.tabIndex >= 0
            ? NodeFilter.FILTER_ACCEPT
            : NodeFilter.FILTER_SKIP;
      },
    });
  for (; n.nextNode(); ) t.push(n.currentNode);
  return t;
}
function Rm(e, t) {
  for (const n of e) if (!f2(n, { upTo: t })) return n;
}
function f2(e, { upTo: t }) {
  if (getComputedStyle(e).visibility === "hidden") return !0;
  for (; e; ) {
    if (t !== void 0 && e === t) return !1;
    if (getComputedStyle(e).display === "none") return !0;
    e = e.parentElement;
  }
  return !1;
}
function d2(e) {
  return e instanceof HTMLInputElement && "select" in e;
}
function Rn(e, { select: t = !1 } = {}) {
  if (e && e.focus) {
    const n = document.activeElement;
    e.focus({ preventScroll: !0 }), e !== n && d2(e) && t && e.select();
  }
}
var Dm = h2();
function h2() {
  let e = [];
  return {
    add(t) {
      const n = e[0];
      t !== n && (n == null || n.pause()), (e = Im(e, t)), e.unshift(t);
    },
    remove(t) {
      var n;
      (e = Im(e, t)), (n = e[0]) == null || n.resume();
    },
  };
}
function Im(e, t) {
  const n = [...e],
    r = n.indexOf(t);
  return r !== -1 && n.splice(r, 1), n;
}
function p2(e) {
  return e.filter((t) => t.tagName !== "A");
}
var m2 = "Portal",
  Jx = v.forwardRef((e, t) => {
    var a;
    const { container: n, ...r } = e,
      [o, i] = v.useState(!1);
    cs(() => i(!0), []);
    const s =
      n ||
      (o && ((a = globalThis == null ? void 0 : globalThis.document) == null ? void 0 : a.body));
    return s ? Kk.createPortal(N.jsx(et.div, { ...r, ref: t }), s) : null;
  });
Jx.displayName = m2;
var nc = 0;
function g2() {
  v.useEffect(() => {
    const e = document.querySelectorAll("[data-radix-focus-guard]");
    return (
      document.body.insertAdjacentElement("afterbegin", e[0] ?? Lm()),
      document.body.insertAdjacentElement("beforeend", e[1] ?? Lm()),
      nc++,
      () => {
        nc === 1 &&
          document.querySelectorAll("[data-radix-focus-guard]").forEach((t) => t.remove()),
          nc--;
      }
    );
  }, []);
}
function Lm() {
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
var Yt = function () {
  return (
    (Yt =
      Object.assign ||
      function (t) {
        for (var n, r = 1, o = arguments.length; r < o; r++) {
          n = arguments[r];
          for (var i in n) Object.prototype.hasOwnProperty.call(n, i) && (t[i] = n[i]);
        }
        return t;
      }),
    Yt.apply(this, arguments)
  );
};
function ew(e, t) {
  var n = {};
  for (var r in e) Object.prototype.hasOwnProperty.call(e, r) && t.indexOf(r) < 0 && (n[r] = e[r]);
  if (e != null && typeof Object.getOwnPropertySymbols == "function")
    for (var o = 0, r = Object.getOwnPropertySymbols(e); o < r.length; o++)
      t.indexOf(r[o]) < 0 &&
        Object.prototype.propertyIsEnumerable.call(e, r[o]) &&
        (n[r[o]] = e[r[o]]);
  return n;
}
function y2(e, t, n) {
  if (n || arguments.length === 2)
    for (var r = 0, o = t.length, i; r < o; r++)
      (i || !(r in t)) && (i || (i = Array.prototype.slice.call(t, 0, r)), (i[r] = t[r]));
  return e.concat(i || Array.prototype.slice.call(t));
}
var za = "right-scroll-bar-position",
  $a = "width-before-scroll-bar",
  v2 = "with-scroll-bars-hidden",
  x2 = "--removed-body-scroll-bar-size";
function rc(e, t) {
  return typeof e == "function" ? e(t) : e && (e.current = t), e;
}
function w2(e, t) {
  var n = v.useState(function () {
    return {
      value: e,
      callback: t,
      facade: {
        get current() {
          return n.value;
        },
        set current(r) {
          var o = n.value;
          o !== r && ((n.value = r), n.callback(r, o));
        },
      },
    };
  })[0];
  return (n.callback = t), n.facade;
}
var S2 = typeof window < "u" ? v.useLayoutEffect : v.useEffect,
  Vm = new WeakMap();
function E2(e, t) {
  var n = w2(null, function (r) {
    return e.forEach(function (o) {
      return rc(o, r);
    });
  });
  return (
    S2(
      function () {
        var r = Vm.get(n);
        if (r) {
          var o = new Set(r),
            i = new Set(e),
            s = n.current;
          o.forEach(function (a) {
            i.has(a) || rc(a, null);
          }),
            i.forEach(function (a) {
              o.has(a) || rc(a, s);
            });
        }
        Vm.set(n, e);
      },
      [e],
    ),
    n
  );
}
function C2(e) {
  return e;
}
function b2(e, t) {
  t === void 0 && (t = C2);
  var n = [],
    r = !1,
    o = {
      read: function () {
        if (r)
          throw new Error(
            "Sidecar: could not `read` from an `assigned` medium. `read` could be used only with `useMedium`.",
          );
        return n.length ? n[n.length - 1] : e;
      },
      useMedium: function (i) {
        var s = t(i, r);
        return (
          n.push(s),
          function () {
            n = n.filter(function (a) {
              return a !== s;
            });
          }
        );
      },
      assignSyncMedium: function (i) {
        for (r = !0; n.length; ) {
          var s = n;
          (n = []), s.forEach(i);
        }
        n = {
          push: function (a) {
            return i(a);
          },
          filter: function () {
            return n;
          },
        };
      },
      assignMedium: function (i) {
        r = !0;
        var s = [];
        if (n.length) {
          var a = n;
          (n = []), a.forEach(i), (s = n);
        }
        var l = function () {
            var c = s;
            (s = []), c.forEach(i);
          },
          u = function () {
            return Promise.resolve().then(l);
          };
        u(),
          (n = {
            push: function (c) {
              s.push(c), u();
            },
            filter: function (c) {
              return (s = s.filter(c)), n;
            },
          });
      },
    };
  return o;
}
function k2(e) {
  e === void 0 && (e = {});
  var t = b2(null);
  return (t.options = Yt({ async: !0, ssr: !1 }, e)), t;
}
var tw = function (e) {
  var t = e.sideCar,
    n = ew(e, ["sideCar"]);
  if (!t) throw new Error("Sidecar: please provide `sideCar` property to import the right car");
  var r = t.read();
  if (!r) throw new Error("Sidecar medium not found");
  return v.createElement(r, Yt({}, n));
};
tw.isSideCarExport = !0;
function _2(e, t) {
  return e.useMedium(t), tw;
}
var nw = k2(),
  oc = function () {},
  iu = v.forwardRef(function (e, t) {
    var n = v.useRef(null),
      r = v.useState({ onScrollCapture: oc, onWheelCapture: oc, onTouchMoveCapture: oc }),
      o = r[0],
      i = r[1],
      s = e.forwardProps,
      a = e.children,
      l = e.className,
      u = e.removeScrollBar,
      c = e.enabled,
      f = e.shards,
      d = e.sideCar,
      p = e.noRelative,
      y = e.noIsolation,
      m = e.inert,
      w = e.allowPinchZoom,
      h = e.as,
      g = h === void 0 ? "div" : h,
      x = e.gapMode,
      S = ew(e, [
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
      E = d,
      C = E2([n, t]),
      b = Yt(Yt({}, S), o);
    return v.createElement(
      v.Fragment,
      null,
      c &&
        v.createElement(E, {
          sideCar: nw,
          removeScrollBar: u,
          shards: f,
          noRelative: p,
          noIsolation: y,
          inert: m,
          setCallbacks: i,
          allowPinchZoom: !!w,
          lockRef: n,
          gapMode: x,
        }),
      s
        ? v.cloneElement(v.Children.only(a), Yt(Yt({}, b), { ref: C }))
        : v.createElement(g, Yt({}, b, { className: l, ref: C }), a),
    );
  });
iu.defaultProps = { enabled: !0, removeScrollBar: !0, inert: !1 };
iu.classNames = { fullWidth: $a, zeroRight: za };
var T2 = function () {
  if (typeof __webpack_nonce__ < "u") return __webpack_nonce__;
};
function N2() {
  if (!document) return null;
  var e = document.createElement("style");
  e.type = "text/css";
  var t = T2();
  return t && e.setAttribute("nonce", t), e;
}
function P2(e, t) {
  e.styleSheet ? (e.styleSheet.cssText = t) : e.appendChild(document.createTextNode(t));
}
function M2(e) {
  var t = document.head || document.getElementsByTagName("head")[0];
  t.appendChild(e);
}
var A2 = function () {
    var e = 0,
      t = null;
    return {
      add: function (n) {
        e == 0 && (t = N2()) && (P2(t, n), M2(t)), e++;
      },
      remove: function () {
        e--, !e && t && (t.parentNode && t.parentNode.removeChild(t), (t = null));
      },
    };
  },
  R2 = function () {
    var e = A2();
    return function (t, n) {
      v.useEffect(
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
  rw = function () {
    var e = R2(),
      t = function (n) {
        var r = n.styles,
          o = n.dynamic;
        return e(r, o), null;
      };
    return t;
  },
  D2 = { left: 0, top: 0, right: 0, gap: 0 },
  ic = function (e) {
    return parseInt(e || "", 10) || 0;
  },
  I2 = function (e) {
    var t = window.getComputedStyle(document.body),
      n = t[e === "padding" ? "paddingLeft" : "marginLeft"],
      r = t[e === "padding" ? "paddingTop" : "marginTop"],
      o = t[e === "padding" ? "paddingRight" : "marginRight"];
    return [ic(n), ic(r), ic(o)];
  },
  L2 = function (e) {
    if ((e === void 0 && (e = "margin"), typeof window > "u")) return D2;
    var t = I2(e),
      n = document.documentElement.clientWidth,
      r = window.innerWidth;
    return { left: t[0], top: t[1], right: t[2], gap: Math.max(0, r - n + t[2] - t[0]) };
  },
  V2 = rw(),
  _o = "data-scroll-locked",
  O2 = function (e, t, n, r) {
    var o = e.left,
      i = e.top,
      s = e.right,
      a = e.gap;
    return (
      n === void 0 && (n = "margin"),
      `
  .`
        .concat(
          v2,
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
          _o,
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
                  o,
                  `px;
    padding-top: `,
                )
                .concat(
                  i,
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
          za,
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
          $a,
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
        .concat(za, " .")
        .concat(
          za,
          ` {
    right: 0 `,
        )
        .concat(
          r,
          `;
  }

  .`,
        )
        .concat($a, " .")
        .concat(
          $a,
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
          _o,
          `] {
    `,
        )
        .concat(x2, ": ")
        .concat(
          a,
          `px;
  }
`,
        )
    );
  },
  Om = function () {
    var e = parseInt(document.body.getAttribute(_o) || "0", 10);
    return isFinite(e) ? e : 0;
  },
  F2 = function () {
    v.useEffect(function () {
      return (
        document.body.setAttribute(_o, (Om() + 1).toString()),
        function () {
          var e = Om() - 1;
          e <= 0 ? document.body.removeAttribute(_o) : document.body.setAttribute(_o, e.toString());
        }
      );
    }, []);
  },
  z2 = function (e) {
    var t = e.noRelative,
      n = e.noImportant,
      r = e.gapMode,
      o = r === void 0 ? "margin" : r;
    F2();
    var i = v.useMemo(
      function () {
        return L2(o);
      },
      [o],
    );
    return v.createElement(V2, { styles: O2(i, !t, o, n ? "" : "!important") });
  },
  Tf = !1;
if (typeof window < "u")
  try {
    var sa = Object.defineProperty({}, "passive", {
      get: function () {
        return (Tf = !0), !0;
      },
    });
    window.addEventListener("test", sa, sa), window.removeEventListener("test", sa, sa);
  } catch {
    Tf = !1;
  }
var Gr = Tf ? { passive: !1 } : !1,
  $2 = function (e) {
    return e.tagName === "TEXTAREA";
  },
  ow = function (e, t) {
    if (!(e instanceof Element)) return !1;
    var n = window.getComputedStyle(e);
    return n[t] !== "hidden" && !(n.overflowY === n.overflowX && !$2(e) && n[t] === "visible");
  },
  j2 = function (e) {
    return ow(e, "overflowY");
  },
  B2 = function (e) {
    return ow(e, "overflowX");
  },
  Fm = function (e, t) {
    var n = t.ownerDocument,
      r = t;
    do {
      typeof ShadowRoot < "u" && r instanceof ShadowRoot && (r = r.host);
      var o = iw(e, r);
      if (o) {
        var i = sw(e, r),
          s = i[1],
          a = i[2];
        if (s > a) return !0;
      }
      r = r.parentNode;
    } while (r && r !== n.body);
    return !1;
  },
  U2 = function (e) {
    var t = e.scrollTop,
      n = e.scrollHeight,
      r = e.clientHeight;
    return [t, n, r];
  },
  H2 = function (e) {
    var t = e.scrollLeft,
      n = e.scrollWidth,
      r = e.clientWidth;
    return [t, n, r];
  },
  iw = function (e, t) {
    return e === "v" ? j2(t) : B2(t);
  },
  sw = function (e, t) {
    return e === "v" ? U2(t) : H2(t);
  },
  W2 = function (e, t) {
    return e === "h" && t === "rtl" ? -1 : 1;
  },
  G2 = function (e, t, n, r, o) {
    var i = W2(e, window.getComputedStyle(t).direction),
      s = i * r,
      a = n.target,
      l = t.contains(a),
      u = !1,
      c = s > 0,
      f = 0,
      d = 0;
    do {
      if (!a) break;
      var p = sw(e, a),
        y = p[0],
        m = p[1],
        w = p[2],
        h = m - w - i * y;
      (y || h) && iw(e, a) && ((f += h), (d += y));
      var g = a.parentNode;
      a = g && g.nodeType === Node.DOCUMENT_FRAGMENT_NODE ? g.host : g;
    } while ((!l && a !== document.body) || (l && (t.contains(a) || t === a)));
    return ((c && Math.abs(f) < 1) || (!c && Math.abs(d) < 1)) && (u = !0), u;
  },
  aa = function (e) {
    return "changedTouches" in e
      ? [e.changedTouches[0].clientX, e.changedTouches[0].clientY]
      : [0, 0];
  },
  zm = function (e) {
    return [e.deltaX, e.deltaY];
  },
  $m = function (e) {
    return e && "current" in e ? e.current : e;
  },
  K2 = function (e, t) {
    return e[0] === t[0] && e[1] === t[1];
  },
  Y2 = function (e) {
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
  X2 = 0,
  Kr = [];
function Z2(e) {
  var t = v.useRef([]),
    n = v.useRef([0, 0]),
    r = v.useRef(),
    o = v.useState(X2++)[0],
    i = v.useState(rw)[0],
    s = v.useRef(e);
  v.useEffect(
    function () {
      s.current = e;
    },
    [e],
  ),
    v.useEffect(
      function () {
        if (e.inert) {
          document.body.classList.add("block-interactivity-".concat(o));
          var m = y2([e.lockRef.current], (e.shards || []).map($m), !0).filter(Boolean);
          return (
            m.forEach(function (w) {
              return w.classList.add("allow-interactivity-".concat(o));
            }),
            function () {
              document.body.classList.remove("block-interactivity-".concat(o)),
                m.forEach(function (w) {
                  return w.classList.remove("allow-interactivity-".concat(o));
                });
            }
          );
        }
      },
      [e.inert, e.lockRef.current, e.shards],
    );
  var a = v.useCallback(function (m, w) {
      if (("touches" in m && m.touches.length === 2) || (m.type === "wheel" && m.ctrlKey))
        return !s.current.allowPinchZoom;
      var h = aa(m),
        g = n.current,
        x = "deltaX" in m ? m.deltaX : g[0] - h[0],
        S = "deltaY" in m ? m.deltaY : g[1] - h[1],
        E,
        C = m.target,
        b = Math.abs(x) > Math.abs(S) ? "h" : "v";
      if ("touches" in m && b === "h" && C.type === "range") return !1;
      var _ = Fm(b, C);
      if (!_) return !0;
      if ((_ ? (E = b) : ((E = b === "v" ? "h" : "v"), (_ = Fm(b, C))), !_)) return !1;
      if ((!r.current && "changedTouches" in m && (x || S) && (r.current = E), !E)) return !0;
      var A = r.current || E;
      return G2(A, w, m, A === "h" ? x : S);
    }, []),
    l = v.useCallback(function (m) {
      var w = m;
      if (!(!Kr.length || Kr[Kr.length - 1] !== i)) {
        var h = "deltaY" in w ? zm(w) : aa(w),
          g = t.current.filter(function (E) {
            return (
              E.name === w.type &&
              (E.target === w.target || w.target === E.shadowParent) &&
              K2(E.delta, h)
            );
          })[0];
        if (g && g.should) {
          w.cancelable && w.preventDefault();
          return;
        }
        if (!g) {
          var x = (s.current.shards || [])
              .map($m)
              .filter(Boolean)
              .filter(function (E) {
                return E.contains(w.target);
              }),
            S = x.length > 0 ? a(w, x[0]) : !s.current.noIsolation;
          S && w.cancelable && w.preventDefault();
        }
      }
    }, []),
    u = v.useCallback(function (m, w, h, g) {
      var x = { name: m, delta: w, target: h, should: g, shadowParent: Q2(h) };
      t.current.push(x),
        setTimeout(function () {
          t.current = t.current.filter(function (S) {
            return S !== x;
          });
        }, 1);
    }, []),
    c = v.useCallback(function (m) {
      (n.current = aa(m)), (r.current = void 0);
    }, []),
    f = v.useCallback(function (m) {
      u(m.type, zm(m), m.target, a(m, e.lockRef.current));
    }, []),
    d = v.useCallback(function (m) {
      u(m.type, aa(m), m.target, a(m, e.lockRef.current));
    }, []);
  v.useEffect(function () {
    return (
      Kr.push(i),
      e.setCallbacks({ onScrollCapture: f, onWheelCapture: f, onTouchMoveCapture: d }),
      document.addEventListener("wheel", l, Gr),
      document.addEventListener("touchmove", l, Gr),
      document.addEventListener("touchstart", c, Gr),
      function () {
        (Kr = Kr.filter(function (m) {
          return m !== i;
        })),
          document.removeEventListener("wheel", l, Gr),
          document.removeEventListener("touchmove", l, Gr),
          document.removeEventListener("touchstart", c, Gr);
      }
    );
  }, []);
  var p = e.removeScrollBar,
    y = e.inert;
  return v.createElement(
    v.Fragment,
    null,
    y ? v.createElement(i, { styles: Y2(o) }) : null,
    p ? v.createElement(z2, { noRelative: e.noRelative, gapMode: e.gapMode }) : null,
  );
}
function Q2(e) {
  for (var t = null; e !== null; )
    e instanceof ShadowRoot && ((t = e.host), (e = e.host)), (e = e.parentNode);
  return t;
}
const q2 = _2(nw, Z2);
var aw = v.forwardRef(function (e, t) {
  return v.createElement(iu, Yt({}, e, { ref: t, sideCar: q2 }));
});
aw.classNames = iu.classNames;
var J2 = function (e) {
    if (typeof document > "u") return null;
    var t = Array.isArray(e) ? e[0] : e;
    return t.ownerDocument.body;
  },
  Yr = new WeakMap(),
  la = new WeakMap(),
  ua = {},
  sc = 0,
  lw = function (e) {
    return e && (e.host || lw(e.parentNode));
  },
  eN = function (e, t) {
    return t
      .map(function (n) {
        if (e.contains(n)) return n;
        var r = lw(n);
        return r && e.contains(r)
          ? r
          : (console.error("aria-hidden", n, "in not contained inside", e, ". Doing nothing"),
            null);
      })
      .filter(function (n) {
        return !!n;
      });
  },
  tN = function (e, t, n, r) {
    var o = eN(t, Array.isArray(e) ? e : [e]);
    ua[n] || (ua[n] = new WeakMap());
    var i = ua[n],
      s = [],
      a = new Set(),
      l = new Set(o),
      u = function (f) {
        !f || a.has(f) || (a.add(f), u(f.parentNode));
      };
    o.forEach(u);
    var c = function (f) {
      !f ||
        l.has(f) ||
        Array.prototype.forEach.call(f.children, function (d) {
          if (a.has(d)) c(d);
          else
            try {
              var p = d.getAttribute(r),
                y = p !== null && p !== "false",
                m = (Yr.get(d) || 0) + 1,
                w = (i.get(d) || 0) + 1;
              Yr.set(d, m),
                i.set(d, w),
                s.push(d),
                m === 1 && y && la.set(d, !0),
                w === 1 && d.setAttribute(n, "true"),
                y || d.setAttribute(r, "true");
            } catch (h) {
              console.error("aria-hidden: cannot operate on ", d, h);
            }
        });
    };
    return (
      c(t),
      a.clear(),
      sc++,
      function () {
        s.forEach(function (f) {
          var d = Yr.get(f) - 1,
            p = i.get(f) - 1;
          Yr.set(f, d),
            i.set(f, p),
            d || (la.has(f) || f.removeAttribute(r), la.delete(f)),
            p || f.removeAttribute(n);
        }),
          sc--,
          sc || ((Yr = new WeakMap()), (Yr = new WeakMap()), (la = new WeakMap()), (ua = {}));
      }
    );
  },
  nN = function (e, t, n) {
    n === void 0 && (n = "data-aria-hidden");
    var r = Array.from(Array.isArray(e) ? e : [e]),
      o = J2(e);
    return o
      ? (r.push.apply(r, Array.from(o.querySelectorAll("[aria-live], script"))),
        tN(r, o, n, "aria-hidden"))
      : function () {
          return null;
        };
  },
  su = "Dialog",
  [uw, vO] = ru(su),
  [rN, jt] = uw(su),
  cw = (e) => {
    const {
        __scopeDialog: t,
        children: n,
        open: r,
        defaultOpen: o,
        onOpenChange: i,
        modal: s = !0,
      } = e,
      a = v.useRef(null),
      l = v.useRef(null),
      [u, c] = sh({ prop: r, defaultProp: o ?? !1, onChange: i, caller: su });
    return N.jsx(rN, {
      scope: t,
      triggerRef: a,
      contentRef: l,
      contentId: zi(),
      titleId: zi(),
      descriptionId: zi(),
      open: u,
      onOpenChange: c,
      onOpenToggle: v.useCallback(() => c((f) => !f), [c]),
      modal: s,
      children: n,
    });
  };
cw.displayName = su;
var fw = "DialogTrigger",
  oN = v.forwardRef((e, t) => {
    const { __scopeDialog: n, ...r } = e,
      o = jt(fw, n),
      i = tn(t, o.triggerRef);
    return N.jsx(et.button, {
      type: "button",
      "aria-haspopup": "dialog",
      "aria-expanded": o.open,
      "aria-controls": o.contentId,
      "data-state": ch(o.open),
      ...r,
      ref: i,
      onClick: Fe(e.onClick, o.onOpenToggle),
    });
  });
oN.displayName = fw;
var lh = "DialogPortal",
  [iN, dw] = uw(lh, { forceMount: void 0 }),
  hw = (e) => {
    const { __scopeDialog: t, forceMount: n, children: r, container: o } = e,
      i = jt(lh, t);
    return N.jsx(iN, {
      scope: t,
      forceMount: n,
      children: v.Children.map(r, (s) =>
        N.jsx(Ls, {
          present: n || i.open,
          children: N.jsx(Jx, { asChild: !0, container: o, children: s }),
        }),
      ),
    });
  };
hw.displayName = lh;
var xl = "DialogOverlay",
  pw = v.forwardRef((e, t) => {
    const n = dw(xl, e.__scopeDialog),
      { forceMount: r = n.forceMount, ...o } = e,
      i = jt(xl, e.__scopeDialog);
    return i.modal
      ? N.jsx(Ls, { present: r || i.open, children: N.jsx(aN, { ...o, ref: t }) })
      : null;
  });
pw.displayName = xl;
var sN = us("DialogOverlay.RemoveScroll"),
  aN = v.forwardRef((e, t) => {
    const { __scopeDialog: n, ...r } = e,
      o = jt(xl, n);
    return N.jsx(aw, {
      as: sN,
      allowPinchZoom: !0,
      shards: [o.contentRef],
      children: N.jsx(et.div, {
        "data-state": ch(o.open),
        ...r,
        ref: t,
        style: { pointerEvents: "auto", ...r.style },
      }),
    });
  }),
  Ir = "DialogContent",
  mw = v.forwardRef((e, t) => {
    const n = dw(Ir, e.__scopeDialog),
      { forceMount: r = n.forceMount, ...o } = e,
      i = jt(Ir, e.__scopeDialog);
    return N.jsx(Ls, {
      present: r || i.open,
      children: i.modal ? N.jsx(lN, { ...o, ref: t }) : N.jsx(uN, { ...o, ref: t }),
    });
  });
mw.displayName = Ir;
var lN = v.forwardRef((e, t) => {
    const n = jt(Ir, e.__scopeDialog),
      r = v.useRef(null),
      o = tn(t, n.contentRef, r);
    return (
      v.useEffect(() => {
        const i = r.current;
        if (i) return nN(i);
      }, []),
      N.jsx(gw, {
        ...e,
        ref: o,
        trapFocus: n.open,
        disableOutsidePointerEvents: !0,
        onCloseAutoFocus: Fe(e.onCloseAutoFocus, (i) => {
          var s;
          i.preventDefault(), (s = n.triggerRef.current) == null || s.focus();
        }),
        onPointerDownOutside: Fe(e.onPointerDownOutside, (i) => {
          const s = i.detail.originalEvent,
            a = s.button === 0 && s.ctrlKey === !0;
          (s.button === 2 || a) && i.preventDefault();
        }),
        onFocusOutside: Fe(e.onFocusOutside, (i) => i.preventDefault()),
      })
    );
  }),
  uN = v.forwardRef((e, t) => {
    const n = jt(Ir, e.__scopeDialog),
      r = v.useRef(!1),
      o = v.useRef(!1);
    return N.jsx(gw, {
      ...e,
      ref: t,
      trapFocus: !1,
      disableOutsidePointerEvents: !1,
      onCloseAutoFocus: (i) => {
        var s, a;
        (s = e.onCloseAutoFocus) == null || s.call(e, i),
          i.defaultPrevented ||
            (r.current || (a = n.triggerRef.current) == null || a.focus(), i.preventDefault()),
          (r.current = !1),
          (o.current = !1);
      },
      onInteractOutside: (i) => {
        var l, u;
        (l = e.onInteractOutside) == null || l.call(e, i),
          i.defaultPrevented ||
            ((r.current = !0), i.detail.originalEvent.type === "pointerdown" && (o.current = !0));
        const s = i.target;
        ((u = n.triggerRef.current) == null ? void 0 : u.contains(s)) && i.preventDefault(),
          i.detail.originalEvent.type === "focusin" && o.current && i.preventDefault();
      },
    });
  }),
  gw = v.forwardRef((e, t) => {
    const { __scopeDialog: n, trapFocus: r, onOpenAutoFocus: o, onCloseAutoFocus: i, ...s } = e,
      a = jt(Ir, n),
      l = v.useRef(null),
      u = tn(t, l);
    return (
      g2(),
      N.jsxs(N.Fragment, {
        children: [
          N.jsx(Qx, {
            asChild: !0,
            loop: !0,
            trapped: r,
            onMountAutoFocus: o,
            onUnmountAutoFocus: i,
            children: N.jsx(Xx, {
              role: "dialog",
              id: a.contentId,
              "aria-describedby": a.descriptionId,
              "aria-labelledby": a.titleId,
              "data-state": ch(a.open),
              ...s,
              ref: u,
              onDismiss: () => a.onOpenChange(!1),
            }),
          }),
          N.jsxs(N.Fragment, {
            children: [
              N.jsx(cN, { titleId: a.titleId }),
              N.jsx(dN, { contentRef: l, descriptionId: a.descriptionId }),
            ],
          }),
        ],
      })
    );
  }),
  uh = "DialogTitle",
  yw = v.forwardRef((e, t) => {
    const { __scopeDialog: n, ...r } = e,
      o = jt(uh, n);
    return N.jsx(et.h2, { id: o.titleId, ...r, ref: t });
  });
yw.displayName = uh;
var vw = "DialogDescription",
  xw = v.forwardRef((e, t) => {
    const { __scopeDialog: n, ...r } = e,
      o = jt(vw, n);
    return N.jsx(et.p, { id: o.descriptionId, ...r, ref: t });
  });
xw.displayName = vw;
var ww = "DialogClose",
  Sw = v.forwardRef((e, t) => {
    const { __scopeDialog: n, ...r } = e,
      o = jt(ww, n);
    return N.jsx(et.button, {
      type: "button",
      ...r,
      ref: t,
      onClick: Fe(e.onClick, () => o.onOpenChange(!1)),
    });
  });
Sw.displayName = ww;
function ch(e) {
  return e ? "open" : "closed";
}
var Ew = "DialogTitleWarning",
  [xO, Cw] = bT(Ew, { contentName: Ir, titleName: uh, docsSlug: "dialog" }),
  cN = ({ titleId: e }) => {
    const t = Cw(Ew),
      n = `\`${t.contentName}\` requires a \`${t.titleName}\` for the component to be accessible for screen reader users.

If you want to hide the \`${t.titleName}\`, you can wrap it with our VisuallyHidden component.

For more information, see https://radix-ui.com/primitives/docs/components/${t.docsSlug}`;
    return (
      v.useEffect(() => {
        e && (document.getElementById(e) || console.error(n));
      }, [n, e]),
      null
    );
  },
  fN = "DialogDescriptionWarning",
  dN = ({ contentRef: e, descriptionId: t }) => {
    const r = `Warning: Missing \`Description\` or \`aria-describedby={undefined}\` for {${Cw(fN).contentName}}.`;
    return (
      v.useEffect(() => {
        var i;
        const o = (i = e.current) == null ? void 0 : i.getAttribute("aria-describedby");
        t && o && (document.getElementById(t) || console.warn(r));
      }, [r, e, t]),
      null
    );
  },
  hN = cw,
  pN = hw,
  bw = pw,
  kw = mw,
  _w = yw,
  Tw = xw,
  mN = Sw;
const gN = hN,
  yN = pN,
  Nw = v.forwardRef(({ className: e, ...t }, n) =>
    N.jsx(bw, {
      ref: n,
      className: le(
        "fixed inset-0 z-50 bg-black/80 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0",
        e,
      ),
      ...t,
    }),
  );
Nw.displayName = bw.displayName;
const Pw = v.forwardRef(({ className: e, children: t, ...n }, r) =>
  N.jsxs(yN, {
    children: [
      N.jsx(Nw, {}),
      N.jsxs(kw, {
        ref: r,
        className: le(
          "fixed left-[50%] top-[50%] z-50 grid w-full max-w-lg translate-x-[-50%] translate-y-[-50%] gap-4 border bg-background p-6 shadow-lg duration-200 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95 data-[state=closed]:slide-out-to-left-1/2 data-[state=closed]:slide-out-to-top-[48%] data-[state=open]:slide-in-from-left-1/2 data-[state=open]:slide-in-from-top-[48%] sm:rounded-lg",
          e,
        ),
        ...n,
        children: [
          t,
          N.jsxs(mN, {
            className:
              "absolute right-4 top-4 rounded-sm opacity-70 ring-offset-background transition-opacity hover:opacity-100 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:pointer-events-none data-[state=open]:bg-accent data-[state=open]:text-muted-foreground",
            children: [
              N.jsx(L_, { className: "h-4 w-4" }),
              N.jsx("span", { className: "sr-only", children: "Close" }),
            ],
          }),
        ],
      }),
    ],
  }),
);
Pw.displayName = kw.displayName;
const Mw = ({ className: e, ...t }) =>
  N.jsx("div", { className: le("flex flex-col space-y-1.5 text-center sm:text-left", e), ...t });
Mw.displayName = "DialogHeader";
const Aw = ({ className: e, ...t }) =>
  N.jsx("div", {
    className: le("flex flex-col-reverse sm:flex-row sm:justify-end sm:space-x-2", e),
    ...t,
  });
Aw.displayName = "DialogFooter";
const Rw = v.forwardRef(({ className: e, ...t }, n) =>
  N.jsx(_w, {
    ref: n,
    className: le("text-lg font-semibold leading-none tracking-tight", e),
    ...t,
  }),
);
Rw.displayName = _w.displayName;
const vN = v.forwardRef(({ className: e, ...t }, n) =>
  N.jsx(Tw, { ref: n, className: le("text-sm text-muted-foreground", e), ...t }),
);
vN.displayName = Tw.displayName;
const Dw = v.forwardRef(({ className: e, type: t, ...n }, r) =>
  N.jsx("input", {
    type: t,
    className: le(
      "flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-base ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium file:text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 md:text-sm",
      e,
    ),
    ref: r,
    ...n,
  }),
);
Dw.displayName = "Input";
const Iw = v.forwardRef(({ className: e, ...t }, n) =>
  N.jsx("textarea", {
    className: le(
      "flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-base ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 md:text-sm",
      e,
    ),
    ref: n,
    ...t,
  }),
);
Iw.displayName = "Textarea";
const Lw = v.createContext({});
function fh(e) {
  const t = v.useRef(null);
  return t.current === null && (t.current = e()), t.current;
}
const dh = v.createContext(null),
  au = v.createContext({ transformPagePoint: (e) => e, isStatic: !1, reducedMotion: "never" });
function xN(e = !0) {
  const t = v.useContext(dh);
  if (t === null) return [!0, null];
  const { isPresent: n, onExitComplete: r, register: o } = t,
    i = v.useId();
  v.useEffect(() => {
    e && o(i);
  }, [e]);
  const s = v.useCallback(() => e && r && r(i), [i, r, e]);
  return !n && r ? [!1, s] : [!0];
}
const hh = typeof window < "u",
  ph = hh ? v.useLayoutEffect : v.useEffect,
  dt = (e) => e;
let Vw = dt;
function mh(e) {
  let t;
  return () => (t === void 0 && (t = e()), t);
}
const $o = (e, t, n) => {
    const r = t - e;
    return r === 0 ? 1 : (n - e) / r;
  },
  gn = (e) => e * 1e3,
  yn = (e) => e / 1e3,
  wN = { useManualTiming: !1 };
function SN(e) {
  let t = new Set(),
    n = new Set(),
    r = !1,
    o = !1;
  const i = new WeakSet();
  let s = { delta: 0, timestamp: 0, isProcessing: !1 };
  function a(u) {
    i.has(u) && (l.schedule(u), e()), u(s);
  }
  const l = {
    schedule: (u, c = !1, f = !1) => {
      const p = f && r ? t : n;
      return c && i.add(u), p.has(u) || p.add(u), u;
    },
    cancel: (u) => {
      n.delete(u), i.delete(u);
    },
    process: (u) => {
      if (((s = u), r)) {
        o = !0;
        return;
      }
      (r = !0), ([t, n] = [n, t]), t.forEach(a), t.clear(), (r = !1), o && ((o = !1), l.process(u));
    },
  };
  return l;
}
const ca = ["read", "resolveKeyframes", "update", "preRender", "render", "postRender"],
  EN = 40;
function Ow(e, t) {
  let n = !1,
    r = !0;
  const o = { delta: 0, timestamp: 0, isProcessing: !1 },
    i = () => (n = !0),
    s = ca.reduce((h, g) => ((h[g] = SN(i)), h), {}),
    { read: a, resolveKeyframes: l, update: u, preRender: c, render: f, postRender: d } = s,
    p = () => {
      const h = performance.now();
      (n = !1),
        (o.delta = r ? 1e3 / 60 : Math.max(Math.min(h - o.timestamp, EN), 1)),
        (o.timestamp = h),
        (o.isProcessing = !0),
        a.process(o),
        l.process(o),
        u.process(o),
        c.process(o),
        f.process(o),
        d.process(o),
        (o.isProcessing = !1),
        n && t && ((r = !1), e(p));
    },
    y = () => {
      (n = !0), (r = !0), o.isProcessing || e(p);
    };
  return {
    schedule: ca.reduce((h, g) => {
      const x = s[g];
      return (h[g] = (S, E = !1, C = !1) => (n || y(), x.schedule(S, E, C))), h;
    }, {}),
    cancel: (h) => {
      for (let g = 0; g < ca.length; g++) s[ca[g]].cancel(h);
    },
    state: o,
    steps: s,
  };
}
const {
    schedule: ae,
    cancel: Cn,
    state: Me,
    steps: ac,
  } = Ow(typeof requestAnimationFrame < "u" ? requestAnimationFrame : dt, !0),
  Fw = v.createContext({ strict: !1 }),
  jm = {
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
  jo = {};
for (const e in jm) jo[e] = { isEnabled: (t) => jm[e].some((n) => !!t[n]) };
function CN(e) {
  for (const t in e) jo[t] = { ...jo[t], ...e[t] };
}
const bN = new Set([
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
function wl(e) {
  return (
    e.startsWith("while") ||
    (e.startsWith("drag") && e !== "draggable") ||
    e.startsWith("layout") ||
    e.startsWith("onTap") ||
    e.startsWith("onPan") ||
    e.startsWith("onLayout") ||
    bN.has(e)
  );
}
let zw = (e) => !wl(e);
function kN(e) {
  e && (zw = (t) => (t.startsWith("on") ? !wl(t) : e(t)));
}
try {
  kN(require("@emotion/is-prop-valid").default);
} catch {}
function _N(e, t, n) {
  const r = {};
  for (const o in e)
    (o === "values" && typeof e.values == "object") ||
      ((zw(o) ||
        (n === !0 && wl(o)) ||
        (!t && !wl(o)) ||
        (e.draggable && o.startsWith("onDrag"))) &&
        (r[o] = e[o]));
  return r;
}
function TN(e) {
  if (typeof Proxy > "u") return e;
  const t = new Map(),
    n = (...r) => e(...r);
  return new Proxy(n, {
    get: (r, o) => (o === "create" ? e : (t.has(o) || t.set(o, e(o)), t.get(o))),
  });
}
const lu = v.createContext({});
function fs(e) {
  return typeof e == "string" || Array.isArray(e);
}
function uu(e) {
  return e !== null && typeof e == "object" && typeof e.start == "function";
}
const gh = ["animate", "whileInView", "whileFocus", "whileHover", "whileTap", "whileDrag", "exit"],
  yh = ["initial", ...gh];
function cu(e) {
  return uu(e.animate) || yh.some((t) => fs(e[t]));
}
function $w(e) {
  return !!(cu(e) || e.variants);
}
function NN(e, t) {
  if (cu(e)) {
    const { initial: n, animate: r } = e;
    return { initial: n === !1 || fs(n) ? n : void 0, animate: fs(r) ? r : void 0 };
  }
  return e.inherit !== !1 ? t : {};
}
function PN(e) {
  const { initial: t, animate: n } = NN(e, v.useContext(lu));
  return v.useMemo(() => ({ initial: t, animate: n }), [Bm(t), Bm(n)]);
}
function Bm(e) {
  return Array.isArray(e) ? e.join(" ") : e;
}
const MN = Symbol.for("motionComponentSymbol");
function fo(e) {
  return e && typeof e == "object" && Object.prototype.hasOwnProperty.call(e, "current");
}
function AN(e, t, n) {
  return v.useCallback(
    (r) => {
      r && e.onMount && e.onMount(r),
        t && (r ? t.mount(r) : t.unmount()),
        n && (typeof n == "function" ? n(r) : fo(n) && (n.current = r));
    },
    [t],
  );
}
const vh = (e) => e.replace(/([a-z])([A-Z])/gu, "$1-$2").toLowerCase(),
  RN = "framerAppearId",
  jw = "data-" + vh(RN),
  { schedule: xh } = Ow(queueMicrotask, !1),
  Bw = v.createContext({});
function DN(e, t, n, r, o) {
  var i, s;
  const { visualElement: a } = v.useContext(lu),
    l = v.useContext(Fw),
    u = v.useContext(dh),
    c = v.useContext(au).reducedMotion,
    f = v.useRef(null);
  (r = r || l.renderer),
    !f.current &&
      r &&
      (f.current = r(e, {
        visualState: t,
        parent: a,
        props: n,
        presenceContext: u,
        blockInitialAnimation: u ? u.initial === !1 : !1,
        reducedMotionConfig: c,
      }));
  const d = f.current,
    p = v.useContext(Bw);
  d && !d.projection && o && (d.type === "html" || d.type === "svg") && IN(f.current, n, o, p);
  const y = v.useRef(!1);
  v.useInsertionEffect(() => {
    d && y.current && d.update(n, u);
  });
  const m = n[jw],
    w = v.useRef(
      !!m &&
        !(!((i = window.MotionHandoffIsComplete) === null || i === void 0) && i.call(window, m)) &&
        ((s = window.MotionHasOptimisedAnimation) === null || s === void 0
          ? void 0
          : s.call(window, m)),
    );
  return (
    ph(() => {
      d &&
        ((y.current = !0),
        (window.MotionIsMounted = !0),
        d.updateFeatures(),
        xh.render(d.render),
        w.current && d.animationState && d.animationState.animateChanges());
    }),
    v.useEffect(() => {
      d &&
        (!w.current && d.animationState && d.animationState.animateChanges(),
        w.current &&
          (queueMicrotask(() => {
            var h;
            (h = window.MotionHandoffMarkAsComplete) === null || h === void 0 || h.call(window, m);
          }),
          (w.current = !1)));
    }),
    d
  );
}
function IN(e, t, n, r) {
  const { layoutId: o, layout: i, drag: s, dragConstraints: a, layoutScroll: l, layoutRoot: u } = t;
  (e.projection = new n(e.latestValues, t["data-framer-portal-id"] ? void 0 : Uw(e.parent))),
    e.projection.setOptions({
      layoutId: o,
      layout: i,
      alwaysMeasureLayout: !!s || (a && fo(a)),
      visualElement: e,
      animationType: typeof i == "string" ? i : "both",
      initialPromotionConfig: r,
      layoutScroll: l,
      layoutRoot: u,
    });
}
function Uw(e) {
  if (e) return e.options.allowProjection !== !1 ? e.projection : Uw(e.parent);
}
function LN({
  preloadedFeatures: e,
  createVisualElement: t,
  useRender: n,
  useVisualState: r,
  Component: o,
}) {
  var i, s;
  e && CN(e);
  function a(u, c) {
    let f;
    const d = { ...v.useContext(au), ...u, layoutId: VN(u) },
      { isStatic: p } = d,
      y = PN(u),
      m = r(u, p);
    if (!p && hh) {
      ON();
      const w = FN(d);
      (f = w.MeasureLayout), (y.visualElement = DN(o, m, d, t, w.ProjectionNode));
    }
    return N.jsxs(lu.Provider, {
      value: y,
      children: [
        f && y.visualElement ? N.jsx(f, { visualElement: y.visualElement, ...d }) : null,
        n(o, u, AN(m, y.visualElement, c), m, p, y.visualElement),
      ],
    });
  }
  a.displayName = `motion.${typeof o == "string" ? o : `create(${(s = (i = o.displayName) !== null && i !== void 0 ? i : o.name) !== null && s !== void 0 ? s : ""})`}`;
  const l = v.forwardRef(a);
  return (l[MN] = o), l;
}
function VN({ layoutId: e }) {
  const t = v.useContext(Lw).id;
  return t && e !== void 0 ? t + "-" + e : e;
}
function ON(e, t) {
  v.useContext(Fw).strict;
}
function FN(e) {
  const { drag: t, layout: n } = jo;
  if (!t && !n) return {};
  const r = { ...t, ...n };
  return {
    MeasureLayout:
      (t != null && t.isEnabled(e)) || (n != null && n.isEnabled(e)) ? r.MeasureLayout : void 0,
    ProjectionNode: r.ProjectionNode,
  };
}
const zN = [
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
function wh(e) {
  return typeof e != "string" || e.includes("-") ? !1 : !!(zN.indexOf(e) > -1 || /[A-Z]/u.test(e));
}
function Um(e) {
  const t = [{}, {}];
  return (
    e == null ||
      e.values.forEach((n, r) => {
        (t[0][r] = n.get()), (t[1][r] = n.getVelocity());
      }),
    t
  );
}
function Sh(e, t, n, r) {
  if (typeof t == "function") {
    const [o, i] = Um(r);
    t = t(n !== void 0 ? n : e.custom, o, i);
  }
  if ((typeof t == "string" && (t = e.variants && e.variants[t]), typeof t == "function")) {
    const [o, i] = Um(r);
    t = t(n !== void 0 ? n : e.custom, o, i);
  }
  return t;
}
const Nf = (e) => Array.isArray(e),
  $N = (e) => !!(e && typeof e == "object" && e.mix && e.toValue),
  jN = (e) => (Nf(e) ? e[e.length - 1] || 0 : e),
  Re = (e) => !!(e && e.getVelocity);
function ja(e) {
  const t = Re(e) ? e.get() : e;
  return $N(t) ? t.toValue() : t;
}
function BN({ scrapeMotionValuesFromProps: e, createRenderState: t, onUpdate: n }, r, o, i) {
  const s = { latestValues: UN(r, o, i, e), renderState: t() };
  return (
    n && ((s.onMount = (a) => n({ props: r, current: a, ...s })), (s.onUpdate = (a) => n(a))), s
  );
}
const Hw = (e) => (t, n) => {
  const r = v.useContext(lu),
    o = v.useContext(dh),
    i = () => BN(e, t, r, o);
  return n ? i() : fh(i);
};
function UN(e, t, n, r) {
  const o = {},
    i = r(e, {});
  for (const d in i) o[d] = ja(i[d]);
  let { initial: s, animate: a } = e;
  const l = cu(e),
    u = $w(e);
  t &&
    u &&
    !l &&
    e.inherit !== !1 &&
    (s === void 0 && (s = t.initial), a === void 0 && (a = t.animate));
  let c = n ? n.initial === !1 : !1;
  c = c || s === !1;
  const f = c ? a : s;
  if (f && typeof f != "boolean" && !uu(f)) {
    const d = Array.isArray(f) ? f : [f];
    for (let p = 0; p < d.length; p++) {
      const y = Sh(e, d[p]);
      if (y) {
        const { transitionEnd: m, transition: w, ...h } = y;
        for (const g in h) {
          let x = h[g];
          if (Array.isArray(x)) {
            const S = c ? x.length - 1 : 0;
            x = x[S];
          }
          x !== null && (o[g] = x);
        }
        for (const g in m) o[g] = m[g];
      }
    }
  }
  return o;
}
const Qo = [
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
  zr = new Set(Qo),
  Ww = (e) => (t) => typeof t == "string" && t.startsWith(e),
  Gw = Ww("--"),
  HN = Ww("var(--"),
  Eh = (e) => (HN(e) ? WN.test(e.split("/*")[0].trim()) : !1),
  WN = /var\(--(?:[\w-]+\s*|[\w-]+\s*,(?:\s*[^)(\s]|\s*\((?:[^)(]|\([^)(]*\))*\))+\s*)\)$/iu,
  Kw = (e, t) => (t && typeof e == "number" ? t.transform(e) : e),
  bn = (e, t, n) => (n > t ? t : n < e ? e : n),
  qo = { test: (e) => typeof e == "number", parse: parseFloat, transform: (e) => e },
  ds = { ...qo, transform: (e) => bn(0, 1, e) },
  fa = { ...qo, default: 1 },
  Vs = (e) => ({
    test: (t) => typeof t == "string" && t.endsWith(e) && t.split(" ").length === 1,
    parse: parseFloat,
    transform: (t) => `${t}${e}`,
  }),
  Dn = Vs("deg"),
  qt = Vs("%"),
  X = Vs("px"),
  GN = Vs("vh"),
  KN = Vs("vw"),
  Hm = { ...qt, parse: (e) => qt.parse(e) / 100, transform: (e) => qt.transform(e * 100) },
  YN = {
    borderWidth: X,
    borderTopWidth: X,
    borderRightWidth: X,
    borderBottomWidth: X,
    borderLeftWidth: X,
    borderRadius: X,
    radius: X,
    borderTopLeftRadius: X,
    borderTopRightRadius: X,
    borderBottomRightRadius: X,
    borderBottomLeftRadius: X,
    width: X,
    maxWidth: X,
    height: X,
    maxHeight: X,
    top: X,
    right: X,
    bottom: X,
    left: X,
    padding: X,
    paddingTop: X,
    paddingRight: X,
    paddingBottom: X,
    paddingLeft: X,
    margin: X,
    marginTop: X,
    marginRight: X,
    marginBottom: X,
    marginLeft: X,
    backgroundPositionX: X,
    backgroundPositionY: X,
  },
  XN = {
    rotate: Dn,
    rotateX: Dn,
    rotateY: Dn,
    rotateZ: Dn,
    scale: fa,
    scaleX: fa,
    scaleY: fa,
    scaleZ: fa,
    skew: Dn,
    skewX: Dn,
    skewY: Dn,
    distance: X,
    translateX: X,
    translateY: X,
    translateZ: X,
    x: X,
    y: X,
    z: X,
    perspective: X,
    transformPerspective: X,
    opacity: ds,
    originX: Hm,
    originY: Hm,
    originZ: X,
  },
  Wm = { ...qo, transform: Math.round },
  Ch = { ...YN, ...XN, zIndex: Wm, size: X, fillOpacity: ds, strokeOpacity: ds, numOctaves: Wm },
  ZN = { x: "translateX", y: "translateY", z: "translateZ", transformPerspective: "perspective" },
  QN = Qo.length;
function qN(e, t, n) {
  let r = "",
    o = !0;
  for (let i = 0; i < QN; i++) {
    const s = Qo[i],
      a = e[s];
    if (a === void 0) continue;
    let l = !0;
    if (
      (typeof a == "number"
        ? (l = a === (s.startsWith("scale") ? 1 : 0))
        : (l = parseFloat(a) === 0),
      !l || n)
    ) {
      const u = Kw(a, Ch[s]);
      if (!l) {
        o = !1;
        const c = ZN[s] || s;
        r += `${c}(${u}) `;
      }
      n && (t[s] = u);
    }
  }
  return (r = r.trim()), n ? (r = n(t, o ? "" : r)) : o && (r = "none"), r;
}
function bh(e, t, n) {
  const { style: r, vars: o, transformOrigin: i } = e;
  let s = !1,
    a = !1;
  for (const l in t) {
    const u = t[l];
    if (zr.has(l)) {
      s = !0;
      continue;
    } else if (Gw(l)) {
      o[l] = u;
      continue;
    } else {
      const c = Kw(u, Ch[l]);
      l.startsWith("origin") ? ((a = !0), (i[l] = c)) : (r[l] = c);
    }
  }
  if (
    (t.transform ||
      (s || n ? (r.transform = qN(t, e.transform, n)) : r.transform && (r.transform = "none")),
    a)
  ) {
    const { originX: l = "50%", originY: u = "50%", originZ: c = 0 } = i;
    r.transformOrigin = `${l} ${u} ${c}`;
  }
}
const JN = { offset: "stroke-dashoffset", array: "stroke-dasharray" },
  eP = { offset: "strokeDashoffset", array: "strokeDasharray" };
function tP(e, t, n = 1, r = 0, o = !0) {
  e.pathLength = 1;
  const i = o ? JN : eP;
  e[i.offset] = X.transform(-r);
  const s = X.transform(t),
    a = X.transform(n);
  e[i.array] = `${s} ${a}`;
}
function Gm(e, t, n) {
  return typeof e == "string" ? e : X.transform(t + n * e);
}
function nP(e, t, n) {
  const r = Gm(t, e.x, e.width),
    o = Gm(n, e.y, e.height);
  return `${r} ${o}`;
}
function kh(
  e,
  {
    attrX: t,
    attrY: n,
    attrScale: r,
    originX: o,
    originY: i,
    pathLength: s,
    pathSpacing: a = 1,
    pathOffset: l = 0,
    ...u
  },
  c,
  f,
) {
  if ((bh(e, u, f), c)) {
    e.style.viewBox && (e.attrs.viewBox = e.style.viewBox);
    return;
  }
  (e.attrs = e.style), (e.style = {});
  const { attrs: d, style: p, dimensions: y } = e;
  d.transform && (y && (p.transform = d.transform), delete d.transform),
    y &&
      (o !== void 0 || i !== void 0 || p.transform) &&
      (p.transformOrigin = nP(y, o !== void 0 ? o : 0.5, i !== void 0 ? i : 0.5)),
    t !== void 0 && (d.x = t),
    n !== void 0 && (d.y = n),
    r !== void 0 && (d.scale = r),
    s !== void 0 && tP(d, s, a, l, !1);
}
const _h = () => ({ style: {}, transform: {}, transformOrigin: {}, vars: {} }),
  Yw = () => ({ ..._h(), attrs: {} }),
  Th = (e) => typeof e == "string" && e.toLowerCase() === "svg";
function Xw(e, { style: t, vars: n }, r, o) {
  Object.assign(e.style, t, o && o.getProjectionStyles(r));
  for (const i in n) e.style.setProperty(i, n[i]);
}
const Zw = new Set([
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
function Qw(e, t, n, r) {
  Xw(e, t, void 0, r);
  for (const o in t.attrs) e.setAttribute(Zw.has(o) ? o : vh(o), t.attrs[o]);
}
const Sl = {};
function rP(e) {
  Object.assign(Sl, e);
}
function qw(e, { layout: t, layoutId: n }) {
  return (
    zr.has(e) || e.startsWith("origin") || ((t || n !== void 0) && (!!Sl[e] || e === "opacity"))
  );
}
function Nh(e, t, n) {
  var r;
  const { style: o } = e,
    i = {};
  for (const s in o)
    (Re(o[s]) ||
      (t.style && Re(t.style[s])) ||
      qw(s, e) ||
      ((r = n == null ? void 0 : n.getValue(s)) === null || r === void 0 ? void 0 : r.liveStyle) !==
        void 0) &&
      (i[s] = o[s]);
  return i;
}
function Jw(e, t, n) {
  const r = Nh(e, t, n);
  for (const o in e)
    if (Re(e[o]) || Re(t[o])) {
      const i = Qo.indexOf(o) !== -1 ? "attr" + o.charAt(0).toUpperCase() + o.substring(1) : o;
      r[i] = e[o];
    }
  return r;
}
function oP(e, t) {
  try {
    t.dimensions = typeof e.getBBox == "function" ? e.getBBox() : e.getBoundingClientRect();
  } catch {
    t.dimensions = { x: 0, y: 0, width: 0, height: 0 };
  }
}
const Km = ["x", "y", "width", "height", "cx", "cy", "r"],
  iP = {
    useVisualState: Hw({
      scrapeMotionValuesFromProps: Jw,
      createRenderState: Yw,
      onUpdate: ({ props: e, prevProps: t, current: n, renderState: r, latestValues: o }) => {
        if (!n) return;
        let i = !!e.drag;
        if (!i) {
          for (const a in o)
            if (zr.has(a)) {
              i = !0;
              break;
            }
        }
        if (!i) return;
        let s = !t;
        if (t)
          for (let a = 0; a < Km.length; a++) {
            const l = Km[a];
            e[l] !== t[l] && (s = !0);
          }
        s &&
          ae.read(() => {
            oP(n, r),
              ae.render(() => {
                kh(r, o, Th(n.tagName), e.transformTemplate), Qw(n, r);
              });
          });
      },
    }),
  },
  sP = { useVisualState: Hw({ scrapeMotionValuesFromProps: Nh, createRenderState: _h }) };
function e1(e, t, n) {
  for (const r in t) !Re(t[r]) && !qw(r, n) && (e[r] = t[r]);
}
function aP({ transformTemplate: e }, t) {
  return v.useMemo(() => {
    const n = _h();
    return bh(n, t, e), Object.assign({}, n.vars, n.style);
  }, [t]);
}
function lP(e, t) {
  const n = e.style || {},
    r = {};
  return e1(r, n, e), Object.assign(r, aP(e, t)), r;
}
function uP(e, t) {
  const n = {},
    r = lP(e, t);
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
function cP(e, t, n, r) {
  const o = v.useMemo(() => {
    const i = Yw();
    return kh(i, t, Th(r), e.transformTemplate), { ...i.attrs, style: { ...i.style } };
  }, [t]);
  if (e.style) {
    const i = {};
    e1(i, e.style, e), (o.style = { ...i, ...o.style });
  }
  return o;
}
function fP(e = !1) {
  return (n, r, o, { latestValues: i }, s) => {
    const l = (wh(n) ? cP : uP)(r, i, s, n),
      u = _N(r, typeof n == "string", e),
      c = n !== v.Fragment ? { ...u, ...l, ref: o } : {},
      { children: f } = r,
      d = v.useMemo(() => (Re(f) ? f.get() : f), [f]);
    return v.createElement(n, { ...c, children: d });
  };
}
function dP(e, t) {
  return function (r, { forwardMotionProps: o } = { forwardMotionProps: !1 }) {
    const s = {
      ...(wh(r) ? iP : sP),
      preloadedFeatures: e,
      useRender: fP(o),
      createVisualElement: t,
      Component: r,
    };
    return LN(s);
  };
}
function t1(e, t) {
  if (!Array.isArray(t)) return !1;
  const n = t.length;
  if (n !== e.length) return !1;
  for (let r = 0; r < n; r++) if (t[r] !== e[r]) return !1;
  return !0;
}
function fu(e, t, n) {
  const r = e.getProps();
  return Sh(r, t, n !== void 0 ? n : r.custom, e);
}
const hP = mh(() => window.ScrollTimeline !== void 0);
class pP {
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
    const r = this.animations.map((o) => {
      if (hP() && o.attachTimeline) return o.attachTimeline(t);
      if (typeof n == "function") return n(o);
    });
    return () => {
      r.forEach((o, i) => {
        o && o(), this.animations[i].stop();
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
class mP extends pP {
  then(t, n) {
    return Promise.all(this.animations).then(t).catch(n);
  }
}
function Ph(e, t) {
  return e ? e[t] || e.default || e : void 0;
}
const Pf = 2e4;
function n1(e) {
  let t = 0;
  const n = 50;
  let r = e.next(t);
  for (; !r.done && t < Pf; ) (t += n), (r = e.next(t));
  return t >= Pf ? 1 / 0 : t;
}
function Mh(e) {
  return typeof e == "function";
}
function Ym(e, t) {
  (e.timeline = t), (e.onfinish = null);
}
const Ah = (e) => Array.isArray(e) && typeof e[0] == "number",
  gP = { linearEasing: void 0 };
function yP(e, t) {
  const n = mh(e);
  return () => {
    var r;
    return (r = gP[t]) !== null && r !== void 0 ? r : n();
  };
}
const El = yP(() => {
    try {
      document.createElement("div").animate({ opacity: 0 }, { easing: "linear(0, 1)" });
    } catch {
      return !1;
    }
    return !0;
  }, "linearEasing"),
  r1 = (e, t, n = 10) => {
    let r = "";
    const o = Math.max(Math.round(t / n), 2);
    for (let i = 0; i < o; i++) r += e($o(0, o - 1, i)) + ", ";
    return `linear(${r.substring(0, r.length - 2)})`;
  };
function o1(e) {
  return !!(
    (typeof e == "function" && El()) ||
    !e ||
    (typeof e == "string" && (e in Mf || El())) ||
    Ah(e) ||
    (Array.isArray(e) && e.every(o1))
  );
}
const bi = ([e, t, n, r]) => `cubic-bezier(${e}, ${t}, ${n}, ${r})`,
  Mf = {
    linear: "linear",
    ease: "ease",
    easeIn: "ease-in",
    easeOut: "ease-out",
    easeInOut: "ease-in-out",
    circIn: bi([0, 0.65, 0.55, 1]),
    circOut: bi([0.55, 0, 1, 0.45]),
    backIn: bi([0.31, 0.01, 0.66, -0.59]),
    backOut: bi([0.33, 1.53, 0.69, 0.99]),
  };
function i1(e, t) {
  if (e)
    return typeof e == "function" && El()
      ? r1(e, t)
      : Ah(e)
        ? bi(e)
        : Array.isArray(e)
          ? e.map((n) => i1(n, t) || Mf.easeOut)
          : Mf[e];
}
const At = { x: !1, y: !1 };
function s1() {
  return At.x || At.y;
}
function vP(e, t, n) {
  var r;
  if (e instanceof Element) return [e];
  if (typeof e == "string") {
    let o = document;
    const i = (r = void 0) !== null && r !== void 0 ? r : o.querySelectorAll(e);
    return i ? Array.from(i) : [];
  }
  return Array.from(e);
}
function a1(e, t) {
  const n = vP(e),
    r = new AbortController(),
    o = { passive: !0, ...t, signal: r.signal };
  return [n, o, () => r.abort()];
}
function Xm(e) {
  return (t) => {
    t.pointerType === "touch" || s1() || e(t);
  };
}
function xP(e, t, n = {}) {
  const [r, o, i] = a1(e, n),
    s = Xm((a) => {
      const { target: l } = a,
        u = t(a);
      if (typeof u != "function" || !l) return;
      const c = Xm((f) => {
        u(f), l.removeEventListener("pointerleave", c);
      });
      l.addEventListener("pointerleave", c, o);
    });
  return (
    r.forEach((a) => {
      a.addEventListener("pointerenter", s, o);
    }),
    i
  );
}
const l1 = (e, t) => (t ? (e === t ? !0 : l1(e, t.parentElement)) : !1),
  Rh = (e) =>
    e.pointerType === "mouse" ? typeof e.button != "number" || e.button <= 0 : e.isPrimary !== !1,
  wP = new Set(["BUTTON", "INPUT", "SELECT", "TEXTAREA", "A"]);
function SP(e) {
  return wP.has(e.tagName) || e.tabIndex !== -1;
}
const ki = new WeakSet();
function Zm(e) {
  return (t) => {
    t.key === "Enter" && e(t);
  };
}
function lc(e, t) {
  e.dispatchEvent(new PointerEvent("pointer" + t, { isPrimary: !0, bubbles: !0 }));
}
const EP = (e, t) => {
  const n = e.currentTarget;
  if (!n) return;
  const r = Zm(() => {
    if (ki.has(n)) return;
    lc(n, "down");
    const o = Zm(() => {
        lc(n, "up");
      }),
      i = () => lc(n, "cancel");
    n.addEventListener("keyup", o, t), n.addEventListener("blur", i, t);
  });
  n.addEventListener("keydown", r, t),
    n.addEventListener("blur", () => n.removeEventListener("keydown", r), t);
};
function Qm(e) {
  return Rh(e) && !s1();
}
function CP(e, t, n = {}) {
  const [r, o, i] = a1(e, n),
    s = (a) => {
      const l = a.currentTarget;
      if (!Qm(a) || ki.has(l)) return;
      ki.add(l);
      const u = t(a),
        c = (p, y) => {
          window.removeEventListener("pointerup", f),
            window.removeEventListener("pointercancel", d),
            !(!Qm(p) || !ki.has(l)) &&
              (ki.delete(l), typeof u == "function" && u(p, { success: y }));
        },
        f = (p) => {
          c(p, n.useGlobalTarget || l1(l, p.target));
        },
        d = (p) => {
          c(p, !1);
        };
      window.addEventListener("pointerup", f, o), window.addEventListener("pointercancel", d, o);
    };
  return (
    r.forEach((a) => {
      !SP(a) && a.getAttribute("tabindex") === null && (a.tabIndex = 0),
        (n.useGlobalTarget ? window : a).addEventListener("pointerdown", s, o),
        a.addEventListener("focus", (u) => EP(u, o), o);
    }),
    i
  );
}
function bP(e) {
  return e === "x" || e === "y"
    ? At[e]
      ? null
      : ((At[e] = !0),
        () => {
          At[e] = !1;
        })
    : At.x || At.y
      ? null
      : ((At.x = At.y = !0),
        () => {
          At.x = At.y = !1;
        });
}
const u1 = new Set(["width", "height", "top", "left", "right", "bottom", ...Qo]);
let Ba;
function kP() {
  Ba = void 0;
}
const Jt = {
  now: () => (
    Ba === void 0 &&
      Jt.set(Me.isProcessing || wN.useManualTiming ? Me.timestamp : performance.now()),
    Ba
  ),
  set: (e) => {
    (Ba = e), queueMicrotask(kP);
  },
};
function Dh(e, t) {
  e.indexOf(t) === -1 && e.push(t);
}
function Ih(e, t) {
  const n = e.indexOf(t);
  n > -1 && e.splice(n, 1);
}
class Lh {
  constructor() {
    this.subscriptions = [];
  }
  add(t) {
    return Dh(this.subscriptions, t), () => Ih(this.subscriptions, t);
  }
  notify(t, n, r) {
    const o = this.subscriptions.length;
    if (o)
      if (o === 1) this.subscriptions[0](t, n, r);
      else
        for (let i = 0; i < o; i++) {
          const s = this.subscriptions[i];
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
function c1(e, t) {
  return t ? e * (1e3 / t) : 0;
}
const qm = 30,
  _P = (e) => !isNaN(parseFloat(e)),
  $i = { current: void 0 };
class TP {
  constructor(t, n = {}) {
    (this.version = "11.18.2"),
      (this.canTrackVelocity = null),
      (this.events = {}),
      (this.updateAndNotify = (r, o = !0) => {
        const i = Jt.now();
        this.updatedAt !== i && this.setPrevFrameValue(),
          (this.prev = this.current),
          this.setCurrent(r),
          this.current !== this.prev &&
            this.events.change &&
            this.events.change.notify(this.current),
          o && this.events.renderRequest && this.events.renderRequest.notify(this.current);
      }),
      (this.hasAnimated = !1),
      this.setCurrent(t),
      (this.owner = n.owner);
  }
  setCurrent(t) {
    (this.current = t),
      (this.updatedAt = Jt.now()),
      this.canTrackVelocity === null && t !== void 0 && (this.canTrackVelocity = _P(this.current));
  }
  setPrevFrameValue(t = this.current) {
    (this.prevFrameValue = t), (this.prevUpdatedAt = this.updatedAt);
  }
  onChange(t) {
    return this.on("change", t);
  }
  on(t, n) {
    this.events[t] || (this.events[t] = new Lh());
    const r = this.events[t].add(n);
    return t === "change"
      ? () => {
          r(),
            ae.read(() => {
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
    return $i.current && $i.current.push(this), this.current;
  }
  getPrevious() {
    return this.prev;
  }
  getVelocity() {
    const t = Jt.now();
    if (!this.canTrackVelocity || this.prevFrameValue === void 0 || t - this.updatedAt > qm)
      return 0;
    const n = Math.min(this.updatedAt - this.prevUpdatedAt, qm);
    return c1(parseFloat(this.current) - parseFloat(this.prevFrameValue), n);
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
function Bo(e, t) {
  return new TP(e, t);
}
function NP(e, t, n) {
  e.hasValue(t) ? e.getValue(t).set(n) : e.addValue(t, Bo(n));
}
function PP(e, t) {
  const n = fu(e, t);
  let { transitionEnd: r = {}, transition: o = {}, ...i } = n || {};
  i = { ...i, ...r };
  for (const s in i) {
    const a = jN(i[s]);
    NP(e, s, a);
  }
}
function MP(e) {
  return !!(Re(e) && e.add);
}
function Af(e, t) {
  const n = e.getValue("willChange");
  if (MP(n)) return n.add(t);
}
function f1(e) {
  return e.props[jw];
}
const d1 = (e, t, n) => (((1 - 3 * n + 3 * t) * e + (3 * n - 6 * t)) * e + 3 * t) * e,
  AP = 1e-7,
  RP = 12;
function DP(e, t, n, r, o) {
  let i,
    s,
    a = 0;
  do (s = t + (n - t) / 2), (i = d1(s, r, o) - e), i > 0 ? (n = s) : (t = s);
  while (Math.abs(i) > AP && ++a < RP);
  return s;
}
function Os(e, t, n, r) {
  if (e === t && n === r) return dt;
  const o = (i) => DP(i, 0, 1, e, n);
  return (i) => (i === 0 || i === 1 ? i : d1(o(i), t, r));
}
const h1 = (e) => (t) => (t <= 0.5 ? e(2 * t) / 2 : (2 - e(2 * (1 - t))) / 2),
  p1 = (e) => (t) => 1 - e(1 - t),
  m1 = Os(0.33, 1.53, 0.69, 0.99),
  Vh = p1(m1),
  g1 = h1(Vh),
  y1 = (e) => ((e *= 2) < 1 ? 0.5 * Vh(e) : 0.5 * (2 - Math.pow(2, -10 * (e - 1)))),
  Oh = (e) => 1 - Math.sin(Math.acos(e)),
  v1 = p1(Oh),
  x1 = h1(Oh),
  w1 = (e) => /^0[^.\s]+$/u.test(e);
function IP(e) {
  return typeof e == "number" ? e === 0 : e !== null ? e === "none" || e === "0" || w1(e) : !0;
}
const ji = (e) => Math.round(e * 1e5) / 1e5,
  Fh = /-?(?:\d+(?:\.\d+)?|\.\d+)/gu;
function LP(e) {
  return e == null;
}
const VP =
    /^(?:#[\da-f]{3,8}|(?:rgb|hsl)a?\((?:-?[\d.]+%?[,\s]+){2}-?[\d.]+%?\s*(?:[,/]\s*)?(?:\b\d+(?:\.\d+)?|\.\d+)?%?\))$/iu,
  zh = (e, t) => (n) =>
    !!(
      (typeof n == "string" && VP.test(n) && n.startsWith(e)) ||
      (t && !LP(n) && Object.prototype.hasOwnProperty.call(n, t))
    ),
  S1 = (e, t, n) => (r) => {
    if (typeof r != "string") return r;
    const [o, i, s, a] = r.match(Fh);
    return {
      [e]: parseFloat(o),
      [t]: parseFloat(i),
      [n]: parseFloat(s),
      alpha: a !== void 0 ? parseFloat(a) : 1,
    };
  },
  OP = (e) => bn(0, 255, e),
  uc = { ...qo, transform: (e) => Math.round(OP(e)) },
  wr = {
    test: zh("rgb", "red"),
    parse: S1("red", "green", "blue"),
    transform: ({ red: e, green: t, blue: n, alpha: r = 1 }) =>
      "rgba(" +
      uc.transform(e) +
      ", " +
      uc.transform(t) +
      ", " +
      uc.transform(n) +
      ", " +
      ji(ds.transform(r)) +
      ")",
  };
function FP(e) {
  let t = "",
    n = "",
    r = "",
    o = "";
  return (
    e.length > 5
      ? ((t = e.substring(1, 3)),
        (n = e.substring(3, 5)),
        (r = e.substring(5, 7)),
        (o = e.substring(7, 9)))
      : ((t = e.substring(1, 2)),
        (n = e.substring(2, 3)),
        (r = e.substring(3, 4)),
        (o = e.substring(4, 5)),
        (t += t),
        (n += n),
        (r += r),
        (o += o)),
    {
      red: parseInt(t, 16),
      green: parseInt(n, 16),
      blue: parseInt(r, 16),
      alpha: o ? parseInt(o, 16) / 255 : 1,
    }
  );
}
const Rf = { test: zh("#"), parse: FP, transform: wr.transform },
  ho = {
    test: zh("hsl", "hue"),
    parse: S1("hue", "saturation", "lightness"),
    transform: ({ hue: e, saturation: t, lightness: n, alpha: r = 1 }) =>
      "hsla(" +
      Math.round(e) +
      ", " +
      qt.transform(ji(t)) +
      ", " +
      qt.transform(ji(n)) +
      ", " +
      ji(ds.transform(r)) +
      ")",
  },
  We = {
    test: (e) => wr.test(e) || Rf.test(e) || ho.test(e),
    parse: (e) => (wr.test(e) ? wr.parse(e) : ho.test(e) ? ho.parse(e) : Rf.parse(e)),
    transform: (e) =>
      typeof e == "string" ? e : e.hasOwnProperty("red") ? wr.transform(e) : ho.transform(e),
  },
  zP =
    /(?:#[\da-f]{3,8}|(?:rgb|hsl)a?\((?:-?[\d.]+%?[,\s]+){2}-?[\d.]+%?\s*(?:[,/]\s*)?(?:\b\d+(?:\.\d+)?|\.\d+)?%?\))/giu;
function $P(e) {
  var t, n;
  return (
    isNaN(e) &&
    typeof e == "string" &&
    (((t = e.match(Fh)) === null || t === void 0 ? void 0 : t.length) || 0) +
      (((n = e.match(zP)) === null || n === void 0 ? void 0 : n.length) || 0) >
      0
  );
}
const E1 = "number",
  C1 = "color",
  jP = "var",
  BP = "var(",
  Jm = "${}",
  UP =
    /var\s*\(\s*--(?:[\w-]+\s*|[\w-]+\s*,(?:\s*[^)(\s]|\s*\((?:[^)(]|\([^)(]*\))*\))+\s*)\)|#[\da-f]{3,8}|(?:rgb|hsl)a?\((?:-?[\d.]+%?[,\s]+){2}-?[\d.]+%?\s*(?:[,/]\s*)?(?:\b\d+(?:\.\d+)?|\.\d+)?%?\)|-?(?:\d+(?:\.\d+)?|\.\d+)/giu;
function hs(e) {
  const t = e.toString(),
    n = [],
    r = { color: [], number: [], var: [] },
    o = [];
  let i = 0;
  const a = t
    .replace(
      UP,
      (l) => (
        We.test(l)
          ? (r.color.push(i), o.push(C1), n.push(We.parse(l)))
          : l.startsWith(BP)
            ? (r.var.push(i), o.push(jP), n.push(l))
            : (r.number.push(i), o.push(E1), n.push(parseFloat(l))),
        ++i,
        Jm
      ),
    )
    .split(Jm);
  return { values: n, split: a, indexes: r, types: o };
}
function b1(e) {
  return hs(e).values;
}
function k1(e) {
  const { split: t, types: n } = hs(e),
    r = t.length;
  return (o) => {
    let i = "";
    for (let s = 0; s < r; s++)
      if (((i += t[s]), o[s] !== void 0)) {
        const a = n[s];
        a === E1 ? (i += ji(o[s])) : a === C1 ? (i += We.transform(o[s])) : (i += o[s]);
      }
    return i;
  };
}
const HP = (e) => (typeof e == "number" ? 0 : e);
function WP(e) {
  const t = b1(e);
  return k1(e)(t.map(HP));
}
const Jn = { test: $P, parse: b1, createTransformer: k1, getAnimatableNone: WP },
  GP = new Set(["brightness", "contrast", "saturate", "opacity"]);
function KP(e) {
  const [t, n] = e.slice(0, -1).split("(");
  if (t === "drop-shadow") return e;
  const [r] = n.match(Fh) || [];
  if (!r) return e;
  const o = n.replace(r, "");
  let i = GP.has(t) ? 1 : 0;
  return r !== n && (i *= 100), t + "(" + i + o + ")";
}
const YP = /\b([a-z-]*)\(.*?\)/gu,
  Df = {
    ...Jn,
    getAnimatableNone: (e) => {
      const t = e.match(YP);
      return t ? t.map(KP).join(" ") : e;
    },
  },
  XP = {
    ...Ch,
    color: We,
    backgroundColor: We,
    outlineColor: We,
    fill: We,
    stroke: We,
    borderColor: We,
    borderTopColor: We,
    borderRightColor: We,
    borderBottomColor: We,
    borderLeftColor: We,
    filter: Df,
    WebkitFilter: Df,
  },
  $h = (e) => XP[e];
function _1(e, t) {
  let n = $h(e);
  return n !== Df && (n = Jn), n.getAnimatableNone ? n.getAnimatableNone(t) : void 0;
}
const ZP = new Set(["auto", "none", "0"]);
function QP(e, t, n) {
  let r = 0,
    o;
  for (; r < e.length && !o; ) {
    const i = e[r];
    typeof i == "string" && !ZP.has(i) && hs(i).values.length && (o = e[r]), r++;
  }
  if (o && n) for (const i of t) e[i] = _1(n, o);
}
const eg = (e) => e === qo || e === X,
  tg = (e, t) => parseFloat(e.split(", ")[t]),
  ng =
    (e, t) =>
    (n, { transform: r }) => {
      if (r === "none" || !r) return 0;
      const o = r.match(/^matrix3d\((.+)\)$/u);
      if (o) return tg(o[1], t);
      {
        const i = r.match(/^matrix\((.+)\)$/u);
        return i ? tg(i[1], e) : 0;
      }
    },
  qP = new Set(["x", "y", "z"]),
  JP = Qo.filter((e) => !qP.has(e));
function eM(e) {
  const t = [];
  return (
    JP.forEach((n) => {
      const r = e.getValue(n);
      r !== void 0 && (t.push([n, r.get()]), r.set(n.startsWith("scale") ? 1 : 0));
    }),
    t
  );
}
const Uo = {
  width: ({ x: e }, { paddingLeft: t = "0", paddingRight: n = "0" }) =>
    e.max - e.min - parseFloat(t) - parseFloat(n),
  height: ({ y: e }, { paddingTop: t = "0", paddingBottom: n = "0" }) =>
    e.max - e.min - parseFloat(t) - parseFloat(n),
  top: (e, { top: t }) => parseFloat(t),
  left: (e, { left: t }) => parseFloat(t),
  bottom: ({ y: e }, { top: t }) => parseFloat(t) + (e.max - e.min),
  right: ({ x: e }, { left: t }) => parseFloat(t) + (e.max - e.min),
  x: ng(4, 13),
  y: ng(5, 14),
};
Uo.translateX = Uo.x;
Uo.translateY = Uo.y;
const _r = new Set();
let If = !1,
  Lf = !1;
function T1() {
  if (Lf) {
    const e = Array.from(_r).filter((r) => r.needsMeasurement),
      t = new Set(e.map((r) => r.element)),
      n = new Map();
    t.forEach((r) => {
      const o = eM(r);
      o.length && (n.set(r, o), r.render());
    }),
      e.forEach((r) => r.measureInitialState()),
      t.forEach((r) => {
        r.render();
        const o = n.get(r);
        o &&
          o.forEach(([i, s]) => {
            var a;
            (a = r.getValue(i)) === null || a === void 0 || a.set(s);
          });
      }),
      e.forEach((r) => r.measureEndState()),
      e.forEach((r) => {
        r.suspendedScrollY !== void 0 && window.scrollTo(0, r.suspendedScrollY);
      });
  }
  (Lf = !1), (If = !1), _r.forEach((e) => e.complete()), _r.clear();
}
function N1() {
  _r.forEach((e) => {
    e.readKeyframes(), e.needsMeasurement && (Lf = !0);
  });
}
function tM() {
  N1(), T1();
}
class jh {
  constructor(t, n, r, o, i, s = !1) {
    (this.isComplete = !1),
      (this.isAsync = !1),
      (this.needsMeasurement = !1),
      (this.isScheduled = !1),
      (this.unresolvedKeyframes = [...t]),
      (this.onComplete = n),
      (this.name = r),
      (this.motionValue = o),
      (this.element = i),
      (this.isAsync = s);
  }
  scheduleResolve() {
    (this.isScheduled = !0),
      this.isAsync
        ? (_r.add(this), If || ((If = !0), ae.read(N1), ae.resolveKeyframes(T1)))
        : (this.readKeyframes(), this.complete());
  }
  readKeyframes() {
    const { unresolvedKeyframes: t, name: n, element: r, motionValue: o } = this;
    for (let i = 0; i < t.length; i++)
      if (t[i] === null)
        if (i === 0) {
          const s = o == null ? void 0 : o.get(),
            a = t[t.length - 1];
          if (s !== void 0) t[0] = s;
          else if (r && n) {
            const l = r.readValue(n, a);
            l != null && (t[0] = l);
          }
          t[0] === void 0 && (t[0] = a), o && s === void 0 && o.set(t[0]);
        } else t[i] = t[i - 1];
  }
  setFinalKeyframe() {}
  measureInitialState() {}
  renderEndStyles() {}
  measureEndState() {}
  complete() {
    (this.isComplete = !0),
      this.onComplete(this.unresolvedKeyframes, this.finalKeyframe),
      _r.delete(this);
  }
  cancel() {
    this.isComplete || ((this.isScheduled = !1), _r.delete(this));
  }
  resume() {
    this.isComplete || this.scheduleResolve();
  }
}
const P1 = (e) => /^-?(?:\d+(?:\.\d+)?|\.\d+)$/u.test(e),
  nM = /^var\(--(?:([\w-]+)|([\w-]+), ?([a-zA-Z\d ()%#.,-]+))\)/u;
function rM(e) {
  const t = nM.exec(e);
  if (!t) return [,];
  const [, n, r, o] = t;
  return [`--${n ?? r}`, o];
}
function M1(e, t, n = 1) {
  const [r, o] = rM(e);
  if (!r) return;
  const i = window.getComputedStyle(t).getPropertyValue(r);
  if (i) {
    const s = i.trim();
    return P1(s) ? parseFloat(s) : s;
  }
  return Eh(o) ? M1(o, t, n + 1) : o;
}
const A1 = (e) => (t) => t.test(e),
  oM = { test: (e) => e === "auto", parse: (e) => e },
  R1 = [qo, X, qt, Dn, KN, GN, oM],
  rg = (e) => R1.find(A1(e));
class D1 extends jh {
  constructor(t, n, r, o, i) {
    super(t, n, r, o, i, !0);
  }
  readKeyframes() {
    const { unresolvedKeyframes: t, element: n, name: r } = this;
    if (!n || !n.current) return;
    super.readKeyframes();
    for (let l = 0; l < t.length; l++) {
      let u = t[l];
      if (typeof u == "string" && ((u = u.trim()), Eh(u))) {
        const c = M1(u, n.current);
        c !== void 0 && (t[l] = c), l === t.length - 1 && (this.finalKeyframe = u);
      }
    }
    if ((this.resolveNoneKeyframes(), !u1.has(r) || t.length !== 2)) return;
    const [o, i] = t,
      s = rg(o),
      a = rg(i);
    if (s !== a)
      if (eg(s) && eg(a))
        for (let l = 0; l < t.length; l++) {
          const u = t[l];
          typeof u == "string" && (t[l] = parseFloat(u));
        }
      else this.needsMeasurement = !0;
  }
  resolveNoneKeyframes() {
    const { unresolvedKeyframes: t, name: n } = this,
      r = [];
    for (let o = 0; o < t.length; o++) IP(t[o]) && r.push(o);
    r.length && QP(t, r, n);
  }
  measureInitialState() {
    const { element: t, unresolvedKeyframes: n, name: r } = this;
    if (!t || !t.current) return;
    r === "height" && (this.suspendedScrollY = window.pageYOffset),
      (this.measuredOrigin = Uo[r](t.measureViewportBox(), window.getComputedStyle(t.current))),
      (n[0] = this.measuredOrigin);
    const o = n[n.length - 1];
    o !== void 0 && t.getValue(r, o).jump(o, !1);
  }
  measureEndState() {
    var t;
    const { element: n, name: r, unresolvedKeyframes: o } = this;
    if (!n || !n.current) return;
    const i = n.getValue(r);
    i && i.jump(this.measuredOrigin, !1);
    const s = o.length - 1,
      a = o[s];
    (o[s] = Uo[r](n.measureViewportBox(), window.getComputedStyle(n.current))),
      a !== null && this.finalKeyframe === void 0 && (this.finalKeyframe = a),
      !((t = this.removedTransforms) === null || t === void 0) &&
        t.length &&
        this.removedTransforms.forEach(([l, u]) => {
          n.getValue(l).set(u);
        }),
      this.resolveNoneKeyframes();
  }
}
const og = (e, t) =>
  t === "zIndex"
    ? !1
    : !!(
        typeof e == "number" ||
        Array.isArray(e) ||
        (typeof e == "string" && (Jn.test(e) || e === "0") && !e.startsWith("url("))
      );
function iM(e) {
  const t = e[0];
  if (e.length === 1) return !0;
  for (let n = 0; n < e.length; n++) if (e[n] !== t) return !0;
}
function sM(e, t, n, r) {
  const o = e[0];
  if (o === null) return !1;
  if (t === "display" || t === "visibility") return !0;
  const i = e[e.length - 1],
    s = og(o, t),
    a = og(i, t);
  return !s || !a ? !1 : iM(e) || ((n === "spring" || Mh(n)) && r);
}
const aM = (e) => e !== null;
function du(e, { repeat: t, repeatType: n = "loop" }, r) {
  const o = e.filter(aM),
    i = t && n !== "loop" && t % 2 === 1 ? 0 : o.length - 1;
  return !i || r === void 0 ? o[i] : r;
}
const lM = 40;
class I1 {
  constructor({
    autoplay: t = !0,
    delay: n = 0,
    type: r = "keyframes",
    repeat: o = 0,
    repeatDelay: i = 0,
    repeatType: s = "loop",
    ...a
  }) {
    (this.isStopped = !1),
      (this.hasAttemptedResolve = !1),
      (this.createdAt = Jt.now()),
      (this.options = {
        autoplay: t,
        delay: n,
        type: r,
        repeat: o,
        repeatDelay: i,
        repeatType: s,
        ...a,
      }),
      this.updateFinishedPromise();
  }
  calcStartTime() {
    return this.resolvedAt
      ? this.resolvedAt - this.createdAt > lM
        ? this.resolvedAt
        : this.createdAt
      : this.createdAt;
  }
  get resolved() {
    return !this._resolved && !this.hasAttemptedResolve && tM(), this._resolved;
  }
  onKeyframesResolved(t, n) {
    (this.resolvedAt = Jt.now()), (this.hasAttemptedResolve = !0);
    const {
      name: r,
      type: o,
      velocity: i,
      delay: s,
      onComplete: a,
      onUpdate: l,
      isGenerator: u,
    } = this.options;
    if (!u && !sM(t, r, o, i))
      if (s) this.options.duration = 0;
      else {
        l && l(du(t, this.options, n)), a && a(), this.resolveFinishedPromise();
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
const ge = (e, t, n) => e + (t - e) * n;
function cc(e, t, n) {
  return (
    n < 0 && (n += 1),
    n > 1 && (n -= 1),
    n < 1 / 6 ? e + (t - e) * 6 * n : n < 1 / 2 ? t : n < 2 / 3 ? e + (t - e) * (2 / 3 - n) * 6 : e
  );
}
function uM({ hue: e, saturation: t, lightness: n, alpha: r }) {
  (e /= 360), (t /= 100), (n /= 100);
  let o = 0,
    i = 0,
    s = 0;
  if (!t) o = i = s = n;
  else {
    const a = n < 0.5 ? n * (1 + t) : n + t - n * t,
      l = 2 * n - a;
    (o = cc(l, a, e + 1 / 3)), (i = cc(l, a, e)), (s = cc(l, a, e - 1 / 3));
  }
  return {
    red: Math.round(o * 255),
    green: Math.round(i * 255),
    blue: Math.round(s * 255),
    alpha: r,
  };
}
function Cl(e, t) {
  return (n) => (n > 0 ? t : e);
}
const fc = (e, t, n) => {
    const r = e * e,
      o = n * (t * t - r) + r;
    return o < 0 ? 0 : Math.sqrt(o);
  },
  cM = [Rf, wr, ho],
  fM = (e) => cM.find((t) => t.test(e));
function ig(e) {
  const t = fM(e);
  if (!t) return !1;
  let n = t.parse(e);
  return t === ho && (n = uM(n)), n;
}
const sg = (e, t) => {
    const n = ig(e),
      r = ig(t);
    if (!n || !r) return Cl(e, t);
    const o = { ...n };
    return (i) => (
      (o.red = fc(n.red, r.red, i)),
      (o.green = fc(n.green, r.green, i)),
      (o.blue = fc(n.blue, r.blue, i)),
      (o.alpha = ge(n.alpha, r.alpha, i)),
      wr.transform(o)
    );
  },
  dM = (e, t) => (n) => t(e(n)),
  Fs = (...e) => e.reduce(dM),
  Vf = new Set(["none", "hidden"]);
function hM(e, t) {
  return Vf.has(e) ? (n) => (n <= 0 ? e : t) : (n) => (n >= 1 ? t : e);
}
function pM(e, t) {
  return (n) => ge(e, t, n);
}
function Bh(e) {
  return typeof e == "number"
    ? pM
    : typeof e == "string"
      ? Eh(e)
        ? Cl
        : We.test(e)
          ? sg
          : yM
      : Array.isArray(e)
        ? L1
        : typeof e == "object"
          ? We.test(e)
            ? sg
            : mM
          : Cl;
}
function L1(e, t) {
  const n = [...e],
    r = n.length,
    o = e.map((i, s) => Bh(i)(i, t[s]));
  return (i) => {
    for (let s = 0; s < r; s++) n[s] = o[s](i);
    return n;
  };
}
function mM(e, t) {
  const n = { ...e, ...t },
    r = {};
  for (const o in n) e[o] !== void 0 && t[o] !== void 0 && (r[o] = Bh(e[o])(e[o], t[o]));
  return (o) => {
    for (const i in r) n[i] = r[i](o);
    return n;
  };
}
function gM(e, t) {
  var n;
  const r = [],
    o = { color: 0, var: 0, number: 0 };
  for (let i = 0; i < t.values.length; i++) {
    const s = t.types[i],
      a = e.indexes[s][o[s]],
      l = (n = e.values[a]) !== null && n !== void 0 ? n : 0;
    (r[i] = l), o[s]++;
  }
  return r;
}
const yM = (e, t) => {
  const n = Jn.createTransformer(t),
    r = hs(e),
    o = hs(t);
  return r.indexes.var.length === o.indexes.var.length &&
    r.indexes.color.length === o.indexes.color.length &&
    r.indexes.number.length >= o.indexes.number.length
    ? (Vf.has(e) && !o.values.length) || (Vf.has(t) && !r.values.length)
      ? hM(e, t)
      : Fs(L1(gM(r, o), o.values), n)
    : Cl(e, t);
};
function V1(e, t, n) {
  return typeof e == "number" && typeof t == "number" && typeof n == "number"
    ? ge(e, t, n)
    : Bh(e)(e, t);
}
const vM = 5;
function O1(e, t, n) {
  const r = Math.max(t - vM, 0);
  return c1(n - e(r), t - r);
}
const xe = {
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
  dc = 0.001;
function xM({
  duration: e = xe.duration,
  bounce: t = xe.bounce,
  velocity: n = xe.velocity,
  mass: r = xe.mass,
}) {
  let o,
    i,
    s = 1 - t;
  (s = bn(xe.minDamping, xe.maxDamping, s)),
    (e = bn(xe.minDuration, xe.maxDuration, yn(e))),
    s < 1
      ? ((o = (u) => {
          const c = u * s,
            f = c * e,
            d = c - n,
            p = Of(u, s),
            y = Math.exp(-f);
          return dc - (d / p) * y;
        }),
        (i = (u) => {
          const f = u * s * e,
            d = f * n + n,
            p = Math.pow(s, 2) * Math.pow(u, 2) * e,
            y = Math.exp(-f),
            m = Of(Math.pow(u, 2), s);
          return ((-o(u) + dc > 0 ? -1 : 1) * ((d - p) * y)) / m;
        }))
      : ((o = (u) => {
          const c = Math.exp(-u * e),
            f = (u - n) * e + 1;
          return -dc + c * f;
        }),
        (i = (u) => {
          const c = Math.exp(-u * e),
            f = (n - u) * (e * e);
          return c * f;
        }));
  const a = 5 / e,
    l = SM(o, i, a);
  if (((e = gn(e)), isNaN(l))) return { stiffness: xe.stiffness, damping: xe.damping, duration: e };
  {
    const u = Math.pow(l, 2) * r;
    return { stiffness: u, damping: s * 2 * Math.sqrt(r * u), duration: e };
  }
}
const wM = 12;
function SM(e, t, n) {
  let r = n;
  for (let o = 1; o < wM; o++) r = r - e(r) / t(r);
  return r;
}
function Of(e, t) {
  return e * Math.sqrt(1 - t * t);
}
const EM = ["duration", "bounce"],
  CM = ["stiffness", "damping", "mass"];
function ag(e, t) {
  return t.some((n) => e[n] !== void 0);
}
function bM(e) {
  let t = {
    velocity: xe.velocity,
    stiffness: xe.stiffness,
    damping: xe.damping,
    mass: xe.mass,
    isResolvedFromDuration: !1,
    ...e,
  };
  if (!ag(e, CM) && ag(e, EM))
    if (e.visualDuration) {
      const n = e.visualDuration,
        r = (2 * Math.PI) / (n * 1.2),
        o = r * r,
        i = 2 * bn(0.05, 1, 1 - (e.bounce || 0)) * Math.sqrt(o);
      t = { ...t, mass: xe.mass, stiffness: o, damping: i };
    } else {
      const n = xM(e);
      (t = { ...t, ...n, mass: xe.mass }), (t.isResolvedFromDuration = !0);
    }
  return t;
}
function F1(e = xe.visualDuration, t = xe.bounce) {
  const n = typeof e != "object" ? { visualDuration: e, keyframes: [0, 1], bounce: t } : e;
  let { restSpeed: r, restDelta: o } = n;
  const i = n.keyframes[0],
    s = n.keyframes[n.keyframes.length - 1],
    a = { done: !1, value: i },
    {
      stiffness: l,
      damping: u,
      mass: c,
      duration: f,
      velocity: d,
      isResolvedFromDuration: p,
    } = bM({ ...n, velocity: -yn(n.velocity || 0) }),
    y = d || 0,
    m = u / (2 * Math.sqrt(l * c)),
    w = s - i,
    h = yn(Math.sqrt(l / c)),
    g = Math.abs(w) < 5;
  r || (r = g ? xe.restSpeed.granular : xe.restSpeed.default),
    o || (o = g ? xe.restDelta.granular : xe.restDelta.default);
  let x;
  if (m < 1) {
    const E = Of(h, m);
    x = (C) => {
      const b = Math.exp(-m * h * C);
      return s - b * (((y + m * h * w) / E) * Math.sin(E * C) + w * Math.cos(E * C));
    };
  } else if (m === 1) x = (E) => s - Math.exp(-h * E) * (w + (y + h * w) * E);
  else {
    const E = h * Math.sqrt(m * m - 1);
    x = (C) => {
      const b = Math.exp(-m * h * C),
        _ = Math.min(E * C, 300);
      return s - (b * ((y + m * h * w) * Math.sinh(_) + E * w * Math.cosh(_))) / E;
    };
  }
  const S = {
    calculatedDuration: (p && f) || null,
    next: (E) => {
      const C = x(E);
      if (p) a.done = E >= f;
      else {
        let b = 0;
        m < 1 && (b = E === 0 ? gn(y) : O1(x, E, C));
        const _ = Math.abs(b) <= r,
          A = Math.abs(s - C) <= o;
        a.done = _ && A;
      }
      return (a.value = a.done ? s : C), a;
    },
    toString: () => {
      const E = Math.min(n1(S), Pf),
        C = r1((b) => S.next(E * b).value, E, 30);
      return E + "ms " + C;
    },
  };
  return S;
}
function lg({
  keyframes: e,
  velocity: t = 0,
  power: n = 0.8,
  timeConstant: r = 325,
  bounceDamping: o = 10,
  bounceStiffness: i = 500,
  modifyTarget: s,
  min: a,
  max: l,
  restDelta: u = 0.5,
  restSpeed: c,
}) {
  const f = e[0],
    d = { done: !1, value: f },
    p = (_) => (a !== void 0 && _ < a) || (l !== void 0 && _ > l),
    y = (_) => (a === void 0 ? l : l === void 0 || Math.abs(a - _) < Math.abs(l - _) ? a : l);
  let m = n * t;
  const w = f + m,
    h = s === void 0 ? w : s(w);
  h !== w && (m = h - f);
  const g = (_) => -m * Math.exp(-_ / r),
    x = (_) => h + g(_),
    S = (_) => {
      const A = g(_),
        R = x(_);
      (d.done = Math.abs(A) <= u), (d.value = d.done ? h : R);
    };
  let E, C;
  const b = (_) => {
    p(d.value) &&
      ((E = _),
      (C = F1({
        keyframes: [d.value, y(d.value)],
        velocity: O1(x, _, d.value),
        damping: o,
        stiffness: i,
        restDelta: u,
        restSpeed: c,
      })));
  };
  return (
    b(0),
    {
      calculatedDuration: null,
      next: (_) => {
        let A = !1;
        return (
          !C && E === void 0 && ((A = !0), S(_), b(_)),
          E !== void 0 && _ >= E ? C.next(_ - E) : (!A && S(_), d)
        );
      },
    }
  );
}
const kM = Os(0.42, 0, 1, 1),
  _M = Os(0, 0, 0.58, 1),
  z1 = Os(0.42, 0, 0.58, 1),
  TM = (e) => Array.isArray(e) && typeof e[0] != "number",
  NM = {
    linear: dt,
    easeIn: kM,
    easeInOut: z1,
    easeOut: _M,
    circIn: Oh,
    circInOut: x1,
    circOut: v1,
    backIn: Vh,
    backInOut: g1,
    backOut: m1,
    anticipate: y1,
  },
  ug = (e) => {
    if (Ah(e)) {
      Vw(e.length === 4);
      const [t, n, r, o] = e;
      return Os(t, n, r, o);
    } else if (typeof e == "string") return NM[e];
    return e;
  };
function PM(e, t, n) {
  const r = [],
    o = n || V1,
    i = e.length - 1;
  for (let s = 0; s < i; s++) {
    let a = o(e[s], e[s + 1]);
    if (t) {
      const l = Array.isArray(t) ? t[s] || dt : t;
      a = Fs(l, a);
    }
    r.push(a);
  }
  return r;
}
function $1(e, t, { clamp: n = !0, ease: r, mixer: o } = {}) {
  const i = e.length;
  if ((Vw(i === t.length), i === 1)) return () => t[0];
  if (i === 2 && t[0] === t[1]) return () => t[1];
  const s = e[0] === e[1];
  e[0] > e[i - 1] && ((e = [...e].reverse()), (t = [...t].reverse()));
  const a = PM(t, r, o),
    l = a.length,
    u = (c) => {
      if (s && c < e[0]) return t[0];
      let f = 0;
      if (l > 1) for (; f < e.length - 2 && !(c < e[f + 1]); f++);
      const d = $o(e[f], e[f + 1], c);
      return a[f](d);
    };
  return n ? (c) => u(bn(e[0], e[i - 1], c)) : u;
}
function MM(e, t) {
  const n = e[e.length - 1];
  for (let r = 1; r <= t; r++) {
    const o = $o(0, t, r);
    e.push(ge(n, 1, o));
  }
}
function AM(e) {
  const t = [0];
  return MM(t, e.length - 1), t;
}
function RM(e, t) {
  return e.map((n) => n * t);
}
function DM(e, t) {
  return e.map(() => t || z1).splice(0, e.length - 1);
}
function bl({ duration: e = 300, keyframes: t, times: n, ease: r = "easeInOut" }) {
  const o = TM(r) ? r.map(ug) : ug(r),
    i = { done: !1, value: t[0] },
    s = RM(n && n.length === t.length ? n : AM(t), e),
    a = $1(s, t, { ease: Array.isArray(o) ? o : DM(t, o) });
  return { calculatedDuration: e, next: (l) => ((i.value = a(l)), (i.done = l >= e), i) };
}
const IM = (e) => {
    const t = ({ timestamp: n }) => e(n);
    return {
      start: () => ae.update(t, !0),
      stop: () => Cn(t),
      now: () => (Me.isProcessing ? Me.timestamp : Jt.now()),
    };
  },
  LM = { decay: lg, inertia: lg, tween: bl, keyframes: bl, spring: F1 },
  VM = (e) => e / 100;
class hu extends I1 {
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
        const { onStop: l } = this.options;
        l && l();
      });
    const { name: n, motionValue: r, element: o, keyframes: i } = this.options,
      s = (o == null ? void 0 : o.KeyframeResolver) || jh,
      a = (l, u) => this.onKeyframesResolved(l, u);
    (this.resolver = new s(i, a, n, r, o)), this.resolver.scheduleResolve();
  }
  flatten() {
    super.flatten(),
      this._resolved && Object.assign(this._resolved, this.initPlayback(this._resolved.keyframes));
  }
  initPlayback(t) {
    const {
        type: n = "keyframes",
        repeat: r = 0,
        repeatDelay: o = 0,
        repeatType: i,
        velocity: s = 0,
      } = this.options,
      a = Mh(n) ? n : LM[n] || bl;
    let l, u;
    a !== bl && typeof t[0] != "number" && ((l = Fs(VM, V1(t[0], t[1]))), (t = [0, 100]));
    const c = a({ ...this.options, keyframes: t });
    i === "mirror" && (u = a({ ...this.options, keyframes: [...t].reverse(), velocity: -s })),
      c.calculatedDuration === null && (c.calculatedDuration = n1(c));
    const { calculatedDuration: f } = c,
      d = f + o,
      p = d * (r + 1) - o;
    return {
      generator: c,
      mirroredGenerator: u,
      mapPercentToKeyframes: l,
      calculatedDuration: f,
      resolvedDuration: d,
      totalDuration: p,
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
      const { keyframes: _ } = this.options;
      return { done: !0, value: _[_.length - 1] };
    }
    const {
      finalKeyframe: o,
      generator: i,
      mirroredGenerator: s,
      mapPercentToKeyframes: a,
      keyframes: l,
      calculatedDuration: u,
      totalDuration: c,
      resolvedDuration: f,
    } = r;
    if (this.startTime === null) return i.next(0);
    const { delay: d, repeat: p, repeatType: y, repeatDelay: m, onUpdate: w } = this.options;
    this.speed > 0
      ? (this.startTime = Math.min(this.startTime, t))
      : this.speed < 0 && (this.startTime = Math.min(t - c / this.speed, this.startTime)),
      n
        ? (this.currentTime = t)
        : this.holdTime !== null
          ? (this.currentTime = this.holdTime)
          : (this.currentTime = Math.round(t - this.startTime) * this.speed);
    const h = this.currentTime - d * (this.speed >= 0 ? 1 : -1),
      g = this.speed >= 0 ? h < 0 : h > c;
    (this.currentTime = Math.max(h, 0)),
      this.state === "finished" && this.holdTime === null && (this.currentTime = c);
    let x = this.currentTime,
      S = i;
    if (p) {
      const _ = Math.min(this.currentTime, c) / f;
      let A = Math.floor(_),
        R = _ % 1;
      !R && _ >= 1 && (R = 1),
        R === 1 && A--,
        (A = Math.min(A, p + 1)),
        !!(A % 2) &&
          (y === "reverse" ? ((R = 1 - R), m && (R -= m / f)) : y === "mirror" && (S = s)),
        (x = bn(0, 1, R) * f);
    }
    const E = g ? { done: !1, value: l[0] } : S.next(x);
    a && (E.value = a(E.value));
    let { done: C } = E;
    !g && u !== null && (C = this.speed >= 0 ? this.currentTime >= c : this.currentTime <= 0);
    const b =
      this.holdTime === null && (this.state === "finished" || (this.state === "running" && C));
    return (
      b && o !== void 0 && (E.value = du(l, this.options, o)),
      w && w(E.value),
      b && this.finish(),
      E
    );
  }
  get duration() {
    const { resolved: t } = this;
    return t ? yn(t.calculatedDuration) : 0;
  }
  get time() {
    return yn(this.currentTime);
  }
  set time(t) {
    (t = gn(t)),
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
    (this.playbackSpeed = t), n && (this.time = yn(this.currentTime));
  }
  play() {
    if ((this.resolver.isScheduled || this.resolver.resume(), !this._resolved)) {
      this.pendingPlayState = "running";
      return;
    }
    if (this.isStopped) return;
    const { driver: t = IM, onPlay: n, startTime: r } = this.options;
    this.driver || (this.driver = t((i) => this.tick(i))), n && n();
    const o = this.driver.now();
    this.holdTime !== null
      ? (this.startTime = o - this.holdTime)
      : this.startTime
        ? this.state === "finished" && (this.startTime = o)
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
function OM(e) {
  return new hu(e);
}
const FM = new Set(["opacity", "clipPath", "filter", "transform"]);
function zM(
  e,
  t,
  n,
  {
    delay: r = 0,
    duration: o = 300,
    repeat: i = 0,
    repeatType: s = "loop",
    ease: a = "easeInOut",
    times: l,
  } = {},
) {
  const u = { [t]: n };
  l && (u.offset = l);
  const c = i1(a, o);
  return (
    Array.isArray(c) && (u.easing = c),
    e.animate(u, {
      delay: r,
      duration: o,
      easing: Array.isArray(c) ? "linear" : c,
      fill: "both",
      iterations: i + 1,
      direction: s === "reverse" ? "alternate" : "normal",
    })
  );
}
const $M = mh(() => Object.hasOwnProperty.call(Element.prototype, "animate")),
  kl = 10,
  jM = 2e4;
function BM(e) {
  return Mh(e.type) || e.type === "spring" || !o1(e.ease);
}
function UM(e, t) {
  const n = new hu({ ...t, keyframes: e, repeat: 0, delay: 0, isGenerator: !0 });
  let r = { done: !1, value: e[0] };
  const o = [];
  let i = 0;
  for (; !r.done && i < jM; ) (r = n.sample(i)), o.push(r.value), (i += kl);
  return { times: void 0, keyframes: o, duration: i - kl, ease: "linear" };
}
const j1 = { anticipate: y1, backInOut: g1, circInOut: x1 };
function HM(e) {
  return e in j1;
}
class cg extends I1 {
  constructor(t) {
    super(t);
    const { name: n, motionValue: r, element: o, keyframes: i } = this.options;
    (this.resolver = new D1(i, (s, a) => this.onKeyframesResolved(s, a), n, r, o)),
      this.resolver.scheduleResolve();
  }
  initPlayback(t, n) {
    let {
      duration: r = 300,
      times: o,
      ease: i,
      type: s,
      motionValue: a,
      name: l,
      startTime: u,
    } = this.options;
    if (!a.owner || !a.owner.current) return !1;
    if ((typeof i == "string" && El() && HM(i) && (i = j1[i]), BM(this.options))) {
      const { onComplete: f, onUpdate: d, motionValue: p, element: y, ...m } = this.options,
        w = UM(t, m);
      (t = w.keyframes),
        t.length === 1 && (t[1] = t[0]),
        (r = w.duration),
        (o = w.times),
        (i = w.ease),
        (s = "keyframes");
    }
    const c = zM(a.owner.current, l, t, { ...this.options, duration: r, times: o, ease: i });
    return (
      (c.startTime = u ?? this.calcStartTime()),
      this.pendingTimeline
        ? (Ym(c, this.pendingTimeline), (this.pendingTimeline = void 0))
        : (c.onfinish = () => {
            const { onComplete: f } = this.options;
            a.set(du(t, this.options, n)), f && f(), this.cancel(), this.resolveFinishedPromise();
          }),
      { animation: c, duration: r, times: o, type: s, ease: i, keyframes: t }
    );
  }
  get duration() {
    const { resolved: t } = this;
    if (!t) return 0;
    const { duration: n } = t;
    return yn(n);
  }
  get time() {
    const { resolved: t } = this;
    if (!t) return 0;
    const { animation: n } = t;
    return yn(n.currentTime || 0);
  }
  set time(t) {
    const { resolved: n } = this;
    if (!n) return;
    const { animation: r } = n;
    r.currentTime = gn(t);
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
      if (!n) return dt;
      const { animation: r } = n;
      Ym(r, t);
    }
    return dt;
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
    const { animation: n, keyframes: r, duration: o, type: i, ease: s, times: a } = t;
    if (n.playState === "idle" || n.playState === "finished") return;
    if (this.time) {
      const { motionValue: u, onUpdate: c, onComplete: f, element: d, ...p } = this.options,
        y = new hu({
          ...p,
          keyframes: r,
          duration: o,
          type: i,
          ease: s,
          times: a,
          isGenerator: !0,
        }),
        m = gn(this.time);
      u.setWithVelocity(y.sample(m - kl).value, y.sample(m).value, kl);
    }
    const { onStop: l } = this.options;
    l && l(), this.cancel();
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
    const { motionValue: n, name: r, repeatDelay: o, repeatType: i, damping: s, type: a } = t;
    if (!n || !n.owner || !(n.owner.current instanceof HTMLElement)) return !1;
    const { onUpdate: l, transformTemplate: u } = n.owner.getProps();
    return $M() && r && FM.has(r) && !l && !u && !o && i !== "mirror" && s !== 0 && a !== "inertia";
  }
}
const WM = { type: "spring", stiffness: 500, damping: 25, restSpeed: 10 },
  GM = (e) => ({
    type: "spring",
    stiffness: 550,
    damping: e === 0 ? 2 * Math.sqrt(550) : 30,
    restSpeed: 10,
  }),
  KM = { type: "keyframes", duration: 0.8 },
  YM = { type: "keyframes", ease: [0.25, 0.1, 0.35, 1], duration: 0.3 },
  XM = (e, { keyframes: t }) =>
    t.length > 2 ? KM : zr.has(e) ? (e.startsWith("scale") ? GM(t[1]) : WM) : YM;
function ZM({
  when: e,
  delay: t,
  delayChildren: n,
  staggerChildren: r,
  staggerDirection: o,
  repeat: i,
  repeatType: s,
  repeatDelay: a,
  from: l,
  elapsed: u,
  ...c
}) {
  return !!Object.keys(c).length;
}
const Uh =
  (e, t, n, r = {}, o, i) =>
  (s) => {
    const a = Ph(r, e) || {},
      l = a.delay || r.delay || 0;
    let { elapsed: u = 0 } = r;
    u = u - gn(l);
    let c = {
      keyframes: Array.isArray(n) ? n : [null, n],
      ease: "easeOut",
      velocity: t.getVelocity(),
      ...a,
      delay: -u,
      onUpdate: (d) => {
        t.set(d), a.onUpdate && a.onUpdate(d);
      },
      onComplete: () => {
        s(), a.onComplete && a.onComplete();
      },
      name: e,
      motionValue: t,
      element: i ? void 0 : o,
    };
    ZM(a) || (c = { ...c, ...XM(e, c) }),
      c.duration && (c.duration = gn(c.duration)),
      c.repeatDelay && (c.repeatDelay = gn(c.repeatDelay)),
      c.from !== void 0 && (c.keyframes[0] = c.from);
    let f = !1;
    if (
      ((c.type === !1 || (c.duration === 0 && !c.repeatDelay)) &&
        ((c.duration = 0), c.delay === 0 && (f = !0)),
      f && !i && t.get() !== void 0)
    ) {
      const d = du(c.keyframes, a);
      if (d !== void 0)
        return (
          ae.update(() => {
            c.onUpdate(d), c.onComplete();
          }),
          new mP([])
        );
    }
    return !i && cg.supports(c) ? new cg(c) : new hu(c);
  };
function QM({ protectedKeys: e, needsAnimating: t }, n) {
  const r = e.hasOwnProperty(n) && t[n] !== !0;
  return (t[n] = !1), r;
}
function B1(e, t, { delay: n = 0, transitionOverride: r, type: o } = {}) {
  var i;
  let { transition: s = e.getDefaultTransition(), transitionEnd: a, ...l } = t;
  r && (s = r);
  const u = [],
    c = o && e.animationState && e.animationState.getState()[o];
  for (const f in l) {
    const d = e.getValue(f, (i = e.latestValues[f]) !== null && i !== void 0 ? i : null),
      p = l[f];
    if (p === void 0 || (c && QM(c, f))) continue;
    const y = { delay: n, ...Ph(s || {}, f) };
    let m = !1;
    if (window.MotionHandoffAnimation) {
      const h = f1(e);
      if (h) {
        const g = window.MotionHandoffAnimation(h, f, ae);
        g !== null && ((y.startTime = g), (m = !0));
      }
    }
    Af(e, f), d.start(Uh(f, d, p, e.shouldReduceMotion && u1.has(f) ? { type: !1 } : y, e, m));
    const w = d.animation;
    w && u.push(w);
  }
  return (
    a &&
      Promise.all(u).then(() => {
        ae.update(() => {
          a && PP(e, a);
        });
      }),
    u
  );
}
function Ff(e, t, n = {}) {
  var r;
  const o = fu(
    e,
    t,
    n.type === "exit"
      ? (r = e.presenceContext) === null || r === void 0
        ? void 0
        : r.custom
      : void 0,
  );
  let { transition: i = e.getDefaultTransition() || {} } = o || {};
  n.transitionOverride && (i = n.transitionOverride);
  const s = o ? () => Promise.all(B1(e, o, n)) : () => Promise.resolve(),
    a =
      e.variantChildren && e.variantChildren.size
        ? (u = 0) => {
            const { delayChildren: c = 0, staggerChildren: f, staggerDirection: d } = i;
            return qM(e, t, c + u, f, d, n);
          }
        : () => Promise.resolve(),
    { when: l } = i;
  if (l) {
    const [u, c] = l === "beforeChildren" ? [s, a] : [a, s];
    return u().then(() => c());
  } else return Promise.all([s(), a(n.delay)]);
}
function qM(e, t, n = 0, r = 0, o = 1, i) {
  const s = [],
    a = (e.variantChildren.size - 1) * r,
    l = o === 1 ? (u = 0) => u * r : (u = 0) => a - u * r;
  return (
    Array.from(e.variantChildren)
      .sort(JM)
      .forEach((u, c) => {
        u.notify("AnimationStart", t),
          s.push(Ff(u, t, { ...i, delay: n + l(c) }).then(() => u.notify("AnimationComplete", t)));
      }),
    Promise.all(s)
  );
}
function JM(e, t) {
  return e.sortNodePosition(t);
}
function eA(e, t, n = {}) {
  e.notify("AnimationStart", t);
  let r;
  if (Array.isArray(t)) {
    const o = t.map((i) => Ff(e, i, n));
    r = Promise.all(o);
  } else if (typeof t == "string") r = Ff(e, t, n);
  else {
    const o = typeof t == "function" ? fu(e, t, n.custom) : t;
    r = Promise.all(B1(e, o, n));
  }
  return r.then(() => {
    e.notify("AnimationComplete", t);
  });
}
const tA = yh.length;
function U1(e) {
  if (!e) return;
  if (!e.isControllingVariants) {
    const n = e.parent ? U1(e.parent) || {} : {};
    return e.props.initial !== void 0 && (n.initial = e.props.initial), n;
  }
  const t = {};
  for (let n = 0; n < tA; n++) {
    const r = yh[n],
      o = e.props[r];
    (fs(o) || o === !1) && (t[r] = o);
  }
  return t;
}
const nA = [...gh].reverse(),
  rA = gh.length;
function oA(e) {
  return (t) => Promise.all(t.map(({ animation: n, options: r }) => eA(e, n, r)));
}
function iA(e) {
  let t = oA(e),
    n = fg(),
    r = !0;
  const o = (l) => (u, c) => {
    var f;
    const d = fu(
      e,
      c,
      l === "exit"
        ? (f = e.presenceContext) === null || f === void 0
          ? void 0
          : f.custom
        : void 0,
    );
    if (d) {
      const { transition: p, transitionEnd: y, ...m } = d;
      u = { ...u, ...m, ...y };
    }
    return u;
  };
  function i(l) {
    t = l(e);
  }
  function s(l) {
    const { props: u } = e,
      c = U1(e.parent) || {},
      f = [],
      d = new Set();
    let p = {},
      y = 1 / 0;
    for (let w = 0; w < rA; w++) {
      const h = nA[w],
        g = n[h],
        x = u[h] !== void 0 ? u[h] : c[h],
        S = fs(x),
        E = h === l ? g.isActive : null;
      E === !1 && (y = w);
      let C = x === c[h] && x !== u[h] && S;
      if (
        (C && r && e.manuallyAnimateOnMount && (C = !1),
        (g.protectedKeys = { ...p }),
        (!g.isActive && E === null) || (!x && !g.prevProp) || uu(x) || typeof x == "boolean")
      )
        continue;
      const b = sA(g.prevProp, x);
      let _ = b || (h === l && g.isActive && !C && S) || (w > y && S),
        A = !1;
      const R = Array.isArray(x) ? x : [x];
      let z = R.reduce(o(h), {});
      E === !1 && (z = {});
      const { prevResolvedValues: F = {} } = g,
        j = { ...F, ...z },
        k = (V) => {
          (_ = !0), d.has(V) && ((A = !0), d.delete(V)), (g.needsAnimating[V] = !0);
          const P = e.getValue(V);
          P && (P.liveStyle = !1);
        };
      for (const V in j) {
        const P = z[V],
          T = F[V];
        if (p.hasOwnProperty(V)) continue;
        let D = !1;
        Nf(P) && Nf(T) ? (D = !t1(P, T)) : (D = P !== T),
          D
            ? P != null
              ? k(V)
              : d.add(V)
            : P !== void 0 && d.has(V)
              ? k(V)
              : (g.protectedKeys[V] = !0);
      }
      (g.prevProp = x),
        (g.prevResolvedValues = z),
        g.isActive && (p = { ...p, ...z }),
        r && e.blockInitialAnimation && (_ = !1),
        _ && (!(C && b) || A) && f.push(...R.map((V) => ({ animation: V, options: { type: h } })));
    }
    if (d.size) {
      const w = {};
      d.forEach((h) => {
        const g = e.getBaseTarget(h),
          x = e.getValue(h);
        x && (x.liveStyle = !0), (w[h] = g ?? null);
      }),
        f.push({ animation: w });
    }
    let m = !!f.length;
    return (
      r && (u.initial === !1 || u.initial === u.animate) && !e.manuallyAnimateOnMount && (m = !1),
      (r = !1),
      m ? t(f) : Promise.resolve()
    );
  }
  function a(l, u) {
    var c;
    if (n[l].isActive === u) return Promise.resolve();
    (c = e.variantChildren) === null ||
      c === void 0 ||
      c.forEach((d) => {
        var p;
        return (p = d.animationState) === null || p === void 0 ? void 0 : p.setActive(l, u);
      }),
      (n[l].isActive = u);
    const f = s(l);
    for (const d in n) n[d].protectedKeys = {};
    return f;
  }
  return {
    animateChanges: s,
    setActive: a,
    setAnimateFunction: i,
    getState: () => n,
    reset: () => {
      (n = fg()), (r = !0);
    },
  };
}
function sA(e, t) {
  return typeof t == "string" ? t !== e : Array.isArray(t) ? !t1(t, e) : !1;
}
function fr(e = !1) {
  return { isActive: e, protectedKeys: {}, needsAnimating: {}, prevResolvedValues: {} };
}
function fg() {
  return {
    animate: fr(!0),
    whileInView: fr(),
    whileHover: fr(),
    whileTap: fr(),
    whileDrag: fr(),
    whileFocus: fr(),
    exit: fr(),
  };
}
class or {
  constructor(t) {
    (this.isMounted = !1), (this.node = t);
  }
  update() {}
}
class aA extends or {
  constructor(t) {
    super(t), t.animationState || (t.animationState = iA(t));
  }
  updateAnimationControlsSubscription() {
    const { animate: t } = this.node.getProps();
    uu(t) && (this.unmountControls = t.subscribe(this.node));
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
let lA = 0;
class uA extends or {
  constructor() {
    super(...arguments), (this.id = lA++);
  }
  update() {
    if (!this.node.presenceContext) return;
    const { isPresent: t, onExitComplete: n } = this.node.presenceContext,
      { isPresent: r } = this.node.prevPresenceContext || {};
    if (!this.node.animationState || t === r) return;
    const o = this.node.animationState.setActive("exit", !t);
    n && !t && o.then(() => n(this.id));
  }
  mount() {
    const { register: t } = this.node.presenceContext || {};
    t && (this.unmount = t(this.id));
  }
  unmount() {}
}
const cA = { animation: { Feature: aA }, exit: { Feature: uA } };
function ps(e, t, n, r = { passive: !0 }) {
  return e.addEventListener(t, n, r), () => e.removeEventListener(t, n);
}
function zs(e) {
  return { point: { x: e.pageX, y: e.pageY } };
}
const fA = (e) => (t) => Rh(t) && e(t, zs(t));
function Bi(e, t, n, r) {
  return ps(e, t, fA(n), r);
}
const dg = (e, t) => Math.abs(e - t);
function dA(e, t) {
  const n = dg(e.x, t.x),
    r = dg(e.y, t.y);
  return Math.sqrt(n ** 2 + r ** 2);
}
class H1 {
  constructor(t, n, { transformPagePoint: r, contextWindow: o, dragSnapToOrigin: i = !1 } = {}) {
    if (
      ((this.startEvent = null),
      (this.lastMoveEvent = null),
      (this.lastMoveEventInfo = null),
      (this.handlers = {}),
      (this.contextWindow = window),
      (this.updatePoint = () => {
        if (!(this.lastMoveEvent && this.lastMoveEventInfo)) return;
        const f = pc(this.lastMoveEventInfo, this.history),
          d = this.startEvent !== null,
          p = dA(f.offset, { x: 0, y: 0 }) >= 3;
        if (!d && !p) return;
        const { point: y } = f,
          { timestamp: m } = Me;
        this.history.push({ ...y, timestamp: m });
        const { onStart: w, onMove: h } = this.handlers;
        d || (w && w(this.lastMoveEvent, f), (this.startEvent = this.lastMoveEvent)),
          h && h(this.lastMoveEvent, f);
      }),
      (this.handlePointerMove = (f, d) => {
        (this.lastMoveEvent = f),
          (this.lastMoveEventInfo = hc(d, this.transformPagePoint)),
          ae.update(this.updatePoint, !0);
      }),
      (this.handlePointerUp = (f, d) => {
        this.end();
        const { onEnd: p, onSessionEnd: y, resumeAnimation: m } = this.handlers;
        if ((this.dragSnapToOrigin && m && m(), !(this.lastMoveEvent && this.lastMoveEventInfo)))
          return;
        const w = pc(
          f.type === "pointercancel" ? this.lastMoveEventInfo : hc(d, this.transformPagePoint),
          this.history,
        );
        this.startEvent && p && p(f, w), y && y(f, w);
      }),
      !Rh(t))
    )
      return;
    (this.dragSnapToOrigin = i),
      (this.handlers = n),
      (this.transformPagePoint = r),
      (this.contextWindow = o || window);
    const s = zs(t),
      a = hc(s, this.transformPagePoint),
      { point: l } = a,
      { timestamp: u } = Me;
    this.history = [{ ...l, timestamp: u }];
    const { onSessionStart: c } = n;
    c && c(t, pc(a, this.history)),
      (this.removeListeners = Fs(
        Bi(this.contextWindow, "pointermove", this.handlePointerMove),
        Bi(this.contextWindow, "pointerup", this.handlePointerUp),
        Bi(this.contextWindow, "pointercancel", this.handlePointerUp),
      ));
  }
  updateHandlers(t) {
    this.handlers = t;
  }
  end() {
    this.removeListeners && this.removeListeners(), Cn(this.updatePoint);
  }
}
function hc(e, t) {
  return t ? { point: t(e.point) } : e;
}
function hg(e, t) {
  return { x: e.x - t.x, y: e.y - t.y };
}
function pc({ point: e }, t) {
  return { point: e, delta: hg(e, W1(t)), offset: hg(e, hA(t)), velocity: pA(t, 0.1) };
}
function hA(e) {
  return e[0];
}
function W1(e) {
  return e[e.length - 1];
}
function pA(e, t) {
  if (e.length < 2) return { x: 0, y: 0 };
  let n = e.length - 1,
    r = null;
  const o = W1(e);
  for (; n >= 0 && ((r = e[n]), !(o.timestamp - r.timestamp > gn(t))); ) n--;
  if (!r) return { x: 0, y: 0 };
  const i = yn(o.timestamp - r.timestamp);
  if (i === 0) return { x: 0, y: 0 };
  const s = { x: (o.x - r.x) / i, y: (o.y - r.y) / i };
  return s.x === 1 / 0 && (s.x = 0), s.y === 1 / 0 && (s.y = 0), s;
}
const G1 = 1e-4,
  mA = 1 - G1,
  gA = 1 + G1,
  K1 = 0.01,
  yA = 0 - K1,
  vA = 0 + K1;
function pt(e) {
  return e.max - e.min;
}
function xA(e, t, n) {
  return Math.abs(e - t) <= n;
}
function pg(e, t, n, r = 0.5) {
  (e.origin = r),
    (e.originPoint = ge(t.min, t.max, e.origin)),
    (e.scale = pt(n) / pt(t)),
    (e.translate = ge(n.min, n.max, e.origin) - e.originPoint),
    ((e.scale >= mA && e.scale <= gA) || isNaN(e.scale)) && (e.scale = 1),
    ((e.translate >= yA && e.translate <= vA) || isNaN(e.translate)) && (e.translate = 0);
}
function Ui(e, t, n, r) {
  pg(e.x, t.x, n.x, r ? r.originX : void 0), pg(e.y, t.y, n.y, r ? r.originY : void 0);
}
function mg(e, t, n) {
  (e.min = n.min + t.min), (e.max = e.min + pt(t));
}
function wA(e, t, n) {
  mg(e.x, t.x, n.x), mg(e.y, t.y, n.y);
}
function gg(e, t, n) {
  (e.min = t.min - n.min), (e.max = e.min + pt(t));
}
function Hi(e, t, n) {
  gg(e.x, t.x, n.x), gg(e.y, t.y, n.y);
}
function SA(e, { min: t, max: n }, r) {
  return (
    t !== void 0 && e < t
      ? (e = r ? ge(t, e, r.min) : Math.max(e, t))
      : n !== void 0 && e > n && (e = r ? ge(n, e, r.max) : Math.min(e, n)),
    e
  );
}
function yg(e, t, n) {
  return {
    min: t !== void 0 ? e.min + t : void 0,
    max: n !== void 0 ? e.max + n - (e.max - e.min) : void 0,
  };
}
function EA(e, { top: t, left: n, bottom: r, right: o }) {
  return { x: yg(e.x, n, o), y: yg(e.y, t, r) };
}
function vg(e, t) {
  let n = t.min - e.min,
    r = t.max - e.max;
  return t.max - t.min < e.max - e.min && ([n, r] = [r, n]), { min: n, max: r };
}
function CA(e, t) {
  return { x: vg(e.x, t.x), y: vg(e.y, t.y) };
}
function bA(e, t) {
  let n = 0.5;
  const r = pt(e),
    o = pt(t);
  return (
    o > r ? (n = $o(t.min, t.max - r, e.min)) : r > o && (n = $o(e.min, e.max - o, t.min)),
    bn(0, 1, n)
  );
}
function kA(e, t) {
  const n = {};
  return (
    t.min !== void 0 && (n.min = t.min - e.min), t.max !== void 0 && (n.max = t.max - e.min), n
  );
}
const zf = 0.35;
function _A(e = zf) {
  return (
    e === !1 ? (e = 0) : e === !0 && (e = zf),
    { x: xg(e, "left", "right"), y: xg(e, "top", "bottom") }
  );
}
function xg(e, t, n) {
  return { min: wg(e, t), max: wg(e, n) };
}
function wg(e, t) {
  return typeof e == "number" ? e : e[t] || 0;
}
const Sg = () => ({ translate: 0, scale: 1, origin: 0, originPoint: 0 }),
  po = () => ({ x: Sg(), y: Sg() }),
  Eg = () => ({ min: 0, max: 0 }),
  Ce = () => ({ x: Eg(), y: Eg() });
function xt(e) {
  return [e("x"), e("y")];
}
function Y1({ top: e, left: t, right: n, bottom: r }) {
  return { x: { min: t, max: n }, y: { min: e, max: r } };
}
function TA({ x: e, y: t }) {
  return { top: t.min, right: e.max, bottom: t.max, left: e.min };
}
function NA(e, t) {
  if (!t) return e;
  const n = t({ x: e.left, y: e.top }),
    r = t({ x: e.right, y: e.bottom });
  return { top: n.y, left: n.x, bottom: r.y, right: r.x };
}
function mc(e) {
  return e === void 0 || e === 1;
}
function $f({ scale: e, scaleX: t, scaleY: n }) {
  return !mc(e) || !mc(t) || !mc(n);
}
function pr(e) {
  return $f(e) || X1(e) || e.z || e.rotate || e.rotateX || e.rotateY || e.skewX || e.skewY;
}
function X1(e) {
  return Cg(e.x) || Cg(e.y);
}
function Cg(e) {
  return e && e !== "0%";
}
function _l(e, t, n) {
  const r = e - n,
    o = t * r;
  return n + o;
}
function bg(e, t, n, r, o) {
  return o !== void 0 && (e = _l(e, o, r)), _l(e, n, r) + t;
}
function jf(e, t = 0, n = 1, r, o) {
  (e.min = bg(e.min, t, n, r, o)), (e.max = bg(e.max, t, n, r, o));
}
function Z1(e, { x: t, y: n }) {
  jf(e.x, t.translate, t.scale, t.originPoint), jf(e.y, n.translate, n.scale, n.originPoint);
}
const kg = 0.999999999999,
  _g = 1.0000000000001;
function PA(e, t, n, r = !1) {
  const o = n.length;
  if (!o) return;
  t.x = t.y = 1;
  let i, s;
  for (let a = 0; a < o; a++) {
    (i = n[a]), (s = i.projectionDelta);
    const { visualElement: l } = i.options;
    (l && l.props.style && l.props.style.display === "contents") ||
      (r &&
        i.options.layoutScroll &&
        i.scroll &&
        i !== i.root &&
        go(e, { x: -i.scroll.offset.x, y: -i.scroll.offset.y }),
      s && ((t.x *= s.x.scale), (t.y *= s.y.scale), Z1(e, s)),
      r && pr(i.latestValues) && go(e, i.latestValues));
  }
  t.x < _g && t.x > kg && (t.x = 1), t.y < _g && t.y > kg && (t.y = 1);
}
function mo(e, t) {
  (e.min = e.min + t), (e.max = e.max + t);
}
function Tg(e, t, n, r, o = 0.5) {
  const i = ge(e.min, e.max, o);
  jf(e, t, n, i, r);
}
function go(e, t) {
  Tg(e.x, t.x, t.scaleX, t.scale, t.originX), Tg(e.y, t.y, t.scaleY, t.scale, t.originY);
}
function Q1(e, t) {
  return Y1(NA(e.getBoundingClientRect(), t));
}
function MA(e, t, n) {
  const r = Q1(e, n),
    { scroll: o } = t;
  return o && (mo(r.x, o.offset.x), mo(r.y, o.offset.y)), r;
}
const q1 = ({ current: e }) => (e ? e.ownerDocument.defaultView : null),
  AA = new WeakMap();
class RA {
  constructor(t) {
    (this.openDragLock = null),
      (this.isDragging = !1),
      (this.currentDirection = null),
      (this.originPoint = { x: 0, y: 0 }),
      (this.constraints = !1),
      (this.hasMutatedConstraints = !1),
      (this.elastic = Ce()),
      (this.visualElement = t);
  }
  start(t, { snapToCursor: n = !1 } = {}) {
    const { presenceContext: r } = this.visualElement;
    if (r && r.isPresent === !1) return;
    const o = (c) => {
        const { dragSnapToOrigin: f } = this.getProps();
        f ? this.pauseAnimation() : this.stopAnimation(), n && this.snapToCursor(zs(c).point);
      },
      i = (c, f) => {
        const { drag: d, dragPropagation: p, onDragStart: y } = this.getProps();
        if (
          d &&
          !p &&
          (this.openDragLock && this.openDragLock(),
          (this.openDragLock = bP(d)),
          !this.openDragLock)
        )
          return;
        (this.isDragging = !0),
          (this.currentDirection = null),
          this.resolveConstraints(),
          this.visualElement.projection &&
            ((this.visualElement.projection.isAnimationBlocked = !0),
            (this.visualElement.projection.target = void 0)),
          xt((w) => {
            let h = this.getAxisMotionValue(w).get() || 0;
            if (qt.test(h)) {
              const { projection: g } = this.visualElement;
              if (g && g.layout) {
                const x = g.layout.layoutBox[w];
                x && (h = pt(x) * (parseFloat(h) / 100));
              }
            }
            this.originPoint[w] = h;
          }),
          y && ae.postRender(() => y(c, f)),
          Af(this.visualElement, "transform");
        const { animationState: m } = this.visualElement;
        m && m.setActive("whileDrag", !0);
      },
      s = (c, f) => {
        const {
          dragPropagation: d,
          dragDirectionLock: p,
          onDirectionLock: y,
          onDrag: m,
        } = this.getProps();
        if (!d && !this.openDragLock) return;
        const { offset: w } = f;
        if (p && this.currentDirection === null) {
          (this.currentDirection = DA(w)),
            this.currentDirection !== null && y && y(this.currentDirection);
          return;
        }
        this.updateAxis("x", f.point, w),
          this.updateAxis("y", f.point, w),
          this.visualElement.render(),
          m && m(c, f);
      },
      a = (c, f) => this.stop(c, f),
      l = () =>
        xt((c) => {
          var f;
          return (
            this.getAnimationState(c) === "paused" &&
            ((f = this.getAxisMotionValue(c).animation) === null || f === void 0
              ? void 0
              : f.play())
          );
        }),
      { dragSnapToOrigin: u } = this.getProps();
    this.panSession = new H1(
      t,
      { onSessionStart: o, onStart: i, onMove: s, onSessionEnd: a, resumeAnimation: l },
      {
        transformPagePoint: this.visualElement.getTransformPagePoint(),
        dragSnapToOrigin: u,
        contextWindow: q1(this.visualElement),
      },
    );
  }
  stop(t, n) {
    const r = this.isDragging;
    if ((this.cancel(), !r)) return;
    const { velocity: o } = n;
    this.startAnimation(o);
    const { onDragEnd: i } = this.getProps();
    i && ae.postRender(() => i(t, n));
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
    const { drag: o } = this.getProps();
    if (!r || !da(t, o, this.currentDirection)) return;
    const i = this.getAxisMotionValue(t);
    let s = this.originPoint[t] + r[t];
    this.constraints && this.constraints[t] && (s = SA(s, this.constraints[t], this.elastic[t])),
      i.set(s);
  }
  resolveConstraints() {
    var t;
    const { dragConstraints: n, dragElastic: r } = this.getProps(),
      o =
        this.visualElement.projection && !this.visualElement.projection.layout
          ? this.visualElement.projection.measure(!1)
          : (t = this.visualElement.projection) === null || t === void 0
            ? void 0
            : t.layout,
      i = this.constraints;
    n && fo(n)
      ? this.constraints || (this.constraints = this.resolveRefConstraints())
      : n && o
        ? (this.constraints = EA(o.layoutBox, n))
        : (this.constraints = !1),
      (this.elastic = _A(r)),
      i !== this.constraints &&
        o &&
        this.constraints &&
        !this.hasMutatedConstraints &&
        xt((s) => {
          this.constraints !== !1 &&
            this.getAxisMotionValue(s) &&
            (this.constraints[s] = kA(o.layoutBox[s], this.constraints[s]));
        });
  }
  resolveRefConstraints() {
    const { dragConstraints: t, onMeasureDragConstraints: n } = this.getProps();
    if (!t || !fo(t)) return !1;
    const r = t.current,
      { projection: o } = this.visualElement;
    if (!o || !o.layout) return !1;
    const i = MA(r, o.root, this.visualElement.getTransformPagePoint());
    let s = CA(o.layout.layoutBox, i);
    if (n) {
      const a = n(TA(s));
      (this.hasMutatedConstraints = !!a), a && (s = Y1(a));
    }
    return s;
  }
  startAnimation(t) {
    const {
        drag: n,
        dragMomentum: r,
        dragElastic: o,
        dragTransition: i,
        dragSnapToOrigin: s,
        onDragTransitionEnd: a,
      } = this.getProps(),
      l = this.constraints || {},
      u = xt((c) => {
        if (!da(c, n, this.currentDirection)) return;
        let f = (l && l[c]) || {};
        s && (f = { min: 0, max: 0 });
        const d = o ? 200 : 1e6,
          p = o ? 40 : 1e7,
          y = {
            type: "inertia",
            velocity: r ? t[c] : 0,
            bounceStiffness: d,
            bounceDamping: p,
            timeConstant: 750,
            restDelta: 1,
            restSpeed: 10,
            ...i,
            ...f,
          };
        return this.startAxisValueAnimation(c, y);
      });
    return Promise.all(u).then(a);
  }
  startAxisValueAnimation(t, n) {
    const r = this.getAxisMotionValue(t);
    return Af(this.visualElement, t), r.start(Uh(t, r, 0, n, this.visualElement, !1));
  }
  stopAnimation() {
    xt((t) => this.getAxisMotionValue(t).stop());
  }
  pauseAnimation() {
    xt((t) => {
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
      o = r[n];
    return o || this.visualElement.getValue(t, (r.initial ? r.initial[t] : void 0) || 0);
  }
  snapToCursor(t) {
    xt((n) => {
      const { drag: r } = this.getProps();
      if (!da(n, r, this.currentDirection)) return;
      const { projection: o } = this.visualElement,
        i = this.getAxisMotionValue(n);
      if (o && o.layout) {
        const { min: s, max: a } = o.layout.layoutBox[n];
        i.set(t[n] - ge(s, a, 0.5));
      }
    });
  }
  scalePositionWithinConstraints() {
    if (!this.visualElement.current) return;
    const { drag: t, dragConstraints: n } = this.getProps(),
      { projection: r } = this.visualElement;
    if (!fo(n) || !r || !this.constraints) return;
    this.stopAnimation();
    const o = { x: 0, y: 0 };
    xt((s) => {
      const a = this.getAxisMotionValue(s);
      if (a && this.constraints !== !1) {
        const l = a.get();
        o[s] = bA({ min: l, max: l }, this.constraints[s]);
      }
    });
    const { transformTemplate: i } = this.visualElement.getProps();
    (this.visualElement.current.style.transform = i ? i({}, "") : "none"),
      r.root && r.root.updateScroll(),
      r.updateLayout(),
      this.resolveConstraints(),
      xt((s) => {
        if (!da(s, t, null)) return;
        const a = this.getAxisMotionValue(s),
          { min: l, max: u } = this.constraints[s];
        a.set(ge(l, u, o[s]));
      });
  }
  addListeners() {
    if (!this.visualElement.current) return;
    AA.set(this.visualElement, this);
    const t = this.visualElement.current,
      n = Bi(t, "pointerdown", (l) => {
        const { drag: u, dragListener: c = !0 } = this.getProps();
        u && c && this.start(l);
      }),
      r = () => {
        const { dragConstraints: l } = this.getProps();
        fo(l) && l.current && (this.constraints = this.resolveRefConstraints());
      },
      { projection: o } = this.visualElement,
      i = o.addEventListener("measure", r);
    o && !o.layout && (o.root && o.root.updateScroll(), o.updateLayout()), ae.read(r);
    const s = ps(window, "resize", () => this.scalePositionWithinConstraints()),
      a = o.addEventListener("didUpdate", ({ delta: l, hasLayoutChanged: u }) => {
        this.isDragging &&
          u &&
          (xt((c) => {
            const f = this.getAxisMotionValue(c);
            f && ((this.originPoint[c] += l[c].translate), f.set(f.get() + l[c].translate));
          }),
          this.visualElement.render());
      });
    return () => {
      s(), n(), i(), a && a();
    };
  }
  getProps() {
    const t = this.visualElement.getProps(),
      {
        drag: n = !1,
        dragDirectionLock: r = !1,
        dragPropagation: o = !1,
        dragConstraints: i = !1,
        dragElastic: s = zf,
        dragMomentum: a = !0,
      } = t;
    return {
      ...t,
      drag: n,
      dragDirectionLock: r,
      dragPropagation: o,
      dragConstraints: i,
      dragElastic: s,
      dragMomentum: a,
    };
  }
}
function da(e, t, n) {
  return (t === !0 || t === e) && (n === null || n === e);
}
function DA(e, t = 10) {
  let n = null;
  return Math.abs(e.y) > t ? (n = "y") : Math.abs(e.x) > t && (n = "x"), n;
}
class IA extends or {
  constructor(t) {
    super(t),
      (this.removeGroupControls = dt),
      (this.removeListeners = dt),
      (this.controls = new RA(t));
  }
  mount() {
    const { dragControls: t } = this.node.getProps();
    t && (this.removeGroupControls = t.subscribe(this.controls)),
      (this.removeListeners = this.controls.addListeners() || dt);
  }
  unmount() {
    this.removeGroupControls(), this.removeListeners();
  }
}
const Ng = (e) => (t, n) => {
  e && ae.postRender(() => e(t, n));
};
class LA extends or {
  constructor() {
    super(...arguments), (this.removePointerDownListener = dt);
  }
  onPointerDown(t) {
    this.session = new H1(t, this.createPanHandlers(), {
      transformPagePoint: this.node.getTransformPagePoint(),
      contextWindow: q1(this.node),
    });
  }
  createPanHandlers() {
    const { onPanSessionStart: t, onPanStart: n, onPan: r, onPanEnd: o } = this.node.getProps();
    return {
      onSessionStart: Ng(t),
      onStart: Ng(n),
      onMove: r,
      onEnd: (i, s) => {
        delete this.session, o && ae.postRender(() => o(i, s));
      },
    };
  }
  mount() {
    this.removePointerDownListener = Bi(this.node.current, "pointerdown", (t) =>
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
const Ua = { hasAnimatedSinceResize: !0, hasEverUpdated: !1 };
function Pg(e, t) {
  return t.max === t.min ? 0 : (e / (t.max - t.min)) * 100;
}
const pi = {
    correct: (e, t) => {
      if (!t.target) return e;
      if (typeof e == "string")
        if (X.test(e)) e = parseFloat(e);
        else return e;
      const n = Pg(e, t.target.x),
        r = Pg(e, t.target.y);
      return `${n}% ${r}%`;
    },
  },
  VA = {
    correct: (e, { treeScale: t, projectionDelta: n }) => {
      const r = e,
        o = Jn.parse(e);
      if (o.length > 5) return r;
      const i = Jn.createTransformer(e),
        s = typeof o[0] != "number" ? 1 : 0,
        a = n.x.scale * t.x,
        l = n.y.scale * t.y;
      (o[0 + s] /= a), (o[1 + s] /= l);
      const u = ge(a, l, 0.5);
      return (
        typeof o[2 + s] == "number" && (o[2 + s] /= u),
        typeof o[3 + s] == "number" && (o[3 + s] /= u),
        i(o)
      );
    },
  };
class OA extends v.Component {
  componentDidMount() {
    const { visualElement: t, layoutGroup: n, switchLayoutGroup: r, layoutId: o } = this.props,
      { projection: i } = t;
    rP(FA),
      i &&
        (n.group && n.group.add(i),
        r && r.register && o && r.register(i),
        i.root.didUpdate(),
        i.addEventListener("animationComplete", () => {
          this.safeToRemove();
        }),
        i.setOptions({ ...i.options, onExitComplete: () => this.safeToRemove() })),
      (Ua.hasEverUpdated = !0);
  }
  getSnapshotBeforeUpdate(t) {
    const { layoutDependency: n, visualElement: r, drag: o, isPresent: i } = this.props,
      s = r.projection;
    return (
      s &&
        ((s.isPresent = i),
        o || t.layoutDependency !== n || n === void 0 ? s.willUpdate() : this.safeToRemove(),
        t.isPresent !== i &&
          (i
            ? s.promote()
            : s.relegate() ||
              ae.postRender(() => {
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
      xh.postRender(() => {
        !t.currentAnimation && t.isLead() && this.safeToRemove();
      }));
  }
  componentWillUnmount() {
    const { visualElement: t, layoutGroup: n, switchLayoutGroup: r } = this.props,
      { projection: o } = t;
    o &&
      (o.scheduleCheckAfterUnmount(),
      n && n.group && n.group.remove(o),
      r && r.deregister && r.deregister(o));
  }
  safeToRemove() {
    const { safeToRemove: t } = this.props;
    t && t();
  }
  render() {
    return null;
  }
}
function J1(e) {
  const [t, n] = xN(),
    r = v.useContext(Lw);
  return N.jsx(OA, {
    ...e,
    layoutGroup: r,
    switchLayoutGroup: v.useContext(Bw),
    isPresent: t,
    safeToRemove: n,
  });
}
const FA = {
  borderRadius: {
    ...pi,
    applyTo: [
      "borderTopLeftRadius",
      "borderTopRightRadius",
      "borderBottomLeftRadius",
      "borderBottomRightRadius",
    ],
  },
  borderTopLeftRadius: pi,
  borderTopRightRadius: pi,
  borderBottomLeftRadius: pi,
  borderBottomRightRadius: pi,
  boxShadow: VA,
};
function zA(e, t, n) {
  const r = Re(e) ? e : Bo(e);
  return r.start(Uh("", r, t, n)), r.animation;
}
function $A(e) {
  return e instanceof SVGElement && e.tagName !== "svg";
}
const jA = (e, t) => e.depth - t.depth;
class BA {
  constructor() {
    (this.children = []), (this.isDirty = !1);
  }
  add(t) {
    Dh(this.children, t), (this.isDirty = !0);
  }
  remove(t) {
    Ih(this.children, t), (this.isDirty = !0);
  }
  forEach(t) {
    this.isDirty && this.children.sort(jA), (this.isDirty = !1), this.children.forEach(t);
  }
}
function UA(e, t) {
  const n = Jt.now(),
    r = ({ timestamp: o }) => {
      const i = o - n;
      i >= t && (Cn(r), e(i - t));
    };
  return ae.read(r, !0), () => Cn(r);
}
const eS = ["TopLeft", "TopRight", "BottomLeft", "BottomRight"],
  HA = eS.length,
  Mg = (e) => (typeof e == "string" ? parseFloat(e) : e),
  Ag = (e) => typeof e == "number" || X.test(e);
function WA(e, t, n, r, o, i) {
  o
    ? ((e.opacity = ge(0, n.opacity !== void 0 ? n.opacity : 1, GA(r))),
      (e.opacityExit = ge(t.opacity !== void 0 ? t.opacity : 1, 0, KA(r))))
    : i &&
      (e.opacity = ge(
        t.opacity !== void 0 ? t.opacity : 1,
        n.opacity !== void 0 ? n.opacity : 1,
        r,
      ));
  for (let s = 0; s < HA; s++) {
    const a = `border${eS[s]}Radius`;
    let l = Rg(t, a),
      u = Rg(n, a);
    if (l === void 0 && u === void 0) continue;
    l || (l = 0),
      u || (u = 0),
      l === 0 || u === 0 || Ag(l) === Ag(u)
        ? ((e[a] = Math.max(ge(Mg(l), Mg(u), r), 0)), (qt.test(u) || qt.test(l)) && (e[a] += "%"))
        : (e[a] = u);
  }
  (t.rotate || n.rotate) && (e.rotate = ge(t.rotate || 0, n.rotate || 0, r));
}
function Rg(e, t) {
  return e[t] !== void 0 ? e[t] : e.borderRadius;
}
const GA = tS(0, 0.5, v1),
  KA = tS(0.5, 0.95, dt);
function tS(e, t, n) {
  return (r) => (r < e ? 0 : r > t ? 1 : n($o(e, t, r)));
}
function Dg(e, t) {
  (e.min = t.min), (e.max = t.max);
}
function vt(e, t) {
  Dg(e.x, t.x), Dg(e.y, t.y);
}
function Ig(e, t) {
  (e.translate = t.translate),
    (e.scale = t.scale),
    (e.originPoint = t.originPoint),
    (e.origin = t.origin);
}
function Lg(e, t, n, r, o) {
  return (e -= t), (e = _l(e, 1 / n, r)), o !== void 0 && (e = _l(e, 1 / o, r)), e;
}
function YA(e, t = 0, n = 1, r = 0.5, o, i = e, s = e) {
  if (
    (qt.test(t) && ((t = parseFloat(t)), (t = ge(s.min, s.max, t / 100) - s.min)),
    typeof t != "number")
  )
    return;
  let a = ge(i.min, i.max, r);
  e === i && (a -= t), (e.min = Lg(e.min, t, n, a, o)), (e.max = Lg(e.max, t, n, a, o));
}
function Vg(e, t, [n, r, o], i, s) {
  YA(e, t[n], t[r], t[o], t.scale, i, s);
}
const XA = ["x", "scaleX", "originX"],
  ZA = ["y", "scaleY", "originY"];
function Og(e, t, n, r) {
  Vg(e.x, t, XA, n ? n.x : void 0, r ? r.x : void 0),
    Vg(e.y, t, ZA, n ? n.y : void 0, r ? r.y : void 0);
}
function Fg(e) {
  return e.translate === 0 && e.scale === 1;
}
function nS(e) {
  return Fg(e.x) && Fg(e.y);
}
function zg(e, t) {
  return e.min === t.min && e.max === t.max;
}
function QA(e, t) {
  return zg(e.x, t.x) && zg(e.y, t.y);
}
function $g(e, t) {
  return Math.round(e.min) === Math.round(t.min) && Math.round(e.max) === Math.round(t.max);
}
function rS(e, t) {
  return $g(e.x, t.x) && $g(e.y, t.y);
}
function jg(e) {
  return pt(e.x) / pt(e.y);
}
function Bg(e, t) {
  return e.translate === t.translate && e.scale === t.scale && e.originPoint === t.originPoint;
}
class qA {
  constructor() {
    this.members = [];
  }
  add(t) {
    Dh(this.members, t), t.scheduleRender();
  }
  remove(t) {
    if ((Ih(this.members, t), t === this.prevLead && (this.prevLead = void 0), t === this.lead)) {
      const n = this.members[this.members.length - 1];
      n && this.promote(n);
    }
  }
  relegate(t) {
    const n = this.members.findIndex((o) => t === o);
    if (n === 0) return !1;
    let r;
    for (let o = n; o >= 0; o--) {
      const i = this.members[o];
      if (i.isPresent !== !1) {
        r = i;
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
      const { crossfade: o } = t.options;
      o === !1 && r.hide();
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
function JA(e, t, n) {
  let r = "";
  const o = e.x.translate / t.x,
    i = e.y.translate / t.y,
    s = (n == null ? void 0 : n.z) || 0;
  if (
    ((o || i || s) && (r = `translate3d(${o}px, ${i}px, ${s}px) `),
    (t.x !== 1 || t.y !== 1) && (r += `scale(${1 / t.x}, ${1 / t.y}) `),
    n)
  ) {
    const { transformPerspective: u, rotate: c, rotateX: f, rotateY: d, skewX: p, skewY: y } = n;
    u && (r = `perspective(${u}px) ${r}`),
      c && (r += `rotate(${c}deg) `),
      f && (r += `rotateX(${f}deg) `),
      d && (r += `rotateY(${d}deg) `),
      p && (r += `skewX(${p}deg) `),
      y && (r += `skewY(${y}deg) `);
  }
  const a = e.x.scale * t.x,
    l = e.y.scale * t.y;
  return (a !== 1 || l !== 1) && (r += `scale(${a}, ${l})`), r || "none";
}
const mr = {
    type: "projectionFrame",
    totalNodes: 0,
    resolvedTargetDeltas: 0,
    recalculatedProjection: 0,
  },
  _i = typeof window < "u" && window.MotionDebug !== void 0,
  gc = ["", "X", "Y", "Z"],
  eR = { visibility: "hidden" },
  Ug = 1e3;
let tR = 0;
function yc(e, t, n, r) {
  const { latestValues: o } = t;
  o[e] && ((n[e] = o[e]), t.setStaticValue(e, 0), r && (r[e] = 0));
}
function oS(e) {
  if (((e.hasCheckedOptimisedAppear = !0), e.root === e)) return;
  const { visualElement: t } = e.options;
  if (!t) return;
  const n = f1(t);
  if (window.MotionHasOptimisedAnimation(n, "transform")) {
    const { layout: o, layoutId: i } = e.options;
    window.MotionCancelOptimisedAnimation(n, "transform", ae, !(o || i));
  }
  const { parent: r } = e;
  r && !r.hasCheckedOptimisedAppear && oS(r);
}
function iS({
  attachResizeListener: e,
  defaultParent: t,
  measureScroll: n,
  checkIsScrollRoot: r,
  resetTransform: o,
}) {
  return class {
    constructor(s = {}, a = t == null ? void 0 : t()) {
      (this.id = tR++),
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
            _i && (mr.totalNodes = mr.resolvedTargetDeltas = mr.recalculatedProjection = 0),
            this.nodes.forEach(oR),
            this.nodes.forEach(uR),
            this.nodes.forEach(cR),
            this.nodes.forEach(iR),
            _i && window.MotionDebug.record(mr);
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
      for (let l = 0; l < this.path.length; l++) this.path[l].shouldResetTransform = !0;
      this.root === this && (this.nodes = new BA());
    }
    addEventListener(s, a) {
      return (
        this.eventHandlers.has(s) || this.eventHandlers.set(s, new Lh()),
        this.eventHandlers.get(s).add(a)
      );
    }
    notifyListeners(s, ...a) {
      const l = this.eventHandlers.get(s);
      l && l.notify(...a);
    }
    hasListeners(s) {
      return this.eventHandlers.has(s);
    }
    mount(s, a = this.root.hasTreeAnimated) {
      if (this.instance) return;
      (this.isSVG = $A(s)), (this.instance = s);
      const { layoutId: l, layout: u, visualElement: c } = this.options;
      if (
        (c && !c.current && c.mount(s),
        this.root.nodes.add(this),
        this.parent && this.parent.children.add(this),
        a && (u || l) && (this.isLayoutDirty = !0),
        e)
      ) {
        let f;
        const d = () => (this.root.updateBlockedByResize = !1);
        e(s, () => {
          (this.root.updateBlockedByResize = !0),
            f && f(),
            (f = UA(d, 250)),
            Ua.hasAnimatedSinceResize && ((Ua.hasAnimatedSinceResize = !1), this.nodes.forEach(Wg));
        });
      }
      l && this.root.registerSharedNode(l, this),
        this.options.animate !== !1 &&
          c &&
          (l || u) &&
          this.addEventListener(
            "didUpdate",
            ({ delta: f, hasLayoutChanged: d, hasRelativeTargetChanged: p, layout: y }) => {
              if (this.isTreeAnimationBlocked()) {
                (this.target = void 0), (this.relativeTarget = void 0);
                return;
              }
              const m = this.options.transition || c.getDefaultTransition() || mR,
                { onLayoutAnimationStart: w, onLayoutAnimationComplete: h } = c.getProps(),
                g = !this.targetLayout || !rS(this.targetLayout, y) || p,
                x = !d && p;
              if (
                this.options.layoutRoot ||
                (this.resumeFrom && this.resumeFrom.instance) ||
                x ||
                (d && (g || !this.currentAnimation))
              ) {
                this.resumeFrom &&
                  ((this.resumingFrom = this.resumeFrom),
                  (this.resumingFrom.resumingFrom = void 0)),
                  this.setAnimationOrigin(f, x);
                const S = { ...Ph(m, "layout"), onPlay: w, onComplete: h };
                (c.shouldReduceMotion || this.options.layoutRoot) && ((S.delay = 0), (S.type = !1)),
                  this.startAnimation(S);
              } else
                d || Wg(this),
                  this.isLead() && this.options.onExitComplete && this.options.onExitComplete();
              this.targetLayout = y;
            },
          );
    }
    unmount() {
      this.options.layoutId && this.willUpdate(), this.root.nodes.remove(this);
      const s = this.getStack();
      s && s.remove(this),
        this.parent && this.parent.children.delete(this),
        (this.instance = void 0),
        Cn(this.updateProjection);
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
        ((this.isUpdating = !0), this.nodes && this.nodes.forEach(fR), this.animationId++);
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
        (window.MotionCancelOptimisedAnimation && !this.hasCheckedOptimisedAppear && oS(this),
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
      const { layoutId: a, layout: l } = this.options;
      if (a === void 0 && !l) return;
      const u = this.getTransformTemplate();
      (this.prevTransformTemplateValue = u ? u(this.latestValues, "") : void 0),
        this.updateSnapshot(),
        s && this.notifyListeners("willUpdate");
    }
    update() {
      if (((this.updateScheduled = !1), this.isUpdateBlocked())) {
        this.unblockUpdate(), this.clearAllSnapshots(), this.nodes.forEach(Hg);
        return;
      }
      this.isUpdating || this.nodes.forEach(aR),
        (this.isUpdating = !1),
        this.nodes.forEach(lR),
        this.nodes.forEach(nR),
        this.nodes.forEach(rR),
        this.clearAllSnapshots();
      const a = Jt.now();
      (Me.delta = bn(0, 1e3 / 60, a - Me.timestamp)),
        (Me.timestamp = a),
        (Me.isProcessing = !0),
        ac.update.process(Me),
        ac.preRender.process(Me),
        ac.render.process(Me),
        (Me.isProcessing = !1);
    }
    didUpdate() {
      this.updateScheduled || ((this.updateScheduled = !0), xh.read(this.scheduleUpdate));
    }
    clearAllSnapshots() {
      this.nodes.forEach(sR), this.sharedNodes.forEach(dR);
    }
    scheduleUpdateProjection() {
      this.projectionUpdateScheduled ||
        ((this.projectionUpdateScheduled = !0), ae.preRender(this.updateProjection, !1, !0));
    }
    scheduleCheckAfterUnmount() {
      ae.postRender(() => {
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
        for (let l = 0; l < this.path.length; l++) this.path[l].updateScroll();
      const s = this.layout;
      (this.layout = this.measure(!1)),
        (this.layoutCorrected = Ce()),
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
        const l = r(this.instance);
        this.scroll = {
          animationId: this.root.animationId,
          phase: s,
          isRoot: l,
          offset: n(this.instance),
          wasRoot: this.scroll ? this.scroll.isRoot : l,
        };
      }
    }
    resetTransform() {
      if (!o) return;
      const s = this.isLayoutDirty || this.shouldResetTransform || this.options.alwaysMeasureLayout,
        a = this.projectionDelta && !nS(this.projectionDelta),
        l = this.getTransformTemplate(),
        u = l ? l(this.latestValues, "") : void 0,
        c = u !== this.prevTransformTemplateValue;
      s &&
        (a || pr(this.latestValues) || c) &&
        (o(this.instance, u), (this.shouldResetTransform = !1), this.scheduleRender());
    }
    measure(s = !0) {
      const a = this.measurePageBox();
      let l = this.removeElementScroll(a);
      return (
        s && (l = this.removeTransform(l)),
        gR(l),
        {
          animationId: this.root.animationId,
          measuredBox: a,
          layoutBox: l,
          latestValues: {},
          source: this.id,
        }
      );
    }
    measurePageBox() {
      var s;
      const { visualElement: a } = this.options;
      if (!a) return Ce();
      const l = a.measureViewportBox();
      if (
        !(((s = this.scroll) === null || s === void 0 ? void 0 : s.wasRoot) || this.path.some(yR))
      ) {
        const { scroll: c } = this.root;
        c && (mo(l.x, c.offset.x), mo(l.y, c.offset.y));
      }
      return l;
    }
    removeElementScroll(s) {
      var a;
      const l = Ce();
      if ((vt(l, s), !((a = this.scroll) === null || a === void 0) && a.wasRoot)) return l;
      for (let u = 0; u < this.path.length; u++) {
        const c = this.path[u],
          { scroll: f, options: d } = c;
        c !== this.root &&
          f &&
          d.layoutScroll &&
          (f.wasRoot && vt(l, s), mo(l.x, f.offset.x), mo(l.y, f.offset.y));
      }
      return l;
    }
    applyTransform(s, a = !1) {
      const l = Ce();
      vt(l, s);
      for (let u = 0; u < this.path.length; u++) {
        const c = this.path[u];
        !a &&
          c.options.layoutScroll &&
          c.scroll &&
          c !== c.root &&
          go(l, { x: -c.scroll.offset.x, y: -c.scroll.offset.y }),
          pr(c.latestValues) && go(l, c.latestValues);
      }
      return pr(this.latestValues) && go(l, this.latestValues), l;
    }
    removeTransform(s) {
      const a = Ce();
      vt(a, s);
      for (let l = 0; l < this.path.length; l++) {
        const u = this.path[l];
        if (!u.instance || !pr(u.latestValues)) continue;
        $f(u.latestValues) && u.updateSnapshot();
        const c = Ce(),
          f = u.measurePageBox();
        vt(c, f), Og(a, u.latestValues, u.snapshot ? u.snapshot.layoutBox : void 0, c);
      }
      return pr(this.latestValues) && Og(a, this.latestValues), a;
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
        this.relativeParent.resolvedRelativeTargetAt !== Me.timestamp &&
        this.relativeParent.resolveTargetDelta(!0);
    }
    resolveTargetDelta(s = !1) {
      var a;
      const l = this.getLead();
      this.isProjectionDirty || (this.isProjectionDirty = l.isProjectionDirty),
        this.isTransformDirty || (this.isTransformDirty = l.isTransformDirty),
        this.isSharedProjectionDirty || (this.isSharedProjectionDirty = l.isSharedProjectionDirty);
      const u = !!this.resumingFrom || this !== l;
      if (
        !(
          s ||
          (u && this.isSharedProjectionDirty) ||
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
          ((this.resolvedRelativeTargetAt = Me.timestamp),
          !this.targetDelta && !this.relativeTarget)
        ) {
          const p = this.getClosestProjectingParent();
          p && p.layout && this.animationProgress !== 1
            ? ((this.relativeParent = p),
              this.forceRelativeParentToResolveTarget(),
              (this.relativeTarget = Ce()),
              (this.relativeTargetOrigin = Ce()),
              Hi(this.relativeTargetOrigin, this.layout.layoutBox, p.layout.layoutBox),
              vt(this.relativeTarget, this.relativeTargetOrigin))
            : (this.relativeParent = this.relativeTarget = void 0);
        }
        if (!(!this.relativeTarget && !this.targetDelta)) {
          if (
            (this.target || ((this.target = Ce()), (this.targetWithTransforms = Ce())),
            this.relativeTarget &&
            this.relativeTargetOrigin &&
            this.relativeParent &&
            this.relativeParent.target
              ? (this.forceRelativeParentToResolveTarget(),
                wA(this.target, this.relativeTarget, this.relativeParent.target))
              : this.targetDelta
                ? (this.resumingFrom
                    ? (this.target = this.applyTransform(this.layout.layoutBox))
                    : vt(this.target, this.layout.layoutBox),
                  Z1(this.target, this.targetDelta))
                : vt(this.target, this.layout.layoutBox),
            this.attemptToResolveRelativeTarget)
          ) {
            this.attemptToResolveRelativeTarget = !1;
            const p = this.getClosestProjectingParent();
            p &&
            !!p.resumingFrom == !!this.resumingFrom &&
            !p.options.layoutScroll &&
            p.target &&
            this.animationProgress !== 1
              ? ((this.relativeParent = p),
                this.forceRelativeParentToResolveTarget(),
                (this.relativeTarget = Ce()),
                (this.relativeTargetOrigin = Ce()),
                Hi(this.relativeTargetOrigin, this.target, p.target),
                vt(this.relativeTarget, this.relativeTargetOrigin))
              : (this.relativeParent = this.relativeTarget = void 0);
          }
          _i && mr.resolvedTargetDeltas++;
        }
      }
    }
    getClosestProjectingParent() {
      if (!(!this.parent || $f(this.parent.latestValues) || X1(this.parent.latestValues)))
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
        l = !!this.resumingFrom || this !== a;
      let u = !0;
      if (
        ((this.isProjectionDirty ||
          (!((s = this.parent) === null || s === void 0) && s.isProjectionDirty)) &&
          (u = !1),
        l && (this.isSharedProjectionDirty || this.isTransformDirty) && (u = !1),
        this.resolvedRelativeTargetAt === Me.timestamp && (u = !1),
        u)
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
      vt(this.layoutCorrected, this.layout.layoutBox);
      const d = this.treeScale.x,
        p = this.treeScale.y;
      PA(this.layoutCorrected, this.treeScale, this.path, l),
        a.layout &&
          !a.target &&
          (this.treeScale.x !== 1 || this.treeScale.y !== 1) &&
          ((a.target = a.layout.layoutBox), (a.targetWithTransforms = Ce()));
      const { target: y } = a;
      if (!y) {
        this.prevProjectionDelta && (this.createProjectionDeltas(), this.scheduleRender());
        return;
      }
      !this.projectionDelta || !this.prevProjectionDelta
        ? this.createProjectionDeltas()
        : (Ig(this.prevProjectionDelta.x, this.projectionDelta.x),
          Ig(this.prevProjectionDelta.y, this.projectionDelta.y)),
        Ui(this.projectionDelta, this.layoutCorrected, y, this.latestValues),
        (this.treeScale.x !== d ||
          this.treeScale.y !== p ||
          !Bg(this.projectionDelta.x, this.prevProjectionDelta.x) ||
          !Bg(this.projectionDelta.y, this.prevProjectionDelta.y)) &&
          ((this.hasProjected = !0),
          this.scheduleRender(),
          this.notifyListeners("projectionUpdate", y)),
        _i && mr.recalculatedProjection++;
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
        const l = this.getStack();
        l && l.scheduleRender();
      }
      this.resumingFrom && !this.resumingFrom.instance && (this.resumingFrom = void 0);
    }
    createProjectionDeltas() {
      (this.prevProjectionDelta = po()),
        (this.projectionDelta = po()),
        (this.projectionDeltaWithTransform = po());
    }
    setAnimationOrigin(s, a = !1) {
      const l = this.snapshot,
        u = l ? l.latestValues : {},
        c = { ...this.latestValues },
        f = po();
      (!this.relativeParent || !this.relativeParent.options.layoutRoot) &&
        (this.relativeTarget = this.relativeTargetOrigin = void 0),
        (this.attemptToResolveRelativeTarget = !a);
      const d = Ce(),
        p = l ? l.source : void 0,
        y = this.layout ? this.layout.source : void 0,
        m = p !== y,
        w = this.getStack(),
        h = !w || w.members.length <= 1,
        g = !!(m && !h && this.options.crossfade === !0 && !this.path.some(pR));
      this.animationProgress = 0;
      let x;
      (this.mixTargetDelta = (S) => {
        const E = S / 1e3;
        Gg(f.x, s.x, E),
          Gg(f.y, s.y, E),
          this.setTargetDelta(f),
          this.relativeTarget &&
            this.relativeTargetOrigin &&
            this.layout &&
            this.relativeParent &&
            this.relativeParent.layout &&
            (Hi(d, this.layout.layoutBox, this.relativeParent.layout.layoutBox),
            hR(this.relativeTarget, this.relativeTargetOrigin, d, E),
            x && QA(this.relativeTarget, x) && (this.isProjectionDirty = !1),
            x || (x = Ce()),
            vt(x, this.relativeTarget)),
          m && ((this.animationValues = c), WA(c, u, this.latestValues, E, g, h)),
          this.root.scheduleUpdateProjection(),
          this.scheduleRender(),
          (this.animationProgress = E);
      }),
        this.mixTargetDelta(this.options.layoutRoot ? 1e3 : 0);
    }
    startAnimation(s) {
      this.notifyListeners("animationStart"),
        this.currentAnimation && this.currentAnimation.stop(),
        this.resumingFrom &&
          this.resumingFrom.currentAnimation &&
          this.resumingFrom.currentAnimation.stop(),
        this.pendingAnimation && (Cn(this.pendingAnimation), (this.pendingAnimation = void 0)),
        (this.pendingAnimation = ae.update(() => {
          (Ua.hasAnimatedSinceResize = !0),
            (this.currentAnimation = zA(0, Ug, {
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
        (this.mixTargetDelta && this.mixTargetDelta(Ug), this.currentAnimation.stop()),
        this.completeAnimation();
    }
    applyTransformsToTarget() {
      const s = this.getLead();
      let { targetWithTransforms: a, target: l, layout: u, latestValues: c } = s;
      if (!(!a || !l || !u)) {
        if (
          this !== s &&
          this.layout &&
          u &&
          sS(this.options.animationType, this.layout.layoutBox, u.layoutBox)
        ) {
          l = this.target || Ce();
          const f = pt(this.layout.layoutBox.x);
          (l.x.min = s.target.x.min), (l.x.max = l.x.min + f);
          const d = pt(this.layout.layoutBox.y);
          (l.y.min = s.target.y.min), (l.y.max = l.y.min + d);
        }
        vt(a, l), go(a, c), Ui(this.projectionDeltaWithTransform, this.layoutCorrected, a, c);
      }
    }
    registerSharedNode(s, a) {
      this.sharedNodes.has(s) || this.sharedNodes.set(s, new qA()), this.sharedNodes.get(s).add(a);
      const u = a.options.initialPromotionConfig;
      a.promote({
        transition: u ? u.transition : void 0,
        preserveFollowOpacity:
          u && u.shouldPreserveFollowOpacity ? u.shouldPreserveFollowOpacity(a) : void 0,
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
    promote({ needsReset: s, transition: a, preserveFollowOpacity: l } = {}) {
      const u = this.getStack();
      u && u.promote(this, l),
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
      const { latestValues: l } = s;
      if (
        ((l.z || l.rotate || l.rotateX || l.rotateY || l.rotateZ || l.skewX || l.skewY) && (a = !0),
        !a)
      )
        return;
      const u = {};
      l.z && yc("z", s, u, this.animationValues);
      for (let c = 0; c < gc.length; c++)
        yc(`rotate${gc[c]}`, s, u, this.animationValues),
          yc(`skew${gc[c]}`, s, u, this.animationValues);
      s.render();
      for (const c in u)
        s.setStaticValue(c, u[c]), this.animationValues && (this.animationValues[c] = u[c]);
      s.scheduleRender();
    }
    getProjectionStyles(s) {
      var a, l;
      if (!this.instance || this.isSVG) return;
      if (!this.isVisible) return eR;
      const u = { visibility: "" },
        c = this.getTransformTemplate();
      if (this.needsReset)
        return (
          (this.needsReset = !1),
          (u.opacity = ""),
          (u.pointerEvents = ja(s == null ? void 0 : s.pointerEvents) || ""),
          (u.transform = c ? c(this.latestValues, "") : "none"),
          u
        );
      const f = this.getLead();
      if (!this.projectionDelta || !this.layout || !f.target) {
        const m = {};
        return (
          this.options.layoutId &&
            ((m.opacity = this.latestValues.opacity !== void 0 ? this.latestValues.opacity : 1),
            (m.pointerEvents = ja(s == null ? void 0 : s.pointerEvents) || "")),
          this.hasProjected &&
            !pr(this.latestValues) &&
            ((m.transform = c ? c({}, "") : "none"), (this.hasProjected = !1)),
          m
        );
      }
      const d = f.animationValues || f.latestValues;
      this.applyTransformsToTarget(),
        (u.transform = JA(this.projectionDeltaWithTransform, this.treeScale, d)),
        c && (u.transform = c(d, u.transform));
      const { x: p, y } = this.projectionDelta;
      (u.transformOrigin = `${p.origin * 100}% ${y.origin * 100}% 0`),
        f.animationValues
          ? (u.opacity =
              f === this
                ? (l = (a = d.opacity) !== null && a !== void 0 ? a : this.latestValues.opacity) !==
                    null && l !== void 0
                  ? l
                  : 1
                : this.preserveOpacity
                  ? this.latestValues.opacity
                  : d.opacityExit)
          : (u.opacity =
              f === this
                ? d.opacity !== void 0
                  ? d.opacity
                  : ""
                : d.opacityExit !== void 0
                  ? d.opacityExit
                  : 0);
      for (const m in Sl) {
        if (d[m] === void 0) continue;
        const { correct: w, applyTo: h } = Sl[m],
          g = u.transform === "none" ? d[m] : w(d[m], f);
        if (h) {
          const x = h.length;
          for (let S = 0; S < x; S++) u[h[S]] = g;
        } else u[m] = g;
      }
      return (
        this.options.layoutId &&
          (u.pointerEvents = f === this ? ja(s == null ? void 0 : s.pointerEvents) || "" : "none"),
        u
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
        this.root.nodes.forEach(Hg),
        this.root.sharedNodes.clear();
    }
  };
}
function nR(e) {
  e.updateLayout();
}
function rR(e) {
  var t;
  const n = ((t = e.resumeFrom) === null || t === void 0 ? void 0 : t.snapshot) || e.snapshot;
  if (e.isLead() && e.layout && n && e.hasListeners("didUpdate")) {
    const { layoutBox: r, measuredBox: o } = e.layout,
      { animationType: i } = e.options,
      s = n.source !== e.layout.source;
    i === "size"
      ? xt((f) => {
          const d = s ? n.measuredBox[f] : n.layoutBox[f],
            p = pt(d);
          (d.min = r[f].min), (d.max = d.min + p);
        })
      : sS(i, n.layoutBox, r) &&
        xt((f) => {
          const d = s ? n.measuredBox[f] : n.layoutBox[f],
            p = pt(r[f]);
          (d.max = d.min + p),
            e.relativeTarget &&
              !e.currentAnimation &&
              ((e.isProjectionDirty = !0), (e.relativeTarget[f].max = e.relativeTarget[f].min + p));
        });
    const a = po();
    Ui(a, r, n.layoutBox);
    const l = po();
    s ? Ui(l, e.applyTransform(o, !0), n.measuredBox) : Ui(l, r, n.layoutBox);
    const u = !nS(a);
    let c = !1;
    if (!e.resumeFrom) {
      const f = e.getClosestProjectingParent();
      if (f && !f.resumeFrom) {
        const { snapshot: d, layout: p } = f;
        if (d && p) {
          const y = Ce();
          Hi(y, n.layoutBox, d.layoutBox);
          const m = Ce();
          Hi(m, r, p.layoutBox),
            rS(y, m) || (c = !0),
            f.options.layoutRoot &&
              ((e.relativeTarget = m), (e.relativeTargetOrigin = y), (e.relativeParent = f));
        }
      }
    }
    e.notifyListeners("didUpdate", {
      layout: r,
      snapshot: n,
      delta: l,
      layoutDelta: a,
      hasLayoutChanged: u,
      hasRelativeTargetChanged: c,
    });
  } else if (e.isLead()) {
    const { onExitComplete: r } = e.options;
    r && r();
  }
  e.options.transition = void 0;
}
function oR(e) {
  _i && mr.totalNodes++,
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
function iR(e) {
  e.isProjectionDirty = e.isSharedProjectionDirty = e.isTransformDirty = !1;
}
function sR(e) {
  e.clearSnapshot();
}
function Hg(e) {
  e.clearMeasurements();
}
function aR(e) {
  e.isLayoutDirty = !1;
}
function lR(e) {
  const { visualElement: t } = e.options;
  t && t.getProps().onBeforeLayoutMeasure && t.notify("BeforeLayoutMeasure"), e.resetTransform();
}
function Wg(e) {
  e.finishAnimation(),
    (e.targetDelta = e.relativeTarget = e.target = void 0),
    (e.isProjectionDirty = !0);
}
function uR(e) {
  e.resolveTargetDelta();
}
function cR(e) {
  e.calcProjection();
}
function fR(e) {
  e.resetSkewAndRotation();
}
function dR(e) {
  e.removeLeadSnapshot();
}
function Gg(e, t, n) {
  (e.translate = ge(t.translate, 0, n)),
    (e.scale = ge(t.scale, 1, n)),
    (e.origin = t.origin),
    (e.originPoint = t.originPoint);
}
function Kg(e, t, n, r) {
  (e.min = ge(t.min, n.min, r)), (e.max = ge(t.max, n.max, r));
}
function hR(e, t, n, r) {
  Kg(e.x, t.x, n.x, r), Kg(e.y, t.y, n.y, r);
}
function pR(e) {
  return e.animationValues && e.animationValues.opacityExit !== void 0;
}
const mR = { duration: 0.45, ease: [0.4, 0, 0.1, 1] },
  Yg = (e) =>
    typeof navigator < "u" && navigator.userAgent && navigator.userAgent.toLowerCase().includes(e),
  Xg = Yg("applewebkit/") && !Yg("chrome/") ? Math.round : dt;
function Zg(e) {
  (e.min = Xg(e.min)), (e.max = Xg(e.max));
}
function gR(e) {
  Zg(e.x), Zg(e.y);
}
function sS(e, t, n) {
  return e === "position" || (e === "preserve-aspect" && !xA(jg(t), jg(n), 0.2));
}
function yR(e) {
  var t;
  return e !== e.root && ((t = e.scroll) === null || t === void 0 ? void 0 : t.wasRoot);
}
const vR = iS({
    attachResizeListener: (e, t) => ps(e, "resize", t),
    measureScroll: () => ({
      x: document.documentElement.scrollLeft || document.body.scrollLeft,
      y: document.documentElement.scrollTop || document.body.scrollTop,
    }),
    checkIsScrollRoot: () => !0,
  }),
  vc = { current: void 0 },
  aS = iS({
    measureScroll: (e) => ({ x: e.scrollLeft, y: e.scrollTop }),
    defaultParent: () => {
      if (!vc.current) {
        const e = new vR({});
        e.mount(window), e.setOptions({ layoutScroll: !0 }), (vc.current = e);
      }
      return vc.current;
    },
    resetTransform: (e, t) => {
      e.style.transform = t !== void 0 ? t : "none";
    },
    checkIsScrollRoot: (e) => window.getComputedStyle(e).position === "fixed",
  }),
  xR = { pan: { Feature: LA }, drag: { Feature: IA, ProjectionNode: aS, MeasureLayout: J1 } };
function Qg(e, t, n) {
  const { props: r } = e;
  e.animationState && r.whileHover && e.animationState.setActive("whileHover", n === "Start");
  const o = "onHover" + n,
    i = r[o];
  i && ae.postRender(() => i(t, zs(t)));
}
class wR extends or {
  mount() {
    const { current: t } = this.node;
    t && (this.unmount = xP(t, (n) => (Qg(this.node, n, "Start"), (r) => Qg(this.node, r, "End"))));
  }
  unmount() {}
}
class SR extends or {
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
    this.unmount = Fs(
      ps(this.node.current, "focus", () => this.onFocus()),
      ps(this.node.current, "blur", () => this.onBlur()),
    );
  }
  unmount() {}
}
function qg(e, t, n) {
  const { props: r } = e;
  e.animationState && r.whileTap && e.animationState.setActive("whileTap", n === "Start");
  const o = "onTap" + (n === "End" ? "" : n),
    i = r[o];
  i && ae.postRender(() => i(t, zs(t)));
}
class ER extends or {
  mount() {
    const { current: t } = this.node;
    t &&
      (this.unmount = CP(
        t,
        (n) => (
          qg(this.node, n, "Start"), (r, { success: o }) => qg(this.node, r, o ? "End" : "Cancel")
        ),
        { useGlobalTarget: this.node.props.globalTapTarget },
      ));
  }
  unmount() {}
}
const Bf = new WeakMap(),
  xc = new WeakMap(),
  CR = (e) => {
    const t = Bf.get(e.target);
    t && t(e);
  },
  bR = (e) => {
    e.forEach(CR);
  };
function kR({ root: e, ...t }) {
  const n = e || document;
  xc.has(n) || xc.set(n, {});
  const r = xc.get(n),
    o = JSON.stringify(t);
  return r[o] || (r[o] = new IntersectionObserver(bR, { root: e, ...t })), r[o];
}
function _R(e, t, n) {
  const r = kR(t);
  return (
    Bf.set(e, n),
    r.observe(e),
    () => {
      Bf.delete(e), r.unobserve(e);
    }
  );
}
const TR = { some: 0, all: 1 };
class NR extends or {
  constructor() {
    super(...arguments), (this.hasEnteredView = !1), (this.isInView = !1);
  }
  startObserver() {
    this.unmount();
    const { viewport: t = {} } = this.node.getProps(),
      { root: n, margin: r, amount: o = "some", once: i } = t,
      s = {
        root: n ? n.current : void 0,
        rootMargin: r,
        threshold: typeof o == "number" ? o : TR[o],
      },
      a = (l) => {
        const { isIntersecting: u } = l;
        if (this.isInView === u || ((this.isInView = u), i && !u && this.hasEnteredView)) return;
        u && (this.hasEnteredView = !0),
          this.node.animationState && this.node.animationState.setActive("whileInView", u);
        const { onViewportEnter: c, onViewportLeave: f } = this.node.getProps(),
          d = u ? c : f;
        d && d(l);
      };
    return _R(this.node.current, s, a);
  }
  mount() {
    this.startObserver();
  }
  update() {
    if (typeof IntersectionObserver > "u") return;
    const { props: t, prevProps: n } = this.node;
    ["amount", "margin", "root"].some(PR(t, n)) && this.startObserver();
  }
  unmount() {}
}
function PR({ viewport: e = {} }, { viewport: t = {} } = {}) {
  return (n) => e[n] !== t[n];
}
const MR = {
    inView: { Feature: NR },
    tap: { Feature: ER },
    focus: { Feature: SR },
    hover: { Feature: wR },
  },
  AR = { layout: { ProjectionNode: aS, MeasureLayout: J1 } },
  Uf = { current: null },
  lS = { current: !1 };
function RR() {
  if (((lS.current = !0), !!hh))
    if (window.matchMedia) {
      const e = window.matchMedia("(prefers-reduced-motion)"),
        t = () => (Uf.current = e.matches);
      e.addListener(t), t();
    } else Uf.current = !1;
}
const DR = [...R1, We, Jn],
  IR = (e) => DR.find(A1(e)),
  Jg = new WeakMap();
function LR(e, t, n) {
  for (const r in t) {
    const o = t[r],
      i = n[r];
    if (Re(o)) e.addValue(r, o);
    else if (Re(i)) e.addValue(r, Bo(o, { owner: e }));
    else if (i !== o)
      if (e.hasValue(r)) {
        const s = e.getValue(r);
        s.liveStyle === !0 ? s.jump(o) : s.hasAnimated || s.set(o);
      } else {
        const s = e.getStaticValue(r);
        e.addValue(r, Bo(s !== void 0 ? s : o, { owner: e }));
      }
  }
  for (const r in n) t[r] === void 0 && e.removeValue(r);
  return t;
}
const ey = [
  "AnimationStart",
  "AnimationComplete",
  "Update",
  "BeforeLayoutMeasure",
  "LayoutMeasure",
  "LayoutAnimationStart",
  "LayoutAnimationComplete",
];
class VR {
  scrapeMotionValuesFromProps(t, n, r) {
    return {};
  }
  constructor(
    {
      parent: t,
      props: n,
      presenceContext: r,
      reducedMotionConfig: o,
      blockInitialAnimation: i,
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
      (this.KeyframeResolver = jh),
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
        const p = Jt.now();
        this.renderScheduledAt < p &&
          ((this.renderScheduledAt = p), ae.render(this.render, !1, !0));
      });
    const { latestValues: l, renderState: u, onUpdate: c } = s;
    (this.onUpdate = c),
      (this.latestValues = l),
      (this.baseTarget = { ...l }),
      (this.initialValues = n.initial ? { ...l } : {}),
      (this.renderState = u),
      (this.parent = t),
      (this.props = n),
      (this.presenceContext = r),
      (this.depth = t ? t.depth + 1 : 0),
      (this.reducedMotionConfig = o),
      (this.options = a),
      (this.blockInitialAnimation = !!i),
      (this.isControllingVariants = cu(n)),
      (this.isVariantNode = $w(n)),
      this.isVariantNode && (this.variantChildren = new Set()),
      (this.manuallyAnimateOnMount = !!(t && t.current));
    const { willChange: f, ...d } = this.scrapeMotionValuesFromProps(n, {}, this);
    for (const p in d) {
      const y = d[p];
      l[p] !== void 0 && Re(y) && y.set(l[p], !1);
    }
  }
  mount(t) {
    (this.current = t),
      Jg.set(t, this),
      this.projection && !this.projection.instance && this.projection.mount(t),
      this.parent &&
        this.isVariantNode &&
        !this.isControllingVariants &&
        (this.removeFromVariantTree = this.parent.addVariantChild(this)),
      this.values.forEach((n, r) => this.bindToMotionValue(r, n)),
      lS.current || RR(),
      (this.shouldReduceMotion =
        this.reducedMotionConfig === "never"
          ? !1
          : this.reducedMotionConfig === "always"
            ? !0
            : Uf.current),
      this.parent && this.parent.children.add(this),
      this.update(this.props, this.presenceContext);
  }
  unmount() {
    Jg.delete(this.current),
      this.projection && this.projection.unmount(),
      Cn(this.notifyUpdate),
      Cn(this.render),
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
    const r = zr.has(t),
      o = n.on("change", (a) => {
        (this.latestValues[t] = a),
          this.props.onUpdate && ae.preRender(this.notifyUpdate),
          r && this.projection && (this.projection.isTransformDirty = !0);
      }),
      i = n.on("renderRequest", this.scheduleRender);
    let s;
    window.MotionCheckAppearSync && (s = window.MotionCheckAppearSync(this, t, n)),
      this.valueSubscriptions.set(t, () => {
        o(), i(), s && s(), n.owner && n.stop();
      });
  }
  sortNodePosition(t) {
    return !this.current || !this.sortInstanceNodePosition || this.type !== t.type
      ? 0
      : this.sortInstanceNodePosition(this.current, t.current);
  }
  updateFeatures() {
    let t = "animation";
    for (t in jo) {
      const n = jo[t];
      if (!n) continue;
      const { isEnabled: r, Feature: o } = n;
      if (
        (!this.features[t] && o && r(this.props) && (this.features[t] = new o(this)),
        this.features[t])
      ) {
        const i = this.features[t];
        i.isMounted ? i.update() : (i.mount(), (i.isMounted = !0));
      }
    }
  }
  triggerBuild() {
    this.build(this.renderState, this.latestValues, this.props);
  }
  measureViewportBox() {
    return this.current ? this.measureInstanceViewportBox(this.current, this.props) : Ce();
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
    for (let r = 0; r < ey.length; r++) {
      const o = ey[r];
      this.propEventSubscriptions[o] &&
        (this.propEventSubscriptions[o](), delete this.propEventSubscriptions[o]);
      const i = "on" + o,
        s = t[i];
      s && (this.propEventSubscriptions[o] = this.on(o, s));
    }
    (this.prevMotionValues = LR(
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
        ((r = Bo(n === null ? void 0 : n, { owner: this })), this.addValue(t, r)),
      r
    );
  }
  readValue(t, n) {
    var r;
    let o =
      this.latestValues[t] !== void 0 || !this.current
        ? this.latestValues[t]
        : (r = this.getBaseTargetFromProps(this.props, t)) !== null && r !== void 0
          ? r
          : this.readValueFromInstance(this.current, t, this.options);
    return (
      o != null &&
        (typeof o == "string" && (P1(o) || w1(o))
          ? (o = parseFloat(o))
          : !IR(o) && Jn.test(n) && (o = _1(t, n)),
        this.setBaseTarget(t, Re(o) ? o.get() : o)),
      Re(o) ? o.get() : o
    );
  }
  setBaseTarget(t, n) {
    this.baseTarget[t] = n;
  }
  getBaseTarget(t) {
    var n;
    const { initial: r } = this.props;
    let o;
    if (typeof r == "string" || typeof r == "object") {
      const s = Sh(
        this.props,
        r,
        (n = this.presenceContext) === null || n === void 0 ? void 0 : n.custom,
      );
      s && (o = s[t]);
    }
    if (r && o !== void 0) return o;
    const i = this.getBaseTargetFromProps(this.props, t);
    return i !== void 0 && !Re(i)
      ? i
      : this.initialValues[t] !== void 0 && o === void 0
        ? void 0
        : this.baseTarget[t];
  }
  on(t, n) {
    return this.events[t] || (this.events[t] = new Lh()), this.events[t].add(n);
  }
  notify(t, ...n) {
    this.events[t] && this.events[t].notify(...n);
  }
}
class uS extends VR {
  constructor() {
    super(...arguments), (this.KeyframeResolver = D1);
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
    Re(t) &&
      (this.childSubscription = t.on("change", (n) => {
        this.current && (this.current.textContent = `${n}`);
      }));
  }
}
function OR(e) {
  return window.getComputedStyle(e);
}
class FR extends uS {
  constructor() {
    super(...arguments), (this.type = "html"), (this.renderInstance = Xw);
  }
  readValueFromInstance(t, n) {
    if (zr.has(n)) {
      const r = $h(n);
      return (r && r.default) || 0;
    } else {
      const r = OR(t),
        o = (Gw(n) ? r.getPropertyValue(n) : r[n]) || 0;
      return typeof o == "string" ? o.trim() : o;
    }
  }
  measureInstanceViewportBox(t, { transformPagePoint: n }) {
    return Q1(t, n);
  }
  build(t, n, r) {
    bh(t, n, r.transformTemplate);
  }
  scrapeMotionValuesFromProps(t, n, r) {
    return Nh(t, n, r);
  }
}
class zR extends uS {
  constructor() {
    super(...arguments),
      (this.type = "svg"),
      (this.isSVGTag = !1),
      (this.measureInstanceViewportBox = Ce);
  }
  getBaseTargetFromProps(t, n) {
    return t[n];
  }
  readValueFromInstance(t, n) {
    if (zr.has(n)) {
      const r = $h(n);
      return (r && r.default) || 0;
    }
    return (n = Zw.has(n) ? n : vh(n)), t.getAttribute(n);
  }
  scrapeMotionValuesFromProps(t, n, r) {
    return Jw(t, n, r);
  }
  build(t, n, r) {
    kh(t, n, this.isSVGTag, r.transformTemplate);
  }
  renderInstance(t, n, r, o) {
    Qw(t, n, r, o);
  }
  mount(t) {
    (this.isSVGTag = Th(t.tagName)), super.mount(t);
  }
}
const $R = (e, t) => (wh(e) ? new zR(t) : new FR(t, { allowProjection: e !== v.Fragment })),
  jR = dP({ ...cA, ...MR, ...xR, ...AR }, $R),
  cS = TN(jR);
function Hh(e) {
  const t = fh(() => Bo(e)),
    { isStatic: n } = v.useContext(au);
  if (n) {
    const [, r] = v.useState(e);
    v.useEffect(() => t.on("change", r), []);
  }
  return t;
}
function fS(e, t) {
  const n = Hh(t()),
    r = () => n.set(t());
  return (
    r(),
    ph(() => {
      const o = () => ae.preRender(r, !1, !0),
        i = e.map((s) => s.on("change", o));
      return () => {
        i.forEach((s) => s()), Cn(r);
      };
    }),
    n
  );
}
function ty(e) {
  return typeof e == "number" ? e : parseFloat(e);
}
function BR(e, t = {}) {
  const { isStatic: n } = v.useContext(au),
    r = v.useRef(null),
    o = Hh(Re(e) ? ty(e.get()) : e),
    i = v.useRef(o.get()),
    s = v.useRef(() => {}),
    a = () => {
      const u = r.current;
      u && u.time === 0 && u.sample(Me.delta),
        l(),
        (r.current = OM({
          keyframes: [o.get(), i.current],
          velocity: o.getVelocity(),
          type: "spring",
          restDelta: 0.001,
          restSpeed: 0.01,
          ...t,
          onUpdate: s.current,
        }));
    },
    l = () => {
      r.current && r.current.stop();
    };
  return (
    v.useInsertionEffect(
      () =>
        o.attach(
          (u, c) => (n ? c(u) : ((i.current = u), (s.current = c), ae.update(a), o.get())),
          l,
        ),
      [JSON.stringify(t)],
    ),
    ph(() => {
      if (Re(e)) return e.on("change", (u) => o.set(ty(u)));
    }, [o]),
    o
  );
}
const UR = (e) => e && typeof e == "object" && e.mix,
  HR = (e) => (UR(e) ? e.mix : void 0);
function WR(...e) {
  const t = !Array.isArray(e[0]),
    n = t ? 0 : -1,
    r = e[0 + n],
    o = e[1 + n],
    i = e[2 + n],
    s = e[3 + n],
    a = $1(o, i, { mixer: HR(i[0]), ...s });
  return t ? a(r) : a;
}
function GR(e) {
  ($i.current = []), e();
  const t = fS($i.current, e);
  return ($i.current = void 0), t;
}
function ny(e, t, n, r) {
  if (typeof e == "function") return GR(e);
  const o = typeof t == "function" ? t : WR(t, n, r);
  return Array.isArray(e) ? ry(e, o) : ry([e], ([i]) => o(i));
}
function ry(e, t) {
  const n = fh(() => []);
  return fS(e, () => {
    n.length = 0;
    const r = e.length;
    for (let o = 0; o < r; o++) n[o] = e[o].get();
    return t(n);
  });
}
const KR = Sx(
    "flex h-full w-max items-end gap-2 rounded-lg p-2 transition-all duration-300 ease-out",
  ),
  dS = L.forwardRef(({ className: e, children: t, ...n }, r) => {
    const o = Hh(1 / 0);
    return N.jsx(cS.div, {
      ref: r,
      onMouseMove: (i) => o.set(i.pageX),
      onMouseLeave: () => o.set(1 / 0),
      ...n,
      className: le(KR({ className: e }), "z-50"),
      children: L.Children.map(t, (i) => L.cloneElement(i, { mouseX: o })),
    });
  });
dS.displayName = "Dock";
const Ha = ({ mouseX: e, className: t, children: n, ...r }) => {
  const o = v.useRef(null),
    i = ny(e, (l) => {
      var c;
      const u = ((c = o.current) == null ? void 0 : c.getBoundingClientRect()) ?? {
        x: 0,
        width: 0,
      };
      return l - u.x - u.width / 2;
    }),
    s = ny(i, [-150, 0, 150], [40, 80, 40]),
    a = BR(s, { mass: 0.1, stiffness: 150, damping: 12 });
  return N.jsx(cS.div, {
    ref: o,
    style: { width: a },
    className: le(
      "flex aspect-square items-center justify-center rounded-full bg-neutral-100/50 dark:bg-neutral-800/50",
      t,
    ),
    ...r,
    children: n,
  });
};
Ha.displayName = "DockIcon";
const hS = L.forwardRef(
  (
    {
      shimmerColor: e = "#ffffff",
      shimmerSize: t = "0.1em",
      shimmerDuration: n = "1.5s",
      borderRadius: r = "100px",
      background: o = "rgba(0, 0, 0, 1)",
      className: i,
      children: s,
      ...a
    },
    l,
  ) =>
    N.jsxs("button", {
      style: {
        "--shimmer-color": e,
        "--shimmer-size": t,
        "--shimmer-duration": n,
        "--background": o,
        borderRadius: r,
      },
      className: le(
        "group relative z-0 flex cursor-pointer items-center justify-center overflow-hidden whitespace-nowrap border border-white/10 px-6 py-3 text-white [background:var(--background)] [border-radius:var(--border-radius)]",
        "transform-gpu transition-transform duration-300 ease-in-out hover:scale-105",
        i,
      ),
      ref: l,
      ...a,
      children: [
        N.jsx("div", {
          className: "absolute inset-0 z-0 overflow-hidden rounded-[inherit]",
          children: N.jsx("div", {
            className: le(
              "absolute inset-0 z-0 h-full w-full animate-[shimmer_var(--shimmer-duration)_infinite] bg-gradient-to-r from-transparent via-transparent to-[var(--shimmer-color)] opacity-0 transition-opacity duration-500 group-hover:opacity-100",
              "[--shimmer-angle:-45deg]",
            ),
          }),
        }),
        N.jsx("div", { className: "relative z-10", children: s }),
      ],
    }),
);
hS.displayName = "ShimmerButton";
function $e(e) {
  if (typeof e == "string" || typeof e == "number") return "" + e;
  let t = "";
  if (Array.isArray(e))
    for (let n = 0, r; n < e.length; n++) (r = $e(e[n])) !== "" && (t += (t && " ") + r);
  else for (let n in e) e[n] && (t += (t && " ") + n);
  return t;
}
const { useDebugValue: YR } = L,
  { useSyncExternalStoreWithSelector: XR } = mx,
  ZR = (e) => e;
function pS(e, t = ZR, n) {
  const r = XR(e.subscribe, e.getState, e.getServerState || e.getInitialState, t, n);
  return YR(r), r;
}
const oy = (e, t) => {
    const n = cx(e),
      r = (o, i = t) => pS(n, o, i);
    return Object.assign(r, n), r;
  },
  QR = (e, t) => (e ? oy(e, t) : oy);
function Ie(e, t) {
  if (Object.is(e, t)) return !0;
  if (typeof e != "object" || e === null || typeof t != "object" || t === null) return !1;
  if (e instanceof Map && t instanceof Map) {
    if (e.size !== t.size) return !1;
    for (const [r, o] of e) if (!Object.is(o, t.get(r))) return !1;
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
var qR = { value: () => {} };
function pu() {
  for (var e = 0, t = arguments.length, n = {}, r; e < t; ++e) {
    if (!(r = arguments[e] + "") || r in n || /[\s.]/.test(r))
      throw new Error("illegal type: " + r);
    n[r] = [];
  }
  return new Wa(n);
}
function Wa(e) {
  this._ = e;
}
function JR(e, t) {
  return e
    .trim()
    .split(/^|\s+/)
    .map(function (n) {
      var r = "",
        o = n.indexOf(".");
      if ((o >= 0 && ((r = n.slice(o + 1)), (n = n.slice(0, o))), n && !t.hasOwnProperty(n)))
        throw new Error("unknown type: " + n);
      return { type: n, name: r };
    });
}
Wa.prototype = pu.prototype = {
  constructor: Wa,
  on: function (e, t) {
    var n = this._,
      r = JR(e + "", n),
      o,
      i = -1,
      s = r.length;
    if (arguments.length < 2) {
      for (; ++i < s; ) if ((o = (e = r[i]).type) && (o = eD(n[o], e.name))) return o;
      return;
    }
    if (t != null && typeof t != "function") throw new Error("invalid callback: " + t);
    for (; ++i < s; )
      if ((o = (e = r[i]).type)) n[o] = iy(n[o], e.name, t);
      else if (t == null) for (o in n) n[o] = iy(n[o], e.name, null);
    return this;
  },
  copy: function () {
    var e = {},
      t = this._;
    for (var n in t) e[n] = t[n].slice();
    return new Wa(e);
  },
  call: function (e, t) {
    if ((o = arguments.length - 2) > 0)
      for (var n = new Array(o), r = 0, o, i; r < o; ++r) n[r] = arguments[r + 2];
    if (!this._.hasOwnProperty(e)) throw new Error("unknown type: " + e);
    for (i = this._[e], r = 0, o = i.length; r < o; ++r) i[r].value.apply(t, n);
  },
  apply: function (e, t, n) {
    if (!this._.hasOwnProperty(e)) throw new Error("unknown type: " + e);
    for (var r = this._[e], o = 0, i = r.length; o < i; ++o) r[o].value.apply(t, n);
  },
};
function eD(e, t) {
  for (var n = 0, r = e.length, o; n < r; ++n) if ((o = e[n]).name === t) return o.value;
}
function iy(e, t, n) {
  for (var r = 0, o = e.length; r < o; ++r)
    if (e[r].name === t) {
      (e[r] = qR), (e = e.slice(0, r).concat(e.slice(r + 1)));
      break;
    }
  return n != null && e.push({ name: t, value: n }), e;
}
var Hf = "http://www.w3.org/1999/xhtml";
const sy = {
  svg: "http://www.w3.org/2000/svg",
  xhtml: Hf,
  xlink: "http://www.w3.org/1999/xlink",
  xml: "http://www.w3.org/XML/1998/namespace",
  xmlns: "http://www.w3.org/2000/xmlns/",
};
function mu(e) {
  var t = (e += ""),
    n = t.indexOf(":");
  return (
    n >= 0 && (t = e.slice(0, n)) !== "xmlns" && (e = e.slice(n + 1)),
    sy.hasOwnProperty(t) ? { space: sy[t], local: e } : e
  );
}
function tD(e) {
  return function () {
    var t = this.ownerDocument,
      n = this.namespaceURI;
    return n === Hf && t.documentElement.namespaceURI === Hf
      ? t.createElement(e)
      : t.createElementNS(n, e);
  };
}
function nD(e) {
  return function () {
    return this.ownerDocument.createElementNS(e.space, e.local);
  };
}
function mS(e) {
  var t = mu(e);
  return (t.local ? nD : tD)(t);
}
function rD() {}
function Wh(e) {
  return e == null
    ? rD
    : function () {
        return this.querySelector(e);
      };
}
function oD(e) {
  typeof e != "function" && (e = Wh(e));
  for (var t = this._groups, n = t.length, r = new Array(n), o = 0; o < n; ++o)
    for (var i = t[o], s = i.length, a = (r[o] = new Array(s)), l, u, c = 0; c < s; ++c)
      (l = i[c]) &&
        (u = e.call(l, l.__data__, c, i)) &&
        ("__data__" in l && (u.__data__ = l.__data__), (a[c] = u));
  return new mt(r, this._parents);
}
function iD(e) {
  return e == null ? [] : Array.isArray(e) ? e : Array.from(e);
}
function sD() {
  return [];
}
function gS(e) {
  return e == null
    ? sD
    : function () {
        return this.querySelectorAll(e);
      };
}
function aD(e) {
  return function () {
    return iD(e.apply(this, arguments));
  };
}
function lD(e) {
  typeof e == "function" ? (e = aD(e)) : (e = gS(e));
  for (var t = this._groups, n = t.length, r = [], o = [], i = 0; i < n; ++i)
    for (var s = t[i], a = s.length, l, u = 0; u < a; ++u)
      (l = s[u]) && (r.push(e.call(l, l.__data__, u, s)), o.push(l));
  return new mt(r, o);
}
function yS(e) {
  return function () {
    return this.matches(e);
  };
}
function vS(e) {
  return function (t) {
    return t.matches(e);
  };
}
var uD = Array.prototype.find;
function cD(e) {
  return function () {
    return uD.call(this.children, e);
  };
}
function fD() {
  return this.firstElementChild;
}
function dD(e) {
  return this.select(e == null ? fD : cD(typeof e == "function" ? e : vS(e)));
}
var hD = Array.prototype.filter;
function pD() {
  return Array.from(this.children);
}
function mD(e) {
  return function () {
    return hD.call(this.children, e);
  };
}
function gD(e) {
  return this.selectAll(e == null ? pD : mD(typeof e == "function" ? e : vS(e)));
}
function yD(e) {
  typeof e != "function" && (e = yS(e));
  for (var t = this._groups, n = t.length, r = new Array(n), o = 0; o < n; ++o)
    for (var i = t[o], s = i.length, a = (r[o] = []), l, u = 0; u < s; ++u)
      (l = i[u]) && e.call(l, l.__data__, u, i) && a.push(l);
  return new mt(r, this._parents);
}
function xS(e) {
  return new Array(e.length);
}
function vD() {
  return new mt(this._enter || this._groups.map(xS), this._parents);
}
function Tl(e, t) {
  (this.ownerDocument = e.ownerDocument),
    (this.namespaceURI = e.namespaceURI),
    (this._next = null),
    (this._parent = e),
    (this.__data__ = t);
}
Tl.prototype = {
  constructor: Tl,
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
function xD(e) {
  return function () {
    return e;
  };
}
function wD(e, t, n, r, o, i) {
  for (var s = 0, a, l = t.length, u = i.length; s < u; ++s)
    (a = t[s]) ? ((a.__data__ = i[s]), (r[s] = a)) : (n[s] = new Tl(e, i[s]));
  for (; s < l; ++s) (a = t[s]) && (o[s] = a);
}
function SD(e, t, n, r, o, i, s) {
  var a,
    l,
    u = new Map(),
    c = t.length,
    f = i.length,
    d = new Array(c),
    p;
  for (a = 0; a < c; ++a)
    (l = t[a]) &&
      ((d[a] = p = s.call(l, l.__data__, a, t) + ""), u.has(p) ? (o[a] = l) : u.set(p, l));
  for (a = 0; a < f; ++a)
    (p = s.call(e, i[a], a, i) + ""),
      (l = u.get(p)) ? ((r[a] = l), (l.__data__ = i[a]), u.delete(p)) : (n[a] = new Tl(e, i[a]));
  for (a = 0; a < c; ++a) (l = t[a]) && u.get(d[a]) === l && (o[a] = l);
}
function ED(e) {
  return e.__data__;
}
function CD(e, t) {
  if (!arguments.length) return Array.from(this, ED);
  var n = t ? SD : wD,
    r = this._parents,
    o = this._groups;
  typeof e != "function" && (e = xD(e));
  for (var i = o.length, s = new Array(i), a = new Array(i), l = new Array(i), u = 0; u < i; ++u) {
    var c = r[u],
      f = o[u],
      d = f.length,
      p = bD(e.call(c, c && c.__data__, u, r)),
      y = p.length,
      m = (a[u] = new Array(y)),
      w = (s[u] = new Array(y)),
      h = (l[u] = new Array(d));
    n(c, f, m, w, h, p, t);
    for (var g = 0, x = 0, S, E; g < y; ++g)
      if ((S = m[g])) {
        for (g >= x && (x = g + 1); !(E = w[x]) && ++x < y; );
        S._next = E || null;
      }
  }
  return (s = new mt(s, r)), (s._enter = a), (s._exit = l), s;
}
function bD(e) {
  return typeof e == "object" && "length" in e ? e : Array.from(e);
}
function kD() {
  return new mt(this._exit || this._groups.map(xS), this._parents);
}
function _D(e, t, n) {
  var r = this.enter(),
    o = this,
    i = this.exit();
  return (
    typeof e == "function" ? ((r = e(r)), r && (r = r.selection())) : (r = r.append(e + "")),
    t != null && ((o = t(o)), o && (o = o.selection())),
    n == null ? i.remove() : n(i),
    r && o ? r.merge(o).order() : o
  );
}
function TD(e) {
  for (
    var t = e.selection ? e.selection() : e,
      n = this._groups,
      r = t._groups,
      o = n.length,
      i = r.length,
      s = Math.min(o, i),
      a = new Array(o),
      l = 0;
    l < s;
    ++l
  )
    for (var u = n[l], c = r[l], f = u.length, d = (a[l] = new Array(f)), p, y = 0; y < f; ++y)
      (p = u[y] || c[y]) && (d[y] = p);
  for (; l < o; ++l) a[l] = n[l];
  return new mt(a, this._parents);
}
function ND() {
  for (var e = this._groups, t = -1, n = e.length; ++t < n; )
    for (var r = e[t], o = r.length - 1, i = r[o], s; --o >= 0; )
      (s = r[o]) &&
        (i && s.compareDocumentPosition(i) ^ 4 && i.parentNode.insertBefore(s, i), (i = s));
  return this;
}
function PD(e) {
  e || (e = MD);
  function t(f, d) {
    return f && d ? e(f.__data__, d.__data__) : !f - !d;
  }
  for (var n = this._groups, r = n.length, o = new Array(r), i = 0; i < r; ++i) {
    for (var s = n[i], a = s.length, l = (o[i] = new Array(a)), u, c = 0; c < a; ++c)
      (u = s[c]) && (l[c] = u);
    l.sort(t);
  }
  return new mt(o, this._parents).order();
}
function MD(e, t) {
  return e < t ? -1 : e > t ? 1 : e >= t ? 0 : NaN;
}
function AD() {
  var e = arguments[0];
  return (arguments[0] = this), e.apply(null, arguments), this;
}
function RD() {
  return Array.from(this);
}
function DD() {
  for (var e = this._groups, t = 0, n = e.length; t < n; ++t)
    for (var r = e[t], o = 0, i = r.length; o < i; ++o) {
      var s = r[o];
      if (s) return s;
    }
  return null;
}
function ID() {
  let e = 0;
  for (const t of this) ++e;
  return e;
}
function LD() {
  return !this.node();
}
function VD(e) {
  for (var t = this._groups, n = 0, r = t.length; n < r; ++n)
    for (var o = t[n], i = 0, s = o.length, a; i < s; ++i)
      (a = o[i]) && e.call(a, a.__data__, i, o);
  return this;
}
function OD(e) {
  return function () {
    this.removeAttribute(e);
  };
}
function FD(e) {
  return function () {
    this.removeAttributeNS(e.space, e.local);
  };
}
function zD(e, t) {
  return function () {
    this.setAttribute(e, t);
  };
}
function $D(e, t) {
  return function () {
    this.setAttributeNS(e.space, e.local, t);
  };
}
function jD(e, t) {
  return function () {
    var n = t.apply(this, arguments);
    n == null ? this.removeAttribute(e) : this.setAttribute(e, n);
  };
}
function BD(e, t) {
  return function () {
    var n = t.apply(this, arguments);
    n == null ? this.removeAttributeNS(e.space, e.local) : this.setAttributeNS(e.space, e.local, n);
  };
}
function UD(e, t) {
  var n = mu(e);
  if (arguments.length < 2) {
    var r = this.node();
    return n.local ? r.getAttributeNS(n.space, n.local) : r.getAttribute(n);
  }
  return this.each(
    (t == null
      ? n.local
        ? FD
        : OD
      : typeof t == "function"
        ? n.local
          ? BD
          : jD
        : n.local
          ? $D
          : zD)(n, t),
  );
}
function wS(e) {
  return (e.ownerDocument && e.ownerDocument.defaultView) || (e.document && e) || e.defaultView;
}
function HD(e) {
  return function () {
    this.style.removeProperty(e);
  };
}
function WD(e, t, n) {
  return function () {
    this.style.setProperty(e, t, n);
  };
}
function GD(e, t, n) {
  return function () {
    var r = t.apply(this, arguments);
    r == null ? this.style.removeProperty(e) : this.style.setProperty(e, r, n);
  };
}
function KD(e, t, n) {
  return arguments.length > 1
    ? this.each((t == null ? HD : typeof t == "function" ? GD : WD)(e, t, n ?? ""))
    : Ho(this.node(), e);
}
function Ho(e, t) {
  return e.style.getPropertyValue(t) || wS(e).getComputedStyle(e, null).getPropertyValue(t);
}
function YD(e) {
  return function () {
    delete this[e];
  };
}
function XD(e, t) {
  return function () {
    this[e] = t;
  };
}
function ZD(e, t) {
  return function () {
    var n = t.apply(this, arguments);
    n == null ? delete this[e] : (this[e] = n);
  };
}
function QD(e, t) {
  return arguments.length > 1
    ? this.each((t == null ? YD : typeof t == "function" ? ZD : XD)(e, t))
    : this.node()[e];
}
function SS(e) {
  return e.trim().split(/^|\s+/);
}
function Gh(e) {
  return e.classList || new ES(e);
}
function ES(e) {
  (this._node = e), (this._names = SS(e.getAttribute("class") || ""));
}
ES.prototype = {
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
function CS(e, t) {
  for (var n = Gh(e), r = -1, o = t.length; ++r < o; ) n.add(t[r]);
}
function bS(e, t) {
  for (var n = Gh(e), r = -1, o = t.length; ++r < o; ) n.remove(t[r]);
}
function qD(e) {
  return function () {
    CS(this, e);
  };
}
function JD(e) {
  return function () {
    bS(this, e);
  };
}
function eI(e, t) {
  return function () {
    (t.apply(this, arguments) ? CS : bS)(this, e);
  };
}
function tI(e, t) {
  var n = SS(e + "");
  if (arguments.length < 2) {
    for (var r = Gh(this.node()), o = -1, i = n.length; ++o < i; ) if (!r.contains(n[o])) return !1;
    return !0;
  }
  return this.each((typeof t == "function" ? eI : t ? qD : JD)(n, t));
}
function nI() {
  this.textContent = "";
}
function rI(e) {
  return function () {
    this.textContent = e;
  };
}
function oI(e) {
  return function () {
    var t = e.apply(this, arguments);
    this.textContent = t ?? "";
  };
}
function iI(e) {
  return arguments.length
    ? this.each(e == null ? nI : (typeof e == "function" ? oI : rI)(e))
    : this.node().textContent;
}
function sI() {
  this.innerHTML = "";
}
function aI(e) {
  return function () {
    this.innerHTML = e;
  };
}
function lI(e) {
  return function () {
    var t = e.apply(this, arguments);
    this.innerHTML = t ?? "";
  };
}
function uI(e) {
  return arguments.length
    ? this.each(e == null ? sI : (typeof e == "function" ? lI : aI)(e))
    : this.node().innerHTML;
}
function cI() {
  this.nextSibling && this.parentNode.appendChild(this);
}
function fI() {
  return this.each(cI);
}
function dI() {
  this.previousSibling && this.parentNode.insertBefore(this, this.parentNode.firstChild);
}
function hI() {
  return this.each(dI);
}
function pI(e) {
  var t = typeof e == "function" ? e : mS(e);
  return this.select(function () {
    return this.appendChild(t.apply(this, arguments));
  });
}
function mI() {
  return null;
}
function gI(e, t) {
  var n = typeof e == "function" ? e : mS(e),
    r = t == null ? mI : typeof t == "function" ? t : Wh(t);
  return this.select(function () {
    return this.insertBefore(n.apply(this, arguments), r.apply(this, arguments) || null);
  });
}
function yI() {
  var e = this.parentNode;
  e && e.removeChild(this);
}
function vI() {
  return this.each(yI);
}
function xI() {
  var e = this.cloneNode(!1),
    t = this.parentNode;
  return t ? t.insertBefore(e, this.nextSibling) : e;
}
function wI() {
  var e = this.cloneNode(!0),
    t = this.parentNode;
  return t ? t.insertBefore(e, this.nextSibling) : e;
}
function SI(e) {
  return this.select(e ? wI : xI);
}
function EI(e) {
  return arguments.length ? this.property("__data__", e) : this.node().__data__;
}
function CI(e) {
  return function (t) {
    e.call(this, t, this.__data__);
  };
}
function bI(e) {
  return e
    .trim()
    .split(/^|\s+/)
    .map(function (t) {
      var n = "",
        r = t.indexOf(".");
      return r >= 0 && ((n = t.slice(r + 1)), (t = t.slice(0, r))), { type: t, name: n };
    });
}
function kI(e) {
  return function () {
    var t = this.__on;
    if (t) {
      for (var n = 0, r = -1, o = t.length, i; n < o; ++n)
        (i = t[n]),
          (!e.type || i.type === e.type) && i.name === e.name
            ? this.removeEventListener(i.type, i.listener, i.options)
            : (t[++r] = i);
      ++r ? (t.length = r) : delete this.__on;
    }
  };
}
function _I(e, t, n) {
  return function () {
    var r = this.__on,
      o,
      i = CI(t);
    if (r) {
      for (var s = 0, a = r.length; s < a; ++s)
        if ((o = r[s]).type === e.type && o.name === e.name) {
          this.removeEventListener(o.type, o.listener, o.options),
            this.addEventListener(o.type, (o.listener = i), (o.options = n)),
            (o.value = t);
          return;
        }
    }
    this.addEventListener(e.type, i, n),
      (o = { type: e.type, name: e.name, value: t, listener: i, options: n }),
      r ? r.push(o) : (this.__on = [o]);
  };
}
function TI(e, t, n) {
  var r = bI(e + ""),
    o,
    i = r.length,
    s;
  if (arguments.length < 2) {
    var a = this.node().__on;
    if (a) {
      for (var l = 0, u = a.length, c; l < u; ++l)
        for (o = 0, c = a[l]; o < i; ++o)
          if ((s = r[o]).type === c.type && s.name === c.name) return c.value;
    }
    return;
  }
  for (a = t ? _I : kI, o = 0; o < i; ++o) this.each(a(r[o], t, n));
  return this;
}
function kS(e, t, n) {
  var r = wS(e),
    o = r.CustomEvent;
  typeof o == "function"
    ? (o = new o(t, n))
    : ((o = r.document.createEvent("Event")),
      n
        ? (o.initEvent(t, n.bubbles, n.cancelable), (o.detail = n.detail))
        : o.initEvent(t, !1, !1)),
    e.dispatchEvent(o);
}
function NI(e, t) {
  return function () {
    return kS(this, e, t);
  };
}
function PI(e, t) {
  return function () {
    return kS(this, e, t.apply(this, arguments));
  };
}
function MI(e, t) {
  return this.each((typeof t == "function" ? PI : NI)(e, t));
}
function* AI() {
  for (var e = this._groups, t = 0, n = e.length; t < n; ++t)
    for (var r = e[t], o = 0, i = r.length, s; o < i; ++o) (s = r[o]) && (yield s);
}
var _S = [null];
function mt(e, t) {
  (this._groups = e), (this._parents = t);
}
function $s() {
  return new mt([[document.documentElement]], _S);
}
function RI() {
  return this;
}
mt.prototype = $s.prototype = {
  constructor: mt,
  select: oD,
  selectAll: lD,
  selectChild: dD,
  selectChildren: gD,
  filter: yD,
  data: CD,
  enter: vD,
  exit: kD,
  join: _D,
  merge: TD,
  selection: RI,
  order: ND,
  sort: PD,
  call: AD,
  nodes: RD,
  node: DD,
  size: ID,
  empty: LD,
  each: VD,
  attr: UD,
  style: KD,
  property: QD,
  classed: tI,
  text: iI,
  html: uI,
  raise: fI,
  lower: hI,
  append: pI,
  insert: gI,
  remove: vI,
  clone: SI,
  datum: EI,
  on: TI,
  dispatch: MI,
  [Symbol.iterator]: AI,
};
function Et(e) {
  return typeof e == "string"
    ? new mt([[document.querySelector(e)]], [document.documentElement])
    : new mt([[e]], _S);
}
function DI(e) {
  let t;
  for (; (t = e.sourceEvent); ) e = t;
  return e;
}
function It(e, t) {
  if (((e = DI(e)), t === void 0 && (t = e.currentTarget), t)) {
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
      var o = t.getBoundingClientRect();
      return [e.clientX - o.left - t.clientLeft, e.clientY - o.top - t.clientTop];
    }
  }
  return [e.pageX, e.pageY];
}
const II = { passive: !1 },
  ms = { capture: !0, passive: !1 };
function wc(e) {
  e.stopImmediatePropagation();
}
function To(e) {
  e.preventDefault(), e.stopImmediatePropagation();
}
function TS(e) {
  var t = e.document.documentElement,
    n = Et(e).on("dragstart.drag", To, ms);
  "onselectstart" in t
    ? n.on("selectstart.drag", To, ms)
    : ((t.__noselect = t.style.MozUserSelect), (t.style.MozUserSelect = "none"));
}
function NS(e, t) {
  var n = e.document.documentElement,
    r = Et(e).on("dragstart.drag", null);
  t &&
    (r.on("click.drag", To, ms),
    setTimeout(function () {
      r.on("click.drag", null);
    }, 0)),
    "onselectstart" in n
      ? r.on("selectstart.drag", null)
      : ((n.style.MozUserSelect = n.__noselect), delete n.__noselect);
}
const ha = (e) => () => e;
function Wf(
  e,
  {
    sourceEvent: t,
    subject: n,
    target: r,
    identifier: o,
    active: i,
    x: s,
    y: a,
    dx: l,
    dy: u,
    dispatch: c,
  },
) {
  Object.defineProperties(this, {
    type: { value: e, enumerable: !0, configurable: !0 },
    sourceEvent: { value: t, enumerable: !0, configurable: !0 },
    subject: { value: n, enumerable: !0, configurable: !0 },
    target: { value: r, enumerable: !0, configurable: !0 },
    identifier: { value: o, enumerable: !0, configurable: !0 },
    active: { value: i, enumerable: !0, configurable: !0 },
    x: { value: s, enumerable: !0, configurable: !0 },
    y: { value: a, enumerable: !0, configurable: !0 },
    dx: { value: l, enumerable: !0, configurable: !0 },
    dy: { value: u, enumerable: !0, configurable: !0 },
    _: { value: c },
  });
}
Wf.prototype.on = function () {
  var e = this._.on.apply(this._, arguments);
  return e === this._ ? this : e;
};
function LI(e) {
  return !e.ctrlKey && !e.button;
}
function VI() {
  return this.parentNode;
}
function OI(e, t) {
  return t ?? { x: e.x, y: e.y };
}
function FI() {
  return navigator.maxTouchPoints || "ontouchstart" in this;
}
function zI() {
  var e = LI,
    t = VI,
    n = OI,
    r = FI,
    o = {},
    i = pu("start", "drag", "end"),
    s = 0,
    a,
    l,
    u,
    c,
    f = 0;
  function d(S) {
    S.on("mousedown.drag", p)
      .filter(r)
      .on("touchstart.drag", w)
      .on("touchmove.drag", h, II)
      .on("touchend.drag touchcancel.drag", g)
      .style("touch-action", "none")
      .style("-webkit-tap-highlight-color", "rgba(0,0,0,0)");
  }
  function p(S, E) {
    if (!(c || !e.call(this, S, E))) {
      var C = x(this, t.call(this, S, E), S, E, "mouse");
      C &&
        (Et(S.view).on("mousemove.drag", y, ms).on("mouseup.drag", m, ms),
        TS(S.view),
        wc(S),
        (u = !1),
        (a = S.clientX),
        (l = S.clientY),
        C("start", S));
    }
  }
  function y(S) {
    if ((To(S), !u)) {
      var E = S.clientX - a,
        C = S.clientY - l;
      u = E * E + C * C > f;
    }
    o.mouse("drag", S);
  }
  function m(S) {
    Et(S.view).on("mousemove.drag mouseup.drag", null), NS(S.view, u), To(S), o.mouse("end", S);
  }
  function w(S, E) {
    if (e.call(this, S, E)) {
      var C = S.changedTouches,
        b = t.call(this, S, E),
        _ = C.length,
        A,
        R;
      for (A = 0; A < _; ++A)
        (R = x(this, b, S, E, C[A].identifier, C[A])) && (wc(S), R("start", S, C[A]));
    }
  }
  function h(S) {
    var E = S.changedTouches,
      C = E.length,
      b,
      _;
    for (b = 0; b < C; ++b) (_ = o[E[b].identifier]) && (To(S), _("drag", S, E[b]));
  }
  function g(S) {
    var E = S.changedTouches,
      C = E.length,
      b,
      _;
    for (
      c && clearTimeout(c),
        c = setTimeout(function () {
          c = null;
        }, 500),
        b = 0;
      b < C;
      ++b
    )
      (_ = o[E[b].identifier]) && (wc(S), _("end", S, E[b]));
  }
  function x(S, E, C, b, _, A) {
    var R = i.copy(),
      z = It(A || C, E),
      F,
      j,
      k;
    if (
      (k = n.call(
        S,
        new Wf("beforestart", {
          sourceEvent: C,
          target: d,
          identifier: _,
          active: s,
          x: z[0],
          y: z[1],
          dx: 0,
          dy: 0,
          dispatch: R,
        }),
        b,
      )) != null
    )
      return (
        (F = k.x - z[0] || 0),
        (j = k.y - z[1] || 0),
        function I(M, V, P) {
          var T = z,
            D;
          switch (M) {
            case "start":
              (o[_] = I), (D = s++);
              break;
            case "end":
              delete o[_], --s;
            case "drag":
              (z = It(P || V, E)), (D = s);
              break;
          }
          R.call(
            M,
            S,
            new Wf(M, {
              sourceEvent: V,
              subject: k,
              target: d,
              identifier: _,
              active: D,
              x: z[0] + F,
              y: z[1] + j,
              dx: z[0] - T[0],
              dy: z[1] - T[1],
              dispatch: R,
            }),
            b,
          );
        }
      );
  }
  return (
    (d.filter = function (S) {
      return arguments.length ? ((e = typeof S == "function" ? S : ha(!!S)), d) : e;
    }),
    (d.container = function (S) {
      return arguments.length ? ((t = typeof S == "function" ? S : ha(S)), d) : t;
    }),
    (d.subject = function (S) {
      return arguments.length ? ((n = typeof S == "function" ? S : ha(S)), d) : n;
    }),
    (d.touchable = function (S) {
      return arguments.length ? ((r = typeof S == "function" ? S : ha(!!S)), d) : r;
    }),
    (d.on = function () {
      var S = i.on.apply(i, arguments);
      return S === i ? d : S;
    }),
    (d.clickDistance = function (S) {
      return arguments.length ? ((f = (S = +S) * S), d) : Math.sqrt(f);
    }),
    d
  );
}
function Kh(e, t, n) {
  (e.prototype = t.prototype = n), (n.constructor = e);
}
function PS(e, t) {
  var n = Object.create(e.prototype);
  for (var r in t) n[r] = t[r];
  return n;
}
function js() {}
var gs = 0.7,
  Nl = 1 / gs,
  No = "\\s*([+-]?\\d+)\\s*",
  ys = "\\s*([+-]?(?:\\d*\\.)?\\d+(?:[eE][+-]?\\d+)?)\\s*",
  en = "\\s*([+-]?(?:\\d*\\.)?\\d+(?:[eE][+-]?\\d+)?)%\\s*",
  $I = /^#([0-9a-f]{3,8})$/,
  jI = new RegExp(`^rgb\\(${No},${No},${No}\\)$`),
  BI = new RegExp(`^rgb\\(${en},${en},${en}\\)$`),
  UI = new RegExp(`^rgba\\(${No},${No},${No},${ys}\\)$`),
  HI = new RegExp(`^rgba\\(${en},${en},${en},${ys}\\)$`),
  WI = new RegExp(`^hsl\\(${ys},${en},${en}\\)$`),
  GI = new RegExp(`^hsla\\(${ys},${en},${en},${ys}\\)$`),
  ay = {
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
Kh(js, vs, {
  copy(e) {
    return Object.assign(new this.constructor(), this, e);
  },
  displayable() {
    return this.rgb().displayable();
  },
  hex: ly,
  formatHex: ly,
  formatHex8: KI,
  formatHsl: YI,
  formatRgb: uy,
  toString: uy,
});
function ly() {
  return this.rgb().formatHex();
}
function KI() {
  return this.rgb().formatHex8();
}
function YI() {
  return MS(this).formatHsl();
}
function uy() {
  return this.rgb().formatRgb();
}
function vs(e) {
  var t, n;
  return (
    (e = (e + "").trim().toLowerCase()),
    (t = $I.exec(e))
      ? ((n = t[1].length),
        (t = parseInt(t[1], 16)),
        n === 6
          ? cy(t)
          : n === 3
            ? new rt(
                ((t >> 8) & 15) | ((t >> 4) & 240),
                ((t >> 4) & 15) | (t & 240),
                ((t & 15) << 4) | (t & 15),
                1,
              )
            : n === 8
              ? pa((t >> 24) & 255, (t >> 16) & 255, (t >> 8) & 255, (t & 255) / 255)
              : n === 4
                ? pa(
                    ((t >> 12) & 15) | ((t >> 8) & 240),
                    ((t >> 8) & 15) | ((t >> 4) & 240),
                    ((t >> 4) & 15) | (t & 240),
                    (((t & 15) << 4) | (t & 15)) / 255,
                  )
                : null)
      : (t = jI.exec(e))
        ? new rt(t[1], t[2], t[3], 1)
        : (t = BI.exec(e))
          ? new rt((t[1] * 255) / 100, (t[2] * 255) / 100, (t[3] * 255) / 100, 1)
          : (t = UI.exec(e))
            ? pa(t[1], t[2], t[3], t[4])
            : (t = HI.exec(e))
              ? pa((t[1] * 255) / 100, (t[2] * 255) / 100, (t[3] * 255) / 100, t[4])
              : (t = WI.exec(e))
                ? hy(t[1], t[2] / 100, t[3] / 100, 1)
                : (t = GI.exec(e))
                  ? hy(t[1], t[2] / 100, t[3] / 100, t[4])
                  : ay.hasOwnProperty(e)
                    ? cy(ay[e])
                    : e === "transparent"
                      ? new rt(NaN, NaN, NaN, 0)
                      : null
  );
}
function cy(e) {
  return new rt((e >> 16) & 255, (e >> 8) & 255, e & 255, 1);
}
function pa(e, t, n, r) {
  return r <= 0 && (e = t = n = NaN), new rt(e, t, n, r);
}
function XI(e) {
  return (
    e instanceof js || (e = vs(e)), e ? ((e = e.rgb()), new rt(e.r, e.g, e.b, e.opacity)) : new rt()
  );
}
function Gf(e, t, n, r) {
  return arguments.length === 1 ? XI(e) : new rt(e, t, n, r ?? 1);
}
function rt(e, t, n, r) {
  (this.r = +e), (this.g = +t), (this.b = +n), (this.opacity = +r);
}
Kh(
  rt,
  Gf,
  PS(js, {
    brighter(e) {
      return (
        (e = e == null ? Nl : Math.pow(Nl, e)),
        new rt(this.r * e, this.g * e, this.b * e, this.opacity)
      );
    },
    darker(e) {
      return (
        (e = e == null ? gs : Math.pow(gs, e)),
        new rt(this.r * e, this.g * e, this.b * e, this.opacity)
      );
    },
    rgb() {
      return this;
    },
    clamp() {
      return new rt(Tr(this.r), Tr(this.g), Tr(this.b), Pl(this.opacity));
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
    hex: fy,
    formatHex: fy,
    formatHex8: ZI,
    formatRgb: dy,
    toString: dy,
  }),
);
function fy() {
  return `#${Sr(this.r)}${Sr(this.g)}${Sr(this.b)}`;
}
function ZI() {
  return `#${Sr(this.r)}${Sr(this.g)}${Sr(this.b)}${Sr((isNaN(this.opacity) ? 1 : this.opacity) * 255)}`;
}
function dy() {
  const e = Pl(this.opacity);
  return `${e === 1 ? "rgb(" : "rgba("}${Tr(this.r)}, ${Tr(this.g)}, ${Tr(this.b)}${e === 1 ? ")" : `, ${e})`}`;
}
function Pl(e) {
  return isNaN(e) ? 1 : Math.max(0, Math.min(1, e));
}
function Tr(e) {
  return Math.max(0, Math.min(255, Math.round(e) || 0));
}
function Sr(e) {
  return (e = Tr(e)), (e < 16 ? "0" : "") + e.toString(16);
}
function hy(e, t, n, r) {
  return (
    r <= 0 ? (e = t = n = NaN) : n <= 0 || n >= 1 ? (e = t = NaN) : t <= 0 && (e = NaN),
    new Vt(e, t, n, r)
  );
}
function MS(e) {
  if (e instanceof Vt) return new Vt(e.h, e.s, e.l, e.opacity);
  if ((e instanceof js || (e = vs(e)), !e)) return new Vt();
  if (e instanceof Vt) return e;
  e = e.rgb();
  var t = e.r / 255,
    n = e.g / 255,
    r = e.b / 255,
    o = Math.min(t, n, r),
    i = Math.max(t, n, r),
    s = NaN,
    a = i - o,
    l = (i + o) / 2;
  return (
    a
      ? (t === i
          ? (s = (n - r) / a + (n < r) * 6)
          : n === i
            ? (s = (r - t) / a + 2)
            : (s = (t - n) / a + 4),
        (a /= l < 0.5 ? i + o : 2 - i - o),
        (s *= 60))
      : (a = l > 0 && l < 1 ? 0 : s),
    new Vt(s, a, l, e.opacity)
  );
}
function QI(e, t, n, r) {
  return arguments.length === 1 ? MS(e) : new Vt(e, t, n, r ?? 1);
}
function Vt(e, t, n, r) {
  (this.h = +e), (this.s = +t), (this.l = +n), (this.opacity = +r);
}
Kh(
  Vt,
  QI,
  PS(js, {
    brighter(e) {
      return (
        (e = e == null ? Nl : Math.pow(Nl, e)), new Vt(this.h, this.s, this.l * e, this.opacity)
      );
    },
    darker(e) {
      return (
        (e = e == null ? gs : Math.pow(gs, e)), new Vt(this.h, this.s, this.l * e, this.opacity)
      );
    },
    rgb() {
      var e = (this.h % 360) + (this.h < 0) * 360,
        t = isNaN(e) || isNaN(this.s) ? 0 : this.s,
        n = this.l,
        r = n + (n < 0.5 ? n : 1 - n) * t,
        o = 2 * n - r;
      return new rt(
        Sc(e >= 240 ? e - 240 : e + 120, o, r),
        Sc(e, o, r),
        Sc(e < 120 ? e + 240 : e - 120, o, r),
        this.opacity,
      );
    },
    clamp() {
      return new Vt(py(this.h), ma(this.s), ma(this.l), Pl(this.opacity));
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
      const e = Pl(this.opacity);
      return `${e === 1 ? "hsl(" : "hsla("}${py(this.h)}, ${ma(this.s) * 100}%, ${ma(this.l) * 100}%${e === 1 ? ")" : `, ${e})`}`;
    },
  }),
);
function py(e) {
  return (e = (e || 0) % 360), e < 0 ? e + 360 : e;
}
function ma(e) {
  return Math.max(0, Math.min(1, e || 0));
}
function Sc(e, t, n) {
  return (
    (e < 60 ? t + ((n - t) * e) / 60 : e < 180 ? n : e < 240 ? t + ((n - t) * (240 - e)) / 60 : t) *
    255
  );
}
const AS = (e) => () => e;
function qI(e, t) {
  return function (n) {
    return e + n * t;
  };
}
function JI(e, t, n) {
  return (
    (e = Math.pow(e, n)),
    (t = Math.pow(t, n) - e),
    (n = 1 / n),
    function (r) {
      return Math.pow(e + r * t, n);
    }
  );
}
function e3(e) {
  return (e = +e) == 1
    ? RS
    : function (t, n) {
        return n - t ? JI(t, n, e) : AS(isNaN(t) ? n : t);
      };
}
function RS(e, t) {
  var n = t - e;
  return n ? qI(e, n) : AS(isNaN(e) ? t : e);
}
const my = (function e(t) {
  var n = e3(t);
  function r(o, i) {
    var s = n((o = Gf(o)).r, (i = Gf(i)).r),
      a = n(o.g, i.g),
      l = n(o.b, i.b),
      u = RS(o.opacity, i.opacity);
    return function (c) {
      return (o.r = s(c)), (o.g = a(c)), (o.b = l(c)), (o.opacity = u(c)), o + "";
    };
  }
  return (r.gamma = e), r;
})(1);
function Vn(e, t) {
  return (
    (e = +e),
    (t = +t),
    function (n) {
      return e * (1 - n) + t * n;
    }
  );
}
var Kf = /[-+]?(?:\d+\.?\d*|\.?\d+)(?:[eE][-+]?\d+)?/g,
  Ec = new RegExp(Kf.source, "g");
function t3(e) {
  return function () {
    return e;
  };
}
function n3(e) {
  return function (t) {
    return e(t) + "";
  };
}
function r3(e, t) {
  var n = (Kf.lastIndex = Ec.lastIndex = 0),
    r,
    o,
    i,
    s = -1,
    a = [],
    l = [];
  for (e = e + "", t = t + ""; (r = Kf.exec(e)) && (o = Ec.exec(t)); )
    (i = o.index) > n && ((i = t.slice(n, i)), a[s] ? (a[s] += i) : (a[++s] = i)),
      (r = r[0]) === (o = o[0])
        ? a[s]
          ? (a[s] += o)
          : (a[++s] = o)
        : ((a[++s] = null), l.push({ i: s, x: Vn(r, o) })),
      (n = Ec.lastIndex);
  return (
    n < t.length && ((i = t.slice(n)), a[s] ? (a[s] += i) : (a[++s] = i)),
    a.length < 2
      ? l[0]
        ? n3(l[0].x)
        : t3(t)
      : ((t = l.length),
        function (u) {
          for (var c = 0, f; c < t; ++c) a[(f = l[c]).i] = f.x(u);
          return a.join("");
        })
  );
}
var gy = 180 / Math.PI,
  Yf = { translateX: 0, translateY: 0, rotate: 0, skewX: 0, scaleX: 1, scaleY: 1 };
function DS(e, t, n, r, o, i) {
  var s, a, l;
  return (
    (s = Math.sqrt(e * e + t * t)) && ((e /= s), (t /= s)),
    (l = e * n + t * r) && ((n -= e * l), (r -= t * l)),
    (a = Math.sqrt(n * n + r * r)) && ((n /= a), (r /= a), (l /= a)),
    e * r < t * n && ((e = -e), (t = -t), (l = -l), (s = -s)),
    {
      translateX: o,
      translateY: i,
      rotate: Math.atan2(t, e) * gy,
      skewX: Math.atan(l) * gy,
      scaleX: s,
      scaleY: a,
    }
  );
}
var ga;
function o3(e) {
  const t = new (typeof DOMMatrix == "function" ? DOMMatrix : WebKitCSSMatrix)(e + "");
  return t.isIdentity ? Yf : DS(t.a, t.b, t.c, t.d, t.e, t.f);
}
function i3(e) {
  return e == null ||
    (ga || (ga = document.createElementNS("http://www.w3.org/2000/svg", "g")),
    ga.setAttribute("transform", e),
    !(e = ga.transform.baseVal.consolidate()))
    ? Yf
    : ((e = e.matrix), DS(e.a, e.b, e.c, e.d, e.e, e.f));
}
function IS(e, t, n, r) {
  function o(u) {
    return u.length ? u.pop() + " " : "";
  }
  function i(u, c, f, d, p, y) {
    if (u !== f || c !== d) {
      var m = p.push("translate(", null, t, null, n);
      y.push({ i: m - 4, x: Vn(u, f) }, { i: m - 2, x: Vn(c, d) });
    } else (f || d) && p.push("translate(" + f + t + d + n);
  }
  function s(u, c, f, d) {
    u !== c
      ? (u - c > 180 ? (c += 360) : c - u > 180 && (u += 360),
        d.push({ i: f.push(o(f) + "rotate(", null, r) - 2, x: Vn(u, c) }))
      : c && f.push(o(f) + "rotate(" + c + r);
  }
  function a(u, c, f, d) {
    u !== c
      ? d.push({ i: f.push(o(f) + "skewX(", null, r) - 2, x: Vn(u, c) })
      : c && f.push(o(f) + "skewX(" + c + r);
  }
  function l(u, c, f, d, p, y) {
    if (u !== f || c !== d) {
      var m = p.push(o(p) + "scale(", null, ",", null, ")");
      y.push({ i: m - 4, x: Vn(u, f) }, { i: m - 2, x: Vn(c, d) });
    } else (f !== 1 || d !== 1) && p.push(o(p) + "scale(" + f + "," + d + ")");
  }
  return function (u, c) {
    var f = [],
      d = [];
    return (
      (u = e(u)),
      (c = e(c)),
      i(u.translateX, u.translateY, c.translateX, c.translateY, f, d),
      s(u.rotate, c.rotate, f, d),
      a(u.skewX, c.skewX, f, d),
      l(u.scaleX, u.scaleY, c.scaleX, c.scaleY, f, d),
      (u = c = null),
      function (p) {
        for (var y = -1, m = d.length, w; ++y < m; ) f[(w = d[y]).i] = w.x(p);
        return f.join("");
      }
    );
  };
}
var s3 = IS(o3, "px, ", "px)", "deg)"),
  a3 = IS(i3, ", ", ")", ")"),
  l3 = 1e-12;
function yy(e) {
  return ((e = Math.exp(e)) + 1 / e) / 2;
}
function u3(e) {
  return ((e = Math.exp(e)) - 1 / e) / 2;
}
function c3(e) {
  return ((e = Math.exp(2 * e)) - 1) / (e + 1);
}
const f3 = (function e(t, n, r) {
  function o(i, s) {
    var a = i[0],
      l = i[1],
      u = i[2],
      c = s[0],
      f = s[1],
      d = s[2],
      p = c - a,
      y = f - l,
      m = p * p + y * y,
      w,
      h;
    if (m < l3)
      (h = Math.log(d / u) / t),
        (w = function (b) {
          return [a + b * p, l + b * y, u * Math.exp(t * b * h)];
        });
    else {
      var g = Math.sqrt(m),
        x = (d * d - u * u + r * m) / (2 * u * n * g),
        S = (d * d - u * u - r * m) / (2 * d * n * g),
        E = Math.log(Math.sqrt(x * x + 1) - x),
        C = Math.log(Math.sqrt(S * S + 1) - S);
      (h = (C - E) / t),
        (w = function (b) {
          var _ = b * h,
            A = yy(E),
            R = (u / (n * g)) * (A * c3(t * _ + E) - u3(E));
          return [a + R * p, l + R * y, (u * A) / yy(t * _ + E)];
        });
    }
    return (w.duration = (h * 1e3 * t) / Math.SQRT2), w;
  }
  return (
    (o.rho = function (i) {
      var s = Math.max(0.001, +i),
        a = s * s,
        l = a * a;
      return e(s, a, l);
    }),
    o
  );
})(Math.SQRT2, 2, 4);
var Wo = 0,
  Ti = 0,
  mi = 0,
  LS = 1e3,
  Ml,
  Ni,
  Al = 0,
  Lr = 0,
  gu = 0,
  xs = typeof performance == "object" && performance.now ? performance : Date,
  VS =
    typeof window == "object" && window.requestAnimationFrame
      ? window.requestAnimationFrame.bind(window)
      : function (e) {
          setTimeout(e, 17);
        };
function Yh() {
  return Lr || (VS(d3), (Lr = xs.now() + gu));
}
function d3() {
  Lr = 0;
}
function Rl() {
  this._call = this._time = this._next = null;
}
Rl.prototype = OS.prototype = {
  constructor: Rl,
  restart: function (e, t, n) {
    if (typeof e != "function") throw new TypeError("callback is not a function");
    (n = (n == null ? Yh() : +n) + (t == null ? 0 : +t)),
      !this._next && Ni !== this && (Ni ? (Ni._next = this) : (Ml = this), (Ni = this)),
      (this._call = e),
      (this._time = n),
      Xf();
  },
  stop: function () {
    this._call && ((this._call = null), (this._time = 1 / 0), Xf());
  },
};
function OS(e, t, n) {
  var r = new Rl();
  return r.restart(e, t, n), r;
}
function h3() {
  Yh(), ++Wo;
  for (var e = Ml, t; e; ) (t = Lr - e._time) >= 0 && e._call.call(void 0, t), (e = e._next);
  --Wo;
}
function vy() {
  (Lr = (Al = xs.now()) + gu), (Wo = Ti = 0);
  try {
    h3();
  } finally {
    (Wo = 0), m3(), (Lr = 0);
  }
}
function p3() {
  var e = xs.now(),
    t = e - Al;
  t > LS && ((gu -= t), (Al = e));
}
function m3() {
  for (var e, t = Ml, n, r = 1 / 0; t; )
    t._call
      ? (r > t._time && (r = t._time), (e = t), (t = t._next))
      : ((n = t._next), (t._next = null), (t = e ? (e._next = n) : (Ml = n)));
  (Ni = e), Xf(r);
}
function Xf(e) {
  if (!Wo) {
    Ti && (Ti = clearTimeout(Ti));
    var t = e - Lr;
    t > 24
      ? (e < 1 / 0 && (Ti = setTimeout(vy, e - xs.now() - gu)), mi && (mi = clearInterval(mi)))
      : (mi || ((Al = xs.now()), (mi = setInterval(p3, LS))), (Wo = 1), VS(vy));
  }
}
function xy(e, t, n) {
  var r = new Rl();
  return (
    (t = t == null ? 0 : +t),
    r.restart(
      (o) => {
        r.stop(), e(o + t);
      },
      t,
      n,
    ),
    r
  );
}
var g3 = pu("start", "end", "cancel", "interrupt"),
  y3 = [],
  FS = 0,
  wy = 1,
  Zf = 2,
  Ga = 3,
  Sy = 4,
  Qf = 5,
  Ka = 6;
function yu(e, t, n, r, o, i) {
  var s = e.__transition;
  if (!s) e.__transition = {};
  else if (n in s) return;
  v3(e, n, {
    name: t,
    index: r,
    group: o,
    on: g3,
    tween: y3,
    time: i.time,
    delay: i.delay,
    duration: i.duration,
    ease: i.ease,
    timer: null,
    state: FS,
  });
}
function Xh(e, t) {
  var n = Bt(e, t);
  if (n.state > FS) throw new Error("too late; already scheduled");
  return n;
}
function nn(e, t) {
  var n = Bt(e, t);
  if (n.state > Ga) throw new Error("too late; already running");
  return n;
}
function Bt(e, t) {
  var n = e.__transition;
  if (!n || !(n = n[t])) throw new Error("transition not found");
  return n;
}
function v3(e, t, n) {
  var r = e.__transition,
    o;
  (r[t] = n), (n.timer = OS(i, 0, n.time));
  function i(u) {
    (n.state = wy), n.timer.restart(s, n.delay, n.time), n.delay <= u && s(u - n.delay);
  }
  function s(u) {
    var c, f, d, p;
    if (n.state !== wy) return l();
    for (c in r)
      if (((p = r[c]), p.name === n.name)) {
        if (p.state === Ga) return xy(s);
        p.state === Sy
          ? ((p.state = Ka),
            p.timer.stop(),
            p.on.call("interrupt", e, e.__data__, p.index, p.group),
            delete r[c])
          : +c < t &&
            ((p.state = Ka),
            p.timer.stop(),
            p.on.call("cancel", e, e.__data__, p.index, p.group),
            delete r[c]);
      }
    if (
      (xy(function () {
        n.state === Ga && ((n.state = Sy), n.timer.restart(a, n.delay, n.time), a(u));
      }),
      (n.state = Zf),
      n.on.call("start", e, e.__data__, n.index, n.group),
      n.state === Zf)
    ) {
      for (n.state = Ga, o = new Array((d = n.tween.length)), c = 0, f = -1; c < d; ++c)
        (p = n.tween[c].value.call(e, e.__data__, n.index, n.group)) && (o[++f] = p);
      o.length = f + 1;
    }
  }
  function a(u) {
    for (
      var c =
          u < n.duration
            ? n.ease.call(null, u / n.duration)
            : (n.timer.restart(l), (n.state = Qf), 1),
        f = -1,
        d = o.length;
      ++f < d;

    )
      o[f].call(e, c);
    n.state === Qf && (n.on.call("end", e, e.__data__, n.index, n.group), l());
  }
  function l() {
    (n.state = Ka), n.timer.stop(), delete r[t];
    for (var u in r) return;
    delete e.__transition;
  }
}
function Ya(e, t) {
  var n = e.__transition,
    r,
    o,
    i = !0,
    s;
  if (n) {
    t = t == null ? null : t + "";
    for (s in n) {
      if ((r = n[s]).name !== t) {
        i = !1;
        continue;
      }
      (o = r.state > Zf && r.state < Qf),
        (r.state = Ka),
        r.timer.stop(),
        r.on.call(o ? "interrupt" : "cancel", e, e.__data__, r.index, r.group),
        delete n[s];
    }
    i && delete e.__transition;
  }
}
function x3(e) {
  return this.each(function () {
    Ya(this, e);
  });
}
function w3(e, t) {
  var n, r;
  return function () {
    var o = nn(this, e),
      i = o.tween;
    if (i !== n) {
      r = n = i;
      for (var s = 0, a = r.length; s < a; ++s)
        if (r[s].name === t) {
          (r = r.slice()), r.splice(s, 1);
          break;
        }
    }
    o.tween = r;
  };
}
function S3(e, t, n) {
  var r, o;
  if (typeof n != "function") throw new Error();
  return function () {
    var i = nn(this, e),
      s = i.tween;
    if (s !== r) {
      o = (r = s).slice();
      for (var a = { name: t, value: n }, l = 0, u = o.length; l < u; ++l)
        if (o[l].name === t) {
          o[l] = a;
          break;
        }
      l === u && o.push(a);
    }
    i.tween = o;
  };
}
function E3(e, t) {
  var n = this._id;
  if (((e += ""), arguments.length < 2)) {
    for (var r = Bt(this.node(), n).tween, o = 0, i = r.length, s; o < i; ++o)
      if ((s = r[o]).name === e) return s.value;
    return null;
  }
  return this.each((t == null ? w3 : S3)(n, e, t));
}
function Zh(e, t, n) {
  var r = e._id;
  return (
    e.each(function () {
      var o = nn(this, r);
      (o.value || (o.value = {}))[t] = n.apply(this, arguments);
    }),
    function (o) {
      return Bt(o, r).value[t];
    }
  );
}
function zS(e, t) {
  var n;
  return (typeof t == "number" ? Vn : t instanceof vs ? my : (n = vs(t)) ? ((t = n), my) : r3)(
    e,
    t,
  );
}
function C3(e) {
  return function () {
    this.removeAttribute(e);
  };
}
function b3(e) {
  return function () {
    this.removeAttributeNS(e.space, e.local);
  };
}
function k3(e, t, n) {
  var r,
    o = n + "",
    i;
  return function () {
    var s = this.getAttribute(e);
    return s === o ? null : s === r ? i : (i = t((r = s), n));
  };
}
function _3(e, t, n) {
  var r,
    o = n + "",
    i;
  return function () {
    var s = this.getAttributeNS(e.space, e.local);
    return s === o ? null : s === r ? i : (i = t((r = s), n));
  };
}
function T3(e, t, n) {
  var r, o, i;
  return function () {
    var s,
      a = n(this),
      l;
    return a == null
      ? void this.removeAttribute(e)
      : ((s = this.getAttribute(e)),
        (l = a + ""),
        s === l ? null : s === r && l === o ? i : ((o = l), (i = t((r = s), a))));
  };
}
function N3(e, t, n) {
  var r, o, i;
  return function () {
    var s,
      a = n(this),
      l;
    return a == null
      ? void this.removeAttributeNS(e.space, e.local)
      : ((s = this.getAttributeNS(e.space, e.local)),
        (l = a + ""),
        s === l ? null : s === r && l === o ? i : ((o = l), (i = t((r = s), a))));
  };
}
function P3(e, t) {
  var n = mu(e),
    r = n === "transform" ? a3 : zS;
  return this.attrTween(
    e,
    typeof t == "function"
      ? (n.local ? N3 : T3)(n, r, Zh(this, "attr." + e, t))
      : t == null
        ? (n.local ? b3 : C3)(n)
        : (n.local ? _3 : k3)(n, r, t),
  );
}
function M3(e, t) {
  return function (n) {
    this.setAttribute(e, t.call(this, n));
  };
}
function A3(e, t) {
  return function (n) {
    this.setAttributeNS(e.space, e.local, t.call(this, n));
  };
}
function R3(e, t) {
  var n, r;
  function o() {
    var i = t.apply(this, arguments);
    return i !== r && (n = (r = i) && A3(e, i)), n;
  }
  return (o._value = t), o;
}
function D3(e, t) {
  var n, r;
  function o() {
    var i = t.apply(this, arguments);
    return i !== r && (n = (r = i) && M3(e, i)), n;
  }
  return (o._value = t), o;
}
function I3(e, t) {
  var n = "attr." + e;
  if (arguments.length < 2) return (n = this.tween(n)) && n._value;
  if (t == null) return this.tween(n, null);
  if (typeof t != "function") throw new Error();
  var r = mu(e);
  return this.tween(n, (r.local ? R3 : D3)(r, t));
}
function L3(e, t) {
  return function () {
    Xh(this, e).delay = +t.apply(this, arguments);
  };
}
function V3(e, t) {
  return (
    (t = +t),
    function () {
      Xh(this, e).delay = t;
    }
  );
}
function O3(e) {
  var t = this._id;
  return arguments.length
    ? this.each((typeof e == "function" ? L3 : V3)(t, e))
    : Bt(this.node(), t).delay;
}
function F3(e, t) {
  return function () {
    nn(this, e).duration = +t.apply(this, arguments);
  };
}
function z3(e, t) {
  return (
    (t = +t),
    function () {
      nn(this, e).duration = t;
    }
  );
}
function $3(e) {
  var t = this._id;
  return arguments.length
    ? this.each((typeof e == "function" ? F3 : z3)(t, e))
    : Bt(this.node(), t).duration;
}
function j3(e, t) {
  if (typeof t != "function") throw new Error();
  return function () {
    nn(this, e).ease = t;
  };
}
function B3(e) {
  var t = this._id;
  return arguments.length ? this.each(j3(t, e)) : Bt(this.node(), t).ease;
}
function U3(e, t) {
  return function () {
    var n = t.apply(this, arguments);
    if (typeof n != "function") throw new Error();
    nn(this, e).ease = n;
  };
}
function H3(e) {
  if (typeof e != "function") throw new Error();
  return this.each(U3(this._id, e));
}
function W3(e) {
  typeof e != "function" && (e = yS(e));
  for (var t = this._groups, n = t.length, r = new Array(n), o = 0; o < n; ++o)
    for (var i = t[o], s = i.length, a = (r[o] = []), l, u = 0; u < s; ++u)
      (l = i[u]) && e.call(l, l.__data__, u, i) && a.push(l);
  return new kn(r, this._parents, this._name, this._id);
}
function G3(e) {
  if (e._id !== this._id) throw new Error();
  for (
    var t = this._groups,
      n = e._groups,
      r = t.length,
      o = n.length,
      i = Math.min(r, o),
      s = new Array(r),
      a = 0;
    a < i;
    ++a
  )
    for (var l = t[a], u = n[a], c = l.length, f = (s[a] = new Array(c)), d, p = 0; p < c; ++p)
      (d = l[p] || u[p]) && (f[p] = d);
  for (; a < r; ++a) s[a] = t[a];
  return new kn(s, this._parents, this._name, this._id);
}
function K3(e) {
  return (e + "")
    .trim()
    .split(/^|\s+/)
    .every(function (t) {
      var n = t.indexOf(".");
      return n >= 0 && (t = t.slice(0, n)), !t || t === "start";
    });
}
function Y3(e, t, n) {
  var r,
    o,
    i = K3(t) ? Xh : nn;
  return function () {
    var s = i(this, e),
      a = s.on;
    a !== r && (o = (r = a).copy()).on(t, n), (s.on = o);
  };
}
function X3(e, t) {
  var n = this._id;
  return arguments.length < 2 ? Bt(this.node(), n).on.on(e) : this.each(Y3(n, e, t));
}
function Z3(e) {
  return function () {
    var t = this.parentNode;
    for (var n in this.__transition) if (+n !== e) return;
    t && t.removeChild(this);
  };
}
function Q3() {
  return this.on("end.remove", Z3(this._id));
}
function q3(e) {
  var t = this._name,
    n = this._id;
  typeof e != "function" && (e = Wh(e));
  for (var r = this._groups, o = r.length, i = new Array(o), s = 0; s < o; ++s)
    for (var a = r[s], l = a.length, u = (i[s] = new Array(l)), c, f, d = 0; d < l; ++d)
      (c = a[d]) &&
        (f = e.call(c, c.__data__, d, a)) &&
        ("__data__" in c && (f.__data__ = c.__data__), (u[d] = f), yu(u[d], t, n, d, u, Bt(c, n)));
  return new kn(i, this._parents, t, n);
}
function J3(e) {
  var t = this._name,
    n = this._id;
  typeof e != "function" && (e = gS(e));
  for (var r = this._groups, o = r.length, i = [], s = [], a = 0; a < o; ++a)
    for (var l = r[a], u = l.length, c, f = 0; f < u; ++f)
      if ((c = l[f])) {
        for (var d = e.call(c, c.__data__, f, l), p, y = Bt(c, n), m = 0, w = d.length; m < w; ++m)
          (p = d[m]) && yu(p, t, n, m, d, y);
        i.push(d), s.push(c);
      }
  return new kn(i, s, t, n);
}
var eL = $s.prototype.constructor;
function tL() {
  return new eL(this._groups, this._parents);
}
function nL(e, t) {
  var n, r, o;
  return function () {
    var i = Ho(this, e),
      s = (this.style.removeProperty(e), Ho(this, e));
    return i === s ? null : i === n && s === r ? o : (o = t((n = i), (r = s)));
  };
}
function $S(e) {
  return function () {
    this.style.removeProperty(e);
  };
}
function rL(e, t, n) {
  var r,
    o = n + "",
    i;
  return function () {
    var s = Ho(this, e);
    return s === o ? null : s === r ? i : (i = t((r = s), n));
  };
}
function oL(e, t, n) {
  var r, o, i;
  return function () {
    var s = Ho(this, e),
      a = n(this),
      l = a + "";
    return (
      a == null && (l = a = (this.style.removeProperty(e), Ho(this, e))),
      s === l ? null : s === r && l === o ? i : ((o = l), (i = t((r = s), a)))
    );
  };
}
function iL(e, t) {
  var n,
    r,
    o,
    i = "style." + t,
    s = "end." + i,
    a;
  return function () {
    var l = nn(this, e),
      u = l.on,
      c = l.value[i] == null ? a || (a = $S(t)) : void 0;
    (u !== n || o !== c) && (r = (n = u).copy()).on(s, (o = c)), (l.on = r);
  };
}
function sL(e, t, n) {
  var r = (e += "") == "transform" ? s3 : zS;
  return t == null
    ? this.styleTween(e, nL(e, r)).on("end.style." + e, $S(e))
    : typeof t == "function"
      ? this.styleTween(e, oL(e, r, Zh(this, "style." + e, t))).each(iL(this._id, e))
      : this.styleTween(e, rL(e, r, t), n).on("end.style." + e, null);
}
function aL(e, t, n) {
  return function (r) {
    this.style.setProperty(e, t.call(this, r), n);
  };
}
function lL(e, t, n) {
  var r, o;
  function i() {
    var s = t.apply(this, arguments);
    return s !== o && (r = (o = s) && aL(e, s, n)), r;
  }
  return (i._value = t), i;
}
function uL(e, t, n) {
  var r = "style." + (e += "");
  if (arguments.length < 2) return (r = this.tween(r)) && r._value;
  if (t == null) return this.tween(r, null);
  if (typeof t != "function") throw new Error();
  return this.tween(r, lL(e, t, n ?? ""));
}
function cL(e) {
  return function () {
    this.textContent = e;
  };
}
function fL(e) {
  return function () {
    var t = e(this);
    this.textContent = t ?? "";
  };
}
function dL(e) {
  return this.tween(
    "text",
    typeof e == "function" ? fL(Zh(this, "text", e)) : cL(e == null ? "" : e + ""),
  );
}
function hL(e) {
  return function (t) {
    this.textContent = e.call(this, t);
  };
}
function pL(e) {
  var t, n;
  function r() {
    var o = e.apply(this, arguments);
    return o !== n && (t = (n = o) && hL(o)), t;
  }
  return (r._value = e), r;
}
function mL(e) {
  var t = "text";
  if (arguments.length < 1) return (t = this.tween(t)) && t._value;
  if (e == null) return this.tween(t, null);
  if (typeof e != "function") throw new Error();
  return this.tween(t, pL(e));
}
function gL() {
  for (
    var e = this._name, t = this._id, n = jS(), r = this._groups, o = r.length, i = 0;
    i < o;
    ++i
  )
    for (var s = r[i], a = s.length, l, u = 0; u < a; ++u)
      if ((l = s[u])) {
        var c = Bt(l, t);
        yu(l, e, n, u, s, {
          time: c.time + c.delay + c.duration,
          delay: 0,
          duration: c.duration,
          ease: c.ease,
        });
      }
  return new kn(r, this._parents, e, n);
}
function yL() {
  var e,
    t,
    n = this,
    r = n._id,
    o = n.size();
  return new Promise(function (i, s) {
    var a = { value: s },
      l = {
        value: function () {
          --o === 0 && i();
        },
      };
    n.each(function () {
      var u = nn(this, r),
        c = u.on;
      c !== e && ((t = (e = c).copy()), t._.cancel.push(a), t._.interrupt.push(a), t._.end.push(l)),
        (u.on = t);
    }),
      o === 0 && i();
  });
}
var vL = 0;
function kn(e, t, n, r) {
  (this._groups = e), (this._parents = t), (this._name = n), (this._id = r);
}
function jS() {
  return ++vL;
}
var ln = $s.prototype;
kn.prototype = {
  constructor: kn,
  select: q3,
  selectAll: J3,
  selectChild: ln.selectChild,
  selectChildren: ln.selectChildren,
  filter: W3,
  merge: G3,
  selection: tL,
  transition: gL,
  call: ln.call,
  nodes: ln.nodes,
  node: ln.node,
  size: ln.size,
  empty: ln.empty,
  each: ln.each,
  on: X3,
  attr: P3,
  attrTween: I3,
  style: sL,
  styleTween: uL,
  text: dL,
  textTween: mL,
  remove: Q3,
  tween: E3,
  delay: O3,
  duration: $3,
  ease: B3,
  easeVarying: H3,
  end: yL,
  [Symbol.iterator]: ln[Symbol.iterator],
};
function xL(e) {
  return ((e *= 2) <= 1 ? e * e * e : (e -= 2) * e * e + 2) / 2;
}
var wL = { time: null, delay: 0, duration: 250, ease: xL };
function SL(e, t) {
  for (var n; !(n = e.__transition) || !(n = n[t]); )
    if (!(e = e.parentNode)) throw new Error(`transition ${t} not found`);
  return n;
}
function EL(e) {
  var t, n;
  e instanceof kn
    ? ((t = e._id), (e = e._name))
    : ((t = jS()), ((n = wL).time = Yh()), (e = e == null ? null : e + ""));
  for (var r = this._groups, o = r.length, i = 0; i < o; ++i)
    for (var s = r[i], a = s.length, l, u = 0; u < a; ++u)
      (l = s[u]) && yu(l, e, t, u, s, n || SL(l, t));
  return new kn(r, this._parents, e, t);
}
$s.prototype.interrupt = x3;
$s.prototype.transition = EL;
const ya = (e) => () => e;
function CL(e, { sourceEvent: t, target: n, transform: r, dispatch: o }) {
  Object.defineProperties(this, {
    type: { value: e, enumerable: !0, configurable: !0 },
    sourceEvent: { value: t, enumerable: !0, configurable: !0 },
    target: { value: n, enumerable: !0, configurable: !0 },
    transform: { value: r, enumerable: !0, configurable: !0 },
    _: { value: o },
  });
}
function pn(e, t, n) {
  (this.k = e), (this.x = t), (this.y = n);
}
pn.prototype = {
  constructor: pn,
  scale: function (e) {
    return e === 1 ? this : new pn(this.k * e, this.x, this.y);
  },
  translate: function (e, t) {
    return (e === 0) & (t === 0) ? this : new pn(this.k, this.x + this.k * e, this.y + this.k * t);
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
var vn = new pn(1, 0, 0);
pn.prototype;
function Cc(e) {
  e.stopImmediatePropagation();
}
function gi(e) {
  e.preventDefault(), e.stopImmediatePropagation();
}
function bL(e) {
  return (!e.ctrlKey || e.type === "wheel") && !e.button;
}
function kL() {
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
function Ey() {
  return this.__zoom || vn;
}
function _L(e) {
  return -e.deltaY * (e.deltaMode === 1 ? 0.05 : e.deltaMode ? 1 : 0.002) * (e.ctrlKey ? 10 : 1);
}
function TL() {
  return navigator.maxTouchPoints || "ontouchstart" in this;
}
function NL(e, t, n) {
  var r = e.invertX(t[0][0]) - n[0][0],
    o = e.invertX(t[1][0]) - n[1][0],
    i = e.invertY(t[0][1]) - n[0][1],
    s = e.invertY(t[1][1]) - n[1][1];
  return e.translate(
    o > r ? (r + o) / 2 : Math.min(0, r) || Math.max(0, o),
    s > i ? (i + s) / 2 : Math.min(0, i) || Math.max(0, s),
  );
}
function BS() {
  var e = bL,
    t = kL,
    n = NL,
    r = _L,
    o = TL,
    i = [0, 1 / 0],
    s = [
      [-1 / 0, -1 / 0],
      [1 / 0, 1 / 0],
    ],
    a = 250,
    l = f3,
    u = pu("start", "zoom", "end"),
    c,
    f,
    d,
    p = 500,
    y = 150,
    m = 0,
    w = 10;
  function h(k) {
    k.property("__zoom", Ey)
      .on("wheel.zoom", _, { passive: !1 })
      .on("mousedown.zoom", A)
      .on("dblclick.zoom", R)
      .filter(o)
      .on("touchstart.zoom", z)
      .on("touchmove.zoom", F)
      .on("touchend.zoom touchcancel.zoom", j)
      .style("-webkit-tap-highlight-color", "rgba(0,0,0,0)");
  }
  (h.transform = function (k, I, M, V) {
    var P = k.selection ? k.selection() : k;
    P.property("__zoom", Ey),
      k !== P
        ? E(k, I, M, V)
        : P.interrupt().each(function () {
            C(this, arguments)
              .event(V)
              .start()
              .zoom(null, typeof I == "function" ? I.apply(this, arguments) : I)
              .end();
          });
  }),
    (h.scaleBy = function (k, I, M, V) {
      h.scaleTo(
        k,
        function () {
          var P = this.__zoom.k,
            T = typeof I == "function" ? I.apply(this, arguments) : I;
          return P * T;
        },
        M,
        V,
      );
    }),
    (h.scaleTo = function (k, I, M, V) {
      h.transform(
        k,
        function () {
          var P = t.apply(this, arguments),
            T = this.__zoom,
            D = M == null ? S(P) : typeof M == "function" ? M.apply(this, arguments) : M,
            O = T.invert(D),
            $ = typeof I == "function" ? I.apply(this, arguments) : I;
          return n(x(g(T, $), D, O), P, s);
        },
        M,
        V,
      );
    }),
    (h.translateBy = function (k, I, M, V) {
      h.transform(
        k,
        function () {
          return n(
            this.__zoom.translate(
              typeof I == "function" ? I.apply(this, arguments) : I,
              typeof M == "function" ? M.apply(this, arguments) : M,
            ),
            t.apply(this, arguments),
            s,
          );
        },
        null,
        V,
      );
    }),
    (h.translateTo = function (k, I, M, V, P) {
      h.transform(
        k,
        function () {
          var T = t.apply(this, arguments),
            D = this.__zoom,
            O = V == null ? S(T) : typeof V == "function" ? V.apply(this, arguments) : V;
          return n(
            vn
              .translate(O[0], O[1])
              .scale(D.k)
              .translate(
                typeof I == "function" ? -I.apply(this, arguments) : -I,
                typeof M == "function" ? -M.apply(this, arguments) : -M,
              ),
            T,
            s,
          );
        },
        V,
        P,
      );
    });
  function g(k, I) {
    return (I = Math.max(i[0], Math.min(i[1], I))), I === k.k ? k : new pn(I, k.x, k.y);
  }
  function x(k, I, M) {
    var V = I[0] - M[0] * k.k,
      P = I[1] - M[1] * k.k;
    return V === k.x && P === k.y ? k : new pn(k.k, V, P);
  }
  function S(k) {
    return [(+k[0][0] + +k[1][0]) / 2, (+k[0][1] + +k[1][1]) / 2];
  }
  function E(k, I, M, V) {
    k.on("start.zoom", function () {
      C(this, arguments).event(V).start();
    })
      .on("interrupt.zoom end.zoom", function () {
        C(this, arguments).event(V).end();
      })
      .tween("zoom", function () {
        var P = this,
          T = arguments,
          D = C(P, T).event(V),
          O = t.apply(P, T),
          $ = M == null ? S(O) : typeof M == "function" ? M.apply(P, T) : M,
          H = Math.max(O[1][0] - O[0][0], O[1][1] - O[0][1]),
          U = P.__zoom,
          K = typeof I == "function" ? I.apply(P, T) : I,
          Z = l(U.invert($).concat(H / U.k), K.invert($).concat(H / K.k));
        return function (q) {
          if (q === 1) q = K;
          else {
            var oe = Z(q),
              re = H / oe[2];
            q = new pn(re, $[0] - oe[0] * re, $[1] - oe[1] * re);
          }
          D.zoom(null, q);
        };
      });
  }
  function C(k, I, M) {
    return (!M && k.__zooming) || new b(k, I);
  }
  function b(k, I) {
    (this.that = k),
      (this.args = I),
      (this.active = 0),
      (this.sourceEvent = null),
      (this.extent = t.apply(k, I)),
      (this.taps = 0);
  }
  b.prototype = {
    event: function (k) {
      return k && (this.sourceEvent = k), this;
    },
    start: function () {
      return ++this.active === 1 && ((this.that.__zooming = this), this.emit("start")), this;
    },
    zoom: function (k, I) {
      return (
        this.mouse && k !== "mouse" && (this.mouse[1] = I.invert(this.mouse[0])),
        this.touch0 && k !== "touch" && (this.touch0[1] = I.invert(this.touch0[0])),
        this.touch1 && k !== "touch" && (this.touch1[1] = I.invert(this.touch1[0])),
        (this.that.__zoom = I),
        this.emit("zoom"),
        this
      );
    },
    end: function () {
      return --this.active === 0 && (delete this.that.__zooming, this.emit("end")), this;
    },
    emit: function (k) {
      var I = Et(this.that).datum();
      u.call(
        k,
        this.that,
        new CL(k, {
          sourceEvent: this.sourceEvent,
          target: h,
          transform: this.that.__zoom,
          dispatch: u,
        }),
        I,
      );
    },
  };
  function _(k, ...I) {
    if (!e.apply(this, arguments)) return;
    var M = C(this, I).event(k),
      V = this.__zoom,
      P = Math.max(i[0], Math.min(i[1], V.k * Math.pow(2, r.apply(this, arguments)))),
      T = It(k);
    if (M.wheel)
      (M.mouse[0][0] !== T[0] || M.mouse[0][1] !== T[1]) &&
        (M.mouse[1] = V.invert((M.mouse[0] = T))),
        clearTimeout(M.wheel);
    else {
      if (V.k === P) return;
      (M.mouse = [T, V.invert(T)]), Ya(this), M.start();
    }
    gi(k),
      (M.wheel = setTimeout(D, y)),
      M.zoom("mouse", n(x(g(V, P), M.mouse[0], M.mouse[1]), M.extent, s));
    function D() {
      (M.wheel = null), M.end();
    }
  }
  function A(k, ...I) {
    if (d || !e.apply(this, arguments)) return;
    var M = k.currentTarget,
      V = C(this, I, !0).event(k),
      P = Et(k.view).on("mousemove.zoom", $, !0).on("mouseup.zoom", H, !0),
      T = It(k, M),
      D = k.clientX,
      O = k.clientY;
    TS(k.view), Cc(k), (V.mouse = [T, this.__zoom.invert(T)]), Ya(this), V.start();
    function $(U) {
      if ((gi(U), !V.moved)) {
        var K = U.clientX - D,
          Z = U.clientY - O;
        V.moved = K * K + Z * Z > m;
      }
      V.event(U).zoom(
        "mouse",
        n(x(V.that.__zoom, (V.mouse[0] = It(U, M)), V.mouse[1]), V.extent, s),
      );
    }
    function H(U) {
      P.on("mousemove.zoom mouseup.zoom", null), NS(U.view, V.moved), gi(U), V.event(U).end();
    }
  }
  function R(k, ...I) {
    if (e.apply(this, arguments)) {
      var M = this.__zoom,
        V = It(k.changedTouches ? k.changedTouches[0] : k, this),
        P = M.invert(V),
        T = M.k * (k.shiftKey ? 0.5 : 2),
        D = n(x(g(M, T), V, P), t.apply(this, I), s);
      gi(k),
        a > 0
          ? Et(this).transition().duration(a).call(E, D, V, k)
          : Et(this).call(h.transform, D, V, k);
    }
  }
  function z(k, ...I) {
    if (e.apply(this, arguments)) {
      var M = k.touches,
        V = M.length,
        P = C(this, I, k.changedTouches.length === V).event(k),
        T,
        D,
        O,
        $;
      for (Cc(k), D = 0; D < V; ++D)
        (O = M[D]),
          ($ = It(O, this)),
          ($ = [$, this.__zoom.invert($), O.identifier]),
          P.touch0
            ? !P.touch1 && P.touch0[2] !== $[2] && ((P.touch1 = $), (P.taps = 0))
            : ((P.touch0 = $), (T = !0), (P.taps = 1 + !!c));
      c && (c = clearTimeout(c)),
        T &&
          (P.taps < 2 &&
            ((f = $[0]),
            (c = setTimeout(function () {
              c = null;
            }, p))),
          Ya(this),
          P.start());
    }
  }
  function F(k, ...I) {
    if (this.__zooming) {
      var M = C(this, I).event(k),
        V = k.changedTouches,
        P = V.length,
        T,
        D,
        O,
        $;
      for (gi(k), T = 0; T < P; ++T)
        (D = V[T]),
          (O = It(D, this)),
          M.touch0 && M.touch0[2] === D.identifier
            ? (M.touch0[0] = O)
            : M.touch1 && M.touch1[2] === D.identifier && (M.touch1[0] = O);
      if (((D = M.that.__zoom), M.touch1)) {
        var H = M.touch0[0],
          U = M.touch0[1],
          K = M.touch1[0],
          Z = M.touch1[1],
          q = (q = K[0] - H[0]) * q + (q = K[1] - H[1]) * q,
          oe = (oe = Z[0] - U[0]) * oe + (oe = Z[1] - U[1]) * oe;
        (D = g(D, Math.sqrt(q / oe))),
          (O = [(H[0] + K[0]) / 2, (H[1] + K[1]) / 2]),
          ($ = [(U[0] + Z[0]) / 2, (U[1] + Z[1]) / 2]);
      } else if (M.touch0) (O = M.touch0[0]), ($ = M.touch0[1]);
      else return;
      M.zoom("touch", n(x(D, O, $), M.extent, s));
    }
  }
  function j(k, ...I) {
    if (this.__zooming) {
      var M = C(this, I).event(k),
        V = k.changedTouches,
        P = V.length,
        T,
        D;
      for (
        Cc(k),
          d && clearTimeout(d),
          d = setTimeout(function () {
            d = null;
          }, p),
          T = 0;
        T < P;
        ++T
      )
        (D = V[T]),
          M.touch0 && M.touch0[2] === D.identifier
            ? delete M.touch0
            : M.touch1 && M.touch1[2] === D.identifier && delete M.touch1;
      if ((M.touch1 && !M.touch0 && ((M.touch0 = M.touch1), delete M.touch1), M.touch0))
        M.touch0[1] = this.__zoom.invert(M.touch0[0]);
      else if (
        (M.end(), M.taps === 2 && ((D = It(D, this)), Math.hypot(f[0] - D[0], f[1] - D[1]) < w))
      ) {
        var O = Et(this).on("dblclick.zoom");
        O && O.apply(this, arguments);
      }
    }
  }
  return (
    (h.wheelDelta = function (k) {
      return arguments.length ? ((r = typeof k == "function" ? k : ya(+k)), h) : r;
    }),
    (h.filter = function (k) {
      return arguments.length ? ((e = typeof k == "function" ? k : ya(!!k)), h) : e;
    }),
    (h.touchable = function (k) {
      return arguments.length ? ((o = typeof k == "function" ? k : ya(!!k)), h) : o;
    }),
    (h.extent = function (k) {
      return arguments.length
        ? ((t =
            typeof k == "function"
              ? k
              : ya([
                  [+k[0][0], +k[0][1]],
                  [+k[1][0], +k[1][1]],
                ])),
          h)
        : t;
    }),
    (h.scaleExtent = function (k) {
      return arguments.length ? ((i[0] = +k[0]), (i[1] = +k[1]), h) : [i[0], i[1]];
    }),
    (h.translateExtent = function (k) {
      return arguments.length
        ? ((s[0][0] = +k[0][0]),
          (s[1][0] = +k[1][0]),
          (s[0][1] = +k[0][1]),
          (s[1][1] = +k[1][1]),
          h)
        : [
            [s[0][0], s[0][1]],
            [s[1][0], s[1][1]],
          ];
    }),
    (h.constrain = function (k) {
      return arguments.length ? ((n = k), h) : n;
    }),
    (h.duration = function (k) {
      return arguments.length ? ((a = +k), h) : a;
    }),
    (h.interpolate = function (k) {
      return arguments.length ? ((l = k), h) : l;
    }),
    (h.on = function () {
      var k = u.on.apply(u, arguments);
      return k === u ? h : k;
    }),
    (h.clickDistance = function (k) {
      return arguments.length ? ((m = (k = +k) * k), h) : Math.sqrt(m);
    }),
    (h.tapDistance = function (k) {
      return arguments.length ? ((w = +k), h) : w;
    }),
    h
  );
}
const vu = v.createContext(null),
  PL = vu.Provider,
  _n = {
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
  US = _n.error001();
function ce(e, t) {
  const n = v.useContext(vu);
  if (n === null) throw new Error(US);
  return pS(n, e, t);
}
const _e = () => {
    const e = v.useContext(vu);
    if (e === null) throw new Error(US);
    return v.useMemo(
      () => ({
        getState: e.getState,
        setState: e.setState,
        subscribe: e.subscribe,
        destroy: e.destroy,
      }),
      [e],
    );
  },
  ML = (e) => (e.userSelectionActive ? "none" : "all");
function Qh({ position: e, children: t, className: n, style: r, ...o }) {
  const i = ce(ML),
    s = `${e}`.split("-");
  return L.createElement(
    "div",
    { className: $e(["react-flow__panel", n, ...s]), style: { ...r, pointerEvents: i }, ...o },
    t,
  );
}
function AL({ proOptions: e, position: t = "bottom-right" }) {
  return e != null && e.hideAttribution
    ? null
    : L.createElement(
        Qh,
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
const RL = ({
  x: e,
  y: t,
  label: n,
  labelStyle: r = {},
  labelShowBg: o = !0,
  labelBgStyle: i = {},
  labelBgPadding: s = [2, 4],
  labelBgBorderRadius: a = 2,
  children: l,
  className: u,
  ...c
}) => {
  const f = v.useRef(null),
    [d, p] = v.useState({ x: 0, y: 0, width: 0, height: 0 }),
    y = $e(["react-flow__edge-textwrapper", u]);
  return (
    v.useEffect(() => {
      if (f.current) {
        const m = f.current.getBBox();
        p({ x: m.x, y: m.y, width: m.width, height: m.height });
      }
    }, [n]),
    typeof n > "u" || !n
      ? null
      : L.createElement(
          "g",
          {
            transform: `translate(${e - d.width / 2} ${t - d.height / 2})`,
            className: y,
            visibility: d.width ? "visible" : "hidden",
            ...c,
          },
          o &&
            L.createElement("rect", {
              width: d.width + 2 * s[0],
              x: -s[0],
              y: -s[1],
              height: d.height + 2 * s[1],
              className: "react-flow__edge-textbg",
              style: i,
              rx: a,
              ry: a,
            }),
          L.createElement(
            "text",
            { className: "react-flow__edge-text", y: d.height / 2, dy: "0.3em", ref: f, style: r },
            n,
          ),
          l,
        )
  );
};
var DL = v.memo(RL);
const qh = (e) => ({ width: e.offsetWidth, height: e.offsetHeight }),
  Go = (e, t = 0, n = 1) => Math.min(Math.max(e, t), n),
  Jh = (e = { x: 0, y: 0 }, t) => ({ x: Go(e.x, t[0][0], t[1][0]), y: Go(e.y, t[0][1], t[1][1]) }),
  Cy = (e, t, n) =>
    e < t ? Go(Math.abs(e - t), 1, 50) / 50 : e > n ? -Go(Math.abs(e - n), 1, 50) / 50 : 0,
  HS = (e, t) => {
    const n = Cy(e.x, 35, t.width - 35) * 20,
      r = Cy(e.y, 35, t.height - 35) * 20;
    return [n, r];
  },
  WS = (e) => {
    var t;
    return (
      ((t = e.getRootNode) == null ? void 0 : t.call(e)) ||
      (window == null ? void 0 : window.document)
    );
  },
  GS = (e, t) => ({
    x: Math.min(e.x, t.x),
    y: Math.min(e.y, t.y),
    x2: Math.max(e.x2, t.x2),
    y2: Math.max(e.y2, t.y2),
  }),
  ws = ({ x: e, y: t, width: n, height: r }) => ({ x: e, y: t, x2: e + n, y2: t + r }),
  KS = ({ x: e, y: t, x2: n, y2: r }) => ({ x: e, y: t, width: n - e, height: r - t }),
  by = (e) => ({
    ...(e.positionAbsolute || { x: 0, y: 0 }),
    width: e.width || 0,
    height: e.height || 0,
  }),
  IL = (e, t) => KS(GS(ws(e), ws(t))),
  qf = (e, t) => {
    const n = Math.max(0, Math.min(e.x + e.width, t.x + t.width) - Math.max(e.x, t.x)),
      r = Math.max(0, Math.min(e.y + e.height, t.y + t.height) - Math.max(e.y, t.y));
    return Math.ceil(n * r);
  },
  LL = (e) => kt(e.width) && kt(e.height) && kt(e.x) && kt(e.y),
  kt = (e) => !isNaN(e) && isFinite(e),
  Se = Symbol.for("internals"),
  YS = ["Enter", " ", "Escape"],
  VL = (e, t) => {},
  OL = (e) => "nativeEvent" in e;
function Jf(e) {
  var o, i;
  const t = OL(e) ? e.nativeEvent : e,
    n =
      ((i = (o = t.composedPath) == null ? void 0 : o.call(t)) == null ? void 0 : i[0]) || e.target;
  return (
    ["INPUT", "SELECT", "TEXTAREA"].includes(n == null ? void 0 : n.nodeName) ||
    (n == null ? void 0 : n.hasAttribute("contenteditable")) ||
    !!(n != null && n.closest(".nokey"))
  );
}
const XS = (e) => "clientX" in e,
  Zn = (e, t) => {
    var i, s;
    const n = XS(e),
      r = n ? e.clientX : (i = e.touches) == null ? void 0 : i[0].clientX,
      o = n ? e.clientY : (s = e.touches) == null ? void 0 : s[0].clientY;
    return {
      x: r - ((t == null ? void 0 : t.left) ?? 0),
      y: o - ((t == null ? void 0 : t.top) ?? 0),
    };
  },
  Dl = () => {
    var e;
    return (
      typeof navigator < "u" &&
      ((e = navigator == null ? void 0 : navigator.userAgent) == null
        ? void 0
        : e.indexOf("Mac")) >= 0
    );
  },
  Jo = ({
    id: e,
    path: t,
    labelX: n,
    labelY: r,
    label: o,
    labelStyle: i,
    labelShowBg: s,
    labelBgStyle: a,
    labelBgPadding: l,
    labelBgBorderRadius: u,
    style: c,
    markerEnd: f,
    markerStart: d,
    interactionWidth: p = 20,
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
      p &&
        L.createElement("path", {
          d: t,
          fill: "none",
          strokeOpacity: 0,
          strokeWidth: p,
          className: "react-flow__edge-interaction",
        }),
      o && kt(n) && kt(r)
        ? L.createElement(DL, {
            x: n,
            y: r,
            label: o,
            labelStyle: i,
            labelShowBg: s,
            labelBgStyle: a,
            labelBgPadding: l,
            labelBgBorderRadius: u,
          })
        : null,
    );
Jo.displayName = "BaseEdge";
function yi(e, t, n) {
  return n === void 0
    ? n
    : (r) => {
        const o = t().edges.find((i) => i.id === e);
        o && n(r, { ...o });
      };
}
function ZS({ sourceX: e, sourceY: t, targetX: n, targetY: r }) {
  const o = Math.abs(n - e) / 2,
    i = n < e ? n + o : n - o,
    s = Math.abs(r - t) / 2,
    a = r < t ? r + s : r - s;
  return [i, a, o, s];
}
function QS({
  sourceX: e,
  sourceY: t,
  targetX: n,
  targetY: r,
  sourceControlX: o,
  sourceControlY: i,
  targetControlX: s,
  targetControlY: a,
}) {
  const l = e * 0.125 + o * 0.375 + s * 0.375 + n * 0.125,
    u = t * 0.125 + i * 0.375 + a * 0.375 + r * 0.125,
    c = Math.abs(l - e),
    f = Math.abs(u - t);
  return [l, u, c, f];
}
var Vr;
(function (e) {
  (e.Strict = "strict"), (e.Loose = "loose");
})(Vr || (Vr = {}));
var Er;
(function (e) {
  (e.Free = "free"), (e.Vertical = "vertical"), (e.Horizontal = "horizontal");
})(Er || (Er = {}));
var Ss;
(function (e) {
  (e.Partial = "partial"), (e.Full = "full");
})(Ss || (Ss = {}));
var fn;
(function (e) {
  (e.Bezier = "default"),
    (e.Straight = "straight"),
    (e.Step = "step"),
    (e.SmoothStep = "smoothstep"),
    (e.SimpleBezier = "simplebezier");
})(fn || (fn = {}));
var Es;
(function (e) {
  (e.Arrow = "arrow"), (e.ArrowClosed = "arrowclosed");
})(Es || (Es = {}));
var G;
(function (e) {
  (e.Left = "left"), (e.Top = "top"), (e.Right = "right"), (e.Bottom = "bottom");
})(G || (G = {}));
function ky({ pos: e, x1: t, y1: n, x2: r, y2: o }) {
  return e === G.Left || e === G.Right ? [0.5 * (t + r), n] : [t, 0.5 * (n + o)];
}
function qS({
  sourceX: e,
  sourceY: t,
  sourcePosition: n = G.Bottom,
  targetX: r,
  targetY: o,
  targetPosition: i = G.Top,
}) {
  const [s, a] = ky({ pos: n, x1: e, y1: t, x2: r, y2: o }),
    [l, u] = ky({ pos: i, x1: r, y1: o, x2: e, y2: t }),
    [c, f, d, p] = QS({
      sourceX: e,
      sourceY: t,
      targetX: r,
      targetY: o,
      sourceControlX: s,
      sourceControlY: a,
      targetControlX: l,
      targetControlY: u,
    });
  return [`M${e},${t} C${s},${a} ${l},${u} ${r},${o}`, c, f, d, p];
}
const ep = v.memo(
  ({
    sourceX: e,
    sourceY: t,
    targetX: n,
    targetY: r,
    sourcePosition: o = G.Bottom,
    targetPosition: i = G.Top,
    label: s,
    labelStyle: a,
    labelShowBg: l,
    labelBgStyle: u,
    labelBgPadding: c,
    labelBgBorderRadius: f,
    style: d,
    markerEnd: p,
    markerStart: y,
    interactionWidth: m,
  }) => {
    const [w, h, g] = qS({
      sourceX: e,
      sourceY: t,
      sourcePosition: o,
      targetX: n,
      targetY: r,
      targetPosition: i,
    });
    return L.createElement(Jo, {
      path: w,
      labelX: h,
      labelY: g,
      label: s,
      labelStyle: a,
      labelShowBg: l,
      labelBgStyle: u,
      labelBgPadding: c,
      labelBgBorderRadius: f,
      style: d,
      markerEnd: p,
      markerStart: y,
      interactionWidth: m,
    });
  },
);
ep.displayName = "SimpleBezierEdge";
const _y = {
    [G.Left]: { x: -1, y: 0 },
    [G.Right]: { x: 1, y: 0 },
    [G.Top]: { x: 0, y: -1 },
    [G.Bottom]: { x: 0, y: 1 },
  },
  FL = ({ source: e, sourcePosition: t = G.Bottom, target: n }) =>
    t === G.Left || t === G.Right
      ? e.x < n.x
        ? { x: 1, y: 0 }
        : { x: -1, y: 0 }
      : e.y < n.y
        ? { x: 0, y: 1 }
        : { x: 0, y: -1 },
  Ty = (e, t) => Math.sqrt(Math.pow(t.x - e.x, 2) + Math.pow(t.y - e.y, 2));
function zL({
  source: e,
  sourcePosition: t = G.Bottom,
  target: n,
  targetPosition: r = G.Top,
  center: o,
  offset: i,
}) {
  const s = _y[t],
    a = _y[r],
    l = { x: e.x + s.x * i, y: e.y + s.y * i },
    u = { x: n.x + a.x * i, y: n.y + a.y * i },
    c = FL({ source: l, sourcePosition: t, target: u }),
    f = c.x !== 0 ? "x" : "y",
    d = c[f];
  let p = [],
    y,
    m;
  const w = { x: 0, y: 0 },
    h = { x: 0, y: 0 },
    [g, x, S, E] = ZS({ sourceX: e.x, sourceY: e.y, targetX: n.x, targetY: n.y });
  if (s[f] * a[f] === -1) {
    (y = o.x ?? g), (m = o.y ?? x);
    const b = [
        { x: y, y: l.y },
        { x: y, y: u.y },
      ],
      _ = [
        { x: l.x, y: m },
        { x: u.x, y: m },
      ];
    s[f] === d ? (p = f === "x" ? b : _) : (p = f === "x" ? _ : b);
  } else {
    const b = [{ x: l.x, y: u.y }],
      _ = [{ x: u.x, y: l.y }];
    if ((f === "x" ? (p = s.x === d ? _ : b) : (p = s.y === d ? b : _), t === r)) {
      const j = Math.abs(e[f] - n[f]);
      if (j <= i) {
        const k = Math.min(i - 1, i - j);
        s[f] === d ? (w[f] = (l[f] > e[f] ? -1 : 1) * k) : (h[f] = (u[f] > n[f] ? -1 : 1) * k);
      }
    }
    if (t !== r) {
      const j = f === "x" ? "y" : "x",
        k = s[f] === a[j],
        I = l[j] > u[j],
        M = l[j] < u[j];
      ((s[f] === 1 && ((!k && I) || (k && M))) || (s[f] !== 1 && ((!k && M) || (k && I)))) &&
        (p = f === "x" ? b : _);
    }
    const A = { x: l.x + w.x, y: l.y + w.y },
      R = { x: u.x + h.x, y: u.y + h.y },
      z = Math.max(Math.abs(A.x - p[0].x), Math.abs(R.x - p[0].x)),
      F = Math.max(Math.abs(A.y - p[0].y), Math.abs(R.y - p[0].y));
    z >= F ? ((y = (A.x + R.x) / 2), (m = p[0].y)) : ((y = p[0].x), (m = (A.y + R.y) / 2));
  }
  return [[e, { x: l.x + w.x, y: l.y + w.y }, ...p, { x: u.x + h.x, y: u.y + h.y }, n], y, m, S, E];
}
function $L(e, t, n, r) {
  const o = Math.min(Ty(e, t) / 2, Ty(t, n) / 2, r),
    { x: i, y: s } = t;
  if ((e.x === i && i === n.x) || (e.y === s && s === n.y)) return `L${i} ${s}`;
  if (e.y === s) {
    const u = e.x < n.x ? -1 : 1,
      c = e.y < n.y ? 1 : -1;
    return `L ${i + o * u},${s}Q ${i},${s} ${i},${s + o * c}`;
  }
  const a = e.x < n.x ? 1 : -1,
    l = e.y < n.y ? -1 : 1;
  return `L ${i},${s + o * l}Q ${i},${s} ${i + o * a},${s}`;
}
function Il({
  sourceX: e,
  sourceY: t,
  sourcePosition: n = G.Bottom,
  targetX: r,
  targetY: o,
  targetPosition: i = G.Top,
  borderRadius: s = 5,
  centerX: a,
  centerY: l,
  offset: u = 20,
}) {
  const [c, f, d, p, y] = zL({
    source: { x: e, y: t },
    sourcePosition: n,
    target: { x: r, y: o },
    targetPosition: i,
    center: { x: a, y: l },
    offset: u,
  });
  return [
    c.reduce((w, h, g) => {
      let x = "";
      return (
        g > 0 && g < c.length - 1
          ? (x = $L(c[g - 1], h, c[g + 1], s))
          : (x = `${g === 0 ? "M" : "L"}${h.x} ${h.y}`),
        (w += x),
        w
      );
    }, ""),
    f,
    d,
    p,
    y,
  ];
}
const xu = v.memo(
  ({
    sourceX: e,
    sourceY: t,
    targetX: n,
    targetY: r,
    label: o,
    labelStyle: i,
    labelShowBg: s,
    labelBgStyle: a,
    labelBgPadding: l,
    labelBgBorderRadius: u,
    style: c,
    sourcePosition: f = G.Bottom,
    targetPosition: d = G.Top,
    markerEnd: p,
    markerStart: y,
    pathOptions: m,
    interactionWidth: w,
  }) => {
    const [h, g, x] = Il({
      sourceX: e,
      sourceY: t,
      sourcePosition: f,
      targetX: n,
      targetY: r,
      targetPosition: d,
      borderRadius: m == null ? void 0 : m.borderRadius,
      offset: m == null ? void 0 : m.offset,
    });
    return L.createElement(Jo, {
      path: h,
      labelX: g,
      labelY: x,
      label: o,
      labelStyle: i,
      labelShowBg: s,
      labelBgStyle: a,
      labelBgPadding: l,
      labelBgBorderRadius: u,
      style: c,
      markerEnd: p,
      markerStart: y,
      interactionWidth: w,
    });
  },
);
xu.displayName = "SmoothStepEdge";
const tp = v.memo((e) => {
  var t;
  return L.createElement(xu, {
    ...e,
    pathOptions: v.useMemo(() => {
      var n;
      return { borderRadius: 0, offset: (n = e.pathOptions) == null ? void 0 : n.offset };
    }, [(t = e.pathOptions) == null ? void 0 : t.offset]),
  });
});
tp.displayName = "StepEdge";
function jL({ sourceX: e, sourceY: t, targetX: n, targetY: r }) {
  const [o, i, s, a] = ZS({ sourceX: e, sourceY: t, targetX: n, targetY: r });
  return [`M ${e},${t}L ${n},${r}`, o, i, s, a];
}
const np = v.memo(
  ({
    sourceX: e,
    sourceY: t,
    targetX: n,
    targetY: r,
    label: o,
    labelStyle: i,
    labelShowBg: s,
    labelBgStyle: a,
    labelBgPadding: l,
    labelBgBorderRadius: u,
    style: c,
    markerEnd: f,
    markerStart: d,
    interactionWidth: p,
  }) => {
    const [y, m, w] = jL({ sourceX: e, sourceY: t, targetX: n, targetY: r });
    return L.createElement(Jo, {
      path: y,
      labelX: m,
      labelY: w,
      label: o,
      labelStyle: i,
      labelShowBg: s,
      labelBgStyle: a,
      labelBgPadding: l,
      labelBgBorderRadius: u,
      style: c,
      markerEnd: f,
      markerStart: d,
      interactionWidth: p,
    });
  },
);
np.displayName = "StraightEdge";
function va(e, t) {
  return e >= 0 ? 0.5 * e : t * 25 * Math.sqrt(-e);
}
function Ny({ pos: e, x1: t, y1: n, x2: r, y2: o, c: i }) {
  switch (e) {
    case G.Left:
      return [t - va(t - r, i), n];
    case G.Right:
      return [t + va(r - t, i), n];
    case G.Top:
      return [t, n - va(n - o, i)];
    case G.Bottom:
      return [t, n + va(o - n, i)];
  }
}
function JS({
  sourceX: e,
  sourceY: t,
  sourcePosition: n = G.Bottom,
  targetX: r,
  targetY: o,
  targetPosition: i = G.Top,
  curvature: s = 0.25,
}) {
  const [a, l] = Ny({ pos: n, x1: e, y1: t, x2: r, y2: o, c: s }),
    [u, c] = Ny({ pos: i, x1: r, y1: o, x2: e, y2: t, c: s }),
    [f, d, p, y] = QS({
      sourceX: e,
      sourceY: t,
      targetX: r,
      targetY: o,
      sourceControlX: a,
      sourceControlY: l,
      targetControlX: u,
      targetControlY: c,
    });
  return [`M${e},${t} C${a},${l} ${u},${c} ${r},${o}`, f, d, p, y];
}
const Ll = v.memo(
  ({
    sourceX: e,
    sourceY: t,
    targetX: n,
    targetY: r,
    sourcePosition: o = G.Bottom,
    targetPosition: i = G.Top,
    label: s,
    labelStyle: a,
    labelShowBg: l,
    labelBgStyle: u,
    labelBgPadding: c,
    labelBgBorderRadius: f,
    style: d,
    markerEnd: p,
    markerStart: y,
    pathOptions: m,
    interactionWidth: w,
  }) => {
    const [h, g, x] = JS({
      sourceX: e,
      sourceY: t,
      sourcePosition: o,
      targetX: n,
      targetY: r,
      targetPosition: i,
      curvature: m == null ? void 0 : m.curvature,
    });
    return L.createElement(Jo, {
      path: h,
      labelX: g,
      labelY: x,
      label: s,
      labelStyle: a,
      labelShowBg: l,
      labelBgStyle: u,
      labelBgPadding: c,
      labelBgBorderRadius: f,
      style: d,
      markerEnd: p,
      markerStart: y,
      interactionWidth: w,
    });
  },
);
Ll.displayName = "BezierEdge";
const rp = v.createContext(null),
  BL = rp.Provider;
rp.Consumer;
const UL = () => v.useContext(rp),
  HL = (e) => "id" in e && "source" in e && "target" in e,
  WL = ({ source: e, sourceHandle: t, target: n, targetHandle: r }) =>
    `reactflow__edge-${e}${t || ""}-${n}${r || ""}`,
  ed = (e, t) =>
    typeof e > "u"
      ? ""
      : typeof e == "string"
        ? e
        : `${t ? `${t}__` : ""}${Object.keys(e)
            .sort()
            .map((r) => `${r}=${e[r]}`)
            .join("&")}`,
  GL = (e, t) =>
    t.some(
      (n) =>
        n.source === e.source &&
        n.target === e.target &&
        (n.sourceHandle === e.sourceHandle || (!n.sourceHandle && !e.sourceHandle)) &&
        (n.targetHandle === e.targetHandle || (!n.targetHandle && !e.targetHandle)),
    ),
  KL = (e, t) => {
    if (!e.source || !e.target) return t;
    let n;
    return HL(e) ? (n = { ...e }) : (n = { ...e, id: WL(e) }), GL(n, t) ? t : t.concat(n);
  },
  td = ({ x: e, y: t }, [n, r, o], i, [s, a]) => {
    const l = { x: (e - n) / o, y: (t - r) / o };
    return i ? { x: s * Math.round(l.x / s), y: a * Math.round(l.y / a) } : l;
  },
  eE = ({ x: e, y: t }, [n, r, o]) => ({ x: e * o + n, y: t * o + r }),
  Nr = (e, t = [0, 0]) => {
    if (!e) return { x: 0, y: 0, positionAbsolute: { x: 0, y: 0 } };
    const n = (e.width ?? 0) * t[0],
      r = (e.height ?? 0) * t[1],
      o = { x: e.position.x - n, y: e.position.y - r };
    return {
      ...o,
      positionAbsolute: e.positionAbsolute
        ? { x: e.positionAbsolute.x - n, y: e.positionAbsolute.y - r }
        : o,
    };
  },
  wu = (e, t = [0, 0]) => {
    if (e.length === 0) return { x: 0, y: 0, width: 0, height: 0 };
    const n = e.reduce(
      (r, o) => {
        const { x: i, y: s } = Nr(o, t).positionAbsolute;
        return GS(r, ws({ x: i, y: s, width: o.width || 0, height: o.height || 0 }));
      },
      { x: 1 / 0, y: 1 / 0, x2: -1 / 0, y2: -1 / 0 },
    );
    return KS(n);
  },
  tE = (e, t, [n, r, o] = [0, 0, 1], i = !1, s = !1, a = [0, 0]) => {
    const l = { x: (t.x - n) / o, y: (t.y - r) / o, width: t.width / o, height: t.height / o },
      u = [];
    return (
      e.forEach((c) => {
        const { width: f, height: d, selectable: p = !0, hidden: y = !1 } = c;
        if ((s && !p) || y) return !1;
        const { positionAbsolute: m } = Nr(c, a),
          w = { x: m.x, y: m.y, width: f || 0, height: d || 0 },
          h = qf(l, w),
          g = typeof f > "u" || typeof d > "u" || f === null || d === null,
          x = i && h > 0,
          S = (f || 0) * (d || 0);
        (g || x || h >= S || c.dragging) && u.push(c);
      }),
      u
    );
  },
  nE = (e, t) => {
    const n = e.map((r) => r.id);
    return t.filter((r) => n.includes(r.source) || n.includes(r.target));
  },
  rE = (e, t, n, r, o, i = 0.1) => {
    const s = t / (e.width * (1 + i)),
      a = n / (e.height * (1 + i)),
      l = Math.min(s, a),
      u = Go(l, r, o),
      c = e.x + e.width / 2,
      f = e.y + e.height / 2,
      d = t / 2 - c * u,
      p = n / 2 - f * u;
    return { x: d, y: p, zoom: u };
  },
  gr = (e, t = 0) => e.transition().duration(t);
function Py(e, t, n, r) {
  return (t[n] || []).reduce((o, i) => {
    var s, a;
    return (
      `${e.id}-${i.id}-${n}` !== r &&
        o.push({
          id: i.id || null,
          type: n,
          nodeId: e.id,
          x: (((s = e.positionAbsolute) == null ? void 0 : s.x) ?? 0) + i.x + i.width / 2,
          y: (((a = e.positionAbsolute) == null ? void 0 : a.y) ?? 0) + i.y + i.height / 2,
        }),
      o
    );
  }, []);
}
function YL(e, t, n, r, o, i) {
  const { x: s, y: a } = Zn(e),
    u = t.elementsFromPoint(s, a).find((y) => y.classList.contains("react-flow__handle"));
  if (u) {
    const y = u.getAttribute("data-nodeid");
    if (y) {
      const m = op(void 0, u),
        w = u.getAttribute("data-handleid"),
        h = i({ nodeId: y, id: w, type: m });
      if (h) {
        const g = o.find((x) => x.nodeId === y && x.type === m && x.id === w);
        return {
          handle: {
            id: w,
            type: m,
            nodeId: y,
            x: (g == null ? void 0 : g.x) || n.x,
            y: (g == null ? void 0 : g.y) || n.y,
          },
          validHandleResult: h,
        };
      }
    }
  }
  let c = [],
    f = 1 / 0;
  if (
    (o.forEach((y) => {
      const m = Math.sqrt((y.x - n.x) ** 2 + (y.y - n.y) ** 2);
      if (m <= r) {
        const w = i(y);
        m <= f &&
          (m < f
            ? (c = [{ handle: y, validHandleResult: w }])
            : m === f && c.push({ handle: y, validHandleResult: w }),
          (f = m));
      }
    }),
    !c.length)
  )
    return { handle: null, validHandleResult: oE() };
  if (c.length === 1) return c[0];
  const d = c.some(({ validHandleResult: y }) => y.isValid),
    p = c.some(({ handle: y }) => y.type === "target");
  return (
    c.find(({ handle: y, validHandleResult: m }) =>
      p ? y.type === "target" : d ? m.isValid : !0,
    ) || c[0]
  );
}
const XL = { source: null, target: null, sourceHandle: null, targetHandle: null },
  oE = () => ({ handleDomNode: null, isValid: !1, connection: XL, endHandle: null });
function iE(e, t, n, r, o, i, s) {
  const a = o === "target",
    l = s.querySelector(
      `.react-flow__handle[data-id="${e == null ? void 0 : e.nodeId}-${e == null ? void 0 : e.id}-${e == null ? void 0 : e.type}"]`,
    ),
    u = { ...oE(), handleDomNode: l };
  if (l) {
    const c = op(void 0, l),
      f = l.getAttribute("data-nodeid"),
      d = l.getAttribute("data-handleid"),
      p = l.classList.contains("connectable"),
      y = l.classList.contains("connectableend"),
      m = {
        source: a ? f : n,
        sourceHandle: a ? d : r,
        target: a ? n : f,
        targetHandle: a ? r : d,
      };
    (u.connection = m),
      p &&
        y &&
        (t === Vr.Strict ? (a && c === "source") || (!a && c === "target") : f !== n || d !== r) &&
        ((u.endHandle = { nodeId: f, handleId: d, type: c }), (u.isValid = i(m)));
  }
  return u;
}
function ZL({ nodes: e, nodeId: t, handleId: n, handleType: r }) {
  return e.reduce((o, i) => {
    if (i[Se]) {
      const { handleBounds: s } = i[Se];
      let a = [],
        l = [];
      s && ((a = Py(i, s, "source", `${t}-${n}-${r}`)), (l = Py(i, s, "target", `${t}-${n}-${r}`))),
        o.push(...a, ...l);
    }
    return o;
  }, []);
}
function op(e, t) {
  return (
    e ||
    (t != null && t.classList.contains("target")
      ? "target"
      : t != null && t.classList.contains("source")
        ? "source"
        : null)
  );
}
function bc(e) {
  e == null ||
    e.classList.remove(
      "valid",
      "connecting",
      "react-flow__handle-valid",
      "react-flow__handle-connecting",
    );
}
function QL(e, t) {
  let n = null;
  return t ? (n = "valid") : e && !t && (n = "invalid"), n;
}
function sE({
  event: e,
  handleId: t,
  nodeId: n,
  onConnect: r,
  isTarget: o,
  getState: i,
  setState: s,
  isValidConnection: a,
  edgeUpdaterType: l,
  onReconnectEnd: u,
}) {
  const c = WS(e.target),
    {
      connectionMode: f,
      domNode: d,
      autoPanOnConnect: p,
      connectionRadius: y,
      onConnectStart: m,
      panBy: w,
      getNodes: h,
      cancelConnection: g,
    } = i();
  let x = 0,
    S;
  const { x: E, y: C } = Zn(e),
    b = c == null ? void 0 : c.elementFromPoint(E, C),
    _ = op(l, b),
    A = d == null ? void 0 : d.getBoundingClientRect();
  if (!A || !_) return;
  let R,
    z = Zn(e, A),
    F = !1,
    j = null,
    k = !1,
    I = null;
  const M = ZL({ nodes: h(), nodeId: n, handleId: t, handleType: _ }),
    V = () => {
      if (!p) return;
      const [D, O] = HS(z, A);
      w({ x: D, y: O }), (x = requestAnimationFrame(V));
    };
  s({
    connectionPosition: z,
    connectionStatus: null,
    connectionNodeId: n,
    connectionHandleId: t,
    connectionHandleType: _,
    connectionStartHandle: { nodeId: n, handleId: t, type: _ },
    connectionEndHandle: null,
  }),
    m == null || m(e, { nodeId: n, handleId: t, handleType: _ });
  function P(D) {
    const { transform: O } = i();
    z = Zn(D, A);
    const { handle: $, validHandleResult: H } = YL(D, c, td(z, O, !1, [1, 1]), y, M, (U) =>
      iE(U, f, n, t, o ? "target" : "source", a, c),
    );
    if (
      ((S = $),
      F || (V(), (F = !0)),
      (I = H.handleDomNode),
      (j = H.connection),
      (k = H.isValid),
      s({
        connectionPosition: S && k ? eE({ x: S.x, y: S.y }, O) : z,
        connectionStatus: QL(!!S, k),
        connectionEndHandle: H.endHandle,
      }),
      !S && !k && !I)
    )
      return bc(R);
    j.source !== j.target &&
      I &&
      (bc(R),
      (R = I),
      I.classList.add("connecting", "react-flow__handle-connecting"),
      I.classList.toggle("valid", k),
      I.classList.toggle("react-flow__handle-valid", k));
  }
  function T(D) {
    var O, $;
    (S || I) && j && k && (r == null || r(j)),
      ($ = (O = i()).onConnectEnd) == null || $.call(O, D),
      l && (u == null || u(D)),
      bc(R),
      g(),
      cancelAnimationFrame(x),
      (F = !1),
      (k = !1),
      (j = null),
      (I = null),
      c.removeEventListener("mousemove", P),
      c.removeEventListener("mouseup", T),
      c.removeEventListener("touchmove", P),
      c.removeEventListener("touchend", T);
  }
  c.addEventListener("mousemove", P),
    c.addEventListener("mouseup", T),
    c.addEventListener("touchmove", P),
    c.addEventListener("touchend", T);
}
const My = () => !0,
  qL = (e) => ({
    connectionStartHandle: e.connectionStartHandle,
    connectOnClick: e.connectOnClick,
    noPanClassName: e.noPanClassName,
  }),
  JL = (e, t, n) => (r) => {
    const { connectionStartHandle: o, connectionEndHandle: i, connectionClickStartHandle: s } = r;
    return {
      connecting:
        ((o == null ? void 0 : o.nodeId) === e &&
          (o == null ? void 0 : o.handleId) === t &&
          (o == null ? void 0 : o.type) === n) ||
        ((i == null ? void 0 : i.nodeId) === e &&
          (i == null ? void 0 : i.handleId) === t &&
          (i == null ? void 0 : i.type) === n),
      clickConnecting:
        (s == null ? void 0 : s.nodeId) === e &&
        (s == null ? void 0 : s.handleId) === t &&
        (s == null ? void 0 : s.type) === n,
    };
  },
  aE = v.forwardRef(
    (
      {
        type: e = "source",
        position: t = G.Top,
        isValidConnection: n,
        isConnectable: r = !0,
        isConnectableStart: o = !0,
        isConnectableEnd: i = !0,
        id: s,
        onConnect: a,
        children: l,
        className: u,
        onMouseDown: c,
        onTouchStart: f,
        ...d
      },
      p,
    ) => {
      var A, R;
      const y = s || null,
        m = e === "target",
        w = _e(),
        h = UL(),
        { connectOnClick: g, noPanClassName: x } = ce(qL, Ie),
        { connecting: S, clickConnecting: E } = ce(JL(h, y, e), Ie);
      h || (R = (A = w.getState()).onError) == null || R.call(A, "010", _n.error010());
      const C = (z) => {
          const { defaultEdgeOptions: F, onConnect: j, hasDefaultEdges: k } = w.getState(),
            I = { ...F, ...z };
          if (k) {
            const { edges: M, setEdges: V } = w.getState();
            V(KL(I, M));
          }
          j == null || j(I), a == null || a(I);
        },
        b = (z) => {
          if (!h) return;
          const F = XS(z);
          o &&
            ((F && z.button === 0) || !F) &&
            sE({
              event: z,
              handleId: y,
              nodeId: h,
              onConnect: C,
              isTarget: m,
              getState: w.getState,
              setState: w.setState,
              isValidConnection: n || w.getState().isValidConnection || My,
            }),
            F ? c == null || c(z) : f == null || f(z);
        },
        _ = (z) => {
          const {
            onClickConnectStart: F,
            onClickConnectEnd: j,
            connectionClickStartHandle: k,
            connectionMode: I,
            isValidConnection: M,
          } = w.getState();
          if (!h || (!k && !o)) return;
          if (!k) {
            F == null || F(z, { nodeId: h, handleId: y, handleType: e }),
              w.setState({ connectionClickStartHandle: { nodeId: h, type: e, handleId: y } });
            return;
          }
          const V = WS(z.target),
            P = n || M || My,
            { connection: T, isValid: D } = iE(
              { nodeId: h, id: y, type: e },
              I,
              k.nodeId,
              k.handleId || null,
              k.type,
              P,
              V,
            );
          D && C(T), j == null || j(z), w.setState({ connectionClickStartHandle: null });
        };
      return L.createElement(
        "div",
        {
          "data-handleid": y,
          "data-nodeid": h,
          "data-handlepos": t,
          "data-id": `${h}-${y}-${e}`,
          className: $e([
            "react-flow__handle",
            `react-flow__handle-${t}`,
            "nodrag",
            x,
            u,
            {
              source: !m,
              target: m,
              connectable: r,
              connectablestart: o,
              connectableend: i,
              connecting: E,
              connectionindicator: r && ((o && !S) || (i && S)),
            },
          ]),
          onMouseDown: b,
          onTouchStart: b,
          onClick: g ? _ : void 0,
          ref: p,
          ...d,
        },
        l,
      );
    },
  );
aE.displayName = "Handle";
var er = v.memo(aE);
const lE = ({
  data: e,
  isConnectable: t,
  targetPosition: n = G.Top,
  sourcePosition: r = G.Bottom,
}) =>
  L.createElement(
    L.Fragment,
    null,
    L.createElement(er, { type: "target", position: n, isConnectable: t }),
    e == null ? void 0 : e.label,
    L.createElement(er, { type: "source", position: r, isConnectable: t }),
  );
lE.displayName = "DefaultNode";
var nd = v.memo(lE);
const uE = ({ data: e, isConnectable: t, sourcePosition: n = G.Bottom }) =>
  L.createElement(
    L.Fragment,
    null,
    e == null ? void 0 : e.label,
    L.createElement(er, { type: "source", position: n, isConnectable: t }),
  );
uE.displayName = "InputNode";
var cE = v.memo(uE);
const fE = ({ data: e, isConnectable: t, targetPosition: n = G.Top }) =>
  L.createElement(
    L.Fragment,
    null,
    L.createElement(er, { type: "target", position: n, isConnectable: t }),
    e == null ? void 0 : e.label,
  );
fE.displayName = "OutputNode";
var dE = v.memo(fE);
const ip = () => null;
ip.displayName = "GroupNode";
const e4 = (e) => ({
    selectedNodes: e.getNodes().filter((t) => t.selected),
    selectedEdges: e.edges.filter((t) => t.selected).map((t) => ({ ...t })),
  }),
  xa = (e) => e.id;
function t4(e, t) {
  return (
    Ie(e.selectedNodes.map(xa), t.selectedNodes.map(xa)) &&
    Ie(e.selectedEdges.map(xa), t.selectedEdges.map(xa))
  );
}
const hE = v.memo(({ onSelectionChange: e }) => {
  const t = _e(),
    { selectedNodes: n, selectedEdges: r } = ce(e4, t4);
  return (
    v.useEffect(() => {
      const o = { nodes: n, edges: r };
      e == null || e(o), t.getState().onSelectionChange.forEach((i) => i(o));
    }, [n, r, e]),
    null
  );
});
hE.displayName = "SelectionListener";
const n4 = (e) => !!e.onSelectionChange;
function r4({ onSelectionChange: e }) {
  const t = ce(n4);
  return e || t ? L.createElement(hE, { onSelectionChange: e }) : null;
}
const o4 = (e) => ({
  setNodes: e.setNodes,
  setEdges: e.setEdges,
  setDefaultNodesAndEdges: e.setDefaultNodesAndEdges,
  setMinZoom: e.setMinZoom,
  setMaxZoom: e.setMaxZoom,
  setTranslateExtent: e.setTranslateExtent,
  setNodeExtent: e.setNodeExtent,
  reset: e.reset,
});
function Xr(e, t) {
  v.useEffect(() => {
    typeof e < "u" && t(e);
  }, [e]);
}
function J(e, t, n) {
  v.useEffect(() => {
    typeof t < "u" && n({ [e]: t });
  }, [t]);
}
const i4 = ({
    nodes: e,
    edges: t,
    defaultNodes: n,
    defaultEdges: r,
    onConnect: o,
    onConnectStart: i,
    onConnectEnd: s,
    onClickConnectStart: a,
    onClickConnectEnd: l,
    nodesDraggable: u,
    nodesConnectable: c,
    nodesFocusable: f,
    edgesFocusable: d,
    edgesUpdatable: p,
    elevateNodesOnSelect: y,
    minZoom: m,
    maxZoom: w,
    nodeExtent: h,
    onNodesChange: g,
    onEdgesChange: x,
    elementsSelectable: S,
    connectionMode: E,
    snapGrid: C,
    snapToGrid: b,
    translateExtent: _,
    connectOnClick: A,
    defaultEdgeOptions: R,
    fitView: z,
    fitViewOptions: F,
    onNodesDelete: j,
    onEdgesDelete: k,
    onNodeDrag: I,
    onNodeDragStart: M,
    onNodeDragStop: V,
    onSelectionDrag: P,
    onSelectionDragStart: T,
    onSelectionDragStop: D,
    noPanClassName: O,
    nodeOrigin: $,
    rfId: H,
    autoPanOnConnect: U,
    autoPanOnNodeDrag: K,
    onError: Z,
    connectionRadius: q,
    isValidConnection: oe,
    nodeDragThreshold: re,
  }) => {
    const {
        setNodes: ne,
        setEdges: Le,
        setDefaultNodesAndEdges: Te,
        setMinZoom: Ye,
        setMaxZoom: je,
        setTranslateExtent: Ee,
        setNodeExtent: lt,
        reset: se,
      } = ce(o4, Ie),
      Y = _e();
    return (
      v.useEffect(() => {
        const Xe = r == null ? void 0 : r.map((rn) => ({ ...rn, ...R }));
        return (
          Te(n, Xe),
          () => {
            se();
          }
        );
      }, []),
      J("defaultEdgeOptions", R, Y.setState),
      J("connectionMode", E, Y.setState),
      J("onConnect", o, Y.setState),
      J("onConnectStart", i, Y.setState),
      J("onConnectEnd", s, Y.setState),
      J("onClickConnectStart", a, Y.setState),
      J("onClickConnectEnd", l, Y.setState),
      J("nodesDraggable", u, Y.setState),
      J("nodesConnectable", c, Y.setState),
      J("nodesFocusable", f, Y.setState),
      J("edgesFocusable", d, Y.setState),
      J("edgesUpdatable", p, Y.setState),
      J("elementsSelectable", S, Y.setState),
      J("elevateNodesOnSelect", y, Y.setState),
      J("snapToGrid", b, Y.setState),
      J("snapGrid", C, Y.setState),
      J("onNodesChange", g, Y.setState),
      J("onEdgesChange", x, Y.setState),
      J("connectOnClick", A, Y.setState),
      J("fitViewOnInit", z, Y.setState),
      J("fitViewOnInitOptions", F, Y.setState),
      J("onNodesDelete", j, Y.setState),
      J("onEdgesDelete", k, Y.setState),
      J("onNodeDrag", I, Y.setState),
      J("onNodeDragStart", M, Y.setState),
      J("onNodeDragStop", V, Y.setState),
      J("onSelectionDrag", P, Y.setState),
      J("onSelectionDragStart", T, Y.setState),
      J("onSelectionDragStop", D, Y.setState),
      J("noPanClassName", O, Y.setState),
      J("nodeOrigin", $, Y.setState),
      J("rfId", H, Y.setState),
      J("autoPanOnConnect", U, Y.setState),
      J("autoPanOnNodeDrag", K, Y.setState),
      J("onError", Z, Y.setState),
      J("connectionRadius", q, Y.setState),
      J("isValidConnection", oe, Y.setState),
      J("nodeDragThreshold", re, Y.setState),
      Xr(e, ne),
      Xr(t, Le),
      Xr(m, Ye),
      Xr(w, je),
      Xr(_, Ee),
      Xr(h, lt),
      null
    );
  },
  Ay = { display: "none" },
  s4 = {
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
  pE = "react-flow__node-desc",
  mE = "react-flow__edge-desc",
  a4 = "react-flow__aria-live",
  l4 = (e) => e.ariaLiveMessage;
function u4({ rfId: e }) {
  const t = ce(l4);
  return L.createElement(
    "div",
    { id: `${a4}-${e}`, "aria-live": "assertive", "aria-atomic": "true", style: s4 },
    t,
  );
}
function c4({ rfId: e, disableKeyboardA11y: t }) {
  return L.createElement(
    L.Fragment,
    null,
    L.createElement(
      "div",
      { id: `${pE}-${e}`, style: Ay },
      "Press enter or space to select a node.",
      !t && "You can then use the arrow keys to move the node around.",
      " Press delete to remove it and escape to cancel.",
      " ",
    ),
    L.createElement(
      "div",
      { id: `${mE}-${e}`, style: Ay },
      "Press enter or space to select an edge. You can then press delete to remove it or escape to cancel.",
    ),
    !t && L.createElement(u4, { rfId: e }),
  );
}
var Cs = (e = null, t = { actInsideInputWithModifier: !0 }) => {
  const [n, r] = v.useState(!1),
    o = v.useRef(!1),
    i = v.useRef(new Set([])),
    [s, a] = v.useMemo(() => {
      if (e !== null) {
        const u = (Array.isArray(e) ? e : [e])
            .filter((f) => typeof f == "string")
            .map((f) => f.split("+")),
          c = u.reduce((f, d) => f.concat(...d), []);
        return [u, c];
      }
      return [[], []];
    }, [e]);
  return (
    v.useEffect(() => {
      const l = typeof document < "u" ? document : null,
        u = (t == null ? void 0 : t.target) || l;
      if (e !== null) {
        const c = (p) => {
            if (
              ((o.current = p.ctrlKey || p.metaKey || p.shiftKey),
              (!o.current || (o.current && !t.actInsideInputWithModifier)) && Jf(p))
            )
              return !1;
            const m = Dy(p.code, a);
            i.current.add(p[m]), Ry(s, i.current, !1) && (p.preventDefault(), r(!0));
          },
          f = (p) => {
            if ((!o.current || (o.current && !t.actInsideInputWithModifier)) && Jf(p)) return !1;
            const m = Dy(p.code, a);
            Ry(s, i.current, !0) ? (r(!1), i.current.clear()) : i.current.delete(p[m]),
              p.key === "Meta" && i.current.clear(),
              (o.current = !1);
          },
          d = () => {
            i.current.clear(), r(!1);
          };
        return (
          u == null || u.addEventListener("keydown", c),
          u == null || u.addEventListener("keyup", f),
          window.addEventListener("blur", d),
          () => {
            u == null || u.removeEventListener("keydown", c),
              u == null || u.removeEventListener("keyup", f),
              window.removeEventListener("blur", d);
          }
        );
      }
    }, [e, r]),
    n
  );
};
function Ry(e, t, n) {
  return e.filter((r) => n || r.length === t.size).some((r) => r.every((o) => t.has(o)));
}
function Dy(e, t) {
  return t.includes(e) ? "code" : "key";
}
function gE(e, t, n, r) {
  var a, l;
  const o = e.parentNode || e.parentId;
  if (!o) return n;
  const i = t.get(o),
    s = Nr(i, r);
  return gE(
    i,
    t,
    {
      x: (n.x ?? 0) + s.x,
      y: (n.y ?? 0) + s.y,
      z:
        (((a = i[Se]) == null ? void 0 : a.z) ?? 0) > (n.z ?? 0)
          ? (((l = i[Se]) == null ? void 0 : l.z) ?? 0)
          : (n.z ?? 0),
    },
    r,
  );
}
function yE(e, t, n) {
  e.forEach((r) => {
    var i;
    const o = r.parentNode || r.parentId;
    if (o && !e.has(o)) throw new Error(`Parent node ${o} not found`);
    if (o || (n != null && n[r.id])) {
      const {
        x: s,
        y: a,
        z: l,
      } = gE(r, e, { ...r.position, z: ((i = r[Se]) == null ? void 0 : i.z) ?? 0 }, t);
      (r.positionAbsolute = { x: s, y: a }),
        (r[Se].z = l),
        n != null && n[r.id] && (r[Se].isParent = !0);
    }
  });
}
function kc(e, t, n, r) {
  const o = new Map(),
    i = {},
    s = r ? 1e3 : 0;
  return (
    e.forEach((a) => {
      var p;
      const l = (kt(a.zIndex) ? a.zIndex : 0) + (a.selected ? s : 0),
        u = t.get(a.id),
        c = { ...a, positionAbsolute: { x: a.position.x, y: a.position.y } },
        f = a.parentNode || a.parentId;
      f && (i[f] = !0);
      const d = (u == null ? void 0 : u.type) && (u == null ? void 0 : u.type) !== a.type;
      Object.defineProperty(c, Se, {
        enumerable: !1,
        value: {
          handleBounds: d || (p = u == null ? void 0 : u[Se]) == null ? void 0 : p.handleBounds,
          z: l,
        },
      }),
        o.set(a.id, c);
    }),
    yE(o, n, i),
    o
  );
}
function vE(e, t = {}) {
  const {
      getNodes: n,
      width: r,
      height: o,
      minZoom: i,
      maxZoom: s,
      d3Zoom: a,
      d3Selection: l,
      fitViewOnInitDone: u,
      fitViewOnInit: c,
      nodeOrigin: f,
    } = e(),
    d = t.initial && !u && c;
  if (a && l && (d || !t.initial)) {
    const y = n().filter((w) => {
        var g;
        const h = t.includeHiddenNodes ? w.width && w.height : !w.hidden;
        return (g = t.nodes) != null && g.length ? h && t.nodes.some((x) => x.id === w.id) : h;
      }),
      m = y.every((w) => w.width && w.height);
    if (y.length > 0 && m) {
      const w = wu(y, f),
        { x: h, y: g, zoom: x } = rE(w, r, o, t.minZoom ?? i, t.maxZoom ?? s, t.padding ?? 0.1),
        S = vn.translate(h, g).scale(x);
      return (
        typeof t.duration == "number" && t.duration > 0
          ? a.transform(gr(l, t.duration), S)
          : a.transform(l, S),
        !0
      );
    }
  }
  return !1;
}
function f4(e, t) {
  return (
    e.forEach((n) => {
      const r = t.get(n.id);
      r && t.set(r.id, { ...r, [Se]: r[Se], selected: n.selected });
    }),
    new Map(t)
  );
}
function d4(e, t) {
  return t.map((n) => {
    const r = e.find((o) => o.id === n.id);
    return r && (n.selected = r.selected), n;
  });
}
function wa({ changedNodes: e, changedEdges: t, get: n, set: r }) {
  const {
    nodeInternals: o,
    edges: i,
    onNodesChange: s,
    onEdgesChange: a,
    hasDefaultNodes: l,
    hasDefaultEdges: u,
  } = n();
  e != null && e.length && (l && r({ nodeInternals: f4(e, o) }), s == null || s(e)),
    t != null && t.length && (u && r({ edges: d4(t, i) }), a == null || a(t));
}
const Zr = () => {},
  h4 = {
    zoomIn: Zr,
    zoomOut: Zr,
    zoomTo: Zr,
    getZoom: () => 1,
    setViewport: Zr,
    getViewport: () => ({ x: 0, y: 0, zoom: 1 }),
    fitView: () => !1,
    setCenter: Zr,
    fitBounds: Zr,
    project: (e) => e,
    screenToFlowPosition: (e) => e,
    flowToScreenPosition: (e) => e,
    viewportInitialized: !1,
  },
  p4 = (e) => ({ d3Zoom: e.d3Zoom, d3Selection: e.d3Selection }),
  m4 = () => {
    const e = _e(),
      { d3Zoom: t, d3Selection: n } = ce(p4, Ie);
    return v.useMemo(
      () =>
        n && t
          ? {
              zoomIn: (o) => t.scaleBy(gr(n, o == null ? void 0 : o.duration), 1.2),
              zoomOut: (o) => t.scaleBy(gr(n, o == null ? void 0 : o.duration), 1 / 1.2),
              zoomTo: (o, i) => t.scaleTo(gr(n, i == null ? void 0 : i.duration), o),
              getZoom: () => e.getState().transform[2],
              setViewport: (o, i) => {
                const [s, a, l] = e.getState().transform,
                  u = vn.translate(o.x ?? s, o.y ?? a).scale(o.zoom ?? l);
                t.transform(gr(n, i == null ? void 0 : i.duration), u);
              },
              getViewport: () => {
                const [o, i, s] = e.getState().transform;
                return { x: o, y: i, zoom: s };
              },
              fitView: (o) => vE(e.getState, o),
              setCenter: (o, i, s) => {
                const { width: a, height: l, maxZoom: u } = e.getState(),
                  c = typeof (s == null ? void 0 : s.zoom) < "u" ? s.zoom : u,
                  f = a / 2 - o * c,
                  d = l / 2 - i * c,
                  p = vn.translate(f, d).scale(c);
                t.transform(gr(n, s == null ? void 0 : s.duration), p);
              },
              fitBounds: (o, i) => {
                const { width: s, height: a, minZoom: l, maxZoom: u } = e.getState(),
                  {
                    x: c,
                    y: f,
                    zoom: d,
                  } = rE(o, s, a, l, u, (i == null ? void 0 : i.padding) ?? 0.1),
                  p = vn.translate(c, f).scale(d);
                t.transform(gr(n, i == null ? void 0 : i.duration), p);
              },
              project: (o) => {
                const { transform: i, snapToGrid: s, snapGrid: a } = e.getState();
                return (
                  console.warn(
                    "[DEPRECATED] `project` is deprecated. Instead use `screenToFlowPosition`. There is no need to subtract the react flow bounds anymore! https://reactflow.dev/api-reference/types/react-flow-instance#screen-to-flow-position",
                  ),
                  td(o, i, s, a)
                );
              },
              screenToFlowPosition: (o) => {
                const { transform: i, snapToGrid: s, snapGrid: a, domNode: l } = e.getState();
                if (!l) return o;
                const { x: u, y: c } = l.getBoundingClientRect(),
                  f = { x: o.x - u, y: o.y - c };
                return td(f, i, s, a);
              },
              flowToScreenPosition: (o) => {
                const { transform: i, domNode: s } = e.getState();
                if (!s) return o;
                const { x: a, y: l } = s.getBoundingClientRect(),
                  u = eE(o, i);
                return { x: u.x + a, y: u.y + l };
              },
              viewportInitialized: !0,
            }
          : h4,
      [t, n],
    );
  };
function Su() {
  const e = m4(),
    t = _e(),
    n = v.useCallback(
      () =>
        t
          .getState()
          .getNodes()
          .map((m) => ({ ...m })),
      [],
    ),
    r = v.useCallback((m) => t.getState().nodeInternals.get(m), []),
    o = v.useCallback(() => {
      const { edges: m = [] } = t.getState();
      return m.map((w) => ({ ...w }));
    }, []),
    i = v.useCallback((m) => {
      const { edges: w = [] } = t.getState();
      return w.find((h) => h.id === m);
    }, []),
    s = v.useCallback((m) => {
      const { getNodes: w, setNodes: h, hasDefaultNodes: g, onNodesChange: x } = t.getState(),
        S = w(),
        E = typeof m == "function" ? m(S) : m;
      if (g) h(E);
      else if (x) {
        const C =
          E.length === 0
            ? S.map((b) => ({ type: "remove", id: b.id }))
            : E.map((b) => ({ item: b, type: "reset" }));
        x(C);
      }
    }, []),
    a = v.useCallback((m) => {
      const { edges: w = [], setEdges: h, hasDefaultEdges: g, onEdgesChange: x } = t.getState(),
        S = typeof m == "function" ? m(w) : m;
      if (g) h(S);
      else if (x) {
        const E =
          S.length === 0
            ? w.map((C) => ({ type: "remove", id: C.id }))
            : S.map((C) => ({ item: C, type: "reset" }));
        x(E);
      }
    }, []),
    l = v.useCallback((m) => {
      const w = Array.isArray(m) ? m : [m],
        { getNodes: h, setNodes: g, hasDefaultNodes: x, onNodesChange: S } = t.getState();
      if (x) {
        const C = [...h(), ...w];
        g(C);
      } else if (S) {
        const E = w.map((C) => ({ item: C, type: "add" }));
        S(E);
      }
    }, []),
    u = v.useCallback((m) => {
      const w = Array.isArray(m) ? m : [m],
        { edges: h = [], setEdges: g, hasDefaultEdges: x, onEdgesChange: S } = t.getState();
      if (x) g([...h, ...w]);
      else if (S) {
        const E = w.map((C) => ({ item: C, type: "add" }));
        S(E);
      }
    }, []),
    c = v.useCallback(() => {
      const { getNodes: m, edges: w = [], transform: h } = t.getState(),
        [g, x, S] = h;
      return {
        nodes: m().map((E) => ({ ...E })),
        edges: w.map((E) => ({ ...E })),
        viewport: { x: g, y: x, zoom: S },
      };
    }, []),
    f = v.useCallback(({ nodes: m, edges: w }) => {
      const {
          nodeInternals: h,
          getNodes: g,
          edges: x,
          hasDefaultNodes: S,
          hasDefaultEdges: E,
          onNodesDelete: C,
          onEdgesDelete: b,
          onNodesChange: _,
          onEdgesChange: A,
        } = t.getState(),
        R = (m || []).map((I) => I.id),
        z = (w || []).map((I) => I.id),
        F = g().reduce((I, M) => {
          const V = M.parentNode || M.parentId,
            P = !R.includes(M.id) && V && I.find((D) => D.id === V);
          return (
            (typeof M.deletable == "boolean" ? M.deletable : !0) &&
              (R.includes(M.id) || P) &&
              I.push(M),
            I
          );
        }, []),
        j = x.filter((I) => (typeof I.deletable == "boolean" ? I.deletable : !0)),
        k = j.filter((I) => z.includes(I.id));
      if (F || k) {
        const I = nE(F, j),
          M = [...k, ...I],
          V = M.reduce((P, T) => (P.includes(T.id) || P.push(T.id), P), []);
        if (
          ((E || S) &&
            (E && t.setState({ edges: x.filter((P) => !V.includes(P.id)) }),
            S &&
              (F.forEach((P) => {
                h.delete(P.id);
              }),
              t.setState({ nodeInternals: new Map(h) }))),
          V.length > 0 && (b == null || b(M), A && A(V.map((P) => ({ id: P, type: "remove" })))),
          F.length > 0 && (C == null || C(F), _))
        ) {
          const P = F.map((T) => ({ id: T.id, type: "remove" }));
          _(P);
        }
      }
    }, []),
    d = v.useCallback((m) => {
      const w = LL(m),
        h = w ? null : t.getState().nodeInternals.get(m.id);
      return !w && !h ? [null, null, w] : [w ? m : by(h), h, w];
    }, []),
    p = v.useCallback((m, w = !0, h) => {
      const [g, x, S] = d(m);
      return g
        ? (h || t.getState().getNodes()).filter((E) => {
            if (!S && (E.id === x.id || !E.positionAbsolute)) return !1;
            const C = by(E),
              b = qf(C, g);
            return (w && b > 0) || b >= g.width * g.height;
          })
        : [];
    }, []),
    y = v.useCallback((m, w, h = !0) => {
      const [g] = d(m);
      if (!g) return !1;
      const x = qf(g, w);
      return (h && x > 0) || x >= g.width * g.height;
    }, []);
  return v.useMemo(
    () => ({
      ...e,
      getNodes: n,
      getNode: r,
      getEdges: o,
      getEdge: i,
      setNodes: s,
      setEdges: a,
      addNodes: l,
      addEdges: u,
      toObject: c,
      deleteElements: f,
      getIntersectingNodes: p,
      isNodeIntersecting: y,
    }),
    [e, n, r, o, i, s, a, l, u, c, f, p, y],
  );
}
const g4 = { actInsideInputWithModifier: !1 };
var y4 = ({ deleteKeyCode: e, multiSelectionKeyCode: t }) => {
  const n = _e(),
    { deleteElements: r } = Su(),
    o = Cs(e, g4),
    i = Cs(t);
  v.useEffect(() => {
    if (o) {
      const { edges: s, getNodes: a } = n.getState(),
        l = a().filter((c) => c.selected),
        u = s.filter((c) => c.selected);
      r({ nodes: l, edges: u }), n.setState({ nodesSelectionActive: !1 });
    }
  }, [o]),
    v.useEffect(() => {
      n.setState({ multiSelectionActive: i });
    }, [i]);
};
function v4(e) {
  const t = _e();
  v.useEffect(() => {
    let n;
    const r = () => {
      var i, s;
      if (!e.current) return;
      const o = qh(e.current);
      (o.height === 0 || o.width === 0) &&
        ((s = (i = t.getState()).onError) == null || s.call(i, "004", _n.error004())),
        t.setState({ width: o.width || 500, height: o.height || 500 });
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
const sp = { position: "absolute", width: "100%", height: "100%", top: 0, left: 0 },
  x4 = (e, t) => e.x !== t.x || e.y !== t.y || e.zoom !== t.k,
  Sa = (e) => ({ x: e.x, y: e.y, zoom: e.k }),
  Qr = (e, t) => e.target.closest(`.${t}`),
  Iy = (e, t) => t === 2 && Array.isArray(e) && e.includes(2),
  Ly = (e) => {
    const t = e.ctrlKey && Dl() ? 10 : 1;
    return -e.deltaY * (e.deltaMode === 1 ? 0.05 : e.deltaMode ? 1 : 0.002) * t;
  },
  w4 = (e) => ({
    d3Zoom: e.d3Zoom,
    d3Selection: e.d3Selection,
    d3ZoomHandler: e.d3ZoomHandler,
    userSelectionActive: e.userSelectionActive,
  }),
  S4 = ({
    onMove: e,
    onMoveStart: t,
    onMoveEnd: n,
    onPaneContextMenu: r,
    zoomOnScroll: o = !0,
    zoomOnPinch: i = !0,
    panOnScroll: s = !1,
    panOnScrollSpeed: a = 0.5,
    panOnScrollMode: l = Er.Free,
    zoomOnDoubleClick: u = !0,
    elementsSelectable: c,
    panOnDrag: f = !0,
    defaultViewport: d,
    translateExtent: p,
    minZoom: y,
    maxZoom: m,
    zoomActivationKeyCode: w,
    preventScrolling: h = !0,
    children: g,
    noWheelClassName: x,
    noPanClassName: S,
  }) => {
    const E = v.useRef(),
      C = _e(),
      b = v.useRef(!1),
      _ = v.useRef(!1),
      A = v.useRef(null),
      R = v.useRef({ x: 0, y: 0, zoom: 0 }),
      { d3Zoom: z, d3Selection: F, d3ZoomHandler: j, userSelectionActive: k } = ce(w4, Ie),
      I = Cs(w),
      M = v.useRef(0),
      V = v.useRef(!1),
      P = v.useRef();
    return (
      v4(A),
      v.useEffect(() => {
        if (A.current) {
          const T = A.current.getBoundingClientRect(),
            D = BS().scaleExtent([y, m]).translateExtent(p),
            O = Et(A.current).call(D),
            $ = vn.translate(d.x, d.y).scale(Go(d.zoom, y, m)),
            H = [
              [0, 0],
              [T.width, T.height],
            ],
            U = D.constrain()($, H, p);
          D.transform(O, U),
            D.wheelDelta(Ly),
            C.setState({
              d3Zoom: D,
              d3Selection: O,
              d3ZoomHandler: O.on("wheel.zoom"),
              transform: [U.x, U.y, U.k],
              domNode: A.current.closest(".react-flow"),
            });
        }
      }, []),
      v.useEffect(() => {
        F &&
          z &&
          (s && !I && !k
            ? F.on(
                "wheel.zoom",
                (T) => {
                  if (Qr(T, x)) return !1;
                  T.preventDefault(), T.stopImmediatePropagation();
                  const D = F.property("__zoom").k || 1;
                  if (T.ctrlKey && i) {
                    const oe = It(T),
                      re = Ly(T),
                      ne = D * Math.pow(2, re);
                    z.scaleTo(F, ne, oe, T);
                    return;
                  }
                  const O = T.deltaMode === 1 ? 20 : 1;
                  let $ = l === Er.Vertical ? 0 : T.deltaX * O,
                    H = l === Er.Horizontal ? 0 : T.deltaY * O;
                  !Dl() && T.shiftKey && l !== Er.Vertical && (($ = T.deltaY * O), (H = 0)),
                    z.translateBy(F, -($ / D) * a, -(H / D) * a, { internal: !0 });
                  const U = Sa(F.property("__zoom")),
                    {
                      onViewportChangeStart: K,
                      onViewportChange: Z,
                      onViewportChangeEnd: q,
                    } = C.getState();
                  clearTimeout(P.current),
                    V.current || ((V.current = !0), t == null || t(T, U), K == null || K(U)),
                    V.current &&
                      (e == null || e(T, U),
                      Z == null || Z(U),
                      (P.current = setTimeout(() => {
                        n == null || n(T, U), q == null || q(U), (V.current = !1);
                      }, 150)));
                },
                { passive: !1 },
              )
            : typeof j < "u" &&
              F.on(
                "wheel.zoom",
                function (T, D) {
                  if ((!h && T.type === "wheel" && !T.ctrlKey) || Qr(T, x)) return null;
                  T.preventDefault(), j.call(this, T, D);
                },
                { passive: !1 },
              ));
      }, [k, s, l, F, z, j, I, i, h, x, t, e, n]),
      v.useEffect(() => {
        z &&
          z.on("start", (T) => {
            var $, H;
            if (!T.sourceEvent || T.sourceEvent.internal) return null;
            M.current = ($ = T.sourceEvent) == null ? void 0 : $.button;
            const { onViewportChangeStart: D } = C.getState(),
              O = Sa(T.transform);
            (b.current = !0),
              (R.current = O),
              ((H = T.sourceEvent) == null ? void 0 : H.type) === "mousedown" &&
                C.setState({ paneDragging: !0 }),
              D == null || D(O),
              t == null || t(T.sourceEvent, O);
          });
      }, [z, t]),
      v.useEffect(() => {
        z &&
          (k && !b.current
            ? z.on("zoom", null)
            : k ||
              z.on("zoom", (T) => {
                var O;
                const { onViewportChange: D } = C.getState();
                if (
                  (C.setState({ transform: [T.transform.x, T.transform.y, T.transform.k] }),
                  (_.current = !!(r && Iy(f, M.current ?? 0))),
                  (e || D) && !((O = T.sourceEvent) != null && O.internal))
                ) {
                  const $ = Sa(T.transform);
                  D == null || D($), e == null || e(T.sourceEvent, $);
                }
              }));
      }, [k, z, e, f, r]),
      v.useEffect(() => {
        z &&
          z.on("end", (T) => {
            if (!T.sourceEvent || T.sourceEvent.internal) return null;
            const { onViewportChangeEnd: D } = C.getState();
            if (
              ((b.current = !1),
              C.setState({ paneDragging: !1 }),
              r && Iy(f, M.current ?? 0) && !_.current && r(T.sourceEvent),
              (_.current = !1),
              (n || D) && x4(R.current, T.transform))
            ) {
              const O = Sa(T.transform);
              (R.current = O),
                clearTimeout(E.current),
                (E.current = setTimeout(
                  () => {
                    D == null || D(O), n == null || n(T.sourceEvent, O);
                  },
                  s ? 150 : 0,
                ));
            }
          });
      }, [z, s, f, n, r]),
      v.useEffect(() => {
        z &&
          z.filter((T) => {
            const D = I || o,
              O = i && T.ctrlKey;
            if (
              (f === !0 || (Array.isArray(f) && f.includes(1))) &&
              T.button === 1 &&
              T.type === "mousedown" &&
              (Qr(T, "react-flow__node") || Qr(T, "react-flow__edge"))
            )
              return !0;
            if (
              (!f && !D && !s && !u && !i) ||
              k ||
              (!u && T.type === "dblclick") ||
              (Qr(T, x) && T.type === "wheel") ||
              (Qr(T, S) && (T.type !== "wheel" || (s && T.type === "wheel" && !I))) ||
              (!i && T.ctrlKey && T.type === "wheel") ||
              (!D && !s && !O && T.type === "wheel") ||
              (!f && (T.type === "mousedown" || T.type === "touchstart")) ||
              (Array.isArray(f) && !f.includes(T.button) && T.type === "mousedown")
            )
              return !1;
            const $ = (Array.isArray(f) && f.includes(T.button)) || !T.button || T.button <= 1;
            return (!T.ctrlKey || T.type === "wheel") && $;
          });
      }, [k, z, o, i, s, u, f, c, I]),
      L.createElement("div", { className: "react-flow__renderer", ref: A, style: sp }, g)
    );
  },
  E4 = (e) => ({
    userSelectionActive: e.userSelectionActive,
    userSelectionRect: e.userSelectionRect,
  });
function C4() {
  const { userSelectionActive: e, userSelectionRect: t } = ce(E4, Ie);
  return e && t
    ? L.createElement("div", {
        className: "react-flow__selection react-flow__container",
        style: { width: t.width, height: t.height, transform: `translate(${t.x}px, ${t.y}px)` },
      })
    : null;
}
function Vy(e, t) {
  const n = t.parentNode || t.parentId,
    r = e.find((o) => o.id === n);
  if (r) {
    const o = t.position.x + t.width - r.width,
      i = t.position.y + t.height - r.height;
    if (o > 0 || i > 0 || t.position.x < 0 || t.position.y < 0) {
      if (
        ((r.style = { ...r.style }),
        (r.style.width = r.style.width ?? r.width),
        (r.style.height = r.style.height ?? r.height),
        o > 0 && (r.style.width += o),
        i > 0 && (r.style.height += i),
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
function xE(e, t) {
  if (e.some((r) => r.type === "reset"))
    return e.filter((r) => r.type === "reset").map((r) => r.item);
  const n = e.filter((r) => r.type === "add").map((r) => r.item);
  return t.reduce((r, o) => {
    const i = e.filter((a) => a.id === o.id);
    if (i.length === 0) return r.push(o), r;
    const s = { ...o };
    for (const a of i)
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
              s.expandParent && Vy(r, s);
            break;
          }
          case "dimensions": {
            typeof a.dimensions < "u" &&
              ((s.width = a.dimensions.width), (s.height = a.dimensions.height)),
              typeof a.updateStyle < "u" && (s.style = { ...(s.style || {}), ...a.dimensions }),
              typeof a.resizing == "boolean" && (s.resizing = a.resizing),
              s.expandParent && Vy(r, s);
            break;
          }
          case "remove":
            return r;
        }
    return r.push(s), r;
  }, n);
}
function wE(e, t) {
  return xE(e, t);
}
function b4(e, t) {
  return xE(e, t);
}
const On = (e, t) => ({ id: e, type: "select", selected: t });
function yo(e, t) {
  return e.reduce((n, r) => {
    const o = t.includes(r.id);
    return (
      !r.selected && o
        ? ((r.selected = !0), n.push(On(r.id, !0)))
        : r.selected && !o && ((r.selected = !1), n.push(On(r.id, !1))),
      n
    );
  }, []);
}
const _c = (e, t) => (n) => {
    n.target === t.current && (e == null || e(n));
  },
  k4 = (e) => ({
    userSelectionActive: e.userSelectionActive,
    elementsSelectable: e.elementsSelectable,
    dragging: e.paneDragging,
  }),
  SE = v.memo(
    ({
      isSelecting: e,
      selectionMode: t = Ss.Full,
      panOnDrag: n,
      onSelectionStart: r,
      onSelectionEnd: o,
      onPaneClick: i,
      onPaneContextMenu: s,
      onPaneScroll: a,
      onPaneMouseEnter: l,
      onPaneMouseMove: u,
      onPaneMouseLeave: c,
      children: f,
    }) => {
      const d = v.useRef(null),
        p = _e(),
        y = v.useRef(0),
        m = v.useRef(0),
        w = v.useRef(),
        { userSelectionActive: h, elementsSelectable: g, dragging: x } = ce(k4, Ie),
        S = () => {
          p.setState({ userSelectionActive: !1, userSelectionRect: null }),
            (y.current = 0),
            (m.current = 0);
        },
        E = (j) => {
          i == null || i(j),
            p.getState().resetSelectedElements(),
            p.setState({ nodesSelectionActive: !1 });
        },
        C = (j) => {
          if (Array.isArray(n) && n != null && n.includes(2)) {
            j.preventDefault();
            return;
          }
          s == null || s(j);
        },
        b = a ? (j) => a(j) : void 0,
        _ = (j) => {
          const { resetSelectedElements: k, domNode: I } = p.getState();
          if (
            ((w.current = I == null ? void 0 : I.getBoundingClientRect()),
            !g || !e || j.button !== 0 || j.target !== d.current || !w.current)
          )
            return;
          const { x: M, y: V } = Zn(j, w.current);
          k(),
            p.setState({
              userSelectionRect: { width: 0, height: 0, startX: M, startY: V, x: M, y: V },
            }),
            r == null || r(j);
        },
        A = (j) => {
          const {
            userSelectionRect: k,
            nodeInternals: I,
            edges: M,
            transform: V,
            onNodesChange: P,
            onEdgesChange: T,
            nodeOrigin: D,
            getNodes: O,
          } = p.getState();
          if (!e || !w.current || !k) return;
          p.setState({ userSelectionActive: !0, nodesSelectionActive: !1 });
          const $ = Zn(j, w.current),
            H = k.startX ?? 0,
            U = k.startY ?? 0,
            K = {
              ...k,
              x: $.x < H ? $.x : H,
              y: $.y < U ? $.y : U,
              width: Math.abs($.x - H),
              height: Math.abs($.y - U),
            },
            Z = O(),
            q = tE(I, K, V, t === Ss.Partial, !0, D),
            oe = nE(q, M).map((ne) => ne.id),
            re = q.map((ne) => ne.id);
          if (y.current !== re.length) {
            y.current = re.length;
            const ne = yo(Z, re);
            ne.length && (P == null || P(ne));
          }
          if (m.current !== oe.length) {
            m.current = oe.length;
            const ne = yo(M, oe);
            ne.length && (T == null || T(ne));
          }
          p.setState({ userSelectionRect: K });
        },
        R = (j) => {
          if (j.button !== 0) return;
          const { userSelectionRect: k } = p.getState();
          !h && k && j.target === d.current && (E == null || E(j)),
            p.setState({ nodesSelectionActive: y.current > 0 }),
            S(),
            o == null || o(j);
        },
        z = (j) => {
          h && (p.setState({ nodesSelectionActive: y.current > 0 }), o == null || o(j)), S();
        },
        F = g && (e || h);
      return L.createElement(
        "div",
        {
          className: $e(["react-flow__pane", { dragging: x, selection: e }]),
          onClick: F ? void 0 : _c(E, d),
          onContextMenu: _c(C, d),
          onWheel: _c(b, d),
          onMouseEnter: F ? void 0 : l,
          onMouseDown: F ? _ : void 0,
          onMouseMove: F ? A : u,
          onMouseUp: F ? R : void 0,
          onMouseLeave: F ? z : c,
          ref: d,
          style: sp,
        },
        f,
        L.createElement(C4, null),
      );
    },
  );
SE.displayName = "Pane";
function EE(e, t) {
  const n = e.parentNode || e.parentId;
  if (!n) return !1;
  const r = t.get(n);
  return r ? (r.selected ? !0 : EE(r, t)) : !1;
}
function Oy(e, t, n) {
  let r = e;
  do {
    if (r != null && r.matches(t)) return !0;
    if (r === n.current) return !1;
    r = r.parentElement;
  } while (r);
  return !1;
}
function _4(e, t, n, r) {
  return Array.from(e.values())
    .filter(
      (o) =>
        (o.selected || o.id === r) &&
        (!o.parentNode || o.parentId || !EE(o, e)) &&
        (o.draggable || (t && typeof o.draggable > "u")),
    )
    .map((o) => {
      var i, s;
      return {
        id: o.id,
        position: o.position || { x: 0, y: 0 },
        positionAbsolute: o.positionAbsolute || { x: 0, y: 0 },
        distance: {
          x: n.x - (((i = o.positionAbsolute) == null ? void 0 : i.x) ?? 0),
          y: n.y - (((s = o.positionAbsolute) == null ? void 0 : s.y) ?? 0),
        },
        delta: { x: 0, y: 0 },
        extent: o.extent,
        parentNode: o.parentNode || o.parentId,
        parentId: o.parentNode || o.parentId,
        width: o.width,
        height: o.height,
        expandParent: o.expandParent,
      };
    });
}
function T4(e, t) {
  return !t || t === "parent" ? t : [t[0], [t[1][0] - (e.width || 0), t[1][1] - (e.height || 0)]];
}
function CE(e, t, n, r, o = [0, 0], i) {
  const s = T4(e, e.extent || r);
  let a = s;
  const l = e.parentNode || e.parentId;
  if (e.extent === "parent" && !e.expandParent)
    if (l && e.width && e.height) {
      const f = n.get(l),
        { x: d, y: p } = Nr(f, o).positionAbsolute;
      a =
        f && kt(d) && kt(p) && kt(f.width) && kt(f.height)
          ? [
              [d + e.width * o[0], p + e.height * o[1]],
              [d + f.width - e.width + e.width * o[0], p + f.height - e.height + e.height * o[1]],
            ]
          : a;
    } else i == null || i("005", _n.error005()), (a = s);
  else if (e.extent && l && e.extent !== "parent") {
    const f = n.get(l),
      { x: d, y: p } = Nr(f, o).positionAbsolute;
    a = [
      [e.extent[0][0] + d, e.extent[0][1] + p],
      [e.extent[1][0] + d, e.extent[1][1] + p],
    ];
  }
  let u = { x: 0, y: 0 };
  if (l) {
    const f = n.get(l);
    u = Nr(f, o).positionAbsolute;
  }
  const c = a && a !== "parent" ? Jh(t, a) : t;
  return { position: { x: c.x - u.x, y: c.y - u.y }, positionAbsolute: c };
}
function Tc({ nodeId: e, dragItems: t, nodeInternals: n }) {
  const r = t.map((o) => ({
    ...n.get(o.id),
    position: o.position,
    positionAbsolute: o.positionAbsolute,
  }));
  return [e ? r.find((o) => o.id === e) : r[0], r];
}
const Fy = (e, t, n, r) => {
  const o = t.querySelectorAll(e);
  if (!o || !o.length) return null;
  const i = Array.from(o),
    s = t.getBoundingClientRect(),
    a = { x: s.width * r[0], y: s.height * r[1] };
  return i.map((l) => {
    const u = l.getBoundingClientRect();
    return {
      id: l.getAttribute("data-handleid"),
      position: l.getAttribute("data-handlepos"),
      x: (u.left - s.left - a.x) / n,
      y: (u.top - s.top - a.y) / n,
      ...qh(l),
    };
  });
};
function vi(e, t, n) {
  return n === void 0
    ? n
    : (r) => {
        const o = t().nodeInternals.get(e);
        o && n(r, { ...o });
      };
}
function rd({ id: e, store: t, unselect: n = !1, nodeRef: r }) {
  const {
      addSelectedNodes: o,
      unselectNodesAndEdges: i,
      multiSelectionActive: s,
      nodeInternals: a,
      onError: l,
    } = t.getState(),
    u = a.get(e);
  if (!u) {
    l == null || l("012", _n.error012(e));
    return;
  }
  t.setState({ nodesSelectionActive: !1 }),
    u.selected
      ? (n || (u.selected && s)) &&
        (i({ nodes: [u], edges: [] }),
        requestAnimationFrame(() => {
          var c;
          return (c = r == null ? void 0 : r.current) == null ? void 0 : c.blur();
        }))
      : o([e]);
}
function N4() {
  const e = _e();
  return v.useCallback(({ sourceEvent: n }) => {
    const { transform: r, snapGrid: o, snapToGrid: i } = e.getState(),
      s = n.touches ? n.touches[0].clientX : n.clientX,
      a = n.touches ? n.touches[0].clientY : n.clientY,
      l = { x: (s - r[0]) / r[2], y: (a - r[1]) / r[2] };
    return {
      xSnapped: i ? o[0] * Math.round(l.x / o[0]) : l.x,
      ySnapped: i ? o[1] * Math.round(l.y / o[1]) : l.y,
      ...l,
    };
  }, []);
}
function Nc(e) {
  return (t, n, r) => (e == null ? void 0 : e(t, r));
}
function bE({
  nodeRef: e,
  disabled: t = !1,
  noDragClassName: n,
  handleSelector: r,
  nodeId: o,
  isSelectable: i,
  selectNodesOnDrag: s,
}) {
  const a = _e(),
    [l, u] = v.useState(!1),
    c = v.useRef([]),
    f = v.useRef({ x: null, y: null }),
    d = v.useRef(0),
    p = v.useRef(null),
    y = v.useRef({ x: 0, y: 0 }),
    m = v.useRef(null),
    w = v.useRef(!1),
    h = v.useRef(!1),
    g = v.useRef(!1),
    x = N4();
  return (
    v.useEffect(() => {
      if (e != null && e.current) {
        const S = Et(e.current),
          E = ({ x: _, y: A }) => {
            const {
              nodeInternals: R,
              onNodeDrag: z,
              onSelectionDrag: F,
              updateNodePositions: j,
              nodeExtent: k,
              snapGrid: I,
              snapToGrid: M,
              nodeOrigin: V,
              onError: P,
            } = a.getState();
            f.current = { x: _, y: A };
            let T = !1,
              D = { x: 0, y: 0, x2: 0, y2: 0 };
            if (c.current.length > 1 && k) {
              const $ = wu(c.current, V);
              D = ws($);
            }
            if (
              ((c.current = c.current.map(($) => {
                const H = { x: _ - $.distance.x, y: A - $.distance.y };
                M && ((H.x = I[0] * Math.round(H.x / I[0])), (H.y = I[1] * Math.round(H.y / I[1])));
                const U = [
                  [k[0][0], k[0][1]],
                  [k[1][0], k[1][1]],
                ];
                c.current.length > 1 &&
                  k &&
                  !$.extent &&
                  ((U[0][0] = $.positionAbsolute.x - D.x + k[0][0]),
                  (U[1][0] = $.positionAbsolute.x + ($.width ?? 0) - D.x2 + k[1][0]),
                  (U[0][1] = $.positionAbsolute.y - D.y + k[0][1]),
                  (U[1][1] = $.positionAbsolute.y + ($.height ?? 0) - D.y2 + k[1][1]));
                const K = CE($, H, R, U, V, P);
                return (
                  (T = T || $.position.x !== K.position.x || $.position.y !== K.position.y),
                  ($.position = K.position),
                  ($.positionAbsolute = K.positionAbsolute),
                  $
                );
              })),
              !T)
            )
              return;
            j(c.current, !0, !0), u(!0);
            const O = o ? z : Nc(F);
            if (O && m.current) {
              const [$, H] = Tc({ nodeId: o, dragItems: c.current, nodeInternals: R });
              O(m.current, $, H);
            }
          },
          C = () => {
            if (!p.current) return;
            const [_, A] = HS(y.current, p.current);
            if (_ !== 0 || A !== 0) {
              const { transform: R, panBy: z } = a.getState();
              (f.current.x = (f.current.x ?? 0) - _ / R[2]),
                (f.current.y = (f.current.y ?? 0) - A / R[2]),
                z({ x: _, y: A }) && E(f.current);
            }
            d.current = requestAnimationFrame(C);
          },
          b = (_) => {
            var V;
            const {
              nodeInternals: A,
              multiSelectionActive: R,
              nodesDraggable: z,
              unselectNodesAndEdges: F,
              onNodeDragStart: j,
              onSelectionDragStart: k,
            } = a.getState();
            h.current = !0;
            const I = o ? j : Nc(k);
            (!s || !i) && !R && o && (((V = A.get(o)) != null && V.selected) || F()),
              o && i && s && rd({ id: o, store: a, nodeRef: e });
            const M = x(_);
            if (((f.current = M), (c.current = _4(A, z, M, o)), I && c.current)) {
              const [P, T] = Tc({ nodeId: o, dragItems: c.current, nodeInternals: A });
              I(_.sourceEvent, P, T);
            }
          };
        if (t) S.on(".drag", null);
        else {
          const _ = zI()
            .on("start", (A) => {
              const { domNode: R, nodeDragThreshold: z } = a.getState();
              z === 0 && b(A), (g.current = !1);
              const F = x(A);
              (f.current = F),
                (p.current = (R == null ? void 0 : R.getBoundingClientRect()) || null),
                (y.current = Zn(A.sourceEvent, p.current));
            })
            .on("drag", (A) => {
              var j, k;
              const R = x(A),
                { autoPanOnNodeDrag: z, nodeDragThreshold: F } = a.getState();
              if (
                (A.sourceEvent.type === "touchmove" &&
                  A.sourceEvent.touches.length > 1 &&
                  (g.current = !0),
                !g.current)
              ) {
                if ((!w.current && h.current && z && ((w.current = !0), C()), !h.current)) {
                  const I =
                      R.xSnapped -
                      (((j = f == null ? void 0 : f.current) == null ? void 0 : j.x) ?? 0),
                    M =
                      R.ySnapped -
                      (((k = f == null ? void 0 : f.current) == null ? void 0 : k.y) ?? 0);
                  Math.sqrt(I * I + M * M) > F && b(A);
                }
                (f.current.x !== R.xSnapped || f.current.y !== R.ySnapped) &&
                  c.current &&
                  h.current &&
                  ((m.current = A.sourceEvent), (y.current = Zn(A.sourceEvent, p.current)), E(R));
              }
            })
            .on("end", (A) => {
              if (
                !(!h.current || g.current) &&
                (u(!1),
                (w.current = !1),
                (h.current = !1),
                cancelAnimationFrame(d.current),
                c.current)
              ) {
                const {
                    updateNodePositions: R,
                    nodeInternals: z,
                    onNodeDragStop: F,
                    onSelectionDragStop: j,
                  } = a.getState(),
                  k = o ? F : Nc(j);
                if ((R(c.current, !1, !1), k)) {
                  const [I, M] = Tc({ nodeId: o, dragItems: c.current, nodeInternals: z });
                  k(A.sourceEvent, I, M);
                }
              }
            })
            .filter((A) => {
              const R = A.target;
              return !A.button && (!n || !Oy(R, `.${n}`, e)) && (!r || Oy(R, r, e));
            });
          return (
            S.call(_),
            () => {
              S.on(".drag", null);
            }
          );
        }
      }
    }, [e, t, n, r, i, a, o, s, x]),
    l
  );
}
function kE() {
  const e = _e();
  return v.useCallback((n) => {
    const {
        nodeInternals: r,
        nodeExtent: o,
        updateNodePositions: i,
        getNodes: s,
        snapToGrid: a,
        snapGrid: l,
        onError: u,
        nodesDraggable: c,
      } = e.getState(),
      f = s().filter((g) => g.selected && (g.draggable || (c && typeof g.draggable > "u"))),
      d = a ? l[0] : 5,
      p = a ? l[1] : 5,
      y = n.isShiftPressed ? 4 : 1,
      m = n.x * d * y,
      w = n.y * p * y,
      h = f.map((g) => {
        if (g.positionAbsolute) {
          const x = { x: g.positionAbsolute.x + m, y: g.positionAbsolute.y + w };
          a && ((x.x = l[0] * Math.round(x.x / l[0])), (x.y = l[1] * Math.round(x.y / l[1])));
          const { positionAbsolute: S, position: E } = CE(g, x, r, o, void 0, u);
          (g.position = E), (g.positionAbsolute = S);
        }
        return g;
      });
    i(h, !0, !1);
  }, []);
}
const Po = {
  ArrowUp: { x: 0, y: -1 },
  ArrowDown: { x: 0, y: 1 },
  ArrowLeft: { x: -1, y: 0 },
  ArrowRight: { x: 1, y: 0 },
};
var xi = (e) => {
  const t = ({
    id: n,
    type: r,
    data: o,
    xPos: i,
    yPos: s,
    xPosOrigin: a,
    yPosOrigin: l,
    selected: u,
    onClick: c,
    onMouseEnter: f,
    onMouseMove: d,
    onMouseLeave: p,
    onContextMenu: y,
    onDoubleClick: m,
    style: w,
    className: h,
    isDraggable: g,
    isSelectable: x,
    isConnectable: S,
    isFocusable: E,
    selectNodesOnDrag: C,
    sourcePosition: b,
    targetPosition: _,
    hidden: A,
    resizeObserver: R,
    dragHandle: z,
    zIndex: F,
    isParent: j,
    noDragClassName: k,
    noPanClassName: I,
    initialized: M,
    disableKeyboardA11y: V,
    ariaLabel: P,
    rfId: T,
    hasHandleBounds: D,
  }) => {
    const O = _e(),
      $ = v.useRef(null),
      H = v.useRef(null),
      U = v.useRef(b),
      K = v.useRef(_),
      Z = v.useRef(r),
      q = x || g || c || f || d || p,
      oe = kE(),
      re = vi(n, O.getState, f),
      ne = vi(n, O.getState, d),
      Le = vi(n, O.getState, p),
      Te = vi(n, O.getState, y),
      Ye = vi(n, O.getState, m),
      je = (se) => {
        const { nodeDragThreshold: Y } = O.getState();
        if ((x && (!C || !g || Y > 0) && rd({ id: n, store: O, nodeRef: $ }), c)) {
          const Xe = O.getState().nodeInternals.get(n);
          Xe && c(se, { ...Xe });
        }
      },
      Ee = (se) => {
        if (!Jf(se) && !V)
          if (YS.includes(se.key) && x) {
            const Y = se.key === "Escape";
            rd({ id: n, store: O, unselect: Y, nodeRef: $ });
          } else
            g &&
              u &&
              Object.prototype.hasOwnProperty.call(Po, se.key) &&
              (O.setState({
                ariaLiveMessage: `Moved selected node ${se.key.replace("Arrow", "").toLowerCase()}. New position, x: ${~~i}, y: ${~~s}`,
              }),
              oe({ x: Po[se.key].x, y: Po[se.key].y, isShiftPressed: se.shiftKey }));
      };
    v.useEffect(
      () => () => {
        H.current && (R == null || R.unobserve(H.current), (H.current = null));
      },
      [],
    ),
      v.useEffect(() => {
        if ($.current && !A) {
          const se = $.current;
          (!M || !D || H.current !== se) &&
            (H.current && (R == null || R.unobserve(H.current)),
            R == null || R.observe(se),
            (H.current = se));
        }
      }, [A, M, D]),
      v.useEffect(() => {
        const se = Z.current !== r,
          Y = U.current !== b,
          Xe = K.current !== _;
        $.current &&
          (se || Y || Xe) &&
          (se && (Z.current = r),
          Y && (U.current = b),
          Xe && (K.current = _),
          O.getState().updateNodeDimensions([{ id: n, nodeElement: $.current, forceUpdate: !0 }]));
      }, [n, r, b, _]);
    const lt = bE({
      nodeRef: $,
      disabled: A || !g,
      noDragClassName: k,
      handleSelector: z,
      nodeId: n,
      isSelectable: x,
      selectNodesOnDrag: C,
    });
    return A
      ? null
      : L.createElement(
          "div",
          {
            className: $e([
              "react-flow__node",
              `react-flow__node-${r}`,
              { [I]: g },
              h,
              { selected: u, selectable: x, parent: j, dragging: lt },
            ]),
            ref: $,
            style: {
              zIndex: F,
              transform: `translate(${a}px,${l}px)`,
              pointerEvents: q ? "all" : "none",
              visibility: M ? "visible" : "hidden",
              ...w,
            },
            "data-id": n,
            "data-testid": `rf__node-${n}`,
            onMouseEnter: re,
            onMouseMove: ne,
            onMouseLeave: Le,
            onContextMenu: Te,
            onClick: je,
            onDoubleClick: Ye,
            onKeyDown: E ? Ee : void 0,
            tabIndex: E ? 0 : void 0,
            role: E ? "button" : void 0,
            "aria-describedby": V ? void 0 : `${pE}-${T}`,
            "aria-label": P,
          },
          L.createElement(
            BL,
            { value: n },
            L.createElement(e, {
              id: n,
              data: o,
              type: r,
              xPos: i,
              yPos: s,
              selected: u,
              isConnectable: S,
              sourcePosition: b,
              targetPosition: _,
              dragging: lt,
              dragHandle: z,
              zIndex: F,
            }),
          ),
        );
  };
  return (t.displayName = "NodeWrapper"), v.memo(t);
};
const P4 = (e) => {
  const t = e.getNodes().filter((n) => n.selected);
  return {
    ...wu(t, e.nodeOrigin),
    transformString: `translate(${e.transform[0]}px,${e.transform[1]}px) scale(${e.transform[2]})`,
    userSelectionActive: e.userSelectionActive,
  };
};
function M4({ onSelectionContextMenu: e, noPanClassName: t, disableKeyboardA11y: n }) {
  const r = _e(),
    { width: o, height: i, x: s, y: a, transformString: l, userSelectionActive: u } = ce(P4, Ie),
    c = kE(),
    f = v.useRef(null);
  if (
    (v.useEffect(() => {
      var y;
      n || (y = f.current) == null || y.focus({ preventScroll: !0 });
    }, [n]),
    bE({ nodeRef: f }),
    u || !o || !i)
  )
    return null;
  const d = e
      ? (y) => {
          const m = r
            .getState()
            .getNodes()
            .filter((w) => w.selected);
          e(y, m);
        }
      : void 0,
    p = (y) => {
      Object.prototype.hasOwnProperty.call(Po, y.key) &&
        c({ x: Po[y.key].x, y: Po[y.key].y, isShiftPressed: y.shiftKey });
    };
  return L.createElement(
    "div",
    {
      className: $e(["react-flow__nodesselection", "react-flow__container", t]),
      style: { transform: l },
    },
    L.createElement("div", {
      ref: f,
      className: "react-flow__nodesselection-rect",
      onContextMenu: d,
      tabIndex: n ? void 0 : -1,
      onKeyDown: n ? void 0 : p,
      style: { width: o, height: i, top: a, left: s },
    }),
  );
}
var A4 = v.memo(M4);
const R4 = (e) => e.nodesSelectionActive,
  _E = ({
    children: e,
    onPaneClick: t,
    onPaneMouseEnter: n,
    onPaneMouseMove: r,
    onPaneMouseLeave: o,
    onPaneContextMenu: i,
    onPaneScroll: s,
    deleteKeyCode: a,
    onMove: l,
    onMoveStart: u,
    onMoveEnd: c,
    selectionKeyCode: f,
    selectionOnDrag: d,
    selectionMode: p,
    onSelectionStart: y,
    onSelectionEnd: m,
    multiSelectionKeyCode: w,
    panActivationKeyCode: h,
    zoomActivationKeyCode: g,
    elementsSelectable: x,
    zoomOnScroll: S,
    zoomOnPinch: E,
    panOnScroll: C,
    panOnScrollSpeed: b,
    panOnScrollMode: _,
    zoomOnDoubleClick: A,
    panOnDrag: R,
    defaultViewport: z,
    translateExtent: F,
    minZoom: j,
    maxZoom: k,
    preventScrolling: I,
    onSelectionContextMenu: M,
    noWheelClassName: V,
    noPanClassName: P,
    disableKeyboardA11y: T,
  }) => {
    const D = ce(R4),
      O = Cs(f),
      $ = Cs(h),
      H = $ || R,
      U = $ || C,
      K = O || (d && H !== !0);
    return (
      y4({ deleteKeyCode: a, multiSelectionKeyCode: w }),
      L.createElement(
        S4,
        {
          onMove: l,
          onMoveStart: u,
          onMoveEnd: c,
          onPaneContextMenu: i,
          elementsSelectable: x,
          zoomOnScroll: S,
          zoomOnPinch: E,
          panOnScroll: U,
          panOnScrollSpeed: b,
          panOnScrollMode: _,
          zoomOnDoubleClick: A,
          panOnDrag: !O && H,
          defaultViewport: z,
          translateExtent: F,
          minZoom: j,
          maxZoom: k,
          zoomActivationKeyCode: g,
          preventScrolling: I,
          noWheelClassName: V,
          noPanClassName: P,
        },
        L.createElement(
          SE,
          {
            onSelectionStart: y,
            onSelectionEnd: m,
            onPaneClick: t,
            onPaneMouseEnter: n,
            onPaneMouseMove: r,
            onPaneMouseLeave: o,
            onPaneContextMenu: i,
            onPaneScroll: s,
            panOnDrag: H,
            isSelecting: !!K,
            selectionMode: p,
          },
          e,
          D &&
            L.createElement(A4, {
              onSelectionContextMenu: M,
              noPanClassName: P,
              disableKeyboardA11y: T,
            }),
        ),
      )
    );
  };
_E.displayName = "FlowRenderer";
var D4 = v.memo(_E);
function I4(e) {
  return ce(
    v.useCallback(
      (n) =>
        e
          ? tE(n.nodeInternals, { x: 0, y: 0, width: n.width, height: n.height }, n.transform, !0)
          : n.getNodes(),
      [e],
    ),
  );
}
function L4(e) {
  const t = {
      input: xi(e.input || cE),
      default: xi(e.default || nd),
      output: xi(e.output || dE),
      group: xi(e.group || ip),
    },
    n = {},
    r = Object.keys(e)
      .filter((o) => !["input", "default", "output", "group"].includes(o))
      .reduce((o, i) => ((o[i] = xi(e[i] || nd)), o), n);
  return { ...t, ...r };
}
const V4 = ({ x: e, y: t, width: n, height: r, origin: o }) =>
    !n || !r
      ? { x: e, y: t }
      : o[0] < 0 || o[1] < 0 || o[0] > 1 || o[1] > 1
        ? { x: e, y: t }
        : { x: e - n * o[0], y: t - r * o[1] },
  O4 = (e) => ({
    nodesDraggable: e.nodesDraggable,
    nodesConnectable: e.nodesConnectable,
    nodesFocusable: e.nodesFocusable,
    elementsSelectable: e.elementsSelectable,
    updateNodeDimensions: e.updateNodeDimensions,
    onError: e.onError,
  }),
  TE = (e) => {
    const {
        nodesDraggable: t,
        nodesConnectable: n,
        nodesFocusable: r,
        elementsSelectable: o,
        updateNodeDimensions: i,
        onError: s,
      } = ce(O4, Ie),
      a = I4(e.onlyRenderVisibleElements),
      l = v.useRef(),
      u = v.useMemo(() => {
        if (typeof ResizeObserver > "u") return null;
        const c = new ResizeObserver((f) => {
          const d = f.map((p) => ({
            id: p.target.getAttribute("data-id"),
            nodeElement: p.target,
            forceUpdate: !0,
          }));
          i(d);
        });
        return (l.current = c), c;
      }, []);
    return (
      v.useEffect(
        () => () => {
          var c;
          (c = l == null ? void 0 : l.current) == null || c.disconnect();
        },
        [],
      ),
      L.createElement(
        "div",
        { className: "react-flow__nodes", style: sp },
        a.map((c) => {
          var E, C, b;
          let f = c.type || "default";
          e.nodeTypes[f] || (s == null || s("003", _n.error003(f)), (f = "default"));
          const d = e.nodeTypes[f] || e.nodeTypes.default,
            p = !!(c.draggable || (t && typeof c.draggable > "u")),
            y = !!(c.selectable || (o && typeof c.selectable > "u")),
            m = !!(c.connectable || (n && typeof c.connectable > "u")),
            w = !!(c.focusable || (r && typeof c.focusable > "u")),
            h = e.nodeExtent ? Jh(c.positionAbsolute, e.nodeExtent) : c.positionAbsolute,
            g = (h == null ? void 0 : h.x) ?? 0,
            x = (h == null ? void 0 : h.y) ?? 0,
            S = V4({
              x: g,
              y: x,
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
            sourcePosition: c.sourcePosition || G.Bottom,
            targetPosition: c.targetPosition || G.Top,
            hidden: c.hidden,
            xPos: g,
            yPos: x,
            xPosOrigin: S.x,
            yPosOrigin: S.y,
            selectNodesOnDrag: e.selectNodesOnDrag,
            onClick: e.onNodeClick,
            onMouseEnter: e.onNodeMouseEnter,
            onMouseMove: e.onNodeMouseMove,
            onMouseLeave: e.onNodeMouseLeave,
            onContextMenu: e.onNodeContextMenu,
            onDoubleClick: e.onNodeDoubleClick,
            selected: !!c.selected,
            isDraggable: p,
            isSelectable: y,
            isConnectable: m,
            isFocusable: w,
            resizeObserver: u,
            dragHandle: c.dragHandle,
            zIndex: ((E = c[Se]) == null ? void 0 : E.z) ?? 0,
            isParent: !!((C = c[Se]) != null && C.isParent),
            noDragClassName: e.noDragClassName,
            noPanClassName: e.noPanClassName,
            initialized: !!c.width && !!c.height,
            rfId: e.rfId,
            disableKeyboardA11y: e.disableKeyboardA11y,
            ariaLabel: c.ariaLabel,
            hasHandleBounds: !!((b = c[Se]) != null && b.handleBounds),
          });
        }),
      )
    );
  };
TE.displayName = "NodeRenderer";
var F4 = v.memo(TE);
const z4 = (e, t, n) => (n === G.Left ? e - t : n === G.Right ? e + t : e),
  $4 = (e, t, n) => (n === G.Top ? e - t : n === G.Bottom ? e + t : e),
  zy = "react-flow__edgeupdater",
  $y = ({
    position: e,
    centerX: t,
    centerY: n,
    radius: r = 10,
    onMouseDown: o,
    onMouseEnter: i,
    onMouseOut: s,
    type: a,
  }) =>
    L.createElement("circle", {
      onMouseDown: o,
      onMouseEnter: i,
      onMouseOut: s,
      className: $e([zy, `${zy}-${a}`]),
      cx: z4(t, r, e),
      cy: $4(n, r, e),
      r,
      stroke: "transparent",
      fill: "transparent",
    }),
  j4 = () => !0;
var qr = (e) => {
  const t = ({
    id: n,
    className: r,
    type: o,
    data: i,
    onClick: s,
    onEdgeDoubleClick: a,
    selected: l,
    animated: u,
    label: c,
    labelStyle: f,
    labelShowBg: d,
    labelBgStyle: p,
    labelBgPadding: y,
    labelBgBorderRadius: m,
    style: w,
    source: h,
    target: g,
    sourceX: x,
    sourceY: S,
    targetX: E,
    targetY: C,
    sourcePosition: b,
    targetPosition: _,
    elementsSelectable: A,
    hidden: R,
    sourceHandleId: z,
    targetHandleId: F,
    onContextMenu: j,
    onMouseEnter: k,
    onMouseMove: I,
    onMouseLeave: M,
    reconnectRadius: V,
    onReconnect: P,
    onReconnectStart: T,
    onReconnectEnd: D,
    markerEnd: O,
    markerStart: $,
    rfId: H,
    ariaLabel: U,
    isFocusable: K,
    isReconnectable: Z,
    pathOptions: q,
    interactionWidth: oe,
    disableKeyboardA11y: re,
  }) => {
    const ne = v.useRef(null),
      [Le, Te] = v.useState(!1),
      [Ye, je] = v.useState(!1),
      Ee = _e(),
      lt = v.useMemo(() => `url('#${ed($, H)}')`, [$, H]),
      se = v.useMemo(() => `url('#${ed(O, H)}')`, [O, H]);
    if (R) return null;
    const Y = (Be) => {
        var Ut;
        const {
            edges: Pt,
            addSelectedEdges: ar,
            unselectNodesAndEdges: lr,
            multiSelectionActive: ur,
          } = Ee.getState(),
          sn = Pt.find((ni) => ni.id === n);
        sn &&
          (A &&
            (Ee.setState({ nodesSelectionActive: !1 }),
            sn.selected && ur
              ? (lr({ nodes: [], edges: [sn] }), (Ut = ne.current) == null || Ut.blur())
              : ar([n])),
          s && s(Be, sn));
      },
      Xe = yi(n, Ee.getState, a),
      rn = yi(n, Ee.getState, j),
      ei = yi(n, Ee.getState, k),
      $r = yi(n, Ee.getState, I),
      jr = yi(n, Ee.getState, M),
      on = (Be, Pt) => {
        if (Be.button !== 0) return;
        const { edges: ar, isValidConnection: lr } = Ee.getState(),
          ur = Pt ? g : h,
          sn = (Pt ? F : z) || null,
          Ut = Pt ? "target" : "source",
          ni = lr || j4,
          Eu = Pt,
          ri = ar.find((cr) => cr.id === n);
        je(!0), T == null || T(Be, ri, Ut);
        const Cu = (cr) => {
          je(!1), D == null || D(cr, ri, Ut);
        };
        sE({
          event: Be,
          handleId: sn,
          nodeId: ur,
          onConnect: (cr) => (P == null ? void 0 : P(ri, cr)),
          isTarget: Eu,
          getState: Ee.getState,
          setState: Ee.setState,
          isValidConnection: ni,
          edgeUpdaterType: Ut,
          onReconnectEnd: Cu,
        });
      },
      Br = (Be) => on(Be, !0),
      ir = (Be) => on(Be, !1),
      sr = () => Te(!0),
      Ur = () => Te(!1),
      Hr = !A && !s,
      ti = (Be) => {
        var Pt;
        if (!re && YS.includes(Be.key) && A) {
          const { unselectNodesAndEdges: ar, addSelectedEdges: lr, edges: ur } = Ee.getState();
          Be.key === "Escape"
            ? ((Pt = ne.current) == null || Pt.blur(),
              ar({ edges: [ur.find((Ut) => Ut.id === n)] }))
            : lr([n]);
        }
      };
    return L.createElement(
      "g",
      {
        className: $e([
          "react-flow__edge",
          `react-flow__edge-${o}`,
          r,
          { selected: l, animated: u, inactive: Hr, updating: Le },
        ]),
        onClick: Y,
        onDoubleClick: Xe,
        onContextMenu: rn,
        onMouseEnter: ei,
        onMouseMove: $r,
        onMouseLeave: jr,
        onKeyDown: K ? ti : void 0,
        tabIndex: K ? 0 : void 0,
        role: K ? "button" : "img",
        "data-testid": `rf__edge-${n}`,
        "aria-label": U === null ? void 0 : U || `Edge from ${h} to ${g}`,
        "aria-describedby": K ? `${mE}-${H}` : void 0,
        ref: ne,
      },
      !Ye &&
        L.createElement(e, {
          id: n,
          source: h,
          target: g,
          selected: l,
          animated: u,
          label: c,
          labelStyle: f,
          labelShowBg: d,
          labelBgStyle: p,
          labelBgPadding: y,
          labelBgBorderRadius: m,
          data: i,
          style: w,
          sourceX: x,
          sourceY: S,
          targetX: E,
          targetY: C,
          sourcePosition: b,
          targetPosition: _,
          sourceHandleId: z,
          targetHandleId: F,
          markerStart: lt,
          markerEnd: se,
          pathOptions: q,
          interactionWidth: oe,
        }),
      Z &&
        L.createElement(
          L.Fragment,
          null,
          (Z === "source" || Z === !0) &&
            L.createElement($y, {
              position: b,
              centerX: x,
              centerY: S,
              radius: V,
              onMouseDown: Br,
              onMouseEnter: sr,
              onMouseOut: Ur,
              type: "source",
            }),
          (Z === "target" || Z === !0) &&
            L.createElement($y, {
              position: _,
              centerX: E,
              centerY: C,
              radius: V,
              onMouseDown: ir,
              onMouseEnter: sr,
              onMouseOut: Ur,
              type: "target",
            }),
        ),
    );
  };
  return (t.displayName = "EdgeWrapper"), v.memo(t);
};
function B4(e) {
  const t = {
      default: qr(e.default || Ll),
      straight: qr(e.bezier || np),
      step: qr(e.step || tp),
      smoothstep: qr(e.step || xu),
      simplebezier: qr(e.simplebezier || ep),
    },
    n = {},
    r = Object.keys(e)
      .filter((o) => !["default", "bezier"].includes(o))
      .reduce((o, i) => ((o[i] = qr(e[i] || Ll)), o), n);
  return { ...t, ...r };
}
function jy(e, t, n = null) {
  const r = ((n == null ? void 0 : n.x) || 0) + t.x,
    o = ((n == null ? void 0 : n.y) || 0) + t.y,
    i = (n == null ? void 0 : n.width) || t.width,
    s = (n == null ? void 0 : n.height) || t.height;
  switch (e) {
    case G.Top:
      return { x: r + i / 2, y: o };
    case G.Right:
      return { x: r + i, y: o + s / 2 };
    case G.Bottom:
      return { x: r + i / 2, y: o + s };
    case G.Left:
      return { x: r, y: o + s / 2 };
  }
}
function By(e, t) {
  return e ? (e.length === 1 || !t ? e[0] : (t && e.find((n) => n.id === t)) || null) : null;
}
const U4 = (e, t, n, r, o, i) => {
  const s = jy(n, e, t),
    a = jy(i, r, o);
  return { sourceX: s.x, sourceY: s.y, targetX: a.x, targetY: a.y };
};
function H4({
  sourcePos: e,
  targetPos: t,
  sourceWidth: n,
  sourceHeight: r,
  targetWidth: o,
  targetHeight: i,
  width: s,
  height: a,
  transform: l,
}) {
  const u = {
    x: Math.min(e.x, t.x),
    y: Math.min(e.y, t.y),
    x2: Math.max(e.x + n, t.x + o),
    y2: Math.max(e.y + r, t.y + i),
  };
  u.x === u.x2 && (u.x2 += 1), u.y === u.y2 && (u.y2 += 1);
  const c = ws({ x: (0 - l[0]) / l[2], y: (0 - l[1]) / l[2], width: s / l[2], height: a / l[2] }),
    f = Math.max(0, Math.min(c.x2, u.x2) - Math.max(c.x, u.x)),
    d = Math.max(0, Math.min(c.y2, u.y2) - Math.max(c.y, u.y));
  return Math.ceil(f * d) > 0;
}
function Uy(e) {
  var r, o, i, s, a;
  const t = ((r = e == null ? void 0 : e[Se]) == null ? void 0 : r.handleBounds) || null,
    n =
      t &&
      (e == null ? void 0 : e.width) &&
      (e == null ? void 0 : e.height) &&
      typeof ((o = e == null ? void 0 : e.positionAbsolute) == null ? void 0 : o.x) < "u" &&
      typeof ((i = e == null ? void 0 : e.positionAbsolute) == null ? void 0 : i.y) < "u";
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
const W4 = [{ level: 0, isMaxLevel: !0, edges: [] }];
function G4(e, t, n = !1) {
  let r = -1;
  const o = e.reduce((s, a) => {
      var c, f;
      const l = kt(a.zIndex);
      let u = l ? a.zIndex : 0;
      if (n) {
        const d = t.get(a.target),
          p = t.get(a.source),
          y = a.selected || (d == null ? void 0 : d.selected) || (p == null ? void 0 : p.selected),
          m = Math.max(
            ((c = p == null ? void 0 : p[Se]) == null ? void 0 : c.z) || 0,
            ((f = d == null ? void 0 : d[Se]) == null ? void 0 : f.z) || 0,
            1e3,
          );
        u = (l ? a.zIndex : 0) + (y ? m : 0);
      }
      return s[u] ? s[u].push(a) : (s[u] = [a]), (r = u > r ? u : r), s;
    }, {}),
    i = Object.entries(o).map(([s, a]) => {
      const l = +s;
      return { edges: a, level: l, isMaxLevel: l === r };
    });
  return i.length === 0 ? W4 : i;
}
function K4(e, t, n) {
  const r = ce(
    v.useCallback(
      (o) =>
        e
          ? o.edges.filter((i) => {
              const s = t.get(i.source),
                a = t.get(i.target);
              return (
                (s == null ? void 0 : s.width) &&
                (s == null ? void 0 : s.height) &&
                (a == null ? void 0 : a.width) &&
                (a == null ? void 0 : a.height) &&
                H4({
                  sourcePos: s.positionAbsolute || { x: 0, y: 0 },
                  targetPos: a.positionAbsolute || { x: 0, y: 0 },
                  sourceWidth: s.width,
                  sourceHeight: s.height,
                  targetWidth: a.width,
                  targetHeight: a.height,
                  width: o.width,
                  height: o.height,
                  transform: o.transform,
                })
              );
            })
          : o.edges,
      [e, t],
    ),
  );
  return G4(r, t, n);
}
const Y4 = ({ color: e = "none", strokeWidth: t = 1 }) =>
    L.createElement("polyline", {
      style: { stroke: e, strokeWidth: t },
      strokeLinecap: "round",
      strokeLinejoin: "round",
      fill: "none",
      points: "-5,-4 0,0 -5,4",
    }),
  X4 = ({ color: e = "none", strokeWidth: t = 1 }) =>
    L.createElement("polyline", {
      style: { stroke: e, fill: e, strokeWidth: t },
      strokeLinecap: "round",
      strokeLinejoin: "round",
      points: "-5,-4 0,0 -5,4 -5,-4",
    }),
  Hy = { [Es.Arrow]: Y4, [Es.ArrowClosed]: X4 };
function Z4(e) {
  const t = _e();
  return v.useMemo(() => {
    var o, i;
    return Object.prototype.hasOwnProperty.call(Hy, e)
      ? Hy[e]
      : ((i = (o = t.getState()).onError) == null || i.call(o, "009", _n.error009(e)), null);
  }, [e]);
}
const Q4 = ({
    id: e,
    type: t,
    color: n,
    width: r = 12.5,
    height: o = 12.5,
    markerUnits: i = "strokeWidth",
    strokeWidth: s,
    orient: a = "auto-start-reverse",
  }) => {
    const l = Z4(t);
    return l
      ? L.createElement(
          "marker",
          {
            className: "react-flow__arrowhead",
            id: e,
            markerWidth: `${r}`,
            markerHeight: `${o}`,
            viewBox: "-10 -10 20 20",
            markerUnits: i,
            orient: a,
            refX: "0",
            refY: "0",
          },
          L.createElement(l, { color: n, strokeWidth: s }),
        )
      : null;
  },
  q4 =
    ({ defaultColor: e, rfId: t }) =>
    (n) => {
      const r = [];
      return n.edges
        .reduce(
          (o, i) => (
            [i.markerStart, i.markerEnd].forEach((s) => {
              if (s && typeof s == "object") {
                const a = ed(s, t);
                r.includes(a) || (o.push({ id: a, color: s.color || e, ...s }), r.push(a));
              }
            }),
            o
          ),
          [],
        )
        .sort((o, i) => o.id.localeCompare(i.id));
    },
  NE = ({ defaultColor: e, rfId: t }) => {
    const n = ce(
      v.useCallback(q4({ defaultColor: e, rfId: t }), [e, t]),
      (r, o) => !(r.length !== o.length || r.some((i, s) => i.id !== o[s].id)),
    );
    return L.createElement(
      "defs",
      null,
      n.map((r) =>
        L.createElement(Q4, {
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
NE.displayName = "MarkerDefinitions";
var J4 = v.memo(NE);
const eV = (e) => ({
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
  PE = ({
    defaultMarkerColor: e,
    onlyRenderVisibleElements: t,
    elevateEdgesOnSelect: n,
    rfId: r,
    edgeTypes: o,
    noPanClassName: i,
    onEdgeContextMenu: s,
    onEdgeMouseEnter: a,
    onEdgeMouseMove: l,
    onEdgeMouseLeave: u,
    onEdgeClick: c,
    onEdgeDoubleClick: f,
    onReconnect: d,
    onReconnectStart: p,
    onReconnectEnd: y,
    reconnectRadius: m,
    children: w,
    disableKeyboardA11y: h,
  }) => {
    const {
        edgesFocusable: g,
        edgesUpdatable: x,
        elementsSelectable: S,
        width: E,
        height: C,
        connectionMode: b,
        nodeInternals: _,
        onError: A,
      } = ce(eV, Ie),
      R = K4(t, _, n);
    return E
      ? L.createElement(
          L.Fragment,
          null,
          R.map(({ level: z, edges: F, isMaxLevel: j }) =>
            L.createElement(
              "svg",
              {
                key: z,
                style: { zIndex: z },
                width: E,
                height: C,
                className: "react-flow__edges react-flow__container",
              },
              j && L.createElement(J4, { defaultColor: e, rfId: r }),
              L.createElement(
                "g",
                null,
                F.map((k) => {
                  const [I, M, V] = Uy(_.get(k.source)),
                    [P, T, D] = Uy(_.get(k.target));
                  if (!V || !D) return null;
                  let O = k.type || "default";
                  o[O] || (A == null || A("011", _n.error011(O)), (O = "default"));
                  const $ = o[O] || o.default,
                    H = b === Vr.Strict ? T.target : (T.target ?? []).concat(T.source ?? []),
                    U = By(M.source, k.sourceHandle),
                    K = By(H, k.targetHandle),
                    Z = (U == null ? void 0 : U.position) || G.Bottom,
                    q = (K == null ? void 0 : K.position) || G.Top,
                    oe = !!(k.focusable || (g && typeof k.focusable > "u")),
                    re = k.reconnectable || k.updatable,
                    ne = typeof d < "u" && (re || (x && typeof re > "u"));
                  if (!U || !K) return A == null || A("008", _n.error008(U, k)), null;
                  const {
                    sourceX: Le,
                    sourceY: Te,
                    targetX: Ye,
                    targetY: je,
                  } = U4(I, U, Z, P, K, q);
                  return L.createElement($, {
                    key: k.id,
                    id: k.id,
                    className: $e([k.className, i]),
                    type: O,
                    data: k.data,
                    selected: !!k.selected,
                    animated: !!k.animated,
                    hidden: !!k.hidden,
                    label: k.label,
                    labelStyle: k.labelStyle,
                    labelShowBg: k.labelShowBg,
                    labelBgStyle: k.labelBgStyle,
                    labelBgPadding: k.labelBgPadding,
                    labelBgBorderRadius: k.labelBgBorderRadius,
                    style: k.style,
                    source: k.source,
                    target: k.target,
                    sourceHandleId: k.sourceHandle,
                    targetHandleId: k.targetHandle,
                    markerEnd: k.markerEnd,
                    markerStart: k.markerStart,
                    sourceX: Le,
                    sourceY: Te,
                    targetX: Ye,
                    targetY: je,
                    sourcePosition: Z,
                    targetPosition: q,
                    elementsSelectable: S,
                    onContextMenu: s,
                    onMouseEnter: a,
                    onMouseMove: l,
                    onMouseLeave: u,
                    onClick: c,
                    onEdgeDoubleClick: f,
                    onReconnect: d,
                    onReconnectStart: p,
                    onReconnectEnd: y,
                    reconnectRadius: m,
                    rfId: r,
                    ariaLabel: k.ariaLabel,
                    isFocusable: oe,
                    isReconnectable: ne,
                    pathOptions: "pathOptions" in k ? k.pathOptions : void 0,
                    interactionWidth: k.interactionWidth,
                    disableKeyboardA11y: h,
                  });
                }),
              ),
            ),
          ),
          w,
        )
      : null;
  };
PE.displayName = "EdgeRenderer";
var tV = v.memo(PE);
const nV = (e) => `translate(${e.transform[0]}px,${e.transform[1]}px) scale(${e.transform[2]})`;
function rV({ children: e }) {
  const t = ce(nV);
  return L.createElement(
    "div",
    { className: "react-flow__viewport react-flow__container", style: { transform: t } },
    e,
  );
}
function oV(e) {
  const t = Su(),
    n = v.useRef(!1);
  v.useEffect(() => {
    !n.current && t.viewportInitialized && e && (setTimeout(() => e(t), 1), (n.current = !0));
  }, [e, t.viewportInitialized]);
}
const iV = { [G.Left]: G.Right, [G.Right]: G.Left, [G.Top]: G.Bottom, [G.Bottom]: G.Top },
  ME = ({
    nodeId: e,
    handleType: t,
    style: n,
    type: r = fn.Bezier,
    CustomComponent: o,
    connectionStatus: i,
  }) => {
    var C, b, _;
    const {
        fromNode: s,
        handleId: a,
        toX: l,
        toY: u,
        connectionMode: c,
      } = ce(
        v.useCallback(
          (A) => ({
            fromNode: A.nodeInternals.get(e),
            handleId: A.connectionHandleId,
            toX: (A.connectionPosition.x - A.transform[0]) / A.transform[2],
            toY: (A.connectionPosition.y - A.transform[1]) / A.transform[2],
            connectionMode: A.connectionMode,
          }),
          [e],
        ),
        Ie,
      ),
      f = (C = s == null ? void 0 : s[Se]) == null ? void 0 : C.handleBounds;
    let d = f == null ? void 0 : f[t];
    if (
      (c === Vr.Loose && (d = d || (f == null ? void 0 : f[t === "source" ? "target" : "source"])),
      !s || !d)
    )
      return null;
    const p = a ? d.find((A) => A.id === a) : d[0],
      y = p ? p.x + p.width / 2 : (s.width ?? 0) / 2,
      m = p ? p.y + p.height / 2 : (s.height ?? 0),
      w = (((b = s.positionAbsolute) == null ? void 0 : b.x) ?? 0) + y,
      h = (((_ = s.positionAbsolute) == null ? void 0 : _.y) ?? 0) + m,
      g = p == null ? void 0 : p.position,
      x = g ? iV[g] : null;
    if (!g || !x) return null;
    if (o)
      return L.createElement(o, {
        connectionLineType: r,
        connectionLineStyle: n,
        fromNode: s,
        fromHandle: p,
        fromX: w,
        fromY: h,
        toX: l,
        toY: u,
        fromPosition: g,
        toPosition: x,
        connectionStatus: i,
      });
    let S = "";
    const E = {
      sourceX: w,
      sourceY: h,
      sourcePosition: g,
      targetX: l,
      targetY: u,
      targetPosition: x,
    };
    return (
      r === fn.Bezier
        ? ([S] = JS(E))
        : r === fn.Step
          ? ([S] = Il({ ...E, borderRadius: 0 }))
          : r === fn.SmoothStep
            ? ([S] = Il(E))
            : r === fn.SimpleBezier
              ? ([S] = qS(E))
              : (S = `M${w},${h} ${l},${u}`),
      L.createElement("path", {
        d: S,
        fill: "none",
        className: "react-flow__connection-path",
        style: n,
      })
    );
  };
ME.displayName = "ConnectionLine";
const sV = (e) => ({
  nodeId: e.connectionNodeId,
  handleType: e.connectionHandleType,
  nodesConnectable: e.nodesConnectable,
  connectionStatus: e.connectionStatus,
  width: e.width,
  height: e.height,
});
function aV({ containerStyle: e, style: t, type: n, component: r }) {
  const {
    nodeId: o,
    handleType: i,
    nodesConnectable: s,
    width: a,
    height: l,
    connectionStatus: u,
  } = ce(sV, Ie);
  return !(o && i && a && s)
    ? null
    : L.createElement(
        "svg",
        {
          style: e,
          width: a,
          height: l,
          className: "react-flow__edges react-flow__connectionline react-flow__container",
        },
        L.createElement(
          "g",
          { className: $e(["react-flow__connection", u]) },
          L.createElement(ME, {
            nodeId: o,
            handleType: i,
            style: t,
            type: n,
            CustomComponent: r,
            connectionStatus: u,
          }),
        ),
      );
}
function Wy(e, t) {
  return v.useRef(null), _e(), v.useMemo(() => t(e), [e]);
}
const AE = ({
  nodeTypes: e,
  edgeTypes: t,
  onMove: n,
  onMoveStart: r,
  onMoveEnd: o,
  onInit: i,
  onNodeClick: s,
  onEdgeClick: a,
  onNodeDoubleClick: l,
  onEdgeDoubleClick: u,
  onNodeMouseEnter: c,
  onNodeMouseMove: f,
  onNodeMouseLeave: d,
  onNodeContextMenu: p,
  onSelectionContextMenu: y,
  onSelectionStart: m,
  onSelectionEnd: w,
  connectionLineType: h,
  connectionLineStyle: g,
  connectionLineComponent: x,
  connectionLineContainerStyle: S,
  selectionKeyCode: E,
  selectionOnDrag: C,
  selectionMode: b,
  multiSelectionKeyCode: _,
  panActivationKeyCode: A,
  zoomActivationKeyCode: R,
  deleteKeyCode: z,
  onlyRenderVisibleElements: F,
  elementsSelectable: j,
  selectNodesOnDrag: k,
  defaultViewport: I,
  translateExtent: M,
  minZoom: V,
  maxZoom: P,
  preventScrolling: T,
  defaultMarkerColor: D,
  zoomOnScroll: O,
  zoomOnPinch: $,
  panOnScroll: H,
  panOnScrollSpeed: U,
  panOnScrollMode: K,
  zoomOnDoubleClick: Z,
  panOnDrag: q,
  onPaneClick: oe,
  onPaneMouseEnter: re,
  onPaneMouseMove: ne,
  onPaneMouseLeave: Le,
  onPaneScroll: Te,
  onPaneContextMenu: Ye,
  onEdgeContextMenu: je,
  onEdgeMouseEnter: Ee,
  onEdgeMouseMove: lt,
  onEdgeMouseLeave: se,
  onReconnect: Y,
  onReconnectStart: Xe,
  onReconnectEnd: rn,
  reconnectRadius: ei,
  noDragClassName: $r,
  noWheelClassName: jr,
  noPanClassName: on,
  elevateEdgesOnSelect: Br,
  disableKeyboardA11y: ir,
  nodeOrigin: sr,
  nodeExtent: Ur,
  rfId: Hr,
}) => {
  const ti = Wy(e, L4),
    Be = Wy(t, B4);
  return (
    oV(i),
    L.createElement(
      D4,
      {
        onPaneClick: oe,
        onPaneMouseEnter: re,
        onPaneMouseMove: ne,
        onPaneMouseLeave: Le,
        onPaneContextMenu: Ye,
        onPaneScroll: Te,
        deleteKeyCode: z,
        selectionKeyCode: E,
        selectionOnDrag: C,
        selectionMode: b,
        onSelectionStart: m,
        onSelectionEnd: w,
        multiSelectionKeyCode: _,
        panActivationKeyCode: A,
        zoomActivationKeyCode: R,
        elementsSelectable: j,
        onMove: n,
        onMoveStart: r,
        onMoveEnd: o,
        zoomOnScroll: O,
        zoomOnPinch: $,
        zoomOnDoubleClick: Z,
        panOnScroll: H,
        panOnScrollSpeed: U,
        panOnScrollMode: K,
        panOnDrag: q,
        defaultViewport: I,
        translateExtent: M,
        minZoom: V,
        maxZoom: P,
        onSelectionContextMenu: y,
        preventScrolling: T,
        noDragClassName: $r,
        noWheelClassName: jr,
        noPanClassName: on,
        disableKeyboardA11y: ir,
      },
      L.createElement(
        rV,
        null,
        L.createElement(
          tV,
          {
            edgeTypes: Be,
            onEdgeClick: a,
            onEdgeDoubleClick: u,
            onlyRenderVisibleElements: F,
            onEdgeContextMenu: je,
            onEdgeMouseEnter: Ee,
            onEdgeMouseMove: lt,
            onEdgeMouseLeave: se,
            onReconnect: Y,
            onReconnectStart: Xe,
            onReconnectEnd: rn,
            reconnectRadius: ei,
            defaultMarkerColor: D,
            noPanClassName: on,
            elevateEdgesOnSelect: !!Br,
            disableKeyboardA11y: ir,
            rfId: Hr,
          },
          L.createElement(aV, { style: g, type: h, component: x, containerStyle: S }),
        ),
        L.createElement("div", { className: "react-flow__edgelabel-renderer" }),
        L.createElement(F4, {
          nodeTypes: ti,
          onNodeClick: s,
          onNodeDoubleClick: l,
          onNodeMouseEnter: c,
          onNodeMouseMove: f,
          onNodeMouseLeave: d,
          onNodeContextMenu: p,
          selectNodesOnDrag: k,
          onlyRenderVisibleElements: F,
          noPanClassName: on,
          noDragClassName: $r,
          disableKeyboardA11y: ir,
          nodeOrigin: sr,
          nodeExtent: Ur,
          rfId: Hr,
        }),
      ),
    )
  );
};
AE.displayName = "GraphView";
var lV = v.memo(AE);
const od = [
    [Number.NEGATIVE_INFINITY, Number.NEGATIVE_INFINITY],
    [Number.POSITIVE_INFINITY, Number.POSITIVE_INFINITY],
  ],
  An = {
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
    translateExtent: od,
    nodeExtent: od,
    nodesSelectionActive: !1,
    userSelectionActive: !1,
    userSelectionRect: null,
    connectionNodeId: null,
    connectionHandleId: null,
    connectionHandleType: "source",
    connectionPosition: { x: 0, y: 0 },
    connectionStatus: null,
    connectionMode: Vr.Strict,
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
    onError: VL,
    isValidConnection: void 0,
  },
  uV = () =>
    QR(
      (e, t) => ({
        ...An,
        setNodes: (n) => {
          const { nodeInternals: r, nodeOrigin: o, elevateNodesOnSelect: i } = t();
          e({ nodeInternals: kc(n, r, o, i) });
        },
        getNodes: () => Array.from(t().nodeInternals.values()),
        setEdges: (n) => {
          const { defaultEdgeOptions: r = {} } = t();
          e({ edges: n.map((o) => ({ ...r, ...o })) });
        },
        setDefaultNodesAndEdges: (n, r) => {
          const o = typeof n < "u",
            i = typeof r < "u",
            s = o ? kc(n, new Map(), t().nodeOrigin, t().elevateNodesOnSelect) : new Map();
          e({ nodeInternals: s, edges: i ? r : [], hasDefaultNodes: o, hasDefaultEdges: i });
        },
        updateNodeDimensions: (n) => {
          const {
              onNodesChange: r,
              nodeInternals: o,
              fitViewOnInit: i,
              fitViewOnInitDone: s,
              fitViewOnInitOptions: a,
              domNode: l,
              nodeOrigin: u,
            } = t(),
            c = l == null ? void 0 : l.querySelector(".react-flow__viewport");
          if (!c) return;
          const f = window.getComputedStyle(c),
            { m22: d } = new window.DOMMatrixReadOnly(f.transform),
            p = n.reduce((m, w) => {
              const h = o.get(w.id);
              if (h != null && h.hidden)
                o.set(h.id, { ...h, [Se]: { ...h[Se], handleBounds: void 0 } });
              else if (h) {
                const g = qh(w.nodeElement);
                !!(
                  g.width &&
                  g.height &&
                  (h.width !== g.width || h.height !== g.height || w.forceUpdate)
                ) &&
                  (o.set(h.id, {
                    ...h,
                    [Se]: {
                      ...h[Se],
                      handleBounds: {
                        source: Fy(".source", w.nodeElement, d, u),
                        target: Fy(".target", w.nodeElement, d, u),
                      },
                    },
                    ...g,
                  }),
                  m.push({ id: h.id, type: "dimensions", dimensions: g }));
              }
              return m;
            }, []);
          yE(o, u);
          const y = s || (i && !s && vE(t, { initial: !0, ...a }));
          e({ nodeInternals: new Map(o), fitViewOnInitDone: y }),
            (p == null ? void 0 : p.length) > 0 && (r == null || r(p));
        },
        updateNodePositions: (n, r = !0, o = !1) => {
          const { triggerNodeChanges: i } = t(),
            s = n.map((a) => {
              const l = { id: a.id, type: "position", dragging: o };
              return r && ((l.positionAbsolute = a.positionAbsolute), (l.position = a.position)), l;
            });
          i(s);
        },
        triggerNodeChanges: (n) => {
          const {
            onNodesChange: r,
            nodeInternals: o,
            hasDefaultNodes: i,
            nodeOrigin: s,
            getNodes: a,
            elevateNodesOnSelect: l,
          } = t();
          if (n != null && n.length) {
            if (i) {
              const u = wE(n, a()),
                c = kc(u, o, s, l);
              e({ nodeInternals: c });
            }
            r == null || r(n);
          }
        },
        addSelectedNodes: (n) => {
          const { multiSelectionActive: r, edges: o, getNodes: i } = t();
          let s,
            a = null;
          r ? (s = n.map((l) => On(l, !0))) : ((s = yo(i(), n)), (a = yo(o, []))),
            wa({ changedNodes: s, changedEdges: a, get: t, set: e });
        },
        addSelectedEdges: (n) => {
          const { multiSelectionActive: r, edges: o, getNodes: i } = t();
          let s,
            a = null;
          r ? (s = n.map((l) => On(l, !0))) : ((s = yo(o, n)), (a = yo(i(), []))),
            wa({ changedNodes: a, changedEdges: s, get: t, set: e });
        },
        unselectNodesAndEdges: ({ nodes: n, edges: r } = {}) => {
          const { edges: o, getNodes: i } = t(),
            s = n || i(),
            a = r || o,
            l = s.map((c) => ((c.selected = !1), On(c.id, !1))),
            u = a.map((c) => On(c.id, !1));
          wa({ changedNodes: l, changedEdges: u, get: t, set: e });
        },
        setMinZoom: (n) => {
          const { d3Zoom: r, maxZoom: o } = t();
          r == null || r.scaleExtent([n, o]), e({ minZoom: n });
        },
        setMaxZoom: (n) => {
          const { d3Zoom: r, minZoom: o } = t();
          r == null || r.scaleExtent([o, n]), e({ maxZoom: n });
        },
        setTranslateExtent: (n) => {
          var r;
          (r = t().d3Zoom) == null || r.translateExtent(n), e({ translateExtent: n });
        },
        resetSelectedElements: () => {
          const { edges: n, getNodes: r } = t(),
            i = r()
              .filter((a) => a.selected)
              .map((a) => On(a.id, !1)),
            s = n.filter((a) => a.selected).map((a) => On(a.id, !1));
          wa({ changedNodes: i, changedEdges: s, get: t, set: e });
        },
        setNodeExtent: (n) => {
          const { nodeInternals: r } = t();
          r.forEach((o) => {
            o.positionAbsolute = Jh(o.position, n);
          }),
            e({ nodeExtent: n, nodeInternals: new Map(r) });
        },
        panBy: (n) => {
          const {
            transform: r,
            width: o,
            height: i,
            d3Zoom: s,
            d3Selection: a,
            translateExtent: l,
          } = t();
          if (!s || !a || (!n.x && !n.y)) return !1;
          const u = vn.translate(r[0] + n.x, r[1] + n.y).scale(r[2]),
            c = [
              [0, 0],
              [o, i],
            ],
            f = s == null ? void 0 : s.constrain()(u, c, l);
          return s.transform(a, f), r[0] !== f.x || r[1] !== f.y || r[2] !== f.k;
        },
        cancelConnection: () =>
          e({
            connectionNodeId: An.connectionNodeId,
            connectionHandleId: An.connectionHandleId,
            connectionHandleType: An.connectionHandleType,
            connectionStatus: An.connectionStatus,
            connectionStartHandle: An.connectionStartHandle,
            connectionEndHandle: An.connectionEndHandle,
          }),
        reset: () => e({ ...An }),
      }),
      Object.is,
    ),
  ap = ({ children: e }) => {
    const t = v.useRef(null);
    return t.current || (t.current = uV()), L.createElement(PL, { value: t.current }, e);
  };
ap.displayName = "ReactFlowProvider";
const RE = ({ children: e }) =>
  v.useContext(vu) ? L.createElement(L.Fragment, null, e) : L.createElement(ap, null, e);
RE.displayName = "ReactFlowWrapper";
const cV = { input: cE, default: nd, output: dE, group: ip },
  fV = { default: Ll, straight: np, step: tp, smoothstep: xu, simplebezier: ep },
  dV = [0, 0],
  hV = [15, 15],
  pV = { x: 0, y: 0, zoom: 1 },
  mV = { width: "100%", height: "100%", overflow: "hidden", position: "relative", zIndex: 0 },
  DE = v.forwardRef(
    (
      {
        nodes: e,
        edges: t,
        defaultNodes: n,
        defaultEdges: r,
        className: o,
        nodeTypes: i = cV,
        edgeTypes: s = fV,
        onNodeClick: a,
        onEdgeClick: l,
        onInit: u,
        onMove: c,
        onMoveStart: f,
        onMoveEnd: d,
        onConnect: p,
        onConnectStart: y,
        onConnectEnd: m,
        onClickConnectStart: w,
        onClickConnectEnd: h,
        onNodeMouseEnter: g,
        onNodeMouseMove: x,
        onNodeMouseLeave: S,
        onNodeContextMenu: E,
        onNodeDoubleClick: C,
        onNodeDragStart: b,
        onNodeDrag: _,
        onNodeDragStop: A,
        onNodesDelete: R,
        onEdgesDelete: z,
        onSelectionChange: F,
        onSelectionDragStart: j,
        onSelectionDrag: k,
        onSelectionDragStop: I,
        onSelectionContextMenu: M,
        onSelectionStart: V,
        onSelectionEnd: P,
        connectionMode: T = Vr.Strict,
        connectionLineType: D = fn.Bezier,
        connectionLineStyle: O,
        connectionLineComponent: $,
        connectionLineContainerStyle: H,
        deleteKeyCode: U = "Backspace",
        selectionKeyCode: K = "Shift",
        selectionOnDrag: Z = !1,
        selectionMode: q = Ss.Full,
        panActivationKeyCode: oe = "Space",
        multiSelectionKeyCode: re = Dl() ? "Meta" : "Control",
        zoomActivationKeyCode: ne = Dl() ? "Meta" : "Control",
        snapToGrid: Le = !1,
        snapGrid: Te = hV,
        onlyRenderVisibleElements: Ye = !1,
        selectNodesOnDrag: je = !0,
        nodesDraggable: Ee,
        nodesConnectable: lt,
        nodesFocusable: se,
        nodeOrigin: Y = dV,
        edgesFocusable: Xe,
        edgesUpdatable: rn,
        elementsSelectable: ei,
        defaultViewport: $r = pV,
        minZoom: jr = 0.5,
        maxZoom: on = 2,
        translateExtent: Br = od,
        preventScrolling: ir = !0,
        nodeExtent: sr,
        defaultMarkerColor: Ur = "#b1b1b7",
        zoomOnScroll: Hr = !0,
        zoomOnPinch: ti = !0,
        panOnScroll: Be = !1,
        panOnScrollSpeed: Pt = 0.5,
        panOnScrollMode: ar = Er.Free,
        zoomOnDoubleClick: lr = !0,
        panOnDrag: ur = !0,
        onPaneClick: sn,
        onPaneMouseEnter: Ut,
        onPaneMouseMove: ni,
        onPaneMouseLeave: Eu,
        onPaneScroll: ri,
        onPaneContextMenu: Cu,
        children: lp,
        onEdgeContextMenu: cr,
        onEdgeDoubleClick: BE,
        onEdgeMouseEnter: UE,
        onEdgeMouseMove: HE,
        onEdgeMouseLeave: WE,
        onEdgeUpdate: GE,
        onEdgeUpdateStart: KE,
        onEdgeUpdateEnd: YE,
        onReconnect: XE,
        onReconnectStart: ZE,
        onReconnectEnd: QE,
        reconnectRadius: qE = 10,
        edgeUpdaterRadius: JE = 10,
        onNodesChange: eC,
        onEdgesChange: tC,
        noDragClassName: nC = "nodrag",
        noWheelClassName: rC = "nowheel",
        noPanClassName: up = "nopan",
        fitView: oC = !1,
        fitViewOptions: iC,
        connectOnClick: sC = !0,
        attributionPosition: aC,
        proOptions: lC,
        defaultEdgeOptions: uC,
        elevateNodesOnSelect: cC = !0,
        elevateEdgesOnSelect: fC = !1,
        disableKeyboardA11y: cp = !1,
        autoPanOnConnect: dC = !0,
        autoPanOnNodeDrag: hC = !0,
        connectionRadius: pC = 20,
        isValidConnection: mC,
        onError: gC,
        style: yC,
        id: fp,
        nodeDragThreshold: vC,
        ...xC
      },
      wC,
    ) => {
      const bu = fp || "1";
      return L.createElement(
        "div",
        {
          ...xC,
          style: { ...yC, ...mV },
          ref: wC,
          className: $e(["react-flow", o]),
          "data-testid": "rf__wrapper",
          id: fp,
        },
        L.createElement(
          RE,
          null,
          L.createElement(lV, {
            onInit: u,
            onMove: c,
            onMoveStart: f,
            onMoveEnd: d,
            onNodeClick: a,
            onEdgeClick: l,
            onNodeMouseEnter: g,
            onNodeMouseMove: x,
            onNodeMouseLeave: S,
            onNodeContextMenu: E,
            onNodeDoubleClick: C,
            nodeTypes: i,
            edgeTypes: s,
            connectionLineType: D,
            connectionLineStyle: O,
            connectionLineComponent: $,
            connectionLineContainerStyle: H,
            selectionKeyCode: K,
            selectionOnDrag: Z,
            selectionMode: q,
            deleteKeyCode: U,
            multiSelectionKeyCode: re,
            panActivationKeyCode: oe,
            zoomActivationKeyCode: ne,
            onlyRenderVisibleElements: Ye,
            selectNodesOnDrag: je,
            defaultViewport: $r,
            translateExtent: Br,
            minZoom: jr,
            maxZoom: on,
            preventScrolling: ir,
            zoomOnScroll: Hr,
            zoomOnPinch: ti,
            zoomOnDoubleClick: lr,
            panOnScroll: Be,
            panOnScrollSpeed: Pt,
            panOnScrollMode: ar,
            panOnDrag: ur,
            onPaneClick: sn,
            onPaneMouseEnter: Ut,
            onPaneMouseMove: ni,
            onPaneMouseLeave: Eu,
            onPaneScroll: ri,
            onPaneContextMenu: Cu,
            onSelectionContextMenu: M,
            onSelectionStart: V,
            onSelectionEnd: P,
            onEdgeContextMenu: cr,
            onEdgeDoubleClick: BE,
            onEdgeMouseEnter: UE,
            onEdgeMouseMove: HE,
            onEdgeMouseLeave: WE,
            onReconnect: XE ?? GE,
            onReconnectStart: ZE ?? KE,
            onReconnectEnd: QE ?? YE,
            reconnectRadius: qE ?? JE,
            defaultMarkerColor: Ur,
            noDragClassName: nC,
            noWheelClassName: rC,
            noPanClassName: up,
            elevateEdgesOnSelect: fC,
            rfId: bu,
            disableKeyboardA11y: cp,
            nodeOrigin: Y,
            nodeExtent: sr,
          }),
          L.createElement(i4, {
            nodes: e,
            edges: t,
            defaultNodes: n,
            defaultEdges: r,
            onConnect: p,
            onConnectStart: y,
            onConnectEnd: m,
            onClickConnectStart: w,
            onClickConnectEnd: h,
            nodesDraggable: Ee,
            nodesConnectable: lt,
            nodesFocusable: se,
            edgesFocusable: Xe,
            edgesUpdatable: rn,
            elementsSelectable: ei,
            elevateNodesOnSelect: cC,
            minZoom: jr,
            maxZoom: on,
            nodeExtent: sr,
            onNodesChange: eC,
            onEdgesChange: tC,
            snapToGrid: Le,
            snapGrid: Te,
            connectionMode: T,
            translateExtent: Br,
            connectOnClick: sC,
            defaultEdgeOptions: uC,
            fitView: oC,
            fitViewOptions: iC,
            onNodesDelete: R,
            onEdgesDelete: z,
            onNodeDragStart: b,
            onNodeDrag: _,
            onNodeDragStop: A,
            onSelectionDrag: k,
            onSelectionDragStart: j,
            onSelectionDragStop: I,
            noPanClassName: up,
            nodeOrigin: Y,
            rfId: bu,
            autoPanOnConnect: dC,
            autoPanOnNodeDrag: hC,
            onError: gC,
            connectionRadius: pC,
            isValidConnection: mC,
            nodeDragThreshold: vC,
          }),
          L.createElement(r4, { onSelectionChange: F }),
          lp,
          L.createElement(AL, { proOptions: lC, position: aC }),
          L.createElement(c4, { rfId: bu, disableKeyboardA11y: cp }),
        ),
      );
    },
  );
DE.displayName = "ReactFlow";
function gV() {
  const e = _e();
  return v.useCallback((t) => {
    const { domNode: n, updateNodeDimensions: r } = e.getState(),
      i = (Array.isArray(t) ? t : [t]).reduce((s, a) => {
        const l = n == null ? void 0 : n.querySelector(`.react-flow__node[data-id="${a}"]`);
        return l && s.push({ id: a, nodeElement: l, forceUpdate: !0 }), s;
      }, []);
    requestAnimationFrame(() => r(i));
  }, []);
}
const IE = ({
  id: e,
  x: t,
  y: n,
  width: r,
  height: o,
  style: i,
  color: s,
  strokeColor: a,
  strokeWidth: l,
  className: u,
  borderRadius: c,
  shapeRendering: f,
  onClick: d,
  selected: p,
}) => {
  const { background: y, backgroundColor: m } = i || {},
    w = s || y || m;
  return L.createElement("rect", {
    className: $e(["react-flow__minimap-node", { selected: p }, u]),
    x: t,
    y: n,
    rx: c,
    ry: c,
    width: r,
    height: o,
    fill: w,
    stroke: a,
    strokeWidth: l,
    shapeRendering: f,
    onClick: d ? (h) => d(h, e) : void 0,
  });
};
IE.displayName = "MiniMapNode";
var yV = v.memo(IE);
const vV = (e) => e.nodeOrigin,
  xV = (e) => e.getNodes().filter((t) => !t.hidden && t.width && t.height),
  Pc = (e) => (e instanceof Function ? e : () => e);
function wV({
  nodeStrokeColor: e = "transparent",
  nodeColor: t = "#e2e2e2",
  nodeClassName: n = "",
  nodeBorderRadius: r = 5,
  nodeStrokeWidth: o = 2,
  nodeComponent: i = yV,
  onClick: s,
}) {
  const a = ce(xV, Ie),
    l = ce(vV),
    u = Pc(t),
    c = Pc(e),
    f = Pc(n),
    d = typeof window > "u" || window.chrome ? "crispEdges" : "geometricPrecision";
  return L.createElement(
    L.Fragment,
    null,
    a.map((p) => {
      const { x: y, y: m } = Nr(p, l).positionAbsolute;
      return L.createElement(i, {
        key: p.id,
        x: y,
        y: m,
        width: p.width,
        height: p.height,
        style: p.style,
        selected: p.selected,
        className: f(p),
        color: u(p),
        borderRadius: r,
        strokeColor: c(p),
        strokeWidth: o,
        shapeRendering: d,
        onClick: s,
        id: p.id,
      });
    }),
  );
}
var SV = v.memo(wV);
const EV = 200,
  CV = 150,
  bV = (e) => {
    const t = e.getNodes(),
      n = {
        x: -e.transform[0] / e.transform[2],
        y: -e.transform[1] / e.transform[2],
        width: e.width / e.transform[2],
        height: e.height / e.transform[2],
      };
    return { viewBB: n, boundingRect: t.length > 0 ? IL(wu(t, e.nodeOrigin), n) : n, rfId: e.rfId };
  },
  kV = "react-flow__minimap-desc";
function LE({
  style: e,
  className: t,
  nodeStrokeColor: n = "transparent",
  nodeColor: r = "#e2e2e2",
  nodeClassName: o = "",
  nodeBorderRadius: i = 5,
  nodeStrokeWidth: s = 2,
  nodeComponent: a,
  maskColor: l = "rgb(240, 240, 240, 0.6)",
  maskStrokeColor: u = "none",
  maskStrokeWidth: c = 1,
  position: f = "bottom-right",
  onClick: d,
  onNodeClick: p,
  pannable: y = !1,
  zoomable: m = !1,
  ariaLabel: w = "React Flow mini map",
  inversePan: h = !1,
  zoomStep: g = 10,
  offsetScale: x = 5,
}) {
  const S = _e(),
    E = v.useRef(null),
    { boundingRect: C, viewBB: b, rfId: _ } = ce(bV, Ie),
    A = (e == null ? void 0 : e.width) ?? EV,
    R = (e == null ? void 0 : e.height) ?? CV,
    z = C.width / A,
    F = C.height / R,
    j = Math.max(z, F),
    k = j * A,
    I = j * R,
    M = x * j,
    V = C.x - (k - C.width) / 2 - M,
    P = C.y - (I - C.height) / 2 - M,
    T = k + M * 2,
    D = I + M * 2,
    O = `${kV}-${_}`,
    $ = v.useRef(0);
  ($.current = j),
    v.useEffect(() => {
      if (E.current) {
        const K = Et(E.current),
          Z = (re) => {
            const { transform: ne, d3Selection: Le, d3Zoom: Te } = S.getState();
            if (re.sourceEvent.type !== "wheel" || !Le || !Te) return;
            const Ye =
                -re.sourceEvent.deltaY *
                (re.sourceEvent.deltaMode === 1 ? 0.05 : re.sourceEvent.deltaMode ? 1 : 0.002) *
                g,
              je = ne[2] * Math.pow(2, Ye);
            Te.scaleTo(Le, je);
          },
          q = (re) => {
            const {
              transform: ne,
              d3Selection: Le,
              d3Zoom: Te,
              translateExtent: Ye,
              width: je,
              height: Ee,
            } = S.getState();
            if (re.sourceEvent.type !== "mousemove" || !Le || !Te) return;
            const lt = $.current * Math.max(1, ne[2]) * (h ? -1 : 1),
              se = {
                x: ne[0] - re.sourceEvent.movementX * lt,
                y: ne[1] - re.sourceEvent.movementY * lt,
              },
              Y = [
                [0, 0],
                [je, Ee],
              ],
              Xe = vn.translate(se.x, se.y).scale(ne[2]),
              rn = Te.constrain()(Xe, Y, Ye);
            Te.transform(Le, rn);
          },
          oe = BS()
            .on("zoom", y ? q : null)
            .on("zoom.wheel", m ? Z : null);
        return (
          K.call(oe),
          () => {
            K.on("zoom", null);
          }
        );
      }
    }, [y, m, h, g]);
  const H = d
      ? (K) => {
          const Z = It(K);
          d(K, { x: Z[0], y: Z[1] });
        }
      : void 0,
    U = p
      ? (K, Z) => {
          const q = S.getState().nodeInternals.get(Z);
          p(K, q);
        }
      : void 0;
  return L.createElement(
    Qh,
    {
      position: f,
      style: e,
      className: $e(["react-flow__minimap", t]),
      "data-testid": "rf__minimap",
    },
    L.createElement(
      "svg",
      {
        width: A,
        height: R,
        viewBox: `${V} ${P} ${T} ${D}`,
        role: "img",
        "aria-labelledby": O,
        ref: E,
        onClick: H,
      },
      w && L.createElement("title", { id: O }, w),
      L.createElement(SV, {
        onClick: U,
        nodeColor: r,
        nodeStrokeColor: n,
        nodeBorderRadius: i,
        nodeClassName: o,
        nodeStrokeWidth: s,
        nodeComponent: a,
      }),
      L.createElement("path", {
        className: "react-flow__minimap-mask",
        d: `M${V - M},${P - M}h${T + M * 2}v${D + M * 2}h${-T - M * 2}z
        M${b.x},${b.y}h${b.width}v${b.height}h${-b.width}z`,
        fill: l,
        fillRule: "evenodd",
        stroke: u,
        strokeWidth: c,
        pointerEvents: "none",
      }),
    ),
  );
}
LE.displayName = "MiniMap";
var _V = v.memo(LE);
function TV() {
  return L.createElement(
    "svg",
    { xmlns: "http://www.w3.org/2000/svg", viewBox: "0 0 32 32" },
    L.createElement("path", {
      d: "M32 18.133H18.133V32h-4.266V18.133H0v-4.266h13.867V0h4.266v13.867H32z",
    }),
  );
}
function NV() {
  return L.createElement(
    "svg",
    { xmlns: "http://www.w3.org/2000/svg", viewBox: "0 0 32 5" },
    L.createElement("path", { d: "M0 0h32v4.2H0z" }),
  );
}
function PV() {
  return L.createElement(
    "svg",
    { xmlns: "http://www.w3.org/2000/svg", viewBox: "0 0 32 30" },
    L.createElement("path", {
      d: "M3.692 4.63c0-.53.4-.938.939-.938h5.215V0H4.708C2.13 0 0 2.054 0 4.63v5.216h3.692V4.631zM27.354 0h-5.2v3.692h5.17c.53 0 .984.4.984.939v5.215H32V4.631A4.624 4.624 0 0027.354 0zm.954 24.83c0 .532-.4.94-.939.94h-5.215v3.768h5.215c2.577 0 4.631-2.13 4.631-4.707v-5.139h-3.692v5.139zm-23.677.94c-.531 0-.939-.4-.939-.94v-5.138H0v5.139c0 2.577 2.13 4.707 4.708 4.707h5.138V25.77H4.631z",
    }),
  );
}
function MV() {
  return L.createElement(
    "svg",
    { xmlns: "http://www.w3.org/2000/svg", viewBox: "0 0 25 32" },
    L.createElement("path", {
      d: "M21.333 10.667H19.81V7.619C19.81 3.429 16.38 0 12.19 0 8 0 4.571 3.429 4.571 7.619v3.048H3.048A3.056 3.056 0 000 13.714v15.238A3.056 3.056 0 003.048 32h18.285a3.056 3.056 0 003.048-3.048V13.714a3.056 3.056 0 00-3.048-3.047zM12.19 24.533a3.056 3.056 0 01-3.047-3.047 3.056 3.056 0 013.047-3.048 3.056 3.056 0 013.048 3.048 3.056 3.056 0 01-3.048 3.047zm4.724-13.866H7.467V7.619c0-2.59 2.133-4.724 4.723-4.724 2.591 0 4.724 2.133 4.724 4.724v3.048z",
    }),
  );
}
function AV() {
  return L.createElement(
    "svg",
    { xmlns: "http://www.w3.org/2000/svg", viewBox: "0 0 25 32" },
    L.createElement("path", {
      d: "M21.333 10.667H19.81V7.619C19.81 3.429 16.38 0 12.19 0c-4.114 1.828-1.37 2.133.305 2.438 1.676.305 4.42 2.59 4.42 5.181v3.048H3.047A3.056 3.056 0 000 13.714v15.238A3.056 3.056 0 003.048 32h18.285a3.056 3.056 0 003.048-3.048V13.714a3.056 3.056 0 00-3.048-3.047zM12.19 24.533a3.056 3.056 0 01-3.047-3.047 3.056 3.056 0 013.047-3.048 3.056 3.056 0 013.048 3.048 3.056 3.056 0 01-3.048 3.047z",
    }),
  );
}
const Pi = ({ children: e, className: t, ...n }) =>
  L.createElement(
    "button",
    { type: "button", className: $e(["react-flow__controls-button", t]), ...n },
    e,
  );
Pi.displayName = "ControlButton";
const RV = (e) => ({
    isInteractive: e.nodesDraggable || e.nodesConnectable || e.elementsSelectable,
    minZoomReached: e.transform[2] <= e.minZoom,
    maxZoomReached: e.transform[2] >= e.maxZoom,
  }),
  VE = ({
    style: e,
    showZoom: t = !0,
    showFitView: n = !0,
    showInteractive: r = !0,
    fitViewOptions: o,
    onZoomIn: i,
    onZoomOut: s,
    onFitView: a,
    onInteractiveChange: l,
    className: u,
    children: c,
    position: f = "bottom-left",
  }) => {
    const d = _e(),
      [p, y] = v.useState(!1),
      { isInteractive: m, minZoomReached: w, maxZoomReached: h } = ce(RV, Ie),
      { zoomIn: g, zoomOut: x, fitView: S } = Su();
    if (
      (v.useEffect(() => {
        y(!0);
      }, []),
      !p)
    )
      return null;
    const E = () => {
        g(), i == null || i();
      },
      C = () => {
        x(), s == null || s();
      },
      b = () => {
        S(o), a == null || a();
      },
      _ = () => {
        d.setState({ nodesDraggable: !m, nodesConnectable: !m, elementsSelectable: !m }),
          l == null || l(!m);
      };
    return L.createElement(
      Qh,
      {
        className: $e(["react-flow__controls", u]),
        position: f,
        style: e,
        "data-testid": "rf__controls",
      },
      t &&
        L.createElement(
          L.Fragment,
          null,
          L.createElement(
            Pi,
            {
              onClick: E,
              className: "react-flow__controls-zoomin",
              title: "zoom in",
              "aria-label": "zoom in",
              disabled: h,
            },
            L.createElement(TV, null),
          ),
          L.createElement(
            Pi,
            {
              onClick: C,
              className: "react-flow__controls-zoomout",
              title: "zoom out",
              "aria-label": "zoom out",
              disabled: w,
            },
            L.createElement(NV, null),
          ),
        ),
      n &&
        L.createElement(
          Pi,
          {
            className: "react-flow__controls-fitview",
            onClick: b,
            title: "fit view",
            "aria-label": "fit view",
          },
          L.createElement(PV, null),
        ),
      r &&
        L.createElement(
          Pi,
          {
            className: "react-flow__controls-interactive",
            onClick: _,
            title: "toggle interactivity",
            "aria-label": "toggle interactivity",
          },
          m ? L.createElement(AV, null) : L.createElement(MV, null),
        ),
      c,
    );
  };
VE.displayName = "Controls";
var DV = v.memo(VE),
  zt;
(function (e) {
  (e.Lines = "lines"), (e.Dots = "dots"), (e.Cross = "cross");
})(zt || (zt = {}));
function IV({ color: e, dimensions: t, lineWidth: n }) {
  return L.createElement("path", {
    stroke: e,
    strokeWidth: n,
    d: `M${t[0] / 2} 0 V${t[1]} M0 ${t[1] / 2} H${t[0]}`,
  });
}
function LV({ color: e, radius: t }) {
  return L.createElement("circle", { cx: t, cy: t, r: t, fill: e });
}
const VV = { [zt.Dots]: "#91919a", [zt.Lines]: "#eee", [zt.Cross]: "#e2e2e2" },
  OV = { [zt.Dots]: 1, [zt.Lines]: 1, [zt.Cross]: 6 },
  FV = (e) => ({ transform: e.transform, patternId: `pattern-${e.rfId}` });
function OE({
  id: e,
  variant: t = zt.Dots,
  gap: n = 20,
  size: r,
  lineWidth: o = 1,
  offset: i = 2,
  color: s,
  style: a,
  className: l,
}) {
  const u = v.useRef(null),
    { transform: c, patternId: f } = ce(FV, Ie),
    d = s || VV[t],
    p = r || OV[t],
    y = t === zt.Dots,
    m = t === zt.Cross,
    w = Array.isArray(n) ? n : [n, n],
    h = [w[0] * c[2] || 1, w[1] * c[2] || 1],
    g = p * c[2],
    x = m ? [g, g] : h,
    S = y ? [g / i, g / i] : [x[0] / i, x[1] / i];
  return L.createElement(
    "svg",
    {
      className: $e(["react-flow__background", l]),
      style: { ...a, position: "absolute", width: "100%", height: "100%", top: 0, left: 0 },
      ref: u,
      "data-testid": "rf__background",
    },
    L.createElement(
      "pattern",
      {
        id: f + e,
        x: c[0] % h[0],
        y: c[1] % h[1],
        width: h[0],
        height: h[1],
        patternUnits: "userSpaceOnUse",
        patternTransform: `translate(-${S[0]},-${S[1]})`,
      },
      y
        ? L.createElement(LV, { color: d, radius: g / i })
        : L.createElement(IV, { dimensions: x, color: d, lineWidth: o }),
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
OE.displayName = "Background";
var zV = v.memo(OE);
const Mo = 40,
  bs = 44,
  Vl = 16,
  Ol = 16,
  Gy = 40,
  Ea = 48;
function FE(e) {
  const t = e ? Object.keys(e) : [];
  return t.length ? bs + 12 + 2 + t.length * 12 : bs;
}
function $V(e) {
  return e + Mo / 2;
}
const Gt = 260,
  vo = 140,
  Cr = 140,
  id = 36,
  zE = 180,
  sd = 100,
  Xt = Mo + 64,
  Fl = Mo + 56,
  Ky = 8,
  Ct = (e) => Math.round(e / Ky) * Ky,
  Ca = (e) => (e ? (Array.isArray(e) ? e : [e]) : []),
  jV = (e) =>
    Ca(e == null ? void 0 : e.entry).length +
      Ca(e == null ? void 0 : e.exit).length +
      Ca(e == null ? void 0 : e.invoke).length +
      Ca(e == null ? void 0 : e.activities).length >
    0;
function $E(e, t = "") {
  const n = [];
  for (const r of Object.keys(e.states ?? {})) {
    const o = e.states[r] ?? {},
      i = t ? `${t}.${r}` : r;
    n.push({ id: i, key: r, def: o }), o.states && n.push(...$E(o, i));
  }
  return n;
}
function zl(e) {
  return e
    ? typeof e == "string"
      ? [e]
      : Array.isArray(e)
        ? e.flatMap(zl)
        : typeof e == "object" && e.target
          ? zl(e.target)
          : []
    : [];
}
function jE(e, t = "") {
  const n = [],
    r = (o) => (t ? `${t}.${o}` : o);
  if (e.on)
    for (const o of Object.keys(e.on))
      for (const i of zl(e.on[o]))
        n.push({ source: t || "ROOT", target: t ? `${t}.${i}` : i, label: o });
  for (const o of Object.keys(e.states ?? {})) {
    const i = e.states[o] ?? {},
      s = r(o);
    if (i.on)
      for (const a of Object.keys(i.on))
        for (const l of zl(i.on[a])) {
          const u = l.startsWith("#") ? l.slice(1) : l.includes(".") ? l : r(l);
          n.push({ source: s, target: u, label: a });
        }
    i.states && n.push(...jE(i, s));
  }
  return n;
}
function BV(e, t, n) {
  var c;
  const r = new Set(e),
    o = new Map(e.map((f) => [f, 0])),
    i = new Map();
  for (const f of e) i.set(f, new Set());
  for (const f of t)
    !r.has(f.source) ||
      !r.has(f.target) ||
      i.get(f.source).has(f.target) ||
      (i.get(f.source).add(f.target), o.set(f.target, (o.get(f.target) ?? 0) + 1));
  const s = [];
  n && r.has(n) && s.push(n);
  for (const f of e) (o.get(f) ?? 0) === 0 && f !== n && s.push(f);
  s.length === 0 && s.push(...[...e].sort());
  const a = [],
    l = new Set();
  for (; l.size < e.length; ) {
    const f = s.filter((y) => !l.has(y));
    if (f.length === 0) {
      const y = e.filter((m) => !l.has(m));
      if (!y.length) break;
      f.push(...y.slice(0, Math.max(1, Math.ceil(y.length / 2))));
    }
    a.push(f), f.forEach((y) => l.add(y));
    const d = [];
    for (const y of f) for (const m of i.get(y) ?? []) l.has(m) || d.push(m);
    s.length = 0;
    const p = new Set();
    for (const y of d) p.has(y) || (p.add(y), s.push(y));
  }
  const u = new Map();
  a.forEach((f, d) => f.forEach((p) => u.set(p, d)));
  for (let f = 1; f < a.length; f++) {
    const d = new Set(a[f - 1]),
      p = {};
    for (const m of t)
      u.get(m.target) === f &&
        d.has(m.source) &&
        (p[(c = m.target)] || (p[c] = [])).push(a[f - 1].indexOf(m.source));
    const y = (m) => (m.length ? m.reduce((w, h) => w + h, 0) / m.length : 0);
    a[f].sort((m, w) => y(p[m] ?? []) - y(p[w] ?? []));
  }
  return a;
}
function UV(e, t) {
  const n = {};
  let r = Xt;
  for (const o of e) {
    const i = o.length * vo + Math.max(0, o.length - 1) * sd;
    let s = t + Fl + Math.max(0, (0 - i) / 2);
    for (const a of o) (n[a] = { x: Ct(r), y: Ct(s) }), (s += vo + sd);
    r += Gt + zE;
  }
  return n;
}
function ad(e) {
  return e.replace(/[^a-zA-Z0-9_]+/g, "_");
}
function HV(e, t, n, r, o) {
  const i = {};
  if (!e.length) return i;
  const s = new Map();
  for (const y of t) (s.get(y.label) || s.set(y.label, []).get(y.label)).push(y);
  const a = e.map((y) => {
      const m = s.get(y) ?? [],
        w = m.map((S) => {
          var E;
          return (((E = n[S.source]) == null ? void 0 : E.x) ?? Xt) + Gt / 2;
        }),
        h = m.map((S) => {
          var E;
          return (((E = n[S.target]) == null ? void 0 : E.x) ?? Xt) + Gt / 2;
        }),
        g = (S) => (S.length ? S.reduce((E, C) => E + C, 0) / S.length : Xt + Gt / 2),
        x = (g(w) + g(h)) / 2;
      return { id: `__event__${ad(y)}`, x: Ct(x - Cr / 2) };
    }),
    l = Xt,
    u = Math.max(l, o - Xt - Cr),
    c = 28,
    f = id + 10,
    d = r + Math.max(14, Math.floor(Fl / 2));
  a.sort((y, m) => y.x - m.x);
  const p = [];
  for (const y of a) {
    const m = Math.max(l, Math.min(u, y.x));
    let w = !1;
    for (const h of p) {
      const g = Math.max(l, h.right + c);
      if (g <= u) {
        (i[y.id] = { x: Ct(g), y: Ct(h.y) }), (h.right = g + Cr), (w = !0);
        break;
      }
    }
    if (!w) {
      const h = d + p.length * f,
        g = m;
      p.push({ y: h, right: g + Cr }), (i[y.id] = { x: Ct(g), y: Ct(h) });
    }
  }
  return i;
}
function Yy(e, t, n, r, o, i) {
  const s = Ct(e.x + n / 2),
    a = Ct(t.x + o / 2),
    l = Ct(e.y + r / 2),
    u = Ct(t.y + i / 2),
    c = Math.abs(a - s),
    f = Math.abs(u - l);
  return a > s && c >= f
    ? { sh: "r", th: "L" }
    : a < s && c >= f
      ? { sh: "l", th: "R" }
      : u < l
        ? { sh: "t", th: "B" }
        : { sh: "b", th: "T" };
}
async function WV(e, t) {
  var S, E;
  const n = e.id ?? "StateMachine",
    r = `${n}__root`,
    o = $E(e),
    i = o.map((C) => C.id),
    s = jE(e).filter((C) => i.includes(C.source) && i.includes(C.target)),
    a = BV(
      i,
      s.map(({ source: C, target: b }) => ({ source: C, target: b })),
      e.initial,
    ),
    l = Math.max(FE(t) + Vl, bs + Vl),
    u = UV(a, l),
    c = Math.max(980, Xt * 2 + Math.max(Gt, a.length * Gt + (a.length - 1) * zE)),
    f = Math.max(...a.map((C) => C.length * vo + Math.max(0, C.length - 1) * sd), vo),
    d = Math.max(560, l + Fl * 2 + f),
    p = [
      {
        id: r,
        type: "rootNode",
        data: { label: n, context: t ?? {} },
        position: { x: Ol, y: Ol },
        style: { width: c, height: d },
        draggable: !0,
        selectable: !1,
      },
    ];
  for (const C of o) {
    const b = u[C.id] ?? { x: Xt, y: l + Fl };
    p.push({
      id: C.id,
      type: (S = C.def) != null && S.states ? "compoundStateNode" : "stateNode",
      data: { label: C.key, definition: C.def, machineId: n, headerOnly: !jV(C.def) },
      position: b,
      style: { width: Gt },
      parentId: r,
      extent: "parent",
      draggable: !0,
    });
  }
  const y = Array.from(new Set(s.map((C) => C.label))).sort(),
    m = HV(y, s, u, l, c);
  for (const C of y) {
    const b = `__event__${ad(C)}`,
      _ = m[b] ?? { x: Xt, y: l + 12 };
    p.push({
      id: b,
      type: "eventNode",
      data: { label: C },
      position: _,
      style: { width: Cr },
      parentId: r,
      extent: "parent",
      draggable: !0,
    });
  }
  const w = [],
    h = (C) => `__event__${ad(C)}`,
    g = new Set(),
    x = new Set();
  for (const C of s) {
    const b = h(C.label),
      _ = `${C.source}->${b}`;
    if (!g.has(_)) {
      g.add(_);
      const R = Yy(u[C.source], m[b] ?? u[C.source], Gt, vo, Cr, id);
      w.push({
        id: `e_se_${C.source}_${b}`,
        source: C.source,
        target: b,
        sourceHandle: R.sh,
        targetHandle: R.th,
        type: "transitionEdge",
        data: { label: "" },
      });
    }
    const A = `${b}->${C.target}`;
    if (!x.has(A)) {
      x.add(A);
      const R = Yy(m[b] ?? u[C.target], u[C.target], Cr, id, Gt, vo);
      w.push({
        id: `e_et_${b}_${C.target}`,
        source: b,
        target: C.target,
        sourceHandle: R.sh,
        targetHandle: R.th,
        type: "transitionEdge",
        data: { label: "" },
      });
    }
  }
  if (e.initial && i.includes(e.initial)) {
    const C = "__initial__root",
      b = (((E = u[e.initial]) == null ? void 0 : E.x) ?? Xt) + Gt / 2;
    p.push({
      id: C,
      type: "initialNode",
      data: {},
      position: { x: Ct(b), y: Math.max(12, l - 56) },
      parentId: r,
      extent: "parent",
      draggable: !1,
      selectable: !1,
    }),
      w.push({
        id: `e_${C}_${e.initial}`,
        source: C,
        target: e.initial,
        sourceHandle: "b",
        targetHandle: "T",
        type: "transitionEdge",
        data: { isInitial: !0, label: "" },
      });
  }
  return { nodes: p, edges: w };
}
const ba = () => new Promise((e) => requestAnimationFrame(() => e())),
  GV = ({ machine: e, activeStateIds: t }) => {
    const [n, r] = v.useState([]),
      [o, i] = v.useState([]),
      { fitView: s, getNodes: a } = Su(),
      l = gV(),
      u = v.useMemo(() => Math.max(FE(e.context) + Vl, bs + Vl), [e.context]),
      c = v.useMemo(() => $V(u), [u]),
      f = v.useCallback(
        (E, C) => {
          const b = new Set(t),
            _ = new Set();
          for (const A of C) b.has(A.source) && _.add(A.target);
          return E.map((A) => ({
            ...A,
            data: { ...A.data, uiStatus: b.has(A.id) ? "active" : _.has(A.id) ? "next" : void 0 },
          }));
        },
        [t],
      ),
      d = v.useCallback((E) => {
        const C = E.find((b) => b.type === "rootNode");
        return C
          ? E.map((b) =>
              b.id === C.id ? b : { ...b, parentId: C.id, extent: "parent", draggable: !0 },
            )
          : E;
      }, []),
      p = v.useCallback(
        (E, C) => {
          const b = E.find((M) => M.type === "rootNode");
          if (!b) return null;
          const _ = E.filter((M) => M.parentId === b.id);
          if (!_.length) return null;
          let A = 1 / 0,
            R = 1 / 0,
            z = -1 / 0,
            F = -1 / 0;
          for (const M of _) {
            const V = M.width ?? 0,
              P = M.height ?? 0;
            (A = Math.min(A, M.position.x)),
              (R = Math.min(R, M.position.y)),
              (z = Math.max(z, M.position.x + V)),
              (F = Math.max(F, M.position.y + P));
          }
          const j = new Map(E.map((M) => [M.id, M]));
          for (const M of C) {
            const V = j.get(M.source),
              P = j.get(M.target);
            if (!V || !P || V.parentId !== b.id || P.parentId !== b.id) continue;
            const T = V.position.x + (V.width ?? 0) / 2,
              D = V.position.y + (V.height ?? 0) / 2,
              O = P.position.x + (P.width ?? 0) / 2,
              $ = P.position.y + (P.height ?? 0) / 2;
            (A = Math.min(A, Math.min(T, O) - Ea)),
              (z = Math.max(z, Math.max(T, O) + Ea)),
              (R = Math.min(R, Math.min(D, $) - Ea)),
              (F = Math.max(F, Math.max(D, $) + Ea));
          }
          R = Math.max(R, c);
          const k = Math.max(z - A + Mo + 72, 320),
            I = Math.max(F - R + Mo + 80 + u - bs, 200 + u);
          return { minX: A, minY: R, width: k, height: I };
        },
        [u, c],
      ),
      y = v.useCallback(
        (E, C) => {
          var M, V;
          const b = E.find((P) => P.type === "rootNode"),
            _ = p(E, C);
          if (!b || !_) return E;
          let A = E;
          const R = c - _.minY;
          R > 0 &&
            (A = A.map((P) =>
              P.id === b.id
                ? { ...P, position: { x: P.position.x, y: P.position.y - R } }
                : P.parentId === b.id
                  ? { ...P, position: { x: P.position.x, y: P.position.y + R } }
                  : P,
            ));
          const z = p(A, C) ?? _,
            F = ((M = b.style) == null ? void 0 : M.width) ?? b.width ?? z.width,
            j = ((V = b.style) == null ? void 0 : V.height) ?? b.height ?? z.height,
            k = Math.max(F, z.width + Gy),
            I = Math.max(j, z.height + Gy);
          return (
            (k !== F || I !== j) &&
              (A = A.map((P) =>
                P.id === b.id ? { ...P, style: { ...P.style, width: k, height: I } } : P,
              )),
            l(b.id),
            A
          );
        },
        [p, c, l],
      ),
      m = v.useCallback(
        (E, C) => {
          const b = E.find((F) => F.type === "rootNode"),
            _ = p(E, C);
          if (!b || !_) return E;
          const A = _.minX - Mo / 2,
            R = _.minY - c,
            z = E.map((F) =>
              F.id === b.id
                ? {
                    ...F,
                    position: { x: b.position.x + A, y: b.position.y + R },
                    style: { ...F.style, width: _.width, height: _.height },
                  }
                : F.parentId === b.id
                  ? { ...F, position: { x: F.position.x - A, y: F.position.y - R } }
                  : F,
            );
          return l(b.id), z;
        },
        [p, c, l],
      ),
      w = v.useCallback(
        async (E) => {
          await ba(),
            await ba(),
            a()
              .filter((b) => b.type !== "rootNode")
              .map((b) => b.id)
              .forEach((b) => l(b)),
            await ba(),
            r((b) => m(b, E)),
            await ba(),
            s({ duration: 500, padding: 0.18, includeHiddenNodes: !0 });
        },
        [a, l, m, s],
      ),
      h = v.useCallback(async () => {
        const { nodes: E, edges: C } = await WV(e.definition, e.context),
          b = d(E),
          _ = f(b, C);
        i(C), r(_), w(C).catch(console.error);
      }, [e.definition, e.context, d, f, w]);
    v.useEffect(() => {
      h().catch(console.error);
    }, [h]),
      v.useEffect(() => {
        r((E) => f(E, o));
      }, [t, o, f]);
    const g = v.useCallback(
        (E) => {
          r((C) => {
            const b = wE(E, C),
              _ = y(b, o);
            return E.some((R) => R.type === "position" && R.dragging) ? _ : f(_, o);
          });
        },
        [o, f, y],
      ),
      x = v.useCallback((E) => i((C) => b4(E, C)), []),
      S = v.useCallback(() => {
        r((E) => {
          const C = m(E, o),
            b = C.filter((_) => _.type !== "rootNode").map((_) => _.id);
          return setTimeout(() => b.forEach((_) => l(_)), 0), C;
        }),
          w(o).catch(console.error);
      }, [m, o, l, w]);
    return {
      nodes: n,
      edges: o,
      onNodesChange: g,
      onEdgesChange: x,
      onNodeDragStop: S,
      relayout: h,
      tightenAndFitWhenReady: w,
    };
  },
  KV = ({ x: e, y: t, onClose: n, onAutoLayout: r, onFitView: o }) =>
    N.jsxs("div", {
      style: { left: e, top: t },
      className: "absolute z-50 rounded-md border bg-popover text-popover-foreground shadow-md",
      onMouseLeave: n,
      children: [
        N.jsx("button", {
          className: "w-full text-left px-3 py-2 hover:bg-muted",
          onClick: () => {
            n(), r();
          },
          children: "Auto layout",
        }),
        N.jsx("button", {
          className: "w-full text-left px-3 py-2 hover:bg-muted",
          onClick: () => {
            n(), o();
          },
          children: "Fit view",
        }),
      ],
    }),
  Xy = (e) => (e ? (Array.isArray(e) ? e : [e]) : []),
  Zy = ({ title: e, items: t, icon: n, colorClass: r }) =>
    t != null && t.length
      ? N.jsxs("div", {
          className: "mb-2 last:mb-0",
          children: [
            N.jsx("h4", {
              className:
                "text-[10px] font-semibold text-muted-foreground mb-1 tracking-wide uppercase",
              children: e,
            }),
            t.map((o, i) =>
              N.jsxs(
                "div",
                {
                  className: "flex items-center gap-2 text-[12px] leading-5",
                  children: [
                    N.jsx(n, { className: le("w-3.5 h-3.5 shrink-0", r) }),
                    N.jsx("span", { className: "truncate", children: o.type ?? o.src ?? o }),
                  ],
                },
                i,
              ),
            ),
          ],
        })
      : null,
  YV = ({ data: e }) => {
    var s, a, l;
    const t = Xy((s = e.definition) == null ? void 0 : s.entry),
      n = Xy((a = e.definition) == null ? void 0 : a.invoke),
      r = t.length > 0 || n.length > 0,
      o = ((l = e.definition) == null ? void 0 : l.type) === "final",
      i = e.uiStatus;
    return N.jsxs(Ms, {
      className: le(
        "w-[240px] rounded-lg border-2 shadow-md",
        i === "active" && "border-blue-500 bg-blue-500/10",
        i === "next" && "border-blue-400/50",
        o && "border-dashed",
      ),
      children: [
        N.jsx(er, { type: "target", position: G.Top, className: "!opacity-0" }),
        N.jsx(As, {
          className: le(
            "p-2.5 rounded-t-md",
            i === "active" ? "bg-blue-500 text-white" : "bg-muted",
          ),
          children: N.jsx(Rs, {
            className: "text-[13px] font-semibold tracking-wide",
            children: e.label,
          }),
        }),
        r &&
          N.jsxs(Ds, {
            className: "p-3",
            children: [
              N.jsx(Zy, {
                title: "Entry actions",
                items: t,
                icon: V_,
                colorClass: "text-yellow-500",
              }),
              N.jsx(Zy, { title: "Invoke", items: n, icon: P_, colorClass: "text-blue-500" }),
            ],
          }),
        !o && N.jsx(er, { type: "source", position: G.Bottom, className: "!opacity-0" }),
      ],
    });
  },
  XV = ({ data: e }) =>
    N.jsxs("div", {
      className:
        "bg-card text-card-foreground rounded-md text-sm font-medium border-2 px-4 py-2 shadow-sm",
      children: [
        e.label,
        N.jsx(er, { type: "target", position: G.Top, className: "!opacity-0" }),
        N.jsx(er, { type: "source", position: G.Bottom, className: "!opacity-0" }),
      ],
    }),
  ZV = (e) =>
    N.jsx("div", {
      className: le(
        "rounded-lg border-2 bg-secondary/20",
        e.selected ? "border-primary/60" : "border-border",
      ),
      children: N.jsx("div", {
        className:
          "p-2 text-[12px] font-bold text-muted-foreground cursor-move border-b bg-secondary/30 rounded-t-lg",
        children: e.data.label,
      }),
    }),
  QV = ({ data: e }) => {
    const t = Object.entries(e.context ?? {}).map(([n, r]) => ({ key: n, type: typeof r }));
    return N.jsxs(Ms, {
      className: le(
        "w-full h-full flex flex-col rounded-xl bg-transparent pointer-events-none border-[6px] border-neutral-300/60 dark:border-neutral-700/80",
      ),
      children: [
        N.jsx(As, {
          className:
            "root-drag-handle p-3 border-b bg-muted/80 backdrop-blur-sm rounded-t-lg cursor-move pointer-events-auto",
          children: N.jsx(Rs, {
            className: "text-[15px] font-semibold tracking-wide text-foreground",
            children: e.label,
          }),
        }),
        t.length > 0 &&
          N.jsxs(Ds, {
            className: "px-3 py-1 border-b bg-muted/80 backdrop-blur-sm pointer-events-none",
            children: [
              N.jsx("h4", {
                className:
                  "text-[10px] font-semibold text-muted-foreground mb-0.5 tracking-wide uppercase",
                children: "Context",
              }),
              t.map(({ key: n, type: r }) =>
                N.jsxs(
                  "div",
                  {
                    className: "text-[12px] leading-5",
                    children: [
                      N.jsx("span", { className: "font-mono font-medium", children: n }),
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
  qV = () => N.jsx("div", { className: "w-0 h-0" }),
  JV = ({ id: e, sourceX: t, sourceY: n, targetX: r, targetY: o, markerEnd: i, data: s }) => {
    const [a] = Il({ sourceX: t, sourceY: n, targetX: r, targetY: o, borderRadius: 16 }),
      l = s == null ? void 0 : s.isInitial,
      u = `M ${t} ${n} L ${t} ${n}`;
    return N.jsxs(N.Fragment, {
      children: [
        l &&
          N.jsx("circle", {
            cx: t,
            cy: n,
            r: 6,
            className: "fill-foreground stroke-background",
            strokeWidth: 2,
          }),
        N.jsx(Jo, {
          id: e,
          path: l ? u : a,
          markerEnd: i,
          style: { strokeWidth: 2, stroke: "hsl(var(--foreground))", opacity: 0.8 },
        }),
      ],
    });
  },
  eO = { rootNode: QV, stateNode: YV, compoundStateNode: ZV, eventNode: XV, initialNode: qV },
  tO = { transitionEdge: JV },
  nO = {
    type: "transitionEdge",
    markerEnd: { type: Es.ArrowClosed, color: "hsl(var(--foreground))" },
  },
  rO = { hideAttribution: !0 },
  oO = [Ol, Ol],
  iO = fn.Step,
  sO = Object.freeze(
    Object.defineProperty(
      {
        __proto__: null,
        connectionLineType: iO,
        defaultEdgeOptions: nO,
        edgeTypes: tO,
        nodeTypes: eO,
        proOptions: rO,
        snapGrid: oO,
      },
      Symbol.toStringTag,
      { value: "Module" },
    ),
  ),
  aO = ({ machine: e, activeStateIds: t }) => {
    const n = v.useRef(null),
      [r, o] = v.useState({ open: !1, x: 0, y: 0 }),
      {
        nodes: i,
        edges: s,
        onNodesChange: a,
        onEdgesChange: l,
        onNodeDragStop: u,
        relayout: c,
        tightenAndFitWhenReady: f,
      } = GV({ machine: e, activeStateIds: t }),
      d = v.useCallback((w) => {
        var g;
        w.preventDefault();
        const h = (g = n.current) == null ? void 0 : g.getBoundingClientRect();
        o({
          open: !0,
          x: w.clientX - ((h == null ? void 0 : h.left) ?? 0),
          y: w.clientY - ((h == null ? void 0 : h.top) ?? 0),
        });
      }, []),
      p = v.useCallback(() => o((w) => ({ ...w, open: !1 })), []),
      y = () => c().catch(console.error),
      m = () => f(s).catch(console.error);
    return N.jsxs("div", {
      ref: n,
      className: "relative h-full w-full",
      children: [
        N.jsxs(DE, {
          nodes: i,
          edges: s,
          onNodesChange: a,
          onEdgesChange: l,
          onNodeDragStop: u,
          onPaneContextMenu: d,
          ...sO,
          nodesDraggable: !0,
          nodesConnectable: !1,
          elementsSelectable: !0,
          fitView: !0,
          minZoom: 0.2,
          maxZoom: 1.5,
          snapToGrid: !0,
          className: "bg-background",
          children: [N.jsx(DV, {}), N.jsx(_V, {}), N.jsx(zV, {})],
        }),
        r.open && N.jsx(KV, { x: r.x, y: r.y, onClose: p, onAutoLayout: y, onFitView: m }),
      ],
    });
  },
  lO = (e) => N.jsx(ap, { children: N.jsx(aO, { ...e }) });
function uO() {
  x_();
  const e = ls((l) => l.machines),
    t = ls((l) => l.isConnected),
    [n, r] = v.useState(null),
    [o, i] = v.useState(!1);
  v.useEffect(() => {
    const l = Object.keys(e);
    (!n || !e[n]) && l.length > 0 && r(l[0]);
  }, [e, n]),
    v.useEffect(() => {
      const l = localStorage.getItem("theme"),
        u = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches,
        c = l ? l === "dark" : u;
      document.documentElement.classList.toggle("dark", c), i(c);
    }, []);
  const s = () => {
      const l = !document.documentElement.classList.contains("dark");
      i(l),
        localStorage.setItem("theme", l ? "dark" : "light"),
        document.documentElement.classList.toggle("dark", l);
    },
    a = n ? e[n] : null;
  return N.jsxs("div", {
    className: "flex h-screen w-full flex-col bg-background font-sans text-foreground",
    children: [
      N.jsx(cO, { onToggleTheme: s, isDark: o, isConnected: t }),
      N.jsxs("div", {
        className: "flex flex-1 overflow-hidden",
        children: [
          N.jsx(fO, { machines: e, selectedMachineId: n, onSelectMachine: r }),
          N.jsx("main", {
            className: "flex-1 flex flex-col overflow-hidden",
            children: a ? N.jsx(dO, { machine: a }, a.id) : N.jsx(gO, {}),
          }),
        ],
      }),
    ],
  });
}
const cO = ({ onToggleTheme: e, isDark: t, isConnected: n }) =>
    N.jsxs("header", {
      className: "flex h-14 items-center justify-between border-b bg-card px-4 lg:px-6",
      children: [
        N.jsxs("div", {
          className: "flex items-center gap-2 font-bold",
          children: [
            N.jsx(C_, { className: "h-6 w-6 text-primary" }),
            N.jsx("span", { children: "XState Inspector" }),
          ],
        }),
        N.jsxs("div", {
          className: "flex items-center gap-3",
          children: [
            N.jsxs("div", {
              className:
                "flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium border " +
                (n
                  ? "border-green-600 text-green-700 dark:text-green-400"
                  : "border-amber-600 text-amber-700 dark:text-amber-400"),
              title: n ? "Connected" : "Disconnected",
              children: [
                n ? N.jsx(I_, { className: "h-4 w-4" }) : N.jsx(D_, { className: "h-4 w-4" }),
                N.jsx("span", { children: n ? "Online" : "Offline" }),
              ],
            }),
            N.jsxs(ih, {
              variant: "ghost",
              size: "icon",
              onClick: e,
              children: [
                N.jsx(R_, {
                  className:
                    "h-5 w-5 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0",
                }),
                N.jsx(__, {
                  className:
                    "absolute h-5 w-5 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100",
                }),
                N.jsx("span", { className: "sr-only", children: "Toggle theme" }),
              ],
            }),
          ],
        }),
      ],
    }),
  fO = ({ machines: e, selectedMachineId: t, onSelectMachine: n }) =>
    N.jsxs("aside", {
      className: "hidden w-72 flex-col border-r bg-card p-4 sm:flex",
      children: [
        N.jsx("h2", {
          className: "text-base font-semibold tracking-tight",
          children: "Live Machines",
        }),
        N.jsx("nav", {
          className: "mt-4 flex flex-col gap-1",
          children: Object.values(e).map((r) =>
            N.jsx(
              "div",
              {
                children: N.jsx(ih, {
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
  dO = ({ machine: e }) =>
    N.jsxs("div", {
      className: "grid h-full grid-cols-1 lg:grid-cols-3 gap-4 p-4",
      children: [
        N.jsxs("div", {
          className: "lg:col-span-2 flex flex-col gap-4 relative",
          children: [
            N.jsxs(Ms, {
              className: "flex-1 flex flex-col",
              children: [
                N.jsxs(As, {
                  children: [
                    N.jsx(Rs, { children: e.id }),
                    N.jsxs("p", {
                      className: "text-sm text-muted-foreground",
                      children: [
                        "Current State:",
                        " ",
                        N.jsx("span", {
                          className: "font-mono text-primary",
                          children: e.currentStateIds.join(", "),
                        }),
                      ],
                    }),
                  ],
                }),
                N.jsx(Ds, {
                  className: "flex-1 relative",
                  children: N.jsx(lO, { machine: e, activeStateIds: e.currentStateIds }),
                }),
              ],
            }),
            N.jsx(pO, { machineId: e.id }),
          ],
        }),
        N.jsx("div", { className: "flex flex-col", children: N.jsx(hO, { machine: e }) }),
      ],
    }),
  hO = ({ machine: e }) =>
    N.jsxs(JT, {
      defaultValue: "events",
      className: "flex-1 flex flex-col overflow-hidden",
      children: [
        N.jsxs(Kx, {
          className: "grid w-full grid-cols-3",
          children: [
            N.jsxs(Oa, {
              value: "events",
              children: [N.jsx(k_, { className: "w-4 h-4 mr-2" }), "Event Log"],
            }),
            N.jsxs(Oa, {
              value: "context",
              children: [N.jsx(A_, { className: "w-4 h-4 mr-2" }), "Context"],
            }),
            N.jsxs(Oa, {
              value: "json",
              children: [N.jsx(b_, { className: "w-4 h-4 mr-2" }), "Definition"],
            }),
          ],
        }),
        N.jsx(Fa, {
          value: "events",
          className: "flex-1 overflow-y-auto mt-0",
          children: N.jsx("div", {
            className: "font-mono text-xs space-y-2 p-4",
            children: e.logs
              .slice()
              .reverse()
              .map((t, n) =>
                N.jsxs(
                  "div",
                  {
                    className: "p-2 rounded bg-muted",
                    children: [
                      N.jsx("p", { className: "font-bold text-primary", children: t.type }),
                      N.jsx("pre", {
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
        N.jsx(Fa, {
          value: "context",
          className: "flex-1 overflow-y-auto mt-0",
          children: N.jsx("pre", {
            className: "font-mono text-xs p-4",
            children: JSON.stringify(e.context, null, 2),
          }),
        }),
        N.jsx(Fa, {
          value: "json",
          className: "flex-1 overflow-y-auto mt-0",
          children: N.jsx("pre", {
            className: "font-mono text-xs p-4",
            children: JSON.stringify(e.definition, null, 2),
          }),
        }),
      ],
    }),
  pO = ({ machineId: e }) => {
    const [t, n] = v.useState(!1),
      r = ls((o) => o.sendCommand);
    return N.jsxs(N.Fragment, {
      children: [
        N.jsx("div", {
          className: "absolute bottom-4 left-1/2 -translate-x-1/2",
          children: N.jsxs(dS, {
            children: [
              N.jsx(Ha, {
                onClick: () => r("resume", { machine_id: e }),
                children: N.jsx(N_, { className: "h-4 w-4" }),
              }),
              N.jsx(Ha, {
                onClick: () => r("pause", { machine_id: e }),
                children: N.jsx(T_, { className: "h-4 w-4" }),
              }),
              N.jsx(Ha, { onClick: () => n(!0), children: N.jsx(M_, { className: "h-4 w-4" }) }),
            ],
          }),
        }),
        N.jsx(mO, { open: t, onOpenChange: n, machineId: e }),
      ],
    });
  },
  mO = ({ open: e, onOpenChange: t, machineId: n }) => {
    const [r, o] = v.useState(""),
      [i, s] = v.useState(""),
      a = ls((u) => u.sendCommand),
      l = () => {
        if (!r) return;
        let u = {};
        try {
          i.trim() && (u = JSON.parse(i));
        } catch {
          alert("Invalid JSON in payload.");
          return;
        }
        a("send_event", { machine_id: n, event: { type: r, payload: u } }), t(!1), o(""), s("");
      };
    return N.jsx(gN, {
      open: e,
      onOpenChange: t,
      children: N.jsxs(Pw, {
        children: [
          N.jsx(Mw, { children: N.jsxs(Rw, { children: ["Send Event to ", n] }) }),
          N.jsxs("div", {
            className: "grid gap-4 py-4",
            children: [
              N.jsx(Dw, {
                placeholder: "Event Type (e.g., ENABLE)",
                value: r,
                onChange: (u) => o(u.target.value),
              }),
              N.jsx(Iw, {
                placeholder: 'Payload (JSON), e.g., {"value": 42}',
                value: i,
                onChange: (u) => s(u.target.value),
              }),
            ],
          }),
          N.jsx(Aw, {
            children: N.jsx(hS, {
              className: "w-full",
              onClick: l,
              children: N.jsx("span", {
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
  gO = () =>
    N.jsx("div", {
      className: "flex h-full items-center justify-center m-4",
      children: N.jsxs(Ms, {
        className: "w-full max-w-md",
        children: [
          N.jsx(As, {
            children: N.jsx(Rs, { className: "text-2xl", children: "No Live Machines Detected" }),
          }),
          N.jsx(Ds, {
            children: N.jsx("p", {
              className: "text-muted-foreground",
              children: "Run a Python script with the InspectorPlugin to begin debugging.",
            }),
          }),
        ],
      }),
    });
Mc.createRoot(document.getElementById("root")).render(
  N.jsx(L.StrictMode, { children: N.jsx(uO, {}) }),
);
