import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64, json
from datetime import datetime

# ===============================
# 🔧 INITIALISATION FIREBASE
# ===============================
if not firebase_admin._apps:
    encoded = st.secrets["firebase_key"]["encoded_key"].strip()
    decoded_json = base64.b64decode(encoded).decode("utf-8")
    cred = credentials.Certificate(json.loads(decoded_json))
    firebase_admin.initialize_app(cred)

db = firestore.client()

ARCHIVE_REF = db.collection("archives").document("monsieur_sezer")
EVENTS_REF = db.collection("memories_events")

# ===============================
# 🤖 INITIALISATION LLM (GRATUIT)
# ===============================
client = Groq(api_key=st.secrets["groq"]["api_key"])

# ===============================
# 🧠 CHARGEMENT MÉMOIRE STRUCTURÉE
# ===============================
res = ARCHIVE_REF.get()
archives = res.to_dict() if res.exists else {}

# ===============================
# 🎨 INTERFACE
# ===============================
st.set_page_config("DELTA AGI", "🧠", layout="wide")
st.title("🧠 DELTA — Cognitive Core (Jarvis-like)")

with st.sidebar:
    st.subheader("📚 Mémoire structurée")
    st.json(archives)

    st.subheader("🕯️ Souvenirs récents")
    events = EVENTS_REF.order_by(
        "importance", direction=firestore.Query.DESCENDING
    ).limit(5).stream()
    st.json([e.to_dict() for e in events])

if "messages" not in st.session_state:
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# ===============================
# 💬 INPUT UTILISATEUR
# ===============================
if prompt := st.chat_input("Ordre direct…"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # ===============================
    # 🧠 ANALYSE COGNITIVE (JARVIS CORE)
    # ===============================
    analysis_prompt = f"""
MÉMOIRE ACTUELLE :
{json.dumps(archives, indent=2)}

INPUT UTILISATEUR :
{prompt}

MISSION :
Tu es le noyau cognitif d’une IA type Jarvis.

Analyse l’input et décide si l’information doit être :
- ignorée
- mémorisée (structure)
- mémorisée comme souvenir résumé
- supprimée

RÈGLES ABSOLUES :
- Importance < 0.5 → IGNORE
- Jamais stocker un message brut
- Toujours résumer un souvenir en 1 phrase
- Répondre STRICTEMENT en JSON

FORMAT :
{{
  "decision": "ignore | update | event | delete",
  "importance": 0.0,
  "stability": "short | medium | long",
  "category": "profil | preferences | objectifs",
  "key": "cle_courte",
  "value": "valeur",
  "summary": "résumé cognitif"
}}
"""

    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "Tu es un moteur cognitif strict."},
            {"role": "user", "content": analysis_prompt}
        ],
        response_format={"type": "json_object"}
    )

    brain = json.loads(completion.choices[0].message.content)

    # ===============================
    # ⚙️ EXÉCUTION DÉCISION
    # ===============================
    decision = brain.get("decision")
    importance = brain.get("importance", 0)

    if decision == "update" and importance >= 0.5:
        ARCHIVE_REF.set({
            brain["category"]: {
                brain["key"]: {
                    "value": brain["value"],
                    "importance": importance,
                    "stability": brain["stability"],
                    "updated": datetime.utcnow().isoformat()
                }
            }
        }, merge=True)

    elif decision == "event" and importance >= 0.5:
        EVENTS_REF.add({
            "summary": brain["summary"],
            "importance": importance,
            "date": firestore.SERVER_TIMESTAMP
        })

    elif decision == "delete":
        ARCHIVE_REF.update({
            f"{brain['category']}.{brain['key']}": firestore.DELETE_FIELD
        })

    # ===============================
    # 🧠 RÉCUPÉRATION MÉMOIRE PERTINENTE
    # ===============================
    events = EVENTS_REF.order_by(
        "importance", direction=firestore.Query.DESCENDING
    ).limit(3).stream()

    memory_context = [e.to_dict()["summary"] for e in events]

    profil = archives.get("profil", {})
    nom = profil.get("nom", "Monsieur")

    # ===============================
    # 🤖 RÉPONSE JARVIS
    # ===============================
    sys_prompt = f"""
Tu es DELTA, l’IA personnelle de {nom}.

Tu te souviens de ces faits importants :
{json.dumps(memory_context)}

Tu connais parfaitement son profil et ses objectifs :
{json.dumps(archives)}

STYLE :
- Jarvis
- Calme
- Précis
- Intelligent
- Loyal
Ne récite jamais la mémoire inutilement.
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": sys_prompt},
            *st.session_state.messages[-5:]
        ]
    ).choices[0].message.content

    with st.chat_message("assistant"):
        st.markdown(response)

    st.session_state.messages.append(
        {"role": "assistant", "content": response}
    )
