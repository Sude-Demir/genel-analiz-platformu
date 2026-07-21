"""Herhangi bir yüklenen veri seti için otomatik kolon tipi algılama ve model eğitimi.

`model.py`'daki İK/attrition modeline özel kod ile kasıtlı olarak ayrı tutulur;
burada özellik listeleri sabit değil, çalışma zamanında verilen veri setine göre belirlenir.
"""
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import classification_report, r2_score, roc_auc_score, root_mean_squared_error
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

CATEGORICAL_MAX_NUMERIC_CARDINALITY = 10


def infer_column_types(df: pd.DataFrame, exclude: list[str] = ()) -> tuple[list[str], list[str]]:
    """Kolonları basit bir kurala göre sayısal/kategorik olarak ayırır: sayısal dtype -> sayısal, diğerleri -> kategorik."""
    numeric, categorical = [], []
    for col in df.columns:
        if col in exclude:
            continue
        if pd.api.types.is_numeric_dtype(df[col]):
            numeric.append(col)
        else:
            categorical.append(col)
    return numeric, categorical


def detect_task_type(y: pd.Series) -> str:
    """Hedef kolonun sınıflandırma mı regresyon mu olduğunu tahmin eder."""
    if pd.api.types.is_numeric_dtype(y) and y.nunique() > CATEGORICAL_MAX_NUMERIC_CARDINALITY:
        return "regression"
    return "classification"


def build_pipeline(categorical_features: list[str], numeric_features: list[str], task_type: str) -> Pipeline:
    preprocessor = ColumnTransformer([
        ("cat", OneHotEncoder(handle_unknown="ignore"), categorical_features),
    ], remainder="passthrough")

    model = (
        RandomForestClassifier(n_estimators=200, max_depth=8, min_samples_leaf=5, class_weight="balanced", random_state=42)
        if task_type == "classification"
        else RandomForestRegressor(n_estimators=200, max_depth=8, min_samples_leaf=5, random_state=42)
    )
    return Pipeline([("preprocess", preprocessor), ("model", model)])


def train_auto_model(df: pd.DataFrame, target_col: str, categorical_features: list[str], numeric_features: list[str]) -> dict:
    """Verilen hedef kolona göre otomatik bir model eğitir ve sonuçları/metrikleri döndürür."""
    task_type = detect_task_type(df[target_col])
    X = df[categorical_features + numeric_features]
    y = df[target_col]

    if task_type == "classification" and (y.dtype == object or y.dtype.name == "category"):
        y = y.astype("category").cat.codes
        class_labels = list(df[target_col].astype("category").cat.categories)
    else:
        class_labels = sorted(y.unique().tolist()) if task_type == "classification" else None

    stratify = y if task_type == "classification" else None
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=stratify)

    pipeline = build_pipeline(categorical_features, numeric_features, task_type)
    pipeline.fit(X_train, y_train)

    metrics: dict = {}
    n_classes = y.nunique() if task_type == "classification" else None
    if task_type == "classification":
        y_pred = pipeline.predict(X_test)
        y_proba = pipeline.predict_proba(X_test)
        metrics["accuracy"] = float((y_pred == y_test).mean())
        try:
            metrics["roc_auc"] = float(
                roc_auc_score(y_test, y_proba[:, 1]) if n_classes == 2
                else roc_auc_score(y_test, y_proba, multi_class="ovr")
            )
        except ValueError:
            metrics["roc_auc"] = None
        metrics["report"] = classification_report(y_test, y_pred, output_dict=True)
    else:
        y_pred = pipeline.predict(X_test)
        metrics["r2"] = float(r2_score(y_test, y_pred))
        metrics["rmse"] = float(root_mean_squared_error(y_test, y_pred))

    return {
        "pipeline": pipeline,
        "task_type": task_type,
        "n_classes": n_classes,
        "class_labels": class_labels,
        "metrics": metrics,
        "categorical_features": categorical_features,
        "numeric_features": numeric_features,
        "target_col": target_col,
    }


def get_feature_importances(pipeline: Pipeline, categorical_features: list[str], numeric_features: list[str]) -> pd.Series:
    ohe: OneHotEncoder = pipeline.named_steps["preprocess"].named_transformers_["cat"]
    names = list(ohe.get_feature_names_out(categorical_features)) + numeric_features
    importances = pipeline.named_steps["model"].feature_importances_
    return pd.Series(importances, index=names).sort_values(ascending=False)


def explain_batch(pipeline: Pipeline, explainer, X: pd.DataFrame, categorical_features: list[str], numeric_features: list[str]) -> pd.DataFrame:
    """Sınıflandırmada pozitif sınıf (kod=1), regresyonda tahmin çıktısı için SHAP katkı matrisini döndürür."""
    X_trans = pipeline.named_steps["preprocess"].transform(X)
    if hasattr(X_trans, "toarray"):
        X_trans = X_trans.toarray()

    shap_values = explainer.shap_values(X_trans)
    if isinstance(shap_values, list):
        values = shap_values[1] if len(shap_values) > 1 else shap_values[0]
    elif getattr(shap_values, "ndim", 2) == 3:
        values = shap_values[:, :, 1]
    else:
        values = shap_values

    ohe: OneHotEncoder = pipeline.named_steps["preprocess"].named_transformers_["cat"]
    names = list(ohe.get_feature_names_out(categorical_features)) + numeric_features
    return pd.DataFrame(values, index=X.index, columns=names)
