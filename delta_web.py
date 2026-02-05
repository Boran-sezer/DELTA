import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64
import json

# --- CONFIGURATION ---
st.set_page_config(page_title="DELTA OS", page_icon="⚡", layout="wide")

# --- ÉTATS DE SESSION (AVANT TOUT LE RESTE) ---
if "messages" not in st.session_state: st.session_state.messages = []
if "unlocked" not in st.session_state: st.session_state.unlocked = False
if "security_mode" not in st.session_state: st.session_state.security_mode = "NORMAL"
if "attempts" not in st.session_state: st.session_state.attempts = 0
if "pending_action" not in st.session_state: st.session_state.pending_action = None

# --- INITIALISATION FIREBASE ---
if not firebase_admin._apps:
    try:
        encoded = st.secrets["firebase_key"]["encoded_key"].strip()
        decoded_json = base64.b64decode(encoded).decode("utf-8")
        creds_dict = json.loads(decoded_json)
        cred = credentials.Certificate(creds_dict)
        firebase_admin.initialize_app(cred)
    except Exception:
        st.error("⚠️ Système de mémoire déconnecté.")

db = firestore.client()
doc_profil = db.collection("memoire").document("profil_monsieur")

# --- CHARGEMENT DU PROFIL ---
res_profil = doc_profil.get()
data = res_profil.to_dict() if res_profil.exists else {}
faits_publics = data.get("faits", [])
faits_verrouilles = data.get("faits_verrouilles", [])

# --- CONNEXION GROQ ---
client = Groq(api_key="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")

# --- INTERFACE ---
st.title("⚡ DELTA SYSTEM")

with st.sidebar:
    st.title("🧠 Archives")
    st.write(f"Sécurité : {'🔓' if st.session_state.unlocked else '🔒'}")
    for i, f in enumerate(faits_publics):
        st.info(f"{f}")
    if st.session_state.unlocked:
        st.subheader("🔐 Scellées")
        for f in faits_verrouilles:
            st.warning(f)

# --- AFFICHAGE CHAT ---
for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# --- ENTREE UTILISATEUR ---
if p := st.chat_input("Ordres ?"):
    st.session_state.messages.append({"role": "user", "content": p})
    with st.chat_message("user"): st.markdown(p)
    
    rep = ""
    low_p = p.lower().strip()

    # 1. LOGIQUE DE SÉCURITÉ (SI ACTIVÉE)
    if st.session_state.security_mode == "WAITING_CODE":
        code_ok = "20082008"
        code_max = "B2008a2020@"
        
        cible = code_ok if st.session_state.attempts < 3 else code_max
        
        if p == cible:
            # ACTION RÉUSSIE
            act = st.session_state.pending_action
            if act == "PURGE":
                doc_profil.set({"faits": [], "faits_verrouilles": []})
                rep = "✅ Mémoire effacée, Monsieur."
            elif act == "UNLOCK":
                st.session_state.unlocked = True
                rep = "✅ Coffre ouvert."
            
            st.session_state.security_mode = "NORMAL"
            st.session_state.attempts = 0
        else:
            st.session_state.attempts += 1
            if st.session_state.attempts < 3:
                rep = f"❌ Code faux ({st.session_state.attempts}/3)."
            elif st.session_state.attempts == 3:
                rep = "⚠️ ÉCHECS RÉPÉTÉS. Entrez le code de secours (B2008a2020@)."
            else:
                rep = "🚨 ANNULATION SÉCURITÉ."
                st.session_state.security_mode = "NORMAL"
                st.session_state.attempts = 0

    # 2. DÉTECTION DES COMMANDES
    elif "réinitialisation complète" in low_p:
        st.session_state.security_mode = "WAITING_CODE"
        st.session_state.pending_action = "PURGE"
        rep = "🔒 Confirmation requise. Entrez le code."
        
    elif "affiche les archives verrouillées" in low_p:
        st.session_state.security_mode = "WAITING_CODE"
        st.session_state.pending_action = "UNLOCK"
        rep = "🔒 Authentification requise pour le coffre."

    # 3. RÉPONSE NORMALE IA
    else:
        with st.chat_message("assistant"):
            instr = {"role": "system", "content": f"Tu es DELTA. Infos: {faits_publics}"}
            r = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[instr] + st.session_state.messages)
            rep = r.choices[0].message.content

    with st.chat_message("assistant"):
        st.markdown(rep)
        st.session_state.messages.append({"role": "assistant", "content": rep})
