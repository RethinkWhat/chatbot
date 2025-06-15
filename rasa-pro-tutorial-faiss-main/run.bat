@echo off

REM === Start RAG API using .ragenv ===
start cmd /k ".ragenv\Scripts\activate && python rag_api.py"

REM === Start Rasa action server using conda environment ===
start cmd /k "conda activate rasa_env && rasa run actions"

REM === Start Rasa shell using conda environment ===
start cmd /k "conda activate rasa_env && rasa shell"