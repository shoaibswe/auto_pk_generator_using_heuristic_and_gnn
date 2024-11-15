# config.py

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Database Configuration (only from environment variables)
DATABASE = {
    "host": os.getenv("DB_HOST"),
    "port": int(os.getenv("DB_PORT")),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME"),
}

# GNN Model Parameters
GNN_PARAMS = {
    "in_feats": 10,  # Number of input features
    "hidden_size": 20,  # Size of hidden layer
    "out_feats": 2,  # Number of output features
}
