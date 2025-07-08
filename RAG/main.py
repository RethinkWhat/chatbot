    #RAG SERVER
from fastapi import FastAPI, Request, HTTPException, Body, File, UploadFile #for db access
from fastapi.responses import JSONResponse
import os # used to get user choice of LLM saved in device environment variable
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware # middleware, allowing connection between client and server
import pymysql # for db access
from pathlib import Path
# local Imports
from rag_pipeline import RAGPipeline  
from build_vector_index import BuildVectorIndex
import bcrypt, subprocess, shutil,json
# Scraper functions
from scrapers.web_scraper import run_scraper
from scrapers.pdf_scraper import scan_all_pdfs
from scrapers.image_scraper import scan_images

from threading import Lock


import weaviate
from weaviate import WeaviateClient
from weaviate.classes.config import Configure

#signal when to stop RAG response
stop_signal = {"stop": False}
stop_lock = Lock()

# Build Knowledge. Can comment out this section if knowledge already built
#build_vector_index = BuildVectorIndex()
#build_vector_index.run()



# Initialize FastAPI app
app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # You can use ["*"] for dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Utility: database connection
def get_db_connection():
    return pymysql.connect(
        host="host.docker.internal", 
        user="root",
        password="root",
        database="navi-bot",
        cursorclass=pymysql.cursors.DictCursor
    )

# now user can choose between LLMs
llm_backend = os.getenv("LLM_BACKEND", "ollama") 
# Initialize RAG pipeline: now RAGPipelines has one argument llm_backend
rag_pipeline = RAGPipeline(llm_backend="ollama")
os.makedirs("knowledge/cleaned", exist_ok=True)

#scraper: clean the data by paraphrasing?
@app.post("/upload")
async def upload_files(files: list[UploadFile] = File(...)):
    upload_folder = "knowledge/raw"
    os.makedirs(upload_folder, exist_ok=True)
    os.makedirs("knowledge/cleaned", exist_ok=True)

    saved = []

    for file in files:
        ext = file.filename.split(".")[-1].lower()
        if ext in ["pdf", "png", "jpg", "jpeg", "txt"]:
            save_path = os.path.join(upload_folder, file.filename)
            with open(save_path, "wb") as f:
                shutil.copyfileobj(file.file, f)
            saved.append(file.filename)

            # # Optional: If it's a .txt, immediately clean it
            # if ext == "txt":
            #     with open(save_path, "r", encoding="utf-8") as f:
            #         raw = f.read()

            #     cleaned = rag_pipeline.paraphrase_with_ollama(raw, file.filename)
            #     clean_path = os.path.join("knowledge/cleaned", file.filename)
            #     with open(clean_path, "w", encoding="utf-8") as cf:
            #         cf.write(cleaned)
        else:
            continue

    return {"uploaded": saved}

@app.get("/health")
async def health_check():
    return {"status": "ok"}

# The menu route
@app.get("/menu")
async def get_menu():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, title, emoji, content FROM menu_item")
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return {"menu": rows}
    except Exception as e:
        print("DB Error:", e)  # This will print to your console
        raise HTTPException(status_code=500, detail="Failed to fetch menu data")


@app.get('/')
def read_root():
    return {"message": "Welcome to the RAG API. Use the /query endpoint to ask questions."}    


@app.post("/chat/stream")
async def stream_response(request: Request):
    body = await request.json()
    print("Received body:", body)  

    # Extract query from tracker
    query = body.get("query", "")
    previousQuestion = body.get("prevQuestion", "")

    if not query:
        return JSONResponse(
            status_code=200,
            content={"responses": [{"query": "No query found in message."}], "events": []}
        )
        
     # Reset stop flag before each new generation
    with stop_lock:
        stop_signal["stop"] = False
        
    
    # 👇 RAG PIPELINE IMPLE
    response = rag_pipeline.get_ollama_stream(query)
    if ("I don't know" in response):
        with open("knowledge/unknown.txt", "a") as file:
            file.write(query + "\n")
    response = JSONResponse(
        status_code=200,
        content={"response" : response} 
        )
    print(response)

@app.post("/predict")
async def predict_endpoint(request: Request):
    body = await request.json()
    print("reached /predict with the ff body: ", body)
    reply = rag_pipeline.predict( 
        message=body.get("message", ""), 
        distinct_id=body.get("distinct_id",""), 
        session_id=body.get("session_id", "")
    )
    return {"response": reply}


#when user clicks on stop button, stop RAG respose
@app.post("/stop")
async def stop_generation():
    with stop_lock:
        stop_signal["stop"] = True
    return {"status": "stop requested"}

# admin login
@app.post("/login")
async def login(request: Request):
    body = await request.json()
    username = body.get("username")
    password = body.get("password")

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM accounts WHERE username=%s", (username,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user and bcrypt.checkpw(password.encode('utf-8'), user["password"].encode('utf-8')):
            return {"status": "success", "message": "Login successful"}
        else:
            raise HTTPException(status_code=401, detail="Invalid credentials")
    except Exception as e:
        print("Login error:", e)
        raise HTTPException(status_code=500, detail="Internal server error")
    
# Admin: CRUDS
@app.get("/admin/menu")
async def get_menu_items():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, title, emoji, content FROM menu_item")
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return {"menu": rows}
    except Exception as e:
        print("Menu fetch error:", e)
        raise HTTPException(status_code=500, detail="Failed to fetch menu data")

