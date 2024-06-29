########## load environment variables
from dotenv import load_dotenv, find_dotenv
import os
load_dotenv(find_dotenv())  # looking for .env file
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
MONGO = os.getenv('MONGO')


class envs:
    def __init__(self):
        self.openai_key = OPENAI_API_KEY
        self.pinecone_key = PINECONE_API_KEY
        self.mongo_uri = MONGO