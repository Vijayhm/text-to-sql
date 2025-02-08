# main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3
import boto3
import json
import requests
import time
import google.generativeai as genai


GEMINI_API_KEY = "AIzaSyB5O6e07Qo8hmbz12qeM6gM4FpX74GiKM0"
genai.configure(api_key=GEMINI_API_KEY)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (you can restrict it later)
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

# AWS DynamoDB Configuration
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')  # Change region if needed.
CACHE_TABLE_NAME = "QueryCache"

# try:
#     cache_table = dynamodb.Table(CACHE_TABLE_NAME)
#     cache_table.load()  # Check if the table exists.
# except Exception as e:
#     print(f"Error loading DynamoDB table: {e}")
#     cache_table = None
try:
    cache_table = dynamodb.Table(CACHE_TABLE_NAME)
    cache_table.load()
except Exception as e:
    print("DynamoDB is not available. Skipping caching.")
    cache_table = None

# DATABASE_PATH = "sample.db"
DATABASE_PATH = "employees.db"

class QueryRequest(BaseModel):
    query: str

def get_schema():
    """
    Extracts the schema from the SQLite database.
    Returns a dictionary with table names as keys and lists of column names as values.
    """
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    schema = {}
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    for (table_name,) in tables:
        cursor.execute(f"PRAGMA table_info({table_name});")
        columns_info = cursor.fetchall()
        columns = [col[1] for col in columns_info]
        schema[table_name] = columns
    conn.close()
    return schema


def generate_sql_from_nl(nl_query, schema):
    """
    Uses Google Gemini API to convert natural language queries into SQL.
    Sends an HTTP request instead of using google.generativeai.
    """
    schema_text = "\n".join(
        [f"Table {table}: " + ", ".join(columns) for table, columns in schema.items()]
    )

    prompt = f"""
    You are an SQL AI assistant. Convert the user's natural language request into a valid SQL query.
    Follow these rules:
    1. Only return a valid SQL query, nothing else.
    2. Ensure column names exactly match the database schema.
    3. Never assume extra columns; only use the ones listed.

    Database Schema:
    {schema_text}

    User Query: "{nl_query}"

    SQL Query:
    """

    print("\n========== DEBUGGING PROMPT SENT TO GEMINI ==========")
    print(prompt)
    print("====================================================\n")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"

    headers = {
        "Content-Type": "application/json"
    }

    data = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }

    try:
        response = requests.post(url, headers=headers, json=data)

        if response.status_code != 200:
            print(f"Gemini API Error: {response.status_code} - {response.text}")
            return "SELECT 'Gemini API request failed' AS error"

        result = response.json()
        
        sql_query = result.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip()

        # Remove Markdown SQL formatting if present
        sql_query = sql_query.replace("```sql", "").replace("```", "").strip()

        print("\n========== CLEANED GEMINI RESPONSE ==========")
        print(sql_query)
        print("==============================================\n")

        print("\n========== GEMINI RESPONSE ==========")
        print(sql_query)
        print("=====================================\n")

        # Validate that the response is a valid SQL query
        if not any(sql_query.lower().startswith(keyword) for keyword in ["select", "update", "delete", "insert"]):
            print("\n⚠️ Warning: Gemini generated an invalid SQL query!\n")
            return "SELECT 'Invalid SQL generated' AS error"

        return sql_query

    except Exception as e:
        print(f"Gemini API Error: {e}")
        return "SELECT 'Error in query generation' AS error"

def get_cached_query(query):
    """
    Checks AWS DynamoDB for a cached result for this query.
    Returns the cached result if available and not expired.
    """
    if not cache_table:
        return None
    try:
        response = cache_table.get_item(Key={'query': query})
        if 'Item' in response:
            if response['Item']['ttl'] > int(time.time()):
                return json.loads(response['Item']['result'])
    except Exception as e:
        print(f"Error retrieving cache: {e}")
    return None

def cache_query_result(query, result, ttl_seconds=3600):
    """
    Caches the query result in AWS DynamoDB with a TTL (default: 1 hour).
    If DynamoDB is unavailable, it simply skips caching.
    """
    if not cache_table:
        return
    try:
        ttl = int(time.time()) + ttl_seconds  # Expiry time for the cache
        cache_table.put_item(
            Item={
                'query': query,
                'result': json.dumps(result),
                'ttl': ttl
            }
        )
    except Exception as e:
        print(f"Error caching query result: {e}")

def summarize_results_with_gemini(query_results):
    """
    Summarizes the query results using Google Gemini API.
    Converts structured database output into a human-readable summary.
    """
    if not query_results:
        return "No records found."

    # If the result contains only one key and it's COUNT, return a numeric summary
    if len(query_results) == 1 and len(query_results[0]) == 1 and "count" in query_results[0].keys():
        return f"The total number is {query_results[0]['count']}."


    # Convert query result to JSON string
    data_text = json.dumps(query_results, indent=2)

    prompt = f"""
    You are an AI assistant summarizing database query results.
    Given the following structured JSON data, create a short natural language summary.

    Data:
    {data_text}

    Summary:
    """

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    
    headers = {
        "Content-Type": "application/json"
    }

    data = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }

    try:
        response = requests.post(url, headers=headers, json=data)

        if response.status_code != 200:
            print(f"Gemini API Error: {response.status_code} - {response.text}")
            return "Failed to generate summary."

        result = response.json()
        
        # Extract summary response
        summary_text = result.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip()

        print("\n========== SUMMARY GENERATED BY GEMINI ==========")
        print(summary_text)
        print("==============================================\n")

        return summary_text

    except Exception as e:
        print(f"Gemini API Error: {e}")
        return "Error summarizing query results."



@app.post("/query")
def process_query(request: QueryRequest):
    nl_query = request.query

    # Step 1: Check for a cached result.
    cached_result = get_cached_query(nl_query)
    if cached_result is not None:
        return {"source": "cache", "result": cached_result}

    # Step 2: Extract database schema.
    schema = get_schema()

    # Step 3: Generate SQL query using Gemini API.
    sql_query = generate_sql_from_nl(nl_query, schema)
    print(f"Generated SQL: {sql_query}")

    # Step 4: Execute the SQL query on SQLite.
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row  # Enable dict-like access to rows.
        cursor = conn.cursor()
        cursor.execute(sql_query)
        rows = cursor.fetchall()
        result = [dict(row) for row in rows]
        print("==============result================")
        print(result)
        print("=====================================")
        conn.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Step 5: Cache the result.
    cache_query_result(nl_query, result)
    summary = summarize_results_with_gemini(result)

    return {"source": "db", "summary": summary, "result": result}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
