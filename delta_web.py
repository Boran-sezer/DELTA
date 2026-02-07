import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64
import json

# --- INITIALISATION FIREBASE ---
if not firebase_admin._apps:
    try:
        # Utilisation de vos secrets Streamlit pour la clé Firebase
        encoded = st.secrets["firebase_key"]["encoded_key"].strip()
        decoded_json = base64.b64decode(encoded).decode("utf-8")
        cred = credentials.Certificate(json.loads(decoded_json))
        firebase_admin.initialize_app(cred)
    except Exception:
        pass

db = firestore.client()
doc_ref = db.collection("memoire").document("profil_monsieur")

# --- AUTHENTIFICATION GROQ ---
client = Groq(api_key="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")

# --- RÉCUPÉRATION MÉMOIRE (SILENCIEUSE) ---
res = doc_ref.get()
archives = res.to_dict().get("archives", {}) if res.exists else {}

# --- INTERFACE ADAPTATIVE & ÉPURÉE ---
st.set_page_config(page_title="DELTA", layout="wide")

st.markdown("""
    <style>
    /* Suppression des éléments d'interface par défaut */
    button { display: none; }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Titre Adaptatif */
    .title-delta { 
        font-family: 'Inter', sans-serif; 
        font-weight: 800; 
        font-size: clamp(2.5rem, 10vw, 4rem); 
        text-align: center; 
        letter-spacing: -3px;
        margin-top: -60px;
        padding-bottom: 20px;
    }

    /* Bulles de chat adaptatives */
    .stChatMessage {
        border-radius: 15px;
        margin-bottom: 12px;
        border: 1px solid rgba(128, 128, 128, 0.1);
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }

    /* Ajustement Mobile */
    @media (max-width: 640px) {
        .title-delta { margin-top: -30px; }
    }
    </style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="title-delta">DELTA</h1>', unsafe_allow_html=True)

if "messages" not in st.session_state:
    st.session_state.messages = []

# Affichage de l'historique
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# --- LOGIQUE DE TRAITEMENT ---
if prompt := st.chat_input("À votre service, Monsieur Sezer..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 1. Mise à jour de la mémoire (Llama 8B - Arrière-plan)
    if len(prompt.split()) > 2:
        try:
            m_prompt = f"Archives: {archives}. Nouveau message: {prompt}. Mets à jour le JSON si une info est utile. Ne change rien sinon."
            check = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "system", "content": "Tu es un gestionnaire de mémoire JSON strict. Pas de texte, juste du JSON."}, {"role": "user", "content": m_prompt}],
                response_format={"type": "json_object"}
            )
            archives = json.loads(check.choices[0].message.content)
            doc_ref.set({"archives": archives}, merge=True)
        except:
            pass

    # 2. Réponse de DELTA (Personnalité Jarvis - Llama 70B)
    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_res = ""
        
        # Intégration naturelle des connaissances
        connaissance_innée = f"Voici ce que tu sais de Monsieur Sezer (utilise-le naturellement sans le citer) : {json.dumps(archives)}" if archives else ""
        
        system_instruction = (
            f"Tu es DELTA, l'IA personnelle de Monsieur Sezer, conçue sur le modèle de JARVIS. "
            f"{connaissance_innée}. "
            "DIRECTIVES DE CONVERSATION : "
            "1. Sois extrêmement poli, dévoué et distingué. "
            "2. Réponds aux questions en utilisant tes connaissances sur lui de manière fluide, comme si c'était TA mémoire. "
            "3. NE DIS JAMAIS 'selon vos archives' ou 'j'ai enregistré'. Parle naturellement. "
            "4. Si on te demande qui tu es, tu es DELTA, l'IA de Monsieur Sezer. "
            "Termine chaque réponse par 'Monsieur Sezer'."
        )

        try:
            stream = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "system", "content": system_instruction}] + st.session_state.messages[-10:],
                temperature=0.6,
                stream=True
            )
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    full_res += chunk.choices[0].delta.content
                    placeholder.markdown(full_res + "▌")
            placeholder.markdown(full_res)
        except Exception:
            st.error("Navré, Monsieur Sezer, une instabilité système empêche la réponse.")

        st.session_state.messages.append({"role": "assistant", "content": full_res})
