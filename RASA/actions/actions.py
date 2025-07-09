# This files contains your custom actions which can be used to run
# custom Python code.
#
# See this guide on how to implement these action:
# https://rasa.com/docs/rasa/custom-actions

from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet
import requests
import sseclient
import pymysql

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# --- FastAPI setup ---
app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all for dev; restrict in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- DB connection ---
def get_db_connection():
    return pymysql.connect(
        host='localhost',
        user='root',
        password='',
        database='navi-bot',
        cursorclass=pymysql.cursors.DictCursor
    )

# --- FastAPI endpoint for menu ---
@app.get("/menu")
async def get_menu():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, emoji, content FROM menu_item")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    return {"menu": rows}


# --- Custom RAG Fallback Action ---
class ActionRAGFallback(Action):
    def name(self) -> str:
        return "action_rag_fallback"

    async def run(self,
                  dispatcher: CollectingDispatcher,
                  tracker: Tracker,
                  domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        user_message = tracker.latest_message.get("text", "").strip().lower()

        # Avoid sending common menu/help keywords to RAG
        if user_message in ["menu", "show menu", "help", "options"]:
            dispatcher.utter_message(text="You can click the menu icon or type a question.")
            return []


        prev_question = tracker.get_slot("prev_question") or ""
        print("RASA PREVIOUS QUESTION: " + prev_question)

        try:

            rag_url = "http://rag_server:8000/predict"
            response = requests.post(
                rag_url,
                json={"query": user_message, 
                    "prevQuestion": prev_question}
            )

            # Get the full answer from the response as a JSON object
            if response.status_code == 200:  # Check if the request was successful
                response_json = response.json()
                full_answer = response_json.get("text", "") 

                # Send the full answer as a message
                dispatcher.utter_message(text=full_answer)
            else:
                # Handle error case
                dispatcher.utter_message(text="Sorry, there was an issue processing your request.")

        except requests.exceptions.RequestException as e:
            dispatcher.utter_message(text=f"Error connecting to RAG service: {str(e)}")

        updated_prev = prev_question + "\n " + user_message
        return [SlotSet("prev_question", updated_prev)]
        