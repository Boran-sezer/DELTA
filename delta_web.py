import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64, json, hashlib
from datetime import datetime

# --- DIAGNOSTIC DE CONNEXION ---
@st.cache_resource
def init_firebase():
    if not firebase_admin._apps:
        try:
            # On récupère le secret
            encoded = st.secrets["firebase_key"]["encoded_key"].strip()
            decoded_json = base64.b64decode(encoded).decode("utf-8")
            cred_dict = json.loads(decoded_json)
            
            # Correction automatique potentielle de la clé privée
            if "private_key" in cred_dict:
                cred_dict["private_key"] = cred_dict["private_key"].replace("\\n", "\n")
                
            cred = credentials.Certificate(cred_dict)
            return firebase_admin.initialize_app(cred)
        except Exception as e:
            st.error(f"❌ Erreur Critique Firebase : {e}")
            return None
    return firebase_admin.get_app()

app = init_firebase()
db = firestore.client() if app else None
USER_ID = "monsieur_sezer"

# --- TEST D'ÉCRITURE FORCÉ AU DÉMARRAGE ---
if db:
    try:
        test_ref = db.collection("DEBUG").document("test_connexion")
        test_ref.set({"status": "OK", "last_ping": datetime.utcnow()})
        st.sidebar.success("✅ Liaison Firebase : ACTIVE")
    except Exception as e:
        st.sidebar.error(f"❌ Liaison Firebase : ÉCHEC ({e})")

# --- INITIALISATION GROQ ---
client = Groq(api_key="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")

# --- LE RESTE DU CODE (VOTRE LOGIQUE ULTRA) ---
def get_memories():
    if not db: return []
    try:
        docs = db.collection("users").document(USER_ID).collection("memory").order_by("created_at", direction=firestore.Query.DESCENDING).limit(10).stream()
        return [d.to_dict() for d in docs]
    except: return []

st.set_page_config(page_title="DELTA DIAGNOSTIC", layout="wide")
st.title("🌐 DELTA : Analyse du Blocage")

recent_memories = get_memories()

with st.sidebar:
    st.header("📊 État du Système")
    if st.button("🔄 Forcer le Test"):
        st.rerun()

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "En attente de diagnostic, Monsieur Sezer."}]

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

if prompt := st.chat_input("Envoyez un test..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Tentative d'écriture
    if db:
        m_hash = hashlib.sha256(prompt.encode()).hexdigest()
        try:
            db.collection("users").document(USER_ID).collection("memory").document(m_hash).set({
                "content": prompt,
                "created_at": datetime.utcnow(),
                "priority": "high"
            })
            st.toast("🔥 ÉCRITURE RÉUSSIE !")
        except Exception as e:
            st.error(f"L'écriture a échoué : {e}")

    # Réponse Jarvis
    with st.chat_message("assistant"):
        try:
            resp = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "system", "content": "Tu es Jarvis. Réponds court."}] + st.session_state.messages[-3:]
            ).choices[0].message.content
            st.markdown(resp)
            st.session_state.messages.append({"role": "assistant", "content": resp})
        except:
            st.error("Groq ne répond pas.")
    
    st.rerun()
