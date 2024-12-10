import streamlit as st
from datetime import datetime
from utils import get_summary
import re
import clipboard


def render_sidebar(db_manager, process_new_recording):
    # Initialize copied list in session state if it doesn't exist
    if 'copied' not in st.session_state:
        st.session_state.copied = []

    with st.sidebar:
        if st.button("Logout"):
            st.session_state.authenticated = False
            st.rerun()

        st.divider()
        render_patient_selection(db_manager)
        render_system_prompts(db_manager)


def render_patient_selection(db_manager):
    st.header("Patient Selection")
    patients = db_manager.get_all_patients(st.session_state.provider_id)

    if 'selected_patient' not in st.session_state:
        st.session_state.selected_patient = ""
        st.session_state.first_name = ""
        st.session_state.last_name = ""

    render_existing_patient_selector(patients, db_manager)
    render_new_patient_form(db_manager)


def render_system_prompts(db_manager):
    st.divider()
    with st.expander("Select System Prompt", expanded=False):
        system_prompts = db_manager.load_system_prompts(
            st.session_state.provider_id)

        selected_prompt_name = st.selectbox(
            "Select a prompt template:",
            options=list(system_prompts.keys())
        )

        updated_prompt = st.text_area(
            "Customize the selected prompt:",
            value=system_prompts[selected_prompt_name],
            height=150
        )

        st.session_state.current_prompt = updated_prompt

        if updated_prompt != system_prompts[selected_prompt_name]:
            system_prompts[selected_prompt_name] = updated_prompt
            db_manager.save_system_prompts(
                system_prompts, st.session_state.provider_id)
            st.success("Prompt updated successfully!")

    with st.expander("Create New Prompt", expanded=False):
        new_prompt_name = st.text_input("New prompt name")
        new_prompt_content = st.text_area("New prompt content", height=150)

        if st.button("Add New Prompt"):
            if new_prompt_name:
                if new_prompt_name in system_prompts:
                    st.error("A prompt with this name already exists!")
                else:
                    system_prompts[new_prompt_name] = new_prompt_content
                    db_manager.save_system_prompts(
                        system_prompts, st.session_state.provider_id)
                    st.success("New prompt template added!")
                    st.rerun()

    with st.sidebar:
        st.divider()
        st.markdown("**Current Prompt Template:**")
        st.info(selected_prompt_name)


def render_recording_section(saved_data, db_manager):
    render_transcript_column(saved_data, db_manager)
    render_summary_column(saved_data, db_manager)


def render_visit_records(db_manager):
    st.header("Visit Records")
    recordings = db_manager.get_patient_recordings(
        st.session_state.selected_patient_id,
        st.session_state.provider_id
    )

    if recordings:
        render_recording_selector(recordings, db_manager)
    else:
        st.info("No recordings found for this patient")

# Helper functions for the main UI components


def render_existing_patient_selector(patients, db_manager):
    if patients:
        patient_options = [""] + [f"{p[0]} {p[1]}" for p in patients]
        patient_ids = {f"{p[0]} {p[1]}": p[2] for p in patients}

        selected_patient = st.selectbox(
            "Select Existing Patient",
            options=patient_options,
            format_func=lambda x: "Select a patient..." if x == "" else x,
            index=patient_options.index(
                st.session_state.selected_patient) if st.session_state.selected_patient in patient_options else 0
        )

        update_patient_state(selected_patient, patient_ids)


def render_new_patient_form(db_manager):
    with st.expander("Create New Patient", expanded=False):
        new_first_name = st.text_input("First Name")
        new_last_name = st.text_input("Last Name")

        if st.button("Create New Patient"):
            handle_new_patient_creation(
                new_first_name, new_last_name, db_manager)


def on_copy_click(text):
    st.session_state.copied.append(text)
    clipboard.copy(text)
    st.toast('Copied to clipboard!')


def render_transcript_column(saved_data, db_manager):
    with st.expander("Transcript", expanded=False):
        key = f"transcript_{str(saved_data['_id'])}"
        transcript = st.text_area(
            label="Transcript content",
            label_visibility="hidden",
            value=saved_data["transcript"],
            height=300,
            key=key,
            on_change=lambda: update_transcript(saved_data, db_manager, key)
        )


def update_transcript(saved_data, db_manager, key):
    db_manager.update_recording_data(
        saved_data["_id"],
        st.session_state[key],
        saved_data["summary"]
    )
    st.success("Transcript updated successfully!")


