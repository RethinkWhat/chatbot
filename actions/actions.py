# This files contains your custom actions which can be used to run
# custom Python code.
#
# See this guide on how to implement these action:
# https://rasa.com/docs/rasa/custom-actions


# This is a simple example for a custom action which utters "Hello World!"

from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
import requests

class ActionRAGFallback(Action):
    def name(self) -> str:
        return "action_rag_fallback"
    
    def run(self, dispatcher: "CollectingDispatcher", 
            tracker: Tracker, 
            domain: dict):
        
        user_message = tracker.latest_message.get('text')

        # Call the RAG service
        #rag_response 

        dispatcher.utter_message(text = "")
        return []
    