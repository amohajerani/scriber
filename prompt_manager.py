import streamlit as st
from typing import Dict, Optional


class PromptManager:
    def __init__(self, db):
        self.db = db
        if 'current_prompt' not in st.session_state:
            st.session_state.current_prompt = None
        if 'selected_prompt_name' not in st.session_state:
            st.session_state.selected_prompt_name = None

    def load_prompts(self) -> Dict[str, str]:
        """Load all prompts for the current provider"""
        return self.db.load_system_prompts(st.session_state.provider_id)

    def save_prompt(self, name: str, content: str) -> None:
        """Save a single prompt"""
        prompts = self.load_prompts()
        prompts[name] = content
        self.db.save_system_prompts(prompts, st.session_state.provider_id)

    def show_prompt_selector(self) -> None:
        """Display prompt selection and management UI"""
        with st.expander("Select System Prompt", expanded=False):
            # Load all prompts
            system_prompts = self.load_prompts()

            if not system_prompts:
                # Initialize with default prompt if none exist
                default_prompt = (
                    "You are a medical scribe assistant. Please create a concise "
                    "and organized summary of the medical consultation, including "
                    "key points about patient history, symptoms, diagnosis, and "
                    "treatment plan. Use medical terminology where appropriate."
                )
                self.save_prompt("Default Medical Summary", default_prompt)
                system_prompts = self.load_prompts()

            # Prompt selector
            selected_prompt_name = st.selectbox(
                "Select a prompt template:",
                options=list(system_prompts.keys()),
                key="prompt_selector"
            )

            # Store selected prompt name in session state
            st.session_state.selected_prompt_name = selected_prompt_name

            # Show and allow editing of the selected prompt
            updated_prompt = st.text_area(
                "Customize the selected prompt:",
                value=system_prompts[selected_prompt_name],
                height=150,
                key="prompt_editor"
            )

            # Store the current prompt in session state
            st.session_state.current_prompt = updated_prompt

            # Save changes to existing prompt
            if updated_prompt != system_prompts[selected_prompt_name]:
                self.save_prompt(selected_prompt_name, updated_prompt)
                st.success("Prompt updated successfully!")

            # Add new prompt section
            st.divider()
            st.subheader("Create New Prompt")
            new_prompt_name = st.text_input(
                "New prompt name",
                key="new_prompt_name"
            )
            new_prompt_content = st.text_area(
                "New prompt content",
                height=100,
                key="new_prompt_content"
            )

            if st.button("Add New Prompt", key="add_prompt_btn"):
                if not new_prompt_name:
                    st.error("Please enter a name for the new prompt")
                elif new_prompt_name in system_prompts:
                    st.error("A prompt with this name already exists!")
                else:
                    self.save_prompt(new_prompt_name, new_prompt_content)
                    st.success("New prompt template added!")
                    st.rerun()

            # Delete prompt section
            st.divider()
            st.subheader("Delete Prompt")
            if len(system_prompts) > 1:  # Prevent deleting the last prompt
                prompt_to_delete = st.selectbox(
                    "Select prompt to delete:",
                    options=list(system_prompts.keys()),
                    key="delete_prompt_selector"
                )
                if st.button("Delete Prompt", key="delete_prompt_btn"):
                    prompts = self.load_prompts()
                    del prompts[prompt_to_delete]
                    self.db.save_system_prompts(
                        prompts, st.session_state.provider_id)
                    st.success(f"Deleted prompt: {prompt_to_delete}")
                    st.rerun()
            else:
                st.info("Cannot delete the last remaining prompt template")

    def show_current_prompt_info(self) -> None:
        """Display current prompt information in the sidebar"""
        if st.session_state.selected_prompt_name:
            st.divider()
            st.markdown("**Current Prompt Template:**")
            st.info(st.session_state.selected_prompt_name)

    def get_current_prompt(self) -> Optional[str]:
        """Get the currently selected prompt content"""
        return st.session_state.current_prompt
