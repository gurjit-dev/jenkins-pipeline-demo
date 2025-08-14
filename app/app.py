from flask import Flask
app = Flask(__name__)

@app.get("/")
def index():
    return "Hello from EKS via Jenkins 🚀"

@app.get("/healthz")
def health():
    return "ok"
