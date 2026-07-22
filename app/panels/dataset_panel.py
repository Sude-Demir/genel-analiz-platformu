"""Dataset Analizi paneli — dosya yükleme, genel istatistik/görselleştirme ve
altında listelenen özel analiz modülleri (İK'ya özgü modüller + genel otomatik model).
"""
import pandas as pd
import plotly.express as px
import streamlit as st

from auto_model import infer_column_types
from data_insights import data_quality_report, detect_outliers, generate_insights
from data_loader import data_ready, load_employees, load_explainer, load_model
from export_utils import build_pdf, to_json_bytes
from model import CATEGORICAL_FEATURES, NUMERIC_FEATURES
from panels.hr_modules import action_center, attrition, auto_model_module, performance, salary_career
from theme import CATEGORICAL, SEQUENTIAL_BLUE, apply_layout

REQUIRED_HR_COLUMNS = set(CATEGORICAL_FEATURES + NUMERIC_FEATURES + ["CalisanID", "Attrition"])


def load_uploaded(uploaded) -> pd.DataFrame:
    name = uploaded.name.lower()
    if name.endswith((".xlsx", ".xls")):
        return pd.read_excel(uploaded)
    if name.endswith(".json"):
        return pd.read_json(uploaded)
    return pd.read_csv(uploaded)


def _render_general_stats(df: pd.DataFrame, name: str):
    st.success(f"Aktif veri seti: **{name}** — {len(df)} satır, {len(df.columns)} kolon")
    with st.container(border=True):
        st.dataframe(df.head(20), width="stretch")

        numeric_cols, categorical_cols = infer_column_types(df)
        st.write(f"**{len(numeric_cols)}** sayısal, **{len(categorical_cols)}** kategorik kolon algılandı.")

        st.markdown("### Genel İstatistikler")
        describe_df = df.describe().T
        st.dataframe(describe_df, width="stretch")

        missing = df.isna().sum()
        missing = missing[missing > 0]
        if not missing.empty:
            st.markdown("**Eksik Değerler**")
            st.dataframe(missing.rename("Eksik Sayısı").to_frame(), width="stretch")

    st.markdown("### 🔎 Veri Kalitesi & Otomatik İçgörüler")
    with st.container(border=True):
        quality = data_quality_report(df)
        outliers_df = detect_outliers(df)
        insights = generate_insights(df)

        if insights:
            st.markdown("**Otomatik İçgörüler**")
            for metin in insights:
                st.markdown(f"- {metin}")
        else:
            st.caption("Bu veri setinde öne çıkan otomatik bir içgörü bulunamadı.")

        kalite_notlari = []
        if quality["yinelenen_satir"] > 0:
            kalite_notlari.append(f"{quality['yinelenen_satir']} adet birebir yinelenen satır var.")
        if quality["sabit_kolonlar"]:
            kalite_notlari.append(f"Sabit/tek değerli kolonlar: {', '.join(quality['sabit_kolonlar'])}.")
        if quality["yuksek_kardinaliteli_kolonlar"]:
            kalite_notlari.append(
                f"Neredeyse her satırda farklı değer alan (ID benzeri) kolonlar: "
                f"{', '.join(quality['yuksek_kardinaliteli_kolonlar'])}."
            )
        if quality["yuksek_eksiklikli_kolonlar"]:
            kalite_notlari.append(
                "Yüksek oranda eksik veri içeren kolonlar: "
                + ", ".join(f"{k} (%{round(v * 100)})" for k, v in quality["yuksek_eksiklikli_kolonlar"].items())
                + "."
            )
        if kalite_notlari:
            st.markdown("**Veri Kalitesi Notları**")
            for not_metni in kalite_notlari:
                st.markdown(f"- {not_metni}")

        if not outliers_df.empty:
            st.markdown("**Aykırı Değerler (IQR yöntemi)**")
            st.dataframe(outliers_df, width="stretch")

    st.markdown("### Görselleştirmeler")
    with st.container(border=True):
        if numeric_cols:
            st.markdown("**Sayısal Kolon Dağılımları**")
            secilen_num = st.multiselect("Kolon seç", numeric_cols, default=numeric_cols[:4], key="ds_num_cols")
            for col in secilen_num:
                fig = px.histogram(df, x=col, color_discrete_sequence=[CATEGORICAL[0]])
                apply_layout(fig, showlegend=False)
                st.plotly_chart(fig, width="stretch", theme=None)

        if categorical_cols:
            st.markdown("**Kategorik Kolon Dağılımları**")
            secilen_cat = st.multiselect("Kolon seç", categorical_cols, default=categorical_cols[:4], key="ds_cat_cols")
            for col in secilen_cat:
                counts = df[col].astype(str).value_counts().head(15)
                fig = px.bar(
                    x=counts.index, y=counts.values,
                    labels={"x": col, "y": "Adet"},
                    color_discrete_sequence=[CATEGORICAL[1]],
                )
                apply_layout(fig, showlegend=False)
                st.plotly_chart(fig, width="stretch", theme=None)

        corr = None
        if len(numeric_cols) >= 2:
            st.markdown("**Korelasyon Matrisi**")
            corr = df[numeric_cols].corr()
            fig = px.imshow(corr, color_continuous_scale=SEQUENTIAL_BLUE, zmin=-1, zmax=1)
            apply_layout(fig)
            st.plotly_chart(fig, width="stretch", theme=None)

    st.markdown("### Dışa Aktar")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.download_button(
            "İstatistik Özetini CSV indir",
            data=describe_df.to_csv().encode("utf-8"),
            file_name=f"{name}_istatistik_ozeti.csv", mime="text/csv", key="ds_csv",
        )
    with c2:
        json_payload = {
            "veri_seti": name,
            "satir_sayisi": len(df),
            "kolon_sayisi": len(df.columns),
            "sayisal_kolonlar": numeric_cols,
            "kategorik_kolonlar": categorical_cols,
            "ozet_istatistikler": describe_df.to_dict(orient="index"),
            "eksik_degerler": missing.to_dict(),
            "veri_kalitesi": quality,
            "aykiri_degerler": outliers_df.to_dict(orient="records"),
            "otomatik_icgoruler": insights,
        }
        st.download_button(
            "JSON indir", data=to_json_bytes(json_payload),
            file_name=f"{name}_rapor.json", mime="application/json", key="ds_json",
        )
    with c3:
        blocks = [
            {"heading": "Genel Bilgiler", "type": "bullets", "content": [
                f"Satır sayısı: {len(df)}", f"Kolon sayısı: {len(df.columns)}",
                f"Sayısal kolonlar: {', '.join(numeric_cols) or '—'}",
                f"Kategorik kolonlar: {', '.join(categorical_cols) or '—'}",
            ]},
        ]
        if not missing.empty:
            blocks.append({"heading": "Eksik Değerler", "type": "table", "content": (
                ["Kolon", "Eksik Sayısı"], list(missing.items()),
            )})
        if insights:
            blocks.append({"heading": "Otomatik İçgörüler", "type": "bullets", "content": insights})
        if not outliers_df.empty:
            blocks.append({"heading": "Aykırı Değerler (IQR)", "type": "table", "content": (
                list(outliers_df.columns), [tuple(row) for row in outliers_df.itertuples(index=False)],
            )})
        pdf_bytes = build_pdf(f"Veri Seti Analiz Raporu — {name}", blocks)
        st.download_button(
            "PDF indir", data=pdf_bytes,
            file_name=f"{name}_rapor.pdf", mime="application/pdf", key="ds_pdf",
        )


