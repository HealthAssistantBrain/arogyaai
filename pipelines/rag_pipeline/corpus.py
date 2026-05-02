from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .config import RagSettings
from .schemas import CorpusChunk
from .text_cleaning import clean_rag_text, clean_text_list, extract_clinical_fields

logger = logging.getLogger("uvicorn.error")

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "apps" / "backend"

SEEDED_MARKDOWN_CORPUS: dict[str, str] = {
    "diabetes.md": """---
title: Diabetes Clinical Reference
topic: diabetes assessment and early management
disease_type: diabetes
source_org: ArogyaAI
---

# Diabetes Clinical Reference

## Symptoms

Diabetes can present with increased thirst, frequent urination, increased hunger, fatigue, blurred vision, slow wound healing, recurrent skin or urinary infections, unexplained weight change, and tingling or numbness in the feet. Symptoms can be mild or absent in early type 2 diabetes.

## Causes

Diabetes develops when insulin production or insulin action is not enough for normal glucose regulation. Type 2 diabetes commonly reflects insulin resistance combined with gradual beta-cell dysfunction. Illness, steroid medicines, pregnancy, pancreatic disease, and endocrine disorders can also worsen glucose control.

## Risk Factors

Risk factors include overweight or central adiposity, physical inactivity, age, family history, history of gestational diabetes, polycystic ovary syndrome, hypertension, dyslipidemia, smoking, sleep apnea, chronic stress, and prior prediabetes.

## Clinical Notes

Diagnosis usually requires HbA1c, fasting plasma glucose, oral glucose tolerance testing, or random plasma glucose with symptoms. HbA1c can be misleading in anemia, pregnancy, kidney disease, recent blood loss, or hemoglobin variants. Diabetes care should also consider blood pressure, lipids, kidney function, urine albumin, foot sensation, eye screening, and cardiovascular risk.

## Recommendations

Arrange confirmatory testing when symptoms or risk markers persist. Encourage high-fiber meals, reduced sugary drinks, regular activity, weight management when appropriate, smoking cessation, sleep improvement, medication review, and clinician follow-up. Urgent care is needed for vomiting, confusion, dehydration, rapid breathing, severe weakness, very high glucose with ketones, chest pain, stroke-like symptoms, or severe foot infection.
""",
    "cardiovascular.md": """---
title: Cardiovascular Clinical Reference
topic: cardiovascular risk and symptom assessment
disease_type: cardiovascular
source_org: ArogyaAI
---

# Cardiovascular Clinical Reference

## Symptoms

Cardiovascular symptoms include chest pressure, tightness, heaviness, shortness of breath, palpitations, dizziness, fainting, leg swelling, reduced exercise tolerance, fatigue, and pain spreading to the jaw, shoulder, back, or arm. Older adults and people with diabetes may have atypical symptoms such as nausea, sweating, indigestion-like discomfort, or unexplained breathlessness.

## Causes

Symptoms may come from coronary artery disease, arrhythmia, heart failure, valve disease, uncontrolled blood pressure, pulmonary embolism, anemia, thyroid disease, infection, dehydration, medication effects, anxiety, or respiratory illness. Acute chest pain, stroke symptoms, and severe breathlessness need time-sensitive triage.

## Risk Factors

Risk factors include hypertension, high LDL cholesterol, diabetes, smoking, chronic kidney disease, obesity, sedentary behavior, excess alcohol, sleep apnea, family history of premature cardiovascular disease, increasing age, inflammatory conditions, pregnancy-related hypertension, chronic stress, and air pollution exposure.

## Clinical Notes

Assessment commonly includes symptom history, examination, blood pressure, ECG, lipid profile, glucose or HbA1c, kidney function, and sometimes troponin, echocardiography, stress testing, or ambulatory rhythm monitoring. Wearable data can support trend review but cannot rule out acute disease.

## Recommendations

Support long-term risk reduction with regular activity as tolerated, smoking cessation, medication adherence, blood pressure and lipid control, glucose management, lower sodium intake when appropriate, weight management, and sleep apnea evaluation when suggested. Seek emergency care for chest pressure lasting more than a few minutes, chest discomfort with sweating or nausea, fainting, severe shortness of breath, neurologic weakness, speech trouble, blue lips, collapse, or palpitations with chest pain or fainting.
""",
    "sleep.md": """---
title: Sleep Clinical Reference
topic: sleep quality and metabolic health
disease_type: sleep
source_org: ArogyaAI
---

# Sleep Clinical Reference

## Symptoms

Sleep problems may present as difficulty falling asleep, frequent awakenings, early waking, non-restorative sleep, daytime sleepiness, morning headache, irritability, poor concentration, fatigue, or reduced exercise tolerance. Snoring, witnessed pauses in breathing, gasping, dry mouth on waking, and morning hypertension can suggest sleep-disordered breathing.

## Causes

Common causes include stress, anxiety, depression, chronic pain, reflux, nocturia, caffeine, alcohol, nicotine, irregular schedules, shift work, medications, poor sleep environment, restless legs, and obstructive sleep apnea. Sleep disruption can also be secondary to poorly controlled diabetes, respiratory disease, cardiovascular disease, or mood disorders.

## Risk Factors

Insomnia risk rises with chronic stress, mood symptoms, pain, late caffeine, alcohol use, nicotine, and irregular routines. Sleep apnea risk rises with snoring, obesity or central adiposity, large neck circumference, nasal obstruction, family history, male sex, menopause, hypertension, diabetes, and resistant high blood pressure.

## Clinical Notes

Sleep assessment should cover schedule, duration, sleep latency, awakenings, snoring, witnessed apnea, daytime sleepiness, mood, pain, substances, medicines, work schedule, and bedroom environment. Wearable sleep estimates are useful for trends but should be interpreted cautiously. Diagnosis of sleep apnea usually requires a sleep study.

## Recommendations

Use a consistent wake time, morning light exposure, regular activity, limited late caffeine and alcohol, a wind-down routine, a cool dark room, and avoidance of long late naps. Suspected sleep apnea warrants clinician evaluation. Urgent attention is needed for dangerous sleepiness while driving, confusion, chest pain at night, severe breathlessness, fainting, neurologic symptoms, or suicidal thoughts.
""",
    "symptoms.md": """---
title: General Symptoms Clinical Reference
topic: symptom triage and primary care reasoning
disease_type: general
source_org: ArogyaAI
---

# General Symptoms Clinical Reference

## Symptoms

Common symptoms such as fatigue, dizziness, headache, fever, cough, nausea, abdominal discomfort, palpitations, chest discomfort, shortness of breath, sleepiness, weakness, urinary symptoms, swelling, and pain should be interpreted by onset, duration, severity, triggers, associated features, medications, vital signs, and medical history.

## Causes

Symptoms can come from infection, dehydration, anemia, thyroid disease, glucose abnormalities, blood pressure changes, heart or lung disease, medication effects, poor sleep, stress, anxiety, pain, inflammation, pregnancy-related conditions, or chronic disease flare. A single symptom usually has several possible explanations.

## Risk Factors

Higher concern is associated with older age, pregnancy, immune suppression, diabetes, kidney disease, known heart or lung disease, anticoagulant use, recent surgery, recent travel, severe pain, persistent fever, abnormal vital signs, sudden onset, progressive worsening, and symptoms that limit normal activity.

## Clinical Notes

Clinical reasoning should first identify red flags, then combine symptom pattern with objective data such as temperature, heart rate, blood pressure, oxygen saturation, glucose, sleep, activity, labs, and recent clinical history. Digital guidance should not diagnose from symptoms alone and should ask follow-up questions when context is missing.

## Recommendations

Seek urgent care for chest pressure, severe shortness of breath, fainting, confusion, one-sided weakness, facial droop, trouble speaking, severe bleeding, blue lips, seizure, severe allergic reaction, sudden severe headache, stiff neck with fever, or rapidly worsening symptoms. For nonurgent symptoms, track timing and severity, hydrate if appropriate, rest, review medications, monitor vital signs, and arrange clinical review if symptoms persist, recur, or worsen.
""",
}


