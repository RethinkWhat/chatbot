lear# NaviBot

This project will hold the chatbot to be adopted by Saint Louis University for its portal.

In creating this bot two different architectures will be adopted catering to two different functions:

First, the RASA architecture was adopted. This architecture focused on the rule-based and intent-based coversations to be held when conversing with the bot. In here the RASA Free Developer Edition was adopted. As per their website, one bot can be used per company, with up to 1000 external conversations/month or 100 internal converations/month.

Question -> RASA -> Determine Intent -> If unable to meet threshold (0.9), fallback to RAG -> Make Chunks and Embed Query (Convert to its Numerical Representation/ Features) -> FAISS (Vector Search to determine the relevant chunks) -> Include Chunks in query -> Pass to LLM -> Get Answer



1. To start the rag server issue the following command:
    - uvicorn main:app --reload or  /opt/anaconda3/envs/rag_venv/bin/uvicorn main:app --reload
2. To start the chatbot issue the following command:
    - rasa shell or /opt/anaconda3/envs/rasa_venv/bin/rasa shell



RASA requires python 3.10 >

## Authors

- [@rethinkwhat](https://github.com/RethinkWhat/)

