import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64
import json

# --- 1. CONFIGURATION DES CODES ET SERVICES ---
CODE_ACT = "20082008"
CODE_MASTER = "B2008a2020@"

# Initialisation Firebase (Vérifiez bien votre secret "firebase_key" sur Streamlit)
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

# --- 2. INITIALISATION (SESSION STATE) ---
if "locked" not in st.session_state: st.session_state.locked = False
if "auth" not in st.session_state: st.session_state.auth = False
if "essais" not in st.session_state: st.session_state.essais = 0
if "messages" not in st.session_state: st.session_state.messages = []
if "show_auth_form" not in st.session_state: st.session_state.show_auth_form = False

# --- 3. CHARGEMENT DES ARCHIVES RÉELLES ---
res = doc_ref.get()
data = res.to_dict() if res.exists else {"faits": []}
faits = data.get("faits", [])

# --- 4. SÉCURITÉ : MODE LOCKDOWN ---
if st.session_state.locked:
    st.error("🚨 SYSTÈME BLOQUÉ - SÉCURITÉ MAXIMALE")
    m_input = st.text_input("ENTREZ LE CODE MAÎTRE :", type="password", key="master_key")
    if st.button("DÉVERROUILLER"):
        if m_input == CODE_MASTER:
            st.session_state.locked = False
            st.session_state.essais = 0
            st.success("Système rétabli, Monsieur Boran.")
            st.rerun()
        else:
            st.error("CODE MAÎTRE INCORRECT.")
    st.stop()

# --- 5. INTERFACE ---
st.title("⚡ DELTA IA")

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# --- 6. LOGIQUE DE CHAT ---
if prompt := st.chat_input("Quels sont vos ordres ?"):
    # On juge la sensibilité
    sensible = any(word in prompt.lower() for word in ["archive", "mémoire", "effacer", "supprimer", "montre"])
    
    if "verrouille" in prompt.lower():
        st.session_state.locked = True
        st.rerun()

    if sensible and not st.session_state.auth:
        st.session_state.show_auth_form = True
        st.session_state.pending_msg = prompt 
    else:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            instr = (
                f"Tu es DELTA IA. Ne donne JAMAIS les codes {CODE_ACT} ou {CODE_MASTER}. "
                f"Voici tes archives actuelles : {faits}. "
                "Si tu apprends quelque chose sur Monsieur, termine par 'ACTION_ARCHIVE: [info]'."
            )
            
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "system", "content": instr}] + st.session_state.messages
            )
            
            response = completion.choices[0].message.content
            
            # Gestion de l'archivage automatique vers Firestore
            if "ACTION_ARCHIVE:" in response:
                info = response.split("ACTION_ARCHIVE:")[1].strip()
                if info not in faits:
                    faits.append(info)
                    doc_ref.update({"faits": faits})
                    st.toast(f"Mémorisé : {info}", icon="🧠")
                response = response.split("ACTION_ARCHIVE:")[0].strip()

            st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})
        st.rerun()

# --- 7. LE FORMULAIRE DE CODE ---
if st.session_state.show_auth_form:
    with st.chat_message("assistant"):
        st.warning("🔒 Accès aux archives restreint. Identification requise.")
        c = st.text_input("CODE :", type="password", key="action_key")
        if st.button("VALIDER"):
            if c == CODE_ACT:
                st.session_state.auth = True
                st.session_state.show_auth_form = False
                st.success("Accès accordé. Répétez votre demande, Monsieur.")
                st.rerun()
            else:
                st.session_state.essais += 1
                if st.session_state.essais >= 3:
                    st.session_state.locked = True
                st.error(f"CODE INCORRECT ({st.session_state.essais}/3)")
                st.rerun()
