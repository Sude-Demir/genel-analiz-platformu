"""Çalışan kaybı (attrition) tahmin modelini eğitir ve kaydeder."""
import json
import os

import joblib
import numpy as np
import pandas as pd
import shap
from lightgbm import LGBMClassifier
from sklearn.calibration import calibration_curve
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score, roc_curve
from sklearn.model_selection import RandomizedSearchCV, StratifiedKFold, learning_curve, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

BASE_DIR = os.path.dirname(__file__)
DATA_PATH = os.path.join(BASE_DIR, "..", "data", "employees.csv")
MODEL_PATH = os.path.join(BASE_DIR, "..", "models", "attrition_model.joblib")
METRICS_PATH = os.path.join(BASE_DIR, "..", "models", "attrition_model_metrics.json")

NUMERIC_FEATURES = [
    "Yas", "GunlukUcret", "EvUzakligiKm", "EgitimSeviyesi", "CalismaOrtamiTatmini",
    "SaatlikUcret", "IseBagliligi", "IsSeviyesi", "IsTatmini", "AylikGelir",
    "AylikUcretOrani", "OncekiSirketSayisi", "MaasArtisYuzdesi", "PerformansPuani",
    "IliskiTatmini", "HisseOpsiyonSeviyesi", "ToplamCalismaYili", "GecenYilEgitimSayisi",
    "IsYasamDengesi", "SirketteKidemYili", "MevcutRoldeKidemYili",
    "SonTerfidenBeriGecenYil", "YoneticiyleGecenYil",
]
CATEGORICAL_FEATURES = [
    "Departman", "Pozisyon", "FazlaMesai", "MedeniDurum", "SeyahatSikligi",
    "EgitimAlani", "Cinsiyet",
]
TARGET = "Attrition"


def _tree_preprocessor() -> ColumnTransformer:
    """Ağaç tabanlı modeller (LightGBM, RandomForest) için ortak preprocessing.

    Sayısal özellikler ölçeklendirilmeden bırakılır (remainder="passthrough") çünkü
    ağaç tabanlı modeller özellik ölçeğinden etkilenmez.
    """
    return ColumnTransformer([
        ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_FEATURES),
    ], remainder="passthrough")


def build_pipeline() -> Pipeline:
    model = LGBMClassifier(class_weight="balanced", random_state=42, verbose=-1)
    return Pipeline([("preprocess", _tree_preprocessor()), ("model", model)])


PARAM_DISTRIBUTIONS = {
    "model__n_estimators": [100, 200, 300, 500],
    "model__num_leaves": [15, 31, 63, 127],
    "model__learning_rate": [0.01, 0.03, 0.05, 0.1],
    "model__min_child_samples": [5, 10, 20, 30],
    "model__reg_alpha": [0, 0.1, 0.5, 1.0],
    "model__reg_lambda": [0, 0.1, 0.5, 1.0],
    "model__subsample": [0.7, 0.8, 0.9, 1.0],
    "model__colsample_bytree": [0.7, 0.8, 0.9, 1.0],
}

RF_PARAM_DISTRIBUTIONS = {
    "model__n_estimators": [200, 300, 500, 800],
    "model__max_depth": [4, 6, 8, 12, None],
    "model__min_samples_leaf": [1, 2, 5, 10],
    "model__max_features": ["sqrt", "log2", 0.5, 0.8],
}


def build_candidate_pipelines() -> dict[str, tuple[Pipeline, dict, int]]:
    """Karşılaştırılacak aday model pipeline'larını, hiperparametre arama uzaylarını ve
    RandomizedSearchCV iterasyon sayılarını döndürür.

    Adaylar kasıtlı olarak ağaç tabanlı modellerle sınırlıdır (LightGBM, RandomForest):
    her ikisi de `.feature_importances_` sağlar ve `shap.TreeExplainer` ile uyumludur,
    böylece hangisi seçilirse seçilsin mevcut açıklanabilirlik (SHAP) ve Aksiyon Merkezi
    zinciri (bkz. app/actions.py) hiçbir değişiklik gerektirmeden çalışmaya devam eder.
    """
    return {
        "LightGBM": (
            Pipeline([("preprocess", _tree_preprocessor()), ("model", LGBMClassifier(
                class_weight="balanced", random_state=42, verbose=-1,
            ))]),
            PARAM_DISTRIBUTIONS,
            30,
        ),
        "RandomForest": (
            Pipeline([("preprocess", _tree_preprocessor()), ("model", RandomForestClassifier(
                class_weight="balanced", random_state=42,
            ))]),
            RF_PARAM_DISTRIBUTIONS,
            20,
        ),
    }


