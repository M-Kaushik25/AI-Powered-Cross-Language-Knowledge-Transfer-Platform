"""
Real evaluation harness for the Living Terminology Knowledge Graph + Multi-Agent pipeline.

METHODOLOGY (read this before trusting any number this file produces):

1. Gold standard: target-language translations come from SEED_TERMS in kg_service.py —
   the same domain-expert-curated terminology used to originally build the KG. Using this
   as the reference for simulated reviewer corrections is standard MT-evaluation practice
   (a reference/gold set), not fabricated data. It should still be spot-checked by an actual
   bilingual domain reviewer before being cited in a paper as ground truth.

2. Cold-start simulation: for a chosen domain + target language, this harness temporarily
   *removes* that language's translation from the KG for the terms under test, producing a
   genuine "the organization hasn't localized this glossary into this language yet" state.
   This is necessary because the KG ships pre-seeded with high-confidence translations for
   all five languages — without artificially creating a cold start, there is nothing for the
   self-update loop to demonstrably improve.

3. What this DOES measure honestly: whether missing/incorrect KG coverage causes real
   term-verification failures and confidence-gated review routing (it does), and whether
   applying corrections through the real `apply_human_correction()` path measurably improves
   term-usage rate on a second pass (it does, because the deterministic offline translator
   injects whatever the KG currently says).

4. What this does NOT measure in offline mode (no GEMINI_API_KEY): actual translation
   fluency/adequacy. The offline deterministic translator injects the KG's exact target term
   by string substitution — so in offline mode, term accuracy is a coverage question, not a
   translation-quality question. Any "fluency" figure below is the Domain-Critic agent's
   heuristic score (length ratio / placeholder / punctuation checks only) — NOT a substitute
   for BLEU/chrF/COMET or human fluency judgment, and it is labeled as such, not as "fluency."

5. Set GEMINI_API_KEY and re-run to get genuine LLM-driven translation and critic scoring —
   at that point the critic score becomes a real (if still LLM-self-reported, not human-
   verified) quality signal, and this docstring's caveat in point 4 no longer applies.

This file replaces a previous version whose `run_comprehensive_ablation()` returned literal
hardcoded numbers and never touched the actual pipeline. Everything below is computed from
real calls into kg_service and multi_agent_service.
"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional

from backend.database import get_db
from backend.services.kg_service import kg_service, SEED_TERMS
from backend.services.multi_agent_service import multi_agent_service

BENCHMARK_SENTENCES = [
    {"id": 1, "en": "Fault tolerance is essential for modern cloud infrastructure to prevent downtime.",
     "terms": ["fault tolerance"], "domain": "cloud_computing"},
    {"id": 2, "en": "A reliable load balancer manages traffic distribution and horizontal scaling across clusters.",
     "terms": ["load balancer", "horizontal scaling"], "domain": "cloud_computing"},
    {"id": 3, "en": "Implementing a circuit breaker pattern avoids cascading failures under eventual consistency.",
     "terms": ["circuit breaker", "eventual consistency"], "domain": "distributed_systems"},
    {"id": 4, "en": "Container orchestration platforms enforce strict rate limiting and service mesh routing.",
     "terms": ["container orchestration", "rate limiting", "service mesh"], "domain": "cloud_computing"},
    {"id": 5, "en": "Operations must guarantee idempotency to handle dead-letter queue retries effectively.",
     "terms": ["idempotency", "dead-letter queue"], "domain": "distributed_systems"},
    {"id": 6, "en": "Cache invalidation remains a major hurdle during high throughput consensus protocol execution.",
     "terms": ["cache invalidation", "consensus protocol"], "domain": "distributed_systems"},
    {"id": 7, "en": "Mechanical ventilators regulate positive end-expiratory pressure and tidal volume for patient respiration.",
     "terms": ["positive end-expiratory pressure", "tidal volume"], "domain": "biomedical_devices"},
    {"id": 8, "en": "Continuous pulse oximetry and capnography are critical to prevent barotrauma during intubation.",
     "terms": ["pulse oximetry", "capnography", "barotrauma"], "domain": "biomedical_devices"},
    {"id": 9, "en": "Biocompatibility standards ensure safety during repeated hemodialysis treatments.",
     "terms": ["biocompatibility", "hemodialysis"], "domain": "biomedical_devices"},
    {"id": 10, "en": "Defibrillator shock delivery must be synchronized with cardiac telemetry monitoring.",
     "terms": ["defibrillator shock"], "domain": "biomedical_devices"},
]

GOLD = {item["source_term"]: item["translations"] for item in SEED_TERMS}


class EvaluationService:

    def _simulate_cold_start(self, domain: str, target_lang: str, term_list: List[str]) -> int:
        """Strips target_lang from the KG for the given terms, simulating an unlocalized glossary.
        Returns the number of terms actually modified (0 if they were already missing that language,
        which is itself an honest, reportable fact, not something to paper over)."""
        modified = 0
        with get_db() as conn:
            cursor = conn.cursor()
            for term in term_list:
                cursor.execute(
                    "SELECT * FROM terms WHERE source_term = ? AND domain = ?",
                    (term.lower().strip(), domain)
                )
                row = cursor.fetchone()
                if not row:
                    continue
                translations = json.loads(row["translations_json"])
                if target_lang in translations:
                    del translations[target_lang]
                    cursor.execute(
                        "UPDATE terms SET translations_json = ?, confidence = 0.30, updated_at = ? WHERE id = ?",
                        (json.dumps(translations, ensure_ascii=False), datetime.utcnow().isoformat(), row["id"])
                    )
                    modified += 1
        return modified

    def _run_round(self, sentences: List[Dict[str, Any]], target_lang: str) -> Dict[str, Any]:
        """Runs the real multi-agent pipeline on each sentence and independently scores the
        output against each sentence's GOLD-REQUIRED terms (BENCHMARK_SENTENCES['terms']),
        not against the pipeline's own self-reported terms_encountered/terms_verified.

        Why: lookup_constraints() only counts a term if the KG ALREADY has a target-language
        translation for it -- so a term missing from the KG (e.g. during cold start) is
        invisible to the pipeline's own accounting rather than counted as a failure. Scoring
        against the sentences' independently-declared required terms avoids that blind spot
        and is the honest way to measure whether cold start actually hurts and correction
        actually helps."""
        required_total = 0
        required_correct = 0
        total_segments = 0
        total_queued = 0
        confidence_sum = 0.0
        critic_heuristic_sum = 0.0
        critic_count = 0
        job_ids = []

        for sent in sentences:
            job_id = str(uuid.uuid4())
            job_ids.append(job_id)
            result = asyncio.run(multi_agent_service.translate_document(
                source_text=sent["en"], target_lang=target_lang, domain=sent["domain"], job_id=job_id
            ))
            total_segments += result["segment_count"]
            total_queued += result["queued_for_review"]
            confidence_sum += result["avg_confidence"] * result["segment_count"]
            for seg in result["segments"]:
                critic_heuristic_sum += seg["critic_report"]["score"]
                critic_count += 1

            output_lower = result["full_translation"].lower()
            for term in sent["terms"]:
                gold_target = GOLD.get(term, {}).get(target_lang)
                required_total += 1
                if gold_target and gold_target.lower() in output_lower:
                    required_correct += 1

        tsr = round((required_correct / required_total) * 100, 2) if required_total else 100.0
        review_rate = round((total_queued / total_segments) * 100, 2) if total_segments else 0.0
        avg_confidence = round(confidence_sum / total_segments, 4) if total_segments else 0.0
        critic_heuristic_avg = round((critic_heuristic_sum / critic_count) * 100, 2) if critic_count else None

        return {
            "term_usage_rate_percent": tsr,
            "review_rate_percent": review_rate,
            "avg_confidence": avg_confidence,
            "critic_heuristic_score_percent": critic_heuristic_avg,
            "gold_required_terms": required_total,
            "gold_terms_correctly_rendered": required_correct,
            "segments_total": total_segments,
            "segments_queued_for_review": total_queued,
            "job_ids": job_ids,
        }

    def _apply_gold_corrections_for_pending(self, target_lang: str, domain: str) -> int:
        """Resolves PENDING review-queue items by applying the real gold-standard correction
        through the real apply_human_correction() path. Returns count of corrections applied."""
        applied = 0
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM review_queue WHERE status = 'PENDING' AND target_lang = ?",
                (target_lang,)
            )
            pending = cursor.fetchall()

        seen_terms = set()
        for item in pending:
            term_text = item["term_text"]
            if not term_text or term_text == "General Segment Drift":
                continue  # nothing gold-standard to apply; a real human would need to judge this one
            if term_text in seen_terms:
                continue
            gold_translation = GOLD.get(term_text, {}).get(target_lang)
            if not gold_translation:
                continue  # no gold reference available -- honestly skip rather than invent one
            kg_service.apply_human_correction(
                source_term=term_text,
                target_lang=target_lang,
                corrected_translation=gold_translation,
                domain=domain,
                reviewer_notes="Simulated reviewer correction using gold-standard seed terminology (see module docstring)."
            )
            applied += 1
            seen_terms.add(term_text)
        return applied

    def run_comprehensive_ablation(self, domain: str = "cloud_computing", target_lang: str = "hi") -> Dict[str, Any]:
        eval_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()

        sentences = [s for s in BENCHMARK_SENTENCES if s["domain"] == domain]
        term_list = sorted({t for s in sentences for t in s["terms"]})

        terms_reset = self._simulate_cold_start(domain, target_lang, term_list)

        round1 = self._run_round(sentences, target_lang)
        round1["round"] = "Round 1 (Cold Start -- KG missing this language for test terms)"
        round1["terms_reset_for_cold_start"] = terms_reset

        corrections_applied = self._apply_gold_corrections_for_pending(target_lang, domain)

        round2 = self._run_round(sentences, target_lang)
        round2["round"] = "Round 2 (Post-Correction -- gold translations applied via apply_human_correction)"
        round2["corrections_applied"] = corrections_applied

        rounds_data = [round1, round2]

        metrics = {
            "honesty_note": (
                "Numbers are computed from live calls to multi_agent_service.translate_document() "
                "and kg_service.apply_human_correction(). No results are hardcoded. Ran in "
                + ("OFFLINE/DETERMINISTIC mode (no GEMINI_API_KEY) -- term-usage-rate reflects KG "
                   "coverage, not translation fluency; see module docstring." if not multi_agent_service.gemini_api_key
                   else "LIVE mode with Gemini API.")
            ),
            "term_usage_rate_gain_points": round(round2["term_usage_rate_percent"] - round1["term_usage_rate_percent"], 2),
            "review_rate_change_points": round(round2["review_rate_percent"] - round1["review_rate_percent"], 2),
            "corrections_applied": corrections_applied,
        }

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO eval_runs (id, name, domain, rounds_json, metrics_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                eval_id,
                f"Cold-Start Correction Ablation ({domain}, target={target_lang})",
                domain,
                json.dumps(rounds_data),
                json.dumps(metrics),
                now
            ))

        return {"eval_id": eval_id, "created_at": now, "domain": domain, "target_lang": target_lang,
                "rounds": rounds_data, "metrics": metrics}

    def run_zero_kg_baseline(self, domain: str = "cloud_computing", target_lang: str = "hi") -> Dict[str, Any]:
        """Honest lower-bound baseline: what happens with zero terminology coverage at all
        (approximates 'generic MT with no glossary'), permanently, with no correction round."""
        sentences = [s for s in BENCHMARK_SENTENCES if s["domain"] == domain]
        term_list = sorted({t for s in sentences for t in s["terms"]})
        self._simulate_cold_start(domain, target_lang, term_list)
        result = self._run_round(sentences, target_lang)
        result["condition"] = "Zero-KG baseline (no terminology coverage, no correction applied)"
        return result

    def get_latest_eval_run(self) -> Dict[str, Any]:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM eval_runs ORDER BY created_at DESC LIMIT 1")
            row = cursor.fetchone()
            if not row:
                return self.run_comprehensive_ablation()
            return {
                "eval_id": row["id"], "name": row["name"], "domain": row["domain"],
                "rounds": json.loads(row["rounds_json"]), "metrics": json.loads(row["metrics_json"]),
                "created_at": row["created_at"]
            }


eval_service = EvaluationService()
