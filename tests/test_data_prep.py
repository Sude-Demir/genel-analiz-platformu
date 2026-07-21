import os

import pandas as pd

from data_prep import COLUMN_MAP, RAW_PATH, VALUE_MAP, prepare


def test_prepare_produces_turkish_columns():
    df = prepare()
    for turkce_ad in COLUMN_MAP.values():
        assert turkce_ad in df.columns


def test_value_map_leaves_no_missing_values():
    df = prepare()
    for kolon in VALUE_MAP:
        assert df[kolon].isna().sum() == 0, f"{kolon} kolonunda eşlenmemiş değer var"


def test_attrition_values_are_turkish():
    df = prepare()
    assert set(df["Attrition"].unique()) <= {"Evet", "Hayır"}


def test_row_count_matches_raw_file():
    raw_df = pd.read_csv(RAW_PATH)
    df = prepare()
    assert len(df) == len(raw_df)


def test_constant_columns_are_dropped():
    df = prepare()
    for sabit_kolon in ("EmployeeCount", "Over18", "StandardHours"):
        assert sabit_kolon not in df.columns
