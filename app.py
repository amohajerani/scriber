import streamlit as st
from whisper_stt import whisper_stt
from dotenv import load_dotenv
import os
import openai
import json
from datetime import datetime
import re

load_dotenv()
openai.api_key = os.getenv('OPENAI_API_KEY')

# Load system prompt from a file


def load_system_prompt(file_path):
    with open(file_path, 'r') as file:
        return file.read().strip()

# Save updated system prompt to a file


def save_system_prompt(file_path, prompt):
    with open(file_path, 'w') as file:
        file.write(prompt)


system_prompt_file = 'system-prompt.txt'
system_prompt = load_system_prompt(system_prompt_file)

# Default system prompt
DEFAULT_SYSTEM_PROMPT = """Please provide a concise summary of the following transcript, 
highlighting the key points and main ideas discussed."""

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


def save_recording_data(transcript, summary, first_name, last_name, filename=None):
    # Create base recordings directory
    os.makedirs('recordings', exist_ok=True)

    # Create user-specific directory using first and last name
    user_dir = os.path.join('recordings', f"{first_name}-{last_name}")
    os.makedirs(user_dir, exist_ok=True)

    # Generate filename based on timestamp if not provided
    if not filename:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H:%M")
        filename = os.path.join(user_dir, f"recording_{timestamp}.json")

    data = {
        "first_name": first_name,
        "last_name": last_name,
        "transcript": transcript,
        "summary": summary,
        "last_modified": datetime.now().isoformat()
    }

    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)

    return filename


def load_recording_data(filename):
    with open(filename, 'r') as f:
        return json.load(f)


def get_all_users():
    if not os.path.exists('recordings'):
        return []
    users = [d for d in os.listdir('recordings') if os.path.isdir(
        os.path.join('recordings', d))]
    # Reformat user names for display by replacing hyphens with spaces
    formatted_users = [d.replace('-', ' ') for d in users]
    return formatted_users


def split_user_name(combined_name):
    # Split the name into first and last name based on space or hyphen
    parts = re.split(r'[- ]', combined_name)
    if len(parts) >= 2:
        return parts[0], ' '.join(parts[1:])
    return combined_name, ""


# Streamlit UI
st.title("Scribe")

# Sidebar for user selection
with st.sidebar:
    st.header("User Selection")
    users = get_all_users()
    if 'selected_user' not in st.session_state:
        st.session_state.selected_user = ""
    selected_user = st.session_state.selected_user
    if users:
        selected_user = st.selectbox(
            "Select Existing User",
            options=[""] + users,
            format_func=lambda x: "Select a user..." if x == "" else x,
            index=users.index(selected_user) +
            1 if selected_user in users else 0
        )

        if selected_user:
            first_name, last_name = split_user_name(selected_user)
        else:
            first_name = last_name = ""

        st.divider()

    st.subheader("Or Create New User")
    new_first_name = st.text_input("First Name")
    new_last_name = st.text_input("Last Name")

    if st.button("Create New User"):
        if new_first_name and new_last_name:
            # Capitalize first and last name for directory creation
            formatted_first_name = new_first_name.capitalize()
            formatted_last_name = new_last_name.capitalize()
            new_user_dir = os.path.join(
                'recordings', f"{formatted_first_name}-{formatted_last_name}")
            os.makedirs(new_user_dir, exist_ok=True)
            st.success(
                f"Created new user: {formatted_first_name} {formatted_last_name}")
            # Automatically select the new user
            st.session_state.selected_user = f"{formatted_first_name} {formatted_last_name}"
            st.session_state.first_name = formatted_first_name
            st.session_state.last_name = formatted_last_name
            st.rerun()
        else:
            st.error("Please enter both first and last name")

    # Add system prompt in a collapsed expander
    st.divider()
    with st.expander("System Prompt", expanded=False):
        updated_system_prompt = st.text_area(
            "Customize the prompt for GPT:",
            value=system_prompt,
            height=150
        )

        # Save the updated system prompt if it has changed
        if updated_system_prompt != system_prompt:
            save_system_prompt(system_prompt_file, updated_system_prompt)
            # Update the current session's system_prompt
            system_prompt = updated_system_prompt
            st.success("System prompt updated successfully!")


