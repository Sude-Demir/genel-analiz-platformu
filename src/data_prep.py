"""IBM HR Analytics Employee Attrition ham verisini temizler ve Türkçeleştirir.

Girdi: data/raw/HR-Employee-Attrition.csv (orijinal İngilizce kolonlar)
Çıktı: data/employees.csv (Türkçe kolon adları ve değerleri)
"""
import os

import pandas as pd

BASE_DIR = os.path.dirname(__file__)
RAW_PATH = os.path.join(BASE_DIR, "..", "data", "raw", "HR-Employee-Attrition.csv")
OUT_PATH = os.path.join(BASE_DIR, "..", "data", "employees.csv")

# Tüm satırlarda sabit olduğu için analitik değeri olmayan kolonlar
CONSTANT_COLUMNS = ["EmployeeCount", "Over18", "StandardHours"]

COLUMN_MAP = {
    "EmployeeNumber": "CalisanID",
    "Age": "Yas",
    "Attrition": "Attrition",
    "BusinessTravel": "SeyahatSikligi",
    "DailyRate": "GunlukUcret",
    "Department": "Departman",
    "DistanceFromHome": "EvUzakligiKm",
    "Education": "EgitimSeviyesi",
    "EducationField": "EgitimAlani",
    "EnvironmentSatisfaction": "CalismaOrtamiTatmini",
    "Gender": "Cinsiyet",
    "HourlyRate": "SaatlikUcret",
    "JobInvolvement": "IseBagliligi",
    "JobLevel": "IsSeviyesi",
    "JobRole": "Pozisyon",
    "JobSatisfaction": "IsTatmini",
    "MaritalStatus": "MedeniDurum",
    "MonthlyIncome": "AylikGelir",
    "MonthlyRate": "AylikUcretOrani",
    "NumCompaniesWorked": "OncekiSirketSayisi",
    "OverTime": "FazlaMesai",
    "PercentSalaryHike": "MaasArtisYuzdesi",
    "PerformanceRating": "PerformansPuani",
    "RelationshipSatisfaction": "IliskiTatmini",
    "StockOptionLevel": "HisseOpsiyonSeviyesi",
    "TotalWorkingYears": "ToplamCalismaYili",
    "TrainingTimesLastYear": "GecenYilEgitimSayisi",
    "WorkLifeBalance": "IsYasamDengesi",
    "YearsAtCompany": "SirketteKidemYili",
    "YearsInCurrentRole": "MevcutRoldeKidemYili",
    "YearsSinceLastPromotion": "SonTerfidenBeriGecenYil",
    "YearsWithCurrManager": "YoneticiyleGecenYil",
}

VALUE_MAP = {
    "SeyahatSikligi": {
        "Travel_Rarely": "Nadiren",
        "Travel_Frequently": "Sık Sık",
        "Non-Travel": "Seyahat Yok",
    },
    "Departman": {
        "Sales": "Satış",
        "Research & Development": "Ar-Ge",
        "Human Resources": "İnsan Kaynakları",
    },
    "EgitimAlani": {
        "Life Sciences": "Yaşam Bilimleri",
        "Medical": "Tıp",
        "Marketing": "Pazarlama",
        "Technical Degree": "Teknik Eğitim",
        "Other": "Diğer",
        "Human Resources": "İnsan Kaynakları",
    },
    "Cinsiyet": {"Male": "Erkek", "Female": "Kadın"},
    "MedeniDurum": {"Single": "Bekar", "Married": "Evli", "Divorced": "Boşanmış"},
    "FazlaMesai": {"Yes": "Evet", "No": "Hayır"},
    "Attrition": {"Yes": "Evet", "No": "Hayır"},
}


def prepare() -> pd.DataFrame:
    df = pd.read_csv(RAW_PATH)
    df = df.drop(columns=CONSTANT_COLUMNS)
    df = df.rename(columns=COLUMN_MAP)
    for column, mapping in VALUE_MAP.items():
        df[column] = df[column].map(mapping)
    return df


if __name__ == "__main__":
    employees = prepare()
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    employees.to_csv(OUT_PATH, index=False)

    print(f"employees.csv yazıldı: {len(employees)} satır, {len(employees.columns)} kolon")
    print(f"Attrition oranı: {(employees['Attrition'] == 'Evet').mean():.2%}")
