from datetime import datetime
from pymongo import MongoClient
from bson.objectid import ObjectId
import os
import streamlit as st


@st.cache_resource
def init_connection():
    try:
        client = MongoClient(os.getenv('MONGO_URI'))
        client.admin.command('ping')
        return client
    except Exception as e:
        st.error(f"Could not connect to MongoDB: {str(e)}")
        return None


class DatabaseManager:
    def __init__(self):
        self.client = init_connection()
        if self.client:
            self.db = self.client['scriber']
        else:
            st.error("Failed to initialize MongoDB connection")
            st.stop()

    def load_system_prompts(self, provider_id):
        try:
            prompts = {}
            query = {"provider_id": provider_id}
            prompts_cursor = self.db.system_messages.find(query)

            if self.db.system_messages.count_documents(query) == 0:
                default_prompt = {
                    "name": "Default Summary",
                    "content": "You are a medical scribe assistant. Create a concise, professional summary of the medical conversation, highlighting key symptoms, diagnoses, and treatment plans. Format the summary in a clear, medical-note style.",
                    "provider_id": provider_id,
                    "created_at": datetime.now(),
                    "last_modified": datetime.now()
                }
                self.db.system_messages.insert_one(default_prompt)
                prompts[default_prompt["name"]] = default_prompt["content"]
            else:
                for doc in prompts_cursor:
                    prompts[doc['name']] = doc['content']

            return prompts
        except Exception as e:
            st.error(f"Error loading system prompts: {str(e)}")
            return {}

    def save_system_prompts(self, prompts, provider_id):
        try:
            self.db.system_messages.delete_many({"provider_id": provider_id})
            for name, content in prompts.items():
                self.db.system_messages.insert_one({
                    "name": name,
                    "content": content,
                    "provider_id": provider_id,
                    "created_at": datetime.now(),
                    "last_modified": datetime.now()
                })
        except Exception as e:
            st.error(f"Error saving system prompts: {str(e)}")

    def save_recording_data(self, transcript, summary, provider_id, patient_id):
        result = self.db.recordings.insert_one({
            "transcript": transcript,
            "summary": summary,
            "provider_id": provider_id,
            "patient_id": patient_id,
            "timestamp": datetime.now(),
            "last_modified": datetime.now()
        })
        return str(result.inserted_id)

    def update_recording_data(self, document_id, transcript, summary):
        self.db.recordings.update_one(
            {"_id": ObjectId(document_id)},
            {
                "$set": {
                    "transcript": transcript,
                    "summary": summary,
                    "last_modified": datetime.now()
                }
            }
        )

    def get_patient_recordings(self, patient_id, provider_id):
        return list(self.db.recordings.find({
            "patient_id": patient_id,
            "provider_id": provider_id
        }).sort("timestamp", -1))

    def load_recording_data(self, document_id):
        return self.db.recordings.find_one({"_id": ObjectId(document_id)})

    def get_all_patients(self, provider_id):
        try:
            patients = list(self.db.patients.find(
                {"provider_id": provider_id},
                {"first_name": 1, "last_name": 1}
            ).sort("last_name", 1))
            return [(p["first_name"], p["last_name"], str(p["_id"])) for p in patients]
        except Exception as e:
            st.error(f"Error fetching patients from database: {str(e)}")
            return []

    def save_patient_data(self, first_name, last_name, provider_id, notes=""):
        result = self.db.patients.insert_one({
            "first_name": first_name,
            "last_name": last_name,
            "notes": notes,
            "provider_id": provider_id,
            "created_at": datetime.now(),
            "last_modified": datetime.now()
        })
        return str(result.inserted_id)

    def update_patient_notes(self, patient_id, notes):
        self.db.patients.update_one(
            {"_id": ObjectId(patient_id)},
            {
                "$set": {
                    "notes": notes,
                    "last_modified": datetime.now()
                }
            }
        )

    def get_patient_notes(self, patient_id):
        patient = self.db.patients.find_one({"_id": ObjectId(patient_id)})
        return patient.get("notes", "") if patient else ""

    def verify_user(self, email, password):
        return self.db.users.find_one({"email": email})

    def create_user(self, email, hashed_password):
        if self.db.users.find_one({"email": email}):
            return False, "Email already exists"

        self.db.users.insert_one({
            "email": email,
            "password": hashed_password,
            "created_at": datetime.now()
        })
        return True, "User created successfully"
