#!/usr/bin/env python3
"""Model zoo for S10 (E1 detection layer). All preprocessing is fitted on training rows only (S8 Eq. 8).
Score conventions: larger = more malicious. Thresholds/calibration are fitted later on December 2019 only."""
import numpy as np, time
import lightgbm as lgb
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.feature_selection import SelectKBest, chi2
from sklearn.decomposition import PCA
from sklearn.linear_model import LogisticRegression
from sklearn.svm import LinearSVC, SVC
from sklearn.neighbors import KNeighborsClassifier
from sklearn.naive_bayes import GaussianNB
from sklearn.ensemble import RandomForestClassifier, ExtraTreesClassifier
from sklearn.neural_network import MLPClassifier
import s10_common as C


def slog(X):
    return C.signed_log1p(X)


def fit_lgbm(Xtr, ytr, params, rounds, seed, weight=None, init_model=None):
    p = dict(params); p['seed'] = seed
    ds = lgb.Dataset(np.asarray(Xtr, dtype=np.float32), label=ytr, weight=weight,
                     params={'verbose': -1, 'max_bin': 255}, free_raw_data=True)
    return lgb.train(p, ds, num_boost_round=rounds, init_model=init_model)


# ---------------------------------------------------------------- binned information gain / mRMR (S8 Eqs. 40, 42, 44)
def quantile_bins(X, nb=10):
    qs = np.linspace(0, 1, nb + 1)[1:-1]
    edges = []
    for j in range(X.shape[1]):
        edges.append(np.unique(np.quantile(X[:, j], qs)))
    return edges


def apply_bins(X, edges):
    B = np.empty(X.shape, dtype=np.uint8)
    for j, e in enumerate(edges):
        B[:, j] = np.searchsorted(e, X[:, j], side='right')
    return B


def _H(p):
    p = p[p > 0]
    return float(-(p * np.log2(p)).sum())


def info_gain(B, y, nb=10):
    n, d = B.shape; Hy = _H(np.bincount(y, minlength=2) / n); out = np.zeros(d)
    for j in range(d):
        c = np.bincount(B[:, j].astype(np.int64) * 2 + y, minlength=2 * nb).reshape(-1, 2)
        tot = c.sum(1); w = tot / n; hc = 0.0
        for b in np.nonzero(tot)[0]:
            hc += w[b] * _H(c[b] / tot[b])
        out[j] = Hy - hc
    return out


def mutual_info_all(B, col, nb=10):
    """I(x_j; x_col) for all j on binned data, vectorised with offset codes (log2)."""
    n, d = B.shape; K = nb * nb
    codes = B.astype(np.int32) * nb + B[:, col].astype(np.int32)[:, None] + (np.arange(d, dtype=np.int32) * K)[None, :]
    joint = np.bincount(codes.ravel(), minlength=d * K).reshape(d, nb, nb) / n
    px = joint.sum(2); py = joint.sum(1)
    with np.errstate(divide='ignore', invalid='ignore'):
        r = joint / (px[:, :, None] * py[:, None, :])
        t = np.where(joint > 0, joint * np.log2(r), 0.0)
    return t.sum(axis=(1, 2))


class IGSelect:
    def __init__(self, k=256):
        self.k = k

    def fit(self, X, y):
        self.edges = quantile_bins(X); B = apply_bins(X, self.edges)
        self.ig = info_gain(B, y); self.sel = np.argsort(-self.ig)[:self.k]; return self

    def transform(self, X):
        return X[:, self.sel]


class MRMR:
    """Greedy mRMR (MID form, Peng et al. 2005; S8 Eq. 44) on 10-bin train-quantile discretisation."""
    def __init__(self, k=128):
        self.k = k

    def fit(self, X, y):
        edges = quantile_bins(X); B = apply_bins(X, edges); self.B_edges = edges
        rel = info_gain(B, y); d = X.shape[1]
        sel = [int(np.argmax(rel))]; red = np.zeros(d); chosen = np.zeros(d, bool); chosen[sel[0]] = True
        for _ in range(1, self.k):
            red += mutual_info_all(B, sel[-1])
            score = rel - red / len(sel); score[chosen] = -np.inf
            j = int(np.argmax(score)); sel.append(j); chosen[j] = True
        self.sel = np.array(sel); self.rel = rel; return self

    def transform(self, X):
        return X[:, self.sel]


# ---------------------------------------------------------------- model wrappers
class Model:
    deterministic = True
    def fit(self, X, y, seed): ...
    def score(self, X): ...


