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
    """Panelin iki bağımsız kısmını sırayla render eder. _render_upload_and_analysis_section()
    içindeki erken "return"lerin (henüz veri yüklenmemişse) _render_compare_section()
    çağrısını engellememesi için ikisi ayrı fonksiyonlarda tutulur."""
    _render_upload_and_analysis_section()
    st.divider()
    _render_compare_section()


def _render_upload_and_analysis_section():
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


def _render_compare_section():
    """Dataset Analizi panelinin içindeki ayrı bir kısım: iki veri setini
    (örn. bu ay ve geçen ay verisi) yan yana karşılaştırır. Yukarıdaki tekil
    veri seti analizinden bağımsız çalışır."""
    st.markdown(tr("## 📊 İki Veri Setini Karşılaştır"))
    st.caption(tr(
        "İki veri seti yükleyin (örn. bu ay ve geçen ay verisi); satır/kolon sayısı, "
        "veri kalitesi ve ortak sayısal kolonların ortalamaları yan yana karşılaştırılır."
    ))

    c1, c2 = st.columns(2)
    with c1:
        upload_a = st.file_uploader(tr("1. Veri Seti"), type=["csv", "xlsx", "xls", "json"], key="ds_compare_upload_a")
    with c2:
        upload_b = st.file_uploader(tr("2. Veri Seti"), type=["csv", "xlsx", "xls", "json"], key="ds_compare_upload_b")

    c3, c4 = st.columns([1, 3])
    with c3:
        ornek_clicked = st.button(tr("🔎 Örnek Dene"), key="ds_compare_example_btn", use_container_width=True)
    with c4:
        compare_clicked = st.button(
            tr("Karşılaştır"), type="primary",
            disabled=not (upload_a and upload_b), key="ds_compare_btn",
        )

    if ornek_clicked:
        if not data_ready():
            st.warning(tr("Dahili İK veri seti bulunamadı. Önce `python src/data_prep.py` çalıştırın."))
        else:
            emp = load_employees()
            yari = len(emp) // 2
            st.session_state["ds_compare_data"] = {
                "a": {"name": tr("İK Verisi — İlk Yarı"), "df": emp.iloc[:yari].reset_index(drop=True)},
                "b": {"name": tr("İK Verisi — İkinci Yarı"), "df": emp.iloc[yari:].reset_index(drop=True)},
            }

    if compare_clicked and upload_a and upload_b:
        try:
            with st.spinner(tr("Veri setleri okunuyor...")):
                df_a = load_uploaded(upload_a)
                df_b = load_uploaded(upload_b)
            st.session_state["ds_compare_data"] = {
                "a": {"name": upload_a.name, "df": df_a},
                "b": {"name": upload_b.name, "df": df_b},
            }
        except Exception as exc:
            st.error(trf("Veri setleri okunamadı. ({hata})", hata=exc))

    if "ds_compare_data" not in st.session_state:
        st.info(tr("Karşılaştırmak için iki veri seti yükleyip 'Karşılaştır' butonuna tıklayın veya 'Örnek Dene' ile hemen deneyin."))
        return

    data = st.session_state["ds_compare_data"]
    a, b = data["a"], data["b"]
    df_a, df_b = a["df"], b["df"]
    name_a, name_b = a["name"], b["name"]

    with st.container(border=True):
        st.markdown(tr("**Genel Karşılaştırma**"))
        cols = st.columns(2)
        for col, name, df in [(cols[0], name_a, df_a), (cols[1], name_b, df_b)]:
            with col:
                st.markdown(f"**{name}**")
                st.metric(tr("Satır Sayısı"), len(df))
                st.metric(tr("Kolon Sayısı"), len(df.columns))

    ortak_kolonlar = sorted(set(df_a.columns) & set(df_b.columns))
    sadece_a = sorted(set(df_a.columns) - set(df_b.columns))
    sadece_b = sorted(set(df_b.columns) - set(df_a.columns))
    if sadece_a or sadece_b:
        with st.expander(tr("Kolon Farklılıkları")):
            if sadece_a:
                st.write(trf("Yalnızca {name}'de olan kolonlar: {cols}", name=name_a, cols=', '.join(sadece_a)))
            if sadece_b:
                st.write(trf("Yalnızca {name}'de olan kolonlar: {cols}", name=name_b, cols=', '.join(sadece_b)))

    quality_a = data_quality_report(df_a)
    quality_b = data_quality_report(df_b)
    with st.container(border=True):
        st.markdown(tr("**Veri Kalitesi Karşılaştırması**"))
        cols = st.columns(2)
        for col, name, df, q in [(cols[0], name_a, df_a, quality_a), (cols[1], name_b, df_b, quality_b)]:
            with col:
                st.markdown(f"**{name}**")
                toplam_hucre = len(df) * len(df.columns)
                eksik_oran = (df.isna().sum().sum() / toplam_hucre * 100) if toplam_hucre else 0
                st.metric(tr("Yinelenen Satır"), q["yinelenen_satir"])
                st.metric(tr("Toplam Eksik Hücre Oranı"), f"%{round(eksik_oran, 1)}")

    numeric_a, _ = infer_column_types(df_a)
    numeric_b, _ = infer_column_types(df_b)
    ortak_sayisal = [c for c in ortak_kolonlar if c in numeric_a and c in numeric_b]

    comp_table = pd.DataFrame()
    if ortak_sayisal:
        with st.container(border=True):
            st.markdown(tr("**Ortak Sayısal Kolonların Ortalama Karşılaştırması**"))
            rows = []
            for col in ortak_sayisal:
                mean_a, mean_b = df_a[col].mean(), df_b[col].mean()
                fark = mean_b - mean_a if pd.notna(mean_a) and pd.notna(mean_b) else None
                fark_yuzde = (fark / mean_a * 100) if fark is not None and mean_a else None
                rows.append({
                    tr("Kolon"): col,
                    trf("Ortalama — {name}", name=name_a): round(mean_a, 2) if pd.notna(mean_a) else None,
                    trf("Ortalama — {name}", name=name_b): round(mean_b, 2) if pd.notna(mean_b) else None,
                    tr("Fark"): round(fark, 2) if fark is not None else None,
                    tr("Fark (%)"): round(fark_yuzde, 1) if fark_yuzde is not None else None,
                })
            comp_table = pd.DataFrame(rows)
            st.dataframe(comp_table, width="stretch", hide_index=True)
    else:
        st.caption(tr("Ortak sayısal kolon bulunamadığı için ortalama karşılaştırması yapılamadı."))

    st.markdown(tr("### Dışa Aktar"))
    c1, c2 = st.columns(2)
    with c1:
        json_payload = {
            "karsilastirma": [
                {"veri_seti": name_a, "satir_sayisi": len(df_a), "kolon_sayisi": len(df_a.columns), "veri_kalitesi": quality_a},
                {"veri_seti": name_b, "satir_sayisi": len(df_b), "kolon_sayisi": len(df_b.columns), "veri_kalitesi": quality_b},
            ],
            "ortak_kolonlar": ortak_kolonlar,
            "yalnizca_a_kolonlar": sadece_a,
            "yalnizca_b_kolonlar": sadece_b,
            "ortak_sayisal_kolon_karsilastirmasi": comp_table.to_dict(orient="records"),
        }
        st.download_button(
            tr("JSON indir"), data=to_json_bytes(json_payload),
            file_name=f"{name_a}_vs_{name_b}_karsilastirma.json", mime="application/json",
            key="ds_compare_json",
        )
    with c2:
        blocks = [
            {"heading": tr("Genel Bilgiler"), "type": "table", "content": (
                [tr("Veri Seti"), tr("Satır Sayısı"), tr("Kolon Sayısı"), tr("Yinelenen Satır")],
                [
                    [name_a, len(df_a), len(df_a.columns), quality_a["yinelenen_satir"]],
                    [name_b, len(df_b), len(df_b.columns), quality_b["yinelenen_satir"]],
                ],
            )},
        ]
        if not comp_table.empty:
            blocks.append({"heading": tr("Ortak Sayısal Kolon Ortalama Karşılaştırması"), "type": "table", "content": (
                list(comp_table.columns), [tuple(row) for row in comp_table.itertuples(index=False)],
            )})
        pdf_bytes = build_pdf(
            trf("Veri Seti Karşılaştırma Raporu — {a} vs {b}", a=name_a, b=name_b), blocks,
        )
        st.download_button(
            tr("PDF indir"), data=pdf_bytes,
            file_name=f"{name_a}_vs_{name_b}_karsilastirma.pdf", mime="application/pdf",
            key="ds_compare_pdf",
        )
