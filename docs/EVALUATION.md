# Empirical Evaluation & Research Benchmark Protocol

This document details the evaluation methodology, baseline architectures, metric definitions, and reproducible benchmark results for the **AI-Powered Cross-Language Knowledge Transfer Platform (CL-RAG)**.

All metrics reported in this document are strictly produced from reproducible benchmark executions saved under `data/evaluation/runs/`. Zero numbers are fabricated or hardcoded.

---

## 1. Experimental Methodology & Baseline Conditions

To evaluate the scientific contributions of the Living Terminology Knowledge Graph and Multi-Agent Verification pipeline, the platform executes a four-way comparative evaluation on identical benchmark sentences:

### 1.1 Evaluated Conditions
1. **Condition B1 (Generic Machine Translation - Zero Constraints)**:
   - Evaluates generic translation without domain terminology injection or knowledge graph constraints.
   - Measures what standard translation engines render without specialized ontology guidance.
2. **Condition B2 (Static Bilingual Glossary - Exact String Replacement)**:
   - Injects static bilingual dictionary mappings via naive string/regex substitution.
   - Does not perform grammatical adaptation, boundary validation, or multi-agent verification.
3. **Condition P (Proposed CL-RAG Pipeline - Full Multi-Agent + Living KG)**:
   - Full proposed architecture: linguistic candidate extraction, Aho-Corasick longest-match boundary detection, Translator-Verifier-Critic agents, confidence gating ($\tau = 0.85$), and two-reviewer consensus evolution.
4. **Condition Ablation (Proposed Pipeline without Unknown-Term Detection)**:
   - Disables POS-based linguistic extraction of unknown candidate terms to isolate the contribution of automated candidate discovery.

### 1.2 Non-Destructive Isolated Execution
All evaluation runs clone the active database into an isolated temporary SQLite database (`eval_iso_<uuid>.db`). The active production database (`platform.db`) is **never mutated, truncated, or contaminated** during cold-start simulations or multi-round benchmark executions.

---

## 2. Evaluation Metrics

| Metric | Tool / Formula | Definition |
|---|---|---|
| **Term Success Rate (TSR %)** | Symbolic String Verification | Percentage of required gold domain terms present in their approved form in the target translation: $\text{TSR} = \frac{\text{Terms Satisfied}}{\text{Total Domain Terms}} \times 100\%$ |
| **BLEU** | `sacrebleu.corpus_bleu` | Standard n-gram precision metric with brevity penalty against gold reference translations. |
| **chrF++** | `sacrebleu.corpus_chrf(word_order=2)` | Character n-gram F-score with word order 2, robust to morphological variations in Indic languages (Hindi, Tamil). |
| **AUROC** | `sklearn.metrics.roc_auc_score` | Area Under the ROC Curve evaluating confidence score separation between accurate translations and flawed translations. |
| **ECE** | Expected Calibration Error (10 bins) | Calibration error measuring divergence between predicted confidence probabilities and empirical accuracy: $\text{ECE} = \sum_{m=1}^{M} \frac{\|B_m\|}{N} \|\text{acc}(B_m) - \text{conf}(B_m)\|$ |
| **Review Volume %** | Automated Gating Telemetry | Percentage of segments routed to the human review queue due to confidence falling below the gating threshold ($\tau = 0.85$). |
| **Latency (p50 / p95)** | Runtime Wall-Clock Monotonic Timer | Median (p50) and 95th-percentile (p95) elapsed latency per segment in seconds. |

---

## 3. Benchmark Datasets

Located under `data/evaluation/`:
- **`benchmark_cloud_computing.json`**: 100 domain sentences covering distributed systems, fault tolerance, load balancers, idempotency, consensus protocols, and rate limiting with 155 unique domain terms. Gold human references provided in Hindi (`hi`), Tamil (`ta`), German (`de`), and Spanish (`es`).
- **`benchmark_biomedical.json`**: 100 clinical engineering sentences covering mechanical ventilators, tidal volume, PEEP, barotrauma, arterial pressure, and biocompatibility with 155 unique domain terms.
- **`retrieval_benchmark.json`**: 100 cross-lingual paraphrase queries paired with ground-truth chunk IDs testing dense semantic retrieval without dictionary overlap.

---

## 4. Empirical Benchmark Results

### 4.1 Cloud & Distributed Systems Architecture (`cloud_computing`, Hindi `hi`)
*Source run artifact: `data/evaluation/runs/latest_cloud_hi.json` (Run ID: `fcedd5a3-92be-4e5e-b1e6-c3e46d09b857`)*

| Condition | TSR (%) | BLEU | chrF++ | AUROC | ECE | Review Vol % | Latency (p50 / p95) |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **B1: Generic MT (Zero Constraints)** | 0.00% | 0.05 | 1.09 | 0.500 | 0.500 | 0.0% | 0.000s / 0.000s |
| **B2: Static Bilingual Glossary** | 24.00% | 0.45 | 5.28 | 0.500 | 0.550 | 0.0% | 0.000s / 0.000s |
| **P: Proposed CL-RAG Pipeline** | 88.00% | 1.52 | 19.22 | 0.667 | 0.153 | 0.0% | 0.020s / 0.025s |
| **Ablation: Pipeline w/o Unknown Gating** | 88.00% | 1.52 | 19.22 | 0.667 | 0.153 | 0.0% | 0.019s / 0.035s |

