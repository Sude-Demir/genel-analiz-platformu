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
        "Mod", ["📄 Tek CV Analizi", "📊 Çoklu CV Karşılaştırma", "🆓 ATS & Derin Analiz"],
        horizontal=True, key="cv_mode",
    )
    st.divider()
    if mod == "📄 Tek CV Analizi":
        _render_single_cv()
    elif mod == "📊 Çoklu CV Karşılaştırma":
        _render_compare_cvs()
    else:
        _render_deep_analysis()


def _render_single_cv():
    st.subheader("CV Yükle")
    st.caption(
        "PDF, DOCX veya TXT formatında bir CV yükleyin. Analiz anahtar kelime tabanlı sezgisel bir "
        "yöntemle yapılır; harici bir dil modeli API'sine bağımlı değildir."
    )
    c1, c2 = st.columns([3, 1])
    with c1:
        cv_file = st.file_uploader("CV dosyası", type=["pdf", "docx", "txt"], key="cv_upload")
    with c2:
        st.write("")
        st.write("")
        ornek_clicked = st.button("🔎 Örnek Dene", key="cv_example_btn", width="stretch")

    if ornek_clicked:
        st.session_state["cv_text"] = ORNEK_CV_METNI
        st.session_state["cv_name"] = "ornek_cv.txt"

    if cv_file is not None:
        try:
            with st.spinner("CV metni çıkarılıyor..."):
                text = extract_text(cv_file)
            if not text.strip():
                st.warning("Dosyadan metin çıkarılamadı (taranmış görsel PDF olabilir).")
            else:
                st.session_state["cv_text"] = text
                st.session_state["cv_name"] = cv_file.name
        except Exception as exc:
            st.error(_friendly_read_error(exc))

    if "cv_text" not in st.session_state:
        st.info("Devam etmek için bir CV dosyası yükleyin veya 'Örnek Dene' ile hemen deneyin.")
        return

    result = analyze_cv(st.session_state["cv_text"])
    file_name = st.session_state["cv_name"]
    if result.get("name"):
        st.success(f"Analiz edilen aday: **{result['name']}** ({file_name})")
    else:
        st.success(f"Analiz edilen dosya: **{file_name}**")

    with st.container(border=True):
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
            with st.container(border=True):
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

                if match["missing_skills"]:
                    st.markdown("**📚 Gelişim Önerileri**")
                    for tip in skill_development_tips(match["missing_skills"]):
                        st.markdown(f"- {tip}")

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
                if match["missing_skills"]:
                    match_blocks.append({
                        "heading": "Gelişim Önerileri", "type": "bullets",
                        "content": skill_development_tips(match["missing_skills"]),
                    })
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


