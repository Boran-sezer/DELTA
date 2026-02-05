import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64
import json

# --- CONFIGURATION ---
st.set_page_config(page_title="DELTA OS", page_icon="⚡", layout="wide")

# --- INITIALISATION FIREBASE ---
if not firebase_admin._apps:
    try:
        encoded = st.secrets["firebase_key"]["encoded_key"].strip()
        decoded_json = base64.b64decode(encoded).decode("utf-8")
        creds_dict = json.loads(decoded_json)
        cred = credentials.Certificate(creds_dict)
        firebase_admin.initialize_app(cred)
    except Exception:
        st.error("⚠️ Connexion Mémoire interrompue.")

db = firestore.client()
doc_profil = db.collection("memoire").document("profil_monsieur")

# --- CONNEXION GROQ ---
client = Groq(api_key="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")

# --- ÉTATS DE SESSION ---
if "messages" not in st.session_state: st.session_state.messages = []
if "unlocked" not in st.session_state: st.session_state.unlocked = False
if "security_step" not in st.session_state: st.session_state.security_step = "NORMAL"
if "attempts" not in st.session_state: st.session_state.attempts = 0
if "pending_action" not in st.session_state: st.session_state.pending_action = None

# --- CHARGEMENT DU PROFIL ---
res_profil = doc_profil.get()
data = res_profil.to_dict() if res_profil.exists else {}
faits_publics = data.get("faits", [])
faits_verrouilles = data.get("faits_verrouilles", [])

# --- SIDEBAR ---
with st.sidebar:
    st.title("🧠 Archives")
    st.write(f"État : {'🔓 Ouvert' if st.session_state.unlocked else '🔒 Fermé'}")
    
    st.subheader("📁 Standard")
    for i, f in enumerate(faits_publics):
        col1, col2 = st.columns([4, 1])
        col1.info(f)
        if col2.button("🗑️", key=f"p_{i}"):
            faits_publics.pop(i)
            doc_profil.update({"faits": faits_publics})
            st.rerun()
            
    if st.session_state.unlocked:
        st.subheader("🔐 Scellées")
        for i, f in enumerate(faits_verrouilles):
            col1, col2 = st.columns([4, 1])
            col1.warning(f)
            if col2.button("🗑️", key=f"s_{i}"):
                faits_verrouilles.pop(i)
                doc_profil.update({"faits_verrouilles": faits_verrouilles})
                st.rerun()

# --- CHAT ---
for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# --- LOGIQUE DE TRAITEMENT ---
if p := st.chat_input("Vos ordres, Monsieur ?"):
    st.session_state.messages.append({"role": "user", "content": p})
    with st.chat_message("user"): st.markdown(p)
    
    rep = ""
    low_p = p.lower().strip()

    # 1. PHASE DE SÉCURITÉ (SI BLOQUÉ)
    if st.session_state.security_step == "VERROU":
        code_normal = "20082008"
        code_secours = "B2008a2020@"
        
        # Choix du code attendu
        attendu = code_normal if st.session_state.attempts < 3 else code_secours
        
        if p == attendu:
            # SUCCÈS
            action = st.session_state.pending_action
            if action['type'] == "PURGE":
                doc_profil.set({"faits": [], "faits_verrouilles": []})
                rep = "✅ **SYSTÈME PURGÉ.** La mémoire est vide."
            elif action['type'] == "LOCK":
                faits_verrouilles.append(action['info'])
                doc_profil.update({"faits_verrouilles": faits_verrouilles})
                rep = "✅ **INFO SCELLÉE.**"
            elif action['type'] == "UNLOCK":
                st.session_state.unlocked = True
                rep = "✅ **COFFRE OUVERT.**"
            elif action['type'] == "DELETE":
                t = action['info'].lower()
                new_pub = [f for f in faits_publics if t not in f.lower()]
                new_priv = [f for f in faits_verrouilles if t not in f.lower()]
                doc_profil.set({"faits": new_pub, "faits_verrouilles": new_priv})
                rep = f"✅ **'{action['info']}' SUPPRIMÉ.**"
            
            st.session_state.security_step = "NORMAL"
            st.session_state.attempts = 0
        else:
            # ÉCHEC
            st.session_state.attempts += 1
            if st.session_state.attempts < 3:
                rep = f"❌ **CODE INCORRECT.** Essai {st.session_state.attempts}/3."
            elif st.session_state.attempts == 3:
                rep = "⚠️ **SÉCURITÉ MAX.** Entrez le code de secours (B2008a2020@)."
            else:
                rep = "🚨 **ABANDON.** Trop d'échecs."
                st.session_state.security_step = "NORMAL"
                st.session_state.attempts = 0

    # 2. PHASE DE DÉTECTION DES ORDRES
    elif "réinitialisation complète" in low_p:
        st.session_state.security_step = "VERROU"
        st.session_state.pending_action = {"type": "PURGE"}
        rep = "🔒 **CONFIRMATION.** Veuillez entrer le code d'accès."
    elif "verrouille" in low_p:
        st.session_state.security_step = "VERROU"
        st.session_state.pending_action = {"type": "LOCK", "info": p.replace("verrouille", "").strip()}
        rep = "🔒 **SCELLAGE.** Code requis."
    elif "affiche les archives verrouillées" in low_p:
        st.session_state.security_step = "VERROU"
        st.session_state.pending_action = {"type": "UNLOCK"}
        rep = "🔒 **AUTHENTIFICATION.** Code requis pour ouvrir le coffre."
    elif "supprime précisément" in low_p:
        st.session_state.security_step = "VERROU"
        st.session_state.pending_action = {"type": "DELETE", "info": p.replace("supprime précisément", "").strip()}
        rep = "🔒 **SUPPRESSION.** Code requis."
    
    # 3. RÉPONSE IA NORMALE
    else:
        with st.chat_message("assistant"):
            instr = {"role": "system", "content": f"Tu es DELTA, majordome de Monsieur Boran. Infos: {faits_publics}."}
            r = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[instr] + st.session_state.messages)
            rep = r.choices[0].message.content

    # AFFICHAGE DE LA RÉPONSE
    with st.chat_message("assistant"):
        st.markdown(rep)
        st.session_state.messages.append({"role": "assistant", "content": rep})
