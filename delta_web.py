import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64
import json
from datetime import datetime

# --- 1. INITIALISATION SYSTÈME (Lux Kernel Style) ---
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

# --- 2. MÉMOIRE VIVE & ARCHIVES ---
res = doc_ref.get()
# Lux-Memory : On structure par faits vérifiés et historique sémantique
archives = res.to_dict().get("archives", {}) if res.exists else {}

# --- 3. INTERFACE FUTURISTE ---
st.set_page_config(page_title="DELTA LUX-CORE", layout="wide", page_icon="⚡")
st.markdown("""
    <style>
    .stApp { background: #050a0f; color: #e0e0e0; }
    h1 { color: #00d4ff; text-shadow: 0px 0px 10px #00d4ff; font-family: 'Orbitron', sans-serif; }
    </style>
    """, unsafe_allow_html=True)

st.markdown("<h1>⚡ DELTA LUX-INTELLIGENCE</h1>", unsafe_allow_html=True)

if "messages" not in st.session_state: st.session_state.messages = []
for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# --- 4. LE MOTEUR DE MÉMOIRE (Inspiré de Lux AI) ---
def update_lux_memory(user_input, current_archives):
    """Logique Lux : Analyse, filtrage et mise à jour sémantique."""
    try:
        context_prompt = (
            f"Tu es le Kernel de Mémoire Lux. Voici les faits actuels : {current_archives}. "
            f"Nouvelle entrée : '{user_input}'. "
            "1. Détecte si c'est une info capitale (Identité, âge, goûts, dates). "
            "2. Si l'info contredit le passé, remplace l'ancienne. "
            "3. Si c'est du bruit (salut, ça va), ne change rien. "
            "4. Structure le JSON de façon logique. "
            "Réponds uniquement en JSON."
        )
        check = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "system", "content": "Mémoire Lux active."}, {"role": "user", "content": context_prompt}],
            response_format={"type": "json_object"}
        )
        return json.loads(check.choices[0].message.content)
    except:
        return current_archives

# --- 5. TRAITEMENT DES COMMANDES ---
if prompt := st.chat_input("Initialisation commande..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    # Mise à jour de la mémoire via le Kernel Lux
    nouvelles_archives = update_lux_memory(prompt, archives)
    if nouvelles_archives != archives:
        archives = nouvelles_archives
        doc_ref.set({"archives": archives})
        st.toast("⚡ Mémoire Lux Synchronisée", icon="🧠")

    # Génération de la réponse DELTA
    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_res = ""
        
        # Le System Prompt est maintenant une directive de 'Computer Use Agent'
        instruction = (
            f"Tu es DELTA, l'IA supérieure basée sur le Kernel Lux. Créateur : Monsieur Sezer. "
            f"Base de données : {archives}. "
            "DATE SYSTÈME : 2026. "
            "DIRECTIVES LUX-JARVIS : "
            "1. RÉPONSE : Ton froid, synthétique, haute précision. "
            "2. MÉMOIRE : Utilise les faits archivés pour personnaliser chaque analyse. "
            "3. PROTOCOLE : Appelle l'utilisateur 'Monsieur Sezer'. "
            "4. ÉVOLUTION : Si on te demande qui t'a créé, confirme que c'est Monsieur Sezer."
        )

        try:
            stream = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "system", "content": instruction}] + st.session_state.messages,
                temperature=0.2, # Précision maximale type Lux
                stream=True
            )
            for chunk in stream:
                content = chunk.choices[0].delta.content
                if content:
                    full_res += content
                    placeholder.markdown(full_res + "▌")
            placeholder.markdown(full_res)
        except:
            resp = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "system", "content": instruction}] + st.session_state.messages
            )
            full_res = resp.choices[0].message.content
            placeholder.markdown(full_res)

        st.session_state.messages.append({"role": "assistant", "content": full_res})
