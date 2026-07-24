"""Streamlit sayfaları için veri ve model yükleme yardımcıları."""
import json
import os
import sys

import joblib
import pandas as pd
import streamlit as st

APP_DIR = os.path.dirname(__file__)
ROOT_DIR = os.path.join(APP_DIR, "..")
DATA_DIR = os.path.join(ROOT_DIR, "data")
MODEL_PATH = os.path.join(ROOT_DIR, "models", "attrition_model.joblib")
METRICS_PATH = os.path.join(ROOT_DIR, "models", "attrition_model_metrics.json")
SENTIMENT_MODEL_PATH = os.path.join(ROOT_DIR, "models", "sentiment_model.joblib")
SENTIMENT_METRICS_PATH = os.path.join(ROOT_DIR, "models", "sentiment_model_metrics.json")

sys.path.insert(0, os.path.join(ROOT_DIR, "src"))


@st.cache_data
def load_employees() -> pd.DataFrame:
    path = os.path.join(DATA_DIR, "employees.csv")
    df = pd.read_csv(path)
    return df


@st.cache_resource
def load_model():
    if not os.path.exists(MODEL_PATH):
        return None
    return joblib.load(MODEL_PATH)


@st.cache_data
def load_model_metrics() -> dict | None:
    """Model karşılaştırma tablosu + değerlendirme eğrilerini (bkz. src/model.py:train) yükler.

    Dosya yoksa (ör. model.py hiç çalıştırılmamışsa veya eski bir sürümle
    eğitilmişse) None döner; çağıran taraf bunu "Model Özeti"nde bu bölümü
    atlayarak sessizce ele almalıdır.
    """
    if not os.path.exists(METRICS_PATH):
        return None
    with open(METRICS_PATH, encoding="utf-8") as f:
        return json.load(f)


@st.cache_resource
def load_sentiment_model():
    """Eğitilmiş TF-IDF + sınıflandırıcı duygu modelini (bkz. src/sentiment_model.py:train)
    yükler. Dosya yoksa None döner; çağıran taraf (company_panel.py) bu durumda ML
    toggle'ını devre dışı bırakıp sözlük tabanlı analyze_sentiment()'a sessizce döner."""
    if not os.path.exists(SENTIMENT_MODEL_PATH):
        return None
    return joblib.load(SENTIMENT_MODEL_PATH)


@st.cache_data
def load_sentiment_model_metrics() -> dict | None:
    if not os.path.exists(SENTIMENT_METRICS_PATH):
        return None
    with open(SENTIMENT_METRICS_PATH, encoding="utf-8") as f:
        return json.load(f)


@st.cache_resource
def load_explainer():
    bundle = load_model()
    if bundle is None:
        return None
    from model import build_explainer
    return build_explainer(bundle["pipeline"])


def data_ready() -> bool:
    return os.path.exists(os.path.join(DATA_DIR, "employees.csv"))


@st.cache_resource
def ollama_ready() -> bool:
    """Yerel Ollama sunucusu (localhost:11434) erişilebilir mi.

    Oturum başına bir kez yoklanır (cache_resource); erişilemezse False
    döner, exception yaymaz. CV Analizi panelindeki opsiyonel semantik
    eşleştirme toggle'ının gösterilip gösterilmeyeceğini belirler.
    """
    try:
        from ollama_client import is_available
        return is_available()
    except Exception:
        return False


@st.cache_resource
def ollama_models() -> list[str]:
    """Yüklü Ollama model adları; sunucuya erişilemezse boş liste döner."""
    try:
        from ollama_client import list_models
        return list_models()
    except Exception:
        return []
