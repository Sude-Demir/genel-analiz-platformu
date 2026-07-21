"""Streamlit sayfaları için veri ve model yükleme yardımcıları."""
import os
import sys

import joblib
import pandas as pd
import streamlit as st

APP_DIR = os.path.dirname(__file__)
ROOT_DIR = os.path.join(APP_DIR, "..")
DATA_DIR = os.path.join(ROOT_DIR, "data")
MODEL_PATH = os.path.join(ROOT_DIR, "models", "attrition_model.joblib")

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


@st.cache_resource
def load_explainer():
    bundle = load_model()
    if bundle is None:
        return None
    from model import build_explainer
    return build_explainer(bundle["pipeline"])


def data_ready() -> bool:
    return os.path.exists(os.path.join(DATA_DIR, "employees.csv"))
