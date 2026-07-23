"""CV Analizi paneli — CV yükleme, bilgi çıkarımı, güçlü/zayıf yön özeti, pozisyon önerisi."""
import re

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from cv_analysis import (
    analyze_cv,
    ats_compatibility,
    detect_inconsistency,
    extract_text,
    find_duplicate_candidate,
    general_score,
    hire_likelihood,
    match_cv_to_job,
    match_multiple_jobs,
    skill_development_tips,
)
from export_utils import build_pdf, to_json_bytes
from translator import tr, trf
from theme import CATEGORICAL, STATUS, apply_layout, risk_status

ORNEK_CV_METNI = (
    "Ayşe Demir\n"
    "E-posta: ayse.demir@example.com | Telefon: 0532 111 22 33\n\n"
    "Deneyim\n"
    "6 yıllık iş deneyimim boyunca veri analizi ve raporlama projelerinde çalıştım.\n"
    "Python, SQL, Power BI ve Tableau kullanarak veri görselleştirme ve makine öğrenmesi "
    "projeleri yürüttüm. Bir projede %25 verimlilik artışı sağladım.\n\n"
    "Eğitim\n"
    "Yüksek Lisans, Bilgisayar Mühendisliği — Boğaziçi Üniversitesi\n\n"
    "Beceriler\n"
    "Python, SQL, Power BI, Tableau, makine öğrenmesi, veri analizi, istatistik, "
    "iletişim becerileri, takım çalışması\n\n"
    "İngilizce biliyorum. Veri Bilimi sertifikası almış bulunuyorum."
)


def _friendly_read_error(exc: Exception) -> str:
    """Dosya okuma hatalarını ham exception yerine kısa, yönlendirici bir mesaja çevirir."""
    return (
        "Dosya okunamadı. Dosyanın bozuk olmadığından, şifreli/parola korumalı olmadığından "
        "ve gerçekten seçilen formatta (PDF/DOCX/TXT) olduğundan emin olun. "
        f"(Teknik detay: {exc})"
    )


def render():
    mod = st.radio(
        tr("Mod"),
        [tr("📄 Tek CV Analizi"), tr("📊 Çoklu CV Karşılaştırma"), tr("🆓 ATS & Derin Analiz")],
        horizontal=True, key="cv_mode",
    )
    st.divider()
    if mod == tr("📄 Tek CV Analizi"):
        _render_single_cv()
    elif mod == tr("📊 Çoklu CV Karşılaştırma"):
        _render_compare_cvs()
    else:
        _render_deep_analysis()


