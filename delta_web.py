import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64
import json
import time
import streamlit.components.v1 as components

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

# --- 2. FONCTION AUTO-SCROLL (JavaScript) ---
def scroll_en_bas():
    # Ce script force la fenêtre à descendre tout en bas
    js = """
    <script>
        var body = window.parent.document.querySelector(".main");
        body.scrollTop = body.scrollHeight;
    </script>
    """
    components.html(js, height=0)

# --- 3. ÉTATS DE SESSION ---
if "messages" not in st.session_state: 
    st.session_state.messages = [{"role": "assistant", "content": "DELTA prêt. Vos ordres, Monsieur SEZER ? ⚡"}]
if "locked" not in st.session_state: st.session_state.locked = False
if "pending_auth" not in st.session_state: st.session_state.pending_auth = False
if "essais" not in st.session_state: st.session_state.essais = 0

# --- 4. LOCKDOWN ---
if st.session_state.locked:
    st.error("🚨 SYSTÈME BLOQUÉ")
    m_input = st.text_input("CODE MAÎTRE :", type="password", key="m_lock")
    if st.button("🔓 RÉACTIVER"):
        if m_input == CODE_MASTER:
            st.session_state.locked = False
            st.session_state.essais = 0
            st.rerun()
    st.stop()

# --- 5. INTERFACE ---
st.markdown("<h1 style='color:#00d4ff;'>⚡ DELTA IA</h1>", unsafe_allow_html=True)

# Affichage de l'historique
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# --- 6. AUTHENTIFICATION (SANS SAUT) ---
if st.session_state.pending_auth:
    scroll_en_bas() # On force le scroll ici
    with st.chat_message("assistant"):
        st.warning(f"🔒 Identification requise ({3 - st.session_state.essais}/3)")
        c = st.text_input("Code :", type="password", key=f"auth_{len(st.session_state.messages)}")
        if st.button("VALIDER"):
            if c == CODE_ACT:
                st.session_state.pending_auth = False
                st.session_state.essais = 0
                res = doc_ref.get()
                faits = res.to_dict().get("faits", []) if res.exists else []
                txt = "Accès autorisé. Archives : \n\n" + "\n".join([f"- {i}" for i in faits])
                st.session_state.messages.append({"role": "assistant", "content": txt})
                st.rerun()
            else:
                st.session_state.essais += 1
                if st.session_state.essais >= 3:
                    st.session_state.locked = True
                st.rerun()
    st.stop()

# --- 7. TRAITEMENT ---
if prompt := st.chat_input("Ordres ?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    if "verrouille" in prompt.lower():
        st.session_state.locked = True
        st.rerun()

    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_raw, displayed = "", ""
        
        # Récupération faits pour l'IA
        res = doc_ref.get()
        faits = res.to_dict().get("faits", []) if res.exists else []
        
        instr = f"Tu es DELTA. Cite pas ces faits sans code : {faits}. Si accès mémoire demandé : REQUIS_CODE."

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
                    st.session_state.pending_auth = True
                    break
                for char in content:
                    displayed += char
                    placeholder.markdown(displayed + "▌")
                    time.sleep(0.01)
                    scroll_en_bas() # Scroll pendant que l'IA écrit

        if st.session_state.pending_auth:
            st.rerun()
        else:
            placeholder.markdown(full_raw)
            st.session_state.messages.append({"role": "assistant", "content": full_raw})
            scroll_en_bas() # Scroll final
