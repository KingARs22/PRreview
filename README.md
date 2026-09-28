This is an Create an AI-powered code assistant that triggers on pull requests to analyze C++ code diffs, identify concurrency flaws, and automatically generate unit test cases. Structure the prompts to specifically evaluate software security vulnerabilities and enforce style guidelines.


Follow the steps to run this Automated PR review system

1.Install Dependencies: Run pip install fastapi uvicorn PyGithub requests google-genai in your virtual environment.
2.Expose the Local Server: Run ngrok http 8000 in your terminal to generate a secure, publicly accessible URL for your local port.
3.Configure GitHub Webhooks: Navigate to your target repository's Settings > Webhooks. Click Add webhook, paste the ngrok URL appended with /webhook, select application/json as the content type, and choose to trigger the webhook exclusively on Pull request events.
4.Execute the Service: Start the FastAPI application via uvicorn main:app --reload and ensure your GITHUB_TOKEN and GEMINI_API_KEY are exported in the terminal session.