class LGBM(Model):
    deterministic = False
    def __init__(self, params, rounds):
        self.params = params; self.rounds = rounds

    def fit(self, X, y, seed):
        self.b = fit_lgbm(X, y, self.params, self.rounds, seed); return self

    def score(self, X):
        return self.b.predict(np.asarray(X, np.float32), raw_score=True)

    def ident(self):
        return C.tree_section_hash(self.b.model_to_string())


class XGB(Model):
    deterministic = False
    def fit(self, X, y, seed):
        import xgboost as xgb
        self.m = xgb.XGBClassifier(n_estimators=400, max_depth=8, learning_rate=0.1, subsample=0.8,
                                   colsample_bytree=0.5, tree_method='hist', n_jobs=2, random_state=seed,
                                   eval_metric='logloss')
        self.m.fit(np.asarray(X, np.float32), y); return self

    def score(self, X):
        return self.m.predict(np.asarray(X, np.float32), output_margin=True)


class Forest(Model):
    deterministic = False
    def __init__(self, kind, n=300):
        self.kind = kind; self.n = n

    def fit(self, X, y, seed):
        cls = RandomForestClassifier if self.kind == 'rf' else ExtraTreesClassifier
        self.m = cls(n_estimators=self.n, max_features='sqrt', n_jobs=2, random_state=seed)
        self.m.fit(np.asarray(X, np.float32), y); return self

    def score(self, X):
        return self.m.predict_proba(np.asarray(X, np.float32))[:, 1]


class Linear(Model):
    """signed log1p -> [selector] -> StandardScaler -> LR or linear SVM. Selector fitted on train only."""
    def __init__(self, sel=None, clf='lr', k=None):
        self.sel = sel; self.clf = clf; self.k = k

    def fit(self, X, y, seed):
        Z = slog(X)
        if self.sel == 'chi2':
            self.mm = MinMaxScaler().fit(Z); Zm = np.clip(self.mm.transform(Z), 0, None)
            self.s = SelectKBest(chi2, k=self.k).fit(Zm, y); Z = Z[:, self.s.get_support()]
        elif self.sel == 'ig':
            self.s = IGSelect(self.k).fit(Z, y); Z = self.s.transform(Z)
        elif self.sel == 'mrmr':
            self.s = MRMR(self.k).fit(Z, y); Z = self.s.transform(Z)
        self.sc = StandardScaler().fit(Z); Z = self.sc.transform(Z)
        if self.sel == 'pca':
            self.p = PCA(n_components=0.95, svd_solver='full', random_state=0).fit(Z); Z = self.p.transform(Z)
        if self.clf == 'lr':
            self.m = LogisticRegression(C=1.0, max_iter=3000, class_weight='balanced')
        else:
            self.m = LinearSVC(C=0.05, class_weight='balanced', dual=False, max_iter=5000)
        self.m.fit(Z, y); return self

    def _tx(self, X):
        Z = slog(X)
        if self.sel == 'chi2':
            Z = Z[:, self.s.get_support()]
        elif self.sel in ('ig', 'mrmr'):
            Z = self.s.transform(Z)
        Z = self.sc.transform(Z)
        if self.sel == 'pca':
            Z = self.p.transform(Z)
        return Z

    def score(self, X):
        return self.m.decision_function(self._tx(X))


class KNN(Model):
    def fit(self, X, y, seed):
        Z = slog(X); self.sc = StandardScaler().fit(Z); Z = self.sc.transform(Z)
        self.p = PCA(n_components=50, random_state=0).fit(Z)
        self.m = KNeighborsClassifier(n_neighbors=15, weights='distance', n_jobs=2).fit(self.p.transform(Z), y); return self

    def score(self, X):
        return self.m.predict_proba(self.p.transform(self.sc.transform(slog(X))))[:, 1]


class NB(Model):
    def fit(self, X, y, seed):
        Z = slog(X); self.sc = StandardScaler().fit(Z)
        self.m = GaussianNB().fit(self.sc.transform(Z), y); return self

    def score(self, X):
        jl = self.m.predict_joint_log_proba(self.sc.transform(slog(X)))
        return jl[:, 1] - jl[:, 0]


