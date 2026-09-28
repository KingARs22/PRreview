import os
import requests
import chromadb
from github import Github
from google import genai
from dotenv import load_dotenv

# Load API keys from the .env file
load_dotenv()

gh = Github(os.getenv("GITHUB_TOKEN"))
gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Initialize an embedded ChromaDB instance. 
# This automatically creates a 'vectordb' directory in your project folder to persist data.
chroma_client = chromadb.PersistentClient(path="./vectordb")
collection = chroma_client.get_or_create_collection(name="pr_history")

def get_gemini_embedding(text: str) -> list[float]:
    """Converts the text diff into a dense vector array using Gemini's embedding model."""
    result = gemini_client.models.embed_content(
        model="gemini-embedding-2",
        contents=text
    )
    return result.embeddings[0].values

def process_pull_request(repo_name: str, pr_number: int):
    repo = gh.get_repo(repo_name)
    pr = repo.get_pull(pr_number)
    
    headers = {
        "Authorization": f"token {os.getenv('GITHUB_TOKEN')}", 
        "Accept": "application/vnd.github.v3.diff"
    }
    diff_response = requests.get(pr.diff_url, headers=headers)
    diff_text = diff_response.text
    
    if not diff_text or len(diff_text) > 20000:
        pr.create_issue_comment("⚠️ Diff is too large for automated AI review. Please split the PR.")
        return

    # 1. Generate an embedding for the incoming code diff
    current_diff_embedding = get_gemini_embedding(diff_text)
    
    # 2. Query the Vector DB for the top 2 most semantically similar past PRs
    historical_context = ""
    if collection.count() > 0:
        db_results = collection.query(
            query_embeddings=[current_diff_embedding],
            n_results=2
        )
        
        if db_results['documents'] and db_results['documents'][0]:
            historical_context = "### Historical Context (Similar Past PRs):\n"
            for idx, doc in enumerate(db_results['documents'][0]):
                # Retrieve the feedback previously given to similar code
                past_feedback = db_results['metadatas'][0][idx].get("feedback", "No feedback recorded.")
                historical_context += f"- Past AI Feedback: {past_feedback}\n"
    
    # 3. Construct the RAG Prompt
    prompt = f"""
    You are an expert C++ security and operating systems reviewer. Analyze this code diff.
    Focus your evaluation strictly on concurrency flaws common in multi-threaded OS shell simulations, including unprotected shared memory access and deadlocks.
    
    {historical_context}
    *If historical context is provided above, ensure the developer is not repeating those specific past mistakes.*
    
    Current Diff:
    {diff_text}
    
    Output a concise Markdown report with headers for 'Critical Security Flaws', 'Concurrency Issues', and 'Optimization Suggestions'.
    """
    
    # 4. Generate the Review via Gemini 2.0 Flash
    response = gemini_client.models.generate_content(
        model='gemini-2.0-flash',
        contents=prompt,
    )
    review_text = response.text
    
    # 5. Publish the feedback to the GitHub PR timeline
    pr.create_issue_comment(f"### 🤖 AI System Analysis\n\n{review_text}")
    
    # 6. Self-Learning: Save this interaction back to ChromaDB for future PRs
    # We store a truncated version of the review to use as metadata context next time
    collection.add(
        ids=[f"{repo_name}-PR{pr_number}"],
        embeddings=[current_diff_embedding],
        documents=[diff_text],
        metadatas=[{"feedback": review_text[:400]}] 
    )