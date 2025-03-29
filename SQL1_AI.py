import streamlit as st
import google.generativeai as genai
import sounddevice as sd
import numpy as np
import wave
import tempfile
import smtplib
import os
import pandas as pd
from email.message import EmailMessage
import speech_recognition as sr
from collections import defaultdict
import sqlite3  # Import SQLite module
from datetime import datetime
import random  # For randomly selecting a station

# 📌 Set page config as the FIRST Streamlit command
st.set_page_config(page_title="Railway Complaint System", layout="wide")

# 🔹 Configure Gemini AI
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')

# 🔹 Define valid PNR numbers
VALID_PNR_NUMBERS = {f"PNRA{i}" for i in range(1, 11)} | {f"PNRB{i}" for i in range(1, 11)}

# 🚀 Supported languages for speech recognition
LANGUAGE_MAP = {
    "Assamese": "as-IN", "Bengali": "bn-IN", "Bodo": "brx-IN",
    "Dogri": "doi-IN", "Gujarati": "gu-IN", "Hindi": "hi-IN",
    "Kannada": "kn-IN", "Kashmiri": "ks-IN", "Konkani": "kok-IN",
    "Maithili": "mai-IN", "Malayalam": "ml-IN", "Manipuri": "mni-IN",
    "Marathi": "mr-IN", "Nepali": "ne-IN", "Odia": "or-IN",
    "Punjabi": "pa-IN", "Sanskrit": "sa-IN", "Santali": "sat-IN",
    "Sindhi": "sd-IN", "Tamil": "ta-IN", "Telugu": "te-IN",
    "Urdu": "ur-IN", "English": "en-IN"
}

# 🚨 Complaint categories and subcategories
CATEGORY_MAP = {
    "STAFF BEHAVIOUR": ["Staff – Behaviour"],
    "SECURITY": ["Smoking", "Drinking Alcohol/Narcotics", "Theft of Passengers' Belongings", "Snatching", "Harassment", "Others"],
    "COACH-CLEANLINESS": ["Toilets", "Cockroach", "Rodents", "Coach-Interior", "Others"],
    "ELECTRICAL-EQUIPMENT": ["Air Conditioner", "Fans", "Lights"],
    "CORRUPTION/BRIBERY": ["Corruption/Bribery"],
    "GOODS": ["Booking", "Delivery", "Overcharging", "Staff Not Available", "Others"],
    "CATERING AND VENDING SERVICES": ["Overcharging", "Service Quality", "Food Quantity", "Food Quality", "Food and Water Not Available", "Others"],
    "MEDICAL ASSISTANCE": ["Medical Assistance"],
    "WATER AVAILABILITY": ["Drinking Water at Platform", "Packaged Drinking Water", "Rail Neer", "Water Vending Machine", "Retiring Room", "Waiting Room", "Toilet", "Others"],
    "MISCELLANEOUS": ["Miscellaneous"]
}

# 📧 Email Credentials (App Passwords)
EMAIL_CREDENTIALS = {
    "tshree4179@gmail.com": "pcxkzqekbymmpywi",
    "vis12356789@gmail.com": "jpprsezowjfabtdi",
    "sphalguna17@gmail.com": "qncwrnpbetipmxvx",
    "mohitv9110@gmail.com": "xbgohksvkgvslisv",
    "sn3951418@gmail.com": "syltqmkdhwdemway",
    "manjushreemr18@gmail.com": "skrdbhwptqxjtyte"
}

# 📧 Email recipients based on category
CATEGORY_EMAILS = {
    "STAFF BEHAVIOUR": "tshree4179@gmail.com",
    "SECURITY": "vis12356789@gmail.com",
    "COACH-CLEANLINESS": "manjushreemr18@gmail.com",
    "ELECTRICAL-EQUIPMENT": "sphalguna17@gmail.com",
    "CORRUPTION/BRIBERY": "sn3951418@gmail.com",
    "GOODS": "tshree4179@gmail.com",
    "CATERING AND VENDING SERVICES": "mohitv9110@gmail.com",
    "MEDICAL ASSISTANCE": "manjushreemr18@gmail.com",
    "WATER AVAILABILITY": "sphalguna17@gmail.com",
    "MISCELLANEOUS": "sn3951418@gmail.com"
}

