@Author:Shoaib
# Hybrid Method for Probabilistic Primary Key Identification

This project implements a hybrid system for probabilistic primary key identification in relational databases using heuristic filtering, attention-based Graph Neural Networks (GNNs), and reinforcement learning (RL).

## Project Structure
- **models/**: Contains the GNN model
- **scripts/**: Core scripts for connecting to the database, running heuristics,RL agent and executing the GNN.
- **main.py**: Entry point to run the full pipeline.

> Installation
1. Clone this repository.
2. Install required packages:
3. pip install -r requirements.txt

> This also can be pulled from Docker by  running
```https://hub.docker.com/r/shoaibswe/generate_primary_key```

> Steps to Run the Application

1. Build and Run with docker-compose: Run the following command to build and start both containers (Python app and PostgreSQL):
```make compose-up```

1.Verify the Containers: Check if the containers are running:
```docker ps```
You should see both postgres_container and python_app_container.

3.Access Logs: Monitor the logs of the Python application to verify it's working:
```docker logs python_app_container```

4.Stop the Services: To stop the containers:
```make compose-down```
