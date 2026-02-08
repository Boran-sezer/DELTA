import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64, json, hashlib
from datetime import datetime

# --- INITIALISATION ---
if not firebase_admin._apps:
    try:
        encoded = st.secrets["firebase_key"]["encoded_key"].strip()
        decoded_json = base64.b64decode(encoded).decode("utf-8")
        cred = credentials.Certificate(json.loads(decoded_json))
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"Erreur Firebase : {e}")

db = firestore.client()
client = Groq(api_key="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")
USER_ID = "monsieur_sezer"

# --- UTILS (VOTRE SYSTÈME) ---
def hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def is_memory_worthy(text: str) -> bool:
    blacklist = ["salut", "ok", "mdr", "lol", "?", "oui", "non"]
    if len(text.strip()) < 10: # Ajusté pour plus de flexibilité
        return False
    if text.lower().strip() in blacklist:
        return False
    return True

# --- INTERFACE ---
st.set_page_config(page_title="DELTA AGI", page_icon="🌐", layout="wide")
st.title("🌐 DELTA : Système de Mémoire Hachée")

# --- RÉCUPÉRATION MÉMOIRE ---
mem_ref = db.collection("users").document(USER_ID).collection("memory")
memories = mem_ref.order_by("created_at", direction=firestore.Query.DESCENDING).limit(10).stream()
context_list = [m.to_dict() for m in memories]

with st.sidebar:
    st.header("🧠 Mémoire Vive (Hash)")
    for m in context_list:
        st.caption(f"[{m.get('category')}] {m.get('content')}")

if "messages" not in st.session_state:
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# --- CORE PROCESS ---
if prompt := st.chat_input("Ordre direct..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    # 1. TEST DE PERTINENCE (VOTRE SYSTÈME)
    if is_memory_worthy(prompt):
        m_hash = hash_text(prompt)
        
        # 2. ANALYSE IA POUR CATÉGORISATION
        try:
            analysis = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "Tu es un système AGI. Catégorise l'info. Réponds en JSON: {'category': '...'} "},
                    {"role": "user", "content": f"Catégorise ceci : {prompt}"}
                ],
                response_format={"type": "json_object"}
            )
            cat = json.loads(analysis.choices[0].message.content).get("category", "conversation")
            
            # 3. SAUVEGARDE FIREBASE
            ref = mem_ref.document(m_hash)
            if not ref.get().exists:
                ref.set({
                    "category": cat,
                    "content": prompt,
                    "created_at": datetime.utcnow(),
                    "confidence": 0.95
                })
                st.toast("🧬 Nouvelle synapse créée.")
        except Exception as e:
            st.error(f"Erreur mémoire : {e}")

    # 4. RÉPONSE STYLE JARVIS
    with st.chat_message("assistant"):
        context_note = f"Archives récentes : {json.dumps(context_list)}"
        sys_instr = f"Tu es DELTA (Jarvis). {context_note}. Sois concis et efficace."
        
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": sys_instr}] + st.session_state.messages[-5:]
        ).choices[0].message.content
        
        st.markdown(response)
        st.session_state.messages.append({"role": "assistant", "content": response})
        st.rerun()
