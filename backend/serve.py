from app import app
from flask import send_from_directory
import os

FRONTEND = os.path.join(os.path.dirname(__file__), '..', 'frontend')

@app.route('/')
def index():
    return send_from_directory(FRONTEND, 'index.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=False)
