"""Çalışan kaybı (attrition) tahmin modelini eğitir ve kaydeder."""
import os

import joblib
import pandas as pd
import shap
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

BASE_DIR = os.path.dirname(__file__)
DATA_PATH = os.path.join(BASE_DIR, "..", "data", "employees.csv")
MODEL_PATH = os.path.join(BASE_DIR, "..", "models", "attrition_model.joblib")

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


def build_pipeline() -> Pipeline:
    preprocessor = ColumnTransformer([
        ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_FEATURES),
    ], remainder="passthrough")

    model = RandomForestClassifier(
        n_estimators=300, max_depth=8, min_samples_leaf=5,
        class_weight="balanced", random_state=42,
    )
    return Pipeline([("preprocess", preprocessor), ("model", model)])


def train():
    df = pd.read_csv(DATA_PATH)
    X = df[CATEGORICAL_FEATURES + NUMERIC_FEATURES]
    y = (df[TARGET] == "Evet").astype(int)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42
    )

    pipeline = build_pipeline()
    pipeline.fit(X_train, y_train)

    y_pred = pipeline.predict(X_test)
    y_proba = pipeline.predict_proba(X_test)[:, 1]

    print(classification_report(y_test, y_pred, target_names=["Kalıyor", "Ayrılıyor"]))
    print(f"ROC-AUC: {roc_auc_score(y_test, y_proba):.3f}")

    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    joblib.dump({
        "pipeline": pipeline,
        "numeric_features": NUMERIC_FEATURES,
        "categorical_features": CATEGORICAL_FEATURES,
    }, MODEL_PATH)
    print(f"Model kaydedildi: {MODEL_PATH}")


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
