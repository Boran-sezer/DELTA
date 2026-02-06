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
states = {
    "messages": [{"role": "assistant", "content": "DELTA opérationnel, Créateur. ⚡"}],
    "locked": False,
    "pending_auth": False,
    "essais": 0,
    "temp_text": ""
}
for key, val in states.items():
    if key not in st.session_state: st.session_state[key] = val

# --- 3. LOCKDOWN ---
if st.session_state.locked:
    st.markdown("<h1 style='color:red;'>🚨 SYSTÈME BLOQUÉ</h1>", unsafe_allow_html=True)
    m_input = st.text_input("CODE MAÎTRE :", type="password", key="m_lock")
    if st.button("🔓 RÉACTIVER"):
        if m_input == CODE_MASTER:
            st.session_state.locked = False
            st.session_state.essais = 0
            st.rerun()
    st.stop()

# --- 4. INTERFACE ---
st.markdown("<h1 style='color:#00d4ff;'>⚡ DELTA IA</h1>", unsafe_allow_html=True)

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# --- 5. AUTHENTIFICATION ---
if st.session_state.pending_auth:
    with st.chat_message("assistant"):
        if st.session_state.temp_text: st.markdown(st.session_state.temp_text + "...")
        st.warning(f"🔒 Identification requise ({3 - st.session_state.essais}/3)")
        c = st.text_input("Code :", type="password", key=f"auth_{len(st.session_state.messages)}")
        if st.button("VALIDER"):
            if c == CODE_ACT:
                st.session_state.pending_auth = False
                st.session_state.essais = 0
                res = doc_ref.get()
                faits = res.to_dict().get("faits", []) if res.exists else []
                txt = f"{st.session_state.temp_text}\n\nAccès autorisé. Archives : \n\n" + "\n".join([f"- {i}" for i in faits])
                st.session_state.messages.append({"role": "assistant", "content": txt})
                st.session_state.temp_text = ""
                st.rerun()
            else:
                st.session_state.essais += 1
                if st.session_state.essais >= 3: st.session_state.locked = True
                st.rerun()

# --- 6. TRAITEMENT DES ORDRES ET MÉMOIRE ---
if prompt := st.chat_input("Écrivez vos ordres ici..."):
    if st.session_state.pending_auth:
        st.error("Veuillez d'abord valider le code de sécurité.")
    else:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)

        # A. ANALYSE POUR MÉMOIRE (FILTRE)
        analyse_prompt = f"L'utilisateur dit : '{prompt}'. Est-ce une information personnelle importante à retenir ? Si oui, réponds UNIQUEMENT l'info sous forme de fait court. Sinon réponds 'NON'."
        check = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role": "user", "content": analyse_prompt}])
        nouveau_fait = check.choices[0].message.content.strip()

        if "NON" not in nouveau_fait.upper() and len(nouveau_fait) > 2:
            res = doc_ref.get()
            faits = res.to_dict().get("faits", []) if res.exists else []
            if nouveau_fait not in faits:
                faits.append(nouveau_fait)
                doc_ref.set({"faits": faits})
                st.toast(f"💾 Archivé : {nouveau_fait}")

        # B. RÉPONSE DE DELTA
        with st.chat_message("assistant"):
            placeholder = st.empty()
            full_raw, displayed = "", ""
            res = doc_ref.get()
            faits = res.to_dict().get("faits", []) if res.exists else []
            
            instr = (
                "Tu es DELTA, le majordome de Monsieur SEZER (ton Créateur). "
                f"SÉCURITÉ : Ne cite JAMAIS ces archives sans code : {faits}. "
                "Si tu dois y accéder, réponds : REQUIS_CODE."
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
                    if "REQUIS_CODE" in full_raw:
                        st.session_state.temp_text = full_raw.replace("REQUIS_CODE", "").strip()
                        st.session_state.pending_auth = True
                        break
                    for char in content:
                        displayed += char
                        placeholder.markdown(displayed + "▌")
                        time.sleep(0.01)

            if st.session_state.pending_auth:
                st.rerun()
            else:
                placeholder.markdown(full_raw)
                st.session_state.messages.append({"role": "assistant", "content": full_raw})