@dataclass(slots=True)
class CorpusDocument:
    document_id: str
    source: str
    title: str
    text: str
    topic: str = "general"
    disease_type: str = "general"
    source_url: str = ""
    source_org: str = ""
    condition: str = ""
    symptoms: tuple[str, ...] = ()
    risk_factors: tuple[str, ...] = ()
    severity: str = "routine"


_METADATA_BY_STEM = {
    "diabetes_risk_factors": {
        "topic": "diabetes risk factors",
        "disease_type": "diabetes",
        "source": "CDC Diabetes Risk Factors",
        "source_url": "https://www.cdc.gov/diabetes/risk-factors/index.html",
        "source_org": "CDC",
    },
    "bmi_impact": {
        "topic": "body weight and metabolic health",
        "disease_type": "diabetes",
        "source": "CDC About Body Mass Index",
        "source_url": "https://www.cdc.gov/bmi/about/index.html",
        "source_org": "CDC",
    },
    "sleep_metabolic_health": {
        "topic": "sleep and metabolic health",
        "disease_type": "sleep",
        "source": "NIH NHLBI Sleep Deprivation and Deficiency",
        "source_url": "https://www.nhlbi.nih.gov/health/sleep-deprivation/health-effects",
        "source_org": "NIH",
    },
    "activity_cardiovascular_risk": {
        "topic": "physical activity and cardiovascular risk",
        "disease_type": "cardiovascular",
        "source": "WHO Physical activity fact sheet",
        "source_url": "https://www.who.int/news-room/fact-sheets/detail/physical-activity",
        "source_org": "WHO",
    },
}