# 🏢 Station names and dummy phone numbers
STATIONS = [
    {"name": "Mumbai Central", "phone": "022-55501001"},
    {"name": "New Delhi Station", "phone": "011-55501002"},
    {"name": "Chennai Central", "phone": "044-55501003"},
    {"name": "Kolkata Howrah", "phone": "033-55501004"},
    {"name": "Bangalore City", "phone": "080-55501005"},
    {"name": "Hyderabad Deccan", "phone": "040-55501006"},
    {"name": "Ahmedabad Junction", "phone": "079-55501007"},
    {"name": "Pune Junction", "phone": "020-55501008"},
    {"name": "Jaipur Station", "phone": "0141-55501009"},
    {"name": "Lucknow Charbagh", "phone": "0522-55501010"}
]

# 🌐 Placeholder text in different languages for the complaint text area
LANGUAGE_PLACEHOLDERS = {
    "Assamese": "আপোনাৰ অভিযোগ ইয়াত লিখক",
    "Bengali": "এখানে আপনার অভিযোগ লিখুন",
    "Bodo": "निनार खन्थायखौ इयानि लिर",
    "Dogri": "इथे अपणी शिकायत लिखो",
    "Gujarati": "અહીં તમારી ફરિયાદ લખો",
    "Hindi": "यहाँ अपनी शिकायत लिखें",
    "Kannada": "ಇಲ್ಲಿ ನಿಮ್ಮ ದೂರು ಬರೆಯಿರಿ",
    "Kashmiri": "پننہ شکایت ایتھہ لکھو",
    "Konkani": "हांगा तुमची तक्रार बरयात",
    "Maithili": "एहि ठाम अपन शिकायत लिखू",
    "Malayalam": "നിന്റെ പരാതി ഇവിടെ എഴുതുക",
    "Manipuri": "ꯅꯤꯡꯒꯤ ꯊꯥꯖꯤꯟꯕ ꯃꯐꯝ ꯂꯤꯁꯤꯟꯕꯤꯗꯨ",
    "Marathi": "येथे तुमची तक्रार लिहा",
    "Nepali": "यहाँ आफ्नो गुनासो लेख्नुहोस्",
    "Odia": "ଏଠାରେ ଆପଣଙ୍କ ଅଭିଯୋଗ ଲେଖନ୍ତୁ",
    "Punjabi": "ਇੱਥੇ ਆਪਣੀ ਸ਼ਿਕਾਇਤ ਲਿਖੋ",
    "Sanskrit": "अत्र तव संनादति लिख",
    "Santali": "ᱤᱱᱟᱹ ᱟᱢᱟᱜ ᱠᱷᱟᱱᱛᱟᱭ ᱚᱞ",
    "Sindhi": "هتي پنهنجي شڪايت لکو",
    "Tamil": "இங்கு உங்கள் புகாரை எழுதவும்",
    "Telugu": "ఇక్కడ మీ ఫిర్యాదును రాయండి",
    "Urdu": "یہاں اپنی شکایت لکھیں",
    "English": "Enter your complaint here"
}

