import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64, json, hashlib
from datetime import datetime

# --- INITIALISATION FIREBASE ---
if not firebase_admin._apps:
    try:
        encoded = st.secrets["firebase_key"]["encoded_key"].strip()
        decoded_json = base64.b64decode(encoded).decode("utf-8")
        cred_dict = json.loads(decoded_json)
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"Erreur Firebase : {e}")
        st.stop()

db = firestore.client()
USER_ID = "monsieur_sezer"

# --- INITIALISATION GROQ ---
client = Groq(api_key="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")

# --- FONCTION DE RÉCUPÉRATION MULTI-BRANCHES ---
def get_all_archives():
    archives = {}
    try:
        # On liste les sous-collections du document utilisateur
        collections = db.collection("archives").document(USER_ID).collections()
        for col in collections:
            docs = col.order_by("created_at", direction=firestore.Query.DESCENDING).limit(3).stream()
            archives[col.id] = [d.to_dict() for d in docs]
        return archives
    except:
        return {}

# --- INTERFACE ---
st.set_page_config(page_title="DELTA AGI", page_icon="🌐", layout="wide")
st.title("🌐 DELTA : Système Jarvis Opérationnel")

# Chargement du contexte global
all_memories = get_all_archives()

with st.sidebar:
    st.header("🗂️ Branches Archives")
    if not all_memories:
        st.info("Initialisation requise...")
    for branch, items in all_memories.items():
        with st.expander(f"📁 {branch}"):
            for item in items:
                st.caption(f"• {item.get('content')[:50]}...")

if "messages" not in st.session_state:
    # PAR DÉFAUT : Delta engage la conversation
    st.session_state.messages = [{"role": "assistant", "content": "À vos ordres, Monsieur Sezer. Le système est en ligne. Que souhaitez-vous structurer aujourd'hui ?"}]

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# --- PROCESSUS COGNITIF ---
if prompt := st.chat_input("Répondez à Jarvis..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    # 1. ANALYSE ET RÉPARTITION DANS LES BRANCHES
    try:
        analysis = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "Tu es l'architecte de données de Monsieur Sezer. Catégorise l'info. Réponds en JSON: {'branch': 'NOM_BRANCHE', 'is_worthy': bool}"},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        res = json.loads(analysis.choices[0].message.content)

        if res.get("is_worthy"):
            branch_name = res.get("branch", "Général")
            m_hash = hashlib.sha256(prompt.encode()).hexdigest()
            
            # Écriture dans la branche spécifique
            db.collection("archives").document(USER_ID).collection(branch_name).document(m_hash).set({
                "content": prompt,
                "created_at": datetime.utcnow()
            }, merge=True)
            st.toast(f"🧬 Donnée injectée dans la branche {branch_name}")
    except Exception as e:
        st.warning(f"Note: Analyse de branche ignorée ({e})")

    # 2. RÉPONSE JARVIS (CONCISE & DIRECTE)
    with st.chat_message("assistant"):
        context_summary = str(all_memories)[:500] # On injecte un condensé des archives
        sys_instr = (
            f"Tu es Jarvis. Ton créateur est Monsieur Sezer. "
            f"Contexte des branches : {context_summary}. "
            "Parle-lui directement. Sois concis, intelligent, et toujours prêt à servir."
        )
        
        try:
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "system", "content": sys_instr}] + st.session_state.messages[-5:]
            ).choices[0].message.content
            
            st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})
        except Exception as e:
            st.error(f"Erreur Groq : {e}")

    st.rerun()
