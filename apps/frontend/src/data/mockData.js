// Prediction output (mirrors PRD Section 7.6 exactly)
export const prediction = {
    user_id: "arjun-sharma-001",
    generated_at: "2026-03-07T10:30:00Z",
    overall_risk_score: 68,
    overall_risk_level: "moderate",
    confidence: "medium",
    data_completeness: 0.82,
    diseases: [
        {
            category: "cardiovascular",
            risk_score: 74,
            risk_level: "high",
            time_horizon: "12_months",
            shap_factors: [
                { feature: "hr_variability", label: "Heart Rate Variability (6/7 days low)", contribution: 28, direction: "negative" },
                { feature: "cholesterol_flag", label: "Cholesterol History — 2022 Lab Report", contribution: 21, direction: "positive" },
                { feature: "sleep_avg_14d", label: "Average Sleep < 5.5 hrs (14 days)", contribution: 18, direction: "negative" },
                { feature: "sedentary_score", label: "Sedentary Desk Lifestyle", contribution: 7, direction: "positive" },
                { feature: "age_risk_factor", label: "Age Risk Factor: 31", contribution: 4, direction: "positive" }
            ]
        },
        { category: "diabetes", risk_score: 31, risk_level: "low", shap_factors: [] },
        { category: "respiratory", risk_score: 18, risk_level: "low", shap_factors: [] },
        { category: "hypertension", risk_score: 41, risk_level: "moderate", shap_factors: [] },
        { category: "hepatic", risk_score: 12, risk_level: "low", shap_factors: [] },
        { category: "metabolic", risk_score: 28, risk_level: "low", shap_factors: [] }
    ],
    alerts: [
        {
            type: "high_risk", category: "cardiovascular",
            message: "Cardiovascular risk elevated — schedule Lipid Profile within 7 days"
        }
    ]
};

// Test recommendations (mirrors PRD Section 12.2 rules)
export const testRecommendations = [
    { name: "Lipid Profile", priority: "urgent", cost_inr: 500, reason: "Cardiovascular risk > 70" },
    { name: "Fasting Blood Sugar", priority: "urgent", cost_inr: 80, reason: "Metabolic risk indicator" },
    { name: "HbA1c", priority: "urgent", cost_inr: 350, reason: "3-month glucose check" },
    { name: "ECG (12-lead)", priority: "recommended", cost_inr: 200, reason: "HRV anomaly detected" },
    { name: "Thyroid Profile", priority: "optional", cost_inr: 600, reason: "Fatigue pattern logged" }
];

// Wearable signals (mirrors PRD Section 5.1 data types)
export const wearableData = {
    heart_rate: {
        current: 84, avg_7d: 81, unit: "BPM",
        trend: [{ t: "6a", v: 78 }, { t: "7a", v: 82 }, { t: "8a", v: 91 }, { t: "9a", v: 88 },
        { t: "10a", v: 84 }, { t: "11a", v: 79 }, { t: "12p", v: 83 }, { t: "1p", v: 85 },
        { t: "2p", v: 80 }, { t: "3p", v: 77 }, { t: "4p", v: 82 }, { t: "Now", v: 84 }]
    },
    spo2: { current: 97, avg_7d: 97.2, unit: "%" },
    hrv: { current: 28, avg_7d: 31, unit: "ms" },
    steps: { today: 5914, goal: 8000, avg_30d: 6200 },
    sleep: {
        last_night_hours: 6.18, goal_hours: 8.0,
        unit: "hrs",
        weekly: [
            { day: "Sun", deep: 7.5, light: 5.0, rem: 3.5, awake: 2.0 },
            { day: "Mon", deep: 8.0, light: 6.0, rem: 4.0, awake: 1.5 },
            { day: "Tue", deep: 6.5, light: 4.5, rem: 3.0, awake: 3.0 },
            { day: "Wed", deep: 9.0, light: 7.0, rem: 5.0, awake: 1.0 },
            { day: "Thu", deep: 10.0, light: 8.0, rem: 5.5, awake: 2.5 },
            { day: "Fri", deep: 11.5, light: 9.5, rem: 6.0, awake: 1.5 },
            { day: "Sat", deep: 12.0, light: 10.0, rem: 6.5, awake: 2.0 }
        ]
    },
    heart_breath: [
        { t: "11p", hr: 74, br: 18 }, { t: "12a", hr: 72, br: 17 }, { t: "1a", hr: 69, br: 16 },
        { t: "2a", hr: 68, br: 17 }, { t: "3a", hr: 71, br: 18 }, { t: "4a", hr: 73, br: 19 },
        { t: "5a", hr: 70, br: 17 }, { t: "6a", hr: 72, br: 16 }, { t: "7a", hr: 63, br: 15 }
    ]
};

// Features (mirrors PRD Section 6 feature names exactly)
export const features = {
    avg_hr_7d: 81.2,
    hr_variability: 28.4,
    spo2_avg_7d: 97.2,
    sleep_avg_14d: 5.8,
    sleep_below_6h_count: 6,
    steps_avg_30d: 6200,
    sedentary_score: 0.62,
    bmi: 24.3,
    bmi_category: 1,
    age: 31,
    age_risk_factor: 0.41,
    symptom_chest_pain_7d: 1,
    symptom_fatigue_14d: 4,
    cholesterol_flag: 1,
    lifestyle_score: 0.5,
    data_completeness: 0.82
};
