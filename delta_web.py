import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64
import json

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

# --- 2. INITIALISATION DES ÉTATS ---
for key in ["locked", "auth", "essais", "messages", "show_auth_form", "pending_prompt", "show_reset_confirm"]:
    if key not in st.session_state:
        if key == "messages": st.session_state[key] = []
        elif key == "essais": st.session_state[key] = 0
        else: st.session_state[key] = False

# --- 3. CHARGEMENT MÉMOIRE ---
res = doc_ref.get()
data = res.to_dict() if res.exists else {"faits": []}
faits = data.get("faits", [])

# --- 4. SÉCURITÉ : LOCKDOWN ---
if st.session_state.locked:
    st.error("🚨 SYSTÈME BLOQUÉ - SÉCURITÉ MAXIMALE")
    m_input = st.text_input("ENTREZ LE CODE MAÎTRE :", type="password", key="m_key")
    if st.button("🔓 DÉBLOQUER"):
        if m_input == CODE_MASTER:
            st.session_state.locked = False
            st.session_state.essais = 0
            st.rerun()
    st.stop()

# --- 5. INTERFACE ---
st.markdown("<h1 style='color:#00d4ff;'>⚡ DELTA IA</h1>", unsafe_allow_html=True)

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# --- 6. LOGIQUE DE TRAITEMENT ---
if prompt := st.chat_input("Quels sont vos ordres, Monsieur ?"):
    p_low = prompt.lower()
    
    # Priorité 1 : RÉINITIALISATION (Détection ultra-large)
    if any(w in p_low for w in ["réinitialise", "reset", "format", "nettoie", "supprime tout"]):
        st.session_state.show_reset_confirm = True
        st.rerun()

    # Priorité 2 : ACTIONS SENSIBLES
    sensible = any(w in p_low for w in ["archive", "mémoire", "montre", "souviens"])
    if sensible and not st.session_state.auth:
        st.session_state.show_auth_form = True
        st.session_state.pending_prompt = prompt
        st.rerun()

    # Priorité 3 : RÉPONSE NORMALE
    else:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)
        
        instr = f"Tu es DELTA IA. Ne donne JAMAIS les codes. Archives : {faits}. Finis par 'ACTION_ARCHIVE: [info]' si besoin. 🤖"
        r = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": instr}] + st.session_state.messages
        )
        rep = r.choices[0].message.content
        
        if "ACTION_ARCHIVE:" in rep:
            info = rep.split("ACTION_ARCHIVE:")[1].strip()
            if info not in faits:
                faits.append(info)
                doc_ref.update({"faits": faits})
            rep = rep.split("ACTION_ARCHIVE:")[0].strip()
            
        st.session_state.messages.append({"role": "assistant", "content": rep})
        st.rerun()

# --- 7. LES FENÊTRES DE SÉCURITÉ (S'affichent si l'état change) ---

if st.session_state.show_auth_form:
    with st.chat_message("assistant"):
        st.warning("🔒 Identification requise pour accéder aux archives.")
        c = st.text_input("Code d'action :", type="password")
        if st.button("Valider"):
            if c == CODE_ACT:
                st.session_state.auth = True
                st.session_state.show_auth_form = False
                st.rerun()
            else:
                st.session_state.essais += 1
                if st.session_state.essais >= 3: st.session_state.locked = True
                st.rerun()

if st.session_state.show_reset_confirm:
    with st.chat_message("assistant"):
        st.error("🧨 PROTOCOLE DE SUPPRESSION TOTALE")
        master_c = st.text_input("ENTREZ LE CODE MAÎTRE :", type="password")
        if st.button("🔥 CONFIRMER LA DESTRUCTION DES DONNÉES"):
            if master_c == CODE_MASTER:
                # NETTOYAGE PHYSIQUE SUR FIREBASE
                doc_ref.set({"faits": []}) 
                st.session_state.messages = []
                st.session_state.show_reset_confirm = False
                st.success("✨ Tout a été effacé, Monsieur.")
                st.rerun()
            else:
                st.error("Code erroné. Procédure annulée. ❌")
