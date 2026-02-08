import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64, json, hashlib
from datetime import datetime

# --- INITIALISATION FIREBASE ---
if not firebase_admin._apps:
    try:
        # Récupération de la clé Firebase depuis les secrets
        encoded = st.secrets["firebase_key"]["encoded_key"].strip()
        decoded_json = base64.b64decode(encoded).decode("utf-8")
        cred = credentials.Certificate(json.loads(decoded_json))
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"Erreur d'initialisation Firebase : {e}")

db = firestore.client()

# --- INITIALISATION GROQ (Via Secrets) ---
try:
    # Assurez-vous que le nom dans vos secrets Streamlit est bien "GROQ_API_KEY"
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except Exception as e:
    st.error(f"Erreur de clé Groq : {e}")

USER_ID = "monsieur_sezer"

# --- UTILS (VOTRE SYSTÈME DE MÉMOIRE) ---
def hash_text(text: str) -> str:
    """Crée une empreinte unique pour éviter les doublons."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def is_memory_worthy(text: str) -> bool:
    """Filtre les messages trop courts ou inutiles."""
    blacklist = ["salut", "ok", "mdr", "lol", "?", "oui", "non"]
    if len(text.strip()) < 10:
        return False
    if text.lower().strip() in blacklist:
        return False
    return True

# --- INTERFACE ---
st.set_page_config(page_title="DELTA AGI", page_icon="🌐", layout="wide")
st.title("🌐 DELTA : Système AGI + LUX")

# --- RÉCUPÉRATION DU CONTEXTE (SOUS-COLLECTION) ---
mem_ref = db.collection("users").document(USER_ID).collection("memory")
try:
    memories = mem_ref.order_by("created_at", direction=firestore.Query.DESCENDING).limit(10).stream()
    context_list = [m.to_dict() for m in memories]
except:
    context_list = []

with st.sidebar:
    st.header("🧠 Mémoire Vive (SHA-256)")
    for m in context_list:
        st.caption(f"[{m.get('category')}] {m.get('content')}")
    if st.button("Actualiser"):
        st.rerun()

if "messages" not in st.session_state:
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# --- PROCESSUS COGNITIF ---
if prompt := st.chat_input("Ordre direct, Monsieur Sezer..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    # 1. SAUVEGARDE MÉMOIRE (FILTRAGE + HASH)
    if is_memory_worthy(prompt):
        m_hash = hash_text(prompt)
        
        try:
            # IA Forte : Décide de la catégorie intelligemment
            analysis = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "Tu es une IA forte. Catégorise l'info pour le système LUX. Réponds en JSON: {'category': '...'} "},
                    {"role": "user", "content": f"Donne une catégorie courte pour : {prompt}"}
                ],
                response_format={"type": "json_object"}
            )
            cat = json.loads(analysis.choices[0].message.content).get("category", "conversation")
            
            # Injection Firebase si hash unique
            ref = mem_ref.document(m_hash)
            if not ref.get().exists:
                ref.set({
                    "category": cat,
                    "content": prompt,
                    "created_at": datetime.utcnow(),
                    "confidence": 0.95
                })
                st.toast("🧬 Synapse enregistrée.")
        except Exception as e:
            st.error(f"Erreur d'analyse mémoire : {e}")

    # 2. RÉPONSE STYLE JARVIS
    with st.chat_message("assistant"):
        # On injecte les souvenirs réels dans le cerveau de l'IA
        context_str = "\n".join([f"- {m['content']}" for m in context_list])
        sys_instr = (
            f"Tu es DELTA, l'IA de Monsieur Sezer. Ton style est celui de Jarvis.\n"
            f"CONNAISSANCES RÉCENTES :\n{context_str}\n"
            "Sois concis, brillant et utilise tes connaissances pour aider ton créateur."
        )
        
        try:
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "system", "content": sys_instr}] + st.session_state.messages[-5:]
            ).choices[0].message.content
            
            st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})
        except Exception as e:
            st.error(f"Erreur de réponse : {e}")
            
    st.rerun()
