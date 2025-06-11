from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import UserUtteranceReverted
import requests

class ActionRAGFallback(Action):
    def name(self) -> Text:
        return "action_rag_fallback"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        user_message = tracker.latest_message.get('text')
        print(f"[DEBUG] User message: {user_message}")

        try:
            response = requests.post("http://localhost:5001/rag-query", json={"question": user_message})
            print(f"[DEBUG] RAG raw response: {response.text}")
            rag_answer = response.json().get("answer", "Sorry, I couldn't find an answer.")
        except Exception as e:
            rag_answer = f"RAG service failed: {str(e)}"

        dispatcher.utter_message(text=rag_answer)

        # Prevent looping by reverting user message or ending fallback chain
        return [UserUtteranceReverted()]