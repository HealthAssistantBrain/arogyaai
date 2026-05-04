from __future__ import annotations

from typing import Any, Iterable


GUIDE_TYPES = (
    {
        "name": "symptom explanation",
        "tags": ("symptoms", "triage", "history"),
        "severity": "watch",
        "focus": (
            "how the symptom pattern usually presents",
            "what timing, severity, triggers, and associated symptoms change the level of concern",
            "which objective readings or labs can help separate common causes from higher-risk patterns",
            "why a single symptom should not be treated as a diagnosis without clinical context",
        ),
    },
    {
        "name": "risk factors and mechanisms",
        "tags": ("risk factors", "mechanism", "clinical reasoning"),
        "severity": "routine",
        "focus": (
            "modifiable and non-modifiable risk factors",
            "how lifestyle, age, family history, medicines, and comorbid disease can interact",
            "which model drivers should be interpreted as probability signals rather than proof of disease",
            "why repeated measurements and trend review are more useful than isolated values",
        ),
    },
    {
        "name": "clinical assessment reference",
        "tags": ("assessment", "labs", "vitals"),
        "severity": "caution",
        "focus": (
            "what a clinician may ask or measure during assessment",
            "which tests, vital signs, or history elements are commonly relevant",
            "how wearable and app data can support trend recognition while remaining incomplete",
            "when persistent or clustered findings justify timely medical follow-up",
        ),
    },
    {
        "name": "lifestyle recommendations",
        "tags": ("lifestyle", "prevention", "self care"),
        "severity": "routine",
        "focus": (
            "safe first-step changes that are usually reasonable for nonurgent patterns",
            "how sleep, activity, food quality, hydration, tobacco, alcohol, and stress affect risk",
            "how to make recommendations gradual and realistic rather than extreme",
            "when symptoms should pause activity escalation until a clinician reviews the pattern",
        ),
    },
    {
        "name": "red flags and escalation",
        "tags": ("red flags", "safety", "urgent care"),
        "severity": "urgent",
        "focus": (
            "symptoms that should be treated as urgent rather than routine coaching",
            "why severe, sudden, worsening, or multi-system symptoms need prompt in-person care",
            "how chronic disease, pregnancy, immune suppression, older age, and abnormal vitals raise concern",
            "how to phrase safety guidance without diagnosing or falsely reassuring",
        ),
    },
)