# In the main content area, display the selected user's name
if selected_user:
    # Load notes from file if it exists
    notes_file_path = os.path.join(
        'recordings', f"{first_name}-{last_name}", 'notes.txt')  # Use hyphen
    if os.path.exists(notes_file_path):
        with open(notes_file_path, 'r') as f:
            st.session_state.notes = f.read()
    st.header(f"{first_name} {last_name}".title())
    # Text area for notes
    st.subheader("Notes")
    notes = st.text_area("Enter your notes here:",
                         value=st.session_state.notes, height=150)

    # Save notes to file when the save button is clicked
    if st.button("Save Notes"):
        with open(notes_file_path, 'w') as f:
            f.write(notes)
        st.success("Notes saved successfully!")
        st.session_state.notes = notes
    st.header("Recording Session")

# Update session state with the selected user's information
if 'first_name' not in st.session_state or st.session_state.first_name != first_name:
    st.session_state.first_name = first_name
if 'last_name' not in st.session_state or st.session_state.last_name != last_name:
    st.session_state.last_name = last_name

# Initialize session state for notes if it doesn't exist or if the user has changed
if 'notes' not in st.session_state or st.session_state.selected_user != selected_user:
    st.session_state.notes = ""


# Initialize session state for summary if it doesn't exist
if 'summary' not in st.session_state:
    st.session_state.summary = ""
if 'last_transcript' not in st.session_state:
    st.session_state.last_transcript = ""

# Initialize session state for file tracking
if 'current_file' not in st.session_state:
    st.session_state.current_file = None

transcript = whisper_stt(openai_api_key=os.getenv(
    'OPENAI_API_KEY'), language='en')

# If you don't pass an API key, the function will attempt to retrieve it as an environment variable : 'OPENAI_API_KEY'.
if transcript:
    # Only process and save if it's a new transcript
    if 'last_transcript' not in st.session_state or transcript != st.session_state.last_transcript:
        st.session_state.last_transcript = transcript

        # Generate summary
        try:
            with st.spinner('Generating summary...'):
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
                    transcript, summary, first_name, last_name)
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
            st.subheader("Transcript")
            edited_transcript = st.text_area(
                "Edit transcript:",
                value=saved_data["transcript"],
                height=300,
                key="current_transcript"
            )

        with col2:
            st.subheader("Summary")
            edited_summary = st.text_area(
                "Edit summary:",
                value=saved_data["summary"],
                height=300,
                key="current_summary"
            )

        # Add a button to save changes
        if st.button("Save Changes", key="save_current_btn"):
            save_recording_data(edited_transcript, edited_summary, first_name, last_name,
                                filename=st.session_state.current_file)
            st.success("Changes saved successfully!")

# Add a section to load and edit previous recordings
if st.session_state.selected_user:
    with st.expander("Load Previous Recordings"):
        if selected_user:
            user_dir = os.path.join('recordings', selected_user.replace(
                ' ', '-'))  # Convert space to hyphen
            if os.path.exists(user_dir):
                recording_files = [f for f in os.listdir(
                    user_dir) if f.endswith('.json')]
                if recording_files:
                    selected_file = st.selectbox(
                        "Select a recording to edit:",
                        recording_files,
                        format_func=lambda x: x.split('_')[1].split('.')[
                            0],  # Show timestamp only
                        key="recording_selector"
                    )

                    if selected_file:
                        file_path = os.path.join(user_dir, selected_file)
                        data = load_recording_data(file_path)

                        # Format the last_modified date
                        last_modified = datetime.fromisoformat(
                            data['last_modified'])
                        formatted_date = last_modified.strftime(
                            "%Y-%m-%d %H:%M")

                        col1, col2 = st.columns(2)

                        with col1:
                            st.subheader("Transcript")
                            edited_transcript = st.text_area(
                                "Edit transcript:",
                                value=data["transcript"],
                                height=300,
                                key="previous_transcript"
                            )

                        with col2:
                            st.subheader("Summary")
                            edited_summary = st.text_area(
                                "Edit summary:",
                                value=data["summary"],
                                height=300,
                                key="previous_summary"
                            )

                        # Display formatted last updated date
                        st.markdown(f"**Last Updated:** {formatted_date}")

                        if st.button("Save Changes to Selected Recording", key="save_previous_btn"):
                            save_recording_data(edited_transcript,
                                                edited_summary,
                                                st.session_state.first_name,
                                                st.session_state.last_name,
                                                filename=file_path)
                            st.success("Changes saved successfully!")
                else:
                    st.info("No previous recordings found for this user")
            else:
                st.info("No previous recordings found for this user")
        else:
            st.info("Please select a user from the sidebar")
