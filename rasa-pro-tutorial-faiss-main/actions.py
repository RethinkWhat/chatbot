from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import CollectingDispatcher
import requests

# RAG Fallback Action
class ActionRAGFallback(Action):
    def name(self) -> Text:
        return "action_rag_fallback"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        user_message = tracker.get_slot("last_user_question") or tracker.latest_message.get("text")
        print(f"[DEBUG] User message: {user_message}")

        try:
            response = requests.post(
                "http://localhost:5001/rag-query",
                json={"question": user_message}
            )
            response.raise_for_status()
            rag_answer = response.json().get("answer", "Sorry, I couldn't find an answer.")
            print(f"[DEBUG] RAG response: {rag_answer}")
        except requests.exceptions.RequestException as e:
            rag_answer = f"[RAG Error] {str(e)}"
            print(f"[ERROR] RAG backend failed: {e}")

        dispatcher.utter_message(text=rag_answer)
        return []


# Optional Prompt Before Using RAG
class ActionRAGPrompt(Action):
    def name(self) -> Text:
        return "action_rag_prompt"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        last_question = tracker.latest_message.get("text")
        print(f"[DEBUG] Setting last_user_question slot to: {last_question}")
        dispatcher.utter_message(
            text="I'm not confident in my answer. Would you like me to search for a better response using external knowledge? (yes/no)"
        )
        return [SlotSet("last_user_question", last_question)]


# If User Declines RAG
class ActionRAGCancel(Action):
    def name(self) -> Text:
        return "action_rag_cancel"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        dispatcher.utter_message(text="Alright, no problem. Let me know if you need help with anything else.")
        return []
