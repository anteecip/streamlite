# ✅ Imports
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge, Lasso
from sklearn.svm import SVR
from sklearn.neighbors import KNeighborsRegressor
from sklearn.decomposition import PCA
from sklearn.feature_selection import SelectKBest, f_regression
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error

from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.model_selection import RepeatedKFold
import numpy as np



# 1️⃣ Pipelines SANS réduction
def build_basic_pipelines():
    pipelines = {}

    pipelines["Ridge"] = Pipeline([
        ("scaler", StandardScaler()),
        ("model", Ridge(alpha=1.0))
    ])

    pipelines["Lasso"] = Pipeline([
        ("scaler", StandardScaler()),
        ("model", Lasso(alpha=0.01, max_iter=10000))
    ])

    pipelines["RandomForest"] = Pipeline([
        ("scaler", StandardScaler()),
        ("model", RandomForestRegressor(random_state=42))
    ])

    pipelines["SVR"] = Pipeline([
        ("scaler", StandardScaler()),
        ("model", SVR(kernel="rbf", C=1.0, epsilon=0.1))
    ])

    pipelines["KNN"] = Pipeline([
        ("scaler", StandardScaler()),
        ("model", KNeighborsRegressor(
            n_neighbors=5,
            weights="distance"
        ))
    ])

    return pipelines

# 2️⃣ Pipelines AVEC PCA
def build_pca_pipelines(n_components=15):
    pipelines = {}

    pipelines["Ridge_PCA"] = Pipeline([
        ("scaler", StandardScaler()),
        ("pca", PCA(n_components=n_components)),
        ("model", Ridge(alpha=1.0))
    ])

    pipelines["SVR_PCA"] = Pipeline([
        ("scaler", StandardScaler()),
        ("pca", PCA(n_components=n_components)),
        ("model", SVR(kernel="rbf", C=1.0, epsilon=0.1))
    ])

    pipelines["KNN_PCA"] = Pipeline([
        ("scaler", StandardScaler()),
        ("pca", PCA(n_components=n_components)),
        ("model", KNeighborsRegressor(
            n_neighbors=5,
            weights="distance"
        ))
    ])

    return pipelines

# 3️⃣ Pipelines avec SelectKBest (souvent meilleur que PCA)
def build_selectkbest_pipelines(k=15):
    pipelines = {}

    pipelines["Ridge_SelectK"] = Pipeline([
        ("scaler", StandardScaler()),
        ("select", SelectKBest(score_func=f_regression, k=k)),
        ("model", Ridge(alpha=1.0))
    ])

    pipelines["SVR_SelectK"] = Pipeline([
        ("scaler", StandardScaler()),
        ("select", SelectKBest(score_func=f_regression, k=k)),
        ("model", SVR(kernel="rbf", C=1.0, epsilon=0.1))
    ])

    pipelines["KNN_SelectK"] = Pipeline([
        ("scaler", StandardScaler()),
        ("select", SelectKBest(score_func=f_regression, k=k)),
        ("model", KNeighborsRegressor(
            n_neighbors=5,
            weights="distance"
        ))
    ])

    return pipelines

# 4️⃣ Fonction pour tout construire
def build_all_pipelines():
    pipelines = {}

    pipelines.update(build_basic_pipelines())
    pipelines.update(build_pca_pipelines(n_components=15))
    pipelines.update(build_selectkbest_pipelines(k=15))

    return pipelines


# Utilisation avec cross-validation


# Pour chaque modèle :

# ✅ MAE moyen en CV (robuste)

# ✅ Variabilité (std)

# ✅ R² sur test réel

# 🔒 Zéro data leakage

# Avec 50–100 samples :

# Le R² test peut beaucoup varier

# Le MAE CV est souvent plus stable

# Donc pour choisir le modèle :

# 👉 Priorité au CV_MAE_mean
# 👉 Test_R2 pour validation finale

def benchmark_models(X, y):

    # 1️⃣ Split train / test
    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=0.2,
        random_state=42
    )

    pipelines = build_all_pipelines()

    results = {}

    for name, pipe in pipelines.items():

        # 2️⃣ Cross-validation sur TRAIN uniquement
        cv_scores = cross_val_score(
            pipe,
            X_train,
            y_train,
            cv=5,
            scoring="neg_mean_absolute_error"
        )
        
        mae_mean = -np.mean(cv_scores)
        mae_std = np.std(cv_scores)

        # 3️⃣ Entraînement final sur TRAIN complet
        pipe.fit(X_train, y_train)

        # 4️⃣ Score sur TEST
        r2_test = pipe.score(X_test, y_test)
       

        results[name] = {
            "CV_MAE_mean": mae_mean,
            "CV_MAE_std": mae_std,
            "Test_R2": r2_test
        }

    return results

# Si 50 valeurs dans tout le set: pas de découpe train/test mais cross_val_score: 
# Parce que la cross-validation :

#     découpe elle-même en 5 folds

#     entraîne sur 4

#     valide sur 1

#     répète 5 fois
def benchmark_models_RepeatedKFold(X, y):
    pipelines = build_all_pipelines()

    results = {}

    for name, model in pipelines.items():
        scores = cross_val_score(
            model,
            X,
            y,
            cv=5,
            scoring="neg_mean_absolute_error"
        )

        mae_scores = -scores
        results[name] = {
            "MAE_mean": np.mean(mae_scores),
            "MAE_std": np.std(mae_scores)
        }

    return results