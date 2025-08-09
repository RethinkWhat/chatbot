# NaviBot

This project will hold the chatbot to be adopted by Saint Louis University

In creating this bot two different architectures were adopted catering to two different functions:

First, the RASA architecture was adopted. This architecture focused on the rule-based and intent-based coversations to be held when conversing with the bot. In here the RASA Free Developer Edition was adopted. As per their website, one bot can be used per company, with up to 1000 external conversations/month or 100 internal converations/month.

Second, the RAG architecture was adopted. This section will focus on the generative AI functionality of the chatbot and allow for contextual information to be derived from a defined knowledge base. The knowledge base will include .txt files, documents, images, and websites. From here, each data type will be converted into a .txt file and thereafter converted to a mathematical vector using FAISS. This will then be chunked and included in the user query to provide a SLU contextualized answer to the supposed query of a user.

Question -> RASA -> Determine Intent -> If unable to meet threshold, fallback to RAG -> Make Chunks and Embed Query (Convert to its Numerical Representation/ Features) -> FAISS (Vector Search to determine the relevant chunks) -> Include Chunks in query -> Pass to LLM -> Get Answer

To run the project a docker compose file has been created. Issuing the "up" command will be sufficient if the aim is to run the project on a CPU. We advise against it. Instead, opt to run Ollama on the GPU under the network "chatbot_network" so that it can be detected by the other services. After running the ollama model, two services will need to be installed within the containers, which can be done by issuing the following commands:
   1. ollama pull llama3:8b
   2. ollama pull nomic-embed-text


## Flow

User Input
   ↓
[Frontend Static Menu]
   └──→ Matched → Predefined Response 
   ↓
[Fallback to RASA]
   └──→ Matched → Intent Template Response 
   ↓
[RAG Pipeline]
   └─→ Embed (InstructorXL)
        ↓
     FAISS Search
        ↓
Recursive Chunk Retrieval (w/ Metadata)
        ↓
[Prompt to LLaMA 3 8B]
   Input = [CONTEXT] + [USER QUESTION]
        ↓
LLM Response


## Authors

- [@rethinkwhat](https://github.com/RethinkWhat/)
- [@PerhapsYou] (https://github.com/PerhapsYou)


# Remaining Task
   The admin side has several issues primarily centered around the scrapers and the conversion to JSON. These issues will be addressed sometime soon when we have access to the necessary hardware to fix them.