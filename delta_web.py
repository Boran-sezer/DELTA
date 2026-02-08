import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64, json

# --- INITIALISATION SÉCURISÉE ---
if not firebase_admin._apps:
    try:
        encoded = st.secrets["firebase_key"]["encoded_key"].strip()
        decoded_json = base64.b64decode(encoded).decode("utf-8")
        cred = credentials.Certificate(json.loads(decoded_json))
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"❌ Erreur d'initialisation Firebase : {e}")

db = firestore.client()
# On pointe sur le document spécifique
doc_ref = db.collection("archives").document("monsieur_sezer")
client = Groq(api_key="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")

# --- CHARGEMENT ---
try:
    res = doc_ref.get()
    archives = res.to_dict() if res.exists else {}
except Exception as e:
    st.error(f"❌ Impossible de lire Firebase : {e}")
    archives = {}

# --- INTERFACE ---
st.set_page_config(page_title="DELTA AGI", page_icon="🌐")
st.title("🌐 DELTA : Diagnostic AGI")

with st.sidebar:
    st.header("🧠 Archives Lux")
    st.write("Statut : " + ("Connecté" if archives else "Vide/Déconnecté"))
    st.json(archives)

if "messages" not in st.session_state:
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# --- MOTEUR D'INJECTION ---
if prompt := st.chat_input("Test d'écriture..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    # 1. ANALYSE COGNITIVE
    try:
        extraction = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": "Tu es une IA forte. Extrais les données en JSON pur."}],
            response_format={"type": "json_object"},
            content=f"Archive ceci : {prompt}. Format: {{'update': {{'categorie': {{'clé': 'valeur'}}}}}}"
        ).choices[0].message.content
        
        brain = json.loads(extraction)
        
        # 2. INJECTION ET CAPTURE D'ERREUR
        if "update" in brain:
            # TENTATIVE D'ÉCRITURE DIRECTE
            try:
                doc_ref.set(brain["update"], merge=True)
                st.success("✅ Données envoyées à Firebase !")
                st.rerun()
            except Exception as fire_err:
                st.error(f"🔥 Erreur Firebase Directe : {fire_err}")
                
    except Exception as ai_err:
        st.error(f"🤖 Erreur IA : {ai_err}")

    # 3. RÉPONSE
    with st.chat_message("assistant"):
        sys_instr = f"Tu es DELTA. Mémoire : {json.dumps(archives)}. Style : Jarvis."
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": sys_instr}] + st.session_state.messages[-5:],
        ).choices[0].message.content
        st.markdown(response)