def _render_compare_cvs():
    st.subheader("Birden Fazla CV Yükle ve Karşılaştır")
    st.caption(
        "PDF, DOCX veya TXT formatında birden fazla CV yükleyin. Aşağıya bir iş ilanı metni "
        "yapıştırırsanız adaylar o ilana uygunluk yüzdesine göre; yapıştırmazsanız beceri sayısı, "
        "deneyim ve eğitim düzeyinden oluşan genel bir güç skoruna göre sıralanır."
    )
    files = st.file_uploader(
        "CV dosyaları", type=["pdf", "docx", "txt"], accept_multiple_files=True, key="cv_compare_upload",
    )
    job_text = st.text_area("İş ilanı metni (opsiyonel)", height=120, key="cv_compare_job_text")

    if not files:
        st.info("Devam etmek için en az iki CV dosyası yükleyin.")
        return

    candidates = []
    with st.spinner(f"{len(files)} CV işleniyor..."):
        for f in files:
            try:
                text = extract_text(f)
            except Exception:
                st.warning(f"**{f.name}** okunamadı: dosya bozuk olabilir veya beklenmeyen bir formatta.")
                continue
            if not text.strip():
                st.warning(f"**{f.name}** dosyasından metin çıkarılamadı (taranmış görsel PDF olabilir).")
                continue

            result = analyze_cv(text)
            match = match_cv_to_job(text, job_text) if job_text.strip() else None
            candidates.append({"dosya": f.name, "text": text, "result": result, "match": match})

    if not candidates:
        st.warning("Hiçbir dosyadan geçerli metin çıkarılamadı.")
        return

    has_job = job_text.strip() != "" and any(c["match"] is not None for c in candidates)
    if job_text.strip() and not has_job:
        st.warning("İlan metninde tanınan beceri anahtar kelimesi bulunamadı; genel skora göre sıralanıyor.")

    sort_key_label = "Uygunluk %" if has_job else "Genel Skor"
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

    comparison_df = pd.DataFrame(rows).sort_values(
        [sort_key_label, "Genel Skor"], ascending=False,
    ).reset_index(drop=True)

    top = comparison_df.iloc[0]
    top_candidate = next(c for c in candidates if c["dosya"] == top["Dosya"])
    top_r = top_candidate["result"]
    top_m = top_candidate["match"]
    top_likelihood = hire_likelihood(top_r, top_m)

    explanation_lines = []
    if has_job:
        explanation_lines.append(
            f"**{top['Dosya']}**, girilen ilana göre adaylar arasındaki en yüksek beceri "
            f"örtüşme yüzdesine (**%{top_m['match_pct']}**, {len(top_m['matched_skills'])} eşleşen / "
            f"{len(top_m['missing_skills'])} eksik beceri) sahip olduğu için 1. sırada seçildi."
        )
        if top_m.get("experience_met") is True:
            explanation_lines.append(f"Deneyim şartını karşılıyor (ilan {top_m['required_experience']} yıl istiyor, adayın ~{top_m['candidate_experience']} yıl deneyimi var).")
        elif top_m.get("experience_met") is False:
            explanation_lines.append(f"Deneyim şartını tam karşılamıyor (ilan {top_m['required_experience']} yıl istiyor, adayın ~{top_m['candidate_experience']} yıl deneyimi var) ama beceri örtüşmesi öne çıkardı.")
    else:
        deneyim_str = f"{top_r['experience_years']} yıl deneyim" if top_r["experience_years"] else "belirsiz deneyim"
        explanation_lines.append(
            f"İlan metni girilmediği için adaylar **genel güç skoruna** göre sıralandı; bu skor "
            f"beceri sayısı + (üst sınırlı) deneyim yılı + eğitim düzeyi ağırlığından oluşuyor. "
            f"**{top['Dosya']}** en yüksek skora (**{general_score(top_r)}**) sahip: "
            f"{len(top_r['all_skills'])} beceri, {deneyim_str}, "
            f"{top_r['education'] or 'belirsiz eğitim düzeyi'}."
        )
    explanation_lines.append(f"Tahmini işe uygunluk olasılığı: **%{top_likelihood}**.")
    if top_r["position_suggestions"]:
        best_pos = top_r["position_suggestions"][0]
        explanation_lines.append(f"En çok öne çıkan tahmini pozisyon: **{best_pos['Pozisyon']}** (uygunluk skoru: {best_pos['Uygunluk Skoru']}).")

    top_label = f"{top['Aday']} ({top['Dosya']})" if top["Aday"] != "—" else top["Dosya"]
    st.success(f"🏆 En uygun aday: **{top_label}** — {sort_key_label}: {top[sort_key_label]}")

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

    st.markdown("### Aday Detayları")
    for c in candidates:
        r = c["result"]
        expander_label = f"{r['name']} ({c['dosya']})" if r.get("name") else c["dosya"]
        with st.expander(expander_label):
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Deneyim", f"{r['experience_years']} yıl" if r["experience_years"] else "—")
            c2.metric("Eğitim Düzeyi", r["education"] or "—")
            c3.metric("Genel Skor", general_score(r))
            c4.metric("Tahmini İşe Uygunluk Olasılığı", f"%{hire_likelihood(r, c['match'])}")

            st.markdown("**🎯 Tahmin Edilen En Uygun Pozisyonlar**")
            if r["position_suggestions"]:
                for p in r["position_suggestions"][:3]:
                    st.markdown(f"- **{p['Pozisyon']}** (uygunluk skoru: {p['Uygunluk Skoru']}) — {p['Eşleşen Beceriler']}")
            else:
                st.caption("Yeterli beceri anahtar kelimesi bulunamadığı için pozisyon tahmini üretilemedi.")

            left, right = st.columns(2)
            with left:
                st.markdown("**💪 Güçlü Yönler**")
                for s in r["strengths"]:
                    st.markdown(f"- {s}")
            with right:
                st.markdown("**🔧 Gelişime Açık Yönler**")
                for w in r["weaknesses"]:
                    st.markdown(f"- {w}")

            if c["match"] is not None and c["match"]["match_pct"] is not None:
                m = c["match"]
                status = risk_status(1 - m["match_pct"] / 100)
                st.markdown(f"**İlana Uygunluk:** :{'green' if status=='good' else 'orange' if status in ('warning','serious') else 'red'}[%{m['match_pct']}]")
                mleft, mright = st.columns(2)
                with mleft:
                    st.markdown("**✅ Eşleşen Beceriler**")
                    st.write(", ".join(m["matched_skills"]) if m["matched_skills"] else "—")
                with mright:
                    st.markdown("**❌ Eksik Beceriler**")
                    st.write(", ".join(m["missing_skills"]) if m["missing_skills"] else "—")

    st.markdown("### Dışa Aktar")
    export_records = []
    for _, row in comparison_df.iterrows():
        export_records.append(row.to_dict())
    explanation_plain = " ".join(line.replace("**", "") for line in explanation_lines)
    c1, c2 = st.columns(2)
    with c1:
        st.download_button(
            "JSON indir", data=to_json_bytes({
                "siralama_olcutu": sort_key_label,
                "adaylar": export_records,
                "en_uygun_aday": top["Dosya"],
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
            "PDF indir", data=pdf_bytes,
            file_name="cv_karsilastirma.pdf", mime="application/pdf", key="cv_compare_pdf",
        )

    st.markdown("### 🧭 En Uygun Aday Neden Seçildi?")
    for line in explanation_lines:
        st.markdown(f"- {line}")

    st.caption(
        "Not: Bu karşılaştırma ve tahminler anahtar kelime tabanlı sezgisel bir yöntemle üretilmiştir; "
        "bir ön değerlendirme olarak kullanılmalı, nihai karar için insan incelemesi yapılmalıdır."
    )


def _parse_job_postings(text: str) -> list[str]:
    postings = re.split(r"\n\s*-{3,}\s*\n", text.strip())
    return [p.strip() for p in postings if p.strip()]


def _render_deep_analysis():
    st.subheader("🆓 ATS Uyumu & Derin Analiz")
    st.caption(
        "ATS uyum skoru, deneyim/unvan tutarsızlığı tespiti, ilan listesine göre gerekçeli "
        "eşleştirme ve yinelenen aday kontrolü — tamamen kural tabanlı, **ücretsiz** ve harici "
        "hiçbir API'ye bağımlı değil (ATS format kontrolü açık kaynak OpenResume'un yaklaşımından "
        "esinlenmiştir). Diğer modlar gibi bir ön değerlendirmedir; nihai karar için insan "
        "incelemesi önerilir."
    )

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
        st.info(
            "Bu özellik, **📊 Çoklu CV Karşılaştırma** sekmesinde yüklediğiniz CV'leri kullanır "
            "(diğer adaylar, yinelenen aday kontrolü için havuz oluşturur). Lütfen önce o sekmede "
            "en az bir CV yükleyin."
        )
        return

    file_names = list(candidate_pool.keys())
    subject_name = st.selectbox("Derin analiz edilecek CV", file_names, key="cv_deep_subject")
    job_text = st.text_area(
        "İş ilanları (birden fazla ilanı '---' ile ayırın, opsiyonel)", height=180, key="cv_deep_job_postings",
    )

    if not st.button("Analiz Et", type="primary", key="cv_deep_analyze_btn"):
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

    st.success(f"Analiz edilen CV: **{subject_name}**")

    ats = result["ats_uyum"]
    st.markdown("### 1️⃣ ATS Uyum Skoru")
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
            st.markdown("**Eksik Anahtar Kelimeler**")
            st.write(", ".join(ats["eksik_anahtar_kelimeler"]) if ats["eksik_anahtar_kelimeler"] else "—")
            st.markdown("**Format Sorunları**")
            st.write(", ".join(ats["format_sorunlari"]) if ats["format_sorunlari"] else "—")
        st.markdown("**İyileştirme Önerileri**")
        for oneri in ats["oneriler"][:3]:
            st.markdown(f"- {oneri}")

    st.markdown("### 2️⃣ Tutarsızlık Analizi")
    tutarsizlik = result["tutarsizlik"]
    if tutarsizlik["var_mi"]:
        st.warning(tutarsizlik["aciklama"])
    else:
        st.success(tutarsizlik["aciklama"] or "Tutarlı")

    st.markdown("### 3️⃣ İlan Eşleştirme")
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
        st.info("İlan listesi girilmedi.")

    st.markdown("### 4️⃣ Yinelenen Aday Kontrolü")
    yinelenen = result["yinelenen_aday"]
    if yinelenen["bulundu_mu"]:
        st.warning(
            f"Olası eşleşme: **{yinelenen['eslesen_kayit']}** "
            f"(benzerlik: %{yinelenen['benzerlik_orani']}). {yinelenen['aciklama']}"
        )
    else:
        st.success(yinelenen["aciklama"] or "Yinelenen aday bulunamadı.")

    st.markdown("### Dışa Aktar")
    c1, c2 = st.columns(2)
    with c1:
        st.download_button(
            "JSON indir", data=to_json_bytes({"aday": subject_name, **result}),
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
            "PDF indir", data=pdf_bytes,
            file_name=f"{subject_name}_derin_analiz.pdf", mime="application/pdf", key="cv_deep_pdf",
        )

    st.caption(
        "Not: Bu analiz anahtar kelime ve kural tabanlı sezgisel bir yöntemle üretilmiştir; "
        "bir ön değerlendirme olarak kullanılmalı, nihai karar için insan incelemesi yapılmalıdır."
    )
