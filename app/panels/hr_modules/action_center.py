"""Aksiyon Merkezi alt modülü."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from actions import suggest_actions
from export_utils import build_pdf, to_json_bytes
from i18n import t
from model import CATEGORICAL_FEATURES, NUMERIC_FEATURES, apply_scenario, explain_batch, explain_instance
from theme import STATUS, apply_layout


def render(emp: pd.DataFrame, pipeline, explainer):
    X_all = emp[CATEGORICAL_FEATURES + NUMERIC_FEATURES]
    emp = emp.copy()
    with st.spinner(t("attr_spinner")):
        emp["RiskSkoru"] = pipeline.predict_proba(X_all)[:, 1]

    tab1, tab2, tab3 = st.tabs([t("ac_ilgi_sekme"), t("ac_senaryo_sekme"), t("ac_tekil_sekme")])

    with tab1:
        st.subheader(t("ac_risk_esigi"))
        threshold = st.slider(t("ac_esik_slider"), 0, 100, 50, step=5, key="ac_threshold") / 100
        at_risk = emp[emp["RiskSkoru"] >= threshold].sort_values("RiskSkoru", ascending=False)
        st.caption(t("ac_esik_caption", n=len(at_risk)))

        rows_df = None
        if at_risk.empty:
            st.info(t("ac_esik_bos"))
        elif explainer is None:
            rows_df = at_risk[["CalisanID", "Departman", "Pozisyon", "RiskSkoru"]]
            with st.container(border=True):
                st.dataframe(rows_df.style.format({"RiskSkoru": "{:.1%}"}), width="stretch", hide_index=True)
        else:
            display_n = min(len(at_risk), 30)
            subset = at_risk.head(display_n)
            with st.spinner(t("ac_aksiyon_spinner", n=display_n)):
                contrib_df = explain_batch(pipeline, explainer, subset[CATEGORICAL_FEATURES + NUMERIC_FEATURES])

            rows = []
            for idx in subset.index:
                suggestions = suggest_actions(contrib_df.loc[idx])
                rows.append({
                    "CalisanID": subset.loc[idx, "CalisanID"],
                    "Departman": subset.loc[idx, "Departman"],
                    "Pozisyon": subset.loc[idx, "Pozisyon"],
                    "RiskSkoru": subset.loc[idx, "RiskSkoru"],
                    "Önerilen Aksiyonlar": " • ".join(suggestions) if suggestions else t("ac_aksiyon_yok_str"),
                })
            rows_df = pd.DataFrame(rows)
            with st.container(border=True):
                st.dataframe(rows_df.style.format({"RiskSkoru": "{:.1%}"}), width="stretch", hide_index=True)
                if len(at_risk) > display_n:
                    st.caption(t("ac_performans_kap", display_n=display_n, total=len(at_risk)))

        if rows_df is not None:
            st.markdown(t("dis_aktar"))
            c1, c2 = st.columns(2)
            with c1:
                st.download_button(
                    t("json_indir"), data=to_json_bytes(rows_df.to_dict(orient="records")),
                    file_name="ilgi_gerektiren_calisanlar.json", mime="application/json", key="ac_json1",
                )
            with c2:
                pdf_bytes = build_pdf("İlgi Gerektiren Çalışanlar Raporu", [
                    {"heading": f"Risk Eşiği: %{threshold*100:.0f}", "type": "table", "content": (
                        list(rows_df.columns), rows_df.astype(str).values.tolist()[:40],
                    )},
                ])
                st.download_button(
                    t("pdf_indir"), data=pdf_bytes,
                    file_name="ilgi_gerektiren_calisanlar.pdf", mime="application/pdf", key="ac_pdf1",
                )

    with tab2:
        st.subheader(t("ac_toplu_baslik"))
        st.caption(t("ac_toplu_caption"))

        c1, c2 = st.columns(2)
        en_riskli_n = t("ac_en_riskli_n")
        dept_gore = t("ac_dept_gore")
        with c1:
            group_choice = st.radio(t("ac_hedef_grup"), [en_riskli_n, dept_gore], horizontal=True, key="ac_group_choice")
            if group_choice == en_riskli_n:
                n = st.slider(t("ac_calisan_sayisi"), 5, 100, 20, step=5, key="ac_n")
                group = emp.sort_values("RiskSkoru", ascending=False).head(n)
            else:
                dept = st.selectbox(t("ac_departman"), emp["Departman"].unique(), key="ac_dept")
                group = emp[emp["Departman"] == dept]
        with c2:
            zam = st.slider(t("ac_maas_zammi"), 0, 30, 10, step=5, key="ac_zam")
            mesai_kaldir = st.checkbox(t("ac_mesai_kaldir"), value=True, key="ac_ot")
            wlb_iyilestir = st.checkbox(t("ac_wlb_artir"), value=False, key="ac_wlb")

        X_group = group[CATEGORICAL_FEATURES + NUMERIC_FEATURES]
        before = pipeline.predict_proba(X_group)[:, 1]
        X_after = apply_scenario(X_group, salary_increase_pct=zam, remove_overtime=mesai_kaldir, improve_wlb=wlb_iyilestir)
        after = pipeline.predict_proba(X_after)[:, 1]

        with st.container(border=True):
            m1, m2, m3 = st.columns(3)
            m1.metric(t("ac_risk_once"), f"{before.mean():.1%}")
            m2.metric(t("ac_risk_sonra"), f"{after.mean():.1%}", delta=f"{(after.mean() - before.mean()):+.1%}", delta_color="inverse")
            m3.metric(t("ac_yuksek_riskten_cikan"), int(((before >= 0.5) & (after < 0.5)).sum()))

            fig = go.Figure()
            fig.add_trace(go.Bar(name="Önce", x=["Grup Ortalaması"], y=[before.mean() * 100], marker_color=STATUS["critical"]))
            fig.add_trace(go.Bar(name="Sonra", x=["Grup Ortalaması"], y=[after.mean() * 100], marker_color=STATUS["good"]))
            apply_layout(fig, yaxis_title="Risk (%)")
            st.plotly_chart(fig, width="stretch", theme=None)

        st.markdown(t("dis_aktar"))
        scenario_result = {
            "hedef_grup": group_choice,
            "grup_buyuklugu": len(group),
            "maas_zammi_yuzde": zam,
            "fazla_mesai_kaldirildi": mesai_kaldir,
            "wlb_iyilestirildi": wlb_iyilestir,
            "ortalama_risk_once": float(before.mean()),
            "ortalama_risk_sonra": float(after.mean()),
            "yuksek_riskten_cikan_kisi_sayisi": int(((before >= 0.5) & (after < 0.5)).sum()),
        }
        c1, c2 = st.columns(2)
        with c1:
            st.download_button(
                t("json_indir"), data=to_json_bytes(scenario_result),
                file_name="toplu_senaryo_sonucu.json", mime="application/json", key="ac_json2",
            )
        with c2:
            pdf_bytes = build_pdf("Toplu Müdahale Senaryosu Raporu", [
                {"heading": "Senaryo", "type": "table", "content": (["Alan", "Değer"], list(scenario_result.items()))},
            ])
            st.download_button(
                t("pdf_indir"), data=pdf_bytes,
                file_name="toplu_senaryo_raporu.pdf", mime="application/pdf", key="ac_pdf2",
            )

    with tab3:
        st.subheader(t("ac_tekil_baslik"))
        riskli_idler = emp.sort_values("RiskSkoru", ascending=False)["CalisanID"].head(50)
        secili_id = st.selectbox(t("ac_calisan_sec"), riskli_idler, key="ac_secili_id")
        row = emp[emp["CalisanID"] == secili_id].iloc[[0]]
        X_row = row[CATEGORICAL_FEATURES + NUMERIC_FEATURES]
        current_risk = pipeline.predict_proba(X_row)[0, 1]

        with st.container(border=True):
            st.metric(t("ac_mevcut_risk"), f"{current_risk:.1%}")

            suggestions = []
            if explainer is not None:
                contrib = explain_instance(pipeline, explainer, X_row)
                suggestions = suggest_actions(contrib)
                if suggestions:
                    st.markdown(t("ac_onerilen_aksiyonlar"))
                    for s in suggestions:
                        st.markdown(f"- {s}")
                else:
                    st.info(t("ac_aksiyon_yok"))

        st.markdown("---")
        st.markdown(t("ac_simulasyon_et"))
        c1, c2, c3 = st.columns(3)
        with c1:
            zam2 = st.slider(t("ac_maas_zammi"), 0, 30, 0, step=5, key="ac_single_zam")
        with c2:
            mesai_kaldir2 = st.checkbox(t("ac_mesai_kaldir"), key="ac_single_ot")
        with c3:
            wlb2 = st.checkbox(t("ac_wlb_artir"), key="ac_single_wlb")

        X_after2 = apply_scenario(X_row, salary_increase_pct=zam2, remove_overtime=mesai_kaldir2, improve_wlb=wlb2)
        new_risk = pipeline.predict_proba(X_after2)[0, 1]

        with st.container(border=True):
            st.metric(
                t("ac_simulasyon_risk"), f"{new_risk:.1%}",
                delta=f"{(new_risk - current_risk):+.1%}", delta_color="inverse",
            )

        st.markdown(t("dis_aktar"))
        single_result = {
            "calisan_id": str(secili_id),
            "mevcut_risk_skoru": float(current_risk),
            "onerilen_aksiyonlar": suggestions,
            "simulasyon_sonrasi_risk_skoru": float(new_risk),
        }
        c1, c2 = st.columns(2)
        with c1:
            st.download_button(
                t("json_indir"), data=to_json_bytes(single_result),
                file_name=f"calisan_{secili_id}_senaryo.json", mime="application/json", key="ac_json3",
            )
        with c2:
            pdf_bytes = build_pdf(f"Çalışan {secili_id} — Müdahale Senaryosu Raporu", [
                {"heading": "Mevcut Durum", "type": "paragraph", "content": f"Mevcut risk skoru: %{current_risk*100:.1f}"},
                {"heading": "Önerilen Aksiyonlar", "type": "bullets", "content": suggestions or [t("ac_aksiyon_yok_str")]},
                {"heading": "Simülasyon Sonucu", "type": "paragraph", "content": f"Simülasyon sonrası risk skoru: %{new_risk*100:.1f}"},
            ])
            st.download_button(
                t("pdf_indir"), data=pdf_bytes,
                file_name=f"calisan_{secili_id}_raporu.pdf", mime="application/pdf", key="ac_pdf3",
            )
