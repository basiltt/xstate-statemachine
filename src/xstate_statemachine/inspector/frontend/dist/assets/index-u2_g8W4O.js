function MC(e, t) {
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
function hd(e) {
  return e && e.__esModule && Object.prototype.hasOwnProperty.call(e, "default") ? e.default : e;
}
var o0 = { exports: {} },
  Fl = {},
  i0 = { exports: {} },
  re = {};
/**
 * @license React
 * react.production.min.js
 *
 * Copyright (c) Facebook, Inc. and its affiliates.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */ var Es = Symbol.for("react.element"),
  AC = Symbol.for("react.portal"),
  RC = Symbol.for("react.fragment"),
  DC = Symbol.for("react.strict_mode"),
  IC = Symbol.for("react.profiler"),
  LC = Symbol.for("react.provider"),
  VC = Symbol.for("react.context"),
  OC = Symbol.for("react.forward_ref"),
  jC = Symbol.for("react.suspense"),
  FC = Symbol.for("react.memo"),
  zC = Symbol.for("react.lazy"),
  vp = Symbol.iterator;
function $C(e) {
  return e === null || typeof e != "object"
    ? null
    : ((e = (vp && e[vp]) || e["@@iterator"]), typeof e == "function" ? e : null);
}
var s0 = {
    isMounted: function () {
      return !1;
    },
    enqueueForceUpdate: function () {},
    enqueueReplaceState: function () {},
    enqueueSetState: function () {},
  },
  a0 = Object.assign,
  l0 = {};
function Wo(e, t, n) {
  (this.props = e), (this.context = t), (this.refs = l0), (this.updater = n || s0);
}
Wo.prototype.isReactComponent = {};
Wo.prototype.setState = function (e, t) {
  if (typeof e != "object" && typeof e != "function" && e != null)
    throw Error(
      "setState(...): takes an object of state variables to update or a function which returns an object of state variables.",
    );
  this.updater.enqueueSetState(this, e, t, "setState");
};
Wo.prototype.forceUpdate = function (e) {
  this.updater.enqueueForceUpdate(this, e, "forceUpdate");
};
function u0() {}
u0.prototype = Wo.prototype;
function pd(e, t, n) {
  (this.props = e), (this.context = t), (this.refs = l0), (this.updater = n || s0);
}
var md = (pd.prototype = new u0());
md.constructor = pd;
a0(md, Wo.prototype);
md.isPureReactComponent = !0;
var xp = Array.isArray,
  c0 = Object.prototype.hasOwnProperty,
  gd = { current: null },
  f0 = { key: !0, ref: !0, __self: !0, __source: !0 };
function d0(e, t, n) {
  var r,
    o = {},
    i = null,
    s = null;
  if (t != null)
    for (r in (t.ref !== void 0 && (s = t.ref), t.key !== void 0 && (i = "" + t.key), t))
      c0.call(t, r) && !f0.hasOwnProperty(r) && (o[r] = t[r]);
  var a = arguments.length - 2;
  if (a === 1) o.children = n;
  else if (1 < a) {
    for (var l = Array(a), u = 0; u < a; u++) l[u] = arguments[u + 2];
    o.children = l;
  }
  if (e && e.defaultProps) for (r in ((a = e.defaultProps), a)) o[r] === void 0 && (o[r] = a[r]);
  return { $$typeof: Es, type: e, key: i, ref: s, props: o, _owner: gd.current };
}
function BC(e, t) {
  return { $$typeof: Es, type: e.type, key: t, ref: e.ref, props: e.props, _owner: e._owner };
}
function yd(e) {
  return typeof e == "object" && e !== null && e.$$typeof === Es;
}
function HC(e) {
  var t = { "=": "=0", ":": "=2" };
  return (
    "$" +
    e.replace(/[=:]/g, function (n) {
      return t[n];
    })
  );
}
var wp = /\/+/g;
function Pu(e, t) {
  return typeof e == "object" && e !== null && e.key != null ? HC("" + e.key) : t.toString(36);
}
function Ea(e, t, n, r, o) {
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
          case Es:
          case AC:
            s = !0;
        }
    }
  if (s)
    return (
      (s = e),
      (o = o(s)),
      (e = r === "" ? "." + Pu(s, 0) : r),
      xp(o)
        ? ((n = ""),
          e != null && (n = e.replace(wp, "$&/") + "/"),
          Ea(o, t, n, "", function (u) {
            return u;
          }))
        : o != null &&
          (yd(o) &&
            (o = BC(
              o,
              n +
                (!o.key || (s && s.key === o.key) ? "" : ("" + o.key).replace(wp, "$&/") + "/") +
                e,
            )),
          t.push(o)),
      1
    );
  if (((s = 0), (r = r === "" ? "." : r + ":"), xp(e)))
    for (var a = 0; a < e.length; a++) {
      i = e[a];
      var l = r + Pu(i, a);
      s += Ea(i, t, n, l, o);
    }
  else if (((l = $C(e)), typeof l == "function"))
    for (e = l.call(e), a = 0; !(i = e.next()).done; )
      (i = i.value), (l = r + Pu(i, a++)), (s += Ea(i, t, n, l, o));
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
function zs(e, t, n) {
  if (e == null) return e;
  var r = [],
    o = 0;
  return (
    Ea(e, r, "", "", function (i) {
      return t.call(n, i, o++);
    }),
    r
  );
}
function UC(e) {
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
var tt = { current: null },
  Ca = { transition: null },
  WC = { ReactCurrentDispatcher: tt, ReactCurrentBatchConfig: Ca, ReactCurrentOwner: gd };
function h0() {
  throw Error("act(...) is not supported in production builds of React.");
}
re.Children = {
  map: zs,
  forEach: function (e, t, n) {
    zs(
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
      zs(e, function () {
        t++;
      }),
      t
    );
  },
  toArray: function (e) {
    return (
      zs(e, function (t) {
        return t;
      }) || []
    );
  },
  only: function (e) {
    if (!yd(e))
      throw Error("React.Children.only expected to receive a single React element child.");
    return e;
  },
};
re.Component = Wo;
re.Fragment = RC;
re.Profiler = IC;
re.PureComponent = pd;
re.StrictMode = DC;
re.Suspense = jC;
re.__SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED = WC;
re.act = h0;
re.cloneElement = function (e, t, n) {
  if (e == null)
    throw Error(
      "React.cloneElement(...): The argument must be a React element, but you passed " + e + ".",
    );
  var r = a0({}, e.props),
    o = e.key,
    i = e.ref,
    s = e._owner;
  if (t != null) {
    if (
      (t.ref !== void 0 && ((i = t.ref), (s = gd.current)),
      t.key !== void 0 && (o = "" + t.key),
      e.type && e.type.defaultProps)
    )
      var a = e.type.defaultProps;
    for (l in t)
      c0.call(t, l) &&
        !f0.hasOwnProperty(l) &&
        (r[l] = t[l] === void 0 && a !== void 0 ? a[l] : t[l]);
  }
  var l = arguments.length - 2;
  if (l === 1) r.children = n;
  else if (1 < l) {
    a = Array(l);
    for (var u = 0; u < l; u++) a[u] = arguments[u + 2];
    r.children = a;
  }
  return { $$typeof: Es, type: e.type, key: o, ref: i, props: r, _owner: s };
};
re.createContext = function (e) {
  return (
    (e = {
      $$typeof: VC,
      _currentValue: e,
      _currentValue2: e,
      _threadCount: 0,
      Provider: null,
      Consumer: null,
      _defaultValue: null,
      _globalName: null,
    }),
    (e.Provider = { $$typeof: LC, _context: e }),
    (e.Consumer = e)
  );
};
re.createElement = d0;
re.createFactory = function (e) {
  var t = d0.bind(null, e);
  return (t.type = e), t;
};
re.createRef = function () {
  return { current: null };
};
re.forwardRef = function (e) {
  return { $$typeof: OC, render: e };
};
re.isValidElement = yd;
re.lazy = function (e) {
  return { $$typeof: zC, _payload: { _status: -1, _result: e }, _init: UC };
};
re.memo = function (e, t) {
  return { $$typeof: FC, type: e, compare: t === void 0 ? null : t };
};
re.startTransition = function (e) {
  var t = Ca.transition;
  Ca.transition = {};
  try {
    e();
  } finally {
    Ca.transition = t;
  }
};
re.unstable_act = h0;
re.useCallback = function (e, t) {
  return tt.current.useCallback(e, t);
};
re.useContext = function (e) {
  return tt.current.useContext(e);
};
re.useDebugValue = function () {};
re.useDeferredValue = function (e) {
  return tt.current.useDeferredValue(e);
};
re.useEffect = function (e, t) {
  return tt.current.useEffect(e, t);
};
re.useId = function () {
  return tt.current.useId();
};
re.useImperativeHandle = function (e, t, n) {
  return tt.current.useImperativeHandle(e, t, n);
};
re.useInsertionEffect = function (e, t) {
  return tt.current.useInsertionEffect(e, t);
};
re.useLayoutEffect = function (e, t) {
  return tt.current.useLayoutEffect(e, t);
};
re.useMemo = function (e, t) {
  return tt.current.useMemo(e, t);
};
re.useReducer = function (e, t, n) {
  return tt.current.useReducer(e, t, n);
};
re.useRef = function (e) {
  return tt.current.useRef(e);
};
re.useState = function (e) {
  return tt.current.useState(e);
};
re.useSyncExternalStore = function (e, t, n) {
  return tt.current.useSyncExternalStore(e, t, n);
};
re.useTransition = function () {
  return tt.current.useTransition();
};
re.version = "18.3.1";
i0.exports = re;
var v = i0.exports;
const L = hd(v),
  p0 = MC({ __proto__: null, default: L }, [v]);
/**
 * @license React
 * react-jsx-runtime.production.min.js
 *
 * Copyright (c) Facebook, Inc. and its affiliates.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */ var GC = v,
  KC = Symbol.for("react.element"),
  YC = Symbol.for("react.fragment"),
  XC = Object.prototype.hasOwnProperty,
  ZC = GC.__SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED.ReactCurrentOwner,
  QC = { key: !0, ref: !0, __self: !0, __source: !0 };
function m0(e, t, n) {
  var r,
    o = {},
    i = null,
    s = null;
  n !== void 0 && (i = "" + n),
    t.key !== void 0 && (i = "" + t.key),
    t.ref !== void 0 && (s = t.ref);
  for (r in t) XC.call(t, r) && !QC.hasOwnProperty(r) && (o[r] = t[r]);
  if (e && e.defaultProps) for (r in ((t = e.defaultProps), t)) o[r] === void 0 && (o[r] = t[r]);
  return { $$typeof: KC, type: e, key: i, ref: s, props: o, _owner: ZC.current };
}
Fl.Fragment = YC;
Fl.jsx = m0;
Fl.jsxs = m0;
o0.exports = Fl;
var C = o0.exports,
  Lc = {},
  g0 = { exports: {} },
  yt = {},
  y0 = { exports: {} },
  v0 = {};
/**
 * @license React
 * scheduler.production.min.js
 *
 * Copyright (c) Facebook, Inc. and its affiliates.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */ (function (e) {
  function t(M, T) {
    var D = M.length;
    M.push(T);
    e: for (; 0 < D; ) {
      var F = (D - 1) >>> 1,
        z = M[F];
      if (0 < o(z, T)) (M[F] = T), (M[D] = z), (D = F);
      else break e;
    }
  }
  function n(M) {
    return M.length === 0 ? null : M[0];
  }
  function r(M) {
    if (M.length === 0) return null;
    var T = M[0],
      D = M.pop();
    if (D !== T) {
      M[0] = D;
      e: for (var F = 0, z = M.length, W = z >>> 1; F < W; ) {
        var H = 2 * (F + 1) - 1,
          Y = M[H],
          U = H + 1,
          X = M[U];
        if (0 > o(Y, D))
          U < z && 0 > o(X, Y)
            ? ((M[F] = X), (M[U] = D), (F = U))
            : ((M[F] = Y), (M[H] = D), (F = H));
        else if (U < z && 0 > o(X, D)) (M[F] = X), (M[U] = D), (F = U);
        else break e;
      }
    }
    return T;
  }
  function o(M, T) {
    var D = M.sortIndex - T.sortIndex;
    return D !== 0 ? D : M.id - T.id;
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
    m = !1,
    y = !1,
    g = !1,
    w = typeof setTimeout == "function" ? setTimeout : null,
    h = typeof clearTimeout == "function" ? clearTimeout : null,
    p = typeof setImmediate < "u" ? setImmediate : null;
  typeof navigator < "u" &&
    navigator.scheduling !== void 0 &&
    navigator.scheduling.isInputPending !== void 0 &&
    navigator.scheduling.isInputPending.bind(navigator.scheduling);
  function x(M) {
    for (var T = n(u); T !== null; ) {
      if (T.callback === null) r(u);
      else if (T.startTime <= M) r(u), (T.sortIndex = T.expirationTime), t(l, T);
      else break;
      T = n(u);
    }
  }
  function S(M) {
    if (((g = !1), x(M), !y))
      if (n(l) !== null) (y = !0), P(E);
      else {
        var T = n(u);
        T !== null && V(S, T.startTime - M);
      }
  }
  function E(M, T) {
    (y = !1), g && ((g = !1), h(N), (N = -1)), (m = !0);
    var D = d;
    try {
      for (x(T), f = n(l); f !== null && (!(f.expirationTime > T) || (M && !O())); ) {
        var F = f.callback;
        if (typeof F == "function") {
          (f.callback = null), (d = f.priorityLevel);
          var z = F(f.expirationTime <= T);
          (T = e.unstable_now()),
            typeof z == "function" ? (f.callback = z) : f === n(l) && r(l),
            x(T);
        } else r(l);
        f = n(l);
      }
      if (f !== null) var W = !0;
      else {
        var H = n(u);
        H !== null && V(S, H.startTime - T), (W = !1);
      }
      return W;
    } finally {
      (f = null), (d = D), (m = !1);
    }
  }
  var _ = !1,
    k = null,
    N = -1,
    A = 5,
    R = -1;
  function O() {
    return !(e.unstable_now() - R < A);
  }
  function j() {
    if (k !== null) {
      var M = e.unstable_now();
      R = M;
      var T = !0;
      try {
        T = k(!0, M);
      } finally {
        T ? $() : ((_ = !1), (k = null));
      }
    } else _ = !1;
  }
  var $;
  if (typeof p == "function")
    $ = function () {
      p(j);
    };
  else if (typeof MessageChannel < "u") {
    var b = new MessageChannel(),
      I = b.port2;
    (b.port1.onmessage = j),
      ($ = function () {
        I.postMessage(null);
      });
  } else
    $ = function () {
      w(j, 0);
    };
  function P(M) {
    (k = M), _ || ((_ = !0), $());
  }
  function V(M, T) {
    N = w(function () {
      M(e.unstable_now());
    }, T);
  }
  (e.unstable_IdlePriority = 5),
    (e.unstable_ImmediatePriority = 1),
    (e.unstable_LowPriority = 4),
    (e.unstable_NormalPriority = 3),
    (e.unstable_Profiling = null),
    (e.unstable_UserBlockingPriority = 2),
    (e.unstable_cancelCallback = function (M) {
      M.callback = null;
    }),
    (e.unstable_continueExecution = function () {
      y || m || ((y = !0), P(E));
    }),
    (e.unstable_forceFrameRate = function (M) {
      0 > M || 125 < M
        ? console.error(
            "forceFrameRate takes a positive int between 0 and 125, forcing frame rates higher than 125 fps is not supported",
          )
        : (A = 0 < M ? Math.floor(1e3 / M) : 5);
    }),
    (e.unstable_getCurrentPriorityLevel = function () {
      return d;
    }),
    (e.unstable_getFirstCallbackNode = function () {
      return n(l);
    }),
    (e.unstable_next = function (M) {
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
        return M();
      } finally {
        d = D;
      }
    }),
    (e.unstable_pauseExecution = function () {}),
    (e.unstable_requestPaint = function () {}),
    (e.unstable_runWithPriority = function (M, T) {
      switch (M) {
        case 1:
        case 2:
        case 3:
        case 4:
        case 5:
          break;
        default:
          M = 3;
      }
      var D = d;
      d = M;
      try {
        return T();
      } finally {
        d = D;
      }
    }),
    (e.unstable_scheduleCallback = function (M, T, D) {
      var F = e.unstable_now();
      switch (
        (typeof D == "object" && D !== null
          ? ((D = D.delay), (D = typeof D == "number" && 0 < D ? F + D : F))
          : (D = F),
        M)
      ) {
        case 1:
          var z = -1;
          break;
        case 2:
          z = 250;
          break;
        case 5:
          z = 1073741823;
          break;
        case 4:
          z = 1e4;
          break;
        default:
          z = 5e3;
      }
      return (
        (z = D + z),
        (M = {
          id: c++,
          callback: T,
          priorityLevel: M,
          startTime: D,
          expirationTime: z,
          sortIndex: -1,
        }),
        D > F
          ? ((M.sortIndex = D),
            t(u, M),
            n(l) === null && M === n(u) && (g ? (h(N), (N = -1)) : (g = !0), V(S, D - F)))
          : ((M.sortIndex = z), t(l, M), y || m || ((y = !0), P(E))),
        M
      );
    }),
    (e.unstable_shouldYield = O),
    (e.unstable_wrapCallback = function (M) {
      var T = d;
      return function () {
        var D = d;
        d = T;
        try {
          return M.apply(this, arguments);
        } finally {
          d = D;
        }
      };
    });
})(v0);
y0.exports = v0;
var qC = y0.exports;
/**
 * @license React
 * react-dom.production.min.js
 *
 * Copyright (c) Facebook, Inc. and its affiliates.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */ var JC = v,
  pt = qC;
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
var x0 = new Set(),
  Bi = {};
function Vr(e, t) {
  Po(e, t), Po(e + "Capture", t);
}
function Po(e, t) {
  for (Bi[e] = t, e = 0; e < t.length; e++) x0.add(t[e]);
}
var vn = !(
    typeof window > "u" ||
    typeof window.document > "u" ||
    typeof window.document.createElement > "u"
  ),
  Vc = Object.prototype.hasOwnProperty,
  eb =
    /^[:A-Z_a-z\u00C0-\u00D6\u00D8-\u00F6\u00F8-\u02FF\u0370-\u037D\u037F-\u1FFF\u200C-\u200D\u2070-\u218F\u2C00-\u2FEF\u3001-\uD7FF\uF900-\uFDCF\uFDF0-\uFFFD][:A-Z_a-z\u00C0-\u00D6\u00D8-\u00F6\u00F8-\u02FF\u0370-\u037D\u037F-\u1FFF\u200C-\u200D\u2070-\u218F\u2C00-\u2FEF\u3001-\uD7FF\uF900-\uFDCF\uFDF0-\uFFFD\-.0-9\u00B7\u0300-\u036F\u203F-\u2040]*$/,
  Sp = {},
  Ep = {};
function tb(e) {
  return Vc.call(Ep, e) ? !0 : Vc.call(Sp, e) ? !1 : eb.test(e) ? (Ep[e] = !0) : ((Sp[e] = !0), !1);
}
function nb(e, t, n, r) {
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
function rb(e, t, n, r) {
  if (t === null || typeof t > "u" || nb(e, t, n, r)) return !0;
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
function nt(e, t, n, r, o, i, s) {
  (this.acceptsBooleans = t === 2 || t === 3 || t === 4),
    (this.attributeName = r),
    (this.attributeNamespace = o),
    (this.mustUseProperty = n),
    (this.propertyName = e),
    (this.type = t),
    (this.sanitizeURL = i),
    (this.removeEmptyString = s);
}
var Be = {};
"children dangerouslySetInnerHTML defaultValue defaultChecked innerHTML suppressContentEditableWarning suppressHydrationWarning style"
  .split(" ")
  .forEach(function (e) {
    Be[e] = new nt(e, 0, !1, e, null, !1, !1);
  });
[
  ["acceptCharset", "accept-charset"],
  ["className", "class"],
  ["htmlFor", "for"],
  ["httpEquiv", "http-equiv"],
].forEach(function (e) {
  var t = e[0];
  Be[t] = new nt(t, 1, !1, e[1], null, !1, !1);
});
["contentEditable", "draggable", "spellCheck", "value"].forEach(function (e) {
  Be[e] = new nt(e, 2, !1, e.toLowerCase(), null, !1, !1);
});
["autoReverse", "externalResourcesRequired", "focusable", "preserveAlpha"].forEach(function (e) {
  Be[e] = new nt(e, 2, !1, e, null, !1, !1);
});
"allowFullScreen async autoFocus autoPlay controls default defer disabled disablePictureInPicture disableRemotePlayback formNoValidate hidden loop noModule noValidate open playsInline readOnly required reversed scoped seamless itemScope"
  .split(" ")
  .forEach(function (e) {
    Be[e] = new nt(e, 3, !1, e.toLowerCase(), null, !1, !1);
  });
["checked", "multiple", "muted", "selected"].forEach(function (e) {
  Be[e] = new nt(e, 3, !0, e, null, !1, !1);
});
["capture", "download"].forEach(function (e) {
  Be[e] = new nt(e, 4, !1, e, null, !1, !1);
});
["cols", "rows", "size", "span"].forEach(function (e) {
  Be[e] = new nt(e, 6, !1, e, null, !1, !1);
});
["rowSpan", "start"].forEach(function (e) {
  Be[e] = new nt(e, 5, !1, e.toLowerCase(), null, !1, !1);
});
var vd = /[\-:]([a-z])/g;
function xd(e) {
  return e[1].toUpperCase();
}
"accent-height alignment-baseline arabic-form baseline-shift cap-height clip-path clip-rule color-interpolation color-interpolation-filters color-profile color-rendering dominant-baseline enable-background fill-opacity fill-rule flood-color flood-opacity font-family font-size font-size-adjust font-stretch font-style font-variant font-weight glyph-name glyph-orientation-horizontal glyph-orientation-vertical horiz-adv-x horiz-origin-x image-rendering letter-spacing lighting-color marker-end marker-mid marker-start overline-position overline-thickness paint-order panose-1 pointer-events rendering-intent shape-rendering stop-color stop-opacity strikethrough-position strikethrough-thickness stroke-dasharray stroke-dashoffset stroke-linecap stroke-linejoin stroke-miterlimit stroke-opacity stroke-width text-anchor text-decoration text-rendering underline-position underline-thickness unicode-bidi unicode-range units-per-em v-alphabetic v-hanging v-ideographic v-mathematical vector-effect vert-adv-y vert-origin-x vert-origin-y word-spacing writing-mode xmlns:xlink x-height"
  .split(" ")
  .forEach(function (e) {
    var t = e.replace(vd, xd);
    Be[t] = new nt(t, 1, !1, e, null, !1, !1);
  });
"xlink:actuate xlink:arcrole xlink:role xlink:show xlink:title xlink:type"
  .split(" ")
  .forEach(function (e) {
    var t = e.replace(vd, xd);
    Be[t] = new nt(t, 1, !1, e, "http://www.w3.org/1999/xlink", !1, !1);
  });
["xml:base", "xml:lang", "xml:space"].forEach(function (e) {
  var t = e.replace(vd, xd);
  Be[t] = new nt(t, 1, !1, e, "http://www.w3.org/XML/1998/namespace", !1, !1);
});
["tabIndex", "crossOrigin"].forEach(function (e) {
  Be[e] = new nt(e, 1, !1, e.toLowerCase(), null, !1, !1);
});
Be.xlinkHref = new nt("xlinkHref", 1, !1, "xlink:href", "http://www.w3.org/1999/xlink", !0, !1);
["src", "href", "action", "formAction"].forEach(function (e) {
  Be[e] = new nt(e, 1, !1, e.toLowerCase(), null, !0, !0);
});
function wd(e, t, n, r) {
  var o = Be.hasOwnProperty(t) ? Be[t] : null;
  (o !== null
    ? o.type !== 0
    : r || !(2 < t.length) || (t[0] !== "o" && t[0] !== "O") || (t[1] !== "n" && t[1] !== "N")) &&
    (rb(t, n, o, r) && (n = null),
    r || o === null
      ? tb(t) && (n === null ? e.removeAttribute(t) : e.setAttribute(t, "" + n))
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
var Tn = JC.__SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED,
  $s = Symbol.for("react.element"),
  qr = Symbol.for("react.portal"),
  Jr = Symbol.for("react.fragment"),
  Sd = Symbol.for("react.strict_mode"),
  Oc = Symbol.for("react.profiler"),
  w0 = Symbol.for("react.provider"),
  S0 = Symbol.for("react.context"),
  Ed = Symbol.for("react.forward_ref"),
  jc = Symbol.for("react.suspense"),
  Fc = Symbol.for("react.suspense_list"),
  Cd = Symbol.for("react.memo"),
  In = Symbol.for("react.lazy"),
  E0 = Symbol.for("react.offscreen"),
  Cp = Symbol.iterator;
function ti(e) {
  return e === null || typeof e != "object"
    ? null
    : ((e = (Cp && e[Cp]) || e["@@iterator"]), typeof e == "function" ? e : null);
}
var Ee = Object.assign,
  Mu;
function yi(e) {
  if (Mu === void 0)
    try {
      throw Error();
    } catch (n) {
      var t = n.stack.trim().match(/\n( *(at )?)/);
      Mu = (t && t[1]) || "";
    }
  return (
    `
` +
    Mu +
    e
  );
}
var Au = !1;
function Ru(e, t) {
  if (!e || Au) return "";
  Au = !0;
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
    (Au = !1), (Error.prepareStackTrace = n);
  }
  return (e = e ? e.displayName || e.name : "") ? yi(e) : "";
}
function ob(e) {
  switch (e.tag) {
    case 5:
      return yi(e.type);
    case 16:
      return yi("Lazy");
    case 13:
      return yi("Suspense");
    case 19:
      return yi("SuspenseList");
    case 0:
    case 2:
    case 15:
      return (e = Ru(e.type, !1)), e;
    case 11:
      return (e = Ru(e.type.render, !1)), e;
    case 1:
      return (e = Ru(e.type, !0)), e;
    default:
      return "";
  }
}
function zc(e) {
  if (e == null) return null;
  if (typeof e == "function") return e.displayName || e.name || null;
  if (typeof e == "string") return e;
  switch (e) {
    case Jr:
      return "Fragment";
    case qr:
      return "Portal";
    case Oc:
      return "Profiler";
    case Sd:
      return "StrictMode";
    case jc:
      return "Suspense";
    case Fc:
      return "SuspenseList";
  }
  if (typeof e == "object")
    switch (e.$$typeof) {
      case S0:
        return (e.displayName || "Context") + ".Consumer";
      case w0:
        return (e._context.displayName || "Context") + ".Provider";
      case Ed:
        var t = e.render;
        return (
          (e = e.displayName),
          e ||
            ((e = t.displayName || t.name || ""),
            (e = e !== "" ? "ForwardRef(" + e + ")" : "ForwardRef")),
          e
        );
      case Cd:
        return (t = e.displayName || null), t !== null ? t : zc(e.type) || "Memo";
      case In:
        (t = e._payload), (e = e._init);
        try {
          return zc(e(t));
        } catch {}
    }
  return null;
}
function ib(e) {
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
      return zc(t);
    case 8:
      return t === Sd ? "StrictMode" : "Mode";
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
function C0(e) {
  var t = e.type;
  return (e = e.nodeName) && e.toLowerCase() === "input" && (t === "checkbox" || t === "radio");
}
function sb(e) {
  var t = C0(e) ? "checked" : "value",
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
function Bs(e) {
  e._valueTracker || (e._valueTracker = sb(e));
}
function b0(e) {
  if (!e) return !1;
  var t = e._valueTracker;
  if (!t) return !0;
  var n = t.getValue(),
    r = "";
  return (
    e && (r = C0(e) ? (e.checked ? "true" : "false") : e.value),
    (e = r),
    e !== n ? (t.setValue(e), !0) : !1
  );
}
function Ka(e) {
  if (((e = e || (typeof document < "u" ? document : void 0)), typeof e > "u")) return null;
  try {
    return e.activeElement || e.body;
  } catch {
    return e.body;
  }
}
function $c(e, t) {
  var n = t.checked;
  return Ee({}, t, {
    defaultChecked: void 0,
    defaultValue: void 0,
    value: void 0,
    checked: n ?? e._wrapperState.initialChecked,
  });
}
function bp(e, t) {
  var n = t.defaultValue == null ? "" : t.defaultValue,
    r = t.checked != null ? t.checked : t.defaultChecked;
  (n = Qn(t.value != null ? t.value : n)),
    (e._wrapperState = {
      initialChecked: r,
      initialValue: n,
      controlled: t.type === "checkbox" || t.type === "radio" ? t.checked != null : t.value != null,
    });
}
function k0(e, t) {
  (t = t.checked), t != null && wd(e, "checked", t, !1);
}
function Bc(e, t) {
  k0(e, t);
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
    ? Hc(e, t.type, n)
    : t.hasOwnProperty("defaultValue") && Hc(e, t.type, Qn(t.defaultValue)),
    t.checked == null && t.defaultChecked != null && (e.defaultChecked = !!t.defaultChecked);
}
function kp(e, t, n) {
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
function Hc(e, t, n) {
  (t !== "number" || Ka(e.ownerDocument) !== e) &&
    (n == null
      ? (e.defaultValue = "" + e._wrapperState.initialValue)
      : e.defaultValue !== "" + n && (e.defaultValue = "" + n));
}
var vi = Array.isArray;
function vo(e, t, n, r) {
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
function Uc(e, t) {
  if (t.dangerouslySetInnerHTML != null) throw Error(B(91));
  return Ee({}, t, {
    value: void 0,
    defaultValue: void 0,
    children: "" + e._wrapperState.initialValue,
  });
}
function Tp(e, t) {
  var n = t.value;
  if (n == null) {
    if (((n = t.children), (t = t.defaultValue), n != null)) {
      if (t != null) throw Error(B(92));
      if (vi(n)) {
        if (1 < n.length) throw Error(B(93));
        n = n[0];
      }
      t = n;
    }
    t == null && (t = ""), (n = t);
  }
  e._wrapperState = { initialValue: Qn(n) };
}
function T0(e, t) {
  var n = Qn(t.value),
    r = Qn(t.defaultValue);
  n != null &&
    ((n = "" + n),
    n !== e.value && (e.value = n),
    t.defaultValue == null && e.defaultValue !== n && (e.defaultValue = n)),
    r != null && (e.defaultValue = "" + r);
}
function _p(e) {
  var t = e.textContent;
  t === e._wrapperState.initialValue && t !== "" && t !== null && (e.value = t);
}
function _0(e) {
  switch (e) {
    case "svg":
      return "http://www.w3.org/2000/svg";
    case "math":
      return "http://www.w3.org/1998/Math/MathML";
    default:
      return "http://www.w3.org/1999/xhtml";
  }
}
function Wc(e, t) {
  return e == null || e === "http://www.w3.org/1999/xhtml"
    ? _0(t)
    : e === "http://www.w3.org/2000/svg" && t === "foreignObject"
      ? "http://www.w3.org/1999/xhtml"
      : e;
}
var Hs,
  N0 = (function (e) {
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
        Hs = Hs || document.createElement("div"),
          Hs.innerHTML = "<svg>" + t.valueOf().toString() + "</svg>",
          t = Hs.firstChild;
        e.firstChild;

      )
        e.removeChild(e.firstChild);
      for (; t.firstChild; ) e.appendChild(t.firstChild);
    }
  });
function Hi(e, t) {
  if (t) {
    var n = e.firstChild;
    if (n && n === e.lastChild && n.nodeType === 3) {
      n.nodeValue = t;
      return;
    }
  }
  e.textContent = t;
}
var _i = {
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
  ab = ["Webkit", "ms", "Moz", "O"];
Object.keys(_i).forEach(function (e) {
  ab.forEach(function (t) {
    (t = t + e.charAt(0).toUpperCase() + e.substring(1)), (_i[t] = _i[e]);
  });
});
function P0(e, t, n) {
  return t == null || typeof t == "boolean" || t === ""
    ? ""
    : n || typeof t != "number" || t === 0 || (_i.hasOwnProperty(e) && _i[e])
      ? ("" + t).trim()
      : t + "px";
}
function M0(e, t) {
  e = e.style;
  for (var n in t)
    if (t.hasOwnProperty(n)) {
      var r = n.indexOf("--") === 0,
        o = P0(n, t[n], r);
      n === "float" && (n = "cssFloat"), r ? e.setProperty(n, o) : (e[n] = o);
    }
}
var lb = Ee(
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
function Gc(e, t) {
  if (t) {
    if (lb[e] && (t.children != null || t.dangerouslySetInnerHTML != null)) throw Error(B(137, e));
    if (t.dangerouslySetInnerHTML != null) {
      if (t.children != null) throw Error(B(60));
      if (typeof t.dangerouslySetInnerHTML != "object" || !("__html" in t.dangerouslySetInnerHTML))
        throw Error(B(61));
    }
    if (t.style != null && typeof t.style != "object") throw Error(B(62));
  }
}
function Kc(e, t) {
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
var Yc = null;
function bd(e) {
  return (
    (e = e.target || e.srcElement || window),
    e.correspondingUseElement && (e = e.correspondingUseElement),
    e.nodeType === 3 ? e.parentNode : e
  );
}
var Xc = null,
  xo = null,
  wo = null;
function Np(e) {
  if ((e = ks(e))) {
    if (typeof Xc != "function") throw Error(B(280));
    var t = e.stateNode;
    t && ((t = Ul(t)), Xc(e.stateNode, e.type, t));
  }
}
function A0(e) {
  xo ? (wo ? wo.push(e) : (wo = [e])) : (xo = e);
}
function R0() {
  if (xo) {
    var e = xo,
      t = wo;
    if (((wo = xo = null), Np(e), t)) for (e = 0; e < t.length; e++) Np(t[e]);
  }
}
function D0(e, t) {
  return e(t);
}
function I0() {}
var Du = !1;
function L0(e, t, n) {
  if (Du) return e(t, n);
  Du = !0;
  try {
    return D0(e, t, n);
  } finally {
    (Du = !1), (xo !== null || wo !== null) && (I0(), R0());
  }
}
function Ui(e, t) {
  var n = e.stateNode;
  if (n === null) return null;
  var r = Ul(n);
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
var Zc = !1;
if (vn)
  try {
    var ni = {};
    Object.defineProperty(ni, "passive", {
      get: function () {
        Zc = !0;
      },
    }),
      window.addEventListener("test", ni, ni),
      window.removeEventListener("test", ni, ni);
  } catch {
    Zc = !1;
  }
function ub(e, t, n, r, o, i, s, a, l) {
  var u = Array.prototype.slice.call(arguments, 3);
  try {
    t.apply(n, u);
  } catch (c) {
    this.onError(c);
  }
}
var Ni = !1,
  Ya = null,
  Xa = !1,
  Qc = null,
  cb = {
    onError: function (e) {
      (Ni = !0), (Ya = e);
    },
  };
function fb(e, t, n, r, o, i, s, a, l) {
  (Ni = !1), (Ya = null), ub.apply(cb, arguments);
}
function db(e, t, n, r, o, i, s, a, l) {
  if ((fb.apply(this, arguments), Ni)) {
    if (Ni) {
      var u = Ya;
      (Ni = !1), (Ya = null);
    } else throw Error(B(198));
    Xa || ((Xa = !0), (Qc = u));
  }
}
function Or(e) {
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
function V0(e) {
  if (e.tag === 13) {
    var t = e.memoizedState;
    if ((t === null && ((e = e.alternate), e !== null && (t = e.memoizedState)), t !== null))
      return t.dehydrated;
  }
  return null;
}
function Pp(e) {
  if (Or(e) !== e) throw Error(B(188));
}
function hb(e) {
  var t = e.alternate;
  if (!t) {
    if (((t = Or(e)), t === null)) throw Error(B(188));
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
        if (i === n) return Pp(o), e;
        if (i === r) return Pp(o), t;
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
function O0(e) {
  return (e = hb(e)), e !== null ? j0(e) : null;
}
function j0(e) {
  if (e.tag === 5 || e.tag === 6) return e;
  for (e = e.child; e !== null; ) {
    var t = j0(e);
    if (t !== null) return t;
    e = e.sibling;
  }
  return null;
}
var F0 = pt.unstable_scheduleCallback,
  Mp = pt.unstable_cancelCallback,
  pb = pt.unstable_shouldYield,
  mb = pt.unstable_requestPaint,
  Ne = pt.unstable_now,
  gb = pt.unstable_getCurrentPriorityLevel,
  kd = pt.unstable_ImmediatePriority,
  z0 = pt.unstable_UserBlockingPriority,
  Za = pt.unstable_NormalPriority,
  yb = pt.unstable_LowPriority,
  $0 = pt.unstable_IdlePriority,
  zl = null,
  Xt = null;
function vb(e) {
  if (Xt && typeof Xt.onCommitFiberRoot == "function")
    try {
      Xt.onCommitFiberRoot(zl, e, void 0, (e.current.flags & 128) === 128);
    } catch {}
}
var Ot = Math.clz32 ? Math.clz32 : Sb,
  xb = Math.log,
  wb = Math.LN2;
function Sb(e) {
  return (e >>>= 0), e === 0 ? 32 : (31 - ((xb(e) / wb) | 0)) | 0;
}
var Us = 64,
  Ws = 4194304;
function xi(e) {
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
function Qa(e, t) {
  var n = e.pendingLanes;
  if (n === 0) return 0;
  var r = 0,
    o = e.suspendedLanes,
    i = e.pingedLanes,
    s = n & 268435455;
  if (s !== 0) {
    var a = s & ~o;
    a !== 0 ? (r = xi(a)) : ((i &= s), i !== 0 && (r = xi(i)));
  } else (s = n & ~o), s !== 0 ? (r = xi(s)) : i !== 0 && (r = xi(i));
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
function Eb(e, t) {
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
function Cb(e, t) {
  for (
    var n = e.suspendedLanes, r = e.pingedLanes, o = e.expirationTimes, i = e.pendingLanes;
    0 < i;

  ) {
    var s = 31 - Ot(i),
      a = 1 << s,
      l = o[s];
    l === -1 ? (!(a & n) || a & r) && (o[s] = Eb(a, t)) : l <= t && (e.expiredLanes |= a),
      (i &= ~a);
  }
}
function qc(e) {
  return (e = e.pendingLanes & -1073741825), e !== 0 ? e : e & 1073741824 ? 1073741824 : 0;
}
function B0() {
  var e = Us;
  return (Us <<= 1), !(Us & 4194240) && (Us = 64), e;
}
function Iu(e) {
  for (var t = [], n = 0; 31 > n; n++) t.push(e);
  return t;
}
function Cs(e, t, n) {
  (e.pendingLanes |= t),
    t !== 536870912 && ((e.suspendedLanes = 0), (e.pingedLanes = 0)),
    (e = e.eventTimes),
    (t = 31 - Ot(t)),
    (e[t] = n);
}
function bb(e, t) {
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
function Td(e, t) {
  var n = (e.entangledLanes |= t);
  for (e = e.entanglements; n; ) {
    var r = 31 - Ot(n),
      o = 1 << r;
    (o & t) | (e[r] & t) && (e[r] |= t), (n &= ~o);
  }
}
var le = 0;
function H0(e) {
  return (e &= -e), 1 < e ? (4 < e ? (e & 268435455 ? 16 : 536870912) : 4) : 1;
}
var U0,
  _d,
  W0,
  G0,
  K0,
  Jc = !1,
  Gs = [],
  Bn = null,
  Hn = null,
  Un = null,
  Wi = new Map(),
  Gi = new Map(),
  jn = [],
  kb =
    "mousedown mouseup touchcancel touchend touchstart auxclick dblclick pointercancel pointerdown pointerup dragend dragstart drop compositionend compositionstart keydown keypress keyup input textInput copy cut paste click change contextmenu reset submit".split(
      " ",
    );
function Ap(e, t) {
  switch (e) {
    case "focusin":
    case "focusout":
      Bn = null;
      break;
    case "dragenter":
    case "dragleave":
      Hn = null;
      break;
    case "mouseover":
    case "mouseout":
      Un = null;
      break;
    case "pointerover":
    case "pointerout":
      Wi.delete(t.pointerId);
      break;
    case "gotpointercapture":
    case "lostpointercapture":
      Gi.delete(t.pointerId);
  }
}
function ri(e, t, n, r, o, i) {
  return e === null || e.nativeEvent !== i
    ? ((e = {
        blockedOn: t,
        domEventName: n,
        eventSystemFlags: r,
        nativeEvent: i,
        targetContainers: [o],
      }),
      t !== null && ((t = ks(t)), t !== null && _d(t)),
      e)
    : ((e.eventSystemFlags |= r),
      (t = e.targetContainers),
      o !== null && t.indexOf(o) === -1 && t.push(o),
      e);
}
function Tb(e, t, n, r, o) {
  switch (t) {
    case "focusin":
      return (Bn = ri(Bn, e, t, n, r, o)), !0;
    case "dragenter":
      return (Hn = ri(Hn, e, t, n, r, o)), !0;
    case "mouseover":
      return (Un = ri(Un, e, t, n, r, o)), !0;
    case "pointerover":
      var i = o.pointerId;
      return Wi.set(i, ri(Wi.get(i) || null, e, t, n, r, o)), !0;
    case "gotpointercapture":
      return (i = o.pointerId), Gi.set(i, ri(Gi.get(i) || null, e, t, n, r, o)), !0;
  }
  return !1;
}
function Y0(e) {
  var t = yr(e.target);
  if (t !== null) {
    var n = Or(t);
    if (n !== null) {
      if (((t = n.tag), t === 13)) {
        if (((t = V0(n)), t !== null)) {
          (e.blockedOn = t),
            K0(e.priority, function () {
              W0(n);
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
function ba(e) {
  if (e.blockedOn !== null) return !1;
  for (var t = e.targetContainers; 0 < t.length; ) {
    var n = ef(e.domEventName, e.eventSystemFlags, t[0], e.nativeEvent);
    if (n === null) {
      n = e.nativeEvent;
      var r = new n.constructor(n.type, n);
      (Yc = r), n.target.dispatchEvent(r), (Yc = null);
    } else return (t = ks(n)), t !== null && _d(t), (e.blockedOn = n), !1;
    t.shift();
  }
  return !0;
}
function Rp(e, t, n) {
  ba(e) && n.delete(t);
}
function _b() {
  (Jc = !1),
    Bn !== null && ba(Bn) && (Bn = null),
    Hn !== null && ba(Hn) && (Hn = null),
    Un !== null && ba(Un) && (Un = null),
    Wi.forEach(Rp),
    Gi.forEach(Rp);
}
function oi(e, t) {
  e.blockedOn === t &&
    ((e.blockedOn = null),
    Jc || ((Jc = !0), pt.unstable_scheduleCallback(pt.unstable_NormalPriority, _b)));
}
function Ki(e) {
  function t(o) {
    return oi(o, e);
  }
  if (0 < Gs.length) {
    oi(Gs[0], e);
    for (var n = 1; n < Gs.length; n++) {
      var r = Gs[n];
      r.blockedOn === e && (r.blockedOn = null);
    }
  }
  for (
    Bn !== null && oi(Bn, e),
      Hn !== null && oi(Hn, e),
      Un !== null && oi(Un, e),
      Wi.forEach(t),
      Gi.forEach(t),
      n = 0;
    n < jn.length;
    n++
  )
    (r = jn[n]), r.blockedOn === e && (r.blockedOn = null);
  for (; 0 < jn.length && ((n = jn[0]), n.blockedOn === null); )
    Y0(n), n.blockedOn === null && jn.shift();
}
var So = Tn.ReactCurrentBatchConfig,
  qa = !0;
function Nb(e, t, n, r) {
  var o = le,
    i = So.transition;
  So.transition = null;
  try {
    (le = 1), Nd(e, t, n, r);
  } finally {
    (le = o), (So.transition = i);
  }
}
function Pb(e, t, n, r) {
  var o = le,
    i = So.transition;
  So.transition = null;
  try {
    (le = 4), Nd(e, t, n, r);
  } finally {
    (le = o), (So.transition = i);
  }
}
function Nd(e, t, n, r) {
  if (qa) {
    var o = ef(e, t, n, r);
    if (o === null) Uu(e, t, r, Ja, n), Ap(e, r);
    else if (Tb(o, e, t, n, r)) r.stopPropagation();
    else if ((Ap(e, r), t & 4 && -1 < kb.indexOf(e))) {
      for (; o !== null; ) {
        var i = ks(o);
        if ((i !== null && U0(i), (i = ef(e, t, n, r)), i === null && Uu(e, t, r, Ja, n), i === o))
          break;
        o = i;
      }
      o !== null && r.stopPropagation();
    } else Uu(e, t, r, null, n);
  }
}
var Ja = null;
function ef(e, t, n, r) {
  if (((Ja = null), (e = bd(r)), (e = yr(e)), e !== null))
    if (((t = Or(e)), t === null)) e = null;
    else if (((n = t.tag), n === 13)) {
      if (((e = V0(t)), e !== null)) return e;
      e = null;
    } else if (n === 3) {
      if (t.stateNode.current.memoizedState.isDehydrated)
        return t.tag === 3 ? t.stateNode.containerInfo : null;
      e = null;
    } else t !== e && (e = null);
  return (Ja = e), null;
}
function X0(e) {
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
      switch (gb()) {
        case kd:
          return 1;
        case z0:
          return 4;
        case Za:
        case yb:
          return 16;
        case $0:
          return 536870912;
        default:
          return 16;
      }
    default:
      return 16;
  }
}
var zn = null,
  Pd = null,
  ka = null;
function Z0() {
  if (ka) return ka;
  var e,
    t = Pd,
    n = t.length,
    r,
    o = "value" in zn ? zn.value : zn.textContent,
    i = o.length;
  for (e = 0; e < n && t[e] === o[e]; e++);
  var s = n - e;
  for (r = 1; r <= s && t[n - r] === o[i - r]; r++);
  return (ka = o.slice(e, 1 < r ? 1 - r : void 0));
}
function Ta(e) {
  var t = e.keyCode;
  return (
    "charCode" in e ? ((e = e.charCode), e === 0 && t === 13 && (e = 13)) : (e = t),
    e === 10 && (e = 13),
    32 <= e || e === 13 ? e : 0
  );
}
function Ks() {
  return !0;
}
function Dp() {
  return !1;
}
function vt(e) {
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
        ? Ks
        : Dp),
      (this.isPropagationStopped = Dp),
      this
    );
  }
  return (
    Ee(t.prototype, {
      preventDefault: function () {
        this.defaultPrevented = !0;
        var n = this.nativeEvent;
        n &&
          (n.preventDefault
            ? n.preventDefault()
            : typeof n.returnValue != "unknown" && (n.returnValue = !1),
          (this.isDefaultPrevented = Ks));
      },
      stopPropagation: function () {
        var n = this.nativeEvent;
        n &&
          (n.stopPropagation
            ? n.stopPropagation()
            : typeof n.cancelBubble != "unknown" && (n.cancelBubble = !0),
          (this.isPropagationStopped = Ks));
      },
      persist: function () {},
      isPersistent: Ks,
    }),
    t
  );
}
var Go = {
    eventPhase: 0,
    bubbles: 0,
    cancelable: 0,
    timeStamp: function (e) {
      return e.timeStamp || Date.now();
    },
    defaultPrevented: 0,
    isTrusted: 0,
  },
  Md = vt(Go),
  bs = Ee({}, Go, { view: 0, detail: 0 }),
  Mb = vt(bs),
  Lu,
  Vu,
  ii,
  $l = Ee({}, bs, {
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
    getModifierState: Ad,
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
        : (e !== ii &&
            (ii && e.type === "mousemove"
              ? ((Lu = e.screenX - ii.screenX), (Vu = e.screenY - ii.screenY))
              : (Vu = Lu = 0),
            (ii = e)),
          Lu);
    },
    movementY: function (e) {
      return "movementY" in e ? e.movementY : Vu;
    },
  }),
  Ip = vt($l),
  Ab = Ee({}, $l, { dataTransfer: 0 }),
  Rb = vt(Ab),
  Db = Ee({}, bs, { relatedTarget: 0 }),
  Ou = vt(Db),
  Ib = Ee({}, Go, { animationName: 0, elapsedTime: 0, pseudoElement: 0 }),
  Lb = vt(Ib),
  Vb = Ee({}, Go, {
    clipboardData: function (e) {
      return "clipboardData" in e ? e.clipboardData : window.clipboardData;
    },
  }),
  Ob = vt(Vb),
  jb = Ee({}, Go, { data: 0 }),
  Lp = vt(jb),
  Fb = {
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
  zb = {
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
  $b = { Alt: "altKey", Control: "ctrlKey", Meta: "metaKey", Shift: "shiftKey" };
function Bb(e) {
  var t = this.nativeEvent;
  return t.getModifierState ? t.getModifierState(e) : (e = $b[e]) ? !!t[e] : !1;
}
function Ad() {
  return Bb;
}
var Hb = Ee({}, bs, {
    key: function (e) {
      if (e.key) {
        var t = Fb[e.key] || e.key;
        if (t !== "Unidentified") return t;
      }
      return e.type === "keypress"
        ? ((e = Ta(e)), e === 13 ? "Enter" : String.fromCharCode(e))
        : e.type === "keydown" || e.type === "keyup"
          ? zb[e.keyCode] || "Unidentified"
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
    getModifierState: Ad,
    charCode: function (e) {
      return e.type === "keypress" ? Ta(e) : 0;
    },
    keyCode: function (e) {
      return e.type === "keydown" || e.type === "keyup" ? e.keyCode : 0;
    },
    which: function (e) {
      return e.type === "keypress"
        ? Ta(e)
        : e.type === "keydown" || e.type === "keyup"
          ? e.keyCode
          : 0;
    },
  }),
  Ub = vt(Hb),
  Wb = Ee({}, $l, {
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
  Vp = vt(Wb),
  Gb = Ee({}, bs, {
    touches: 0,
    targetTouches: 0,
    changedTouches: 0,
    altKey: 0,
    metaKey: 0,
    ctrlKey: 0,
    shiftKey: 0,
    getModifierState: Ad,
  }),
  Kb = vt(Gb),
  Yb = Ee({}, Go, { propertyName: 0, elapsedTime: 0, pseudoElement: 0 }),
  Xb = vt(Yb),
  Zb = Ee({}, $l, {
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
  Qb = vt(Zb),
  qb = [9, 13, 27, 32],
  Rd = vn && "CompositionEvent" in window,
  Pi = null;
vn && "documentMode" in document && (Pi = document.documentMode);
var Jb = vn && "TextEvent" in window && !Pi,
  Q0 = vn && (!Rd || (Pi && 8 < Pi && 11 >= Pi)),
  Op = " ",
  jp = !1;
function q0(e, t) {
  switch (e) {
    case "keyup":
      return qb.indexOf(t.keyCode) !== -1;
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
function J0(e) {
  return (e = e.detail), typeof e == "object" && "data" in e ? e.data : null;
}
var eo = !1;
function e2(e, t) {
  switch (e) {
    case "compositionend":
      return J0(t);
    case "keypress":
      return t.which !== 32 ? null : ((jp = !0), Op);
    case "textInput":
      return (e = t.data), e === Op && jp ? null : e;
    default:
      return null;
  }
}
function t2(e, t) {
  if (eo)
    return e === "compositionend" || (!Rd && q0(e, t))
      ? ((e = Z0()), (ka = Pd = zn = null), (eo = !1), e)
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
      return Q0 && t.locale !== "ko" ? null : t.data;
    default:
      return null;
  }
}
var n2 = {
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
function Fp(e) {
  var t = e && e.nodeName && e.nodeName.toLowerCase();
  return t === "input" ? !!n2[e.type] : t === "textarea";
}
function ev(e, t, n, r) {
  A0(r),
    (t = el(t, "onChange")),
    0 < t.length &&
      ((n = new Md("onChange", "change", null, n, r)), e.push({ event: n, listeners: t }));
}
var Mi = null,
  Yi = null;
function r2(e) {
  fv(e, 0);
}
function Bl(e) {
  var t = ro(e);
  if (b0(t)) return e;
}
function o2(e, t) {
  if (e === "change") return t;
}
var tv = !1;
if (vn) {
  var ju;
  if (vn) {
    var Fu = "oninput" in document;
    if (!Fu) {
      var zp = document.createElement("div");
      zp.setAttribute("oninput", "return;"), (Fu = typeof zp.oninput == "function");
    }
    ju = Fu;
  } else ju = !1;
  tv = ju && (!document.documentMode || 9 < document.documentMode);
}
function $p() {
  Mi && (Mi.detachEvent("onpropertychange", nv), (Yi = Mi = null));
}
function nv(e) {
  if (e.propertyName === "value" && Bl(Yi)) {
    var t = [];
    ev(t, Yi, e, bd(e)), L0(r2, t);
  }
}
function i2(e, t, n) {
  e === "focusin"
    ? ($p(), (Mi = t), (Yi = n), Mi.attachEvent("onpropertychange", nv))
    : e === "focusout" && $p();
}
function s2(e) {
  if (e === "selectionchange" || e === "keyup" || e === "keydown") return Bl(Yi);
}
function a2(e, t) {
  if (e === "click") return Bl(t);
}
function l2(e, t) {
  if (e === "input" || e === "change") return Bl(t);
}
function u2(e, t) {
  return (e === t && (e !== 0 || 1 / e === 1 / t)) || (e !== e && t !== t);
}
var zt = typeof Object.is == "function" ? Object.is : u2;
function Xi(e, t) {
  if (zt(e, t)) return !0;
  if (typeof e != "object" || e === null || typeof t != "object" || t === null) return !1;
  var n = Object.keys(e),
    r = Object.keys(t);
  if (n.length !== r.length) return !1;
  for (r = 0; r < n.length; r++) {
    var o = n[r];
    if (!Vc.call(t, o) || !zt(e[o], t[o])) return !1;
  }
  return !0;
}
function Bp(e) {
  for (; e && e.firstChild; ) e = e.firstChild;
  return e;
}
function Hp(e, t) {
  var n = Bp(e);
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
    n = Bp(n);
  }
}
function rv(e, t) {
  return e && t
    ? e === t
      ? !0
      : e && e.nodeType === 3
        ? !1
        : t && t.nodeType === 3
          ? rv(e, t.parentNode)
          : "contains" in e
            ? e.contains(t)
            : e.compareDocumentPosition
              ? !!(e.compareDocumentPosition(t) & 16)
              : !1
    : !1;
}
function ov() {
  for (var e = window, t = Ka(); t instanceof e.HTMLIFrameElement; ) {
    try {
      var n = typeof t.contentWindow.location.href == "string";
    } catch {
      n = !1;
    }
    if (n) e = t.contentWindow;
    else break;
    t = Ka(e.document);
  }
  return t;
}
function Dd(e) {
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
function c2(e) {
  var t = ov(),
    n = e.focusedElem,
    r = e.selectionRange;
  if (t !== n && n && n.ownerDocument && rv(n.ownerDocument.documentElement, n)) {
    if (r !== null && Dd(n)) {
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
          (o = Hp(n, i));
        var s = Hp(n, r);
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
var f2 = vn && "documentMode" in document && 11 >= document.documentMode,
  to = null,
  tf = null,
  Ai = null,
  nf = !1;
function Up(e, t, n) {
  var r = n.window === n ? n.document : n.nodeType === 9 ? n : n.ownerDocument;
  nf ||
    to == null ||
    to !== Ka(r) ||
    ((r = to),
    "selectionStart" in r && Dd(r)
      ? (r = { start: r.selectionStart, end: r.selectionEnd })
      : ((r = ((r.ownerDocument && r.ownerDocument.defaultView) || window).getSelection()),
        (r = {
          anchorNode: r.anchorNode,
          anchorOffset: r.anchorOffset,
          focusNode: r.focusNode,
          focusOffset: r.focusOffset,
        })),
    (Ai && Xi(Ai, r)) ||
      ((Ai = r),
      (r = el(tf, "onSelect")),
      0 < r.length &&
        ((t = new Md("onSelect", "select", null, t, n)),
        e.push({ event: t, listeners: r }),
        (t.target = to))));
}
function Ys(e, t) {
  var n = {};
  return (
    (n[e.toLowerCase()] = t.toLowerCase()),
    (n["Webkit" + e] = "webkit" + t),
    (n["Moz" + e] = "moz" + t),
    n
  );
}
var no = {
    animationend: Ys("Animation", "AnimationEnd"),
    animationiteration: Ys("Animation", "AnimationIteration"),
    animationstart: Ys("Animation", "AnimationStart"),
    transitionend: Ys("Transition", "TransitionEnd"),
  },
  zu = {},
  iv = {};
vn &&
  ((iv = document.createElement("div").style),
  "AnimationEvent" in window ||
    (delete no.animationend.animation,
    delete no.animationiteration.animation,
    delete no.animationstart.animation),
  "TransitionEvent" in window || delete no.transitionend.transition);
function Hl(e) {
  if (zu[e]) return zu[e];
  if (!no[e]) return e;
  var t = no[e],
    n;
  for (n in t) if (t.hasOwnProperty(n) && n in iv) return (zu[e] = t[n]);
  return e;
}
var sv = Hl("animationend"),
  av = Hl("animationiteration"),
  lv = Hl("animationstart"),
  uv = Hl("transitionend"),
  cv = new Map(),
  Wp =
    "abort auxClick cancel canPlay canPlayThrough click close contextMenu copy cut drag dragEnd dragEnter dragExit dragLeave dragOver dragStart drop durationChange emptied encrypted ended error gotPointerCapture input invalid keyDown keyPress keyUp load loadedData loadedMetadata loadStart lostPointerCapture mouseDown mouseMove mouseOut mouseOver mouseUp paste pause play playing pointerCancel pointerDown pointerMove pointerOut pointerOver pointerUp progress rateChange reset resize seeked seeking stalled submit suspend timeUpdate touchCancel touchEnd touchStart volumeChange scroll toggle touchMove waiting wheel".split(
      " ",
    );
function er(e, t) {
  cv.set(e, t), Vr(t, [e]);
}
for (var $u = 0; $u < Wp.length; $u++) {
  var Bu = Wp[$u],
    d2 = Bu.toLowerCase(),
    h2 = Bu[0].toUpperCase() + Bu.slice(1);
  er(d2, "on" + h2);
}
er(sv, "onAnimationEnd");
er(av, "onAnimationIteration");
er(lv, "onAnimationStart");
er("dblclick", "onDoubleClick");
er("focusin", "onFocus");
er("focusout", "onBlur");
er(uv, "onTransitionEnd");
Po("onMouseEnter", ["mouseout", "mouseover"]);
Po("onMouseLeave", ["mouseout", "mouseover"]);
Po("onPointerEnter", ["pointerout", "pointerover"]);
Po("onPointerLeave", ["pointerout", "pointerover"]);
Vr("onChange", "change click focusin focusout input keydown keyup selectionchange".split(" "));
Vr(
  "onSelect",
  "focusout contextmenu dragend focusin keydown keyup mousedown mouseup selectionchange".split(" "),
);
Vr("onBeforeInput", ["compositionend", "keypress", "textInput", "paste"]);
Vr("onCompositionEnd", "compositionend focusout keydown keypress keyup mousedown".split(" "));
Vr("onCompositionStart", "compositionstart focusout keydown keypress keyup mousedown".split(" "));
Vr("onCompositionUpdate", "compositionupdate focusout keydown keypress keyup mousedown".split(" "));
var wi =
    "abort canplay canplaythrough durationchange emptied encrypted ended error loadeddata loadedmetadata loadstart pause play playing progress ratechange resize seeked seeking stalled suspend timeupdate volumechange waiting".split(
      " ",
    ),
  p2 = new Set("cancel close invalid load scroll toggle".split(" ").concat(wi));
function Gp(e, t, n) {
  var r = e.type || "unknown-event";
  (e.currentTarget = n), db(r, t, void 0, e), (e.currentTarget = null);
}
function fv(e, t) {
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
          Gp(o, a, u), (i = l);
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
          Gp(o, a, u), (i = l);
        }
    }
  }
  if (Xa) throw ((e = Qc), (Xa = !1), (Qc = null), e);
}
function ge(e, t) {
  var n = t[lf];
  n === void 0 && (n = t[lf] = new Set());
  var r = e + "__bubble";
  n.has(r) || (dv(t, e, 2, !1), n.add(r));
}
function Hu(e, t, n) {
  var r = 0;
  t && (r |= 4), dv(n, e, r, t);
}
var Xs = "_reactListening" + Math.random().toString(36).slice(2);
function Zi(e) {
  if (!e[Xs]) {
    (e[Xs] = !0),
      x0.forEach(function (n) {
        n !== "selectionchange" && (p2.has(n) || Hu(n, !1, e), Hu(n, !0, e));
      });
    var t = e.nodeType === 9 ? e : e.ownerDocument;
    t === null || t[Xs] || ((t[Xs] = !0), Hu("selectionchange", !1, t));
  }
}
function dv(e, t, n, r) {
  switch (X0(t)) {
    case 1:
      var o = Nb;
      break;
    case 4:
      o = Pb;
      break;
    default:
      o = Nd;
  }
  (n = o.bind(null, t, n, e)),
    (o = void 0),
    !Zc || (t !== "touchstart" && t !== "touchmove" && t !== "wheel") || (o = !0),
    r
      ? o !== void 0
        ? e.addEventListener(t, n, { capture: !0, passive: o })
        : e.addEventListener(t, n, !0)
      : o !== void 0
        ? e.addEventListener(t, n, { passive: o })
        : e.addEventListener(t, n, !1);
}
function Uu(e, t, n, r, o) {
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
  L0(function () {
    var u = i,
      c = bd(n),
      f = [];
    e: {
      var d = cv.get(e);
      if (d !== void 0) {
        var m = Md,
          y = e;
        switch (e) {
          case "keypress":
            if (Ta(n) === 0) break e;
          case "keydown":
          case "keyup":
            m = Ub;
            break;
          case "focusin":
            (y = "focus"), (m = Ou);
            break;
          case "focusout":
            (y = "blur"), (m = Ou);
            break;
          case "beforeblur":
          case "afterblur":
            m = Ou;
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
            m = Ip;
            break;
          case "drag":
          case "dragend":
          case "dragenter":
          case "dragexit":
          case "dragleave":
          case "dragover":
          case "dragstart":
          case "drop":
            m = Rb;
            break;
          case "touchcancel":
          case "touchend":
          case "touchmove":
          case "touchstart":
            m = Kb;
            break;
          case sv:
          case av:
          case lv:
            m = Lb;
            break;
          case uv:
            m = Xb;
            break;
          case "scroll":
            m = Mb;
            break;
          case "wheel":
            m = Qb;
            break;
          case "copy":
          case "cut":
          case "paste":
            m = Ob;
            break;
          case "gotpointercapture":
          case "lostpointercapture":
          case "pointercancel":
          case "pointerdown":
          case "pointermove":
          case "pointerout":
          case "pointerover":
          case "pointerup":
            m = Vp;
        }
        var g = (t & 4) !== 0,
          w = !g && e === "scroll",
          h = g ? (d !== null ? d + "Capture" : null) : d;
        g = [];
        for (var p = u, x; p !== null; ) {
          x = p;
          var S = x.stateNode;
          if (
            (x.tag === 5 &&
              S !== null &&
              ((x = S), h !== null && ((S = Ui(p, h)), S != null && g.push(Qi(p, S, x)))),
            w)
          )
            break;
          p = p.return;
        }
        0 < g.length && ((d = new m(d, y, null, n, c)), f.push({ event: d, listeners: g }));
      }
    }
    if (!(t & 7)) {
      e: {
        if (
          ((d = e === "mouseover" || e === "pointerover"),
          (m = e === "mouseout" || e === "pointerout"),
          d && n !== Yc && (y = n.relatedTarget || n.fromElement) && (yr(y) || y[xn]))
        )
          break e;
        if (
          (m || d) &&
          ((d =
            c.window === c ? c : (d = c.ownerDocument) ? d.defaultView || d.parentWindow : window),
          m
            ? ((y = n.relatedTarget || n.toElement),
              (m = u),
              (y = y ? yr(y) : null),
              y !== null && ((w = Or(y)), y !== w || (y.tag !== 5 && y.tag !== 6)) && (y = null))
            : ((m = null), (y = u)),
          m !== y)
        ) {
          if (
            ((g = Ip),
            (S = "onMouseLeave"),
            (h = "onMouseEnter"),
            (p = "mouse"),
            (e === "pointerout" || e === "pointerover") &&
              ((g = Vp), (S = "onPointerLeave"), (h = "onPointerEnter"), (p = "pointer")),
            (w = m == null ? d : ro(m)),
            (x = y == null ? d : ro(y)),
            (d = new g(S, p + "leave", m, n, c)),
            (d.target = w),
            (d.relatedTarget = x),
            (S = null),
            yr(c) === u &&
              ((g = new g(h, p + "enter", y, n, c)),
              (g.target = x),
              (g.relatedTarget = w),
              (S = g)),
            (w = S),
            m && y)
          )
            t: {
              for (g = m, h = y, p = 0, x = g; x; x = Ur(x)) p++;
              for (x = 0, S = h; S; S = Ur(S)) x++;
              for (; 0 < p - x; ) (g = Ur(g)), p--;
              for (; 0 < x - p; ) (h = Ur(h)), x--;
              for (; p--; ) {
                if (g === h || (h !== null && g === h.alternate)) break t;
                (g = Ur(g)), (h = Ur(h));
              }
              g = null;
            }
          else g = null;
          m !== null && Kp(f, d, m, g, !1), y !== null && w !== null && Kp(f, w, y, g, !0);
        }
      }
      e: {
        if (
          ((d = u ? ro(u) : window),
          (m = d.nodeName && d.nodeName.toLowerCase()),
          m === "select" || (m === "input" && d.type === "file"))
        )
          var E = o2;
        else if (Fp(d))
          if (tv) E = l2;
          else {
            E = s2;
            var _ = i2;
          }
        else
          (m = d.nodeName) &&
            m.toLowerCase() === "input" &&
            (d.type === "checkbox" || d.type === "radio") &&
            (E = a2);
        if (E && (E = E(e, u))) {
          ev(f, E, n, c);
          break e;
        }
        _ && _(e, d, u),
          e === "focusout" &&
            (_ = d._wrapperState) &&
            _.controlled &&
            d.type === "number" &&
            Hc(d, "number", d.value);
      }
      switch (((_ = u ? ro(u) : window), e)) {
        case "focusin":
          (Fp(_) || _.contentEditable === "true") && ((to = _), (tf = u), (Ai = null));
          break;
        case "focusout":
          Ai = tf = to = null;
          break;
        case "mousedown":
          nf = !0;
          break;
        case "contextmenu":
        case "mouseup":
        case "dragend":
          (nf = !1), Up(f, n, c);
          break;
        case "selectionchange":
          if (f2) break;
        case "keydown":
        case "keyup":
          Up(f, n, c);
      }
      var k;
      if (Rd)
        e: {
          switch (e) {
            case "compositionstart":
              var N = "onCompositionStart";
              break e;
            case "compositionend":
              N = "onCompositionEnd";
              break e;
            case "compositionupdate":
              N = "onCompositionUpdate";
              break e;
          }
          N = void 0;
        }
      else
        eo
          ? q0(e, n) && (N = "onCompositionEnd")
          : e === "keydown" && n.keyCode === 229 && (N = "onCompositionStart");
      N &&
        (Q0 &&
          n.locale !== "ko" &&
          (eo || N !== "onCompositionStart"
            ? N === "onCompositionEnd" && eo && (k = Z0())
            : ((zn = c), (Pd = "value" in zn ? zn.value : zn.textContent), (eo = !0))),
        (_ = el(u, N)),
        0 < _.length &&
          ((N = new Lp(N, e, null, n, c)),
          f.push({ event: N, listeners: _ }),
          k ? (N.data = k) : ((k = J0(n)), k !== null && (N.data = k)))),
        (k = Jb ? e2(e, n) : t2(e, n)) &&
          ((u = el(u, "onBeforeInput")),
          0 < u.length &&
            ((c = new Lp("onBeforeInput", "beforeinput", null, n, c)),
            f.push({ event: c, listeners: u }),
            (c.data = k)));
    }
    fv(f, t);
  });
}
function Qi(e, t, n) {
  return { instance: e, listener: t, currentTarget: n };
}
function el(e, t) {
  for (var n = t + "Capture", r = []; e !== null; ) {
    var o = e,
      i = o.stateNode;
    o.tag === 5 &&
      i !== null &&
      ((o = i),
      (i = Ui(e, n)),
      i != null && r.unshift(Qi(e, i, o)),
      (i = Ui(e, t)),
      i != null && r.push(Qi(e, i, o))),
      (e = e.return);
  }
  return r;
}
function Ur(e) {
  if (e === null) return null;
  do e = e.return;
  while (e && e.tag !== 5);
  return e || null;
}
function Kp(e, t, n, r, o) {
  for (var i = t._reactName, s = []; n !== null && n !== r; ) {
    var a = n,
      l = a.alternate,
      u = a.stateNode;
    if (l !== null && l === r) break;
    a.tag === 5 &&
      u !== null &&
      ((a = u),
      o
        ? ((l = Ui(n, i)), l != null && s.unshift(Qi(n, l, a)))
        : o || ((l = Ui(n, i)), l != null && s.push(Qi(n, l, a)))),
      (n = n.return);
  }
  s.length !== 0 && e.push({ event: t, listeners: s });
}
var m2 = /\r\n?/g,
  g2 = /\u0000|\uFFFD/g;
function Yp(e) {
  return (typeof e == "string" ? e : "" + e)
    .replace(
      m2,
      `
`,
    )
    .replace(g2, "");
}
function Zs(e, t, n) {
  if (((t = Yp(t)), Yp(e) !== t && n)) throw Error(B(425));
}
function tl() {}
var rf = null,
  of = null;
function sf(e, t) {
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
var af = typeof setTimeout == "function" ? setTimeout : void 0,
  y2 = typeof clearTimeout == "function" ? clearTimeout : void 0,
  Xp = typeof Promise == "function" ? Promise : void 0,
  v2 =
    typeof queueMicrotask == "function"
      ? queueMicrotask
      : typeof Xp < "u"
        ? function (e) {
            return Xp.resolve(null).then(e).catch(x2);
          }
        : af;
function x2(e) {
  setTimeout(function () {
    throw e;
  });
}
function Wu(e, t) {
  var n = t,
    r = 0;
  do {
    var o = n.nextSibling;
    if ((e.removeChild(n), o && o.nodeType === 8))
      if (((n = o.data), n === "/$")) {
        if (r === 0) {
          e.removeChild(o), Ki(t);
          return;
        }
        r--;
      } else (n !== "$" && n !== "$?" && n !== "$!") || r++;
    n = o;
  } while (n);
  Ki(t);
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
function Zp(e) {
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
var Ko = Math.random().toString(36).slice(2),
  Kt = "__reactFiber$" + Ko,
  qi = "__reactProps$" + Ko,
  xn = "__reactContainer$" + Ko,
  lf = "__reactEvents$" + Ko,
  w2 = "__reactListeners$" + Ko,
  S2 = "__reactHandles$" + Ko;
function yr(e) {
  var t = e[Kt];
  if (t) return t;
  for (var n = e.parentNode; n; ) {
    if ((t = n[xn] || n[Kt])) {
      if (((n = t.alternate), t.child !== null || (n !== null && n.child !== null)))
        for (e = Zp(e); e !== null; ) {
          if ((n = e[Kt])) return n;
          e = Zp(e);
        }
      return t;
    }
    (e = n), (n = e.parentNode);
  }
  return null;
}
function ks(e) {
  return (
    (e = e[Kt] || e[xn]),
    !e || (e.tag !== 5 && e.tag !== 6 && e.tag !== 13 && e.tag !== 3) ? null : e
  );
}
function ro(e) {
  if (e.tag === 5 || e.tag === 6) return e.stateNode;
  throw Error(B(33));
}
function Ul(e) {
  return e[qi] || null;
}
var uf = [],
  oo = -1;
function tr(e) {
  return { current: e };
}
function ye(e) {
  0 > oo || ((e.current = uf[oo]), (uf[oo] = null), oo--);
}
function he(e, t) {
  oo++, (uf[oo] = e.current), (e.current = t);
}
var qn = {},
  Qe = tr(qn),
  at = tr(!1),
  Nr = qn;
function Mo(e, t) {
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
function lt(e) {
  return (e = e.childContextTypes), e != null;
}
function nl() {
  ye(at), ye(Qe);
}
function Qp(e, t, n) {
  if (Qe.current !== qn) throw Error(B(168));
  he(Qe, t), he(at, n);
}
function hv(e, t, n) {
  var r = e.stateNode;
  if (((t = t.childContextTypes), typeof r.getChildContext != "function")) return n;
  r = r.getChildContext();
  for (var o in r) if (!(o in t)) throw Error(B(108, ib(e) || "Unknown", o));
  return Ee({}, n, r);
}
function rl(e) {
  return (
    (e = ((e = e.stateNode) && e.__reactInternalMemoizedMergedChildContext) || qn),
    (Nr = Qe.current),
    he(Qe, e),
    he(at, at.current),
    !0
  );
}
function qp(e, t, n) {
  var r = e.stateNode;
  if (!r) throw Error(B(169));
  n
    ? ((e = hv(e, t, Nr)),
      (r.__reactInternalMemoizedMergedChildContext = e),
      ye(at),
      ye(Qe),
      he(Qe, e))
    : ye(at),
    he(at, n);
}
var un = null,
  Wl = !1,
  Gu = !1;
function pv(e) {
  un === null ? (un = [e]) : un.push(e);
}
function E2(e) {
  (Wl = !0), pv(e);
}
function nr() {
  if (!Gu && un !== null) {
    Gu = !0;
    var e = 0,
      t = le;
    try {
      var n = un;
      for (le = 1; e < n.length; e++) {
        var r = n[e];
        do r = r(!0);
        while (r !== null);
      }
      (un = null), (Wl = !1);
    } catch (o) {
      throw (un !== null && (un = un.slice(e + 1)), F0(kd, nr), o);
    } finally {
      (le = t), (Gu = !1);
    }
  }
  return null;
}
var io = [],
  so = 0,
  ol = null,
  il = 0,
  St = [],
  Et = 0,
  Pr = null,
  fn = 1,
  dn = "";
function fr(e, t) {
  (io[so++] = il), (io[so++] = ol), (ol = e), (il = t);
}
function mv(e, t, n) {
  (St[Et++] = fn), (St[Et++] = dn), (St[Et++] = Pr), (Pr = e);
  var r = fn;
  e = dn;
  var o = 32 - Ot(r) - 1;
  (r &= ~(1 << o)), (n += 1);
  var i = 32 - Ot(t) + o;
  if (30 < i) {
    var s = o - (o % 5);
    (i = (r & ((1 << s) - 1)).toString(32)),
      (r >>= s),
      (o -= s),
      (fn = (1 << (32 - Ot(t) + o)) | (n << o) | r),
      (dn = i + e);
  } else (fn = (1 << i) | (n << o) | r), (dn = e);
}
function Id(e) {
  e.return !== null && (fr(e, 1), mv(e, 1, 0));
}
function Ld(e) {
  for (; e === ol; ) (ol = io[--so]), (io[so] = null), (il = io[--so]), (io[so] = null);
  for (; e === Pr; )
    (Pr = St[--Et]),
      (St[Et] = null),
      (dn = St[--Et]),
      (St[Et] = null),
      (fn = St[--Et]),
      (St[Et] = null);
}
var dt = null,
  ft = null,
  ve = !1,
  Lt = null;
function gv(e, t) {
  var n = bt(5, null, null, 0);
  (n.elementType = "DELETED"),
    (n.stateNode = t),
    (n.return = e),
    (t = e.deletions),
    t === null ? ((e.deletions = [n]), (e.flags |= 16)) : t.push(n);
}
function Jp(e, t) {
  switch (e.tag) {
    case 5:
      var n = e.type;
      return (
        (t = t.nodeType !== 1 || n.toLowerCase() !== t.nodeName.toLowerCase() ? null : t),
        t !== null ? ((e.stateNode = t), (dt = e), (ft = Wn(t.firstChild)), !0) : !1
      );
    case 6:
      return (
        (t = e.pendingProps === "" || t.nodeType !== 3 ? null : t),
        t !== null ? ((e.stateNode = t), (dt = e), (ft = null), !0) : !1
      );
    case 13:
      return (
        (t = t.nodeType !== 8 ? null : t),
        t !== null
          ? ((n = Pr !== null ? { id: fn, overflow: dn } : null),
            (e.memoizedState = { dehydrated: t, treeContext: n, retryLane: 1073741824 }),
            (n = bt(18, null, null, 0)),
            (n.stateNode = t),
            (n.return = e),
            (e.child = n),
            (dt = e),
            (ft = null),
            !0)
          : !1
      );
    default:
      return !1;
  }
}
function cf(e) {
  return (e.mode & 1) !== 0 && (e.flags & 128) === 0;
}
function ff(e) {
  if (ve) {
    var t = ft;
    if (t) {
      var n = t;
      if (!Jp(e, t)) {
        if (cf(e)) throw Error(B(418));
        t = Wn(n.nextSibling);
        var r = dt;
        t && Jp(e, t) ? gv(r, n) : ((e.flags = (e.flags & -4097) | 2), (ve = !1), (dt = e));
      }
    } else {
      if (cf(e)) throw Error(B(418));
      (e.flags = (e.flags & -4097) | 2), (ve = !1), (dt = e);
    }
  }
}
function em(e) {
  for (e = e.return; e !== null && e.tag !== 5 && e.tag !== 3 && e.tag !== 13; ) e = e.return;
  dt = e;
}
function Qs(e) {
  if (e !== dt) return !1;
  if (!ve) return em(e), (ve = !0), !1;
  var t;
  if (
    ((t = e.tag !== 3) &&
      !(t = e.tag !== 5) &&
      ((t = e.type), (t = t !== "head" && t !== "body" && !sf(e.type, e.memoizedProps))),
    t && (t = ft))
  ) {
    if (cf(e)) throw (yv(), Error(B(418)));
    for (; t; ) gv(e, t), (t = Wn(t.nextSibling));
  }
  if ((em(e), e.tag === 13)) {
    if (((e = e.memoizedState), (e = e !== null ? e.dehydrated : null), !e)) throw Error(B(317));
    e: {
      for (e = e.nextSibling, t = 0; e; ) {
        if (e.nodeType === 8) {
          var n = e.data;
          if (n === "/$") {
            if (t === 0) {
              ft = Wn(e.nextSibling);
              break e;
            }
            t--;
          } else (n !== "$" && n !== "$!" && n !== "$?") || t++;
        }
        e = e.nextSibling;
      }
      ft = null;
    }
  } else ft = dt ? Wn(e.stateNode.nextSibling) : null;
  return !0;
}
function yv() {
  for (var e = ft; e; ) e = Wn(e.nextSibling);
}
function Ao() {
  (ft = dt = null), (ve = !1);
}
function Vd(e) {
  Lt === null ? (Lt = [e]) : Lt.push(e);
}
var C2 = Tn.ReactCurrentBatchConfig;
function si(e, t, n) {
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
function qs(e, t) {
  throw (
    ((e = Object.prototype.toString.call(t)),
    Error(
      B(31, e === "[object Object]" ? "object with keys {" + Object.keys(t).join(", ") + "}" : e),
    ))
  );
}
function tm(e) {
  var t = e._init;
  return t(e._payload);
}
function vv(e) {
  function t(h, p) {
    if (e) {
      var x = h.deletions;
      x === null ? ((h.deletions = [p]), (h.flags |= 16)) : x.push(p);
    }
  }
  function n(h, p) {
    if (!e) return null;
    for (; p !== null; ) t(h, p), (p = p.sibling);
    return null;
  }
  function r(h, p) {
    for (h = new Map(); p !== null; )
      p.key !== null ? h.set(p.key, p) : h.set(p.index, p), (p = p.sibling);
    return h;
  }
  function o(h, p) {
    return (h = Xn(h, p)), (h.index = 0), (h.sibling = null), h;
  }
  function i(h, p, x) {
    return (
      (h.index = x),
      e
        ? ((x = h.alternate),
          x !== null ? ((x = x.index), x < p ? ((h.flags |= 2), p) : x) : ((h.flags |= 2), p))
        : ((h.flags |= 1048576), p)
    );
  }
  function s(h) {
    return e && h.alternate === null && (h.flags |= 2), h;
  }
  function a(h, p, x, S) {
    return p === null || p.tag !== 6
      ? ((p = Ju(x, h.mode, S)), (p.return = h), p)
      : ((p = o(p, x)), (p.return = h), p);
  }
  function l(h, p, x, S) {
    var E = x.type;
    return E === Jr
      ? c(h, p, x.props.children, S, x.key)
      : p !== null &&
          (p.elementType === E ||
            (typeof E == "object" && E !== null && E.$$typeof === In && tm(E) === p.type))
        ? ((S = o(p, x.props)), (S.ref = si(h, p, x)), (S.return = h), S)
        : ((S = Da(x.type, x.key, x.props, null, h.mode, S)),
          (S.ref = si(h, p, x)),
          (S.return = h),
          S);
  }
  function u(h, p, x, S) {
    return p === null ||
      p.tag !== 4 ||
      p.stateNode.containerInfo !== x.containerInfo ||
      p.stateNode.implementation !== x.implementation
      ? ((p = ec(x, h.mode, S)), (p.return = h), p)
      : ((p = o(p, x.children || [])), (p.return = h), p);
  }
  function c(h, p, x, S, E) {
    return p === null || p.tag !== 7
      ? ((p = br(x, h.mode, S, E)), (p.return = h), p)
      : ((p = o(p, x)), (p.return = h), p);
  }
  function f(h, p, x) {
    if ((typeof p == "string" && p !== "") || typeof p == "number")
      return (p = Ju("" + p, h.mode, x)), (p.return = h), p;
    if (typeof p == "object" && p !== null) {
      switch (p.$$typeof) {
        case $s:
          return (
            (x = Da(p.type, p.key, p.props, null, h.mode, x)),
            (x.ref = si(h, null, p)),
            (x.return = h),
            x
          );
        case qr:
          return (p = ec(p, h.mode, x)), (p.return = h), p;
        case In:
          var S = p._init;
          return f(h, S(p._payload), x);
      }
      if (vi(p) || ti(p)) return (p = br(p, h.mode, x, null)), (p.return = h), p;
      qs(h, p);
    }
    return null;
  }
  function d(h, p, x, S) {
    var E = p !== null ? p.key : null;
    if ((typeof x == "string" && x !== "") || typeof x == "number")
      return E !== null ? null : a(h, p, "" + x, S);
    if (typeof x == "object" && x !== null) {
      switch (x.$$typeof) {
        case $s:
          return x.key === E ? l(h, p, x, S) : null;
        case qr:
          return x.key === E ? u(h, p, x, S) : null;
        case In:
          return (E = x._init), d(h, p, E(x._payload), S);
      }
      if (vi(x) || ti(x)) return E !== null ? null : c(h, p, x, S, null);
      qs(h, x);
    }
    return null;
  }
  function m(h, p, x, S, E) {
    if ((typeof S == "string" && S !== "") || typeof S == "number")
      return (h = h.get(x) || null), a(p, h, "" + S, E);
    if (typeof S == "object" && S !== null) {
      switch (S.$$typeof) {
        case $s:
          return (h = h.get(S.key === null ? x : S.key) || null), l(p, h, S, E);
        case qr:
          return (h = h.get(S.key === null ? x : S.key) || null), u(p, h, S, E);
        case In:
          var _ = S._init;
          return m(h, p, x, _(S._payload), E);
      }
      if (vi(S) || ti(S)) return (h = h.get(x) || null), c(p, h, S, E, null);
      qs(p, S);
    }
    return null;
  }
  function y(h, p, x, S) {
    for (var E = null, _ = null, k = p, N = (p = 0), A = null; k !== null && N < x.length; N++) {
      k.index > N ? ((A = k), (k = null)) : (A = k.sibling);
      var R = d(h, k, x[N], S);
      if (R === null) {
        k === null && (k = A);
        break;
      }
      e && k && R.alternate === null && t(h, k),
        (p = i(R, p, N)),
        _ === null ? (E = R) : (_.sibling = R),
        (_ = R),
        (k = A);
    }
    if (N === x.length) return n(h, k), ve && fr(h, N), E;
    if (k === null) {
      for (; N < x.length; N++)
        (k = f(h, x[N], S)),
          k !== null && ((p = i(k, p, N)), _ === null ? (E = k) : (_.sibling = k), (_ = k));
      return ve && fr(h, N), E;
    }
    for (k = r(h, k); N < x.length; N++)
      (A = m(k, h, N, x[N], S)),
        A !== null &&
          (e && A.alternate !== null && k.delete(A.key === null ? N : A.key),
          (p = i(A, p, N)),
          _ === null ? (E = A) : (_.sibling = A),
          (_ = A));
    return (
      e &&
        k.forEach(function (O) {
          return t(h, O);
        }),
      ve && fr(h, N),
      E
    );
  }
  function g(h, p, x, S) {
    var E = ti(x);
    if (typeof E != "function") throw Error(B(150));
    if (((x = E.call(x)), x == null)) throw Error(B(151));
    for (
      var _ = (E = null), k = p, N = (p = 0), A = null, R = x.next();
      k !== null && !R.done;
      N++, R = x.next()
    ) {
      k.index > N ? ((A = k), (k = null)) : (A = k.sibling);
      var O = d(h, k, R.value, S);
      if (O === null) {
        k === null && (k = A);
        break;
      }
      e && k && O.alternate === null && t(h, k),
        (p = i(O, p, N)),
        _ === null ? (E = O) : (_.sibling = O),
        (_ = O),
        (k = A);
    }
    if (R.done) return n(h, k), ve && fr(h, N), E;
    if (k === null) {
      for (; !R.done; N++, R = x.next())
        (R = f(h, R.value, S)),
          R !== null && ((p = i(R, p, N)), _ === null ? (E = R) : (_.sibling = R), (_ = R));
      return ve && fr(h, N), E;
    }
    for (k = r(h, k); !R.done; N++, R = x.next())
      (R = m(k, h, N, R.value, S)),
        R !== null &&
          (e && R.alternate !== null && k.delete(R.key === null ? N : R.key),
          (p = i(R, p, N)),
          _ === null ? (E = R) : (_.sibling = R),
          (_ = R));
    return (
      e &&
        k.forEach(function (j) {
          return t(h, j);
        }),
      ve && fr(h, N),
      E
    );
  }
  function w(h, p, x, S) {
    if (
      (typeof x == "object" &&
        x !== null &&
        x.type === Jr &&
        x.key === null &&
        (x = x.props.children),
      typeof x == "object" && x !== null)
    ) {
      switch (x.$$typeof) {
        case $s:
          e: {
            for (var E = x.key, _ = p; _ !== null; ) {
              if (_.key === E) {
                if (((E = x.type), E === Jr)) {
                  if (_.tag === 7) {
                    n(h, _.sibling), (p = o(_, x.props.children)), (p.return = h), (h = p);
                    break e;
                  }
                } else if (
                  _.elementType === E ||
                  (typeof E == "object" && E !== null && E.$$typeof === In && tm(E) === _.type)
                ) {
                  n(h, _.sibling),
                    (p = o(_, x.props)),
                    (p.ref = si(h, _, x)),
                    (p.return = h),
                    (h = p);
                  break e;
                }
                n(h, _);
                break;
              } else t(h, _);
              _ = _.sibling;
            }
            x.type === Jr
              ? ((p = br(x.props.children, h.mode, S, x.key)), (p.return = h), (h = p))
              : ((S = Da(x.type, x.key, x.props, null, h.mode, S)),
                (S.ref = si(h, p, x)),
                (S.return = h),
                (h = S));
          }
          return s(h);
        case qr:
          e: {
            for (_ = x.key; p !== null; ) {
              if (p.key === _)
                if (
                  p.tag === 4 &&
                  p.stateNode.containerInfo === x.containerInfo &&
                  p.stateNode.implementation === x.implementation
                ) {
                  n(h, p.sibling), (p = o(p, x.children || [])), (p.return = h), (h = p);
                  break e;
                } else {
                  n(h, p);
                  break;
                }
              else t(h, p);
              p = p.sibling;
            }
            (p = ec(x, h.mode, S)), (p.return = h), (h = p);
          }
          return s(h);
        case In:
          return (_ = x._init), w(h, p, _(x._payload), S);
      }
      if (vi(x)) return y(h, p, x, S);
      if (ti(x)) return g(h, p, x, S);
      qs(h, x);
    }
    return (typeof x == "string" && x !== "") || typeof x == "number"
      ? ((x = "" + x),
        p !== null && p.tag === 6
          ? (n(h, p.sibling), (p = o(p, x)), (p.return = h), (h = p))
          : (n(h, p), (p = Ju(x, h.mode, S)), (p.return = h), (h = p)),
        s(h))
      : n(h, p);
  }
  return w;
}
var Ro = vv(!0),
  xv = vv(!1),
  sl = tr(null),
  al = null,
  ao = null,
  Od = null;
function jd() {
  Od = ao = al = null;
}
function Fd(e) {
  var t = sl.current;
  ye(sl), (e._currentValue = t);
}
function df(e, t, n) {
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
function Eo(e, t) {
  (al = e),
    (Od = ao = null),
    (e = e.dependencies),
    e !== null && e.firstContext !== null && (e.lanes & t && (it = !0), (e.firstContext = null));
}
function _t(e) {
  var t = e._currentValue;
  if (Od !== e)
    if (((e = { context: e, memoizedValue: t, next: null }), ao === null)) {
      if (al === null) throw Error(B(308));
      (ao = e), (al.dependencies = { lanes: 0, firstContext: e });
    } else ao = ao.next = e;
  return t;
}
var vr = null;
function zd(e) {
  vr === null ? (vr = [e]) : vr.push(e);
}
function wv(e, t, n, r) {
  var o = t.interleaved;
  return (
    o === null ? ((n.next = n), zd(t)) : ((n.next = o.next), (o.next = n)),
    (t.interleaved = n),
    wn(e, r)
  );
}
function wn(e, t) {
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
function $d(e) {
  e.updateQueue = {
    baseState: e.memoizedState,
    firstBaseUpdate: null,
    lastBaseUpdate: null,
    shared: { pending: null, interleaved: null, lanes: 0 },
    effects: null,
  };
}
function Sv(e, t) {
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
function pn(e, t) {
  return { eventTime: e, lane: t, tag: 0, payload: null, callback: null, next: null };
}
function Gn(e, t, n) {
  var r = e.updateQueue;
  if (r === null) return null;
  if (((r = r.shared), ie & 2)) {
    var o = r.pending;
    return o === null ? (t.next = t) : ((t.next = o.next), (o.next = t)), (r.pending = t), wn(e, n);
  }
  return (
    (o = r.interleaved),
    o === null ? ((t.next = t), zd(r)) : ((t.next = o.next), (o.next = t)),
    (r.interleaved = t),
    wn(e, n)
  );
}
function _a(e, t, n) {
  if (((t = t.updateQueue), t !== null && ((t = t.shared), (n & 4194240) !== 0))) {
    var r = t.lanes;
    (r &= e.pendingLanes), (n |= r), (t.lanes = n), Td(e, n);
  }
}
function nm(e, t) {
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
function ll(e, t, n, r) {
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
        m = a.eventTime;
      if ((r & d) === d) {
        c !== null &&
          (c = c.next =
            {
              eventTime: m,
              lane: 0,
              tag: a.tag,
              payload: a.payload,
              callback: a.callback,
              next: null,
            });
        e: {
          var y = e,
            g = a;
          switch (((d = t), (m = n), g.tag)) {
            case 1:
              if (((y = g.payload), typeof y == "function")) {
                f = y.call(m, f, d);
                break e;
              }
              f = y;
              break e;
            case 3:
              y.flags = (y.flags & -65537) | 128;
            case 0:
              if (((y = g.payload), (d = typeof y == "function" ? y.call(m, f, d) : y), d == null))
                break e;
              f = Ee({}, f, d);
              break e;
            case 2:
              Ln = !0;
          }
        }
        a.callback !== null &&
          a.lane !== 0 &&
          ((e.flags |= 64), (d = o.effects), d === null ? (o.effects = [a]) : d.push(a));
      } else
        (m = {
          eventTime: m,
          lane: d,
          tag: a.tag,
          payload: a.payload,
          callback: a.callback,
          next: null,
        }),
          c === null ? ((u = c = m), (l = f)) : (c = c.next = m),
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
    (Ar |= s), (e.lanes = s), (e.memoizedState = f);
  }
}
function rm(e, t, n) {
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
var Ts = {},
  Zt = tr(Ts),
  Ji = tr(Ts),
  es = tr(Ts);
function xr(e) {
  if (e === Ts) throw Error(B(174));
  return e;
}
function Bd(e, t) {
  switch ((he(es, t), he(Ji, e), he(Zt, Ts), (e = t.nodeType), e)) {
    case 9:
    case 11:
      t = (t = t.documentElement) ? t.namespaceURI : Wc(null, "");
      break;
    default:
      (e = e === 8 ? t.parentNode : t),
        (t = e.namespaceURI || null),
        (e = e.tagName),
        (t = Wc(t, e));
  }
  ye(Zt), he(Zt, t);
}
function Do() {
  ye(Zt), ye(Ji), ye(es);
}
function Ev(e) {
  xr(es.current);
  var t = xr(Zt.current),
    n = Wc(t, e.type);
  t !== n && (he(Ji, e), he(Zt, n));
}
function Hd(e) {
  Ji.current === e && (ye(Zt), ye(Ji));
}
var xe = tr(0);
function ul(e) {
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
var Ku = [];
function Ud() {
  for (var e = 0; e < Ku.length; e++) Ku[e]._workInProgressVersionPrimary = null;
  Ku.length = 0;
}
var Na = Tn.ReactCurrentDispatcher,
  Yu = Tn.ReactCurrentBatchConfig,
  Mr = 0,
  Se = null,
  Re = null,
  Le = null,
  cl = !1,
  Ri = !1,
  ts = 0,
  b2 = 0;
function Ge() {
  throw Error(B(321));
}
function Wd(e, t) {
  if (t === null) return !1;
  for (var n = 0; n < t.length && n < e.length; n++) if (!zt(e[n], t[n])) return !1;
  return !0;
}
function Gd(e, t, n, r, o, i) {
  if (
    ((Mr = i),
    (Se = t),
    (t.memoizedState = null),
    (t.updateQueue = null),
    (t.lanes = 0),
    (Na.current = e === null || e.memoizedState === null ? N2 : P2),
    (e = n(r, o)),
    Ri)
  ) {
    i = 0;
    do {
      if (((Ri = !1), (ts = 0), 25 <= i)) throw Error(B(301));
      (i += 1), (Le = Re = null), (t.updateQueue = null), (Na.current = M2), (e = n(r, o));
    } while (Ri);
  }
  if (
    ((Na.current = fl),
    (t = Re !== null && Re.next !== null),
    (Mr = 0),
    (Le = Re = Se = null),
    (cl = !1),
    t)
  )
    throw Error(B(300));
  return e;
}
function Kd() {
  var e = ts !== 0;
  return (ts = 0), e;
}
function Wt() {
  var e = { memoizedState: null, baseState: null, baseQueue: null, queue: null, next: null };
  return Le === null ? (Se.memoizedState = Le = e) : (Le = Le.next = e), Le;
}
function Nt() {
  if (Re === null) {
    var e = Se.alternate;
    e = e !== null ? e.memoizedState : null;
  } else e = Re.next;
  var t = Le === null ? Se.memoizedState : Le.next;
  if (t !== null) (Le = t), (Re = e);
  else {
    if (e === null) throw Error(B(310));
    (Re = e),
      (e = {
        memoizedState: Re.memoizedState,
        baseState: Re.baseState,
        baseQueue: Re.baseQueue,
        queue: Re.queue,
        next: null,
      }),
      Le === null ? (Se.memoizedState = Le = e) : (Le = Le.next = e);
  }
  return Le;
}
function ns(e, t) {
  return typeof t == "function" ? t(e) : t;
}
function Xu(e) {
  var t = Nt(),
    n = t.queue;
  if (n === null) throw Error(B(311));
  n.lastRenderedReducer = e;
  var r = Re,
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
      if ((Mr & c) === c)
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
        l === null ? ((a = l = f), (s = r)) : (l = l.next = f), (Se.lanes |= c), (Ar |= c);
      }
      u = u.next;
    } while (u !== null && u !== i);
    l === null ? (s = r) : (l.next = a),
      zt(r, t.memoizedState) || (it = !0),
      (t.memoizedState = r),
      (t.baseState = s),
      (t.baseQueue = l),
      (n.lastRenderedState = r);
  }
  if (((e = n.interleaved), e !== null)) {
    o = e;
    do (i = o.lane), (Se.lanes |= i), (Ar |= i), (o = o.next);
    while (o !== e);
  } else o === null && (n.lanes = 0);
  return [t.memoizedState, n.dispatch];
}
function Zu(e) {
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
    zt(i, t.memoizedState) || (it = !0),
      (t.memoizedState = i),
      t.baseQueue === null && (t.baseState = i),
      (n.lastRenderedState = i);
  }
  return [i, r];
}
function Cv() {}
function bv(e, t) {
  var n = Se,
    r = Nt(),
    o = t(),
    i = !zt(r.memoizedState, o);
  if (
    (i && ((r.memoizedState = o), (it = !0)),
    (r = r.queue),
    Yd(_v.bind(null, n, r, e), [e]),
    r.getSnapshot !== t || i || (Le !== null && Le.memoizedState.tag & 1))
  ) {
    if (((n.flags |= 2048), rs(9, Tv.bind(null, n, r, o, t), void 0, null), Oe === null))
      throw Error(B(349));
    Mr & 30 || kv(n, t, o);
  }
  return o;
}
function kv(e, t, n) {
  (e.flags |= 16384),
    (e = { getSnapshot: t, value: n }),
    (t = Se.updateQueue),
    t === null
      ? ((t = { lastEffect: null, stores: null }), (Se.updateQueue = t), (t.stores = [e]))
      : ((n = t.stores), n === null ? (t.stores = [e]) : n.push(e));
}
function Tv(e, t, n, r) {
  (t.value = n), (t.getSnapshot = r), Nv(t) && Pv(e);
}
function _v(e, t, n) {
  return n(function () {
    Nv(t) && Pv(e);
  });
}
function Nv(e) {
  var t = e.getSnapshot;
  e = e.value;
  try {
    var n = t();
    return !zt(e, n);
  } catch {
    return !0;
  }
}
function Pv(e) {
  var t = wn(e, 1);
  t !== null && jt(t, e, 1, -1);
}
function om(e) {
  var t = Wt();
  return (
    typeof e == "function" && (e = e()),
    (t.memoizedState = t.baseState = e),
    (e = {
      pending: null,
      interleaved: null,
      lanes: 0,
      dispatch: null,
      lastRenderedReducer: ns,
      lastRenderedState: e,
    }),
    (t.queue = e),
    (e = e.dispatch = _2.bind(null, Se, e)),
    [t.memoizedState, e]
  );
}
function rs(e, t, n, r) {
  return (
    (e = { tag: e, create: t, destroy: n, deps: r, next: null }),
    (t = Se.updateQueue),
    t === null
      ? ((t = { lastEffect: null, stores: null }),
        (Se.updateQueue = t),
        (t.lastEffect = e.next = e))
      : ((n = t.lastEffect),
        n === null
          ? (t.lastEffect = e.next = e)
          : ((r = n.next), (n.next = e), (e.next = r), (t.lastEffect = e))),
    e
  );
}
function Mv() {
  return Nt().memoizedState;
}
function Pa(e, t, n, r) {
  var o = Wt();
  (Se.flags |= e), (o.memoizedState = rs(1 | t, n, void 0, r === void 0 ? null : r));
}
function Gl(e, t, n, r) {
  var o = Nt();
  r = r === void 0 ? null : r;
  var i = void 0;
  if (Re !== null) {
    var s = Re.memoizedState;
    if (((i = s.destroy), r !== null && Wd(r, s.deps))) {
      o.memoizedState = rs(t, n, i, r);
      return;
    }
  }
  (Se.flags |= e), (o.memoizedState = rs(1 | t, n, i, r));
}
function im(e, t) {
  return Pa(8390656, 8, e, t);
}
function Yd(e, t) {
  return Gl(2048, 8, e, t);
}
function Av(e, t) {
  return Gl(4, 2, e, t);
}
function Rv(e, t) {
  return Gl(4, 4, e, t);
}
function Dv(e, t) {
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
function Iv(e, t, n) {
  return (n = n != null ? n.concat([e]) : null), Gl(4, 4, Dv.bind(null, t, e), n);
}
function Xd() {}
function Lv(e, t) {
  var n = Nt();
  t = t === void 0 ? null : t;
  var r = n.memoizedState;
  return r !== null && t !== null && Wd(t, r[1]) ? r[0] : ((n.memoizedState = [e, t]), e);
}
function Vv(e, t) {
  var n = Nt();
  t = t === void 0 ? null : t;
  var r = n.memoizedState;
  return r !== null && t !== null && Wd(t, r[1])
    ? r[0]
    : ((e = e()), (n.memoizedState = [e, t]), e);
}
function Ov(e, t, n) {
  return Mr & 21
    ? (zt(n, t) || ((n = B0()), (Se.lanes |= n), (Ar |= n), (e.baseState = !0)), t)
    : (e.baseState && ((e.baseState = !1), (it = !0)), (e.memoizedState = n));
}
function k2(e, t) {
  var n = le;
  (le = n !== 0 && 4 > n ? n : 4), e(!0);
  var r = Yu.transition;
  Yu.transition = {};
  try {
    e(!1), t();
  } finally {
    (le = n), (Yu.transition = r);
  }
}
function jv() {
  return Nt().memoizedState;
}
function T2(e, t, n) {
  var r = Yn(e);
  if (((n = { lane: r, action: n, hasEagerState: !1, eagerState: null, next: null }), Fv(e)))
    zv(t, n);
  else if (((n = wv(e, t, n, r)), n !== null)) {
    var o = et();
    jt(n, e, r, o), $v(n, t, r);
  }
}
function _2(e, t, n) {
  var r = Yn(e),
    o = { lane: r, action: n, hasEagerState: !1, eagerState: null, next: null };
  if (Fv(e)) zv(t, o);
  else {
    var i = e.alternate;
    if (e.lanes === 0 && (i === null || i.lanes === 0) && ((i = t.lastRenderedReducer), i !== null))
      try {
        var s = t.lastRenderedState,
          a = i(s, n);
        if (((o.hasEagerState = !0), (o.eagerState = a), zt(a, s))) {
          var l = t.interleaved;
          l === null ? ((o.next = o), zd(t)) : ((o.next = l.next), (l.next = o)),
            (t.interleaved = o);
          return;
        }
      } catch {
      } finally {
      }
    (n = wv(e, t, o, r)), n !== null && ((o = et()), jt(n, e, r, o), $v(n, t, r));
  }
}
function Fv(e) {
  var t = e.alternate;
  return e === Se || (t !== null && t === Se);
}
function zv(e, t) {
  Ri = cl = !0;
  var n = e.pending;
  n === null ? (t.next = t) : ((t.next = n.next), (n.next = t)), (e.pending = t);
}
function $v(e, t, n) {
  if (n & 4194240) {
    var r = t.lanes;
    (r &= e.pendingLanes), (n |= r), (t.lanes = n), Td(e, n);
  }
}
var fl = {
    readContext: _t,
    useCallback: Ge,
    useContext: Ge,
    useEffect: Ge,
    useImperativeHandle: Ge,
    useInsertionEffect: Ge,
    useLayoutEffect: Ge,
    useMemo: Ge,
    useReducer: Ge,
    useRef: Ge,
    useState: Ge,
    useDebugValue: Ge,
    useDeferredValue: Ge,
    useTransition: Ge,
    useMutableSource: Ge,
    useSyncExternalStore: Ge,
    useId: Ge,
    unstable_isNewReconciler: !1,
  },
  N2 = {
    readContext: _t,
    useCallback: function (e, t) {
      return (Wt().memoizedState = [e, t === void 0 ? null : t]), e;
    },
    useContext: _t,
    useEffect: im,
    useImperativeHandle: function (e, t, n) {
      return (n = n != null ? n.concat([e]) : null), Pa(4194308, 4, Dv.bind(null, t, e), n);
    },
    useLayoutEffect: function (e, t) {
      return Pa(4194308, 4, e, t);
    },
    useInsertionEffect: function (e, t) {
      return Pa(4, 2, e, t);
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
        (e = e.dispatch = T2.bind(null, Se, e)),
        [r.memoizedState, e]
      );
    },
    useRef: function (e) {
      var t = Wt();
      return (e = { current: e }), (t.memoizedState = e);
    },
    useState: om,
    useDebugValue: Xd,
    useDeferredValue: function (e) {
      return (Wt().memoizedState = e);
    },
    useTransition: function () {
      var e = om(!1),
        t = e[0];
      return (e = k2.bind(null, e[1])), (Wt().memoizedState = e), [t, e];
    },
    useMutableSource: function () {},
    useSyncExternalStore: function (e, t, n) {
      var r = Se,
        o = Wt();
      if (ve) {
        if (n === void 0) throw Error(B(407));
        n = n();
      } else {
        if (((n = t()), Oe === null)) throw Error(B(349));
        Mr & 30 || kv(r, t, n);
      }
      o.memoizedState = n;
      var i = { value: n, getSnapshot: t };
      return (
        (o.queue = i),
        im(_v.bind(null, r, i, e), [e]),
        (r.flags |= 2048),
        rs(9, Tv.bind(null, r, i, n, t), void 0, null),
        n
      );
    },
    useId: function () {
      var e = Wt(),
        t = Oe.identifierPrefix;
      if (ve) {
        var n = dn,
          r = fn;
        (n = (r & ~(1 << (32 - Ot(r) - 1))).toString(32) + n),
          (t = ":" + t + "R" + n),
          (n = ts++),
          0 < n && (t += "H" + n.toString(32)),
          (t += ":");
      } else (n = b2++), (t = ":" + t + "r" + n.toString(32) + ":");
      return (e.memoizedState = t);
    },
    unstable_isNewReconciler: !1,
  },
  P2 = {
    readContext: _t,
    useCallback: Lv,
    useContext: _t,
    useEffect: Yd,
    useImperativeHandle: Iv,
    useInsertionEffect: Av,
    useLayoutEffect: Rv,
    useMemo: Vv,
    useReducer: Xu,
    useRef: Mv,
    useState: function () {
      return Xu(ns);
    },
    useDebugValue: Xd,
    useDeferredValue: function (e) {
      var t = Nt();
      return Ov(t, Re.memoizedState, e);
    },
    useTransition: function () {
      var e = Xu(ns)[0],
        t = Nt().memoizedState;
      return [e, t];
    },
    useMutableSource: Cv,
    useSyncExternalStore: bv,
    useId: jv,
    unstable_isNewReconciler: !1,
  },
  M2 = {
    readContext: _t,
    useCallback: Lv,
    useContext: _t,
    useEffect: Yd,
    useImperativeHandle: Iv,
    useInsertionEffect: Av,
    useLayoutEffect: Rv,
    useMemo: Vv,
    useReducer: Zu,
    useRef: Mv,
    useState: function () {
      return Zu(ns);
    },
    useDebugValue: Xd,
    useDeferredValue: function (e) {
      var t = Nt();
      return Re === null ? (t.memoizedState = e) : Ov(t, Re.memoizedState, e);
    },
    useTransition: function () {
      var e = Zu(ns)[0],
        t = Nt().memoizedState;
      return [e, t];
    },
    useMutableSource: Cv,
    useSyncExternalStore: bv,
    useId: jv,
    unstable_isNewReconciler: !1,
  };
function Rt(e, t) {
  if (e && e.defaultProps) {
    (t = Ee({}, t)), (e = e.defaultProps);
    for (var n in e) t[n] === void 0 && (t[n] = e[n]);
    return t;
  }
  return t;
}
function hf(e, t, n, r) {
  (t = e.memoizedState),
    (n = n(r, t)),
    (n = n == null ? t : Ee({}, t, n)),
    (e.memoizedState = n),
    e.lanes === 0 && (e.updateQueue.baseState = n);
}
var Kl = {
  isMounted: function (e) {
    return (e = e._reactInternals) ? Or(e) === e : !1;
  },
  enqueueSetState: function (e, t, n) {
    e = e._reactInternals;
    var r = et(),
      o = Yn(e),
      i = pn(r, o);
    (i.payload = t),
      n != null && (i.callback = n),
      (t = Gn(e, i, o)),
      t !== null && (jt(t, e, o, r), _a(t, e, o));
  },
  enqueueReplaceState: function (e, t, n) {
    e = e._reactInternals;
    var r = et(),
      o = Yn(e),
      i = pn(r, o);
    (i.tag = 1),
      (i.payload = t),
      n != null && (i.callback = n),
      (t = Gn(e, i, o)),
      t !== null && (jt(t, e, o, r), _a(t, e, o));
  },
  enqueueForceUpdate: function (e, t) {
    e = e._reactInternals;
    var n = et(),
      r = Yn(e),
      o = pn(n, r);
    (o.tag = 2),
      t != null && (o.callback = t),
      (t = Gn(e, o, r)),
      t !== null && (jt(t, e, r, n), _a(t, e, r));
  },
};
function sm(e, t, n, r, o, i, s) {
  return (
    (e = e.stateNode),
    typeof e.shouldComponentUpdate == "function"
      ? e.shouldComponentUpdate(r, i, s)
      : t.prototype && t.prototype.isPureReactComponent
        ? !Xi(n, r) || !Xi(o, i)
        : !0
  );
}
function Bv(e, t, n) {
  var r = !1,
    o = qn,
    i = t.contextType;
  return (
    typeof i == "object" && i !== null
      ? (i = _t(i))
      : ((o = lt(t) ? Nr : Qe.current),
        (r = t.contextTypes),
        (i = (r = r != null) ? Mo(e, o) : qn)),
    (t = new t(n, i)),
    (e.memoizedState = t.state !== null && t.state !== void 0 ? t.state : null),
    (t.updater = Kl),
    (e.stateNode = t),
    (t._reactInternals = e),
    r &&
      ((e = e.stateNode),
      (e.__reactInternalMemoizedUnmaskedChildContext = o),
      (e.__reactInternalMemoizedMaskedChildContext = i)),
    t
  );
}
function am(e, t, n, r) {
  (e = t.state),
    typeof t.componentWillReceiveProps == "function" && t.componentWillReceiveProps(n, r),
    typeof t.UNSAFE_componentWillReceiveProps == "function" &&
      t.UNSAFE_componentWillReceiveProps(n, r),
    t.state !== e && Kl.enqueueReplaceState(t, t.state, null);
}
function pf(e, t, n, r) {
  var o = e.stateNode;
  (o.props = n), (o.state = e.memoizedState), (o.refs = {}), $d(e);
  var i = t.contextType;
  typeof i == "object" && i !== null
    ? (o.context = _t(i))
    : ((i = lt(t) ? Nr : Qe.current), (o.context = Mo(e, i))),
    (o.state = e.memoizedState),
    (i = t.getDerivedStateFromProps),
    typeof i == "function" && (hf(e, t, i, n), (o.state = e.memoizedState)),
    typeof t.getDerivedStateFromProps == "function" ||
      typeof o.getSnapshotBeforeUpdate == "function" ||
      (typeof o.UNSAFE_componentWillMount != "function" &&
        typeof o.componentWillMount != "function") ||
      ((t = o.state),
      typeof o.componentWillMount == "function" && o.componentWillMount(),
      typeof o.UNSAFE_componentWillMount == "function" && o.UNSAFE_componentWillMount(),
      t !== o.state && Kl.enqueueReplaceState(o, o.state, null),
      ll(e, n, o, r),
      (o.state = e.memoizedState)),
    typeof o.componentDidMount == "function" && (e.flags |= 4194308);
}
function Io(e, t) {
  try {
    var n = "",
      r = t;
    do (n += ob(r)), (r = r.return);
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
function Qu(e, t, n) {
  return { value: e, source: null, stack: n ?? null, digest: t ?? null };
}
function mf(e, t) {
  try {
    console.error(t.value);
  } catch (n) {
    setTimeout(function () {
      throw n;
    });
  }
}
var A2 = typeof WeakMap == "function" ? WeakMap : Map;
function Hv(e, t, n) {
  (n = pn(-1, n)), (n.tag = 3), (n.payload = { element: null });
  var r = t.value;
  return (
    (n.callback = function () {
      hl || ((hl = !0), (kf = r)), mf(e, t);
    }),
    n
  );
}
function Uv(e, t, n) {
  (n = pn(-1, n)), (n.tag = 3);
  var r = e.type.getDerivedStateFromError;
  if (typeof r == "function") {
    var o = t.value;
    (n.payload = function () {
      return r(o);
    }),
      (n.callback = function () {
        mf(e, t);
      });
  }
  var i = e.stateNode;
  return (
    i !== null &&
      typeof i.componentDidCatch == "function" &&
      (n.callback = function () {
        mf(e, t), typeof r != "function" && (Kn === null ? (Kn = new Set([this])) : Kn.add(this));
        var s = t.stack;
        this.componentDidCatch(t.value, { componentStack: s !== null ? s : "" });
      }),
    n
  );
}
function lm(e, t, n) {
  var r = e.pingCache;
  if (r === null) {
    r = e.pingCache = new A2();
    var o = new Set();
    r.set(t, o);
  } else (o = r.get(t)), o === void 0 && ((o = new Set()), r.set(t, o));
  o.has(n) || (o.add(n), (e = W2.bind(null, e, t, n)), t.then(e, e));
}
function um(e) {
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
function cm(e, t, n, r, o) {
  return e.mode & 1
    ? ((e.flags |= 65536), (e.lanes = o), e)
    : (e === t
        ? (e.flags |= 65536)
        : ((e.flags |= 128),
          (n.flags |= 131072),
          (n.flags &= -52805),
          n.tag === 1 &&
            (n.alternate === null ? (n.tag = 17) : ((t = pn(-1, 1)), (t.tag = 2), Gn(n, t, 1))),
          (n.lanes |= 1)),
      e);
}
var R2 = Tn.ReactCurrentOwner,
  it = !1;
function Je(e, t, n, r) {
  t.child = e === null ? xv(t, null, n, r) : Ro(t, e.child, n, r);
}
function fm(e, t, n, r, o) {
  n = n.render;
  var i = t.ref;
  return (
    Eo(t, o),
    (r = Gd(e, t, n, r, i, o)),
    (n = Kd()),
    e !== null && !it
      ? ((t.updateQueue = e.updateQueue), (t.flags &= -2053), (e.lanes &= ~o), Sn(e, t, o))
      : (ve && n && Id(t), (t.flags |= 1), Je(e, t, r, o), t.child)
  );
}
function dm(e, t, n, r, o) {
  if (e === null) {
    var i = n.type;
    return typeof i == "function" &&
      !rh(i) &&
      i.defaultProps === void 0 &&
      n.compare === null &&
      n.defaultProps === void 0
      ? ((t.tag = 15), (t.type = i), Wv(e, t, i, r, o))
      : ((e = Da(n.type, null, r, t, t.mode, o)), (e.ref = t.ref), (e.return = t), (t.child = e));
  }
  if (((i = e.child), !(e.lanes & o))) {
    var s = i.memoizedProps;
    if (((n = n.compare), (n = n !== null ? n : Xi), n(s, r) && e.ref === t.ref))
      return Sn(e, t, o);
  }
  return (t.flags |= 1), (e = Xn(i, r)), (e.ref = t.ref), (e.return = t), (t.child = e);
}
function Wv(e, t, n, r, o) {
  if (e !== null) {
    var i = e.memoizedProps;
    if (Xi(i, r) && e.ref === t.ref)
      if (((it = !1), (t.pendingProps = r = i), (e.lanes & o) !== 0)) e.flags & 131072 && (it = !0);
      else return (t.lanes = e.lanes), Sn(e, t, o);
  }
  return gf(e, t, n, r, o);
}
function Gv(e, t, n) {
  var r = t.pendingProps,
    o = r.children,
    i = e !== null ? e.memoizedState : null;
  if (r.mode === "hidden")
    if (!(t.mode & 1))
      (t.memoizedState = { baseLanes: 0, cachePool: null, transitions: null }),
        he(uo, ct),
        (ct |= n);
    else {
      if (!(n & 1073741824))
        return (
          (e = i !== null ? i.baseLanes | n : n),
          (t.lanes = t.childLanes = 1073741824),
          (t.memoizedState = { baseLanes: e, cachePool: null, transitions: null }),
          (t.updateQueue = null),
          he(uo, ct),
          (ct |= e),
          null
        );
      (t.memoizedState = { baseLanes: 0, cachePool: null, transitions: null }),
        (r = i !== null ? i.baseLanes : n),
        he(uo, ct),
        (ct |= r);
    }
  else
    i !== null ? ((r = i.baseLanes | n), (t.memoizedState = null)) : (r = n), he(uo, ct), (ct |= r);
  return Je(e, t, o, n), t.child;
}
function Kv(e, t) {
  var n = t.ref;
  ((e === null && n !== null) || (e !== null && e.ref !== n)) &&
    ((t.flags |= 512), (t.flags |= 2097152));
}
function gf(e, t, n, r, o) {
  var i = lt(n) ? Nr : Qe.current;
  return (
    (i = Mo(t, i)),
    Eo(t, o),
    (n = Gd(e, t, n, r, i, o)),
    (r = Kd()),
    e !== null && !it
      ? ((t.updateQueue = e.updateQueue), (t.flags &= -2053), (e.lanes &= ~o), Sn(e, t, o))
      : (ve && r && Id(t), (t.flags |= 1), Je(e, t, n, o), t.child)
  );
}
function hm(e, t, n, r, o) {
  if (lt(n)) {
    var i = !0;
    rl(t);
  } else i = !1;
  if ((Eo(t, o), t.stateNode === null)) Ma(e, t), Bv(t, n, r), pf(t, n, r, o), (r = !0);
  else if (e === null) {
    var s = t.stateNode,
      a = t.memoizedProps;
    s.props = a;
    var l = s.context,
      u = n.contextType;
    typeof u == "object" && u !== null
      ? (u = _t(u))
      : ((u = lt(n) ? Nr : Qe.current), (u = Mo(t, u)));
    var c = n.getDerivedStateFromProps,
      f = typeof c == "function" || typeof s.getSnapshotBeforeUpdate == "function";
    f ||
      (typeof s.UNSAFE_componentWillReceiveProps != "function" &&
        typeof s.componentWillReceiveProps != "function") ||
      ((a !== r || l !== u) && am(t, s, r, u)),
      (Ln = !1);
    var d = t.memoizedState;
    (s.state = d),
      ll(t, r, s, o),
      (l = t.memoizedState),
      a !== r || d !== l || at.current || Ln
        ? (typeof c == "function" && (hf(t, n, c, r), (l = t.memoizedState)),
          (a = Ln || sm(t, n, a, r, d, l, u))
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
      Sv(e, t),
      (a = t.memoizedProps),
      (u = t.type === t.elementType ? a : Rt(t.type, a)),
      (s.props = u),
      (f = t.pendingProps),
      (d = s.context),
      (l = n.contextType),
      typeof l == "object" && l !== null
        ? (l = _t(l))
        : ((l = lt(n) ? Nr : Qe.current), (l = Mo(t, l)));
    var m = n.getDerivedStateFromProps;
    (c = typeof m == "function" || typeof s.getSnapshotBeforeUpdate == "function") ||
      (typeof s.UNSAFE_componentWillReceiveProps != "function" &&
        typeof s.componentWillReceiveProps != "function") ||
      ((a !== f || d !== l) && am(t, s, r, l)),
      (Ln = !1),
      (d = t.memoizedState),
      (s.state = d),
      ll(t, r, s, o);
    var y = t.memoizedState;
    a !== f || d !== y || at.current || Ln
      ? (typeof m == "function" && (hf(t, n, m, r), (y = t.memoizedState)),
        (u = Ln || sm(t, n, u, r, d, y, l) || !1)
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
  return yf(e, t, n, r, i, o);
}
function yf(e, t, n, r, o, i) {
  Kv(e, t);
  var s = (t.flags & 128) !== 0;
  if (!r && !s) return o && qp(t, n, !1), Sn(e, t, i);
  (r = t.stateNode), (R2.current = t);
  var a = s && typeof n.getDerivedStateFromError != "function" ? null : r.render();
  return (
    (t.flags |= 1),
    e !== null && s
      ? ((t.child = Ro(t, e.child, null, i)), (t.child = Ro(t, null, a, i)))
      : Je(e, t, a, i),
    (t.memoizedState = r.state),
    o && qp(t, n, !0),
    t.child
  );
}
function Yv(e) {
  var t = e.stateNode;
  t.pendingContext
    ? Qp(e, t.pendingContext, t.pendingContext !== t.context)
    : t.context && Qp(e, t.context, !1),
    Bd(e, t.containerInfo);
}
function pm(e, t, n, r, o) {
  return Ao(), Vd(o), (t.flags |= 256), Je(e, t, n, r), t.child;
}
var vf = { dehydrated: null, treeContext: null, retryLane: 0 };
function xf(e) {
  return { baseLanes: e, cachePool: null, transitions: null };
}
function Xv(e, t, n) {
  var r = t.pendingProps,
    o = xe.current,
    i = !1,
    s = (t.flags & 128) !== 0,
    a;
  if (
    ((a = s) || (a = e !== null && e.memoizedState === null ? !1 : (o & 2) !== 0),
    a ? ((i = !0), (t.flags &= -129)) : (e === null || e.memoizedState !== null) && (o |= 1),
    he(xe, o & 1),
    e === null)
  )
    return (
      ff(t),
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
                : (i = Zl(s, r, 0, null)),
              (e = br(e, r, n, null)),
              (i.return = t),
              (e.return = t),
              (i.sibling = e),
              (t.child = i),
              (t.child.memoizedState = xf(n)),
              (t.memoizedState = vf),
              e)
            : Zd(t, s))
    );
  if (((o = e.memoizedState), o !== null && ((a = o.dehydrated), a !== null)))
    return D2(e, t, s, r, a, o, n);
  if (i) {
    (i = r.fallback), (s = t.mode), (o = e.child), (a = o.sibling);
    var l = { mode: "hidden", children: r.children };
    return (
      !(s & 1) && t.child !== o
        ? ((r = t.child), (r.childLanes = 0), (r.pendingProps = l), (t.deletions = null))
        : ((r = Xn(o, l)), (r.subtreeFlags = o.subtreeFlags & 14680064)),
      a !== null ? (i = Xn(a, i)) : ((i = br(i, s, n, null)), (i.flags |= 2)),
      (i.return = t),
      (r.return = t),
      (r.sibling = i),
      (t.child = r),
      (r = i),
      (i = t.child),
      (s = e.child.memoizedState),
      (s =
        s === null
          ? xf(n)
          : { baseLanes: s.baseLanes | n, cachePool: null, transitions: s.transitions }),
      (i.memoizedState = s),
      (i.childLanes = e.childLanes & ~n),
      (t.memoizedState = vf),
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
function Zd(e, t) {
  return (t = Zl({ mode: "visible", children: t }, e.mode, 0, null)), (t.return = e), (e.child = t);
}
function Js(e, t, n, r) {
  return (
    r !== null && Vd(r),
    Ro(t, e.child, null, n),
    (e = Zd(t, t.pendingProps.children)),
    (e.flags |= 2),
    (t.memoizedState = null),
    e
  );
}
function D2(e, t, n, r, o, i, s) {
  if (n)
    return t.flags & 256
      ? ((t.flags &= -257), (r = Qu(Error(B(422)))), Js(e, t, s, r))
      : t.memoizedState !== null
        ? ((t.child = e.child), (t.flags |= 128), null)
        : ((i = r.fallback),
          (o = t.mode),
          (r = Zl({ mode: "visible", children: r.children }, o, 0, null)),
          (i = br(i, o, s, null)),
          (i.flags |= 2),
          (r.return = t),
          (i.return = t),
          (r.sibling = i),
          (t.child = r),
          t.mode & 1 && Ro(t, e.child, null, s),
          (t.child.memoizedState = xf(s)),
          (t.memoizedState = vf),
          i);
  if (!(t.mode & 1)) return Js(e, t, s, null);
  if (o.data === "$!") {
    if (((r = o.nextSibling && o.nextSibling.dataset), r)) var a = r.dgst;
    return (r = a), (i = Error(B(419))), (r = Qu(i, r, void 0)), Js(e, t, s, r);
  }
  if (((a = (s & e.childLanes) !== 0), it || a)) {
    if (((r = Oe), r !== null)) {
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
        o !== 0 && o !== i.retryLane && ((i.retryLane = o), wn(e, o), jt(r, e, o, -1));
    }
    return nh(), (r = Qu(Error(B(421)))), Js(e, t, s, r);
  }
  return o.data === "$?"
    ? ((t.flags |= 128), (t.child = e.child), (t = G2.bind(null, e)), (o._reactRetry = t), null)
    : ((e = i.treeContext),
      (ft = Wn(o.nextSibling)),
      (dt = t),
      (ve = !0),
      (Lt = null),
      e !== null &&
        ((St[Et++] = fn),
        (St[Et++] = dn),
        (St[Et++] = Pr),
        (fn = e.id),
        (dn = e.overflow),
        (Pr = t)),
      (t = Zd(t, r.children)),
      (t.flags |= 4096),
      t);
}
function mm(e, t, n) {
  e.lanes |= t;
  var r = e.alternate;
  r !== null && (r.lanes |= t), df(e.return, t, n);
}
function qu(e, t, n, r, o) {
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
function Zv(e, t, n) {
  var r = t.pendingProps,
    o = r.revealOrder,
    i = r.tail;
  if ((Je(e, t, r.children, n), (r = xe.current), r & 2)) (r = (r & 1) | 2), (t.flags |= 128);
  else {
    if (e !== null && e.flags & 128)
      e: for (e = t.child; e !== null; ) {
        if (e.tag === 13) e.memoizedState !== null && mm(e, n, t);
        else if (e.tag === 19) mm(e, n, t);
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
    switch (o) {
      case "forwards":
        for (n = t.child, o = null; n !== null; )
          (e = n.alternate), e !== null && ul(e) === null && (o = n), (n = n.sibling);
        (n = o),
          n === null ? ((o = t.child), (t.child = null)) : ((o = n.sibling), (n.sibling = null)),
          qu(t, !1, o, n, i);
        break;
      case "backwards":
        for (n = null, o = t.child, t.child = null; o !== null; ) {
          if (((e = o.alternate), e !== null && ul(e) === null)) {
            t.child = o;
            break;
          }
          (e = o.sibling), (o.sibling = n), (n = o), (o = e);
        }
        qu(t, !0, n, null, i);
        break;
      case "together":
        qu(t, !1, null, null, void 0);
        break;
      default:
        t.memoizedState = null;
    }
  return t.child;
}
function Ma(e, t) {
  !(t.mode & 1) && e !== null && ((e.alternate = null), (t.alternate = null), (t.flags |= 2));
}
function Sn(e, t, n) {
  if ((e !== null && (t.dependencies = e.dependencies), (Ar |= t.lanes), !(n & t.childLanes)))
    return null;
  if (e !== null && t.child !== e.child) throw Error(B(153));
  if (t.child !== null) {
    for (e = t.child, n = Xn(e, e.pendingProps), t.child = n, n.return = t; e.sibling !== null; )
      (e = e.sibling), (n = n.sibling = Xn(e, e.pendingProps)), (n.return = t);
    n.sibling = null;
  }
  return t.child;
}
function I2(e, t, n) {
  switch (t.tag) {
    case 3:
      Yv(t), Ao();
      break;
    case 5:
      Ev(t);
      break;
    case 1:
      lt(t.type) && rl(t);
      break;
    case 4:
      Bd(t, t.stateNode.containerInfo);
      break;
    case 10:
      var r = t.type._context,
        o = t.memoizedProps.value;
      he(sl, r._currentValue), (r._currentValue = o);
      break;
    case 13:
      if (((r = t.memoizedState), r !== null))
        return r.dehydrated !== null
          ? (he(xe, xe.current & 1), (t.flags |= 128), null)
          : n & t.child.childLanes
            ? Xv(e, t, n)
            : (he(xe, xe.current & 1), (e = Sn(e, t, n)), e !== null ? e.sibling : null);
      he(xe, xe.current & 1);
      break;
    case 19:
      if (((r = (n & t.childLanes) !== 0), e.flags & 128)) {
        if (r) return Zv(e, t, n);
        t.flags |= 128;
      }
      if (
        ((o = t.memoizedState),
        o !== null && ((o.rendering = null), (o.tail = null), (o.lastEffect = null)),
        he(xe, xe.current),
        r)
      )
        break;
      return null;
    case 22:
    case 23:
      return (t.lanes = 0), Gv(e, t, n);
  }
  return Sn(e, t, n);
}
var Qv, wf, qv, Jv;
Qv = function (e, t) {
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
wf = function () {};
qv = function (e, t, n, r) {
  var o = e.memoizedProps;
  if (o !== r) {
    (e = t.stateNode), xr(Zt.current);
    var i = null;
    switch (n) {
      case "input":
        (o = $c(e, o)), (r = $c(e, r)), (i = []);
        break;
      case "select":
        (o = Ee({}, o, { value: void 0 })), (r = Ee({}, r, { value: void 0 })), (i = []);
        break;
      case "textarea":
        (o = Uc(e, o)), (r = Uc(e, r)), (i = []);
        break;
      default:
        typeof o.onClick != "function" && typeof r.onClick == "function" && (e.onclick = tl);
    }
    Gc(n, r);
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
            (Bi.hasOwnProperty(u) ? i || (i = []) : (i = i || []).push(u, null));
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
                (Bi.hasOwnProperty(u)
                  ? (l != null && u === "onScroll" && ge("scroll", e), i || a === l || (i = []))
                  : (i = i || []).push(u, l));
    }
    n && (i = i || []).push("style", n);
    var u = i;
    (t.updateQueue = u) && (t.flags |= 4);
  }
};
Jv = function (e, t, n, r) {
  n !== r && (t.flags |= 4);
};
function ai(e, t) {
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
function Ke(e) {
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
function L2(e, t, n) {
  var r = t.pendingProps;
  switch ((Ld(t), t.tag)) {
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
      return Ke(t), null;
    case 1:
      return lt(t.type) && nl(), Ke(t), null;
    case 3:
      return (
        (r = t.stateNode),
        Do(),
        ye(at),
        ye(Qe),
        Ud(),
        r.pendingContext && ((r.context = r.pendingContext), (r.pendingContext = null)),
        (e === null || e.child === null) &&
          (Qs(t)
            ? (t.flags |= 4)
            : e === null ||
              (e.memoizedState.isDehydrated && !(t.flags & 256)) ||
              ((t.flags |= 1024), Lt !== null && (Nf(Lt), (Lt = null)))),
        wf(e, t),
        Ke(t),
        null
      );
    case 5:
      Hd(t);
      var o = xr(es.current);
      if (((n = t.type), e !== null && t.stateNode != null))
        qv(e, t, n, r, o), e.ref !== t.ref && ((t.flags |= 512), (t.flags |= 2097152));
      else {
        if (!r) {
          if (t.stateNode === null) throw Error(B(166));
          return Ke(t), null;
        }
        if (((e = xr(Zt.current)), Qs(t))) {
          (r = t.stateNode), (n = t.type);
          var i = t.memoizedProps;
          switch (((r[Kt] = t), (r[qi] = i), (e = (t.mode & 1) !== 0), n)) {
            case "dialog":
              ge("cancel", r), ge("close", r);
              break;
            case "iframe":
            case "object":
            case "embed":
              ge("load", r);
              break;
            case "video":
            case "audio":
              for (o = 0; o < wi.length; o++) ge(wi[o], r);
              break;
            case "source":
              ge("error", r);
              break;
            case "img":
            case "image":
            case "link":
              ge("error", r), ge("load", r);
              break;
            case "details":
              ge("toggle", r);
              break;
            case "input":
              bp(r, i), ge("invalid", r);
              break;
            case "select":
              (r._wrapperState = { wasMultiple: !!i.multiple }), ge("invalid", r);
              break;
            case "textarea":
              Tp(r, i), ge("invalid", r);
          }
          Gc(n, i), (o = null);
          for (var s in i)
            if (i.hasOwnProperty(s)) {
              var a = i[s];
              s === "children"
                ? typeof a == "string"
                  ? r.textContent !== a &&
                    (i.suppressHydrationWarning !== !0 && Zs(r.textContent, a, e),
                    (o = ["children", a]))
                  : typeof a == "number" &&
                    r.textContent !== "" + a &&
                    (i.suppressHydrationWarning !== !0 && Zs(r.textContent, a, e),
                    (o = ["children", "" + a]))
                : Bi.hasOwnProperty(s) && a != null && s === "onScroll" && ge("scroll", r);
            }
          switch (n) {
            case "input":
              Bs(r), kp(r, i, !0);
              break;
            case "textarea":
              Bs(r), _p(r);
              break;
            case "select":
            case "option":
              break;
            default:
              typeof i.onClick == "function" && (r.onclick = tl);
          }
          (r = o), (t.updateQueue = r), r !== null && (t.flags |= 4);
        } else {
          (s = o.nodeType === 9 ? o : o.ownerDocument),
            e === "http://www.w3.org/1999/xhtml" && (e = _0(n)),
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
            (e[qi] = r),
            Qv(e, t, !1, !1),
            (t.stateNode = e);
          e: {
            switch (((s = Kc(n, r)), n)) {
              case "dialog":
                ge("cancel", e), ge("close", e), (o = r);
                break;
              case "iframe":
              case "object":
              case "embed":
                ge("load", e), (o = r);
                break;
              case "video":
              case "audio":
                for (o = 0; o < wi.length; o++) ge(wi[o], e);
                o = r;
                break;
              case "source":
                ge("error", e), (o = r);
                break;
              case "img":
              case "image":
              case "link":
                ge("error", e), ge("load", e), (o = r);
                break;
              case "details":
                ge("toggle", e), (o = r);
                break;
              case "input":
                bp(e, r), (o = $c(e, r)), ge("invalid", e);
                break;
              case "option":
                o = r;
                break;
              case "select":
                (e._wrapperState = { wasMultiple: !!r.multiple }),
                  (o = Ee({}, r, { value: void 0 })),
                  ge("invalid", e);
                break;
              case "textarea":
                Tp(e, r), (o = Uc(e, r)), ge("invalid", e);
                break;
              default:
                o = r;
            }
            Gc(n, o), (a = o);
            for (i in a)
              if (a.hasOwnProperty(i)) {
                var l = a[i];
                i === "style"
                  ? M0(e, l)
                  : i === "dangerouslySetInnerHTML"
                    ? ((l = l ? l.__html : void 0), l != null && N0(e, l))
                    : i === "children"
                      ? typeof l == "string"
                        ? (n !== "textarea" || l !== "") && Hi(e, l)
                        : typeof l == "number" && Hi(e, "" + l)
                      : i !== "suppressContentEditableWarning" &&
                        i !== "suppressHydrationWarning" &&
                        i !== "autoFocus" &&
                        (Bi.hasOwnProperty(i)
                          ? l != null && i === "onScroll" && ge("scroll", e)
                          : l != null && wd(e, i, l, s));
              }
            switch (n) {
              case "input":
                Bs(e), kp(e, r, !1);
                break;
              case "textarea":
                Bs(e), _p(e);
                break;
              case "option":
                r.value != null && e.setAttribute("value", "" + Qn(r.value));
                break;
              case "select":
                (e.multiple = !!r.multiple),
                  (i = r.value),
                  i != null
                    ? vo(e, !!r.multiple, i, !1)
                    : r.defaultValue != null && vo(e, !!r.multiple, r.defaultValue, !0);
                break;
              default:
                typeof o.onClick == "function" && (e.onclick = tl);
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
      return Ke(t), null;
    case 6:
      if (e && t.stateNode != null) Jv(e, t, e.memoizedProps, r);
      else {
        if (typeof r != "string" && t.stateNode === null) throw Error(B(166));
        if (((n = xr(es.current)), xr(Zt.current), Qs(t))) {
          if (
            ((r = t.stateNode),
            (n = t.memoizedProps),
            (r[Kt] = t),
            (i = r.nodeValue !== n) && ((e = dt), e !== null))
          )
            switch (e.tag) {
              case 3:
                Zs(r.nodeValue, n, (e.mode & 1) !== 0);
                break;
              case 5:
                e.memoizedProps.suppressHydrationWarning !== !0 &&
                  Zs(r.nodeValue, n, (e.mode & 1) !== 0);
            }
          i && (t.flags |= 4);
        } else
          (r = (n.nodeType === 9 ? n : n.ownerDocument).createTextNode(r)),
            (r[Kt] = t),
            (t.stateNode = r);
      }
      return Ke(t), null;
    case 13:
      if (
        (ye(xe),
        (r = t.memoizedState),
        e === null || (e.memoizedState !== null && e.memoizedState.dehydrated !== null))
      ) {
        if (ve && ft !== null && t.mode & 1 && !(t.flags & 128))
          yv(), Ao(), (t.flags |= 98560), (i = !1);
        else if (((i = Qs(t)), r !== null && r.dehydrated !== null)) {
          if (e === null) {
            if (!i) throw Error(B(318));
            if (((i = t.memoizedState), (i = i !== null ? i.dehydrated : null), !i))
              throw Error(B(317));
            i[Kt] = t;
          } else Ao(), !(t.flags & 128) && (t.memoizedState = null), (t.flags |= 4);
          Ke(t), (i = !1);
        } else Lt !== null && (Nf(Lt), (Lt = null)), (i = !0);
        if (!i) return t.flags & 65536 ? t : null;
      }
      return t.flags & 128
        ? ((t.lanes = n), t)
        : ((r = r !== null),
          r !== (e !== null && e.memoizedState !== null) &&
            r &&
            ((t.child.flags |= 8192),
            t.mode & 1 && (e === null || xe.current & 1 ? De === 0 && (De = 3) : nh())),
          t.updateQueue !== null && (t.flags |= 4),
          Ke(t),
          null);
    case 4:
      return Do(), wf(e, t), e === null && Zi(t.stateNode.containerInfo), Ke(t), null;
    case 10:
      return Fd(t.type._context), Ke(t), null;
    case 17:
      return lt(t.type) && nl(), Ke(t), null;
    case 19:
      if ((ye(xe), (i = t.memoizedState), i === null)) return Ke(t), null;
      if (((r = (t.flags & 128) !== 0), (s = i.rendering), s === null))
        if (r) ai(i, !1);
        else {
          if (De !== 0 || (e !== null && e.flags & 128))
            for (e = t.child; e !== null; ) {
              if (((s = ul(e)), s !== null)) {
                for (
                  t.flags |= 128,
                    ai(i, !1),
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
                return he(xe, (xe.current & 1) | 2), t.child;
              }
              e = e.sibling;
            }
          i.tail !== null &&
            Ne() > Lo &&
            ((t.flags |= 128), (r = !0), ai(i, !1), (t.lanes = 4194304));
        }
      else {
        if (!r)
          if (((e = ul(s)), e !== null)) {
            if (
              ((t.flags |= 128),
              (r = !0),
              (n = e.updateQueue),
              n !== null && ((t.updateQueue = n), (t.flags |= 4)),
              ai(i, !0),
              i.tail === null && i.tailMode === "hidden" && !s.alternate && !ve)
            )
              return Ke(t), null;
          } else
            2 * Ne() - i.renderingStartTime > Lo &&
              n !== 1073741824 &&
              ((t.flags |= 128), (r = !0), ai(i, !1), (t.lanes = 4194304));
        i.isBackwards
          ? ((s.sibling = t.child), (t.child = s))
          : ((n = i.last), n !== null ? (n.sibling = s) : (t.child = s), (i.last = s));
      }
      return i.tail !== null
        ? ((t = i.tail),
          (i.rendering = t),
          (i.tail = t.sibling),
          (i.renderingStartTime = Ne()),
          (t.sibling = null),
          (n = xe.current),
          he(xe, r ? (n & 1) | 2 : n & 1),
          t)
        : (Ke(t), null);
    case 22:
    case 23:
      return (
        th(),
        (r = t.memoizedState !== null),
        e !== null && (e.memoizedState !== null) !== r && (t.flags |= 8192),
        r && t.mode & 1
          ? ct & 1073741824 && (Ke(t), t.subtreeFlags & 6 && (t.flags |= 8192))
          : Ke(t),
        null
      );
    case 24:
      return null;
    case 25:
      return null;
  }
  throw Error(B(156, t.tag));
}
function V2(e, t) {
  switch ((Ld(t), t.tag)) {
    case 1:
      return (
        lt(t.type) && nl(), (e = t.flags), e & 65536 ? ((t.flags = (e & -65537) | 128), t) : null
      );
    case 3:
      return (
        Do(),
        ye(at),
        ye(Qe),
        Ud(),
        (e = t.flags),
        e & 65536 && !(e & 128) ? ((t.flags = (e & -65537) | 128), t) : null
      );
    case 5:
      return Hd(t), null;
    case 13:
      if ((ye(xe), (e = t.memoizedState), e !== null && e.dehydrated !== null)) {
        if (t.alternate === null) throw Error(B(340));
        Ao();
      }
      return (e = t.flags), e & 65536 ? ((t.flags = (e & -65537) | 128), t) : null;
    case 19:
      return ye(xe), null;
    case 4:
      return Do(), null;
    case 10:
      return Fd(t.type._context), null;
    case 22:
    case 23:
      return th(), null;
    case 24:
      return null;
    default:
      return null;
  }
}
var ea = !1,
  Ze = !1,
  O2 = typeof WeakSet == "function" ? WeakSet : Set,
  G = null;
function lo(e, t) {
  var n = e.ref;
  if (n !== null)
    if (typeof n == "function")
      try {
        n(null);
      } catch (r) {
        ke(e, t, r);
      }
    else n.current = null;
}
function Sf(e, t, n) {
  try {
    n();
  } catch (r) {
    ke(e, t, r);
  }
}
var gm = !1;
function j2(e, t) {
  if (((rf = qa), (e = ov()), Dd(e))) {
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
              var m;
              f !== n || (o !== 0 && f.nodeType !== 3) || (a = s + o),
                f !== i || (r !== 0 && f.nodeType !== 3) || (l = s + r),
                f.nodeType === 3 && (s += f.nodeValue.length),
                (m = f.firstChild) !== null;

            )
              (d = f), (f = m);
            for (;;) {
              if (f === e) break t;
              if (
                (d === n && ++u === o && (a = s),
                d === i && ++c === r && (l = s),
                (m = f.nextSibling) !== null)
              )
                break;
              (f = d), (d = f.parentNode);
            }
            f = m;
          }
          n = a === -1 || l === -1 ? null : { start: a, end: l };
        } else n = null;
      }
    n = n || { start: 0, end: 0 };
  } else n = null;
  for (of = { focusedElem: e, selectionRange: n }, qa = !1, G = t; G !== null; )
    if (((t = G), (e = t.child), (t.subtreeFlags & 1028) !== 0 && e !== null))
      (e.return = t), (G = e);
    else
      for (; G !== null; ) {
        t = G;
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
                  var g = y.memoizedProps,
                    w = y.memoizedState,
                    h = t.stateNode,
                    p = h.getSnapshotBeforeUpdate(t.elementType === t.type ? g : Rt(t.type, g), w);
                  h.__reactInternalSnapshotBeforeUpdate = p;
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
          ke(t, t.return, S);
        }
        if (((e = t.sibling), e !== null)) {
          (e.return = t.return), (G = e);
          break;
        }
        G = t.return;
      }
  return (y = gm), (gm = !1), y;
}
function Di(e, t, n) {
  var r = t.updateQueue;
  if (((r = r !== null ? r.lastEffect : null), r !== null)) {
    var o = (r = r.next);
    do {
      if ((o.tag & e) === e) {
        var i = o.destroy;
        (o.destroy = void 0), i !== void 0 && Sf(t, n, i);
      }
      o = o.next;
    } while (o !== r);
  }
}
function Yl(e, t) {
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
function Ef(e) {
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
function ex(e) {
  var t = e.alternate;
  t !== null && ((e.alternate = null), ex(t)),
    (e.child = null),
    (e.deletions = null),
    (e.sibling = null),
    e.tag === 5 &&
      ((t = e.stateNode),
      t !== null && (delete t[Kt], delete t[qi], delete t[lf], delete t[w2], delete t[S2])),
    (e.stateNode = null),
    (e.return = null),
    (e.dependencies = null),
    (e.memoizedProps = null),
    (e.memoizedState = null),
    (e.pendingProps = null),
    (e.stateNode = null),
    (e.updateQueue = null);
}
function tx(e) {
  return e.tag === 5 || e.tag === 3 || e.tag === 4;
}
function ym(e) {
  e: for (;;) {
    for (; e.sibling === null; ) {
      if (e.return === null || tx(e.return)) return null;
      e = e.return;
    }
    for (e.sibling.return = e.return, e = e.sibling; e.tag !== 5 && e.tag !== 6 && e.tag !== 18; ) {
      if (e.flags & 2 || e.child === null || e.tag === 4) continue e;
      (e.child.return = e), (e = e.child);
    }
    if (!(e.flags & 2)) return e.stateNode;
  }
}
function Cf(e, t, n) {
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
          n != null || t.onclick !== null || (t.onclick = tl));
  else if (r !== 4 && ((e = e.child), e !== null))
    for (Cf(e, t, n), e = e.sibling; e !== null; ) Cf(e, t, n), (e = e.sibling);
}
function bf(e, t, n) {
  var r = e.tag;
  if (r === 5 || r === 6) (e = e.stateNode), t ? n.insertBefore(e, t) : n.appendChild(e);
  else if (r !== 4 && ((e = e.child), e !== null))
    for (bf(e, t, n), e = e.sibling; e !== null; ) bf(e, t, n), (e = e.sibling);
}
var Fe = null,
  Dt = !1;
function _n(e, t, n) {
  for (n = n.child; n !== null; ) nx(e, t, n), (n = n.sibling);
}
function nx(e, t, n) {
  if (Xt && typeof Xt.onCommitFiberUnmount == "function")
    try {
      Xt.onCommitFiberUnmount(zl, n);
    } catch {}
  switch (n.tag) {
    case 5:
      Ze || lo(n, t);
    case 6:
      var r = Fe,
        o = Dt;
      (Fe = null),
        _n(e, t, n),
        (Fe = r),
        (Dt = o),
        Fe !== null &&
          (Dt
            ? ((e = Fe),
              (n = n.stateNode),
              e.nodeType === 8 ? e.parentNode.removeChild(n) : e.removeChild(n))
            : Fe.removeChild(n.stateNode));
      break;
    case 18:
      Fe !== null &&
        (Dt
          ? ((e = Fe),
            (n = n.stateNode),
            e.nodeType === 8 ? Wu(e.parentNode, n) : e.nodeType === 1 && Wu(e, n),
            Ki(e))
          : Wu(Fe, n.stateNode));
      break;
    case 4:
      (r = Fe),
        (o = Dt),
        (Fe = n.stateNode.containerInfo),
        (Dt = !0),
        _n(e, t, n),
        (Fe = r),
        (Dt = o);
      break;
    case 0:
    case 11:
    case 14:
    case 15:
      if (!Ze && ((r = n.updateQueue), r !== null && ((r = r.lastEffect), r !== null))) {
        o = r = r.next;
        do {
          var i = o,
            s = i.destroy;
          (i = i.tag), s !== void 0 && (i & 2 || i & 4) && Sf(n, t, s), (o = o.next);
        } while (o !== r);
      }
      _n(e, t, n);
      break;
    case 1:
      if (!Ze && (lo(n, t), (r = n.stateNode), typeof r.componentWillUnmount == "function"))
        try {
          (r.props = n.memoizedProps), (r.state = n.memoizedState), r.componentWillUnmount();
        } catch (a) {
          ke(n, t, a);
        }
      _n(e, t, n);
      break;
    case 21:
      _n(e, t, n);
      break;
    case 22:
      n.mode & 1
        ? ((Ze = (r = Ze) || n.memoizedState !== null), _n(e, t, n), (Ze = r))
        : _n(e, t, n);
      break;
    default:
      _n(e, t, n);
  }
}
function vm(e) {
  var t = e.updateQueue;
  if (t !== null) {
    e.updateQueue = null;
    var n = e.stateNode;
    n === null && (n = e.stateNode = new O2()),
      t.forEach(function (r) {
        var o = K2.bind(null, e, r);
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
              (Fe = a.stateNode), (Dt = !1);
              break e;
            case 3:
              (Fe = a.stateNode.containerInfo), (Dt = !0);
              break e;
            case 4:
              (Fe = a.stateNode.containerInfo), (Dt = !0);
              break e;
          }
          a = a.return;
        }
        if (Fe === null) throw Error(B(160));
        nx(i, s, o), (Fe = null), (Dt = !1);
        var l = o.alternate;
        l !== null && (l.return = null), (o.return = null);
      } catch (u) {
        ke(o, t, u);
      }
    }
  if (t.subtreeFlags & 12854) for (t = t.child; t !== null; ) rx(t, e), (t = t.sibling);
}
function rx(e, t) {
  var n = e.alternate,
    r = e.flags;
  switch (e.tag) {
    case 0:
    case 11:
    case 14:
    case 15:
      if ((Mt(t, e), Ut(e), r & 4)) {
        try {
          Di(3, e, e.return), Yl(3, e);
        } catch (g) {
          ke(e, e.return, g);
        }
        try {
          Di(5, e, e.return);
        } catch (g) {
          ke(e, e.return, g);
        }
      }
      break;
    case 1:
      Mt(t, e), Ut(e), r & 512 && n !== null && lo(n, n.return);
      break;
    case 5:
      if ((Mt(t, e), Ut(e), r & 512 && n !== null && lo(n, n.return), e.flags & 32)) {
        var o = e.stateNode;
        try {
          Hi(o, "");
        } catch (g) {
          ke(e, e.return, g);
        }
      }
      if (r & 4 && ((o = e.stateNode), o != null)) {
        var i = e.memoizedProps,
          s = n !== null ? n.memoizedProps : i,
          a = e.type,
          l = e.updateQueue;
        if (((e.updateQueue = null), l !== null))
          try {
            a === "input" && i.type === "radio" && i.name != null && k0(o, i), Kc(a, s);
            var u = Kc(a, i);
            for (s = 0; s < l.length; s += 2) {
              var c = l[s],
                f = l[s + 1];
              c === "style"
                ? M0(o, f)
                : c === "dangerouslySetInnerHTML"
                  ? N0(o, f)
                  : c === "children"
                    ? Hi(o, f)
                    : wd(o, c, f, u);
            }
            switch (a) {
              case "input":
                Bc(o, i);
                break;
              case "textarea":
                T0(o, i);
                break;
              case "select":
                var d = o._wrapperState.wasMultiple;
                o._wrapperState.wasMultiple = !!i.multiple;
                var m = i.value;
                m != null
                  ? vo(o, !!i.multiple, m, !1)
                  : d !== !!i.multiple &&
                    (i.defaultValue != null
                      ? vo(o, !!i.multiple, i.defaultValue, !0)
                      : vo(o, !!i.multiple, i.multiple ? [] : "", !1));
            }
            o[qi] = i;
          } catch (g) {
            ke(e, e.return, g);
          }
      }
      break;
    case 6:
      if ((Mt(t, e), Ut(e), r & 4)) {
        if (e.stateNode === null) throw Error(B(162));
        (o = e.stateNode), (i = e.memoizedProps);
        try {
          o.nodeValue = i;
        } catch (g) {
          ke(e, e.return, g);
        }
      }
      break;
    case 3:
      if ((Mt(t, e), Ut(e), r & 4 && n !== null && n.memoizedState.isDehydrated))
        try {
          Ki(t.containerInfo);
        } catch (g) {
          ke(e, e.return, g);
        }
      break;
    case 4:
      Mt(t, e), Ut(e);
      break;
    case 13:
      Mt(t, e),
        Ut(e),
        (o = e.child),
        o.flags & 8192 &&
          ((i = o.memoizedState !== null),
          (o.stateNode.isHidden = i),
          !i || (o.alternate !== null && o.alternate.memoizedState !== null) || (Jd = Ne())),
        r & 4 && vm(e);
      break;
    case 22:
      if (
        ((c = n !== null && n.memoizedState !== null),
        e.mode & 1 ? ((Ze = (u = Ze) || c), Mt(t, e), (Ze = u)) : Mt(t, e),
        Ut(e),
        r & 8192)
      ) {
        if (((u = e.memoizedState !== null), (e.stateNode.isHidden = u) && !c && e.mode & 1))
          for (G = e, c = e.child; c !== null; ) {
            for (f = G = c; G !== null; ) {
              switch (((d = G), (m = d.child), d.tag)) {
                case 0:
                case 11:
                case 14:
                case 15:
                  Di(4, d, d.return);
                  break;
                case 1:
                  lo(d, d.return);
                  var y = d.stateNode;
                  if (typeof y.componentWillUnmount == "function") {
                    (r = d), (n = d.return);
                    try {
                      (t = r),
                        (y.props = t.memoizedProps),
                        (y.state = t.memoizedState),
                        y.componentWillUnmount();
                    } catch (g) {
                      ke(r, n, g);
                    }
                  }
                  break;
                case 5:
                  lo(d, d.return);
                  break;
                case 22:
                  if (d.memoizedState !== null) {
                    wm(f);
                    continue;
                  }
              }
              m !== null ? ((m.return = d), (G = m)) : wm(f);
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
                      (a.style.display = P0("display", s)));
              } catch (g) {
                ke(e, e.return, g);
              }
            }
          } else if (f.tag === 6) {
            if (c === null)
              try {
                f.stateNode.nodeValue = u ? "" : f.memoizedProps;
              } catch (g) {
                ke(e, e.return, g);
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
      Mt(t, e), Ut(e), r & 4 && vm(e);
      break;
    case 21:
      break;
    default:
      Mt(t, e), Ut(e);
  }
}
function Ut(e) {
  var t = e.flags;
  if (t & 2) {
    try {
      e: {
        for (var n = e.return; n !== null; ) {
          if (tx(n)) {
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
          r.flags & 32 && (Hi(o, ""), (r.flags &= -33));
          var i = ym(e);
          bf(e, i, o);
          break;
        case 3:
        case 4:
          var s = r.stateNode.containerInfo,
            a = ym(e);
          Cf(e, a, s);
          break;
        default:
          throw Error(B(161));
      }
    } catch (l) {
      ke(e, e.return, l);
    }
    e.flags &= -3;
  }
  t & 4096 && (e.flags &= -4097);
}
function F2(e, t, n) {
  (G = e), ox(e);
}
function ox(e, t, n) {
  for (var r = (e.mode & 1) !== 0; G !== null; ) {
    var o = G,
      i = o.child;
    if (o.tag === 22 && r) {
      var s = o.memoizedState !== null || ea;
      if (!s) {
        var a = o.alternate,
          l = (a !== null && a.memoizedState !== null) || Ze;
        a = ea;
        var u = Ze;
        if (((ea = s), (Ze = l) && !u))
          for (G = o; G !== null; )
            (s = G),
              (l = s.child),
              s.tag === 22 && s.memoizedState !== null
                ? Sm(o)
                : l !== null
                  ? ((l.return = s), (G = l))
                  : Sm(o);
        for (; i !== null; ) (G = i), ox(i), (i = i.sibling);
        (G = o), (ea = a), (Ze = u);
      }
      xm(e);
    } else o.subtreeFlags & 8772 && i !== null ? ((i.return = o), (G = i)) : xm(e);
  }
}
function xm(e) {
  for (; G !== null; ) {
    var t = G;
    if (t.flags & 8772) {
      var n = t.alternate;
      try {
        if (t.flags & 8772)
          switch (t.tag) {
            case 0:
            case 11:
            case 15:
              Ze || Yl(5, t);
              break;
            case 1:
              var r = t.stateNode;
              if (t.flags & 4 && !Ze)
                if (n === null) r.componentDidMount();
                else {
                  var o = t.elementType === t.type ? n.memoizedProps : Rt(t.type, n.memoizedProps);
                  r.componentDidUpdate(o, n.memoizedState, r.__reactInternalSnapshotBeforeUpdate);
                }
              var i = t.updateQueue;
              i !== null && rm(t, i, r);
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
                rm(t, s, n);
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
                    f !== null && Ki(f);
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
        Ze || (t.flags & 512 && Ef(t));
      } catch (d) {
        ke(t, t.return, d);
      }
    }
    if (t === e) {
      G = null;
      break;
    }
    if (((n = t.sibling), n !== null)) {
      (n.return = t.return), (G = n);
      break;
    }
    G = t.return;
  }
}
function wm(e) {
  for (; G !== null; ) {
    var t = G;
    if (t === e) {
      G = null;
      break;
    }
    var n = t.sibling;
    if (n !== null) {
      (n.return = t.return), (G = n);
      break;
    }
    G = t.return;
  }
}
function Sm(e) {
  for (; G !== null; ) {
    var t = G;
    try {
      switch (t.tag) {
        case 0:
        case 11:
        case 15:
          var n = t.return;
          try {
            Yl(4, t);
          } catch (l) {
            ke(t, n, l);
          }
          break;
        case 1:
          var r = t.stateNode;
          if (typeof r.componentDidMount == "function") {
            var o = t.return;
            try {
              r.componentDidMount();
            } catch (l) {
              ke(t, o, l);
            }
          }
          var i = t.return;
          try {
            Ef(t);
          } catch (l) {
            ke(t, i, l);
          }
          break;
        case 5:
          var s = t.return;
          try {
            Ef(t);
          } catch (l) {
            ke(t, s, l);
          }
      }
    } catch (l) {
      ke(t, t.return, l);
    }
    if (t === e) {
      G = null;
      break;
    }
    var a = t.sibling;
    if (a !== null) {
      (a.return = t.return), (G = a);
      break;
    }
    G = t.return;
  }
}
var z2 = Math.ceil,
  dl = Tn.ReactCurrentDispatcher,
  Qd = Tn.ReactCurrentOwner,
  Tt = Tn.ReactCurrentBatchConfig,
  ie = 0,
  Oe = null,
  Pe = null,
  ze = 0,
  ct = 0,
  uo = tr(0),
  De = 0,
  os = null,
  Ar = 0,
  Xl = 0,
  qd = 0,
  Ii = null,
  ot = null,
  Jd = 0,
  Lo = 1 / 0,
  ln = null,
  hl = !1,
  kf = null,
  Kn = null,
  ta = !1,
  $n = null,
  pl = 0,
  Li = 0,
  Tf = null,
  Aa = -1,
  Ra = 0;
function et() {
  return ie & 6 ? Ne() : Aa !== -1 ? Aa : (Aa = Ne());
}
function Yn(e) {
  return e.mode & 1
    ? ie & 2 && ze !== 0
      ? ze & -ze
      : C2.transition !== null
        ? (Ra === 0 && (Ra = B0()), Ra)
        : ((e = le), e !== 0 || ((e = window.event), (e = e === void 0 ? 16 : X0(e.type))), e)
    : 1;
}
function jt(e, t, n, r) {
  if (50 < Li) throw ((Li = 0), (Tf = null), Error(B(185)));
  Cs(e, n, r),
    (!(ie & 2) || e !== Oe) &&
      (e === Oe && (!(ie & 2) && (Xl |= n), De === 4 && Fn(e, ze)),
      ut(e, r),
      n === 1 && ie === 0 && !(t.mode & 1) && ((Lo = Ne() + 500), Wl && nr()));
}
function ut(e, t) {
  var n = e.callbackNode;
  Cb(e, t);
  var r = Qa(e, e === Oe ? ze : 0);
  if (r === 0) n !== null && Mp(n), (e.callbackNode = null), (e.callbackPriority = 0);
  else if (((t = r & -r), e.callbackPriority !== t)) {
    if ((n != null && Mp(n), t === 1))
      e.tag === 0 ? E2(Em.bind(null, e)) : pv(Em.bind(null, e)),
        v2(function () {
          !(ie & 6) && nr();
        }),
        (n = null);
    else {
      switch (H0(r)) {
        case 1:
          n = kd;
          break;
        case 4:
          n = z0;
          break;
        case 16:
          n = Za;
          break;
        case 536870912:
          n = $0;
          break;
        default:
          n = Za;
      }
      n = dx(n, ix.bind(null, e));
    }
    (e.callbackPriority = t), (e.callbackNode = n);
  }
}
function ix(e, t) {
  if (((Aa = -1), (Ra = 0), ie & 6)) throw Error(B(327));
  var n = e.callbackNode;
  if (Co() && e.callbackNode !== n) return null;
  var r = Qa(e, e === Oe ? ze : 0);
  if (r === 0) return null;
  if (r & 30 || r & e.expiredLanes || t) t = ml(e, r);
  else {
    t = r;
    var o = ie;
    ie |= 2;
    var i = ax();
    (Oe !== e || ze !== t) && ((ln = null), (Lo = Ne() + 500), Cr(e, t));
    do
      try {
        H2();
        break;
      } catch (a) {
        sx(e, a);
      }
    while (!0);
    jd(), (dl.current = i), (ie = o), Pe !== null ? (t = 0) : ((Oe = null), (ze = 0), (t = De));
  }
  if (t !== 0) {
    if ((t === 2 && ((o = qc(e)), o !== 0 && ((r = o), (t = _f(e, o)))), t === 1))
      throw ((n = os), Cr(e, 0), Fn(e, r), ut(e, Ne()), n);
    if (t === 6) Fn(e, r);
    else {
      if (
        ((o = e.current.alternate),
        !(r & 30) &&
          !$2(o) &&
          ((t = ml(e, r)), t === 2 && ((i = qc(e)), i !== 0 && ((r = i), (t = _f(e, i)))), t === 1))
      )
        throw ((n = os), Cr(e, 0), Fn(e, r), ut(e, Ne()), n);
      switch (((e.finishedWork = o), (e.finishedLanes = r), t)) {
        case 0:
        case 1:
          throw Error(B(345));
        case 2:
          dr(e, ot, ln);
          break;
        case 3:
          if ((Fn(e, r), (r & 130023424) === r && ((t = Jd + 500 - Ne()), 10 < t))) {
            if (Qa(e, 0) !== 0) break;
            if (((o = e.suspendedLanes), (o & r) !== r)) {
              et(), (e.pingedLanes |= e.suspendedLanes & o);
              break;
            }
            e.timeoutHandle = af(dr.bind(null, e, ot, ln), t);
            break;
          }
          dr(e, ot, ln);
          break;
        case 4:
          if ((Fn(e, r), (r & 4194240) === r)) break;
          for (t = e.eventTimes, o = -1; 0 < r; ) {
            var s = 31 - Ot(r);
            (i = 1 << s), (s = t[s]), s > o && (o = s), (r &= ~i);
          }
          if (
            ((r = o),
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
                          : 1960 * z2(r / 1960)) - r),
            10 < r)
          ) {
            e.timeoutHandle = af(dr.bind(null, e, ot, ln), r);
            break;
          }
          dr(e, ot, ln);
          break;
        case 5:
          dr(e, ot, ln);
          break;
        default:
          throw Error(B(329));
      }
    }
  }
  return ut(e, Ne()), e.callbackNode === n ? ix.bind(null, e) : null;
}
function _f(e, t) {
  var n = Ii;
  return (
    e.current.memoizedState.isDehydrated && (Cr(e, t).flags |= 256),
    (e = ml(e, t)),
    e !== 2 && ((t = ot), (ot = n), t !== null && Nf(t)),
    e
  );
}
function Nf(e) {
  ot === null ? (ot = e) : ot.push.apply(ot, e);
}
function $2(e) {
  for (var t = e; ; ) {
    if (t.flags & 16384) {
      var n = t.updateQueue;
      if (n !== null && ((n = n.stores), n !== null))
        for (var r = 0; r < n.length; r++) {
          var o = n[r],
            i = o.getSnapshot;
          o = o.value;
          try {
            if (!zt(i(), o)) return !1;
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
function Fn(e, t) {
  for (
    t &= ~qd, t &= ~Xl, e.suspendedLanes |= t, e.pingedLanes &= ~t, e = e.expirationTimes;
    0 < t;

  ) {
    var n = 31 - Ot(t),
      r = 1 << n;
    (e[n] = -1), (t &= ~r);
  }
}
function Em(e) {
  if (ie & 6) throw Error(B(327));
  Co();
  var t = Qa(e, 0);
  if (!(t & 1)) return ut(e, Ne()), null;
  var n = ml(e, t);
  if (e.tag !== 0 && n === 2) {
    var r = qc(e);
    r !== 0 && ((t = r), (n = _f(e, r)));
  }
  if (n === 1) throw ((n = os), Cr(e, 0), Fn(e, t), ut(e, Ne()), n);
  if (n === 6) throw Error(B(345));
  return (
    (e.finishedWork = e.current.alternate), (e.finishedLanes = t), dr(e, ot, ln), ut(e, Ne()), null
  );
}
function eh(e, t) {
  var n = ie;
  ie |= 1;
  try {
    return e(t);
  } finally {
    (ie = n), ie === 0 && ((Lo = Ne() + 500), Wl && nr());
  }
}
function Rr(e) {
  $n !== null && $n.tag === 0 && !(ie & 6) && Co();
  var t = ie;
  ie |= 1;
  var n = Tt.transition,
    r = le;
  try {
    if (((Tt.transition = null), (le = 1), e)) return e();
  } finally {
    (le = r), (Tt.transition = n), (ie = t), !(ie & 6) && nr();
  }
}
function th() {
  (ct = uo.current), ye(uo);
}
function Cr(e, t) {
  (e.finishedWork = null), (e.finishedLanes = 0);
  var n = e.timeoutHandle;
  if ((n !== -1 && ((e.timeoutHandle = -1), y2(n)), Pe !== null))
    for (n = Pe.return; n !== null; ) {
      var r = n;
      switch ((Ld(r), r.tag)) {
        case 1:
          (r = r.type.childContextTypes), r != null && nl();
          break;
        case 3:
          Do(), ye(at), ye(Qe), Ud();
          break;
        case 5:
          Hd(r);
          break;
        case 4:
          Do();
          break;
        case 13:
          ye(xe);
          break;
        case 19:
          ye(xe);
          break;
        case 10:
          Fd(r.type._context);
          break;
        case 22:
        case 23:
          th();
      }
      n = n.return;
    }
  if (
    ((Oe = e),
    (Pe = e = Xn(e.current, null)),
    (ze = ct = t),
    (De = 0),
    (os = null),
    (qd = Xl = Ar = 0),
    (ot = Ii = null),
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
function sx(e, t) {
  do {
    var n = Pe;
    try {
      if ((jd(), (Na.current = fl), cl)) {
        for (var r = Se.memoizedState; r !== null; ) {
          var o = r.queue;
          o !== null && (o.pending = null), (r = r.next);
        }
        cl = !1;
      }
      if (
        ((Mr = 0),
        (Le = Re = Se = null),
        (Ri = !1),
        (ts = 0),
        (Qd.current = null),
        n === null || n.return === null)
      ) {
        (De = 1), (os = t), (Pe = null);
        break;
      }
      e: {
        var i = e,
          s = n.return,
          a = n,
          l = t;
        if (
          ((t = ze),
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
          var m = um(s);
          if (m !== null) {
            (m.flags &= -257), cm(m, s, a, i, t), m.mode & 1 && lm(i, u, t), (t = m), (l = u);
            var y = t.updateQueue;
            if (y === null) {
              var g = new Set();
              g.add(l), (t.updateQueue = g);
            } else y.add(l);
            break e;
          } else {
            if (!(t & 1)) {
              lm(i, u, t), nh();
              break e;
            }
            l = Error(B(426));
          }
        } else if (ve && a.mode & 1) {
          var w = um(s);
          if (w !== null) {
            !(w.flags & 65536) && (w.flags |= 256), cm(w, s, a, i, t), Vd(Io(l, a));
            break e;
          }
        }
        (i = l = Io(l, a)), De !== 4 && (De = 2), Ii === null ? (Ii = [i]) : Ii.push(i), (i = s);
        do {
          switch (i.tag) {
            case 3:
              (i.flags |= 65536), (t &= -t), (i.lanes |= t);
              var h = Hv(i, l, t);
              nm(i, h);
              break e;
            case 1:
              a = l;
              var p = i.type,
                x = i.stateNode;
              if (
                !(i.flags & 128) &&
                (typeof p.getDerivedStateFromError == "function" ||
                  (x !== null &&
                    typeof x.componentDidCatch == "function" &&
                    (Kn === null || !Kn.has(x))))
              ) {
                (i.flags |= 65536), (t &= -t), (i.lanes |= t);
                var S = Uv(i, a, t);
                nm(i, S);
                break e;
              }
          }
          i = i.return;
        } while (i !== null);
      }
      ux(n);
    } catch (E) {
      (t = E), Pe === n && n !== null && (Pe = n = n.return);
      continue;
    }
    break;
  } while (!0);
}
function ax() {
  var e = dl.current;
  return (dl.current = fl), e === null ? fl : e;
}
function nh() {
  (De === 0 || De === 3 || De === 2) && (De = 4),
    Oe === null || (!(Ar & 268435455) && !(Xl & 268435455)) || Fn(Oe, ze);
}
function ml(e, t) {
  var n = ie;
  ie |= 2;
  var r = ax();
  (Oe !== e || ze !== t) && ((ln = null), Cr(e, t));
  do
    try {
      B2();
      break;
    } catch (o) {
      sx(e, o);
    }
  while (!0);
  if ((jd(), (ie = n), (dl.current = r), Pe !== null)) throw Error(B(261));
  return (Oe = null), (ze = 0), De;
}
function B2() {
  for (; Pe !== null; ) lx(Pe);
}
function H2() {
  for (; Pe !== null && !pb(); ) lx(Pe);
}
function lx(e) {
  var t = fx(e.alternate, e, ct);
  (e.memoizedProps = e.pendingProps), t === null ? ux(e) : (Pe = t), (Qd.current = null);
}
function ux(e) {
  var t = e;
  do {
    var n = t.alternate;
    if (((e = t.return), t.flags & 32768)) {
      if (((n = V2(n, t)), n !== null)) {
        (n.flags &= 32767), (Pe = n);
        return;
      }
      if (e !== null) (e.flags |= 32768), (e.subtreeFlags = 0), (e.deletions = null);
      else {
        (De = 6), (Pe = null);
        return;
      }
    } else if (((n = L2(n, t, ct)), n !== null)) {
      Pe = n;
      return;
    }
    if (((t = t.sibling), t !== null)) {
      Pe = t;
      return;
    }
    Pe = t = e;
  } while (t !== null);
  De === 0 && (De = 5);
}
function dr(e, t, n) {
  var r = le,
    o = Tt.transition;
  try {
    (Tt.transition = null), (le = 1), U2(e, t, n, r);
  } finally {
    (Tt.transition = o), (le = r);
  }
  return null;
}
function U2(e, t, n, r) {
  do Co();
  while ($n !== null);
  if (ie & 6) throw Error(B(327));
  n = e.finishedWork;
  var o = e.finishedLanes;
  if (n === null) return null;
  if (((e.finishedWork = null), (e.finishedLanes = 0), n === e.current)) throw Error(B(177));
  (e.callbackNode = null), (e.callbackPriority = 0);
  var i = n.lanes | n.childLanes;
  if (
    (bb(e, i),
    e === Oe && ((Pe = Oe = null), (ze = 0)),
    (!(n.subtreeFlags & 2064) && !(n.flags & 2064)) ||
      ta ||
      ((ta = !0),
      dx(Za, function () {
        return Co(), null;
      })),
    (i = (n.flags & 15990) !== 0),
    n.subtreeFlags & 15990 || i)
  ) {
    (i = Tt.transition), (Tt.transition = null);
    var s = le;
    le = 1;
    var a = ie;
    (ie |= 4),
      (Qd.current = null),
      j2(e, n),
      rx(n, e),
      c2(of),
      (qa = !!rf),
      (of = rf = null),
      (e.current = n),
      F2(n),
      mb(),
      (ie = a),
      (le = s),
      (Tt.transition = i);
  } else e.current = n;
  if (
    (ta && ((ta = !1), ($n = e), (pl = o)),
    (i = e.pendingLanes),
    i === 0 && (Kn = null),
    vb(n.stateNode),
    ut(e, Ne()),
    t !== null)
  )
    for (r = e.onRecoverableError, n = 0; n < t.length; n++)
      (o = t[n]), r(o.value, { componentStack: o.stack, digest: o.digest });
  if (hl) throw ((hl = !1), (e = kf), (kf = null), e);
  return (
    pl & 1 && e.tag !== 0 && Co(),
    (i = e.pendingLanes),
    i & 1 ? (e === Tf ? Li++ : ((Li = 0), (Tf = e))) : (Li = 0),
    nr(),
    null
  );
}
function Co() {
  if ($n !== null) {
    var e = H0(pl),
      t = Tt.transition,
      n = le;
    try {
      if (((Tt.transition = null), (le = 16 > e ? 16 : e), $n === null)) var r = !1;
      else {
        if (((e = $n), ($n = null), (pl = 0), ie & 6)) throw Error(B(331));
        var o = ie;
        for (ie |= 4, G = e.current; G !== null; ) {
          var i = G,
            s = i.child;
          if (G.flags & 16) {
            var a = i.deletions;
            if (a !== null) {
              for (var l = 0; l < a.length; l++) {
                var u = a[l];
                for (G = u; G !== null; ) {
                  var c = G;
                  switch (c.tag) {
                    case 0:
                    case 11:
                    case 15:
                      Di(8, c, i);
                  }
                  var f = c.child;
                  if (f !== null) (f.return = c), (G = f);
                  else
                    for (; G !== null; ) {
                      c = G;
                      var d = c.sibling,
                        m = c.return;
                      if ((ex(c), c === u)) {
                        G = null;
                        break;
                      }
                      if (d !== null) {
                        (d.return = m), (G = d);
                        break;
                      }
                      G = m;
                    }
                }
              }
              var y = i.alternate;
              if (y !== null) {
                var g = y.child;
                if (g !== null) {
                  y.child = null;
                  do {
                    var w = g.sibling;
                    (g.sibling = null), (g = w);
                  } while (g !== null);
                }
              }
              G = i;
            }
          }
          if (i.subtreeFlags & 2064 && s !== null) (s.return = i), (G = s);
          else
            e: for (; G !== null; ) {
              if (((i = G), i.flags & 2048))
                switch (i.tag) {
                  case 0:
                  case 11:
                  case 15:
                    Di(9, i, i.return);
                }
              var h = i.sibling;
              if (h !== null) {
                (h.return = i.return), (G = h);
                break e;
              }
              G = i.return;
            }
        }
        var p = e.current;
        for (G = p; G !== null; ) {
          s = G;
          var x = s.child;
          if (s.subtreeFlags & 2064 && x !== null) (x.return = s), (G = x);
          else
            e: for (s = p; G !== null; ) {
              if (((a = G), a.flags & 2048))
                try {
                  switch (a.tag) {
                    case 0:
                    case 11:
                    case 15:
                      Yl(9, a);
                  }
                } catch (E) {
                  ke(a, a.return, E);
                }
              if (a === s) {
                G = null;
                break e;
              }
              var S = a.sibling;
              if (S !== null) {
                (S.return = a.return), (G = S);
                break e;
              }
              G = a.return;
            }
        }
        if (((ie = o), nr(), Xt && typeof Xt.onPostCommitFiberRoot == "function"))
          try {
            Xt.onPostCommitFiberRoot(zl, e);
          } catch {}
        r = !0;
      }
      return r;
    } finally {
      (le = n), (Tt.transition = t);
    }
  }
  return !1;
}
function Cm(e, t, n) {
  (t = Io(n, t)),
    (t = Hv(e, t, 1)),
    (e = Gn(e, t, 1)),
    (t = et()),
    e !== null && (Cs(e, 1, t), ut(e, t));
}
function ke(e, t, n) {
  if (e.tag === 3) Cm(e, e, n);
  else
    for (; t !== null; ) {
      if (t.tag === 3) {
        Cm(t, e, n);
        break;
      } else if (t.tag === 1) {
        var r = t.stateNode;
        if (
          typeof t.type.getDerivedStateFromError == "function" ||
          (typeof r.componentDidCatch == "function" && (Kn === null || !Kn.has(r)))
        ) {
          (e = Io(n, e)),
            (e = Uv(t, e, 1)),
            (t = Gn(t, e, 1)),
            (e = et()),
            t !== null && (Cs(t, 1, e), ut(t, e));
          break;
        }
      }
      t = t.return;
    }
}
function W2(e, t, n) {
  var r = e.pingCache;
  r !== null && r.delete(t),
    (t = et()),
    (e.pingedLanes |= e.suspendedLanes & n),
    Oe === e &&
      (ze & n) === n &&
      (De === 4 || (De === 3 && (ze & 130023424) === ze && 500 > Ne() - Jd) ? Cr(e, 0) : (qd |= n)),
    ut(e, t);
}
function cx(e, t) {
  t === 0 && (e.mode & 1 ? ((t = Ws), (Ws <<= 1), !(Ws & 130023424) && (Ws = 4194304)) : (t = 1));
  var n = et();
  (e = wn(e, t)), e !== null && (Cs(e, t, n), ut(e, n));
}
function G2(e) {
  var t = e.memoizedState,
    n = 0;
  t !== null && (n = t.retryLane), cx(e, n);
}
function K2(e, t) {
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
  r !== null && r.delete(t), cx(e, n);
}
var fx;
fx = function (e, t, n) {
  if (e !== null)
    if (e.memoizedProps !== t.pendingProps || at.current) it = !0;
    else {
      if (!(e.lanes & n) && !(t.flags & 128)) return (it = !1), I2(e, t, n);
      it = !!(e.flags & 131072);
    }
  else (it = !1), ve && t.flags & 1048576 && mv(t, il, t.index);
  switch (((t.lanes = 0), t.tag)) {
    case 2:
      var r = t.type;
      Ma(e, t), (e = t.pendingProps);
      var o = Mo(t, Qe.current);
      Eo(t, n), (o = Gd(null, t, r, e, o, n));
      var i = Kd();
      return (
        (t.flags |= 1),
        typeof o == "object" && o !== null && typeof o.render == "function" && o.$$typeof === void 0
          ? ((t.tag = 1),
            (t.memoizedState = null),
            (t.updateQueue = null),
            lt(r) ? ((i = !0), rl(t)) : (i = !1),
            (t.memoizedState = o.state !== null && o.state !== void 0 ? o.state : null),
            $d(t),
            (o.updater = Kl),
            (t.stateNode = o),
            (o._reactInternals = t),
            pf(t, r, e, n),
            (t = yf(null, t, r, !0, i, n)))
          : ((t.tag = 0), ve && i && Id(t), Je(null, t, o, n), (t = t.child)),
        t
      );
    case 16:
      r = t.elementType;
      e: {
        switch (
          (Ma(e, t),
          (e = t.pendingProps),
          (o = r._init),
          (r = o(r._payload)),
          (t.type = r),
          (o = t.tag = X2(r)),
          (e = Rt(r, e)),
          o)
        ) {
          case 0:
            t = gf(null, t, r, e, n);
            break e;
          case 1:
            t = hm(null, t, r, e, n);
            break e;
          case 11:
            t = fm(null, t, r, e, n);
            break e;
          case 14:
            t = dm(null, t, r, Rt(r.type, e), n);
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
        gf(e, t, r, o, n)
      );
    case 1:
      return (
        (r = t.type),
        (o = t.pendingProps),
        (o = t.elementType === r ? o : Rt(r, o)),
        hm(e, t, r, o, n)
      );
    case 3:
      e: {
        if ((Yv(t), e === null)) throw Error(B(387));
        (r = t.pendingProps), (i = t.memoizedState), (o = i.element), Sv(e, t), ll(t, r, null, n);
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
            (o = Io(Error(B(423)), t)), (t = pm(e, t, r, n, o));
            break e;
          } else if (r !== o) {
            (o = Io(Error(B(424)), t)), (t = pm(e, t, r, n, o));
            break e;
          } else
            for (
              ft = Wn(t.stateNode.containerInfo.firstChild),
                dt = t,
                ve = !0,
                Lt = null,
                n = xv(t, null, r, n),
                t.child = n;
              n;

            )
              (n.flags = (n.flags & -3) | 4096), (n = n.sibling);
        else {
          if ((Ao(), r === o)) {
            t = Sn(e, t, n);
            break e;
          }
          Je(e, t, r, n);
        }
        t = t.child;
      }
      return t;
    case 5:
      return (
        Ev(t),
        e === null && ff(t),
        (r = t.type),
        (o = t.pendingProps),
        (i = e !== null ? e.memoizedProps : null),
        (s = o.children),
        sf(r, o) ? (s = null) : i !== null && sf(r, i) && (t.flags |= 32),
        Kv(e, t),
        Je(e, t, s, n),
        t.child
      );
    case 6:
      return e === null && ff(t), null;
    case 13:
      return Xv(e, t, n);
    case 4:
      return (
        Bd(t, t.stateNode.containerInfo),
        (r = t.pendingProps),
        e === null ? (t.child = Ro(t, null, r, n)) : Je(e, t, r, n),
        t.child
      );
    case 11:
      return (
        (r = t.type),
        (o = t.pendingProps),
        (o = t.elementType === r ? o : Rt(r, o)),
        fm(e, t, r, o, n)
      );
    case 7:
      return Je(e, t, t.pendingProps, n), t.child;
    case 8:
      return Je(e, t, t.pendingProps.children, n), t.child;
    case 12:
      return Je(e, t, t.pendingProps.children, n), t.child;
    case 10:
      e: {
        if (
          ((r = t.type._context),
          (o = t.pendingProps),
          (i = t.memoizedProps),
          (s = o.value),
          he(sl, r._currentValue),
          (r._currentValue = s),
          i !== null)
        )
          if (zt(i.value, s)) {
            if (i.children === o.children && !at.current) {
              t = Sn(e, t, n);
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
                      (l = pn(-1, n & -n)), (l.tag = 2);
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
                      df(i.return, n, t),
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
                  df(s, n, t),
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
        Je(e, t, o.children, n), (t = t.child);
      }
      return t;
    case 9:
      return (
        (o = t.type),
        (r = t.pendingProps.children),
        Eo(t, n),
        (o = _t(o)),
        (r = r(o)),
        (t.flags |= 1),
        Je(e, t, r, n),
        t.child
      );
    case 14:
      return (r = t.type), (o = Rt(r, t.pendingProps)), (o = Rt(r.type, o)), dm(e, t, r, o, n);
    case 15:
      return Wv(e, t, t.type, t.pendingProps, n);
    case 17:
      return (
        (r = t.type),
        (o = t.pendingProps),
        (o = t.elementType === r ? o : Rt(r, o)),
        Ma(e, t),
        (t.tag = 1),
        lt(r) ? ((e = !0), rl(t)) : (e = !1),
        Eo(t, n),
        Bv(t, r, o),
        pf(t, r, o, n),
        yf(null, t, r, !0, e, n)
      );
    case 19:
      return Zv(e, t, n);
    case 22:
      return Gv(e, t, n);
  }
  throw Error(B(156, t.tag));
};
function dx(e, t) {
  return F0(e, t);
}
function Y2(e, t, n, r) {
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
  return new Y2(e, t, n, r);
}
function rh(e) {
  return (e = e.prototype), !(!e || !e.isReactComponent);
}
function X2(e) {
  if (typeof e == "function") return rh(e) ? 1 : 0;
  if (e != null) {
    if (((e = e.$$typeof), e === Ed)) return 11;
    if (e === Cd) return 14;
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
function Da(e, t, n, r, o, i) {
  var s = 2;
  if (((r = e), typeof e == "function")) rh(e) && (s = 1);
  else if (typeof e == "string") s = 5;
  else
    e: switch (e) {
      case Jr:
        return br(n.children, o, i, t);
      case Sd:
        (s = 8), (o |= 8);
        break;
      case Oc:
        return (e = bt(12, n, t, o | 2)), (e.elementType = Oc), (e.lanes = i), e;
      case jc:
        return (e = bt(13, n, t, o)), (e.elementType = jc), (e.lanes = i), e;
      case Fc:
        return (e = bt(19, n, t, o)), (e.elementType = Fc), (e.lanes = i), e;
      case E0:
        return Zl(n, o, i, t);
      default:
        if (typeof e == "object" && e !== null)
          switch (e.$$typeof) {
            case w0:
              s = 10;
              break e;
            case S0:
              s = 9;
              break e;
            case Ed:
              s = 11;
              break e;
            case Cd:
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
function br(e, t, n, r) {
  return (e = bt(7, e, r, t)), (e.lanes = n), e;
}
function Zl(e, t, n, r) {
  return (
    (e = bt(22, e, r, t)), (e.elementType = E0), (e.lanes = n), (e.stateNode = { isHidden: !1 }), e
  );
}
function Ju(e, t, n) {
  return (e = bt(6, e, null, t)), (e.lanes = n), e;
}
function ec(e, t, n) {
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
function Z2(e, t, n, r, o) {
  (this.tag = t),
    (this.containerInfo = e),
    (this.finishedWork = this.pingCache = this.current = this.pendingChildren = null),
    (this.timeoutHandle = -1),
    (this.callbackNode = this.pendingContext = this.context = null),
    (this.callbackPriority = 0),
    (this.eventTimes = Iu(0)),
    (this.expirationTimes = Iu(-1)),
    (this.entangledLanes =
      this.finishedLanes =
      this.mutableReadLanes =
      this.expiredLanes =
      this.pingedLanes =
      this.suspendedLanes =
      this.pendingLanes =
        0),
    (this.entanglements = Iu(0)),
    (this.identifierPrefix = r),
    (this.onRecoverableError = o),
    (this.mutableSourceEagerHydrationData = null);
}
function oh(e, t, n, r, o, i, s, a, l) {
  return (
    (e = new Z2(e, t, n, a, l)),
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
    $d(i),
    e
  );
}
function Q2(e, t, n) {
  var r = 3 < arguments.length && arguments[3] !== void 0 ? arguments[3] : null;
  return {
    $$typeof: qr,
    key: r == null ? null : "" + r,
    children: e,
    containerInfo: t,
    implementation: n,
  };
}
function hx(e) {
  if (!e) return qn;
  e = e._reactInternals;
  e: {
    if (Or(e) !== e || e.tag !== 1) throw Error(B(170));
    var t = e;
    do {
      switch (t.tag) {
        case 3:
          t = t.stateNode.context;
          break e;
        case 1:
          if (lt(t.type)) {
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
    if (lt(n)) return hv(e, n, t);
  }
  return t;
}
function px(e, t, n, r, o, i, s, a, l) {
  return (
    (e = oh(n, r, !0, e, o, i, s, a, l)),
    (e.context = hx(null)),
    (n = e.current),
    (r = et()),
    (o = Yn(n)),
    (i = pn(r, o)),
    (i.callback = t ?? null),
    Gn(n, i, o),
    (e.current.lanes = o),
    Cs(e, o, r),
    ut(e, r),
    e
  );
}
function Ql(e, t, n, r) {
  var o = t.current,
    i = et(),
    s = Yn(o);
  return (
    (n = hx(n)),
    t.context === null ? (t.context = n) : (t.pendingContext = n),
    (t = pn(i, s)),
    (t.payload = { element: e }),
    (r = r === void 0 ? null : r),
    r !== null && (t.callback = r),
    (e = Gn(o, t, s)),
    e !== null && (jt(e, o, s, i), _a(e, o, s)),
    s
  );
}
function gl(e) {
  if (((e = e.current), !e.child)) return null;
  switch (e.child.tag) {
    case 5:
      return e.child.stateNode;
    default:
      return e.child.stateNode;
  }
}
function bm(e, t) {
  if (((e = e.memoizedState), e !== null && e.dehydrated !== null)) {
    var n = e.retryLane;
    e.retryLane = n !== 0 && n < t ? n : t;
  }
}
function ih(e, t) {
  bm(e, t), (e = e.alternate) && bm(e, t);
}
function q2() {
  return null;
}
var mx =
  typeof reportError == "function"
    ? reportError
    : function (e) {
        console.error(e);
      };
function sh(e) {
  this._internalRoot = e;
}
ql.prototype.render = sh.prototype.render = function (e) {
  var t = this._internalRoot;
  if (t === null) throw Error(B(409));
  Ql(e, t, null, null);
};
ql.prototype.unmount = sh.prototype.unmount = function () {
  var e = this._internalRoot;
  if (e !== null) {
    this._internalRoot = null;
    var t = e.containerInfo;
    Rr(function () {
      Ql(null, e, null, null);
    }),
      (t[xn] = null);
  }
};
function ql(e) {
  this._internalRoot = e;
}
ql.prototype.unstable_scheduleHydration = function (e) {
  if (e) {
    var t = G0();
    e = { blockedOn: null, target: e, priority: t };
    for (var n = 0; n < jn.length && t !== 0 && t < jn[n].priority; n++);
    jn.splice(n, 0, e), n === 0 && Y0(e);
  }
};
function ah(e) {
  return !(!e || (e.nodeType !== 1 && e.nodeType !== 9 && e.nodeType !== 11));
}
function Jl(e) {
  return !(
    !e ||
    (e.nodeType !== 1 &&
      e.nodeType !== 9 &&
      e.nodeType !== 11 &&
      (e.nodeType !== 8 || e.nodeValue !== " react-mount-point-unstable "))
  );
}
function km() {}
function J2(e, t, n, r, o) {
  if (o) {
    if (typeof r == "function") {
      var i = r;
      r = function () {
        var u = gl(s);
        i.call(u);
      };
    }
    var s = px(t, r, e, 0, null, !1, !1, "", km);
    return (
      (e._reactRootContainer = s),
      (e[xn] = s.current),
      Zi(e.nodeType === 8 ? e.parentNode : e),
      Rr(),
      s
    );
  }
  for (; (o = e.lastChild); ) e.removeChild(o);
  if (typeof r == "function") {
    var a = r;
    r = function () {
      var u = gl(l);
      a.call(u);
    };
  }
  var l = oh(e, 0, !1, null, null, !1, !1, "", km);
  return (
    (e._reactRootContainer = l),
    (e[xn] = l.current),
    Zi(e.nodeType === 8 ? e.parentNode : e),
    Rr(function () {
      Ql(t, l, n, r);
    }),
    l
  );
}
function eu(e, t, n, r, o) {
  var i = n._reactRootContainer;
  if (i) {
    var s = i;
    if (typeof o == "function") {
      var a = o;
      o = function () {
        var l = gl(s);
        a.call(l);
      };
    }
    Ql(t, s, e, o);
  } else s = J2(n, t, e, o, r);
  return gl(s);
}
U0 = function (e) {
  switch (e.tag) {
    case 3:
      var t = e.stateNode;
      if (t.current.memoizedState.isDehydrated) {
        var n = xi(t.pendingLanes);
        n !== 0 && (Td(t, n | 1), ut(t, Ne()), !(ie & 6) && ((Lo = Ne() + 500), nr()));
      }
      break;
    case 13:
      Rr(function () {
        var r = wn(e, 1);
        if (r !== null) {
          var o = et();
          jt(r, e, 1, o);
        }
      }),
        ih(e, 1);
  }
};
_d = function (e) {
  if (e.tag === 13) {
    var t = wn(e, 134217728);
    if (t !== null) {
      var n = et();
      jt(t, e, 134217728, n);
    }
    ih(e, 134217728);
  }
};
W0 = function (e) {
  if (e.tag === 13) {
    var t = Yn(e),
      n = wn(e, t);
    if (n !== null) {
      var r = et();
      jt(n, e, t, r);
    }
    ih(e, t);
  }
};
G0 = function () {
  return le;
};
K0 = function (e, t) {
  var n = le;
  try {
    return (le = e), t();
  } finally {
    le = n;
  }
};
Xc = function (e, t, n) {
  switch (t) {
    case "input":
      if ((Bc(e, n), (t = n.name), n.type === "radio" && t != null)) {
        for (n = e; n.parentNode; ) n = n.parentNode;
        for (
          n = n.querySelectorAll("input[name=" + JSON.stringify("" + t) + '][type="radio"]'), t = 0;
          t < n.length;
          t++
        ) {
          var r = n[t];
          if (r !== e && r.form === e.form) {
            var o = Ul(r);
            if (!o) throw Error(B(90));
            b0(r), Bc(r, o);
          }
        }
      }
      break;
    case "textarea":
      T0(e, n);
      break;
    case "select":
      (t = n.value), t != null && vo(e, !!n.multiple, t, !1);
  }
};
D0 = eh;
I0 = Rr;
var ek = { usingClientEntryPoint: !1, Events: [ks, ro, Ul, A0, R0, eh] },
  li = {
    findFiberByHostInstance: yr,
    bundleType: 0,
    version: "18.3.1",
    rendererPackageName: "react-dom",
  },
  tk = {
    bundleType: li.bundleType,
    version: li.version,
    rendererPackageName: li.rendererPackageName,
    rendererConfig: li.rendererConfig,
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
      return (e = O0(e)), e === null ? null : e.stateNode;
    },
    findFiberByHostInstance: li.findFiberByHostInstance || q2,
    findHostInstancesForRefresh: null,
    scheduleRefresh: null,
    scheduleRoot: null,
    setRefreshHandler: null,
    getCurrentFiber: null,
    reconcilerVersion: "18.3.1-next-f1338f8080-20240426",
  };
if (typeof __REACT_DEVTOOLS_GLOBAL_HOOK__ < "u") {
  var na = __REACT_DEVTOOLS_GLOBAL_HOOK__;
  if (!na.isDisabled && na.supportsFiber)
    try {
      (zl = na.inject(tk)), (Xt = na);
    } catch {}
}
yt.__SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED = ek;
yt.createPortal = function (e, t) {
  var n = 2 < arguments.length && arguments[2] !== void 0 ? arguments[2] : null;
  if (!ah(t)) throw Error(B(200));
  return Q2(e, t, null, n);
};
yt.createRoot = function (e, t) {
  if (!ah(e)) throw Error(B(299));
  var n = !1,
    r = "",
    o = mx;
  return (
    t != null &&
      (t.unstable_strictMode === !0 && (n = !0),
      t.identifierPrefix !== void 0 && (r = t.identifierPrefix),
      t.onRecoverableError !== void 0 && (o = t.onRecoverableError)),
    (t = oh(e, 1, !1, null, null, n, !1, r, o)),
    (e[xn] = t.current),
    Zi(e.nodeType === 8 ? e.parentNode : e),
    new sh(t)
  );
};
yt.findDOMNode = function (e) {
  if (e == null) return null;
  if (e.nodeType === 1) return e;
  var t = e._reactInternals;
  if (t === void 0)
    throw typeof e.render == "function"
      ? Error(B(188))
      : ((e = Object.keys(e).join(",")), Error(B(268, e)));
  return (e = O0(t)), (e = e === null ? null : e.stateNode), e;
};
yt.flushSync = function (e) {
  return Rr(e);
};
yt.hydrate = function (e, t, n) {
  if (!Jl(t)) throw Error(B(200));
  return eu(null, e, t, !0, n);
};
yt.hydrateRoot = function (e, t, n) {
  if (!ah(e)) throw Error(B(405));
  var r = (n != null && n.hydratedSources) || null,
    o = !1,
    i = "",
    s = mx;
  if (
    (n != null &&
      (n.unstable_strictMode === !0 && (o = !0),
      n.identifierPrefix !== void 0 && (i = n.identifierPrefix),
      n.onRecoverableError !== void 0 && (s = n.onRecoverableError)),
    (t = px(t, null, e, 1, n ?? null, o, !1, i, s)),
    (e[xn] = t.current),
    Zi(e),
    r)
  )
    for (e = 0; e < r.length; e++)
      (n = r[e]),
        (o = n._getVersion),
        (o = o(n._source)),
        t.mutableSourceEagerHydrationData == null
          ? (t.mutableSourceEagerHydrationData = [n, o])
          : t.mutableSourceEagerHydrationData.push(n, o);
  return new ql(t);
};
yt.render = function (e, t, n) {
  if (!Jl(t)) throw Error(B(200));
  return eu(null, e, t, !1, n);
};
yt.unmountComponentAtNode = function (e) {
  if (!Jl(e)) throw Error(B(40));
  return e._reactRootContainer
    ? (Rr(function () {
        eu(null, null, e, !1, function () {
          (e._reactRootContainer = null), (e[xn] = null);
        });
      }),
      !0)
    : !1;
};
yt.unstable_batchedUpdates = eh;
yt.unstable_renderSubtreeIntoContainer = function (e, t, n, r) {
  if (!Jl(n)) throw Error(B(200));
  if (e == null || e._reactInternals === void 0) throw Error(B(38));
  return eu(e, t, n, !1, r);
};
yt.version = "18.3.1-next-f1338f8080-20240426";
function gx() {
  if (
    !(
      typeof __REACT_DEVTOOLS_GLOBAL_HOOK__ > "u" ||
      typeof __REACT_DEVTOOLS_GLOBAL_HOOK__.checkDCE != "function"
    )
  )
    try {
      __REACT_DEVTOOLS_GLOBAL_HOOK__.checkDCE(gx);
    } catch (e) {
      console.error(e);
    }
}
gx(), (g0.exports = yt);
var tu = g0.exports;
const nk = hd(tu);
var Tm = tu;
(Lc.createRoot = Tm.createRoot), (Lc.hydrateRoot = Tm.hydrateRoot);
const rk = {},
  _m = (e) => {
    let t;
    const n = new Set(),
      r = (c, f) => {
        const d = typeof c == "function" ? c(t) : c;
        if (!Object.is(d, t)) {
          const m = t;
          (t = (f ?? (typeof d != "object" || d === null)) ? d : Object.assign({}, t, d)),
            n.forEach((y) => y(t, m));
        }
      },
      o = () => t,
      l = {
        setState: r,
        getState: o,
        getInitialState: () => u,
        subscribe: (c) => (n.add(c), () => n.delete(c)),
        destroy: () => {
          (rk ? "production" : void 0) !== "production" &&
            console.warn(
              "[DEPRECATED] The `destroy` method will be unsupported in a future version. Instead use unsubscribe function returned by subscribe. Everything will be garbage-collected if store is garbage-collected.",
            ),
            n.clear();
        },
      },
      u = (t = e(r, o, l));
    return l;
  },
  yx = (e) => (e ? _m(e) : _m);
var vx = { exports: {} },
  xx = {},
  wx = { exports: {} },
  Sx = {};
/**
 * @license React
 * use-sync-external-store-shim.production.js
 *
 * Copyright (c) Meta Platforms, Inc. and affiliates.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */ var Vo = v;
function ok(e, t) {
  return (e === t && (e !== 0 || 1 / e === 1 / t)) || (e !== e && t !== t);
}
var ik = typeof Object.is == "function" ? Object.is : ok,
  sk = Vo.useState,
  ak = Vo.useEffect,
  lk = Vo.useLayoutEffect,
  uk = Vo.useDebugValue;
function ck(e, t) {
  var n = t(),
    r = sk({ inst: { value: n, getSnapshot: t } }),
    o = r[0].inst,
    i = r[1];
  return (
    lk(
      function () {
        (o.value = n), (o.getSnapshot = t), tc(o) && i({ inst: o });
      },
      [e, n, t],
    ),
    ak(
      function () {
        return (
          tc(o) && i({ inst: o }),
          e(function () {
            tc(o) && i({ inst: o });
          })
        );
      },
      [e],
    ),
    uk(n),
    n
  );
}
function tc(e) {
  var t = e.getSnapshot;
  e = e.value;
  try {
    var n = t();
    return !ik(e, n);
  } catch {
    return !0;
  }
}
function fk(e, t) {
  return t();
}
var dk =
  typeof window > "u" || typeof window.document > "u" || typeof window.document.createElement > "u"
    ? fk
    : ck;
Sx.useSyncExternalStore = Vo.useSyncExternalStore !== void 0 ? Vo.useSyncExternalStore : dk;
wx.exports = Sx;
var hk = wx.exports;
/**
 * @license React
 * use-sync-external-store-shim/with-selector.production.js
 *
 * Copyright (c) Meta Platforms, Inc. and affiliates.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */ var nu = v,
  pk = hk;
function mk(e, t) {
  return (e === t && (e !== 0 || 1 / e === 1 / t)) || (e !== e && t !== t);
}
var gk = typeof Object.is == "function" ? Object.is : mk,
  yk = pk.useSyncExternalStore,
  vk = nu.useRef,
  xk = nu.useEffect,
  wk = nu.useMemo,
  Sk = nu.useDebugValue;
xx.useSyncExternalStoreWithSelector = function (e, t, n, r, o) {
  var i = vk(null);
  if (i.current === null) {
    var s = { hasValue: !1, value: null };
    i.current = s;
  } else s = i.current;
  i = wk(
    function () {
      function l(m) {
        if (!u) {
          if (((u = !0), (c = m), (m = r(m)), o !== void 0 && s.hasValue)) {
            var y = s.value;
            if (o(y, m)) return (f = y);
          }
          return (f = m);
        }
        if (((y = f), gk(c, m))) return y;
        var g = r(m);
        return o !== void 0 && o(y, g) ? ((c = m), y) : ((c = m), (f = g));
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
  var a = yk(e, i[0], i[1]);
  return (
    xk(
      function () {
        (s.hasValue = !0), (s.value = a);
      },
      [a],
    ),
    Sk(a),
    a
  );
};
vx.exports = xx;
var Ek = vx.exports;
const Ex = hd(Ek),
  Cx = {},
  { useDebugValue: Ck } = L,
  { useSyncExternalStoreWithSelector: bk } = Ex;
let Nm = !1;
const kk = (e) => e;
function Tk(e, t = kk, n) {
  (Cx ? "production" : void 0) !== "production" &&
    n &&
    !Nm &&
    (console.warn(
      "[DEPRECATED] Use `createWithEqualityFn` instead of `create` or use `useStoreWithEqualityFn` instead of `useStore`. They can be imported from 'zustand/traditional'. https://github.com/pmndrs/zustand/discussions/1937",
    ),
    (Nm = !0));
  const r = bk(e.subscribe, e.getState, e.getServerState || e.getInitialState, t, n);
  return Ck(r), r;
}
const Pm = (e) => {
    (Cx ? "production" : void 0) !== "production" &&
      typeof e != "function" &&
      console.warn(
        "[DEPRECATED] Passing a vanilla store will be unsupported in a future version. Instead use `import { useStore } from 'zustand'`.",
      );
    const t = typeof e == "function" ? yx(e) : e,
      n = (r, o) => Tk(t, r, o);
    return Object.assign(n, t), n;
  },
  _k = (e) => (e ? Pm(e) : Pm),
  is = _k((e, t) => ({
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
      e((r) => {
        const o = typeof n.timestamp == "number" ? n.timestamp : Date.now();
        return {
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
              registeredAt: o,
              updatedAt: o,
            },
          },
        };
      }),
    updateMachineTransition: (n) =>
      e((r) => {
        const o = r.machines[n.machine_id];
        if (!o) return r;
        const i = o.currentStateIds.length > 0 ? o.currentStateIds[0] : "",
          s = n.to_state_ids.length > 0 ? n.to_state_ids[0] : "",
          a = typeof n.timestamp == "number" ? n.timestamp : Date.now();
        return {
          machines: {
            ...r.machines,
            [n.machine_id]: {
              ...o,
              currentStateIds: n.to_state_ids,
              context: n.full_context,
              lastTransition: { sourceId: i, targetId: s, event: n.event },
              logs: [...o.logs, { type: "transition", payload: n }],
              updatedAt: a,
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
                  updatedAt: Date.now(),
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
          delete i[n.id],
          {
            machines: {
              ...r.machines,
              [n.machine_id]: { ...o, services: i, updatedAt: Date.now() },
            },
          }
        );
      }),
    addLog: (n, r) =>
      e((o) => {
        const i = o.machines[n];
        return i
          ? {
              machines: {
                ...o.machines,
                [n]: { ...i, logs: [...i.logs, r], updatedAt: Date.now() },
              },
            }
          : o;
      }),
  })),
  Nk = () => {
    const e = is((t) => t.connect);
    v.useEffect(() => {
      e();
    }, [e]);
  };
/**
 * @license lucide-react v0.379.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */ const Pk = (e) => e.replace(/([a-z0-9])([A-Z])/g, "$1-$2").toLowerCase(),
  bx = (...e) => e.filter((t, n, r) => !!t && r.indexOf(t) === n).join(" ");
/**
 * @license lucide-react v0.379.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */ var Mk = {
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
 */ const Ak = v.forwardRef(
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
        ...Mk,
        width: t,
        height: t,
        stroke: e,
        strokeWidth: r ? (Number(n) * 24) / Number(t) : n,
        className: bx("lucide", o),
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
 */ const Me = (e, t) => {
  const n = v.forwardRef(({ className: r, ...o }, i) =>
    v.createElement(Ak, { ref: i, iconNode: t, className: bx(`lucide-${Pk(e)}`, r), ...o }),
  );
  return (n.displayName = `${e}`), n;
};
/**
 * @license lucide-react v0.379.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */ const Rk = Me("Bot", [
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
 */ const Dk = Me("Check", [["path", { d: "M20 6 9 17l-5-5", key: "1gmf2c" }]]);
/**
 * @license lucide-react v0.379.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */ const Ik = Me("Clock", [
  ["circle", { cx: "12", cy: "12", r: "10", key: "1mglay" }],
  ["polyline", { points: "12 6 12 12 16 14", key: "68esgv" }],
]);
/**
 * @license lucide-react v0.379.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */ const Lk = Me("FileJson", [
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
 */ const Vk = Me("History", [
  ["path", { d: "M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8", key: "1357e3" }],
  ["path", { d: "M3 3v5h5", key: "1xhq8a" }],
  ["path", { d: "M12 7v5l4 2", key: "1fdv2h" }],
]);
/**
 * @license lucide-react v0.379.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */ const Ok = Me("ListFilter", [
  ["path", { d: "M3 6h18", key: "d0wm0j" }],
  ["path", { d: "M7 12h10", key: "b7w52i" }],
  ["path", { d: "M10 18h4", key: "1ulq68" }],
]);
/**
 * @license lucide-react v0.379.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */ const jk = Me("Moon", [["path", { d: "M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z", key: "a7tn18" }]]);
/**
 * @license lucide-react v0.379.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */ const Fk = Me("MoveDiagonal2", [
  ["polyline", { points: "5 11 5 5 11 5", key: "ncfzxk" }],
  ["polyline", { points: "19 13 19 19 13 19", key: "1mk7hk" }],
  ["line", { x1: "5", x2: "19", y1: "5", y2: "19", key: "mcyte3" }],
]);
/**
 * @license lucide-react v0.379.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */ const zk = Me("Pause", [
  ["rect", { x: "14", y: "4", width: "4", height: "16", rx: "1", key: "zuxfzm" }],
  ["rect", { x: "6", y: "4", width: "4", height: "16", rx: "1", key: "1okwgv" }],
]);
/**
 * @license lucide-react v0.379.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */ const $k = Me("Play", [["polygon", { points: "6 3 20 12 6 21 6 3", key: "1oa8hb" }]]);
/**
 * @license lucide-react v0.379.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */ const Bk = Me("RadioTower", [
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
 */ const Mm = Me("Search", [
  ["circle", { cx: "11", cy: "11", r: "8", key: "4ej97u" }],
  ["path", { d: "m21 21-4.3-4.3", key: "1qie3q" }],
]);
/**
 * @license lucide-react v0.379.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */ const Hk = Me("Send", [
  ["path", { d: "m22 2-7 20-4-9-9-4Z", key: "1q3vgg" }],
  ["path", { d: "M22 2 11 13", key: "nzbqef" }],
]);
/**
 * @license lucide-react v0.379.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */ const Uk = Me("Settings", [
  [
    "path",
    {
      d: "M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z",
      key: "1qme2f",
    },
  ],
  ["circle", { cx: "12", cy: "12", r: "3", key: "1v7zrd" }],
]);
/**
 * @license lucide-react v0.379.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */ const Wk = Me("SquareActivity", [
  ["rect", { width: "18", height: "18", x: "3", y: "3", rx: "2", key: "afitv7" }],
  ["path", { d: "M17 12h-2l-2 5-2-10-2 5H7", key: "15hlnc" }],
]);
/**
 * @license lucide-react v0.379.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */ const Gk = Me("Sun", [
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
 */ const Kk = Me("WifiOff", [
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
 */ const Yk = Me("Wifi", [
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
 */ const lh = Me("X", [
  ["path", { d: "M18 6 6 18", key: "1bl5f8" }],
  ["path", { d: "m6 6 12 12", key: "d8bk6v" }],
]);
/**
 * @license lucide-react v0.379.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */ const Xk = Me("Zap", [
  [
    "path",
    {
      d: "M4 14a1 1 0 0 1-.78-1.63l9.9-10.2a.5.5 0 0 1 .86.46l-1.92 6.02A1 1 0 0 0 13 10h7a1 1 0 0 1 .78 1.63l-9.9 10.2a.5.5 0 0 1-.86-.46l1.92-6.02A1 1 0 0 0 11 14z",
      key: "1xq2db",
    },
  ],
]);
function Am(e, t) {
  if (typeof e == "function") return e(t);
  e != null && (e.current = t);
}
function kx(...e) {
  return (t) => {
    let n = !1;
    const r = e.map((o) => {
      const i = Am(o, t);
      return !n && typeof i == "function" && (n = !0), i;
    });
    if (n)
      return () => {
        for (let o = 0; o < r.length; o++) {
          const i = r[o];
          typeof i == "function" ? i() : Am(e[o], null);
        }
      };
  };
}
function en(...e) {
  return v.useCallback(kx(...e), e);
}
function ss(e) {
  const t = Qk(e),
    n = v.forwardRef((r, o) => {
      const { children: i, ...s } = r,
        a = v.Children.toArray(i),
        l = a.find(Jk);
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
        return C.jsx(t, {
          ...s,
          ref: o,
          children: v.isValidElement(u) ? v.cloneElement(u, void 0, c) : null,
        });
      }
      return C.jsx(t, { ...s, ref: o, children: i });
    });
  return (n.displayName = `${e}.Slot`), n;
}
var Zk = ss("Slot");
function Qk(e) {
  const t = v.forwardRef((n, r) => {
    const { children: o, ...i } = n;
    if (v.isValidElement(o)) {
      const s = tT(o),
        a = eT(i, o.props);
      return o.type !== v.Fragment && (a.ref = r ? kx(r, s) : s), v.cloneElement(o, a);
    }
    return v.Children.count(o) > 1 ? v.Children.only(null) : null;
  });
  return (t.displayName = `${e}.SlotClone`), t;
}
var qk = Symbol("radix.slottable");
function Jk(e) {
  return (
    v.isValidElement(e) &&
    typeof e.type == "function" &&
    "__radixId" in e.type &&
    e.type.__radixId === qk
  );
}
function eT(e, t) {
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
function tT(e) {
  var r, o;
  let t = (r = Object.getOwnPropertyDescriptor(e.props, "ref")) == null ? void 0 : r.get,
    n = t && "isReactWarning" in t && t.isReactWarning;
  return n
    ? e.ref
    : ((t = (o = Object.getOwnPropertyDescriptor(e, "ref")) == null ? void 0 : o.get),
      (n = t && "isReactWarning" in t && t.isReactWarning),
      n ? e.props.ref : e.props.ref || e.ref);
}
function Tx(e) {
  var t,
    n,
    r = "";
  if (typeof e == "string" || typeof e == "number") r += e;
  else if (typeof e == "object")
    if (Array.isArray(e)) {
      var o = e.length;
      for (t = 0; t < o; t++) e[t] && (n = Tx(e[t])) && (r && (r += " "), (r += n));
    } else for (n in e) e[n] && (r && (r += " "), (r += n));
  return r;
}
function _x() {
  for (var e, t, n = 0, r = "", o = arguments.length; n < o; n++)
    (e = arguments[n]) && (t = Tx(e)) && (r && (r += " "), (r += t));
  return r;
}
const Rm = (e) => (typeof e == "boolean" ? `${e}` : e === 0 ? "0" : e),
  Dm = _x,
  Nx = (e, t) => (n) => {
    var r;
    if ((t == null ? void 0 : t.variants) == null)
      return Dm(e, n == null ? void 0 : n.class, n == null ? void 0 : n.className);
    const { variants: o, defaultVariants: i } = t,
      s = Object.keys(o).map((u) => {
        const c = n == null ? void 0 : n[u],
          f = i == null ? void 0 : i[u];
        if (c === null) return null;
        const d = Rm(c) || Rm(f);
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
              let { class: f, className: d, ...m } = c;
              return Object.entries(m).every((y) => {
                let [g, w] = y;
                return Array.isArray(w) ? w.includes({ ...i, ...a }[g]) : { ...i, ...a }[g] === w;
              })
                ? [...u, f, d]
                : u;
            }, []);
    return Dm(e, s, l, n == null ? void 0 : n.class, n == null ? void 0 : n.className);
  },
  uh = "-",
  nT = (e) => {
    const t = oT(e),
      { conflictingClassGroups: n, conflictingClassGroupModifiers: r } = e;
    return {
      getClassGroupId: (s) => {
        const a = s.split(uh);
        return a[0] === "" && a.length !== 1 && a.shift(), Px(a, t) || rT(s);
      },
      getConflictingClassGroupIds: (s, a) => {
        const l = n[s] || [];
        return a && r[s] ? [...l, ...r[s]] : l;
      },
    };
  },
  Px = (e, t) => {
    var s;
    if (e.length === 0) return t.classGroupId;
    const n = e[0],
      r = t.nextPart.get(n),
      o = r ? Px(e.slice(1), r) : void 0;
    if (o) return o;
    if (t.validators.length === 0) return;
    const i = e.join(uh);
    return (s = t.validators.find(({ validator: a }) => a(i))) == null ? void 0 : s.classGroupId;
  },
  Im = /^\[(.+)\]$/,
  rT = (e) => {
    if (Im.test(e)) {
      const t = Im.exec(e)[1],
        n = t == null ? void 0 : t.substring(0, t.indexOf(":"));
      if (n) return "arbitrary.." + n;
    }
  },
  oT = (e) => {
    const { theme: t, prefix: n } = e,
      r = { nextPart: new Map(), validators: [] };
    return (
      sT(Object.entries(e.classGroups), n).forEach(([i, s]) => {
        Pf(s, r, i, t);
      }),
      r
    );
  },
  Pf = (e, t, n, r) => {
    e.forEach((o) => {
      if (typeof o == "string") {
        const i = o === "" ? t : Lm(t, o);
        i.classGroupId = n;
        return;
      }
      if (typeof o == "function") {
        if (iT(o)) {
          Pf(o(r), t, n, r);
          return;
        }
        t.validators.push({ validator: o, classGroupId: n });
        return;
      }
      Object.entries(o).forEach(([i, s]) => {
        Pf(s, Lm(t, i), n, r);
      });
    });
  },
  Lm = (e, t) => {
    let n = e;
    return (
      t.split(uh).forEach((r) => {
        n.nextPart.has(r) || n.nextPart.set(r, { nextPart: new Map(), validators: [] }),
          (n = n.nextPart.get(r));
      }),
      n
    );
  },
  iT = (e) => e.isThemeGetter,
  sT = (e, t) =>
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
  aT = (e) => {
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
  Mx = "!",
  lT = (e) => {
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
          m = d.startsWith(Mx),
          y = m ? d.substring(1) : d,
          g = f && f > c ? f - c : void 0;
        return {
          modifiers: l,
          hasImportantModifier: m,
          baseClassName: y,
          maybePostfixModifierPosition: g,
        };
      };
    return n ? (a) => n({ className: a, parseClassName: s }) : s;
  },
  uT = (e) => {
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
  cT = (e) => ({ cache: aT(e.cacheSize), parseClassName: lT(e), ...nT(e) }),
  fT = /\s+/,
  dT = (e, t) => {
    const { parseClassName: n, getClassGroupId: r, getConflictingClassGroupIds: o } = t,
      i = [],
      s = e.trim().split(fT);
    let a = "";
    for (let l = s.length - 1; l >= 0; l -= 1) {
      const u = s[l],
        {
          modifiers: c,
          hasImportantModifier: f,
          baseClassName: d,
          maybePostfixModifierPosition: m,
        } = n(u);
      let y = !!m,
        g = r(y ? d.substring(0, m) : d);
      if (!g) {
        if (!y) {
          a = u + (a.length > 0 ? " " + a : a);
          continue;
        }
        if (((g = r(d)), !g)) {
          a = u + (a.length > 0 ? " " + a : a);
          continue;
        }
        y = !1;
      }
      const w = uT(c).join(":"),
        h = f ? w + Mx : w,
        p = h + g;
      if (i.includes(p)) continue;
      i.push(p);
      const x = o(g, y);
      for (let S = 0; S < x.length; ++S) {
        const E = x[S];
        i.push(h + E);
      }
      a = u + (a.length > 0 ? " " + a : a);
    }
    return a;
  };
function hT() {
  let e = 0,
    t,
    n,
    r = "";
  for (; e < arguments.length; ) (t = arguments[e++]) && (n = Ax(t)) && (r && (r += " "), (r += n));
  return r;
}
const Ax = (e) => {
  if (typeof e == "string") return e;
  let t,
    n = "";
  for (let r = 0; r < e.length; r++) e[r] && (t = Ax(e[r])) && (n && (n += " "), (n += t));
  return n;
};
function pT(e, ...t) {
  let n,
    r,
    o,
    i = s;
  function s(l) {
    const u = t.reduce((c, f) => f(c), e());
    return (n = cT(u)), (r = n.cache.get), (o = n.cache.set), (i = a), a(l);
  }
  function a(l) {
    const u = r(l);
    if (u) return u;
    const c = dT(l, n);
    return o(l, c), c;
  }
  return function () {
    return i(hT.apply(null, arguments));
  };
}
const me = (e) => {
    const t = (n) => n[e] || [];
    return (t.isThemeGetter = !0), t;
  },
  Rx = /^\[(?:([a-z-]+):)?(.+)\]$/i,
  mT = /^\d+\/\d+$/,
  gT = new Set(["px", "full", "screen"]),
  yT = /^(\d+(\.\d+)?)?(xs|sm|md|lg|xl)$/,
  vT =
    /\d+(%|px|r?em|[sdl]?v([hwib]|min|max)|pt|pc|in|cm|mm|cap|ch|ex|r?lh|cq(w|h|i|b|min|max))|\b(calc|min|max|clamp)\(.+\)|^0$/,
  xT = /^(rgba?|hsla?|hwb|(ok)?(lab|lch))\(.+\)$/,
  wT = /^(inset_)?-?((\d+)?\.?(\d+)[a-z]+|0)_-?((\d+)?\.?(\d+)[a-z]+|0)/,
  ST =
    /^(url|image|image-set|cross-fade|element|(repeating-)?(linear|radial|conic)-gradient)\(.+\)$/,
  sn = (e) => bo(e) || gT.has(e) || mT.test(e),
  Nn = (e) => Yo(e, "length", PT),
  bo = (e) => !!e && !Number.isNaN(Number(e)),
  nc = (e) => Yo(e, "number", bo),
  ui = (e) => !!e && Number.isInteger(Number(e)),
  ET = (e) => e.endsWith("%") && bo(e.slice(0, -1)),
  ee = (e) => Rx.test(e),
  Pn = (e) => yT.test(e),
  CT = new Set(["length", "size", "percentage"]),
  bT = (e) => Yo(e, CT, Dx),
  kT = (e) => Yo(e, "position", Dx),
  TT = new Set(["image", "url"]),
  _T = (e) => Yo(e, TT, AT),
  NT = (e) => Yo(e, "", MT),
  ci = () => !0,
  Yo = (e, t, n) => {
    const r = Rx.exec(e);
    return r ? (r[1] ? (typeof t == "string" ? r[1] === t : t.has(r[1])) : n(r[2])) : !1;
  },
  PT = (e) => vT.test(e) && !xT.test(e),
  Dx = () => !1,
  MT = (e) => wT.test(e),
  AT = (e) => ST.test(e),
  RT = () => {
    const e = me("colors"),
      t = me("spacing"),
      n = me("blur"),
      r = me("brightness"),
      o = me("borderColor"),
      i = me("borderRadius"),
      s = me("borderSpacing"),
      a = me("borderWidth"),
      l = me("contrast"),
      u = me("grayscale"),
      c = me("hueRotate"),
      f = me("invert"),
      d = me("gap"),
      m = me("gradientColorStops"),
      y = me("gradientColorStopPositions"),
      g = me("inset"),
      w = me("margin"),
      h = me("opacity"),
      p = me("padding"),
      x = me("saturate"),
      S = me("scale"),
      E = me("sepia"),
      _ = me("skew"),
      k = me("space"),
      N = me("translate"),
      A = () => ["auto", "contain", "none"],
      R = () => ["auto", "hidden", "clip", "visible", "scroll"],
      O = () => ["auto", ee, t],
      j = () => [ee, t],
      $ = () => ["", sn, Nn],
      b = () => ["auto", bo, ee],
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
      P = () => ["solid", "dashed", "dotted", "double", "none"],
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
      M = () => ["start", "end", "center", "between", "around", "evenly", "stretch"],
      T = () => ["", "0", ee],
      D = () => ["auto", "avoid", "all", "avoid-page", "page", "left", "right", "column"],
      F = () => [bo, ee];
    return {
      cacheSize: 500,
      separator: ":",
      theme: {
        colors: [ci],
        spacing: [sn, Nn],
        blur: ["none", "", Pn, ee],
        brightness: F(),
        borderColor: [e],
        borderRadius: ["none", "", "full", Pn, ee],
        borderSpacing: j(),
        borderWidth: $(),
        contrast: F(),
        grayscale: T(),
        hueRotate: F(),
        invert: T(),
        gap: j(),
        gradientColorStops: [e],
        gradientColorStopPositions: [ET, Nn],
        inset: O(),
        margin: O(),
        opacity: F(),
        padding: j(),
        saturate: F(),
        scale: F(),
        sepia: T(),
        skew: F(),
        space: j(),
        translate: j(),
      },
      classGroups: {
        aspect: [{ aspect: ["auto", "square", "video", ee] }],
        container: ["container"],
        columns: [{ columns: [Pn] }],
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
        "object-position": [{ object: [...I(), ee] }],
        overflow: [{ overflow: R() }],
        "overflow-x": [{ "overflow-x": R() }],
        "overflow-y": [{ "overflow-y": R() }],
        overscroll: [{ overscroll: A() }],
        "overscroll-x": [{ "overscroll-x": A() }],
        "overscroll-y": [{ "overscroll-y": A() }],
        position: ["static", "fixed", "absolute", "relative", "sticky"],
        inset: [{ inset: [g] }],
        "inset-x": [{ "inset-x": [g] }],
        "inset-y": [{ "inset-y": [g] }],
        start: [{ start: [g] }],
        end: [{ end: [g] }],
        top: [{ top: [g] }],
        right: [{ right: [g] }],
        bottom: [{ bottom: [g] }],
        left: [{ left: [g] }],
        visibility: ["visible", "invisible", "collapse"],
        z: [{ z: ["auto", ui, ee] }],
        basis: [{ basis: O() }],
        "flex-direction": [{ flex: ["row", "row-reverse", "col", "col-reverse"] }],
        "flex-wrap": [{ flex: ["wrap", "wrap-reverse", "nowrap"] }],
        flex: [{ flex: ["1", "auto", "initial", "none", ee] }],
        grow: [{ grow: T() }],
        shrink: [{ shrink: T() }],
        order: [{ order: ["first", "last", "none", ui, ee] }],
        "grid-cols": [{ "grid-cols": [ci] }],
        "col-start-end": [{ col: ["auto", { span: ["full", ui, ee] }, ee] }],
        "col-start": [{ "col-start": b() }],
        "col-end": [{ "col-end": b() }],
        "grid-rows": [{ "grid-rows": [ci] }],
        "row-start-end": [{ row: ["auto", { span: [ui, ee] }, ee] }],
        "row-start": [{ "row-start": b() }],
        "row-end": [{ "row-end": b() }],
        "grid-flow": [{ "grid-flow": ["row", "col", "dense", "row-dense", "col-dense"] }],
        "auto-cols": [{ "auto-cols": ["auto", "min", "max", "fr", ee] }],
        "auto-rows": [{ "auto-rows": ["auto", "min", "max", "fr", ee] }],
        gap: [{ gap: [d] }],
        "gap-x": [{ "gap-x": [d] }],
        "gap-y": [{ "gap-y": [d] }],
        "justify-content": [{ justify: ["normal", ...M()] }],
        "justify-items": [{ "justify-items": ["start", "end", "center", "stretch"] }],
        "justify-self": [{ "justify-self": ["auto", "start", "end", "center", "stretch"] }],
        "align-content": [{ content: ["normal", ...M(), "baseline"] }],
        "align-items": [{ items: ["start", "end", "center", "baseline", "stretch"] }],
        "align-self": [{ self: ["auto", "start", "end", "center", "stretch", "baseline"] }],
        "place-content": [{ "place-content": [...M(), "baseline"] }],
        "place-items": [{ "place-items": ["start", "end", "center", "baseline", "stretch"] }],
        "place-self": [{ "place-self": ["auto", "start", "end", "center", "stretch"] }],
        p: [{ p: [p] }],
        px: [{ px: [p] }],
        py: [{ py: [p] }],
        ps: [{ ps: [p] }],
        pe: [{ pe: [p] }],
        pt: [{ pt: [p] }],
        pr: [{ pr: [p] }],
        pb: [{ pb: [p] }],
        pl: [{ pl: [p] }],
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
          { "max-w": [ee, t, "none", "full", "min", "max", "fit", "prose", { screen: [Pn] }, Pn] },
        ],
        h: [{ h: [ee, t, "auto", "min", "max", "fit", "svh", "lvh", "dvh"] }],
        "min-h": [{ "min-h": [ee, t, "min", "max", "fit", "svh", "lvh", "dvh"] }],
        "max-h": [{ "max-h": [ee, t, "min", "max", "fit", "svh", "lvh", "dvh"] }],
        size: [{ size: [ee, t, "auto", "min", "max", "fit"] }],
        "font-size": [{ text: ["base", Pn, Nn] }],
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
              nc,
            ],
          },
        ],
        "font-family": [{ font: [ci] }],
        "fvn-normal": ["normal-nums"],
        "fvn-ordinal": ["ordinal"],
        "fvn-slashed-zero": ["slashed-zero"],
        "fvn-figure": ["lining-nums", "oldstyle-nums"],
        "fvn-spacing": ["proportional-nums", "tabular-nums"],
        "fvn-fraction": ["diagonal-fractions", "stacked-fractions"],
        tracking: [{ tracking: ["tighter", "tight", "normal", "wide", "wider", "widest", ee] }],
        "line-clamp": [{ "line-clamp": ["none", bo, nc] }],
        leading: [{ leading: ["none", "tight", "snug", "normal", "relaxed", "loose", sn, ee] }],
        "list-image": [{ "list-image": ["none", ee] }],
        "list-style-type": [{ list: ["none", "disc", "decimal", ee] }],
        "list-style-position": [{ list: ["inside", "outside"] }],
        "placeholder-color": [{ placeholder: [e] }],
        "placeholder-opacity": [{ "placeholder-opacity": [h] }],
        "text-alignment": [{ text: ["left", "center", "right", "justify", "start", "end"] }],
        "text-color": [{ text: [e] }],
        "text-opacity": [{ "text-opacity": [h] }],
        "text-decoration": ["underline", "overline", "line-through", "no-underline"],
        "text-decoration-style": [{ decoration: [...P(), "wavy"] }],
        "text-decoration-thickness": [{ decoration: ["auto", "from-font", sn, Nn] }],
        "underline-offset": [{ "underline-offset": ["auto", sn, ee] }],
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
        "bg-opacity": [{ "bg-opacity": [h] }],
        "bg-origin": [{ "bg-origin": ["border", "padding", "content"] }],
        "bg-position": [{ bg: [...I(), kT] }],
        "bg-repeat": [{ bg: ["no-repeat", { repeat: ["", "x", "y", "round", "space"] }] }],
        "bg-size": [{ bg: ["auto", "cover", "contain", bT] }],
        "bg-image": [
          { bg: ["none", { "gradient-to": ["t", "tr", "r", "br", "b", "bl", "l", "tl"] }, _T] },
        ],
        "bg-color": [{ bg: [e] }],
        "gradient-from-pos": [{ from: [y] }],
        "gradient-via-pos": [{ via: [y] }],
        "gradient-to-pos": [{ to: [y] }],
        "gradient-from": [{ from: [m] }],
        "gradient-via": [{ via: [m] }],
        "gradient-to": [{ to: [m] }],
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
        "border-style": [{ border: [...P(), "hidden"] }],
        "divide-x": [{ "divide-x": [a] }],
        "divide-x-reverse": ["divide-x-reverse"],
        "divide-y": [{ "divide-y": [a] }],
        "divide-y-reverse": ["divide-y-reverse"],
        "divide-opacity": [{ "divide-opacity": [h] }],
        "divide-style": [{ divide: P() }],
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
        "outline-style": [{ outline: ["", ...P()] }],
        "outline-offset": [{ "outline-offset": [sn, ee] }],
        "outline-w": [{ outline: [sn, Nn] }],
        "outline-color": [{ outline: [e] }],
        "ring-w": [{ ring: $() }],
        "ring-w-inset": ["ring-inset"],
        "ring-color": [{ ring: [e] }],
        "ring-opacity": [{ "ring-opacity": [h] }],
        "ring-offset-w": [{ "ring-offset": [sn, Nn] }],
        "ring-offset-color": [{ "ring-offset": [e] }],
        shadow: [{ shadow: ["", "inner", "none", Pn, NT] }],
        "shadow-color": [{ shadow: [ci] }],
        opacity: [{ opacity: [h] }],
        "mix-blend": [{ "mix-blend": [...V(), "plus-lighter", "plus-darker"] }],
        "bg-blend": [{ "bg-blend": V() }],
        filter: [{ filter: ["", "none"] }],
        blur: [{ blur: [n] }],
        brightness: [{ brightness: [r] }],
        contrast: [{ contrast: [l] }],
        "drop-shadow": [{ "drop-shadow": ["", "none", Pn, ee] }],
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
          { transition: ["none", "all", "", "colors", "opacity", "shadow", "transform", ee] },
        ],
        duration: [{ duration: F() }],
        ease: [{ ease: ["linear", "in", "out", "in-out", ee] }],
        delay: [{ delay: F() }],
        animate: [{ animate: ["none", "spin", "ping", "pulse", "bounce", ee] }],
        transform: [{ transform: ["", "gpu", "none"] }],
        scale: [{ scale: [S] }],
        "scale-x": [{ "scale-x": [S] }],
        "scale-y": [{ "scale-y": [S] }],
        rotate: [{ rotate: [ui, ee] }],
        "translate-x": [{ "translate-x": [N] }],
        "translate-y": [{ "translate-y": [N] }],
        "skew-x": [{ "skew-x": [_] }],
        "skew-y": [{ "skew-y": [_] }],
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
        "will-change": [{ "will-change": ["auto", "scroll", "contents", "transform", ee] }],
        fill: [{ fill: [e, "none"] }],
        "stroke-w": [{ stroke: [sn, Nn, nc] }],
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
  DT = pT(RT);
function se(...e) {
  return DT(_x(e));
}
const IT = Nx(
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
  yl = v.forwardRef(({ className: e, variant: t, size: n, asChild: r = !1, ...o }, i) => {
    const s = r ? Zk : "button";
    return C.jsx(s, { className: se(IT({ variant: t, size: n, className: e })), ref: i, ...o });
  });
yl.displayName = "Button";
const _s = v.forwardRef(({ className: e, ...t }, n) =>
  C.jsx("div", {
    ref: n,
    className: se("rounded-lg border bg-card text-card-foreground shadow-sm", e),
    ...t,
  }),
);
_s.displayName = "Card";
const Ns = v.forwardRef(({ className: e, ...t }, n) =>
  C.jsx("div", { ref: n, className: se("flex flex-col space-y-1.5 p-6", e), ...t }),
);
Ns.displayName = "CardHeader";
const Ps = v.forwardRef(({ className: e, ...t }, n) =>
  C.jsx("div", {
    ref: n,
    className: se("text-2xl font-semibold leading-none tracking-tight", e),
    ...t,
  }),
);
Ps.displayName = "CardTitle";
const LT = v.forwardRef(({ className: e, ...t }, n) =>
  C.jsx("div", { ref: n, className: se("text-sm text-muted-foreground", e), ...t }),
);
LT.displayName = "CardDescription";
const Ms = v.forwardRef(({ className: e, ...t }, n) =>
  C.jsx("div", { ref: n, className: se("p-6 pt-0", e), ...t }),
);
Ms.displayName = "CardContent";
const VT = v.forwardRef(({ className: e, ...t }, n) =>
  C.jsx("div", { ref: n, className: se("flex items-center p-6 pt-0", e), ...t }),
);
VT.displayName = "CardFooter";
function $e(e, t, { checkForDefaultPrevented: n = !0 } = {}) {
  return function (o) {
    if ((e == null || e(o), n === !1 || !o.defaultPrevented)) return t == null ? void 0 : t(o);
  };
}
function OT(e, t) {
  const n = v.createContext(t),
    r = (i) => {
      const { children: s, ...a } = i,
        l = v.useMemo(() => a, Object.values(a));
      return C.jsx(n.Provider, { value: l, children: s });
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
      const { scope: d, children: m, ...y } = f,
        g = ((h = d == null ? void 0 : d[e]) == null ? void 0 : h[l]) || a,
        w = v.useMemo(() => y, Object.values(y));
      return C.jsx(g.Provider, { value: w, children: m });
    };
    u.displayName = i + "Provider";
    function c(f, d) {
      var g;
      const m = ((g = d == null ? void 0 : d[e]) == null ? void 0 : g[l]) || a,
        y = v.useContext(m);
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
  return (o.scopeName = e), [r, jT(o, ...t)];
}
function jT(...e) {
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
function FT(e) {
  const t = e + "CollectionProvider",
    [n, r] = ru(t),
    [o, i] = n(t, { collectionRef: { current: null }, itemMap: new Map() }),
    s = (g) => {
      const { scope: w, children: h } = g,
        p = L.useRef(null),
        x = L.useRef(new Map()).current;
      return C.jsx(o, { scope: w, itemMap: x, collectionRef: p, children: h });
    };
  s.displayName = t;
  const a = e + "CollectionSlot",
    l = ss(a),
    u = L.forwardRef((g, w) => {
      const { scope: h, children: p } = g,
        x = i(a, h),
        S = en(w, x.collectionRef);
      return C.jsx(l, { ref: S, children: p });
    });
  u.displayName = a;
  const c = e + "CollectionItemSlot",
    f = "data-radix-collection-item",
    d = ss(c),
    m = L.forwardRef((g, w) => {
      const { scope: h, children: p, ...x } = g,
        S = L.useRef(null),
        E = en(w, S),
        _ = i(c, h);
      return (
        L.useEffect(() => (_.itemMap.set(S, { ref: S, ...x }), () => void _.itemMap.delete(S))),
        C.jsx(d, { [f]: "", ref: E, children: p })
      );
    });
  m.displayName = c;
  function y(g) {
    const w = i(e + "CollectionConsumer", g);
    return L.useCallback(() => {
      const p = w.collectionRef.current;
      if (!p) return [];
      const x = Array.from(p.querySelectorAll(`[${f}]`));
      return Array.from(w.itemMap.values()).sort(
        (_, k) => x.indexOf(_.ref.current) - x.indexOf(k.ref.current),
      );
    }, [w.collectionRef, w.itemMap]);
  }
  return [{ Provider: s, Slot: u, ItemSlot: m }, y, r];
}
var as = globalThis != null && globalThis.document ? v.useLayoutEffect : () => {},
  zT = p0[" useId ".trim().toString()] || (() => {}),
  $T = 0;
function Vi(e) {
  const [t, n] = v.useState(zT());
  return (
    as(() => {
      n((r) => r ?? String($T++));
    }, [e]),
    t ? `radix-${t}` : ""
  );
}
var BT = [
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
  rt = BT.reduce((e, t) => {
    const n = ss(`Primitive.${t}`),
      r = v.forwardRef((o, i) => {
        const { asChild: s, ...a } = o,
          l = s ? n : t;
        return (
          typeof window < "u" && (window[Symbol.for("radix-ui")] = !0), C.jsx(l, { ...a, ref: i })
        );
      });
    return (r.displayName = `Primitive.${t}`), { ...e, [t]: r };
  }, {});
function HT(e, t) {
  e && tu.flushSync(() => e.dispatchEvent(t));
}
function Oo(e) {
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
var UT = p0[" useInsertionEffect ".trim().toString()] || as;
function ch({ prop: e, defaultProp: t, onChange: n = () => {}, caller: r }) {
  const [o, i, s] = WT({ defaultProp: t, onChange: n }),
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
        const d = GT(c) ? c(e) : c;
        d !== e && ((f = s.current) == null || f.call(s, d));
      } else i(c);
    },
    [a, e, i, s],
  );
  return [l, u];
}
function WT({ defaultProp: e, onChange: t }) {
  const [n, r] = v.useState(e),
    o = v.useRef(n),
    i = v.useRef(t);
  return (
    UT(() => {
      i.current = t;
    }, [t]),
    v.useEffect(() => {
      var s;
      o.current !== n && ((s = i.current) == null || s.call(i, n), (o.current = n));
    }, [n, o]),
    [n, r, i]
  );
}
function GT(e) {
  return typeof e == "function";
}
var KT = v.createContext(void 0);
function Ix(e) {
  const t = v.useContext(KT);
  return e || t || "ltr";
}
var rc = "rovingFocusGroup.onEntryFocus",
  YT = { bubbles: !1, cancelable: !0 },
  As = "RovingFocusGroup",
  [Mf, Lx, XT] = FT(As),
  [ZT, Vx] = ru(As, [XT]),
  [QT, qT] = ZT(As),
  Ox = v.forwardRef((e, t) =>
    C.jsx(Mf.Provider, {
      scope: e.__scopeRovingFocusGroup,
      children: C.jsx(Mf.Slot, {
        scope: e.__scopeRovingFocusGroup,
        children: C.jsx(JT, { ...e, ref: t }),
      }),
    }),
  );
Ox.displayName = As;
var JT = v.forwardRef((e, t) => {
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
      m = en(t, d),
      y = Ix(i),
      [g, w] = ch({ prop: s, defaultProp: a ?? null, onChange: l, caller: As }),
      [h, p] = v.useState(!1),
      x = Oo(u),
      S = Lx(n),
      E = v.useRef(!1),
      [_, k] = v.useState(0);
    return (
      v.useEffect(() => {
        const N = d.current;
        if (N) return N.addEventListener(rc, x), () => N.removeEventListener(rc, x);
      }, [x]),
      C.jsx(QT, {
        scope: n,
        orientation: r,
        dir: y,
        loop: o,
        currentTabStopId: g,
        onItemFocus: v.useCallback((N) => w(N), [w]),
        onItemShiftTab: v.useCallback(() => p(!0), []),
        onFocusableItemAdd: v.useCallback(() => k((N) => N + 1), []),
        onFocusableItemRemove: v.useCallback(() => k((N) => N - 1), []),
        children: C.jsx(rt.div, {
          tabIndex: h || _ === 0 ? -1 : 0,
          "data-orientation": r,
          ...f,
          ref: m,
          style: { outline: "none", ...e.style },
          onMouseDown: $e(e.onMouseDown, () => {
            E.current = !0;
          }),
          onFocus: $e(e.onFocus, (N) => {
            const A = !E.current;
            if (N.target === N.currentTarget && A && !h) {
              const R = new CustomEvent(rc, YT);
              if ((N.currentTarget.dispatchEvent(R), !R.defaultPrevented)) {
                const O = S().filter((P) => P.focusable),
                  j = O.find((P) => P.active),
                  $ = O.find((P) => P.id === g),
                  I = [j, $, ...O].filter(Boolean).map((P) => P.ref.current);
                zx(I, c);
              }
            }
            E.current = !1;
          }),
          onBlur: $e(e.onBlur, () => p(!1)),
        }),
      })
    );
  }),
  jx = "RovingFocusGroupItem",
  Fx = v.forwardRef((e, t) => {
    const {
        __scopeRovingFocusGroup: n,
        focusable: r = !0,
        active: o = !1,
        tabStopId: i,
        children: s,
        ...a
      } = e,
      l = Vi(),
      u = i || l,
      c = qT(jx, n),
      f = c.currentTabStopId === u,
      d = Lx(n),
      { onFocusableItemAdd: m, onFocusableItemRemove: y, currentTabStopId: g } = c;
    return (
      v.useEffect(() => {
        if (r) return m(), () => y();
      }, [r, m, y]),
      C.jsx(Mf.ItemSlot, {
        scope: n,
        id: u,
        focusable: r,
        active: o,
        children: C.jsx(rt.span, {
          tabIndex: f ? 0 : -1,
          "data-orientation": c.orientation,
          ...a,
          ref: t,
          onMouseDown: $e(e.onMouseDown, (w) => {
            r ? c.onItemFocus(u) : w.preventDefault();
          }),
          onFocus: $e(e.onFocus, () => c.onItemFocus(u)),
          onKeyDown: $e(e.onKeyDown, (w) => {
            if (w.key === "Tab" && w.shiftKey) {
              c.onItemShiftTab();
              return;
            }
            if (w.target !== w.currentTarget) return;
            const h = n_(w, c.orientation, c.dir);
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
                x = c.loop ? r_(x, S + 1) : x.slice(S + 1);
              }
              setTimeout(() => zx(x));
            }
          }),
          children: typeof s == "function" ? s({ isCurrentTabStop: f, hasTabStop: g != null }) : s,
        }),
      })
    );
  });
Fx.displayName = jx;
var e_ = {
  ArrowLeft: "prev",
  ArrowUp: "prev",
  ArrowRight: "next",
  ArrowDown: "next",
  PageUp: "first",
  Home: "first",
  PageDown: "last",
  End: "last",
};
function t_(e, t) {
  return t !== "rtl" ? e : e === "ArrowLeft" ? "ArrowRight" : e === "ArrowRight" ? "ArrowLeft" : e;
}
function n_(e, t, n) {
  const r = t_(e.key, n);
  if (
    !(t === "vertical" && ["ArrowLeft", "ArrowRight"].includes(r)) &&
    !(t === "horizontal" && ["ArrowUp", "ArrowDown"].includes(r))
  )
    return e_[r];
}
function zx(e, t = !1) {
  const n = document.activeElement;
  for (const r of e)
    if (r === n || (r.focus({ preventScroll: t }), document.activeElement !== n)) return;
}
function r_(e, t) {
  return e.map((n, r) => e[(t + r) % e.length]);
}
var o_ = Ox,
  i_ = Fx;
function s_(e, t) {
  return v.useReducer((n, r) => t[n][r] ?? n, e);
}
var Rs = (e) => {
  const { present: t, children: n } = e,
    r = a_(t),
    o = typeof n == "function" ? n({ present: r.isPresent }) : v.Children.only(n),
    i = en(r.ref, l_(o));
  return typeof n == "function" || r.isPresent ? v.cloneElement(o, { ref: i }) : null;
};
Rs.displayName = "Presence";
function a_(e) {
  const [t, n] = v.useState(),
    r = v.useRef(null),
    o = v.useRef(e),
    i = v.useRef("none"),
    s = e ? "mounted" : "unmounted",
    [a, l] = s_(s, {
      mounted: { UNMOUNT: "unmounted", ANIMATION_OUT: "unmountSuspended" },
      unmountSuspended: { MOUNT: "mounted", ANIMATION_END: "unmounted" },
      unmounted: { MOUNT: "mounted" },
    });
  return (
    v.useEffect(() => {
      const u = ra(r.current);
      i.current = a === "mounted" ? u : "none";
    }, [a]),
    as(() => {
      const u = r.current,
        c = o.current;
      if (c !== e) {
        const d = i.current,
          m = ra(u);
        e
          ? l("MOUNT")
          : m === "none" || (u == null ? void 0 : u.display) === "none"
            ? l("UNMOUNT")
            : l(c && d !== m ? "ANIMATION_OUT" : "UNMOUNT"),
          (o.current = e);
      }
    }, [e, l]),
    as(() => {
      if (t) {
        let u;
        const c = t.ownerDocument.defaultView ?? window,
          f = (m) => {
            const g = ra(r.current).includes(CSS.escape(m.animationName));
            if (m.target === t && g && (l("ANIMATION_END"), !o.current)) {
              const w = t.style.animationFillMode;
              (t.style.animationFillMode = "forwards"),
                (u = c.setTimeout(() => {
                  t.style.animationFillMode === "forwards" && (t.style.animationFillMode = w);
                }));
            }
          },
          d = (m) => {
            m.target === t && (i.current = ra(r.current));
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
function ra(e) {
  return (e == null ? void 0 : e.animationName) || "none";
}
function l_(e) {
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
  [u_, W5] = ru(ou, [Vx]),
  $x = Vx(),
  [c_, fh] = u_(ou),
  Bx = v.forwardRef((e, t) => {
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
      c = Ix(a),
      [f, d] = ch({ prop: r, onChange: o, defaultProp: i ?? "", caller: ou });
    return C.jsx(c_, {
      scope: n,
      baseId: Vi(),
      value: f,
      onValueChange: d,
      orientation: s,
      dir: c,
      activationMode: l,
      children: C.jsx(rt.div, { dir: c, "data-orientation": s, ...u, ref: t }),
    });
  });
Bx.displayName = ou;
var Hx = "TabsList",
  Ux = v.forwardRef((e, t) => {
    const { __scopeTabs: n, loop: r = !0, ...o } = e,
      i = fh(Hx, n),
      s = $x(n);
    return C.jsx(o_, {
      asChild: !0,
      ...s,
      orientation: i.orientation,
      dir: i.dir,
      loop: r,
      children: C.jsx(rt.div, { role: "tablist", "aria-orientation": i.orientation, ...o, ref: t }),
    });
  });
Ux.displayName = Hx;
var Wx = "TabsTrigger",
  Gx = v.forwardRef((e, t) => {
    const { __scopeTabs: n, value: r, disabled: o = !1, ...i } = e,
      s = fh(Wx, n),
      a = $x(n),
      l = Xx(s.baseId, r),
      u = Zx(s.baseId, r),
      c = r === s.value;
    return C.jsx(i_, {
      asChild: !0,
      ...a,
      focusable: !o,
      active: c,
      children: C.jsx(rt.button, {
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
        onMouseDown: $e(e.onMouseDown, (f) => {
          !o && f.button === 0 && f.ctrlKey === !1 ? s.onValueChange(r) : f.preventDefault();
        }),
        onKeyDown: $e(e.onKeyDown, (f) => {
          [" ", "Enter"].includes(f.key) && s.onValueChange(r);
        }),
        onFocus: $e(e.onFocus, () => {
          const f = s.activationMode !== "manual";
          !c && !o && f && s.onValueChange(r);
        }),
      }),
    });
  });
Gx.displayName = Wx;
var Kx = "TabsContent",
  Yx = v.forwardRef((e, t) => {
    const { __scopeTabs: n, value: r, forceMount: o, children: i, ...s } = e,
      a = fh(Kx, n),
      l = Xx(a.baseId, r),
      u = Zx(a.baseId, r),
      c = r === a.value,
      f = v.useRef(c);
    return (
      v.useEffect(() => {
        const d = requestAnimationFrame(() => (f.current = !1));
        return () => cancelAnimationFrame(d);
      }, []),
      C.jsx(Rs, {
        present: o || c,
        children: ({ present: d }) =>
          C.jsx(rt.div, {
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
Yx.displayName = Kx;
function Xx(e, t) {
  return `${e}-trigger-${t}`;
}
function Zx(e, t) {
  return `${e}-content-${t}`;
}
var f_ = Bx,
  Qx = Ux,
  qx = Gx,
  Jx = Yx;
const d_ = f_,
  ew = v.forwardRef(({ className: e, ...t }, n) =>
    C.jsx(Qx, {
      ref: n,
      className: se(
        "inline-flex h-10 items-center justify-center rounded-md bg-muted p-1 text-muted-foreground",
        e,
      ),
      ...t,
    }),
  );
ew.displayName = Qx.displayName;
const Ia = v.forwardRef(({ className: e, ...t }, n) =>
  C.jsx(qx, {
    ref: n,
    className: se(
      "inline-flex items-center justify-center whitespace-nowrap rounded-sm px-3 py-1.5 text-sm font-medium ring-offset-background transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 data-[state=active]:bg-background data-[state=active]:text-foreground data-[state=active]:shadow-sm",
      e,
    ),
    ...t,
  }),
);
Ia.displayName = qx.displayName;
const La = v.forwardRef(({ className: e, ...t }, n) =>
  C.jsx(Jx, {
    ref: n,
    className: se(
      "mt-2 ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
      e,
    ),
    ...t,
  }),
);
La.displayName = Jx.displayName;
function h_(e, t = globalThis == null ? void 0 : globalThis.document) {
  const n = Oo(e);
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
var p_ = "DismissableLayer",
  Af = "dismissableLayer.update",
  m_ = "dismissableLayer.pointerDownOutside",
  g_ = "dismissableLayer.focusOutside",
  Vm,
  tw = v.createContext({
    layers: new Set(),
    layersWithOutsidePointerEventsDisabled: new Set(),
    branches: new Set(),
  }),
  nw = v.forwardRef((e, t) => {
    const {
        disableOutsidePointerEvents: n = !1,
        onEscapeKeyDown: r,
        onPointerDownOutside: o,
        onFocusOutside: i,
        onInteractOutside: s,
        onDismiss: a,
        ...l
      } = e,
      u = v.useContext(tw),
      [c, f] = v.useState(null),
      d =
        (c == null ? void 0 : c.ownerDocument) ??
        (globalThis == null ? void 0 : globalThis.document),
      [, m] = v.useState({}),
      y = en(t, (k) => f(k)),
      g = Array.from(u.layers),
      [w] = [...u.layersWithOutsidePointerEventsDisabled].slice(-1),
      h = g.indexOf(w),
      p = c ? g.indexOf(c) : -1,
      x = u.layersWithOutsidePointerEventsDisabled.size > 0,
      S = p >= h,
      E = x_((k) => {
        const N = k.target,
          A = [...u.branches].some((R) => R.contains(N));
        !S || A || (o == null || o(k), s == null || s(k), k.defaultPrevented || a == null || a());
      }, d),
      _ = w_((k) => {
        const N = k.target;
        [...u.branches].some((R) => R.contains(N)) ||
          (i == null || i(k), s == null || s(k), k.defaultPrevented || a == null || a());
      }, d);
    return (
      h_((k) => {
        p === u.layers.size - 1 &&
          (r == null || r(k), !k.defaultPrevented && a && (k.preventDefault(), a()));
      }, d),
      v.useEffect(() => {
        if (c)
          return (
            n &&
              (u.layersWithOutsidePointerEventsDisabled.size === 0 &&
                ((Vm = d.body.style.pointerEvents), (d.body.style.pointerEvents = "none")),
              u.layersWithOutsidePointerEventsDisabled.add(c)),
            u.layers.add(c),
            Om(),
            () => {
              n &&
                u.layersWithOutsidePointerEventsDisabled.size === 1 &&
                (d.body.style.pointerEvents = Vm);
            }
          );
      }, [c, d, n, u]),
      v.useEffect(
        () => () => {
          c && (u.layers.delete(c), u.layersWithOutsidePointerEventsDisabled.delete(c), Om());
        },
        [c, u],
      ),
      v.useEffect(() => {
        const k = () => m({});
        return document.addEventListener(Af, k), () => document.removeEventListener(Af, k);
      }, []),
      C.jsx(rt.div, {
        ...l,
        ref: y,
        style: { pointerEvents: x ? (S ? "auto" : "none") : void 0, ...e.style },
        onFocusCapture: $e(e.onFocusCapture, _.onFocusCapture),
        onBlurCapture: $e(e.onBlurCapture, _.onBlurCapture),
        onPointerDownCapture: $e(e.onPointerDownCapture, E.onPointerDownCapture),
      })
    );
  });
nw.displayName = p_;
var y_ = "DismissableLayerBranch",
  v_ = v.forwardRef((e, t) => {
    const n = v.useContext(tw),
      r = v.useRef(null),
      o = en(t, r);
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
      C.jsx(rt.div, { ...e, ref: o })
    );
  });
v_.displayName = y_;
function x_(e, t = globalThis == null ? void 0 : globalThis.document) {
  const n = Oo(e),
    r = v.useRef(!1),
    o = v.useRef(() => {});
  return (
    v.useEffect(() => {
      const i = (a) => {
          if (a.target && !r.current) {
            let l = function () {
              rw(m_, n, u, { discrete: !0 });
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
function w_(e, t = globalThis == null ? void 0 : globalThis.document) {
  const n = Oo(e),
    r = v.useRef(!1);
  return (
    v.useEffect(() => {
      const o = (i) => {
        i.target && !r.current && rw(g_, n, { originalEvent: i }, { discrete: !1 });
      };
      return t.addEventListener("focusin", o), () => t.removeEventListener("focusin", o);
    }, [t, n]),
    { onFocusCapture: () => (r.current = !0), onBlurCapture: () => (r.current = !1) }
  );
}
function Om() {
  const e = new CustomEvent(Af);
  document.dispatchEvent(e);
}
function rw(e, t, n, { discrete: r }) {
  const o = n.originalEvent.target,
    i = new CustomEvent(e, { bubbles: !1, cancelable: !0, detail: n });
  t && o.addEventListener(e, t, { once: !0 }), r ? HT(o, i) : o.dispatchEvent(i);
}
var oc = "focusScope.autoFocusOnMount",
  ic = "focusScope.autoFocusOnUnmount",
  jm = { bubbles: !1, cancelable: !0 },
  S_ = "FocusScope",
  ow = v.forwardRef((e, t) => {
    const { loop: n = !1, trapped: r = !1, onMountAutoFocus: o, onUnmountAutoFocus: i, ...s } = e,
      [a, l] = v.useState(null),
      u = Oo(o),
      c = Oo(i),
      f = v.useRef(null),
      d = en(t, (g) => l(g)),
      m = v.useRef({
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
        let g = function (x) {
            if (m.paused || !a) return;
            const S = x.target;
            a.contains(S) ? (f.current = S) : An(f.current, { select: !0 });
          },
          w = function (x) {
            if (m.paused || !a) return;
            const S = x.relatedTarget;
            S !== null && (a.contains(S) || An(f.current, { select: !0 }));
          },
          h = function (x) {
            if (document.activeElement === document.body)
              for (const E of x) E.removedNodes.length > 0 && An(a);
          };
        document.addEventListener("focusin", g), document.addEventListener("focusout", w);
        const p = new MutationObserver(h);
        return (
          a && p.observe(a, { childList: !0, subtree: !0 }),
          () => {
            document.removeEventListener("focusin", g),
              document.removeEventListener("focusout", w),
              p.disconnect();
          }
        );
      }
    }, [r, a, m.paused]),
      v.useEffect(() => {
        if (a) {
          zm.add(m);
          const g = document.activeElement;
          if (!a.contains(g)) {
            const h = new CustomEvent(oc, jm);
            a.addEventListener(oc, u),
              a.dispatchEvent(h),
              h.defaultPrevented ||
                (E_(__(iw(a)), { select: !0 }), document.activeElement === g && An(a));
          }
          return () => {
            a.removeEventListener(oc, u),
              setTimeout(() => {
                const h = new CustomEvent(ic, jm);
                a.addEventListener(ic, c),
                  a.dispatchEvent(h),
                  h.defaultPrevented || An(g ?? document.body, { select: !0 }),
                  a.removeEventListener(ic, c),
                  zm.remove(m);
              }, 0);
          };
        }
      }, [a, u, c, m]);
    const y = v.useCallback(
      (g) => {
        if ((!n && !r) || m.paused) return;
        const w = g.key === "Tab" && !g.altKey && !g.ctrlKey && !g.metaKey,
          h = document.activeElement;
        if (w && h) {
          const p = g.currentTarget,
            [x, S] = C_(p);
          x && S
            ? !g.shiftKey && h === S
              ? (g.preventDefault(), n && An(x, { select: !0 }))
              : g.shiftKey && h === x && (g.preventDefault(), n && An(S, { select: !0 }))
            : h === p && g.preventDefault();
        }
      },
      [n, r, m.paused],
    );
    return C.jsx(rt.div, { tabIndex: -1, ...s, ref: d, onKeyDown: y });
  });
ow.displayName = S_;
function E_(e, { select: t = !1 } = {}) {
  const n = document.activeElement;
  for (const r of e) if ((An(r, { select: t }), document.activeElement !== n)) return;
}
function C_(e) {
  const t = iw(e),
    n = Fm(t, e),
    r = Fm(t.reverse(), e);
  return [n, r];
}
function iw(e) {
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
function Fm(e, t) {
  for (const n of e) if (!b_(n, { upTo: t })) return n;
}
function b_(e, { upTo: t }) {
  if (getComputedStyle(e).visibility === "hidden") return !0;
  for (; e; ) {
    if (t !== void 0 && e === t) return !1;
    if (getComputedStyle(e).display === "none") return !0;
    e = e.parentElement;
  }
  return !1;
}
function k_(e) {
  return e instanceof HTMLInputElement && "select" in e;
}
function An(e, { select: t = !1 } = {}) {
  if (e && e.focus) {
    const n = document.activeElement;
    e.focus({ preventScroll: !0 }), e !== n && k_(e) && t && e.select();
  }
}
var zm = T_();
function T_() {
  let e = [];
  return {
    add(t) {
      const n = e[0];
      t !== n && (n == null || n.pause()), (e = $m(e, t)), e.unshift(t);
    },
    remove(t) {
      var n;
      (e = $m(e, t)), (n = e[0]) == null || n.resume();
    },
  };
}
function $m(e, t) {
  const n = [...e],
    r = n.indexOf(t);
  return r !== -1 && n.splice(r, 1), n;
}
function __(e) {
  return e.filter((t) => t.tagName !== "A");
}
var N_ = "Portal",
  sw = v.forwardRef((e, t) => {
    var a;
    const { container: n, ...r } = e,
      [o, i] = v.useState(!1);
    as(() => i(!0), []);
    const s =
      n ||
      (o && ((a = globalThis == null ? void 0 : globalThis.document) == null ? void 0 : a.body));
    return s ? nk.createPortal(C.jsx(rt.div, { ...r, ref: t }), s) : null;
  });
sw.displayName = N_;
var sc = 0;
function P_() {
  v.useEffect(() => {
    const e = document.querySelectorAll("[data-radix-focus-guard]");
    return (
      document.body.insertAdjacentElement("afterbegin", e[0] ?? Bm()),
      document.body.insertAdjacentElement("beforeend", e[1] ?? Bm()),
      sc++,
      () => {
        sc === 1 &&
          document.querySelectorAll("[data-radix-focus-guard]").forEach((t) => t.remove()),
          sc--;
      }
    );
  }, []);
}
function Bm() {
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
function aw(e, t) {
  var n = {};
  for (var r in e) Object.prototype.hasOwnProperty.call(e, r) && t.indexOf(r) < 0 && (n[r] = e[r]);
  if (e != null && typeof Object.getOwnPropertySymbols == "function")
    for (var o = 0, r = Object.getOwnPropertySymbols(e); o < r.length; o++)
      t.indexOf(r[o]) < 0 &&
        Object.prototype.propertyIsEnumerable.call(e, r[o]) &&
        (n[r[o]] = e[r[o]]);
  return n;
}
function M_(e, t, n) {
  if (n || arguments.length === 2)
    for (var r = 0, o = t.length, i; r < o; r++)
      (i || !(r in t)) && (i || (i = Array.prototype.slice.call(t, 0, r)), (i[r] = t[r]));
  return e.concat(i || Array.prototype.slice.call(t));
}
var Va = "right-scroll-bar-position",
  Oa = "width-before-scroll-bar",
  A_ = "with-scroll-bars-hidden",
  R_ = "--removed-body-scroll-bar-size";
function ac(e, t) {
  return typeof e == "function" ? e(t) : e && (e.current = t), e;
}
function D_(e, t) {
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
var I_ = typeof window < "u" ? v.useLayoutEffect : v.useEffect,
  Hm = new WeakMap();
function L_(e, t) {
  var n = D_(null, function (r) {
    return e.forEach(function (o) {
      return ac(o, r);
    });
  });
  return (
    I_(
      function () {
        var r = Hm.get(n);
        if (r) {
          var o = new Set(r),
            i = new Set(e),
            s = n.current;
          o.forEach(function (a) {
            i.has(a) || ac(a, null);
          }),
            i.forEach(function (a) {
              o.has(a) || ac(a, s);
            });
        }
        Hm.set(n, e);
      },
      [e],
    ),
    n
  );
}
function V_(e) {
  return e;
}
function O_(e, t) {
  t === void 0 && (t = V_);
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
function j_(e) {
  e === void 0 && (e = {});
  var t = O_(null);
  return (t.options = Yt({ async: !0, ssr: !1 }, e)), t;
}
var lw = function (e) {
  var t = e.sideCar,
    n = aw(e, ["sideCar"]);
  if (!t) throw new Error("Sidecar: please provide `sideCar` property to import the right car");
  var r = t.read();
  if (!r) throw new Error("Sidecar medium not found");
  return v.createElement(r, Yt({}, n));
};
lw.isSideCarExport = !0;
function F_(e, t) {
  return e.useMedium(t), lw;
}
var uw = j_(),
  lc = function () {},
  iu = v.forwardRef(function (e, t) {
    var n = v.useRef(null),
      r = v.useState({ onScrollCapture: lc, onWheelCapture: lc, onTouchMoveCapture: lc }),
      o = r[0],
      i = r[1],
      s = e.forwardProps,
      a = e.children,
      l = e.className,
      u = e.removeScrollBar,
      c = e.enabled,
      f = e.shards,
      d = e.sideCar,
      m = e.noRelative,
      y = e.noIsolation,
      g = e.inert,
      w = e.allowPinchZoom,
      h = e.as,
      p = h === void 0 ? "div" : h,
      x = e.gapMode,
      S = aw(e, [
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
      _ = L_([n, t]),
      k = Yt(Yt({}, S), o);
    return v.createElement(
      v.Fragment,
      null,
      c &&
        v.createElement(E, {
          sideCar: uw,
          removeScrollBar: u,
          shards: f,
          noRelative: m,
          noIsolation: y,
          inert: g,
          setCallbacks: i,
          allowPinchZoom: !!w,
          lockRef: n,
          gapMode: x,
        }),
      s
        ? v.cloneElement(v.Children.only(a), Yt(Yt({}, k), { ref: _ }))
        : v.createElement(p, Yt({}, k, { className: l, ref: _ }), a),
    );
  });
iu.defaultProps = { enabled: !0, removeScrollBar: !0, inert: !1 };
iu.classNames = { fullWidth: Oa, zeroRight: Va };
var z_ = function () {
  if (typeof __webpack_nonce__ < "u") return __webpack_nonce__;
};
function $_() {
  if (!document) return null;
  var e = document.createElement("style");
  e.type = "text/css";
  var t = z_();
  return t && e.setAttribute("nonce", t), e;
}
function B_(e, t) {
  e.styleSheet ? (e.styleSheet.cssText = t) : e.appendChild(document.createTextNode(t));
}
function H_(e) {
  var t = document.head || document.getElementsByTagName("head")[0];
  t.appendChild(e);
}
var U_ = function () {
    var e = 0,
      t = null;
    return {
      add: function (n) {
        e == 0 && (t = $_()) && (B_(t, n), H_(t)), e++;
      },
      remove: function () {
        e--, !e && t && (t.parentNode && t.parentNode.removeChild(t), (t = null));
      },
    };
  },
  W_ = function () {
    var e = U_();
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
  cw = function () {
    var e = W_(),
      t = function (n) {
        var r = n.styles,
          o = n.dynamic;
        return e(r, o), null;
      };
    return t;
  },
  G_ = { left: 0, top: 0, right: 0, gap: 0 },
  uc = function (e) {
    return parseInt(e || "", 10) || 0;
  },
  K_ = function (e) {
    var t = window.getComputedStyle(document.body),
      n = t[e === "padding" ? "paddingLeft" : "marginLeft"],
      r = t[e === "padding" ? "paddingTop" : "marginTop"],
      o = t[e === "padding" ? "paddingRight" : "marginRight"];
    return [uc(n), uc(r), uc(o)];
  },
  Y_ = function (e) {
    if ((e === void 0 && (e = "margin"), typeof window > "u")) return G_;
    var t = K_(e),
      n = document.documentElement.clientWidth,
      r = window.innerWidth;
    return { left: t[0], top: t[1], right: t[2], gap: Math.max(0, r - n + t[2] - t[0]) };
  },
  X_ = cw(),
  ko = "data-scroll-locked",
  Z_ = function (e, t, n, r) {
    var o = e.left,
      i = e.top,
      s = e.right,
      a = e.gap;
    return (
      n === void 0 && (n = "margin"),
      `
  .`
        .concat(
          A_,
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
          ko,
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
          Va,
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
          Oa,
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
        .concat(Va, " .")
        .concat(
          Va,
          ` {
    right: 0 `,
        )
        .concat(
          r,
          `;
  }

  .`,
        )
        .concat(Oa, " .")
        .concat(
          Oa,
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
          ko,
          `] {
    `,
        )
        .concat(R_, ": ")
        .concat(
          a,
          `px;
  }
`,
        )
    );
  },
  Um = function () {
    var e = parseInt(document.body.getAttribute(ko) || "0", 10);
    return isFinite(e) ? e : 0;
  },
  Q_ = function () {
    v.useEffect(function () {
      return (
        document.body.setAttribute(ko, (Um() + 1).toString()),
        function () {
          var e = Um() - 1;
          e <= 0 ? document.body.removeAttribute(ko) : document.body.setAttribute(ko, e.toString());
        }
      );
    }, []);
  },
  q_ = function (e) {
    var t = e.noRelative,
      n = e.noImportant,
      r = e.gapMode,
      o = r === void 0 ? "margin" : r;
    Q_();
    var i = v.useMemo(
      function () {
        return Y_(o);
      },
      [o],
    );
    return v.createElement(X_, { styles: Z_(i, !t, o, n ? "" : "!important") });
  },
  Rf = !1;
if (typeof window < "u")
  try {
    var oa = Object.defineProperty({}, "passive", {
      get: function () {
        return (Rf = !0), !0;
      },
    });
    window.addEventListener("test", oa, oa), window.removeEventListener("test", oa, oa);
  } catch {
    Rf = !1;
  }
var Wr = Rf ? { passive: !1 } : !1,
  J_ = function (e) {
    return e.tagName === "TEXTAREA";
  },
  fw = function (e, t) {
    if (!(e instanceof Element)) return !1;
    var n = window.getComputedStyle(e);
    return n[t] !== "hidden" && !(n.overflowY === n.overflowX && !J_(e) && n[t] === "visible");
  },
  eN = function (e) {
    return fw(e, "overflowY");
  },
  tN = function (e) {
    return fw(e, "overflowX");
  },
  Wm = function (e, t) {
    var n = t.ownerDocument,
      r = t;
    do {
      typeof ShadowRoot < "u" && r instanceof ShadowRoot && (r = r.host);
      var o = dw(e, r);
      if (o) {
        var i = hw(e, r),
          s = i[1],
          a = i[2];
        if (s > a) return !0;
      }
      r = r.parentNode;
    } while (r && r !== n.body);
    return !1;
  },
  nN = function (e) {
    var t = e.scrollTop,
      n = e.scrollHeight,
      r = e.clientHeight;
    return [t, n, r];
  },
  rN = function (e) {
    var t = e.scrollLeft,
      n = e.scrollWidth,
      r = e.clientWidth;
    return [t, n, r];
  },
  dw = function (e, t) {
    return e === "v" ? eN(t) : tN(t);
  },
  hw = function (e, t) {
    return e === "v" ? nN(t) : rN(t);
  },
  oN = function (e, t) {
    return e === "h" && t === "rtl" ? -1 : 1;
  },
  iN = function (e, t, n, r, o) {
    var i = oN(e, window.getComputedStyle(t).direction),
      s = i * r,
      a = n.target,
      l = t.contains(a),
      u = !1,
      c = s > 0,
      f = 0,
      d = 0;
    do {
      if (!a) break;
      var m = hw(e, a),
        y = m[0],
        g = m[1],
        w = m[2],
        h = g - w - i * y;
      (y || h) && dw(e, a) && ((f += h), (d += y));
      var p = a.parentNode;
      a = p && p.nodeType === Node.DOCUMENT_FRAGMENT_NODE ? p.host : p;
    } while ((!l && a !== document.body) || (l && (t.contains(a) || t === a)));
    return ((c && Math.abs(f) < 1) || (!c && Math.abs(d) < 1)) && (u = !0), u;
  },
  ia = function (e) {
    return "changedTouches" in e
      ? [e.changedTouches[0].clientX, e.changedTouches[0].clientY]
      : [0, 0];
  },
  Gm = function (e) {
    return [e.deltaX, e.deltaY];
  },
  Km = function (e) {
    return e && "current" in e ? e.current : e;
  },
  sN = function (e, t) {
    return e[0] === t[0] && e[1] === t[1];
  },
  aN = function (e) {
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
  lN = 0,
  Gr = [];
function uN(e) {
  var t = v.useRef([]),
    n = v.useRef([0, 0]),
    r = v.useRef(),
    o = v.useState(lN++)[0],
    i = v.useState(cw)[0],
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
          var g = M_([e.lockRef.current], (e.shards || []).map(Km), !0).filter(Boolean);
          return (
            g.forEach(function (w) {
              return w.classList.add("allow-interactivity-".concat(o));
            }),
            function () {
              document.body.classList.remove("block-interactivity-".concat(o)),
                g.forEach(function (w) {
                  return w.classList.remove("allow-interactivity-".concat(o));
                });
            }
          );
        }
      },
      [e.inert, e.lockRef.current, e.shards],
    );
  var a = v.useCallback(function (g, w) {
      if (("touches" in g && g.touches.length === 2) || (g.type === "wheel" && g.ctrlKey))
        return !s.current.allowPinchZoom;
      var h = ia(g),
        p = n.current,
        x = "deltaX" in g ? g.deltaX : p[0] - h[0],
        S = "deltaY" in g ? g.deltaY : p[1] - h[1],
        E,
        _ = g.target,
        k = Math.abs(x) > Math.abs(S) ? "h" : "v";
      if ("touches" in g && k === "h" && _.type === "range") return !1;
      var N = Wm(k, _);
      if (!N) return !0;
      if ((N ? (E = k) : ((E = k === "v" ? "h" : "v"), (N = Wm(k, _))), !N)) return !1;
      if ((!r.current && "changedTouches" in g && (x || S) && (r.current = E), !E)) return !0;
      var A = r.current || E;
      return iN(A, w, g, A === "h" ? x : S);
    }, []),
    l = v.useCallback(function (g) {
      var w = g;
      if (!(!Gr.length || Gr[Gr.length - 1] !== i)) {
        var h = "deltaY" in w ? Gm(w) : ia(w),
          p = t.current.filter(function (E) {
            return (
              E.name === w.type &&
              (E.target === w.target || w.target === E.shadowParent) &&
              sN(E.delta, h)
            );
          })[0];
        if (p && p.should) {
          w.cancelable && w.preventDefault();
          return;
        }
        if (!p) {
          var x = (s.current.shards || [])
              .map(Km)
              .filter(Boolean)
              .filter(function (E) {
                return E.contains(w.target);
              }),
            S = x.length > 0 ? a(w, x[0]) : !s.current.noIsolation;
          S && w.cancelable && w.preventDefault();
        }
      }
    }, []),
    u = v.useCallback(function (g, w, h, p) {
      var x = { name: g, delta: w, target: h, should: p, shadowParent: cN(h) };
      t.current.push(x),
        setTimeout(function () {
          t.current = t.current.filter(function (S) {
            return S !== x;
          });
        }, 1);
    }, []),
    c = v.useCallback(function (g) {
      (n.current = ia(g)), (r.current = void 0);
    }, []),
    f = v.useCallback(function (g) {
      u(g.type, Gm(g), g.target, a(g, e.lockRef.current));
    }, []),
    d = v.useCallback(function (g) {
      u(g.type, ia(g), g.target, a(g, e.lockRef.current));
    }, []);
  v.useEffect(function () {
    return (
      Gr.push(i),
      e.setCallbacks({ onScrollCapture: f, onWheelCapture: f, onTouchMoveCapture: d }),
      document.addEventListener("wheel", l, Wr),
      document.addEventListener("touchmove", l, Wr),
      document.addEventListener("touchstart", c, Wr),
      function () {
        (Gr = Gr.filter(function (g) {
          return g !== i;
        })),
          document.removeEventListener("wheel", l, Wr),
          document.removeEventListener("touchmove", l, Wr),
          document.removeEventListener("touchstart", c, Wr);
      }
    );
  }, []);
  var m = e.removeScrollBar,
    y = e.inert;
  return v.createElement(
    v.Fragment,
    null,
    y ? v.createElement(i, { styles: aN(o) }) : null,
    m ? v.createElement(q_, { noRelative: e.noRelative, gapMode: e.gapMode }) : null,
  );
}
function cN(e) {
  for (var t = null; e !== null; )
    e instanceof ShadowRoot && ((t = e.host), (e = e.host)), (e = e.parentNode);
  return t;
}
const fN = F_(uw, uN);
var pw = v.forwardRef(function (e, t) {
  return v.createElement(iu, Yt({}, e, { ref: t, sideCar: fN }));
});
pw.classNames = iu.classNames;
var dN = function (e) {
    if (typeof document > "u") return null;
    var t = Array.isArray(e) ? e[0] : e;
    return t.ownerDocument.body;
  },
  Kr = new WeakMap(),
  sa = new WeakMap(),
  aa = {},
  cc = 0,
  mw = function (e) {
    return e && (e.host || mw(e.parentNode));
  },
  hN = function (e, t) {
    return t
      .map(function (n) {
        if (e.contains(n)) return n;
        var r = mw(n);
        return r && e.contains(r)
          ? r
          : (console.error("aria-hidden", n, "in not contained inside", e, ". Doing nothing"),
            null);
      })
      .filter(function (n) {
        return !!n;
      });
  },
  pN = function (e, t, n, r) {
    var o = hN(t, Array.isArray(e) ? e : [e]);
    aa[n] || (aa[n] = new WeakMap());
    var i = aa[n],
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
              var m = d.getAttribute(r),
                y = m !== null && m !== "false",
                g = (Kr.get(d) || 0) + 1,
                w = (i.get(d) || 0) + 1;
              Kr.set(d, g),
                i.set(d, w),
                s.push(d),
                g === 1 && y && sa.set(d, !0),
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
      cc++,
      function () {
        s.forEach(function (f) {
          var d = Kr.get(f) - 1,
            m = i.get(f) - 1;
          Kr.set(f, d),
            i.set(f, m),
            d || (sa.has(f) || f.removeAttribute(r), sa.delete(f)),
            m || f.removeAttribute(n);
        }),
          cc--,
          cc || ((Kr = new WeakMap()), (Kr = new WeakMap()), (sa = new WeakMap()), (aa = {}));
      }
    );
  },
  mN = function (e, t, n) {
    n === void 0 && (n = "data-aria-hidden");
    var r = Array.from(Array.isArray(e) ? e : [e]),
      o = dN(e);
    return o
      ? (r.push.apply(r, Array.from(o.querySelectorAll("[aria-live], script"))),
        pN(r, o, n, "aria-hidden"))
      : function () {
          return null;
        };
  },
  su = "Dialog",
  [gw, G5] = ru(su),
  [gN, $t] = gw(su),
  yw = (e) => {
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
      [u, c] = ch({ prop: r, defaultProp: o ?? !1, onChange: i, caller: su });
    return C.jsx(gN, {
      scope: t,
      triggerRef: a,
      contentRef: l,
      contentId: Vi(),
      titleId: Vi(),
      descriptionId: Vi(),
      open: u,
      onOpenChange: c,
      onOpenToggle: v.useCallback(() => c((f) => !f), [c]),
      modal: s,
      children: n,
    });
  };
yw.displayName = su;
var vw = "DialogTrigger",
  yN = v.forwardRef((e, t) => {
    const { __scopeDialog: n, ...r } = e,
      o = $t(vw, n),
      i = en(t, o.triggerRef);
    return C.jsx(rt.button, {
      type: "button",
      "aria-haspopup": "dialog",
      "aria-expanded": o.open,
      "aria-controls": o.contentId,
      "data-state": ph(o.open),
      ...r,
      ref: i,
      onClick: $e(e.onClick, o.onOpenToggle),
    });
  });
yN.displayName = vw;
var dh = "DialogPortal",
  [vN, xw] = gw(dh, { forceMount: void 0 }),
  ww = (e) => {
    const { __scopeDialog: t, forceMount: n, children: r, container: o } = e,
      i = $t(dh, t);
    return C.jsx(vN, {
      scope: t,
      forceMount: n,
      children: v.Children.map(r, (s) =>
        C.jsx(Rs, {
          present: n || i.open,
          children: C.jsx(sw, { asChild: !0, container: o, children: s }),
        }),
      ),
    });
  };
ww.displayName = dh;
var vl = "DialogOverlay",
  Sw = v.forwardRef((e, t) => {
    const n = xw(vl, e.__scopeDialog),
      { forceMount: r = n.forceMount, ...o } = e,
      i = $t(vl, e.__scopeDialog);
    return i.modal
      ? C.jsx(Rs, { present: r || i.open, children: C.jsx(wN, { ...o, ref: t }) })
      : null;
  });
Sw.displayName = vl;
var xN = ss("DialogOverlay.RemoveScroll"),
  wN = v.forwardRef((e, t) => {
    const { __scopeDialog: n, ...r } = e,
      o = $t(vl, n);
    return C.jsx(pw, {
      as: xN,
      allowPinchZoom: !0,
      shards: [o.contentRef],
      children: C.jsx(rt.div, {
        "data-state": ph(o.open),
        ...r,
        ref: t,
        style: { pointerEvents: "auto", ...r.style },
      }),
    });
  }),
  Dr = "DialogContent",
  Ew = v.forwardRef((e, t) => {
    const n = xw(Dr, e.__scopeDialog),
      { forceMount: r = n.forceMount, ...o } = e,
      i = $t(Dr, e.__scopeDialog);
    return C.jsx(Rs, {
      present: r || i.open,
      children: i.modal ? C.jsx(SN, { ...o, ref: t }) : C.jsx(EN, { ...o, ref: t }),
    });
  });
Ew.displayName = Dr;
var SN = v.forwardRef((e, t) => {
    const n = $t(Dr, e.__scopeDialog),
      r = v.useRef(null),
      o = en(t, n.contentRef, r);
    return (
      v.useEffect(() => {
        const i = r.current;
        if (i) return mN(i);
      }, []),
      C.jsx(Cw, {
        ...e,
        ref: o,
        trapFocus: n.open,
        disableOutsidePointerEvents: !0,
        onCloseAutoFocus: $e(e.onCloseAutoFocus, (i) => {
          var s;
          i.preventDefault(), (s = n.triggerRef.current) == null || s.focus();
        }),
        onPointerDownOutside: $e(e.onPointerDownOutside, (i) => {
          const s = i.detail.originalEvent,
            a = s.button === 0 && s.ctrlKey === !0;
          (s.button === 2 || a) && i.preventDefault();
        }),
        onFocusOutside: $e(e.onFocusOutside, (i) => i.preventDefault()),
      })
    );
  }),
  EN = v.forwardRef((e, t) => {
    const n = $t(Dr, e.__scopeDialog),
      r = v.useRef(!1),
      o = v.useRef(!1);
    return C.jsx(Cw, {
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
  Cw = v.forwardRef((e, t) => {
    const { __scopeDialog: n, trapFocus: r, onOpenAutoFocus: o, onCloseAutoFocus: i, ...s } = e,
      a = $t(Dr, n),
      l = v.useRef(null),
      u = en(t, l);
    return (
      P_(),
      C.jsxs(C.Fragment, {
        children: [
          C.jsx(ow, {
            asChild: !0,
            loop: !0,
            trapped: r,
            onMountAutoFocus: o,
            onUnmountAutoFocus: i,
            children: C.jsx(nw, {
              role: "dialog",
              id: a.contentId,
              "aria-describedby": a.descriptionId,
              "aria-labelledby": a.titleId,
              "data-state": ph(a.open),
              ...s,
              ref: u,
              onDismiss: () => a.onOpenChange(!1),
            }),
          }),
          C.jsxs(C.Fragment, {
            children: [
              C.jsx(CN, { titleId: a.titleId }),
              C.jsx(kN, { contentRef: l, descriptionId: a.descriptionId }),
            ],
          }),
        ],
      })
    );
  }),
  hh = "DialogTitle",
  bw = v.forwardRef((e, t) => {
    const { __scopeDialog: n, ...r } = e,
      o = $t(hh, n);
    return C.jsx(rt.h2, { id: o.titleId, ...r, ref: t });
  });
bw.displayName = hh;
var kw = "DialogDescription",
  Tw = v.forwardRef((e, t) => {
    const { __scopeDialog: n, ...r } = e,
      o = $t(kw, n);
    return C.jsx(rt.p, { id: o.descriptionId, ...r, ref: t });
  });
Tw.displayName = kw;
var _w = "DialogClose",
  Nw = v.forwardRef((e, t) => {
    const { __scopeDialog: n, ...r } = e,
      o = $t(_w, n);
    return C.jsx(rt.button, {
      type: "button",
      ...r,
      ref: t,
      onClick: $e(e.onClick, () => o.onOpenChange(!1)),
    });
  });
Nw.displayName = _w;
function ph(e) {
  return e ? "open" : "closed";
}
var Pw = "DialogTitleWarning",
  [K5, Mw] = OT(Pw, { contentName: Dr, titleName: hh, docsSlug: "dialog" }),
  CN = ({ titleId: e }) => {
    const t = Mw(Pw),
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
  bN = "DialogDescriptionWarning",
  kN = ({ contentRef: e, descriptionId: t }) => {
    const r = `Warning: Missing \`Description\` or \`aria-describedby={undefined}\` for {${Mw(bN).contentName}}.`;
    return (
      v.useEffect(() => {
        var i;
        const o = (i = e.current) == null ? void 0 : i.getAttribute("aria-describedby");
        t && o && (document.getElementById(t) || console.warn(r));
      }, [r, e, t]),
      null
    );
  },
  Aw = yw,
  Rw = ww,
  au = Sw,
  lu = Ew,
  uu = bw,
  cu = Tw,
  Dw = Nw;
const TN = Aw,
  _N = Rw,
  Iw = v.forwardRef(({ className: e, ...t }, n) =>
    C.jsx(au, {
      ref: n,
      className: se(
        "fixed inset-0 z-50 bg-black/80 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0",
        e,
      ),
      ...t,
    }),
  );
Iw.displayName = au.displayName;
const Lw = v.forwardRef(({ className: e, children: t, ...n }, r) =>
  C.jsxs(_N, {
    children: [
      C.jsx(Iw, {}),
      C.jsxs(lu, {
        ref: r,
        className: se(
          "fixed left-[50%] top-[50%] z-50 grid w-full max-w-lg translate-x-[-50%] translate-y-[-50%] gap-4 border bg-background p-6 shadow-lg duration-200 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95 data-[state=closed]:slide-out-to-left-1/2 data-[state=closed]:slide-out-to-top-[48%] data-[state=open]:slide-in-from-left-1/2 data-[state=open]:slide-in-from-top-[48%] sm:rounded-lg",
          e,
        ),
        ...n,
        children: [
          t,
          C.jsxs(Dw, {
            className:
              "absolute right-4 top-4 rounded-sm opacity-70 ring-offset-background transition-opacity hover:opacity-100 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:pointer-events-none data-[state=open]:bg-accent data-[state=open]:text-muted-foreground",
            children: [
              C.jsx(lh, { className: "h-4 w-4" }),
              C.jsx("span", { className: "sr-only", children: "Close" }),
            ],
          }),
        ],
      }),
    ],
  }),
);
Lw.displayName = lu.displayName;
const Vw = ({ className: e, ...t }) =>
  C.jsx("div", { className: se("flex flex-col space-y-1.5 text-center sm:text-left", e), ...t });
Vw.displayName = "DialogHeader";
const Ow = ({ className: e, ...t }) =>
  C.jsx("div", {
    className: se("flex flex-col-reverse sm:flex-row sm:justify-end sm:space-x-2", e),
    ...t,
  });
Ow.displayName = "DialogFooter";
const jw = v.forwardRef(({ className: e, ...t }, n) =>
  C.jsx(uu, {
    ref: n,
    className: se("text-lg font-semibold leading-none tracking-tight", e),
    ...t,
  }),
);
jw.displayName = uu.displayName;
const NN = v.forwardRef(({ className: e, ...t }, n) =>
  C.jsx(cu, { ref: n, className: se("text-sm text-muted-foreground", e), ...t }),
);
NN.displayName = cu.displayName;
const mh = v.forwardRef(({ className: e, type: t, ...n }, r) =>
  C.jsx("input", {
    type: t,
    className: se(
      "flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-base ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium file:text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 md:text-sm",
      e,
    ),
    ref: r,
    ...n,
  }),
);
mh.displayName = "Input";
const Fw = v.forwardRef(({ className: e, ...t }, n) =>
  C.jsx("textarea", {
    className: se(
      "flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-base ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 md:text-sm",
      e,
    ),
    ref: n,
    ...t,
  }),
);
Fw.displayName = "Textarea";
const PN = Aw,
  MN = Rw,
  zw = v.forwardRef(({ className: e, ...t }, n) =>
    C.jsx(au, {
      ref: n,
      className: se(
        "fixed inset-0 z-50 bg-black/80 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0",
        e,
      ),
      ...t,
    }),
  );
zw.displayName = au.displayName;
const $w = v.forwardRef(({ className: e, children: t, ...n }, r) =>
  C.jsxs(MN, {
    children: [
      C.jsx(zw, {}),
      C.jsxs(lu, {
        ref: r,
        className: se(
          "fixed right-0 top-0 z-50 h-full w-[85%] sm:w-[420px] md:w-[480px] lg:w-[520px] border-l bg-background p-6 shadow-lg duration-300 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:slide-out-to-right data-[state=open]:slide-in-from-right",
          e,
        ),
        ...n,
        children: [
          t,
          C.jsxs(Dw, {
            className:
              "absolute right-4 top-4 rounded-sm opacity-70 ring-offset-background transition-opacity hover:opacity-100 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:pointer-events-none",
            children: [
              C.jsx(lh, { className: "h-4 w-4" }),
              C.jsx("span", { className: "sr-only", children: "Close" }),
            ],
          }),
        ],
      }),
    ],
  }),
);
$w.displayName = lu.displayName;
const Bw = ({ className: e, ...t }) => C.jsx("div", { className: se("mb-4", e), ...t });
Bw.displayName = "SheetHeader";
const Hw = v.forwardRef(({ className: e, ...t }, n) =>
  C.jsx(uu, {
    ref: n,
    className: se("text-lg font-semibold leading-none tracking-tight", e),
    ...t,
  }),
);
Hw.displayName = uu.displayName;
const AN = v.forwardRef(({ className: e, ...t }, n) =>
  C.jsx(cu, { ref: n, className: se("text-sm text-muted-foreground", e), ...t }),
);
AN.displayName = cu.displayName;
const Uw = v.createContext({});
function gh(e) {
  const t = v.useRef(null);
  return t.current === null && (t.current = e()), t.current;
}
const yh = v.createContext(null),
  fu = v.createContext({ transformPagePoint: (e) => e, isStatic: !1, reducedMotion: "never" });
function RN(e = !0) {
  const t = v.useContext(yh);
  if (t === null) return [!0, null];
  const { isPresent: n, onExitComplete: r, register: o } = t,
    i = v.useId();
  v.useEffect(() => {
    e && o(i);
  }, [e]);
  const s = v.useCallback(() => e && r && r(i), [i, r, e]);
  return !n && r ? [!1, s] : [!0];
}
const vh = typeof window < "u",
  xh = vh ? v.useLayoutEffect : v.useEffect,
  ht = (e) => e;
let Ww = ht;
function wh(e) {
  let t;
  return () => (t === void 0 && (t = e()), t);
}
const jo = (e, t, n) => {
    const r = t - e;
    return r === 0 ? 1 : (n - e) / r;
  },
  mn = (e) => e * 1e3,
  gn = (e) => e / 1e3,
  DN = { useManualTiming: !1 };
function IN(e) {
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
      const m = f && r ? t : n;
      return c && i.add(u), m.has(u) || m.add(u), u;
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
const la = ["read", "resolveKeyframes", "update", "preRender", "render", "postRender"],
  LN = 40;
function Gw(e, t) {
  let n = !1,
    r = !0;
  const o = { delta: 0, timestamp: 0, isProcessing: !1 },
    i = () => (n = !0),
    s = la.reduce((h, p) => ((h[p] = IN(i)), h), {}),
    { read: a, resolveKeyframes: l, update: u, preRender: c, render: f, postRender: d } = s,
    m = () => {
      const h = performance.now();
      (n = !1),
        (o.delta = r ? 1e3 / 60 : Math.max(Math.min(h - o.timestamp, LN), 1)),
        (o.timestamp = h),
        (o.isProcessing = !0),
        a.process(o),
        l.process(o),
        u.process(o),
        c.process(o),
        f.process(o),
        d.process(o),
        (o.isProcessing = !1),
        n && t && ((r = !1), e(m));
    },
    y = () => {
      (n = !0), (r = !0), o.isProcessing || e(m);
    };
  return {
    schedule: la.reduce((h, p) => {
      const x = s[p];
      return (h[p] = (S, E = !1, _ = !1) => (n || y(), x.schedule(S, E, _))), h;
    }, {}),
    cancel: (h) => {
      for (let p = 0; p < la.length; p++) s[la[p]].cancel(h);
    },
    state: o,
    steps: s,
  };
}
const {
    schedule: ce,
    cancel: En,
    state: Ie,
    steps: fc,
  } = Gw(typeof requestAnimationFrame < "u" ? requestAnimationFrame : ht, !0),
  Kw = v.createContext({ strict: !1 }),
  Ym = {
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
  Fo = {};
for (const e in Ym) Fo[e] = { isEnabled: (t) => Ym[e].some((n) => !!t[n]) };
function VN(e) {
  for (const t in e) Fo[t] = { ...Fo[t], ...e[t] };
}
const ON = new Set([
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
function xl(e) {
  return (
    e.startsWith("while") ||
    (e.startsWith("drag") && e !== "draggable") ||
    e.startsWith("layout") ||
    e.startsWith("onTap") ||
    e.startsWith("onPan") ||
    e.startsWith("onLayout") ||
    ON.has(e)
  );
}
let Yw = (e) => !xl(e);
function jN(e) {
  e && (Yw = (t) => (t.startsWith("on") ? !xl(t) : e(t)));
}
try {
  jN(require("@emotion/is-prop-valid").default);
} catch {}
function FN(e, t, n) {
  const r = {};
  for (const o in e)
    (o === "values" && typeof e.values == "object") ||
      ((Yw(o) ||
        (n === !0 && xl(o)) ||
        (!t && !xl(o)) ||
        (e.draggable && o.startsWith("onDrag"))) &&
        (r[o] = e[o]));
  return r;
}
function zN(e) {
  if (typeof Proxy > "u") return e;
  const t = new Map(),
    n = (...r) => e(...r);
  return new Proxy(n, {
    get: (r, o) => (o === "create" ? e : (t.has(o) || t.set(o, e(o)), t.get(o))),
  });
}
const du = v.createContext({});
function ls(e) {
  return typeof e == "string" || Array.isArray(e);
}
function hu(e) {
  return e !== null && typeof e == "object" && typeof e.start == "function";
}
const Sh = ["animate", "whileInView", "whileFocus", "whileHover", "whileTap", "whileDrag", "exit"],
  Eh = ["initial", ...Sh];
function pu(e) {
  return hu(e.animate) || Eh.some((t) => ls(e[t]));
}
function Xw(e) {
  return !!(pu(e) || e.variants);
}
function $N(e, t) {
  if (pu(e)) {
    const { initial: n, animate: r } = e;
    return { initial: n === !1 || ls(n) ? n : void 0, animate: ls(r) ? r : void 0 };
  }
  return e.inherit !== !1 ? t : {};
}
function BN(e) {
  const { initial: t, animate: n } = $N(e, v.useContext(du));
  return v.useMemo(() => ({ initial: t, animate: n }), [Xm(t), Xm(n)]);
}
function Xm(e) {
  return Array.isArray(e) ? e.join(" ") : e;
}
const HN = Symbol.for("motionComponentSymbol");
function co(e) {
  return e && typeof e == "object" && Object.prototype.hasOwnProperty.call(e, "current");
}
function UN(e, t, n) {
  return v.useCallback(
    (r) => {
      r && e.onMount && e.onMount(r),
        t && (r ? t.mount(r) : t.unmount()),
        n && (typeof n == "function" ? n(r) : co(n) && (n.current = r));
    },
    [t],
  );
}
const Ch = (e) => e.replace(/([a-z])([A-Z])/gu, "$1-$2").toLowerCase(),
  WN = "framerAppearId",
  Zw = "data-" + Ch(WN),
  { schedule: bh } = Gw(queueMicrotask, !1),
  Qw = v.createContext({});
function GN(e, t, n, r, o) {
  var i, s;
  const { visualElement: a } = v.useContext(du),
    l = v.useContext(Kw),
    u = v.useContext(yh),
    c = v.useContext(fu).reducedMotion,
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
    m = v.useContext(Qw);
  d && !d.projection && o && (d.type === "html" || d.type === "svg") && KN(f.current, n, o, m);
  const y = v.useRef(!1);
  v.useInsertionEffect(() => {
    d && y.current && d.update(n, u);
  });
  const g = n[Zw],
    w = v.useRef(
      !!g &&
        !(!((i = window.MotionHandoffIsComplete) === null || i === void 0) && i.call(window, g)) &&
        ((s = window.MotionHasOptimisedAnimation) === null || s === void 0
          ? void 0
          : s.call(window, g)),
    );
  return (
    xh(() => {
      d &&
        ((y.current = !0),
        (window.MotionIsMounted = !0),
        d.updateFeatures(),
        bh.render(d.render),
        w.current && d.animationState && d.animationState.animateChanges());
    }),
    v.useEffect(() => {
      d &&
        (!w.current && d.animationState && d.animationState.animateChanges(),
        w.current &&
          (queueMicrotask(() => {
            var h;
            (h = window.MotionHandoffMarkAsComplete) === null || h === void 0 || h.call(window, g);
          }),
          (w.current = !1)));
    }),
    d
  );
}
function KN(e, t, n, r) {
  const { layoutId: o, layout: i, drag: s, dragConstraints: a, layoutScroll: l, layoutRoot: u } = t;
  (e.projection = new n(e.latestValues, t["data-framer-portal-id"] ? void 0 : qw(e.parent))),
    e.projection.setOptions({
      layoutId: o,
      layout: i,
      alwaysMeasureLayout: !!s || (a && co(a)),
      visualElement: e,
      animationType: typeof i == "string" ? i : "both",
      initialPromotionConfig: r,
      layoutScroll: l,
      layoutRoot: u,
    });
}
function qw(e) {
  if (e) return e.options.allowProjection !== !1 ? e.projection : qw(e.parent);
}
function YN({
  preloadedFeatures: e,
  createVisualElement: t,
  useRender: n,
  useVisualState: r,
  Component: o,
}) {
  var i, s;
  e && VN(e);
  function a(u, c) {
    let f;
    const d = { ...v.useContext(fu), ...u, layoutId: XN(u) },
      { isStatic: m } = d,
      y = BN(u),
      g = r(u, m);
    if (!m && vh) {
      ZN();
      const w = QN(d);
      (f = w.MeasureLayout), (y.visualElement = GN(o, g, d, t, w.ProjectionNode));
    }
    return C.jsxs(du.Provider, {
      value: y,
      children: [
        f && y.visualElement ? C.jsx(f, { visualElement: y.visualElement, ...d }) : null,
        n(o, u, UN(g, y.visualElement, c), g, m, y.visualElement),
      ],
    });
  }
  a.displayName = `motion.${typeof o == "string" ? o : `create(${(s = (i = o.displayName) !== null && i !== void 0 ? i : o.name) !== null && s !== void 0 ? s : ""})`}`;
  const l = v.forwardRef(a);
  return (l[HN] = o), l;
}
function XN({ layoutId: e }) {
  const t = v.useContext(Uw).id;
  return t && e !== void 0 ? t + "-" + e : e;
}
function ZN(e, t) {
  v.useContext(Kw).strict;
}
function QN(e) {
  const { drag: t, layout: n } = Fo;
  if (!t && !n) return {};
  const r = { ...t, ...n };
  return {
    MeasureLayout:
      (t != null && t.isEnabled(e)) || (n != null && n.isEnabled(e)) ? r.MeasureLayout : void 0,
    ProjectionNode: r.ProjectionNode,
  };
}
const qN = [
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
function kh(e) {
  return typeof e != "string" || e.includes("-") ? !1 : !!(qN.indexOf(e) > -1 || /[A-Z]/u.test(e));
}
function Zm(e) {
  const t = [{}, {}];
  return (
    e == null ||
      e.values.forEach((n, r) => {
        (t[0][r] = n.get()), (t[1][r] = n.getVelocity());
      }),
    t
  );
}
function Th(e, t, n, r) {
  if (typeof t == "function") {
    const [o, i] = Zm(r);
    t = t(n !== void 0 ? n : e.custom, o, i);
  }
  if ((typeof t == "string" && (t = e.variants && e.variants[t]), typeof t == "function")) {
    const [o, i] = Zm(r);
    t = t(n !== void 0 ? n : e.custom, o, i);
  }
  return t;
}
const Df = (e) => Array.isArray(e),
  JN = (e) => !!(e && typeof e == "object" && e.mix && e.toValue),
  eP = (e) => (Df(e) ? e[e.length - 1] || 0 : e),
  Ve = (e) => !!(e && e.getVelocity);
function ja(e) {
  const t = Ve(e) ? e.get() : e;
  return JN(t) ? t.toValue() : t;
}
function tP({ scrapeMotionValuesFromProps: e, createRenderState: t, onUpdate: n }, r, o, i) {
  const s = { latestValues: nP(r, o, i, e), renderState: t() };
  return (
    n && ((s.onMount = (a) => n({ props: r, current: a, ...s })), (s.onUpdate = (a) => n(a))), s
  );
}
const Jw = (e) => (t, n) => {
  const r = v.useContext(du),
    o = v.useContext(yh),
    i = () => tP(e, t, r, o);
  return n ? i() : gh(i);
};
function nP(e, t, n, r) {
  const o = {},
    i = r(e, {});
  for (const d in i) o[d] = ja(i[d]);
  let { initial: s, animate: a } = e;
  const l = pu(e),
    u = Xw(e);
  t &&
    u &&
    !l &&
    e.inherit !== !1 &&
    (s === void 0 && (s = t.initial), a === void 0 && (a = t.animate));
  let c = n ? n.initial === !1 : !1;
  c = c || s === !1;
  const f = c ? a : s;
  if (f && typeof f != "boolean" && !hu(f)) {
    const d = Array.isArray(f) ? f : [f];
    for (let m = 0; m < d.length; m++) {
      const y = Th(e, d[m]);
      if (y) {
        const { transitionEnd: g, transition: w, ...h } = y;
        for (const p in h) {
          let x = h[p];
          if (Array.isArray(x)) {
            const S = c ? x.length - 1 : 0;
            x = x[S];
          }
          x !== null && (o[p] = x);
        }
        for (const p in g) o[p] = g[p];
      }
    }
  }
  return o;
}
const Xo = [
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
  jr = new Set(Xo),
  e1 = (e) => (t) => typeof t == "string" && t.startsWith(e),
  t1 = e1("--"),
  rP = e1("var(--"),
  _h = (e) => (rP(e) ? oP.test(e.split("/*")[0].trim()) : !1),
  oP = /var\(--(?:[\w-]+\s*|[\w-]+\s*,(?:\s*[^)(\s]|\s*\((?:[^)(]|\([^)(]*\))*\))+\s*)\)$/iu,
  n1 = (e, t) => (t && typeof e == "number" ? t.transform(e) : e),
  Cn = (e, t, n) => (n > t ? t : n < e ? e : n),
  Zo = { test: (e) => typeof e == "number", parse: parseFloat, transform: (e) => e },
  us = { ...Zo, transform: (e) => Cn(0, 1, e) },
  ua = { ...Zo, default: 1 },
  Ds = (e) => ({
    test: (t) => typeof t == "string" && t.endsWith(e) && t.split(" ").length === 1,
    parse: parseFloat,
    transform: (t) => `${t}${e}`,
  }),
  Rn = Ds("deg"),
  Qt = Ds("%"),
  Q = Ds("px"),
  iP = Ds("vh"),
  sP = Ds("vw"),
  Qm = { ...Qt, parse: (e) => Qt.parse(e) / 100, transform: (e) => Qt.transform(e * 100) },
  aP = {
    borderWidth: Q,
    borderTopWidth: Q,
    borderRightWidth: Q,
    borderBottomWidth: Q,
    borderLeftWidth: Q,
    borderRadius: Q,
    radius: Q,
    borderTopLeftRadius: Q,
    borderTopRightRadius: Q,
    borderBottomRightRadius: Q,
    borderBottomLeftRadius: Q,
    width: Q,
    maxWidth: Q,
    height: Q,
    maxHeight: Q,
    top: Q,
    right: Q,
    bottom: Q,
    left: Q,
    padding: Q,
    paddingTop: Q,
    paddingRight: Q,
    paddingBottom: Q,
    paddingLeft: Q,
    margin: Q,
    marginTop: Q,
    marginRight: Q,
    marginBottom: Q,
    marginLeft: Q,
    backgroundPositionX: Q,
    backgroundPositionY: Q,
  },
  lP = {
    rotate: Rn,
    rotateX: Rn,
    rotateY: Rn,
    rotateZ: Rn,
    scale: ua,
    scaleX: ua,
    scaleY: ua,
    scaleZ: ua,
    skew: Rn,
    skewX: Rn,
    skewY: Rn,
    distance: Q,
    translateX: Q,
    translateY: Q,
    translateZ: Q,
    x: Q,
    y: Q,
    z: Q,
    perspective: Q,
    transformPerspective: Q,
    opacity: us,
    originX: Qm,
    originY: Qm,
    originZ: Q,
  },
  qm = { ...Zo, transform: Math.round },
  Nh = { ...aP, ...lP, zIndex: qm, size: Q, fillOpacity: us, strokeOpacity: us, numOctaves: qm },
  uP = { x: "translateX", y: "translateY", z: "translateZ", transformPerspective: "perspective" },
  cP = Xo.length;
function fP(e, t, n) {
  let r = "",
    o = !0;
  for (let i = 0; i < cP; i++) {
    const s = Xo[i],
      a = e[s];
    if (a === void 0) continue;
    let l = !0;
    if (
      (typeof a == "number"
        ? (l = a === (s.startsWith("scale") ? 1 : 0))
        : (l = parseFloat(a) === 0),
      !l || n)
    ) {
      const u = n1(a, Nh[s]);
      if (!l) {
        o = !1;
        const c = uP[s] || s;
        r += `${c}(${u}) `;
      }
      n && (t[s] = u);
    }
  }
  return (r = r.trim()), n ? (r = n(t, o ? "" : r)) : o && (r = "none"), r;
}
function Ph(e, t, n) {
  const { style: r, vars: o, transformOrigin: i } = e;
  let s = !1,
    a = !1;
  for (const l in t) {
    const u = t[l];
    if (jr.has(l)) {
      s = !0;
      continue;
    } else if (t1(l)) {
      o[l] = u;
      continue;
    } else {
      const c = n1(u, Nh[l]);
      l.startsWith("origin") ? ((a = !0), (i[l] = c)) : (r[l] = c);
    }
  }
  if (
    (t.transform ||
      (s || n ? (r.transform = fP(t, e.transform, n)) : r.transform && (r.transform = "none")),
    a)
  ) {
    const { originX: l = "50%", originY: u = "50%", originZ: c = 0 } = i;
    r.transformOrigin = `${l} ${u} ${c}`;
  }
}
const dP = { offset: "stroke-dashoffset", array: "stroke-dasharray" },
  hP = { offset: "strokeDashoffset", array: "strokeDasharray" };
function pP(e, t, n = 1, r = 0, o = !0) {
  e.pathLength = 1;
  const i = o ? dP : hP;
  e[i.offset] = Q.transform(-r);
  const s = Q.transform(t),
    a = Q.transform(n);
  e[i.array] = `${s} ${a}`;
}
function Jm(e, t, n) {
  return typeof e == "string" ? e : Q.transform(t + n * e);
}
function mP(e, t, n) {
  const r = Jm(t, e.x, e.width),
    o = Jm(n, e.y, e.height);
  return `${r} ${o}`;
}
function Mh(
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
  if ((Ph(e, u, f), c)) {
    e.style.viewBox && (e.attrs.viewBox = e.style.viewBox);
    return;
  }
  (e.attrs = e.style), (e.style = {});
  const { attrs: d, style: m, dimensions: y } = e;
  d.transform && (y && (m.transform = d.transform), delete d.transform),
    y &&
      (o !== void 0 || i !== void 0 || m.transform) &&
      (m.transformOrigin = mP(y, o !== void 0 ? o : 0.5, i !== void 0 ? i : 0.5)),
    t !== void 0 && (d.x = t),
    n !== void 0 && (d.y = n),
    r !== void 0 && (d.scale = r),
    s !== void 0 && pP(d, s, a, l, !1);
}
const Ah = () => ({ style: {}, transform: {}, transformOrigin: {}, vars: {} }),
  r1 = () => ({ ...Ah(), attrs: {} }),
  Rh = (e) => typeof e == "string" && e.toLowerCase() === "svg";
function o1(e, { style: t, vars: n }, r, o) {
  Object.assign(e.style, t, o && o.getProjectionStyles(r));
  for (const i in n) e.style.setProperty(i, n[i]);
}
const i1 = new Set([
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
function s1(e, t, n, r) {
  o1(e, t, void 0, r);
  for (const o in t.attrs) e.setAttribute(i1.has(o) ? o : Ch(o), t.attrs[o]);
}
const wl = {};
function gP(e) {
  Object.assign(wl, e);
}
function a1(e, { layout: t, layoutId: n }) {
  return (
    jr.has(e) || e.startsWith("origin") || ((t || n !== void 0) && (!!wl[e] || e === "opacity"))
  );
}
function Dh(e, t, n) {
  var r;
  const { style: o } = e,
    i = {};
  for (const s in o)
    (Ve(o[s]) ||
      (t.style && Ve(t.style[s])) ||
      a1(s, e) ||
      ((r = n == null ? void 0 : n.getValue(s)) === null || r === void 0 ? void 0 : r.liveStyle) !==
        void 0) &&
      (i[s] = o[s]);
  return i;
}
function l1(e, t, n) {
  const r = Dh(e, t, n);
  for (const o in e)
    if (Ve(e[o]) || Ve(t[o])) {
      const i = Xo.indexOf(o) !== -1 ? "attr" + o.charAt(0).toUpperCase() + o.substring(1) : o;
      r[i] = e[o];
    }
  return r;
}
function yP(e, t) {
  try {
    t.dimensions = typeof e.getBBox == "function" ? e.getBBox() : e.getBoundingClientRect();
  } catch {
    t.dimensions = { x: 0, y: 0, width: 0, height: 0 };
  }
}
const eg = ["x", "y", "width", "height", "cx", "cy", "r"],
  vP = {
    useVisualState: Jw({
      scrapeMotionValuesFromProps: l1,
      createRenderState: r1,
      onUpdate: ({ props: e, prevProps: t, current: n, renderState: r, latestValues: o }) => {
        if (!n) return;
        let i = !!e.drag;
        if (!i) {
          for (const a in o)
            if (jr.has(a)) {
              i = !0;
              break;
            }
        }
        if (!i) return;
        let s = !t;
        if (t)
          for (let a = 0; a < eg.length; a++) {
            const l = eg[a];
            e[l] !== t[l] && (s = !0);
          }
        s &&
          ce.read(() => {
            yP(n, r),
              ce.render(() => {
                Mh(r, o, Rh(n.tagName), e.transformTemplate), s1(n, r);
              });
          });
      },
    }),
  },
  xP = { useVisualState: Jw({ scrapeMotionValuesFromProps: Dh, createRenderState: Ah }) };
function u1(e, t, n) {
  for (const r in t) !Ve(t[r]) && !a1(r, n) && (e[r] = t[r]);
}
function wP({ transformTemplate: e }, t) {
  return v.useMemo(() => {
    const n = Ah();
    return Ph(n, t, e), Object.assign({}, n.vars, n.style);
  }, [t]);
}
function SP(e, t) {
  const n = e.style || {},
    r = {};
  return u1(r, n, e), Object.assign(r, wP(e, t)), r;
}
function EP(e, t) {
  const n = {},
    r = SP(e, t);
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
function CP(e, t, n, r) {
  const o = v.useMemo(() => {
    const i = r1();
    return Mh(i, t, Rh(r), e.transformTemplate), { ...i.attrs, style: { ...i.style } };
  }, [t]);
  if (e.style) {
    const i = {};
    u1(i, e.style, e), (o.style = { ...i, ...o.style });
  }
  return o;
}
function bP(e = !1) {
  return (n, r, o, { latestValues: i }, s) => {
    const l = (kh(n) ? CP : EP)(r, i, s, n),
      u = FN(r, typeof n == "string", e),
      c = n !== v.Fragment ? { ...u, ...l, ref: o } : {},
      { children: f } = r,
      d = v.useMemo(() => (Ve(f) ? f.get() : f), [f]);
    return v.createElement(n, { ...c, children: d });
  };
}
function kP(e, t) {
  return function (r, { forwardMotionProps: o } = { forwardMotionProps: !1 }) {
    const s = {
      ...(kh(r) ? vP : xP),
      preloadedFeatures: e,
      useRender: bP(o),
      createVisualElement: t,
      Component: r,
    };
    return YN(s);
  };
}
function c1(e, t) {
  if (!Array.isArray(t)) return !1;
  const n = t.length;
  if (n !== e.length) return !1;
  for (let r = 0; r < n; r++) if (t[r] !== e[r]) return !1;
  return !0;
}
function mu(e, t, n) {
  const r = e.getProps();
  return Th(r, t, n !== void 0 ? n : r.custom, e);
}
const TP = wh(() => window.ScrollTimeline !== void 0);
class _P {
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
      if (TP() && o.attachTimeline) return o.attachTimeline(t);
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
class NP extends _P {
  then(t, n) {
    return Promise.all(this.animations).then(t).catch(n);
  }
}
function Ih(e, t) {
  return e ? e[t] || e.default || e : void 0;
}
const If = 2e4;
function f1(e) {
  let t = 0;
  const n = 50;
  let r = e.next(t);
  for (; !r.done && t < If; ) (t += n), (r = e.next(t));
  return t >= If ? 1 / 0 : t;
}
function Lh(e) {
  return typeof e == "function";
}
function tg(e, t) {
  (e.timeline = t), (e.onfinish = null);
}
const Vh = (e) => Array.isArray(e) && typeof e[0] == "number",
  PP = { linearEasing: void 0 };
function MP(e, t) {
  const n = wh(e);
  return () => {
    var r;
    return (r = PP[t]) !== null && r !== void 0 ? r : n();
  };
}
const Sl = MP(() => {
    try {
      document.createElement("div").animate({ opacity: 0 }, { easing: "linear(0, 1)" });
    } catch {
      return !1;
    }
    return !0;
  }, "linearEasing"),
  d1 = (e, t, n = 10) => {
    let r = "";
    const o = Math.max(Math.round(t / n), 2);
    for (let i = 0; i < o; i++) r += e(jo(0, o - 1, i)) + ", ";
    return `linear(${r.substring(0, r.length - 2)})`;
  };
function h1(e) {
  return !!(
    (typeof e == "function" && Sl()) ||
    !e ||
    (typeof e == "string" && (e in Lf || Sl())) ||
    Vh(e) ||
    (Array.isArray(e) && e.every(h1))
  );
}
const Si = ([e, t, n, r]) => `cubic-bezier(${e}, ${t}, ${n}, ${r})`,
  Lf = {
    linear: "linear",
    ease: "ease",
    easeIn: "ease-in",
    easeOut: "ease-out",
    easeInOut: "ease-in-out",
    circIn: Si([0, 0.65, 0.55, 1]),
    circOut: Si([0.55, 0, 1, 0.45]),
    backIn: Si([0.31, 0.01, 0.66, -0.59]),
    backOut: Si([0.33, 1.53, 0.69, 0.99]),
  };
function p1(e, t) {
  if (e)
    return typeof e == "function" && Sl()
      ? d1(e, t)
      : Vh(e)
        ? Si(e)
        : Array.isArray(e)
          ? e.map((n) => p1(n, t) || Lf.easeOut)
          : Lf[e];
}
const At = { x: !1, y: !1 };
function m1() {
  return At.x || At.y;
}
function AP(e, t, n) {
  var r;
  if (e instanceof Element) return [e];
  if (typeof e == "string") {
    let o = document;
    const i = (r = void 0) !== null && r !== void 0 ? r : o.querySelectorAll(e);
    return i ? Array.from(i) : [];
  }
  return Array.from(e);
}
function g1(e, t) {
  const n = AP(e),
    r = new AbortController(),
    o = { passive: !0, ...t, signal: r.signal };
  return [n, o, () => r.abort()];
}
function ng(e) {
  return (t) => {
    t.pointerType === "touch" || m1() || e(t);
  };
}
function RP(e, t, n = {}) {
  const [r, o, i] = g1(e, n),
    s = ng((a) => {
      const { target: l } = a,
        u = t(a);
      if (typeof u != "function" || !l) return;
      const c = ng((f) => {
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
const y1 = (e, t) => (t ? (e === t ? !0 : y1(e, t.parentElement)) : !1),
  Oh = (e) =>
    e.pointerType === "mouse" ? typeof e.button != "number" || e.button <= 0 : e.isPrimary !== !1,
  DP = new Set(["BUTTON", "INPUT", "SELECT", "TEXTAREA", "A"]);
function IP(e) {
  return DP.has(e.tagName) || e.tabIndex !== -1;
}
const Ei = new WeakSet();
function rg(e) {
  return (t) => {
    t.key === "Enter" && e(t);
  };
}
function dc(e, t) {
  e.dispatchEvent(new PointerEvent("pointer" + t, { isPrimary: !0, bubbles: !0 }));
}
const LP = (e, t) => {
  const n = e.currentTarget;
  if (!n) return;
  const r = rg(() => {
    if (Ei.has(n)) return;
    dc(n, "down");
    const o = rg(() => {
        dc(n, "up");
      }),
      i = () => dc(n, "cancel");
    n.addEventListener("keyup", o, t), n.addEventListener("blur", i, t);
  });
  n.addEventListener("keydown", r, t),
    n.addEventListener("blur", () => n.removeEventListener("keydown", r), t);
};
function og(e) {
  return Oh(e) && !m1();
}
function VP(e, t, n = {}) {
  const [r, o, i] = g1(e, n),
    s = (a) => {
      const l = a.currentTarget;
      if (!og(a) || Ei.has(l)) return;
      Ei.add(l);
      const u = t(a),
        c = (m, y) => {
          window.removeEventListener("pointerup", f),
            window.removeEventListener("pointercancel", d),
            !(!og(m) || !Ei.has(l)) &&
              (Ei.delete(l), typeof u == "function" && u(m, { success: y }));
        },
        f = (m) => {
          c(m, n.useGlobalTarget || y1(l, m.target));
        },
        d = (m) => {
          c(m, !1);
        };
      window.addEventListener("pointerup", f, o), window.addEventListener("pointercancel", d, o);
    };
  return (
    r.forEach((a) => {
      !IP(a) && a.getAttribute("tabindex") === null && (a.tabIndex = 0),
        (n.useGlobalTarget ? window : a).addEventListener("pointerdown", s, o),
        a.addEventListener("focus", (u) => LP(u, o), o);
    }),
    i
  );
}
function OP(e) {
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
const v1 = new Set(["width", "height", "top", "left", "right", "bottom", ...Xo]);
let Fa;
function jP() {
  Fa = void 0;
}
const qt = {
  now: () => (
    Fa === void 0 &&
      qt.set(Ie.isProcessing || DN.useManualTiming ? Ie.timestamp : performance.now()),
    Fa
  ),
  set: (e) => {
    (Fa = e), queueMicrotask(jP);
  },
};
function jh(e, t) {
  e.indexOf(t) === -1 && e.push(t);
}
function Fh(e, t) {
  const n = e.indexOf(t);
  n > -1 && e.splice(n, 1);
}
class zh {
  constructor() {
    this.subscriptions = [];
  }
  add(t) {
    return jh(this.subscriptions, t), () => Fh(this.subscriptions, t);
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
function x1(e, t) {
  return t ? e * (1e3 / t) : 0;
}
const ig = 30,
  FP = (e) => !isNaN(parseFloat(e)),
  Oi = { current: void 0 };
class zP {
  constructor(t, n = {}) {
    (this.version = "11.18.2"),
      (this.canTrackVelocity = null),
      (this.events = {}),
      (this.updateAndNotify = (r, o = !0) => {
        const i = qt.now();
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
      (this.updatedAt = qt.now()),
      this.canTrackVelocity === null && t !== void 0 && (this.canTrackVelocity = FP(this.current));
  }
  setPrevFrameValue(t = this.current) {
    (this.prevFrameValue = t), (this.prevUpdatedAt = this.updatedAt);
  }
  onChange(t) {
    return this.on("change", t);
  }
  on(t, n) {
    this.events[t] || (this.events[t] = new zh());
    const r = this.events[t].add(n);
    return t === "change"
      ? () => {
          r(),
            ce.read(() => {
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
    return Oi.current && Oi.current.push(this), this.current;
  }
  getPrevious() {
    return this.prev;
  }
  getVelocity() {
    const t = qt.now();
    if (!this.canTrackVelocity || this.prevFrameValue === void 0 || t - this.updatedAt > ig)
      return 0;
    const n = Math.min(this.updatedAt - this.prevUpdatedAt, ig);
    return x1(parseFloat(this.current) - parseFloat(this.prevFrameValue), n);
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
function zo(e, t) {
  return new zP(e, t);
}
function $P(e, t, n) {
  e.hasValue(t) ? e.getValue(t).set(n) : e.addValue(t, zo(n));
}
function BP(e, t) {
  const n = mu(e, t);
  let { transitionEnd: r = {}, transition: o = {}, ...i } = n || {};
  i = { ...i, ...r };
  for (const s in i) {
    const a = eP(i[s]);
    $P(e, s, a);
  }
}
function HP(e) {
  return !!(Ve(e) && e.add);
}
function Vf(e, t) {
  const n = e.getValue("willChange");
  if (HP(n)) return n.add(t);
}
function w1(e) {
  return e.props[Zw];
}
const S1 = (e, t, n) => (((1 - 3 * n + 3 * t) * e + (3 * n - 6 * t)) * e + 3 * t) * e,
  UP = 1e-7,
  WP = 12;
function GP(e, t, n, r, o) {
  let i,
    s,
    a = 0;
  do (s = t + (n - t) / 2), (i = S1(s, r, o) - e), i > 0 ? (n = s) : (t = s);
  while (Math.abs(i) > UP && ++a < WP);
  return s;
}
function Is(e, t, n, r) {
  if (e === t && n === r) return ht;
  const o = (i) => GP(i, 0, 1, e, n);
  return (i) => (i === 0 || i === 1 ? i : S1(o(i), t, r));
}
const E1 = (e) => (t) => (t <= 0.5 ? e(2 * t) / 2 : (2 - e(2 * (1 - t))) / 2),
  C1 = (e) => (t) => 1 - e(1 - t),
  b1 = Is(0.33, 1.53, 0.69, 0.99),
  $h = C1(b1),
  k1 = E1($h),
  T1 = (e) => ((e *= 2) < 1 ? 0.5 * $h(e) : 0.5 * (2 - Math.pow(2, -10 * (e - 1)))),
  Bh = (e) => 1 - Math.sin(Math.acos(e)),
  _1 = C1(Bh),
  N1 = E1(Bh),
  P1 = (e) => /^0[^.\s]+$/u.test(e);
function KP(e) {
  return typeof e == "number" ? e === 0 : e !== null ? e === "none" || e === "0" || P1(e) : !0;
}
const ji = (e) => Math.round(e * 1e5) / 1e5,
  Hh = /-?(?:\d+(?:\.\d+)?|\.\d+)/gu;
function YP(e) {
  return e == null;
}
const XP =
    /^(?:#[\da-f]{3,8}|(?:rgb|hsl)a?\((?:-?[\d.]+%?[,\s]+){2}-?[\d.]+%?\s*(?:[,/]\s*)?(?:\b\d+(?:\.\d+)?|\.\d+)?%?\))$/iu,
  Uh = (e, t) => (n) =>
    !!(
      (typeof n == "string" && XP.test(n) && n.startsWith(e)) ||
      (t && !YP(n) && Object.prototype.hasOwnProperty.call(n, t))
    ),
  M1 = (e, t, n) => (r) => {
    if (typeof r != "string") return r;
    const [o, i, s, a] = r.match(Hh);
    return {
      [e]: parseFloat(o),
      [t]: parseFloat(i),
      [n]: parseFloat(s),
      alpha: a !== void 0 ? parseFloat(a) : 1,
    };
  },
  ZP = (e) => Cn(0, 255, e),
  hc = { ...Zo, transform: (e) => Math.round(ZP(e)) },
  wr = {
    test: Uh("rgb", "red"),
    parse: M1("red", "green", "blue"),
    transform: ({ red: e, green: t, blue: n, alpha: r = 1 }) =>
      "rgba(" +
      hc.transform(e) +
      ", " +
      hc.transform(t) +
      ", " +
      hc.transform(n) +
      ", " +
      ji(us.transform(r)) +
      ")",
  };
function QP(e) {
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
const Of = { test: Uh("#"), parse: QP, transform: wr.transform },
  fo = {
    test: Uh("hsl", "hue"),
    parse: M1("hue", "saturation", "lightness"),
    transform: ({ hue: e, saturation: t, lightness: n, alpha: r = 1 }) =>
      "hsla(" +
      Math.round(e) +
      ", " +
      Qt.transform(ji(t)) +
      ", " +
      Qt.transform(ji(n)) +
      ", " +
      ji(us.transform(r)) +
      ")",
  },
  Ye = {
    test: (e) => wr.test(e) || Of.test(e) || fo.test(e),
    parse: (e) => (wr.test(e) ? wr.parse(e) : fo.test(e) ? fo.parse(e) : Of.parse(e)),
    transform: (e) =>
      typeof e == "string" ? e : e.hasOwnProperty("red") ? wr.transform(e) : fo.transform(e),
  },
  qP =
    /(?:#[\da-f]{3,8}|(?:rgb|hsl)a?\((?:-?[\d.]+%?[,\s]+){2}-?[\d.]+%?\s*(?:[,/]\s*)?(?:\b\d+(?:\.\d+)?|\.\d+)?%?\))/giu;
function JP(e) {
  var t, n;
  return (
    isNaN(e) &&
    typeof e == "string" &&
    (((t = e.match(Hh)) === null || t === void 0 ? void 0 : t.length) || 0) +
      (((n = e.match(qP)) === null || n === void 0 ? void 0 : n.length) || 0) >
      0
  );
}
const A1 = "number",
  R1 = "color",
  eM = "var",
  tM = "var(",
  sg = "${}",
  nM =
    /var\s*\(\s*--(?:[\w-]+\s*|[\w-]+\s*,(?:\s*[^)(\s]|\s*\((?:[^)(]|\([^)(]*\))*\))+\s*)\)|#[\da-f]{3,8}|(?:rgb|hsl)a?\((?:-?[\d.]+%?[,\s]+){2}-?[\d.]+%?\s*(?:[,/]\s*)?(?:\b\d+(?:\.\d+)?|\.\d+)?%?\)|-?(?:\d+(?:\.\d+)?|\.\d+)/giu;
function cs(e) {
  const t = e.toString(),
    n = [],
    r = { color: [], number: [], var: [] },
    o = [];
  let i = 0;
  const a = t
    .replace(
      nM,
      (l) => (
        Ye.test(l)
          ? (r.color.push(i), o.push(R1), n.push(Ye.parse(l)))
          : l.startsWith(tM)
            ? (r.var.push(i), o.push(eM), n.push(l))
            : (r.number.push(i), o.push(A1), n.push(parseFloat(l))),
        ++i,
        sg
      ),
    )
    .split(sg);
  return { values: n, split: a, indexes: r, types: o };
}
function D1(e) {
  return cs(e).values;
}
function I1(e) {
  const { split: t, types: n } = cs(e),
    r = t.length;
  return (o) => {
    let i = "";
    for (let s = 0; s < r; s++)
      if (((i += t[s]), o[s] !== void 0)) {
        const a = n[s];
        a === A1 ? (i += ji(o[s])) : a === R1 ? (i += Ye.transform(o[s])) : (i += o[s]);
      }
    return i;
  };
}
const rM = (e) => (typeof e == "number" ? 0 : e);
function oM(e) {
  const t = D1(e);
  return I1(e)(t.map(rM));
}
const Jn = { test: JP, parse: D1, createTransformer: I1, getAnimatableNone: oM },
  iM = new Set(["brightness", "contrast", "saturate", "opacity"]);
function sM(e) {
  const [t, n] = e.slice(0, -1).split("(");
  if (t === "drop-shadow") return e;
  const [r] = n.match(Hh) || [];
  if (!r) return e;
  const o = n.replace(r, "");
  let i = iM.has(t) ? 1 : 0;
  return r !== n && (i *= 100), t + "(" + i + o + ")";
}
const aM = /\b([a-z-]*)\(.*?\)/gu,
  jf = {
    ...Jn,
    getAnimatableNone: (e) => {
      const t = e.match(aM);
      return t ? t.map(sM).join(" ") : e;
    },
  },
  lM = {
    ...Nh,
    color: Ye,
    backgroundColor: Ye,
    outlineColor: Ye,
    fill: Ye,
    stroke: Ye,
    borderColor: Ye,
    borderTopColor: Ye,
    borderRightColor: Ye,
    borderBottomColor: Ye,
    borderLeftColor: Ye,
    filter: jf,
    WebkitFilter: jf,
  },
  Wh = (e) => lM[e];
function L1(e, t) {
  let n = Wh(e);
  return n !== jf && (n = Jn), n.getAnimatableNone ? n.getAnimatableNone(t) : void 0;
}
const uM = new Set(["auto", "none", "0"]);
function cM(e, t, n) {
  let r = 0,
    o;
  for (; r < e.length && !o; ) {
    const i = e[r];
    typeof i == "string" && !uM.has(i) && cs(i).values.length && (o = e[r]), r++;
  }
  if (o && n) for (const i of t) e[i] = L1(n, o);
}
const ag = (e) => e === Zo || e === Q,
  lg = (e, t) => parseFloat(e.split(", ")[t]),
  ug =
    (e, t) =>
    (n, { transform: r }) => {
      if (r === "none" || !r) return 0;
      const o = r.match(/^matrix3d\((.+)\)$/u);
      if (o) return lg(o[1], t);
      {
        const i = r.match(/^matrix\((.+)\)$/u);
        return i ? lg(i[1], e) : 0;
      }
    },
  fM = new Set(["x", "y", "z"]),
  dM = Xo.filter((e) => !fM.has(e));
function hM(e) {
  const t = [];
  return (
    dM.forEach((n) => {
      const r = e.getValue(n);
      r !== void 0 && (t.push([n, r.get()]), r.set(n.startsWith("scale") ? 1 : 0));
    }),
    t
  );
}
const $o = {
  width: ({ x: e }, { paddingLeft: t = "0", paddingRight: n = "0" }) =>
    e.max - e.min - parseFloat(t) - parseFloat(n),
  height: ({ y: e }, { paddingTop: t = "0", paddingBottom: n = "0" }) =>
    e.max - e.min - parseFloat(t) - parseFloat(n),
  top: (e, { top: t }) => parseFloat(t),
  left: (e, { left: t }) => parseFloat(t),
  bottom: ({ y: e }, { top: t }) => parseFloat(t) + (e.max - e.min),
  right: ({ x: e }, { left: t }) => parseFloat(t) + (e.max - e.min),
  x: ug(4, 13),
  y: ug(5, 14),
};
$o.translateX = $o.x;
$o.translateY = $o.y;
const kr = new Set();
let Ff = !1,
  zf = !1;
function V1() {
  if (zf) {
    const e = Array.from(kr).filter((r) => r.needsMeasurement),
      t = new Set(e.map((r) => r.element)),
      n = new Map();
    t.forEach((r) => {
      const o = hM(r);
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
  (zf = !1), (Ff = !1), kr.forEach((e) => e.complete()), kr.clear();
}
function O1() {
  kr.forEach((e) => {
    e.readKeyframes(), e.needsMeasurement && (zf = !0);
  });
}
function pM() {
  O1(), V1();
}
class Gh {
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
        ? (kr.add(this), Ff || ((Ff = !0), ce.read(O1), ce.resolveKeyframes(V1)))
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
      kr.delete(this);
  }
  cancel() {
    this.isComplete || ((this.isScheduled = !1), kr.delete(this));
  }
  resume() {
    this.isComplete || this.scheduleResolve();
  }
}
const j1 = (e) => /^-?(?:\d+(?:\.\d+)?|\.\d+)$/u.test(e),
  mM = /^var\(--(?:([\w-]+)|([\w-]+), ?([a-zA-Z\d ()%#.,-]+))\)/u;
function gM(e) {
  const t = mM.exec(e);
  if (!t) return [,];
  const [, n, r, o] = t;
  return [`--${n ?? r}`, o];
}
function F1(e, t, n = 1) {
  const [r, o] = gM(e);
  if (!r) return;
  const i = window.getComputedStyle(t).getPropertyValue(r);
  if (i) {
    const s = i.trim();
    return j1(s) ? parseFloat(s) : s;
  }
  return _h(o) ? F1(o, t, n + 1) : o;
}
const z1 = (e) => (t) => t.test(e),
  yM = { test: (e) => e === "auto", parse: (e) => e },
  $1 = [Zo, Q, Qt, Rn, sP, iP, yM],
  cg = (e) => $1.find(z1(e));
class B1 extends Gh {
  constructor(t, n, r, o, i) {
    super(t, n, r, o, i, !0);
  }
  readKeyframes() {
    const { unresolvedKeyframes: t, element: n, name: r } = this;
    if (!n || !n.current) return;
    super.readKeyframes();
    for (let l = 0; l < t.length; l++) {
      let u = t[l];
      if (typeof u == "string" && ((u = u.trim()), _h(u))) {
        const c = F1(u, n.current);
        c !== void 0 && (t[l] = c), l === t.length - 1 && (this.finalKeyframe = u);
      }
    }
    if ((this.resolveNoneKeyframes(), !v1.has(r) || t.length !== 2)) return;
    const [o, i] = t,
      s = cg(o),
      a = cg(i);
    if (s !== a)
      if (ag(s) && ag(a))
        for (let l = 0; l < t.length; l++) {
          const u = t[l];
          typeof u == "string" && (t[l] = parseFloat(u));
        }
      else this.needsMeasurement = !0;
  }
  resolveNoneKeyframes() {
    const { unresolvedKeyframes: t, name: n } = this,
      r = [];
    for (let o = 0; o < t.length; o++) KP(t[o]) && r.push(o);
    r.length && cM(t, r, n);
  }
  measureInitialState() {
    const { element: t, unresolvedKeyframes: n, name: r } = this;
    if (!t || !t.current) return;
    r === "height" && (this.suspendedScrollY = window.pageYOffset),
      (this.measuredOrigin = $o[r](t.measureViewportBox(), window.getComputedStyle(t.current))),
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
    (o[s] = $o[r](n.measureViewportBox(), window.getComputedStyle(n.current))),
      a !== null && this.finalKeyframe === void 0 && (this.finalKeyframe = a),
      !((t = this.removedTransforms) === null || t === void 0) &&
        t.length &&
        this.removedTransforms.forEach(([l, u]) => {
          n.getValue(l).set(u);
        }),
      this.resolveNoneKeyframes();
  }
}
const fg = (e, t) =>
  t === "zIndex"
    ? !1
    : !!(
        typeof e == "number" ||
        Array.isArray(e) ||
        (typeof e == "string" && (Jn.test(e) || e === "0") && !e.startsWith("url("))
      );
function vM(e) {
  const t = e[0];
  if (e.length === 1) return !0;
  for (let n = 0; n < e.length; n++) if (e[n] !== t) return !0;
}
function xM(e, t, n, r) {
  const o = e[0];
  if (o === null) return !1;
  if (t === "display" || t === "visibility") return !0;
  const i = e[e.length - 1],
    s = fg(o, t),
    a = fg(i, t);
  return !s || !a ? !1 : vM(e) || ((n === "spring" || Lh(n)) && r);
}
const wM = (e) => e !== null;
function gu(e, { repeat: t, repeatType: n = "loop" }, r) {
  const o = e.filter(wM),
    i = t && n !== "loop" && t % 2 === 1 ? 0 : o.length - 1;
  return !i || r === void 0 ? o[i] : r;
}
const SM = 40;
class H1 {
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
      (this.createdAt = qt.now()),
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
      ? this.resolvedAt - this.createdAt > SM
        ? this.resolvedAt
        : this.createdAt
      : this.createdAt;
  }
  get resolved() {
    return !this._resolved && !this.hasAttemptedResolve && pM(), this._resolved;
  }
  onKeyframesResolved(t, n) {
    (this.resolvedAt = qt.now()), (this.hasAttemptedResolve = !0);
    const {
      name: r,
      type: o,
      velocity: i,
      delay: s,
      onComplete: a,
      onUpdate: l,
      isGenerator: u,
    } = this.options;
    if (!u && !xM(t, r, o, i))
      if (s) this.options.duration = 0;
      else {
        l && l(gu(t, this.options, n)), a && a(), this.resolveFinishedPromise();
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
const we = (e, t, n) => e + (t - e) * n;
function pc(e, t, n) {
  return (
    n < 0 && (n += 1),
    n > 1 && (n -= 1),
    n < 1 / 6 ? e + (t - e) * 6 * n : n < 1 / 2 ? t : n < 2 / 3 ? e + (t - e) * (2 / 3 - n) * 6 : e
  );
}
function EM({ hue: e, saturation: t, lightness: n, alpha: r }) {
  (e /= 360), (t /= 100), (n /= 100);
  let o = 0,
    i = 0,
    s = 0;
  if (!t) o = i = s = n;
  else {
    const a = n < 0.5 ? n * (1 + t) : n + t - n * t,
      l = 2 * n - a;
    (o = pc(l, a, e + 1 / 3)), (i = pc(l, a, e)), (s = pc(l, a, e - 1 / 3));
  }
  return {
    red: Math.round(o * 255),
    green: Math.round(i * 255),
    blue: Math.round(s * 255),
    alpha: r,
  };
}
function El(e, t) {
  return (n) => (n > 0 ? t : e);
}
const mc = (e, t, n) => {
    const r = e * e,
      o = n * (t * t - r) + r;
    return o < 0 ? 0 : Math.sqrt(o);
  },
  CM = [Of, wr, fo],
  bM = (e) => CM.find((t) => t.test(e));
function dg(e) {
  const t = bM(e);
  if (!t) return !1;
  let n = t.parse(e);
  return t === fo && (n = EM(n)), n;
}
const hg = (e, t) => {
    const n = dg(e),
      r = dg(t);
    if (!n || !r) return El(e, t);
    const o = { ...n };
    return (i) => (
      (o.red = mc(n.red, r.red, i)),
      (o.green = mc(n.green, r.green, i)),
      (o.blue = mc(n.blue, r.blue, i)),
      (o.alpha = we(n.alpha, r.alpha, i)),
      wr.transform(o)
    );
  },
  kM = (e, t) => (n) => t(e(n)),
  Ls = (...e) => e.reduce(kM),
  $f = new Set(["none", "hidden"]);
function TM(e, t) {
  return $f.has(e) ? (n) => (n <= 0 ? e : t) : (n) => (n >= 1 ? t : e);
}
function _M(e, t) {
  return (n) => we(e, t, n);
}
function Kh(e) {
  return typeof e == "number"
    ? _M
    : typeof e == "string"
      ? _h(e)
        ? El
        : Ye.test(e)
          ? hg
          : MM
      : Array.isArray(e)
        ? U1
        : typeof e == "object"
          ? Ye.test(e)
            ? hg
            : NM
          : El;
}
function U1(e, t) {
  const n = [...e],
    r = n.length,
    o = e.map((i, s) => Kh(i)(i, t[s]));
  return (i) => {
    for (let s = 0; s < r; s++) n[s] = o[s](i);
    return n;
  };
}
function NM(e, t) {
  const n = { ...e, ...t },
    r = {};
  for (const o in n) e[o] !== void 0 && t[o] !== void 0 && (r[o] = Kh(e[o])(e[o], t[o]));
  return (o) => {
    for (const i in r) n[i] = r[i](o);
    return n;
  };
}
function PM(e, t) {
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
const MM = (e, t) => {
  const n = Jn.createTransformer(t),
    r = cs(e),
    o = cs(t);
  return r.indexes.var.length === o.indexes.var.length &&
    r.indexes.color.length === o.indexes.color.length &&
    r.indexes.number.length >= o.indexes.number.length
    ? ($f.has(e) && !o.values.length) || ($f.has(t) && !r.values.length)
      ? TM(e, t)
      : Ls(U1(PM(r, o), o.values), n)
    : El(e, t);
};
function W1(e, t, n) {
  return typeof e == "number" && typeof t == "number" && typeof n == "number"
    ? we(e, t, n)
    : Kh(e)(e, t);
}
const AM = 5;
function G1(e, t, n) {
  const r = Math.max(t - AM, 0);
  return x1(n - e(r), t - r);
}
const be = {
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
  gc = 0.001;
function RM({
  duration: e = be.duration,
  bounce: t = be.bounce,
  velocity: n = be.velocity,
  mass: r = be.mass,
}) {
  let o,
    i,
    s = 1 - t;
  (s = Cn(be.minDamping, be.maxDamping, s)),
    (e = Cn(be.minDuration, be.maxDuration, gn(e))),
    s < 1
      ? ((o = (u) => {
          const c = u * s,
            f = c * e,
            d = c - n,
            m = Bf(u, s),
            y = Math.exp(-f);
          return gc - (d / m) * y;
        }),
        (i = (u) => {
          const f = u * s * e,
            d = f * n + n,
            m = Math.pow(s, 2) * Math.pow(u, 2) * e,
            y = Math.exp(-f),
            g = Bf(Math.pow(u, 2), s);
          return ((-o(u) + gc > 0 ? -1 : 1) * ((d - m) * y)) / g;
        }))
      : ((o = (u) => {
          const c = Math.exp(-u * e),
            f = (u - n) * e + 1;
          return -gc + c * f;
        }),
        (i = (u) => {
          const c = Math.exp(-u * e),
            f = (n - u) * (e * e);
          return c * f;
        }));
  const a = 5 / e,
    l = IM(o, i, a);
  if (((e = mn(e)), isNaN(l))) return { stiffness: be.stiffness, damping: be.damping, duration: e };
  {
    const u = Math.pow(l, 2) * r;
    return { stiffness: u, damping: s * 2 * Math.sqrt(r * u), duration: e };
  }
}
const DM = 12;
function IM(e, t, n) {
  let r = n;
  for (let o = 1; o < DM; o++) r = r - e(r) / t(r);
  return r;
}
function Bf(e, t) {
  return e * Math.sqrt(1 - t * t);
}
const LM = ["duration", "bounce"],
  VM = ["stiffness", "damping", "mass"];
function pg(e, t) {
  return t.some((n) => e[n] !== void 0);
}
function OM(e) {
  let t = {
    velocity: be.velocity,
    stiffness: be.stiffness,
    damping: be.damping,
    mass: be.mass,
    isResolvedFromDuration: !1,
    ...e,
  };
  if (!pg(e, VM) && pg(e, LM))
    if (e.visualDuration) {
      const n = e.visualDuration,
        r = (2 * Math.PI) / (n * 1.2),
        o = r * r,
        i = 2 * Cn(0.05, 1, 1 - (e.bounce || 0)) * Math.sqrt(o);
      t = { ...t, mass: be.mass, stiffness: o, damping: i };
    } else {
      const n = RM(e);
      (t = { ...t, ...n, mass: be.mass }), (t.isResolvedFromDuration = !0);
    }
  return t;
}
function K1(e = be.visualDuration, t = be.bounce) {
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
      isResolvedFromDuration: m,
    } = OM({ ...n, velocity: -gn(n.velocity || 0) }),
    y = d || 0,
    g = u / (2 * Math.sqrt(l * c)),
    w = s - i,
    h = gn(Math.sqrt(l / c)),
    p = Math.abs(w) < 5;
  r || (r = p ? be.restSpeed.granular : be.restSpeed.default),
    o || (o = p ? be.restDelta.granular : be.restDelta.default);
  let x;
  if (g < 1) {
    const E = Bf(h, g);
    x = (_) => {
      const k = Math.exp(-g * h * _);
      return s - k * (((y + g * h * w) / E) * Math.sin(E * _) + w * Math.cos(E * _));
    };
  } else if (g === 1) x = (E) => s - Math.exp(-h * E) * (w + (y + h * w) * E);
  else {
    const E = h * Math.sqrt(g * g - 1);
    x = (_) => {
      const k = Math.exp(-g * h * _),
        N = Math.min(E * _, 300);
      return s - (k * ((y + g * h * w) * Math.sinh(N) + E * w * Math.cosh(N))) / E;
    };
  }
  const S = {
    calculatedDuration: (m && f) || null,
    next: (E) => {
      const _ = x(E);
      if (m) a.done = E >= f;
      else {
        let k = 0;
        g < 1 && (k = E === 0 ? mn(y) : G1(x, E, _));
        const N = Math.abs(k) <= r,
          A = Math.abs(s - _) <= o;
        a.done = N && A;
      }
      return (a.value = a.done ? s : _), a;
    },
    toString: () => {
      const E = Math.min(f1(S), If),
        _ = d1((k) => S.next(E * k).value, E, 30);
      return E + "ms " + _;
    },
  };
  return S;
}
function mg({
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
    m = (N) => (a !== void 0 && N < a) || (l !== void 0 && N > l),
    y = (N) => (a === void 0 ? l : l === void 0 || Math.abs(a - N) < Math.abs(l - N) ? a : l);
  let g = n * t;
  const w = f + g,
    h = s === void 0 ? w : s(w);
  h !== w && (g = h - f);
  const p = (N) => -g * Math.exp(-N / r),
    x = (N) => h + p(N),
    S = (N) => {
      const A = p(N),
        R = x(N);
      (d.done = Math.abs(A) <= u), (d.value = d.done ? h : R);
    };
  let E, _;
  const k = (N) => {
    m(d.value) &&
      ((E = N),
      (_ = K1({
        keyframes: [d.value, y(d.value)],
        velocity: G1(x, N, d.value),
        damping: o,
        stiffness: i,
        restDelta: u,
        restSpeed: c,
      })));
  };
  return (
    k(0),
    {
      calculatedDuration: null,
      next: (N) => {
        let A = !1;
        return (
          !_ && E === void 0 && ((A = !0), S(N), k(N)),
          E !== void 0 && N >= E ? _.next(N - E) : (!A && S(N), d)
        );
      },
    }
  );
}
const jM = Is(0.42, 0, 1, 1),
  FM = Is(0, 0, 0.58, 1),
  Y1 = Is(0.42, 0, 0.58, 1),
  zM = (e) => Array.isArray(e) && typeof e[0] != "number",
  $M = {
    linear: ht,
    easeIn: jM,
    easeInOut: Y1,
    easeOut: FM,
    circIn: Bh,
    circInOut: N1,
    circOut: _1,
    backIn: $h,
    backInOut: k1,
    backOut: b1,
    anticipate: T1,
  },
  gg = (e) => {
    if (Vh(e)) {
      Ww(e.length === 4);
      const [t, n, r, o] = e;
      return Is(t, n, r, o);
    } else if (typeof e == "string") return $M[e];
    return e;
  };
function BM(e, t, n) {
  const r = [],
    o = n || W1,
    i = e.length - 1;
  for (let s = 0; s < i; s++) {
    let a = o(e[s], e[s + 1]);
    if (t) {
      const l = Array.isArray(t) ? t[s] || ht : t;
      a = Ls(l, a);
    }
    r.push(a);
  }
  return r;
}
function X1(e, t, { clamp: n = !0, ease: r, mixer: o } = {}) {
  const i = e.length;
  if ((Ww(i === t.length), i === 1)) return () => t[0];
  if (i === 2 && t[0] === t[1]) return () => t[1];
  const s = e[0] === e[1];
  e[0] > e[i - 1] && ((e = [...e].reverse()), (t = [...t].reverse()));
  const a = BM(t, r, o),
    l = a.length,
    u = (c) => {
      if (s && c < e[0]) return t[0];
      let f = 0;
      if (l > 1) for (; f < e.length - 2 && !(c < e[f + 1]); f++);
      const d = jo(e[f], e[f + 1], c);
      return a[f](d);
    };
  return n ? (c) => u(Cn(e[0], e[i - 1], c)) : u;
}
function HM(e, t) {
  const n = e[e.length - 1];
  for (let r = 1; r <= t; r++) {
    const o = jo(0, t, r);
    e.push(we(n, 1, o));
  }
}
function UM(e) {
  const t = [0];
  return HM(t, e.length - 1), t;
}
function WM(e, t) {
  return e.map((n) => n * t);
}
function GM(e, t) {
  return e.map(() => t || Y1).splice(0, e.length - 1);
}
function Cl({ duration: e = 300, keyframes: t, times: n, ease: r = "easeInOut" }) {
  const o = zM(r) ? r.map(gg) : gg(r),
    i = { done: !1, value: t[0] },
    s = WM(n && n.length === t.length ? n : UM(t), e),
    a = X1(s, t, { ease: Array.isArray(o) ? o : GM(t, o) });
  return { calculatedDuration: e, next: (l) => ((i.value = a(l)), (i.done = l >= e), i) };
}
const KM = (e) => {
    const t = ({ timestamp: n }) => e(n);
    return {
      start: () => ce.update(t, !0),
      stop: () => En(t),
      now: () => (Ie.isProcessing ? Ie.timestamp : qt.now()),
    };
  },
  YM = { decay: mg, inertia: mg, tween: Cl, keyframes: Cl, spring: K1 },
  XM = (e) => e / 100;
class yu extends H1 {
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
      s = (o == null ? void 0 : o.KeyframeResolver) || Gh,
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
      a = Lh(n) ? n : YM[n] || Cl;
    let l, u;
    a !== Cl && typeof t[0] != "number" && ((l = Ls(XM, W1(t[0], t[1]))), (t = [0, 100]));
    const c = a({ ...this.options, keyframes: t });
    i === "mirror" && (u = a({ ...this.options, keyframes: [...t].reverse(), velocity: -s })),
      c.calculatedDuration === null && (c.calculatedDuration = f1(c));
    const { calculatedDuration: f } = c,
      d = f + o,
      m = d * (r + 1) - o;
    return {
      generator: c,
      mirroredGenerator: u,
      mapPercentToKeyframes: l,
      calculatedDuration: f,
      resolvedDuration: d,
      totalDuration: m,
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
      const { keyframes: N } = this.options;
      return { done: !0, value: N[N.length - 1] };
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
    const { delay: d, repeat: m, repeatType: y, repeatDelay: g, onUpdate: w } = this.options;
    this.speed > 0
      ? (this.startTime = Math.min(this.startTime, t))
      : this.speed < 0 && (this.startTime = Math.min(t - c / this.speed, this.startTime)),
      n
        ? (this.currentTime = t)
        : this.holdTime !== null
          ? (this.currentTime = this.holdTime)
          : (this.currentTime = Math.round(t - this.startTime) * this.speed);
    const h = this.currentTime - d * (this.speed >= 0 ? 1 : -1),
      p = this.speed >= 0 ? h < 0 : h > c;
    (this.currentTime = Math.max(h, 0)),
      this.state === "finished" && this.holdTime === null && (this.currentTime = c);
    let x = this.currentTime,
      S = i;
    if (m) {
      const N = Math.min(this.currentTime, c) / f;
      let A = Math.floor(N),
        R = N % 1;
      !R && N >= 1 && (R = 1),
        R === 1 && A--,
        (A = Math.min(A, m + 1)),
        !!(A % 2) &&
          (y === "reverse" ? ((R = 1 - R), g && (R -= g / f)) : y === "mirror" && (S = s)),
        (x = Cn(0, 1, R) * f);
    }
    const E = p ? { done: !1, value: l[0] } : S.next(x);
    a && (E.value = a(E.value));
    let { done: _ } = E;
    !p && u !== null && (_ = this.speed >= 0 ? this.currentTime >= c : this.currentTime <= 0);
    const k =
      this.holdTime === null && (this.state === "finished" || (this.state === "running" && _));
    return (
      k && o !== void 0 && (E.value = gu(l, this.options, o)),
      w && w(E.value),
      k && this.finish(),
      E
    );
  }
  get duration() {
    const { resolved: t } = this;
    return t ? gn(t.calculatedDuration) : 0;
  }
  get time() {
    return gn(this.currentTime);
  }
  set time(t) {
    (t = mn(t)),
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
    (this.playbackSpeed = t), n && (this.time = gn(this.currentTime));
  }
  play() {
    if ((this.resolver.isScheduled || this.resolver.resume(), !this._resolved)) {
      this.pendingPlayState = "running";
      return;
    }
    if (this.isStopped) return;
    const { driver: t = KM, onPlay: n, startTime: r } = this.options;
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
function ZM(e) {
  return new yu(e);
}
const QM = new Set(["opacity", "clipPath", "filter", "transform"]);
function qM(
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
  const c = p1(a, o);
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
const JM = wh(() => Object.hasOwnProperty.call(Element.prototype, "animate")),
  bl = 10,
  eA = 2e4;
function tA(e) {
  return Lh(e.type) || e.type === "spring" || !h1(e.ease);
}
function nA(e, t) {
  const n = new yu({ ...t, keyframes: e, repeat: 0, delay: 0, isGenerator: !0 });
  let r = { done: !1, value: e[0] };
  const o = [];
  let i = 0;
  for (; !r.done && i < eA; ) (r = n.sample(i)), o.push(r.value), (i += bl);
  return { times: void 0, keyframes: o, duration: i - bl, ease: "linear" };
}
const Z1 = { anticipate: T1, backInOut: k1, circInOut: N1 };
function rA(e) {
  return e in Z1;
}
class yg extends H1 {
  constructor(t) {
    super(t);
    const { name: n, motionValue: r, element: o, keyframes: i } = this.options;
    (this.resolver = new B1(i, (s, a) => this.onKeyframesResolved(s, a), n, r, o)),
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
    if ((typeof i == "string" && Sl() && rA(i) && (i = Z1[i]), tA(this.options))) {
      const { onComplete: f, onUpdate: d, motionValue: m, element: y, ...g } = this.options,
        w = nA(t, g);
      (t = w.keyframes),
        t.length === 1 && (t[1] = t[0]),
        (r = w.duration),
        (o = w.times),
        (i = w.ease),
        (s = "keyframes");
    }
    const c = qM(a.owner.current, l, t, { ...this.options, duration: r, times: o, ease: i });
    return (
      (c.startTime = u ?? this.calcStartTime()),
      this.pendingTimeline
        ? (tg(c, this.pendingTimeline), (this.pendingTimeline = void 0))
        : (c.onfinish = () => {
            const { onComplete: f } = this.options;
            a.set(gu(t, this.options, n)), f && f(), this.cancel(), this.resolveFinishedPromise();
          }),
      { animation: c, duration: r, times: o, type: s, ease: i, keyframes: t }
    );
  }
  get duration() {
    const { resolved: t } = this;
    if (!t) return 0;
    const { duration: n } = t;
    return gn(n);
  }
  get time() {
    const { resolved: t } = this;
    if (!t) return 0;
    const { animation: n } = t;
    return gn(n.currentTime || 0);
  }
  set time(t) {
    const { resolved: n } = this;
    if (!n) return;
    const { animation: r } = n;
    r.currentTime = mn(t);
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
      if (!n) return ht;
      const { animation: r } = n;
      tg(r, t);
    }
    return ht;
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
      const { motionValue: u, onUpdate: c, onComplete: f, element: d, ...m } = this.options,
        y = new yu({
          ...m,
          keyframes: r,
          duration: o,
          type: i,
          ease: s,
          times: a,
          isGenerator: !0,
        }),
        g = mn(this.time);
      u.setWithVelocity(y.sample(g - bl).value, y.sample(g).value, bl);
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
    return JM() && r && QM.has(r) && !l && !u && !o && i !== "mirror" && s !== 0 && a !== "inertia";
  }
}
const oA = { type: "spring", stiffness: 500, damping: 25, restSpeed: 10 },
  iA = (e) => ({
    type: "spring",
    stiffness: 550,
    damping: e === 0 ? 2 * Math.sqrt(550) : 30,
    restSpeed: 10,
  }),
  sA = { type: "keyframes", duration: 0.8 },
  aA = { type: "keyframes", ease: [0.25, 0.1, 0.35, 1], duration: 0.3 },
  lA = (e, { keyframes: t }) =>
    t.length > 2 ? sA : jr.has(e) ? (e.startsWith("scale") ? iA(t[1]) : oA) : aA;
function uA({
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
const Yh =
  (e, t, n, r = {}, o, i) =>
  (s) => {
    const a = Ih(r, e) || {},
      l = a.delay || r.delay || 0;
    let { elapsed: u = 0 } = r;
    u = u - mn(l);
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
    uA(a) || (c = { ...c, ...lA(e, c) }),
      c.duration && (c.duration = mn(c.duration)),
      c.repeatDelay && (c.repeatDelay = mn(c.repeatDelay)),
      c.from !== void 0 && (c.keyframes[0] = c.from);
    let f = !1;
    if (
      ((c.type === !1 || (c.duration === 0 && !c.repeatDelay)) &&
        ((c.duration = 0), c.delay === 0 && (f = !0)),
      f && !i && t.get() !== void 0)
    ) {
      const d = gu(c.keyframes, a);
      if (d !== void 0)
        return (
          ce.update(() => {
            c.onUpdate(d), c.onComplete();
          }),
          new NP([])
        );
    }
    return !i && yg.supports(c) ? new yg(c) : new yu(c);
  };
function cA({ protectedKeys: e, needsAnimating: t }, n) {
  const r = e.hasOwnProperty(n) && t[n] !== !0;
  return (t[n] = !1), r;
}
function Q1(e, t, { delay: n = 0, transitionOverride: r, type: o } = {}) {
  var i;
  let { transition: s = e.getDefaultTransition(), transitionEnd: a, ...l } = t;
  r && (s = r);
  const u = [],
    c = o && e.animationState && e.animationState.getState()[o];
  for (const f in l) {
    const d = e.getValue(f, (i = e.latestValues[f]) !== null && i !== void 0 ? i : null),
      m = l[f];
    if (m === void 0 || (c && cA(c, f))) continue;
    const y = { delay: n, ...Ih(s || {}, f) };
    let g = !1;
    if (window.MotionHandoffAnimation) {
      const h = w1(e);
      if (h) {
        const p = window.MotionHandoffAnimation(h, f, ce);
        p !== null && ((y.startTime = p), (g = !0));
      }
    }
    Vf(e, f), d.start(Yh(f, d, m, e.shouldReduceMotion && v1.has(f) ? { type: !1 } : y, e, g));
    const w = d.animation;
    w && u.push(w);
  }
  return (
    a &&
      Promise.all(u).then(() => {
        ce.update(() => {
          a && BP(e, a);
        });
      }),
    u
  );
}
function Hf(e, t, n = {}) {
  var r;
  const o = mu(
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
  const s = o ? () => Promise.all(Q1(e, o, n)) : () => Promise.resolve(),
    a =
      e.variantChildren && e.variantChildren.size
        ? (u = 0) => {
            const { delayChildren: c = 0, staggerChildren: f, staggerDirection: d } = i;
            return fA(e, t, c + u, f, d, n);
          }
        : () => Promise.resolve(),
    { when: l } = i;
  if (l) {
    const [u, c] = l === "beforeChildren" ? [s, a] : [a, s];
    return u().then(() => c());
  } else return Promise.all([s(), a(n.delay)]);
}
function fA(e, t, n = 0, r = 0, o = 1, i) {
  const s = [],
    a = (e.variantChildren.size - 1) * r,
    l = o === 1 ? (u = 0) => u * r : (u = 0) => a - u * r;
  return (
    Array.from(e.variantChildren)
      .sort(dA)
      .forEach((u, c) => {
        u.notify("AnimationStart", t),
          s.push(Hf(u, t, { ...i, delay: n + l(c) }).then(() => u.notify("AnimationComplete", t)));
      }),
    Promise.all(s)
  );
}
function dA(e, t) {
  return e.sortNodePosition(t);
}
function hA(e, t, n = {}) {
  e.notify("AnimationStart", t);
  let r;
  if (Array.isArray(t)) {
    const o = t.map((i) => Hf(e, i, n));
    r = Promise.all(o);
  } else if (typeof t == "string") r = Hf(e, t, n);
  else {
    const o = typeof t == "function" ? mu(e, t, n.custom) : t;
    r = Promise.all(Q1(e, o, n));
  }
  return r.then(() => {
    e.notify("AnimationComplete", t);
  });
}
const pA = Eh.length;
function q1(e) {
  if (!e) return;
  if (!e.isControllingVariants) {
    const n = e.parent ? q1(e.parent) || {} : {};
    return e.props.initial !== void 0 && (n.initial = e.props.initial), n;
  }
  const t = {};
  for (let n = 0; n < pA; n++) {
    const r = Eh[n],
      o = e.props[r];
    (ls(o) || o === !1) && (t[r] = o);
  }
  return t;
}
const mA = [...Sh].reverse(),
  gA = Sh.length;
function yA(e) {
  return (t) => Promise.all(t.map(({ animation: n, options: r }) => hA(e, n, r)));
}
function vA(e) {
  let t = yA(e),
    n = vg(),
    r = !0;
  const o = (l) => (u, c) => {
    var f;
    const d = mu(
      e,
      c,
      l === "exit"
        ? (f = e.presenceContext) === null || f === void 0
          ? void 0
          : f.custom
        : void 0,
    );
    if (d) {
      const { transition: m, transitionEnd: y, ...g } = d;
      u = { ...u, ...g, ...y };
    }
    return u;
  };
  function i(l) {
    t = l(e);
  }
  function s(l) {
    const { props: u } = e,
      c = q1(e.parent) || {},
      f = [],
      d = new Set();
    let m = {},
      y = 1 / 0;
    for (let w = 0; w < gA; w++) {
      const h = mA[w],
        p = n[h],
        x = u[h] !== void 0 ? u[h] : c[h],
        S = ls(x),
        E = h === l ? p.isActive : null;
      E === !1 && (y = w);
      let _ = x === c[h] && x !== u[h] && S;
      if (
        (_ && r && e.manuallyAnimateOnMount && (_ = !1),
        (p.protectedKeys = { ...m }),
        (!p.isActive && E === null) || (!x && !p.prevProp) || hu(x) || typeof x == "boolean")
      )
        continue;
      const k = xA(p.prevProp, x);
      let N = k || (h === l && p.isActive && !_ && S) || (w > y && S),
        A = !1;
      const R = Array.isArray(x) ? x : [x];
      let O = R.reduce(o(h), {});
      E === !1 && (O = {});
      const { prevResolvedValues: j = {} } = p,
        $ = { ...j, ...O },
        b = (V) => {
          (N = !0), d.has(V) && ((A = !0), d.delete(V)), (p.needsAnimating[V] = !0);
          const M = e.getValue(V);
          M && (M.liveStyle = !1);
        };
      for (const V in $) {
        const M = O[V],
          T = j[V];
        if (m.hasOwnProperty(V)) continue;
        let D = !1;
        Df(M) && Df(T) ? (D = !c1(M, T)) : (D = M !== T),
          D
            ? M != null
              ? b(V)
              : d.add(V)
            : M !== void 0 && d.has(V)
              ? b(V)
              : (p.protectedKeys[V] = !0);
      }
      (p.prevProp = x),
        (p.prevResolvedValues = O),
        p.isActive && (m = { ...m, ...O }),
        r && e.blockInitialAnimation && (N = !1),
        N && (!(_ && k) || A) && f.push(...R.map((V) => ({ animation: V, options: { type: h } })));
    }
    if (d.size) {
      const w = {};
      d.forEach((h) => {
        const p = e.getBaseTarget(h),
          x = e.getValue(h);
        x && (x.liveStyle = !0), (w[h] = p ?? null);
      }),
        f.push({ animation: w });
    }
    let g = !!f.length;
    return (
      r && (u.initial === !1 || u.initial === u.animate) && !e.manuallyAnimateOnMount && (g = !1),
      (r = !1),
      g ? t(f) : Promise.resolve()
    );
  }
  function a(l, u) {
    var c;
    if (n[l].isActive === u) return Promise.resolve();
    (c = e.variantChildren) === null ||
      c === void 0 ||
      c.forEach((d) => {
        var m;
        return (m = d.animationState) === null || m === void 0 ? void 0 : m.setActive(l, u);
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
      (n = vg()), (r = !0);
    },
  };
}
function xA(e, t) {
  return typeof t == "string" ? t !== e : Array.isArray(t) ? !c1(t, e) : !1;
}
function cr(e = !1) {
  return { isActive: e, protectedKeys: {}, needsAnimating: {}, prevResolvedValues: {} };
}
function vg() {
  return {
    animate: cr(!0),
    whileInView: cr(),
    whileHover: cr(),
    whileTap: cr(),
    whileDrag: cr(),
    whileFocus: cr(),
    exit: cr(),
  };
}
class rr {
  constructor(t) {
    (this.isMounted = !1), (this.node = t);
  }
  update() {}
}
class wA extends rr {
  constructor(t) {
    super(t), t.animationState || (t.animationState = vA(t));
  }
  updateAnimationControlsSubscription() {
    const { animate: t } = this.node.getProps();
    hu(t) && (this.unmountControls = t.subscribe(this.node));
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
let SA = 0;
class EA extends rr {
  constructor() {
    super(...arguments), (this.id = SA++);
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
const CA = { animation: { Feature: wA }, exit: { Feature: EA } };
function fs(e, t, n, r = { passive: !0 }) {
  return e.addEventListener(t, n, r), () => e.removeEventListener(t, n);
}
function Vs(e) {
  return { point: { x: e.pageX, y: e.pageY } };
}
const bA = (e) => (t) => Oh(t) && e(t, Vs(t));
function Fi(e, t, n, r) {
  return fs(e, t, bA(n), r);
}
const xg = (e, t) => Math.abs(e - t);
function kA(e, t) {
  const n = xg(e.x, t.x),
    r = xg(e.y, t.y);
  return Math.sqrt(n ** 2 + r ** 2);
}
class J1 {
  constructor(t, n, { transformPagePoint: r, contextWindow: o, dragSnapToOrigin: i = !1 } = {}) {
    if (
      ((this.startEvent = null),
      (this.lastMoveEvent = null),
      (this.lastMoveEventInfo = null),
      (this.handlers = {}),
      (this.contextWindow = window),
      (this.updatePoint = () => {
        if (!(this.lastMoveEvent && this.lastMoveEventInfo)) return;
        const f = vc(this.lastMoveEventInfo, this.history),
          d = this.startEvent !== null,
          m = kA(f.offset, { x: 0, y: 0 }) >= 3;
        if (!d && !m) return;
        const { point: y } = f,
          { timestamp: g } = Ie;
        this.history.push({ ...y, timestamp: g });
        const { onStart: w, onMove: h } = this.handlers;
        d || (w && w(this.lastMoveEvent, f), (this.startEvent = this.lastMoveEvent)),
          h && h(this.lastMoveEvent, f);
      }),
      (this.handlePointerMove = (f, d) => {
        (this.lastMoveEvent = f),
          (this.lastMoveEventInfo = yc(d, this.transformPagePoint)),
          ce.update(this.updatePoint, !0);
      }),
      (this.handlePointerUp = (f, d) => {
        this.end();
        const { onEnd: m, onSessionEnd: y, resumeAnimation: g } = this.handlers;
        if ((this.dragSnapToOrigin && g && g(), !(this.lastMoveEvent && this.lastMoveEventInfo)))
          return;
        const w = vc(
          f.type === "pointercancel" ? this.lastMoveEventInfo : yc(d, this.transformPagePoint),
          this.history,
        );
        this.startEvent && m && m(f, w), y && y(f, w);
      }),
      !Oh(t))
    )
      return;
    (this.dragSnapToOrigin = i),
      (this.handlers = n),
      (this.transformPagePoint = r),
      (this.contextWindow = o || window);
    const s = Vs(t),
      a = yc(s, this.transformPagePoint),
      { point: l } = a,
      { timestamp: u } = Ie;
    this.history = [{ ...l, timestamp: u }];
    const { onSessionStart: c } = n;
    c && c(t, vc(a, this.history)),
      (this.removeListeners = Ls(
        Fi(this.contextWindow, "pointermove", this.handlePointerMove),
        Fi(this.contextWindow, "pointerup", this.handlePointerUp),
        Fi(this.contextWindow, "pointercancel", this.handlePointerUp),
      ));
  }
  updateHandlers(t) {
    this.handlers = t;
  }
  end() {
    this.removeListeners && this.removeListeners(), En(this.updatePoint);
  }
}
function yc(e, t) {
  return t ? { point: t(e.point) } : e;
}
function wg(e, t) {
  return { x: e.x - t.x, y: e.y - t.y };
}
function vc({ point: e }, t) {
  return { point: e, delta: wg(e, eS(t)), offset: wg(e, TA(t)), velocity: _A(t, 0.1) };
}
function TA(e) {
  return e[0];
}
function eS(e) {
  return e[e.length - 1];
}
function _A(e, t) {
  if (e.length < 2) return { x: 0, y: 0 };
  let n = e.length - 1,
    r = null;
  const o = eS(e);
  for (; n >= 0 && ((r = e[n]), !(o.timestamp - r.timestamp > mn(t))); ) n--;
  if (!r) return { x: 0, y: 0 };
  const i = gn(o.timestamp - r.timestamp);
  if (i === 0) return { x: 0, y: 0 };
  const s = { x: (o.x - r.x) / i, y: (o.y - r.y) / i };
  return s.x === 1 / 0 && (s.x = 0), s.y === 1 / 0 && (s.y = 0), s;
}
const tS = 1e-4,
  NA = 1 - tS,
  PA = 1 + tS,
  nS = 0.01,
  MA = 0 - nS,
  AA = 0 + nS;
function mt(e) {
  return e.max - e.min;
}
function RA(e, t, n) {
  return Math.abs(e - t) <= n;
}
function Sg(e, t, n, r = 0.5) {
  (e.origin = r),
    (e.originPoint = we(t.min, t.max, e.origin)),
    (e.scale = mt(n) / mt(t)),
    (e.translate = we(n.min, n.max, e.origin) - e.originPoint),
    ((e.scale >= NA && e.scale <= PA) || isNaN(e.scale)) && (e.scale = 1),
    ((e.translate >= MA && e.translate <= AA) || isNaN(e.translate)) && (e.translate = 0);
}
function zi(e, t, n, r) {
  Sg(e.x, t.x, n.x, r ? r.originX : void 0), Sg(e.y, t.y, n.y, r ? r.originY : void 0);
}
function Eg(e, t, n) {
  (e.min = n.min + t.min), (e.max = e.min + mt(t));
}
function DA(e, t, n) {
  Eg(e.x, t.x, n.x), Eg(e.y, t.y, n.y);
}
function Cg(e, t, n) {
  (e.min = t.min - n.min), (e.max = e.min + mt(t));
}
function $i(e, t, n) {
  Cg(e.x, t.x, n.x), Cg(e.y, t.y, n.y);
}
function IA(e, { min: t, max: n }, r) {
  return (
    t !== void 0 && e < t
      ? (e = r ? we(t, e, r.min) : Math.max(e, t))
      : n !== void 0 && e > n && (e = r ? we(n, e, r.max) : Math.min(e, n)),
    e
  );
}
function bg(e, t, n) {
  return {
    min: t !== void 0 ? e.min + t : void 0,
    max: n !== void 0 ? e.max + n - (e.max - e.min) : void 0,
  };
}
function LA(e, { top: t, left: n, bottom: r, right: o }) {
  return { x: bg(e.x, n, o), y: bg(e.y, t, r) };
}
function kg(e, t) {
  let n = t.min - e.min,
    r = t.max - e.max;
  return t.max - t.min < e.max - e.min && ([n, r] = [r, n]), { min: n, max: r };
}
function VA(e, t) {
  return { x: kg(e.x, t.x), y: kg(e.y, t.y) };
}
function OA(e, t) {
  let n = 0.5;
  const r = mt(e),
    o = mt(t);
  return (
    o > r ? (n = jo(t.min, t.max - r, e.min)) : r > o && (n = jo(e.min, e.max - o, t.min)),
    Cn(0, 1, n)
  );
}
function jA(e, t) {
  const n = {};
  return (
    t.min !== void 0 && (n.min = t.min - e.min), t.max !== void 0 && (n.max = t.max - e.min), n
  );
}
const Uf = 0.35;
function FA(e = Uf) {
  return (
    e === !1 ? (e = 0) : e === !0 && (e = Uf),
    { x: Tg(e, "left", "right"), y: Tg(e, "top", "bottom") }
  );
}
function Tg(e, t, n) {
  return { min: _g(e, t), max: _g(e, n) };
}
function _g(e, t) {
  return typeof e == "number" ? e : e[t] || 0;
}
const Ng = () => ({ translate: 0, scale: 1, origin: 0, originPoint: 0 }),
  ho = () => ({ x: Ng(), y: Ng() }),
  Pg = () => ({ min: 0, max: 0 }),
  _e = () => ({ x: Pg(), y: Pg() });
function wt(e) {
  return [e("x"), e("y")];
}
function rS({ top: e, left: t, right: n, bottom: r }) {
  return { x: { min: t, max: n }, y: { min: e, max: r } };
}
function zA({ x: e, y: t }) {
  return { top: t.min, right: e.max, bottom: t.max, left: e.min };
}
function $A(e, t) {
  if (!t) return e;
  const n = t({ x: e.left, y: e.top }),
    r = t({ x: e.right, y: e.bottom });
  return { top: n.y, left: n.x, bottom: r.y, right: r.x };
}
function xc(e) {
  return e === void 0 || e === 1;
}
function Wf({ scale: e, scaleX: t, scaleY: n }) {
  return !xc(e) || !xc(t) || !xc(n);
}
function hr(e) {
  return Wf(e) || oS(e) || e.z || e.rotate || e.rotateX || e.rotateY || e.skewX || e.skewY;
}
function oS(e) {
  return Mg(e.x) || Mg(e.y);
}
function Mg(e) {
  return e && e !== "0%";
}
function kl(e, t, n) {
  const r = e - n,
    o = t * r;
  return n + o;
}
function Ag(e, t, n, r, o) {
  return o !== void 0 && (e = kl(e, o, r)), kl(e, n, r) + t;
}
function Gf(e, t = 0, n = 1, r, o) {
  (e.min = Ag(e.min, t, n, r, o)), (e.max = Ag(e.max, t, n, r, o));
}
function iS(e, { x: t, y: n }) {
  Gf(e.x, t.translate, t.scale, t.originPoint), Gf(e.y, n.translate, n.scale, n.originPoint);
}
const Rg = 0.999999999999,
  Dg = 1.0000000000001;
function BA(e, t, n, r = !1) {
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
        mo(e, { x: -i.scroll.offset.x, y: -i.scroll.offset.y }),
      s && ((t.x *= s.x.scale), (t.y *= s.y.scale), iS(e, s)),
      r && hr(i.latestValues) && mo(e, i.latestValues));
  }
  t.x < Dg && t.x > Rg && (t.x = 1), t.y < Dg && t.y > Rg && (t.y = 1);
}
function po(e, t) {
  (e.min = e.min + t), (e.max = e.max + t);
}
function Ig(e, t, n, r, o = 0.5) {
  const i = we(e.min, e.max, o);
  Gf(e, t, n, i, r);
}
function mo(e, t) {
  Ig(e.x, t.x, t.scaleX, t.scale, t.originX), Ig(e.y, t.y, t.scaleY, t.scale, t.originY);
}
function sS(e, t) {
  return rS($A(e.getBoundingClientRect(), t));
}
function HA(e, t, n) {
  const r = sS(e, n),
    { scroll: o } = t;
  return o && (po(r.x, o.offset.x), po(r.y, o.offset.y)), r;
}
const aS = ({ current: e }) => (e ? e.ownerDocument.defaultView : null),
  UA = new WeakMap();
class WA {
  constructor(t) {
    (this.openDragLock = null),
      (this.isDragging = !1),
      (this.currentDirection = null),
      (this.originPoint = { x: 0, y: 0 }),
      (this.constraints = !1),
      (this.hasMutatedConstraints = !1),
      (this.elastic = _e()),
      (this.visualElement = t);
  }
  start(t, { snapToCursor: n = !1 } = {}) {
    const { presenceContext: r } = this.visualElement;
    if (r && r.isPresent === !1) return;
    const o = (c) => {
        const { dragSnapToOrigin: f } = this.getProps();
        f ? this.pauseAnimation() : this.stopAnimation(), n && this.snapToCursor(Vs(c).point);
      },
      i = (c, f) => {
        const { drag: d, dragPropagation: m, onDragStart: y } = this.getProps();
        if (
          d &&
          !m &&
          (this.openDragLock && this.openDragLock(),
          (this.openDragLock = OP(d)),
          !this.openDragLock)
        )
          return;
        (this.isDragging = !0),
          (this.currentDirection = null),
          this.resolveConstraints(),
          this.visualElement.projection &&
            ((this.visualElement.projection.isAnimationBlocked = !0),
            (this.visualElement.projection.target = void 0)),
          wt((w) => {
            let h = this.getAxisMotionValue(w).get() || 0;
            if (Qt.test(h)) {
              const { projection: p } = this.visualElement;
              if (p && p.layout) {
                const x = p.layout.layoutBox[w];
                x && (h = mt(x) * (parseFloat(h) / 100));
              }
            }
            this.originPoint[w] = h;
          }),
          y && ce.postRender(() => y(c, f)),
          Vf(this.visualElement, "transform");
        const { animationState: g } = this.visualElement;
        g && g.setActive("whileDrag", !0);
      },
      s = (c, f) => {
        const {
          dragPropagation: d,
          dragDirectionLock: m,
          onDirectionLock: y,
          onDrag: g,
        } = this.getProps();
        if (!d && !this.openDragLock) return;
        const { offset: w } = f;
        if (m && this.currentDirection === null) {
          (this.currentDirection = GA(w)),
            this.currentDirection !== null && y && y(this.currentDirection);
          return;
        }
        this.updateAxis("x", f.point, w),
          this.updateAxis("y", f.point, w),
          this.visualElement.render(),
          g && g(c, f);
      },
      a = (c, f) => this.stop(c, f),
      l = () =>
        wt((c) => {
          var f;
          return (
            this.getAnimationState(c) === "paused" &&
            ((f = this.getAxisMotionValue(c).animation) === null || f === void 0
              ? void 0
              : f.play())
          );
        }),
      { dragSnapToOrigin: u } = this.getProps();
    this.panSession = new J1(
      t,
      { onSessionStart: o, onStart: i, onMove: s, onSessionEnd: a, resumeAnimation: l },
      {
        transformPagePoint: this.visualElement.getTransformPagePoint(),
        dragSnapToOrigin: u,
        contextWindow: aS(this.visualElement),
      },
    );
  }
  stop(t, n) {
    const r = this.isDragging;
    if ((this.cancel(), !r)) return;
    const { velocity: o } = n;
    this.startAnimation(o);
    const { onDragEnd: i } = this.getProps();
    i && ce.postRender(() => i(t, n));
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
    if (!r || !ca(t, o, this.currentDirection)) return;
    const i = this.getAxisMotionValue(t);
    let s = this.originPoint[t] + r[t];
    this.constraints && this.constraints[t] && (s = IA(s, this.constraints[t], this.elastic[t])),
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
    n && co(n)
      ? this.constraints || (this.constraints = this.resolveRefConstraints())
      : n && o
        ? (this.constraints = LA(o.layoutBox, n))
        : (this.constraints = !1),
      (this.elastic = FA(r)),
      i !== this.constraints &&
        o &&
        this.constraints &&
        !this.hasMutatedConstraints &&
        wt((s) => {
          this.constraints !== !1 &&
            this.getAxisMotionValue(s) &&
            (this.constraints[s] = jA(o.layoutBox[s], this.constraints[s]));
        });
  }
  resolveRefConstraints() {
    const { dragConstraints: t, onMeasureDragConstraints: n } = this.getProps();
    if (!t || !co(t)) return !1;
    const r = t.current,
      { projection: o } = this.visualElement;
    if (!o || !o.layout) return !1;
    const i = HA(r, o.root, this.visualElement.getTransformPagePoint());
    let s = VA(o.layout.layoutBox, i);
    if (n) {
      const a = n(zA(s));
      (this.hasMutatedConstraints = !!a), a && (s = rS(a));
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
      u = wt((c) => {
        if (!ca(c, n, this.currentDirection)) return;
        let f = (l && l[c]) || {};
        s && (f = { min: 0, max: 0 });
        const d = o ? 200 : 1e6,
          m = o ? 40 : 1e7,
          y = {
            type: "inertia",
            velocity: r ? t[c] : 0,
            bounceStiffness: d,
            bounceDamping: m,
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
    return Vf(this.visualElement, t), r.start(Yh(t, r, 0, n, this.visualElement, !1));
  }
  stopAnimation() {
    wt((t) => this.getAxisMotionValue(t).stop());
  }
  pauseAnimation() {
    wt((t) => {
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
    wt((n) => {
      const { drag: r } = this.getProps();
      if (!ca(n, r, this.currentDirection)) return;
      const { projection: o } = this.visualElement,
        i = this.getAxisMotionValue(n);
      if (o && o.layout) {
        const { min: s, max: a } = o.layout.layoutBox[n];
        i.set(t[n] - we(s, a, 0.5));
      }
    });
  }
  scalePositionWithinConstraints() {
    if (!this.visualElement.current) return;
    const { drag: t, dragConstraints: n } = this.getProps(),
      { projection: r } = this.visualElement;
    if (!co(n) || !r || !this.constraints) return;
    this.stopAnimation();
    const o = { x: 0, y: 0 };
    wt((s) => {
      const a = this.getAxisMotionValue(s);
      if (a && this.constraints !== !1) {
        const l = a.get();
        o[s] = OA({ min: l, max: l }, this.constraints[s]);
      }
    });
    const { transformTemplate: i } = this.visualElement.getProps();
    (this.visualElement.current.style.transform = i ? i({}, "") : "none"),
      r.root && r.root.updateScroll(),
      r.updateLayout(),
      this.resolveConstraints(),
      wt((s) => {
        if (!ca(s, t, null)) return;
        const a = this.getAxisMotionValue(s),
          { min: l, max: u } = this.constraints[s];
        a.set(we(l, u, o[s]));
      });
  }
  addListeners() {
    if (!this.visualElement.current) return;
    UA.set(this.visualElement, this);
    const t = this.visualElement.current,
      n = Fi(t, "pointerdown", (l) => {
        const { drag: u, dragListener: c = !0 } = this.getProps();
        u && c && this.start(l);
      }),
      r = () => {
        const { dragConstraints: l } = this.getProps();
        co(l) && l.current && (this.constraints = this.resolveRefConstraints());
      },
      { projection: o } = this.visualElement,
      i = o.addEventListener("measure", r);
    o && !o.layout && (o.root && o.root.updateScroll(), o.updateLayout()), ce.read(r);
    const s = fs(window, "resize", () => this.scalePositionWithinConstraints()),
      a = o.addEventListener("didUpdate", ({ delta: l, hasLayoutChanged: u }) => {
        this.isDragging &&
          u &&
          (wt((c) => {
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
        dragElastic: s = Uf,
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
function ca(e, t, n) {
  return (t === !0 || t === e) && (n === null || n === e);
}
function GA(e, t = 10) {
  let n = null;
  return Math.abs(e.y) > t ? (n = "y") : Math.abs(e.x) > t && (n = "x"), n;
}
class KA extends rr {
  constructor(t) {
    super(t),
      (this.removeGroupControls = ht),
      (this.removeListeners = ht),
      (this.controls = new WA(t));
  }
  mount() {
    const { dragControls: t } = this.node.getProps();
    t && (this.removeGroupControls = t.subscribe(this.controls)),
      (this.removeListeners = this.controls.addListeners() || ht);
  }
  unmount() {
    this.removeGroupControls(), this.removeListeners();
  }
}
const Lg = (e) => (t, n) => {
  e && ce.postRender(() => e(t, n));
};
class YA extends rr {
  constructor() {
    super(...arguments), (this.removePointerDownListener = ht);
  }
  onPointerDown(t) {
    this.session = new J1(t, this.createPanHandlers(), {
      transformPagePoint: this.node.getTransformPagePoint(),
      contextWindow: aS(this.node),
    });
  }
  createPanHandlers() {
    const { onPanSessionStart: t, onPanStart: n, onPan: r, onPanEnd: o } = this.node.getProps();
    return {
      onSessionStart: Lg(t),
      onStart: Lg(n),
      onMove: r,
      onEnd: (i, s) => {
        delete this.session, o && ce.postRender(() => o(i, s));
      },
    };
  }
  mount() {
    this.removePointerDownListener = Fi(this.node.current, "pointerdown", (t) =>
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
const za = { hasAnimatedSinceResize: !0, hasEverUpdated: !1 };
function Vg(e, t) {
  return t.max === t.min ? 0 : (e / (t.max - t.min)) * 100;
}
const fi = {
    correct: (e, t) => {
      if (!t.target) return e;
      if (typeof e == "string")
        if (Q.test(e)) e = parseFloat(e);
        else return e;
      const n = Vg(e, t.target.x),
        r = Vg(e, t.target.y);
      return `${n}% ${r}%`;
    },
  },
  XA = {
    correct: (e, { treeScale: t, projectionDelta: n }) => {
      const r = e,
        o = Jn.parse(e);
      if (o.length > 5) return r;
      const i = Jn.createTransformer(e),
        s = typeof o[0] != "number" ? 1 : 0,
        a = n.x.scale * t.x,
        l = n.y.scale * t.y;
      (o[0 + s] /= a), (o[1 + s] /= l);
      const u = we(a, l, 0.5);
      return (
        typeof o[2 + s] == "number" && (o[2 + s] /= u),
        typeof o[3 + s] == "number" && (o[3 + s] /= u),
        i(o)
      );
    },
  };
class ZA extends v.Component {
  componentDidMount() {
    const { visualElement: t, layoutGroup: n, switchLayoutGroup: r, layoutId: o } = this.props,
      { projection: i } = t;
    gP(QA),
      i &&
        (n.group && n.group.add(i),
        r && r.register && o && r.register(i),
        i.root.didUpdate(),
        i.addEventListener("animationComplete", () => {
          this.safeToRemove();
        }),
        i.setOptions({ ...i.options, onExitComplete: () => this.safeToRemove() })),
      (za.hasEverUpdated = !0);
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
              ce.postRender(() => {
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
      bh.postRender(() => {
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
function lS(e) {
  const [t, n] = RN(),
    r = v.useContext(Uw);
  return C.jsx(ZA, {
    ...e,
    layoutGroup: r,
    switchLayoutGroup: v.useContext(Qw),
    isPresent: t,
    safeToRemove: n,
  });
}
const QA = {
  borderRadius: {
    ...fi,
    applyTo: [
      "borderTopLeftRadius",
      "borderTopRightRadius",
      "borderBottomLeftRadius",
      "borderBottomRightRadius",
    ],
  },
  borderTopLeftRadius: fi,
  borderTopRightRadius: fi,
  borderBottomLeftRadius: fi,
  borderBottomRightRadius: fi,
  boxShadow: XA,
};
function qA(e, t, n) {
  const r = Ve(e) ? e : zo(e);
  return r.start(Yh("", r, t, n)), r.animation;
}
function JA(e) {
  return e instanceof SVGElement && e.tagName !== "svg";
}
const eR = (e, t) => e.depth - t.depth;
class tR {
  constructor() {
    (this.children = []), (this.isDirty = !1);
  }
  add(t) {
    jh(this.children, t), (this.isDirty = !0);
  }
  remove(t) {
    Fh(this.children, t), (this.isDirty = !0);
  }
  forEach(t) {
    this.isDirty && this.children.sort(eR), (this.isDirty = !1), this.children.forEach(t);
  }
}
function nR(e, t) {
  const n = qt.now(),
    r = ({ timestamp: o }) => {
      const i = o - n;
      i >= t && (En(r), e(i - t));
    };
  return ce.read(r, !0), () => En(r);
}
const uS = ["TopLeft", "TopRight", "BottomLeft", "BottomRight"],
  rR = uS.length,
  Og = (e) => (typeof e == "string" ? parseFloat(e) : e),
  jg = (e) => typeof e == "number" || Q.test(e);
function oR(e, t, n, r, o, i) {
  o
    ? ((e.opacity = we(0, n.opacity !== void 0 ? n.opacity : 1, iR(r))),
      (e.opacityExit = we(t.opacity !== void 0 ? t.opacity : 1, 0, sR(r))))
    : i &&
      (e.opacity = we(
        t.opacity !== void 0 ? t.opacity : 1,
        n.opacity !== void 0 ? n.opacity : 1,
        r,
      ));
  for (let s = 0; s < rR; s++) {
    const a = `border${uS[s]}Radius`;
    let l = Fg(t, a),
      u = Fg(n, a);
    if (l === void 0 && u === void 0) continue;
    l || (l = 0),
      u || (u = 0),
      l === 0 || u === 0 || jg(l) === jg(u)
        ? ((e[a] = Math.max(we(Og(l), Og(u), r), 0)), (Qt.test(u) || Qt.test(l)) && (e[a] += "%"))
        : (e[a] = u);
  }
  (t.rotate || n.rotate) && (e.rotate = we(t.rotate || 0, n.rotate || 0, r));
}
function Fg(e, t) {
  return e[t] !== void 0 ? e[t] : e.borderRadius;
}
const iR = cS(0, 0.5, _1),
  sR = cS(0.5, 0.95, ht);
function cS(e, t, n) {
  return (r) => (r < e ? 0 : r > t ? 1 : n(jo(e, t, r)));
}
function zg(e, t) {
  (e.min = t.min), (e.max = t.max);
}
function xt(e, t) {
  zg(e.x, t.x), zg(e.y, t.y);
}
function $g(e, t) {
  (e.translate = t.translate),
    (e.scale = t.scale),
    (e.originPoint = t.originPoint),
    (e.origin = t.origin);
}
function Bg(e, t, n, r, o) {
  return (e -= t), (e = kl(e, 1 / n, r)), o !== void 0 && (e = kl(e, 1 / o, r)), e;
}
function aR(e, t = 0, n = 1, r = 0.5, o, i = e, s = e) {
  if (
    (Qt.test(t) && ((t = parseFloat(t)), (t = we(s.min, s.max, t / 100) - s.min)),
    typeof t != "number")
  )
    return;
  let a = we(i.min, i.max, r);
  e === i && (a -= t), (e.min = Bg(e.min, t, n, a, o)), (e.max = Bg(e.max, t, n, a, o));
}
function Hg(e, t, [n, r, o], i, s) {
  aR(e, t[n], t[r], t[o], t.scale, i, s);
}
const lR = ["x", "scaleX", "originX"],
  uR = ["y", "scaleY", "originY"];
function Ug(e, t, n, r) {
  Hg(e.x, t, lR, n ? n.x : void 0, r ? r.x : void 0),
    Hg(e.y, t, uR, n ? n.y : void 0, r ? r.y : void 0);
}
function Wg(e) {
  return e.translate === 0 && e.scale === 1;
}
function fS(e) {
  return Wg(e.x) && Wg(e.y);
}
function Gg(e, t) {
  return e.min === t.min && e.max === t.max;
}
function cR(e, t) {
  return Gg(e.x, t.x) && Gg(e.y, t.y);
}
function Kg(e, t) {
  return Math.round(e.min) === Math.round(t.min) && Math.round(e.max) === Math.round(t.max);
}
function dS(e, t) {
  return Kg(e.x, t.x) && Kg(e.y, t.y);
}
function Yg(e) {
  return mt(e.x) / mt(e.y);
}
function Xg(e, t) {
  return e.translate === t.translate && e.scale === t.scale && e.originPoint === t.originPoint;
}
class fR {
  constructor() {
    this.members = [];
  }
  add(t) {
    jh(this.members, t), t.scheduleRender();
  }
  remove(t) {
    if ((Fh(this.members, t), t === this.prevLead && (this.prevLead = void 0), t === this.lead)) {
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
function dR(e, t, n) {
  let r = "";
  const o = e.x.translate / t.x,
    i = e.y.translate / t.y,
    s = (n == null ? void 0 : n.z) || 0;
  if (
    ((o || i || s) && (r = `translate3d(${o}px, ${i}px, ${s}px) `),
    (t.x !== 1 || t.y !== 1) && (r += `scale(${1 / t.x}, ${1 / t.y}) `),
    n)
  ) {
    const { transformPerspective: u, rotate: c, rotateX: f, rotateY: d, skewX: m, skewY: y } = n;
    u && (r = `perspective(${u}px) ${r}`),
      c && (r += `rotate(${c}deg) `),
      f && (r += `rotateX(${f}deg) `),
      d && (r += `rotateY(${d}deg) `),
      m && (r += `skewX(${m}deg) `),
      y && (r += `skewY(${y}deg) `);
  }
  const a = e.x.scale * t.x,
    l = e.y.scale * t.y;
  return (a !== 1 || l !== 1) && (r += `scale(${a}, ${l})`), r || "none";
}
const pr = {
    type: "projectionFrame",
    totalNodes: 0,
    resolvedTargetDeltas: 0,
    recalculatedProjection: 0,
  },
  Ci = typeof window < "u" && window.MotionDebug !== void 0,
  wc = ["", "X", "Y", "Z"],
  hR = { visibility: "hidden" },
  Zg = 1e3;
let pR = 0;
function Sc(e, t, n, r) {
  const { latestValues: o } = t;
  o[e] && ((n[e] = o[e]), t.setStaticValue(e, 0), r && (r[e] = 0));
}
function hS(e) {
  if (((e.hasCheckedOptimisedAppear = !0), e.root === e)) return;
  const { visualElement: t } = e.options;
  if (!t) return;
  const n = w1(t);
  if (window.MotionHasOptimisedAnimation(n, "transform")) {
    const { layout: o, layoutId: i } = e.options;
    window.MotionCancelOptimisedAnimation(n, "transform", ce, !(o || i));
  }
  const { parent: r } = e;
  r && !r.hasCheckedOptimisedAppear && hS(r);
}
function pS({
  attachResizeListener: e,
  defaultParent: t,
  measureScroll: n,
  checkIsScrollRoot: r,
  resetTransform: o,
}) {
  return class {
    constructor(s = {}, a = t == null ? void 0 : t()) {
      (this.id = pR++),
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
            Ci && (pr.totalNodes = pr.resolvedTargetDeltas = pr.recalculatedProjection = 0),
            this.nodes.forEach(yR),
            this.nodes.forEach(ER),
            this.nodes.forEach(CR),
            this.nodes.forEach(vR),
            Ci && window.MotionDebug.record(pr);
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
      this.root === this && (this.nodes = new tR());
    }
    addEventListener(s, a) {
      return (
        this.eventHandlers.has(s) || this.eventHandlers.set(s, new zh()),
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
      (this.isSVG = JA(s)), (this.instance = s);
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
            (f = nR(d, 250)),
            za.hasAnimatedSinceResize && ((za.hasAnimatedSinceResize = !1), this.nodes.forEach(qg));
        });
      }
      l && this.root.registerSharedNode(l, this),
        this.options.animate !== !1 &&
          c &&
          (l || u) &&
          this.addEventListener(
            "didUpdate",
            ({ delta: f, hasLayoutChanged: d, hasRelativeTargetChanged: m, layout: y }) => {
              if (this.isTreeAnimationBlocked()) {
                (this.target = void 0), (this.relativeTarget = void 0);
                return;
              }
              const g = this.options.transition || c.getDefaultTransition() || NR,
                { onLayoutAnimationStart: w, onLayoutAnimationComplete: h } = c.getProps(),
                p = !this.targetLayout || !dS(this.targetLayout, y) || m,
                x = !d && m;
              if (
                this.options.layoutRoot ||
                (this.resumeFrom && this.resumeFrom.instance) ||
                x ||
                (d && (p || !this.currentAnimation))
              ) {
                this.resumeFrom &&
                  ((this.resumingFrom = this.resumeFrom),
                  (this.resumingFrom.resumingFrom = void 0)),
                  this.setAnimationOrigin(f, x);
                const S = { ...Ih(g, "layout"), onPlay: w, onComplete: h };
                (c.shouldReduceMotion || this.options.layoutRoot) && ((S.delay = 0), (S.type = !1)),
                  this.startAnimation(S);
              } else
                d || qg(this),
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
        En(this.updateProjection);
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
        ((this.isUpdating = !0), this.nodes && this.nodes.forEach(bR), this.animationId++);
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
        (window.MotionCancelOptimisedAnimation && !this.hasCheckedOptimisedAppear && hS(this),
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
        this.unblockUpdate(), this.clearAllSnapshots(), this.nodes.forEach(Qg);
        return;
      }
      this.isUpdating || this.nodes.forEach(wR),
        (this.isUpdating = !1),
        this.nodes.forEach(SR),
        this.nodes.forEach(mR),
        this.nodes.forEach(gR),
        this.clearAllSnapshots();
      const a = qt.now();
      (Ie.delta = Cn(0, 1e3 / 60, a - Ie.timestamp)),
        (Ie.timestamp = a),
        (Ie.isProcessing = !0),
        fc.update.process(Ie),
        fc.preRender.process(Ie),
        fc.render.process(Ie),
        (Ie.isProcessing = !1);
    }
    didUpdate() {
      this.updateScheduled || ((this.updateScheduled = !0), bh.read(this.scheduleUpdate));
    }
    clearAllSnapshots() {
      this.nodes.forEach(xR), this.sharedNodes.forEach(kR);
    }
    scheduleUpdateProjection() {
      this.projectionUpdateScheduled ||
        ((this.projectionUpdateScheduled = !0), ce.preRender(this.updateProjection, !1, !0));
    }
    scheduleCheckAfterUnmount() {
      ce.postRender(() => {
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
        (this.layoutCorrected = _e()),
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
        a = this.projectionDelta && !fS(this.projectionDelta),
        l = this.getTransformTemplate(),
        u = l ? l(this.latestValues, "") : void 0,
        c = u !== this.prevTransformTemplateValue;
      s &&
        (a || hr(this.latestValues) || c) &&
        (o(this.instance, u), (this.shouldResetTransform = !1), this.scheduleRender());
    }
    measure(s = !0) {
      const a = this.measurePageBox();
      let l = this.removeElementScroll(a);
      return (
        s && (l = this.removeTransform(l)),
        PR(l),
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
      if (!a) return _e();
      const l = a.measureViewportBox();
      if (
        !(((s = this.scroll) === null || s === void 0 ? void 0 : s.wasRoot) || this.path.some(MR))
      ) {
        const { scroll: c } = this.root;
        c && (po(l.x, c.offset.x), po(l.y, c.offset.y));
      }
      return l;
    }
    removeElementScroll(s) {
      var a;
      const l = _e();
      if ((xt(l, s), !((a = this.scroll) === null || a === void 0) && a.wasRoot)) return l;
      for (let u = 0; u < this.path.length; u++) {
        const c = this.path[u],
          { scroll: f, options: d } = c;
        c !== this.root &&
          f &&
          d.layoutScroll &&
          (f.wasRoot && xt(l, s), po(l.x, f.offset.x), po(l.y, f.offset.y));
      }
      return l;
    }
    applyTransform(s, a = !1) {
      const l = _e();
      xt(l, s);
      for (let u = 0; u < this.path.length; u++) {
        const c = this.path[u];
        !a &&
          c.options.layoutScroll &&
          c.scroll &&
          c !== c.root &&
          mo(l, { x: -c.scroll.offset.x, y: -c.scroll.offset.y }),
          hr(c.latestValues) && mo(l, c.latestValues);
      }
      return hr(this.latestValues) && mo(l, this.latestValues), l;
    }
    removeTransform(s) {
      const a = _e();
      xt(a, s);
      for (let l = 0; l < this.path.length; l++) {
        const u = this.path[l];
        if (!u.instance || !hr(u.latestValues)) continue;
        Wf(u.latestValues) && u.updateSnapshot();
        const c = _e(),
          f = u.measurePageBox();
        xt(c, f), Ug(a, u.latestValues, u.snapshot ? u.snapshot.layoutBox : void 0, c);
      }
      return hr(this.latestValues) && Ug(a, this.latestValues), a;
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
        this.relativeParent.resolvedRelativeTargetAt !== Ie.timestamp &&
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
          ((this.resolvedRelativeTargetAt = Ie.timestamp),
          !this.targetDelta && !this.relativeTarget)
        ) {
          const m = this.getClosestProjectingParent();
          m && m.layout && this.animationProgress !== 1
            ? ((this.relativeParent = m),
              this.forceRelativeParentToResolveTarget(),
              (this.relativeTarget = _e()),
              (this.relativeTargetOrigin = _e()),
              $i(this.relativeTargetOrigin, this.layout.layoutBox, m.layout.layoutBox),
              xt(this.relativeTarget, this.relativeTargetOrigin))
            : (this.relativeParent = this.relativeTarget = void 0);
        }
        if (!(!this.relativeTarget && !this.targetDelta)) {
          if (
            (this.target || ((this.target = _e()), (this.targetWithTransforms = _e())),
            this.relativeTarget &&
            this.relativeTargetOrigin &&
            this.relativeParent &&
            this.relativeParent.target
              ? (this.forceRelativeParentToResolveTarget(),
                DA(this.target, this.relativeTarget, this.relativeParent.target))
              : this.targetDelta
                ? (this.resumingFrom
                    ? (this.target = this.applyTransform(this.layout.layoutBox))
                    : xt(this.target, this.layout.layoutBox),
                  iS(this.target, this.targetDelta))
                : xt(this.target, this.layout.layoutBox),
            this.attemptToResolveRelativeTarget)
          ) {
            this.attemptToResolveRelativeTarget = !1;
            const m = this.getClosestProjectingParent();
            m &&
            !!m.resumingFrom == !!this.resumingFrom &&
            !m.options.layoutScroll &&
            m.target &&
            this.animationProgress !== 1
              ? ((this.relativeParent = m),
                this.forceRelativeParentToResolveTarget(),
                (this.relativeTarget = _e()),
                (this.relativeTargetOrigin = _e()),
                $i(this.relativeTargetOrigin, this.target, m.target),
                xt(this.relativeTarget, this.relativeTargetOrigin))
              : (this.relativeParent = this.relativeTarget = void 0);
          }
          Ci && pr.resolvedTargetDeltas++;
        }
      }
    }
    getClosestProjectingParent() {
      if (!(!this.parent || Wf(this.parent.latestValues) || oS(this.parent.latestValues)))
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
        this.resolvedRelativeTargetAt === Ie.timestamp && (u = !1),
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
      xt(this.layoutCorrected, this.layout.layoutBox);
      const d = this.treeScale.x,
        m = this.treeScale.y;
      BA(this.layoutCorrected, this.treeScale, this.path, l),
        a.layout &&
          !a.target &&
          (this.treeScale.x !== 1 || this.treeScale.y !== 1) &&
          ((a.target = a.layout.layoutBox), (a.targetWithTransforms = _e()));
      const { target: y } = a;
      if (!y) {
        this.prevProjectionDelta && (this.createProjectionDeltas(), this.scheduleRender());
        return;
      }
      !this.projectionDelta || !this.prevProjectionDelta
        ? this.createProjectionDeltas()
        : ($g(this.prevProjectionDelta.x, this.projectionDelta.x),
          $g(this.prevProjectionDelta.y, this.projectionDelta.y)),
        zi(this.projectionDelta, this.layoutCorrected, y, this.latestValues),
        (this.treeScale.x !== d ||
          this.treeScale.y !== m ||
          !Xg(this.projectionDelta.x, this.prevProjectionDelta.x) ||
          !Xg(this.projectionDelta.y, this.prevProjectionDelta.y)) &&
          ((this.hasProjected = !0),
          this.scheduleRender(),
          this.notifyListeners("projectionUpdate", y)),
        Ci && pr.recalculatedProjection++;
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
      (this.prevProjectionDelta = ho()),
        (this.projectionDelta = ho()),
        (this.projectionDeltaWithTransform = ho());
    }
    setAnimationOrigin(s, a = !1) {
      const l = this.snapshot,
        u = l ? l.latestValues : {},
        c = { ...this.latestValues },
        f = ho();
      (!this.relativeParent || !this.relativeParent.options.layoutRoot) &&
        (this.relativeTarget = this.relativeTargetOrigin = void 0),
        (this.attemptToResolveRelativeTarget = !a);
      const d = _e(),
        m = l ? l.source : void 0,
        y = this.layout ? this.layout.source : void 0,
        g = m !== y,
        w = this.getStack(),
        h = !w || w.members.length <= 1,
        p = !!(g && !h && this.options.crossfade === !0 && !this.path.some(_R));
      this.animationProgress = 0;
      let x;
      (this.mixTargetDelta = (S) => {
        const E = S / 1e3;
        Jg(f.x, s.x, E),
          Jg(f.y, s.y, E),
          this.setTargetDelta(f),
          this.relativeTarget &&
            this.relativeTargetOrigin &&
            this.layout &&
            this.relativeParent &&
            this.relativeParent.layout &&
            ($i(d, this.layout.layoutBox, this.relativeParent.layout.layoutBox),
            TR(this.relativeTarget, this.relativeTargetOrigin, d, E),
            x && cR(this.relativeTarget, x) && (this.isProjectionDirty = !1),
            x || (x = _e()),
            xt(x, this.relativeTarget)),
          g && ((this.animationValues = c), oR(c, u, this.latestValues, E, p, h)),
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
        this.pendingAnimation && (En(this.pendingAnimation), (this.pendingAnimation = void 0)),
        (this.pendingAnimation = ce.update(() => {
          (za.hasAnimatedSinceResize = !0),
            (this.currentAnimation = qA(0, Zg, {
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
        (this.mixTargetDelta && this.mixTargetDelta(Zg), this.currentAnimation.stop()),
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
          mS(this.options.animationType, this.layout.layoutBox, u.layoutBox)
        ) {
          l = this.target || _e();
          const f = mt(this.layout.layoutBox.x);
          (l.x.min = s.target.x.min), (l.x.max = l.x.min + f);
          const d = mt(this.layout.layoutBox.y);
          (l.y.min = s.target.y.min), (l.y.max = l.y.min + d);
        }
        xt(a, l), mo(a, c), zi(this.projectionDeltaWithTransform, this.layoutCorrected, a, c);
      }
    }
    registerSharedNode(s, a) {
      this.sharedNodes.has(s) || this.sharedNodes.set(s, new fR()), this.sharedNodes.get(s).add(a);
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
      l.z && Sc("z", s, u, this.animationValues);
      for (let c = 0; c < wc.length; c++)
        Sc(`rotate${wc[c]}`, s, u, this.animationValues),
          Sc(`skew${wc[c]}`, s, u, this.animationValues);
      s.render();
      for (const c in u)
        s.setStaticValue(c, u[c]), this.animationValues && (this.animationValues[c] = u[c]);
      s.scheduleRender();
    }
    getProjectionStyles(s) {
      var a, l;
      if (!this.instance || this.isSVG) return;
      if (!this.isVisible) return hR;
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
        const g = {};
        return (
          this.options.layoutId &&
            ((g.opacity = this.latestValues.opacity !== void 0 ? this.latestValues.opacity : 1),
            (g.pointerEvents = ja(s == null ? void 0 : s.pointerEvents) || "")),
          this.hasProjected &&
            !hr(this.latestValues) &&
            ((g.transform = c ? c({}, "") : "none"), (this.hasProjected = !1)),
          g
        );
      }
      const d = f.animationValues || f.latestValues;
      this.applyTransformsToTarget(),
        (u.transform = dR(this.projectionDeltaWithTransform, this.treeScale, d)),
        c && (u.transform = c(d, u.transform));
      const { x: m, y } = this.projectionDelta;
      (u.transformOrigin = `${m.origin * 100}% ${y.origin * 100}% 0`),
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
      for (const g in wl) {
        if (d[g] === void 0) continue;
        const { correct: w, applyTo: h } = wl[g],
          p = u.transform === "none" ? d[g] : w(d[g], f);
        if (h) {
          const x = h.length;
          for (let S = 0; S < x; S++) u[h[S]] = p;
        } else u[g] = p;
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
        this.root.nodes.forEach(Qg),
        this.root.sharedNodes.clear();
    }
  };
}
function mR(e) {
  e.updateLayout();
}
function gR(e) {
  var t;
  const n = ((t = e.resumeFrom) === null || t === void 0 ? void 0 : t.snapshot) || e.snapshot;
  if (e.isLead() && e.layout && n && e.hasListeners("didUpdate")) {
    const { layoutBox: r, measuredBox: o } = e.layout,
      { animationType: i } = e.options,
      s = n.source !== e.layout.source;
    i === "size"
      ? wt((f) => {
          const d = s ? n.measuredBox[f] : n.layoutBox[f],
            m = mt(d);
          (d.min = r[f].min), (d.max = d.min + m);
        })
      : mS(i, n.layoutBox, r) &&
        wt((f) => {
          const d = s ? n.measuredBox[f] : n.layoutBox[f],
            m = mt(r[f]);
          (d.max = d.min + m),
            e.relativeTarget &&
              !e.currentAnimation &&
              ((e.isProjectionDirty = !0), (e.relativeTarget[f].max = e.relativeTarget[f].min + m));
        });
    const a = ho();
    zi(a, r, n.layoutBox);
    const l = ho();
    s ? zi(l, e.applyTransform(o, !0), n.measuredBox) : zi(l, r, n.layoutBox);
    const u = !fS(a);
    let c = !1;
    if (!e.resumeFrom) {
      const f = e.getClosestProjectingParent();
      if (f && !f.resumeFrom) {
        const { snapshot: d, layout: m } = f;
        if (d && m) {
          const y = _e();
          $i(y, n.layoutBox, d.layoutBox);
          const g = _e();
          $i(g, r, m.layoutBox),
            dS(y, g) || (c = !0),
            f.options.layoutRoot &&
              ((e.relativeTarget = g), (e.relativeTargetOrigin = y), (e.relativeParent = f));
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
function yR(e) {
  Ci && pr.totalNodes++,
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
function vR(e) {
  e.isProjectionDirty = e.isSharedProjectionDirty = e.isTransformDirty = !1;
}
function xR(e) {
  e.clearSnapshot();
}
function Qg(e) {
  e.clearMeasurements();
}
function wR(e) {
  e.isLayoutDirty = !1;
}
function SR(e) {
  const { visualElement: t } = e.options;
  t && t.getProps().onBeforeLayoutMeasure && t.notify("BeforeLayoutMeasure"), e.resetTransform();
}
function qg(e) {
  e.finishAnimation(),
    (e.targetDelta = e.relativeTarget = e.target = void 0),
    (e.isProjectionDirty = !0);
}
function ER(e) {
  e.resolveTargetDelta();
}
function CR(e) {
  e.calcProjection();
}
function bR(e) {
  e.resetSkewAndRotation();
}
function kR(e) {
  e.removeLeadSnapshot();
}
function Jg(e, t, n) {
  (e.translate = we(t.translate, 0, n)),
    (e.scale = we(t.scale, 1, n)),
    (e.origin = t.origin),
    (e.originPoint = t.originPoint);
}
function ey(e, t, n, r) {
  (e.min = we(t.min, n.min, r)), (e.max = we(t.max, n.max, r));
}
function TR(e, t, n, r) {
  ey(e.x, t.x, n.x, r), ey(e.y, t.y, n.y, r);
}
function _R(e) {
  return e.animationValues && e.animationValues.opacityExit !== void 0;
}
const NR = { duration: 0.45, ease: [0.4, 0, 0.1, 1] },
  ty = (e) =>
    typeof navigator < "u" && navigator.userAgent && navigator.userAgent.toLowerCase().includes(e),
  ny = ty("applewebkit/") && !ty("chrome/") ? Math.round : ht;
function ry(e) {
  (e.min = ny(e.min)), (e.max = ny(e.max));
}
function PR(e) {
  ry(e.x), ry(e.y);
}
function mS(e, t, n) {
  return e === "position" || (e === "preserve-aspect" && !RA(Yg(t), Yg(n), 0.2));
}
function MR(e) {
  var t;
  return e !== e.root && ((t = e.scroll) === null || t === void 0 ? void 0 : t.wasRoot);
}
const AR = pS({
    attachResizeListener: (e, t) => fs(e, "resize", t),
    measureScroll: () => ({
      x: document.documentElement.scrollLeft || document.body.scrollLeft,
      y: document.documentElement.scrollTop || document.body.scrollTop,
    }),
    checkIsScrollRoot: () => !0,
  }),
  Ec = { current: void 0 },
  gS = pS({
    measureScroll: (e) => ({ x: e.scrollLeft, y: e.scrollTop }),
    defaultParent: () => {
      if (!Ec.current) {
        const e = new AR({});
        e.mount(window), e.setOptions({ layoutScroll: !0 }), (Ec.current = e);
      }
      return Ec.current;
    },
    resetTransform: (e, t) => {
      e.style.transform = t !== void 0 ? t : "none";
    },
    checkIsScrollRoot: (e) => window.getComputedStyle(e).position === "fixed",
  }),
  RR = { pan: { Feature: YA }, drag: { Feature: KA, ProjectionNode: gS, MeasureLayout: lS } };
function oy(e, t, n) {
  const { props: r } = e;
  e.animationState && r.whileHover && e.animationState.setActive("whileHover", n === "Start");
  const o = "onHover" + n,
    i = r[o];
  i && ce.postRender(() => i(t, Vs(t)));
}
class DR extends rr {
  mount() {
    const { current: t } = this.node;
    t && (this.unmount = RP(t, (n) => (oy(this.node, n, "Start"), (r) => oy(this.node, r, "End"))));
  }
  unmount() {}
}
class IR extends rr {
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
    this.unmount = Ls(
      fs(this.node.current, "focus", () => this.onFocus()),
      fs(this.node.current, "blur", () => this.onBlur()),
    );
  }
  unmount() {}
}
function iy(e, t, n) {
  const { props: r } = e;
  e.animationState && r.whileTap && e.animationState.setActive("whileTap", n === "Start");
  const o = "onTap" + (n === "End" ? "" : n),
    i = r[o];
  i && ce.postRender(() => i(t, Vs(t)));
}
class LR extends rr {
  mount() {
    const { current: t } = this.node;
    t &&
      (this.unmount = VP(
        t,
        (n) => (
          iy(this.node, n, "Start"), (r, { success: o }) => iy(this.node, r, o ? "End" : "Cancel")
        ),
        { useGlobalTarget: this.node.props.globalTapTarget },
      ));
  }
  unmount() {}
}
const Kf = new WeakMap(),
  Cc = new WeakMap(),
  VR = (e) => {
    const t = Kf.get(e.target);
    t && t(e);
  },
  OR = (e) => {
    e.forEach(VR);
  };
function jR({ root: e, ...t }) {
  const n = e || document;
  Cc.has(n) || Cc.set(n, {});
  const r = Cc.get(n),
    o = JSON.stringify(t);
  return r[o] || (r[o] = new IntersectionObserver(OR, { root: e, ...t })), r[o];
}
function FR(e, t, n) {
  const r = jR(t);
  return (
    Kf.set(e, n),
    r.observe(e),
    () => {
      Kf.delete(e), r.unobserve(e);
    }
  );
}
const zR = { some: 0, all: 1 };
class $R extends rr {
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
        threshold: typeof o == "number" ? o : zR[o],
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
    return FR(this.node.current, s, a);
  }
  mount() {
    this.startObserver();
  }
  update() {
    if (typeof IntersectionObserver > "u") return;
    const { props: t, prevProps: n } = this.node;
    ["amount", "margin", "root"].some(BR(t, n)) && this.startObserver();
  }
  unmount() {}
}
function BR({ viewport: e = {} }, { viewport: t = {} } = {}) {
  return (n) => e[n] !== t[n];
}
const HR = {
    inView: { Feature: $R },
    tap: { Feature: LR },
    focus: { Feature: IR },
    hover: { Feature: DR },
  },
  UR = { layout: { ProjectionNode: gS, MeasureLayout: lS } },
  Yf = { current: null },
  yS = { current: !1 };
function WR() {
  if (((yS.current = !0), !!vh))
    if (window.matchMedia) {
      const e = window.matchMedia("(prefers-reduced-motion)"),
        t = () => (Yf.current = e.matches);
      e.addListener(t), t();
    } else Yf.current = !1;
}
const GR = [...$1, Ye, Jn],
  KR = (e) => GR.find(z1(e)),
  sy = new WeakMap();
function YR(e, t, n) {
  for (const r in t) {
    const o = t[r],
      i = n[r];
    if (Ve(o)) e.addValue(r, o);
    else if (Ve(i)) e.addValue(r, zo(o, { owner: e }));
    else if (i !== o)
      if (e.hasValue(r)) {
        const s = e.getValue(r);
        s.liveStyle === !0 ? s.jump(o) : s.hasAnimated || s.set(o);
      } else {
        const s = e.getStaticValue(r);
        e.addValue(r, zo(s !== void 0 ? s : o, { owner: e }));
      }
  }
  for (const r in n) t[r] === void 0 && e.removeValue(r);
  return t;
}
const ay = [
  "AnimationStart",
  "AnimationComplete",
  "Update",
  "BeforeLayoutMeasure",
  "LayoutMeasure",
  "LayoutAnimationStart",
  "LayoutAnimationComplete",
];
class XR {
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
      (this.KeyframeResolver = Gh),
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
        const m = qt.now();
        this.renderScheduledAt < m &&
          ((this.renderScheduledAt = m), ce.render(this.render, !1, !0));
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
      (this.isControllingVariants = pu(n)),
      (this.isVariantNode = Xw(n)),
      this.isVariantNode && (this.variantChildren = new Set()),
      (this.manuallyAnimateOnMount = !!(t && t.current));
    const { willChange: f, ...d } = this.scrapeMotionValuesFromProps(n, {}, this);
    for (const m in d) {
      const y = d[m];
      l[m] !== void 0 && Ve(y) && y.set(l[m], !1);
    }
  }
  mount(t) {
    (this.current = t),
      sy.set(t, this),
      this.projection && !this.projection.instance && this.projection.mount(t),
      this.parent &&
        this.isVariantNode &&
        !this.isControllingVariants &&
        (this.removeFromVariantTree = this.parent.addVariantChild(this)),
      this.values.forEach((n, r) => this.bindToMotionValue(r, n)),
      yS.current || WR(),
      (this.shouldReduceMotion =
        this.reducedMotionConfig === "never"
          ? !1
          : this.reducedMotionConfig === "always"
            ? !0
            : Yf.current),
      this.parent && this.parent.children.add(this),
      this.update(this.props, this.presenceContext);
  }
  unmount() {
    sy.delete(this.current),
      this.projection && this.projection.unmount(),
      En(this.notifyUpdate),
      En(this.render),
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
    const r = jr.has(t),
      o = n.on("change", (a) => {
        (this.latestValues[t] = a),
          this.props.onUpdate && ce.preRender(this.notifyUpdate),
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
    for (t in Fo) {
      const n = Fo[t];
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
    return this.current ? this.measureInstanceViewportBox(this.current, this.props) : _e();
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
    for (let r = 0; r < ay.length; r++) {
      const o = ay[r];
      this.propEventSubscriptions[o] &&
        (this.propEventSubscriptions[o](), delete this.propEventSubscriptions[o]);
      const i = "on" + o,
        s = t[i];
      s && (this.propEventSubscriptions[o] = this.on(o, s));
    }
    (this.prevMotionValues = YR(
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
        ((r = zo(n === null ? void 0 : n, { owner: this })), this.addValue(t, r)),
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
        (typeof o == "string" && (j1(o) || P1(o))
          ? (o = parseFloat(o))
          : !KR(o) && Jn.test(n) && (o = L1(t, n)),
        this.setBaseTarget(t, Ve(o) ? o.get() : o)),
      Ve(o) ? o.get() : o
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
      const s = Th(
        this.props,
        r,
        (n = this.presenceContext) === null || n === void 0 ? void 0 : n.custom,
      );
      s && (o = s[t]);
    }
    if (r && o !== void 0) return o;
    const i = this.getBaseTargetFromProps(this.props, t);
    return i !== void 0 && !Ve(i)
      ? i
      : this.initialValues[t] !== void 0 && o === void 0
        ? void 0
        : this.baseTarget[t];
  }
  on(t, n) {
    return this.events[t] || (this.events[t] = new zh()), this.events[t].add(n);
  }
  notify(t, ...n) {
    this.events[t] && this.events[t].notify(...n);
  }
}
class vS extends XR {
  constructor() {
    super(...arguments), (this.KeyframeResolver = B1);
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
    Ve(t) &&
      (this.childSubscription = t.on("change", (n) => {
        this.current && (this.current.textContent = `${n}`);
      }));
  }
}
function ZR(e) {
  return window.getComputedStyle(e);
}
class QR extends vS {
  constructor() {
    super(...arguments), (this.type = "html"), (this.renderInstance = o1);
  }
  readValueFromInstance(t, n) {
    if (jr.has(n)) {
      const r = Wh(n);
      return (r && r.default) || 0;
    } else {
      const r = ZR(t),
        o = (t1(n) ? r.getPropertyValue(n) : r[n]) || 0;
      return typeof o == "string" ? o.trim() : o;
    }
  }
  measureInstanceViewportBox(t, { transformPagePoint: n }) {
    return sS(t, n);
  }
  build(t, n, r) {
    Ph(t, n, r.transformTemplate);
  }
  scrapeMotionValuesFromProps(t, n, r) {
    return Dh(t, n, r);
  }
}
class qR extends vS {
  constructor() {
    super(...arguments),
      (this.type = "svg"),
      (this.isSVGTag = !1),
      (this.measureInstanceViewportBox = _e);
  }
  getBaseTargetFromProps(t, n) {
    return t[n];
  }
  readValueFromInstance(t, n) {
    if (jr.has(n)) {
      const r = Wh(n);
      return (r && r.default) || 0;
    }
    return (n = i1.has(n) ? n : Ch(n)), t.getAttribute(n);
  }
  scrapeMotionValuesFromProps(t, n, r) {
    return l1(t, n, r);
  }
  build(t, n, r) {
    Mh(t, n, this.isSVGTag, r.transformTemplate);
  }
  renderInstance(t, n, r, o) {
    s1(t, n, r, o);
  }
  mount(t) {
    (this.isSVGTag = Rh(t.tagName)), super.mount(t);
  }
}
const JR = (e, t) => (kh(e) ? new qR(t) : new QR(t, { allowProjection: e !== v.Fragment })),
  eD = kP({ ...CA, ...HR, ...RR, ...UR }, JR),
  xS = zN(eD);
function Xh(e) {
  const t = gh(() => zo(e)),
    { isStatic: n } = v.useContext(fu);
  if (n) {
    const [, r] = v.useState(e);
    v.useEffect(() => t.on("change", r), []);
  }
  return t;
}
function wS(e, t) {
  const n = Xh(t()),
    r = () => n.set(t());
  return (
    r(),
    xh(() => {
      const o = () => ce.preRender(r, !1, !0),
        i = e.map((s) => s.on("change", o));
      return () => {
        i.forEach((s) => s()), En(r);
      };
    }),
    n
  );
}
function ly(e) {
  return typeof e == "number" ? e : parseFloat(e);
}
function tD(e, t = {}) {
  const { isStatic: n } = v.useContext(fu),
    r = v.useRef(null),
    o = Xh(Ve(e) ? ly(e.get()) : e),
    i = v.useRef(o.get()),
    s = v.useRef(() => {}),
    a = () => {
      const u = r.current;
      u && u.time === 0 && u.sample(Ie.delta),
        l(),
        (r.current = ZM({
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
          (u, c) => (n ? c(u) : ((i.current = u), (s.current = c), ce.update(a), o.get())),
          l,
        ),
      [JSON.stringify(t)],
    ),
    xh(() => {
      if (Ve(e)) return e.on("change", (u) => o.set(ly(u)));
    }, [o]),
    o
  );
}
const nD = (e) => e && typeof e == "object" && e.mix,
  rD = (e) => (nD(e) ? e.mix : void 0);
function oD(...e) {
  const t = !Array.isArray(e[0]),
    n = t ? 0 : -1,
    r = e[0 + n],
    o = e[1 + n],
    i = e[2 + n],
    s = e[3 + n],
    a = X1(o, i, { mixer: rD(i[0]), ...s });
  return t ? a(r) : a;
}
function iD(e) {
  (Oi.current = []), e();
  const t = wS(Oi.current, e);
  return (Oi.current = void 0), t;
}
function uy(e, t, n, r) {
  if (typeof e == "function") return iD(e);
  const o = typeof t == "function" ? t : oD(t, n, r);
  return Array.isArray(e) ? cy(e, o) : cy([e], ([i]) => o(i));
}
function cy(e, t) {
  const n = gh(() => []);
  return wS(e, () => {
    n.length = 0;
    const r = e.length;
    for (let o = 0; o < r; o++) n[o] = e[o].get();
    return t(n);
  });
}
const sD = Nx(
    "flex h-full w-max items-end gap-2 rounded-lg p-2 transition-all duration-300 ease-out",
  ),
  SS = L.forwardRef(({ className: e, children: t, ...n }, r) => {
    const o = Xh(1 / 0);
    return C.jsx(xS.div, {
      ref: r,
      onMouseMove: (i) => o.set(i.pageX),
      onMouseLeave: () => o.set(1 / 0),
      ...n,
      className: se(sD({ className: e }), "z-50"),
      children: L.Children.map(t, (i) => L.cloneElement(i, { mouseX: o })),
    });
  });
SS.displayName = "Dock";
const $a = ({ mouseX: e, className: t, children: n, ...r }) => {
  const o = v.useRef(null),
    i = uy(e, (l) => {
      var c;
      const u = ((c = o.current) == null ? void 0 : c.getBoundingClientRect()) ?? {
        x: 0,
        width: 0,
      };
      return l - u.x - u.width / 2;
    }),
    s = uy(i, [-150, 0, 150], [40, 80, 40]),
    a = tD(s, { mass: 0.1, stiffness: 150, damping: 12 });
  return C.jsx(xS.div, {
    ref: o,
    style: { width: a },
    className: se(
      "flex aspect-square items-center justify-center rounded-full bg-neutral-100/50 dark:bg-neutral-800/50",
      t,
    ),
    ...r,
    children: n,
  });
};
$a.displayName = "DockIcon";
const ES = L.forwardRef(
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
    C.jsxs("button", {
      style: {
        "--shimmer-color": e,
        "--shimmer-size": t,
        "--shimmer-duration": n,
        "--background": o,
        borderRadius: r,
      },
      className: se(
        "group relative z-0 flex cursor-pointer items-center justify-center overflow-hidden whitespace-nowrap border border-white/10 px-6 py-3 text-white [background:var(--background)] [border-radius:var(--border-radius)]",
        "transform-gpu transition-transform duration-300 ease-in-out hover:scale-105",
        i,
      ),
      ref: l,
      ...a,
      children: [
        C.jsx("div", {
          className: "absolute inset-0 z-0 overflow-hidden rounded-[inherit]",
          children: C.jsx("div", {
            className: se(
              "absolute inset-0 z-0 h-full w-full animate-[shimmer_var(--shimmer-duration)_infinite] bg-gradient-to-r from-transparent via-transparent to-[var(--shimmer-color)] opacity-0 transition-opacity duration-500 group-hover:opacity-100",
              "[--shimmer-angle:-45deg]",
            ),
          }),
        }),
        C.jsx("div", { className: "relative z-10", children: s }),
      ],
    }),
);
ES.displayName = "ShimmerButton";
function He(e) {
  if (typeof e == "string" || typeof e == "number") return "" + e;
  let t = "";
  if (Array.isArray(e))
    for (let n = 0, r; n < e.length; n++) (r = He(e[n])) !== "" && (t += (t && " ") + r);
  else for (let n in e) e[n] && (t += (t && " ") + n);
  return t;
}
const { useDebugValue: aD } = L,
  { useSyncExternalStoreWithSelector: lD } = Ex,
  uD = (e) => e;
function CS(e, t = uD, n) {
  const r = lD(e.subscribe, e.getState, e.getServerState || e.getInitialState, t, n);
  return aD(r), r;
}
const fy = (e, t) => {
    const n = yx(e),
      r = (o, i = t) => CS(n, o, i);
    return Object.assign(r, n), r;
  },
  cD = (e, t) => (e ? fy(e, t) : fy);
function je(e, t) {
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
var fD = { value: () => {} };
function vu() {
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
function dD(e, t) {
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
Ba.prototype = vu.prototype = {
  constructor: Ba,
  on: function (e, t) {
    var n = this._,
      r = dD(e + "", n),
      o,
      i = -1,
      s = r.length;
    if (arguments.length < 2) {
      for (; ++i < s; ) if ((o = (e = r[i]).type) && (o = hD(n[o], e.name))) return o;
      return;
    }
    if (t != null && typeof t != "function") throw new Error("invalid callback: " + t);
    for (; ++i < s; )
      if ((o = (e = r[i]).type)) n[o] = dy(n[o], e.name, t);
      else if (t == null) for (o in n) n[o] = dy(n[o], e.name, null);
    return this;
  },
  copy: function () {
    var e = {},
      t = this._;
    for (var n in t) e[n] = t[n].slice();
    return new Ba(e);
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
function hD(e, t) {
  for (var n = 0, r = e.length, o; n < r; ++n) if ((o = e[n]).name === t) return o.value;
}
function dy(e, t, n) {
  for (var r = 0, o = e.length; r < o; ++r)
    if (e[r].name === t) {
      (e[r] = fD), (e = e.slice(0, r).concat(e.slice(r + 1)));
      break;
    }
  return n != null && e.push({ name: t, value: n }), e;
}
var Xf = "http://www.w3.org/1999/xhtml";
const hy = {
  svg: "http://www.w3.org/2000/svg",
  xhtml: Xf,
  xlink: "http://www.w3.org/1999/xlink",
  xml: "http://www.w3.org/XML/1998/namespace",
  xmlns: "http://www.w3.org/2000/xmlns/",
};
function xu(e) {
  var t = (e += ""),
    n = t.indexOf(":");
  return (
    n >= 0 && (t = e.slice(0, n)) !== "xmlns" && (e = e.slice(n + 1)),
    hy.hasOwnProperty(t) ? { space: hy[t], local: e } : e
  );
}
function pD(e) {
  return function () {
    var t = this.ownerDocument,
      n = this.namespaceURI;
    return n === Xf && t.documentElement.namespaceURI === Xf
      ? t.createElement(e)
      : t.createElementNS(n, e);
  };
}
function mD(e) {
  return function () {
    return this.ownerDocument.createElementNS(e.space, e.local);
  };
}
function bS(e) {
  var t = xu(e);
  return (t.local ? mD : pD)(t);
}
function gD() {}
function Zh(e) {
  return e == null
    ? gD
    : function () {
        return this.querySelector(e);
      };
}
function yD(e) {
  typeof e != "function" && (e = Zh(e));
  for (var t = this._groups, n = t.length, r = new Array(n), o = 0; o < n; ++o)
    for (var i = t[o], s = i.length, a = (r[o] = new Array(s)), l, u, c = 0; c < s; ++c)
      (l = i[c]) &&
        (u = e.call(l, l.__data__, c, i)) &&
        ("__data__" in l && (u.__data__ = l.__data__), (a[c] = u));
  return new gt(r, this._parents);
}
function vD(e) {
  return e == null ? [] : Array.isArray(e) ? e : Array.from(e);
}
function xD() {
  return [];
}
function kS(e) {
  return e == null
    ? xD
    : function () {
        return this.querySelectorAll(e);
      };
}
function wD(e) {
  return function () {
    return vD(e.apply(this, arguments));
  };
}
function SD(e) {
  typeof e == "function" ? (e = wD(e)) : (e = kS(e));
  for (var t = this._groups, n = t.length, r = [], o = [], i = 0; i < n; ++i)
    for (var s = t[i], a = s.length, l, u = 0; u < a; ++u)
      (l = s[u]) && (r.push(e.call(l, l.__data__, u, s)), o.push(l));
  return new gt(r, o);
}
function TS(e) {
  return function () {
    return this.matches(e);
  };
}
function _S(e) {
  return function (t) {
    return t.matches(e);
  };
}
var ED = Array.prototype.find;
function CD(e) {
  return function () {
    return ED.call(this.children, e);
  };
}
function bD() {
  return this.firstElementChild;
}
function kD(e) {
  return this.select(e == null ? bD : CD(typeof e == "function" ? e : _S(e)));
}
var TD = Array.prototype.filter;
function _D() {
  return Array.from(this.children);
}
function ND(e) {
  return function () {
    return TD.call(this.children, e);
  };
}
function PD(e) {
  return this.selectAll(e == null ? _D : ND(typeof e == "function" ? e : _S(e)));
}
function MD(e) {
  typeof e != "function" && (e = TS(e));
  for (var t = this._groups, n = t.length, r = new Array(n), o = 0; o < n; ++o)
    for (var i = t[o], s = i.length, a = (r[o] = []), l, u = 0; u < s; ++u)
      (l = i[u]) && e.call(l, l.__data__, u, i) && a.push(l);
  return new gt(r, this._parents);
}
function NS(e) {
  return new Array(e.length);
}
function AD() {
  return new gt(this._enter || this._groups.map(NS), this._parents);
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
function RD(e) {
  return function () {
    return e;
  };
}
function DD(e, t, n, r, o, i) {
  for (var s = 0, a, l = t.length, u = i.length; s < u; ++s)
    (a = t[s]) ? ((a.__data__ = i[s]), (r[s] = a)) : (n[s] = new Tl(e, i[s]));
  for (; s < l; ++s) (a = t[s]) && (o[s] = a);
}
function ID(e, t, n, r, o, i, s) {
  var a,
    l,
    u = new Map(),
    c = t.length,
    f = i.length,
    d = new Array(c),
    m;
  for (a = 0; a < c; ++a)
    (l = t[a]) &&
      ((d[a] = m = s.call(l, l.__data__, a, t) + ""), u.has(m) ? (o[a] = l) : u.set(m, l));
  for (a = 0; a < f; ++a)
    (m = s.call(e, i[a], a, i) + ""),
      (l = u.get(m)) ? ((r[a] = l), (l.__data__ = i[a]), u.delete(m)) : (n[a] = new Tl(e, i[a]));
  for (a = 0; a < c; ++a) (l = t[a]) && u.get(d[a]) === l && (o[a] = l);
}
function LD(e) {
  return e.__data__;
}
function VD(e, t) {
  if (!arguments.length) return Array.from(this, LD);
  var n = t ? ID : DD,
    r = this._parents,
    o = this._groups;
  typeof e != "function" && (e = RD(e));
  for (var i = o.length, s = new Array(i), a = new Array(i), l = new Array(i), u = 0; u < i; ++u) {
    var c = r[u],
      f = o[u],
      d = f.length,
      m = OD(e.call(c, c && c.__data__, u, r)),
      y = m.length,
      g = (a[u] = new Array(y)),
      w = (s[u] = new Array(y)),
      h = (l[u] = new Array(d));
    n(c, f, g, w, h, m, t);
    for (var p = 0, x = 0, S, E; p < y; ++p)
      if ((S = g[p])) {
        for (p >= x && (x = p + 1); !(E = w[x]) && ++x < y; );
        S._next = E || null;
      }
  }
  return (s = new gt(s, r)), (s._enter = a), (s._exit = l), s;
}
function OD(e) {
  return typeof e == "object" && "length" in e ? e : Array.from(e);
}
function jD() {
  return new gt(this._exit || this._groups.map(NS), this._parents);
}
function FD(e, t, n) {
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
function zD(e) {
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
    for (var u = n[l], c = r[l], f = u.length, d = (a[l] = new Array(f)), m, y = 0; y < f; ++y)
      (m = u[y] || c[y]) && (d[y] = m);
  for (; l < o; ++l) a[l] = n[l];
  return new gt(a, this._parents);
}
function $D() {
  for (var e = this._groups, t = -1, n = e.length; ++t < n; )
    for (var r = e[t], o = r.length - 1, i = r[o], s; --o >= 0; )
      (s = r[o]) &&
        (i && s.compareDocumentPosition(i) ^ 4 && i.parentNode.insertBefore(s, i), (i = s));
  return this;
}
function BD(e) {
  e || (e = HD);
  function t(f, d) {
    return f && d ? e(f.__data__, d.__data__) : !f - !d;
  }
  for (var n = this._groups, r = n.length, o = new Array(r), i = 0; i < r; ++i) {
    for (var s = n[i], a = s.length, l = (o[i] = new Array(a)), u, c = 0; c < a; ++c)
      (u = s[c]) && (l[c] = u);
    l.sort(t);
  }
  return new gt(o, this._parents).order();
}
function HD(e, t) {
  return e < t ? -1 : e > t ? 1 : e >= t ? 0 : NaN;
}
function UD() {
  var e = arguments[0];
  return (arguments[0] = this), e.apply(null, arguments), this;
}
function WD() {
  return Array.from(this);
}
function GD() {
  for (var e = this._groups, t = 0, n = e.length; t < n; ++t)
    for (var r = e[t], o = 0, i = r.length; o < i; ++o) {
      var s = r[o];
      if (s) return s;
    }
  return null;
}
function KD() {
  let e = 0;
  for (const t of this) ++e;
  return e;
}
function YD() {
  return !this.node();
}
function XD(e) {
  for (var t = this._groups, n = 0, r = t.length; n < r; ++n)
    for (var o = t[n], i = 0, s = o.length, a; i < s; ++i)
      (a = o[i]) && e.call(a, a.__data__, i, o);
  return this;
}
function ZD(e) {
  return function () {
    this.removeAttribute(e);
  };
}
function QD(e) {
  return function () {
    this.removeAttributeNS(e.space, e.local);
  };
}
function qD(e, t) {
  return function () {
    this.setAttribute(e, t);
  };
}
function JD(e, t) {
  return function () {
    this.setAttributeNS(e.space, e.local, t);
  };
}
function eI(e, t) {
  return function () {
    var n = t.apply(this, arguments);
    n == null ? this.removeAttribute(e) : this.setAttribute(e, n);
  };
}
function tI(e, t) {
  return function () {
    var n = t.apply(this, arguments);
    n == null ? this.removeAttributeNS(e.space, e.local) : this.setAttributeNS(e.space, e.local, n);
  };
}
function nI(e, t) {
  var n = xu(e);
  if (arguments.length < 2) {
    var r = this.node();
    return n.local ? r.getAttributeNS(n.space, n.local) : r.getAttribute(n);
  }
  return this.each(
    (t == null
      ? n.local
        ? QD
        : ZD
      : typeof t == "function"
        ? n.local
          ? tI
          : eI
        : n.local
          ? JD
          : qD)(n, t),
  );
}
function PS(e) {
  return (e.ownerDocument && e.ownerDocument.defaultView) || (e.document && e) || e.defaultView;
}
function rI(e) {
  return function () {
    this.style.removeProperty(e);
  };
}
function oI(e, t, n) {
  return function () {
    this.style.setProperty(e, t, n);
  };
}
function iI(e, t, n) {
  return function () {
    var r = t.apply(this, arguments);
    r == null ? this.style.removeProperty(e) : this.style.setProperty(e, r, n);
  };
}
function sI(e, t, n) {
  return arguments.length > 1
    ? this.each((t == null ? rI : typeof t == "function" ? iI : oI)(e, t, n ?? ""))
    : Bo(this.node(), e);
}
function Bo(e, t) {
  return e.style.getPropertyValue(t) || PS(e).getComputedStyle(e, null).getPropertyValue(t);
}
function aI(e) {
  return function () {
    delete this[e];
  };
}
function lI(e, t) {
  return function () {
    this[e] = t;
  };
}
function uI(e, t) {
  return function () {
    var n = t.apply(this, arguments);
    n == null ? delete this[e] : (this[e] = n);
  };
}
function cI(e, t) {
  return arguments.length > 1
    ? this.each((t == null ? aI : typeof t == "function" ? uI : lI)(e, t))
    : this.node()[e];
}
function MS(e) {
  return e.trim().split(/^|\s+/);
}
function Qh(e) {
  return e.classList || new AS(e);
}
function AS(e) {
  (this._node = e), (this._names = MS(e.getAttribute("class") || ""));
}
AS.prototype = {
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
function RS(e, t) {
  for (var n = Qh(e), r = -1, o = t.length; ++r < o; ) n.add(t[r]);
}
function DS(e, t) {
  for (var n = Qh(e), r = -1, o = t.length; ++r < o; ) n.remove(t[r]);
}
function fI(e) {
  return function () {
    RS(this, e);
  };
}
function dI(e) {
  return function () {
    DS(this, e);
  };
}
function hI(e, t) {
  return function () {
    (t.apply(this, arguments) ? RS : DS)(this, e);
  };
}
function pI(e, t) {
  var n = MS(e + "");
  if (arguments.length < 2) {
    for (var r = Qh(this.node()), o = -1, i = n.length; ++o < i; ) if (!r.contains(n[o])) return !1;
    return !0;
  }
  return this.each((typeof t == "function" ? hI : t ? fI : dI)(n, t));
}
function mI() {
  this.textContent = "";
}
function gI(e) {
  return function () {
    this.textContent = e;
  };
}
function yI(e) {
  return function () {
    var t = e.apply(this, arguments);
    this.textContent = t ?? "";
  };
}
function vI(e) {
  return arguments.length
    ? this.each(e == null ? mI : (typeof e == "function" ? yI : gI)(e))
    : this.node().textContent;
}
function xI() {
  this.innerHTML = "";
}
function wI(e) {
  return function () {
    this.innerHTML = e;
  };
}
function SI(e) {
  return function () {
    var t = e.apply(this, arguments);
    this.innerHTML = t ?? "";
  };
}
function EI(e) {
  return arguments.length
    ? this.each(e == null ? xI : (typeof e == "function" ? SI : wI)(e))
    : this.node().innerHTML;
}
function CI() {
  this.nextSibling && this.parentNode.appendChild(this);
}
function bI() {
  return this.each(CI);
}
function kI() {
  this.previousSibling && this.parentNode.insertBefore(this, this.parentNode.firstChild);
}
function TI() {
  return this.each(kI);
}
function _I(e) {
  var t = typeof e == "function" ? e : bS(e);
  return this.select(function () {
    return this.appendChild(t.apply(this, arguments));
  });
}
function NI() {
  return null;
}
function PI(e, t) {
  var n = typeof e == "function" ? e : bS(e),
    r = t == null ? NI : typeof t == "function" ? t : Zh(t);
  return this.select(function () {
    return this.insertBefore(n.apply(this, arguments), r.apply(this, arguments) || null);
  });
}
function MI() {
  var e = this.parentNode;
  e && e.removeChild(this);
}
function AI() {
  return this.each(MI);
}
function RI() {
  var e = this.cloneNode(!1),
    t = this.parentNode;
  return t ? t.insertBefore(e, this.nextSibling) : e;
}
function DI() {
  var e = this.cloneNode(!0),
    t = this.parentNode;
  return t ? t.insertBefore(e, this.nextSibling) : e;
}
function II(e) {
  return this.select(e ? DI : RI);
}
function LI(e) {
  return arguments.length ? this.property("__data__", e) : this.node().__data__;
}
function VI(e) {
  return function (t) {
    e.call(this, t, this.__data__);
  };
}
function OI(e) {
  return e
    .trim()
    .split(/^|\s+/)
    .map(function (t) {
      var n = "",
        r = t.indexOf(".");
      return r >= 0 && ((n = t.slice(r + 1)), (t = t.slice(0, r))), { type: t, name: n };
    });
}
function jI(e) {
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
function FI(e, t, n) {
  return function () {
    var r = this.__on,
      o,
      i = VI(t);
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
function zI(e, t, n) {
  var r = OI(e + ""),
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
  for (a = t ? FI : jI, o = 0; o < i; ++o) this.each(a(r[o], t, n));
  return this;
}
function IS(e, t, n) {
  var r = PS(e),
    o = r.CustomEvent;
  typeof o == "function"
    ? (o = new o(t, n))
    : ((o = r.document.createEvent("Event")),
      n
        ? (o.initEvent(t, n.bubbles, n.cancelable), (o.detail = n.detail))
        : o.initEvent(t, !1, !1)),
    e.dispatchEvent(o);
}
function $I(e, t) {
  return function () {
    return IS(this, e, t);
  };
}
function BI(e, t) {
  return function () {
    return IS(this, e, t.apply(this, arguments));
  };
}
function HI(e, t) {
  return this.each((typeof t == "function" ? BI : $I)(e, t));
}
function* UI() {
  for (var e = this._groups, t = 0, n = e.length; t < n; ++t)
    for (var r = e[t], o = 0, i = r.length, s; o < i; ++o) (s = r[o]) && (yield s);
}
var LS = [null];
function gt(e, t) {
  (this._groups = e), (this._parents = t);
}
function Os() {
  return new gt([[document.documentElement]], LS);
}
function WI() {
  return this;
}
gt.prototype = Os.prototype = {
  constructor: gt,
  select: yD,
  selectAll: SD,
  selectChild: kD,
  selectChildren: PD,
  filter: MD,
  data: VD,
  enter: AD,
  exit: jD,
  join: FD,
  merge: zD,
  selection: WI,
  order: $D,
  sort: BD,
  call: UD,
  nodes: WD,
  node: GD,
  size: KD,
  empty: YD,
  each: XD,
  attr: nI,
  style: sI,
  property: cI,
  classed: pI,
  text: vI,
  html: EI,
  raise: bI,
  lower: TI,
  append: _I,
  insert: PI,
  remove: AI,
  clone: II,
  datum: LI,
  on: zI,
  dispatch: HI,
  [Symbol.iterator]: UI,
};
function Ct(e) {
  return typeof e == "string"
    ? new gt([[document.querySelector(e)]], [document.documentElement])
    : new gt([[e]], LS);
}
function GI(e) {
  let t;
  for (; (t = e.sourceEvent); ) e = t;
  return e;
}
function It(e, t) {
  if (((e = GI(e)), t === void 0 && (t = e.currentTarget), t)) {
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
const KI = { passive: !1 },
  ds = { capture: !0, passive: !1 };
function bc(e) {
  e.stopImmediatePropagation();
}
function To(e) {
  e.preventDefault(), e.stopImmediatePropagation();
}
function VS(e) {
  var t = e.document.documentElement,
    n = Ct(e).on("dragstart.drag", To, ds);
  "onselectstart" in t
    ? n.on("selectstart.drag", To, ds)
    : ((t.__noselect = t.style.MozUserSelect), (t.style.MozUserSelect = "none"));
}
function OS(e, t) {
  var n = e.document.documentElement,
    r = Ct(e).on("dragstart.drag", null);
  t &&
    (r.on("click.drag", To, ds),
    setTimeout(function () {
      r.on("click.drag", null);
    }, 0)),
    "onselectstart" in n
      ? r.on("selectstart.drag", null)
      : ((n.style.MozUserSelect = n.__noselect), delete n.__noselect);
}
const fa = (e) => () => e;
function Zf(
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
Zf.prototype.on = function () {
  var e = this._.on.apply(this._, arguments);
  return e === this._ ? this : e;
};
function YI(e) {
  return !e.ctrlKey && !e.button;
}
function XI() {
  return this.parentNode;
}
function ZI(e, t) {
  return t ?? { x: e.x, y: e.y };
}
function QI() {
  return navigator.maxTouchPoints || "ontouchstart" in this;
}
function qI() {
  var e = YI,
    t = XI,
    n = ZI,
    r = QI,
    o = {},
    i = vu("start", "drag", "end"),
    s = 0,
    a,
    l,
    u,
    c,
    f = 0;
  function d(S) {
    S.on("mousedown.drag", m)
      .filter(r)
      .on("touchstart.drag", w)
      .on("touchmove.drag", h, KI)
      .on("touchend.drag touchcancel.drag", p)
      .style("touch-action", "none")
      .style("-webkit-tap-highlight-color", "rgba(0,0,0,0)");
  }
  function m(S, E) {
    if (!(c || !e.call(this, S, E))) {
      var _ = x(this, t.call(this, S, E), S, E, "mouse");
      _ &&
        (Ct(S.view).on("mousemove.drag", y, ds).on("mouseup.drag", g, ds),
        VS(S.view),
        bc(S),
        (u = !1),
        (a = S.clientX),
        (l = S.clientY),
        _("start", S));
    }
  }
  function y(S) {
    if ((To(S), !u)) {
      var E = S.clientX - a,
        _ = S.clientY - l;
      u = E * E + _ * _ > f;
    }
    o.mouse("drag", S);
  }
  function g(S) {
    Ct(S.view).on("mousemove.drag mouseup.drag", null), OS(S.view, u), To(S), o.mouse("end", S);
  }
  function w(S, E) {
    if (e.call(this, S, E)) {
      var _ = S.changedTouches,
        k = t.call(this, S, E),
        N = _.length,
        A,
        R;
      for (A = 0; A < N; ++A)
        (R = x(this, k, S, E, _[A].identifier, _[A])) && (bc(S), R("start", S, _[A]));
    }
  }
  function h(S) {
    var E = S.changedTouches,
      _ = E.length,
      k,
      N;
    for (k = 0; k < _; ++k) (N = o[E[k].identifier]) && (To(S), N("drag", S, E[k]));
  }
  function p(S) {
    var E = S.changedTouches,
      _ = E.length,
      k,
      N;
    for (
      c && clearTimeout(c),
        c = setTimeout(function () {
          c = null;
        }, 500),
        k = 0;
      k < _;
      ++k
    )
      (N = o[E[k].identifier]) && (bc(S), N("end", S, E[k]));
  }
  function x(S, E, _, k, N, A) {
    var R = i.copy(),
      O = It(A || _, E),
      j,
      $,
      b;
    if (
      (b = n.call(
        S,
        new Zf("beforestart", {
          sourceEvent: _,
          target: d,
          identifier: N,
          active: s,
          x: O[0],
          y: O[1],
          dx: 0,
          dy: 0,
          dispatch: R,
        }),
        k,
      )) != null
    )
      return (
        (j = b.x - O[0] || 0),
        ($ = b.y - O[1] || 0),
        function I(P, V, M) {
          var T = O,
            D;
          switch (P) {
            case "start":
              (o[N] = I), (D = s++);
              break;
            case "end":
              delete o[N], --s;
            case "drag":
              (O = It(M || V, E)), (D = s);
              break;
          }
          R.call(
            P,
            S,
            new Zf(P, {
              sourceEvent: V,
              subject: b,
              target: d,
              identifier: N,
              active: D,
              x: O[0] + j,
              y: O[1] + $,
              dx: O[0] - T[0],
              dy: O[1] - T[1],
              dispatch: R,
            }),
            k,
          );
        }
      );
  }
  return (
    (d.filter = function (S) {
      return arguments.length ? ((e = typeof S == "function" ? S : fa(!!S)), d) : e;
    }),
    (d.container = function (S) {
      return arguments.length ? ((t = typeof S == "function" ? S : fa(S)), d) : t;
    }),
    (d.subject = function (S) {
      return arguments.length ? ((n = typeof S == "function" ? S : fa(S)), d) : n;
    }),
    (d.touchable = function (S) {
      return arguments.length ? ((r = typeof S == "function" ? S : fa(!!S)), d) : r;
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
function qh(e, t, n) {
  (e.prototype = t.prototype = n), (n.constructor = e);
}
function jS(e, t) {
  var n = Object.create(e.prototype);
  for (var r in t) n[r] = t[r];
  return n;
}
function js() {}
var hs = 0.7,
  _l = 1 / hs,
  _o = "\\s*([+-]?\\d+)\\s*",
  ps = "\\s*([+-]?(?:\\d*\\.)?\\d+(?:[eE][+-]?\\d+)?)\\s*",
  Jt = "\\s*([+-]?(?:\\d*\\.)?\\d+(?:[eE][+-]?\\d+)?)%\\s*",
  JI = /^#([0-9a-f]{3,8})$/,
  e3 = new RegExp(`^rgb\\(${_o},${_o},${_o}\\)$`),
  t3 = new RegExp(`^rgb\\(${Jt},${Jt},${Jt}\\)$`),
  n3 = new RegExp(`^rgba\\(${_o},${_o},${_o},${ps}\\)$`),
  r3 = new RegExp(`^rgba\\(${Jt},${Jt},${Jt},${ps}\\)$`),
  o3 = new RegExp(`^hsl\\(${ps},${Jt},${Jt}\\)$`),
  i3 = new RegExp(`^hsla\\(${ps},${Jt},${Jt},${ps}\\)$`),
  py = {
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
qh(js, ms, {
  copy(e) {
    return Object.assign(new this.constructor(), this, e);
  },
  displayable() {
    return this.rgb().displayable();
  },
  hex: my,
  formatHex: my,
  formatHex8: s3,
  formatHsl: a3,
  formatRgb: gy,
  toString: gy,
});
function my() {
  return this.rgb().formatHex();
}
function s3() {
  return this.rgb().formatHex8();
}
function a3() {
  return FS(this).formatHsl();
}
function gy() {
  return this.rgb().formatRgb();
}
function ms(e) {
  var t, n;
  return (
    (e = (e + "").trim().toLowerCase()),
    (t = JI.exec(e))
      ? ((n = t[1].length),
        (t = parseInt(t[1], 16)),
        n === 6
          ? yy(t)
          : n === 3
            ? new st(
                ((t >> 8) & 15) | ((t >> 4) & 240),
                ((t >> 4) & 15) | (t & 240),
                ((t & 15) << 4) | (t & 15),
                1,
              )
            : n === 8
              ? da((t >> 24) & 255, (t >> 16) & 255, (t >> 8) & 255, (t & 255) / 255)
              : n === 4
                ? da(
                    ((t >> 12) & 15) | ((t >> 8) & 240),
                    ((t >> 8) & 15) | ((t >> 4) & 240),
                    ((t >> 4) & 15) | (t & 240),
                    (((t & 15) << 4) | (t & 15)) / 255,
                  )
                : null)
      : (t = e3.exec(e))
        ? new st(t[1], t[2], t[3], 1)
        : (t = t3.exec(e))
          ? new st((t[1] * 255) / 100, (t[2] * 255) / 100, (t[3] * 255) / 100, 1)
          : (t = n3.exec(e))
            ? da(t[1], t[2], t[3], t[4])
            : (t = r3.exec(e))
              ? da((t[1] * 255) / 100, (t[2] * 255) / 100, (t[3] * 255) / 100, t[4])
              : (t = o3.exec(e))
                ? wy(t[1], t[2] / 100, t[3] / 100, 1)
                : (t = i3.exec(e))
                  ? wy(t[1], t[2] / 100, t[3] / 100, t[4])
                  : py.hasOwnProperty(e)
                    ? yy(py[e])
                    : e === "transparent"
                      ? new st(NaN, NaN, NaN, 0)
                      : null
  );
}
function yy(e) {
  return new st((e >> 16) & 255, (e >> 8) & 255, e & 255, 1);
}
function da(e, t, n, r) {
  return r <= 0 && (e = t = n = NaN), new st(e, t, n, r);
}
function l3(e) {
  return (
    e instanceof js || (e = ms(e)), e ? ((e = e.rgb()), new st(e.r, e.g, e.b, e.opacity)) : new st()
  );
}
function Qf(e, t, n, r) {
  return arguments.length === 1 ? l3(e) : new st(e, t, n, r ?? 1);
}
function st(e, t, n, r) {
  (this.r = +e), (this.g = +t), (this.b = +n), (this.opacity = +r);
}
qh(
  st,
  Qf,
  jS(js, {
    brighter(e) {
      return (
        (e = e == null ? _l : Math.pow(_l, e)),
        new st(this.r * e, this.g * e, this.b * e, this.opacity)
      );
    },
    darker(e) {
      return (
        (e = e == null ? hs : Math.pow(hs, e)),
        new st(this.r * e, this.g * e, this.b * e, this.opacity)
      );
    },
    rgb() {
      return this;
    },
    clamp() {
      return new st(Tr(this.r), Tr(this.g), Tr(this.b), Nl(this.opacity));
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
    hex: vy,
    formatHex: vy,
    formatHex8: u3,
    formatRgb: xy,
    toString: xy,
  }),
);
function vy() {
  return `#${Sr(this.r)}${Sr(this.g)}${Sr(this.b)}`;
}
function u3() {
  return `#${Sr(this.r)}${Sr(this.g)}${Sr(this.b)}${Sr((isNaN(this.opacity) ? 1 : this.opacity) * 255)}`;
}
function xy() {
  const e = Nl(this.opacity);
  return `${e === 1 ? "rgb(" : "rgba("}${Tr(this.r)}, ${Tr(this.g)}, ${Tr(this.b)}${e === 1 ? ")" : `, ${e})`}`;
}
function Nl(e) {
  return isNaN(e) ? 1 : Math.max(0, Math.min(1, e));
}
function Tr(e) {
  return Math.max(0, Math.min(255, Math.round(e) || 0));
}
function Sr(e) {
  return (e = Tr(e)), (e < 16 ? "0" : "") + e.toString(16);
}
function wy(e, t, n, r) {
  return (
    r <= 0 ? (e = t = n = NaN) : n <= 0 || n >= 1 ? (e = t = NaN) : t <= 0 && (e = NaN),
    new Vt(e, t, n, r)
  );
}
function FS(e) {
  if (e instanceof Vt) return new Vt(e.h, e.s, e.l, e.opacity);
  if ((e instanceof js || (e = ms(e)), !e)) return new Vt();
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
function c3(e, t, n, r) {
  return arguments.length === 1 ? FS(e) : new Vt(e, t, n, r ?? 1);
}
function Vt(e, t, n, r) {
  (this.h = +e), (this.s = +t), (this.l = +n), (this.opacity = +r);
}
qh(
  Vt,
  c3,
  jS(js, {
    brighter(e) {
      return (
        (e = e == null ? _l : Math.pow(_l, e)), new Vt(this.h, this.s, this.l * e, this.opacity)
      );
    },
    darker(e) {
      return (
        (e = e == null ? hs : Math.pow(hs, e)), new Vt(this.h, this.s, this.l * e, this.opacity)
      );
    },
    rgb() {
      var e = (this.h % 360) + (this.h < 0) * 360,
        t = isNaN(e) || isNaN(this.s) ? 0 : this.s,
        n = this.l,
        r = n + (n < 0.5 ? n : 1 - n) * t,
        o = 2 * n - r;
      return new st(
        kc(e >= 240 ? e - 240 : e + 120, o, r),
        kc(e, o, r),
        kc(e < 120 ? e + 240 : e - 120, o, r),
        this.opacity,
      );
    },
    clamp() {
      return new Vt(Sy(this.h), ha(this.s), ha(this.l), Nl(this.opacity));
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
      const e = Nl(this.opacity);
      return `${e === 1 ? "hsl(" : "hsla("}${Sy(this.h)}, ${ha(this.s) * 100}%, ${ha(this.l) * 100}%${e === 1 ? ")" : `, ${e})`}`;
    },
  }),
);
function Sy(e) {
  return (e = (e || 0) % 360), e < 0 ? e + 360 : e;
}
function ha(e) {
  return Math.max(0, Math.min(1, e || 0));
}
function kc(e, t, n) {
  return (
    (e < 60 ? t + ((n - t) * e) / 60 : e < 180 ? n : e < 240 ? t + ((n - t) * (240 - e)) / 60 : t) *
    255
  );
}
const zS = (e) => () => e;
function f3(e, t) {
  return function (n) {
    return e + n * t;
  };
}
function d3(e, t, n) {
  return (
    (e = Math.pow(e, n)),
    (t = Math.pow(t, n) - e),
    (n = 1 / n),
    function (r) {
      return Math.pow(e + r * t, n);
    }
  );
}
function h3(e) {
  return (e = +e) == 1
    ? $S
    : function (t, n) {
        return n - t ? d3(t, n, e) : zS(isNaN(t) ? n : t);
      };
}
function $S(e, t) {
  var n = t - e;
  return n ? f3(e, n) : zS(isNaN(e) ? t : e);
}
const Ey = (function e(t) {
  var n = h3(t);
  function r(o, i) {
    var s = n((o = Qf(o)).r, (i = Qf(i)).r),
      a = n(o.g, i.g),
      l = n(o.b, i.b),
      u = $S(o.opacity, i.opacity);
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
var qf = /[-+]?(?:\d+\.?\d*|\.?\d+)(?:[eE][-+]?\d+)?/g,
  Tc = new RegExp(qf.source, "g");
function p3(e) {
  return function () {
    return e;
  };
}
function m3(e) {
  return function (t) {
    return e(t) + "";
  };
}
function g3(e, t) {
  var n = (qf.lastIndex = Tc.lastIndex = 0),
    r,
    o,
    i,
    s = -1,
    a = [],
    l = [];
  for (e = e + "", t = t + ""; (r = qf.exec(e)) && (o = Tc.exec(t)); )
    (i = o.index) > n && ((i = t.slice(n, i)), a[s] ? (a[s] += i) : (a[++s] = i)),
      (r = r[0]) === (o = o[0])
        ? a[s]
          ? (a[s] += o)
          : (a[++s] = o)
        : ((a[++s] = null), l.push({ i: s, x: Vn(r, o) })),
      (n = Tc.lastIndex);
  return (
    n < t.length && ((i = t.slice(n)), a[s] ? (a[s] += i) : (a[++s] = i)),
    a.length < 2
      ? l[0]
        ? m3(l[0].x)
        : p3(t)
      : ((t = l.length),
        function (u) {
          for (var c = 0, f; c < t; ++c) a[(f = l[c]).i] = f.x(u);
          return a.join("");
        })
  );
}
var Cy = 180 / Math.PI,
  Jf = { translateX: 0, translateY: 0, rotate: 0, skewX: 0, scaleX: 1, scaleY: 1 };
function BS(e, t, n, r, o, i) {
  var s, a, l;
  return (
    (s = Math.sqrt(e * e + t * t)) && ((e /= s), (t /= s)),
    (l = e * n + t * r) && ((n -= e * l), (r -= t * l)),
    (a = Math.sqrt(n * n + r * r)) && ((n /= a), (r /= a), (l /= a)),
    e * r < t * n && ((e = -e), (t = -t), (l = -l), (s = -s)),
    {
      translateX: o,
      translateY: i,
      rotate: Math.atan2(t, e) * Cy,
      skewX: Math.atan(l) * Cy,
      scaleX: s,
      scaleY: a,
    }
  );
}
var pa;
function y3(e) {
  const t = new (typeof DOMMatrix == "function" ? DOMMatrix : WebKitCSSMatrix)(e + "");
  return t.isIdentity ? Jf : BS(t.a, t.b, t.c, t.d, t.e, t.f);
}
function v3(e) {
  return e == null ||
    (pa || (pa = document.createElementNS("http://www.w3.org/2000/svg", "g")),
    pa.setAttribute("transform", e),
    !(e = pa.transform.baseVal.consolidate()))
    ? Jf
    : ((e = e.matrix), BS(e.a, e.b, e.c, e.d, e.e, e.f));
}
function HS(e, t, n, r) {
  function o(u) {
    return u.length ? u.pop() + " " : "";
  }
  function i(u, c, f, d, m, y) {
    if (u !== f || c !== d) {
      var g = m.push("translate(", null, t, null, n);
      y.push({ i: g - 4, x: Vn(u, f) }, { i: g - 2, x: Vn(c, d) });
    } else (f || d) && m.push("translate(" + f + t + d + n);
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
  function l(u, c, f, d, m, y) {
    if (u !== f || c !== d) {
      var g = m.push(o(m) + "scale(", null, ",", null, ")");
      y.push({ i: g - 4, x: Vn(u, f) }, { i: g - 2, x: Vn(c, d) });
    } else (f !== 1 || d !== 1) && m.push(o(m) + "scale(" + f + "," + d + ")");
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
      function (m) {
        for (var y = -1, g = d.length, w; ++y < g; ) f[(w = d[y]).i] = w.x(m);
        return f.join("");
      }
    );
  };
}
var x3 = HS(y3, "px, ", "px)", "deg)"),
  w3 = HS(v3, ", ", ")", ")"),
  S3 = 1e-12;
function by(e) {
  return ((e = Math.exp(e)) + 1 / e) / 2;
}
function E3(e) {
  return ((e = Math.exp(e)) - 1 / e) / 2;
}
function C3(e) {
  return ((e = Math.exp(2 * e)) - 1) / (e + 1);
}
const b3 = (function e(t, n, r) {
  function o(i, s) {
    var a = i[0],
      l = i[1],
      u = i[2],
      c = s[0],
      f = s[1],
      d = s[2],
      m = c - a,
      y = f - l,
      g = m * m + y * y,
      w,
      h;
    if (g < S3)
      (h = Math.log(d / u) / t),
        (w = function (k) {
          return [a + k * m, l + k * y, u * Math.exp(t * k * h)];
        });
    else {
      var p = Math.sqrt(g),
        x = (d * d - u * u + r * g) / (2 * u * n * p),
        S = (d * d - u * u - r * g) / (2 * d * n * p),
        E = Math.log(Math.sqrt(x * x + 1) - x),
        _ = Math.log(Math.sqrt(S * S + 1) - S);
      (h = (_ - E) / t),
        (w = function (k) {
          var N = k * h,
            A = by(E),
            R = (u / (n * p)) * (A * C3(t * N + E) - E3(E));
          return [a + R * m, l + R * y, (u * A) / by(t * N + E)];
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
var Ho = 0,
  bi = 0,
  di = 0,
  US = 1e3,
  Pl,
  ki,
  Ml = 0,
  Ir = 0,
  wu = 0,
  gs = typeof performance == "object" && performance.now ? performance : Date,
  WS =
    typeof window == "object" && window.requestAnimationFrame
      ? window.requestAnimationFrame.bind(window)
      : function (e) {
          setTimeout(e, 17);
        };
function Jh() {
  return Ir || (WS(k3), (Ir = gs.now() + wu));
}
function k3() {
  Ir = 0;
}
function Al() {
  this._call = this._time = this._next = null;
}
Al.prototype = GS.prototype = {
  constructor: Al,
  restart: function (e, t, n) {
    if (typeof e != "function") throw new TypeError("callback is not a function");
    (n = (n == null ? Jh() : +n) + (t == null ? 0 : +t)),
      !this._next && ki !== this && (ki ? (ki._next = this) : (Pl = this), (ki = this)),
      (this._call = e),
      (this._time = n),
      ed();
  },
  stop: function () {
    this._call && ((this._call = null), (this._time = 1 / 0), ed());
  },
};
function GS(e, t, n) {
  var r = new Al();
  return r.restart(e, t, n), r;
}
function T3() {
  Jh(), ++Ho;
  for (var e = Pl, t; e; ) (t = Ir - e._time) >= 0 && e._call.call(void 0, t), (e = e._next);
  --Ho;
}
function ky() {
  (Ir = (Ml = gs.now()) + wu), (Ho = bi = 0);
  try {
    T3();
  } finally {
    (Ho = 0), N3(), (Ir = 0);
  }
}
function _3() {
  var e = gs.now(),
    t = e - Ml;
  t > US && ((wu -= t), (Ml = e));
}
function N3() {
  for (var e, t = Pl, n, r = 1 / 0; t; )
    t._call
      ? (r > t._time && (r = t._time), (e = t), (t = t._next))
      : ((n = t._next), (t._next = null), (t = e ? (e._next = n) : (Pl = n)));
  (ki = e), ed(r);
}
function ed(e) {
  if (!Ho) {
    bi && (bi = clearTimeout(bi));
    var t = e - Ir;
    t > 24
      ? (e < 1 / 0 && (bi = setTimeout(ky, e - gs.now() - wu)), di && (di = clearInterval(di)))
      : (di || ((Ml = gs.now()), (di = setInterval(_3, US))), (Ho = 1), WS(ky));
  }
}
function Ty(e, t, n) {
  var r = new Al();
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
var P3 = vu("start", "end", "cancel", "interrupt"),
  M3 = [],
  KS = 0,
  _y = 1,
  td = 2,
  Ha = 3,
  Ny = 4,
  nd = 5,
  Ua = 6;
function Su(e, t, n, r, o, i) {
  var s = e.__transition;
  if (!s) e.__transition = {};
  else if (n in s) return;
  A3(e, n, {
    name: t,
    index: r,
    group: o,
    on: P3,
    tween: M3,
    time: i.time,
    delay: i.delay,
    duration: i.duration,
    ease: i.ease,
    timer: null,
    state: KS,
  });
}
function ep(e, t) {
  var n = Bt(e, t);
  if (n.state > KS) throw new Error("too late; already scheduled");
  return n;
}
function tn(e, t) {
  var n = Bt(e, t);
  if (n.state > Ha) throw new Error("too late; already running");
  return n;
}
function Bt(e, t) {
  var n = e.__transition;
  if (!n || !(n = n[t])) throw new Error("transition not found");
  return n;
}
function A3(e, t, n) {
  var r = e.__transition,
    o;
  (r[t] = n), (n.timer = GS(i, 0, n.time));
  function i(u) {
    (n.state = _y), n.timer.restart(s, n.delay, n.time), n.delay <= u && s(u - n.delay);
  }
  function s(u) {
    var c, f, d, m;
    if (n.state !== _y) return l();
    for (c in r)
      if (((m = r[c]), m.name === n.name)) {
        if (m.state === Ha) return Ty(s);
        m.state === Ny
          ? ((m.state = Ua),
            m.timer.stop(),
            m.on.call("interrupt", e, e.__data__, m.index, m.group),
            delete r[c])
          : +c < t &&
            ((m.state = Ua),
            m.timer.stop(),
            m.on.call("cancel", e, e.__data__, m.index, m.group),
            delete r[c]);
      }
    if (
      (Ty(function () {
        n.state === Ha && ((n.state = Ny), n.timer.restart(a, n.delay, n.time), a(u));
      }),
      (n.state = td),
      n.on.call("start", e, e.__data__, n.index, n.group),
      n.state === td)
    ) {
      for (n.state = Ha, o = new Array((d = n.tween.length)), c = 0, f = -1; c < d; ++c)
        (m = n.tween[c].value.call(e, e.__data__, n.index, n.group)) && (o[++f] = m);
      o.length = f + 1;
    }
  }
  function a(u) {
    for (
      var c =
          u < n.duration
            ? n.ease.call(null, u / n.duration)
            : (n.timer.restart(l), (n.state = nd), 1),
        f = -1,
        d = o.length;
      ++f < d;

    )
      o[f].call(e, c);
    n.state === nd && (n.on.call("end", e, e.__data__, n.index, n.group), l());
  }
  function l() {
    (n.state = Ua), n.timer.stop(), delete r[t];
    for (var u in r) return;
    delete e.__transition;
  }
}
function Wa(e, t) {
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
      (o = r.state > td && r.state < nd),
        (r.state = Ua),
        r.timer.stop(),
        r.on.call(o ? "interrupt" : "cancel", e, e.__data__, r.index, r.group),
        delete n[s];
    }
    i && delete e.__transition;
  }
}
function R3(e) {
  return this.each(function () {
    Wa(this, e);
  });
}
function D3(e, t) {
  var n, r;
  return function () {
    var o = tn(this, e),
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
function I3(e, t, n) {
  var r, o;
  if (typeof n != "function") throw new Error();
  return function () {
    var i = tn(this, e),
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
function L3(e, t) {
  var n = this._id;
  if (((e += ""), arguments.length < 2)) {
    for (var r = Bt(this.node(), n).tween, o = 0, i = r.length, s; o < i; ++o)
      if ((s = r[o]).name === e) return s.value;
    return null;
  }
  return this.each((t == null ? D3 : I3)(n, e, t));
}
function tp(e, t, n) {
  var r = e._id;
  return (
    e.each(function () {
      var o = tn(this, r);
      (o.value || (o.value = {}))[t] = n.apply(this, arguments);
    }),
    function (o) {
      return Bt(o, r).value[t];
    }
  );
}
function YS(e, t) {
  var n;
  return (typeof t == "number" ? Vn : t instanceof ms ? Ey : (n = ms(t)) ? ((t = n), Ey) : g3)(
    e,
    t,
  );
}
function V3(e) {
  return function () {
    this.removeAttribute(e);
  };
}
function O3(e) {
  return function () {
    this.removeAttributeNS(e.space, e.local);
  };
}
function j3(e, t, n) {
  var r,
    o = n + "",
    i;
  return function () {
    var s = this.getAttribute(e);
    return s === o ? null : s === r ? i : (i = t((r = s), n));
  };
}
function F3(e, t, n) {
  var r,
    o = n + "",
    i;
  return function () {
    var s = this.getAttributeNS(e.space, e.local);
    return s === o ? null : s === r ? i : (i = t((r = s), n));
  };
}
function z3(e, t, n) {
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
function $3(e, t, n) {
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
function B3(e, t) {
  var n = xu(e),
    r = n === "transform" ? w3 : YS;
  return this.attrTween(
    e,
    typeof t == "function"
      ? (n.local ? $3 : z3)(n, r, tp(this, "attr." + e, t))
      : t == null
        ? (n.local ? O3 : V3)(n)
        : (n.local ? F3 : j3)(n, r, t),
  );
}
function H3(e, t) {
  return function (n) {
    this.setAttribute(e, t.call(this, n));
  };
}
function U3(e, t) {
  return function (n) {
    this.setAttributeNS(e.space, e.local, t.call(this, n));
  };
}
function W3(e, t) {
  var n, r;
  function o() {
    var i = t.apply(this, arguments);
    return i !== r && (n = (r = i) && U3(e, i)), n;
  }
  return (o._value = t), o;
}
function G3(e, t) {
  var n, r;
  function o() {
    var i = t.apply(this, arguments);
    return i !== r && (n = (r = i) && H3(e, i)), n;
  }
  return (o._value = t), o;
}
function K3(e, t) {
  var n = "attr." + e;
  if (arguments.length < 2) return (n = this.tween(n)) && n._value;
  if (t == null) return this.tween(n, null);
  if (typeof t != "function") throw new Error();
  var r = xu(e);
  return this.tween(n, (r.local ? W3 : G3)(r, t));
}
function Y3(e, t) {
  return function () {
    ep(this, e).delay = +t.apply(this, arguments);
  };
}
function X3(e, t) {
  return (
    (t = +t),
    function () {
      ep(this, e).delay = t;
    }
  );
}
function Z3(e) {
  var t = this._id;
  return arguments.length
    ? this.each((typeof e == "function" ? Y3 : X3)(t, e))
    : Bt(this.node(), t).delay;
}
function Q3(e, t) {
  return function () {
    tn(this, e).duration = +t.apply(this, arguments);
  };
}
function q3(e, t) {
  return (
    (t = +t),
    function () {
      tn(this, e).duration = t;
    }
  );
}
function J3(e) {
  var t = this._id;
  return arguments.length
    ? this.each((typeof e == "function" ? Q3 : q3)(t, e))
    : Bt(this.node(), t).duration;
}
function eL(e, t) {
  if (typeof t != "function") throw new Error();
  return function () {
    tn(this, e).ease = t;
  };
}
function tL(e) {
  var t = this._id;
  return arguments.length ? this.each(eL(t, e)) : Bt(this.node(), t).ease;
}
function nL(e, t) {
  return function () {
    var n = t.apply(this, arguments);
    if (typeof n != "function") throw new Error();
    tn(this, e).ease = n;
  };
}
function rL(e) {
  if (typeof e != "function") throw new Error();
  return this.each(nL(this._id, e));
}
function oL(e) {
  typeof e != "function" && (e = TS(e));
  for (var t = this._groups, n = t.length, r = new Array(n), o = 0; o < n; ++o)
    for (var i = t[o], s = i.length, a = (r[o] = []), l, u = 0; u < s; ++u)
      (l = i[u]) && e.call(l, l.__data__, u, i) && a.push(l);
  return new bn(r, this._parents, this._name, this._id);
}
function iL(e) {
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
    for (var l = t[a], u = n[a], c = l.length, f = (s[a] = new Array(c)), d, m = 0; m < c; ++m)
      (d = l[m] || u[m]) && (f[m] = d);
  for (; a < r; ++a) s[a] = t[a];
  return new bn(s, this._parents, this._name, this._id);
}
function sL(e) {
  return (e + "")
    .trim()
    .split(/^|\s+/)
    .every(function (t) {
      var n = t.indexOf(".");
      return n >= 0 && (t = t.slice(0, n)), !t || t === "start";
    });
}
function aL(e, t, n) {
  var r,
    o,
    i = sL(t) ? ep : tn;
  return function () {
    var s = i(this, e),
      a = s.on;
    a !== r && (o = (r = a).copy()).on(t, n), (s.on = o);
  };
}
function lL(e, t) {
  var n = this._id;
  return arguments.length < 2 ? Bt(this.node(), n).on.on(e) : this.each(aL(n, e, t));
}
function uL(e) {
  return function () {
    var t = this.parentNode;
    for (var n in this.__transition) if (+n !== e) return;
    t && t.removeChild(this);
  };
}
function cL() {
  return this.on("end.remove", uL(this._id));
}
function fL(e) {
  var t = this._name,
    n = this._id;
  typeof e != "function" && (e = Zh(e));
  for (var r = this._groups, o = r.length, i = new Array(o), s = 0; s < o; ++s)
    for (var a = r[s], l = a.length, u = (i[s] = new Array(l)), c, f, d = 0; d < l; ++d)
      (c = a[d]) &&
        (f = e.call(c, c.__data__, d, a)) &&
        ("__data__" in c && (f.__data__ = c.__data__), (u[d] = f), Su(u[d], t, n, d, u, Bt(c, n)));
  return new bn(i, this._parents, t, n);
}
function dL(e) {
  var t = this._name,
    n = this._id;
  typeof e != "function" && (e = kS(e));
  for (var r = this._groups, o = r.length, i = [], s = [], a = 0; a < o; ++a)
    for (var l = r[a], u = l.length, c, f = 0; f < u; ++f)
      if ((c = l[f])) {
        for (var d = e.call(c, c.__data__, f, l), m, y = Bt(c, n), g = 0, w = d.length; g < w; ++g)
          (m = d[g]) && Su(m, t, n, g, d, y);
        i.push(d), s.push(c);
      }
  return new bn(i, s, t, n);
}
var hL = Os.prototype.constructor;
function pL() {
  return new hL(this._groups, this._parents);
}
function mL(e, t) {
  var n, r, o;
  return function () {
    var i = Bo(this, e),
      s = (this.style.removeProperty(e), Bo(this, e));
    return i === s ? null : i === n && s === r ? o : (o = t((n = i), (r = s)));
  };
}
function XS(e) {
  return function () {
    this.style.removeProperty(e);
  };
}
function gL(e, t, n) {
  var r,
    o = n + "",
    i;
  return function () {
    var s = Bo(this, e);
    return s === o ? null : s === r ? i : (i = t((r = s), n));
  };
}
function yL(e, t, n) {
  var r, o, i;
  return function () {
    var s = Bo(this, e),
      a = n(this),
      l = a + "";
    return (
      a == null && (l = a = (this.style.removeProperty(e), Bo(this, e))),
      s === l ? null : s === r && l === o ? i : ((o = l), (i = t((r = s), a)))
    );
  };
}
function vL(e, t) {
  var n,
    r,
    o,
    i = "style." + t,
    s = "end." + i,
    a;
  return function () {
    var l = tn(this, e),
      u = l.on,
      c = l.value[i] == null ? a || (a = XS(t)) : void 0;
    (u !== n || o !== c) && (r = (n = u).copy()).on(s, (o = c)), (l.on = r);
  };
}
function xL(e, t, n) {
  var r = (e += "") == "transform" ? x3 : YS;
  return t == null
    ? this.styleTween(e, mL(e, r)).on("end.style." + e, XS(e))
    : typeof t == "function"
      ? this.styleTween(e, yL(e, r, tp(this, "style." + e, t))).each(vL(this._id, e))
      : this.styleTween(e, gL(e, r, t), n).on("end.style." + e, null);
}
function wL(e, t, n) {
  return function (r) {
    this.style.setProperty(e, t.call(this, r), n);
  };
}
function SL(e, t, n) {
  var r, o;
  function i() {
    var s = t.apply(this, arguments);
    return s !== o && (r = (o = s) && wL(e, s, n)), r;
  }
  return (i._value = t), i;
}
function EL(e, t, n) {
  var r = "style." + (e += "");
  if (arguments.length < 2) return (r = this.tween(r)) && r._value;
  if (t == null) return this.tween(r, null);
  if (typeof t != "function") throw new Error();
  return this.tween(r, SL(e, t, n ?? ""));
}
function CL(e) {
  return function () {
    this.textContent = e;
  };
}
function bL(e) {
  return function () {
    var t = e(this);
    this.textContent = t ?? "";
  };
}
function kL(e) {
  return this.tween(
    "text",
    typeof e == "function" ? bL(tp(this, "text", e)) : CL(e == null ? "" : e + ""),
  );
}
function TL(e) {
  return function (t) {
    this.textContent = e.call(this, t);
  };
}
function _L(e) {
  var t, n;
  function r() {
    var o = e.apply(this, arguments);
    return o !== n && (t = (n = o) && TL(o)), t;
  }
  return (r._value = e), r;
}
function NL(e) {
  var t = "text";
  if (arguments.length < 1) return (t = this.tween(t)) && t._value;
  if (e == null) return this.tween(t, null);
  if (typeof e != "function") throw new Error();
  return this.tween(t, _L(e));
}
function PL() {
  for (
    var e = this._name, t = this._id, n = ZS(), r = this._groups, o = r.length, i = 0;
    i < o;
    ++i
  )
    for (var s = r[i], a = s.length, l, u = 0; u < a; ++u)
      if ((l = s[u])) {
        var c = Bt(l, t);
        Su(l, e, n, u, s, {
          time: c.time + c.delay + c.duration,
          delay: 0,
          duration: c.duration,
          ease: c.ease,
        });
      }
  return new bn(r, this._parents, e, n);
}
function ML() {
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
      var u = tn(this, r),
        c = u.on;
      c !== e && ((t = (e = c).copy()), t._.cancel.push(a), t._.interrupt.push(a), t._.end.push(l)),
        (u.on = t);
    }),
      o === 0 && i();
  });
}
var AL = 0;
function bn(e, t, n, r) {
  (this._groups = e), (this._parents = t), (this._name = n), (this._id = r);
}
function ZS() {
  return ++AL;
}
var an = Os.prototype;
bn.prototype = {
  constructor: bn,
  select: fL,
  selectAll: dL,
  selectChild: an.selectChild,
  selectChildren: an.selectChildren,
  filter: oL,
  merge: iL,
  selection: pL,
  transition: PL,
  call: an.call,
  nodes: an.nodes,
  node: an.node,
  size: an.size,
  empty: an.empty,
  each: an.each,
  on: lL,
  attr: B3,
  attrTween: K3,
  style: xL,
  styleTween: EL,
  text: kL,
  textTween: NL,
  remove: cL,
  tween: L3,
  delay: Z3,
  duration: J3,
  ease: tL,
  easeVarying: rL,
  end: ML,
  [Symbol.iterator]: an[Symbol.iterator],
};
function RL(e) {
  return ((e *= 2) <= 1 ? e * e * e : (e -= 2) * e * e + 2) / 2;
}
var DL = { time: null, delay: 0, duration: 250, ease: RL };
function IL(e, t) {
  for (var n; !(n = e.__transition) || !(n = n[t]); )
    if (!(e = e.parentNode)) throw new Error(`transition ${t} not found`);
  return n;
}
function LL(e) {
  var t, n;
  e instanceof bn
    ? ((t = e._id), (e = e._name))
    : ((t = ZS()), ((n = DL).time = Jh()), (e = e == null ? null : e + ""));
  for (var r = this._groups, o = r.length, i = 0; i < o; ++i)
    for (var s = r[i], a = s.length, l, u = 0; u < a; ++u)
      (l = s[u]) && Su(l, e, t, u, s, n || IL(l, t));
  return new bn(r, this._parents, e, t);
}
Os.prototype.interrupt = R3;
Os.prototype.transition = LL;
const ma = (e) => () => e;
function VL(e, { sourceEvent: t, target: n, transform: r, dispatch: o }) {
  Object.defineProperties(this, {
    type: { value: e, enumerable: !0, configurable: !0 },
    sourceEvent: { value: t, enumerable: !0, configurable: !0 },
    target: { value: n, enumerable: !0, configurable: !0 },
    transform: { value: r, enumerable: !0, configurable: !0 },
    _: { value: o },
  });
}
function hn(e, t, n) {
  (this.k = e), (this.x = t), (this.y = n);
}
hn.prototype = {
  constructor: hn,
  scale: function (e) {
    return e === 1 ? this : new hn(this.k * e, this.x, this.y);
  },
  translate: function (e, t) {
    return (e === 0) & (t === 0) ? this : new hn(this.k, this.x + this.k * e, this.y + this.k * t);
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
var yn = new hn(1, 0, 0);
hn.prototype;
function _c(e) {
  e.stopImmediatePropagation();
}
function hi(e) {
  e.preventDefault(), e.stopImmediatePropagation();
}
function OL(e) {
  return (!e.ctrlKey || e.type === "wheel") && !e.button;
}
function jL() {
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
function Py() {
  return this.__zoom || yn;
}
function FL(e) {
  return -e.deltaY * (e.deltaMode === 1 ? 0.05 : e.deltaMode ? 1 : 0.002) * (e.ctrlKey ? 10 : 1);
}
function zL() {
  return navigator.maxTouchPoints || "ontouchstart" in this;
}
function $L(e, t, n) {
  var r = e.invertX(t[0][0]) - n[0][0],
    o = e.invertX(t[1][0]) - n[1][0],
    i = e.invertY(t[0][1]) - n[0][1],
    s = e.invertY(t[1][1]) - n[1][1];
  return e.translate(
    o > r ? (r + o) / 2 : Math.min(0, r) || Math.max(0, o),
    s > i ? (i + s) / 2 : Math.min(0, i) || Math.max(0, s),
  );
}
function QS() {
  var e = OL,
    t = jL,
    n = $L,
    r = FL,
    o = zL,
    i = [0, 1 / 0],
    s = [
      [-1 / 0, -1 / 0],
      [1 / 0, 1 / 0],
    ],
    a = 250,
    l = b3,
    u = vu("start", "zoom", "end"),
    c,
    f,
    d,
    m = 500,
    y = 150,
    g = 0,
    w = 10;
  function h(b) {
    b.property("__zoom", Py)
      .on("wheel.zoom", N, { passive: !1 })
      .on("mousedown.zoom", A)
      .on("dblclick.zoom", R)
      .filter(o)
      .on("touchstart.zoom", O)
      .on("touchmove.zoom", j)
      .on("touchend.zoom touchcancel.zoom", $)
      .style("-webkit-tap-highlight-color", "rgba(0,0,0,0)");
  }
  (h.transform = function (b, I, P, V) {
    var M = b.selection ? b.selection() : b;
    M.property("__zoom", Py),
      b !== M
        ? E(b, I, P, V)
        : M.interrupt().each(function () {
            _(this, arguments)
              .event(V)
              .start()
              .zoom(null, typeof I == "function" ? I.apply(this, arguments) : I)
              .end();
          });
  }),
    (h.scaleBy = function (b, I, P, V) {
      h.scaleTo(
        b,
        function () {
          var M = this.__zoom.k,
            T = typeof I == "function" ? I.apply(this, arguments) : I;
          return M * T;
        },
        P,
        V,
      );
    }),
    (h.scaleTo = function (b, I, P, V) {
      h.transform(
        b,
        function () {
          var M = t.apply(this, arguments),
            T = this.__zoom,
            D = P == null ? S(M) : typeof P == "function" ? P.apply(this, arguments) : P,
            F = T.invert(D),
            z = typeof I == "function" ? I.apply(this, arguments) : I;
          return n(x(p(T, z), D, F), M, s);
        },
        P,
        V,
      );
    }),
    (h.translateBy = function (b, I, P, V) {
      h.transform(
        b,
        function () {
          return n(
            this.__zoom.translate(
              typeof I == "function" ? I.apply(this, arguments) : I,
              typeof P == "function" ? P.apply(this, arguments) : P,
            ),
            t.apply(this, arguments),
            s,
          );
        },
        null,
        V,
      );
    }),
    (h.translateTo = function (b, I, P, V, M) {
      h.transform(
        b,
        function () {
          var T = t.apply(this, arguments),
            D = this.__zoom,
            F = V == null ? S(T) : typeof V == "function" ? V.apply(this, arguments) : V;
          return n(
            yn
              .translate(F[0], F[1])
              .scale(D.k)
              .translate(
                typeof I == "function" ? -I.apply(this, arguments) : -I,
                typeof P == "function" ? -P.apply(this, arguments) : -P,
              ),
            T,
            s,
          );
        },
        V,
        M,
      );
    });
  function p(b, I) {
    return (I = Math.max(i[0], Math.min(i[1], I))), I === b.k ? b : new hn(I, b.x, b.y);
  }
  function x(b, I, P) {
    var V = I[0] - P[0] * b.k,
      M = I[1] - P[1] * b.k;
    return V === b.x && M === b.y ? b : new hn(b.k, V, M);
  }
  function S(b) {
    return [(+b[0][0] + +b[1][0]) / 2, (+b[0][1] + +b[1][1]) / 2];
  }
  function E(b, I, P, V) {
    b.on("start.zoom", function () {
      _(this, arguments).event(V).start();
    })
      .on("interrupt.zoom end.zoom", function () {
        _(this, arguments).event(V).end();
      })
      .tween("zoom", function () {
        var M = this,
          T = arguments,
          D = _(M, T).event(V),
          F = t.apply(M, T),
          z = P == null ? S(F) : typeof P == "function" ? P.apply(M, T) : P,
          W = Math.max(F[1][0] - F[0][0], F[1][1] - F[0][1]),
          H = M.__zoom,
          Y = typeof I == "function" ? I.apply(M, T) : I,
          U = l(H.invert(z).concat(W / H.k), Y.invert(z).concat(W / Y.k));
        return function (X) {
          if (X === 1) X = Y;
          else {
            var te = U(X),
              q = W / te[2];
            X = new hn(q, z[0] - te[0] * q, z[1] - te[1] * q);
          }
          D.zoom(null, X);
        };
      });
  }
  function _(b, I, P) {
    return (!P && b.__zooming) || new k(b, I);
  }
  function k(b, I) {
    (this.that = b),
      (this.args = I),
      (this.active = 0),
      (this.sourceEvent = null),
      (this.extent = t.apply(b, I)),
      (this.taps = 0);
  }
  k.prototype = {
    event: function (b) {
      return b && (this.sourceEvent = b), this;
    },
    start: function () {
      return ++this.active === 1 && ((this.that.__zooming = this), this.emit("start")), this;
    },
    zoom: function (b, I) {
      return (
        this.mouse && b !== "mouse" && (this.mouse[1] = I.invert(this.mouse[0])),
        this.touch0 && b !== "touch" && (this.touch0[1] = I.invert(this.touch0[0])),
        this.touch1 && b !== "touch" && (this.touch1[1] = I.invert(this.touch1[0])),
        (this.that.__zoom = I),
        this.emit("zoom"),
        this
      );
    },
    end: function () {
      return --this.active === 0 && (delete this.that.__zooming, this.emit("end")), this;
    },
    emit: function (b) {
      var I = Ct(this.that).datum();
      u.call(
        b,
        this.that,
        new VL(b, {
          sourceEvent: this.sourceEvent,
          target: h,
          transform: this.that.__zoom,
          dispatch: u,
        }),
        I,
      );
    },
  };
  function N(b, ...I) {
    if (!e.apply(this, arguments)) return;
    var P = _(this, I).event(b),
      V = this.__zoom,
      M = Math.max(i[0], Math.min(i[1], V.k * Math.pow(2, r.apply(this, arguments)))),
      T = It(b);
    if (P.wheel)
      (P.mouse[0][0] !== T[0] || P.mouse[0][1] !== T[1]) &&
        (P.mouse[1] = V.invert((P.mouse[0] = T))),
        clearTimeout(P.wheel);
    else {
      if (V.k === M) return;
      (P.mouse = [T, V.invert(T)]), Wa(this), P.start();
    }
    hi(b),
      (P.wheel = setTimeout(D, y)),
      P.zoom("mouse", n(x(p(V, M), P.mouse[0], P.mouse[1]), P.extent, s));
    function D() {
      (P.wheel = null), P.end();
    }
  }
  function A(b, ...I) {
    if (d || !e.apply(this, arguments)) return;
    var P = b.currentTarget,
      V = _(this, I, !0).event(b),
      M = Ct(b.view).on("mousemove.zoom", z, !0).on("mouseup.zoom", W, !0),
      T = It(b, P),
      D = b.clientX,
      F = b.clientY;
    VS(b.view), _c(b), (V.mouse = [T, this.__zoom.invert(T)]), Wa(this), V.start();
    function z(H) {
      if ((hi(H), !V.moved)) {
        var Y = H.clientX - D,
          U = H.clientY - F;
        V.moved = Y * Y + U * U > g;
      }
      V.event(H).zoom(
        "mouse",
        n(x(V.that.__zoom, (V.mouse[0] = It(H, P)), V.mouse[1]), V.extent, s),
      );
    }
    function W(H) {
      M.on("mousemove.zoom mouseup.zoom", null), OS(H.view, V.moved), hi(H), V.event(H).end();
    }
  }
  function R(b, ...I) {
    if (e.apply(this, arguments)) {
      var P = this.__zoom,
        V = It(b.changedTouches ? b.changedTouches[0] : b, this),
        M = P.invert(V),
        T = P.k * (b.shiftKey ? 0.5 : 2),
        D = n(x(p(P, T), V, M), t.apply(this, I), s);
      hi(b),
        a > 0
          ? Ct(this).transition().duration(a).call(E, D, V, b)
          : Ct(this).call(h.transform, D, V, b);
    }
  }
  function O(b, ...I) {
    if (e.apply(this, arguments)) {
      var P = b.touches,
        V = P.length,
        M = _(this, I, b.changedTouches.length === V).event(b),
        T,
        D,
        F,
        z;
      for (_c(b), D = 0; D < V; ++D)
        (F = P[D]),
          (z = It(F, this)),
          (z = [z, this.__zoom.invert(z), F.identifier]),
          M.touch0
            ? !M.touch1 && M.touch0[2] !== z[2] && ((M.touch1 = z), (M.taps = 0))
            : ((M.touch0 = z), (T = !0), (M.taps = 1 + !!c));
      c && (c = clearTimeout(c)),
        T &&
          (M.taps < 2 &&
            ((f = z[0]),
            (c = setTimeout(function () {
              c = null;
            }, m))),
          Wa(this),
          M.start());
    }
  }
  function j(b, ...I) {
    if (this.__zooming) {
      var P = _(this, I).event(b),
        V = b.changedTouches,
        M = V.length,
        T,
        D,
        F,
        z;
      for (hi(b), T = 0; T < M; ++T)
        (D = V[T]),
          (F = It(D, this)),
          P.touch0 && P.touch0[2] === D.identifier
            ? (P.touch0[0] = F)
            : P.touch1 && P.touch1[2] === D.identifier && (P.touch1[0] = F);
      if (((D = P.that.__zoom), P.touch1)) {
        var W = P.touch0[0],
          H = P.touch0[1],
          Y = P.touch1[0],
          U = P.touch1[1],
          X = (X = Y[0] - W[0]) * X + (X = Y[1] - W[1]) * X,
          te = (te = U[0] - H[0]) * te + (te = U[1] - H[1]) * te;
        (D = p(D, Math.sqrt(X / te))),
          (F = [(W[0] + Y[0]) / 2, (W[1] + Y[1]) / 2]),
          (z = [(H[0] + U[0]) / 2, (H[1] + U[1]) / 2]);
      } else if (P.touch0) (F = P.touch0[0]), (z = P.touch0[1]);
      else return;
      P.zoom("touch", n(x(D, F, z), P.extent, s));
    }
  }
  function $(b, ...I) {
    if (this.__zooming) {
      var P = _(this, I).event(b),
        V = b.changedTouches,
        M = V.length,
        T,
        D;
      for (
        _c(b),
          d && clearTimeout(d),
          d = setTimeout(function () {
            d = null;
          }, m),
          T = 0;
        T < M;
        ++T
      )
        (D = V[T]),
          P.touch0 && P.touch0[2] === D.identifier
            ? delete P.touch0
            : P.touch1 && P.touch1[2] === D.identifier && delete P.touch1;
      if ((P.touch1 && !P.touch0 && ((P.touch0 = P.touch1), delete P.touch1), P.touch0))
        P.touch0[1] = this.__zoom.invert(P.touch0[0]);
      else if (
        (P.end(), P.taps === 2 && ((D = It(D, this)), Math.hypot(f[0] - D[0], f[1] - D[1]) < w))
      ) {
        var F = Ct(this).on("dblclick.zoom");
        F && F.apply(this, arguments);
      }
    }
  }
  return (
    (h.wheelDelta = function (b) {
      return arguments.length ? ((r = typeof b == "function" ? b : ma(+b)), h) : r;
    }),
    (h.filter = function (b) {
      return arguments.length ? ((e = typeof b == "function" ? b : ma(!!b)), h) : e;
    }),
    (h.touchable = function (b) {
      return arguments.length ? ((o = typeof b == "function" ? b : ma(!!b)), h) : o;
    }),
    (h.extent = function (b) {
      return arguments.length
        ? ((t =
            typeof b == "function"
              ? b
              : ma([
                  [+b[0][0], +b[0][1]],
                  [+b[1][0], +b[1][1]],
                ])),
          h)
        : t;
    }),
    (h.scaleExtent = function (b) {
      return arguments.length ? ((i[0] = +b[0]), (i[1] = +b[1]), h) : [i[0], i[1]];
    }),
    (h.translateExtent = function (b) {
      return arguments.length
        ? ((s[0][0] = +b[0][0]),
          (s[1][0] = +b[1][0]),
          (s[0][1] = +b[0][1]),
          (s[1][1] = +b[1][1]),
          h)
        : [
            [s[0][0], s[0][1]],
            [s[1][0], s[1][1]],
          ];
    }),
    (h.constrain = function (b) {
      return arguments.length ? ((n = b), h) : n;
    }),
    (h.duration = function (b) {
      return arguments.length ? ((a = +b), h) : a;
    }),
    (h.interpolate = function (b) {
      return arguments.length ? ((l = b), h) : l;
    }),
    (h.on = function () {
      var b = u.on.apply(u, arguments);
      return b === u ? h : b;
    }),
    (h.clickDistance = function (b) {
      return arguments.length ? ((g = (b = +b) * b), h) : Math.sqrt(g);
    }),
    (h.tapDistance = function (b) {
      return arguments.length ? ((w = +b), h) : w;
    }),
    h
  );
}
const Eu = v.createContext(null),
  BL = Eu.Provider,
  kn = {
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
  qS = kn.error001();
function fe(e, t) {
  const n = v.useContext(Eu);
  if (n === null) throw new Error(qS);
  return CS(n, e, t);
}
const Ae = () => {
    const e = v.useContext(Eu);
    if (e === null) throw new Error(qS);
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
  HL = (e) => (e.userSelectionActive ? "none" : "all");
function np({ position: e, children: t, className: n, style: r, ...o }) {
  const i = fe(HL),
    s = `${e}`.split("-");
  return L.createElement(
    "div",
    { className: He(["react-flow__panel", n, ...s]), style: { ...r, pointerEvents: i }, ...o },
    t,
  );
}
function UL({ proOptions: e, position: t = "bottom-right" }) {
  return e != null && e.hideAttribution
    ? null
    : L.createElement(
        np,
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
const WL = ({
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
    [d, m] = v.useState({ x: 0, y: 0, width: 0, height: 0 }),
    y = He(["react-flow__edge-textwrapper", u]);
  return (
    v.useEffect(() => {
      if (f.current) {
        const g = f.current.getBBox();
        m({ x: g.x, y: g.y, width: g.width, height: g.height });
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
var GL = v.memo(WL);
const rp = (e) => ({ width: e.offsetWidth, height: e.offsetHeight }),
  Uo = (e, t = 0, n = 1) => Math.min(Math.max(e, t), n),
  op = (e = { x: 0, y: 0 }, t) => ({ x: Uo(e.x, t[0][0], t[1][0]), y: Uo(e.y, t[0][1], t[1][1]) }),
  My = (e, t, n) =>
    e < t ? Uo(Math.abs(e - t), 1, 50) / 50 : e > n ? -Uo(Math.abs(e - n), 1, 50) / 50 : 0,
  JS = (e, t) => {
    const n = My(e.x, 35, t.width - 35) * 20,
      r = My(e.y, 35, t.height - 35) * 20;
    return [n, r];
  },
  eE = (e) => {
    var t;
    return (
      ((t = e.getRootNode) == null ? void 0 : t.call(e)) ||
      (window == null ? void 0 : window.document)
    );
  },
  tE = (e, t) => ({
    x: Math.min(e.x, t.x),
    y: Math.min(e.y, t.y),
    x2: Math.max(e.x2, t.x2),
    y2: Math.max(e.y2, t.y2),
  }),
  ys = ({ x: e, y: t, width: n, height: r }) => ({ x: e, y: t, x2: e + n, y2: t + r }),
  nE = ({ x: e, y: t, x2: n, y2: r }) => ({ x: e, y: t, width: n - e, height: r - t }),
  Ay = (e) => ({
    ...(e.positionAbsolute || { x: 0, y: 0 }),
    width: e.width || 0,
    height: e.height || 0,
  }),
  KL = (e, t) => nE(tE(ys(e), ys(t))),
  rd = (e, t) => {
    const n = Math.max(0, Math.min(e.x + e.width, t.x + t.width) - Math.max(e.x, t.x)),
      r = Math.max(0, Math.min(e.y + e.height, t.y + t.height) - Math.max(e.y, t.y));
    return Math.ceil(n * r);
  },
  YL = (e) => kt(e.width) && kt(e.height) && kt(e.x) && kt(e.y),
  kt = (e) => !isNaN(e) && isFinite(e),
  Te = Symbol.for("internals"),
  rE = ["Enter", " ", "Escape"],
  XL = (e, t) => {},
  ZL = (e) => "nativeEvent" in e;
function od(e) {
  var o, i;
  const t = ZL(e) ? e.nativeEvent : e,
    n =
      ((i = (o = t.composedPath) == null ? void 0 : o.call(t)) == null ? void 0 : i[0]) || e.target;
  return (
    ["INPUT", "SELECT", "TEXTAREA"].includes(n == null ? void 0 : n.nodeName) ||
    (n == null ? void 0 : n.hasAttribute("contenteditable")) ||
    !!(n != null && n.closest(".nokey"))
  );
}
const oE = (e) => "clientX" in e,
  Zn = (e, t) => {
    var i, s;
    const n = oE(e),
      r = n ? e.clientX : (i = e.touches) == null ? void 0 : i[0].clientX,
      o = n ? e.clientY : (s = e.touches) == null ? void 0 : s[0].clientY;
    return {
      x: r - ((t == null ? void 0 : t.left) ?? 0),
      y: o - ((t == null ? void 0 : t.top) ?? 0),
    };
  },
  Rl = () => {
    var e;
    return (
      typeof navigator < "u" &&
      ((e = navigator == null ? void 0 : navigator.userAgent) == null
        ? void 0
        : e.indexOf("Mac")) >= 0
    );
  },
  Fs = ({
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
    interactionWidth: m = 20,
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
      m &&
        L.createElement("path", {
          d: t,
          fill: "none",
          strokeOpacity: 0,
          strokeWidth: m,
          className: "react-flow__edge-interaction",
        }),
      o && kt(n) && kt(r)
        ? L.createElement(GL, {
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
Fs.displayName = "BaseEdge";
function pi(e, t, n) {
  return n === void 0
    ? n
    : (r) => {
        const o = t().edges.find((i) => i.id === e);
        o && n(r, { ...o });
      };
}
function iE({ sourceX: e, sourceY: t, targetX: n, targetY: r }) {
  const o = Math.abs(n - e) / 2,
    i = n < e ? n + o : n - o,
    s = Math.abs(r - t) / 2,
    a = r < t ? r + s : r - s;
  return [i, a, o, s];
}
function sE({
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
var Lr;
(function (e) {
  (e.Strict = "strict"), (e.Loose = "loose");
})(Lr || (Lr = {}));
var Er;
(function (e) {
  (e.Free = "free"), (e.Vertical = "vertical"), (e.Horizontal = "horizontal");
})(Er || (Er = {}));
var vs;
(function (e) {
  (e.Partial = "partial"), (e.Full = "full");
})(vs || (vs = {}));
var cn;
(function (e) {
  (e.Bezier = "default"),
    (e.Straight = "straight"),
    (e.Step = "step"),
    (e.SmoothStep = "smoothstep"),
    (e.SimpleBezier = "simplebezier");
})(cn || (cn = {}));
var xs;
(function (e) {
  (e.Arrow = "arrow"), (e.ArrowClosed = "arrowclosed");
})(xs || (xs = {}));
var K;
(function (e) {
  (e.Left = "left"), (e.Top = "top"), (e.Right = "right"), (e.Bottom = "bottom");
})(K || (K = {}));
function Ry({ pos: e, x1: t, y1: n, x2: r, y2: o }) {
  return e === K.Left || e === K.Right ? [0.5 * (t + r), n] : [t, 0.5 * (n + o)];
}
function aE({
  sourceX: e,
  sourceY: t,
  sourcePosition: n = K.Bottom,
  targetX: r,
  targetY: o,
  targetPosition: i = K.Top,
}) {
  const [s, a] = Ry({ pos: n, x1: e, y1: t, x2: r, y2: o }),
    [l, u] = Ry({ pos: i, x1: r, y1: o, x2: e, y2: t }),
    [c, f, d, m] = sE({
      sourceX: e,
      sourceY: t,
      targetX: r,
      targetY: o,
      sourceControlX: s,
      sourceControlY: a,
      targetControlX: l,
      targetControlY: u,
    });
  return [`M${e},${t} C${s},${a} ${l},${u} ${r},${o}`, c, f, d, m];
}
const ip = v.memo(
  ({
    sourceX: e,
    sourceY: t,
    targetX: n,
    targetY: r,
    sourcePosition: o = K.Bottom,
    targetPosition: i = K.Top,
    label: s,
    labelStyle: a,
    labelShowBg: l,
    labelBgStyle: u,
    labelBgPadding: c,
    labelBgBorderRadius: f,
    style: d,
    markerEnd: m,
    markerStart: y,
    interactionWidth: g,
  }) => {
    const [w, h, p] = aE({
      sourceX: e,
      sourceY: t,
      sourcePosition: o,
      targetX: n,
      targetY: r,
      targetPosition: i,
    });
    return L.createElement(Fs, {
      path: w,
      labelX: h,
      labelY: p,
      label: s,
      labelStyle: a,
      labelShowBg: l,
      labelBgStyle: u,
      labelBgPadding: c,
      labelBgBorderRadius: f,
      style: d,
      markerEnd: m,
      markerStart: y,
      interactionWidth: g,
    });
  },
);
ip.displayName = "SimpleBezierEdge";
const Dy = {
    [K.Left]: { x: -1, y: 0 },
    [K.Right]: { x: 1, y: 0 },
    [K.Top]: { x: 0, y: -1 },
    [K.Bottom]: { x: 0, y: 1 },
  },
  QL = ({ source: e, sourcePosition: t = K.Bottom, target: n }) =>
    t === K.Left || t === K.Right
      ? e.x < n.x
        ? { x: 1, y: 0 }
        : { x: -1, y: 0 }
      : e.y < n.y
        ? { x: 0, y: 1 }
        : { x: 0, y: -1 },
  Iy = (e, t) => Math.sqrt(Math.pow(t.x - e.x, 2) + Math.pow(t.y - e.y, 2));
function qL({
  source: e,
  sourcePosition: t = K.Bottom,
  target: n,
  targetPosition: r = K.Top,
  center: o,
  offset: i,
}) {
  const s = Dy[t],
    a = Dy[r],
    l = { x: e.x + s.x * i, y: e.y + s.y * i },
    u = { x: n.x + a.x * i, y: n.y + a.y * i },
    c = QL({ source: l, sourcePosition: t, target: u }),
    f = c.x !== 0 ? "x" : "y",
    d = c[f];
  let m = [],
    y,
    g;
  const w = { x: 0, y: 0 },
    h = { x: 0, y: 0 },
    [p, x, S, E] = iE({ sourceX: e.x, sourceY: e.y, targetX: n.x, targetY: n.y });
  if (s[f] * a[f] === -1) {
    (y = o.x ?? p), (g = o.y ?? x);
    const k = [
        { x: y, y: l.y },
        { x: y, y: u.y },
      ],
      N = [
        { x: l.x, y: g },
        { x: u.x, y: g },
      ];
    s[f] === d ? (m = f === "x" ? k : N) : (m = f === "x" ? N : k);
  } else {
    const k = [{ x: l.x, y: u.y }],
      N = [{ x: u.x, y: l.y }];
    if ((f === "x" ? (m = s.x === d ? N : k) : (m = s.y === d ? k : N), t === r)) {
      const $ = Math.abs(e[f] - n[f]);
      if ($ <= i) {
        const b = Math.min(i - 1, i - $);
        s[f] === d ? (w[f] = (l[f] > e[f] ? -1 : 1) * b) : (h[f] = (u[f] > n[f] ? -1 : 1) * b);
      }
    }
    if (t !== r) {
      const $ = f === "x" ? "y" : "x",
        b = s[f] === a[$],
        I = l[$] > u[$],
        P = l[$] < u[$];
      ((s[f] === 1 && ((!b && I) || (b && P))) || (s[f] !== 1 && ((!b && P) || (b && I)))) &&
        (m = f === "x" ? k : N);
    }
    const A = { x: l.x + w.x, y: l.y + w.y },
      R = { x: u.x + h.x, y: u.y + h.y },
      O = Math.max(Math.abs(A.x - m[0].x), Math.abs(R.x - m[0].x)),
      j = Math.max(Math.abs(A.y - m[0].y), Math.abs(R.y - m[0].y));
    O >= j ? ((y = (A.x + R.x) / 2), (g = m[0].y)) : ((y = m[0].x), (g = (A.y + R.y) / 2));
  }
  return [[e, { x: l.x + w.x, y: l.y + w.y }, ...m, { x: u.x + h.x, y: u.y + h.y }, n], y, g, S, E];
}
function JL(e, t, n, r) {
  const o = Math.min(Iy(e, t) / 2, Iy(t, n) / 2, r),
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
function Dl({
  sourceX: e,
  sourceY: t,
  sourcePosition: n = K.Bottom,
  targetX: r,
  targetY: o,
  targetPosition: i = K.Top,
  borderRadius: s = 5,
  centerX: a,
  centerY: l,
  offset: u = 20,
}) {
  const [c, f, d, m, y] = qL({
    source: { x: e, y: t },
    sourcePosition: n,
    target: { x: r, y: o },
    targetPosition: i,
    center: { x: a, y: l },
    offset: u,
  });
  return [
    c.reduce((w, h, p) => {
      let x = "";
      return (
        p > 0 && p < c.length - 1
          ? (x = JL(c[p - 1], h, c[p + 1], s))
          : (x = `${p === 0 ? "M" : "L"}${h.x} ${h.y}`),
        (w += x),
        w
      );
    }, ""),
    f,
    d,
    m,
    y,
  ];
}
const Cu = v.memo(
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
    sourcePosition: f = K.Bottom,
    targetPosition: d = K.Top,
    markerEnd: m,
    markerStart: y,
    pathOptions: g,
    interactionWidth: w,
  }) => {
    const [h, p, x] = Dl({
      sourceX: e,
      sourceY: t,
      sourcePosition: f,
      targetX: n,
      targetY: r,
      targetPosition: d,
      borderRadius: g == null ? void 0 : g.borderRadius,
      offset: g == null ? void 0 : g.offset,
    });
    return L.createElement(Fs, {
      path: h,
      labelX: p,
      labelY: x,
      label: o,
      labelStyle: i,
      labelShowBg: s,
      labelBgStyle: a,
      labelBgPadding: l,
      labelBgBorderRadius: u,
      style: c,
      markerEnd: m,
      markerStart: y,
      interactionWidth: w,
    });
  },
);
Cu.displayName = "SmoothStepEdge";
const sp = v.memo((e) => {
  var t;
  return L.createElement(Cu, {
    ...e,
    pathOptions: v.useMemo(() => {
      var n;
      return { borderRadius: 0, offset: (n = e.pathOptions) == null ? void 0 : n.offset };
    }, [(t = e.pathOptions) == null ? void 0 : t.offset]),
  });
});
sp.displayName = "StepEdge";
function e4({ sourceX: e, sourceY: t, targetX: n, targetY: r }) {
  const [o, i, s, a] = iE({ sourceX: e, sourceY: t, targetX: n, targetY: r });
  return [`M ${e},${t}L ${n},${r}`, o, i, s, a];
}
const ap = v.memo(
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
    interactionWidth: m,
  }) => {
    const [y, g, w] = e4({ sourceX: e, sourceY: t, targetX: n, targetY: r });
    return L.createElement(Fs, {
      path: y,
      labelX: g,
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
      interactionWidth: m,
    });
  },
);
ap.displayName = "StraightEdge";
function ga(e, t) {
  return e >= 0 ? 0.5 * e : t * 25 * Math.sqrt(-e);
}
function Ly({ pos: e, x1: t, y1: n, x2: r, y2: o, c: i }) {
  switch (e) {
    case K.Left:
      return [t - ga(t - r, i), n];
    case K.Right:
      return [t + ga(r - t, i), n];
    case K.Top:
      return [t, n - ga(n - o, i)];
    case K.Bottom:
      return [t, n + ga(o - n, i)];
  }
}
function lE({
  sourceX: e,
  sourceY: t,
  sourcePosition: n = K.Bottom,
  targetX: r,
  targetY: o,
  targetPosition: i = K.Top,
  curvature: s = 0.25,
}) {
  const [a, l] = Ly({ pos: n, x1: e, y1: t, x2: r, y2: o, c: s }),
    [u, c] = Ly({ pos: i, x1: r, y1: o, x2: e, y2: t, c: s }),
    [f, d, m, y] = sE({
      sourceX: e,
      sourceY: t,
      targetX: r,
      targetY: o,
      sourceControlX: a,
      sourceControlY: l,
      targetControlX: u,
      targetControlY: c,
    });
  return [`M${e},${t} C${a},${l} ${u},${c} ${r},${o}`, f, d, m, y];
}
const Il = v.memo(
  ({
    sourceX: e,
    sourceY: t,
    targetX: n,
    targetY: r,
    sourcePosition: o = K.Bottom,
    targetPosition: i = K.Top,
    label: s,
    labelStyle: a,
    labelShowBg: l,
    labelBgStyle: u,
    labelBgPadding: c,
    labelBgBorderRadius: f,
    style: d,
    markerEnd: m,
    markerStart: y,
    pathOptions: g,
    interactionWidth: w,
  }) => {
    const [h, p, x] = lE({
      sourceX: e,
      sourceY: t,
      sourcePosition: o,
      targetX: n,
      targetY: r,
      targetPosition: i,
      curvature: g == null ? void 0 : g.curvature,
    });
    return L.createElement(Fs, {
      path: h,
      labelX: p,
      labelY: x,
      label: s,
      labelStyle: a,
      labelShowBg: l,
      labelBgStyle: u,
      labelBgPadding: c,
      labelBgBorderRadius: f,
      style: d,
      markerEnd: m,
      markerStart: y,
      interactionWidth: w,
    });
  },
);
Il.displayName = "BezierEdge";
const lp = v.createContext(null),
  t4 = lp.Provider;
lp.Consumer;
const n4 = () => v.useContext(lp),
  r4 = (e) => "id" in e && "source" in e && "target" in e,
  o4 = ({ source: e, sourceHandle: t, target: n, targetHandle: r }) =>
    `reactflow__edge-${e}${t || ""}-${n}${r || ""}`,
  id = (e, t) =>
    typeof e > "u"
      ? ""
      : typeof e == "string"
        ? e
        : `${t ? `${t}__` : ""}${Object.keys(e)
            .sort()
            .map((r) => `${r}=${e[r]}`)
            .join("&")}`,
  i4 = (e, t) =>
    t.some(
      (n) =>
        n.source === e.source &&
        n.target === e.target &&
        (n.sourceHandle === e.sourceHandle || (!n.sourceHandle && !e.sourceHandle)) &&
        (n.targetHandle === e.targetHandle || (!n.targetHandle && !e.targetHandle)),
    ),
  s4 = (e, t) => {
    if (!e.source || !e.target) return t;
    let n;
    return r4(e) ? (n = { ...e }) : (n = { ...e, id: o4(e) }), i4(n, t) ? t : t.concat(n);
  },
  sd = ({ x: e, y: t }, [n, r, o], i, [s, a]) => {
    const l = { x: (e - n) / o, y: (t - r) / o };
    return i ? { x: s * Math.round(l.x / s), y: a * Math.round(l.y / a) } : l;
  },
  uE = ({ x: e, y: t }, [n, r, o]) => ({ x: e * o + n, y: t * o + r }),
  _r = (e, t = [0, 0]) => {
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
  bu = (e, t = [0, 0]) => {
    if (e.length === 0) return { x: 0, y: 0, width: 0, height: 0 };
    const n = e.reduce(
      (r, o) => {
        const { x: i, y: s } = _r(o, t).positionAbsolute;
        return tE(r, ys({ x: i, y: s, width: o.width || 0, height: o.height || 0 }));
      },
      { x: 1 / 0, y: 1 / 0, x2: -1 / 0, y2: -1 / 0 },
    );
    return nE(n);
  },
  cE = (e, t, [n, r, o] = [0, 0, 1], i = !1, s = !1, a = [0, 0]) => {
    const l = { x: (t.x - n) / o, y: (t.y - r) / o, width: t.width / o, height: t.height / o },
      u = [];
    return (
      e.forEach((c) => {
        const { width: f, height: d, selectable: m = !0, hidden: y = !1 } = c;
        if ((s && !m) || y) return !1;
        const { positionAbsolute: g } = _r(c, a),
          w = { x: g.x, y: g.y, width: f || 0, height: d || 0 },
          h = rd(l, w),
          p = typeof f > "u" || typeof d > "u" || f === null || d === null,
          x = i && h > 0,
          S = (f || 0) * (d || 0);
        (p || x || h >= S || c.dragging) && u.push(c);
      }),
      u
    );
  },
  fE = (e, t) => {
    const n = e.map((r) => r.id);
    return t.filter((r) => n.includes(r.source) || n.includes(r.target));
  },
  dE = (e, t, n, r, o, i = 0.1) => {
    const s = t / (e.width * (1 + i)),
      a = n / (e.height * (1 + i)),
      l = Math.min(s, a),
      u = Uo(l, r, o),
      c = e.x + e.width / 2,
      f = e.y + e.height / 2,
      d = t / 2 - c * u,
      m = n / 2 - f * u;
    return { x: d, y: m, zoom: u };
  },
  mr = (e, t = 0) => e.transition().duration(t);
function Vy(e, t, n, r) {
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
function a4(e, t, n, r, o, i) {
  const { x: s, y: a } = Zn(e),
    u = t.elementsFromPoint(s, a).find((y) => y.classList.contains("react-flow__handle"));
  if (u) {
    const y = u.getAttribute("data-nodeid");
    if (y) {
      const g = up(void 0, u),
        w = u.getAttribute("data-handleid"),
        h = i({ nodeId: y, id: w, type: g });
      if (h) {
        const p = o.find((x) => x.nodeId === y && x.type === g && x.id === w);
        return {
          handle: {
            id: w,
            type: g,
            nodeId: y,
            x: (p == null ? void 0 : p.x) || n.x,
            y: (p == null ? void 0 : p.y) || n.y,
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
      const g = Math.sqrt((y.x - n.x) ** 2 + (y.y - n.y) ** 2);
      if (g <= r) {
        const w = i(y);
        g <= f &&
          (g < f
            ? (c = [{ handle: y, validHandleResult: w }])
            : g === f && c.push({ handle: y, validHandleResult: w }),
          (f = g));
      }
    }),
    !c.length)
  )
    return { handle: null, validHandleResult: hE() };
  if (c.length === 1) return c[0];
  const d = c.some(({ validHandleResult: y }) => y.isValid),
    m = c.some(({ handle: y }) => y.type === "target");
  return (
    c.find(({ handle: y, validHandleResult: g }) =>
      m ? y.type === "target" : d ? g.isValid : !0,
    ) || c[0]
  );
}
const l4 = { source: null, target: null, sourceHandle: null, targetHandle: null },
  hE = () => ({ handleDomNode: null, isValid: !1, connection: l4, endHandle: null });
function pE(e, t, n, r, o, i, s) {
  const a = o === "target",
    l = s.querySelector(
      `.react-flow__handle[data-id="${e == null ? void 0 : e.nodeId}-${e == null ? void 0 : e.id}-${e == null ? void 0 : e.type}"]`,
    ),
    u = { ...hE(), handleDomNode: l };
  if (l) {
    const c = up(void 0, l),
      f = l.getAttribute("data-nodeid"),
      d = l.getAttribute("data-handleid"),
      m = l.classList.contains("connectable"),
      y = l.classList.contains("connectableend"),
      g = {
        source: a ? f : n,
        sourceHandle: a ? d : r,
        target: a ? n : f,
        targetHandle: a ? r : d,
      };
    (u.connection = g),
      m &&
        y &&
        (t === Lr.Strict ? (a && c === "source") || (!a && c === "target") : f !== n || d !== r) &&
        ((u.endHandle = { nodeId: f, handleId: d, type: c }), (u.isValid = i(g)));
  }
  return u;
}
function u4({ nodes: e, nodeId: t, handleId: n, handleType: r }) {
  return e.reduce((o, i) => {
    if (i[Te]) {
      const { handleBounds: s } = i[Te];
      let a = [],
        l = [];
      s && ((a = Vy(i, s, "source", `${t}-${n}-${r}`)), (l = Vy(i, s, "target", `${t}-${n}-${r}`))),
        o.push(...a, ...l);
    }
    return o;
  }, []);
}
function up(e, t) {
  return (
    e ||
    (t != null && t.classList.contains("target")
      ? "target"
      : t != null && t.classList.contains("source")
        ? "source"
        : null)
  );
}
function Nc(e) {
  e == null ||
    e.classList.remove(
      "valid",
      "connecting",
      "react-flow__handle-valid",
      "react-flow__handle-connecting",
    );
}
function c4(e, t) {
  let n = null;
  return t ? (n = "valid") : e && !t && (n = "invalid"), n;
}
function mE({
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
  const c = eE(e.target),
    {
      connectionMode: f,
      domNode: d,
      autoPanOnConnect: m,
      connectionRadius: y,
      onConnectStart: g,
      panBy: w,
      getNodes: h,
      cancelConnection: p,
    } = i();
  let x = 0,
    S;
  const { x: E, y: _ } = Zn(e),
    k = c == null ? void 0 : c.elementFromPoint(E, _),
    N = up(l, k),
    A = d == null ? void 0 : d.getBoundingClientRect();
  if (!A || !N) return;
  let R,
    O = Zn(e, A),
    j = !1,
    $ = null,
    b = !1,
    I = null;
  const P = u4({ nodes: h(), nodeId: n, handleId: t, handleType: N }),
    V = () => {
      if (!m) return;
      const [D, F] = JS(O, A);
      w({ x: D, y: F }), (x = requestAnimationFrame(V));
    };
  s({
    connectionPosition: O,
    connectionStatus: null,
    connectionNodeId: n,
    connectionHandleId: t,
    connectionHandleType: N,
    connectionStartHandle: { nodeId: n, handleId: t, type: N },
    connectionEndHandle: null,
  }),
    g == null || g(e, { nodeId: n, handleId: t, handleType: N });
  function M(D) {
    const { transform: F } = i();
    O = Zn(D, A);
    const { handle: z, validHandleResult: W } = a4(D, c, sd(O, F, !1, [1, 1]), y, P, (H) =>
      pE(H, f, n, t, o ? "target" : "source", a, c),
    );
    if (
      ((S = z),
      j || (V(), (j = !0)),
      (I = W.handleDomNode),
      ($ = W.connection),
      (b = W.isValid),
      s({
        connectionPosition: S && b ? uE({ x: S.x, y: S.y }, F) : O,
        connectionStatus: c4(!!S, b),
        connectionEndHandle: W.endHandle,
      }),
      !S && !b && !I)
    )
      return Nc(R);
    $.source !== $.target &&
      I &&
      (Nc(R),
      (R = I),
      I.classList.add("connecting", "react-flow__handle-connecting"),
      I.classList.toggle("valid", b),
      I.classList.toggle("react-flow__handle-valid", b));
  }
  function T(D) {
    var F, z;
    (S || I) && $ && b && (r == null || r($)),
      (z = (F = i()).onConnectEnd) == null || z.call(F, D),
      l && (u == null || u(D)),
      Nc(R),
      p(),
      cancelAnimationFrame(x),
      (j = !1),
      (b = !1),
      ($ = null),
      (I = null),
      c.removeEventListener("mousemove", M),
      c.removeEventListener("mouseup", T),
      c.removeEventListener("touchmove", M),
      c.removeEventListener("touchend", T);
  }
  c.addEventListener("mousemove", M),
    c.addEventListener("mouseup", T),
    c.addEventListener("touchmove", M),
    c.addEventListener("touchend", T);
}
const Oy = () => !0,
  f4 = (e) => ({
    connectionStartHandle: e.connectionStartHandle,
    connectOnClick: e.connectOnClick,
    noPanClassName: e.noPanClassName,
  }),
  d4 = (e, t, n) => (r) => {
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
  gE = v.forwardRef(
    (
      {
        type: e = "source",
        position: t = K.Top,
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
      m,
    ) => {
      var A, R;
      const y = s || null,
        g = e === "target",
        w = Ae(),
        h = n4(),
        { connectOnClick: p, noPanClassName: x } = fe(f4, je),
        { connecting: S, clickConnecting: E } = fe(d4(h, y, e), je);
      h || (R = (A = w.getState()).onError) == null || R.call(A, "010", kn.error010());
      const _ = (O) => {
          const { defaultEdgeOptions: j, onConnect: $, hasDefaultEdges: b } = w.getState(),
            I = { ...j, ...O };
          if (b) {
            const { edges: P, setEdges: V } = w.getState();
            V(s4(I, P));
          }
          $ == null || $(I), a == null || a(I);
        },
        k = (O) => {
          if (!h) return;
          const j = oE(O);
          o &&
            ((j && O.button === 0) || !j) &&
            mE({
              event: O,
              handleId: y,
              nodeId: h,
              onConnect: _,
              isTarget: g,
              getState: w.getState,
              setState: w.setState,
              isValidConnection: n || w.getState().isValidConnection || Oy,
            }),
            j ? c == null || c(O) : f == null || f(O);
        },
        N = (O) => {
          const {
            onClickConnectStart: j,
            onClickConnectEnd: $,
            connectionClickStartHandle: b,
            connectionMode: I,
            isValidConnection: P,
          } = w.getState();
          if (!h || (!b && !o)) return;
          if (!b) {
            j == null || j(O, { nodeId: h, handleId: y, handleType: e }),
              w.setState({ connectionClickStartHandle: { nodeId: h, type: e, handleId: y } });
            return;
          }
          const V = eE(O.target),
            M = n || P || Oy,
            { connection: T, isValid: D } = pE(
              { nodeId: h, id: y, type: e },
              I,
              b.nodeId,
              b.handleId || null,
              b.type,
              M,
              V,
            );
          D && _(T), $ == null || $(O), w.setState({ connectionClickStartHandle: null });
        };
      return L.createElement(
        "div",
        {
          "data-handleid": y,
          "data-nodeid": h,
          "data-handlepos": t,
          "data-id": `${h}-${y}-${e}`,
          className: He([
            "react-flow__handle",
            `react-flow__handle-${t}`,
            "nodrag",
            x,
            u,
            {
              source: !g,
              target: g,
              connectable: r,
              connectablestart: o,
              connectableend: i,
              connecting: E,
              connectionindicator: r && ((o && !S) || (i && S)),
            },
          ]),
          onMouseDown: k,
          onTouchStart: k,
          onClick: p ? N : void 0,
          ref: m,
          ...d,
        },
        l,
      );
    },
  );
gE.displayName = "Handle";
var ws = v.memo(gE);
const yE = ({
  data: e,
  isConnectable: t,
  targetPosition: n = K.Top,
  sourcePosition: r = K.Bottom,
}) =>
  L.createElement(
    L.Fragment,
    null,
    L.createElement(ws, { type: "target", position: n, isConnectable: t }),
    e == null ? void 0 : e.label,
    L.createElement(ws, { type: "source", position: r, isConnectable: t }),
  );
yE.displayName = "DefaultNode";
var ad = v.memo(yE);
const vE = ({ data: e, isConnectable: t, sourcePosition: n = K.Bottom }) =>
  L.createElement(
    L.Fragment,
    null,
    e == null ? void 0 : e.label,
    L.createElement(ws, { type: "source", position: n, isConnectable: t }),
  );
vE.displayName = "InputNode";
var xE = v.memo(vE);
const wE = ({ data: e, isConnectable: t, targetPosition: n = K.Top }) =>
  L.createElement(
    L.Fragment,
    null,
    L.createElement(ws, { type: "target", position: n, isConnectable: t }),
    e == null ? void 0 : e.label,
  );
wE.displayName = "OutputNode";
var SE = v.memo(wE);
const cp = () => null;
cp.displayName = "GroupNode";
const h4 = (e) => ({
    selectedNodes: e.getNodes().filter((t) => t.selected),
    selectedEdges: e.edges.filter((t) => t.selected).map((t) => ({ ...t })),
  }),
  ya = (e) => e.id;
function p4(e, t) {
  return (
    je(e.selectedNodes.map(ya), t.selectedNodes.map(ya)) &&
    je(e.selectedEdges.map(ya), t.selectedEdges.map(ya))
  );
}
const EE = v.memo(({ onSelectionChange: e }) => {
  const t = Ae(),
    { selectedNodes: n, selectedEdges: r } = fe(h4, p4);
  return (
    v.useEffect(() => {
      const o = { nodes: n, edges: r };
      e == null || e(o), t.getState().onSelectionChange.forEach((i) => i(o));
    }, [n, r, e]),
    null
  );
});
EE.displayName = "SelectionListener";
const m4 = (e) => !!e.onSelectionChange;
function g4({ onSelectionChange: e }) {
  const t = fe(m4);
  return e || t ? L.createElement(EE, { onSelectionChange: e }) : null;
}
const y4 = (e) => ({
  setNodes: e.setNodes,
  setEdges: e.setEdges,
  setDefaultNodesAndEdges: e.setDefaultNodesAndEdges,
  setMinZoom: e.setMinZoom,
  setMaxZoom: e.setMaxZoom,
  setTranslateExtent: e.setTranslateExtent,
  setNodeExtent: e.setNodeExtent,
  reset: e.reset,
});
function Yr(e, t) {
  v.useEffect(() => {
    typeof e < "u" && t(e);
  }, [e]);
}
function ne(e, t, n) {
  v.useEffect(() => {
    typeof t < "u" && n({ [e]: t });
  }, [t]);
}
const v4 = ({
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
    edgesUpdatable: m,
    elevateNodesOnSelect: y,
    minZoom: g,
    maxZoom: w,
    nodeExtent: h,
    onNodesChange: p,
    onEdgesChange: x,
    elementsSelectable: S,
    connectionMode: E,
    snapGrid: _,
    snapToGrid: k,
    translateExtent: N,
    connectOnClick: A,
    defaultEdgeOptions: R,
    fitView: O,
    fitViewOptions: j,
    onNodesDelete: $,
    onEdgesDelete: b,
    onNodeDrag: I,
    onNodeDragStart: P,
    onNodeDragStop: V,
    onSelectionDrag: M,
    onSelectionDragStart: T,
    onSelectionDragStop: D,
    noPanClassName: F,
    nodeOrigin: z,
    rfId: W,
    autoPanOnConnect: H,
    autoPanOnNodeDrag: Y,
    onError: U,
    connectionRadius: X,
    isValidConnection: te,
    nodeDragThreshold: q,
  }) => {
    const {
        setNodes: J,
        setEdges: oe,
        setDefaultNodesAndEdges: pe,
        setMinZoom: Ce,
        setMaxZoom: ae,
        setTranslateExtent: de,
        setNodeExtent: Ue,
        reset: ue,
      } = fe(y4, je),
      Z = Ae();
    return (
      v.useEffect(() => {
        const qe = r == null ? void 0 : r.map((nn) => ({ ...nn, ...R }));
        return (
          pe(n, qe),
          () => {
            ue();
          }
        );
      }, []),
      ne("defaultEdgeOptions", R, Z.setState),
      ne("connectionMode", E, Z.setState),
      ne("onConnect", o, Z.setState),
      ne("onConnectStart", i, Z.setState),
      ne("onConnectEnd", s, Z.setState),
      ne("onClickConnectStart", a, Z.setState),
      ne("onClickConnectEnd", l, Z.setState),
      ne("nodesDraggable", u, Z.setState),
      ne("nodesConnectable", c, Z.setState),
      ne("nodesFocusable", f, Z.setState),
      ne("edgesFocusable", d, Z.setState),
      ne("edgesUpdatable", m, Z.setState),
      ne("elementsSelectable", S, Z.setState),
      ne("elevateNodesOnSelect", y, Z.setState),
      ne("snapToGrid", k, Z.setState),
      ne("snapGrid", _, Z.setState),
      ne("onNodesChange", p, Z.setState),
      ne("onEdgesChange", x, Z.setState),
      ne("connectOnClick", A, Z.setState),
      ne("fitViewOnInit", O, Z.setState),
      ne("fitViewOnInitOptions", j, Z.setState),
      ne("onNodesDelete", $, Z.setState),
      ne("onEdgesDelete", b, Z.setState),
      ne("onNodeDrag", I, Z.setState),
      ne("onNodeDragStart", P, Z.setState),
      ne("onNodeDragStop", V, Z.setState),
      ne("onSelectionDrag", M, Z.setState),
      ne("onSelectionDragStart", T, Z.setState),
      ne("onSelectionDragStop", D, Z.setState),
      ne("noPanClassName", F, Z.setState),
      ne("nodeOrigin", z, Z.setState),
      ne("rfId", W, Z.setState),
      ne("autoPanOnConnect", H, Z.setState),
      ne("autoPanOnNodeDrag", Y, Z.setState),
      ne("onError", U, Z.setState),
      ne("connectionRadius", X, Z.setState),
      ne("isValidConnection", te, Z.setState),
      ne("nodeDragThreshold", q, Z.setState),
      Yr(e, J),
      Yr(t, oe),
      Yr(g, Ce),
      Yr(w, ae),
      Yr(N, de),
      Yr(h, Ue),
      null
    );
  },
  jy = { display: "none" },
  x4 = {
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
  CE = "react-flow__node-desc",
  bE = "react-flow__edge-desc",
  w4 = "react-flow__aria-live",
  S4 = (e) => e.ariaLiveMessage;
function E4({ rfId: e }) {
  const t = fe(S4);
  return L.createElement(
    "div",
    { id: `${w4}-${e}`, "aria-live": "assertive", "aria-atomic": "true", style: x4 },
    t,
  );
}
function C4({ rfId: e, disableKeyboardA11y: t }) {
  return L.createElement(
    L.Fragment,
    null,
    L.createElement(
      "div",
      { id: `${CE}-${e}`, style: jy },
      "Press enter or space to select a node.",
      !t && "You can then use the arrow keys to move the node around.",
      " Press delete to remove it and escape to cancel.",
      " ",
    ),
    L.createElement(
      "div",
      { id: `${bE}-${e}`, style: jy },
      "Press enter or space to select an edge. You can then press delete to remove it or escape to cancel.",
    ),
    !t && L.createElement(E4, { rfId: e }),
  );
}
var Ss = (e = null, t = { actInsideInputWithModifier: !0 }) => {
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
        const c = (m) => {
            if (
              ((o.current = m.ctrlKey || m.metaKey || m.shiftKey),
              (!o.current || (o.current && !t.actInsideInputWithModifier)) && od(m))
            )
              return !1;
            const g = zy(m.code, a);
            i.current.add(m[g]), Fy(s, i.current, !1) && (m.preventDefault(), r(!0));
          },
          f = (m) => {
            if ((!o.current || (o.current && !t.actInsideInputWithModifier)) && od(m)) return !1;
            const g = zy(m.code, a);
            Fy(s, i.current, !0) ? (r(!1), i.current.clear()) : i.current.delete(m[g]),
              m.key === "Meta" && i.current.clear(),
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
function Fy(e, t, n) {
  return e.filter((r) => n || r.length === t.size).some((r) => r.every((o) => t.has(o)));
}
function zy(e, t) {
  return t.includes(e) ? "code" : "key";
}
function kE(e, t, n, r) {
  var a, l;
  const o = e.parentNode || e.parentId;
  if (!o) return n;
  const i = t.get(o),
    s = _r(i, r);
  return kE(
    i,
    t,
    {
      x: (n.x ?? 0) + s.x,
      y: (n.y ?? 0) + s.y,
      z:
        (((a = i[Te]) == null ? void 0 : a.z) ?? 0) > (n.z ?? 0)
          ? (((l = i[Te]) == null ? void 0 : l.z) ?? 0)
          : (n.z ?? 0),
    },
    r,
  );
}
function TE(e, t, n) {
  e.forEach((r) => {
    var i;
    const o = r.parentNode || r.parentId;
    if (o && !e.has(o)) throw new Error(`Parent node ${o} not found`);
    if (o || (n != null && n[r.id])) {
      const {
        x: s,
        y: a,
        z: l,
      } = kE(r, e, { ...r.position, z: ((i = r[Te]) == null ? void 0 : i.z) ?? 0 }, t);
      (r.positionAbsolute = { x: s, y: a }),
        (r[Te].z = l),
        n != null && n[r.id] && (r[Te].isParent = !0);
    }
  });
}
function Pc(e, t, n, r) {
  const o = new Map(),
    i = {},
    s = r ? 1e3 : 0;
  return (
    e.forEach((a) => {
      var m;
      const l = (kt(a.zIndex) ? a.zIndex : 0) + (a.selected ? s : 0),
        u = t.get(a.id),
        c = { ...a, positionAbsolute: { x: a.position.x, y: a.position.y } },
        f = a.parentNode || a.parentId;
      f && (i[f] = !0);
      const d = (u == null ? void 0 : u.type) && (u == null ? void 0 : u.type) !== a.type;
      Object.defineProperty(c, Te, {
        enumerable: !1,
        value: {
          handleBounds: d || (m = u == null ? void 0 : u[Te]) == null ? void 0 : m.handleBounds,
          z: l,
        },
      }),
        o.set(a.id, c);
    }),
    TE(o, n, i),
    o
  );
}
function _E(e, t = {}) {
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
        var p;
        const h = t.includeHiddenNodes ? w.width && w.height : !w.hidden;
        return (p = t.nodes) != null && p.length ? h && t.nodes.some((x) => x.id === w.id) : h;
      }),
      g = y.every((w) => w.width && w.height);
    if (y.length > 0 && g) {
      const w = bu(y, f),
        { x: h, y: p, zoom: x } = dE(w, r, o, t.minZoom ?? i, t.maxZoom ?? s, t.padding ?? 0.1),
        S = yn.translate(h, p).scale(x);
      return (
        typeof t.duration == "number" && t.duration > 0
          ? a.transform(mr(l, t.duration), S)
          : a.transform(l, S),
        !0
      );
    }
  }
  return !1;
}
function b4(e, t) {
  return (
    e.forEach((n) => {
      const r = t.get(n.id);
      r && t.set(r.id, { ...r, [Te]: r[Te], selected: n.selected });
    }),
    new Map(t)
  );
}
function k4(e, t) {
  return t.map((n) => {
    const r = e.find((o) => o.id === n.id);
    return r && (n.selected = r.selected), n;
  });
}
function va({ changedNodes: e, changedEdges: t, get: n, set: r }) {
  const {
    nodeInternals: o,
    edges: i,
    onNodesChange: s,
    onEdgesChange: a,
    hasDefaultNodes: l,
    hasDefaultEdges: u,
  } = n();
  e != null && e.length && (l && r({ nodeInternals: b4(e, o) }), s == null || s(e)),
    t != null && t.length && (u && r({ edges: k4(t, i) }), a == null || a(t));
}
const Xr = () => {},
  T4 = {
    zoomIn: Xr,
    zoomOut: Xr,
    zoomTo: Xr,
    getZoom: () => 1,
    setViewport: Xr,
    getViewport: () => ({ x: 0, y: 0, zoom: 1 }),
    fitView: () => !1,
    setCenter: Xr,
    fitBounds: Xr,
    project: (e) => e,
    screenToFlowPosition: (e) => e,
    flowToScreenPosition: (e) => e,
    viewportInitialized: !1,
  },
  _4 = (e) => ({ d3Zoom: e.d3Zoom, d3Selection: e.d3Selection }),
  N4 = () => {
    const e = Ae(),
      { d3Zoom: t, d3Selection: n } = fe(_4, je);
    return v.useMemo(
      () =>
        n && t
          ? {
              zoomIn: (o) => t.scaleBy(mr(n, o == null ? void 0 : o.duration), 1.2),
              zoomOut: (o) => t.scaleBy(mr(n, o == null ? void 0 : o.duration), 1 / 1.2),
              zoomTo: (o, i) => t.scaleTo(mr(n, i == null ? void 0 : i.duration), o),
              getZoom: () => e.getState().transform[2],
              setViewport: (o, i) => {
                const [s, a, l] = e.getState().transform,
                  u = yn.translate(o.x ?? s, o.y ?? a).scale(o.zoom ?? l);
                t.transform(mr(n, i == null ? void 0 : i.duration), u);
              },
              getViewport: () => {
                const [o, i, s] = e.getState().transform;
                return { x: o, y: i, zoom: s };
              },
              fitView: (o) => _E(e.getState, o),
              setCenter: (o, i, s) => {
                const { width: a, height: l, maxZoom: u } = e.getState(),
                  c = typeof (s == null ? void 0 : s.zoom) < "u" ? s.zoom : u,
                  f = a / 2 - o * c,
                  d = l / 2 - i * c,
                  m = yn.translate(f, d).scale(c);
                t.transform(mr(n, s == null ? void 0 : s.duration), m);
              },
              fitBounds: (o, i) => {
                const { width: s, height: a, minZoom: l, maxZoom: u } = e.getState(),
                  {
                    x: c,
                    y: f,
                    zoom: d,
                  } = dE(o, s, a, l, u, (i == null ? void 0 : i.padding) ?? 0.1),
                  m = yn.translate(c, f).scale(d);
                t.transform(mr(n, i == null ? void 0 : i.duration), m);
              },
              project: (o) => {
                const { transform: i, snapToGrid: s, snapGrid: a } = e.getState();
                return (
                  console.warn(
                    "[DEPRECATED] `project` is deprecated. Instead use `screenToFlowPosition`. There is no need to subtract the react flow bounds anymore! https://reactflow.dev/api-reference/types/react-flow-instance#screen-to-flow-position",
                  ),
                  sd(o, i, s, a)
                );
              },
              screenToFlowPosition: (o) => {
                const { transform: i, snapToGrid: s, snapGrid: a, domNode: l } = e.getState();
                if (!l) return o;
                const { x: u, y: c } = l.getBoundingClientRect(),
                  f = { x: o.x - u, y: o.y - c };
                return sd(f, i, s, a);
              },
              flowToScreenPosition: (o) => {
                const { transform: i, domNode: s } = e.getState();
                if (!s) return o;
                const { x: a, y: l } = s.getBoundingClientRect(),
                  u = uE(o, i);
                return { x: u.x + a, y: u.y + l };
              },
              viewportInitialized: !0,
            }
          : T4,
      [t, n],
    );
  };
function ku() {
  const e = N4(),
    t = Ae(),
    n = v.useCallback(
      () =>
        t
          .getState()
          .getNodes()
          .map((g) => ({ ...g })),
      [],
    ),
    r = v.useCallback((g) => t.getState().nodeInternals.get(g), []),
    o = v.useCallback(() => {
      const { edges: g = [] } = t.getState();
      return g.map((w) => ({ ...w }));
    }, []),
    i = v.useCallback((g) => {
      const { edges: w = [] } = t.getState();
      return w.find((h) => h.id === g);
    }, []),
    s = v.useCallback((g) => {
      const { getNodes: w, setNodes: h, hasDefaultNodes: p, onNodesChange: x } = t.getState(),
        S = w(),
        E = typeof g == "function" ? g(S) : g;
      if (p) h(E);
      else if (x) {
        const _ =
          E.length === 0
            ? S.map((k) => ({ type: "remove", id: k.id }))
            : E.map((k) => ({ item: k, type: "reset" }));
        x(_);
      }
    }, []),
    a = v.useCallback((g) => {
      const { edges: w = [], setEdges: h, hasDefaultEdges: p, onEdgesChange: x } = t.getState(),
        S = typeof g == "function" ? g(w) : g;
      if (p) h(S);
      else if (x) {
        const E =
          S.length === 0
            ? w.map((_) => ({ type: "remove", id: _.id }))
            : S.map((_) => ({ item: _, type: "reset" }));
        x(E);
      }
    }, []),
    l = v.useCallback((g) => {
      const w = Array.isArray(g) ? g : [g],
        { getNodes: h, setNodes: p, hasDefaultNodes: x, onNodesChange: S } = t.getState();
      if (x) {
        const _ = [...h(), ...w];
        p(_);
      } else if (S) {
        const E = w.map((_) => ({ item: _, type: "add" }));
        S(E);
      }
    }, []),
    u = v.useCallback((g) => {
      const w = Array.isArray(g) ? g : [g],
        { edges: h = [], setEdges: p, hasDefaultEdges: x, onEdgesChange: S } = t.getState();
      if (x) p([...h, ...w]);
      else if (S) {
        const E = w.map((_) => ({ item: _, type: "add" }));
        S(E);
      }
    }, []),
    c = v.useCallback(() => {
      const { getNodes: g, edges: w = [], transform: h } = t.getState(),
        [p, x, S] = h;
      return {
        nodes: g().map((E) => ({ ...E })),
        edges: w.map((E) => ({ ...E })),
        viewport: { x: p, y: x, zoom: S },
      };
    }, []),
    f = v.useCallback(({ nodes: g, edges: w }) => {
      const {
          nodeInternals: h,
          getNodes: p,
          edges: x,
          hasDefaultNodes: S,
          hasDefaultEdges: E,
          onNodesDelete: _,
          onEdgesDelete: k,
          onNodesChange: N,
          onEdgesChange: A,
        } = t.getState(),
        R = (g || []).map((I) => I.id),
        O = (w || []).map((I) => I.id),
        j = p().reduce((I, P) => {
          const V = P.parentNode || P.parentId,
            M = !R.includes(P.id) && V && I.find((D) => D.id === V);
          return (
            (typeof P.deletable == "boolean" ? P.deletable : !0) &&
              (R.includes(P.id) || M) &&
              I.push(P),
            I
          );
        }, []),
        $ = x.filter((I) => (typeof I.deletable == "boolean" ? I.deletable : !0)),
        b = $.filter((I) => O.includes(I.id));
      if (j || b) {
        const I = fE(j, $),
          P = [...b, ...I],
          V = P.reduce((M, T) => (M.includes(T.id) || M.push(T.id), M), []);
        if (
          ((E || S) &&
            (E && t.setState({ edges: x.filter((M) => !V.includes(M.id)) }),
            S &&
              (j.forEach((M) => {
                h.delete(M.id);
              }),
              t.setState({ nodeInternals: new Map(h) }))),
          V.length > 0 && (k == null || k(P), A && A(V.map((M) => ({ id: M, type: "remove" })))),
          j.length > 0 && (_ == null || _(j), N))
        ) {
          const M = j.map((T) => ({ id: T.id, type: "remove" }));
          N(M);
        }
      }
    }, []),
    d = v.useCallback((g) => {
      const w = YL(g),
        h = w ? null : t.getState().nodeInternals.get(g.id);
      return !w && !h ? [null, null, w] : [w ? g : Ay(h), h, w];
    }, []),
    m = v.useCallback((g, w = !0, h) => {
      const [p, x, S] = d(g);
      return p
        ? (h || t.getState().getNodes()).filter((E) => {
            if (!S && (E.id === x.id || !E.positionAbsolute)) return !1;
            const _ = Ay(E),
              k = rd(_, p);
            return (w && k > 0) || k >= p.width * p.height;
          })
        : [];
    }, []),
    y = v.useCallback((g, w, h = !0) => {
      const [p] = d(g);
      if (!p) return !1;
      const x = rd(p, w);
      return (h && x > 0) || x >= p.width * p.height;
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
      getIntersectingNodes: m,
      isNodeIntersecting: y,
    }),
    [e, n, r, o, i, s, a, l, u, c, f, m, y],
  );
}
const P4 = { actInsideInputWithModifier: !1 };
var M4 = ({ deleteKeyCode: e, multiSelectionKeyCode: t }) => {
  const n = Ae(),
    { deleteElements: r } = ku(),
    o = Ss(e, P4),
    i = Ss(t);
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
function A4(e) {
  const t = Ae();
  v.useEffect(() => {
    let n;
    const r = () => {
      var i, s;
      if (!e.current) return;
      const o = rp(e.current);
      (o.height === 0 || o.width === 0) &&
        ((s = (i = t.getState()).onError) == null || s.call(i, "004", kn.error004())),
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
const fp = { position: "absolute", width: "100%", height: "100%", top: 0, left: 0 },
  R4 = (e, t) => e.x !== t.x || e.y !== t.y || e.zoom !== t.k,
  xa = (e) => ({ x: e.x, y: e.y, zoom: e.k }),
  Zr = (e, t) => e.target.closest(`.${t}`),
  $y = (e, t) => t === 2 && Array.isArray(e) && e.includes(2),
  By = (e) => {
    const t = e.ctrlKey && Rl() ? 10 : 1;
    return -e.deltaY * (e.deltaMode === 1 ? 0.05 : e.deltaMode ? 1 : 0.002) * t;
  },
  D4 = (e) => ({
    d3Zoom: e.d3Zoom,
    d3Selection: e.d3Selection,
    d3ZoomHandler: e.d3ZoomHandler,
    userSelectionActive: e.userSelectionActive,
  }),
  I4 = ({
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
    translateExtent: m,
    minZoom: y,
    maxZoom: g,
    zoomActivationKeyCode: w,
    preventScrolling: h = !0,
    children: p,
    noWheelClassName: x,
    noPanClassName: S,
  }) => {
    const E = v.useRef(),
      _ = Ae(),
      k = v.useRef(!1),
      N = v.useRef(!1),
      A = v.useRef(null),
      R = v.useRef({ x: 0, y: 0, zoom: 0 }),
      { d3Zoom: O, d3Selection: j, d3ZoomHandler: $, userSelectionActive: b } = fe(D4, je),
      I = Ss(w),
      P = v.useRef(0),
      V = v.useRef(!1),
      M = v.useRef();
    return (
      A4(A),
      v.useEffect(() => {
        if (A.current) {
          const T = A.current.getBoundingClientRect(),
            D = QS().scaleExtent([y, g]).translateExtent(m),
            F = Ct(A.current).call(D),
            z = yn.translate(d.x, d.y).scale(Uo(d.zoom, y, g)),
            W = [
              [0, 0],
              [T.width, T.height],
            ],
            H = D.constrain()(z, W, m);
          D.transform(F, H),
            D.wheelDelta(By),
            _.setState({
              d3Zoom: D,
              d3Selection: F,
              d3ZoomHandler: F.on("wheel.zoom"),
              transform: [H.x, H.y, H.k],
              domNode: A.current.closest(".react-flow"),
            });
        }
      }, []),
      v.useEffect(() => {
        j &&
          O &&
          (s && !I && !b
            ? j.on(
                "wheel.zoom",
                (T) => {
                  if (Zr(T, x)) return !1;
                  T.preventDefault(), T.stopImmediatePropagation();
                  const D = j.property("__zoom").k || 1;
                  if (T.ctrlKey && i) {
                    const te = It(T),
                      q = By(T),
                      J = D * Math.pow(2, q);
                    O.scaleTo(j, J, te, T);
                    return;
                  }
                  const F = T.deltaMode === 1 ? 20 : 1;
                  let z = l === Er.Vertical ? 0 : T.deltaX * F,
                    W = l === Er.Horizontal ? 0 : T.deltaY * F;
                  !Rl() && T.shiftKey && l !== Er.Vertical && ((z = T.deltaY * F), (W = 0)),
                    O.translateBy(j, -(z / D) * a, -(W / D) * a, { internal: !0 });
                  const H = xa(j.property("__zoom")),
                    {
                      onViewportChangeStart: Y,
                      onViewportChange: U,
                      onViewportChangeEnd: X,
                    } = _.getState();
                  clearTimeout(M.current),
                    V.current || ((V.current = !0), t == null || t(T, H), Y == null || Y(H)),
                    V.current &&
                      (e == null || e(T, H),
                      U == null || U(H),
                      (M.current = setTimeout(() => {
                        n == null || n(T, H), X == null || X(H), (V.current = !1);
                      }, 150)));
                },
                { passive: !1 },
              )
            : typeof $ < "u" &&
              j.on(
                "wheel.zoom",
                function (T, D) {
                  if ((!h && T.type === "wheel" && !T.ctrlKey) || Zr(T, x)) return null;
                  T.preventDefault(), $.call(this, T, D);
                },
                { passive: !1 },
              ));
      }, [b, s, l, j, O, $, I, i, h, x, t, e, n]),
      v.useEffect(() => {
        O &&
          O.on("start", (T) => {
            var z, W;
            if (!T.sourceEvent || T.sourceEvent.internal) return null;
            P.current = (z = T.sourceEvent) == null ? void 0 : z.button;
            const { onViewportChangeStart: D } = _.getState(),
              F = xa(T.transform);
            (k.current = !0),
              (R.current = F),
              ((W = T.sourceEvent) == null ? void 0 : W.type) === "mousedown" &&
                _.setState({ paneDragging: !0 }),
              D == null || D(F),
              t == null || t(T.sourceEvent, F);
          });
      }, [O, t]),
      v.useEffect(() => {
        O &&
          (b && !k.current
            ? O.on("zoom", null)
            : b ||
              O.on("zoom", (T) => {
                var F;
                const { onViewportChange: D } = _.getState();
                if (
                  (_.setState({ transform: [T.transform.x, T.transform.y, T.transform.k] }),
                  (N.current = !!(r && $y(f, P.current ?? 0))),
                  (e || D) && !((F = T.sourceEvent) != null && F.internal))
                ) {
                  const z = xa(T.transform);
                  D == null || D(z), e == null || e(T.sourceEvent, z);
                }
              }));
      }, [b, O, e, f, r]),
      v.useEffect(() => {
        O &&
          O.on("end", (T) => {
            if (!T.sourceEvent || T.sourceEvent.internal) return null;
            const { onViewportChangeEnd: D } = _.getState();
            if (
              ((k.current = !1),
              _.setState({ paneDragging: !1 }),
              r && $y(f, P.current ?? 0) && !N.current && r(T.sourceEvent),
              (N.current = !1),
              (n || D) && R4(R.current, T.transform))
            ) {
              const F = xa(T.transform);
              (R.current = F),
                clearTimeout(E.current),
                (E.current = setTimeout(
                  () => {
                    D == null || D(F), n == null || n(T.sourceEvent, F);
                  },
                  s ? 150 : 0,
                ));
            }
          });
      }, [O, s, f, n, r]),
      v.useEffect(() => {
        O &&
          O.filter((T) => {
            const D = I || o,
              F = i && T.ctrlKey;
            if (
              (f === !0 || (Array.isArray(f) && f.includes(1))) &&
              T.button === 1 &&
              T.type === "mousedown" &&
              (Zr(T, "react-flow__node") || Zr(T, "react-flow__edge"))
            )
              return !0;
            if (
              (!f && !D && !s && !u && !i) ||
              b ||
              (!u && T.type === "dblclick") ||
              (Zr(T, x) && T.type === "wheel") ||
              (Zr(T, S) && (T.type !== "wheel" || (s && T.type === "wheel" && !I))) ||
              (!i && T.ctrlKey && T.type === "wheel") ||
              (!D && !s && !F && T.type === "wheel") ||
              (!f && (T.type === "mousedown" || T.type === "touchstart")) ||
              (Array.isArray(f) && !f.includes(T.button) && T.type === "mousedown")
            )
              return !1;
            const z = (Array.isArray(f) && f.includes(T.button)) || !T.button || T.button <= 1;
            return (!T.ctrlKey || T.type === "wheel") && z;
          });
      }, [b, O, o, i, s, u, f, c, I]),
      L.createElement("div", { className: "react-flow__renderer", ref: A, style: fp }, p)
    );
  },
  L4 = (e) => ({
    userSelectionActive: e.userSelectionActive,
    userSelectionRect: e.userSelectionRect,
  });
function V4() {
  const { userSelectionActive: e, userSelectionRect: t } = fe(L4, je);
  return e && t
    ? L.createElement("div", {
        className: "react-flow__selection react-flow__container",
        style: { width: t.width, height: t.height, transform: `translate(${t.x}px, ${t.y}px)` },
      })
    : null;
}
function Hy(e, t) {
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
function NE(e, t) {
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
              s.expandParent && Hy(r, s);
            break;
          }
          case "dimensions": {
            typeof a.dimensions < "u" &&
              ((s.width = a.dimensions.width), (s.height = a.dimensions.height)),
              typeof a.updateStyle < "u" && (s.style = { ...(s.style || {}), ...a.dimensions }),
              typeof a.resizing == "boolean" && (s.resizing = a.resizing),
              s.expandParent && Hy(r, s);
            break;
          }
          case "remove":
            return r;
        }
    return r.push(s), r;
  }, n);
}
function PE(e, t) {
  return NE(e, t);
}
function O4(e, t) {
  return NE(e, t);
}
const On = (e, t) => ({ id: e, type: "select", selected: t });
function go(e, t) {
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
const Mc = (e, t) => (n) => {
    n.target === t.current && (e == null || e(n));
  },
  j4 = (e) => ({
    userSelectionActive: e.userSelectionActive,
    elementsSelectable: e.elementsSelectable,
    dragging: e.paneDragging,
  }),
  ME = v.memo(
    ({
      isSelecting: e,
      selectionMode: t = vs.Full,
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
        m = Ae(),
        y = v.useRef(0),
        g = v.useRef(0),
        w = v.useRef(),
        { userSelectionActive: h, elementsSelectable: p, dragging: x } = fe(j4, je),
        S = () => {
          m.setState({ userSelectionActive: !1, userSelectionRect: null }),
            (y.current = 0),
            (g.current = 0);
        },
        E = ($) => {
          i == null || i($),
            m.getState().resetSelectedElements(),
            m.setState({ nodesSelectionActive: !1 });
        },
        _ = ($) => {
          if (Array.isArray(n) && n != null && n.includes(2)) {
            $.preventDefault();
            return;
          }
          s == null || s($);
        },
        k = a ? ($) => a($) : void 0,
        N = ($) => {
          const { resetSelectedElements: b, domNode: I } = m.getState();
          if (
            ((w.current = I == null ? void 0 : I.getBoundingClientRect()),
            !p || !e || $.button !== 0 || $.target !== d.current || !w.current)
          )
            return;
          const { x: P, y: V } = Zn($, w.current);
          b(),
            m.setState({
              userSelectionRect: { width: 0, height: 0, startX: P, startY: V, x: P, y: V },
            }),
            r == null || r($);
        },
        A = ($) => {
          const {
            userSelectionRect: b,
            nodeInternals: I,
            edges: P,
            transform: V,
            onNodesChange: M,
            onEdgesChange: T,
            nodeOrigin: D,
            getNodes: F,
          } = m.getState();
          if (!e || !w.current || !b) return;
          m.setState({ userSelectionActive: !0, nodesSelectionActive: !1 });
          const z = Zn($, w.current),
            W = b.startX ?? 0,
            H = b.startY ?? 0,
            Y = {
              ...b,
              x: z.x < W ? z.x : W,
              y: z.y < H ? z.y : H,
              width: Math.abs(z.x - W),
              height: Math.abs(z.y - H),
            },
            U = F(),
            X = cE(I, Y, V, t === vs.Partial, !0, D),
            te = fE(X, P).map((J) => J.id),
            q = X.map((J) => J.id);
          if (y.current !== q.length) {
            y.current = q.length;
            const J = go(U, q);
            J.length && (M == null || M(J));
          }
          if (g.current !== te.length) {
            g.current = te.length;
            const J = go(P, te);
            J.length && (T == null || T(J));
          }
          m.setState({ userSelectionRect: Y });
        },
        R = ($) => {
          if ($.button !== 0) return;
          const { userSelectionRect: b } = m.getState();
          !h && b && $.target === d.current && (E == null || E($)),
            m.setState({ nodesSelectionActive: y.current > 0 }),
            S(),
            o == null || o($);
        },
        O = ($) => {
          h && (m.setState({ nodesSelectionActive: y.current > 0 }), o == null || o($)), S();
        },
        j = p && (e || h);
      return L.createElement(
        "div",
        {
          className: He(["react-flow__pane", { dragging: x, selection: e }]),
          onClick: j ? void 0 : Mc(E, d),
          onContextMenu: Mc(_, d),
          onWheel: Mc(k, d),
          onMouseEnter: j ? void 0 : l,
          onMouseDown: j ? N : void 0,
          onMouseMove: j ? A : u,
          onMouseUp: j ? R : void 0,
          onMouseLeave: j ? O : c,
          ref: d,
          style: fp,
        },
        f,
        L.createElement(V4, null),
      );
    },
  );
ME.displayName = "Pane";
function AE(e, t) {
  const n = e.parentNode || e.parentId;
  if (!n) return !1;
  const r = t.get(n);
  return r ? (r.selected ? !0 : AE(r, t)) : !1;
}
function Uy(e, t, n) {
  let r = e;
  do {
    if (r != null && r.matches(t)) return !0;
    if (r === n.current) return !1;
    r = r.parentElement;
  } while (r);
  return !1;
}
function F4(e, t, n, r) {
  return Array.from(e.values())
    .filter(
      (o) =>
        (o.selected || o.id === r) &&
        (!o.parentNode || o.parentId || !AE(o, e)) &&
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
function z4(e, t) {
  return !t || t === "parent" ? t : [t[0], [t[1][0] - (e.width || 0), t[1][1] - (e.height || 0)]];
}
function RE(e, t, n, r, o = [0, 0], i) {
  const s = z4(e, e.extent || r);
  let a = s;
  const l = e.parentNode || e.parentId;
  if (e.extent === "parent" && !e.expandParent)
    if (l && e.width && e.height) {
      const f = n.get(l),
        { x: d, y: m } = _r(f, o).positionAbsolute;
      a =
        f && kt(d) && kt(m) && kt(f.width) && kt(f.height)
          ? [
              [d + e.width * o[0], m + e.height * o[1]],
              [d + f.width - e.width + e.width * o[0], m + f.height - e.height + e.height * o[1]],
            ]
          : a;
    } else i == null || i("005", kn.error005()), (a = s);
  else if (e.extent && l && e.extent !== "parent") {
    const f = n.get(l),
      { x: d, y: m } = _r(f, o).positionAbsolute;
    a = [
      [e.extent[0][0] + d, e.extent[0][1] + m],
      [e.extent[1][0] + d, e.extent[1][1] + m],
    ];
  }
  let u = { x: 0, y: 0 };
  if (l) {
    const f = n.get(l);
    u = _r(f, o).positionAbsolute;
  }
  const c = a && a !== "parent" ? op(t, a) : t;
  return { position: { x: c.x - u.x, y: c.y - u.y }, positionAbsolute: c };
}
function Ac({ nodeId: e, dragItems: t, nodeInternals: n }) {
  const r = t.map((o) => ({
    ...n.get(o.id),
    position: o.position,
    positionAbsolute: o.positionAbsolute,
  }));
  return [e ? r.find((o) => o.id === e) : r[0], r];
}
const Wy = (e, t, n, r) => {
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
      ...rp(l),
    };
  });
};
function mi(e, t, n) {
  return n === void 0
    ? n
    : (r) => {
        const o = t().nodeInternals.get(e);
        o && n(r, { ...o });
      };
}
function ld({ id: e, store: t, unselect: n = !1, nodeRef: r }) {
  const {
      addSelectedNodes: o,
      unselectNodesAndEdges: i,
      multiSelectionActive: s,
      nodeInternals: a,
      onError: l,
    } = t.getState(),
    u = a.get(e);
  if (!u) {
    l == null || l("012", kn.error012(e));
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
function $4() {
  const e = Ae();
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
function Rc(e) {
  return (t, n, r) => (e == null ? void 0 : e(t, r));
}
function DE({
  nodeRef: e,
  disabled: t = !1,
  noDragClassName: n,
  handleSelector: r,
  nodeId: o,
  isSelectable: i,
  selectNodesOnDrag: s,
}) {
  const a = Ae(),
    [l, u] = v.useState(!1),
    c = v.useRef([]),
    f = v.useRef({ x: null, y: null }),
    d = v.useRef(0),
    m = v.useRef(null),
    y = v.useRef({ x: 0, y: 0 }),
    g = v.useRef(null),
    w = v.useRef(!1),
    h = v.useRef(!1),
    p = v.useRef(!1),
    x = $4();
  return (
    v.useEffect(() => {
      if (e != null && e.current) {
        const S = Ct(e.current),
          E = ({ x: N, y: A }) => {
            const {
              nodeInternals: R,
              onNodeDrag: O,
              onSelectionDrag: j,
              updateNodePositions: $,
              nodeExtent: b,
              snapGrid: I,
              snapToGrid: P,
              nodeOrigin: V,
              onError: M,
            } = a.getState();
            f.current = { x: N, y: A };
            let T = !1,
              D = { x: 0, y: 0, x2: 0, y2: 0 };
            if (c.current.length > 1 && b) {
              const z = bu(c.current, V);
              D = ys(z);
            }
            if (
              ((c.current = c.current.map((z) => {
                const W = { x: N - z.distance.x, y: A - z.distance.y };
                P && ((W.x = I[0] * Math.round(W.x / I[0])), (W.y = I[1] * Math.round(W.y / I[1])));
                const H = [
                  [b[0][0], b[0][1]],
                  [b[1][0], b[1][1]],
                ];
                c.current.length > 1 &&
                  b &&
                  !z.extent &&
                  ((H[0][0] = z.positionAbsolute.x - D.x + b[0][0]),
                  (H[1][0] = z.positionAbsolute.x + (z.width ?? 0) - D.x2 + b[1][0]),
                  (H[0][1] = z.positionAbsolute.y - D.y + b[0][1]),
                  (H[1][1] = z.positionAbsolute.y + (z.height ?? 0) - D.y2 + b[1][1]));
                const Y = RE(z, W, R, H, V, M);
                return (
                  (T = T || z.position.x !== Y.position.x || z.position.y !== Y.position.y),
                  (z.position = Y.position),
                  (z.positionAbsolute = Y.positionAbsolute),
                  z
                );
              })),
              !T)
            )
              return;
            $(c.current, !0, !0), u(!0);
            const F = o ? O : Rc(j);
            if (F && g.current) {
              const [z, W] = Ac({ nodeId: o, dragItems: c.current, nodeInternals: R });
              F(g.current, z, W);
            }
          },
          _ = () => {
            if (!m.current) return;
            const [N, A] = JS(y.current, m.current);
            if (N !== 0 || A !== 0) {
              const { transform: R, panBy: O } = a.getState();
              (f.current.x = (f.current.x ?? 0) - N / R[2]),
                (f.current.y = (f.current.y ?? 0) - A / R[2]),
                O({ x: N, y: A }) && E(f.current);
            }
            d.current = requestAnimationFrame(_);
          },
          k = (N) => {
            var V;
            const {
              nodeInternals: A,
              multiSelectionActive: R,
              nodesDraggable: O,
              unselectNodesAndEdges: j,
              onNodeDragStart: $,
              onSelectionDragStart: b,
            } = a.getState();
            h.current = !0;
            const I = o ? $ : Rc(b);
            (!s || !i) && !R && o && (((V = A.get(o)) != null && V.selected) || j()),
              o && i && s && ld({ id: o, store: a, nodeRef: e });
            const P = x(N);
            if (((f.current = P), (c.current = F4(A, O, P, o)), I && c.current)) {
              const [M, T] = Ac({ nodeId: o, dragItems: c.current, nodeInternals: A });
              I(N.sourceEvent, M, T);
            }
          };
        if (t) S.on(".drag", null);
        else {
          const N = qI()
            .on("start", (A) => {
              const { domNode: R, nodeDragThreshold: O } = a.getState();
              O === 0 && k(A), (p.current = !1);
              const j = x(A);
              (f.current = j),
                (m.current = (R == null ? void 0 : R.getBoundingClientRect()) || null),
                (y.current = Zn(A.sourceEvent, m.current));
            })
            .on("drag", (A) => {
              var $, b;
              const R = x(A),
                { autoPanOnNodeDrag: O, nodeDragThreshold: j } = a.getState();
              if (
                (A.sourceEvent.type === "touchmove" &&
                  A.sourceEvent.touches.length > 1 &&
                  (p.current = !0),
                !p.current)
              ) {
                if ((!w.current && h.current && O && ((w.current = !0), _()), !h.current)) {
                  const I =
                      R.xSnapped -
                      ((($ = f == null ? void 0 : f.current) == null ? void 0 : $.x) ?? 0),
                    P =
                      R.ySnapped -
                      (((b = f == null ? void 0 : f.current) == null ? void 0 : b.y) ?? 0);
                  Math.sqrt(I * I + P * P) > j && k(A);
                }
                (f.current.x !== R.xSnapped || f.current.y !== R.ySnapped) &&
                  c.current &&
                  h.current &&
                  ((g.current = A.sourceEvent), (y.current = Zn(A.sourceEvent, m.current)), E(R));
              }
            })
            .on("end", (A) => {
              if (
                !(!h.current || p.current) &&
                (u(!1),
                (w.current = !1),
                (h.current = !1),
                cancelAnimationFrame(d.current),
                c.current)
              ) {
                const {
                    updateNodePositions: R,
                    nodeInternals: O,
                    onNodeDragStop: j,
                    onSelectionDragStop: $,
                  } = a.getState(),
                  b = o ? j : Rc($);
                if ((R(c.current, !1, !1), b)) {
                  const [I, P] = Ac({ nodeId: o, dragItems: c.current, nodeInternals: O });
                  b(A.sourceEvent, I, P);
                }
              }
            })
            .filter((A) => {
              const R = A.target;
              return !A.button && (!n || !Uy(R, `.${n}`, e)) && (!r || Uy(R, r, e));
            });
          return (
            S.call(N),
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
function IE() {
  const e = Ae();
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
      f = s().filter((p) => p.selected && (p.draggable || (c && typeof p.draggable > "u"))),
      d = a ? l[0] : 5,
      m = a ? l[1] : 5,
      y = n.isShiftPressed ? 4 : 1,
      g = n.x * d * y,
      w = n.y * m * y,
      h = f.map((p) => {
        if (p.positionAbsolute) {
          const x = { x: p.positionAbsolute.x + g, y: p.positionAbsolute.y + w };
          a && ((x.x = l[0] * Math.round(x.x / l[0])), (x.y = l[1] * Math.round(x.y / l[1])));
          const { positionAbsolute: S, position: E } = RE(p, x, r, o, void 0, u);
          (p.position = E), (p.positionAbsolute = S);
        }
        return p;
      });
    i(h, !0, !1);
  }, []);
}
const No = {
  ArrowUp: { x: 0, y: -1 },
  ArrowDown: { x: 0, y: 1 },
  ArrowLeft: { x: -1, y: 0 },
  ArrowRight: { x: 1, y: 0 },
};
var gi = (e) => {
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
    onMouseLeave: m,
    onContextMenu: y,
    onDoubleClick: g,
    style: w,
    className: h,
    isDraggable: p,
    isSelectable: x,
    isConnectable: S,
    isFocusable: E,
    selectNodesOnDrag: _,
    sourcePosition: k,
    targetPosition: N,
    hidden: A,
    resizeObserver: R,
    dragHandle: O,
    zIndex: j,
    isParent: $,
    noDragClassName: b,
    noPanClassName: I,
    initialized: P,
    disableKeyboardA11y: V,
    ariaLabel: M,
    rfId: T,
    hasHandleBounds: D,
  }) => {
    const F = Ae(),
      z = v.useRef(null),
      W = v.useRef(null),
      H = v.useRef(k),
      Y = v.useRef(N),
      U = v.useRef(r),
      X = x || p || c || f || d || m,
      te = IE(),
      q = mi(n, F.getState, f),
      J = mi(n, F.getState, d),
      oe = mi(n, F.getState, m),
      pe = mi(n, F.getState, y),
      Ce = mi(n, F.getState, g),
      ae = (ue) => {
        const { nodeDragThreshold: Z } = F.getState();
        if ((x && (!_ || !p || Z > 0) && ld({ id: n, store: F, nodeRef: z }), c)) {
          const qe = F.getState().nodeInternals.get(n);
          qe && c(ue, { ...qe });
        }
      },
      de = (ue) => {
        if (!od(ue) && !V)
          if (rE.includes(ue.key) && x) {
            const Z = ue.key === "Escape";
            ld({ id: n, store: F, unselect: Z, nodeRef: z });
          } else
            p &&
              u &&
              Object.prototype.hasOwnProperty.call(No, ue.key) &&
              (F.setState({
                ariaLiveMessage: `Moved selected node ${ue.key.replace("Arrow", "").toLowerCase()}. New position, x: ${~~i}, y: ${~~s}`,
              }),
              te({ x: No[ue.key].x, y: No[ue.key].y, isShiftPressed: ue.shiftKey }));
      };
    v.useEffect(
      () => () => {
        W.current && (R == null || R.unobserve(W.current), (W.current = null));
      },
      [],
    ),
      v.useEffect(() => {
        if (z.current && !A) {
          const ue = z.current;
          (!P || !D || W.current !== ue) &&
            (W.current && (R == null || R.unobserve(W.current)),
            R == null || R.observe(ue),
            (W.current = ue));
        }
      }, [A, P, D]),
      v.useEffect(() => {
        const ue = U.current !== r,
          Z = H.current !== k,
          qe = Y.current !== N;
        z.current &&
          (ue || Z || qe) &&
          (ue && (U.current = r),
          Z && (H.current = k),
          qe && (Y.current = N),
          F.getState().updateNodeDimensions([{ id: n, nodeElement: z.current, forceUpdate: !0 }]));
      }, [n, r, k, N]);
    const Ue = DE({
      nodeRef: z,
      disabled: A || !p,
      noDragClassName: b,
      handleSelector: O,
      nodeId: n,
      isSelectable: x,
      selectNodesOnDrag: _,
    });
    return A
      ? null
      : L.createElement(
          "div",
          {
            className: He([
              "react-flow__node",
              `react-flow__node-${r}`,
              { [I]: p },
              h,
              { selected: u, selectable: x, parent: $, dragging: Ue },
            ]),
            ref: z,
            style: {
              zIndex: j,
              transform: `translate(${a}px,${l}px)`,
              pointerEvents: X ? "all" : "none",
              visibility: P ? "visible" : "hidden",
              ...w,
            },
            "data-id": n,
            "data-testid": `rf__node-${n}`,
            onMouseEnter: q,
            onMouseMove: J,
            onMouseLeave: oe,
            onContextMenu: pe,
            onClick: ae,
            onDoubleClick: Ce,
            onKeyDown: E ? de : void 0,
            tabIndex: E ? 0 : void 0,
            role: E ? "button" : void 0,
            "aria-describedby": V ? void 0 : `${CE}-${T}`,
            "aria-label": M,
          },
          L.createElement(
            t4,
            { value: n },
            L.createElement(e, {
              id: n,
              data: o,
              type: r,
              xPos: i,
              yPos: s,
              selected: u,
              isConnectable: S,
              sourcePosition: k,
              targetPosition: N,
              dragging: Ue,
              dragHandle: O,
              zIndex: j,
            }),
          ),
        );
  };
  return (t.displayName = "NodeWrapper"), v.memo(t);
};
const B4 = (e) => {
  const t = e.getNodes().filter((n) => n.selected);
  return {
    ...bu(t, e.nodeOrigin),
    transformString: `translate(${e.transform[0]}px,${e.transform[1]}px) scale(${e.transform[2]})`,
    userSelectionActive: e.userSelectionActive,
  };
};
function H4({ onSelectionContextMenu: e, noPanClassName: t, disableKeyboardA11y: n }) {
  const r = Ae(),
    { width: o, height: i, x: s, y: a, transformString: l, userSelectionActive: u } = fe(B4, je),
    c = IE(),
    f = v.useRef(null);
  if (
    (v.useEffect(() => {
      var y;
      n || (y = f.current) == null || y.focus({ preventScroll: !0 });
    }, [n]),
    DE({ nodeRef: f }),
    u || !o || !i)
  )
    return null;
  const d = e
      ? (y) => {
          const g = r
            .getState()
            .getNodes()
            .filter((w) => w.selected);
          e(y, g);
        }
      : void 0,
    m = (y) => {
      Object.prototype.hasOwnProperty.call(No, y.key) &&
        c({ x: No[y.key].x, y: No[y.key].y, isShiftPressed: y.shiftKey });
    };
  return L.createElement(
    "div",
    {
      className: He(["react-flow__nodesselection", "react-flow__container", t]),
      style: { transform: l },
    },
    L.createElement("div", {
      ref: f,
      className: "react-flow__nodesselection-rect",
      onContextMenu: d,
      tabIndex: n ? void 0 : -1,
      onKeyDown: n ? void 0 : m,
      style: { width: o, height: i, top: a, left: s },
    }),
  );
}
var U4 = v.memo(H4);
const W4 = (e) => e.nodesSelectionActive,
  LE = ({
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
    selectionMode: m,
    onSelectionStart: y,
    onSelectionEnd: g,
    multiSelectionKeyCode: w,
    panActivationKeyCode: h,
    zoomActivationKeyCode: p,
    elementsSelectable: x,
    zoomOnScroll: S,
    zoomOnPinch: E,
    panOnScroll: _,
    panOnScrollSpeed: k,
    panOnScrollMode: N,
    zoomOnDoubleClick: A,
    panOnDrag: R,
    defaultViewport: O,
    translateExtent: j,
    minZoom: $,
    maxZoom: b,
    preventScrolling: I,
    onSelectionContextMenu: P,
    noWheelClassName: V,
    noPanClassName: M,
    disableKeyboardA11y: T,
  }) => {
    const D = fe(W4),
      F = Ss(f),
      z = Ss(h),
      W = z || R,
      H = z || _,
      Y = F || (d && W !== !0);
    return (
      M4({ deleteKeyCode: a, multiSelectionKeyCode: w }),
      L.createElement(
        I4,
        {
          onMove: l,
          onMoveStart: u,
          onMoveEnd: c,
          onPaneContextMenu: i,
          elementsSelectable: x,
          zoomOnScroll: S,
          zoomOnPinch: E,
          panOnScroll: H,
          panOnScrollSpeed: k,
          panOnScrollMode: N,
          zoomOnDoubleClick: A,
          panOnDrag: !F && W,
          defaultViewport: O,
          translateExtent: j,
          minZoom: $,
          maxZoom: b,
          zoomActivationKeyCode: p,
          preventScrolling: I,
          noWheelClassName: V,
          noPanClassName: M,
        },
        L.createElement(
          ME,
          {
            onSelectionStart: y,
            onSelectionEnd: g,
            onPaneClick: t,
            onPaneMouseEnter: n,
            onPaneMouseMove: r,
            onPaneMouseLeave: o,
            onPaneContextMenu: i,
            onPaneScroll: s,
            panOnDrag: W,
            isSelecting: !!Y,
            selectionMode: m,
          },
          e,
          D &&
            L.createElement(U4, {
              onSelectionContextMenu: P,
              noPanClassName: M,
              disableKeyboardA11y: T,
            }),
        ),
      )
    );
  };
LE.displayName = "FlowRenderer";
var G4 = v.memo(LE);
function K4(e) {
  return fe(
    v.useCallback(
      (n) =>
        e
          ? cE(n.nodeInternals, { x: 0, y: 0, width: n.width, height: n.height }, n.transform, !0)
          : n.getNodes(),
      [e],
    ),
  );
}
function Y4(e) {
  const t = {
      input: gi(e.input || xE),
      default: gi(e.default || ad),
      output: gi(e.output || SE),
      group: gi(e.group || cp),
    },
    n = {},
    r = Object.keys(e)
      .filter((o) => !["input", "default", "output", "group"].includes(o))
      .reduce((o, i) => ((o[i] = gi(e[i] || ad)), o), n);
  return { ...t, ...r };
}
const X4 = ({ x: e, y: t, width: n, height: r, origin: o }) =>
    !n || !r
      ? { x: e, y: t }
      : o[0] < 0 || o[1] < 0 || o[0] > 1 || o[1] > 1
        ? { x: e, y: t }
        : { x: e - n * o[0], y: t - r * o[1] },
  Z4 = (e) => ({
    nodesDraggable: e.nodesDraggable,
    nodesConnectable: e.nodesConnectable,
    nodesFocusable: e.nodesFocusable,
    elementsSelectable: e.elementsSelectable,
    updateNodeDimensions: e.updateNodeDimensions,
    onError: e.onError,
  }),
  VE = (e) => {
    const {
        nodesDraggable: t,
        nodesConnectable: n,
        nodesFocusable: r,
        elementsSelectable: o,
        updateNodeDimensions: i,
        onError: s,
      } = fe(Z4, je),
      a = K4(e.onlyRenderVisibleElements),
      l = v.useRef(),
      u = v.useMemo(() => {
        if (typeof ResizeObserver > "u") return null;
        const c = new ResizeObserver((f) => {
          const d = f.map((m) => ({
            id: m.target.getAttribute("data-id"),
            nodeElement: m.target,
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
        { className: "react-flow__nodes", style: fp },
        a.map((c) => {
          var E, _, k;
          let f = c.type || "default";
          e.nodeTypes[f] || (s == null || s("003", kn.error003(f)), (f = "default"));
          const d = e.nodeTypes[f] || e.nodeTypes.default,
            m = !!(c.draggable || (t && typeof c.draggable > "u")),
            y = !!(c.selectable || (o && typeof c.selectable > "u")),
            g = !!(c.connectable || (n && typeof c.connectable > "u")),
            w = !!(c.focusable || (r && typeof c.focusable > "u")),
            h = e.nodeExtent ? op(c.positionAbsolute, e.nodeExtent) : c.positionAbsolute,
            p = (h == null ? void 0 : h.x) ?? 0,
            x = (h == null ? void 0 : h.y) ?? 0,
            S = X4({
              x: p,
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
            sourcePosition: c.sourcePosition || K.Bottom,
            targetPosition: c.targetPosition || K.Top,
            hidden: c.hidden,
            xPos: p,
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
            isDraggable: m,
            isSelectable: y,
            isConnectable: g,
            isFocusable: w,
            resizeObserver: u,
            dragHandle: c.dragHandle,
            zIndex: ((E = c[Te]) == null ? void 0 : E.z) ?? 0,
            isParent: !!((_ = c[Te]) != null && _.isParent),
            noDragClassName: e.noDragClassName,
            noPanClassName: e.noPanClassName,
            initialized: !!c.width && !!c.height,
            rfId: e.rfId,
            disableKeyboardA11y: e.disableKeyboardA11y,
            ariaLabel: c.ariaLabel,
            hasHandleBounds: !!((k = c[Te]) != null && k.handleBounds),
          });
        }),
      )
    );
  };
VE.displayName = "NodeRenderer";
var Q4 = v.memo(VE);
const q4 = (e, t, n) => (n === K.Left ? e - t : n === K.Right ? e + t : e),
  J4 = (e, t, n) => (n === K.Top ? e - t : n === K.Bottom ? e + t : e),
  Gy = "react-flow__edgeupdater",
  Ky = ({
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
      className: He([Gy, `${Gy}-${a}`]),
      cx: q4(t, r, e),
      cy: J4(n, r, e),
      r,
      stroke: "transparent",
      fill: "transparent",
    }),
  eV = () => !0;
var Qr = (e) => {
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
    labelBgStyle: m,
    labelBgPadding: y,
    labelBgBorderRadius: g,
    style: w,
    source: h,
    target: p,
    sourceX: x,
    sourceY: S,
    targetX: E,
    targetY: _,
    sourcePosition: k,
    targetPosition: N,
    elementsSelectable: A,
    hidden: R,
    sourceHandleId: O,
    targetHandleId: j,
    onContextMenu: $,
    onMouseEnter: b,
    onMouseMove: I,
    onMouseLeave: P,
    reconnectRadius: V,
    onReconnect: M,
    onReconnectStart: T,
    onReconnectEnd: D,
    markerEnd: F,
    markerStart: z,
    rfId: W,
    ariaLabel: H,
    isFocusable: Y,
    isReconnectable: U,
    pathOptions: X,
    interactionWidth: te,
    disableKeyboardA11y: q,
  }) => {
    const J = v.useRef(null),
      [oe, pe] = v.useState(!1),
      [Ce, ae] = v.useState(!1),
      de = Ae(),
      Ue = v.useMemo(() => `url('#${id(z, W)}')`, [z, W]),
      ue = v.useMemo(() => `url('#${id(F, W)}')`, [F, W]);
    if (R) return null;
    const Z = (We) => {
        var Ht;
        const {
            edges: Pt,
            addSelectedEdges: sr,
            unselectNodesAndEdges: ar,
            multiSelectionActive: lr,
          } = de.getState(),
          on = Pt.find((Jo) => Jo.id === n);
        on &&
          (A &&
            (de.setState({ nodesSelectionActive: !1 }),
            on.selected && lr
              ? (ar({ nodes: [], edges: [on] }), (Ht = J.current) == null || Ht.blur())
              : sr([n])),
          s && s(We, on));
      },
      qe = pi(n, de.getState, a),
      nn = pi(n, de.getState, $),
      Qo = pi(n, de.getState, b),
      Fr = pi(n, de.getState, I),
      zr = pi(n, de.getState, P),
      rn = (We, Pt) => {
        if (We.button !== 0) return;
        const { edges: sr, isValidConnection: ar } = de.getState(),
          lr = Pt ? p : h,
          on = (Pt ? j : O) || null,
          Ht = Pt ? "target" : "source",
          Jo = ar || eV,
          Tu = Pt,
          ei = sr.find((ur) => ur.id === n);
        ae(!0), T == null || T(We, ei, Ht);
        const _u = (ur) => {
          ae(!1), D == null || D(ur, ei, Ht);
        };
        mE({
          event: We,
          handleId: on,
          nodeId: lr,
          onConnect: (ur) => (M == null ? void 0 : M(ei, ur)),
          isTarget: Tu,
          getState: de.getState,
          setState: de.setState,
          isValidConnection: Jo,
          edgeUpdaterType: Ht,
          onReconnectEnd: _u,
        });
      },
      $r = (We) => rn(We, !0),
      or = (We) => rn(We, !1),
      ir = () => pe(!0),
      Br = () => pe(!1),
      Hr = !A && !s,
      qo = (We) => {
        var Pt;
        if (!q && rE.includes(We.key) && A) {
          const { unselectNodesAndEdges: sr, addSelectedEdges: ar, edges: lr } = de.getState();
          We.key === "Escape"
            ? ((Pt = J.current) == null || Pt.blur(), sr({ edges: [lr.find((Ht) => Ht.id === n)] }))
            : ar([n]);
        }
      };
    return L.createElement(
      "g",
      {
        className: He([
          "react-flow__edge",
          `react-flow__edge-${o}`,
          r,
          { selected: l, animated: u, inactive: Hr, updating: oe },
        ]),
        onClick: Z,
        onDoubleClick: qe,
        onContextMenu: nn,
        onMouseEnter: Qo,
        onMouseMove: Fr,
        onMouseLeave: zr,
        onKeyDown: Y ? qo : void 0,
        tabIndex: Y ? 0 : void 0,
        role: Y ? "button" : "img",
        "data-testid": `rf__edge-${n}`,
        "aria-label": H === null ? void 0 : H || `Edge from ${h} to ${p}`,
        "aria-describedby": Y ? `${bE}-${W}` : void 0,
        ref: J,
      },
      !Ce &&
        L.createElement(e, {
          id: n,
          source: h,
          target: p,
          selected: l,
          animated: u,
          label: c,
          labelStyle: f,
          labelShowBg: d,
          labelBgStyle: m,
          labelBgPadding: y,
          labelBgBorderRadius: g,
          data: i,
          style: w,
          sourceX: x,
          sourceY: S,
          targetX: E,
          targetY: _,
          sourcePosition: k,
          targetPosition: N,
          sourceHandleId: O,
          targetHandleId: j,
          markerStart: Ue,
          markerEnd: ue,
          pathOptions: X,
          interactionWidth: te,
        }),
      U &&
        L.createElement(
          L.Fragment,
          null,
          (U === "source" || U === !0) &&
            L.createElement(Ky, {
              position: k,
              centerX: x,
              centerY: S,
              radius: V,
              onMouseDown: $r,
              onMouseEnter: ir,
              onMouseOut: Br,
              type: "source",
            }),
          (U === "target" || U === !0) &&
            L.createElement(Ky, {
              position: N,
              centerX: E,
              centerY: _,
              radius: V,
              onMouseDown: or,
              onMouseEnter: ir,
              onMouseOut: Br,
              type: "target",
            }),
        ),
    );
  };
  return (t.displayName = "EdgeWrapper"), v.memo(t);
};
function tV(e) {
  const t = {
      default: Qr(e.default || Il),
      straight: Qr(e.bezier || ap),
      step: Qr(e.step || sp),
      smoothstep: Qr(e.step || Cu),
      simplebezier: Qr(e.simplebezier || ip),
    },
    n = {},
    r = Object.keys(e)
      .filter((o) => !["default", "bezier"].includes(o))
      .reduce((o, i) => ((o[i] = Qr(e[i] || Il)), o), n);
  return { ...t, ...r };
}
function Yy(e, t, n = null) {
  const r = ((n == null ? void 0 : n.x) || 0) + t.x,
    o = ((n == null ? void 0 : n.y) || 0) + t.y,
    i = (n == null ? void 0 : n.width) || t.width,
    s = (n == null ? void 0 : n.height) || t.height;
  switch (e) {
    case K.Top:
      return { x: r + i / 2, y: o };
    case K.Right:
      return { x: r + i, y: o + s / 2 };
    case K.Bottom:
      return { x: r + i / 2, y: o + s };
    case K.Left:
      return { x: r, y: o + s / 2 };
  }
}
function Xy(e, t) {
  return e ? (e.length === 1 || !t ? e[0] : (t && e.find((n) => n.id === t)) || null) : null;
}
const nV = (e, t, n, r, o, i) => {
  const s = Yy(n, e, t),
    a = Yy(i, r, o);
  return { sourceX: s.x, sourceY: s.y, targetX: a.x, targetY: a.y };
};
function rV({
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
  const c = ys({ x: (0 - l[0]) / l[2], y: (0 - l[1]) / l[2], width: s / l[2], height: a / l[2] }),
    f = Math.max(0, Math.min(c.x2, u.x2) - Math.max(c.x, u.x)),
    d = Math.max(0, Math.min(c.y2, u.y2) - Math.max(c.y, u.y));
  return Math.ceil(f * d) > 0;
}
function Zy(e) {
  var r, o, i, s, a;
  const t = ((r = e == null ? void 0 : e[Te]) == null ? void 0 : r.handleBounds) || null,
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
const oV = [{ level: 0, isMaxLevel: !0, edges: [] }];
function iV(e, t, n = !1) {
  let r = -1;
  const o = e.reduce((s, a) => {
      var c, f;
      const l = kt(a.zIndex);
      let u = l ? a.zIndex : 0;
      if (n) {
        const d = t.get(a.target),
          m = t.get(a.source),
          y = a.selected || (d == null ? void 0 : d.selected) || (m == null ? void 0 : m.selected),
          g = Math.max(
            ((c = m == null ? void 0 : m[Te]) == null ? void 0 : c.z) || 0,
            ((f = d == null ? void 0 : d[Te]) == null ? void 0 : f.z) || 0,
            1e3,
          );
        u = (l ? a.zIndex : 0) + (y ? g : 0);
      }
      return s[u] ? s[u].push(a) : (s[u] = [a]), (r = u > r ? u : r), s;
    }, {}),
    i = Object.entries(o).map(([s, a]) => {
      const l = +s;
      return { edges: a, level: l, isMaxLevel: l === r };
    });
  return i.length === 0 ? oV : i;
}
function sV(e, t, n) {
  const r = fe(
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
                rV({
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
  return iV(r, t, n);
}
const aV = ({ color: e = "none", strokeWidth: t = 1 }) =>
    L.createElement("polyline", {
      style: { stroke: e, strokeWidth: t },
      strokeLinecap: "round",
      strokeLinejoin: "round",
      fill: "none",
      points: "-5,-4 0,0 -5,4",
    }),
  lV = ({ color: e = "none", strokeWidth: t = 1 }) =>
    L.createElement("polyline", {
      style: { stroke: e, fill: e, strokeWidth: t },
      strokeLinecap: "round",
      strokeLinejoin: "round",
      points: "-5,-4 0,0 -5,4 -5,-4",
    }),
  Qy = { [xs.Arrow]: aV, [xs.ArrowClosed]: lV };
function uV(e) {
  const t = Ae();
  return v.useMemo(() => {
    var o, i;
    return Object.prototype.hasOwnProperty.call(Qy, e)
      ? Qy[e]
      : ((i = (o = t.getState()).onError) == null || i.call(o, "009", kn.error009(e)), null);
  }, [e]);
}
const cV = ({
    id: e,
    type: t,
    color: n,
    width: r = 12.5,
    height: o = 12.5,
    markerUnits: i = "strokeWidth",
    strokeWidth: s,
    orient: a = "auto-start-reverse",
  }) => {
    const l = uV(t);
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
  fV =
    ({ defaultColor: e, rfId: t }) =>
    (n) => {
      const r = [];
      return n.edges
        .reduce(
          (o, i) => (
            [i.markerStart, i.markerEnd].forEach((s) => {
              if (s && typeof s == "object") {
                const a = id(s, t);
                r.includes(a) || (o.push({ id: a, color: s.color || e, ...s }), r.push(a));
              }
            }),
            o
          ),
          [],
        )
        .sort((o, i) => o.id.localeCompare(i.id));
    },
  OE = ({ defaultColor: e, rfId: t }) => {
    const n = fe(
      v.useCallback(fV({ defaultColor: e, rfId: t }), [e, t]),
      (r, o) => !(r.length !== o.length || r.some((i, s) => i.id !== o[s].id)),
    );
    return L.createElement(
      "defs",
      null,
      n.map((r) =>
        L.createElement(cV, {
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
OE.displayName = "MarkerDefinitions";
var dV = v.memo(OE);
const hV = (e) => ({
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
  jE = ({
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
    onReconnectStart: m,
    onReconnectEnd: y,
    reconnectRadius: g,
    children: w,
    disableKeyboardA11y: h,
  }) => {
    const {
        edgesFocusable: p,
        edgesUpdatable: x,
        elementsSelectable: S,
        width: E,
        height: _,
        connectionMode: k,
        nodeInternals: N,
        onError: A,
      } = fe(hV, je),
      R = sV(t, N, n);
    return E
      ? L.createElement(
          L.Fragment,
          null,
          R.map(({ level: O, edges: j, isMaxLevel: $ }) =>
            L.createElement(
              "svg",
              {
                key: O,
                style: { zIndex: O },
                width: E,
                height: _,
                className: "react-flow__edges react-flow__container",
              },
              $ && L.createElement(dV, { defaultColor: e, rfId: r }),
              L.createElement(
                "g",
                null,
                j.map((b) => {
                  const [I, P, V] = Zy(N.get(b.source)),
                    [M, T, D] = Zy(N.get(b.target));
                  if (!V || !D) return null;
                  let F = b.type || "default";
                  o[F] || (A == null || A("011", kn.error011(F)), (F = "default"));
                  const z = o[F] || o.default,
                    W = k === Lr.Strict ? T.target : (T.target ?? []).concat(T.source ?? []),
                    H = Xy(P.source, b.sourceHandle),
                    Y = Xy(W, b.targetHandle),
                    U = (H == null ? void 0 : H.position) || K.Bottom,
                    X = (Y == null ? void 0 : Y.position) || K.Top,
                    te = !!(b.focusable || (p && typeof b.focusable > "u")),
                    q = b.reconnectable || b.updatable,
                    J = typeof d < "u" && (q || (x && typeof q > "u"));
                  if (!H || !Y) return A == null || A("008", kn.error008(H, b)), null;
                  const {
                    sourceX: oe,
                    sourceY: pe,
                    targetX: Ce,
                    targetY: ae,
                  } = nV(I, H, U, M, Y, X);
                  return L.createElement(z, {
                    key: b.id,
                    id: b.id,
                    className: He([b.className, i]),
                    type: F,
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
                    sourceX: oe,
                    sourceY: pe,
                    targetX: Ce,
                    targetY: ae,
                    sourcePosition: U,
                    targetPosition: X,
                    elementsSelectable: S,
                    onContextMenu: s,
                    onMouseEnter: a,
                    onMouseMove: l,
                    onMouseLeave: u,
                    onClick: c,
                    onEdgeDoubleClick: f,
                    onReconnect: d,
                    onReconnectStart: m,
                    onReconnectEnd: y,
                    reconnectRadius: g,
                    rfId: r,
                    ariaLabel: b.ariaLabel,
                    isFocusable: te,
                    isReconnectable: J,
                    pathOptions: "pathOptions" in b ? b.pathOptions : void 0,
                    interactionWidth: b.interactionWidth,
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
jE.displayName = "EdgeRenderer";
var pV = v.memo(jE);
const mV = (e) => `translate(${e.transform[0]}px,${e.transform[1]}px) scale(${e.transform[2]})`;
function gV({ children: e }) {
  const t = fe(mV);
  return L.createElement(
    "div",
    { className: "react-flow__viewport react-flow__container", style: { transform: t } },
    e,
  );
}
function yV(e) {
  const t = ku(),
    n = v.useRef(!1);
  v.useEffect(() => {
    !n.current && t.viewportInitialized && e && (setTimeout(() => e(t), 1), (n.current = !0));
  }, [e, t.viewportInitialized]);
}
const vV = { [K.Left]: K.Right, [K.Right]: K.Left, [K.Top]: K.Bottom, [K.Bottom]: K.Top },
  FE = ({
    nodeId: e,
    handleType: t,
    style: n,
    type: r = cn.Bezier,
    CustomComponent: o,
    connectionStatus: i,
  }) => {
    var _, k, N;
    const {
        fromNode: s,
        handleId: a,
        toX: l,
        toY: u,
        connectionMode: c,
      } = fe(
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
        je,
      ),
      f = (_ = s == null ? void 0 : s[Te]) == null ? void 0 : _.handleBounds;
    let d = f == null ? void 0 : f[t];
    if (
      (c === Lr.Loose && (d = d || (f == null ? void 0 : f[t === "source" ? "target" : "source"])),
      !s || !d)
    )
      return null;
    const m = a ? d.find((A) => A.id === a) : d[0],
      y = m ? m.x + m.width / 2 : (s.width ?? 0) / 2,
      g = m ? m.y + m.height / 2 : (s.height ?? 0),
      w = (((k = s.positionAbsolute) == null ? void 0 : k.x) ?? 0) + y,
      h = (((N = s.positionAbsolute) == null ? void 0 : N.y) ?? 0) + g,
      p = m == null ? void 0 : m.position,
      x = p ? vV[p] : null;
    if (!p || !x) return null;
    if (o)
      return L.createElement(o, {
        connectionLineType: r,
        connectionLineStyle: n,
        fromNode: s,
        fromHandle: m,
        fromX: w,
        fromY: h,
        toX: l,
        toY: u,
        fromPosition: p,
        toPosition: x,
        connectionStatus: i,
      });
    let S = "";
    const E = {
      sourceX: w,
      sourceY: h,
      sourcePosition: p,
      targetX: l,
      targetY: u,
      targetPosition: x,
    };
    return (
      r === cn.Bezier
        ? ([S] = lE(E))
        : r === cn.Step
          ? ([S] = Dl({ ...E, borderRadius: 0 }))
          : r === cn.SmoothStep
            ? ([S] = Dl(E))
            : r === cn.SimpleBezier
              ? ([S] = aE(E))
              : (S = `M${w},${h} ${l},${u}`),
      L.createElement("path", {
        d: S,
        fill: "none",
        className: "react-flow__connection-path",
        style: n,
      })
    );
  };
FE.displayName = "ConnectionLine";
const xV = (e) => ({
  nodeId: e.connectionNodeId,
  handleType: e.connectionHandleType,
  nodesConnectable: e.nodesConnectable,
  connectionStatus: e.connectionStatus,
  width: e.width,
  height: e.height,
});
function wV({ containerStyle: e, style: t, type: n, component: r }) {
  const {
    nodeId: o,
    handleType: i,
    nodesConnectable: s,
    width: a,
    height: l,
    connectionStatus: u,
  } = fe(xV, je);
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
          { className: He(["react-flow__connection", u]) },
          L.createElement(FE, {
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
function qy(e, t) {
  return v.useRef(null), Ae(), v.useMemo(() => t(e), [e]);
}
const zE = ({
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
  onNodeContextMenu: m,
  onSelectionContextMenu: y,
  onSelectionStart: g,
  onSelectionEnd: w,
  connectionLineType: h,
  connectionLineStyle: p,
  connectionLineComponent: x,
  connectionLineContainerStyle: S,
  selectionKeyCode: E,
  selectionOnDrag: _,
  selectionMode: k,
  multiSelectionKeyCode: N,
  panActivationKeyCode: A,
  zoomActivationKeyCode: R,
  deleteKeyCode: O,
  onlyRenderVisibleElements: j,
  elementsSelectable: $,
  selectNodesOnDrag: b,
  defaultViewport: I,
  translateExtent: P,
  minZoom: V,
  maxZoom: M,
  preventScrolling: T,
  defaultMarkerColor: D,
  zoomOnScroll: F,
  zoomOnPinch: z,
  panOnScroll: W,
  panOnScrollSpeed: H,
  panOnScrollMode: Y,
  zoomOnDoubleClick: U,
  panOnDrag: X,
  onPaneClick: te,
  onPaneMouseEnter: q,
  onPaneMouseMove: J,
  onPaneMouseLeave: oe,
  onPaneScroll: pe,
  onPaneContextMenu: Ce,
  onEdgeContextMenu: ae,
  onEdgeMouseEnter: de,
  onEdgeMouseMove: Ue,
  onEdgeMouseLeave: ue,
  onReconnect: Z,
  onReconnectStart: qe,
  onReconnectEnd: nn,
  reconnectRadius: Qo,
  noDragClassName: Fr,
  noWheelClassName: zr,
  noPanClassName: rn,
  elevateEdgesOnSelect: $r,
  disableKeyboardA11y: or,
  nodeOrigin: ir,
  nodeExtent: Br,
  rfId: Hr,
}) => {
  const qo = qy(e, Y4),
    We = qy(t, tV);
  return (
    yV(i),
    L.createElement(
      G4,
      {
        onPaneClick: te,
        onPaneMouseEnter: q,
        onPaneMouseMove: J,
        onPaneMouseLeave: oe,
        onPaneContextMenu: Ce,
        onPaneScroll: pe,
        deleteKeyCode: O,
        selectionKeyCode: E,
        selectionOnDrag: _,
        selectionMode: k,
        onSelectionStart: g,
        onSelectionEnd: w,
        multiSelectionKeyCode: N,
        panActivationKeyCode: A,
        zoomActivationKeyCode: R,
        elementsSelectable: $,
        onMove: n,
        onMoveStart: r,
        onMoveEnd: o,
        zoomOnScroll: F,
        zoomOnPinch: z,
        zoomOnDoubleClick: U,
        panOnScroll: W,
        panOnScrollSpeed: H,
        panOnScrollMode: Y,
        panOnDrag: X,
        defaultViewport: I,
        translateExtent: P,
        minZoom: V,
        maxZoom: M,
        onSelectionContextMenu: y,
        preventScrolling: T,
        noDragClassName: Fr,
        noWheelClassName: zr,
        noPanClassName: rn,
        disableKeyboardA11y: or,
      },
      L.createElement(
        gV,
        null,
        L.createElement(
          pV,
          {
            edgeTypes: We,
            onEdgeClick: a,
            onEdgeDoubleClick: u,
            onlyRenderVisibleElements: j,
            onEdgeContextMenu: ae,
            onEdgeMouseEnter: de,
            onEdgeMouseMove: Ue,
            onEdgeMouseLeave: ue,
            onReconnect: Z,
            onReconnectStart: qe,
            onReconnectEnd: nn,
            reconnectRadius: Qo,
            defaultMarkerColor: D,
            noPanClassName: rn,
            elevateEdgesOnSelect: !!$r,
            disableKeyboardA11y: or,
            rfId: Hr,
          },
          L.createElement(wV, { style: p, type: h, component: x, containerStyle: S }),
        ),
        L.createElement("div", { className: "react-flow__edgelabel-renderer" }),
        L.createElement(Q4, {
          nodeTypes: qo,
          onNodeClick: s,
          onNodeDoubleClick: l,
          onNodeMouseEnter: c,
          onNodeMouseMove: f,
          onNodeMouseLeave: d,
          onNodeContextMenu: m,
          selectNodesOnDrag: b,
          onlyRenderVisibleElements: j,
          noPanClassName: rn,
          noDragClassName: Fr,
          disableKeyboardA11y: or,
          nodeOrigin: ir,
          nodeExtent: Br,
          rfId: Hr,
        }),
      ),
    )
  );
};
zE.displayName = "GraphView";
var SV = v.memo(zE);
const ud = [
    [Number.NEGATIVE_INFINITY, Number.NEGATIVE_INFINITY],
    [Number.POSITIVE_INFINITY, Number.POSITIVE_INFINITY],
  ],
  Mn = {
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
    translateExtent: ud,
    nodeExtent: ud,
    nodesSelectionActive: !1,
    userSelectionActive: !1,
    userSelectionRect: null,
    connectionNodeId: null,
    connectionHandleId: null,
    connectionHandleType: "source",
    connectionPosition: { x: 0, y: 0 },
    connectionStatus: null,
    connectionMode: Lr.Strict,
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
    onError: XL,
    isValidConnection: void 0,
  },
  EV = () =>
    cD(
      (e, t) => ({
        ...Mn,
        setNodes: (n) => {
          const { nodeInternals: r, nodeOrigin: o, elevateNodesOnSelect: i } = t();
          e({ nodeInternals: Pc(n, r, o, i) });
        },
        getNodes: () => Array.from(t().nodeInternals.values()),
        setEdges: (n) => {
          const { defaultEdgeOptions: r = {} } = t();
          e({ edges: n.map((o) => ({ ...r, ...o })) });
        },
        setDefaultNodesAndEdges: (n, r) => {
          const o = typeof n < "u",
            i = typeof r < "u",
            s = o ? Pc(n, new Map(), t().nodeOrigin, t().elevateNodesOnSelect) : new Map();
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
            m = n.reduce((g, w) => {
              const h = o.get(w.id);
              if (h != null && h.hidden)
                o.set(h.id, { ...h, [Te]: { ...h[Te], handleBounds: void 0 } });
              else if (h) {
                const p = rp(w.nodeElement);
                !!(
                  p.width &&
                  p.height &&
                  (h.width !== p.width || h.height !== p.height || w.forceUpdate)
                ) &&
                  (o.set(h.id, {
                    ...h,
                    [Te]: {
                      ...h[Te],
                      handleBounds: {
                        source: Wy(".source", w.nodeElement, d, u),
                        target: Wy(".target", w.nodeElement, d, u),
                      },
                    },
                    ...p,
                  }),
                  g.push({ id: h.id, type: "dimensions", dimensions: p }));
              }
              return g;
            }, []);
          TE(o, u);
          const y = s || (i && !s && _E(t, { initial: !0, ...a }));
          e({ nodeInternals: new Map(o), fitViewOnInitDone: y }),
            (m == null ? void 0 : m.length) > 0 && (r == null || r(m));
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
              const u = PE(n, a()),
                c = Pc(u, o, s, l);
              e({ nodeInternals: c });
            }
            r == null || r(n);
          }
        },
        addSelectedNodes: (n) => {
          const { multiSelectionActive: r, edges: o, getNodes: i } = t();
          let s,
            a = null;
          r ? (s = n.map((l) => On(l, !0))) : ((s = go(i(), n)), (a = go(o, []))),
            va({ changedNodes: s, changedEdges: a, get: t, set: e });
        },
        addSelectedEdges: (n) => {
          const { multiSelectionActive: r, edges: o, getNodes: i } = t();
          let s,
            a = null;
          r ? (s = n.map((l) => On(l, !0))) : ((s = go(o, n)), (a = go(i(), []))),
            va({ changedNodes: a, changedEdges: s, get: t, set: e });
        },
        unselectNodesAndEdges: ({ nodes: n, edges: r } = {}) => {
          const { edges: o, getNodes: i } = t(),
            s = n || i(),
            a = r || o,
            l = s.map((c) => ((c.selected = !1), On(c.id, !1))),
            u = a.map((c) => On(c.id, !1));
          va({ changedNodes: l, changedEdges: u, get: t, set: e });
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
          va({ changedNodes: i, changedEdges: s, get: t, set: e });
        },
        setNodeExtent: (n) => {
          const { nodeInternals: r } = t();
          r.forEach((o) => {
            o.positionAbsolute = op(o.position, n);
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
          const u = yn.translate(r[0] + n.x, r[1] + n.y).scale(r[2]),
            c = [
              [0, 0],
              [o, i],
            ],
            f = s == null ? void 0 : s.constrain()(u, c, l);
          return s.transform(a, f), r[0] !== f.x || r[1] !== f.y || r[2] !== f.k;
        },
        cancelConnection: () =>
          e({
            connectionNodeId: Mn.connectionNodeId,
            connectionHandleId: Mn.connectionHandleId,
            connectionHandleType: Mn.connectionHandleType,
            connectionStatus: Mn.connectionStatus,
            connectionStartHandle: Mn.connectionStartHandle,
            connectionEndHandle: Mn.connectionEndHandle,
          }),
        reset: () => e({ ...Mn }),
      }),
      Object.is,
    ),
  dp = ({ children: e }) => {
    const t = v.useRef(null);
    return t.current || (t.current = EV()), L.createElement(BL, { value: t.current }, e);
  };
dp.displayName = "ReactFlowProvider";
const $E = ({ children: e }) =>
  v.useContext(Eu) ? L.createElement(L.Fragment, null, e) : L.createElement(dp, null, e);
$E.displayName = "ReactFlowWrapper";
const CV = { input: xE, default: ad, output: SE, group: cp },
  bV = { default: Il, straight: ap, step: sp, smoothstep: Cu, simplebezier: ip },
  kV = [0, 0],
  TV = [15, 15],
  _V = { x: 0, y: 0, zoom: 1 },
  NV = { width: "100%", height: "100%", overflow: "hidden", position: "relative", zIndex: 0 },
  BE = v.forwardRef(
    (
      {
        nodes: e,
        edges: t,
        defaultNodes: n,
        defaultEdges: r,
        className: o,
        nodeTypes: i = CV,
        edgeTypes: s = bV,
        onNodeClick: a,
        onEdgeClick: l,
        onInit: u,
        onMove: c,
        onMoveStart: f,
        onMoveEnd: d,
        onConnect: m,
        onConnectStart: y,
        onConnectEnd: g,
        onClickConnectStart: w,
        onClickConnectEnd: h,
        onNodeMouseEnter: p,
        onNodeMouseMove: x,
        onNodeMouseLeave: S,
        onNodeContextMenu: E,
        onNodeDoubleClick: _,
        onNodeDragStart: k,
        onNodeDrag: N,
        onNodeDragStop: A,
        onNodesDelete: R,
        onEdgesDelete: O,
        onSelectionChange: j,
        onSelectionDragStart: $,
        onSelectionDrag: b,
        onSelectionDragStop: I,
        onSelectionContextMenu: P,
        onSelectionStart: V,
        onSelectionEnd: M,
        connectionMode: T = Lr.Strict,
        connectionLineType: D = cn.Bezier,
        connectionLineStyle: F,
        connectionLineComponent: z,
        connectionLineContainerStyle: W,
        deleteKeyCode: H = "Backspace",
        selectionKeyCode: Y = "Shift",
        selectionOnDrag: U = !1,
        selectionMode: X = vs.Full,
        panActivationKeyCode: te = "Space",
        multiSelectionKeyCode: q = Rl() ? "Meta" : "Control",
        zoomActivationKeyCode: J = Rl() ? "Meta" : "Control",
        snapToGrid: oe = !1,
        snapGrid: pe = TV,
        onlyRenderVisibleElements: Ce = !1,
        selectNodesOnDrag: ae = !0,
        nodesDraggable: de,
        nodesConnectable: Ue,
        nodesFocusable: ue,
        nodeOrigin: Z = kV,
        edgesFocusable: qe,
        edgesUpdatable: nn,
        elementsSelectable: Qo,
        defaultViewport: Fr = _V,
        minZoom: zr = 0.5,
        maxZoom: rn = 2,
        translateExtent: $r = ud,
        preventScrolling: or = !0,
        nodeExtent: ir,
        defaultMarkerColor: Br = "#b1b1b7",
        zoomOnScroll: Hr = !0,
        zoomOnPinch: qo = !0,
        panOnScroll: We = !1,
        panOnScrollSpeed: Pt = 0.5,
        panOnScrollMode: sr = Er.Free,
        zoomOnDoubleClick: ar = !0,
        panOnDrag: lr = !0,
        onPaneClick: on,
        onPaneMouseEnter: Ht,
        onPaneMouseMove: Jo,
        onPaneMouseLeave: Tu,
        onPaneScroll: ei,
        onPaneContextMenu: _u,
        children: pp,
        onEdgeContextMenu: ur,
        onEdgeDoubleClick: QE,
        onEdgeMouseEnter: qE,
        onEdgeMouseMove: JE,
        onEdgeMouseLeave: eC,
        onEdgeUpdate: tC,
        onEdgeUpdateStart: nC,
        onEdgeUpdateEnd: rC,
        onReconnect: oC,
        onReconnectStart: iC,
        onReconnectEnd: sC,
        reconnectRadius: aC = 10,
        edgeUpdaterRadius: lC = 10,
        onNodesChange: uC,
        onEdgesChange: cC,
        noDragClassName: fC = "nodrag",
        noWheelClassName: dC = "nowheel",
        noPanClassName: mp = "nopan",
        fitView: hC = !1,
        fitViewOptions: pC,
        connectOnClick: mC = !0,
        attributionPosition: gC,
        proOptions: yC,
        defaultEdgeOptions: vC,
        elevateNodesOnSelect: xC = !0,
        elevateEdgesOnSelect: wC = !1,
        disableKeyboardA11y: gp = !1,
        autoPanOnConnect: SC = !0,
        autoPanOnNodeDrag: EC = !0,
        connectionRadius: CC = 20,
        isValidConnection: bC,
        onError: kC,
        style: TC,
        id: yp,
        nodeDragThreshold: _C,
        ...NC
      },
      PC,
    ) => {
      const Nu = yp || "1";
      return L.createElement(
        "div",
        {
          ...NC,
          style: { ...TC, ...NV },
          ref: PC,
          className: He(["react-flow", o]),
          "data-testid": "rf__wrapper",
          id: yp,
        },
        L.createElement(
          $E,
          null,
          L.createElement(SV, {
            onInit: u,
            onMove: c,
            onMoveStart: f,
            onMoveEnd: d,
            onNodeClick: a,
            onEdgeClick: l,
            onNodeMouseEnter: p,
            onNodeMouseMove: x,
            onNodeMouseLeave: S,
            onNodeContextMenu: E,
            onNodeDoubleClick: _,
            nodeTypes: i,
            edgeTypes: s,
            connectionLineType: D,
            connectionLineStyle: F,
            connectionLineComponent: z,
            connectionLineContainerStyle: W,
            selectionKeyCode: Y,
            selectionOnDrag: U,
            selectionMode: X,
            deleteKeyCode: H,
            multiSelectionKeyCode: q,
            panActivationKeyCode: te,
            zoomActivationKeyCode: J,
            onlyRenderVisibleElements: Ce,
            selectNodesOnDrag: ae,
            defaultViewport: Fr,
            translateExtent: $r,
            minZoom: zr,
            maxZoom: rn,
            preventScrolling: or,
            zoomOnScroll: Hr,
            zoomOnPinch: qo,
            zoomOnDoubleClick: ar,
            panOnScroll: We,
            panOnScrollSpeed: Pt,
            panOnScrollMode: sr,
            panOnDrag: lr,
            onPaneClick: on,
            onPaneMouseEnter: Ht,
            onPaneMouseMove: Jo,
            onPaneMouseLeave: Tu,
            onPaneScroll: ei,
            onPaneContextMenu: _u,
            onSelectionContextMenu: P,
            onSelectionStart: V,
            onSelectionEnd: M,
            onEdgeContextMenu: ur,
            onEdgeDoubleClick: QE,
            onEdgeMouseEnter: qE,
            onEdgeMouseMove: JE,
            onEdgeMouseLeave: eC,
            onReconnect: oC ?? tC,
            onReconnectStart: iC ?? nC,
            onReconnectEnd: sC ?? rC,
            reconnectRadius: aC ?? lC,
            defaultMarkerColor: Br,
            noDragClassName: fC,
            noWheelClassName: dC,
            noPanClassName: mp,
            elevateEdgesOnSelect: wC,
            rfId: Nu,
            disableKeyboardA11y: gp,
            nodeOrigin: Z,
            nodeExtent: ir,
          }),
          L.createElement(v4, {
            nodes: e,
            edges: t,
            defaultNodes: n,
            defaultEdges: r,
            onConnect: m,
            onConnectStart: y,
            onConnectEnd: g,
            onClickConnectStart: w,
            onClickConnectEnd: h,
            nodesDraggable: de,
            nodesConnectable: Ue,
            nodesFocusable: ue,
            edgesFocusable: qe,
            edgesUpdatable: nn,
            elementsSelectable: Qo,
            elevateNodesOnSelect: xC,
            minZoom: zr,
            maxZoom: rn,
            nodeExtent: ir,
            onNodesChange: uC,
            onEdgesChange: cC,
            snapToGrid: oe,
            snapGrid: pe,
            connectionMode: T,
            translateExtent: $r,
            connectOnClick: mC,
            defaultEdgeOptions: vC,
            fitView: hC,
            fitViewOptions: pC,
            onNodesDelete: R,
            onEdgesDelete: O,
            onNodeDragStart: k,
            onNodeDrag: N,
            onNodeDragStop: A,
            onSelectionDrag: b,
            onSelectionDragStart: $,
            onSelectionDragStop: I,
            noPanClassName: mp,
            nodeOrigin: Z,
            rfId: Nu,
            autoPanOnConnect: SC,
            autoPanOnNodeDrag: EC,
            onError: kC,
            connectionRadius: CC,
            isValidConnection: bC,
            nodeDragThreshold: _C,
          }),
          L.createElement(g4, { onSelectionChange: j }),
          pp,
          L.createElement(UL, { proOptions: yC, position: gC }),
          L.createElement(C4, { rfId: Nu, disableKeyboardA11y: gp }),
        ),
      );
    },
  );
BE.displayName = "ReactFlow";
const PV = (e) => {
  var t;
  return (t = e.domNode) == null ? void 0 : t.querySelector(".react-flow__edgelabel-renderer");
};
function MV({ children: e }) {
  const t = fe(PV);
  return t ? tu.createPortal(e, t) : null;
}
function AV() {
  const e = Ae();
  return v.useCallback((t) => {
    const { domNode: n, updateNodeDimensions: r } = e.getState(),
      i = (Array.isArray(t) ? t : [t]).reduce((s, a) => {
        const l = n == null ? void 0 : n.querySelector(`.react-flow__node[data-id="${a}"]`);
        return l && s.push({ id: a, nodeElement: l, forceUpdate: !0 }), s;
      }, []);
    requestAnimationFrame(() => r(i));
  }, []);
}
const HE = ({
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
  selected: m,
}) => {
  const { background: y, backgroundColor: g } = i || {},
    w = s || y || g;
  return L.createElement("rect", {
    className: He(["react-flow__minimap-node", { selected: m }, u]),
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
HE.displayName = "MiniMapNode";
var RV = v.memo(HE);
const DV = (e) => e.nodeOrigin,
  IV = (e) => e.getNodes().filter((t) => !t.hidden && t.width && t.height),
  Dc = (e) => (e instanceof Function ? e : () => e);
function LV({
  nodeStrokeColor: e = "transparent",
  nodeColor: t = "#e2e2e2",
  nodeClassName: n = "",
  nodeBorderRadius: r = 5,
  nodeStrokeWidth: o = 2,
  nodeComponent: i = RV,
  onClick: s,
}) {
  const a = fe(IV, je),
    l = fe(DV),
    u = Dc(t),
    c = Dc(e),
    f = Dc(n),
    d = typeof window > "u" || window.chrome ? "crispEdges" : "geometricPrecision";
  return L.createElement(
    L.Fragment,
    null,
    a.map((m) => {
      const { x: y, y: g } = _r(m, l).positionAbsolute;
      return L.createElement(i, {
        key: m.id,
        x: y,
        y: g,
        width: m.width,
        height: m.height,
        style: m.style,
        selected: m.selected,
        className: f(m),
        color: u(m),
        borderRadius: r,
        strokeColor: c(m),
        strokeWidth: o,
        shapeRendering: d,
        onClick: s,
        id: m.id,
      });
    }),
  );
}
var VV = v.memo(LV);
const OV = 200,
  jV = 150,
  FV = (e) => {
    const t = e.getNodes(),
      n = {
        x: -e.transform[0] / e.transform[2],
        y: -e.transform[1] / e.transform[2],
        width: e.width / e.transform[2],
        height: e.height / e.transform[2],
      };
    return { viewBB: n, boundingRect: t.length > 0 ? KL(bu(t, e.nodeOrigin), n) : n, rfId: e.rfId };
  },
  zV = "react-flow__minimap-desc";
function UE({
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
  onNodeClick: m,
  pannable: y = !1,
  zoomable: g = !1,
  ariaLabel: w = "React Flow mini map",
  inversePan: h = !1,
  zoomStep: p = 10,
  offsetScale: x = 5,
}) {
  const S = Ae(),
    E = v.useRef(null),
    { boundingRect: _, viewBB: k, rfId: N } = fe(FV, je),
    A = (e == null ? void 0 : e.width) ?? OV,
    R = (e == null ? void 0 : e.height) ?? jV,
    O = _.width / A,
    j = _.height / R,
    $ = Math.max(O, j),
    b = $ * A,
    I = $ * R,
    P = x * $,
    V = _.x - (b - _.width) / 2 - P,
    M = _.y - (I - _.height) / 2 - P,
    T = b + P * 2,
    D = I + P * 2,
    F = `${zV}-${N}`,
    z = v.useRef(0);
  (z.current = $),
    v.useEffect(() => {
      if (E.current) {
        const Y = Ct(E.current),
          U = (q) => {
            const { transform: J, d3Selection: oe, d3Zoom: pe } = S.getState();
            if (q.sourceEvent.type !== "wheel" || !oe || !pe) return;
            const Ce =
                -q.sourceEvent.deltaY *
                (q.sourceEvent.deltaMode === 1 ? 0.05 : q.sourceEvent.deltaMode ? 1 : 0.002) *
                p,
              ae = J[2] * Math.pow(2, Ce);
            pe.scaleTo(oe, ae);
          },
          X = (q) => {
            const {
              transform: J,
              d3Selection: oe,
              d3Zoom: pe,
              translateExtent: Ce,
              width: ae,
              height: de,
            } = S.getState();
            if (q.sourceEvent.type !== "mousemove" || !oe || !pe) return;
            const Ue = z.current * Math.max(1, J[2]) * (h ? -1 : 1),
              ue = {
                x: J[0] - q.sourceEvent.movementX * Ue,
                y: J[1] - q.sourceEvent.movementY * Ue,
              },
              Z = [
                [0, 0],
                [ae, de],
              ],
              qe = yn.translate(ue.x, ue.y).scale(J[2]),
              nn = pe.constrain()(qe, Z, Ce);
            pe.transform(oe, nn);
          },
          te = QS()
            .on("zoom", y ? X : null)
            .on("zoom.wheel", g ? U : null);
        return (
          Y.call(te),
          () => {
            Y.on("zoom", null);
          }
        );
      }
    }, [y, g, h, p]);
  const W = d
      ? (Y) => {
          const U = It(Y);
          d(Y, { x: U[0], y: U[1] });
        }
      : void 0,
    H = m
      ? (Y, U) => {
          const X = S.getState().nodeInternals.get(U);
          m(Y, X);
        }
      : void 0;
  return L.createElement(
    np,
    {
      position: f,
      style: e,
      className: He(["react-flow__minimap", t]),
      "data-testid": "rf__minimap",
    },
    L.createElement(
      "svg",
      {
        width: A,
        height: R,
        viewBox: `${V} ${M} ${T} ${D}`,
        role: "img",
        "aria-labelledby": F,
        ref: E,
        onClick: W,
      },
      w && L.createElement("title", { id: F }, w),
      L.createElement(VV, {
        onClick: H,
        nodeColor: r,
        nodeStrokeColor: n,
        nodeBorderRadius: i,
        nodeClassName: o,
        nodeStrokeWidth: s,
        nodeComponent: a,
      }),
      L.createElement("path", {
        className: "react-flow__minimap-mask",
        d: `M${V - P},${M - P}h${T + P * 2}v${D + P * 2}h${-T - P * 2}z
        M${k.x},${k.y}h${k.width}v${k.height}h${-k.width}z`,
        fill: l,
        fillRule: "evenodd",
        stroke: u,
        strokeWidth: c,
        pointerEvents: "none",
      }),
    ),
  );
}
UE.displayName = "MiniMap";
var $V = v.memo(UE);
function BV() {
  return L.createElement(
    "svg",
    { xmlns: "http://www.w3.org/2000/svg", viewBox: "0 0 32 32" },
    L.createElement("path", {
      d: "M32 18.133H18.133V32h-4.266V18.133H0v-4.266h13.867V0h4.266v13.867H32z",
    }),
  );
}
function HV() {
  return L.createElement(
    "svg",
    { xmlns: "http://www.w3.org/2000/svg", viewBox: "0 0 32 5" },
    L.createElement("path", { d: "M0 0h32v4.2H0z" }),
  );
}
function UV() {
  return L.createElement(
    "svg",
    { xmlns: "http://www.w3.org/2000/svg", viewBox: "0 0 32 30" },
    L.createElement("path", {
      d: "M3.692 4.63c0-.53.4-.938.939-.938h5.215V0H4.708C2.13 0 0 2.054 0 4.63v5.216h3.692V4.631zM27.354 0h-5.2v3.692h5.17c.53 0 .984.4.984.939v5.215H32V4.631A4.624 4.624 0 0027.354 0zm.954 24.83c0 .532-.4.94-.939.94h-5.215v3.768h5.215c2.577 0 4.631-2.13 4.631-4.707v-5.139h-3.692v5.139zm-23.677.94c-.531 0-.939-.4-.939-.94v-5.138H0v5.139c0 2.577 2.13 4.707 4.708 4.707h5.138V25.77H4.631z",
    }),
  );
}
function WV() {
  return L.createElement(
    "svg",
    { xmlns: "http://www.w3.org/2000/svg", viewBox: "0 0 25 32" },
    L.createElement("path", {
      d: "M21.333 10.667H19.81V7.619C19.81 3.429 16.38 0 12.19 0 8 0 4.571 3.429 4.571 7.619v3.048H3.048A3.056 3.056 0 000 13.714v15.238A3.056 3.056 0 003.048 32h18.285a3.056 3.056 0 003.048-3.048V13.714a3.056 3.056 0 00-3.048-3.047zM12.19 24.533a3.056 3.056 0 01-3.047-3.047 3.056 3.056 0 013.047-3.048 3.056 3.056 0 013.048 3.048 3.056 3.056 0 01-3.048 3.047zm4.724-13.866H7.467V7.619c0-2.59 2.133-4.724 4.723-4.724 2.591 0 4.724 2.133 4.724 4.724v3.048z",
    }),
  );
}
function GV() {
  return L.createElement(
    "svg",
    { xmlns: "http://www.w3.org/2000/svg", viewBox: "0 0 25 32" },
    L.createElement("path", {
      d: "M21.333 10.667H19.81V7.619C19.81 3.429 16.38 0 12.19 0c-4.114 1.828-1.37 2.133.305 2.438 1.676.305 4.42 2.59 4.42 5.181v3.048H3.047A3.056 3.056 0 000 13.714v15.238A3.056 3.056 0 003.048 32h18.285a3.056 3.056 0 003.048-3.048V13.714a3.056 3.056 0 00-3.048-3.047zM12.19 24.533a3.056 3.056 0 01-3.047-3.047 3.056 3.056 0 013.047-3.048 3.056 3.056 0 013.048 3.048 3.056 3.056 0 01-3.048 3.047z",
    }),
  );
}
const Ti = ({ children: e, className: t, ...n }) =>
  L.createElement(
    "button",
    { type: "button", className: He(["react-flow__controls-button", t]), ...n },
    e,
  );
Ti.displayName = "ControlButton";
const KV = (e) => ({
    isInteractive: e.nodesDraggable || e.nodesConnectable || e.elementsSelectable,
    minZoomReached: e.transform[2] <= e.minZoom,
    maxZoomReached: e.transform[2] >= e.maxZoom,
  }),
  WE = ({
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
    const d = Ae(),
      [m, y] = v.useState(!1),
      { isInteractive: g, minZoomReached: w, maxZoomReached: h } = fe(KV, je),
      { zoomIn: p, zoomOut: x, fitView: S } = ku();
    if (
      (v.useEffect(() => {
        y(!0);
      }, []),
      !m)
    )
      return null;
    const E = () => {
        p(), i == null || i();
      },
      _ = () => {
        x(), s == null || s();
      },
      k = () => {
        S(o), a == null || a();
      },
      N = () => {
        d.setState({ nodesDraggable: !g, nodesConnectable: !g, elementsSelectable: !g }),
          l == null || l(!g);
      };
    return L.createElement(
      np,
      {
        className: He(["react-flow__controls", u]),
        position: f,
        style: e,
        "data-testid": "rf__controls",
      },
      t &&
        L.createElement(
          L.Fragment,
          null,
          L.createElement(
            Ti,
            {
              onClick: E,
              className: "react-flow__controls-zoomin",
              title: "zoom in",
              "aria-label": "zoom in",
              disabled: h,
            },
            L.createElement(BV, null),
          ),
          L.createElement(
            Ti,
            {
              onClick: _,
              className: "react-flow__controls-zoomout",
              title: "zoom out",
              "aria-label": "zoom out",
              disabled: w,
            },
            L.createElement(HV, null),
          ),
        ),
      n &&
        L.createElement(
          Ti,
          {
            className: "react-flow__controls-fitview",
            onClick: k,
            title: "fit view",
            "aria-label": "fit view",
          },
          L.createElement(UV, null),
        ),
      r &&
        L.createElement(
          Ti,
          {
            className: "react-flow__controls-interactive",
            onClick: N,
            title: "toggle interactivity",
            "aria-label": "toggle interactivity",
          },
          g ? L.createElement(GV, null) : L.createElement(WV, null),
        ),
      c,
    );
  };
WE.displayName = "Controls";
var YV = v.memo(WE),
  Ft;
(function (e) {
  (e.Lines = "lines"), (e.Dots = "dots"), (e.Cross = "cross");
})(Ft || (Ft = {}));
function XV({ color: e, dimensions: t, lineWidth: n }) {
  return L.createElement("path", {
    stroke: e,
    strokeWidth: n,
    d: `M${t[0] / 2} 0 V${t[1]} M0 ${t[1] / 2} H${t[0]}`,
  });
}
function ZV({ color: e, radius: t }) {
  return L.createElement("circle", { cx: t, cy: t, r: t, fill: e });
}
const QV = { [Ft.Dots]: "#91919a", [Ft.Lines]: "#eee", [Ft.Cross]: "#e2e2e2" },
  qV = { [Ft.Dots]: 1, [Ft.Lines]: 1, [Ft.Cross]: 6 },
  JV = (e) => ({ transform: e.transform, patternId: `pattern-${e.rfId}` });
function GE({
  id: e,
  variant: t = Ft.Dots,
  gap: n = 20,
  size: r,
  lineWidth: o = 1,
  offset: i = 2,
  color: s,
  style: a,
  className: l,
}) {
  const u = v.useRef(null),
    { transform: c, patternId: f } = fe(JV, je),
    d = s || QV[t],
    m = r || qV[t],
    y = t === Ft.Dots,
    g = t === Ft.Cross,
    w = Array.isArray(n) ? n : [n, n],
    h = [w[0] * c[2] || 1, w[1] * c[2] || 1],
    p = m * c[2],
    x = g ? [p, p] : h,
    S = y ? [p / i, p / i] : [x[0] / i, x[1] / i];
  return L.createElement(
    "svg",
    {
      className: He(["react-flow__background", l]),
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
        ? L.createElement(ZV, { color: d, radius: p / i })
        : L.createElement(XV, { dimensions: x, color: d, lineWidth: o }),
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
GE.displayName = "Background";
var e5 = v.memo(GE);
const Gt = 40,
  Ll = 44,
  Vl = 16,
  Ol = 16,
  wa = 96;
function KE(e) {
  const t = e ? Object.keys(e) : [];
  return t.length ? Ll + 12 + 2 + t.length * 12 : Ll;
}
function t5(e) {
  return e + Gt / 2;
}
const Dn = 260,
  gr = 140,
  YE = 180,
  cd = 100,
  Ga = Gt + 64,
  fd = Gt + 56,
  yo = 8,
  dd = (e) => Math.round(e / yo) * yo,
  hp = 24,
  Sa = (e) => (e ? (Array.isArray(e) ? e : [e]) : []),
  n5 = (e) =>
    Sa(e == null ? void 0 : e.entry).length +
      Sa(e == null ? void 0 : e.exit).length +
      Sa(e == null ? void 0 : e.invoke).length +
      Sa(e == null ? void 0 : e.activities).length >
    0;
function XE(e, t = "") {
  const n = [];
  for (const r of Object.keys(e.states ?? {})) {
    const o = e.states[r] ?? {},
      i = t ? `${t}.${r}` : r;
    n.push({ id: i, key: r, def: o }), o.states && n.push(...XE(o, i));
  }
  return n;
}
function jl(e) {
  return e
    ? typeof e == "string"
      ? [e]
      : Array.isArray(e)
        ? e.flatMap(jl)
        : typeof e == "object" && e.target
          ? jl(e.target)
          : []
    : [];
}
function ZE(e, t = "") {
  const n = [],
    r = (o) => (t ? `${t}.${o}` : o);
  if (e.on)
    for (const o of Object.keys(e.on))
      for (const i of jl(e.on[o]))
        n.push({ source: t || "ROOT", target: t ? `${t}.${i}` : i, label: o });
  for (const o of Object.keys(e.states ?? {})) {
    const i = e.states[o] ?? {},
      s = r(o);
    if (i.on)
      for (const a of Object.keys(i.on))
        for (const l of jl(i.on[a])) {
          const u = l.startsWith("#") ? l.slice(1) : l.includes(".") ? l : r(l);
          n.push({ source: s, target: u, label: a });
        }
    i.states && n.push(...ZE(i, s));
  }
  return n;
}
function r5(e, t, n) {
  const r = new Set(e),
    o = new Map(),
    i = new Map();
  for (const l of e) o.set(l, new Set()), i.set(l, new Set());
  for (const l of t)
    !r.has(l.source) ||
      !r.has(l.target) ||
      (o.get(l.source).add(l.target), i.get(l.target).add(l.source));
  const s = [],
    a = new Set();
  for (n && r.has(n) && (s.push([n]), a.add(n)); a.size < e.length; ) {
    const l = s[s.length - 1] || [],
      u = [];
    for (const c of l) for (const f of o.get(c) || []) a.has(f) || (u.push(f), a.add(f));
    if (u.length === 0) {
      const c = e.filter((f) => !a.has(f));
      c.length > 0 && (u.push(c[0]), a.add(c[0]));
    }
    if (u.length > 0) s.push(u);
    else break;
  }
  return s.filter((l) => l.length > 0);
}
function o5(e, t) {
  const n = {};
  let r = Ga;
  for (const o of e) {
    const i = o.length * gr + Math.max(0, o.length - 1) * cd;
    let s = t + fd + Math.max(0, (0 - i) / 2);
    for (const a of o) (n[a] = { x: dd(r), y: dd(s) }), (s += gr + cd);
    r += Dn + YE;
  }
  return n;
}
function i5(e) {
  return e.replace(/[^a-zA-Z0-9_]+/g, "_");
}
function s5(e, t, n, r, o, i) {
  const s = e.x + n / 2,
    a = e.y + r / 2,
    l = t.x + o / 2,
    u = t.y + i / 2,
    c = l - s,
    f = u - a;
  return Math.abs(c) > Math.abs(f)
    ? c > 0
      ? { sh: "r", th: "L" }
      : { sh: "l", th: "R" }
    : f > 0
      ? { sh: "b", th: "T" }
      : { sh: "t", th: "B" };
}
function a5(e, t) {
  const n = new Map(),
    r = (o, i, s, a) => {
      const l = `${o}|${i}|${s ? "S" : "T"}`;
      (n.get(l) || n.set(l, []).get(l)).push(a);
    };
  for (let o = 0; o < e.length; o++) {
    const i = e[o];
    if (!t.has(i.source) || !t.has(i.target)) continue;
    const s = (i.sourceHandle ?? "").charAt(0),
      a = (i.targetHandle ?? "").charAt(0);
    s && r(i.source, s, !0, { ei: o, side: s, isSource: !0 }),
      a && r(i.target, a, !1, { ei: o, side: a, isSource: !1 });
  }
  for (const [, o] of n) {
    o.sort((s, a) => s.ei - a.ei);
    const i = o.length;
    for (let s = 0; s < i; s++) {
      const a = o[s],
        l = Math.min(hp - 1, s),
        u = `${a.side}${l}`;
      a.isSource ? (e[a.ei].sourceHandle = u) : (e[a.ei].targetHandle = u);
    }
  }
}
function l5(e, t) {
  var i, s;
  const n = new Map(),
    r = (a, l) => {
      const u = (l ?? "").charAt(0),
        f = (Math.max(0, parseInt((l ?? "").slice(1)) || 0) + 1) / (hp + 1);
      switch (u) {
        case "l":
          return { x: a.x, y: a.y + a.h * f };
        case "r":
          return { x: a.x + a.w, y: a.y + a.h * f };
        case "t":
          return { x: a.x + a.w * f, y: a.y };
        case "b":
          return { x: a.x + a.w * f, y: a.y + a.h };
        case "L":
          return { x: a.x, y: a.y + a.h * f };
        case "R":
          return { x: a.x + a.w, y: a.y + a.h * f };
        case "T":
          return { x: a.x + a.w * f, y: a.y };
        case "B":
          return { x: a.x + a.w * f, y: a.y + a.h };
        default:
          return { x: a.x + a.w / 2, y: a.y + a.h / 2 };
      }
    };
  for (let a = 0; a < e.length; a++) {
    const l = e[a],
      u = t.get(l.source),
      c = t.get(l.target);
    if (!u || !c) continue;
    const f = r(u, l.sourceHandle),
      d = r(c, l.targetHandle),
      m = (i = l.sourceHandle) == null ? void 0 : i.charAt(0),
      y = m === "l" || m === "r",
      g = y ? (f.x + d.x) / 2 : (f.y + d.y) / 2,
      w = y ? Math.min(f.y, d.y) : Math.min(f.x, d.x),
      h = y ? Math.max(f.y, d.y) : Math.max(f.x, d.x),
      p = Math.round(g / yo) * yo,
      x = Math.round(w / (yo * 2)),
      S = Math.round(h / (yo * 2)),
      E = `${y ? "H" : "V"}|${p}|${x}-${S}`;
    (n.get(E) || n.set(E, []).get(E)).push(a);
  }
  const o = 10;
  for (const a of n.values()) {
    if (a.length <= 1) continue;
    a.sort((u, c) => u - c);
    const l = a.length;
    for (let u = 0; u < l; u++) {
      const c = u - (l - 1) / 2,
        f = a[u],
        d = e[f],
        m = (s = d.sourceHandle) == null ? void 0 : s.charAt(0),
        y = m === "l" || m === "r";
      d.data = { ...(d.data ?? {}), laneAxis: y ? "x" : "y", laneOffset: c * o };
    }
  }
}
async function u5(e, t) {
  var w, h;
  const n = e.id ?? "StateMachine",
    r = `${n}__root`,
    o = XE(e),
    i = o.map((p) => p.id),
    s = ZE(e).filter((p) => i.includes(p.source) && i.includes(p.target)),
    a = r5(
      i,
      s.map(({ source: p, target: x }) => ({ source: p, target: x })),
      e.initial,
    ),
    l = Math.max(KE(t) + Vl, Ll + Vl),
    u = o5(a, l),
    c = Math.max(980, Ga * 2 + Math.max(Dn, a.length * Dn + (a.length - 1) * YE)),
    f = Math.max(...a.map((p) => p.length * gr + Math.max(0, p.length - 1) * cd), gr),
    d = Math.max(560, l + fd * 2 + f),
    m = [
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
  for (const p of o) {
    const x = u[p.id] ?? { x: Ga, y: l + fd };
    m.push({
      id: p.id,
      type: (w = p.def) != null && w.states ? "compoundStateNode" : "stateNode",
      data: { label: p.key, definition: p.def, machineId: n, headerOnly: !n5(p.def) },
      position: x,
      style: { width: Dn },
      parentId: r,
      extent: "parent",
      draggable: !0,
    });
  }
  const y = [],
    g = new Map();
  for (const p of o) g.set(p.id, { x: u[p.id].x, y: u[p.id].y, w: Dn, h: gr });
  for (const p of s) {
    const x = s5(u[p.source], u[p.target], Dn, gr, Dn, gr);
    y.push({
      id: `edge_${p.source}_${p.target}_${i5(p.label)}`,
      source: p.source,
      target: p.target,
      sourceHandle: x.sh,
      targetHandle: x.th,
      type: "transitionEdge",
      data: { label: p.label },
    });
  }
  if ((a5(y, g), l5(y, g), e.initial && i.includes(e.initial))) {
    const p = "__initial__root",
      x = (((h = u[e.initial]) == null ? void 0 : h.x) ?? Ga) + Dn / 2;
    m.push({
      id: p,
      type: "initialNode",
      data: {},
      position: { x: dd(x), y: Math.max(12, l - 56) },
      parentId: r,
      extent: "parent",
      draggable: !1,
      selectable: !1,
    });
    const S = Math.floor(hp / 2);
    y.push({
      id: `e_${p}_${e.initial}`,
      source: p,
      target: e.initial,
      sourceHandle: "b",
      targetHandle: `T${S}`,
      type: "transitionEdge",
      data: { isInitial: !0, label: "" },
    });
  }
  return { nodes: m, edges: y };
}
function c5(e, t) {
  const n = v.useCallback(() => {
      try {
        const s = localStorage.getItem(e);
        if (!s) return new Map();
        const a = JSON.parse(s);
        return new Map(Object.entries(a));
      } catch {
        return new Map();
      }
    }, [e]),
    r = v.useCallback(
      (s) => {
        const a = n();
        return a.size === 0
          ? s
          : s.map((l) => {
              const u = a.get(l.id);
              return u ? { ...l, position: { x: u.x, y: u.y } } : l;
            });
      },
      [n],
    ),
    o = v.useCallback(() => {
      try {
        const s = {};
        for (const a of t()) s[a.id] = { x: a.position.x, y: a.position.y };
        localStorage.setItem(e, JSON.stringify(s));
      } catch {}
    }, [t, e]),
    i = v.useCallback(
      (s) => {
        try {
          const a = {};
          for (const l of s) a[l.id] = { x: l.position.x, y: l.position.y };
          localStorage.setItem(e, JSON.stringify(a));
        } catch {}
      },
      [e],
    );
  return {
    loadSavedPositions: n,
    applySavedPositions: r,
    savePositionsFromGraph: o,
    savePositionsSnapshot: i,
  };
}
function f5(e, t) {
  const n = v.useMemo(() => {
      try {
        const a = localStorage.getItem(e);
        if (!a) return null;
        const l = JSON.parse(a);
        if (l && typeof l.x == "number" && typeof l.y == "number" && typeof l.zoom == "number")
          return l;
      } catch {}
      return null;
    }, [e]),
    [r, o] = v.useState(n ?? void 0),
    i = v.useCallback(() => {
      try {
        const a = localStorage.getItem(e);
        if (!a) return null;
        const l = JSON.parse(a);
        return typeof l == "object" &&
          l !== null &&
          typeof l.x == "number" &&
          typeof l.y == "number" &&
          typeof l.zoom == "number"
          ? l
          : null;
      } catch {
        return null;
      }
    }, [e]),
    s = v.useCallback(
      (a) => {
        try {
          const l = a ?? (t == null ? void 0 : t());
          if (!l) return;
          localStorage.setItem(e, JSON.stringify(l));
        } catch {}
      },
      [e, t],
    );
  return {
    initialViewport: n,
    viewport: r,
    setViewportState: o,
    loadSavedViewport: i,
    saveViewport: s,
  };
}
function d5(e) {
  const t = v.useCallback(
      (r, o) => {
        const i = new Set(e),
          s = new Set();
        for (const a of o) i.has(a.source) && s.add(a.target);
        return r.map((a) => ({
          ...a,
          data: { ...a.data, uiStatus: i.has(a.id) ? "active" : s.has(a.id) ? "next" : void 0 },
        }));
      },
      [e],
    ),
    n = v.useCallback(
      (r) => {
        const o = new Set(e),
          i = new Set();
        for (const s of r) o.has(s.source) && i.add(s.target);
        return r.map((s) => ({
          ...s,
          data: { ...(s.data ?? {}), uiActive: o.has(s.source) || i.has(s.source) },
        }));
      },
      [e],
    );
  return { decorateStatuses: t, decorateEdgeStatuses: n };
}
const h5 = 24;
function p5() {
  const e = v.useCallback((o, i, s) => {
      const a = o.x,
        l = o.y,
        u = o.x + o.w,
        c = o.y + o.h,
        f = i.x,
        d = i.y,
        m = i.x + i.w,
        y = i.y + i.h,
        g = a + o.w / 2,
        w = l + o.h / 2,
        h = f + i.w / 2,
        p = d + i.h / 2,
        x = d + Math.min(24, i.h * 0.35),
        S = y - Math.min(24, i.h * 0.35),
        E = w >= x && w <= S,
        _ = f + Math.min(36, i.w * 0.35),
        k = m - Math.min(36, i.w * 0.35),
        N = g >= _ && g <= k;
      if (E) {
        const T = g < f ? "L" : g > m ? "R" : (s ?? (h >= g ? "L" : "R"));
        return { sh: T === "L" ? "r" : "l", th: T, dir: T };
      }
      if (N) {
        const T = w < d ? "T" : w > y ? "B" : (s ?? (p >= w ? "T" : "B"));
        return { sh: T === "T" ? "b" : "t", th: T, dir: T };
      }
      const A = h - g,
        R = p - w,
        O = Math.abs(R) * 0.6,
        j = Math.abs(A) * 0.6,
        $ = Math.max(0, f - u) + O,
        b = Math.max(0, a - m) + O,
        I = Math.max(0, d - c) + j,
        P = Math.max(0, l - y) + j,
        V = [
          { dir: "L", sh: "r", th: "L", cost: $ },
          { dir: "R", sh: "l", th: "R", cost: b },
          { dir: "T", sh: "b", th: "T", cost: I },
          { dir: "B", sh: "t", th: "B", cost: P },
        ];
      let M = V[0];
      for (const T of V) T.cost < M.cost && (M = T);
      if (s) {
        const T = V.find((F) => F.dir === s);
        T && T.cost <= M.cost + 18 && (M = T);
      }
      return { sh: M.sh, th: M.th, dir: M.dir };
    }, []),
    t = v.useCallback((o) => {
      var s, a;
      const i = new Map();
      for (const l of o) {
        const u = l.width ?? ((s = l.style) == null ? void 0 : s.width) ?? 160,
          c =
            l.height ??
            ((a = l.style) == null ? void 0 : a.height) ??
            (l.type === "eventNode" ? 36 : 120);
        i.set(l.id, { x: l.position.x, y: l.position.y, w: u, h: c });
      }
      return i;
    }, []);
  function n(o, i) {
    const s = new Map(),
      a = (l, u, c, f) => {
        const d = `${l}|${u}|${c ? "S" : "T"}`;
        (s.get(d) || s.set(d, []).get(d)).push(f);
      };
    for (let l = 0; l < o.length; l++) {
      const u = o[l],
        c = i.get(u.source),
        f = i.get(u.target);
      if (!c || !f) continue;
      const d = c.x + c.w / 2,
        m = c.y + c.h / 2,
        y = f.x + f.w / 2,
        g = f.y + f.h / 2,
        w = (u.sourceHandle ?? "").charAt(0),
        h = (u.targetHandle ?? "").charAt(0);
      w &&
        a(u.source, w, !0, { ei: l, side: w, isSource: !0, key: w === "l" || w === "r" ? g : y }),
        h &&
          a(u.target, h, !1, { ei: l, side: h, isSource: !1, key: h === "L" || h === "R" ? m : d });
    }
    for (const [, l] of s) {
      l.sort((u, c) => u.key - c.key);
      for (let u = 0; u < l.length; u++) {
        const c = l[u],
          f = `${c.side}${Math.min(h5 - 1, u)}`;
        c.isSource ? (o[c.ei].sourceHandle = f) : (o[c.ei].targetHandle = f);
      }
    }
  }
  const r = v.useCallback(
    (o, i, s) => {
      const a = t(i);
      let l = !1;
      const u = o.map((c) => {
        var p, x, S;
        if (!a.has(c.source) || !a.has(c.target) || (s && !s.has(c.source) && !s.has(c.target)))
          return c;
        const f = a.get(c.source),
          d = a.get(c.target),
          m = (p = c.data) == null ? void 0 : p.dir,
          { sh: y, th: g, dir: w } = e(f, d, m);
        return ((x = c.sourceHandle) == null ? void 0 : x.startsWith(y)) &&
          ((S = c.targetHandle) == null ? void 0 : S.startsWith(g)) &&
          m === w
          ? c
          : ((l = !0),
            { ...c, sourceHandle: y, targetHandle: g, data: { ...(c.data ?? {}), dir: w } });
      });
      return n(u, a), l ? u : o;
    },
    [t, e],
  );
  return { pickHandlesRuntime: e, getNodeBoxes: t, recomputeEdgeHandles: r };
}
const Ic = () => new Promise((e) => requestAnimationFrame(() => e()));
function m5(e) {
  const {
      reservedTop: t,
      headerGuardTop: n,
      fitView: r,
      getNodes: o,
      updateNodeInternals: i,
      saveViewport: s,
      hasSavedPositions: a,
    } = e,
    l = v.useCallback((y) => {
      const g = y.find((w) => w.type === "rootNode");
      return g
        ? y.map((w) =>
            w.id === g.id
              ? w
              : { ...w, parentId: g.id, extent: "parent", draggable: !0, expandParent: !0 },
          )
        : y;
    }, []),
    u = v.useCallback(
      (y, g) => {
        const w = y.find((R) => R.type === "rootNode");
        if (!w) return null;
        const h = y.filter((R) => R.parentId === w.id);
        if (!h.length) return null;
        let p = 1 / 0,
          x = 1 / 0,
          S = -1 / 0,
          E = -1 / 0;
        for (const R of h) {
          const O = R.width ?? 0,
            j = R.height ?? 0;
          (p = Math.min(p, R.position.x)),
            (x = Math.min(x, R.position.y)),
            (S = Math.max(S, R.position.x + O)),
            (E = Math.max(E, R.position.y + j));
        }
        const _ = new Map(y.map((R) => [R.id, R]));
        for (const R of g) {
          const O = _.get(R.source),
            j = _.get(R.target);
          if (!O || !j || O.parentId !== w.id || j.parentId !== w.id) continue;
          const $ = O.position.x + (O.width ?? 0) / 2,
            b = O.position.y + (O.height ?? 0) / 2,
            I = j.position.x + (j.width ?? 0) / 2,
            P = j.position.y + (j.height ?? 0) / 2;
          (p = Math.min(p, Math.min($, I) - wa)),
            (S = Math.max(S, Math.max($, I) + wa)),
            (x = Math.min(x, Math.min(b, P) - wa)),
            (E = Math.max(E, Math.max(b, P) + wa));
        }
        const k = Math.max(x, n),
          N = Math.max(S - p + Gt, 320),
          A = Math.max(E - k + Gt + t, t + 200);
        return { minX: p, minY: x, width: N, height: A };
      },
      [t, n],
    ),
    c = v.useCallback(
      (y, g) => {
        const w = y.find((k) => k.type === "rootNode"),
          h = u(y, g);
        if (!w || !h) return y;
        const p = Gt / 2,
          x = n;
        let S = h.minX - p,
          E = h.minY - x;
        Math.abs(S) < 0.5 && (S = 0), Math.abs(E) < 0.5 && (E = 0);
        const _ = y.map((k) => {
          var N, A;
          return k.id === w.id
            ? {
                ...k,
                position: {
                  x: (((N = k.position) == null ? void 0 : N.x) ?? 0) + S,
                  y: (((A = k.position) == null ? void 0 : A.y) ?? 0) + E,
                },
                style: { ...k.style, width: h.width, height: h.height },
              }
            : k.parentId === w.id
              ? { ...k, position: { x: k.position.x - S, y: k.position.y - E } }
              : k;
        });
        return i(w.id), _;
      },
      [u, n, i],
    ),
    f = v.useCallback(
      (y, g) => {
        const w = y.find((k) => k.type === "rootNode"),
          h = u(y, g);
        if (!w || !h) return y;
        const p = Gt / 2,
          x = n,
          S = h.minX - p,
          E = h.minY - x,
          _ = y.map((k) => {
            var N, A;
            return k.id === w.id
              ? {
                  ...k,
                  position: {
                    x: (((N = k.position) == null ? void 0 : N.x) ?? 0) + S,
                    y: (((A = k.position) == null ? void 0 : A.y) ?? 0) + E,
                  },
                  style: { ...k.style, width: h.width, height: h.height },
                }
              : k.parentId === w.id
                ? { ...k, position: { x: k.position.x - S, y: k.position.y - E } }
                : k;
          });
        return i(w.id), _;
      },
      [u, n, i],
    ),
    d = v.useCallback(
      async (y, g) => {
        await Ic(),
          await Ic(),
          o()
            .filter((h) => h.type !== "rootNode")
            .map((h) => h.id)
            .forEach((h) => i(h)),
          await Ic(),
          g == null || g.adjustPositions,
          r({ duration: 500, padding: 0.18, includeHiddenNodes: !0 }),
          setTimeout(() => s(), 0);
      },
      [o, i, r, s, a],
    ),
    m = v.useCallback(
      (y, g) => {
        var N, A, R, O, j, $;
        const w = g.find((b) => b.type === "rootNode");
        if (!w) return y;
        let h = w.width ?? ((N = w.style) == null ? void 0 : N.width),
          p = w.height ?? ((A = w.style) == null ? void 0 : A.height);
        if (h == null || p == null) {
          const b = u(g, y);
          b && (h ?? (h = b.width), p ?? (p = b.height));
        }
        const x = 22,
          S = (((R = w.position) == null ? void 0 : R.y) ?? 0) + e.reservedTop + 24,
          E = (((O = w.position) == null ? void 0 : O.x) ?? 0) + Gt / 2 + x,
          _ =
            h != null
              ? (((j = w.position) == null ? void 0 : j.x) ?? 0) + h - Gt / 2 - x
              : Number.POSITIVE_INFINITY,
          k =
            p != null
              ? ((($ = w.position) == null ? void 0 : $.y) ?? 0) + p - Gt / 2 - x
              : Number.POSITIVE_INFINITY;
        return y.map((b) => ({
          ...b,
          data: { ...(b.data ?? {}), clampTopY: S, clampLeftX: E, clampRightX: _, clampBottomY: k },
        }));
      },
      [u, e.reservedTop],
    );
  return {
    ensureUnderRoot: l,
    computeRootBounds: u,
    guardHeaderAndMaybeGrow: c,
    fitRootTightly: f,
    tightenAndFitWhenReady: d,
    withHeaderClamp: m,
  };
}
const g5 = ({ machine: e, activeStateIds: t, autoFitAfterDrag: n = !0 }) => {
    const [r, o] = v.useState([]),
      [i, s] = v.useState([]),
      [a, l] = v.useState(!1),
      u = v.useRef([]);
    v.useEffect(() => {
      u.current = r;
    }, [r]);
    const c = v.useRef(!1),
      { fitView: f, getNodes: d, getViewport: m } = ku(),
      y = AV(),
      g = v.useMemo(() => `xsi.positions.${e.id}`, [e.id]),
      w = v.useMemo(() => `xsi.viewport.${e.id}`, [e.id]),
      h = v.useMemo(() => Math.max(KE(e.context) + Vl, Ll + Vl), [e.context]),
      p = v.useMemo(() => t5(h), [h]),
      {
        initialViewport: x,
        viewport: S,
        setViewportState: E,
        loadSavedViewport: _,
        saveViewport: k,
      } = f5(w, m),
      {
        loadSavedPositions: N,
        applySavedPositions: A,
        savePositionsFromGraph: R,
        savePositionsSnapshot: O,
      } = c5(g, d),
      { decorateStatuses: j, decorateEdgeStatuses: $ } = d5(t),
      { recomputeEdgeHandles: b } = p5(),
      {
        ensureUnderRoot: I,
        guardHeaderAndMaybeGrow: P,
        fitRootTightly: V,
        tightenAndFitWhenReady: M,
        withHeaderClamp: T,
      } = m5({
        reservedTop: h,
        headerGuardTop: p,
        fitView: f,
        getNodes: d,
        updateNodeInternals: y,
        saveViewport: k,
        hasSavedPositions: a,
      }),
      D = v.useCallback(
        async (U) => {
          if (U != null && U.resetSavedPositions) {
            try {
              localStorage.removeItem(g);
            } catch {}
            l(!1);
          }
          const { nodes: X, edges: te } = await u5(e.definition, e.context),
            q = $(te),
            J = I(X),
            oe = j(J, q),
            pe = U != null && U.resetSavedPositions ? !1 : N().size > 0;
          l(pe);
          const Ce = pe ? A(oe) : oe,
            ae = pe ? Ce : P(Ce, q),
            de = T(q, ae);
          s(de), o(ae), U != null && U.resetSavedPositions && O(ae);
          const Ue = _();
          x ? E(x) : Ue ? E(Ue) : M(de, { adjustPositions: !pe }).catch(console.error);
        },
        [e.definition, e.context, I, j, $, A, P, M, N, _, x, T, O, g],
      );
    v.useEffect(() => {
      D().catch(console.error);
    }, [D]),
      v.useEffect(() => {
        s((U) => $(U)), o((U) => j(U, i));
      }, [t, j, $]);
    const F = v.useCallback(
        (U) => {
          let X = !1;
          const te = new Set(),
            q = new Set();
          for (const J of U)
            J.type === "position" && (q.add(J.id), J.dragging ? te.add(J.id) : (X = !0));
          o((J) => {
            const oe = PE(U, J);
            if (U.some((ae) => ae.type === "position" && ae.dragging)) {
              const ae = P(oe, i);
              return s((de) => T(b(de, ae, te), ae)), j(ae, i);
            }
            if (X)
              return c.current ? ((c.current = !1), J) : (s((ae) => T(b(ae, oe, q), oe)), j(oe, i));
            const Ce = P(oe, i);
            return s((ae) => T(b(ae, Ce), Ce)), j(Ce, i);
          });
        },
        [i, j, P, T, b],
      ),
      z = v.useCallback((U) => s((X) => T($(O4(U, X)), u.current)), [$, T]),
      W = v.useCallback(() => {
        (c.current = !0), setTimeout(() => (c.current = !1), 0);
        let U = null;
        o((te) => {
          const q = V(te, i);
          U = q;
          const J = q.filter((oe) => oe.type !== "rootNode").map((oe) => oe.id);
          return setTimeout(() => J.forEach((oe) => y(oe)), 0), s((oe) => T(b(oe, q), q)), q;
        });
        const X = U;
        X && X.length > 0 ? O(X) : R(),
          k(),
          n &&
            setTimeout(() => {
              s((te) => T(te, u.current)),
                M(T(i, u.current), { adjustPositions: !1 }).catch(console.error);
            }, 0);
      }, [i, V, y, M, n, R, O, k, T, b]),
      H = v.useCallback(
        (U, X) => {
          X && E(X), k(X);
        },
        [k],
      ),
      Y = v.useCallback((U) => {
        E(U);
      }, []);
    return {
      nodes: r,
      edges: i,
      onNodesChange: F,
      onEdgesChange: z,
      onNodeDragStop: W,
      relayout: D,
      tightenAndFitWhenReady: M,
      hasSavedPositions: a,
      onMoveEnd: H,
      initialViewport: x,
      viewport: S,
      onViewportChange: Y,
    };
  },
  y5 = ({ x: e, y: t, onClose: n, onAutoLayout: r, onFitView: o }) =>
    C.jsxs("div", {
      style: { left: e, top: t },
      className: "absolute z-50 rounded-md border bg-popover text-popover-foreground shadow-md",
      onMouseLeave: n,
      children: [
        C.jsx("button", {
          className: "w-full text-left px-3 py-2 hover:bg-muted",
          onClick: () => {
            n(), r();
          },
          children: "Auto layout",
        }),
        C.jsx("button", {
          className: "w-full text-left px-3 py-2 hover:bg-muted",
          onClick: () => {
            n(), o();
          },
          children: "Fit view",
        }),
      ],
    }),
  Jy = (e) => (e ? (Array.isArray(e) ? e : [e]) : []),
  e0 = ({ title: e, items: t, icon: n, colorClass: r }) =>
    t != null && t.length
      ? C.jsxs("div", {
          className: "mb-2 last:mb-0",
          children: [
            C.jsx("h4", {
              className:
                "text-[10px] font-semibold text-muted-foreground mb-1 tracking-wide uppercase",
              children: e,
            }),
            t.map((o, i) =>
              C.jsxs(
                "div",
                {
                  className: "flex items-center gap-2 text-[12px] leading-5",
                  children: [
                    C.jsx(n, { className: se("w-3.5 h-3.5 shrink-0", r) }),
                    C.jsx("span", { className: "truncate", children: o.type ?? o.src ?? o }),
                  ],
                },
                i,
              ),
            ),
          ],
        })
      : null,
  t0 = 24;
function Xe({ side: e, type: t, upper: n }) {
  const r = e === "top" || e === "bottom",
    o = e === "top" ? K.Top : e === "bottom" ? K.Bottom : e === "left" ? K.Left : K.Right;
  return C.jsx(C.Fragment, {
    children: Array.from({ length: t0 }).map((i, s) => {
      const a = ((s + 1) / (t0 + 1)) * 100,
        l = r ? { left: `${a}%` } : { top: `${a}%` };
      return C.jsx(
        ws,
        { id: `${n}${s}`, type: t, position: o, className: "!opacity-0", style: l },
        `${n}${s}`,
      );
    }),
  });
}
const v5 = ({ data: e }) => {
    var s, a, l;
    const t = Jy((s = e.definition) == null ? void 0 : s.entry),
      n = Jy((a = e.definition) == null ? void 0 : a.invoke),
      r = t.length > 0 || n.length > 0,
      o = ((l = e.definition) == null ? void 0 : l.type) === "final",
      i = e.uiStatus;
    return C.jsxs(_s, {
      className: se(
        "w-[240px] rounded-lg border-2 shadow-md",
        i === "active" && "border-blue-500 bg-blue-500/10",
        i === "next" && "border-blue-400/50",
        o && "border-dashed",
      ),
      children: [
        C.jsx(Xe, { side: "top", type: "target", upper: "T" }),
        C.jsx(Xe, { side: "bottom", type: "target", upper: "B" }),
        C.jsx(Xe, { side: "left", type: "target", upper: "L" }),
        C.jsx(Xe, { side: "right", type: "target", upper: "R" }),
        C.jsx(Ns, {
          className: se(
            "p-2.5 rounded-t-md",
            i === "active" ? "bg-blue-500 text-white" : "bg-muted",
          ),
          children: C.jsx(Ps, {
            className: "text-[13px] font-semibold tracking-wide",
            children: e.label,
          }),
        }),
        r &&
          C.jsxs(Ms, {
            className: "p-3",
            children: [
              C.jsx(e0, {
                title: "Entry actions",
                items: t,
                icon: Xk,
                colorClass: "text-yellow-500",
              }),
              C.jsx(e0, { title: "Invoke", items: n, icon: Bk, colorClass: "text-blue-500" }),
            ],
          }),
        !o &&
          C.jsxs(C.Fragment, {
            children: [
              C.jsx(Xe, { side: "top", type: "source", upper: "t" }),
              C.jsx(Xe, { side: "bottom", type: "source", upper: "b" }),
              C.jsx(Xe, { side: "left", type: "source", upper: "l" }),
              C.jsx(Xe, { side: "right", type: "source", upper: "r" }),
            ],
          }),
      ],
    });
  },
  x5 = ({ data: e }) =>
    C.jsxs("div", {
      className:
        "bg-card text-card-foreground rounded-md text-sm font-medium border-2 px-4 py-2 shadow-sm",
      children: [
        e.label,
        C.jsx(Xe, { side: "top", type: "target", upper: "T" }),
        C.jsx(Xe, { side: "bottom", type: "target", upper: "B" }),
        C.jsx(Xe, { side: "left", type: "target", upper: "L" }),
        C.jsx(Xe, { side: "right", type: "target", upper: "R" }),
        C.jsx(Xe, { side: "top", type: "source", upper: "t" }),
        C.jsx(Xe, { side: "bottom", type: "source", upper: "b" }),
        C.jsx(Xe, { side: "left", type: "source", upper: "l" }),
        C.jsx(Xe, { side: "right", type: "source", upper: "r" }),
      ],
    }),
  w5 = (e) =>
    C.jsx("div", {
      className: se(
        "rounded-lg border-2 bg-secondary/20",
        e.selected ? "border-primary/60" : "border-border",
      ),
      children: C.jsx("div", {
        className:
          "p-2 text-[12px] font-bold text-muted-foreground cursor-move border-b bg-secondary/30 rounded-t-lg",
        children: e.data.label,
      }),
    }),
  S5 = ({ data: e }) => {
    const t = Object.entries(e.context ?? {}).map(([n, r]) => ({ key: n, type: typeof r }));
    return C.jsxs(_s, {
      className: se(
        "w-full h-full flex flex-col rounded-xl bg-transparent pointer-events-none border-[6px] border-neutral-300/60 dark:border-neutral-700/80",
      ),
      children: [
        C.jsx(Ns, {
          className:
            "root-drag-handle p-3 border-b bg-muted/80 backdrop-blur-sm rounded-t-lg cursor-move pointer-events-auto",
          children: C.jsx(Ps, {
            className: "text-[15px] font-semibold tracking-wide text-foreground",
            children: e.label,
          }),
        }),
        t.length > 0 &&
          C.jsxs(Ms, {
            className: "px-3 py-1 border-b bg-muted/80 backdrop-blur-sm pointer-events-none",
            children: [
              C.jsx("h4", {
                className:
                  "text-[10px] font-semibold text-muted-foreground mb-0.5 tracking-wide uppercase",
                children: "Context",
              }),
              t.map(({ key: n, type: r }) =>
                C.jsxs(
                  "div",
                  {
                    className: "text-[12px] leading-5",
                    children: [
                      C.jsx("span", { className: "font-mono font-medium", children: n }),
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
  E5 = () => C.jsx("div", { className: "w-0 h-0" });
function C5(e) {
  const { sx: t, sy: n, tx: r, ty: o, sp: i, tp: s, centerBias: a, bounds: l } = e,
    u = (l == null ? void 0 : l.left) ?? -1 / 0,
    c = (l == null ? void 0 : l.right) ?? 1 / 0,
    f = (l == null ? void 0 : l.top) ?? -1 / 0,
    d = (l == null ? void 0 : l.bottom) ?? 1 / 0,
    m = i,
    y = m === K.Left || m === K.Right,
    g = (t + r) / 2 + ((a == null ? void 0 : a.x) ?? 0),
    w = (n + o) / 2 + ((a == null ? void 0 : a.y) ?? 0),
    h = Math.max(u, Math.min(g, c)),
    p = Math.max(f, Math.min(w, d)),
    x = y ? 22 : 18,
    [S, E, _] = Dl({
      sourceX: t,
      sourceY: n,
      targetX: r,
      targetY: o,
      sourcePosition: i,
      targetPosition: s,
      borderRadius: 10,
      centerX: h,
      centerY: p,
      offset: x,
    });
  return { d: S, lx: E, ly: _ };
}
const b5 = ({
    id: e,
    sourceX: t,
    sourceY: n,
    targetX: r,
    targetY: o,
    sourcePosition: i,
    targetPosition: s,
    markerEnd: a,
    data: l,
  }) => {
    const u = l == null ? void 0 : l.clampTopY,
      c = l == null ? void 0 : l.clampLeftX,
      f = l == null ? void 0 : l.clampRightX,
      d = l == null ? void 0 : l.clampBottomY,
      m = l == null ? void 0 : l.laneAxis,
      y = (l == null ? void 0 : l.laneOffset) ?? 0,
      g = !!(l != null && l.isInitial),
      w = !!(l != null && l.uiActive),
      h = l == null ? void 0 : l.label,
      p = m === "x" ? { x: y } : m === "y" ? { y } : {},
      {
        d: x,
        lx: S,
        ly: E,
      } = C5({
        sx: t,
        sy: n,
        tx: r,
        ty: o,
        sp: i,
        tp: s,
        centerBias: p,
        bounds: { left: c, right: f, top: u, bottom: d },
      }),
      N = {
        stroke: g
          ? "hsl(var(--foreground) / 0.45)"
          : w
            ? "hsl(var(--foreground) / 0.9)"
            : "hsl(var(--foreground) / 0.55)",
        strokeWidth: w ? 2.2 : 2,
        fill: "none",
      },
      A = m === "x" ? y : 0,
      R = m === "y" ? y : 0,
      O = u ? Math.max(E + R, u + 8) : E + R,
      j = Math.min(Math.max(S + A, c ?? -1 / 0), f ?? 1 / 0);
    return C.jsxs(C.Fragment, {
      children: [
        !g &&
          h &&
          C.jsx(MV, {
            children: C.jsx("div", {
              className: "nodrag nopan absolute pointer-events-none",
              style: { transform: `translate(-50%, -50%) translate(${j}px, ${O}px)` },
              children: C.jsx("div", {
                className: "px-2 py-0.5 rounded-full text-xs bg-background border shadow-sm",
                children: h,
              }),
            }),
          }),
        C.jsx("path", {
          id: e,
          d: x,
          style: N,
          markerEnd: a,
          shapeRendering: "geometricPrecision",
        }),
      ],
    });
  },
  k5 = { rootNode: S5, stateNode: v5, compoundStateNode: w5, eventNode: x5, initialNode: E5 },
  T5 = { transitionEdge: b5 },
  _5 = {
    type: "transitionEdge",
    markerEnd: { type: xs.ArrowClosed, color: "hsl(var(--foreground))" },
  },
  N5 = { hideAttribution: !0 },
  P5 = [Ol, Ol],
  M5 = cn.Step,
  A5 = {
    nodeTypes: k5,
    edgeTypes: T5,
    defaultEdgeOptions: _5,
    proOptions: N5,
    snapGrid: P5,
    connectionLineType: M5,
  },
  R5 = ({ machine: e, activeStateIds: t, autoFitAfterDrag: n = !0, showMinimap: r = !0 }) => {
    const o = v.useRef(null),
      [i, s] = v.useState({ open: !1, x: 0, y: 0 }),
      {
        nodes: a,
        edges: l,
        onNodesChange: u,
        onEdgesChange: c,
        onNodeDragStop: f,
        relayout: d,
        tightenAndFitWhenReady: m,
        hasSavedPositions: y,
        onMoveEnd: g,
        initialViewport: w,
      } = g5({ machine: e, activeStateIds: t, autoFitAfterDrag: n }),
      h = v.useCallback((E) => {
        var k;
        E.preventDefault();
        const _ = (k = o.current) == null ? void 0 : k.getBoundingClientRect();
        s({
          open: !0,
          x: E.clientX - ((_ == null ? void 0 : _.left) ?? 0),
          y: E.clientY - ((_ == null ? void 0 : _.top) ?? 0),
        });
      }, []),
      p = v.useCallback(() => s((E) => ({ ...E, open: !1 })), []),
      x = () => d({ resetSavedPositions: !0 }).catch(console.error),
      S = () => m(l).catch(console.error);
    return C.jsxs("div", {
      ref: o,
      className: "relative h-full w-full",
      children: [
        C.jsxs(BE, {
          nodes: a,
          edges: l,
          onNodesChange: u,
          onEdgesChange: c,
          onNodeDragStop: f,
          onPaneContextMenu: h,
          onMoveEnd: g,
          ...A5,
          nodesDraggable: !0,
          nodesConnectable: !1,
          elementsSelectable: !0,
          defaultViewport: w ?? void 0,
          fitView: !y && !w,
          minZoom: 0.2,
          maxZoom: 1.5,
          snapToGrid: !0,
          className: "bg-background",
          children: [
            C.jsx(YV, {}),
            r &&
              C.jsx($V, {
                className: "rounded-md border shadow-sm",
                style: { backgroundColor: "hsl(var(--card))" },
                maskColor: "hsl(var(--background) / 0.6)",
                nodeColor: () => "hsl(var(--muted))",
                nodeStrokeColor: () => "hsl(var(--border))",
              }),
            C.jsx(e5, {}),
          ],
        }),
        i.open && C.jsx(y5, { x: i.x, y: i.y, onClose: p, onAutoLayout: x, onFitView: S }),
      ],
    });
  },
  D5 = (e) => C.jsx(dp, { children: C.jsx(R5, { ...e }) }),
  n0 = "inspector:lastSelectedMachineId",
  r0 = "inspector:sortOrder",
  I5 = (e) => (e ? new Date(e).toLocaleTimeString([], { hour12: !1 }) : ""),
  L5 = (e, t) => {
    const n = [...e];
    switch (t) {
      case "name-asc":
        return n.sort((r, o) => r.id.localeCompare(o.id));
      case "name-desc":
        return n.sort((r, o) => o.id.localeCompare(r.id));
      case "updated-asc":
        return n.sort((r, o) => r.updatedAt - o.updatedAt);
      case "updated-desc":
      default:
        return n.sort((r, o) => o.updatedAt - r.updatedAt);
    }
  };
function V5() {
  Nk();
  const e = is((p) => p.machines),
    t = is((p) => p.isConnected),
    [n, r] = v.useState(null),
    [o, i] = v.useState(() => localStorage.getItem(r0) ?? "updated-desc"),
    [s, a] = v.useState(!1),
    [l, u] = v.useState(!1),
    [c, f] = v.useState(() => {
      const p = localStorage.getItem("autoFitAfterDrag");
      return p ? p === "true" : !0;
    }),
    [d, m] = v.useState(() => {
      const p = localStorage.getItem("showMinimap");
      return p ? p === "true" : !0;
    });
  v.useEffect(() => {
    var E;
    if (Object.keys(e).length === 0) {
      r(null);
      return;
    }
    const x = localStorage.getItem(n0);
    if (x && e[x]) {
      r(x);
      return;
    }
    const S =
      (E = [...Object.values(e)].sort((_, k) => k.registeredAt - _.registeredAt)[0]) == null
        ? void 0
        : E.id;
    S && r(S);
  }, [e]),
    v.useEffect(() => {
      n && localStorage.setItem(n0, n);
    }, [n]),
    v.useEffect(() => {
      localStorage.setItem(r0, o);
    }, [o]),
    v.useEffect(() => {
      const p = localStorage.getItem("theme"),
        x = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches,
        S = p ? p === "dark" : x;
      document.documentElement.classList.toggle("dark", S), a(S);
    }, []);
  const y = () => {
      const p = !document.documentElement.classList.contains("dark");
      a(p),
        localStorage.setItem("theme", p ? "dark" : "light"),
        document.documentElement.classList.toggle("dark", p);
    },
    g = (p) => {
      f(p), localStorage.setItem("autoFitAfterDrag", p ? "true" : "false");
    },
    w = (p) => {
      m(p), localStorage.setItem("showMinimap", p ? "true" : "false");
    },
    h = n ? e[n] : null;
  return C.jsxs("div", {
    className: "flex h-screen w-full flex-col bg-background font-sans text-foreground",
    children: [
      C.jsx(O5, { onToggleTheme: y, isDark: s, isConnected: t, onOpenSettings: () => u(!0) }),
      C.jsxs("div", {
        className: "flex flex-1 overflow-hidden",
        children: [
          C.jsx(j5, {
            machines: e,
            selectedMachineId: n,
            onSelect: r,
            sortOrder: o,
            onChangeSort: i,
          }),
          C.jsx("main", {
            className: "flex-1 flex flex-col overflow-hidden",
            children: h
              ? C.jsx(F5, { machine: h, autoFitAfterDrag: c, showMinimap: d }, h.id)
              : C.jsx(U5, {}),
          }),
        ],
      }),
      C.jsx(H5, {
        open: l,
        onOpenChange: u,
        autoFitAfterDrag: c,
        onChangeAutoFit: g,
        showMinimap: d,
        onChangeShowMinimap: w,
      }),
    ],
  });
}
const O5 = ({ onToggleTheme: e, isDark: t, isConnected: n, onOpenSettings: r }) =>
    C.jsxs("header", {
      className: "flex h-14 items-center justify-between border-b bg-card px-4 lg:px-6",
      children: [
        C.jsxs("div", {
          className: "flex items-center gap-2 font-bold",
          children: [
            C.jsx(Rk, { className: "h-6 w-6 text-primary" }),
            C.jsx("span", { children: "XState Inspector" }),
          ],
        }),
        C.jsxs("div", {
          className: "flex items-center gap-3",
          children: [
            C.jsxs("div", {
              className:
                "flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium border " +
                (n
                  ? "border-green-600 text-green-700 dark:text-green-400"
                  : "border-amber-600 text-amber-700 dark:text-amber-400"),
              title: n ? "Connected" : "Disconnected",
              children: [
                n ? C.jsx(Yk, { className: "h-4 w-4" }) : C.jsx(Kk, { className: "h-4 w-4" }),
                C.jsx("span", { children: n ? "Online" : "Offline" }),
              ],
            }),
            C.jsx(yl, {
              variant: "ghost",
              size: "icon",
              onClick: r,
              "aria-label": "Settings",
              children: C.jsx(Uk, { className: "h-5 w-5" }),
            }),
            C.jsxs(yl, {
              variant: "ghost",
              size: "icon",
              onClick: e,
              "aria-label": "Toggle theme",
              children: [
                C.jsx(Gk, {
                  className:
                    "h-5 w-5 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0",
                }),
                C.jsx(jk, {
                  className:
                    "absolute h-5 w-5 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100",
                }),
                C.jsx("span", { className: "sr-only", children: "Toggle theme" }),
              ],
            }),
          ],
        }),
      ],
    }),
  j5 = ({ machines: e, selectedMachineId: t, onSelect: n, sortOrder: r, onChangeSort: o }) => {
    const [i, s] = v.useState(""),
      [a, l] = v.useState(!1),
      [u, c] = v.useState(!1),
      f = v.useRef(null);
    v.useEffect(() => {
      if (!a) return;
      const y = (w) => {
          f.current && !f.current.contains(w.target) && l(!1);
        },
        g = (w) => {
          w.key === "Escape" && l(!1);
        };
      return (
        document.addEventListener("mousedown", y),
        document.addEventListener("keydown", g),
        () => {
          document.removeEventListener("mousedown", y), document.removeEventListener("keydown", g);
        }
      );
    }, [a]);
    const d = v.useMemo(() => {
        const y = Object.values(e),
          g = i ? y.filter((w) => w.id.toLowerCase().includes(i.toLowerCase())) : y;
        return L5(g, r);
      }, [e, i, r]),
      m = () => {
        s(""), c(!1);
      };
    return C.jsxs("aside", {
      className: "hidden w-80 flex-col border-r bg-card p-4 sm:flex",
      children: [
        u
          ? C.jsxs("div", {
              className: "relative pb-2 border-b border-border/60",
              children: [
                C.jsx(Mm, {
                  className:
                    "pointer-events-none absolute left-2 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground",
                }),
                C.jsx(mh, {
                  id: "inspector-search-input",
                  value: i,
                  onChange: (y) => s(y.target.value),
                  onKeyDown: (y) => {
                    y.key === "Escape" && m();
                  },
                  placeholder: "Filter registered Machines",
                  className: "pl-8 pr-8",
                }),
                C.jsx("button", {
                  className:
                    "absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground",
                  onClick: m,
                  "aria-label": "Clear",
                  children: C.jsx(lh, { className: "h-4 w-4" }),
                }),
              ],
            })
          : C.jsxs("div", {
              className: "flex items-center justify-between pb-2 border-b border-border/60",
              children: [
                C.jsxs("button", {
                  className:
                    "flex items-center gap-2 rounded-md px-2 py-1 text-sm text-foreground/90 hover:bg-muted/60",
                  onClick: () => {
                    c(!0),
                      l(!1),
                      setTimeout(() => {
                        const y = document.getElementById("inspector-search-input");
                        y == null || y.focus();
                      }, 0);
                  },
                  "aria-label": "Open search",
                  children: [
                    C.jsx(Mm, { className: "h-4 w-4" }),
                    C.jsx("span", { className: "font-semibold", children: "Machines" }),
                  ],
                }),
                C.jsxs("div", {
                  className: "relative",
                  ref: f,
                  children: [
                    C.jsx(yl, {
                      variant: "ghost",
                      size: "icon",
                      onClick: () => l((y) => !y),
                      "aria-label": "Sort",
                      children: C.jsx(Ok, { className: "h-4 w-4" }),
                    }),
                    a &&
                      C.jsx("div", {
                        className:
                          "absolute right-0 z-10 mt-2 w-40 rounded-md border bg-popover p-1 shadow-md",
                        children: [
                          { id: "name-asc", label: "Name A—Z" },
                          { id: "name-desc", label: "Name Z—A" },
                          { id: "updated-desc", label: "Last updated" },
                          { id: "updated-asc", label: "First updated" },
                        ].map((y) =>
                          C.jsxs(
                            "button",
                            {
                              className:
                                "flex w-full items-center rounded px-2 py-1 text-sm hover:bg-muted/60",
                              onClick: () => {
                                o(y.id), l(!1);
                              },
                              children: [
                                C.jsx(Dk, {
                                  className:
                                    "mr-2 h-3.5 w-3.5 " +
                                    (r === y.id ? "opacity-100 text-primary" : "opacity-0"),
                                  "aria-hidden": "true",
                                }),
                                C.jsx("span", {
                                  className: r === y.id ? "text-primary" : void 0,
                                  children: y.label,
                                }),
                              ],
                            },
                            y.id,
                          ),
                        ),
                      }),
                  ],
                }),
              ],
            }),
        C.jsx("nav", {
          className: "mt-3 flex flex-col gap-2 overflow-y-auto",
          children: d.map((y) => {
            const g = t === y.id;
            return C.jsxs(
              "button",
              {
                className:
                  "group relative rounded-md border p-2 text-left transition-colors " +
                  (g ? "border-primary/70 bg-primary/5" : "border-border hover:bg-muted/40"),
                onClick: () => n(y.id),
                title: g ? "Currently shown on canvas" : "Show on canvas",
                children: [
                  C.jsxs("div", {
                    className: "flex items-center justify-between",
                    children: [
                      C.jsx("span", { className: "font-medium truncate", children: y.id }),
                      g &&
                        C.jsx("span", {
                          className:
                            "ml-2 rounded-full bg-primary/20 px-2 py-0.5 text-[10px] font-semibold text-primary",
                          children: "Active",
                        }),
                    ],
                  }),
                  C.jsxs("div", {
                    className: "mt-0.5 flex items-center gap-1.5 text-xs text-muted-foreground",
                    children: [
                      C.jsx(Ik, { className: "h-3.5 w-3.5" }),
                      C.jsx("span", { className: "opacity-80", children: "Reg:" }),
                      C.jsx("span", { className: "font-medium", children: I5(y.registeredAt) }),
                    ],
                  }),
                ],
              },
              y.id,
            );
          }),
        }),
      ],
    });
  },
  F5 = ({ machine: e, autoFitAfterDrag: t, showMinimap: n }) =>
    C.jsxs("div", {
      className: "grid h-full grid-cols-1 lg:grid-cols-3 gap-4 p-4",
      children: [
        C.jsxs("div", {
          className: "lg:col-span-2 flex flex-col gap-4 relative",
          children: [
            C.jsxs(_s, {
              className: "flex-1 flex flex-col",
              children: [
                C.jsxs(Ns, {
                  children: [
                    C.jsx(Ps, { children: e.id }),
                    C.jsxs("p", {
                      className: "text-sm text-muted-foreground",
                      children: [
                        "Current State:",
                        " ",
                        C.jsx("span", {
                          className: "font-mono text-primary",
                          children: e.currentStateIds.join(", "),
                        }),
                      ],
                    }),
                  ],
                }),
                C.jsx(Ms, {
                  className: "flex-1 relative",
                  children: C.jsx(D5, {
                    machine: e,
                    activeStateIds: e.currentStateIds,
                    autoFitAfterDrag: t,
                    showMinimap: n,
                  }),
                }),
              ],
            }),
            C.jsx($5, { machineId: e.id }),
          ],
        }),
        C.jsx("div", {
          className: "flex flex-col",
          children: C.jsx(z5, { machine: e, autoFitAfterDrag: t }),
        }),
      ],
    }),
  z5 = ({ machine: e }) =>
    C.jsxs(d_, {
      defaultValue: "events",
      className: "flex-1 flex flex-col overflow-hidden",
      children: [
        C.jsxs(ew, {
          className: "grid w-full grid-cols-3",
          children: [
            C.jsxs(Ia, {
              value: "events",
              children: [C.jsx(Vk, { className: "w-4 h-4 mr-2" }), "Event Log"],
            }),
            C.jsxs(Ia, {
              value: "context",
              children: [C.jsx(Wk, { className: "w-4 h-4 mr-2" }), "Context"],
            }),
            C.jsxs(Ia, {
              value: "json",
              children: [C.jsx(Lk, { className: "w-4 h-4 mr-2" }), "Definition"],
            }),
          ],
        }),
        C.jsx(La, {
          value: "events",
          className: "flex-1 overflow-y-auto mt-0",
          children: C.jsx("div", {
            className: "font-mono text-xs space-y-2 p-4",
            children: e.logs
              .slice()
              .reverse()
              .map((t, n) =>
                C.jsxs(
                  "div",
                  {
                    className: "p-2 rounded bg-muted",
                    children: [
                      C.jsx("p", { className: "font-bold text-primary", children: t.type }),
                      C.jsx("pre", {
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
        C.jsx(La, {
          value: "context",
          className: "flex-1 overflow-y-auto mt-0",
          children: C.jsx("pre", {
            className: "font-mono text-xs p-4",
            children: JSON.stringify(e.context, null, 2),
          }),
        }),
        C.jsx(La, {
          value: "json",
          className: "flex-1 overflow-y-auto mt-0",
          children: C.jsx("pre", {
            className: "font-mono text-xs p-4",
            children: JSON.stringify(e.definition, null, 2),
          }),
        }),
      ],
    }),
  $5 = ({ machineId: e }) => {
    const [t, n] = v.useState(!1),
      r = is((o) => o.sendCommand);
    return C.jsxs(C.Fragment, {
      children: [
        C.jsx("div", {
          className: "absolute bottom-4 left-1/2 -translate-x-1/2",
          children: C.jsxs(SS, {
            children: [
              C.jsx($a, {
                onClick: () => r("resume", { machine_id: e }),
                children: C.jsx($k, { className: "h-4 w-4" }),
              }),
              C.jsx($a, {
                onClick: () => r("pause", { machine_id: e }),
                children: C.jsx(zk, { className: "h-4 w-4" }),
              }),
              C.jsx($a, { onClick: () => n(!0), children: C.jsx(Hk, { className: "h-4 w-4" }) }),
            ],
          }),
        }),
        C.jsx(B5, { open: t, onOpenChange: n, machineId: e }),
      ],
    });
  },
  B5 = ({ open: e, onOpenChange: t, machineId: n }) => {
    const [r, o] = v.useState(""),
      [i, s] = v.useState(""),
      a = is((u) => u.sendCommand),
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
    return C.jsx(TN, {
      open: e,
      onOpenChange: t,
      children: C.jsxs(Lw, {
        children: [
          C.jsx(Vw, { children: C.jsxs(jw, { children: ["Send Event to ", n] }) }),
          C.jsxs("div", {
            className: "grid gap-4 py-4",
            children: [
              C.jsx(mh, {
                placeholder: "Event Type (e.g., ENABLE)",
                value: r,
                onChange: (u) => o(u.target.value),
              }),
              C.jsx(Fw, {
                placeholder: 'Payload (JSON), e.g., {"value": 42}',
                value: i,
                onChange: (u) => s(u.target.value),
              }),
            ],
          }),
          C.jsx(Ow, {
            children: C.jsx(ES, {
              className: "w-full",
              onClick: l,
              children: C.jsx("span", {
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
  H5 = ({
    open: e,
    onOpenChange: t,
    autoFitAfterDrag: n,
    onChangeAutoFit: r,
    showMinimap: o,
    onChangeShowMinimap: i,
  }) =>
    C.jsx(PN, {
      open: e,
      onOpenChange: t,
      children: C.jsxs($w, {
        children: [
          C.jsx(Bw, { children: C.jsx(Hw, { children: "Settings" }) }),
          C.jsxs("div", {
            className: "space-y-3",
            children: [
              C.jsxs("div", {
                className: "flex items-center gap-2 text-sm font-semibold",
                children: [
                  C.jsx(Fk, { className: "h-4 w-4 text-primary" }),
                  C.jsx("span", { children: "Layout & Canvas" }),
                ],
              }),
              C.jsxs("div", {
                className: "rounded-md border p-3 bg-card/50 space-y-3",
                children: [
                  C.jsxs("label", {
                    className: "flex items-center gap-3 text-sm",
                    children: [
                      C.jsx("input", {
                        type: "checkbox",
                        className: "h-4 w-4",
                        checked: n,
                        onChange: (s) => r(s.target.checked),
                      }),
                      C.jsxs("div", {
                        className: "flex flex-col",
                        children: [
                          C.jsx("span", {
                            className: "font-medium",
                            children: "Auto-fit view after drag",
                          }),
                          C.jsx("span", {
                            className: "text-xs text-muted-foreground",
                            children:
                              "After moving nodes, automatically fit the diagram to the current content.",
                          }),
                        ],
                      }),
                    ],
                  }),
                  C.jsxs("label", {
                    className: "flex items-center gap-3 text-sm",
                    children: [
                      C.jsx("input", {
                        type: "checkbox",
                        className: "h-4 w-4",
                        checked: o,
                        onChange: (s) => i(s.target.checked),
                      }),
                      C.jsxs("div", {
                        className: "flex flex-col",
                        children: [
                          C.jsx("span", { className: "font-medium", children: "Show Minimap" }),
                          C.jsx("span", {
                            className: "text-xs text-muted-foreground",
                            children: "Toggle the React Flow minimap on the canvas.",
                          }),
                        ],
                      }),
                    ],
                  }),
                ],
              }),
            ],
          }),
        ],
      }),
    }),
  U5 = () =>
    C.jsx("div", {
      className: "flex h-full items-center justify-center m-4",
      children: C.jsxs(_s, {
        className: "w-full max-w-md",
        children: [
          C.jsx(Ns, {
            children: C.jsx(Ps, { className: "text-2xl", children: "No Live Machines Detected" }),
          }),
          C.jsx(Ms, {
            children: C.jsx("p", {
              className: "text-muted-foreground",
              children: "Run a Python script with the InspectorPlugin to begin debugging.",
            }),
          }),
        ],
      }),
    });
Lc.createRoot(document.getElementById("root")).render(
  C.jsx(L.StrictMode, { children: C.jsx(V5, {}) }),
);
