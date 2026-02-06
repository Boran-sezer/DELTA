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

# --- 2. ÉTATS ---
if "messages" not in st.session_state: 
    st.session_state.messages = [{"role": "assistant", "content": "DELTA opérationnel. ⚡"}]
if "locked" not in st.session_state: st.session_state.locked = False
if "ask_auth" not in st.session_state: st.session_state.ask_auth = False
if "temp_prompt" not in st.session_state: st.session_state.temp_prompt = None

# --- 3. CHARGEMENT MÉMOIRE ---
res = doc_ref.get()
data = res.to_dict() if res.exists else {"faits": []}
faits = data.get("faits", [])

# --- 4. SÉCURITÉ LOCKDOWN ---
if st.session_state.locked:
    st.error("🚨 SYSTÈME VERROUILLÉ")
    if st.text_input("CODE MAÎTRE :", type="password", key="lock") == CODE_MASTER:
        st.session_state.locked = False
        st.rerun()
    st.stop()

# --- 5. LOGIQUE DE RÉPONSE ---
def reponse_delta(prompt, mode="normal"):
    if mode == "archives":
        instr = f"Tu es DELTA. Liste ces archives de Monsieur SEZER sans aucun blabla : {faits}."
    else:
        instr = (
            f"Tu es DELTA, majordome de Monsieur SEZER. Sois ultra-concis. "
            f"Archives actuelles : {faits}. "
            "Si Monsieur demande de supprimer une info, réponds : 'ACTION_DELETE: [mot-clé]'."
            "Si Monsieur donne une nouvelle info, réponds : 'ACTION_ARCHIVE: [info]'."
        )

    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_raw, displayed = "", ""
        stream = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": instr}] + st.session_state.messages,
            stream=True
        )
        
        for chunk in stream:
            content = chunk.choices[0].delta.content
            if content:
                full_raw += content
                if "ACTION_" in full_raw: break
                for char in content:
                    displayed += char
                    placeholder.markdown(displayed + "▌")
                    time.sleep(0.01)
        
        clean = full_raw.split("ACTION_")[0].strip()
        if not clean and "ACTION_DELETE" in full_raw:
            clean = "C'est fait, Monsieur SEZER. J'ai effacé cela de ma mémoire."
        
        placeholder.markdown(clean)
        st.session_state.messages.append({"role": "assistant", "content": clean})

        # --- ACTIONS FIREBASE ---
        if "ACTION_DELETE:" in full_raw:
            cible = full_raw.split("ACTION_DELETE:")[1].strip().lower()
            nouveaux_faits = [f for f in faits if cible not in f.lower()]
            doc_ref.set({"faits": nouveaux_faits}, merge=True)
            st.toast("Suppression effectuée.")
            time.sleep(1)
            st.rerun()

        if "ACTION_ARCHIVE:" in full_raw:
            info = full_raw.split("ACTION_ARCHIVE:")[1].strip()
            if info not in faits:
                faits.append(info)
                doc_ref.set({"faits": faits}, merge=True)
                st.toast("Mémorisé.")

# --- 6. INTERFACE ---
st.markdown("<h1 style='color:#00d4ff;'>⚡ DELTA</h1>", unsafe_allow_html=True)

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# Gestion du formulaire de code
if st.session_state.ask_auth:
    with st.chat_message("assistant"):
        st.warning("🔒 Accès à la mémoire requis.")
        code = st.text_input("CODE :", type="password", key="auth_field")
        if st.button("VALIDER"):
            if code == CODE_ACT:
                st.session_state.ask_auth = False
                reponse_delta("Affichage mémoire", mode="archives")
                st.rerun()
            else:
                st.error("Code incorrect.")
    st.stop()

# Saisie utilisateur
if prompt := st.chat_input("Ordres ?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    p_low = prompt.lower()
    
    # 1. Verrouillage
    if "verrouille" in p_low:
        st.session_state.locked = True
        st.rerun()
    
    # 2. Sécurité : On bloque TOUT ce qui touche à la mémoire/archives
    elif any(w in p_low for w in ["mémoire", "archive", "souviens", "faits", "notes"]):
        st.session_state.ask_auth = True
        st.rerun()
    
    # 3. Actions normales
    else:
        reponse_delta(prompt)
        st.rerun()
