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
    
    async def run(self, dispatcher: "CollectingDispatcher", 
            tracker: Tracker, 
            domain: dict):
        
        user_message = tracker.latest_message.get("text")

        # Call the RAG service
        #rag_response 
        rag_url = "http://rag_server:8000/query"
        try:
            response = requests.post(
                rag_url, 
                json={"query": user_message})
            rag_response = response.json().get("response", "No answer found.")
            print("RAG response:", rag_response)
            response.raise_for_status()  # Raise an error for bad responses


            if response.status_code == 200:
                print("RAG response:", rag_response)

                rag_response = response.json().get("response", "Sorry I couldn't find an answer.")
            else: 
                rag_response = "Sorry, there was an error processing your request."
        except requests.exceptions.RequestException as e:
            rag_response = f"Error connecting to RAG service: {str(e)}"

        # Send the response back to the user
        dispatcher.utter_message(text=rag_response)

        return []
    