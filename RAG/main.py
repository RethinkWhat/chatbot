    #RAG SERVER
from fastapi import FastAPI, Request, HTTPException, Body, File, UploadFile #for db access
from fastapi.responses import JSONResponse
import os # used to get user choice of LLM saved in device environment variable
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware # middleware, allowing connection between client and server
import pymysql # for db access
from pathlib import Path
from typing import Dict, List
# local Imports
from rag_pipeline import RAGPipeline  
from build_vector_index import BuildVectorIndex
import bcrypt, subprocess, shutil,json
# Scraper functions
from scrapers.web_scraper import run_scraper
from scrapers.pdf_scraper import PDFScraper
from scrapers.image_scraper import scan_images



from threading import Lock


import weaviate
from weaviate import WeaviateClient
from weaviate.classes.config import Configure
from constants import apologyMsg

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


@app.get("/health")
async def health_check():
    return {"status": "ok"}

#===================================
# CONTENT BELOW IS API ENDPT FOR ACCESSING BACKEND, DEDICATED FOR ADMIN CRUDS
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

@app.post("/predict")
async def predict_endpoint(request: Request):

    # Reset stop flag before each new generation
    with stop_lock:
        stop_signal["stop"] = False
        
    body = await request.json()
    print("reached /predict with the ff body: ", body)
    query = body.get("query")
    reply = rag_pipeline.predict( 
        message=body.get("query", ""), 
        distinct_id=body.get("distinct_id",""), 
        session_id=body.get("session_id", ""),
        query = query
    )

    if ("I apologize" in reply):
        with open("knowledge/unknown.txt", "a") as file:
            file.write(query + "\n")

    print("SENDING THIS REPLY: ", reply)
    return {"text": reply}


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

# URLS.txt
URLS_FILE = os.path.join(os.path.dirname(__file__), "urls.txt")

#admin popup:scraper popup
#==========================
URLS_PATH = "urls.txt"
SCRAPER_SCRIPT = "web_scraper.py"

@app.get("/scrape/urls")
def get_urls():
    if not os.path.exists(URLS_PATH):
        return {"urls": []}
    with open(URLS_PATH, "r", encoding="utf-8") as f:
        urls = [line.strip() for line in f if line.strip()]
    return {"urls": urls}

@app.post("/scrape/urls")
async def save_urls(request: Request):
    data = await request.json()
    urls = data.get("urls", "")
    with open(URLS_PATH, "w", encoding="utf-8") as f:
        f.write(urls.strip() + "\n")
    return {"status": "✅ URLs saved to urls.txt"}

@app.post("/scrape/run")
def run_web_scraper():
    try:
        result = subprocess.run(["python3", "scrapers/web_scraper.py"], capture_output=True, text=True, check=True)
        return {"status": "✅ Web scraping complete", "stdout": result.stdout}
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"❌ Scraping failed: {e.stderr}")
#========================================

@app.get("/urls")
def get_urls() -> Dict[str, List[str]]:
    """Read urls.txt and return as JSON list."""
    if not os.path.exists(URLS_FILE):
        return {"urls": []}
    with open(URLS_FILE, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f.readlines() if line.strip()]
    return {"urls": lines}


@app.post("/urls")
async def save_urls(request: Request) -> Dict[str, str]:
    """Save a JSON list of URLs into urls.txt."""
    try:
        data = await request.json()
        urls = data.get("urls", [])
        with open(URLS_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(urls) + "\n")
        return {"status": "URLs updated."}
    except Exception as e:
        return {"status": f"Failed to update URLs: {str(e)}"}
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


@app.get("/knowledge/txt")
def list_txt_files():
    files = [f for f in os.listdir("knowledge/raw") if f.endswith(".txt")]
    return {"files": files}

@app.get("/knowledge/txt/{filename}")
def get_txt_content(filename: str):
    path = os.path.join("knowledge/raw", filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File not found")
    with open(path, "r", encoding="utf-8") as f:
        return {"content": f.read()}


# JSONify txts
# @app.post("/trigger/jsonify-txt/{filename}")
# def jsonify_single_file(filename: str):
#     input_path = f"knowledge/txt/{filename}"
#     output_path = f"knowledge/testJson/{filename.replace('.txt', '.json')}"

#     if not os.path.exists(input_path):
#         raise HTTPException(status_code=404, detail="File not found")
#     rag = RAGPipeline()
#     with open(input_path, "r", encoding="utf-8") as f:
#         raw_text = f.read()

#     result = rag.jsonifyTxt(raw_text)

#     with open(output_path, "w", encoding="utf-8") as out:
#         json.dump(result, out, indent=2, ensure_ascii=False)

#     return {"status": "success", "json_file": output_path}

@app.post("/trigger/jsonify-txt")
def batch_convert_txts_to_json(input_dir, output_dir):
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    for txt_file in Path(input_dir).glob("*.txt"):
        with open(txt_file, "r", encoding="utf-8") as f:
            text = f.read()

        result = extract_json_from_txt(text)
        out_path = Path(output_dir) / (txt_file.stem + ".json")

        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        print(f"✅ Processed {txt_file.name}")


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
    run_scraper(urls_path="urls.txt", output_dir="knowledge/raw", depth=2)
    return {"status": "web scrape done"}

@app.post("/trigger/pdf")
async def trigger_pdf_scanner():
    scraper=PDFScraper()
    scraper.scan_all_pdfs()
    return {"status": "pdf scan done"}

@app.post("/trigger/image")
async def trigger_image_scanner():
    scan_images(input_folder="knowledge/raw")
    return {"status": "image scan done"}

# are we still building index? Or are we weaviating?
# @app.post("/trigger/index")
# async def trigger_vector_index():
#     builder = BuildVectorIndex()
#     num_chunks = builder.build_index()  # Capture return value
#     return {"status": "vector index built", "chunks": num_chunks}