CONDITIONS: tuple[dict[str, Any], ...] = (
    {
        "key": "diabetes_type_2",
        "condition": "type 2 diabetes risk",
        "disease_type": "diabetes",
        "source": "CDC Diabetes",
        "source_org": "CDC",
        "source_url": "https://www.cdc.gov/diabetes/index.html",
        "signals": ("increased thirst", "frequent urination", "fatigue", "blurred vision", "slow wound healing"),
        "risk_factors": ("family history", "higher body weight", "physical inactivity", "prediabetes", "hypertension"),
        "red_flags": ("confusion", "dehydration", "rapid breathing", "vomiting with very high glucose"),
    },
    {
        "key": "hypertension",
        "condition": "hypertension and elevated blood pressure",
        "disease_type": "hypertension",
        "source": "CDC High Blood Pressure",
        "source_org": "CDC",
        "source_url": "https://www.cdc.gov/high-blood-pressure/about/index.html",
        "signals": ("repeated high blood pressure", "headache", "dizziness", "chest discomfort", "shortness of breath"),
        "risk_factors": ("age", "family history", "high sodium intake", "diabetes", "physical inactivity"),
        "red_flags": ("chest pain", "severe shortness of breath", "confusion", "new neurologic weakness"),
    },
    {
        "key": "cardiovascular_disease",
        "condition": "cardiovascular disease risk",
        "disease_type": "cardiovascular",
        "source": "WHO Cardiovascular diseases fact sheet",
        "source_org": "WHO",
        "source_url": "https://www.who.int/news-room/fact-sheets/detail/cardiovascular-diseases-(cvds)",
        "signals": ("chest pressure", "breathlessness", "palpitations", "leg swelling", "reduced exercise tolerance"),
        "risk_factors": ("smoking", "high blood pressure", "diabetes", "high blood lipids", "physical inactivity"),
        "red_flags": ("chest pressure lasting more than a few minutes", "fainting", "stroke symptoms", "collapse"),
    },
    {
        "key": "dyslipidemia",
        "condition": "cholesterol and lipid risk",
        "disease_type": "cardiovascular",
        "source": "CDC Cholesterol",
        "source_org": "CDC",
        "source_url": "https://www.cdc.gov/cholesterol/index.htm",
        "signals": ("high LDL", "high triglycerides", "low HDL", "xanthomas", "family history of early heart disease"),
        "risk_factors": ("diet quality", "diabetes", "hypothyroidism", "kidney disease", "genetic lipid disorders"),
        "red_flags": ("chest pain", "stroke symptoms", "severe shortness of breath", "fainting"),
    },
    {
        "key": "obesity_weight",
        "condition": "body weight and metabolic risk",
        "disease_type": "obesity",
        "source": "WHO Obesity and overweight fact sheet",
        "source_org": "WHO",
        "source_url": "https://www.who.int/news-room/fact-sheets/detail/obesity-and-overweight",
        "signals": ("increasing BMI", "waist gain", "reduced stamina", "snoring", "joint pain"),
        "risk_factors": ("sleep disruption", "physical inactivity", "medicines", "food environment", "stress"),
        "red_flags": ("rapid unexplained weight change", "breathlessness at rest", "chest pain", "severe swelling"),
    },
    {
        "key": "physical_inactivity",
        "condition": "low physical activity and sedentary behavior",
        "disease_type": "lifestyle",
        "source": "WHO Physical activity fact sheet",
        "source_org": "WHO",
        "source_url": "https://www.who.int/news-room/fact-sheets/detail/physical-activity",
        "signals": ("low steps", "sedentary time", "deconditioning", "fatigue with exertion", "weight gain"),
        "risk_factors": ("desk work", "pain", "poor sleep", "low mood", "unsafe walking environment"),
        "red_flags": ("chest pain with exertion", "fainting", "severe breathlessness", "new neurologic symptoms"),
    },
    {
        "key": "sleep_deficiency",
        "condition": "sleep deficiency",
        "disease_type": "sleep",
        "source": "NIH NHLBI Sleep Deprivation and Deficiency",
        "source_org": "NIH",
        "source_url": "https://www.nhlbi.nih.gov/health/sleep-deprivation/health-effects",
        "signals": ("daytime sleepiness", "fatigue", "poor concentration", "irritability", "slow reaction time"),
        "risk_factors": ("irregular schedule", "late caffeine", "stress", "pain", "screen exposure"),
        "red_flags": ("dangerous sleepiness while driving", "confusion", "chest pain at night", "suicidal thoughts"),
    },
    {
        "key": "sleep_apnea",
        "condition": "obstructive sleep apnea risk",
        "disease_type": "sleep",
        "source": "NIH NHLBI Sleep Apnea",
        "source_org": "NIH",
        "source_url": "https://www.nhlbi.nih.gov/health/sleep-apnea",
        "signals": ("loud snoring", "witnessed pauses in breathing", "gasping", "morning headache", "daytime sleepiness"),
        "risk_factors": ("higher body weight", "large neck circumference", "nasal obstruction", "hypertension", "family history"),
        "red_flags": ("severe breathlessness", "dangerous sleepiness", "chest pain", "fainting"),
    },
    {
        "key": "asthma",
        "condition": "asthma symptoms and triggers",
        "disease_type": "respiratory",
        "source": "CDC Asthma",
        "source_org": "CDC",
        "source_url": "https://www.cdc.gov/asthma/index.html",
        "signals": ("wheezing", "cough", "chest tightness", "shortness of breath", "night symptoms"),
        "risk_factors": ("allergens", "smoke", "air pollution", "respiratory infection", "exercise trigger"),
        "red_flags": ("trouble speaking", "blue lips", "severe breathlessness", "poor response to rescue medicine"),
    },
    {
        "key": "copd",
        "condition": "COPD and chronic breathlessness",
        "disease_type": "respiratory",
        "source": "NIH NHLBI COPD",
        "source_org": "NIH",
        "source_url": "https://www.nhlbi.nih.gov/health/copd",
        "signals": ("chronic cough", "mucus", "wheezing", "chest tightness", "shortness of breath with activity"),
        "risk_factors": ("smoking", "secondhand smoke", "air pollution", "occupational dust", "family history"),
        "red_flags": ("severe breathlessness", "blue lips", "confusion", "chest pain"),
    },
    {
        "key": "influenza_respiratory_infection",
        "condition": "influenza-like respiratory infection",
        "disease_type": "infection",
        "source": "CDC Influenza",
        "source_org": "CDC",
        "source_url": "https://www.cdc.gov/flu/signs-symptoms/index.html",
        "signals": ("fever", "cough", "sore throat", "body aches", "fatigue"),
        "risk_factors": ("older age", "pregnancy", "asthma", "diabetes", "heart disease"),
        "red_flags": ("difficulty breathing", "persistent chest pain", "confusion", "dehydration"),
    },
    {
        "key": "chronic_kidney_disease",
        "condition": "chronic kidney disease risk",
        "disease_type": "kidney",
        "source": "NIDDK Chronic Kidney Disease",
        "source_org": "NIH",
        "source_url": "https://www.niddk.nih.gov/health-information/kidney-disease/chronic-kidney-disease-ckd",
        "signals": ("reduced eGFR", "albumin in urine", "swelling", "fatigue", "high blood pressure"),
        "risk_factors": ("diabetes", "high blood pressure", "heart disease", "family history of kidney failure", "NSAID exposure"),
        "red_flags": ("very low urine output", "confusion", "severe swelling", "shortness of breath"),
    },
    {
        "key": "anemia",
        "condition": "anemia and low hemoglobin",
        "disease_type": "hematology",
        "source": "NIH NHLBI Anemia",
        "source_org": "NIH",
        "source_url": "https://www.nhlbi.nih.gov/health/anemia",
        "signals": ("fatigue", "weakness", "shortness of breath", "dizziness", "pale skin"),
        "risk_factors": ("blood loss", "low iron intake", "B12 deficiency", "kidney disease", "heavy menstrual bleeding"),
        "red_flags": ("chest pain", "fainting", "black stools", "heavy bleeding"),
    },
    {
        "key": "thyroid_dysfunction",
        "condition": "thyroid dysfunction",
        "disease_type": "endocrine",
        "source": "NIDDK Thyroid Disease",
        "source_org": "NIH",
        "source_url": "https://www.niddk.nih.gov/health-information/endocrine-diseases/thyroid-disease",
        "signals": ("fatigue", "weight change", "palpitations", "heat or cold intolerance", "bowel change"),
        "risk_factors": ("family history", "autoimmune disease", "iodine imbalance", "thyroid surgery", "certain medicines"),
        "red_flags": ("severe palpitations", "confusion", "chest pain", "extreme weakness"),
    },
    {
        "key": "uti",
        "condition": "urinary tract infection",
        "disease_type": "urinary",
        "source": "CDC Urinary Tract Infection",
        "source_org": "CDC",
        "source_url": "https://www.cdc.gov/uti/about/index.html",
        "signals": ("burning urination", "frequent urination", "urgency", "lower abdominal pressure", "blood in urine"),
        "risk_factors": ("previous UTI", "recent sexual activity", "pregnancy", "older age", "urinary tract structural problems"),
        "red_flags": ("fever", "chills", "flank pain", "nausea or vomiting"),
    },
    {
        "key": "gerd",
        "condition": "gastroesophageal reflux disease",
        "disease_type": "digestive",
        "source": "NIDDK GERD",
        "source_org": "NIH",
        "source_url": "https://www.niddk.nih.gov/health-information/digestive-diseases/acid-reflux-ger-gerd-adults/symptoms-causes",
        "signals": ("heartburn", "regurgitation", "chest burning", "chronic cough", "trouble swallowing"),
        "risk_factors": ("large late meals", "higher body weight", "pregnancy", "tobacco", "trigger foods"),
        "red_flags": ("trouble swallowing", "vomiting blood", "black stools", "unexplained weight loss"),
    },
    {
        "key": "diarrhea_dehydration",
        "condition": "diarrhea and dehydration risk",
        "disease_type": "digestive",
        "source": "NIDDK Diarrhea",
        "source_org": "NIH",
        "source_url": "https://www.niddk.nih.gov/health-information/digestive-diseases/diarrhea/symptoms-causes",
        "signals": ("loose watery stools", "abdominal cramps", "nausea", "dizziness", "dark urine"),
        "risk_factors": ("infection exposure", "food poisoning", "antibiotics", "immune suppression", "older age"),
        "red_flags": ("blood in stool", "severe dehydration", "high fever", "severe abdominal pain"),
    },
    {
        "key": "constipation",
        "condition": "constipation",
        "disease_type": "digestive",
        "source": "NIDDK Constipation",
        "source_org": "NIH",
        "source_url": "https://www.niddk.nih.gov/health-information/digestive-diseases/constipation/symptoms-causes",
        "signals": ("hard stools", "infrequent stools", "straining", "bloating", "incomplete emptying"),
        "risk_factors": ("low fiber intake", "dehydration", "low physical activity", "iron supplements", "hypothyroidism"),
        "red_flags": ("blood in stool", "constant abdominal pain", "vomiting", "unexplained weight loss"),
    },
    {
        "key": "headache_migraine",
        "condition": "headache and migraine patterns",
        "disease_type": "neurology",
        "source": "NIH NINDS Headache",
        "source_org": "NIH",
        "source_url": "https://www.ninds.nih.gov/health-information/disorders/headache",
        "signals": ("headache", "light sensitivity", "nausea", "visual aura", "neck tension"),
        "risk_factors": ("sleep disruption", "stress", "dehydration", "skipped meals", "medication overuse"),
        "red_flags": ("sudden worst headache", "new weakness", "confusion", "stiff neck with fever"),
    },
    {
        "key": "dizziness",
        "condition": "dizziness and faintness",
        "disease_type": "general",
        "source": "ArogyaAI Clinical Safety Reference",
        "source_org": "ArogyaAI",
        "source_url": "",
        "signals": ("lightheadedness", "vertigo", "faintness", "unsteadiness", "palpitations"),
        "risk_factors": ("dehydration", "low blood pressure", "medication effects", "anemia", "arrhythmia"),
        "red_flags": ("fainting", "chest pain", "new neurologic symptoms", "severe headache"),
    },
    {
        "key": "stress_anxiety",
        "condition": "stress and anxiety symptoms",
        "disease_type": "mental_health",
        "source": "NIH NIMH Anxiety Disorders",
        "source_org": "NIH",
        "source_url": "https://www.nimh.nih.gov/health/topics/anxiety-disorders",
        "signals": ("worry", "palpitations", "shortness of breath", "sleep disruption", "muscle tension"),
        "risk_factors": ("life stress", "trauma", "caffeine", "poor sleep", "family history"),
        "red_flags": ("suicidal thoughts", "chest pain", "fainting", "inability to function"),
    },
    {
        "key": "depression_fatigue",
        "condition": "depression-related fatigue and low mood",
        "disease_type": "mental_health",
        "source": "NIH NIMH Depression",
        "source_org": "NIH",
        "source_url": "https://www.nimh.nih.gov/health/topics/depression",
        "signals": ("low mood", "loss of interest", "fatigue", "sleep change", "appetite change"),
        "risk_factors": ("chronic stress", "medical illness", "family history", "substance use", "social isolation"),
        "red_flags": ("suicidal thoughts", "self-harm thoughts", "psychosis", "inability to care for self"),
    },
    {
        "key": "air_quality",
        "condition": "air quality and respiratory irritation",
        "disease_type": "environmental",
        "source": "WHO Air pollution",
        "source_org": "WHO",
        "source_url": "https://www.who.int/health-topics/air-pollution",
        "signals": ("cough", "wheezing", "shortness of breath", "throat irritation", "reduced exercise tolerance"),
        "risk_factors": ("asthma", "COPD", "heart disease", "outdoor pollution", "wildfire smoke"),
        "red_flags": ("severe breathlessness", "blue lips", "chest pain", "confusion"),
    },
    {
        "key": "medication_effects",
        "condition": "medication effects and symptom review",
        "disease_type": "medication_safety",
        "source": "ArogyaAI Medication Safety Reference",
        "source_org": "ArogyaAI",
        "source_url": "",
        "signals": ("dizziness", "fatigue", "nausea", "sleep change", "blood pressure change"),
        "risk_factors": ("new medicine", "dose change", "multiple medicines", "kidney disease", "older age"),
        "red_flags": ("swelling of lips or face", "trouble breathing", "fainting", "severe rash"),
    },
)