def render_summary_column(saved_data, db_manager):
    header_col1, header_col2, header_col3 = st.columns([0.6, 0.2, 0.2])
    with header_col1:
        st.subheader("Summary")

    with header_col3:
        render_regenerate_button(saved_data, db_manager)

    key = f"summary_{str(saved_data['_id'])}"
    summary = st.text_area(
        label="Summary content",
        label_visibility="hidden",
        value=saved_data["summary"],
        height=300,
        key=key,
        on_change=lambda: update_summary(saved_data, db_manager, key)
    )


def update_summary(saved_data, db_manager, key):
    db_manager.update_recording_data(
        saved_data["_id"],
        saved_data["transcript"],
        st.session_state[key]
    )
    st.success("Summary updated successfully!")


def render_regenerate_button(saved_data, db_manager):
    button_key = f"regenerate_summary_{str(saved_data['_id'])}"

    if st.button("Rewrite", key=button_key, use_container_width=False):
        try:
            with st.spinner('Generating new summary...'):
                new_summary = get_summary(
                    saved_data["transcript"],
                    st.session_state.current_prompt
                )

                db_manager.update_recording_data(
                    saved_data["_id"],
                    saved_data["transcript"],
                    new_summary
                )

                if 'current_recording_id' in st.session_state:
                    st.session_state.current_recording_id = str(
                        saved_data['_id'])

                st.rerun()
        except Exception as e:
            st.error(f"Error regenerating summary: {str(e)}")


def render_recording_selector(recordings, db_manager):
    if 'current_recording_id' not in st.session_state:
        st.session_state.current_recording_id = None

    recording_options = [
        (r["timestamp"].strftime("%Y-%m-%d %H:%M"), str(r["_id"]))
        for r in recordings
    ]

    selected_recording = st.selectbox(
        "Select a recording:",
        options=[r[1] for r in recording_options],
        format_func=lambda x: next(r[0]
                                   for r in recording_options if r[1] == x),
        key="visit_recording_selector"
    )

    if selected_recording:
        st.session_state.current_recording_id = selected_recording
        saved_data = db_manager.load_recording_data(selected_recording)
        render_recording_section(saved_data, db_manager)


def update_patient_state(selected_patient, patient_ids):
    st.session_state.selected_patient = selected_patient

    if selected_patient:
        first_name, last_name = split_patient_name(selected_patient)
        st.session_state.first_name = first_name
        st.session_state.last_name = last_name
        st.session_state.selected_patient_id = patient_ids.get(
            selected_patient)
        if 'notes' in st.session_state:
            del st.session_state.notes
    else:
        st.session_state.first_name = ""
        st.session_state.last_name = ""
        st.session_state.selected_patient_id = None
        if 'notes' in st.session_state:
            del st.session_state.notes


def handle_new_patient_creation(new_first_name, new_last_name, db_manager):
    if new_first_name and new_last_name:
        formatted_first_name = new_first_name.capitalize()
        formatted_last_name = new_last_name.capitalize()

        try:
            patient_id = db_manager.save_patient_data(
                formatted_first_name,
                formatted_last_name,
                st.session_state.provider_id
            )
            st.success(
                f"Created new patient: {formatted_first_name} {formatted_last_name}")
            st.session_state.selected_patient = f"{formatted_first_name} {formatted_last_name}"
            st.session_state.first_name = formatted_first_name
            st.session_state.last_name = formatted_last_name
            st.rerun()
        except Exception as e:
            st.error(f"Error saving patient to database: {str(e)}")
    else:
        st.error("Please enter both first and last name")


def split_patient_name(combined_name):
    parts = re.split(r'[- ]', combined_name)
    if len(parts) >= 2:
        return parts[0], ' '.join(parts[1:])
    return combined_name, ""


def render_patient_notes(db_manager):
    with st.expander("Notes", expanded=False):
        # Initialize notes in session state if not already present
        if 'notes' not in st.session_state:
            st.session_state.notes = db_manager.get_patient_notes(
                st.session_state.selected_patient_id)

        notes_input_key = "notes_input"

        def save_notes():
            new_value = st.session_state[notes_input_key]
            st.session_state.notes = new_value
            db_manager.update_patient_notes(
                st.session_state.selected_patient_id, new_value)
            st.success("Notes saved successfully!")

        st.text_area(
            "Enter your notes here:",
            key=notes_input_key,
            value=st.session_state.notes,
            height=150,
            on_change=save_notes
        )