_SEVERITY_RANK = {
    "routine": 0,
    "watch": 1,
    "caution": 2,
    "urgent": 3,
}


def infer_clinical_severity(value: Any, *, default: str = "routine") -> str:
    text = str(value or "").lower()
    if any(
        term in text
        for term in (
            "emergency",
            "urgent care",
            "urgent attention",
            "seek immediate",
            "immediate medical",
            "severe shortness of breath",
            "stroke-like",
            "chest pressure lasting",
            "collapse",
        )
    ):
        return "urgent"
    if any(
        term in text
        for term in (
            "prompt clinical",
            "red flag",
            "worsening",
            "persistent",
            "high concern",
            "higher concern",
            "clinician evaluation",
        )
    ):
        return "caution"
    if any(term in text for term in ("monitor", "track", "follow-up", "follow up", "review")):
        return "watch"
    return default if default in _SEVERITY_RANK else "routine"


def normalize_severity(value: Any, *, text: Any = "") -> str:
    label = str(value or "").strip().lower().replace("_", " ").replace("-", " ")
    aliases = {
        "low": "routine",
        "normal": "routine",
        "moderate": "caution",
        "medium": "caution",
        "high": "urgent",
        "critical": "urgent",
        "severe": "urgent",
    }
    label = aliases.get(label, label)
    if label in _SEVERITY_RANK:
        return label
    return infer_clinical_severity(text)


def highest_severity(values: Iterable[Any]) -> str:
    severities = [normalize_severity(value) for value in values]
    if not severities:
        return "routine"
    return max(severities, key=lambda item: _SEVERITY_RANK.get(item, 0))


def resolve_corpus_dir(corpus_dir: Path | str) -> Path:
    path = Path(corpus_dir)
    if path.is_absolute():
        return path

    candidates: list[Path] = []
    normalized_parts = tuple(part.lower() for part in path.parts)
    if normalized_parts[:2] == ("apps", "backend"):
        candidates.append(REPO_ROOT / path)

    candidates.extend([Path.cwd() / path, REPO_ROOT / path, BACKEND_ROOT / path])

    unique_candidates: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate.resolve(strict=False)).lower()
        if key not in seen:
            seen.add(key)
            unique_candidates.append(candidate)

    for candidate in unique_candidates:
        if candidate.exists():
            return candidate
    return unique_candidates[0]


