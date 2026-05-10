from __future__ import annotations


FORBIDDEN_CERTAINTY_PATTERNS: list[tuple[str, str]] = [
    (r"\bYou (?:definitely|certainly|clearly) have\b", "There are signs that may suggest"),
    (r"\bThis confirms (?:you have|that you)\b", "This may be worth evaluating for"),
    (r"\bYou (?:are|have been) diagnosed with\b", "Based on what you've shared, a clinician might consider"),
    (r"\bThis (?:guarantees|proves|means) you have\b", "This could be associated with"),
    (r"\bYou (?:must|need to) take\b", "It may be advisable to discuss with your doctor"),
    (r"\bThe (?:diagnosis|result) is\b", "The assessment suggests"),
    (r"\bIt is (?:certain|definitive) that\b", "There is some indication that"),
    (r"\bI can (?:confirm|diagnose)\b", "Based on available information, it appears"),
    (r"\bWithout doubt\b", "With some uncertainty"),
    (r"\bThere is no question (?:that|you)\b", "It appears likely that"),
    (r"\bYour condition is\b", "The symptoms you've described may be consistent with"),
    (r"\bYou (?:are|will be) fine\b", "Your symptoms seem manageable, though a checkup is always sensible"),
    (r"\bNothing to worry about\b", "While this may not be serious, it's worth monitoring"),
    (r"\bThis is (?:definitely|certainly) not\b", "This seems less likely to be"),
    (r"\btake (\d+(?:\.\d+)?\s*(?:mg|ml|g|units?))\b", "discuss the appropriate dosage with your doctor"),
]

MEDICATION_PATTERNS: list[str] = [
    r"\b\d+\s*(?:mg|ml|mcg|μg|g|IU|units?)\b(?:\s+(?:of|per|daily|twice|once))?",
    r"\btake (?:one|two|three|\d+) (?:tablet|capsule|pill|dose)s?\b",
    r"\b(?:start|begin|initiate) (?:on|with)\s+\w+",
    r"\bprescri(?:be|ption)\b",
    r"\bdrug interaction\b.*\bcombine\b",
    r"\bself.medicate\b",
    r"\bstop taking\b.*\b(?:your|the)\s+\w+\b",
    r"\bincrease (?:your )?dose\b",
    r"\bdo not take\b.{0,40}\b(?:if|while|with)\b",
]

EMERGENCY_PATTERNS: dict[str, list[str]] = {
    "cardiac": [
        r"\bchest (?:pain|tightness|pressure|discomfort)\b",
        r"\b(?:heart attack|myocardial infarction|MI)\b",
        r"\barm (?:pain|numbness).{0,40}\bchest\b",
        r"\bjaw pain.{0,40}\bchest\b",
        r"\bpalpitations.{0,40}\b(?:severe|extreme|fainting)\b",
    ],
    "neurological": [
        r"\b(?:stroke|TIA|transient ischemic)\b",
        r"\bsudden (?:numbness|weakness).{0,40}\b(?:face|arm|leg)\b",
        r"\bslurred speech\b",
        r"\bsudden (?:severe )?headache\b",
        r"\bvision (?:loss|change).{0,40}sudden\b",
        r"\bseizure\b",
        r"\bunconsciousness\b",
    ],
    "respiratory": [
        r"\b(?:can't|cannot|difficulty) breath(?:e|ing)\b",
        r"\bshortness of breath.{0,40}\b(?:severe|sudden|extreme)\b",
        r"\bblue (?:lips|fingers|face|skin)\b",
        r"\bcyanosis\b",
        r"\boxygen.{0,40}(?:low|dropping|crisis)\b",
    ],
    "diabetic_emergency": [
        r"\bhypoglycemi(?:a|c).{0,40}\b(?:severe|unconscious|unresponsive)\b",
        r"\bblood sugar.{0,40}\b(?:very low|critically low|below 50|below 40)\b",
        r"\bdiabetic ketoacidosis\b",
        r"\bDKA\b",
    ],
    "self_harm": [
        r"\b(?:kill|hurt) (?:myself|yourself)\b",
        r"\bsuicid(?:e|al)\b",
        r"\bwant to die\b",
        r"\bself.harm\b",
        r"\bend (?:my|their) life\b",
        r"\bno reason to live\b",
    ],
    "bleeding": [
        r"\bsevere (?:bleeding|blood loss|hemorrhage)\b",
        r"\buncontrolled bleeding\b",
        r"\bhemorrhage\b",
    ],
    "allergic": [
        r"\banaphylax(?:is|tic)\b",
        r"\bthroat (?:closing|swelling).{0,40}\b(?:can't|cannot) breath\b",
        r"\bsevere allergic reaction\b",
    ],
}

