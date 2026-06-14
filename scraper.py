import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import urllib.parse
import re
import csv
import sys
import time

# 1. System/Terminal Configuration
def init_terminal_encoding():
    """Configures system stdout and stderr to handle UTF-8 symbols on Windows terminals."""
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')

def find_next_url(html_text, current_url):
    """Return the absolute URL of the next page, or None if this is the last."""
    soup = BeautifulSoup(html_text, "html.parser")
    next_li = soup.find("li", class_="next")
    if next_li is None:
        return None  # we've reached the end of the catalog
    next_href = next_li.find("a")["href"]
    return urljoin(current_url, next_href)


# 2. Side-Effects / I/O HTTP Fetching
def fetch_page_content(url, headers):
    """Performs HTTP GET request and returns the response."""
    response = requests.get(url, headers=headers, timeout=10)
    response.encoding = "utf-8"
    response.raise_for_status()
    return response

def fetch_book_details(detail_url, headers):
    """
    Fetches the detail page of a book and extracts:
    - UPC
    - Stock Count
    - Description
    - Category
    Returns a dictionary of these fields. If any failure occurs, returns default empty values.
    """
    default_details = {
        "upc": "",
        "stock_count": 0,
        "description": "",
        "category": ""
    }
    try:
        response = requests.get(detail_url, headers=headers, timeout=10)
        response.encoding = "utf-8"
        if response.status_code != 200:
            print(f"  [Warning] Failed to fetch details for {detail_url}: Status {response.status_code}")
            return default_details
            
        soup = BeautifulSoup(response.text, "html.parser")
        
        # 1. Category extraction
        category = ""
        breadcrumb = soup.find("ul", class_="breadcrumb")
        if breadcrumb:
            lis = breadcrumb.find_all("li")
            if len(lis) >= 3:
                category = lis[2].text.strip()
                
        # 2. Description extraction
        description = ""
        desc_div = soup.find("div", id="product_description")
        if desc_div:
            desc_p = desc_div.find_next_sibling("p")
            if desc_p:
                description = desc_p.text.strip()
                
        # 3. Product Info Table (UPC & Stock count)
        upc = ""
        stock_count = 0
        table = soup.find("table", class_="table-striped")
        if table:
            rows = table.find_all("tr")
            table_data = {}
            for row in rows:
                th = row.find("th")
                td = row.find("td")
                if th and td:
                    table_data[th.text.strip()] = td.text.strip()
            
            upc = table_data.get("UPC", "")
            availability = table_data.get("Availability", "")
            # Find the stock number (e.g., "In stock (22 available)")
            if availability:
                match = re.search(r"\((\d+)\s+available\)", availability)
                if match:
                    stock_count = int(match.group(1))
                    
        return {
            "upc": upc,
            "stock_count": stock_count,
            "description": description,
            "category": category
        }
    except Exception as e:
        print(f"  [Warning] Error fetching details for {detail_url}: {e}")
        return default_details

# 3. Pure Data Transformations
def get_book_articles(html_text):
    """Parses HTML text and returns a list of BS4 article pods."""
    soup = BeautifulSoup(html_text, "html.parser")
    return soup.find_all("article", class_="product_pod")

def parse_rating(classes):
    """Converts star rating class name word to integer."""
    rating_map = {
        "One": 1,
        "Two": 2,
        "Three": 3,
        "Four": 4,
        "Five": 5
    }
    word = [c for c in classes if c != "star-rating"][0]
    return rating_map.get(word, 0)

def extract_book_data(article, base_url, index):
    """Transforms a single HTML article pod into a structured dictionary."""
    title_a = article.find("h3").find("a")
    full_title = title_a.get("title", "").strip()
    
    href = title_a.get("href", "").strip()
    detail_link = urllib.parse.urljoin(base_url, href)
    
    price_text = article.find("p", class_="price_color").text.strip()
    price_clean = re.sub(r"[^\d.]", "", price_text)
    price_val = float(price_clean)
    
    rating_classes = article.find("p", class_="star-rating").get("class", [])
    rating_val = parse_rating(rating_classes)
    
    stock_text = article.find("p", class_="instock availability").text.strip()
    stock_clean = "In stock" if "in stock" in stock_text.lower() else "Out of stock"
    
    return {
        "index": index,
        "full_title": full_title,
        "price": price_val,
        "rating": rating_val,
        "stock": stock_clean,
        "link": detail_link
    }

def truncate_title(title, max_len=40):
    """Truncates titles strictly matching screenshot's word/dot truncation rules."""
    return title[:27] + "..." if len(title) > max_len else title

def format_rating_stars(rating):
    """Produces star rating characters, adding details for 3-star rating."""
    return "★" * rating + (" (3)" if rating == 3 else "")

def format_book_line(book, total_count):
    """Formats a single book row block or ellipsis row for the console."""
    index = book["index"]
    if not (1 <= index <= 7 or index == total_count):
        return "  ..." if index == 8 else ""
        
    title_display = truncate_title(book["full_title"])
    rating_stars = format_rating_stars(book["rating"])
    prefix = f"  {index}. "
    main_row = f"{prefix}{title_display}"
    price_str = f"£{book['price']:.2f}"
    
    # Align price at column index 56 and start rating 3 spaces after price
    formatted_row = f"{main_row:<56}{price_str}   {rating_stars}"
    return f"{formatted_row}\n     {book['stock']}"