class SVMRBF(Model):
    """Proof of concept on a stratified sub-sample n_s = 10,000 (S8 Eq. 39)."""
    def __init__(self, ns=10000):
        self.ns = ns

    def fit(self, X, y, seed):
        rng = np.random.default_rng(seed); idx = []
        for c in (0, 1):
            ic = np.where(y == c)[0]; idx.append(rng.choice(ic, int(round(self.ns * len(ic) / len(y))), replace=False))
        idx = np.sort(np.concatenate(idx))
        Z = slog(np.asarray(X)[idx]); self.sc = StandardScaler().fit(Z)
        self.m = SVC(C=1.0, kernel='rbf', gamma='scale', class_weight='balanced', cache_size=2000)
        self.m.fit(self.sc.transform(Z), y[idx]); self.n_sv = int(self.m.n_support_.sum()); return self

    def score(self, X):
        out = []
        for s in range(0, len(X), 5000):
            out.append(self.m.decision_function(self.sc.transform(slog(np.asarray(X[s:s + 5000])))))
        return np.concatenate(out)


class MLP(Model):
    """Shallow MLP proof of concept on a 20,000-row stratified sub-sample."""
    deterministic = False
    def fit(self, X, y, seed):
        rng = np.random.default_rng(seed); idx = []
        for c in (0, 1):
            ic = np.where(y == c)[0]; idx.append(rng.choice(ic, int(round(20000 * len(ic) / len(y))), replace=False))
        idx = np.sort(np.concatenate(idx))
        Z = slog(np.asarray(X)[idx]); self.sc = StandardScaler().fit(Z)
        self.m = MLPClassifier(hidden_layer_sizes=(256,), alpha=1e-4, batch_size=256, learning_rate_init=1e-3,
                               max_iter=40, random_state=seed)
        self.m.fit(self.sc.transform(Z), y[idx]); return self

    def score(self, X):
        # logit = pre-activation of the output unit, computed in float64 (predict_proba is float32 and saturates at 1.0,
        # which made 20-27% of the first S10 scores +inf; fixed before any MLP metric was reported)
        a = self.sc.transform(slog(X)).astype(np.float64)
        for W, b in zip(self.m.coefs_[:-1], self.m.intercepts_[:-1]):
            a = np.maximum(a @ W.astype(np.float64) + b.astype(np.float64), 0.0)        # ReLU hidden layer(s)
        return (a @ self.m.coefs_[-1].astype(np.float64) + self.m.intercepts_[-1].astype(np.float64)).ravel()


class TemporalStack(Model):
    """S8 Eq. 51: chronological blocks B1 = Aug29-Sep30, B2 = Oct, B3 = Nov. Meta-features of block j come from
    base learners trained on blocks < j only; meta-learner = LR on (B2 u B3). Base learners refit on all blocks."""
    deterministic = False
    def __init__(self, block):
        self.block = block   # array of block ids (1,2,3) aligned with training rows

    def _bases(self, X, y, seed):
        return [LGBM(C.LGB_TRACE, C.LGB_TRACE_ROUNDS).fit(X, y, seed), Linear(None, 'lr').fit(X, y, seed),
                Forest('et', 150).fit(X, y, seed)]

    @staticmethod
    def _feat(bases, X):
        f = [bases[0].score(X), bases[1].score(X)]
        p = np.clip(bases[2].score(X), 1e-4, 1 - 1e-4); f.append(np.log(p / (1 - p)))
        return np.column_stack(f)

    def fit(self, X, y, seed):
        X = np.asarray(X); mf = []; my = []
        for j in (2, 3):
            tr = self.block < j; te = self.block == j
            b = self._bases(X[tr], y[tr], seed); mf.append(self._feat(b, X[te])); my.append(y[te])
        self.meta = LogisticRegression(C=1.0, max_iter=1000).fit(np.vstack(mf), np.concatenate(my))
        self.bases = self._bases(X, y, seed); return self

    def score(self, X):
        return self.meta.decision_function(self._feat(self.bases, X))


def make(name, block=None):
    return {
        'lgbm_trace': lambda: LGBM(C.LGB_TRACE, C.LGB_TRACE_ROUNDS),
        'lgbm_ember': lambda: LGBM(C.LGB_EMBER, C.LGB_EMBER_ROUNDS),
        'xgb': lambda: XGB(),
        'rf': lambda: Forest('rf'),
        'et': lambda: Forest('et'),
        'lr': lambda: Linear(None, 'lr'),
        'lr_chi2': lambda: Linear('chi2', 'lr', 256),
        'lr_ig': lambda: Linear('ig', 'lr', 256),
        'lr_mrmr': lambda: Linear('mrmr', 'lr', 128),
        'lr_pca': lambda: Linear('pca', 'lr'),
        'svm_lin': lambda: Linear(None, 'svm'),
        'svm_rbf': lambda: SVMRBF(),
        'knn': lambda: KNN(),
        'nb': lambda: NB(),
        'mlp': lambda: MLP(),
        'stack': lambda: TemporalStack(block),
    }[name]()
