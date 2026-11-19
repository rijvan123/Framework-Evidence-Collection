"""The 17-detector zoo of the evaluation (paper Table 'zoo').

Every detector returns a real-valued score (a margin, log-odds or a probability) where larger means
more malicious; the decision is ``score > theta``. ``default_threshold`` is the score of p = 0.5."""
from __future__ import annotations

import io
import pickle
import time

import lightgbm as lgb
import numpy as np
from sklearn.ensemble import ExtraTreesClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import GaussianNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC, LinearSVC

from ..features.preprocess import IGSelector, MRMRSelector, SignedLog1p, chi2_steps, pca
from . import lgbm as L

DISPLAY = {
    'lgbm_trace': 'LGBM-TRACE (f₀ family)', 'lgbm_ember': 'LGBM-EMBER', 'xgboost': 'XGBoost', 'rf': 'Random forest',
    'et': 'Extra trees', 'lr': 'LR', 'lr_chi2': 'LR + χ²(256)', 'lr_ig': 'LR + IG(256)', 'lr_mrmr': 'LR + mRMR(128)',
    'lr_pca': 'LR + PCA(0.95)', 'linsvm': 'Linear SVM', 'rbfsvm': 'RBF-SVM (PoC, 10k)', 'knn': 'k-NN (PCA-50)',
    'gnb': 'Gaussian NB', 'mlp': 'MLP (PoC, 20k)', 'stack': 'Temporal stacking',
    'ember2018_pub': 'EMBER-2018 GBDT (published model)'}
TREE = {'lgbm_trace', 'lgbm_ember', 'xgboost', 'rf', 'et', 'stack', 'ember2018_pub'}
PROBA_SCORE = {'rf', 'et', 'knn'}           # scores are probabilities: default threshold 0.5


def seeds_for(key: str, cfg: dict) -> list[int]:
    s = cfg['seeds']
    m = cfg['models']
    if key in m.get('multi_seed', []):
        return list(s['models'])
    if key in m.get('slow_seed', []):
        return list(s['slow_models'])
    return [int(s['f0'])]


class Model:
    def __init__(self, key, seed, obj, kind, extra=None):
        self.key, self.seed, self.obj, self.kind = key, seed, obj, kind
        self.extra = extra or {}
        self.default_threshold = 0.5 if key in PROBA_SCORE else 0.0
        self.fit_seconds = None

    # ---------------------------------------------------------------- scoring
    def score(self, X, chunk: int = 20000) -> np.ndarray:
        n = X.shape[0]
        out = np.empty(n, np.float64)
        for s in range(0, n, chunk):
            out[s:s + chunk] = self._score(np.asarray(X[s:s + chunk], dtype=np.float32))
        return out

    def _score(self, X):
        k = self.kind
        if k == 'lgbm':
            return self.obj.predict(X, raw_score=True)
        if k == 'xgb':
            import xgboost as xgb
            return self.obj.get_booster().predict(xgb.DMatrix(X), output_margin=True).astype(np.float64)
        if k == 'proba':
            return self.obj.predict_proba(X)[:, 1]
        if k == 'decision':
            return np.asarray(self.obj.decision_function(X), dtype=np.float64)
        if k == 'nb':
            lp = self.obj.predict_log_proba(X)
            return lp[:, 1] - lp[:, 0]
        if k == 'mlp':
            return mlp_logit(self.obj, X)
        if k == 'stack':
            return self.obj.decision_function(X)
        raise ValueError(k)

    # ---------------------------------------------------------------- persistence / identity
    def to_bytes(self) -> bytes:
        if self.kind == 'lgbm':
            return self.obj.model_to_string(num_iteration=-1).encode()
        buf = io.BytesIO()
        pickle.dump(self.obj, buf, protocol=4)
        return buf.getvalue()

    def identity(self) -> dict:
        if self.kind == 'lgbm':
            return L.identity(self.obj)
        import hashlib
        b = self.to_bytes()
        return dict(file_sha256=hashlib.sha256(b).hexdigest(), model_bytes=len(b))


def mlp_logit(pipe: Pipeline, X) -> np.ndarray:
    """Output-unit logit in float64 (deviation D17: the logit of float32 predict_proba saturates)."""
    Z = X
    for name, step in pipe.steps[:-1]:
        Z = step.transform(Z)
    mlp = pipe.steps[-1][1]
    H = np.asarray(Z, dtype=np.float64)
    for i, (W, b) in enumerate(zip(mlp.coefs_, mlp.intercepts_)):
        H = H @ W.astype(np.float64) + b.astype(np.float64)
        if i < len(mlp.coefs_) - 1:
            H = np.maximum(H, 0) if mlp.activation == 'relu' else np.tanh(H)
    return H.ravel()


