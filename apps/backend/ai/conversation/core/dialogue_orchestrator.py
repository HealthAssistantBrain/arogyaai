from __future__ import annotations

import logging

from ..clinical import ClinicianStyleEngine, EscalationDialogue, ReassuranceEngine, SeverityDialogue
from ..compression import ContextCompression
from ..dialogue import ConversationalPacing, FollowupGenerator
from ..personality import EmotionalCalibration, ToneAdapter, VerbosityController
from ..schemas import ConversationState, DialogueContext, MemorySnapshot

logger = logging.getLogger("uvicorn.error")


class DialogueOrchestrator:
    def __init__(self) -> None:
        self.followups = FollowupGenerator()
        self.severity = SeverityDialogue()
        self.reassurance = ReassuranceEngine()
        self.escalation = EscalationDialogue()
        self.style = ClinicianStyleEngine()
        self.calibration = EmotionalCalibration()
        self.tones = ToneAdapter()
        self.verbosity = VerbosityController()
        self.pacing = ConversationalPacing()
        self.compression = ContextCompression()

    def orchestrate(
        self,
        *,
        context: DialogueContext,
        snapshot: MemorySnapshot,
        plan: dict[str, object],
        state: ConversationState,
    ) -> dict[str, object]:
        calibration = self.calibration.calibrate(context, snapshot)
        tone = self.tones.select(context, snapshot, calibration)
        awareness = plan.get("awareness") if isinstance(plan.get("awareness"), dict) else {}
        follow_up_questions = self.followups.generate(
            context,
            snapshot,
            limit=int(plan.get("followup_limit") or 2),
        )

        base_message = str(
            context.response_payload.get("message")
            or context.response_payload.get("summary")
            or context.response_payload.get("clinical_interpretation")
            or ""
        ).strip()
        continuity_reference = snapshot.conversational.continuity_reference
        severity_line = self.severity.describe(context, snapshot)
        grounding_line = str(awareness.get("grounding_line") or "").strip()
        reassurance_line = self.reassurance.compose(context, snapshot) if plan.get("use_reassurance") else ""
        escalation_line = self.escalation.compose(context, snapshot)

        paragraphs: list[str] = []
        if plan.get("use_continuity") and continuity_reference:
            paragraphs.append(f"Keeping continuity in mind, {continuity_reference}.")
        if severity_line:
            paragraphs.append(severity_line)
        if grounding_line and grounding_line.lower() not in base_message.lower():
            paragraphs.append(grounding_line)
        if base_message:
            paragraphs.append(base_message)
        if reassurance_line:
            paragraphs.append(reassurance_line)
        if escalation_line:
            paragraphs.append(escalation_line)

        message = self.style.polish(context, paragraphs)
        message = self.verbosity.trim(
            message,
            target_words=int(plan.get("target_words") or 90),
        )
        follow_up_questions = self.verbosity.reduce_repetition(follow_up_questions)
        quick_replies = self._quick_replies(context, snapshot, follow_up_questions)
        streaming = self.pacing.build(
            message,
            depth=str(plan.get("depth") or context.depth or "short"),
            target_chunk_words=int(plan.get("chunk_target_words") or 22),
        )
        compression = self.compression.compress(context, snapshot)

        state.follow_up_pending = bool(follow_up_questions)
        state.follow_up_focus = follow_up_questions[:2]
        state.recent_recommendations = self.verbosity.reduce_repetition(
            list(context.response_payload.get("recommendations") or [])
            + list(snapshot.conversational.prior_recommendations or [])
        )[:3]
        state.response_chunks = len(streaming.get("chunks") or [])
        state.typing_label = str(streaming.get("typing_label") or state.typing_label)
        state.chunk_strategy = str(streaming.get("chunk_strategy") or state.chunk_strategy)
        state.pacing = {
            "typing_delay_ms": streaming.get("typing_delay_ms"),
            "target_words": plan.get("target_words"),
        }
        state.compression = compression

        logger.info(
            "[DIALOGUE_REASONING] session=%s mode=%s depth=%s tone=%s chunks=%s",
            context.session_id,
            context.mode,
            context.depth,
            tone.get("profile"),
            len(streaming.get("chunks") or []),
        )
        logger.info(
            "[FOLLOWUP_GENERATED] session=%s count=%s",
            context.session_id,
            len(follow_up_questions),
        )
        logger.info(
            "[CONTEXT_SUMMARIZED] session=%s retained=%s",
            context.session_id,
            compression.get("retained_items"),
        )

        return {
            "message": message,
            "follow_up_questions": follow_up_questions,
            "quick_replies": quick_replies,
            "streaming": streaming,
            "conversation_state": state.to_api_payload(),
            "context_compression": compression,
            "tone_profile": tone,
            "calibration": calibration,
            "physiological_grounding": awareness,
        }

    def _quick_replies(
        self,
        context: DialogueContext,
        snapshot: MemorySnapshot,
        follow_up_questions: list[str],
    ) -> list[str]:
        replies: list[str] = []
        if follow_up_questions:
            replies.append("Tell me what changed")
        if snapshot.symptom.baseline_signals:
            replies.append("Compare with my baseline")
        if snapshot.symptom.recovery_trajectory:
            replies.append("What should I monitor")
        if context.mode == "expert":
            replies.append("Show the deeper analysis")
        return replies[:3]
