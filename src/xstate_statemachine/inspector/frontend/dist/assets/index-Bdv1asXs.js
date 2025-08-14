function YD(e, t) {
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
var Sa =
  typeof globalThis < "u"
    ? globalThis
    : typeof window < "u"
    ? window
    : typeof global < "u"
    ? global
    : typeof self < "u"
    ? self
    : {};
function ry(e) {
  return e && e.__esModule && Object.prototype.hasOwnProperty.call(e, "default") ? e.default : e;
}
var pk = { exports: {} },
  xl = {},
  mk = { exports: {} },
  ie = {};
/**
 * @license React
 * react.production.min.js
 *
 * Copyright (c) Facebook, Inc. and its affiliates.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */ var ra = Symbol.for("react.element"),
  XD = Symbol.for("react.portal"),
  ZD = Symbol.for("react.fragment"),
  QD = Symbol.for("react.strict_mode"),
  JD = Symbol.for("react.profiler"),
  eO = Symbol.for("react.provider"),
  tO = Symbol.for("react.context"),
  nO = Symbol.for("react.forward_ref"),
  rO = Symbol.for("react.suspense"),
  iO = Symbol.for("react.memo"),
  oO = Symbol.for("react.lazy"),
  Nw = Symbol.iterator;
function sO(e) {
  return e === null || typeof e != "object"
    ? null
    : ((e = (Nw && e[Nw]) || e["@@iterator"]), typeof e == "function" ? e : null);
}
var gk = {
    isMounted: function () {
      return !1;
    },
    enqueueForceUpdate: function () {},
    enqueueReplaceState: function () {},
    enqueueSetState: function () {},
  },
  vk = Object.assign,
  yk = {};
function wo(e, t, n) {
  (this.props = e), (this.context = t), (this.refs = yk), (this.updater = n || gk);
}
wo.prototype.isReactComponent = {};
wo.prototype.setState = function (e, t) {
  if (typeof e != "object" && typeof e != "function" && e != null)
    throw Error(
      "setState(...): takes an object of state variables to update or a function which returns an object of state variables."
    );
  this.updater.enqueueSetState(this, e, t, "setState");
};
wo.prototype.forceUpdate = function (e) {
  this.updater.enqueueForceUpdate(this, e, "forceUpdate");
};
function wk() {}
wk.prototype = wo.prototype;
function iy(e, t, n) {
  (this.props = e), (this.context = t), (this.refs = yk), (this.updater = n || gk);
}
var oy = (iy.prototype = new wk());
oy.constructor = iy;
vk(oy, wo.prototype);
oy.isPureReactComponent = !0;
var Mw = Array.isArray,
  xk = Object.prototype.hasOwnProperty,
  sy = { current: null },
  _k = { key: !0, ref: !0, __self: !0, __source: !0 };
function Sk(e, t, n) {
  var r,
    i = {},
    o = null,
    s = null;
  if (t != null)
    for (r in (t.ref !== void 0 && (s = t.ref), t.key !== void 0 && (o = "" + t.key), t))
      xk.call(t, r) && !_k.hasOwnProperty(r) && (i[r] = t[r]);
  var a = arguments.length - 2;
  if (a === 1) i.children = n;
  else if (1 < a) {
    for (var u = Array(a), l = 0; l < a; l++) u[l] = arguments[l + 2];
    i.children = u;
  }
  if (e && e.defaultProps) for (r in ((a = e.defaultProps), a)) i[r] === void 0 && (i[r] = a[r]);
  return { $$typeof: ra, type: e, key: o, ref: s, props: i, _owner: sy.current };
}
function aO(e, t) {
  return { $$typeof: ra, type: e.type, key: t, ref: e.ref, props: e.props, _owner: e._owner };
}
function ay(e) {
  return typeof e == "object" && e !== null && e.$$typeof === ra;
}
function uO(e) {
  var t = { "=": "=0", ":": "=2" };
  return (
    "$" +
    e.replace(/[=:]/g, function (n) {
      return t[n];
    })
  );
}
var Iw = /\/+/g;
function Ec(e, t) {
  return typeof e == "object" && e !== null && e.key != null ? uO("" + e.key) : t.toString(36);
}
function ou(e, t, n, r, i) {
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
          case ra:
          case XD:
            s = !0;
        }
    }
  if (s)
    return (
      (s = e),
      (i = i(s)),
      (e = r === "" ? "." + Ec(s, 0) : r),
      Mw(i)
        ? ((n = ""),
          e != null && (n = e.replace(Iw, "$&/") + "/"),
          ou(i, t, n, "", function (l) {
            return l;
          }))
        : i != null &&
          (ay(i) &&
            (i = aO(
              i,
              n +
                (!i.key || (s && s.key === i.key) ? "" : ("" + i.key).replace(Iw, "$&/") + "/") +
                e
            )),
          t.push(i)),
      1
    );
  if (((s = 0), (r = r === "" ? "." : r + ":"), Mw(e)))
    for (var a = 0; a < e.length; a++) {
      o = e[a];
      var u = r + Ec(o, a);
      s += ou(o, t, n, u, i);
    }
  else if (((u = sO(e)), typeof u == "function"))
    for (e = u.call(e), a = 0; !(o = e.next()).done; )
      (o = o.value), (u = r + Ec(o, a++)), (s += ou(o, t, n, u, i));
  else if (o === "object")
    throw (
      ((t = String(e)),
      Error(
        "Objects are not valid as a React child (found: " +
          (t === "[object Object]" ? "object with keys {" + Object.keys(e).join(", ") + "}" : t) +
          "). If you meant to render a collection of children, use an array instead."
      ))
    );
  return s;
}
function ba(e, t, n) {
  if (e == null) return e;
  var r = [],
    i = 0;
  return (
    ou(e, r, "", "", function (o) {
      return t.call(n, o, i++);
    }),
    r
  );
}
function lO(e) {
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
var ut = { current: null },
  su = { transition: null },
  cO = { ReactCurrentDispatcher: ut, ReactCurrentBatchConfig: su, ReactCurrentOwner: sy };
function bk() {
  throw Error("act(...) is not supported in production builds of React.");
}
ie.Children = {
  map: ba,
  forEach: function (e, t, n) {
    ba(
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
      ba(e, function () {
        t++;
      }),
      t
    );
  },
  toArray: function (e) {
    return (
      ba(e, function (t) {
        return t;
      }) || []
    );
  },
  only: function (e) {
    if (!ay(e))
      throw Error("React.Children.only expected to receive a single React element child.");
    return e;
  },
};
ie.Component = wo;
ie.Fragment = ZD;
ie.Profiler = JD;
ie.PureComponent = iy;
ie.StrictMode = QD;
ie.Suspense = rO;
ie.__SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED = cO;
ie.act = bk;
ie.cloneElement = function (e, t, n) {
  if (e == null)
    throw Error(
      "React.cloneElement(...): The argument must be a React element, but you passed " + e + "."
    );
  var r = vk({}, e.props),
    i = e.key,
    o = e.ref,
    s = e._owner;
  if (t != null) {
    if (
      (t.ref !== void 0 && ((o = t.ref), (s = sy.current)),
      t.key !== void 0 && (i = "" + t.key),
      e.type && e.type.defaultProps)
    )
      var a = e.type.defaultProps;
    for (u in t)
      xk.call(t, u) &&
        !_k.hasOwnProperty(u) &&
        (r[u] = t[u] === void 0 && a !== void 0 ? a[u] : t[u]);
  }
  var u = arguments.length - 2;
  if (u === 1) r.children = n;
  else if (1 < u) {
    a = Array(u);
    for (var l = 0; l < u; l++) a[l] = arguments[l + 2];
    r.children = a;
  }
  return { $$typeof: ra, type: e.type, key: i, ref: o, props: r, _owner: s };
};
ie.createContext = function (e) {
  return (
    (e = {
      $$typeof: tO,
      _currentValue: e,
      _currentValue2: e,
      _threadCount: 0,
      Provider: null,
      Consumer: null,
      _defaultValue: null,
      _globalName: null,
    }),
    (e.Provider = { $$typeof: eO, _context: e }),
    (e.Consumer = e)
  );
};
ie.createElement = Sk;
ie.createFactory = function (e) {
  var t = Sk.bind(null, e);
  return (t.type = e), t;
};
ie.createRef = function () {
  return { current: null };
};
ie.forwardRef = function (e) {
  return { $$typeof: nO, render: e };
};
ie.isValidElement = ay;
ie.lazy = function (e) {
  return { $$typeof: oO, _payload: { _status: -1, _result: e }, _init: lO };
};
ie.memo = function (e, t) {
  return { $$typeof: iO, type: e, compare: t === void 0 ? null : t };
};
ie.startTransition = function (e) {
  var t = su.transition;
  su.transition = {};
  try {
    e();
  } finally {
    su.transition = t;
  }
};
ie.unstable_act = bk;
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
mk.exports = ie;
var _ = mk.exports;
const L = ry(_),
  Ek = YD({ __proto__: null, default: L }, [_]);
/**
 * @license React
 * react-jsx-runtime.production.min.js
 *
 * Copyright (c) Facebook, Inc. and its affiliates.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */ var fO = _,
  dO = Symbol.for("react.element"),
  hO = Symbol.for("react.fragment"),
  pO = Object.prototype.hasOwnProperty,
  mO = fO.__SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED.ReactCurrentOwner,
  gO = { key: !0, ref: !0, __self: !0, __source: !0 };
function Ck(e, t, n) {
  var r,
    i = {},
    o = null,
    s = null;
  n !== void 0 && (o = "" + n),
    t.key !== void 0 && (o = "" + t.key),
    t.ref !== void 0 && (s = t.ref);
  for (r in t) pO.call(t, r) && !gO.hasOwnProperty(r) && (i[r] = t[r]);
  if (e && e.defaultProps) for (r in ((t = e.defaultProps), t)) i[r] === void 0 && (i[r] = t[r]);
  return { $$typeof: dO, type: e, key: o, ref: s, props: i, _owner: mO.current };
}
xl.Fragment = hO;
xl.jsx = Ck;
xl.jsxs = Ck;
pk.exports = xl;
var M = pk.exports,
  Cg = {},
  Tk = { exports: {} },
  Rt = {},
  kk = { exports: {} },
  Pk = {};
/**
 * @license React
 * scheduler.production.min.js
 *
 * Copyright (c) Facebook, Inc. and its affiliates.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */ (function (e) {
  function t(A, k) {
    var D = A.length;
    A.push(k);
    e: for (; 0 < D; ) {
      var j = (D - 1) >>> 1,
        $ = A[j];
      if (0 < i($, k)) (A[j] = k), (A[D] = $), (D = j);
      else break e;
    }
  }
  function n(A) {
    return A.length === 0 ? null : A[0];
  }
  function r(A) {
    if (A.length === 0) return null;
    var k = A[0],
      D = A.pop();
    if (D !== k) {
      A[0] = D;
      e: for (var j = 0, $ = A.length, U = $ >>> 1; j < U; ) {
        var B = 2 * (j + 1) - 1,
          W = A[B],
          X = B + 1,
          ee = A[X];
        if (0 > i(W, D))
          X < $ && 0 > i(ee, W)
            ? ((A[j] = ee), (A[X] = D), (j = X))
            : ((A[j] = W), (A[B] = D), (j = B));
        else if (X < $ && 0 > i(ee, D)) (A[j] = ee), (A[X] = D), (j = X);
        else break e;
      }
    }
    return k;
  }
  function i(A, k) {
    var D = A.sortIndex - k.sortIndex;
    return D !== 0 ? D : A.id - k.id;
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
  function w(A) {
    for (var k = n(l); k !== null; ) {
      if (k.callback === null) r(l);
      else if (k.startTime <= A) r(l), (k.sortIndex = k.expirationTime), t(u, k);
      else break;
      k = n(l);
    }
  }
  function x(A) {
    if (((p = !1), w(A), !v))
      if (n(u) !== null) (v = !0), R(S);
      else {
        var k = n(l);
        k !== null && F(x, k.startTime - A);
      }
  }
  function S(A, k) {
    (v = !1), p && ((p = !1), m(T), (T = -1)), (h = !0);
    var D = d;
    try {
      for (w(k), f = n(u); f !== null && (!(f.expirationTime > k) || (A && !I())); ) {
        var j = f.callback;
        if (typeof j == "function") {
          (f.callback = null), (d = f.priorityLevel);
          var $ = j(f.expirationTime <= k);
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
  var C = !1,
    E = null,
    T = -1,
    P = 5,
    N = -1;
  function I() {
    return !(e.unstable_now() - N < P);
  }
  function V() {
    if (E !== null) {
      var A = e.unstable_now();
      N = A;
      var k = !0;
      try {
        k = E(!0, A);
      } finally {
        k ? q() : ((C = !1), (E = null));
      }
    } else C = !1;
  }
  var q;
  if (typeof g == "function")
    q = function () {
      g(V);
    };
  else if (typeof MessageChannel < "u") {
    var b = new MessageChannel(),
      O = b.port2;
    (b.port1.onmessage = V),
      (q = function () {
        O.postMessage(null);
      });
  } else
    q = function () {
      y(V, 0);
    };
  function R(A) {
    (E = A), C || ((C = !0), q());
  }
  function F(A, k) {
    T = y(function () {
      A(e.unstable_now());
    }, k);
  }
  (e.unstable_IdlePriority = 5),
    (e.unstable_ImmediatePriority = 1),
    (e.unstable_LowPriority = 4),
    (e.unstable_NormalPriority = 3),
    (e.unstable_Profiling = null),
    (e.unstable_UserBlockingPriority = 2),
    (e.unstable_cancelCallback = function (A) {
      A.callback = null;
    }),
    (e.unstable_continueExecution = function () {
      v || h || ((v = !0), R(S));
    }),
    (e.unstable_forceFrameRate = function (A) {
      0 > A || 125 < A
        ? console.error(
            "forceFrameRate takes a positive int between 0 and 125, forcing frame rates higher than 125 fps is not supported"
          )
        : (P = 0 < A ? Math.floor(1e3 / A) : 5);
    }),
    (e.unstable_getCurrentPriorityLevel = function () {
      return d;
    }),
    (e.unstable_getFirstCallbackNode = function () {
      return n(u);
    }),
    (e.unstable_next = function (A) {
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
        return A();
      } finally {
        d = D;
      }
    }),
    (e.unstable_pauseExecution = function () {}),
    (e.unstable_requestPaint = function () {}),
    (e.unstable_runWithPriority = function (A, k) {
      switch (A) {
        case 1:
        case 2:
        case 3:
        case 4:
        case 5:
          break;
        default:
          A = 3;
      }
      var D = d;
      d = A;
      try {
        return k();
      } finally {
        d = D;
      }
    }),
    (e.unstable_scheduleCallback = function (A, k, D) {
      var j = e.unstable_now();
      switch (
        (typeof D == "object" && D !== null
          ? ((D = D.delay), (D = typeof D == "number" && 0 < D ? j + D : j))
          : (D = j),
        A)
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
        (A = {
          id: c++,
          callback: k,
          priorityLevel: A,
          startTime: D,
          expirationTime: $,
          sortIndex: -1,
        }),
        D > j
          ? ((A.sortIndex = D),
            t(l, A),
            n(u) === null && A === n(l) && (p ? (m(T), (T = -1)) : (p = !0), F(x, D - j)))
          : ((A.sortIndex = $), t(u, A), v || h || ((v = !0), R(S))),
        A
      );
    }),
    (e.unstable_shouldYield = I),
    (e.unstable_wrapCallback = function (A) {
      var k = d;
      return function () {
        var D = d;
        d = k;
        try {
          return A.apply(this, arguments);
        } finally {
          d = D;
        }
      };
    });
})(Pk);
kk.exports = Pk;
var vO = kk.exports;
/**
 * @license React
 * react-dom.production.min.js
 *
 * Copyright (c) Facebook, Inc. and its affiliates.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */ var yO = _,
  Tt = vO;
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
var Rk = new Set(),
  Cs = {};
function ci(e, t) {
  no(e, t), no(e + "Capture", t);
}
function no(e, t) {
  for (Cs[e] = t, e = 0; e < t.length; e++) Rk.add(t[e]);
}
var $n = !(
    typeof window > "u" ||
    typeof window.document > "u" ||
    typeof window.document.createElement > "u"
  ),
  Tg = Object.prototype.hasOwnProperty,
  wO = /^[:A-Z_a-z\u00C0-\u00D6\u00D8-\u00F6\u00F8-\u02FF\u0370-\u037D\u037F-\u1FFF\u200C-\u200D\u2070-\u218F\u2C00-\u2FEF\u3001-\uD7FF\uF900-\uFDCF\uFDF0-\uFFFD][:A-Z_a-z\u00C0-\u00D6\u00D8-\u00F6\u00F8-\u02FF\u0370-\u037D\u037F-\u1FFF\u200C-\u200D\u2070-\u218F\u2C00-\u2FEF\u3001-\uD7FF\uF900-\uFDCF\uFDF0-\uFFFD\-.0-9\u00B7\u0300-\u036F\u203F-\u2040]*$/,
  Dw = {},
  Ow = {};
function xO(e) {
  return Tg.call(Ow, e) ? !0 : Tg.call(Dw, e) ? !1 : wO.test(e) ? (Ow[e] = !0) : ((Dw[e] = !0), !1);
}
function _O(e, t, n, r) {
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
function SO(e, t, n, r) {
  if (t === null || typeof t > "u" || _O(e, t, n, r)) return !0;
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
var uy = /[\-:]([a-z])/g;
function ly(e) {
  return e[1].toUpperCase();
}
"accent-height alignment-baseline arabic-form baseline-shift cap-height clip-path clip-rule color-interpolation color-interpolation-filters color-profile color-rendering dominant-baseline enable-background fill-opacity fill-rule flood-color flood-opacity font-family font-size font-size-adjust font-stretch font-style font-variant font-weight glyph-name glyph-orientation-horizontal glyph-orientation-vertical horiz-adv-x horiz-origin-x image-rendering letter-spacing lighting-color marker-end marker-mid marker-start overline-position overline-thickness paint-order panose-1 pointer-events rendering-intent shape-rendering stop-color stop-opacity strikethrough-position strikethrough-thickness stroke-dasharray stroke-dashoffset stroke-linecap stroke-linejoin stroke-miterlimit stroke-opacity stroke-width text-anchor text-decoration text-rendering underline-position underline-thickness unicode-bidi unicode-range units-per-em v-alphabetic v-hanging v-ideographic v-mathematical vector-effect vert-adv-y vert-origin-x vert-origin-y word-spacing writing-mode xmlns:xlink x-height"
  .split(" ")
  .forEach(function (e) {
    var t = e.replace(uy, ly);
    Xe[t] = new lt(t, 1, !1, e, null, !1, !1);
  });
"xlink:actuate xlink:arcrole xlink:role xlink:show xlink:title xlink:type"
  .split(" ")
  .forEach(function (e) {
    var t = e.replace(uy, ly);
    Xe[t] = new lt(t, 1, !1, e, "http://www.w3.org/1999/xlink", !1, !1);
  });
["xml:base", "xml:lang", "xml:space"].forEach(function (e) {
  var t = e.replace(uy, ly);
  Xe[t] = new lt(t, 1, !1, e, "http://www.w3.org/XML/1998/namespace", !1, !1);
});
["tabIndex", "crossOrigin"].forEach(function (e) {
  Xe[e] = new lt(e, 1, !1, e.toLowerCase(), null, !1, !1);
});
Xe.xlinkHref = new lt("xlinkHref", 1, !1, "xlink:href", "http://www.w3.org/1999/xlink", !0, !1);
["src", "href", "action", "formAction"].forEach(function (e) {
  Xe[e] = new lt(e, 1, !1, e.toLowerCase(), null, !0, !0);
});
function cy(e, t, n, r) {
  var i = Xe.hasOwnProperty(t) ? Xe[t] : null;
  (i !== null
    ? i.type !== 0
    : r || !(2 < t.length) || (t[0] !== "o" && t[0] !== "O") || (t[1] !== "n" && t[1] !== "N")) &&
    (SO(t, n, i, r) && (n = null),
    r || i === null
      ? xO(t) && (n === null ? e.removeAttribute(t) : e.setAttribute(t, "" + n))
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
var Xn = yO.__SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED,
  Ea = Symbol.for("react.element"),
  ki = Symbol.for("react.portal"),
  Pi = Symbol.for("react.fragment"),
  fy = Symbol.for("react.strict_mode"),
  kg = Symbol.for("react.profiler"),
  Ak = Symbol.for("react.provider"),
  Nk = Symbol.for("react.context"),
  dy = Symbol.for("react.forward_ref"),
  Pg = Symbol.for("react.suspense"),
  Rg = Symbol.for("react.suspense_list"),
  hy = Symbol.for("react.memo"),
  ar = Symbol.for("react.lazy"),
  Mk = Symbol.for("react.offscreen"),
  Lw = Symbol.iterator;
function Mo(e) {
  return e === null || typeof e != "object"
    ? null
    : ((e = (Lw && e[Lw]) || e["@@iterator"]), typeof e == "function" ? e : null);
}
var Se = Object.assign,
  Cc;
function Ko(e) {
  if (Cc === void 0)
    try {
      throw Error();
    } catch (n) {
      var t = n.stack.trim().match(/\n( *(at )?)/);
      Cc = (t && t[1]) || "";
    }
  return (
    `
` +
    Cc +
    e
  );
}
var Tc = !1;
function kc(e, t) {
  if (!e || Tc) return "";
  Tc = !0;
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
    (Tc = !1), (Error.prepareStackTrace = n);
  }
  return (e = e ? e.displayName || e.name : "") ? Ko(e) : "";
}
function bO(e) {
  switch (e.tag) {
    case 5:
      return Ko(e.type);
    case 16:
      return Ko("Lazy");
    case 13:
      return Ko("Suspense");
    case 19:
      return Ko("SuspenseList");
    case 0:
    case 2:
    case 15:
      return (e = kc(e.type, !1)), e;
    case 11:
      return (e = kc(e.type.render, !1)), e;
    case 1:
      return (e = kc(e.type, !0)), e;
    default:
      return "";
  }
}
function Ag(e) {
  if (e == null) return null;
  if (typeof e == "function") return e.displayName || e.name || null;
  if (typeof e == "string") return e;
  switch (e) {
    case Pi:
      return "Fragment";
    case ki:
      return "Portal";
    case kg:
      return "Profiler";
    case fy:
      return "StrictMode";
    case Pg:
      return "Suspense";
    case Rg:
      return "SuspenseList";
  }
  if (typeof e == "object")
    switch (e.$$typeof) {
      case Nk:
        return (e.displayName || "Context") + ".Consumer";
      case Ak:
        return (e._context.displayName || "Context") + ".Provider";
      case dy:
        var t = e.render;
        return (
          (e = e.displayName),
          e ||
            ((e = t.displayName || t.name || ""),
            (e = e !== "" ? "ForwardRef(" + e + ")" : "ForwardRef")),
          e
        );
      case hy:
        return (t = e.displayName || null), t !== null ? t : Ag(e.type) || "Memo";
      case ar:
        (t = e._payload), (e = e._init);
        try {
          return Ag(e(t));
        } catch {}
    }
  return null;
}
function EO(e) {
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
      return Ag(t);
    case 8:
      return t === fy ? "StrictMode" : "Mode";
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
function kr(e) {
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
function Ik(e) {
  var t = e.type;
  return (e = e.nodeName) && e.toLowerCase() === "input" && (t === "checkbox" || t === "radio");
}
function CO(e) {
  var t = Ik(e) ? "checked" : "value",
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
function Ca(e) {
  e._valueTracker || (e._valueTracker = CO(e));
}
function Dk(e) {
  if (!e) return !1;
  var t = e._valueTracker;
  if (!t) return !0;
  var n = t.getValue(),
    r = "";
  return (
    e && (r = Ik(e) ? (e.checked ? "true" : "false") : e.value),
    (e = r),
    e !== n ? (t.setValue(e), !0) : !1
  );
}
function Ru(e) {
  if (((e = e || (typeof document < "u" ? document : void 0)), typeof e > "u")) return null;
  try {
    return e.activeElement || e.body;
  } catch {
    return e.body;
  }
}
function Ng(e, t) {
  var n = t.checked;
  return Se({}, t, {
    defaultChecked: void 0,
    defaultValue: void 0,
    value: void 0,
    checked: n ?? e._wrapperState.initialChecked,
  });
}
function Fw(e, t) {
  var n = t.defaultValue == null ? "" : t.defaultValue,
    r = t.checked != null ? t.checked : t.defaultChecked;
  (n = kr(t.value != null ? t.value : n)),
    (e._wrapperState = {
      initialChecked: r,
      initialValue: n,
      controlled: t.type === "checkbox" || t.type === "radio" ? t.checked != null : t.value != null,
    });
}
function Ok(e, t) {
  (t = t.checked), t != null && cy(e, "checked", t, !1);
}
function Mg(e, t) {
  Ok(e, t);
  var n = kr(t.value),
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
    ? Ig(e, t.type, n)
    : t.hasOwnProperty("defaultValue") && Ig(e, t.type, kr(t.defaultValue)),
    t.checked == null && t.defaultChecked != null && (e.defaultChecked = !!t.defaultChecked);
}
function Vw(e, t, n) {
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
function Ig(e, t, n) {
  (t !== "number" || Ru(e.ownerDocument) !== e) &&
    (n == null
      ? (e.defaultValue = "" + e._wrapperState.initialValue)
      : e.defaultValue !== "" + n && (e.defaultValue = "" + n));
}
var Yo = Array.isArray;
function Hi(e, t, n, r) {
  if (((e = e.options), t)) {
    t = {};
    for (var i = 0; i < n.length; i++) t["$" + n[i]] = !0;
    for (n = 0; n < e.length; n++)
      (i = t.hasOwnProperty("$" + e[n].value)),
        e[n].selected !== i && (e[n].selected = i),
        i && r && (e[n].defaultSelected = !0);
  } else {
    for (n = "" + kr(n), t = null, i = 0; i < e.length; i++) {
      if (e[i].value === n) {
        (e[i].selected = !0), r && (e[i].defaultSelected = !0);
        return;
      }
      t !== null || e[i].disabled || (t = e[i]);
    }
    t !== null && (t.selected = !0);
  }
}
function Dg(e, t) {
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
      if (Yo(n)) {
        if (1 < n.length) throw Error(z(93));
        n = n[0];
      }
      t = n;
    }
    t == null && (t = ""), (n = t);
  }
  e._wrapperState = { initialValue: kr(n) };
}
function Lk(e, t) {
  var n = kr(t.value),
    r = kr(t.defaultValue);
  n != null &&
    ((n = "" + n),
    n !== e.value && (e.value = n),
    t.defaultValue == null && e.defaultValue !== n && (e.defaultValue = n)),
    r != null && (e.defaultValue = "" + r);
}
function qw(e) {
  var t = e.textContent;
  t === e._wrapperState.initialValue && t !== "" && t !== null && (e.value = t);
}
function Fk(e) {
  switch (e) {
    case "svg":
      return "http://www.w3.org/2000/svg";
    case "math":
      return "http://www.w3.org/1998/Math/MathML";
    default:
      return "http://www.w3.org/1999/xhtml";
  }
}
function Og(e, t) {
  return e == null || e === "http://www.w3.org/1999/xhtml"
    ? Fk(t)
    : e === "http://www.w3.org/2000/svg" && t === "foreignObject"
    ? "http://www.w3.org/1999/xhtml"
    : e;
}
var Ta,
  Vk = (function (e) {
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
        Ta = Ta || document.createElement("div"),
          Ta.innerHTML = "<svg>" + t.valueOf().toString() + "</svg>",
          t = Ta.firstChild;
        e.firstChild;

      )
        e.removeChild(e.firstChild);
      for (; t.firstChild; ) e.appendChild(t.firstChild);
    }
  });
function Ts(e, t) {
  if (t) {
    var n = e.firstChild;
    if (n && n === e.lastChild && n.nodeType === 3) {
      n.nodeValue = t;
      return;
    }
  }
  e.textContent = t;
}
var cs = {
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
  TO = ["Webkit", "ms", "Moz", "O"];
Object.keys(cs).forEach(function (e) {
  TO.forEach(function (t) {
    (t = t + e.charAt(0).toUpperCase() + e.substring(1)), (cs[t] = cs[e]);
  });
});
function jk(e, t, n) {
  return t == null || typeof t == "boolean" || t === ""
    ? ""
    : n || typeof t != "number" || t === 0 || (cs.hasOwnProperty(e) && cs[e])
    ? ("" + t).trim()
    : t + "px";
}
function qk(e, t) {
  e = e.style;
  for (var n in t)
    if (t.hasOwnProperty(n)) {
      var r = n.indexOf("--") === 0,
        i = jk(n, t[n], r);
      n === "float" && (n = "cssFloat"), r ? e.setProperty(n, i) : (e[n] = i);
    }
}
var kO = Se(
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
function Lg(e, t) {
  if (t) {
    if (kO[e] && (t.children != null || t.dangerouslySetInnerHTML != null)) throw Error(z(137, e));
    if (t.dangerouslySetInnerHTML != null) {
      if (t.children != null) throw Error(z(60));
      if (typeof t.dangerouslySetInnerHTML != "object" || !("__html" in t.dangerouslySetInnerHTML))
        throw Error(z(61));
    }
    if (t.style != null && typeof t.style != "object") throw Error(z(62));
  }
}
function Fg(e, t) {
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
var Vg = null;
function py(e) {
  return (
    (e = e.target || e.srcElement || window),
    e.correspondingUseElement && (e = e.correspondingUseElement),
    e.nodeType === 3 ? e.parentNode : e
  );
}
var jg = null,
  Gi = null,
  Wi = null;
function $w(e) {
  if ((e = sa(e))) {
    if (typeof jg != "function") throw Error(z(280));
    var t = e.stateNode;
    t && ((t = Cl(t)), jg(e.stateNode, e.type, t));
  }
}
function $k(e) {
  Gi ? (Wi ? Wi.push(e) : (Wi = [e])) : (Gi = e);
}
function zk() {
  if (Gi) {
    var e = Gi,
      t = Wi;
    if (((Wi = Gi = null), $w(e), t)) for (e = 0; e < t.length; e++) $w(t[e]);
  }
}
function Bk(e, t) {
  return e(t);
}
function Uk() {}
var Pc = !1;
function Hk(e, t, n) {
  if (Pc) return e(t, n);
  Pc = !0;
  try {
    return Bk(e, t, n);
  } finally {
    (Pc = !1), (Gi !== null || Wi !== null) && (Uk(), zk());
  }
}
function ks(e, t) {
  var n = e.stateNode;
  if (n === null) return null;
  var r = Cl(n);
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
var qg = !1;
if ($n)
  try {
    var Io = {};
    Object.defineProperty(Io, "passive", {
      get: function () {
        qg = !0;
      },
    }),
      window.addEventListener("test", Io, Io),
      window.removeEventListener("test", Io, Io);
  } catch {
    qg = !1;
  }
function PO(e, t, n, r, i, o, s, a, u) {
  var l = Array.prototype.slice.call(arguments, 3);
  try {
    t.apply(n, l);
  } catch (c) {
    this.onError(c);
  }
}
var fs = !1,
  Au = null,
  Nu = !1,
  $g = null,
  RO = {
    onError: function (e) {
      (fs = !0), (Au = e);
    },
  };
function AO(e, t, n, r, i, o, s, a, u) {
  (fs = !1), (Au = null), PO.apply(RO, arguments);
}
function NO(e, t, n, r, i, o, s, a, u) {
  if ((AO.apply(this, arguments), fs)) {
    if (fs) {
      var l = Au;
      (fs = !1), (Au = null);
    } else throw Error(z(198));
    Nu || ((Nu = !0), ($g = l));
  }
}
function fi(e) {
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
function Gk(e) {
  if (e.tag === 13) {
    var t = e.memoizedState;
    if ((t === null && ((e = e.alternate), e !== null && (t = e.memoizedState)), t !== null))
      return t.dehydrated;
  }
  return null;
}
function zw(e) {
  if (fi(e) !== e) throw Error(z(188));
}
function MO(e) {
  var t = e.alternate;
  if (!t) {
    if (((t = fi(e)), t === null)) throw Error(z(188));
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
        if (o === n) return zw(i), e;
        if (o === r) return zw(i), t;
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
function Wk(e) {
  return (e = MO(e)), e !== null ? Kk(e) : null;
}
function Kk(e) {
  if (e.tag === 5 || e.tag === 6) return e;
  for (e = e.child; e !== null; ) {
    var t = Kk(e);
    if (t !== null) return t;
    e = e.sibling;
  }
  return null;
}
var Yk = Tt.unstable_scheduleCallback,
  Bw = Tt.unstable_cancelCallback,
  IO = Tt.unstable_shouldYield,
  DO = Tt.unstable_requestPaint,
  Ne = Tt.unstable_now,
  OO = Tt.unstable_getCurrentPriorityLevel,
  my = Tt.unstable_ImmediatePriority,
  Xk = Tt.unstable_UserBlockingPriority,
  Mu = Tt.unstable_NormalPriority,
  LO = Tt.unstable_LowPriority,
  Zk = Tt.unstable_IdlePriority,
  _l = null,
  mn = null;
function FO(e) {
  if (mn && typeof mn.onCommitFiberRoot == "function")
    try {
      mn.onCommitFiberRoot(_l, e, void 0, (e.current.flags & 128) === 128);
    } catch {}
}
var Qt = Math.clz32 ? Math.clz32 : qO,
  VO = Math.log,
  jO = Math.LN2;
function qO(e) {
  return (e >>>= 0), e === 0 ? 32 : (31 - ((VO(e) / jO) | 0)) | 0;
}
var ka = 64,
  Pa = 4194304;
function Xo(e) {
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
function Iu(e, t) {
  var n = e.pendingLanes;
  if (n === 0) return 0;
  var r = 0,
    i = e.suspendedLanes,
    o = e.pingedLanes,
    s = n & 268435455;
  if (s !== 0) {
    var a = s & ~i;
    a !== 0 ? (r = Xo(a)) : ((o &= s), o !== 0 && (r = Xo(o)));
  } else (s = n & ~i), s !== 0 ? (r = Xo(s)) : o !== 0 && (r = Xo(o));
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
      (n = 31 - Qt(t)), (i = 1 << n), (r |= e[n]), (t &= ~i);
  return r;
}
function $O(e, t) {
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
function zO(e, t) {
  for (
    var n = e.suspendedLanes, r = e.pingedLanes, i = e.expirationTimes, o = e.pendingLanes;
    0 < o;

  ) {
    var s = 31 - Qt(o),
      a = 1 << s,
      u = i[s];
    u === -1 ? (!(a & n) || a & r) && (i[s] = $O(a, t)) : u <= t && (e.expiredLanes |= a),
      (o &= ~a);
  }
}
function zg(e) {
  return (e = e.pendingLanes & -1073741825), e !== 0 ? e : e & 1073741824 ? 1073741824 : 0;
}
function Qk() {
  var e = ka;
  return (ka <<= 1), !(ka & 4194240) && (ka = 64), e;
}
function Rc(e) {
  for (var t = [], n = 0; 31 > n; n++) t.push(e);
  return t;
}
function ia(e, t, n) {
  (e.pendingLanes |= t),
    t !== 536870912 && ((e.suspendedLanes = 0), (e.pingedLanes = 0)),
    (e = e.eventTimes),
    (t = 31 - Qt(t)),
    (e[t] = n);
}
function BO(e, t) {
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
    var i = 31 - Qt(n),
      o = 1 << i;
    (t[i] = 0), (r[i] = -1), (e[i] = -1), (n &= ~o);
  }
}
function gy(e, t) {
  var n = (e.entangledLanes |= t);
  for (e = e.entanglements; n; ) {
    var r = 31 - Qt(n),
      i = 1 << r;
    (i & t) | (e[r] & t) && (e[r] |= t), (n &= ~i);
  }
}
var ce = 0;
function Jk(e) {
  return (e &= -e), 1 < e ? (4 < e ? (e & 268435455 ? 16 : 536870912) : 4) : 1;
}
var eP,
  vy,
  tP,
  nP,
  rP,
  Bg = !1,
  Ra = [],
  vr = null,
  yr = null,
  wr = null,
  Ps = new Map(),
  Rs = new Map(),
  fr = [],
  UO = "mousedown mouseup touchcancel touchend touchstart auxclick dblclick pointercancel pointerdown pointerup dragend dragstart drop compositionend compositionstart keydown keypress keyup input textInput copy cut paste click change contextmenu reset submit".split(
    " "
  );
function Uw(e, t) {
  switch (e) {
    case "focusin":
    case "focusout":
      vr = null;
      break;
    case "dragenter":
    case "dragleave":
      yr = null;
      break;
    case "mouseover":
    case "mouseout":
      wr = null;
      break;
    case "pointerover":
    case "pointerout":
      Ps.delete(t.pointerId);
      break;
    case "gotpointercapture":
    case "lostpointercapture":
      Rs.delete(t.pointerId);
  }
}
function Do(e, t, n, r, i, o) {
  return e === null || e.nativeEvent !== o
    ? ((e = {
        blockedOn: t,
        domEventName: n,
        eventSystemFlags: r,
        nativeEvent: o,
        targetContainers: [i],
      }),
      t !== null && ((t = sa(t)), t !== null && vy(t)),
      e)
    : ((e.eventSystemFlags |= r),
      (t = e.targetContainers),
      i !== null && t.indexOf(i) === -1 && t.push(i),
      e);
}
function HO(e, t, n, r, i) {
  switch (t) {
    case "focusin":
      return (vr = Do(vr, e, t, n, r, i)), !0;
    case "dragenter":
      return (yr = Do(yr, e, t, n, r, i)), !0;
    case "mouseover":
      return (wr = Do(wr, e, t, n, r, i)), !0;
    case "pointerover":
      var o = i.pointerId;
      return Ps.set(o, Do(Ps.get(o) || null, e, t, n, r, i)), !0;
    case "gotpointercapture":
      return (o = i.pointerId), Rs.set(o, Do(Rs.get(o) || null, e, t, n, r, i)), !0;
  }
  return !1;
}
function iP(e) {
  var t = Ur(e.target);
  if (t !== null) {
    var n = fi(t);
    if (n !== null) {
      if (((t = n.tag), t === 13)) {
        if (((t = Gk(n)), t !== null)) {
          (e.blockedOn = t),
            rP(e.priority, function () {
              tP(n);
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
function au(e) {
  if (e.blockedOn !== null) return !1;
  for (var t = e.targetContainers; 0 < t.length; ) {
    var n = Ug(e.domEventName, e.eventSystemFlags, t[0], e.nativeEvent);
    if (n === null) {
      n = e.nativeEvent;
      var r = new n.constructor(n.type, n);
      (Vg = r), n.target.dispatchEvent(r), (Vg = null);
    } else return (t = sa(n)), t !== null && vy(t), (e.blockedOn = n), !1;
    t.shift();
  }
  return !0;
}
function Hw(e, t, n) {
  au(e) && n.delete(t);
}
function GO() {
  (Bg = !1),
    vr !== null && au(vr) && (vr = null),
    yr !== null && au(yr) && (yr = null),
    wr !== null && au(wr) && (wr = null),
    Ps.forEach(Hw),
    Rs.forEach(Hw);
}
function Oo(e, t) {
  e.blockedOn === t &&
    ((e.blockedOn = null),
    Bg || ((Bg = !0), Tt.unstable_scheduleCallback(Tt.unstable_NormalPriority, GO)));
}
function As(e) {
  function t(i) {
    return Oo(i, e);
  }
  if (0 < Ra.length) {
    Oo(Ra[0], e);
    for (var n = 1; n < Ra.length; n++) {
      var r = Ra[n];
      r.blockedOn === e && (r.blockedOn = null);
    }
  }
  for (
    vr !== null && Oo(vr, e),
      yr !== null && Oo(yr, e),
      wr !== null && Oo(wr, e),
      Ps.forEach(t),
      Rs.forEach(t),
      n = 0;
    n < fr.length;
    n++
  )
    (r = fr[n]), r.blockedOn === e && (r.blockedOn = null);
  for (; 0 < fr.length && ((n = fr[0]), n.blockedOn === null); )
    iP(n), n.blockedOn === null && fr.shift();
}
var Ki = Xn.ReactCurrentBatchConfig,
  Du = !0;
function WO(e, t, n, r) {
  var i = ce,
    o = Ki.transition;
  Ki.transition = null;
  try {
    (ce = 1), yy(e, t, n, r);
  } finally {
    (ce = i), (Ki.transition = o);
  }
}
function KO(e, t, n, r) {
  var i = ce,
    o = Ki.transition;
  Ki.transition = null;
  try {
    (ce = 4), yy(e, t, n, r);
  } finally {
    (ce = i), (Ki.transition = o);
  }
}
function yy(e, t, n, r) {
  if (Du) {
    var i = Ug(e, t, n, r);
    if (i === null) jc(e, t, r, Ou, n), Uw(e, r);
    else if (HO(i, e, t, n, r)) r.stopPropagation();
    else if ((Uw(e, r), t & 4 && -1 < UO.indexOf(e))) {
      for (; i !== null; ) {
        var o = sa(i);
        if ((o !== null && eP(o), (o = Ug(e, t, n, r)), o === null && jc(e, t, r, Ou, n), o === i))
          break;
        i = o;
      }
      i !== null && r.stopPropagation();
    } else jc(e, t, r, null, n);
  }
}
var Ou = null;
function Ug(e, t, n, r) {
  if (((Ou = null), (e = py(r)), (e = Ur(e)), e !== null))
    if (((t = fi(e)), t === null)) e = null;
    else if (((n = t.tag), n === 13)) {
      if (((e = Gk(t)), e !== null)) return e;
      e = null;
    } else if (n === 3) {
      if (t.stateNode.current.memoizedState.isDehydrated)
        return t.tag === 3 ? t.stateNode.containerInfo : null;
      e = null;
    } else t !== e && (e = null);
  return (Ou = e), null;
}
function oP(e) {
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
      switch (OO()) {
        case my:
          return 1;
        case Xk:
          return 4;
        case Mu:
        case LO:
          return 16;
        case Zk:
          return 536870912;
        default:
          return 16;
      }
    default:
      return 16;
  }
}
var mr = null,
  wy = null,
  uu = null;
function sP() {
  if (uu) return uu;
  var e,
    t = wy,
    n = t.length,
    r,
    i = "value" in mr ? mr.value : mr.textContent,
    o = i.length;
  for (e = 0; e < n && t[e] === i[e]; e++);
  var s = n - e;
  for (r = 1; r <= s && t[n - r] === i[o - r]; r++);
  return (uu = i.slice(e, 1 < r ? 1 - r : void 0));
}
function lu(e) {
  var t = e.keyCode;
  return (
    "charCode" in e ? ((e = e.charCode), e === 0 && t === 13 && (e = 13)) : (e = t),
    e === 10 && (e = 13),
    32 <= e || e === 13 ? e : 0
  );
}
function Aa() {
  return !0;
}
function Gw() {
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
        ? Aa
        : Gw),
      (this.isPropagationStopped = Gw),
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
          (this.isDefaultPrevented = Aa));
      },
      stopPropagation: function () {
        var n = this.nativeEvent;
        n &&
          (n.stopPropagation
            ? n.stopPropagation()
            : typeof n.cancelBubble != "unknown" && (n.cancelBubble = !0),
          (this.isPropagationStopped = Aa));
      },
      persist: function () {},
      isPersistent: Aa,
    }),
    t
  );
}
var xo = {
    eventPhase: 0,
    bubbles: 0,
    cancelable: 0,
    timeStamp: function (e) {
      return e.timeStamp || Date.now();
    },
    defaultPrevented: 0,
    isTrusted: 0,
  },
  xy = At(xo),
  oa = Se({}, xo, { view: 0, detail: 0 }),
  YO = At(oa),
  Ac,
  Nc,
  Lo,
  Sl = Se({}, oa, {
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
    getModifierState: _y,
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
        : (e !== Lo &&
            (Lo && e.type === "mousemove"
              ? ((Ac = e.screenX - Lo.screenX), (Nc = e.screenY - Lo.screenY))
              : (Nc = Ac = 0),
            (Lo = e)),
          Ac);
    },
    movementY: function (e) {
      return "movementY" in e ? e.movementY : Nc;
    },
  }),
  Ww = At(Sl),
  XO = Se({}, Sl, { dataTransfer: 0 }),
  ZO = At(XO),
  QO = Se({}, oa, { relatedTarget: 0 }),
  Mc = At(QO),
  JO = Se({}, xo, { animationName: 0, elapsedTime: 0, pseudoElement: 0 }),
  eL = At(JO),
  tL = Se({}, xo, {
    clipboardData: function (e) {
      return "clipboardData" in e ? e.clipboardData : window.clipboardData;
    },
  }),
  nL = At(tL),
  rL = Se({}, xo, { data: 0 }),
  Kw = At(rL),
  iL = {
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
  oL = {
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
  sL = { Alt: "altKey", Control: "ctrlKey", Meta: "metaKey", Shift: "shiftKey" };
function aL(e) {
  var t = this.nativeEvent;
  return t.getModifierState ? t.getModifierState(e) : (e = sL[e]) ? !!t[e] : !1;
}
function _y() {
  return aL;
}
var uL = Se({}, oa, {
    key: function (e) {
      if (e.key) {
        var t = iL[e.key] || e.key;
        if (t !== "Unidentified") return t;
      }
      return e.type === "keypress"
        ? ((e = lu(e)), e === 13 ? "Enter" : String.fromCharCode(e))
        : e.type === "keydown" || e.type === "keyup"
        ? oL[e.keyCode] || "Unidentified"
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
    getModifierState: _y,
    charCode: function (e) {
      return e.type === "keypress" ? lu(e) : 0;
    },
    keyCode: function (e) {
      return e.type === "keydown" || e.type === "keyup" ? e.keyCode : 0;
    },
    which: function (e) {
      return e.type === "keypress"
        ? lu(e)
        : e.type === "keydown" || e.type === "keyup"
        ? e.keyCode
        : 0;
    },
  }),
  lL = At(uL),
  cL = Se({}, Sl, {
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
  Yw = At(cL),
  fL = Se({}, oa, {
    touches: 0,
    targetTouches: 0,
    changedTouches: 0,
    altKey: 0,
    metaKey: 0,
    ctrlKey: 0,
    shiftKey: 0,
    getModifierState: _y,
  }),
  dL = At(fL),
  hL = Se({}, xo, { propertyName: 0, elapsedTime: 0, pseudoElement: 0 }),
  pL = At(hL),
  mL = Se({}, Sl, {
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
  gL = At(mL),
  vL = [9, 13, 27, 32],
  Sy = $n && "CompositionEvent" in window,
  ds = null;
$n && "documentMode" in document && (ds = document.documentMode);
var yL = $n && "TextEvent" in window && !ds,
  aP = $n && (!Sy || (ds && 8 < ds && 11 >= ds)),
  Xw = " ",
  Zw = !1;
function uP(e, t) {
  switch (e) {
    case "keyup":
      return vL.indexOf(t.keyCode) !== -1;
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
function lP(e) {
  return (e = e.detail), typeof e == "object" && "data" in e ? e.data : null;
}
var Ri = !1;
function wL(e, t) {
  switch (e) {
    case "compositionend":
      return lP(t);
    case "keypress":
      return t.which !== 32 ? null : ((Zw = !0), Xw);
    case "textInput":
      return (e = t.data), e === Xw && Zw ? null : e;
    default:
      return null;
  }
}
function xL(e, t) {
  if (Ri)
    return e === "compositionend" || (!Sy && uP(e, t))
      ? ((e = sP()), (uu = wy = mr = null), (Ri = !1), e)
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
      return aP && t.locale !== "ko" ? null : t.data;
    default:
      return null;
  }
}
var _L = {
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
function Qw(e) {
  var t = e && e.nodeName && e.nodeName.toLowerCase();
  return t === "input" ? !!_L[e.type] : t === "textarea";
}
function cP(e, t, n, r) {
  $k(r),
    (t = Lu(t, "onChange")),
    0 < t.length &&
      ((n = new xy("onChange", "change", null, n, r)), e.push({ event: n, listeners: t }));
}
var hs = null,
  Ns = null;
function SL(e) {
  _P(e, 0);
}
function bl(e) {
  var t = Mi(e);
  if (Dk(t)) return e;
}
function bL(e, t) {
  if (e === "change") return t;
}
var fP = !1;
if ($n) {
  var Ic;
  if ($n) {
    var Dc = "oninput" in document;
    if (!Dc) {
      var Jw = document.createElement("div");
      Jw.setAttribute("oninput", "return;"), (Dc = typeof Jw.oninput == "function");
    }
    Ic = Dc;
  } else Ic = !1;
  fP = Ic && (!document.documentMode || 9 < document.documentMode);
}
function e1() {
  hs && (hs.detachEvent("onpropertychange", dP), (Ns = hs = null));
}
function dP(e) {
  if (e.propertyName === "value" && bl(Ns)) {
    var t = [];
    cP(t, Ns, e, py(e)), Hk(SL, t);
  }
}
function EL(e, t, n) {
  e === "focusin"
    ? (e1(), (hs = t), (Ns = n), hs.attachEvent("onpropertychange", dP))
    : e === "focusout" && e1();
}
function CL(e) {
  if (e === "selectionchange" || e === "keyup" || e === "keydown") return bl(Ns);
}
function TL(e, t) {
  if (e === "click") return bl(t);
}
function kL(e, t) {
  if (e === "input" || e === "change") return bl(t);
}
function PL(e, t) {
  return (e === t && (e !== 0 || 1 / e === 1 / t)) || (e !== e && t !== t);
}
var tn = typeof Object.is == "function" ? Object.is : PL;
function Ms(e, t) {
  if (tn(e, t)) return !0;
  if (typeof e != "object" || e === null || typeof t != "object" || t === null) return !1;
  var n = Object.keys(e),
    r = Object.keys(t);
  if (n.length !== r.length) return !1;
  for (r = 0; r < n.length; r++) {
    var i = n[r];
    if (!Tg.call(t, i) || !tn(e[i], t[i])) return !1;
  }
  return !0;
}
function t1(e) {
  for (; e && e.firstChild; ) e = e.firstChild;
  return e;
}
function n1(e, t) {
  var n = t1(e);
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
    n = t1(n);
  }
}
function hP(e, t) {
  return e && t
    ? e === t
      ? !0
      : e && e.nodeType === 3
      ? !1
      : t && t.nodeType === 3
      ? hP(e, t.parentNode)
      : "contains" in e
      ? e.contains(t)
      : e.compareDocumentPosition
      ? !!(e.compareDocumentPosition(t) & 16)
      : !1
    : !1;
}
function pP() {
  for (var e = window, t = Ru(); t instanceof e.HTMLIFrameElement; ) {
    try {
      var n = typeof t.contentWindow.location.href == "string";
    } catch {
      n = !1;
    }
    if (n) e = t.contentWindow;
    else break;
    t = Ru(e.document);
  }
  return t;
}
function by(e) {
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
function RL(e) {
  var t = pP(),
    n = e.focusedElem,
    r = e.selectionRange;
  if (t !== n && n && n.ownerDocument && hP(n.ownerDocument.documentElement, n)) {
    if (r !== null && by(n)) {
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
          (i = n1(n, o));
        var s = n1(n, r);
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
var AL = $n && "documentMode" in document && 11 >= document.documentMode,
  Ai = null,
  Hg = null,
  ps = null,
  Gg = !1;
function r1(e, t, n) {
  var r = n.window === n ? n.document : n.nodeType === 9 ? n : n.ownerDocument;
  Gg ||
    Ai == null ||
    Ai !== Ru(r) ||
    ((r = Ai),
    "selectionStart" in r && by(r)
      ? (r = { start: r.selectionStart, end: r.selectionEnd })
      : ((r = ((r.ownerDocument && r.ownerDocument.defaultView) || window).getSelection()),
        (r = {
          anchorNode: r.anchorNode,
          anchorOffset: r.anchorOffset,
          focusNode: r.focusNode,
          focusOffset: r.focusOffset,
        })),
    (ps && Ms(ps, r)) ||
      ((ps = r),
      (r = Lu(Hg, "onSelect")),
      0 < r.length &&
        ((t = new xy("onSelect", "select", null, t, n)),
        e.push({ event: t, listeners: r }),
        (t.target = Ai))));
}
function Na(e, t) {
  var n = {};
  return (
    (n[e.toLowerCase()] = t.toLowerCase()),
    (n["Webkit" + e] = "webkit" + t),
    (n["Moz" + e] = "moz" + t),
    n
  );
}
var Ni = {
    animationend: Na("Animation", "AnimationEnd"),
    animationiteration: Na("Animation", "AnimationIteration"),
    animationstart: Na("Animation", "AnimationStart"),
    transitionend: Na("Transition", "TransitionEnd"),
  },
  Oc = {},
  mP = {};
$n &&
  ((mP = document.createElement("div").style),
  "AnimationEvent" in window ||
    (delete Ni.animationend.animation,
    delete Ni.animationiteration.animation,
    delete Ni.animationstart.animation),
  "TransitionEvent" in window || delete Ni.transitionend.transition);
function El(e) {
  if (Oc[e]) return Oc[e];
  if (!Ni[e]) return e;
  var t = Ni[e],
    n;
  for (n in t) if (t.hasOwnProperty(n) && n in mP) return (Oc[e] = t[n]);
  return e;
}
var gP = El("animationend"),
  vP = El("animationiteration"),
  yP = El("animationstart"),
  wP = El("transitionend"),
  xP = new Map(),
  i1 = "abort auxClick cancel canPlay canPlayThrough click close contextMenu copy cut drag dragEnd dragEnter dragExit dragLeave dragOver dragStart drop durationChange emptied encrypted ended error gotPointerCapture input invalid keyDown keyPress keyUp load loadedData loadedMetadata loadStart lostPointerCapture mouseDown mouseMove mouseOut mouseOver mouseUp paste pause play playing pointerCancel pointerDown pointerMove pointerOut pointerOver pointerUp progress rateChange reset resize seeked seeking stalled submit suspend timeUpdate touchCancel touchEnd touchStart volumeChange scroll toggle touchMove waiting wheel".split(
    " "
  );
function Nr(e, t) {
  xP.set(e, t), ci(t, [e]);
}
for (var Lc = 0; Lc < i1.length; Lc++) {
  var Fc = i1[Lc],
    NL = Fc.toLowerCase(),
    ML = Fc[0].toUpperCase() + Fc.slice(1);
  Nr(NL, "on" + ML);
}
Nr(gP, "onAnimationEnd");
Nr(vP, "onAnimationIteration");
Nr(yP, "onAnimationStart");
Nr("dblclick", "onDoubleClick");
Nr("focusin", "onFocus");
Nr("focusout", "onBlur");
Nr(wP, "onTransitionEnd");
no("onMouseEnter", ["mouseout", "mouseover"]);
no("onMouseLeave", ["mouseout", "mouseover"]);
no("onPointerEnter", ["pointerout", "pointerover"]);
no("onPointerLeave", ["pointerout", "pointerover"]);
ci("onChange", "change click focusin focusout input keydown keyup selectionchange".split(" "));
ci(
  "onSelect",
  "focusout contextmenu dragend focusin keydown keyup mousedown mouseup selectionchange".split(" ")
);
ci("onBeforeInput", ["compositionend", "keypress", "textInput", "paste"]);
ci("onCompositionEnd", "compositionend focusout keydown keypress keyup mousedown".split(" "));
ci("onCompositionStart", "compositionstart focusout keydown keypress keyup mousedown".split(" "));
ci("onCompositionUpdate", "compositionupdate focusout keydown keypress keyup mousedown".split(" "));
var Zo = "abort canplay canplaythrough durationchange emptied encrypted ended error loadeddata loadedmetadata loadstart pause play playing progress ratechange resize seeked seeking stalled suspend timeupdate volumechange waiting".split(
    " "
  ),
  IL = new Set("cancel close invalid load scroll toggle".split(" ").concat(Zo));
function o1(e, t, n) {
  var r = e.type || "unknown-event";
  (e.currentTarget = n), NO(r, t, void 0, e), (e.currentTarget = null);
}
function _P(e, t) {
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
          o1(i, a, l), (o = u);
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
          o1(i, a, l), (o = u);
        }
    }
  }
  if (Nu) throw ((e = $g), (Nu = !1), ($g = null), e);
}
function me(e, t) {
  var n = t[Zg];
  n === void 0 && (n = t[Zg] = new Set());
  var r = e + "__bubble";
  n.has(r) || (SP(t, e, 2, !1), n.add(r));
}
function Vc(e, t, n) {
  var r = 0;
  t && (r |= 4), SP(n, e, r, t);
}
var Ma = "_reactListening" + Math.random().toString(36).slice(2);
function Is(e) {
  if (!e[Ma]) {
    (e[Ma] = !0),
      Rk.forEach(function (n) {
        n !== "selectionchange" && (IL.has(n) || Vc(n, !1, e), Vc(n, !0, e));
      });
    var t = e.nodeType === 9 ? e : e.ownerDocument;
    t === null || t[Ma] || ((t[Ma] = !0), Vc("selectionchange", !1, t));
  }
}
function SP(e, t, n, r) {
  switch (oP(t)) {
    case 1:
      var i = WO;
      break;
    case 4:
      i = KO;
      break;
    default:
      i = yy;
  }
  (n = i.bind(null, t, n, e)),
    (i = void 0),
    !qg || (t !== "touchstart" && t !== "touchmove" && t !== "wheel") || (i = !0),
    r
      ? i !== void 0
        ? e.addEventListener(t, n, { capture: !0, passive: i })
        : e.addEventListener(t, n, !0)
      : i !== void 0
      ? e.addEventListener(t, n, { passive: i })
      : e.addEventListener(t, n, !1);
}
function jc(e, t, n, r, i) {
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
          if (((s = Ur(a)), s === null)) return;
          if (((u = s.tag), u === 5 || u === 6)) {
            r = o = s;
            continue e;
          }
          a = a.parentNode;
        }
      }
      r = r.return;
    }
  Hk(function () {
    var l = o,
      c = py(n),
      f = [];
    e: {
      var d = xP.get(e);
      if (d !== void 0) {
        var h = xy,
          v = e;
        switch (e) {
          case "keypress":
            if (lu(n) === 0) break e;
          case "keydown":
          case "keyup":
            h = lL;
            break;
          case "focusin":
            (v = "focus"), (h = Mc);
            break;
          case "focusout":
            (v = "blur"), (h = Mc);
            break;
          case "beforeblur":
          case "afterblur":
            h = Mc;
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
            h = Ww;
            break;
          case "drag":
          case "dragend":
          case "dragenter":
          case "dragexit":
          case "dragleave":
          case "dragover":
          case "dragstart":
          case "drop":
            h = ZO;
            break;
          case "touchcancel":
          case "touchend":
          case "touchmove":
          case "touchstart":
            h = dL;
            break;
          case gP:
          case vP:
          case yP:
            h = eL;
            break;
          case wP:
            h = pL;
            break;
          case "scroll":
            h = YO;
            break;
          case "wheel":
            h = gL;
            break;
          case "copy":
          case "cut":
          case "paste":
            h = nL;
            break;
          case "gotpointercapture":
          case "lostpointercapture":
          case "pointercancel":
          case "pointerdown":
          case "pointermove":
          case "pointerout":
          case "pointerover":
          case "pointerup":
            h = Yw;
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
              ((w = x), m !== null && ((x = ks(g, m)), x != null && p.push(Ds(g, x, w)))),
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
          d && n !== Vg && (v = n.relatedTarget || n.fromElement) && (Ur(v) || v[zn]))
        )
          break e;
        if (
          (h || d) &&
          ((d =
            c.window === c ? c : (d = c.ownerDocument) ? d.defaultView || d.parentWindow : window),
          h
            ? ((v = n.relatedTarget || n.toElement),
              (h = l),
              (v = v ? Ur(v) : null),
              v !== null && ((y = fi(v)), v !== y || (v.tag !== 5 && v.tag !== 6)) && (v = null))
            : ((h = null), (v = l)),
          h !== v)
        ) {
          if (
            ((p = Ww),
            (x = "onMouseLeave"),
            (m = "onMouseEnter"),
            (g = "mouse"),
            (e === "pointerout" || e === "pointerover") &&
              ((p = Yw), (x = "onPointerLeave"), (m = "onPointerEnter"), (g = "pointer")),
            (y = h == null ? d : Mi(h)),
            (w = v == null ? d : Mi(v)),
            (d = new p(x, g + "leave", h, n, c)),
            (d.target = y),
            (d.relatedTarget = w),
            (x = null),
            Ur(c) === l &&
              ((p = new p(m, g + "enter", v, n, c)),
              (p.target = w),
              (p.relatedTarget = y),
              (x = p)),
            (y = x),
            h && v)
          )
            t: {
              for (p = h, m = v, g = 0, w = p; w; w = yi(w)) g++;
              for (w = 0, x = m; x; x = yi(x)) w++;
              for (; 0 < g - w; ) (p = yi(p)), g--;
              for (; 0 < w - g; ) (m = yi(m)), w--;
              for (; g--; ) {
                if (p === m || (m !== null && p === m.alternate)) break t;
                (p = yi(p)), (m = yi(m));
              }
              p = null;
            }
          else p = null;
          h !== null && s1(f, d, h, p, !1), v !== null && y !== null && s1(f, y, v, p, !0);
        }
      }
      e: {
        if (
          ((d = l ? Mi(l) : window),
          (h = d.nodeName && d.nodeName.toLowerCase()),
          h === "select" || (h === "input" && d.type === "file"))
        )
          var S = bL;
        else if (Qw(d))
          if (fP) S = kL;
          else {
            S = CL;
            var C = EL;
          }
        else
          (h = d.nodeName) &&
            h.toLowerCase() === "input" &&
            (d.type === "checkbox" || d.type === "radio") &&
            (S = TL);
        if (S && (S = S(e, l))) {
          cP(f, S, n, c);
          break e;
        }
        C && C(e, d, l),
          e === "focusout" &&
            (C = d._wrapperState) &&
            C.controlled &&
            d.type === "number" &&
            Ig(d, "number", d.value);
      }
      switch (((C = l ? Mi(l) : window), e)) {
        case "focusin":
          (Qw(C) || C.contentEditable === "true") && ((Ai = C), (Hg = l), (ps = null));
          break;
        case "focusout":
          ps = Hg = Ai = null;
          break;
        case "mousedown":
          Gg = !0;
          break;
        case "contextmenu":
        case "mouseup":
        case "dragend":
          (Gg = !1), r1(f, n, c);
          break;
        case "selectionchange":
          if (AL) break;
        case "keydown":
        case "keyup":
          r1(f, n, c);
      }
      var E;
      if (Sy)
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
        Ri
          ? uP(e, n) && (T = "onCompositionEnd")
          : e === "keydown" && n.keyCode === 229 && (T = "onCompositionStart");
      T &&
        (aP &&
          n.locale !== "ko" &&
          (Ri || T !== "onCompositionStart"
            ? T === "onCompositionEnd" && Ri && (E = sP())
            : ((mr = c), (wy = "value" in mr ? mr.value : mr.textContent), (Ri = !0))),
        (C = Lu(l, T)),
        0 < C.length &&
          ((T = new Kw(T, e, null, n, c)),
          f.push({ event: T, listeners: C }),
          E ? (T.data = E) : ((E = lP(n)), E !== null && (T.data = E)))),
        (E = yL ? wL(e, n) : xL(e, n)) &&
          ((l = Lu(l, "onBeforeInput")),
          0 < l.length &&
            ((c = new Kw("onBeforeInput", "beforeinput", null, n, c)),
            f.push({ event: c, listeners: l }),
            (c.data = E)));
    }
    _P(f, t);
  });
}
function Ds(e, t, n) {
  return { instance: e, listener: t, currentTarget: n };
}
function Lu(e, t) {
  for (var n = t + "Capture", r = []; e !== null; ) {
    var i = e,
      o = i.stateNode;
    i.tag === 5 &&
      o !== null &&
      ((i = o),
      (o = ks(e, n)),
      o != null && r.unshift(Ds(e, o, i)),
      (o = ks(e, t)),
      o != null && r.push(Ds(e, o, i))),
      (e = e.return);
  }
  return r;
}
function yi(e) {
  if (e === null) return null;
  do e = e.return;
  while (e && e.tag !== 5);
  return e || null;
}
function s1(e, t, n, r, i) {
  for (var o = t._reactName, s = []; n !== null && n !== r; ) {
    var a = n,
      u = a.alternate,
      l = a.stateNode;
    if (u !== null && u === r) break;
    a.tag === 5 &&
      l !== null &&
      ((a = l),
      i
        ? ((u = ks(n, o)), u != null && s.unshift(Ds(n, u, a)))
        : i || ((u = ks(n, o)), u != null && s.push(Ds(n, u, a)))),
      (n = n.return);
  }
  s.length !== 0 && e.push({ event: t, listeners: s });
}
var DL = /\r\n?/g,
  OL = /\u0000|\uFFFD/g;
function a1(e) {
  return (typeof e == "string" ? e : "" + e)
    .replace(
      DL,
      `
`
    )
    .replace(OL, "");
}
function Ia(e, t, n) {
  if (((t = a1(t)), a1(e) !== t && n)) throw Error(z(425));
}
function Fu() {}
var Wg = null,
  Kg = null;
function Yg(e, t) {
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
var Xg = typeof setTimeout == "function" ? setTimeout : void 0,
  LL = typeof clearTimeout == "function" ? clearTimeout : void 0,
  u1 = typeof Promise == "function" ? Promise : void 0,
  FL =
    typeof queueMicrotask == "function"
      ? queueMicrotask
      : typeof u1 < "u"
      ? function (e) {
          return u1.resolve(null).then(e).catch(VL);
        }
      : Xg;
function VL(e) {
  setTimeout(function () {
    throw e;
  });
}
function qc(e, t) {
  var n = t,
    r = 0;
  do {
    var i = n.nextSibling;
    if ((e.removeChild(n), i && i.nodeType === 8))
      if (((n = i.data), n === "/$")) {
        if (r === 0) {
          e.removeChild(i), As(t);
          return;
        }
        r--;
      } else (n !== "$" && n !== "$?" && n !== "$!") || r++;
    n = i;
  } while (n);
  As(t);
}
function xr(e) {
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
function l1(e) {
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
var _o = Math.random().toString(36).slice(2),
  dn = "__reactFiber$" + _o,
  Os = "__reactProps$" + _o,
  zn = "__reactContainer$" + _o,
  Zg = "__reactEvents$" + _o,
  jL = "__reactListeners$" + _o,
  qL = "__reactHandles$" + _o;
function Ur(e) {
  var t = e[dn];
  if (t) return t;
  for (var n = e.parentNode; n; ) {
    if ((t = n[zn] || n[dn])) {
      if (((n = t.alternate), t.child !== null || (n !== null && n.child !== null)))
        for (e = l1(e); e !== null; ) {
          if ((n = e[dn])) return n;
          e = l1(e);
        }
      return t;
    }
    (e = n), (n = e.parentNode);
  }
  return null;
}
function sa(e) {
  return (
    (e = e[dn] || e[zn]),
    !e || (e.tag !== 5 && e.tag !== 6 && e.tag !== 13 && e.tag !== 3) ? null : e
  );
}
function Mi(e) {
  if (e.tag === 5 || e.tag === 6) return e.stateNode;
  throw Error(z(33));
}
function Cl(e) {
  return e[Os] || null;
}
var Qg = [],
  Ii = -1;
function Mr(e) {
  return { current: e };
}
function ge(e) {
  0 > Ii || ((e.current = Qg[Ii]), (Qg[Ii] = null), Ii--);
}
function de(e, t) {
  Ii++, (Qg[Ii] = e.current), (e.current = t);
}
var Pr = {},
  rt = Mr(Pr),
  gt = Mr(!1),
  ni = Pr;
function ro(e, t) {
  var n = e.type.contextTypes;
  if (!n) return Pr;
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
function Vu() {
  ge(gt), ge(rt);
}
function c1(e, t, n) {
  if (rt.current !== Pr) throw Error(z(168));
  de(rt, t), de(gt, n);
}
function bP(e, t, n) {
  var r = e.stateNode;
  if (((t = t.childContextTypes), typeof r.getChildContext != "function")) return n;
  r = r.getChildContext();
  for (var i in r) if (!(i in t)) throw Error(z(108, EO(e) || "Unknown", i));
  return Se({}, n, r);
}
function ju(e) {
  return (
    (e = ((e = e.stateNode) && e.__reactInternalMemoizedMergedChildContext) || Pr),
    (ni = rt.current),
    de(rt, e),
    de(gt, gt.current),
    !0
  );
}
function f1(e, t, n) {
  var r = e.stateNode;
  if (!r) throw Error(z(169));
  n
    ? ((e = bP(e, t, ni)),
      (r.__reactInternalMemoizedMergedChildContext = e),
      ge(gt),
      ge(rt),
      de(rt, e))
    : ge(gt),
    de(gt, n);
}
var Nn = null,
  Tl = !1,
  $c = !1;
function EP(e) {
  Nn === null ? (Nn = [e]) : Nn.push(e);
}
function $L(e) {
  (Tl = !0), EP(e);
}
function Ir() {
  if (!$c && Nn !== null) {
    $c = !0;
    var e = 0,
      t = ce;
    try {
      var n = Nn;
      for (ce = 1; e < n.length; e++) {
        var r = n[e];
        do r = r(!0);
        while (r !== null);
      }
      (Nn = null), (Tl = !1);
    } catch (i) {
      throw (Nn !== null && (Nn = Nn.slice(e + 1)), Yk(my, Ir), i);
    } finally {
      (ce = t), ($c = !1);
    }
  }
  return null;
}
var Di = [],
  Oi = 0,
  qu = null,
  $u = 0,
  It = [],
  Dt = 0,
  ri = null,
  Mn = 1,
  In = "";
function jr(e, t) {
  (Di[Oi++] = $u), (Di[Oi++] = qu), (qu = e), ($u = t);
}
function CP(e, t, n) {
  (It[Dt++] = Mn), (It[Dt++] = In), (It[Dt++] = ri), (ri = e);
  var r = Mn;
  e = In;
  var i = 32 - Qt(r) - 1;
  (r &= ~(1 << i)), (n += 1);
  var o = 32 - Qt(t) + i;
  if (30 < o) {
    var s = i - (i % 5);
    (o = (r & ((1 << s) - 1)).toString(32)),
      (r >>= s),
      (i -= s),
      (Mn = (1 << (32 - Qt(t) + i)) | (n << i) | r),
      (In = o + e);
  } else (Mn = (1 << o) | (n << i) | r), (In = e);
}
function Ey(e) {
  e.return !== null && (jr(e, 1), CP(e, 1, 0));
}
function Cy(e) {
  for (; e === qu; ) (qu = Di[--Oi]), (Di[Oi] = null), ($u = Di[--Oi]), (Di[Oi] = null);
  for (; e === ri; )
    (ri = It[--Dt]),
      (It[Dt] = null),
      (In = It[--Dt]),
      (It[Dt] = null),
      (Mn = It[--Dt]),
      (It[Dt] = null);
}
var Et = null,
  bt = null,
  ve = !1,
  Xt = null;
function TP(e, t) {
  var n = Lt(5, null, null, 0);
  (n.elementType = "DELETED"),
    (n.stateNode = t),
    (n.return = e),
    (t = e.deletions),
    t === null ? ((e.deletions = [n]), (e.flags |= 16)) : t.push(n);
}
function d1(e, t) {
  switch (e.tag) {
    case 5:
      var n = e.type;
      return (
        (t = t.nodeType !== 1 || n.toLowerCase() !== t.nodeName.toLowerCase() ? null : t),
        t !== null ? ((e.stateNode = t), (Et = e), (bt = xr(t.firstChild)), !0) : !1
      );
    case 6:
      return (
        (t = e.pendingProps === "" || t.nodeType !== 3 ? null : t),
        t !== null ? ((e.stateNode = t), (Et = e), (bt = null), !0) : !1
      );
    case 13:
      return (
        (t = t.nodeType !== 8 ? null : t),
        t !== null
          ? ((n = ri !== null ? { id: Mn, overflow: In } : null),
            (e.memoizedState = { dehydrated: t, treeContext: n, retryLane: 1073741824 }),
            (n = Lt(18, null, null, 0)),
            (n.stateNode = t),
            (n.return = e),
            (e.child = n),
            (Et = e),
            (bt = null),
            !0)
          : !1
      );
    default:
      return !1;
  }
}
function Jg(e) {
  return (e.mode & 1) !== 0 && (e.flags & 128) === 0;
}
function ev(e) {
  if (ve) {
    var t = bt;
    if (t) {
      var n = t;
      if (!d1(e, t)) {
        if (Jg(e)) throw Error(z(418));
        t = xr(n.nextSibling);
        var r = Et;
        t && d1(e, t) ? TP(r, n) : ((e.flags = (e.flags & -4097) | 2), (ve = !1), (Et = e));
      }
    } else {
      if (Jg(e)) throw Error(z(418));
      (e.flags = (e.flags & -4097) | 2), (ve = !1), (Et = e);
    }
  }
}
function h1(e) {
  for (e = e.return; e !== null && e.tag !== 5 && e.tag !== 3 && e.tag !== 13; ) e = e.return;
  Et = e;
}
function Da(e) {
  if (e !== Et) return !1;
  if (!ve) return h1(e), (ve = !0), !1;
  var t;
  if (
    ((t = e.tag !== 3) &&
      !(t = e.tag !== 5) &&
      ((t = e.type), (t = t !== "head" && t !== "body" && !Yg(e.type, e.memoizedProps))),
    t && (t = bt))
  ) {
    if (Jg(e)) throw (kP(), Error(z(418)));
    for (; t; ) TP(e, t), (t = xr(t.nextSibling));
  }
  if ((h1(e), e.tag === 13)) {
    if (((e = e.memoizedState), (e = e !== null ? e.dehydrated : null), !e)) throw Error(z(317));
    e: {
      for (e = e.nextSibling, t = 0; e; ) {
        if (e.nodeType === 8) {
          var n = e.data;
          if (n === "/$") {
            if (t === 0) {
              bt = xr(e.nextSibling);
              break e;
            }
            t--;
          } else (n !== "$" && n !== "$!" && n !== "$?") || t++;
        }
        e = e.nextSibling;
      }
      bt = null;
    }
  } else bt = Et ? xr(e.stateNode.nextSibling) : null;
  return !0;
}
function kP() {
  for (var e = bt; e; ) e = xr(e.nextSibling);
}
function io() {
  (bt = Et = null), (ve = !1);
}
function Ty(e) {
  Xt === null ? (Xt = [e]) : Xt.push(e);
}
var zL = Xn.ReactCurrentBatchConfig;
function Fo(e, t, n) {
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
function Oa(e, t) {
  throw (
    ((e = Object.prototype.toString.call(t)),
    Error(
      z(31, e === "[object Object]" ? "object with keys {" + Object.keys(t).join(", ") + "}" : e)
    ))
  );
}
function p1(e) {
  var t = e._init;
  return t(e._payload);
}
function PP(e) {
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
    return (m = Er(m, g)), (m.index = 0), (m.sibling = null), m;
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
      ? ((g = Kc(w, m.mode, x)), (g.return = m), g)
      : ((g = i(g, w)), (g.return = m), g);
  }
  function u(m, g, w, x) {
    var S = w.type;
    return S === Pi
      ? c(m, g, w.props.children, x, w.key)
      : g !== null &&
        (g.elementType === S ||
          (typeof S == "object" && S !== null && S.$$typeof === ar && p1(S) === g.type))
      ? ((x = i(g, w.props)), (x.ref = Fo(m, g, w)), (x.return = m), x)
      : ((x = gu(w.type, w.key, w.props, null, m.mode, x)),
        (x.ref = Fo(m, g, w)),
        (x.return = m),
        x);
  }
  function l(m, g, w, x) {
    return g === null ||
      g.tag !== 4 ||
      g.stateNode.containerInfo !== w.containerInfo ||
      g.stateNode.implementation !== w.implementation
      ? ((g = Yc(w, m.mode, x)), (g.return = m), g)
      : ((g = i(g, w.children || [])), (g.return = m), g);
  }
  function c(m, g, w, x, S) {
    return g === null || g.tag !== 7
      ? ((g = Qr(w, m.mode, x, S)), (g.return = m), g)
      : ((g = i(g, w)), (g.return = m), g);
  }
  function f(m, g, w) {
    if ((typeof g == "string" && g !== "") || typeof g == "number")
      return (g = Kc("" + g, m.mode, w)), (g.return = m), g;
    if (typeof g == "object" && g !== null) {
      switch (g.$$typeof) {
        case Ea:
          return (
            (w = gu(g.type, g.key, g.props, null, m.mode, w)),
            (w.ref = Fo(m, null, g)),
            (w.return = m),
            w
          );
        case ki:
          return (g = Yc(g, m.mode, w)), (g.return = m), g;
        case ar:
          var x = g._init;
          return f(m, x(g._payload), w);
      }
      if (Yo(g) || Mo(g)) return (g = Qr(g, m.mode, w, null)), (g.return = m), g;
      Oa(m, g);
    }
    return null;
  }
  function d(m, g, w, x) {
    var S = g !== null ? g.key : null;
    if ((typeof w == "string" && w !== "") || typeof w == "number")
      return S !== null ? null : a(m, g, "" + w, x);
    if (typeof w == "object" && w !== null) {
      switch (w.$$typeof) {
        case Ea:
          return w.key === S ? u(m, g, w, x) : null;
        case ki:
          return w.key === S ? l(m, g, w, x) : null;
        case ar:
          return (S = w._init), d(m, g, S(w._payload), x);
      }
      if (Yo(w) || Mo(w)) return S !== null ? null : c(m, g, w, x, null);
      Oa(m, w);
    }
    return null;
  }
  function h(m, g, w, x, S) {
    if ((typeof x == "string" && x !== "") || typeof x == "number")
      return (m = m.get(w) || null), a(g, m, "" + x, S);
    if (typeof x == "object" && x !== null) {
      switch (x.$$typeof) {
        case Ea:
          return (m = m.get(x.key === null ? w : x.key) || null), u(g, m, x, S);
        case ki:
          return (m = m.get(x.key === null ? w : x.key) || null), l(g, m, x, S);
        case ar:
          var C = x._init;
          return h(m, g, w, C(x._payload), S);
      }
      if (Yo(x) || Mo(x)) return (m = m.get(w) || null), c(g, m, x, S, null);
      Oa(g, x);
    }
    return null;
  }
  function v(m, g, w, x) {
    for (var S = null, C = null, E = g, T = (g = 0), P = null; E !== null && T < w.length; T++) {
      E.index > T ? ((P = E), (E = null)) : (P = E.sibling);
      var N = d(m, E, w[T], x);
      if (N === null) {
        E === null && (E = P);
        break;
      }
      e && E && N.alternate === null && t(m, E),
        (g = o(N, g, T)),
        C === null ? (S = N) : (C.sibling = N),
        (C = N),
        (E = P);
    }
    if (T === w.length) return n(m, E), ve && jr(m, T), S;
    if (E === null) {
      for (; T < w.length; T++)
        (E = f(m, w[T], x)),
          E !== null && ((g = o(E, g, T)), C === null ? (S = E) : (C.sibling = E), (C = E));
      return ve && jr(m, T), S;
    }
    for (E = r(m, E); T < w.length; T++)
      (P = h(E, m, T, w[T], x)),
        P !== null &&
          (e && P.alternate !== null && E.delete(P.key === null ? T : P.key),
          (g = o(P, g, T)),
          C === null ? (S = P) : (C.sibling = P),
          (C = P));
    return (
      e &&
        E.forEach(function (I) {
          return t(m, I);
        }),
      ve && jr(m, T),
      S
    );
  }
  function p(m, g, w, x) {
    var S = Mo(w);
    if (typeof S != "function") throw Error(z(150));
    if (((w = S.call(w)), w == null)) throw Error(z(151));
    for (
      var C = (S = null), E = g, T = (g = 0), P = null, N = w.next();
      E !== null && !N.done;
      T++, N = w.next()
    ) {
      E.index > T ? ((P = E), (E = null)) : (P = E.sibling);
      var I = d(m, E, N.value, x);
      if (I === null) {
        E === null && (E = P);
        break;
      }
      e && E && I.alternate === null && t(m, E),
        (g = o(I, g, T)),
        C === null ? (S = I) : (C.sibling = I),
        (C = I),
        (E = P);
    }
    if (N.done) return n(m, E), ve && jr(m, T), S;
    if (E === null) {
      for (; !N.done; T++, N = w.next())
        (N = f(m, N.value, x)),
          N !== null && ((g = o(N, g, T)), C === null ? (S = N) : (C.sibling = N), (C = N));
      return ve && jr(m, T), S;
    }
    for (E = r(m, E); !N.done; T++, N = w.next())
      (N = h(E, m, T, N.value, x)),
        N !== null &&
          (e && N.alternate !== null && E.delete(N.key === null ? T : N.key),
          (g = o(N, g, T)),
          C === null ? (S = N) : (C.sibling = N),
          (C = N));
    return (
      e &&
        E.forEach(function (V) {
          return t(m, V);
        }),
      ve && jr(m, T),
      S
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
        case Ea:
          e: {
            for (var S = w.key, C = g; C !== null; ) {
              if (C.key === S) {
                if (((S = w.type), S === Pi)) {
                  if (C.tag === 7) {
                    n(m, C.sibling), (g = i(C, w.props.children)), (g.return = m), (m = g);
                    break e;
                  }
                } else if (
                  C.elementType === S ||
                  (typeof S == "object" && S !== null && S.$$typeof === ar && p1(S) === C.type)
                ) {
                  n(m, C.sibling),
                    (g = i(C, w.props)),
                    (g.ref = Fo(m, C, w)),
                    (g.return = m),
                    (m = g);
                  break e;
                }
                n(m, C);
                break;
              } else t(m, C);
              C = C.sibling;
            }
            w.type === Pi
              ? ((g = Qr(w.props.children, m.mode, x, w.key)), (g.return = m), (m = g))
              : ((x = gu(w.type, w.key, w.props, null, m.mode, x)),
                (x.ref = Fo(m, g, w)),
                (x.return = m),
                (m = x));
          }
          return s(m);
        case ki:
          e: {
            for (C = w.key; g !== null; ) {
              if (g.key === C)
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
            (g = Yc(w, m.mode, x)), (g.return = m), (m = g);
          }
          return s(m);
        case ar:
          return (C = w._init), y(m, g, C(w._payload), x);
      }
      if (Yo(w)) return v(m, g, w, x);
      if (Mo(w)) return p(m, g, w, x);
      Oa(m, w);
    }
    return (typeof w == "string" && w !== "") || typeof w == "number"
      ? ((w = "" + w),
        g !== null && g.tag === 6
          ? (n(m, g.sibling), (g = i(g, w)), (g.return = m), (m = g))
          : (n(m, g), (g = Kc(w, m.mode, x)), (g.return = m), (m = g)),
        s(m))
      : n(m, g);
  }
  return y;
}
var oo = PP(!0),
  RP = PP(!1),
  zu = Mr(null),
  Bu = null,
  Li = null,
  ky = null;
function Py() {
  ky = Li = Bu = null;
}
function Ry(e) {
  var t = zu.current;
  ge(zu), (e._currentValue = t);
}
function tv(e, t, n) {
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
function Yi(e, t) {
  (Bu = e),
    (ky = Li = null),
    (e = e.dependencies),
    e !== null && e.firstContext !== null && (e.lanes & t && (pt = !0), (e.firstContext = null));
}
function jt(e) {
  var t = e._currentValue;
  if (ky !== e)
    if (((e = { context: e, memoizedValue: t, next: null }), Li === null)) {
      if (Bu === null) throw Error(z(308));
      (Li = e), (Bu.dependencies = { lanes: 0, firstContext: e });
    } else Li = Li.next = e;
  return t;
}
var Hr = null;
function Ay(e) {
  Hr === null ? (Hr = [e]) : Hr.push(e);
}
function AP(e, t, n, r) {
  var i = t.interleaved;
  return (
    i === null ? ((n.next = n), Ay(t)) : ((n.next = i.next), (i.next = n)),
    (t.interleaved = n),
    Bn(e, r)
  );
}
function Bn(e, t) {
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
var ur = !1;
function Ny(e) {
  e.updateQueue = {
    baseState: e.memoizedState,
    firstBaseUpdate: null,
    lastBaseUpdate: null,
    shared: { pending: null, interleaved: null, lanes: 0 },
    effects: null,
  };
}
function NP(e, t) {
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
function Fn(e, t) {
  return { eventTime: e, lane: t, tag: 0, payload: null, callback: null, next: null };
}
function _r(e, t, n) {
  var r = e.updateQueue;
  if (r === null) return null;
  if (((r = r.shared), ae & 2)) {
    var i = r.pending;
    return i === null ? (t.next = t) : ((t.next = i.next), (i.next = t)), (r.pending = t), Bn(e, n);
  }
  return (
    (i = r.interleaved),
    i === null ? ((t.next = t), Ay(r)) : ((t.next = i.next), (i.next = t)),
    (r.interleaved = t),
    Bn(e, n)
  );
}
function cu(e, t, n) {
  if (((t = t.updateQueue), t !== null && ((t = t.shared), (n & 4194240) !== 0))) {
    var r = t.lanes;
    (r &= e.pendingLanes), (n |= r), (t.lanes = n), gy(e, n);
  }
}
function m1(e, t) {
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
function Uu(e, t, n, r) {
  var i = e.updateQueue;
  ur = !1;
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
          (c = c.next = {
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
              ur = !0;
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
    (oi |= s), (e.lanes = s), (e.memoizedState = f);
  }
}
function g1(e, t, n) {
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
var aa = {},
  gn = Mr(aa),
  Ls = Mr(aa),
  Fs = Mr(aa);
function Gr(e) {
  if (e === aa) throw Error(z(174));
  return e;
}
function My(e, t) {
  switch ((de(Fs, t), de(Ls, e), de(gn, aa), (e = t.nodeType), e)) {
    case 9:
    case 11:
      t = (t = t.documentElement) ? t.namespaceURI : Og(null, "");
      break;
    default:
      (e = e === 8 ? t.parentNode : t),
        (t = e.namespaceURI || null),
        (e = e.tagName),
        (t = Og(t, e));
  }
  ge(gn), de(gn, t);
}
function so() {
  ge(gn), ge(Ls), ge(Fs);
}
function MP(e) {
  Gr(Fs.current);
  var t = Gr(gn.current),
    n = Og(t, e.type);
  t !== n && (de(Ls, e), de(gn, n));
}
function Iy(e) {
  Ls.current === e && (ge(gn), ge(Ls));
}
var we = Mr(0);
function Hu(e) {
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
var zc = [];
function Dy() {
  for (var e = 0; e < zc.length; e++) zc[e]._workInProgressVersionPrimary = null;
  zc.length = 0;
}
var fu = Xn.ReactCurrentDispatcher,
  Bc = Xn.ReactCurrentBatchConfig,
  ii = 0,
  _e = null,
  Oe = null,
  ze = null,
  Gu = !1,
  ms = !1,
  Vs = 0,
  BL = 0;
function Je() {
  throw Error(z(321));
}
function Oy(e, t) {
  if (t === null) return !1;
  for (var n = 0; n < t.length && n < e.length; n++) if (!tn(e[n], t[n])) return !1;
  return !0;
}
function Ly(e, t, n, r, i, o) {
  if (
    ((ii = o),
    (_e = t),
    (t.memoizedState = null),
    (t.updateQueue = null),
    (t.lanes = 0),
    (fu.current = e === null || e.memoizedState === null ? WL : KL),
    (e = n(r, i)),
    ms)
  ) {
    o = 0;
    do {
      if (((ms = !1), (Vs = 0), 25 <= o)) throw Error(z(301));
      (o += 1), (ze = Oe = null), (t.updateQueue = null), (fu.current = YL), (e = n(r, i));
    } while (ms);
  }
  if (
    ((fu.current = Wu),
    (t = Oe !== null && Oe.next !== null),
    (ii = 0),
    (ze = Oe = _e = null),
    (Gu = !1),
    t)
  )
    throw Error(z(300));
  return e;
}
function Fy() {
  var e = Vs !== 0;
  return (Vs = 0), e;
}
function fn() {
  var e = { memoizedState: null, baseState: null, baseQueue: null, queue: null, next: null };
  return ze === null ? (_e.memoizedState = ze = e) : (ze = ze.next = e), ze;
}
function qt() {
  if (Oe === null) {
    var e = _e.alternate;
    e = e !== null ? e.memoizedState : null;
  } else e = Oe.next;
  var t = ze === null ? _e.memoizedState : ze.next;
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
      ze === null ? (_e.memoizedState = ze = e) : (ze = ze.next = e);
  }
  return ze;
}
function js(e, t) {
  return typeof t == "function" ? t(e) : t;
}
function Uc(e) {
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
      if ((ii & c) === c)
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
        u === null ? ((a = u = f), (s = r)) : (u = u.next = f), (_e.lanes |= c), (oi |= c);
      }
      l = l.next;
    } while (l !== null && l !== o);
    u === null ? (s = r) : (u.next = a),
      tn(r, t.memoizedState) || (pt = !0),
      (t.memoizedState = r),
      (t.baseState = s),
      (t.baseQueue = u),
      (n.lastRenderedState = r);
  }
  if (((e = n.interleaved), e !== null)) {
    i = e;
    do (o = i.lane), (_e.lanes |= o), (oi |= o), (i = i.next);
    while (i !== e);
  } else i === null && (n.lanes = 0);
  return [t.memoizedState, n.dispatch];
}
function Hc(e) {
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
    tn(o, t.memoizedState) || (pt = !0),
      (t.memoizedState = o),
      t.baseQueue === null && (t.baseState = o),
      (n.lastRenderedState = o);
  }
  return [o, r];
}
function IP() {}
function DP(e, t) {
  var n = _e,
    r = qt(),
    i = t(),
    o = !tn(r.memoizedState, i);
  if (
    (o && ((r.memoizedState = i), (pt = !0)),
    (r = r.queue),
    Vy(FP.bind(null, n, r, e), [e]),
    r.getSnapshot !== t || o || (ze !== null && ze.memoizedState.tag & 1))
  ) {
    if (((n.flags |= 2048), qs(9, LP.bind(null, n, r, i, t), void 0, null), Ue === null))
      throw Error(z(349));
    ii & 30 || OP(n, t, i);
  }
  return i;
}
function OP(e, t, n) {
  (e.flags |= 16384),
    (e = { getSnapshot: t, value: n }),
    (t = _e.updateQueue),
    t === null
      ? ((t = { lastEffect: null, stores: null }), (_e.updateQueue = t), (t.stores = [e]))
      : ((n = t.stores), n === null ? (t.stores = [e]) : n.push(e));
}
function LP(e, t, n, r) {
  (t.value = n), (t.getSnapshot = r), VP(t) && jP(e);
}
function FP(e, t, n) {
  return n(function () {
    VP(t) && jP(e);
  });
}
function VP(e) {
  var t = e.getSnapshot;
  e = e.value;
  try {
    var n = t();
    return !tn(e, n);
  } catch {
    return !0;
  }
}
function jP(e) {
  var t = Bn(e, 1);
  t !== null && Jt(t, e, 1, -1);
}
function v1(e) {
  var t = fn();
  return (
    typeof e == "function" && (e = e()),
    (t.memoizedState = t.baseState = e),
    (e = {
      pending: null,
      interleaved: null,
      lanes: 0,
      dispatch: null,
      lastRenderedReducer: js,
      lastRenderedState: e,
    }),
    (t.queue = e),
    (e = e.dispatch = GL.bind(null, _e, e)),
    [t.memoizedState, e]
  );
}
function qs(e, t, n, r) {
  return (
    (e = { tag: e, create: t, destroy: n, deps: r, next: null }),
    (t = _e.updateQueue),
    t === null
      ? ((t = { lastEffect: null, stores: null }),
        (_e.updateQueue = t),
        (t.lastEffect = e.next = e))
      : ((n = t.lastEffect),
        n === null
          ? (t.lastEffect = e.next = e)
          : ((r = n.next), (n.next = e), (e.next = r), (t.lastEffect = e))),
    e
  );
}
function qP() {
  return qt().memoizedState;
}
function du(e, t, n, r) {
  var i = fn();
  (_e.flags |= e), (i.memoizedState = qs(1 | t, n, void 0, r === void 0 ? null : r));
}
function kl(e, t, n, r) {
  var i = qt();
  r = r === void 0 ? null : r;
  var o = void 0;
  if (Oe !== null) {
    var s = Oe.memoizedState;
    if (((o = s.destroy), r !== null && Oy(r, s.deps))) {
      i.memoizedState = qs(t, n, o, r);
      return;
    }
  }
  (_e.flags |= e), (i.memoizedState = qs(1 | t, n, o, r));
}
function y1(e, t) {
  return du(8390656, 8, e, t);
}
function Vy(e, t) {
  return kl(2048, 8, e, t);
}
function $P(e, t) {
  return kl(4, 2, e, t);
}
function zP(e, t) {
  return kl(4, 4, e, t);
}
function BP(e, t) {
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
function UP(e, t, n) {
  return (n = n != null ? n.concat([e]) : null), kl(4, 4, BP.bind(null, t, e), n);
}
function jy() {}
function HP(e, t) {
  var n = qt();
  t = t === void 0 ? null : t;
  var r = n.memoizedState;
  return r !== null && t !== null && Oy(t, r[1]) ? r[0] : ((n.memoizedState = [e, t]), e);
}
function GP(e, t) {
  var n = qt();
  t = t === void 0 ? null : t;
  var r = n.memoizedState;
  return r !== null && t !== null && Oy(t, r[1])
    ? r[0]
    : ((e = e()), (n.memoizedState = [e, t]), e);
}
function WP(e, t, n) {
  return ii & 21
    ? (tn(n, t) || ((n = Qk()), (_e.lanes |= n), (oi |= n), (e.baseState = !0)), t)
    : (e.baseState && ((e.baseState = !1), (pt = !0)), (e.memoizedState = n));
}
function UL(e, t) {
  var n = ce;
  (ce = n !== 0 && 4 > n ? n : 4), e(!0);
  var r = Bc.transition;
  Bc.transition = {};
  try {
    e(!1), t();
  } finally {
    (ce = n), (Bc.transition = r);
  }
}
function KP() {
  return qt().memoizedState;
}
function HL(e, t, n) {
  var r = br(e);
  if (((n = { lane: r, action: n, hasEagerState: !1, eagerState: null, next: null }), YP(e)))
    XP(t, n);
  else if (((n = AP(e, t, n, r)), n !== null)) {
    var i = at();
    Jt(n, e, r, i), ZP(n, t, r);
  }
}
function GL(e, t, n) {
  var r = br(e),
    i = { lane: r, action: n, hasEagerState: !1, eagerState: null, next: null };
  if (YP(e)) XP(t, i);
  else {
    var o = e.alternate;
    if (e.lanes === 0 && (o === null || o.lanes === 0) && ((o = t.lastRenderedReducer), o !== null))
      try {
        var s = t.lastRenderedState,
          a = o(s, n);
        if (((i.hasEagerState = !0), (i.eagerState = a), tn(a, s))) {
          var u = t.interleaved;
          u === null ? ((i.next = i), Ay(t)) : ((i.next = u.next), (u.next = i)),
            (t.interleaved = i);
          return;
        }
      } catch {
      } finally {
      }
    (n = AP(e, t, i, r)), n !== null && ((i = at()), Jt(n, e, r, i), ZP(n, t, r));
  }
}
function YP(e) {
  var t = e.alternate;
  return e === _e || (t !== null && t === _e);
}
function XP(e, t) {
  ms = Gu = !0;
  var n = e.pending;
  n === null ? (t.next = t) : ((t.next = n.next), (n.next = t)), (e.pending = t);
}
function ZP(e, t, n) {
  if (n & 4194240) {
    var r = t.lanes;
    (r &= e.pendingLanes), (n |= r), (t.lanes = n), gy(e, n);
  }
}
var Wu = {
    readContext: jt,
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
  WL = {
    readContext: jt,
    useCallback: function (e, t) {
      return (fn().memoizedState = [e, t === void 0 ? null : t]), e;
    },
    useContext: jt,
    useEffect: y1,
    useImperativeHandle: function (e, t, n) {
      return (n = n != null ? n.concat([e]) : null), du(4194308, 4, BP.bind(null, t, e), n);
    },
    useLayoutEffect: function (e, t) {
      return du(4194308, 4, e, t);
    },
    useInsertionEffect: function (e, t) {
      return du(4, 2, e, t);
    },
    useMemo: function (e, t) {
      var n = fn();
      return (t = t === void 0 ? null : t), (e = e()), (n.memoizedState = [e, t]), e;
    },
    useReducer: function (e, t, n) {
      var r = fn();
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
        (e = e.dispatch = HL.bind(null, _e, e)),
        [r.memoizedState, e]
      );
    },
    useRef: function (e) {
      var t = fn();
      return (e = { current: e }), (t.memoizedState = e);
    },
    useState: v1,
    useDebugValue: jy,
    useDeferredValue: function (e) {
      return (fn().memoizedState = e);
    },
    useTransition: function () {
      var e = v1(!1),
        t = e[0];
      return (e = UL.bind(null, e[1])), (fn().memoizedState = e), [t, e];
    },
    useMutableSource: function () {},
    useSyncExternalStore: function (e, t, n) {
      var r = _e,
        i = fn();
      if (ve) {
        if (n === void 0) throw Error(z(407));
        n = n();
      } else {
        if (((n = t()), Ue === null)) throw Error(z(349));
        ii & 30 || OP(r, t, n);
      }
      i.memoizedState = n;
      var o = { value: n, getSnapshot: t };
      return (
        (i.queue = o),
        y1(FP.bind(null, r, o, e), [e]),
        (r.flags |= 2048),
        qs(9, LP.bind(null, r, o, n, t), void 0, null),
        n
      );
    },
    useId: function () {
      var e = fn(),
        t = Ue.identifierPrefix;
      if (ve) {
        var n = In,
          r = Mn;
        (n = (r & ~(1 << (32 - Qt(r) - 1))).toString(32) + n),
          (t = ":" + t + "R" + n),
          (n = Vs++),
          0 < n && (t += "H" + n.toString(32)),
          (t += ":");
      } else (n = BL++), (t = ":" + t + "r" + n.toString(32) + ":");
      return (e.memoizedState = t);
    },
    unstable_isNewReconciler: !1,
  },
  KL = {
    readContext: jt,
    useCallback: HP,
    useContext: jt,
    useEffect: Vy,
    useImperativeHandle: UP,
    useInsertionEffect: $P,
    useLayoutEffect: zP,
    useMemo: GP,
    useReducer: Uc,
    useRef: qP,
    useState: function () {
      return Uc(js);
    },
    useDebugValue: jy,
    useDeferredValue: function (e) {
      var t = qt();
      return WP(t, Oe.memoizedState, e);
    },
    useTransition: function () {
      var e = Uc(js)[0],
        t = qt().memoizedState;
      return [e, t];
    },
    useMutableSource: IP,
    useSyncExternalStore: DP,
    useId: KP,
    unstable_isNewReconciler: !1,
  },
  YL = {
    readContext: jt,
    useCallback: HP,
    useContext: jt,
    useEffect: Vy,
    useImperativeHandle: UP,
    useInsertionEffect: $P,
    useLayoutEffect: zP,
    useMemo: GP,
    useReducer: Hc,
    useRef: qP,
    useState: function () {
      return Hc(js);
    },
    useDebugValue: jy,
    useDeferredValue: function (e) {
      var t = qt();
      return Oe === null ? (t.memoizedState = e) : WP(t, Oe.memoizedState, e);
    },
    useTransition: function () {
      var e = Hc(js)[0],
        t = qt().memoizedState;
      return [e, t];
    },
    useMutableSource: IP,
    useSyncExternalStore: DP,
    useId: KP,
    unstable_isNewReconciler: !1,
  };
function Wt(e, t) {
  if (e && e.defaultProps) {
    (t = Se({}, t)), (e = e.defaultProps);
    for (var n in e) t[n] === void 0 && (t[n] = e[n]);
    return t;
  }
  return t;
}
function nv(e, t, n, r) {
  (t = e.memoizedState),
    (n = n(r, t)),
    (n = n == null ? t : Se({}, t, n)),
    (e.memoizedState = n),
    e.lanes === 0 && (e.updateQueue.baseState = n);
}
var Pl = {
  isMounted: function (e) {
    return (e = e._reactInternals) ? fi(e) === e : !1;
  },
  enqueueSetState: function (e, t, n) {
    e = e._reactInternals;
    var r = at(),
      i = br(e),
      o = Fn(r, i);
    (o.payload = t),
      n != null && (o.callback = n),
      (t = _r(e, o, i)),
      t !== null && (Jt(t, e, i, r), cu(t, e, i));
  },
  enqueueReplaceState: function (e, t, n) {
    e = e._reactInternals;
    var r = at(),
      i = br(e),
      o = Fn(r, i);
    (o.tag = 1),
      (o.payload = t),
      n != null && (o.callback = n),
      (t = _r(e, o, i)),
      t !== null && (Jt(t, e, i, r), cu(t, e, i));
  },
  enqueueForceUpdate: function (e, t) {
    e = e._reactInternals;
    var n = at(),
      r = br(e),
      i = Fn(n, r);
    (i.tag = 2),
      t != null && (i.callback = t),
      (t = _r(e, i, r)),
      t !== null && (Jt(t, e, r, n), cu(t, e, r));
  },
};
function w1(e, t, n, r, i, o, s) {
  return (
    (e = e.stateNode),
    typeof e.shouldComponentUpdate == "function"
      ? e.shouldComponentUpdate(r, o, s)
      : t.prototype && t.prototype.isPureReactComponent
      ? !Ms(n, r) || !Ms(i, o)
      : !0
  );
}
function QP(e, t, n) {
  var r = !1,
    i = Pr,
    o = t.contextType;
  return (
    typeof o == "object" && o !== null
      ? (o = jt(o))
      : ((i = vt(t) ? ni : rt.current),
        (r = t.contextTypes),
        (o = (r = r != null) ? ro(e, i) : Pr)),
    (t = new t(n, o)),
    (e.memoizedState = t.state !== null && t.state !== void 0 ? t.state : null),
    (t.updater = Pl),
    (e.stateNode = t),
    (t._reactInternals = e),
    r &&
      ((e = e.stateNode),
      (e.__reactInternalMemoizedUnmaskedChildContext = i),
      (e.__reactInternalMemoizedMaskedChildContext = o)),
    t
  );
}
function x1(e, t, n, r) {
  (e = t.state),
    typeof t.componentWillReceiveProps == "function" && t.componentWillReceiveProps(n, r),
    typeof t.UNSAFE_componentWillReceiveProps == "function" &&
      t.UNSAFE_componentWillReceiveProps(n, r),
    t.state !== e && Pl.enqueueReplaceState(t, t.state, null);
}
function rv(e, t, n, r) {
  var i = e.stateNode;
  (i.props = n), (i.state = e.memoizedState), (i.refs = {}), Ny(e);
  var o = t.contextType;
  typeof o == "object" && o !== null
    ? (i.context = jt(o))
    : ((o = vt(t) ? ni : rt.current), (i.context = ro(e, o))),
    (i.state = e.memoizedState),
    (o = t.getDerivedStateFromProps),
    typeof o == "function" && (nv(e, t, o, n), (i.state = e.memoizedState)),
    typeof t.getDerivedStateFromProps == "function" ||
      typeof i.getSnapshotBeforeUpdate == "function" ||
      (typeof i.UNSAFE_componentWillMount != "function" &&
        typeof i.componentWillMount != "function") ||
      ((t = i.state),
      typeof i.componentWillMount == "function" && i.componentWillMount(),
      typeof i.UNSAFE_componentWillMount == "function" && i.UNSAFE_componentWillMount(),
      t !== i.state && Pl.enqueueReplaceState(i, i.state, null),
      Uu(e, n, i, r),
      (i.state = e.memoizedState)),
    typeof i.componentDidMount == "function" && (e.flags |= 4194308);
}
function ao(e, t) {
  try {
    var n = "",
      r = t;
    do (n += bO(r)), (r = r.return);
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
function Gc(e, t, n) {
  return { value: e, source: null, stack: n ?? null, digest: t ?? null };
}
function iv(e, t) {
  try {
    console.error(t.value);
  } catch (n) {
    setTimeout(function () {
      throw n;
    });
  }
}
var XL = typeof WeakMap == "function" ? WeakMap : Map;
function JP(e, t, n) {
  (n = Fn(-1, n)), (n.tag = 3), (n.payload = { element: null });
  var r = t.value;
  return (
    (n.callback = function () {
      Yu || ((Yu = !0), (pv = r)), iv(e, t);
    }),
    n
  );
}
function eR(e, t, n) {
  (n = Fn(-1, n)), (n.tag = 3);
  var r = e.type.getDerivedStateFromError;
  if (typeof r == "function") {
    var i = t.value;
    (n.payload = function () {
      return r(i);
    }),
      (n.callback = function () {
        iv(e, t);
      });
  }
  var o = e.stateNode;
  return (
    o !== null &&
      typeof o.componentDidCatch == "function" &&
      (n.callback = function () {
        iv(e, t), typeof r != "function" && (Sr === null ? (Sr = new Set([this])) : Sr.add(this));
        var s = t.stack;
        this.componentDidCatch(t.value, { componentStack: s !== null ? s : "" });
      }),
    n
  );
}
function _1(e, t, n) {
  var r = e.pingCache;
  if (r === null) {
    r = e.pingCache = new XL();
    var i = new Set();
    r.set(t, i);
  } else (i = r.get(t)), i === void 0 && ((i = new Set()), r.set(t, i));
  i.has(n) || (i.add(n), (e = cF.bind(null, e, t, n)), t.then(e, e));
}
function S1(e) {
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
            (n.alternate === null ? (n.tag = 17) : ((t = Fn(-1, 1)), (t.tag = 2), _r(n, t, 1))),
          (n.lanes |= 1)),
      e);
}
var ZL = Xn.ReactCurrentOwner,
  pt = !1;
function st(e, t, n, r) {
  t.child = e === null ? RP(t, null, n, r) : oo(t, e.child, n, r);
}
function E1(e, t, n, r, i) {
  n = n.render;
  var o = t.ref;
  return (
    Yi(t, i),
    (r = Ly(e, t, n, r, o, i)),
    (n = Fy()),
    e !== null && !pt
      ? ((t.updateQueue = e.updateQueue), (t.flags &= -2053), (e.lanes &= ~i), Un(e, t, i))
      : (ve && n && Ey(t), (t.flags |= 1), st(e, t, r, i), t.child)
  );
}
function C1(e, t, n, r, i) {
  if (e === null) {
    var o = n.type;
    return typeof o == "function" &&
      !Wy(o) &&
      o.defaultProps === void 0 &&
      n.compare === null &&
      n.defaultProps === void 0
      ? ((t.tag = 15), (t.type = o), tR(e, t, o, r, i))
      : ((e = gu(n.type, null, r, t, t.mode, i)), (e.ref = t.ref), (e.return = t), (t.child = e));
  }
  if (((o = e.child), !(e.lanes & i))) {
    var s = o.memoizedProps;
    if (((n = n.compare), (n = n !== null ? n : Ms), n(s, r) && e.ref === t.ref))
      return Un(e, t, i);
  }
  return (t.flags |= 1), (e = Er(o, r)), (e.ref = t.ref), (e.return = t), (t.child = e);
}
function tR(e, t, n, r, i) {
  if (e !== null) {
    var o = e.memoizedProps;
    if (Ms(o, r) && e.ref === t.ref)
      if (((pt = !1), (t.pendingProps = r = o), (e.lanes & i) !== 0)) e.flags & 131072 && (pt = !0);
      else return (t.lanes = e.lanes), Un(e, t, i);
  }
  return ov(e, t, n, r, i);
}
function nR(e, t, n) {
  var r = t.pendingProps,
    i = r.children,
    o = e !== null ? e.memoizedState : null;
  if (r.mode === "hidden")
    if (!(t.mode & 1))
      (t.memoizedState = { baseLanes: 0, cachePool: null, transitions: null }),
        de(Vi, _t),
        (_t |= n);
    else {
      if (!(n & 1073741824))
        return (
          (e = o !== null ? o.baseLanes | n : n),
          (t.lanes = t.childLanes = 1073741824),
          (t.memoizedState = { baseLanes: e, cachePool: null, transitions: null }),
          (t.updateQueue = null),
          de(Vi, _t),
          (_t |= e),
          null
        );
      (t.memoizedState = { baseLanes: 0, cachePool: null, transitions: null }),
        (r = o !== null ? o.baseLanes : n),
        de(Vi, _t),
        (_t |= r);
    }
  else
    o !== null ? ((r = o.baseLanes | n), (t.memoizedState = null)) : (r = n), de(Vi, _t), (_t |= r);
  return st(e, t, i, n), t.child;
}
function rR(e, t) {
  var n = t.ref;
  ((e === null && n !== null) || (e !== null && e.ref !== n)) &&
    ((t.flags |= 512), (t.flags |= 2097152));
}
function ov(e, t, n, r, i) {
  var o = vt(n) ? ni : rt.current;
  return (
    (o = ro(t, o)),
    Yi(t, i),
    (n = Ly(e, t, n, r, o, i)),
    (r = Fy()),
    e !== null && !pt
      ? ((t.updateQueue = e.updateQueue), (t.flags &= -2053), (e.lanes &= ~i), Un(e, t, i))
      : (ve && r && Ey(t), (t.flags |= 1), st(e, t, n, i), t.child)
  );
}
function T1(e, t, n, r, i) {
  if (vt(n)) {
    var o = !0;
    ju(t);
  } else o = !1;
  if ((Yi(t, i), t.stateNode === null)) hu(e, t), QP(t, n, r), rv(t, n, r, i), (r = !0);
  else if (e === null) {
    var s = t.stateNode,
      a = t.memoizedProps;
    s.props = a;
    var u = s.context,
      l = n.contextType;
    typeof l == "object" && l !== null
      ? (l = jt(l))
      : ((l = vt(n) ? ni : rt.current), (l = ro(t, l)));
    var c = n.getDerivedStateFromProps,
      f = typeof c == "function" || typeof s.getSnapshotBeforeUpdate == "function";
    f ||
      (typeof s.UNSAFE_componentWillReceiveProps != "function" &&
        typeof s.componentWillReceiveProps != "function") ||
      ((a !== r || u !== l) && x1(t, s, r, l)),
      (ur = !1);
    var d = t.memoizedState;
    (s.state = d),
      Uu(t, r, s, i),
      (u = t.memoizedState),
      a !== r || d !== u || gt.current || ur
        ? (typeof c == "function" && (nv(t, n, c, r), (u = t.memoizedState)),
          (a = ur || w1(t, n, a, r, d, u, l))
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
      NP(e, t),
      (a = t.memoizedProps),
      (l = t.type === t.elementType ? a : Wt(t.type, a)),
      (s.props = l),
      (f = t.pendingProps),
      (d = s.context),
      (u = n.contextType),
      typeof u == "object" && u !== null
        ? (u = jt(u))
        : ((u = vt(n) ? ni : rt.current), (u = ro(t, u)));
    var h = n.getDerivedStateFromProps;
    (c = typeof h == "function" || typeof s.getSnapshotBeforeUpdate == "function") ||
      (typeof s.UNSAFE_componentWillReceiveProps != "function" &&
        typeof s.componentWillReceiveProps != "function") ||
      ((a !== f || d !== u) && x1(t, s, r, u)),
      (ur = !1),
      (d = t.memoizedState),
      (s.state = d),
      Uu(t, r, s, i);
    var v = t.memoizedState;
    a !== f || d !== v || gt.current || ur
      ? (typeof h == "function" && (nv(t, n, h, r), (v = t.memoizedState)),
        (l = ur || w1(t, n, l, r, d, v, u) || !1)
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
  return sv(e, t, n, r, o, i);
}
function sv(e, t, n, r, i, o) {
  rR(e, t);
  var s = (t.flags & 128) !== 0;
  if (!r && !s) return i && f1(t, n, !1), Un(e, t, o);
  (r = t.stateNode), (ZL.current = t);
  var a = s && typeof n.getDerivedStateFromError != "function" ? null : r.render();
  return (
    (t.flags |= 1),
    e !== null && s
      ? ((t.child = oo(t, e.child, null, o)), (t.child = oo(t, null, a, o)))
      : st(e, t, a, o),
    (t.memoizedState = r.state),
    i && f1(t, n, !0),
    t.child
  );
}
function iR(e) {
  var t = e.stateNode;
  t.pendingContext
    ? c1(e, t.pendingContext, t.pendingContext !== t.context)
    : t.context && c1(e, t.context, !1),
    My(e, t.containerInfo);
}
function k1(e, t, n, r, i) {
  return io(), Ty(i), (t.flags |= 256), st(e, t, n, r), t.child;
}
var av = { dehydrated: null, treeContext: null, retryLane: 0 };
function uv(e) {
  return { baseLanes: e, cachePool: null, transitions: null };
}
function oR(e, t, n) {
  var r = t.pendingProps,
    i = we.current,
    o = !1,
    s = (t.flags & 128) !== 0,
    a;
  if (
    ((a = s) || (a = e !== null && e.memoizedState === null ? !1 : (i & 2) !== 0),
    a ? ((o = !0), (t.flags &= -129)) : (e === null || e.memoizedState !== null) && (i |= 1),
    de(we, i & 1),
    e === null)
  )
    return (
      ev(t),
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
                : (o = Nl(s, r, 0, null)),
              (e = Qr(e, r, n, null)),
              (o.return = t),
              (e.return = t),
              (o.sibling = e),
              (t.child = o),
              (t.child.memoizedState = uv(n)),
              (t.memoizedState = av),
              e)
            : qy(t, s))
    );
  if (((i = e.memoizedState), i !== null && ((a = i.dehydrated), a !== null)))
    return QL(e, t, s, r, a, i, n);
  if (o) {
    (o = r.fallback), (s = t.mode), (i = e.child), (a = i.sibling);
    var u = { mode: "hidden", children: r.children };
    return (
      !(s & 1) && t.child !== i
        ? ((r = t.child), (r.childLanes = 0), (r.pendingProps = u), (t.deletions = null))
        : ((r = Er(i, u)), (r.subtreeFlags = i.subtreeFlags & 14680064)),
      a !== null ? (o = Er(a, o)) : ((o = Qr(o, s, n, null)), (o.flags |= 2)),
      (o.return = t),
      (r.return = t),
      (r.sibling = o),
      (t.child = r),
      (r = o),
      (o = t.child),
      (s = e.child.memoizedState),
      (s =
        s === null
          ? uv(n)
          : { baseLanes: s.baseLanes | n, cachePool: null, transitions: s.transitions }),
      (o.memoizedState = s),
      (o.childLanes = e.childLanes & ~n),
      (t.memoizedState = av),
      r
    );
  }
  return (
    (o = e.child),
    (e = o.sibling),
    (r = Er(o, { mode: "visible", children: r.children })),
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
function qy(e, t) {
  return (t = Nl({ mode: "visible", children: t }, e.mode, 0, null)), (t.return = e), (e.child = t);
}
function La(e, t, n, r) {
  return (
    r !== null && Ty(r),
    oo(t, e.child, null, n),
    (e = qy(t, t.pendingProps.children)),
    (e.flags |= 2),
    (t.memoizedState = null),
    e
  );
}
function QL(e, t, n, r, i, o, s) {
  if (n)
    return t.flags & 256
      ? ((t.flags &= -257), (r = Gc(Error(z(422)))), La(e, t, s, r))
      : t.memoizedState !== null
      ? ((t.child = e.child), (t.flags |= 128), null)
      : ((o = r.fallback),
        (i = t.mode),
        (r = Nl({ mode: "visible", children: r.children }, i, 0, null)),
        (o = Qr(o, i, s, null)),
        (o.flags |= 2),
        (r.return = t),
        (o.return = t),
        (r.sibling = o),
        (t.child = r),
        t.mode & 1 && oo(t, e.child, null, s),
        (t.child.memoizedState = uv(s)),
        (t.memoizedState = av),
        o);
  if (!(t.mode & 1)) return La(e, t, s, null);
  if (i.data === "$!") {
    if (((r = i.nextSibling && i.nextSibling.dataset), r)) var a = r.dgst;
    return (r = a), (o = Error(z(419))), (r = Gc(o, r, void 0)), La(e, t, s, r);
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
        i !== 0 && i !== o.retryLane && ((o.retryLane = i), Bn(e, i), Jt(r, e, i, -1));
    }
    return Gy(), (r = Gc(Error(z(421)))), La(e, t, s, r);
  }
  return i.data === "$?"
    ? ((t.flags |= 128), (t.child = e.child), (t = fF.bind(null, e)), (i._reactRetry = t), null)
    : ((e = o.treeContext),
      (bt = xr(i.nextSibling)),
      (Et = t),
      (ve = !0),
      (Xt = null),
      e !== null &&
        ((It[Dt++] = Mn),
        (It[Dt++] = In),
        (It[Dt++] = ri),
        (Mn = e.id),
        (In = e.overflow),
        (ri = t)),
      (t = qy(t, r.children)),
      (t.flags |= 4096),
      t);
}
function P1(e, t, n) {
  e.lanes |= t;
  var r = e.alternate;
  r !== null && (r.lanes |= t), tv(e.return, t, n);
}
function Wc(e, t, n, r, i) {
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
function sR(e, t, n) {
  var r = t.pendingProps,
    i = r.revealOrder,
    o = r.tail;
  if ((st(e, t, r.children, n), (r = we.current), r & 2)) (r = (r & 1) | 2), (t.flags |= 128);
  else {
    if (e !== null && e.flags & 128)
      e: for (e = t.child; e !== null; ) {
        if (e.tag === 13) e.memoizedState !== null && P1(e, n, t);
        else if (e.tag === 19) P1(e, n, t);
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
  if ((de(we, r), !(t.mode & 1))) t.memoizedState = null;
  else
    switch (i) {
      case "forwards":
        for (n = t.child, i = null; n !== null; )
          (e = n.alternate), e !== null && Hu(e) === null && (i = n), (n = n.sibling);
        (n = i),
          n === null ? ((i = t.child), (t.child = null)) : ((i = n.sibling), (n.sibling = null)),
          Wc(t, !1, i, n, o);
        break;
      case "backwards":
        for (n = null, i = t.child, t.child = null; i !== null; ) {
          if (((e = i.alternate), e !== null && Hu(e) === null)) {
            t.child = i;
            break;
          }
          (e = i.sibling), (i.sibling = n), (n = i), (i = e);
        }
        Wc(t, !0, n, null, o);
        break;
      case "together":
        Wc(t, !1, null, null, void 0);
        break;
      default:
        t.memoizedState = null;
    }
  return t.child;
}
function hu(e, t) {
  !(t.mode & 1) && e !== null && ((e.alternate = null), (t.alternate = null), (t.flags |= 2));
}
function Un(e, t, n) {
  if ((e !== null && (t.dependencies = e.dependencies), (oi |= t.lanes), !(n & t.childLanes)))
    return null;
  if (e !== null && t.child !== e.child) throw Error(z(153));
  if (t.child !== null) {
    for (e = t.child, n = Er(e, e.pendingProps), t.child = n, n.return = t; e.sibling !== null; )
      (e = e.sibling), (n = n.sibling = Er(e, e.pendingProps)), (n.return = t);
    n.sibling = null;
  }
  return t.child;
}
function JL(e, t, n) {
  switch (t.tag) {
    case 3:
      iR(t), io();
      break;
    case 5:
      MP(t);
      break;
    case 1:
      vt(t.type) && ju(t);
      break;
    case 4:
      My(t, t.stateNode.containerInfo);
      break;
    case 10:
      var r = t.type._context,
        i = t.memoizedProps.value;
      de(zu, r._currentValue), (r._currentValue = i);
      break;
    case 13:
      if (((r = t.memoizedState), r !== null))
        return r.dehydrated !== null
          ? (de(we, we.current & 1), (t.flags |= 128), null)
          : n & t.child.childLanes
          ? oR(e, t, n)
          : (de(we, we.current & 1), (e = Un(e, t, n)), e !== null ? e.sibling : null);
      de(we, we.current & 1);
      break;
    case 19:
      if (((r = (n & t.childLanes) !== 0), e.flags & 128)) {
        if (r) return sR(e, t, n);
        t.flags |= 128;
      }
      if (
        ((i = t.memoizedState),
        i !== null && ((i.rendering = null), (i.tail = null), (i.lastEffect = null)),
        de(we, we.current),
        r)
      )
        break;
      return null;
    case 22:
    case 23:
      return (t.lanes = 0), nR(e, t, n);
  }
  return Un(e, t, n);
}
var aR, lv, uR, lR;
aR = function (e, t) {
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
lv = function () {};
uR = function (e, t, n, r) {
  var i = e.memoizedProps;
  if (i !== r) {
    (e = t.stateNode), Gr(gn.current);
    var o = null;
    switch (n) {
      case "input":
        (i = Ng(e, i)), (r = Ng(e, r)), (o = []);
        break;
      case "select":
        (i = Se({}, i, { value: void 0 })), (r = Se({}, r, { value: void 0 })), (o = []);
        break;
      case "textarea":
        (i = Dg(e, i)), (r = Dg(e, r)), (o = []);
        break;
      default:
        typeof i.onClick != "function" && typeof r.onClick == "function" && (e.onclick = Fu);
    }
    Lg(n, r);
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
            (Cs.hasOwnProperty(l) ? o || (o = []) : (o = o || []).push(l, null));
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
              (Cs.hasOwnProperty(l)
                ? (u != null && l === "onScroll" && me("scroll", e), o || a === u || (o = []))
                : (o = o || []).push(l, u));
    }
    n && (o = o || []).push("style", n);
    var l = o;
    (t.updateQueue = l) && (t.flags |= 4);
  }
};
lR = function (e, t, n, r) {
  n !== r && (t.flags |= 4);
};
function Vo(e, t) {
  if (!ve)
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
function eF(e, t, n) {
  var r = t.pendingProps;
  switch ((Cy(t), t.tag)) {
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
      return vt(t.type) && Vu(), et(t), null;
    case 3:
      return (
        (r = t.stateNode),
        so(),
        ge(gt),
        ge(rt),
        Dy(),
        r.pendingContext && ((r.context = r.pendingContext), (r.pendingContext = null)),
        (e === null || e.child === null) &&
          (Da(t)
            ? (t.flags |= 4)
            : e === null ||
              (e.memoizedState.isDehydrated && !(t.flags & 256)) ||
              ((t.flags |= 1024), Xt !== null && (vv(Xt), (Xt = null)))),
        lv(e, t),
        et(t),
        null
      );
    case 5:
      Iy(t);
      var i = Gr(Fs.current);
      if (((n = t.type), e !== null && t.stateNode != null))
        uR(e, t, n, r, i), e.ref !== t.ref && ((t.flags |= 512), (t.flags |= 2097152));
      else {
        if (!r) {
          if (t.stateNode === null) throw Error(z(166));
          return et(t), null;
        }
        if (((e = Gr(gn.current)), Da(t))) {
          (r = t.stateNode), (n = t.type);
          var o = t.memoizedProps;
          switch (((r[dn] = t), (r[Os] = o), (e = (t.mode & 1) !== 0), n)) {
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
              for (i = 0; i < Zo.length; i++) me(Zo[i], r);
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
              Fw(r, o), me("invalid", r);
              break;
            case "select":
              (r._wrapperState = { wasMultiple: !!o.multiple }), me("invalid", r);
              break;
            case "textarea":
              jw(r, o), me("invalid", r);
          }
          Lg(n, o), (i = null);
          for (var s in o)
            if (o.hasOwnProperty(s)) {
              var a = o[s];
              s === "children"
                ? typeof a == "string"
                  ? r.textContent !== a &&
                    (o.suppressHydrationWarning !== !0 && Ia(r.textContent, a, e),
                    (i = ["children", a]))
                  : typeof a == "number" &&
                    r.textContent !== "" + a &&
                    (o.suppressHydrationWarning !== !0 && Ia(r.textContent, a, e),
                    (i = ["children", "" + a]))
                : Cs.hasOwnProperty(s) && a != null && s === "onScroll" && me("scroll", r);
            }
          switch (n) {
            case "input":
              Ca(r), Vw(r, o, !0);
              break;
            case "textarea":
              Ca(r), qw(r);
              break;
            case "select":
            case "option":
              break;
            default:
              typeof o.onClick == "function" && (r.onclick = Fu);
          }
          (r = i), (t.updateQueue = r), r !== null && (t.flags |= 4);
        } else {
          (s = i.nodeType === 9 ? i : i.ownerDocument),
            e === "http://www.w3.org/1999/xhtml" && (e = Fk(n)),
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
            (e[dn] = t),
            (e[Os] = r),
            aR(e, t, !1, !1),
            (t.stateNode = e);
          e: {
            switch (((s = Fg(n, r)), n)) {
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
                for (i = 0; i < Zo.length; i++) me(Zo[i], e);
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
                Fw(e, r), (i = Ng(e, r)), me("invalid", e);
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
                jw(e, r), (i = Dg(e, r)), me("invalid", e);
                break;
              default:
                i = r;
            }
            Lg(n, i), (a = i);
            for (o in a)
              if (a.hasOwnProperty(o)) {
                var u = a[o];
                o === "style"
                  ? qk(e, u)
                  : o === "dangerouslySetInnerHTML"
                  ? ((u = u ? u.__html : void 0), u != null && Vk(e, u))
                  : o === "children"
                  ? typeof u == "string"
                    ? (n !== "textarea" || u !== "") && Ts(e, u)
                    : typeof u == "number" && Ts(e, "" + u)
                  : o !== "suppressContentEditableWarning" &&
                    o !== "suppressHydrationWarning" &&
                    o !== "autoFocus" &&
                    (Cs.hasOwnProperty(o)
                      ? u != null && o === "onScroll" && me("scroll", e)
                      : u != null && cy(e, o, u, s));
              }
            switch (n) {
              case "input":
                Ca(e), Vw(e, r, !1);
                break;
              case "textarea":
                Ca(e), qw(e);
                break;
              case "option":
                r.value != null && e.setAttribute("value", "" + kr(r.value));
                break;
              case "select":
                (e.multiple = !!r.multiple),
                  (o = r.value),
                  o != null
                    ? Hi(e, !!r.multiple, o, !1)
                    : r.defaultValue != null && Hi(e, !!r.multiple, r.defaultValue, !0);
                break;
              default:
                typeof i.onClick == "function" && (e.onclick = Fu);
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
      if (e && t.stateNode != null) lR(e, t, e.memoizedProps, r);
      else {
        if (typeof r != "string" && t.stateNode === null) throw Error(z(166));
        if (((n = Gr(Fs.current)), Gr(gn.current), Da(t))) {
          if (
            ((r = t.stateNode),
            (n = t.memoizedProps),
            (r[dn] = t),
            (o = r.nodeValue !== n) && ((e = Et), e !== null))
          )
            switch (e.tag) {
              case 3:
                Ia(r.nodeValue, n, (e.mode & 1) !== 0);
                break;
              case 5:
                e.memoizedProps.suppressHydrationWarning !== !0 &&
                  Ia(r.nodeValue, n, (e.mode & 1) !== 0);
            }
          o && (t.flags |= 4);
        } else
          (r = (n.nodeType === 9 ? n : n.ownerDocument).createTextNode(r)),
            (r[dn] = t),
            (t.stateNode = r);
      }
      return et(t), null;
    case 13:
      if (
        (ge(we),
        (r = t.memoizedState),
        e === null || (e.memoizedState !== null && e.memoizedState.dehydrated !== null))
      ) {
        if (ve && bt !== null && t.mode & 1 && !(t.flags & 128))
          kP(), io(), (t.flags |= 98560), (o = !1);
        else if (((o = Da(t)), r !== null && r.dehydrated !== null)) {
          if (e === null) {
            if (!o) throw Error(z(318));
            if (((o = t.memoizedState), (o = o !== null ? o.dehydrated : null), !o))
              throw Error(z(317));
            o[dn] = t;
          } else io(), !(t.flags & 128) && (t.memoizedState = null), (t.flags |= 4);
          et(t), (o = !1);
        } else Xt !== null && (vv(Xt), (Xt = null)), (o = !0);
        if (!o) return t.flags & 65536 ? t : null;
      }
      return t.flags & 128
        ? ((t.lanes = n), t)
        : ((r = r !== null),
          r !== (e !== null && e.memoizedState !== null) &&
            r &&
            ((t.child.flags |= 8192),
            t.mode & 1 && (e === null || we.current & 1 ? Le === 0 && (Le = 3) : Gy())),
          t.updateQueue !== null && (t.flags |= 4),
          et(t),
          null);
    case 4:
      return so(), lv(e, t), e === null && Is(t.stateNode.containerInfo), et(t), null;
    case 10:
      return Ry(t.type._context), et(t), null;
    case 17:
      return vt(t.type) && Vu(), et(t), null;
    case 19:
      if ((ge(we), (o = t.memoizedState), o === null)) return et(t), null;
      if (((r = (t.flags & 128) !== 0), (s = o.rendering), s === null))
        if (r) Vo(o, !1);
        else {
          if (Le !== 0 || (e !== null && e.flags & 128))
            for (e = t.child; e !== null; ) {
              if (((s = Hu(e)), s !== null)) {
                for (
                  t.flags |= 128,
                    Vo(o, !1),
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
                return de(we, (we.current & 1) | 2), t.child;
              }
              e = e.sibling;
            }
          o.tail !== null &&
            Ne() > uo &&
            ((t.flags |= 128), (r = !0), Vo(o, !1), (t.lanes = 4194304));
        }
      else {
        if (!r)
          if (((e = Hu(s)), e !== null)) {
            if (
              ((t.flags |= 128),
              (r = !0),
              (n = e.updateQueue),
              n !== null && ((t.updateQueue = n), (t.flags |= 4)),
              Vo(o, !0),
              o.tail === null && o.tailMode === "hidden" && !s.alternate && !ve)
            )
              return et(t), null;
          } else
            2 * Ne() - o.renderingStartTime > uo &&
              n !== 1073741824 &&
              ((t.flags |= 128), (r = !0), Vo(o, !1), (t.lanes = 4194304));
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
          (n = we.current),
          de(we, r ? (n & 1) | 2 : n & 1),
          t)
        : (et(t), null);
    case 22:
    case 23:
      return (
        Hy(),
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
function tF(e, t) {
  switch ((Cy(t), t.tag)) {
    case 1:
      return (
        vt(t.type) && Vu(), (e = t.flags), e & 65536 ? ((t.flags = (e & -65537) | 128), t) : null
      );
    case 3:
      return (
        so(),
        ge(gt),
        ge(rt),
        Dy(),
        (e = t.flags),
        e & 65536 && !(e & 128) ? ((t.flags = (e & -65537) | 128), t) : null
      );
    case 5:
      return Iy(t), null;
    case 13:
      if ((ge(we), (e = t.memoizedState), e !== null && e.dehydrated !== null)) {
        if (t.alternate === null) throw Error(z(340));
        io();
      }
      return (e = t.flags), e & 65536 ? ((t.flags = (e & -65537) | 128), t) : null;
    case 19:
      return ge(we), null;
    case 4:
      return so(), null;
    case 10:
      return Ry(t.type._context), null;
    case 22:
    case 23:
      return Hy(), null;
    case 24:
      return null;
    default:
      return null;
  }
}
var Fa = !1,
  nt = !1,
  nF = typeof WeakSet == "function" ? WeakSet : Set,
  H = null;
function Fi(e, t) {
  var n = e.ref;
  if (n !== null)
    if (typeof n == "function")
      try {
        n(null);
      } catch (r) {
        Ce(e, t, r);
      }
    else n.current = null;
}
function cv(e, t, n) {
  try {
    n();
  } catch (r) {
    Ce(e, t, r);
  }
}
var R1 = !1;
function rF(e, t) {
  if (((Wg = Du), (e = pP()), by(e))) {
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
  for (Kg = { focusedElem: e, selectionRange: n }, Du = !1, H = t; H !== null; )
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
                    g = m.getSnapshotBeforeUpdate(t.elementType === t.type ? p : Wt(t.type, p), y);
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
          Ce(t, t.return, x);
        }
        if (((e = t.sibling), e !== null)) {
          (e.return = t.return), (H = e);
          break;
        }
        H = t.return;
      }
  return (v = R1), (R1 = !1), v;
}
function gs(e, t, n) {
  var r = t.updateQueue;
  if (((r = r !== null ? r.lastEffect : null), r !== null)) {
    var i = (r = r.next);
    do {
      if ((i.tag & e) === e) {
        var o = i.destroy;
        (i.destroy = void 0), o !== void 0 && cv(t, n, o);
      }
      i = i.next;
    } while (i !== r);
  }
}
function Rl(e, t) {
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
function fv(e) {
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
function cR(e) {
  var t = e.alternate;
  t !== null && ((e.alternate = null), cR(t)),
    (e.child = null),
    (e.deletions = null),
    (e.sibling = null),
    e.tag === 5 &&
      ((t = e.stateNode),
      t !== null && (delete t[dn], delete t[Os], delete t[Zg], delete t[jL], delete t[qL])),
    (e.stateNode = null),
    (e.return = null),
    (e.dependencies = null),
    (e.memoizedProps = null),
    (e.memoizedState = null),
    (e.pendingProps = null),
    (e.stateNode = null),
    (e.updateQueue = null);
}
function fR(e) {
  return e.tag === 5 || e.tag === 3 || e.tag === 4;
}
function A1(e) {
  e: for (;;) {
    for (; e.sibling === null; ) {
      if (e.return === null || fR(e.return)) return null;
      e = e.return;
    }
    for (e.sibling.return = e.return, e = e.sibling; e.tag !== 5 && e.tag !== 6 && e.tag !== 18; ) {
      if (e.flags & 2 || e.child === null || e.tag === 4) continue e;
      (e.child.return = e), (e = e.child);
    }
    if (!(e.flags & 2)) return e.stateNode;
  }
}
function dv(e, t, n) {
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
          n != null || t.onclick !== null || (t.onclick = Fu));
  else if (r !== 4 && ((e = e.child), e !== null))
    for (dv(e, t, n), e = e.sibling; e !== null; ) dv(e, t, n), (e = e.sibling);
}
function hv(e, t, n) {
  var r = e.tag;
  if (r === 5 || r === 6) (e = e.stateNode), t ? n.insertBefore(e, t) : n.appendChild(e);
  else if (r !== 4 && ((e = e.child), e !== null))
    for (hv(e, t, n), e = e.sibling; e !== null; ) hv(e, t, n), (e = e.sibling);
}
var We = null,
  Kt = !1;
function er(e, t, n) {
  for (n = n.child; n !== null; ) dR(e, t, n), (n = n.sibling);
}
function dR(e, t, n) {
  if (mn && typeof mn.onCommitFiberUnmount == "function")
    try {
      mn.onCommitFiberUnmount(_l, n);
    } catch {}
  switch (n.tag) {
    case 5:
      nt || Fi(n, t);
    case 6:
      var r = We,
        i = Kt;
      (We = null),
        er(e, t, n),
        (We = r),
        (Kt = i),
        We !== null &&
          (Kt
            ? ((e = We),
              (n = n.stateNode),
              e.nodeType === 8 ? e.parentNode.removeChild(n) : e.removeChild(n))
            : We.removeChild(n.stateNode));
      break;
    case 18:
      We !== null &&
        (Kt
          ? ((e = We),
            (n = n.stateNode),
            e.nodeType === 8 ? qc(e.parentNode, n) : e.nodeType === 1 && qc(e, n),
            As(e))
          : qc(We, n.stateNode));
      break;
    case 4:
      (r = We),
        (i = Kt),
        (We = n.stateNode.containerInfo),
        (Kt = !0),
        er(e, t, n),
        (We = r),
        (Kt = i);
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
          (o = o.tag), s !== void 0 && (o & 2 || o & 4) && cv(n, t, s), (i = i.next);
        } while (i !== r);
      }
      er(e, t, n);
      break;
    case 1:
      if (!nt && (Fi(n, t), (r = n.stateNode), typeof r.componentWillUnmount == "function"))
        try {
          (r.props = n.memoizedProps), (r.state = n.memoizedState), r.componentWillUnmount();
        } catch (a) {
          Ce(n, t, a);
        }
      er(e, t, n);
      break;
    case 21:
      er(e, t, n);
      break;
    case 22:
      n.mode & 1
        ? ((nt = (r = nt) || n.memoizedState !== null), er(e, t, n), (nt = r))
        : er(e, t, n);
      break;
    default:
      er(e, t, n);
  }
}
function N1(e) {
  var t = e.updateQueue;
  if (t !== null) {
    e.updateQueue = null;
    var n = e.stateNode;
    n === null && (n = e.stateNode = new nF()),
      t.forEach(function (r) {
        var i = dF.bind(null, e, r);
        n.has(r) || (n.add(r), r.then(i, i));
      });
  }
}
function Ht(e, t) {
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
              (We = a.stateNode), (Kt = !1);
              break e;
            case 3:
              (We = a.stateNode.containerInfo), (Kt = !0);
              break e;
            case 4:
              (We = a.stateNode.containerInfo), (Kt = !0);
              break e;
          }
          a = a.return;
        }
        if (We === null) throw Error(z(160));
        dR(o, s, i), (We = null), (Kt = !1);
        var u = i.alternate;
        u !== null && (u.return = null), (i.return = null);
      } catch (l) {
        Ce(i, t, l);
      }
    }
  if (t.subtreeFlags & 12854) for (t = t.child; t !== null; ) hR(t, e), (t = t.sibling);
}
function hR(e, t) {
  var n = e.alternate,
    r = e.flags;
  switch (e.tag) {
    case 0:
    case 11:
    case 14:
    case 15:
      if ((Ht(t, e), cn(e), r & 4)) {
        try {
          gs(3, e, e.return), Rl(3, e);
        } catch (p) {
          Ce(e, e.return, p);
        }
        try {
          gs(5, e, e.return);
        } catch (p) {
          Ce(e, e.return, p);
        }
      }
      break;
    case 1:
      Ht(t, e), cn(e), r & 512 && n !== null && Fi(n, n.return);
      break;
    case 5:
      if ((Ht(t, e), cn(e), r & 512 && n !== null && Fi(n, n.return), e.flags & 32)) {
        var i = e.stateNode;
        try {
          Ts(i, "");
        } catch (p) {
          Ce(e, e.return, p);
        }
      }
      if (r & 4 && ((i = e.stateNode), i != null)) {
        var o = e.memoizedProps,
          s = n !== null ? n.memoizedProps : o,
          a = e.type,
          u = e.updateQueue;
        if (((e.updateQueue = null), u !== null))
          try {
            a === "input" && o.type === "radio" && o.name != null && Ok(i, o), Fg(a, s);
            var l = Fg(a, o);
            for (s = 0; s < u.length; s += 2) {
              var c = u[s],
                f = u[s + 1];
              c === "style"
                ? qk(i, f)
                : c === "dangerouslySetInnerHTML"
                ? Vk(i, f)
                : c === "children"
                ? Ts(i, f)
                : cy(i, c, f, l);
            }
            switch (a) {
              case "input":
                Mg(i, o);
                break;
              case "textarea":
                Lk(i, o);
                break;
              case "select":
                var d = i._wrapperState.wasMultiple;
                i._wrapperState.wasMultiple = !!o.multiple;
                var h = o.value;
                h != null
                  ? Hi(i, !!o.multiple, h, !1)
                  : d !== !!o.multiple &&
                    (o.defaultValue != null
                      ? Hi(i, !!o.multiple, o.defaultValue, !0)
                      : Hi(i, !!o.multiple, o.multiple ? [] : "", !1));
            }
            i[Os] = o;
          } catch (p) {
            Ce(e, e.return, p);
          }
      }
      break;
    case 6:
      if ((Ht(t, e), cn(e), r & 4)) {
        if (e.stateNode === null) throw Error(z(162));
        (i = e.stateNode), (o = e.memoizedProps);
        try {
          i.nodeValue = o;
        } catch (p) {
          Ce(e, e.return, p);
        }
      }
      break;
    case 3:
      if ((Ht(t, e), cn(e), r & 4 && n !== null && n.memoizedState.isDehydrated))
        try {
          As(t.containerInfo);
        } catch (p) {
          Ce(e, e.return, p);
        }
      break;
    case 4:
      Ht(t, e), cn(e);
      break;
    case 13:
      Ht(t, e),
        cn(e),
        (i = e.child),
        i.flags & 8192 &&
          ((o = i.memoizedState !== null),
          (i.stateNode.isHidden = o),
          !o || (i.alternate !== null && i.alternate.memoizedState !== null) || (By = Ne())),
        r & 4 && N1(e);
      break;
    case 22:
      if (
        ((c = n !== null && n.memoizedState !== null),
        e.mode & 1 ? ((nt = (l = nt) || c), Ht(t, e), (nt = l)) : Ht(t, e),
        cn(e),
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
                  gs(4, d, d.return);
                  break;
                case 1:
                  Fi(d, d.return);
                  var v = d.stateNode;
                  if (typeof v.componentWillUnmount == "function") {
                    (r = d), (n = d.return);
                    try {
                      (t = r),
                        (v.props = t.memoizedProps),
                        (v.state = t.memoizedState),
                        v.componentWillUnmount();
                    } catch (p) {
                      Ce(r, n, p);
                    }
                  }
                  break;
                case 5:
                  Fi(d, d.return);
                  break;
                case 22:
                  if (d.memoizedState !== null) {
                    I1(f);
                    continue;
                  }
              }
              h !== null ? ((h.return = d), (H = h)) : I1(f);
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
                      (a.style.display = jk("display", s)));
              } catch (p) {
                Ce(e, e.return, p);
              }
            }
          } else if (f.tag === 6) {
            if (c === null)
              try {
                f.stateNode.nodeValue = l ? "" : f.memoizedProps;
              } catch (p) {
                Ce(e, e.return, p);
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
      Ht(t, e), cn(e), r & 4 && N1(e);
      break;
    case 21:
      break;
    default:
      Ht(t, e), cn(e);
  }
}
function cn(e) {
  var t = e.flags;
  if (t & 2) {
    try {
      e: {
        for (var n = e.return; n !== null; ) {
          if (fR(n)) {
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
          r.flags & 32 && (Ts(i, ""), (r.flags &= -33));
          var o = A1(e);
          hv(e, o, i);
          break;
        case 3:
        case 4:
          var s = r.stateNode.containerInfo,
            a = A1(e);
          dv(e, a, s);
          break;
        default:
          throw Error(z(161));
      }
    } catch (u) {
      Ce(e, e.return, u);
    }
    e.flags &= -3;
  }
  t & 4096 && (e.flags &= -4097);
}
function iF(e, t, n) {
  (H = e), pR(e);
}
function pR(e, t, n) {
  for (var r = (e.mode & 1) !== 0; H !== null; ) {
    var i = H,
      o = i.child;
    if (i.tag === 22 && r) {
      var s = i.memoizedState !== null || Fa;
      if (!s) {
        var a = i.alternate,
          u = (a !== null && a.memoizedState !== null) || nt;
        a = Fa;
        var l = nt;
        if (((Fa = s), (nt = u) && !l))
          for (H = i; H !== null; )
            (s = H),
              (u = s.child),
              s.tag === 22 && s.memoizedState !== null
                ? D1(i)
                : u !== null
                ? ((u.return = s), (H = u))
                : D1(i);
        for (; o !== null; ) (H = o), pR(o), (o = o.sibling);
        (H = i), (Fa = a), (nt = l);
      }
      M1(e);
    } else i.subtreeFlags & 8772 && o !== null ? ((o.return = i), (H = o)) : M1(e);
  }
}
function M1(e) {
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
              nt || Rl(5, t);
              break;
            case 1:
              var r = t.stateNode;
              if (t.flags & 4 && !nt)
                if (n === null) r.componentDidMount();
                else {
                  var i = t.elementType === t.type ? n.memoizedProps : Wt(t.type, n.memoizedProps);
                  r.componentDidUpdate(i, n.memoizedState, r.__reactInternalSnapshotBeforeUpdate);
                }
              var o = t.updateQueue;
              o !== null && g1(t, o, r);
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
                g1(t, s, n);
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
                    f !== null && As(f);
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
        nt || (t.flags & 512 && fv(t));
      } catch (d) {
        Ce(t, t.return, d);
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
function I1(e) {
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
function D1(e) {
  for (; H !== null; ) {
    var t = H;
    try {
      switch (t.tag) {
        case 0:
        case 11:
        case 15:
          var n = t.return;
          try {
            Rl(4, t);
          } catch (u) {
            Ce(t, n, u);
          }
          break;
        case 1:
          var r = t.stateNode;
          if (typeof r.componentDidMount == "function") {
            var i = t.return;
            try {
              r.componentDidMount();
            } catch (u) {
              Ce(t, i, u);
            }
          }
          var o = t.return;
          try {
            fv(t);
          } catch (u) {
            Ce(t, o, u);
          }
          break;
        case 5:
          var s = t.return;
          try {
            fv(t);
          } catch (u) {
            Ce(t, s, u);
          }
      }
    } catch (u) {
      Ce(t, t.return, u);
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
var oF = Math.ceil,
  Ku = Xn.ReactCurrentDispatcher,
  $y = Xn.ReactCurrentOwner,
  Vt = Xn.ReactCurrentBatchConfig,
  ae = 0,
  Ue = null,
  Me = null,
  Ke = 0,
  _t = 0,
  Vi = Mr(0),
  Le = 0,
  $s = null,
  oi = 0,
  Al = 0,
  zy = 0,
  vs = null,
  ht = null,
  By = 0,
  uo = 1 / 0,
  An = null,
  Yu = !1,
  pv = null,
  Sr = null,
  Va = !1,
  gr = null,
  Xu = 0,
  ys = 0,
  mv = null,
  pu = -1,
  mu = 0;
function at() {
  return ae & 6 ? Ne() : pu !== -1 ? pu : (pu = Ne());
}
function br(e) {
  return e.mode & 1
    ? ae & 2 && Ke !== 0
      ? Ke & -Ke
      : zL.transition !== null
      ? (mu === 0 && (mu = Qk()), mu)
      : ((e = ce), e !== 0 || ((e = window.event), (e = e === void 0 ? 16 : oP(e.type))), e)
    : 1;
}
function Jt(e, t, n, r) {
  if (50 < ys) throw ((ys = 0), (mv = null), Error(z(185)));
  ia(e, n, r),
    (!(ae & 2) || e !== Ue) &&
      (e === Ue && (!(ae & 2) && (Al |= n), Le === 4 && dr(e, Ke)),
      yt(e, r),
      n === 1 && ae === 0 && !(t.mode & 1) && ((uo = Ne() + 500), Tl && Ir()));
}
function yt(e, t) {
  var n = e.callbackNode;
  zO(e, t);
  var r = Iu(e, e === Ue ? Ke : 0);
  if (r === 0) n !== null && Bw(n), (e.callbackNode = null), (e.callbackPriority = 0);
  else if (((t = r & -r), e.callbackPriority !== t)) {
    if ((n != null && Bw(n), t === 1))
      e.tag === 0 ? $L(O1.bind(null, e)) : EP(O1.bind(null, e)),
        FL(function () {
          !(ae & 6) && Ir();
        }),
        (n = null);
    else {
      switch (Jk(r)) {
        case 1:
          n = my;
          break;
        case 4:
          n = Xk;
          break;
        case 16:
          n = Mu;
          break;
        case 536870912:
          n = Zk;
          break;
        default:
          n = Mu;
      }
      n = SR(n, mR.bind(null, e));
    }
    (e.callbackPriority = t), (e.callbackNode = n);
  }
}
function mR(e, t) {
  if (((pu = -1), (mu = 0), ae & 6)) throw Error(z(327));
  var n = e.callbackNode;
  if (Xi() && e.callbackNode !== n) return null;
  var r = Iu(e, e === Ue ? Ke : 0);
  if (r === 0) return null;
  if (r & 30 || r & e.expiredLanes || t) t = Zu(e, r);
  else {
    t = r;
    var i = ae;
    ae |= 2;
    var o = vR();
    (Ue !== e || Ke !== t) && ((An = null), (uo = Ne() + 500), Zr(e, t));
    do
      try {
        uF();
        break;
      } catch (a) {
        gR(e, a);
      }
    while (!0);
    Py(), (Ku.current = o), (ae = i), Me !== null ? (t = 0) : ((Ue = null), (Ke = 0), (t = Le));
  }
  if (t !== 0) {
    if ((t === 2 && ((i = zg(e)), i !== 0 && ((r = i), (t = gv(e, i)))), t === 1))
      throw ((n = $s), Zr(e, 0), dr(e, r), yt(e, Ne()), n);
    if (t === 6) dr(e, r);
    else {
      if (
        ((i = e.current.alternate),
        !(r & 30) &&
          !sF(i) &&
          ((t = Zu(e, r)), t === 2 && ((o = zg(e)), o !== 0 && ((r = o), (t = gv(e, o)))), t === 1))
      )
        throw ((n = $s), Zr(e, 0), dr(e, r), yt(e, Ne()), n);
      switch (((e.finishedWork = i), (e.finishedLanes = r), t)) {
        case 0:
        case 1:
          throw Error(z(345));
        case 2:
          qr(e, ht, An);
          break;
        case 3:
          if ((dr(e, r), (r & 130023424) === r && ((t = By + 500 - Ne()), 10 < t))) {
            if (Iu(e, 0) !== 0) break;
            if (((i = e.suspendedLanes), (i & r) !== r)) {
              at(), (e.pingedLanes |= e.suspendedLanes & i);
              break;
            }
            e.timeoutHandle = Xg(qr.bind(null, e, ht, An), t);
            break;
          }
          qr(e, ht, An);
          break;
        case 4:
          if ((dr(e, r), (r & 4194240) === r)) break;
          for (t = e.eventTimes, i = -1; 0 < r; ) {
            var s = 31 - Qt(r);
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
                : 1960 * oF(r / 1960)) - r),
            10 < r)
          ) {
            e.timeoutHandle = Xg(qr.bind(null, e, ht, An), r);
            break;
          }
          qr(e, ht, An);
          break;
        case 5:
          qr(e, ht, An);
          break;
        default:
          throw Error(z(329));
      }
    }
  }
  return yt(e, Ne()), e.callbackNode === n ? mR.bind(null, e) : null;
}
function gv(e, t) {
  var n = vs;
  return (
    e.current.memoizedState.isDehydrated && (Zr(e, t).flags |= 256),
    (e = Zu(e, t)),
    e !== 2 && ((t = ht), (ht = n), t !== null && vv(t)),
    e
  );
}
function vv(e) {
  ht === null ? (ht = e) : ht.push.apply(ht, e);
}
function sF(e) {
  for (var t = e; ; ) {
    if (t.flags & 16384) {
      var n = t.updateQueue;
      if (n !== null && ((n = n.stores), n !== null))
        for (var r = 0; r < n.length; r++) {
          var i = n[r],
            o = i.getSnapshot;
          i = i.value;
          try {
            if (!tn(o(), i)) return !1;
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
function dr(e, t) {
  for (
    t &= ~zy, t &= ~Al, e.suspendedLanes |= t, e.pingedLanes &= ~t, e = e.expirationTimes;
    0 < t;

  ) {
    var n = 31 - Qt(t),
      r = 1 << n;
    (e[n] = -1), (t &= ~r);
  }
}
function O1(e) {
  if (ae & 6) throw Error(z(327));
  Xi();
  var t = Iu(e, 0);
  if (!(t & 1)) return yt(e, Ne()), null;
  var n = Zu(e, t);
  if (e.tag !== 0 && n === 2) {
    var r = zg(e);
    r !== 0 && ((t = r), (n = gv(e, r)));
  }
  if (n === 1) throw ((n = $s), Zr(e, 0), dr(e, t), yt(e, Ne()), n);
  if (n === 6) throw Error(z(345));
  return (
    (e.finishedWork = e.current.alternate), (e.finishedLanes = t), qr(e, ht, An), yt(e, Ne()), null
  );
}
function Uy(e, t) {
  var n = ae;
  ae |= 1;
  try {
    return e(t);
  } finally {
    (ae = n), ae === 0 && ((uo = Ne() + 500), Tl && Ir());
  }
}
function si(e) {
  gr !== null && gr.tag === 0 && !(ae & 6) && Xi();
  var t = ae;
  ae |= 1;
  var n = Vt.transition,
    r = ce;
  try {
    if (((Vt.transition = null), (ce = 1), e)) return e();
  } finally {
    (ce = r), (Vt.transition = n), (ae = t), !(ae & 6) && Ir();
  }
}
function Hy() {
  (_t = Vi.current), ge(Vi);
}
function Zr(e, t) {
  (e.finishedWork = null), (e.finishedLanes = 0);
  var n = e.timeoutHandle;
  if ((n !== -1 && ((e.timeoutHandle = -1), LL(n)), Me !== null))
    for (n = Me.return; n !== null; ) {
      var r = n;
      switch ((Cy(r), r.tag)) {
        case 1:
          (r = r.type.childContextTypes), r != null && Vu();
          break;
        case 3:
          so(), ge(gt), ge(rt), Dy();
          break;
        case 5:
          Iy(r);
          break;
        case 4:
          so();
          break;
        case 13:
          ge(we);
          break;
        case 19:
          ge(we);
          break;
        case 10:
          Ry(r.type._context);
          break;
        case 22:
        case 23:
          Hy();
      }
      n = n.return;
    }
  if (
    ((Ue = e),
    (Me = e = Er(e.current, null)),
    (Ke = _t = t),
    (Le = 0),
    ($s = null),
    (zy = Al = oi = 0),
    (ht = vs = null),
    Hr !== null)
  ) {
    for (t = 0; t < Hr.length; t++)
      if (((n = Hr[t]), (r = n.interleaved), r !== null)) {
        n.interleaved = null;
        var i = r.next,
          o = n.pending;
        if (o !== null) {
          var s = o.next;
          (o.next = i), (r.next = s);
        }
        n.pending = r;
      }
    Hr = null;
  }
  return e;
}
function gR(e, t) {
  do {
    var n = Me;
    try {
      if ((Py(), (fu.current = Wu), Gu)) {
        for (var r = _e.memoizedState; r !== null; ) {
          var i = r.queue;
          i !== null && (i.pending = null), (r = r.next);
        }
        Gu = !1;
      }
      if (
        ((ii = 0),
        (ze = Oe = _e = null),
        (ms = !1),
        (Vs = 0),
        ($y.current = null),
        n === null || n.return === null)
      ) {
        (Le = 1), ($s = t), (Me = null);
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
          var h = S1(s);
          if (h !== null) {
            (h.flags &= -257), b1(h, s, a, o, t), h.mode & 1 && _1(o, l, t), (t = h), (u = l);
            var v = t.updateQueue;
            if (v === null) {
              var p = new Set();
              p.add(u), (t.updateQueue = p);
            } else v.add(u);
            break e;
          } else {
            if (!(t & 1)) {
              _1(o, l, t), Gy();
              break e;
            }
            u = Error(z(426));
          }
        } else if (ve && a.mode & 1) {
          var y = S1(s);
          if (y !== null) {
            !(y.flags & 65536) && (y.flags |= 256), b1(y, s, a, o, t), Ty(ao(u, a));
            break e;
          }
        }
        (o = u = ao(u, a)), Le !== 4 && (Le = 2), vs === null ? (vs = [o]) : vs.push(o), (o = s);
        do {
          switch (o.tag) {
            case 3:
              (o.flags |= 65536), (t &= -t), (o.lanes |= t);
              var m = JP(o, u, t);
              m1(o, m);
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
                    (Sr === null || !Sr.has(w))))
              ) {
                (o.flags |= 65536), (t &= -t), (o.lanes |= t);
                var x = eR(o, a, t);
                m1(o, x);
                break e;
              }
          }
          o = o.return;
        } while (o !== null);
      }
      wR(n);
    } catch (S) {
      (t = S), Me === n && n !== null && (Me = n = n.return);
      continue;
    }
    break;
  } while (!0);
}
function vR() {
  var e = Ku.current;
  return (Ku.current = Wu), e === null ? Wu : e;
}
function Gy() {
  (Le === 0 || Le === 3 || Le === 2) && (Le = 4),
    Ue === null || (!(oi & 268435455) && !(Al & 268435455)) || dr(Ue, Ke);
}
function Zu(e, t) {
  var n = ae;
  ae |= 2;
  var r = vR();
  (Ue !== e || Ke !== t) && ((An = null), Zr(e, t));
  do
    try {
      aF();
      break;
    } catch (i) {
      gR(e, i);
    }
  while (!0);
  if ((Py(), (ae = n), (Ku.current = r), Me !== null)) throw Error(z(261));
  return (Ue = null), (Ke = 0), Le;
}
function aF() {
  for (; Me !== null; ) yR(Me);
}
function uF() {
  for (; Me !== null && !IO(); ) yR(Me);
}
function yR(e) {
  var t = _R(e.alternate, e, _t);
  (e.memoizedProps = e.pendingProps), t === null ? wR(e) : (Me = t), ($y.current = null);
}
function wR(e) {
  var t = e;
  do {
    var n = t.alternate;
    if (((e = t.return), t.flags & 32768)) {
      if (((n = tF(n, t)), n !== null)) {
        (n.flags &= 32767), (Me = n);
        return;
      }
      if (e !== null) (e.flags |= 32768), (e.subtreeFlags = 0), (e.deletions = null);
      else {
        (Le = 6), (Me = null);
        return;
      }
    } else if (((n = eF(n, t, _t)), n !== null)) {
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
function qr(e, t, n) {
  var r = ce,
    i = Vt.transition;
  try {
    (Vt.transition = null), (ce = 1), lF(e, t, n, r);
  } finally {
    (Vt.transition = i), (ce = r);
  }
  return null;
}
function lF(e, t, n, r) {
  do Xi();
  while (gr !== null);
  if (ae & 6) throw Error(z(327));
  n = e.finishedWork;
  var i = e.finishedLanes;
  if (n === null) return null;
  if (((e.finishedWork = null), (e.finishedLanes = 0), n === e.current)) throw Error(z(177));
  (e.callbackNode = null), (e.callbackPriority = 0);
  var o = n.lanes | n.childLanes;
  if (
    (BO(e, o),
    e === Ue && ((Me = Ue = null), (Ke = 0)),
    (!(n.subtreeFlags & 2064) && !(n.flags & 2064)) ||
      Va ||
      ((Va = !0),
      SR(Mu, function () {
        return Xi(), null;
      })),
    (o = (n.flags & 15990) !== 0),
    n.subtreeFlags & 15990 || o)
  ) {
    (o = Vt.transition), (Vt.transition = null);
    var s = ce;
    ce = 1;
    var a = ae;
    (ae |= 4),
      ($y.current = null),
      rF(e, n),
      hR(n, e),
      RL(Kg),
      (Du = !!Wg),
      (Kg = Wg = null),
      (e.current = n),
      iF(n),
      DO(),
      (ae = a),
      (ce = s),
      (Vt.transition = o);
  } else e.current = n;
  if (
    (Va && ((Va = !1), (gr = e), (Xu = i)),
    (o = e.pendingLanes),
    o === 0 && (Sr = null),
    FO(n.stateNode),
    yt(e, Ne()),
    t !== null)
  )
    for (r = e.onRecoverableError, n = 0; n < t.length; n++)
      (i = t[n]), r(i.value, { componentStack: i.stack, digest: i.digest });
  if (Yu) throw ((Yu = !1), (e = pv), (pv = null), e);
  return (
    Xu & 1 && e.tag !== 0 && Xi(),
    (o = e.pendingLanes),
    o & 1 ? (e === mv ? ys++ : ((ys = 0), (mv = e))) : (ys = 0),
    Ir(),
    null
  );
}
function Xi() {
  if (gr !== null) {
    var e = Jk(Xu),
      t = Vt.transition,
      n = ce;
    try {
      if (((Vt.transition = null), (ce = 16 > e ? 16 : e), gr === null)) var r = !1;
      else {
        if (((e = gr), (gr = null), (Xu = 0), ae & 6)) throw Error(z(331));
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
                      gs(8, c, o);
                  }
                  var f = c.child;
                  if (f !== null) (f.return = c), (H = f);
                  else
                    for (; H !== null; ) {
                      c = H;
                      var d = c.sibling,
                        h = c.return;
                      if ((cR(c), c === l)) {
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
                    gs(9, o, o.return);
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
                      Rl(9, a);
                  }
                } catch (S) {
                  Ce(a, a.return, S);
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
        if (((ae = i), Ir(), mn && typeof mn.onPostCommitFiberRoot == "function"))
          try {
            mn.onPostCommitFiberRoot(_l, e);
          } catch {}
        r = !0;
      }
      return r;
    } finally {
      (ce = n), (Vt.transition = t);
    }
  }
  return !1;
}
function L1(e, t, n) {
  (t = ao(n, t)),
    (t = JP(e, t, 1)),
    (e = _r(e, t, 1)),
    (t = at()),
    e !== null && (ia(e, 1, t), yt(e, t));
}
function Ce(e, t, n) {
  if (e.tag === 3) L1(e, e, n);
  else
    for (; t !== null; ) {
      if (t.tag === 3) {
        L1(t, e, n);
        break;
      } else if (t.tag === 1) {
        var r = t.stateNode;
        if (
          typeof t.type.getDerivedStateFromError == "function" ||
          (typeof r.componentDidCatch == "function" && (Sr === null || !Sr.has(r)))
        ) {
          (e = ao(n, e)),
            (e = eR(t, e, 1)),
            (t = _r(t, e, 1)),
            (e = at()),
            t !== null && (ia(t, 1, e), yt(t, e));
          break;
        }
      }
      t = t.return;
    }
}
function cF(e, t, n) {
  var r = e.pingCache;
  r !== null && r.delete(t),
    (t = at()),
    (e.pingedLanes |= e.suspendedLanes & n),
    Ue === e &&
      (Ke & n) === n &&
      (Le === 4 || (Le === 3 && (Ke & 130023424) === Ke && 500 > Ne() - By) ? Zr(e, 0) : (zy |= n)),
    yt(e, t);
}
function xR(e, t) {
  t === 0 && (e.mode & 1 ? ((t = Pa), (Pa <<= 1), !(Pa & 130023424) && (Pa = 4194304)) : (t = 1));
  var n = at();
  (e = Bn(e, t)), e !== null && (ia(e, t, n), yt(e, n));
}
function fF(e) {
  var t = e.memoizedState,
    n = 0;
  t !== null && (n = t.retryLane), xR(e, n);
}
function dF(e, t) {
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
  r !== null && r.delete(t), xR(e, n);
}
var _R;
_R = function (e, t, n) {
  if (e !== null)
    if (e.memoizedProps !== t.pendingProps || gt.current) pt = !0;
    else {
      if (!(e.lanes & n) && !(t.flags & 128)) return (pt = !1), JL(e, t, n);
      pt = !!(e.flags & 131072);
    }
  else (pt = !1), ve && t.flags & 1048576 && CP(t, $u, t.index);
  switch (((t.lanes = 0), t.tag)) {
    case 2:
      var r = t.type;
      hu(e, t), (e = t.pendingProps);
      var i = ro(t, rt.current);
      Yi(t, n), (i = Ly(null, t, r, e, i, n));
      var o = Fy();
      return (
        (t.flags |= 1),
        typeof i == "object" && i !== null && typeof i.render == "function" && i.$$typeof === void 0
          ? ((t.tag = 1),
            (t.memoizedState = null),
            (t.updateQueue = null),
            vt(r) ? ((o = !0), ju(t)) : (o = !1),
            (t.memoizedState = i.state !== null && i.state !== void 0 ? i.state : null),
            Ny(t),
            (i.updater = Pl),
            (t.stateNode = i),
            (i._reactInternals = t),
            rv(t, r, e, n),
            (t = sv(null, t, r, !0, o, n)))
          : ((t.tag = 0), ve && o && Ey(t), st(null, t, i, n), (t = t.child)),
        t
      );
    case 16:
      r = t.elementType;
      e: {
        switch (
          (hu(e, t),
          (e = t.pendingProps),
          (i = r._init),
          (r = i(r._payload)),
          (t.type = r),
          (i = t.tag = pF(r)),
          (e = Wt(r, e)),
          i)
        ) {
          case 0:
            t = ov(null, t, r, e, n);
            break e;
          case 1:
            t = T1(null, t, r, e, n);
            break e;
          case 11:
            t = E1(null, t, r, e, n);
            break e;
          case 14:
            t = C1(null, t, r, Wt(r.type, e), n);
            break e;
        }
        throw Error(z(306, r, ""));
      }
      return t;
    case 0:
      return (
        (r = t.type),
        (i = t.pendingProps),
        (i = t.elementType === r ? i : Wt(r, i)),
        ov(e, t, r, i, n)
      );
    case 1:
      return (
        (r = t.type),
        (i = t.pendingProps),
        (i = t.elementType === r ? i : Wt(r, i)),
        T1(e, t, r, i, n)
      );
    case 3:
      e: {
        if ((iR(t), e === null)) throw Error(z(387));
        (r = t.pendingProps), (o = t.memoizedState), (i = o.element), NP(e, t), Uu(t, r, null, n);
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
            (i = ao(Error(z(423)), t)), (t = k1(e, t, r, n, i));
            break e;
          } else if (r !== i) {
            (i = ao(Error(z(424)), t)), (t = k1(e, t, r, n, i));
            break e;
          } else
            for (
              bt = xr(t.stateNode.containerInfo.firstChild),
                Et = t,
                ve = !0,
                Xt = null,
                n = RP(t, null, r, n),
                t.child = n;
              n;

            )
              (n.flags = (n.flags & -3) | 4096), (n = n.sibling);
        else {
          if ((io(), r === i)) {
            t = Un(e, t, n);
            break e;
          }
          st(e, t, r, n);
        }
        t = t.child;
      }
      return t;
    case 5:
      return (
        MP(t),
        e === null && ev(t),
        (r = t.type),
        (i = t.pendingProps),
        (o = e !== null ? e.memoizedProps : null),
        (s = i.children),
        Yg(r, i) ? (s = null) : o !== null && Yg(r, o) && (t.flags |= 32),
        rR(e, t),
        st(e, t, s, n),
        t.child
      );
    case 6:
      return e === null && ev(t), null;
    case 13:
      return oR(e, t, n);
    case 4:
      return (
        My(t, t.stateNode.containerInfo),
        (r = t.pendingProps),
        e === null ? (t.child = oo(t, null, r, n)) : st(e, t, r, n),
        t.child
      );
    case 11:
      return (
        (r = t.type),
        (i = t.pendingProps),
        (i = t.elementType === r ? i : Wt(r, i)),
        E1(e, t, r, i, n)
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
          de(zu, r._currentValue),
          (r._currentValue = s),
          o !== null)
        )
          if (tn(o.value, s)) {
            if (o.children === i.children && !gt.current) {
              t = Un(e, t, n);
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
                      (u = Fn(-1, n & -n)), (u.tag = 2);
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
                      tv(o.return, n, t),
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
                  tv(s, n, t),
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
        Yi(t, n),
        (i = jt(i)),
        (r = r(i)),
        (t.flags |= 1),
        st(e, t, r, n),
        t.child
      );
    case 14:
      return (r = t.type), (i = Wt(r, t.pendingProps)), (i = Wt(r.type, i)), C1(e, t, r, i, n);
    case 15:
      return tR(e, t, t.type, t.pendingProps, n);
    case 17:
      return (
        (r = t.type),
        (i = t.pendingProps),
        (i = t.elementType === r ? i : Wt(r, i)),
        hu(e, t),
        (t.tag = 1),
        vt(r) ? ((e = !0), ju(t)) : (e = !1),
        Yi(t, n),
        QP(t, r, i),
        rv(t, r, i, n),
        sv(null, t, r, !0, e, n)
      );
    case 19:
      return sR(e, t, n);
    case 22:
      return nR(e, t, n);
  }
  throw Error(z(156, t.tag));
};
function SR(e, t) {
  return Yk(e, t);
}
function hF(e, t, n, r) {
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
function Lt(e, t, n, r) {
  return new hF(e, t, n, r);
}
function Wy(e) {
  return (e = e.prototype), !(!e || !e.isReactComponent);
}
function pF(e) {
  if (typeof e == "function") return Wy(e) ? 1 : 0;
  if (e != null) {
    if (((e = e.$$typeof), e === dy)) return 11;
    if (e === hy) return 14;
  }
  return 2;
}
function Er(e, t) {
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
function gu(e, t, n, r, i, o) {
  var s = 2;
  if (((r = e), typeof e == "function")) Wy(e) && (s = 1);
  else if (typeof e == "string") s = 5;
  else
    e: switch (e) {
      case Pi:
        return Qr(n.children, i, o, t);
      case fy:
        (s = 8), (i |= 8);
        break;
      case kg:
        return (e = Lt(12, n, t, i | 2)), (e.elementType = kg), (e.lanes = o), e;
      case Pg:
        return (e = Lt(13, n, t, i)), (e.elementType = Pg), (e.lanes = o), e;
      case Rg:
        return (e = Lt(19, n, t, i)), (e.elementType = Rg), (e.lanes = o), e;
      case Mk:
        return Nl(n, i, o, t);
      default:
        if (typeof e == "object" && e !== null)
          switch (e.$$typeof) {
            case Ak:
              s = 10;
              break e;
            case Nk:
              s = 9;
              break e;
            case dy:
              s = 11;
              break e;
            case hy:
              s = 14;
              break e;
            case ar:
              (s = 16), (r = null);
              break e;
          }
        throw Error(z(130, e == null ? e : typeof e, ""));
    }
  return (t = Lt(s, n, t, i)), (t.elementType = e), (t.type = r), (t.lanes = o), t;
}
function Qr(e, t, n, r) {
  return (e = Lt(7, e, r, t)), (e.lanes = n), e;
}
function Nl(e, t, n, r) {
  return (
    (e = Lt(22, e, r, t)), (e.elementType = Mk), (e.lanes = n), (e.stateNode = { isHidden: !1 }), e
  );
}
function Kc(e, t, n) {
  return (e = Lt(6, e, null, t)), (e.lanes = n), e;
}
function Yc(e, t, n) {
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
function mF(e, t, n, r, i) {
  (this.tag = t),
    (this.containerInfo = e),
    (this.finishedWork = this.pingCache = this.current = this.pendingChildren = null),
    (this.timeoutHandle = -1),
    (this.callbackNode = this.pendingContext = this.context = null),
    (this.callbackPriority = 0),
    (this.eventTimes = Rc(0)),
    (this.expirationTimes = Rc(-1)),
    (this.entangledLanes = this.finishedLanes = this.mutableReadLanes = this.expiredLanes = this.pingedLanes = this.suspendedLanes = this.pendingLanes = 0),
    (this.entanglements = Rc(0)),
    (this.identifierPrefix = r),
    (this.onRecoverableError = i),
    (this.mutableSourceEagerHydrationData = null);
}
function Ky(e, t, n, r, i, o, s, a, u) {
  return (
    (e = new mF(e, t, n, a, u)),
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
    Ny(o),
    e
  );
}
function gF(e, t, n) {
  var r = 3 < arguments.length && arguments[3] !== void 0 ? arguments[3] : null;
  return {
    $$typeof: ki,
    key: r == null ? null : "" + r,
    children: e,
    containerInfo: t,
    implementation: n,
  };
}
function bR(e) {
  if (!e) return Pr;
  e = e._reactInternals;
  e: {
    if (fi(e) !== e || e.tag !== 1) throw Error(z(170));
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
    if (vt(n)) return bP(e, n, t);
  }
  return t;
}
function ER(e, t, n, r, i, o, s, a, u) {
  return (
    (e = Ky(n, r, !0, e, i, o, s, a, u)),
    (e.context = bR(null)),
    (n = e.current),
    (r = at()),
    (i = br(n)),
    (o = Fn(r, i)),
    (o.callback = t ?? null),
    _r(n, o, i),
    (e.current.lanes = i),
    ia(e, i, r),
    yt(e, r),
    e
  );
}
function Ml(e, t, n, r) {
  var i = t.current,
    o = at(),
    s = br(i);
  return (
    (n = bR(n)),
    t.context === null ? (t.context = n) : (t.pendingContext = n),
    (t = Fn(o, s)),
    (t.payload = { element: e }),
    (r = r === void 0 ? null : r),
    r !== null && (t.callback = r),
    (e = _r(i, t, s)),
    e !== null && (Jt(e, i, s, o), cu(e, i, s)),
    s
  );
}
function Qu(e) {
  if (((e = e.current), !e.child)) return null;
  switch (e.child.tag) {
    case 5:
      return e.child.stateNode;
    default:
      return e.child.stateNode;
  }
}
function F1(e, t) {
  if (((e = e.memoizedState), e !== null && e.dehydrated !== null)) {
    var n = e.retryLane;
    e.retryLane = n !== 0 && n < t ? n : t;
  }
}
function Yy(e, t) {
  F1(e, t), (e = e.alternate) && F1(e, t);
}
function vF() {
  return null;
}
var CR =
  typeof reportError == "function"
    ? reportError
    : function (e) {
        console.error(e);
      };
function Xy(e) {
  this._internalRoot = e;
}
Il.prototype.render = Xy.prototype.render = function (e) {
  var t = this._internalRoot;
  if (t === null) throw Error(z(409));
  Ml(e, t, null, null);
};
Il.prototype.unmount = Xy.prototype.unmount = function () {
  var e = this._internalRoot;
  if (e !== null) {
    this._internalRoot = null;
    var t = e.containerInfo;
    si(function () {
      Ml(null, e, null, null);
    }),
      (t[zn] = null);
  }
};
function Il(e) {
  this._internalRoot = e;
}
Il.prototype.unstable_scheduleHydration = function (e) {
  if (e) {
    var t = nP();
    e = { blockedOn: null, target: e, priority: t };
    for (var n = 0; n < fr.length && t !== 0 && t < fr[n].priority; n++);
    fr.splice(n, 0, e), n === 0 && iP(e);
  }
};
function Zy(e) {
  return !(!e || (e.nodeType !== 1 && e.nodeType !== 9 && e.nodeType !== 11));
}
function Dl(e) {
  return !(
    !e ||
    (e.nodeType !== 1 &&
      e.nodeType !== 9 &&
      e.nodeType !== 11 &&
      (e.nodeType !== 8 || e.nodeValue !== " react-mount-point-unstable "))
  );
}
function V1() {}
function yF(e, t, n, r, i) {
  if (i) {
    if (typeof r == "function") {
      var o = r;
      r = function () {
        var l = Qu(s);
        o.call(l);
      };
    }
    var s = ER(t, r, e, 0, null, !1, !1, "", V1);
    return (
      (e._reactRootContainer = s),
      (e[zn] = s.current),
      Is(e.nodeType === 8 ? e.parentNode : e),
      si(),
      s
    );
  }
  for (; (i = e.lastChild); ) e.removeChild(i);
  if (typeof r == "function") {
    var a = r;
    r = function () {
      var l = Qu(u);
      a.call(l);
    };
  }
  var u = Ky(e, 0, !1, null, null, !1, !1, "", V1);
  return (
    (e._reactRootContainer = u),
    (e[zn] = u.current),
    Is(e.nodeType === 8 ? e.parentNode : e),
    si(function () {
      Ml(t, u, n, r);
    }),
    u
  );
}
function Ol(e, t, n, r, i) {
  var o = n._reactRootContainer;
  if (o) {
    var s = o;
    if (typeof i == "function") {
      var a = i;
      i = function () {
        var u = Qu(s);
        a.call(u);
      };
    }
    Ml(t, s, e, i);
  } else s = yF(n, t, e, i, r);
  return Qu(s);
}
eP = function (e) {
  switch (e.tag) {
    case 3:
      var t = e.stateNode;
      if (t.current.memoizedState.isDehydrated) {
        var n = Xo(t.pendingLanes);
        n !== 0 && (gy(t, n | 1), yt(t, Ne()), !(ae & 6) && ((uo = Ne() + 500), Ir()));
      }
      break;
    case 13:
      si(function () {
        var r = Bn(e, 1);
        if (r !== null) {
          var i = at();
          Jt(r, e, 1, i);
        }
      }),
        Yy(e, 1);
  }
};
vy = function (e) {
  if (e.tag === 13) {
    var t = Bn(e, 134217728);
    if (t !== null) {
      var n = at();
      Jt(t, e, 134217728, n);
    }
    Yy(e, 134217728);
  }
};
tP = function (e) {
  if (e.tag === 13) {
    var t = br(e),
      n = Bn(e, t);
    if (n !== null) {
      var r = at();
      Jt(n, e, t, r);
    }
    Yy(e, t);
  }
};
nP = function () {
  return ce;
};
rP = function (e, t) {
  var n = ce;
  try {
    return (ce = e), t();
  } finally {
    ce = n;
  }
};
jg = function (e, t, n) {
  switch (t) {
    case "input":
      if ((Mg(e, n), (t = n.name), n.type === "radio" && t != null)) {
        for (n = e; n.parentNode; ) n = n.parentNode;
        for (
          n = n.querySelectorAll("input[name=" + JSON.stringify("" + t) + '][type="radio"]'), t = 0;
          t < n.length;
          t++
        ) {
          var r = n[t];
          if (r !== e && r.form === e.form) {
            var i = Cl(r);
            if (!i) throw Error(z(90));
            Dk(r), Mg(r, i);
          }
        }
      }
      break;
    case "textarea":
      Lk(e, n);
      break;
    case "select":
      (t = n.value), t != null && Hi(e, !!n.multiple, t, !1);
  }
};
Bk = Uy;
Uk = si;
var wF = { usingClientEntryPoint: !1, Events: [sa, Mi, Cl, $k, zk, Uy] },
  jo = {
    findFiberByHostInstance: Ur,
    bundleType: 0,
    version: "18.3.1",
    rendererPackageName: "react-dom",
  },
  xF = {
    bundleType: jo.bundleType,
    version: jo.version,
    rendererPackageName: jo.rendererPackageName,
    rendererConfig: jo.rendererConfig,
    overrideHookState: null,
    overrideHookStateDeletePath: null,
    overrideHookStateRenamePath: null,
    overrideProps: null,
    overridePropsDeletePath: null,
    overridePropsRenamePath: null,
    setErrorHandler: null,
    setSuspenseHandler: null,
    scheduleUpdate: null,
    currentDispatcherRef: Xn.ReactCurrentDispatcher,
    findHostInstanceByFiber: function (e) {
      return (e = Wk(e)), e === null ? null : e.stateNode;
    },
    findFiberByHostInstance: jo.findFiberByHostInstance || vF,
    findHostInstancesForRefresh: null,
    scheduleRefresh: null,
    scheduleRoot: null,
    setRefreshHandler: null,
    getCurrentFiber: null,
    reconcilerVersion: "18.3.1-next-f1338f8080-20240426",
  };
if (typeof __REACT_DEVTOOLS_GLOBAL_HOOK__ < "u") {
  var ja = __REACT_DEVTOOLS_GLOBAL_HOOK__;
  if (!ja.isDisabled && ja.supportsFiber)
    try {
      (_l = ja.inject(xF)), (mn = ja);
    } catch {}
}
Rt.__SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED = wF;
Rt.createPortal = function (e, t) {
  var n = 2 < arguments.length && arguments[2] !== void 0 ? arguments[2] : null;
  if (!Zy(t)) throw Error(z(200));
  return gF(e, t, null, n);
};
Rt.createRoot = function (e, t) {
  if (!Zy(e)) throw Error(z(299));
  var n = !1,
    r = "",
    i = CR;
  return (
    t != null &&
      (t.unstable_strictMode === !0 && (n = !0),
      t.identifierPrefix !== void 0 && (r = t.identifierPrefix),
      t.onRecoverableError !== void 0 && (i = t.onRecoverableError)),
    (t = Ky(e, 1, !1, null, null, n, !1, r, i)),
    (e[zn] = t.current),
    Is(e.nodeType === 8 ? e.parentNode : e),
    new Xy(t)
  );
};
Rt.findDOMNode = function (e) {
  if (e == null) return null;
  if (e.nodeType === 1) return e;
  var t = e._reactInternals;
  if (t === void 0)
    throw typeof e.render == "function"
      ? Error(z(188))
      : ((e = Object.keys(e).join(",")), Error(z(268, e)));
  return (e = Wk(t)), (e = e === null ? null : e.stateNode), e;
};
Rt.flushSync = function (e) {
  return si(e);
};
Rt.hydrate = function (e, t, n) {
  if (!Dl(t)) throw Error(z(200));
  return Ol(null, e, t, !0, n);
};
Rt.hydrateRoot = function (e, t, n) {
  if (!Zy(e)) throw Error(z(405));
  var r = (n != null && n.hydratedSources) || null,
    i = !1,
    o = "",
    s = CR;
  if (
    (n != null &&
      (n.unstable_strictMode === !0 && (i = !0),
      n.identifierPrefix !== void 0 && (o = n.identifierPrefix),
      n.onRecoverableError !== void 0 && (s = n.onRecoverableError)),
    (t = ER(t, null, e, 1, n ?? null, i, !1, o, s)),
    (e[zn] = t.current),
    Is(e),
    r)
  )
    for (e = 0; e < r.length; e++)
      (n = r[e]),
        (i = n._getVersion),
        (i = i(n._source)),
        t.mutableSourceEagerHydrationData == null
          ? (t.mutableSourceEagerHydrationData = [n, i])
          : t.mutableSourceEagerHydrationData.push(n, i);
  return new Il(t);
};
Rt.render = function (e, t, n) {
  if (!Dl(t)) throw Error(z(200));
  return Ol(null, e, t, !1, n);
};
Rt.unmountComponentAtNode = function (e) {
  if (!Dl(e)) throw Error(z(40));
  return e._reactRootContainer
    ? (si(function () {
        Ol(null, null, e, !1, function () {
          (e._reactRootContainer = null), (e[zn] = null);
        });
      }),
      !0)
    : !1;
};
Rt.unstable_batchedUpdates = Uy;
Rt.unstable_renderSubtreeIntoContainer = function (e, t, n, r) {
  if (!Dl(n)) throw Error(z(200));
  if (e == null || e._reactInternals === void 0) throw Error(z(38));
  return Ol(e, t, n, !1, r);
};
Rt.version = "18.3.1-next-f1338f8080-20240426";
function TR() {
  if (
    !(
      typeof __REACT_DEVTOOLS_GLOBAL_HOOK__ > "u" ||
      typeof __REACT_DEVTOOLS_GLOBAL_HOOK__.checkDCE != "function"
    )
  )
    try {
      __REACT_DEVTOOLS_GLOBAL_HOOK__.checkDCE(TR);
    } catch (e) {
      console.error(e);
    }
}
TR(), (Tk.exports = Rt);
var Qy = Tk.exports;
const _F = ry(Qy);
var j1 = Qy;
(Cg.createRoot = j1.createRoot), (Cg.hydrateRoot = j1.hydrateRoot);
const SF = {},
  q1 = (e) => {
    let t;
    const n = new Set(),
      r = (c, f) => {
        const d = typeof c == "function" ? c(t) : c;
        if (!Object.is(d, t)) {
          const h = t;
          (t = f ?? (typeof d != "object" || d === null) ? d : Object.assign({}, t, d)),
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
          (SF ? "production" : void 0) !== "production" &&
            console.warn(
              "[DEPRECATED] The `destroy` method will be unsupported in a future version. Instead use unsubscribe function returned by subscribe. Everything will be garbage-collected if store is garbage-collected."
            ),
            n.clear();
        },
      },
      l = (t = e(r, i, u));
    return u;
  },
  kR = (e) => (e ? q1(e) : q1);
var PR = { exports: {} },
  RR = {},
  AR = { exports: {} },
  NR = {};
/**
 * @license React
 * use-sync-external-store-shim.production.js
 *
 * Copyright (c) Meta Platforms, Inc. and affiliates.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */ var lo = _;
function bF(e, t) {
  return (e === t && (e !== 0 || 1 / e === 1 / t)) || (e !== e && t !== t);
}
var EF = typeof Object.is == "function" ? Object.is : bF,
  CF = lo.useState,
  TF = lo.useEffect,
  kF = lo.useLayoutEffect,
  PF = lo.useDebugValue;
function RF(e, t) {
  var n = t(),
    r = CF({ inst: { value: n, getSnapshot: t } }),
    i = r[0].inst,
    o = r[1];
  return (
    kF(
      function () {
        (i.value = n), (i.getSnapshot = t), Xc(i) && o({ inst: i });
      },
      [e, n, t]
    ),
    TF(
      function () {
        return (
          Xc(i) && o({ inst: i }),
          e(function () {
            Xc(i) && o({ inst: i });
          })
        );
      },
      [e]
    ),
    PF(n),
    n
  );
}
function Xc(e) {
  var t = e.getSnapshot;
  e = e.value;
  try {
    var n = t();
    return !EF(e, n);
  } catch {
    return !0;
  }
}
function AF(e, t) {
  return t();
}
var NF =
  typeof window > "u" || typeof window.document > "u" || typeof window.document.createElement > "u"
    ? AF
    : RF;
NR.useSyncExternalStore = lo.useSyncExternalStore !== void 0 ? lo.useSyncExternalStore : NF;
AR.exports = NR;
var MF = AR.exports;
/**
 * @license React
 * use-sync-external-store-shim/with-selector.production.js
 *
 * Copyright (c) Meta Platforms, Inc. and affiliates.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */ var Ll = _,
  IF = MF;
function DF(e, t) {
  return (e === t && (e !== 0 || 1 / e === 1 / t)) || (e !== e && t !== t);
}
var OF = typeof Object.is == "function" ? Object.is : DF,
  LF = IF.useSyncExternalStore,
  FF = Ll.useRef,
  VF = Ll.useEffect,
  jF = Ll.useMemo,
  qF = Ll.useDebugValue;
RR.useSyncExternalStoreWithSelector = function (e, t, n, r, i) {
  var o = FF(null);
  if (o.current === null) {
    var s = { hasValue: !1, value: null };
    o.current = s;
  } else s = o.current;
  o = jF(
    function () {
      function u(h) {
        if (!l) {
          if (((l = !0), (c = h), (h = r(h)), i !== void 0 && s.hasValue)) {
            var v = s.value;
            if (i(v, h)) return (f = v);
          }
          return (f = h);
        }
        if (((v = f), OF(c, h))) return v;
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
    [t, n, r, i]
  );
  var a = LF(e, o[0], o[1]);
  return (
    VF(
      function () {
        (s.hasValue = !0), (s.value = a);
      },
      [a]
    ),
    qF(a),
    a
  );
};
PR.exports = RR;
var $F = PR.exports;
const MR = ry($F),
  IR = {},
  { useDebugValue: zF } = L,
  { useSyncExternalStoreWithSelector: BF } = MR;
let $1 = !1;
const UF = (e) => e;
function HF(e, t = UF, n) {
  (IR ? "production" : void 0) !== "production" &&
    n &&
    !$1 &&
    (console.warn(
      "[DEPRECATED] Use `createWithEqualityFn` instead of `create` or use `useStoreWithEqualityFn` instead of `useStore`. They can be imported from 'zustand/traditional'. https://github.com/pmndrs/zustand/discussions/1937"
    ),
    ($1 = !0));
  const r = BF(e.subscribe, e.getState, e.getServerState || e.getInitialState, t, n);
  return zF(r), r;
}
const z1 = (e) => {
    (IR ? "production" : void 0) !== "production" &&
      typeof e != "function" &&
      console.warn(
        "[DEPRECATED] Passing a vanilla store will be unsupported in a future version. Instead use `import { useStore } from 'zustand'`."
      );
    const t = typeof e == "function" ? kR(e) : e,
      n = (r, i) => HF(t, r, i);
    return Object.assign(n, t), n;
  },
  GF = (e) => (e ? z1(e) : z1),
  Fl = GF((e, t) => ({
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
          : r
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
  WF = () => {
    const e = Fl((t) => t.connect);
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
const { useDebugValue: KF } = L,
  { useSyncExternalStoreWithSelector: YF } = MR,
  XF = (e) => e;
function DR(e, t = XF, n) {
  const r = YF(e.subscribe, e.getState, e.getServerState || e.getInitialState, t, n);
  return KF(r), r;
}
const B1 = (e, t) => {
    const n = kR(e),
      r = (i, o = t) => DR(n, i, o);
    return Object.assign(r, n), r;
  },
  ZF = (e, t) => (e ? B1(e, t) : B1);
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
var QF = { value: () => {} };
function Vl() {
  for (var e = 0, t = arguments.length, n = {}, r; e < t; ++e) {
    if (!(r = arguments[e] + "") || r in n || /[\s.]/.test(r))
      throw new Error("illegal type: " + r);
    n[r] = [];
  }
  return new vu(n);
}
function vu(e) {
  this._ = e;
}
function JF(e, t) {
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
vu.prototype = Vl.prototype = {
  constructor: vu,
  on: function (e, t) {
    var n = this._,
      r = JF(e + "", n),
      i,
      o = -1,
      s = r.length;
    if (arguments.length < 2) {
      for (; ++o < s; ) if ((i = (e = r[o]).type) && (i = e3(n[i], e.name))) return i;
      return;
    }
    if (t != null && typeof t != "function") throw new Error("invalid callback: " + t);
    for (; ++o < s; )
      if ((i = (e = r[o]).type)) n[i] = U1(n[i], e.name, t);
      else if (t == null) for (i in n) n[i] = U1(n[i], e.name, null);
    return this;
  },
  copy: function () {
    var e = {},
      t = this._;
    for (var n in t) e[n] = t[n].slice();
    return new vu(e);
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
function e3(e, t) {
  for (var n = 0, r = e.length, i; n < r; ++n) if ((i = e[n]).name === t) return i.value;
}
function U1(e, t, n) {
  for (var r = 0, i = e.length; r < i; ++r)
    if (e[r].name === t) {
      (e[r] = QF), (e = e.slice(0, r).concat(e.slice(r + 1)));
      break;
    }
  return n != null && e.push({ name: t, value: n }), e;
}
var yv = "http://www.w3.org/1999/xhtml";
const H1 = {
  svg: "http://www.w3.org/2000/svg",
  xhtml: yv,
  xlink: "http://www.w3.org/1999/xlink",
  xml: "http://www.w3.org/XML/1998/namespace",
  xmlns: "http://www.w3.org/2000/xmlns/",
};
function jl(e) {
  var t = (e += ""),
    n = t.indexOf(":");
  return (
    n >= 0 && (t = e.slice(0, n)) !== "xmlns" && (e = e.slice(n + 1)),
    H1.hasOwnProperty(t) ? { space: H1[t], local: e } : e
  );
}
function t3(e) {
  return function () {
    var t = this.ownerDocument,
      n = this.namespaceURI;
    return n === yv && t.documentElement.namespaceURI === yv
      ? t.createElement(e)
      : t.createElementNS(n, e);
  };
}
function n3(e) {
  return function () {
    return this.ownerDocument.createElementNS(e.space, e.local);
  };
}
function OR(e) {
  var t = jl(e);
  return (t.local ? n3 : t3)(t);
}
function r3() {}
function Jy(e) {
  return e == null
    ? r3
    : function () {
        return this.querySelector(e);
      };
}
function i3(e) {
  typeof e != "function" && (e = Jy(e));
  for (var t = this._groups, n = t.length, r = new Array(n), i = 0; i < n; ++i)
    for (var o = t[i], s = o.length, a = (r[i] = new Array(s)), u, l, c = 0; c < s; ++c)
      (u = o[c]) &&
        (l = e.call(u, u.__data__, c, o)) &&
        ("__data__" in u && (l.__data__ = u.__data__), (a[c] = l));
  return new kt(r, this._parents);
}
function o3(e) {
  return e == null ? [] : Array.isArray(e) ? e : Array.from(e);
}
function s3() {
  return [];
}
function LR(e) {
  return e == null
    ? s3
    : function () {
        return this.querySelectorAll(e);
      };
}
function a3(e) {
  return function () {
    return o3(e.apply(this, arguments));
  };
}
function u3(e) {
  typeof e == "function" ? (e = a3(e)) : (e = LR(e));
  for (var t = this._groups, n = t.length, r = [], i = [], o = 0; o < n; ++o)
    for (var s = t[o], a = s.length, u, l = 0; l < a; ++l)
      (u = s[l]) && (r.push(e.call(u, u.__data__, l, s)), i.push(u));
  return new kt(r, i);
}
function FR(e) {
  return function () {
    return this.matches(e);
  };
}
function VR(e) {
  return function (t) {
    return t.matches(e);
  };
}
var l3 = Array.prototype.find;
function c3(e) {
  return function () {
    return l3.call(this.children, e);
  };
}
function f3() {
  return this.firstElementChild;
}
function d3(e) {
  return this.select(e == null ? f3 : c3(typeof e == "function" ? e : VR(e)));
}
var h3 = Array.prototype.filter;
function p3() {
  return Array.from(this.children);
}
function m3(e) {
  return function () {
    return h3.call(this.children, e);
  };
}
function g3(e) {
  return this.selectAll(e == null ? p3 : m3(typeof e == "function" ? e : VR(e)));
}
function v3(e) {
  typeof e != "function" && (e = FR(e));
  for (var t = this._groups, n = t.length, r = new Array(n), i = 0; i < n; ++i)
    for (var o = t[i], s = o.length, a = (r[i] = []), u, l = 0; l < s; ++l)
      (u = o[l]) && e.call(u, u.__data__, l, o) && a.push(u);
  return new kt(r, this._parents);
}
function jR(e) {
  return new Array(e.length);
}
function y3() {
  return new kt(this._enter || this._groups.map(jR), this._parents);
}
function Ju(e, t) {
  (this.ownerDocument = e.ownerDocument),
    (this.namespaceURI = e.namespaceURI),
    (this._next = null),
    (this._parent = e),
    (this.__data__ = t);
}
Ju.prototype = {
  constructor: Ju,
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
function w3(e) {
  return function () {
    return e;
  };
}
function x3(e, t, n, r, i, o) {
  for (var s = 0, a, u = t.length, l = o.length; s < l; ++s)
    (a = t[s]) ? ((a.__data__ = o[s]), (r[s] = a)) : (n[s] = new Ju(e, o[s]));
  for (; s < u; ++s) (a = t[s]) && (i[s] = a);
}
function _3(e, t, n, r, i, o, s) {
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
      (u = l.get(h)) ? ((r[a] = u), (u.__data__ = o[a]), l.delete(h)) : (n[a] = new Ju(e, o[a]));
  for (a = 0; a < c; ++a) (u = t[a]) && l.get(d[a]) === u && (i[a] = u);
}
function S3(e) {
  return e.__data__;
}
function b3(e, t) {
  if (!arguments.length) return Array.from(this, S3);
  var n = t ? _3 : x3,
    r = this._parents,
    i = this._groups;
  typeof e != "function" && (e = w3(e));
  for (var o = i.length, s = new Array(o), a = new Array(o), u = new Array(o), l = 0; l < o; ++l) {
    var c = r[l],
      f = i[l],
      d = f.length,
      h = E3(e.call(c, c && c.__data__, l, r)),
      v = h.length,
      p = (a[l] = new Array(v)),
      y = (s[l] = new Array(v)),
      m = (u[l] = new Array(d));
    n(c, f, p, y, m, h, t);
    for (var g = 0, w = 0, x, S; g < v; ++g)
      if ((x = p[g])) {
        for (g >= w && (w = g + 1); !(S = y[w]) && ++w < v; );
        x._next = S || null;
      }
  }
  return (s = new kt(s, r)), (s._enter = a), (s._exit = u), s;
}
function E3(e) {
  return typeof e == "object" && "length" in e ? e : Array.from(e);
}
function C3() {
  return new kt(this._exit || this._groups.map(jR), this._parents);
}
function T3(e, t, n) {
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
function k3(e) {
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
function P3() {
  for (var e = this._groups, t = -1, n = e.length; ++t < n; )
    for (var r = e[t], i = r.length - 1, o = r[i], s; --i >= 0; )
      (s = r[i]) &&
        (o && s.compareDocumentPosition(o) ^ 4 && o.parentNode.insertBefore(s, o), (o = s));
  return this;
}
function R3(e) {
  e || (e = A3);
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
function A3(e, t) {
  return e < t ? -1 : e > t ? 1 : e >= t ? 0 : NaN;
}
function N3() {
  var e = arguments[0];
  return (arguments[0] = this), e.apply(null, arguments), this;
}
function M3() {
  return Array.from(this);
}
function I3() {
  for (var e = this._groups, t = 0, n = e.length; t < n; ++t)
    for (var r = e[t], i = 0, o = r.length; i < o; ++i) {
      var s = r[i];
      if (s) return s;
    }
  return null;
}
function D3() {
  let e = 0;
  for (const t of this) ++e;
  return e;
}
function O3() {
  return !this.node();
}
function L3(e) {
  for (var t = this._groups, n = 0, r = t.length; n < r; ++n)
    for (var i = t[n], o = 0, s = i.length, a; o < s; ++o)
      (a = i[o]) && e.call(a, a.__data__, o, i);
  return this;
}
function F3(e) {
  return function () {
    this.removeAttribute(e);
  };
}
function V3(e) {
  return function () {
    this.removeAttributeNS(e.space, e.local);
  };
}
function j3(e, t) {
  return function () {
    this.setAttribute(e, t);
  };
}
function q3(e, t) {
  return function () {
    this.setAttributeNS(e.space, e.local, t);
  };
}
function $3(e, t) {
  return function () {
    var n = t.apply(this, arguments);
    n == null ? this.removeAttribute(e) : this.setAttribute(e, n);
  };
}
function z3(e, t) {
  return function () {
    var n = t.apply(this, arguments);
    n == null ? this.removeAttributeNS(e.space, e.local) : this.setAttributeNS(e.space, e.local, n);
  };
}
function B3(e, t) {
  var n = jl(e);
  if (arguments.length < 2) {
    var r = this.node();
    return n.local ? r.getAttributeNS(n.space, n.local) : r.getAttribute(n);
  }
  return this.each(
    (t == null
      ? n.local
        ? V3
        : F3
      : typeof t == "function"
      ? n.local
        ? z3
        : $3
      : n.local
      ? q3
      : j3)(n, t)
  );
}
function qR(e) {
  return (e.ownerDocument && e.ownerDocument.defaultView) || (e.document && e) || e.defaultView;
}
function U3(e) {
  return function () {
    this.style.removeProperty(e);
  };
}
function H3(e, t, n) {
  return function () {
    this.style.setProperty(e, t, n);
  };
}
function G3(e, t, n) {
  return function () {
    var r = t.apply(this, arguments);
    r == null ? this.style.removeProperty(e) : this.style.setProperty(e, r, n);
  };
}
function W3(e, t, n) {
  return arguments.length > 1
    ? this.each((t == null ? U3 : typeof t == "function" ? G3 : H3)(e, t, n ?? ""))
    : co(this.node(), e);
}
function co(e, t) {
  return e.style.getPropertyValue(t) || qR(e).getComputedStyle(e, null).getPropertyValue(t);
}
function K3(e) {
  return function () {
    delete this[e];
  };
}
function Y3(e, t) {
  return function () {
    this[e] = t;
  };
}
function X3(e, t) {
  return function () {
    var n = t.apply(this, arguments);
    n == null ? delete this[e] : (this[e] = n);
  };
}
function Z3(e, t) {
  return arguments.length > 1
    ? this.each((t == null ? K3 : typeof t == "function" ? X3 : Y3)(e, t))
    : this.node()[e];
}
function $R(e) {
  return e.trim().split(/^|\s+/);
}
function e0(e) {
  return e.classList || new zR(e);
}
function zR(e) {
  (this._node = e), (this._names = $R(e.getAttribute("class") || ""));
}
zR.prototype = {
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
function BR(e, t) {
  for (var n = e0(e), r = -1, i = t.length; ++r < i; ) n.add(t[r]);
}
function UR(e, t) {
  for (var n = e0(e), r = -1, i = t.length; ++r < i; ) n.remove(t[r]);
}
function Q3(e) {
  return function () {
    BR(this, e);
  };
}
function J3(e) {
  return function () {
    UR(this, e);
  };
}
function eV(e, t) {
  return function () {
    (t.apply(this, arguments) ? BR : UR)(this, e);
  };
}
function tV(e, t) {
  var n = $R(e + "");
  if (arguments.length < 2) {
    for (var r = e0(this.node()), i = -1, o = n.length; ++i < o; ) if (!r.contains(n[i])) return !1;
    return !0;
  }
  return this.each((typeof t == "function" ? eV : t ? Q3 : J3)(n, t));
}
function nV() {
  this.textContent = "";
}
function rV(e) {
  return function () {
    this.textContent = e;
  };
}
function iV(e) {
  return function () {
    var t = e.apply(this, arguments);
    this.textContent = t ?? "";
  };
}
function oV(e) {
  return arguments.length
    ? this.each(e == null ? nV : (typeof e == "function" ? iV : rV)(e))
    : this.node().textContent;
}
function sV() {
  this.innerHTML = "";
}
function aV(e) {
  return function () {
    this.innerHTML = e;
  };
}
function uV(e) {
  return function () {
    var t = e.apply(this, arguments);
    this.innerHTML = t ?? "";
  };
}
function lV(e) {
  return arguments.length
    ? this.each(e == null ? sV : (typeof e == "function" ? uV : aV)(e))
    : this.node().innerHTML;
}
function cV() {
  this.nextSibling && this.parentNode.appendChild(this);
}
function fV() {
  return this.each(cV);
}
function dV() {
  this.previousSibling && this.parentNode.insertBefore(this, this.parentNode.firstChild);
}
function hV() {
  return this.each(dV);
}
function pV(e) {
  var t = typeof e == "function" ? e : OR(e);
  return this.select(function () {
    return this.appendChild(t.apply(this, arguments));
  });
}
function mV() {
  return null;
}
function gV(e, t) {
  var n = typeof e == "function" ? e : OR(e),
    r = t == null ? mV : typeof t == "function" ? t : Jy(t);
  return this.select(function () {
    return this.insertBefore(n.apply(this, arguments), r.apply(this, arguments) || null);
  });
}
function vV() {
  var e = this.parentNode;
  e && e.removeChild(this);
}
function yV() {
  return this.each(vV);
}
function wV() {
  var e = this.cloneNode(!1),
    t = this.parentNode;
  return t ? t.insertBefore(e, this.nextSibling) : e;
}
function xV() {
  var e = this.cloneNode(!0),
    t = this.parentNode;
  return t ? t.insertBefore(e, this.nextSibling) : e;
}
function _V(e) {
  return this.select(e ? xV : wV);
}
function SV(e) {
  return arguments.length ? this.property("__data__", e) : this.node().__data__;
}
function bV(e) {
  return function (t) {
    e.call(this, t, this.__data__);
  };
}
function EV(e) {
  return e
    .trim()
    .split(/^|\s+/)
    .map(function (t) {
      var n = "",
        r = t.indexOf(".");
      return r >= 0 && ((n = t.slice(r + 1)), (t = t.slice(0, r))), { type: t, name: n };
    });
}
function CV(e) {
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
function TV(e, t, n) {
  return function () {
    var r = this.__on,
      i,
      o = bV(t);
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
function kV(e, t, n) {
  var r = EV(e + ""),
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
  for (a = t ? TV : CV, i = 0; i < o; ++i) this.each(a(r[i], t, n));
  return this;
}
function HR(e, t, n) {
  var r = qR(e),
    i = r.CustomEvent;
  typeof i == "function"
    ? (i = new i(t, n))
    : ((i = r.document.createEvent("Event")),
      n
        ? (i.initEvent(t, n.bubbles, n.cancelable), (i.detail = n.detail))
        : i.initEvent(t, !1, !1)),
    e.dispatchEvent(i);
}
function PV(e, t) {
  return function () {
    return HR(this, e, t);
  };
}
function RV(e, t) {
  return function () {
    return HR(this, e, t.apply(this, arguments));
  };
}
function AV(e, t) {
  return this.each((typeof t == "function" ? RV : PV)(e, t));
}
function* NV() {
  for (var e = this._groups, t = 0, n = e.length; t < n; ++t)
    for (var r = e[t], i = 0, o = r.length, s; i < o; ++i) (s = r[i]) && (yield s);
}
var GR = [null];
function kt(e, t) {
  (this._groups = e), (this._parents = t);
}
function ua() {
  return new kt([[document.documentElement]], GR);
}
function MV() {
  return this;
}
kt.prototype = ua.prototype = {
  constructor: kt,
  select: i3,
  selectAll: u3,
  selectChild: d3,
  selectChildren: g3,
  filter: v3,
  data: b3,
  enter: y3,
  exit: C3,
  join: T3,
  merge: k3,
  selection: MV,
  order: P3,
  sort: R3,
  call: N3,
  nodes: M3,
  node: I3,
  size: D3,
  empty: O3,
  each: L3,
  attr: B3,
  style: W3,
  property: Z3,
  classed: tV,
  text: oV,
  html: lV,
  raise: fV,
  lower: hV,
  append: pV,
  insert: gV,
  remove: yV,
  clone: _V,
  datum: SV,
  on: kV,
  dispatch: AV,
  [Symbol.iterator]: NV,
};
function Ot(e) {
  return typeof e == "string"
    ? new kt([[document.querySelector(e)]], [document.documentElement])
    : new kt([[e]], GR);
}
function IV(e) {
  let t;
  for (; (t = e.sourceEvent); ) e = t;
  return e;
}
function Yt(e, t) {
  if (((e = IV(e)), t === void 0 && (t = e.currentTarget), t)) {
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
const DV = { passive: !1 },
  zs = { capture: !0, passive: !1 };
function Zc(e) {
  e.stopImmediatePropagation();
}
function Zi(e) {
  e.preventDefault(), e.stopImmediatePropagation();
}
function WR(e) {
  var t = e.document.documentElement,
    n = Ot(e).on("dragstart.drag", Zi, zs);
  "onselectstart" in t
    ? n.on("selectstart.drag", Zi, zs)
    : ((t.__noselect = t.style.MozUserSelect), (t.style.MozUserSelect = "none"));
}
function KR(e, t) {
  var n = e.document.documentElement,
    r = Ot(e).on("dragstart.drag", null);
  t &&
    (r.on("click.drag", Zi, zs),
    setTimeout(function () {
      r.on("click.drag", null);
    }, 0)),
    "onselectstart" in n
      ? r.on("selectstart.drag", null)
      : ((n.style.MozUserSelect = n.__noselect), delete n.__noselect);
}
const qa = (e) => () => e;
function wv(
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
  }
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
wv.prototype.on = function () {
  var e = this._.on.apply(this._, arguments);
  return e === this._ ? this : e;
};
function OV(e) {
  return !e.ctrlKey && !e.button;
}
function LV() {
  return this.parentNode;
}
function FV(e, t) {
  return t ?? { x: e.x, y: e.y };
}
function VV() {
  return navigator.maxTouchPoints || "ontouchstart" in this;
}
function jV() {
  var e = OV,
    t = LV,
    n = FV,
    r = VV,
    i = {},
    o = Vl("start", "drag", "end"),
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
      .on("touchmove.drag", m, DV)
      .on("touchend.drag touchcancel.drag", g)
      .style("touch-action", "none")
      .style("-webkit-tap-highlight-color", "rgba(0,0,0,0)");
  }
  function h(x, S) {
    if (!(c || !e.call(this, x, S))) {
      var C = w(this, t.call(this, x, S), x, S, "mouse");
      C &&
        (Ot(x.view).on("mousemove.drag", v, zs).on("mouseup.drag", p, zs),
        WR(x.view),
        Zc(x),
        (l = !1),
        (a = x.clientX),
        (u = x.clientY),
        C("start", x));
    }
  }
  function v(x) {
    if ((Zi(x), !l)) {
      var S = x.clientX - a,
        C = x.clientY - u;
      l = S * S + C * C > f;
    }
    i.mouse("drag", x);
  }
  function p(x) {
    Ot(x.view).on("mousemove.drag mouseup.drag", null), KR(x.view, l), Zi(x), i.mouse("end", x);
  }
  function y(x, S) {
    if (e.call(this, x, S)) {
      var C = x.changedTouches,
        E = t.call(this, x, S),
        T = C.length,
        P,
        N;
      for (P = 0; P < T; ++P)
        (N = w(this, E, x, S, C[P].identifier, C[P])) && (Zc(x), N("start", x, C[P]));
    }
  }
  function m(x) {
    var S = x.changedTouches,
      C = S.length,
      E,
      T;
    for (E = 0; E < C; ++E) (T = i[S[E].identifier]) && (Zi(x), T("drag", x, S[E]));
  }
  function g(x) {
    var S = x.changedTouches,
      C = S.length,
      E,
      T;
    for (
      c && clearTimeout(c),
        c = setTimeout(function () {
          c = null;
        }, 500),
        E = 0;
      E < C;
      ++E
    )
      (T = i[S[E].identifier]) && (Zc(x), T("end", x, S[E]));
  }
  function w(x, S, C, E, T, P) {
    var N = o.copy(),
      I = Yt(P || C, S),
      V,
      q,
      b;
    if (
      (b = n.call(
        x,
        new wv("beforestart", {
          sourceEvent: C,
          target: d,
          identifier: T,
          active: s,
          x: I[0],
          y: I[1],
          dx: 0,
          dy: 0,
          dispatch: N,
        }),
        E
      )) != null
    )
      return (
        (V = b.x - I[0] || 0),
        (q = b.y - I[1] || 0),
        function O(R, F, A) {
          var k = I,
            D;
          switch (R) {
            case "start":
              (i[T] = O), (D = s++);
              break;
            case "end":
              delete i[T], --s;
            case "drag":
              (I = Yt(A || F, S)), (D = s);
              break;
          }
          N.call(
            R,
            x,
            new wv(R, {
              sourceEvent: F,
              subject: b,
              target: d,
              identifier: T,
              active: D,
              x: I[0] + V,
              y: I[1] + q,
              dx: I[0] - k[0],
              dy: I[1] - k[1],
              dispatch: N,
            }),
            E
          );
        }
      );
  }
  return (
    (d.filter = function (x) {
      return arguments.length ? ((e = typeof x == "function" ? x : qa(!!x)), d) : e;
    }),
    (d.container = function (x) {
      return arguments.length ? ((t = typeof x == "function" ? x : qa(x)), d) : t;
    }),
    (d.subject = function (x) {
      return arguments.length ? ((n = typeof x == "function" ? x : qa(x)), d) : n;
    }),
    (d.touchable = function (x) {
      return arguments.length ? ((r = typeof x == "function" ? x : qa(!!x)), d) : r;
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
function t0(e, t, n) {
  (e.prototype = t.prototype = n), (n.constructor = e);
}
function YR(e, t) {
  var n = Object.create(e.prototype);
  for (var r in t) n[r] = t[r];
  return n;
}
function la() {}
var Bs = 0.7,
  el = 1 / Bs,
  Qi = "\\s*([+-]?\\d+)\\s*",
  Us = "\\s*([+-]?(?:\\d*\\.)?\\d+(?:[eE][+-]?\\d+)?)\\s*",
  vn = "\\s*([+-]?(?:\\d*\\.)?\\d+(?:[eE][+-]?\\d+)?)%\\s*",
  qV = /^#([0-9a-f]{3,8})$/,
  $V = new RegExp(`^rgb\\(${Qi},${Qi},${Qi}\\)$`),
  zV = new RegExp(`^rgb\\(${vn},${vn},${vn}\\)$`),
  BV = new RegExp(`^rgba\\(${Qi},${Qi},${Qi},${Us}\\)$`),
  UV = new RegExp(`^rgba\\(${vn},${vn},${vn},${Us}\\)$`),
  HV = new RegExp(`^hsl\\(${Us},${vn},${vn}\\)$`),
  GV = new RegExp(`^hsla\\(${Us},${vn},${vn},${Us}\\)$`),
  G1 = {
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
t0(la, Hs, {
  copy(e) {
    return Object.assign(new this.constructor(), this, e);
  },
  displayable() {
    return this.rgb().displayable();
  },
  hex: W1,
  formatHex: W1,
  formatHex8: WV,
  formatHsl: KV,
  formatRgb: K1,
  toString: K1,
});
function W1() {
  return this.rgb().formatHex();
}
function WV() {
  return this.rgb().formatHex8();
}
function KV() {
  return XR(this).formatHsl();
}
function K1() {
  return this.rgb().formatRgb();
}
function Hs(e) {
  var t, n;
  return (
    (e = (e + "").trim().toLowerCase()),
    (t = qV.exec(e))
      ? ((n = t[1].length),
        (t = parseInt(t[1], 16)),
        n === 6
          ? Y1(t)
          : n === 3
          ? new mt(
              ((t >> 8) & 15) | ((t >> 4) & 240),
              ((t >> 4) & 15) | (t & 240),
              ((t & 15) << 4) | (t & 15),
              1
            )
          : n === 8
          ? $a((t >> 24) & 255, (t >> 16) & 255, (t >> 8) & 255, (t & 255) / 255)
          : n === 4
          ? $a(
              ((t >> 12) & 15) | ((t >> 8) & 240),
              ((t >> 8) & 15) | ((t >> 4) & 240),
              ((t >> 4) & 15) | (t & 240),
              (((t & 15) << 4) | (t & 15)) / 255
            )
          : null)
      : (t = $V.exec(e))
      ? new mt(t[1], t[2], t[3], 1)
      : (t = zV.exec(e))
      ? new mt((t[1] * 255) / 100, (t[2] * 255) / 100, (t[3] * 255) / 100, 1)
      : (t = BV.exec(e))
      ? $a(t[1], t[2], t[3], t[4])
      : (t = UV.exec(e))
      ? $a((t[1] * 255) / 100, (t[2] * 255) / 100, (t[3] * 255) / 100, t[4])
      : (t = HV.exec(e))
      ? Q1(t[1], t[2] / 100, t[3] / 100, 1)
      : (t = GV.exec(e))
      ? Q1(t[1], t[2] / 100, t[3] / 100, t[4])
      : G1.hasOwnProperty(e)
      ? Y1(G1[e])
      : e === "transparent"
      ? new mt(NaN, NaN, NaN, 0)
      : null
  );
}
function Y1(e) {
  return new mt((e >> 16) & 255, (e >> 8) & 255, e & 255, 1);
}
function $a(e, t, n, r) {
  return r <= 0 && (e = t = n = NaN), new mt(e, t, n, r);
}
function YV(e) {
  return (
    e instanceof la || (e = Hs(e)), e ? ((e = e.rgb()), new mt(e.r, e.g, e.b, e.opacity)) : new mt()
  );
}
function xv(e, t, n, r) {
  return arguments.length === 1 ? YV(e) : new mt(e, t, n, r ?? 1);
}
function mt(e, t, n, r) {
  (this.r = +e), (this.g = +t), (this.b = +n), (this.opacity = +r);
}
t0(
  mt,
  xv,
  YR(la, {
    brighter(e) {
      return (
        (e = e == null ? el : Math.pow(el, e)),
        new mt(this.r * e, this.g * e, this.b * e, this.opacity)
      );
    },
    darker(e) {
      return (
        (e = e == null ? Bs : Math.pow(Bs, e)),
        new mt(this.r * e, this.g * e, this.b * e, this.opacity)
      );
    },
    rgb() {
      return this;
    },
    clamp() {
      return new mt(Jr(this.r), Jr(this.g), Jr(this.b), tl(this.opacity));
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
    hex: X1,
    formatHex: X1,
    formatHex8: XV,
    formatRgb: Z1,
    toString: Z1,
  })
);
function X1() {
  return `#${Wr(this.r)}${Wr(this.g)}${Wr(this.b)}`;
}
function XV() {
  return `#${Wr(this.r)}${Wr(this.g)}${Wr(this.b)}${Wr(
    (isNaN(this.opacity) ? 1 : this.opacity) * 255
  )}`;
}
function Z1() {
  const e = tl(this.opacity);
  return `${e === 1 ? "rgb(" : "rgba("}${Jr(this.r)}, ${Jr(this.g)}, ${Jr(this.b)}${
    e === 1 ? ")" : `, ${e})`
  }`;
}
function tl(e) {
  return isNaN(e) ? 1 : Math.max(0, Math.min(1, e));
}
function Jr(e) {
  return Math.max(0, Math.min(255, Math.round(e) || 0));
}
function Wr(e) {
  return (e = Jr(e)), (e < 16 ? "0" : "") + e.toString(16);
}
function Q1(e, t, n, r) {
  return (
    r <= 0 ? (e = t = n = NaN) : n <= 0 || n >= 1 ? (e = t = NaN) : t <= 0 && (e = NaN),
    new Zt(e, t, n, r)
  );
}
function XR(e) {
  if (e instanceof Zt) return new Zt(e.h, e.s, e.l, e.opacity);
  if ((e instanceof la || (e = Hs(e)), !e)) return new Zt();
  if (e instanceof Zt) return e;
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
    new Zt(s, a, u, e.opacity)
  );
}
function ZV(e, t, n, r) {
  return arguments.length === 1 ? XR(e) : new Zt(e, t, n, r ?? 1);
}
function Zt(e, t, n, r) {
  (this.h = +e), (this.s = +t), (this.l = +n), (this.opacity = +r);
}
t0(
  Zt,
  ZV,
  YR(la, {
    brighter(e) {
      return (
        (e = e == null ? el : Math.pow(el, e)), new Zt(this.h, this.s, this.l * e, this.opacity)
      );
    },
    darker(e) {
      return (
        (e = e == null ? Bs : Math.pow(Bs, e)), new Zt(this.h, this.s, this.l * e, this.opacity)
      );
    },
    rgb() {
      var e = (this.h % 360) + (this.h < 0) * 360,
        t = isNaN(e) || isNaN(this.s) ? 0 : this.s,
        n = this.l,
        r = n + (n < 0.5 ? n : 1 - n) * t,
        i = 2 * n - r;
      return new mt(
        Qc(e >= 240 ? e - 240 : e + 120, i, r),
        Qc(e, i, r),
        Qc(e < 120 ? e + 240 : e - 120, i, r),
        this.opacity
      );
    },
    clamp() {
      return new Zt(J1(this.h), za(this.s), za(this.l), tl(this.opacity));
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
      const e = tl(this.opacity);
      return `${e === 1 ? "hsl(" : "hsla("}${J1(this.h)}, ${za(this.s) * 100}%, ${
        za(this.l) * 100
      }%${e === 1 ? ")" : `, ${e})`}`;
    },
  })
);
function J1(e) {
  return (e = (e || 0) % 360), e < 0 ? e + 360 : e;
}
function za(e) {
  return Math.max(0, Math.min(1, e || 0));
}
function Qc(e, t, n) {
  return (
    (e < 60 ? t + ((n - t) * e) / 60 : e < 180 ? n : e < 240 ? t + ((n - t) * (240 - e)) / 60 : t) *
    255
  );
}
const ZR = (e) => () => e;
function QV(e, t) {
  return function (n) {
    return e + n * t;
  };
}
function JV(e, t, n) {
  return (
    (e = Math.pow(e, n)),
    (t = Math.pow(t, n) - e),
    (n = 1 / n),
    function (r) {
      return Math.pow(e + r * t, n);
    }
  );
}
function ej(e) {
  return (e = +e) == 1
    ? QR
    : function (t, n) {
        return n - t ? JV(t, n, e) : ZR(isNaN(t) ? n : t);
      };
}
function QR(e, t) {
  var n = t - e;
  return n ? QV(e, n) : ZR(isNaN(e) ? t : e);
}
const ex = (function e(t) {
  var n = ej(t);
  function r(i, o) {
    var s = n((i = xv(i)).r, (o = xv(o)).r),
      a = n(i.g, o.g),
      u = n(i.b, o.b),
      l = QR(i.opacity, o.opacity);
    return function (c) {
      return (i.r = s(c)), (i.g = a(c)), (i.b = u(c)), (i.opacity = l(c)), i + "";
    };
  }
  return (r.gamma = e), r;
})(1);
function lr(e, t) {
  return (
    (e = +e),
    (t = +t),
    function (n) {
      return e * (1 - n) + t * n;
    }
  );
}
var _v = /[-+]?(?:\d+\.?\d*|\.?\d+)(?:[eE][-+]?\d+)?/g,
  Jc = new RegExp(_v.source, "g");
function tj(e) {
  return function () {
    return e;
  };
}
function nj(e) {
  return function (t) {
    return e(t) + "";
  };
}
function rj(e, t) {
  var n = (_v.lastIndex = Jc.lastIndex = 0),
    r,
    i,
    o,
    s = -1,
    a = [],
    u = [];
  for (e = e + "", t = t + ""; (r = _v.exec(e)) && (i = Jc.exec(t)); )
    (o = i.index) > n && ((o = t.slice(n, o)), a[s] ? (a[s] += o) : (a[++s] = o)),
      (r = r[0]) === (i = i[0])
        ? a[s]
          ? (a[s] += i)
          : (a[++s] = i)
        : ((a[++s] = null), u.push({ i: s, x: lr(r, i) })),
      (n = Jc.lastIndex);
  return (
    n < t.length && ((o = t.slice(n)), a[s] ? (a[s] += o) : (a[++s] = o)),
    a.length < 2
      ? u[0]
        ? nj(u[0].x)
        : tj(t)
      : ((t = u.length),
        function (l) {
          for (var c = 0, f; c < t; ++c) a[(f = u[c]).i] = f.x(l);
          return a.join("");
        })
  );
}
var tx = 180 / Math.PI,
  Sv = { translateX: 0, translateY: 0, rotate: 0, skewX: 0, scaleX: 1, scaleY: 1 };
function JR(e, t, n, r, i, o) {
  var s, a, u;
  return (
    (s = Math.sqrt(e * e + t * t)) && ((e /= s), (t /= s)),
    (u = e * n + t * r) && ((n -= e * u), (r -= t * u)),
    (a = Math.sqrt(n * n + r * r)) && ((n /= a), (r /= a), (u /= a)),
    e * r < t * n && ((e = -e), (t = -t), (u = -u), (s = -s)),
    {
      translateX: i,
      translateY: o,
      rotate: Math.atan2(t, e) * tx,
      skewX: Math.atan(u) * tx,
      scaleX: s,
      scaleY: a,
    }
  );
}
var Ba;
function ij(e) {
  const t = new (typeof DOMMatrix == "function" ? DOMMatrix : WebKitCSSMatrix)(e + "");
  return t.isIdentity ? Sv : JR(t.a, t.b, t.c, t.d, t.e, t.f);
}
function oj(e) {
  return e == null ||
    (Ba || (Ba = document.createElementNS("http://www.w3.org/2000/svg", "g")),
    Ba.setAttribute("transform", e),
    !(e = Ba.transform.baseVal.consolidate()))
    ? Sv
    : ((e = e.matrix), JR(e.a, e.b, e.c, e.d, e.e, e.f));
}
function eA(e, t, n, r) {
  function i(l) {
    return l.length ? l.pop() + " " : "";
  }
  function o(l, c, f, d, h, v) {
    if (l !== f || c !== d) {
      var p = h.push("translate(", null, t, null, n);
      v.push({ i: p - 4, x: lr(l, f) }, { i: p - 2, x: lr(c, d) });
    } else (f || d) && h.push("translate(" + f + t + d + n);
  }
  function s(l, c, f, d) {
    l !== c
      ? (l - c > 180 ? (c += 360) : c - l > 180 && (l += 360),
        d.push({ i: f.push(i(f) + "rotate(", null, r) - 2, x: lr(l, c) }))
      : c && f.push(i(f) + "rotate(" + c + r);
  }
  function a(l, c, f, d) {
    l !== c
      ? d.push({ i: f.push(i(f) + "skewX(", null, r) - 2, x: lr(l, c) })
      : c && f.push(i(f) + "skewX(" + c + r);
  }
  function u(l, c, f, d, h, v) {
    if (l !== f || c !== d) {
      var p = h.push(i(h) + "scale(", null, ",", null, ")");
      v.push({ i: p - 4, x: lr(l, f) }, { i: p - 2, x: lr(c, d) });
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
var sj = eA(ij, "px, ", "px)", "deg)"),
  aj = eA(oj, ", ", ")", ")"),
  uj = 1e-12;
function nx(e) {
  return ((e = Math.exp(e)) + 1 / e) / 2;
}
function lj(e) {
  return ((e = Math.exp(e)) - 1 / e) / 2;
}
function cj(e) {
  return ((e = Math.exp(2 * e)) - 1) / (e + 1);
}
const fj = (function e(t, n, r) {
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
    if (p < uj)
      (m = Math.log(d / l) / t),
        (y = function (E) {
          return [a + E * h, u + E * v, l * Math.exp(t * E * m)];
        });
    else {
      var g = Math.sqrt(p),
        w = (d * d - l * l + r * p) / (2 * l * n * g),
        x = (d * d - l * l - r * p) / (2 * d * n * g),
        S = Math.log(Math.sqrt(w * w + 1) - w),
        C = Math.log(Math.sqrt(x * x + 1) - x);
      (m = (C - S) / t),
        (y = function (E) {
          var T = E * m,
            P = nx(S),
            N = (l / (n * g)) * (P * cj(t * T + S) - lj(S));
          return [a + N * h, u + N * v, (l * P) / nx(t * T + S)];
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
var fo = 0,
  Qo = 0,
  qo = 0,
  tA = 1e3,
  nl,
  Jo,
  rl = 0,
  ai = 0,
  ql = 0,
  Gs = typeof performance == "object" && performance.now ? performance : Date,
  nA =
    typeof window == "object" && window.requestAnimationFrame
      ? window.requestAnimationFrame.bind(window)
      : function (e) {
          setTimeout(e, 17);
        };
function n0() {
  return ai || (nA(dj), (ai = Gs.now() + ql));
}
function dj() {
  ai = 0;
}
function il() {
  this._call = this._time = this._next = null;
}
il.prototype = rA.prototype = {
  constructor: il,
  restart: function (e, t, n) {
    if (typeof e != "function") throw new TypeError("callback is not a function");
    (n = (n == null ? n0() : +n) + (t == null ? 0 : +t)),
      !this._next && Jo !== this && (Jo ? (Jo._next = this) : (nl = this), (Jo = this)),
      (this._call = e),
      (this._time = n),
      bv();
  },
  stop: function () {
    this._call && ((this._call = null), (this._time = 1 / 0), bv());
  },
};
function rA(e, t, n) {
  var r = new il();
  return r.restart(e, t, n), r;
}
function hj() {
  n0(), ++fo;
  for (var e = nl, t; e; ) (t = ai - e._time) >= 0 && e._call.call(void 0, t), (e = e._next);
  --fo;
}
function rx() {
  (ai = (rl = Gs.now()) + ql), (fo = Qo = 0);
  try {
    hj();
  } finally {
    (fo = 0), mj(), (ai = 0);
  }
}
function pj() {
  var e = Gs.now(),
    t = e - rl;
  t > tA && ((ql -= t), (rl = e));
}
function mj() {
  for (var e, t = nl, n, r = 1 / 0; t; )
    t._call
      ? (r > t._time && (r = t._time), (e = t), (t = t._next))
      : ((n = t._next), (t._next = null), (t = e ? (e._next = n) : (nl = n)));
  (Jo = e), bv(r);
}
function bv(e) {
  if (!fo) {
    Qo && (Qo = clearTimeout(Qo));
    var t = e - ai;
    t > 24
      ? (e < 1 / 0 && (Qo = setTimeout(rx, e - Gs.now() - ql)), qo && (qo = clearInterval(qo)))
      : (qo || ((rl = Gs.now()), (qo = setInterval(pj, tA))), (fo = 1), nA(rx));
  }
}
function ix(e, t, n) {
  var r = new il();
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
var gj = Vl("start", "end", "cancel", "interrupt"),
  vj = [],
  iA = 0,
  ox = 1,
  Ev = 2,
  yu = 3,
  sx = 4,
  Cv = 5,
  wu = 6;
function $l(e, t, n, r, i, o) {
  var s = e.__transition;
  if (!s) e.__transition = {};
  else if (n in s) return;
  yj(e, n, {
    name: t,
    index: r,
    group: i,
    on: gj,
    tween: vj,
    time: o.time,
    delay: o.delay,
    duration: o.duration,
    ease: o.ease,
    timer: null,
    state: iA,
  });
}
function r0(e, t) {
  var n = nn(e, t);
  if (n.state > iA) throw new Error("too late; already scheduled");
  return n;
}
function _n(e, t) {
  var n = nn(e, t);
  if (n.state > yu) throw new Error("too late; already running");
  return n;
}
function nn(e, t) {
  var n = e.__transition;
  if (!n || !(n = n[t])) throw new Error("transition not found");
  return n;
}
function yj(e, t, n) {
  var r = e.__transition,
    i;
  (r[t] = n), (n.timer = rA(o, 0, n.time));
  function o(l) {
    (n.state = ox), n.timer.restart(s, n.delay, n.time), n.delay <= l && s(l - n.delay);
  }
  function s(l) {
    var c, f, d, h;
    if (n.state !== ox) return u();
    for (c in r)
      if (((h = r[c]), h.name === n.name)) {
        if (h.state === yu) return ix(s);
        h.state === sx
          ? ((h.state = wu),
            h.timer.stop(),
            h.on.call("interrupt", e, e.__data__, h.index, h.group),
            delete r[c])
          : +c < t &&
            ((h.state = wu),
            h.timer.stop(),
            h.on.call("cancel", e, e.__data__, h.index, h.group),
            delete r[c]);
      }
    if (
      (ix(function () {
        n.state === yu && ((n.state = sx), n.timer.restart(a, n.delay, n.time), a(l));
      }),
      (n.state = Ev),
      n.on.call("start", e, e.__data__, n.index, n.group),
      n.state === Ev)
    ) {
      for (n.state = yu, i = new Array((d = n.tween.length)), c = 0, f = -1; c < d; ++c)
        (h = n.tween[c].value.call(e, e.__data__, n.index, n.group)) && (i[++f] = h);
      i.length = f + 1;
    }
  }
  function a(l) {
    for (
      var c =
          l < n.duration
            ? n.ease.call(null, l / n.duration)
            : (n.timer.restart(u), (n.state = Cv), 1),
        f = -1,
        d = i.length;
      ++f < d;

    )
      i[f].call(e, c);
    n.state === Cv && (n.on.call("end", e, e.__data__, n.index, n.group), u());
  }
  function u() {
    (n.state = wu), n.timer.stop(), delete r[t];
    for (var l in r) return;
    delete e.__transition;
  }
}
function xu(e, t) {
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
      (i = r.state > Ev && r.state < Cv),
        (r.state = wu),
        r.timer.stop(),
        r.on.call(i ? "interrupt" : "cancel", e, e.__data__, r.index, r.group),
        delete n[s];
    }
    o && delete e.__transition;
  }
}
function wj(e) {
  return this.each(function () {
    xu(this, e);
  });
}
function xj(e, t) {
  var n, r;
  return function () {
    var i = _n(this, e),
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
function _j(e, t, n) {
  var r, i;
  if (typeof n != "function") throw new Error();
  return function () {
    var o = _n(this, e),
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
function Sj(e, t) {
  var n = this._id;
  if (((e += ""), arguments.length < 2)) {
    for (var r = nn(this.node(), n).tween, i = 0, o = r.length, s; i < o; ++i)
      if ((s = r[i]).name === e) return s.value;
    return null;
  }
  return this.each((t == null ? xj : _j)(n, e, t));
}
function i0(e, t, n) {
  var r = e._id;
  return (
    e.each(function () {
      var i = _n(this, r);
      (i.value || (i.value = {}))[t] = n.apply(this, arguments);
    }),
    function (i) {
      return nn(i, r).value[t];
    }
  );
}
function oA(e, t) {
  var n;
  return (typeof t == "number" ? lr : t instanceof Hs ? ex : (n = Hs(t)) ? ((t = n), ex) : rj)(
    e,
    t
  );
}
function bj(e) {
  return function () {
    this.removeAttribute(e);
  };
}
function Ej(e) {
  return function () {
    this.removeAttributeNS(e.space, e.local);
  };
}
function Cj(e, t, n) {
  var r,
    i = n + "",
    o;
  return function () {
    var s = this.getAttribute(e);
    return s === i ? null : s === r ? o : (o = t((r = s), n));
  };
}
function Tj(e, t, n) {
  var r,
    i = n + "",
    o;
  return function () {
    var s = this.getAttributeNS(e.space, e.local);
    return s === i ? null : s === r ? o : (o = t((r = s), n));
  };
}
function kj(e, t, n) {
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
function Pj(e, t, n) {
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
function Rj(e, t) {
  var n = jl(e),
    r = n === "transform" ? aj : oA;
  return this.attrTween(
    e,
    typeof t == "function"
      ? (n.local ? Pj : kj)(n, r, i0(this, "attr." + e, t))
      : t == null
      ? (n.local ? Ej : bj)(n)
      : (n.local ? Tj : Cj)(n, r, t)
  );
}
function Aj(e, t) {
  return function (n) {
    this.setAttribute(e, t.call(this, n));
  };
}
function Nj(e, t) {
  return function (n) {
    this.setAttributeNS(e.space, e.local, t.call(this, n));
  };
}
function Mj(e, t) {
  var n, r;
  function i() {
    var o = t.apply(this, arguments);
    return o !== r && (n = (r = o) && Nj(e, o)), n;
  }
  return (i._value = t), i;
}
function Ij(e, t) {
  var n, r;
  function i() {
    var o = t.apply(this, arguments);
    return o !== r && (n = (r = o) && Aj(e, o)), n;
  }
  return (i._value = t), i;
}
function Dj(e, t) {
  var n = "attr." + e;
  if (arguments.length < 2) return (n = this.tween(n)) && n._value;
  if (t == null) return this.tween(n, null);
  if (typeof t != "function") throw new Error();
  var r = jl(e);
  return this.tween(n, (r.local ? Mj : Ij)(r, t));
}
function Oj(e, t) {
  return function () {
    r0(this, e).delay = +t.apply(this, arguments);
  };
}
function Lj(e, t) {
  return (
    (t = +t),
    function () {
      r0(this, e).delay = t;
    }
  );
}
function Fj(e) {
  var t = this._id;
  return arguments.length
    ? this.each((typeof e == "function" ? Oj : Lj)(t, e))
    : nn(this.node(), t).delay;
}
function Vj(e, t) {
  return function () {
    _n(this, e).duration = +t.apply(this, arguments);
  };
}
function jj(e, t) {
  return (
    (t = +t),
    function () {
      _n(this, e).duration = t;
    }
  );
}
function qj(e) {
  var t = this._id;
  return arguments.length
    ? this.each((typeof e == "function" ? Vj : jj)(t, e))
    : nn(this.node(), t).duration;
}
function $j(e, t) {
  if (typeof t != "function") throw new Error();
  return function () {
    _n(this, e).ease = t;
  };
}
function zj(e) {
  var t = this._id;
  return arguments.length ? this.each($j(t, e)) : nn(this.node(), t).ease;
}
function Bj(e, t) {
  return function () {
    var n = t.apply(this, arguments);
    if (typeof n != "function") throw new Error();
    _n(this, e).ease = n;
  };
}
function Uj(e) {
  if (typeof e != "function") throw new Error();
  return this.each(Bj(this._id, e));
}
function Hj(e) {
  typeof e != "function" && (e = FR(e));
  for (var t = this._groups, n = t.length, r = new Array(n), i = 0; i < n; ++i)
    for (var o = t[i], s = o.length, a = (r[i] = []), u, l = 0; l < s; ++l)
      (u = o[l]) && e.call(u, u.__data__, l, o) && a.push(u);
  return new Hn(r, this._parents, this._name, this._id);
}
function Gj(e) {
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
  return new Hn(s, this._parents, this._name, this._id);
}
function Wj(e) {
  return (e + "")
    .trim()
    .split(/^|\s+/)
    .every(function (t) {
      var n = t.indexOf(".");
      return n >= 0 && (t = t.slice(0, n)), !t || t === "start";
    });
}
function Kj(e, t, n) {
  var r,
    i,
    o = Wj(t) ? r0 : _n;
  return function () {
    var s = o(this, e),
      a = s.on;
    a !== r && (i = (r = a).copy()).on(t, n), (s.on = i);
  };
}
function Yj(e, t) {
  var n = this._id;
  return arguments.length < 2 ? nn(this.node(), n).on.on(e) : this.each(Kj(n, e, t));
}
function Xj(e) {
  return function () {
    var t = this.parentNode;
    for (var n in this.__transition) if (+n !== e) return;
    t && t.removeChild(this);
  };
}
function Zj() {
  return this.on("end.remove", Xj(this._id));
}
function Qj(e) {
  var t = this._name,
    n = this._id;
  typeof e != "function" && (e = Jy(e));
  for (var r = this._groups, i = r.length, o = new Array(i), s = 0; s < i; ++s)
    for (var a = r[s], u = a.length, l = (o[s] = new Array(u)), c, f, d = 0; d < u; ++d)
      (c = a[d]) &&
        (f = e.call(c, c.__data__, d, a)) &&
        ("__data__" in c && (f.__data__ = c.__data__), (l[d] = f), $l(l[d], t, n, d, l, nn(c, n)));
  return new Hn(o, this._parents, t, n);
}
function Jj(e) {
  var t = this._name,
    n = this._id;
  typeof e != "function" && (e = LR(e));
  for (var r = this._groups, i = r.length, o = [], s = [], a = 0; a < i; ++a)
    for (var u = r[a], l = u.length, c, f = 0; f < l; ++f)
      if ((c = u[f])) {
        for (var d = e.call(c, c.__data__, f, u), h, v = nn(c, n), p = 0, y = d.length; p < y; ++p)
          (h = d[p]) && $l(h, t, n, p, d, v);
        o.push(d), s.push(c);
      }
  return new Hn(o, s, t, n);
}
var eq = ua.prototype.constructor;
function tq() {
  return new eq(this._groups, this._parents);
}
function nq(e, t) {
  var n, r, i;
  return function () {
    var o = co(this, e),
      s = (this.style.removeProperty(e), co(this, e));
    return o === s ? null : o === n && s === r ? i : (i = t((n = o), (r = s)));
  };
}
function sA(e) {
  return function () {
    this.style.removeProperty(e);
  };
}
function rq(e, t, n) {
  var r,
    i = n + "",
    o;
  return function () {
    var s = co(this, e);
    return s === i ? null : s === r ? o : (o = t((r = s), n));
  };
}
function iq(e, t, n) {
  var r, i, o;
  return function () {
    var s = co(this, e),
      a = n(this),
      u = a + "";
    return (
      a == null && (u = a = (this.style.removeProperty(e), co(this, e))),
      s === u ? null : s === r && u === i ? o : ((i = u), (o = t((r = s), a)))
    );
  };
}
function oq(e, t) {
  var n,
    r,
    i,
    o = "style." + t,
    s = "end." + o,
    a;
  return function () {
    var u = _n(this, e),
      l = u.on,
      c = u.value[o] == null ? a || (a = sA(t)) : void 0;
    (l !== n || i !== c) && (r = (n = l).copy()).on(s, (i = c)), (u.on = r);
  };
}
function sq(e, t, n) {
  var r = (e += "") == "transform" ? sj : oA;
  return t == null
    ? this.styleTween(e, nq(e, r)).on("end.style." + e, sA(e))
    : typeof t == "function"
    ? this.styleTween(e, iq(e, r, i0(this, "style." + e, t))).each(oq(this._id, e))
    : this.styleTween(e, rq(e, r, t), n).on("end.style." + e, null);
}
function aq(e, t, n) {
  return function (r) {
    this.style.setProperty(e, t.call(this, r), n);
  };
}
function uq(e, t, n) {
  var r, i;
  function o() {
    var s = t.apply(this, arguments);
    return s !== i && (r = (i = s) && aq(e, s, n)), r;
  }
  return (o._value = t), o;
}
function lq(e, t, n) {
  var r = "style." + (e += "");
  if (arguments.length < 2) return (r = this.tween(r)) && r._value;
  if (t == null) return this.tween(r, null);
  if (typeof t != "function") throw new Error();
  return this.tween(r, uq(e, t, n ?? ""));
}
function cq(e) {
  return function () {
    this.textContent = e;
  };
}
function fq(e) {
  return function () {
    var t = e(this);
    this.textContent = t ?? "";
  };
}
function dq(e) {
  return this.tween(
    "text",
    typeof e == "function" ? fq(i0(this, "text", e)) : cq(e == null ? "" : e + "")
  );
}
function hq(e) {
  return function (t) {
    this.textContent = e.call(this, t);
  };
}
function pq(e) {
  var t, n;
  function r() {
    var i = e.apply(this, arguments);
    return i !== n && (t = (n = i) && hq(i)), t;
  }
  return (r._value = e), r;
}
function mq(e) {
  var t = "text";
  if (arguments.length < 1) return (t = this.tween(t)) && t._value;
  if (e == null) return this.tween(t, null);
  if (typeof e != "function") throw new Error();
  return this.tween(t, pq(e));
}
function gq() {
  for (
    var e = this._name, t = this._id, n = aA(), r = this._groups, i = r.length, o = 0;
    o < i;
    ++o
  )
    for (var s = r[o], a = s.length, u, l = 0; l < a; ++l)
      if ((u = s[l])) {
        var c = nn(u, t);
        $l(u, e, n, l, s, {
          time: c.time + c.delay + c.duration,
          delay: 0,
          duration: c.duration,
          ease: c.ease,
        });
      }
  return new Hn(r, this._parents, e, n);
}
function vq() {
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
      var l = _n(this, r),
        c = l.on;
      c !== e && ((t = (e = c).copy()), t._.cancel.push(a), t._.interrupt.push(a), t._.end.push(u)),
        (l.on = t);
    }),
      i === 0 && o();
  });
}
var yq = 0;
function Hn(e, t, n, r) {
  (this._groups = e), (this._parents = t), (this._name = n), (this._id = r);
}
function aA() {
  return ++yq;
}
var kn = ua.prototype;
Hn.prototype = {
  constructor: Hn,
  select: Qj,
  selectAll: Jj,
  selectChild: kn.selectChild,
  selectChildren: kn.selectChildren,
  filter: Hj,
  merge: Gj,
  selection: tq,
  transition: gq,
  call: kn.call,
  nodes: kn.nodes,
  node: kn.node,
  size: kn.size,
  empty: kn.empty,
  each: kn.each,
  on: Yj,
  attr: Rj,
  attrTween: Dj,
  style: sq,
  styleTween: lq,
  text: dq,
  textTween: mq,
  remove: Zj,
  tween: Sj,
  delay: Fj,
  duration: qj,
  ease: zj,
  easeVarying: Uj,
  end: vq,
  [Symbol.iterator]: kn[Symbol.iterator],
};
function wq(e) {
  return ((e *= 2) <= 1 ? e * e * e : (e -= 2) * e * e + 2) / 2;
}
var xq = { time: null, delay: 0, duration: 250, ease: wq };
function _q(e, t) {
  for (var n; !(n = e.__transition) || !(n = n[t]); )
    if (!(e = e.parentNode)) throw new Error(`transition ${t} not found`);
  return n;
}
function Sq(e) {
  var t, n;
  e instanceof Hn
    ? ((t = e._id), (e = e._name))
    : ((t = aA()), ((n = xq).time = n0()), (e = e == null ? null : e + ""));
  for (var r = this._groups, i = r.length, o = 0; o < i; ++o)
    for (var s = r[o], a = s.length, u, l = 0; l < a; ++l)
      (u = s[l]) && $l(u, e, t, l, s, n || _q(u, t));
  return new Hn(r, this._parents, e, t);
}
ua.prototype.interrupt = wj;
ua.prototype.transition = Sq;
const Ua = (e) => () => e;
function bq(e, { sourceEvent: t, target: n, transform: r, dispatch: i }) {
  Object.defineProperties(this, {
    type: { value: e, enumerable: !0, configurable: !0 },
    sourceEvent: { value: t, enumerable: !0, configurable: !0 },
    target: { value: n, enumerable: !0, configurable: !0 },
    transform: { value: r, enumerable: !0, configurable: !0 },
    _: { value: i },
  });
}
function Dn(e, t, n) {
  (this.k = e), (this.x = t), (this.y = n);
}
Dn.prototype = {
  constructor: Dn,
  scale: function (e) {
    return e === 1 ? this : new Dn(this.k * e, this.x, this.y);
  },
  translate: function (e, t) {
    return (e === 0) & (t === 0) ? this : new Dn(this.k, this.x + this.k * e, this.y + this.k * t);
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
var Vn = new Dn(1, 0, 0);
Dn.prototype;
function ef(e) {
  e.stopImmediatePropagation();
}
function $o(e) {
  e.preventDefault(), e.stopImmediatePropagation();
}
function Eq(e) {
  return (!e.ctrlKey || e.type === "wheel") && !e.button;
}
function Cq() {
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
function ax() {
  return this.__zoom || Vn;
}
function Tq(e) {
  return -e.deltaY * (e.deltaMode === 1 ? 0.05 : e.deltaMode ? 1 : 0.002) * (e.ctrlKey ? 10 : 1);
}
function kq() {
  return navigator.maxTouchPoints || "ontouchstart" in this;
}
function Pq(e, t, n) {
  var r = e.invertX(t[0][0]) - n[0][0],
    i = e.invertX(t[1][0]) - n[1][0],
    o = e.invertY(t[0][1]) - n[0][1],
    s = e.invertY(t[1][1]) - n[1][1];
  return e.translate(
    i > r ? (r + i) / 2 : Math.min(0, r) || Math.max(0, i),
    s > o ? (o + s) / 2 : Math.min(0, o) || Math.max(0, s)
  );
}
function uA() {
  var e = Eq,
    t = Cq,
    n = Pq,
    r = Tq,
    i = kq,
    o = [0, 1 / 0],
    s = [
      [-1 / 0, -1 / 0],
      [1 / 0, 1 / 0],
    ],
    a = 250,
    u = fj,
    l = Vl("start", "zoom", "end"),
    c,
    f,
    d,
    h = 500,
    v = 150,
    p = 0,
    y = 10;
  function m(b) {
    b.property("__zoom", ax)
      .on("wheel.zoom", T, { passive: !1 })
      .on("mousedown.zoom", P)
      .on("dblclick.zoom", N)
      .filter(i)
      .on("touchstart.zoom", I)
      .on("touchmove.zoom", V)
      .on("touchend.zoom touchcancel.zoom", q)
      .style("-webkit-tap-highlight-color", "rgba(0,0,0,0)");
  }
  (m.transform = function (b, O, R, F) {
    var A = b.selection ? b.selection() : b;
    A.property("__zoom", ax),
      b !== A
        ? S(b, O, R, F)
        : A.interrupt().each(function () {
            C(this, arguments)
              .event(F)
              .start()
              .zoom(null, typeof O == "function" ? O.apply(this, arguments) : O)
              .end();
          });
  }),
    (m.scaleBy = function (b, O, R, F) {
      m.scaleTo(
        b,
        function () {
          var A = this.__zoom.k,
            k = typeof O == "function" ? O.apply(this, arguments) : O;
          return A * k;
        },
        R,
        F
      );
    }),
    (m.scaleTo = function (b, O, R, F) {
      m.transform(
        b,
        function () {
          var A = t.apply(this, arguments),
            k = this.__zoom,
            D = R == null ? x(A) : typeof R == "function" ? R.apply(this, arguments) : R,
            j = k.invert(D),
            $ = typeof O == "function" ? O.apply(this, arguments) : O;
          return n(w(g(k, $), D, j), A, s);
        },
        R,
        F
      );
    }),
    (m.translateBy = function (b, O, R, F) {
      m.transform(
        b,
        function () {
          return n(
            this.__zoom.translate(
              typeof O == "function" ? O.apply(this, arguments) : O,
              typeof R == "function" ? R.apply(this, arguments) : R
            ),
            t.apply(this, arguments),
            s
          );
        },
        null,
        F
      );
    }),
    (m.translateTo = function (b, O, R, F, A) {
      m.transform(
        b,
        function () {
          var k = t.apply(this, arguments),
            D = this.__zoom,
            j = F == null ? x(k) : typeof F == "function" ? F.apply(this, arguments) : F;
          return n(
            Vn.translate(j[0], j[1])
              .scale(D.k)
              .translate(
                typeof O == "function" ? -O.apply(this, arguments) : -O,
                typeof R == "function" ? -R.apply(this, arguments) : -R
              ),
            k,
            s
          );
        },
        F,
        A
      );
    });
  function g(b, O) {
    return (O = Math.max(o[0], Math.min(o[1], O))), O === b.k ? b : new Dn(O, b.x, b.y);
  }
  function w(b, O, R) {
    var F = O[0] - R[0] * b.k,
      A = O[1] - R[1] * b.k;
    return F === b.x && A === b.y ? b : new Dn(b.k, F, A);
  }
  function x(b) {
    return [(+b[0][0] + +b[1][0]) / 2, (+b[0][1] + +b[1][1]) / 2];
  }
  function S(b, O, R, F) {
    b.on("start.zoom", function () {
      C(this, arguments).event(F).start();
    })
      .on("interrupt.zoom end.zoom", function () {
        C(this, arguments).event(F).end();
      })
      .tween("zoom", function () {
        var A = this,
          k = arguments,
          D = C(A, k).event(F),
          j = t.apply(A, k),
          $ = R == null ? x(j) : typeof R == "function" ? R.apply(A, k) : R,
          U = Math.max(j[1][0] - j[0][0], j[1][1] - j[0][1]),
          B = A.__zoom,
          W = typeof O == "function" ? O.apply(A, k) : O,
          X = u(B.invert($).concat(U / B.k), W.invert($).concat(U / W.k));
        return function (ee) {
          if (ee === 1) ee = W;
          else {
            var ue = X(ee),
              se = U / ue[2];
            ee = new Dn(se, $[0] - ue[0] * se, $[1] - ue[1] * se);
          }
          D.zoom(null, ee);
        };
      });
  }
  function C(b, O, R) {
    return (!R && b.__zooming) || new E(b, O);
  }
  function E(b, O) {
    (this.that = b),
      (this.args = O),
      (this.active = 0),
      (this.sourceEvent = null),
      (this.extent = t.apply(b, O)),
      (this.taps = 0);
  }
  E.prototype = {
    event: function (b) {
      return b && (this.sourceEvent = b), this;
    },
    start: function () {
      return ++this.active === 1 && ((this.that.__zooming = this), this.emit("start")), this;
    },
    zoom: function (b, O) {
      return (
        this.mouse && b !== "mouse" && (this.mouse[1] = O.invert(this.mouse[0])),
        this.touch0 && b !== "touch" && (this.touch0[1] = O.invert(this.touch0[0])),
        this.touch1 && b !== "touch" && (this.touch1[1] = O.invert(this.touch1[0])),
        (this.that.__zoom = O),
        this.emit("zoom"),
        this
      );
    },
    end: function () {
      return --this.active === 0 && (delete this.that.__zooming, this.emit("end")), this;
    },
    emit: function (b) {
      var O = Ot(this.that).datum();
      l.call(
        b,
        this.that,
        new bq(b, {
          sourceEvent: this.sourceEvent,
          target: m,
          transform: this.that.__zoom,
          dispatch: l,
        }),
        O
      );
    },
  };
  function T(b, ...O) {
    if (!e.apply(this, arguments)) return;
    var R = C(this, O).event(b),
      F = this.__zoom,
      A = Math.max(o[0], Math.min(o[1], F.k * Math.pow(2, r.apply(this, arguments)))),
      k = Yt(b);
    if (R.wheel)
      (R.mouse[0][0] !== k[0] || R.mouse[0][1] !== k[1]) &&
        (R.mouse[1] = F.invert((R.mouse[0] = k))),
        clearTimeout(R.wheel);
    else {
      if (F.k === A) return;
      (R.mouse = [k, F.invert(k)]), xu(this), R.start();
    }
    $o(b),
      (R.wheel = setTimeout(D, v)),
      R.zoom("mouse", n(w(g(F, A), R.mouse[0], R.mouse[1]), R.extent, s));
    function D() {
      (R.wheel = null), R.end();
    }
  }
  function P(b, ...O) {
    if (d || !e.apply(this, arguments)) return;
    var R = b.currentTarget,
      F = C(this, O, !0).event(b),
      A = Ot(b.view).on("mousemove.zoom", $, !0).on("mouseup.zoom", U, !0),
      k = Yt(b, R),
      D = b.clientX,
      j = b.clientY;
    WR(b.view), ef(b), (F.mouse = [k, this.__zoom.invert(k)]), xu(this), F.start();
    function $(B) {
      if (($o(B), !F.moved)) {
        var W = B.clientX - D,
          X = B.clientY - j;
        F.moved = W * W + X * X > p;
      }
      F.event(B).zoom(
        "mouse",
        n(w(F.that.__zoom, (F.mouse[0] = Yt(B, R)), F.mouse[1]), F.extent, s)
      );
    }
    function U(B) {
      A.on("mousemove.zoom mouseup.zoom", null), KR(B.view, F.moved), $o(B), F.event(B).end();
    }
  }
  function N(b, ...O) {
    if (e.apply(this, arguments)) {
      var R = this.__zoom,
        F = Yt(b.changedTouches ? b.changedTouches[0] : b, this),
        A = R.invert(F),
        k = R.k * (b.shiftKey ? 0.5 : 2),
        D = n(w(g(R, k), F, A), t.apply(this, O), s);
      $o(b),
        a > 0
          ? Ot(this).transition().duration(a).call(S, D, F, b)
          : Ot(this).call(m.transform, D, F, b);
    }
  }
  function I(b, ...O) {
    if (e.apply(this, arguments)) {
      var R = b.touches,
        F = R.length,
        A = C(this, O, b.changedTouches.length === F).event(b),
        k,
        D,
        j,
        $;
      for (ef(b), D = 0; D < F; ++D)
        (j = R[D]),
          ($ = Yt(j, this)),
          ($ = [$, this.__zoom.invert($), j.identifier]),
          A.touch0
            ? !A.touch1 && A.touch0[2] !== $[2] && ((A.touch1 = $), (A.taps = 0))
            : ((A.touch0 = $), (k = !0), (A.taps = 1 + !!c));
      c && (c = clearTimeout(c)),
        k &&
          (A.taps < 2 &&
            ((f = $[0]),
            (c = setTimeout(function () {
              c = null;
            }, h))),
          xu(this),
          A.start());
    }
  }
  function V(b, ...O) {
    if (this.__zooming) {
      var R = C(this, O).event(b),
        F = b.changedTouches,
        A = F.length,
        k,
        D,
        j,
        $;
      for ($o(b), k = 0; k < A; ++k)
        (D = F[k]),
          (j = Yt(D, this)),
          R.touch0 && R.touch0[2] === D.identifier
            ? (R.touch0[0] = j)
            : R.touch1 && R.touch1[2] === D.identifier && (R.touch1[0] = j);
      if (((D = R.that.__zoom), R.touch1)) {
        var U = R.touch0[0],
          B = R.touch0[1],
          W = R.touch1[0],
          X = R.touch1[1],
          ee = (ee = W[0] - U[0]) * ee + (ee = W[1] - U[1]) * ee,
          ue = (ue = X[0] - B[0]) * ue + (ue = X[1] - B[1]) * ue;
        (D = g(D, Math.sqrt(ee / ue))),
          (j = [(U[0] + W[0]) / 2, (U[1] + W[1]) / 2]),
          ($ = [(B[0] + X[0]) / 2, (B[1] + X[1]) / 2]);
      } else if (R.touch0) (j = R.touch0[0]), ($ = R.touch0[1]);
      else return;
      R.zoom("touch", n(w(D, j, $), R.extent, s));
    }
  }
  function q(b, ...O) {
    if (this.__zooming) {
      var R = C(this, O).event(b),
        F = b.changedTouches,
        A = F.length,
        k,
        D;
      for (
        ef(b),
          d && clearTimeout(d),
          d = setTimeout(function () {
            d = null;
          }, h),
          k = 0;
        k < A;
        ++k
      )
        (D = F[k]),
          R.touch0 && R.touch0[2] === D.identifier
            ? delete R.touch0
            : R.touch1 && R.touch1[2] === D.identifier && delete R.touch1;
      if ((R.touch1 && !R.touch0 && ((R.touch0 = R.touch1), delete R.touch1), R.touch0))
        R.touch0[1] = this.__zoom.invert(R.touch0[0]);
      else if (
        (R.end(), R.taps === 2 && ((D = Yt(D, this)), Math.hypot(f[0] - D[0], f[1] - D[1]) < y))
      ) {
        var j = Ot(this).on("dblclick.zoom");
        j && j.apply(this, arguments);
      }
    }
  }
  return (
    (m.wheelDelta = function (b) {
      return arguments.length ? ((r = typeof b == "function" ? b : Ua(+b)), m) : r;
    }),
    (m.filter = function (b) {
      return arguments.length ? ((e = typeof b == "function" ? b : Ua(!!b)), m) : e;
    }),
    (m.touchable = function (b) {
      return arguments.length ? ((i = typeof b == "function" ? b : Ua(!!b)), m) : i;
    }),
    (m.extent = function (b) {
      return arguments.length
        ? ((t =
            typeof b == "function"
              ? b
              : Ua([
                  [+b[0][0], +b[0][1]],
                  [+b[1][0], +b[1][1]],
                ])),
          m)
        : t;
    }),
    (m.scaleExtent = function (b) {
      return arguments.length ? ((o[0] = +b[0]), (o[1] = +b[1]), m) : [o[0], o[1]];
    }),
    (m.translateExtent = function (b) {
      return arguments.length
        ? ((s[0][0] = +b[0][0]),
          (s[1][0] = +b[1][0]),
          (s[0][1] = +b[0][1]),
          (s[1][1] = +b[1][1]),
          m)
        : [
            [s[0][0], s[0][1]],
            [s[1][0], s[1][1]],
          ];
    }),
    (m.constrain = function (b) {
      return arguments.length ? ((n = b), m) : n;
    }),
    (m.duration = function (b) {
      return arguments.length ? ((a = +b), m) : a;
    }),
    (m.interpolate = function (b) {
      return arguments.length ? ((u = b), m) : u;
    }),
    (m.on = function () {
      var b = l.on.apply(l, arguments);
      return b === l ? m : b;
    }),
    (m.clickDistance = function (b) {
      return arguments.length ? ((p = (b = +b) * b), m) : Math.sqrt(p);
    }),
    (m.tapDistance = function (b) {
      return arguments.length ? ((y = +b), m) : y;
    }),
    m
  );
}
const zl = _.createContext(null),
  Rq = zl.Provider,
  Gn = {
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
  lA = Gn.error001();
function he(e, t) {
  const n = _.useContext(zl);
  if (n === null) throw new Error(lA);
  return DR(n, e, t);
}
const Fe = () => {
    const e = _.useContext(zl);
    if (e === null) throw new Error(lA);
    return _.useMemo(
      () => ({
        getState: e.getState,
        setState: e.setState,
        subscribe: e.subscribe,
        destroy: e.destroy,
      }),
      [e]
    );
  },
  Aq = (e) => (e.userSelectionActive ? "none" : "all");
function o0({ position: e, children: t, className: n, style: r, ...i }) {
  const o = he(Aq),
    s = `${e}`.split("-");
  return L.createElement(
    "div",
    { className: Ze(["react-flow__panel", n, ...s]), style: { ...r, pointerEvents: o }, ...i },
    t
  );
}
function Nq({ proOptions: e, position: t = "bottom-right" }) {
  return e != null && e.hideAttribution
    ? null
    : L.createElement(
        o0,
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
          "React Flow"
        )
      );
}
const Mq = ({
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
            n
          ),
          u
        )
  );
};
var Iq = _.memo(Mq);
const s0 = (e) => ({ width: e.offsetWidth, height: e.offsetHeight }),
  ho = (e, t = 0, n = 1) => Math.min(Math.max(e, t), n),
  a0 = (e = { x: 0, y: 0 }, t) => ({ x: ho(e.x, t[0][0], t[1][0]), y: ho(e.y, t[0][1], t[1][1]) }),
  ux = (e, t, n) =>
    e < t ? ho(Math.abs(e - t), 1, 50) / 50 : e > n ? -ho(Math.abs(e - n), 1, 50) / 50 : 0,
  cA = (e, t) => {
    const n = ux(e.x, 35, t.width - 35) * 20,
      r = ux(e.y, 35, t.height - 35) * 20;
    return [n, r];
  },
  fA = (e) => {
    var t;
    return (
      ((t = e.getRootNode) == null ? void 0 : t.call(e)) ||
      (window == null ? void 0 : window.document)
    );
  },
  dA = (e, t) => ({
    x: Math.min(e.x, t.x),
    y: Math.min(e.y, t.y),
    x2: Math.max(e.x2, t.x2),
    y2: Math.max(e.y2, t.y2),
  }),
  Ws = ({ x: e, y: t, width: n, height: r }) => ({ x: e, y: t, x2: e + n, y2: t + r }),
  hA = ({ x: e, y: t, x2: n, y2: r }) => ({ x: e, y: t, width: n - e, height: r - t }),
  lx = (e) => ({
    ...(e.positionAbsolute || { x: 0, y: 0 }),
    width: e.width || 0,
    height: e.height || 0,
  }),
  Dq = (e, t) => hA(dA(Ws(e), Ws(t))),
  Tv = (e, t) => {
    const n = Math.max(0, Math.min(e.x + e.width, t.x + t.width) - Math.max(e.x, t.x)),
      r = Math.max(0, Math.min(e.y + e.height, t.y + t.height) - Math.max(e.y, t.y));
    return Math.ceil(n * r);
  },
  Oq = (e) => Ft(e.width) && Ft(e.height) && Ft(e.x) && Ft(e.y),
  Ft = (e) => !isNaN(e) && isFinite(e),
  Te = Symbol.for("internals"),
  pA = ["Enter", " ", "Escape"],
  Lq = (e, t) => {},
  Fq = (e) => "nativeEvent" in e;
function kv(e) {
  var i, o;
  const t = Fq(e) ? e.nativeEvent : e,
    n =
      ((o = (i = t.composedPath) == null ? void 0 : i.call(t)) == null ? void 0 : o[0]) || e.target;
  return (
    ["INPUT", "SELECT", "TEXTAREA"].includes(n == null ? void 0 : n.nodeName) ||
    (n == null ? void 0 : n.hasAttribute("contenteditable")) ||
    !!(n != null && n.closest(".nokey"))
  );
}
const mA = (e) => "clientX" in e,
  Cr = (e, t) => {
    var o, s;
    const n = mA(e),
      r = n ? e.clientX : (o = e.touches) == null ? void 0 : o[0].clientX,
      i = n ? e.clientY : (s = e.touches) == null ? void 0 : s[0].clientY;
    return {
      x: r - ((t == null ? void 0 : t.left) ?? 0),
      y: i - ((t == null ? void 0 : t.top) ?? 0),
    };
  },
  ol = () => {
    var e;
    return (
      typeof navigator < "u" &&
      ((e = navigator == null ? void 0 : navigator.userAgent) == null
        ? void 0
        : e.indexOf("Mac")) >= 0
    );
  },
  ca = ({
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
        ? L.createElement(Iq, {
            x: n,
            y: r,
            label: i,
            labelStyle: o,
            labelShowBg: s,
            labelBgStyle: a,
            labelBgPadding: u,
            labelBgBorderRadius: l,
          })
        : null
    );
ca.displayName = "BaseEdge";
function zo(e, t, n) {
  return n === void 0
    ? n
    : (r) => {
        const i = t().edges.find((o) => o.id === e);
        i && n(r, { ...i });
      };
}
function gA({ sourceX: e, sourceY: t, targetX: n, targetY: r }) {
  const i = Math.abs(n - e) / 2,
    o = n < e ? n + i : n - i,
    s = Math.abs(r - t) / 2,
    a = r < t ? r + s : r - s;
  return [o, a, i, s];
}
function vA({
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
var ui;
(function (e) {
  (e.Strict = "strict"), (e.Loose = "loose");
})(ui || (ui = {}));
var Kr;
(function (e) {
  (e.Free = "free"), (e.Vertical = "vertical"), (e.Horizontal = "horizontal");
})(Kr || (Kr = {}));
var Ks;
(function (e) {
  (e.Partial = "partial"), (e.Full = "full");
})(Ks || (Ks = {}));
var hr;
(function (e) {
  (e.Bezier = "default"),
    (e.Straight = "straight"),
    (e.Step = "step"),
    (e.SmoothStep = "smoothstep"),
    (e.SimpleBezier = "simplebezier");
})(hr || (hr = {}));
var Ys;
(function (e) {
  (e.Arrow = "arrow"), (e.ArrowClosed = "arrowclosed");
})(Ys || (Ys = {}));
var Y;
(function (e) {
  (e.Left = "left"), (e.Top = "top"), (e.Right = "right"), (e.Bottom = "bottom");
})(Y || (Y = {}));
function cx({ pos: e, x1: t, y1: n, x2: r, y2: i }) {
  return e === Y.Left || e === Y.Right ? [0.5 * (t + r), n] : [t, 0.5 * (n + i)];
}
function yA({
  sourceX: e,
  sourceY: t,
  sourcePosition: n = Y.Bottom,
  targetX: r,
  targetY: i,
  targetPosition: o = Y.Top,
}) {
  const [s, a] = cx({ pos: n, x1: e, y1: t, x2: r, y2: i }),
    [u, l] = cx({ pos: o, x1: r, y1: i, x2: e, y2: t }),
    [c, f, d, h] = vA({
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
const u0 = _.memo(
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
    const [y, m, g] = yA({
      sourceX: e,
      sourceY: t,
      sourcePosition: i,
      targetX: n,
      targetY: r,
      targetPosition: o,
    });
    return L.createElement(ca, {
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
  }
);
u0.displayName = "SimpleBezierEdge";
const fx = {
    [Y.Left]: { x: -1, y: 0 },
    [Y.Right]: { x: 1, y: 0 },
    [Y.Top]: { x: 0, y: -1 },
    [Y.Bottom]: { x: 0, y: 1 },
  },
  Vq = ({ source: e, sourcePosition: t = Y.Bottom, target: n }) =>
    t === Y.Left || t === Y.Right
      ? e.x < n.x
        ? { x: 1, y: 0 }
        : { x: -1, y: 0 }
      : e.y < n.y
      ? { x: 0, y: 1 }
      : { x: 0, y: -1 },
  dx = (e, t) => Math.sqrt(Math.pow(t.x - e.x, 2) + Math.pow(t.y - e.y, 2));
function jq({
  source: e,
  sourcePosition: t = Y.Bottom,
  target: n,
  targetPosition: r = Y.Top,
  center: i,
  offset: o,
}) {
  const s = fx[t],
    a = fx[r],
    u = { x: e.x + s.x * o, y: e.y + s.y * o },
    l = { x: n.x + a.x * o, y: n.y + a.y * o },
    c = Vq({ source: u, sourcePosition: t, target: l }),
    f = c.x !== 0 ? "x" : "y",
    d = c[f];
  let h = [],
    v,
    p;
  const y = { x: 0, y: 0 },
    m = { x: 0, y: 0 },
    [g, w, x, S] = gA({ sourceX: e.x, sourceY: e.y, targetX: n.x, targetY: n.y });
  if (s[f] * a[f] === -1) {
    (v = i.x ?? g), (p = i.y ?? w);
    const E = [
        { x: v, y: u.y },
        { x: v, y: l.y },
      ],
      T = [
        { x: u.x, y: p },
        { x: l.x, y: p },
      ];
    s[f] === d ? (h = f === "x" ? E : T) : (h = f === "x" ? T : E);
  } else {
    const E = [{ x: u.x, y: l.y }],
      T = [{ x: l.x, y: u.y }];
    if ((f === "x" ? (h = s.x === d ? T : E) : (h = s.y === d ? E : T), t === r)) {
      const q = Math.abs(e[f] - n[f]);
      if (q <= o) {
        const b = Math.min(o - 1, o - q);
        s[f] === d ? (y[f] = (u[f] > e[f] ? -1 : 1) * b) : (m[f] = (l[f] > n[f] ? -1 : 1) * b);
      }
    }
    if (t !== r) {
      const q = f === "x" ? "y" : "x",
        b = s[f] === a[q],
        O = u[q] > l[q],
        R = u[q] < l[q];
      ((s[f] === 1 && ((!b && O) || (b && R))) || (s[f] !== 1 && ((!b && R) || (b && O)))) &&
        (h = f === "x" ? E : T);
    }
    const P = { x: u.x + y.x, y: u.y + y.y },
      N = { x: l.x + m.x, y: l.y + m.y },
      I = Math.max(Math.abs(P.x - h[0].x), Math.abs(N.x - h[0].x)),
      V = Math.max(Math.abs(P.y - h[0].y), Math.abs(N.y - h[0].y));
    I >= V ? ((v = (P.x + N.x) / 2), (p = h[0].y)) : ((v = h[0].x), (p = (P.y + N.y) / 2));
  }
  return [[e, { x: u.x + y.x, y: u.y + y.y }, ...h, { x: l.x + m.x, y: l.y + m.y }, n], v, p, x, S];
}
function qq(e, t, n, r) {
  const i = Math.min(dx(e, t) / 2, dx(t, n) / 2, r),
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
function Pv({
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
  const [c, f, d, h, v] = jq({
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
          ? (w = qq(c[g - 1], m, c[g + 1], s))
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
const Bl = _.memo(
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
    const [m, g, w] = Pv({
      sourceX: e,
      sourceY: t,
      sourcePosition: f,
      targetX: n,
      targetY: r,
      targetPosition: d,
      borderRadius: p == null ? void 0 : p.borderRadius,
      offset: p == null ? void 0 : p.offset,
    });
    return L.createElement(ca, {
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
  }
);
Bl.displayName = "SmoothStepEdge";
const l0 = _.memo((e) => {
  var t;
  return L.createElement(Bl, {
    ...e,
    pathOptions: _.useMemo(() => {
      var n;
      return { borderRadius: 0, offset: (n = e.pathOptions) == null ? void 0 : n.offset };
    }, [(t = e.pathOptions) == null ? void 0 : t.offset]),
  });
});
l0.displayName = "StepEdge";
function $q({ sourceX: e, sourceY: t, targetX: n, targetY: r }) {
  const [i, o, s, a] = gA({ sourceX: e, sourceY: t, targetX: n, targetY: r });
  return [`M ${e},${t}L ${n},${r}`, i, o, s, a];
}
const c0 = _.memo(
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
    const [v, p, y] = $q({ sourceX: e, sourceY: t, targetX: n, targetY: r });
    return L.createElement(ca, {
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
  }
);
c0.displayName = "StraightEdge";
function Ha(e, t) {
  return e >= 0 ? 0.5 * e : t * 25 * Math.sqrt(-e);
}
function hx({ pos: e, x1: t, y1: n, x2: r, y2: i, c: o }) {
  switch (e) {
    case Y.Left:
      return [t - Ha(t - r, o), n];
    case Y.Right:
      return [t + Ha(r - t, o), n];
    case Y.Top:
      return [t, n - Ha(n - i, o)];
    case Y.Bottom:
      return [t, n + Ha(i - n, o)];
  }
}
function wA({
  sourceX: e,
  sourceY: t,
  sourcePosition: n = Y.Bottom,
  targetX: r,
  targetY: i,
  targetPosition: o = Y.Top,
  curvature: s = 0.25,
}) {
  const [a, u] = hx({ pos: n, x1: e, y1: t, x2: r, y2: i, c: s }),
    [l, c] = hx({ pos: o, x1: r, y1: i, x2: e, y2: t, c: s }),
    [f, d, h, v] = vA({
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
const sl = _.memo(
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
    const [m, g, w] = wA({
      sourceX: e,
      sourceY: t,
      sourcePosition: i,
      targetX: n,
      targetY: r,
      targetPosition: o,
      curvature: p == null ? void 0 : p.curvature,
    });
    return L.createElement(ca, {
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
  }
);
sl.displayName = "BezierEdge";
const f0 = _.createContext(null),
  zq = f0.Provider;
f0.Consumer;
const Bq = () => _.useContext(f0),
  Uq = (e) => "id" in e && "source" in e && "target" in e,
  Hq = ({ source: e, sourceHandle: t, target: n, targetHandle: r }) =>
    `reactflow__edge-${e}${t || ""}-${n}${r || ""}`,
  Rv = (e, t) =>
    typeof e > "u"
      ? ""
      : typeof e == "string"
      ? e
      : `${t ? `${t}__` : ""}${Object.keys(e)
          .sort()
          .map((r) => `${r}=${e[r]}`)
          .join("&")}`,
  Gq = (e, t) =>
    t.some(
      (n) =>
        n.source === e.source &&
        n.target === e.target &&
        (n.sourceHandle === e.sourceHandle || (!n.sourceHandle && !e.sourceHandle)) &&
        (n.targetHandle === e.targetHandle || (!n.targetHandle && !e.targetHandle))
    ),
  Wq = (e, t) => {
    if (!e.source || !e.target) return t;
    let n;
    return Uq(e) ? (n = { ...e }) : (n = { ...e, id: Hq(e) }), Gq(n, t) ? t : t.concat(n);
  },
  Av = ({ x: e, y: t }, [n, r, i], o, [s, a]) => {
    const u = { x: (e - n) / i, y: (t - r) / i };
    return o ? { x: s * Math.round(u.x / s), y: a * Math.round(u.y / a) } : u;
  },
  xA = ({ x: e, y: t }, [n, r, i]) => ({ x: e * i + n, y: t * i + r }),
  ei = (e, t = [0, 0]) => {
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
  Ul = (e, t = [0, 0]) => {
    if (e.length === 0) return { x: 0, y: 0, width: 0, height: 0 };
    const n = e.reduce(
      (r, i) => {
        const { x: o, y: s } = ei(i, t).positionAbsolute;
        return dA(r, Ws({ x: o, y: s, width: i.width || 0, height: i.height || 0 }));
      },
      { x: 1 / 0, y: 1 / 0, x2: -1 / 0, y2: -1 / 0 }
    );
    return hA(n);
  },
  _A = (e, t, [n, r, i] = [0, 0, 1], o = !1, s = !1, a = [0, 0]) => {
    const u = { x: (t.x - n) / i, y: (t.y - r) / i, width: t.width / i, height: t.height / i },
      l = [];
    return (
      e.forEach((c) => {
        const { width: f, height: d, selectable: h = !0, hidden: v = !1 } = c;
        if ((s && !h) || v) return !1;
        const { positionAbsolute: p } = ei(c, a),
          y = { x: p.x, y: p.y, width: f || 0, height: d || 0 },
          m = Tv(u, y),
          g = typeof f > "u" || typeof d > "u" || f === null || d === null,
          w = o && m > 0,
          x = (f || 0) * (d || 0);
        (g || w || m >= x || c.dragging) && l.push(c);
      }),
      l
    );
  },
  SA = (e, t) => {
    const n = e.map((r) => r.id);
    return t.filter((r) => n.includes(r.source) || n.includes(r.target));
  },
  bA = (e, t, n, r, i, o = 0.1) => {
    const s = t / (e.width * (1 + o)),
      a = n / (e.height * (1 + o)),
      u = Math.min(s, a),
      l = ho(u, r, i),
      c = e.x + e.width / 2,
      f = e.y + e.height / 2,
      d = t / 2 - c * l,
      h = n / 2 - f * l;
    return { x: d, y: h, zoom: l };
  },
  $r = (e, t = 0) => e.transition().duration(t);
function px(e, t, n, r) {
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
function Kq(e, t, n, r, i, o) {
  const { x: s, y: a } = Cr(e),
    l = t.elementsFromPoint(s, a).find((v) => v.classList.contains("react-flow__handle"));
  if (l) {
    const v = l.getAttribute("data-nodeid");
    if (v) {
      const p = d0(void 0, l),
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
    return { handle: null, validHandleResult: EA() };
  if (c.length === 1) return c[0];
  const d = c.some(({ validHandleResult: v }) => v.isValid),
    h = c.some(({ handle: v }) => v.type === "target");
  return (
    c.find(({ handle: v, validHandleResult: p }) =>
      h ? v.type === "target" : d ? p.isValid : !0
    ) || c[0]
  );
}
const Yq = { source: null, target: null, sourceHandle: null, targetHandle: null },
  EA = () => ({ handleDomNode: null, isValid: !1, connection: Yq, endHandle: null });
function CA(e, t, n, r, i, o, s) {
  const a = i === "target",
    u = s.querySelector(
      `.react-flow__handle[data-id="${e == null ? void 0 : e.nodeId}-${e == null ? void 0 : e.id}-${
        e == null ? void 0 : e.type
      }"]`
    ),
    l = { ...EA(), handleDomNode: u };
  if (u) {
    const c = d0(void 0, u),
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
        (t === ui.Strict ? (a && c === "source") || (!a && c === "target") : f !== n || d !== r) &&
        ((l.endHandle = { nodeId: f, handleId: d, type: c }), (l.isValid = o(p)));
  }
  return l;
}
function Xq({ nodes: e, nodeId: t, handleId: n, handleType: r }) {
  return e.reduce((i, o) => {
    if (o[Te]) {
      const { handleBounds: s } = o[Te];
      let a = [],
        u = [];
      s && ((a = px(o, s, "source", `${t}-${n}-${r}`)), (u = px(o, s, "target", `${t}-${n}-${r}`))),
        i.push(...a, ...u);
    }
    return i;
  }, []);
}
function d0(e, t) {
  return (
    e ||
    (t != null && t.classList.contains("target")
      ? "target"
      : t != null && t.classList.contains("source")
      ? "source"
      : null)
  );
}
function tf(e) {
  e == null ||
    e.classList.remove(
      "valid",
      "connecting",
      "react-flow__handle-valid",
      "react-flow__handle-connecting"
    );
}
function Zq(e, t) {
  let n = null;
  return t ? (n = "valid") : e && !t && (n = "invalid"), n;
}
function TA({
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
  const c = fA(e.target),
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
  const { x: S, y: C } = Cr(e),
    E = c == null ? void 0 : c.elementFromPoint(S, C),
    T = d0(u, E),
    P = d == null ? void 0 : d.getBoundingClientRect();
  if (!P || !T) return;
  let N,
    I = Cr(e, P),
    V = !1,
    q = null,
    b = !1,
    O = null;
  const R = Xq({ nodes: m(), nodeId: n, handleId: t, handleType: T }),
    F = () => {
      if (!h) return;
      const [D, j] = cA(I, P);
      y({ x: D, y: j }), (w = requestAnimationFrame(F));
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
  function A(D) {
    const { transform: j } = o();
    I = Cr(D, P);
    const { handle: $, validHandleResult: U } = Kq(D, c, Av(I, j, !1, [1, 1]), v, R, (B) =>
      CA(B, f, n, t, i ? "target" : "source", a, c)
    );
    if (
      ((x = $),
      V || (F(), (V = !0)),
      (O = U.handleDomNode),
      (q = U.connection),
      (b = U.isValid),
      s({
        connectionPosition: x && b ? xA({ x: x.x, y: x.y }, j) : I,
        connectionStatus: Zq(!!x, b),
        connectionEndHandle: U.endHandle,
      }),
      !x && !b && !O)
    )
      return tf(N);
    q.source !== q.target &&
      O &&
      (tf(N),
      (N = O),
      O.classList.add("connecting", "react-flow__handle-connecting"),
      O.classList.toggle("valid", b),
      O.classList.toggle("react-flow__handle-valid", b));
  }
  function k(D) {
    var j, $;
    (x || O) && q && b && (r == null || r(q)),
      ($ = (j = o()).onConnectEnd) == null || $.call(j, D),
      u && (l == null || l(D)),
      tf(N),
      g(),
      cancelAnimationFrame(w),
      (V = !1),
      (b = !1),
      (q = null),
      (O = null),
      c.removeEventListener("mousemove", A),
      c.removeEventListener("mouseup", k),
      c.removeEventListener("touchmove", A),
      c.removeEventListener("touchend", k);
  }
  c.addEventListener("mousemove", A),
    c.addEventListener("mouseup", k),
    c.addEventListener("touchmove", A),
    c.addEventListener("touchend", k);
}
const mx = () => !0,
  Qq = (e) => ({
    connectionStartHandle: e.connectionStartHandle,
    connectOnClick: e.connectOnClick,
    noPanClassName: e.noPanClassName,
  }),
  Jq = (e, t, n) => (r) => {
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
  kA = _.forwardRef(
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
      h
    ) => {
      var P, N;
      const v = s || null,
        p = e === "target",
        y = Fe(),
        m = Bq(),
        { connectOnClick: g, noPanClassName: w } = he(Qq, He),
        { connecting: x, clickConnecting: S } = he(Jq(m, v, e), He);
      m || (N = (P = y.getState()).onError) == null || N.call(P, "010", Gn.error010());
      const C = (I) => {
          const { defaultEdgeOptions: V, onConnect: q, hasDefaultEdges: b } = y.getState(),
            O = { ...V, ...I };
          if (b) {
            const { edges: R, setEdges: F } = y.getState();
            F(Wq(O, R));
          }
          q == null || q(O), a == null || a(O);
        },
        E = (I) => {
          if (!m) return;
          const V = mA(I);
          i &&
            ((V && I.button === 0) || !V) &&
            TA({
              event: I,
              handleId: v,
              nodeId: m,
              onConnect: C,
              isTarget: p,
              getState: y.getState,
              setState: y.setState,
              isValidConnection: n || y.getState().isValidConnection || mx,
            }),
            V ? c == null || c(I) : f == null || f(I);
        },
        T = (I) => {
          const {
            onClickConnectStart: V,
            onClickConnectEnd: q,
            connectionClickStartHandle: b,
            connectionMode: O,
            isValidConnection: R,
          } = y.getState();
          if (!m || (!b && !i)) return;
          if (!b) {
            V == null || V(I, { nodeId: m, handleId: v, handleType: e }),
              y.setState({ connectionClickStartHandle: { nodeId: m, type: e, handleId: v } });
            return;
          }
          const F = fA(I.target),
            A = n || R || mx,
            { connection: k, isValid: D } = CA(
              { nodeId: m, id: v, type: e },
              O,
              b.nodeId,
              b.handleId || null,
              b.type,
              A,
              F
            );
          D && C(k), q == null || q(I), y.setState({ connectionClickStartHandle: null });
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
              connecting: S,
              connectionindicator: r && ((i && !x) || (o && x)),
            },
          ]),
          onMouseDown: E,
          onTouchStart: E,
          onClick: g ? T : void 0,
          ref: h,
          ...d,
        },
        u
      );
    }
  );
kA.displayName = "Handle";
var al = _.memo(kA);
const PA = ({
  data: e,
  isConnectable: t,
  targetPosition: n = Y.Top,
  sourcePosition: r = Y.Bottom,
}) =>
  L.createElement(
    L.Fragment,
    null,
    L.createElement(al, { type: "target", position: n, isConnectable: t }),
    e == null ? void 0 : e.label,
    L.createElement(al, { type: "source", position: r, isConnectable: t })
  );
PA.displayName = "DefaultNode";
var Nv = _.memo(PA);
const RA = ({ data: e, isConnectable: t, sourcePosition: n = Y.Bottom }) =>
  L.createElement(
    L.Fragment,
    null,
    e == null ? void 0 : e.label,
    L.createElement(al, { type: "source", position: n, isConnectable: t })
  );
RA.displayName = "InputNode";
var AA = _.memo(RA);
const NA = ({ data: e, isConnectable: t, targetPosition: n = Y.Top }) =>
  L.createElement(
    L.Fragment,
    null,
    L.createElement(al, { type: "target", position: n, isConnectable: t }),
    e == null ? void 0 : e.label
  );
NA.displayName = "OutputNode";
var MA = _.memo(NA);
const h0 = () => null;
h0.displayName = "GroupNode";
const e$ = (e) => ({
    selectedNodes: e.getNodes().filter((t) => t.selected),
    selectedEdges: e.edges.filter((t) => t.selected).map((t) => ({ ...t })),
  }),
  Ga = (e) => e.id;
function t$(e, t) {
  return (
    He(e.selectedNodes.map(Ga), t.selectedNodes.map(Ga)) &&
    He(e.selectedEdges.map(Ga), t.selectedEdges.map(Ga))
  );
}
const IA = _.memo(({ onSelectionChange: e }) => {
  const t = Fe(),
    { selectedNodes: n, selectedEdges: r } = he(e$, t$);
  return (
    _.useEffect(() => {
      const i = { nodes: n, edges: r };
      e == null || e(i), t.getState().onSelectionChange.forEach((o) => o(i));
    }, [n, r, e]),
    null
  );
});
IA.displayName = "SelectionListener";
const n$ = (e) => !!e.onSelectionChange;
function r$({ onSelectionChange: e }) {
  const t = he(n$);
  return e || t ? L.createElement(IA, { onSelectionChange: e }) : null;
}
const i$ = (e) => ({
  setNodes: e.setNodes,
  setEdges: e.setEdges,
  setDefaultNodesAndEdges: e.setDefaultNodesAndEdges,
  setMinZoom: e.setMinZoom,
  setMaxZoom: e.setMaxZoom,
  setTranslateExtent: e.setTranslateExtent,
  setNodeExtent: e.setNodeExtent,
  reset: e.reset,
});
function wi(e, t) {
  _.useEffect(() => {
    typeof e < "u" && t(e);
  }, [e]);
}
function re(e, t, n) {
  _.useEffect(() => {
    typeof t < "u" && n({ [e]: t });
  }, [t]);
}
const o$ = ({
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
    connectionMode: S,
    snapGrid: C,
    snapToGrid: E,
    translateExtent: T,
    connectOnClick: P,
    defaultEdgeOptions: N,
    fitView: I,
    fitViewOptions: V,
    onNodesDelete: q,
    onEdgesDelete: b,
    onNodeDrag: O,
    onNodeDragStart: R,
    onNodeDragStop: F,
    onSelectionDrag: A,
    onSelectionDragStart: k,
    onSelectionDragStop: D,
    noPanClassName: j,
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
        setDefaultNodesAndEdges: Pe,
        setMinZoom: Ge,
        setMaxZoom: Ve,
        setTranslateExtent: Q,
        setNodeExtent: je,
        reset: K,
      } = he(i$, He),
      G = Fe();
    return (
      _.useEffect(() => {
        const be = r == null ? void 0 : r.map((Bt) => ({ ...Bt, ...N }));
        return (
          Pe(n, be),
          () => {
            K();
          }
        );
      }, []),
      re("defaultEdgeOptions", N, G.setState),
      re("connectionMode", S, G.setState),
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
      re("snapToGrid", E, G.setState),
      re("snapGrid", C, G.setState),
      re("onNodesChange", g, G.setState),
      re("onEdgesChange", w, G.setState),
      re("connectOnClick", P, G.setState),
      re("fitViewOnInit", I, G.setState),
      re("fitViewOnInitOptions", V, G.setState),
      re("onNodesDelete", q, G.setState),
      re("onEdgesDelete", b, G.setState),
      re("onNodeDrag", O, G.setState),
      re("onNodeDragStart", R, G.setState),
      re("onNodeDragStop", F, G.setState),
      re("onSelectionDrag", A, G.setState),
      re("onSelectionDragStart", k, G.setState),
      re("onSelectionDragStop", D, G.setState),
      re("noPanClassName", j, G.setState),
      re("nodeOrigin", $, G.setState),
      re("rfId", U, G.setState),
      re("autoPanOnConnect", B, G.setState),
      re("autoPanOnNodeDrag", W, G.setState),
      re("onError", X, G.setState),
      re("connectionRadius", ee, G.setState),
      re("isValidConnection", ue, G.setState),
      re("nodeDragThreshold", se, G.setState),
      wi(e, oe),
      wi(t, De),
      wi(p, Ge),
      wi(y, Ve),
      wi(T, Q),
      wi(m, je),
      null
    );
  },
  gx = { display: "none" },
  s$ = {
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
  DA = "react-flow__node-desc",
  OA = "react-flow__edge-desc",
  a$ = "react-flow__aria-live",
  u$ = (e) => e.ariaLiveMessage;
function l$({ rfId: e }) {
  const t = he(u$);
  return L.createElement(
    "div",
    { id: `${a$}-${e}`, "aria-live": "assertive", "aria-atomic": "true", style: s$ },
    t
  );
}
function c$({ rfId: e, disableKeyboardA11y: t }) {
  return L.createElement(
    L.Fragment,
    null,
    L.createElement(
      "div",
      { id: `${DA}-${e}`, style: gx },
      "Press enter or space to select a node.",
      !t && "You can then use the arrow keys to move the node around.",
      " Press delete to remove it and escape to cancel.",
      " "
    ),
    L.createElement(
      "div",
      { id: `${OA}-${e}`, style: gx },
      "Press enter or space to select an edge. You can then press delete to remove it or escape to cancel."
    ),
    !t && L.createElement(l$, { rfId: e })
  );
}
var Xs = (e = null, t = { actInsideInputWithModifier: !0 }) => {
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
              (!i.current || (i.current && !t.actInsideInputWithModifier)) && kv(h))
            )
              return !1;
            const p = yx(h.code, a);
            o.current.add(h[p]), vx(s, o.current, !1) && (h.preventDefault(), r(!0));
          },
          f = (h) => {
            if ((!i.current || (i.current && !t.actInsideInputWithModifier)) && kv(h)) return !1;
            const p = yx(h.code, a);
            vx(s, o.current, !0) ? (r(!1), o.current.clear()) : o.current.delete(h[p]),
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
function vx(e, t, n) {
  return e.filter((r) => n || r.length === t.size).some((r) => r.every((i) => t.has(i)));
}
function yx(e, t) {
  return t.includes(e) ? "code" : "key";
}
function LA(e, t, n, r) {
  var a, u;
  const i = e.parentNode || e.parentId;
  if (!i) return n;
  const o = t.get(i),
    s = ei(o, r);
  return LA(
    o,
    t,
    {
      x: (n.x ?? 0) + s.x,
      y: (n.y ?? 0) + s.y,
      z:
        (((a = o[Te]) == null ? void 0 : a.z) ?? 0) > (n.z ?? 0)
          ? ((u = o[Te]) == null ? void 0 : u.z) ?? 0
          : n.z ?? 0,
    },
    r
  );
}
function FA(e, t, n) {
  e.forEach((r) => {
    var o;
    const i = r.parentNode || r.parentId;
    if (i && !e.has(i)) throw new Error(`Parent node ${i} not found`);
    if (i || (n != null && n[r.id])) {
      const { x: s, y: a, z: u } = LA(
        r,
        e,
        { ...r.position, z: ((o = r[Te]) == null ? void 0 : o.z) ?? 0 },
        t
      );
      (r.positionAbsolute = { x: s, y: a }),
        (r[Te].z = u),
        n != null && n[r.id] && (r[Te].isParent = !0);
    }
  });
}
function nf(e, t, n, r) {
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
      Object.defineProperty(c, Te, {
        enumerable: !1,
        value: {
          handleBounds: d || (h = l == null ? void 0 : l[Te]) == null ? void 0 : h.handleBounds,
          z: u,
        },
      }),
        i.set(a.id, c);
    }),
    FA(i, n, o),
    i
  );
}
function VA(e, t = {}) {
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
      const y = Ul(v, f),
        { x: m, y: g, zoom: w } = bA(y, r, i, t.minZoom ?? o, t.maxZoom ?? s, t.padding ?? 0.1),
        x = Vn.translate(m, g).scale(w);
      return (
        typeof t.duration == "number" && t.duration > 0
          ? a.transform($r(u, t.duration), x)
          : a.transform(u, x),
        !0
      );
    }
  }
  return !1;
}
function f$(e, t) {
  return (
    e.forEach((n) => {
      const r = t.get(n.id);
      r && t.set(r.id, { ...r, [Te]: r[Te], selected: n.selected });
    }),
    new Map(t)
  );
}
function d$(e, t) {
  return t.map((n) => {
    const r = e.find((i) => i.id === n.id);
    return r && (n.selected = r.selected), n;
  });
}
function Wa({ changedNodes: e, changedEdges: t, get: n, set: r }) {
  const {
    nodeInternals: i,
    edges: o,
    onNodesChange: s,
    onEdgesChange: a,
    hasDefaultNodes: u,
    hasDefaultEdges: l,
  } = n();
  e != null && e.length && (u && r({ nodeInternals: f$(e, i) }), s == null || s(e)),
    t != null && t.length && (l && r({ edges: d$(t, o) }), a == null || a(t));
}
const xi = () => {},
  h$ = {
    zoomIn: xi,
    zoomOut: xi,
    zoomTo: xi,
    getZoom: () => 1,
    setViewport: xi,
    getViewport: () => ({ x: 0, y: 0, zoom: 1 }),
    fitView: () => !1,
    setCenter: xi,
    fitBounds: xi,
    project: (e) => e,
    screenToFlowPosition: (e) => e,
    flowToScreenPosition: (e) => e,
    viewportInitialized: !1,
  },
  p$ = (e) => ({ d3Zoom: e.d3Zoom, d3Selection: e.d3Selection }),
  m$ = () => {
    const e = Fe(),
      { d3Zoom: t, d3Selection: n } = he(p$, He);
    return _.useMemo(
      () =>
        n && t
          ? {
              zoomIn: (i) => t.scaleBy($r(n, i == null ? void 0 : i.duration), 1.2),
              zoomOut: (i) => t.scaleBy($r(n, i == null ? void 0 : i.duration), 1 / 1.2),
              zoomTo: (i, o) => t.scaleTo($r(n, o == null ? void 0 : o.duration), i),
              getZoom: () => e.getState().transform[2],
              setViewport: (i, o) => {
                const [s, a, u] = e.getState().transform,
                  l = Vn.translate(i.x ?? s, i.y ?? a).scale(i.zoom ?? u);
                t.transform($r(n, o == null ? void 0 : o.duration), l);
              },
              getViewport: () => {
                const [i, o, s] = e.getState().transform;
                return { x: i, y: o, zoom: s };
              },
              fitView: (i) => VA(e.getState, i),
              setCenter: (i, o, s) => {
                const { width: a, height: u, maxZoom: l } = e.getState(),
                  c = typeof (s == null ? void 0 : s.zoom) < "u" ? s.zoom : l,
                  f = a / 2 - i * c,
                  d = u / 2 - o * c,
                  h = Vn.translate(f, d).scale(c);
                t.transform($r(n, s == null ? void 0 : s.duration), h);
              },
              fitBounds: (i, o) => {
                const { width: s, height: a, minZoom: u, maxZoom: l } = e.getState(),
                  { x: c, y: f, zoom: d } = bA(
                    i,
                    s,
                    a,
                    u,
                    l,
                    (o == null ? void 0 : o.padding) ?? 0.1
                  ),
                  h = Vn.translate(c, f).scale(d);
                t.transform($r(n, o == null ? void 0 : o.duration), h);
              },
              project: (i) => {
                const { transform: o, snapToGrid: s, snapGrid: a } = e.getState();
                return (
                  console.warn(
                    "[DEPRECATED] `project` is deprecated. Instead use `screenToFlowPosition`. There is no need to subtract the react flow bounds anymore! https://reactflow.dev/api-reference/types/react-flow-instance#screen-to-flow-position"
                  ),
                  Av(i, o, s, a)
                );
              },
              screenToFlowPosition: (i) => {
                const { transform: o, snapToGrid: s, snapGrid: a, domNode: u } = e.getState();
                if (!u) return i;
                const { x: l, y: c } = u.getBoundingClientRect(),
                  f = { x: i.x - l, y: i.y - c };
                return Av(f, o, s, a);
              },
              flowToScreenPosition: (i) => {
                const { transform: o, domNode: s } = e.getState();
                if (!s) return i;
                const { x: a, y: u } = s.getBoundingClientRect(),
                  l = xA(i, o);
                return { x: l.x + a, y: l.y + u };
              },
              viewportInitialized: !0,
            }
          : h$,
      [t, n]
    );
  };
function p0() {
  const e = m$(),
    t = Fe(),
    n = _.useCallback(
      () =>
        t
          .getState()
          .getNodes()
          .map((p) => ({ ...p })),
      []
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
        S = typeof p == "function" ? p(x) : p;
      if (g) m(S);
      else if (w) {
        const C =
          S.length === 0
            ? x.map((E) => ({ type: "remove", id: E.id }))
            : S.map((E) => ({ item: E, type: "reset" }));
        w(C);
      }
    }, []),
    a = _.useCallback((p) => {
      const { edges: y = [], setEdges: m, hasDefaultEdges: g, onEdgesChange: w } = t.getState(),
        x = typeof p == "function" ? p(y) : p;
      if (g) m(x);
      else if (w) {
        const S =
          x.length === 0
            ? y.map((C) => ({ type: "remove", id: C.id }))
            : x.map((C) => ({ item: C, type: "reset" }));
        w(S);
      }
    }, []),
    u = _.useCallback((p) => {
      const y = Array.isArray(p) ? p : [p],
        { getNodes: m, setNodes: g, hasDefaultNodes: w, onNodesChange: x } = t.getState();
      if (w) {
        const C = [...m(), ...y];
        g(C);
      } else if (x) {
        const S = y.map((C) => ({ item: C, type: "add" }));
        x(S);
      }
    }, []),
    l = _.useCallback((p) => {
      const y = Array.isArray(p) ? p : [p],
        { edges: m = [], setEdges: g, hasDefaultEdges: w, onEdgesChange: x } = t.getState();
      if (w) g([...m, ...y]);
      else if (x) {
        const S = y.map((C) => ({ item: C, type: "add" }));
        x(S);
      }
    }, []),
    c = _.useCallback(() => {
      const { getNodes: p, edges: y = [], transform: m } = t.getState(),
        [g, w, x] = m;
      return {
        nodes: p().map((S) => ({ ...S })),
        edges: y.map((S) => ({ ...S })),
        viewport: { x: g, y: w, zoom: x },
      };
    }, []),
    f = _.useCallback(({ nodes: p, edges: y }) => {
      const {
          nodeInternals: m,
          getNodes: g,
          edges: w,
          hasDefaultNodes: x,
          hasDefaultEdges: S,
          onNodesDelete: C,
          onEdgesDelete: E,
          onNodesChange: T,
          onEdgesChange: P,
        } = t.getState(),
        N = (p || []).map((O) => O.id),
        I = (y || []).map((O) => O.id),
        V = g().reduce((O, R) => {
          const F = R.parentNode || R.parentId,
            A = !N.includes(R.id) && F && O.find((D) => D.id === F);
          return (
            (typeof R.deletable == "boolean" ? R.deletable : !0) &&
              (N.includes(R.id) || A) &&
              O.push(R),
            O
          );
        }, []),
        q = w.filter((O) => (typeof O.deletable == "boolean" ? O.deletable : !0)),
        b = q.filter((O) => I.includes(O.id));
      if (V || b) {
        const O = SA(V, q),
          R = [...b, ...O],
          F = R.reduce((A, k) => (A.includes(k.id) || A.push(k.id), A), []);
        if (
          ((S || x) &&
            (S && t.setState({ edges: w.filter((A) => !F.includes(A.id)) }),
            x &&
              (V.forEach((A) => {
                m.delete(A.id);
              }),
              t.setState({ nodeInternals: new Map(m) }))),
          F.length > 0 && (E == null || E(R), P && P(F.map((A) => ({ id: A, type: "remove" })))),
          V.length > 0 && (C == null || C(V), T))
        ) {
          const A = V.map((k) => ({ id: k.id, type: "remove" }));
          T(A);
        }
      }
    }, []),
    d = _.useCallback((p) => {
      const y = Oq(p),
        m = y ? null : t.getState().nodeInternals.get(p.id);
      return !y && !m ? [null, null, y] : [y ? p : lx(m), m, y];
    }, []),
    h = _.useCallback((p, y = !0, m) => {
      const [g, w, x] = d(p);
      return g
        ? (m || t.getState().getNodes()).filter((S) => {
            if (!x && (S.id === w.id || !S.positionAbsolute)) return !1;
            const C = lx(S),
              E = Tv(C, g);
            return (y && E > 0) || E >= g.width * g.height;
          })
        : [];
    }, []),
    v = _.useCallback((p, y, m = !0) => {
      const [g] = d(p);
      if (!g) return !1;
      const w = Tv(g, y);
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
    [e, n, r, i, o, s, a, u, l, c, f, h, v]
  );
}
const g$ = { actInsideInputWithModifier: !1 };
var v$ = ({ deleteKeyCode: e, multiSelectionKeyCode: t }) => {
  const n = Fe(),
    { deleteElements: r } = p0(),
    i = Xs(e, g$),
    o = Xs(t);
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
function y$(e) {
  const t = Fe();
  _.useEffect(() => {
    let n;
    const r = () => {
      var o, s;
      if (!e.current) return;
      const i = s0(e.current);
      (i.height === 0 || i.width === 0) &&
        ((s = (o = t.getState()).onError) == null || s.call(o, "004", Gn.error004())),
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
const m0 = { position: "absolute", width: "100%", height: "100%", top: 0, left: 0 },
  w$ = (e, t) => e.x !== t.x || e.y !== t.y || e.zoom !== t.k,
  Ka = (e) => ({ x: e.x, y: e.y, zoom: e.k }),
  _i = (e, t) => e.target.closest(`.${t}`),
  wx = (e, t) => t === 2 && Array.isArray(e) && e.includes(2),
  xx = (e) => {
    const t = e.ctrlKey && ol() ? 10 : 1;
    return -e.deltaY * (e.deltaMode === 1 ? 0.05 : e.deltaMode ? 1 : 0.002) * t;
  },
  x$ = (e) => ({
    d3Zoom: e.d3Zoom,
    d3Selection: e.d3Selection,
    d3ZoomHandler: e.d3ZoomHandler,
    userSelectionActive: e.userSelectionActive,
  }),
  _$ = ({
    onMove: e,
    onMoveStart: t,
    onMoveEnd: n,
    onPaneContextMenu: r,
    zoomOnScroll: i = !0,
    zoomOnPinch: o = !0,
    panOnScroll: s = !1,
    panOnScrollSpeed: a = 0.5,
    panOnScrollMode: u = Kr.Free,
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
    const S = _.useRef(),
      C = Fe(),
      E = _.useRef(!1),
      T = _.useRef(!1),
      P = _.useRef(null),
      N = _.useRef({ x: 0, y: 0, zoom: 0 }),
      { d3Zoom: I, d3Selection: V, d3ZoomHandler: q, userSelectionActive: b } = he(x$, He),
      O = Xs(y),
      R = _.useRef(0),
      F = _.useRef(!1),
      A = _.useRef();
    return (
      y$(P),
      _.useEffect(() => {
        if (P.current) {
          const k = P.current.getBoundingClientRect(),
            D = uA().scaleExtent([v, p]).translateExtent(h),
            j = Ot(P.current).call(D),
            $ = Vn.translate(d.x, d.y).scale(ho(d.zoom, v, p)),
            U = [
              [0, 0],
              [k.width, k.height],
            ],
            B = D.constrain()($, U, h);
          D.transform(j, B),
            D.wheelDelta(xx),
            C.setState({
              d3Zoom: D,
              d3Selection: j,
              d3ZoomHandler: j.on("wheel.zoom"),
              transform: [B.x, B.y, B.k],
              domNode: P.current.closest(".react-flow"),
            });
        }
      }, []),
      _.useEffect(() => {
        V &&
          I &&
          (s && !O && !b
            ? V.on(
                "wheel.zoom",
                (k) => {
                  if (_i(k, w)) return !1;
                  k.preventDefault(), k.stopImmediatePropagation();
                  const D = V.property("__zoom").k || 1;
                  if (k.ctrlKey && o) {
                    const ue = Yt(k),
                      se = xx(k),
                      oe = D * Math.pow(2, se);
                    I.scaleTo(V, oe, ue, k);
                    return;
                  }
                  const j = k.deltaMode === 1 ? 20 : 1;
                  let $ = u === Kr.Vertical ? 0 : k.deltaX * j,
                    U = u === Kr.Horizontal ? 0 : k.deltaY * j;
                  !ol() && k.shiftKey && u !== Kr.Vertical && (($ = k.deltaY * j), (U = 0)),
                    I.translateBy(V, -($ / D) * a, -(U / D) * a, { internal: !0 });
                  const B = Ka(V.property("__zoom")),
                    {
                      onViewportChangeStart: W,
                      onViewportChange: X,
                      onViewportChangeEnd: ee,
                    } = C.getState();
                  clearTimeout(A.current),
                    F.current || ((F.current = !0), t == null || t(k, B), W == null || W(B)),
                    F.current &&
                      (e == null || e(k, B),
                      X == null || X(B),
                      (A.current = setTimeout(() => {
                        n == null || n(k, B), ee == null || ee(B), (F.current = !1);
                      }, 150)));
                },
                { passive: !1 }
              )
            : typeof q < "u" &&
              V.on(
                "wheel.zoom",
                function (k, D) {
                  if ((!m && k.type === "wheel" && !k.ctrlKey) || _i(k, w)) return null;
                  k.preventDefault(), q.call(this, k, D);
                },
                { passive: !1 }
              ));
      }, [b, s, u, V, I, q, O, o, m, w, t, e, n]),
      _.useEffect(() => {
        I &&
          I.on("start", (k) => {
            var $, U;
            if (!k.sourceEvent || k.sourceEvent.internal) return null;
            R.current = ($ = k.sourceEvent) == null ? void 0 : $.button;
            const { onViewportChangeStart: D } = C.getState(),
              j = Ka(k.transform);
            (E.current = !0),
              (N.current = j),
              ((U = k.sourceEvent) == null ? void 0 : U.type) === "mousedown" &&
                C.setState({ paneDragging: !0 }),
              D == null || D(j),
              t == null || t(k.sourceEvent, j);
          });
      }, [I, t]),
      _.useEffect(() => {
        I &&
          (b && !E.current
            ? I.on("zoom", null)
            : b ||
              I.on("zoom", (k) => {
                var j;
                const { onViewportChange: D } = C.getState();
                if (
                  (C.setState({ transform: [k.transform.x, k.transform.y, k.transform.k] }),
                  (T.current = !!(r && wx(f, R.current ?? 0))),
                  (e || D) && !((j = k.sourceEvent) != null && j.internal))
                ) {
                  const $ = Ka(k.transform);
                  D == null || D($), e == null || e(k.sourceEvent, $);
                }
              }));
      }, [b, I, e, f, r]),
      _.useEffect(() => {
        I &&
          I.on("end", (k) => {
            if (!k.sourceEvent || k.sourceEvent.internal) return null;
            const { onViewportChangeEnd: D } = C.getState();
            if (
              ((E.current = !1),
              C.setState({ paneDragging: !1 }),
              r && wx(f, R.current ?? 0) && !T.current && r(k.sourceEvent),
              (T.current = !1),
              (n || D) && w$(N.current, k.transform))
            ) {
              const j = Ka(k.transform);
              (N.current = j),
                clearTimeout(S.current),
                (S.current = setTimeout(
                  () => {
                    D == null || D(j), n == null || n(k.sourceEvent, j);
                  },
                  s ? 150 : 0
                ));
            }
          });
      }, [I, s, f, n, r]),
      _.useEffect(() => {
        I &&
          I.filter((k) => {
            const D = O || i,
              j = o && k.ctrlKey;
            if (
              (f === !0 || (Array.isArray(f) && f.includes(1))) &&
              k.button === 1 &&
              k.type === "mousedown" &&
              (_i(k, "react-flow__node") || _i(k, "react-flow__edge"))
            )
              return !0;
            if (
              (!f && !D && !s && !l && !o) ||
              b ||
              (!l && k.type === "dblclick") ||
              (_i(k, w) && k.type === "wheel") ||
              (_i(k, x) && (k.type !== "wheel" || (s && k.type === "wheel" && !O))) ||
              (!o && k.ctrlKey && k.type === "wheel") ||
              (!D && !s && !j && k.type === "wheel") ||
              (!f && (k.type === "mousedown" || k.type === "touchstart")) ||
              (Array.isArray(f) && !f.includes(k.button) && k.type === "mousedown")
            )
              return !1;
            const $ = (Array.isArray(f) && f.includes(k.button)) || !k.button || k.button <= 1;
            return (!k.ctrlKey || k.type === "wheel") && $;
          });
      }, [b, I, i, o, s, l, f, c, O]),
      L.createElement("div", { className: "react-flow__renderer", ref: P, style: m0 }, g)
    );
  },
  S$ = (e) => ({
    userSelectionActive: e.userSelectionActive,
    userSelectionRect: e.userSelectionRect,
  });
function b$() {
  const { userSelectionActive: e, userSelectionRect: t } = he(S$, He);
  return e && t
    ? L.createElement("div", {
        className: "react-flow__selection react-flow__container",
        style: { width: t.width, height: t.height, transform: `translate(${t.x}px, ${t.y}px)` },
      })
    : null;
}
function _x(e, t) {
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
function E$(e, t) {
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
              s.expandParent && _x(r, s);
            break;
          }
          case "dimensions": {
            typeof a.dimensions < "u" &&
              ((s.width = a.dimensions.width), (s.height = a.dimensions.height)),
              typeof a.updateStyle < "u" && (s.style = { ...(s.style || {}), ...a.dimensions }),
              typeof a.resizing == "boolean" && (s.resizing = a.resizing),
              s.expandParent && _x(r, s);
            break;
          }
          case "remove":
            return r;
        }
    return r.push(s), r;
  }, n);
}
function C$(e, t) {
  return E$(e, t);
}
const cr = (e, t) => ({ id: e, type: "select", selected: t });
function ji(e, t) {
  return e.reduce((n, r) => {
    const i = t.includes(r.id);
    return (
      !r.selected && i
        ? ((r.selected = !0), n.push(cr(r.id, !0)))
        : r.selected && !i && ((r.selected = !1), n.push(cr(r.id, !1))),
      n
    );
  }, []);
}
const rf = (e, t) => (n) => {
    n.target === t.current && (e == null || e(n));
  },
  T$ = (e) => ({
    userSelectionActive: e.userSelectionActive,
    elementsSelectable: e.elementsSelectable,
    dragging: e.paneDragging,
  }),
  jA = _.memo(
    ({
      isSelecting: e,
      selectionMode: t = Ks.Full,
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
        { userSelectionActive: m, elementsSelectable: g, dragging: w } = he(T$, He),
        x = () => {
          h.setState({ userSelectionActive: !1, userSelectionRect: null }),
            (v.current = 0),
            (p.current = 0);
        },
        S = (q) => {
          o == null || o(q),
            h.getState().resetSelectedElements(),
            h.setState({ nodesSelectionActive: !1 });
        },
        C = (q) => {
          if (Array.isArray(n) && n != null && n.includes(2)) {
            q.preventDefault();
            return;
          }
          s == null || s(q);
        },
        E = a ? (q) => a(q) : void 0,
        T = (q) => {
          const { resetSelectedElements: b, domNode: O } = h.getState();
          if (
            ((y.current = O == null ? void 0 : O.getBoundingClientRect()),
            !g || !e || q.button !== 0 || q.target !== d.current || !y.current)
          )
            return;
          const { x: R, y: F } = Cr(q, y.current);
          b(),
            h.setState({
              userSelectionRect: { width: 0, height: 0, startX: R, startY: F, x: R, y: F },
            }),
            r == null || r(q);
        },
        P = (q) => {
          const {
            userSelectionRect: b,
            nodeInternals: O,
            edges: R,
            transform: F,
            onNodesChange: A,
            onEdgesChange: k,
            nodeOrigin: D,
            getNodes: j,
          } = h.getState();
          if (!e || !y.current || !b) return;
          h.setState({ userSelectionActive: !0, nodesSelectionActive: !1 });
          const $ = Cr(q, y.current),
            U = b.startX ?? 0,
            B = b.startY ?? 0,
            W = {
              ...b,
              x: $.x < U ? $.x : U,
              y: $.y < B ? $.y : B,
              width: Math.abs($.x - U),
              height: Math.abs($.y - B),
            },
            X = j(),
            ee = _A(O, W, F, t === Ks.Partial, !0, D),
            ue = SA(ee, R).map((oe) => oe.id),
            se = ee.map((oe) => oe.id);
          if (v.current !== se.length) {
            v.current = se.length;
            const oe = ji(X, se);
            oe.length && (A == null || A(oe));
          }
          if (p.current !== ue.length) {
            p.current = ue.length;
            const oe = ji(R, ue);
            oe.length && (k == null || k(oe));
          }
          h.setState({ userSelectionRect: W });
        },
        N = (q) => {
          if (q.button !== 0) return;
          const { userSelectionRect: b } = h.getState();
          !m && b && q.target === d.current && (S == null || S(q)),
            h.setState({ nodesSelectionActive: v.current > 0 }),
            x(),
            i == null || i(q);
        },
        I = (q) => {
          m && (h.setState({ nodesSelectionActive: v.current > 0 }), i == null || i(q)), x();
        },
        V = g && (e || m);
      return L.createElement(
        "div",
        {
          className: Ze(["react-flow__pane", { dragging: w, selection: e }]),
          onClick: V ? void 0 : rf(S, d),
          onContextMenu: rf(C, d),
          onWheel: rf(E, d),
          onMouseEnter: V ? void 0 : u,
          onMouseDown: V ? T : void 0,
          onMouseMove: V ? P : l,
          onMouseUp: V ? N : void 0,
          onMouseLeave: V ? I : c,
          ref: d,
          style: m0,
        },
        f,
        L.createElement(b$, null)
      );
    }
  );
jA.displayName = "Pane";
function qA(e, t) {
  const n = e.parentNode || e.parentId;
  if (!n) return !1;
  const r = t.get(n);
  return r ? (r.selected ? !0 : qA(r, t)) : !1;
}
function Sx(e, t, n) {
  let r = e;
  do {
    if (r != null && r.matches(t)) return !0;
    if (r === n.current) return !1;
    r = r.parentElement;
  } while (r);
  return !1;
}
function k$(e, t, n, r) {
  return Array.from(e.values())
    .filter(
      (i) =>
        (i.selected || i.id === r) &&
        (!i.parentNode || i.parentId || !qA(i, e)) &&
        (i.draggable || (t && typeof i.draggable > "u"))
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
function P$(e, t) {
  return !t || t === "parent" ? t : [t[0], [t[1][0] - (e.width || 0), t[1][1] - (e.height || 0)]];
}
function $A(e, t, n, r, i = [0, 0], o) {
  const s = P$(e, e.extent || r);
  let a = s;
  const u = e.parentNode || e.parentId;
  if (e.extent === "parent" && !e.expandParent)
    if (u && e.width && e.height) {
      const f = n.get(u),
        { x: d, y: h } = ei(f, i).positionAbsolute;
      a =
        f && Ft(d) && Ft(h) && Ft(f.width) && Ft(f.height)
          ? [
              [d + e.width * i[0], h + e.height * i[1]],
              [d + f.width - e.width + e.width * i[0], h + f.height - e.height + e.height * i[1]],
            ]
          : a;
    } else o == null || o("005", Gn.error005()), (a = s);
  else if (e.extent && u && e.extent !== "parent") {
    const f = n.get(u),
      { x: d, y: h } = ei(f, i).positionAbsolute;
    a = [
      [e.extent[0][0] + d, e.extent[0][1] + h],
      [e.extent[1][0] + d, e.extent[1][1] + h],
    ];
  }
  let l = { x: 0, y: 0 };
  if (u) {
    const f = n.get(u);
    l = ei(f, i).positionAbsolute;
  }
  const c = a && a !== "parent" ? a0(t, a) : t;
  return { position: { x: c.x - l.x, y: c.y - l.y }, positionAbsolute: c };
}
function of({ nodeId: e, dragItems: t, nodeInternals: n }) {
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
      ...s0(u),
    };
  });
};
function Bo(e, t, n) {
  return n === void 0
    ? n
    : (r) => {
        const i = t().nodeInternals.get(e);
        i && n(r, { ...i });
      };
}
function Mv({ id: e, store: t, unselect: n = !1, nodeRef: r }) {
  const {
      addSelectedNodes: i,
      unselectNodesAndEdges: o,
      multiSelectionActive: s,
      nodeInternals: a,
      onError: u,
    } = t.getState(),
    l = a.get(e);
  if (!l) {
    u == null || u("012", Gn.error012(e));
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
function R$() {
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
function sf(e) {
  return (t, n, r) => (e == null ? void 0 : e(t, r));
}
function zA({
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
    w = R$();
  return (
    _.useEffect(() => {
      if (e != null && e.current) {
        const x = Ot(e.current),
          S = ({ x: T, y: P }) => {
            const {
              nodeInternals: N,
              onNodeDrag: I,
              onSelectionDrag: V,
              updateNodePositions: q,
              nodeExtent: b,
              snapGrid: O,
              snapToGrid: R,
              nodeOrigin: F,
              onError: A,
            } = a.getState();
            f.current = { x: T, y: P };
            let k = !1,
              D = { x: 0, y: 0, x2: 0, y2: 0 };
            if (c.current.length > 1 && b) {
              const $ = Ul(c.current, F);
              D = Ws($);
            }
            if (
              ((c.current = c.current.map(($) => {
                const U = { x: T - $.distance.x, y: P - $.distance.y };
                R && ((U.x = O[0] * Math.round(U.x / O[0])), (U.y = O[1] * Math.round(U.y / O[1])));
                const B = [
                  [b[0][0], b[0][1]],
                  [b[1][0], b[1][1]],
                ];
                c.current.length > 1 &&
                  b &&
                  !$.extent &&
                  ((B[0][0] = $.positionAbsolute.x - D.x + b[0][0]),
                  (B[1][0] = $.positionAbsolute.x + ($.width ?? 0) - D.x2 + b[1][0]),
                  (B[0][1] = $.positionAbsolute.y - D.y + b[0][1]),
                  (B[1][1] = $.positionAbsolute.y + ($.height ?? 0) - D.y2 + b[1][1]));
                const W = $A($, U, N, B, F, A);
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
            const j = i ? I : sf(V);
            if (j && p.current) {
              const [$, U] = of({ nodeId: i, dragItems: c.current, nodeInternals: N });
              j(p.current, $, U);
            }
          },
          C = () => {
            if (!h.current) return;
            const [T, P] = cA(v.current, h.current);
            if (T !== 0 || P !== 0) {
              const { transform: N, panBy: I } = a.getState();
              (f.current.x = (f.current.x ?? 0) - T / N[2]),
                (f.current.y = (f.current.y ?? 0) - P / N[2]),
                I({ x: T, y: P }) && S(f.current);
            }
            d.current = requestAnimationFrame(C);
          },
          E = (T) => {
            var F;
            const {
              nodeInternals: P,
              multiSelectionActive: N,
              nodesDraggable: I,
              unselectNodesAndEdges: V,
              onNodeDragStart: q,
              onSelectionDragStart: b,
            } = a.getState();
            m.current = !0;
            const O = i ? q : sf(b);
            (!s || !o) && !N && i && (((F = P.get(i)) != null && F.selected) || V()),
              i && o && s && Mv({ id: i, store: a, nodeRef: e });
            const R = w(T);
            if (((f.current = R), (c.current = k$(P, I, R, i)), O && c.current)) {
              const [A, k] = of({ nodeId: i, dragItems: c.current, nodeInternals: P });
              O(T.sourceEvent, A, k);
            }
          };
        if (t) x.on(".drag", null);
        else {
          const T = jV()
            .on("start", (P) => {
              const { domNode: N, nodeDragThreshold: I } = a.getState();
              I === 0 && E(P), (g.current = !1);
              const V = w(P);
              (f.current = V),
                (h.current = (N == null ? void 0 : N.getBoundingClientRect()) || null),
                (v.current = Cr(P.sourceEvent, h.current));
            })
            .on("drag", (P) => {
              var q, b;
              const N = w(P),
                { autoPanOnNodeDrag: I, nodeDragThreshold: V } = a.getState();
              if (
                (P.sourceEvent.type === "touchmove" &&
                  P.sourceEvent.touches.length > 1 &&
                  (g.current = !0),
                !g.current)
              ) {
                if ((!y.current && m.current && I && ((y.current = !0), C()), !m.current)) {
                  const O =
                      N.xSnapped -
                      (((q = f == null ? void 0 : f.current) == null ? void 0 : q.x) ?? 0),
                    R =
                      N.ySnapped -
                      (((b = f == null ? void 0 : f.current) == null ? void 0 : b.y) ?? 0);
                  Math.sqrt(O * O + R * R) > V && E(P);
                }
                (f.current.x !== N.xSnapped || f.current.y !== N.ySnapped) &&
                  c.current &&
                  m.current &&
                  ((p.current = P.sourceEvent), (v.current = Cr(P.sourceEvent, h.current)), S(N));
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
                    updateNodePositions: N,
                    nodeInternals: I,
                    onNodeDragStop: V,
                    onSelectionDragStop: q,
                  } = a.getState(),
                  b = i ? V : sf(q);
                if ((N(c.current, !1, !1), b)) {
                  const [O, R] = of({ nodeId: i, dragItems: c.current, nodeInternals: I });
                  b(P.sourceEvent, O, R);
                }
              }
            })
            .filter((P) => {
              const N = P.target;
              return !P.button && (!n || !Sx(N, `.${n}`, e)) && (!r || Sx(N, r, e));
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
function BA() {
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
          const { positionAbsolute: x, position: S } = $A(g, w, r, i, void 0, l);
          (g.position = S), (g.positionAbsolute = x);
        }
        return g;
      });
    o(m, !0, !1);
  }, []);
}
const Ji = {
  ArrowUp: { x: 0, y: -1 },
  ArrowDown: { x: 0, y: 1 },
  ArrowLeft: { x: -1, y: 0 },
  ArrowRight: { x: 1, y: 0 },
};
var Uo = (e) => {
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
    isFocusable: S,
    selectNodesOnDrag: C,
    sourcePosition: E,
    targetPosition: T,
    hidden: P,
    resizeObserver: N,
    dragHandle: I,
    zIndex: V,
    isParent: q,
    noDragClassName: b,
    noPanClassName: O,
    initialized: R,
    disableKeyboardA11y: F,
    ariaLabel: A,
    rfId: k,
    hasHandleBounds: D,
  }) => {
    const j = Fe(),
      $ = _.useRef(null),
      U = _.useRef(null),
      B = _.useRef(E),
      W = _.useRef(T),
      X = _.useRef(r),
      ee = w || g || c || f || d || h,
      ue = BA(),
      se = Bo(n, j.getState, f),
      oe = Bo(n, j.getState, d),
      De = Bo(n, j.getState, h),
      Pe = Bo(n, j.getState, v),
      Ge = Bo(n, j.getState, p),
      Ve = (K) => {
        const { nodeDragThreshold: G } = j.getState();
        if ((w && (!C || !g || G > 0) && Mv({ id: n, store: j, nodeRef: $ }), c)) {
          const be = j.getState().nodeInternals.get(n);
          be && c(K, { ...be });
        }
      },
      Q = (K) => {
        if (!kv(K) && !F)
          if (pA.includes(K.key) && w) {
            const G = K.key === "Escape";
            Mv({ id: n, store: j, unselect: G, nodeRef: $ });
          } else
            g &&
              l &&
              Object.prototype.hasOwnProperty.call(Ji, K.key) &&
              (j.setState({
                ariaLiveMessage: `Moved selected node ${K.key
                  .replace("Arrow", "")
                  .toLowerCase()}. New position, x: ${~~o}, y: ${~~s}`,
              }),
              ue({ x: Ji[K.key].x, y: Ji[K.key].y, isShiftPressed: K.shiftKey }));
      };
    _.useEffect(
      () => () => {
        U.current && (N == null || N.unobserve(U.current), (U.current = null));
      },
      []
    ),
      _.useEffect(() => {
        if ($.current && !P) {
          const K = $.current;
          (!R || !D || U.current !== K) &&
            (U.current && (N == null || N.unobserve(U.current)),
            N == null || N.observe(K),
            (U.current = K));
        }
      }, [P, R, D]),
      _.useEffect(() => {
        const K = X.current !== r,
          G = B.current !== E,
          be = W.current !== T;
        $.current &&
          (K || G || be) &&
          (K && (X.current = r),
          G && (B.current = E),
          be && (W.current = T),
          j.getState().updateNodeDimensions([{ id: n, nodeElement: $.current, forceUpdate: !0 }]));
      }, [n, r, E, T]);
    const je = zA({
      nodeRef: $,
      disabled: P || !g,
      noDragClassName: b,
      handleSelector: I,
      nodeId: n,
      isSelectable: w,
      selectNodesOnDrag: C,
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
              { selected: l, selectable: w, parent: q, dragging: je },
            ]),
            ref: $,
            style: {
              zIndex: V,
              transform: `translate(${a}px,${u}px)`,
              pointerEvents: ee ? "all" : "none",
              visibility: R ? "visible" : "hidden",
              ...y,
            },
            "data-id": n,
            "data-testid": `rf__node-${n}`,
            onMouseEnter: se,
            onMouseMove: oe,
            onMouseLeave: De,
            onContextMenu: Pe,
            onClick: Ve,
            onDoubleClick: Ge,
            onKeyDown: S ? Q : void 0,
            tabIndex: S ? 0 : void 0,
            role: S ? "button" : void 0,
            "aria-describedby": F ? void 0 : `${DA}-${k}`,
            "aria-label": A,
          },
          L.createElement(
            zq,
            { value: n },
            L.createElement(e, {
              id: n,
              data: i,
              type: r,
              xPos: o,
              yPos: s,
              selected: l,
              isConnectable: x,
              sourcePosition: E,
              targetPosition: T,
              dragging: je,
              dragHandle: I,
              zIndex: V,
            })
          )
        );
  };
  return (t.displayName = "NodeWrapper"), _.memo(t);
};
const A$ = (e) => {
  const t = e.getNodes().filter((n) => n.selected);
  return {
    ...Ul(t, e.nodeOrigin),
    transformString: `translate(${e.transform[0]}px,${e.transform[1]}px) scale(${e.transform[2]})`,
    userSelectionActive: e.userSelectionActive,
  };
};
function N$({ onSelectionContextMenu: e, noPanClassName: t, disableKeyboardA11y: n }) {
  const r = Fe(),
    { width: i, height: o, x: s, y: a, transformString: u, userSelectionActive: l } = he(A$, He),
    c = BA(),
    f = _.useRef(null);
  if (
    (_.useEffect(() => {
      var v;
      n || (v = f.current) == null || v.focus({ preventScroll: !0 });
    }, [n]),
    zA({ nodeRef: f }),
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
      Object.prototype.hasOwnProperty.call(Ji, v.key) &&
        c({ x: Ji[v.key].x, y: Ji[v.key].y, isShiftPressed: v.shiftKey });
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
    })
  );
}
var M$ = _.memo(N$);
const I$ = (e) => e.nodesSelectionActive,
  UA = ({
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
    zoomOnPinch: S,
    panOnScroll: C,
    panOnScrollSpeed: E,
    panOnScrollMode: T,
    zoomOnDoubleClick: P,
    panOnDrag: N,
    defaultViewport: I,
    translateExtent: V,
    minZoom: q,
    maxZoom: b,
    preventScrolling: O,
    onSelectionContextMenu: R,
    noWheelClassName: F,
    noPanClassName: A,
    disableKeyboardA11y: k,
  }) => {
    const D = he(I$),
      j = Xs(f),
      $ = Xs(m),
      U = $ || N,
      B = $ || C,
      W = j || (d && U !== !0);
    return (
      v$({ deleteKeyCode: a, multiSelectionKeyCode: y }),
      L.createElement(
        _$,
        {
          onMove: u,
          onMoveStart: l,
          onMoveEnd: c,
          onPaneContextMenu: o,
          elementsSelectable: w,
          zoomOnScroll: x,
          zoomOnPinch: S,
          panOnScroll: B,
          panOnScrollSpeed: E,
          panOnScrollMode: T,
          zoomOnDoubleClick: P,
          panOnDrag: !j && U,
          defaultViewport: I,
          translateExtent: V,
          minZoom: q,
          maxZoom: b,
          zoomActivationKeyCode: g,
          preventScrolling: O,
          noWheelClassName: F,
          noPanClassName: A,
        },
        L.createElement(
          jA,
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
            L.createElement(M$, {
              onSelectionContextMenu: R,
              noPanClassName: A,
              disableKeyboardA11y: k,
            })
        )
      )
    );
  };
UA.displayName = "FlowRenderer";
var D$ = _.memo(UA);
function O$(e) {
  return he(
    _.useCallback(
      (n) =>
        e
          ? _A(n.nodeInternals, { x: 0, y: 0, width: n.width, height: n.height }, n.transform, !0)
          : n.getNodes(),
      [e]
    )
  );
}
function L$(e) {
  const t = {
      input: Uo(e.input || AA),
      default: Uo(e.default || Nv),
      output: Uo(e.output || MA),
      group: Uo(e.group || h0),
    },
    n = {},
    r = Object.keys(e)
      .filter((i) => !["input", "default", "output", "group"].includes(i))
      .reduce((i, o) => ((i[o] = Uo(e[o] || Nv)), i), n);
  return { ...t, ...r };
}
const F$ = ({ x: e, y: t, width: n, height: r, origin: i }) =>
    !n || !r
      ? { x: e, y: t }
      : i[0] < 0 || i[1] < 0 || i[0] > 1 || i[1] > 1
      ? { x: e, y: t }
      : { x: e - n * i[0], y: t - r * i[1] },
  V$ = (e) => ({
    nodesDraggable: e.nodesDraggable,
    nodesConnectable: e.nodesConnectable,
    nodesFocusable: e.nodesFocusable,
    elementsSelectable: e.elementsSelectable,
    updateNodeDimensions: e.updateNodeDimensions,
    onError: e.onError,
  }),
  HA = (e) => {
    const {
        nodesDraggable: t,
        nodesConnectable: n,
        nodesFocusable: r,
        elementsSelectable: i,
        updateNodeDimensions: o,
        onError: s,
      } = he(V$, He),
      a = O$(e.onlyRenderVisibleElements),
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
        []
      ),
      L.createElement(
        "div",
        { className: "react-flow__nodes", style: m0 },
        a.map((c) => {
          var S, C, E;
          let f = c.type || "default";
          e.nodeTypes[f] || (s == null || s("003", Gn.error003(f)), (f = "default"));
          const d = e.nodeTypes[f] || e.nodeTypes.default,
            h = !!(c.draggable || (t && typeof c.draggable > "u")),
            v = !!(c.selectable || (i && typeof c.selectable > "u")),
            p = !!(c.connectable || (n && typeof c.connectable > "u")),
            y = !!(c.focusable || (r && typeof c.focusable > "u")),
            m = e.nodeExtent ? a0(c.positionAbsolute, e.nodeExtent) : c.positionAbsolute,
            g = (m == null ? void 0 : m.x) ?? 0,
            w = (m == null ? void 0 : m.y) ?? 0,
            x = F$({
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
            zIndex: ((S = c[Te]) == null ? void 0 : S.z) ?? 0,
            isParent: !!((C = c[Te]) != null && C.isParent),
            noDragClassName: e.noDragClassName,
            noPanClassName: e.noPanClassName,
            initialized: !!c.width && !!c.height,
            rfId: e.rfId,
            disableKeyboardA11y: e.disableKeyboardA11y,
            ariaLabel: c.ariaLabel,
            hasHandleBounds: !!((E = c[Te]) != null && E.handleBounds),
          });
        })
      )
    );
  };
HA.displayName = "NodeRenderer";
var j$ = _.memo(HA);
const q$ = (e, t, n) => (n === Y.Left ? e - t : n === Y.Right ? e + t : e),
  $$ = (e, t, n) => (n === Y.Top ? e - t : n === Y.Bottom ? e + t : e),
  Ex = "react-flow__edgeupdater",
  Cx = ({
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
      className: Ze([Ex, `${Ex}-${a}`]),
      cx: q$(t, r, e),
      cy: $$(n, r, e),
      r,
      stroke: "transparent",
      fill: "transparent",
    }),
  z$ = () => !0;
var Si = (e) => {
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
    targetX: S,
    targetY: C,
    sourcePosition: E,
    targetPosition: T,
    elementsSelectable: P,
    hidden: N,
    sourceHandleId: I,
    targetHandleId: V,
    onContextMenu: q,
    onMouseEnter: b,
    onMouseMove: O,
    onMouseLeave: R,
    reconnectRadius: F,
    onReconnect: A,
    onReconnectStart: k,
    onReconnectEnd: D,
    markerEnd: j,
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
      [De, Pe] = _.useState(!1),
      [Ge, Ve] = _.useState(!1),
      Q = Fe(),
      je = _.useMemo(() => `url('#${Rv($, U)}')`, [$, U]),
      K = _.useMemo(() => `url('#${Rv(j, U)}')`, [j, U]);
    if (N) return null;
    const G = (qe) => {
        var ln;
        const {
            edges: dt,
            addSelectedEdges: Qe,
            unselectNodesAndEdges: ot,
            multiSelectionActive: Lr,
          } = Q.getState(),
          Tn = dt.find((Ao) => Ao.id === n);
        Tn &&
          (P &&
            (Q.setState({ nodesSelectionActive: !1 }),
            Tn.selected && Lr
              ? (ot({ nodes: [], edges: [Tn] }), (ln = oe.current) == null || ln.blur())
              : Qe([n])),
          s && s(qe, Tn));
      },
      be = zo(n, Q.getState, a),
      Bt = zo(n, Q.getState, q),
      an = zo(n, Q.getState, b),
      it = zo(n, Q.getState, O),
      Re = zo(n, Q.getState, R),
      ft = (qe, dt) => {
        if (qe.button !== 0) return;
        const { edges: Qe, isValidConnection: ot } = Q.getState(),
          Lr = dt ? g : m,
          Tn = (dt ? V : I) || null,
          ln = dt ? "target" : "source",
          Ao = ot || z$,
          _c = dt,
          No = Qe.find((Fr) => Fr.id === n);
        Ve(!0), k == null || k(qe, No, ln);
        const Sc = (Fr) => {
          Ve(!1), D == null || D(Fr, No, ln);
        };
        TA({
          event: qe,
          handleId: Tn,
          nodeId: Lr,
          onConnect: (Fr) => (A == null ? void 0 : A(No, Fr)),
          isTarget: _c,
          getState: Q.getState,
          setState: Q.setState,
          isValidConnection: Ao,
          edgeUpdaterType: ln,
          onReconnectEnd: Sc,
        });
      },
      Ut = (qe) => ft(qe, !0),
      En = (qe) => ft(qe, !1),
      un = () => Pe(!0),
      xt = () => Pe(!1),
      Cn = !P && !s,
      Jn = (qe) => {
        var dt;
        if (!se && pA.includes(qe.key) && P) {
          const { unselectNodesAndEdges: Qe, addSelectedEdges: ot, edges: Lr } = Q.getState();
          qe.key === "Escape"
            ? ((dt = oe.current) == null || dt.blur(),
              Qe({ edges: [Lr.find((ln) => ln.id === n)] }))
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
          { selected: u, animated: l, inactive: Cn, updating: De },
        ]),
        onClick: G,
        onDoubleClick: be,
        onContextMenu: Bt,
        onMouseEnter: an,
        onMouseMove: it,
        onMouseLeave: Re,
        onKeyDown: W ? Jn : void 0,
        tabIndex: W ? 0 : void 0,
        role: W ? "button" : "img",
        "data-testid": `rf__edge-${n}`,
        "aria-label": B === null ? void 0 : B || `Edge from ${m} to ${g}`,
        "aria-describedby": W ? `${OA}-${U}` : void 0,
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
          targetX: S,
          targetY: C,
          sourcePosition: E,
          targetPosition: T,
          sourceHandleId: I,
          targetHandleId: V,
          markerStart: je,
          markerEnd: K,
          pathOptions: ee,
          interactionWidth: ue,
        }),
      X &&
        L.createElement(
          L.Fragment,
          null,
          (X === "source" || X === !0) &&
            L.createElement(Cx, {
              position: E,
              centerX: w,
              centerY: x,
              radius: F,
              onMouseDown: Ut,
              onMouseEnter: un,
              onMouseOut: xt,
              type: "source",
            }),
          (X === "target" || X === !0) &&
            L.createElement(Cx, {
              position: T,
              centerX: S,
              centerY: C,
              radius: F,
              onMouseDown: En,
              onMouseEnter: un,
              onMouseOut: xt,
              type: "target",
            })
        )
    );
  };
  return (t.displayName = "EdgeWrapper"), _.memo(t);
};
function B$(e) {
  const t = {
      default: Si(e.default || sl),
      straight: Si(e.bezier || c0),
      step: Si(e.step || l0),
      smoothstep: Si(e.step || Bl),
      simplebezier: Si(e.simplebezier || u0),
    },
    n = {},
    r = Object.keys(e)
      .filter((i) => !["default", "bezier"].includes(i))
      .reduce((i, o) => ((i[o] = Si(e[o] || sl)), i), n);
  return { ...t, ...r };
}
function Tx(e, t, n = null) {
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
function kx(e, t) {
  return e ? (e.length === 1 || !t ? e[0] : (t && e.find((n) => n.id === t)) || null) : null;
}
const U$ = (e, t, n, r, i, o) => {
  const s = Tx(n, e, t),
    a = Tx(o, r, i);
  return { sourceX: s.x, sourceY: s.y, targetX: a.x, targetY: a.y };
};
function H$({
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
  const c = Ws({ x: (0 - u[0]) / u[2], y: (0 - u[1]) / u[2], width: s / u[2], height: a / u[2] }),
    f = Math.max(0, Math.min(c.x2, l.x2) - Math.max(c.x, l.x)),
    d = Math.max(0, Math.min(c.y2, l.y2) - Math.max(c.y, l.y));
  return Math.ceil(f * d) > 0;
}
function Px(e) {
  var r, i, o, s, a;
  const t = ((r = e == null ? void 0 : e[Te]) == null ? void 0 : r.handleBounds) || null,
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
const G$ = [{ level: 0, isMaxLevel: !0, edges: [] }];
function W$(e, t, n = !1) {
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
            ((c = h == null ? void 0 : h[Te]) == null ? void 0 : c.z) || 0,
            ((f = d == null ? void 0 : d[Te]) == null ? void 0 : f.z) || 0,
            1e3
          );
        l = (u ? a.zIndex : 0) + (v ? p : 0);
      }
      return s[l] ? s[l].push(a) : (s[l] = [a]), (r = l > r ? l : r), s;
    }, {}),
    o = Object.entries(i).map(([s, a]) => {
      const u = +s;
      return { edges: a, level: u, isMaxLevel: u === r };
    });
  return o.length === 0 ? G$ : o;
}
function K$(e, t, n) {
  const r = he(
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
                H$({
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
      [e, t]
    )
  );
  return W$(r, t, n);
}
const Y$ = ({ color: e = "none", strokeWidth: t = 1 }) =>
    L.createElement("polyline", {
      style: { stroke: e, strokeWidth: t },
      strokeLinecap: "round",
      strokeLinejoin: "round",
      fill: "none",
      points: "-5,-4 0,0 -5,4",
    }),
  X$ = ({ color: e = "none", strokeWidth: t = 1 }) =>
    L.createElement("polyline", {
      style: { stroke: e, fill: e, strokeWidth: t },
      strokeLinecap: "round",
      strokeLinejoin: "round",
      points: "-5,-4 0,0 -5,4 -5,-4",
    }),
  Rx = { [Ys.Arrow]: Y$, [Ys.ArrowClosed]: X$ };
function Z$(e) {
  const t = Fe();
  return _.useMemo(() => {
    var i, o;
    return Object.prototype.hasOwnProperty.call(Rx, e)
      ? Rx[e]
      : ((o = (i = t.getState()).onError) == null || o.call(i, "009", Gn.error009(e)), null);
  }, [e]);
}
const Q$ = ({
    id: e,
    type: t,
    color: n,
    width: r = 12.5,
    height: i = 12.5,
    markerUnits: o = "strokeWidth",
    strokeWidth: s,
    orient: a = "auto-start-reverse",
  }) => {
    const u = Z$(t);
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
          L.createElement(u, { color: n, strokeWidth: s })
        )
      : null;
  },
  J$ = ({ defaultColor: e, rfId: t }) => (n) => {
    const r = [];
    return n.edges
      .reduce(
        (i, o) => (
          [o.markerStart, o.markerEnd].forEach((s) => {
            if (s && typeof s == "object") {
              const a = Rv(s, t);
              r.includes(a) || (i.push({ id: a, color: s.color || e, ...s }), r.push(a));
            }
          }),
          i
        ),
        []
      )
      .sort((i, o) => i.id.localeCompare(o.id));
  },
  GA = ({ defaultColor: e, rfId: t }) => {
    const n = he(
      _.useCallback(J$({ defaultColor: e, rfId: t }), [e, t]),
      (r, i) => !(r.length !== i.length || r.some((o, s) => o.id !== i[s].id))
    );
    return L.createElement(
      "defs",
      null,
      n.map((r) =>
        L.createElement(Q$, {
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
GA.displayName = "MarkerDefinitions";
var ez = _.memo(GA);
const tz = (e) => ({
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
  WA = ({
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
        width: S,
        height: C,
        connectionMode: E,
        nodeInternals: T,
        onError: P,
      } = he(tz, He),
      N = K$(t, T, n);
    return S
      ? L.createElement(
          L.Fragment,
          null,
          N.map(({ level: I, edges: V, isMaxLevel: q }) =>
            L.createElement(
              "svg",
              {
                key: I,
                style: { zIndex: I },
                width: S,
                height: C,
                className: "react-flow__edges react-flow__container",
              },
              q && L.createElement(ez, { defaultColor: e, rfId: r }),
              L.createElement(
                "g",
                null,
                V.map((b) => {
                  const [O, R, F] = Px(T.get(b.source)),
                    [A, k, D] = Px(T.get(b.target));
                  if (!F || !D) return null;
                  let j = b.type || "default";
                  i[j] || (P == null || P("011", Gn.error011(j)), (j = "default"));
                  const $ = i[j] || i.default,
                    U = E === ui.Strict ? k.target : (k.target ?? []).concat(k.source ?? []),
                    B = kx(R.source, b.sourceHandle),
                    W = kx(U, b.targetHandle),
                    X = (B == null ? void 0 : B.position) || Y.Bottom,
                    ee = (W == null ? void 0 : W.position) || Y.Top,
                    ue = !!(b.focusable || (g && typeof b.focusable > "u")),
                    se = b.reconnectable || b.updatable,
                    oe = typeof d < "u" && (se || (w && typeof se > "u"));
                  if (!B || !W) return P == null || P("008", Gn.error008(B, b)), null;
                  const { sourceX: De, sourceY: Pe, targetX: Ge, targetY: Ve } = U$(
                    O,
                    B,
                    X,
                    A,
                    W,
                    ee
                  );
                  return L.createElement($, {
                    key: b.id,
                    id: b.id,
                    className: Ze([b.className, o]),
                    type: j,
                    data: b.data,
                    selected: !!b.selected,
                    animated: !!b.animated,
                    hidden: !!b.hidden,
                    label: b.label,
                    labelStyle: b.labelStyle,
                    labelShowBg: b.labelShowBg,
                    labelBgStyle: b.labelBgStyle,
                    labelBgPadding: b.labelBgPadding,
                    labelBgBorderRadius: b.labelBgBorderRadius,
                    style: b.style,
                    source: b.source,
                    target: b.target,
                    sourceHandleId: b.sourceHandle,
                    targetHandleId: b.targetHandle,
                    markerEnd: b.markerEnd,
                    markerStart: b.markerStart,
                    sourceX: De,
                    sourceY: Pe,
                    targetX: Ge,
                    targetY: Ve,
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
                    ariaLabel: b.ariaLabel,
                    isFocusable: ue,
                    isReconnectable: oe,
                    pathOptions: "pathOptions" in b ? b.pathOptions : void 0,
                    interactionWidth: b.interactionWidth,
                    disableKeyboardA11y: m,
                  });
                })
              )
            )
          ),
          y
        )
      : null;
  };
WA.displayName = "EdgeRenderer";
var nz = _.memo(WA);
const rz = (e) => `translate(${e.transform[0]}px,${e.transform[1]}px) scale(${e.transform[2]})`;
function iz({ children: e }) {
  const t = he(rz);
  return L.createElement(
    "div",
    { className: "react-flow__viewport react-flow__container", style: { transform: t } },
    e
  );
}
function oz(e) {
  const t = p0(),
    n = _.useRef(!1);
  _.useEffect(() => {
    !n.current && t.viewportInitialized && e && (setTimeout(() => e(t), 1), (n.current = !0));
  }, [e, t.viewportInitialized]);
}
const sz = { [Y.Left]: Y.Right, [Y.Right]: Y.Left, [Y.Top]: Y.Bottom, [Y.Bottom]: Y.Top },
  KA = ({
    nodeId: e,
    handleType: t,
    style: n,
    type: r = hr.Bezier,
    CustomComponent: i,
    connectionStatus: o,
  }) => {
    var C, E, T;
    const { fromNode: s, handleId: a, toX: u, toY: l, connectionMode: c } = he(
        _.useCallback(
          (P) => ({
            fromNode: P.nodeInternals.get(e),
            handleId: P.connectionHandleId,
            toX: (P.connectionPosition.x - P.transform[0]) / P.transform[2],
            toY: (P.connectionPosition.y - P.transform[1]) / P.transform[2],
            connectionMode: P.connectionMode,
          }),
          [e]
        ),
        He
      ),
      f = (C = s == null ? void 0 : s[Te]) == null ? void 0 : C.handleBounds;
    let d = f == null ? void 0 : f[t];
    if (
      (c === ui.Loose && (d = d || (f == null ? void 0 : f[t === "source" ? "target" : "source"])),
      !s || !d)
    )
      return null;
    const h = a ? d.find((P) => P.id === a) : d[0],
      v = h ? h.x + h.width / 2 : (s.width ?? 0) / 2,
      p = h ? h.y + h.height / 2 : s.height ?? 0,
      y = (((E = s.positionAbsolute) == null ? void 0 : E.x) ?? 0) + v,
      m = (((T = s.positionAbsolute) == null ? void 0 : T.y) ?? 0) + p,
      g = h == null ? void 0 : h.position,
      w = g ? sz[g] : null;
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
    const S = {
      sourceX: y,
      sourceY: m,
      sourcePosition: g,
      targetX: u,
      targetY: l,
      targetPosition: w,
    };
    return (
      r === hr.Bezier
        ? ([x] = wA(S))
        : r === hr.Step
        ? ([x] = Pv({ ...S, borderRadius: 0 }))
        : r === hr.SmoothStep
        ? ([x] = Pv(S))
        : r === hr.SimpleBezier
        ? ([x] = yA(S))
        : (x = `M${y},${m} ${u},${l}`),
      L.createElement("path", {
        d: x,
        fill: "none",
        className: "react-flow__connection-path",
        style: n,
      })
    );
  };
KA.displayName = "ConnectionLine";
const az = (e) => ({
  nodeId: e.connectionNodeId,
  handleType: e.connectionHandleType,
  nodesConnectable: e.nodesConnectable,
  connectionStatus: e.connectionStatus,
  width: e.width,
  height: e.height,
});
function uz({ containerStyle: e, style: t, type: n, component: r }) {
  const {
    nodeId: i,
    handleType: o,
    nodesConnectable: s,
    width: a,
    height: u,
    connectionStatus: l,
  } = he(az, He);
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
          L.createElement(KA, {
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
function Ax(e, t) {
  return _.useRef(null), Fe(), _.useMemo(() => t(e), [e]);
}
const YA = ({
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
  selectionKeyCode: S,
  selectionOnDrag: C,
  selectionMode: E,
  multiSelectionKeyCode: T,
  panActivationKeyCode: P,
  zoomActivationKeyCode: N,
  deleteKeyCode: I,
  onlyRenderVisibleElements: V,
  elementsSelectable: q,
  selectNodesOnDrag: b,
  defaultViewport: O,
  translateExtent: R,
  minZoom: F,
  maxZoom: A,
  preventScrolling: k,
  defaultMarkerColor: D,
  zoomOnScroll: j,
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
  onPaneScroll: Pe,
  onPaneContextMenu: Ge,
  onEdgeContextMenu: Ve,
  onEdgeMouseEnter: Q,
  onEdgeMouseMove: je,
  onEdgeMouseLeave: K,
  onReconnect: G,
  onReconnectStart: be,
  onReconnectEnd: Bt,
  reconnectRadius: an,
  noDragClassName: it,
  noWheelClassName: Re,
  noPanClassName: ft,
  elevateEdgesOnSelect: Ut,
  disableKeyboardA11y: En,
  nodeOrigin: un,
  nodeExtent: xt,
  rfId: Cn,
}) => {
  const Jn = Ax(e, L$),
    qe = Ax(t, B$);
  return (
    oz(o),
    L.createElement(
      D$,
      {
        onPaneClick: ue,
        onPaneMouseEnter: se,
        onPaneMouseMove: oe,
        onPaneMouseLeave: De,
        onPaneContextMenu: Ge,
        onPaneScroll: Pe,
        deleteKeyCode: I,
        selectionKeyCode: S,
        selectionOnDrag: C,
        selectionMode: E,
        onSelectionStart: p,
        onSelectionEnd: y,
        multiSelectionKeyCode: T,
        panActivationKeyCode: P,
        zoomActivationKeyCode: N,
        elementsSelectable: q,
        onMove: n,
        onMoveStart: r,
        onMoveEnd: i,
        zoomOnScroll: j,
        zoomOnPinch: $,
        zoomOnDoubleClick: X,
        panOnScroll: U,
        panOnScrollSpeed: B,
        panOnScrollMode: W,
        panOnDrag: ee,
        defaultViewport: O,
        translateExtent: R,
        minZoom: F,
        maxZoom: A,
        onSelectionContextMenu: v,
        preventScrolling: k,
        noDragClassName: it,
        noWheelClassName: Re,
        noPanClassName: ft,
        disableKeyboardA11y: En,
      },
      L.createElement(
        iz,
        null,
        L.createElement(
          nz,
          {
            edgeTypes: qe,
            onEdgeClick: a,
            onEdgeDoubleClick: l,
            onlyRenderVisibleElements: V,
            onEdgeContextMenu: Ve,
            onEdgeMouseEnter: Q,
            onEdgeMouseMove: je,
            onEdgeMouseLeave: K,
            onReconnect: G,
            onReconnectStart: be,
            onReconnectEnd: Bt,
            reconnectRadius: an,
            defaultMarkerColor: D,
            noPanClassName: ft,
            elevateEdgesOnSelect: !!Ut,
            disableKeyboardA11y: En,
            rfId: Cn,
          },
          L.createElement(uz, { style: g, type: m, component: w, containerStyle: x })
        ),
        L.createElement("div", { className: "react-flow__edgelabel-renderer" }),
        L.createElement(j$, {
          nodeTypes: Jn,
          onNodeClick: s,
          onNodeDoubleClick: u,
          onNodeMouseEnter: c,
          onNodeMouseMove: f,
          onNodeMouseLeave: d,
          onNodeContextMenu: h,
          selectNodesOnDrag: b,
          onlyRenderVisibleElements: V,
          noPanClassName: ft,
          noDragClassName: it,
          disableKeyboardA11y: En,
          nodeOrigin: un,
          nodeExtent: xt,
          rfId: Cn,
        })
      )
    )
  );
};
YA.displayName = "GraphView";
var lz = _.memo(YA);
const Iv = [
    [Number.NEGATIVE_INFINITY, Number.NEGATIVE_INFINITY],
    [Number.POSITIVE_INFINITY, Number.POSITIVE_INFINITY],
  ],
  tr = {
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
    translateExtent: Iv,
    nodeExtent: Iv,
    nodesSelectionActive: !1,
    userSelectionActive: !1,
    userSelectionRect: null,
    connectionNodeId: null,
    connectionHandleId: null,
    connectionHandleType: "source",
    connectionPosition: { x: 0, y: 0 },
    connectionStatus: null,
    connectionMode: ui.Strict,
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
    onError: Lq,
    isValidConnection: void 0,
  },
  cz = () =>
    ZF(
      (e, t) => ({
        ...tr,
        setNodes: (n) => {
          const { nodeInternals: r, nodeOrigin: i, elevateNodesOnSelect: o } = t();
          e({ nodeInternals: nf(n, r, i, o) });
        },
        getNodes: () => Array.from(t().nodeInternals.values()),
        setEdges: (n) => {
          const { defaultEdgeOptions: r = {} } = t();
          e({ edges: n.map((i) => ({ ...r, ...i })) });
        },
        setDefaultNodesAndEdges: (n, r) => {
          const i = typeof n < "u",
            o = typeof r < "u",
            s = i ? nf(n, new Map(), t().nodeOrigin, t().elevateNodesOnSelect) : new Map();
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
                i.set(m.id, { ...m, [Te]: { ...m[Te], handleBounds: void 0 } });
              else if (m) {
                const g = s0(y.nodeElement);
                !!(
                  g.width &&
                  g.height &&
                  (m.width !== g.width || m.height !== g.height || y.forceUpdate)
                ) &&
                  (i.set(m.id, {
                    ...m,
                    [Te]: {
                      ...m[Te],
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
          FA(i, l);
          const v = s || (o && !s && VA(t, { initial: !0, ...a }));
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
              const l = C$(n, a()),
                c = nf(l, i, s, u);
              e({ nodeInternals: c });
            }
            r == null || r(n);
          }
        },
        addSelectedNodes: (n) => {
          const { multiSelectionActive: r, edges: i, getNodes: o } = t();
          let s,
            a = null;
          r ? (s = n.map((u) => cr(u, !0))) : ((s = ji(o(), n)), (a = ji(i, []))),
            Wa({ changedNodes: s, changedEdges: a, get: t, set: e });
        },
        addSelectedEdges: (n) => {
          const { multiSelectionActive: r, edges: i, getNodes: o } = t();
          let s,
            a = null;
          r ? (s = n.map((u) => cr(u, !0))) : ((s = ji(i, n)), (a = ji(o(), []))),
            Wa({ changedNodes: a, changedEdges: s, get: t, set: e });
        },
        unselectNodesAndEdges: ({ nodes: n, edges: r } = {}) => {
          const { edges: i, getNodes: o } = t(),
            s = n || o(),
            a = r || i,
            u = s.map((c) => ((c.selected = !1), cr(c.id, !1))),
            l = a.map((c) => cr(c.id, !1));
          Wa({ changedNodes: u, changedEdges: l, get: t, set: e });
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
              .map((a) => cr(a.id, !1)),
            s = n.filter((a) => a.selected).map((a) => cr(a.id, !1));
          Wa({ changedNodes: o, changedEdges: s, get: t, set: e });
        },
        setNodeExtent: (n) => {
          const { nodeInternals: r } = t();
          r.forEach((i) => {
            i.positionAbsolute = a0(i.position, n);
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
          const l = Vn.translate(r[0] + n.x, r[1] + n.y).scale(r[2]),
            c = [
              [0, 0],
              [i, o],
            ],
            f = s == null ? void 0 : s.constrain()(l, c, u);
          return s.transform(a, f), r[0] !== f.x || r[1] !== f.y || r[2] !== f.k;
        },
        cancelConnection: () =>
          e({
            connectionNodeId: tr.connectionNodeId,
            connectionHandleId: tr.connectionHandleId,
            connectionHandleType: tr.connectionHandleType,
            connectionStatus: tr.connectionStatus,
            connectionStartHandle: tr.connectionStartHandle,
            connectionEndHandle: tr.connectionEndHandle,
          }),
        reset: () => e({ ...tr }),
      }),
      Object.is
    ),
  XA = ({ children: e }) => {
    const t = _.useRef(null);
    return t.current || (t.current = cz()), L.createElement(Rq, { value: t.current }, e);
  };
XA.displayName = "ReactFlowProvider";
const ZA = ({ children: e }) =>
  _.useContext(zl) ? L.createElement(L.Fragment, null, e) : L.createElement(XA, null, e);
ZA.displayName = "ReactFlowWrapper";
const fz = { input: AA, default: Nv, output: MA, group: h0 },
  dz = { default: sl, straight: c0, step: l0, smoothstep: Bl, simplebezier: u0 },
  hz = [0, 0],
  pz = [15, 15],
  mz = { x: 0, y: 0, zoom: 1 },
  gz = { width: "100%", height: "100%", overflow: "hidden", position: "relative", zIndex: 0 },
  QA = _.forwardRef(
    (
      {
        nodes: e,
        edges: t,
        defaultNodes: n,
        defaultEdges: r,
        className: i,
        nodeTypes: o = fz,
        edgeTypes: s = dz,
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
        onNodeContextMenu: S,
        onNodeDoubleClick: C,
        onNodeDragStart: E,
        onNodeDrag: T,
        onNodeDragStop: P,
        onNodesDelete: N,
        onEdgesDelete: I,
        onSelectionChange: V,
        onSelectionDragStart: q,
        onSelectionDrag: b,
        onSelectionDragStop: O,
        onSelectionContextMenu: R,
        onSelectionStart: F,
        onSelectionEnd: A,
        connectionMode: k = ui.Strict,
        connectionLineType: D = hr.Bezier,
        connectionLineStyle: j,
        connectionLineComponent: $,
        connectionLineContainerStyle: U,
        deleteKeyCode: B = "Backspace",
        selectionKeyCode: W = "Shift",
        selectionOnDrag: X = !1,
        selectionMode: ee = Ks.Full,
        panActivationKeyCode: ue = "Space",
        multiSelectionKeyCode: se = ol() ? "Meta" : "Control",
        zoomActivationKeyCode: oe = ol() ? "Meta" : "Control",
        snapToGrid: De = !1,
        snapGrid: Pe = pz,
        onlyRenderVisibleElements: Ge = !1,
        selectNodesOnDrag: Ve = !0,
        nodesDraggable: Q,
        nodesConnectable: je,
        nodesFocusable: K,
        nodeOrigin: G = hz,
        edgesFocusable: be,
        edgesUpdatable: Bt,
        elementsSelectable: an,
        defaultViewport: it = mz,
        minZoom: Re = 0.5,
        maxZoom: ft = 2,
        translateExtent: Ut = Iv,
        preventScrolling: En = !0,
        nodeExtent: un,
        defaultMarkerColor: xt = "#b1b1b7",
        zoomOnScroll: Cn = !0,
        zoomOnPinch: Jn = !0,
        panOnScroll: qe = !1,
        panOnScrollSpeed: dt = 0.5,
        panOnScrollMode: Qe = Kr.Free,
        zoomOnDoubleClick: ot = !0,
        panOnDrag: Lr = !0,
        onPaneClick: Tn,
        onPaneMouseEnter: ln,
        onPaneMouseMove: Ao,
        onPaneMouseLeave: _c,
        onPaneScroll: No,
        onPaneContextMenu: Sc,
        children: kw,
        onEdgeContextMenu: Fr,
        onEdgeDoubleClick: gD,
        onEdgeMouseEnter: vD,
        onEdgeMouseMove: yD,
        onEdgeMouseLeave: wD,
        onEdgeUpdate: xD,
        onEdgeUpdateStart: _D,
        onEdgeUpdateEnd: SD,
        onReconnect: bD,
        onReconnectStart: ED,
        onReconnectEnd: CD,
        reconnectRadius: TD = 10,
        edgeUpdaterRadius: kD = 10,
        onNodesChange: PD,
        onEdgesChange: RD,
        noDragClassName: AD = "nodrag",
        noWheelClassName: ND = "nowheel",
        noPanClassName: Pw = "nopan",
        fitView: MD = !1,
        fitViewOptions: ID,
        connectOnClick: DD = !0,
        attributionPosition: OD,
        proOptions: LD,
        defaultEdgeOptions: FD,
        elevateNodesOnSelect: VD = !0,
        elevateEdgesOnSelect: jD = !1,
        disableKeyboardA11y: Rw = !1,
        autoPanOnConnect: qD = !0,
        autoPanOnNodeDrag: $D = !0,
        connectionRadius: zD = 20,
        isValidConnection: BD,
        onError: UD,
        style: HD,
        id: Aw,
        nodeDragThreshold: GD,
        ...WD
      },
      KD
    ) => {
      const bc = Aw || "1";
      return L.createElement(
        "div",
        {
          ...WD,
          style: { ...HD, ...gz },
          ref: KD,
          className: Ze(["react-flow", i]),
          "data-testid": "rf__wrapper",
          id: Aw,
        },
        L.createElement(
          ZA,
          null,
          L.createElement(lz, {
            onInit: l,
            onMove: c,
            onMoveStart: f,
            onMoveEnd: d,
            onNodeClick: a,
            onEdgeClick: u,
            onNodeMouseEnter: g,
            onNodeMouseMove: w,
            onNodeMouseLeave: x,
            onNodeContextMenu: S,
            onNodeDoubleClick: C,
            nodeTypes: o,
            edgeTypes: s,
            connectionLineType: D,
            connectionLineStyle: j,
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
            selectNodesOnDrag: Ve,
            defaultViewport: it,
            translateExtent: Ut,
            minZoom: Re,
            maxZoom: ft,
            preventScrolling: En,
            zoomOnScroll: Cn,
            zoomOnPinch: Jn,
            zoomOnDoubleClick: ot,
            panOnScroll: qe,
            panOnScrollSpeed: dt,
            panOnScrollMode: Qe,
            panOnDrag: Lr,
            onPaneClick: Tn,
            onPaneMouseEnter: ln,
            onPaneMouseMove: Ao,
            onPaneMouseLeave: _c,
            onPaneScroll: No,
            onPaneContextMenu: Sc,
            onSelectionContextMenu: R,
            onSelectionStart: F,
            onSelectionEnd: A,
            onEdgeContextMenu: Fr,
            onEdgeDoubleClick: gD,
            onEdgeMouseEnter: vD,
            onEdgeMouseMove: yD,
            onEdgeMouseLeave: wD,
            onReconnect: bD ?? xD,
            onReconnectStart: ED ?? _D,
            onReconnectEnd: CD ?? SD,
            reconnectRadius: TD ?? kD,
            defaultMarkerColor: xt,
            noDragClassName: AD,
            noWheelClassName: ND,
            noPanClassName: Pw,
            elevateEdgesOnSelect: jD,
            rfId: bc,
            disableKeyboardA11y: Rw,
            nodeOrigin: G,
            nodeExtent: un,
          }),
          L.createElement(o$, {
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
            nodesConnectable: je,
            nodesFocusable: K,
            edgesFocusable: be,
            edgesUpdatable: Bt,
            elementsSelectable: an,
            elevateNodesOnSelect: VD,
            minZoom: Re,
            maxZoom: ft,
            nodeExtent: un,
            onNodesChange: PD,
            onEdgesChange: RD,
            snapToGrid: De,
            snapGrid: Pe,
            connectionMode: k,
            translateExtent: Ut,
            connectOnClick: DD,
            defaultEdgeOptions: FD,
            fitView: MD,
            fitViewOptions: ID,
            onNodesDelete: N,
            onEdgesDelete: I,
            onNodeDragStart: E,
            onNodeDrag: T,
            onNodeDragStop: P,
            onSelectionDrag: b,
            onSelectionDragStart: q,
            onSelectionDragStop: O,
            noPanClassName: Pw,
            nodeOrigin: G,
            rfId: bc,
            autoPanOnConnect: qD,
            autoPanOnNodeDrag: $D,
            onError: UD,
            connectionRadius: zD,
            isValidConnection: BD,
            nodeDragThreshold: GD,
          }),
          L.createElement(r$, { onSelectionChange: V }),
          kw,
          L.createElement(Nq, { proOptions: LD, position: OD }),
          L.createElement(c$, { rfId: bc, disableKeyboardA11y: Rw })
        )
      );
    }
  );
QA.displayName = "ReactFlow";
const JA = ({
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
JA.displayName = "MiniMapNode";
var vz = _.memo(JA);
const yz = (e) => e.nodeOrigin,
  wz = (e) => e.getNodes().filter((t) => !t.hidden && t.width && t.height),
  af = (e) => (e instanceof Function ? e : () => e);
function xz({
  nodeStrokeColor: e = "transparent",
  nodeColor: t = "#e2e2e2",
  nodeClassName: n = "",
  nodeBorderRadius: r = 5,
  nodeStrokeWidth: i = 2,
  nodeComponent: o = vz,
  onClick: s,
}) {
  const a = he(wz, He),
    u = he(yz),
    l = af(t),
    c = af(e),
    f = af(n),
    d = typeof window > "u" || window.chrome ? "crispEdges" : "geometricPrecision";
  return L.createElement(
    L.Fragment,
    null,
    a.map((h) => {
      const { x: v, y: p } = ei(h, u).positionAbsolute;
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
    })
  );
}
var _z = _.memo(xz);
const Sz = 200,
  bz = 150,
  Ez = (e) => {
    const t = e.getNodes(),
      n = {
        x: -e.transform[0] / e.transform[2],
        y: -e.transform[1] / e.transform[2],
        width: e.width / e.transform[2],
        height: e.height / e.transform[2],
      };
    return { viewBB: n, boundingRect: t.length > 0 ? Dq(Ul(t, e.nodeOrigin), n) : n, rfId: e.rfId };
  },
  Cz = "react-flow__minimap-desc";
function eN({
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
    S = _.useRef(null),
    { boundingRect: C, viewBB: E, rfId: T } = he(Ez, He),
    P = (e == null ? void 0 : e.width) ?? Sz,
    N = (e == null ? void 0 : e.height) ?? bz,
    I = C.width / P,
    V = C.height / N,
    q = Math.max(I, V),
    b = q * P,
    O = q * N,
    R = w * q,
    F = C.x - (b - C.width) / 2 - R,
    A = C.y - (O - C.height) / 2 - R,
    k = b + R * 2,
    D = O + R * 2,
    j = `${Cz}-${T}`,
    $ = _.useRef(0);
  ($.current = q),
    _.useEffect(() => {
      if (S.current) {
        const W = Ot(S.current),
          X = (se) => {
            const { transform: oe, d3Selection: De, d3Zoom: Pe } = x.getState();
            if (se.sourceEvent.type !== "wheel" || !De || !Pe) return;
            const Ge =
                -se.sourceEvent.deltaY *
                (se.sourceEvent.deltaMode === 1 ? 0.05 : se.sourceEvent.deltaMode ? 1 : 0.002) *
                g,
              Ve = oe[2] * Math.pow(2, Ge);
            Pe.scaleTo(De, Ve);
          },
          ee = (se) => {
            const {
              transform: oe,
              d3Selection: De,
              d3Zoom: Pe,
              translateExtent: Ge,
              width: Ve,
              height: Q,
            } = x.getState();
            if (se.sourceEvent.type !== "mousemove" || !De || !Pe) return;
            const je = $.current * Math.max(1, oe[2]) * (m ? -1 : 1),
              K = {
                x: oe[0] - se.sourceEvent.movementX * je,
                y: oe[1] - se.sourceEvent.movementY * je,
              },
              G = [
                [0, 0],
                [Ve, Q],
              ],
              be = Vn.translate(K.x, K.y).scale(oe[2]),
              Bt = Pe.constrain()(be, G, Ge);
            Pe.transform(De, Bt);
          },
          ue = uA()
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
          const X = Yt(W);
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
    o0,
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
        height: N,
        viewBox: `${F} ${A} ${k} ${D}`,
        role: "img",
        "aria-labelledby": j,
        ref: S,
        onClick: U,
      },
      y && L.createElement("title", { id: j }, y),
      L.createElement(_z, {
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
        d: `M${F - R},${A - R}h${k + R * 2}v${D + R * 2}h${-k - R * 2}z
        M${E.x},${E.y}h${E.width}v${E.height}h${-E.width}z`,
        fill: u,
        fillRule: "evenodd",
        stroke: l,
        strokeWidth: c,
        pointerEvents: "none",
      })
    )
  );
}
eN.displayName = "MiniMap";
var Tz = _.memo(eN);
function kz() {
  return L.createElement(
    "svg",
    { xmlns: "http://www.w3.org/2000/svg", viewBox: "0 0 32 32" },
    L.createElement("path", {
      d: "M32 18.133H18.133V32h-4.266V18.133H0v-4.266h13.867V0h4.266v13.867H32z",
    })
  );
}
function Pz() {
  return L.createElement(
    "svg",
    { xmlns: "http://www.w3.org/2000/svg", viewBox: "0 0 32 5" },
    L.createElement("path", { d: "M0 0h32v4.2H0z" })
  );
}
function Rz() {
  return L.createElement(
    "svg",
    { xmlns: "http://www.w3.org/2000/svg", viewBox: "0 0 32 30" },
    L.createElement("path", {
      d:
        "M3.692 4.63c0-.53.4-.938.939-.938h5.215V0H4.708C2.13 0 0 2.054 0 4.63v5.216h3.692V4.631zM27.354 0h-5.2v3.692h5.17c.53 0 .984.4.984.939v5.215H32V4.631A4.624 4.624 0 0027.354 0zm.954 24.83c0 .532-.4.94-.939.94h-5.215v3.768h5.215c2.577 0 4.631-2.13 4.631-4.707v-5.139h-3.692v5.139zm-23.677.94c-.531 0-.939-.4-.939-.94v-5.138H0v5.139c0 2.577 2.13 4.707 4.708 4.707h5.138V25.77H4.631z",
    })
  );
}
function Az() {
  return L.createElement(
    "svg",
    { xmlns: "http://www.w3.org/2000/svg", viewBox: "0 0 25 32" },
    L.createElement("path", {
      d:
        "M21.333 10.667H19.81V7.619C19.81 3.429 16.38 0 12.19 0 8 0 4.571 3.429 4.571 7.619v3.048H3.048A3.056 3.056 0 000 13.714v15.238A3.056 3.056 0 003.048 32h18.285a3.056 3.056 0 003.048-3.048V13.714a3.056 3.056 0 00-3.048-3.047zM12.19 24.533a3.056 3.056 0 01-3.047-3.047 3.056 3.056 0 013.047-3.048 3.056 3.056 0 013.048 3.048 3.056 3.056 0 01-3.048 3.047zm4.724-13.866H7.467V7.619c0-2.59 2.133-4.724 4.723-4.724 2.591 0 4.724 2.133 4.724 4.724v3.048z",
    })
  );
}
function Nz() {
  return L.createElement(
    "svg",
    { xmlns: "http://www.w3.org/2000/svg", viewBox: "0 0 25 32" },
    L.createElement("path", {
      d:
        "M21.333 10.667H19.81V7.619C19.81 3.429 16.38 0 12.19 0c-4.114 1.828-1.37 2.133.305 2.438 1.676.305 4.42 2.59 4.42 5.181v3.048H3.047A3.056 3.056 0 000 13.714v15.238A3.056 3.056 0 003.048 32h18.285a3.056 3.056 0 003.048-3.048V13.714a3.056 3.056 0 00-3.048-3.047zM12.19 24.533a3.056 3.056 0 01-3.047-3.047 3.056 3.056 0 013.047-3.048 3.056 3.056 0 013.048 3.048 3.056 3.056 0 01-3.048 3.047z",
    })
  );
}
const es = ({ children: e, className: t, ...n }) =>
  L.createElement(
    "button",
    { type: "button", className: Ze(["react-flow__controls-button", t]), ...n },
    e
  );
es.displayName = "ControlButton";
const Mz = (e) => ({
    isInteractive: e.nodesDraggable || e.nodesConnectable || e.elementsSelectable,
    minZoomReached: e.transform[2] <= e.minZoom,
    maxZoomReached: e.transform[2] >= e.maxZoom,
  }),
  tN = ({
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
      { isInteractive: p, minZoomReached: y, maxZoomReached: m } = he(Mz, He),
      { zoomIn: g, zoomOut: w, fitView: x } = p0();
    if (
      (_.useEffect(() => {
        v(!0);
      }, []),
      !h)
    )
      return null;
    const S = () => {
        g(), o == null || o();
      },
      C = () => {
        w(), s == null || s();
      },
      E = () => {
        x(i), a == null || a();
      },
      T = () => {
        d.setState({ nodesDraggable: !p, nodesConnectable: !p, elementsSelectable: !p }),
          u == null || u(!p);
      };
    return L.createElement(
      o0,
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
            es,
            {
              onClick: S,
              className: "react-flow__controls-zoomin",
              title: "zoom in",
              "aria-label": "zoom in",
              disabled: m,
            },
            L.createElement(kz, null)
          ),
          L.createElement(
            es,
            {
              onClick: C,
              className: "react-flow__controls-zoomout",
              title: "zoom out",
              "aria-label": "zoom out",
              disabled: y,
            },
            L.createElement(Pz, null)
          )
        ),
      n &&
        L.createElement(
          es,
          {
            className: "react-flow__controls-fitview",
            onClick: E,
            title: "fit view",
            "aria-label": "fit view",
          },
          L.createElement(Rz, null)
        ),
      r &&
        L.createElement(
          es,
          {
            className: "react-flow__controls-interactive",
            onClick: T,
            title: "toggle interactivity",
            "aria-label": "toggle interactivity",
          },
          p ? L.createElement(Nz, null) : L.createElement(Az, null)
        ),
      c
    );
  };
tN.displayName = "Controls";
var Iz = _.memo(tN),
  en;
(function (e) {
  (e.Lines = "lines"), (e.Dots = "dots"), (e.Cross = "cross");
})(en || (en = {}));
function Dz({ color: e, dimensions: t, lineWidth: n }) {
  return L.createElement("path", {
    stroke: e,
    strokeWidth: n,
    d: `M${t[0] / 2} 0 V${t[1]} M0 ${t[1] / 2} H${t[0]}`,
  });
}
function Oz({ color: e, radius: t }) {
  return L.createElement("circle", { cx: t, cy: t, r: t, fill: e });
}
const Lz = { [en.Dots]: "#91919a", [en.Lines]: "#eee", [en.Cross]: "#e2e2e2" },
  Fz = { [en.Dots]: 1, [en.Lines]: 1, [en.Cross]: 6 },
  Vz = (e) => ({ transform: e.transform, patternId: `pattern-${e.rfId}` });
function nN({
  id: e,
  variant: t = en.Dots,
  gap: n = 20,
  size: r,
  lineWidth: i = 1,
  offset: o = 2,
  color: s,
  style: a,
  className: u,
}) {
  const l = _.useRef(null),
    { transform: c, patternId: f } = he(Vz, He),
    d = s || Lz[t],
    h = r || Fz[t],
    v = t === en.Dots,
    p = t === en.Cross,
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
        ? L.createElement(Oz, { color: d, radius: g / o })
        : L.createElement(Dz, { dimensions: w, color: d, lineWidth: i })
    ),
    L.createElement("rect", {
      x: "0",
      y: "0",
      width: "100%",
      height: "100%",
      fill: `url(#${f + e})`,
    })
  );
}
nN.displayName = "Background";
var jz = _.memo(nN);
function g0(e) {
  throw new Error(
    'Could not dynamically require "' +
      e +
      '". Please configure the dynamicRequireTargets or/and ignoreDynamicRequires option of @rollup/plugin-commonjs appropriately for this require call to work.'
  );
}
var uf, Nx;
function qz() {
  if (Nx) return uf;
  Nx = 1;
  function e() {
    (this.__data__ = []), (this.size = 0);
  }
  return (uf = e), uf;
}
var lf, Mx;
function So() {
  if (Mx) return lf;
  Mx = 1;
  function e(t, n) {
    return t === n || (t !== t && n !== n);
  }
  return (lf = e), lf;
}
var cf, Ix;
function Hl() {
  if (Ix) return cf;
  Ix = 1;
  var e = So();
  function t(n, r) {
    for (var i = n.length; i--; ) if (e(n[i][0], r)) return i;
    return -1;
  }
  return (cf = t), cf;
}
var ff, Dx;
function $z() {
  if (Dx) return ff;
  Dx = 1;
  var e = Hl(),
    t = Array.prototype,
    n = t.splice;
  function r(i) {
    var o = this.__data__,
      s = e(o, i);
    if (s < 0) return !1;
    var a = o.length - 1;
    return s == a ? o.pop() : n.call(o, s, 1), --this.size, !0;
  }
  return (ff = r), ff;
}
var df, Ox;
function zz() {
  if (Ox) return df;
  Ox = 1;
  var e = Hl();
  function t(n) {
    var r = this.__data__,
      i = e(r, n);
    return i < 0 ? void 0 : r[i][1];
  }
  return (df = t), df;
}
var hf, Lx;
function Bz() {
  if (Lx) return hf;
  Lx = 1;
  var e = Hl();
  function t(n) {
    return e(this.__data__, n) > -1;
  }
  return (hf = t), hf;
}
var pf, Fx;
function Uz() {
  if (Fx) return pf;
  Fx = 1;
  var e = Hl();
  function t(n, r) {
    var i = this.__data__,
      o = e(i, n);
    return o < 0 ? (++this.size, i.push([n, r])) : (i[o][1] = r), this;
  }
  return (pf = t), pf;
}
var mf, Vx;
function Gl() {
  if (Vx) return mf;
  Vx = 1;
  var e = qz(),
    t = $z(),
    n = zz(),
    r = Bz(),
    i = Uz();
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
    (mf = o),
    mf
  );
}
var gf, jx;
function Hz() {
  if (jx) return gf;
  jx = 1;
  var e = Gl();
  function t() {
    (this.__data__ = new e()), (this.size = 0);
  }
  return (gf = t), gf;
}
var vf, qx;
function Gz() {
  if (qx) return vf;
  qx = 1;
  function e(t) {
    var n = this.__data__,
      r = n.delete(t);
    return (this.size = n.size), r;
  }
  return (vf = e), vf;
}
var yf, $x;
function Wz() {
  if ($x) return yf;
  $x = 1;
  function e(t) {
    return this.__data__.get(t);
  }
  return (yf = e), yf;
}
var wf, zx;
function Kz() {
  if (zx) return wf;
  zx = 1;
  function e(t) {
    return this.__data__.has(t);
  }
  return (wf = e), wf;
}
var xf, Bx;
function rN() {
  if (Bx) return xf;
  Bx = 1;
  var e = typeof Sa == "object" && Sa && Sa.Object === Object && Sa;
  return (xf = e), xf;
}
var _f, Ux;
function rn() {
  if (Ux) return _f;
  Ux = 1;
  var e = rN(),
    t = typeof self == "object" && self && self.Object === Object && self,
    n = e || t || Function("return this")();
  return (_f = n), _f;
}
var Sf, Hx;
function bo() {
  if (Hx) return Sf;
  Hx = 1;
  var e = rn(),
    t = e.Symbol;
  return (Sf = t), Sf;
}
var bf, Gx;
function Yz() {
  if (Gx) return bf;
  Gx = 1;
  var e = bo(),
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
  return (bf = o), bf;
}
var Ef, Wx;
function Xz() {
  if (Wx) return Ef;
  Wx = 1;
  var e = Object.prototype,
    t = e.toString;
  function n(r) {
    return t.call(r);
  }
  return (Ef = n), Ef;
}
var Cf, Kx;
function di() {
  if (Kx) return Cf;
  Kx = 1;
  var e = bo(),
    t = Yz(),
    n = Xz(),
    r = "[object Null]",
    i = "[object Undefined]",
    o = e ? e.toStringTag : void 0;
  function s(a) {
    return a == null ? (a === void 0 ? i : r) : o && o in Object(a) ? t(a) : n(a);
  }
  return (Cf = s), Cf;
}
var Tf, Yx;
function $t() {
  if (Yx) return Tf;
  Yx = 1;
  function e(t) {
    var n = typeof t;
    return t != null && (n == "object" || n == "function");
  }
  return (Tf = e), Tf;
}
var kf, Xx;
function fa() {
  if (Xx) return kf;
  Xx = 1;
  var e = di(),
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
  return (kf = s), kf;
}
var Pf, Zx;
function Zz() {
  if (Zx) return Pf;
  Zx = 1;
  var e = rn(),
    t = e["__core-js_shared__"];
  return (Pf = t), Pf;
}
var Rf, Qx;
function Qz() {
  if (Qx) return Rf;
  Qx = 1;
  var e = Zz(),
    t = (function () {
      var r = /[^.]+$/.exec((e && e.keys && e.keys.IE_PROTO) || "");
      return r ? "Symbol(src)_1." + r : "";
    })();
  function n(r) {
    return !!t && t in r;
  }
  return (Rf = n), Rf;
}
var Af, Jx;
function iN() {
  if (Jx) return Af;
  Jx = 1;
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
  return (Af = n), Af;
}
var Nf, e_;
function Jz() {
  if (e_) return Nf;
  e_ = 1;
  var e = fa(),
    t = Qz(),
    n = $t(),
    r = iN(),
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
        "$"
    );
  function f(d) {
    if (!n(d) || t(d)) return !1;
    var h = e(d) ? c : o;
    return h.test(r(d));
  }
  return (Nf = f), Nf;
}
var Mf, t_;
function e4() {
  if (t_) return Mf;
  t_ = 1;
  function e(t, n) {
    return t == null ? void 0 : t[n];
  }
  return (Mf = e), Mf;
}
var If, n_;
function hi() {
  if (n_) return If;
  n_ = 1;
  var e = Jz(),
    t = e4();
  function n(r, i) {
    var o = t(r, i);
    return e(o) ? o : void 0;
  }
  return (If = n), If;
}
var Df, r_;
function v0() {
  if (r_) return Df;
  r_ = 1;
  var e = hi(),
    t = rn(),
    n = e(t, "Map");
  return (Df = n), Df;
}
var Of, i_;
function Wl() {
  if (i_) return Of;
  i_ = 1;
  var e = hi(),
    t = e(Object, "create");
  return (Of = t), Of;
}
var Lf, o_;
function t4() {
  if (o_) return Lf;
  o_ = 1;
  var e = Wl();
  function t() {
    (this.__data__ = e ? e(null) : {}), (this.size = 0);
  }
  return (Lf = t), Lf;
}
var Ff, s_;
function n4() {
  if (s_) return Ff;
  s_ = 1;
  function e(t) {
    var n = this.has(t) && delete this.__data__[t];
    return (this.size -= n ? 1 : 0), n;
  }
  return (Ff = e), Ff;
}
var Vf, a_;
function r4() {
  if (a_) return Vf;
  a_ = 1;
  var e = Wl(),
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
  return (Vf = i), Vf;
}
var jf, u_;
function i4() {
  if (u_) return jf;
  u_ = 1;
  var e = Wl(),
    t = Object.prototype,
    n = t.hasOwnProperty;
  function r(i) {
    var o = this.__data__;
    return e ? o[i] !== void 0 : n.call(o, i);
  }
  return (jf = r), jf;
}
var qf, l_;
function o4() {
  if (l_) return qf;
  l_ = 1;
  var e = Wl(),
    t = "__lodash_hash_undefined__";
  function n(r, i) {
    var o = this.__data__;
    return (this.size += this.has(r) ? 0 : 1), (o[r] = e && i === void 0 ? t : i), this;
  }
  return (qf = n), qf;
}
var $f, c_;
function s4() {
  if (c_) return $f;
  c_ = 1;
  var e = t4(),
    t = n4(),
    n = r4(),
    r = i4(),
    i = o4();
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
    ($f = o),
    $f
  );
}
var zf, f_;
function a4() {
  if (f_) return zf;
  f_ = 1;
  var e = s4(),
    t = Gl(),
    n = v0();
  function r() {
    (this.size = 0), (this.__data__ = { hash: new e(), map: new (n || t)(), string: new e() });
  }
  return (zf = r), zf;
}
var Bf, d_;
function u4() {
  if (d_) return Bf;
  d_ = 1;
  function e(t) {
    var n = typeof t;
    return n == "string" || n == "number" || n == "symbol" || n == "boolean"
      ? t !== "__proto__"
      : t === null;
  }
  return (Bf = e), Bf;
}
var Uf, h_;
function Kl() {
  if (h_) return Uf;
  h_ = 1;
  var e = u4();
  function t(n, r) {
    var i = n.__data__;
    return e(r) ? i[typeof r == "string" ? "string" : "hash"] : i.map;
  }
  return (Uf = t), Uf;
}
var Hf, p_;
function l4() {
  if (p_) return Hf;
  p_ = 1;
  var e = Kl();
  function t(n) {
    var r = e(this, n).delete(n);
    return (this.size -= r ? 1 : 0), r;
  }
  return (Hf = t), Hf;
}
var Gf, m_;
function c4() {
  if (m_) return Gf;
  m_ = 1;
  var e = Kl();
  function t(n) {
    return e(this, n).get(n);
  }
  return (Gf = t), Gf;
}
var Wf, g_;
function f4() {
  if (g_) return Wf;
  g_ = 1;
  var e = Kl();
  function t(n) {
    return e(this, n).has(n);
  }
  return (Wf = t), Wf;
}
var Kf, v_;
function d4() {
  if (v_) return Kf;
  v_ = 1;
  var e = Kl();
  function t(n, r) {
    var i = e(this, n),
      o = i.size;
    return i.set(n, r), (this.size += i.size == o ? 0 : 1), this;
  }
  return (Kf = t), Kf;
}
var Yf, y_;
function y0() {
  if (y_) return Yf;
  y_ = 1;
  var e = a4(),
    t = l4(),
    n = c4(),
    r = f4(),
    i = d4();
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
    (Yf = o),
    Yf
  );
}
var Xf, w_;
function h4() {
  if (w_) return Xf;
  w_ = 1;
  var e = Gl(),
    t = v0(),
    n = y0(),
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
  return (Xf = i), Xf;
}
var Zf, x_;
function Yl() {
  if (x_) return Zf;
  x_ = 1;
  var e = Gl(),
    t = Hz(),
    n = Gz(),
    r = Wz(),
    i = Kz(),
    o = h4();
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
    (Zf = s),
    Zf
  );
}
var Qf, __;
function w0() {
  if (__) return Qf;
  __ = 1;
  function e(t, n) {
    for (var r = -1, i = t == null ? 0 : t.length; ++r < i && n(t[r], r, t) !== !1; );
    return t;
  }
  return (Qf = e), Qf;
}
var Jf, S_;
function oN() {
  if (S_) return Jf;
  S_ = 1;
  var e = hi(),
    t = (function () {
      try {
        var n = e(Object, "defineProperty");
        return n({}, "", {}), n;
      } catch {}
    })();
  return (Jf = t), Jf;
}
var ed, b_;
function Xl() {
  if (b_) return ed;
  b_ = 1;
  var e = oN();
  function t(n, r, i) {
    r == "__proto__" && e
      ? e(n, r, { configurable: !0, enumerable: !0, value: i, writable: !0 })
      : (n[r] = i);
  }
  return (ed = t), ed;
}
var td, E_;
function Zl() {
  if (E_) return td;
  E_ = 1;
  var e = Xl(),
    t = So(),
    n = Object.prototype,
    r = n.hasOwnProperty;
  function i(o, s, a) {
    var u = o[s];
    (!(r.call(o, s) && t(u, a)) || (a === void 0 && !(s in o))) && e(o, s, a);
  }
  return (td = i), td;
}
var nd, C_;
function da() {
  if (C_) return nd;
  C_ = 1;
  var e = Zl(),
    t = Xl();
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
  return (nd = n), nd;
}
var rd, T_;
function p4() {
  if (T_) return rd;
  T_ = 1;
  function e(t, n) {
    for (var r = -1, i = Array(t); ++r < t; ) i[r] = n(r);
    return i;
  }
  return (rd = e), rd;
}
var id, k_;
function Sn() {
  if (k_) return id;
  k_ = 1;
  function e(t) {
    return t != null && typeof t == "object";
  }
  return (id = e), id;
}
var od, P_;
function m4() {
  if (P_) return od;
  P_ = 1;
  var e = di(),
    t = Sn(),
    n = "[object Arguments]";
  function r(i) {
    return t(i) && e(i) == n;
  }
  return (od = r), od;
}
var sd, R_;
function ha() {
  if (R_) return sd;
  R_ = 1;
  var e = m4(),
    t = Sn(),
    n = Object.prototype,
    r = n.hasOwnProperty,
    i = n.propertyIsEnumerable,
    o = e(
      (function () {
        return arguments;
      })()
    )
      ? e
      : function (s) {
          return t(s) && r.call(s, "callee") && !i.call(s, "callee");
        };
  return (sd = o), sd;
}
var ad, A_;
function Ie() {
  if (A_) return ad;
  A_ = 1;
  var e = Array.isArray;
  return (ad = e), ad;
}
var ts = { exports: {} },
  ud,
  N_;
function g4() {
  if (N_) return ud;
  N_ = 1;
  function e() {
    return !1;
  }
  return (ud = e), ud;
}
ts.exports;
var M_;
function Eo() {
  return (
    M_ ||
      ((M_ = 1),
      (function (e, t) {
        var n = rn(),
          r = g4(),
          i = t && !t.nodeType && t,
          o = i && !0 && e && !e.nodeType && e,
          s = o && o.exports === i,
          a = s ? n.Buffer : void 0,
          u = a ? a.isBuffer : void 0,
          l = u || r;
        e.exports = l;
      })(ts, ts.exports)),
    ts.exports
  );
}
var ld, I_;
function Ql() {
  if (I_) return ld;
  I_ = 1;
  var e = 9007199254740991,
    t = /^(?:0|[1-9]\d*)$/;
  function n(r, i) {
    var o = typeof r;
    return (
      (i = i ?? e),
      !!i && (o == "number" || (o != "symbol" && t.test(r))) && r > -1 && r % 1 == 0 && r < i
    );
  }
  return (ld = n), ld;
}
var cd, D_;
function x0() {
  if (D_) return cd;
  D_ = 1;
  var e = 9007199254740991;
  function t(n) {
    return typeof n == "number" && n > -1 && n % 1 == 0 && n <= e;
  }
  return (cd = t), cd;
}
var fd, O_;
function v4() {
  if (O_) return fd;
  O_ = 1;
  var e = di(),
    t = x0(),
    n = Sn(),
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
    S = "[object Int16Array]",
    C = "[object Int32Array]",
    E = "[object Uint8Array]",
    T = "[object Uint8ClampedArray]",
    P = "[object Uint16Array]",
    N = "[object Uint32Array]",
    I = {};
  (I[g] = I[w] = I[x] = I[S] = I[C] = I[E] = I[T] = I[P] = I[N] = !0),
    (I[r] = I[i] = I[y] = I[o] = I[m] = I[s] = I[a] = I[u] = I[l] = I[c] = I[f] = I[d] = I[h] = I[
      v
    ] = I[p] = !1);
  function V(q) {
    return n(q) && t(q.length) && !!I[e(q)];
  }
  return (fd = V), fd;
}
var dd, L_;
function Jl() {
  if (L_) return dd;
  L_ = 1;
  function e(t) {
    return function (n) {
      return t(n);
    };
  }
  return (dd = e), dd;
}
var ns = { exports: {} };
ns.exports;
var F_;
function _0() {
  return (
    F_ ||
      ((F_ = 1),
      (function (e, t) {
        var n = rN(),
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
      })(ns, ns.exports)),
    ns.exports
  );
}
var hd, V_;
function pa() {
  if (V_) return hd;
  V_ = 1;
  var e = v4(),
    t = Jl(),
    n = _0(),
    r = n && n.isTypedArray,
    i = r ? t(r) : e;
  return (hd = i), hd;
}
var pd, j_;
function sN() {
  if (j_) return pd;
  j_ = 1;
  var e = p4(),
    t = ha(),
    n = Ie(),
    r = Eo(),
    i = Ql(),
    o = pa(),
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
  return (pd = u), pd;
}
var md, q_;
function ec() {
  if (q_) return md;
  q_ = 1;
  var e = Object.prototype;
  function t(n) {
    var r = n && n.constructor,
      i = (typeof r == "function" && r.prototype) || e;
    return n === i;
  }
  return (md = t), md;
}
var gd, $_;
function aN() {
  if ($_) return gd;
  $_ = 1;
  function e(t, n) {
    return function (r) {
      return t(n(r));
    };
  }
  return (gd = e), gd;
}
var vd, z_;
function y4() {
  if (z_) return vd;
  z_ = 1;
  var e = aN(),
    t = e(Object.keys, Object);
  return (vd = t), vd;
}
var yd, B_;
function S0() {
  if (B_) return yd;
  B_ = 1;
  var e = ec(),
    t = y4(),
    n = Object.prototype,
    r = n.hasOwnProperty;
  function i(o) {
    if (!e(o)) return t(o);
    var s = [];
    for (var a in Object(o)) r.call(o, a) && a != "constructor" && s.push(a);
    return s;
  }
  return (yd = i), yd;
}
var wd, U_;
function Zn() {
  if (U_) return wd;
  U_ = 1;
  var e = fa(),
    t = x0();
  function n(r) {
    return r != null && t(r.length) && !e(r);
  }
  return (wd = n), wd;
}
var xd, H_;
function Dr() {
  if (H_) return xd;
  H_ = 1;
  var e = sN(),
    t = S0(),
    n = Zn();
  function r(i) {
    return n(i) ? e(i) : t(i);
  }
  return (xd = r), xd;
}
var _d, G_;
function w4() {
  if (G_) return _d;
  G_ = 1;
  var e = da(),
    t = Dr();
  function n(r, i) {
    return r && e(i, t(i), r);
  }
  return (_d = n), _d;
}
var Sd, W_;
function x4() {
  if (W_) return Sd;
  W_ = 1;
  function e(t) {
    var n = [];
    if (t != null) for (var r in Object(t)) n.push(r);
    return n;
  }
  return (Sd = e), Sd;
}
var bd, K_;
function _4() {
  if (K_) return bd;
  K_ = 1;
  var e = $t(),
    t = ec(),
    n = x4(),
    r = Object.prototype,
    i = r.hasOwnProperty;
  function o(s) {
    if (!e(s)) return n(s);
    var a = t(s),
      u = [];
    for (var l in s) (l == "constructor" && (a || !i.call(s, l))) || u.push(l);
    return u;
  }
  return (bd = o), bd;
}
var Ed, Y_;
function pi() {
  if (Y_) return Ed;
  Y_ = 1;
  var e = sN(),
    t = _4(),
    n = Zn();
  function r(i) {
    return n(i) ? e(i, !0) : t(i);
  }
  return (Ed = r), Ed;
}
var Cd, X_;
function S4() {
  if (X_) return Cd;
  X_ = 1;
  var e = da(),
    t = pi();
  function n(r, i) {
    return r && e(i, t(i), r);
  }
  return (Cd = n), Cd;
}
var rs = { exports: {} };
rs.exports;
var Z_;
function uN() {
  return (
    Z_ ||
      ((Z_ = 1),
      (function (e, t) {
        var n = rn(),
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
      })(rs, rs.exports)),
    rs.exports
  );
}
var Td, Q_;
function lN() {
  if (Q_) return Td;
  Q_ = 1;
  function e(t, n) {
    var r = -1,
      i = t.length;
    for (n || (n = Array(i)); ++r < i; ) n[r] = t[r];
    return n;
  }
  return (Td = e), Td;
}
var kd, J_;
function cN() {
  if (J_) return kd;
  J_ = 1;
  function e(t, n) {
    for (var r = -1, i = t == null ? 0 : t.length, o = 0, s = []; ++r < i; ) {
      var a = t[r];
      n(a, r, t) && (s[o++] = a);
    }
    return s;
  }
  return (kd = e), kd;
}
var Pd, eS;
function fN() {
  if (eS) return Pd;
  eS = 1;
  function e() {
    return [];
  }
  return (Pd = e), Pd;
}
var Rd, tS;
function b0() {
  if (tS) return Rd;
  tS = 1;
  var e = cN(),
    t = fN(),
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
  return (Rd = o), Rd;
}
var Ad, nS;
function b4() {
  if (nS) return Ad;
  nS = 1;
  var e = da(),
    t = b0();
  function n(r, i) {
    return e(r, t(r), i);
  }
  return (Ad = n), Ad;
}
var Nd, rS;
function E0() {
  if (rS) return Nd;
  rS = 1;
  function e(t, n) {
    for (var r = -1, i = n.length, o = t.length; ++r < i; ) t[o + r] = n[r];
    return t;
  }
  return (Nd = e), Nd;
}
var Md, iS;
function tc() {
  if (iS) return Md;
  iS = 1;
  var e = aN(),
    t = e(Object.getPrototypeOf, Object);
  return (Md = t), Md;
}
var Id, oS;
function dN() {
  if (oS) return Id;
  oS = 1;
  var e = E0(),
    t = tc(),
    n = b0(),
    r = fN(),
    i = Object.getOwnPropertySymbols,
    o = i
      ? function (s) {
          for (var a = []; s; ) e(a, n(s)), (s = t(s));
          return a;
        }
      : r;
  return (Id = o), Id;
}
var Dd, sS;
function E4() {
  if (sS) return Dd;
  sS = 1;
  var e = da(),
    t = dN();
  function n(r, i) {
    return e(r, t(r), i);
  }
  return (Dd = n), Dd;
}
var Od, aS;
function hN() {
  if (aS) return Od;
  aS = 1;
  var e = E0(),
    t = Ie();
  function n(r, i, o) {
    var s = i(r);
    return t(r) ? s : e(s, o(r));
  }
  return (Od = n), Od;
}
var Ld, uS;
function pN() {
  if (uS) return Ld;
  uS = 1;
  var e = hN(),
    t = b0(),
    n = Dr();
  function r(i) {
    return e(i, n, t);
  }
  return (Ld = r), Ld;
}
var Fd, lS;
function C4() {
  if (lS) return Fd;
  lS = 1;
  var e = hN(),
    t = dN(),
    n = pi();
  function r(i) {
    return e(i, n, t);
  }
  return (Fd = r), Fd;
}
var Vd, cS;
function T4() {
  if (cS) return Vd;
  cS = 1;
  var e = hi(),
    t = rn(),
    n = e(t, "DataView");
  return (Vd = n), Vd;
}
var jd, fS;
function k4() {
  if (fS) return jd;
  fS = 1;
  var e = hi(),
    t = rn(),
    n = e(t, "Promise");
  return (jd = n), jd;
}
var qd, dS;
function mN() {
  if (dS) return qd;
  dS = 1;
  var e = hi(),
    t = rn(),
    n = e(t, "Set");
  return (qd = n), qd;
}
var $d, hS;
function P4() {
  if (hS) return $d;
  hS = 1;
  var e = hi(),
    t = rn(),
    n = e(t, "WeakMap");
  return ($d = n), $d;
}
var zd, pS;
function Co() {
  if (pS) return zd;
  pS = 1;
  var e = T4(),
    t = v0(),
    n = k4(),
    r = mN(),
    i = P4(),
    o = di(),
    s = iN(),
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
          S = x == u ? w.constructor : void 0,
          C = S ? s(S) : "";
        if (C)
          switch (C) {
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
    (zd = g),
    zd
  );
}
var Bd, mS;
function R4() {
  if (mS) return Bd;
  mS = 1;
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
  return (Bd = n), Bd;
}
var Ud, gS;
function gN() {
  if (gS) return Ud;
  gS = 1;
  var e = rn(),
    t = e.Uint8Array;
  return (Ud = t), Ud;
}
var Hd, vS;
function C0() {
  if (vS) return Hd;
  vS = 1;
  var e = gN();
  function t(n) {
    var r = new n.constructor(n.byteLength);
    return new e(r).set(new e(n)), r;
  }
  return (Hd = t), Hd;
}
var Gd, yS;
function A4() {
  if (yS) return Gd;
  yS = 1;
  var e = C0();
  function t(n, r) {
    var i = r ? e(n.buffer) : n.buffer;
    return new n.constructor(i, n.byteOffset, n.byteLength);
  }
  return (Gd = t), Gd;
}
var Wd, wS;
function N4() {
  if (wS) return Wd;
  wS = 1;
  var e = /\w*$/;
  function t(n) {
    var r = new n.constructor(n.source, e.exec(n));
    return (r.lastIndex = n.lastIndex), r;
  }
  return (Wd = t), Wd;
}
var Kd, xS;
function M4() {
  if (xS) return Kd;
  xS = 1;
  var e = bo(),
    t = e ? e.prototype : void 0,
    n = t ? t.valueOf : void 0;
  function r(i) {
    return n ? Object(n.call(i)) : {};
  }
  return (Kd = r), Kd;
}
var Yd, _S;
function vN() {
  if (_S) return Yd;
  _S = 1;
  var e = C0();
  function t(n, r) {
    var i = r ? e(n.buffer) : n.buffer;
    return new n.constructor(i, n.byteOffset, n.length);
  }
  return (Yd = t), Yd;
}
var Xd, SS;
function I4() {
  if (SS) return Xd;
  SS = 1;
  var e = C0(),
    t = A4(),
    n = N4(),
    r = M4(),
    i = vN(),
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
    S = "[object Uint8ClampedArray]",
    C = "[object Uint16Array]",
    E = "[object Uint32Array]";
  function T(P, N, I) {
    var V = P.constructor;
    switch (N) {
      case h:
        return e(P);
      case o:
      case s:
        return new V(+P);
      case v:
        return t(P, I);
      case p:
      case y:
      case m:
      case g:
      case w:
      case x:
      case S:
      case C:
      case E:
        return i(P, I);
      case a:
        return new V();
      case u:
      case f:
        return new V(P);
      case l:
        return n(P);
      case c:
        return new V();
      case d:
        return r(P);
    }
  }
  return (Xd = T), Xd;
}
var Zd, bS;
function yN() {
  if (bS) return Zd;
  bS = 1;
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
  return (Zd = n), Zd;
}
var Qd, ES;
function wN() {
  if (ES) return Qd;
  ES = 1;
  var e = yN(),
    t = tc(),
    n = ec();
  function r(i) {
    return typeof i.constructor == "function" && !n(i) ? e(t(i)) : {};
  }
  return (Qd = r), Qd;
}
var Jd, CS;
function D4() {
  if (CS) return Jd;
  CS = 1;
  var e = Co(),
    t = Sn(),
    n = "[object Map]";
  function r(i) {
    return t(i) && e(i) == n;
  }
  return (Jd = r), Jd;
}
var eh, TS;
function O4() {
  if (TS) return eh;
  TS = 1;
  var e = D4(),
    t = Jl(),
    n = _0(),
    r = n && n.isMap,
    i = r ? t(r) : e;
  return (eh = i), eh;
}
var th, kS;
function L4() {
  if (kS) return th;
  kS = 1;
  var e = Co(),
    t = Sn(),
    n = "[object Set]";
  function r(i) {
    return t(i) && e(i) == n;
  }
  return (th = r), th;
}
var nh, PS;
function F4() {
  if (PS) return nh;
  PS = 1;
  var e = L4(),
    t = Jl(),
    n = _0(),
    r = n && n.isSet,
    i = r ? t(r) : e;
  return (nh = i), nh;
}
var rh, RS;
function xN() {
  if (RS) return rh;
  RS = 1;
  var e = Yl(),
    t = w0(),
    n = Zl(),
    r = w4(),
    i = S4(),
    o = uN(),
    s = lN(),
    a = b4(),
    u = E4(),
    l = pN(),
    c = C4(),
    f = Co(),
    d = R4(),
    h = I4(),
    v = wN(),
    p = Ie(),
    y = Eo(),
    m = O4(),
    g = $t(),
    w = F4(),
    x = Dr(),
    S = pi(),
    C = 1,
    E = 2,
    T = 4,
    P = "[object Arguments]",
    N = "[object Array]",
    I = "[object Boolean]",
    V = "[object Date]",
    q = "[object Error]",
    b = "[object Function]",
    O = "[object GeneratorFunction]",
    R = "[object Map]",
    F = "[object Number]",
    A = "[object Object]",
    k = "[object RegExp]",
    D = "[object Set]",
    j = "[object String]",
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
    Pe = "[object Uint8ClampedArray]",
    Ge = "[object Uint16Array]",
    Ve = "[object Uint32Array]",
    Q = {};
  (Q[P] = Q[N] = Q[B] = Q[W] = Q[I] = Q[V] = Q[X] = Q[ee] = Q[ue] = Q[se] = Q[oe] = Q[R] = Q[F] = Q[
    A
  ] = Q[k] = Q[D] = Q[j] = Q[$] = Q[De] = Q[Pe] = Q[Ge] = Q[Ve] = !0),
    (Q[q] = Q[b] = Q[U] = !1);
  function je(K, G, be, Bt, an, it) {
    var Re,
      ft = G & C,
      Ut = G & E,
      En = G & T;
    if ((be && (Re = an ? be(K, Bt, an, it) : be(K)), Re !== void 0)) return Re;
    if (!g(K)) return K;
    var un = p(K);
    if (un) {
      if (((Re = d(K)), !ft)) return s(K, Re);
    } else {
      var xt = f(K),
        Cn = xt == b || xt == O;
      if (y(K)) return o(K, ft);
      if (xt == A || xt == P || (Cn && !an)) {
        if (((Re = Ut || Cn ? {} : v(K)), !ft)) return Ut ? u(K, i(Re, K)) : a(K, r(Re, K));
      } else {
        if (!Q[xt]) return an ? K : {};
        Re = h(K, xt, ft);
      }
    }
    it || (it = new e());
    var Jn = it.get(K);
    if (Jn) return Jn;
    it.set(K, Re),
      w(K)
        ? K.forEach(function (Qe) {
            Re.add(je(Qe, G, be, Qe, K, it));
          })
        : m(K) &&
          K.forEach(function (Qe, ot) {
            Re.set(ot, je(Qe, G, be, ot, K, it));
          });
    var qe = En ? (Ut ? c : l) : Ut ? S : x,
      dt = un ? void 0 : qe(K);
    return (
      t(dt || K, function (Qe, ot) {
        dt && ((ot = Qe), (Qe = K[ot])), n(Re, ot, je(Qe, G, be, ot, K, it));
      }),
      Re
    );
  }
  return (rh = je), rh;
}
var ih, AS;
function V4() {
  if (AS) return ih;
  AS = 1;
  var e = xN(),
    t = 4;
  function n(r) {
    return e(r, t);
  }
  return (ih = n), ih;
}
var oh, NS;
function T0() {
  if (NS) return oh;
  NS = 1;
  function e(t) {
    return function () {
      return t;
    };
  }
  return (oh = e), oh;
}
var sh, MS;
function j4() {
  if (MS) return sh;
  MS = 1;
  function e(t) {
    return function (n, r, i) {
      for (var o = -1, s = Object(n), a = i(n), u = a.length; u--; ) {
        var l = a[t ? u : ++o];
        if (r(s[l], l, s) === !1) break;
      }
      return n;
    };
  }
  return (sh = e), sh;
}
var ah, IS;
function k0() {
  if (IS) return ah;
  IS = 1;
  var e = j4(),
    t = e();
  return (ah = t), ah;
}
var uh, DS;
function P0() {
  if (DS) return uh;
  DS = 1;
  var e = k0(),
    t = Dr();
  function n(r, i) {
    return r && e(r, i, t);
  }
  return (uh = n), uh;
}
var lh, OS;
function q4() {
  if (OS) return lh;
  OS = 1;
  var e = Zn();
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
  return (lh = t), lh;
}
var ch, LS;
function nc() {
  if (LS) return ch;
  LS = 1;
  var e = P0(),
    t = q4(),
    n = t(e);
  return (ch = n), ch;
}
var fh, FS;
function mi() {
  if (FS) return fh;
  FS = 1;
  function e(t) {
    return t;
  }
  return (fh = e), fh;
}
var dh, VS;
function _N() {
  if (VS) return dh;
  VS = 1;
  var e = mi();
  function t(n) {
    return typeof n == "function" ? n : e;
  }
  return (dh = t), dh;
}
var hh, jS;
function SN() {
  if (jS) return hh;
  jS = 1;
  var e = w0(),
    t = nc(),
    n = _N(),
    r = Ie();
  function i(o, s) {
    var a = r(o) ? e : t;
    return a(o, n(s));
  }
  return (hh = i), hh;
}
var ph, qS;
function bN() {
  return qS || ((qS = 1), (ph = SN())), ph;
}
var mh, $S;
function $4() {
  if ($S) return mh;
  $S = 1;
  var e = nc();
  function t(n, r) {
    var i = [];
    return (
      e(n, function (o, s, a) {
        r(o, s, a) && i.push(o);
      }),
      i
    );
  }
  return (mh = t), mh;
}
var gh, zS;
function z4() {
  if (zS) return gh;
  zS = 1;
  var e = "__lodash_hash_undefined__";
  function t(n) {
    return this.__data__.set(n, e), this;
  }
  return (gh = t), gh;
}
var vh, BS;
function B4() {
  if (BS) return vh;
  BS = 1;
  function e(t) {
    return this.__data__.has(t);
  }
  return (vh = e), vh;
}
var yh, US;
function EN() {
  if (US) return yh;
  US = 1;
  var e = y0(),
    t = z4(),
    n = B4();
  function r(i) {
    var o = -1,
      s = i == null ? 0 : i.length;
    for (this.__data__ = new e(); ++o < s; ) this.add(i[o]);
  }
  return (r.prototype.add = r.prototype.push = t), (r.prototype.has = n), (yh = r), yh;
}
var wh, HS;
function U4() {
  if (HS) return wh;
  HS = 1;
  function e(t, n) {
    for (var r = -1, i = t == null ? 0 : t.length; ++r < i; ) if (n(t[r], r, t)) return !0;
    return !1;
  }
  return (wh = e), wh;
}
var xh, GS;
function CN() {
  if (GS) return xh;
  GS = 1;
  function e(t, n) {
    return t.has(n);
  }
  return (xh = e), xh;
}
var _h, WS;
function TN() {
  if (WS) return _h;
  WS = 1;
  var e = EN(),
    t = U4(),
    n = CN(),
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
        S = a[m];
      if (l) var C = d ? l(S, x, m, a, s, f) : l(x, S, m, s, a, f);
      if (C !== void 0) {
        if (C) continue;
        g = !1;
        break;
      }
      if (w) {
        if (
          !t(a, function (E, T) {
            if (!n(w, T) && (x === E || c(x, E, u, l, f))) return w.push(T);
          })
        ) {
          g = !1;
          break;
        }
      } else if (!(x === S || c(x, S, u, l, f))) {
        g = !1;
        break;
      }
    }
    return f.delete(s), f.delete(a), g;
  }
  return (_h = o), _h;
}
var Sh, KS;
function H4() {
  if (KS) return Sh;
  KS = 1;
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
  return (Sh = e), Sh;
}
var bh, YS;
function R0() {
  if (YS) return bh;
  YS = 1;
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
  return (bh = e), bh;
}
var Eh, XS;
function G4() {
  if (XS) return Eh;
  XS = 1;
  var e = bo(),
    t = gN(),
    n = So(),
    r = TN(),
    i = H4(),
    o = R0(),
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
  function S(C, E, T, P, N, I, V) {
    switch (T) {
      case g:
        if (C.byteLength != E.byteLength || C.byteOffset != E.byteOffset) return !1;
        (C = C.buffer), (E = E.buffer);
      case m:
        return !(C.byteLength != E.byteLength || !I(new t(C), new t(E)));
      case u:
      case l:
      case d:
        return n(+C, +E);
      case c:
        return C.name == E.name && C.message == E.message;
      case h:
      case p:
        return C == E + "";
      case f:
        var q = i;
      case v:
        var b = P & s;
        if ((q || (q = o), C.size != E.size && !b)) return !1;
        var O = V.get(C);
        if (O) return O == E;
        (P |= a), V.set(C, E);
        var R = r(q(C), q(E), P, N, I, V);
        return V.delete(C), R;
      case y:
        if (x) return x.call(C) == x.call(E);
    }
    return !1;
  }
  return (Eh = S), Eh;
}
var Ch, ZS;
function W4() {
  if (ZS) return Ch;
  ZS = 1;
  var e = pN(),
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
    for (var S = f; ++y < h; ) {
      m = d[y];
      var C = o[m],
        E = s[m];
      if (u) var T = f ? u(E, C, m, s, o, c) : u(C, E, m, o, s, c);
      if (!(T === void 0 ? C === E || l(C, E, a, u, c) : T)) {
        x = !1;
        break;
      }
      S || (S = m == "constructor");
    }
    if (x && !S) {
      var P = o.constructor,
        N = s.constructor;
      P != N &&
        "constructor" in o &&
        "constructor" in s &&
        !(typeof P == "function" && P instanceof P && typeof N == "function" && N instanceof N) &&
        (x = !1);
    }
    return c.delete(o), c.delete(s), x;
  }
  return (Ch = i), Ch;
}
var Th, QS;
function K4() {
  if (QS) return Th;
  QS = 1;
  var e = Yl(),
    t = TN(),
    n = G4(),
    r = W4(),
    i = Co(),
    o = Ie(),
    s = Eo(),
    a = pa(),
    u = 1,
    l = "[object Arguments]",
    c = "[object Array]",
    f = "[object Object]",
    d = Object.prototype,
    h = d.hasOwnProperty;
  function v(p, y, m, g, w, x) {
    var S = o(p),
      C = o(y),
      E = S ? c : i(p),
      T = C ? c : i(y);
    (E = E == l ? f : E), (T = T == l ? f : T);
    var P = E == f,
      N = T == f,
      I = E == T;
    if (I && s(p)) {
      if (!s(y)) return !1;
      (S = !0), (P = !1);
    }
    if (I && !P)
      return x || (x = new e()), S || a(p) ? t(p, y, m, g, w, x) : n(p, y, E, m, g, w, x);
    if (!(m & u)) {
      var V = P && h.call(p, "__wrapped__"),
        q = N && h.call(y, "__wrapped__");
      if (V || q) {
        var b = V ? p.value() : p,
          O = q ? y.value() : y;
        return x || (x = new e()), w(b, O, m, g, x);
      }
    }
    return I ? (x || (x = new e()), r(p, y, m, g, w, x)) : !1;
  }
  return (Th = v), Th;
}
var kh, JS;
function kN() {
  if (JS) return kh;
  JS = 1;
  var e = K4(),
    t = Sn();
  function n(r, i, o, s, a) {
    return r === i
      ? !0
      : r == null || i == null || (!t(r) && !t(i))
      ? r !== r && i !== i
      : e(r, i, o, s, n, a);
  }
  return (kh = n), kh;
}
var Ph, eb;
function Y4() {
  if (eb) return Ph;
  eb = 1;
  var e = Yl(),
    t = kN(),
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
  return (Ph = i), Ph;
}
var Rh, tb;
function PN() {
  if (tb) return Rh;
  tb = 1;
  var e = $t();
  function t(n) {
    return n === n && !e(n);
  }
  return (Rh = t), Rh;
}
var Ah, nb;
function X4() {
  if (nb) return Ah;
  nb = 1;
  var e = PN(),
    t = Dr();
  function n(r) {
    for (var i = t(r), o = i.length; o--; ) {
      var s = i[o],
        a = r[s];
      i[o] = [s, a, e(a)];
    }
    return i;
  }
  return (Ah = n), Ah;
}
var Nh, rb;
function RN() {
  if (rb) return Nh;
  rb = 1;
  function e(t, n) {
    return function (r) {
      return r == null ? !1 : r[t] === n && (n !== void 0 || t in Object(r));
    };
  }
  return (Nh = e), Nh;
}
var Mh, ib;
function Z4() {
  if (ib) return Mh;
  ib = 1;
  var e = Y4(),
    t = X4(),
    n = RN();
  function r(i) {
    var o = t(i);
    return o.length == 1 && o[0][2]
      ? n(o[0][0], o[0][1])
      : function (s) {
          return s === i || e(s, i, o);
        };
  }
  return (Mh = r), Mh;
}
var Ih, ob;
function To() {
  if (ob) return Ih;
  ob = 1;
  var e = di(),
    t = Sn(),
    n = "[object Symbol]";
  function r(i) {
    return typeof i == "symbol" || (t(i) && e(i) == n);
  }
  return (Ih = r), Ih;
}
var Dh, sb;
function A0() {
  if (sb) return Dh;
  sb = 1;
  var e = Ie(),
    t = To(),
    n = /\.|\[(?:[^[\]]*|(["'])(?:(?!\1)[^\\]|\\.)*?\1)\]/,
    r = /^\w*$/;
  function i(o, s) {
    if (e(o)) return !1;
    var a = typeof o;
    return a == "number" || a == "symbol" || a == "boolean" || o == null || t(o)
      ? !0
      : r.test(o) || !n.test(o) || (s != null && o in Object(s));
  }
  return (Dh = i), Dh;
}
var Oh, ab;
function Q4() {
  if (ab) return Oh;
  ab = 1;
  var e = y0(),
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
  return (n.Cache = e), (Oh = n), Oh;
}
var Lh, ub;
function J4() {
  if (ub) return Lh;
  ub = 1;
  var e = Q4(),
    t = 500;
  function n(r) {
    var i = e(r, function (s) {
        return o.size === t && o.clear(), s;
      }),
      o = i.cache;
    return i;
  }
  return (Lh = n), Lh;
}
var Fh, lb;
function eB() {
  if (lb) return Fh;
  lb = 1;
  var e = J4(),
    t = /[^.[\]]+|\[(?:(-?\d+(?:\.\d+)?)|(["'])((?:(?!\2)[^\\]|\\.)*?)\2)\]|(?=(?:\.|\[\])(?:\.|\[\]|$))/g,
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
  return (Fh = r), Fh;
}
var Vh, cb;
function rc() {
  if (cb) return Vh;
  cb = 1;
  function e(t, n) {
    for (var r = -1, i = t == null ? 0 : t.length, o = Array(i); ++r < i; ) o[r] = n(t[r], r, t);
    return o;
  }
  return (Vh = e), Vh;
}
var jh, fb;
function tB() {
  if (fb) return jh;
  fb = 1;
  var e = bo(),
    t = rc(),
    n = Ie(),
    r = To(),
    i = e ? e.prototype : void 0,
    o = i ? i.toString : void 0;
  function s(a) {
    if (typeof a == "string") return a;
    if (n(a)) return t(a, s) + "";
    if (r(a)) return o ? o.call(a) : "";
    var u = a + "";
    return u == "0" && 1 / a == -1 / 0 ? "-0" : u;
  }
  return (jh = s), jh;
}
var qh, db;
function AN() {
  if (db) return qh;
  db = 1;
  var e = tB();
  function t(n) {
    return n == null ? "" : e(n);
  }
  return (qh = t), qh;
}
var $h, hb;
function ic() {
  if (hb) return $h;
  hb = 1;
  var e = Ie(),
    t = A0(),
    n = eB(),
    r = AN();
  function i(o, s) {
    return e(o) ? o : t(o, s) ? [o] : n(r(o));
  }
  return ($h = i), $h;
}
var zh, pb;
function ma() {
  if (pb) return zh;
  pb = 1;
  var e = To();
  function t(n) {
    if (typeof n == "string" || e(n)) return n;
    var r = n + "";
    return r == "0" && 1 / n == -1 / 0 ? "-0" : r;
  }
  return (zh = t), zh;
}
var Bh, mb;
function oc() {
  if (mb) return Bh;
  mb = 1;
  var e = ic(),
    t = ma();
  function n(r, i) {
    i = e(i, r);
    for (var o = 0, s = i.length; r != null && o < s; ) r = r[t(i[o++])];
    return o && o == s ? r : void 0;
  }
  return (Bh = n), Bh;
}
var Uh, gb;
function nB() {
  if (gb) return Uh;
  gb = 1;
  var e = oc();
  function t(n, r, i) {
    var o = n == null ? void 0 : e(n, r);
    return o === void 0 ? i : o;
  }
  return (Uh = t), Uh;
}
var Hh, vb;
function rB() {
  if (vb) return Hh;
  vb = 1;
  function e(t, n) {
    return t != null && n in Object(t);
  }
  return (Hh = e), Hh;
}
var Gh, yb;
function NN() {
  if (yb) return Gh;
  yb = 1;
  var e = ic(),
    t = ha(),
    n = Ie(),
    r = Ql(),
    i = x0(),
    o = ma();
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
  return (Gh = s), Gh;
}
var Wh, wb;
function MN() {
  if (wb) return Wh;
  wb = 1;
  var e = rB(),
    t = NN();
  function n(r, i) {
    return r != null && t(r, i, e);
  }
  return (Wh = n), Wh;
}
var Kh, xb;
function iB() {
  if (xb) return Kh;
  xb = 1;
  var e = kN(),
    t = nB(),
    n = MN(),
    r = A0(),
    i = PN(),
    o = RN(),
    s = ma(),
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
  return (Kh = l), Kh;
}
var Yh, _b;
function IN() {
  if (_b) return Yh;
  _b = 1;
  function e(t) {
    return function (n) {
      return n == null ? void 0 : n[t];
    };
  }
  return (Yh = e), Yh;
}
var Xh, Sb;
function oB() {
  if (Sb) return Xh;
  Sb = 1;
  var e = oc();
  function t(n) {
    return function (r) {
      return e(r, n);
    };
  }
  return (Xh = t), Xh;
}
var Zh, bb;
function sB() {
  if (bb) return Zh;
  bb = 1;
  var e = IN(),
    t = oB(),
    n = A0(),
    r = ma();
  function i(o) {
    return n(o) ? e(r(o)) : t(o);
  }
  return (Zh = i), Zh;
}
var Qh, Eb;
function Qn() {
  if (Eb) return Qh;
  Eb = 1;
  var e = Z4(),
    t = iB(),
    n = mi(),
    r = Ie(),
    i = sB();
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
  return (Qh = o), Qh;
}
var Jh, Cb;
function DN() {
  if (Cb) return Jh;
  Cb = 1;
  var e = cN(),
    t = $4(),
    n = Qn(),
    r = Ie();
  function i(o, s) {
    var a = r(o) ? e : t;
    return a(o, n(s, 3));
  }
  return (Jh = i), Jh;
}
var ep, Tb;
function aB() {
  if (Tb) return ep;
  Tb = 1;
  var e = Object.prototype,
    t = e.hasOwnProperty;
  function n(r, i) {
    return r != null && t.call(r, i);
  }
  return (ep = n), ep;
}
var tp, kb;
function ON() {
  if (kb) return tp;
  kb = 1;
  var e = aB(),
    t = NN();
  function n(r, i) {
    return r != null && t(r, i, e);
  }
  return (tp = n), tp;
}
var np, Pb;
function uB() {
  if (Pb) return np;
  Pb = 1;
  var e = S0(),
    t = Co(),
    n = ha(),
    r = Ie(),
    i = Zn(),
    o = Eo(),
    s = ec(),
    a = pa(),
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
  return (np = d), np;
}
var rp, Rb;
function LN() {
  if (Rb) return rp;
  Rb = 1;
  function e(t) {
    return t === void 0;
  }
  return (rp = e), rp;
}
var ip, Ab;
function FN() {
  if (Ab) return ip;
  Ab = 1;
  var e = nc(),
    t = Zn();
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
  return (ip = n), ip;
}
var op, Nb;
function VN() {
  if (Nb) return op;
  Nb = 1;
  var e = rc(),
    t = Qn(),
    n = FN(),
    r = Ie();
  function i(o, s) {
    var a = r(o) ? e : n;
    return a(o, t(s, 3));
  }
  return (op = i), op;
}
var sp, Mb;
function lB() {
  if (Mb) return sp;
  Mb = 1;
  function e(t, n, r, i) {
    var o = -1,
      s = t == null ? 0 : t.length;
    for (i && s && (r = t[++o]); ++o < s; ) r = n(r, t[o], o, t);
    return r;
  }
  return (sp = e), sp;
}
var ap, Ib;
function cB() {
  if (Ib) return ap;
  Ib = 1;
  function e(t, n, r, i, o) {
    return (
      o(t, function (s, a, u) {
        r = i ? ((i = !1), s) : n(r, s, a, u);
      }),
      r
    );
  }
  return (ap = e), ap;
}
var up, Db;
function jN() {
  if (Db) return up;
  Db = 1;
  var e = lB(),
    t = nc(),
    n = Qn(),
    r = cB(),
    i = Ie();
  function o(s, a, u) {
    var l = i(s) ? e : r,
      c = arguments.length < 3;
    return l(s, n(a, 4), u, c, t);
  }
  return (up = o), up;
}
var lp, Ob;
function fB() {
  if (Ob) return lp;
  Ob = 1;
  var e = di(),
    t = Ie(),
    n = Sn(),
    r = "[object String]";
  function i(o) {
    return typeof o == "string" || (!t(o) && n(o) && e(o) == r);
  }
  return (lp = i), lp;
}
var cp, Lb;
function dB() {
  if (Lb) return cp;
  Lb = 1;
  var e = IN(),
    t = e("length");
  return (cp = t), cp;
}
var fp, Fb;
function hB() {
  if (Fb) return fp;
  Fb = 1;
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
  return (fp = u), fp;
}
var dp, Vb;
function pB() {
  if (Vb) return dp;
  Vb = 1;
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
  function x(S) {
    for (var C = (w.lastIndex = 0); w.test(S); ) ++C;
    return C;
  }
  return (dp = x), dp;
}
var hp, jb;
function mB() {
  if (jb) return hp;
  jb = 1;
  var e = dB(),
    t = hB(),
    n = pB();
  function r(i) {
    return t(i) ? n(i) : e(i);
  }
  return (hp = r), hp;
}
var pp, qb;
function gB() {
  if (qb) return pp;
  qb = 1;
  var e = S0(),
    t = Co(),
    n = Zn(),
    r = fB(),
    i = mB(),
    o = "[object Map]",
    s = "[object Set]";
  function a(u) {
    if (u == null) return 0;
    if (n(u)) return r(u) ? i(u) : u.length;
    var l = t(u);
    return l == o || l == s ? u.size : e(u).length;
  }
  return (pp = a), pp;
}
var mp, $b;
function vB() {
  if ($b) return mp;
  $b = 1;
  var e = w0(),
    t = yN(),
    n = P0(),
    r = Qn(),
    i = tc(),
    o = Ie(),
    s = Eo(),
    a = fa(),
    u = $t(),
    l = pa();
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
  return (mp = c), mp;
}
var gp, zb;
function yB() {
  if (zb) return gp;
  zb = 1;
  var e = bo(),
    t = ha(),
    n = Ie(),
    r = e ? e.isConcatSpreadable : void 0;
  function i(o) {
    return n(o) || t(o) || !!(r && o && o[r]);
  }
  return (gp = i), gp;
}
var vp, Bb;
function N0() {
  if (Bb) return vp;
  Bb = 1;
  var e = E0(),
    t = yB();
  function n(r, i, o, s, a) {
    var u = -1,
      l = r.length;
    for (o || (o = t), a || (a = []); ++u < l; ) {
      var c = r[u];
      i > 0 && o(c) ? (i > 1 ? n(c, i - 1, o, s, a) : e(a, c)) : s || (a[a.length] = c);
    }
    return a;
  }
  return (vp = n), vp;
}
var yp, Ub;
function wB() {
  if (Ub) return yp;
  Ub = 1;
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
  return (yp = e), yp;
}
var wp, Hb;
function qN() {
  if (Hb) return wp;
  Hb = 1;
  var e = wB(),
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
  return (wp = n), wp;
}
var xp, Gb;
function xB() {
  if (Gb) return xp;
  Gb = 1;
  var e = T0(),
    t = oN(),
    n = mi(),
    r = t
      ? function (i, o) {
          return t(i, "toString", { configurable: !0, enumerable: !1, value: e(o), writable: !0 });
        }
      : n;
  return (xp = r), xp;
}
var _p, Wb;
function _B() {
  if (Wb) return _p;
  Wb = 1;
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
  return (_p = r), _p;
}
var Sp, Kb;
function $N() {
  if (Kb) return Sp;
  Kb = 1;
  var e = xB(),
    t = _B(),
    n = t(e);
  return (Sp = n), Sp;
}
var bp, Yb;
function sc() {
  if (Yb) return bp;
  Yb = 1;
  var e = mi(),
    t = qN(),
    n = $N();
  function r(i, o) {
    return n(t(i, o, e), i + "");
  }
  return (bp = r), bp;
}
var Ep, Xb;
function zN() {
  if (Xb) return Ep;
  Xb = 1;
  function e(t, n, r, i) {
    for (var o = t.length, s = r + (i ? 1 : -1); i ? s-- : ++s < o; ) if (n(t[s], s, t)) return s;
    return -1;
  }
  return (Ep = e), Ep;
}
var Cp, Zb;
function SB() {
  if (Zb) return Cp;
  Zb = 1;
  function e(t) {
    return t !== t;
  }
  return (Cp = e), Cp;
}
var Tp, Qb;
function bB() {
  if (Qb) return Tp;
  Qb = 1;
  function e(t, n, r) {
    for (var i = r - 1, o = t.length; ++i < o; ) if (t[i] === n) return i;
    return -1;
  }
  return (Tp = e), Tp;
}
var kp, Jb;
function EB() {
  if (Jb) return kp;
  Jb = 1;
  var e = zN(),
    t = SB(),
    n = bB();
  function r(i, o, s) {
    return o === o ? n(i, o, s) : e(i, t, s);
  }
  return (kp = r), kp;
}
var Pp, eE;
function CB() {
  if (eE) return Pp;
  eE = 1;
  var e = EB();
  function t(n, r) {
    var i = n == null ? 0 : n.length;
    return !!i && e(n, r, 0) > -1;
  }
  return (Pp = t), Pp;
}
var Rp, tE;
function TB() {
  if (tE) return Rp;
  tE = 1;
  function e(t, n, r) {
    for (var i = -1, o = t == null ? 0 : t.length; ++i < o; ) if (r(n, t[i])) return !0;
    return !1;
  }
  return (Rp = e), Rp;
}
var Ap, nE;
function kB() {
  if (nE) return Ap;
  nE = 1;
  function e() {}
  return (Ap = e), Ap;
}
var Np, rE;
function PB() {
  if (rE) return Np;
  rE = 1;
  var e = mN(),
    t = kB(),
    n = R0(),
    r = 1 / 0,
    i =
      e && 1 / n(new e([, -0]))[1] == r
        ? function (o) {
            return new e(o);
          }
        : t;
  return (Np = i), Np;
}
var Mp, iE;
function RB() {
  if (iE) return Mp;
  iE = 1;
  var e = EN(),
    t = CB(),
    n = TB(),
    r = CN(),
    i = PB(),
    o = R0(),
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
  return (Mp = a), Mp;
}
var Ip, oE;
function BN() {
  if (oE) return Ip;
  oE = 1;
  var e = Zn(),
    t = Sn();
  function n(r) {
    return t(r) && e(r);
  }
  return (Ip = n), Ip;
}
var Dp, sE;
function AB() {
  if (sE) return Dp;
  sE = 1;
  var e = N0(),
    t = sc(),
    n = RB(),
    r = BN(),
    i = t(function (o) {
      return n(e(o, 1, r, !0));
    });
  return (Dp = i), Dp;
}
var Op, aE;
function NB() {
  if (aE) return Op;
  aE = 1;
  var e = rc();
  function t(n, r) {
    return e(r, function (i) {
      return n[i];
    });
  }
  return (Op = t), Op;
}
var Lp, uE;
function UN() {
  if (uE) return Lp;
  uE = 1;
  var e = NB(),
    t = Dr();
  function n(r) {
    return r == null ? [] : e(r, t(r));
  }
  return (Lp = n), Lp;
}
var Fp, lE;
function zt() {
  if (lE) return Fp;
  lE = 1;
  var e;
  if (typeof g0 == "function")
    try {
      e = {
        clone: V4(),
        constant: T0(),
        each: bN(),
        filter: DN(),
        has: ON(),
        isArray: Ie(),
        isEmpty: uB(),
        isFunction: fa(),
        isUndefined: LN(),
        keys: Dr(),
        map: VN(),
        reduce: jN(),
        size: gB(),
        transform: vB(),
        union: AB(),
        values: UN(),
      };
    } catch {}
  return e || (e = window._), (Fp = e), Fp;
}
var Vp, cE;
function M0() {
  if (cE) return Vp;
  cE = 1;
  var e = zt();
  Vp = i;
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
  return Vp;
}
var jp, fE;
function MB() {
  return fE || ((fE = 1), (jp = "2.1.8")), jp;
}
var qp, dE;
function IB() {
  return dE || ((dE = 1), (qp = { Graph: M0(), version: MB() })), qp;
}
var $p, hE;
function DB() {
  if (hE) return $p;
  hE = 1;
  var e = zt(),
    t = M0();
  $p = { write: n, read: o };
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
  return $p;
}
var zp, pE;
function OB() {
  if (pE) return zp;
  pE = 1;
  var e = zt();
  zp = t;
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
  return zp;
}
var Bp, mE;
function HN() {
  if (mE) return Bp;
  mE = 1;
  var e = zt();
  Bp = t;
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
            r
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
    Bp
  );
}
var Up, gE;
function GN() {
  if (gE) return Up;
  gE = 1;
  var e = zt(),
    t = HN();
  Up = r;
  var n = e.constant(1);
  function r(o, s, a, u) {
    return i(
      o,
      String(s),
      a || n,
      u ||
        function (l) {
          return o.outEdges(l);
        }
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
            "dijkstra does not allow negative edge weights. Bad edge: " + v + " Weight: " + m
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
  return Up;
}
var Hp, vE;
function LB() {
  if (vE) return Hp;
  vE = 1;
  var e = GN(),
    t = zt();
  Hp = n;
  function n(r, i, o) {
    return t.transform(
      r.nodes(),
      function (s, a) {
        s[a] = e(r, a, i, o);
      },
      {}
    );
  }
  return Hp;
}
var Gp, yE;
function WN() {
  if (yE) return Gp;
  yE = 1;
  var e = zt();
  Gp = t;
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
  return Gp;
}
var Wp, wE;
function FB() {
  if (wE) return Wp;
  wE = 1;
  var e = zt(),
    t = WN();
  Wp = n;
  function n(r) {
    return e.filter(t(r), function (i) {
      return i.length > 1 || (i.length === 1 && r.hasEdge(i[0], i[0]));
    });
  }
  return Wp;
}
var Kp, xE;
function VB() {
  if (xE) return Kp;
  xE = 1;
  var e = zt();
  Kp = n;
  var t = e.constant(1);
  function n(i, o, s) {
    return r(
      i,
      o || t,
      s ||
        function (a) {
          return i.outEdges(a);
        }
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
  return Kp;
}
var Yp, _E;
function KN() {
  if (_E) return Yp;
  _E = 1;
  var e = zt();
  (Yp = t), (t.CycleException = n);
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
  return (n.prototype = new Error()), Yp;
}
var Xp, SE;
function jB() {
  if (SE) return Xp;
  SE = 1;
  var e = KN();
  Xp = t;
  function t(n) {
    try {
      e(n);
    } catch (r) {
      if (r instanceof e.CycleException) return !1;
      throw r;
    }
    return !0;
  }
  return Xp;
}
var Zp, bE;
function YN() {
  if (bE) return Zp;
  bE = 1;
  var e = zt();
  Zp = t;
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
  return Zp;
}
var Qp, EE;
function qB() {
  if (EE) return Qp;
  EE = 1;
  var e = YN();
  Qp = t;
  function t(n, r) {
    return e(n, r, "post");
  }
  return Qp;
}
var Jp, CE;
function $B() {
  if (CE) return Jp;
  CE = 1;
  var e = YN();
  Jp = t;
  function t(n, r) {
    return e(n, r, "pre");
  }
  return Jp;
}
var em, TE;
function zB() {
  if (TE) return em;
  TE = 1;
  var e = zt(),
    t = M0(),
    n = HN();
  em = r;
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
  return em;
}
var tm, kE;
function BB() {
  return (
    kE ||
      ((kE = 1),
      (tm = {
        components: OB(),
        dijkstra: GN(),
        dijkstraAll: LB(),
        findCycles: FB(),
        floydWarshall: VB(),
        isAcyclic: jB(),
        postorder: qB(),
        preorder: $B(),
        prim: zB(),
        tarjan: WN(),
        topsort: KN(),
      })),
    tm
  );
}
var nm, PE;
function UB() {
  if (PE) return nm;
  PE = 1;
  var e = IB();
  return (nm = { Graph: e.Graph, json: DB(), alg: BB(), version: e.version }), nm;
}
var ul;
if (typeof g0 == "function")
  try {
    ul = UB();
  } catch {}
ul || (ul = window.graphlib);
var on = ul,
  rm,
  RE;
function HB() {
  if (RE) return rm;
  RE = 1;
  var e = xN(),
    t = 1,
    n = 4;
  function r(i) {
    return e(i, t | n);
  }
  return (rm = r), rm;
}
var im, AE;
function ac() {
  if (AE) return im;
  AE = 1;
  var e = So(),
    t = Zn(),
    n = Ql(),
    r = $t();
  function i(o, s, a) {
    if (!r(a)) return !1;
    var u = typeof s;
    return (u == "number" ? t(a) && n(s, a.length) : u == "string" && s in a) ? e(a[s], o) : !1;
  }
  return (im = i), im;
}
var om, NE;
function GB() {
  if (NE) return om;
  NE = 1;
  var e = sc(),
    t = So(),
    n = ac(),
    r = pi(),
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
  return (om = s), om;
}
var sm, ME;
function WB() {
  if (ME) return sm;
  ME = 1;
  var e = Qn(),
    t = Zn(),
    n = Dr();
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
  return (sm = r), sm;
}
var am, IE;
function KB() {
  if (IE) return am;
  IE = 1;
  var e = /\s/;
  function t(n) {
    for (var r = n.length; r-- && e.test(n.charAt(r)); );
    return r;
  }
  return (am = t), am;
}
var um, DE;
function YB() {
  if (DE) return um;
  DE = 1;
  var e = KB(),
    t = /^\s+/;
  function n(r) {
    return r && r.slice(0, e(r) + 1).replace(t, "");
  }
  return (um = n), um;
}
var lm, OE;
function XB() {
  if (OE) return lm;
  OE = 1;
  var e = YB(),
    t = $t(),
    n = To(),
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
  return (lm = u), lm;
}
var cm, LE;
function XN() {
  if (LE) return cm;
  LE = 1;
  var e = XB(),
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
  return (cm = r), cm;
}
var fm, FE;
function ZB() {
  if (FE) return fm;
  FE = 1;
  var e = XN();
  function t(n) {
    var r = e(n),
      i = r % 1;
    return r === r ? (i ? r - i : r) : 0;
  }
  return (fm = t), fm;
}
var dm, VE;
function QB() {
  if (VE) return dm;
  VE = 1;
  var e = zN(),
    t = Qn(),
    n = ZB(),
    r = Math.max;
  function i(o, s, a) {
    var u = o == null ? 0 : o.length;
    if (!u) return -1;
    var l = a == null ? 0 : n(a);
    return l < 0 && (l = r(u + l, 0)), e(o, t(s, 3), l);
  }
  return (dm = i), dm;
}
var hm, jE;
function JB() {
  if (jE) return hm;
  jE = 1;
  var e = WB(),
    t = QB(),
    n = e(t);
  return (hm = n), hm;
}
var pm, qE;
function ZN() {
  if (qE) return pm;
  qE = 1;
  var e = N0();
  function t(n) {
    var r = n == null ? 0 : n.length;
    return r ? e(n, 1) : [];
  }
  return (pm = t), pm;
}
var mm, $E;
function e5() {
  if ($E) return mm;
  $E = 1;
  var e = k0(),
    t = _N(),
    n = pi();
  function r(i, o) {
    return i == null ? i : e(i, t(o), n);
  }
  return (mm = r), mm;
}
var gm, zE;
function t5() {
  if (zE) return gm;
  zE = 1;
  function e(t) {
    var n = t == null ? 0 : t.length;
    return n ? t[n - 1] : void 0;
  }
  return (gm = e), gm;
}
var vm, BE;
function n5() {
  if (BE) return vm;
  BE = 1;
  var e = Xl(),
    t = P0(),
    n = Qn();
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
  return (vm = r), vm;
}
var ym, UE;
function I0() {
  if (UE) return ym;
  UE = 1;
  var e = To();
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
  return (ym = t), ym;
}
var wm, HE;
function r5() {
  if (HE) return wm;
  HE = 1;
  function e(t, n) {
    return t > n;
  }
  return (wm = e), wm;
}
var xm, GE;
function i5() {
  if (GE) return xm;
  GE = 1;
  var e = I0(),
    t = r5(),
    n = mi();
  function r(i) {
    return i && i.length ? e(i, n, t) : void 0;
  }
  return (xm = r), xm;
}
var _m, WE;
function QN() {
  if (WE) return _m;
  WE = 1;
  var e = Xl(),
    t = So();
  function n(r, i, o) {
    ((o !== void 0 && !t(r[i], o)) || (o === void 0 && !(i in r))) && e(r, i, o);
  }
  return (_m = n), _m;
}
var Sm, KE;
function o5() {
  if (KE) return Sm;
  KE = 1;
  var e = di(),
    t = tc(),
    n = Sn(),
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
  return (Sm = l), Sm;
}
var bm, YE;
function JN() {
  if (YE) return bm;
  YE = 1;
  function e(t, n) {
    if (!(n === "constructor" && typeof t[n] == "function") && n != "__proto__") return t[n];
  }
  return (bm = e), bm;
}
var Em, XE;
function s5() {
  if (XE) return Em;
  XE = 1;
  var e = da(),
    t = pi();
  function n(r) {
    return e(r, t(r));
  }
  return (Em = n), Em;
}
var Cm, ZE;
function a5() {
  if (ZE) return Cm;
  ZE = 1;
  var e = QN(),
    t = uN(),
    n = vN(),
    r = lN(),
    i = wN(),
    o = ha(),
    s = Ie(),
    a = BN(),
    u = Eo(),
    l = fa(),
    c = $t(),
    f = o5(),
    d = pa(),
    h = JN(),
    v = s5();
  function p(y, m, g, w, x, S, C) {
    var E = h(y, g),
      T = h(m, g),
      P = C.get(T);
    if (P) {
      e(y, g, P);
      return;
    }
    var N = S ? S(E, T, g + "", y, m, C) : void 0,
      I = N === void 0;
    if (I) {
      var V = s(T),
        q = !V && u(T),
        b = !V && !q && d(T);
      (N = T),
        V || q || b
          ? s(E)
            ? (N = E)
            : a(E)
            ? (N = r(E))
            : q
            ? ((I = !1), (N = t(T, !0)))
            : b
            ? ((I = !1), (N = n(T, !0)))
            : (N = [])
          : f(T) || o(T)
          ? ((N = E), o(E) ? (N = v(E)) : (!c(E) || l(E)) && (N = i(T)))
          : (I = !1);
    }
    I && (C.set(T, N), x(N, T, w, S, C), C.delete(T)), e(y, g, N);
  }
  return (Cm = p), Cm;
}
var Tm, QE;
function u5() {
  if (QE) return Tm;
  QE = 1;
  var e = Yl(),
    t = QN(),
    n = k0(),
    r = a5(),
    i = $t(),
    o = pi(),
    s = JN();
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
        o
      );
  }
  return (Tm = a), Tm;
}
var km, JE;
function l5() {
  if (JE) return km;
  JE = 1;
  var e = sc(),
    t = ac();
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
  return (km = n), km;
}
var Pm, eC;
function c5() {
  if (eC) return Pm;
  eC = 1;
  var e = u5(),
    t = l5(),
    n = t(function (r, i, o) {
      e(r, i, o);
    });
  return (Pm = n), Pm;
}
var Rm, tC;
function eM() {
  if (tC) return Rm;
  tC = 1;
  function e(t, n) {
    return t < n;
  }
  return (Rm = e), Rm;
}
var Am, nC;
function f5() {
  if (nC) return Am;
  nC = 1;
  var e = I0(),
    t = eM(),
    n = mi();
  function r(i) {
    return i && i.length ? e(i, n, t) : void 0;
  }
  return (Am = r), Am;
}
var Nm, rC;
function d5() {
  if (rC) return Nm;
  rC = 1;
  var e = I0(),
    t = Qn(),
    n = eM();
  function r(i, o) {
    return i && i.length ? e(i, t(o, 2), n) : void 0;
  }
  return (Nm = r), Nm;
}
var Mm, iC;
function h5() {
  if (iC) return Mm;
  iC = 1;
  var e = rn(),
    t = function () {
      return e.Date.now();
    };
  return (Mm = t), Mm;
}
var Im, oC;
function p5() {
  if (oC) return Im;
  oC = 1;
  var e = Zl(),
    t = ic(),
    n = Ql(),
    r = $t(),
    i = ma();
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
  return (Im = o), Im;
}
var Dm, sC;
function m5() {
  if (sC) return Dm;
  sC = 1;
  var e = oc(),
    t = p5(),
    n = ic();
  function r(i, o, s) {
    for (var a = -1, u = o.length, l = {}; ++a < u; ) {
      var c = o[a],
        f = e(i, c);
      s(f, c) && t(l, n(c, i), f);
    }
    return l;
  }
  return (Dm = r), Dm;
}
var Om, aC;
function g5() {
  if (aC) return Om;
  aC = 1;
  var e = m5(),
    t = MN();
  function n(r, i) {
    return e(r, i, function (o, s) {
      return t(r, s);
    });
  }
  return (Om = n), Om;
}
var Lm, uC;
function v5() {
  if (uC) return Lm;
  uC = 1;
  var e = ZN(),
    t = qN(),
    n = $N();
  function r(i) {
    return n(t(i, void 0, e), i + "");
  }
  return (Lm = r), Lm;
}
var Fm, lC;
function y5() {
  if (lC) return Fm;
  lC = 1;
  var e = g5(),
    t = v5(),
    n = t(function (r, i) {
      return r == null ? {} : e(r, i);
    });
  return (Fm = n), Fm;
}
var Vm, cC;
function w5() {
  if (cC) return Vm;
  cC = 1;
  var e = Math.ceil,
    t = Math.max;
  function n(r, i, o, s) {
    for (var a = -1, u = t(e((i - r) / (o || 1)), 0), l = Array(u); u--; )
      (l[s ? u : ++a] = r), (r += o);
    return l;
  }
  return (Vm = n), Vm;
}
var jm, fC;
function x5() {
  if (fC) return jm;
  fC = 1;
  var e = w5(),
    t = ac(),
    n = XN();
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
  return (jm = r), jm;
}
var qm, dC;
function _5() {
  if (dC) return qm;
  dC = 1;
  var e = x5(),
    t = e();
  return (qm = t), qm;
}
var $m, hC;
function S5() {
  if (hC) return $m;
  hC = 1;
  function e(t, n) {
    var r = t.length;
    for (t.sort(n); r--; ) t[r] = t[r].value;
    return t;
  }
  return ($m = e), $m;
}
var zm, pC;
function b5() {
  if (pC) return zm;
  pC = 1;
  var e = To();
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
  return (zm = t), zm;
}
var Bm, mC;
function E5() {
  if (mC) return Bm;
  mC = 1;
  var e = b5();
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
  return (Bm = t), Bm;
}
var Um, gC;
function C5() {
  if (gC) return Um;
  gC = 1;
  var e = rc(),
    t = oc(),
    n = Qn(),
    r = FN(),
    i = S5(),
    o = Jl(),
    s = E5(),
    a = mi(),
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
  return (Um = l), Um;
}
var Hm, vC;
function T5() {
  if (vC) return Hm;
  vC = 1;
  var e = N0(),
    t = C5(),
    n = sc(),
    r = ac(),
    i = n(function (o, s) {
      if (o == null) return [];
      var a = s.length;
      return (
        a > 1 && r(o, s[0], s[1]) ? (s = []) : a > 2 && r(s[0], s[1], s[2]) && (s = [s[0]]),
        t(o, e(s, 1), [])
      );
    });
  return (Hm = i), Hm;
}
var Gm, yC;
function k5() {
  if (yC) return Gm;
  yC = 1;
  var e = AN(),
    t = 0;
  function n(r) {
    var i = ++t;
    return e(r) + i;
  }
  return (Gm = n), Gm;
}
var Wm, wC;
function P5() {
  if (wC) return Wm;
  wC = 1;
  function e(t, n, r) {
    for (var i = -1, o = t.length, s = n.length, a = {}; ++i < o; ) {
      var u = i < s ? n[i] : void 0;
      r(a, t[i], u);
    }
    return a;
  }
  return (Wm = e), Wm;
}
var Km, xC;
function R5() {
  if (xC) return Km;
  xC = 1;
  var e = Zl(),
    t = P5();
  function n(r, i) {
    return t(r || [], i || [], e);
  }
  return (Km = n), Km;
}
var ll;
if (typeof g0 == "function")
  try {
    ll = {
      cloneDeep: HB(),
      constant: T0(),
      defaults: GB(),
      each: bN(),
      filter: DN(),
      find: JB(),
      flatten: ZN(),
      forEach: SN(),
      forIn: e5(),
      has: ON(),
      isUndefined: LN(),
      last: t5(),
      map: VN(),
      mapValues: n5(),
      max: i5(),
      merge: c5(),
      min: f5(),
      minBy: d5(),
      now: h5(),
      pick: y5(),
      range: _5(),
      reduce: jN(),
      sortBy: T5(),
      uniqueId: k5(),
      values: UN(),
      zipObject: R5(),
    };
  } catch {}
ll || (ll = window._);
var ye = ll,
  A5 = uc;
function uc() {
  var e = {};
  (e._next = e._prev = e), (this._sentinel = e);
}
uc.prototype.dequeue = function () {
  var e = this._sentinel,
    t = e._prev;
  if (t !== e) return tM(t), t;
};
uc.prototype.enqueue = function (e) {
  var t = this._sentinel;
  e._prev && e._next && tM(e),
    (e._next = t._next),
    (t._next._prev = e),
    (t._next = e),
    (e._prev = t);
};
uc.prototype.toString = function () {
  for (var e = [], t = this._sentinel, n = t._prev; n !== t; )
    e.push(JSON.stringify(n, N5)), (n = n._prev);
  return "[" + e.join(", ") + "]";
};
function tM(e) {
  (e._prev._next = e._next), (e._next._prev = e._prev), delete e._next, delete e._prev;
}
function N5(e, t) {
  if (e !== "_next" && e !== "_prev") return t;
}
var On = ye,
  M5 = on.Graph,
  I5 = A5,
  D5 = L5,
  O5 = On.constant(1);
function L5(e, t) {
  if (e.nodeCount() <= 1) return [];
  var n = V5(e, t || O5),
    r = F5(n.graph, n.buckets, n.zeroIdx);
  return On.flatten(
    On.map(r, function (i) {
      return e.outEdges(i.v, i.w);
    }),
    !0
  );
}
function F5(e, t, n) {
  for (var r = [], i = t[t.length - 1], o = t[0], s; e.nodeCount(); ) {
    for (; (s = o.dequeue()); ) Ym(e, t, n, s);
    for (; (s = i.dequeue()); ) Ym(e, t, n, s);
    if (e.nodeCount()) {
      for (var a = t.length - 2; a > 0; --a)
        if (((s = t[a].dequeue()), s)) {
          r = r.concat(Ym(e, t, n, s, !0));
          break;
        }
    }
  }
  return r;
}
function Ym(e, t, n, r, i) {
  var o = i ? [] : void 0;
  return (
    On.forEach(e.inEdges(r.v), function (s) {
      var a = e.edge(s),
        u = e.node(s.v);
      i && o.push({ v: s.v, w: s.w }), (u.out -= a), Dv(t, n, u);
    }),
    On.forEach(e.outEdges(r.v), function (s) {
      var a = e.edge(s),
        u = s.w,
        l = e.node(u);
      (l.in -= a), Dv(t, n, l);
    }),
    e.removeNode(r.v),
    o
  );
}
function V5(e, t) {
  var n = new M5(),
    r = 0,
    i = 0;
  On.forEach(e.nodes(), function (a) {
    n.setNode(a, { v: a, in: 0, out: 0 });
  }),
    On.forEach(e.edges(), function (a) {
      var u = n.edge(a.v, a.w) || 0,
        l = t(a),
        c = u + l;
      n.setEdge(a.v, a.w, c),
        (i = Math.max(i, (n.node(a.v).out += l))),
        (r = Math.max(r, (n.node(a.w).in += l)));
    });
  var o = On.range(i + r + 3).map(function () {
      return new I5();
    }),
    s = r + 1;
  return (
    On.forEach(n.nodes(), function (a) {
      Dv(o, s, n.node(a));
    }),
    { graph: n, buckets: o, zeroIdx: s }
  );
}
function Dv(e, t, n) {
  n.out ? (n.in ? e[n.out - n.in + t].enqueue(n) : e[e.length - 1].enqueue(n)) : e[0].enqueue(n);
}
var Yr = ye,
  j5 = D5,
  q5 = { run: $5, undo: B5 };
function $5(e) {
  var t = e.graph().acyclicer === "greedy" ? j5(e, n(e)) : z5(e);
  Yr.forEach(t, function (r) {
    var i = e.edge(r);
    e.removeEdge(r),
      (i.forwardName = r.name),
      (i.reversed = !0),
      e.setEdge(r.w, r.v, i, Yr.uniqueId("rev"));
  });
  function n(r) {
    return function (i) {
      return r.edge(i).weight;
    };
  }
}
function z5(e) {
  var t = [],
    n = {},
    r = {};
  function i(o) {
    Yr.has(r, o) ||
      ((r[o] = !0),
      (n[o] = !0),
      Yr.forEach(e.outEdges(o), function (s) {
        Yr.has(n, s.w) ? t.push(s) : i(s.w);
      }),
      delete n[o]);
  }
  return Yr.forEach(e.nodes(), i), t;
}
function B5(e) {
  Yr.forEach(e.edges(), function (t) {
    var n = e.edge(t);
    if (n.reversed) {
      e.removeEdge(t);
      var r = n.forwardName;
      delete n.reversed, delete n.forwardName, e.setEdge(t.w, t.v, n, r);
    }
  });
}
var le = ye,
  nM = on.Graph,
  wt = {
    addDummyNode: rM,
    simplify: U5,
    asNonCompoundGraph: H5,
    successorWeights: G5,
    predecessorWeights: W5,
    intersectRect: K5,
    buildLayerMatrix: Y5,
    normalizeRanks: X5,
    removeEmptyRanks: Z5,
    addBorderNode: Q5,
    maxRank: iM,
    partition: J5,
    time: e8,
    notime: t8,
  };
function rM(e, t, n, r) {
  var i;
  do i = le.uniqueId(r);
  while (e.hasNode(i));
  return (n.dummy = t), e.setNode(i, n), i;
}
function U5(e) {
  var t = new nM().setGraph(e.graph());
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
function H5(e) {
  var t = new nM({ multigraph: e.isMultigraph() }).setGraph(e.graph());
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
function G5(e) {
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
function W5(e) {
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
function K5(e, t) {
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
function Y5(e) {
  var t = le.map(le.range(iM(e) + 1), function () {
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
function X5(e) {
  var t = le.min(
    le.map(e.nodes(), function (n) {
      return e.node(n).rank;
    })
  );
  le.forEach(e.nodes(), function (n) {
    var r = e.node(n);
    le.has(r, "rank") && (r.rank -= t);
  });
}
function Z5(e) {
  var t = le.min(
      le.map(e.nodes(), function (o) {
        return e.node(o).rank;
      })
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
function Q5(e, t, n, r) {
  var i = { width: 0, height: 0 };
  return arguments.length >= 4 && ((i.rank = n), (i.order = r)), rM(e, "border", i, t);
}
function iM(e) {
  return le.max(
    le.map(e.nodes(), function (t) {
      var n = e.node(t).rank;
      if (!le.isUndefined(n)) return n;
    })
  );
}
function J5(e, t) {
  var n = { lhs: [], rhs: [] };
  return (
    le.forEach(e, function (r) {
      t(r) ? n.lhs.push(r) : n.rhs.push(r);
    }),
    n
  );
}
function e8(e, t) {
  var n = le.now();
  try {
    return t();
  } finally {
    console.log(e + " time: " + (le.now() - n) + "ms");
  }
}
function t8(e, t) {
  return t();
}
var oM = ye,
  n8 = wt,
  r8 = { run: i8, undo: s8 };
function i8(e) {
  (e.graph().dummyChains = []),
    oM.forEach(e.edges(), function (t) {
      o8(e, t);
    });
}
function o8(e, t) {
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
        (l = n8.addDummyNode(e, "edge", c, "_d")),
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
function s8(e) {
  oM.forEach(e.graph().dummyChains, function (t) {
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
var Ya = ye,
  lc = { longestPath: a8, slack: u8 };
function a8(e) {
  var t = {};
  function n(r) {
    var i = e.node(r);
    if (Ya.has(t, r)) return i.rank;
    t[r] = !0;
    var o = Ya.min(
      Ya.map(e.outEdges(r), function (s) {
        return n(s.w) - e.edge(s).minlen;
      })
    );
    return (o === Number.POSITIVE_INFINITY || o === void 0 || o === null) && (o = 0), (i.rank = o);
  }
  Ya.forEach(e.sources(), n);
}
function u8(e, t) {
  return e.node(t.w).rank - e.node(t.v).rank - e.edge(t).minlen;
}
var cl = ye,
  l8 = on.Graph,
  fl = lc.slack,
  sM = c8;
function c8(e) {
  var t = new l8({ directed: !1 }),
    n = e.nodes()[0],
    r = e.nodeCount();
  t.setNode(n, {});
  for (var i, o; f8(t, e) < r; )
    (i = d8(t, e)), (o = t.hasNode(i.v) ? fl(e, i) : -fl(e, i)), h8(t, e, o);
  return t;
}
function f8(e, t) {
  function n(r) {
    cl.forEach(t.nodeEdges(r), function (i) {
      var o = i.v,
        s = r === o ? i.w : o;
      !e.hasNode(s) && !fl(t, i) && (e.setNode(s, {}), e.setEdge(r, s, {}), n(s));
    });
  }
  return cl.forEach(e.nodes(), n), e.nodeCount();
}
function d8(e, t) {
  return cl.minBy(t.edges(), function (n) {
    if (e.hasNode(n.v) !== e.hasNode(n.w)) return fl(t, n);
  });
}
function h8(e, t, n) {
  cl.forEach(e.nodes(), function (r) {
    t.node(r).rank += n;
  });
}
var Wn = ye,
  p8 = sM,
  m8 = lc.slack,
  g8 = lc.longestPath,
  v8 = on.alg.preorder,
  y8 = on.alg.postorder,
  w8 = wt.simplify,
  x8 = gi;
gi.initLowLimValues = O0;
gi.initCutValues = D0;
gi.calcCutValue = aM;
gi.leaveEdge = lM;
gi.enterEdge = cM;
gi.exchangeEdges = fM;
function gi(e) {
  (e = w8(e)), g8(e);
  var t = p8(e);
  O0(t), D0(t, e);
  for (var n, r; (n = lM(t)); ) (r = cM(t, e, n)), fM(t, e, n, r);
}
function D0(e, t) {
  var n = y8(e, e.nodes());
  (n = n.slice(0, n.length - 1)),
    Wn.forEach(n, function (r) {
      _8(e, t, r);
    });
}
function _8(e, t, n) {
  var r = e.node(n),
    i = r.parent;
  e.edge(n, i).cutvalue = aM(e, t, n);
}
function aM(e, t, n) {
  var r = e.node(n),
    i = r.parent,
    o = !0,
    s = t.edge(n, i),
    a = 0;
  return (
    s || ((o = !1), (s = t.edge(i, n))),
    (a = s.weight),
    Wn.forEach(t.nodeEdges(n), function (u) {
      var l = u.v === n,
        c = l ? u.w : u.v;
      if (c !== i) {
        var f = l === o,
          d = t.edge(u).weight;
        if (((a += f ? d : -d), b8(e, n, c))) {
          var h = e.edge(n, c).cutvalue;
          a += f ? -h : h;
        }
      }
    }),
    a
  );
}
function O0(e, t) {
  arguments.length < 2 && (t = e.nodes()[0]), uM(e, {}, 1, t);
}
function uM(e, t, n, r, i) {
  var o = n,
    s = e.node(r);
  return (
    (t[r] = !0),
    Wn.forEach(e.neighbors(r), function (a) {
      Wn.has(t, a) || (n = uM(e, t, n, a, r));
    }),
    (s.low = o),
    (s.lim = n++),
    i ? (s.parent = i) : delete s.parent,
    n
  );
}
function lM(e) {
  return Wn.find(e.edges(), function (t) {
    return e.edge(t).cutvalue < 0;
  });
}
function cM(e, t, n) {
  var r = n.v,
    i = n.w;
  t.hasEdge(r, i) || ((r = n.w), (i = n.v));
  var o = e.node(r),
    s = e.node(i),
    a = o,
    u = !1;
  o.lim > s.lim && ((a = s), (u = !0));
  var l = Wn.filter(t.edges(), function (c) {
    return u === _C(e, e.node(c.v), a) && u !== _C(e, e.node(c.w), a);
  });
  return Wn.minBy(l, function (c) {
    return m8(t, c);
  });
}
function fM(e, t, n, r) {
  var i = n.v,
    o = n.w;
  e.removeEdge(i, o), e.setEdge(r.v, r.w, {}), O0(e), D0(e, t), S8(e, t);
}
function S8(e, t) {
  var n = Wn.find(e.nodes(), function (i) {
      return !t.node(i).parent;
    }),
    r = v8(e, n);
  (r = r.slice(1)),
    Wn.forEach(r, function (i) {
      var o = e.node(i).parent,
        s = t.edge(i, o),
        a = !1;
      s || ((s = t.edge(o, i)), (a = !0)),
        (t.node(i).rank = t.node(o).rank + (a ? s.minlen : -s.minlen));
    });
}
function b8(e, t, n) {
  return e.hasEdge(t, n);
}
function _C(e, t, n) {
  return n.low <= t.lim && t.lim <= n.lim;
}
var E8 = lc,
  dM = E8.longestPath,
  C8 = sM,
  T8 = x8,
  k8 = P8;
function P8(e) {
  switch (e.graph().ranker) {
    case "network-simplex":
      SC(e);
      break;
    case "tight-tree":
      A8(e);
      break;
    case "longest-path":
      R8(e);
      break;
    default:
      SC(e);
  }
}
var R8 = dM;
function A8(e) {
  dM(e), C8(e);
}
function SC(e) {
  T8(e);
}
var Ov = ye,
  N8 = M8;
function M8(e) {
  var t = D8(e);
  Ov.forEach(e.graph().dummyChains, function (n) {
    for (
      var r = e.node(n),
        i = r.edgeObj,
        o = I8(e, t, i.v, i.w),
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
function I8(e, t, n, r) {
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
function D8(e) {
  var t = {},
    n = 0;
  function r(i) {
    var o = n;
    Ov.forEach(e.children(i), r), (t[i] = { low: o, lim: n++ });
  }
  return Ov.forEach(e.children(), r), t;
}
var Ln = ye,
  Lv = wt,
  O8 = { run: L8, cleanup: j8 };
function L8(e) {
  var t = Lv.addDummyNode(e, "root", {}, "_root"),
    n = F8(e),
    r = Ln.max(Ln.values(n)) - 1,
    i = 2 * r + 1;
  (e.graph().nestingRoot = t),
    Ln.forEach(e.edges(), function (s) {
      e.edge(s).minlen *= i;
    });
  var o = V8(e) + 1;
  Ln.forEach(e.children(), function (s) {
    hM(e, t, i, o, r, n, s);
  }),
    (e.graph().nodeRankFactor = i);
}
function hM(e, t, n, r, i, o, s) {
  var a = e.children(s);
  if (!a.length) {
    s !== t && e.setEdge(t, s, { weight: 0, minlen: n });
    return;
  }
  var u = Lv.addBorderNode(e, "_bt"),
    l = Lv.addBorderNode(e, "_bb"),
    c = e.node(s);
  e.setParent(u, s),
    (c.borderTop = u),
    e.setParent(l, s),
    (c.borderBottom = l),
    Ln.forEach(a, function (f) {
      hM(e, t, n, r, i, o, f);
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
function F8(e) {
  var t = {};
  function n(r, i) {
    var o = e.children(r);
    o &&
      o.length &&
      Ln.forEach(o, function (s) {
        n(s, i + 1);
      }),
      (t[r] = i);
  }
  return (
    Ln.forEach(e.children(), function (r) {
      n(r, 1);
    }),
    t
  );
}
function V8(e) {
  return Ln.reduce(
    e.edges(),
    function (t, n) {
      return t + e.edge(n).weight;
    },
    0
  );
}
function j8(e) {
  var t = e.graph();
  e.removeNode(t.nestingRoot),
    delete t.nestingRoot,
    Ln.forEach(e.edges(), function (n) {
      var r = e.edge(n);
      r.nestingEdge && e.removeEdge(n);
    });
}
var Xm = ye,
  q8 = wt,
  $8 = z8;
function z8(e) {
  function t(n) {
    var r = e.children(n),
      i = e.node(n);
    if ((r.length && Xm.forEach(r, t), Xm.has(i, "minRank"))) {
      (i.borderLeft = []), (i.borderRight = []);
      for (var o = i.minRank, s = i.maxRank + 1; o < s; ++o)
        bC(e, "borderLeft", "_bl", n, i, o), bC(e, "borderRight", "_br", n, i, o);
    }
  }
  Xm.forEach(e.children(), t);
}
function bC(e, t, n, r, i, o) {
  var s = { width: 0, height: 0, rank: o, borderType: t },
    a = i[t][o - 1],
    u = q8.addDummyNode(e, "border", s, n);
  (i[t][o] = u), e.setParent(u, r), a && e.setEdge(a, u, { weight: 1 });
}
var pn = ye,
  B8 = { adjust: U8, undo: H8 };
function U8(e) {
  var t = e.graph().rankdir.toLowerCase();
  (t === "lr" || t === "rl") && pM(e);
}
function H8(e) {
  var t = e.graph().rankdir.toLowerCase();
  (t === "bt" || t === "rl") && G8(e), (t === "lr" || t === "rl") && (W8(e), pM(e));
}
function pM(e) {
  pn.forEach(e.nodes(), function (t) {
    EC(e.node(t));
  }),
    pn.forEach(e.edges(), function (t) {
      EC(e.edge(t));
    });
}
function EC(e) {
  var t = e.width;
  (e.width = e.height), (e.height = t);
}
function G8(e) {
  pn.forEach(e.nodes(), function (t) {
    Zm(e.node(t));
  }),
    pn.forEach(e.edges(), function (t) {
      var n = e.edge(t);
      pn.forEach(n.points, Zm), pn.has(n, "y") && Zm(n);
    });
}
function Zm(e) {
  e.y = -e.y;
}
function W8(e) {
  pn.forEach(e.nodes(), function (t) {
    Qm(e.node(t));
  }),
    pn.forEach(e.edges(), function (t) {
      var n = e.edge(t);
      pn.forEach(n.points, Qm), pn.has(n, "x") && Qm(n);
    });
}
function Qm(e) {
  var t = e.x;
  (e.x = e.y), (e.y = t);
}
var Pn = ye,
  K8 = Y8;
function Y8(e) {
  var t = {},
    n = Pn.filter(e.nodes(), function (a) {
      return !e.children(a).length;
    }),
    r = Pn.max(
      Pn.map(n, function (a) {
        return e.node(a).rank;
      })
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
var nr = ye,
  X8 = Z8;
function Z8(e, t) {
  for (var n = 0, r = 1; r < t.length; ++r) n += Q8(e, t[r - 1], t[r]);
  return n;
}
function Q8(e, t, n) {
  for (
    var r = nr.zipObject(
        n,
        nr.map(n, function (l, c) {
          return c;
        })
      ),
      i = nr.flatten(
        nr.map(t, function (l) {
          return nr.sortBy(
            nr.map(e.outEdges(l), function (c) {
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
  var s = 2 * o - 1;
  o -= 1;
  var a = nr.map(new Array(s), function () {
      return 0;
    }),
    u = 0;
  return (
    nr.forEach(
      i.forEach(function (l) {
        var c = l.pos + o;
        a[c] += l.weight;
        for (var f = 0; c > 0; ) c % 2 && (f += a[c + 1]), (c = (c - 1) >> 1), (a[c] += l.weight);
        u += l.weight * f;
      })
    ),
    u
  );
}
var CC = ye,
  J8 = e6;
function e6(e, t) {
  return CC.map(t, function (n) {
    var r = e.inEdges(n);
    if (r.length) {
      var i = CC.reduce(
        r,
        function (o, s) {
          var a = e.edge(s),
            u = e.node(s.v);
          return { sum: o.sum + a.weight * u.order, weight: o.weight + a.weight };
        },
        { sum: 0, weight: 0 }
      );
      return { v: n, barycenter: i.sum / i.weight, weight: i.weight };
    } else return { v: n };
  });
}
var St = ye,
  t6 = n6;
function n6(e, t) {
  var n = {};
  St.forEach(e, function (i, o) {
    var s = (n[i.v] = { indegree: 0, in: [], out: [], vs: [i.v], i: o });
    St.isUndefined(i.barycenter) || ((s.barycenter = i.barycenter), (s.weight = i.weight));
  }),
    St.forEach(t.edges(), function (i) {
      var o = n[i.v],
        s = n[i.w];
      !St.isUndefined(o) && !St.isUndefined(s) && (s.indegree++, o.out.push(n[i.w]));
    });
  var r = St.filter(n, function (i) {
    return !i.indegree;
  });
  return r6(r);
}
function r6(e) {
  var t = [];
  function n(o) {
    return function (s) {
      s.merged ||
        ((St.isUndefined(s.barycenter) ||
          St.isUndefined(o.barycenter) ||
          s.barycenter >= o.barycenter) &&
          i6(o, s));
    };
  }
  function r(o) {
    return function (s) {
      s.in.push(o), --s.indegree === 0 && e.push(s);
    };
  }
  for (; e.length; ) {
    var i = e.pop();
    t.push(i), St.forEach(i.in.reverse(), n(i)), St.forEach(i.out, r(i));
  }
  return St.map(
    St.filter(t, function (o) {
      return !o.merged;
    }),
    function (o) {
      return St.pick(o, ["vs", "i", "barycenter", "weight"]);
    }
  );
}
function i6(e, t) {
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
var is = ye,
  o6 = wt,
  s6 = a6;
function a6(e, t) {
  var n = o6.partition(e, function (c) {
      return is.has(c, "barycenter");
    }),
    r = n.lhs,
    i = is.sortBy(n.rhs, function (c) {
      return -c.i;
    }),
    o = [],
    s = 0,
    a = 0,
    u = 0;
  r.sort(u6(!!t)),
    (u = TC(o, i, u)),
    is.forEach(r, function (c) {
      (u += c.vs.length),
        o.push(c.vs),
        (s += c.barycenter * c.weight),
        (a += c.weight),
        (u = TC(o, i, u));
    });
  var l = { vs: is.flatten(o, !0) };
  return a && ((l.barycenter = s / a), (l.weight = a)), l;
}
function TC(e, t, n) {
  for (var r; t.length && (r = is.last(t)).i <= n; ) t.pop(), e.push(r.vs), n++;
  return n;
}
function u6(e) {
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
var pr = ye,
  l6 = J8,
  c6 = t6,
  f6 = s6,
  d6 = mM;
function mM(e, t, n, r) {
  var i = e.children(t),
    o = e.node(t),
    s = o ? o.borderLeft : void 0,
    a = o ? o.borderRight : void 0,
    u = {};
  s &&
    (i = pr.filter(i, function (v) {
      return v !== s && v !== a;
    }));
  var l = l6(e, i);
  pr.forEach(l, function (v) {
    if (e.children(v.v).length) {
      var p = mM(e, v.v, n, r);
      (u[v.v] = p), pr.has(p, "barycenter") && p6(v, p);
    }
  });
  var c = c6(l, n);
  h6(c, u);
  var f = f6(c, r);
  if (s && ((f.vs = pr.flatten([s, f.vs, a], !0)), e.predecessors(s).length)) {
    var d = e.node(e.predecessors(s)[0]),
      h = e.node(e.predecessors(a)[0]);
    pr.has(f, "barycenter") || ((f.barycenter = 0), (f.weight = 0)),
      (f.barycenter = (f.barycenter * f.weight + d.order + h.order) / (f.weight + 2)),
      (f.weight += 2);
  }
  return f;
}
function h6(e, t) {
  pr.forEach(e, function (n) {
    n.vs = pr.flatten(
      n.vs.map(function (r) {
        return t[r] ? t[r].vs : r;
      }),
      !0
    );
  });
}
function p6(e, t) {
  pr.isUndefined(e.barycenter)
    ? ((e.barycenter = t.barycenter), (e.weight = t.weight))
    : ((e.barycenter = (e.barycenter * e.weight + t.barycenter * t.weight) / (e.weight + t.weight)),
      (e.weight += t.weight));
}
var os = ye,
  m6 = on.Graph,
  g6 = v6;
function v6(e, t, n) {
  var r = y6(e),
    i = new m6({ compound: !0 }).setGraph({ root: r }).setDefaultNodeLabel(function (o) {
      return e.node(o);
    });
  return (
    os.forEach(e.nodes(), function (o) {
      var s = e.node(o),
        a = e.parent(o);
      (s.rank === t || (s.minRank <= t && t <= s.maxRank)) &&
        (i.setNode(o),
        i.setParent(o, a || r),
        os.forEach(e[n](o), function (u) {
          var l = u.v === o ? u.w : u.v,
            c = i.edge(l, o),
            f = os.isUndefined(c) ? 0 : c.weight;
          i.setEdge(l, o, { weight: e.edge(u).weight + f });
        }),
        os.has(s, "minRank") &&
          i.setNode(o, { borderLeft: s.borderLeft[t], borderRight: s.borderRight[t] }));
    }),
    i
  );
}
function y6(e) {
  for (var t; e.hasNode((t = os.uniqueId("_root"))); );
  return t;
}
var w6 = ye,
  x6 = _6;
function _6(e, t, n) {
  var r = {},
    i;
  w6.forEach(n, function (o) {
    for (var s = e.parent(o), a, u; s; ) {
      if (((a = e.parent(s)), a ? ((u = r[a]), (r[a] = s)) : ((u = i), (i = s)), u && u !== s)) {
        t.setEdge(u, s);
        return;
      }
      s = a;
    }
  });
}
var Tr = ye,
  S6 = K8,
  b6 = X8,
  E6 = d6,
  C6 = g6,
  T6 = x6,
  k6 = on.Graph,
  kC = wt,
  P6 = R6;
function R6(e) {
  var t = kC.maxRank(e),
    n = PC(e, Tr.range(1, t + 1), "inEdges"),
    r = PC(e, Tr.range(t - 1, -1, -1), "outEdges"),
    i = S6(e);
  RC(e, i);
  for (var o = Number.POSITIVE_INFINITY, s, a = 0, u = 0; u < 4; ++a, ++u) {
    A6(a % 2 ? n : r, a % 4 >= 2), (i = kC.buildLayerMatrix(e));
    var l = b6(e, i);
    l < o && ((u = 0), (s = Tr.cloneDeep(i)), (o = l));
  }
  RC(e, s);
}
function PC(e, t, n) {
  return Tr.map(t, function (r) {
    return C6(e, r, n);
  });
}
function A6(e, t) {
  var n = new k6();
  Tr.forEach(e, function (r) {
    var i = r.graph().root,
      o = E6(r, i, n, t);
    Tr.forEach(o.vs, function (s, a) {
      r.node(s).order = a;
    }),
      T6(r, n, o.vs);
  });
}
function RC(e, t) {
  Tr.forEach(t, function (n) {
    Tr.forEach(n, function (r, i) {
      e.node(r).order = i;
    });
  });
}
var J = ye,
  N6 = on.Graph,
  M6 = wt,
  I6 = { positionX: U6 };
function D6(e, t) {
  var n = {};
  function r(i, o) {
    var s = 0,
      a = 0,
      u = i.length,
      l = J.last(o);
    return (
      J.forEach(o, function (c, f) {
        var d = L6(e, c),
          h = d ? e.node(d).order : u;
        (d || c === l) &&
          (J.forEach(o.slice(a, f + 1), function (v) {
            J.forEach(e.predecessors(v), function (p) {
              var y = e.node(p),
                m = y.order;
              (m < s || h < m) && !(y.dummy && e.node(v).dummy) && gM(n, p, v);
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
function O6(e, t) {
  var n = {};
  function r(o, s, a, u, l) {
    var c;
    J.forEach(J.range(s, a), function (f) {
      (c = o[f]),
        e.node(c).dummy &&
          J.forEach(e.predecessors(c), function (d) {
            var h = e.node(d);
            h.dummy && (h.order < u || h.order > l) && gM(n, d, c);
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
function L6(e, t) {
  if (e.node(t).dummy)
    return J.find(e.predecessors(t), function (n) {
      return e.node(n).dummy;
    });
}
function gM(e, t, n) {
  if (t > n) {
    var r = t;
    (t = n), (n = r);
  }
  var i = e[t];
  i || (e[t] = i = {}), (i[n] = !0);
}
function F6(e, t, n) {
  if (t > n) {
    var r = t;
    (t = n), (n = r);
  }
  return J.has(e[t], n);
}
function V6(e, t, n, r) {
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
              !F6(n, l, v) &&
              ((o[v] = l), (o[l] = i[l] = i[v]), (u = s[v]));
          }
        }
      });
    }),
    { root: i, align: o }
  );
}
function j6(e, t, n, r, i) {
  var o = {},
    s = q6(e, t, n, i),
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
function q6(e, t, n, r) {
  var i = new N6(),
    o = e.graph(),
    s = H6(o.nodesep, o.edgesep, r);
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
function $6(e, t) {
  return J.minBy(J.values(t), function (n) {
    var r = Number.NEGATIVE_INFINITY,
      i = Number.POSITIVE_INFINITY;
    return (
      J.forIn(n, function (o, s) {
        var a = G6(e, s) / 2;
        (r = Math.max(o + a, r)), (i = Math.min(o - a, i));
      }),
      r - i
    );
  });
}
function z6(e, t) {
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
function B6(e, t) {
  return J.mapValues(e.ul, function (n, r) {
    if (t) return e[t.toLowerCase()][r];
    var i = J.sortBy(J.map(e, r));
    return (i[1] + i[2]) / 2;
  });
}
function U6(e) {
  var t = M6.buildLayerMatrix(e),
    n = J.merge(D6(e, t), O6(e, t)),
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
          l = V6(e, i, n, u),
          c = j6(e, i, l.root, l.align, a === "r");
        a === "r" &&
          (c = J.mapValues(c, function (f) {
            return -f;
          })),
          (r[s + a] = c);
      });
  });
  var o = $6(e, r);
  return z6(r, o), B6(r, e.graph().align);
}
function H6(e, t, n) {
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
function G6(e, t) {
  return e.node(t).width;
}
var ss = ye,
  vM = wt,
  W6 = I6.positionX,
  K6 = Y6;
function Y6(e) {
  (e = vM.asNonCompoundGraph(e)),
    X6(e),
    ss.forEach(W6(e), function (t, n) {
      e.node(n).x = t;
    });
}
function X6(e) {
  var t = vM.buildLayerMatrix(e),
    n = e.graph().ranksep,
    r = 0;
  ss.forEach(t, function (i) {
    var o = ss.max(
      ss.map(i, function (s) {
        return e.node(s).height;
      })
    );
    ss.forEach(i, function (s) {
      e.node(s).y = r + o / 2;
    }),
      (r += o + n);
  });
}
var ne = ye,
  AC = q5,
  NC = r8,
  Z6 = k8,
  Q6 = wt.normalizeRanks,
  J6 = N8,
  eU = wt.removeEmptyRanks,
  MC = O8,
  tU = $8,
  IC = B8,
  nU = P6,
  rU = K6,
  Rr = wt,
  iU = on.Graph,
  oU = sU;
function sU(e, t) {
  var n = t && t.debugTiming ? Rr.time : Rr.notime;
  n("layout", function () {
    var r = n("  buildLayoutGraph", function () {
      return vU(e);
    });
    n("  runLayout", function () {
      aU(r, n);
    }),
      n("  updateInputGraph", function () {
        uU(e, r);
      });
  });
}
function aU(e, t) {
  t("    makeSpaceForEdgeLabels", function () {
    yU(e);
  }),
    t("    removeSelfEdges", function () {
      kU(e);
    }),
    t("    acyclic", function () {
      AC.run(e);
    }),
    t("    nestingGraph.run", function () {
      MC.run(e);
    }),
    t("    rank", function () {
      Z6(Rr.asNonCompoundGraph(e));
    }),
    t("    injectEdgeLabelProxies", function () {
      wU(e);
    }),
    t("    removeEmptyRanks", function () {
      eU(e);
    }),
    t("    nestingGraph.cleanup", function () {
      MC.cleanup(e);
    }),
    t("    normalizeRanks", function () {
      Q6(e);
    }),
    t("    assignRankMinMax", function () {
      xU(e);
    }),
    t("    removeEdgeLabelProxies", function () {
      _U(e);
    }),
    t("    normalize.run", function () {
      NC.run(e);
    }),
    t("    parentDummyChains", function () {
      J6(e);
    }),
    t("    addBorderSegments", function () {
      tU(e);
    }),
    t("    order", function () {
      nU(e);
    }),
    t("    insertSelfEdges", function () {
      PU(e);
    }),
    t("    adjustCoordinateSystem", function () {
      IC.adjust(e);
    }),
    t("    position", function () {
      rU(e);
    }),
    t("    positionSelfEdges", function () {
      RU(e);
    }),
    t("    removeBorderNodes", function () {
      TU(e);
    }),
    t("    normalize.undo", function () {
      NC.undo(e);
    }),
    t("    fixupEdgeLabelCoords", function () {
      EU(e);
    }),
    t("    undoCoordinateSystem", function () {
      IC.undo(e);
    }),
    t("    translateGraph", function () {
      SU(e);
    }),
    t("    assignNodeIntersects", function () {
      bU(e);
    }),
    t("    reversePoints", function () {
      CU(e);
    }),
    t("    acyclic.undo", function () {
      AC.undo(e);
    });
}
function uU(e, t) {
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
var lU = ["nodesep", "edgesep", "ranksep", "marginx", "marginy"],
  cU = { ranksep: 50, edgesep: 20, nodesep: 50, rankdir: "tb" },
  fU = ["acyclicer", "ranker", "rankdir", "align"],
  dU = ["width", "height"],
  hU = { width: 0, height: 0 },
  pU = ["minlen", "weight", "width", "height", "labeloffset"],
  mU = { minlen: 1, weight: 1, width: 0, height: 0, labeloffset: 10, labelpos: "r" },
  gU = ["labelpos"];
function vU(e) {
  var t = new iU({ multigraph: !0, compound: !0 }),
    n = eg(e.graph());
  return (
    t.setGraph(ne.merge({}, cU, Jm(n, lU), ne.pick(n, fU))),
    ne.forEach(e.nodes(), function (r) {
      var i = eg(e.node(r));
      t.setNode(r, ne.defaults(Jm(i, dU), hU)), t.setParent(r, e.parent(r));
    }),
    ne.forEach(e.edges(), function (r) {
      var i = eg(e.edge(r));
      t.setEdge(r, ne.merge({}, mU, Jm(i, pU), ne.pick(i, gU)));
    }),
    t
  );
}
function yU(e) {
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
function wU(e) {
  ne.forEach(e.edges(), function (t) {
    var n = e.edge(t);
    if (n.width && n.height) {
      var r = e.node(t.v),
        i = e.node(t.w),
        o = { rank: (i.rank - r.rank) / 2 + r.rank, e: t };
      Rr.addDummyNode(e, "edge-proxy", o, "_ep");
    }
  });
}
function xU(e) {
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
function _U(e) {
  ne.forEach(e.nodes(), function (t) {
    var n = e.node(t);
    n.dummy === "edge-proxy" && ((e.edge(n.e).labelRank = n.rank), e.removeNode(t));
  });
}
function SU(e) {
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
function bU(e) {
  ne.forEach(e.edges(), function (t) {
    var n = e.edge(t),
      r = e.node(t.v),
      i = e.node(t.w),
      o,
      s;
    n.points
      ? ((o = n.points[0]), (s = n.points[n.points.length - 1]))
      : ((n.points = []), (o = i), (s = r)),
      n.points.unshift(Rr.intersectRect(r, o)),
      n.points.push(Rr.intersectRect(i, s));
  });
}
function EU(e) {
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
function CU(e) {
  ne.forEach(e.edges(), function (t) {
    var n = e.edge(t);
    n.reversed && n.points.reverse();
  });
}
function TU(e) {
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
function kU(e) {
  ne.forEach(e.edges(), function (t) {
    if (t.v === t.w) {
      var n = e.node(t.v);
      n.selfEdges || (n.selfEdges = []),
        n.selfEdges.push({ e: t, label: e.edge(t) }),
        e.removeEdge(t);
    }
  });
}
function PU(e) {
  var t = Rr.buildLayerMatrix(e);
  ne.forEach(t, function (n) {
    var r = 0;
    ne.forEach(n, function (i, o) {
      var s = e.node(i);
      (s.order = o + r),
        ne.forEach(s.selfEdges, function (a) {
          Rr.addDummyNode(
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
            "_se"
          );
        }),
        delete s.selfEdges;
    });
  });
}
function RU(e) {
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
function Jm(e, t) {
  return ne.mapValues(ne.pick(e, t), Number);
}
function eg(e) {
  var t = {};
  return (
    ne.forEach(e, function (n, r) {
      t[r.toLowerCase()] = n;
    }),
    t
  );
}
var Xa = ye,
  AU = wt,
  NU = on.Graph,
  MU = { debugOrdering: IU };
function IU(e) {
  var t = AU.buildLayerMatrix(e),
    n = new NU({ compound: !0, multigraph: !0 }).setGraph({});
  return (
    Xa.forEach(e.nodes(), function (r) {
      n.setNode(r, { label: r }), n.setParent(r, "layer" + e.node(r).rank);
    }),
    Xa.forEach(e.edges(), function (r) {
      n.setEdge(r.v, r.w, {}, r.name);
    }),
    Xa.forEach(t, function (r, i) {
      var o = "layer" + i;
      n.setNode(o, { rank: "same" }),
        Xa.reduce(r, function (s, a) {
          return n.setEdge(s, a, { style: "invis" }), a;
        });
    }),
    n
  );
}
var DU = "0.8.5",
  yM = {
    graphlib: on,
    layout: oU,
    debug: MU,
    util: { time: wt.time, notime: wt.notime },
    version: DU,
  };
const Ti = new yM.graphlib.Graph();
Ti.setDefaultEdgeLabel(() => ({}));
const tg = 200,
  ng = 50,
  OU = (e, t) => {
    Ti.setGraph({ rankdir: "TB", nodesep: 25, ranksep: 60 });
    const n = [],
      r = [];
    function i(s) {
      if (!(!s || !s.id)) {
        if (
          (n.push({
            id: s.id,
            data: { label: s.key },
            position: { x: 0, y: 0 },
            style: {
              background: t.includes(s.id) ? "#3b82f6" : "#ffffff",
              color: t.includes(s.id) ? "white" : "black",
              border: "1px solid #9ca3af",
              borderRadius: "8px",
              width: tg,
              height: ng,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            },
          }),
          Ti.setNode(s.id, { width: tg, height: ng }),
          s.on)
        )
          for (const a in s.on) {
            const u = s.on[a],
              l = Array.isArray(u) ? u : [u];
            for (const c of l) {
              const f = typeof c == "string" ? c : c.target,
                d = f.startsWith(".")
                  ? s.id.substring(0, s.id.lastIndexOf(".")) + f
                  : `${e.id}.${f}`;
              r.push({
                id: `e-${s.id}-${d}-${a}`,
                source: s.id,
                target: d,
                label: a,
                markerEnd: { type: Ys.ArrowClosed },
              }),
                Ti.setEdge(s.id, d);
            }
          }
        if (s.states)
          for (const a in s.states) {
            const u = s.states[a];
            (u.id = `${s.id}.${a}`), (u.key = a), i(u);
          }
      }
    }
    const o = { ...e, id: e.id, key: e.id };
    return (
      i(o),
      yM.layout(Ti),
      n.forEach((s) => {
        const a = Ti.node(s.id);
        a && (s.position = { x: a.x - tg / 2, y: a.y - ng / 2 });
      }),
      { nodes: n, edges: r }
    );
  },
  LU = ({ machine: e, activeStateIds: t }) => {
    const { nodes: n, edges: r } = _.useMemo(() => OU(e.definition, t), [e.definition, t]);
    return !n || n.length === 0
      ? M.jsx("div", { className: "p-4 text-gray-500", children: "Could not render diagram." })
      : M.jsx("div", {
          className:
            "h-[600px] w-full bg-gray-50 dark:bg-gray-900 rounded-lg border dark:border-gray-700",
          children: M.jsxs(QA, {
            nodes: n,
            edges: r,
            fitView: !0,
            proOptions: { hideAttribution: !0 },
            children: [
              M.jsx(Iz, {}),
              M.jsx(Tz, { nodeStrokeWidth: 3, zoomable: !0, pannable: !0 }),
              M.jsx(jz, { color: "#aaa", gap: 16 }),
            ],
          }),
        });
  };
/**
 * @license lucide-react v0.379.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */ const FU = (e) => e.replace(/([a-z0-9])([A-Z])/g, "$1-$2").toLowerCase(),
  wM = (...e) => e.filter((t, n, r) => !!t && r.indexOf(t) === n).join(" ");
/**
 * @license lucide-react v0.379.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */ var VU = {
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
 */ const jU = _.forwardRef(
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
    u
  ) =>
    _.createElement(
      "svg",
      {
        ref: u,
        ...VU,
        width: t,
        height: t,
        stroke: e,
        strokeWidth: r ? (Number(n) * 24) / Number(t) : n,
        className: wM("lucide", i),
        ...a,
      },
      [...s.map(([l, c]) => _.createElement(l, c)), ...(Array.isArray(o) ? o : [o])]
    )
);
/**
 * @license lucide-react v0.379.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */ const bn = (e, t) => {
  const n = _.forwardRef(({ className: r, ...i }, o) =>
    _.createElement(jU, { ref: o, iconNode: t, className: wM(`lucide-${FU(e)}`, r), ...i })
  );
  return (n.displayName = `${e}`), n;
};
/**
 * @license lucide-react v0.379.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */ const qU = bn("Bot", [
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
 */ const $U = bn("FileJson", [
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
 */ const zU = bn("History", [
  ["path", { d: "M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8", key: "1357e3" }],
  ["path", { d: "M3 3v5h5", key: "1xhq8a" }],
  ["path", { d: "M12 7v5l4 2", key: "1fdv2h" }],
]);
/**
 * @license lucide-react v0.379.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */ const BU = bn("Moon", [["path", { d: "M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z", key: "a7tn18" }]]);
/**
 * @license lucide-react v0.379.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */ const UU = bn("Pause", [
  ["rect", { x: "14", y: "4", width: "4", height: "16", rx: "1", key: "zuxfzm" }],
  ["rect", { x: "6", y: "4", width: "4", height: "16", rx: "1", key: "1okwgv" }],
]);
/**
 * @license lucide-react v0.379.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */ const HU = bn("Play", [["polygon", { points: "6 3 20 12 6 21 6 3", key: "1oa8hb" }]]);
/**
 * @license lucide-react v0.379.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */ const GU = bn("Send", [
  ["path", { d: "m22 2-7 20-4-9-9-4Z", key: "1q3vgg" }],
  ["path", { d: "M22 2 11 13", key: "nzbqef" }],
]);
/**
 * @license lucide-react v0.379.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */ const WU = bn("SquareActivity", [
  ["rect", { width: "18", height: "18", x: "3", y: "3", rx: "2", key: "afitv7" }],
  ["path", { d: "M17 12h-2l-2 5-2-10-2 5H7", key: "15hlnc" }],
]);
/**
 * @license lucide-react v0.379.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */ const KU = bn("Sun", [
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
 */ const YU = bn("X", [
  ["path", { d: "M18 6 6 18", key: "1bl5f8" }],
  ["path", { d: "m6 6 12 12", key: "d8bk6v" }],
]);
function DC(e, t) {
  if (typeof e == "function") return e(t);
  e != null && (e.current = t);
}
function xM(...e) {
  return (t) => {
    let n = !1;
    const r = e.map((i) => {
      const o = DC(i, t);
      return !n && typeof o == "function" && (n = !0), o;
    });
    if (n)
      return () => {
        for (let i = 0; i < r.length; i++) {
          const o = r[i];
          typeof o == "function" ? o() : DC(e[i], null);
        }
      };
  };
}
function xn(...e) {
  return _.useCallback(xM(...e), e);
}
function Zs(e) {
  const t = ZU(e),
    n = _.forwardRef((r, i) => {
      const { children: o, ...s } = r,
        a = _.Children.toArray(o),
        u = a.find(JU);
      if (u) {
        const l = u.props.children,
          c = a.map((f) =>
            f === u
              ? _.Children.count(l) > 1
                ? _.Children.only(null)
                : _.isValidElement(l)
                ? l.props.children
                : null
              : f
          );
        return M.jsx(t, {
          ...s,
          ref: i,
          children: _.isValidElement(l) ? _.cloneElement(l, void 0, c) : null,
        });
      }
      return M.jsx(t, { ...s, ref: i, children: o });
    });
  return (n.displayName = `${e}.Slot`), n;
}
var XU = Zs("Slot");
function ZU(e) {
  const t = _.forwardRef((n, r) => {
    const { children: i, ...o } = n;
    if (_.isValidElement(i)) {
      const s = tH(i),
        a = eH(o, i.props);
      return i.type !== _.Fragment && (a.ref = r ? xM(r, s) : s), _.cloneElement(i, a);
    }
    return _.Children.count(i) > 1 ? _.Children.only(null) : null;
  });
  return (t.displayName = `${e}.SlotClone`), t;
}
var QU = Symbol("radix.slottable");
function JU(e) {
  return (
    _.isValidElement(e) &&
    typeof e.type == "function" &&
    "__radixId" in e.type &&
    e.type.__radixId === QU
  );
}
function eH(e, t) {
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
function tH(e) {
  var r, i;
  let t = (r = Object.getOwnPropertyDescriptor(e.props, "ref")) == null ? void 0 : r.get,
    n = t && "isReactWarning" in t && t.isReactWarning;
  return n
    ? e.ref
    : ((t = (i = Object.getOwnPropertyDescriptor(e, "ref")) == null ? void 0 : i.get),
      (n = t && "isReactWarning" in t && t.isReactWarning),
      n ? e.props.ref : e.props.ref || e.ref);
}
function _M(e) {
  var t,
    n,
    r = "";
  if (typeof e == "string" || typeof e == "number") r += e;
  else if (typeof e == "object")
    if (Array.isArray(e)) {
      var i = e.length;
      for (t = 0; t < i; t++) e[t] && (n = _M(e[t])) && (r && (r += " "), (r += n));
    } else for (n in e) e[n] && (r && (r += " "), (r += n));
  return r;
}
function SM() {
  for (var e, t, n = 0, r = "", i = arguments.length; n < i; n++)
    (e = arguments[n]) && (t = _M(e)) && (r && (r += " "), (r += t));
  return r;
}
const OC = (e) => (typeof e == "boolean" ? `${e}` : e === 0 ? "0" : e),
  LC = SM,
  bM = (e, t) => (n) => {
    var r;
    if ((t == null ? void 0 : t.variants) == null)
      return LC(e, n == null ? void 0 : n.class, n == null ? void 0 : n.className);
    const { variants: i, defaultVariants: o } = t,
      s = Object.keys(i).map((l) => {
        const c = n == null ? void 0 : n[l],
          f = o == null ? void 0 : o[l];
        if (c === null) return null;
        const d = OC(c) || OC(f);
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
    return LC(e, s, u, n == null ? void 0 : n.class, n == null ? void 0 : n.className);
  },
  L0 = "-",
  nH = (e) => {
    const t = iH(e),
      { conflictingClassGroups: n, conflictingClassGroupModifiers: r } = e;
    return {
      getClassGroupId: (s) => {
        const a = s.split(L0);
        return a[0] === "" && a.length !== 1 && a.shift(), EM(a, t) || rH(s);
      },
      getConflictingClassGroupIds: (s, a) => {
        const u = n[s] || [];
        return a && r[s] ? [...u, ...r[s]] : u;
      },
    };
  },
  EM = (e, t) => {
    var s;
    if (e.length === 0) return t.classGroupId;
    const n = e[0],
      r = t.nextPart.get(n),
      i = r ? EM(e.slice(1), r) : void 0;
    if (i) return i;
    if (t.validators.length === 0) return;
    const o = e.join(L0);
    return (s = t.validators.find(({ validator: a }) => a(o))) == null ? void 0 : s.classGroupId;
  },
  FC = /^\[(.+)\]$/,
  rH = (e) => {
    if (FC.test(e)) {
      const t = FC.exec(e)[1],
        n = t == null ? void 0 : t.substring(0, t.indexOf(":"));
      if (n) return "arbitrary.." + n;
    }
  },
  iH = (e) => {
    const { theme: t, prefix: n } = e,
      r = { nextPart: new Map(), validators: [] };
    return (
      sH(Object.entries(e.classGroups), n).forEach(([o, s]) => {
        Fv(s, r, o, t);
      }),
      r
    );
  },
  Fv = (e, t, n, r) => {
    e.forEach((i) => {
      if (typeof i == "string") {
        const o = i === "" ? t : VC(t, i);
        o.classGroupId = n;
        return;
      }
      if (typeof i == "function") {
        if (oH(i)) {
          Fv(i(r), t, n, r);
          return;
        }
        t.validators.push({ validator: i, classGroupId: n });
        return;
      }
      Object.entries(i).forEach(([o, s]) => {
        Fv(s, VC(t, o), n, r);
      });
    });
  },
  VC = (e, t) => {
    let n = e;
    return (
      t.split(L0).forEach((r) => {
        n.nextPart.has(r) || n.nextPart.set(r, { nextPart: new Map(), validators: [] }),
          (n = n.nextPart.get(r));
      }),
      n
    );
  },
  oH = (e) => e.isThemeGetter,
  sH = (e, t) =>
    t
      ? e.map(([n, r]) => {
          const i = r.map((o) =>
            typeof o == "string"
              ? t + o
              : typeof o == "object"
              ? Object.fromEntries(Object.entries(o).map(([s, a]) => [t + s, a]))
              : o
          );
          return [n, i];
        })
      : e,
  aH = (e) => {
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
  CM = "!",
  uH = (e) => {
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
          h = d.startsWith(CM),
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
  lH = (e) => {
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
  cH = (e) => ({ cache: aH(e.cacheSize), parseClassName: uH(e), ...nH(e) }),
  fH = /\s+/,
  dH = (e, t) => {
    const { parseClassName: n, getClassGroupId: r, getConflictingClassGroupIds: i } = t,
      o = [],
      s = e.trim().split(fH);
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
      const y = lH(c).join(":"),
        m = f ? y + CM : y,
        g = m + p;
      if (o.includes(g)) continue;
      o.push(g);
      const w = i(p, v);
      for (let x = 0; x < w.length; ++x) {
        const S = w[x];
        o.push(m + S);
      }
      a = l + (a.length > 0 ? " " + a : a);
    }
    return a;
  };
function hH() {
  let e = 0,
    t,
    n,
    r = "";
  for (; e < arguments.length; ) (t = arguments[e++]) && (n = TM(t)) && (r && (r += " "), (r += n));
  return r;
}
const TM = (e) => {
  if (typeof e == "string") return e;
  let t,
    n = "";
  for (let r = 0; r < e.length; r++) e[r] && (t = TM(e[r])) && (n && (n += " "), (n += t));
  return n;
};
function pH(e, ...t) {
  let n,
    r,
    i,
    o = s;
  function s(u) {
    const l = t.reduce((c, f) => f(c), e());
    return (n = cH(l)), (r = n.cache.get), (i = n.cache.set), (o = a), a(u);
  }
  function a(u) {
    const l = r(u);
    if (l) return l;
    const c = dH(u, n);
    return i(u, c), c;
  }
  return function () {
    return o(hH.apply(null, arguments));
  };
}
const pe = (e) => {
    const t = (n) => n[e] || [];
    return (t.isThemeGetter = !0), t;
  },
  kM = /^\[(?:([a-z-]+):)?(.+)\]$/i,
  mH = /^\d+\/\d+$/,
  gH = new Set(["px", "full", "screen"]),
  vH = /^(\d+(\.\d+)?)?(xs|sm|md|lg|xl)$/,
  yH = /\d+(%|px|r?em|[sdl]?v([hwib]|min|max)|pt|pc|in|cm|mm|cap|ch|ex|r?lh|cq(w|h|i|b|min|max))|\b(calc|min|max|clamp)\(.+\)|^0$/,
  wH = /^(rgba?|hsla?|hwb|(ok)?(lab|lch))\(.+\)$/,
  xH = /^(inset_)?-?((\d+)?\.?(\d+)[a-z]+|0)_-?((\d+)?\.?(\d+)[a-z]+|0)/,
  _H = /^(url|image|image-set|cross-fade|element|(repeating-)?(linear|radial|conic)-gradient)\(.+\)$/,
  Rn = (e) => eo(e) || gH.has(e) || mH.test(e),
  rr = (e) => ko(e, "length", RH),
  eo = (e) => !!e && !Number.isNaN(Number(e)),
  rg = (e) => ko(e, "number", eo),
  Ho = (e) => !!e && Number.isInteger(Number(e)),
  SH = (e) => e.endsWith("%") && eo(e.slice(0, -1)),
  te = (e) => kM.test(e),
  ir = (e) => vH.test(e),
  bH = new Set(["length", "size", "percentage"]),
  EH = (e) => ko(e, bH, PM),
  CH = (e) => ko(e, "position", PM),
  TH = new Set(["image", "url"]),
  kH = (e) => ko(e, TH, NH),
  PH = (e) => ko(e, "", AH),
  Go = () => !0,
  ko = (e, t, n) => {
    const r = kM.exec(e);
    return r ? (r[1] ? (typeof t == "string" ? r[1] === t : t.has(r[1])) : n(r[2])) : !1;
  },
  RH = (e) => yH.test(e) && !wH.test(e),
  PM = () => !1,
  AH = (e) => xH.test(e),
  NH = (e) => _H.test(e),
  MH = () => {
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
      S = pe("sepia"),
      C = pe("skew"),
      E = pe("space"),
      T = pe("translate"),
      P = () => ["auto", "contain", "none"],
      N = () => ["auto", "hidden", "clip", "visible", "scroll"],
      I = () => ["auto", te, t],
      V = () => [te, t],
      q = () => ["", Rn, rr],
      b = () => ["auto", eo, te],
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
      R = () => ["solid", "dashed", "dotted", "double", "none"],
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
      A = () => ["start", "end", "center", "between", "around", "evenly", "stretch"],
      k = () => ["", "0", te],
      D = () => ["auto", "avoid", "all", "avoid-page", "page", "left", "right", "column"],
      j = () => [eo, te];
    return {
      cacheSize: 500,
      separator: ":",
      theme: {
        colors: [Go],
        spacing: [Rn, rr],
        blur: ["none", "", ir, te],
        brightness: j(),
        borderColor: [e],
        borderRadius: ["none", "", "full", ir, te],
        borderSpacing: V(),
        borderWidth: q(),
        contrast: j(),
        grayscale: k(),
        hueRotate: j(),
        invert: k(),
        gap: V(),
        gradientColorStops: [e],
        gradientColorStopPositions: [SH, rr],
        inset: I(),
        margin: I(),
        opacity: j(),
        padding: V(),
        saturate: j(),
        scale: j(),
        sepia: k(),
        skew: j(),
        space: V(),
        translate: V(),
      },
      classGroups: {
        aspect: [{ aspect: ["auto", "square", "video", te] }],
        container: ["container"],
        columns: [{ columns: [ir] }],
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
        overflow: [{ overflow: N() }],
        "overflow-x": [{ "overflow-x": N() }],
        "overflow-y": [{ "overflow-y": N() }],
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
        z: [{ z: ["auto", Ho, te] }],
        basis: [{ basis: I() }],
        "flex-direction": [{ flex: ["row", "row-reverse", "col", "col-reverse"] }],
        "flex-wrap": [{ flex: ["wrap", "wrap-reverse", "nowrap"] }],
        flex: [{ flex: ["1", "auto", "initial", "none", te] }],
        grow: [{ grow: k() }],
        shrink: [{ shrink: k() }],
        order: [{ order: ["first", "last", "none", Ho, te] }],
        "grid-cols": [{ "grid-cols": [Go] }],
        "col-start-end": [{ col: ["auto", { span: ["full", Ho, te] }, te] }],
        "col-start": [{ "col-start": b() }],
        "col-end": [{ "col-end": b() }],
        "grid-rows": [{ "grid-rows": [Go] }],
        "row-start-end": [{ row: ["auto", { span: [Ho, te] }, te] }],
        "row-start": [{ "row-start": b() }],
        "row-end": [{ "row-end": b() }],
        "grid-flow": [{ "grid-flow": ["row", "col", "dense", "row-dense", "col-dense"] }],
        "auto-cols": [{ "auto-cols": ["auto", "min", "max", "fr", te] }],
        "auto-rows": [{ "auto-rows": ["auto", "min", "max", "fr", te] }],
        gap: [{ gap: [d] }],
        "gap-x": [{ "gap-x": [d] }],
        "gap-y": [{ "gap-y": [d] }],
        "justify-content": [{ justify: ["normal", ...A()] }],
        "justify-items": [{ "justify-items": ["start", "end", "center", "stretch"] }],
        "justify-self": [{ "justify-self": ["auto", "start", "end", "center", "stretch"] }],
        "align-content": [{ content: ["normal", ...A(), "baseline"] }],
        "align-items": [{ items: ["start", "end", "center", "baseline", "stretch"] }],
        "align-self": [{ self: ["auto", "start", "end", "center", "stretch", "baseline"] }],
        "place-content": [{ "place-content": [...A(), "baseline"] }],
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
        "space-x": [{ "space-x": [E] }],
        "space-x-reverse": ["space-x-reverse"],
        "space-y": [{ "space-y": [E] }],
        "space-y-reverse": ["space-y-reverse"],
        w: [{ w: ["auto", "min", "max", "fit", "svw", "lvw", "dvw", te, t] }],
        "min-w": [{ "min-w": [te, t, "min", "max", "fit"] }],
        "max-w": [
          { "max-w": [te, t, "none", "full", "min", "max", "fit", "prose", { screen: [ir] }, ir] },
        ],
        h: [{ h: [te, t, "auto", "min", "max", "fit", "svh", "lvh", "dvh"] }],
        "min-h": [{ "min-h": [te, t, "min", "max", "fit", "svh", "lvh", "dvh"] }],
        "max-h": [{ "max-h": [te, t, "min", "max", "fit", "svh", "lvh", "dvh"] }],
        size: [{ size: [te, t, "auto", "min", "max", "fit"] }],
        "font-size": [{ text: ["base", ir, rr] }],
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
              rg,
            ],
          },
        ],
        "font-family": [{ font: [Go] }],
        "fvn-normal": ["normal-nums"],
        "fvn-ordinal": ["ordinal"],
        "fvn-slashed-zero": ["slashed-zero"],
        "fvn-figure": ["lining-nums", "oldstyle-nums"],
        "fvn-spacing": ["proportional-nums", "tabular-nums"],
        "fvn-fraction": ["diagonal-fractions", "stacked-fractions"],
        tracking: [{ tracking: ["tighter", "tight", "normal", "wide", "wider", "widest", te] }],
        "line-clamp": [{ "line-clamp": ["none", eo, rg] }],
        leading: [{ leading: ["none", "tight", "snug", "normal", "relaxed", "loose", Rn, te] }],
        "list-image": [{ "list-image": ["none", te] }],
        "list-style-type": [{ list: ["none", "disc", "decimal", te] }],
        "list-style-position": [{ list: ["inside", "outside"] }],
        "placeholder-color": [{ placeholder: [e] }],
        "placeholder-opacity": [{ "placeholder-opacity": [m] }],
        "text-alignment": [{ text: ["left", "center", "right", "justify", "start", "end"] }],
        "text-color": [{ text: [e] }],
        "text-opacity": [{ "text-opacity": [m] }],
        "text-decoration": ["underline", "overline", "line-through", "no-underline"],
        "text-decoration-style": [{ decoration: [...R(), "wavy"] }],
        "text-decoration-thickness": [{ decoration: ["auto", "from-font", Rn, rr] }],
        "underline-offset": [{ "underline-offset": ["auto", Rn, te] }],
        "text-decoration-color": [{ decoration: [e] }],
        "text-transform": ["uppercase", "lowercase", "capitalize", "normal-case"],
        "text-overflow": ["truncate", "text-ellipsis", "text-clip"],
        "text-wrap": [{ text: ["wrap", "nowrap", "balance", "pretty"] }],
        indent: [{ indent: V() }],
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
        "bg-position": [{ bg: [...O(), CH] }],
        "bg-repeat": [{ bg: ["no-repeat", { repeat: ["", "x", "y", "round", "space"] }] }],
        "bg-size": [{ bg: ["auto", "cover", "contain", EH] }],
        "bg-image": [
          { bg: ["none", { "gradient-to": ["t", "tr", "r", "br", "b", "bl", "l", "tl"] }, kH] },
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
        "border-style": [{ border: [...R(), "hidden"] }],
        "divide-x": [{ "divide-x": [a] }],
        "divide-x-reverse": ["divide-x-reverse"],
        "divide-y": [{ "divide-y": [a] }],
        "divide-y-reverse": ["divide-y-reverse"],
        "divide-opacity": [{ "divide-opacity": [m] }],
        "divide-style": [{ divide: R() }],
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
        "outline-style": [{ outline: ["", ...R()] }],
        "outline-offset": [{ "outline-offset": [Rn, te] }],
        "outline-w": [{ outline: [Rn, rr] }],
        "outline-color": [{ outline: [e] }],
        "ring-w": [{ ring: q() }],
        "ring-w-inset": ["ring-inset"],
        "ring-color": [{ ring: [e] }],
        "ring-opacity": [{ "ring-opacity": [m] }],
        "ring-offset-w": [{ "ring-offset": [Rn, rr] }],
        "ring-offset-color": [{ "ring-offset": [e] }],
        shadow: [{ shadow: ["", "inner", "none", ir, PH] }],
        "shadow-color": [{ shadow: [Go] }],
        opacity: [{ opacity: [m] }],
        "mix-blend": [{ "mix-blend": [...F(), "plus-lighter", "plus-darker"] }],
        "bg-blend": [{ "bg-blend": F() }],
        filter: [{ filter: ["", "none"] }],
        blur: [{ blur: [n] }],
        brightness: [{ brightness: [r] }],
        contrast: [{ contrast: [u] }],
        "drop-shadow": [{ "drop-shadow": ["", "none", ir, te] }],
        grayscale: [{ grayscale: [l] }],
        "hue-rotate": [{ "hue-rotate": [c] }],
        invert: [{ invert: [f] }],
        saturate: [{ saturate: [w] }],
        sepia: [{ sepia: [S] }],
        "backdrop-filter": [{ "backdrop-filter": ["", "none"] }],
        "backdrop-blur": [{ "backdrop-blur": [n] }],
        "backdrop-brightness": [{ "backdrop-brightness": [r] }],
        "backdrop-contrast": [{ "backdrop-contrast": [u] }],
        "backdrop-grayscale": [{ "backdrop-grayscale": [l] }],
        "backdrop-hue-rotate": [{ "backdrop-hue-rotate": [c] }],
        "backdrop-invert": [{ "backdrop-invert": [f] }],
        "backdrop-opacity": [{ "backdrop-opacity": [m] }],
        "backdrop-saturate": [{ "backdrop-saturate": [w] }],
        "backdrop-sepia": [{ "backdrop-sepia": [S] }],
        "border-collapse": [{ border: ["collapse", "separate"] }],
        "border-spacing": [{ "border-spacing": [s] }],
        "border-spacing-x": [{ "border-spacing-x": [s] }],
        "border-spacing-y": [{ "border-spacing-y": [s] }],
        "table-layout": [{ table: ["auto", "fixed"] }],
        caption: [{ caption: ["top", "bottom"] }],
        transition: [
          { transition: ["none", "all", "", "colors", "opacity", "shadow", "transform", te] },
        ],
        duration: [{ duration: j() }],
        ease: [{ ease: ["linear", "in", "out", "in-out", te] }],
        delay: [{ delay: j() }],
        animate: [{ animate: ["none", "spin", "ping", "pulse", "bounce", te] }],
        transform: [{ transform: ["", "gpu", "none"] }],
        scale: [{ scale: [x] }],
        "scale-x": [{ "scale-x": [x] }],
        "scale-y": [{ "scale-y": [x] }],
        rotate: [{ rotate: [Ho, te] }],
        "translate-x": [{ "translate-x": [T] }],
        "translate-y": [{ "translate-y": [T] }],
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
        "scroll-m": [{ "scroll-m": V() }],
        "scroll-mx": [{ "scroll-mx": V() }],
        "scroll-my": [{ "scroll-my": V() }],
        "scroll-ms": [{ "scroll-ms": V() }],
        "scroll-me": [{ "scroll-me": V() }],
        "scroll-mt": [{ "scroll-mt": V() }],
        "scroll-mr": [{ "scroll-mr": V() }],
        "scroll-mb": [{ "scroll-mb": V() }],
        "scroll-ml": [{ "scroll-ml": V() }],
        "scroll-p": [{ "scroll-p": V() }],
        "scroll-px": [{ "scroll-px": V() }],
        "scroll-py": [{ "scroll-py": V() }],
        "scroll-ps": [{ "scroll-ps": V() }],
        "scroll-pe": [{ "scroll-pe": V() }],
        "scroll-pt": [{ "scroll-pt": V() }],
        "scroll-pr": [{ "scroll-pr": V() }],
        "scroll-pb": [{ "scroll-pb": V() }],
        "scroll-pl": [{ "scroll-pl": V() }],
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
        "stroke-w": [{ stroke: [Rn, rr, rg] }],
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
  IH = pH(MH);
function ke(...e) {
  return IH(SM(e));
}
const DH = bM(
    "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0",
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
    }
  ),
  F0 = _.forwardRef(({ className: e, variant: t, size: n, asChild: r = !1, ...i }, o) => {
    const s = r ? XU : "button";
    return M.jsx(s, { className: ke(DH({ variant: t, size: n, className: e })), ref: o, ...i });
  });
F0.displayName = "Button";
const V0 = _.forwardRef(({ className: e, ...t }, n) =>
  M.jsx("div", {
    ref: n,
    className: ke("rounded-lg border bg-card text-card-foreground shadow-sm", e),
    ...t,
  })
);
V0.displayName = "Card";
const j0 = _.forwardRef(({ className: e, ...t }, n) =>
  M.jsx("div", { ref: n, className: ke("flex flex-col space-y-1.5 p-6", e), ...t })
);
j0.displayName = "CardHeader";
const q0 = _.forwardRef(({ className: e, ...t }, n) =>
  M.jsx("div", {
    ref: n,
    className: ke("text-2xl font-semibold leading-none tracking-tight", e),
    ...t,
  })
);
q0.displayName = "CardTitle";
const OH = _.forwardRef(({ className: e, ...t }, n) =>
  M.jsx("div", { ref: n, className: ke("text-sm text-muted-foreground", e), ...t })
);
OH.displayName = "CardDescription";
const $0 = _.forwardRef(({ className: e, ...t }, n) =>
  M.jsx("div", { ref: n, className: ke("p-6 pt-0", e), ...t })
);
$0.displayName = "CardContent";
const LH = _.forwardRef(({ className: e, ...t }, n) =>
  M.jsx("div", { ref: n, className: ke("flex items-center p-6 pt-0", e), ...t })
);
LH.displayName = "CardFooter";
function Ye(e, t, { checkForDefaultPrevented: n = !0 } = {}) {
  return function (i) {
    if ((e == null || e(i), n === !1 || !i.defaultPrevented)) return t == null ? void 0 : t(i);
  };
}
function FH(e, t) {
  const n = _.createContext(t),
    r = (o) => {
      const { children: s, ...a } = o,
        u = _.useMemo(() => a, Object.values(a));
      return M.jsx(n.Provider, { value: u, children: s });
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
function cc(e, t = []) {
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
      return M.jsx(p.Provider, { value: y, children: h });
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
  return (i.scopeName = e), [r, VH(i, ...t)];
}
function VH(...e) {
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
function jH(e) {
  const t = e + "CollectionProvider",
    [n, r] = cc(t),
    [i, o] = n(t, { collectionRef: { current: null }, itemMap: new Map() }),
    s = (p) => {
      const { scope: y, children: m } = p,
        g = L.useRef(null),
        w = L.useRef(new Map()).current;
      return M.jsx(i, { scope: y, itemMap: w, collectionRef: g, children: m });
    };
  s.displayName = t;
  const a = e + "CollectionSlot",
    u = Zs(a),
    l = L.forwardRef((p, y) => {
      const { scope: m, children: g } = p,
        w = o(a, m),
        x = xn(y, w.collectionRef);
      return M.jsx(u, { ref: x, children: g });
    });
  l.displayName = a;
  const c = e + "CollectionItemSlot",
    f = "data-radix-collection-item",
    d = Zs(c),
    h = L.forwardRef((p, y) => {
      const { scope: m, children: g, ...w } = p,
        x = L.useRef(null),
        S = xn(y, x),
        C = o(c, m);
      return (
        L.useEffect(() => (C.itemMap.set(x, { ref: x, ...w }), () => void C.itemMap.delete(x))),
        M.jsx(d, { [f]: "", ref: S, children: g })
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
        (C, E) => w.indexOf(C.ref.current) - w.indexOf(E.ref.current)
      );
    }, [y.collectionRef, y.itemMap]);
  }
  return [{ Provider: s, Slot: l, ItemSlot: h }, v, r];
}
var Qs = globalThis != null && globalThis.document ? _.useLayoutEffect : () => {},
  qH = Ek[" useId ".trim().toString()] || (() => {}),
  $H = 0;
function ws(e) {
  const [t, n] = _.useState(qH());
  return (
    Qs(() => {
      n((r) => r ?? String($H++));
    }, [e]),
    t ? `radix-${t}` : ""
  );
}
var zH = [
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
  ct = zH.reduce((e, t) => {
    const n = Zs(`Primitive.${t}`),
      r = _.forwardRef((i, o) => {
        const { asChild: s, ...a } = i,
          u = s ? n : t;
        return (
          typeof window < "u" && (window[Symbol.for("radix-ui")] = !0), M.jsx(u, { ...a, ref: o })
        );
      });
    return (r.displayName = `Primitive.${t}`), { ...e, [t]: r };
  }, {});
function BH(e, t) {
  e && Qy.flushSync(() => e.dispatchEvent(t));
}
function po(e) {
  const t = _.useRef(e);
  return (
    _.useEffect(() => {
      t.current = e;
    }),
    _.useMemo(
      () => (...n) => {
        var r;
        return (r = t.current) == null ? void 0 : r.call(t, ...n);
      },
      []
    )
  );
}
var UH = Ek[" useInsertionEffect ".trim().toString()] || Qs;
function z0({ prop: e, defaultProp: t, onChange: n = () => {}, caller: r }) {
  const [i, o, s] = HH({ defaultProp: t, onChange: n }),
    a = e !== void 0,
    u = a ? e : i;
  {
    const c = _.useRef(e !== void 0);
    _.useEffect(() => {
      const f = c.current;
      f !== a &&
        console.warn(
          `${r} is changing from ${f ? "controlled" : "uncontrolled"} to ${
            a ? "controlled" : "uncontrolled"
          }. Components should not switch from controlled to uncontrolled (or vice versa). Decide between using a controlled or uncontrolled value for the lifetime of the component.`
        ),
        (c.current = a);
    }, [a, r]);
  }
  const l = _.useCallback(
    (c) => {
      var f;
      if (a) {
        const d = GH(c) ? c(e) : c;
        d !== e && ((f = s.current) == null || f.call(s, d));
      } else o(c);
    },
    [a, e, o, s]
  );
  return [u, l];
}
function HH({ defaultProp: e, onChange: t }) {
  const [n, r] = _.useState(e),
    i = _.useRef(n),
    o = _.useRef(t);
  return (
    UH(() => {
      o.current = t;
    }, [t]),
    _.useEffect(() => {
      var s;
      i.current !== n && ((s = o.current) == null || s.call(o, n), (i.current = n));
    }, [n, i]),
    [n, r, o]
  );
}
function GH(e) {
  return typeof e == "function";
}
var WH = _.createContext(void 0);
function RM(e) {
  const t = _.useContext(WH);
  return e || t || "ltr";
}
var ig = "rovingFocusGroup.onEntryFocus",
  KH = { bubbles: !1, cancelable: !0 },
  ga = "RovingFocusGroup",
  [Vv, AM, YH] = jH(ga),
  [XH, NM] = cc(ga, [YH]),
  [ZH, QH] = XH(ga),
  MM = _.forwardRef((e, t) =>
    M.jsx(Vv.Provider, {
      scope: e.__scopeRovingFocusGroup,
      children: M.jsx(Vv.Slot, {
        scope: e.__scopeRovingFocusGroup,
        children: M.jsx(JH, { ...e, ref: t }),
      }),
    })
  );
MM.displayName = ga;
var JH = _.forwardRef((e, t) => {
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
      h = xn(t, d),
      v = RM(o),
      [p, y] = z0({ prop: s, defaultProp: a ?? null, onChange: u, caller: ga }),
      [m, g] = _.useState(!1),
      w = po(l),
      x = AM(n),
      S = _.useRef(!1),
      [C, E] = _.useState(0);
    return (
      _.useEffect(() => {
        const T = d.current;
        if (T) return T.addEventListener(ig, w), () => T.removeEventListener(ig, w);
      }, [w]),
      M.jsx(ZH, {
        scope: n,
        orientation: r,
        dir: v,
        loop: i,
        currentTabStopId: p,
        onItemFocus: _.useCallback((T) => y(T), [y]),
        onItemShiftTab: _.useCallback(() => g(!0), []),
        onFocusableItemAdd: _.useCallback(() => E((T) => T + 1), []),
        onFocusableItemRemove: _.useCallback(() => E((T) => T - 1), []),
        children: M.jsx(ct.div, {
          tabIndex: m || C === 0 ? -1 : 0,
          "data-orientation": r,
          ...f,
          ref: h,
          style: { outline: "none", ...e.style },
          onMouseDown: Ye(e.onMouseDown, () => {
            S.current = !0;
          }),
          onFocus: Ye(e.onFocus, (T) => {
            const P = !S.current;
            if (T.target === T.currentTarget && P && !m) {
              const N = new CustomEvent(ig, KH);
              if ((T.currentTarget.dispatchEvent(N), !N.defaultPrevented)) {
                const I = x().filter((R) => R.focusable),
                  V = I.find((R) => R.active),
                  q = I.find((R) => R.id === p),
                  O = [V, q, ...I].filter(Boolean).map((R) => R.ref.current);
                OM(O, c);
              }
            }
            S.current = !1;
          }),
          onBlur: Ye(e.onBlur, () => g(!1)),
        }),
      })
    );
  }),
  IM = "RovingFocusGroupItem",
  DM = _.forwardRef((e, t) => {
    const {
        __scopeRovingFocusGroup: n,
        focusable: r = !0,
        active: i = !1,
        tabStopId: o,
        children: s,
        ...a
      } = e,
      u = ws(),
      l = o || u,
      c = QH(IM, n),
      f = c.currentTabStopId === l,
      d = AM(n),
      { onFocusableItemAdd: h, onFocusableItemRemove: v, currentTabStopId: p } = c;
    return (
      _.useEffect(() => {
        if (r) return h(), () => v();
      }, [r, h, v]),
      M.jsx(Vv.ItemSlot, {
        scope: n,
        id: l,
        focusable: r,
        active: i,
        children: M.jsx(ct.span, {
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
            const m = nG(y, c.orientation, c.dir);
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
                w = c.loop ? rG(w, x + 1) : w.slice(x + 1);
              }
              setTimeout(() => OM(w));
            }
          }),
          children: typeof s == "function" ? s({ isCurrentTabStop: f, hasTabStop: p != null }) : s,
        }),
      })
    );
  });
DM.displayName = IM;
var eG = {
  ArrowLeft: "prev",
  ArrowUp: "prev",
  ArrowRight: "next",
  ArrowDown: "next",
  PageUp: "first",
  Home: "first",
  PageDown: "last",
  End: "last",
};
function tG(e, t) {
  return t !== "rtl" ? e : e === "ArrowLeft" ? "ArrowRight" : e === "ArrowRight" ? "ArrowLeft" : e;
}
function nG(e, t, n) {
  const r = tG(e.key, n);
  if (
    !(t === "vertical" && ["ArrowLeft", "ArrowRight"].includes(r)) &&
    !(t === "horizontal" && ["ArrowUp", "ArrowDown"].includes(r))
  )
    return eG[r];
}
function OM(e, t = !1) {
  const n = document.activeElement;
  for (const r of e)
    if (r === n || (r.focus({ preventScroll: t }), document.activeElement !== n)) return;
}
function rG(e, t) {
  return e.map((n, r) => e[(t + r) % e.length]);
}
var iG = MM,
  oG = DM;
function sG(e, t) {
  return _.useReducer((n, r) => t[n][r] ?? n, e);
}
var va = (e) => {
  const { present: t, children: n } = e,
    r = aG(t),
    i = typeof n == "function" ? n({ present: r.isPresent }) : _.Children.only(n),
    o = xn(r.ref, uG(i));
  return typeof n == "function" || r.isPresent ? _.cloneElement(i, { ref: o }) : null;
};
va.displayName = "Presence";
function aG(e) {
  const [t, n] = _.useState(),
    r = _.useRef(null),
    i = _.useRef(e),
    o = _.useRef("none"),
    s = e ? "mounted" : "unmounted",
    [a, u] = sG(s, {
      mounted: { UNMOUNT: "unmounted", ANIMATION_OUT: "unmountSuspended" },
      unmountSuspended: { MOUNT: "mounted", ANIMATION_END: "unmounted" },
      unmounted: { MOUNT: "mounted" },
    });
  return (
    _.useEffect(() => {
      const l = Za(r.current);
      o.current = a === "mounted" ? l : "none";
    }, [a]),
    Qs(() => {
      const l = r.current,
        c = i.current;
      if (c !== e) {
        const d = o.current,
          h = Za(l);
        e
          ? u("MOUNT")
          : h === "none" || (l == null ? void 0 : l.display) === "none"
          ? u("UNMOUNT")
          : u(c && d !== h ? "ANIMATION_OUT" : "UNMOUNT"),
          (i.current = e);
      }
    }, [e, u]),
    Qs(() => {
      if (t) {
        let l;
        const c = t.ownerDocument.defaultView ?? window,
          f = (h) => {
            const p = Za(r.current).includes(CSS.escape(h.animationName));
            if (h.target === t && p && (u("ANIMATION_END"), !i.current)) {
              const y = t.style.animationFillMode;
              (t.style.animationFillMode = "forwards"),
                (l = c.setTimeout(() => {
                  t.style.animationFillMode === "forwards" && (t.style.animationFillMode = y);
                }));
            }
          },
          d = (h) => {
            h.target === t && (o.current = Za(r.current));
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
function Za(e) {
  return (e == null ? void 0 : e.animationName) || "none";
}
function uG(e) {
  var r, i;
  let t = (r = Object.getOwnPropertyDescriptor(e.props, "ref")) == null ? void 0 : r.get,
    n = t && "isReactWarning" in t && t.isReactWarning;
  return n
    ? e.ref
    : ((t = (i = Object.getOwnPropertyDescriptor(e, "ref")) == null ? void 0 : i.get),
      (n = t && "isReactWarning" in t && t.isReactWarning),
      n ? e.props.ref : e.props.ref || e.ref);
}
var fc = "Tabs",
  [lG, mX] = cc(fc, [NM]),
  LM = NM(),
  [cG, B0] = lG(fc),
  FM = _.forwardRef((e, t) => {
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
      c = RM(a),
      [f, d] = z0({ prop: r, onChange: i, defaultProp: o ?? "", caller: fc });
    return M.jsx(cG, {
      scope: n,
      baseId: ws(),
      value: f,
      onValueChange: d,
      orientation: s,
      dir: c,
      activationMode: u,
      children: M.jsx(ct.div, { dir: c, "data-orientation": s, ...l, ref: t }),
    });
  });
FM.displayName = fc;
var VM = "TabsList",
  jM = _.forwardRef((e, t) => {
    const { __scopeTabs: n, loop: r = !0, ...i } = e,
      o = B0(VM, n),
      s = LM(n);
    return M.jsx(iG, {
      asChild: !0,
      ...s,
      orientation: o.orientation,
      dir: o.dir,
      loop: r,
      children: M.jsx(ct.div, { role: "tablist", "aria-orientation": o.orientation, ...i, ref: t }),
    });
  });
jM.displayName = VM;
var qM = "TabsTrigger",
  $M = _.forwardRef((e, t) => {
    const { __scopeTabs: n, value: r, disabled: i = !1, ...o } = e,
      s = B0(qM, n),
      a = LM(n),
      u = UM(s.baseId, r),
      l = HM(s.baseId, r),
      c = r === s.value;
    return M.jsx(oG, {
      asChild: !0,
      ...a,
      focusable: !i,
      active: c,
      children: M.jsx(ct.button, {
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
$M.displayName = qM;
var zM = "TabsContent",
  BM = _.forwardRef((e, t) => {
    const { __scopeTabs: n, value: r, forceMount: i, children: o, ...s } = e,
      a = B0(zM, n),
      u = UM(a.baseId, r),
      l = HM(a.baseId, r),
      c = r === a.value,
      f = _.useRef(c);
    return (
      _.useEffect(() => {
        const d = requestAnimationFrame(() => (f.current = !1));
        return () => cancelAnimationFrame(d);
      }, []),
      M.jsx(va, {
        present: i || c,
        children: ({ present: d }) =>
          M.jsx(ct.div, {
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
BM.displayName = zM;
function UM(e, t) {
  return `${e}-trigger-${t}`;
}
function HM(e, t) {
  return `${e}-content-${t}`;
}
var fG = FM,
  GM = jM,
  WM = $M,
  KM = BM;
const dG = fG,
  YM = _.forwardRef(({ className: e, ...t }, n) =>
    M.jsx(GM, {
      ref: n,
      className: ke(
        "inline-flex h-10 items-center justify-center rounded-md bg-muted p-1 text-muted-foreground",
        e
      ),
      ...t,
    })
  );
YM.displayName = GM.displayName;
const _u = _.forwardRef(({ className: e, ...t }, n) =>
  M.jsx(WM, {
    ref: n,
    className: ke(
      "inline-flex items-center justify-center whitespace-nowrap rounded-sm px-3 py-1.5 text-sm font-medium ring-offset-background transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 data-[state=active]:bg-background data-[state=active]:text-foreground data-[state=active]:shadow-sm",
      e
    ),
    ...t,
  })
);
_u.displayName = WM.displayName;
const Su = _.forwardRef(({ className: e, ...t }, n) =>
  M.jsx(KM, {
    ref: n,
    className: ke(
      "mt-2 ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
      e
    ),
    ...t,
  })
);
Su.displayName = KM.displayName;
function hG(e, t = globalThis == null ? void 0 : globalThis.document) {
  const n = po(e);
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
var pG = "DismissableLayer",
  jv = "dismissableLayer.update",
  mG = "dismissableLayer.pointerDownOutside",
  gG = "dismissableLayer.focusOutside",
  jC,
  XM = _.createContext({
    layers: new Set(),
    layersWithOutsidePointerEventsDisabled: new Set(),
    branches: new Set(),
  }),
  ZM = _.forwardRef((e, t) => {
    const {
        disableOutsidePointerEvents: n = !1,
        onEscapeKeyDown: r,
        onPointerDownOutside: i,
        onFocusOutside: o,
        onInteractOutside: s,
        onDismiss: a,
        ...u
      } = e,
      l = _.useContext(XM),
      [c, f] = _.useState(null),
      d =
        (c == null ? void 0 : c.ownerDocument) ??
        (globalThis == null ? void 0 : globalThis.document),
      [, h] = _.useState({}),
      v = xn(t, (E) => f(E)),
      p = Array.from(l.layers),
      [y] = [...l.layersWithOutsidePointerEventsDisabled].slice(-1),
      m = p.indexOf(y),
      g = c ? p.indexOf(c) : -1,
      w = l.layersWithOutsidePointerEventsDisabled.size > 0,
      x = g >= m,
      S = wG((E) => {
        const T = E.target,
          P = [...l.branches].some((N) => N.contains(T));
        !x || P || (i == null || i(E), s == null || s(E), E.defaultPrevented || a == null || a());
      }, d),
      C = xG((E) => {
        const T = E.target;
        [...l.branches].some((N) => N.contains(T)) ||
          (o == null || o(E), s == null || s(E), E.defaultPrevented || a == null || a());
      }, d);
    return (
      hG((E) => {
        g === l.layers.size - 1 &&
          (r == null || r(E), !E.defaultPrevented && a && (E.preventDefault(), a()));
      }, d),
      _.useEffect(() => {
        if (c)
          return (
            n &&
              (l.layersWithOutsidePointerEventsDisabled.size === 0 &&
                ((jC = d.body.style.pointerEvents), (d.body.style.pointerEvents = "none")),
              l.layersWithOutsidePointerEventsDisabled.add(c)),
            l.layers.add(c),
            qC(),
            () => {
              n &&
                l.layersWithOutsidePointerEventsDisabled.size === 1 &&
                (d.body.style.pointerEvents = jC);
            }
          );
      }, [c, d, n, l]),
      _.useEffect(
        () => () => {
          c && (l.layers.delete(c), l.layersWithOutsidePointerEventsDisabled.delete(c), qC());
        },
        [c, l]
      ),
      _.useEffect(() => {
        const E = () => h({});
        return document.addEventListener(jv, E), () => document.removeEventListener(jv, E);
      }, []),
      M.jsx(ct.div, {
        ...u,
        ref: v,
        style: { pointerEvents: w ? (x ? "auto" : "none") : void 0, ...e.style },
        onFocusCapture: Ye(e.onFocusCapture, C.onFocusCapture),
        onBlurCapture: Ye(e.onBlurCapture, C.onBlurCapture),
        onPointerDownCapture: Ye(e.onPointerDownCapture, S.onPointerDownCapture),
      })
    );
  });
ZM.displayName = pG;
var vG = "DismissableLayerBranch",
  yG = _.forwardRef((e, t) => {
    const n = _.useContext(XM),
      r = _.useRef(null),
      i = xn(t, r);
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
      M.jsx(ct.div, { ...e, ref: i })
    );
  });
yG.displayName = vG;
function wG(e, t = globalThis == null ? void 0 : globalThis.document) {
  const n = po(e),
    r = _.useRef(!1),
    i = _.useRef(() => {});
  return (
    _.useEffect(() => {
      const o = (a) => {
          if (a.target && !r.current) {
            let u = function () {
              QM(mG, n, l, { discrete: !0 });
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
function xG(e, t = globalThis == null ? void 0 : globalThis.document) {
  const n = po(e),
    r = _.useRef(!1);
  return (
    _.useEffect(() => {
      const i = (o) => {
        o.target && !r.current && QM(gG, n, { originalEvent: o }, { discrete: !1 });
      };
      return t.addEventListener("focusin", i), () => t.removeEventListener("focusin", i);
    }, [t, n]),
    { onFocusCapture: () => (r.current = !0), onBlurCapture: () => (r.current = !1) }
  );
}
function qC() {
  const e = new CustomEvent(jv);
  document.dispatchEvent(e);
}
function QM(e, t, n, { discrete: r }) {
  const i = n.originalEvent.target,
    o = new CustomEvent(e, { bubbles: !1, cancelable: !0, detail: n });
  t && i.addEventListener(e, t, { once: !0 }), r ? BH(i, o) : i.dispatchEvent(o);
}
var og = "focusScope.autoFocusOnMount",
  sg = "focusScope.autoFocusOnUnmount",
  $C = { bubbles: !1, cancelable: !0 },
  _G = "FocusScope",
  JM = _.forwardRef((e, t) => {
    const { loop: n = !1, trapped: r = !1, onMountAutoFocus: i, onUnmountAutoFocus: o, ...s } = e,
      [a, u] = _.useState(null),
      l = po(i),
      c = po(o),
      f = _.useRef(null),
      d = xn(t, (p) => u(p)),
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
            a.contains(x) ? (f.current = x) : or(f.current, { select: !0 });
          },
          y = function (w) {
            if (h.paused || !a) return;
            const x = w.relatedTarget;
            x !== null && (a.contains(x) || or(f.current, { select: !0 }));
          },
          m = function (w) {
            if (document.activeElement === document.body)
              for (const S of w) S.removedNodes.length > 0 && or(a);
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
          BC.add(h);
          const p = document.activeElement;
          if (!a.contains(p)) {
            const m = new CustomEvent(og, $C);
            a.addEventListener(og, l),
              a.dispatchEvent(m),
              m.defaultPrevented ||
                (SG(kG(e2(a)), { select: !0 }), document.activeElement === p && or(a));
          }
          return () => {
            a.removeEventListener(og, l),
              setTimeout(() => {
                const m = new CustomEvent(sg, $C);
                a.addEventListener(sg, c),
                  a.dispatchEvent(m),
                  m.defaultPrevented || or(p ?? document.body, { select: !0 }),
                  a.removeEventListener(sg, c),
                  BC.remove(h);
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
            [w, x] = bG(g);
          w && x
            ? !p.shiftKey && m === x
              ? (p.preventDefault(), n && or(w, { select: !0 }))
              : p.shiftKey && m === w && (p.preventDefault(), n && or(x, { select: !0 }))
            : m === g && p.preventDefault();
        }
      },
      [n, r, h.paused]
    );
    return M.jsx(ct.div, { tabIndex: -1, ...s, ref: d, onKeyDown: v });
  });
JM.displayName = _G;
function SG(e, { select: t = !1 } = {}) {
  const n = document.activeElement;
  for (const r of e) if ((or(r, { select: t }), document.activeElement !== n)) return;
}
function bG(e) {
  const t = e2(e),
    n = zC(t, e),
    r = zC(t.reverse(), e);
  return [n, r];
}
function e2(e) {
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
function zC(e, t) {
  for (const n of e) if (!EG(n, { upTo: t })) return n;
}
function EG(e, { upTo: t }) {
  if (getComputedStyle(e).visibility === "hidden") return !0;
  for (; e; ) {
    if (t !== void 0 && e === t) return !1;
    if (getComputedStyle(e).display === "none") return !0;
    e = e.parentElement;
  }
  return !1;
}
function CG(e) {
  return e instanceof HTMLInputElement && "select" in e;
}
function or(e, { select: t = !1 } = {}) {
  if (e && e.focus) {
    const n = document.activeElement;
    e.focus({ preventScroll: !0 }), e !== n && CG(e) && t && e.select();
  }
}
var BC = TG();
function TG() {
  let e = [];
  return {
    add(t) {
      const n = e[0];
      t !== n && (n == null || n.pause()), (e = UC(e, t)), e.unshift(t);
    },
    remove(t) {
      var n;
      (e = UC(e, t)), (n = e[0]) == null || n.resume();
    },
  };
}
function UC(e, t) {
  const n = [...e],
    r = n.indexOf(t);
  return r !== -1 && n.splice(r, 1), n;
}
function kG(e) {
  return e.filter((t) => t.tagName !== "A");
}
var PG = "Portal",
  t2 = _.forwardRef((e, t) => {
    var a;
    const { container: n, ...r } = e,
      [i, o] = _.useState(!1);
    Qs(() => o(!0), []);
    const s =
      n ||
      (i && ((a = globalThis == null ? void 0 : globalThis.document) == null ? void 0 : a.body));
    return s ? _F.createPortal(M.jsx(ct.div, { ...r, ref: t }), s) : null;
  });
t2.displayName = PG;
var ag = 0;
function RG() {
  _.useEffect(() => {
    const e = document.querySelectorAll("[data-radix-focus-guard]");
    return (
      document.body.insertAdjacentElement("afterbegin", e[0] ?? HC()),
      document.body.insertAdjacentElement("beforeend", e[1] ?? HC()),
      ag++,
      () => {
        ag === 1 &&
          document.querySelectorAll("[data-radix-focus-guard]").forEach((t) => t.remove()),
          ag--;
      }
    );
  }, []);
}
function HC() {
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
var hn = function () {
  return (
    (hn =
      Object.assign ||
      function (t) {
        for (var n, r = 1, i = arguments.length; r < i; r++) {
          n = arguments[r];
          for (var o in n) Object.prototype.hasOwnProperty.call(n, o) && (t[o] = n[o]);
        }
        return t;
      }),
    hn.apply(this, arguments)
  );
};
function n2(e, t) {
  var n = {};
  for (var r in e) Object.prototype.hasOwnProperty.call(e, r) && t.indexOf(r) < 0 && (n[r] = e[r]);
  if (e != null && typeof Object.getOwnPropertySymbols == "function")
    for (var i = 0, r = Object.getOwnPropertySymbols(e); i < r.length; i++)
      t.indexOf(r[i]) < 0 &&
        Object.prototype.propertyIsEnumerable.call(e, r[i]) &&
        (n[r[i]] = e[r[i]]);
  return n;
}
function AG(e, t, n) {
  if (n || arguments.length === 2)
    for (var r = 0, i = t.length, o; r < i; r++)
      (o || !(r in t)) && (o || (o = Array.prototype.slice.call(t, 0, r)), (o[r] = t[r]));
  return e.concat(o || Array.prototype.slice.call(t));
}
var bu = "right-scroll-bar-position",
  Eu = "width-before-scroll-bar",
  NG = "with-scroll-bars-hidden",
  MG = "--removed-body-scroll-bar-size";
function ug(e, t) {
  return typeof e == "function" ? e(t) : e && (e.current = t), e;
}
function IG(e, t) {
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
var DG = typeof window < "u" ? _.useLayoutEffect : _.useEffect,
  GC = new WeakMap();
function OG(e, t) {
  var n = IG(null, function (r) {
    return e.forEach(function (i) {
      return ug(i, r);
    });
  });
  return (
    DG(
      function () {
        var r = GC.get(n);
        if (r) {
          var i = new Set(r),
            o = new Set(e),
            s = n.current;
          i.forEach(function (a) {
            o.has(a) || ug(a, null);
          }),
            o.forEach(function (a) {
              i.has(a) || ug(a, s);
            });
        }
        GC.set(n, e);
      },
      [e]
    ),
    n
  );
}
function LG(e) {
  return e;
}
function FG(e, t) {
  t === void 0 && (t = LG);
  var n = [],
    r = !1,
    i = {
      read: function () {
        if (r)
          throw new Error(
            "Sidecar: could not `read` from an `assigned` medium. `read` could be used only with `useMedium`."
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
function VG(e) {
  e === void 0 && (e = {});
  var t = FG(null);
  return (t.options = hn({ async: !0, ssr: !1 }, e)), t;
}
var r2 = function (e) {
  var t = e.sideCar,
    n = n2(e, ["sideCar"]);
  if (!t) throw new Error("Sidecar: please provide `sideCar` property to import the right car");
  var r = t.read();
  if (!r) throw new Error("Sidecar medium not found");
  return _.createElement(r, hn({}, n));
};
r2.isSideCarExport = !0;
function jG(e, t) {
  return e.useMedium(t), r2;
}
var i2 = VG(),
  lg = function () {},
  dc = _.forwardRef(function (e, t) {
    var n = _.useRef(null),
      r = _.useState({ onScrollCapture: lg, onWheelCapture: lg, onTouchMoveCapture: lg }),
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
      x = n2(e, [
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
      S = d,
      C = OG([n, t]),
      E = hn(hn({}, x), i);
    return _.createElement(
      _.Fragment,
      null,
      c &&
        _.createElement(S, {
          sideCar: i2,
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
        ? _.cloneElement(_.Children.only(a), hn(hn({}, E), { ref: C }))
        : _.createElement(g, hn({}, E, { className: u, ref: C }), a)
    );
  });
dc.defaultProps = { enabled: !0, removeScrollBar: !0, inert: !1 };
dc.classNames = { fullWidth: Eu, zeroRight: bu };
var qG = function () {
  if (typeof __webpack_nonce__ < "u") return __webpack_nonce__;
};
function $G() {
  if (!document) return null;
  var e = document.createElement("style");
  e.type = "text/css";
  var t = qG();
  return t && e.setAttribute("nonce", t), e;
}
function zG(e, t) {
  e.styleSheet ? (e.styleSheet.cssText = t) : e.appendChild(document.createTextNode(t));
}
function BG(e) {
  var t = document.head || document.getElementsByTagName("head")[0];
  t.appendChild(e);
}
var UG = function () {
    var e = 0,
      t = null;
    return {
      add: function (n) {
        e == 0 && (t = $G()) && (zG(t, n), BG(t)), e++;
      },
      remove: function () {
        e--, !e && t && (t.parentNode && t.parentNode.removeChild(t), (t = null));
      },
    };
  },
  HG = function () {
    var e = UG();
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
        [t && n]
      );
    };
  },
  o2 = function () {
    var e = HG(),
      t = function (n) {
        var r = n.styles,
          i = n.dynamic;
        return e(r, i), null;
      };
    return t;
  },
  GG = { left: 0, top: 0, right: 0, gap: 0 },
  cg = function (e) {
    return parseInt(e || "", 10) || 0;
  },
  WG = function (e) {
    var t = window.getComputedStyle(document.body),
      n = t[e === "padding" ? "paddingLeft" : "marginLeft"],
      r = t[e === "padding" ? "paddingTop" : "marginTop"],
      i = t[e === "padding" ? "paddingRight" : "marginRight"];
    return [cg(n), cg(r), cg(i)];
  },
  KG = function (e) {
    if ((e === void 0 && (e = "margin"), typeof window > "u")) return GG;
    var t = WG(e),
      n = document.documentElement.clientWidth,
      r = window.innerWidth;
    return { left: t[0], top: t[1], right: t[2], gap: Math.max(0, r - n + t[2] - t[0]) };
  },
  YG = o2(),
  to = "data-scroll-locked",
  XG = function (e, t, n, r) {
    var i = e.left,
      o = e.top,
      s = e.right,
      a = e.gap;
    return (
      n === void 0 && (n = "margin"),
      `
  .`
        .concat(
          NG,
          ` {
   overflow: hidden `
        )
        .concat(
          r,
          `;
   padding-right: `
        )
        .concat(a, "px ")
        .concat(
          r,
          `;
  }
  body[`
        )
        .concat(
          to,
          `] {
    overflow: hidden `
        )
        .concat(
          r,
          `;
    overscroll-behavior: contain;
    `
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
    padding-top: `
                )
                .concat(
                  o,
                  `px;
    padding-right: `
                )
                .concat(
                  s,
                  `px;
    margin-left:0;
    margin-top:0;
    margin-right: `
                )
                .concat(a, "px ")
                .concat(
                  r,
                  `;
    `
                ),
            n === "padding" && "padding-right: ".concat(a, "px ").concat(r, ";"),
          ]
            .filter(Boolean)
            .join(""),
          `
  }

  .`
        )
        .concat(
          bu,
          ` {
    right: `
        )
        .concat(a, "px ")
        .concat(
          r,
          `;
  }

  .`
        )
        .concat(
          Eu,
          ` {
    margin-right: `
        )
        .concat(a, "px ")
        .concat(
          r,
          `;
  }

  .`
        )
        .concat(bu, " .")
        .concat(
          bu,
          ` {
    right: 0 `
        )
        .concat(
          r,
          `;
  }

  .`
        )
        .concat(Eu, " .")
        .concat(
          Eu,
          ` {
    margin-right: 0 `
        )
        .concat(
          r,
          `;
  }

  body[`
        )
        .concat(
          to,
          `] {
    `
        )
        .concat(MG, ": ")
        .concat(
          a,
          `px;
  }
`
        )
    );
  },
  WC = function () {
    var e = parseInt(document.body.getAttribute(to) || "0", 10);
    return isFinite(e) ? e : 0;
  },
  ZG = function () {
    _.useEffect(function () {
      return (
        document.body.setAttribute(to, (WC() + 1).toString()),
        function () {
          var e = WC() - 1;
          e <= 0 ? document.body.removeAttribute(to) : document.body.setAttribute(to, e.toString());
        }
      );
    }, []);
  },
  QG = function (e) {
    var t = e.noRelative,
      n = e.noImportant,
      r = e.gapMode,
      i = r === void 0 ? "margin" : r;
    ZG();
    var o = _.useMemo(
      function () {
        return KG(i);
      },
      [i]
    );
    return _.createElement(YG, { styles: XG(o, !t, i, n ? "" : "!important") });
  },
  qv = !1;
if (typeof window < "u")
  try {
    var Qa = Object.defineProperty({}, "passive", {
      get: function () {
        return (qv = !0), !0;
      },
    });
    window.addEventListener("test", Qa, Qa), window.removeEventListener("test", Qa, Qa);
  } catch {
    qv = !1;
  }
var bi = qv ? { passive: !1 } : !1,
  JG = function (e) {
    return e.tagName === "TEXTAREA";
  },
  s2 = function (e, t) {
    if (!(e instanceof Element)) return !1;
    var n = window.getComputedStyle(e);
    return n[t] !== "hidden" && !(n.overflowY === n.overflowX && !JG(e) && n[t] === "visible");
  },
  eW = function (e) {
    return s2(e, "overflowY");
  },
  tW = function (e) {
    return s2(e, "overflowX");
  },
  KC = function (e, t) {
    var n = t.ownerDocument,
      r = t;
    do {
      typeof ShadowRoot < "u" && r instanceof ShadowRoot && (r = r.host);
      var i = a2(e, r);
      if (i) {
        var o = u2(e, r),
          s = o[1],
          a = o[2];
        if (s > a) return !0;
      }
      r = r.parentNode;
    } while (r && r !== n.body);
    return !1;
  },
  nW = function (e) {
    var t = e.scrollTop,
      n = e.scrollHeight,
      r = e.clientHeight;
    return [t, n, r];
  },
  rW = function (e) {
    var t = e.scrollLeft,
      n = e.scrollWidth,
      r = e.clientWidth;
    return [t, n, r];
  },
  a2 = function (e, t) {
    return e === "v" ? eW(t) : tW(t);
  },
  u2 = function (e, t) {
    return e === "v" ? nW(t) : rW(t);
  },
  iW = function (e, t) {
    return e === "h" && t === "rtl" ? -1 : 1;
  },
  oW = function (e, t, n, r, i) {
    var o = iW(e, window.getComputedStyle(t).direction),
      s = o * r,
      a = n.target,
      u = t.contains(a),
      l = !1,
      c = s > 0,
      f = 0,
      d = 0;
    do {
      if (!a) break;
      var h = u2(e, a),
        v = h[0],
        p = h[1],
        y = h[2],
        m = p - y - o * v;
      (v || m) && a2(e, a) && ((f += m), (d += v));
      var g = a.parentNode;
      a = g && g.nodeType === Node.DOCUMENT_FRAGMENT_NODE ? g.host : g;
    } while ((!u && a !== document.body) || (u && (t.contains(a) || t === a)));
    return ((c && Math.abs(f) < 1) || (!c && Math.abs(d) < 1)) && (l = !0), l;
  },
  Ja = function (e) {
    return "changedTouches" in e
      ? [e.changedTouches[0].clientX, e.changedTouches[0].clientY]
      : [0, 0];
  },
  YC = function (e) {
    return [e.deltaX, e.deltaY];
  },
  XC = function (e) {
    return e && "current" in e ? e.current : e;
  },
  sW = function (e, t) {
    return e[0] === t[0] && e[1] === t[1];
  },
  aW = function (e) {
    return `
  .block-interactivity-`
      .concat(
        e,
        ` {pointer-events: none;}
  .allow-interactivity-`
      )
      .concat(
        e,
        ` {pointer-events: all;}
`
      );
  },
  uW = 0,
  Ei = [];
function lW(e) {
  var t = _.useRef([]),
    n = _.useRef([0, 0]),
    r = _.useRef(),
    i = _.useState(uW++)[0],
    o = _.useState(o2)[0],
    s = _.useRef(e);
  _.useEffect(
    function () {
      s.current = e;
    },
    [e]
  ),
    _.useEffect(
      function () {
        if (e.inert) {
          document.body.classList.add("block-interactivity-".concat(i));
          var p = AG([e.lockRef.current], (e.shards || []).map(XC), !0).filter(Boolean);
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
      [e.inert, e.lockRef.current, e.shards]
    );
  var a = _.useCallback(function (p, y) {
      if (("touches" in p && p.touches.length === 2) || (p.type === "wheel" && p.ctrlKey))
        return !s.current.allowPinchZoom;
      var m = Ja(p),
        g = n.current,
        w = "deltaX" in p ? p.deltaX : g[0] - m[0],
        x = "deltaY" in p ? p.deltaY : g[1] - m[1],
        S,
        C = p.target,
        E = Math.abs(w) > Math.abs(x) ? "h" : "v";
      if ("touches" in p && E === "h" && C.type === "range") return !1;
      var T = KC(E, C);
      if (!T) return !0;
      if ((T ? (S = E) : ((S = E === "v" ? "h" : "v"), (T = KC(E, C))), !T)) return !1;
      if ((!r.current && "changedTouches" in p && (w || x) && (r.current = S), !S)) return !0;
      var P = r.current || S;
      return oW(P, y, p, P === "h" ? w : x);
    }, []),
    u = _.useCallback(function (p) {
      var y = p;
      if (!(!Ei.length || Ei[Ei.length - 1] !== o)) {
        var m = "deltaY" in y ? YC(y) : Ja(y),
          g = t.current.filter(function (S) {
            return (
              S.name === y.type &&
              (S.target === y.target || y.target === S.shadowParent) &&
              sW(S.delta, m)
            );
          })[0];
        if (g && g.should) {
          y.cancelable && y.preventDefault();
          return;
        }
        if (!g) {
          var w = (s.current.shards || [])
              .map(XC)
              .filter(Boolean)
              .filter(function (S) {
                return S.contains(y.target);
              }),
            x = w.length > 0 ? a(y, w[0]) : !s.current.noIsolation;
          x && y.cancelable && y.preventDefault();
        }
      }
    }, []),
    l = _.useCallback(function (p, y, m, g) {
      var w = { name: p, delta: y, target: m, should: g, shadowParent: cW(m) };
      t.current.push(w),
        setTimeout(function () {
          t.current = t.current.filter(function (x) {
            return x !== w;
          });
        }, 1);
    }, []),
    c = _.useCallback(function (p) {
      (n.current = Ja(p)), (r.current = void 0);
    }, []),
    f = _.useCallback(function (p) {
      l(p.type, YC(p), p.target, a(p, e.lockRef.current));
    }, []),
    d = _.useCallback(function (p) {
      l(p.type, Ja(p), p.target, a(p, e.lockRef.current));
    }, []);
  _.useEffect(function () {
    return (
      Ei.push(o),
      e.setCallbacks({ onScrollCapture: f, onWheelCapture: f, onTouchMoveCapture: d }),
      document.addEventListener("wheel", u, bi),
      document.addEventListener("touchmove", u, bi),
      document.addEventListener("touchstart", c, bi),
      function () {
        (Ei = Ei.filter(function (p) {
          return p !== o;
        })),
          document.removeEventListener("wheel", u, bi),
          document.removeEventListener("touchmove", u, bi),
          document.removeEventListener("touchstart", c, bi);
      }
    );
  }, []);
  var h = e.removeScrollBar,
    v = e.inert;
  return _.createElement(
    _.Fragment,
    null,
    v ? _.createElement(o, { styles: aW(i) }) : null,
    h ? _.createElement(QG, { noRelative: e.noRelative, gapMode: e.gapMode }) : null
  );
}
function cW(e) {
  for (var t = null; e !== null; )
    e instanceof ShadowRoot && ((t = e.host), (e = e.host)), (e = e.parentNode);
  return t;
}
const fW = jG(i2, lW);
var l2 = _.forwardRef(function (e, t) {
  return _.createElement(dc, hn({}, e, { ref: t, sideCar: fW }));
});
l2.classNames = dc.classNames;
var dW = function (e) {
    if (typeof document > "u") return null;
    var t = Array.isArray(e) ? e[0] : e;
    return t.ownerDocument.body;
  },
  Ci = new WeakMap(),
  eu = new WeakMap(),
  tu = {},
  fg = 0,
  c2 = function (e) {
    return e && (e.host || c2(e.parentNode));
  },
  hW = function (e, t) {
    return t
      .map(function (n) {
        if (e.contains(n)) return n;
        var r = c2(n);
        return r && e.contains(r)
          ? r
          : (console.error("aria-hidden", n, "in not contained inside", e, ". Doing nothing"),
            null);
      })
      .filter(function (n) {
        return !!n;
      });
  },
  pW = function (e, t, n, r) {
    var i = hW(t, Array.isArray(e) ? e : [e]);
    tu[n] || (tu[n] = new WeakMap());
    var o = tu[n],
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
                p = (Ci.get(d) || 0) + 1,
                y = (o.get(d) || 0) + 1;
              Ci.set(d, p),
                o.set(d, y),
                s.push(d),
                p === 1 && v && eu.set(d, !0),
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
      fg++,
      function () {
        s.forEach(function (f) {
          var d = Ci.get(f) - 1,
            h = o.get(f) - 1;
          Ci.set(f, d),
            o.set(f, h),
            d || (eu.has(f) || f.removeAttribute(r), eu.delete(f)),
            h || f.removeAttribute(n);
        }),
          fg--,
          fg || ((Ci = new WeakMap()), (Ci = new WeakMap()), (eu = new WeakMap()), (tu = {}));
      }
    );
  },
  mW = function (e, t, n) {
    n === void 0 && (n = "data-aria-hidden");
    var r = Array.from(Array.isArray(e) ? e : [e]),
      i = dW(e);
    return i
      ? (r.push.apply(r, Array.from(i.querySelectorAll("[aria-live], script"))),
        pW(r, i, n, "aria-hidden"))
      : function () {
          return null;
        };
  },
  hc = "Dialog",
  [f2, gX] = cc(hc),
  [gW, sn] = f2(hc),
  d2 = (e) => {
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
      [l, c] = z0({ prop: r, defaultProp: i ?? !1, onChange: o, caller: hc });
    return M.jsx(gW, {
      scope: t,
      triggerRef: a,
      contentRef: u,
      contentId: ws(),
      titleId: ws(),
      descriptionId: ws(),
      open: l,
      onOpenChange: c,
      onOpenToggle: _.useCallback(() => c((f) => !f), [c]),
      modal: s,
      children: n,
    });
  };
d2.displayName = hc;
var h2 = "DialogTrigger",
  vW = _.forwardRef((e, t) => {
    const { __scopeDialog: n, ...r } = e,
      i = sn(h2, n),
      o = xn(t, i.triggerRef);
    return M.jsx(ct.button, {
      type: "button",
      "aria-haspopup": "dialog",
      "aria-expanded": i.open,
      "aria-controls": i.contentId,
      "data-state": G0(i.open),
      ...r,
      ref: o,
      onClick: Ye(e.onClick, i.onOpenToggle),
    });
  });
vW.displayName = h2;
var U0 = "DialogPortal",
  [yW, p2] = f2(U0, { forceMount: void 0 }),
  m2 = (e) => {
    const { __scopeDialog: t, forceMount: n, children: r, container: i } = e,
      o = sn(U0, t);
    return M.jsx(yW, {
      scope: t,
      forceMount: n,
      children: _.Children.map(r, (s) =>
        M.jsx(va, {
          present: n || o.open,
          children: M.jsx(t2, { asChild: !0, container: i, children: s }),
        })
      ),
    });
  };
m2.displayName = U0;
var dl = "DialogOverlay",
  g2 = _.forwardRef((e, t) => {
    const n = p2(dl, e.__scopeDialog),
      { forceMount: r = n.forceMount, ...i } = e,
      o = sn(dl, e.__scopeDialog);
    return o.modal
      ? M.jsx(va, { present: r || o.open, children: M.jsx(xW, { ...i, ref: t }) })
      : null;
  });
g2.displayName = dl;
var wW = Zs("DialogOverlay.RemoveScroll"),
  xW = _.forwardRef((e, t) => {
    const { __scopeDialog: n, ...r } = e,
      i = sn(dl, n);
    return M.jsx(l2, {
      as: wW,
      allowPinchZoom: !0,
      shards: [i.contentRef],
      children: M.jsx(ct.div, {
        "data-state": G0(i.open),
        ...r,
        ref: t,
        style: { pointerEvents: "auto", ...r.style },
      }),
    });
  }),
  li = "DialogContent",
  v2 = _.forwardRef((e, t) => {
    const n = p2(li, e.__scopeDialog),
      { forceMount: r = n.forceMount, ...i } = e,
      o = sn(li, e.__scopeDialog);
    return M.jsx(va, {
      present: r || o.open,
      children: o.modal ? M.jsx(_W, { ...i, ref: t }) : M.jsx(SW, { ...i, ref: t }),
    });
  });
v2.displayName = li;
var _W = _.forwardRef((e, t) => {
    const n = sn(li, e.__scopeDialog),
      r = _.useRef(null),
      i = xn(t, n.contentRef, r);
    return (
      _.useEffect(() => {
        const o = r.current;
        if (o) return mW(o);
      }, []),
      M.jsx(y2, {
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
  SW = _.forwardRef((e, t) => {
    const n = sn(li, e.__scopeDialog),
      r = _.useRef(!1),
      i = _.useRef(!1);
    return M.jsx(y2, {
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
  y2 = _.forwardRef((e, t) => {
    const { __scopeDialog: n, trapFocus: r, onOpenAutoFocus: i, onCloseAutoFocus: o, ...s } = e,
      a = sn(li, n),
      u = _.useRef(null),
      l = xn(t, u);
    return (
      RG(),
      M.jsxs(M.Fragment, {
        children: [
          M.jsx(JM, {
            asChild: !0,
            loop: !0,
            trapped: r,
            onMountAutoFocus: i,
            onUnmountAutoFocus: o,
            children: M.jsx(ZM, {
              role: "dialog",
              id: a.contentId,
              "aria-describedby": a.descriptionId,
              "aria-labelledby": a.titleId,
              "data-state": G0(a.open),
              ...s,
              ref: l,
              onDismiss: () => a.onOpenChange(!1),
            }),
          }),
          M.jsxs(M.Fragment, {
            children: [
              M.jsx(bW, { titleId: a.titleId }),
              M.jsx(CW, { contentRef: u, descriptionId: a.descriptionId }),
            ],
          }),
        ],
      })
    );
  }),
  H0 = "DialogTitle",
  w2 = _.forwardRef((e, t) => {
    const { __scopeDialog: n, ...r } = e,
      i = sn(H0, n);
    return M.jsx(ct.h2, { id: i.titleId, ...r, ref: t });
  });
w2.displayName = H0;
var x2 = "DialogDescription",
  _2 = _.forwardRef((e, t) => {
    const { __scopeDialog: n, ...r } = e,
      i = sn(x2, n);
    return M.jsx(ct.p, { id: i.descriptionId, ...r, ref: t });
  });
_2.displayName = x2;
var S2 = "DialogClose",
  b2 = _.forwardRef((e, t) => {
    const { __scopeDialog: n, ...r } = e,
      i = sn(S2, n);
    return M.jsx(ct.button, {
      type: "button",
      ...r,
      ref: t,
      onClick: Ye(e.onClick, () => i.onOpenChange(!1)),
    });
  });
b2.displayName = S2;
function G0(e) {
  return e ? "open" : "closed";
}
var E2 = "DialogTitleWarning",
  [vX, C2] = FH(E2, { contentName: li, titleName: H0, docsSlug: "dialog" }),
  bW = ({ titleId: e }) => {
    const t = C2(E2),
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
  EW = "DialogDescriptionWarning",
  CW = ({ contentRef: e, descriptionId: t }) => {
    const r = `Warning: Missing \`Description\` or \`aria-describedby={undefined}\` for {${
      C2(EW).contentName
    }}.`;
    return (
      _.useEffect(() => {
        var o;
        const i = (o = e.current) == null ? void 0 : o.getAttribute("aria-describedby");
        t && i && (document.getElementById(t) || console.warn(r));
      }, [r, e, t]),
      null
    );
  },
  TW = d2,
  kW = m2,
  T2 = g2,
  k2 = v2,
  P2 = w2,
  R2 = _2,
  PW = b2;
const RW = TW,
  AW = kW,
  A2 = _.forwardRef(({ className: e, ...t }, n) =>
    M.jsx(T2, {
      ref: n,
      className: ke(
        "fixed inset-0 z-50 bg-black/80 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0",
        e
      ),
      ...t,
    })
  );
A2.displayName = T2.displayName;
const N2 = _.forwardRef(({ className: e, children: t, ...n }, r) =>
  M.jsxs(AW, {
    children: [
      M.jsx(A2, {}),
      M.jsxs(k2, {
        ref: r,
        className: ke(
          "fixed left-[50%] top-[50%] z-50 grid w-full max-w-lg translate-x-[-50%] translate-y-[-50%] gap-4 border bg-background p-6 shadow-lg duration-200 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95 data-[state=closed]:slide-out-to-left-1/2 data-[state=closed]:slide-out-to-top-[48%] data-[state=open]:slide-in-from-left-1/2 data-[state=open]:slide-in-from-top-[48%] sm:rounded-lg",
          e
        ),
        ...n,
        children: [
          t,
          M.jsxs(PW, {
            className:
              "absolute right-4 top-4 rounded-sm opacity-70 ring-offset-background transition-opacity hover:opacity-100 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:pointer-events-none data-[state=open]:bg-accent data-[state=open]:text-muted-foreground",
            children: [
              M.jsx(YU, { className: "h-4 w-4" }),
              M.jsx("span", { className: "sr-only", children: "Close" }),
            ],
          }),
        ],
      }),
    ],
  })
);
N2.displayName = k2.displayName;
const M2 = ({ className: e, ...t }) =>
  M.jsx("div", { className: ke("flex flex-col space-y-1.5 text-center sm:text-left", e), ...t });
M2.displayName = "DialogHeader";
const I2 = ({ className: e, ...t }) =>
  M.jsx("div", {
    className: ke("flex flex-col-reverse sm:flex-row sm:justify-end sm:space-x-2", e),
    ...t,
  });
I2.displayName = "DialogFooter";
const D2 = _.forwardRef(({ className: e, ...t }, n) =>
  M.jsx(P2, { ref: n, className: ke("text-lg font-semibold leading-none tracking-tight", e), ...t })
);
D2.displayName = P2.displayName;
const NW = _.forwardRef(({ className: e, ...t }, n) =>
  M.jsx(R2, { ref: n, className: ke("text-sm text-muted-foreground", e), ...t })
);
NW.displayName = R2.displayName;
const O2 = _.forwardRef(({ className: e, type: t, ...n }, r) =>
  M.jsx("input", {
    type: t,
    className: ke(
      "flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-base ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium file:text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 md:text-sm",
      e
    ),
    ref: r,
    ...n,
  })
);
O2.displayName = "Input";
const L2 = _.forwardRef(({ className: e, ...t }, n) =>
  M.jsx("textarea", {
    className: ke(
      "flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-base ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 md:text-sm",
      e
    ),
    ref: n,
    ...t,
  })
);
L2.displayName = "Textarea";
const F2 = _.createContext({});
function W0(e) {
  const t = _.useRef(null);
  return t.current === null && (t.current = e()), t.current;
}
const K0 = _.createContext(null),
  pc = _.createContext({ transformPagePoint: (e) => e, isStatic: !1, reducedMotion: "never" });
function MW(e = !0) {
  const t = _.useContext(K0);
  if (t === null) return [!0, null];
  const { isPresent: n, onExitComplete: r, register: i } = t,
    o = _.useId();
  _.useEffect(() => {
    e && i(o);
  }, [e]);
  const s = _.useCallback(() => e && r && r(o), [o, r, e]);
  return !n && r ? [!1, s] : [!0];
}
const Y0 = typeof window < "u",
  X0 = Y0 ? _.useLayoutEffect : _.useEffect,
  Ct = (e) => e;
let V2 = Ct;
function Z0(e) {
  let t;
  return () => (t === void 0 && (t = e()), t);
}
const mo = (e, t, n) => {
    const r = t - e;
    return r === 0 ? 1 : (n - e) / r;
  },
  jn = (e) => e * 1e3,
  qn = (e) => e / 1e3,
  IW = { useManualTiming: !1 };
function DW(e) {
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
const nu = ["read", "resolveKeyframes", "update", "preRender", "render", "postRender"],
  OW = 40;
function j2(e, t) {
  let n = !1,
    r = !0;
  const i = { delta: 0, timestamp: 0, isProcessing: !1 },
    o = () => (n = !0),
    s = nu.reduce((m, g) => ((m[g] = DW(o)), m), {}),
    { read: a, resolveKeyframes: u, update: l, preRender: c, render: f, postRender: d } = s,
    h = () => {
      const m = performance.now();
      (n = !1),
        (i.delta = r ? 1e3 / 60 : Math.max(Math.min(m - i.timestamp, OW), 1)),
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
    schedule: nu.reduce((m, g) => {
      const w = s[g];
      return (m[g] = (x, S = !1, C = !1) => (n || v(), w.schedule(x, S, C))), m;
    }, {}),
    cancel: (m) => {
      for (let g = 0; g < nu.length; g++) s[nu[g]].cancel(m);
    },
    state: i,
    steps: s,
  };
}
const { schedule: fe, cancel: Kn, state: $e, steps: dg } = j2(
    typeof requestAnimationFrame < "u" ? requestAnimationFrame : Ct,
    !0
  ),
  q2 = _.createContext({ strict: !1 }),
  ZC = {
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
  go = {};
for (const e in ZC) go[e] = { isEnabled: (t) => ZC[e].some((n) => !!t[n]) };
function LW(e) {
  for (const t in e) go[t] = { ...go[t], ...e[t] };
}
const FW = new Set([
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
function hl(e) {
  return (
    e.startsWith("while") ||
    (e.startsWith("drag") && e !== "draggable") ||
    e.startsWith("layout") ||
    e.startsWith("onTap") ||
    e.startsWith("onPan") ||
    e.startsWith("onLayout") ||
    FW.has(e)
  );
}
let $2 = (e) => !hl(e);
function VW(e) {
  e && ($2 = (t) => (t.startsWith("on") ? !hl(t) : e(t)));
}
try {
  VW(require("@emotion/is-prop-valid").default);
} catch {}
function jW(e, t, n) {
  const r = {};
  for (const i in e)
    (i === "values" && typeof e.values == "object") ||
      (($2(i) ||
        (n === !0 && hl(i)) ||
        (!t && !hl(i)) ||
        (e.draggable && i.startsWith("onDrag"))) &&
        (r[i] = e[i]));
  return r;
}
function qW(e) {
  if (typeof Proxy > "u") return e;
  const t = new Map(),
    n = (...r) => e(...r);
  return new Proxy(n, {
    get: (r, i) => (i === "create" ? e : (t.has(i) || t.set(i, e(i)), t.get(i))),
  });
}
const mc = _.createContext({});
function Js(e) {
  return typeof e == "string" || Array.isArray(e);
}
function gc(e) {
  return e !== null && typeof e == "object" && typeof e.start == "function";
}
const Q0 = ["animate", "whileInView", "whileFocus", "whileHover", "whileTap", "whileDrag", "exit"],
  J0 = ["initial", ...Q0];
function vc(e) {
  return gc(e.animate) || J0.some((t) => Js(e[t]));
}
function z2(e) {
  return !!(vc(e) || e.variants);
}
function $W(e, t) {
  if (vc(e)) {
    const { initial: n, animate: r } = e;
    return { initial: n === !1 || Js(n) ? n : void 0, animate: Js(r) ? r : void 0 };
  }
  return e.inherit !== !1 ? t : {};
}
function zW(e) {
  const { initial: t, animate: n } = $W(e, _.useContext(mc));
  return _.useMemo(() => ({ initial: t, animate: n }), [QC(t), QC(n)]);
}
function QC(e) {
  return Array.isArray(e) ? e.join(" ") : e;
}
const BW = Symbol.for("motionComponentSymbol");
function qi(e) {
  return e && typeof e == "object" && Object.prototype.hasOwnProperty.call(e, "current");
}
function UW(e, t, n) {
  return _.useCallback(
    (r) => {
      r && e.onMount && e.onMount(r),
        t && (r ? t.mount(r) : t.unmount()),
        n && (typeof n == "function" ? n(r) : qi(n) && (n.current = r));
    },
    [t]
  );
}
const ew = (e) => e.replace(/([a-z])([A-Z])/gu, "$1-$2").toLowerCase(),
  HW = "framerAppearId",
  B2 = "data-" + ew(HW),
  { schedule: tw } = j2(queueMicrotask, !1),
  U2 = _.createContext({});
function GW(e, t, n, r, i) {
  var o, s;
  const { visualElement: a } = _.useContext(mc),
    u = _.useContext(q2),
    l = _.useContext(K0),
    c = _.useContext(pc).reducedMotion,
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
    h = _.useContext(U2);
  d && !d.projection && i && (d.type === "html" || d.type === "svg") && WW(f.current, n, i, h);
  const v = _.useRef(!1);
  _.useInsertionEffect(() => {
    d && v.current && d.update(n, l);
  });
  const p = n[B2],
    y = _.useRef(
      !!p &&
        !(!((o = window.MotionHandoffIsComplete) === null || o === void 0) && o.call(window, p)) &&
        ((s = window.MotionHasOptimisedAnimation) === null || s === void 0
          ? void 0
          : s.call(window, p))
    );
  return (
    X0(() => {
      d &&
        ((v.current = !0),
        (window.MotionIsMounted = !0),
        d.updateFeatures(),
        tw.render(d.render),
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
function WW(e, t, n, r) {
  const { layoutId: i, layout: o, drag: s, dragConstraints: a, layoutScroll: u, layoutRoot: l } = t;
  (e.projection = new n(e.latestValues, t["data-framer-portal-id"] ? void 0 : H2(e.parent))),
    e.projection.setOptions({
      layoutId: i,
      layout: o,
      alwaysMeasureLayout: !!s || (a && qi(a)),
      visualElement: e,
      animationType: typeof o == "string" ? o : "both",
      initialPromotionConfig: r,
      layoutScroll: u,
      layoutRoot: l,
    });
}
function H2(e) {
  if (e) return e.options.allowProjection !== !1 ? e.projection : H2(e.parent);
}
function KW({
  preloadedFeatures: e,
  createVisualElement: t,
  useRender: n,
  useVisualState: r,
  Component: i,
}) {
  var o, s;
  e && LW(e);
  function a(l, c) {
    let f;
    const d = { ..._.useContext(pc), ...l, layoutId: YW(l) },
      { isStatic: h } = d,
      v = zW(l),
      p = r(l, h);
    if (!h && Y0) {
      XW();
      const y = ZW(d);
      (f = y.MeasureLayout), (v.visualElement = GW(i, p, d, t, y.ProjectionNode));
    }
    return M.jsxs(mc.Provider, {
      value: v,
      children: [
        f && v.visualElement ? M.jsx(f, { visualElement: v.visualElement, ...d }) : null,
        n(i, l, UW(p, v.visualElement, c), p, h, v.visualElement),
      ],
    });
  }
  a.displayName = `motion.${
    typeof i == "string"
      ? i
      : `create(${
          (s = (o = i.displayName) !== null && o !== void 0 ? o : i.name) !== null && s !== void 0
            ? s
            : ""
        })`
  }`;
  const u = _.forwardRef(a);
  return (u[BW] = i), u;
}
function YW({ layoutId: e }) {
  const t = _.useContext(F2).id;
  return t && e !== void 0 ? t + "-" + e : e;
}
function XW(e, t) {
  _.useContext(q2).strict;
}
function ZW(e) {
  const { drag: t, layout: n } = go;
  if (!t && !n) return {};
  const r = { ...t, ...n };
  return {
    MeasureLayout:
      (t != null && t.isEnabled(e)) || (n != null && n.isEnabled(e)) ? r.MeasureLayout : void 0,
    ProjectionNode: r.ProjectionNode,
  };
}
const QW = [
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
function nw(e) {
  return typeof e != "string" || e.includes("-") ? !1 : !!(QW.indexOf(e) > -1 || /[A-Z]/u.test(e));
}
function JC(e) {
  const t = [{}, {}];
  return (
    e == null ||
      e.values.forEach((n, r) => {
        (t[0][r] = n.get()), (t[1][r] = n.getVelocity());
      }),
    t
  );
}
function rw(e, t, n, r) {
  if (typeof t == "function") {
    const [i, o] = JC(r);
    t = t(n !== void 0 ? n : e.custom, i, o);
  }
  if ((typeof t == "string" && (t = e.variants && e.variants[t]), typeof t == "function")) {
    const [i, o] = JC(r);
    t = t(n !== void 0 ? n : e.custom, i, o);
  }
  return t;
}
const $v = (e) => Array.isArray(e),
  JW = (e) => !!(e && typeof e == "object" && e.mix && e.toValue),
  e9 = (e) => ($v(e) ? e[e.length - 1] || 0 : e),
  Be = (e) => !!(e && e.getVelocity);
function Cu(e) {
  const t = Be(e) ? e.get() : e;
  return JW(t) ? t.toValue() : t;
}
function t9({ scrapeMotionValuesFromProps: e, createRenderState: t, onUpdate: n }, r, i, o) {
  const s = { latestValues: n9(r, i, o, e), renderState: t() };
  return (
    n && ((s.onMount = (a) => n({ props: r, current: a, ...s })), (s.onUpdate = (a) => n(a))), s
  );
}
const G2 = (e) => (t, n) => {
  const r = _.useContext(mc),
    i = _.useContext(K0),
    o = () => t9(e, t, r, i);
  return n ? o() : W0(o);
};
function n9(e, t, n, r) {
  const i = {},
    o = r(e, {});
  for (const d in o) i[d] = Cu(o[d]);
  let { initial: s, animate: a } = e;
  const u = vc(e),
    l = z2(e);
  t &&
    l &&
    !u &&
    e.inherit !== !1 &&
    (s === void 0 && (s = t.initial), a === void 0 && (a = t.animate));
  let c = n ? n.initial === !1 : !1;
  c = c || s === !1;
  const f = c ? a : s;
  if (f && typeof f != "boolean" && !gc(f)) {
    const d = Array.isArray(f) ? f : [f];
    for (let h = 0; h < d.length; h++) {
      const v = rw(e, d[h]);
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
const Po = [
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
  vi = new Set(Po),
  W2 = (e) => (t) => typeof t == "string" && t.startsWith(e),
  K2 = W2("--"),
  r9 = W2("var(--"),
  iw = (e) => (r9(e) ? i9.test(e.split("/*")[0].trim()) : !1),
  i9 = /var\(--(?:[\w-]+\s*|[\w-]+\s*,(?:\s*[^)(\s]|\s*\((?:[^)(]|\([^)(]*\))*\))+\s*)\)$/iu,
  Y2 = (e, t) => (t && typeof e == "number" ? t.transform(e) : e),
  Yn = (e, t, n) => (n > t ? t : n < e ? e : n),
  Ro = { test: (e) => typeof e == "number", parse: parseFloat, transform: (e) => e },
  ea = { ...Ro, transform: (e) => Yn(0, 1, e) },
  ru = { ...Ro, default: 1 },
  ya = (e) => ({
    test: (t) => typeof t == "string" && t.endsWith(e) && t.split(" ").length === 1,
    parse: parseFloat,
    transform: (t) => `${t}${e}`,
  }),
  sr = ya("deg"),
  yn = ya("%"),
  Z = ya("px"),
  o9 = ya("vh"),
  s9 = ya("vw"),
  eT = { ...yn, parse: (e) => yn.parse(e) / 100, transform: (e) => yn.transform(e * 100) },
  a9 = {
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
  u9 = {
    rotate: sr,
    rotateX: sr,
    rotateY: sr,
    rotateZ: sr,
    scale: ru,
    scaleX: ru,
    scaleY: ru,
    scaleZ: ru,
    skew: sr,
    skewX: sr,
    skewY: sr,
    distance: Z,
    translateX: Z,
    translateY: Z,
    translateZ: Z,
    x: Z,
    y: Z,
    z: Z,
    perspective: Z,
    transformPerspective: Z,
    opacity: ea,
    originX: eT,
    originY: eT,
    originZ: Z,
  },
  tT = { ...Ro, transform: Math.round },
  ow = { ...a9, ...u9, zIndex: tT, size: Z, fillOpacity: ea, strokeOpacity: ea, numOctaves: tT },
  l9 = { x: "translateX", y: "translateY", z: "translateZ", transformPerspective: "perspective" },
  c9 = Po.length;
function f9(e, t, n) {
  let r = "",
    i = !0;
  for (let o = 0; o < c9; o++) {
    const s = Po[o],
      a = e[s];
    if (a === void 0) continue;
    let u = !0;
    if (
      (typeof a == "number"
        ? (u = a === (s.startsWith("scale") ? 1 : 0))
        : (u = parseFloat(a) === 0),
      !u || n)
    ) {
      const l = Y2(a, ow[s]);
      if (!u) {
        i = !1;
        const c = l9[s] || s;
        r += `${c}(${l}) `;
      }
      n && (t[s] = l);
    }
  }
  return (r = r.trim()), n ? (r = n(t, i ? "" : r)) : i && (r = "none"), r;
}
function sw(e, t, n) {
  const { style: r, vars: i, transformOrigin: o } = e;
  let s = !1,
    a = !1;
  for (const u in t) {
    const l = t[u];
    if (vi.has(u)) {
      s = !0;
      continue;
    } else if (K2(u)) {
      i[u] = l;
      continue;
    } else {
      const c = Y2(l, ow[u]);
      u.startsWith("origin") ? ((a = !0), (o[u] = c)) : (r[u] = c);
    }
  }
  if (
    (t.transform ||
      (s || n ? (r.transform = f9(t, e.transform, n)) : r.transform && (r.transform = "none")),
    a)
  ) {
    const { originX: u = "50%", originY: l = "50%", originZ: c = 0 } = o;
    r.transformOrigin = `${u} ${l} ${c}`;
  }
}
const d9 = { offset: "stroke-dashoffset", array: "stroke-dasharray" },
  h9 = { offset: "strokeDashoffset", array: "strokeDasharray" };
function p9(e, t, n = 1, r = 0, i = !0) {
  e.pathLength = 1;
  const o = i ? d9 : h9;
  e[o.offset] = Z.transform(-r);
  const s = Z.transform(t),
    a = Z.transform(n);
  e[o.array] = `${s} ${a}`;
}
function nT(e, t, n) {
  return typeof e == "string" ? e : Z.transform(t + n * e);
}
function m9(e, t, n) {
  const r = nT(t, e.x, e.width),
    i = nT(n, e.y, e.height);
  return `${r} ${i}`;
}
function aw(
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
  f
) {
  if ((sw(e, l, f), c)) {
    e.style.viewBox && (e.attrs.viewBox = e.style.viewBox);
    return;
  }
  (e.attrs = e.style), (e.style = {});
  const { attrs: d, style: h, dimensions: v } = e;
  d.transform && (v && (h.transform = d.transform), delete d.transform),
    v &&
      (i !== void 0 || o !== void 0 || h.transform) &&
      (h.transformOrigin = m9(v, i !== void 0 ? i : 0.5, o !== void 0 ? o : 0.5)),
    t !== void 0 && (d.x = t),
    n !== void 0 && (d.y = n),
    r !== void 0 && (d.scale = r),
    s !== void 0 && p9(d, s, a, u, !1);
}
const uw = () => ({ style: {}, transform: {}, transformOrigin: {}, vars: {} }),
  X2 = () => ({ ...uw(), attrs: {} }),
  lw = (e) => typeof e == "string" && e.toLowerCase() === "svg";
function Z2(e, { style: t, vars: n }, r, i) {
  Object.assign(e.style, t, i && i.getProjectionStyles(r));
  for (const o in n) e.style.setProperty(o, n[o]);
}
const Q2 = new Set([
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
function J2(e, t, n, r) {
  Z2(e, t, void 0, r);
  for (const i in t.attrs) e.setAttribute(Q2.has(i) ? i : ew(i), t.attrs[i]);
}
const pl = {};
function g9(e) {
  Object.assign(pl, e);
}
function eI(e, { layout: t, layoutId: n }) {
  return (
    vi.has(e) || e.startsWith("origin") || ((t || n !== void 0) && (!!pl[e] || e === "opacity"))
  );
}
function cw(e, t, n) {
  var r;
  const { style: i } = e,
    o = {};
  for (const s in i)
    (Be(i[s]) ||
      (t.style && Be(t.style[s])) ||
      eI(s, e) ||
      ((r = n == null ? void 0 : n.getValue(s)) === null || r === void 0 ? void 0 : r.liveStyle) !==
        void 0) &&
      (o[s] = i[s]);
  return o;
}
function tI(e, t, n) {
  const r = cw(e, t, n);
  for (const i in e)
    if (Be(e[i]) || Be(t[i])) {
      const o = Po.indexOf(i) !== -1 ? "attr" + i.charAt(0).toUpperCase() + i.substring(1) : i;
      r[o] = e[i];
    }
  return r;
}
function v9(e, t) {
  try {
    t.dimensions = typeof e.getBBox == "function" ? e.getBBox() : e.getBoundingClientRect();
  } catch {
    t.dimensions = { x: 0, y: 0, width: 0, height: 0 };
  }
}
const rT = ["x", "y", "width", "height", "cx", "cy", "r"],
  y9 = {
    useVisualState: G2({
      scrapeMotionValuesFromProps: tI,
      createRenderState: X2,
      onUpdate: ({ props: e, prevProps: t, current: n, renderState: r, latestValues: i }) => {
        if (!n) return;
        let o = !!e.drag;
        if (!o) {
          for (const a in i)
            if (vi.has(a)) {
              o = !0;
              break;
            }
        }
        if (!o) return;
        let s = !t;
        if (t)
          for (let a = 0; a < rT.length; a++) {
            const u = rT[a];
            e[u] !== t[u] && (s = !0);
          }
        s &&
          fe.read(() => {
            v9(n, r),
              fe.render(() => {
                aw(r, i, lw(n.tagName), e.transformTemplate), J2(n, r);
              });
          });
      },
    }),
  },
  w9 = { useVisualState: G2({ scrapeMotionValuesFromProps: cw, createRenderState: uw }) };
function nI(e, t, n) {
  for (const r in t) !Be(t[r]) && !eI(r, n) && (e[r] = t[r]);
}
function x9({ transformTemplate: e }, t) {
  return _.useMemo(() => {
    const n = uw();
    return sw(n, t, e), Object.assign({}, n.vars, n.style);
  }, [t]);
}
function _9(e, t) {
  const n = e.style || {},
    r = {};
  return nI(r, n, e), Object.assign(r, x9(e, t)), r;
}
function S9(e, t) {
  const n = {},
    r = _9(e, t);
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
function b9(e, t, n, r) {
  const i = _.useMemo(() => {
    const o = X2();
    return aw(o, t, lw(r), e.transformTemplate), { ...o.attrs, style: { ...o.style } };
  }, [t]);
  if (e.style) {
    const o = {};
    nI(o, e.style, e), (i.style = { ...o, ...i.style });
  }
  return i;
}
function E9(e = !1) {
  return (n, r, i, { latestValues: o }, s) => {
    const u = (nw(n) ? b9 : S9)(r, o, s, n),
      l = jW(r, typeof n == "string", e),
      c = n !== _.Fragment ? { ...l, ...u, ref: i } : {},
      { children: f } = r,
      d = _.useMemo(() => (Be(f) ? f.get() : f), [f]);
    return _.createElement(n, { ...c, children: d });
  };
}
function C9(e, t) {
  return function (r, { forwardMotionProps: i } = { forwardMotionProps: !1 }) {
    const s = {
      ...(nw(r) ? y9 : w9),
      preloadedFeatures: e,
      useRender: E9(i),
      createVisualElement: t,
      Component: r,
    };
    return KW(s);
  };
}
function rI(e, t) {
  if (!Array.isArray(t)) return !1;
  const n = t.length;
  if (n !== e.length) return !1;
  for (let r = 0; r < n; r++) if (t[r] !== e[r]) return !1;
  return !0;
}
function yc(e, t, n) {
  const r = e.getProps();
  return rw(r, t, n !== void 0 ? n : r.custom, e);
}
const T9 = Z0(() => window.ScrollTimeline !== void 0);
class k9 {
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
      if (T9() && i.attachTimeline) return i.attachTimeline(t);
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
class P9 extends k9 {
  then(t, n) {
    return Promise.all(this.animations).then(t).catch(n);
  }
}
function fw(e, t) {
  return e ? e[t] || e.default || e : void 0;
}
const zv = 2e4;
function iI(e) {
  let t = 0;
  const n = 50;
  let r = e.next(t);
  for (; !r.done && t < zv; ) (t += n), (r = e.next(t));
  return t >= zv ? 1 / 0 : t;
}
function dw(e) {
  return typeof e == "function";
}
function iT(e, t) {
  (e.timeline = t), (e.onfinish = null);
}
const hw = (e) => Array.isArray(e) && typeof e[0] == "number",
  R9 = { linearEasing: void 0 };
function A9(e, t) {
  const n = Z0(e);
  return () => {
    var r;
    return (r = R9[t]) !== null && r !== void 0 ? r : n();
  };
}
const ml = A9(() => {
    try {
      document.createElement("div").animate({ opacity: 0 }, { easing: "linear(0, 1)" });
    } catch {
      return !1;
    }
    return !0;
  }, "linearEasing"),
  oI = (e, t, n = 10) => {
    let r = "";
    const i = Math.max(Math.round(t / n), 2);
    for (let o = 0; o < i; o++) r += e(mo(0, i - 1, o)) + ", ";
    return `linear(${r.substring(0, r.length - 2)})`;
  };
function sI(e) {
  return !!(
    (typeof e == "function" && ml()) ||
    !e ||
    (typeof e == "string" && (e in Bv || ml())) ||
    hw(e) ||
    (Array.isArray(e) && e.every(sI))
  );
}
const as = ([e, t, n, r]) => `cubic-bezier(${e}, ${t}, ${n}, ${r})`,
  Bv = {
    linear: "linear",
    ease: "ease",
    easeIn: "ease-in",
    easeOut: "ease-out",
    easeInOut: "ease-in-out",
    circIn: as([0, 0.65, 0.55, 1]),
    circOut: as([0.55, 0, 1, 0.45]),
    backIn: as([0.31, 0.01, 0.66, -0.59]),
    backOut: as([0.33, 1.53, 0.69, 0.99]),
  };
function aI(e, t) {
  if (e)
    return typeof e == "function" && ml()
      ? oI(e, t)
      : hw(e)
      ? as(e)
      : Array.isArray(e)
      ? e.map((n) => aI(n, t) || Bv.easeOut)
      : Bv[e];
}
const Gt = { x: !1, y: !1 };
function uI() {
  return Gt.x || Gt.y;
}
function N9(e, t, n) {
  var r;
  if (e instanceof Element) return [e];
  if (typeof e == "string") {
    let i = document;
    const o = (r = void 0) !== null && r !== void 0 ? r : i.querySelectorAll(e);
    return o ? Array.from(o) : [];
  }
  return Array.from(e);
}
function lI(e, t) {
  const n = N9(e),
    r = new AbortController(),
    i = { passive: !0, ...t, signal: r.signal };
  return [n, i, () => r.abort()];
}
function oT(e) {
  return (t) => {
    t.pointerType === "touch" || uI() || e(t);
  };
}
function M9(e, t, n = {}) {
  const [r, i, o] = lI(e, n),
    s = oT((a) => {
      const { target: u } = a,
        l = t(a);
      if (typeof l != "function" || !u) return;
      const c = oT((f) => {
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
const cI = (e, t) => (t ? (e === t ? !0 : cI(e, t.parentElement)) : !1),
  pw = (e) =>
    e.pointerType === "mouse" ? typeof e.button != "number" || e.button <= 0 : e.isPrimary !== !1,
  I9 = new Set(["BUTTON", "INPUT", "SELECT", "TEXTAREA", "A"]);
function D9(e) {
  return I9.has(e.tagName) || e.tabIndex !== -1;
}
const us = new WeakSet();
function sT(e) {
  return (t) => {
    t.key === "Enter" && e(t);
  };
}
function hg(e, t) {
  e.dispatchEvent(new PointerEvent("pointer" + t, { isPrimary: !0, bubbles: !0 }));
}
const O9 = (e, t) => {
  const n = e.currentTarget;
  if (!n) return;
  const r = sT(() => {
    if (us.has(n)) return;
    hg(n, "down");
    const i = sT(() => {
        hg(n, "up");
      }),
      o = () => hg(n, "cancel");
    n.addEventListener("keyup", i, t), n.addEventListener("blur", o, t);
  });
  n.addEventListener("keydown", r, t),
    n.addEventListener("blur", () => n.removeEventListener("keydown", r), t);
};
function aT(e) {
  return pw(e) && !uI();
}
function L9(e, t, n = {}) {
  const [r, i, o] = lI(e, n),
    s = (a) => {
      const u = a.currentTarget;
      if (!aT(a) || us.has(u)) return;
      us.add(u);
      const l = t(a),
        c = (h, v) => {
          window.removeEventListener("pointerup", f),
            window.removeEventListener("pointercancel", d),
            !(!aT(h) || !us.has(u)) &&
              (us.delete(u), typeof l == "function" && l(h, { success: v }));
        },
        f = (h) => {
          c(h, n.useGlobalTarget || cI(u, h.target));
        },
        d = (h) => {
          c(h, !1);
        };
      window.addEventListener("pointerup", f, i), window.addEventListener("pointercancel", d, i);
    };
  return (
    r.forEach((a) => {
      !D9(a) && a.getAttribute("tabindex") === null && (a.tabIndex = 0),
        (n.useGlobalTarget ? window : a).addEventListener("pointerdown", s, i),
        a.addEventListener("focus", (l) => O9(l, i), i);
    }),
    o
  );
}
function F9(e) {
  return e === "x" || e === "y"
    ? Gt[e]
      ? null
      : ((Gt[e] = !0),
        () => {
          Gt[e] = !1;
        })
    : Gt.x || Gt.y
    ? null
    : ((Gt.x = Gt.y = !0),
      () => {
        Gt.x = Gt.y = !1;
      });
}
const fI = new Set(["width", "height", "top", "left", "right", "bottom", ...Po]);
let Tu;
function V9() {
  Tu = void 0;
}
const wn = {
  now: () => (
    Tu === void 0 &&
      wn.set($e.isProcessing || IW.useManualTiming ? $e.timestamp : performance.now()),
    Tu
  ),
  set: (e) => {
    (Tu = e), queueMicrotask(V9);
  },
};
function mw(e, t) {
  e.indexOf(t) === -1 && e.push(t);
}
function gw(e, t) {
  const n = e.indexOf(t);
  n > -1 && e.splice(n, 1);
}
class vw {
  constructor() {
    this.subscriptions = [];
  }
  add(t) {
    return mw(this.subscriptions, t), () => gw(this.subscriptions, t);
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
function dI(e, t) {
  return t ? e * (1e3 / t) : 0;
}
const uT = 30,
  j9 = (e) => !isNaN(parseFloat(e)),
  xs = { current: void 0 };
class q9 {
  constructor(t, n = {}) {
    (this.version = "11.18.2"),
      (this.canTrackVelocity = null),
      (this.events = {}),
      (this.updateAndNotify = (r, i = !0) => {
        const o = wn.now();
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
      (this.updatedAt = wn.now()),
      this.canTrackVelocity === null && t !== void 0 && (this.canTrackVelocity = j9(this.current));
  }
  setPrevFrameValue(t = this.current) {
    (this.prevFrameValue = t), (this.prevUpdatedAt = this.updatedAt);
  }
  onChange(t) {
    return this.on("change", t);
  }
  on(t, n) {
    this.events[t] || (this.events[t] = new vw());
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
    return xs.current && xs.current.push(this), this.current;
  }
  getPrevious() {
    return this.prev;
  }
  getVelocity() {
    const t = wn.now();
    if (!this.canTrackVelocity || this.prevFrameValue === void 0 || t - this.updatedAt > uT)
      return 0;
    const n = Math.min(this.updatedAt - this.prevUpdatedAt, uT);
    return dI(parseFloat(this.current) - parseFloat(this.prevFrameValue), n);
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
function vo(e, t) {
  return new q9(e, t);
}
function $9(e, t, n) {
  e.hasValue(t) ? e.getValue(t).set(n) : e.addValue(t, vo(n));
}
function z9(e, t) {
  const n = yc(e, t);
  let { transitionEnd: r = {}, transition: i = {}, ...o } = n || {};
  o = { ...o, ...r };
  for (const s in o) {
    const a = e9(o[s]);
    $9(e, s, a);
  }
}
function B9(e) {
  return !!(Be(e) && e.add);
}
function Uv(e, t) {
  const n = e.getValue("willChange");
  if (B9(n)) return n.add(t);
}
function hI(e) {
  return e.props[B2];
}
const pI = (e, t, n) => (((1 - 3 * n + 3 * t) * e + (3 * n - 6 * t)) * e + 3 * t) * e,
  U9 = 1e-7,
  H9 = 12;
function G9(e, t, n, r, i) {
  let o,
    s,
    a = 0;
  do (s = t + (n - t) / 2), (o = pI(s, r, i) - e), o > 0 ? (n = s) : (t = s);
  while (Math.abs(o) > U9 && ++a < H9);
  return s;
}
function wa(e, t, n, r) {
  if (e === t && n === r) return Ct;
  const i = (o) => G9(o, 0, 1, e, n);
  return (o) => (o === 0 || o === 1 ? o : pI(i(o), t, r));
}
const mI = (e) => (t) => (t <= 0.5 ? e(2 * t) / 2 : (2 - e(2 * (1 - t))) / 2),
  gI = (e) => (t) => 1 - e(1 - t),
  vI = wa(0.33, 1.53, 0.69, 0.99),
  yw = gI(vI),
  yI = mI(yw),
  wI = (e) => ((e *= 2) < 1 ? 0.5 * yw(e) : 0.5 * (2 - Math.pow(2, -10 * (e - 1)))),
  ww = (e) => 1 - Math.sin(Math.acos(e)),
  xI = gI(ww),
  _I = mI(ww),
  SI = (e) => /^0[^.\s]+$/u.test(e);
function W9(e) {
  return typeof e == "number" ? e === 0 : e !== null ? e === "none" || e === "0" || SI(e) : !0;
}
const _s = (e) => Math.round(e * 1e5) / 1e5,
  xw = /-?(?:\d+(?:\.\d+)?|\.\d+)/gu;
function K9(e) {
  return e == null;
}
const Y9 = /^(?:#[\da-f]{3,8}|(?:rgb|hsl)a?\((?:-?[\d.]+%?[,\s]+){2}-?[\d.]+%?\s*(?:[,/]\s*)?(?:\b\d+(?:\.\d+)?|\.\d+)?%?\))$/iu,
  _w = (e, t) => (n) =>
    !!(
      (typeof n == "string" && Y9.test(n) && n.startsWith(e)) ||
      (t && !K9(n) && Object.prototype.hasOwnProperty.call(n, t))
    ),
  bI = (e, t, n) => (r) => {
    if (typeof r != "string") return r;
    const [i, o, s, a] = r.match(xw);
    return {
      [e]: parseFloat(i),
      [t]: parseFloat(o),
      [n]: parseFloat(s),
      alpha: a !== void 0 ? parseFloat(a) : 1,
    };
  },
  X9 = (e) => Yn(0, 255, e),
  pg = { ...Ro, transform: (e) => Math.round(X9(e)) },
  Xr = {
    test: _w("rgb", "red"),
    parse: bI("red", "green", "blue"),
    transform: ({ red: e, green: t, blue: n, alpha: r = 1 }) =>
      "rgba(" +
      pg.transform(e) +
      ", " +
      pg.transform(t) +
      ", " +
      pg.transform(n) +
      ", " +
      _s(ea.transform(r)) +
      ")",
  };
function Z9(e) {
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
const Hv = { test: _w("#"), parse: Z9, transform: Xr.transform },
  $i = {
    test: _w("hsl", "hue"),
    parse: bI("hue", "saturation", "lightness"),
    transform: ({ hue: e, saturation: t, lightness: n, alpha: r = 1 }) =>
      "hsla(" +
      Math.round(e) +
      ", " +
      yn.transform(_s(t)) +
      ", " +
      yn.transform(_s(n)) +
      ", " +
      _s(ea.transform(r)) +
      ")",
  },
  tt = {
    test: (e) => Xr.test(e) || Hv.test(e) || $i.test(e),
    parse: (e) => (Xr.test(e) ? Xr.parse(e) : $i.test(e) ? $i.parse(e) : Hv.parse(e)),
    transform: (e) =>
      typeof e == "string" ? e : e.hasOwnProperty("red") ? Xr.transform(e) : $i.transform(e),
  },
  Q9 = /(?:#[\da-f]{3,8}|(?:rgb|hsl)a?\((?:-?[\d.]+%?[,\s]+){2}-?[\d.]+%?\s*(?:[,/]\s*)?(?:\b\d+(?:\.\d+)?|\.\d+)?%?\))/giu;
function J9(e) {
  var t, n;
  return (
    isNaN(e) &&
    typeof e == "string" &&
    (((t = e.match(xw)) === null || t === void 0 ? void 0 : t.length) || 0) +
      (((n = e.match(Q9)) === null || n === void 0 ? void 0 : n.length) || 0) >
      0
  );
}
const EI = "number",
  CI = "color",
  e7 = "var",
  t7 = "var(",
  lT = "${}",
  n7 = /var\s*\(\s*--(?:[\w-]+\s*|[\w-]+\s*,(?:\s*[^)(\s]|\s*\((?:[^)(]|\([^)(]*\))*\))+\s*)\)|#[\da-f]{3,8}|(?:rgb|hsl)a?\((?:-?[\d.]+%?[,\s]+){2}-?[\d.]+%?\s*(?:[,/]\s*)?(?:\b\d+(?:\.\d+)?|\.\d+)?%?\)|-?(?:\d+(?:\.\d+)?|\.\d+)/giu;
function ta(e) {
  const t = e.toString(),
    n = [],
    r = { color: [], number: [], var: [] },
    i = [];
  let o = 0;
  const a = t
    .replace(
      n7,
      (u) => (
        tt.test(u)
          ? (r.color.push(o), i.push(CI), n.push(tt.parse(u)))
          : u.startsWith(t7)
          ? (r.var.push(o), i.push(e7), n.push(u))
          : (r.number.push(o), i.push(EI), n.push(parseFloat(u))),
        ++o,
        lT
      )
    )
    .split(lT);
  return { values: n, split: a, indexes: r, types: i };
}
function TI(e) {
  return ta(e).values;
}
function kI(e) {
  const { split: t, types: n } = ta(e),
    r = t.length;
  return (i) => {
    let o = "";
    for (let s = 0; s < r; s++)
      if (((o += t[s]), i[s] !== void 0)) {
        const a = n[s];
        a === EI ? (o += _s(i[s])) : a === CI ? (o += tt.transform(i[s])) : (o += i[s]);
      }
    return o;
  };
}
const r7 = (e) => (typeof e == "number" ? 0 : e);
function i7(e) {
  const t = TI(e);
  return kI(e)(t.map(r7));
}
const Ar = { test: J9, parse: TI, createTransformer: kI, getAnimatableNone: i7 },
  o7 = new Set(["brightness", "contrast", "saturate", "opacity"]);
function s7(e) {
  const [t, n] = e.slice(0, -1).split("(");
  if (t === "drop-shadow") return e;
  const [r] = n.match(xw) || [];
  if (!r) return e;
  const i = n.replace(r, "");
  let o = o7.has(t) ? 1 : 0;
  return r !== n && (o *= 100), t + "(" + o + i + ")";
}
const a7 = /\b([a-z-]*)\(.*?\)/gu,
  Gv = {
    ...Ar,
    getAnimatableNone: (e) => {
      const t = e.match(a7);
      return t ? t.map(s7).join(" ") : e;
    },
  },
  u7 = {
    ...ow,
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
    filter: Gv,
    WebkitFilter: Gv,
  },
  Sw = (e) => u7[e];
function PI(e, t) {
  let n = Sw(e);
  return n !== Gv && (n = Ar), n.getAnimatableNone ? n.getAnimatableNone(t) : void 0;
}
const l7 = new Set(["auto", "none", "0"]);
function c7(e, t, n) {
  let r = 0,
    i;
  for (; r < e.length && !i; ) {
    const o = e[r];
    typeof o == "string" && !l7.has(o) && ta(o).values.length && (i = e[r]), r++;
  }
  if (i && n) for (const o of t) e[o] = PI(n, i);
}
const cT = (e) => e === Ro || e === Z,
  fT = (e, t) => parseFloat(e.split(", ")[t]),
  dT = (e, t) => (n, { transform: r }) => {
    if (r === "none" || !r) return 0;
    const i = r.match(/^matrix3d\((.+)\)$/u);
    if (i) return fT(i[1], t);
    {
      const o = r.match(/^matrix\((.+)\)$/u);
      return o ? fT(o[1], e) : 0;
    }
  },
  f7 = new Set(["x", "y", "z"]),
  d7 = Po.filter((e) => !f7.has(e));
function h7(e) {
  const t = [];
  return (
    d7.forEach((n) => {
      const r = e.getValue(n);
      r !== void 0 && (t.push([n, r.get()]), r.set(n.startsWith("scale") ? 1 : 0));
    }),
    t
  );
}
const yo = {
  width: ({ x: e }, { paddingLeft: t = "0", paddingRight: n = "0" }) =>
    e.max - e.min - parseFloat(t) - parseFloat(n),
  height: ({ y: e }, { paddingTop: t = "0", paddingBottom: n = "0" }) =>
    e.max - e.min - parseFloat(t) - parseFloat(n),
  top: (e, { top: t }) => parseFloat(t),
  left: (e, { left: t }) => parseFloat(t),
  bottom: ({ y: e }, { top: t }) => parseFloat(t) + (e.max - e.min),
  right: ({ x: e }, { left: t }) => parseFloat(t) + (e.max - e.min),
  x: dT(4, 13),
  y: dT(5, 14),
};
yo.translateX = yo.x;
yo.translateY = yo.y;
const ti = new Set();
let Wv = !1,
  Kv = !1;
function RI() {
  if (Kv) {
    const e = Array.from(ti).filter((r) => r.needsMeasurement),
      t = new Set(e.map((r) => r.element)),
      n = new Map();
    t.forEach((r) => {
      const i = h7(r);
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
  (Kv = !1), (Wv = !1), ti.forEach((e) => e.complete()), ti.clear();
}
function AI() {
  ti.forEach((e) => {
    e.readKeyframes(), e.needsMeasurement && (Kv = !0);
  });
}
function p7() {
  AI(), RI();
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
        ? (ti.add(this), Wv || ((Wv = !0), fe.read(AI), fe.resolveKeyframes(RI)))
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
      ti.delete(this);
  }
  cancel() {
    this.isComplete || ((this.isScheduled = !1), ti.delete(this));
  }
  resume() {
    this.isComplete || this.scheduleResolve();
  }
}
const NI = (e) => /^-?(?:\d+(?:\.\d+)?|\.\d+)$/u.test(e),
  m7 = /^var\(--(?:([\w-]+)|([\w-]+), ?([a-zA-Z\d ()%#.,-]+))\)/u;
function g7(e) {
  const t = m7.exec(e);
  if (!t) return [,];
  const [, n, r, i] = t;
  return [`--${n ?? r}`, i];
}
function MI(e, t, n = 1) {
  const [r, i] = g7(e);
  if (!r) return;
  const o = window.getComputedStyle(t).getPropertyValue(r);
  if (o) {
    const s = o.trim();
    return NI(s) ? parseFloat(s) : s;
  }
  return iw(i) ? MI(i, t, n + 1) : i;
}
const II = (e) => (t) => t.test(e),
  v7 = { test: (e) => e === "auto", parse: (e) => e },
  DI = [Ro, Z, yn, sr, s9, o9, v7],
  hT = (e) => DI.find(II(e));
class OI extends bw {
  constructor(t, n, r, i, o) {
    super(t, n, r, i, o, !0);
  }
  readKeyframes() {
    const { unresolvedKeyframes: t, element: n, name: r } = this;
    if (!n || !n.current) return;
    super.readKeyframes();
    for (let u = 0; u < t.length; u++) {
      let l = t[u];
      if (typeof l == "string" && ((l = l.trim()), iw(l))) {
        const c = MI(l, n.current);
        c !== void 0 && (t[u] = c), u === t.length - 1 && (this.finalKeyframe = l);
      }
    }
    if ((this.resolveNoneKeyframes(), !fI.has(r) || t.length !== 2)) return;
    const [i, o] = t,
      s = hT(i),
      a = hT(o);
    if (s !== a)
      if (cT(s) && cT(a))
        for (let u = 0; u < t.length; u++) {
          const l = t[u];
          typeof l == "string" && (t[u] = parseFloat(l));
        }
      else this.needsMeasurement = !0;
  }
  resolveNoneKeyframes() {
    const { unresolvedKeyframes: t, name: n } = this,
      r = [];
    for (let i = 0; i < t.length; i++) W9(t[i]) && r.push(i);
    r.length && c7(t, r, n);
  }
  measureInitialState() {
    const { element: t, unresolvedKeyframes: n, name: r } = this;
    if (!t || !t.current) return;
    r === "height" && (this.suspendedScrollY = window.pageYOffset),
      (this.measuredOrigin = yo[r](t.measureViewportBox(), window.getComputedStyle(t.current))),
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
    (i[s] = yo[r](n.measureViewportBox(), window.getComputedStyle(n.current))),
      a !== null && this.finalKeyframe === void 0 && (this.finalKeyframe = a),
      !((t = this.removedTransforms) === null || t === void 0) &&
        t.length &&
        this.removedTransforms.forEach(([u, l]) => {
          n.getValue(u).set(l);
        }),
      this.resolveNoneKeyframes();
  }
}
const pT = (e, t) =>
  t === "zIndex"
    ? !1
    : !!(
        typeof e == "number" ||
        Array.isArray(e) ||
        (typeof e == "string" && (Ar.test(e) || e === "0") && !e.startsWith("url("))
      );
function y7(e) {
  const t = e[0];
  if (e.length === 1) return !0;
  for (let n = 0; n < e.length; n++) if (e[n] !== t) return !0;
}
function w7(e, t, n, r) {
  const i = e[0];
  if (i === null) return !1;
  if (t === "display" || t === "visibility") return !0;
  const o = e[e.length - 1],
    s = pT(i, t),
    a = pT(o, t);
  return !s || !a ? !1 : y7(e) || ((n === "spring" || dw(n)) && r);
}
const x7 = (e) => e !== null;
function wc(e, { repeat: t, repeatType: n = "loop" }, r) {
  const i = e.filter(x7),
    o = t && n !== "loop" && t % 2 === 1 ? 0 : i.length - 1;
  return !o || r === void 0 ? i[o] : r;
}
const _7 = 40;
class LI {
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
      (this.createdAt = wn.now()),
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
      ? this.resolvedAt - this.createdAt > _7
        ? this.resolvedAt
        : this.createdAt
      : this.createdAt;
  }
  get resolved() {
    return !this._resolved && !this.hasAttemptedResolve && p7(), this._resolved;
  }
  onKeyframesResolved(t, n) {
    (this.resolvedAt = wn.now()), (this.hasAttemptedResolve = !0);
    const {
      name: r,
      type: i,
      velocity: o,
      delay: s,
      onComplete: a,
      onUpdate: u,
      isGenerator: l,
    } = this.options;
    if (!l && !w7(t, r, i, o))
      if (s) this.options.duration = 0;
      else {
        u && u(wc(t, this.options, n)), a && a(), this.resolveFinishedPromise();
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
const xe = (e, t, n) => e + (t - e) * n;
function mg(e, t, n) {
  return (
    n < 0 && (n += 1),
    n > 1 && (n -= 1),
    n < 1 / 6 ? e + (t - e) * 6 * n : n < 1 / 2 ? t : n < 2 / 3 ? e + (t - e) * (2 / 3 - n) * 6 : e
  );
}
function S7({ hue: e, saturation: t, lightness: n, alpha: r }) {
  (e /= 360), (t /= 100), (n /= 100);
  let i = 0,
    o = 0,
    s = 0;
  if (!t) i = o = s = n;
  else {
    const a = n < 0.5 ? n * (1 + t) : n + t - n * t,
      u = 2 * n - a;
    (i = mg(u, a, e + 1 / 3)), (o = mg(u, a, e)), (s = mg(u, a, e - 1 / 3));
  }
  return {
    red: Math.round(i * 255),
    green: Math.round(o * 255),
    blue: Math.round(s * 255),
    alpha: r,
  };
}
function gl(e, t) {
  return (n) => (n > 0 ? t : e);
}
const gg = (e, t, n) => {
    const r = e * e,
      i = n * (t * t - r) + r;
    return i < 0 ? 0 : Math.sqrt(i);
  },
  b7 = [Hv, Xr, $i],
  E7 = (e) => b7.find((t) => t.test(e));
function mT(e) {
  const t = E7(e);
  if (!t) return !1;
  let n = t.parse(e);
  return t === $i && (n = S7(n)), n;
}
const gT = (e, t) => {
    const n = mT(e),
      r = mT(t);
    if (!n || !r) return gl(e, t);
    const i = { ...n };
    return (o) => (
      (i.red = gg(n.red, r.red, o)),
      (i.green = gg(n.green, r.green, o)),
      (i.blue = gg(n.blue, r.blue, o)),
      (i.alpha = xe(n.alpha, r.alpha, o)),
      Xr.transform(i)
    );
  },
  C7 = (e, t) => (n) => t(e(n)),
  xa = (...e) => e.reduce(C7),
  Yv = new Set(["none", "hidden"]);
function T7(e, t) {
  return Yv.has(e) ? (n) => (n <= 0 ? e : t) : (n) => (n >= 1 ? t : e);
}
function k7(e, t) {
  return (n) => xe(e, t, n);
}
function Ew(e) {
  return typeof e == "number"
    ? k7
    : typeof e == "string"
    ? iw(e)
      ? gl
      : tt.test(e)
      ? gT
      : A7
    : Array.isArray(e)
    ? FI
    : typeof e == "object"
    ? tt.test(e)
      ? gT
      : P7
    : gl;
}
function FI(e, t) {
  const n = [...e],
    r = n.length,
    i = e.map((o, s) => Ew(o)(o, t[s]));
  return (o) => {
    for (let s = 0; s < r; s++) n[s] = i[s](o);
    return n;
  };
}
function P7(e, t) {
  const n = { ...e, ...t },
    r = {};
  for (const i in n) e[i] !== void 0 && t[i] !== void 0 && (r[i] = Ew(e[i])(e[i], t[i]));
  return (i) => {
    for (const o in r) n[o] = r[o](i);
    return n;
  };
}
function R7(e, t) {
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
const A7 = (e, t) => {
  const n = Ar.createTransformer(t),
    r = ta(e),
    i = ta(t);
  return r.indexes.var.length === i.indexes.var.length &&
    r.indexes.color.length === i.indexes.color.length &&
    r.indexes.number.length >= i.indexes.number.length
    ? (Yv.has(e) && !i.values.length) || (Yv.has(t) && !r.values.length)
      ? T7(e, t)
      : xa(FI(R7(r, i), i.values), n)
    : gl(e, t);
};
function VI(e, t, n) {
  return typeof e == "number" && typeof t == "number" && typeof n == "number"
    ? xe(e, t, n)
    : Ew(e)(e, t);
}
const N7 = 5;
function jI(e, t, n) {
  const r = Math.max(t - N7, 0);
  return dI(n - e(r), t - r);
}
const Ee = {
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
  vg = 0.001;
function M7({
  duration: e = Ee.duration,
  bounce: t = Ee.bounce,
  velocity: n = Ee.velocity,
  mass: r = Ee.mass,
}) {
  let i,
    o,
    s = 1 - t;
  (s = Yn(Ee.minDamping, Ee.maxDamping, s)),
    (e = Yn(Ee.minDuration, Ee.maxDuration, qn(e))),
    s < 1
      ? ((i = (l) => {
          const c = l * s,
            f = c * e,
            d = c - n,
            h = Xv(l, s),
            v = Math.exp(-f);
          return vg - (d / h) * v;
        }),
        (o = (l) => {
          const f = l * s * e,
            d = f * n + n,
            h = Math.pow(s, 2) * Math.pow(l, 2) * e,
            v = Math.exp(-f),
            p = Xv(Math.pow(l, 2), s);
          return ((-i(l) + vg > 0 ? -1 : 1) * ((d - h) * v)) / p;
        }))
      : ((i = (l) => {
          const c = Math.exp(-l * e),
            f = (l - n) * e + 1;
          return -vg + c * f;
        }),
        (o = (l) => {
          const c = Math.exp(-l * e),
            f = (n - l) * (e * e);
          return c * f;
        }));
  const a = 5 / e,
    u = D7(i, o, a);
  if (((e = jn(e)), isNaN(u))) return { stiffness: Ee.stiffness, damping: Ee.damping, duration: e };
  {
    const l = Math.pow(u, 2) * r;
    return { stiffness: l, damping: s * 2 * Math.sqrt(r * l), duration: e };
  }
}
const I7 = 12;
function D7(e, t, n) {
  let r = n;
  for (let i = 1; i < I7; i++) r = r - e(r) / t(r);
  return r;
}
function Xv(e, t) {
  return e * Math.sqrt(1 - t * t);
}
const O7 = ["duration", "bounce"],
  L7 = ["stiffness", "damping", "mass"];
function vT(e, t) {
  return t.some((n) => e[n] !== void 0);
}
function F7(e) {
  let t = {
    velocity: Ee.velocity,
    stiffness: Ee.stiffness,
    damping: Ee.damping,
    mass: Ee.mass,
    isResolvedFromDuration: !1,
    ...e,
  };
  if (!vT(e, L7) && vT(e, O7))
    if (e.visualDuration) {
      const n = e.visualDuration,
        r = (2 * Math.PI) / (n * 1.2),
        i = r * r,
        o = 2 * Yn(0.05, 1, 1 - (e.bounce || 0)) * Math.sqrt(i);
      t = { ...t, mass: Ee.mass, stiffness: i, damping: o };
    } else {
      const n = M7(e);
      (t = { ...t, ...n, mass: Ee.mass }), (t.isResolvedFromDuration = !0);
    }
  return t;
}
function qI(e = Ee.visualDuration, t = Ee.bounce) {
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
    } = F7({ ...n, velocity: -qn(n.velocity || 0) }),
    v = d || 0,
    p = l / (2 * Math.sqrt(u * c)),
    y = s - o,
    m = qn(Math.sqrt(u / c)),
    g = Math.abs(y) < 5;
  r || (r = g ? Ee.restSpeed.granular : Ee.restSpeed.default),
    i || (i = g ? Ee.restDelta.granular : Ee.restDelta.default);
  let w;
  if (p < 1) {
    const S = Xv(m, p);
    w = (C) => {
      const E = Math.exp(-p * m * C);
      return s - E * (((v + p * m * y) / S) * Math.sin(S * C) + y * Math.cos(S * C));
    };
  } else if (p === 1) w = (S) => s - Math.exp(-m * S) * (y + (v + m * y) * S);
  else {
    const S = m * Math.sqrt(p * p - 1);
    w = (C) => {
      const E = Math.exp(-p * m * C),
        T = Math.min(S * C, 300);
      return s - (E * ((v + p * m * y) * Math.sinh(T) + S * y * Math.cosh(T))) / S;
    };
  }
  const x = {
    calculatedDuration: (h && f) || null,
    next: (S) => {
      const C = w(S);
      if (h) a.done = S >= f;
      else {
        let E = 0;
        p < 1 && (E = S === 0 ? jn(v) : jI(w, S, C));
        const T = Math.abs(E) <= r,
          P = Math.abs(s - C) <= i;
        a.done = T && P;
      }
      return (a.value = a.done ? s : C), a;
    },
    toString: () => {
      const S = Math.min(iI(x), zv),
        C = oI((E) => x.next(S * E).value, S, 30);
      return S + "ms " + C;
    },
  };
  return x;
}
function yT({
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
        N = w(T);
      (d.done = Math.abs(P) <= l), (d.value = d.done ? m : N);
    };
  let S, C;
  const E = (T) => {
    h(d.value) &&
      ((S = T),
      (C = qI({
        keyframes: [d.value, v(d.value)],
        velocity: jI(w, T, d.value),
        damping: i,
        stiffness: o,
        restDelta: l,
        restSpeed: c,
      })));
  };
  return (
    E(0),
    {
      calculatedDuration: null,
      next: (T) => {
        let P = !1;
        return (
          !C && S === void 0 && ((P = !0), x(T), E(T)),
          S !== void 0 && T >= S ? C.next(T - S) : (!P && x(T), d)
        );
      },
    }
  );
}
const V7 = wa(0.42, 0, 1, 1),
  j7 = wa(0, 0, 0.58, 1),
  $I = wa(0.42, 0, 0.58, 1),
  q7 = (e) => Array.isArray(e) && typeof e[0] != "number",
  $7 = {
    linear: Ct,
    easeIn: V7,
    easeInOut: $I,
    easeOut: j7,
    circIn: ww,
    circInOut: _I,
    circOut: xI,
    backIn: yw,
    backInOut: yI,
    backOut: vI,
    anticipate: wI,
  },
  wT = (e) => {
    if (hw(e)) {
      V2(e.length === 4);
      const [t, n, r, i] = e;
      return wa(t, n, r, i);
    } else if (typeof e == "string") return $7[e];
    return e;
  };
function z7(e, t, n) {
  const r = [],
    i = n || VI,
    o = e.length - 1;
  for (let s = 0; s < o; s++) {
    let a = i(e[s], e[s + 1]);
    if (t) {
      const u = Array.isArray(t) ? t[s] || Ct : t;
      a = xa(u, a);
    }
    r.push(a);
  }
  return r;
}
function zI(e, t, { clamp: n = !0, ease: r, mixer: i } = {}) {
  const o = e.length;
  if ((V2(o === t.length), o === 1)) return () => t[0];
  if (o === 2 && t[0] === t[1]) return () => t[1];
  const s = e[0] === e[1];
  e[0] > e[o - 1] && ((e = [...e].reverse()), (t = [...t].reverse()));
  const a = z7(t, r, i),
    u = a.length,
    l = (c) => {
      if (s && c < e[0]) return t[0];
      let f = 0;
      if (u > 1) for (; f < e.length - 2 && !(c < e[f + 1]); f++);
      const d = mo(e[f], e[f + 1], c);
      return a[f](d);
    };
  return n ? (c) => l(Yn(e[0], e[o - 1], c)) : l;
}
function B7(e, t) {
  const n = e[e.length - 1];
  for (let r = 1; r <= t; r++) {
    const i = mo(0, t, r);
    e.push(xe(n, 1, i));
  }
}
function U7(e) {
  const t = [0];
  return B7(t, e.length - 1), t;
}
function H7(e, t) {
  return e.map((n) => n * t);
}
function G7(e, t) {
  return e.map(() => t || $I).splice(0, e.length - 1);
}
function vl({ duration: e = 300, keyframes: t, times: n, ease: r = "easeInOut" }) {
  const i = q7(r) ? r.map(wT) : wT(r),
    o = { done: !1, value: t[0] },
    s = H7(n && n.length === t.length ? n : U7(t), e),
    a = zI(s, t, { ease: Array.isArray(i) ? i : G7(t, i) });
  return { calculatedDuration: e, next: (u) => ((o.value = a(u)), (o.done = u >= e), o) };
}
const W7 = (e) => {
    const t = ({ timestamp: n }) => e(n);
    return {
      start: () => fe.update(t, !0),
      stop: () => Kn(t),
      now: () => ($e.isProcessing ? $e.timestamp : wn.now()),
    };
  },
  K7 = { decay: yT, inertia: yT, tween: vl, keyframes: vl, spring: qI },
  Y7 = (e) => e / 100;
class xc extends LI {
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
      a = dw(n) ? n : K7[n] || vl;
    let u, l;
    a !== vl && typeof t[0] != "number" && ((u = xa(Y7, VI(t[0], t[1]))), (t = [0, 100]));
    const c = a({ ...this.options, keyframes: t });
    o === "mirror" && (l = a({ ...this.options, keyframes: [...t].reverse(), velocity: -s })),
      c.calculatedDuration === null && (c.calculatedDuration = iI(c));
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
        N = T % 1;
      !N && T >= 1 && (N = 1),
        N === 1 && P--,
        (P = Math.min(P, h + 1)),
        !!(P % 2) &&
          (v === "reverse" ? ((N = 1 - N), p && (N -= p / f)) : v === "mirror" && (x = s)),
        (w = Yn(0, 1, N) * f);
    }
    const S = g ? { done: !1, value: u[0] } : x.next(w);
    a && (S.value = a(S.value));
    let { done: C } = S;
    !g && l !== null && (C = this.speed >= 0 ? this.currentTime >= c : this.currentTime <= 0);
    const E =
      this.holdTime === null && (this.state === "finished" || (this.state === "running" && C));
    return (
      E && i !== void 0 && (S.value = wc(u, this.options, i)),
      y && y(S.value),
      E && this.finish(),
      S
    );
  }
  get duration() {
    const { resolved: t } = this;
    return t ? qn(t.calculatedDuration) : 0;
  }
  get time() {
    return qn(this.currentTime);
  }
  set time(t) {
    (t = jn(t)),
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
    (this.playbackSpeed = t), n && (this.time = qn(this.currentTime));
  }
  play() {
    if ((this.resolver.isScheduled || this.resolver.resume(), !this._resolved)) {
      this.pendingPlayState = "running";
      return;
    }
    if (this.isStopped) return;
    const { driver: t = W7, onPlay: n, startTime: r } = this.options;
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
function X7(e) {
  return new xc(e);
}
const Z7 = new Set(["opacity", "clipPath", "filter", "transform"]);
function Q7(
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
  } = {}
) {
  const l = { [t]: n };
  u && (l.offset = u);
  const c = aI(a, i);
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
const J7 = Z0(() => Object.hasOwnProperty.call(Element.prototype, "animate")),
  yl = 10,
  eK = 2e4;
function tK(e) {
  return dw(e.type) || e.type === "spring" || !sI(e.ease);
}
function nK(e, t) {
  const n = new xc({ ...t, keyframes: e, repeat: 0, delay: 0, isGenerator: !0 });
  let r = { done: !1, value: e[0] };
  const i = [];
  let o = 0;
  for (; !r.done && o < eK; ) (r = n.sample(o)), i.push(r.value), (o += yl);
  return { times: void 0, keyframes: i, duration: o - yl, ease: "linear" };
}
const BI = { anticipate: wI, backInOut: yI, circInOut: _I };
function rK(e) {
  return e in BI;
}
class xT extends LI {
  constructor(t) {
    super(t);
    const { name: n, motionValue: r, element: i, keyframes: o } = this.options;
    (this.resolver = new OI(o, (s, a) => this.onKeyframesResolved(s, a), n, r, i)),
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
    if ((typeof o == "string" && ml() && rK(o) && (o = BI[o]), tK(this.options))) {
      const { onComplete: f, onUpdate: d, motionValue: h, element: v, ...p } = this.options,
        y = nK(t, p);
      (t = y.keyframes),
        t.length === 1 && (t[1] = t[0]),
        (r = y.duration),
        (i = y.times),
        (o = y.ease),
        (s = "keyframes");
    }
    const c = Q7(a.owner.current, u, t, { ...this.options, duration: r, times: i, ease: o });
    return (
      (c.startTime = l ?? this.calcStartTime()),
      this.pendingTimeline
        ? (iT(c, this.pendingTimeline), (this.pendingTimeline = void 0))
        : (c.onfinish = () => {
            const { onComplete: f } = this.options;
            a.set(wc(t, this.options, n)), f && f(), this.cancel(), this.resolveFinishedPromise();
          }),
      { animation: c, duration: r, times: i, type: s, ease: o, keyframes: t }
    );
  }
  get duration() {
    const { resolved: t } = this;
    if (!t) return 0;
    const { duration: n } = t;
    return qn(n);
  }
  get time() {
    const { resolved: t } = this;
    if (!t) return 0;
    const { animation: n } = t;
    return qn(n.currentTime || 0);
  }
  set time(t) {
    const { resolved: n } = this;
    if (!n) return;
    const { animation: r } = n;
    r.currentTime = jn(t);
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
      iT(r, t);
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
        v = new xc({
          ...h,
          keyframes: r,
          duration: i,
          type: o,
          ease: s,
          times: a,
          isGenerator: !0,
        }),
        p = jn(this.time);
      l.setWithVelocity(v.sample(p - yl).value, v.sample(p).value, yl);
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
    return J7() && r && Z7.has(r) && !u && !l && !i && o !== "mirror" && s !== 0 && a !== "inertia";
  }
}
const iK = { type: "spring", stiffness: 500, damping: 25, restSpeed: 10 },
  oK = (e) => ({
    type: "spring",
    stiffness: 550,
    damping: e === 0 ? 2 * Math.sqrt(550) : 30,
    restSpeed: 10,
  }),
  sK = { type: "keyframes", duration: 0.8 },
  aK = { type: "keyframes", ease: [0.25, 0.1, 0.35, 1], duration: 0.3 },
  uK = (e, { keyframes: t }) =>
    t.length > 2 ? sK : vi.has(e) ? (e.startsWith("scale") ? oK(t[1]) : iK) : aK;
function lK({
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
const Cw = (e, t, n, r = {}, i, o) => (s) => {
  const a = fw(r, e) || {},
    u = a.delay || r.delay || 0;
  let { elapsed: l = 0 } = r;
  l = l - jn(u);
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
  lK(a) || (c = { ...c, ...uK(e, c) }),
    c.duration && (c.duration = jn(c.duration)),
    c.repeatDelay && (c.repeatDelay = jn(c.repeatDelay)),
    c.from !== void 0 && (c.keyframes[0] = c.from);
  let f = !1;
  if (
    ((c.type === !1 || (c.duration === 0 && !c.repeatDelay)) &&
      ((c.duration = 0), c.delay === 0 && (f = !0)),
    f && !o && t.get() !== void 0)
  ) {
    const d = wc(c.keyframes, a);
    if (d !== void 0)
      return (
        fe.update(() => {
          c.onUpdate(d), c.onComplete();
        }),
        new P9([])
      );
  }
  return !o && xT.supports(c) ? new xT(c) : new xc(c);
};
function cK({ protectedKeys: e, needsAnimating: t }, n) {
  const r = e.hasOwnProperty(n) && t[n] !== !0;
  return (t[n] = !1), r;
}
function UI(e, t, { delay: n = 0, transitionOverride: r, type: i } = {}) {
  var o;
  let { transition: s = e.getDefaultTransition(), transitionEnd: a, ...u } = t;
  r && (s = r);
  const l = [],
    c = i && e.animationState && e.animationState.getState()[i];
  for (const f in u) {
    const d = e.getValue(f, (o = e.latestValues[f]) !== null && o !== void 0 ? o : null),
      h = u[f];
    if (h === void 0 || (c && cK(c, f))) continue;
    const v = { delay: n, ...fw(s || {}, f) };
    let p = !1;
    if (window.MotionHandoffAnimation) {
      const m = hI(e);
      if (m) {
        const g = window.MotionHandoffAnimation(m, f, fe);
        g !== null && ((v.startTime = g), (p = !0));
      }
    }
    Uv(e, f), d.start(Cw(f, d, h, e.shouldReduceMotion && fI.has(f) ? { type: !1 } : v, e, p));
    const y = d.animation;
    y && l.push(y);
  }
  return (
    a &&
      Promise.all(l).then(() => {
        fe.update(() => {
          a && z9(e, a);
        });
      }),
    l
  );
}
function Zv(e, t, n = {}) {
  var r;
  const i = yc(
    e,
    t,
    n.type === "exit"
      ? (r = e.presenceContext) === null || r === void 0
        ? void 0
        : r.custom
      : void 0
  );
  let { transition: o = e.getDefaultTransition() || {} } = i || {};
  n.transitionOverride && (o = n.transitionOverride);
  const s = i ? () => Promise.all(UI(e, i, n)) : () => Promise.resolve(),
    a =
      e.variantChildren && e.variantChildren.size
        ? (l = 0) => {
            const { delayChildren: c = 0, staggerChildren: f, staggerDirection: d } = o;
            return fK(e, t, c + l, f, d, n);
          }
        : () => Promise.resolve(),
    { when: u } = o;
  if (u) {
    const [l, c] = u === "beforeChildren" ? [s, a] : [a, s];
    return l().then(() => c());
  } else return Promise.all([s(), a(n.delay)]);
}
function fK(e, t, n = 0, r = 0, i = 1, o) {
  const s = [],
    a = (e.variantChildren.size - 1) * r,
    u = i === 1 ? (l = 0) => l * r : (l = 0) => a - l * r;
  return (
    Array.from(e.variantChildren)
      .sort(dK)
      .forEach((l, c) => {
        l.notify("AnimationStart", t),
          s.push(Zv(l, t, { ...o, delay: n + u(c) }).then(() => l.notify("AnimationComplete", t)));
      }),
    Promise.all(s)
  );
}
function dK(e, t) {
  return e.sortNodePosition(t);
}
function hK(e, t, n = {}) {
  e.notify("AnimationStart", t);
  let r;
  if (Array.isArray(t)) {
    const i = t.map((o) => Zv(e, o, n));
    r = Promise.all(i);
  } else if (typeof t == "string") r = Zv(e, t, n);
  else {
    const i = typeof t == "function" ? yc(e, t, n.custom) : t;
    r = Promise.all(UI(e, i, n));
  }
  return r.then(() => {
    e.notify("AnimationComplete", t);
  });
}
const pK = J0.length;
function HI(e) {
  if (!e) return;
  if (!e.isControllingVariants) {
    const n = e.parent ? HI(e.parent) || {} : {};
    return e.props.initial !== void 0 && (n.initial = e.props.initial), n;
  }
  const t = {};
  for (let n = 0; n < pK; n++) {
    const r = J0[n],
      i = e.props[r];
    (Js(i) || i === !1) && (t[r] = i);
  }
  return t;
}
const mK = [...Q0].reverse(),
  gK = Q0.length;
function vK(e) {
  return (t) => Promise.all(t.map(({ animation: n, options: r }) => hK(e, n, r)));
}
function yK(e) {
  let t = vK(e),
    n = _T(),
    r = !0;
  const i = (u) => (l, c) => {
    var f;
    const d = yc(
      e,
      c,
      u === "exit" ? ((f = e.presenceContext) === null || f === void 0 ? void 0 : f.custom) : void 0
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
      c = HI(e.parent) || {},
      f = [],
      d = new Set();
    let h = {},
      v = 1 / 0;
    for (let y = 0; y < gK; y++) {
      const m = mK[y],
        g = n[m],
        w = l[m] !== void 0 ? l[m] : c[m],
        x = Js(w),
        S = m === u ? g.isActive : null;
      S === !1 && (v = y);
      let C = w === c[m] && w !== l[m] && x;
      if (
        (C && r && e.manuallyAnimateOnMount && (C = !1),
        (g.protectedKeys = { ...h }),
        (!g.isActive && S === null) || (!w && !g.prevProp) || gc(w) || typeof w == "boolean")
      )
        continue;
      const E = wK(g.prevProp, w);
      let T = E || (m === u && g.isActive && !C && x) || (y > v && x),
        P = !1;
      const N = Array.isArray(w) ? w : [w];
      let I = N.reduce(i(m), {});
      S === !1 && (I = {});
      const { prevResolvedValues: V = {} } = g,
        q = { ...V, ...I },
        b = (F) => {
          (T = !0), d.has(F) && ((P = !0), d.delete(F)), (g.needsAnimating[F] = !0);
          const A = e.getValue(F);
          A && (A.liveStyle = !1);
        };
      for (const F in q) {
        const A = I[F],
          k = V[F];
        if (h.hasOwnProperty(F)) continue;
        let D = !1;
        $v(A) && $v(k) ? (D = !rI(A, k)) : (D = A !== k),
          D
            ? A != null
              ? b(F)
              : d.add(F)
            : A !== void 0 && d.has(F)
            ? b(F)
            : (g.protectedKeys[F] = !0);
      }
      (g.prevProp = w),
        (g.prevResolvedValues = I),
        g.isActive && (h = { ...h, ...I }),
        r && e.blockInitialAnimation && (T = !1),
        T && (!(C && E) || P) && f.push(...N.map((F) => ({ animation: F, options: { type: m } })));
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
      (n = _T()), (r = !0);
    },
  };
}
function wK(e, t) {
  return typeof t == "string" ? t !== e : Array.isArray(t) ? !rI(t, e) : !1;
}
function Vr(e = !1) {
  return { isActive: e, protectedKeys: {}, needsAnimating: {}, prevResolvedValues: {} };
}
function _T() {
  return {
    animate: Vr(!0),
    whileInView: Vr(),
    whileHover: Vr(),
    whileTap: Vr(),
    whileDrag: Vr(),
    whileFocus: Vr(),
    exit: Vr(),
  };
}
class Or {
  constructor(t) {
    (this.isMounted = !1), (this.node = t);
  }
  update() {}
}
class xK extends Or {
  constructor(t) {
    super(t), t.animationState || (t.animationState = yK(t));
  }
  updateAnimationControlsSubscription() {
    const { animate: t } = this.node.getProps();
    gc(t) && (this.unmountControls = t.subscribe(this.node));
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
let _K = 0;
class SK extends Or {
  constructor() {
    super(...arguments), (this.id = _K++);
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
const bK = { animation: { Feature: xK }, exit: { Feature: SK } };
function na(e, t, n, r = { passive: !0 }) {
  return e.addEventListener(t, n, r), () => e.removeEventListener(t, n);
}
function _a(e) {
  return { point: { x: e.pageX, y: e.pageY } };
}
const EK = (e) => (t) => pw(t) && e(t, _a(t));
function Ss(e, t, n, r) {
  return na(e, t, EK(n), r);
}
const ST = (e, t) => Math.abs(e - t);
function CK(e, t) {
  const n = ST(e.x, t.x),
    r = ST(e.y, t.y);
  return Math.sqrt(n ** 2 + r ** 2);
}
class GI {
  constructor(t, n, { transformPagePoint: r, contextWindow: i, dragSnapToOrigin: o = !1 } = {}) {
    if (
      ((this.startEvent = null),
      (this.lastMoveEvent = null),
      (this.lastMoveEventInfo = null),
      (this.handlers = {}),
      (this.contextWindow = window),
      (this.updatePoint = () => {
        if (!(this.lastMoveEvent && this.lastMoveEventInfo)) return;
        const f = wg(this.lastMoveEventInfo, this.history),
          d = this.startEvent !== null,
          h = CK(f.offset, { x: 0, y: 0 }) >= 3;
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
          (this.lastMoveEventInfo = yg(d, this.transformPagePoint)),
          fe.update(this.updatePoint, !0);
      }),
      (this.handlePointerUp = (f, d) => {
        this.end();
        const { onEnd: h, onSessionEnd: v, resumeAnimation: p } = this.handlers;
        if ((this.dragSnapToOrigin && p && p(), !(this.lastMoveEvent && this.lastMoveEventInfo)))
          return;
        const y = wg(
          f.type === "pointercancel" ? this.lastMoveEventInfo : yg(d, this.transformPagePoint),
          this.history
        );
        this.startEvent && h && h(f, y), v && v(f, y);
      }),
      !pw(t))
    )
      return;
    (this.dragSnapToOrigin = o),
      (this.handlers = n),
      (this.transformPagePoint = r),
      (this.contextWindow = i || window);
    const s = _a(t),
      a = yg(s, this.transformPagePoint),
      { point: u } = a,
      { timestamp: l } = $e;
    this.history = [{ ...u, timestamp: l }];
    const { onSessionStart: c } = n;
    c && c(t, wg(a, this.history)),
      (this.removeListeners = xa(
        Ss(this.contextWindow, "pointermove", this.handlePointerMove),
        Ss(this.contextWindow, "pointerup", this.handlePointerUp),
        Ss(this.contextWindow, "pointercancel", this.handlePointerUp)
      ));
  }
  updateHandlers(t) {
    this.handlers = t;
  }
  end() {
    this.removeListeners && this.removeListeners(), Kn(this.updatePoint);
  }
}
function yg(e, t) {
  return t ? { point: t(e.point) } : e;
}
function bT(e, t) {
  return { x: e.x - t.x, y: e.y - t.y };
}
function wg({ point: e }, t) {
  return { point: e, delta: bT(e, WI(t)), offset: bT(e, TK(t)), velocity: kK(t, 0.1) };
}
function TK(e) {
  return e[0];
}
function WI(e) {
  return e[e.length - 1];
}
function kK(e, t) {
  if (e.length < 2) return { x: 0, y: 0 };
  let n = e.length - 1,
    r = null;
  const i = WI(e);
  for (; n >= 0 && ((r = e[n]), !(i.timestamp - r.timestamp > jn(t))); ) n--;
  if (!r) return { x: 0, y: 0 };
  const o = qn(i.timestamp - r.timestamp);
  if (o === 0) return { x: 0, y: 0 };
  const s = { x: (i.x - r.x) / o, y: (i.y - r.y) / o };
  return s.x === 1 / 0 && (s.x = 0), s.y === 1 / 0 && (s.y = 0), s;
}
const KI = 1e-4,
  PK = 1 - KI,
  RK = 1 + KI,
  YI = 0.01,
  AK = 0 - YI,
  NK = 0 + YI;
function Pt(e) {
  return e.max - e.min;
}
function MK(e, t, n) {
  return Math.abs(e - t) <= n;
}
function ET(e, t, n, r = 0.5) {
  (e.origin = r),
    (e.originPoint = xe(t.min, t.max, e.origin)),
    (e.scale = Pt(n) / Pt(t)),
    (e.translate = xe(n.min, n.max, e.origin) - e.originPoint),
    ((e.scale >= PK && e.scale <= RK) || isNaN(e.scale)) && (e.scale = 1),
    ((e.translate >= AK && e.translate <= NK) || isNaN(e.translate)) && (e.translate = 0);
}
function bs(e, t, n, r) {
  ET(e.x, t.x, n.x, r ? r.originX : void 0), ET(e.y, t.y, n.y, r ? r.originY : void 0);
}
function CT(e, t, n) {
  (e.min = n.min + t.min), (e.max = e.min + Pt(t));
}
function IK(e, t, n) {
  CT(e.x, t.x, n.x), CT(e.y, t.y, n.y);
}
function TT(e, t, n) {
  (e.min = t.min - n.min), (e.max = e.min + Pt(t));
}
function Es(e, t, n) {
  TT(e.x, t.x, n.x), TT(e.y, t.y, n.y);
}
function DK(e, { min: t, max: n }, r) {
  return (
    t !== void 0 && e < t
      ? (e = r ? xe(t, e, r.min) : Math.max(e, t))
      : n !== void 0 && e > n && (e = r ? xe(n, e, r.max) : Math.min(e, n)),
    e
  );
}
function kT(e, t, n) {
  return {
    min: t !== void 0 ? e.min + t : void 0,
    max: n !== void 0 ? e.max + n - (e.max - e.min) : void 0,
  };
}
function OK(e, { top: t, left: n, bottom: r, right: i }) {
  return { x: kT(e.x, n, i), y: kT(e.y, t, r) };
}
function PT(e, t) {
  let n = t.min - e.min,
    r = t.max - e.max;
  return t.max - t.min < e.max - e.min && ([n, r] = [r, n]), { min: n, max: r };
}
function LK(e, t) {
  return { x: PT(e.x, t.x), y: PT(e.y, t.y) };
}
function FK(e, t) {
  let n = 0.5;
  const r = Pt(e),
    i = Pt(t);
  return (
    i > r ? (n = mo(t.min, t.max - r, e.min)) : r > i && (n = mo(e.min, e.max - i, t.min)),
    Yn(0, 1, n)
  );
}
function VK(e, t) {
  const n = {};
  return (
    t.min !== void 0 && (n.min = t.min - e.min), t.max !== void 0 && (n.max = t.max - e.min), n
  );
}
const Qv = 0.35;
function jK(e = Qv) {
  return (
    e === !1 ? (e = 0) : e === !0 && (e = Qv),
    { x: RT(e, "left", "right"), y: RT(e, "top", "bottom") }
  );
}
function RT(e, t, n) {
  return { min: AT(e, t), max: AT(e, n) };
}
function AT(e, t) {
  return typeof e == "number" ? e : e[t] || 0;
}
const NT = () => ({ translate: 0, scale: 1, origin: 0, originPoint: 0 }),
  zi = () => ({ x: NT(), y: NT() }),
  MT = () => ({ min: 0, max: 0 }),
  Ae = () => ({ x: MT(), y: MT() });
function Mt(e) {
  return [e("x"), e("y")];
}
function XI({ top: e, left: t, right: n, bottom: r }) {
  return { x: { min: t, max: n }, y: { min: e, max: r } };
}
function qK({ x: e, y: t }) {
  return { top: t.min, right: e.max, bottom: t.max, left: e.min };
}
function $K(e, t) {
  if (!t) return e;
  const n = t({ x: e.left, y: e.top }),
    r = t({ x: e.right, y: e.bottom });
  return { top: n.y, left: n.x, bottom: r.y, right: r.x };
}
function xg(e) {
  return e === void 0 || e === 1;
}
function Jv({ scale: e, scaleX: t, scaleY: n }) {
  return !xg(e) || !xg(t) || !xg(n);
}
function zr(e) {
  return Jv(e) || ZI(e) || e.z || e.rotate || e.rotateX || e.rotateY || e.skewX || e.skewY;
}
function ZI(e) {
  return IT(e.x) || IT(e.y);
}
function IT(e) {
  return e && e !== "0%";
}
function wl(e, t, n) {
  const r = e - n,
    i = t * r;
  return n + i;
}
function DT(e, t, n, r, i) {
  return i !== void 0 && (e = wl(e, i, r)), wl(e, n, r) + t;
}
function ey(e, t = 0, n = 1, r, i) {
  (e.min = DT(e.min, t, n, r, i)), (e.max = DT(e.max, t, n, r, i));
}
function QI(e, { x: t, y: n }) {
  ey(e.x, t.translate, t.scale, t.originPoint), ey(e.y, n.translate, n.scale, n.originPoint);
}
const OT = 0.999999999999,
  LT = 1.0000000000001;
function zK(e, t, n, r = !1) {
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
        Ui(e, { x: -o.scroll.offset.x, y: -o.scroll.offset.y }),
      s && ((t.x *= s.x.scale), (t.y *= s.y.scale), QI(e, s)),
      r && zr(o.latestValues) && Ui(e, o.latestValues));
  }
  t.x < LT && t.x > OT && (t.x = 1), t.y < LT && t.y > OT && (t.y = 1);
}
function Bi(e, t) {
  (e.min = e.min + t), (e.max = e.max + t);
}
function FT(e, t, n, r, i = 0.5) {
  const o = xe(e.min, e.max, i);
  ey(e, t, n, o, r);
}
function Ui(e, t) {
  FT(e.x, t.x, t.scaleX, t.scale, t.originX), FT(e.y, t.y, t.scaleY, t.scale, t.originY);
}
function JI(e, t) {
  return XI($K(e.getBoundingClientRect(), t));
}
function BK(e, t, n) {
  const r = JI(e, n),
    { scroll: i } = t;
  return i && (Bi(r.x, i.offset.x), Bi(r.y, i.offset.y)), r;
}
const eD = ({ current: e }) => (e ? e.ownerDocument.defaultView : null),
  UK = new WeakMap();
class HK {
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
        f ? this.pauseAnimation() : this.stopAnimation(), n && this.snapToCursor(_a(c).point);
      },
      o = (c, f) => {
        const { drag: d, dragPropagation: h, onDragStart: v } = this.getProps();
        if (
          d &&
          !h &&
          (this.openDragLock && this.openDragLock(),
          (this.openDragLock = F9(d)),
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
            if (yn.test(m)) {
              const { projection: g } = this.visualElement;
              if (g && g.layout) {
                const w = g.layout.layoutBox[y];
                w && (m = Pt(w) * (parseFloat(m) / 100));
              }
            }
            this.originPoint[y] = m;
          }),
          v && fe.postRender(() => v(c, f)),
          Uv(this.visualElement, "transform");
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
          (this.currentDirection = GK(y)),
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
    this.panSession = new GI(
      t,
      { onSessionStart: i, onStart: o, onMove: s, onSessionEnd: a, resumeAnimation: u },
      {
        transformPagePoint: this.visualElement.getTransformPagePoint(),
        dragSnapToOrigin: l,
        contextWindow: eD(this.visualElement),
      }
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
    if (!r || !iu(t, i, this.currentDirection)) return;
    const o = this.getAxisMotionValue(t);
    let s = this.originPoint[t] + r[t];
    this.constraints && this.constraints[t] && (s = DK(s, this.constraints[t], this.elastic[t])),
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
    n && qi(n)
      ? this.constraints || (this.constraints = this.resolveRefConstraints())
      : n && i
      ? (this.constraints = OK(i.layoutBox, n))
      : (this.constraints = !1),
      (this.elastic = jK(r)),
      o !== this.constraints &&
        i &&
        this.constraints &&
        !this.hasMutatedConstraints &&
        Mt((s) => {
          this.constraints !== !1 &&
            this.getAxisMotionValue(s) &&
            (this.constraints[s] = VK(i.layoutBox[s], this.constraints[s]));
        });
  }
  resolveRefConstraints() {
    const { dragConstraints: t, onMeasureDragConstraints: n } = this.getProps();
    if (!t || !qi(t)) return !1;
    const r = t.current,
      { projection: i } = this.visualElement;
    if (!i || !i.layout) return !1;
    const o = BK(r, i.root, this.visualElement.getTransformPagePoint());
    let s = LK(i.layout.layoutBox, o);
    if (n) {
      const a = n(qK(s));
      (this.hasMutatedConstraints = !!a), a && (s = XI(a));
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
        if (!iu(c, n, this.currentDirection)) return;
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
    return Uv(this.visualElement, t), r.start(Cw(t, r, 0, n, this.visualElement, !1));
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
      if (!iu(n, r, this.currentDirection)) return;
      const { projection: i } = this.visualElement,
        o = this.getAxisMotionValue(n);
      if (i && i.layout) {
        const { min: s, max: a } = i.layout.layoutBox[n];
        o.set(t[n] - xe(s, a, 0.5));
      }
    });
  }
  scalePositionWithinConstraints() {
    if (!this.visualElement.current) return;
    const { drag: t, dragConstraints: n } = this.getProps(),
      { projection: r } = this.visualElement;
    if (!qi(n) || !r || !this.constraints) return;
    this.stopAnimation();
    const i = { x: 0, y: 0 };
    Mt((s) => {
      const a = this.getAxisMotionValue(s);
      if (a && this.constraints !== !1) {
        const u = a.get();
        i[s] = FK({ min: u, max: u }, this.constraints[s]);
      }
    });
    const { transformTemplate: o } = this.visualElement.getProps();
    (this.visualElement.current.style.transform = o ? o({}, "") : "none"),
      r.root && r.root.updateScroll(),
      r.updateLayout(),
      this.resolveConstraints(),
      Mt((s) => {
        if (!iu(s, t, null)) return;
        const a = this.getAxisMotionValue(s),
          { min: u, max: l } = this.constraints[s];
        a.set(xe(u, l, i[s]));
      });
  }
  addListeners() {
    if (!this.visualElement.current) return;
    UK.set(this.visualElement, this);
    const t = this.visualElement.current,
      n = Ss(t, "pointerdown", (u) => {
        const { drag: l, dragListener: c = !0 } = this.getProps();
        l && c && this.start(u);
      }),
      r = () => {
        const { dragConstraints: u } = this.getProps();
        qi(u) && u.current && (this.constraints = this.resolveRefConstraints());
      },
      { projection: i } = this.visualElement,
      o = i.addEventListener("measure", r);
    i && !i.layout && (i.root && i.root.updateScroll(), i.updateLayout()), fe.read(r);
    const s = na(window, "resize", () => this.scalePositionWithinConstraints()),
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
        dragElastic: s = Qv,
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
function iu(e, t, n) {
  return (t === !0 || t === e) && (n === null || n === e);
}
function GK(e, t = 10) {
  let n = null;
  return Math.abs(e.y) > t ? (n = "y") : Math.abs(e.x) > t && (n = "x"), n;
}
class WK extends Or {
  constructor(t) {
    super(t),
      (this.removeGroupControls = Ct),
      (this.removeListeners = Ct),
      (this.controls = new HK(t));
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
const VT = (e) => (t, n) => {
  e && fe.postRender(() => e(t, n));
};
class KK extends Or {
  constructor() {
    super(...arguments), (this.removePointerDownListener = Ct);
  }
  onPointerDown(t) {
    this.session = new GI(t, this.createPanHandlers(), {
      transformPagePoint: this.node.getTransformPagePoint(),
      contextWindow: eD(this.node),
    });
  }
  createPanHandlers() {
    const { onPanSessionStart: t, onPanStart: n, onPan: r, onPanEnd: i } = this.node.getProps();
    return {
      onSessionStart: VT(t),
      onStart: VT(n),
      onMove: r,
      onEnd: (o, s) => {
        delete this.session, i && fe.postRender(() => i(o, s));
      },
    };
  }
  mount() {
    this.removePointerDownListener = Ss(this.node.current, "pointerdown", (t) =>
      this.onPointerDown(t)
    );
  }
  update() {
    this.session && this.session.updateHandlers(this.createPanHandlers());
  }
  unmount() {
    this.removePointerDownListener(), this.session && this.session.end();
  }
}
const ku = { hasAnimatedSinceResize: !0, hasEverUpdated: !1 };
function jT(e, t) {
  return t.max === t.min ? 0 : (e / (t.max - t.min)) * 100;
}
const Wo = {
    correct: (e, t) => {
      if (!t.target) return e;
      if (typeof e == "string")
        if (Z.test(e)) e = parseFloat(e);
        else return e;
      const n = jT(e, t.target.x),
        r = jT(e, t.target.y);
      return `${n}% ${r}%`;
    },
  },
  YK = {
    correct: (e, { treeScale: t, projectionDelta: n }) => {
      const r = e,
        i = Ar.parse(e);
      if (i.length > 5) return r;
      const o = Ar.createTransformer(e),
        s = typeof i[0] != "number" ? 1 : 0,
        a = n.x.scale * t.x,
        u = n.y.scale * t.y;
      (i[0 + s] /= a), (i[1 + s] /= u);
      const l = xe(a, u, 0.5);
      return (
        typeof i[2 + s] == "number" && (i[2 + s] /= l),
        typeof i[3 + s] == "number" && (i[3 + s] /= l),
        o(i)
      );
    },
  };
class XK extends _.Component {
  componentDidMount() {
    const { visualElement: t, layoutGroup: n, switchLayoutGroup: r, layoutId: i } = this.props,
      { projection: o } = t;
    g9(ZK),
      o &&
        (n.group && n.group.add(o),
        r && r.register && i && r.register(o),
        o.root.didUpdate(),
        o.addEventListener("animationComplete", () => {
          this.safeToRemove();
        }),
        o.setOptions({ ...o.options, onExitComplete: () => this.safeToRemove() })),
      (ku.hasEverUpdated = !0);
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
      tw.postRender(() => {
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
function tD(e) {
  const [t, n] = MW(),
    r = _.useContext(F2);
  return M.jsx(XK, {
    ...e,
    layoutGroup: r,
    switchLayoutGroup: _.useContext(U2),
    isPresent: t,
    safeToRemove: n,
  });
}
const ZK = {
  borderRadius: {
    ...Wo,
    applyTo: [
      "borderTopLeftRadius",
      "borderTopRightRadius",
      "borderBottomLeftRadius",
      "borderBottomRightRadius",
    ],
  },
  borderTopLeftRadius: Wo,
  borderTopRightRadius: Wo,
  borderBottomLeftRadius: Wo,
  borderBottomRightRadius: Wo,
  boxShadow: YK,
};
function QK(e, t, n) {
  const r = Be(e) ? e : vo(e);
  return r.start(Cw("", r, t, n)), r.animation;
}
function JK(e) {
  return e instanceof SVGElement && e.tagName !== "svg";
}
const eY = (e, t) => e.depth - t.depth;
class tY {
  constructor() {
    (this.children = []), (this.isDirty = !1);
  }
  add(t) {
    mw(this.children, t), (this.isDirty = !0);
  }
  remove(t) {
    gw(this.children, t), (this.isDirty = !0);
  }
  forEach(t) {
    this.isDirty && this.children.sort(eY), (this.isDirty = !1), this.children.forEach(t);
  }
}
function nY(e, t) {
  const n = wn.now(),
    r = ({ timestamp: i }) => {
      const o = i - n;
      o >= t && (Kn(r), e(o - t));
    };
  return fe.read(r, !0), () => Kn(r);
}
const nD = ["TopLeft", "TopRight", "BottomLeft", "BottomRight"],
  rY = nD.length,
  qT = (e) => (typeof e == "string" ? parseFloat(e) : e),
  $T = (e) => typeof e == "number" || Z.test(e);
function iY(e, t, n, r, i, o) {
  i
    ? ((e.opacity = xe(0, n.opacity !== void 0 ? n.opacity : 1, oY(r))),
      (e.opacityExit = xe(t.opacity !== void 0 ? t.opacity : 1, 0, sY(r))))
    : o &&
      (e.opacity = xe(
        t.opacity !== void 0 ? t.opacity : 1,
        n.opacity !== void 0 ? n.opacity : 1,
        r
      ));
  for (let s = 0; s < rY; s++) {
    const a = `border${nD[s]}Radius`;
    let u = zT(t, a),
      l = zT(n, a);
    if (u === void 0 && l === void 0) continue;
    u || (u = 0),
      l || (l = 0),
      u === 0 || l === 0 || $T(u) === $T(l)
        ? ((e[a] = Math.max(xe(qT(u), qT(l), r), 0)), (yn.test(l) || yn.test(u)) && (e[a] += "%"))
        : (e[a] = l);
  }
  (t.rotate || n.rotate) && (e.rotate = xe(t.rotate || 0, n.rotate || 0, r));
}
function zT(e, t) {
  return e[t] !== void 0 ? e[t] : e.borderRadius;
}
const oY = rD(0, 0.5, xI),
  sY = rD(0.5, 0.95, Ct);
function rD(e, t, n) {
  return (r) => (r < e ? 0 : r > t ? 1 : n(mo(e, t, r)));
}
function BT(e, t) {
  (e.min = t.min), (e.max = t.max);
}
function Nt(e, t) {
  BT(e.x, t.x), BT(e.y, t.y);
}
function UT(e, t) {
  (e.translate = t.translate),
    (e.scale = t.scale),
    (e.originPoint = t.originPoint),
    (e.origin = t.origin);
}
function HT(e, t, n, r, i) {
  return (e -= t), (e = wl(e, 1 / n, r)), i !== void 0 && (e = wl(e, 1 / i, r)), e;
}
function aY(e, t = 0, n = 1, r = 0.5, i, o = e, s = e) {
  if (
    (yn.test(t) && ((t = parseFloat(t)), (t = xe(s.min, s.max, t / 100) - s.min)),
    typeof t != "number")
  )
    return;
  let a = xe(o.min, o.max, r);
  e === o && (a -= t), (e.min = HT(e.min, t, n, a, i)), (e.max = HT(e.max, t, n, a, i));
}
function GT(e, t, [n, r, i], o, s) {
  aY(e, t[n], t[r], t[i], t.scale, o, s);
}
const uY = ["x", "scaleX", "originX"],
  lY = ["y", "scaleY", "originY"];
function WT(e, t, n, r) {
  GT(e.x, t, uY, n ? n.x : void 0, r ? r.x : void 0),
    GT(e.y, t, lY, n ? n.y : void 0, r ? r.y : void 0);
}
function KT(e) {
  return e.translate === 0 && e.scale === 1;
}
function iD(e) {
  return KT(e.x) && KT(e.y);
}
function YT(e, t) {
  return e.min === t.min && e.max === t.max;
}
function cY(e, t) {
  return YT(e.x, t.x) && YT(e.y, t.y);
}
function XT(e, t) {
  return Math.round(e.min) === Math.round(t.min) && Math.round(e.max) === Math.round(t.max);
}
function oD(e, t) {
  return XT(e.x, t.x) && XT(e.y, t.y);
}
function ZT(e) {
  return Pt(e.x) / Pt(e.y);
}
function QT(e, t) {
  return e.translate === t.translate && e.scale === t.scale && e.originPoint === t.originPoint;
}
class fY {
  constructor() {
    this.members = [];
  }
  add(t) {
    mw(this.members, t), t.scheduleRender();
  }
  remove(t) {
    if ((gw(this.members, t), t === this.prevLead && (this.prevLead = void 0), t === this.lead)) {
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
function dY(e, t, n) {
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
const Br = {
    type: "projectionFrame",
    totalNodes: 0,
    resolvedTargetDeltas: 0,
    recalculatedProjection: 0,
  },
  ls = typeof window < "u" && window.MotionDebug !== void 0,
  _g = ["", "X", "Y", "Z"],
  hY = { visibility: "hidden" },
  JT = 1e3;
let pY = 0;
function Sg(e, t, n, r) {
  const { latestValues: i } = t;
  i[e] && ((n[e] = i[e]), t.setStaticValue(e, 0), r && (r[e] = 0));
}
function sD(e) {
  if (((e.hasCheckedOptimisedAppear = !0), e.root === e)) return;
  const { visualElement: t } = e.options;
  if (!t) return;
  const n = hI(t);
  if (window.MotionHasOptimisedAnimation(n, "transform")) {
    const { layout: i, layoutId: o } = e.options;
    window.MotionCancelOptimisedAnimation(n, "transform", fe, !(i || o));
  }
  const { parent: r } = e;
  r && !r.hasCheckedOptimisedAppear && sD(r);
}
function aD({
  attachResizeListener: e,
  defaultParent: t,
  measureScroll: n,
  checkIsScrollRoot: r,
  resetTransform: i,
}) {
  return class {
    constructor(s = {}, a = t == null ? void 0 : t()) {
      (this.id = pY++),
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
            ls && (Br.totalNodes = Br.resolvedTargetDeltas = Br.recalculatedProjection = 0),
            this.nodes.forEach(vY),
            this.nodes.forEach(SY),
            this.nodes.forEach(bY),
            this.nodes.forEach(yY),
            ls && window.MotionDebug.record(Br);
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
      this.root === this && (this.nodes = new tY());
    }
    addEventListener(s, a) {
      return (
        this.eventHandlers.has(s) || this.eventHandlers.set(s, new vw()),
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
      (this.isSVG = JK(s)), (this.instance = s);
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
            (f = nY(d, 250)),
            ku.hasAnimatedSinceResize && ((ku.hasAnimatedSinceResize = !1), this.nodes.forEach(tk));
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
              const p = this.options.transition || c.getDefaultTransition() || PY,
                { onLayoutAnimationStart: y, onLayoutAnimationComplete: m } = c.getProps(),
                g = !this.targetLayout || !oD(this.targetLayout, v) || h,
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
                const x = { ...fw(p, "layout"), onPlay: y, onComplete: m };
                (c.shouldReduceMotion || this.options.layoutRoot) && ((x.delay = 0), (x.type = !1)),
                  this.startAnimation(x);
              } else
                d || tk(this),
                  this.isLead() && this.options.onExitComplete && this.options.onExitComplete();
              this.targetLayout = v;
            }
          );
    }
    unmount() {
      this.options.layoutId && this.willUpdate(), this.root.nodes.remove(this);
      const s = this.getStack();
      s && s.remove(this),
        this.parent && this.parent.children.delete(this),
        (this.instance = void 0),
        Kn(this.updateProjection);
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
        ((this.isUpdating = !0), this.nodes && this.nodes.forEach(EY), this.animationId++);
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
        (window.MotionCancelOptimisedAnimation && !this.hasCheckedOptimisedAppear && sD(this),
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
        this.unblockUpdate(), this.clearAllSnapshots(), this.nodes.forEach(ek);
        return;
      }
      this.isUpdating || this.nodes.forEach(xY),
        (this.isUpdating = !1),
        this.nodes.forEach(_Y),
        this.nodes.forEach(mY),
        this.nodes.forEach(gY),
        this.clearAllSnapshots();
      const a = wn.now();
      ($e.delta = Yn(0, 1e3 / 60, a - $e.timestamp)),
        ($e.timestamp = a),
        ($e.isProcessing = !0),
        dg.update.process($e),
        dg.preRender.process($e),
        dg.render.process($e),
        ($e.isProcessing = !1);
    }
    didUpdate() {
      this.updateScheduled || ((this.updateScheduled = !0), tw.read(this.scheduleUpdate));
    }
    clearAllSnapshots() {
      this.nodes.forEach(wY), this.sharedNodes.forEach(CY);
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
        a = this.projectionDelta && !iD(this.projectionDelta),
        u = this.getTransformTemplate(),
        l = u ? u(this.latestValues, "") : void 0,
        c = l !== this.prevTransformTemplateValue;
      s &&
        (a || zr(this.latestValues) || c) &&
        (i(this.instance, l), (this.shouldResetTransform = !1), this.scheduleRender());
    }
    measure(s = !0) {
      const a = this.measurePageBox();
      let u = this.removeElementScroll(a);
      return (
        s && (u = this.removeTransform(u)),
        RY(u),
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
        !(((s = this.scroll) === null || s === void 0 ? void 0 : s.wasRoot) || this.path.some(AY))
      ) {
        const { scroll: c } = this.root;
        c && (Bi(u.x, c.offset.x), Bi(u.y, c.offset.y));
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
          (f.wasRoot && Nt(u, s), Bi(u.x, f.offset.x), Bi(u.y, f.offset.y));
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
          Ui(u, { x: -c.scroll.offset.x, y: -c.scroll.offset.y }),
          zr(c.latestValues) && Ui(u, c.latestValues);
      }
      return zr(this.latestValues) && Ui(u, this.latestValues), u;
    }
    removeTransform(s) {
      const a = Ae();
      Nt(a, s);
      for (let u = 0; u < this.path.length; u++) {
        const l = this.path[u];
        if (!l.instance || !zr(l.latestValues)) continue;
        Jv(l.latestValues) && l.updateSnapshot();
        const c = Ae(),
          f = l.measurePageBox();
        Nt(c, f), WT(a, l.latestValues, l.snapshot ? l.snapshot.layoutBox : void 0, c);
      }
      return zr(this.latestValues) && WT(a, this.latestValues), a;
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
              Es(this.relativeTargetOrigin, this.layout.layoutBox, h.layout.layoutBox),
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
                IK(this.target, this.relativeTarget, this.relativeParent.target))
              : this.targetDelta
              ? (this.resumingFrom
                  ? (this.target = this.applyTransform(this.layout.layoutBox))
                  : Nt(this.target, this.layout.layoutBox),
                QI(this.target, this.targetDelta))
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
                Es(this.relativeTargetOrigin, this.target, h.target),
                Nt(this.relativeTarget, this.relativeTargetOrigin))
              : (this.relativeParent = this.relativeTarget = void 0);
          }
          ls && Br.resolvedTargetDeltas++;
        }
      }
    }
    getClosestProjectingParent() {
      if (!(!this.parent || Jv(this.parent.latestValues) || ZI(this.parent.latestValues)))
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
      zK(this.layoutCorrected, this.treeScale, this.path, u),
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
        : (UT(this.prevProjectionDelta.x, this.projectionDelta.x),
          UT(this.prevProjectionDelta.y, this.projectionDelta.y)),
        bs(this.projectionDelta, this.layoutCorrected, v, this.latestValues),
        (this.treeScale.x !== d ||
          this.treeScale.y !== h ||
          !QT(this.projectionDelta.x, this.prevProjectionDelta.x) ||
          !QT(this.projectionDelta.y, this.prevProjectionDelta.y)) &&
          ((this.hasProjected = !0),
          this.scheduleRender(),
          this.notifyListeners("projectionUpdate", v)),
        ls && Br.recalculatedProjection++;
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
      (this.prevProjectionDelta = zi()),
        (this.projectionDelta = zi()),
        (this.projectionDeltaWithTransform = zi());
    }
    setAnimationOrigin(s, a = !1) {
      const u = this.snapshot,
        l = u ? u.latestValues : {},
        c = { ...this.latestValues },
        f = zi();
      (!this.relativeParent || !this.relativeParent.options.layoutRoot) &&
        (this.relativeTarget = this.relativeTargetOrigin = void 0),
        (this.attemptToResolveRelativeTarget = !a);
      const d = Ae(),
        h = u ? u.source : void 0,
        v = this.layout ? this.layout.source : void 0,
        p = h !== v,
        y = this.getStack(),
        m = !y || y.members.length <= 1,
        g = !!(p && !m && this.options.crossfade === !0 && !this.path.some(kY));
      this.animationProgress = 0;
      let w;
      (this.mixTargetDelta = (x) => {
        const S = x / 1e3;
        nk(f.x, s.x, S),
          nk(f.y, s.y, S),
          this.setTargetDelta(f),
          this.relativeTarget &&
            this.relativeTargetOrigin &&
            this.layout &&
            this.relativeParent &&
            this.relativeParent.layout &&
            (Es(d, this.layout.layoutBox, this.relativeParent.layout.layoutBox),
            TY(this.relativeTarget, this.relativeTargetOrigin, d, S),
            w && cY(this.relativeTarget, w) && (this.isProjectionDirty = !1),
            w || (w = Ae()),
            Nt(w, this.relativeTarget)),
          p && ((this.animationValues = c), iY(c, l, this.latestValues, S, g, m)),
          this.root.scheduleUpdateProjection(),
          this.scheduleRender(),
          (this.animationProgress = S);
      }),
        this.mixTargetDelta(this.options.layoutRoot ? 1e3 : 0);
    }
    startAnimation(s) {
      this.notifyListeners("animationStart"),
        this.currentAnimation && this.currentAnimation.stop(),
        this.resumingFrom &&
          this.resumingFrom.currentAnimation &&
          this.resumingFrom.currentAnimation.stop(),
        this.pendingAnimation && (Kn(this.pendingAnimation), (this.pendingAnimation = void 0)),
        (this.pendingAnimation = fe.update(() => {
          (ku.hasAnimatedSinceResize = !0),
            (this.currentAnimation = QK(0, JT, {
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
        (this.mixTargetDelta && this.mixTargetDelta(JT), this.currentAnimation.stop()),
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
          uD(this.options.animationType, this.layout.layoutBox, l.layoutBox)
        ) {
          u = this.target || Ae();
          const f = Pt(this.layout.layoutBox.x);
          (u.x.min = s.target.x.min), (u.x.max = u.x.min + f);
          const d = Pt(this.layout.layoutBox.y);
          (u.y.min = s.target.y.min), (u.y.max = u.y.min + d);
        }
        Nt(a, u), Ui(a, c), bs(this.projectionDeltaWithTransform, this.layoutCorrected, a, c);
      }
    }
    registerSharedNode(s, a) {
      this.sharedNodes.has(s) || this.sharedNodes.set(s, new fY()), this.sharedNodes.get(s).add(a);
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
      u.z && Sg("z", s, l, this.animationValues);
      for (let c = 0; c < _g.length; c++)
        Sg(`rotate${_g[c]}`, s, l, this.animationValues),
          Sg(`skew${_g[c]}`, s, l, this.animationValues);
      s.render();
      for (const c in l)
        s.setStaticValue(c, l[c]), this.animationValues && (this.animationValues[c] = l[c]);
      s.scheduleRender();
    }
    getProjectionStyles(s) {
      var a, u;
      if (!this.instance || this.isSVG) return;
      if (!this.isVisible) return hY;
      const l = { visibility: "" },
        c = this.getTransformTemplate();
      if (this.needsReset)
        return (
          (this.needsReset = !1),
          (l.opacity = ""),
          (l.pointerEvents = Cu(s == null ? void 0 : s.pointerEvents) || ""),
          (l.transform = c ? c(this.latestValues, "") : "none"),
          l
        );
      const f = this.getLead();
      if (!this.projectionDelta || !this.layout || !f.target) {
        const p = {};
        return (
          this.options.layoutId &&
            ((p.opacity = this.latestValues.opacity !== void 0 ? this.latestValues.opacity : 1),
            (p.pointerEvents = Cu(s == null ? void 0 : s.pointerEvents) || "")),
          this.hasProjected &&
            !zr(this.latestValues) &&
            ((p.transform = c ? c({}, "") : "none"), (this.hasProjected = !1)),
          p
        );
      }
      const d = f.animationValues || f.latestValues;
      this.applyTransformsToTarget(),
        (l.transform = dY(this.projectionDeltaWithTransform, this.treeScale, d)),
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
      for (const p in pl) {
        if (d[p] === void 0) continue;
        const { correct: y, applyTo: m } = pl[p],
          g = l.transform === "none" ? d[p] : y(d[p], f);
        if (m) {
          const w = m.length;
          for (let x = 0; x < w; x++) l[m[x]] = g;
        } else l[p] = g;
      }
      return (
        this.options.layoutId &&
          (l.pointerEvents = f === this ? Cu(s == null ? void 0 : s.pointerEvents) || "" : "none"),
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
        this.root.nodes.forEach(ek),
        this.root.sharedNodes.clear();
    }
  };
}
function mY(e) {
  e.updateLayout();
}
function gY(e) {
  var t;
  const n = ((t = e.resumeFrom) === null || t === void 0 ? void 0 : t.snapshot) || e.snapshot;
  if (e.isLead() && e.layout && n && e.hasListeners("didUpdate")) {
    const { layoutBox: r, measuredBox: i } = e.layout,
      { animationType: o } = e.options,
      s = n.source !== e.layout.source;
    o === "size"
      ? Mt((f) => {
          const d = s ? n.measuredBox[f] : n.layoutBox[f],
            h = Pt(d);
          (d.min = r[f].min), (d.max = d.min + h);
        })
      : uD(o, n.layoutBox, r) &&
        Mt((f) => {
          const d = s ? n.measuredBox[f] : n.layoutBox[f],
            h = Pt(r[f]);
          (d.max = d.min + h),
            e.relativeTarget &&
              !e.currentAnimation &&
              ((e.isProjectionDirty = !0), (e.relativeTarget[f].max = e.relativeTarget[f].min + h));
        });
    const a = zi();
    bs(a, r, n.layoutBox);
    const u = zi();
    s ? bs(u, e.applyTransform(i, !0), n.measuredBox) : bs(u, r, n.layoutBox);
    const l = !iD(a);
    let c = !1;
    if (!e.resumeFrom) {
      const f = e.getClosestProjectingParent();
      if (f && !f.resumeFrom) {
        const { snapshot: d, layout: h } = f;
        if (d && h) {
          const v = Ae();
          Es(v, n.layoutBox, d.layoutBox);
          const p = Ae();
          Es(p, r, h.layoutBox),
            oD(v, p) || (c = !0),
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
function vY(e) {
  ls && Br.totalNodes++,
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
function yY(e) {
  e.isProjectionDirty = e.isSharedProjectionDirty = e.isTransformDirty = !1;
}
function wY(e) {
  e.clearSnapshot();
}
function ek(e) {
  e.clearMeasurements();
}
function xY(e) {
  e.isLayoutDirty = !1;
}
function _Y(e) {
  const { visualElement: t } = e.options;
  t && t.getProps().onBeforeLayoutMeasure && t.notify("BeforeLayoutMeasure"), e.resetTransform();
}
function tk(e) {
  e.finishAnimation(),
    (e.targetDelta = e.relativeTarget = e.target = void 0),
    (e.isProjectionDirty = !0);
}
function SY(e) {
  e.resolveTargetDelta();
}
function bY(e) {
  e.calcProjection();
}
function EY(e) {
  e.resetSkewAndRotation();
}
function CY(e) {
  e.removeLeadSnapshot();
}
function nk(e, t, n) {
  (e.translate = xe(t.translate, 0, n)),
    (e.scale = xe(t.scale, 1, n)),
    (e.origin = t.origin),
    (e.originPoint = t.originPoint);
}
function rk(e, t, n, r) {
  (e.min = xe(t.min, n.min, r)), (e.max = xe(t.max, n.max, r));
}
function TY(e, t, n, r) {
  rk(e.x, t.x, n.x, r), rk(e.y, t.y, n.y, r);
}
function kY(e) {
  return e.animationValues && e.animationValues.opacityExit !== void 0;
}
const PY = { duration: 0.45, ease: [0.4, 0, 0.1, 1] },
  ik = (e) =>
    typeof navigator < "u" && navigator.userAgent && navigator.userAgent.toLowerCase().includes(e),
  ok = ik("applewebkit/") && !ik("chrome/") ? Math.round : Ct;
function sk(e) {
  (e.min = ok(e.min)), (e.max = ok(e.max));
}
function RY(e) {
  sk(e.x), sk(e.y);
}
function uD(e, t, n) {
  return e === "position" || (e === "preserve-aspect" && !MK(ZT(t), ZT(n), 0.2));
}
function AY(e) {
  var t;
  return e !== e.root && ((t = e.scroll) === null || t === void 0 ? void 0 : t.wasRoot);
}
const NY = aD({
    attachResizeListener: (e, t) => na(e, "resize", t),
    measureScroll: () => ({
      x: document.documentElement.scrollLeft || document.body.scrollLeft,
      y: document.documentElement.scrollTop || document.body.scrollTop,
    }),
    checkIsScrollRoot: () => !0,
  }),
  bg = { current: void 0 },
  lD = aD({
    measureScroll: (e) => ({ x: e.scrollLeft, y: e.scrollTop }),
    defaultParent: () => {
      if (!bg.current) {
        const e = new NY({});
        e.mount(window), e.setOptions({ layoutScroll: !0 }), (bg.current = e);
      }
      return bg.current;
    },
    resetTransform: (e, t) => {
      e.style.transform = t !== void 0 ? t : "none";
    },
    checkIsScrollRoot: (e) => window.getComputedStyle(e).position === "fixed",
  }),
  MY = { pan: { Feature: KK }, drag: { Feature: WK, ProjectionNode: lD, MeasureLayout: tD } };
function ak(e, t, n) {
  const { props: r } = e;
  e.animationState && r.whileHover && e.animationState.setActive("whileHover", n === "Start");
  const i = "onHover" + n,
    o = r[i];
  o && fe.postRender(() => o(t, _a(t)));
}
class IY extends Or {
  mount() {
    const { current: t } = this.node;
    t && (this.unmount = M9(t, (n) => (ak(this.node, n, "Start"), (r) => ak(this.node, r, "End"))));
  }
  unmount() {}
}
class DY extends Or {
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
    this.unmount = xa(
      na(this.node.current, "focus", () => this.onFocus()),
      na(this.node.current, "blur", () => this.onBlur())
    );
  }
  unmount() {}
}
function uk(e, t, n) {
  const { props: r } = e;
  e.animationState && r.whileTap && e.animationState.setActive("whileTap", n === "Start");
  const i = "onTap" + (n === "End" ? "" : n),
    o = r[i];
  o && fe.postRender(() => o(t, _a(t)));
}
class OY extends Or {
  mount() {
    const { current: t } = this.node;
    t &&
      (this.unmount = L9(
        t,
        (n) => (
          uk(this.node, n, "Start"), (r, { success: i }) => uk(this.node, r, i ? "End" : "Cancel")
        ),
        { useGlobalTarget: this.node.props.globalTapTarget }
      ));
  }
  unmount() {}
}
const ty = new WeakMap(),
  Eg = new WeakMap(),
  LY = (e) => {
    const t = ty.get(e.target);
    t && t(e);
  },
  FY = (e) => {
    e.forEach(LY);
  };
function VY({ root: e, ...t }) {
  const n = e || document;
  Eg.has(n) || Eg.set(n, {});
  const r = Eg.get(n),
    i = JSON.stringify(t);
  return r[i] || (r[i] = new IntersectionObserver(FY, { root: e, ...t })), r[i];
}
function jY(e, t, n) {
  const r = VY(t);
  return (
    ty.set(e, n),
    r.observe(e),
    () => {
      ty.delete(e), r.unobserve(e);
    }
  );
}
const qY = { some: 0, all: 1 };
class $Y extends Or {
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
        threshold: typeof i == "number" ? i : qY[i],
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
    return jY(this.node.current, s, a);
  }
  mount() {
    this.startObserver();
  }
  update() {
    if (typeof IntersectionObserver > "u") return;
    const { props: t, prevProps: n } = this.node;
    ["amount", "margin", "root"].some(zY(t, n)) && this.startObserver();
  }
  unmount() {}
}
function zY({ viewport: e = {} }, { viewport: t = {} } = {}) {
  return (n) => e[n] !== t[n];
}
const BY = {
    inView: { Feature: $Y },
    tap: { Feature: OY },
    focus: { Feature: DY },
    hover: { Feature: IY },
  },
  UY = { layout: { ProjectionNode: lD, MeasureLayout: tD } },
  ny = { current: null },
  cD = { current: !1 };
function HY() {
  if (((cD.current = !0), !!Y0))
    if (window.matchMedia) {
      const e = window.matchMedia("(prefers-reduced-motion)"),
        t = () => (ny.current = e.matches);
      e.addListener(t), t();
    } else ny.current = !1;
}
const GY = [...DI, tt, Ar],
  WY = (e) => GY.find(II(e)),
  lk = new WeakMap();
function KY(e, t, n) {
  for (const r in t) {
    const i = t[r],
      o = n[r];
    if (Be(i)) e.addValue(r, i);
    else if (Be(o)) e.addValue(r, vo(i, { owner: e }));
    else if (o !== i)
      if (e.hasValue(r)) {
        const s = e.getValue(r);
        s.liveStyle === !0 ? s.jump(i) : s.hasAnimated || s.set(i);
      } else {
        const s = e.getStaticValue(r);
        e.addValue(r, vo(s !== void 0 ? s : i, { owner: e }));
      }
  }
  for (const r in n) t[r] === void 0 && e.removeValue(r);
  return t;
}
const ck = [
  "AnimationStart",
  "AnimationComplete",
  "Update",
  "BeforeLayoutMeasure",
  "LayoutMeasure",
  "LayoutAnimationStart",
  "LayoutAnimationComplete",
];
class YY {
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
    a = {}
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
        const h = wn.now();
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
      (this.isControllingVariants = vc(n)),
      (this.isVariantNode = z2(n)),
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
      lk.set(t, this),
      this.projection && !this.projection.instance && this.projection.mount(t),
      this.parent &&
        this.isVariantNode &&
        !this.isControllingVariants &&
        (this.removeFromVariantTree = this.parent.addVariantChild(this)),
      this.values.forEach((n, r) => this.bindToMotionValue(r, n)),
      cD.current || HY(),
      (this.shouldReduceMotion =
        this.reducedMotionConfig === "never"
          ? !1
          : this.reducedMotionConfig === "always"
          ? !0
          : ny.current),
      this.parent && this.parent.children.add(this),
      this.update(this.props, this.presenceContext);
  }
  unmount() {
    lk.delete(this.current),
      this.projection && this.projection.unmount(),
      Kn(this.notifyUpdate),
      Kn(this.render),
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
    const r = vi.has(t),
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
    for (t in go) {
      const n = go[t];
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
    for (let r = 0; r < ck.length; r++) {
      const i = ck[r];
      this.propEventSubscriptions[i] &&
        (this.propEventSubscriptions[i](), delete this.propEventSubscriptions[i]);
      const o = "on" + i,
        s = t[o];
      s && (this.propEventSubscriptions[i] = this.on(i, s));
    }
    (this.prevMotionValues = KY(
      this,
      this.scrapeMotionValuesFromProps(t, this.prevProps, this),
      this.prevMotionValues
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
        ((r = vo(n === null ? void 0 : n, { owner: this })), this.addValue(t, r)),
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
        (typeof i == "string" && (NI(i) || SI(i))
          ? (i = parseFloat(i))
          : !WY(i) && Ar.test(n) && (i = PI(t, n)),
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
      const s = rw(
        this.props,
        r,
        (n = this.presenceContext) === null || n === void 0 ? void 0 : n.custom
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
    return this.events[t] || (this.events[t] = new vw()), this.events[t].add(n);
  }
  notify(t, ...n) {
    this.events[t] && this.events[t].notify(...n);
  }
}
class fD extends YY {
  constructor() {
    super(...arguments), (this.KeyframeResolver = OI);
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
function XY(e) {
  return window.getComputedStyle(e);
}
class ZY extends fD {
  constructor() {
    super(...arguments), (this.type = "html"), (this.renderInstance = Z2);
  }
  readValueFromInstance(t, n) {
    if (vi.has(n)) {
      const r = Sw(n);
      return (r && r.default) || 0;
    } else {
      const r = XY(t),
        i = (K2(n) ? r.getPropertyValue(n) : r[n]) || 0;
      return typeof i == "string" ? i.trim() : i;
    }
  }
  measureInstanceViewportBox(t, { transformPagePoint: n }) {
    return JI(t, n);
  }
  build(t, n, r) {
    sw(t, n, r.transformTemplate);
  }
  scrapeMotionValuesFromProps(t, n, r) {
    return cw(t, n, r);
  }
}
class QY extends fD {
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
    if (vi.has(n)) {
      const r = Sw(n);
      return (r && r.default) || 0;
    }
    return (n = Q2.has(n) ? n : ew(n)), t.getAttribute(n);
  }
  scrapeMotionValuesFromProps(t, n, r) {
    return tI(t, n, r);
  }
  build(t, n, r) {
    aw(t, n, this.isSVGTag, r.transformTemplate);
  }
  renderInstance(t, n, r, i) {
    J2(t, n, r, i);
  }
  mount(t) {
    (this.isSVGTag = lw(t.tagName)), super.mount(t);
  }
}
const JY = (e, t) => (nw(e) ? new QY(t) : new ZY(t, { allowProjection: e !== _.Fragment })),
  eX = C9({ ...bK, ...BY, ...MY, ...UY }, JY),
  dD = qW(eX);
function Tw(e) {
  const t = W0(() => vo(e)),
    { isStatic: n } = _.useContext(pc);
  if (n) {
    const [, r] = _.useState(e);
    _.useEffect(() => t.on("change", r), []);
  }
  return t;
}
function hD(e, t) {
  const n = Tw(t()),
    r = () => n.set(t());
  return (
    r(),
    X0(() => {
      const i = () => fe.preRender(r, !1, !0),
        o = e.map((s) => s.on("change", i));
      return () => {
        o.forEach((s) => s()), Kn(r);
      };
    }),
    n
  );
}
function fk(e) {
  return typeof e == "number" ? e : parseFloat(e);
}
function tX(e, t = {}) {
  const { isStatic: n } = _.useContext(pc),
    r = _.useRef(null),
    i = Tw(Be(e) ? fk(e.get()) : e),
    o = _.useRef(i.get()),
    s = _.useRef(() => {}),
    a = () => {
      const l = r.current;
      l && l.time === 0 && l.sample($e.delta),
        u(),
        (r.current = X7({
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
          u
        ),
      [JSON.stringify(t)]
    ),
    X0(() => {
      if (Be(e)) return e.on("change", (l) => i.set(fk(l)));
    }, [i]),
    i
  );
}
const nX = (e) => e && typeof e == "object" && e.mix,
  rX = (e) => (nX(e) ? e.mix : void 0);
function iX(...e) {
  const t = !Array.isArray(e[0]),
    n = t ? 0 : -1,
    r = e[0 + n],
    i = e[1 + n],
    o = e[2 + n],
    s = e[3 + n],
    a = zI(i, o, { mixer: rX(o[0]), ...s });
  return t ? a(r) : a;
}
function oX(e) {
  (xs.current = []), e();
  const t = hD(xs.current, e);
  return (xs.current = void 0), t;
}
function dk(e, t, n, r) {
  if (typeof e == "function") return oX(e);
  const i = typeof t == "function" ? t : iX(t, n, r);
  return Array.isArray(e) ? hk(e, i) : hk([e], ([o]) => i(o));
}
function hk(e, t) {
  const n = W0(() => []);
  return hD(e, () => {
    n.length = 0;
    const r = e.length;
    for (let i = 0; i < r; i++) n[i] = e[i].get();
    return t(n);
  });
}
const sX = bM(
    "flex h-full w-max items-end gap-2 rounded-lg p-2 transition-all duration-300 ease-out"
  ),
  pD = L.forwardRef(({ className: e, children: t, ...n }, r) => {
    const i = Tw(1 / 0);
    return M.jsx(dD.div, {
      ref: r,
      onMouseMove: (o) => i.set(o.pageX),
      onMouseLeave: () => i.set(1 / 0),
      ...n,
      className: ke(sX({ className: e }), "z-50"),
      children: L.Children.map(t, (o) => L.cloneElement(o, { mouseX: i })),
    });
  });
pD.displayName = "Dock";
const Pu = ({ mouseX: e, className: t, children: n, ...r }) => {
  const i = _.useRef(null),
    o = dk(e, (u) => {
      var c;
      const l = ((c = i.current) == null ? void 0 : c.getBoundingClientRect()) ?? {
        x: 0,
        width: 0,
      };
      return u - l.x - l.width / 2;
    }),
    s = dk(o, [-150, 0, 150], [40, 80, 40]),
    a = tX(s, { mass: 0.1, stiffness: 150, damping: 12 });
  return M.jsx(dD.div, {
    ref: i,
    style: { width: a },
    className: ke(
      "flex aspect-square items-center justify-center rounded-full bg-neutral-100/50 dark:bg-neutral-800/50",
      t
    ),
    ...r,
    children: n,
  });
};
Pu.displayName = "DockIcon";
const mD = L.forwardRef(
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
    u
  ) =>
    M.jsxs("button", {
      style: {
        "--shimmer-color": e,
        "--shimmer-size": t,
        "--shimmer-duration": n,
        "--background": i,
        borderRadius: r,
      },
      className: ke(
        "group relative z-0 flex cursor-pointer items-center justify-center overflow-hidden whitespace-nowrap border border-white/10 px-6 py-3 text-white [background:var(--background)] [border-radius:var(--border-radius)]",
        "transform-gpu transition-transform duration-300 ease-in-out hover:scale-105",
        o
      ),
      ref: u,
      ...a,
      children: [
        M.jsx("div", {
          className: "absolute inset-0 z-0 overflow-hidden rounded-[inherit]",
          children: M.jsx("div", {
            className: ke(
              "absolute inset-0 z-0 h-full w-full animate-[shimmer_var(--shimmer-duration)_infinite] bg-gradient-to-r from-transparent via-transparent to-[var(--shimmer-color)] opacity-0 transition-opacity duration-500 group-hover:opacity-100",
              "[--shimmer-angle:-45deg]"
            ),
          }),
        }),
        M.jsx("div", { className: "relative z-10", children: s }),
      ],
    })
);
mD.displayName = "ShimmerButton";
function aX() {
  WF();
  const e = Fl((a) => a.machines),
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
  return M.jsxs("div", {
    className: "flex h-screen w-full flex-col bg-background font-sans text-foreground",
    children: [
      M.jsx(uX, { onToggleTheme: o, isDark: r }),
      M.jsxs("div", {
        className: "flex flex-1 overflow-hidden",
        children: [
          M.jsx(lX, { machines: e, selectedMachineId: t, onSelectMachine: n }),
          M.jsx("main", {
            className: "flex-1 flex flex-col overflow-hidden",
            children: s ? M.jsx(cX, { machine: s }, s.id) : M.jsx(pX, {}),
          }),
        ],
      }),
    ],
  });
}
const uX = ({ onToggleTheme: e, isDark: t }) =>
    M.jsxs("header", {
      className: "flex h-14 items-center justify-between border-b bg-card px-4 lg:px-6",
      children: [
        M.jsxs("div", {
          className: "flex items-center gap-2 font-bold",
          children: [
            M.jsx(qU, { className: "h-6 w-6 text-primary" }),
            M.jsx("span", { children: "XState Inspector" }),
          ],
        }),
        M.jsxs(F0, {
          variant: "ghost",
          size: "icon",
          onClick: e,
          children: [
            M.jsx(KU, {
              className: "h-5 w-5 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0",
            }),
            M.jsx(BU, {
              className:
                "absolute h-5 w-5 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100",
            }),
            M.jsx("span", { className: "sr-only", children: "Toggle theme" }),
          ],
        }),
      ],
    }),
  lX = ({ machines: e, selectedMachineId: t, onSelectMachine: n }) =>
    M.jsxs("aside", {
      className: "hidden w-72 flex-col border-r bg-card p-4 sm:flex",
      children: [
        M.jsx("h2", {
          className: "text-base font-semibold tracking-tight",
          children: "Live Machines",
        }),
        M.jsx("nav", {
          className: "mt-4 flex flex-col gap-1",
          children: Object.values(e).map((r) =>
            M.jsx(
              "div",
              {
                children: M.jsx(F0, {
                  variant: t === r.id ? "secondary" : "ghost",
                  className: "w-full justify-start",
                  onClick: () => n(r.id),
                  children: r.id,
                }),
              },
              r.id
            )
          ),
        }),
      ],
    }),
  cX = ({ machine: e }) =>
    M.jsxs("div", {
      className: "grid h-full grid-cols-1 lg:grid-cols-3 gap-4 p-4",
      children: [
        M.jsxs("div", {
          className: "lg:col-span-2 flex flex-col gap-4 relative",
          children: [
            M.jsxs(V0, {
              className: "flex-1 flex flex-col",
              children: [
                M.jsxs(j0, {
                  children: [
                    M.jsx(q0, { children: e.id }),
                    M.jsxs("p", {
                      className: "text-sm text-muted-foreground",
                      children: [
                        "Current State: ",
                        M.jsx("span", {
                          className: "font-mono text-primary",
                          children: e.currentStateIds.join(", "),
                        }),
                      ],
                    }),
                  ],
                }),
                M.jsx($0, {
                  className: "flex-1 relative",
                  children: M.jsx(LU, { machine: e, activeStateIds: e.currentStateIds }),
                }),
              ],
            }),
            M.jsx(dX, { machineId: e.id }),
          ],
        }),
        M.jsx("div", { className: "flex flex-col", children: M.jsx(fX, { machine: e }) }),
      ],
    }),
  fX = ({ machine: e }) =>
    M.jsxs(dG, {
      defaultValue: "events",
      className: "flex-1 flex flex-col overflow-hidden",
      children: [
        M.jsxs(YM, {
          className: "grid w-full grid-cols-3",
          children: [
            M.jsxs(_u, {
              value: "events",
              children: [M.jsx(zU, { className: "w-4 h-4 mr-2" }), "Event Log"],
            }),
            M.jsxs(_u, {
              value: "context",
              children: [M.jsx(WU, { className: "w-4 h-4 mr-2" }), "Context"],
            }),
            M.jsxs(_u, {
              value: "json",
              children: [M.jsx($U, { className: "w-4 h-4 mr-2" }), "Definition"],
            }),
          ],
        }),
        M.jsx(Su, {
          value: "events",
          className: "flex-1 overflow-y-auto mt-0",
          children: M.jsx("div", {
            className: "font-mono text-xs space-y-2 p-4",
            children: e.logs
              .slice()
              .reverse()
              .map((t, n) =>
                M.jsxs(
                  "div",
                  {
                    className: "p-2 rounded bg-muted",
                    children: [
                      M.jsx("p", { className: "font-bold text-primary", children: t.type }),
                      M.jsx("pre", {
                        className:
                          "text-muted-foreground whitespace-pre-wrap break-all text-[11px]",
                        children: JSON.stringify(t.payload, null, 2),
                      }),
                    ],
                  },
                  n
                )
              ),
          }),
        }),
        M.jsx(Su, {
          value: "context",
          className: "flex-1 overflow-y-auto mt-0",
          children: M.jsx("pre", {
            className: "font-mono text-xs p-4",
            children: JSON.stringify(e.context, null, 2),
          }),
        }),
        M.jsx(Su, {
          value: "json",
          className: "flex-1 overflow-y-auto mt-0",
          children: M.jsx("pre", {
            className: "font-mono text-xs p-4",
            children: JSON.stringify(e.definition, null, 2),
          }),
        }),
      ],
    }),
  dX = ({ machineId: e }) => {
    const [t, n] = _.useState(!1),
      r = Fl((i) => i.sendCommand);
    return M.jsxs(M.Fragment, {
      children: [
        M.jsx("div", {
          className: "absolute bottom-4 left-1/2 -translate-x-1/2",
          children: M.jsxs(pD, {
            children: [
              M.jsx(Pu, {
                onClick: () => r("resume", { machine_id: e }),
                children: M.jsx(HU, { className: "h-4 w-4" }),
              }),
              M.jsx(Pu, {
                onClick: () => r("pause", { machine_id: e }),
                children: M.jsx(UU, { className: "h-4 w-4" }),
              }),
              M.jsx(Pu, { onClick: () => n(!0), children: M.jsx(GU, { className: "h-4 w-4" }) }),
            ],
          }),
        }),
        M.jsx(hX, { open: t, onOpenChange: n, machineId: e }),
      ],
    });
  },
  hX = ({ open: e, onOpenChange: t, machineId: n }) => {
    const [r, i] = _.useState(""),
      [o, s] = _.useState(""),
      a = Fl((l) => l.sendCommand),
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
    return M.jsx(RW, {
      open: e,
      onOpenChange: t,
      children: M.jsxs(N2, {
        children: [
          M.jsx(M2, { children: M.jsxs(D2, { children: ["Send Event to ", n] }) }),
          M.jsxs("div", {
            className: "grid gap-4 py-4",
            children: [
              M.jsx(O2, {
                placeholder: "Event Type (e.g., ENABLE)",
                value: r,
                onChange: (l) => i(l.target.value),
              }),
              M.jsx(L2, {
                placeholder: 'Payload (JSON), e.g., {"value": 42}',
                value: o,
                onChange: (l) => s(l.target.value),
              }),
            ],
          }),
          M.jsx(I2, {
            children: M.jsx(mD, {
              className: "w-full",
              onClick: u,
              children: M.jsx("span", {
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
  pX = () =>
    M.jsx("div", {
      className: "flex h-full items-center justify-center m-4",
      children: M.jsxs(V0, {
        className: "w-full max-w-md",
        children: [
          M.jsx(j0, {
            children: M.jsx(q0, { className: "text-2xl", children: "No Live Machines Detected" }),
          }),
          M.jsx($0, {
            children: M.jsx("p", {
              className: "text-muted-foreground",
              children: "Run a Python script with the InspectorPlugin to begin debugging.",
            }),
          }),
        ],
      }),
    });
Cg.createRoot(document.getElementById("root")).render(
  M.jsx(L.StrictMode, { children: M.jsx(aX, {}) })
);