def render():
    st.subheader("Veri Seti Yükle")
    kaynak = st.radio("Kaynak", ["Dosya Yükle", "Dahili İK Örnek Verisi"], horizontal=True, key="ds_kaynak")

    if kaynak == "Dosya Yükle":
        uploaded = st.file_uploader("CSV, Excel veya JSON dosyası", type=["csv", "xlsx", "xls", "json"], key="ds_upload")
        if uploaded is not None:
            try:
                with st.spinner("Dosya okunuyor..."):
                    st.session_state["ds_df"] = load_uploaded(uploaded)
                st.session_state["ds_name"] = uploaded.name
                st.session_state["ds_is_builtin"] = False
            except Exception as exc:
                st.error(
                    "Dosya okunamadı. Dosyanın seçilen formatta (CSV/Excel/JSON) ve bozuk olmadığından "
                    f"emin olun. (Teknik detay: {exc})"
                )
    else:
        if not data_ready():
            st.warning("Dahili İK veri seti bulunamadı. Önce `python src/data_prep.py` çalıştırın.")
        elif st.button("Dahili İK Veri Setini Yükle"):
            st.session_state["ds_df"] = load_employees()
            st.session_state["ds_name"] = "İK Çalışan Verisi (dahili)"
            st.session_state["ds_is_builtin"] = True

    if "ds_df" not in st.session_state:
        st.info("Devam etmek için bir dosya yükleyin veya dahili İK veri setini seçin.")
        return

    df = st.session_state["ds_df"]
    name = st.session_state["ds_name"]
    _render_general_stats(df, name)

    st.divider()
    st.markdown("## 🧩 Özel Analiz Modülleri")

    has_hr_schema = REQUIRED_HR_COLUMNS.issubset(set(df.columns))
    bundle = load_model() if has_hr_schema else None
    explainer = load_explainer() if bundle is not None else None

    options = ["Yok (sadece genel istatistik)", "🤖 Otomatik Model Eğitimi & Açıklama (Genel)"]
    if has_hr_schema and bundle is not None:
        options += [
            "📉 Çalışan Kaybı Tahmini", "🏆 Performans Analizi",
            "💰 Maaş & Kariyer Analizi", "🎯 Aksiyon Merkezi",
        ]
    elif not has_hr_schema:
        st.caption(
            "İK'ya özgü modüller (Çalışan Kaybı Tahmini, Performans Analizi, Maaş & Kariyer Analizi, "
            "Aksiyon Merkezi) yalnızca beklenen İK şemasına sahip bir veri setinde (örn. dahili İK "
            "örnek verisi) kullanılabilir."
        )
    elif bundle is None:
        st.caption("Eğitilmiş çalışan kaybı modeli bulunamadı; önce `python src/model.py` çalıştırın.")

    # İK şeması + eğitilmiş model mevcutsa, en yüksek değerli modül (Çalışan Kaybı Tahmini)
    # varsayılan olarak seçili gelir; kullanıcı "ds_module_select" widget'ıyla daha önce
    # etkileşime girdiyse bu index yok sayılır (Streamlit yalnızca ilk render'da uygular).
    default_index = 0
    if has_hr_schema and bundle is not None and "📉 Çalışan Kaybı Tahmini" in options:
        default_index = options.index("📉 Çalışan Kaybı Tahmini")

    secim = st.selectbox("Modül Seç", options, index=default_index, key="ds_module_select")

    if secim == "🤖 Otomatik Model Eğitimi & Açıklama (Genel)":
        auto_model_module.render(df, state_prefix="ds")
    elif secim == "📉 Çalışan Kaybı Tahmini":
        attrition.render(df, bundle["pipeline"], explainer)
    elif secim == "🏆 Performans Analizi":
        performance.render(df)
    elif secim == "💰 Maaş & Kariyer Analizi":
        salary_career.render(df)
    elif secim == "🎯 Aksiyon Merkezi":
        action_center.render(df, bundle["pipeline"], explainer)
