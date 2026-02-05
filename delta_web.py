import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64
import json

# --- CONFIGURATION ---
st.set_page_config(page_title="DELTA OS", page_icon="⚡", layout="wide")

# --- INITIALISATION FIREBASE ---
if not firebase_admin._apps:
    try:
        encoded = st.secrets["firebase_key"]["encoded_key"].strip()
        decoded_json = base64.b64decode(encoded).decode("utf-8")
        creds_dict = json.loads(decoded_json)
        cred = credentials.Certificate(creds_dict)
        firebase_admin.initialize_app(cred)
    except Exception:
        st.error("⚠️ Connexion Mémoire interrompue.")

db = firestore.client()
doc_profil = db.collection("memoire").document("profil_monsieur")
client = Groq(api_key="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")

# --- ÉTATS DE SESSION ---
if "messages" not in st.session_state: st.session_state.messages = []
if "unlocked" not in st.session_state: st.session_state.unlocked = False
if "security_mode" not in st.session_state: st.session_state.security_mode = None
if "attempts" not in st.session_state: st.session_state.attempts = 0
if "pending_data" not in st.session_state: st.session_state.pending_data = None

# --- CHARGEMENT DU PROFIL ---
res_profil = doc_profil.get()
data = res_profil.to_dict() if res_profil.exists else {}
faits_publics = data.get("faits", [])
faits_verrouilles = data.get("faits_verrouilles", [])

# --- SIDEBAR ---
with st.sidebar:
    st.title("🧠 Archives")
    for i, f in enumerate(faits_publics):
        col1, col2 = st.columns([4, 1])
        col1.info(f)
        if col2.button("🗑️", key=f"p_{i}"):
            faits_publics.pop(i)
            doc_profil.update({"faits": faits_publics})
            st.rerun()
    if st.session_state.unlocked:
        st.subheader("🔐 Scellées")
        for i, f in enumerate(faits_verrouilles):
            col1, col2 = st.columns([4, 1])
            col1.warning(f)
            if col2.button("🗑️", key=f"s_{i}"):
                faits_verrouilles.pop(i)
                doc_profil.update({"faits_verrouilles": faits_verrouilles})
                st.rerun()

# --- CHAT ---
for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

if p := st.chat_input("Vos ordres, Monsieur ?"):
    # Nettoyage de l'entrée pour éviter les bugs
    user_input = p.strip()
    low_p = user_input.lower()

    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"): st.markdown(user_input)

    rep = ""

    # --- 1. MODE SÉCURITÉ ACTIF ---
    if st.session_state.security_mode:
        code_normal = "20082008"
        code_secours = "B2008a2020@"
        
        # Choix du code attendu
        attendu = code_normal if st.session_state.attempts < 3 else code_secours
        
        if user_input == attendu:
            mode = st.session_state.security_mode
            if mode == "PURGE":
                doc_profil.set({"faits": [], "faits_verrouilles": []})
                rep = "✅ **ACCÈS MAÎTRE.** Mémoire purgée, Monsieur."
            elif mode == "UNLOCK":
                st.session_state.unlocked = True
                rep = "✅ **COFFRE OUVERT.**"
            # (Ajouter LOCK/DELETE ici si besoin)
            
            st.session_state.security_mode = None
            st.session_state.attempts = 0
        else:
            st.session_state.attempts += 1
            if st.session_state.attempts < 3:
                rep = f"❌ **CODE INCORRECT.** Essai {st.session_state.attempts}/3."
            elif st.session_state.attempts == 3:
                rep = "⚠️ **SÉCURITÉ MAX.** Entrez le code Pro Max (B2008a2020@)."
            else:
                rep = "🚨 **ANNULATION.** Trop d'échecs."
                st.session_state.security_mode = None
                st.session_state.attempts = 0

    # --- 2. DÉTECTION DES ORDRES (DÉCLENCHEMENT) ---
    elif "réinitialisation complète" in low_p:
        st.session_state.security_mode = "PURGE"
        st.session_state.attempts = 0
        rep = "🔒 **CONFIRMATION REQUISE.** Veuillez entrer le code d'accès."

    elif "affiche les archives verrouillées" in low_p:
        st.session_state.security_mode = "UNLOCK"
        st.session_state.attempts = 0
        rep = "🔒 **AUTHENTIFICATION.** Code requis pour ouvrir le coffre."

    # --- 3. RÉPONSE IA NORMALE ---
    else:
        with st.chat_message("assistant"):
            instr = {"role": "system", "content": "Tu es DELTA, majordome fidèle de Monsieur Boran."}
            r = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[instr] + st.session_state.messages)
            rep = r.choices[0].message.content

    with st.chat_message("assistant"):
        st.markdown(rep)
        st.session_state.messages.append({"role": "assistant", "content": rep})