def _stratified_subsample(y, n, seed):
    if n >= len(y):
        return np.arange(len(y))
    rng = np.random.default_rng(seed)
    idx = []
    for c in np.unique(y):
        ci = np.flatnonzero(y == c)
        k = int(round(n * len(ci) / len(y)))
        idx.append(rng.choice(ci, size=min(k, len(ci)), replace=False))
    return np.sort(np.concatenate(idx))


def _lr(cfg_m, seed):
    return LogisticRegression(C=cfg_m['lr']['C'], max_iter=cfg_m['lr']['max_iter'], class_weight='balanced',
                              random_state=seed)


class TemporalStack:
    """Temporally ordered stacking (Eq. (51)): meta-features of block j come from base learners trained on
    blocks < j only; the meta-learner is a logistic regression; base learners are refitted on all blocks."""

    def __init__(self, cfg, seed, threads):
        self.cfg, self.seed, self.threads = cfg, seed, threads

    def _bases(self):
        m = self.cfg['models']
        st = m['stack']
        out = []
        for b in st['base']:
            if b == 'lgbm_trace':
                out.append(('lgbm', None))
            elif b == 'et':
                out.append(('et', ExtraTreesClassifier(n_estimators=st.get('et_trees', 100), max_features='sqrt',
                                                        n_jobs=self.threads, random_state=self.seed)))
            elif b == 'lr':
                out.append(('lr', Pipeline([('log', SignedLog1p()), ('sc', StandardScaler()), ('clf', _lr(m, self.seed))])))
        return out

    def _fit_bases(self, X, y):
        fitted = []
        for name, est in self._bases():
            if name == 'lgbm':
                fitted.append(('lgbm', L.train_lgbm(X, y, self.cfg['models']['lgbm_trace'], self.seed, self.threads)))
            else:
                fitted.append((name, est.fit(X, y)))
        return fitted

    @staticmethod
    def _meta(fitted, X):
        cols = []
        for name, est in fitted:
            if name == 'lgbm':
                cols.append(est.predict(X, raw_score=True))
            elif name == 'et':
                p = np.clip(est.predict_proba(X)[:, 1], 1e-4, 1 - 1e-4)
                cols.append(np.log(p / (1 - p)))
            else:
                cols.append(est.decision_function(X))
        return np.column_stack(cols)

    def fit(self, X, y, t):
        nb = int(self.cfg['models']['stack'].get('blocks', 3))
        order = np.argsort(t, kind='stable')
        blocks = np.array_split(order, nb)
        Zs, ys = [], []
        for j in range(1, nb):
            prev = np.sort(np.concatenate(blocks[:j]))
            cur = np.sort(blocks[j])
            f = self._fit_bases(X[prev], y[prev])
            Zs.append(self._meta(f, X[cur]))
            ys.append(y[cur])
        Z = np.vstack(Zs)
        self.scaler = StandardScaler().fit(Z)
        self.meta = LogisticRegression(C=1.0, max_iter=1000).fit(self.scaler.transform(Z), np.concatenate(ys))
        self.bases = self._fit_bases(X, y)
        return self

    def decision_function(self, X):
        return self.meta.decision_function(self.scaler.transform(self._meta(self.bases, X)))