# POST new menu item
@app.post("/admin/menu")
async def add_menu_item(data: dict = Body(...)):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO menu_item (title, emoji, content) VALUES (%s, %s, %s)",
            (data["title"], data["emoji"], data["content"])
        )
        conn.commit()
        cursor.close()
        conn.close()
        return {"status": "success"}
    except Exception as e:
        print("Insert error:", e)
        raise HTTPException(status_code=500, detail="Failed to add menu item")

# PUT update menu item
@app.put("/admin/menu/{item_id}")
async def update_menu_item(item_id: int, data: dict = Body(...)):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE menu_item SET title=%s, emoji=%s, content=%s WHERE id=%s",
            (data["title"], data["emoji"], data["content"], item_id)
        )
        conn.commit()
        cursor.close()
        conn.close()
        return {"status": "updated"}
    except Exception as e:
        print("Update error:", e)
        raise HTTPException(status_code=500, detail="Failed to update menu item")

# DELETE menu item
@app.delete("/admin/menu/{item_id}")
async def delete_menu_item(item_id: int):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM menu_item WHERE id=%s", (item_id,))
        conn.commit()
        cursor.close()
        conn.close()
        return {"status": "deleted"}
    except Exception as e:
        print("Delete error:", e)
        raise HTTPException(status_code=500, detail="Failed to delete menu item")
  
@app.get("/admin")
async def serve_admin():
    return FileResponse("Client/admin.html")    
# Admin: Scraper page
@app.get("/scrape")
async def serve_scraper():
    return FileResponse("Client/scraper.html")

@app.post("/scrape")
async def run_scraper_endpoint(data: dict = Body(...)):
    depth = data.get("depth", 2)

    try:
        # Adjust path based on your project layout
        result = subprocess.run(
            ["python3", "RASA/scrapers/web_scraper.py", "--depth", str(depth)],
            capture_output=True,
            text=True,
            timeout=300  # Optional timeout in seconds
        )
        return {
            "output": result.stdout,
            "error": result.stderr
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": str(e)})
    
#populate all json in /knowledge/json
@app.get("/knowledge/json")
async def list_json_files():
    folder = "knowledge/json"
    files = [f for f in os.listdir(folder) if f.endswith(".json")]
    return {"files": files}

@app.get("/knowledge/json/{filename}")
async def get_json_file(filename: str):
    path = os.path.join("knowledge", "json", filename)
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="File not found")
    with open(path, "r", encoding="utf-8") as f:
        return {"content": json.load(f)}


@app.post("/knowledge/json/{filename}")
async def save_json_file(filename: str, data: dict = Body(...)):
    path = os.path.join("knowledge", "json", filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data["content"], f, indent=2, ensure_ascii=False)
    return {"status": "saved"}


#upload files
@app.post("/upload")
async def upload_files(files: list[UploadFile] = File(...)):
    upload_folder = "knowledge"
    saved = []

    for file in files:
        ext = file.filename.split(".")[-1].lower()
        if ext in ["pdf", "png", "jpg", "jpeg", "txt"]:
            save_path = os.path.join(upload_folder, file.filename)
            with open(save_path, "wb") as f:
                shutil.copyfileobj(file.file, f)
            saved.append(file.filename)
        else:
            continue

    return {"uploaded": saved}


@app.post("/trigger/scrape")
async def trigger_web_scraper():
    run_scraper(urls_path="urls.txt", output_dir="knowledge/txt", depth=2)
    return {"status": "web scrape done"}

@app.post("/trigger/pdf")
async def trigger_pdf_scanner():
    scan_all_pdfs()
    return {"status": "pdf scan done"}

@app.post("/trigger/image")
async def trigger_image_scanner():
    scan_images(folder="knowledge/txt")
    return {"status": "image scan done"}

@app.post("/trigger/clean")
async def trigger_cleaning():
    os.makedirs("knowledge/cleaned", exist_ok=True)
    rag = RAGPipeline()
    count = 0
    for filename in os.listdir("knowledge/txt"):
        if filename.endswith(".txt"):
            with open(f"knowledge/txt/{filename}", "r", encoding="utf-8") as f:
                raw = f.read()
            cleaned = rag.paraphrase_with_ollama(raw, filename)
            with open(f"knowledge/cleaned/{filename}", "w", encoding="utf-8") as f:
                f.write(cleaned)
            count += 1
    return {"status": "cleaning complete", "files": count}

@app.post("/trigger/jsonify")
async def trigger_jsonify():
    if not rag_pipeline:
        return JSONResponse(status_code=500, content={"message": "RAG pipeline not initialized"})

    source_dir = "knowledge/txt"
    output_dir = "knowledge/json"
    os.makedirs(output_dir, exist_ok=True)

    converted = []
    for fname in os.listdir(source_dir):
        if fname.endswith(".txt"):
            with open(os.path.join(source_dir, fname), "r", encoding="utf-8") as f:
                content = f.read()
            jsonified = rag_pipeline.jsonifyTxt(content)
            if jsonified:
                json_path = os.path.join(output_dir, Path(fname).stem + ".json")
                with open(json_path, "w", encoding="utf-8") as out:
                    json.dump(jsonified, out, indent=2)
                converted.append(fname)

    return {"status": "converted", "files": converted}

@app.post("/trigger/index")
async def trigger_vector_index():
    builder = BuildVectorIndex()
    num_chunks = builder.build_index()  # Capture return value
    return {"status": "vector index built", "chunks": num_chunks}