def _sentence_list(values: tuple[str, ...]) -> str:
    if len(values) == 1:
        return values[0]
    return ", ".join(values[:-1]) + f", and {values[-1]}"


def iter_generated_documents() -> Iterable[dict[str, Any]]:
    for condition in CONDITIONS:
        for guide in GUIDE_TYPES:
            for variant_index, focus in enumerate(guide["focus"], start=1):
                condition_name = condition["condition"]
                guide_name = guide["name"]
                title = f"{condition_name.title()} - {guide_name.title()} {variant_index}"
                tags = tuple(
                    dict.fromkeys(
                        (
                            condition["disease_type"],
                            condition["key"].replace("_", " "),
                            *guide["tags"],
                            *condition["signals"][:3],
                            *condition["risk_factors"][:3],
                        )
                    )
                )
                text = (
                    f"This guide covers {condition_name} with emphasis on {focus}. "
                    f"Relevant symptoms or signals include {_sentence_list(condition['signals'])}. "
                    f"Risk interpretation should consider {_sentence_list(condition['risk_factors'])}. "
                    "ArogyaAI should explain these findings as possible contributors or risk markers, not as a confirmed diagnosis. "
                    "Use timing, severity, trend direction, associated symptoms, recent medicines, vitals, and laboratory context to make retrieval-grounded reasoning more specific. "
                    f"Escalation language should be stronger when the user reports {_sentence_list(condition['red_flags'])}. "
                    "For nonurgent patterns, recommend practical monitoring, clinician follow-up when symptoms persist, and lifestyle steps that fit the user's current capacity."
                )
                yield {
                    "document_id": f"generated:{condition['key']}:{guide_name.replace(' ', '_')}:{variant_index}",
                    "source": condition["source"],
                    "source_url": condition["source_url"],
                    "source_org": condition["source_org"],
                    "topic": f"{condition_name} {guide_name} {variant_index}",
                    "disease_type": condition["disease_type"],
                    "title": title,
                    "text": text,
                    "condition": condition_name,
                    "symptoms": condition["signals"],
                    "risk_factors": condition["risk_factors"],
                    "severity": guide["severity"],
                    "tags": tags,
                }
