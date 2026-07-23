"""Dataset Analizi paneli — dosya yükleme, genel istatistik/görselleştirme ve özel analiz modülleri."""
import pandas as pd
import plotly.express as px
import streamlit as st

from auto_model import infer_column_types
from data_insights import data_quality_report, detect_outliers, generate_insights
from data_loader import data_ready, load_employees, load_explainer, load_model
from export_utils import build_pdf, to_json_bytes
from translator import tr, trf
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
    st.success(trf(
        "Aktif veri seti: **{name}** — {rows} satır, {cols} kolon",
        name=name, rows=len(df), cols=len(df.columns),
    ))
    with st.container(border=True):
        st.dataframe(df.head(20), width="stretch")

        numeric_cols, categorical_cols = infer_column_types(df)
        st.write(trf(
            "**{n_num}** sayısal, **{n_cat}** kategorik kolon algılandı.",
            n_num=len(numeric_cols), n_cat=len(categorical_cols),
        ))

        st.markdown(tr("### Genel İstatistikler"))
        describe_df = df.describe().T
        st.dataframe(describe_df, width="stretch")

        missing = df.isna().sum()
        missing = missing[missing > 0]
        if not missing.empty:
            st.markdown(tr("**Eksik Değerler**"))
            st.dataframe(missing.rename(tr("Eksik Sayısı")).to_frame(), width="stretch")

    st.markdown(tr("### 🔎 Veri Kalitesi & Otomatik İçgörüler"))
    with st.container(border=True):
        quality = data_quality_report(df)
        outliers_df = detect_outliers(df)
        insights = generate_insights(df)

        if insights:
            st.markdown(tr("**Otomatik İçgörüler**"))
            for metin in insights:
                st.markdown(f"- {tr(metin)}")
        else:
            st.caption(tr("Bu veri setinde öne çıkan otomatik bir içgörü bulunamadı."))

        kalite_notlari = []
        if quality["yinelenen_satir"] > 0:
            kalite_notlari.append(trf("{n} adet birebir yinelenen satır var.", n=quality['yinelenen_satir']))
        if quality["sabit_kolonlar"]:
            kalite_notlari.append(trf("Sabit/tek değerli kolonlar: {cols}.", cols=', '.join(quality['sabit_kolonlar'])))
        if quality["yuksek_kardinaliteli_kolonlar"]:
            kalite_notlari.append(trf(
                "Neredeyse her satırda farklı değer alan (ID benzeri) kolonlar: {cols}.",
                cols=', '.join(quality['yuksek_kardinaliteli_kolonlar']),
            ))
        if quality["yuksek_eksiklikli_kolonlar"]:
            kalite_notlari.append(trf(
                "Yüksek oranda eksik veri içeren kolonlar: {cols}.",
                cols=", ".join(f"{k} (%{round(v * 100)})" for k, v in quality["yuksek_eksiklikli_kolonlar"].items()),
            ))
        if kalite_notlari:
            st.markdown(tr("**Veri Kalitesi Notları**"))
            for not_metni in kalite_notlari:
                st.markdown(f"- {not_metni}")

        if not outliers_df.empty:
            st.markdown(tr("**Aykırı Değerler (IQR yöntemi)**"))
            st.dataframe(outliers_df, width="stretch")

    st.markdown(tr("### Görselleştirmeler"))
    with st.container(border=True):
        if numeric_cols:
            st.markdown(tr("**Sayısal Kolon Dağılımları**"))
            secilen_num = st.multiselect(tr("Kolon seç"), numeric_cols, default=numeric_cols[:4], key="ds_num_cols")
            for col in secilen_num:
                fig = px.histogram(df, x=col, color_discrete_sequence=[CATEGORICAL[0]])
                apply_layout(fig, showlegend=False)
                st.plotly_chart(fig, width="stretch", theme=None)

        if categorical_cols:
            st.markdown(tr("**Kategorik Kolon Dağılımları**"))
            secilen_cat = st.multiselect(tr("Kolon seç"), categorical_cols, default=categorical_cols[:4], key="ds_cat_cols")
            for col in secilen_cat:
                counts = df[col].astype(str).value_counts().head(15)
                fig = px.bar(
                    x=counts.index, y=counts.values,
                    labels={"x": col, "y": tr("Adet")},
                    color_discrete_sequence=[CATEGORICAL[1]],
                )
                apply_layout(fig, showlegend=False)
                st.plotly_chart(fig, width="stretch", theme=None)

        if len(numeric_cols) >= 2:
            st.markdown(tr("**Korelasyon Matrisi**"))
            corr = df[numeric_cols].corr()
            fig = px.imshow(corr, color_continuous_scale=SEQUENTIAL_BLUE, zmin=-1, zmax=1)
            apply_layout(fig)
            st.plotly_chart(fig, width="stretch", theme=None)

    st.markdown(tr("### Dışa Aktar"))
    c1, c2, c3 = st.columns(3)
    with c1:
        st.download_button(
            tr("İstatistik Özetini CSV indir"),
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
            tr("JSON indir"), data=to_json_bytes(json_payload),
            file_name=f"{name}_rapor.json", mime="application/json", key="ds_json",
        )
    with c3:
        blocks = [
            {"heading": tr("Genel Bilgiler"), "type": "bullets", "content": [
                trf("Satır sayısı: {n}", n=len(df)),
                trf("Kolon sayısı: {n}", n=len(df.columns)),
                trf("Sayısal kolonlar: {cols}", cols=', '.join(numeric_cols) or '—'),
                trf("Kategorik kolonlar: {cols}", cols=', '.join(categorical_cols) or '—'),
            ]},
        ]
        if not missing.empty:
            blocks.append({"heading": tr("Eksik Değerler"), "type": "table", "content": (
                [tr("Kolon"), tr("Eksik Sayısı")], list(missing.items()),
            )})
        if insights:
            blocks.append({"heading": tr("Otomatik İçgörüler"), "type": "bullets", "content": insights})
        if not outliers_df.empty:
            blocks.append({"heading": tr("Aykırı Değerler (IQR)"), "type": "table", "content": (
                list(outliers_df.columns), [tuple(row) for row in outliers_df.itertuples(index=False)],
            )})
        pdf_bytes = build_pdf(trf("Veri Seti Analiz Raporu — {name}", name=name), blocks)
        st.download_button(
            tr("PDF indir"), data=pdf_bytes,
            file_name=f"{name}_rapor.pdf", mime="application/pdf", key="ds_pdf",
        )


