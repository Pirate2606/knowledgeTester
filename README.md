# KnowledgeTester

## Instructions:

### Prerequisites:
    1. Python3 should be installed on the system.
    2. Weavy should be up and running.
    3. Need an active internet connection.

### To run the project locally, follow the following steps:
    1. Setup a virtual environment:
        For ubuntu:
            1. sudo apt install virtualenv
            2. virtualenv -p python3 name_of_environment
            3. To activate: source name_of_environment/bin/activate
        For windows:
            1.	pip install virtualenv
            2.	python -m venv <path for creating virtualenv>
            3.	To activate: <virtualenv path>\Scripts\activate

    2. Clone the repository: git clone https://github.com/Pirate2606/knowledgeTester
    3. Change the directory: cd knowledgeTester
    4. Install the requirements: pip install -r requirements.txt
    5. Generate OAuth client ID and Secret for Google.
    6. Generate API key for YouTube API
    7. Place the client ID, client secret, API key, Weavy ID, and Weavy secret in "config.py".
    8. Create database: flask createdb
    9. Run the server: python3 app.py
    10. Open this link in browser: http://127.0.0.1:5000/