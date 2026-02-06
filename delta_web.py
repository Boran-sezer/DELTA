import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64
import json
import time

# --- 1. CONFIGURATION DES ACCÈS ---
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

# --- 2. ÉTATS DE SESSION (MÉMOIRE VIVE) ---
states = {
    "messages": [{"role": "assistant", "content": "DELTA opérationnel. Prêt pour vos ordres, Monsieur SEZER. ⚡"}],
    "locked": False,
    "pending_auth": False,
    "essais": 0
}
for key, val in states.items():
    if key not in st.session_state:
        st.session_state[key] = val

# --- 3. RÉCUPÉRATION DE LA MÉMOIRE LONG TERME ---
res = doc_ref.get()
faits = res.to_dict().get("faits", []) if res.exists else []

# --- 4. SÉCURITÉ : MODE LOCKDOWN ---
if st.session_state.locked:
    st.error("🚨 SYSTÈME VERROUILLÉ - TROP DE TENTATIVES")
    m_input = st.text_input("ENTREZ LE CODE MAÎTRE POUR RÉACTIVER :", type="password", key="master_field")
    if st.button("🔓 RÉACTIVER LE SYSTÈME"):
        if m_input == CODE_MASTER:
            st.session_state.locked = False
            st.session_state.essais = 0
            st.session_state.messages.append({"role": "assistant", "content": "Système réinitialisé par Code Maître. Bienvenue, Monsieur."})
            st.rerun()
        else:
            st.error("Code Maître invalide.")
    st.stop()

# --- 5. INTERFACE ET HISTORIQUE ---
st.markdown("<h1 style='color:#00d4ff;'>⚡ DELTA IA</h1>", unsafe_allow_html=True)

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# --- 6. ÉCRAN D'AUTHENTIFICATION (DÉCLENCHÉ PAR DELTA) ---
if st.session_state.pending_auth:
    with st.chat_message("assistant"):
        st.warning(f"🔒 Accès restreint. Tentatives restantes : {3 - st.session_state.essais}")
        c = st.text_input("Veuillez décliner votre identité (Code) :", type="password", key="delta_auth_field")
        
        if st.button("CONFIRMER L'ACCÈS"):
            if c == CODE_ACT:
                st.session_state.pending_auth = False
                st.session_state.essais = 0
                info_txt = "Accès autorisé. Voici vos notes confidentielles : \n\n" + "\n".join([f"- {i}" for i in faits])
                st.session_state.messages.append({"role": "assistant", "content": info_txt})
                st.rerun()
            else:
                st.session_state.essais += 1
                if st.session_state.essais >= 3:
                    st.session_state.locked = True
                    st.session_state.pending_auth = False
                    st.rerun()
                else:
                    st.error(f"Accès refusé. Tentative {st.session_state.essais}/3.")
    st.stop()

# --- 7. TRAITEMENT DES ORDRES ---
if prompt := st.chat_input("Vos ordres, Monsieur SEZER ?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Commande manuelle de verrouillage
    if "verrouille" in prompt.lower():
        st.session_state.locked = True
        st.rerun()

    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_raw, displayed = "", ""
        
        # Instructions pour l'intelligence de DELTA
        instr = (
            f"Tu es DELTA, le majordome de Monsieur SEZER. Sois ultra-concis. "
            f"Tu as accès à ces archives : {faits}. "
            "PROTOCOLE : Si Monsieur pose une question sur ses informations personnelles, "
            "ses archives ou demande à voir sa mémoire, réponds EXACTEMENT : REQUIS_CODE. "
            "Sinon, réponds normalement."
        )

        stream = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": instr}] + st.session_state.messages,
            stream=True
        )

        for chunk in stream:
            content = chunk.choices[0].delta.content
            if content:
                full_raw += content
                if "REQUIS_CODE" in full_raw: break
                for char in content:
                    displayed += char
                    placeholder.markdown(displayed + "▌")
                    time.sleep(0.01)

        # Vérification si l'IA demande le code
        if "REQUIS_CODE" in full_raw:
            st.session_state.pending_auth = True
            st.rerun()
        else:
            placeholder.markdown(full_raw)
            st.session_state.messages.append({"role": "assistant", "content": full_raw})
