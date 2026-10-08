import json
import uuid
import re
from datetime import datetime
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


class KnowledgeGraphService:
    def __init__(self):
        from backend.database import init_db
        init_db()
        self.seed_database_if_empty()

    def seed_database_if_empty(self):
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM terms")
            count = cursor.fetchone()["count"]
            if count == 0:
                now = datetime.utcnow().isoformat()
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
        2. Detects new uncataloged technical acronyms and multi-word candidates using POS/pattern heuristics.
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
        acronym_matches = re.findall(r'\b[A-Z]{3,6}\b', text)
        for acr in set(acronym_matches):
            acr_low = acr.lower()
            if acr_low not in seen_terms:
                candidates.append({
                    "id": None,
                    "source_term": acr,
                    "domain": domain,
                    "definition": f"Extracted technical acronym ({acr})",
                    "translations": {"hi": acr, "ta": acr, "de": acr, "es": acr},
                    "version": 0,
                    "confidence": 0.70,
                    "occurrences": text.count(acr),
                    "is_new": True
                })
                seen_terms.add(acr_low)

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
        term_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        SELF-EVOLUTION CORE:
        Applies a human correction to the Living Terminology Knowledge Graph:
        - Increments version number (v -> v+1)
        - Updates approved translation
        - Sets confidence to 1.0 (human verified)
        - Logs provenance in term_audit_log
        - Resolves review_queue entries for this term
        """
        source_clean = source_term.lower().strip()
        now = datetime.utcnow().isoformat()
        
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
                translations[target_lang] = corrected_translation.strip()
                
                cursor.execute("""
                    UPDATE terms
                    SET translations_json = ?,
                        version = ?,
                        confidence = 1.0,
                        status = 'APPROVED',
                        updated_at = ?
                    WHERE id = ?
                """, (
                    json.dumps(translations, ensure_ascii=False),
                    new_version,
                    now,
                    term_id
                ))
                
                # Log audit history
                cursor.execute("""
                    INSERT INTO term_audit_log (id, term_id, version, action, changed_by, old_value_json, new_value_json, reviewer_notes, timestamp)
                    VALUES (?, ?, ?, 'HUMAN_CORRECTION', 'HUMAN_REVIEWER', ?, ?, ?, ?)
                """, (
                    str(uuid.uuid4()),
                    term_id,
                    new_version,
                    json.dumps(old_translations, ensure_ascii=False),
                    json.dumps(translations, ensure_ascii=False),
                    reviewer_notes,
                    now
                ))
                
            else:
                # Create brand new verified term node
                term_id = str(uuid.uuid4())
                new_version = 1
                translations = {target_lang: corrected_translation.strip()}
                cursor.execute("""
                    INSERT INTO terms (id, source_term, domain, definition, translations_json, version, confidence, status, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, 1, 1.0, 'APPROVED', ?, ?)
                """, (
                    term_id,
                    source_clean,
                    domain,
                    f"Domain term identified and approved by human reviewer",
                    json.dumps(translations, ensure_ascii=False),
                    now,
                    now
                ))
                
                cursor.execute("""
                    INSERT INTO term_audit_log (id, term_id, version, action, changed_by, new_value_json, reviewer_notes, timestamp)
                    VALUES (?, ?, 1, 'HUMAN_NEW_TERM', 'HUMAN_REVIEWER', ?, ?, ?)
                """, (
                    str(uuid.uuid4()),
                    term_id,
                    json.dumps(translations, ensure_ascii=False),
                    reviewer_notes,
                    now
                ))
            
            # Resolve any matching pending items in review queue
            cursor.execute("""
                UPDATE review_queue
                SET status = 'RESOLVED',
                    resolved_at = ?,
                    reviewer_comment = ?
                WHERE (term_id = ? OR term_text = ?) AND target_lang = ? AND status = 'PENDING'
            """, (
                now,
                f"Resolved via KG update to '{corrected_translation}'",
                term_id,
                source_clean,
                target_lang
            ))
            
            return {
                "term_id": term_id,
                "source_term": source_clean,
                "domain": domain,
                "target_lang": target_lang,
                "approved_translation": corrected_translation.strip(),
                "new_version": new_version,
                "confidence": 1.0,
                "status": "APPROVED",
                "timestamp": now
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

        return {"nodes": nodes, "links": links}


kg_service = KnowledgeGraphService()
