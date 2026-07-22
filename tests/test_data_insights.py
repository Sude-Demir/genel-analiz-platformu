import pandas as pd

from data_insights import data_quality_report, detect_outliers, generate_insights


def test_data_quality_report_detects_duplicate_rows():
    df = pd.DataFrame({"a": [1, 1, 2], "b": ["x", "x", "y"]})
    report = data_quality_report(df)
    assert report["yinelenen_satir"] == 1


def test_data_quality_report_detects_constant_column():
    df = pd.DataFrame({"a": [1, 2, 3], "sabit": ["x", "x", "x"]})
    report = data_quality_report(df)
    assert "sabit" in report["sabit_kolonlar"]


def test_data_quality_report_detects_high_missing_column():
    df = pd.DataFrame({
        "a": range(20),
        "cok_eksik": [None] * 15 + [1] * 5,
    })
    report = data_quality_report(df)
    assert "cok_eksik" in report["yuksek_eksiklikli_kolonlar"]
    assert report["yuksek_eksiklikli_kolonlar"]["cok_eksik"] == 0.75


def test_data_quality_report_detects_high_cardinality_categorical():
    df = pd.DataFrame({
        "id_benzeri": [f"kod-{i}" for i in range(25)],
        "sabit_kategori": ["A"] * 25,
    })
    report = data_quality_report(df)
    assert "id_benzeri" in report["yuksek_kardinaliteli_kolonlar"]


def test_detect_outliers_finds_extreme_value():
    df = pd.DataFrame({"deger": [10, 11, 12, 13, 12, 11, 10, 1000]})
    result = detect_outliers(df)
    assert "deger" in result["Kolon"].tolist()
    row = result[result["Kolon"] == "deger"].iloc[0]
    assert row["Aykırı Değer Sayısı"] == 1


def test_detect_outliers_returns_empty_when_no_outliers():
    df = pd.DataFrame({"deger": [10, 11, 12, 13, 11, 12]})
    result = detect_outliers(df)
    assert result.empty


def test_generate_insights_reports_strong_correlation():
    df = pd.DataFrame({
        "x": [1, 2, 3, 4, 5],
        "y": [2, 4, 6, 8, 10],
    })
    insights = generate_insights(df)
    assert any("x" in i and "y" in i for i in insights)


def test_generate_insights_reports_missing_data():
    df = pd.DataFrame({
        "a": list(range(10)),
        "eksik_kolon": [None] * 5 + list(range(5)),
    })
    insights = generate_insights(df)
    assert any("eksik_kolon" in i for i in insights)


def test_generate_insights_reports_imbalanced_category():
    df = pd.DataFrame({
        "kategori": ["A"] * 19 + ["B"],
    })
    insights = generate_insights(df)
    assert any("kategori" in i for i in insights)


def test_generate_insights_reports_duplicate_rows():
    df = pd.DataFrame({"a": [1, 1], "b": [2, 2]})
    insights = generate_insights(df)
    assert any("yinelenen" in i for i in insights)


def test_generate_insights_handles_empty_dataframe_without_error():
    df = pd.DataFrame()
    insights = generate_insights(df)
    assert insights == []