def ensure_corpus_seeded(corpus_dir: Path | str) -> Path:
    target_dir = resolve_corpus_dir(corpus_dir)
    created_directory = not target_dir.exists()
    target_dir.mkdir(parents=True, exist_ok=True)

    seeded_files: list[str] = []
    for filename, content in SEEDED_MARKDOWN_CORPUS.items():
        file_path = target_dir / filename
        existing = file_path.read_text(encoding="utf-8").strip() if file_path.exists() else ""
        if existing:
            continue
        file_path.write_text(content.strip() + "\n", encoding="utf-8")
        seeded_files.append(filename)

    if created_directory or seeded_files:
        logger.info(
            "RAG corpus seeded | path=%s files=%s",
            target_dir,
            ", ".join(seeded_files) if seeded_files else "none",
        )

    return target_dir


def _clean_text(value: Any, default: str = "") -> str:
    text = str(value or "").strip()
    return text or default


def _normalize_paragraphs(text: str) -> list[str]:
    return [part.strip() for part in text.split("\n\n") if part.strip()]


def _word_count(text: str) -> int:
    return len(re.findall(r"\S+", text))


def _chunk_paragraphs(paragraphs: list[str], minimum_words: int, maximum_words: int) -> list[str]:
    chunks: list[str] = []
    current_parts: list[str] = []
    current_words = 0

    for paragraph in paragraphs:
        paragraph_words = len(paragraph.split())
        if current_parts and current_words >= minimum_words and current_words + paragraph_words > maximum_words:
            chunks.append("\n\n".join(current_parts).strip())
            current_parts = []
            current_words = 0

        current_parts.append(paragraph)
        current_words += paragraph_words

    if current_parts:
        chunks.append("\n\n".join(current_parts).strip())

    return chunks


def _parse_markdown_frontmatter(raw_text: str) -> tuple[dict[str, str], str]:
    if not raw_text.startswith("---"):
        return {}, raw_text

    match = re.match(r"^---\s*\n(?P<meta>.*?)\n---\s*\n(?P<body>.*)$", raw_text, flags=re.DOTALL)
    if not match:
        return {}, raw_text

    metadata: dict[str, str] = {}
    for line in match.group("meta").splitlines():
        key, separator, value = line.partition(":")
        if separator:
            metadata[key.strip()] = value.strip().strip("\"'")
    return metadata, match.group("body")


def _load_markdown_documents(corpus_dir: Path) -> list[CorpusDocument]:
    documents: list[CorpusDocument] = []
    for file_path in sorted(corpus_dir.glob("*.md")):
        raw_text = file_path.read_text(encoding="utf-8").strip()
        if not raw_text:
            continue

        metadata, body = _parse_markdown_frontmatter(raw_text)
        paragraphs = _normalize_paragraphs(raw_text)
        title = file_path.stem.replace("_", " ").title()
        if paragraphs and paragraphs[0].startswith("#"):
            title = paragraphs[0].lstrip("#").strip()
            paragraphs = paragraphs[1:]

        if body != raw_text:
            paragraphs = _normalize_paragraphs(body)
            if paragraphs and paragraphs[0].startswith("#"):
                title = paragraphs[0].lstrip("#").strip()
                paragraphs = paragraphs[1:]

        defaults = _METADATA_BY_STEM.get(file_path.stem, {})
        clinical_fields = extract_clinical_fields(body, fallback_condition=metadata.get("title") or title)
        cleaned_text = clinical_fields["text"]
        documents.append(
            CorpusDocument(
                document_id=file_path.stem,
                source=_clean_text(metadata.get("source"), _clean_text(defaults.get("source"), file_path.name)),
                source_url=_clean_text(metadata.get("source_url"), _clean_text(defaults.get("source_url"))),
                source_org=_clean_text(metadata.get("source_org"), _clean_text(defaults.get("source_org"))),
                topic=_clean_text(metadata.get("topic"), _clean_text(defaults.get("topic"), "general")),
                disease_type=_clean_text(metadata.get("disease_type"), _clean_text(defaults.get("disease_type"), "general")),
                title=_clean_text(metadata.get("title"), title),
                text=cleaned_text or "\n\n".join(paragraphs).strip(),
                condition=clinical_fields["condition"],
                symptoms=tuple(clinical_fields["symptoms"]),
                risk_factors=tuple(clinical_fields["risk_factors"]),
                severity=normalize_severity(metadata.get("severity"), text=body),
            )
        )

    return documents


