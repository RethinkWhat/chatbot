lear# NaviBot

This project will hold the chatbot to be adopted by Saint Louis University

In creating this bot two different architectures were adopted catering to two different functions:

First, the RASA architecture was adopted. This architecture focused on the rule-based and intent-based coversations to be held when conversing with the bot. In here the RASA Free Developer Edition was adopted. As per their website, one bot can be used per company, with up to 1000 external conversations/month or 100 internal converations/month.

Second, the RAG architecture was adopted. This section will focus on the generative AI functionality of the chatbot and allow for contextual information to be derived from a defined knowledge base. The knowledge base will include .txt files, documents, images, and websites. From here, each data type will be converted into a .txt file and thereafter converted to a mathematical vector using FAISS. This will then be chunked and included in the user query to provide a SLU contextualized answer to the supposed query of a user.

Question -> RASA -> Determine Intent -> If unable to meet threshold, fallback to RAG -> Make Chunks and Embed Query (Convert to its Numerical Representation/ Features) -> FAISS (Vector Search to determine the relevant chunks) -> Include Chunks in query -> Pass to LLM -> Get Answer



1. To start the rag server issue the following command:
    - /opt/anaconda3/envs/rag_venv/bin/uvicorn 
2. To start the rasa actions server (The pipeline to allow the fallback mechanism to RAG) issue the following command
    - /opt/anaconda3/envs/rasa_venv/bin/rasa run actions
3. To start the chatbot issue the following command:
    - /opt/anaconda3/envs/rasa_venv/bin/rasa shell


1. Locally will need to download poppler and tesseract:
    - brew install poppler (or Windows equivlent)
    - brew install tesseract

## Authors

- [@rethinkwhat](https://github.com/RethinkWhat/)
- [@PerhapsYou] (https://github.com/PerhapsYou)