ESCALATION_TEMPLATES: dict[str, str] = {
    "cardiac": (
        "⚠️ The symptoms you've described, especially chest pain or pressure, require immediate medical attention. "
        "Please call emergency services (112 / 911) or go to your nearest emergency room right away. "
        "Do not drive yourself. If available, chew an aspirin (325mg) unless allergic. Stay calm and seated."
    ),
    "neurological": (
        "⚠️ These symptoms may indicate a stroke or serious neurological event. Time is critical. "
        "Call emergency services (112 / 911) immediately. Note the time symptoms started because it matters for treatment. "
        "Do not eat or drink anything, and stay with someone until help arrives."
    ),
    "respiratory": (
        "⚠️ Severe breathing difficulty requires immediate emergency care. Call 112 / 911 now. "
        "Sit upright and stay as calm as possible. If you have a prescribed inhaler, use it. Do not lie flat."
    ),
    "diabetic_emergency": (
        "⚠️ A severe blood sugar emergency can be life-threatening. If conscious and able to swallow, consume fast-acting sugar such as juice, "
        "glucose gel, or candy. Call someone to stay with you and contact emergency services (112 / 911) immediately."
    ),
    "self_harm": (
        "💙 I'm really glad you're talking to me, and I want you to be safe. What you're feeling sounds incredibly difficult. "
        "Please reach out to a crisis helpline right now. In India you can call iCall at 9152987821. "
        "If you're in immediate danger, please go to your nearest emergency room or call 112."
    ),
    "bleeding": (
        "⚠️ Severe or uncontrolled bleeding is a medical emergency. Apply firm, direct pressure with a clean cloth and call 112 / 911 immediately. "
        "Do not remove the cloth. Add more on top if it becomes soaked through, and keep the person still."
    ),
    "allergic": (
        "⚠️ Severe allergic reaction or anaphylaxis is life-threatening. Use an EpiPen if available, then call 112 / 911 immediately even if symptoms improve. "
        "Lie down with legs elevated unless breathing is difficult, then sit upright."
    ),
    "general_emergency": (
        "⚠️ Based on what you've described, please seek immediate medical attention. "
        "Call emergency services (112 / 911) or go to your nearest emergency room. Your safety is the priority right now."
    ),
}

HEDGE_PHRASES = [
    "may indicate",
    "could be associated with",
    "worth evaluating clinically",
    "should be assessed by a healthcare provider",
    "may be consistent with",
    "is a possibility worth discussing with your doctor",
    "merits professional evaluation",
    "could suggest",
]

HIGH_RISK_TERMS: set[str] = {
    "cancer",
    "tumor",
    "malignant",
    "carcinoma",
    "metastasis",
    "hiv",
    "aids",
    "sepsis",
    "meningitis",
    "encephalitis",
    "pulmonary embolism",
    "dvt",
    "deep vein thrombosis",
    "kidney failure",
    "liver failure",
    "heart failure",
    "multiple sclerosis",
    "als",
    "parkinson's",
    "alzheimer's",
    "psychosis",
    "schizophrenia",
    "bipolar disorder",
}

RAG_MIN_CONFIDENCE_THRESHOLD: float = 0.45
RAG_STRONG_CONFIDENCE_THRESHOLD: float = 0.72
