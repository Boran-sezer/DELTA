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

# --- 2. GESTION DES ÉTATS (SESSION STATE) ---
if "messages" not in st.session_state: 
    st.session_state.messages = [{"role": "assistant", "content": "Système DELTA activé. Prêt à vous servir, Monsieur SEZER. ⚡"}]
if "auth" not in st.session_state: st.session_state.auth = False
if "locked" not in st.session_state: st.session_state.locked = False

# --- 3. CHARGEMENT DE LA MÉMOIRE ---
res = doc_ref.get()
data = res.to_dict() if res.exists else {"faits": []}
faits = data.get("faits", [])

# --- 4. SÉCURITÉ : MODE LOCKDOWN ---
if st.session_state.locked:
    st.error("🚨 SYSTÈME BLOQUÉ - SÉCURITÉ MAXIMALE")
    m_input = st.text_input("ENTREZ LE CODE MAÎTRE :", type="password")
    if st.button("🔓 DÉBLOQUER"):
        if m_input == CODE_MASTER:
            st.session_state.locked = False
            st.rerun()
    st.stop()

# --- 5. LOGIQUE DE GÉNÉRATION DISCRÈTE ET LENTE ---
def flux_delta(prompt):
    instr = (
        "Tu es DELTA IA, le majordome personnel de Monsieur SEZER. Tu es sa création. "
        "CONSIGNE DE DISCRÉTION : Ne mentionne JAMAIS tes archives ou tes balises techniques. "
        "Réponds avec efficacité. Si tu apprends une info importante, "
        "termine impérativement par 'ACTION_ARCHIVE: [info]'."
        f"Archives confidentielles (NE PAS RÉCITER) : {faits}."
    )
    
    stream = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "system", "content": instr}] + st.session_state.messages,
        stream=True
    )
    
    for chunk in stream:
        content = chunk.choices[0].delta.content
        if content:
            yield content

# --- 6. INTERFACE DE CHAT ---
st.markdown("<h1 style='color:#00d4ff;'>⚡ DELTA IA</h1>", unsafe_allow_html=True)

# Affichage de l'historique
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# Zone de saisie
if prompt := st.chat_input("Vos ordres, Monsieur SEZER ?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Commande de verrouillage
    if "verrouille" in prompt.lower():
        st.session_state.locked = True
        st.rerun()

    # Réponse de DELTA
    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_raw_text = ""
        displayed_text = ""
        
        # Effet d'écriture ralentie et filtrage des balises
        for chunk in flux_delta(prompt):
            full_raw_text += chunk
            
            # Si on commence à détecter la balise, on arrête d'afficher
            if "ACTION_ARCHIVE" in full_raw_text:
                break
            
            # Affichage lettre par lettre pour le style
            for char in chunk:
                displayed_text += char
                placeholder.markdown(displayed_text + "▌")
                time.sleep(0.02) # Vitesse réglée pour Monsieur SEZER
        
        # Nettoyage final pour l'enregistrement
        clean_response = full_raw_text.split("ACTION_ARCHIVE")[0].strip()
        placeholder.markdown(clean_response)

        # Archivage secret en arrière-plan
        if "ACTION_ARCHIVE:" in full_raw_text:
            info = full_raw_text.split("ACTION_ARCHIVE:")[1].strip().split('\n')[0]
            if info not in faits:
                faits.append(info)
                doc_ref.set({"faits": faits}, merge=True)
                # Note : On ne met plus de message de succès pour rester discret

    st.session_state.messages.append({"role": "assistant", "content": clean_response})

# --- 7. PROTECTION DES ARCHIVES ---
if any(w in (prompt or "").lower() for w in ["archive", "mémoire"]):
    if not st.session_state.auth:
        with st.chat_message("assistant"):
            st.warning("🔒 Identification requise pour accéder aux dossiers.")
            c = st.text_input("CODE :", type="password")
            if st.button("CONFIRMER"):
                if c == CODE_ACT:
                    st.session_state.auth = True
                    st.rerun()