# 🔧 SQLite Database Setup with Schema Migration
def init_db():
    # Connect to the database in the Documents folder
    conn = sqlite3.connect(r"C:\Users\visma\Documents\complaints.db")
    c = conn.cursor()

    # Check if the table exists
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='complaints'")
    table_exists = c.fetchone()

    # Define the expected columns (added station_name and station_phone)
    expected_columns = [
        "id INTEGER PRIMARY KEY AUTOINCREMENT",
        "phone_number TEXT",
        "pnr_number TEXT",
        "complaint TEXT",
        "category_subcategory TEXT",
        "language TEXT",
        "timestamp TEXT",
        "station_name TEXT",  # New column
        "station_phone TEXT"  # New column
    ]

    if not table_exists:
        # Table doesn't exist, create it with the correct schema
        c.execute(f'''
            CREATE TABLE complaints (
                {", ".join(expected_columns)}
            )
        ''')
    else:
        # Table exists, check its schema
        c.execute("PRAGMA table_info(complaints)")
        existing_columns = [col[1] for col in c.fetchall()]  # Get list of column names

        # Expected column names (without the type definitions)
        expected_column_names = [col.split()[0] for col in expected_columns]

        # Check for missing columns
        missing_columns = [col for col in expected_column_names if col not in existing_columns]

        if missing_columns:
            # If there are missing columns, we need to migrate the table
            # Step 1: Rename the existing table
            c.execute("ALTER TABLE complaints RENAME TO complaints_old")

            # Step 2: Create a new table with the correct schema
            c.execute(f'''
                CREATE TABLE complaints (
                    {", ".join(expected_columns)}
                )
            ''')

            # Step 3: Get the columns in the old table
            c.execute("PRAGMA table_info(complaints_old)")
            old_columns = [col[1] for col in c.fetchall()]

            # Step 4: Migrate data (only for columns that exist in the old table)
            common_columns = [col for col in expected_column_names if col in old_columns and col != "id"]
            if common_columns:
                columns_str = ", ".join(common_columns)
                c.execute(f'''
                    INSERT INTO complaints ({columns_str})
                    SELECT {columns_str}
                    FROM complaints_old
                ''')

            # Step 5: Drop the old table
            c.execute("DROP TABLE complaints_old")

    conn.commit()
    conn.close()

# Initialize the database (no messages displayed)
init_db()

