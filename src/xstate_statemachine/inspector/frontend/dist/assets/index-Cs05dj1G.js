(function () {
  const t = document.createElement("link").relList;
  if (t && t.supports && t.supports("modulepreload")) return;
  for (const i of document.querySelectorAll('link[rel="modulepreload"]')) r(i);
  new MutationObserver((i) => {
    for (const o of i)
      if (o.type === "childList")
        for (const a of o.addedNodes) a.tagName === "LINK" && a.rel === "modulepreload" && r(a);
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
var ta =
  typeof globalThis < "u"
    ? globalThis
    : typeof window < "u"
    ? window
    : typeof global < "u"
    ? global
    : typeof self < "u"
    ? self
    : {};
function tS(e) {
  return e && e.__esModule && Object.prototype.hasOwnProperty.call(e, "default") ? e.default : e;
}
var nS = { exports: {} },
  Ts = {},
  rS = { exports: {} },
  re = {};
/**
 * @license React
 * react.production.min.js
 *
 * Copyright (c) Facebook, Inc. and its affiliates.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */ var Bo = Symbol.for("react.element"),
  WC = Symbol.for("react.portal"),
  KC = Symbol.for("react.fragment"),
  YC = Symbol.for("react.strict_mode"),
  XC = Symbol.for("react.profiler"),
  QC = Symbol.for("react.provider"),
  ZC = Symbol.for("react.context"),
  JC = Symbol.for("react.forward_ref"),
  eN = Symbol.for("react.suspense"),
  tN = Symbol.for("react.memo"),
  nN = Symbol.for("react.lazy"),
  Xv = Symbol.iterator;
function rN(e) {
  return e === null || typeof e != "object"
    ? null
    : ((e = (Xv && e[Xv]) || e["@@iterator"]), typeof e == "function" ? e : null);
}
var iS = {
    isMounted: function () {
      return !1;
    },
    enqueueForceUpdate: function () {},
    enqueueReplaceState: function () {},
    enqueueSetState: function () {},
  },
  oS = Object.assign,
  aS = {};
function xi(e, t, n) {
  (this.props = e), (this.context = t), (this.refs = aS), (this.updater = n || iS);
}
xi.prototype.isReactComponent = {};
xi.prototype.setState = function (e, t) {
  if (typeof e != "object" && typeof e != "function" && e != null)
    throw Error(
      "setState(...): takes an object of state variables to update or a function which returns an object of state variables."
    );
  this.updater.enqueueSetState(this, e, t, "setState");
};
xi.prototype.forceUpdate = function (e) {
  this.updater.enqueueForceUpdate(this, e, "forceUpdate");
};
function sS() {}
sS.prototype = xi.prototype;
function pg(e, t, n) {
  (this.props = e), (this.context = t), (this.refs = aS), (this.updater = n || iS);
}
var gg = (pg.prototype = new sS());
gg.constructor = pg;
oS(gg, xi.prototype);
gg.isPureReactComponent = !0;
var Qv = Array.isArray,
  uS = Object.prototype.hasOwnProperty,
  vg = { current: null },
  lS = { key: !0, ref: !0, __self: !0, __source: !0 };
function cS(e, t, n) {
  var r,
    i = {},
    o = null,
    a = null;
  if (t != null)
    for (r in (t.ref !== void 0 && (a = t.ref), t.key !== void 0 && (o = "" + t.key), t))
      uS.call(t, r) && !lS.hasOwnProperty(r) && (i[r] = t[r]);
  var s = arguments.length - 2;
  if (s === 1) i.children = n;
  else if (1 < s) {
    for (var u = Array(s), l = 0; l < s; l++) u[l] = arguments[l + 2];
    i.children = u;
  }
  if (e && e.defaultProps) for (r in ((s = e.defaultProps), s)) i[r] === void 0 && (i[r] = s[r]);
  return { $$typeof: Bo, type: e, key: o, ref: a, props: i, _owner: vg.current };
}
function iN(e, t) {
  return { $$typeof: Bo, type: e.type, key: t, ref: e.ref, props: e.props, _owner: e._owner };
}
function mg(e) {
  return typeof e == "object" && e !== null && e.$$typeof === Bo;
}
function oN(e) {
  var t = { "=": "=0", ":": "=2" };
  return (
    "$" +
    e.replace(/[=:]/g, function (n) {
      return t[n];
    })
  );
}
var Zv = /\/+/g;
function xu(e, t) {
  return typeof e == "object" && e !== null && e.key != null ? oN("" + e.key) : t.toString(36);
}
function Ia(e, t, n, r, i) {
  var o = typeof e;
  (o === "undefined" || o === "boolean") && (e = null);
  var a = !1;
  if (e === null) a = !0;
  else
    switch (o) {
      case "string":
      case "number":
        a = !0;
        break;
      case "object":
        switch (e.$$typeof) {
          case Bo:
          case WC:
            a = !0;
        }
    }
  if (a)
    return (
      (a = e),
      (i = i(a)),
      (e = r === "" ? "." + xu(a, 0) : r),
      Qv(i)
        ? ((n = ""),
          e != null && (n = e.replace(Zv, "$&/") + "/"),
          Ia(i, t, n, "", function (l) {
            return l;
          }))
        : i != null &&
          (mg(i) &&
            (i = iN(
              i,
              n +
                (!i.key || (a && a.key === i.key) ? "" : ("" + i.key).replace(Zv, "$&/") + "/") +
                e
            )),
          t.push(i)),
      1
    );
  if (((a = 0), (r = r === "" ? "." : r + ":"), Qv(e)))
    for (var s = 0; s < e.length; s++) {
      o = e[s];
      var u = r + xu(o, s);
      a += Ia(o, t, n, u, i);
    }
  else if (((u = rN(e)), typeof u == "function"))
    for (e = u.call(e), s = 0; !(o = e.next()).done; )
      (o = o.value), (u = r + xu(o, s++)), (a += Ia(o, t, n, u, i));
  else if (o === "object")
    throw (
      ((t = String(e)),
      Error(
        "Objects are not valid as a React child (found: " +
          (t === "[object Object]" ? "object with keys {" + Object.keys(e).join(", ") + "}" : t) +
          "). If you meant to render a collection of children, use an array instead."
      ))
    );
  return a;
}
function na(e, t, n) {
  if (e == null) return e;
  var r = [],
    i = 0;
  return (
    Ia(e, r, "", "", function (o) {
      return t.call(n, o, i++);
    }),
    r
  );
}
function aN(e) {
  if (e._status === -1) {
    var t = e._result;
    (t = t()),
      t.then(
        function (n) {
          (e._status === 0 || e._status === -1) && ((e._status = 1), (e._result = n));
        },
        function (n) {
          (e._status === 0 || e._status === -1) && ((e._status = 2), (e._result = n));
        }
      ),
      e._status === -1 && ((e._status = 0), (e._result = t));
  }
  if (e._status === 1) return e._result.default;
  throw e._result;
}
var Ze = { current: null },
  Aa = { transition: null },
  sN = { ReactCurrentDispatcher: Ze, ReactCurrentBatchConfig: Aa, ReactCurrentOwner: vg };
function fS() {
  throw Error("act(...) is not supported in production builds of React.");
}
re.Children = {
  map: na,
  forEach: function (e, t, n) {
    na(
      e,
      function () {
        t.apply(this, arguments);
      },
      n
    );
  },
  count: function (e) {
    var t = 0;
    return (
      na(e, function () {
        t++;
      }),
      t
    );
  },
  toArray: function (e) {
    return (
      na(e, function (t) {
        return t;
      }) || []
    );
  },
  only: function (e) {
    if (!mg(e))
      throw Error("React.Children.only expected to receive a single React element child.");
    return e;
  },
};
re.Component = xi;
re.Fragment = KC;
re.Profiler = XC;
re.PureComponent = pg;
re.StrictMode = YC;
re.Suspense = eN;
re.__SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED = sN;
re.act = fS;
re.cloneElement = function (e, t, n) {
  if (e == null)
    throw Error(
      "React.cloneElement(...): The argument must be a React element, but you passed " + e + "."
    );
  var r = oS({}, e.props),
    i = e.key,
    o = e.ref,
    a = e._owner;
  if (t != null) {
    if (
      (t.ref !== void 0 && ((o = t.ref), (a = vg.current)),
      t.key !== void 0 && (i = "" + t.key),
      e.type && e.type.defaultProps)
    )
      var s = e.type.defaultProps;
    for (u in t)
      uS.call(t, u) &&
        !lS.hasOwnProperty(u) &&
        (r[u] = t[u] === void 0 && s !== void 0 ? s[u] : t[u]);
  }
  var u = arguments.length - 2;
  if (u === 1) r.children = n;
  else if (1 < u) {
    s = Array(u);
    for (var l = 0; l < u; l++) s[l] = arguments[l + 2];
    r.children = s;
  }
  return { $$typeof: Bo, type: e.type, key: i, ref: o, props: r, _owner: a };
};
re.createContext = function (e) {
  return (
    (e = {
      $$typeof: ZC,
      _currentValue: e,
      _currentValue2: e,
      _threadCount: 0,
      Provider: null,
      Consumer: null,
      _defaultValue: null,
      _globalName: null,
    }),
    (e.Provider = { $$typeof: QC, _context: e }),
    (e.Consumer = e)
  );
};
re.createElement = cS;
re.createFactory = function (e) {
  var t = cS.bind(null, e);
  return (t.type = e), t;
};
re.createRef = function () {
  return { current: null };
};
re.forwardRef = function (e) {
  return { $$typeof: JC, render: e };
};
re.isValidElement = mg;
re.lazy = function (e) {
  return { $$typeof: nN, _payload: { _status: -1, _result: e }, _init: aN };
};
re.memo = function (e, t) {
  return { $$typeof: tN, type: e, compare: t === void 0 ? null : t };
};
re.startTransition = function (e) {
  var t = Aa.transition;
  Aa.transition = {};
  try {
    e();
  } finally {
    Aa.transition = t;
  }
};
re.unstable_act = fS;
re.useCallback = function (e, t) {
  return Ze.current.useCallback(e, t);
};
re.useContext = function (e) {
  return Ze.current.useContext(e);
};
re.useDebugValue = function () {};
re.useDeferredValue = function (e) {
  return Ze.current.useDeferredValue(e);
};
re.useEffect = function (e, t) {
  return Ze.current.useEffect(e, t);
};
re.useId = function () {
  return Ze.current.useId();
};
re.useImperativeHandle = function (e, t, n) {
  return Ze.current.useImperativeHandle(e, t, n);
};
re.useInsertionEffect = function (e, t) {
  return Ze.current.useInsertionEffect(e, t);
};
re.useLayoutEffect = function (e, t) {
  return Ze.current.useLayoutEffect(e, t);
};
re.useMemo = function (e, t) {
  return Ze.current.useMemo(e, t);
};
re.useReducer = function (e, t, n) {
  return Ze.current.useReducer(e, t, n);
};
re.useRef = function (e) {
  return Ze.current.useRef(e);
};
re.useState = function (e) {
  return Ze.current.useState(e);
};
re.useSyncExternalStore = function (e, t, n) {
  return Ze.current.useSyncExternalStore(e, t, n);
};
re.useTransition = function () {
  return Ze.current.useTransition();
};
re.version = "18.3.1";
rS.exports = re;
var q = rS.exports;
const O = tS(q);
/**
 * @license React
 * react-jsx-runtime.production.min.js
 *
 * Copyright (c) Facebook, Inc. and its affiliates.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */ var uN = q,
  lN = Symbol.for("react.element"),
  cN = Symbol.for("react.fragment"),
  fN = Object.prototype.hasOwnProperty,
  dN = uN.__SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED.ReactCurrentOwner,
  hN = { key: !0, ref: !0, __self: !0, __source: !0 };
function dS(e, t, n) {
  var r,
    i = {},
    o = null,
    a = null;
  n !== void 0 && (o = "" + n),
    t.key !== void 0 && (o = "" + t.key),
    t.ref !== void 0 && (a = t.ref);
  for (r in t) fN.call(t, r) && !hN.hasOwnProperty(r) && (i[r] = t[r]);
  if (e && e.defaultProps) for (r in ((t = e.defaultProps), t)) i[r] === void 0 && (i[r] = t[r]);
  return { $$typeof: lN, type: e, key: o, ref: a, props: i, _owner: dN.current };
}
Ts.Fragment = cN;
Ts.jsx = dS;
Ts.jsxs = dS;
nS.exports = Ts;
var W = nS.exports,
  tp = {},
  hS = { exports: {} },
  vt = {},
  pS = { exports: {} },
  gS = {};
/**
 * @license React
 * scheduler.production.min.js
 *
 * Copyright (c) Facebook, Inc. and its affiliates.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */ (function (e) {
  function t(R, b) {
    var A = R.length;
    R.push(b);
    e: for (; 0 < A; ) {
      var L = (A - 1) >>> 1,
        D = R[L];
      if (0 < i(D, b)) (R[L] = b), (R[A] = D), (A = L);
      else break e;
    }
  }
  function n(R) {
    return R.length === 0 ? null : R[0];
  }
  function r(R) {
    if (R.length === 0) return null;
    var b = R[0],
      A = R.pop();
    if (A !== b) {
      R[0] = A;
      e: for (var L = 0, D = R.length, H = D >>> 1; L < H; ) {
        var B = 2 * (L + 1) - 1,
          G = R[B],
          X = B + 1,
          J = R[X];
        if (0 > i(G, A))
          X < D && 0 > i(J, G)
            ? ((R[L] = J), (R[X] = A), (L = X))
            : ((R[L] = G), (R[B] = A), (L = B));
        else if (X < D && 0 > i(J, A)) (R[L] = J), (R[X] = A), (L = X);
        else break e;
      }
    }
    return b;
  }
  function i(R, b) {
    var A = R.sortIndex - b.sortIndex;
    return A !== 0 ? A : R.id - b.id;
  }
  if (typeof performance == "object" && typeof performance.now == "function") {
    var o = performance;
    e.unstable_now = function () {
      return o.now();
    };
  } else {
    var a = Date,
      s = a.now();
    e.unstable_now = function () {
      return a.now() - s;
    };
  }
  var u = [],
    l = [],
    c = 1,
    f = null,
    d = 3,
    h = !1,
    m = !1,
    v = !1,
    w = typeof setTimeout == "function" ? setTimeout : null,
    p = typeof clearTimeout == "function" ? clearTimeout : null,
    g = typeof setImmediate < "u" ? setImmediate : null;
  typeof navigator < "u" &&
    navigator.scheduling !== void 0 &&
    navigator.scheduling.isInputPending !== void 0 &&
    navigator.scheduling.isInputPending.bind(navigator.scheduling);
  function y(R) {
    for (var b = n(l); b !== null; ) {
      if (b.callback === null) r(l);
      else if (b.startTime <= R) r(l), (b.sortIndex = b.expirationTime), t(u, b);
      else break;
      b = n(l);
    }
  }
  function _(R) {
    if (((v = !1), y(R), !m))
      if (n(u) !== null) (m = !0), N(S);
      else {
        var b = n(l);
        b !== null && $(_, b.startTime - R);
      }
  }
  function S(R, b) {
    (m = !1), v && ((v = !1), p(C), (C = -1)), (h = !0);
    var A = d;
    try {
      for (y(b), f = n(u); f !== null && (!(f.expirationTime > b) || (R && !M())); ) {
        var L = f.callback;
        if (typeof L == "function") {
          (f.callback = null), (d = f.priorityLevel);
          var D = L(f.expirationTime <= b);
          (b = e.unstable_now()),
            typeof D == "function" ? (f.callback = D) : f === n(u) && r(u),
            y(b);
        } else r(u);
        f = n(u);
      }
      if (f !== null) var H = !0;
      else {
        var B = n(l);
        B !== null && $(_, B.startTime - b), (H = !1);
      }
      return H;
    } finally {
      (f = null), (d = A), (h = !1);
    }
  }
  var E = !1,
    k = null,
    C = -1,
    T = 5,
    I = -1;
  function M() {
    return !(e.unstable_now() - I < T);
  }
  function z() {
    if (k !== null) {
      var R = e.unstable_now();
      I = R;
      var b = !0;
      try {
        b = k(!0, R);
      } finally {
        b ? F() : ((E = !1), (k = null));
      }
    } else E = !1;
  }
  var F;
  if (typeof g == "function")
    F = function () {
      g(z);
    };
  else if (typeof MessageChannel < "u") {
    var x = new MessageChannel(),
      P = x.port2;
    (x.port1.onmessage = z),
      (F = function () {
        P.postMessage(null);
      });
  } else
    F = function () {
      w(z, 0);
    };
  function N(R) {
    (k = R), E || ((E = !0), F());
  }
  function $(R, b) {
    C = w(function () {
      R(e.unstable_now());
    }, b);
  }
  (e.unstable_IdlePriority = 5),
    (e.unstable_ImmediatePriority = 1),
    (e.unstable_LowPriority = 4),
    (e.unstable_NormalPriority = 3),
    (e.unstable_Profiling = null),
    (e.unstable_UserBlockingPriority = 2),
    (e.unstable_cancelCallback = function (R) {
      R.callback = null;
    }),
    (e.unstable_continueExecution = function () {
      m || h || ((m = !0), N(S));
    }),
    (e.unstable_forceFrameRate = function (R) {
      0 > R || 125 < R
        ? console.error(
            "forceFrameRate takes a positive int between 0 and 125, forcing frame rates higher than 125 fps is not supported"
          )
        : (T = 0 < R ? Math.floor(1e3 / R) : 5);
    }),
    (e.unstable_getCurrentPriorityLevel = function () {
      return d;
    }),
    (e.unstable_getFirstCallbackNode = function () {
      return n(u);
    }),
    (e.unstable_next = function (R) {
      switch (d) {
        case 1:
        case 2:
        case 3:
          var b = 3;
          break;
        default:
          b = d;
      }
      var A = d;
      d = b;
      try {
        return R();
      } finally {
        d = A;
      }
    }),
    (e.unstable_pauseExecution = function () {}),
    (e.unstable_requestPaint = function () {}),
    (e.unstable_runWithPriority = function (R, b) {
      switch (R) {
        case 1:
        case 2:
        case 3:
        case 4:
        case 5:
          break;
        default:
          R = 3;
      }
      var A = d;
      d = R;
      try {
        return b();
      } finally {
        d = A;
      }
    }),
    (e.unstable_scheduleCallback = function (R, b, A) {
      var L = e.unstable_now();
      switch (
        (typeof A == "object" && A !== null
          ? ((A = A.delay), (A = typeof A == "number" && 0 < A ? L + A : L))
          : (A = L),
        R)
      ) {
        case 1:
          var D = -1;
          break;
        case 2:
          D = 250;
          break;
        case 5:
          D = 1073741823;
          break;
        case 4:
          D = 1e4;
          break;
        default:
          D = 5e3;
      }
      return (
        (D = A + D),
        (R = {
          id: c++,
          callback: b,
          priorityLevel: R,
          startTime: A,
          expirationTime: D,
          sortIndex: -1,
        }),
        A > L
          ? ((R.sortIndex = A),
            t(l, R),
            n(u) === null && R === n(l) && (v ? (p(C), (C = -1)) : (v = !0), $(_, A - L)))
          : ((R.sortIndex = D), t(u, R), m || h || ((m = !0), N(S))),
        R
      );
    }),
    (e.unstable_shouldYield = M),
    (e.unstable_wrapCallback = function (R) {
      var b = d;
      return function () {
        var A = d;
        d = b;
        try {
          return R.apply(this, arguments);
        } finally {
          d = A;
        }
      };
    });
})(gS);
pS.exports = gS;
var pN = pS.exports;
/**
 * @license React
 * react-dom.production.min.js
 *
 * Copyright (c) Facebook, Inc. and its affiliates.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */ var gN = q,
  pt = pN;
function j(e) {
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
var vS = new Set(),
  vo = {};
function Rr(e, t) {
  ci(e, t), ci(e + "Capture", t);
}
function ci(e, t) {
  for (vo[e] = t, e = 0; e < t.length; e++) vS.add(t[e]);
}
var mn = !(
    typeof window > "u" ||
    typeof window.document > "u" ||
    typeof window.document.createElement > "u"
  ),
  np = Object.prototype.hasOwnProperty,
  vN = /^[:A-Z_a-z\u00C0-\u00D6\u00D8-\u00F6\u00F8-\u02FF\u0370-\u037D\u037F-\u1FFF\u200C-\u200D\u2070-\u218F\u2C00-\u2FEF\u3001-\uD7FF\uF900-\uFDCF\uFDF0-\uFFFD][:A-Z_a-z\u00C0-\u00D6\u00D8-\u00F6\u00F8-\u02FF\u0370-\u037D\u037F-\u1FFF\u200C-\u200D\u2070-\u218F\u2C00-\u2FEF\u3001-\uD7FF\uF900-\uFDCF\uFDF0-\uFFFD\-.0-9\u00B7\u0300-\u036F\u203F-\u2040]*$/,
  Jv = {},
  em = {};
function mN(e) {
  return np.call(em, e) ? !0 : np.call(Jv, e) ? !1 : vN.test(e) ? (em[e] = !0) : ((Jv[e] = !0), !1);
}
function yN(e, t, n, r) {
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
function _N(e, t, n, r) {
  if (t === null || typeof t > "u" || yN(e, t, n, r)) return !0;
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
function Je(e, t, n, r, i, o, a) {
  (this.acceptsBooleans = t === 2 || t === 3 || t === 4),
    (this.attributeName = r),
    (this.attributeNamespace = i),
    (this.mustUseProperty = n),
    (this.propertyName = e),
    (this.type = t),
    (this.sanitizeURL = o),
    (this.removeEmptyString = a);
}
var je = {};
"children dangerouslySetInnerHTML defaultValue defaultChecked innerHTML suppressContentEditableWarning suppressHydrationWarning style"
  .split(" ")
  .forEach(function (e) {
    je[e] = new Je(e, 0, !1, e, null, !1, !1);
  });
[
  ["acceptCharset", "accept-charset"],
  ["className", "class"],
  ["htmlFor", "for"],
  ["httpEquiv", "http-equiv"],
].forEach(function (e) {
  var t = e[0];
  je[t] = new Je(t, 1, !1, e[1], null, !1, !1);
});
["contentEditable", "draggable", "spellCheck", "value"].forEach(function (e) {
  je[e] = new Je(e, 2, !1, e.toLowerCase(), null, !1, !1);
});
["autoReverse", "externalResourcesRequired", "focusable", "preserveAlpha"].forEach(function (e) {
  je[e] = new Je(e, 2, !1, e, null, !1, !1);
});
"allowFullScreen async autoFocus autoPlay controls default defer disabled disablePictureInPicture disableRemotePlayback formNoValidate hidden loop noModule noValidate open playsInline readOnly required reversed scoped seamless itemScope"
  .split(" ")
  .forEach(function (e) {
    je[e] = new Je(e, 3, !1, e.toLowerCase(), null, !1, !1);
  });
["checked", "multiple", "muted", "selected"].forEach(function (e) {
  je[e] = new Je(e, 3, !0, e, null, !1, !1);
});
["capture", "download"].forEach(function (e) {
  je[e] = new Je(e, 4, !1, e, null, !1, !1);
});
["cols", "rows", "size", "span"].forEach(function (e) {
  je[e] = new Je(e, 6, !1, e, null, !1, !1);
});
["rowSpan", "start"].forEach(function (e) {
  je[e] = new Je(e, 5, !1, e.toLowerCase(), null, !1, !1);
});
var yg = /[\-:]([a-z])/g;
function _g(e) {
  return e[1].toUpperCase();
}
"accent-height alignment-baseline arabic-form baseline-shift cap-height clip-path clip-rule color-interpolation color-interpolation-filters color-profile color-rendering dominant-baseline enable-background fill-opacity fill-rule flood-color flood-opacity font-family font-size font-size-adjust font-stretch font-style font-variant font-weight glyph-name glyph-orientation-horizontal glyph-orientation-vertical horiz-adv-x horiz-origin-x image-rendering letter-spacing lighting-color marker-end marker-mid marker-start overline-position overline-thickness paint-order panose-1 pointer-events rendering-intent shape-rendering stop-color stop-opacity strikethrough-position strikethrough-thickness stroke-dasharray stroke-dashoffset stroke-linecap stroke-linejoin stroke-miterlimit stroke-opacity stroke-width text-anchor text-decoration text-rendering underline-position underline-thickness unicode-bidi unicode-range units-per-em v-alphabetic v-hanging v-ideographic v-mathematical vector-effect vert-adv-y vert-origin-x vert-origin-y word-spacing writing-mode xmlns:xlink x-height"
  .split(" ")
  .forEach(function (e) {
    var t = e.replace(yg, _g);
    je[t] = new Je(t, 1, !1, e, null, !1, !1);
  });
"xlink:actuate xlink:arcrole xlink:role xlink:show xlink:title xlink:type"
  .split(" ")
  .forEach(function (e) {
    var t = e.replace(yg, _g);
    je[t] = new Je(t, 1, !1, e, "http://www.w3.org/1999/xlink", !1, !1);
  });
["xml:base", "xml:lang", "xml:space"].forEach(function (e) {
  var t = e.replace(yg, _g);
  je[t] = new Je(t, 1, !1, e, "http://www.w3.org/XML/1998/namespace", !1, !1);
});
["tabIndex", "crossOrigin"].forEach(function (e) {
  je[e] = new Je(e, 1, !1, e.toLowerCase(), null, !1, !1);
});
je.xlinkHref = new Je("xlinkHref", 1, !1, "xlink:href", "http://www.w3.org/1999/xlink", !0, !1);
["src", "href", "action", "formAction"].forEach(function (e) {
  je[e] = new Je(e, 1, !1, e.toLowerCase(), null, !0, !0);
});
function wg(e, t, n, r) {
  var i = je.hasOwnProperty(t) ? je[t] : null;
  (i !== null
    ? i.type !== 0
    : r || !(2 < t.length) || (t[0] !== "o" && t[0] !== "O") || (t[1] !== "n" && t[1] !== "N")) &&
    (_N(t, n, i, r) && (n = null),
    r || i === null
      ? mN(t) && (n === null ? e.removeAttribute(t) : e.setAttribute(t, "" + n))
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
var bn = gN.__SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED,
  ra = Symbol.for("react.element"),
  jr = Symbol.for("react.portal"),
  Br = Symbol.for("react.fragment"),
  xg = Symbol.for("react.strict_mode"),
  rp = Symbol.for("react.profiler"),
  mS = Symbol.for("react.provider"),
  yS = Symbol.for("react.context"),
  Sg = Symbol.for("react.forward_ref"),
  ip = Symbol.for("react.suspense"),
  op = Symbol.for("react.suspense_list"),
  Eg = Symbol.for("react.memo"),
  Pn = Symbol.for("react.lazy"),
  _S = Symbol.for("react.offscreen"),
  tm = Symbol.iterator;
function Mi(e) {
  return e === null || typeof e != "object"
    ? null
    : ((e = (tm && e[tm]) || e["@@iterator"]), typeof e == "function" ? e : null);
}
var _e = Object.assign,
  Su;
function Wi(e) {
  if (Su === void 0)
    try {
      throw Error();
    } catch (n) {
      var t = n.stack.trim().match(/\n( *(at )?)/);
      Su = (t && t[1]) || "";
    }
  return (
    `
` +
    Su +
    e
  );
}
var Eu = !1;
function bu(e, t) {
  if (!e || Eu) return "";
  Eu = !0;
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
          a = i.length - 1,
          s = o.length - 1;
        1 <= a && 0 <= s && i[a] !== o[s];

      )
        s--;
      for (; 1 <= a && 0 <= s; a--, s--)
        if (i[a] !== o[s]) {
          if (a !== 1 || s !== 1)
            do
              if ((a--, s--, 0 > s || i[a] !== o[s])) {
                var u =
                  `
` + i[a].replace(" at new ", " at ");
                return (
                  e.displayName &&
                    u.includes("<anonymous>") &&
                    (u = u.replace("<anonymous>", e.displayName)),
                  u
                );
              }
            while (1 <= a && 0 <= s);
          break;
        }
    }
  } finally {
    (Eu = !1), (Error.prepareStackTrace = n);
  }
  return (e = e ? e.displayName || e.name : "") ? Wi(e) : "";
}
function wN(e) {
  switch (e.tag) {
    case 5:
      return Wi(e.type);
    case 16:
      return Wi("Lazy");
    case 13:
      return Wi("Suspense");
    case 19:
      return Wi("SuspenseList");
    case 0:
    case 2:
    case 15:
      return (e = bu(e.type, !1)), e;
    case 11:
      return (e = bu(e.type.render, !1)), e;
    case 1:
      return (e = bu(e.type, !0)), e;
    default:
      return "";
  }
}
function ap(e) {
  if (e == null) return null;
  if (typeof e == "function") return e.displayName || e.name || null;
  if (typeof e == "string") return e;
  switch (e) {
    case Br:
      return "Fragment";
    case jr:
      return "Portal";
    case rp:
      return "Profiler";
    case xg:
      return "StrictMode";
    case ip:
      return "Suspense";
    case op:
      return "SuspenseList";
  }
  if (typeof e == "object")
    switch (e.$$typeof) {
      case yS:
        return (e.displayName || "Context") + ".Consumer";
      case mS:
        return (e._context.displayName || "Context") + ".Provider";
      case Sg:
        var t = e.render;
        return (
          (e = e.displayName),
          e ||
            ((e = t.displayName || t.name || ""),
            (e = e !== "" ? "ForwardRef(" + e + ")" : "ForwardRef")),
          e
        );
      case Eg:
        return (t = e.displayName || null), t !== null ? t : ap(e.type) || "Memo";
      case Pn:
        (t = e._payload), (e = e._init);
        try {
          return ap(e(t));
        } catch {}
    }
  return null;
}
function xN(e) {
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
      return ap(t);
    case 8:
      return t === xg ? "StrictMode" : "Mode";
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
function Jn(e) {
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
function wS(e) {
  var t = e.type;
  return (e = e.nodeName) && e.toLowerCase() === "input" && (t === "checkbox" || t === "radio");
}
function SN(e) {
  var t = wS(e) ? "checked" : "value",
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
        set: function (a) {
          (r = "" + a), o.call(this, a);
        },
      }),
      Object.defineProperty(e, t, { enumerable: n.enumerable }),
      {
        getValue: function () {
          return r;
        },
        setValue: function (a) {
          r = "" + a;
        },
        stopTracking: function () {
          (e._valueTracker = null), delete e[t];
        },
      }
    );
  }
}
function ia(e) {
  e._valueTracker || (e._valueTracker = SN(e));
}
function xS(e) {
  if (!e) return !1;
  var t = e._valueTracker;
  if (!t) return !0;
  var n = t.getValue(),
    r = "";
  return (
    e && (r = wS(e) ? (e.checked ? "true" : "false") : e.value),
    (e = r),
    e !== n ? (t.setValue(e), !0) : !1
  );
}
function Ga(e) {
  if (((e = e || (typeof document < "u" ? document : void 0)), typeof e > "u")) return null;
  try {
    return e.activeElement || e.body;
  } catch {
    return e.body;
  }
}
function sp(e, t) {
  var n = t.checked;
  return _e({}, t, {
    defaultChecked: void 0,
    defaultValue: void 0,
    value: void 0,
    checked: n ?? e._wrapperState.initialChecked,
  });
}
function nm(e, t) {
  var n = t.defaultValue == null ? "" : t.defaultValue,
    r = t.checked != null ? t.checked : t.defaultChecked;
  (n = Jn(t.value != null ? t.value : n)),
    (e._wrapperState = {
      initialChecked: r,
      initialValue: n,
      controlled: t.type === "checkbox" || t.type === "radio" ? t.checked != null : t.value != null,
    });
}
function SS(e, t) {
  (t = t.checked), t != null && wg(e, "checked", t, !1);
}
function up(e, t) {
  SS(e, t);
  var n = Jn(t.value),
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
    ? lp(e, t.type, n)
    : t.hasOwnProperty("defaultValue") && lp(e, t.type, Jn(t.defaultValue)),
    t.checked == null && t.defaultChecked != null && (e.defaultChecked = !!t.defaultChecked);
}
function rm(e, t, n) {
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
function lp(e, t, n) {
  (t !== "number" || Ga(e.ownerDocument) !== e) &&
    (n == null
      ? (e.defaultValue = "" + e._wrapperState.initialValue)
      : e.defaultValue !== "" + n && (e.defaultValue = "" + n));
}
var Ki = Array.isArray;
function ei(e, t, n, r) {
  if (((e = e.options), t)) {
    t = {};
    for (var i = 0; i < n.length; i++) t["$" + n[i]] = !0;
    for (n = 0; n < e.length; n++)
      (i = t.hasOwnProperty("$" + e[n].value)),
        e[n].selected !== i && (e[n].selected = i),
        i && r && (e[n].defaultSelected = !0);
  } else {
    for (n = "" + Jn(n), t = null, i = 0; i < e.length; i++) {
      if (e[i].value === n) {
        (e[i].selected = !0), r && (e[i].defaultSelected = !0);
        return;
      }
      t !== null || e[i].disabled || (t = e[i]);
    }
    t !== null && (t.selected = !0);
  }
}
function cp(e, t) {
  if (t.dangerouslySetInnerHTML != null) throw Error(j(91));
  return _e({}, t, {
    value: void 0,
    defaultValue: void 0,
    children: "" + e._wrapperState.initialValue,
  });
}
function im(e, t) {
  var n = t.value;
  if (n == null) {
    if (((n = t.children), (t = t.defaultValue), n != null)) {
      if (t != null) throw Error(j(92));
      if (Ki(n)) {
        if (1 < n.length) throw Error(j(93));
        n = n[0];
      }
      t = n;
    }
    t == null && (t = ""), (n = t);
  }
  e._wrapperState = { initialValue: Jn(n) };
}
function ES(e, t) {
  var n = Jn(t.value),
    r = Jn(t.defaultValue);
  n != null &&
    ((n = "" + n),
    n !== e.value && (e.value = n),
    t.defaultValue == null && e.defaultValue !== n && (e.defaultValue = n)),
    r != null && (e.defaultValue = "" + r);
}
function om(e) {
  var t = e.textContent;
  t === e._wrapperState.initialValue && t !== "" && t !== null && (e.value = t);
}
function bS(e) {
  switch (e) {
    case "svg":
      return "http://www.w3.org/2000/svg";
    case "math":
      return "http://www.w3.org/1998/Math/MathML";
    default:
      return "http://www.w3.org/1999/xhtml";
  }
}
function fp(e, t) {
  return e == null || e === "http://www.w3.org/1999/xhtml"
    ? bS(t)
    : e === "http://www.w3.org/2000/svg" && t === "foreignObject"
    ? "http://www.w3.org/1999/xhtml"
    : e;
}
var oa,
  kS = (function (e) {
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
        oa = oa || document.createElement("div"),
          oa.innerHTML = "<svg>" + t.valueOf().toString() + "</svg>",
          t = oa.firstChild;
        e.firstChild;

      )
        e.removeChild(e.firstChild);
      for (; t.firstChild; ) e.appendChild(t.firstChild);
    }
  });
function mo(e, t) {
  if (t) {
    var n = e.firstChild;
    if (n && n === e.lastChild && n.nodeType === 3) {
      n.nodeValue = t;
      return;
    }
  }
  e.textContent = t;
}
var ao = {
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
  EN = ["Webkit", "ms", "Moz", "O"];
Object.keys(ao).forEach(function (e) {
  EN.forEach(function (t) {
    (t = t + e.charAt(0).toUpperCase() + e.substring(1)), (ao[t] = ao[e]);
  });
});
function CS(e, t, n) {
  return t == null || typeof t == "boolean" || t === ""
    ? ""
    : n || typeof t != "number" || t === 0 || (ao.hasOwnProperty(e) && ao[e])
    ? ("" + t).trim()
    : t + "px";
}
function NS(e, t) {
  e = e.style;
  for (var n in t)
    if (t.hasOwnProperty(n)) {
      var r = n.indexOf("--") === 0,
        i = CS(n, t[n], r);
      n === "float" && (n = "cssFloat"), r ? e.setProperty(n, i) : (e[n] = i);
    }
}
var bN = _e(
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
  }
);
function dp(e, t) {
  if (t) {
    if (bN[e] && (t.children != null || t.dangerouslySetInnerHTML != null)) throw Error(j(137, e));
    if (t.dangerouslySetInnerHTML != null) {
      if (t.children != null) throw Error(j(60));
      if (typeof t.dangerouslySetInnerHTML != "object" || !("__html" in t.dangerouslySetInnerHTML))
        throw Error(j(61));
    }
    if (t.style != null && typeof t.style != "object") throw Error(j(62));
  }
}
function hp(e, t) {
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
var pp = null;
function bg(e) {
  return (
    (e = e.target || e.srcElement || window),
    e.correspondingUseElement && (e = e.correspondingUseElement),
    e.nodeType === 3 ? e.parentNode : e
  );
}
var gp = null,
  ti = null,
  ni = null;
function am(e) {
  if ((e = Uo(e))) {
    if (typeof gp != "function") throw Error(j(280));
    var t = e.stateNode;
    t && ((t = qs(t)), gp(e.stateNode, e.type, t));
  }
}
function RS(e) {
  ti ? (ni ? ni.push(e) : (ni = [e])) : (ti = e);
}
function TS() {
  if (ti) {
    var e = ti,
      t = ni;
    if (((ni = ti = null), am(e), t)) for (e = 0; e < t.length; e++) am(t[e]);
  }
}
function IS(e, t) {
  return e(t);
}
function AS() {}
var ku = !1;
function MS(e, t, n) {
  if (ku) return e(t, n);
  ku = !0;
  try {
    return IS(e, t, n);
  } finally {
    (ku = !1), (ti !== null || ni !== null) && (AS(), TS());
  }
}
function yo(e, t) {
  var n = e.stateNode;
  if (n === null) return null;
  var r = qs(n);
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
  if (n && typeof n != "function") throw Error(j(231, t, typeof n));
  return n;
}
var vp = !1;
if (mn)
  try {
    var Pi = {};
    Object.defineProperty(Pi, "passive", {
      get: function () {
        vp = !0;
      },
    }),
      window.addEventListener("test", Pi, Pi),
      window.removeEventListener("test", Pi, Pi);
  } catch {
    vp = !1;
  }
function kN(e, t, n, r, i, o, a, s, u) {
  var l = Array.prototype.slice.call(arguments, 3);
  try {
    t.apply(n, l);
  } catch (c) {
    this.onError(c);
  }
}
var so = !1,
  Wa = null,
  Ka = !1,
  mp = null,
  CN = {
    onError: function (e) {
      (so = !0), (Wa = e);
    },
  };
function NN(e, t, n, r, i, o, a, s, u) {
  (so = !1), (Wa = null), kN.apply(CN, arguments);
}
function RN(e, t, n, r, i, o, a, s, u) {
  if ((NN.apply(this, arguments), so)) {
    if (so) {
      var l = Wa;
      (so = !1), (Wa = null);
    } else throw Error(j(198));
    Ka || ((Ka = !0), (mp = l));
  }
}
function Tr(e) {
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
function PS(e) {
  if (e.tag === 13) {
    var t = e.memoizedState;
    if ((t === null && ((e = e.alternate), e !== null && (t = e.memoizedState)), t !== null))
      return t.dehydrated;
  }
  return null;
}
function sm(e) {
  if (Tr(e) !== e) throw Error(j(188));
}
function TN(e) {
  var t = e.alternate;
  if (!t) {
    if (((t = Tr(e)), t === null)) throw Error(j(188));
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
        if (o === n) return sm(i), e;
        if (o === r) return sm(i), t;
        o = o.sibling;
      }
      throw Error(j(188));
    }
    if (n.return !== r.return) (n = i), (r = o);
    else {
      for (var a = !1, s = i.child; s; ) {
        if (s === n) {
          (a = !0), (n = i), (r = o);
          break;
        }
        if (s === r) {
          (a = !0), (r = i), (n = o);
          break;
        }
        s = s.sibling;
      }
      if (!a) {
        for (s = o.child; s; ) {
          if (s === n) {
            (a = !0), (n = o), (r = i);
            break;
          }
          if (s === r) {
            (a = !0), (r = o), (n = i);
            break;
          }
          s = s.sibling;
        }
        if (!a) throw Error(j(189));
      }
    }
    if (n.alternate !== r) throw Error(j(190));
  }
  if (n.tag !== 3) throw Error(j(188));
  return n.stateNode.current === n ? e : t;
}
function qS(e) {
  return (e = TN(e)), e !== null ? OS(e) : null;
}
function OS(e) {
  if (e.tag === 5 || e.tag === 6) return e;
  for (e = e.child; e !== null; ) {
    var t = OS(e);
    if (t !== null) return t;
    e = e.sibling;
  }
  return null;
}
var LS = pt.unstable_scheduleCallback,
  um = pt.unstable_cancelCallback,
  IN = pt.unstable_shouldYield,
  AN = pt.unstable_requestPaint,
  ke = pt.unstable_now,
  MN = pt.unstable_getCurrentPriorityLevel,
  kg = pt.unstable_ImmediatePriority,
  zS = pt.unstable_UserBlockingPriority,
  Ya = pt.unstable_NormalPriority,
  PN = pt.unstable_LowPriority,
  $S = pt.unstable_IdlePriority,
  Is = null,
  Xt = null;
function qN(e) {
  if (Xt && typeof Xt.onCommitFiberRoot == "function")
    try {
      Xt.onCommitFiberRoot(Is, e, void 0, (e.current.flags & 128) === 128);
    } catch {}
}
var Lt = Math.clz32 ? Math.clz32 : zN,
  ON = Math.log,
  LN = Math.LN2;
function zN(e) {
  return (e >>>= 0), e === 0 ? 32 : (31 - ((ON(e) / LN) | 0)) | 0;
}
var aa = 64,
  sa = 4194304;
function Yi(e) {
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
function Xa(e, t) {
  var n = e.pendingLanes;
  if (n === 0) return 0;
  var r = 0,
    i = e.suspendedLanes,
    o = e.pingedLanes,
    a = n & 268435455;
  if (a !== 0) {
    var s = a & ~i;
    s !== 0 ? (r = Yi(s)) : ((o &= a), o !== 0 && (r = Yi(o)));
  } else (a = n & ~i), a !== 0 ? (r = Yi(a)) : o !== 0 && (r = Yi(o));
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
      (n = 31 - Lt(t)), (i = 1 << n), (r |= e[n]), (t &= ~i);
  return r;
}
function $N(e, t) {
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
function DN(e, t) {
  for (
    var n = e.suspendedLanes, r = e.pingedLanes, i = e.expirationTimes, o = e.pendingLanes;
    0 < o;

  ) {
    var a = 31 - Lt(o),
      s = 1 << a,
      u = i[a];
    u === -1 ? (!(s & n) || s & r) && (i[a] = $N(s, t)) : u <= t && (e.expiredLanes |= s),
      (o &= ~s);
  }
}
function yp(e) {
  return (e = e.pendingLanes & -1073741825), e !== 0 ? e : e & 1073741824 ? 1073741824 : 0;
}
function DS() {
  var e = aa;
  return (aa <<= 1), !(aa & 4194240) && (aa = 64), e;
}
function Cu(e) {
  for (var t = [], n = 0; 31 > n; n++) t.push(e);
  return t;
}
function Ho(e, t, n) {
  (e.pendingLanes |= t),
    t !== 536870912 && ((e.suspendedLanes = 0), (e.pingedLanes = 0)),
    (e = e.eventTimes),
    (t = 31 - Lt(t)),
    (e[t] = n);
}
function FN(e, t) {
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
    var i = 31 - Lt(n),
      o = 1 << i;
    (t[i] = 0), (r[i] = -1), (e[i] = -1), (n &= ~o);
  }
}
function Cg(e, t) {
  var n = (e.entangledLanes |= t);
  for (e = e.entanglements; n; ) {
    var r = 31 - Lt(n),
      i = 1 << r;
    (i & t) | (e[r] & t) && (e[r] |= t), (n &= ~i);
  }
}
var le = 0;
function FS(e) {
  return (e &= -e), 1 < e ? (4 < e ? (e & 268435455 ? 16 : 536870912) : 4) : 1;
}
var jS,
  Ng,
  BS,
  HS,
  VS,
  _p = !1,
  ua = [],
  Hn = null,
  Vn = null,
  Un = null,
  _o = new Map(),
  wo = new Map(),
  zn = [],
  jN = "mousedown mouseup touchcancel touchend touchstart auxclick dblclick pointercancel pointerdown pointerup dragend dragstart drop compositionend compositionstart keydown keypress keyup input textInput copy cut paste click change contextmenu reset submit".split(
    " "
  );
function lm(e, t) {
  switch (e) {
    case "focusin":
    case "focusout":
      Hn = null;
      break;
    case "dragenter":
    case "dragleave":
      Vn = null;
      break;
    case "mouseover":
    case "mouseout":
      Un = null;
      break;
    case "pointerover":
    case "pointerout":
      _o.delete(t.pointerId);
      break;
    case "gotpointercapture":
    case "lostpointercapture":
      wo.delete(t.pointerId);
  }
}
function qi(e, t, n, r, i, o) {
  return e === null || e.nativeEvent !== o
    ? ((e = {
        blockedOn: t,
        domEventName: n,
        eventSystemFlags: r,
        nativeEvent: o,
        targetContainers: [i],
      }),
      t !== null && ((t = Uo(t)), t !== null && Ng(t)),
      e)
    : ((e.eventSystemFlags |= r),
      (t = e.targetContainers),
      i !== null && t.indexOf(i) === -1 && t.push(i),
      e);
}
function BN(e, t, n, r, i) {
  switch (t) {
    case "focusin":
      return (Hn = qi(Hn, e, t, n, r, i)), !0;
    case "dragenter":
      return (Vn = qi(Vn, e, t, n, r, i)), !0;
    case "mouseover":
      return (Un = qi(Un, e, t, n, r, i)), !0;
    case "pointerover":
      var o = i.pointerId;
      return _o.set(o, qi(_o.get(o) || null, e, t, n, r, i)), !0;
    case "gotpointercapture":
      return (o = i.pointerId), wo.set(o, qi(wo.get(o) || null, e, t, n, r, i)), !0;
  }
  return !1;
}
function US(e) {
  var t = fr(e.target);
  if (t !== null) {
    var n = Tr(t);
    if (n !== null) {
      if (((t = n.tag), t === 13)) {
        if (((t = PS(n)), t !== null)) {
          (e.blockedOn = t),
            VS(e.priority, function () {
              BS(n);
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
function Ma(e) {
  if (e.blockedOn !== null) return !1;
  for (var t = e.targetContainers; 0 < t.length; ) {
    var n = wp(e.domEventName, e.eventSystemFlags, t[0], e.nativeEvent);
    if (n === null) {
      n = e.nativeEvent;
      var r = new n.constructor(n.type, n);
      (pp = r), n.target.dispatchEvent(r), (pp = null);
    } else return (t = Uo(n)), t !== null && Ng(t), (e.blockedOn = n), !1;
    t.shift();
  }
  return !0;
}
function cm(e, t, n) {
  Ma(e) && n.delete(t);
}
function HN() {
  (_p = !1),
    Hn !== null && Ma(Hn) && (Hn = null),
    Vn !== null && Ma(Vn) && (Vn = null),
    Un !== null && Ma(Un) && (Un = null),
    _o.forEach(cm),
    wo.forEach(cm);
}
function Oi(e, t) {
  e.blockedOn === t &&
    ((e.blockedOn = null),
    _p || ((_p = !0), pt.unstable_scheduleCallback(pt.unstable_NormalPriority, HN)));
}
function xo(e) {
  function t(i) {
    return Oi(i, e);
  }
  if (0 < ua.length) {
    Oi(ua[0], e);
    for (var n = 1; n < ua.length; n++) {
      var r = ua[n];
      r.blockedOn === e && (r.blockedOn = null);
    }
  }
  for (
    Hn !== null && Oi(Hn, e),
      Vn !== null && Oi(Vn, e),
      Un !== null && Oi(Un, e),
      _o.forEach(t),
      wo.forEach(t),
      n = 0;
    n < zn.length;
    n++
  )
    (r = zn[n]), r.blockedOn === e && (r.blockedOn = null);
  for (; 0 < zn.length && ((n = zn[0]), n.blockedOn === null); )
    US(n), n.blockedOn === null && zn.shift();
}
var ri = bn.ReactCurrentBatchConfig,
  Qa = !0;
function VN(e, t, n, r) {
  var i = le,
    o = ri.transition;
  ri.transition = null;
  try {
    (le = 1), Rg(e, t, n, r);
  } finally {
    (le = i), (ri.transition = o);
  }
}
function UN(e, t, n, r) {
  var i = le,
    o = ri.transition;
  ri.transition = null;
  try {
    (le = 4), Rg(e, t, n, r);
  } finally {
    (le = i), (ri.transition = o);
  }
}
function Rg(e, t, n, r) {
  if (Qa) {
    var i = wp(e, t, n, r);
    if (i === null) Lu(e, t, r, Za, n), lm(e, r);
    else if (BN(i, e, t, n, r)) r.stopPropagation();
    else if ((lm(e, r), t & 4 && -1 < jN.indexOf(e))) {
      for (; i !== null; ) {
        var o = Uo(i);
        if ((o !== null && jS(o), (o = wp(e, t, n, r)), o === null && Lu(e, t, r, Za, n), o === i))
          break;
        i = o;
      }
      i !== null && r.stopPropagation();
    } else Lu(e, t, r, null, n);
  }
}
var Za = null;
function wp(e, t, n, r) {
  if (((Za = null), (e = bg(r)), (e = fr(e)), e !== null))
    if (((t = Tr(e)), t === null)) e = null;
    else if (((n = t.tag), n === 13)) {
      if (((e = PS(t)), e !== null)) return e;
      e = null;
    } else if (n === 3) {
      if (t.stateNode.current.memoizedState.isDehydrated)
        return t.tag === 3 ? t.stateNode.containerInfo : null;
      e = null;
    } else t !== e && (e = null);
  return (Za = e), null;
}
function GS(e) {
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
      switch (MN()) {
        case kg:
          return 1;
        case zS:
          return 4;
        case Ya:
        case PN:
          return 16;
        case $S:
          return 536870912;
        default:
          return 16;
      }
    default:
      return 16;
  }
}
var jn = null,
  Tg = null,
  Pa = null;
function WS() {
  if (Pa) return Pa;
  var e,
    t = Tg,
    n = t.length,
    r,
    i = "value" in jn ? jn.value : jn.textContent,
    o = i.length;
  for (e = 0; e < n && t[e] === i[e]; e++);
  var a = n - e;
  for (r = 1; r <= a && t[n - r] === i[o - r]; r++);
  return (Pa = i.slice(e, 1 < r ? 1 - r : void 0));
}
function qa(e) {
  var t = e.keyCode;
  return (
    "charCode" in e ? ((e = e.charCode), e === 0 && t === 13 && (e = 13)) : (e = t),
    e === 10 && (e = 13),
    32 <= e || e === 13 ? e : 0
  );
}
function la() {
  return !0;
}
function fm() {
  return !1;
}
function mt(e) {
  function t(n, r, i, o, a) {
    (this._reactName = n),
      (this._targetInst = i),
      (this.type = r),
      (this.nativeEvent = o),
      (this.target = a),
      (this.currentTarget = null);
    for (var s in e) e.hasOwnProperty(s) && ((n = e[s]), (this[s] = n ? n(o) : o[s]));
    return (
      (this.isDefaultPrevented = (
        o.defaultPrevented != null ? o.defaultPrevented : o.returnValue === !1
      )
        ? la
        : fm),
      (this.isPropagationStopped = fm),
      this
    );
  }
  return (
    _e(t.prototype, {
      preventDefault: function () {
        this.defaultPrevented = !0;
        var n = this.nativeEvent;
        n &&
          (n.preventDefault
            ? n.preventDefault()
            : typeof n.returnValue != "unknown" && (n.returnValue = !1),
          (this.isDefaultPrevented = la));
      },
      stopPropagation: function () {
        var n = this.nativeEvent;
        n &&
          (n.stopPropagation
            ? n.stopPropagation()
            : typeof n.cancelBubble != "unknown" && (n.cancelBubble = !0),
          (this.isPropagationStopped = la));
      },
      persist: function () {},
      isPersistent: la,
    }),
    t
  );
}
var Si = {
    eventPhase: 0,
    bubbles: 0,
    cancelable: 0,
    timeStamp: function (e) {
      return e.timeStamp || Date.now();
    },
    defaultPrevented: 0,
    isTrusted: 0,
  },
  Ig = mt(Si),
  Vo = _e({}, Si, { view: 0, detail: 0 }),
  GN = mt(Vo),
  Nu,
  Ru,
  Li,
  As = _e({}, Vo, {
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
    getModifierState: Ag,
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
        : (e !== Li &&
            (Li && e.type === "mousemove"
              ? ((Nu = e.screenX - Li.screenX), (Ru = e.screenY - Li.screenY))
              : (Ru = Nu = 0),
            (Li = e)),
          Nu);
    },
    movementY: function (e) {
      return "movementY" in e ? e.movementY : Ru;
    },
  }),
  dm = mt(As),
  WN = _e({}, As, { dataTransfer: 0 }),
  KN = mt(WN),
  YN = _e({}, Vo, { relatedTarget: 0 }),
  Tu = mt(YN),
  XN = _e({}, Si, { animationName: 0, elapsedTime: 0, pseudoElement: 0 }),
  QN = mt(XN),
  ZN = _e({}, Si, {
    clipboardData: function (e) {
      return "clipboardData" in e ? e.clipboardData : window.clipboardData;
    },
  }),
  JN = mt(ZN),
  eR = _e({}, Si, { data: 0 }),
  hm = mt(eR),
  tR = {
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
  nR = {
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
  rR = { Alt: "altKey", Control: "ctrlKey", Meta: "metaKey", Shift: "shiftKey" };
function iR(e) {
  var t = this.nativeEvent;
  return t.getModifierState ? t.getModifierState(e) : (e = rR[e]) ? !!t[e] : !1;
}
function Ag() {
  return iR;
}
var oR = _e({}, Vo, {
    key: function (e) {
      if (e.key) {
        var t = tR[e.key] || e.key;
        if (t !== "Unidentified") return t;
      }
      return e.type === "keypress"
        ? ((e = qa(e)), e === 13 ? "Enter" : String.fromCharCode(e))
        : e.type === "keydown" || e.type === "keyup"
        ? nR[e.keyCode] || "Unidentified"
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
    getModifierState: Ag,
    charCode: function (e) {
      return e.type === "keypress" ? qa(e) : 0;
    },
    keyCode: function (e) {
      return e.type === "keydown" || e.type === "keyup" ? e.keyCode : 0;
    },
    which: function (e) {
      return e.type === "keypress"
        ? qa(e)
        : e.type === "keydown" || e.type === "keyup"
        ? e.keyCode
        : 0;
    },
  }),
  aR = mt(oR),
  sR = _e({}, As, {
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
  pm = mt(sR),
  uR = _e({}, Vo, {
    touches: 0,
    targetTouches: 0,
    changedTouches: 0,
    altKey: 0,
    metaKey: 0,
    ctrlKey: 0,
    shiftKey: 0,
    getModifierState: Ag,
  }),
  lR = mt(uR),
  cR = _e({}, Si, { propertyName: 0, elapsedTime: 0, pseudoElement: 0 }),
  fR = mt(cR),
  dR = _e({}, As, {
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
  hR = mt(dR),
  pR = [9, 13, 27, 32],
  Mg = mn && "CompositionEvent" in window,
  uo = null;
mn && "documentMode" in document && (uo = document.documentMode);
var gR = mn && "TextEvent" in window && !uo,
  KS = mn && (!Mg || (uo && 8 < uo && 11 >= uo)),
  gm = " ",
  vm = !1;
function YS(e, t) {
  switch (e) {
    case "keyup":
      return pR.indexOf(t.keyCode) !== -1;
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
function XS(e) {
  return (e = e.detail), typeof e == "object" && "data" in e ? e.data : null;
}
var Hr = !1;
function vR(e, t) {
  switch (e) {
    case "compositionend":
      return XS(t);
    case "keypress":
      return t.which !== 32 ? null : ((vm = !0), gm);
    case "textInput":
      return (e = t.data), e === gm && vm ? null : e;
    default:
      return null;
  }
}
function mR(e, t) {
  if (Hr)
    return e === "compositionend" || (!Mg && YS(e, t))
      ? ((e = WS()), (Pa = Tg = jn = null), (Hr = !1), e)
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
      return KS && t.locale !== "ko" ? null : t.data;
    default:
      return null;
  }
}
var yR = {
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
function mm(e) {
  var t = e && e.nodeName && e.nodeName.toLowerCase();
  return t === "input" ? !!yR[e.type] : t === "textarea";
}
function QS(e, t, n, r) {
  RS(r),
    (t = Ja(t, "onChange")),
    0 < t.length &&
      ((n = new Ig("onChange", "change", null, n, r)), e.push({ event: n, listeners: t }));
}
var lo = null,
  So = null;
function _R(e) {
  uE(e, 0);
}
function Ms(e) {
  var t = Gr(e);
  if (xS(t)) return e;
}
function wR(e, t) {
  if (e === "change") return t;
}
var ZS = !1;
if (mn) {
  var Iu;
  if (mn) {
    var Au = "oninput" in document;
    if (!Au) {
      var ym = document.createElement("div");
      ym.setAttribute("oninput", "return;"), (Au = typeof ym.oninput == "function");
    }
    Iu = Au;
  } else Iu = !1;
  ZS = Iu && (!document.documentMode || 9 < document.documentMode);
}
function _m() {
  lo && (lo.detachEvent("onpropertychange", JS), (So = lo = null));
}
function JS(e) {
  if (e.propertyName === "value" && Ms(So)) {
    var t = [];
    QS(t, So, e, bg(e)), MS(_R, t);
  }
}
function xR(e, t, n) {
  e === "focusin"
    ? (_m(), (lo = t), (So = n), lo.attachEvent("onpropertychange", JS))
    : e === "focusout" && _m();
}
function SR(e) {
  if (e === "selectionchange" || e === "keyup" || e === "keydown") return Ms(So);
}
function ER(e, t) {
  if (e === "click") return Ms(t);
}
function bR(e, t) {
  if (e === "input" || e === "change") return Ms(t);
}
function kR(e, t) {
  return (e === t && (e !== 0 || 1 / e === 1 / t)) || (e !== e && t !== t);
}
var Dt = typeof Object.is == "function" ? Object.is : kR;
function Eo(e, t) {
  if (Dt(e, t)) return !0;
  if (typeof e != "object" || e === null || typeof t != "object" || t === null) return !1;
  var n = Object.keys(e),
    r = Object.keys(t);
  if (n.length !== r.length) return !1;
  for (r = 0; r < n.length; r++) {
    var i = n[r];
    if (!np.call(t, i) || !Dt(e[i], t[i])) return !1;
  }
  return !0;
}
function wm(e) {
  for (; e && e.firstChild; ) e = e.firstChild;
  return e;
}
function xm(e, t) {
  var n = wm(e);
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
    n = wm(n);
  }
}
function eE(e, t) {
  return e && t
    ? e === t
      ? !0
      : e && e.nodeType === 3
      ? !1
      : t && t.nodeType === 3
      ? eE(e, t.parentNode)
      : "contains" in e
      ? e.contains(t)
      : e.compareDocumentPosition
      ? !!(e.compareDocumentPosition(t) & 16)
      : !1
    : !1;
}
function tE() {
  for (var e = window, t = Ga(); t instanceof e.HTMLIFrameElement; ) {
    try {
      var n = typeof t.contentWindow.location.href == "string";
    } catch {
      n = !1;
    }
    if (n) e = t.contentWindow;
    else break;
    t = Ga(e.document);
  }
  return t;
}
function Pg(e) {
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
function CR(e) {
  var t = tE(),
    n = e.focusedElem,
    r = e.selectionRange;
  if (t !== n && n && n.ownerDocument && eE(n.ownerDocument.documentElement, n)) {
    if (r !== null && Pg(n)) {
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
          (i = xm(n, o));
        var a = xm(n, r);
        i &&
          a &&
          (e.rangeCount !== 1 ||
            e.anchorNode !== i.node ||
            e.anchorOffset !== i.offset ||
            e.focusNode !== a.node ||
            e.focusOffset !== a.offset) &&
          ((t = t.createRange()),
          t.setStart(i.node, i.offset),
          e.removeAllRanges(),
          o > r
            ? (e.addRange(t), e.extend(a.node, a.offset))
            : (t.setEnd(a.node, a.offset), e.addRange(t)));
      }
    }
    for (t = [], e = n; (e = e.parentNode); )
      e.nodeType === 1 && t.push({ element: e, left: e.scrollLeft, top: e.scrollTop });
    for (typeof n.focus == "function" && n.focus(), n = 0; n < t.length; n++)
      (e = t[n]), (e.element.scrollLeft = e.left), (e.element.scrollTop = e.top);
  }
}
var NR = mn && "documentMode" in document && 11 >= document.documentMode,
  Vr = null,
  xp = null,
  co = null,
  Sp = !1;
function Sm(e, t, n) {
  var r = n.window === n ? n.document : n.nodeType === 9 ? n : n.ownerDocument;
  Sp ||
    Vr == null ||
    Vr !== Ga(r) ||
    ((r = Vr),
    "selectionStart" in r && Pg(r)
      ? (r = { start: r.selectionStart, end: r.selectionEnd })
      : ((r = ((r.ownerDocument && r.ownerDocument.defaultView) || window).getSelection()),
        (r = {
          anchorNode: r.anchorNode,
          anchorOffset: r.anchorOffset,
          focusNode: r.focusNode,
          focusOffset: r.focusOffset,
        })),
    (co && Eo(co, r)) ||
      ((co = r),
      (r = Ja(xp, "onSelect")),
      0 < r.length &&
        ((t = new Ig("onSelect", "select", null, t, n)),
        e.push({ event: t, listeners: r }),
        (t.target = Vr))));
}
function ca(e, t) {
  var n = {};
  return (
    (n[e.toLowerCase()] = t.toLowerCase()),
    (n["Webkit" + e] = "webkit" + t),
    (n["Moz" + e] = "moz" + t),
    n
  );
}
var Ur = {
    animationend: ca("Animation", "AnimationEnd"),
    animationiteration: ca("Animation", "AnimationIteration"),
    animationstart: ca("Animation", "AnimationStart"),
    transitionend: ca("Transition", "TransitionEnd"),
  },
  Mu = {},
  nE = {};
mn &&
  ((nE = document.createElement("div").style),
  "AnimationEvent" in window ||
    (delete Ur.animationend.animation,
    delete Ur.animationiteration.animation,
    delete Ur.animationstart.animation),
  "TransitionEvent" in window || delete Ur.transitionend.transition);
function Ps(e) {
  if (Mu[e]) return Mu[e];
  if (!Ur[e]) return e;
  var t = Ur[e],
    n;
  for (n in t) if (t.hasOwnProperty(n) && n in nE) return (Mu[e] = t[n]);
  return e;
}
var rE = Ps("animationend"),
  iE = Ps("animationiteration"),
  oE = Ps("animationstart"),
  aE = Ps("transitionend"),
  sE = new Map(),
  Em = "abort auxClick cancel canPlay canPlayThrough click close contextMenu copy cut drag dragEnd dragEnter dragExit dragLeave dragOver dragStart drop durationChange emptied encrypted ended error gotPointerCapture input invalid keyDown keyPress keyUp load loadedData loadedMetadata loadStart lostPointerCapture mouseDown mouseMove mouseOut mouseOver mouseUp paste pause play playing pointerCancel pointerDown pointerMove pointerOut pointerOver pointerUp progress rateChange reset resize seeked seeking stalled submit suspend timeUpdate touchCancel touchEnd touchStart volumeChange scroll toggle touchMove waiting wheel".split(
    " "
  );
function nr(e, t) {
  sE.set(e, t), Rr(t, [e]);
}
for (var Pu = 0; Pu < Em.length; Pu++) {
  var qu = Em[Pu],
    RR = qu.toLowerCase(),
    TR = qu[0].toUpperCase() + qu.slice(1);
  nr(RR, "on" + TR);
}
nr(rE, "onAnimationEnd");
nr(iE, "onAnimationIteration");
nr(oE, "onAnimationStart");
nr("dblclick", "onDoubleClick");
nr("focusin", "onFocus");
nr("focusout", "onBlur");
nr(aE, "onTransitionEnd");
ci("onMouseEnter", ["mouseout", "mouseover"]);
ci("onMouseLeave", ["mouseout", "mouseover"]);
ci("onPointerEnter", ["pointerout", "pointerover"]);
ci("onPointerLeave", ["pointerout", "pointerover"]);
Rr("onChange", "change click focusin focusout input keydown keyup selectionchange".split(" "));
Rr(
  "onSelect",
  "focusout contextmenu dragend focusin keydown keyup mousedown mouseup selectionchange".split(" ")
);
Rr("onBeforeInput", ["compositionend", "keypress", "textInput", "paste"]);
Rr("onCompositionEnd", "compositionend focusout keydown keypress keyup mousedown".split(" "));
Rr("onCompositionStart", "compositionstart focusout keydown keypress keyup mousedown".split(" "));
Rr("onCompositionUpdate", "compositionupdate focusout keydown keypress keyup mousedown".split(" "));
var Xi = "abort canplay canplaythrough durationchange emptied encrypted ended error loadeddata loadedmetadata loadstart pause play playing progress ratechange resize seeked seeking stalled suspend timeupdate volumechange waiting".split(
    " "
  ),
  IR = new Set("cancel close invalid load scroll toggle".split(" ").concat(Xi));
function bm(e, t, n) {
  var r = e.type || "unknown-event";
  (e.currentTarget = n), RN(r, t, void 0, e), (e.currentTarget = null);
}
function uE(e, t) {
  t = (t & 4) !== 0;
  for (var n = 0; n < e.length; n++) {
    var r = e[n],
      i = r.event;
    r = r.listeners;
    e: {
      var o = void 0;
      if (t)
        for (var a = r.length - 1; 0 <= a; a--) {
          var s = r[a],
            u = s.instance,
            l = s.currentTarget;
          if (((s = s.listener), u !== o && i.isPropagationStopped())) break e;
          bm(i, s, l), (o = u);
        }
      else
        for (a = 0; a < r.length; a++) {
          if (
            ((s = r[a]),
            (u = s.instance),
            (l = s.currentTarget),
            (s = s.listener),
            u !== o && i.isPropagationStopped())
          )
            break e;
          bm(i, s, l), (o = u);
        }
    }
  }
  if (Ka) throw ((e = mp), (Ka = !1), (mp = null), e);
}
function he(e, t) {
  var n = t[Np];
  n === void 0 && (n = t[Np] = new Set());
  var r = e + "__bubble";
  n.has(r) || (lE(t, e, 2, !1), n.add(r));
}
function Ou(e, t, n) {
  var r = 0;
  t && (r |= 4), lE(n, e, r, t);
}
var fa = "_reactListening" + Math.random().toString(36).slice(2);
function bo(e) {
  if (!e[fa]) {
    (e[fa] = !0),
      vS.forEach(function (n) {
        n !== "selectionchange" && (IR.has(n) || Ou(n, !1, e), Ou(n, !0, e));
      });
    var t = e.nodeType === 9 ? e : e.ownerDocument;
    t === null || t[fa] || ((t[fa] = !0), Ou("selectionchange", !1, t));
  }
}
function lE(e, t, n, r) {
  switch (GS(t)) {
    case 1:
      var i = VN;
      break;
    case 4:
      i = UN;
      break;
    default:
      i = Rg;
  }
  (n = i.bind(null, t, n, e)),
    (i = void 0),
    !vp || (t !== "touchstart" && t !== "touchmove" && t !== "wheel") || (i = !0),
    r
      ? i !== void 0
        ? e.addEventListener(t, n, { capture: !0, passive: i })
        : e.addEventListener(t, n, !0)
      : i !== void 0
      ? e.addEventListener(t, n, { passive: i })
      : e.addEventListener(t, n, !1);
}
function Lu(e, t, n, r, i) {
  var o = r;
  if (!(t & 1) && !(t & 2) && r !== null)
    e: for (;;) {
      if (r === null) return;
      var a = r.tag;
      if (a === 3 || a === 4) {
        var s = r.stateNode.containerInfo;
        if (s === i || (s.nodeType === 8 && s.parentNode === i)) break;
        if (a === 4)
          for (a = r.return; a !== null; ) {
            var u = a.tag;
            if (
              (u === 3 || u === 4) &&
              ((u = a.stateNode.containerInfo), u === i || (u.nodeType === 8 && u.parentNode === i))
            )
              return;
            a = a.return;
          }
        for (; s !== null; ) {
          if (((a = fr(s)), a === null)) return;
          if (((u = a.tag), u === 5 || u === 6)) {
            r = o = a;
            continue e;
          }
          s = s.parentNode;
        }
      }
      r = r.return;
    }
  MS(function () {
    var l = o,
      c = bg(n),
      f = [];
    e: {
      var d = sE.get(e);
      if (d !== void 0) {
        var h = Ig,
          m = e;
        switch (e) {
          case "keypress":
            if (qa(n) === 0) break e;
          case "keydown":
          case "keyup":
            h = aR;
            break;
          case "focusin":
            (m = "focus"), (h = Tu);
            break;
          case "focusout":
            (m = "blur"), (h = Tu);
            break;
          case "beforeblur":
          case "afterblur":
            h = Tu;
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
            h = dm;
            break;
          case "drag":
          case "dragend":
          case "dragenter":
          case "dragexit":
          case "dragleave":
          case "dragover":
          case "dragstart":
          case "drop":
            h = KN;
            break;
          case "touchcancel":
          case "touchend":
          case "touchmove":
          case "touchstart":
            h = lR;
            break;
          case rE:
          case iE:
          case oE:
            h = QN;
            break;
          case aE:
            h = fR;
            break;
          case "scroll":
            h = GN;
            break;
          case "wheel":
            h = hR;
            break;
          case "copy":
          case "cut":
          case "paste":
            h = JN;
            break;
          case "gotpointercapture":
          case "lostpointercapture":
          case "pointercancel":
          case "pointerdown":
          case "pointermove":
          case "pointerout":
          case "pointerover":
          case "pointerup":
            h = pm;
        }
        var v = (t & 4) !== 0,
          w = !v && e === "scroll",
          p = v ? (d !== null ? d + "Capture" : null) : d;
        v = [];
        for (var g = l, y; g !== null; ) {
          y = g;
          var _ = y.stateNode;
          if (
            (y.tag === 5 &&
              _ !== null &&
              ((y = _), p !== null && ((_ = yo(g, p)), _ != null && v.push(ko(g, _, y)))),
            w)
          )
            break;
          g = g.return;
        }
        0 < v.length && ((d = new h(d, m, null, n, c)), f.push({ event: d, listeners: v }));
      }
    }
    if (!(t & 7)) {
      e: {
        if (
          ((d = e === "mouseover" || e === "pointerover"),
          (h = e === "mouseout" || e === "pointerout"),
          d && n !== pp && (m = n.relatedTarget || n.fromElement) && (fr(m) || m[yn]))
        )
          break e;
        if (
          (h || d) &&
          ((d =
            c.window === c ? c : (d = c.ownerDocument) ? d.defaultView || d.parentWindow : window),
          h
            ? ((m = n.relatedTarget || n.toElement),
              (h = l),
              (m = m ? fr(m) : null),
              m !== null && ((w = Tr(m)), m !== w || (m.tag !== 5 && m.tag !== 6)) && (m = null))
            : ((h = null), (m = l)),
          h !== m)
        ) {
          if (
            ((v = dm),
            (_ = "onMouseLeave"),
            (p = "onMouseEnter"),
            (g = "mouse"),
            (e === "pointerout" || e === "pointerover") &&
              ((v = pm), (_ = "onPointerLeave"), (p = "onPointerEnter"), (g = "pointer")),
            (w = h == null ? d : Gr(h)),
            (y = m == null ? d : Gr(m)),
            (d = new v(_, g + "leave", h, n, c)),
            (d.target = w),
            (d.relatedTarget = y),
            (_ = null),
            fr(c) === l &&
              ((v = new v(p, g + "enter", m, n, c)),
              (v.target = y),
              (v.relatedTarget = w),
              (_ = v)),
            (w = _),
            h && m)
          )
            t: {
              for (v = h, p = m, g = 0, y = v; y; y = Or(y)) g++;
              for (y = 0, _ = p; _; _ = Or(_)) y++;
              for (; 0 < g - y; ) (v = Or(v)), g--;
              for (; 0 < y - g; ) (p = Or(p)), y--;
              for (; g--; ) {
                if (v === p || (p !== null && v === p.alternate)) break t;
                (v = Or(v)), (p = Or(p));
              }
              v = null;
            }
          else v = null;
          h !== null && km(f, d, h, v, !1), m !== null && w !== null && km(f, w, m, v, !0);
        }
      }
      e: {
        if (
          ((d = l ? Gr(l) : window),
          (h = d.nodeName && d.nodeName.toLowerCase()),
          h === "select" || (h === "input" && d.type === "file"))
        )
          var S = wR;
        else if (mm(d))
          if (ZS) S = bR;
          else {
            S = SR;
            var E = xR;
          }
        else
          (h = d.nodeName) &&
            h.toLowerCase() === "input" &&
            (d.type === "checkbox" || d.type === "radio") &&
            (S = ER);
        if (S && (S = S(e, l))) {
          QS(f, S, n, c);
          break e;
        }
        E && E(e, d, l),
          e === "focusout" &&
            (E = d._wrapperState) &&
            E.controlled &&
            d.type === "number" &&
            lp(d, "number", d.value);
      }
      switch (((E = l ? Gr(l) : window), e)) {
        case "focusin":
          (mm(E) || E.contentEditable === "true") && ((Vr = E), (xp = l), (co = null));
          break;
        case "focusout":
          co = xp = Vr = null;
          break;
        case "mousedown":
          Sp = !0;
          break;
        case "contextmenu":
        case "mouseup":
        case "dragend":
          (Sp = !1), Sm(f, n, c);
          break;
        case "selectionchange":
          if (NR) break;
        case "keydown":
        case "keyup":
          Sm(f, n, c);
      }
      var k;
      if (Mg)
        e: {
          switch (e) {
            case "compositionstart":
              var C = "onCompositionStart";
              break e;
            case "compositionend":
              C = "onCompositionEnd";
              break e;
            case "compositionupdate":
              C = "onCompositionUpdate";
              break e;
          }
          C = void 0;
        }
      else
        Hr
          ? YS(e, n) && (C = "onCompositionEnd")
          : e === "keydown" && n.keyCode === 229 && (C = "onCompositionStart");
      C &&
        (KS &&
          n.locale !== "ko" &&
          (Hr || C !== "onCompositionStart"
            ? C === "onCompositionEnd" && Hr && (k = WS())
            : ((jn = c), (Tg = "value" in jn ? jn.value : jn.textContent), (Hr = !0))),
        (E = Ja(l, C)),
        0 < E.length &&
          ((C = new hm(C, e, null, n, c)),
          f.push({ event: C, listeners: E }),
          k ? (C.data = k) : ((k = XS(n)), k !== null && (C.data = k)))),
        (k = gR ? vR(e, n) : mR(e, n)) &&
          ((l = Ja(l, "onBeforeInput")),
          0 < l.length &&
            ((c = new hm("onBeforeInput", "beforeinput", null, n, c)),
            f.push({ event: c, listeners: l }),
            (c.data = k)));
    }
    uE(f, t);
  });
}
function ko(e, t, n) {
  return { instance: e, listener: t, currentTarget: n };
}
function Ja(e, t) {
  for (var n = t + "Capture", r = []; e !== null; ) {
    var i = e,
      o = i.stateNode;
    i.tag === 5 &&
      o !== null &&
      ((i = o),
      (o = yo(e, n)),
      o != null && r.unshift(ko(e, o, i)),
      (o = yo(e, t)),
      o != null && r.push(ko(e, o, i))),
      (e = e.return);
  }
  return r;
}
function Or(e) {
  if (e === null) return null;
  do e = e.return;
  while (e && e.tag !== 5);
  return e || null;
}
function km(e, t, n, r, i) {
  for (var o = t._reactName, a = []; n !== null && n !== r; ) {
    var s = n,
      u = s.alternate,
      l = s.stateNode;
    if (u !== null && u === r) break;
    s.tag === 5 &&
      l !== null &&
      ((s = l),
      i
        ? ((u = yo(n, o)), u != null && a.unshift(ko(n, u, s)))
        : i || ((u = yo(n, o)), u != null && a.push(ko(n, u, s)))),
      (n = n.return);
  }
  a.length !== 0 && e.push({ event: t, listeners: a });
}
var AR = /\r\n?/g,
  MR = /\u0000|\uFFFD/g;
function Cm(e) {
  return (typeof e == "string" ? e : "" + e)
    .replace(
      AR,
      `
`
    )
    .replace(MR, "");
}
function da(e, t, n) {
  if (((t = Cm(t)), Cm(e) !== t && n)) throw Error(j(425));
}
function es() {}
var Ep = null,
  bp = null;
function kp(e, t) {
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
var Cp = typeof setTimeout == "function" ? setTimeout : void 0,
  PR = typeof clearTimeout == "function" ? clearTimeout : void 0,
  Nm = typeof Promise == "function" ? Promise : void 0,
  qR =
    typeof queueMicrotask == "function"
      ? queueMicrotask
      : typeof Nm < "u"
      ? function (e) {
          return Nm.resolve(null).then(e).catch(OR);
        }
      : Cp;
function OR(e) {
  setTimeout(function () {
    throw e;
  });
}
function zu(e, t) {
  var n = t,
    r = 0;
  do {
    var i = n.nextSibling;
    if ((e.removeChild(n), i && i.nodeType === 8))
      if (((n = i.data), n === "/$")) {
        if (r === 0) {
          e.removeChild(i), xo(t);
          return;
        }
        r--;
      } else (n !== "$" && n !== "$?" && n !== "$!") || r++;
    n = i;
  } while (n);
  xo(t);
}
function Gn(e) {
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
function Rm(e) {
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
var Ei = Math.random().toString(36).slice(2),
  Kt = "__reactFiber$" + Ei,
  Co = "__reactProps$" + Ei,
  yn = "__reactContainer$" + Ei,
  Np = "__reactEvents$" + Ei,
  LR = "__reactListeners$" + Ei,
  zR = "__reactHandles$" + Ei;
function fr(e) {
  var t = e[Kt];
  if (t) return t;
  for (var n = e.parentNode; n; ) {
    if ((t = n[yn] || n[Kt])) {
      if (((n = t.alternate), t.child !== null || (n !== null && n.child !== null)))
        for (e = Rm(e); e !== null; ) {
          if ((n = e[Kt])) return n;
          e = Rm(e);
        }
      return t;
    }
    (e = n), (n = e.parentNode);
  }
  return null;
}
function Uo(e) {
  return (
    (e = e[Kt] || e[yn]),
    !e || (e.tag !== 5 && e.tag !== 6 && e.tag !== 13 && e.tag !== 3) ? null : e
  );
}
function Gr(e) {
  if (e.tag === 5 || e.tag === 6) return e.stateNode;
  throw Error(j(33));
}
function qs(e) {
  return e[Co] || null;
}
var Rp = [],
  Wr = -1;
function rr(e) {
  return { current: e };
}
function pe(e) {
  0 > Wr || ((e.current = Rp[Wr]), (Rp[Wr] = null), Wr--);
}
function ce(e, t) {
  Wr++, (Rp[Wr] = e.current), (e.current = t);
}
var er = {},
  We = rr(er),
  ot = rr(!1),
  xr = er;
function fi(e, t) {
  var n = e.type.contextTypes;
  if (!n) return er;
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
function at(e) {
  return (e = e.childContextTypes), e != null;
}
function ts() {
  pe(ot), pe(We);
}
function Tm(e, t, n) {
  if (We.current !== er) throw Error(j(168));
  ce(We, t), ce(ot, n);
}
function cE(e, t, n) {
  var r = e.stateNode;
  if (((t = t.childContextTypes), typeof r.getChildContext != "function")) return n;
  r = r.getChildContext();
  for (var i in r) if (!(i in t)) throw Error(j(108, xN(e) || "Unknown", i));
  return _e({}, n, r);
}
function ns(e) {
  return (
    (e = ((e = e.stateNode) && e.__reactInternalMemoizedMergedChildContext) || er),
    (xr = We.current),
    ce(We, e),
    ce(ot, ot.current),
    !0
  );
}
function Im(e, t, n) {
  var r = e.stateNode;
  if (!r) throw Error(j(169));
  n
    ? ((e = cE(e, t, xr)),
      (r.__reactInternalMemoizedMergedChildContext = e),
      pe(ot),
      pe(We),
      ce(We, e))
    : pe(ot),
    ce(ot, n);
}
var ln = null,
  Os = !1,
  $u = !1;
function fE(e) {
  ln === null ? (ln = [e]) : ln.push(e);
}
function $R(e) {
  (Os = !0), fE(e);
}
function ir() {
  if (!$u && ln !== null) {
    $u = !0;
    var e = 0,
      t = le;
    try {
      var n = ln;
      for (le = 1; e < n.length; e++) {
        var r = n[e];
        do r = r(!0);
        while (r !== null);
      }
      (ln = null), (Os = !1);
    } catch (i) {
      throw (ln !== null && (ln = ln.slice(e + 1)), LS(kg, ir), i);
    } finally {
      (le = t), ($u = !1);
    }
  }
  return null;
}
var Kr = [],
  Yr = 0,
  rs = null,
  is = 0,
  yt = [],
  _t = 0,
  Sr = null,
  cn = 1,
  fn = "";
function ur(e, t) {
  (Kr[Yr++] = is), (Kr[Yr++] = rs), (rs = e), (is = t);
}
function dE(e, t, n) {
  (yt[_t++] = cn), (yt[_t++] = fn), (yt[_t++] = Sr), (Sr = e);
  var r = cn;
  e = fn;
  var i = 32 - Lt(r) - 1;
  (r &= ~(1 << i)), (n += 1);
  var o = 32 - Lt(t) + i;
  if (30 < o) {
    var a = i - (i % 5);
    (o = (r & ((1 << a) - 1)).toString(32)),
      (r >>= a),
      (i -= a),
      (cn = (1 << (32 - Lt(t) + i)) | (n << i) | r),
      (fn = o + e);
  } else (cn = (1 << o) | (n << i) | r), (fn = e);
}
function qg(e) {
  e.return !== null && (ur(e, 1), dE(e, 1, 0));
}
function Og(e) {
  for (; e === rs; ) (rs = Kr[--Yr]), (Kr[Yr] = null), (is = Kr[--Yr]), (Kr[Yr] = null);
  for (; e === Sr; )
    (Sr = yt[--_t]),
      (yt[_t] = null),
      (fn = yt[--_t]),
      (yt[_t] = null),
      (cn = yt[--_t]),
      (yt[_t] = null);
}
var ht = null,
  dt = null,
  ge = !1,
  qt = null;
function hE(e, t) {
  var n = xt(5, null, null, 0);
  (n.elementType = "DELETED"),
    (n.stateNode = t),
    (n.return = e),
    (t = e.deletions),
    t === null ? ((e.deletions = [n]), (e.flags |= 16)) : t.push(n);
}
function Am(e, t) {
  switch (e.tag) {
    case 5:
      var n = e.type;
      return (
        (t = t.nodeType !== 1 || n.toLowerCase() !== t.nodeName.toLowerCase() ? null : t),
        t !== null ? ((e.stateNode = t), (ht = e), (dt = Gn(t.firstChild)), !0) : !1
      );
    case 6:
      return (
        (t = e.pendingProps === "" || t.nodeType !== 3 ? null : t),
        t !== null ? ((e.stateNode = t), (ht = e), (dt = null), !0) : !1
      );
    case 13:
      return (
        (t = t.nodeType !== 8 ? null : t),
        t !== null
          ? ((n = Sr !== null ? { id: cn, overflow: fn } : null),
            (e.memoizedState = { dehydrated: t, treeContext: n, retryLane: 1073741824 }),
            (n = xt(18, null, null, 0)),
            (n.stateNode = t),
            (n.return = e),
            (e.child = n),
            (ht = e),
            (dt = null),
            !0)
          : !1
      );
    default:
      return !1;
  }
}
function Tp(e) {
  return (e.mode & 1) !== 0 && (e.flags & 128) === 0;
}
function Ip(e) {
  if (ge) {
    var t = dt;
    if (t) {
      var n = t;
      if (!Am(e, t)) {
        if (Tp(e)) throw Error(j(418));
        t = Gn(n.nextSibling);
        var r = ht;
        t && Am(e, t) ? hE(r, n) : ((e.flags = (e.flags & -4097) | 2), (ge = !1), (ht = e));
      }
    } else {
      if (Tp(e)) throw Error(j(418));
      (e.flags = (e.flags & -4097) | 2), (ge = !1), (ht = e);
    }
  }
}
function Mm(e) {
  for (e = e.return; e !== null && e.tag !== 5 && e.tag !== 3 && e.tag !== 13; ) e = e.return;
  ht = e;
}
function ha(e) {
  if (e !== ht) return !1;
  if (!ge) return Mm(e), (ge = !0), !1;
  var t;
  if (
    ((t = e.tag !== 3) &&
      !(t = e.tag !== 5) &&
      ((t = e.type), (t = t !== "head" && t !== "body" && !kp(e.type, e.memoizedProps))),
    t && (t = dt))
  ) {
    if (Tp(e)) throw (pE(), Error(j(418)));
    for (; t; ) hE(e, t), (t = Gn(t.nextSibling));
  }
  if ((Mm(e), e.tag === 13)) {
    if (((e = e.memoizedState), (e = e !== null ? e.dehydrated : null), !e)) throw Error(j(317));
    e: {
      for (e = e.nextSibling, t = 0; e; ) {
        if (e.nodeType === 8) {
          var n = e.data;
          if (n === "/$") {
            if (t === 0) {
              dt = Gn(e.nextSibling);
              break e;
            }
            t--;
          } else (n !== "$" && n !== "$!" && n !== "$?") || t++;
        }
        e = e.nextSibling;
      }
      dt = null;
    }
  } else dt = ht ? Gn(e.stateNode.nextSibling) : null;
  return !0;
}
function pE() {
  for (var e = dt; e; ) e = Gn(e.nextSibling);
}
function di() {
  (dt = ht = null), (ge = !1);
}
function Lg(e) {
  qt === null ? (qt = [e]) : qt.push(e);
}
var DR = bn.ReactCurrentBatchConfig;
function zi(e, t, n) {
  if (((e = n.ref), e !== null && typeof e != "function" && typeof e != "object")) {
    if (n._owner) {
      if (((n = n._owner), n)) {
        if (n.tag !== 1) throw Error(j(309));
        var r = n.stateNode;
      }
      if (!r) throw Error(j(147, e));
      var i = r,
        o = "" + e;
      return t !== null && t.ref !== null && typeof t.ref == "function" && t.ref._stringRef === o
        ? t.ref
        : ((t = function (a) {
            var s = i.refs;
            a === null ? delete s[o] : (s[o] = a);
          }),
          (t._stringRef = o),
          t);
    }
    if (typeof e != "string") throw Error(j(284));
    if (!n._owner) throw Error(j(290, e));
  }
  return e;
}
function pa(e, t) {
  throw (
    ((e = Object.prototype.toString.call(t)),
    Error(
      j(31, e === "[object Object]" ? "object with keys {" + Object.keys(t).join(", ") + "}" : e)
    ))
  );
}
function Pm(e) {
  var t = e._init;
  return t(e._payload);
}
function gE(e) {
  function t(p, g) {
    if (e) {
      var y = p.deletions;
      y === null ? ((p.deletions = [g]), (p.flags |= 16)) : y.push(g);
    }
  }
  function n(p, g) {
    if (!e) return null;
    for (; g !== null; ) t(p, g), (g = g.sibling);
    return null;
  }
  function r(p, g) {
    for (p = new Map(); g !== null; )
      g.key !== null ? p.set(g.key, g) : p.set(g.index, g), (g = g.sibling);
    return p;
  }
  function i(p, g) {
    return (p = Xn(p, g)), (p.index = 0), (p.sibling = null), p;
  }
  function o(p, g, y) {
    return (
      (p.index = y),
      e
        ? ((y = p.alternate),
          y !== null ? ((y = y.index), y < g ? ((p.flags |= 2), g) : y) : ((p.flags |= 2), g))
        : ((p.flags |= 1048576), g)
    );
  }
  function a(p) {
    return e && p.alternate === null && (p.flags |= 2), p;
  }
  function s(p, g, y, _) {
    return g === null || g.tag !== 6
      ? ((g = Uu(y, p.mode, _)), (g.return = p), g)
      : ((g = i(g, y)), (g.return = p), g);
  }
  function u(p, g, y, _) {
    var S = y.type;
    return S === Br
      ? c(p, g, y.props.children, _, y.key)
      : g !== null &&
        (g.elementType === S ||
          (typeof S == "object" && S !== null && S.$$typeof === Pn && Pm(S) === g.type))
      ? ((_ = i(g, y.props)), (_.ref = zi(p, g, y)), (_.return = p), _)
      : ((_ = ja(y.type, y.key, y.props, null, p.mode, _)),
        (_.ref = zi(p, g, y)),
        (_.return = p),
        _);
  }
  function l(p, g, y, _) {
    return g === null ||
      g.tag !== 4 ||
      g.stateNode.containerInfo !== y.containerInfo ||
      g.stateNode.implementation !== y.implementation
      ? ((g = Gu(y, p.mode, _)), (g.return = p), g)
      : ((g = i(g, y.children || [])), (g.return = p), g);
  }
  function c(p, g, y, _, S) {
    return g === null || g.tag !== 7
      ? ((g = yr(y, p.mode, _, S)), (g.return = p), g)
      : ((g = i(g, y)), (g.return = p), g);
  }
  function f(p, g, y) {
    if ((typeof g == "string" && g !== "") || typeof g == "number")
      return (g = Uu("" + g, p.mode, y)), (g.return = p), g;
    if (typeof g == "object" && g !== null) {
      switch (g.$$typeof) {
        case ra:
          return (
            (y = ja(g.type, g.key, g.props, null, p.mode, y)),
            (y.ref = zi(p, null, g)),
            (y.return = p),
            y
          );
        case jr:
          return (g = Gu(g, p.mode, y)), (g.return = p), g;
        case Pn:
          var _ = g._init;
          return f(p, _(g._payload), y);
      }
      if (Ki(g) || Mi(g)) return (g = yr(g, p.mode, y, null)), (g.return = p), g;
      pa(p, g);
    }
    return null;
  }
  function d(p, g, y, _) {
    var S = g !== null ? g.key : null;
    if ((typeof y == "string" && y !== "") || typeof y == "number")
      return S !== null ? null : s(p, g, "" + y, _);
    if (typeof y == "object" && y !== null) {
      switch (y.$$typeof) {
        case ra:
          return y.key === S ? u(p, g, y, _) : null;
        case jr:
          return y.key === S ? l(p, g, y, _) : null;
        case Pn:
          return (S = y._init), d(p, g, S(y._payload), _);
      }
      if (Ki(y) || Mi(y)) return S !== null ? null : c(p, g, y, _, null);
      pa(p, y);
    }
    return null;
  }
  function h(p, g, y, _, S) {
    if ((typeof _ == "string" && _ !== "") || typeof _ == "number")
      return (p = p.get(y) || null), s(g, p, "" + _, S);
    if (typeof _ == "object" && _ !== null) {
      switch (_.$$typeof) {
        case ra:
          return (p = p.get(_.key === null ? y : _.key) || null), u(g, p, _, S);
        case jr:
          return (p = p.get(_.key === null ? y : _.key) || null), l(g, p, _, S);
        case Pn:
          var E = _._init;
          return h(p, g, y, E(_._payload), S);
      }
      if (Ki(_) || Mi(_)) return (p = p.get(y) || null), c(g, p, _, S, null);
      pa(g, _);
    }
    return null;
  }
  function m(p, g, y, _) {
    for (var S = null, E = null, k = g, C = (g = 0), T = null; k !== null && C < y.length; C++) {
      k.index > C ? ((T = k), (k = null)) : (T = k.sibling);
      var I = d(p, k, y[C], _);
      if (I === null) {
        k === null && (k = T);
        break;
      }
      e && k && I.alternate === null && t(p, k),
        (g = o(I, g, C)),
        E === null ? (S = I) : (E.sibling = I),
        (E = I),
        (k = T);
    }
    if (C === y.length) return n(p, k), ge && ur(p, C), S;
    if (k === null) {
      for (; C < y.length; C++)
        (k = f(p, y[C], _)),
          k !== null && ((g = o(k, g, C)), E === null ? (S = k) : (E.sibling = k), (E = k));
      return ge && ur(p, C), S;
    }
    for (k = r(p, k); C < y.length; C++)
      (T = h(k, p, C, y[C], _)),
        T !== null &&
          (e && T.alternate !== null && k.delete(T.key === null ? C : T.key),
          (g = o(T, g, C)),
          E === null ? (S = T) : (E.sibling = T),
          (E = T));
    return (
      e &&
        k.forEach(function (M) {
          return t(p, M);
        }),
      ge && ur(p, C),
      S
    );
  }
  function v(p, g, y, _) {
    var S = Mi(y);
    if (typeof S != "function") throw Error(j(150));
    if (((y = S.call(y)), y == null)) throw Error(j(151));
    for (
      var E = (S = null), k = g, C = (g = 0), T = null, I = y.next();
      k !== null && !I.done;
      C++, I = y.next()
    ) {
      k.index > C ? ((T = k), (k = null)) : (T = k.sibling);
      var M = d(p, k, I.value, _);
      if (M === null) {
        k === null && (k = T);
        break;
      }
      e && k && M.alternate === null && t(p, k),
        (g = o(M, g, C)),
        E === null ? (S = M) : (E.sibling = M),
        (E = M),
        (k = T);
    }
    if (I.done) return n(p, k), ge && ur(p, C), S;
    if (k === null) {
      for (; !I.done; C++, I = y.next())
        (I = f(p, I.value, _)),
          I !== null && ((g = o(I, g, C)), E === null ? (S = I) : (E.sibling = I), (E = I));
      return ge && ur(p, C), S;
    }
    for (k = r(p, k); !I.done; C++, I = y.next())
      (I = h(k, p, C, I.value, _)),
        I !== null &&
          (e && I.alternate !== null && k.delete(I.key === null ? C : I.key),
          (g = o(I, g, C)),
          E === null ? (S = I) : (E.sibling = I),
          (E = I));
    return (
      e &&
        k.forEach(function (z) {
          return t(p, z);
        }),
      ge && ur(p, C),
      S
    );
  }
  function w(p, g, y, _) {
    if (
      (typeof y == "object" &&
        y !== null &&
        y.type === Br &&
        y.key === null &&
        (y = y.props.children),
      typeof y == "object" && y !== null)
    ) {
      switch (y.$$typeof) {
        case ra:
          e: {
            for (var S = y.key, E = g; E !== null; ) {
              if (E.key === S) {
                if (((S = y.type), S === Br)) {
                  if (E.tag === 7) {
                    n(p, E.sibling), (g = i(E, y.props.children)), (g.return = p), (p = g);
                    break e;
                  }
                } else if (
                  E.elementType === S ||
                  (typeof S == "object" && S !== null && S.$$typeof === Pn && Pm(S) === E.type)
                ) {
                  n(p, E.sibling),
                    (g = i(E, y.props)),
                    (g.ref = zi(p, E, y)),
                    (g.return = p),
                    (p = g);
                  break e;
                }
                n(p, E);
                break;
              } else t(p, E);
              E = E.sibling;
            }
            y.type === Br
              ? ((g = yr(y.props.children, p.mode, _, y.key)), (g.return = p), (p = g))
              : ((_ = ja(y.type, y.key, y.props, null, p.mode, _)),
                (_.ref = zi(p, g, y)),
                (_.return = p),
                (p = _));
          }
          return a(p);
        case jr:
          e: {
            for (E = y.key; g !== null; ) {
              if (g.key === E)
                if (
                  g.tag === 4 &&
                  g.stateNode.containerInfo === y.containerInfo &&
                  g.stateNode.implementation === y.implementation
                ) {
                  n(p, g.sibling), (g = i(g, y.children || [])), (g.return = p), (p = g);
                  break e;
                } else {
                  n(p, g);
                  break;
                }
              else t(p, g);
              g = g.sibling;
            }
            (g = Gu(y, p.mode, _)), (g.return = p), (p = g);
          }
          return a(p);
        case Pn:
          return (E = y._init), w(p, g, E(y._payload), _);
      }
      if (Ki(y)) return m(p, g, y, _);
      if (Mi(y)) return v(p, g, y, _);
      pa(p, y);
    }
    return (typeof y == "string" && y !== "") || typeof y == "number"
      ? ((y = "" + y),
        g !== null && g.tag === 6
          ? (n(p, g.sibling), (g = i(g, y)), (g.return = p), (p = g))
          : (n(p, g), (g = Uu(y, p.mode, _)), (g.return = p), (p = g)),
        a(p))
      : n(p, g);
  }
  return w;
}
var hi = gE(!0),
  vE = gE(!1),
  os = rr(null),
  as = null,
  Xr = null,
  zg = null;
function $g() {
  zg = Xr = as = null;
}
function Dg(e) {
  var t = os.current;
  pe(os), (e._currentValue = t);
}
function Ap(e, t, n) {
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
function ii(e, t) {
  (as = e),
    (zg = Xr = null),
    (e = e.dependencies),
    e !== null && e.firstContext !== null && (e.lanes & t && (rt = !0), (e.firstContext = null));
}
function bt(e) {
  var t = e._currentValue;
  if (zg !== e)
    if (((e = { context: e, memoizedValue: t, next: null }), Xr === null)) {
      if (as === null) throw Error(j(308));
      (Xr = e), (as.dependencies = { lanes: 0, firstContext: e });
    } else Xr = Xr.next = e;
  return t;
}
var dr = null;
function Fg(e) {
  dr === null ? (dr = [e]) : dr.push(e);
}
function mE(e, t, n, r) {
  var i = t.interleaved;
  return (
    i === null ? ((n.next = n), Fg(t)) : ((n.next = i.next), (i.next = n)),
    (t.interleaved = n),
    _n(e, r)
  );
}
function _n(e, t) {
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
var qn = !1;
function jg(e) {
  e.updateQueue = {
    baseState: e.memoizedState,
    firstBaseUpdate: null,
    lastBaseUpdate: null,
    shared: { pending: null, interleaved: null, lanes: 0 },
    effects: null,
  };
}
function yE(e, t) {
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
function gn(e, t) {
  return { eventTime: e, lane: t, tag: 0, payload: null, callback: null, next: null };
}
function Wn(e, t, n) {
  var r = e.updateQueue;
  if (r === null) return null;
  if (((r = r.shared), ae & 2)) {
    var i = r.pending;
    return i === null ? (t.next = t) : ((t.next = i.next), (i.next = t)), (r.pending = t), _n(e, n);
  }
  return (
    (i = r.interleaved),
    i === null ? ((t.next = t), Fg(r)) : ((t.next = i.next), (i.next = t)),
    (r.interleaved = t),
    _n(e, n)
  );
}
function Oa(e, t, n) {
  if (((t = t.updateQueue), t !== null && ((t = t.shared), (n & 4194240) !== 0))) {
    var r = t.lanes;
    (r &= e.pendingLanes), (n |= r), (t.lanes = n), Cg(e, n);
  }
}
function qm(e, t) {
  var n = e.updateQueue,
    r = e.alternate;
  if (r !== null && ((r = r.updateQueue), n === r)) {
    var i = null,
      o = null;
    if (((n = n.firstBaseUpdate), n !== null)) {
      do {
        var a = {
          eventTime: n.eventTime,
          lane: n.lane,
          tag: n.tag,
          payload: n.payload,
          callback: n.callback,
          next: null,
        };
        o === null ? (i = o = a) : (o = o.next = a), (n = n.next);
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
function ss(e, t, n, r) {
  var i = e.updateQueue;
  qn = !1;
  var o = i.firstBaseUpdate,
    a = i.lastBaseUpdate,
    s = i.shared.pending;
  if (s !== null) {
    i.shared.pending = null;
    var u = s,
      l = u.next;
    (u.next = null), a === null ? (o = l) : (a.next = l), (a = u);
    var c = e.alternate;
    c !== null &&
      ((c = c.updateQueue),
      (s = c.lastBaseUpdate),
      s !== a && (s === null ? (c.firstBaseUpdate = l) : (s.next = l), (c.lastBaseUpdate = u)));
  }
  if (o !== null) {
    var f = i.baseState;
    (a = 0), (c = l = u = null), (s = o);
    do {
      var d = s.lane,
        h = s.eventTime;
      if ((r & d) === d) {
        c !== null &&
          (c = c.next = {
            eventTime: h,
            lane: 0,
            tag: s.tag,
            payload: s.payload,
            callback: s.callback,
            next: null,
          });
        e: {
          var m = e,
            v = s;
          switch (((d = t), (h = n), v.tag)) {
            case 1:
              if (((m = v.payload), typeof m == "function")) {
                f = m.call(h, f, d);
                break e;
              }
              f = m;
              break e;
            case 3:
              m.flags = (m.flags & -65537) | 128;
            case 0:
              if (((m = v.payload), (d = typeof m == "function" ? m.call(h, f, d) : m), d == null))
                break e;
              f = _e({}, f, d);
              break e;
            case 2:
              qn = !0;
          }
        }
        s.callback !== null &&
          s.lane !== 0 &&
          ((e.flags |= 64), (d = i.effects), d === null ? (i.effects = [s]) : d.push(s));
      } else
        (h = {
          eventTime: h,
          lane: d,
          tag: s.tag,
          payload: s.payload,
          callback: s.callback,
          next: null,
        }),
          c === null ? ((l = c = h), (u = f)) : (c = c.next = h),
          (a |= d);
      if (((s = s.next), s === null)) {
        if (((s = i.shared.pending), s === null)) break;
        (d = s), (s = d.next), (d.next = null), (i.lastBaseUpdate = d), (i.shared.pending = null);
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
      do (a |= i.lane), (i = i.next);
      while (i !== t);
    } else o === null && (i.shared.lanes = 0);
    (br |= a), (e.lanes = a), (e.memoizedState = f);
  }
}
function Om(e, t, n) {
  if (((e = t.effects), (t.effects = null), e !== null))
    for (t = 0; t < e.length; t++) {
      var r = e[t],
        i = r.callback;
      if (i !== null) {
        if (((r.callback = null), (r = n), typeof i != "function")) throw Error(j(191, i));
        i.call(r);
      }
    }
}
var Go = {},
  Qt = rr(Go),
  No = rr(Go),
  Ro = rr(Go);
function hr(e) {
  if (e === Go) throw Error(j(174));
  return e;
}
function Bg(e, t) {
  switch ((ce(Ro, t), ce(No, e), ce(Qt, Go), (e = t.nodeType), e)) {
    case 9:
    case 11:
      t = (t = t.documentElement) ? t.namespaceURI : fp(null, "");
      break;
    default:
      (e = e === 8 ? t.parentNode : t),
        (t = e.namespaceURI || null),
        (e = e.tagName),
        (t = fp(t, e));
  }
  pe(Qt), ce(Qt, t);
}
function pi() {
  pe(Qt), pe(No), pe(Ro);
}
function _E(e) {
  hr(Ro.current);
  var t = hr(Qt.current),
    n = fp(t, e.type);
  t !== n && (ce(No, e), ce(Qt, n));
}
function Hg(e) {
  No.current === e && (pe(Qt), pe(No));
}
var me = rr(0);
function us(e) {
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
var Du = [];
function Vg() {
  for (var e = 0; e < Du.length; e++) Du[e]._workInProgressVersionPrimary = null;
  Du.length = 0;
}
var La = bn.ReactCurrentDispatcher,
  Fu = bn.ReactCurrentBatchConfig,
  Er = 0,
  ye = null,
  Te = null,
  Oe = null,
  ls = !1,
  fo = !1,
  To = 0,
  FR = 0;
function Ve() {
  throw Error(j(321));
}
function Ug(e, t) {
  if (t === null) return !1;
  for (var n = 0; n < t.length && n < e.length; n++) if (!Dt(e[n], t[n])) return !1;
  return !0;
}
function Gg(e, t, n, r, i, o) {
  if (
    ((Er = o),
    (ye = t),
    (t.memoizedState = null),
    (t.updateQueue = null),
    (t.lanes = 0),
    (La.current = e === null || e.memoizedState === null ? VR : UR),
    (e = n(r, i)),
    fo)
  ) {
    o = 0;
    do {
      if (((fo = !1), (To = 0), 25 <= o)) throw Error(j(301));
      (o += 1), (Oe = Te = null), (t.updateQueue = null), (La.current = GR), (e = n(r, i));
    } while (fo);
  }
  if (
    ((La.current = cs),
    (t = Te !== null && Te.next !== null),
    (Er = 0),
    (Oe = Te = ye = null),
    (ls = !1),
    t)
  )
    throw Error(j(300));
  return e;
}
function Wg() {
  var e = To !== 0;
  return (To = 0), e;
}
function Wt() {
  var e = { memoizedState: null, baseState: null, baseQueue: null, queue: null, next: null };
  return Oe === null ? (ye.memoizedState = Oe = e) : (Oe = Oe.next = e), Oe;
}
function kt() {
  if (Te === null) {
    var e = ye.alternate;
    e = e !== null ? e.memoizedState : null;
  } else e = Te.next;
  var t = Oe === null ? ye.memoizedState : Oe.next;
  if (t !== null) (Oe = t), (Te = e);
  else {
    if (e === null) throw Error(j(310));
    (Te = e),
      (e = {
        memoizedState: Te.memoizedState,
        baseState: Te.baseState,
        baseQueue: Te.baseQueue,
        queue: Te.queue,
        next: null,
      }),
      Oe === null ? (ye.memoizedState = Oe = e) : (Oe = Oe.next = e);
  }
  return Oe;
}
function Io(e, t) {
  return typeof t == "function" ? t(e) : t;
}
function ju(e) {
  var t = kt(),
    n = t.queue;
  if (n === null) throw Error(j(311));
  n.lastRenderedReducer = e;
  var r = Te,
    i = r.baseQueue,
    o = n.pending;
  if (o !== null) {
    if (i !== null) {
      var a = i.next;
      (i.next = o.next), (o.next = a);
    }
    (r.baseQueue = i = o), (n.pending = null);
  }
  if (i !== null) {
    (o = i.next), (r = r.baseState);
    var s = (a = null),
      u = null,
      l = o;
    do {
      var c = l.lane;
      if ((Er & c) === c)
        u !== null &&
          (u = u.next = {
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
        u === null ? ((s = u = f), (a = r)) : (u = u.next = f), (ye.lanes |= c), (br |= c);
      }
      l = l.next;
    } while (l !== null && l !== o);
    u === null ? (a = r) : (u.next = s),
      Dt(r, t.memoizedState) || (rt = !0),
      (t.memoizedState = r),
      (t.baseState = a),
      (t.baseQueue = u),
      (n.lastRenderedState = r);
  }
  if (((e = n.interleaved), e !== null)) {
    i = e;
    do (o = i.lane), (ye.lanes |= o), (br |= o), (i = i.next);
    while (i !== e);
  } else i === null && (n.lanes = 0);
  return [t.memoizedState, n.dispatch];
}
function Bu(e) {
  var t = kt(),
    n = t.queue;
  if (n === null) throw Error(j(311));
  n.lastRenderedReducer = e;
  var r = n.dispatch,
    i = n.pending,
    o = t.memoizedState;
  if (i !== null) {
    n.pending = null;
    var a = (i = i.next);
    do (o = e(o, a.action)), (a = a.next);
    while (a !== i);
    Dt(o, t.memoizedState) || (rt = !0),
      (t.memoizedState = o),
      t.baseQueue === null && (t.baseState = o),
      (n.lastRenderedState = o);
  }
  return [o, r];
}
function wE() {}
function xE(e, t) {
  var n = ye,
    r = kt(),
    i = t(),
    o = !Dt(r.memoizedState, i);
  if (
    (o && ((r.memoizedState = i), (rt = !0)),
    (r = r.queue),
    Kg(bE.bind(null, n, r, e), [e]),
    r.getSnapshot !== t || o || (Oe !== null && Oe.memoizedState.tag & 1))
  ) {
    if (((n.flags |= 2048), Ao(9, EE.bind(null, n, r, i, t), void 0, null), Le === null))
      throw Error(j(349));
    Er & 30 || SE(n, t, i);
  }
  return i;
}
function SE(e, t, n) {
  (e.flags |= 16384),
    (e = { getSnapshot: t, value: n }),
    (t = ye.updateQueue),
    t === null
      ? ((t = { lastEffect: null, stores: null }), (ye.updateQueue = t), (t.stores = [e]))
      : ((n = t.stores), n === null ? (t.stores = [e]) : n.push(e));
}
function EE(e, t, n, r) {
  (t.value = n), (t.getSnapshot = r), kE(t) && CE(e);
}
function bE(e, t, n) {
  return n(function () {
    kE(t) && CE(e);
  });
}
function kE(e) {
  var t = e.getSnapshot;
  e = e.value;
  try {
    var n = t();
    return !Dt(e, n);
  } catch {
    return !0;
  }
}
function CE(e) {
  var t = _n(e, 1);
  t !== null && zt(t, e, 1, -1);
}
function Lm(e) {
  var t = Wt();
  return (
    typeof e == "function" && (e = e()),
    (t.memoizedState = t.baseState = e),
    (e = {
      pending: null,
      interleaved: null,
      lanes: 0,
      dispatch: null,
      lastRenderedReducer: Io,
      lastRenderedState: e,
    }),
    (t.queue = e),
    (e = e.dispatch = HR.bind(null, ye, e)),
    [t.memoizedState, e]
  );
}
function Ao(e, t, n, r) {
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
function NE() {
  return kt().memoizedState;
}
function za(e, t, n, r) {
  var i = Wt();
  (ye.flags |= e), (i.memoizedState = Ao(1 | t, n, void 0, r === void 0 ? null : r));
}
function Ls(e, t, n, r) {
  var i = kt();
  r = r === void 0 ? null : r;
  var o = void 0;
  if (Te !== null) {
    var a = Te.memoizedState;
    if (((o = a.destroy), r !== null && Ug(r, a.deps))) {
      i.memoizedState = Ao(t, n, o, r);
      return;
    }
  }
  (ye.flags |= e), (i.memoizedState = Ao(1 | t, n, o, r));
}
function zm(e, t) {
  return za(8390656, 8, e, t);
}
function Kg(e, t) {
  return Ls(2048, 8, e, t);
}
function RE(e, t) {
  return Ls(4, 2, e, t);
}
function TE(e, t) {
  return Ls(4, 4, e, t);
}
function IE(e, t) {
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
function AE(e, t, n) {
  return (n = n != null ? n.concat([e]) : null), Ls(4, 4, IE.bind(null, t, e), n);
}
function Yg() {}
function ME(e, t) {
  var n = kt();
  t = t === void 0 ? null : t;
  var r = n.memoizedState;
  return r !== null && t !== null && Ug(t, r[1]) ? r[0] : ((n.memoizedState = [e, t]), e);
}
function PE(e, t) {
  var n = kt();
  t = t === void 0 ? null : t;
  var r = n.memoizedState;
  return r !== null && t !== null && Ug(t, r[1])
    ? r[0]
    : ((e = e()), (n.memoizedState = [e, t]), e);
}
function qE(e, t, n) {
  return Er & 21
    ? (Dt(n, t) || ((n = DS()), (ye.lanes |= n), (br |= n), (e.baseState = !0)), t)
    : (e.baseState && ((e.baseState = !1), (rt = !0)), (e.memoizedState = n));
}
function jR(e, t) {
  var n = le;
  (le = n !== 0 && 4 > n ? n : 4), e(!0);
  var r = Fu.transition;
  Fu.transition = {};
  try {
    e(!1), t();
  } finally {
    (le = n), (Fu.transition = r);
  }
}
function OE() {
  return kt().memoizedState;
}
function BR(e, t, n) {
  var r = Yn(e);
  if (((n = { lane: r, action: n, hasEagerState: !1, eagerState: null, next: null }), LE(e)))
    zE(t, n);
  else if (((n = mE(e, t, n, r)), n !== null)) {
    var i = Qe();
    zt(n, e, r, i), $E(n, t, r);
  }
}
function HR(e, t, n) {
  var r = Yn(e),
    i = { lane: r, action: n, hasEagerState: !1, eagerState: null, next: null };
  if (LE(e)) zE(t, i);
  else {
    var o = e.alternate;
    if (e.lanes === 0 && (o === null || o.lanes === 0) && ((o = t.lastRenderedReducer), o !== null))
      try {
        var a = t.lastRenderedState,
          s = o(a, n);
        if (((i.hasEagerState = !0), (i.eagerState = s), Dt(s, a))) {
          var u = t.interleaved;
          u === null ? ((i.next = i), Fg(t)) : ((i.next = u.next), (u.next = i)),
            (t.interleaved = i);
          return;
        }
      } catch {
      } finally {
      }
    (n = mE(e, t, i, r)), n !== null && ((i = Qe()), zt(n, e, r, i), $E(n, t, r));
  }
}
function LE(e) {
  var t = e.alternate;
  return e === ye || (t !== null && t === ye);
}
function zE(e, t) {
  fo = ls = !0;
  var n = e.pending;
  n === null ? (t.next = t) : ((t.next = n.next), (n.next = t)), (e.pending = t);
}
function $E(e, t, n) {
  if (n & 4194240) {
    var r = t.lanes;
    (r &= e.pendingLanes), (n |= r), (t.lanes = n), Cg(e, n);
  }
}
var cs = {
    readContext: bt,
    useCallback: Ve,
    useContext: Ve,
    useEffect: Ve,
    useImperativeHandle: Ve,
    useInsertionEffect: Ve,
    useLayoutEffect: Ve,
    useMemo: Ve,
    useReducer: Ve,
    useRef: Ve,
    useState: Ve,
    useDebugValue: Ve,
    useDeferredValue: Ve,
    useTransition: Ve,
    useMutableSource: Ve,
    useSyncExternalStore: Ve,
    useId: Ve,
    unstable_isNewReconciler: !1,
  },
  VR = {
    readContext: bt,
    useCallback: function (e, t) {
      return (Wt().memoizedState = [e, t === void 0 ? null : t]), e;
    },
    useContext: bt,
    useEffect: zm,
    useImperativeHandle: function (e, t, n) {
      return (n = n != null ? n.concat([e]) : null), za(4194308, 4, IE.bind(null, t, e), n);
    },
    useLayoutEffect: function (e, t) {
      return za(4194308, 4, e, t);
    },
    useInsertionEffect: function (e, t) {
      return za(4, 2, e, t);
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
        (e = e.dispatch = BR.bind(null, ye, e)),
        [r.memoizedState, e]
      );
    },
    useRef: function (e) {
      var t = Wt();
      return (e = { current: e }), (t.memoizedState = e);
    },
    useState: Lm,
    useDebugValue: Yg,
    useDeferredValue: function (e) {
      return (Wt().memoizedState = e);
    },
    useTransition: function () {
      var e = Lm(!1),
        t = e[0];
      return (e = jR.bind(null, e[1])), (Wt().memoizedState = e), [t, e];
    },
    useMutableSource: function () {},
    useSyncExternalStore: function (e, t, n) {
      var r = ye,
        i = Wt();
      if (ge) {
        if (n === void 0) throw Error(j(407));
        n = n();
      } else {
        if (((n = t()), Le === null)) throw Error(j(349));
        Er & 30 || SE(r, t, n);
      }
      i.memoizedState = n;
      var o = { value: n, getSnapshot: t };
      return (
        (i.queue = o),
        zm(bE.bind(null, r, o, e), [e]),
        (r.flags |= 2048),
        Ao(9, EE.bind(null, r, o, n, t), void 0, null),
        n
      );
    },
    useId: function () {
      var e = Wt(),
        t = Le.identifierPrefix;
      if (ge) {
        var n = fn,
          r = cn;
        (n = (r & ~(1 << (32 - Lt(r) - 1))).toString(32) + n),
          (t = ":" + t + "R" + n),
          (n = To++),
          0 < n && (t += "H" + n.toString(32)),
          (t += ":");
      } else (n = FR++), (t = ":" + t + "r" + n.toString(32) + ":");
      return (e.memoizedState = t);
    },
    unstable_isNewReconciler: !1,
  },
  UR = {
    readContext: bt,
    useCallback: ME,
    useContext: bt,
    useEffect: Kg,
    useImperativeHandle: AE,
    useInsertionEffect: RE,
    useLayoutEffect: TE,
    useMemo: PE,
    useReducer: ju,
    useRef: NE,
    useState: function () {
      return ju(Io);
    },
    useDebugValue: Yg,
    useDeferredValue: function (e) {
      var t = kt();
      return qE(t, Te.memoizedState, e);
    },
    useTransition: function () {
      var e = ju(Io)[0],
        t = kt().memoizedState;
      return [e, t];
    },
    useMutableSource: wE,
    useSyncExternalStore: xE,
    useId: OE,
    unstable_isNewReconciler: !1,
  },
  GR = {
    readContext: bt,
    useCallback: ME,
    useContext: bt,
    useEffect: Kg,
    useImperativeHandle: AE,
    useInsertionEffect: RE,
    useLayoutEffect: TE,
    useMemo: PE,
    useReducer: Bu,
    useRef: NE,
    useState: function () {
      return Bu(Io);
    },
    useDebugValue: Yg,
    useDeferredValue: function (e) {
      var t = kt();
      return Te === null ? (t.memoizedState = e) : qE(t, Te.memoizedState, e);
    },
    useTransition: function () {
      var e = Bu(Io)[0],
        t = kt().memoizedState;
      return [e, t];
    },
    useMutableSource: wE,
    useSyncExternalStore: xE,
    useId: OE,
    unstable_isNewReconciler: !1,
  };
function At(e, t) {
  if (e && e.defaultProps) {
    (t = _e({}, t)), (e = e.defaultProps);
    for (var n in e) t[n] === void 0 && (t[n] = e[n]);
    return t;
  }
  return t;
}
function Mp(e, t, n, r) {
  (t = e.memoizedState),
    (n = n(r, t)),
    (n = n == null ? t : _e({}, t, n)),
    (e.memoizedState = n),
    e.lanes === 0 && (e.updateQueue.baseState = n);
}
var zs = {
  isMounted: function (e) {
    return (e = e._reactInternals) ? Tr(e) === e : !1;
  },
  enqueueSetState: function (e, t, n) {
    e = e._reactInternals;
    var r = Qe(),
      i = Yn(e),
      o = gn(r, i);
    (o.payload = t),
      n != null && (o.callback = n),
      (t = Wn(e, o, i)),
      t !== null && (zt(t, e, i, r), Oa(t, e, i));
  },
  enqueueReplaceState: function (e, t, n) {
    e = e._reactInternals;
    var r = Qe(),
      i = Yn(e),
      o = gn(r, i);
    (o.tag = 1),
      (o.payload = t),
      n != null && (o.callback = n),
      (t = Wn(e, o, i)),
      t !== null && (zt(t, e, i, r), Oa(t, e, i));
  },
  enqueueForceUpdate: function (e, t) {
    e = e._reactInternals;
    var n = Qe(),
      r = Yn(e),
      i = gn(n, r);
    (i.tag = 2),
      t != null && (i.callback = t),
      (t = Wn(e, i, r)),
      t !== null && (zt(t, e, r, n), Oa(t, e, r));
  },
};
function $m(e, t, n, r, i, o, a) {
  return (
    (e = e.stateNode),
    typeof e.shouldComponentUpdate == "function"
      ? e.shouldComponentUpdate(r, o, a)
      : t.prototype && t.prototype.isPureReactComponent
      ? !Eo(n, r) || !Eo(i, o)
      : !0
  );
}
function DE(e, t, n) {
  var r = !1,
    i = er,
    o = t.contextType;
  return (
    typeof o == "object" && o !== null
      ? (o = bt(o))
      : ((i = at(t) ? xr : We.current),
        (r = t.contextTypes),
        (o = (r = r != null) ? fi(e, i) : er)),
    (t = new t(n, o)),
    (e.memoizedState = t.state !== null && t.state !== void 0 ? t.state : null),
    (t.updater = zs),
    (e.stateNode = t),
    (t._reactInternals = e),
    r &&
      ((e = e.stateNode),
      (e.__reactInternalMemoizedUnmaskedChildContext = i),
      (e.__reactInternalMemoizedMaskedChildContext = o)),
    t
  );
}
function Dm(e, t, n, r) {
  (e = t.state),
    typeof t.componentWillReceiveProps == "function" && t.componentWillReceiveProps(n, r),
    typeof t.UNSAFE_componentWillReceiveProps == "function" &&
      t.UNSAFE_componentWillReceiveProps(n, r),
    t.state !== e && zs.enqueueReplaceState(t, t.state, null);
}
function Pp(e, t, n, r) {
  var i = e.stateNode;
  (i.props = n), (i.state = e.memoizedState), (i.refs = {}), jg(e);
  var o = t.contextType;
  typeof o == "object" && o !== null
    ? (i.context = bt(o))
    : ((o = at(t) ? xr : We.current), (i.context = fi(e, o))),
    (i.state = e.memoizedState),
    (o = t.getDerivedStateFromProps),
    typeof o == "function" && (Mp(e, t, o, n), (i.state = e.memoizedState)),
    typeof t.getDerivedStateFromProps == "function" ||
      typeof i.getSnapshotBeforeUpdate == "function" ||
      (typeof i.UNSAFE_componentWillMount != "function" &&
        typeof i.componentWillMount != "function") ||
      ((t = i.state),
      typeof i.componentWillMount == "function" && i.componentWillMount(),
      typeof i.UNSAFE_componentWillMount == "function" && i.UNSAFE_componentWillMount(),
      t !== i.state && zs.enqueueReplaceState(i, i.state, null),
      ss(e, n, i, r),
      (i.state = e.memoizedState)),
    typeof i.componentDidMount == "function" && (e.flags |= 4194308);
}
function gi(e, t) {
  try {
    var n = "",
      r = t;
    do (n += wN(r)), (r = r.return);
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
function Hu(e, t, n) {
  return { value: e, source: null, stack: n ?? null, digest: t ?? null };
}
function qp(e, t) {
  try {
    console.error(t.value);
  } catch (n) {
    setTimeout(function () {
      throw n;
    });
  }
}
var WR = typeof WeakMap == "function" ? WeakMap : Map;
function FE(e, t, n) {
  (n = gn(-1, n)), (n.tag = 3), (n.payload = { element: null });
  var r = t.value;
  return (
    (n.callback = function () {
      ds || ((ds = !0), (Vp = r)), qp(e, t);
    }),
    n
  );
}
function jE(e, t, n) {
  (n = gn(-1, n)), (n.tag = 3);
  var r = e.type.getDerivedStateFromError;
  if (typeof r == "function") {
    var i = t.value;
    (n.payload = function () {
      return r(i);
    }),
      (n.callback = function () {
        qp(e, t);
      });
  }
  var o = e.stateNode;
  return (
    o !== null &&
      typeof o.componentDidCatch == "function" &&
      (n.callback = function () {
        qp(e, t), typeof r != "function" && (Kn === null ? (Kn = new Set([this])) : Kn.add(this));
        var a = t.stack;
        this.componentDidCatch(t.value, { componentStack: a !== null ? a : "" });
      }),
    n
  );
}
function Fm(e, t, n) {
  var r = e.pingCache;
  if (r === null) {
    r = e.pingCache = new WR();
    var i = new Set();
    r.set(t, i);
  } else (i = r.get(t)), i === void 0 && ((i = new Set()), r.set(t, i));
  i.has(n) || (i.add(n), (e = sT.bind(null, e, t, n)), t.then(e, e));
}
function jm(e) {
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
function Bm(e, t, n, r, i) {
  return e.mode & 1
    ? ((e.flags |= 65536), (e.lanes = i), e)
    : (e === t
        ? (e.flags |= 65536)
        : ((e.flags |= 128),
          (n.flags |= 131072),
          (n.flags &= -52805),
          n.tag === 1 &&
            (n.alternate === null ? (n.tag = 17) : ((t = gn(-1, 1)), (t.tag = 2), Wn(n, t, 1))),
          (n.lanes |= 1)),
      e);
}
var KR = bn.ReactCurrentOwner,
  rt = !1;
function Xe(e, t, n, r) {
  t.child = e === null ? vE(t, null, n, r) : hi(t, e.child, n, r);
}
function Hm(e, t, n, r, i) {
  n = n.render;
  var o = t.ref;
  return (
    ii(t, i),
    (r = Gg(e, t, n, r, o, i)),
    (n = Wg()),
    e !== null && !rt
      ? ((t.updateQueue = e.updateQueue), (t.flags &= -2053), (e.lanes &= ~i), wn(e, t, i))
      : (ge && n && qg(t), (t.flags |= 1), Xe(e, t, r, i), t.child)
  );
}
function Vm(e, t, n, r, i) {
  if (e === null) {
    var o = n.type;
    return typeof o == "function" &&
      !rv(o) &&
      o.defaultProps === void 0 &&
      n.compare === null &&
      n.defaultProps === void 0
      ? ((t.tag = 15), (t.type = o), BE(e, t, o, r, i))
      : ((e = ja(n.type, null, r, t, t.mode, i)), (e.ref = t.ref), (e.return = t), (t.child = e));
  }
  if (((o = e.child), !(e.lanes & i))) {
    var a = o.memoizedProps;
    if (((n = n.compare), (n = n !== null ? n : Eo), n(a, r) && e.ref === t.ref))
      return wn(e, t, i);
  }
  return (t.flags |= 1), (e = Xn(o, r)), (e.ref = t.ref), (e.return = t), (t.child = e);
}
function BE(e, t, n, r, i) {
  if (e !== null) {
    var o = e.memoizedProps;
    if (Eo(o, r) && e.ref === t.ref)
      if (((rt = !1), (t.pendingProps = r = o), (e.lanes & i) !== 0)) e.flags & 131072 && (rt = !0);
      else return (t.lanes = e.lanes), wn(e, t, i);
  }
  return Op(e, t, n, r, i);
}
function HE(e, t, n) {
  var r = t.pendingProps,
    i = r.children,
    o = e !== null ? e.memoizedState : null;
  if (r.mode === "hidden")
    if (!(t.mode & 1))
      (t.memoizedState = { baseLanes: 0, cachePool: null, transitions: null }),
        ce(Zr, ct),
        (ct |= n);
    else {
      if (!(n & 1073741824))
        return (
          (e = o !== null ? o.baseLanes | n : n),
          (t.lanes = t.childLanes = 1073741824),
          (t.memoizedState = { baseLanes: e, cachePool: null, transitions: null }),
          (t.updateQueue = null),
          ce(Zr, ct),
          (ct |= e),
          null
        );
      (t.memoizedState = { baseLanes: 0, cachePool: null, transitions: null }),
        (r = o !== null ? o.baseLanes : n),
        ce(Zr, ct),
        (ct |= r);
    }
  else
    o !== null ? ((r = o.baseLanes | n), (t.memoizedState = null)) : (r = n), ce(Zr, ct), (ct |= r);
  return Xe(e, t, i, n), t.child;
}
function VE(e, t) {
  var n = t.ref;
  ((e === null && n !== null) || (e !== null && e.ref !== n)) &&
    ((t.flags |= 512), (t.flags |= 2097152));
}
function Op(e, t, n, r, i) {
  var o = at(n) ? xr : We.current;
  return (
    (o = fi(t, o)),
    ii(t, i),
    (n = Gg(e, t, n, r, o, i)),
    (r = Wg()),
    e !== null && !rt
      ? ((t.updateQueue = e.updateQueue), (t.flags &= -2053), (e.lanes &= ~i), wn(e, t, i))
      : (ge && r && qg(t), (t.flags |= 1), Xe(e, t, n, i), t.child)
  );
}
function Um(e, t, n, r, i) {
  if (at(n)) {
    var o = !0;
    ns(t);
  } else o = !1;
  if ((ii(t, i), t.stateNode === null)) $a(e, t), DE(t, n, r), Pp(t, n, r, i), (r = !0);
  else if (e === null) {
    var a = t.stateNode,
      s = t.memoizedProps;
    a.props = s;
    var u = a.context,
      l = n.contextType;
    typeof l == "object" && l !== null
      ? (l = bt(l))
      : ((l = at(n) ? xr : We.current), (l = fi(t, l)));
    var c = n.getDerivedStateFromProps,
      f = typeof c == "function" || typeof a.getSnapshotBeforeUpdate == "function";
    f ||
      (typeof a.UNSAFE_componentWillReceiveProps != "function" &&
        typeof a.componentWillReceiveProps != "function") ||
      ((s !== r || u !== l) && Dm(t, a, r, l)),
      (qn = !1);
    var d = t.memoizedState;
    (a.state = d),
      ss(t, r, a, i),
      (u = t.memoizedState),
      s !== r || d !== u || ot.current || qn
        ? (typeof c == "function" && (Mp(t, n, c, r), (u = t.memoizedState)),
          (s = qn || $m(t, n, s, r, d, u, l))
            ? (f ||
                (typeof a.UNSAFE_componentWillMount != "function" &&
                  typeof a.componentWillMount != "function") ||
                (typeof a.componentWillMount == "function" && a.componentWillMount(),
                typeof a.UNSAFE_componentWillMount == "function" && a.UNSAFE_componentWillMount()),
              typeof a.componentDidMount == "function" && (t.flags |= 4194308))
            : (typeof a.componentDidMount == "function" && (t.flags |= 4194308),
              (t.memoizedProps = r),
              (t.memoizedState = u)),
          (a.props = r),
          (a.state = u),
          (a.context = l),
          (r = s))
        : (typeof a.componentDidMount == "function" && (t.flags |= 4194308), (r = !1));
  } else {
    (a = t.stateNode),
      yE(e, t),
      (s = t.memoizedProps),
      (l = t.type === t.elementType ? s : At(t.type, s)),
      (a.props = l),
      (f = t.pendingProps),
      (d = a.context),
      (u = n.contextType),
      typeof u == "object" && u !== null
        ? (u = bt(u))
        : ((u = at(n) ? xr : We.current), (u = fi(t, u)));
    var h = n.getDerivedStateFromProps;
    (c = typeof h == "function" || typeof a.getSnapshotBeforeUpdate == "function") ||
      (typeof a.UNSAFE_componentWillReceiveProps != "function" &&
        typeof a.componentWillReceiveProps != "function") ||
      ((s !== f || d !== u) && Dm(t, a, r, u)),
      (qn = !1),
      (d = t.memoizedState),
      (a.state = d),
      ss(t, r, a, i);
    var m = t.memoizedState;
    s !== f || d !== m || ot.current || qn
      ? (typeof h == "function" && (Mp(t, n, h, r), (m = t.memoizedState)),
        (l = qn || $m(t, n, l, r, d, m, u) || !1)
          ? (c ||
              (typeof a.UNSAFE_componentWillUpdate != "function" &&
                typeof a.componentWillUpdate != "function") ||
              (typeof a.componentWillUpdate == "function" && a.componentWillUpdate(r, m, u),
              typeof a.UNSAFE_componentWillUpdate == "function" &&
                a.UNSAFE_componentWillUpdate(r, m, u)),
            typeof a.componentDidUpdate == "function" && (t.flags |= 4),
            typeof a.getSnapshotBeforeUpdate == "function" && (t.flags |= 1024))
          : (typeof a.componentDidUpdate != "function" ||
              (s === e.memoizedProps && d === e.memoizedState) ||
              (t.flags |= 4),
            typeof a.getSnapshotBeforeUpdate != "function" ||
              (s === e.memoizedProps && d === e.memoizedState) ||
              (t.flags |= 1024),
            (t.memoizedProps = r),
            (t.memoizedState = m)),
        (a.props = r),
        (a.state = m),
        (a.context = u),
        (r = l))
      : (typeof a.componentDidUpdate != "function" ||
          (s === e.memoizedProps && d === e.memoizedState) ||
          (t.flags |= 4),
        typeof a.getSnapshotBeforeUpdate != "function" ||
          (s === e.memoizedProps && d === e.memoizedState) ||
          (t.flags |= 1024),
        (r = !1));
  }
  return Lp(e, t, n, r, o, i);
}
function Lp(e, t, n, r, i, o) {
  VE(e, t);
  var a = (t.flags & 128) !== 0;
  if (!r && !a) return i && Im(t, n, !1), wn(e, t, o);
  (r = t.stateNode), (KR.current = t);
  var s = a && typeof n.getDerivedStateFromError != "function" ? null : r.render();
  return (
    (t.flags |= 1),
    e !== null && a
      ? ((t.child = hi(t, e.child, null, o)), (t.child = hi(t, null, s, o)))
      : Xe(e, t, s, o),
    (t.memoizedState = r.state),
    i && Im(t, n, !0),
    t.child
  );
}
function UE(e) {
  var t = e.stateNode;
  t.pendingContext
    ? Tm(e, t.pendingContext, t.pendingContext !== t.context)
    : t.context && Tm(e, t.context, !1),
    Bg(e, t.containerInfo);
}
function Gm(e, t, n, r, i) {
  return di(), Lg(i), (t.flags |= 256), Xe(e, t, n, r), t.child;
}
var zp = { dehydrated: null, treeContext: null, retryLane: 0 };
function $p(e) {
  return { baseLanes: e, cachePool: null, transitions: null };
}
function GE(e, t, n) {
  var r = t.pendingProps,
    i = me.current,
    o = !1,
    a = (t.flags & 128) !== 0,
    s;
  if (
    ((s = a) || (s = e !== null && e.memoizedState === null ? !1 : (i & 2) !== 0),
    s ? ((o = !0), (t.flags &= -129)) : (e === null || e.memoizedState !== null) && (i |= 1),
    ce(me, i & 1),
    e === null)
  )
    return (
      Ip(t),
      (e = t.memoizedState),
      e !== null && ((e = e.dehydrated), e !== null)
        ? (t.mode & 1 ? (e.data === "$!" ? (t.lanes = 8) : (t.lanes = 1073741824)) : (t.lanes = 1),
          null)
        : ((a = r.children),
          (e = r.fallback),
          o
            ? ((r = t.mode),
              (o = t.child),
              (a = { mode: "hidden", children: a }),
              !(r & 1) && o !== null
                ? ((o.childLanes = 0), (o.pendingProps = a))
                : (o = Fs(a, r, 0, null)),
              (e = yr(e, r, n, null)),
              (o.return = t),
              (e.return = t),
              (o.sibling = e),
              (t.child = o),
              (t.child.memoizedState = $p(n)),
              (t.memoizedState = zp),
              e)
            : Xg(t, a))
    );
  if (((i = e.memoizedState), i !== null && ((s = i.dehydrated), s !== null)))
    return YR(e, t, a, r, s, i, n);
  if (o) {
    (o = r.fallback), (a = t.mode), (i = e.child), (s = i.sibling);
    var u = { mode: "hidden", children: r.children };
    return (
      !(a & 1) && t.child !== i
        ? ((r = t.child), (r.childLanes = 0), (r.pendingProps = u), (t.deletions = null))
        : ((r = Xn(i, u)), (r.subtreeFlags = i.subtreeFlags & 14680064)),
      s !== null ? (o = Xn(s, o)) : ((o = yr(o, a, n, null)), (o.flags |= 2)),
      (o.return = t),
      (r.return = t),
      (r.sibling = o),
      (t.child = r),
      (r = o),
      (o = t.child),
      (a = e.child.memoizedState),
      (a =
        a === null
          ? $p(n)
          : { baseLanes: a.baseLanes | n, cachePool: null, transitions: a.transitions }),
      (o.memoizedState = a),
      (o.childLanes = e.childLanes & ~n),
      (t.memoizedState = zp),
      r
    );
  }
  return (
    (o = e.child),
    (e = o.sibling),
    (r = Xn(o, { mode: "visible", children: r.children })),
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
function Xg(e, t) {
  return (t = Fs({ mode: "visible", children: t }, e.mode, 0, null)), (t.return = e), (e.child = t);
}
function ga(e, t, n, r) {
  return (
    r !== null && Lg(r),
    hi(t, e.child, null, n),
    (e = Xg(t, t.pendingProps.children)),
    (e.flags |= 2),
    (t.memoizedState = null),
    e
  );
}
function YR(e, t, n, r, i, o, a) {
  if (n)
    return t.flags & 256
      ? ((t.flags &= -257), (r = Hu(Error(j(422)))), ga(e, t, a, r))
      : t.memoizedState !== null
      ? ((t.child = e.child), (t.flags |= 128), null)
      : ((o = r.fallback),
        (i = t.mode),
        (r = Fs({ mode: "visible", children: r.children }, i, 0, null)),
        (o = yr(o, i, a, null)),
        (o.flags |= 2),
        (r.return = t),
        (o.return = t),
        (r.sibling = o),
        (t.child = r),
        t.mode & 1 && hi(t, e.child, null, a),
        (t.child.memoizedState = $p(a)),
        (t.memoizedState = zp),
        o);
  if (!(t.mode & 1)) return ga(e, t, a, null);
  if (i.data === "$!") {
    if (((r = i.nextSibling && i.nextSibling.dataset), r)) var s = r.dgst;
    return (r = s), (o = Error(j(419))), (r = Hu(o, r, void 0)), ga(e, t, a, r);
  }
  if (((s = (a & e.childLanes) !== 0), rt || s)) {
    if (((r = Le), r !== null)) {
      switch (a & -a) {
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
      (i = i & (r.suspendedLanes | a) ? 0 : i),
        i !== 0 && i !== o.retryLane && ((o.retryLane = i), _n(e, i), zt(r, e, i, -1));
    }
    return nv(), (r = Hu(Error(j(421)))), ga(e, t, a, r);
  }
  return i.data === "$?"
    ? ((t.flags |= 128), (t.child = e.child), (t = uT.bind(null, e)), (i._reactRetry = t), null)
    : ((e = o.treeContext),
      (dt = Gn(i.nextSibling)),
      (ht = t),
      (ge = !0),
      (qt = null),
      e !== null &&
        ((yt[_t++] = cn),
        (yt[_t++] = fn),
        (yt[_t++] = Sr),
        (cn = e.id),
        (fn = e.overflow),
        (Sr = t)),
      (t = Xg(t, r.children)),
      (t.flags |= 4096),
      t);
}
function Wm(e, t, n) {
  e.lanes |= t;
  var r = e.alternate;
  r !== null && (r.lanes |= t), Ap(e.return, t, n);
}
function Vu(e, t, n, r, i) {
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
function WE(e, t, n) {
  var r = t.pendingProps,
    i = r.revealOrder,
    o = r.tail;
  if ((Xe(e, t, r.children, n), (r = me.current), r & 2)) (r = (r & 1) | 2), (t.flags |= 128);
  else {
    if (e !== null && e.flags & 128)
      e: for (e = t.child; e !== null; ) {
        if (e.tag === 13) e.memoizedState !== null && Wm(e, n, t);
        else if (e.tag === 19) Wm(e, n, t);
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
  if ((ce(me, r), !(t.mode & 1))) t.memoizedState = null;
  else
    switch (i) {
      case "forwards":
        for (n = t.child, i = null; n !== null; )
          (e = n.alternate), e !== null && us(e) === null && (i = n), (n = n.sibling);
        (n = i),
          n === null ? ((i = t.child), (t.child = null)) : ((i = n.sibling), (n.sibling = null)),
          Vu(t, !1, i, n, o);
        break;
      case "backwards":
        for (n = null, i = t.child, t.child = null; i !== null; ) {
          if (((e = i.alternate), e !== null && us(e) === null)) {
            t.child = i;
            break;
          }
          (e = i.sibling), (i.sibling = n), (n = i), (i = e);
        }
        Vu(t, !0, n, null, o);
        break;
      case "together":
        Vu(t, !1, null, null, void 0);
        break;
      default:
        t.memoizedState = null;
    }
  return t.child;
}
function $a(e, t) {
  !(t.mode & 1) && e !== null && ((e.alternate = null), (t.alternate = null), (t.flags |= 2));
}
function wn(e, t, n) {
  if ((e !== null && (t.dependencies = e.dependencies), (br |= t.lanes), !(n & t.childLanes)))
    return null;
  if (e !== null && t.child !== e.child) throw Error(j(153));
  if (t.child !== null) {
    for (e = t.child, n = Xn(e, e.pendingProps), t.child = n, n.return = t; e.sibling !== null; )
      (e = e.sibling), (n = n.sibling = Xn(e, e.pendingProps)), (n.return = t);
    n.sibling = null;
  }
  return t.child;
}
function XR(e, t, n) {
  switch (t.tag) {
    case 3:
      UE(t), di();
      break;
    case 5:
      _E(t);
      break;
    case 1:
      at(t.type) && ns(t);
      break;
    case 4:
      Bg(t, t.stateNode.containerInfo);
      break;
    case 10:
      var r = t.type._context,
        i = t.memoizedProps.value;
      ce(os, r._currentValue), (r._currentValue = i);
      break;
    case 13:
      if (((r = t.memoizedState), r !== null))
        return r.dehydrated !== null
          ? (ce(me, me.current & 1), (t.flags |= 128), null)
          : n & t.child.childLanes
          ? GE(e, t, n)
          : (ce(me, me.current & 1), (e = wn(e, t, n)), e !== null ? e.sibling : null);
      ce(me, me.current & 1);
      break;
    case 19:
      if (((r = (n & t.childLanes) !== 0), e.flags & 128)) {
        if (r) return WE(e, t, n);
        t.flags |= 128;
      }
      if (
        ((i = t.memoizedState),
        i !== null && ((i.rendering = null), (i.tail = null), (i.lastEffect = null)),
        ce(me, me.current),
        r)
      )
        break;
      return null;
    case 22:
    case 23:
      return (t.lanes = 0), HE(e, t, n);
  }
  return wn(e, t, n);
}
var KE, Dp, YE, XE;
KE = function (e, t) {
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
Dp = function () {};
YE = function (e, t, n, r) {
  var i = e.memoizedProps;
  if (i !== r) {
    (e = t.stateNode), hr(Qt.current);
    var o = null;
    switch (n) {
      case "input":
        (i = sp(e, i)), (r = sp(e, r)), (o = []);
        break;
      case "select":
        (i = _e({}, i, { value: void 0 })), (r = _e({}, r, { value: void 0 })), (o = []);
        break;
      case "textarea":
        (i = cp(e, i)), (r = cp(e, r)), (o = []);
        break;
      default:
        typeof i.onClick != "function" && typeof r.onClick == "function" && (e.onclick = es);
    }
    dp(n, r);
    var a;
    n = null;
    for (l in i)
      if (!r.hasOwnProperty(l) && i.hasOwnProperty(l) && i[l] != null)
        if (l === "style") {
          var s = i[l];
          for (a in s) s.hasOwnProperty(a) && (n || (n = {}), (n[a] = ""));
        } else
          l !== "dangerouslySetInnerHTML" &&
            l !== "children" &&
            l !== "suppressContentEditableWarning" &&
            l !== "suppressHydrationWarning" &&
            l !== "autoFocus" &&
            (vo.hasOwnProperty(l) ? o || (o = []) : (o = o || []).push(l, null));
    for (l in r) {
      var u = r[l];
      if (
        ((s = i != null ? i[l] : void 0),
        r.hasOwnProperty(l) && u !== s && (u != null || s != null))
      )
        if (l === "style")
          if (s) {
            for (a in s)
              !s.hasOwnProperty(a) || (u && u.hasOwnProperty(a)) || (n || (n = {}), (n[a] = ""));
            for (a in u) u.hasOwnProperty(a) && s[a] !== u[a] && (n || (n = {}), (n[a] = u[a]));
          } else n || (o || (o = []), o.push(l, n)), (n = u);
        else
          l === "dangerouslySetInnerHTML"
            ? ((u = u ? u.__html : void 0),
              (s = s ? s.__html : void 0),
              u != null && s !== u && (o = o || []).push(l, u))
            : l === "children"
            ? (typeof u != "string" && typeof u != "number") || (o = o || []).push(l, "" + u)
            : l !== "suppressContentEditableWarning" &&
              l !== "suppressHydrationWarning" &&
              (vo.hasOwnProperty(l)
                ? (u != null && l === "onScroll" && he("scroll", e), o || s === u || (o = []))
                : (o = o || []).push(l, u));
    }
    n && (o = o || []).push("style", n);
    var l = o;
    (t.updateQueue = l) && (t.flags |= 4);
  }
};
XE = function (e, t, n, r) {
  n !== r && (t.flags |= 4);
};
function $i(e, t) {
  if (!ge)
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
function Ue(e) {
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
function QR(e, t, n) {
  var r = t.pendingProps;
  switch ((Og(t), t.tag)) {
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
      return Ue(t), null;
    case 1:
      return at(t.type) && ts(), Ue(t), null;
    case 3:
      return (
        (r = t.stateNode),
        pi(),
        pe(ot),
        pe(We),
        Vg(),
        r.pendingContext && ((r.context = r.pendingContext), (r.pendingContext = null)),
        (e === null || e.child === null) &&
          (ha(t)
            ? (t.flags |= 4)
            : e === null ||
              (e.memoizedState.isDehydrated && !(t.flags & 256)) ||
              ((t.flags |= 1024), qt !== null && (Wp(qt), (qt = null)))),
        Dp(e, t),
        Ue(t),
        null
      );
    case 5:
      Hg(t);
      var i = hr(Ro.current);
      if (((n = t.type), e !== null && t.stateNode != null))
        YE(e, t, n, r, i), e.ref !== t.ref && ((t.flags |= 512), (t.flags |= 2097152));
      else {
        if (!r) {
          if (t.stateNode === null) throw Error(j(166));
          return Ue(t), null;
        }
        if (((e = hr(Qt.current)), ha(t))) {
          (r = t.stateNode), (n = t.type);
          var o = t.memoizedProps;
          switch (((r[Kt] = t), (r[Co] = o), (e = (t.mode & 1) !== 0), n)) {
            case "dialog":
              he("cancel", r), he("close", r);
              break;
            case "iframe":
            case "object":
            case "embed":
              he("load", r);
              break;
            case "video":
            case "audio":
              for (i = 0; i < Xi.length; i++) he(Xi[i], r);
              break;
            case "source":
              he("error", r);
              break;
            case "img":
            case "image":
            case "link":
              he("error", r), he("load", r);
              break;
            case "details":
              he("toggle", r);
              break;
            case "input":
              nm(r, o), he("invalid", r);
              break;
            case "select":
              (r._wrapperState = { wasMultiple: !!o.multiple }), he("invalid", r);
              break;
            case "textarea":
              im(r, o), he("invalid", r);
          }
          dp(n, o), (i = null);
          for (var a in o)
            if (o.hasOwnProperty(a)) {
              var s = o[a];
              a === "children"
                ? typeof s == "string"
                  ? r.textContent !== s &&
                    (o.suppressHydrationWarning !== !0 && da(r.textContent, s, e),
                    (i = ["children", s]))
                  : typeof s == "number" &&
                    r.textContent !== "" + s &&
                    (o.suppressHydrationWarning !== !0 && da(r.textContent, s, e),
                    (i = ["children", "" + s]))
                : vo.hasOwnProperty(a) && s != null && a === "onScroll" && he("scroll", r);
            }
          switch (n) {
            case "input":
              ia(r), rm(r, o, !0);
              break;
            case "textarea":
              ia(r), om(r);
              break;
            case "select":
            case "option":
              break;
            default:
              typeof o.onClick == "function" && (r.onclick = es);
          }
          (r = i), (t.updateQueue = r), r !== null && (t.flags |= 4);
        } else {
          (a = i.nodeType === 9 ? i : i.ownerDocument),
            e === "http://www.w3.org/1999/xhtml" && (e = bS(n)),
            e === "http://www.w3.org/1999/xhtml"
              ? n === "script"
                ? ((e = a.createElement("div")),
                  (e.innerHTML = "<script></script>"),
                  (e = e.removeChild(e.firstChild)))
                : typeof r.is == "string"
                ? (e = a.createElement(n, { is: r.is }))
                : ((e = a.createElement(n)),
                  n === "select" &&
                    ((a = e), r.multiple ? (a.multiple = !0) : r.size && (a.size = r.size)))
              : (e = a.createElementNS(e, n)),
            (e[Kt] = t),
            (e[Co] = r),
            KE(e, t, !1, !1),
            (t.stateNode = e);
          e: {
            switch (((a = hp(n, r)), n)) {
              case "dialog":
                he("cancel", e), he("close", e), (i = r);
                break;
              case "iframe":
              case "object":
              case "embed":
                he("load", e), (i = r);
                break;
              case "video":
              case "audio":
                for (i = 0; i < Xi.length; i++) he(Xi[i], e);
                i = r;
                break;
              case "source":
                he("error", e), (i = r);
                break;
              case "img":
              case "image":
              case "link":
                he("error", e), he("load", e), (i = r);
                break;
              case "details":
                he("toggle", e), (i = r);
                break;
              case "input":
                nm(e, r), (i = sp(e, r)), he("invalid", e);
                break;
              case "option":
                i = r;
                break;
              case "select":
                (e._wrapperState = { wasMultiple: !!r.multiple }),
                  (i = _e({}, r, { value: void 0 })),
                  he("invalid", e);
                break;
              case "textarea":
                im(e, r), (i = cp(e, r)), he("invalid", e);
                break;
              default:
                i = r;
            }
            dp(n, i), (s = i);
            for (o in s)
              if (s.hasOwnProperty(o)) {
                var u = s[o];
                o === "style"
                  ? NS(e, u)
                  : o === "dangerouslySetInnerHTML"
                  ? ((u = u ? u.__html : void 0), u != null && kS(e, u))
                  : o === "children"
                  ? typeof u == "string"
                    ? (n !== "textarea" || u !== "") && mo(e, u)
                    : typeof u == "number" && mo(e, "" + u)
                  : o !== "suppressContentEditableWarning" &&
                    o !== "suppressHydrationWarning" &&
                    o !== "autoFocus" &&
                    (vo.hasOwnProperty(o)
                      ? u != null && o === "onScroll" && he("scroll", e)
                      : u != null && wg(e, o, u, a));
              }
            switch (n) {
              case "input":
                ia(e), rm(e, r, !1);
                break;
              case "textarea":
                ia(e), om(e);
                break;
              case "option":
                r.value != null && e.setAttribute("value", "" + Jn(r.value));
                break;
              case "select":
                (e.multiple = !!r.multiple),
                  (o = r.value),
                  o != null
                    ? ei(e, !!r.multiple, o, !1)
                    : r.defaultValue != null && ei(e, !!r.multiple, r.defaultValue, !0);
                break;
              default:
                typeof i.onClick == "function" && (e.onclick = es);
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
      return Ue(t), null;
    case 6:
      if (e && t.stateNode != null) XE(e, t, e.memoizedProps, r);
      else {
        if (typeof r != "string" && t.stateNode === null) throw Error(j(166));
        if (((n = hr(Ro.current)), hr(Qt.current), ha(t))) {
          if (
            ((r = t.stateNode),
            (n = t.memoizedProps),
            (r[Kt] = t),
            (o = r.nodeValue !== n) && ((e = ht), e !== null))
          )
            switch (e.tag) {
              case 3:
                da(r.nodeValue, n, (e.mode & 1) !== 0);
                break;
              case 5:
                e.memoizedProps.suppressHydrationWarning !== !0 &&
                  da(r.nodeValue, n, (e.mode & 1) !== 0);
            }
          o && (t.flags |= 4);
        } else
          (r = (n.nodeType === 9 ? n : n.ownerDocument).createTextNode(r)),
            (r[Kt] = t),
            (t.stateNode = r);
      }
      return Ue(t), null;
    case 13:
      if (
        (pe(me),
        (r = t.memoizedState),
        e === null || (e.memoizedState !== null && e.memoizedState.dehydrated !== null))
      ) {
        if (ge && dt !== null && t.mode & 1 && !(t.flags & 128))
          pE(), di(), (t.flags |= 98560), (o = !1);
        else if (((o = ha(t)), r !== null && r.dehydrated !== null)) {
          if (e === null) {
            if (!o) throw Error(j(318));
            if (((o = t.memoizedState), (o = o !== null ? o.dehydrated : null), !o))
              throw Error(j(317));
            o[Kt] = t;
          } else di(), !(t.flags & 128) && (t.memoizedState = null), (t.flags |= 4);
          Ue(t), (o = !1);
        } else qt !== null && (Wp(qt), (qt = null)), (o = !0);
        if (!o) return t.flags & 65536 ? t : null;
      }
      return t.flags & 128
        ? ((t.lanes = n), t)
        : ((r = r !== null),
          r !== (e !== null && e.memoizedState !== null) &&
            r &&
            ((t.child.flags |= 8192),
            t.mode & 1 && (e === null || me.current & 1 ? Ie === 0 && (Ie = 3) : nv())),
          t.updateQueue !== null && (t.flags |= 4),
          Ue(t),
          null);
    case 4:
      return pi(), Dp(e, t), e === null && bo(t.stateNode.containerInfo), Ue(t), null;
    case 10:
      return Dg(t.type._context), Ue(t), null;
    case 17:
      return at(t.type) && ts(), Ue(t), null;
    case 19:
      if ((pe(me), (o = t.memoizedState), o === null)) return Ue(t), null;
      if (((r = (t.flags & 128) !== 0), (a = o.rendering), a === null))
        if (r) $i(o, !1);
        else {
          if (Ie !== 0 || (e !== null && e.flags & 128))
            for (e = t.child; e !== null; ) {
              if (((a = us(e)), a !== null)) {
                for (
                  t.flags |= 128,
                    $i(o, !1),
                    r = a.updateQueue,
                    r !== null && ((t.updateQueue = r), (t.flags |= 4)),
                    t.subtreeFlags = 0,
                    r = n,
                    n = t.child;
                  n !== null;

                )
                  (o = n),
                    (e = r),
                    (o.flags &= 14680066),
                    (a = o.alternate),
                    a === null
                      ? ((o.childLanes = 0),
                        (o.lanes = e),
                        (o.child = null),
                        (o.subtreeFlags = 0),
                        (o.memoizedProps = null),
                        (o.memoizedState = null),
                        (o.updateQueue = null),
                        (o.dependencies = null),
                        (o.stateNode = null))
                      : ((o.childLanes = a.childLanes),
                        (o.lanes = a.lanes),
                        (o.child = a.child),
                        (o.subtreeFlags = 0),
                        (o.deletions = null),
                        (o.memoizedProps = a.memoizedProps),
                        (o.memoizedState = a.memoizedState),
                        (o.updateQueue = a.updateQueue),
                        (o.type = a.type),
                        (e = a.dependencies),
                        (o.dependencies =
                          e === null ? null : { lanes: e.lanes, firstContext: e.firstContext })),
                    (n = n.sibling);
                return ce(me, (me.current & 1) | 2), t.child;
              }
              e = e.sibling;
            }
          o.tail !== null &&
            ke() > vi &&
            ((t.flags |= 128), (r = !0), $i(o, !1), (t.lanes = 4194304));
        }
      else {
        if (!r)
          if (((e = us(a)), e !== null)) {
            if (
              ((t.flags |= 128),
              (r = !0),
              (n = e.updateQueue),
              n !== null && ((t.updateQueue = n), (t.flags |= 4)),
              $i(o, !0),
              o.tail === null && o.tailMode === "hidden" && !a.alternate && !ge)
            )
              return Ue(t), null;
          } else
            2 * ke() - o.renderingStartTime > vi &&
              n !== 1073741824 &&
              ((t.flags |= 128), (r = !0), $i(o, !1), (t.lanes = 4194304));
        o.isBackwards
          ? ((a.sibling = t.child), (t.child = a))
          : ((n = o.last), n !== null ? (n.sibling = a) : (t.child = a), (o.last = a));
      }
      return o.tail !== null
        ? ((t = o.tail),
          (o.rendering = t),
          (o.tail = t.sibling),
          (o.renderingStartTime = ke()),
          (t.sibling = null),
          (n = me.current),
          ce(me, r ? (n & 1) | 2 : n & 1),
          t)
        : (Ue(t), null);
    case 22:
    case 23:
      return (
        tv(),
        (r = t.memoizedState !== null),
        e !== null && (e.memoizedState !== null) !== r && (t.flags |= 8192),
        r && t.mode & 1
          ? ct & 1073741824 && (Ue(t), t.subtreeFlags & 6 && (t.flags |= 8192))
          : Ue(t),
        null
      );
    case 24:
      return null;
    case 25:
      return null;
  }
  throw Error(j(156, t.tag));
}
function ZR(e, t) {
  switch ((Og(t), t.tag)) {
    case 1:
      return (
        at(t.type) && ts(), (e = t.flags), e & 65536 ? ((t.flags = (e & -65537) | 128), t) : null
      );
    case 3:
      return (
        pi(),
        pe(ot),
        pe(We),
        Vg(),
        (e = t.flags),
        e & 65536 && !(e & 128) ? ((t.flags = (e & -65537) | 128), t) : null
      );
    case 5:
      return Hg(t), null;
    case 13:
      if ((pe(me), (e = t.memoizedState), e !== null && e.dehydrated !== null)) {
        if (t.alternate === null) throw Error(j(340));
        di();
      }
      return (e = t.flags), e & 65536 ? ((t.flags = (e & -65537) | 128), t) : null;
    case 19:
      return pe(me), null;
    case 4:
      return pi(), null;
    case 10:
      return Dg(t.type._context), null;
    case 22:
    case 23:
      return tv(), null;
    case 24:
      return null;
    default:
      return null;
  }
}
var va = !1,
  Ge = !1,
  JR = typeof WeakSet == "function" ? WeakSet : Set,
  V = null;
function Qr(e, t) {
  var n = e.ref;
  if (n !== null)
    if (typeof n == "function")
      try {
        n(null);
      } catch (r) {
        xe(e, t, r);
      }
    else n.current = null;
}
function Fp(e, t, n) {
  try {
    n();
  } catch (r) {
    xe(e, t, r);
  }
}
var Km = !1;
function eT(e, t) {
  if (((Ep = Qa), (e = tE()), Pg(e))) {
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
          var a = 0,
            s = -1,
            u = -1,
            l = 0,
            c = 0,
            f = e,
            d = null;
          t: for (;;) {
            for (
              var h;
              f !== n || (i !== 0 && f.nodeType !== 3) || (s = a + i),
                f !== o || (r !== 0 && f.nodeType !== 3) || (u = a + r),
                f.nodeType === 3 && (a += f.nodeValue.length),
                (h = f.firstChild) !== null;

            )
              (d = f), (f = h);
            for (;;) {
              if (f === e) break t;
              if (
                (d === n && ++l === i && (s = a),
                d === o && ++c === r && (u = a),
                (h = f.nextSibling) !== null)
              )
                break;
              (f = d), (d = f.parentNode);
            }
            f = h;
          }
          n = s === -1 || u === -1 ? null : { start: s, end: u };
        } else n = null;
      }
    n = n || { start: 0, end: 0 };
  } else n = null;
  for (bp = { focusedElem: e, selectionRange: n }, Qa = !1, V = t; V !== null; )
    if (((t = V), (e = t.child), (t.subtreeFlags & 1028) !== 0 && e !== null))
      (e.return = t), (V = e);
    else
      for (; V !== null; ) {
        t = V;
        try {
          var m = t.alternate;
          if (t.flags & 1024)
            switch (t.tag) {
              case 0:
              case 11:
              case 15:
                break;
              case 1:
                if (m !== null) {
                  var v = m.memoizedProps,
                    w = m.memoizedState,
                    p = t.stateNode,
                    g = p.getSnapshotBeforeUpdate(t.elementType === t.type ? v : At(t.type, v), w);
                  p.__reactInternalSnapshotBeforeUpdate = g;
                }
                break;
              case 3:
                var y = t.stateNode.containerInfo;
                y.nodeType === 1
                  ? (y.textContent = "")
                  : y.nodeType === 9 && y.documentElement && y.removeChild(y.documentElement);
                break;
              case 5:
              case 6:
              case 4:
              case 17:
                break;
              default:
                throw Error(j(163));
            }
        } catch (_) {
          xe(t, t.return, _);
        }
        if (((e = t.sibling), e !== null)) {
          (e.return = t.return), (V = e);
          break;
        }
        V = t.return;
      }
  return (m = Km), (Km = !1), m;
}
function ho(e, t, n) {
  var r = t.updateQueue;
  if (((r = r !== null ? r.lastEffect : null), r !== null)) {
    var i = (r = r.next);
    do {
      if ((i.tag & e) === e) {
        var o = i.destroy;
        (i.destroy = void 0), o !== void 0 && Fp(t, n, o);
      }
      i = i.next;
    } while (i !== r);
  }
}
function $s(e, t) {
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
function jp(e) {
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
function QE(e) {
  var t = e.alternate;
  t !== null && ((e.alternate = null), QE(t)),
    (e.child = null),
    (e.deletions = null),
    (e.sibling = null),
    e.tag === 5 &&
      ((t = e.stateNode),
      t !== null && (delete t[Kt], delete t[Co], delete t[Np], delete t[LR], delete t[zR])),
    (e.stateNode = null),
    (e.return = null),
    (e.dependencies = null),
    (e.memoizedProps = null),
    (e.memoizedState = null),
    (e.pendingProps = null),
    (e.stateNode = null),
    (e.updateQueue = null);
}
function ZE(e) {
  return e.tag === 5 || e.tag === 3 || e.tag === 4;
}
function Ym(e) {
  e: for (;;) {
    for (; e.sibling === null; ) {
      if (e.return === null || ZE(e.return)) return null;
      e = e.return;
    }
    for (e.sibling.return = e.return, e = e.sibling; e.tag !== 5 && e.tag !== 6 && e.tag !== 18; ) {
      if (e.flags & 2 || e.child === null || e.tag === 4) continue e;
      (e.child.return = e), (e = e.child);
    }
    if (!(e.flags & 2)) return e.stateNode;
  }
}
function Bp(e, t, n) {
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
          n != null || t.onclick !== null || (t.onclick = es));
  else if (r !== 4 && ((e = e.child), e !== null))
    for (Bp(e, t, n), e = e.sibling; e !== null; ) Bp(e, t, n), (e = e.sibling);
}
function Hp(e, t, n) {
  var r = e.tag;
  if (r === 5 || r === 6) (e = e.stateNode), t ? n.insertBefore(e, t) : n.appendChild(e);
  else if (r !== 4 && ((e = e.child), e !== null))
    for (Hp(e, t, n), e = e.sibling; e !== null; ) Hp(e, t, n), (e = e.sibling);
}
var De = null,
  Mt = !1;
function Rn(e, t, n) {
  for (n = n.child; n !== null; ) JE(e, t, n), (n = n.sibling);
}
function JE(e, t, n) {
  if (Xt && typeof Xt.onCommitFiberUnmount == "function")
    try {
      Xt.onCommitFiberUnmount(Is, n);
    } catch {}
  switch (n.tag) {
    case 5:
      Ge || Qr(n, t);
    case 6:
      var r = De,
        i = Mt;
      (De = null),
        Rn(e, t, n),
        (De = r),
        (Mt = i),
        De !== null &&
          (Mt
            ? ((e = De),
              (n = n.stateNode),
              e.nodeType === 8 ? e.parentNode.removeChild(n) : e.removeChild(n))
            : De.removeChild(n.stateNode));
      break;
    case 18:
      De !== null &&
        (Mt
          ? ((e = De),
            (n = n.stateNode),
            e.nodeType === 8 ? zu(e.parentNode, n) : e.nodeType === 1 && zu(e, n),
            xo(e))
          : zu(De, n.stateNode));
      break;
    case 4:
      (r = De),
        (i = Mt),
        (De = n.stateNode.containerInfo),
        (Mt = !0),
        Rn(e, t, n),
        (De = r),
        (Mt = i);
      break;
    case 0:
    case 11:
    case 14:
    case 15:
      if (!Ge && ((r = n.updateQueue), r !== null && ((r = r.lastEffect), r !== null))) {
        i = r = r.next;
        do {
          var o = i,
            a = o.destroy;
          (o = o.tag), a !== void 0 && (o & 2 || o & 4) && Fp(n, t, a), (i = i.next);
        } while (i !== r);
      }
      Rn(e, t, n);
      break;
    case 1:
      if (!Ge && (Qr(n, t), (r = n.stateNode), typeof r.componentWillUnmount == "function"))
        try {
          (r.props = n.memoizedProps), (r.state = n.memoizedState), r.componentWillUnmount();
        } catch (s) {
          xe(n, t, s);
        }
      Rn(e, t, n);
      break;
    case 21:
      Rn(e, t, n);
      break;
    case 22:
      n.mode & 1
        ? ((Ge = (r = Ge) || n.memoizedState !== null), Rn(e, t, n), (Ge = r))
        : Rn(e, t, n);
      break;
    default:
      Rn(e, t, n);
  }
}
function Xm(e) {
  var t = e.updateQueue;
  if (t !== null) {
    e.updateQueue = null;
    var n = e.stateNode;
    n === null && (n = e.stateNode = new JR()),
      t.forEach(function (r) {
        var i = lT.bind(null, e, r);
        n.has(r) || (n.add(r), r.then(i, i));
      });
  }
}
function It(e, t) {
  var n = t.deletions;
  if (n !== null)
    for (var r = 0; r < n.length; r++) {
      var i = n[r];
      try {
        var o = e,
          a = t,
          s = a;
        e: for (; s !== null; ) {
          switch (s.tag) {
            case 5:
              (De = s.stateNode), (Mt = !1);
              break e;
            case 3:
              (De = s.stateNode.containerInfo), (Mt = !0);
              break e;
            case 4:
              (De = s.stateNode.containerInfo), (Mt = !0);
              break e;
          }
          s = s.return;
        }
        if (De === null) throw Error(j(160));
        JE(o, a, i), (De = null), (Mt = !1);
        var u = i.alternate;
        u !== null && (u.return = null), (i.return = null);
      } catch (l) {
        xe(i, t, l);
      }
    }
  if (t.subtreeFlags & 12854) for (t = t.child; t !== null; ) eb(t, e), (t = t.sibling);
}
function eb(e, t) {
  var n = e.alternate,
    r = e.flags;
  switch (e.tag) {
    case 0:
    case 11:
    case 14:
    case 15:
      if ((It(t, e), Gt(e), r & 4)) {
        try {
          ho(3, e, e.return), $s(3, e);
        } catch (v) {
          xe(e, e.return, v);
        }
        try {
          ho(5, e, e.return);
        } catch (v) {
          xe(e, e.return, v);
        }
      }
      break;
    case 1:
      It(t, e), Gt(e), r & 512 && n !== null && Qr(n, n.return);
      break;
    case 5:
      if ((It(t, e), Gt(e), r & 512 && n !== null && Qr(n, n.return), e.flags & 32)) {
        var i = e.stateNode;
        try {
          mo(i, "");
        } catch (v) {
          xe(e, e.return, v);
        }
      }
      if (r & 4 && ((i = e.stateNode), i != null)) {
        var o = e.memoizedProps,
          a = n !== null ? n.memoizedProps : o,
          s = e.type,
          u = e.updateQueue;
        if (((e.updateQueue = null), u !== null))
          try {
            s === "input" && o.type === "radio" && o.name != null && SS(i, o), hp(s, a);
            var l = hp(s, o);
            for (a = 0; a < u.length; a += 2) {
              var c = u[a],
                f = u[a + 1];
              c === "style"
                ? NS(i, f)
                : c === "dangerouslySetInnerHTML"
                ? kS(i, f)
                : c === "children"
                ? mo(i, f)
                : wg(i, c, f, l);
            }
            switch (s) {
              case "input":
                up(i, o);
                break;
              case "textarea":
                ES(i, o);
                break;
              case "select":
                var d = i._wrapperState.wasMultiple;
                i._wrapperState.wasMultiple = !!o.multiple;
                var h = o.value;
                h != null
                  ? ei(i, !!o.multiple, h, !1)
                  : d !== !!o.multiple &&
                    (o.defaultValue != null
                      ? ei(i, !!o.multiple, o.defaultValue, !0)
                      : ei(i, !!o.multiple, o.multiple ? [] : "", !1));
            }
            i[Co] = o;
          } catch (v) {
            xe(e, e.return, v);
          }
      }
      break;
    case 6:
      if ((It(t, e), Gt(e), r & 4)) {
        if (e.stateNode === null) throw Error(j(162));
        (i = e.stateNode), (o = e.memoizedProps);
        try {
          i.nodeValue = o;
        } catch (v) {
          xe(e, e.return, v);
        }
      }
      break;
    case 3:
      if ((It(t, e), Gt(e), r & 4 && n !== null && n.memoizedState.isDehydrated))
        try {
          xo(t.containerInfo);
        } catch (v) {
          xe(e, e.return, v);
        }
      break;
    case 4:
      It(t, e), Gt(e);
      break;
    case 13:
      It(t, e),
        Gt(e),
        (i = e.child),
        i.flags & 8192 &&
          ((o = i.memoizedState !== null),
          (i.stateNode.isHidden = o),
          !o || (i.alternate !== null && i.alternate.memoizedState !== null) || (Jg = ke())),
        r & 4 && Xm(e);
      break;
    case 22:
      if (
        ((c = n !== null && n.memoizedState !== null),
        e.mode & 1 ? ((Ge = (l = Ge) || c), It(t, e), (Ge = l)) : It(t, e),
        Gt(e),
        r & 8192)
      ) {
        if (((l = e.memoizedState !== null), (e.stateNode.isHidden = l) && !c && e.mode & 1))
          for (V = e, c = e.child; c !== null; ) {
            for (f = V = c; V !== null; ) {
              switch (((d = V), (h = d.child), d.tag)) {
                case 0:
                case 11:
                case 14:
                case 15:
                  ho(4, d, d.return);
                  break;
                case 1:
                  Qr(d, d.return);
                  var m = d.stateNode;
                  if (typeof m.componentWillUnmount == "function") {
                    (r = d), (n = d.return);
                    try {
                      (t = r),
                        (m.props = t.memoizedProps),
                        (m.state = t.memoizedState),
                        m.componentWillUnmount();
                    } catch (v) {
                      xe(r, n, v);
                    }
                  }
                  break;
                case 5:
                  Qr(d, d.return);
                  break;
                case 22:
                  if (d.memoizedState !== null) {
                    Zm(f);
                    continue;
                  }
              }
              h !== null ? ((h.return = d), (V = h)) : Zm(f);
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
                    : ((s = f.stateNode),
                      (u = f.memoizedProps.style),
                      (a = u != null && u.hasOwnProperty("display") ? u.display : null),
                      (s.style.display = CS("display", a)));
              } catch (v) {
                xe(e, e.return, v);
              }
            }
          } else if (f.tag === 6) {
            if (c === null)
              try {
                f.stateNode.nodeValue = l ? "" : f.memoizedProps;
              } catch (v) {
                xe(e, e.return, v);
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
      It(t, e), Gt(e), r & 4 && Xm(e);
      break;
    case 21:
      break;
    default:
      It(t, e), Gt(e);
  }
}
function Gt(e) {
  var t = e.flags;
  if (t & 2) {
    try {
      e: {
        for (var n = e.return; n !== null; ) {
          if (ZE(n)) {
            var r = n;
            break e;
          }
          n = n.return;
        }
        throw Error(j(160));
      }
      switch (r.tag) {
        case 5:
          var i = r.stateNode;
          r.flags & 32 && (mo(i, ""), (r.flags &= -33));
          var o = Ym(e);
          Hp(e, o, i);
          break;
        case 3:
        case 4:
          var a = r.stateNode.containerInfo,
            s = Ym(e);
          Bp(e, s, a);
          break;
        default:
          throw Error(j(161));
      }
    } catch (u) {
      xe(e, e.return, u);
    }
    e.flags &= -3;
  }
  t & 4096 && (e.flags &= -4097);
}
function tT(e, t, n) {
  (V = e), tb(e);
}
function tb(e, t, n) {
  for (var r = (e.mode & 1) !== 0; V !== null; ) {
    var i = V,
      o = i.child;
    if (i.tag === 22 && r) {
      var a = i.memoizedState !== null || va;
      if (!a) {
        var s = i.alternate,
          u = (s !== null && s.memoizedState !== null) || Ge;
        s = va;
        var l = Ge;
        if (((va = a), (Ge = u) && !l))
          for (V = i; V !== null; )
            (a = V),
              (u = a.child),
              a.tag === 22 && a.memoizedState !== null
                ? Jm(i)
                : u !== null
                ? ((u.return = a), (V = u))
                : Jm(i);
        for (; o !== null; ) (V = o), tb(o), (o = o.sibling);
        (V = i), (va = s), (Ge = l);
      }
      Qm(e);
    } else i.subtreeFlags & 8772 && o !== null ? ((o.return = i), (V = o)) : Qm(e);
  }
}
function Qm(e) {
  for (; V !== null; ) {
    var t = V;
    if (t.flags & 8772) {
      var n = t.alternate;
      try {
        if (t.flags & 8772)
          switch (t.tag) {
            case 0:
            case 11:
            case 15:
              Ge || $s(5, t);
              break;
            case 1:
              var r = t.stateNode;
              if (t.flags & 4 && !Ge)
                if (n === null) r.componentDidMount();
                else {
                  var i = t.elementType === t.type ? n.memoizedProps : At(t.type, n.memoizedProps);
                  r.componentDidUpdate(i, n.memoizedState, r.__reactInternalSnapshotBeforeUpdate);
                }
              var o = t.updateQueue;
              o !== null && Om(t, o, r);
              break;
            case 3:
              var a = t.updateQueue;
              if (a !== null) {
                if (((n = null), t.child !== null))
                  switch (t.child.tag) {
                    case 5:
                      n = t.child.stateNode;
                      break;
                    case 1:
                      n = t.child.stateNode;
                  }
                Om(t, a, n);
              }
              break;
            case 5:
              var s = t.stateNode;
              if (n === null && t.flags & 4) {
                n = s;
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
                    f !== null && xo(f);
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
              throw Error(j(163));
          }
        Ge || (t.flags & 512 && jp(t));
      } catch (d) {
        xe(t, t.return, d);
      }
    }
    if (t === e) {
      V = null;
      break;
    }
    if (((n = t.sibling), n !== null)) {
      (n.return = t.return), (V = n);
      break;
    }
    V = t.return;
  }
}
function Zm(e) {
  for (; V !== null; ) {
    var t = V;
    if (t === e) {
      V = null;
      break;
    }
    var n = t.sibling;
    if (n !== null) {
      (n.return = t.return), (V = n);
      break;
    }
    V = t.return;
  }
}
function Jm(e) {
  for (; V !== null; ) {
    var t = V;
    try {
      switch (t.tag) {
        case 0:
        case 11:
        case 15:
          var n = t.return;
          try {
            $s(4, t);
          } catch (u) {
            xe(t, n, u);
          }
          break;
        case 1:
          var r = t.stateNode;
          if (typeof r.componentDidMount == "function") {
            var i = t.return;
            try {
              r.componentDidMount();
            } catch (u) {
              xe(t, i, u);
            }
          }
          var o = t.return;
          try {
            jp(t);
          } catch (u) {
            xe(t, o, u);
          }
          break;
        case 5:
          var a = t.return;
          try {
            jp(t);
          } catch (u) {
            xe(t, a, u);
          }
      }
    } catch (u) {
      xe(t, t.return, u);
    }
    if (t === e) {
      V = null;
      break;
    }
    var s = t.sibling;
    if (s !== null) {
      (s.return = t.return), (V = s);
      break;
    }
    V = t.return;
  }
}
var nT = Math.ceil,
  fs = bn.ReactCurrentDispatcher,
  Qg = bn.ReactCurrentOwner,
  Et = bn.ReactCurrentBatchConfig,
  ae = 0,
  Le = null,
  Ce = null,
  Fe = 0,
  ct = 0,
  Zr = rr(0),
  Ie = 0,
  Mo = null,
  br = 0,
  Ds = 0,
  Zg = 0,
  po = null,
  nt = null,
  Jg = 0,
  vi = 1 / 0,
  un = null,
  ds = !1,
  Vp = null,
  Kn = null,
  ma = !1,
  Bn = null,
  hs = 0,
  go = 0,
  Up = null,
  Da = -1,
  Fa = 0;
function Qe() {
  return ae & 6 ? ke() : Da !== -1 ? Da : (Da = ke());
}
function Yn(e) {
  return e.mode & 1
    ? ae & 2 && Fe !== 0
      ? Fe & -Fe
      : DR.transition !== null
      ? (Fa === 0 && (Fa = DS()), Fa)
      : ((e = le), e !== 0 || ((e = window.event), (e = e === void 0 ? 16 : GS(e.type))), e)
    : 1;
}
function zt(e, t, n, r) {
  if (50 < go) throw ((go = 0), (Up = null), Error(j(185)));
  Ho(e, n, r),
    (!(ae & 2) || e !== Le) &&
      (e === Le && (!(ae & 2) && (Ds |= n), Ie === 4 && $n(e, Fe)),
      st(e, r),
      n === 1 && ae === 0 && !(t.mode & 1) && ((vi = ke() + 500), Os && ir()));
}
function st(e, t) {
  var n = e.callbackNode;
  DN(e, t);
  var r = Xa(e, e === Le ? Fe : 0);
  if (r === 0) n !== null && um(n), (e.callbackNode = null), (e.callbackPriority = 0);
  else if (((t = r & -r), e.callbackPriority !== t)) {
    if ((n != null && um(n), t === 1))
      e.tag === 0 ? $R(ey.bind(null, e)) : fE(ey.bind(null, e)),
        qR(function () {
          !(ae & 6) && ir();
        }),
        (n = null);
    else {
      switch (FS(r)) {
        case 1:
          n = kg;
          break;
        case 4:
          n = zS;
          break;
        case 16:
          n = Ya;
          break;
        case 536870912:
          n = $S;
          break;
        default:
          n = Ya;
      }
      n = lb(n, nb.bind(null, e));
    }
    (e.callbackPriority = t), (e.callbackNode = n);
  }
}
function nb(e, t) {
  if (((Da = -1), (Fa = 0), ae & 6)) throw Error(j(327));
  var n = e.callbackNode;
  if (oi() && e.callbackNode !== n) return null;
  var r = Xa(e, e === Le ? Fe : 0);
  if (r === 0) return null;
  if (r & 30 || r & e.expiredLanes || t) t = ps(e, r);
  else {
    t = r;
    var i = ae;
    ae |= 2;
    var o = ib();
    (Le !== e || Fe !== t) && ((un = null), (vi = ke() + 500), mr(e, t));
    do
      try {
        oT();
        break;
      } catch (s) {
        rb(e, s);
      }
    while (!0);
    $g(), (fs.current = o), (ae = i), Ce !== null ? (t = 0) : ((Le = null), (Fe = 0), (t = Ie));
  }
  if (t !== 0) {
    if ((t === 2 && ((i = yp(e)), i !== 0 && ((r = i), (t = Gp(e, i)))), t === 1))
      throw ((n = Mo), mr(e, 0), $n(e, r), st(e, ke()), n);
    if (t === 6) $n(e, r);
    else {
      if (
        ((i = e.current.alternate),
        !(r & 30) &&
          !rT(i) &&
          ((t = ps(e, r)), t === 2 && ((o = yp(e)), o !== 0 && ((r = o), (t = Gp(e, o)))), t === 1))
      )
        throw ((n = Mo), mr(e, 0), $n(e, r), st(e, ke()), n);
      switch (((e.finishedWork = i), (e.finishedLanes = r), t)) {
        case 0:
        case 1:
          throw Error(j(345));
        case 2:
          lr(e, nt, un);
          break;
        case 3:
          if (($n(e, r), (r & 130023424) === r && ((t = Jg + 500 - ke()), 10 < t))) {
            if (Xa(e, 0) !== 0) break;
            if (((i = e.suspendedLanes), (i & r) !== r)) {
              Qe(), (e.pingedLanes |= e.suspendedLanes & i);
              break;
            }
            e.timeoutHandle = Cp(lr.bind(null, e, nt, un), t);
            break;
          }
          lr(e, nt, un);
          break;
        case 4:
          if (($n(e, r), (r & 4194240) === r)) break;
          for (t = e.eventTimes, i = -1; 0 < r; ) {
            var a = 31 - Lt(r);
            (o = 1 << a), (a = t[a]), a > i && (i = a), (r &= ~o);
          }
          if (
            ((r = i),
            (r = ke() - r),
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
                : 1960 * nT(r / 1960)) - r),
            10 < r)
          ) {
            e.timeoutHandle = Cp(lr.bind(null, e, nt, un), r);
            break;
          }
          lr(e, nt, un);
          break;
        case 5:
          lr(e, nt, un);
          break;
        default:
          throw Error(j(329));
      }
    }
  }
  return st(e, ke()), e.callbackNode === n ? nb.bind(null, e) : null;
}
function Gp(e, t) {
  var n = po;
  return (
    e.current.memoizedState.isDehydrated && (mr(e, t).flags |= 256),
    (e = ps(e, t)),
    e !== 2 && ((t = nt), (nt = n), t !== null && Wp(t)),
    e
  );
}
function Wp(e) {
  nt === null ? (nt = e) : nt.push.apply(nt, e);
}
function rT(e) {
  for (var t = e; ; ) {
    if (t.flags & 16384) {
      var n = t.updateQueue;
      if (n !== null && ((n = n.stores), n !== null))
        for (var r = 0; r < n.length; r++) {
          var i = n[r],
            o = i.getSnapshot;
          i = i.value;
          try {
            if (!Dt(o(), i)) return !1;
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
function $n(e, t) {
  for (
    t &= ~Zg, t &= ~Ds, e.suspendedLanes |= t, e.pingedLanes &= ~t, e = e.expirationTimes;
    0 < t;

  ) {
    var n = 31 - Lt(t),
      r = 1 << n;
    (e[n] = -1), (t &= ~r);
  }
}
function ey(e) {
  if (ae & 6) throw Error(j(327));
  oi();
  var t = Xa(e, 0);
  if (!(t & 1)) return st(e, ke()), null;
  var n = ps(e, t);
  if (e.tag !== 0 && n === 2) {
    var r = yp(e);
    r !== 0 && ((t = r), (n = Gp(e, r)));
  }
  if (n === 1) throw ((n = Mo), mr(e, 0), $n(e, t), st(e, ke()), n);
  if (n === 6) throw Error(j(345));
  return (
    (e.finishedWork = e.current.alternate), (e.finishedLanes = t), lr(e, nt, un), st(e, ke()), null
  );
}
function ev(e, t) {
  var n = ae;
  ae |= 1;
  try {
    return e(t);
  } finally {
    (ae = n), ae === 0 && ((vi = ke() + 500), Os && ir());
  }
}
function kr(e) {
  Bn !== null && Bn.tag === 0 && !(ae & 6) && oi();
  var t = ae;
  ae |= 1;
  var n = Et.transition,
    r = le;
  try {
    if (((Et.transition = null), (le = 1), e)) return e();
  } finally {
    (le = r), (Et.transition = n), (ae = t), !(ae & 6) && ir();
  }
}
function tv() {
  (ct = Zr.current), pe(Zr);
}
function mr(e, t) {
  (e.finishedWork = null), (e.finishedLanes = 0);
  var n = e.timeoutHandle;
  if ((n !== -1 && ((e.timeoutHandle = -1), PR(n)), Ce !== null))
    for (n = Ce.return; n !== null; ) {
      var r = n;
      switch ((Og(r), r.tag)) {
        case 1:
          (r = r.type.childContextTypes), r != null && ts();
          break;
        case 3:
          pi(), pe(ot), pe(We), Vg();
          break;
        case 5:
          Hg(r);
          break;
        case 4:
          pi();
          break;
        case 13:
          pe(me);
          break;
        case 19:
          pe(me);
          break;
        case 10:
          Dg(r.type._context);
          break;
        case 22:
        case 23:
          tv();
      }
      n = n.return;
    }
  if (
    ((Le = e),
    (Ce = e = Xn(e.current, null)),
    (Fe = ct = t),
    (Ie = 0),
    (Mo = null),
    (Zg = Ds = br = 0),
    (nt = po = null),
    dr !== null)
  ) {
    for (t = 0; t < dr.length; t++)
      if (((n = dr[t]), (r = n.interleaved), r !== null)) {
        n.interleaved = null;
        var i = r.next,
          o = n.pending;
        if (o !== null) {
          var a = o.next;
          (o.next = i), (r.next = a);
        }
        n.pending = r;
      }
    dr = null;
  }
  return e;
}
function rb(e, t) {
  do {
    var n = Ce;
    try {
      if (($g(), (La.current = cs), ls)) {
        for (var r = ye.memoizedState; r !== null; ) {
          var i = r.queue;
          i !== null && (i.pending = null), (r = r.next);
        }
        ls = !1;
      }
      if (
        ((Er = 0),
        (Oe = Te = ye = null),
        (fo = !1),
        (To = 0),
        (Qg.current = null),
        n === null || n.return === null)
      ) {
        (Ie = 1), (Mo = t), (Ce = null);
        break;
      }
      e: {
        var o = e,
          a = n.return,
          s = n,
          u = t;
        if (
          ((t = Fe),
          (s.flags |= 32768),
          u !== null && typeof u == "object" && typeof u.then == "function")
        ) {
          var l = u,
            c = s,
            f = c.tag;
          if (!(c.mode & 1) && (f === 0 || f === 11 || f === 15)) {
            var d = c.alternate;
            d
              ? ((c.updateQueue = d.updateQueue),
                (c.memoizedState = d.memoizedState),
                (c.lanes = d.lanes))
              : ((c.updateQueue = null), (c.memoizedState = null));
          }
          var h = jm(a);
          if (h !== null) {
            (h.flags &= -257), Bm(h, a, s, o, t), h.mode & 1 && Fm(o, l, t), (t = h), (u = l);
            var m = t.updateQueue;
            if (m === null) {
              var v = new Set();
              v.add(u), (t.updateQueue = v);
            } else m.add(u);
            break e;
          } else {
            if (!(t & 1)) {
              Fm(o, l, t), nv();
              break e;
            }
            u = Error(j(426));
          }
        } else if (ge && s.mode & 1) {
          var w = jm(a);
          if (w !== null) {
            !(w.flags & 65536) && (w.flags |= 256), Bm(w, a, s, o, t), Lg(gi(u, s));
            break e;
          }
        }
        (o = u = gi(u, s)), Ie !== 4 && (Ie = 2), po === null ? (po = [o]) : po.push(o), (o = a);
        do {
          switch (o.tag) {
            case 3:
              (o.flags |= 65536), (t &= -t), (o.lanes |= t);
              var p = FE(o, u, t);
              qm(o, p);
              break e;
            case 1:
              s = u;
              var g = o.type,
                y = o.stateNode;
              if (
                !(o.flags & 128) &&
                (typeof g.getDerivedStateFromError == "function" ||
                  (y !== null &&
                    typeof y.componentDidCatch == "function" &&
                    (Kn === null || !Kn.has(y))))
              ) {
                (o.flags |= 65536), (t &= -t), (o.lanes |= t);
                var _ = jE(o, s, t);
                qm(o, _);
                break e;
              }
          }
          o = o.return;
        } while (o !== null);
      }
      ab(n);
    } catch (S) {
      (t = S), Ce === n && n !== null && (Ce = n = n.return);
      continue;
    }
    break;
  } while (!0);
}
function ib() {
  var e = fs.current;
  return (fs.current = cs), e === null ? cs : e;
}
function nv() {
  (Ie === 0 || Ie === 3 || Ie === 2) && (Ie = 4),
    Le === null || (!(br & 268435455) && !(Ds & 268435455)) || $n(Le, Fe);
}
function ps(e, t) {
  var n = ae;
  ae |= 2;
  var r = ib();
  (Le !== e || Fe !== t) && ((un = null), mr(e, t));
  do
    try {
      iT();
      break;
    } catch (i) {
      rb(e, i);
    }
  while (!0);
  if (($g(), (ae = n), (fs.current = r), Ce !== null)) throw Error(j(261));
  return (Le = null), (Fe = 0), Ie;
}
function iT() {
  for (; Ce !== null; ) ob(Ce);
}
function oT() {
  for (; Ce !== null && !IN(); ) ob(Ce);
}
function ob(e) {
  var t = ub(e.alternate, e, ct);
  (e.memoizedProps = e.pendingProps), t === null ? ab(e) : (Ce = t), (Qg.current = null);
}
function ab(e) {
  var t = e;
  do {
    var n = t.alternate;
    if (((e = t.return), t.flags & 32768)) {
      if (((n = ZR(n, t)), n !== null)) {
        (n.flags &= 32767), (Ce = n);
        return;
      }
      if (e !== null) (e.flags |= 32768), (e.subtreeFlags = 0), (e.deletions = null);
      else {
        (Ie = 6), (Ce = null);
        return;
      }
    } else if (((n = QR(n, t, ct)), n !== null)) {
      Ce = n;
      return;
    }
    if (((t = t.sibling), t !== null)) {
      Ce = t;
      return;
    }
    Ce = t = e;
  } while (t !== null);
  Ie === 0 && (Ie = 5);
}
function lr(e, t, n) {
  var r = le,
    i = Et.transition;
  try {
    (Et.transition = null), (le = 1), aT(e, t, n, r);
  } finally {
    (Et.transition = i), (le = r);
  }
  return null;
}
function aT(e, t, n, r) {
  do oi();
  while (Bn !== null);
  if (ae & 6) throw Error(j(327));
  n = e.finishedWork;
  var i = e.finishedLanes;
  if (n === null) return null;
  if (((e.finishedWork = null), (e.finishedLanes = 0), n === e.current)) throw Error(j(177));
  (e.callbackNode = null), (e.callbackPriority = 0);
  var o = n.lanes | n.childLanes;
  if (
    (FN(e, o),
    e === Le && ((Ce = Le = null), (Fe = 0)),
    (!(n.subtreeFlags & 2064) && !(n.flags & 2064)) ||
      ma ||
      ((ma = !0),
      lb(Ya, function () {
        return oi(), null;
      })),
    (o = (n.flags & 15990) !== 0),
    n.subtreeFlags & 15990 || o)
  ) {
    (o = Et.transition), (Et.transition = null);
    var a = le;
    le = 1;
    var s = ae;
    (ae |= 4),
      (Qg.current = null),
      eT(e, n),
      eb(n, e),
      CR(bp),
      (Qa = !!Ep),
      (bp = Ep = null),
      (e.current = n),
      tT(n),
      AN(),
      (ae = s),
      (le = a),
      (Et.transition = o);
  } else e.current = n;
  if (
    (ma && ((ma = !1), (Bn = e), (hs = i)),
    (o = e.pendingLanes),
    o === 0 && (Kn = null),
    qN(n.stateNode),
    st(e, ke()),
    t !== null)
  )
    for (r = e.onRecoverableError, n = 0; n < t.length; n++)
      (i = t[n]), r(i.value, { componentStack: i.stack, digest: i.digest });
  if (ds) throw ((ds = !1), (e = Vp), (Vp = null), e);
  return (
    hs & 1 && e.tag !== 0 && oi(),
    (o = e.pendingLanes),
    o & 1 ? (e === Up ? go++ : ((go = 0), (Up = e))) : (go = 0),
    ir(),
    null
  );
}
function oi() {
  if (Bn !== null) {
    var e = FS(hs),
      t = Et.transition,
      n = le;
    try {
      if (((Et.transition = null), (le = 16 > e ? 16 : e), Bn === null)) var r = !1;
      else {
        if (((e = Bn), (Bn = null), (hs = 0), ae & 6)) throw Error(j(331));
        var i = ae;
        for (ae |= 4, V = e.current; V !== null; ) {
          var o = V,
            a = o.child;
          if (V.flags & 16) {
            var s = o.deletions;
            if (s !== null) {
              for (var u = 0; u < s.length; u++) {
                var l = s[u];
                for (V = l; V !== null; ) {
                  var c = V;
                  switch (c.tag) {
                    case 0:
                    case 11:
                    case 15:
                      ho(8, c, o);
                  }
                  var f = c.child;
                  if (f !== null) (f.return = c), (V = f);
                  else
                    for (; V !== null; ) {
                      c = V;
                      var d = c.sibling,
                        h = c.return;
                      if ((QE(c), c === l)) {
                        V = null;
                        break;
                      }
                      if (d !== null) {
                        (d.return = h), (V = d);
                        break;
                      }
                      V = h;
                    }
                }
              }
              var m = o.alternate;
              if (m !== null) {
                var v = m.child;
                if (v !== null) {
                  m.child = null;
                  do {
                    var w = v.sibling;
                    (v.sibling = null), (v = w);
                  } while (v !== null);
                }
              }
              V = o;
            }
          }
          if (o.subtreeFlags & 2064 && a !== null) (a.return = o), (V = a);
          else
            e: for (; V !== null; ) {
              if (((o = V), o.flags & 2048))
                switch (o.tag) {
                  case 0:
                  case 11:
                  case 15:
                    ho(9, o, o.return);
                }
              var p = o.sibling;
              if (p !== null) {
                (p.return = o.return), (V = p);
                break e;
              }
              V = o.return;
            }
        }
        var g = e.current;
        for (V = g; V !== null; ) {
          a = V;
          var y = a.child;
          if (a.subtreeFlags & 2064 && y !== null) (y.return = a), (V = y);
          else
            e: for (a = g; V !== null; ) {
              if (((s = V), s.flags & 2048))
                try {
                  switch (s.tag) {
                    case 0:
                    case 11:
                    case 15:
                      $s(9, s);
                  }
                } catch (S) {
                  xe(s, s.return, S);
                }
              if (s === a) {
                V = null;
                break e;
              }
              var _ = s.sibling;
              if (_ !== null) {
                (_.return = s.return), (V = _);
                break e;
              }
              V = s.return;
            }
        }
        if (((ae = i), ir(), Xt && typeof Xt.onPostCommitFiberRoot == "function"))
          try {
            Xt.onPostCommitFiberRoot(Is, e);
          } catch {}
        r = !0;
      }
      return r;
    } finally {
      (le = n), (Et.transition = t);
    }
  }
  return !1;
}
function ty(e, t, n) {
  (t = gi(n, t)),
    (t = FE(e, t, 1)),
    (e = Wn(e, t, 1)),
    (t = Qe()),
    e !== null && (Ho(e, 1, t), st(e, t));
}
function xe(e, t, n) {
  if (e.tag === 3) ty(e, e, n);
  else
    for (; t !== null; ) {
      if (t.tag === 3) {
        ty(t, e, n);
        break;
      } else if (t.tag === 1) {
        var r = t.stateNode;
        if (
          typeof t.type.getDerivedStateFromError == "function" ||
          (typeof r.componentDidCatch == "function" && (Kn === null || !Kn.has(r)))
        ) {
          (e = gi(n, e)),
            (e = jE(t, e, 1)),
            (t = Wn(t, e, 1)),
            (e = Qe()),
            t !== null && (Ho(t, 1, e), st(t, e));
          break;
        }
      }
      t = t.return;
    }
}
function sT(e, t, n) {
  var r = e.pingCache;
  r !== null && r.delete(t),
    (t = Qe()),
    (e.pingedLanes |= e.suspendedLanes & n),
    Le === e &&
      (Fe & n) === n &&
      (Ie === 4 || (Ie === 3 && (Fe & 130023424) === Fe && 500 > ke() - Jg) ? mr(e, 0) : (Zg |= n)),
    st(e, t);
}
function sb(e, t) {
  t === 0 && (e.mode & 1 ? ((t = sa), (sa <<= 1), !(sa & 130023424) && (sa = 4194304)) : (t = 1));
  var n = Qe();
  (e = _n(e, t)), e !== null && (Ho(e, t, n), st(e, n));
}
function uT(e) {
  var t = e.memoizedState,
    n = 0;
  t !== null && (n = t.retryLane), sb(e, n);
}
function lT(e, t) {
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
      throw Error(j(314));
  }
  r !== null && r.delete(t), sb(e, n);
}
var ub;
ub = function (e, t, n) {
  if (e !== null)
    if (e.memoizedProps !== t.pendingProps || ot.current) rt = !0;
    else {
      if (!(e.lanes & n) && !(t.flags & 128)) return (rt = !1), XR(e, t, n);
      rt = !!(e.flags & 131072);
    }
  else (rt = !1), ge && t.flags & 1048576 && dE(t, is, t.index);
  switch (((t.lanes = 0), t.tag)) {
    case 2:
      var r = t.type;
      $a(e, t), (e = t.pendingProps);
      var i = fi(t, We.current);
      ii(t, n), (i = Gg(null, t, r, e, i, n));
      var o = Wg();
      return (
        (t.flags |= 1),
        typeof i == "object" && i !== null && typeof i.render == "function" && i.$$typeof === void 0
          ? ((t.tag = 1),
            (t.memoizedState = null),
            (t.updateQueue = null),
            at(r) ? ((o = !0), ns(t)) : (o = !1),
            (t.memoizedState = i.state !== null && i.state !== void 0 ? i.state : null),
            jg(t),
            (i.updater = zs),
            (t.stateNode = i),
            (i._reactInternals = t),
            Pp(t, r, e, n),
            (t = Lp(null, t, r, !0, o, n)))
          : ((t.tag = 0), ge && o && qg(t), Xe(null, t, i, n), (t = t.child)),
        t
      );
    case 16:
      r = t.elementType;
      e: {
        switch (
          ($a(e, t),
          (e = t.pendingProps),
          (i = r._init),
          (r = i(r._payload)),
          (t.type = r),
          (i = t.tag = fT(r)),
          (e = At(r, e)),
          i)
        ) {
          case 0:
            t = Op(null, t, r, e, n);
            break e;
          case 1:
            t = Um(null, t, r, e, n);
            break e;
          case 11:
            t = Hm(null, t, r, e, n);
            break e;
          case 14:
            t = Vm(null, t, r, At(r.type, e), n);
            break e;
        }
        throw Error(j(306, r, ""));
      }
      return t;
    case 0:
      return (
        (r = t.type),
        (i = t.pendingProps),
        (i = t.elementType === r ? i : At(r, i)),
        Op(e, t, r, i, n)
      );
    case 1:
      return (
        (r = t.type),
        (i = t.pendingProps),
        (i = t.elementType === r ? i : At(r, i)),
        Um(e, t, r, i, n)
      );
    case 3:
      e: {
        if ((UE(t), e === null)) throw Error(j(387));
        (r = t.pendingProps), (o = t.memoizedState), (i = o.element), yE(e, t), ss(t, r, null, n);
        var a = t.memoizedState;
        if (((r = a.element), o.isDehydrated))
          if (
            ((o = {
              element: r,
              isDehydrated: !1,
              cache: a.cache,
              pendingSuspenseBoundaries: a.pendingSuspenseBoundaries,
              transitions: a.transitions,
            }),
            (t.updateQueue.baseState = o),
            (t.memoizedState = o),
            t.flags & 256)
          ) {
            (i = gi(Error(j(423)), t)), (t = Gm(e, t, r, n, i));
            break e;
          } else if (r !== i) {
            (i = gi(Error(j(424)), t)), (t = Gm(e, t, r, n, i));
            break e;
          } else
            for (
              dt = Gn(t.stateNode.containerInfo.firstChild),
                ht = t,
                ge = !0,
                qt = null,
                n = vE(t, null, r, n),
                t.child = n;
              n;

            )
              (n.flags = (n.flags & -3) | 4096), (n = n.sibling);
        else {
          if ((di(), r === i)) {
            t = wn(e, t, n);
            break e;
          }
          Xe(e, t, r, n);
        }
        t = t.child;
      }
      return t;
    case 5:
      return (
        _E(t),
        e === null && Ip(t),
        (r = t.type),
        (i = t.pendingProps),
        (o = e !== null ? e.memoizedProps : null),
        (a = i.children),
        kp(r, i) ? (a = null) : o !== null && kp(r, o) && (t.flags |= 32),
        VE(e, t),
        Xe(e, t, a, n),
        t.child
      );
    case 6:
      return e === null && Ip(t), null;
    case 13:
      return GE(e, t, n);
    case 4:
      return (
        Bg(t, t.stateNode.containerInfo),
        (r = t.pendingProps),
        e === null ? (t.child = hi(t, null, r, n)) : Xe(e, t, r, n),
        t.child
      );
    case 11:
      return (
        (r = t.type),
        (i = t.pendingProps),
        (i = t.elementType === r ? i : At(r, i)),
        Hm(e, t, r, i, n)
      );
    case 7:
      return Xe(e, t, t.pendingProps, n), t.child;
    case 8:
      return Xe(e, t, t.pendingProps.children, n), t.child;
    case 12:
      return Xe(e, t, t.pendingProps.children, n), t.child;
    case 10:
      e: {
        if (
          ((r = t.type._context),
          (i = t.pendingProps),
          (o = t.memoizedProps),
          (a = i.value),
          ce(os, r._currentValue),
          (r._currentValue = a),
          o !== null)
        )
          if (Dt(o.value, a)) {
            if (o.children === i.children && !ot.current) {
              t = wn(e, t, n);
              break e;
            }
          } else
            for (o = t.child, o !== null && (o.return = t); o !== null; ) {
              var s = o.dependencies;
              if (s !== null) {
                a = o.child;
                for (var u = s.firstContext; u !== null; ) {
                  if (u.context === r) {
                    if (o.tag === 1) {
                      (u = gn(-1, n & -n)), (u.tag = 2);
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
                      Ap(o.return, n, t),
                      (s.lanes |= n);
                    break;
                  }
                  u = u.next;
                }
              } else if (o.tag === 10) a = o.type === t.type ? null : o.child;
              else if (o.tag === 18) {
                if (((a = o.return), a === null)) throw Error(j(341));
                (a.lanes |= n),
                  (s = a.alternate),
                  s !== null && (s.lanes |= n),
                  Ap(a, n, t),
                  (a = o.sibling);
              } else a = o.child;
              if (a !== null) a.return = o;
              else
                for (a = o; a !== null; ) {
                  if (a === t) {
                    a = null;
                    break;
                  }
                  if (((o = a.sibling), o !== null)) {
                    (o.return = a.return), (a = o);
                    break;
                  }
                  a = a.return;
                }
              o = a;
            }
        Xe(e, t, i.children, n), (t = t.child);
      }
      return t;
    case 9:
      return (
        (i = t.type),
        (r = t.pendingProps.children),
        ii(t, n),
        (i = bt(i)),
        (r = r(i)),
        (t.flags |= 1),
        Xe(e, t, r, n),
        t.child
      );
    case 14:
      return (r = t.type), (i = At(r, t.pendingProps)), (i = At(r.type, i)), Vm(e, t, r, i, n);
    case 15:
      return BE(e, t, t.type, t.pendingProps, n);
    case 17:
      return (
        (r = t.type),
        (i = t.pendingProps),
        (i = t.elementType === r ? i : At(r, i)),
        $a(e, t),
        (t.tag = 1),
        at(r) ? ((e = !0), ns(t)) : (e = !1),
        ii(t, n),
        DE(t, r, i),
        Pp(t, r, i, n),
        Lp(null, t, r, !0, e, n)
      );
    case 19:
      return WE(e, t, n);
    case 22:
      return HE(e, t, n);
  }
  throw Error(j(156, t.tag));
};
function lb(e, t) {
  return LS(e, t);
}
function cT(e, t, n, r) {
  (this.tag = e),
    (this.key = n),
    (this.sibling = this.child = this.return = this.stateNode = this.type = this.elementType = null),
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
function xt(e, t, n, r) {
  return new cT(e, t, n, r);
}
function rv(e) {
  return (e = e.prototype), !(!e || !e.isReactComponent);
}
function fT(e) {
  if (typeof e == "function") return rv(e) ? 1 : 0;
  if (e != null) {
    if (((e = e.$$typeof), e === Sg)) return 11;
    if (e === Eg) return 14;
  }
  return 2;
}
function Xn(e, t) {
  var n = e.alternate;
  return (
    n === null
      ? ((n = xt(e.tag, t, e.key, e.mode)),
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
function ja(e, t, n, r, i, o) {
  var a = 2;
  if (((r = e), typeof e == "function")) rv(e) && (a = 1);
  else if (typeof e == "string") a = 5;
  else
    e: switch (e) {
      case Br:
        return yr(n.children, i, o, t);
      case xg:
        (a = 8), (i |= 8);
        break;
      case rp:
        return (e = xt(12, n, t, i | 2)), (e.elementType = rp), (e.lanes = o), e;
      case ip:
        return (e = xt(13, n, t, i)), (e.elementType = ip), (e.lanes = o), e;
      case op:
        return (e = xt(19, n, t, i)), (e.elementType = op), (e.lanes = o), e;
      case _S:
        return Fs(n, i, o, t);
      default:
        if (typeof e == "object" && e !== null)
          switch (e.$$typeof) {
            case mS:
              a = 10;
              break e;
            case yS:
              a = 9;
              break e;
            case Sg:
              a = 11;
              break e;
            case Eg:
              a = 14;
              break e;
            case Pn:
              (a = 16), (r = null);
              break e;
          }
        throw Error(j(130, e == null ? e : typeof e, ""));
    }
  return (t = xt(a, n, t, i)), (t.elementType = e), (t.type = r), (t.lanes = o), t;
}
function yr(e, t, n, r) {
  return (e = xt(7, e, r, t)), (e.lanes = n), e;
}
function Fs(e, t, n, r) {
  return (
    (e = xt(22, e, r, t)), (e.elementType = _S), (e.lanes = n), (e.stateNode = { isHidden: !1 }), e
  );
}
function Uu(e, t, n) {
  return (e = xt(6, e, null, t)), (e.lanes = n), e;
}
function Gu(e, t, n) {
  return (
    (t = xt(4, e.children !== null ? e.children : [], e.key, t)),
    (t.lanes = n),
    (t.stateNode = {
      containerInfo: e.containerInfo,
      pendingChildren: null,
      implementation: e.implementation,
    }),
    t
  );
}
function dT(e, t, n, r, i) {
  (this.tag = t),
    (this.containerInfo = e),
    (this.finishedWork = this.pingCache = this.current = this.pendingChildren = null),
    (this.timeoutHandle = -1),
    (this.callbackNode = this.pendingContext = this.context = null),
    (this.callbackPriority = 0),
    (this.eventTimes = Cu(0)),
    (this.expirationTimes = Cu(-1)),
    (this.entangledLanes = this.finishedLanes = this.mutableReadLanes = this.expiredLanes = this.pingedLanes = this.suspendedLanes = this.pendingLanes = 0),
    (this.entanglements = Cu(0)),
    (this.identifierPrefix = r),
    (this.onRecoverableError = i),
    (this.mutableSourceEagerHydrationData = null);
}
function iv(e, t, n, r, i, o, a, s, u) {
  return (
    (e = new dT(e, t, n, s, u)),
    t === 1 ? ((t = 1), o === !0 && (t |= 8)) : (t = 0),
    (o = xt(3, null, null, t)),
    (e.current = o),
    (o.stateNode = e),
    (o.memoizedState = {
      element: r,
      isDehydrated: n,
      cache: null,
      transitions: null,
      pendingSuspenseBoundaries: null,
    }),
    jg(o),
    e
  );
}
function hT(e, t, n) {
  var r = 3 < arguments.length && arguments[3] !== void 0 ? arguments[3] : null;
  return {
    $$typeof: jr,
    key: r == null ? null : "" + r,
    children: e,
    containerInfo: t,
    implementation: n,
  };
}
function cb(e) {
  if (!e) return er;
  e = e._reactInternals;
  e: {
    if (Tr(e) !== e || e.tag !== 1) throw Error(j(170));
    var t = e;
    do {
      switch (t.tag) {
        case 3:
          t = t.stateNode.context;
          break e;
        case 1:
          if (at(t.type)) {
            t = t.stateNode.__reactInternalMemoizedMergedChildContext;
            break e;
          }
      }
      t = t.return;
    } while (t !== null);
    throw Error(j(171));
  }
  if (e.tag === 1) {
    var n = e.type;
    if (at(n)) return cE(e, n, t);
  }
  return t;
}
function fb(e, t, n, r, i, o, a, s, u) {
  return (
    (e = iv(n, r, !0, e, i, o, a, s, u)),
    (e.context = cb(null)),
    (n = e.current),
    (r = Qe()),
    (i = Yn(n)),
    (o = gn(r, i)),
    (o.callback = t ?? null),
    Wn(n, o, i),
    (e.current.lanes = i),
    Ho(e, i, r),
    st(e, r),
    e
  );
}
function js(e, t, n, r) {
  var i = t.current,
    o = Qe(),
    a = Yn(i);
  return (
    (n = cb(n)),
    t.context === null ? (t.context = n) : (t.pendingContext = n),
    (t = gn(o, a)),
    (t.payload = { element: e }),
    (r = r === void 0 ? null : r),
    r !== null && (t.callback = r),
    (e = Wn(i, t, a)),
    e !== null && (zt(e, i, a, o), Oa(e, i, a)),
    a
  );
}
function gs(e) {
  if (((e = e.current), !e.child)) return null;
  switch (e.child.tag) {
    case 5:
      return e.child.stateNode;
    default:
      return e.child.stateNode;
  }
}
function ny(e, t) {
  if (((e = e.memoizedState), e !== null && e.dehydrated !== null)) {
    var n = e.retryLane;
    e.retryLane = n !== 0 && n < t ? n : t;
  }
}
function ov(e, t) {
  ny(e, t), (e = e.alternate) && ny(e, t);
}
function pT() {
  return null;
}
var db =
  typeof reportError == "function"
    ? reportError
    : function (e) {
        console.error(e);
      };
function av(e) {
  this._internalRoot = e;
}
Bs.prototype.render = av.prototype.render = function (e) {
  var t = this._internalRoot;
  if (t === null) throw Error(j(409));
  js(e, t, null, null);
};
Bs.prototype.unmount = av.prototype.unmount = function () {
  var e = this._internalRoot;
  if (e !== null) {
    this._internalRoot = null;
    var t = e.containerInfo;
    kr(function () {
      js(null, e, null, null);
    }),
      (t[yn] = null);
  }
};
function Bs(e) {
  this._internalRoot = e;
}
Bs.prototype.unstable_scheduleHydration = function (e) {
  if (e) {
    var t = HS();
    e = { blockedOn: null, target: e, priority: t };
    for (var n = 0; n < zn.length && t !== 0 && t < zn[n].priority; n++);
    zn.splice(n, 0, e), n === 0 && US(e);
  }
};
function sv(e) {
  return !(!e || (e.nodeType !== 1 && e.nodeType !== 9 && e.nodeType !== 11));
}
function Hs(e) {
  return !(
    !e ||
    (e.nodeType !== 1 &&
      e.nodeType !== 9 &&
      e.nodeType !== 11 &&
      (e.nodeType !== 8 || e.nodeValue !== " react-mount-point-unstable "))
  );
}
function ry() {}
function gT(e, t, n, r, i) {
  if (i) {
    if (typeof r == "function") {
      var o = r;
      r = function () {
        var l = gs(a);
        o.call(l);
      };
    }
    var a = fb(t, r, e, 0, null, !1, !1, "", ry);
    return (
      (e._reactRootContainer = a),
      (e[yn] = a.current),
      bo(e.nodeType === 8 ? e.parentNode : e),
      kr(),
      a
    );
  }
  for (; (i = e.lastChild); ) e.removeChild(i);
  if (typeof r == "function") {
    var s = r;
    r = function () {
      var l = gs(u);
      s.call(l);
    };
  }
  var u = iv(e, 0, !1, null, null, !1, !1, "", ry);
  return (
    (e._reactRootContainer = u),
    (e[yn] = u.current),
    bo(e.nodeType === 8 ? e.parentNode : e),
    kr(function () {
      js(t, u, n, r);
    }),
    u
  );
}
function Vs(e, t, n, r, i) {
  var o = n._reactRootContainer;
  if (o) {
    var a = o;
    if (typeof i == "function") {
      var s = i;
      i = function () {
        var u = gs(a);
        s.call(u);
      };
    }
    js(t, a, e, i);
  } else a = gT(n, t, e, i, r);
  return gs(a);
}
jS = function (e) {
  switch (e.tag) {
    case 3:
      var t = e.stateNode;
      if (t.current.memoizedState.isDehydrated) {
        var n = Yi(t.pendingLanes);
        n !== 0 && (Cg(t, n | 1), st(t, ke()), !(ae & 6) && ((vi = ke() + 500), ir()));
      }
      break;
    case 13:
      kr(function () {
        var r = _n(e, 1);
        if (r !== null) {
          var i = Qe();
          zt(r, e, 1, i);
        }
      }),
        ov(e, 1);
  }
};
Ng = function (e) {
  if (e.tag === 13) {
    var t = _n(e, 134217728);
    if (t !== null) {
      var n = Qe();
      zt(t, e, 134217728, n);
    }
    ov(e, 134217728);
  }
};
BS = function (e) {
  if (e.tag === 13) {
    var t = Yn(e),
      n = _n(e, t);
    if (n !== null) {
      var r = Qe();
      zt(n, e, t, r);
    }
    ov(e, t);
  }
};
HS = function () {
  return le;
};
VS = function (e, t) {
  var n = le;
  try {
    return (le = e), t();
  } finally {
    le = n;
  }
};
gp = function (e, t, n) {
  switch (t) {
    case "input":
      if ((up(e, n), (t = n.name), n.type === "radio" && t != null)) {
        for (n = e; n.parentNode; ) n = n.parentNode;
        for (
          n = n.querySelectorAll("input[name=" + JSON.stringify("" + t) + '][type="radio"]'), t = 0;
          t < n.length;
          t++
        ) {
          var r = n[t];
          if (r !== e && r.form === e.form) {
            var i = qs(r);
            if (!i) throw Error(j(90));
            xS(r), up(r, i);
          }
        }
      }
      break;
    case "textarea":
      ES(e, n);
      break;
    case "select":
      (t = n.value), t != null && ei(e, !!n.multiple, t, !1);
  }
};
IS = ev;
AS = kr;
var vT = { usingClientEntryPoint: !1, Events: [Uo, Gr, qs, RS, TS, ev] },
  Di = {
    findFiberByHostInstance: fr,
    bundleType: 0,
    version: "18.3.1",
    rendererPackageName: "react-dom",
  },
  mT = {
    bundleType: Di.bundleType,
    version: Di.version,
    rendererPackageName: Di.rendererPackageName,
    rendererConfig: Di.rendererConfig,
    overrideHookState: null,
    overrideHookStateDeletePath: null,
    overrideHookStateRenamePath: null,
    overrideProps: null,
    overridePropsDeletePath: null,
    overridePropsRenamePath: null,
    setErrorHandler: null,
    setSuspenseHandler: null,
    scheduleUpdate: null,
    currentDispatcherRef: bn.ReactCurrentDispatcher,
    findHostInstanceByFiber: function (e) {
      return (e = qS(e)), e === null ? null : e.stateNode;
    },
    findFiberByHostInstance: Di.findFiberByHostInstance || pT,
    findHostInstancesForRefresh: null,
    scheduleRefresh: null,
    scheduleRoot: null,
    setRefreshHandler: null,
    getCurrentFiber: null,
    reconcilerVersion: "18.3.1-next-f1338f8080-20240426",
  };
if (typeof __REACT_DEVTOOLS_GLOBAL_HOOK__ < "u") {
  var ya = __REACT_DEVTOOLS_GLOBAL_HOOK__;
  if (!ya.isDisabled && ya.supportsFiber)
    try {
      (Is = ya.inject(mT)), (Xt = ya);
    } catch {}
}
vt.__SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED = vT;
vt.createPortal = function (e, t) {
  var n = 2 < arguments.length && arguments[2] !== void 0 ? arguments[2] : null;
  if (!sv(t)) throw Error(j(200));
  return hT(e, t, null, n);
};
vt.createRoot = function (e, t) {
  if (!sv(e)) throw Error(j(299));
  var n = !1,
    r = "",
    i = db;
  return (
    t != null &&
      (t.unstable_strictMode === !0 && (n = !0),
      t.identifierPrefix !== void 0 && (r = t.identifierPrefix),
      t.onRecoverableError !== void 0 && (i = t.onRecoverableError)),
    (t = iv(e, 1, !1, null, null, n, !1, r, i)),
    (e[yn] = t.current),
    bo(e.nodeType === 8 ? e.parentNode : e),
    new av(t)
  );
};
vt.findDOMNode = function (e) {
  if (e == null) return null;
  if (e.nodeType === 1) return e;
  var t = e._reactInternals;
  if (t === void 0)
    throw typeof e.render == "function"
      ? Error(j(188))
      : ((e = Object.keys(e).join(",")), Error(j(268, e)));
  return (e = qS(t)), (e = e === null ? null : e.stateNode), e;
};
vt.flushSync = function (e) {
  return kr(e);
};
vt.hydrate = function (e, t, n) {
  if (!Hs(t)) throw Error(j(200));
  return Vs(null, e, t, !0, n);
};
vt.hydrateRoot = function (e, t, n) {
  if (!sv(e)) throw Error(j(405));
  var r = (n != null && n.hydratedSources) || null,
    i = !1,
    o = "",
    a = db;
  if (
    (n != null &&
      (n.unstable_strictMode === !0 && (i = !0),
      n.identifierPrefix !== void 0 && (o = n.identifierPrefix),
      n.onRecoverableError !== void 0 && (a = n.onRecoverableError)),
    (t = fb(t, null, e, 1, n ?? null, i, !1, o, a)),
    (e[yn] = t.current),
    bo(e),
    r)
  )
    for (e = 0; e < r.length; e++)
      (n = r[e]),
        (i = n._getVersion),
        (i = i(n._source)),
        t.mutableSourceEagerHydrationData == null
          ? (t.mutableSourceEagerHydrationData = [n, i])
          : t.mutableSourceEagerHydrationData.push(n, i);
  return new Bs(t);
};
vt.render = function (e, t, n) {
  if (!Hs(t)) throw Error(j(200));
  return Vs(null, e, t, !1, n);
};
vt.unmountComponentAtNode = function (e) {
  if (!Hs(e)) throw Error(j(40));
  return e._reactRootContainer
    ? (kr(function () {
        Vs(null, null, e, !1, function () {
          (e._reactRootContainer = null), (e[yn] = null);
        });
      }),
      !0)
    : !1;
};
vt.unstable_batchedUpdates = ev;
vt.unstable_renderSubtreeIntoContainer = function (e, t, n, r) {
  if (!Hs(n)) throw Error(j(200));
  if (e == null || e._reactInternals === void 0) throw Error(j(38));
  return Vs(e, t, n, !1, r);
};
vt.version = "18.3.1-next-f1338f8080-20240426";
function hb() {
  if (
    !(
      typeof __REACT_DEVTOOLS_GLOBAL_HOOK__ > "u" ||
      typeof __REACT_DEVTOOLS_GLOBAL_HOOK__.checkDCE != "function"
    )
  )
    try {
      __REACT_DEVTOOLS_GLOBAL_HOOK__.checkDCE(hb);
    } catch (e) {
      console.error(e);
    }
}
hb(), (hS.exports = vt);
var yT = hS.exports,
  iy = yT;
(tp.createRoot = iy.createRoot), (tp.hydrateRoot = iy.hydrateRoot);
const _T = {},
  oy = (e) => {
    let t;
    const n = new Set(),
      r = (c, f) => {
        const d = typeof c == "function" ? c(t) : c;
        if (!Object.is(d, t)) {
          const h = t;
          (t = f ?? (typeof d != "object" || d === null) ? d : Object.assign({}, t, d)),
            n.forEach((m) => m(t, h));
        }
      },
      i = () => t,
      u = {
        setState: r,
        getState: i,
        getInitialState: () => l,
        subscribe: (c) => (n.add(c), () => n.delete(c)),
        destroy: () => {
          (_T ? "production" : void 0) !== "production" &&
            console.warn(
              "[DEPRECATED] The `destroy` method will be unsupported in a future version. Instead use unsubscribe function returned by subscribe. Everything will be garbage-collected if store is garbage-collected."
            ),
            n.clear();
        },
      },
      l = (t = e(r, i, u));
    return u;
  },
  pb = (e) => (e ? oy(e) : oy);
var gb = { exports: {} },
  vb = {},
  mb = { exports: {} },
  yb = {};
/**
 * @license React
 * use-sync-external-store-shim.production.js
 *
 * Copyright (c) Meta Platforms, Inc. and affiliates.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */ var mi = q;
function wT(e, t) {
  return (e === t && (e !== 0 || 1 / e === 1 / t)) || (e !== e && t !== t);
}
var xT = typeof Object.is == "function" ? Object.is : wT,
  ST = mi.useState,
  ET = mi.useEffect,
  bT = mi.useLayoutEffect,
  kT = mi.useDebugValue;
function CT(e, t) {
  var n = t(),
    r = ST({ inst: { value: n, getSnapshot: t } }),
    i = r[0].inst,
    o = r[1];
  return (
    bT(
      function () {
        (i.value = n), (i.getSnapshot = t), Wu(i) && o({ inst: i });
      },
      [e, n, t]
    ),
    ET(
      function () {
        return (
          Wu(i) && o({ inst: i }),
          e(function () {
            Wu(i) && o({ inst: i });
          })
        );
      },
      [e]
    ),
    kT(n),
    n
  );
}
function Wu(e) {
  var t = e.getSnapshot;
  e = e.value;
  try {
    var n = t();
    return !xT(e, n);
  } catch {
    return !0;
  }
}
function NT(e, t) {
  return t();
}
var RT =
  typeof window > "u" || typeof window.document > "u" || typeof window.document.createElement > "u"
    ? NT
    : CT;
yb.useSyncExternalStore = mi.useSyncExternalStore !== void 0 ? mi.useSyncExternalStore : RT;
mb.exports = yb;
var TT = mb.exports;
/**
 * @license React
 * use-sync-external-store-shim/with-selector.production.js
 *
 * Copyright (c) Meta Platforms, Inc. and affiliates.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */ var Us = q,
  IT = TT;
function AT(e, t) {
  return (e === t && (e !== 0 || 1 / e === 1 / t)) || (e !== e && t !== t);
}
var MT = typeof Object.is == "function" ? Object.is : AT,
  PT = IT.useSyncExternalStore,
  qT = Us.useRef,
  OT = Us.useEffect,
  LT = Us.useMemo,
  zT = Us.useDebugValue;
vb.useSyncExternalStoreWithSelector = function (e, t, n, r, i) {
  var o = qT(null);
  if (o.current === null) {
    var a = { hasValue: !1, value: null };
    o.current = a;
  } else a = o.current;
  o = LT(
    function () {
      function u(h) {
        if (!l) {
          if (((l = !0), (c = h), (h = r(h)), i !== void 0 && a.hasValue)) {
            var m = a.value;
            if (i(m, h)) return (f = m);
          }
          return (f = h);
        }
        if (((m = f), MT(c, h))) return m;
        var v = r(h);
        return i !== void 0 && i(m, v) ? ((c = h), m) : ((c = h), (f = v));
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
    [t, n, r, i]
  );
  var s = PT(e, o[0], o[1]);
  return (
    OT(
      function () {
        (a.hasValue = !0), (a.value = s);
      },
      [s]
    ),
    zT(s),
    s
  );
};
gb.exports = vb;
var $T = gb.exports;
const _b = tS($T),
  wb = {},
  { useDebugValue: DT } = O,
  { useSyncExternalStoreWithSelector: FT } = _b;
let ay = !1;
const jT = (e) => e;
function BT(e, t = jT, n) {
  (wb ? "production" : void 0) !== "production" &&
    n &&
    !ay &&
    (console.warn(
      "[DEPRECATED] Use `createWithEqualityFn` instead of `create` or use `useStoreWithEqualityFn` instead of `useStore`. They can be imported from 'zustand/traditional'. https://github.com/pmndrs/zustand/discussions/1937"
    ),
    (ay = !0));
  const r = FT(e.subscribe, e.getState, e.getServerState || e.getInitialState, t, n);
  return DT(r), r;
}
const sy = (e) => {
    (wb ? "production" : void 0) !== "production" &&
      typeof e != "function" &&
      console.warn(
        "[DEPRECATED] Passing a vanilla store will be unsupported in a future version. Instead use `import { useStore } from 'zustand'`."
      );
    const t = typeof e == "function" ? pb(e) : e,
      n = (r, i) => BT(t, r, i);
    return Object.assign(n, t), n;
  },
  HT = (e) => (e ? sy(e) : sy),
  xb = HT((e) => ({
    machines: {},
    addMachine: (t) =>
      e((n) => ({
        machines: {
          ...n.machines,
          [t.machine_id]: {
            id: t.machine_id,
            definition: t.definition,
            currentStateIds: t.initial_state_ids,
            context: t.initial_context,
            logs: [{ type: "machine_registered", payload: t }],
            services: {},
          },
        },
      })),
    updateMachineTransition: (t) =>
      e((n) =>
        n.machines[t.machine_id]
          ? {
              machines: {
                ...n.machines,
                [t.machine_id]: {
                  ...n.machines[t.machine_id],
                  currentStateIds: t.to_state_ids,
                  context: t.full_context,
                  logs: [...n.machines[t.machine_id].logs, { type: "transition", payload: t }],
                },
              },
            }
          : n
      ),
    addService: (t) =>
      e((n) =>
        n.machines[t.machine_id]
          ? {
              machines: {
                ...n.machines,
                [t.machine_id]: {
                  ...n.machines[t.machine_id],
                  services: {
                    ...n.machines[t.machine_id].services,
                    [t.id]: { src: t.service, status: "running" },
                  },
                  logs: [...n.machines[t.machine_id].logs, { type: "service_invoked", payload: t }],
                },
              },
            }
          : n
      ),
    removeService: (t) =>
      e((n) => {
        if (!n.machines[t.machine_id]) return n;
        const r = { ...n.machines[t.machine_id].services };
        return (
          delete r[t.id],
          {
            machines: {
              ...n.machines,
              [t.machine_id]: { ...n.machines[t.machine_id], services: r },
            },
          }
        );
      }),
    addLog: (t, n) =>
      e((r) =>
        r.machines[t]
          ? {
              machines: {
                ...r.machines,
                [t]: { ...r.machines[t], logs: [...r.machines[t].logs, n] },
              },
            }
          : r
      ),
  })),
  VT = () => {
    const {
      addMachine: e,
      updateMachineTransition: t,
      addService: n,
      removeService: r,
      addLog: i,
    } = xb();
    q.useEffect(() => {
      const o = new WebSocket("ws://127.0.0.1:8008/ws");
      return (
        (o.onopen = () => console.log("Inspector WebSocket connected")),
        (o.onclose = () => console.log("Inspector WebSocket disconnected")),
        (o.onmessage = (a) => {
          const s = JSON.parse(a.data);
          switch (s.type) {
            case "machine_registered":
              e(s.payload);
              break;
            case "transition":
              t(s.payload);
              break;
            case "service_invoked":
              n(s.payload);
              break;
            case "service_stopped":
              r(s.payload);
              break;
            default:
              i(s.machine_id, { type: s.type, payload: s.payload, ...s });
              break;
          }
        }),
        () => {
          o.close();
        }
      );
    }, [e, t, n, r, i]);
  };
function Be(e) {
  if (typeof e == "string" || typeof e == "number") return "" + e;
  let t = "";
  if (Array.isArray(e))
    for (let n = 0, r; n < e.length; n++) (r = Be(e[n])) !== "" && (t += (t && " ") + r);
  else for (let n in e) e[n] && (t += (t && " ") + n);
  return t;
}
const { useDebugValue: UT } = O,
  { useSyncExternalStoreWithSelector: GT } = _b,
  WT = (e) => e;
function Sb(e, t = WT, n) {
  const r = GT(e.subscribe, e.getState, e.getServerState || e.getInitialState, t, n);
  return UT(r), r;
}
const uy = (e, t) => {
    const n = pb(e),
      r = (i, o = t) => Sb(n, i, o);
    return Object.assign(r, n), r;
  },
  KT = (e, t) => (e ? uy(e, t) : uy);
function ze(e, t) {
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
var YT = { value: () => {} };
function Gs() {
  for (var e = 0, t = arguments.length, n = {}, r; e < t; ++e) {
    if (!(r = arguments[e] + "") || r in n || /[\s.]/.test(r))
      throw new Error("illegal type: " + r);
    n[r] = [];
  }
  return new Ba(n);
}
function Ba(e) {
  this._ = e;
}
function XT(e, t) {
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
Ba.prototype = Gs.prototype = {
  constructor: Ba,
  on: function (e, t) {
    var n = this._,
      r = XT(e + "", n),
      i,
      o = -1,
      a = r.length;
    if (arguments.length < 2) {
      for (; ++o < a; ) if ((i = (e = r[o]).type) && (i = QT(n[i], e.name))) return i;
      return;
    }
    if (t != null && typeof t != "function") throw new Error("invalid callback: " + t);
    for (; ++o < a; )
      if ((i = (e = r[o]).type)) n[i] = ly(n[i], e.name, t);
      else if (t == null) for (i in n) n[i] = ly(n[i], e.name, null);
    return this;
  },
  copy: function () {
    var e = {},
      t = this._;
    for (var n in t) e[n] = t[n].slice();
    return new Ba(e);
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
function QT(e, t) {
  for (var n = 0, r = e.length, i; n < r; ++n) if ((i = e[n]).name === t) return i.value;
}
function ly(e, t, n) {
  for (var r = 0, i = e.length; r < i; ++r)
    if (e[r].name === t) {
      (e[r] = YT), (e = e.slice(0, r).concat(e.slice(r + 1)));
      break;
    }
  return n != null && e.push({ name: t, value: n }), e;
}
var Kp = "http://www.w3.org/1999/xhtml";
const cy = {
  svg: "http://www.w3.org/2000/svg",
  xhtml: Kp,
  xlink: "http://www.w3.org/1999/xlink",
  xml: "http://www.w3.org/XML/1998/namespace",
  xmlns: "http://www.w3.org/2000/xmlns/",
};
function Ws(e) {
  var t = (e += ""),
    n = t.indexOf(":");
  return (
    n >= 0 && (t = e.slice(0, n)) !== "xmlns" && (e = e.slice(n + 1)),
    cy.hasOwnProperty(t) ? { space: cy[t], local: e } : e
  );
}
function ZT(e) {
  return function () {
    var t = this.ownerDocument,
      n = this.namespaceURI;
    return n === Kp && t.documentElement.namespaceURI === Kp
      ? t.createElement(e)
      : t.createElementNS(n, e);
  };
}
function JT(e) {
  return function () {
    return this.ownerDocument.createElementNS(e.space, e.local);
  };
}
function Eb(e) {
  var t = Ws(e);
  return (t.local ? JT : ZT)(t);
}
function eI() {}
function uv(e) {
  return e == null
    ? eI
    : function () {
        return this.querySelector(e);
      };
}
function tI(e) {
  typeof e != "function" && (e = uv(e));
  for (var t = this._groups, n = t.length, r = new Array(n), i = 0; i < n; ++i)
    for (var o = t[i], a = o.length, s = (r[i] = new Array(a)), u, l, c = 0; c < a; ++c)
      (u = o[c]) &&
        (l = e.call(u, u.__data__, c, o)) &&
        ("__data__" in u && (l.__data__ = u.__data__), (s[c] = l));
  return new gt(r, this._parents);
}
function nI(e) {
  return e == null ? [] : Array.isArray(e) ? e : Array.from(e);
}
function rI() {
  return [];
}
function bb(e) {
  return e == null
    ? rI
    : function () {
        return this.querySelectorAll(e);
      };
}
function iI(e) {
  return function () {
    return nI(e.apply(this, arguments));
  };
}
function oI(e) {
  typeof e == "function" ? (e = iI(e)) : (e = bb(e));
  for (var t = this._groups, n = t.length, r = [], i = [], o = 0; o < n; ++o)
    for (var a = t[o], s = a.length, u, l = 0; l < s; ++l)
      (u = a[l]) && (r.push(e.call(u, u.__data__, l, a)), i.push(u));
  return new gt(r, i);
}
function kb(e) {
  return function () {
    return this.matches(e);
  };
}
function Cb(e) {
  return function (t) {
    return t.matches(e);
  };
}
var aI = Array.prototype.find;
function sI(e) {
  return function () {
    return aI.call(this.children, e);
  };
}
function uI() {
  return this.firstElementChild;
}
function lI(e) {
  return this.select(e == null ? uI : sI(typeof e == "function" ? e : Cb(e)));
}
var cI = Array.prototype.filter;
function fI() {
  return Array.from(this.children);
}
function dI(e) {
  return function () {
    return cI.call(this.children, e);
  };
}
function hI(e) {
  return this.selectAll(e == null ? fI : dI(typeof e == "function" ? e : Cb(e)));
}
function pI(e) {
  typeof e != "function" && (e = kb(e));
  for (var t = this._groups, n = t.length, r = new Array(n), i = 0; i < n; ++i)
    for (var o = t[i], a = o.length, s = (r[i] = []), u, l = 0; l < a; ++l)
      (u = o[l]) && e.call(u, u.__data__, l, o) && s.push(u);
  return new gt(r, this._parents);
}
function Nb(e) {
  return new Array(e.length);
}
function gI() {
  return new gt(this._enter || this._groups.map(Nb), this._parents);
}
function vs(e, t) {
  (this.ownerDocument = e.ownerDocument),
    (this.namespaceURI = e.namespaceURI),
    (this._next = null),
    (this._parent = e),
    (this.__data__ = t);
}
vs.prototype = {
  constructor: vs,
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
function vI(e) {
  return function () {
    return e;
  };
}
function mI(e, t, n, r, i, o) {
  for (var a = 0, s, u = t.length, l = o.length; a < l; ++a)
    (s = t[a]) ? ((s.__data__ = o[a]), (r[a] = s)) : (n[a] = new vs(e, o[a]));
  for (; a < u; ++a) (s = t[a]) && (i[a] = s);
}
function yI(e, t, n, r, i, o, a) {
  var s,
    u,
    l = new Map(),
    c = t.length,
    f = o.length,
    d = new Array(c),
    h;
  for (s = 0; s < c; ++s)
    (u = t[s]) &&
      ((d[s] = h = a.call(u, u.__data__, s, t) + ""), l.has(h) ? (i[s] = u) : l.set(h, u));
  for (s = 0; s < f; ++s)
    (h = a.call(e, o[s], s, o) + ""),
      (u = l.get(h)) ? ((r[s] = u), (u.__data__ = o[s]), l.delete(h)) : (n[s] = new vs(e, o[s]));
  for (s = 0; s < c; ++s) (u = t[s]) && l.get(d[s]) === u && (i[s] = u);
}
function _I(e) {
  return e.__data__;
}
function wI(e, t) {
  if (!arguments.length) return Array.from(this, _I);
  var n = t ? yI : mI,
    r = this._parents,
    i = this._groups;
  typeof e != "function" && (e = vI(e));
  for (var o = i.length, a = new Array(o), s = new Array(o), u = new Array(o), l = 0; l < o; ++l) {
    var c = r[l],
      f = i[l],
      d = f.length,
      h = xI(e.call(c, c && c.__data__, l, r)),
      m = h.length,
      v = (s[l] = new Array(m)),
      w = (a[l] = new Array(m)),
      p = (u[l] = new Array(d));
    n(c, f, v, w, p, h, t);
    for (var g = 0, y = 0, _, S; g < m; ++g)
      if ((_ = v[g])) {
        for (g >= y && (y = g + 1); !(S = w[y]) && ++y < m; );
        _._next = S || null;
      }
  }
  return (a = new gt(a, r)), (a._enter = s), (a._exit = u), a;
}
function xI(e) {
  return typeof e == "object" && "length" in e ? e : Array.from(e);
}
function SI() {
  return new gt(this._exit || this._groups.map(Nb), this._parents);
}
function EI(e, t, n) {
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
function bI(e) {
  for (
    var t = e.selection ? e.selection() : e,
      n = this._groups,
      r = t._groups,
      i = n.length,
      o = r.length,
      a = Math.min(i, o),
      s = new Array(i),
      u = 0;
    u < a;
    ++u
  )
    for (var l = n[u], c = r[u], f = l.length, d = (s[u] = new Array(f)), h, m = 0; m < f; ++m)
      (h = l[m] || c[m]) && (d[m] = h);
  for (; u < i; ++u) s[u] = n[u];
  return new gt(s, this._parents);
}
function kI() {
  for (var e = this._groups, t = -1, n = e.length; ++t < n; )
    for (var r = e[t], i = r.length - 1, o = r[i], a; --i >= 0; )
      (a = r[i]) &&
        (o && a.compareDocumentPosition(o) ^ 4 && o.parentNode.insertBefore(a, o), (o = a));
  return this;
}
function CI(e) {
  e || (e = NI);
  function t(f, d) {
    return f && d ? e(f.__data__, d.__data__) : !f - !d;
  }
  for (var n = this._groups, r = n.length, i = new Array(r), o = 0; o < r; ++o) {
    for (var a = n[o], s = a.length, u = (i[o] = new Array(s)), l, c = 0; c < s; ++c)
      (l = a[c]) && (u[c] = l);
    u.sort(t);
  }
  return new gt(i, this._parents).order();
}
function NI(e, t) {
  return e < t ? -1 : e > t ? 1 : e >= t ? 0 : NaN;
}
function RI() {
  var e = arguments[0];
  return (arguments[0] = this), e.apply(null, arguments), this;
}
function TI() {
  return Array.from(this);
}
function II() {
  for (var e = this._groups, t = 0, n = e.length; t < n; ++t)
    for (var r = e[t], i = 0, o = r.length; i < o; ++i) {
      var a = r[i];
      if (a) return a;
    }
  return null;
}
function AI() {
  let e = 0;
  for (const t of this) ++e;
  return e;
}
function MI() {
  return !this.node();
}
function PI(e) {
  for (var t = this._groups, n = 0, r = t.length; n < r; ++n)
    for (var i = t[n], o = 0, a = i.length, s; o < a; ++o)
      (s = i[o]) && e.call(s, s.__data__, o, i);
  return this;
}
function qI(e) {
  return function () {
    this.removeAttribute(e);
  };
}
function OI(e) {
  return function () {
    this.removeAttributeNS(e.space, e.local);
  };
}
function LI(e, t) {
  return function () {
    this.setAttribute(e, t);
  };
}
function zI(e, t) {
  return function () {
    this.setAttributeNS(e.space, e.local, t);
  };
}
function $I(e, t) {
  return function () {
    var n = t.apply(this, arguments);
    n == null ? this.removeAttribute(e) : this.setAttribute(e, n);
  };
}
function DI(e, t) {
  return function () {
    var n = t.apply(this, arguments);
    n == null ? this.removeAttributeNS(e.space, e.local) : this.setAttributeNS(e.space, e.local, n);
  };
}
function FI(e, t) {
  var n = Ws(e);
  if (arguments.length < 2) {
    var r = this.node();
    return n.local ? r.getAttributeNS(n.space, n.local) : r.getAttribute(n);
  }
  return this.each(
    (t == null
      ? n.local
        ? OI
        : qI
      : typeof t == "function"
      ? n.local
        ? DI
        : $I
      : n.local
      ? zI
      : LI)(n, t)
  );
}
function Rb(e) {
  return (e.ownerDocument && e.ownerDocument.defaultView) || (e.document && e) || e.defaultView;
}
function jI(e) {
  return function () {
    this.style.removeProperty(e);
  };
}
function BI(e, t, n) {
  return function () {
    this.style.setProperty(e, t, n);
  };
}
function HI(e, t, n) {
  return function () {
    var r = t.apply(this, arguments);
    r == null ? this.style.removeProperty(e) : this.style.setProperty(e, r, n);
  };
}
function VI(e, t, n) {
  return arguments.length > 1
    ? this.each((t == null ? jI : typeof t == "function" ? HI : BI)(e, t, n ?? ""))
    : yi(this.node(), e);
}
function yi(e, t) {
  return e.style.getPropertyValue(t) || Rb(e).getComputedStyle(e, null).getPropertyValue(t);
}
function UI(e) {
  return function () {
    delete this[e];
  };
}
function GI(e, t) {
  return function () {
    this[e] = t;
  };
}
function WI(e, t) {
  return function () {
    var n = t.apply(this, arguments);
    n == null ? delete this[e] : (this[e] = n);
  };
}
function KI(e, t) {
  return arguments.length > 1
    ? this.each((t == null ? UI : typeof t == "function" ? WI : GI)(e, t))
    : this.node()[e];
}
function Tb(e) {
  return e.trim().split(/^|\s+/);
}
function lv(e) {
  return e.classList || new Ib(e);
}
function Ib(e) {
  (this._node = e), (this._names = Tb(e.getAttribute("class") || ""));
}
Ib.prototype = {
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
function Ab(e, t) {
  for (var n = lv(e), r = -1, i = t.length; ++r < i; ) n.add(t[r]);
}
function Mb(e, t) {
  for (var n = lv(e), r = -1, i = t.length; ++r < i; ) n.remove(t[r]);
}
function YI(e) {
  return function () {
    Ab(this, e);
  };
}
function XI(e) {
  return function () {
    Mb(this, e);
  };
}
function QI(e, t) {
  return function () {
    (t.apply(this, arguments) ? Ab : Mb)(this, e);
  };
}
function ZI(e, t) {
  var n = Tb(e + "");
  if (arguments.length < 2) {
    for (var r = lv(this.node()), i = -1, o = n.length; ++i < o; ) if (!r.contains(n[i])) return !1;
    return !0;
  }
  return this.each((typeof t == "function" ? QI : t ? YI : XI)(n, t));
}
function JI() {
  this.textContent = "";
}
function eA(e) {
  return function () {
    this.textContent = e;
  };
}
function tA(e) {
  return function () {
    var t = e.apply(this, arguments);
    this.textContent = t ?? "";
  };
}
function nA(e) {
  return arguments.length
    ? this.each(e == null ? JI : (typeof e == "function" ? tA : eA)(e))
    : this.node().textContent;
}
function rA() {
  this.innerHTML = "";
}
function iA(e) {
  return function () {
    this.innerHTML = e;
  };
}
function oA(e) {
  return function () {
    var t = e.apply(this, arguments);
    this.innerHTML = t ?? "";
  };
}
function aA(e) {
  return arguments.length
    ? this.each(e == null ? rA : (typeof e == "function" ? oA : iA)(e))
    : this.node().innerHTML;
}
function sA() {
  this.nextSibling && this.parentNode.appendChild(this);
}
function uA() {
  return this.each(sA);
}
function lA() {
  this.previousSibling && this.parentNode.insertBefore(this, this.parentNode.firstChild);
}
function cA() {
  return this.each(lA);
}
function fA(e) {
  var t = typeof e == "function" ? e : Eb(e);
  return this.select(function () {
    return this.appendChild(t.apply(this, arguments));
  });
}
function dA() {
  return null;
}
function hA(e, t) {
  var n = typeof e == "function" ? e : Eb(e),
    r = t == null ? dA : typeof t == "function" ? t : uv(t);
  return this.select(function () {
    return this.insertBefore(n.apply(this, arguments), r.apply(this, arguments) || null);
  });
}
function pA() {
  var e = this.parentNode;
  e && e.removeChild(this);
}
function gA() {
  return this.each(pA);
}
function vA() {
  var e = this.cloneNode(!1),
    t = this.parentNode;
  return t ? t.insertBefore(e, this.nextSibling) : e;
}
function mA() {
  var e = this.cloneNode(!0),
    t = this.parentNode;
  return t ? t.insertBefore(e, this.nextSibling) : e;
}
function yA(e) {
  return this.select(e ? mA : vA);
}
function _A(e) {
  return arguments.length ? this.property("__data__", e) : this.node().__data__;
}
function wA(e) {
  return function (t) {
    e.call(this, t, this.__data__);
  };
}
function xA(e) {
  return e
    .trim()
    .split(/^|\s+/)
    .map(function (t) {
      var n = "",
        r = t.indexOf(".");
      return r >= 0 && ((n = t.slice(r + 1)), (t = t.slice(0, r))), { type: t, name: n };
    });
}
function SA(e) {
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
function EA(e, t, n) {
  return function () {
    var r = this.__on,
      i,
      o = wA(t);
    if (r) {
      for (var a = 0, s = r.length; a < s; ++a)
        if ((i = r[a]).type === e.type && i.name === e.name) {
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
function bA(e, t, n) {
  var r = xA(e + ""),
    i,
    o = r.length,
    a;
  if (arguments.length < 2) {
    var s = this.node().__on;
    if (s) {
      for (var u = 0, l = s.length, c; u < l; ++u)
        for (i = 0, c = s[u]; i < o; ++i)
          if ((a = r[i]).type === c.type && a.name === c.name) return c.value;
    }
    return;
  }
  for (s = t ? EA : SA, i = 0; i < o; ++i) this.each(s(r[i], t, n));
  return this;
}
function Pb(e, t, n) {
  var r = Rb(e),
    i = r.CustomEvent;
  typeof i == "function"
    ? (i = new i(t, n))
    : ((i = r.document.createEvent("Event")),
      n
        ? (i.initEvent(t, n.bubbles, n.cancelable), (i.detail = n.detail))
        : i.initEvent(t, !1, !1)),
    e.dispatchEvent(i);
}
function kA(e, t) {
  return function () {
    return Pb(this, e, t);
  };
}
function CA(e, t) {
  return function () {
    return Pb(this, e, t.apply(this, arguments));
  };
}
function NA(e, t) {
  return this.each((typeof t == "function" ? CA : kA)(e, t));
}
function* RA() {
  for (var e = this._groups, t = 0, n = e.length; t < n; ++t)
    for (var r = e[t], i = 0, o = r.length, a; i < o; ++i) (a = r[i]) && (yield a);
}
var qb = [null];
function gt(e, t) {
  (this._groups = e), (this._parents = t);
}
function Wo() {
  return new gt([[document.documentElement]], qb);
}
function TA() {
  return this;
}
gt.prototype = Wo.prototype = {
  constructor: gt,
  select: tI,
  selectAll: oI,
  selectChild: lI,
  selectChildren: hI,
  filter: pI,
  data: wI,
  enter: gI,
  exit: SI,
  join: EI,
  merge: bI,
  selection: TA,
  order: kI,
  sort: CI,
  call: RI,
  nodes: TI,
  node: II,
  size: AI,
  empty: MI,
  each: PI,
  attr: FI,
  style: VI,
  property: KI,
  classed: ZI,
  text: nA,
  html: aA,
  raise: uA,
  lower: cA,
  append: fA,
  insert: hA,
  remove: gA,
  clone: yA,
  datum: _A,
  on: bA,
  dispatch: NA,
  [Symbol.iterator]: RA,
};
function wt(e) {
  return typeof e == "string"
    ? new gt([[document.querySelector(e)]], [document.documentElement])
    : new gt([[e]], qb);
}
function IA(e) {
  let t;
  for (; (t = e.sourceEvent); ) e = t;
  return e;
}
function Pt(e, t) {
  if (((e = IA(e)), t === void 0 && (t = e.currentTarget), t)) {
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
const AA = { passive: !1 },
  Po = { capture: !0, passive: !1 };
function Ku(e) {
  e.stopImmediatePropagation();
}
function ai(e) {
  e.preventDefault(), e.stopImmediatePropagation();
}
function Ob(e) {
  var t = e.document.documentElement,
    n = wt(e).on("dragstart.drag", ai, Po);
  "onselectstart" in t
    ? n.on("selectstart.drag", ai, Po)
    : ((t.__noselect = t.style.MozUserSelect), (t.style.MozUserSelect = "none"));
}
function Lb(e, t) {
  var n = e.document.documentElement,
    r = wt(e).on("dragstart.drag", null);
  t &&
    (r.on("click.drag", ai, Po),
    setTimeout(function () {
      r.on("click.drag", null);
    }, 0)),
    "onselectstart" in n
      ? r.on("selectstart.drag", null)
      : ((n.style.MozUserSelect = n.__noselect), delete n.__noselect);
}
const _a = (e) => () => e;
function Yp(
  e,
  {
    sourceEvent: t,
    subject: n,
    target: r,
    identifier: i,
    active: o,
    x: a,
    y: s,
    dx: u,
    dy: l,
    dispatch: c,
  }
) {
  Object.defineProperties(this, {
    type: { value: e, enumerable: !0, configurable: !0 },
    sourceEvent: { value: t, enumerable: !0, configurable: !0 },
    subject: { value: n, enumerable: !0, configurable: !0 },
    target: { value: r, enumerable: !0, configurable: !0 },
    identifier: { value: i, enumerable: !0, configurable: !0 },
    active: { value: o, enumerable: !0, configurable: !0 },
    x: { value: a, enumerable: !0, configurable: !0 },
    y: { value: s, enumerable: !0, configurable: !0 },
    dx: { value: u, enumerable: !0, configurable: !0 },
    dy: { value: l, enumerable: !0, configurable: !0 },
    _: { value: c },
  });
}
Yp.prototype.on = function () {
  var e = this._.on.apply(this._, arguments);
  return e === this._ ? this : e;
};
function MA(e) {
  return !e.ctrlKey && !e.button;
}
function PA() {
  return this.parentNode;
}
function qA(e, t) {
  return t ?? { x: e.x, y: e.y };
}
function OA() {
  return navigator.maxTouchPoints || "ontouchstart" in this;
}
function LA() {
  var e = MA,
    t = PA,
    n = qA,
    r = OA,
    i = {},
    o = Gs("start", "drag", "end"),
    a = 0,
    s,
    u,
    l,
    c,
    f = 0;
  function d(_) {
    _.on("mousedown.drag", h)
      .filter(r)
      .on("touchstart.drag", w)
      .on("touchmove.drag", p, AA)
      .on("touchend.drag touchcancel.drag", g)
      .style("touch-action", "none")
      .style("-webkit-tap-highlight-color", "rgba(0,0,0,0)");
  }
  function h(_, S) {
    if (!(c || !e.call(this, _, S))) {
      var E = y(this, t.call(this, _, S), _, S, "mouse");
      E &&
        (wt(_.view).on("mousemove.drag", m, Po).on("mouseup.drag", v, Po),
        Ob(_.view),
        Ku(_),
        (l = !1),
        (s = _.clientX),
        (u = _.clientY),
        E("start", _));
    }
  }
  function m(_) {
    if ((ai(_), !l)) {
      var S = _.clientX - s,
        E = _.clientY - u;
      l = S * S + E * E > f;
    }
    i.mouse("drag", _);
  }
  function v(_) {
    wt(_.view).on("mousemove.drag mouseup.drag", null), Lb(_.view, l), ai(_), i.mouse("end", _);
  }
  function w(_, S) {
    if (e.call(this, _, S)) {
      var E = _.changedTouches,
        k = t.call(this, _, S),
        C = E.length,
        T,
        I;
      for (T = 0; T < C; ++T)
        (I = y(this, k, _, S, E[T].identifier, E[T])) && (Ku(_), I("start", _, E[T]));
    }
  }
  function p(_) {
    var S = _.changedTouches,
      E = S.length,
      k,
      C;
    for (k = 0; k < E; ++k) (C = i[S[k].identifier]) && (ai(_), C("drag", _, S[k]));
  }
  function g(_) {
    var S = _.changedTouches,
      E = S.length,
      k,
      C;
    for (
      c && clearTimeout(c),
        c = setTimeout(function () {
          c = null;
        }, 500),
        k = 0;
      k < E;
      ++k
    )
      (C = i[S[k].identifier]) && (Ku(_), C("end", _, S[k]));
  }
  function y(_, S, E, k, C, T) {
    var I = o.copy(),
      M = Pt(T || E, S),
      z,
      F,
      x;
    if (
      (x = n.call(
        _,
        new Yp("beforestart", {
          sourceEvent: E,
          target: d,
          identifier: C,
          active: a,
          x: M[0],
          y: M[1],
          dx: 0,
          dy: 0,
          dispatch: I,
        }),
        k
      )) != null
    )
      return (
        (z = x.x - M[0] || 0),
        (F = x.y - M[1] || 0),
        function P(N, $, R) {
          var b = M,
            A;
          switch (N) {
            case "start":
              (i[C] = P), (A = a++);
              break;
            case "end":
              delete i[C], --a;
            case "drag":
              (M = Pt(R || $, S)), (A = a);
              break;
          }
          I.call(
            N,
            _,
            new Yp(N, {
              sourceEvent: $,
              subject: x,
              target: d,
              identifier: C,
              active: A,
              x: M[0] + z,
              y: M[1] + F,
              dx: M[0] - b[0],
              dy: M[1] - b[1],
              dispatch: I,
            }),
            k
          );
        }
      );
  }
  return (
    (d.filter = function (_) {
      return arguments.length ? ((e = typeof _ == "function" ? _ : _a(!!_)), d) : e;
    }),
    (d.container = function (_) {
      return arguments.length ? ((t = typeof _ == "function" ? _ : _a(_)), d) : t;
    }),
    (d.subject = function (_) {
      return arguments.length ? ((n = typeof _ == "function" ? _ : _a(_)), d) : n;
    }),
    (d.touchable = function (_) {
      return arguments.length ? ((r = typeof _ == "function" ? _ : _a(!!_)), d) : r;
    }),
    (d.on = function () {
      var _ = o.on.apply(o, arguments);
      return _ === o ? d : _;
    }),
    (d.clickDistance = function (_) {
      return arguments.length ? ((f = (_ = +_) * _), d) : Math.sqrt(f);
    }),
    d
  );
}
function cv(e, t, n) {
  (e.prototype = t.prototype = n), (n.constructor = e);
}
function zb(e, t) {
  var n = Object.create(e.prototype);
  for (var r in t) n[r] = t[r];
  return n;
}
function Ko() {}
var qo = 0.7,
  ms = 1 / qo,
  si = "\\s*([+-]?\\d+)\\s*",
  Oo = "\\s*([+-]?(?:\\d*\\.)?\\d+(?:[eE][+-]?\\d+)?)\\s*",
  Zt = "\\s*([+-]?(?:\\d*\\.)?\\d+(?:[eE][+-]?\\d+)?)%\\s*",
  zA = /^#([0-9a-f]{3,8})$/,
  $A = new RegExp(`^rgb\\(${si},${si},${si}\\)$`),
  DA = new RegExp(`^rgb\\(${Zt},${Zt},${Zt}\\)$`),
  FA = new RegExp(`^rgba\\(${si},${si},${si},${Oo}\\)$`),
  jA = new RegExp(`^rgba\\(${Zt},${Zt},${Zt},${Oo}\\)$`),
  BA = new RegExp(`^hsl\\(${Oo},${Zt},${Zt}\\)$`),
  HA = new RegExp(`^hsla\\(${Oo},${Zt},${Zt},${Oo}\\)$`),
  fy = {
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
cv(Ko, Lo, {
  copy(e) {
    return Object.assign(new this.constructor(), this, e);
  },
  displayable() {
    return this.rgb().displayable();
  },
  hex: dy,
  formatHex: dy,
  formatHex8: VA,
  formatHsl: UA,
  formatRgb: hy,
  toString: hy,
});
function dy() {
  return this.rgb().formatHex();
}
function VA() {
  return this.rgb().formatHex8();
}
function UA() {
  return $b(this).formatHsl();
}
function hy() {
  return this.rgb().formatRgb();
}
function Lo(e) {
  var t, n;
  return (
    (e = (e + "").trim().toLowerCase()),
    (t = zA.exec(e))
      ? ((n = t[1].length),
        (t = parseInt(t[1], 16)),
        n === 6
          ? py(t)
          : n === 3
          ? new it(
              ((t >> 8) & 15) | ((t >> 4) & 240),
              ((t >> 4) & 15) | (t & 240),
              ((t & 15) << 4) | (t & 15),
              1
            )
          : n === 8
          ? wa((t >> 24) & 255, (t >> 16) & 255, (t >> 8) & 255, (t & 255) / 255)
          : n === 4
          ? wa(
              ((t >> 12) & 15) | ((t >> 8) & 240),
              ((t >> 8) & 15) | ((t >> 4) & 240),
              ((t >> 4) & 15) | (t & 240),
              (((t & 15) << 4) | (t & 15)) / 255
            )
          : null)
      : (t = $A.exec(e))
      ? new it(t[1], t[2], t[3], 1)
      : (t = DA.exec(e))
      ? new it((t[1] * 255) / 100, (t[2] * 255) / 100, (t[3] * 255) / 100, 1)
      : (t = FA.exec(e))
      ? wa(t[1], t[2], t[3], t[4])
      : (t = jA.exec(e))
      ? wa((t[1] * 255) / 100, (t[2] * 255) / 100, (t[3] * 255) / 100, t[4])
      : (t = BA.exec(e))
      ? my(t[1], t[2] / 100, t[3] / 100, 1)
      : (t = HA.exec(e))
      ? my(t[1], t[2] / 100, t[3] / 100, t[4])
      : fy.hasOwnProperty(e)
      ? py(fy[e])
      : e === "transparent"
      ? new it(NaN, NaN, NaN, 0)
      : null
  );
}
function py(e) {
  return new it((e >> 16) & 255, (e >> 8) & 255, e & 255, 1);
}
function wa(e, t, n, r) {
  return r <= 0 && (e = t = n = NaN), new it(e, t, n, r);
}
function GA(e) {
  return (
    e instanceof Ko || (e = Lo(e)), e ? ((e = e.rgb()), new it(e.r, e.g, e.b, e.opacity)) : new it()
  );
}
function Xp(e, t, n, r) {
  return arguments.length === 1 ? GA(e) : new it(e, t, n, r ?? 1);
}
function it(e, t, n, r) {
  (this.r = +e), (this.g = +t), (this.b = +n), (this.opacity = +r);
}
cv(
  it,
  Xp,
  zb(Ko, {
    brighter(e) {
      return (
        (e = e == null ? ms : Math.pow(ms, e)),
        new it(this.r * e, this.g * e, this.b * e, this.opacity)
      );
    },
    darker(e) {
      return (
        (e = e == null ? qo : Math.pow(qo, e)),
        new it(this.r * e, this.g * e, this.b * e, this.opacity)
      );
    },
    rgb() {
      return this;
    },
    clamp() {
      return new it(_r(this.r), _r(this.g), _r(this.b), ys(this.opacity));
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
    hex: gy,
    formatHex: gy,
    formatHex8: WA,
    formatRgb: vy,
    toString: vy,
  })
);
function gy() {
  return `#${pr(this.r)}${pr(this.g)}${pr(this.b)}`;
}
function WA() {
  return `#${pr(this.r)}${pr(this.g)}${pr(this.b)}${pr(
    (isNaN(this.opacity) ? 1 : this.opacity) * 255
  )}`;
}
function vy() {
  const e = ys(this.opacity);
  return `${e === 1 ? "rgb(" : "rgba("}${_r(this.r)}, ${_r(this.g)}, ${_r(this.b)}${
    e === 1 ? ")" : `, ${e})`
  }`;
}
function ys(e) {
  return isNaN(e) ? 1 : Math.max(0, Math.min(1, e));
}
function _r(e) {
  return Math.max(0, Math.min(255, Math.round(e) || 0));
}
function pr(e) {
  return (e = _r(e)), (e < 16 ? "0" : "") + e.toString(16);
}
function my(e, t, n, r) {
  return (
    r <= 0 ? (e = t = n = NaN) : n <= 0 || n >= 1 ? (e = t = NaN) : t <= 0 && (e = NaN),
    new Ot(e, t, n, r)
  );
}
function $b(e) {
  if (e instanceof Ot) return new Ot(e.h, e.s, e.l, e.opacity);
  if ((e instanceof Ko || (e = Lo(e)), !e)) return new Ot();
  if (e instanceof Ot) return e;
  e = e.rgb();
  var t = e.r / 255,
    n = e.g / 255,
    r = e.b / 255,
    i = Math.min(t, n, r),
    o = Math.max(t, n, r),
    a = NaN,
    s = o - i,
    u = (o + i) / 2;
  return (
    s
      ? (t === o
          ? (a = (n - r) / s + (n < r) * 6)
          : n === o
          ? (a = (r - t) / s + 2)
          : (a = (t - n) / s + 4),
        (s /= u < 0.5 ? o + i : 2 - o - i),
        (a *= 60))
      : (s = u > 0 && u < 1 ? 0 : a),
    new Ot(a, s, u, e.opacity)
  );
}
function KA(e, t, n, r) {
  return arguments.length === 1 ? $b(e) : new Ot(e, t, n, r ?? 1);
}
function Ot(e, t, n, r) {
  (this.h = +e), (this.s = +t), (this.l = +n), (this.opacity = +r);
}
cv(
  Ot,
  KA,
  zb(Ko, {
    brighter(e) {
      return (
        (e = e == null ? ms : Math.pow(ms, e)), new Ot(this.h, this.s, this.l * e, this.opacity)
      );
    },
    darker(e) {
      return (
        (e = e == null ? qo : Math.pow(qo, e)), new Ot(this.h, this.s, this.l * e, this.opacity)
      );
    },
    rgb() {
      var e = (this.h % 360) + (this.h < 0) * 360,
        t = isNaN(e) || isNaN(this.s) ? 0 : this.s,
        n = this.l,
        r = n + (n < 0.5 ? n : 1 - n) * t,
        i = 2 * n - r;
      return new it(
        Yu(e >= 240 ? e - 240 : e + 120, i, r),
        Yu(e, i, r),
        Yu(e < 120 ? e + 240 : e - 120, i, r),
        this.opacity
      );
    },
    clamp() {
      return new Ot(yy(this.h), xa(this.s), xa(this.l), ys(this.opacity));
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
      const e = ys(this.opacity);
      return `${e === 1 ? "hsl(" : "hsla("}${yy(this.h)}, ${xa(this.s) * 100}%, ${
        xa(this.l) * 100
      }%${e === 1 ? ")" : `, ${e})`}`;
    },
  })
);
function yy(e) {
  return (e = (e || 0) % 360), e < 0 ? e + 360 : e;
}
function xa(e) {
  return Math.max(0, Math.min(1, e || 0));
}
function Yu(e, t, n) {
  return (
    (e < 60 ? t + ((n - t) * e) / 60 : e < 180 ? n : e < 240 ? t + ((n - t) * (240 - e)) / 60 : t) *
    255
  );
}
const Db = (e) => () => e;
function YA(e, t) {
  return function (n) {
    return e + n * t;
  };
}
function XA(e, t, n) {
  return (
    (e = Math.pow(e, n)),
    (t = Math.pow(t, n) - e),
    (n = 1 / n),
    function (r) {
      return Math.pow(e + r * t, n);
    }
  );
}
function QA(e) {
  return (e = +e) == 1
    ? Fb
    : function (t, n) {
        return n - t ? XA(t, n, e) : Db(isNaN(t) ? n : t);
      };
}
function Fb(e, t) {
  var n = t - e;
  return n ? YA(e, n) : Db(isNaN(e) ? t : e);
}
const _y = (function e(t) {
  var n = QA(t);
  function r(i, o) {
    var a = n((i = Xp(i)).r, (o = Xp(o)).r),
      s = n(i.g, o.g),
      u = n(i.b, o.b),
      l = Fb(i.opacity, o.opacity);
    return function (c) {
      return (i.r = a(c)), (i.g = s(c)), (i.b = u(c)), (i.opacity = l(c)), i + "";
    };
  }
  return (r.gamma = e), r;
})(1);
function On(e, t) {
  return (
    (e = +e),
    (t = +t),
    function (n) {
      return e * (1 - n) + t * n;
    }
  );
}
var Qp = /[-+]?(?:\d+\.?\d*|\.?\d+)(?:[eE][-+]?\d+)?/g,
  Xu = new RegExp(Qp.source, "g");
function ZA(e) {
  return function () {
    return e;
  };
}
function JA(e) {
  return function (t) {
    return e(t) + "";
  };
}
function eM(e, t) {
  var n = (Qp.lastIndex = Xu.lastIndex = 0),
    r,
    i,
    o,
    a = -1,
    s = [],
    u = [];
  for (e = e + "", t = t + ""; (r = Qp.exec(e)) && (i = Xu.exec(t)); )
    (o = i.index) > n && ((o = t.slice(n, o)), s[a] ? (s[a] += o) : (s[++a] = o)),
      (r = r[0]) === (i = i[0])
        ? s[a]
          ? (s[a] += i)
          : (s[++a] = i)
        : ((s[++a] = null), u.push({ i: a, x: On(r, i) })),
      (n = Xu.lastIndex);
  return (
    n < t.length && ((o = t.slice(n)), s[a] ? (s[a] += o) : (s[++a] = o)),
    s.length < 2
      ? u[0]
        ? JA(u[0].x)
        : ZA(t)
      : ((t = u.length),
        function (l) {
          for (var c = 0, f; c < t; ++c) s[(f = u[c]).i] = f.x(l);
          return s.join("");
        })
  );
}
var wy = 180 / Math.PI,
  Zp = { translateX: 0, translateY: 0, rotate: 0, skewX: 0, scaleX: 1, scaleY: 1 };
function jb(e, t, n, r, i, o) {
  var a, s, u;
  return (
    (a = Math.sqrt(e * e + t * t)) && ((e /= a), (t /= a)),
    (u = e * n + t * r) && ((n -= e * u), (r -= t * u)),
    (s = Math.sqrt(n * n + r * r)) && ((n /= s), (r /= s), (u /= s)),
    e * r < t * n && ((e = -e), (t = -t), (u = -u), (a = -a)),
    {
      translateX: i,
      translateY: o,
      rotate: Math.atan2(t, e) * wy,
      skewX: Math.atan(u) * wy,
      scaleX: a,
      scaleY: s,
    }
  );
}
var Sa;
function tM(e) {
  const t = new (typeof DOMMatrix == "function" ? DOMMatrix : WebKitCSSMatrix)(e + "");
  return t.isIdentity ? Zp : jb(t.a, t.b, t.c, t.d, t.e, t.f);
}
function nM(e) {
  return e == null ||
    (Sa || (Sa = document.createElementNS("http://www.w3.org/2000/svg", "g")),
    Sa.setAttribute("transform", e),
    !(e = Sa.transform.baseVal.consolidate()))
    ? Zp
    : ((e = e.matrix), jb(e.a, e.b, e.c, e.d, e.e, e.f));
}
function Bb(e, t, n, r) {
  function i(l) {
    return l.length ? l.pop() + " " : "";
  }
  function o(l, c, f, d, h, m) {
    if (l !== f || c !== d) {
      var v = h.push("translate(", null, t, null, n);
      m.push({ i: v - 4, x: On(l, f) }, { i: v - 2, x: On(c, d) });
    } else (f || d) && h.push("translate(" + f + t + d + n);
  }
  function a(l, c, f, d) {
    l !== c
      ? (l - c > 180 ? (c += 360) : c - l > 180 && (l += 360),
        d.push({ i: f.push(i(f) + "rotate(", null, r) - 2, x: On(l, c) }))
      : c && f.push(i(f) + "rotate(" + c + r);
  }
  function s(l, c, f, d) {
    l !== c
      ? d.push({ i: f.push(i(f) + "skewX(", null, r) - 2, x: On(l, c) })
      : c && f.push(i(f) + "skewX(" + c + r);
  }
  function u(l, c, f, d, h, m) {
    if (l !== f || c !== d) {
      var v = h.push(i(h) + "scale(", null, ",", null, ")");
      m.push({ i: v - 4, x: On(l, f) }, { i: v - 2, x: On(c, d) });
    } else (f !== 1 || d !== 1) && h.push(i(h) + "scale(" + f + "," + d + ")");
  }
  return function (l, c) {
    var f = [],
      d = [];
    return (
      (l = e(l)),
      (c = e(c)),
      o(l.translateX, l.translateY, c.translateX, c.translateY, f, d),
      a(l.rotate, c.rotate, f, d),
      s(l.skewX, c.skewX, f, d),
      u(l.scaleX, l.scaleY, c.scaleX, c.scaleY, f, d),
      (l = c = null),
      function (h) {
        for (var m = -1, v = d.length, w; ++m < v; ) f[(w = d[m]).i] = w.x(h);
        return f.join("");
      }
    );
  };
}
var rM = Bb(tM, "px, ", "px)", "deg)"),
  iM = Bb(nM, ", ", ")", ")"),
  oM = 1e-12;
function xy(e) {
  return ((e = Math.exp(e)) + 1 / e) / 2;
}
function aM(e) {
  return ((e = Math.exp(e)) - 1 / e) / 2;
}
function sM(e) {
  return ((e = Math.exp(2 * e)) - 1) / (e + 1);
}
const uM = (function e(t, n, r) {
  function i(o, a) {
    var s = o[0],
      u = o[1],
      l = o[2],
      c = a[0],
      f = a[1],
      d = a[2],
      h = c - s,
      m = f - u,
      v = h * h + m * m,
      w,
      p;
    if (v < oM)
      (p = Math.log(d / l) / t),
        (w = function (k) {
          return [s + k * h, u + k * m, l * Math.exp(t * k * p)];
        });
    else {
      var g = Math.sqrt(v),
        y = (d * d - l * l + r * v) / (2 * l * n * g),
        _ = (d * d - l * l - r * v) / (2 * d * n * g),
        S = Math.log(Math.sqrt(y * y + 1) - y),
        E = Math.log(Math.sqrt(_ * _ + 1) - _);
      (p = (E - S) / t),
        (w = function (k) {
          var C = k * p,
            T = xy(S),
            I = (l / (n * g)) * (T * sM(t * C + S) - aM(S));
          return [s + I * h, u + I * m, (l * T) / xy(t * C + S)];
        });
    }
    return (w.duration = (p * 1e3 * t) / Math.SQRT2), w;
  }
  return (
    (i.rho = function (o) {
      var a = Math.max(0.001, +o),
        s = a * a,
        u = s * s;
      return e(a, s, u);
    }),
    i
  );
})(Math.SQRT2, 2, 4);
var _i = 0,
  Qi = 0,
  Fi = 0,
  Hb = 1e3,
  _s,
  Zi,
  ws = 0,
  Cr = 0,
  Ks = 0,
  zo = typeof performance == "object" && performance.now ? performance : Date,
  Vb =
    typeof window == "object" && window.requestAnimationFrame
      ? window.requestAnimationFrame.bind(window)
      : function (e) {
          setTimeout(e, 17);
        };
function fv() {
  return Cr || (Vb(lM), (Cr = zo.now() + Ks));
}
function lM() {
  Cr = 0;
}
function xs() {
  this._call = this._time = this._next = null;
}
xs.prototype = Ub.prototype = {
  constructor: xs,
  restart: function (e, t, n) {
    if (typeof e != "function") throw new TypeError("callback is not a function");
    (n = (n == null ? fv() : +n) + (t == null ? 0 : +t)),
      !this._next && Zi !== this && (Zi ? (Zi._next = this) : (_s = this), (Zi = this)),
      (this._call = e),
      (this._time = n),
      Jp();
  },
  stop: function () {
    this._call && ((this._call = null), (this._time = 1 / 0), Jp());
  },
};
function Ub(e, t, n) {
  var r = new xs();
  return r.restart(e, t, n), r;
}
function cM() {
  fv(), ++_i;
  for (var e = _s, t; e; ) (t = Cr - e._time) >= 0 && e._call.call(void 0, t), (e = e._next);
  --_i;
}
function Sy() {
  (Cr = (ws = zo.now()) + Ks), (_i = Qi = 0);
  try {
    cM();
  } finally {
    (_i = 0), dM(), (Cr = 0);
  }
}
function fM() {
  var e = zo.now(),
    t = e - ws;
  t > Hb && ((Ks -= t), (ws = e));
}
function dM() {
  for (var e, t = _s, n, r = 1 / 0; t; )
    t._call
      ? (r > t._time && (r = t._time), (e = t), (t = t._next))
      : ((n = t._next), (t._next = null), (t = e ? (e._next = n) : (_s = n)));
  (Zi = e), Jp(r);
}
function Jp(e) {
  if (!_i) {
    Qi && (Qi = clearTimeout(Qi));
    var t = e - Cr;
    t > 24
      ? (e < 1 / 0 && (Qi = setTimeout(Sy, e - zo.now() - Ks)), Fi && (Fi = clearInterval(Fi)))
      : (Fi || ((ws = zo.now()), (Fi = setInterval(fM, Hb))), (_i = 1), Vb(Sy));
  }
}
function Ey(e, t, n) {
  var r = new xs();
  return (
    (t = t == null ? 0 : +t),
    r.restart(
      (i) => {
        r.stop(), e(i + t);
      },
      t,
      n
    ),
    r
  );
}
var hM = Gs("start", "end", "cancel", "interrupt"),
  pM = [],
  Gb = 0,
  by = 1,
  eg = 2,
  Ha = 3,
  ky = 4,
  tg = 5,
  Va = 6;
function Ys(e, t, n, r, i, o) {
  var a = e.__transition;
  if (!a) e.__transition = {};
  else if (n in a) return;
  gM(e, n, {
    name: t,
    index: r,
    group: i,
    on: hM,
    tween: pM,
    time: o.time,
    delay: o.delay,
    duration: o.duration,
    ease: o.ease,
    timer: null,
    state: Gb,
  });
}
function dv(e, t) {
  var n = Ft(e, t);
  if (n.state > Gb) throw new Error("too late; already scheduled");
  return n;
}
function Jt(e, t) {
  var n = Ft(e, t);
  if (n.state > Ha) throw new Error("too late; already running");
  return n;
}
function Ft(e, t) {
  var n = e.__transition;
  if (!n || !(n = n[t])) throw new Error("transition not found");
  return n;
}
function gM(e, t, n) {
  var r = e.__transition,
    i;
  (r[t] = n), (n.timer = Ub(o, 0, n.time));
  function o(l) {
    (n.state = by), n.timer.restart(a, n.delay, n.time), n.delay <= l && a(l - n.delay);
  }
  function a(l) {
    var c, f, d, h;
    if (n.state !== by) return u();
    for (c in r)
      if (((h = r[c]), h.name === n.name)) {
        if (h.state === Ha) return Ey(a);
        h.state === ky
          ? ((h.state = Va),
            h.timer.stop(),
            h.on.call("interrupt", e, e.__data__, h.index, h.group),
            delete r[c])
          : +c < t &&
            ((h.state = Va),
            h.timer.stop(),
            h.on.call("cancel", e, e.__data__, h.index, h.group),
            delete r[c]);
      }
    if (
      (Ey(function () {
        n.state === Ha && ((n.state = ky), n.timer.restart(s, n.delay, n.time), s(l));
      }),
      (n.state = eg),
      n.on.call("start", e, e.__data__, n.index, n.group),
      n.state === eg)
    ) {
      for (n.state = Ha, i = new Array((d = n.tween.length)), c = 0, f = -1; c < d; ++c)
        (h = n.tween[c].value.call(e, e.__data__, n.index, n.group)) && (i[++f] = h);
      i.length = f + 1;
    }
  }
  function s(l) {
    for (
      var c =
          l < n.duration
            ? n.ease.call(null, l / n.duration)
            : (n.timer.restart(u), (n.state = tg), 1),
        f = -1,
        d = i.length;
      ++f < d;

    )
      i[f].call(e, c);
    n.state === tg && (n.on.call("end", e, e.__data__, n.index, n.group), u());
  }
  function u() {
    (n.state = Va), n.timer.stop(), delete r[t];
    for (var l in r) return;
    delete e.__transition;
  }
}
function Ua(e, t) {
  var n = e.__transition,
    r,
    i,
    o = !0,
    a;
  if (n) {
    t = t == null ? null : t + "";
    for (a in n) {
      if ((r = n[a]).name !== t) {
        o = !1;
        continue;
      }
      (i = r.state > eg && r.state < tg),
        (r.state = Va),
        r.timer.stop(),
        r.on.call(i ? "interrupt" : "cancel", e, e.__data__, r.index, r.group),
        delete n[a];
    }
    o && delete e.__transition;
  }
}
function vM(e) {
  return this.each(function () {
    Ua(this, e);
  });
}
function mM(e, t) {
  var n, r;
  return function () {
    var i = Jt(this, e),
      o = i.tween;
    if (o !== n) {
      r = n = o;
      for (var a = 0, s = r.length; a < s; ++a)
        if (r[a].name === t) {
          (r = r.slice()), r.splice(a, 1);
          break;
        }
    }
    i.tween = r;
  };
}
function yM(e, t, n) {
  var r, i;
  if (typeof n != "function") throw new Error();
  return function () {
    var o = Jt(this, e),
      a = o.tween;
    if (a !== r) {
      i = (r = a).slice();
      for (var s = { name: t, value: n }, u = 0, l = i.length; u < l; ++u)
        if (i[u].name === t) {
          i[u] = s;
          break;
        }
      u === l && i.push(s);
    }
    o.tween = i;
  };
}
function _M(e, t) {
  var n = this._id;
  if (((e += ""), arguments.length < 2)) {
    for (var r = Ft(this.node(), n).tween, i = 0, o = r.length, a; i < o; ++i)
      if ((a = r[i]).name === e) return a.value;
    return null;
  }
  return this.each((t == null ? mM : yM)(n, e, t));
}
function hv(e, t, n) {
  var r = e._id;
  return (
    e.each(function () {
      var i = Jt(this, r);
      (i.value || (i.value = {}))[t] = n.apply(this, arguments);
    }),
    function (i) {
      return Ft(i, r).value[t];
    }
  );
}
function Wb(e, t) {
  var n;
  return (typeof t == "number" ? On : t instanceof Lo ? _y : (n = Lo(t)) ? ((t = n), _y) : eM)(
    e,
    t
  );
}
function wM(e) {
  return function () {
    this.removeAttribute(e);
  };
}
function xM(e) {
  return function () {
    this.removeAttributeNS(e.space, e.local);
  };
}
function SM(e, t, n) {
  var r,
    i = n + "",
    o;
  return function () {
    var a = this.getAttribute(e);
    return a === i ? null : a === r ? o : (o = t((r = a), n));
  };
}
function EM(e, t, n) {
  var r,
    i = n + "",
    o;
  return function () {
    var a = this.getAttributeNS(e.space, e.local);
    return a === i ? null : a === r ? o : (o = t((r = a), n));
  };
}
function bM(e, t, n) {
  var r, i, o;
  return function () {
    var a,
      s = n(this),
      u;
    return s == null
      ? void this.removeAttribute(e)
      : ((a = this.getAttribute(e)),
        (u = s + ""),
        a === u ? null : a === r && u === i ? o : ((i = u), (o = t((r = a), s))));
  };
}
function kM(e, t, n) {
  var r, i, o;
  return function () {
    var a,
      s = n(this),
      u;
    return s == null
      ? void this.removeAttributeNS(e.space, e.local)
      : ((a = this.getAttributeNS(e.space, e.local)),
        (u = s + ""),
        a === u ? null : a === r && u === i ? o : ((i = u), (o = t((r = a), s))));
  };
}
function CM(e, t) {
  var n = Ws(e),
    r = n === "transform" ? iM : Wb;
  return this.attrTween(
    e,
    typeof t == "function"
      ? (n.local ? kM : bM)(n, r, hv(this, "attr." + e, t))
      : t == null
      ? (n.local ? xM : wM)(n)
      : (n.local ? EM : SM)(n, r, t)
  );
}
function NM(e, t) {
  return function (n) {
    this.setAttribute(e, t.call(this, n));
  };
}
function RM(e, t) {
  return function (n) {
    this.setAttributeNS(e.space, e.local, t.call(this, n));
  };
}
function TM(e, t) {
  var n, r;
  function i() {
    var o = t.apply(this, arguments);
    return o !== r && (n = (r = o) && RM(e, o)), n;
  }
  return (i._value = t), i;
}
function IM(e, t) {
  var n, r;
  function i() {
    var o = t.apply(this, arguments);
    return o !== r && (n = (r = o) && NM(e, o)), n;
  }
  return (i._value = t), i;
}
function AM(e, t) {
  var n = "attr." + e;
  if (arguments.length < 2) return (n = this.tween(n)) && n._value;
  if (t == null) return this.tween(n, null);
  if (typeof t != "function") throw new Error();
  var r = Ws(e);
  return this.tween(n, (r.local ? TM : IM)(r, t));
}
function MM(e, t) {
  return function () {
    dv(this, e).delay = +t.apply(this, arguments);
  };
}
function PM(e, t) {
  return (
    (t = +t),
    function () {
      dv(this, e).delay = t;
    }
  );
}
function qM(e) {
  var t = this._id;
  return arguments.length
    ? this.each((typeof e == "function" ? MM : PM)(t, e))
    : Ft(this.node(), t).delay;
}
function OM(e, t) {
  return function () {
    Jt(this, e).duration = +t.apply(this, arguments);
  };
}
function LM(e, t) {
  return (
    (t = +t),
    function () {
      Jt(this, e).duration = t;
    }
  );
}
function zM(e) {
  var t = this._id;
  return arguments.length
    ? this.each((typeof e == "function" ? OM : LM)(t, e))
    : Ft(this.node(), t).duration;
}
function $M(e, t) {
  if (typeof t != "function") throw new Error();
  return function () {
    Jt(this, e).ease = t;
  };
}
function DM(e) {
  var t = this._id;
  return arguments.length ? this.each($M(t, e)) : Ft(this.node(), t).ease;
}
function FM(e, t) {
  return function () {
    var n = t.apply(this, arguments);
    if (typeof n != "function") throw new Error();
    Jt(this, e).ease = n;
  };
}
function jM(e) {
  if (typeof e != "function") throw new Error();
  return this.each(FM(this._id, e));
}
function BM(e) {
  typeof e != "function" && (e = kb(e));
  for (var t = this._groups, n = t.length, r = new Array(n), i = 0; i < n; ++i)
    for (var o = t[i], a = o.length, s = (r[i] = []), u, l = 0; l < a; ++l)
      (u = o[l]) && e.call(u, u.__data__, l, o) && s.push(u);
  return new xn(r, this._parents, this._name, this._id);
}
function HM(e) {
  if (e._id !== this._id) throw new Error();
  for (
    var t = this._groups,
      n = e._groups,
      r = t.length,
      i = n.length,
      o = Math.min(r, i),
      a = new Array(r),
      s = 0;
    s < o;
    ++s
  )
    for (var u = t[s], l = n[s], c = u.length, f = (a[s] = new Array(c)), d, h = 0; h < c; ++h)
      (d = u[h] || l[h]) && (f[h] = d);
  for (; s < r; ++s) a[s] = t[s];
  return new xn(a, this._parents, this._name, this._id);
}
function VM(e) {
  return (e + "")
    .trim()
    .split(/^|\s+/)
    .every(function (t) {
      var n = t.indexOf(".");
      return n >= 0 && (t = t.slice(0, n)), !t || t === "start";
    });
}
function UM(e, t, n) {
  var r,
    i,
    o = VM(t) ? dv : Jt;
  return function () {
    var a = o(this, e),
      s = a.on;
    s !== r && (i = (r = s).copy()).on(t, n), (a.on = i);
  };
}
function GM(e, t) {
  var n = this._id;
  return arguments.length < 2 ? Ft(this.node(), n).on.on(e) : this.each(UM(n, e, t));
}
function WM(e) {
  return function () {
    var t = this.parentNode;
    for (var n in this.__transition) if (+n !== e) return;
    t && t.removeChild(this);
  };
}
function KM() {
  return this.on("end.remove", WM(this._id));
}
function YM(e) {
  var t = this._name,
    n = this._id;
  typeof e != "function" && (e = uv(e));
  for (var r = this._groups, i = r.length, o = new Array(i), a = 0; a < i; ++a)
    for (var s = r[a], u = s.length, l = (o[a] = new Array(u)), c, f, d = 0; d < u; ++d)
      (c = s[d]) &&
        (f = e.call(c, c.__data__, d, s)) &&
        ("__data__" in c && (f.__data__ = c.__data__), (l[d] = f), Ys(l[d], t, n, d, l, Ft(c, n)));
  return new xn(o, this._parents, t, n);
}
function XM(e) {
  var t = this._name,
    n = this._id;
  typeof e != "function" && (e = bb(e));
  for (var r = this._groups, i = r.length, o = [], a = [], s = 0; s < i; ++s)
    for (var u = r[s], l = u.length, c, f = 0; f < l; ++f)
      if ((c = u[f])) {
        for (var d = e.call(c, c.__data__, f, u), h, m = Ft(c, n), v = 0, w = d.length; v < w; ++v)
          (h = d[v]) && Ys(h, t, n, v, d, m);
        o.push(d), a.push(c);
      }
  return new xn(o, a, t, n);
}
var QM = Wo.prototype.constructor;
function ZM() {
  return new QM(this._groups, this._parents);
}
function JM(e, t) {
  var n, r, i;
  return function () {
    var o = yi(this, e),
      a = (this.style.removeProperty(e), yi(this, e));
    return o === a ? null : o === n && a === r ? i : (i = t((n = o), (r = a)));
  };
}
function Kb(e) {
  return function () {
    this.style.removeProperty(e);
  };
}
function eP(e, t, n) {
  var r,
    i = n + "",
    o;
  return function () {
    var a = yi(this, e);
    return a === i ? null : a === r ? o : (o = t((r = a), n));
  };
}
function tP(e, t, n) {
  var r, i, o;
  return function () {
    var a = yi(this, e),
      s = n(this),
      u = s + "";
    return (
      s == null && (u = s = (this.style.removeProperty(e), yi(this, e))),
      a === u ? null : a === r && u === i ? o : ((i = u), (o = t((r = a), s)))
    );
  };
}
function nP(e, t) {
  var n,
    r,
    i,
    o = "style." + t,
    a = "end." + o,
    s;
  return function () {
    var u = Jt(this, e),
      l = u.on,
      c = u.value[o] == null ? s || (s = Kb(t)) : void 0;
    (l !== n || i !== c) && (r = (n = l).copy()).on(a, (i = c)), (u.on = r);
  };
}
function rP(e, t, n) {
  var r = (e += "") == "transform" ? rM : Wb;
  return t == null
    ? this.styleTween(e, JM(e, r)).on("end.style." + e, Kb(e))
    : typeof t == "function"
    ? this.styleTween(e, tP(e, r, hv(this, "style." + e, t))).each(nP(this._id, e))
    : this.styleTween(e, eP(e, r, t), n).on("end.style." + e, null);
}
function iP(e, t, n) {
  return function (r) {
    this.style.setProperty(e, t.call(this, r), n);
  };
}
function oP(e, t, n) {
  var r, i;
  function o() {
    var a = t.apply(this, arguments);
    return a !== i && (r = (i = a) && iP(e, a, n)), r;
  }
  return (o._value = t), o;
}
function aP(e, t, n) {
  var r = "style." + (e += "");
  if (arguments.length < 2) return (r = this.tween(r)) && r._value;
  if (t == null) return this.tween(r, null);
  if (typeof t != "function") throw new Error();
  return this.tween(r, oP(e, t, n ?? ""));
}
function sP(e) {
  return function () {
    this.textContent = e;
  };
}
function uP(e) {
  return function () {
    var t = e(this);
    this.textContent = t ?? "";
  };
}
function lP(e) {
  return this.tween(
    "text",
    typeof e == "function" ? uP(hv(this, "text", e)) : sP(e == null ? "" : e + "")
  );
}
function cP(e) {
  return function (t) {
    this.textContent = e.call(this, t);
  };
}
function fP(e) {
  var t, n;
  function r() {
    var i = e.apply(this, arguments);
    return i !== n && (t = (n = i) && cP(i)), t;
  }
  return (r._value = e), r;
}
function dP(e) {
  var t = "text";
  if (arguments.length < 1) return (t = this.tween(t)) && t._value;
  if (e == null) return this.tween(t, null);
  if (typeof e != "function") throw new Error();
  return this.tween(t, fP(e));
}
function hP() {
  for (
    var e = this._name, t = this._id, n = Yb(), r = this._groups, i = r.length, o = 0;
    o < i;
    ++o
  )
    for (var a = r[o], s = a.length, u, l = 0; l < s; ++l)
      if ((u = a[l])) {
        var c = Ft(u, t);
        Ys(u, e, n, l, a, {
          time: c.time + c.delay + c.duration,
          delay: 0,
          duration: c.duration,
          ease: c.ease,
        });
      }
  return new xn(r, this._parents, e, n);
}
function pP() {
  var e,
    t,
    n = this,
    r = n._id,
    i = n.size();
  return new Promise(function (o, a) {
    var s = { value: a },
      u = {
        value: function () {
          --i === 0 && o();
        },
      };
    n.each(function () {
      var l = Jt(this, r),
        c = l.on;
      c !== e && ((t = (e = c).copy()), t._.cancel.push(s), t._.interrupt.push(s), t._.end.push(u)),
        (l.on = t);
    }),
      i === 0 && o();
  });
}
var gP = 0;
function xn(e, t, n, r) {
  (this._groups = e), (this._parents = t), (this._name = n), (this._id = r);
}
function Yb() {
  return ++gP;
}
var on = Wo.prototype;
xn.prototype = {
  constructor: xn,
  select: YM,
  selectAll: XM,
  selectChild: on.selectChild,
  selectChildren: on.selectChildren,
  filter: BM,
  merge: HM,
  selection: ZM,
  transition: hP,
  call: on.call,
  nodes: on.nodes,
  node: on.node,
  size: on.size,
  empty: on.empty,
  each: on.each,
  on: GM,
  attr: CM,
  attrTween: AM,
  style: rP,
  styleTween: aP,
  text: lP,
  textTween: dP,
  remove: KM,
  tween: _M,
  delay: qM,
  duration: zM,
  ease: DM,
  easeVarying: jM,
  end: pP,
  [Symbol.iterator]: on[Symbol.iterator],
};
function vP(e) {
  return ((e *= 2) <= 1 ? e * e * e : (e -= 2) * e * e + 2) / 2;
}
var mP = { time: null, delay: 0, duration: 250, ease: vP };
function yP(e, t) {
  for (var n; !(n = e.__transition) || !(n = n[t]); )
    if (!(e = e.parentNode)) throw new Error(`transition ${t} not found`);
  return n;
}
function _P(e) {
  var t, n;
  e instanceof xn
    ? ((t = e._id), (e = e._name))
    : ((t = Yb()), ((n = mP).time = fv()), (e = e == null ? null : e + ""));
  for (var r = this._groups, i = r.length, o = 0; o < i; ++o)
    for (var a = r[o], s = a.length, u, l = 0; l < s; ++l)
      (u = a[l]) && Ys(u, e, t, l, a, n || yP(u, t));
  return new xn(r, this._parents, e, t);
}
Wo.prototype.interrupt = vM;
Wo.prototype.transition = _P;
const Ea = (e) => () => e;
function wP(e, { sourceEvent: t, target: n, transform: r, dispatch: i }) {
  Object.defineProperties(this, {
    type: { value: e, enumerable: !0, configurable: !0 },
    sourceEvent: { value: t, enumerable: !0, configurable: !0 },
    target: { value: n, enumerable: !0, configurable: !0 },
    transform: { value: r, enumerable: !0, configurable: !0 },
    _: { value: i },
  });
}
function dn(e, t, n) {
  (this.k = e), (this.x = t), (this.y = n);
}
dn.prototype = {
  constructor: dn,
  scale: function (e) {
    return e === 1 ? this : new dn(this.k * e, this.x, this.y);
  },
  translate: function (e, t) {
    return (e === 0) & (t === 0) ? this : new dn(this.k, this.x + this.k * e, this.y + this.k * t);
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
var vn = new dn(1, 0, 0);
dn.prototype;
function Qu(e) {
  e.stopImmediatePropagation();
}
function ji(e) {
  e.preventDefault(), e.stopImmediatePropagation();
}
function xP(e) {
  return (!e.ctrlKey || e.type === "wheel") && !e.button;
}
function SP() {
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
function Cy() {
  return this.__zoom || vn;
}
function EP(e) {
  return -e.deltaY * (e.deltaMode === 1 ? 0.05 : e.deltaMode ? 1 : 0.002) * (e.ctrlKey ? 10 : 1);
}
function bP() {
  return navigator.maxTouchPoints || "ontouchstart" in this;
}
function kP(e, t, n) {
  var r = e.invertX(t[0][0]) - n[0][0],
    i = e.invertX(t[1][0]) - n[1][0],
    o = e.invertY(t[0][1]) - n[0][1],
    a = e.invertY(t[1][1]) - n[1][1];
  return e.translate(
    i > r ? (r + i) / 2 : Math.min(0, r) || Math.max(0, i),
    a > o ? (o + a) / 2 : Math.min(0, o) || Math.max(0, a)
  );
}
function Xb() {
  var e = xP,
    t = SP,
    n = kP,
    r = EP,
    i = bP,
    o = [0, 1 / 0],
    a = [
      [-1 / 0, -1 / 0],
      [1 / 0, 1 / 0],
    ],
    s = 250,
    u = uM,
    l = Gs("start", "zoom", "end"),
    c,
    f,
    d,
    h = 500,
    m = 150,
    v = 0,
    w = 10;
  function p(x) {
    x.property("__zoom", Cy)
      .on("wheel.zoom", C, { passive: !1 })
      .on("mousedown.zoom", T)
      .on("dblclick.zoom", I)
      .filter(i)
      .on("touchstart.zoom", M)
      .on("touchmove.zoom", z)
      .on("touchend.zoom touchcancel.zoom", F)
      .style("-webkit-tap-highlight-color", "rgba(0,0,0,0)");
  }
  (p.transform = function (x, P, N, $) {
    var R = x.selection ? x.selection() : x;
    R.property("__zoom", Cy),
      x !== R
        ? S(x, P, N, $)
        : R.interrupt().each(function () {
            E(this, arguments)
              .event($)
              .start()
              .zoom(null, typeof P == "function" ? P.apply(this, arguments) : P)
              .end();
          });
  }),
    (p.scaleBy = function (x, P, N, $) {
      p.scaleTo(
        x,
        function () {
          var R = this.__zoom.k,
            b = typeof P == "function" ? P.apply(this, arguments) : P;
          return R * b;
        },
        N,
        $
      );
    }),
    (p.scaleTo = function (x, P, N, $) {
      p.transform(
        x,
        function () {
          var R = t.apply(this, arguments),
            b = this.__zoom,
            A = N == null ? _(R) : typeof N == "function" ? N.apply(this, arguments) : N,
            L = b.invert(A),
            D = typeof P == "function" ? P.apply(this, arguments) : P;
          return n(y(g(b, D), A, L), R, a);
        },
        N,
        $
      );
    }),
    (p.translateBy = function (x, P, N, $) {
      p.transform(
        x,
        function () {
          return n(
            this.__zoom.translate(
              typeof P == "function" ? P.apply(this, arguments) : P,
              typeof N == "function" ? N.apply(this, arguments) : N
            ),
            t.apply(this, arguments),
            a
          );
        },
        null,
        $
      );
    }),
    (p.translateTo = function (x, P, N, $, R) {
      p.transform(
        x,
        function () {
          var b = t.apply(this, arguments),
            A = this.__zoom,
            L = $ == null ? _(b) : typeof $ == "function" ? $.apply(this, arguments) : $;
          return n(
            vn
              .translate(L[0], L[1])
              .scale(A.k)
              .translate(
                typeof P == "function" ? -P.apply(this, arguments) : -P,
                typeof N == "function" ? -N.apply(this, arguments) : -N
              ),
            b,
            a
          );
        },
        $,
        R
      );
    });
  function g(x, P) {
    return (P = Math.max(o[0], Math.min(o[1], P))), P === x.k ? x : new dn(P, x.x, x.y);
  }
  function y(x, P, N) {
    var $ = P[0] - N[0] * x.k,
      R = P[1] - N[1] * x.k;
    return $ === x.x && R === x.y ? x : new dn(x.k, $, R);
  }
  function _(x) {
    return [(+x[0][0] + +x[1][0]) / 2, (+x[0][1] + +x[1][1]) / 2];
  }
  function S(x, P, N, $) {
    x.on("start.zoom", function () {
      E(this, arguments).event($).start();
    })
      .on("interrupt.zoom end.zoom", function () {
        E(this, arguments).event($).end();
      })
      .tween("zoom", function () {
        var R = this,
          b = arguments,
          A = E(R, b).event($),
          L = t.apply(R, b),
          D = N == null ? _(L) : typeof N == "function" ? N.apply(R, b) : N,
          H = Math.max(L[1][0] - L[0][0], L[1][1] - L[0][1]),
          B = R.__zoom,
          G = typeof P == "function" ? P.apply(R, b) : P,
          X = u(B.invert(D).concat(H / B.k), G.invert(D).concat(H / G.k));
        return function (J) {
          if (J === 1) J = G;
          else {
            var se = X(J),
              oe = H / se[2];
            J = new dn(oe, D[0] - se[0] * oe, D[1] - se[1] * oe);
          }
          A.zoom(null, J);
        };
      });
  }
  function E(x, P, N) {
    return (!N && x.__zooming) || new k(x, P);
  }
  function k(x, P) {
    (this.that = x),
      (this.args = P),
      (this.active = 0),
      (this.sourceEvent = null),
      (this.extent = t.apply(x, P)),
      (this.taps = 0);
  }
  k.prototype = {
    event: function (x) {
      return x && (this.sourceEvent = x), this;
    },
    start: function () {
      return ++this.active === 1 && ((this.that.__zooming = this), this.emit("start")), this;
    },
    zoom: function (x, P) {
      return (
        this.mouse && x !== "mouse" && (this.mouse[1] = P.invert(this.mouse[0])),
        this.touch0 && x !== "touch" && (this.touch0[1] = P.invert(this.touch0[0])),
        this.touch1 && x !== "touch" && (this.touch1[1] = P.invert(this.touch1[0])),
        (this.that.__zoom = P),
        this.emit("zoom"),
        this
      );
    },
    end: function () {
      return --this.active === 0 && (delete this.that.__zooming, this.emit("end")), this;
    },
    emit: function (x) {
      var P = wt(this.that).datum();
      l.call(
        x,
        this.that,
        new wP(x, {
          sourceEvent: this.sourceEvent,
          target: p,
          transform: this.that.__zoom,
          dispatch: l,
        }),
        P
      );
    },
  };
  function C(x, ...P) {
    if (!e.apply(this, arguments)) return;
    var N = E(this, P).event(x),
      $ = this.__zoom,
      R = Math.max(o[0], Math.min(o[1], $.k * Math.pow(2, r.apply(this, arguments)))),
      b = Pt(x);
    if (N.wheel)
      (N.mouse[0][0] !== b[0] || N.mouse[0][1] !== b[1]) &&
        (N.mouse[1] = $.invert((N.mouse[0] = b))),
        clearTimeout(N.wheel);
    else {
      if ($.k === R) return;
      (N.mouse = [b, $.invert(b)]), Ua(this), N.start();
    }
    ji(x),
      (N.wheel = setTimeout(A, m)),
      N.zoom("mouse", n(y(g($, R), N.mouse[0], N.mouse[1]), N.extent, a));
    function A() {
      (N.wheel = null), N.end();
    }
  }
  function T(x, ...P) {
    if (d || !e.apply(this, arguments)) return;
    var N = x.currentTarget,
      $ = E(this, P, !0).event(x),
      R = wt(x.view).on("mousemove.zoom", D, !0).on("mouseup.zoom", H, !0),
      b = Pt(x, N),
      A = x.clientX,
      L = x.clientY;
    Ob(x.view), Qu(x), ($.mouse = [b, this.__zoom.invert(b)]), Ua(this), $.start();
    function D(B) {
      if ((ji(B), !$.moved)) {
        var G = B.clientX - A,
          X = B.clientY - L;
        $.moved = G * G + X * X > v;
      }
      $.event(B).zoom(
        "mouse",
        n(y($.that.__zoom, ($.mouse[0] = Pt(B, N)), $.mouse[1]), $.extent, a)
      );
    }
    function H(B) {
      R.on("mousemove.zoom mouseup.zoom", null), Lb(B.view, $.moved), ji(B), $.event(B).end();
    }
  }
  function I(x, ...P) {
    if (e.apply(this, arguments)) {
      var N = this.__zoom,
        $ = Pt(x.changedTouches ? x.changedTouches[0] : x, this),
        R = N.invert($),
        b = N.k * (x.shiftKey ? 0.5 : 2),
        A = n(y(g(N, b), $, R), t.apply(this, P), a);
      ji(x),
        s > 0
          ? wt(this).transition().duration(s).call(S, A, $, x)
          : wt(this).call(p.transform, A, $, x);
    }
  }
  function M(x, ...P) {
    if (e.apply(this, arguments)) {
      var N = x.touches,
        $ = N.length,
        R = E(this, P, x.changedTouches.length === $).event(x),
        b,
        A,
        L,
        D;
      for (Qu(x), A = 0; A < $; ++A)
        (L = N[A]),
          (D = Pt(L, this)),
          (D = [D, this.__zoom.invert(D), L.identifier]),
          R.touch0
            ? !R.touch1 && R.touch0[2] !== D[2] && ((R.touch1 = D), (R.taps = 0))
            : ((R.touch0 = D), (b = !0), (R.taps = 1 + !!c));
      c && (c = clearTimeout(c)),
        b &&
          (R.taps < 2 &&
            ((f = D[0]),
            (c = setTimeout(function () {
              c = null;
            }, h))),
          Ua(this),
          R.start());
    }
  }
  function z(x, ...P) {
    if (this.__zooming) {
      var N = E(this, P).event(x),
        $ = x.changedTouches,
        R = $.length,
        b,
        A,
        L,
        D;
      for (ji(x), b = 0; b < R; ++b)
        (A = $[b]),
          (L = Pt(A, this)),
          N.touch0 && N.touch0[2] === A.identifier
            ? (N.touch0[0] = L)
            : N.touch1 && N.touch1[2] === A.identifier && (N.touch1[0] = L);
      if (((A = N.that.__zoom), N.touch1)) {
        var H = N.touch0[0],
          B = N.touch0[1],
          G = N.touch1[0],
          X = N.touch1[1],
          J = (J = G[0] - H[0]) * J + (J = G[1] - H[1]) * J,
          se = (se = X[0] - B[0]) * se + (se = X[1] - B[1]) * se;
        (A = g(A, Math.sqrt(J / se))),
          (L = [(H[0] + G[0]) / 2, (H[1] + G[1]) / 2]),
          (D = [(B[0] + X[0]) / 2, (B[1] + X[1]) / 2]);
      } else if (N.touch0) (L = N.touch0[0]), (D = N.touch0[1]);
      else return;
      N.zoom("touch", n(y(A, L, D), N.extent, a));
    }
  }
  function F(x, ...P) {
    if (this.__zooming) {
      var N = E(this, P).event(x),
        $ = x.changedTouches,
        R = $.length,
        b,
        A;
      for (
        Qu(x),
          d && clearTimeout(d),
          d = setTimeout(function () {
            d = null;
          }, h),
          b = 0;
        b < R;
        ++b
      )
        (A = $[b]),
          N.touch0 && N.touch0[2] === A.identifier
            ? delete N.touch0
            : N.touch1 && N.touch1[2] === A.identifier && delete N.touch1;
      if ((N.touch1 && !N.touch0 && ((N.touch0 = N.touch1), delete N.touch1), N.touch0))
        N.touch0[1] = this.__zoom.invert(N.touch0[0]);
      else if (
        (N.end(), N.taps === 2 && ((A = Pt(A, this)), Math.hypot(f[0] - A[0], f[1] - A[1]) < w))
      ) {
        var L = wt(this).on("dblclick.zoom");
        L && L.apply(this, arguments);
      }
    }
  }
  return (
    (p.wheelDelta = function (x) {
      return arguments.length ? ((r = typeof x == "function" ? x : Ea(+x)), p) : r;
    }),
    (p.filter = function (x) {
      return arguments.length ? ((e = typeof x == "function" ? x : Ea(!!x)), p) : e;
    }),
    (p.touchable = function (x) {
      return arguments.length ? ((i = typeof x == "function" ? x : Ea(!!x)), p) : i;
    }),
    (p.extent = function (x) {
      return arguments.length
        ? ((t =
            typeof x == "function"
              ? x
              : Ea([
                  [+x[0][0], +x[0][1]],
                  [+x[1][0], +x[1][1]],
                ])),
          p)
        : t;
    }),
    (p.scaleExtent = function (x) {
      return arguments.length ? ((o[0] = +x[0]), (o[1] = +x[1]), p) : [o[0], o[1]];
    }),
    (p.translateExtent = function (x) {
      return arguments.length
        ? ((a[0][0] = +x[0][0]),
          (a[1][0] = +x[1][0]),
          (a[0][1] = +x[0][1]),
          (a[1][1] = +x[1][1]),
          p)
        : [
            [a[0][0], a[0][1]],
            [a[1][0], a[1][1]],
          ];
    }),
    (p.constrain = function (x) {
      return arguments.length ? ((n = x), p) : n;
    }),
    (p.duration = function (x) {
      return arguments.length ? ((s = +x), p) : s;
    }),
    (p.interpolate = function (x) {
      return arguments.length ? ((u = x), p) : u;
    }),
    (p.on = function () {
      var x = l.on.apply(l, arguments);
      return x === l ? p : x;
    }),
    (p.clickDistance = function (x) {
      return arguments.length ? ((v = (x = +x) * x), p) : Math.sqrt(v);
    }),
    (p.tapDistance = function (x) {
      return arguments.length ? ((w = +x), p) : w;
    }),
    p
  );
}
const Xs = q.createContext(null),
  CP = Xs.Provider,
  Sn = {
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
      `Couldn't create edge for ${e ? "target" : "source"} handle id: "${
        e ? t.targetHandle : t.sourceHandle
      }", edge id: ${t.id}.`,
    error010: () =>
      "Handle: No node id found. Make sure to only use a Handle inside a custom Node.",
    error011: (e) => `Edge type "${e}" not found. Using fallback type "default".`,
    error012: (e) =>
      `Node with id "${e}" does not exist, it may have been removed. This can happen when a node is deleted before the "onNodeClick" handler is called.`,
  },
  Qb = Sn.error001();
function fe(e, t) {
  const n = q.useContext(Xs);
  if (n === null) throw new Error(Qb);
  return Sb(n, e, t);
}
const Ae = () => {
    const e = q.useContext(Xs);
    if (e === null) throw new Error(Qb);
    return q.useMemo(
      () => ({
        getState: e.getState,
        setState: e.setState,
        subscribe: e.subscribe,
        destroy: e.destroy,
      }),
      [e]
    );
  },
  NP = (e) => (e.userSelectionActive ? "none" : "all");
function pv({ position: e, children: t, className: n, style: r, ...i }) {
  const o = fe(NP),
    a = `${e}`.split("-");
  return O.createElement(
    "div",
    { className: Be(["react-flow__panel", n, ...a]), style: { ...r, pointerEvents: o }, ...i },
    t
  );
}
function RP({ proOptions: e, position: t = "bottom-right" }) {
  return e != null && e.hideAttribution
    ? null
    : O.createElement(
        pv,
        {
          position: t,
          className: "react-flow__attribution",
          "data-message":
            "Please only hide this attribution when you are subscribed to React Flow Pro: https://reactflow.dev/pro",
        },
        O.createElement(
          "a",
          {
            href: "https://reactflow.dev",
            target: "_blank",
            rel: "noopener noreferrer",
            "aria-label": "React Flow attribution",
          },
          "React Flow"
        )
      );
}
const TP = ({
  x: e,
  y: t,
  label: n,
  labelStyle: r = {},
  labelShowBg: i = !0,
  labelBgStyle: o = {},
  labelBgPadding: a = [2, 4],
  labelBgBorderRadius: s = 2,
  children: u,
  className: l,
  ...c
}) => {
  const f = q.useRef(null),
    [d, h] = q.useState({ x: 0, y: 0, width: 0, height: 0 }),
    m = Be(["react-flow__edge-textwrapper", l]);
  return (
    q.useEffect(() => {
      if (f.current) {
        const v = f.current.getBBox();
        h({ x: v.x, y: v.y, width: v.width, height: v.height });
      }
    }, [n]),
    typeof n > "u" || !n
      ? null
      : O.createElement(
          "g",
          {
            transform: `translate(${e - d.width / 2} ${t - d.height / 2})`,
            className: m,
            visibility: d.width ? "visible" : "hidden",
            ...c,
          },
          i &&
            O.createElement("rect", {
              width: d.width + 2 * a[0],
              x: -a[0],
              y: -a[1],
              height: d.height + 2 * a[1],
              className: "react-flow__edge-textbg",
              style: o,
              rx: s,
              ry: s,
            }),
          O.createElement(
            "text",
            { className: "react-flow__edge-text", y: d.height / 2, dy: "0.3em", ref: f, style: r },
            n
          ),
          u
        )
  );
};
var IP = q.memo(TP);
const gv = (e) => ({ width: e.offsetWidth, height: e.offsetHeight }),
  wi = (e, t = 0, n = 1) => Math.min(Math.max(e, t), n),
  vv = (e = { x: 0, y: 0 }, t) => ({ x: wi(e.x, t[0][0], t[1][0]), y: wi(e.y, t[0][1], t[1][1]) }),
  Ny = (e, t, n) =>
    e < t ? wi(Math.abs(e - t), 1, 50) / 50 : e > n ? -wi(Math.abs(e - n), 1, 50) / 50 : 0,
  Zb = (e, t) => {
    const n = Ny(e.x, 35, t.width - 35) * 20,
      r = Ny(e.y, 35, t.height - 35) * 20;
    return [n, r];
  },
  Jb = (e) => {
    var t;
    return (
      ((t = e.getRootNode) == null ? void 0 : t.call(e)) ||
      (window == null ? void 0 : window.document)
    );
  },
  ek = (e, t) => ({
    x: Math.min(e.x, t.x),
    y: Math.min(e.y, t.y),
    x2: Math.max(e.x2, t.x2),
    y2: Math.max(e.y2, t.y2),
  }),
  $o = ({ x: e, y: t, width: n, height: r }) => ({ x: e, y: t, x2: e + n, y2: t + r }),
  tk = ({ x: e, y: t, x2: n, y2: r }) => ({ x: e, y: t, width: n - e, height: r - t }),
  Ry = (e) => ({
    ...(e.positionAbsolute || { x: 0, y: 0 }),
    width: e.width || 0,
    height: e.height || 0,
  }),
  AP = (e, t) => tk(ek($o(e), $o(t))),
  ng = (e, t) => {
    const n = Math.max(0, Math.min(e.x + e.width, t.x + t.width) - Math.max(e.x, t.x)),
      r = Math.max(0, Math.min(e.y + e.height, t.y + t.height) - Math.max(e.y, t.y));
    return Math.ceil(n * r);
  },
  MP = (e) => St(e.width) && St(e.height) && St(e.x) && St(e.y),
  St = (e) => !isNaN(e) && isFinite(e),
  Se = Symbol.for("internals"),
  nk = ["Enter", " ", "Escape"],
  PP = (e, t) => {},
  qP = (e) => "nativeEvent" in e;
function rg(e) {
  var i, o;
  const t = qP(e) ? e.nativeEvent : e,
    n =
      ((o = (i = t.composedPath) == null ? void 0 : i.call(t)) == null ? void 0 : o[0]) || e.target;
  return (
    ["INPUT", "SELECT", "TEXTAREA"].includes(n == null ? void 0 : n.nodeName) ||
    (n == null ? void 0 : n.hasAttribute("contenteditable")) ||
    !!(n != null && n.closest(".nokey"))
  );
}
const rk = (e) => "clientX" in e,
  Qn = (e, t) => {
    var o, a;
    const n = rk(e),
      r = n ? e.clientX : (o = e.touches) == null ? void 0 : o[0].clientX,
      i = n ? e.clientY : (a = e.touches) == null ? void 0 : a[0].clientY;
    return {
      x: r - ((t == null ? void 0 : t.left) ?? 0),
      y: i - ((t == null ? void 0 : t.top) ?? 0),
    };
  },
  Ss = () => {
    var e;
    return (
      typeof navigator < "u" &&
      ((e = navigator == null ? void 0 : navigator.userAgent) == null
        ? void 0
        : e.indexOf("Mac")) >= 0
    );
  },
  Yo = ({
    id: e,
    path: t,
    labelX: n,
    labelY: r,
    label: i,
    labelStyle: o,
    labelShowBg: a,
    labelBgStyle: s,
    labelBgPadding: u,
    labelBgBorderRadius: l,
    style: c,
    markerEnd: f,
    markerStart: d,
    interactionWidth: h = 20,
  }) =>
    O.createElement(
      O.Fragment,
      null,
      O.createElement("path", {
        id: e,
        style: c,
        d: t,
        fill: "none",
        className: "react-flow__edge-path",
        markerEnd: f,
        markerStart: d,
      }),
      h &&
        O.createElement("path", {
          d: t,
          fill: "none",
          strokeOpacity: 0,
          strokeWidth: h,
          className: "react-flow__edge-interaction",
        }),
      i && St(n) && St(r)
        ? O.createElement(IP, {
            x: n,
            y: r,
            label: i,
            labelStyle: o,
            labelShowBg: a,
            labelBgStyle: s,
            labelBgPadding: u,
            labelBgBorderRadius: l,
          })
        : null
    );
Yo.displayName = "BaseEdge";
function Bi(e, t, n) {
  return n === void 0
    ? n
    : (r) => {
        const i = t().edges.find((o) => o.id === e);
        i && n(r, { ...i });
      };
}
function ik({ sourceX: e, sourceY: t, targetX: n, targetY: r }) {
  const i = Math.abs(n - e) / 2,
    o = n < e ? n + i : n - i,
    a = Math.abs(r - t) / 2,
    s = r < t ? r + a : r - a;
  return [o, s, i, a];
}
function ok({
  sourceX: e,
  sourceY: t,
  targetX: n,
  targetY: r,
  sourceControlX: i,
  sourceControlY: o,
  targetControlX: a,
  targetControlY: s,
}) {
  const u = e * 0.125 + i * 0.375 + a * 0.375 + n * 0.125,
    l = t * 0.125 + o * 0.375 + s * 0.375 + r * 0.125,
    c = Math.abs(u - e),
    f = Math.abs(l - t);
  return [u, l, c, f];
}
var Nr;
(function (e) {
  (e.Strict = "strict"), (e.Loose = "loose");
})(Nr || (Nr = {}));
var gr;
(function (e) {
  (e.Free = "free"), (e.Vertical = "vertical"), (e.Horizontal = "horizontal");
})(gr || (gr = {}));
var Do;
(function (e) {
  (e.Partial = "partial"), (e.Full = "full");
})(Do || (Do = {}));
var Dn;
(function (e) {
  (e.Bezier = "default"),
    (e.Straight = "straight"),
    (e.Step = "step"),
    (e.SmoothStep = "smoothstep"),
    (e.SimpleBezier = "simplebezier");
})(Dn || (Dn = {}));
var Fo;
(function (e) {
  (e.Arrow = "arrow"), (e.ArrowClosed = "arrowclosed");
})(Fo || (Fo = {}));
var Y;
(function (e) {
  (e.Left = "left"), (e.Top = "top"), (e.Right = "right"), (e.Bottom = "bottom");
})(Y || (Y = {}));
function Ty({ pos: e, x1: t, y1: n, x2: r, y2: i }) {
  return e === Y.Left || e === Y.Right ? [0.5 * (t + r), n] : [t, 0.5 * (n + i)];
}
function ak({
  sourceX: e,
  sourceY: t,
  sourcePosition: n = Y.Bottom,
  targetX: r,
  targetY: i,
  targetPosition: o = Y.Top,
}) {
  const [a, s] = Ty({ pos: n, x1: e, y1: t, x2: r, y2: i }),
    [u, l] = Ty({ pos: o, x1: r, y1: i, x2: e, y2: t }),
    [c, f, d, h] = ok({
      sourceX: e,
      sourceY: t,
      targetX: r,
      targetY: i,
      sourceControlX: a,
      sourceControlY: s,
      targetControlX: u,
      targetControlY: l,
    });
  return [`M${e},${t} C${a},${s} ${u},${l} ${r},${i}`, c, f, d, h];
}
const mv = q.memo(
  ({
    sourceX: e,
    sourceY: t,
    targetX: n,
    targetY: r,
    sourcePosition: i = Y.Bottom,
    targetPosition: o = Y.Top,
    label: a,
    labelStyle: s,
    labelShowBg: u,
    labelBgStyle: l,
    labelBgPadding: c,
    labelBgBorderRadius: f,
    style: d,
    markerEnd: h,
    markerStart: m,
    interactionWidth: v,
  }) => {
    const [w, p, g] = ak({
      sourceX: e,
      sourceY: t,
      sourcePosition: i,
      targetX: n,
      targetY: r,
      targetPosition: o,
    });
    return O.createElement(Yo, {
      path: w,
      labelX: p,
      labelY: g,
      label: a,
      labelStyle: s,
      labelShowBg: u,
      labelBgStyle: l,
      labelBgPadding: c,
      labelBgBorderRadius: f,
      style: d,
      markerEnd: h,
      markerStart: m,
      interactionWidth: v,
    });
  }
);
mv.displayName = "SimpleBezierEdge";
const Iy = {
    [Y.Left]: { x: -1, y: 0 },
    [Y.Right]: { x: 1, y: 0 },
    [Y.Top]: { x: 0, y: -1 },
    [Y.Bottom]: { x: 0, y: 1 },
  },
  OP = ({ source: e, sourcePosition: t = Y.Bottom, target: n }) =>
    t === Y.Left || t === Y.Right
      ? e.x < n.x
        ? { x: 1, y: 0 }
        : { x: -1, y: 0 }
      : e.y < n.y
      ? { x: 0, y: 1 }
      : { x: 0, y: -1 },
  Ay = (e, t) => Math.sqrt(Math.pow(t.x - e.x, 2) + Math.pow(t.y - e.y, 2));
function LP({
  source: e,
  sourcePosition: t = Y.Bottom,
  target: n,
  targetPosition: r = Y.Top,
  center: i,
  offset: o,
}) {
  const a = Iy[t],
    s = Iy[r],
    u = { x: e.x + a.x * o, y: e.y + a.y * o },
    l = { x: n.x + s.x * o, y: n.y + s.y * o },
    c = OP({ source: u, sourcePosition: t, target: l }),
    f = c.x !== 0 ? "x" : "y",
    d = c[f];
  let h = [],
    m,
    v;
  const w = { x: 0, y: 0 },
    p = { x: 0, y: 0 },
    [g, y, _, S] = ik({ sourceX: e.x, sourceY: e.y, targetX: n.x, targetY: n.y });
  if (a[f] * s[f] === -1) {
    (m = i.x ?? g), (v = i.y ?? y);
    const k = [
        { x: m, y: u.y },
        { x: m, y: l.y },
      ],
      C = [
        { x: u.x, y: v },
        { x: l.x, y: v },
      ];
    a[f] === d ? (h = f === "x" ? k : C) : (h = f === "x" ? C : k);
  } else {
    const k = [{ x: u.x, y: l.y }],
      C = [{ x: l.x, y: u.y }];
    if ((f === "x" ? (h = a.x === d ? C : k) : (h = a.y === d ? k : C), t === r)) {
      const F = Math.abs(e[f] - n[f]);
      if (F <= o) {
        const x = Math.min(o - 1, o - F);
        a[f] === d ? (w[f] = (u[f] > e[f] ? -1 : 1) * x) : (p[f] = (l[f] > n[f] ? -1 : 1) * x);
      }
    }
    if (t !== r) {
      const F = f === "x" ? "y" : "x",
        x = a[f] === s[F],
        P = u[F] > l[F],
        N = u[F] < l[F];
      ((a[f] === 1 && ((!x && P) || (x && N))) || (a[f] !== 1 && ((!x && N) || (x && P)))) &&
        (h = f === "x" ? k : C);
    }
    const T = { x: u.x + w.x, y: u.y + w.y },
      I = { x: l.x + p.x, y: l.y + p.y },
      M = Math.max(Math.abs(T.x - h[0].x), Math.abs(I.x - h[0].x)),
      z = Math.max(Math.abs(T.y - h[0].y), Math.abs(I.y - h[0].y));
    M >= z ? ((m = (T.x + I.x) / 2), (v = h[0].y)) : ((m = h[0].x), (v = (T.y + I.y) / 2));
  }
  return [[e, { x: u.x + w.x, y: u.y + w.y }, ...h, { x: l.x + p.x, y: l.y + p.y }, n], m, v, _, S];
}
function zP(e, t, n, r) {
  const i = Math.min(Ay(e, t) / 2, Ay(t, n) / 2, r),
    { x: o, y: a } = t;
  if ((e.x === o && o === n.x) || (e.y === a && a === n.y)) return `L${o} ${a}`;
  if (e.y === a) {
    const l = e.x < n.x ? -1 : 1,
      c = e.y < n.y ? 1 : -1;
    return `L ${o + i * l},${a}Q ${o},${a} ${o},${a + i * c}`;
  }
  const s = e.x < n.x ? 1 : -1,
    u = e.y < n.y ? -1 : 1;
  return `L ${o},${a + i * u}Q ${o},${a} ${o + i * s},${a}`;
}
function ig({
  sourceX: e,
  sourceY: t,
  sourcePosition: n = Y.Bottom,
  targetX: r,
  targetY: i,
  targetPosition: o = Y.Top,
  borderRadius: a = 5,
  centerX: s,
  centerY: u,
  offset: l = 20,
}) {
  const [c, f, d, h, m] = LP({
    source: { x: e, y: t },
    sourcePosition: n,
    target: { x: r, y: i },
    targetPosition: o,
    center: { x: s, y: u },
    offset: l,
  });
  return [
    c.reduce((w, p, g) => {
      let y = "";
      return (
        g > 0 && g < c.length - 1
          ? (y = zP(c[g - 1], p, c[g + 1], a))
          : (y = `${g === 0 ? "M" : "L"}${p.x} ${p.y}`),
        (w += y),
        w
      );
    }, ""),
    f,
    d,
    h,
    m,
  ];
}
const Qs = q.memo(
  ({
    sourceX: e,
    sourceY: t,
    targetX: n,
    targetY: r,
    label: i,
    labelStyle: o,
    labelShowBg: a,
    labelBgStyle: s,
    labelBgPadding: u,
    labelBgBorderRadius: l,
    style: c,
    sourcePosition: f = Y.Bottom,
    targetPosition: d = Y.Top,
    markerEnd: h,
    markerStart: m,
    pathOptions: v,
    interactionWidth: w,
  }) => {
    const [p, g, y] = ig({
      sourceX: e,
      sourceY: t,
      sourcePosition: f,
      targetX: n,
      targetY: r,
      targetPosition: d,
      borderRadius: v == null ? void 0 : v.borderRadius,
      offset: v == null ? void 0 : v.offset,
    });
    return O.createElement(Yo, {
      path: p,
      labelX: g,
      labelY: y,
      label: i,
      labelStyle: o,
      labelShowBg: a,
      labelBgStyle: s,
      labelBgPadding: u,
      labelBgBorderRadius: l,
      style: c,
      markerEnd: h,
      markerStart: m,
      interactionWidth: w,
    });
  }
);
Qs.displayName = "SmoothStepEdge";
const yv = q.memo((e) => {
  var t;
  return O.createElement(Qs, {
    ...e,
    pathOptions: q.useMemo(() => {
      var n;
      return { borderRadius: 0, offset: (n = e.pathOptions) == null ? void 0 : n.offset };
    }, [(t = e.pathOptions) == null ? void 0 : t.offset]),
  });
});
yv.displayName = "StepEdge";
function $P({ sourceX: e, sourceY: t, targetX: n, targetY: r }) {
  const [i, o, a, s] = ik({ sourceX: e, sourceY: t, targetX: n, targetY: r });
  return [`M ${e},${t}L ${n},${r}`, i, o, a, s];
}
const _v = q.memo(
  ({
    sourceX: e,
    sourceY: t,
    targetX: n,
    targetY: r,
    label: i,
    labelStyle: o,
    labelShowBg: a,
    labelBgStyle: s,
    labelBgPadding: u,
    labelBgBorderRadius: l,
    style: c,
    markerEnd: f,
    markerStart: d,
    interactionWidth: h,
  }) => {
    const [m, v, w] = $P({ sourceX: e, sourceY: t, targetX: n, targetY: r });
    return O.createElement(Yo, {
      path: m,
      labelX: v,
      labelY: w,
      label: i,
      labelStyle: o,
      labelShowBg: a,
      labelBgStyle: s,
      labelBgPadding: u,
      labelBgBorderRadius: l,
      style: c,
      markerEnd: f,
      markerStart: d,
      interactionWidth: h,
    });
  }
);
_v.displayName = "StraightEdge";
function ba(e, t) {
  return e >= 0 ? 0.5 * e : t * 25 * Math.sqrt(-e);
}
function My({ pos: e, x1: t, y1: n, x2: r, y2: i, c: o }) {
  switch (e) {
    case Y.Left:
      return [t - ba(t - r, o), n];
    case Y.Right:
      return [t + ba(r - t, o), n];
    case Y.Top:
      return [t, n - ba(n - i, o)];
    case Y.Bottom:
      return [t, n + ba(i - n, o)];
  }
}
function sk({
  sourceX: e,
  sourceY: t,
  sourcePosition: n = Y.Bottom,
  targetX: r,
  targetY: i,
  targetPosition: o = Y.Top,
  curvature: a = 0.25,
}) {
  const [s, u] = My({ pos: n, x1: e, y1: t, x2: r, y2: i, c: a }),
    [l, c] = My({ pos: o, x1: r, y1: i, x2: e, y2: t, c: a }),
    [f, d, h, m] = ok({
      sourceX: e,
      sourceY: t,
      targetX: r,
      targetY: i,
      sourceControlX: s,
      sourceControlY: u,
      targetControlX: l,
      targetControlY: c,
    });
  return [`M${e},${t} C${s},${u} ${l},${c} ${r},${i}`, f, d, h, m];
}
const Es = q.memo(
  ({
    sourceX: e,
    sourceY: t,
    targetX: n,
    targetY: r,
    sourcePosition: i = Y.Bottom,
    targetPosition: o = Y.Top,
    label: a,
    labelStyle: s,
    labelShowBg: u,
    labelBgStyle: l,
    labelBgPadding: c,
    labelBgBorderRadius: f,
    style: d,
    markerEnd: h,
    markerStart: m,
    pathOptions: v,
    interactionWidth: w,
  }) => {
    const [p, g, y] = sk({
      sourceX: e,
      sourceY: t,
      sourcePosition: i,
      targetX: n,
      targetY: r,
      targetPosition: o,
      curvature: v == null ? void 0 : v.curvature,
    });
    return O.createElement(Yo, {
      path: p,
      labelX: g,
      labelY: y,
      label: a,
      labelStyle: s,
      labelShowBg: u,
      labelBgStyle: l,
      labelBgPadding: c,
      labelBgBorderRadius: f,
      style: d,
      markerEnd: h,
      markerStart: m,
      interactionWidth: w,
    });
  }
);
Es.displayName = "BezierEdge";
const wv = q.createContext(null),
  DP = wv.Provider;
wv.Consumer;
const FP = () => q.useContext(wv),
  jP = (e) => "id" in e && "source" in e && "target" in e,
  BP = ({ source: e, sourceHandle: t, target: n, targetHandle: r }) =>
    `reactflow__edge-${e}${t || ""}-${n}${r || ""}`,
  og = (e, t) =>
    typeof e > "u"
      ? ""
      : typeof e == "string"
      ? e
      : `${t ? `${t}__` : ""}${Object.keys(e)
          .sort()
          .map((r) => `${r}=${e[r]}`)
          .join("&")}`,
  HP = (e, t) =>
    t.some(
      (n) =>
        n.source === e.source &&
        n.target === e.target &&
        (n.sourceHandle === e.sourceHandle || (!n.sourceHandle && !e.sourceHandle)) &&
        (n.targetHandle === e.targetHandle || (!n.targetHandle && !e.targetHandle))
    ),
  VP = (e, t) => {
    if (!e.source || !e.target) return t;
    let n;
    return jP(e) ? (n = { ...e }) : (n = { ...e, id: BP(e) }), HP(n, t) ? t : t.concat(n);
  },
  ag = ({ x: e, y: t }, [n, r, i], o, [a, s]) => {
    const u = { x: (e - n) / i, y: (t - r) / i };
    return o ? { x: a * Math.round(u.x / a), y: s * Math.round(u.y / s) } : u;
  },
  uk = ({ x: e, y: t }, [n, r, i]) => ({ x: e * i + n, y: t * i + r }),
  wr = (e, t = [0, 0]) => {
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
  Zs = (e, t = [0, 0]) => {
    if (e.length === 0) return { x: 0, y: 0, width: 0, height: 0 };
    const n = e.reduce(
      (r, i) => {
        const { x: o, y: a } = wr(i, t).positionAbsolute;
        return ek(r, $o({ x: o, y: a, width: i.width || 0, height: i.height || 0 }));
      },
      { x: 1 / 0, y: 1 / 0, x2: -1 / 0, y2: -1 / 0 }
    );
    return tk(n);
  },
  lk = (e, t, [n, r, i] = [0, 0, 1], o = !1, a = !1, s = [0, 0]) => {
    const u = { x: (t.x - n) / i, y: (t.y - r) / i, width: t.width / i, height: t.height / i },
      l = [];
    return (
      e.forEach((c) => {
        const { width: f, height: d, selectable: h = !0, hidden: m = !1 } = c;
        if ((a && !h) || m) return !1;
        const { positionAbsolute: v } = wr(c, s),
          w = { x: v.x, y: v.y, width: f || 0, height: d || 0 },
          p = ng(u, w),
          g = typeof f > "u" || typeof d > "u" || f === null || d === null,
          y = o && p > 0,
          _ = (f || 0) * (d || 0);
        (g || y || p >= _ || c.dragging) && l.push(c);
      }),
      l
    );
  },
  ck = (e, t) => {
    const n = e.map((r) => r.id);
    return t.filter((r) => n.includes(r.source) || n.includes(r.target));
  },
  fk = (e, t, n, r, i, o = 0.1) => {
    const a = t / (e.width * (1 + o)),
      s = n / (e.height * (1 + o)),
      u = Math.min(a, s),
      l = wi(u, r, i),
      c = e.x + e.width / 2,
      f = e.y + e.height / 2,
      d = t / 2 - c * l,
      h = n / 2 - f * l;
    return { x: d, y: h, zoom: l };
  },
  cr = (e, t = 0) => e.transition().duration(t);
function Py(e, t, n, r) {
  return (t[n] || []).reduce((i, o) => {
    var a, s;
    return (
      `${e.id}-${o.id}-${n}` !== r &&
        i.push({
          id: o.id || null,
          type: n,
          nodeId: e.id,
          x: (((a = e.positionAbsolute) == null ? void 0 : a.x) ?? 0) + o.x + o.width / 2,
          y: (((s = e.positionAbsolute) == null ? void 0 : s.y) ?? 0) + o.y + o.height / 2,
        }),
      i
    );
  }, []);
}
function UP(e, t, n, r, i, o) {
  const { x: a, y: s } = Qn(e),
    l = t.elementsFromPoint(a, s).find((m) => m.classList.contains("react-flow__handle"));
  if (l) {
    const m = l.getAttribute("data-nodeid");
    if (m) {
      const v = xv(void 0, l),
        w = l.getAttribute("data-handleid"),
        p = o({ nodeId: m, id: w, type: v });
      if (p) {
        const g = i.find((y) => y.nodeId === m && y.type === v && y.id === w);
        return {
          handle: {
            id: w,
            type: v,
            nodeId: m,
            x: (g == null ? void 0 : g.x) || n.x,
            y: (g == null ? void 0 : g.y) || n.y,
          },
          validHandleResult: p,
        };
      }
    }
  }
  let c = [],
    f = 1 / 0;
  if (
    (i.forEach((m) => {
      const v = Math.sqrt((m.x - n.x) ** 2 + (m.y - n.y) ** 2);
      if (v <= r) {
        const w = o(m);
        v <= f &&
          (v < f
            ? (c = [{ handle: m, validHandleResult: w }])
            : v === f && c.push({ handle: m, validHandleResult: w }),
          (f = v));
      }
    }),
    !c.length)
  )
    return { handle: null, validHandleResult: dk() };
  if (c.length === 1) return c[0];
  const d = c.some(({ validHandleResult: m }) => m.isValid),
    h = c.some(({ handle: m }) => m.type === "target");
  return (
    c.find(({ handle: m, validHandleResult: v }) =>
      h ? m.type === "target" : d ? v.isValid : !0
    ) || c[0]
  );
}
const GP = { source: null, target: null, sourceHandle: null, targetHandle: null },
  dk = () => ({ handleDomNode: null, isValid: !1, connection: GP, endHandle: null });
function hk(e, t, n, r, i, o, a) {
  const s = i === "target",
    u = a.querySelector(
      `.react-flow__handle[data-id="${e == null ? void 0 : e.nodeId}-${e == null ? void 0 : e.id}-${
        e == null ? void 0 : e.type
      }"]`
    ),
    l = { ...dk(), handleDomNode: u };
  if (u) {
    const c = xv(void 0, u),
      f = u.getAttribute("data-nodeid"),
      d = u.getAttribute("data-handleid"),
      h = u.classList.contains("connectable"),
      m = u.classList.contains("connectableend"),
      v = {
        source: s ? f : n,
        sourceHandle: s ? d : r,
        target: s ? n : f,
        targetHandle: s ? r : d,
      };
    (l.connection = v),
      h &&
        m &&
        (t === Nr.Strict ? (s && c === "source") || (!s && c === "target") : f !== n || d !== r) &&
        ((l.endHandle = { nodeId: f, handleId: d, type: c }), (l.isValid = o(v)));
  }
  return l;
}
function WP({ nodes: e, nodeId: t, handleId: n, handleType: r }) {
  return e.reduce((i, o) => {
    if (o[Se]) {
      const { handleBounds: a } = o[Se];
      let s = [],
        u = [];
      a && ((s = Py(o, a, "source", `${t}-${n}-${r}`)), (u = Py(o, a, "target", `${t}-${n}-${r}`))),
        i.push(...s, ...u);
    }
    return i;
  }, []);
}
function xv(e, t) {
  return (
    e ||
    (t != null && t.classList.contains("target")
      ? "target"
      : t != null && t.classList.contains("source")
      ? "source"
      : null)
  );
}
function Zu(e) {
  e == null ||
    e.classList.remove(
      "valid",
      "connecting",
      "react-flow__handle-valid",
      "react-flow__handle-connecting"
    );
}
function KP(e, t) {
  let n = null;
  return t ? (n = "valid") : e && !t && (n = "invalid"), n;
}
function pk({
  event: e,
  handleId: t,
  nodeId: n,
  onConnect: r,
  isTarget: i,
  getState: o,
  setState: a,
  isValidConnection: s,
  edgeUpdaterType: u,
  onReconnectEnd: l,
}) {
  const c = Jb(e.target),
    {
      connectionMode: f,
      domNode: d,
      autoPanOnConnect: h,
      connectionRadius: m,
      onConnectStart: v,
      panBy: w,
      getNodes: p,
      cancelConnection: g,
    } = o();
  let y = 0,
    _;
  const { x: S, y: E } = Qn(e),
    k = c == null ? void 0 : c.elementFromPoint(S, E),
    C = xv(u, k),
    T = d == null ? void 0 : d.getBoundingClientRect();
  if (!T || !C) return;
  let I,
    M = Qn(e, T),
    z = !1,
    F = null,
    x = !1,
    P = null;
  const N = WP({ nodes: p(), nodeId: n, handleId: t, handleType: C }),
    $ = () => {
      if (!h) return;
      const [A, L] = Zb(M, T);
      w({ x: A, y: L }), (y = requestAnimationFrame($));
    };
  a({
    connectionPosition: M,
    connectionStatus: null,
    connectionNodeId: n,
    connectionHandleId: t,
    connectionHandleType: C,
    connectionStartHandle: { nodeId: n, handleId: t, type: C },
    connectionEndHandle: null,
  }),
    v == null || v(e, { nodeId: n, handleId: t, handleType: C });
  function R(A) {
    const { transform: L } = o();
    M = Qn(A, T);
    const { handle: D, validHandleResult: H } = UP(A, c, ag(M, L, !1, [1, 1]), m, N, (B) =>
      hk(B, f, n, t, i ? "target" : "source", s, c)
    );
    if (
      ((_ = D),
      z || ($(), (z = !0)),
      (P = H.handleDomNode),
      (F = H.connection),
      (x = H.isValid),
      a({
        connectionPosition: _ && x ? uk({ x: _.x, y: _.y }, L) : M,
        connectionStatus: KP(!!_, x),
        connectionEndHandle: H.endHandle,
      }),
      !_ && !x && !P)
    )
      return Zu(I);
    F.source !== F.target &&
      P &&
      (Zu(I),
      (I = P),
      P.classList.add("connecting", "react-flow__handle-connecting"),
      P.classList.toggle("valid", x),
      P.classList.toggle("react-flow__handle-valid", x));
  }
  function b(A) {
    var L, D;
    (_ || P) && F && x && (r == null || r(F)),
      (D = (L = o()).onConnectEnd) == null || D.call(L, A),
      u && (l == null || l(A)),
      Zu(I),
      g(),
      cancelAnimationFrame(y),
      (z = !1),
      (x = !1),
      (F = null),
      (P = null),
      c.removeEventListener("mousemove", R),
      c.removeEventListener("mouseup", b),
      c.removeEventListener("touchmove", R),
      c.removeEventListener("touchend", b);
  }
  c.addEventListener("mousemove", R),
    c.addEventListener("mouseup", b),
    c.addEventListener("touchmove", R),
    c.addEventListener("touchend", b);
}
const qy = () => !0,
  YP = (e) => ({
    connectionStartHandle: e.connectionStartHandle,
    connectOnClick: e.connectOnClick,
    noPanClassName: e.noPanClassName,
  }),
  XP = (e, t, n) => (r) => {
    const { connectionStartHandle: i, connectionEndHandle: o, connectionClickStartHandle: a } = r;
    return {
      connecting:
        ((i == null ? void 0 : i.nodeId) === e &&
          (i == null ? void 0 : i.handleId) === t &&
          (i == null ? void 0 : i.type) === n) ||
        ((o == null ? void 0 : o.nodeId) === e &&
          (o == null ? void 0 : o.handleId) === t &&
          (o == null ? void 0 : o.type) === n),
      clickConnecting:
        (a == null ? void 0 : a.nodeId) === e &&
        (a == null ? void 0 : a.handleId) === t &&
        (a == null ? void 0 : a.type) === n,
    };
  },
  gk = q.forwardRef(
    (
      {
        type: e = "source",
        position: t = Y.Top,
        isValidConnection: n,
        isConnectable: r = !0,
        isConnectableStart: i = !0,
        isConnectableEnd: o = !0,
        id: a,
        onConnect: s,
        children: u,
        className: l,
        onMouseDown: c,
        onTouchStart: f,
        ...d
      },
      h
    ) => {
      var T, I;
      const m = a || null,
        v = e === "target",
        w = Ae(),
        p = FP(),
        { connectOnClick: g, noPanClassName: y } = fe(YP, ze),
        { connecting: _, clickConnecting: S } = fe(XP(p, m, e), ze);
      p || (I = (T = w.getState()).onError) == null || I.call(T, "010", Sn.error010());
      const E = (M) => {
          const { defaultEdgeOptions: z, onConnect: F, hasDefaultEdges: x } = w.getState(),
            P = { ...z, ...M };
          if (x) {
            const { edges: N, setEdges: $ } = w.getState();
            $(VP(P, N));
          }
          F == null || F(P), s == null || s(P);
        },
        k = (M) => {
          if (!p) return;
          const z = rk(M);
          i &&
            ((z && M.button === 0) || !z) &&
            pk({
              event: M,
              handleId: m,
              nodeId: p,
              onConnect: E,
              isTarget: v,
              getState: w.getState,
              setState: w.setState,
              isValidConnection: n || w.getState().isValidConnection || qy,
            }),
            z ? c == null || c(M) : f == null || f(M);
        },
        C = (M) => {
          const {
            onClickConnectStart: z,
            onClickConnectEnd: F,
            connectionClickStartHandle: x,
            connectionMode: P,
            isValidConnection: N,
          } = w.getState();
          if (!p || (!x && !i)) return;
          if (!x) {
            z == null || z(M, { nodeId: p, handleId: m, handleType: e }),
              w.setState({ connectionClickStartHandle: { nodeId: p, type: e, handleId: m } });
            return;
          }
          const $ = Jb(M.target),
            R = n || N || qy,
            { connection: b, isValid: A } = hk(
              { nodeId: p, id: m, type: e },
              P,
              x.nodeId,
              x.handleId || null,
              x.type,
              R,
              $
            );
          A && E(b), F == null || F(M), w.setState({ connectionClickStartHandle: null });
        };
      return O.createElement(
        "div",
        {
          "data-handleid": m,
          "data-nodeid": p,
          "data-handlepos": t,
          "data-id": `${p}-${m}-${e}`,
          className: Be([
            "react-flow__handle",
            `react-flow__handle-${t}`,
            "nodrag",
            y,
            l,
            {
              source: !v,
              target: v,
              connectable: r,
              connectablestart: i,
              connectableend: o,
              connecting: S,
              connectionindicator: r && ((i && !_) || (o && _)),
            },
          ]),
          onMouseDown: k,
          onTouchStart: k,
          onClick: g ? C : void 0,
          ref: h,
          ...d,
        },
        u
      );
    }
  );
gk.displayName = "Handle";
var bs = q.memo(gk);
const vk = ({
  data: e,
  isConnectable: t,
  targetPosition: n = Y.Top,
  sourcePosition: r = Y.Bottom,
}) =>
  O.createElement(
    O.Fragment,
    null,
    O.createElement(bs, { type: "target", position: n, isConnectable: t }),
    e == null ? void 0 : e.label,
    O.createElement(bs, { type: "source", position: r, isConnectable: t })
  );
vk.displayName = "DefaultNode";
var sg = q.memo(vk);
const mk = ({ data: e, isConnectable: t, sourcePosition: n = Y.Bottom }) =>
  O.createElement(
    O.Fragment,
    null,
    e == null ? void 0 : e.label,
    O.createElement(bs, { type: "source", position: n, isConnectable: t })
  );
mk.displayName = "InputNode";
var yk = q.memo(mk);
const _k = ({ data: e, isConnectable: t, targetPosition: n = Y.Top }) =>
  O.createElement(
    O.Fragment,
    null,
    O.createElement(bs, { type: "target", position: n, isConnectable: t }),
    e == null ? void 0 : e.label
  );
_k.displayName = "OutputNode";
var wk = q.memo(_k);
const Sv = () => null;
Sv.displayName = "GroupNode";
const QP = (e) => ({
    selectedNodes: e.getNodes().filter((t) => t.selected),
    selectedEdges: e.edges.filter((t) => t.selected).map((t) => ({ ...t })),
  }),
  ka = (e) => e.id;
function ZP(e, t) {
  return (
    ze(e.selectedNodes.map(ka), t.selectedNodes.map(ka)) &&
    ze(e.selectedEdges.map(ka), t.selectedEdges.map(ka))
  );
}
const xk = q.memo(({ onSelectionChange: e }) => {
  const t = Ae(),
    { selectedNodes: n, selectedEdges: r } = fe(QP, ZP);
  return (
    q.useEffect(() => {
      const i = { nodes: n, edges: r };
      e == null || e(i), t.getState().onSelectionChange.forEach((o) => o(i));
    }, [n, r, e]),
    null
  );
});
xk.displayName = "SelectionListener";
const JP = (e) => !!e.onSelectionChange;
function e3({ onSelectionChange: e }) {
  const t = fe(JP);
  return e || t ? O.createElement(xk, { onSelectionChange: e }) : null;
}
const t3 = (e) => ({
  setNodes: e.setNodes,
  setEdges: e.setEdges,
  setDefaultNodesAndEdges: e.setDefaultNodesAndEdges,
  setMinZoom: e.setMinZoom,
  setMaxZoom: e.setMaxZoom,
  setTranslateExtent: e.setTranslateExtent,
  setNodeExtent: e.setNodeExtent,
  reset: e.reset,
});
function Lr(e, t) {
  q.useEffect(() => {
    typeof e < "u" && t(e);
  }, [e]);
}
function ne(e, t, n) {
  q.useEffect(() => {
    typeof t < "u" && n({ [e]: t });
  }, [t]);
}
const n3 = ({
    nodes: e,
    edges: t,
    defaultNodes: n,
    defaultEdges: r,
    onConnect: i,
    onConnectStart: o,
    onConnectEnd: a,
    onClickConnectStart: s,
    onClickConnectEnd: u,
    nodesDraggable: l,
    nodesConnectable: c,
    nodesFocusable: f,
    edgesFocusable: d,
    edgesUpdatable: h,
    elevateNodesOnSelect: m,
    minZoom: v,
    maxZoom: w,
    nodeExtent: p,
    onNodesChange: g,
    onEdgesChange: y,
    elementsSelectable: _,
    connectionMode: S,
    snapGrid: E,
    snapToGrid: k,
    translateExtent: C,
    connectOnClick: T,
    defaultEdgeOptions: I,
    fitView: M,
    fitViewOptions: z,
    onNodesDelete: F,
    onEdgesDelete: x,
    onNodeDrag: P,
    onNodeDragStart: N,
    onNodeDragStop: $,
    onSelectionDrag: R,
    onSelectionDragStart: b,
    onSelectionDragStop: A,
    noPanClassName: L,
    nodeOrigin: D,
    rfId: H,
    autoPanOnConnect: B,
    autoPanOnNodeDrag: G,
    onError: X,
    connectionRadius: J,
    isValidConnection: se,
    nodeDragThreshold: oe,
  }) => {
    const {
        setNodes: ie,
        setEdges: Re,
        setDefaultNodesAndEdges: Ee,
        setMinZoom: $e,
        setMaxZoom: Me,
        setTranslateExtent: Q,
        setNodeExtent: Pe,
        reset: K,
      } = fe(t3, ze),
      U = Ae();
    return (
      q.useEffect(() => {
        const we = r == null ? void 0 : r.map((Rt) => ({ ...Rt, ...I }));
        return (
          Ee(n, we),
          () => {
            K();
          }
        );
      }, []),
      ne("defaultEdgeOptions", I, U.setState),
      ne("connectionMode", S, U.setState),
      ne("onConnect", i, U.setState),
      ne("onConnectStart", o, U.setState),
      ne("onConnectEnd", a, U.setState),
      ne("onClickConnectStart", s, U.setState),
      ne("onClickConnectEnd", u, U.setState),
      ne("nodesDraggable", l, U.setState),
      ne("nodesConnectable", c, U.setState),
      ne("nodesFocusable", f, U.setState),
      ne("edgesFocusable", d, U.setState),
      ne("edgesUpdatable", h, U.setState),
      ne("elementsSelectable", _, U.setState),
      ne("elevateNodesOnSelect", m, U.setState),
      ne("snapToGrid", k, U.setState),
      ne("snapGrid", E, U.setState),
      ne("onNodesChange", g, U.setState),
      ne("onEdgesChange", y, U.setState),
      ne("connectOnClick", T, U.setState),
      ne("fitViewOnInit", M, U.setState),
      ne("fitViewOnInitOptions", z, U.setState),
      ne("onNodesDelete", F, U.setState),
      ne("onEdgesDelete", x, U.setState),
      ne("onNodeDrag", P, U.setState),
      ne("onNodeDragStart", N, U.setState),
      ne("onNodeDragStop", $, U.setState),
      ne("onSelectionDrag", R, U.setState),
      ne("onSelectionDragStart", b, U.setState),
      ne("onSelectionDragStop", A, U.setState),
      ne("noPanClassName", L, U.setState),
      ne("nodeOrigin", D, U.setState),
      ne("rfId", H, U.setState),
      ne("autoPanOnConnect", B, U.setState),
      ne("autoPanOnNodeDrag", G, U.setState),
      ne("onError", X, U.setState),
      ne("connectionRadius", J, U.setState),
      ne("isValidConnection", se, U.setState),
      ne("nodeDragThreshold", oe, U.setState),
      Lr(e, ie),
      Lr(t, Re),
      Lr(v, $e),
      Lr(w, Me),
      Lr(C, Q),
      Lr(p, Pe),
      null
    );
  },
  Oy = { display: "none" },
  r3 = {
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
  Sk = "react-flow__node-desc",
  Ek = "react-flow__edge-desc",
  i3 = "react-flow__aria-live",
  o3 = (e) => e.ariaLiveMessage;
function a3({ rfId: e }) {
  const t = fe(o3);
  return O.createElement(
    "div",
    { id: `${i3}-${e}`, "aria-live": "assertive", "aria-atomic": "true", style: r3 },
    t
  );
}
function s3({ rfId: e, disableKeyboardA11y: t }) {
  return O.createElement(
    O.Fragment,
    null,
    O.createElement(
      "div",
      { id: `${Sk}-${e}`, style: Oy },
      "Press enter or space to select a node.",
      !t && "You can then use the arrow keys to move the node around.",
      " Press delete to remove it and escape to cancel.",
      " "
    ),
    O.createElement(
      "div",
      { id: `${Ek}-${e}`, style: Oy },
      "Press enter or space to select an edge. You can then press delete to remove it or escape to cancel."
    ),
    !t && O.createElement(a3, { rfId: e })
  );
}
var jo = (e = null, t = { actInsideInputWithModifier: !0 }) => {
  const [n, r] = q.useState(!1),
    i = q.useRef(!1),
    o = q.useRef(new Set([])),
    [a, s] = q.useMemo(() => {
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
    q.useEffect(() => {
      const u = typeof document < "u" ? document : null,
        l = (t == null ? void 0 : t.target) || u;
      if (e !== null) {
        const c = (h) => {
            if (
              ((i.current = h.ctrlKey || h.metaKey || h.shiftKey),
              (!i.current || (i.current && !t.actInsideInputWithModifier)) && rg(h))
            )
              return !1;
            const v = zy(h.code, s);
            o.current.add(h[v]), Ly(a, o.current, !1) && (h.preventDefault(), r(!0));
          },
          f = (h) => {
            if ((!i.current || (i.current && !t.actInsideInputWithModifier)) && rg(h)) return !1;
            const v = zy(h.code, s);
            Ly(a, o.current, !0) ? (r(!1), o.current.clear()) : o.current.delete(h[v]),
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
function Ly(e, t, n) {
  return e.filter((r) => n || r.length === t.size).some((r) => r.every((i) => t.has(i)));
}
function zy(e, t) {
  return t.includes(e) ? "code" : "key";
}
function bk(e, t, n, r) {
  var s, u;
  const i = e.parentNode || e.parentId;
  if (!i) return n;
  const o = t.get(i),
    a = wr(o, r);
  return bk(
    o,
    t,
    {
      x: (n.x ?? 0) + a.x,
      y: (n.y ?? 0) + a.y,
      z:
        (((s = o[Se]) == null ? void 0 : s.z) ?? 0) > (n.z ?? 0)
          ? ((u = o[Se]) == null ? void 0 : u.z) ?? 0
          : n.z ?? 0,
    },
    r
  );
}
function kk(e, t, n) {
  e.forEach((r) => {
    var o;
    const i = r.parentNode || r.parentId;
    if (i && !e.has(i)) throw new Error(`Parent node ${i} not found`);
    if (i || (n != null && n[r.id])) {
      const { x: a, y: s, z: u } = bk(
        r,
        e,
        { ...r.position, z: ((o = r[Se]) == null ? void 0 : o.z) ?? 0 },
        t
      );
      (r.positionAbsolute = { x: a, y: s }),
        (r[Se].z = u),
        n != null && n[r.id] && (r[Se].isParent = !0);
    }
  });
}
function Ju(e, t, n, r) {
  const i = new Map(),
    o = {},
    a = r ? 1e3 : 0;
  return (
    e.forEach((s) => {
      var h;
      const u = (St(s.zIndex) ? s.zIndex : 0) + (s.selected ? a : 0),
        l = t.get(s.id),
        c = { ...s, positionAbsolute: { x: s.position.x, y: s.position.y } },
        f = s.parentNode || s.parentId;
      f && (o[f] = !0);
      const d = (l == null ? void 0 : l.type) && (l == null ? void 0 : l.type) !== s.type;
      Object.defineProperty(c, Se, {
        enumerable: !1,
        value: {
          handleBounds: d || (h = l == null ? void 0 : l[Se]) == null ? void 0 : h.handleBounds,
          z: u,
        },
      }),
        i.set(s.id, c);
    }),
    kk(i, n, o),
    i
  );
}
function Ck(e, t = {}) {
  const {
      getNodes: n,
      width: r,
      height: i,
      minZoom: o,
      maxZoom: a,
      d3Zoom: s,
      d3Selection: u,
      fitViewOnInitDone: l,
      fitViewOnInit: c,
      nodeOrigin: f,
    } = e(),
    d = t.initial && !l && c;
  if (s && u && (d || !t.initial)) {
    const m = n().filter((w) => {
        var g;
        const p = t.includeHiddenNodes ? w.width && w.height : !w.hidden;
        return (g = t.nodes) != null && g.length ? p && t.nodes.some((y) => y.id === w.id) : p;
      }),
      v = m.every((w) => w.width && w.height);
    if (m.length > 0 && v) {
      const w = Zs(m, f),
        { x: p, y: g, zoom: y } = fk(w, r, i, t.minZoom ?? o, t.maxZoom ?? a, t.padding ?? 0.1),
        _ = vn.translate(p, g).scale(y);
      return (
        typeof t.duration == "number" && t.duration > 0
          ? s.transform(cr(u, t.duration), _)
          : s.transform(u, _),
        !0
      );
    }
  }
  return !1;
}
function u3(e, t) {
  return (
    e.forEach((n) => {
      const r = t.get(n.id);
      r && t.set(r.id, { ...r, [Se]: r[Se], selected: n.selected });
    }),
    new Map(t)
  );
}
function l3(e, t) {
  return t.map((n) => {
    const r = e.find((i) => i.id === n.id);
    return r && (n.selected = r.selected), n;
  });
}
function Ca({ changedNodes: e, changedEdges: t, get: n, set: r }) {
  const {
    nodeInternals: i,
    edges: o,
    onNodesChange: a,
    onEdgesChange: s,
    hasDefaultNodes: u,
    hasDefaultEdges: l,
  } = n();
  e != null && e.length && (u && r({ nodeInternals: u3(e, i) }), a == null || a(e)),
    t != null && t.length && (l && r({ edges: l3(t, o) }), s == null || s(t));
}
const zr = () => {},
  c3 = {
    zoomIn: zr,
    zoomOut: zr,
    zoomTo: zr,
    getZoom: () => 1,
    setViewport: zr,
    getViewport: () => ({ x: 0, y: 0, zoom: 1 }),
    fitView: () => !1,
    setCenter: zr,
    fitBounds: zr,
    project: (e) => e,
    screenToFlowPosition: (e) => e,
    flowToScreenPosition: (e) => e,
    viewportInitialized: !1,
  },
  f3 = (e) => ({ d3Zoom: e.d3Zoom, d3Selection: e.d3Selection }),
  d3 = () => {
    const e = Ae(),
      { d3Zoom: t, d3Selection: n } = fe(f3, ze);
    return q.useMemo(
      () =>
        n && t
          ? {
              zoomIn: (i) => t.scaleBy(cr(n, i == null ? void 0 : i.duration), 1.2),
              zoomOut: (i) => t.scaleBy(cr(n, i == null ? void 0 : i.duration), 1 / 1.2),
              zoomTo: (i, o) => t.scaleTo(cr(n, o == null ? void 0 : o.duration), i),
              getZoom: () => e.getState().transform[2],
              setViewport: (i, o) => {
                const [a, s, u] = e.getState().transform,
                  l = vn.translate(i.x ?? a, i.y ?? s).scale(i.zoom ?? u);
                t.transform(cr(n, o == null ? void 0 : o.duration), l);
              },
              getViewport: () => {
                const [i, o, a] = e.getState().transform;
                return { x: i, y: o, zoom: a };
              },
              fitView: (i) => Ck(e.getState, i),
              setCenter: (i, o, a) => {
                const { width: s, height: u, maxZoom: l } = e.getState(),
                  c = typeof (a == null ? void 0 : a.zoom) < "u" ? a.zoom : l,
                  f = s / 2 - i * c,
                  d = u / 2 - o * c,
                  h = vn.translate(f, d).scale(c);
                t.transform(cr(n, a == null ? void 0 : a.duration), h);
              },
              fitBounds: (i, o) => {
                const { width: a, height: s, minZoom: u, maxZoom: l } = e.getState(),
                  { x: c, y: f, zoom: d } = fk(
                    i,
                    a,
                    s,
                    u,
                    l,
                    (o == null ? void 0 : o.padding) ?? 0.1
                  ),
                  h = vn.translate(c, f).scale(d);
                t.transform(cr(n, o == null ? void 0 : o.duration), h);
              },
              project: (i) => {
                const { transform: o, snapToGrid: a, snapGrid: s } = e.getState();
                return (
                  console.warn(
                    "[DEPRECATED] `project` is deprecated. Instead use `screenToFlowPosition`. There is no need to subtract the react flow bounds anymore! https://reactflow.dev/api-reference/types/react-flow-instance#screen-to-flow-position"
                  ),
                  ag(i, o, a, s)
                );
              },
              screenToFlowPosition: (i) => {
                const { transform: o, snapToGrid: a, snapGrid: s, domNode: u } = e.getState();
                if (!u) return i;
                const { x: l, y: c } = u.getBoundingClientRect(),
                  f = { x: i.x - l, y: i.y - c };
                return ag(f, o, a, s);
              },
              flowToScreenPosition: (i) => {
                const { transform: o, domNode: a } = e.getState();
                if (!a) return i;
                const { x: s, y: u } = a.getBoundingClientRect(),
                  l = uk(i, o);
                return { x: l.x + s, y: l.y + u };
              },
              viewportInitialized: !0,
            }
          : c3,
      [t, n]
    );
  };
function Ev() {
  const e = d3(),
    t = Ae(),
    n = q.useCallback(
      () =>
        t
          .getState()
          .getNodes()
          .map((v) => ({ ...v })),
      []
    ),
    r = q.useCallback((v) => t.getState().nodeInternals.get(v), []),
    i = q.useCallback(() => {
      const { edges: v = [] } = t.getState();
      return v.map((w) => ({ ...w }));
    }, []),
    o = q.useCallback((v) => {
      const { edges: w = [] } = t.getState();
      return w.find((p) => p.id === v);
    }, []),
    a = q.useCallback((v) => {
      const { getNodes: w, setNodes: p, hasDefaultNodes: g, onNodesChange: y } = t.getState(),
        _ = w(),
        S = typeof v == "function" ? v(_) : v;
      if (g) p(S);
      else if (y) {
        const E =
          S.length === 0
            ? _.map((k) => ({ type: "remove", id: k.id }))
            : S.map((k) => ({ item: k, type: "reset" }));
        y(E);
      }
    }, []),
    s = q.useCallback((v) => {
      const { edges: w = [], setEdges: p, hasDefaultEdges: g, onEdgesChange: y } = t.getState(),
        _ = typeof v == "function" ? v(w) : v;
      if (g) p(_);
      else if (y) {
        const S =
          _.length === 0
            ? w.map((E) => ({ type: "remove", id: E.id }))
            : _.map((E) => ({ item: E, type: "reset" }));
        y(S);
      }
    }, []),
    u = q.useCallback((v) => {
      const w = Array.isArray(v) ? v : [v],
        { getNodes: p, setNodes: g, hasDefaultNodes: y, onNodesChange: _ } = t.getState();
      if (y) {
        const E = [...p(), ...w];
        g(E);
      } else if (_) {
        const S = w.map((E) => ({ item: E, type: "add" }));
        _(S);
      }
    }, []),
    l = q.useCallback((v) => {
      const w = Array.isArray(v) ? v : [v],
        { edges: p = [], setEdges: g, hasDefaultEdges: y, onEdgesChange: _ } = t.getState();
      if (y) g([...p, ...w]);
      else if (_) {
        const S = w.map((E) => ({ item: E, type: "add" }));
        _(S);
      }
    }, []),
    c = q.useCallback(() => {
      const { getNodes: v, edges: w = [], transform: p } = t.getState(),
        [g, y, _] = p;
      return {
        nodes: v().map((S) => ({ ...S })),
        edges: w.map((S) => ({ ...S })),
        viewport: { x: g, y, zoom: _ },
      };
    }, []),
    f = q.useCallback(({ nodes: v, edges: w }) => {
      const {
          nodeInternals: p,
          getNodes: g,
          edges: y,
          hasDefaultNodes: _,
          hasDefaultEdges: S,
          onNodesDelete: E,
          onEdgesDelete: k,
          onNodesChange: C,
          onEdgesChange: T,
        } = t.getState(),
        I = (v || []).map((P) => P.id),
        M = (w || []).map((P) => P.id),
        z = g().reduce((P, N) => {
          const $ = N.parentNode || N.parentId,
            R = !I.includes(N.id) && $ && P.find((A) => A.id === $);
          return (
            (typeof N.deletable == "boolean" ? N.deletable : !0) &&
              (I.includes(N.id) || R) &&
              P.push(N),
            P
          );
        }, []),
        F = y.filter((P) => (typeof P.deletable == "boolean" ? P.deletable : !0)),
        x = F.filter((P) => M.includes(P.id));
      if (z || x) {
        const P = ck(z, F),
          N = [...x, ...P],
          $ = N.reduce((R, b) => (R.includes(b.id) || R.push(b.id), R), []);
        if (
          ((S || _) &&
            (S && t.setState({ edges: y.filter((R) => !$.includes(R.id)) }),
            _ &&
              (z.forEach((R) => {
                p.delete(R.id);
              }),
              t.setState({ nodeInternals: new Map(p) }))),
          $.length > 0 && (k == null || k(N), T && T($.map((R) => ({ id: R, type: "remove" })))),
          z.length > 0 && (E == null || E(z), C))
        ) {
          const R = z.map((b) => ({ id: b.id, type: "remove" }));
          C(R);
        }
      }
    }, []),
    d = q.useCallback((v) => {
      const w = MP(v),
        p = w ? null : t.getState().nodeInternals.get(v.id);
      return !w && !p ? [null, null, w] : [w ? v : Ry(p), p, w];
    }, []),
    h = q.useCallback((v, w = !0, p) => {
      const [g, y, _] = d(v);
      return g
        ? (p || t.getState().getNodes()).filter((S) => {
            if (!_ && (S.id === y.id || !S.positionAbsolute)) return !1;
            const E = Ry(S),
              k = ng(E, g);
            return (w && k > 0) || k >= g.width * g.height;
          })
        : [];
    }, []),
    m = q.useCallback((v, w, p = !0) => {
      const [g] = d(v);
      if (!g) return !1;
      const y = ng(g, w);
      return (p && y > 0) || y >= g.width * g.height;
    }, []);
  return q.useMemo(
    () => ({
      ...e,
      getNodes: n,
      getNode: r,
      getEdges: i,
      getEdge: o,
      setNodes: a,
      setEdges: s,
      addNodes: u,
      addEdges: l,
      toObject: c,
      deleteElements: f,
      getIntersectingNodes: h,
      isNodeIntersecting: m,
    }),
    [e, n, r, i, o, a, s, u, l, c, f, h, m]
  );
}
const h3 = { actInsideInputWithModifier: !1 };
var p3 = ({ deleteKeyCode: e, multiSelectionKeyCode: t }) => {
  const n = Ae(),
    { deleteElements: r } = Ev(),
    i = jo(e, h3),
    o = jo(t);
  q.useEffect(() => {
    if (i) {
      const { edges: a, getNodes: s } = n.getState(),
        u = s().filter((c) => c.selected),
        l = a.filter((c) => c.selected);
      r({ nodes: u, edges: l }), n.setState({ nodesSelectionActive: !1 });
    }
  }, [i]),
    q.useEffect(() => {
      n.setState({ multiSelectionActive: o });
    }, [o]);
};
function g3(e) {
  const t = Ae();
  q.useEffect(() => {
    let n;
    const r = () => {
      var o, a;
      if (!e.current) return;
      const i = gv(e.current);
      (i.height === 0 || i.width === 0) &&
        ((a = (o = t.getState()).onError) == null || a.call(o, "004", Sn.error004())),
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
const bv = { position: "absolute", width: "100%", height: "100%", top: 0, left: 0 },
  v3 = (e, t) => e.x !== t.x || e.y !== t.y || e.zoom !== t.k,
  Na = (e) => ({ x: e.x, y: e.y, zoom: e.k }),
  $r = (e, t) => e.target.closest(`.${t}`),
  $y = (e, t) => t === 2 && Array.isArray(e) && e.includes(2),
  Dy = (e) => {
    const t = e.ctrlKey && Ss() ? 10 : 1;
    return -e.deltaY * (e.deltaMode === 1 ? 0.05 : e.deltaMode ? 1 : 0.002) * t;
  },
  m3 = (e) => ({
    d3Zoom: e.d3Zoom,
    d3Selection: e.d3Selection,
    d3ZoomHandler: e.d3ZoomHandler,
    userSelectionActive: e.userSelectionActive,
  }),
  y3 = ({
    onMove: e,
    onMoveStart: t,
    onMoveEnd: n,
    onPaneContextMenu: r,
    zoomOnScroll: i = !0,
    zoomOnPinch: o = !0,
    panOnScroll: a = !1,
    panOnScrollSpeed: s = 0.5,
    panOnScrollMode: u = gr.Free,
    zoomOnDoubleClick: l = !0,
    elementsSelectable: c,
    panOnDrag: f = !0,
    defaultViewport: d,
    translateExtent: h,
    minZoom: m,
    maxZoom: v,
    zoomActivationKeyCode: w,
    preventScrolling: p = !0,
    children: g,
    noWheelClassName: y,
    noPanClassName: _,
  }) => {
    const S = q.useRef(),
      E = Ae(),
      k = q.useRef(!1),
      C = q.useRef(!1),
      T = q.useRef(null),
      I = q.useRef({ x: 0, y: 0, zoom: 0 }),
      { d3Zoom: M, d3Selection: z, d3ZoomHandler: F, userSelectionActive: x } = fe(m3, ze),
      P = jo(w),
      N = q.useRef(0),
      $ = q.useRef(!1),
      R = q.useRef();
    return (
      g3(T),
      q.useEffect(() => {
        if (T.current) {
          const b = T.current.getBoundingClientRect(),
            A = Xb().scaleExtent([m, v]).translateExtent(h),
            L = wt(T.current).call(A),
            D = vn.translate(d.x, d.y).scale(wi(d.zoom, m, v)),
            H = [
              [0, 0],
              [b.width, b.height],
            ],
            B = A.constrain()(D, H, h);
          A.transform(L, B),
            A.wheelDelta(Dy),
            E.setState({
              d3Zoom: A,
              d3Selection: L,
              d3ZoomHandler: L.on("wheel.zoom"),
              transform: [B.x, B.y, B.k],
              domNode: T.current.closest(".react-flow"),
            });
        }
      }, []),
      q.useEffect(() => {
        z &&
          M &&
          (a && !P && !x
            ? z.on(
                "wheel.zoom",
                (b) => {
                  if ($r(b, y)) return !1;
                  b.preventDefault(), b.stopImmediatePropagation();
                  const A = z.property("__zoom").k || 1;
                  if (b.ctrlKey && o) {
                    const se = Pt(b),
                      oe = Dy(b),
                      ie = A * Math.pow(2, oe);
                    M.scaleTo(z, ie, se, b);
                    return;
                  }
                  const L = b.deltaMode === 1 ? 20 : 1;
                  let D = u === gr.Vertical ? 0 : b.deltaX * L,
                    H = u === gr.Horizontal ? 0 : b.deltaY * L;
                  !Ss() && b.shiftKey && u !== gr.Vertical && ((D = b.deltaY * L), (H = 0)),
                    M.translateBy(z, -(D / A) * s, -(H / A) * s, { internal: !0 });
                  const B = Na(z.property("__zoom")),
                    {
                      onViewportChangeStart: G,
                      onViewportChange: X,
                      onViewportChangeEnd: J,
                    } = E.getState();
                  clearTimeout(R.current),
                    $.current || (($.current = !0), t == null || t(b, B), G == null || G(B)),
                    $.current &&
                      (e == null || e(b, B),
                      X == null || X(B),
                      (R.current = setTimeout(() => {
                        n == null || n(b, B), J == null || J(B), ($.current = !1);
                      }, 150)));
                },
                { passive: !1 }
              )
            : typeof F < "u" &&
              z.on(
                "wheel.zoom",
                function (b, A) {
                  if ((!p && b.type === "wheel" && !b.ctrlKey) || $r(b, y)) return null;
                  b.preventDefault(), F.call(this, b, A);
                },
                { passive: !1 }
              ));
      }, [x, a, u, z, M, F, P, o, p, y, t, e, n]),
      q.useEffect(() => {
        M &&
          M.on("start", (b) => {
            var D, H;
            if (!b.sourceEvent || b.sourceEvent.internal) return null;
            N.current = (D = b.sourceEvent) == null ? void 0 : D.button;
            const { onViewportChangeStart: A } = E.getState(),
              L = Na(b.transform);
            (k.current = !0),
              (I.current = L),
              ((H = b.sourceEvent) == null ? void 0 : H.type) === "mousedown" &&
                E.setState({ paneDragging: !0 }),
              A == null || A(L),
              t == null || t(b.sourceEvent, L);
          });
      }, [M, t]),
      q.useEffect(() => {
        M &&
          (x && !k.current
            ? M.on("zoom", null)
            : x ||
              M.on("zoom", (b) => {
                var L;
                const { onViewportChange: A } = E.getState();
                if (
                  (E.setState({ transform: [b.transform.x, b.transform.y, b.transform.k] }),
                  (C.current = !!(r && $y(f, N.current ?? 0))),
                  (e || A) && !((L = b.sourceEvent) != null && L.internal))
                ) {
                  const D = Na(b.transform);
                  A == null || A(D), e == null || e(b.sourceEvent, D);
                }
              }));
      }, [x, M, e, f, r]),
      q.useEffect(() => {
        M &&
          M.on("end", (b) => {
            if (!b.sourceEvent || b.sourceEvent.internal) return null;
            const { onViewportChangeEnd: A } = E.getState();
            if (
              ((k.current = !1),
              E.setState({ paneDragging: !1 }),
              r && $y(f, N.current ?? 0) && !C.current && r(b.sourceEvent),
              (C.current = !1),
              (n || A) && v3(I.current, b.transform))
            ) {
              const L = Na(b.transform);
              (I.current = L),
                clearTimeout(S.current),
                (S.current = setTimeout(
                  () => {
                    A == null || A(L), n == null || n(b.sourceEvent, L);
                  },
                  a ? 150 : 0
                ));
            }
          });
      }, [M, a, f, n, r]),
      q.useEffect(() => {
        M &&
          M.filter((b) => {
            const A = P || i,
              L = o && b.ctrlKey;
            if (
              (f === !0 || (Array.isArray(f) && f.includes(1))) &&
              b.button === 1 &&
              b.type === "mousedown" &&
              ($r(b, "react-flow__node") || $r(b, "react-flow__edge"))
            )
              return !0;
            if (
              (!f && !A && !a && !l && !o) ||
              x ||
              (!l && b.type === "dblclick") ||
              ($r(b, y) && b.type === "wheel") ||
              ($r(b, _) && (b.type !== "wheel" || (a && b.type === "wheel" && !P))) ||
              (!o && b.ctrlKey && b.type === "wheel") ||
              (!A && !a && !L && b.type === "wheel") ||
              (!f && (b.type === "mousedown" || b.type === "touchstart")) ||
              (Array.isArray(f) && !f.includes(b.button) && b.type === "mousedown")
            )
              return !1;
            const D = (Array.isArray(f) && f.includes(b.button)) || !b.button || b.button <= 1;
            return (!b.ctrlKey || b.type === "wheel") && D;
          });
      }, [x, M, i, o, a, l, f, c, P]),
      O.createElement("div", { className: "react-flow__renderer", ref: T, style: bv }, g)
    );
  },
  _3 = (e) => ({
    userSelectionActive: e.userSelectionActive,
    userSelectionRect: e.userSelectionRect,
  });
function w3() {
  const { userSelectionActive: e, userSelectionRect: t } = fe(_3, ze);
  return e && t
    ? O.createElement("div", {
        className: "react-flow__selection react-flow__container",
        style: { width: t.width, height: t.height, transform: `translate(${t.x}px, ${t.y}px)` },
      })
    : null;
}
function Fy(e, t) {
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
        const a = Math.abs(t.position.x);
        (r.position.x = r.position.x - a), (r.style.width += a), (t.position.x = 0);
      }
      if (t.position.y < 0) {
        const a = Math.abs(t.position.y);
        (r.position.y = r.position.y - a), (r.style.height += a), (t.position.y = 0);
      }
      (r.width = r.style.width), (r.height = r.style.height);
    }
  }
}
function x3(e, t) {
  if (e.some((r) => r.type === "reset"))
    return e.filter((r) => r.type === "reset").map((r) => r.item);
  const n = e.filter((r) => r.type === "add").map((r) => r.item);
  return t.reduce((r, i) => {
    const o = e.filter((s) => s.id === i.id);
    if (o.length === 0) return r.push(i), r;
    const a = { ...i };
    for (const s of o)
      if (s)
        switch (s.type) {
          case "select": {
            a.selected = s.selected;
            break;
          }
          case "position": {
            typeof s.position < "u" && (a.position = s.position),
              typeof s.positionAbsolute < "u" && (a.positionAbsolute = s.positionAbsolute),
              typeof s.dragging < "u" && (a.dragging = s.dragging),
              a.expandParent && Fy(r, a);
            break;
          }
          case "dimensions": {
            typeof s.dimensions < "u" &&
              ((a.width = s.dimensions.width), (a.height = s.dimensions.height)),
              typeof s.updateStyle < "u" && (a.style = { ...(a.style || {}), ...s.dimensions }),
              typeof s.resizing == "boolean" && (a.resizing = s.resizing),
              a.expandParent && Fy(r, a);
            break;
          }
          case "remove":
            return r;
        }
    return r.push(a), r;
  }, n);
}
function S3(e, t) {
  return x3(e, t);
}
const Ln = (e, t) => ({ id: e, type: "select", selected: t });
function Jr(e, t) {
  return e.reduce((n, r) => {
    const i = t.includes(r.id);
    return (
      !r.selected && i
        ? ((r.selected = !0), n.push(Ln(r.id, !0)))
        : r.selected && !i && ((r.selected = !1), n.push(Ln(r.id, !1))),
      n
    );
  }, []);
}
const el = (e, t) => (n) => {
    n.target === t.current && (e == null || e(n));
  },
  E3 = (e) => ({
    userSelectionActive: e.userSelectionActive,
    elementsSelectable: e.elementsSelectable,
    dragging: e.paneDragging,
  }),
  Nk = q.memo(
    ({
      isSelecting: e,
      selectionMode: t = Do.Full,
      panOnDrag: n,
      onSelectionStart: r,
      onSelectionEnd: i,
      onPaneClick: o,
      onPaneContextMenu: a,
      onPaneScroll: s,
      onPaneMouseEnter: u,
      onPaneMouseMove: l,
      onPaneMouseLeave: c,
      children: f,
    }) => {
      const d = q.useRef(null),
        h = Ae(),
        m = q.useRef(0),
        v = q.useRef(0),
        w = q.useRef(),
        { userSelectionActive: p, elementsSelectable: g, dragging: y } = fe(E3, ze),
        _ = () => {
          h.setState({ userSelectionActive: !1, userSelectionRect: null }),
            (m.current = 0),
            (v.current = 0);
        },
        S = (F) => {
          o == null || o(F),
            h.getState().resetSelectedElements(),
            h.setState({ nodesSelectionActive: !1 });
        },
        E = (F) => {
          if (Array.isArray(n) && n != null && n.includes(2)) {
            F.preventDefault();
            return;
          }
          a == null || a(F);
        },
        k = s ? (F) => s(F) : void 0,
        C = (F) => {
          const { resetSelectedElements: x, domNode: P } = h.getState();
          if (
            ((w.current = P == null ? void 0 : P.getBoundingClientRect()),
            !g || !e || F.button !== 0 || F.target !== d.current || !w.current)
          )
            return;
          const { x: N, y: $ } = Qn(F, w.current);
          x(),
            h.setState({
              userSelectionRect: { width: 0, height: 0, startX: N, startY: $, x: N, y: $ },
            }),
            r == null || r(F);
        },
        T = (F) => {
          const {
            userSelectionRect: x,
            nodeInternals: P,
            edges: N,
            transform: $,
            onNodesChange: R,
            onEdgesChange: b,
            nodeOrigin: A,
            getNodes: L,
          } = h.getState();
          if (!e || !w.current || !x) return;
          h.setState({ userSelectionActive: !0, nodesSelectionActive: !1 });
          const D = Qn(F, w.current),
            H = x.startX ?? 0,
            B = x.startY ?? 0,
            G = {
              ...x,
              x: D.x < H ? D.x : H,
              y: D.y < B ? D.y : B,
              width: Math.abs(D.x - H),
              height: Math.abs(D.y - B),
            },
            X = L(),
            J = lk(P, G, $, t === Do.Partial, !0, A),
            se = ck(J, N).map((ie) => ie.id),
            oe = J.map((ie) => ie.id);
          if (m.current !== oe.length) {
            m.current = oe.length;
            const ie = Jr(X, oe);
            ie.length && (R == null || R(ie));
          }
          if (v.current !== se.length) {
            v.current = se.length;
            const ie = Jr(N, se);
            ie.length && (b == null || b(ie));
          }
          h.setState({ userSelectionRect: G });
        },
        I = (F) => {
          if (F.button !== 0) return;
          const { userSelectionRect: x } = h.getState();
          !p && x && F.target === d.current && (S == null || S(F)),
            h.setState({ nodesSelectionActive: m.current > 0 }),
            _(),
            i == null || i(F);
        },
        M = (F) => {
          p && (h.setState({ nodesSelectionActive: m.current > 0 }), i == null || i(F)), _();
        },
        z = g && (e || p);
      return O.createElement(
        "div",
        {
          className: Be(["react-flow__pane", { dragging: y, selection: e }]),
          onClick: z ? void 0 : el(S, d),
          onContextMenu: el(E, d),
          onWheel: el(k, d),
          onMouseEnter: z ? void 0 : u,
          onMouseDown: z ? C : void 0,
          onMouseMove: z ? T : l,
          onMouseUp: z ? I : void 0,
          onMouseLeave: z ? M : c,
          ref: d,
          style: bv,
        },
        f,
        O.createElement(w3, null)
      );
    }
  );
Nk.displayName = "Pane";
function Rk(e, t) {
  const n = e.parentNode || e.parentId;
  if (!n) return !1;
  const r = t.get(n);
  return r ? (r.selected ? !0 : Rk(r, t)) : !1;
}
function jy(e, t, n) {
  let r = e;
  do {
    if (r != null && r.matches(t)) return !0;
    if (r === n.current) return !1;
    r = r.parentElement;
  } while (r);
  return !1;
}
function b3(e, t, n, r) {
  return Array.from(e.values())
    .filter(
      (i) =>
        (i.selected || i.id === r) &&
        (!i.parentNode || i.parentId || !Rk(i, e)) &&
        (i.draggable || (t && typeof i.draggable > "u"))
    )
    .map((i) => {
      var o, a;
      return {
        id: i.id,
        position: i.position || { x: 0, y: 0 },
        positionAbsolute: i.positionAbsolute || { x: 0, y: 0 },
        distance: {
          x: n.x - (((o = i.positionAbsolute) == null ? void 0 : o.x) ?? 0),
          y: n.y - (((a = i.positionAbsolute) == null ? void 0 : a.y) ?? 0),
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
function k3(e, t) {
  return !t || t === "parent" ? t : [t[0], [t[1][0] - (e.width || 0), t[1][1] - (e.height || 0)]];
}
function Tk(e, t, n, r, i = [0, 0], o) {
  const a = k3(e, e.extent || r);
  let s = a;
  const u = e.parentNode || e.parentId;
  if (e.extent === "parent" && !e.expandParent)
    if (u && e.width && e.height) {
      const f = n.get(u),
        { x: d, y: h } = wr(f, i).positionAbsolute;
      s =
        f && St(d) && St(h) && St(f.width) && St(f.height)
          ? [
              [d + e.width * i[0], h + e.height * i[1]],
              [d + f.width - e.width + e.width * i[0], h + f.height - e.height + e.height * i[1]],
            ]
          : s;
    } else o == null || o("005", Sn.error005()), (s = a);
  else if (e.extent && u && e.extent !== "parent") {
    const f = n.get(u),
      { x: d, y: h } = wr(f, i).positionAbsolute;
    s = [
      [e.extent[0][0] + d, e.extent[0][1] + h],
      [e.extent[1][0] + d, e.extent[1][1] + h],
    ];
  }
  let l = { x: 0, y: 0 };
  if (u) {
    const f = n.get(u);
    l = wr(f, i).positionAbsolute;
  }
  const c = s && s !== "parent" ? vv(t, s) : t;
  return { position: { x: c.x - l.x, y: c.y - l.y }, positionAbsolute: c };
}
function tl({ nodeId: e, dragItems: t, nodeInternals: n }) {
  const r = t.map((i) => ({
    ...n.get(i.id),
    position: i.position,
    positionAbsolute: i.positionAbsolute,
  }));
  return [e ? r.find((i) => i.id === e) : r[0], r];
}
const By = (e, t, n, r) => {
  const i = t.querySelectorAll(e);
  if (!i || !i.length) return null;
  const o = Array.from(i),
    a = t.getBoundingClientRect(),
    s = { x: a.width * r[0], y: a.height * r[1] };
  return o.map((u) => {
    const l = u.getBoundingClientRect();
    return {
      id: u.getAttribute("data-handleid"),
      position: u.getAttribute("data-handlepos"),
      x: (l.left - a.left - s.x) / n,
      y: (l.top - a.top - s.y) / n,
      ...gv(u),
    };
  });
};
function Hi(e, t, n) {
  return n === void 0
    ? n
    : (r) => {
        const i = t().nodeInternals.get(e);
        i && n(r, { ...i });
      };
}
function ug({ id: e, store: t, unselect: n = !1, nodeRef: r }) {
  const {
      addSelectedNodes: i,
      unselectNodesAndEdges: o,
      multiSelectionActive: a,
      nodeInternals: s,
      onError: u,
    } = t.getState(),
    l = s.get(e);
  if (!l) {
    u == null || u("012", Sn.error012(e));
    return;
  }
  t.setState({ nodesSelectionActive: !1 }),
    l.selected
      ? (n || (l.selected && a)) &&
        (o({ nodes: [l], edges: [] }),
        requestAnimationFrame(() => {
          var c;
          return (c = r == null ? void 0 : r.current) == null ? void 0 : c.blur();
        }))
      : i([e]);
}
function C3() {
  const e = Ae();
  return q.useCallback(({ sourceEvent: n }) => {
    const { transform: r, snapGrid: i, snapToGrid: o } = e.getState(),
      a = n.touches ? n.touches[0].clientX : n.clientX,
      s = n.touches ? n.touches[0].clientY : n.clientY,
      u = { x: (a - r[0]) / r[2], y: (s - r[1]) / r[2] };
    return {
      xSnapped: o ? i[0] * Math.round(u.x / i[0]) : u.x,
      ySnapped: o ? i[1] * Math.round(u.y / i[1]) : u.y,
      ...u,
    };
  }, []);
}
function nl(e) {
  return (t, n, r) => (e == null ? void 0 : e(t, r));
}
function Ik({
  nodeRef: e,
  disabled: t = !1,
  noDragClassName: n,
  handleSelector: r,
  nodeId: i,
  isSelectable: o,
  selectNodesOnDrag: a,
}) {
  const s = Ae(),
    [u, l] = q.useState(!1),
    c = q.useRef([]),
    f = q.useRef({ x: null, y: null }),
    d = q.useRef(0),
    h = q.useRef(null),
    m = q.useRef({ x: 0, y: 0 }),
    v = q.useRef(null),
    w = q.useRef(!1),
    p = q.useRef(!1),
    g = q.useRef(!1),
    y = C3();
  return (
    q.useEffect(() => {
      if (e != null && e.current) {
        const _ = wt(e.current),
          S = ({ x: C, y: T }) => {
            const {
              nodeInternals: I,
              onNodeDrag: M,
              onSelectionDrag: z,
              updateNodePositions: F,
              nodeExtent: x,
              snapGrid: P,
              snapToGrid: N,
              nodeOrigin: $,
              onError: R,
            } = s.getState();
            f.current = { x: C, y: T };
            let b = !1,
              A = { x: 0, y: 0, x2: 0, y2: 0 };
            if (c.current.length > 1 && x) {
              const D = Zs(c.current, $);
              A = $o(D);
            }
            if (
              ((c.current = c.current.map((D) => {
                const H = { x: C - D.distance.x, y: T - D.distance.y };
                N && ((H.x = P[0] * Math.round(H.x / P[0])), (H.y = P[1] * Math.round(H.y / P[1])));
                const B = [
                  [x[0][0], x[0][1]],
                  [x[1][0], x[1][1]],
                ];
                c.current.length > 1 &&
                  x &&
                  !D.extent &&
                  ((B[0][0] = D.positionAbsolute.x - A.x + x[0][0]),
                  (B[1][0] = D.positionAbsolute.x + (D.width ?? 0) - A.x2 + x[1][0]),
                  (B[0][1] = D.positionAbsolute.y - A.y + x[0][1]),
                  (B[1][1] = D.positionAbsolute.y + (D.height ?? 0) - A.y2 + x[1][1]));
                const G = Tk(D, H, I, B, $, R);
                return (
                  (b = b || D.position.x !== G.position.x || D.position.y !== G.position.y),
                  (D.position = G.position),
                  (D.positionAbsolute = G.positionAbsolute),
                  D
                );
              })),
              !b)
            )
              return;
            F(c.current, !0, !0), l(!0);
            const L = i ? M : nl(z);
            if (L && v.current) {
              const [D, H] = tl({ nodeId: i, dragItems: c.current, nodeInternals: I });
              L(v.current, D, H);
            }
          },
          E = () => {
            if (!h.current) return;
            const [C, T] = Zb(m.current, h.current);
            if (C !== 0 || T !== 0) {
              const { transform: I, panBy: M } = s.getState();
              (f.current.x = (f.current.x ?? 0) - C / I[2]),
                (f.current.y = (f.current.y ?? 0) - T / I[2]),
                M({ x: C, y: T }) && S(f.current);
            }
            d.current = requestAnimationFrame(E);
          },
          k = (C) => {
            var $;
            const {
              nodeInternals: T,
              multiSelectionActive: I,
              nodesDraggable: M,
              unselectNodesAndEdges: z,
              onNodeDragStart: F,
              onSelectionDragStart: x,
            } = s.getState();
            p.current = !0;
            const P = i ? F : nl(x);
            (!a || !o) && !I && i && ((($ = T.get(i)) != null && $.selected) || z()),
              i && o && a && ug({ id: i, store: s, nodeRef: e });
            const N = y(C);
            if (((f.current = N), (c.current = b3(T, M, N, i)), P && c.current)) {
              const [R, b] = tl({ nodeId: i, dragItems: c.current, nodeInternals: T });
              P(C.sourceEvent, R, b);
            }
          };
        if (t) _.on(".drag", null);
        else {
          const C = LA()
            .on("start", (T) => {
              const { domNode: I, nodeDragThreshold: M } = s.getState();
              M === 0 && k(T), (g.current = !1);
              const z = y(T);
              (f.current = z),
                (h.current = (I == null ? void 0 : I.getBoundingClientRect()) || null),
                (m.current = Qn(T.sourceEvent, h.current));
            })
            .on("drag", (T) => {
              var F, x;
              const I = y(T),
                { autoPanOnNodeDrag: M, nodeDragThreshold: z } = s.getState();
              if (
                (T.sourceEvent.type === "touchmove" &&
                  T.sourceEvent.touches.length > 1 &&
                  (g.current = !0),
                !g.current)
              ) {
                if ((!w.current && p.current && M && ((w.current = !0), E()), !p.current)) {
                  const P =
                      I.xSnapped -
                      (((F = f == null ? void 0 : f.current) == null ? void 0 : F.x) ?? 0),
                    N =
                      I.ySnapped -
                      (((x = f == null ? void 0 : f.current) == null ? void 0 : x.y) ?? 0);
                  Math.sqrt(P * P + N * N) > z && k(T);
                }
                (f.current.x !== I.xSnapped || f.current.y !== I.ySnapped) &&
                  c.current &&
                  p.current &&
                  ((v.current = T.sourceEvent), (m.current = Qn(T.sourceEvent, h.current)), S(I));
              }
            })
            .on("end", (T) => {
              if (
                !(!p.current || g.current) &&
                (l(!1),
                (w.current = !1),
                (p.current = !1),
                cancelAnimationFrame(d.current),
                c.current)
              ) {
                const {
                    updateNodePositions: I,
                    nodeInternals: M,
                    onNodeDragStop: z,
                    onSelectionDragStop: F,
                  } = s.getState(),
                  x = i ? z : nl(F);
                if ((I(c.current, !1, !1), x)) {
                  const [P, N] = tl({ nodeId: i, dragItems: c.current, nodeInternals: M });
                  x(T.sourceEvent, P, N);
                }
              }
            })
            .filter((T) => {
              const I = T.target;
              return !T.button && (!n || !jy(I, `.${n}`, e)) && (!r || jy(I, r, e));
            });
          return (
            _.call(C),
            () => {
              _.on(".drag", null);
            }
          );
        }
      }
    }, [e, t, n, r, o, s, i, a, y]),
    u
  );
}
function Ak() {
  const e = Ae();
  return q.useCallback((n) => {
    const {
        nodeInternals: r,
        nodeExtent: i,
        updateNodePositions: o,
        getNodes: a,
        snapToGrid: s,
        snapGrid: u,
        onError: l,
        nodesDraggable: c,
      } = e.getState(),
      f = a().filter((g) => g.selected && (g.draggable || (c && typeof g.draggable > "u"))),
      d = s ? u[0] : 5,
      h = s ? u[1] : 5,
      m = n.isShiftPressed ? 4 : 1,
      v = n.x * d * m,
      w = n.y * h * m,
      p = f.map((g) => {
        if (g.positionAbsolute) {
          const y = { x: g.positionAbsolute.x + v, y: g.positionAbsolute.y + w };
          s && ((y.x = u[0] * Math.round(y.x / u[0])), (y.y = u[1] * Math.round(y.y / u[1])));
          const { positionAbsolute: _, position: S } = Tk(g, y, r, i, void 0, l);
          (g.position = S), (g.positionAbsolute = _);
        }
        return g;
      });
    o(p, !0, !1);
  }, []);
}
const ui = {
  ArrowUp: { x: 0, y: -1 },
  ArrowDown: { x: 0, y: 1 },
  ArrowLeft: { x: -1, y: 0 },
  ArrowRight: { x: 1, y: 0 },
};
var Vi = (e) => {
  const t = ({
    id: n,
    type: r,
    data: i,
    xPos: o,
    yPos: a,
    xPosOrigin: s,
    yPosOrigin: u,
    selected: l,
    onClick: c,
    onMouseEnter: f,
    onMouseMove: d,
    onMouseLeave: h,
    onContextMenu: m,
    onDoubleClick: v,
    style: w,
    className: p,
    isDraggable: g,
    isSelectable: y,
    isConnectable: _,
    isFocusable: S,
    selectNodesOnDrag: E,
    sourcePosition: k,
    targetPosition: C,
    hidden: T,
    resizeObserver: I,
    dragHandle: M,
    zIndex: z,
    isParent: F,
    noDragClassName: x,
    noPanClassName: P,
    initialized: N,
    disableKeyboardA11y: $,
    ariaLabel: R,
    rfId: b,
    hasHandleBounds: A,
  }) => {
    const L = Ae(),
      D = q.useRef(null),
      H = q.useRef(null),
      B = q.useRef(k),
      G = q.useRef(C),
      X = q.useRef(r),
      J = y || g || c || f || d || h,
      se = Ak(),
      oe = Hi(n, L.getState, f),
      ie = Hi(n, L.getState, d),
      Re = Hi(n, L.getState, h),
      Ee = Hi(n, L.getState, m),
      $e = Hi(n, L.getState, v),
      Me = (K) => {
        const { nodeDragThreshold: U } = L.getState();
        if ((y && (!E || !g || U > 0) && ug({ id: n, store: L, nodeRef: D }), c)) {
          const we = L.getState().nodeInternals.get(n);
          we && c(K, { ...we });
        }
      },
      Q = (K) => {
        if (!rg(K) && !$)
          if (nk.includes(K.key) && y) {
            const U = K.key === "Escape";
            ug({ id: n, store: L, unselect: U, nodeRef: D });
          } else
            g &&
              l &&
              Object.prototype.hasOwnProperty.call(ui, K.key) &&
              (L.setState({
                ariaLiveMessage: `Moved selected node ${K.key
                  .replace("Arrow", "")
                  .toLowerCase()}. New position, x: ${~~o}, y: ${~~a}`,
              }),
              se({ x: ui[K.key].x, y: ui[K.key].y, isShiftPressed: K.shiftKey }));
      };
    q.useEffect(
      () => () => {
        H.current && (I == null || I.unobserve(H.current), (H.current = null));
      },
      []
    ),
      q.useEffect(() => {
        if (D.current && !T) {
          const K = D.current;
          (!N || !A || H.current !== K) &&
            (H.current && (I == null || I.unobserve(H.current)),
            I == null || I.observe(K),
            (H.current = K));
        }
      }, [T, N, A]),
      q.useEffect(() => {
        const K = X.current !== r,
          U = B.current !== k,
          we = G.current !== C;
        D.current &&
          (K || U || we) &&
          (K && (X.current = r),
          U && (B.current = k),
          we && (G.current = C),
          L.getState().updateNodeDimensions([{ id: n, nodeElement: D.current, forceUpdate: !0 }]));
      }, [n, r, k, C]);
    const Pe = Ik({
      nodeRef: D,
      disabled: T || !g,
      noDragClassName: x,
      handleSelector: M,
      nodeId: n,
      isSelectable: y,
      selectNodesOnDrag: E,
    });
    return T
      ? null
      : O.createElement(
          "div",
          {
            className: Be([
              "react-flow__node",
              `react-flow__node-${r}`,
              { [P]: g },
              p,
              { selected: l, selectable: y, parent: F, dragging: Pe },
            ]),
            ref: D,
            style: {
              zIndex: z,
              transform: `translate(${s}px,${u}px)`,
              pointerEvents: J ? "all" : "none",
              visibility: N ? "visible" : "hidden",
              ...w,
            },
            "data-id": n,
            "data-testid": `rf__node-${n}`,
            onMouseEnter: oe,
            onMouseMove: ie,
            onMouseLeave: Re,
            onContextMenu: Ee,
            onClick: Me,
            onDoubleClick: $e,
            onKeyDown: S ? Q : void 0,
            tabIndex: S ? 0 : void 0,
            role: S ? "button" : void 0,
            "aria-describedby": $ ? void 0 : `${Sk}-${b}`,
            "aria-label": R,
          },
          O.createElement(
            DP,
            { value: n },
            O.createElement(e, {
              id: n,
              data: i,
              type: r,
              xPos: o,
              yPos: a,
              selected: l,
              isConnectable: _,
              sourcePosition: k,
              targetPosition: C,
              dragging: Pe,
              dragHandle: M,
              zIndex: z,
            })
          )
        );
  };
  return (t.displayName = "NodeWrapper"), q.memo(t);
};
const N3 = (e) => {
  const t = e.getNodes().filter((n) => n.selected);
  return {
    ...Zs(t, e.nodeOrigin),
    transformString: `translate(${e.transform[0]}px,${e.transform[1]}px) scale(${e.transform[2]})`,
    userSelectionActive: e.userSelectionActive,
  };
};
function R3({ onSelectionContextMenu: e, noPanClassName: t, disableKeyboardA11y: n }) {
  const r = Ae(),
    { width: i, height: o, x: a, y: s, transformString: u, userSelectionActive: l } = fe(N3, ze),
    c = Ak(),
    f = q.useRef(null);
  if (
    (q.useEffect(() => {
      var m;
      n || (m = f.current) == null || m.focus({ preventScroll: !0 });
    }, [n]),
    Ik({ nodeRef: f }),
    l || !i || !o)
  )
    return null;
  const d = e
      ? (m) => {
          const v = r
            .getState()
            .getNodes()
            .filter((w) => w.selected);
          e(m, v);
        }
      : void 0,
    h = (m) => {
      Object.prototype.hasOwnProperty.call(ui, m.key) &&
        c({ x: ui[m.key].x, y: ui[m.key].y, isShiftPressed: m.shiftKey });
    };
  return O.createElement(
    "div",
    {
      className: Be(["react-flow__nodesselection", "react-flow__container", t]),
      style: { transform: u },
    },
    O.createElement("div", {
      ref: f,
      className: "react-flow__nodesselection-rect",
      onContextMenu: d,
      tabIndex: n ? void 0 : -1,
      onKeyDown: n ? void 0 : h,
      style: { width: i, height: o, top: s, left: a },
    })
  );
}
var T3 = q.memo(R3);
const I3 = (e) => e.nodesSelectionActive,
  Mk = ({
    children: e,
    onPaneClick: t,
    onPaneMouseEnter: n,
    onPaneMouseMove: r,
    onPaneMouseLeave: i,
    onPaneContextMenu: o,
    onPaneScroll: a,
    deleteKeyCode: s,
    onMove: u,
    onMoveStart: l,
    onMoveEnd: c,
    selectionKeyCode: f,
    selectionOnDrag: d,
    selectionMode: h,
    onSelectionStart: m,
    onSelectionEnd: v,
    multiSelectionKeyCode: w,
    panActivationKeyCode: p,
    zoomActivationKeyCode: g,
    elementsSelectable: y,
    zoomOnScroll: _,
    zoomOnPinch: S,
    panOnScroll: E,
    panOnScrollSpeed: k,
    panOnScrollMode: C,
    zoomOnDoubleClick: T,
    panOnDrag: I,
    defaultViewport: M,
    translateExtent: z,
    minZoom: F,
    maxZoom: x,
    preventScrolling: P,
    onSelectionContextMenu: N,
    noWheelClassName: $,
    noPanClassName: R,
    disableKeyboardA11y: b,
  }) => {
    const A = fe(I3),
      L = jo(f),
      D = jo(p),
      H = D || I,
      B = D || E,
      G = L || (d && H !== !0);
    return (
      p3({ deleteKeyCode: s, multiSelectionKeyCode: w }),
      O.createElement(
        y3,
        {
          onMove: u,
          onMoveStart: l,
          onMoveEnd: c,
          onPaneContextMenu: o,
          elementsSelectable: y,
          zoomOnScroll: _,
          zoomOnPinch: S,
          panOnScroll: B,
          panOnScrollSpeed: k,
          panOnScrollMode: C,
          zoomOnDoubleClick: T,
          panOnDrag: !L && H,
          defaultViewport: M,
          translateExtent: z,
          minZoom: F,
          maxZoom: x,
          zoomActivationKeyCode: g,
          preventScrolling: P,
          noWheelClassName: $,
          noPanClassName: R,
        },
        O.createElement(
          Nk,
          {
            onSelectionStart: m,
            onSelectionEnd: v,
            onPaneClick: t,
            onPaneMouseEnter: n,
            onPaneMouseMove: r,
            onPaneMouseLeave: i,
            onPaneContextMenu: o,
            onPaneScroll: a,
            panOnDrag: H,
            isSelecting: !!G,
            selectionMode: h,
          },
          e,
          A &&
            O.createElement(T3, {
              onSelectionContextMenu: N,
              noPanClassName: R,
              disableKeyboardA11y: b,
            })
        )
      )
    );
  };
Mk.displayName = "FlowRenderer";
var A3 = q.memo(Mk);
function M3(e) {
  return fe(
    q.useCallback(
      (n) =>
        e
          ? lk(n.nodeInternals, { x: 0, y: 0, width: n.width, height: n.height }, n.transform, !0)
          : n.getNodes(),
      [e]
    )
  );
}
function P3(e) {
  const t = {
      input: Vi(e.input || yk),
      default: Vi(e.default || sg),
      output: Vi(e.output || wk),
      group: Vi(e.group || Sv),
    },
    n = {},
    r = Object.keys(e)
      .filter((i) => !["input", "default", "output", "group"].includes(i))
      .reduce((i, o) => ((i[o] = Vi(e[o] || sg)), i), n);
  return { ...t, ...r };
}
const q3 = ({ x: e, y: t, width: n, height: r, origin: i }) =>
    !n || !r
      ? { x: e, y: t }
      : i[0] < 0 || i[1] < 0 || i[0] > 1 || i[1] > 1
      ? { x: e, y: t }
      : { x: e - n * i[0], y: t - r * i[1] },
  O3 = (e) => ({
    nodesDraggable: e.nodesDraggable,
    nodesConnectable: e.nodesConnectable,
    nodesFocusable: e.nodesFocusable,
    elementsSelectable: e.elementsSelectable,
    updateNodeDimensions: e.updateNodeDimensions,
    onError: e.onError,
  }),
  Pk = (e) => {
    const {
        nodesDraggable: t,
        nodesConnectable: n,
        nodesFocusable: r,
        elementsSelectable: i,
        updateNodeDimensions: o,
        onError: a,
      } = fe(O3, ze),
      s = M3(e.onlyRenderVisibleElements),
      u = q.useRef(),
      l = q.useMemo(() => {
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
      q.useEffect(
        () => () => {
          var c;
          (c = u == null ? void 0 : u.current) == null || c.disconnect();
        },
        []
      ),
      O.createElement(
        "div",
        { className: "react-flow__nodes", style: bv },
        s.map((c) => {
          var S, E, k;
          let f = c.type || "default";
          e.nodeTypes[f] || (a == null || a("003", Sn.error003(f)), (f = "default"));
          const d = e.nodeTypes[f] || e.nodeTypes.default,
            h = !!(c.draggable || (t && typeof c.draggable > "u")),
            m = !!(c.selectable || (i && typeof c.selectable > "u")),
            v = !!(c.connectable || (n && typeof c.connectable > "u")),
            w = !!(c.focusable || (r && typeof c.focusable > "u")),
            p = e.nodeExtent ? vv(c.positionAbsolute, e.nodeExtent) : c.positionAbsolute,
            g = (p == null ? void 0 : p.x) ?? 0,
            y = (p == null ? void 0 : p.y) ?? 0,
            _ = q3({ x: g, y, width: c.width ?? 0, height: c.height ?? 0, origin: e.nodeOrigin });
          return O.createElement(d, {
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
            yPos: y,
            xPosOrigin: _.x,
            yPosOrigin: _.y,
            selectNodesOnDrag: e.selectNodesOnDrag,
            onClick: e.onNodeClick,
            onMouseEnter: e.onNodeMouseEnter,
            onMouseMove: e.onNodeMouseMove,
            onMouseLeave: e.onNodeMouseLeave,
            onContextMenu: e.onNodeContextMenu,
            onDoubleClick: e.onNodeDoubleClick,
            selected: !!c.selected,
            isDraggable: h,
            isSelectable: m,
            isConnectable: v,
            isFocusable: w,
            resizeObserver: l,
            dragHandle: c.dragHandle,
            zIndex: ((S = c[Se]) == null ? void 0 : S.z) ?? 0,
            isParent: !!((E = c[Se]) != null && E.isParent),
            noDragClassName: e.noDragClassName,
            noPanClassName: e.noPanClassName,
            initialized: !!c.width && !!c.height,
            rfId: e.rfId,
            disableKeyboardA11y: e.disableKeyboardA11y,
            ariaLabel: c.ariaLabel,
            hasHandleBounds: !!((k = c[Se]) != null && k.handleBounds),
          });
        })
      )
    );
  };
Pk.displayName = "NodeRenderer";
var L3 = q.memo(Pk);
const z3 = (e, t, n) => (n === Y.Left ? e - t : n === Y.Right ? e + t : e),
  $3 = (e, t, n) => (n === Y.Top ? e - t : n === Y.Bottom ? e + t : e),
  Hy = "react-flow__edgeupdater",
  Vy = ({
    position: e,
    centerX: t,
    centerY: n,
    radius: r = 10,
    onMouseDown: i,
    onMouseEnter: o,
    onMouseOut: a,
    type: s,
  }) =>
    O.createElement("circle", {
      onMouseDown: i,
      onMouseEnter: o,
      onMouseOut: a,
      className: Be([Hy, `${Hy}-${s}`]),
      cx: z3(t, r, e),
      cy: $3(n, r, e),
      r,
      stroke: "transparent",
      fill: "transparent",
    }),
  D3 = () => !0;
var Dr = (e) => {
  const t = ({
    id: n,
    className: r,
    type: i,
    data: o,
    onClick: a,
    onEdgeDoubleClick: s,
    selected: u,
    animated: l,
    label: c,
    labelStyle: f,
    labelShowBg: d,
    labelBgStyle: h,
    labelBgPadding: m,
    labelBgBorderRadius: v,
    style: w,
    source: p,
    target: g,
    sourceX: y,
    sourceY: _,
    targetX: S,
    targetY: E,
    sourcePosition: k,
    targetPosition: C,
    elementsSelectable: T,
    hidden: I,
    sourceHandleId: M,
    targetHandleId: z,
    onContextMenu: F,
    onMouseEnter: x,
    onMouseMove: P,
    onMouseLeave: N,
    reconnectRadius: $,
    onReconnect: R,
    onReconnectStart: b,
    onReconnectEnd: A,
    markerEnd: L,
    markerStart: D,
    rfId: H,
    ariaLabel: B,
    isFocusable: G,
    isReconnectable: X,
    pathOptions: J,
    interactionWidth: se,
    disableKeyboardA11y: oe,
  }) => {
    const ie = q.useRef(null),
      [Re, Ee] = q.useState(!1),
      [$e, Me] = q.useState(!1),
      Q = Ae(),
      Pe = q.useMemo(() => `url('#${og(D, H)}')`, [D, H]),
      K = q.useMemo(() => `url('#${og(L, H)}')`, [L, H]);
    if (I) return null;
    const U = (qe) => {
        var Ut;
        const {
            edges: tt,
            addSelectedEdges: He,
            unselectNodesAndEdges: Ye,
            multiSelectionActive: ar,
          } = Q.getState(),
          rn = tt.find((Ii) => Ii.id === n);
        rn &&
          (T &&
            (Q.setState({ nodesSelectionActive: !1 }),
            rn.selected && ar
              ? (Ye({ nodes: [], edges: [rn] }), (Ut = ie.current) == null || Ut.blur())
              : He([n])),
          a && a(qe, rn));
      },
      we = Bi(n, Q.getState, s),
      Rt = Bi(n, Q.getState, F),
      Ht = Bi(n, Q.getState, x),
      Ke = Bi(n, Q.getState, P),
      be = Bi(n, Q.getState, N),
      et = (qe, tt) => {
        if (qe.button !== 0) return;
        const { edges: He, isValidConnection: Ye } = Q.getState(),
          ar = tt ? g : p,
          rn = (tt ? z : M) || null,
          Ut = tt ? "target" : "source",
          Ii = Ye || D3,
          yu = tt,
          Ai = He.find((sr) => sr.id === n);
        Me(!0), b == null || b(qe, Ai, Ut);
        const _u = (sr) => {
          Me(!1), A == null || A(sr, Ai, Ut);
        };
        pk({
          event: qe,
          handleId: rn,
          nodeId: ar,
          onConnect: (sr) => (R == null ? void 0 : R(Ai, sr)),
          isTarget: yu,
          getState: Q.getState,
          setState: Q.setState,
          isValidConnection: Ii,
          edgeUpdaterType: Ut,
          onReconnectEnd: _u,
        });
      },
      Tt = (qe) => et(qe, !0),
      tn = (qe) => et(qe, !1),
      Vt = () => Ee(!0),
      lt = () => Ee(!1),
      nn = !T && !a,
      Nn = (qe) => {
        var tt;
        if (!oe && nk.includes(qe.key) && T) {
          const { unselectNodesAndEdges: He, addSelectedEdges: Ye, edges: ar } = Q.getState();
          qe.key === "Escape"
            ? ((tt = ie.current) == null || tt.blur(),
              He({ edges: [ar.find((Ut) => Ut.id === n)] }))
            : Ye([n]);
        }
      };
    return O.createElement(
      "g",
      {
        className: Be([
          "react-flow__edge",
          `react-flow__edge-${i}`,
          r,
          { selected: u, animated: l, inactive: nn, updating: Re },
        ]),
        onClick: U,
        onDoubleClick: we,
        onContextMenu: Rt,
        onMouseEnter: Ht,
        onMouseMove: Ke,
        onMouseLeave: be,
        onKeyDown: G ? Nn : void 0,
        tabIndex: G ? 0 : void 0,
        role: G ? "button" : "img",
        "data-testid": `rf__edge-${n}`,
        "aria-label": B === null ? void 0 : B || `Edge from ${p} to ${g}`,
        "aria-describedby": G ? `${Ek}-${H}` : void 0,
        ref: ie,
      },
      !$e &&
        O.createElement(e, {
          id: n,
          source: p,
          target: g,
          selected: u,
          animated: l,
          label: c,
          labelStyle: f,
          labelShowBg: d,
          labelBgStyle: h,
          labelBgPadding: m,
          labelBgBorderRadius: v,
          data: o,
          style: w,
          sourceX: y,
          sourceY: _,
          targetX: S,
          targetY: E,
          sourcePosition: k,
          targetPosition: C,
          sourceHandleId: M,
          targetHandleId: z,
          markerStart: Pe,
          markerEnd: K,
          pathOptions: J,
          interactionWidth: se,
        }),
      X &&
        O.createElement(
          O.Fragment,
          null,
          (X === "source" || X === !0) &&
            O.createElement(Vy, {
              position: k,
              centerX: y,
              centerY: _,
              radius: $,
              onMouseDown: Tt,
              onMouseEnter: Vt,
              onMouseOut: lt,
              type: "source",
            }),
          (X === "target" || X === !0) &&
            O.createElement(Vy, {
              position: C,
              centerX: S,
              centerY: E,
              radius: $,
              onMouseDown: tn,
              onMouseEnter: Vt,
              onMouseOut: lt,
              type: "target",
            })
        )
    );
  };
  return (t.displayName = "EdgeWrapper"), q.memo(t);
};
function F3(e) {
  const t = {
      default: Dr(e.default || Es),
      straight: Dr(e.bezier || _v),
      step: Dr(e.step || yv),
      smoothstep: Dr(e.step || Qs),
      simplebezier: Dr(e.simplebezier || mv),
    },
    n = {},
    r = Object.keys(e)
      .filter((i) => !["default", "bezier"].includes(i))
      .reduce((i, o) => ((i[o] = Dr(e[o] || Es)), i), n);
  return { ...t, ...r };
}
function Uy(e, t, n = null) {
  const r = ((n == null ? void 0 : n.x) || 0) + t.x,
    i = ((n == null ? void 0 : n.y) || 0) + t.y,
    o = (n == null ? void 0 : n.width) || t.width,
    a = (n == null ? void 0 : n.height) || t.height;
  switch (e) {
    case Y.Top:
      return { x: r + o / 2, y: i };
    case Y.Right:
      return { x: r + o, y: i + a / 2 };
    case Y.Bottom:
      return { x: r + o / 2, y: i + a };
    case Y.Left:
      return { x: r, y: i + a / 2 };
  }
}
function Gy(e, t) {
  return e ? (e.length === 1 || !t ? e[0] : (t && e.find((n) => n.id === t)) || null) : null;
}
const j3 = (e, t, n, r, i, o) => {
  const a = Uy(n, e, t),
    s = Uy(o, r, i);
  return { sourceX: a.x, sourceY: a.y, targetX: s.x, targetY: s.y };
};
function B3({
  sourcePos: e,
  targetPos: t,
  sourceWidth: n,
  sourceHeight: r,
  targetWidth: i,
  targetHeight: o,
  width: a,
  height: s,
  transform: u,
}) {
  const l = {
    x: Math.min(e.x, t.x),
    y: Math.min(e.y, t.y),
    x2: Math.max(e.x + n, t.x + i),
    y2: Math.max(e.y + r, t.y + o),
  };
  l.x === l.x2 && (l.x2 += 1), l.y === l.y2 && (l.y2 += 1);
  const c = $o({ x: (0 - u[0]) / u[2], y: (0 - u[1]) / u[2], width: a / u[2], height: s / u[2] }),
    f = Math.max(0, Math.min(c.x2, l.x2) - Math.max(c.x, l.x)),
    d = Math.max(0, Math.min(c.y2, l.y2) - Math.max(c.y, l.y));
  return Math.ceil(f * d) > 0;
}
function Wy(e) {
  var r, i, o, a, s;
  const t = ((r = e == null ? void 0 : e[Se]) == null ? void 0 : r.handleBounds) || null,
    n =
      t &&
      (e == null ? void 0 : e.width) &&
      (e == null ? void 0 : e.height) &&
      typeof ((i = e == null ? void 0 : e.positionAbsolute) == null ? void 0 : i.x) < "u" &&
      typeof ((o = e == null ? void 0 : e.positionAbsolute) == null ? void 0 : o.y) < "u";
  return [
    {
      x: ((a = e == null ? void 0 : e.positionAbsolute) == null ? void 0 : a.x) || 0,
      y: ((s = e == null ? void 0 : e.positionAbsolute) == null ? void 0 : s.y) || 0,
      width: (e == null ? void 0 : e.width) || 0,
      height: (e == null ? void 0 : e.height) || 0,
    },
    t,
    !!n,
  ];
}
const H3 = [{ level: 0, isMaxLevel: !0, edges: [] }];
function V3(e, t, n = !1) {
  let r = -1;
  const i = e.reduce((a, s) => {
      var c, f;
      const u = St(s.zIndex);
      let l = u ? s.zIndex : 0;
      if (n) {
        const d = t.get(s.target),
          h = t.get(s.source),
          m = s.selected || (d == null ? void 0 : d.selected) || (h == null ? void 0 : h.selected),
          v = Math.max(
            ((c = h == null ? void 0 : h[Se]) == null ? void 0 : c.z) || 0,
            ((f = d == null ? void 0 : d[Se]) == null ? void 0 : f.z) || 0,
            1e3
          );
        l = (u ? s.zIndex : 0) + (m ? v : 0);
      }
      return a[l] ? a[l].push(s) : (a[l] = [s]), (r = l > r ? l : r), a;
    }, {}),
    o = Object.entries(i).map(([a, s]) => {
      const u = +a;
      return { edges: s, level: u, isMaxLevel: u === r };
    });
  return o.length === 0 ? H3 : o;
}
function U3(e, t, n) {
  const r = fe(
    q.useCallback(
      (i) =>
        e
          ? i.edges.filter((o) => {
              const a = t.get(o.source),
                s = t.get(o.target);
              return (
                (a == null ? void 0 : a.width) &&
                (a == null ? void 0 : a.height) &&
                (s == null ? void 0 : s.width) &&
                (s == null ? void 0 : s.height) &&
                B3({
                  sourcePos: a.positionAbsolute || { x: 0, y: 0 },
                  targetPos: s.positionAbsolute || { x: 0, y: 0 },
                  sourceWidth: a.width,
                  sourceHeight: a.height,
                  targetWidth: s.width,
                  targetHeight: s.height,
                  width: i.width,
                  height: i.height,
                  transform: i.transform,
                })
              );
            })
          : i.edges,
      [e, t]
    )
  );
  return V3(r, t, n);
}
const G3 = ({ color: e = "none", strokeWidth: t = 1 }) =>
    O.createElement("polyline", {
      style: { stroke: e, strokeWidth: t },
      strokeLinecap: "round",
      strokeLinejoin: "round",
      fill: "none",
      points: "-5,-4 0,0 -5,4",
    }),
  W3 = ({ color: e = "none", strokeWidth: t = 1 }) =>
    O.createElement("polyline", {
      style: { stroke: e, fill: e, strokeWidth: t },
      strokeLinecap: "round",
      strokeLinejoin: "round",
      points: "-5,-4 0,0 -5,4 -5,-4",
    }),
  Ky = { [Fo.Arrow]: G3, [Fo.ArrowClosed]: W3 };
function K3(e) {
  const t = Ae();
  return q.useMemo(() => {
    var i, o;
    return Object.prototype.hasOwnProperty.call(Ky, e)
      ? Ky[e]
      : ((o = (i = t.getState()).onError) == null || o.call(i, "009", Sn.error009(e)), null);
  }, [e]);
}
const Y3 = ({
    id: e,
    type: t,
    color: n,
    width: r = 12.5,
    height: i = 12.5,
    markerUnits: o = "strokeWidth",
    strokeWidth: a,
    orient: s = "auto-start-reverse",
  }) => {
    const u = K3(t);
    return u
      ? O.createElement(
          "marker",
          {
            className: "react-flow__arrowhead",
            id: e,
            markerWidth: `${r}`,
            markerHeight: `${i}`,
            viewBox: "-10 -10 20 20",
            markerUnits: o,
            orient: s,
            refX: "0",
            refY: "0",
          },
          O.createElement(u, { color: n, strokeWidth: a })
        )
      : null;
  },
  X3 = ({ defaultColor: e, rfId: t }) => (n) => {
    const r = [];
    return n.edges
      .reduce(
        (i, o) => (
          [o.markerStart, o.markerEnd].forEach((a) => {
            if (a && typeof a == "object") {
              const s = og(a, t);
              r.includes(s) || (i.push({ id: s, color: a.color || e, ...a }), r.push(s));
            }
          }),
          i
        ),
        []
      )
      .sort((i, o) => i.id.localeCompare(o.id));
  },
  qk = ({ defaultColor: e, rfId: t }) => {
    const n = fe(
      q.useCallback(X3({ defaultColor: e, rfId: t }), [e, t]),
      (r, i) => !(r.length !== i.length || r.some((o, a) => o.id !== i[a].id))
    );
    return O.createElement(
      "defs",
      null,
      n.map((r) =>
        O.createElement(Y3, {
          id: r.id,
          key: r.id,
          type: r.type,
          color: r.color,
          width: r.width,
          height: r.height,
          markerUnits: r.markerUnits,
          strokeWidth: r.strokeWidth,
          orient: r.orient,
        })
      )
    );
  };
qk.displayName = "MarkerDefinitions";
var Q3 = q.memo(qk);
const Z3 = (e) => ({
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
  Ok = ({
    defaultMarkerColor: e,
    onlyRenderVisibleElements: t,
    elevateEdgesOnSelect: n,
    rfId: r,
    edgeTypes: i,
    noPanClassName: o,
    onEdgeContextMenu: a,
    onEdgeMouseEnter: s,
    onEdgeMouseMove: u,
    onEdgeMouseLeave: l,
    onEdgeClick: c,
    onEdgeDoubleClick: f,
    onReconnect: d,
    onReconnectStart: h,
    onReconnectEnd: m,
    reconnectRadius: v,
    children: w,
    disableKeyboardA11y: p,
  }) => {
    const {
        edgesFocusable: g,
        edgesUpdatable: y,
        elementsSelectable: _,
        width: S,
        height: E,
        connectionMode: k,
        nodeInternals: C,
        onError: T,
      } = fe(Z3, ze),
      I = U3(t, C, n);
    return S
      ? O.createElement(
          O.Fragment,
          null,
          I.map(({ level: M, edges: z, isMaxLevel: F }) =>
            O.createElement(
              "svg",
              {
                key: M,
                style: { zIndex: M },
                width: S,
                height: E,
                className: "react-flow__edges react-flow__container",
              },
              F && O.createElement(Q3, { defaultColor: e, rfId: r }),
              O.createElement(
                "g",
                null,
                z.map((x) => {
                  const [P, N, $] = Wy(C.get(x.source)),
                    [R, b, A] = Wy(C.get(x.target));
                  if (!$ || !A) return null;
                  let L = x.type || "default";
                  i[L] || (T == null || T("011", Sn.error011(L)), (L = "default"));
                  const D = i[L] || i.default,
                    H = k === Nr.Strict ? b.target : (b.target ?? []).concat(b.source ?? []),
                    B = Gy(N.source, x.sourceHandle),
                    G = Gy(H, x.targetHandle),
                    X = (B == null ? void 0 : B.position) || Y.Bottom,
                    J = (G == null ? void 0 : G.position) || Y.Top,
                    se = !!(x.focusable || (g && typeof x.focusable > "u")),
                    oe = x.reconnectable || x.updatable,
                    ie = typeof d < "u" && (oe || (y && typeof oe > "u"));
                  if (!B || !G) return T == null || T("008", Sn.error008(B, x)), null;
                  const { sourceX: Re, sourceY: Ee, targetX: $e, targetY: Me } = j3(
                    P,
                    B,
                    X,
                    R,
                    G,
                    J
                  );
                  return O.createElement(D, {
                    key: x.id,
                    id: x.id,
                    className: Be([x.className, o]),
                    type: L,
                    data: x.data,
                    selected: !!x.selected,
                    animated: !!x.animated,
                    hidden: !!x.hidden,
                    label: x.label,
                    labelStyle: x.labelStyle,
                    labelShowBg: x.labelShowBg,
                    labelBgStyle: x.labelBgStyle,
                    labelBgPadding: x.labelBgPadding,
                    labelBgBorderRadius: x.labelBgBorderRadius,
                    style: x.style,
                    source: x.source,
                    target: x.target,
                    sourceHandleId: x.sourceHandle,
                    targetHandleId: x.targetHandle,
                    markerEnd: x.markerEnd,
                    markerStart: x.markerStart,
                    sourceX: Re,
                    sourceY: Ee,
                    targetX: $e,
                    targetY: Me,
                    sourcePosition: X,
                    targetPosition: J,
                    elementsSelectable: _,
                    onContextMenu: a,
                    onMouseEnter: s,
                    onMouseMove: u,
                    onMouseLeave: l,
                    onClick: c,
                    onEdgeDoubleClick: f,
                    onReconnect: d,
                    onReconnectStart: h,
                    onReconnectEnd: m,
                    reconnectRadius: v,
                    rfId: r,
                    ariaLabel: x.ariaLabel,
                    isFocusable: se,
                    isReconnectable: ie,
                    pathOptions: "pathOptions" in x ? x.pathOptions : void 0,
                    interactionWidth: x.interactionWidth,
                    disableKeyboardA11y: p,
                  });
                })
              )
            )
          ),
          w
        )
      : null;
  };
Ok.displayName = "EdgeRenderer";
var J3 = q.memo(Ok);
const eq = (e) => `translate(${e.transform[0]}px,${e.transform[1]}px) scale(${e.transform[2]})`;
function tq({ children: e }) {
  const t = fe(eq);
  return O.createElement(
    "div",
    { className: "react-flow__viewport react-flow__container", style: { transform: t } },
    e
  );
}
function nq(e) {
  const t = Ev(),
    n = q.useRef(!1);
  q.useEffect(() => {
    !n.current && t.viewportInitialized && e && (setTimeout(() => e(t), 1), (n.current = !0));
  }, [e, t.viewportInitialized]);
}
const rq = { [Y.Left]: Y.Right, [Y.Right]: Y.Left, [Y.Top]: Y.Bottom, [Y.Bottom]: Y.Top },
  Lk = ({
    nodeId: e,
    handleType: t,
    style: n,
    type: r = Dn.Bezier,
    CustomComponent: i,
    connectionStatus: o,
  }) => {
    var E, k, C;
    const { fromNode: a, handleId: s, toX: u, toY: l, connectionMode: c } = fe(
        q.useCallback(
          (T) => ({
            fromNode: T.nodeInternals.get(e),
            handleId: T.connectionHandleId,
            toX: (T.connectionPosition.x - T.transform[0]) / T.transform[2],
            toY: (T.connectionPosition.y - T.transform[1]) / T.transform[2],
            connectionMode: T.connectionMode,
          }),
          [e]
        ),
        ze
      ),
      f = (E = a == null ? void 0 : a[Se]) == null ? void 0 : E.handleBounds;
    let d = f == null ? void 0 : f[t];
    if (
      (c === Nr.Loose && (d = d || (f == null ? void 0 : f[t === "source" ? "target" : "source"])),
      !a || !d)
    )
      return null;
    const h = s ? d.find((T) => T.id === s) : d[0],
      m = h ? h.x + h.width / 2 : (a.width ?? 0) / 2,
      v = h ? h.y + h.height / 2 : a.height ?? 0,
      w = (((k = a.positionAbsolute) == null ? void 0 : k.x) ?? 0) + m,
      p = (((C = a.positionAbsolute) == null ? void 0 : C.y) ?? 0) + v,
      g = h == null ? void 0 : h.position,
      y = g ? rq[g] : null;
    if (!g || !y) return null;
    if (i)
      return O.createElement(i, {
        connectionLineType: r,
        connectionLineStyle: n,
        fromNode: a,
        fromHandle: h,
        fromX: w,
        fromY: p,
        toX: u,
        toY: l,
        fromPosition: g,
        toPosition: y,
        connectionStatus: o,
      });
    let _ = "";
    const S = {
      sourceX: w,
      sourceY: p,
      sourcePosition: g,
      targetX: u,
      targetY: l,
      targetPosition: y,
    };
    return (
      r === Dn.Bezier
        ? ([_] = sk(S))
        : r === Dn.Step
        ? ([_] = ig({ ...S, borderRadius: 0 }))
        : r === Dn.SmoothStep
        ? ([_] = ig(S))
        : r === Dn.SimpleBezier
        ? ([_] = ak(S))
        : (_ = `M${w},${p} ${u},${l}`),
      O.createElement("path", {
        d: _,
        fill: "none",
        className: "react-flow__connection-path",
        style: n,
      })
    );
  };
Lk.displayName = "ConnectionLine";
const iq = (e) => ({
  nodeId: e.connectionNodeId,
  handleType: e.connectionHandleType,
  nodesConnectable: e.nodesConnectable,
  connectionStatus: e.connectionStatus,
  width: e.width,
  height: e.height,
});
function oq({ containerStyle: e, style: t, type: n, component: r }) {
  const {
    nodeId: i,
    handleType: o,
    nodesConnectable: a,
    width: s,
    height: u,
    connectionStatus: l,
  } = fe(iq, ze);
  return !(i && o && s && a)
    ? null
    : O.createElement(
        "svg",
        {
          style: e,
          width: s,
          height: u,
          className: "react-flow__edges react-flow__connectionline react-flow__container",
        },
        O.createElement(
          "g",
          { className: Be(["react-flow__connection", l]) },
          O.createElement(Lk, {
            nodeId: i,
            handleType: o,
            style: t,
            type: n,
            CustomComponent: r,
            connectionStatus: l,
          })
        )
      );
}
function Yy(e, t) {
  return q.useRef(null), Ae(), q.useMemo(() => t(e), [e]);
}
const zk = ({
  nodeTypes: e,
  edgeTypes: t,
  onMove: n,
  onMoveStart: r,
  onMoveEnd: i,
  onInit: o,
  onNodeClick: a,
  onEdgeClick: s,
  onNodeDoubleClick: u,
  onEdgeDoubleClick: l,
  onNodeMouseEnter: c,
  onNodeMouseMove: f,
  onNodeMouseLeave: d,
  onNodeContextMenu: h,
  onSelectionContextMenu: m,
  onSelectionStart: v,
  onSelectionEnd: w,
  connectionLineType: p,
  connectionLineStyle: g,
  connectionLineComponent: y,
  connectionLineContainerStyle: _,
  selectionKeyCode: S,
  selectionOnDrag: E,
  selectionMode: k,
  multiSelectionKeyCode: C,
  panActivationKeyCode: T,
  zoomActivationKeyCode: I,
  deleteKeyCode: M,
  onlyRenderVisibleElements: z,
  elementsSelectable: F,
  selectNodesOnDrag: x,
  defaultViewport: P,
  translateExtent: N,
  minZoom: $,
  maxZoom: R,
  preventScrolling: b,
  defaultMarkerColor: A,
  zoomOnScroll: L,
  zoomOnPinch: D,
  panOnScroll: H,
  panOnScrollSpeed: B,
  panOnScrollMode: G,
  zoomOnDoubleClick: X,
  panOnDrag: J,
  onPaneClick: se,
  onPaneMouseEnter: oe,
  onPaneMouseMove: ie,
  onPaneMouseLeave: Re,
  onPaneScroll: Ee,
  onPaneContextMenu: $e,
  onEdgeContextMenu: Me,
  onEdgeMouseEnter: Q,
  onEdgeMouseMove: Pe,
  onEdgeMouseLeave: K,
  onReconnect: U,
  onReconnectStart: we,
  onReconnectEnd: Rt,
  reconnectRadius: Ht,
  noDragClassName: Ke,
  noWheelClassName: be,
  noPanClassName: et,
  elevateEdgesOnSelect: Tt,
  disableKeyboardA11y: tn,
  nodeOrigin: Vt,
  nodeExtent: lt,
  rfId: nn,
}) => {
  const Nn = Yy(e, P3),
    qe = Yy(t, F3);
  return (
    nq(o),
    O.createElement(
      A3,
      {
        onPaneClick: se,
        onPaneMouseEnter: oe,
        onPaneMouseMove: ie,
        onPaneMouseLeave: Re,
        onPaneContextMenu: $e,
        onPaneScroll: Ee,
        deleteKeyCode: M,
        selectionKeyCode: S,
        selectionOnDrag: E,
        selectionMode: k,
        onSelectionStart: v,
        onSelectionEnd: w,
        multiSelectionKeyCode: C,
        panActivationKeyCode: T,
        zoomActivationKeyCode: I,
        elementsSelectable: F,
        onMove: n,
        onMoveStart: r,
        onMoveEnd: i,
        zoomOnScroll: L,
        zoomOnPinch: D,
        zoomOnDoubleClick: X,
        panOnScroll: H,
        panOnScrollSpeed: B,
        panOnScrollMode: G,
        panOnDrag: J,
        defaultViewport: P,
        translateExtent: N,
        minZoom: $,
        maxZoom: R,
        onSelectionContextMenu: m,
        preventScrolling: b,
        noDragClassName: Ke,
        noWheelClassName: be,
        noPanClassName: et,
        disableKeyboardA11y: tn,
      },
      O.createElement(
        tq,
        null,
        O.createElement(
          J3,
          {
            edgeTypes: qe,
            onEdgeClick: s,
            onEdgeDoubleClick: l,
            onlyRenderVisibleElements: z,
            onEdgeContextMenu: Me,
            onEdgeMouseEnter: Q,
            onEdgeMouseMove: Pe,
            onEdgeMouseLeave: K,
            onReconnect: U,
            onReconnectStart: we,
            onReconnectEnd: Rt,
            reconnectRadius: Ht,
            defaultMarkerColor: A,
            noPanClassName: et,
            elevateEdgesOnSelect: !!Tt,
            disableKeyboardA11y: tn,
            rfId: nn,
          },
          O.createElement(oq, { style: g, type: p, component: y, containerStyle: _ })
        ),
        O.createElement("div", { className: "react-flow__edgelabel-renderer" }),
        O.createElement(L3, {
          nodeTypes: Nn,
          onNodeClick: a,
          onNodeDoubleClick: u,
          onNodeMouseEnter: c,
          onNodeMouseMove: f,
          onNodeMouseLeave: d,
          onNodeContextMenu: h,
          selectNodesOnDrag: x,
          onlyRenderVisibleElements: z,
          noPanClassName: et,
          noDragClassName: Ke,
          disableKeyboardA11y: tn,
          nodeOrigin: Vt,
          nodeExtent: lt,
          rfId: nn,
        })
      )
    )
  );
};
zk.displayName = "GraphView";
var aq = q.memo(zk);
const lg = [
    [Number.NEGATIVE_INFINITY, Number.NEGATIVE_INFINITY],
    [Number.POSITIVE_INFINITY, Number.POSITIVE_INFINITY],
  ],
  Tn = {
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
    translateExtent: lg,
    nodeExtent: lg,
    nodesSelectionActive: !1,
    userSelectionActive: !1,
    userSelectionRect: null,
    connectionNodeId: null,
    connectionHandleId: null,
    connectionHandleType: "source",
    connectionPosition: { x: 0, y: 0 },
    connectionStatus: null,
    connectionMode: Nr.Strict,
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
    onError: PP,
    isValidConnection: void 0,
  },
  sq = () =>
    KT(
      (e, t) => ({
        ...Tn,
        setNodes: (n) => {
          const { nodeInternals: r, nodeOrigin: i, elevateNodesOnSelect: o } = t();
          e({ nodeInternals: Ju(n, r, i, o) });
        },
        getNodes: () => Array.from(t().nodeInternals.values()),
        setEdges: (n) => {
          const { defaultEdgeOptions: r = {} } = t();
          e({ edges: n.map((i) => ({ ...r, ...i })) });
        },
        setDefaultNodesAndEdges: (n, r) => {
          const i = typeof n < "u",
            o = typeof r < "u",
            a = i ? Ju(n, new Map(), t().nodeOrigin, t().elevateNodesOnSelect) : new Map();
          e({ nodeInternals: a, edges: o ? r : [], hasDefaultNodes: i, hasDefaultEdges: o });
        },
        updateNodeDimensions: (n) => {
          const {
              onNodesChange: r,
              nodeInternals: i,
              fitViewOnInit: o,
              fitViewOnInitDone: a,
              fitViewOnInitOptions: s,
              domNode: u,
              nodeOrigin: l,
            } = t(),
            c = u == null ? void 0 : u.querySelector(".react-flow__viewport");
          if (!c) return;
          const f = window.getComputedStyle(c),
            { m22: d } = new window.DOMMatrixReadOnly(f.transform),
            h = n.reduce((v, w) => {
              const p = i.get(w.id);
              if (p != null && p.hidden)
                i.set(p.id, { ...p, [Se]: { ...p[Se], handleBounds: void 0 } });
              else if (p) {
                const g = gv(w.nodeElement);
                !!(
                  g.width &&
                  g.height &&
                  (p.width !== g.width || p.height !== g.height || w.forceUpdate)
                ) &&
                  (i.set(p.id, {
                    ...p,
                    [Se]: {
                      ...p[Se],
                      handleBounds: {
                        source: By(".source", w.nodeElement, d, l),
                        target: By(".target", w.nodeElement, d, l),
                      },
                    },
                    ...g,
                  }),
                  v.push({ id: p.id, type: "dimensions", dimensions: g }));
              }
              return v;
            }, []);
          kk(i, l);
          const m = a || (o && !a && Ck(t, { initial: !0, ...s }));
          e({ nodeInternals: new Map(i), fitViewOnInitDone: m }),
            (h == null ? void 0 : h.length) > 0 && (r == null || r(h));
        },
        updateNodePositions: (n, r = !0, i = !1) => {
          const { triggerNodeChanges: o } = t(),
            a = n.map((s) => {
              const u = { id: s.id, type: "position", dragging: i };
              return r && ((u.positionAbsolute = s.positionAbsolute), (u.position = s.position)), u;
            });
          o(a);
        },
        triggerNodeChanges: (n) => {
          const {
            onNodesChange: r,
            nodeInternals: i,
            hasDefaultNodes: o,
            nodeOrigin: a,
            getNodes: s,
            elevateNodesOnSelect: u,
          } = t();
          if (n != null && n.length) {
            if (o) {
              const l = S3(n, s()),
                c = Ju(l, i, a, u);
              e({ nodeInternals: c });
            }
            r == null || r(n);
          }
        },
        addSelectedNodes: (n) => {
          const { multiSelectionActive: r, edges: i, getNodes: o } = t();
          let a,
            s = null;
          r ? (a = n.map((u) => Ln(u, !0))) : ((a = Jr(o(), n)), (s = Jr(i, []))),
            Ca({ changedNodes: a, changedEdges: s, get: t, set: e });
        },
        addSelectedEdges: (n) => {
          const { multiSelectionActive: r, edges: i, getNodes: o } = t();
          let a,
            s = null;
          r ? (a = n.map((u) => Ln(u, !0))) : ((a = Jr(i, n)), (s = Jr(o(), []))),
            Ca({ changedNodes: s, changedEdges: a, get: t, set: e });
        },
        unselectNodesAndEdges: ({ nodes: n, edges: r } = {}) => {
          const { edges: i, getNodes: o } = t(),
            a = n || o(),
            s = r || i,
            u = a.map((c) => ((c.selected = !1), Ln(c.id, !1))),
            l = s.map((c) => Ln(c.id, !1));
          Ca({ changedNodes: u, changedEdges: l, get: t, set: e });
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
              .filter((s) => s.selected)
              .map((s) => Ln(s.id, !1)),
            a = n.filter((s) => s.selected).map((s) => Ln(s.id, !1));
          Ca({ changedNodes: o, changedEdges: a, get: t, set: e });
        },
        setNodeExtent: (n) => {
          const { nodeInternals: r } = t();
          r.forEach((i) => {
            i.positionAbsolute = vv(i.position, n);
          }),
            e({ nodeExtent: n, nodeInternals: new Map(r) });
        },
        panBy: (n) => {
          const {
            transform: r,
            width: i,
            height: o,
            d3Zoom: a,
            d3Selection: s,
            translateExtent: u,
          } = t();
          if (!a || !s || (!n.x && !n.y)) return !1;
          const l = vn.translate(r[0] + n.x, r[1] + n.y).scale(r[2]),
            c = [
              [0, 0],
              [i, o],
            ],
            f = a == null ? void 0 : a.constrain()(l, c, u);
          return a.transform(s, f), r[0] !== f.x || r[1] !== f.y || r[2] !== f.k;
        },
        cancelConnection: () =>
          e({
            connectionNodeId: Tn.connectionNodeId,
            connectionHandleId: Tn.connectionHandleId,
            connectionHandleType: Tn.connectionHandleType,
            connectionStatus: Tn.connectionStatus,
            connectionStartHandle: Tn.connectionStartHandle,
            connectionEndHandle: Tn.connectionEndHandle,
          }),
        reset: () => e({ ...Tn }),
      }),
      Object.is
    ),
  $k = ({ children: e }) => {
    const t = q.useRef(null);
    return t.current || (t.current = sq()), O.createElement(CP, { value: t.current }, e);
  };
$k.displayName = "ReactFlowProvider";
const Dk = ({ children: e }) =>
  q.useContext(Xs) ? O.createElement(O.Fragment, null, e) : O.createElement($k, null, e);
Dk.displayName = "ReactFlowWrapper";
const uq = { input: yk, default: sg, output: wk, group: Sv },
  lq = { default: Es, straight: _v, step: yv, smoothstep: Qs, simplebezier: mv },
  cq = [0, 0],
  fq = [15, 15],
  dq = { x: 0, y: 0, zoom: 1 },
  hq = { width: "100%", height: "100%", overflow: "hidden", position: "relative", zIndex: 0 },
  Fk = q.forwardRef(
    (
      {
        nodes: e,
        edges: t,
        defaultNodes: n,
        defaultEdges: r,
        className: i,
        nodeTypes: o = uq,
        edgeTypes: a = lq,
        onNodeClick: s,
        onEdgeClick: u,
        onInit: l,
        onMove: c,
        onMoveStart: f,
        onMoveEnd: d,
        onConnect: h,
        onConnectStart: m,
        onConnectEnd: v,
        onClickConnectStart: w,
        onClickConnectEnd: p,
        onNodeMouseEnter: g,
        onNodeMouseMove: y,
        onNodeMouseLeave: _,
        onNodeContextMenu: S,
        onNodeDoubleClick: E,
        onNodeDragStart: k,
        onNodeDrag: C,
        onNodeDragStop: T,
        onNodesDelete: I,
        onEdgesDelete: M,
        onSelectionChange: z,
        onSelectionDragStart: F,
        onSelectionDrag: x,
        onSelectionDragStop: P,
        onSelectionContextMenu: N,
        onSelectionStart: $,
        onSelectionEnd: R,
        connectionMode: b = Nr.Strict,
        connectionLineType: A = Dn.Bezier,
        connectionLineStyle: L,
        connectionLineComponent: D,
        connectionLineContainerStyle: H,
        deleteKeyCode: B = "Backspace",
        selectionKeyCode: G = "Shift",
        selectionOnDrag: X = !1,
        selectionMode: J = Do.Full,
        panActivationKeyCode: se = "Space",
        multiSelectionKeyCode: oe = Ss() ? "Meta" : "Control",
        zoomActivationKeyCode: ie = Ss() ? "Meta" : "Control",
        snapToGrid: Re = !1,
        snapGrid: Ee = fq,
        onlyRenderVisibleElements: $e = !1,
        selectNodesOnDrag: Me = !0,
        nodesDraggable: Q,
        nodesConnectable: Pe,
        nodesFocusable: K,
        nodeOrigin: U = cq,
        edgesFocusable: we,
        edgesUpdatable: Rt,
        elementsSelectable: Ht,
        defaultViewport: Ke = dq,
        minZoom: be = 0.5,
        maxZoom: et = 2,
        translateExtent: Tt = lg,
        preventScrolling: tn = !0,
        nodeExtent: Vt,
        defaultMarkerColor: lt = "#b1b1b7",
        zoomOnScroll: nn = !0,
        zoomOnPinch: Nn = !0,
        panOnScroll: qe = !1,
        panOnScrollSpeed: tt = 0.5,
        panOnScrollMode: He = gr.Free,
        zoomOnDoubleClick: Ye = !0,
        panOnDrag: ar = !0,
        onPaneClick: rn,
        onPaneMouseEnter: Ut,
        onPaneMouseMove: Ii,
        onPaneMouseLeave: yu,
        onPaneScroll: Ai,
        onPaneContextMenu: _u,
        children: Gv,
        onEdgeContextMenu: sr,
        onEdgeDoubleClick: pC,
        onEdgeMouseEnter: gC,
        onEdgeMouseMove: vC,
        onEdgeMouseLeave: mC,
        onEdgeUpdate: yC,
        onEdgeUpdateStart: _C,
        onEdgeUpdateEnd: wC,
        onReconnect: xC,
        onReconnectStart: SC,
        onReconnectEnd: EC,
        reconnectRadius: bC = 10,
        edgeUpdaterRadius: kC = 10,
        onNodesChange: CC,
        onEdgesChange: NC,
        noDragClassName: RC = "nodrag",
        noWheelClassName: TC = "nowheel",
        noPanClassName: Wv = "nopan",
        fitView: IC = !1,
        fitViewOptions: AC,
        connectOnClick: MC = !0,
        attributionPosition: PC,
        proOptions: qC,
        defaultEdgeOptions: OC,
        elevateNodesOnSelect: LC = !0,
        elevateEdgesOnSelect: zC = !1,
        disableKeyboardA11y: Kv = !1,
        autoPanOnConnect: $C = !0,
        autoPanOnNodeDrag: DC = !0,
        connectionRadius: FC = 20,
        isValidConnection: jC,
        onError: BC,
        style: HC,
        id: Yv,
        nodeDragThreshold: VC,
        ...UC
      },
      GC
    ) => {
      const wu = Yv || "1";
      return O.createElement(
        "div",
        {
          ...UC,
          style: { ...HC, ...hq },
          ref: GC,
          className: Be(["react-flow", i]),
          "data-testid": "rf__wrapper",
          id: Yv,
        },
        O.createElement(
          Dk,
          null,
          O.createElement(aq, {
            onInit: l,
            onMove: c,
            onMoveStart: f,
            onMoveEnd: d,
            onNodeClick: s,
            onEdgeClick: u,
            onNodeMouseEnter: g,
            onNodeMouseMove: y,
            onNodeMouseLeave: _,
            onNodeContextMenu: S,
            onNodeDoubleClick: E,
            nodeTypes: o,
            edgeTypes: a,
            connectionLineType: A,
            connectionLineStyle: L,
            connectionLineComponent: D,
            connectionLineContainerStyle: H,
            selectionKeyCode: G,
            selectionOnDrag: X,
            selectionMode: J,
            deleteKeyCode: B,
            multiSelectionKeyCode: oe,
            panActivationKeyCode: se,
            zoomActivationKeyCode: ie,
            onlyRenderVisibleElements: $e,
            selectNodesOnDrag: Me,
            defaultViewport: Ke,
            translateExtent: Tt,
            minZoom: be,
            maxZoom: et,
            preventScrolling: tn,
            zoomOnScroll: nn,
            zoomOnPinch: Nn,
            zoomOnDoubleClick: Ye,
            panOnScroll: qe,
            panOnScrollSpeed: tt,
            panOnScrollMode: He,
            panOnDrag: ar,
            onPaneClick: rn,
            onPaneMouseEnter: Ut,
            onPaneMouseMove: Ii,
            onPaneMouseLeave: yu,
            onPaneScroll: Ai,
            onPaneContextMenu: _u,
            onSelectionContextMenu: N,
            onSelectionStart: $,
            onSelectionEnd: R,
            onEdgeContextMenu: sr,
            onEdgeDoubleClick: pC,
            onEdgeMouseEnter: gC,
            onEdgeMouseMove: vC,
            onEdgeMouseLeave: mC,
            onReconnect: xC ?? yC,
            onReconnectStart: SC ?? _C,
            onReconnectEnd: EC ?? wC,
            reconnectRadius: bC ?? kC,
            defaultMarkerColor: lt,
            noDragClassName: RC,
            noWheelClassName: TC,
            noPanClassName: Wv,
            elevateEdgesOnSelect: zC,
            rfId: wu,
            disableKeyboardA11y: Kv,
            nodeOrigin: U,
            nodeExtent: Vt,
          }),
          O.createElement(n3, {
            nodes: e,
            edges: t,
            defaultNodes: n,
            defaultEdges: r,
            onConnect: h,
            onConnectStart: m,
            onConnectEnd: v,
            onClickConnectStart: w,
            onClickConnectEnd: p,
            nodesDraggable: Q,
            nodesConnectable: Pe,
            nodesFocusable: K,
            edgesFocusable: we,
            edgesUpdatable: Rt,
            elementsSelectable: Ht,
            elevateNodesOnSelect: LC,
            minZoom: be,
            maxZoom: et,
            nodeExtent: Vt,
            onNodesChange: CC,
            onEdgesChange: NC,
            snapToGrid: Re,
            snapGrid: Ee,
            connectionMode: b,
            translateExtent: Tt,
            connectOnClick: MC,
            defaultEdgeOptions: OC,
            fitView: IC,
            fitViewOptions: AC,
            onNodesDelete: I,
            onEdgesDelete: M,
            onNodeDragStart: k,
            onNodeDrag: C,
            onNodeDragStop: T,
            onSelectionDrag: x,
            onSelectionDragStart: F,
            onSelectionDragStop: P,
            noPanClassName: Wv,
            nodeOrigin: U,
            rfId: wu,
            autoPanOnConnect: $C,
            autoPanOnNodeDrag: DC,
            onError: BC,
            connectionRadius: FC,
            isValidConnection: jC,
            nodeDragThreshold: VC,
          }),
          O.createElement(e3, { onSelectionChange: z }),
          Gv,
          O.createElement(RP, { proOptions: qC, position: PC }),
          O.createElement(s3, { rfId: wu, disableKeyboardA11y: Kv })
        )
      );
    }
  );
Fk.displayName = "ReactFlow";
const jk = ({
  id: e,
  x: t,
  y: n,
  width: r,
  height: i,
  style: o,
  color: a,
  strokeColor: s,
  strokeWidth: u,
  className: l,
  borderRadius: c,
  shapeRendering: f,
  onClick: d,
  selected: h,
}) => {
  const { background: m, backgroundColor: v } = o || {},
    w = a || m || v;
  return O.createElement("rect", {
    className: Be(["react-flow__minimap-node", { selected: h }, l]),
    x: t,
    y: n,
    rx: c,
    ry: c,
    width: r,
    height: i,
    fill: w,
    stroke: s,
    strokeWidth: u,
    shapeRendering: f,
    onClick: d ? (p) => d(p, e) : void 0,
  });
};
jk.displayName = "MiniMapNode";
var pq = q.memo(jk);
const gq = (e) => e.nodeOrigin,
  vq = (e) => e.getNodes().filter((t) => !t.hidden && t.width && t.height),
  rl = (e) => (e instanceof Function ? e : () => e);
function mq({
  nodeStrokeColor: e = "transparent",
  nodeColor: t = "#e2e2e2",
  nodeClassName: n = "",
  nodeBorderRadius: r = 5,
  nodeStrokeWidth: i = 2,
  nodeComponent: o = pq,
  onClick: a,
}) {
  const s = fe(vq, ze),
    u = fe(gq),
    l = rl(t),
    c = rl(e),
    f = rl(n),
    d = typeof window > "u" || window.chrome ? "crispEdges" : "geometricPrecision";
  return O.createElement(
    O.Fragment,
    null,
    s.map((h) => {
      const { x: m, y: v } = wr(h, u).positionAbsolute;
      return O.createElement(o, {
        key: h.id,
        x: m,
        y: v,
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
        onClick: a,
        id: h.id,
      });
    })
  );
}
var yq = q.memo(mq);
const _q = 200,
  wq = 150,
  xq = (e) => {
    const t = e.getNodes(),
      n = {
        x: -e.transform[0] / e.transform[2],
        y: -e.transform[1] / e.transform[2],
        width: e.width / e.transform[2],
        height: e.height / e.transform[2],
      };
    return { viewBB: n, boundingRect: t.length > 0 ? AP(Zs(t, e.nodeOrigin), n) : n, rfId: e.rfId };
  },
  Sq = "react-flow__minimap-desc";
function Bk({
  style: e,
  className: t,
  nodeStrokeColor: n = "transparent",
  nodeColor: r = "#e2e2e2",
  nodeClassName: i = "",
  nodeBorderRadius: o = 5,
  nodeStrokeWidth: a = 2,
  nodeComponent: s,
  maskColor: u = "rgb(240, 240, 240, 0.6)",
  maskStrokeColor: l = "none",
  maskStrokeWidth: c = 1,
  position: f = "bottom-right",
  onClick: d,
  onNodeClick: h,
  pannable: m = !1,
  zoomable: v = !1,
  ariaLabel: w = "React Flow mini map",
  inversePan: p = !1,
  zoomStep: g = 10,
  offsetScale: y = 5,
}) {
  const _ = Ae(),
    S = q.useRef(null),
    { boundingRect: E, viewBB: k, rfId: C } = fe(xq, ze),
    T = (e == null ? void 0 : e.width) ?? _q,
    I = (e == null ? void 0 : e.height) ?? wq,
    M = E.width / T,
    z = E.height / I,
    F = Math.max(M, z),
    x = F * T,
    P = F * I,
    N = y * F,
    $ = E.x - (x - E.width) / 2 - N,
    R = E.y - (P - E.height) / 2 - N,
    b = x + N * 2,
    A = P + N * 2,
    L = `${Sq}-${C}`,
    D = q.useRef(0);
  (D.current = F),
    q.useEffect(() => {
      if (S.current) {
        const G = wt(S.current),
          X = (oe) => {
            const { transform: ie, d3Selection: Re, d3Zoom: Ee } = _.getState();
            if (oe.sourceEvent.type !== "wheel" || !Re || !Ee) return;
            const $e =
                -oe.sourceEvent.deltaY *
                (oe.sourceEvent.deltaMode === 1 ? 0.05 : oe.sourceEvent.deltaMode ? 1 : 0.002) *
                g,
              Me = ie[2] * Math.pow(2, $e);
            Ee.scaleTo(Re, Me);
          },
          J = (oe) => {
            const {
              transform: ie,
              d3Selection: Re,
              d3Zoom: Ee,
              translateExtent: $e,
              width: Me,
              height: Q,
            } = _.getState();
            if (oe.sourceEvent.type !== "mousemove" || !Re || !Ee) return;
            const Pe = D.current * Math.max(1, ie[2]) * (p ? -1 : 1),
              K = {
                x: ie[0] - oe.sourceEvent.movementX * Pe,
                y: ie[1] - oe.sourceEvent.movementY * Pe,
              },
              U = [
                [0, 0],
                [Me, Q],
              ],
              we = vn.translate(K.x, K.y).scale(ie[2]),
              Rt = Ee.constrain()(we, U, $e);
            Ee.transform(Re, Rt);
          },
          se = Xb()
            .on("zoom", m ? J : null)
            .on("zoom.wheel", v ? X : null);
        return (
          G.call(se),
          () => {
            G.on("zoom", null);
          }
        );
      }
    }, [m, v, p, g]);
  const H = d
      ? (G) => {
          const X = Pt(G);
          d(G, { x: X[0], y: X[1] });
        }
      : void 0,
    B = h
      ? (G, X) => {
          const J = _.getState().nodeInternals.get(X);
          h(G, J);
        }
      : void 0;
  return O.createElement(
    pv,
    {
      position: f,
      style: e,
      className: Be(["react-flow__minimap", t]),
      "data-testid": "rf__minimap",
    },
    O.createElement(
      "svg",
      {
        width: T,
        height: I,
        viewBox: `${$} ${R} ${b} ${A}`,
        role: "img",
        "aria-labelledby": L,
        ref: S,
        onClick: H,
      },
      w && O.createElement("title", { id: L }, w),
      O.createElement(yq, {
        onClick: B,
        nodeColor: r,
        nodeStrokeColor: n,
        nodeBorderRadius: o,
        nodeClassName: i,
        nodeStrokeWidth: a,
        nodeComponent: s,
      }),
      O.createElement("path", {
        className: "react-flow__minimap-mask",
        d: `M${$ - N},${R - N}h${b + N * 2}v${A + N * 2}h${-b - N * 2}z
        M${k.x},${k.y}h${k.width}v${k.height}h${-k.width}z`,
        fill: u,
        fillRule: "evenodd",
        stroke: l,
        strokeWidth: c,
        pointerEvents: "none",
      })
    )
  );
}
Bk.displayName = "MiniMap";
var Eq = q.memo(Bk);
function bq() {
  return O.createElement(
    "svg",
    { xmlns: "http://www.w3.org/2000/svg", viewBox: "0 0 32 32" },
    O.createElement("path", {
      d: "M32 18.133H18.133V32h-4.266V18.133H0v-4.266h13.867V0h4.266v13.867H32z",
    })
  );
}
function kq() {
  return O.createElement(
    "svg",
    { xmlns: "http://www.w3.org/2000/svg", viewBox: "0 0 32 5" },
    O.createElement("path", { d: "M0 0h32v4.2H0z" })
  );
}
function Cq() {
  return O.createElement(
    "svg",
    { xmlns: "http://www.w3.org/2000/svg", viewBox: "0 0 32 30" },
    O.createElement("path", {
      d:
        "M3.692 4.63c0-.53.4-.938.939-.938h5.215V0H4.708C2.13 0 0 2.054 0 4.63v5.216h3.692V4.631zM27.354 0h-5.2v3.692h5.17c.53 0 .984.4.984.939v5.215H32V4.631A4.624 4.624 0 0027.354 0zm.954 24.83c0 .532-.4.94-.939.94h-5.215v3.768h5.215c2.577 0 4.631-2.13 4.631-4.707v-5.139h-3.692v5.139zm-23.677.94c-.531 0-.939-.4-.939-.94v-5.138H0v5.139c0 2.577 2.13 4.707 4.708 4.707h5.138V25.77H4.631z",
    })
  );
}
function Nq() {
  return O.createElement(
    "svg",
    { xmlns: "http://www.w3.org/2000/svg", viewBox: "0 0 25 32" },
    O.createElement("path", {
      d:
        "M21.333 10.667H19.81V7.619C19.81 3.429 16.38 0 12.19 0 8 0 4.571 3.429 4.571 7.619v3.048H3.048A3.056 3.056 0 000 13.714v15.238A3.056 3.056 0 003.048 32h18.285a3.056 3.056 0 003.048-3.048V13.714a3.056 3.056 0 00-3.048-3.047zM12.19 24.533a3.056 3.056 0 01-3.047-3.047 3.056 3.056 0 013.047-3.048 3.056 3.056 0 013.048 3.048 3.056 3.056 0 01-3.048 3.047zm4.724-13.866H7.467V7.619c0-2.59 2.133-4.724 4.723-4.724 2.591 0 4.724 2.133 4.724 4.724v3.048z",
    })
  );
}
function Rq() {
  return O.createElement(
    "svg",
    { xmlns: "http://www.w3.org/2000/svg", viewBox: "0 0 25 32" },
    O.createElement("path", {
      d:
        "M21.333 10.667H19.81V7.619C19.81 3.429 16.38 0 12.19 0c-4.114 1.828-1.37 2.133.305 2.438 1.676.305 4.42 2.59 4.42 5.181v3.048H3.047A3.056 3.056 0 000 13.714v15.238A3.056 3.056 0 003.048 32h18.285a3.056 3.056 0 003.048-3.048V13.714a3.056 3.056 0 00-3.048-3.047zM12.19 24.533a3.056 3.056 0 01-3.047-3.047 3.056 3.056 0 013.047-3.048 3.056 3.056 0 013.048 3.048 3.056 3.056 0 01-3.048 3.047z",
    })
  );
}
const Ji = ({ children: e, className: t, ...n }) =>
  O.createElement(
    "button",
    { type: "button", className: Be(["react-flow__controls-button", t]), ...n },
    e
  );
Ji.displayName = "ControlButton";
const Tq = (e) => ({
    isInteractive: e.nodesDraggable || e.nodesConnectable || e.elementsSelectable,
    minZoomReached: e.transform[2] <= e.minZoom,
    maxZoomReached: e.transform[2] >= e.maxZoom,
  }),
  Hk = ({
    style: e,
    showZoom: t = !0,
    showFitView: n = !0,
    showInteractive: r = !0,
    fitViewOptions: i,
    onZoomIn: o,
    onZoomOut: a,
    onFitView: s,
    onInteractiveChange: u,
    className: l,
    children: c,
    position: f = "bottom-left",
  }) => {
    const d = Ae(),
      [h, m] = q.useState(!1),
      { isInteractive: v, minZoomReached: w, maxZoomReached: p } = fe(Tq, ze),
      { zoomIn: g, zoomOut: y, fitView: _ } = Ev();
    if (
      (q.useEffect(() => {
        m(!0);
      }, []),
      !h)
    )
      return null;
    const S = () => {
        g(), o == null || o();
      },
      E = () => {
        y(), a == null || a();
      },
      k = () => {
        _(i), s == null || s();
      },
      C = () => {
        d.setState({ nodesDraggable: !v, nodesConnectable: !v, elementsSelectable: !v }),
          u == null || u(!v);
      };
    return O.createElement(
      pv,
      {
        className: Be(["react-flow__controls", l]),
        position: f,
        style: e,
        "data-testid": "rf__controls",
      },
      t &&
        O.createElement(
          O.Fragment,
          null,
          O.createElement(
            Ji,
            {
              onClick: S,
              className: "react-flow__controls-zoomin",
              title: "zoom in",
              "aria-label": "zoom in",
              disabled: p,
            },
            O.createElement(bq, null)
          ),
          O.createElement(
            Ji,
            {
              onClick: E,
              className: "react-flow__controls-zoomout",
              title: "zoom out",
              "aria-label": "zoom out",
              disabled: w,
            },
            O.createElement(kq, null)
          )
        ),
      n &&
        O.createElement(
          Ji,
          {
            className: "react-flow__controls-fitview",
            onClick: k,
            title: "fit view",
            "aria-label": "fit view",
          },
          O.createElement(Cq, null)
        ),
      r &&
        O.createElement(
          Ji,
          {
            className: "react-flow__controls-interactive",
            onClick: C,
            title: "toggle interactivity",
            "aria-label": "toggle interactivity",
          },
          v ? O.createElement(Rq, null) : O.createElement(Nq, null)
        ),
      c
    );
  };
Hk.displayName = "Controls";
var Iq = q.memo(Hk),
  $t;
(function (e) {
  (e.Lines = "lines"), (e.Dots = "dots"), (e.Cross = "cross");
})($t || ($t = {}));
function Aq({ color: e, dimensions: t, lineWidth: n }) {
  return O.createElement("path", {
    stroke: e,
    strokeWidth: n,
    d: `M${t[0] / 2} 0 V${t[1]} M0 ${t[1] / 2} H${t[0]}`,
  });
}
function Mq({ color: e, radius: t }) {
  return O.createElement("circle", { cx: t, cy: t, r: t, fill: e });
}
const Pq = { [$t.Dots]: "#91919a", [$t.Lines]: "#eee", [$t.Cross]: "#e2e2e2" },
  qq = { [$t.Dots]: 1, [$t.Lines]: 1, [$t.Cross]: 6 },
  Oq = (e) => ({ transform: e.transform, patternId: `pattern-${e.rfId}` });
function Vk({
  id: e,
  variant: t = $t.Dots,
  gap: n = 20,
  size: r,
  lineWidth: i = 1,
  offset: o = 2,
  color: a,
  style: s,
  className: u,
}) {
  const l = q.useRef(null),
    { transform: c, patternId: f } = fe(Oq, ze),
    d = a || Pq[t],
    h = r || qq[t],
    m = t === $t.Dots,
    v = t === $t.Cross,
    w = Array.isArray(n) ? n : [n, n],
    p = [w[0] * c[2] || 1, w[1] * c[2] || 1],
    g = h * c[2],
    y = v ? [g, g] : p,
    _ = m ? [g / o, g / o] : [y[0] / o, y[1] / o];
  return O.createElement(
    "svg",
    {
      className: Be(["react-flow__background", u]),
      style: { ...s, position: "absolute", width: "100%", height: "100%", top: 0, left: 0 },
      ref: l,
      "data-testid": "rf__background",
    },
    O.createElement(
      "pattern",
      {
        id: f + e,
        x: c[0] % p[0],
        y: c[1] % p[1],
        width: p[0],
        height: p[1],
        patternUnits: "userSpaceOnUse",
        patternTransform: `translate(-${_[0]},-${_[1]})`,
      },
      m
        ? O.createElement(Mq, { color: d, radius: g / o })
        : O.createElement(Aq, { dimensions: y, color: d, lineWidth: i })
    ),
    O.createElement("rect", {
      x: "0",
      y: "0",
      width: "100%",
      height: "100%",
      fill: `url(#${f + e})`,
    })
  );
}
Vk.displayName = "Background";
var Lq = q.memo(Vk);
function kv(e) {
  throw new Error(
    'Could not dynamically require "' +
      e +
      '". Please configure the dynamicRequireTargets or/and ignoreDynamicRequires option of @rollup/plugin-commonjs appropriately for this require call to work.'
  );
}
var il, Xy;
function zq() {
  if (Xy) return il;
  Xy = 1;
  function e() {
    (this.__data__ = []), (this.size = 0);
  }
  return (il = e), il;
}
var ol, Qy;
function bi() {
  if (Qy) return ol;
  Qy = 1;
  function e(t, n) {
    return t === n || (t !== t && n !== n);
  }
  return (ol = e), ol;
}
var al, Zy;
function Js() {
  if (Zy) return al;
  Zy = 1;
  var e = bi();
  function t(n, r) {
    for (var i = n.length; i--; ) if (e(n[i][0], r)) return i;
    return -1;
  }
  return (al = t), al;
}
var sl, Jy;
function $q() {
  if (Jy) return sl;
  Jy = 1;
  var e = Js(),
    t = Array.prototype,
    n = t.splice;
  function r(i) {
    var o = this.__data__,
      a = e(o, i);
    if (a < 0) return !1;
    var s = o.length - 1;
    return a == s ? o.pop() : n.call(o, a, 1), --this.size, !0;
  }
  return (sl = r), sl;
}
var ul, e0;
function Dq() {
  if (e0) return ul;
  e0 = 1;
  var e = Js();
  function t(n) {
    var r = this.__data__,
      i = e(r, n);
    return i < 0 ? void 0 : r[i][1];
  }
  return (ul = t), ul;
}
var ll, t0;
function Fq() {
  if (t0) return ll;
  t0 = 1;
  var e = Js();
  function t(n) {
    return e(this.__data__, n) > -1;
  }
  return (ll = t), ll;
}
var cl, n0;
function jq() {
  if (n0) return cl;
  n0 = 1;
  var e = Js();
  function t(n, r) {
    var i = this.__data__,
      o = e(i, n);
    return o < 0 ? (++this.size, i.push([n, r])) : (i[o][1] = r), this;
  }
  return (cl = t), cl;
}
var fl, r0;
function eu() {
  if (r0) return fl;
  r0 = 1;
  var e = zq(),
    t = $q(),
    n = Dq(),
    r = Fq(),
    i = jq();
  function o(a) {
    var s = -1,
      u = a == null ? 0 : a.length;
    for (this.clear(); ++s < u; ) {
      var l = a[s];
      this.set(l[0], l[1]);
    }
  }
  return (
    (o.prototype.clear = e),
    (o.prototype.delete = t),
    (o.prototype.get = n),
    (o.prototype.has = r),
    (o.prototype.set = i),
    (fl = o),
    fl
  );
}
var dl, i0;
function Bq() {
  if (i0) return dl;
  i0 = 1;
  var e = eu();
  function t() {
    (this.__data__ = new e()), (this.size = 0);
  }
  return (dl = t), dl;
}
var hl, o0;
function Hq() {
  if (o0) return hl;
  o0 = 1;
  function e(t) {
    var n = this.__data__,
      r = n.delete(t);
    return (this.size = n.size), r;
  }
  return (hl = e), hl;
}
var pl, a0;
function Vq() {
  if (a0) return pl;
  a0 = 1;
  function e(t) {
    return this.__data__.get(t);
  }
  return (pl = e), pl;
}
var gl, s0;
function Uq() {
  if (s0) return gl;
  s0 = 1;
  function e(t) {
    return this.__data__.has(t);
  }
  return (gl = e), gl;
}
var vl, u0;
function Uk() {
  if (u0) return vl;
  u0 = 1;
  var e = typeof ta == "object" && ta && ta.Object === Object && ta;
  return (vl = e), vl;
}
var ml, l0;
function jt() {
  if (l0) return ml;
  l0 = 1;
  var e = Uk(),
    t = typeof self == "object" && self && self.Object === Object && self,
    n = e || t || Function("return this")();
  return (ml = n), ml;
}
var yl, c0;
function ki() {
  if (c0) return yl;
  c0 = 1;
  var e = jt(),
    t = e.Symbol;
  return (yl = t), yl;
}
var _l, f0;
function Gq() {
  if (f0) return _l;
  f0 = 1;
  var e = ki(),
    t = Object.prototype,
    n = t.hasOwnProperty,
    r = t.toString,
    i = e ? e.toStringTag : void 0;
  function o(a) {
    var s = n.call(a, i),
      u = a[i];
    try {
      a[i] = void 0;
      var l = !0;
    } catch {}
    var c = r.call(a);
    return l && (s ? (a[i] = u) : delete a[i]), c;
  }
  return (_l = o), _l;
}
var wl, d0;
function Wq() {
  if (d0) return wl;
  d0 = 1;
  var e = Object.prototype,
    t = e.toString;
  function n(r) {
    return t.call(r);
  }
  return (wl = n), wl;
}
var xl, h0;
function Ir() {
  if (h0) return xl;
  h0 = 1;
  var e = ki(),
    t = Gq(),
    n = Wq(),
    r = "[object Null]",
    i = "[object Undefined]",
    o = e ? e.toStringTag : void 0;
  function a(s) {
    return s == null ? (s === void 0 ? i : r) : o && o in Object(s) ? t(s) : n(s);
  }
  return (xl = a), xl;
}
var Sl, p0;
function Ct() {
  if (p0) return Sl;
  p0 = 1;
  function e(t) {
    var n = typeof t;
    return t != null && (n == "object" || n == "function");
  }
  return (Sl = e), Sl;
}
var El, g0;
function Xo() {
  if (g0) return El;
  g0 = 1;
  var e = Ir(),
    t = Ct(),
    n = "[object AsyncFunction]",
    r = "[object Function]",
    i = "[object GeneratorFunction]",
    o = "[object Proxy]";
  function a(s) {
    if (!t(s)) return !1;
    var u = e(s);
    return u == r || u == i || u == n || u == o;
  }
  return (El = a), El;
}
var bl, v0;
function Kq() {
  if (v0) return bl;
  v0 = 1;
  var e = jt(),
    t = e["__core-js_shared__"];
  return (bl = t), bl;
}
var kl, m0;
function Yq() {
  if (m0) return kl;
  m0 = 1;
  var e = Kq(),
    t = (function () {
      var r = /[^.]+$/.exec((e && e.keys && e.keys.IE_PROTO) || "");
      return r ? "Symbol(src)_1." + r : "";
    })();
  function n(r) {
    return !!t && t in r;
  }
  return (kl = n), kl;
}
var Cl, y0;
function Gk() {
  if (y0) return Cl;
  y0 = 1;
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
  return (Cl = n), Cl;
}
var Nl, _0;
function Xq() {
  if (_0) return Nl;
  _0 = 1;
  var e = Xo(),
    t = Yq(),
    n = Ct(),
    r = Gk(),
    i = /[\\^$.*+?()[\]{}|]/g,
    o = /^\[object .+?Constructor\]$/,
    a = Function.prototype,
    s = Object.prototype,
    u = a.toString,
    l = s.hasOwnProperty,
    c = RegExp(
      "^" +
        u
          .call(l)
          .replace(i, "\\$&")
          .replace(/hasOwnProperty|(function).*?(?=\\\()| for .+?(?=\\\])/g, "$1.*?") +
        "$"
    );
  function f(d) {
    if (!n(d) || t(d)) return !1;
    var h = e(d) ? c : o;
    return h.test(r(d));
  }
  return (Nl = f), Nl;
}
var Rl, w0;
function Qq() {
  if (w0) return Rl;
  w0 = 1;
  function e(t, n) {
    return t == null ? void 0 : t[n];
  }
  return (Rl = e), Rl;
}
var Tl, x0;
function Ar() {
  if (x0) return Tl;
  x0 = 1;
  var e = Xq(),
    t = Qq();
  function n(r, i) {
    var o = t(r, i);
    return e(o) ? o : void 0;
  }
  return (Tl = n), Tl;
}
var Il, S0;
function Cv() {
  if (S0) return Il;
  S0 = 1;
  var e = Ar(),
    t = jt(),
    n = e(t, "Map");
  return (Il = n), Il;
}
var Al, E0;
function tu() {
  if (E0) return Al;
  E0 = 1;
  var e = Ar(),
    t = e(Object, "create");
  return (Al = t), Al;
}
var Ml, b0;
function Zq() {
  if (b0) return Ml;
  b0 = 1;
  var e = tu();
  function t() {
    (this.__data__ = e ? e(null) : {}), (this.size = 0);
  }
  return (Ml = t), Ml;
}
var Pl, k0;
function Jq() {
  if (k0) return Pl;
  k0 = 1;
  function e(t) {
    var n = this.has(t) && delete this.__data__[t];
    return (this.size -= n ? 1 : 0), n;
  }
  return (Pl = e), Pl;
}
var ql, C0;
function e4() {
  if (C0) return ql;
  C0 = 1;
  var e = tu(),
    t = "__lodash_hash_undefined__",
    n = Object.prototype,
    r = n.hasOwnProperty;
  function i(o) {
    var a = this.__data__;
    if (e) {
      var s = a[o];
      return s === t ? void 0 : s;
    }
    return r.call(a, o) ? a[o] : void 0;
  }
  return (ql = i), ql;
}
var Ol, N0;
function t4() {
  if (N0) return Ol;
  N0 = 1;
  var e = tu(),
    t = Object.prototype,
    n = t.hasOwnProperty;
  function r(i) {
    var o = this.__data__;
    return e ? o[i] !== void 0 : n.call(o, i);
  }
  return (Ol = r), Ol;
}
var Ll, R0;
function n4() {
  if (R0) return Ll;
  R0 = 1;
  var e = tu(),
    t = "__lodash_hash_undefined__";
  function n(r, i) {
    var o = this.__data__;
    return (this.size += this.has(r) ? 0 : 1), (o[r] = e && i === void 0 ? t : i), this;
  }
  return (Ll = n), Ll;
}
var zl, T0;
function r4() {
  if (T0) return zl;
  T0 = 1;
  var e = Zq(),
    t = Jq(),
    n = e4(),
    r = t4(),
    i = n4();
  function o(a) {
    var s = -1,
      u = a == null ? 0 : a.length;
    for (this.clear(); ++s < u; ) {
      var l = a[s];
      this.set(l[0], l[1]);
    }
  }
  return (
    (o.prototype.clear = e),
    (o.prototype.delete = t),
    (o.prototype.get = n),
    (o.prototype.has = r),
    (o.prototype.set = i),
    (zl = o),
    zl
  );
}
var $l, I0;
function i4() {
  if (I0) return $l;
  I0 = 1;
  var e = r4(),
    t = eu(),
    n = Cv();
  function r() {
    (this.size = 0), (this.__data__ = { hash: new e(), map: new (n || t)(), string: new e() });
  }
  return ($l = r), $l;
}
var Dl, A0;
function o4() {
  if (A0) return Dl;
  A0 = 1;
  function e(t) {
    var n = typeof t;
    return n == "string" || n == "number" || n == "symbol" || n == "boolean"
      ? t !== "__proto__"
      : t === null;
  }
  return (Dl = e), Dl;
}
var Fl, M0;
function nu() {
  if (M0) return Fl;
  M0 = 1;
  var e = o4();
  function t(n, r) {
    var i = n.__data__;
    return e(r) ? i[typeof r == "string" ? "string" : "hash"] : i.map;
  }
  return (Fl = t), Fl;
}
var jl, P0;
function a4() {
  if (P0) return jl;
  P0 = 1;
  var e = nu();
  function t(n) {
    var r = e(this, n).delete(n);
    return (this.size -= r ? 1 : 0), r;
  }
  return (jl = t), jl;
}
var Bl, q0;
function s4() {
  if (q0) return Bl;
  q0 = 1;
  var e = nu();
  function t(n) {
    return e(this, n).get(n);
  }
  return (Bl = t), Bl;
}
var Hl, O0;
function u4() {
  if (O0) return Hl;
  O0 = 1;
  var e = nu();
  function t(n) {
    return e(this, n).has(n);
  }
  return (Hl = t), Hl;
}
var Vl, L0;
function l4() {
  if (L0) return Vl;
  L0 = 1;
  var e = nu();
  function t(n, r) {
    var i = e(this, n),
      o = i.size;
    return i.set(n, r), (this.size += i.size == o ? 0 : 1), this;
  }
  return (Vl = t), Vl;
}
var Ul, z0;
function Nv() {
  if (z0) return Ul;
  z0 = 1;
  var e = i4(),
    t = a4(),
    n = s4(),
    r = u4(),
    i = l4();
  function o(a) {
    var s = -1,
      u = a == null ? 0 : a.length;
    for (this.clear(); ++s < u; ) {
      var l = a[s];
      this.set(l[0], l[1]);
    }
  }
  return (
    (o.prototype.clear = e),
    (o.prototype.delete = t),
    (o.prototype.get = n),
    (o.prototype.has = r),
    (o.prototype.set = i),
    (Ul = o),
    Ul
  );
}
var Gl, $0;
function c4() {
  if ($0) return Gl;
  $0 = 1;
  var e = eu(),
    t = Cv(),
    n = Nv(),
    r = 200;
  function i(o, a) {
    var s = this.__data__;
    if (s instanceof e) {
      var u = s.__data__;
      if (!t || u.length < r - 1) return u.push([o, a]), (this.size = ++s.size), this;
      s = this.__data__ = new n(u);
    }
    return s.set(o, a), (this.size = s.size), this;
  }
  return (Gl = i), Gl;
}
var Wl, D0;
function ru() {
  if (D0) return Wl;
  D0 = 1;
  var e = eu(),
    t = Bq(),
    n = Hq(),
    r = Vq(),
    i = Uq(),
    o = c4();
  function a(s) {
    var u = (this.__data__ = new e(s));
    this.size = u.size;
  }
  return (
    (a.prototype.clear = t),
    (a.prototype.delete = n),
    (a.prototype.get = r),
    (a.prototype.has = i),
    (a.prototype.set = o),
    (Wl = a),
    Wl
  );
}
var Kl, F0;
function Rv() {
  if (F0) return Kl;
  F0 = 1;
  function e(t, n) {
    for (var r = -1, i = t == null ? 0 : t.length; ++r < i && n(t[r], r, t) !== !1; );
    return t;
  }
  return (Kl = e), Kl;
}
var Yl, j0;
function Wk() {
  if (j0) return Yl;
  j0 = 1;
  var e = Ar(),
    t = (function () {
      try {
        var n = e(Object, "defineProperty");
        return n({}, "", {}), n;
      } catch {}
    })();
  return (Yl = t), Yl;
}
var Xl, B0;
function iu() {
  if (B0) return Xl;
  B0 = 1;
  var e = Wk();
  function t(n, r, i) {
    r == "__proto__" && e
      ? e(n, r, { configurable: !0, enumerable: !0, value: i, writable: !0 })
      : (n[r] = i);
  }
  return (Xl = t), Xl;
}
var Ql, H0;
function ou() {
  if (H0) return Ql;
  H0 = 1;
  var e = iu(),
    t = bi(),
    n = Object.prototype,
    r = n.hasOwnProperty;
  function i(o, a, s) {
    var u = o[a];
    (!(r.call(o, a) && t(u, s)) || (s === void 0 && !(a in o))) && e(o, a, s);
  }
  return (Ql = i), Ql;
}
var Zl, V0;
function Qo() {
  if (V0) return Zl;
  V0 = 1;
  var e = ou(),
    t = iu();
  function n(r, i, o, a) {
    var s = !o;
    o || (o = {});
    for (var u = -1, l = i.length; ++u < l; ) {
      var c = i[u],
        f = a ? a(o[c], r[c], c, o, r) : void 0;
      f === void 0 && (f = r[c]), s ? t(o, c, f) : e(o, c, f);
    }
    return o;
  }
  return (Zl = n), Zl;
}
var Jl, U0;
function f4() {
  if (U0) return Jl;
  U0 = 1;
  function e(t, n) {
    for (var r = -1, i = Array(t); ++r < t; ) i[r] = n(r);
    return i;
  }
  return (Jl = e), Jl;
}
var ec, G0;
function en() {
  if (G0) return ec;
  G0 = 1;
  function e(t) {
    return t != null && typeof t == "object";
  }
  return (ec = e), ec;
}
var tc, W0;
function d4() {
  if (W0) return tc;
  W0 = 1;
  var e = Ir(),
    t = en(),
    n = "[object Arguments]";
  function r(i) {
    return t(i) && e(i) == n;
  }
  return (tc = r), tc;
}
var nc, K0;
function Zo() {
  if (K0) return nc;
  K0 = 1;
  var e = d4(),
    t = en(),
    n = Object.prototype,
    r = n.hasOwnProperty,
    i = n.propertyIsEnumerable,
    o = e(
      (function () {
        return arguments;
      })()
    )
      ? e
      : function (a) {
          return t(a) && r.call(a, "callee") && !i.call(a, "callee");
        };
  return (nc = o), nc;
}
var rc, Y0;
function Ne() {
  if (Y0) return rc;
  Y0 = 1;
  var e = Array.isArray;
  return (rc = e), rc;
}
var eo = { exports: {} },
  ic,
  X0;
function h4() {
  if (X0) return ic;
  X0 = 1;
  function e() {
    return !1;
  }
  return (ic = e), ic;
}
eo.exports;
var Q0;
function Ci() {
  return (
    Q0 ||
      ((Q0 = 1),
      (function (e, t) {
        var n = jt(),
          r = h4(),
          i = t && !t.nodeType && t,
          o = i && !0 && e && !e.nodeType && e,
          a = o && o.exports === i,
          s = a ? n.Buffer : void 0,
          u = s ? s.isBuffer : void 0,
          l = u || r;
        e.exports = l;
      })(eo, eo.exports)),
    eo.exports
  );
}
var oc, Z0;
function au() {
  if (Z0) return oc;
  Z0 = 1;
  var e = 9007199254740991,
    t = /^(?:0|[1-9]\d*)$/;
  function n(r, i) {
    var o = typeof r;
    return (
      (i = i ?? e),
      !!i && (o == "number" || (o != "symbol" && t.test(r))) && r > -1 && r % 1 == 0 && r < i
    );
  }
  return (oc = n), oc;
}
var ac, J0;
function Tv() {
  if (J0) return ac;
  J0 = 1;
  var e = 9007199254740991;
  function t(n) {
    return typeof n == "number" && n > -1 && n % 1 == 0 && n <= e;
  }
  return (ac = t), ac;
}
var sc, e1;
function p4() {
  if (e1) return sc;
  e1 = 1;
  var e = Ir(),
    t = Tv(),
    n = en(),
    r = "[object Arguments]",
    i = "[object Array]",
    o = "[object Boolean]",
    a = "[object Date]",
    s = "[object Error]",
    u = "[object Function]",
    l = "[object Map]",
    c = "[object Number]",
    f = "[object Object]",
    d = "[object RegExp]",
    h = "[object Set]",
    m = "[object String]",
    v = "[object WeakMap]",
    w = "[object ArrayBuffer]",
    p = "[object DataView]",
    g = "[object Float32Array]",
    y = "[object Float64Array]",
    _ = "[object Int8Array]",
    S = "[object Int16Array]",
    E = "[object Int32Array]",
    k = "[object Uint8Array]",
    C = "[object Uint8ClampedArray]",
    T = "[object Uint16Array]",
    I = "[object Uint32Array]",
    M = {};
  (M[g] = M[y] = M[_] = M[S] = M[E] = M[k] = M[C] = M[T] = M[I] = !0),
    (M[r] = M[i] = M[w] = M[o] = M[p] = M[a] = M[s] = M[u] = M[l] = M[c] = M[f] = M[d] = M[h] = M[
      m
    ] = M[v] = !1);
  function z(F) {
    return n(F) && t(F.length) && !!M[e(F)];
  }
  return (sc = z), sc;
}
var uc, t1;
function su() {
  if (t1) return uc;
  t1 = 1;
  function e(t) {
    return function (n) {
      return t(n);
    };
  }
  return (uc = e), uc;
}
var to = { exports: {} };
to.exports;
var n1;
function Iv() {
  return (
    n1 ||
      ((n1 = 1),
      (function (e, t) {
        var n = Uk(),
          r = t && !t.nodeType && t,
          i = r && !0 && e && !e.nodeType && e,
          o = i && i.exports === r,
          a = o && n.process,
          s = (function () {
            try {
              var u = i && i.require && i.require("util").types;
              return u || (a && a.binding && a.binding("util"));
            } catch {}
          })();
        e.exports = s;
      })(to, to.exports)),
    to.exports
  );
}
var lc, r1;
function Jo() {
  if (r1) return lc;
  r1 = 1;
  var e = p4(),
    t = su(),
    n = Iv(),
    r = n && n.isTypedArray,
    i = r ? t(r) : e;
  return (lc = i), lc;
}
var cc, i1;
function Kk() {
  if (i1) return cc;
  i1 = 1;
  var e = f4(),
    t = Zo(),
    n = Ne(),
    r = Ci(),
    i = au(),
    o = Jo(),
    a = Object.prototype,
    s = a.hasOwnProperty;
  function u(l, c) {
    var f = n(l),
      d = !f && t(l),
      h = !f && !d && r(l),
      m = !f && !d && !h && o(l),
      v = f || d || h || m,
      w = v ? e(l.length, String) : [],
      p = w.length;
    for (var g in l)
      (c || s.call(l, g)) &&
        !(
          v &&
          (g == "length" ||
            (h && (g == "offset" || g == "parent")) ||
            (m && (g == "buffer" || g == "byteLength" || g == "byteOffset")) ||
            i(g, p))
        ) &&
        w.push(g);
    return w;
  }
  return (cc = u), cc;
}
var fc, o1;
function uu() {
  if (o1) return fc;
  o1 = 1;
  var e = Object.prototype;
  function t(n) {
    var r = n && n.constructor,
      i = (typeof r == "function" && r.prototype) || e;
    return n === i;
  }
  return (fc = t), fc;
}
var dc, a1;
function Yk() {
  if (a1) return dc;
  a1 = 1;
  function e(t, n) {
    return function (r) {
      return t(n(r));
    };
  }
  return (dc = e), dc;
}
var hc, s1;
function g4() {
  if (s1) return hc;
  s1 = 1;
  var e = Yk(),
    t = e(Object.keys, Object);
  return (hc = t), hc;
}
var pc, u1;
function Av() {
  if (u1) return pc;
  u1 = 1;
  var e = uu(),
    t = g4(),
    n = Object.prototype,
    r = n.hasOwnProperty;
  function i(o) {
    if (!e(o)) return t(o);
    var a = [];
    for (var s in Object(o)) r.call(o, s) && s != "constructor" && a.push(s);
    return a;
  }
  return (pc = i), pc;
}
var gc, l1;
function kn() {
  if (l1) return gc;
  l1 = 1;
  var e = Xo(),
    t = Tv();
  function n(r) {
    return r != null && t(r.length) && !e(r);
  }
  return (gc = n), gc;
}
var vc, c1;
function or() {
  if (c1) return vc;
  c1 = 1;
  var e = Kk(),
    t = Av(),
    n = kn();
  function r(i) {
    return n(i) ? e(i) : t(i);
  }
  return (vc = r), vc;
}
var mc, f1;
function v4() {
  if (f1) return mc;
  f1 = 1;
  var e = Qo(),
    t = or();
  function n(r, i) {
    return r && e(i, t(i), r);
  }
  return (mc = n), mc;
}
var yc, d1;
function m4() {
  if (d1) return yc;
  d1 = 1;
  function e(t) {
    var n = [];
    if (t != null) for (var r in Object(t)) n.push(r);
    return n;
  }
  return (yc = e), yc;
}
var _c, h1;
function y4() {
  if (h1) return _c;
  h1 = 1;
  var e = Ct(),
    t = uu(),
    n = m4(),
    r = Object.prototype,
    i = r.hasOwnProperty;
  function o(a) {
    if (!e(a)) return n(a);
    var s = t(a),
      u = [];
    for (var l in a) (l == "constructor" && (s || !i.call(a, l))) || u.push(l);
    return u;
  }
  return (_c = o), _c;
}
var wc, p1;
function Mr() {
  if (p1) return wc;
  p1 = 1;
  var e = Kk(),
    t = y4(),
    n = kn();
  function r(i) {
    return n(i) ? e(i, !0) : t(i);
  }
  return (wc = r), wc;
}
var xc, g1;
function _4() {
  if (g1) return xc;
  g1 = 1;
  var e = Qo(),
    t = Mr();
  function n(r, i) {
    return r && e(i, t(i), r);
  }
  return (xc = n), xc;
}
var no = { exports: {} };
no.exports;
var v1;
function Xk() {
  return (
    v1 ||
      ((v1 = 1),
      (function (e, t) {
        var n = jt(),
          r = t && !t.nodeType && t,
          i = r && !0 && e && !e.nodeType && e,
          o = i && i.exports === r,
          a = o ? n.Buffer : void 0,
          s = a ? a.allocUnsafe : void 0;
        function u(l, c) {
          if (c) return l.slice();
          var f = l.length,
            d = s ? s(f) : new l.constructor(f);
          return l.copy(d), d;
        }
        e.exports = u;
      })(no, no.exports)),
    no.exports
  );
}
var Sc, m1;
function Qk() {
  if (m1) return Sc;
  m1 = 1;
  function e(t, n) {
    var r = -1,
      i = t.length;
    for (n || (n = Array(i)); ++r < i; ) n[r] = t[r];
    return n;
  }
  return (Sc = e), Sc;
}
var Ec, y1;
function Zk() {
  if (y1) return Ec;
  y1 = 1;
  function e(t, n) {
    for (var r = -1, i = t == null ? 0 : t.length, o = 0, a = []; ++r < i; ) {
      var s = t[r];
      n(s, r, t) && (a[o++] = s);
    }
    return a;
  }
  return (Ec = e), Ec;
}
var bc, _1;
function Jk() {
  if (_1) return bc;
  _1 = 1;
  function e() {
    return [];
  }
  return (bc = e), bc;
}
var kc, w1;
function Mv() {
  if (w1) return kc;
  w1 = 1;
  var e = Zk(),
    t = Jk(),
    n = Object.prototype,
    r = n.propertyIsEnumerable,
    i = Object.getOwnPropertySymbols,
    o = i
      ? function (a) {
          return a == null
            ? []
            : ((a = Object(a)),
              e(i(a), function (s) {
                return r.call(a, s);
              }));
        }
      : t;
  return (kc = o), kc;
}
var Cc, x1;
function w4() {
  if (x1) return Cc;
  x1 = 1;
  var e = Qo(),
    t = Mv();
  function n(r, i) {
    return e(r, t(r), i);
  }
  return (Cc = n), Cc;
}
var Nc, S1;
function Pv() {
  if (S1) return Nc;
  S1 = 1;
  function e(t, n) {
    for (var r = -1, i = n.length, o = t.length; ++r < i; ) t[o + r] = n[r];
    return t;
  }
  return (Nc = e), Nc;
}
var Rc, E1;
function lu() {
  if (E1) return Rc;
  E1 = 1;
  var e = Yk(),
    t = e(Object.getPrototypeOf, Object);
  return (Rc = t), Rc;
}
var Tc, b1;
function e2() {
  if (b1) return Tc;
  b1 = 1;
  var e = Pv(),
    t = lu(),
    n = Mv(),
    r = Jk(),
    i = Object.getOwnPropertySymbols,
    o = i
      ? function (a) {
          for (var s = []; a; ) e(s, n(a)), (a = t(a));
          return s;
        }
      : r;
  return (Tc = o), Tc;
}
var Ic, k1;
function x4() {
  if (k1) return Ic;
  k1 = 1;
  var e = Qo(),
    t = e2();
  function n(r, i) {
    return e(r, t(r), i);
  }
  return (Ic = n), Ic;
}
var Ac, C1;
function t2() {
  if (C1) return Ac;
  C1 = 1;
  var e = Pv(),
    t = Ne();
  function n(r, i, o) {
    var a = i(r);
    return t(r) ? a : e(a, o(r));
  }
  return (Ac = n), Ac;
}
var Mc, N1;
function n2() {
  if (N1) return Mc;
  N1 = 1;
  var e = t2(),
    t = Mv(),
    n = or();
  function r(i) {
    return e(i, n, t);
  }
  return (Mc = r), Mc;
}
var Pc, R1;
function S4() {
  if (R1) return Pc;
  R1 = 1;
  var e = t2(),
    t = e2(),
    n = Mr();
  function r(i) {
    return e(i, n, t);
  }
  return (Pc = r), Pc;
}
var qc, T1;
function E4() {
  if (T1) return qc;
  T1 = 1;
  var e = Ar(),
    t = jt(),
    n = e(t, "DataView");
  return (qc = n), qc;
}
var Oc, I1;
function b4() {
  if (I1) return Oc;
  I1 = 1;
  var e = Ar(),
    t = jt(),
    n = e(t, "Promise");
  return (Oc = n), Oc;
}
var Lc, A1;
function r2() {
  if (A1) return Lc;
  A1 = 1;
  var e = Ar(),
    t = jt(),
    n = e(t, "Set");
  return (Lc = n), Lc;
}
var zc, M1;
function k4() {
  if (M1) return zc;
  M1 = 1;
  var e = Ar(),
    t = jt(),
    n = e(t, "WeakMap");
  return (zc = n), zc;
}
var $c, P1;
function Ni() {
  if (P1) return $c;
  P1 = 1;
  var e = E4(),
    t = Cv(),
    n = b4(),
    r = r2(),
    i = k4(),
    o = Ir(),
    a = Gk(),
    s = "[object Map]",
    u = "[object Object]",
    l = "[object Promise]",
    c = "[object Set]",
    f = "[object WeakMap]",
    d = "[object DataView]",
    h = a(e),
    m = a(t),
    v = a(n),
    w = a(r),
    p = a(i),
    g = o;
  return (
    ((e && g(new e(new ArrayBuffer(1))) != d) ||
      (t && g(new t()) != s) ||
      (n && g(n.resolve()) != l) ||
      (r && g(new r()) != c) ||
      (i && g(new i()) != f)) &&
      (g = function (y) {
        var _ = o(y),
          S = _ == u ? y.constructor : void 0,
          E = S ? a(S) : "";
        if (E)
          switch (E) {
            case h:
              return d;
            case m:
              return s;
            case v:
              return l;
            case w:
              return c;
            case p:
              return f;
          }
        return _;
      }),
    ($c = g),
    $c
  );
}
var Dc, q1;
function C4() {
  if (q1) return Dc;
  q1 = 1;
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
  return (Dc = n), Dc;
}
var Fc, O1;
function i2() {
  if (O1) return Fc;
  O1 = 1;
  var e = jt(),
    t = e.Uint8Array;
  return (Fc = t), Fc;
}
var jc, L1;
function qv() {
  if (L1) return jc;
  L1 = 1;
  var e = i2();
  function t(n) {
    var r = new n.constructor(n.byteLength);
    return new e(r).set(new e(n)), r;
  }
  return (jc = t), jc;
}
var Bc, z1;
function N4() {
  if (z1) return Bc;
  z1 = 1;
  var e = qv();
  function t(n, r) {
    var i = r ? e(n.buffer) : n.buffer;
    return new n.constructor(i, n.byteOffset, n.byteLength);
  }
  return (Bc = t), Bc;
}
var Hc, $1;
function R4() {
  if ($1) return Hc;
  $1 = 1;
  var e = /\w*$/;
  function t(n) {
    var r = new n.constructor(n.source, e.exec(n));
    return (r.lastIndex = n.lastIndex), r;
  }
  return (Hc = t), Hc;
}
var Vc, D1;
function T4() {
  if (D1) return Vc;
  D1 = 1;
  var e = ki(),
    t = e ? e.prototype : void 0,
    n = t ? t.valueOf : void 0;
  function r(i) {
    return n ? Object(n.call(i)) : {};
  }
  return (Vc = r), Vc;
}
var Uc, F1;
function o2() {
  if (F1) return Uc;
  F1 = 1;
  var e = qv();
  function t(n, r) {
    var i = r ? e(n.buffer) : n.buffer;
    return new n.constructor(i, n.byteOffset, n.length);
  }
  return (Uc = t), Uc;
}
var Gc, j1;
function I4() {
  if (j1) return Gc;
  j1 = 1;
  var e = qv(),
    t = N4(),
    n = R4(),
    r = T4(),
    i = o2(),
    o = "[object Boolean]",
    a = "[object Date]",
    s = "[object Map]",
    u = "[object Number]",
    l = "[object RegExp]",
    c = "[object Set]",
    f = "[object String]",
    d = "[object Symbol]",
    h = "[object ArrayBuffer]",
    m = "[object DataView]",
    v = "[object Float32Array]",
    w = "[object Float64Array]",
    p = "[object Int8Array]",
    g = "[object Int16Array]",
    y = "[object Int32Array]",
    _ = "[object Uint8Array]",
    S = "[object Uint8ClampedArray]",
    E = "[object Uint16Array]",
    k = "[object Uint32Array]";
  function C(T, I, M) {
    var z = T.constructor;
    switch (I) {
      case h:
        return e(T);
      case o:
      case a:
        return new z(+T);
      case m:
        return t(T, M);
      case v:
      case w:
      case p:
      case g:
      case y:
      case _:
      case S:
      case E:
      case k:
        return i(T, M);
      case s:
        return new z();
      case u:
      case f:
        return new z(T);
      case l:
        return n(T);
      case c:
        return new z();
      case d:
        return r(T);
    }
  }
  return (Gc = C), Gc;
}
var Wc, B1;
function a2() {
  if (B1) return Wc;
  B1 = 1;
  var e = Ct(),
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
  return (Wc = n), Wc;
}
var Kc, H1;
function s2() {
  if (H1) return Kc;
  H1 = 1;
  var e = a2(),
    t = lu(),
    n = uu();
  function r(i) {
    return typeof i.constructor == "function" && !n(i) ? e(t(i)) : {};
  }
  return (Kc = r), Kc;
}
var Yc, V1;
function A4() {
  if (V1) return Yc;
  V1 = 1;
  var e = Ni(),
    t = en(),
    n = "[object Map]";
  function r(i) {
    return t(i) && e(i) == n;
  }
  return (Yc = r), Yc;
}
var Xc, U1;
function M4() {
  if (U1) return Xc;
  U1 = 1;
  var e = A4(),
    t = su(),
    n = Iv(),
    r = n && n.isMap,
    i = r ? t(r) : e;
  return (Xc = i), Xc;
}
var Qc, G1;
function P4() {
  if (G1) return Qc;
  G1 = 1;
  var e = Ni(),
    t = en(),
    n = "[object Set]";
  function r(i) {
    return t(i) && e(i) == n;
  }
  return (Qc = r), Qc;
}
var Zc, W1;
function q4() {
  if (W1) return Zc;
  W1 = 1;
  var e = P4(),
    t = su(),
    n = Iv(),
    r = n && n.isSet,
    i = r ? t(r) : e;
  return (Zc = i), Zc;
}
var Jc, K1;
function u2() {
  if (K1) return Jc;
  K1 = 1;
  var e = ru(),
    t = Rv(),
    n = ou(),
    r = v4(),
    i = _4(),
    o = Xk(),
    a = Qk(),
    s = w4(),
    u = x4(),
    l = n2(),
    c = S4(),
    f = Ni(),
    d = C4(),
    h = I4(),
    m = s2(),
    v = Ne(),
    w = Ci(),
    p = M4(),
    g = Ct(),
    y = q4(),
    _ = or(),
    S = Mr(),
    E = 1,
    k = 2,
    C = 4,
    T = "[object Arguments]",
    I = "[object Array]",
    M = "[object Boolean]",
    z = "[object Date]",
    F = "[object Error]",
    x = "[object Function]",
    P = "[object GeneratorFunction]",
    N = "[object Map]",
    $ = "[object Number]",
    R = "[object Object]",
    b = "[object RegExp]",
    A = "[object Set]",
    L = "[object String]",
    D = "[object Symbol]",
    H = "[object WeakMap]",
    B = "[object ArrayBuffer]",
    G = "[object DataView]",
    X = "[object Float32Array]",
    J = "[object Float64Array]",
    se = "[object Int8Array]",
    oe = "[object Int16Array]",
    ie = "[object Int32Array]",
    Re = "[object Uint8Array]",
    Ee = "[object Uint8ClampedArray]",
    $e = "[object Uint16Array]",
    Me = "[object Uint32Array]",
    Q = {};
  (Q[T] = Q[I] = Q[B] = Q[G] = Q[M] = Q[z] = Q[X] = Q[J] = Q[se] = Q[oe] = Q[ie] = Q[N] = Q[$] = Q[
    R
  ] = Q[b] = Q[A] = Q[L] = Q[D] = Q[Re] = Q[Ee] = Q[$e] = Q[Me] = !0),
    (Q[F] = Q[x] = Q[H] = !1);
  function Pe(K, U, we, Rt, Ht, Ke) {
    var be,
      et = U & E,
      Tt = U & k,
      tn = U & C;
    if ((we && (be = Ht ? we(K, Rt, Ht, Ke) : we(K)), be !== void 0)) return be;
    if (!g(K)) return K;
    var Vt = v(K);
    if (Vt) {
      if (((be = d(K)), !et)) return a(K, be);
    } else {
      var lt = f(K),
        nn = lt == x || lt == P;
      if (w(K)) return o(K, et);
      if (lt == R || lt == T || (nn && !Ht)) {
        if (((be = Tt || nn ? {} : m(K)), !et)) return Tt ? u(K, i(be, K)) : s(K, r(be, K));
      } else {
        if (!Q[lt]) return Ht ? K : {};
        be = h(K, lt, et);
      }
    }
    Ke || (Ke = new e());
    var Nn = Ke.get(K);
    if (Nn) return Nn;
    Ke.set(K, be),
      y(K)
        ? K.forEach(function (He) {
            be.add(Pe(He, U, we, He, K, Ke));
          })
        : p(K) &&
          K.forEach(function (He, Ye) {
            be.set(Ye, Pe(He, U, we, Ye, K, Ke));
          });
    var qe = tn ? (Tt ? c : l) : Tt ? S : _,
      tt = Vt ? void 0 : qe(K);
    return (
      t(tt || K, function (He, Ye) {
        tt && ((Ye = He), (He = K[Ye])), n(be, Ye, Pe(He, U, we, Ye, K, Ke));
      }),
      be
    );
  }
  return (Jc = Pe), Jc;
}
var ef, Y1;
function O4() {
  if (Y1) return ef;
  Y1 = 1;
  var e = u2(),
    t = 4;
  function n(r) {
    return e(r, t);
  }
  return (ef = n), ef;
}
var tf, X1;
function Ov() {
  if (X1) return tf;
  X1 = 1;
  function e(t) {
    return function () {
      return t;
    };
  }
  return (tf = e), tf;
}
var nf, Q1;
function L4() {
  if (Q1) return nf;
  Q1 = 1;
  function e(t) {
    return function (n, r, i) {
      for (var o = -1, a = Object(n), s = i(n), u = s.length; u--; ) {
        var l = s[t ? u : ++o];
        if (r(a[l], l, a) === !1) break;
      }
      return n;
    };
  }
  return (nf = e), nf;
}
var rf, Z1;
function Lv() {
  if (Z1) return rf;
  Z1 = 1;
  var e = L4(),
    t = e();
  return (rf = t), rf;
}
var of, J1;
function zv() {
  if (J1) return of;
  J1 = 1;
  var e = Lv(),
    t = or();
  function n(r, i) {
    return r && e(r, i, t);
  }
  return (of = n), of;
}
var af, e_;
function z4() {
  if (e_) return af;
  e_ = 1;
  var e = kn();
  function t(n, r) {
    return function (i, o) {
      if (i == null) return i;
      if (!e(i)) return n(i, o);
      for (
        var a = i.length, s = r ? a : -1, u = Object(i);
        (r ? s-- : ++s < a) && o(u[s], s, u) !== !1;

      );
      return i;
    };
  }
  return (af = t), af;
}
var sf, t_;
function cu() {
  if (t_) return sf;
  t_ = 1;
  var e = zv(),
    t = z4(),
    n = t(e);
  return (sf = n), sf;
}
var uf, n_;
function Pr() {
  if (n_) return uf;
  n_ = 1;
  function e(t) {
    return t;
  }
  return (uf = e), uf;
}
var lf, r_;
function l2() {
  if (r_) return lf;
  r_ = 1;
  var e = Pr();
  function t(n) {
    return typeof n == "function" ? n : e;
  }
  return (lf = t), lf;
}
var cf, i_;
function c2() {
  if (i_) return cf;
  i_ = 1;
  var e = Rv(),
    t = cu(),
    n = l2(),
    r = Ne();
  function i(o, a) {
    var s = r(o) ? e : t;
    return s(o, n(a));
  }
  return (cf = i), cf;
}
var ff, o_;
function f2() {
  return o_ || ((o_ = 1), (ff = c2())), ff;
}
var df, a_;
function $4() {
  if (a_) return df;
  a_ = 1;
  var e = cu();
  function t(n, r) {
    var i = [];
    return (
      e(n, function (o, a, s) {
        r(o, a, s) && i.push(o);
      }),
      i
    );
  }
  return (df = t), df;
}
var hf, s_;
function D4() {
  if (s_) return hf;
  s_ = 1;
  var e = "__lodash_hash_undefined__";
  function t(n) {
    return this.__data__.set(n, e), this;
  }
  return (hf = t), hf;
}
var pf, u_;
function F4() {
  if (u_) return pf;
  u_ = 1;
  function e(t) {
    return this.__data__.has(t);
  }
  return (pf = e), pf;
}
var gf, l_;
function d2() {
  if (l_) return gf;
  l_ = 1;
  var e = Nv(),
    t = D4(),
    n = F4();
  function r(i) {
    var o = -1,
      a = i == null ? 0 : i.length;
    for (this.__data__ = new e(); ++o < a; ) this.add(i[o]);
  }
  return (r.prototype.add = r.prototype.push = t), (r.prototype.has = n), (gf = r), gf;
}
var vf, c_;
function j4() {
  if (c_) return vf;
  c_ = 1;
  function e(t, n) {
    for (var r = -1, i = t == null ? 0 : t.length; ++r < i; ) if (n(t[r], r, t)) return !0;
    return !1;
  }
  return (vf = e), vf;
}
var mf, f_;
function h2() {
  if (f_) return mf;
  f_ = 1;
  function e(t, n) {
    return t.has(n);
  }
  return (mf = e), mf;
}
var yf, d_;
function p2() {
  if (d_) return yf;
  d_ = 1;
  var e = d2(),
    t = j4(),
    n = h2(),
    r = 1,
    i = 2;
  function o(a, s, u, l, c, f) {
    var d = u & r,
      h = a.length,
      m = s.length;
    if (h != m && !(d && m > h)) return !1;
    var v = f.get(a),
      w = f.get(s);
    if (v && w) return v == s && w == a;
    var p = -1,
      g = !0,
      y = u & i ? new e() : void 0;
    for (f.set(a, s), f.set(s, a); ++p < h; ) {
      var _ = a[p],
        S = s[p];
      if (l) var E = d ? l(S, _, p, s, a, f) : l(_, S, p, a, s, f);
      if (E !== void 0) {
        if (E) continue;
        g = !1;
        break;
      }
      if (y) {
        if (
          !t(s, function (k, C) {
            if (!n(y, C) && (_ === k || c(_, k, u, l, f))) return y.push(C);
          })
        ) {
          g = !1;
          break;
        }
      } else if (!(_ === S || c(_, S, u, l, f))) {
        g = !1;
        break;
      }
    }
    return f.delete(a), f.delete(s), g;
  }
  return (yf = o), yf;
}
var _f, h_;
function B4() {
  if (h_) return _f;
  h_ = 1;
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
  return (_f = e), _f;
}
var wf, p_;
function $v() {
  if (p_) return wf;
  p_ = 1;
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
  return (wf = e), wf;
}
var xf, g_;
function H4() {
  if (g_) return xf;
  g_ = 1;
  var e = ki(),
    t = i2(),
    n = bi(),
    r = p2(),
    i = B4(),
    o = $v(),
    a = 1,
    s = 2,
    u = "[object Boolean]",
    l = "[object Date]",
    c = "[object Error]",
    f = "[object Map]",
    d = "[object Number]",
    h = "[object RegExp]",
    m = "[object Set]",
    v = "[object String]",
    w = "[object Symbol]",
    p = "[object ArrayBuffer]",
    g = "[object DataView]",
    y = e ? e.prototype : void 0,
    _ = y ? y.valueOf : void 0;
  function S(E, k, C, T, I, M, z) {
    switch (C) {
      case g:
        if (E.byteLength != k.byteLength || E.byteOffset != k.byteOffset) return !1;
        (E = E.buffer), (k = k.buffer);
      case p:
        return !(E.byteLength != k.byteLength || !M(new t(E), new t(k)));
      case u:
      case l:
      case d:
        return n(+E, +k);
      case c:
        return E.name == k.name && E.message == k.message;
      case h:
      case v:
        return E == k + "";
      case f:
        var F = i;
      case m:
        var x = T & a;
        if ((F || (F = o), E.size != k.size && !x)) return !1;
        var P = z.get(E);
        if (P) return P == k;
        (T |= s), z.set(E, k);
        var N = r(F(E), F(k), T, I, M, z);
        return z.delete(E), N;
      case w:
        if (_) return _.call(E) == _.call(k);
    }
    return !1;
  }
  return (xf = S), xf;
}
var Sf, v_;
function V4() {
  if (v_) return Sf;
  v_ = 1;
  var e = n2(),
    t = 1,
    n = Object.prototype,
    r = n.hasOwnProperty;
  function i(o, a, s, u, l, c) {
    var f = s & t,
      d = e(o),
      h = d.length,
      m = e(a),
      v = m.length;
    if (h != v && !f) return !1;
    for (var w = h; w--; ) {
      var p = d[w];
      if (!(f ? p in a : r.call(a, p))) return !1;
    }
    var g = c.get(o),
      y = c.get(a);
    if (g && y) return g == a && y == o;
    var _ = !0;
    c.set(o, a), c.set(a, o);
    for (var S = f; ++w < h; ) {
      p = d[w];
      var E = o[p],
        k = a[p];
      if (u) var C = f ? u(k, E, p, a, o, c) : u(E, k, p, o, a, c);
      if (!(C === void 0 ? E === k || l(E, k, s, u, c) : C)) {
        _ = !1;
        break;
      }
      S || (S = p == "constructor");
    }
    if (_ && !S) {
      var T = o.constructor,
        I = a.constructor;
      T != I &&
        "constructor" in o &&
        "constructor" in a &&
        !(typeof T == "function" && T instanceof T && typeof I == "function" && I instanceof I) &&
        (_ = !1);
    }
    return c.delete(o), c.delete(a), _;
  }
  return (Sf = i), Sf;
}
var Ef, m_;
function U4() {
  if (m_) return Ef;
  m_ = 1;
  var e = ru(),
    t = p2(),
    n = H4(),
    r = V4(),
    i = Ni(),
    o = Ne(),
    a = Ci(),
    s = Jo(),
    u = 1,
    l = "[object Arguments]",
    c = "[object Array]",
    f = "[object Object]",
    d = Object.prototype,
    h = d.hasOwnProperty;
  function m(v, w, p, g, y, _) {
    var S = o(v),
      E = o(w),
      k = S ? c : i(v),
      C = E ? c : i(w);
    (k = k == l ? f : k), (C = C == l ? f : C);
    var T = k == f,
      I = C == f,
      M = k == C;
    if (M && a(v)) {
      if (!a(w)) return !1;
      (S = !0), (T = !1);
    }
    if (M && !T)
      return _ || (_ = new e()), S || s(v) ? t(v, w, p, g, y, _) : n(v, w, k, p, g, y, _);
    if (!(p & u)) {
      var z = T && h.call(v, "__wrapped__"),
        F = I && h.call(w, "__wrapped__");
      if (z || F) {
        var x = z ? v.value() : v,
          P = F ? w.value() : w;
        return _ || (_ = new e()), y(x, P, p, g, _);
      }
    }
    return M ? (_ || (_ = new e()), r(v, w, p, g, y, _)) : !1;
  }
  return (Ef = m), Ef;
}
var bf, y_;
function g2() {
  if (y_) return bf;
  y_ = 1;
  var e = U4(),
    t = en();
  function n(r, i, o, a, s) {
    return r === i
      ? !0
      : r == null || i == null || (!t(r) && !t(i))
      ? r !== r && i !== i
      : e(r, i, o, a, n, s);
  }
  return (bf = n), bf;
}
var kf, __;
function G4() {
  if (__) return kf;
  __ = 1;
  var e = ru(),
    t = g2(),
    n = 1,
    r = 2;
  function i(o, a, s, u) {
    var l = s.length,
      c = l,
      f = !u;
    if (o == null) return !c;
    for (o = Object(o); l--; ) {
      var d = s[l];
      if (f && d[2] ? d[1] !== o[d[0]] : !(d[0] in o)) return !1;
    }
    for (; ++l < c; ) {
      d = s[l];
      var h = d[0],
        m = o[h],
        v = d[1];
      if (f && d[2]) {
        if (m === void 0 && !(h in o)) return !1;
      } else {
        var w = new e();
        if (u) var p = u(m, v, h, o, a, w);
        if (!(p === void 0 ? t(v, m, n | r, u, w) : p)) return !1;
      }
    }
    return !0;
  }
  return (kf = i), kf;
}
var Cf, w_;
function v2() {
  if (w_) return Cf;
  w_ = 1;
  var e = Ct();
  function t(n) {
    return n === n && !e(n);
  }
  return (Cf = t), Cf;
}
var Nf, x_;
function W4() {
  if (x_) return Nf;
  x_ = 1;
  var e = v2(),
    t = or();
  function n(r) {
    for (var i = t(r), o = i.length; o--; ) {
      var a = i[o],
        s = r[a];
      i[o] = [a, s, e(s)];
    }
    return i;
  }
  return (Nf = n), Nf;
}
var Rf, S_;
function m2() {
  if (S_) return Rf;
  S_ = 1;
  function e(t, n) {
    return function (r) {
      return r == null ? !1 : r[t] === n && (n !== void 0 || t in Object(r));
    };
  }
  return (Rf = e), Rf;
}
var Tf, E_;
function K4() {
  if (E_) return Tf;
  E_ = 1;
  var e = G4(),
    t = W4(),
    n = m2();
  function r(i) {
    var o = t(i);
    return o.length == 1 && o[0][2]
      ? n(o[0][0], o[0][1])
      : function (a) {
          return a === i || e(a, i, o);
        };
  }
  return (Tf = r), Tf;
}
var If, b_;
function Ri() {
  if (b_) return If;
  b_ = 1;
  var e = Ir(),
    t = en(),
    n = "[object Symbol]";
  function r(i) {
    return typeof i == "symbol" || (t(i) && e(i) == n);
  }
  return (If = r), If;
}
var Af, k_;
function Dv() {
  if (k_) return Af;
  k_ = 1;
  var e = Ne(),
    t = Ri(),
    n = /\.|\[(?:[^[\]]*|(["'])(?:(?!\1)[^\\]|\\.)*?\1)\]/,
    r = /^\w*$/;
  function i(o, a) {
    if (e(o)) return !1;
    var s = typeof o;
    return s == "number" || s == "symbol" || s == "boolean" || o == null || t(o)
      ? !0
      : r.test(o) || !n.test(o) || (a != null && o in Object(a));
  }
  return (Af = i), Af;
}
var Mf, C_;
function Y4() {
  if (C_) return Mf;
  C_ = 1;
  var e = Nv(),
    t = "Expected a function";
  function n(r, i) {
    if (typeof r != "function" || (i != null && typeof i != "function")) throw new TypeError(t);
    var o = function () {
      var a = arguments,
        s = i ? i.apply(this, a) : a[0],
        u = o.cache;
      if (u.has(s)) return u.get(s);
      var l = r.apply(this, a);
      return (o.cache = u.set(s, l) || u), l;
    };
    return (o.cache = new (n.Cache || e)()), o;
  }
  return (n.Cache = e), (Mf = n), Mf;
}
var Pf, N_;
function X4() {
  if (N_) return Pf;
  N_ = 1;
  var e = Y4(),
    t = 500;
  function n(r) {
    var i = e(r, function (a) {
        return o.size === t && o.clear(), a;
      }),
      o = i.cache;
    return i;
  }
  return (Pf = n), Pf;
}
var qf, R_;
function Q4() {
  if (R_) return qf;
  R_ = 1;
  var e = X4(),
    t = /[^.[\]]+|\[(?:(-?\d+(?:\.\d+)?)|(["'])((?:(?!\2)[^\\]|\\.)*?)\2)\]|(?=(?:\.|\[\])(?:\.|\[\]|$))/g,
    n = /\\(\\)?/g,
    r = e(function (i) {
      var o = [];
      return (
        i.charCodeAt(0) === 46 && o.push(""),
        i.replace(t, function (a, s, u, l) {
          o.push(u ? l.replace(n, "$1") : s || a);
        }),
        o
      );
    });
  return (qf = r), qf;
}
var Of, T_;
function fu() {
  if (T_) return Of;
  T_ = 1;
  function e(t, n) {
    for (var r = -1, i = t == null ? 0 : t.length, o = Array(i); ++r < i; ) o[r] = n(t[r], r, t);
    return o;
  }
  return (Of = e), Of;
}
var Lf, I_;
function Z4() {
  if (I_) return Lf;
  I_ = 1;
  var e = ki(),
    t = fu(),
    n = Ne(),
    r = Ri(),
    i = e ? e.prototype : void 0,
    o = i ? i.toString : void 0;
  function a(s) {
    if (typeof s == "string") return s;
    if (n(s)) return t(s, a) + "";
    if (r(s)) return o ? o.call(s) : "";
    var u = s + "";
    return u == "0" && 1 / s == -1 / 0 ? "-0" : u;
  }
  return (Lf = a), Lf;
}
var zf, A_;
function y2() {
  if (A_) return zf;
  A_ = 1;
  var e = Z4();
  function t(n) {
    return n == null ? "" : e(n);
  }
  return (zf = t), zf;
}
var $f, M_;
function du() {
  if (M_) return $f;
  M_ = 1;
  var e = Ne(),
    t = Dv(),
    n = Q4(),
    r = y2();
  function i(o, a) {
    return e(o) ? o : t(o, a) ? [o] : n(r(o));
  }
  return ($f = i), $f;
}
var Df, P_;
function ea() {
  if (P_) return Df;
  P_ = 1;
  var e = Ri();
  function t(n) {
    if (typeof n == "string" || e(n)) return n;
    var r = n + "";
    return r == "0" && 1 / n == -1 / 0 ? "-0" : r;
  }
  return (Df = t), Df;
}
var Ff, q_;
function hu() {
  if (q_) return Ff;
  q_ = 1;
  var e = du(),
    t = ea();
  function n(r, i) {
    i = e(i, r);
    for (var o = 0, a = i.length; r != null && o < a; ) r = r[t(i[o++])];
    return o && o == a ? r : void 0;
  }
  return (Ff = n), Ff;
}
var jf, O_;
function J4() {
  if (O_) return jf;
  O_ = 1;
  var e = hu();
  function t(n, r, i) {
    var o = n == null ? void 0 : e(n, r);
    return o === void 0 ? i : o;
  }
  return (jf = t), jf;
}
var Bf, L_;
function eO() {
  if (L_) return Bf;
  L_ = 1;
  function e(t, n) {
    return t != null && n in Object(t);
  }
  return (Bf = e), Bf;
}
var Hf, z_;
function _2() {
  if (z_) return Hf;
  z_ = 1;
  var e = du(),
    t = Zo(),
    n = Ne(),
    r = au(),
    i = Tv(),
    o = ea();
  function a(s, u, l) {
    u = e(u, s);
    for (var c = -1, f = u.length, d = !1; ++c < f; ) {
      var h = o(u[c]);
      if (!(d = s != null && l(s, h))) break;
      s = s[h];
    }
    return d || ++c != f
      ? d
      : ((f = s == null ? 0 : s.length), !!f && i(f) && r(h, f) && (n(s) || t(s)));
  }
  return (Hf = a), Hf;
}
var Vf, $_;
function w2() {
  if ($_) return Vf;
  $_ = 1;
  var e = eO(),
    t = _2();
  function n(r, i) {
    return r != null && t(r, i, e);
  }
  return (Vf = n), Vf;
}
var Uf, D_;
function tO() {
  if (D_) return Uf;
  D_ = 1;
  var e = g2(),
    t = J4(),
    n = w2(),
    r = Dv(),
    i = v2(),
    o = m2(),
    a = ea(),
    s = 1,
    u = 2;
  function l(c, f) {
    return r(c) && i(f)
      ? o(a(c), f)
      : function (d) {
          var h = t(d, c);
          return h === void 0 && h === f ? n(d, c) : e(f, h, s | u);
        };
  }
  return (Uf = l), Uf;
}
var Gf, F_;
function x2() {
  if (F_) return Gf;
  F_ = 1;
  function e(t) {
    return function (n) {
      return n == null ? void 0 : n[t];
    };
  }
  return (Gf = e), Gf;
}
var Wf, j_;
function nO() {
  if (j_) return Wf;
  j_ = 1;
  var e = hu();
  function t(n) {
    return function (r) {
      return e(r, n);
    };
  }
  return (Wf = t), Wf;
}
var Kf, B_;
function rO() {
  if (B_) return Kf;
  B_ = 1;
  var e = x2(),
    t = nO(),
    n = Dv(),
    r = ea();
  function i(o) {
    return n(o) ? e(r(o)) : t(o);
  }
  return (Kf = i), Kf;
}
var Yf, H_;
function Cn() {
  if (H_) return Yf;
  H_ = 1;
  var e = K4(),
    t = tO(),
    n = Pr(),
    r = Ne(),
    i = rO();
  function o(a) {
    return typeof a == "function"
      ? a
      : a == null
      ? n
      : typeof a == "object"
      ? r(a)
        ? t(a[0], a[1])
        : e(a)
      : i(a);
  }
  return (Yf = o), Yf;
}
var Xf, V_;
function S2() {
  if (V_) return Xf;
  V_ = 1;
  var e = Zk(),
    t = $4(),
    n = Cn(),
    r = Ne();
  function i(o, a) {
    var s = r(o) ? e : t;
    return s(o, n(a, 3));
  }
  return (Xf = i), Xf;
}
var Qf, U_;
function iO() {
  if (U_) return Qf;
  U_ = 1;
  var e = Object.prototype,
    t = e.hasOwnProperty;
  function n(r, i) {
    return r != null && t.call(r, i);
  }
  return (Qf = n), Qf;
}
var Zf, G_;
function E2() {
  if (G_) return Zf;
  G_ = 1;
  var e = iO(),
    t = _2();
  function n(r, i) {
    return r != null && t(r, i, e);
  }
  return (Zf = n), Zf;
}
var Jf, W_;
function oO() {
  if (W_) return Jf;
  W_ = 1;
  var e = Av(),
    t = Ni(),
    n = Zo(),
    r = Ne(),
    i = kn(),
    o = Ci(),
    a = uu(),
    s = Jo(),
    u = "[object Map]",
    l = "[object Set]",
    c = Object.prototype,
    f = c.hasOwnProperty;
  function d(h) {
    if (h == null) return !0;
    if (
      i(h) &&
      (r(h) || typeof h == "string" || typeof h.splice == "function" || o(h) || s(h) || n(h))
    )
      return !h.length;
    var m = t(h);
    if (m == u || m == l) return !h.size;
    if (a(h)) return !e(h).length;
    for (var v in h) if (f.call(h, v)) return !1;
    return !0;
  }
  return (Jf = d), Jf;
}
var ed, K_;
function b2() {
  if (K_) return ed;
  K_ = 1;
  function e(t) {
    return t === void 0;
  }
  return (ed = e), ed;
}
var td, Y_;
function k2() {
  if (Y_) return td;
  Y_ = 1;
  var e = cu(),
    t = kn();
  function n(r, i) {
    var o = -1,
      a = t(r) ? Array(r.length) : [];
    return (
      e(r, function (s, u, l) {
        a[++o] = i(s, u, l);
      }),
      a
    );
  }
  return (td = n), td;
}
var nd, X_;
function C2() {
  if (X_) return nd;
  X_ = 1;
  var e = fu(),
    t = Cn(),
    n = k2(),
    r = Ne();
  function i(o, a) {
    var s = r(o) ? e : n;
    return s(o, t(a, 3));
  }
  return (nd = i), nd;
}
var rd, Q_;
function aO() {
  if (Q_) return rd;
  Q_ = 1;
  function e(t, n, r, i) {
    var o = -1,
      a = t == null ? 0 : t.length;
    for (i && a && (r = t[++o]); ++o < a; ) r = n(r, t[o], o, t);
    return r;
  }
  return (rd = e), rd;
}
var id, Z_;
function sO() {
  if (Z_) return id;
  Z_ = 1;
  function e(t, n, r, i, o) {
    return (
      o(t, function (a, s, u) {
        r = i ? ((i = !1), a) : n(r, a, s, u);
      }),
      r
    );
  }
  return (id = e), id;
}
var od, J_;
function N2() {
  if (J_) return od;
  J_ = 1;
  var e = aO(),
    t = cu(),
    n = Cn(),
    r = sO(),
    i = Ne();
  function o(a, s, u) {
    var l = i(a) ? e : r,
      c = arguments.length < 3;
    return l(a, n(s, 4), u, c, t);
  }
  return (od = o), od;
}
var ad, ew;
function uO() {
  if (ew) return ad;
  ew = 1;
  var e = Ir(),
    t = Ne(),
    n = en(),
    r = "[object String]";
  function i(o) {
    return typeof o == "string" || (!t(o) && n(o) && e(o) == r);
  }
  return (ad = i), ad;
}
var sd, tw;
function lO() {
  if (tw) return sd;
  tw = 1;
  var e = x2(),
    t = e("length");
  return (sd = t), sd;
}
var ud, nw;
function cO() {
  if (nw) return ud;
  nw = 1;
  var e = "\\ud800-\\udfff",
    t = "\\u0300-\\u036f",
    n = "\\ufe20-\\ufe2f",
    r = "\\u20d0-\\u20ff",
    i = t + n + r,
    o = "\\ufe0e\\ufe0f",
    a = "\\u200d",
    s = RegExp("[" + a + e + i + o + "]");
  function u(l) {
    return s.test(l);
  }
  return (ud = u), ud;
}
var ld, rw;
function fO() {
  if (rw) return ld;
  rw = 1;
  var e = "\\ud800-\\udfff",
    t = "\\u0300-\\u036f",
    n = "\\ufe20-\\ufe2f",
    r = "\\u20d0-\\u20ff",
    i = t + n + r,
    o = "\\ufe0e\\ufe0f",
    a = "[" + e + "]",
    s = "[" + i + "]",
    u = "\\ud83c[\\udffb-\\udfff]",
    l = "(?:" + s + "|" + u + ")",
    c = "[^" + e + "]",
    f = "(?:\\ud83c[\\udde6-\\uddff]){2}",
    d = "[\\ud800-\\udbff][\\udc00-\\udfff]",
    h = "\\u200d",
    m = l + "?",
    v = "[" + o + "]?",
    w = "(?:" + h + "(?:" + [c, f, d].join("|") + ")" + v + m + ")*",
    p = v + m + w,
    g = "(?:" + [c + s + "?", s, f, d, a].join("|") + ")",
    y = RegExp(u + "(?=" + u + ")|" + g + p, "g");
  function _(S) {
    for (var E = (y.lastIndex = 0); y.test(S); ) ++E;
    return E;
  }
  return (ld = _), ld;
}
var cd, iw;
function dO() {
  if (iw) return cd;
  iw = 1;
  var e = lO(),
    t = cO(),
    n = fO();
  function r(i) {
    return t(i) ? n(i) : e(i);
  }
  return (cd = r), cd;
}
var fd, ow;
function hO() {
  if (ow) return fd;
  ow = 1;
  var e = Av(),
    t = Ni(),
    n = kn(),
    r = uO(),
    i = dO(),
    o = "[object Map]",
    a = "[object Set]";
  function s(u) {
    if (u == null) return 0;
    if (n(u)) return r(u) ? i(u) : u.length;
    var l = t(u);
    return l == o || l == a ? u.size : e(u).length;
  }
  return (fd = s), fd;
}
var dd, aw;
function pO() {
  if (aw) return dd;
  aw = 1;
  var e = Rv(),
    t = a2(),
    n = zv(),
    r = Cn(),
    i = lu(),
    o = Ne(),
    a = Ci(),
    s = Xo(),
    u = Ct(),
    l = Jo();
  function c(f, d, h) {
    var m = o(f),
      v = m || a(f) || l(f);
    if (((d = r(d, 4)), h == null)) {
      var w = f && f.constructor;
      v ? (h = m ? new w() : []) : u(f) ? (h = s(w) ? t(i(f)) : {}) : (h = {});
    }
    return (
      (v ? e : n)(f, function (p, g, y) {
        return d(h, p, g, y);
      }),
      h
    );
  }
  return (dd = c), dd;
}
var hd, sw;
function gO() {
  if (sw) return hd;
  sw = 1;
  var e = ki(),
    t = Zo(),
    n = Ne(),
    r = e ? e.isConcatSpreadable : void 0;
  function i(o) {
    return n(o) || t(o) || !!(r && o && o[r]);
  }
  return (hd = i), hd;
}
var pd, uw;
function Fv() {
  if (uw) return pd;
  uw = 1;
  var e = Pv(),
    t = gO();
  function n(r, i, o, a, s) {
    var u = -1,
      l = r.length;
    for (o || (o = t), s || (s = []); ++u < l; ) {
      var c = r[u];
      i > 0 && o(c) ? (i > 1 ? n(c, i - 1, o, a, s) : e(s, c)) : a || (s[s.length] = c);
    }
    return s;
  }
  return (pd = n), pd;
}
var gd, lw;
function vO() {
  if (lw) return gd;
  lw = 1;
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
  return (gd = e), gd;
}
var vd, cw;
function R2() {
  if (cw) return vd;
  cw = 1;
  var e = vO(),
    t = Math.max;
  function n(r, i, o) {
    return (
      (i = t(i === void 0 ? r.length - 1 : i, 0)),
      function () {
        for (var a = arguments, s = -1, u = t(a.length - i, 0), l = Array(u); ++s < u; )
          l[s] = a[i + s];
        s = -1;
        for (var c = Array(i + 1); ++s < i; ) c[s] = a[s];
        return (c[i] = o(l)), e(r, this, c);
      }
    );
  }
  return (vd = n), vd;
}
var md, fw;
function mO() {
  if (fw) return md;
  fw = 1;
  var e = Ov(),
    t = Wk(),
    n = Pr(),
    r = t
      ? function (i, o) {
          return t(i, "toString", { configurable: !0, enumerable: !1, value: e(o), writable: !0 });
        }
      : n;
  return (md = r), md;
}
var yd, dw;
function yO() {
  if (dw) return yd;
  dw = 1;
  var e = 800,
    t = 16,
    n = Date.now;
  function r(i) {
    var o = 0,
      a = 0;
    return function () {
      var s = n(),
        u = t - (s - a);
      if (((a = s), u > 0)) {
        if (++o >= e) return arguments[0];
      } else o = 0;
      return i.apply(void 0, arguments);
    };
  }
  return (yd = r), yd;
}
var _d, hw;
function T2() {
  if (hw) return _d;
  hw = 1;
  var e = mO(),
    t = yO(),
    n = t(e);
  return (_d = n), _d;
}
var wd, pw;
function pu() {
  if (pw) return wd;
  pw = 1;
  var e = Pr(),
    t = R2(),
    n = T2();
  function r(i, o) {
    return n(t(i, o, e), i + "");
  }
  return (wd = r), wd;
}
var xd, gw;
function I2() {
  if (gw) return xd;
  gw = 1;
  function e(t, n, r, i) {
    for (var o = t.length, a = r + (i ? 1 : -1); i ? a-- : ++a < o; ) if (n(t[a], a, t)) return a;
    return -1;
  }
  return (xd = e), xd;
}
var Sd, vw;
function _O() {
  if (vw) return Sd;
  vw = 1;
  function e(t) {
    return t !== t;
  }
  return (Sd = e), Sd;
}
var Ed, mw;
function wO() {
  if (mw) return Ed;
  mw = 1;
  function e(t, n, r) {
    for (var i = r - 1, o = t.length; ++i < o; ) if (t[i] === n) return i;
    return -1;
  }
  return (Ed = e), Ed;
}
var bd, yw;
function xO() {
  if (yw) return bd;
  yw = 1;
  var e = I2(),
    t = _O(),
    n = wO();
  function r(i, o, a) {
    return o === o ? n(i, o, a) : e(i, t, a);
  }
  return (bd = r), bd;
}
var kd, _w;
function SO() {
  if (_w) return kd;
  _w = 1;
  var e = xO();
  function t(n, r) {
    var i = n == null ? 0 : n.length;
    return !!i && e(n, r, 0) > -1;
  }
  return (kd = t), kd;
}
var Cd, ww;
function EO() {
  if (ww) return Cd;
  ww = 1;
  function e(t, n, r) {
    for (var i = -1, o = t == null ? 0 : t.length; ++i < o; ) if (r(n, t[i])) return !0;
    return !1;
  }
  return (Cd = e), Cd;
}
var Nd, xw;
function bO() {
  if (xw) return Nd;
  xw = 1;
  function e() {}
  return (Nd = e), Nd;
}
var Rd, Sw;
function kO() {
  if (Sw) return Rd;
  Sw = 1;
  var e = r2(),
    t = bO(),
    n = $v(),
    r = 1 / 0,
    i =
      e && 1 / n(new e([, -0]))[1] == r
        ? function (o) {
            return new e(o);
          }
        : t;
  return (Rd = i), Rd;
}
var Td, Ew;
function CO() {
  if (Ew) return Td;
  Ew = 1;
  var e = d2(),
    t = SO(),
    n = EO(),
    r = h2(),
    i = kO(),
    o = $v(),
    a = 200;
  function s(u, l, c) {
    var f = -1,
      d = t,
      h = u.length,
      m = !0,
      v = [],
      w = v;
    if (c) (m = !1), (d = n);
    else if (h >= a) {
      var p = l ? null : i(u);
      if (p) return o(p);
      (m = !1), (d = r), (w = new e());
    } else w = l ? [] : v;
    e: for (; ++f < h; ) {
      var g = u[f],
        y = l ? l(g) : g;
      if (((g = c || g !== 0 ? g : 0), m && y === y)) {
        for (var _ = w.length; _--; ) if (w[_] === y) continue e;
        l && w.push(y), v.push(g);
      } else d(w, y, c) || (w !== v && w.push(y), v.push(g));
    }
    return v;
  }
  return (Td = s), Td;
}
var Id, bw;
function A2() {
  if (bw) return Id;
  bw = 1;
  var e = kn(),
    t = en();
  function n(r) {
    return t(r) && e(r);
  }
  return (Id = n), Id;
}
var Ad, kw;
function NO() {
  if (kw) return Ad;
  kw = 1;
  var e = Fv(),
    t = pu(),
    n = CO(),
    r = A2(),
    i = t(function (o) {
      return n(e(o, 1, r, !0));
    });
  return (Ad = i), Ad;
}
var Md, Cw;
function RO() {
  if (Cw) return Md;
  Cw = 1;
  var e = fu();
  function t(n, r) {
    return e(r, function (i) {
      return n[i];
    });
  }
  return (Md = t), Md;
}
var Pd, Nw;
function M2() {
  if (Nw) return Pd;
  Nw = 1;
  var e = RO(),
    t = or();
  function n(r) {
    return r == null ? [] : e(r, t(r));
  }
  return (Pd = n), Pd;
}
var qd, Rw;
function Nt() {
  if (Rw) return qd;
  Rw = 1;
  var e;
  if (typeof kv == "function")
    try {
      e = {
        clone: O4(),
        constant: Ov(),
        each: f2(),
        filter: S2(),
        has: E2(),
        isArray: Ne(),
        isEmpty: oO(),
        isFunction: Xo(),
        isUndefined: b2(),
        keys: or(),
        map: C2(),
        reduce: N2(),
        size: hO(),
        transform: pO(),
        union: NO(),
        values: M2(),
      };
    } catch {}
  return e || (e = window._), (qd = e), qd;
}
var Od, Tw;
function jv() {
  if (Tw) return Od;
  Tw = 1;
  var e = Nt();
  Od = i;
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
        e.each(c, function (m) {
          d.length > 1 ? h.setNode(m, f) : h.setNode(m);
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
      e.each(this._nodes, function (v, w) {
        c(w) && f.setNode(w, v);
      }),
        e.each(this._edgeObjs, function (v) {
          f.hasNode(v.v) && f.hasNode(v.w) && f.setEdge(v, d.edge(v));
        });
      var h = {};
      function m(v) {
        var w = d.parent(v);
        return w === void 0 || f.hasNode(w) ? ((h[v] = w), w) : w in h ? h[w] : m(w);
      }
      return (
        this._isCompound &&
          e.each(f.nodes(), function (v) {
            f.setParent(v, m(v));
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
        e.reduce(c, function (m, v) {
          return h.length > 1 ? d.setEdge(m, v, f) : d.setEdge(m, v), v;
        }),
        this
      );
    }),
    (i.prototype.setEdge = function () {
      var c,
        f,
        d,
        h,
        m = !1,
        v = arguments[0];
      typeof v == "object" && v !== null && "v" in v
        ? ((c = v.v),
          (f = v.w),
          (d = v.name),
          arguments.length === 2 && ((h = arguments[1]), (m = !0)))
        : ((c = v),
          (f = arguments[1]),
          (d = arguments[3]),
          arguments.length > 2 && ((h = arguments[2]), (m = !0))),
        (c = "" + c),
        (f = "" + f),
        e.isUndefined(d) || (d = "" + d);
      var w = s(this._isDirected, c, f, d);
      if (e.has(this._edgeLabels, w)) return m && (this._edgeLabels[w] = h), this;
      if (!e.isUndefined(d) && !this._isMultigraph)
        throw new Error("Cannot set a named edge when isMultigraph = false");
      this.setNode(c),
        this.setNode(f),
        (this._edgeLabels[w] = m ? h : this._defaultEdgeLabelFn(c, f, d));
      var p = u(this._isDirected, c, f, d);
      return (
        (c = p.v),
        (f = p.w),
        Object.freeze(p),
        (this._edgeObjs[w] = p),
        o(this._preds[f], c),
        o(this._sucs[c], f),
        (this._in[f][w] = p),
        (this._out[c][w] = p),
        this._edgeCount++,
        this
      );
    }),
    (i.prototype.edge = function (c, f, d) {
      var h =
        arguments.length === 1 ? l(this._isDirected, arguments[0]) : s(this._isDirected, c, f, d);
      return this._edgeLabels[h];
    }),
    (i.prototype.hasEdge = function (c, f, d) {
      var h =
        arguments.length === 1 ? l(this._isDirected, arguments[0]) : s(this._isDirected, c, f, d);
      return e.has(this._edgeLabels, h);
    }),
    (i.prototype.removeEdge = function (c, f, d) {
      var h =
          arguments.length === 1 ? l(this._isDirected, arguments[0]) : s(this._isDirected, c, f, d),
        m = this._edgeObjs[h];
      return (
        m &&
          ((c = m.v),
          (f = m.w),
          delete this._edgeLabels[h],
          delete this._edgeObjs[h],
          a(this._preds[f], c),
          a(this._sucs[c], f),
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
          ? e.filter(h, function (m) {
              return m.v === f;
            })
          : h;
      }
    }),
    (i.prototype.outEdges = function (c, f) {
      var d = this._out[c];
      if (d) {
        var h = e.values(d);
        return f
          ? e.filter(h, function (m) {
              return m.w === f;
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
  function a(c, f) {
    --c[f] || delete c[f];
  }
  function s(c, f, d, h) {
    var m = "" + f,
      v = "" + d;
    if (!c && m > v) {
      var w = m;
      (m = v), (v = w);
    }
    return m + r + v + r + (e.isUndefined(h) ? t : h);
  }
  function u(c, f, d, h) {
    var m = "" + f,
      v = "" + d;
    if (!c && m > v) {
      var w = m;
      (m = v), (v = w);
    }
    var p = { v: m, w: v };
    return h && (p.name = h), p;
  }
  function l(c, f) {
    return s(c, f.v, f.w, f.name);
  }
  return Od;
}
var Ld, Iw;
function TO() {
  return Iw || ((Iw = 1), (Ld = "2.1.8")), Ld;
}
var zd, Aw;
function IO() {
  return Aw || ((Aw = 1), (zd = { Graph: jv(), version: TO() })), zd;
}
var $d, Mw;
function AO() {
  if (Mw) return $d;
  Mw = 1;
  var e = Nt(),
    t = jv();
  $d = { write: n, read: o };
  function n(a) {
    var s = {
      options: { directed: a.isDirected(), multigraph: a.isMultigraph(), compound: a.isCompound() },
      nodes: r(a),
      edges: i(a),
    };
    return e.isUndefined(a.graph()) || (s.value = e.clone(a.graph())), s;
  }
  function r(a) {
    return e.map(a.nodes(), function (s) {
      var u = a.node(s),
        l = a.parent(s),
        c = { v: s };
      return e.isUndefined(u) || (c.value = u), e.isUndefined(l) || (c.parent = l), c;
    });
  }
  function i(a) {
    return e.map(a.edges(), function (s) {
      var u = a.edge(s),
        l = { v: s.v, w: s.w };
      return e.isUndefined(s.name) || (l.name = s.name), e.isUndefined(u) || (l.value = u), l;
    });
  }
  function o(a) {
    var s = new t(a.options).setGraph(a.value);
    return (
      e.each(a.nodes, function (u) {
        s.setNode(u.v, u.value), u.parent && s.setParent(u.v, u.parent);
      }),
      e.each(a.edges, function (u) {
        s.setEdge({ v: u.v, w: u.w, name: u.name }, u.value);
      }),
      s
    );
  }
  return $d;
}
var Dd, Pw;
function MO() {
  if (Pw) return Dd;
  Pw = 1;
  var e = Nt();
  Dd = t;
  function t(n) {
    var r = {},
      i = [],
      o;
    function a(s) {
      e.has(r, s) ||
        ((r[s] = !0), o.push(s), e.each(n.successors(s), a), e.each(n.predecessors(s), a));
    }
    return (
      e.each(n.nodes(), function (s) {
        (o = []), a(s), o.length && i.push(o);
      }),
      i
    );
  }
  return Dd;
}
var Fd, qw;
function P2() {
  if (qw) return Fd;
  qw = 1;
  var e = Nt();
  Fd = t;
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
          a = o.length;
        return (i[n] = a), o.push({ key: n, priority: r }), this._decrease(a), !0;
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
            r
        );
      (this._arr[i].priority = r), this._decrease(i);
    }),
    (t.prototype._heapify = function (n) {
      var r = this._arr,
        i = 2 * n,
        o = i + 1,
        a = n;
      i < r.length &&
        ((a = r[i].priority < r[a].priority ? i : a),
        o < r.length && (a = r[o].priority < r[a].priority ? o : a),
        a !== n && (this._swap(n, a), this._heapify(a)));
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
        a = i[n],
        s = i[r];
      (i[n] = s), (i[r] = a), (o[s.key] = n), (o[a.key] = r);
    }),
    Fd
  );
}
var jd, Ow;
function q2() {
  if (Ow) return jd;
  Ow = 1;
  var e = Nt(),
    t = P2();
  jd = r;
  var n = e.constant(1);
  function r(o, a, s, u) {
    return i(
      o,
      String(a),
      s || n,
      u ||
        function (l) {
          return o.outEdges(l);
        }
    );
  }
  function i(o, a, s, u) {
    var l = {},
      c = new t(),
      f,
      d,
      h = function (m) {
        var v = m.v !== f ? m.v : m.w,
          w = l[v],
          p = s(m),
          g = d.distance + p;
        if (p < 0)
          throw new Error(
            "dijkstra does not allow negative edge weights. Bad edge: " + m + " Weight: " + p
          );
        g < w.distance && ((w.distance = g), (w.predecessor = f), c.decrease(v, g));
      };
    for (
      o.nodes().forEach(function (m) {
        var v = m === a ? 0 : Number.POSITIVE_INFINITY;
        (l[m] = { distance: v }), c.add(m, v);
      });
      c.size() > 0 && ((f = c.removeMin()), (d = l[f]), d.distance !== Number.POSITIVE_INFINITY);

    )
      u(f).forEach(h);
    return l;
  }
  return jd;
}
var Bd, Lw;
function PO() {
  if (Lw) return Bd;
  Lw = 1;
  var e = q2(),
    t = Nt();
  Bd = n;
  function n(r, i, o) {
    return t.transform(
      r.nodes(),
      function (a, s) {
        a[s] = e(r, s, i, o);
      },
      {}
    );
  }
  return Bd;
}
var Hd, zw;
function O2() {
  if (zw) return Hd;
  zw = 1;
  var e = Nt();
  Hd = t;
  function t(n) {
    var r = 0,
      i = [],
      o = {},
      a = [];
    function s(u) {
      var l = (o[u] = { onStack: !0, lowlink: r, index: r++ });
      if (
        (i.push(u),
        n.successors(u).forEach(function (d) {
          e.has(o, d)
            ? o[d].onStack && (l.lowlink = Math.min(l.lowlink, o[d].index))
            : (s(d), (l.lowlink = Math.min(l.lowlink, o[d].lowlink)));
        }),
        l.lowlink === l.index)
      ) {
        var c = [],
          f;
        do (f = i.pop()), (o[f].onStack = !1), c.push(f);
        while (u !== f);
        a.push(c);
      }
    }
    return (
      n.nodes().forEach(function (u) {
        e.has(o, u) || s(u);
      }),
      a
    );
  }
  return Hd;
}
var Vd, $w;
function qO() {
  if ($w) return Vd;
  $w = 1;
  var e = Nt(),
    t = O2();
  Vd = n;
  function n(r) {
    return e.filter(t(r), function (i) {
      return i.length > 1 || (i.length === 1 && r.hasEdge(i[0], i[0]));
    });
  }
  return Vd;
}
var Ud, Dw;
function OO() {
  if (Dw) return Ud;
  Dw = 1;
  var e = Nt();
  Ud = n;
  var t = e.constant(1);
  function n(i, o, a) {
    return r(
      i,
      o || t,
      a ||
        function (s) {
          return i.outEdges(s);
        }
    );
  }
  function r(i, o, a) {
    var s = {},
      u = i.nodes();
    return (
      u.forEach(function (l) {
        (s[l] = {}),
          (s[l][l] = { distance: 0 }),
          u.forEach(function (c) {
            l !== c && (s[l][c] = { distance: Number.POSITIVE_INFINITY });
          }),
          a(l).forEach(function (c) {
            var f = c.v === l ? c.w : c.v,
              d = o(c);
            s[l][f] = { distance: d, predecessor: l };
          });
      }),
      u.forEach(function (l) {
        var c = s[l];
        u.forEach(function (f) {
          var d = s[f];
          u.forEach(function (h) {
            var m = d[l],
              v = c[h],
              w = d[h],
              p = m.distance + v.distance;
            p < w.distance && ((w.distance = p), (w.predecessor = v.predecessor));
          });
        });
      }),
      s
    );
  }
  return Ud;
}
var Gd, Fw;
function L2() {
  if (Fw) return Gd;
  Fw = 1;
  var e = Nt();
  (Gd = t), (t.CycleException = n);
  function t(r) {
    var i = {},
      o = {},
      a = [];
    function s(u) {
      if (e.has(o, u)) throw new n();
      e.has(i, u) ||
        ((o[u] = !0), (i[u] = !0), e.each(r.predecessors(u), s), delete o[u], a.push(u));
    }
    if ((e.each(r.sinks(), s), e.size(i) !== r.nodeCount())) throw new n();
    return a;
  }
  function n() {}
  return (n.prototype = new Error()), Gd;
}
var Wd, jw;
function LO() {
  if (jw) return Wd;
  jw = 1;
  var e = L2();
  Wd = t;
  function t(n) {
    try {
      e(n);
    } catch (r) {
      if (r instanceof e.CycleException) return !1;
      throw r;
    }
    return !0;
  }
  return Wd;
}
var Kd, Bw;
function z2() {
  if (Bw) return Kd;
  Bw = 1;
  var e = Nt();
  Kd = t;
  function t(r, i, o) {
    e.isArray(i) || (i = [i]);
    var a = (r.isDirected() ? r.successors : r.neighbors).bind(r),
      s = [],
      u = {};
    return (
      e.each(i, function (l) {
        if (!r.hasNode(l)) throw new Error("Graph does not have node: " + l);
        n(r, l, o === "post", u, a, s);
      }),
      s
    );
  }
  function n(r, i, o, a, s, u) {
    e.has(a, i) ||
      ((a[i] = !0),
      o || u.push(i),
      e.each(s(i), function (l) {
        n(r, l, o, a, s, u);
      }),
      o && u.push(i));
  }
  return Kd;
}
var Yd, Hw;
function zO() {
  if (Hw) return Yd;
  Hw = 1;
  var e = z2();
  Yd = t;
  function t(n, r) {
    return e(n, r, "post");
  }
  return Yd;
}
var Xd, Vw;
function $O() {
  if (Vw) return Xd;
  Vw = 1;
  var e = z2();
  Xd = t;
  function t(n, r) {
    return e(n, r, "pre");
  }
  return Xd;
}
var Qd, Uw;
function DO() {
  if (Uw) return Qd;
  Uw = 1;
  var e = Nt(),
    t = jv(),
    n = P2();
  Qd = r;
  function r(i, o) {
    var a = new t(),
      s = {},
      u = new n(),
      l;
    function c(d) {
      var h = d.v === l ? d.w : d.v,
        m = u.priority(h);
      if (m !== void 0) {
        var v = o(d);
        v < m && ((s[h] = l), u.decrease(h, v));
      }
    }
    if (i.nodeCount() === 0) return a;
    e.each(i.nodes(), function (d) {
      u.add(d, Number.POSITIVE_INFINITY), a.setNode(d);
    }),
      u.decrease(i.nodes()[0], 0);
    for (var f = !1; u.size() > 0; ) {
      if (((l = u.removeMin()), e.has(s, l))) a.setEdge(l, s[l]);
      else {
        if (f) throw new Error("Input graph is not connected: " + i);
        f = !0;
      }
      i.nodeEdges(l).forEach(c);
    }
    return a;
  }
  return Qd;
}
var Zd, Gw;
function FO() {
  return (
    Gw ||
      ((Gw = 1),
      (Zd = {
        components: MO(),
        dijkstra: q2(),
        dijkstraAll: PO(),
        findCycles: qO(),
        floydWarshall: OO(),
        isAcyclic: LO(),
        postorder: zO(),
        preorder: $O(),
        prim: DO(),
        tarjan: O2(),
        topsort: L2(),
      })),
    Zd
  );
}
var Jd, Ww;
function jO() {
  if (Ww) return Jd;
  Ww = 1;
  var e = IO();
  return (Jd = { Graph: e.Graph, json: AO(), alg: FO(), version: e.version }), Jd;
}
var ks;
if (typeof kv == "function")
  try {
    ks = jO();
  } catch {}
ks || (ks = window.graphlib);
var Bt = ks,
  eh,
  Kw;
function BO() {
  if (Kw) return eh;
  Kw = 1;
  var e = u2(),
    t = 1,
    n = 4;
  function r(i) {
    return e(i, t | n);
  }
  return (eh = r), eh;
}
var th, Yw;
function gu() {
  if (Yw) return th;
  Yw = 1;
  var e = bi(),
    t = kn(),
    n = au(),
    r = Ct();
  function i(o, a, s) {
    if (!r(s)) return !1;
    var u = typeof a;
    return (u == "number" ? t(s) && n(a, s.length) : u == "string" && a in s) ? e(s[a], o) : !1;
  }
  return (th = i), th;
}
var nh, Xw;
function HO() {
  if (Xw) return nh;
  Xw = 1;
  var e = pu(),
    t = bi(),
    n = gu(),
    r = Mr(),
    i = Object.prototype,
    o = i.hasOwnProperty,
    a = e(function (s, u) {
      s = Object(s);
      var l = -1,
        c = u.length,
        f = c > 2 ? u[2] : void 0;
      for (f && n(u[0], u[1], f) && (c = 1); ++l < c; )
        for (var d = u[l], h = r(d), m = -1, v = h.length; ++m < v; ) {
          var w = h[m],
            p = s[w];
          (p === void 0 || (t(p, i[w]) && !o.call(s, w))) && (s[w] = d[w]);
        }
      return s;
    });
  return (nh = a), nh;
}
var rh, Qw;
function VO() {
  if (Qw) return rh;
  Qw = 1;
  var e = Cn(),
    t = kn(),
    n = or();
  function r(i) {
    return function (o, a, s) {
      var u = Object(o);
      if (!t(o)) {
        var l = e(a, 3);
        (o = n(o)),
          (a = function (f) {
            return l(u[f], f, u);
          });
      }
      var c = i(o, a, s);
      return c > -1 ? u[l ? o[c] : c] : void 0;
    };
  }
  return (rh = r), rh;
}
var ih, Zw;
function UO() {
  if (Zw) return ih;
  Zw = 1;
  var e = /\s/;
  function t(n) {
    for (var r = n.length; r-- && e.test(n.charAt(r)); );
    return r;
  }
  return (ih = t), ih;
}
var oh, Jw;
function GO() {
  if (Jw) return oh;
  Jw = 1;
  var e = UO(),
    t = /^\s+/;
  function n(r) {
    return r && r.slice(0, e(r) + 1).replace(t, "");
  }
  return (oh = n), oh;
}
var ah, ex;
function WO() {
  if (ex) return ah;
  ex = 1;
  var e = GO(),
    t = Ct(),
    n = Ri(),
    r = NaN,
    i = /^[-+]0x[0-9a-f]+$/i,
    o = /^0b[01]+$/i,
    a = /^0o[0-7]+$/i,
    s = parseInt;
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
    return f || a.test(l) ? s(l.slice(2), f ? 2 : 8) : i.test(l) ? r : +l;
  }
  return (ah = u), ah;
}
var sh, tx;
function $2() {
  if (tx) return sh;
  tx = 1;
  var e = WO(),
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
  return (sh = r), sh;
}
var uh, nx;
function KO() {
  if (nx) return uh;
  nx = 1;
  var e = $2();
  function t(n) {
    var r = e(n),
      i = r % 1;
    return r === r ? (i ? r - i : r) : 0;
  }
  return (uh = t), uh;
}
var lh, rx;
function YO() {
  if (rx) return lh;
  rx = 1;
  var e = I2(),
    t = Cn(),
    n = KO(),
    r = Math.max;
  function i(o, a, s) {
    var u = o == null ? 0 : o.length;
    if (!u) return -1;
    var l = s == null ? 0 : n(s);
    return l < 0 && (l = r(u + l, 0)), e(o, t(a, 3), l);
  }
  return (lh = i), lh;
}
var ch, ix;
function XO() {
  if (ix) return ch;
  ix = 1;
  var e = VO(),
    t = YO(),
    n = e(t);
  return (ch = n), ch;
}
var fh, ox;
function D2() {
  if (ox) return fh;
  ox = 1;
  var e = Fv();
  function t(n) {
    var r = n == null ? 0 : n.length;
    return r ? e(n, 1) : [];
  }
  return (fh = t), fh;
}
var dh, ax;
function QO() {
  if (ax) return dh;
  ax = 1;
  var e = Lv(),
    t = l2(),
    n = Mr();
  function r(i, o) {
    return i == null ? i : e(i, t(o), n);
  }
  return (dh = r), dh;
}
var hh, sx;
function ZO() {
  if (sx) return hh;
  sx = 1;
  function e(t) {
    var n = t == null ? 0 : t.length;
    return n ? t[n - 1] : void 0;
  }
  return (hh = e), hh;
}
var ph, ux;
function JO() {
  if (ux) return ph;
  ux = 1;
  var e = iu(),
    t = zv(),
    n = Cn();
  function r(i, o) {
    var a = {};
    return (
      (o = n(o, 3)),
      t(i, function (s, u, l) {
        e(a, u, o(s, u, l));
      }),
      a
    );
  }
  return (ph = r), ph;
}
var gh, lx;
function Bv() {
  if (lx) return gh;
  lx = 1;
  var e = Ri();
  function t(n, r, i) {
    for (var o = -1, a = n.length; ++o < a; ) {
      var s = n[o],
        u = r(s);
      if (u != null && (l === void 0 ? u === u && !e(u) : i(u, l)))
        var l = u,
          c = s;
    }
    return c;
  }
  return (gh = t), gh;
}
var vh, cx;
function eL() {
  if (cx) return vh;
  cx = 1;
  function e(t, n) {
    return t > n;
  }
  return (vh = e), vh;
}
var mh, fx;
function tL() {
  if (fx) return mh;
  fx = 1;
  var e = Bv(),
    t = eL(),
    n = Pr();
  function r(i) {
    return i && i.length ? e(i, n, t) : void 0;
  }
  return (mh = r), mh;
}
var yh, dx;
function F2() {
  if (dx) return yh;
  dx = 1;
  var e = iu(),
    t = bi();
  function n(r, i, o) {
    ((o !== void 0 && !t(r[i], o)) || (o === void 0 && !(i in r))) && e(r, i, o);
  }
  return (yh = n), yh;
}
var _h, hx;
function nL() {
  if (hx) return _h;
  hx = 1;
  var e = Ir(),
    t = lu(),
    n = en(),
    r = "[object Object]",
    i = Function.prototype,
    o = Object.prototype,
    a = i.toString,
    s = o.hasOwnProperty,
    u = a.call(Object);
  function l(c) {
    if (!n(c) || e(c) != r) return !1;
    var f = t(c);
    if (f === null) return !0;
    var d = s.call(f, "constructor") && f.constructor;
    return typeof d == "function" && d instanceof d && a.call(d) == u;
  }
  return (_h = l), _h;
}
var wh, px;
function j2() {
  if (px) return wh;
  px = 1;
  function e(t, n) {
    if (!(n === "constructor" && typeof t[n] == "function") && n != "__proto__") return t[n];
  }
  return (wh = e), wh;
}
var xh, gx;
function rL() {
  if (gx) return xh;
  gx = 1;
  var e = Qo(),
    t = Mr();
  function n(r) {
    return e(r, t(r));
  }
  return (xh = n), xh;
}
var Sh, vx;
function iL() {
  if (vx) return Sh;
  vx = 1;
  var e = F2(),
    t = Xk(),
    n = o2(),
    r = Qk(),
    i = s2(),
    o = Zo(),
    a = Ne(),
    s = A2(),
    u = Ci(),
    l = Xo(),
    c = Ct(),
    f = nL(),
    d = Jo(),
    h = j2(),
    m = rL();
  function v(w, p, g, y, _, S, E) {
    var k = h(w, g),
      C = h(p, g),
      T = E.get(C);
    if (T) {
      e(w, g, T);
      return;
    }
    var I = S ? S(k, C, g + "", w, p, E) : void 0,
      M = I === void 0;
    if (M) {
      var z = a(C),
        F = !z && u(C),
        x = !z && !F && d(C);
      (I = C),
        z || F || x
          ? a(k)
            ? (I = k)
            : s(k)
            ? (I = r(k))
            : F
            ? ((M = !1), (I = t(C, !0)))
            : x
            ? ((M = !1), (I = n(C, !0)))
            : (I = [])
          : f(C) || o(C)
          ? ((I = k), o(k) ? (I = m(k)) : (!c(k) || l(k)) && (I = i(C)))
          : (M = !1);
    }
    M && (E.set(C, I), _(I, C, y, S, E), E.delete(C)), e(w, g, I);
  }
  return (Sh = v), Sh;
}
var Eh, mx;
function oL() {
  if (mx) return Eh;
  mx = 1;
  var e = ru(),
    t = F2(),
    n = Lv(),
    r = iL(),
    i = Ct(),
    o = Mr(),
    a = j2();
  function s(u, l, c, f, d) {
    u !== l &&
      n(
        l,
        function (h, m) {
          if ((d || (d = new e()), i(h))) r(u, l, m, c, s, f, d);
          else {
            var v = f ? f(a(u, m), h, m + "", u, l, d) : void 0;
            v === void 0 && (v = h), t(u, m, v);
          }
        },
        o
      );
  }
  return (Eh = s), Eh;
}
var bh, yx;
function aL() {
  if (yx) return bh;
  yx = 1;
  var e = pu(),
    t = gu();
  function n(r) {
    return e(function (i, o) {
      var a = -1,
        s = o.length,
        u = s > 1 ? o[s - 1] : void 0,
        l = s > 2 ? o[2] : void 0;
      for (
        u = r.length > 3 && typeof u == "function" ? (s--, u) : void 0,
          l && t(o[0], o[1], l) && ((u = s < 3 ? void 0 : u), (s = 1)),
          i = Object(i);
        ++a < s;

      ) {
        var c = o[a];
        c && r(i, c, a, u);
      }
      return i;
    });
  }
  return (bh = n), bh;
}
var kh, _x;
function sL() {
  if (_x) return kh;
  _x = 1;
  var e = oL(),
    t = aL(),
    n = t(function (r, i, o) {
      e(r, i, o);
    });
  return (kh = n), kh;
}
var Ch, wx;
function B2() {
  if (wx) return Ch;
  wx = 1;
  function e(t, n) {
    return t < n;
  }
  return (Ch = e), Ch;
}
var Nh, xx;
function uL() {
  if (xx) return Nh;
  xx = 1;
  var e = Bv(),
    t = B2(),
    n = Pr();
  function r(i) {
    return i && i.length ? e(i, n, t) : void 0;
  }
  return (Nh = r), Nh;
}
var Rh, Sx;
function lL() {
  if (Sx) return Rh;
  Sx = 1;
  var e = Bv(),
    t = Cn(),
    n = B2();
  function r(i, o) {
    return i && i.length ? e(i, t(o, 2), n) : void 0;
  }
  return (Rh = r), Rh;
}
var Th, Ex;
function cL() {
  if (Ex) return Th;
  Ex = 1;
  var e = jt(),
    t = function () {
      return e.Date.now();
    };
  return (Th = t), Th;
}
var Ih, bx;
function fL() {
  if (bx) return Ih;
  bx = 1;
  var e = ou(),
    t = du(),
    n = au(),
    r = Ct(),
    i = ea();
  function o(a, s, u, l) {
    if (!r(a)) return a;
    s = t(s, a);
    for (var c = -1, f = s.length, d = f - 1, h = a; h != null && ++c < f; ) {
      var m = i(s[c]),
        v = u;
      if (m === "__proto__" || m === "constructor" || m === "prototype") return a;
      if (c != d) {
        var w = h[m];
        (v = l ? l(w, m, h) : void 0), v === void 0 && (v = r(w) ? w : n(s[c + 1]) ? [] : {});
      }
      e(h, m, v), (h = h[m]);
    }
    return a;
  }
  return (Ih = o), Ih;
}
var Ah, kx;
function dL() {
  if (kx) return Ah;
  kx = 1;
  var e = hu(),
    t = fL(),
    n = du();
  function r(i, o, a) {
    for (var s = -1, u = o.length, l = {}; ++s < u; ) {
      var c = o[s],
        f = e(i, c);
      a(f, c) && t(l, n(c, i), f);
    }
    return l;
  }
  return (Ah = r), Ah;
}
var Mh, Cx;
function hL() {
  if (Cx) return Mh;
  Cx = 1;
  var e = dL(),
    t = w2();
  function n(r, i) {
    return e(r, i, function (o, a) {
      return t(r, a);
    });
  }
  return (Mh = n), Mh;
}
var Ph, Nx;
function pL() {
  if (Nx) return Ph;
  Nx = 1;
  var e = D2(),
    t = R2(),
    n = T2();
  function r(i) {
    return n(t(i, void 0, e), i + "");
  }
  return (Ph = r), Ph;
}
var qh, Rx;
function gL() {
  if (Rx) return qh;
  Rx = 1;
  var e = hL(),
    t = pL(),
    n = t(function (r, i) {
      return r == null ? {} : e(r, i);
    });
  return (qh = n), qh;
}
var Oh, Tx;
function vL() {
  if (Tx) return Oh;
  Tx = 1;
  var e = Math.ceil,
    t = Math.max;
  function n(r, i, o, a) {
    for (var s = -1, u = t(e((i - r) / (o || 1)), 0), l = Array(u); u--; )
      (l[a ? u : ++s] = r), (r += o);
    return l;
  }
  return (Oh = n), Oh;
}
var Lh, Ix;
function mL() {
  if (Ix) return Lh;
  Ix = 1;
  var e = vL(),
    t = gu(),
    n = $2();
  function r(i) {
    return function (o, a, s) {
      return (
        s && typeof s != "number" && t(o, a, s) && (a = s = void 0),
        (o = n(o)),
        a === void 0 ? ((a = o), (o = 0)) : (a = n(a)),
        (s = s === void 0 ? (o < a ? 1 : -1) : n(s)),
        e(o, a, s, i)
      );
    };
  }
  return (Lh = r), Lh;
}
var zh, Ax;
function yL() {
  if (Ax) return zh;
  Ax = 1;
  var e = mL(),
    t = e();
  return (zh = t), zh;
}
var $h, Mx;
function _L() {
  if (Mx) return $h;
  Mx = 1;
  function e(t, n) {
    var r = t.length;
    for (t.sort(n); r--; ) t[r] = t[r].value;
    return t;
  }
  return ($h = e), $h;
}
var Dh, Px;
function wL() {
  if (Px) return Dh;
  Px = 1;
  var e = Ri();
  function t(n, r) {
    if (n !== r) {
      var i = n !== void 0,
        o = n === null,
        a = n === n,
        s = e(n),
        u = r !== void 0,
        l = r === null,
        c = r === r,
        f = e(r);
      if (
        (!l && !f && !s && n > r) ||
        (s && u && c && !l && !f) ||
        (o && u && c) ||
        (!i && c) ||
        !a
      )
        return 1;
      if (
        (!o && !s && !f && n < r) ||
        (f && i && a && !o && !s) ||
        (l && i && a) ||
        (!u && a) ||
        !c
      )
        return -1;
    }
    return 0;
  }
  return (Dh = t), Dh;
}
var Fh, qx;
function xL() {
  if (qx) return Fh;
  qx = 1;
  var e = wL();
  function t(n, r, i) {
    for (var o = -1, a = n.criteria, s = r.criteria, u = a.length, l = i.length; ++o < u; ) {
      var c = e(a[o], s[o]);
      if (c) {
        if (o >= l) return c;
        var f = i[o];
        return c * (f == "desc" ? -1 : 1);
      }
    }
    return n.index - r.index;
  }
  return (Fh = t), Fh;
}
var jh, Ox;
function SL() {
  if (Ox) return jh;
  Ox = 1;
  var e = fu(),
    t = hu(),
    n = Cn(),
    r = k2(),
    i = _L(),
    o = su(),
    a = xL(),
    s = Pr(),
    u = Ne();
  function l(c, f, d) {
    f.length
      ? (f = e(f, function (v) {
          return u(v)
            ? function (w) {
                return t(w, v.length === 1 ? v[0] : v);
              }
            : v;
        }))
      : (f = [s]);
    var h = -1;
    f = e(f, o(n));
    var m = r(c, function (v, w, p) {
      var g = e(f, function (y) {
        return y(v);
      });
      return { criteria: g, index: ++h, value: v };
    });
    return i(m, function (v, w) {
      return a(v, w, d);
    });
  }
  return (jh = l), jh;
}
var Bh, Lx;
function EL() {
  if (Lx) return Bh;
  Lx = 1;
  var e = Fv(),
    t = SL(),
    n = pu(),
    r = gu(),
    i = n(function (o, a) {
      if (o == null) return [];
      var s = a.length;
      return (
        s > 1 && r(o, a[0], a[1]) ? (a = []) : s > 2 && r(a[0], a[1], a[2]) && (a = [a[0]]),
        t(o, e(a, 1), [])
      );
    });
  return (Bh = i), Bh;
}
var Hh, zx;
function bL() {
  if (zx) return Hh;
  zx = 1;
  var e = y2(),
    t = 0;
  function n(r) {
    var i = ++t;
    return e(r) + i;
  }
  return (Hh = n), Hh;
}
var Vh, $x;
function kL() {
  if ($x) return Vh;
  $x = 1;
  function e(t, n, r) {
    for (var i = -1, o = t.length, a = n.length, s = {}; ++i < o; ) {
      var u = i < a ? n[i] : void 0;
      r(s, t[i], u);
    }
    return s;
  }
  return (Vh = e), Vh;
}
var Uh, Dx;
function CL() {
  if (Dx) return Uh;
  Dx = 1;
  var e = ou(),
    t = kL();
  function n(r, i) {
    return t(r || [], i || [], e);
  }
  return (Uh = n), Uh;
}
var Cs;
if (typeof kv == "function")
  try {
    Cs = {
      cloneDeep: BO(),
      constant: Ov(),
      defaults: HO(),
      each: f2(),
      filter: S2(),
      find: XO(),
      flatten: D2(),
      forEach: c2(),
      forIn: QO(),
      has: E2(),
      isUndefined: b2(),
      last: ZO(),
      map: C2(),
      mapValues: JO(),
      max: tL(),
      merge: sL(),
      min: uL(),
      minBy: lL(),
      now: cL(),
      pick: gL(),
      range: yL(),
      reduce: N2(),
      sortBy: EL(),
      uniqueId: bL(),
      values: M2(),
      zipObject: CL(),
    };
  } catch {}
Cs || (Cs = window._);
var ve = Cs,
  NL = vu;
function vu() {
  var e = {};
  (e._next = e._prev = e), (this._sentinel = e);
}
vu.prototype.dequeue = function () {
  var e = this._sentinel,
    t = e._prev;
  if (t !== e) return H2(t), t;
};
vu.prototype.enqueue = function (e) {
  var t = this._sentinel;
  e._prev && e._next && H2(e),
    (e._next = t._next),
    (t._next._prev = e),
    (t._next = e),
    (e._prev = t);
};
vu.prototype.toString = function () {
  for (var e = [], t = this._sentinel, n = t._prev; n !== t; )
    e.push(JSON.stringify(n, RL)), (n = n._prev);
  return "[" + e.join(", ") + "]";
};
function H2(e) {
  (e._prev._next = e._next), (e._next._prev = e._prev), delete e._next, delete e._prev;
}
function RL(e, t) {
  if (e !== "_next" && e !== "_prev") return t;
}
var hn = ve,
  TL = Bt.Graph,
  IL = NL,
  AL = PL,
  ML = hn.constant(1);
function PL(e, t) {
  if (e.nodeCount() <= 1) return [];
  var n = OL(e, t || ML),
    r = qL(n.graph, n.buckets, n.zeroIdx);
  return hn.flatten(
    hn.map(r, function (i) {
      return e.outEdges(i.v, i.w);
    }),
    !0
  );
}
function qL(e, t, n) {
  for (var r = [], i = t[t.length - 1], o = t[0], a; e.nodeCount(); ) {
    for (; (a = o.dequeue()); ) Gh(e, t, n, a);
    for (; (a = i.dequeue()); ) Gh(e, t, n, a);
    if (e.nodeCount()) {
      for (var s = t.length - 2; s > 0; --s)
        if (((a = t[s].dequeue()), a)) {
          r = r.concat(Gh(e, t, n, a, !0));
          break;
        }
    }
  }
  return r;
}
function Gh(e, t, n, r, i) {
  var o = i ? [] : void 0;
  return (
    hn.forEach(e.inEdges(r.v), function (a) {
      var s = e.edge(a),
        u = e.node(a.v);
      i && o.push({ v: a.v, w: a.w }), (u.out -= s), cg(t, n, u);
    }),
    hn.forEach(e.outEdges(r.v), function (a) {
      var s = e.edge(a),
        u = a.w,
        l = e.node(u);
      (l.in -= s), cg(t, n, l);
    }),
    e.removeNode(r.v),
    o
  );
}
function OL(e, t) {
  var n = new TL(),
    r = 0,
    i = 0;
  hn.forEach(e.nodes(), function (s) {
    n.setNode(s, { v: s, in: 0, out: 0 });
  }),
    hn.forEach(e.edges(), function (s) {
      var u = n.edge(s.v, s.w) || 0,
        l = t(s),
        c = u + l;
      n.setEdge(s.v, s.w, c),
        (i = Math.max(i, (n.node(s.v).out += l))),
        (r = Math.max(r, (n.node(s.w).in += l)));
    });
  var o = hn.range(i + r + 3).map(function () {
      return new IL();
    }),
    a = r + 1;
  return (
    hn.forEach(n.nodes(), function (s) {
      cg(o, a, n.node(s));
    }),
    { graph: n, buckets: o, zeroIdx: a }
  );
}
function cg(e, t, n) {
  n.out ? (n.in ? e[n.out - n.in + t].enqueue(n) : e[e.length - 1].enqueue(n)) : e[0].enqueue(n);
}
var vr = ve,
  LL = AL,
  zL = { run: $L, undo: FL };
function $L(e) {
  var t = e.graph().acyclicer === "greedy" ? LL(e, n(e)) : DL(e);
  vr.forEach(t, function (r) {
    var i = e.edge(r);
    e.removeEdge(r),
      (i.forwardName = r.name),
      (i.reversed = !0),
      e.setEdge(r.w, r.v, i, vr.uniqueId("rev"));
  });
  function n(r) {
    return function (i) {
      return r.edge(i).weight;
    };
  }
}
function DL(e) {
  var t = [],
    n = {},
    r = {};
  function i(o) {
    vr.has(r, o) ||
      ((r[o] = !0),
      (n[o] = !0),
      vr.forEach(e.outEdges(o), function (a) {
        vr.has(n, a.w) ? t.push(a) : i(a.w);
      }),
      delete n[o]);
  }
  return vr.forEach(e.nodes(), i), t;
}
function FL(e) {
  vr.forEach(e.edges(), function (t) {
    var n = e.edge(t);
    if (n.reversed) {
      e.removeEdge(t);
      var r = n.forwardName;
      delete n.reversed, delete n.forwardName, e.setEdge(t.w, t.v, n, r);
    }
  });
}
var ue = ve,
  V2 = Bt.Graph,
  ut = {
    addDummyNode: U2,
    simplify: jL,
    asNonCompoundGraph: BL,
    successorWeights: HL,
    predecessorWeights: VL,
    intersectRect: UL,
    buildLayerMatrix: GL,
    normalizeRanks: WL,
    removeEmptyRanks: KL,
    addBorderNode: YL,
    maxRank: G2,
    partition: XL,
    time: QL,
    notime: ZL,
  };
function U2(e, t, n, r) {
  var i;
  do i = ue.uniqueId(r);
  while (e.hasNode(i));
  return (n.dummy = t), e.setNode(i, n), i;
}
function jL(e) {
  var t = new V2().setGraph(e.graph());
  return (
    ue.forEach(e.nodes(), function (n) {
      t.setNode(n, e.node(n));
    }),
    ue.forEach(e.edges(), function (n) {
      var r = t.edge(n.v, n.w) || { weight: 0, minlen: 1 },
        i = e.edge(n);
      t.setEdge(n.v, n.w, { weight: r.weight + i.weight, minlen: Math.max(r.minlen, i.minlen) });
    }),
    t
  );
}
function BL(e) {
  var t = new V2({ multigraph: e.isMultigraph() }).setGraph(e.graph());
  return (
    ue.forEach(e.nodes(), function (n) {
      e.children(n).length || t.setNode(n, e.node(n));
    }),
    ue.forEach(e.edges(), function (n) {
      t.setEdge(n, e.edge(n));
    }),
    t
  );
}
function HL(e) {
  var t = ue.map(e.nodes(), function (n) {
    var r = {};
    return (
      ue.forEach(e.outEdges(n), function (i) {
        r[i.w] = (r[i.w] || 0) + e.edge(i).weight;
      }),
      r
    );
  });
  return ue.zipObject(e.nodes(), t);
}
function VL(e) {
  var t = ue.map(e.nodes(), function (n) {
    var r = {};
    return (
      ue.forEach(e.inEdges(n), function (i) {
        r[i.v] = (r[i.v] || 0) + e.edge(i).weight;
      }),
      r
    );
  });
  return ue.zipObject(e.nodes(), t);
}
function UL(e, t) {
  var n = e.x,
    r = e.y,
    i = t.x - n,
    o = t.y - r,
    a = e.width / 2,
    s = e.height / 2;
  if (!i && !o) throw new Error("Not possible to find intersection inside of the rectangle");
  var u, l;
  return (
    Math.abs(o) * a > Math.abs(i) * s
      ? (o < 0 && (s = -s), (u = (s * i) / o), (l = s))
      : (i < 0 && (a = -a), (u = a), (l = (a * o) / i)),
    { x: n + u, y: r + l }
  );
}
function GL(e) {
  var t = ue.map(ue.range(G2(e) + 1), function () {
    return [];
  });
  return (
    ue.forEach(e.nodes(), function (n) {
      var r = e.node(n),
        i = r.rank;
      ue.isUndefined(i) || (t[i][r.order] = n);
    }),
    t
  );
}
function WL(e) {
  var t = ue.min(
    ue.map(e.nodes(), function (n) {
      return e.node(n).rank;
    })
  );
  ue.forEach(e.nodes(), function (n) {
    var r = e.node(n);
    ue.has(r, "rank") && (r.rank -= t);
  });
}
function KL(e) {
  var t = ue.min(
      ue.map(e.nodes(), function (o) {
        return e.node(o).rank;
      })
    ),
    n = [];
  ue.forEach(e.nodes(), function (o) {
    var a = e.node(o).rank - t;
    n[a] || (n[a] = []), n[a].push(o);
  });
  var r = 0,
    i = e.graph().nodeRankFactor;
  ue.forEach(n, function (o, a) {
    ue.isUndefined(o) && a % i !== 0
      ? --r
      : r &&
        ue.forEach(o, function (s) {
          e.node(s).rank += r;
        });
  });
}
function YL(e, t, n, r) {
  var i = { width: 0, height: 0 };
  return arguments.length >= 4 && ((i.rank = n), (i.order = r)), U2(e, "border", i, t);
}
function G2(e) {
  return ue.max(
    ue.map(e.nodes(), function (t) {
      var n = e.node(t).rank;
      if (!ue.isUndefined(n)) return n;
    })
  );
}
function XL(e, t) {
  var n = { lhs: [], rhs: [] };
  return (
    ue.forEach(e, function (r) {
      t(r) ? n.lhs.push(r) : n.rhs.push(r);
    }),
    n
  );
}
function QL(e, t) {
  var n = ue.now();
  try {
    return t();
  } finally {
    console.log(e + " time: " + (ue.now() - n) + "ms");
  }
}
function ZL(e, t) {
  return t();
}
var W2 = ve,
  JL = ut,
  ez = { run: tz, undo: rz };
function tz(e) {
  (e.graph().dummyChains = []),
    W2.forEach(e.edges(), function (t) {
      nz(e, t);
    });
}
function nz(e, t) {
  var n = t.v,
    r = e.node(n).rank,
    i = t.w,
    o = e.node(i).rank,
    a = t.name,
    s = e.edge(t),
    u = s.labelRank;
  if (o !== r + 1) {
    e.removeEdge(t);
    var l, c, f;
    for (f = 0, ++r; r < o; ++f, ++r)
      (s.points = []),
        (c = { width: 0, height: 0, edgeLabel: s, edgeObj: t, rank: r }),
        (l = JL.addDummyNode(e, "edge", c, "_d")),
        r === u &&
          ((c.width = s.width),
          (c.height = s.height),
          (c.dummy = "edge-label"),
          (c.labelpos = s.labelpos)),
        e.setEdge(n, l, { weight: s.weight }, a),
        f === 0 && e.graph().dummyChains.push(l),
        (n = l);
    e.setEdge(n, i, { weight: s.weight }, a);
  }
}
function rz(e) {
  W2.forEach(e.graph().dummyChains, function (t) {
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
var Ra = ve,
  mu = { longestPath: iz, slack: oz };
function iz(e) {
  var t = {};
  function n(r) {
    var i = e.node(r);
    if (Ra.has(t, r)) return i.rank;
    t[r] = !0;
    var o = Ra.min(
      Ra.map(e.outEdges(r), function (a) {
        return n(a.w) - e.edge(a).minlen;
      })
    );
    return (o === Number.POSITIVE_INFINITY || o === void 0 || o === null) && (o = 0), (i.rank = o);
  }
  Ra.forEach(e.sources(), n);
}
function oz(e, t) {
  return e.node(t.w).rank - e.node(t.v).rank - e.edge(t).minlen;
}
var Ns = ve,
  az = Bt.Graph,
  Rs = mu.slack,
  K2 = sz;
function sz(e) {
  var t = new az({ directed: !1 }),
    n = e.nodes()[0],
    r = e.nodeCount();
  t.setNode(n, {});
  for (var i, o; uz(t, e) < r; )
    (i = lz(t, e)), (o = t.hasNode(i.v) ? Rs(e, i) : -Rs(e, i)), cz(t, e, o);
  return t;
}
function uz(e, t) {
  function n(r) {
    Ns.forEach(t.nodeEdges(r), function (i) {
      var o = i.v,
        a = r === o ? i.w : o;
      !e.hasNode(a) && !Rs(t, i) && (e.setNode(a, {}), e.setEdge(r, a, {}), n(a));
    });
  }
  return Ns.forEach(e.nodes(), n), e.nodeCount();
}
function lz(e, t) {
  return Ns.minBy(t.edges(), function (n) {
    if (e.hasNode(n.v) !== e.hasNode(n.w)) return Rs(t, n);
  });
}
function cz(e, t, n) {
  Ns.forEach(e.nodes(), function (r) {
    t.node(r).rank += n;
  });
}
var En = ve,
  fz = K2,
  dz = mu.slack,
  hz = mu.longestPath,
  pz = Bt.alg.preorder,
  gz = Bt.alg.postorder,
  vz = ut.simplify,
  mz = qr;
qr.initLowLimValues = Vv;
qr.initCutValues = Hv;
qr.calcCutValue = Y2;
qr.leaveEdge = Q2;
qr.enterEdge = Z2;
qr.exchangeEdges = J2;
function qr(e) {
  (e = vz(e)), hz(e);
  var t = fz(e);
  Vv(t), Hv(t, e);
  for (var n, r; (n = Q2(t)); ) (r = Z2(t, e, n)), J2(t, e, n, r);
}
function Hv(e, t) {
  var n = gz(e, e.nodes());
  (n = n.slice(0, n.length - 1)),
    En.forEach(n, function (r) {
      yz(e, t, r);
    });
}
function yz(e, t, n) {
  var r = e.node(n),
    i = r.parent;
  e.edge(n, i).cutvalue = Y2(e, t, n);
}
function Y2(e, t, n) {
  var r = e.node(n),
    i = r.parent,
    o = !0,
    a = t.edge(n, i),
    s = 0;
  return (
    a || ((o = !1), (a = t.edge(i, n))),
    (s = a.weight),
    En.forEach(t.nodeEdges(n), function (u) {
      var l = u.v === n,
        c = l ? u.w : u.v;
      if (c !== i) {
        var f = l === o,
          d = t.edge(u).weight;
        if (((s += f ? d : -d), wz(e, n, c))) {
          var h = e.edge(n, c).cutvalue;
          s += f ? -h : h;
        }
      }
    }),
    s
  );
}
function Vv(e, t) {
  arguments.length < 2 && (t = e.nodes()[0]), X2(e, {}, 1, t);
}
function X2(e, t, n, r, i) {
  var o = n,
    a = e.node(r);
  return (
    (t[r] = !0),
    En.forEach(e.neighbors(r), function (s) {
      En.has(t, s) || (n = X2(e, t, n, s, r));
    }),
    (a.low = o),
    (a.lim = n++),
    i ? (a.parent = i) : delete a.parent,
    n
  );
}
function Q2(e) {
  return En.find(e.edges(), function (t) {
    return e.edge(t).cutvalue < 0;
  });
}
function Z2(e, t, n) {
  var r = n.v,
    i = n.w;
  t.hasEdge(r, i) || ((r = n.w), (i = n.v));
  var o = e.node(r),
    a = e.node(i),
    s = o,
    u = !1;
  o.lim > a.lim && ((s = a), (u = !0));
  var l = En.filter(t.edges(), function (c) {
    return u === Fx(e, e.node(c.v), s) && u !== Fx(e, e.node(c.w), s);
  });
  return En.minBy(l, function (c) {
    return dz(t, c);
  });
}
function J2(e, t, n, r) {
  var i = n.v,
    o = n.w;
  e.removeEdge(i, o), e.setEdge(r.v, r.w, {}), Vv(e), Hv(e, t), _z(e, t);
}
function _z(e, t) {
  var n = En.find(e.nodes(), function (i) {
      return !t.node(i).parent;
    }),
    r = pz(e, n);
  (r = r.slice(1)),
    En.forEach(r, function (i) {
      var o = e.node(i).parent,
        a = t.edge(i, o),
        s = !1;
      a || ((a = t.edge(o, i)), (s = !0)),
        (t.node(i).rank = t.node(o).rank + (s ? a.minlen : -a.minlen));
    });
}
function wz(e, t, n) {
  return e.hasEdge(t, n);
}
function Fx(e, t, n) {
  return n.low <= t.lim && t.lim <= n.lim;
}
var xz = mu,
  eC = xz.longestPath,
  Sz = K2,
  Ez = mz,
  bz = kz;
function kz(e) {
  switch (e.graph().ranker) {
    case "network-simplex":
      jx(e);
      break;
    case "tight-tree":
      Nz(e);
      break;
    case "longest-path":
      Cz(e);
      break;
    default:
      jx(e);
  }
}
var Cz = eC;
function Nz(e) {
  eC(e), Sz(e);
}
function jx(e) {
  Ez(e);
}
var fg = ve,
  Rz = Tz;
function Tz(e) {
  var t = Az(e);
  fg.forEach(e.graph().dummyChains, function (n) {
    for (
      var r = e.node(n),
        i = r.edgeObj,
        o = Iz(e, t, i.v, i.w),
        a = o.path,
        s = o.lca,
        u = 0,
        l = a[u],
        c = !0;
      n !== i.w;

    ) {
      if (((r = e.node(n)), c)) {
        for (; (l = a[u]) !== s && e.node(l).maxRank < r.rank; ) u++;
        l === s && (c = !1);
      }
      if (!c) {
        for (; u < a.length - 1 && e.node((l = a[u + 1])).minRank <= r.rank; ) u++;
        l = a[u];
      }
      e.setParent(n, l), (n = e.successors(n)[0]);
    }
  });
}
function Iz(e, t, n, r) {
  var i = [],
    o = [],
    a = Math.min(t[n].low, t[r].low),
    s = Math.max(t[n].lim, t[r].lim),
    u,
    l;
  u = n;
  do (u = e.parent(u)), i.push(u);
  while (u && (t[u].low > a || s > t[u].lim));
  for (l = u, u = r; (u = e.parent(u)) !== l; ) o.push(u);
  return { path: i.concat(o.reverse()), lca: l };
}
function Az(e) {
  var t = {},
    n = 0;
  function r(i) {
    var o = n;
    fg.forEach(e.children(i), r), (t[i] = { low: o, lim: n++ });
  }
  return fg.forEach(e.children(), r), t;
}
var pn = ve,
  dg = ut,
  Mz = { run: Pz, cleanup: Lz };
function Pz(e) {
  var t = dg.addDummyNode(e, "root", {}, "_root"),
    n = qz(e),
    r = pn.max(pn.values(n)) - 1,
    i = 2 * r + 1;
  (e.graph().nestingRoot = t),
    pn.forEach(e.edges(), function (a) {
      e.edge(a).minlen *= i;
    });
  var o = Oz(e) + 1;
  pn.forEach(e.children(), function (a) {
    tC(e, t, i, o, r, n, a);
  }),
    (e.graph().nodeRankFactor = i);
}
function tC(e, t, n, r, i, o, a) {
  var s = e.children(a);
  if (!s.length) {
    a !== t && e.setEdge(t, a, { weight: 0, minlen: n });
    return;
  }
  var u = dg.addBorderNode(e, "_bt"),
    l = dg.addBorderNode(e, "_bb"),
    c = e.node(a);
  e.setParent(u, a),
    (c.borderTop = u),
    e.setParent(l, a),
    (c.borderBottom = l),
    pn.forEach(s, function (f) {
      tC(e, t, n, r, i, o, f);
      var d = e.node(f),
        h = d.borderTop ? d.borderTop : f,
        m = d.borderBottom ? d.borderBottom : f,
        v = d.borderTop ? r : 2 * r,
        w = h !== m ? 1 : i - o[a] + 1;
      e.setEdge(u, h, { weight: v, minlen: w, nestingEdge: !0 }),
        e.setEdge(m, l, { weight: v, minlen: w, nestingEdge: !0 });
    }),
    e.parent(a) || e.setEdge(t, u, { weight: 0, minlen: i + o[a] });
}
function qz(e) {
  var t = {};
  function n(r, i) {
    var o = e.children(r);
    o &&
      o.length &&
      pn.forEach(o, function (a) {
        n(a, i + 1);
      }),
      (t[r] = i);
  }
  return (
    pn.forEach(e.children(), function (r) {
      n(r, 1);
    }),
    t
  );
}
function Oz(e) {
  return pn.reduce(
    e.edges(),
    function (t, n) {
      return t + e.edge(n).weight;
    },
    0
  );
}
function Lz(e) {
  var t = e.graph();
  e.removeNode(t.nestingRoot),
    delete t.nestingRoot,
    pn.forEach(e.edges(), function (n) {
      var r = e.edge(n);
      r.nestingEdge && e.removeEdge(n);
    });
}
var Wh = ve,
  zz = ut,
  $z = Dz;
function Dz(e) {
  function t(n) {
    var r = e.children(n),
      i = e.node(n);
    if ((r.length && Wh.forEach(r, t), Wh.has(i, "minRank"))) {
      (i.borderLeft = []), (i.borderRight = []);
      for (var o = i.minRank, a = i.maxRank + 1; o < a; ++o)
        Bx(e, "borderLeft", "_bl", n, i, o), Bx(e, "borderRight", "_br", n, i, o);
    }
  }
  Wh.forEach(e.children(), t);
}
function Bx(e, t, n, r, i, o) {
  var a = { width: 0, height: 0, rank: o, borderType: t },
    s = i[t][o - 1],
    u = zz.addDummyNode(e, "border", a, n);
  (i[t][o] = u), e.setParent(u, r), s && e.setEdge(s, u, { weight: 1 });
}
var Yt = ve,
  Fz = { adjust: jz, undo: Bz };
function jz(e) {
  var t = e.graph().rankdir.toLowerCase();
  (t === "lr" || t === "rl") && nC(e);
}
function Bz(e) {
  var t = e.graph().rankdir.toLowerCase();
  (t === "bt" || t === "rl") && Hz(e), (t === "lr" || t === "rl") && (Vz(e), nC(e));
}
function nC(e) {
  Yt.forEach(e.nodes(), function (t) {
    Hx(e.node(t));
  }),
    Yt.forEach(e.edges(), function (t) {
      Hx(e.edge(t));
    });
}
function Hx(e) {
  var t = e.width;
  (e.width = e.height), (e.height = t);
}
function Hz(e) {
  Yt.forEach(e.nodes(), function (t) {
    Kh(e.node(t));
  }),
    Yt.forEach(e.edges(), function (t) {
      var n = e.edge(t);
      Yt.forEach(n.points, Kh), Yt.has(n, "y") && Kh(n);
    });
}
function Kh(e) {
  e.y = -e.y;
}
function Vz(e) {
  Yt.forEach(e.nodes(), function (t) {
    Yh(e.node(t));
  }),
    Yt.forEach(e.edges(), function (t) {
      var n = e.edge(t);
      Yt.forEach(n.points, Yh), Yt.has(n, "x") && Yh(n);
    });
}
function Yh(e) {
  var t = e.x;
  (e.x = e.y), (e.y = t);
}
var an = ve,
  Uz = Gz;
function Gz(e) {
  var t = {},
    n = an.filter(e.nodes(), function (s) {
      return !e.children(s).length;
    }),
    r = an.max(
      an.map(n, function (s) {
        return e.node(s).rank;
      })
    ),
    i = an.map(an.range(r + 1), function () {
      return [];
    });
  function o(s) {
    if (!an.has(t, s)) {
      t[s] = !0;
      var u = e.node(s);
      i[u.rank].push(s), an.forEach(e.successors(s), o);
    }
  }
  var a = an.sortBy(n, function (s) {
    return e.node(s).rank;
  });
  return an.forEach(a, o), i;
}
var In = ve,
  Wz = Kz;
function Kz(e, t) {
  for (var n = 0, r = 1; r < t.length; ++r) n += Yz(e, t[r - 1], t[r]);
  return n;
}
function Yz(e, t, n) {
  for (
    var r = In.zipObject(
        n,
        In.map(n, function (l, c) {
          return c;
        })
      ),
      i = In.flatten(
        In.map(t, function (l) {
          return In.sortBy(
            In.map(e.outEdges(l), function (c) {
              return { pos: r[c.w], weight: e.edge(c).weight };
            }),
            "pos"
          );
        }),
        !0
      ),
      o = 1;
    o < n.length;

  )
    o <<= 1;
  var a = 2 * o - 1;
  o -= 1;
  var s = In.map(new Array(a), function () {
      return 0;
    }),
    u = 0;
  return (
    In.forEach(
      i.forEach(function (l) {
        var c = l.pos + o;
        s[c] += l.weight;
        for (var f = 0; c > 0; ) c % 2 && (f += s[c + 1]), (c = (c - 1) >> 1), (s[c] += l.weight);
        u += l.weight * f;
      })
    ),
    u
  );
}
var Vx = ve,
  Xz = Qz;
function Qz(e, t) {
  return Vx.map(t, function (n) {
    var r = e.inEdges(n);
    if (r.length) {
      var i = Vx.reduce(
        r,
        function (o, a) {
          var s = e.edge(a),
            u = e.node(a.v);
          return { sum: o.sum + s.weight * u.order, weight: o.weight + s.weight };
        },
        { sum: 0, weight: 0 }
      );
      return { v: n, barycenter: i.sum / i.weight, weight: i.weight };
    } else return { v: n };
  });
}
var ft = ve,
  Zz = Jz;
function Jz(e, t) {
  var n = {};
  ft.forEach(e, function (i, o) {
    var a = (n[i.v] = { indegree: 0, in: [], out: [], vs: [i.v], i: o });
    ft.isUndefined(i.barycenter) || ((a.barycenter = i.barycenter), (a.weight = i.weight));
  }),
    ft.forEach(t.edges(), function (i) {
      var o = n[i.v],
        a = n[i.w];
      !ft.isUndefined(o) && !ft.isUndefined(a) && (a.indegree++, o.out.push(n[i.w]));
    });
  var r = ft.filter(n, function (i) {
    return !i.indegree;
  });
  return e$(r);
}
function e$(e) {
  var t = [];
  function n(o) {
    return function (a) {
      a.merged ||
        ((ft.isUndefined(a.barycenter) ||
          ft.isUndefined(o.barycenter) ||
          a.barycenter >= o.barycenter) &&
          t$(o, a));
    };
  }
  function r(o) {
    return function (a) {
      a.in.push(o), --a.indegree === 0 && e.push(a);
    };
  }
  for (; e.length; ) {
    var i = e.pop();
    t.push(i), ft.forEach(i.in.reverse(), n(i)), ft.forEach(i.out, r(i));
  }
  return ft.map(
    ft.filter(t, function (o) {
      return !o.merged;
    }),
    function (o) {
      return ft.pick(o, ["vs", "i", "barycenter", "weight"]);
    }
  );
}
function t$(e, t) {
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
var ro = ve,
  n$ = ut,
  r$ = i$;
function i$(e, t) {
  var n = n$.partition(e, function (c) {
      return ro.has(c, "barycenter");
    }),
    r = n.lhs,
    i = ro.sortBy(n.rhs, function (c) {
      return -c.i;
    }),
    o = [],
    a = 0,
    s = 0,
    u = 0;
  r.sort(o$(!!t)),
    (u = Ux(o, i, u)),
    ro.forEach(r, function (c) {
      (u += c.vs.length),
        o.push(c.vs),
        (a += c.barycenter * c.weight),
        (s += c.weight),
        (u = Ux(o, i, u));
    });
  var l = { vs: ro.flatten(o, !0) };
  return s && ((l.barycenter = a / s), (l.weight = s)), l;
}
function Ux(e, t, n) {
  for (var r; t.length && (r = ro.last(t)).i <= n; ) t.pop(), e.push(r.vs), n++;
  return n;
}
function o$(e) {
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
var Fn = ve,
  a$ = Xz,
  s$ = Zz,
  u$ = r$,
  l$ = rC;
function rC(e, t, n, r) {
  var i = e.children(t),
    o = e.node(t),
    a = o ? o.borderLeft : void 0,
    s = o ? o.borderRight : void 0,
    u = {};
  a &&
    (i = Fn.filter(i, function (m) {
      return m !== a && m !== s;
    }));
  var l = a$(e, i);
  Fn.forEach(l, function (m) {
    if (e.children(m.v).length) {
      var v = rC(e, m.v, n, r);
      (u[m.v] = v), Fn.has(v, "barycenter") && f$(m, v);
    }
  });
  var c = s$(l, n);
  c$(c, u);
  var f = u$(c, r);
  if (a && ((f.vs = Fn.flatten([a, f.vs, s], !0)), e.predecessors(a).length)) {
    var d = e.node(e.predecessors(a)[0]),
      h = e.node(e.predecessors(s)[0]);
    Fn.has(f, "barycenter") || ((f.barycenter = 0), (f.weight = 0)),
      (f.barycenter = (f.barycenter * f.weight + d.order + h.order) / (f.weight + 2)),
      (f.weight += 2);
  }
  return f;
}
function c$(e, t) {
  Fn.forEach(e, function (n) {
    n.vs = Fn.flatten(
      n.vs.map(function (r) {
        return t[r] ? t[r].vs : r;
      }),
      !0
    );
  });
}
function f$(e, t) {
  Fn.isUndefined(e.barycenter)
    ? ((e.barycenter = t.barycenter), (e.weight = t.weight))
    : ((e.barycenter = (e.barycenter * e.weight + t.barycenter * t.weight) / (e.weight + t.weight)),
      (e.weight += t.weight));
}
var io = ve,
  d$ = Bt.Graph,
  h$ = p$;
function p$(e, t, n) {
  var r = g$(e),
    i = new d$({ compound: !0 }).setGraph({ root: r }).setDefaultNodeLabel(function (o) {
      return e.node(o);
    });
  return (
    io.forEach(e.nodes(), function (o) {
      var a = e.node(o),
        s = e.parent(o);
      (a.rank === t || (a.minRank <= t && t <= a.maxRank)) &&
        (i.setNode(o),
        i.setParent(o, s || r),
        io.forEach(e[n](o), function (u) {
          var l = u.v === o ? u.w : u.v,
            c = i.edge(l, o),
            f = io.isUndefined(c) ? 0 : c.weight;
          i.setEdge(l, o, { weight: e.edge(u).weight + f });
        }),
        io.has(a, "minRank") &&
          i.setNode(o, { borderLeft: a.borderLeft[t], borderRight: a.borderRight[t] }));
    }),
    i
  );
}
function g$(e) {
  for (var t; e.hasNode((t = io.uniqueId("_root"))); );
  return t;
}
var v$ = ve,
  m$ = y$;
function y$(e, t, n) {
  var r = {},
    i;
  v$.forEach(n, function (o) {
    for (var a = e.parent(o), s, u; a; ) {
      if (((s = e.parent(a)), s ? ((u = r[s]), (r[s] = a)) : ((u = i), (i = a)), u && u !== a)) {
        t.setEdge(u, a);
        return;
      }
      a = s;
    }
  });
}
var Zn = ve,
  _$ = Uz,
  w$ = Wz,
  x$ = l$,
  S$ = h$,
  E$ = m$,
  b$ = Bt.Graph,
  Gx = ut,
  k$ = C$;
function C$(e) {
  var t = Gx.maxRank(e),
    n = Wx(e, Zn.range(1, t + 1), "inEdges"),
    r = Wx(e, Zn.range(t - 1, -1, -1), "outEdges"),
    i = _$(e);
  Kx(e, i);
  for (var o = Number.POSITIVE_INFINITY, a, s = 0, u = 0; u < 4; ++s, ++u) {
    N$(s % 2 ? n : r, s % 4 >= 2), (i = Gx.buildLayerMatrix(e));
    var l = w$(e, i);
    l < o && ((u = 0), (a = Zn.cloneDeep(i)), (o = l));
  }
  Kx(e, a);
}
function Wx(e, t, n) {
  return Zn.map(t, function (r) {
    return S$(e, r, n);
  });
}
function N$(e, t) {
  var n = new b$();
  Zn.forEach(e, function (r) {
    var i = r.graph().root,
      o = x$(r, i, n, t);
    Zn.forEach(o.vs, function (a, s) {
      r.node(a).order = s;
    }),
      E$(r, n, o.vs);
  });
}
function Kx(e, t) {
  Zn.forEach(t, function (n) {
    Zn.forEach(n, function (r, i) {
      e.node(r).order = i;
    });
  });
}
var Z = ve,
  R$ = Bt.Graph,
  T$ = ut,
  I$ = { positionX: j$ };
function A$(e, t) {
  var n = {};
  function r(i, o) {
    var a = 0,
      s = 0,
      u = i.length,
      l = Z.last(o);
    return (
      Z.forEach(o, function (c, f) {
        var d = P$(e, c),
          h = d ? e.node(d).order : u;
        (d || c === l) &&
          (Z.forEach(o.slice(s, f + 1), function (m) {
            Z.forEach(e.predecessors(m), function (v) {
              var w = e.node(v),
                p = w.order;
              (p < a || h < p) && !(w.dummy && e.node(m).dummy) && iC(n, v, m);
            });
          }),
          (s = f + 1),
          (a = h));
      }),
      o
    );
  }
  return Z.reduce(t, r), n;
}
function M$(e, t) {
  var n = {};
  function r(o, a, s, u, l) {
    var c;
    Z.forEach(Z.range(a, s), function (f) {
      (c = o[f]),
        e.node(c).dummy &&
          Z.forEach(e.predecessors(c), function (d) {
            var h = e.node(d);
            h.dummy && (h.order < u || h.order > l) && iC(n, d, c);
          });
    });
  }
  function i(o, a) {
    var s = -1,
      u,
      l = 0;
    return (
      Z.forEach(a, function (c, f) {
        if (e.node(c).dummy === "border") {
          var d = e.predecessors(c);
          d.length && ((u = e.node(d[0]).order), r(a, l, f, s, u), (l = f), (s = u));
        }
        r(a, l, a.length, u, o.length);
      }),
      a
    );
  }
  return Z.reduce(t, i), n;
}
function P$(e, t) {
  if (e.node(t).dummy)
    return Z.find(e.predecessors(t), function (n) {
      return e.node(n).dummy;
    });
}
function iC(e, t, n) {
  if (t > n) {
    var r = t;
    (t = n), (n = r);
  }
  var i = e[t];
  i || (e[t] = i = {}), (i[n] = !0);
}
function q$(e, t, n) {
  if (t > n) {
    var r = t;
    (t = n), (n = r);
  }
  return Z.has(e[t], n);
}
function O$(e, t, n, r) {
  var i = {},
    o = {},
    a = {};
  return (
    Z.forEach(t, function (s) {
      Z.forEach(s, function (u, l) {
        (i[u] = u), (o[u] = u), (a[u] = l);
      });
    }),
    Z.forEach(t, function (s) {
      var u = -1;
      Z.forEach(s, function (l) {
        var c = r(l);
        if (c.length) {
          c = Z.sortBy(c, function (v) {
            return a[v];
          });
          for (var f = (c.length - 1) / 2, d = Math.floor(f), h = Math.ceil(f); d <= h; ++d) {
            var m = c[d];
            o[l] === l &&
              u < a[m] &&
              !q$(n, l, m) &&
              ((o[m] = l), (o[l] = i[l] = i[m]), (u = a[m]));
          }
        }
      });
    }),
    { root: i, align: o }
  );
}
function L$(e, t, n, r, i) {
  var o = {},
    a = z$(e, t, n, i),
    s = i ? "borderLeft" : "borderRight";
  function u(f, d) {
    for (var h = a.nodes(), m = h.pop(), v = {}; m; )
      v[m] ? f(m) : ((v[m] = !0), h.push(m), (h = h.concat(d(m)))), (m = h.pop());
  }
  function l(f) {
    o[f] = a.inEdges(f).reduce(function (d, h) {
      return Math.max(d, o[h.v] + a.edge(h));
    }, 0);
  }
  function c(f) {
    var d = a.outEdges(f).reduce(function (m, v) {
        return Math.min(m, o[v.w] - a.edge(v));
      }, Number.POSITIVE_INFINITY),
      h = e.node(f);
    d !== Number.POSITIVE_INFINITY && h.borderType !== s && (o[f] = Math.max(o[f], d));
  }
  return (
    u(l, a.predecessors.bind(a)),
    u(c, a.successors.bind(a)),
    Z.forEach(r, function (f) {
      o[f] = o[n[f]];
    }),
    o
  );
}
function z$(e, t, n, r) {
  var i = new R$(),
    o = e.graph(),
    a = B$(o.nodesep, o.edgesep, r);
  return (
    Z.forEach(t, function (s) {
      var u;
      Z.forEach(s, function (l) {
        var c = n[l];
        if ((i.setNode(c), u)) {
          var f = n[u],
            d = i.edge(f, c);
          i.setEdge(f, c, Math.max(a(e, l, u), d || 0));
        }
        u = l;
      });
    }),
    i
  );
}
function $$(e, t) {
  return Z.minBy(Z.values(t), function (n) {
    var r = Number.NEGATIVE_INFINITY,
      i = Number.POSITIVE_INFINITY;
    return (
      Z.forIn(n, function (o, a) {
        var s = H$(e, a) / 2;
        (r = Math.max(o + s, r)), (i = Math.min(o - s, i));
      }),
      r - i
    );
  });
}
function D$(e, t) {
  var n = Z.values(t),
    r = Z.min(n),
    i = Z.max(n);
  Z.forEach(["u", "d"], function (o) {
    Z.forEach(["l", "r"], function (a) {
      var s = o + a,
        u = e[s],
        l;
      if (u !== t) {
        var c = Z.values(u);
        (l = a === "l" ? r - Z.min(c) : i - Z.max(c)),
          l &&
            (e[s] = Z.mapValues(u, function (f) {
              return f + l;
            }));
      }
    });
  });
}
function F$(e, t) {
  return Z.mapValues(e.ul, function (n, r) {
    if (t) return e[t.toLowerCase()][r];
    var i = Z.sortBy(Z.map(e, r));
    return (i[1] + i[2]) / 2;
  });
}
function j$(e) {
  var t = T$.buildLayerMatrix(e),
    n = Z.merge(A$(e, t), M$(e, t)),
    r = {},
    i;
  Z.forEach(["u", "d"], function (a) {
    (i = a === "u" ? t : Z.values(t).reverse()),
      Z.forEach(["l", "r"], function (s) {
        s === "r" &&
          (i = Z.map(i, function (f) {
            return Z.values(f).reverse();
          }));
        var u = (a === "u" ? e.predecessors : e.successors).bind(e),
          l = O$(e, i, n, u),
          c = L$(e, i, l.root, l.align, s === "r");
        s === "r" &&
          (c = Z.mapValues(c, function (f) {
            return -f;
          })),
          (r[a + s] = c);
      });
  });
  var o = $$(e, r);
  return D$(r, o), F$(r, e.graph().align);
}
function B$(e, t, n) {
  return function (r, i, o) {
    var a = r.node(i),
      s = r.node(o),
      u = 0,
      l;
    if (((u += a.width / 2), Z.has(a, "labelpos")))
      switch (a.labelpos.toLowerCase()) {
        case "l":
          l = -a.width / 2;
          break;
        case "r":
          l = a.width / 2;
          break;
      }
    if (
      (l && (u += n ? l : -l),
      (l = 0),
      (u += (a.dummy ? t : e) / 2),
      (u += (s.dummy ? t : e) / 2),
      (u += s.width / 2),
      Z.has(s, "labelpos"))
    )
      switch (s.labelpos.toLowerCase()) {
        case "l":
          l = s.width / 2;
          break;
        case "r":
          l = -s.width / 2;
          break;
      }
    return l && (u += n ? l : -l), (l = 0), u;
  };
}
function H$(e, t) {
  return e.node(t).width;
}
var oo = ve,
  oC = ut,
  V$ = I$.positionX,
  U$ = G$;
function G$(e) {
  (e = oC.asNonCompoundGraph(e)),
    W$(e),
    oo.forEach(V$(e), function (t, n) {
      e.node(n).x = t;
    });
}
function W$(e) {
  var t = oC.buildLayerMatrix(e),
    n = e.graph().ranksep,
    r = 0;
  oo.forEach(t, function (i) {
    var o = oo.max(
      oo.map(i, function (a) {
        return e.node(a).height;
      })
    );
    oo.forEach(i, function (a) {
      e.node(a).y = r + o / 2;
    }),
      (r += o + n);
  });
}
var te = ve,
  Yx = zL,
  Xx = ez,
  K$ = bz,
  Y$ = ut.normalizeRanks,
  X$ = Rz,
  Q$ = ut.removeEmptyRanks,
  Qx = Mz,
  Z$ = $z,
  Zx = Fz,
  J$ = k$,
  eD = U$,
  tr = ut,
  tD = Bt.Graph,
  nD = rD;
function rD(e, t) {
  var n = t && t.debugTiming ? tr.time : tr.notime;
  n("layout", function () {
    var r = n("  buildLayoutGraph", function () {
      return pD(e);
    });
    n("  runLayout", function () {
      iD(r, n);
    }),
      n("  updateInputGraph", function () {
        oD(e, r);
      });
  });
}
function iD(e, t) {
  t("    makeSpaceForEdgeLabels", function () {
    gD(e);
  }),
    t("    removeSelfEdges", function () {
      bD(e);
    }),
    t("    acyclic", function () {
      Yx.run(e);
    }),
    t("    nestingGraph.run", function () {
      Qx.run(e);
    }),
    t("    rank", function () {
      K$(tr.asNonCompoundGraph(e));
    }),
    t("    injectEdgeLabelProxies", function () {
      vD(e);
    }),
    t("    removeEmptyRanks", function () {
      Q$(e);
    }),
    t("    nestingGraph.cleanup", function () {
      Qx.cleanup(e);
    }),
    t("    normalizeRanks", function () {
      Y$(e);
    }),
    t("    assignRankMinMax", function () {
      mD(e);
    }),
    t("    removeEdgeLabelProxies", function () {
      yD(e);
    }),
    t("    normalize.run", function () {
      Xx.run(e);
    }),
    t("    parentDummyChains", function () {
      X$(e);
    }),
    t("    addBorderSegments", function () {
      Z$(e);
    }),
    t("    order", function () {
      J$(e);
    }),
    t("    insertSelfEdges", function () {
      kD(e);
    }),
    t("    adjustCoordinateSystem", function () {
      Zx.adjust(e);
    }),
    t("    position", function () {
      eD(e);
    }),
    t("    positionSelfEdges", function () {
      CD(e);
    }),
    t("    removeBorderNodes", function () {
      ED(e);
    }),
    t("    normalize.undo", function () {
      Xx.undo(e);
    }),
    t("    fixupEdgeLabelCoords", function () {
      xD(e);
    }),
    t("    undoCoordinateSystem", function () {
      Zx.undo(e);
    }),
    t("    translateGraph", function () {
      _D(e);
    }),
    t("    assignNodeIntersects", function () {
      wD(e);
    }),
    t("    reversePoints", function () {
      SD(e);
    }),
    t("    acyclic.undo", function () {
      Yx.undo(e);
    });
}
function oD(e, t) {
  te.forEach(e.nodes(), function (n) {
    var r = e.node(n),
      i = t.node(n);
    r &&
      ((r.x = i.x),
      (r.y = i.y),
      t.children(n).length && ((r.width = i.width), (r.height = i.height)));
  }),
    te.forEach(e.edges(), function (n) {
      var r = e.edge(n),
        i = t.edge(n);
      (r.points = i.points), te.has(i, "x") && ((r.x = i.x), (r.y = i.y));
    }),
    (e.graph().width = t.graph().width),
    (e.graph().height = t.graph().height);
}
var aD = ["nodesep", "edgesep", "ranksep", "marginx", "marginy"],
  sD = { ranksep: 50, edgesep: 20, nodesep: 50, rankdir: "tb" },
  uD = ["acyclicer", "ranker", "rankdir", "align"],
  lD = ["width", "height"],
  cD = { width: 0, height: 0 },
  fD = ["minlen", "weight", "width", "height", "labeloffset"],
  dD = { minlen: 1, weight: 1, width: 0, height: 0, labeloffset: 10, labelpos: "r" },
  hD = ["labelpos"];
function pD(e) {
  var t = new tD({ multigraph: !0, compound: !0 }),
    n = Qh(e.graph());
  return (
    t.setGraph(te.merge({}, sD, Xh(n, aD), te.pick(n, uD))),
    te.forEach(e.nodes(), function (r) {
      var i = Qh(e.node(r));
      t.setNode(r, te.defaults(Xh(i, lD), cD)), t.setParent(r, e.parent(r));
    }),
    te.forEach(e.edges(), function (r) {
      var i = Qh(e.edge(r));
      t.setEdge(r, te.merge({}, dD, Xh(i, fD), te.pick(i, hD)));
    }),
    t
  );
}
function gD(e) {
  var t = e.graph();
  (t.ranksep /= 2),
    te.forEach(e.edges(), function (n) {
      var r = e.edge(n);
      (r.minlen *= 2),
        r.labelpos.toLowerCase() !== "c" &&
          (t.rankdir === "TB" || t.rankdir === "BT"
            ? (r.width += r.labeloffset)
            : (r.height += r.labeloffset));
    });
}
function vD(e) {
  te.forEach(e.edges(), function (t) {
    var n = e.edge(t);
    if (n.width && n.height) {
      var r = e.node(t.v),
        i = e.node(t.w),
        o = { rank: (i.rank - r.rank) / 2 + r.rank, e: t };
      tr.addDummyNode(e, "edge-proxy", o, "_ep");
    }
  });
}
function mD(e) {
  var t = 0;
  te.forEach(e.nodes(), function (n) {
    var r = e.node(n);
    r.borderTop &&
      ((r.minRank = e.node(r.borderTop).rank),
      (r.maxRank = e.node(r.borderBottom).rank),
      (t = te.max(t, r.maxRank)));
  }),
    (e.graph().maxRank = t);
}
function yD(e) {
  te.forEach(e.nodes(), function (t) {
    var n = e.node(t);
    n.dummy === "edge-proxy" && ((e.edge(n.e).labelRank = n.rank), e.removeNode(t));
  });
}
function _D(e) {
  var t = Number.POSITIVE_INFINITY,
    n = 0,
    r = Number.POSITIVE_INFINITY,
    i = 0,
    o = e.graph(),
    a = o.marginx || 0,
    s = o.marginy || 0;
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
  te.forEach(e.nodes(), function (l) {
    u(e.node(l));
  }),
    te.forEach(e.edges(), function (l) {
      var c = e.edge(l);
      te.has(c, "x") && u(c);
    }),
    (t -= a),
    (r -= s),
    te.forEach(e.nodes(), function (l) {
      var c = e.node(l);
      (c.x -= t), (c.y -= r);
    }),
    te.forEach(e.edges(), function (l) {
      var c = e.edge(l);
      te.forEach(c.points, function (f) {
        (f.x -= t), (f.y -= r);
      }),
        te.has(c, "x") && (c.x -= t),
        te.has(c, "y") && (c.y -= r);
    }),
    (o.width = n - t + a),
    (o.height = i - r + s);
}
function wD(e) {
  te.forEach(e.edges(), function (t) {
    var n = e.edge(t),
      r = e.node(t.v),
      i = e.node(t.w),
      o,
      a;
    n.points
      ? ((o = n.points[0]), (a = n.points[n.points.length - 1]))
      : ((n.points = []), (o = i), (a = r)),
      n.points.unshift(tr.intersectRect(r, o)),
      n.points.push(tr.intersectRect(i, a));
  });
}
function xD(e) {
  te.forEach(e.edges(), function (t) {
    var n = e.edge(t);
    if (te.has(n, "x"))
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
function SD(e) {
  te.forEach(e.edges(), function (t) {
    var n = e.edge(t);
    n.reversed && n.points.reverse();
  });
}
function ED(e) {
  te.forEach(e.nodes(), function (t) {
    if (e.children(t).length) {
      var n = e.node(t),
        r = e.node(n.borderTop),
        i = e.node(n.borderBottom),
        o = e.node(te.last(n.borderLeft)),
        a = e.node(te.last(n.borderRight));
      (n.width = Math.abs(a.x - o.x)),
        (n.height = Math.abs(i.y - r.y)),
        (n.x = o.x + n.width / 2),
        (n.y = r.y + n.height / 2);
    }
  }),
    te.forEach(e.nodes(), function (t) {
      e.node(t).dummy === "border" && e.removeNode(t);
    });
}
function bD(e) {
  te.forEach(e.edges(), function (t) {
    if (t.v === t.w) {
      var n = e.node(t.v);
      n.selfEdges || (n.selfEdges = []),
        n.selfEdges.push({ e: t, label: e.edge(t) }),
        e.removeEdge(t);
    }
  });
}
function kD(e) {
  var t = tr.buildLayerMatrix(e);
  te.forEach(t, function (n) {
    var r = 0;
    te.forEach(n, function (i, o) {
      var a = e.node(i);
      (a.order = o + r),
        te.forEach(a.selfEdges, function (s) {
          tr.addDummyNode(
            e,
            "selfedge",
            {
              width: s.label.width,
              height: s.label.height,
              rank: a.rank,
              order: o + ++r,
              e: s.e,
              label: s.label,
            },
            "_se"
          );
        }),
        delete a.selfEdges;
    });
  });
}
function CD(e) {
  te.forEach(e.nodes(), function (t) {
    var n = e.node(t);
    if (n.dummy === "selfedge") {
      var r = e.node(n.e.v),
        i = r.x + r.width / 2,
        o = r.y,
        a = n.x - i,
        s = r.height / 2;
      e.setEdge(n.e, n.label),
        e.removeNode(t),
        (n.label.points = [
          { x: i + (2 * a) / 3, y: o - s },
          { x: i + (5 * a) / 6, y: o - s },
          { x: i + a, y: o },
          { x: i + (5 * a) / 6, y: o + s },
          { x: i + (2 * a) / 3, y: o + s },
        ]),
        (n.label.x = n.x),
        (n.label.y = n.y);
    }
  });
}
function Xh(e, t) {
  return te.mapValues(te.pick(e, t), Number);
}
function Qh(e) {
  var t = {};
  return (
    te.forEach(e, function (n, r) {
      t[r.toLowerCase()] = n;
    }),
    t
  );
}
var Ta = ve,
  ND = ut,
  RD = Bt.Graph,
  TD = { debugOrdering: ID };
function ID(e) {
  var t = ND.buildLayerMatrix(e),
    n = new RD({ compound: !0, multigraph: !0 }).setGraph({});
  return (
    Ta.forEach(e.nodes(), function (r) {
      n.setNode(r, { label: r }), n.setParent(r, "layer" + e.node(r).rank);
    }),
    Ta.forEach(e.edges(), function (r) {
      n.setEdge(r.v, r.w, {}, r.name);
    }),
    Ta.forEach(t, function (r, i) {
      var o = "layer" + i;
      n.setNode(o, { rank: "same" }),
        Ta.reduce(r, function (a, s) {
          return n.setEdge(a, s, { style: "invis" }), s;
        });
    }),
    n
  );
}
var AD = "0.8.5",
  aC = {
    graphlib: Bt,
    layout: nD,
    debug: TD,
    util: { time: ut.time, notime: ut.notime },
    version: AD,
  };
const Fr = new aC.graphlib.Graph();
Fr.setDefaultEdgeLabel(() => ({}));
const Zh = 200,
  Jh = 50,
  MD = (e, t) => {
    Fr.setGraph({ rankdir: "TB", nodesep: 25, ranksep: 60 });
    const n = [],
      r = [];
    function i(a) {
      if (!(!a || !a.id)) {
        if (
          (n.push({
            id: a.id,
            data: { label: a.key },
            position: { x: 0, y: 0 },
            style: {
              background: t.includes(a.id) ? "#3b82f6" : "#ffffff",
              color: t.includes(a.id) ? "white" : "black",
              border: "1px solid #9ca3af",
              borderRadius: "8px",
              width: Zh,
              height: Jh,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            },
          }),
          Fr.setNode(a.id, { width: Zh, height: Jh }),
          a.on)
        )
          for (const s in a.on) {
            const u = a.on[s],
              l = Array.isArray(u) ? u : [u];
            for (const c of l) {
              const f = typeof c == "string" ? c : c.target,
                d = f.startsWith(".")
                  ? a.id.substring(0, a.id.lastIndexOf(".")) + f
                  : `${e.id}.${f}`;
              r.push({
                id: `e-${a.id}-${d}-${s}`,
                source: a.id,
                target: d,
                label: s,
                markerEnd: { type: Fo.ArrowClosed },
              }),
                Fr.setEdge(a.id, d);
            }
          }
        if (a.states)
          for (const s in a.states) {
            const u = a.states[s];
            (u.id = `${a.id}.${s}`), (u.key = s), i(u);
          }
      }
    }
    const o = { ...e, id: e.id, key: e.id };
    return (
      i(o),
      aC.layout(Fr),
      n.forEach((a) => {
        const s = Fr.node(a.id);
        s && (a.position = { x: s.x - Zh / 2, y: s.y - Jh / 2 });
      }),
      { nodes: n, edges: r }
    );
  },
  PD = ({ machine: e, activeStateIds: t }) => {
    const { nodes: n, edges: r } = q.useMemo(() => MD(e.definition, t), [e.definition, t]);
    return !n || n.length === 0
      ? W.jsx("div", { className: "p-4 text-gray-500", children: "Could not render diagram." })
      : W.jsx("div", {
          className:
            "h-[600px] w-full bg-gray-50 dark:bg-gray-900 rounded-lg border dark:border-gray-700",
          children: W.jsxs(Fk, {
            nodes: n,
            edges: r,
            fitView: !0,
            proOptions: { hideAttribution: !0 },
            children: [
              W.jsx(Iq, {}),
              W.jsx(Eq, { nodeStrokeWidth: 3, zoomable: !0, pannable: !0 }),
              W.jsx(Lq, { color: "#aaa", gap: 16 }),
            ],
          }),
        });
  };
/**
 * @license lucide-react v0.303.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */ var qD = {
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
 * @license lucide-react v0.303.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */ const OD = (e) =>
    e
      .replace(/([a-z0-9])([A-Z])/g, "$1-$2")
      .toLowerCase()
      .trim(),
  sC = (e, t) => {
    const n = q.forwardRef(
      (
        {
          color: r = "currentColor",
          size: i = 24,
          strokeWidth: o = 2,
          absoluteStrokeWidth: a,
          className: s = "",
          children: u,
          ...l
        },
        c
      ) =>
        q.createElement(
          "svg",
          {
            ref: c,
            ...qD,
            width: i,
            height: i,
            stroke: r,
            strokeWidth: a ? (Number(o) * 24) / Number(i) : o,
            className: ["lucide", `lucide-${OD(e)}`, s].join(" "),
            ...l,
          },
          [...t.map(([f, d]) => q.createElement(f, d)), ...(Array.isArray(u) ? u : [u])]
        )
    );
    return (n.displayName = `${e}`), n;
  };
/**
 * @license lucide-react v0.303.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */ const LD = sC("Moon", [["path", { d: "M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z", key: "a7tn18" }]]);
/**
 * @license lucide-react v0.303.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */ const zD = sC("Sun", [
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
function uC(e) {
  var t,
    n,
    r = "";
  if (typeof e == "string" || typeof e == "number") r += e;
  else if (typeof e == "object")
    if (Array.isArray(e)) {
      var i = e.length;
      for (t = 0; t < i; t++) e[t] && (n = uC(e[t])) && (r && (r += " "), (r += n));
    } else for (n in e) e[n] && (r && (r += " "), (r += n));
  return r;
}
function $D() {
  for (var e, t, n = 0, r = "", i = arguments.length; n < i; n++)
    (e = arguments[n]) && (t = uC(e)) && (r && (r += " "), (r += t));
  return r;
}
const Uv = "-",
  DD = (e) => {
    const t = jD(e),
      { conflictingClassGroups: n, conflictingClassGroupModifiers: r } = e;
    return {
      getClassGroupId: (a) => {
        const s = a.split(Uv);
        return s[0] === "" && s.length !== 1 && s.shift(), lC(s, t) || FD(a);
      },
      getConflictingClassGroupIds: (a, s) => {
        const u = n[a] || [];
        return s && r[a] ? [...u, ...r[a]] : u;
      },
    };
  },
  lC = (e, t) => {
    var a;
    if (e.length === 0) return t.classGroupId;
    const n = e[0],
      r = t.nextPart.get(n),
      i = r ? lC(e.slice(1), r) : void 0;
    if (i) return i;
    if (t.validators.length === 0) return;
    const o = e.join(Uv);
    return (a = t.validators.find(({ validator: s }) => s(o))) == null ? void 0 : a.classGroupId;
  },
  Jx = /^\[(.+)\]$/,
  FD = (e) => {
    if (Jx.test(e)) {
      const t = Jx.exec(e)[1],
        n = t == null ? void 0 : t.substring(0, t.indexOf(":"));
      if (n) return "arbitrary.." + n;
    }
  },
  jD = (e) => {
    const { theme: t, prefix: n } = e,
      r = { nextPart: new Map(), validators: [] };
    return (
      HD(Object.entries(e.classGroups), n).forEach(([o, a]) => {
        hg(a, r, o, t);
      }),
      r
    );
  },
  hg = (e, t, n, r) => {
    e.forEach((i) => {
      if (typeof i == "string") {
        const o = i === "" ? t : eS(t, i);
        o.classGroupId = n;
        return;
      }
      if (typeof i == "function") {
        if (BD(i)) {
          hg(i(r), t, n, r);
          return;
        }
        t.validators.push({ validator: i, classGroupId: n });
        return;
      }
      Object.entries(i).forEach(([o, a]) => {
        hg(a, eS(t, o), n, r);
      });
    });
  },
  eS = (e, t) => {
    let n = e;
    return (
      t.split(Uv).forEach((r) => {
        n.nextPart.has(r) || n.nextPart.set(r, { nextPart: new Map(), validators: [] }),
          (n = n.nextPart.get(r));
      }),
      n
    );
  },
  BD = (e) => e.isThemeGetter,
  HD = (e, t) =>
    t
      ? e.map(([n, r]) => {
          const i = r.map((o) =>
            typeof o == "string"
              ? t + o
              : typeof o == "object"
              ? Object.fromEntries(Object.entries(o).map(([a, s]) => [t + a, s]))
              : o
          );
          return [n, i];
        })
      : e,
  VD = (e) => {
    if (e < 1) return { get: () => {}, set: () => {} };
    let t = 0,
      n = new Map(),
      r = new Map();
    const i = (o, a) => {
      n.set(o, a), t++, t > e && ((t = 0), (r = n), (n = new Map()));
    };
    return {
      get(o) {
        let a = n.get(o);
        if (a !== void 0) return a;
        if ((a = r.get(o)) !== void 0) return i(o, a), a;
      },
      set(o, a) {
        n.has(o) ? n.set(o, a) : i(o, a);
      },
    };
  },
  cC = "!",
  UD = (e) => {
    const { separator: t, experimentalParseClassName: n } = e,
      r = t.length === 1,
      i = t[0],
      o = t.length,
      a = (s) => {
        const u = [];
        let l = 0,
          c = 0,
          f;
        for (let w = 0; w < s.length; w++) {
          let p = s[w];
          if (l === 0) {
            if (p === i && (r || s.slice(w, w + o) === t)) {
              u.push(s.slice(c, w)), (c = w + o);
              continue;
            }
            if (p === "/") {
              f = w;
              continue;
            }
          }
          p === "[" ? l++ : p === "]" && l--;
        }
        const d = u.length === 0 ? s : s.substring(c),
          h = d.startsWith(cC),
          m = h ? d.substring(1) : d,
          v = f && f > c ? f - c : void 0;
        return {
          modifiers: u,
          hasImportantModifier: h,
          baseClassName: m,
          maybePostfixModifierPosition: v,
        };
      };
    return n ? (s) => n({ className: s, parseClassName: a }) : a;
  },
  GD = (e) => {
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
  WD = (e) => ({ cache: VD(e.cacheSize), parseClassName: UD(e), ...DD(e) }),
  KD = /\s+/,
  YD = (e, t) => {
    const { parseClassName: n, getClassGroupId: r, getConflictingClassGroupIds: i } = t,
      o = [],
      a = e.trim().split(KD);
    let s = "";
    for (let u = a.length - 1; u >= 0; u -= 1) {
      const l = a[u],
        {
          modifiers: c,
          hasImportantModifier: f,
          baseClassName: d,
          maybePostfixModifierPosition: h,
        } = n(l);
      let m = !!h,
        v = r(m ? d.substring(0, h) : d);
      if (!v) {
        if (!m) {
          s = l + (s.length > 0 ? " " + s : s);
          continue;
        }
        if (((v = r(d)), !v)) {
          s = l + (s.length > 0 ? " " + s : s);
          continue;
        }
        m = !1;
      }
      const w = GD(c).join(":"),
        p = f ? w + cC : w,
        g = p + v;
      if (o.includes(g)) continue;
      o.push(g);
      const y = i(v, m);
      for (let _ = 0; _ < y.length; ++_) {
        const S = y[_];
        o.push(p + S);
      }
      s = l + (s.length > 0 ? " " + s : s);
    }
    return s;
  };
function XD() {
  let e = 0,
    t,
    n,
    r = "";
  for (; e < arguments.length; ) (t = arguments[e++]) && (n = fC(t)) && (r && (r += " "), (r += n));
  return r;
}
const fC = (e) => {
  if (typeof e == "string") return e;
  let t,
    n = "";
  for (let r = 0; r < e.length; r++) e[r] && (t = fC(e[r])) && (n && (n += " "), (n += t));
  return n;
};
function QD(e, ...t) {
  let n,
    r,
    i,
    o = a;
  function a(u) {
    const l = t.reduce((c, f) => f(c), e());
    return (n = WD(l)), (r = n.cache.get), (i = n.cache.set), (o = s), s(u);
  }
  function s(u) {
    const l = r(u);
    if (l) return l;
    const c = YD(u, n);
    return i(u, c), c;
  }
  return function () {
    return o(XD.apply(null, arguments));
  };
}
const de = (e) => {
    const t = (n) => n[e] || [];
    return (t.isThemeGetter = !0), t;
  },
  dC = /^\[(?:([a-z-]+):)?(.+)\]$/i,
  ZD = /^\d+\/\d+$/,
  JD = new Set(["px", "full", "screen"]),
  e5 = /^(\d+(\.\d+)?)?(xs|sm|md|lg|xl)$/,
  t5 = /\d+(%|px|r?em|[sdl]?v([hwib]|min|max)|pt|pc|in|cm|mm|cap|ch|ex|r?lh|cq(w|h|i|b|min|max))|\b(calc|min|max|clamp)\(.+\)|^0$/,
  n5 = /^(rgba?|hsla?|hwb|(ok)?(lab|lch))\(.+\)$/,
  r5 = /^(inset_)?-?((\d+)?\.?(\d+)[a-z]+|0)_-?((\d+)?\.?(\d+)[a-z]+|0)/,
  i5 = /^(url|image|image-set|cross-fade|element|(repeating-)?(linear|radial|conic)-gradient)\(.+\)$/,
  sn = (e) => li(e) || JD.has(e) || ZD.test(e),
  An = (e) => Ti(e, "length", d5),
  li = (e) => !!e && !Number.isNaN(Number(e)),
  ep = (e) => Ti(e, "number", li),
  Ui = (e) => !!e && Number.isInteger(Number(e)),
  o5 = (e) => e.endsWith("%") && li(e.slice(0, -1)),
  ee = (e) => dC.test(e),
  Mn = (e) => e5.test(e),
  a5 = new Set(["length", "size", "percentage"]),
  s5 = (e) => Ti(e, a5, hC),
  u5 = (e) => Ti(e, "position", hC),
  l5 = new Set(["image", "url"]),
  c5 = (e) => Ti(e, l5, p5),
  f5 = (e) => Ti(e, "", h5),
  Gi = () => !0,
  Ti = (e, t, n) => {
    const r = dC.exec(e);
    return r ? (r[1] ? (typeof t == "string" ? r[1] === t : t.has(r[1])) : n(r[2])) : !1;
  },
  d5 = (e) => t5.test(e) && !n5.test(e),
  hC = () => !1,
  h5 = (e) => r5.test(e),
  p5 = (e) => i5.test(e),
  g5 = () => {
    const e = de("colors"),
      t = de("spacing"),
      n = de("blur"),
      r = de("brightness"),
      i = de("borderColor"),
      o = de("borderRadius"),
      a = de("borderSpacing"),
      s = de("borderWidth"),
      u = de("contrast"),
      l = de("grayscale"),
      c = de("hueRotate"),
      f = de("invert"),
      d = de("gap"),
      h = de("gradientColorStops"),
      m = de("gradientColorStopPositions"),
      v = de("inset"),
      w = de("margin"),
      p = de("opacity"),
      g = de("padding"),
      y = de("saturate"),
      _ = de("scale"),
      S = de("sepia"),
      E = de("skew"),
      k = de("space"),
      C = de("translate"),
      T = () => ["auto", "contain", "none"],
      I = () => ["auto", "hidden", "clip", "visible", "scroll"],
      M = () => ["auto", ee, t],
      z = () => [ee, t],
      F = () => ["", sn, An],
      x = () => ["auto", li, ee],
      P = () => [
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
      N = () => ["solid", "dashed", "dotted", "double", "none"],
      $ = () => [
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
      R = () => ["start", "end", "center", "between", "around", "evenly", "stretch"],
      b = () => ["", "0", ee],
      A = () => ["auto", "avoid", "all", "avoid-page", "page", "left", "right", "column"],
      L = () => [li, ee];
    return {
      cacheSize: 500,
      separator: ":",
      theme: {
        colors: [Gi],
        spacing: [sn, An],
        blur: ["none", "", Mn, ee],
        brightness: L(),
        borderColor: [e],
        borderRadius: ["none", "", "full", Mn, ee],
        borderSpacing: z(),
        borderWidth: F(),
        contrast: L(),
        grayscale: b(),
        hueRotate: L(),
        invert: b(),
        gap: z(),
        gradientColorStops: [e],
        gradientColorStopPositions: [o5, An],
        inset: M(),
        margin: M(),
        opacity: L(),
        padding: z(),
        saturate: L(),
        scale: L(),
        sepia: b(),
        skew: L(),
        space: z(),
        translate: z(),
      },
      classGroups: {
        aspect: [{ aspect: ["auto", "square", "video", ee] }],
        container: ["container"],
        columns: [{ columns: [Mn] }],
        "break-after": [{ "break-after": A() }],
        "break-before": [{ "break-before": A() }],
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
        "object-position": [{ object: [...P(), ee] }],
        overflow: [{ overflow: I() }],
        "overflow-x": [{ "overflow-x": I() }],
        "overflow-y": [{ "overflow-y": I() }],
        overscroll: [{ overscroll: T() }],
        "overscroll-x": [{ "overscroll-x": T() }],
        "overscroll-y": [{ "overscroll-y": T() }],
        position: ["static", "fixed", "absolute", "relative", "sticky"],
        inset: [{ inset: [v] }],
        "inset-x": [{ "inset-x": [v] }],
        "inset-y": [{ "inset-y": [v] }],
        start: [{ start: [v] }],
        end: [{ end: [v] }],
        top: [{ top: [v] }],
        right: [{ right: [v] }],
        bottom: [{ bottom: [v] }],
        left: [{ left: [v] }],
        visibility: ["visible", "invisible", "collapse"],
        z: [{ z: ["auto", Ui, ee] }],
        basis: [{ basis: M() }],
        "flex-direction": [{ flex: ["row", "row-reverse", "col", "col-reverse"] }],
        "flex-wrap": [{ flex: ["wrap", "wrap-reverse", "nowrap"] }],
        flex: [{ flex: ["1", "auto", "initial", "none", ee] }],
        grow: [{ grow: b() }],
        shrink: [{ shrink: b() }],
        order: [{ order: ["first", "last", "none", Ui, ee] }],
        "grid-cols": [{ "grid-cols": [Gi] }],
        "col-start-end": [{ col: ["auto", { span: ["full", Ui, ee] }, ee] }],
        "col-start": [{ "col-start": x() }],
        "col-end": [{ "col-end": x() }],
        "grid-rows": [{ "grid-rows": [Gi] }],
        "row-start-end": [{ row: ["auto", { span: [Ui, ee] }, ee] }],
        "row-start": [{ "row-start": x() }],
        "row-end": [{ "row-end": x() }],
        "grid-flow": [{ "grid-flow": ["row", "col", "dense", "row-dense", "col-dense"] }],
        "auto-cols": [{ "auto-cols": ["auto", "min", "max", "fr", ee] }],
        "auto-rows": [{ "auto-rows": ["auto", "min", "max", "fr", ee] }],
        gap: [{ gap: [d] }],
        "gap-x": [{ "gap-x": [d] }],
        "gap-y": [{ "gap-y": [d] }],
        "justify-content": [{ justify: ["normal", ...R()] }],
        "justify-items": [{ "justify-items": ["start", "end", "center", "stretch"] }],
        "justify-self": [{ "justify-self": ["auto", "start", "end", "center", "stretch"] }],
        "align-content": [{ content: ["normal", ...R(), "baseline"] }],
        "align-items": [{ items: ["start", "end", "center", "baseline", "stretch"] }],
        "align-self": [{ self: ["auto", "start", "end", "center", "stretch", "baseline"] }],
        "place-content": [{ "place-content": [...R(), "baseline"] }],
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
        "space-x": [{ "space-x": [k] }],
        "space-x-reverse": ["space-x-reverse"],
        "space-y": [{ "space-y": [k] }],
        "space-y-reverse": ["space-y-reverse"],
        w: [{ w: ["auto", "min", "max", "fit", "svw", "lvw", "dvw", ee, t] }],
        "min-w": [{ "min-w": [ee, t, "min", "max", "fit"] }],
        "max-w": [
          { "max-w": [ee, t, "none", "full", "min", "max", "fit", "prose", { screen: [Mn] }, Mn] },
        ],
        h: [{ h: [ee, t, "auto", "min", "max", "fit", "svh", "lvh", "dvh"] }],
        "min-h": [{ "min-h": [ee, t, "min", "max", "fit", "svh", "lvh", "dvh"] }],
        "max-h": [{ "max-h": [ee, t, "min", "max", "fit", "svh", "lvh", "dvh"] }],
        size: [{ size: [ee, t, "auto", "min", "max", "fit"] }],
        "font-size": [{ text: ["base", Mn, An] }],
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
              ep,
            ],
          },
        ],
        "font-family": [{ font: [Gi] }],
        "fvn-normal": ["normal-nums"],
        "fvn-ordinal": ["ordinal"],
        "fvn-slashed-zero": ["slashed-zero"],
        "fvn-figure": ["lining-nums", "oldstyle-nums"],
        "fvn-spacing": ["proportional-nums", "tabular-nums"],
        "fvn-fraction": ["diagonal-fractions", "stacked-fractions"],
        tracking: [{ tracking: ["tighter", "tight", "normal", "wide", "wider", "widest", ee] }],
        "line-clamp": [{ "line-clamp": ["none", li, ep] }],
        leading: [{ leading: ["none", "tight", "snug", "normal", "relaxed", "loose", sn, ee] }],
        "list-image": [{ "list-image": ["none", ee] }],
        "list-style-type": [{ list: ["none", "disc", "decimal", ee] }],
        "list-style-position": [{ list: ["inside", "outside"] }],
        "placeholder-color": [{ placeholder: [e] }],
        "placeholder-opacity": [{ "placeholder-opacity": [p] }],
        "text-alignment": [{ text: ["left", "center", "right", "justify", "start", "end"] }],
        "text-color": [{ text: [e] }],
        "text-opacity": [{ "text-opacity": [p] }],
        "text-decoration": ["underline", "overline", "line-through", "no-underline"],
        "text-decoration-style": [{ decoration: [...N(), "wavy"] }],
        "text-decoration-thickness": [{ decoration: ["auto", "from-font", sn, An] }],
        "underline-offset": [{ "underline-offset": ["auto", sn, ee] }],
        "text-decoration-color": [{ decoration: [e] }],
        "text-transform": ["uppercase", "lowercase", "capitalize", "normal-case"],
        "text-overflow": ["truncate", "text-ellipsis", "text-clip"],
        "text-wrap": [{ text: ["wrap", "nowrap", "balance", "pretty"] }],
        indent: [{ indent: z() }],
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
              ee,
            ],
          },
        ],
        whitespace: [
          { whitespace: ["normal", "nowrap", "pre", "pre-line", "pre-wrap", "break-spaces"] },
        ],
        break: [{ break: ["normal", "words", "all", "keep"] }],
        hyphens: [{ hyphens: ["none", "manual", "auto"] }],
        content: [{ content: ["none", ee] }],
        "bg-attachment": [{ bg: ["fixed", "local", "scroll"] }],
        "bg-clip": [{ "bg-clip": ["border", "padding", "content", "text"] }],
        "bg-opacity": [{ "bg-opacity": [p] }],
        "bg-origin": [{ "bg-origin": ["border", "padding", "content"] }],
        "bg-position": [{ bg: [...P(), u5] }],
        "bg-repeat": [{ bg: ["no-repeat", { repeat: ["", "x", "y", "round", "space"] }] }],
        "bg-size": [{ bg: ["auto", "cover", "contain", s5] }],
        "bg-image": [
          { bg: ["none", { "gradient-to": ["t", "tr", "r", "br", "b", "bl", "l", "tl"] }, c5] },
        ],
        "bg-color": [{ bg: [e] }],
        "gradient-from-pos": [{ from: [m] }],
        "gradient-via-pos": [{ via: [m] }],
        "gradient-to-pos": [{ to: [m] }],
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
        "border-w": [{ border: [s] }],
        "border-w-x": [{ "border-x": [s] }],
        "border-w-y": [{ "border-y": [s] }],
        "border-w-s": [{ "border-s": [s] }],
        "border-w-e": [{ "border-e": [s] }],
        "border-w-t": [{ "border-t": [s] }],
        "border-w-r": [{ "border-r": [s] }],
        "border-w-b": [{ "border-b": [s] }],
        "border-w-l": [{ "border-l": [s] }],
        "border-opacity": [{ "border-opacity": [p] }],
        "border-style": [{ border: [...N(), "hidden"] }],
        "divide-x": [{ "divide-x": [s] }],
        "divide-x-reverse": ["divide-x-reverse"],
        "divide-y": [{ "divide-y": [s] }],
        "divide-y-reverse": ["divide-y-reverse"],
        "divide-opacity": [{ "divide-opacity": [p] }],
        "divide-style": [{ divide: N() }],
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
        "outline-style": [{ outline: ["", ...N()] }],
        "outline-offset": [{ "outline-offset": [sn, ee] }],
        "outline-w": [{ outline: [sn, An] }],
        "outline-color": [{ outline: [e] }],
        "ring-w": [{ ring: F() }],
        "ring-w-inset": ["ring-inset"],
        "ring-color": [{ ring: [e] }],
        "ring-opacity": [{ "ring-opacity": [p] }],
        "ring-offset-w": [{ "ring-offset": [sn, An] }],
        "ring-offset-color": [{ "ring-offset": [e] }],
        shadow: [{ shadow: ["", "inner", "none", Mn, f5] }],
        "shadow-color": [{ shadow: [Gi] }],
        opacity: [{ opacity: [p] }],
        "mix-blend": [{ "mix-blend": [...$(), "plus-lighter", "plus-darker"] }],
        "bg-blend": [{ "bg-blend": $() }],
        filter: [{ filter: ["", "none"] }],
        blur: [{ blur: [n] }],
        brightness: [{ brightness: [r] }],
        contrast: [{ contrast: [u] }],
        "drop-shadow": [{ "drop-shadow": ["", "none", Mn, ee] }],
        grayscale: [{ grayscale: [l] }],
        "hue-rotate": [{ "hue-rotate": [c] }],
        invert: [{ invert: [f] }],
        saturate: [{ saturate: [y] }],
        sepia: [{ sepia: [S] }],
        "backdrop-filter": [{ "backdrop-filter": ["", "none"] }],
        "backdrop-blur": [{ "backdrop-blur": [n] }],
        "backdrop-brightness": [{ "backdrop-brightness": [r] }],
        "backdrop-contrast": [{ "backdrop-contrast": [u] }],
        "backdrop-grayscale": [{ "backdrop-grayscale": [l] }],
        "backdrop-hue-rotate": [{ "backdrop-hue-rotate": [c] }],
        "backdrop-invert": [{ "backdrop-invert": [f] }],
        "backdrop-opacity": [{ "backdrop-opacity": [p] }],
        "backdrop-saturate": [{ "backdrop-saturate": [y] }],
        "backdrop-sepia": [{ "backdrop-sepia": [S] }],
        "border-collapse": [{ border: ["collapse", "separate"] }],
        "border-spacing": [{ "border-spacing": [a] }],
        "border-spacing-x": [{ "border-spacing-x": [a] }],
        "border-spacing-y": [{ "border-spacing-y": [a] }],
        "table-layout": [{ table: ["auto", "fixed"] }],
        caption: [{ caption: ["top", "bottom"] }],
        transition: [
          { transition: ["none", "all", "", "colors", "opacity", "shadow", "transform", ee] },
        ],
        duration: [{ duration: L() }],
        ease: [{ ease: ["linear", "in", "out", "in-out", ee] }],
        delay: [{ delay: L() }],
        animate: [{ animate: ["none", "spin", "ping", "pulse", "bounce", ee] }],
        transform: [{ transform: ["", "gpu", "none"] }],
        scale: [{ scale: [_] }],
        "scale-x": [{ "scale-x": [_] }],
        "scale-y": [{ "scale-y": [_] }],
        rotate: [{ rotate: [Ui, ee] }],
        "translate-x": [{ "translate-x": [C] }],
        "translate-y": [{ "translate-y": [C] }],
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
              ee,
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
              ee,
            ],
          },
        ],
        "caret-color": [{ caret: [e] }],
        "pointer-events": [{ "pointer-events": ["none", "auto"] }],
        resize: [{ resize: ["none", "y", "x", ""] }],
        "scroll-behavior": [{ scroll: ["auto", "smooth"] }],
        "scroll-m": [{ "scroll-m": z() }],
        "scroll-mx": [{ "scroll-mx": z() }],
        "scroll-my": [{ "scroll-my": z() }],
        "scroll-ms": [{ "scroll-ms": z() }],
        "scroll-me": [{ "scroll-me": z() }],
        "scroll-mt": [{ "scroll-mt": z() }],
        "scroll-mr": [{ "scroll-mr": z() }],
        "scroll-mb": [{ "scroll-mb": z() }],
        "scroll-ml": [{ "scroll-ml": z() }],
        "scroll-p": [{ "scroll-p": z() }],
        "scroll-px": [{ "scroll-px": z() }],
        "scroll-py": [{ "scroll-py": z() }],
        "scroll-ps": [{ "scroll-ps": z() }],
        "scroll-pe": [{ "scroll-pe": z() }],
        "scroll-pt": [{ "scroll-pt": z() }],
        "scroll-pr": [{ "scroll-pr": z() }],
        "scroll-pb": [{ "scroll-pb": z() }],
        "scroll-pl": [{ "scroll-pl": z() }],
        "snap-align": [{ snap: ["start", "end", "center", "align-none"] }],
        "snap-stop": [{ snap: ["normal", "always"] }],
        "snap-type": [{ snap: ["none", "x", "y", "both"] }],
        "snap-strictness": [{ snap: ["mandatory", "proximity"] }],
        touch: [{ touch: ["auto", "none", "manipulation"] }],
        "touch-x": [{ "touch-pan": ["x", "left", "right"] }],
        "touch-y": [{ "touch-pan": ["y", "up", "down"] }],
        "touch-pz": ["touch-pinch-zoom"],
        select: [{ select: ["none", "text", "all", "auto"] }],
        "will-change": [{ "will-change": ["auto", "scroll", "contents", "transform", ee] }],
        fill: [{ fill: [e, "none"] }],
        "stroke-w": [{ stroke: [sn, An, ep] }],
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
  v5 = QD(g5);
function m5(...e) {
  return v5($D(e));
}
function y5() {
  VT();
  const e = xb((s) => s.machines),
    [t, n] = q.useState(null),
    [r, i] = q.useState(!1);
  q.useEffect(() => {
    const s = Object.keys(e);
    !t && s.length > 0 && n(s[0]), t && !e[t] && n(s.length > 0 ? s[0] : null);
  }, [e, t]),
    q.useEffect(() => {
      const s =
        localStorage.getItem("theme") === "dark" ||
        (!("theme" in localStorage) && window.matchMedia("(prefers-color-scheme: dark)").matches);
      i(s), document.documentElement.classList.toggle("dark", s);
    }, []);
  const o = () => {
      const s = !r;
      i(s),
        localStorage.setItem("theme", s ? "dark" : "light"),
        document.documentElement.classList.toggle("dark", s);
    },
    a = t ? e[t] : null;
  return W.jsxs("div", {
    className: "flex h-screen w-full flex-col bg-muted/40 font-sans",
    children: [
      W.jsx(_5, {
        machines: e,
        selectedMachineId: t,
        onSelectMachine: n,
        onToggleTheme: o,
        isDark: r,
      }),
      W.jsx("main", {
        className: "flex flex-col gap-4 p-4 sm:py-4 sm:pl-14 md:pl-[280px]",
        children: a
          ? W.jsx(w5, { machine: a })
          : W.jsx("div", {
              className:
                "flex h-full items-center justify-center rounded-lg border border-dashed shadow-sm",
              children: W.jsxs("div", {
                className: "text-center",
                children: [
                  W.jsx("h3", {
                    className: "text-2xl font-bold tracking-tight",
                    children: "No Live Machines",
                  }),
                  W.jsx("p", {
                    className: "text-muted-foreground",
                    children: "Run a Python script with the InspectorPlugin to begin.",
                  }),
                ],
              }),
            }),
      }),
    ],
  });
}
function _5({
  machines: e,
  selectedMachineId: t,
  onSelectMachine: n,
  onToggleTheme: r,
  isDark: i,
}) {
  return W.jsxs("aside", {
    className:
      "fixed inset-y-0 left-0 z-10 hidden w-14 flex-col border-r bg-background sm:flex md:w-[280px]",
    children: [
      W.jsxs("nav", {
        className: "flex flex-col items-center gap-4 px-2 py-4 md:items-stretch",
        children: [
          W.jsx("div", {
            className: "hidden h-16 items-center justify-between border-b px-6 md:flex",
            children: W.jsx("h1", { className: "text-lg font-bold", children: "XState Inspector" }),
          }),
          Object.values(e).map((o) =>
            W.jsxs(
              "button",
              {
                onClick: () => n(o.id),
                className: m5(
                  "flex items-center justify-center gap-3 rounded-lg px-3 py-2 text-muted-foreground transition-all hover:text-primary md:justify-start",
                  t === o.id && "bg-accent text-primary"
                ),
                children: [
                  W.jsxs("svg", {
                    xmlns: "http://www.w3.org/2000/svg",
                    width: "24",
                    height: "24",
                    viewBox: "0 0 24 24",
                    fill: "none",
                    stroke: "currentColor",
                    strokeWidth: "2",
                    strokeLinecap: "round",
                    strokeLinejoin: "round",
                    className: "h-5 w-5",
                    children: [
                      W.jsx("path", { d: "m12 14 4-4" }),
                      W.jsx("path", { d: "m12 14-4-4" }),
                      W.jsx("path", { d: "M12 20v-8" }),
                      W.jsx("path", { d: "M12 4v2" }),
                      W.jsx("path", { d: "M12 10h.01" }),
                      W.jsx("path", { d: "M20 12h-2" }),
                      W.jsx("path", { d: "M10 12h.01" }),
                      W.jsx("path", { d: "m4.929 19.071 1.414-1.414" }),
                      W.jsx("path", { d: "m17.657 6.343-1.414 1.414" }),
                      W.jsx("path", { d: "m4.929 4.929 1.414 1.414" }),
                      W.jsx("path", { d: "m17.657 17.657-1.414 1.414" }),
                    ],
                  }),
                  W.jsx("span", { className: "hidden md:inline", children: o.id }),
                ],
              },
              o.id
            )
          ),
        ],
      }),
      W.jsx("nav", {
        className: "mt-auto flex flex-col items-center gap-4 px-2 py-4 md:items-stretch",
        children: W.jsxs("button", {
          onClick: r,
          className:
            "flex items-center justify-center gap-3 rounded-lg px-3 py-2 text-muted-foreground transition-all hover:text-primary md:justify-start",
          children: [
            i ? W.jsx(zD, { className: "h-5 w-5" }) : W.jsx(LD, { className: "h-5 w-5" }),
            W.jsx("span", { className: "hidden md:inline", children: "Toggle Theme" }),
          ],
        }),
      }),
    ],
  });
}
function w5({ machine: e }) {
  return W.jsxs(W.Fragment, {
    children: [
      W.jsxs("header", {
        children: [
          W.jsx("h1", { className: "text-4xl font-bold tracking-tight", children: e.id }),
          W.jsxs("p", {
            className: "text-muted-foreground",
            children: [
              "Current State: ",
              W.jsx("span", {
                className: "font-mono text-primary",
                children: e.currentStateIds.join(", "),
              }),
            ],
          }),
        ],
      }),
      W.jsxs("div", {
        className: "grid gap-4 md:grid-cols-2 lg:grid-cols-7",
        children: [
          W.jsx("div", {
            className: "rounded-xl border bg-card text-card-foreground shadow lg:col-span-4",
            children: W.jsxs("div", {
              className: "p-6",
              children: [
                W.jsx("h3", { className: "font-semibold text-lg mb-4", children: "Statechart" }),
                W.jsx(PD, { machine: e, activeStateIds: e.currentStateIds }),
              ],
            }),
          }),
          W.jsx("div", {
            className: "rounded-xl border bg-card text-card-foreground shadow lg:col-span-3",
            children: W.jsxs("div", {
              className: "p-6",
              children: [
                W.jsx("h3", { className: "font-semibold text-lg mb-2", children: "Context" }),
                W.jsx("pre", {
                  className:
                    "mt-2 h-[200px] w-full overflow-auto rounded-md bg-muted p-4 font-mono text-sm",
                  children: JSON.stringify(e.context, null, 2),
                }),
                W.jsx("h3", {
                  className: "font-semibold text-lg mt-4 mb-2",
                  children: "Event Log",
                }),
                W.jsx("div", {
                  className:
                    "h-[250px] w-full overflow-auto rounded-md bg-muted p-2 font-mono text-xs",
                  children: e.logs.map((t, n) =>
                    W.jsxs(
                      "div",
                      {
                        className: "p-2 border-b border-background",
                        children: [
                          W.jsx("p", { className: "font-bold", children: t.type }),
                          W.jsx("p", {
                            className: "text-muted-foreground",
                            children: JSON.stringify(t.payload),
                          }),
                        ],
                      },
                      n
                    )
                  ),
                }),
              ],
            }),
          }),
        ],
      }),
    ],
  });
}
tp.createRoot(document.getElementById("root")).render(
  W.jsx(O.StrictMode, { children: W.jsx(y5, {}) })
);