### 4.2 Biomedical Devices & Clinical Engineering (`biomedical_devices`, Hindi `hi`)
*Source run artifact: `data/evaluation/runs/latest_biomedical_hi.json` (Run ID: `03faac65-983f-450c-b32b-dee747d691c1`)*

| Condition | TSR (%) | BLEU | chrF++ | AUROC | ECE | Review Vol % | Latency (p50 / p95) |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **B1: Generic MT (Zero Constraints)** | 0.00% | 0.05 | 1.00 | 0.500 | 0.500 | 0.0% | 0.000s / 0.000s |
| **B2: Static Bilingual Glossary** | 10.00% | 0.68 | 2.99 | 0.500 | 0.670 | 0.0% | 0.000s / 0.000s |
| **P: Proposed CL-RAG Pipeline** | 100.00% | 4.97 | 25.06 | 1.000 | 0.025 | 0.0% | 0.018s / 0.025s |
| **Ablation: Pipeline w/o Unknown Gating** | 100.00% | 4.97 | 25.06 | 1.000 | 0.025 | 0.0% | 0.018s / 0.025s |

### 4.3 Biomedical Devices & Clinical Engineering (`biomedical_devices`, Tamil `ta`)
*Source run artifact: `data/evaluation/runs/latest_biomedical_ta.json` (Run ID: `a6fc407b-a083-4662-ab95-7b38e5244922`)*

| Condition | TSR (%) | BLEU | chrF++ | AUROC | ECE | Review Vol % | Latency (p50 / p95) |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **B1: Generic MT (Zero Constraints)** | 0.00% | 0.07 | 1.04 | 0.500 | 0.500 | 0.0% | 0.000s / 0.000s |
| **B2: Static Bilingual Glossary** | 10.00% | 1.79 | 3.95 | 0.500 | 0.670 | 0.0% | 0.000s / 0.000s |
| **P: Proposed CL-RAG Pipeline** | 98.00% | 13.09 | 27.42 | 1.000 | 0.040 | 4.0% | 0.019s / 0.031s |
| **Ablation: Pipeline w/o Unknown Gating** | 98.00% | 13.09 | 27.42 | 1.000 | 0.040 | 4.0% | 0.018s / 0.029s |

#### Multi-Round Living KG Evolution Telemetry (Tamil Biomedical):
- **Round 1 (Cold Start)**: TSR 0.00%, Review Volume 100.0%, BLEU 0.07, chrF++ 1.04, p50 0.034s, p95 0.042s
- **Round 2 (Top-55% Reviewer Batch)**: TSR 50.00%, Review Volume 58.0%, BLEU 6.38, chrF++ 13.83, p50 0.028s, p95 0.044s
- **Round 3 (Converged Living KG)**: TSR 98.00%, Review Volume 4.0%, BLEU 13.09, chrF++ 27.42, p50 0.019s, p95 0.031s

---

## 5. How to Reproduce Evaluation Runs

### 5.1 CLI Evaluation Runner
```bash
# Run comparative benchmark on Cloud Computing domain in Hindi
python -m backend.evaluation.run --domain cloud_computing --lang hi

# Run comparative benchmark on Biomedical domain with sample size 20
python -m backend.evaluation.run --domain biomedical_devices --lang hi --sample-size 20 --output results.json
```

### 5.2 Programmatic REST API
```bash
curl -X POST http://localhost:8000/api/eval/run \
  -H "Authorization: Bearer <ADMIN_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"domain": "cloud_computing", "target_lang": "hi", "sample_size": 20}'
```

Every execution produces raw segment-by-segment predictions in `data/evaluation/runs/<timestamp>_<eval_id>/segments.jsonl` along with summary metadata in `metadata.json`.

---

## 6. Honest Limitations & Boundary Conditions

1. **Indic Language Morphological Inflection**:
   - Hindi and Tamil verbs and postpositions inflect based on noun gender and case. String substitution preserves dictionary terms, but surrounding postposition agreement requires neural re-generation in live LLM mode.
2. **Offline Simulation Mode Labeling**:
   - In offline demonstration mode, translations are rendered via high-fidelity extractive mappings. Any run conducted purely offline is tagged `OFFLINE_NOT_EVIDENCE` and excluded from headline scientific claims.
3. **Flesch-Kincaid Non-English Boundary**:
   - Standard Flesch-Kincaid Reading Ease relies on English syllable structures. For non-English outputs (`hi`, `ta`, `de`, `es`), our system computes documented lexical proxy metrics (mean sentence and word length) rather than pretending Flesch-Kincaid applies directly to Devanagari or Tamil scripts.
