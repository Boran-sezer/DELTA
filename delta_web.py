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

# --- 2. ÉTATS DE SESSION (VÉRIFICATION STRICTE) ---
keys = ["locked", "auth", "essais", "messages", "show_auth_form", "pending_prompt", "show_reset_confirm"]
for k in keys:
    if k not in st.session_state:
        st.session_state[k] = [] if k == "messages" else (0 if k == "essais" else False)

# --- 3. CHARGEMENT ARCHIVES ---
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

# --- 5. LOGIQUE DE RÉINITIALISATION (PRIORITÉ ABSOLUE) ---
if st.session_state.show_reset_confirm:
    with st.chat_message("assistant"):
        st.error("🧨 PROTOCOLE DE SUPPRESSION TOTALE")
        master_c = st.text_input("ENTREZ LE CODE MAÎTRE POUR TOUT EFFACER :", type="password", key="res_input")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("❌ ANNULER"):
                st.session_state.show_reset_confirm = False
                st.rerun()
        with col2:
            if st.button("🔥 TOUT EFFACER"):
                if master_c == CODE_MASTER:
                    doc_ref.set({"faits": []}) # Écrase Firebase
                    st.session_state.messages = []
                    st.session_state.show_reset_confirm = False
                    st.success("✨ Base de données nettoyée avec succès.")
                    st.rerun()
                else:
                    st.error("CODE INCORRECT. ALERTE SÉCURITÉ. ❌")
    st.stop() # On arrête le reste de l'affichage ici pendant la confirmation

# --- 6. INTERFACE DE CHAT ---
st.markdown("<h1 style='color:#00d4ff;'>⚡ DELTA IA</h1>", unsafe_allow_html=True)

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

if prompt := st.chat_input("Quels sont vos ordres, Monsieur ?"):
    p_low = prompt.lower()
    
    # DÉTECTION RESET (On intercepte avant que l'IA ne réponde)
    if "réinitialisation complete" in p_low or "réinitialise" in p_low or "reset" in p_low:
        st.session_state.show_reset_confirm = True
        st.rerun()

    # DÉTECTION SENSIBLE (Archives)
    sensible = any(w in p_low for w in ["archive", "mémoire", "montre", "souviens"])
    if sensible and not st.session_state.auth:
        st.session_state.show_auth_form = True
        st.session_state.pending_prompt = prompt
        st.rerun()

    # RÉPONSE IA NORMALE
    else:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)
        
        instr = f"Tu es DELTA IA. Ne donne JAMAIS les codes. Archives : {faits}. 🤖"
        r = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": instr}] + st.session_state.messages
        )
        rep = r.choices[0].message.content
        st.session_state.messages.append({"role": "assistant", "content": rep})
        st.rerun()

# --- 7. FENÊTRE AUTH (ONE-SHOT) ---
if st.session_state.show_auth_form:
    with st.chat_message("assistant"):
        st.warning("🔒 Code d'action requis.")
        c = st.text_input("Code :", type="password", key="act_input")
        if st.button("Valider"):
            if c == CODE_ACT:
                st.session_state.auth = True
                st.session_state.show_auth_form = False
                st.rerun()
            else:
                st.session_state.essais += 1
                if st.session_state.essais >= 3: st.session_state.locked = True
                st.rerun()
