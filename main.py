import os
from fastapi import FastAPI, Request, BackgroundTasks
from reviewer import process_pull_request

app = FastAPI()

@app.post("/webhook")
async def github_webhook(request: Request, background_tasks: BackgroundTasks):
    payload = await request.json()
    
    # GitHub webhooks for pull requests include an 'action' property and a nested 'pull_request' object.
    if "pull_request" not in payload:
        return {"status": "ignored", "reason": "Not a pull request event"}
        
    action = payload.get("action")
    if action not in ["opened", "synchronize"]:
        return {"status": "ignored", "reason": f"Action '{action}' ignored"}
        
    pr_number = payload["pull_request"]["number"]
    repo_full_name = payload["repository"]["full_name"]
    
    # Injecting BackgroundTasks allows FastAPI to send an HTTP 200 response immediately.
    # This prevents the GitHub webhook from timing out while the external LLM call executes.
    background_tasks.add_task(process_pull_request, repo_full_name, pr_number)
    
    return {"status": "accepted", "message": "PR review queued"}