def evaluate_predictions(y_test: pd.Series, y_pred, y_proba) -> dict:
    """Test seti tahminlerinden accuracy/ROC-AUC/classification_report/confusion_matrix/ROC eğrisi üretir."""
    fpr, tpr, _ = roc_curve(y_test, y_proba)
    return {
        "accuracy": float((y_pred == y_test).mean()),
        "roc_auc": float(roc_auc_score(y_test, y_proba)),
        "report": classification_report(y_test, y_pred, target_names=["Kalıyor", "Ayrılıyor"], output_dict=True),
        "confusion_matrix": confusion_matrix(y_test, y_pred).tolist(),
        "roc_curve": {"fpr": fpr.tolist(), "tpr": tpr.tolist()},
    }


def compute_learning_curve(pipeline: Pipeline, X_train: pd.DataFrame, y_train: pd.Series, cv) -> dict:
    """Eğitim seti büyüklüğü arttıkça CV ROC-AUC'nin nasıl değiştiğini (öğrenme eğrisi) hesaplar.

    Modelin daha fazla veriyle mi yoksa daha iyi özellik/hiperparametrelerle mi
    iyileşeceğini ayırt etmeye yarar (örn. eğri düzleşmişse veri eklemek yerine
    özellik mühendisliğine odaklanmak daha mantıklıdır).
    """
    train_sizes, train_scores, test_scores = learning_curve(
        pipeline, X_train, y_train, cv=cv, scoring="roc_auc",
        train_sizes=np.linspace(0.1, 1.0, 5), random_state=42,
    )
    return {
        "train_sizes": train_sizes.tolist(),
        "train_scores_mean": train_scores.mean(axis=1).tolist(),
        "test_scores_mean": test_scores.mean(axis=1).tolist(),
    }


def compute_calibration_curve(y_test: pd.Series, y_proba, n_bins: int = 10) -> dict:
    """Modelin verdiği olasılıkların gerçek gözlenen sıklıkla ne ölçüde örtüştüğünü hesaplar.

    Örn. model "%70 ayrılma olasılığı" dediğinde, gerçekte bu gruptaki çalışanların
    gerçekten ~%70'i ayrılmışsa model iyi kalibre edilmiş demektir.
    """
    prob_true, prob_pred = calibration_curve(y_test, y_proba, n_bins=n_bins)
    return {"prob_true": prob_true.tolist(), "prob_pred": prob_pred.tolist()}


def train():
    df = pd.read_csv(DATA_PATH)
    X = df[CATEGORICAL_FEATURES + NUMERIC_FEATURES]
    y = (df[TARGET] == "Evet").astype(int)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42
    )

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

    comparison = []
    best_name, best_pipeline, best_cv_score = None, None, -1.0
    for name, (candidate_pipeline, param_dist, n_iter) in build_candidate_pipelines().items():
        search = RandomizedSearchCV(
            candidate_pipeline, param_dist,
            n_iter=n_iter, scoring="roc_auc", cv=cv, random_state=42, n_jobs=-1,
        )
        search.fit(X_train, y_train)
        comparison.append({
            "model": name,
            "cv_roc_auc": float(search.best_score_),
            "best_params": search.best_params_,
        })
        print(f"[{name}] CV ROC-AUC (ortalama): {search.best_score_:.3f}  |  hiperparametreler: {search.best_params_}")
        if search.best_score_ > best_cv_score:
            best_name, best_pipeline, best_cv_score = name, search.best_estimator_, search.best_score_

    comparison.sort(key=lambda r: r["cv_roc_auc"], reverse=True)
    print(f"\nSeçilen model: {best_name} (CV ROC-AUC: {best_cv_score:.3f})")

    y_pred = best_pipeline.predict(X_test)
    y_proba = best_pipeline.predict_proba(X_test)[:, 1]
    eval_metrics = evaluate_predictions(y_test, y_pred, y_proba)

    print(classification_report(y_test, y_pred, target_names=["Kalıyor", "Ayrılıyor"]))
    print(f"Test ROC-AUC: {eval_metrics['roc_auc']:.3f}")

    learning = compute_learning_curve(best_pipeline, X_train, y_train, cv)
    calibration = compute_calibration_curve(y_test, y_proba)

    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    joblib.dump({
        "pipeline": best_pipeline,
        "model_name": best_name,
        "numeric_features": NUMERIC_FEATURES,
        "categorical_features": CATEGORICAL_FEATURES,
    }, MODEL_PATH)
    print(f"Model kaydedildi: {MODEL_PATH}")

    with open(METRICS_PATH, "w", encoding="utf-8") as f:
        json.dump({
            "selected_model": best_name,
            "model_comparison": comparison,
            "test_metrics": {
                "accuracy": eval_metrics["accuracy"],
                "roc_auc": eval_metrics["roc_auc"],
                "report": eval_metrics["report"],
            },
            "confusion_matrix": eval_metrics["confusion_matrix"],
            "roc_curve": eval_metrics["roc_curve"],
            "learning_curve": learning,
            "calibration_curve": calibration,
        }, f, ensure_ascii=False, indent=2)
    print(f"Metrikler kaydedildi: {METRICS_PATH}")


