import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64
import json

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="DELTA IA", page_icon="⚡", layout="centered")

# --- 2. INITIALISATION SERVICES ---
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

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

# --- 3. CHARGEMENT DES ARCHIVES ---
res = doc_ref.get()
data = res.to_dict() if res.exists else {"faits": []}
faits = data.get("faits", [])

# --- 4. INTERFACE DE CHAT ---
st.markdown("<h1 style='color:#00d4ff;'>⚡ DELTA IA</h1>", unsafe_allow_html=True)

if "messages" not in st.session_state:
    st.session_state.messages = []

# Affichage des messages
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# --- 5. LOGIQUE DE CHAT ET SÉCURITÉ DYNAMIQUE ---
if p := st.chat_input("Quels sont vos ordres, Monsieur ?"):
    st.session_state.messages.append({"role": "user", "content": p})
    with st.chat_message("user"):
        st.markdown(p)

    # DÉTECTION D'ACTION SENSIBLE (Archives ou Contrôle PC)
    mots_cles = ["archive", "mémoire", "souviens", "ordinateur", "pc", "ouvrir", "commande"]
    est_sensible = any(mot in p.lower() for mot in mots_cles)

    if est_sensible and not st.session_state["authenticated"]:
        with st.chat_message("assistant"):
            st.warning("🔒 Cette action nécessite une autorisation de niveau Administrateur.")
            code_input = st.text_input("Veuillez entrer le code secret :", type="password", key="secu_input")
            if st.button("Valider"):
                if code_input == "20082008":
                    st.session_state["authenticated"] = True
                    st.success("Accès autorisé. Relancez votre commande, Monsieur.")
                    st.rerun()
                else:
                    st.error("Code incorrect.")
    else:
        # RÉPONSE DE L'IA
        with st.chat_message("assistant"):
            instr = (
                "Tu es DELTA IA. Tu as accès à ces archives : {faits}. "
                "Si l'utilisateur n'est pas authentifié, refuse de donner des détails précis sur les archives. "
                "Si l'info est importante, ajoute 'ACTION_ARCHIVE: [info]' à la fin."
            )
            
            r = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "system", "content": instr}] + st.session_state.messages
            )
            
            rep = r.choices[0].message.content
            
            # Gestion Archivage
            if "ACTION_ARCHIVE:" in rep:
                partie_archive = rep.split("ACTION_ARCHIVE:")[1].strip()
                if partie_archive not in faits:
                    faits.append(partie_archive)
                    doc_ref.update({"faits": faits})
                    st.toast(f"Mémorisé : {partie_archive}", icon="🧠")
                rep = rep.split("ACTION_ARCHIVE:")[0].strip()

            st.markdown(rep)
            st.session_state.messages.append({"role": "assistant", "content": rep})
