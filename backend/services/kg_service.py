import json
import uuid
import re
import math
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from backend.database import get_db

# ─────────────────────────────────────────────────────────────
# Seed Domain Terminology (Comprehensive Multilingual Seed)
# Domains: cloud_computing, distributed_systems, biomedical_devices
# Languages: en -> hi (Hindi), ta (Tamil), de (German), es (Spanish)
# ─────────────────────────────────────────────────────────────
SEED_TERMS = [
    # Cloud & Distributed Systems
    {
        "source_term": "fault tolerance",
        "domain": "cloud_computing",
        "definition": "The ability of a distributed system to continue operating properly in the event of failure of some components.",
        "translations": {
            "hi": "त्रुटि सहिष्णुता",
            "ta": "பிழை சகிப்புத்தன்மை",
            "de": "Fehlertoleranz",
            "es": "tolerancia a fallos"
        },
        "confidence": 0.98
    },
    {
        "source_term": "load balancer",
        "domain": "cloud_computing",
        "definition": "A reverse-proxy device or software that distributes network or application traffic across a cluster of servers.",
        "translations": {
            "hi": "भार संतुलनकर्ता",
            "ta": "சுமை சமநிலைப்படுத்தி",
            "de": "Lastverteiler",
            "es": "balanceador de carga"
        },
        "confidence": 0.97
    },
    {
        "source_term": "horizontal scaling",
        "domain": "cloud_computing",
        "definition": "Adding more nodes or machines to a distributed system pool to handle increasing computational demand.",
        "translations": {
            "hi": "क्षैतिज स्केलिंग",
            "ta": "கிடைமட்ட அளவிடுதல்",
            "de": "horizontale Skalierung",
            "es": "escalabilidad horizontal"
        },
        "confidence": 0.96
    },
    {
        "source_term": "circuit breaker",
        "domain": "distributed_systems",
        "definition": "A design pattern used to detect failures and prevent cascading errors across microservices.",
        "translations": {
            "hi": "सर्किट ब्रेकर पैटर्न",
            "ta": "மின்சுற்று முறிப்பான் முறை",
            "de": "Schutzschalter-Muster",
            "es": "patrón disyuntor"
        },
        "confidence": 0.95
    },
    {
        "source_term": "eventual consistency",
        "domain": "distributed_systems",
        "definition": "A consistency model guaranteeing that, if no new updates are made to an item, all replicas will eventually return the last updated value.",
        "translations": {
            "hi": "अंतिम संगति",
            "ta": "இறுதி நிலைத்தன்மை",
            "de": "schließliche Konsistenz",
            "es": "consistencia eventual"
        },
        "confidence": 0.94
    },
    {
        "source_term": "container orchestration",
        "domain": "cloud_computing",
        "definition": "Automated management, deployment, scaling, and networking of software containers.",
        "translations": {
            "hi": "कंटेनर ऑर्केस्ट्रेशन",
            "ta": "கொள்கலன் ஒருங்கிணைப்பு",
            "de": "Container-Orchestrierung",
            "es": "orquestación de contenedores"
        },
        "confidence": 0.96
    },
    {
        "source_term": "rate limiting",
        "domain": "cloud_computing",
        "definition": "A strategy for limiting network traffic by capping how often a user or client can repeat an action within a specified timeframe.",
        "translations": {
            "hi": "दर सीमांकन",
            "ta": "விகித வரம்பு",
            "de": "Ratenbegrenzung",
            "es": "limitación de tasa"
        },
        "confidence": 0.98
    },
    {
        "source_term": "service mesh",
        "domain": "distributed_systems",
        "definition": "A dedicated infrastructure layer for facilitating service-to-service communications using sidecar proxies.",
        "translations": {
            "hi": "सेवा जाल",
            "ta": "சேவை வலைப்பின்னல்",
            "de": "Service-Mesh",
            "es": "malla de servicios"
        },
        "confidence": 0.95
    },
    {
        "source_term": "idempotency",
        "domain": "distributed_systems",
        "definition": "A property of certain operations in mathematics and computer science whereby they can be applied multiple times without changing the result beyond the initial application.",
        "translations": {
            "hi": "समसामयिकता (इडेंपोटेंसी)",
            "ta": "மாறா விளைவுத்தன்மை",
            "de": "Idempotenz",
            "es": "idempotencia"
        },
        "confidence": 0.97
    },
    {
        "source_term": "cache invalidation",
        "domain": "cloud_computing",
        "definition": "A process where entries in a cache are actively cleared or replaced when the underlying data changes.",
        "translations": {
            "hi": "कैश अमान्यकरण",
            "ta": "தற்காலிக நினைவக செல்லாததாக்கல்",
            "de": "Cache-Invalidierung",
            "es": "invalidación de caché"
        },
        "confidence": 0.94
    },
    {
        "source_term": "dead-letter queue",
        "domain": "distributed_systems",
        "definition": "A specialized message queue service designed to hold messages that cannot be successfully processed by consumer endpoints.",
        "translations": {
            "hi": "असंसाधित संदेश पंक्ति (डेड-लेटर क्यू)",
            "ta": "செயலாக்க முடியாத செய்தி வரிசை",
            "de": "Dead-Letter-Warteschlange",
            "es": "cola de mensajes no entregados"
        },
        "confidence": 0.95
    },
    {
        "source_term": "consensus protocol",
        "domain": "distributed_systems",
        "definition": "A fault-tolerant algorithm used in distributed systems to achieve agreement among multiple nodes.",
        "translations": {
            "hi": "सर्वसम्मति प्रोटोकॉल",
            "ta": "ஒருங்கிணைந்த ஒருமித்த நெறிமுறை",
            "de": "Konsensprotokoll",
            "es": "protocolo de consenso"
        },
        "confidence": 0.96
    },

    # Biomedical Devices & Medical Engineering
    {
        "source_term": "positive end-expiratory pressure",
        "domain": "biomedical_devices",
        "definition": "The pressure in the lungs above atmospheric pressure that exists at the end of expiration during mechanical ventilation.",
        "translations": {
            "hi": "सकारात्मक अंतिम-उच्छ्वास दबाव (पीईईपी)",
            "ta": "நேர்மறை மூச்சு வெளிவிடு அழுத்தம்",
            "de": "positiver endexspiratorischer Druck (PEEP)",
            "es": "presión positiva al final de la espiración (PEEP)"
        },
        "confidence": 0.99
    },
    {
        "source_term": "tidal volume",
        "domain": "biomedical_devices",
        "definition": "The lung volume representing the normal volume of air displaced between normal inhalation and exhalation when extra effort is not applied.",
        "translations": {
            "hi": "ज्वारीय आयतन (टाइडल वॉल्यूम)",
            "ta": "மூச்சுக்காற்று கொள்ளளவு",
            "de": "Atemzugvolumen",
            "es": "volumen corriente"
        },
        "confidence": 0.98
    },
    {
        "source_term": "pulse oximetry",
        "domain": "biomedical_devices",
        "definition": "A noninvasive method for monitoring a person's peripheral blood oxygen saturation.",
        "translations": {
            "hi": "पल्स ऑक्सीमेट्री",
            "ta": "நாடி ஆக்சிஜன் அளவீடு",
            "de": "Pulsoxymetrie",
            "es": "pulsioximetría"
        },
        "confidence": 0.98
    },
    {
        "source_term": "biocompatibility",
        "domain": "biomedical_devices",
        "definition": "The property of a material being compatible with living tissue or a living system by not being toxic or causing immunological rejection.",
        "translations": {
            "hi": "जैव अनुकूलता",
            "ta": "உயிரியல் இணக்கத்தன்மை",
            "de": "Biokompatibilität",
            "es": "biocompatibilidad"
        },
        "confidence": 0.97
    },
    {
        "source_term": "hemodialysis",
        "domain": "biomedical_devices",
        "definition": "A medical procedure to remove waste products and excess fluid from the blood when the kidneys stop functioning.",
        "translations": {
            "hi": "रक्त अपोहन (हेमोडायलिसिस)",
            "ta": "இரத்த சுத்திகரிப்பு முறை",
            "de": "Hämodialyse",
            "es": "hemodiálisis"
        },
        "confidence": 0.99
    },
    {
        "source_term": "capnography",
        "domain": "biomedical_devices",
        "definition": "The continuous monitoring of the concentration or partial pressure of carbon dioxide in the respiratory gases.",
        "translations": {
            "hi": "कैप्नोग्राफी",
            "ta": "கார்பன் டை ஆக்சைடு அளவீடு",
            "de": "Kapnografie",
            "es": "capnografía"
        },
        "confidence": 0.96
    },
    {
        "source_term": "defibrillator shock",
        "domain": "biomedical_devices",
        "definition": "A therapeutic dose of electrical energy delivered to the heart during cardiac dysrhythmias.",
        "translations": {
            "hi": "डिफाइब्रिलेटर विद्युत झटका",
            "ta": "இதய அதிர்வு மீட்பு மின்னதிர்ச்சி",
            "de": "Defibrillationsschock",
            "es": "descarga de desfibrilador"
        },
        "confidence": 0.98
    },
    {
        "source_term": "barotrauma",
        "domain": "biomedical_devices",
        "definition": "Physical tissue damage caused by a pressure difference between an unvented body space and the ambient gas or fluid.",
        "translations": {
            "hi": "बैरोट्रॉमा (दाब आघात)",
            "ta": "அழுத்த அதிர்ச்சி காயம்",
            "de": "Barotrauma",
            "es": "barotrauma"
        },
        "confidence": 0.97
    }
]


