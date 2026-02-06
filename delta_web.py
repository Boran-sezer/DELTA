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
    st.session_state.messages = [{"role": "assistant", "content": "DELTA opérationnel, Créateur. Prêt pour vos ordres. ⚡"}]
if "locked" not in st.session_state: st.session_state.locked = False
if "pending_auth" not in st.session_state: st.session_state.pending_auth = False
if "essais" not in st.session_state: st.session_state.essais = 0
if "temp_text" not in st.session_state: st.session_state.temp_text = ""

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
        if st.session_state.temp_text:
            st.markdown(st.session_state.temp_text + "...")
        st.warning(f"🔒 Identification requise ({3 - st.session_state.essais}/3)")
        c = st.text_input("Code :", type="password", key=f"auth_{len(st.session_state.messages)}")
        
        if st.button("VALIDER"):
            if c == CODE_ACT:
                st.session_state.pending_auth = False
                st.session_state.essais = 0
                
                # RÉCUPÉRATION CIBLÉE APRÈS CODE
                res = doc_ref.get()
                faits = res.to_dict().get("faits", []) if res.exists else []
                
                # On demande à DELTA de répondre spécifiquement à la dernière question avec les faits
                reponse_finale = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": f"Tu es DELTA. Tu as maintenant accès à ces archives : {faits}. Réponds PRÉCISÉMENT à la question du Créateur sans lister tout le reste, sauf s'il le demande."},
                    ] + st.session_state.messages
                )
                
                txt = reponse_finale.choices[0].message.content
                st.session_state.messages.append({"role": "assistant", "content": txt})
                st.session_state.temp_text = ""
                st.rerun()
            else:
                st.session_state.essais += 1
                if st.session_state.essais >= 3:
                    st.session_state.locked = True
                st.rerun()

# --- 6. TRAITEMENT ---
if prompt := st.chat_input("Écrivez vos ordres ici..."):
    if st.session_state.pending_auth:
        st.error("Veuillez d'abord valider le code de sécurité.")
    else:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            placeholder = st.empty()
            full_raw, displayed = "", ""
            
            res = doc_ref.get()
            faits = res.to_dict().get("faits", []) if res.exists else []
            
            instr = (
                "Tu es DELTA, le majordome de Monsieur SEZER (ton Créateur). "
                "Tu connais l'existence de tes archives mais tu ne peux pas lire leur contenu précis sans code. "
                "Si la question nécessite de fouiller dans les archives (ex: âge, voiture, préférences), réponds : REQUIS_CODE."
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
