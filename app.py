import streamlit as st
import glob
import os
from google import genai
from google.genai import types

st.set_page_config(
    page_title="Profesorul AI - PLIF",
    page_icon="👨‍🏫",
    layout="centered"
)

st.title("👨‍🏫 Profesorul AI – Îmbunățiri Funciare")
st.caption("Platformă interactivă de pregătire profesională în Irigații, Desecare-Drenaj, CES și Hidraulică.")

# --- 1. PRELUARE SECURIZATĂ A CHEII API ---
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"].strip()
else:
    st.error("Cheia GEMINI_API_KEY nu este configurată în Streamlit Secrets!")
    st.stop()

client = genai.Client(api_key=api_key)

# --- 2. DETECTARE AUTOMATĂ ȘI VERIFICARE MODEL ---
@st.cache_resource
def find_active_model():
    try:
        # Preluăm toate modelele disponibile direct din contul tău Google AI Studio
        all_models = list(client.models.list())
        available_names = [m.name.replace("models/", "") for m in all_models]
        
        # Căutăm cele mai bune opțiuni în ordinea preferințelor
        for pref in ["gemini-2.0-flash", "gemini-2.0-flash-lite", "gemini-1.5-flash", "gemini-1.5-pro"]:
            if pref in available_names:
                return pref
        
        # Dacă nu găsește un nume exact din listă, alege primul model activ
        for name in available_names:
            if "flash" in name or "gemini" in name:
                return name
                
        if available_names:
            return available_names[0]
    except Exception as e:
        st.sidebar.warning(f"Atenție la scanarea modelelor: {e}")
    return "gemini-2.0-flash"

ACTIVE_MODEL = find_active_model()
st.sidebar.success(f"🤖 Model activ conectat: `{ACTIVE_MODEL}`")

# --- 3. ÎNCĂRCAREA BAZEI DE CUNOȘTINȚE ---
@st.cache_data
def load_knowledge_base():
    full_context = ""
    kb_files = glob.glob("./KnowledgeBase_PLIF/**/*.md", recursive=True) + glob.glob("./*.md", recursive=True)
    for fpath in kb_files:
        if "README" in fpath:
            continue
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                filename = os.path.basename(fpath)
                full_context += f"\n\n--- [FIȘIER: {filename}] ---\n" + f.read()
        except Exception:
            pass
    return full_context if full_context else "Se utilizează cunoștințele generale din ingineria hidroameliorativă românească."

KB_CONTEXT = load_knowledge_base()

# --- 4. GESTIONAREA ISTORICULUI DE CHAT ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# Afișarea mesajelor anterioare
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Prompt-ul utilizatorului
if prompt := st.chat_input("Adresează o întrebare Profesorului AI..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    system_instruction = f"""Ești un Profesor Universitar de Elită și Mentor în Ingineria Îmbunățirilor Funciare (PLIF) din România.
Ai la dispoziție Baza de Cunoștințe specializată:
{KB_CONTEXT[:8000]} [...]

Misiunea ta pedagogică:
1. Să explici noțiuni teoretice, tehnologii de exploatare, ecuații hidraulice (ex: Glover-Dumm, Penman-Monteith, curbe pompe) clar, concis și pedagogic.
2. Să răspunzi cu rigoare ingineriască ancorată în practica din România (norme ANIF, STAS-uri, condiții de teren).
3. Oferă exerciții practice de calcul numerice rezolvate pas cu pas sau grile de verificare când ți se cere.
4. Folosește notații LaTeX pentru toate formulele matematice/hidraulice."""

    formatted_history = []
    for msg in st.session_state.messages:
        role = "user" if msg["role"] == "user" else "model"
        formatted_history.append(types.Content(role=role, parts=[types.Part.from_text(text=msg["content"])]))

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        try:
            response = client.models.generate_content(
                model=ACTIVE_MODEL,
                contents=formatted_history,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.2
                )
            )
            full_response = response.text
            message_placeholder.markdown(full_response)
            st.session_state.messages.append({"role": "assistant", "content": full_response})
        except Exception as e:
            st.error(f"Eroare la conectare cu modelul `{ACTIVE_MODEL}`: {str(e)}")