def get_feature_importances(pipeline: Pipeline) -> pd.Series:
    ohe: OneHotEncoder = pipeline.named_steps["preprocess"].named_transformers_["cat"]
    cat_names = list(ohe.get_feature_names_out(CATEGORICAL_FEATURES))
    all_names = cat_names + NUMERIC_FEATURES
    importances = pipeline.named_steps["model"].feature_importances_
    return pd.Series(importances, index=all_names).sort_values(ascending=False)


def build_explainer(pipeline: Pipeline) -> shap.TreeExplainer:
    """Ağaç modeli için SHAP explainer'ı oluşturur (pahalı olduğu için çağıran taraf cache'lemeli)."""
    return shap.TreeExplainer(pipeline.named_steps["model"])


def explain_batch(pipeline: Pipeline, explainer: shap.TreeExplainer, X: pd.DataFrame) -> pd.DataFrame:
    """Birden çok çalışan satırı için her özelliğin risk skoruna katkısını (SHAP değeri) döndürür.

    Satırlar X ile aynı index'i, kolonlar genişletilmiş özellik adlarını taşır.
    Pozitif değer ayrılma riskini artırır, negatif değer azaltır.
    """
    X_trans = pipeline.named_steps["preprocess"].transform(X)
    if hasattr(X_trans, "toarray"):
        X_trans = X_trans.toarray()

    shap_values = explainer.shap_values(X_trans)
    if isinstance(shap_values, list):
        values = shap_values[1]  # "Evet" (ayrılıyor) sınıfına ait katkılar
    elif shap_values.ndim == 3:
        values = shap_values[:, :, 1]
    else:
        values = shap_values

    ohe: OneHotEncoder = pipeline.named_steps["preprocess"].named_transformers_["cat"]
    cat_names = list(ohe.get_feature_names_out(CATEGORICAL_FEATURES))
    all_names = cat_names + NUMERIC_FEATURES
    return pd.DataFrame(values, index=X.index, columns=all_names)


def explain_instance(pipeline: Pipeline, explainer: shap.TreeExplainer, X_row: pd.DataFrame) -> pd.Series:
    """Tek bir çalışan satırı için her özelliğin risk skoruna katkısını (SHAP değeri) döndürür."""
    return explain_batch(pipeline, explainer, X_row).iloc[0]


def apply_scenario(
    X: pd.DataFrame,
    salary_increase_pct: float = 0,
    remove_overtime: bool = False,
    improve_wlb: bool = False,
) -> pd.DataFrame:
    """Seçilen çalışan(lar) için varsayımsal bir İK müdahale senaryosu uygular ve değiştirilmiş kopyayı döndürür."""
    X = X.copy()
    if salary_increase_pct:
        X["AylikGelir"] = X["AylikGelir"] * (1 + salary_increase_pct / 100)
    if remove_overtime:
        X["FazlaMesai"] = "Hayır"
    if improve_wlb:
        X["IsYasamDengesi"] = (X["IsYasamDengesi"] + 1).clip(upper=4)
    return X


if __name__ == "__main__":
    train()
