# AI-Powered Cross-Language Knowledge Transfer Platform
### Project & IEEE Paper Preparation Document

---

## 1. Problem Validity Analysis (Multi-Perspective)

### 1.1 Industry / Enterprise Perspective
Multinational organizations routinely lose fidelity when technical knowledge crosses languages. A specification, safety manual, or API document translated by a generic MT engine can silently mistranslate a controlled term (an alloy grade, a regulatory clause, a method name), because the translator has no persistent memory of how that organization has always rendered that term. Production multilingual-RAG guidance from 2025–2026 explicitly calls this out: glossaries must be versioned and pinned at ingest time, or term consistency across a knowledge base is lost when the glossary changes.

### 1.2 Research / Academic Perspective
Cross-lingual research collaboration faces the same failure at corpus scale — a Chinese and an English paper on the same subfield may use inconsistent renderings of the same concept, breaking literature search, citation linking, and reproducibility across language communities.

### 1.3 Technical / Linguistic Perspective
This is an active, unsolved research problem, not a solved one that a general LLM already handles:
- The WMT25 Terminology Translation shared task exists specifically because current MT/LLM systems cannot guarantee that required terminology constraints are respected in the output, even when a term dictionary or a large-LLM annotator is used to augment training data.
- Terminology-constrained MT (TC-MT) is treated as a distinct subfield with its own metrics — Term-Usage/Success Rate (fraction of required term pairs present in the output), typically targeting >95% for strong systems, evaluated alongside BLEU/chrF/COMET for fluency.
- Effective terminology-resource construction is described as crucial specifically in domains with evolving terminology or high out-of-vocabulary risk (new scientific fields, emerging regulations), which is exactly the enterprise/research setting this project targets.

### 1.4 Economic Perspective
Human technical translation and localization is slow and expensive. Existing tooling (SDL Trados, memoQ, static translation memory) is mature but not adaptive, not LLM-native, and requires manual glossary curation — a real cost center for multinational engineering, pharma, and manufacturing firms.

### 1.5 Verdict
The problem is real, current tooling (generic MT, static glossaries, vanilla LLM prompting) is demonstrably insufficient per current literature, and it is an active 2025–2026 research area (COLING 2025, EMNLP 2025, WMT25, multiple Springer venues). This makes it a legitimate, defensible final-year project with a real gap to publish against — provided the contribution goes beyond a wrapper around an existing translation API.

---

## 2. Why Naive Solutions Fail (Gap Analysis)

| Gap | Why current systems fail here |
|---|---|
| No terminology guarantee | Constraint-injection methods improve term usage but don't guarantee it; the main disadvantage of current constraint methods is the lack of guarantee that all constraints are respected in translation. |
| Static glossaries | Manually maintained term lists don't evolve; nobody auto-updates them from corrections in production. |
| No cross-document consistency | Per-request translation calls have no memory across documents or time; the same term can be rendered three different ways in three different files. |
| No confidence signal | Systems don't know when they're unsure, so they can't cheaply route only the risky terms to a human reviewer — it's all-or-nothing automation or all-manual review. |
| "Adapt" is usually skipped | Most systems translate; almost none adapt reading level/expertise *and* language together, despite this being explicitly part of the original problem statement. |
| Privacy in enterprise deployment | Sending proprietary technical documents to third-party MT APIs is a governance problem multinational organizations actually face; solutions that keep the terminology KG on-premises/federated address this directly. |

---

## 2A. Closest Competing System (Verified — Update as of Sept 2026)

A full-text check of recent literature surfaced a deployed system close enough to this proposal that it must be addressed explicitly, not discovered later by a reviewer:

**Di Rosa, E. (2026). "Multi-Agent Orchestration for Terminology-Constrained Machine Translation in Industrial Localization." ACL 2026 Industry Track, pp. 917–926.**

**What it does:** AIDA_term is a deployed, production system using four sequential role-specialized agents (Analysis → Translation → Post-editing → Review). It achieves 99.4% terminology accuracy on the WMT25 Terminology Translation benchmark (Track 1, en→de/es/ru, IT domain), outperforming all 20 submitted systems, and is shown to be driven by pipeline architecture rather than model capability (even older-generation models beat the field). It processes thousands of terminology-constrained requests daily at a real localization provider.