def _render_single_cv():
    st.subheader(tr("CV Yükle"))
    st.caption(tr("PDF, DOCX veya TXT formatında bir CV yükleyin. Analiz anahtar kelime tabanlı sezgisel bir yöntemle yapılır; harici bir dil modeli API'sine bağımlı değildir."))
    c1, c2 = st.columns([3, 1])
    with c1:
        cv_file = st.file_uploader(tr("CV dosyası"), type=["pdf", "docx", "txt"], key="cv_upload")
    with c2:
        st.write("")
        st.write("")
        ornek_clicked = st.button(tr("🔎 Örnek Dene"), key="cv_example_btn", width="stretch")

    if ornek_clicked:
        st.session_state["cv_text"] = ORNEK_CV_METNI
        st.session_state["cv_name"] = "ornek_cv.txt"

    if cv_file is not None:
        try:
            with st.spinner(tr("CV metni çıkarılıyor...")):
                text = extract_text(cv_file)
            if not text.strip():
                st.warning(tr("Dosyadan metin çıkarılamadı (taranmış görsel PDF olabilir)."))
            else:
                st.session_state["cv_text"] = text
                st.session_state["cv_name"] = cv_file.name
        except Exception as exc:
            st.error(_friendly_read_error(exc))

    if "cv_text" not in st.session_state:
        st.info(tr("Devam etmek için bir CV dosyası yükleyin veya 'Örnek Dene' ile hemen deneyin."))
        return

    result = analyze_cv(st.session_state["cv_text"])
    file_name = st.session_state["cv_name"]
    if result.get("name"):
        st.success(trf("Analiz edilen aday: **{name}** ({file_name})", name=result['name'], file_name=file_name))
    else:
        st.success(trf("Analiz edilen dosya: **{file_name}**", file_name=file_name))

    with st.container(border=True):
        c1, c2, c3 = st.columns(3)
        c1.metric(tr("Tahmini Deneyim"), trf("{years} yıl", years=result['experience_years']) if result["experience_years"] else "—")
        c2.metric(tr("Eğitim Düzeyi"), result["education"] or "—")
        c3.metric(tr("Tespit Edilen Beceri Sayısı"), len(result["all_skills"]))

        st.markdown(tr("**İletişim Bilgileri**"))
        not_det = tr("Tespit edilemedi")
        st.write(f"{tr('E-posta')}: {result['contact']['email'] or not_det} | {tr('Telefon')}: {result['contact']['phone'] or not_det}")

    st.markdown(tr("### Tespit Edilen Beceriler"))
    skill_rows = []
    if result["skills"]:
        skill_rows = [{"Alan": g, "Beceriler": ", ".join(kws), "Adet": len(kws)} for g, kws in result["skills"].items()]
        skill_df = pd.DataFrame(skill_rows).sort_values("Adet", ascending=False)
        st.dataframe(skill_df, width="stretch", hide_index=True)
        fig = px.bar(skill_df.sort_values("Adet"), x="Adet", y="Alan", orientation="h", color_discrete_sequence=[CATEGORICAL[0]])
        apply_layout(fig, showlegend=False)
        st.plotly_chart(fig, width="stretch", theme=None)
    else:
        st.info(tr("Beceri anahtar kelimesi tespit edilemedi."))

    left, right = st.columns(2)
    with left:
        st.markdown(tr("### 💪 Güçlü Yönler"))
        for s in result["strengths"]:
            st.markdown(f"- {tr(s)}")
    with right:
        st.markdown(tr("### 🔧 Gelişime Açık Yönler"))
        for w in result["weaknesses"]:
            st.markdown(f"- {tr(w)}")

    likelihood = hire_likelihood(result, None)
    likelihood_status = risk_status(1 - likelihood / 100)
    if likelihood_status in ("serious", "critical") and result["improvement_tips"]:
        with st.container(border=True):
            st.markdown(tr("### 📝 CV'nizi Güçlendirmek İçin Öneriler"))
            st.caption(trf(
                "Tahmini işe uygunluk olasılığı %{val} — beklenenin altında görünüyor. "
                "Aşağıdaki noktalar CV'nizi güçlendirmenize yardımcı olabilir.",
                val=likelihood,
            ))
            for tip in result["improvement_tips"]:
                st.markdown(f"- {tr(tip)}")

    st.markdown(tr("### 🎯 Uygun Pozisyon Önerileri"))
    if result["position_suggestions"]:
        st.dataframe(pd.DataFrame(result["position_suggestions"]), width="stretch", hide_index=True)
    else:
        st.info(tr("Yeterli beceri anahtar kelimesi bulunamadığı için pozisyon önerisi üretilemedi."))

    st.markdown(tr("### 🎯 İlana Göre Eşleştirme"))
    st.caption(tr("Bir iş ilanı metni yapıştırın; CV'deki beceriler ilanla karşılaştırılıp uygunluk yüzdesi hesaplanır."))
    job_text = st.text_area(tr("İş ilanı metni"), height=150, key="cv_job_text")

    match = None
    if job_text.strip():
        match = match_cv_to_job(st.session_state["cv_text"], job_text)
        if match["match_pct"] is None:
            st.warning(tr("İlan metninde tanınan beceri anahtar kelimesi bulunamadı."))
        elif match["match_pct"] == 0:
            st.warning(tr("Uygun aday bulunamadı."))
        else:
            with st.container(border=True):
                status = risk_status(1 - match["match_pct"] / 100)
                c1, c2, c3 = st.columns(3)
                c1.metric(tr("Uygunluk Skoru"), f"%{match['match_pct']}")
                c2.metric(tr("Eşleşen Beceri"), len(match["matched_skills"]))
                c3.metric(tr("Eksik Beceri"), len(match["missing_skills"]))

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
                    st.markdown(tr("**✅ Eşleşen Beceriler**"))
                    st.write(", ".join(match["matched_skills"]) if match["matched_skills"] else "—")
                with right:
                    st.markdown(tr("**❌ Eksik Beceriler**"))
                    st.write(", ".join(match["missing_skills"]) if match["missing_skills"] else "—")

                if match["missing_skills"]:
                    st.markdown(tr("**📚 Gelişim Önerileri**"))
                    for tip in skill_development_tips(match["missing_skills"]):
                        st.markdown(f"- {tr(tip)}")

                if match["required_experience"] is not None:
                    if match["candidate_experience"] is not None:
                        durum = tr("✅ Karşılıyor") if match["experience_met"] else tr("⚠️ Karşılamıyor")
                        st.caption(trf(
                            "Deneyim: ilan {required} yıl istiyor, aday ~{candidate} yıl — {durum}",
                            required=match['required_experience'], candidate=match['candidate_experience'], durum=durum,
                        ))
                    else:
                        st.caption(trf("Deneyim: ilan {required} yıl istiyor, adayın deneyimi CV'de net değil.", required=match['required_experience']))

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
                    tr("JSON indir"), data=to_json_bytes(match),
                    file_name=f"{file_name}_ilan_eslesme.json", mime="application/json", key="cv_match_json",
                )
            with c2:
                match_blocks = [
                    {"heading": "Uygunluk Skoru", "type": "paragraph", "content": f"%{match['match_pct']}"},
                    {"heading": "Eşleşen Beceriler", "type": "bullets", "content": match["matched_skills"] or ["—"]},
                    {"heading": "Eksik Beceriler", "type": "bullets", "content": match["missing_skills"] or ["—"]},
                ]
                if match["missing_skills"]:
                    match_blocks.append({
                        "heading": "Gelişim Önerileri", "type": "bullets",
                        "content": skill_development_tips(match["missing_skills"]),
                    })
                pdf_bytes = build_pdf(f"İlan Eşleştirme Raporu — {file_name}", match_blocks)
                st.download_button(
                    tr("PDF indir"), data=pdf_bytes,
                    file_name=f"{file_name}_ilan_eslesme.pdf", mime="application/pdf", key="cv_match_pdf",
                )
    else:
        st.info(tr("Eşleştirme sonucu görmek için yukarıya bir ilan metni yapıştırın."))

    st.markdown(tr("### Dışa Aktar"))
    c1, c2 = st.columns(2)
    with c1:
        st.download_button(
            tr("JSON indir"), data=to_json_bytes({"dosya": file_name, **result}),
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
        if result["improvement_tips"]:
            blocks.append({"heading": "CV'nizi Güçlendirmek İçin Öneriler", "type": "bullets", "content": result["improvement_tips"]})
        if result["position_suggestions"]:
            blocks.append({"heading": "Uygun Pozisyon Önerileri", "type": "table", "content": (
                ["Pozisyon", "Uygunluk Skoru", "Eşleşen Beceriler"],
                [[p["Pozisyon"], p["Uygunluk Skoru"], p["Eşleşen Beceriler"]] for p in result["position_suggestions"]],
            )})
        pdf_bytes = build_pdf(f"CV Analiz Raporu — {file_name}", blocks)
        st.download_button(
            tr("PDF indir"), data=pdf_bytes,
            file_name=f"{file_name}_analiz.pdf", mime="application/pdf", key="cv_pdf",
        )

    st.caption(tr("Not: Bu analiz anahtar kelime tabanlı sezgisel bir yöntemle üretilmiştir; bir ön değerlendirme olarak kullanılmalı, nihai karar için insan incelemesi yapılmalıdır."))


def _render_compare_cvs():
    st.subheader(tr("Birden Fazla CV Yükle ve Karşılaştır"))
    st.caption(tr("PDF, DOCX veya TXT formatında birden fazla CV yükleyin. Aşağıya bir iş ilanı metni yapıştırırsanız adaylar o ilana uygunluk yüzdesine göre; yapıştırmazsanız beceri sayısı, deneyim ve eğitim düzeyinden oluşan genel bir güç skoruna göre sıralanır."))
    files = st.file_uploader(
        tr("CV dosyaları"), type=["pdf", "docx", "txt"], accept_multiple_files=True, key="cv_compare_upload",
    )
    job_text = st.text_area(tr("İş ilanı metni (opsiyonel)"), height=120, key="cv_compare_job_text")

    if not files:
        st.info(tr("Devam etmek için en az iki CV dosyası yükleyin."))
        return

    candidates = []
    with st.spinner(f"{len(files)} CV işleniyor..."):
        for f in files:
            try:
                text = extract_text(f)
            except Exception:
                st.warning(trf("**{name}** okunamadı: dosya bozuk olabilir veya beklenmeyen bir formatta.", name=f.name))
                continue
            if not text.strip():
                st.warning(trf("**{name}** dosyasından metin çıkarılamadı (taranmış görsel PDF olabilir).", name=f.name))
                continue

            result = analyze_cv(text)
            match = match_cv_to_job(text, job_text) if job_text.strip() else None
            candidates.append({"dosya": f.name, "text": text, "result": result, "match": match})

    if not candidates:
        st.warning(tr("Hiçbir dosyadan geçerli metin çıkarılamadı."))
        return

    has_job = job_text.strip() != "" and any(c["match"] is not None for c in candidates)
    if job_text.strip() and not has_job:
        st.warning(tr("İlan metninde tanınan beceri anahtar kelimesi bulunamadı; genel skora göre sıralanıyor."))

    sort_key_label = "Uygunluk %" if has_job else "Genel Skor"
    sort_key_display = tr(sort_key_label)
    rows = []
    for c in candidates:
        r = c["result"]
        m = c["match"]
        row = {
            "Dosya": c["dosya"],
            "Aday": r.get("name") or "—",
            "Deneyim (yıl)": r["experience_years"] if r["experience_years"] else "—",
            "Eğitim": r["education"] or "—",
            "Beceri Sayısı": len(r["all_skills"]),
            "Genel Skor": general_score(r),
            "Tahmini İşe Uygunluk Olasılığı (%)": hire_likelihood(r, m),
        }
        if has_job:
            row["Uygunluk %"] = m["match_pct"] if m and m["match_pct"] is not None else 0
            row["Eşleşen Beceri"] = len(m["matched_skills"]) if m else 0
            row["Eksik Beceri"] = len(m["missing_skills"]) if m else 0
        rows.append(row)

    # Sıralama YALNIZCA uygunluk puanına (sort_key_label) göre yapılır; ikincil bir
    # kıstas (ör. Genel Skor) eklenmez ve kind="mergesort" ile stabil tutulur ki aynı
    # puana sahip adayların göreli sırası (yükleme sırası) korunsun.
    comparison_df = pd.DataFrame(rows).sort_values(
        sort_key_label, ascending=False, kind="mergesort",
    ).reset_index(drop=True)

    top = comparison_df.iloc[0]
    top_score = top[sort_key_label]
    tied_files = comparison_df.loc[comparison_df[sort_key_label] == top_score, "Dosya"].tolist()
    no_suitable_candidate = top_score == 0
    all_tied = len(tied_files) == len(comparison_df)

    explanation_lines = []
    if no_suitable_candidate:
        st.warning(tr("Uygun aday bulunamadı."))
        explanation_lines.append(trf(
            "Hiçbir adayın {label} puanı %0'ın üzerinde değil; bu nedenle bir aday önerilmiyor.",
            label=sort_key_display,
        ))
    elif all_tied:
        st.info(trf(
            "⚖️ Eşit Uygunluk: Tüm adaylar aynı {label} puanına sahip (**{score}**) — {files}.",
            label=sort_key_display, score=top_score, files=', '.join(tied_files),
        ))
        explanation_lines.append(trf(
            "Tüm adaylar ({files}) aynı {label} puanına ({score}) sahip "
            "olduğu için aralarında bir öncelik sıralaması yapılmadı.",
            files=', '.join(tied_files), label=sort_key_display, score=top_score,
        ))
    else:
        top_candidate = next(c for c in candidates if c["dosya"] == top["Dosya"])
        top_r = top_candidate["result"]
        top_m = top_candidate["match"]
        top_likelihood = hire_likelihood(top_r, top_m)

        if has_job:
            explanation_lines.append(trf(
                "**{dosya}**, girilen ilana göre adaylar arasındaki en yüksek beceri "
                "örtüşme yüzdesine (**%{pct}**, {matched} eşleşen / "
                "{missing} eksik beceri) sahip olduğu için 1. sırada seçildi.",
                dosya=top['Dosya'], pct=top_m['match_pct'],
                matched=len(top_m['matched_skills']), missing=len(top_m['missing_skills']),
            ))
            if top_m.get("experience_met") is True:
                explanation_lines.append(trf(
                    "Deneyim şartını karşılıyor (ilan {required} yıl istiyor, adayın ~{candidate} yıl deneyimi var).",
                    required=top_m['required_experience'], candidate=top_m['candidate_experience'],
                ))
            elif top_m.get("experience_met") is False:
                explanation_lines.append(trf(
                    "Deneyim şartını tam karşılamıyor (ilan {required} yıl istiyor, adayın ~{candidate} yıl deneyimi var) ama beceri örtüşmesi öne çıkardı.",
                    required=top_m['required_experience'], candidate=top_m['candidate_experience'],
                ))
        else:
            deneyim_str = trf("{years} yıl deneyim", years=top_r['experience_years']) if top_r["experience_years"] else tr("belirsiz deneyim")
            egitim_str = top_r['education'] or tr('belirsiz eğitim düzeyi')
            explanation_lines.append(trf(
                "İlan metni girilmediği için adaylar **genel güç skoruna** göre sıralandı; bu skor "
                "beceri sayısı + (üst sınırlı) deneyim yılı + eğitim düzeyi ağırlığından oluşuyor. "
                "**{dosya}** en yüksek skora (**{score}**) sahip: "
                "{skill_count} beceri, {deneyim}, {egitim}.",
                dosya=top['Dosya'], score=general_score(top_r),
                skill_count=len(top_r['all_skills']), deneyim=deneyim_str, egitim=egitim_str,
            ))
        explanation_lines.append(trf("Tahmini işe uygunluk olasılığı: **%{val}**.", val=top_likelihood))
        if top_r["position_suggestions"]:
            best_pos = top_r["position_suggestions"][0]
            explanation_lines.append(trf(
                "En çok öne çıkan tahmini pozisyon: **{pozisyon}** (uygunluk skoru: {skor}).",
                pozisyon=best_pos['Pozisyon'], skor=best_pos['Uygunluk Skoru'],
            ))

        top_label = f"{top['Aday']} ({top['Dosya']})" if top["Aday"] != "—" else top["Dosya"]
        st.success(trf(
            "🏆 En uygun aday: **{top_label}** — {label}: {score}",
            top_label=top_label, label=sort_key_display, score=top[sort_key_label],
        ))

    with st.container(border=True):
        format_map = {"Uygunluk %": "{:.0f}", "Tahmini İşe Uygunluk Olasılığı (%)": "{:.0f}"}
        st.dataframe(
            comparison_df.style.format(format_map), width="stretch", hide_index=True,
        )

        chart_df = comparison_df.sort_values(sort_key_label)
        fig = px.bar(
            chart_df, x=sort_key_label, y="Dosya", orientation="h",
            color_discrete_sequence=[CATEGORICAL[0]],
        )
        apply_layout(fig, showlegend=False)
        st.plotly_chart(fig, width="stretch", theme=None)

    st.markdown(tr("### Aday Detayları"))
    for c in candidates:
        r = c["result"]
        expander_label = f"{r['name']} ({c['dosya']})" if r.get("name") else c["dosya"]
        with st.expander(expander_label):
            candidate_likelihood = hire_likelihood(r, c['match'])
            c1, c2, c3, c4 = st.columns(4)
            c1.metric(tr("Tahmini Deneyim"), trf("{years} yıl", years=r['experience_years']) if r["experience_years"] else "—")
            c2.metric(tr("Eğitim Düzeyi"), r["education"] or "—")
            c3.metric(tr("Genel Skor"), general_score(r))
            c4.metric(tr("Tahmini İşe Uygunluk Olasılığı"), f"%{candidate_likelihood}")

            st.markdown(tr("**🎯 Tahmin Edilen En Uygun Pozisyonlar**"))
            if r["position_suggestions"]:
                for p in r["position_suggestions"][:3]:
                    st.markdown(f"- **{p['Pozisyon']}** ({tr('uygunluk skoru')}: {p['Uygunluk Skoru']}) — {p['Eşleşen Beceriler']}")
            else:
                st.caption(tr("Yeterli beceri anahtar kelimesi bulunamadığı için pozisyon önerisi üretilemedi."))

            left, right = st.columns(2)
            with left:
                st.markdown(tr("### 💪 Güçlü Yönler"))
                for s in r["strengths"]:
                    st.markdown(f"- {tr(s)}")
            with right:
                st.markdown(tr("### 🔧 Gelişime Açık Yönler"))
                for w in r["weaknesses"]:
                    st.markdown(f"- {tr(w)}")

            candidate_likelihood_status = risk_status(1 - candidate_likelihood / 100)
            if candidate_likelihood_status in ("serious", "critical") and r["improvement_tips"]:
                st.markdown(tr("### 📝 Geliştirme Önerileri"))
                for tip in r["improvement_tips"]:
                    st.markdown(f"- {tr(tip)}")

            if c["match"] is not None and c["match"]["match_pct"] is not None:
                m = c["match"]
                status = risk_status(1 - m["match_pct"] / 100)
                st.markdown(f"**{tr('İlana Uygunluk')}:** :{'green' if status=='good' else 'orange' if status in ('warning','serious') else 'red'}[%{m['match_pct']}]")
                mleft, mright = st.columns(2)
                with mleft:
                    st.markdown(tr("**✅ Eşleşen Beceriler**"))
                    st.write(", ".join(m["matched_skills"]) if m["matched_skills"] else "—")
                with mright:
                    st.markdown(tr("**❌ Eksik Beceriler**"))
                    st.write(", ".join(m["missing_skills"]) if m["missing_skills"] else "—")

    st.markdown(tr("### Dışa Aktar"))
    if no_suitable_candidate:
        en_uygun_aday_value = None
    elif all_tied:
        en_uygun_aday_value = tied_files
    else:
        en_uygun_aday_value = top["Dosya"]
    export_records = []
    for _, row in comparison_df.iterrows():
        export_records.append(row.to_dict())
    explanation_plain = " ".join(line.replace("**", "") for line in explanation_lines)
    c1, c2 = st.columns(2)
    with c1:
        st.download_button(
            tr("JSON indir"), data=to_json_bytes({
                "siralama_olcutu": sort_key_label,
                "adaylar": export_records,
                "en_uygun_aday": en_uygun_aday_value,
                "secim_gerekcesi": explanation_plain,
            }),
            file_name="cv_karsilastirma.json", mime="application/json", key="cv_compare_json",
        )
    with c2:
        pdf_blocks = [
            {"heading": "Karşılaştırma Tablosu", "type": "table", "content": (
                list(comparison_df.columns), comparison_df.values.tolist(),
            )},
            {"heading": "Sıralama Ölçütü", "type": "paragraph", "content": sort_key_label},
            {"heading": "En Uygun Aday Neden Seçildi?", "type": "paragraph", "content": explanation_plain},
        ]
        pdf_bytes = build_pdf("CV Karşılaştırma Raporu", pdf_blocks)
        st.download_button(
            tr("PDF indir"), data=pdf_bytes,
            file_name="cv_karsilastirma.pdf", mime="application/pdf", key="cv_compare_pdf",
        )

    st.markdown(tr("### 🧭 En Uygun Aday Neden Seçildi?"))
    for line in explanation_lines:
        st.markdown(f"- {line}")

    st.caption(tr("Not: Bu analiz anahtar kelime tabanlı sezgisel bir yöntemle üretilmiştir; bir ön değerlendirme olarak kullanılmalı, nihai karar için insan incelemesi yapılmalıdır."))


def _parse_job_postings(text: str) -> list[str]:
    postings = re.split(r"\n\s*-{3,}\s*\n", text.strip())
    return [p.strip() for p in postings if p.strip()]


def _render_deep_analysis():
    st.subheader(tr("🆓 ATS Uyumu & Derin Analiz"))
    st.caption(tr("ATS uyum skoru, deneyim/unvan tutarsızlığı tespiti, ilan listesine göre gerekçeli eşleştirme ve yinelenen aday kontrolü — tamamen kural tabanlı, **ücretsiz** ve harici hiçbir API'ye bağımlı değil."))

    # Karşılaştırma sekmesindeki dosyalar mevcutsa, metinlerini hemen widget'a bağlı
    # OLMAYAN bir session_state anahtarına anlık görüntü olarak kaydediyoruz: Streamlit,
    # bir script çalışmasında render edilmeyen widget'ların (örn. bu moddayken
    # "cv_compare_upload" file_uploader'ı) session_state değerini birkaç rerun sonra
    # otomatik temizler; bu yüzden ham dosya nesnelerine değil bu anlık görüntüye güveniyoruz.
    compare_files = st.session_state.get("cv_compare_upload") or []
    if compare_files:
        pool = {}
        for f in compare_files:
            try:
                text = extract_text(f)
            except Exception:
                continue
            if text.strip():
                pool[f.name] = text
        if pool:
            st.session_state["cv_deep_candidate_pool"] = pool

    candidate_pool = st.session_state.get("cv_deep_candidate_pool")
    if not candidate_pool:
        st.info(tr("Bu özellik, **📊 Çoklu CV Karşılaştırma** sekmesinde yüklediğiniz CV'leri kullanır. Lütfen önce o sekmede en az bir CV yükleyin."))
        return

    file_names = list(candidate_pool.keys())
    subject_name = st.selectbox(tr("Derin analiz edilecek CV"), file_names, key="cv_deep_subject")
    job_text = st.text_area(
        tr("İş ilanları (birden fazla ilanı '---' ile ayırın, opsiyonel)"), height=180, key="cv_deep_job_postings",
    )

    if not st.button(tr("Analiz Et"), type="primary", key="cv_deep_analyze_btn"):
        return

    subject_text = candidate_pool[subject_name]
    subject_result = analyze_cv(subject_text)
    other_candidates = [
        {"dosya": name, "text": text}
        for name, text in candidate_pool.items() if name != subject_name
    ]
    job_postings = _parse_job_postings(job_text)
    single_match = match_cv_to_job(subject_text, job_postings[0]) if len(job_postings) == 1 else None

    result = {
        "ats_uyum": ats_compatibility(subject_result, subject_text, single_match),
        "tutarsizlik": detect_inconsistency(subject_result, subject_text),
        "ilan_eslestirme": match_multiple_jobs(subject_text, job_postings),
        "yinelenen_aday": find_duplicate_candidate(subject_text, subject_result, other_candidates),
    }

    st.success(trf("Analiz edilen CV: **{name}**", name=subject_name))

    ats = result["ats_uyum"]
    st.markdown(tr("### 1️⃣ ATS Uyum Skoru"))
    with st.container(border=True):
        status = risk_status(1 - ats["skor"] / 100)
        c1, c2 = st.columns([1, 2])
        with c1:
            fig = go.Figure(go.Indicator(
                mode="gauge+number", value=ats["skor"], number={"suffix": "%"},
                gauge={"axis": {"range": [0, 100]}, "bar": {"color": STATUS[status]}},
            ))
            apply_layout(fig, height=220)
            st.plotly_chart(fig, width="stretch", theme=None)
        with c2:
            st.markdown(tr("**Eksik Anahtar Kelimeler**"))
            st.write(", ".join(ats["eksik_anahtar_kelimeler"]) if ats["eksik_anahtar_kelimeler"] else "—")
            st.markdown(tr("**Format Sorunları**"))
            st.write(", ".join(ats["format_sorunlari"]) if ats["format_sorunlari"] else "—")
        st.markdown(tr("**İyileştirme Önerileri**"))
        for oneri in ats["oneriler"][:3]:
            st.markdown(f"- {tr(oneri)}")

    st.markdown(tr("### 2️⃣ Tutarsızlık Analizi"))
    tutarsizlik = result["tutarsizlik"]
    if tutarsizlik["var_mi"]:
        st.warning(tr(tutarsizlik["aciklama"]))
    else:
        st.success(tr(tutarsizlik["aciklama"]) if tutarsizlik["aciklama"] else tr("Tutarlı"))

    st.markdown(tr("### 3️⃣ İlan Eşleştirme"))
    ilanlar = result["ilan_eslestirme"]
    if ilanlar:
        with st.container(border=True):
            ilan_df = pd.DataFrame(ilanlar).rename(columns={
                "ilan_basligi": "İlan", "skor": "Skor", "gerekce": "Gerekçe",
            })
            st.dataframe(ilan_df, width="stretch", hide_index=True)
            fig2 = px.bar(
                ilan_df.sort_values("Skor"), x="Skor", y="İlan", orientation="h",
                color_discrete_sequence=[CATEGORICAL[0]],
            )
            apply_layout(fig2, showlegend=False)
            st.plotly_chart(fig2, width="stretch", theme=None)
    else:
        st.info(tr("İlan listesi girilmedi."))

    st.markdown(tr("### 4️⃣ Yinelenen Aday Kontrolü"))
    yinelenen = result["yinelenen_aday"]
    if yinelenen["bulundu_mu"]:
        st.warning(trf(
            "Olası eşleşme: **{kayit}** (benzerlik: %{benzerlik}). {aciklama}",
            kayit=yinelenen['eslesen_kayit'], benzerlik=yinelenen['benzerlik_orani'],
            aciklama=tr(yinelenen['aciklama']),
        ))
    else:
        st.success(tr(yinelenen["aciklama"]) if yinelenen["aciklama"] else tr("Yinelenen aday bulunamadı."))

    st.markdown(tr("### Dışa Aktar"))
    c1, c2 = st.columns(2)
    with c1:
        st.download_button(
            tr("JSON indir"), data=to_json_bytes({"aday": subject_name, **result}),
            file_name=f"{subject_name}_derin_analiz.json", mime="application/json", key="cv_deep_json",
        )
    with c2:
        pdf_blocks = [
            {"heading": "ATS Uyum Skoru", "type": "paragraph", "content": f"%{ats['skor']}"},
            {"heading": "İyileştirme Önerileri", "type": "bullets", "content": ats["oneriler"] or ["—"]},
            {"heading": "Tutarsızlık Analizi", "type": "paragraph", "content": tutarsizlik["aciklama"]},
            {"heading": "İlan Eşleştirme", "type": "table", "content": (
                ["İlan", "Skor", "Gerekçe"],
                [[i["ilan_basligi"], i["skor"], i["gerekce"]] for i in ilanlar],
            )} if ilanlar else {"heading": "İlan Eşleştirme", "type": "paragraph", "content": "İlan listesi girilmedi."},
            {"heading": "Yinelenen Aday Kontrolü", "type": "paragraph", "content": yinelenen["aciklama"]},
        ]
        pdf_bytes = build_pdf(f"CV Derin Analiz Raporu — {subject_name}", pdf_blocks)
        st.download_button(
            tr("PDF indir"), data=pdf_bytes,
            file_name=f"{subject_name}_derin_analiz.pdf", mime="application/pdf", key="cv_deep_pdf",
        )

    st.caption(tr("Not: Bu analiz anahtar kelime tabanlı sezgisel bir yöntemle üretilmiştir; bir ön değerlendirme olarak kullanılmalı, nihai karar için insan incelemesi yapılmalıdır."))
