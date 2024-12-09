import streamlit as st
from whisper_stt import whisper_stt
from dotenv import load_dotenv
import os
import openai
import json
from datetime import datetime
import re
from streamlit.components.v1 import html
import pyperclip
from pymongo import MongoClient
from bson.objectid import ObjectId
from user_utils import create_user, verify_user
import ssl
import hashlib
import hmac
load_dotenv()

openai.api_key = os.getenv('OPENAI_API_KEY')

# Initialize session state right after imports and before any other Streamlit commands
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False
    st.session_state['provider_id'] = None

# Initialize connection


@st.cache_resource
def init_connection():
    try:
        # Add SSL configuration and increase timeouts
        client = MongoClient(
            os.getenv('MONGO_URI')
        )
        # Test the connection
        client.admin.command('ping')
        return client
    except Exception as e:
        st.error(f"Could not connect to MongoDB: {str(e)}")
        return None


# Initialize the client
mongo_client = init_connection()
if mongo_client:
    db = mongo_client['scriber']

else:
    st.error("Failed to initialize MongoDB connection")
    st.stop()


def load_system_prompts():
    """Load system prompts from MongoDB"""
    try:
        prompts = {}
        query = {"provider_id": st.session_state.provider_id}
        prompts_cursor = db.system_messages.find(query)

        # If no prompts exist, create a default one
        if db.system_messages.count_documents(query) == 0:
            default_prompt = {
                "name": "Default Summary",
                "content": "You are a medical scribe assistant. Create a concise, professional summary of the medical conversation, highlighting key symptoms, diagnoses, and treatment plans. Format the summary in a clear, medical-note style.",
                "provider_id": st.session_state.provider_id,
                "created_at": datetime.now(),
                "last_modified": datetime.now()
            }
            db.system_messages.insert_one(default_prompt)
            prompts[default_prompt["name"]] = default_prompt["content"]
        else:
            for doc in prompts_cursor:
                prompts[doc['name']] = doc['content']

        return prompts
    except Exception as e:
        st.error(f"Error loading system prompts: {str(e)}")
        return {}


def save_system_prompts(prompts):
    """Save system prompts to MongoDB"""
    try:
        # Clear existing prompts for this provider
        db.system_messages.delete_many(
            {"provider_id": st.session_state.provider_id})

        # Insert new prompts
        for name, content in prompts.items():
            db.system_messages.insert_one({
                "name": name,
                "content": content,
                "provider_id": st.session_state.provider_id,
                "created_at": datetime.now(),
                "last_modified": datetime.now()
            })
    except Exception as e:
        st.error(f"Error saving system prompts: {str(e)}")


first_name = ""
last_name = ""


def get_summary(transcript, system_prompt):
    response = openai.chat.completions.create(

        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": transcript}
        ]
    )

    return response.choices[0].message.content


def save_recording_data(transcript, summary):
    """
    Save the recording data to the mongo database and return the document ID
    """
    result = db.recordings.insert_one({
        "transcript": transcript,
        "summary": summary,
        "provider_id": st.session_state.provider_id,
        "patient_id": st.session_state.selected_patient_id,
        "timestamp": datetime.now(),
        "last_modified": datetime.now()
    })
    return str(result.inserted_id)


def update_recording_data(document_id, transcript, summary):
    """
    Update an existing recording in the database
    """
    db.recordings.update_one(
        {"_id": ObjectId(document_id)},
        {
            "$set": {
                "transcript": transcript,
                "summary": summary,
                "last_modified": datetime.now()
            }
        }
    )


def get_patient_recordings(patient_id):
    """
    Get all recordings for a specific patient
    """
    return list(db.recordings.find({
        "patient_id": patient_id,
        "provider_id": st.session_state.provider_id
    }).sort("timestamp", -1))


def load_recording_data(document_id):
    return db.recordings.find_one({"_id": ObjectId(document_id)})


def get_all_patients():
    """Get all patients for the current provider"""
    try:
        patients = list(db.patients.find(
            {"provider_id": st.session_state.provider_id},
            {"first_name": 1, "last_name": 1}
        ).sort("last_name", 1))

        return [(p["first_name"], p["last_name"], str(p["_id"])) for p in patients]
    except Exception as e:
        st.error(f"Error fetching patients from database: {str(e)}")
        return []


def split_patient_name(combined_name):
    # Split the name into first and last name based on space or hyphen
    parts = re.split(r'[- ]', combined_name)
    if len(parts) >= 2:
        return parts[0], ' '.join(parts[1:])
    return combined_name, ""