**Confirmed NOT present in AIDA_term (verified from full paper text, not just the abstract):**
- The termbase/glossary is a **static, per-project input** supplied by the client and cleaned per batch — it does not update itself from reviewer corrections across sessions.
- Human review in production is **full/uniform** (a two-stage post-edit + independent review on every segment in their hardest domain), not gated by a per-term confidence score.
- No reader-expertise-level adaptation — their Analysis agent profiles audience/competence only to guide translation register, not to produce differently-adapted outputs.

**Implication for this project:**
1. Do **not** position "using a multi-agent translator/verifier/review pipeline" as your novelty — it is already published and deployed at high accuracy.
2. Do **not** attempt to beat AIDA_term's term-accuracy numbers on the same WMT25 IT-domain benchmark — 99.4% is close to saturated for that benchmark, and it is a deployed industrial system, not a fair target for a final-year project's headline metric.
3. **Do** position novelty specifically around: (a) a self-updating terminology memory across jobs, (b) confidence-gated (not uniform) human review, (c) expertise-adaptive summarization. All three are absent from the closest published competitor, based on the full paper text.
4. **Reusable finding for your own design:** AIDA_term found that batch-level terminology processing dropped accuracy by 22 percentage points versus per-segment processing — agents implicitly "resolve" a term once and silently drop it elsewhere in the batch. Process terminology per segment in your own pipeline regardless of architecture.
5. The authors released prompt templates and outputs at `github.com/emanueledirosa/aida_t-acl2026-industrytrack` (unverified content — check license and contents yourself before use) and offer research access to the system; this is a plausible source for a static-glossary baseline/control condition rather than building one from scratch.

---

## 3. Proposed Novel Contribution

> **A self-evolving, domain-specific Terminology Knowledge Graph, verified by a multi-agent translation pipeline, with confidence-gated human-in-the-loop correction, driving both terminology-faithful translation and expertise-adaptive summarization.**

This is a synthesis of three separate active research threads (terminology-constrained MT, multilingual RAG/knowledge-graph grounding, and multi-agent LLM verification), not a wrapper around a single API call. Three specific novel elements — each explicitly checked against the closest published system, AIDA_term (§2A), and confirmed absent there as of the full-text review:

### 3.0 Research Gap (Confirmed Version)

**Existing research:**
→ AIDA_term (Di Rosa, ACL 2026) establishes that a role-specialized, sequential multi-agent pipeline with per-segment glossary injection achieves state-of-the-art terminology accuracy on WMT25, and is deployed in production with full human review of every segment.

**Limitation:**
→ The termbase is a fixed, per-project input; human review effort is uniform across all output rather than targeted by confidence; and the system optimizes translation quality without adapting the same content to different reader-expertise levels.

**Our approach:**
→ Extend a role-specialized multi-agent pipeline with (a) a terminology knowledge graph that updates from reviewer corrections and persists across translation jobs, (b) a per-term confidence score that determines whether human review is needed at all, and (c) a downstream summarization stage that adapts translated content to stated reader-expertise levels.

**Contribution (to be measured, not yet claimed):**
→ Whether term-usage accuracy on repeated/recurring terms improves across correction rounds without re-supplying a termbase, and whether confidence-gating reduces reviewed-segment volume relative to full manual review at matched accuracy.

**Research question:**
→ *Given a role-specialized multi-agent translation pipeline, does making the termbase self-updating and gating human review by confidence improve terminology consistency across repeated jobs while reducing reviewed volume, compared to a static-termbase baseline modeled on AIDA_term's published configuration?*

### 3.0.1 Contributions (measurable, not yet evidenced — each maps to an experiment in §5)