def render():
    st.subheader(tr("Veri Seti Yükle"))
    kaynak_dosya = tr("Dosya Yükle")
    kaynak_dahili = tr("Dahili İK Örnek Verisi")
    kaynak = st.radio(tr("Kaynak"), [kaynak_dosya, kaynak_dahili], horizontal=True, key="ds_kaynak")

    if kaynak == kaynak_dosya:
        uploaded = st.file_uploader(tr("CSV, Excel veya JSON dosyası"), type=["csv", "xlsx", "xls", "json"], key="ds_upload")
        if uploaded is not None:
            try:
                with st.spinner(tr("Dosya okunuyor...")):
                    st.session_state["ds_df"] = load_uploaded(uploaded)
                st.session_state["ds_name"] = uploaded.name
                st.session_state["ds_is_builtin"] = False
            except Exception as exc:
                st.error(trf("Dosya okunamadı. ({hata})", hata=exc))
    else:
        if not data_ready():
            st.warning(tr("Dahili İK veri seti bulunamadı. Önce `python src/data_prep.py` çalıştırın."))
        elif st.button(tr("Dahili İK Veri Setini Yükle")):
            st.session_state["ds_df"] = load_employees()
            st.session_state["ds_name"] = tr("İK Çalışan Verisi (dahili)")
            st.session_state["ds_is_builtin"] = True

    if "ds_df" not in st.session_state:
        st.info(tr("Devam etmek için bir dosya yükleyin veya dahili İK veri setini seçin."))
        return

    df = st.session_state["ds_df"]
    name = st.session_state["ds_name"]
    _render_general_stats(df, name)

    st.divider()
    st.markdown(tr("## 🧩 Özel Analiz Modülleri"))

    has_hr_schema = REQUIRED_HR_COLUMNS.issubset(set(df.columns))
    bundle = load_model() if has_hr_schema else None
    explainer = load_explainer() if bundle is not None else None

    modul_yok = tr("Yok (sadece genel istatistik)")
    modul_auto = tr("🤖 Otomatik Model Eğitimi & Açıklama (Genel)")
    modul_attrition = tr("📉 Çalışan Kaybı Tahmini")
    modul_performance = tr("🏆 Performans Analizi")
    modul_salary = tr("💰 Maaş & Kariyer Analizi")
    modul_action = tr("🎯 Aksiyon Merkezi")

    options = [modul_yok, modul_auto]
    if has_hr_schema and bundle is not None:
        options += [modul_attrition, modul_performance, modul_salary, modul_action]
    elif not has_hr_schema:
        st.caption(tr(
            "İK'ya özgü modüller yalnızca beklenen İK şemasına sahip bir veri setinde kullanılabilir."
        ))
    elif bundle is None:
        st.caption(tr("Eğitilmiş çalışan kaybı modeli bulunamadı; önce `python src/model.py` çalıştırın."))

    default_index = 0
    if has_hr_schema and bundle is not None and modul_attrition in options:
        default_index = options.index(modul_attrition)

    secim = st.selectbox(tr("Modül Seç"), options, index=default_index, key="ds_module_select")

    if secim == modul_auto:
        auto_model_module.render(df, state_prefix="ds")
    elif secim == modul_attrition:
        attrition.render(df, bundle["pipeline"], explainer)
    elif secim == modul_performance:
        performance.render(df)
    elif secim == modul_salary:
        salary_career.render(df)
    elif secim == modul_action:
        action_center.render(df, bundle["pipeline"], explainer)