# Add this new function after the imports
def create_copy_button(text, button_id):
    """Create a copy button for the specified text"""
    # Escape special characters for JavaScript
    escaped_text = text.replace('`', '\\`').replace(
        '\\', '\\\\').replace('\n', '\\n')
    copy_js = f"""
        <script>
        function copyText{button_id}() {{
            const text = `{escaped_text}`;
            navigator.clipboard.writeText(text).then(function() {{
                console.log('Text copied');
            }}).catch(function(err) {{
                console.error('Failed to copy text:', err);
            }});
        }}
        </script>
        <button 
            onclick="copyText{button_id}()"
            style="background-color: transparent; border: none; padding: 0; margin-left: 5px; cursor: pointer; font-size: 20px;"
        >
            🔗
        </button>
    """
    return copy_js


def save_patient_data(first_name, last_name, notes=""):
    """Save patient data to MongoDB database"""
    result = db.patients.insert_one({
        "first_name": first_name,
        "last_name": last_name,
        "notes": notes,
        "provider_id": st.session_state.provider_id,
        "created_at": datetime.now(),
        "last_modified": datetime.now()
    })
    return str(result.inserted_id)


def update_patient_notes(patient_id, notes):
    """
    Update patient notes in MongoDB database
    """
    db.patients.update_one(
        {"_id": ObjectId(patient_id)},
        {
            "$set": {
                "notes": notes,
                "last_modified": datetime.now()
            }
        }
    )


def get_patient_notes(patient_id):
    """
    Get patient notes from MongoDB database
    """
    patient = db.patients.find_one({"_id": ObjectId(patient_id)})
    return patient.get("notes", "") if patient else ""


# Authentication UI
if not st.session_state.authenticated:
    st.title("Login")

    tab1, tab2 = st.tabs(["Login", "Register"])

    with tab1:
        login_email = st.text_input("Email", key="login_email_field")
        login_password = st.text_input(
            "Password", type="password", key="login_password_field")

        if st.button("Login", key="login_button"):
            provider_id = verify_user(login_email, login_password, db)
            if provider_id:
                st.session_state.authenticated = True
                st.session_state.provider_id = provider_id
                st.success("Logged in successfully!")
                st.rerun()
            else:
                st.error("Invalid email or password")

    with tab2:
        new_email = st.text_input("Email", key="register_email")
        new_password = st.text_input(
            "Password", type="password", key="register_password")
        confirm_password = st.text_input("Confirm Password", type="password")

        if st.button("Register"):
            if new_password != confirm_password:
                st.error("Passwords do not match")
            elif not new_email or not new_password:
                st.error("Please fill in all fields")
            else:
                success, message = create_user(new_email, new_password, db)
                if success:
                    st.success(message)
                else:
                    st.error(message)

    st.stop()  # Prevent the rest of the app from loading

# Original app code starts here
st.title("Scribe")

# Sidebar for patient selection
with st.sidebar:
    if st.button("Logout"):
        st.session_state.authenticated = False
        st.rerun()

    st.divider()
    st.header("Patient Selection")
    patients = get_all_patients()
    if 'selected_patient' not in st.session_state:
        st.session_state.selected_patient = ""
        st.session_state.first_name = ""
        st.session_state.last_name = ""

    if patients:
        # Format patient names for display
        patient_options = [""] + [f"{p[0]} {p[1]}" for p in patients]
        patient_ids = {f"{p[0]} {p[1]}": p[2] for p in patients}

        selected_patient = st.selectbox(
            "Select Existing Patient",
            options=patient_options,
            format_func=lambda x: "Select a patient..." if x == "" else x,
            index=patient_options.index(
                st.session_state.selected_patient) if st.session_state.selected_patient in patient_options else 0
        )

        st.session_state.selected_patient = selected_patient

        if selected_patient:
            first_name, last_name = split_patient_name(selected_patient)
            st.session_state.first_name = first_name
            st.session_state.last_name = last_name
            # Store the patient ID in session state
            st.session_state.selected_patient_id = patient_ids.get(
                selected_patient)
        else:
            st.session_state.first_name = ""
            st.session_state.last_name = ""
            st.session_state.selected_patient_id = None

        st.divider()

    st.subheader("Or Create New patient")
    new_first_name = st.text_input("First Name")
    new_last_name = st.text_input("Last Name")

    if st.button("Create New patient"):
        if new_first_name and new_last_name:
            # Capitalize first and last name for directory creation
            formatted_first_name = new_first_name.capitalize()
            formatted_last_name = new_last_name.capitalize()
            new_patient_dir = os.path.join(
                'recordings', f"{formatted_first_name}-{formatted_last_name}")
            os.makedirs(new_patient_dir, exist_ok=True)

            # Save patient to MongoDB
            try:
                patient_id = save_patient_data(
                    formatted_first_name, formatted_last_name)
                st.success(
                    f"Created new patient: {formatted_first_name} {formatted_last_name}")
                # Automatically select the new patient
                st.session_state.selected_patient = f"{formatted_first_name} {formatted_last_name}"
                st.session_state.first_name = formatted_first_name
                st.session_state.last_name = formatted_last_name
                st.rerun()
            except Exception as e:
                st.error(f"Error saving patient to database: {str(e)}")
        else:
            st.error("Please enter both first and last name")

    # Add system prompt in a collapsed expander
    st.divider()
    with st.expander("Select System Prompt", expanded=False):
        # Load all prompts
        system_prompts = load_system_prompts()

        # Prompt selector
        selected_prompt_name = st.selectbox(
            "Select a prompt template:",
            options=list(system_prompts.keys())
        )

        # Show and allow editing of the selected prompt
        updated_prompt = st.text_area(
            "Customize the selected prompt:",
            value=system_prompts[selected_prompt_name],
            height=150
        )

        # Save changes to existing prompt
        if updated_prompt != system_prompts[selected_prompt_name]:
            system_prompts[selected_prompt_name] = updated_prompt
            save_system_prompts(system_prompts)
            st.success("Prompt updated successfully!")

        # Add new prompt button
        new_prompt_name = st.text_input("New prompt name")
        if st.button("Add New Prompt"):
            if new_prompt_name:
                if new_prompt_name in system_prompts:
                    st.error("A prompt with this name already exists!")
                else:
                    system_prompts[new_prompt_name] = "Enter your prompt here"
                    save_system_prompts(system_prompts)
                    st.success("New prompt template added!")
                    st.rerun()

    # Add this right after the system prompt expander in the sidebar
    with st.sidebar:
        st.divider()
        st.markdown("**Current Prompt Template:**")
        st.info(selected_prompt_name)