def _iter_json_documents(payload: Any, file_path: Path) -> Iterable[dict[str, Any]]:
    if isinstance(payload, list):
        for item in payload:
            if isinstance(item, dict):
                yield item
        return

    if not isinstance(payload, dict):
        return

    source_defaults = {
        "source": payload.get("source"),
        "source_url": payload.get("source_url"),
        "source_org": payload.get("source_org"),
        "topic": payload.get("topic"),
        "disease_type": payload.get("disease_type"),
    }
    if isinstance(payload.get("documents"), list):
        for item in payload["documents"]:
            if isinstance(item, dict):
                yield {**source_defaults, **item}
        return

    for source_index, source in enumerate(payload.get("sources") or [], start=1):
        if not isinstance(source, dict):
            continue
        defaults = {
            "source": source.get("source"),
            "source_url": source.get("source_url"),
            "source_org": source.get("source_org"),
            "topic": source.get("topic"),
            "disease_type": source.get("disease_type"),
        }
        for guidance_index, guidance in enumerate(source.get("guidance") or [], start=1):
            if not isinstance(guidance, dict):
                continue
            record = {**defaults, **guidance}
            record.setdefault("document_id", f"{file_path.stem}:{source_index}:{guidance_index}")
            yield record


def _load_json_documents(corpus_dir: Path) -> list[CorpusDocument]:
    documents: list[CorpusDocument] = []
    for file_path in sorted(corpus_dir.glob("*.json")):
        payload = json.loads(file_path.read_text(encoding="utf-8"))
        for index, record in enumerate(_iter_json_documents(payload, file_path), start=1):
            text = _clean_text(record.get("text"))
            title = _clean_text(record.get("title"), f"{file_path.stem} document {index}")
            if not text:
                continue
            documents.append(
                CorpusDocument(
                    document_id=_clean_text(record.get("document_id"), f"{file_path.stem}:{index}"),
                    source=_clean_text(record.get("source"), file_path.name),
                    source_url=_clean_text(record.get("source_url")),
                    source_org=_clean_text(record.get("source_org")),
                    topic=_clean_text(record.get("topic"), "general"),
                    disease_type=_clean_text(record.get("disease_type"), "general"),
                    title=title,
                    text=clean_rag_text(text),
                    condition=_clean_text(record.get("condition"), title),
                    symptoms=tuple(clean_text_list(record.get("symptoms"), limit=8, item_limit=120)),
                    risk_factors=tuple(clean_text_list(record.get("risk_factors") or record.get("riskFactors"), limit=8, item_limit=120)),
                    severity=normalize_severity(record.get("severity"), text=text),
                )
            )

    for file_path in sorted(corpus_dir.glob("*.jsonl")):
        for line_number, line in enumerate(file_path.read_text(encoding="utf-8").splitlines(), start=1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            record = json.loads(line)
            if not isinstance(record, dict):
                continue
            text = _clean_text(record.get("text"))
            if not text:
                continue
            documents.append(
                CorpusDocument(
                    document_id=_clean_text(record.get("document_id"), f"{file_path.stem}:{line_number}"),
                    source=_clean_text(record.get("source"), file_path.name),
                    source_url=_clean_text(record.get("source_url")),
                    source_org=_clean_text(record.get("source_org")),
                    topic=_clean_text(record.get("topic"), "general"),
                    disease_type=_clean_text(record.get("disease_type"), "general"),
                    title=_clean_text(record.get("title"), f"{file_path.stem} document {line_number}"),
                    text=clean_rag_text(text),
                    condition=_clean_text(record.get("condition"), _clean_text(record.get("title"), f"{file_path.stem} document {line_number}")),
                    symptoms=tuple(clean_text_list(record.get("symptoms"), limit=8, item_limit=120)),
                    risk_factors=tuple(clean_text_list(record.get("risk_factors") or record.get("riskFactors"), limit=8, item_limit=120)),
                    severity=normalize_severity(record.get("severity"), text=text),
                )
            )

    return documents


def load_corpus_documents(settings: RagSettings | None = None) -> list[CorpusDocument]:
    cfg = settings or RagSettings()
    corpus_dir = ensure_corpus_seeded(cfg.corpus_dir)

    documents = [*_load_markdown_documents(corpus_dir), *_load_json_documents(corpus_dir)]
    documents.sort(key=lambda item: (item.source_org, item.source, item.disease_type, item.topic, item.document_id))
    return documents


def _chunk_document(document: CorpusDocument, minimum_words: int, maximum_words: int) -> list[str]:
    paragraphs = _normalize_paragraphs(document.text) or [document.text]
    if _word_count(document.text) <= maximum_words:
        return [document.text]
    return _chunk_paragraphs(paragraphs, minimum_words, maximum_words)


def _build_chunk(
    *,
    chunk_id: str,
    documents: list[CorpusDocument],
    part_number: int,
) -> CorpusChunk:
    first = documents[0]
    title = first.title if len(documents) == 1 else f"{first.source} guidance, part {part_number}"
    text = "\n\n".join(f"{document.title}. {document.text}" for document in documents).strip()
    return CorpusChunk(
        chunk_id=chunk_id,
        source=first.source,
        source_url=first.source_url,
        source_org=first.source_org,
        category=first.disease_type or first.topic or "general",
        topic=first.topic or "general",
        disease_type=first.disease_type or "general",
        title=title,
        text=clean_rag_text(text),
        document_ids=tuple(document.document_id for document in documents),
        condition=first.condition,
        symptoms=tuple(item for document in documents for item in document.symptoms),
        risk_factors=tuple(item for document in documents for item in document.risk_factors),
        severity=highest_severity(document.severity for document in documents),
    )


def load_corpus_chunks(settings: RagSettings | None = None) -> list[CorpusChunk]:
    cfg = settings or RagSettings()
    documents = load_corpus_documents(cfg)

    chunks: list[CorpusChunk] = []
    grouped: dict[tuple[str, str, str, str], list[CorpusDocument]] = {}
    for document in documents:
        if _word_count(document.text) > cfg.chunk_max_words:
            for index, chunk_text in enumerate(_chunk_document(document, cfg.chunk_min_words, cfg.chunk_max_words), start=1):
                chunks.append(
                    CorpusChunk(
                        chunk_id=f"{document.document_id}:chunk:{index}",
                        source=document.source,
                        source_url=document.source_url,
                        source_org=document.source_org,
                        category=document.disease_type or document.topic or "general",
                        topic=document.topic or "general",
                        disease_type=document.disease_type or "general",
                        title=document.title,
                        text=clean_rag_text(chunk_text),
                        document_ids=(document.document_id,),
                        condition=document.condition,
                        symptoms=document.symptoms,
                        risk_factors=document.risk_factors,
                        severity=document.severity,
                    )
                )
            continue

        key = (document.source, document.source_url, document.topic, document.disease_type)
        grouped.setdefault(key, []).append(document)

    for group_index, group_documents in enumerate(grouped.values(), start=1):
        current: list[CorpusDocument] = []
        current_words = 0
        part_number = 1
        for document in group_documents:
            document_words = _word_count(document.text) + _word_count(document.title)
            if current and current_words >= cfg.chunk_min_words and current_words + document_words > cfg.chunk_max_words:
                chunks.append(
                    _build_chunk(
                        chunk_id=f"group:{group_index}:part:{part_number}",
                        documents=current,
                        part_number=part_number,
                    )
                )
                current = []
                current_words = 0
                part_number += 1

            current.append(document)
            current_words += document_words

        if current:
            chunks.append(
                _build_chunk(
                    chunk_id=f"group:{group_index}:part:{part_number}",
                    documents=current,
                    part_number=part_number,
                )
            )

    return chunks
