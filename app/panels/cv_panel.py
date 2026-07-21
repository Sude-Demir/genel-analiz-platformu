"""CV Analizi paneli — CV yükleme, bilgi çıkarımı, güçlü/zayıf yön özeti, pozisyon önerisi."""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from cv_analysis import analyze_cv, extract_text, match_cv_to_job
from export_utils import build_pdf, to_json_bytes
from theme import CATEGORICAL, STATUS, apply_layout, risk_status


def render():
    st.subheader("CV Yükle")
    st.caption(
        "PDF, DOCX veya TXT formatında bir CV yükleyin. Analiz anahtar kelime tabanlı sezgisel bir "
        "yöntemle yapılır; harici bir dil modeli API'sine bağımlı değildir."
    )
    cv_file = st.file_uploader("CV dosyası", type=["pdf", "docx", "txt"], key="cv_upload")

    if cv_file is not None:
        try:
            text = extract_text(cv_file)
            if not text.strip():
                st.warning("Dosyadan metin çıkarılamadı (taranmış görsel PDF olabilir).")
            else:
                st.session_state["cv_text"] = text
                st.session_state["cv_name"] = cv_file.name
        except Exception as exc:
            st.error(f"Dosya okunamadı: {exc}")

    if "cv_text" not in st.session_state:
        st.info("Devam etmek için bir CV dosyası yükleyin.")
        return

    result = analyze_cv(st.session_state["cv_text"])
    file_name = st.session_state["cv_name"]
    st.success(f"Analiz edilen dosya: **{file_name}**")

    c1, c2, c3 = st.columns(3)
    c1.metric("Tahmini Deneyim", f"{result['experience_years']} yıl" if result["experience_years"] else "—")
    c2.metric("Eğitim Düzeyi", result["education"] or "—")
    c3.metric("Tespit Edilen Beceri Sayısı", len(result["all_skills"]))

    st.markdown("**İletişim Bilgileri**")
    st.write(f"E-posta: {result['contact']['email'] or 'Tespit edilemedi'} | Telefon: {result['contact']['phone'] or 'Tespit edilemedi'}")

    st.markdown("### Tespit Edilen Beceriler")
    skill_rows = []
    if result["skills"]:
        skill_rows = [{"Alan": g, "Beceriler": ", ".join(kws), "Adet": len(kws)} for g, kws in result["skills"].items()]
        skill_df = pd.DataFrame(skill_rows).sort_values("Adet", ascending=False)
        st.dataframe(skill_df, width="stretch", hide_index=True)
        fig = px.bar(skill_df.sort_values("Adet"), x="Adet", y="Alan", orientation="h", color_discrete_sequence=[CATEGORICAL[0]])
        apply_layout(fig, showlegend=False)
        st.plotly_chart(fig, width="stretch", theme=None)
    else:
        st.info("Beceri anahtar kelimesi tespit edilemedi.")

    left, right = st.columns(2)
    with left:
        st.markdown("### 💪 Güçlü Yönler")
        for s in result["strengths"]:
            st.markdown(f"- {s}")
    with right:
        st.markdown("### 🔧 Gelişime Açık Yönler")
        for w in result["weaknesses"]:
            st.markdown(f"- {w}")

    st.markdown("### 🎯 Uygun Pozisyon Önerileri")
    if result["position_suggestions"]:
        st.dataframe(pd.DataFrame(result["position_suggestions"]), width="stretch", hide_index=True)
    else:
        st.info("Yeterli beceri anahtar kelimesi bulunamadığı için pozisyon önerisi üretilemedi.")

    st.markdown("### 🎯 İlana Göre Eşleştirme")
    st.caption("Bir iş ilanı metni yapıştırın; CV'deki beceriler ilanla karşılaştırılıp uygunluk yüzdesi hesaplanır.")
    job_text = st.text_area("İş ilanı metni", height=150, key="cv_job_text")

    match = None
    if job_text.strip():
        match = match_cv_to_job(st.session_state["cv_text"], job_text)
        if match["match_pct"] is None:
            st.warning("İlan metninde tanınan beceri anahtar kelimesi bulunamadı.")
        else:
            status = risk_status(1 - match["match_pct"] / 100)
            c1, c2, c3 = st.columns(3)
            c1.metric("Uygunluk Skoru", f"%{match['match_pct']}")
            c2.metric("Eşleşen Beceri", len(match["matched_skills"]))
            c3.metric("Eksik Beceri", len(match["missing_skills"]))

            fig = go.Figure(go.Indicator(
                mode="gauge+number",
                value=match["match_pct"],
                number={"suffix": "%"},
                gauge={"axis": {"range": [0, 100]}, "bar": {"color": STATUS[status]}},
            ))
            apply_layout(fig)
            st.plotly_chart(fig, width="stretch", theme=None)

            left, right = st.columns(2)
            with left:
                st.markdown("**✅ Eşleşen Beceriler**")
                st.write(", ".join(match["matched_skills"]) if match["matched_skills"] else "—")
            with right:
                st.markdown("**❌ Eksik Beceriler**")
                st.write(", ".join(match["missing_skills"]) if match["missing_skills"] else "—")

            if match["required_experience"] is not None:
                if match["candidate_experience"] is not None:
                    durum = "✅ Karşılıyor" if match["experience_met"] else "⚠️ Karşılamıyor"
                    st.caption(
                        f"Deneyim: ilan {match['required_experience']} yıl istiyor, "
                        f"aday ~{match['candidate_experience']} yıl — {durum}"
                    )
                else:
                    st.caption(f"Deneyim: ilan {match['required_experience']} yıl istiyor, adayın deneyimi CV'de net değil.")

            if match["group_breakdown"]:
                breakdown_df = pd.DataFrame(match["group_breakdown"])
                fig2 = px.bar(
                    breakdown_df, x="İlan Beceri Sayısı", y="Alan", orientation="h",
                    color_discrete_sequence=[CATEGORICAL[0]],
                )
                fig2.add_bar(
                    x=breakdown_df["Eşleşen"], y=breakdown_df["Alan"], orientation="h",
                    name="Eşleşen", marker_color=CATEGORICAL[1],
                )
                apply_layout(fig2, barmode="overlay", showlegend=False)
                st.plotly_chart(fig2, width="stretch", theme=None)

            c1, c2 = st.columns(2)
            with c1:
                st.download_button(
                    "JSON indir", data=to_json_bytes(match),
                    file_name=f"{file_name}_ilan_eslesme.json", mime="application/json", key="cv_match_json",
                )
            with c2:
                match_blocks = [
                    {"heading": "Uygunluk Skoru", "type": "paragraph", "content": f"%{match['match_pct']}"},
                    {"heading": "Eşleşen Beceriler", "type": "bullets", "content": match["matched_skills"] or ["—"]},
                    {"heading": "Eksik Beceriler", "type": "bullets", "content": match["missing_skills"] or ["—"]},
                ]
                pdf_bytes = build_pdf(f"İlan Eşleştirme Raporu — {file_name}", match_blocks)
                st.download_button(
                    "PDF indir", data=pdf_bytes,
                    file_name=f"{file_name}_ilan_eslesme.pdf", mime="application/pdf", key="cv_match_pdf",
                )
    else:
        st.info("Eşleştirme sonucu görmek için yukarıya bir ilan metni yapıştırın.")

    st.markdown("### Dışa Aktar")
    c1, c2 = st.columns(2)
    with c1:
        st.download_button(
            "JSON indir", data=to_json_bytes({"dosya": file_name, **result}),
            file_name=f"{file_name}_analiz.json", mime="application/json", key="cv_json",
        )
    with c2:
        blocks = [
            {"heading": "İletişim Bilgileri", "type": "bullets", "content": [
                f"E-posta: {result['contact']['email'] or 'Tespit edilemedi'}",
                f"Telefon: {result['contact']['phone'] or 'Tespit edilemedi'}",
            ]},
            {"heading": "Genel Bilgiler", "type": "bullets", "content": [
                f"Tahmini deneyim: {result['experience_years'] if result['experience_years'] else 'Belirlenemedi'} yıl",
                f"Eğitim düzeyi: {result['education'] or 'Belirlenemedi'}",
                f"Kelime sayısı: {result['word_count']}",
            ]},
        ]
        if skill_rows:
            blocks.append({"heading": "Tespit Edilen Beceriler", "type": "table", "content": (
                ["Alan", "Beceriler", "Adet"], [[r["Alan"], r["Beceriler"], r["Adet"]] for r in skill_rows],
            )})
        blocks.append({"heading": "Güçlü Yönler", "type": "bullets", "content": result["strengths"]})
        blocks.append({"heading": "Gelişime Açık Yönler", "type": "bullets", "content": result["weaknesses"]})
        if result["position_suggestions"]:
            blocks.append({"heading": "Uygun Pozisyon Önerileri", "type": "table", "content": (
                ["Pozisyon", "Uygunluk Skoru", "Eşleşen Beceriler"],
                [[p["Pozisyon"], p["Uygunluk Skoru"], p["Eşleşen Beceriler"]] for p in result["position_suggestions"]],
            )})
        pdf_bytes = build_pdf(f"CV Analiz Raporu — {file_name}", blocks)
        st.download_button(
            "PDF indir", data=pdf_bytes,
            file_name=f"{file_name}_analiz.pdf", mime="application/pdf", key="cv_pdf",
        )

    st.caption(
        "Not: Bu analiz anahtar kelime tabanlı sezgisel bir yöntemle üretilmiştir; "
        "bir ön değerlendirme olarak kullanılmalı, nihai karar için insan incelemesi yapılmalıdır."
    )
