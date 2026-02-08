import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64, json

# --- INITIALISATION ---
if not firebase_admin._apps:
    try:
        encoded = st.secrets["firebase_key"]["encoded_key"].strip()
        decoded_json = base64.b64decode(encoded).decode("utf-8")
        cred = credentials.Certificate(json.loads(decoded_json))
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"Erreur Firebase : {e}")

db = firestore.client()
doc_ref = db.collection("archives").document("monsieur_sezer")
client = Groq(api_key="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")

# --- LECTURE MÉMOIRE ---
res = doc_ref.get()
archives = res.to_dict() if res.exists else {}

# --- INTERFACE ---
st.set_page_config(page_title="DELTA AGI", page_icon="🌐")
st.title("🌐 DELTA : Intelligence Forte")

with st.sidebar:
    st.header("🧠 Mémoire Lux")
    st.json(archives)

if "messages" not in st.session_state:
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# --- CORE PROCESS ---
if prompt := st.chat_input("Ordre direct..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    # 1. ANALYSE COGNITIVE (Syntaxe corrigée)
    try:
        # On place le prompt correctement dans 'messages'
        analysis_prompt = f"Archive ceci si pertinent : {prompt}. Format: {{'update': {{'categorie': {{'clé': 'valeur'}}}}}}"
        
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "Tu es une IA forte. Extrais les données en JSON pur."},
                {"role": "user", "content": analysis_prompt}
            ],
            response_format={"type": "json_object"}
        )
        
        brain = json.loads(completion.choices[0].message.content)
        
        # 2. INJECTION FIREBASE
        if "update" in brain and brain["update"]:
            doc_ref.set(brain["update"], merge=True)
            st.success("✅ Archive synchronisée.")
            st.rerun()
            
    except Exception as e:
        st.error(f"Erreur système : {e}")

    # 3. RÉPONSE ADAPTATIVE
    with st.chat_message("assistant"):
        nom = archives.get("profil", {}).get("nom", "Monsieur Sezer")
        sys_instr = f"Tu es DELTA, l'IA de {nom}. Archives : {json.dumps(archives)}. Style : Jarvis."
        
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": sys_instr}] + st.session_state.messages[-5:]
        ).choices[0].message.content
        
        st.markdown(response)
        st.session_state.messages.append({"role": "assistant", "content": response})