def calculate_stats(books):
    """Computes mathematical and count aggregates over the scraped book set."""
    if not books:
        return {"avg_price": 0.0, "total_price": 0.0, "five_star_count": 0, "in_stock_count": 0, "total_stock": 0}
    prices = [b["price"] for b in books]
    total_price = sum(prices)
    avg_price = total_price / len(prices)
    five_star_count = sum(1 for b in books if b["rating"] == 5)
    in_stock_count = sum(1 for b in books if b["stock"] == "In stock")
    total_stock = sum(b.get("stock_count", 0) for b in books)
    return {
        "avg_price": avg_price,
        "total_price": total_price,
        "five_star_count": five_star_count,
        "in_stock_count": in_stock_count,
        "total_stock": total_stock
    }

def format_summary(books_count, stats):
    """Produces the final summary block string with aligned label/value pairs."""
    labels = [
        ("Books scraped:", f"{books_count}"),
        ("Average price:", f"£{stats['avg_price']:.2f}"),
        ("Total value:", f"£{stats['total_price']:.2f}"),
        ("Highest rated:", f"{stats['five_star_count']} books with 5 stars"),
        ("In-stock status:", f"{stats['in_stock_count']} books marked in stock"),
        ("Total inventory:", f"{stats['total_stock']} units available")
    ]
    lines = [f"  {label:<18}  {val}" for label, val in labels]
    return "Summary:\n" + "\n".join(lines)

# 4. Side-Effects / I/O CSV Writing
def write_csv(books, csv_file):
    """Writes the list of extracted book dictionaries to a CSV file."""
    with open(csv_file, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Title", "Price", "Rating", "Availability", "Link", "UPC", "Stock Count", "Category", "Description"])
        for book in books:
            writer.writerow([
                book.get("full_title", ""),
                book.get("price", 0.0),
                book.get("rating", 0),
                book.get("stock", ""),
                book.get("link", ""),
                book.get("upc", ""),
                book.get("stock_count", 0),
                book.get("category", ""),
                book.get("description", "")
            ])

# 5. Pipeline Orchestrator
def run_scraper(url, csv_file, max_pages=None):
    """Executes the scraper pipeline end-to-end, feeding inputs to functional units."""
    init_terminal_encoding()
    
    border = "=" * 90
    print(border)
    print("BOOK SCRAPER")
    print(border)
    print()
    
    headers = {
        "User-Agent": "BookScraper/1.0 (Polite book scraper for learning purposes)"
    }
    
    all_books = []
    current_page_url = url
    page_num = 1
    total_pages = 50
    if max_pages is not None:
        total_pages = min(50, max_pages)
        
    total_books_estimate = 1000 if max_pages is None else total_pages * 20
    
    # We will use this to track how many books we have processed overall
    book_global_index = 1
    
    while current_page_url and page_num <= total_pages:
        print(f"Scraping catalog page {page_num} of {total_pages}: {current_page_url}")
        
        try:
            response = fetch_page_content(current_page_url, headers)
            html_text = response.text
            
            # Determine next page URL before processing books on this page
            next_page_url = find_next_url(html_text, current_page_url)
        except Exception as e:
            print(f"  [Warning] Failed to fetch catalog page {page_num}: {e}")
            # Fallback URL calculation for next page
            current_page_url = f"https://books.toscrape.com/catalogue/page-{page_num + 1}.html"
            page_num += 1
            continue
            
        articles = get_book_articles(html_text)
        print(f"  Found {len(articles)} books on page {page_num}")
        
        for art in articles:
            try:
                # Extract basic data (title, price, rating, stock status, detail link)
                book = extract_book_data(art, current_page_url, book_global_index)
                
                # Fetch detailed page fields (UPC, stock count, description, category)
                print(f"  -> Scraping book {book_global_index} of {total_books_estimate}: \"{truncate_title(book['full_title'], 30)}\"")
                details = fetch_book_details(book["link"], headers)
                book.update(details)
                
                all_books.append(book)
            except Exception as e:
                print(f"  [Warning] Failed to process book {book_global_index}: {e}")
            
            book_global_index += 1
            # Polite delay between book detail page requests (0.5s)
            time.sleep(0.5)
            
        # Update for next iteration
        current_page_url = next_page_url
        page_num += 1
        
        # Polite delay between page requests (1.0s)
        if current_page_url:
            time.sleep(1.0)
            
    total_count = len(all_books)
    print()
    print(f" ✓ Scraped {total_count} books successfully")
    print()
    
    # Filter empty outputs to output formatted rows
    for line in filter(None, (format_book_line(b, total_count) for b in all_books)):
        print(line)
        
    print()
    write_csv(all_books, csv_file)
    print(f" ✓ Saved: {csv_file}")
    print()
    
    stats = calculate_stats(all_books)
    print(format_summary(total_count, stats))

def main():
    try:
        # Set max_pages to a number (e.g. 1) to test a subset, or leave None for the full 50-page scrape
        run_scraper("https://books.toscrape.com/", "books.csv", max_pages=None)
    except Exception as e:
        print(f"An error occurred: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()