def fit_model(key: str, seed: int, Xtr, ytr, cfg: dict, t_train=None, threads: int = 2) -> Model:
    """Fit one detector of the zoo on the training window (all preprocessing inside the window)."""
    m = cfg['models']
    sel = m['select']
    t0 = time.perf_counter()
    Xtr = np.asarray(Xtr, dtype=np.float32)
    ytr = np.asarray(ytr).astype(np.int64)
    if key == 'lgbm_trace':
        mdl = Model(key, seed, L.train_lgbm(Xtr, ytr, m['lgbm_trace'], seed, threads), 'lgbm')
    elif key == 'lgbm_ember':
        mdl = Model(key, seed, L.train_lgbm(Xtr, ytr, m['lgbm_ember'], seed, threads), 'lgbm')
    elif key == 'xgboost':
        import xgboost as xgb
        p = m['xgboost']
        est = xgb.XGBClassifier(n_estimators=p['n_estimators'], max_depth=p['max_depth'], learning_rate=p['learning_rate'],
                                subsample=p['subsample'], colsample_bytree=p['colsample_bytree'], tree_method='hist',
                                n_jobs=threads, random_state=seed, verbosity=0)
        mdl = Model(key, seed, est.fit(Xtr, ytr), 'xgb')
    elif key in ('rf', 'et'):
        p = m[key]
        cls = RandomForestClassifier if key == 'rf' else ExtraTreesClassifier
        est = cls(n_estimators=p['n_estimators'], max_features=p.get('max_features', 'sqrt'), n_jobs=threads,
                  random_state=seed)
        mdl = Model(key, seed, est.fit(Xtr, ytr), 'proba')
    elif key.startswith('lr'):
        steps = [('log', SignedLog1p())]
        if key == 'lr_chi2':
            steps += chi2_steps(sel['chi2_k'])
            steps += [('sc', StandardScaler())]
        else:
            steps += [('sc', StandardScaler())]
            if key == 'lr_ig':
                steps += [('sel', IGSelector(sel['ig_k'], sel['ig_bins']))]
            elif key == 'lr_mrmr':
                steps += [('sel', MRMRSelector(sel['mrmr_k'], sel['ig_bins']))]
            elif key == 'lr_pca':
                steps += [('pca', pca(sel['pca_var'], seed))]
        steps += [('clf', _lr(m, seed))]
        mdl = Model(key, seed, Pipeline(steps).fit(Xtr, ytr), 'decision')
    elif key == 'linsvm':
        p = m['linsvm']
        est = Pipeline([('log', SignedLog1p()), ('sc', StandardScaler()),
                        ('clf', LinearSVC(C=p['C'], max_iter=p['max_iter'], class_weight='balanced', random_state=seed))])
        mdl = Model(key, seed, est.fit(Xtr, ytr), 'decision')
    elif key == 'rbfsvm':
        p = m['rbfsvm']
        sub = _stratified_subsample(ytr, p['n_train'], seed)
        est = Pipeline([('log', SignedLog1p()), ('sc', StandardScaler()),
                        ('clf', SVC(C=p['C'], gamma=p['gamma'], kernel='rbf', cache_size=1000, random_state=seed))])
        mdl = Model(key, seed, est.fit(Xtr[sub], ytr[sub]), 'decision', extra=dict(n_train=int(len(sub))))
    elif key == 'knn':
        p = m['knn']
        est = Pipeline([('log', SignedLog1p()), ('sc', StandardScaler()), ('pca', pca(p['pca'], seed)),
                        ('clf', KNeighborsClassifier(n_neighbors=p['k'], n_jobs=threads))])
        mdl = Model(key, seed, est.fit(Xtr, ytr), 'proba')
    elif key == 'gnb':
        mdl = Model(key, seed, GaussianNB().fit(Xtr, ytr), 'nb')
    elif key == 'mlp':
        p = m['mlp']
        sub = _stratified_subsample(ytr, p['n_train'], seed)
        est = Pipeline([('log', SignedLog1p()), ('sc', StandardScaler()),
                        ('clf', MLPClassifier(hidden_layer_sizes=tuple(p['hidden']), alpha=p['alpha'], max_iter=p['max_iter'],
                                              early_stopping=True, random_state=seed))])
        mdl = Model(key, seed, est.fit(Xtr[sub], ytr[sub]), 'mlp', extra=dict(n_train=int(len(sub))))
    elif key == 'stack':
        if t_train is None:
            raise ValueError('temporal stacking needs the first-seen days of the training rows')
        mdl = Model(key, seed, TemporalStack(cfg, seed, threads).fit(Xtr, ytr, np.asarray(t_train)), 'stack')
    else:
        raise KeyError(key)
    mdl.fit_seconds = round(time.perf_counter() - t0, 3)
    return mdl


def load_published(path) -> Model | None:
    """The published EMBER-2018 LightGBM model (scored only, never retrained)."""
    from pathlib import Path
    p = Path(path)
    if not p.exists():
        return None
    mdl = Model('ember2018_pub', 0, lgb.Booster(model_file=str(p)), 'lgbm')
    mdl.fit_seconds = 0.0
    return mdl


def model_from_bytes(key: str, seed: int, data: bytes) -> Model:
    if key in ('lgbm_trace', 'lgbm_ember', 'ember2018_pub'):
        return Model(key, seed, lgb.Booster(model_str=data.decode()), 'lgbm')
    obj = pickle.loads(data)
    kind = {'xgboost': 'xgb', 'rf': 'proba', 'et': 'proba', 'knn': 'proba', 'gnb': 'nb', 'mlp': 'mlp',
            'stack': 'stack'}.get(key, 'decision')
    return Model(key, seed, obj, kind)
