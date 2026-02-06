import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64
import json
import time

# --- 1. CONFIGURATION ---
CODE_ACT = "20082008"
CODE_MASTER = "B2008a2020@"

if not firebase_admin._apps:
    try:
        encoded = st.secrets["firebase_key"]["encoded_key"].strip()
        decoded_json = base64.b64decode(encoded).decode("utf-8")
        cred = credentials.Certificate(json.loads(decoded_json))
        firebase_admin.initialize_app(cred)
    except: pass

db = firestore.client()
doc_ref = db.collection("memoire").document("profil_monsieur")
client = Groq(api_key="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")

# --- 2. ÉTATS DE SESSION ---
if "messages" not in st.session_state: 
    st.session_state.messages = [{"role": "assistant", "content": "Système DELTA activé. Prêt à vous servir, Monsieur SEZER. ⚡"}]
if "auth" not in st.session_state: st.session_state.auth = False
if "locked" not in st.session_state: st.session_state.locked = False

# --- 3. CHARGEMENT MÉMOIRE ---
res = doc_ref.get()
data = res.to_dict() if res.exists else {"faits": []}
faits = data.get("faits", [])

# --- 4. SÉCURITÉ LOCKDOWN ---
if st.session_state.locked:
    st.error("🚨 SYSTÈME BLOQUÉ")
    m_input = st.text_input("CODE MAÎTRE :", type="password")
    if st.button("DÉBLOQUER"):
        if m_input == CODE_MASTER:
            st.session_state.locked = False
            st.rerun()
    st.stop()

# --- 5. FONCTION D'ÉCRITURE PROGRESSIVE (STREAMING) ---
def generer_reponse(prompt):
    instr = (
        "Tu es DELTA IA, le majordome discret de Monsieur SEZER. "
        "Ne récite JAMAIS tes archives sans demande explicite. "
        "Réponds de manière concise et efficace. "
        f"Archives : {faits}. "
        "Si tu apprends une info, termine par 'ACTION_ARCHIVE: [info]'."
    )
    
    stream = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "system", "content": instr}] + st.session_state.messages,
        stream=True # On active le flux
    )
    
    full_response = ""
    for chunk in stream:
        content = chunk.choices[0].delta.content
        if content:
            full_response += content
            yield content # On envoie chaque morceau un par un

# --- 6. INTERFACE ---
st.markdown("<h1 style='color:#00d4ff;'>⚡ DELTA IA</h1>", unsafe_allow_html=True)

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

if prompt := st.chat_input("Vos ordres, Monsieur SEZER ?"):
    # Affichage immédiat du message utilisateur
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Logique de sécurité simple
    p_low = prompt.lower()
    if "verrouille" in p_low:
        st.session_state.locked = True
        st.rerun()

    # Traitement de la réponse avec effet d'écriture
    with st.chat_message("assistant"):
        placeholder = st.empty()
        # On utilise le générateur pour l'effet "frappe au clavier"
        response = st.write_stream(generer_reponse(prompt))
        
        # Gestion discrète de l'archivage après l'écriture
        if "ACTION_ARCHIVE:" in response:
            info = response.split("ACTION_ARCHIVE:")[1].strip()
            if info not in faits:
                faits.append(info)
                doc_ref.set({"faits": faits}, merge=True)
                st.toast("Note enregistrée.", icon="📝")
            response = response.split("ACTION_ARCHIVE:")[0].strip()
            placeholder.markdown(response) # On nettoie l'affichage final

    st.session_state.messages.append({"role": "assistant", "content": response})

# --- 7. AUTHENTIFICATION ---
if any(w in (prompt or "").lower() for w in ["archive", "mémoire"]):
    if not st.session_state.auth:
        with st.chat_message("assistant"):
            st.warning("🔒 Validation requise.")
            c = st.text_input("Code :", type="password")
            if st.button("Valider"):
                if c == CODE_ACT:
                    st.session_state.auth = True
                    st.rerun()