SEED_RELATIONSHIPS = [
    ("circuit breaker", "fault tolerance", "SUBCLASS_OF", 0.98),
    ("load balancer", "fault tolerance", "CONTEXT_OF", 0.95),
    ("dead-letter queue", "circuit breaker", "CONTEXT_OF", 0.92),
    ("consensus protocol", "fault tolerance", "CONTEXT_OF", 0.96),
    ("horizontal scaling", "load balancer", "CONTEXT_OF", 0.94),
    ("service mesh", "circuit breaker", "CONTEXT_OF", 0.93),
    ("idempotency", "fault tolerance", "CONTEXT_OF", 0.95),
    ("cache invalidation", "eventual consistency", "CONTEXT_OF", 0.91),
    ("tidal volume", "mechanical ventilator", "SUBCLASS_OF", 0.97),
    ("positive end-expiratory pressure", "mechanical ventilator", "SUBCLASS_OF", 0.96),
    ("arterial blood pressure", "hemodynamic monitoring", "SUBCLASS_OF", 0.98),
    ("pulse oximeter", "hemodynamic monitoring", "CONTEXT_OF", 0.95),
]

class KnowledgeGraphService:
    def __init__(self):
        from backend.database import init_db
        init_db()
        self.seed_database_if_empty()

    def seed_database_if_empty(self):
        from backend.database import get_utc_now_iso
        now = get_utc_now_iso()
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM terms")
            count = cursor.fetchone()["count"]
            if count == 0:
                for item in SEED_TERMS:
                    term_id = str(uuid.uuid4())
                    cursor.execute("""
                        INSERT INTO terms (id, source_term, domain, definition, translations_json, version, confidence, status, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, 1, ?, 'APPROVED', ?, ?)
                    """, (
                        term_id,
                        item["source_term"].lower().strip(),
                        item["domain"],
                        item["definition"],
                        json.dumps(item["translations"], ensure_ascii=False),
                        item["confidence"],
                        now,
                        now
                    ))
                    # Add initial audit log
                    cursor.execute("""
                        INSERT INTO term_audit_log (id, term_id, version, action, changed_by, new_value_json, reviewer_notes, timestamp)
                        VALUES (?, ?, 1, 'SEED_CREATION', 'SYSTEM_INITIALIZER', ?, 'Initial domain ontology seed', ?)
                    """, (
                        str(uuid.uuid4()),
                        term_id,
                        json.dumps(item["translations"], ensure_ascii=False),
                        now
                    ))

            # Seed ontological relationships if empty
            cursor.execute("SELECT COUNT(*) as rel_count FROM term_relationships")
            rel_count = cursor.fetchone()["rel_count"]
            if rel_count == 0:
                for src_name, tgt_name, rel_type, rel_conf in SEED_RELATIONSHIPS:
                    cursor.execute("SELECT id FROM terms WHERE source_term = ?", (src_name.lower(),))
                    src_row = cursor.fetchone()
                    cursor.execute("SELECT id FROM terms WHERE source_term = ?", (tgt_name.lower(),))
                    tgt_row = cursor.fetchone()
                    if src_row and tgt_row:
                        cursor.execute("""
                            INSERT INTO term_relationships (id, source_term_id, target_term_id, relation_type, confidence, created_at)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (str(uuid.uuid4()), src_row["id"], tgt_row["id"], rel_type, rel_conf, now))

    def get_all_terms(self, domain: Optional[str] = None, search: Optional[str] = None) -> List[Dict[str, Any]]:
        with get_db() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM terms WHERE 1=1"
            params = []
            if domain and domain != "all":
                query += " AND domain = ?"
                params.append(domain)
            if search:
                query += " AND (source_term LIKE ? OR definition LIKE ?)"
                params.extend([f"%{search}%", f"%{search}%"])
            query += " ORDER BY source_term ASC"
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            for row in rows:
                row["translations"] = json.loads(row["translations_json"])
            return rows

    def get_term_by_id(self, term_id: str) -> Optional[Dict[str, Any]]:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM terms WHERE id = ?", (term_id,))
            row = cursor.fetchone()
            if not row:
                return None
            row["translations"] = json.loads(row["translations_json"])
            
            # Fetch audit history
            cursor.execute("SELECT * FROM term_audit_log WHERE term_id = ? ORDER BY version DESC", (term_id,))
            row["audit_history"] = cursor.fetchall()
            return row

    def extract_candidate_terms(self, text: str, domain: str = "cloud_computing") -> List[Dict[str, Any]]:
        """
        Auto-extracts candidate domain terms from text:
        1. Identifies existing approved Knowledge Graph terms in the text.
        2. Detects new uncataloged technical acronyms (e.g. ACID, SLA, PEEP).
        3. Extracts multi-word technical compounds and noun phrases using linguistic patterns & C-Value ranking.
        """
        text_lower = text.lower()
        candidates = []
        seen_terms = set()

        # Step 1: Match against known terms in Knowledge Graph
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM terms WHERE domain = ? OR domain = 'cloud_computing'", (domain,))
            known_terms = cursor.fetchall()

            for kt in known_terms:
                st = kt["source_term"]
                pattern = r'\b' + re.escape(st) + r'\b'
                matches = list(re.finditer(pattern, text_lower))
                if matches and st not in seen_terms:
                    translations = json.loads(kt["translations_json"])
                    candidates.append({
                        "id": kt["id"],
                        "source_term": kt["source_term"],
                        "domain": kt["domain"],
                        "definition": kt["definition"],
                        "translations": translations,
                        "version": kt["version"],
                        "confidence": kt["confidence"],
                        "occurrences": len(matches),
                        "is_new": False
                    })
                    seen_terms.add(st)

        # Step 2: Extract uppercase acronyms (e.g., PEEP, REST, ACID, SLO, SLA, MTBF)
        acronym_matches = re.findall(r'\b[A-Z]{2,6}\b', text)
        stop_acronyms = {"THE", "AND", "FOR", "NOT", "ALL", "NEW", "ANY"}
        for acr in set(acronym_matches):
            if acr in stop_acronyms:
                continue
            acr_low = acr.lower()
            if acr_low not in seen_terms:
                candidates.append({
                    "id": None,
                    "source_term": acr,
                    "domain": domain,
                    "definition": f"Extracted technical acronym ({acr})",
                    "translations": {"hi": acr, "ta": acr, "de": acr, "es": acr},
                    "version": 0,
                    "confidence": 0.75,
                    "occurrences": text.count(acr),
                    "is_new": True
                })
                seen_terms.add(acr_low)

        # Step 3: Linguistic Noun-Phrase & Compound Term Extraction with C-Value Scoring
        # Technical adjective and noun modifiers
        tech_modifiers = {
            "distributed", "concurrent", "stateless", "stateful", "asynchronous",
            "synchronous", "byzantine", "fault", "load", "dead", "consensus",
            "cache", "service", "event", "stream", "micro", "neural", "biomedical",
            "arterial", "cardiac", "continuous", "active", "passive", "immutable",
            "eventual", "high", "low", "dynamic", "static", "resilient"
        }
        tech_head_suffixes = (
            "tion", "sion", "ment", "ance", "ence", "ity", "ing", "er", "or",
            "ism", "ics", "logy", "ware", "base", " mesh", " queue", " pool"
        )
        tech_stop_words = {
            "this", "that", "these", "those", "each", "every", "some", "many",
            "more", "most", "such", "other", "another", "good", "great", "high level"
        }

        # Match 2-word and 3-word potential candidate phrases: [Modifier]+ [Head]
        words = re.findall(r'\b[a-zA-Z\-]{3,}\b', text_lower)
        phrase_counts: Dict[str, int] = {}

        # 2-grams
        for i in range(len(words) - 1):
            w1, w2 = words[i], words[i + 1]
            if w1 in tech_modifiers or any(w2.endswith(sfx) for sfx in tech_head_suffixes):
                phrase = f"{w1} {w2}"
                if phrase not in tech_stop_words:
                    phrase_counts[phrase] = phrase_counts.get(phrase, 0) + 1

        # Hyphenated compounds (e.g., dead-letter, zero-trust, round-robin)
        hyphen_matches = re.findall(r'\b[a-zA-Z]{3,}-[a-zA-Z]{3,}\b', text_lower)
        for h in hyphen_matches:
            if h not in tech_stop_words:
                phrase_counts[h] = phrase_counts.get(h, 0) + 1

        # C-Value calculation for multi-word phrases: C-Value = log2(|phrase| + 1) * freq
        for phrase, freq in phrase_counts.items():
            if phrase in seen_terms:
                continue
            
            # Check if phrase is substring of already seen known term
            if any(phrase in st for st in seen_terms):
                continue

            word_len = len(phrase.split())
            c_value = math.log2(word_len + 1) * freq
            
            # Filter threshold: minimum C-Value of 1.0
            if c_value >= 1.0:
                conf = round(min(0.85, 0.60 + 0.05 * c_value), 2)
                candidates.append({
                    "id": None,
                    "source_term": phrase,
                    "domain": domain,
                    "definition": f"Candidate multi-word term extracted via C-Value analysis ({c_value:.2f})",
                    "translations": {},
                    "version": 0,
                    "confidence": conf,
                    "occurrences": freq,
                    "is_new": True
                })
                seen_terms.add(phrase)

        return sorted(candidates, key=lambda x: (not x["is_new"], -x["occurrences"]))

    def find_uncovered_terms(self, source_segment: str, domain: str, target_lang: str) -> List[Dict[str, Any]]:
        """Detects domain terms present in the segment for which the KG has NO target-language
        translation yet. lookup_constraints() only returns terms it can already translate, so a
        term missing target-language coverage is currently invisible to the verifier/confidence
        pipeline -- this method closes that blind spot."""
        source_lower = source_segment.lower()
        uncovered = []
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM terms WHERE (domain = ? OR domain = 'cloud_computing')", (domain,)
            )
            terms = cursor.fetchall()
            for t in terms:
                st = t["source_term"]
                pattern = r'\b' + re.escape(st) + r'\b'
                if re.search(pattern, source_lower):
                    translations = json.loads(t["translations_json"])
                    if target_lang not in translations:
                        uncovered.append({"term_id": t["id"], "source_term": st})
        return uncovered

    def lookup_constraints(self, source_segment: str, domain: str, target_lang: str) -> List[Dict[str, Any]]:
        """
        Retrieves segment-level terminology constraints for a specific target language.
        Crucial per ACL 2026 (AIDA_term finding: segment-level injection avoids 22% batch accuracy drop).
        """
        source_lower = source_segment.lower()
        constraints = []
        
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM terms WHERE (domain = ? OR domain = 'cloud_computing') AND status = 'APPROVED'", (domain,))
            terms = cursor.fetchall()
            
            for t in terms:
                st = t["source_term"]
                pattern = r'\b' + re.escape(st) + r'\b'
                if re.search(pattern, source_lower):
                    translations = json.loads(t["translations_json"])
                    target_term = translations.get(target_lang)
                    if target_term:
                        constraints.append({
                            "term_id": t["id"],
                            "source_term": st,
                            "target_term": target_term,
                            "target_lang": target_lang,
                            "version": t["version"],
                            "confidence": t["confidence"]
                        })
        return constraints

    def apply_human_correction(
        self,
        source_term: str,
        target_lang: str,
        corrected_translation: str,
        domain: str = "cloud_computing",
        reviewer_notes: str = "Human expert review update",
        term_id: Optional[str] = None,
        reviewer_id: str = "SYSTEM_REVIEWER",
        reviewer_role: str = "REVIEWER",
        target_confidence: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        CONTROLLED KG UPDATE WITH ANTI-POISONING:
        Applies a verified human correction to the Living Terminology Knowledge Graph:
        - Validates input format and cleans target term
        - Increments version number (v -> v+1)
        - Computes controlled confidence based on reviewer role (Admin: 0.98, Reviewer: 0.95, explicit override if provided)
        - Logs full provenance and audit trail with reviewer ID and timestamp
        - Resolves matching review_queue entries
        """
        source_clean = source_term.lower().strip()
        trans_clean = corrected_translation.strip()
        from datetime import timezone
        now = datetime.now(timezone.utc).isoformat()
        
        # Calculate controlled confidence (prevent instant 1.0 poisoning)
        if target_confidence is not None:
            assigned_conf = max(0.50, min(0.99, float(target_confidence)))
        elif reviewer_role == "ADMIN":
            assigned_conf = 0.98
        elif reviewer_role == "REVIEWER":
            assigned_conf = 0.95
        else:
            assigned_conf = 0.70
        
        with get_db() as conn:
            cursor = conn.cursor()
            
            # Find existing term or create new
            if term_id:
                cursor.execute("SELECT * FROM terms WHERE id = ?", (term_id,))
            else:
                cursor.execute("SELECT * FROM terms WHERE source_term = ? AND domain = ?", (source_clean, domain))
            
            existing = cursor.fetchone()
            
            if existing:
                term_id = existing["id"]
                current_version = existing["version"]
                new_version = current_version + 1
                translations = json.loads(existing["translations_json"])
                old_translations = dict(translations)
                
                # Update translation for target_lang
                translations[target_lang] = trans_clean
                
                cursor.execute("""
                    UPDATE terms
                    SET translations_json = ?,
                        version = ?,
                        confidence = ?,
                        status = 'APPROVED',
                        approved_by = ?,
                        updated_at = ?
                    WHERE id = ?
                """, (
                    json.dumps(translations, ensure_ascii=False),
                    new_version,
                    assigned_conf,
                    reviewer_id,
                    now,
                    term_id
                ))
                
                # Log audit history with authenticated reviewer ID
                cursor.execute("""
                    INSERT INTO term_audit_log (id, term_id, version, action, changed_by, old_value_json, new_value_json, reviewer_notes, timestamp)
                    VALUES (?, ?, ?, 'HUMAN_CORRECTION', ?, ?, ?, ?, ?)
                """, (
                    str(uuid.uuid4()),
                    term_id,
                    new_version,
                    reviewer_id,
                    json.dumps(old_translations, ensure_ascii=False),
                    json.dumps(translations, ensure_ascii=False),
                    reviewer_notes,
                    now
                ))
                
            else:
                # Create brand new verified term node
                term_id = str(uuid.uuid4())
                new_version = 1
                translations = {target_lang: trans_clean}
                cursor.execute("""
                    INSERT INTO terms (id, source_term, domain, definition, translations_json, version, confidence, status, created_by, approved_by, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, 1, ?, 'APPROVED', ?, ?, ?, ?)
                """, (
                    term_id,
                    source_clean,
                    domain,
                    f"Domain term verified by reviewer ({reviewer_role})",
                    json.dumps(translations, ensure_ascii=False),
                    assigned_conf,
                    reviewer_id,
                    reviewer_id,
                    now,
                    now
                ))
                
                cursor.execute("""
                    INSERT INTO term_audit_log (id, term_id, version, action, changed_by, new_value_json, reviewer_notes, timestamp)
                    VALUES (?, ?, 1, 'HUMAN_NEW_TERM', ?, ?, ?, ?)
                """, (
                    str(uuid.uuid4()),
                    term_id,
                    reviewer_id,
                    json.dumps(translations, ensure_ascii=False),
                    reviewer_notes,
                    now
                ))
            
            # Resolve any matching pending items in review queue
            valid_user_fk = None
            if reviewer_id:
                cursor.execute("SELECT id FROM users WHERE id = ?", (reviewer_id,))
                if cursor.fetchone():
                    valid_user_fk = reviewer_id

            cursor.execute("""
                UPDATE review_queue
                SET status = 'RESOLVED',
                    reviewed_by = ?,
                    resolved_at = ?,
                    reviewer_comment = ?
                WHERE (term_id = ? OR term_text = ?) AND target_lang = ? AND status = 'PENDING'
            """, (
                valid_user_fk,
                now,
                f"Resolved via verified update by {reviewer_role} to '{trans_clean}'",
                term_id,
                source_clean,
                target_lang
            ))
            
            return {
                "term_id": term_id,
                "source_term": source_clean,
                "domain": domain,
                "target_lang": target_lang,
                "approved_translation": trans_clean,
                "new_version": new_version,
                "confidence": assigned_conf,
                "reviewer_id": reviewer_id,
                "reviewer_role": reviewer_role,
                "status": "APPROVED",
                "timestamp": now
            }

    def rollback_term(self, term_id: str, target_version: int, reviewer_id: str, reason: str = "Rollback to prior version") -> Dict[str, Any]:
        """
        Anti-Poisoning Rollback: Reverts a term to an earlier recorded version in term_audit_log.
        """
        from datetime import timezone
        now = datetime.now(timezone.utc).isoformat()
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM terms WHERE id = ?", (term_id,))
            term = cursor.fetchone()
            if not term:
                raise ValueError(f"Term {term_id} not found.")

            cursor.execute("SELECT * FROM term_audit_log WHERE term_id = ? AND version = ?", (term_id, target_version))
            target_audit = cursor.fetchone()
            if not target_audit:
                raise ValueError(f"Audit log for version {target_version} of term {term_id} not found.")

            restored_translations = target_audit["new_value_json"]
            new_version = term["version"] + 1

            cursor.execute("""
                UPDATE terms
                SET translations_json = ?,
                    version = ?,
                    confidence = 0.90,
                    updated_at = ?
                WHERE id = ?
            """, (restored_translations, new_version, now, term_id))

            cursor.execute("""
                INSERT INTO term_audit_log (id, term_id, version, action, changed_by, old_value_json, new_value_json, reviewer_notes, timestamp)
                VALUES (?, ?, ?, 'ROLLBACK', ?, ?, ?, ?, ?)
            """, (
                str(uuid.uuid4()),
                term_id,
                new_version,
                reviewer_id,
                term["translations_json"],
                restored_translations,
                f"Rollback to v{target_version}: {reason}",
                now
            ))

            return {
                "term_id": term_id,
                "restored_version": target_version,
                "new_version": new_version,
                "translations": json.loads(restored_translations),
                "timestamp": now
            }

    def stage_candidate_term(self, source_term: str, domain: str, target_lang: str, proposed_translation: str, user_id: str, definition: Optional[str] = None) -> Dict[str, Any]:
        """
        Stages an unverified term proposal from standard users with status='CANDIDATE' and low confidence.
        Requires reviewer approval before injection into translation constraints.
        """
        from datetime import timezone
        now = datetime.now(timezone.utc).isoformat()
        source_clean = source_term.lower().strip()
        trans_clean = proposed_translation.strip()
        term_id = str(uuid.uuid4())
        translations = {target_lang: trans_clean}

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM terms WHERE source_term = ? AND domain = ?", (source_clean, domain))
            if cursor.fetchone():
                raise ValueError("Term already exists in Knowledge Graph.")

            cursor.execute("""
                INSERT INTO terms (id, source_term, domain, definition, translations_json, version, confidence, status, created_by, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, 1, 0.50, 'CANDIDATE', ?, ?, ?)
            """, (
                term_id,
                source_clean,
                domain,
                definition or "Proposed candidate term awaiting expert verification",
                json.dumps(translations, ensure_ascii=False),
                user_id,
                now,
                now
            ))

            cursor.execute("""
                INSERT INTO term_audit_log (id, term_id, version, action, changed_by, new_value_json, reviewer_notes, timestamp)
                VALUES (?, ?, 1, 'USER_CANDIDATE_SUBMISSION', ?, ?, 'Staged for reviewer verification', ?)
            """, (
                str(uuid.uuid4()),
                term_id,
                user_id,
                json.dumps(translations, ensure_ascii=False),
                now
            ))

        return {
            "term_id": term_id,
            "source_term": source_clean,
            "domain": domain,
            "status": "CANDIDATE",
            "confidence": 0.50,
            "created_by": user_id
        }

    def export_graph_json(self, domain: Optional[str] = None) -> Dict[str, Any]:
        """
        Exports the Knowledge Graph into a nodes-and-links format for visual exploration.
        """
        terms = self.get_all_terms(domain=domain)
        nodes = []
        links = []
        
        # Domain root nodes
        domains_found = set(t["domain"] for t in terms)
        for d in domains_found:
            nodes.append({
                "id": f"domain_{d}",
                "name": d.replace("_", " ").title(),
                "group": "domain",
                "size": 25
            })

        for t in terms:
            node_id = f"term_{t['id']}"
            nodes.append({
                "id": node_id,
                "name": t["source_term"],
                "group": "term",
                "domain": t["domain"],
                "version": t["version"],
                "confidence": t["confidence"],
                "translations": t["translations"],
                "size": 15 + min(t["version"] * 3, 15)
            })
            
            # Link from domain to term
            links.append({
                "source": f"domain_{t['domain']}",
                "target": node_id,
                "type": "IN_DOMAIN"
            })
            
            # Target language translation nodes (selected)
            for lang, trans in t["translations"].items():
                lang_node_id = f"trans_{t['id']}_{lang}"
                nodes.append({
                    "id": lang_node_id,
                    "name": f"{trans} ({lang.upper()})",
                    "group": "translation",
                    "lang": lang,
                    "size": 10
                })
                links.append({
                    "source": node_id,
                    "target": lang_node_id,
                    "type": "TRANSLATES_TO"
                })

        # Inter-term ontological relationships
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT r.source_term_id, r.target_term_id, r.relation_type, r.confidence
                FROM term_relationships r
            """)
            rels = cursor.fetchall()
            for r in rels:
                links.append({
                    "source": f"term_{r['source_term_id']}",
                    "target": f"term_{r['target_term_id']}",
                    "type": r["relation_type"],
                    "confidence": r["confidence"]
                })

        return {"nodes": nodes, "links": links}


kg_service = KnowledgeGraphService()