# In the main content area
if st.session_state.selected_patient:
    st.header(
        f"{st.session_state.first_name} {st.session_state.last_name}".title())

    # Load notes from MongoDB
    if 'notes' not in st.session_state:
        st.session_state.notes = get_patient_notes(
            st.session_state.selected_patient_id)

    st.subheader("Notes")
    notes = st.text_area("Enter your notes here:",
                         value=st.session_state.notes,
                         height=150)

    # Save notes to MongoDB when the save button is clicked
    if st.button("Save Notes"):
        update_patient_notes(st.session_state.selected_patient_id, notes)
        st.session_state.notes = notes
        st.success("Notes saved successfully!")

    st.header("Recording Session")

    # Move the recording functionality here
    transcript = whisper_stt(openai_api_key=os.getenv(
        'OPENAI_API_KEY'), language='en')

    # Rest of the recording logic...
    if transcript:
        # Only process and save if it's a new transcript
        if 'last_transcript' not in st.session_state or transcript != st.session_state.last_transcript:
            st.session_state.last_transcript = transcript

            # Generate summary
            try:
                with st.spinner('Generating summary...'):
                    # Use the updated system prompt
                    system_prompt = updated_prompt
                    messages = [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": transcript}
                    ]

                    response = openai.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=messages
                    )
                    summary = response.choices[0].message.content

                    # Save to disk immediately
                    st.session_state.current_file = save_recording_data(
                        transcript, summary)
                    st.success("Recording saved successfully!")
            except Exception as e:
                st.error(f"Error processing recording: {str(e)}")
                st.stop()

        # Load the saved data from disk
        if st.session_state.current_file:
            saved_data = load_recording_data(st.session_state.current_file)

            # Create two columns for transcript and summary
            col1, col2 = st.columns(2)

            with col1:
                # Create a container for subheader and icon
                header_col1, header_col2 = st.columns([0.8, 0.2])
                with header_col1:
                    st.subheader("Transcript")
                with header_col2:
                    st.write("")  # Spacing for vertical alignment
                    if st.button("🔗", key=f"copy_transcript_{saved_data['transcript'][:10]}", use_container_width=False):
                        pyperclip.copy(saved_data["transcript"])
                        st.toast('Copied to clipboard!')

                edited_transcript = st.text_area(
                    label="Transcript content",
                    label_visibility="hidden",
                    value=saved_data["transcript"],
                    height=300,
                    key="current_transcript"
                )

            with col2:
                # Create a container for subheader and icon
                header_col1, header_col2, header_col3 = st.columns(
                    [0.6, 0.2, 0.2])
                with header_col1:
                    st.subheader("Summary")
                with header_col2:
                    st.write("")  # Spacing for vertical alignment
                    if st.button("🔗", key=f"copy_summary_{saved_data['summary'][:10]}", use_container_width=False):
                        pyperclip.copy(saved_data["summary"])
                        st.toast('Copied to clipboard!')
                with header_col3:
                    if st.button("🔄", key="regenerate_summary", use_container_width=False):
                        with st.spinner('Generating new summary...'):
                            # Use the updated system prompt
                            new_summary = get_summary(
                                edited_transcript, updated_prompt)
                            # Update the saved data with new summary
                            update_recording_data(
                                st.session_state.current_file, edited_transcript, new_summary)
                            st.success("Summary regenerated successfully!")
                            st.rerun()

                edited_summary = st.text_area(
                    label="Summary content",
                    label_visibility="hidden",
                    value=saved_data["summary"],
                    height=300,
                    key="current_summary"
                )

            # Add a button to save changes
            if st.button("Save Changes", key="save_current_btn"):
                save_recording_data(edited_transcript, edited_summary,
                                    filename=st.session_state.current_file)
                st.success("Changes saved successfully!")

    # Add a section to load and edit previous recordings
    with st.expander("Load Previous Recordings"):
        recordings = get_patient_recordings(
            st.session_state.selected_patient_id)
        if recordings:
            # Format options for the selectbox
            recording_options = [
                (r["timestamp"].strftime("%Y-%m-%d %H:%M"), str(r["_id"]))
                for r in recordings
            ]

            selected_recording = st.selectbox(
                "Select a recording to edit:",
                options=[r[1] for r in recording_options],
                format_func=lambda x: next(
                    r[0] for r in recording_options if r[1] == x),
                key="recording_selector"
            )

            if selected_recording:
                data = load_recording_data(selected_recording)

                # Format the last_modified date directly since it's already a datetime object
                formatted_date = data['last_modified'].strftime(
                    "%Y-%m-%d %H:%M")

                col1, col2 = st.columns(2)

                with col1:
                    # Create a container for subheader and icon
                    header_col1, header_col2 = st.columns([0.8, 0.2])
                    with header_col1:
                        st.subheader("Transcript")
                    with header_col2:
                        st.write("")  # Spacing for vertical alignment
                        if st.button("🔗", key=f"copy_transcript_prev_{selected_recording}", use_container_width=False):
                            pyperclip.copy(data["transcript"])
                            st.toast('Copied to clipboard!')
                    edited_transcript = st.text_area(
                        label="Previous transcript content",
                        label_visibility="hidden",
                        value=data["transcript"],
                        height=300,
                        key="previous_transcript"
                    )

                with col2:
                    # Create a container for subheader and icon
                    header_col1, header_col2, header_col3 = st.columns(
                        [0.6, 0.2, 0.2])
                    with header_col1:
                        st.subheader("Summary")
                    with header_col2:
                        st.write("")  # Spacing for vertical alignment
                        if st.button("🔗", key=f"copy_summary_prev_{selected_recording}", use_container_width=False):
                            pyperclip.copy(data["summary"])
                            st.toast('Copied to clipboard!')
                    with header_col3:
                        if st.button("🔄", key=f"regenerate_summary_prev_{selected_recording}", use_container_width=False):
                            with st.spinner('Generating new summary...'):
                                # Use the updated system prompt
                                new_summary = get_summary(
                                    edited_transcript, updated_prompt)
                                update_recording_data(
                                    selected_recording, edited_transcript, new_summary)
                                st.success(
                                    "Summary regenerated successfully!")
                                st.rerun()

                    edited_summary = st.text_area(
                        label="Previous summary content",
                        label_visibility="hidden",
                        value=data["summary"],
                        height=300,
                        key="previous_summary"
                    )

                # Display formatted last updated date
                st.markdown(f"**Last Updated:** {formatted_date}")

                if st.button("Save Changes to Selected Recording", key="save_previous_btn"):
                    update_recording_data(
                        selected_recording,
                        edited_transcript,
                        edited_summary
                    )
                    st.success("Changes saved successfully!")
        else:
            st.info("No previous recordings found for this patient")
else:
    st.info("Please select a patient from the sidebar")

# Add these functions after the existing initialization code


def hash_password(password):
    """Hash a password using SHA-256"""
    salt = os.getenv('PASSWORD_SALT', 'default_salt')
    return hmac.new(salt.encode(), password.encode(), hashlib.sha256).hexdigest()


def create_user(email, password):
    """Create a new user in the database"""
    if db.users.find_one({"email": email}):
        return False, "Email already exists"

    hashed_password = hash_password(password)
    db.users.insert_one({
        "email": email,
        "password": hashed_password,
        "created_at": datetime.now()
    })
    return True, "User created successfully"


def verify_user(email, password):
    """Verify user credentials"""
    user = db.users.find_one({"email": email})
    if not user:
        return False

    hashed_password = hash_password(password)
    return hmac.compare_digest(user['password'], hashed_password)


# Add this right after the load_dotenv() call
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
