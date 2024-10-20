# config.py

DATABASE = {
    'host': 'localhost',
    'database': 'postgres',  # Update this with your database name
    'user': 'postgres',  # Update this with your database username
    'password': '1234'  # Update this with your database password
}

# GNN Model Parameters
GNN_PARAMS = {
    'in_feats': 10,
    'hidden_size': 20,
    'out_feats': 2
}

# Reinforcement Learning Parameters
RL_PARAMS = {
    'alpha': 0.1,  # Learning rate
    'gamma': 0.9,  # Discount factor
    'epsilon': 0.1  # Exploration-exploitation trade-off
}
