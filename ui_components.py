import streamlit as st
import pyperclip
from datetime import datetime


def create_copy_button(text, button_id):
    """Create a copy button for the specified text"""
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


def show_patient_notes(db):
    """Display and handle patient notes section"""
    st.subheader("Notes")

    # Initialize notes in session state if not present
    if 'notes' not in st.session_state:
        # Try to load existing notes from database
        patient_data = db.get_patient_data(
            st.session_state.selected_patient_id)
        st.session_state.notes = patient_data.get(
            'notes', '') if patient_data else ''

    notes = st.text_area("Enter your notes here:",
                         value=st.session_state.notes,
                         height=150)

    if st.button("Save Notes"):
        db.update_patient_notes(st.session_state.selected_patient_id, notes)
        st.session_state.notes = notes
        st.success("Notes saved successfully!")


def show_current_recording_ui(saved_data, get_summary, update_recording_data, db):
    """Display the current recording interface"""
    col1, col2 = st.columns(2)

    with col1:
        header_col1, header_col2 = st.columns([0.8, 0.2])
        with header_col1:
            st.subheader("Transcript")
        with header_col2:
            st.write("")
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
        header_col1, header_col2, header_col3 = st.columns([0.6, 0.2, 0.2])
        with header_col1:
            st.subheader("Summary")
        with header_col2:
            st.write("")
            if st.button("🔗", key=f"copy_summary_current_{saved_data['summary'][:10]}", use_container_width=False):
                pyperclip.copy(saved_data["summary"])
                st.toast('Copied to clipboard!')
        with header_col3:
            if st.button("🔄", key=f"regenerate_summary_current", use_container_width=False):
                with st.spinner('Generating new summary...'):
                    new_summary = get_summary(
                        edited_transcript,
                        st.session_state.current_prompt
                    )
                    update_recording_data(
                        st.session_state.current_file,
                        edited_transcript,
                        new_summary
                    )
                    st.success("Summary regenerated successfully!")
                    st.rerun()

        edited_summary = st.text_area(
            label="Summary content",
            label_visibility="hidden",
            value=saved_data["summary"],
            height=300,
            key="current_summary"
        )

    if st.button("Save Changes", key="save_current_btn"):
        db.save_recording(edited_transcript, edited_summary,
                          filename=st.session_state.current_file)
        st.success("Changes saved successfully!")

    return edited_transcript, edited_summary


def show_previous_recordings_ui(db, get_summary, update_recording_data):
    """Display the previous recordings interface"""
    with st.expander("Load Previous Recordings"):
        recordings = db.get_patient_recordings(
            st.session_state.selected_patient_id,
            st.session_state.provider_id
        )

        if not recordings:
            st.info("No previous recordings found for this patient")
            return

        recording_options = [
            (r["timestamp"].strftime("%Y-%m-%d %H:%M"), str(r["_id"]))
            for r in recordings
        ]

        selected_recording = st.selectbox(
            "Select a recording to edit:",
            options=[r[1] for r in recording_options],
            format_func=lambda x: next(r[0]
                                       for r in recording_options if r[1] == x),
            key="recording_selector"
        )

        if selected_recording and (not hasattr(st.session_state, 'current_file') or
                                   selected_recording != st.session_state.current_file):
            show_previous_recording_content(
                selected_recording, db, get_summary, update_recording_data)


def show_previous_recording_content(selected_recording, db, get_summary, update_recording_data):
    """Display content for a selected previous recording"""
    data = db.get_recording(selected_recording)
    formatted_date = data['last_modified'].strftime("%Y-%m-%d %H:%M")

    col1, col2 = st.columns(2)

    with col1:
        header_col1, header_col2 = st.columns([0.8, 0.2])
        with header_col1:
            st.subheader("Transcript")
        with header_col2:
            st.write("")
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
        header_col1, header_col2, header_col3 = st.columns([0.6, 0.2, 0.2])
        with header_col1:
            st.subheader("Summary")
        with header_col2:
            st.write("")
            if st.button("🔗", key=f"copy_summary_prev_{selected_recording}", use_container_width=False):
                pyperclip.copy(data["summary"])
                st.toast('Copied to clipboard!')
        with header_col3:
            if st.button("🔄", key=f"regenerate_summary_prev_{selected_recording}", use_container_width=False):
                with st.spinner('Generating new summary...'):
                    new_summary = get_summary(
                        edited_transcript,
                        st.session_state.current_prompt
                    )
                    update_recording_data(
                        selected_recording,
                        edited_transcript,
                        new_summary
                    )
                    st.success("Summary regenerated successfully!")
                    st.rerun()

        edited_summary = st.text_area(
            label="Previous summary content",
            label_visibility="hidden",
            value=data["summary"],
            height=300,
            key="previous_summary"
        )

    st.markdown(f"**Last Updated:** {formatted_date}")

    if st.button("Save Changes to Selected Recording", key="save_previous_btn"):
        update_recording_data(
            selected_recording,
            edited_transcript,
            edited_summary
        )
        st.success("Changes saved successfully!")