1. A self-updating terminology knowledge graph construction method that converts human reviewer corrections into persistent, versioned KG updates — measured by term-usage accuracy on repeated terms across correction rounds 1 through N.
2. A confidence-gating mechanism that routes only low-confidence term translations to human review — measured by % of terms requiring review vs. a full-manual-review baseline, at matched or better term-usage accuracy.
3. An empirical comparison against a static-glossary multi-agent baseline (architecture modeled on AIDA_term's published design, since its code/data cannot be assumed reusable without verification) isolating whether *self-updating* specifically, not just "using multiple agents," drives any accuracy improvement.
4. An expertise-adaptive summarization layer evaluated independently of translation quality, showing translation-fidelity and reader-appropriateness metrics don't degrade each other when combined in one pipeline.
5. *(Conditional on 1–4 landing cleanly)* A released domain-specific terminology evaluation set (200–500 terms, chosen domain, 2–3 language pairs), since public benchmarks are thin outside WMT/IT-domain English-centric data.

**Scope discipline:** contributions 1–3 are the paper. 4 is a differentiator worth doing well or not at all. 5 is bonus credibility, not a substitute for 1–3 producing a real result.

### 3.1 Living Terminology Knowledge Graph (not a static glossary)
- Auto-extracts candidate domain terms from ingested documents (NER + domain-adapted term extraction).
- Stores each term as a node: `term → definition → approved translation per language → version history → confidence/provenance`.
- **Self-updates**: every human correction becomes new training/constraint data, closing a loop that current TC-MT literature still treats as a one-time resource-construction step.

### 3.2 Multi-Agent Verification with Calibrated Confidence
- **Translator agent** proposes the translation.
- **Terminology-verifier agent** checks output against the KG (symbolic constraint check, not just soft prompting).
- **Domain-critic agent** flags semantic drift / mistranslation risk using a second independent LLM pass.
- Output receives a **calibrated confidence score per term**; only low-confidence spans are routed to a human reviewer — this is the efficiency argument over full-manual review and the quality argument over full-automatic MT.

### 3.3 Expertise-Adaptive Summarization (the "adapts" requirement)
- The same source content is restructured for a novice vs. an expert reader *in the target language*, not just translated at a fixed complexity level — directly answering the "adapts domain-specific knowledge" clause of the original problem statement, which most competing systems ignore.

### 3.4 (Optional stretch novelty) Privacy-preserving deployment
- Keep the terminology KG and raw documents on-premises per organization; only anonymized/abstracted queries or embeddings leave the boundary — mirrors recent multi-agent LLM work on privacy-preserving technical query translation for enterprise settings.

---

## 4. System Architecture

```
Source technical documents
        |
        v
Terminology extraction  --------------------->  Living Terminology
(NER + term candidate                            Knowledge Graph
 mining, domain-adapted)                         (per-domain, versioned)
        |                                                ^
        v                                                |
Multi-agent translation                                  |
 - Translator agent                                      |
 - Terminology-verifier agent  <------------------------ | (constraint lookup)
 - Domain-critic agent                                   |
        |                                                |
        v                                                |
Confidence-gated human review  ------------------------->+
 (only low-confidence terms                    (correction → new KG entry)
  routed to a human expert)
        |
        v
Adaptive multilingual output
 (tuned to target language AND reader expertise level)
```

**Suggested stack:**
- LLM core: open model fine-tuned for constrained decoding (Qwen3 / Gemma3) or API-based (Claude/GPT) with a terminology-constraint layer.
- Knowledge graph: Neo4j or similar graph DB for the living terminology store.
- Retrieval: cross-lingual embeddings + reranker (e.g., BGE-m3 / multilingual cross-encoder) for grounding translation/summarization in the correct source passages.
- Orchestration: multi-agent framework (LangGraph / custom agent loop) for translator → verifier → critic pipeline.
- Frontend: web app for document upload, side-by-side translation view, human-review queue, glossary dashboard.

---

## 5. Evaluation Plan

**Build your own evaluation set** (public terminology benchmarks are thin outside WMT and mostly English-centric): 200–500 domain terms across 2–3 language pairs, drawn from one chosen technical domain (recommend picking ONE domain — e.g., mechanical engineering specs, or medical device manuals — rather than "all technical knowledge," to keep scope final-year-sized).

**Proposed composite metric — Term Fidelity Score (your paper's empirical contribution):**
- Term-Usage/Success Rate (required terms correctly present) — compare against ≥95% benchmark reported for strong existing TC-MT systems.
- Fluency: BLEU / chrF / COMET.
- New: **Adaptation Appropriateness Score** — human or LLM-judged fit of output to the stated reader-expertise level.

**Key ablation (your strongest, most citable result):** show the Term Fidelity Score improves over successive correction rounds as the KG self-updates — i.e., the system demonstrably gets better with use, which most static-glossary systems cannot claim.

**Baselines to compare against:** raw Google Translate/DeepL, vanilla GPT-4/Claude prompted translation (no KG), a standard terminology-injection baseline (dictionary-prompted MT, following prior TC-MT work), and a static-glossary multi-agent baseline modeled on AIDA_term's published four-agent configuration (Analysis→Translation→Post-editing→Review with per-segment glossary injection, no self-update, no confidence gating) — this last baseline is what makes contributions 1–2 (§3.0.1) actually demonstrable, since it isolates the effect of self-updating and confidence-gating from "just using multiple agents."

**Do not evaluate primarily on WMT25 Track 1 (en→de/es/ru, IT domain).** AIDA_term already reports 99.4% terminology accuracy there, beating all 20 submitted systems — that benchmark is close to saturated and is not a fair target for a final-year project's headline result. Pick a domain WMT25 doesn't cover for your primary evaluation; if you want a sanity check against the literature, report WMT25 numbers as a secondary reference point only.

**Design note carried over from AIDA_term's ablations:** process terminology constraints per segment, not in a batch — their ablation found batch-level term processing dropped accuracy by 22 percentage points because agents implicitly resolve a term once and silently drop it elsewhere in the batch. This applies regardless of your own architecture.

---

## 6. Suggested IEEE Paper Framing

**Working title options:**
- "A Self-Evolving Terminology Knowledge Graph with Multi-Agent Verification for Terminology-Faithful Technical Translation"
- "Confidence-Gated Human-in-the-Loop Translation for Cross-Lingual Technical Knowledge Transfer"
- "Beyond Translation: Multi-Agent, Expertise-Adaptive Cross-Language Knowledge Sharing for Multinational Organizations"

**Suggested paper structure:**
1. Introduction — motivate with the enterprise/research knowledge-loss problem (Section 1 above).
2. Related Work — TC-MT (WMT25, terminology-constrained MT surveys), multilingual RAG/knowledge-graph grounding, multi-agent LLM pipelines. **AIDA_term (Di Rosa, ACL 2026 Industry Track) must be cited and explicitly differentiated as the closest published system** — see §2A for the exact differentiation points, verified against its full text, not just its abstract.
3. System Design — living KG + multi-agent pipeline + adaptive summarization (Section 3–4).
4. Evaluation Methodology — Term Fidelity Score, dataset construction, baselines (Section 5).
5. Results — term-usage rate over correction rounds (the self-improvement ablation is your headline figure), fluency comparison, human evaluation of adaptation quality.
6. Discussion — limitations (domain scope, cold-start KG problem, cost of human review at scale), privacy/deployment considerations.
7. Conclusion & Future Work.

**Why this is publishable at final-year level:** it's a systems + empirical evaluation paper (common, accepted IEEE conference format), it engages directly with 2025–2026 literature gaps (self-updating glossary, confidence-gated review loop, combined adaptation), and it has a clear, falsifiable claim (Term Fidelity Score improves with correction rounds) rather than just "we built a translation app."

---

## 7. Scope Recommendation for a Final-Year Team

- Pick **one** technical domain and **2–3** language pairs — do not attempt general-purpose "all knowledge."
- Build the living KG and multi-agent verification loop first — this is the novel core and the empirical contribution.
- Treat the expertise-adaptive summarization as a secondary, differentiating feature, not the primary engineering focus.
- Budget real time for building your own evaluation set (this is normal for TC-MT research — public benchmarks are limited).

---

## 8. Key Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Cold-start: KG has no terms at project start | Seed from an existing domain glossary/standard (e.g., an industry terminology standard for your chosen domain) before live extraction begins. |
| Human review bottleneck | Confidence gating should route only a small fraction (target <15%) of terms to review — validate this ratio empirically as a result, not an assumption. |
| Scope creep into "general AI translator" | Explicitly scope to one domain; frame breadth as future work, not a deliverable. |
| Evaluation set too small for statistical significance | Report confidence intervals; supplement automatic metrics with structured human evaluation (even 2–3 domain-expert reviewers materially strengthens the paper). |

---

*Grounding note: claims about the current state of terminology-constrained MT, multilingual RAG glossary consistency, and multi-agent translation research reflect published work from COLING 2025, EMNLP 2025, WMT25, and related 2025–2026 venues, current as of September 2026. The AIDA_term analysis (§2A) is based on a direct read of the full ACL 2026 Industry Track paper (Di Rosa, 2026, pp. 917–926, doi: 10.18653/v1/2026.acl-industry.63), not just its abstract. Its GitHub repository (`github.com/emanueledirosa/aida_t-acl2026-industrytrack`) was referenced in the paper but its contents have not been independently verified — check it directly before relying on it as a baseline source.*