def save_to_db(complaint_data):
    try:
        # Connect to the database in the Documents folder
        conn = sqlite3.connect(r"C:\Users\visma\Documents\complaints.db")
        c = conn.cursor()
        c.execute('''
            INSERT INTO complaints (phone_number, pnr_number, complaint, category_subcategory, language, timestamp, station_name, station_phone)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            complaint_data["phone_number"],
            complaint_data["pnr_number"],
            complaint_data["complaint"],
            complaint_data["category_subcategory"],
            complaint_data["language"],
            complaint_data["timestamp"],
            complaint_data["station_name"],
            complaint_data["station_phone"]
        ))
        conn.commit()
        st.success("✅ Complaint saved to SQLite database successfully!")
    except Exception as e:
        st.error(f"❌ Error saving to database: {e}")
        raise e
    finally:
        conn.close()

def read_from_db():
    try:
        conn = sqlite3.connect(r"C:\Users\visma\Documents\complaints.db")
        df = pd.read_sql_query("SELECT * FROM complaints", conn)
        return df
    except Exception as e:
        st.error(f"❌ Error reading from database: {e}")
        return pd.DataFrame()
    finally:
        conn.close()

def categorize_complaint(complaint_text):
    # Categorize Complaint using Gemini AI
    prompt = (
        f"Classify this railway complaint: '{complaint_text}'. "
        f"Identify all relevant categories and subcategories. "
        f"Return them in the format: 'CATEGORY1 - SUBCATEGORY1, CATEGORY2 - SUBCATEGORY2, ...'. "
        f"Use only from these categories: {CATEGORY_MAP}."
    )
    response = model.generate_content(prompt)
    valid_pairs = []

    if response and response.text:
        ai_output = response.text.strip().upper()
        st.write(f"🟡 AI Output: {ai_output}")
        pairs = [pair.strip() for pair in ai_output.split(',')]
        for pair in pairs:
            if " - " in pair:
                cat, sub = pair.split(" - ", 1)
                cat = cat.strip().upper()
                sub = sub.strip().upper()
                matched_category = next((c for c in CATEGORY_MAP if c.upper() == cat), None)
                if matched_category:
                    valid_subcategories = [s.upper() for s in CATEGORY_MAP[matched_category]]
                    if sub in valid_subcategories:
                        valid_pairs.append((matched_category, sub))
                    else:
                        st.warning(f"⚠ Invalid subcategory '{sub}' for category '{matched_category}'. Skipping.")
                else:
                    st.warning(f"⚠ Invalid category '{cat}'. Skipping.")
            else:
                st.warning(f"⚠ Invalid pair format: '{pair}'. Skipping.")
    if not valid_pairs:
        valid_pairs = [("MISCELLANEOUS", "Others")]

    valid_pairs = list(set(valid_pairs))  # Remove duplicates

    # Group subcategories by category
    category_to_subcategories = defaultdict(list)
    for cat, sub in valid_pairs:
        category_to_subcategories[cat].append(sub)

    return category_to_subcategories

def display_categories(category_to_subcategories):
    # Display categories and subcategories in the desired format
    st.write("📂 Assigned Categories and Subcategories:")
    for category, subcategories in category_to_subcategories.items():
        st.markdown(f'<p class="category-text">{category}</p>', unsafe_allow_html=True)  # Category in white
        for sub in subcategories:
            st.markdown(f'<p class="subcategory-text">  - {sub}</p>', unsafe_allow_html=True)  # Subcategory in white

def assign_station():
    # Randomly select a station from the STATIONS list
    return random.choice(STATIONS)

def display_station(station):
    # Display the assigned station name and phone number
    st.write("🏢 Assigned Station:")
    st.markdown(f'<p class="category-text">{station["name"]}</p>', unsafe_allow_html=True)
    st.markdown(f'<p class="subcategory-text">📞 Phone: {station["phone"]}</p>', unsafe_allow_html=True)

def send_complaint_email(category, subcategories, complaint_text, user_phone, pnr_number, station):
    recipient_email = CATEGORY_EMAILS.get(category, "tshree4179@gmail.com")
    sender_email = recipient_email
    sender_password = EMAIL_CREDENTIALS.get(sender_email, "")
    
    if not sender_password:
        st.error(f"❌ No password found for {sender_email}")
        return
    
    msg = EmailMessage()
    msg["From"] = sender_email
    msg["To"] = recipient_email
    msg["Subject"] = f"🚆 New Railway Complaint - {category}"
    
    subcategories_str = ", ".join(subcategories)
    msg.set_content(f"""
    🚨 New Complaint Submitted 🚨
    
    📂 Category: {category}
    🗂 Subcategories: {subcategories_str}
    📝 Complaint Details: {complaint_text}
    📞 User Phone: {user_phone}
    🎟 PNR Number: {pnr_number}
    🏢 Assigned Station: {station["name"]}
    📞 Station Phone: {station["phone"]}

    Please take necessary action.

    Regards,  
    Railway Complaint System
    """, charset="utf-8")

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        st.success(f"✅ Email sent successfully to {recipient_email} for category {category}")
    except Exception as e:
        st.error(f"❌ Failed to send email to {recipient_email}: {e}")

# Function to apply styles (cached to prevent re-rendering)
@st.cache_resource
def set_styles():
    st.markdown(
        """
        <style>
        /* Apply blurred background image using ::before pseudo-element */
        .stApp::before {
            content: "";
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: url("https://images.pexels.com/photos/31196452/pexels-photo-31196452.jpeg") no-repeat center center fixed;
            background-size: cover;
            filter: blur(20px);  /* Blur set to 20px */
            -webkit-filter: blur(20px);  /* For Safari compatibility */
            z-index: -1;  /* Place it behind the content */
        }
        /* Ensure the main app content is visible with a semi-transparent background */
        .stApp {
            background: rgba(255, 255, 255, 0.85);  /* Increased opacity for better contrast with black text */
            position: relative;
            z-index: 1;  /* Ensure content is above the blurred background */
            min-height: 100vh;  /* Ensure the app takes full height */
        }
        /* Sidebar styling - Transparent background to match the blurred image */
        [data-testid="stSidebar"] {
            background: transparent !important;  /* Transparent to show blurred background */
            z-index: 2;  /* Ensure sidebar is above the background */
        }
        /* Sidebar Title "Navigation" (Black) */
        [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
            color: #000000 !important;  /* Pure black for "Navigation" */
        }
        /* Sidebar Navigation Items (White) - Targeting radio button labels with higher specificity */
        [data-testid="stSidebar"] .stRadio > div > label > div > p {
            color: white !important;
            font-weight: bold !important;
            text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.5) !important;  /* Subtle black shadow for contrast */
        }
        /* Additional selector for the label itself */
        [data-testid="stSidebar"] .stRadio > div > label {
            color: white !important;
        }
        /* Target the text inside the radio button options directly */
        [data-testid="stSidebar"] .stRadio > div > label > div {
            color: white !important;
        }
        /* Fallback for any other text in the sidebar navigation */
        [data-testid="stSidebar"] .stRadio * {
            color: white !important;
        }
        /* Ensure all text within sidebar navigation is white */
        [data-testid="stSidebarNav"] * {
            color: white !important;
        }
        /* Sidebar Links & Buttons (White) */
        [data-testid="stSidebar"] a {
            color: white !important;
        }
        [data-testid="stSidebar"] button {
            color: white !important;
        }
        /* Main content headings (White for contrast) */
        h1, h2, h3 {
            color: white !important;
            font-size: 35px !important;
            text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.5);  /* Add shadow for better readability */
        }
        /* Subheadings and labels (Darker black for readability) */
        h4, h5, h6, p, label {
            color: #000000 !important;  /* Pure black */
            font-size: 35px !important;
        }
        /* Input fields styling */
        input, textarea {
            font-size: 30px !important;
            color: #000000 !important;  /* Pure black text in inputs */
            background-color: white !important;  /* White background for input fields */
            border: 1px solid #000000 !important;  /* Pure black border for visibility */
            font-family: 'Noto Sans', sans-serif !important;  /* Font supporting multiple languages */
        }
        /* Button Styling */
        .stButton>button {
            color: #000000 !important;  /* Pure black text on buttons */
            font-size: 30px !important;
            background-color: white !important;
            border: 1px solid #000000 !important;  /* Pure black border for visibility */
        }
        /* Centered Home Title (black with shadow) */
        .centered-title {
            text-align: center;
            font-size: 80px !important;  /* Larger title */
            font-weight: bold;
            color: black !important;
            text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.5);  /* Shadow for readability */
            margin-top: 50px;
        }
        /* Category styling in Admin Panel (White with shadow) */
        .category-text {
            font-size: 35px !important;
            color: white !important;
            text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.5);  /* Shadow for readability */
        }
        /* Subcategory styling in Admin Panel (White with shadow) */
        .subcategory-text {
            font-size: 28px !important;
            color: white !important;
            text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.5);  /* Shadow for readability */
        }
        /* General text in main content (Darker black for readability) */
        .stMarkdown, .stText, .stRadio > label, .stSelectbox > label, .stTextInput > label, .stTextArea > label {
            color: #000000 !important;  /* Pure black */
            font-family: 'Noto Sans', sans-serif !important;  /* Font supporting multiple languages */
        }
        /* Help page text (Darker black for readability) */
        .help-info, .stMarkdown {
            color: #000000 !important;  /* Pure black */
            font-family: 'Noto Sans', sans-serif !important;  /* Font supporting multiple languages */
        }
        /* Ensure all text elements use a font that supports multiple languages */
        * {
            font-family: 'Noto Sans', sans-serif !important;
        }
        </style>
        <link href="https://fonts.googleapis.com/css2?family=Noto+Sans:ital,wght@0,400;0,700;1,400;1,700&family=Noto+Sans+Assamese&family=Noto+Sans+Bengali&family=Noto+Sans+Devanagari&family=Noto+Sans+Gujarati&family=Noto+Sans+Kannada&family=Noto+Sans+Malayalam&family=Noto+Sans+Oriya&family=Noto+Sans+Punjabi&family=Noto+Sans+Tamil&family=Noto+Sans+Telugu&family=Noto+Sans+Urdu&display=swap" rel="stylesheet">
        """,
        unsafe_allow_html=True
    )
# Apply styles after set_page_config
set_styles()

# Sidebar setup
st.sidebar.image(r"C:\Users\visma\Downloads\Indian_Railway_Logo_2.png", width=250)  # Logo in sidebar
st.sidebar.title("📌 Navigation")
menu = ["Home", "File a Complaint", "Admin Panel", "Help"]
choice = st.sidebar.radio("Go to", menu)

# Initialize session state
if "audio_path" not in st.session_state:
    st.session_state["audio_path"] = None
if "complaint_data" not in st.session_state:
    st.session_state["complaint_data"] = []

# 📩 Submit Complaint (User Side)
if choice == "File a Complaint":
    st.title("📩 File a Complaint")
    phone_number = st.text_input("📞 Enter Phone Number")
    pnr_number = st.text_input("🎟 Enter PNR Number")

    # 🚨 Validate PNR
    if pnr_number and pnr_number not in VALID_PNR_NUMBERS:
        st.error("❌ Invalid PNR number! Please enter a valid PNR from PNRA1–PNRA10 or PNRB1–PNRB10.")
        st.stop()

    # 🌍 Select Language
    language = st.selectbox("🌎 Choose Complaint Language", list(LANGUAGE_MAP.keys()))
    selected_lang_code = LANGUAGE_MAP[language]

    # 🎤 Complaint Input Method
    st.subheader("📝 How would you like to submit your complaint?")
    input_method = st.radio("Select Input Method", ["Record/Upload Audio", "Type Complaint"])

    if input_method == "Record/Upload Audio":
        st.subheader("🎙 Record or Upload Complaint Audio")
        col1, col2 = st.columns(2)

        with col1:
            if st.button("🎙 Start Recording (10 sec)"):
                st.write("✅ Recording started! Speak now.")
                temp_audio_path = tempfile.NamedTemporaryFile(delete=False, suffix=".wav").name
                audio_data = sd.rec(int(10 * 44100), samplerate=44100, channels=1, dtype=np.int16)
                sd.wait()
                with wave.open(temp_audio_path, 'wb') as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(44100)
                    wf.writeframes(audio_data.tobytes())
                st.session_state["audio_path"] = temp_audio_path
                st.success("✅ Recording Completed!")

        with col2:
            uploaded_file = st.file_uploader("📂 Upload an Audio File", type=["wav", "mp3", "m4a"])
            if uploaded_file:
                temp_audio_path = tempfile.NamedTemporaryFile(delete=False, suffix=".wav").name
                with open(temp_audio_path, "wb") as f:
                    f.write(uploaded_file.read())
                st.session_state["audio_path"] = temp_audio_path
                st.success("✅ File Uploaded Successfully.")

        if st.session_state["audio_path"]:
            # Transcribe the audio
            st.write("⏳ Transcribing Audio Complaint...")
            recognizer = sr.Recognizer()
            with sr.AudioFile(st.session_state["audio_path"]) as source:
                audio_data = recognizer.record(source)
            try:
                complaint_text = recognizer.recognize_google(audio_data, language=selected_lang_code)
                st.success("✅ Transcription completed!")
            except sr.UnknownValueError:
                complaint_text = "❌ Could not understand the audio."
                st.error(complaint_text)
                st.stop()
            except sr.RequestError:
                complaint_text = "❌ Speech Recognition API unavailable."
                st.error(complaint_text)
                st.stop()

            # Show transcribed text with edit option
            st.write("🎤 Transcribed Complaint:")
            edited_complaint = st.text_area("Edit your complaint if needed:", complaint_text, height=150)

            if st.button("📩 Submit Audio Complaint", key="submit_audio"):
                # Categorize the complaint using the edited text
                category_to_subcategories = categorize_complaint(edited_complaint)

                # Display categories and subcategories
                display_categories(category_to_subcategories)

                # Store the complaint for admin review
                st.session_state["complaint_data"].append({
                    "phone_number": phone_number,
                    "pnr_number": pnr_number,
                    "audio_path": st.session_state["audio_path"],
                    "language_code": selected_lang_code,
                    "input_type": "audio",
                    "complaint_text": edited_complaint  # Store the edited text
                })
                st.session_state["audio_path"] = None  # Reset audio path

                # Show confirmation message
                st.success("✅ Complaint successfully submitted and sent to Admin Panel for review!")

    elif input_method == "Type Complaint":
        st.subheader("✍ Type Your Complaint")
        # Use the placeholder in the selected language
        placeholder_text = LANGUAGE_PLACEHOLDERS.get(language, "Enter your complaint here")
        typed_complaint = st.text_area("Enter your complaint here", height=150, placeholder=placeholder_text)
        
        if st.button("📩 Submit Typed Complaint", key="submit_typed"):
            if typed_complaint:
                # Categorize the complaint
                category_to_subcategories = categorize_complaint(typed_complaint)

                # Display categories and subcategories
                display_categories(category_to_subcategories)

                # Store the complaint for admin review
                st.session_state["complaint_data"].append({
                    "phone_number": phone_number,
                    "pnr_number": pnr_number,
                    "complaint_text": typed_complaint,
                    "language_code": selected_lang_code,
                    "input_type": "text",
                    "language": language  # Store the language for reference
                })
                
                # Show confirmation message
                st.success("✅ Complaint successfully submitted and sent to Admin Panel for review!")
            else:
                st.error("❌ Please enter a complaint before submitting.")

# 🔒 Admin Panel
elif choice == "Admin Panel":
    st.title("🔒 Admin Panel")
    password = st.text_input("Enter Admin Password", type="password")
    if password != "admin123":  # Simple password check (replace with a secure method)
        st.error("❌ Incorrect password!")
        st.stop()

    st.subheader("Pending Complaints")
    if not st.session_state["complaint_data"]:
        st.write("No pending complaints.")
    else:
        for idx, complaint in enumerate(st.session_state["complaint_data"]):
            st.write(f"Complaint {idx + 1}:")
            st.write(f"Phone: {complaint['phone_number']}, PNR: {complaint['pnr_number']}")
            st.write(f"Language: {complaint.get('language', 'Not specified')}")

            # Handle complaint based on input type
            if complaint["input_type"] == "audio":
                # Use the already transcribed text
                complaint_text = complaint["complaint_text"]
            else:  # input_type == "text"
                st.write("📝 Typed Complaint:")
                complaint_text = complaint["complaint_text"]

            edited_text = st.text_area(f"Edit Complaint Text (Complaint {idx + 1}):", complaint_text, height=150, key=f"edit_{idx}")

            if st.button(f"Process Complaint {idx + 1}", key=f"process_{idx}"):
                # Categorize Complaint using Gemini AI
                category_to_subcategories = categorize_complaint(edited_text)

                # Display categories and subcategories
                display_categories(category_to_subcategories)

                # Assign a station
                assigned_station = assign_station()
                display_station(assigned_station)

                # Save to SQLite
                category_subcategory_str = ", ".join([f"{cat} - {sub}" for cat, subs in category_to_subcategories.items() for sub in subs])
                complaint_data = {
                    "phone_number": complaint["phone_number"],
                    "pnr_number": complaint["pnr_number"],
                    "complaint": edited_text,
                    "category_subcategory": category_subcategory_str,
                    "language": complaint.get("language", "Not specified"),
                    "timestamp": datetime.now().isoformat(),
                    "station_name": assigned_station["name"],
                    "station_phone": assigned_station["phone"]
                }
                save_to_db(complaint_data)

                # Send emails for each unique category
                for category, subcategories in category_to_subcategories.items():
                    send_complaint_email(category, subcategories, edited_text, complaint["phone_number"], complaint["pnr_number"], assigned_station)

                # Remove processed complaint
                st.session_state["complaint_data"].pop(idx)
                st.success("✅ Complaint processed and removed from pending list!")

    # Display all complaints from the database
    st.subheader("All Processed Complaints")
    df = read_from_db()
    if not df.empty:
        st.dataframe(df)
    else:
        st.write("No processed complaints found in the database.")

# ℹ Help Page
elif choice == "Help":
    st.title("ℹ Help & Information")
    st.write("""
    ### How to Use the Railway Complaint System
    1. Enter Details: Provide your phone number and PNR number.
    2. Select Language: Choose your preferred language for the complaint.
    3. Submit Complaint: Either record/upload an audio complaint or type your complaint directly.
    4. Submit: Submit for admin review.
    5. Admin Panel: Admins can process complaints, categorize them, and send emails.

    ### Supported Categories
    Your complaint can be classified into multiple categories and subcategories, such as:
    - STAFF BEHAVIOUR: Staff – Behaviour
    - SECURITY: Smoking, Theft, etc.
    - COACH-CLEANLINESS: Toilets, Cockroach, etc.
    - And more...

    ### Contact
    For assistance, email: support@railwaycomplaints.com
    """)

# Home Page
elif choice == "Home":
    st.markdown('<h1 class="centered-title">🚆 Railway Complaint System</h1>', unsafe_allow_html=True)