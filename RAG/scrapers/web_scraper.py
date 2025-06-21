import os
import requests
import json
import time
import threading
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from concurrent.futures import ThreadPoolExecutor
import logging


# Setup logging
logging.basicConfig(
    level=logging.INFO,  # Change to DEBUG for more verbose output
    format='[%(levelname)s] %(message)s'
)


HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}

visited_urls = set()
visited_lock = threading.Lock()
#set up unnecessary elements that the scraper will avoid
unnecessary = ["mp4","mp3", "m4v", "upload", "uploads", "download", "downloads", "shopify"]

#methods
def fetch_html(url):
    try:
        response = requests.get(url, headers=HEADERS, timeout=20)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return None

def parse_html(html, url):
    soup = BeautifulSoup(html, "lxml")

    headings = {f"h{i}": [h.text.strip() for h in soup.find_all(f"h{i}")] for i in range(1, 4)}
    paragraphs = [p.text.strip() for p in soup.find_all("p") if len(p.text.strip()) > 50]

    faqs = []
    for faq_section in soup.find_all(class_=lambda x: x and "faq" in x.lower()):
        questions = faq_section.find_all(["h2", "h3", "strong"])
        answers = faq_section.find_all("p")
        for q, a in zip(questions, answers):
            faqs.append({"question": q.text.strip(), "answer": a.text.strip()})

    return {
        "url": url,
        "headings": headings,
        "paragraphs": paragraphs,
        "faqs": faqs
    }

def get_internal_links(html, base_url):
    soup = BeautifulSoup(html, "lxml")
    links = set()

    for link in soup.find_all("a", href=True):
        href = link["href"]
        full_url = urljoin(base_url, href)
        parsed_url = urlparse(full_url)

        if parsed_url.netloc == urlparse(base_url).netloc and not parsed_url.fragment:
            # Skip links with product-related keywords
            if any(keyword in full_url.lower() for keyword in unnecessary):
                print(f"\nSkipping unnecessary Link: {full_url}\n")
                continue

            links.add(full_url)

    return links

def crawl(url, depth=2):
    with visited_lock:
        if url in visited_urls or depth == 0:
            return []
        visited_urls.add(url)

    print(f"Crawling: {url} (Depth: {depth})")

    html = fetch_html(url)
    if not html:
        return []
    
    # Download assets like PDFs and images, and save them to the output folder
    download_assets(html, url, output_folder="knowledge")

    page_data = parse_html(html, url)
    sub_links = get_internal_links(html, url)

    sub_pages = []
    with ThreadPoolExecutor(max_workers=15) as executor:  # Adjust the number of workers as needed
        futures = [executor.submit(crawl, sub_url, depth - 1) for sub_url in sub_links]
        for future in futures:
            sub_pages.extend(future.result())

    return [page_data] + sub_pages

# Christian-JUN20===============
#download any seen pdfs and images
def download_assets(html, base_url, output_folder="knowledge"):
    os.makedirs(output_folder, exist_ok=True)
    soup = BeautifulSoup(html, "lxml")
    
    for tag in soup.find_all("a", href=True):
        href = tag["href"]
        file_url = urljoin(base_url, href)
        if any(file_url.lower().endswith(ext) for ext in [".pdf", ".png", ".jpg", ".jpeg", ".bmp", ".tiff"]):
            try:
                response = requests.get(file_url, headers=HEADERS, timeout=10)
                response.raise_for_status()
                filename = os.path.basename(urlparse(file_url).path)
                with open(os.path.join(output_folder, filename), "wb") as f:
                    f.write(response.content)
                logging.info(f"Downloaded: {filename}")
            except Exception as e:
                logging.warning(f"Failed to download {file_url}: {e}")
# ==========================

# Save parsed data to txt
def save_to_txt(parsed_data_list, domain_name, output_dir="knowledge"):
    
    output_dir = os.path.join("knowledge")
    os.makedirs(output_dir, exist_ok=True)

    filepath = os.path.join(output_dir, f"{domain_name}.txt")
    print(f"[Save] Writing data to file: {filepath}")

    with open(filepath, "w", encoding="utf-8") as f:
        for entry in parsed_data_list:
            # Write H1 (main title), if any
            for heading in entry["headings"].get("h1", []):
                f.write(f"{heading.strip()}\n\n")

            # Optionally write H2 and H3 headings
            for h_level in ["h2", "h3"]:
                for heading in entry["headings"].get(h_level, []):
                    f.write(f"{heading.strip()}\n\n")

            # Write all paragraphs
            for paragraph in entry["paragraphs"]:
                f.write(f"{paragraph.strip()}\n\n")

            # Write FAQs (question + answer)
            for faq in entry["faqs"]:
                question = faq["question"].strip()
                answer = faq["answer"].strip()
                f.write(f"{question}\n{answer}\n\n")

def run_scraper(urls_path="urls.txt", output_dir="knowledge", depth=2):
    from urllib.parse import urlparse

    with open(urls_path, "r", encoding="utf-8") as f:
        urls = [line.strip() for line in f if line.strip()]

    for url in urls:
        logging.info(f"[Start] Scraping: {url}")
        scraped_data = crawl(url, depth=depth)
        domain = urlparse(url).netloc.replace("www.", "")
        save_to_txt(scraped_data, domain, output_dir=output_dir)
        logging.info(f"[Success] Data from {url} saved to {output_dir}/{domain}.txt")

def main():
    # Read URLs from urls.txt
    with open("urls.txt", "r", encoding="utf-8") as f:
        urls = [line.strip() for line in f if line.strip()]

    for url in urls:
        print(f"\n[Start] Scraping: {url}")
        scraped_data = crawl(url, depth=2)  # Depth can be tuned
        # Replace prints like this:
        logging.info("Starting scraper")
        logging.debug("Fetched HTML from %s", url)

        domain = urlparse(url).netloc.replace("www.", "")
        save_to_txt(scraped_data, domain)

        print(f"[Success] Data from {url} saved to data/{domain}.txt\n")
        
if __name__ == "__main__":
    main()