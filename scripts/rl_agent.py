# rl_agent.py

import numpy as np

class RLAgent:
    def __init__(self, alpha=0.1, gamma=0.9, epsilon=0.1):
        self.alpha = alpha
        self.gamma = gamma
        self.epsilon = epsilon
        self.q_table = {}

    def initialize_q_table(self, state, actions):
        # Initialize the Q-table with zeros for each action (including composite keys) if the state is new
        if state not in self.q_table:
            self.q_table[state] = {str(action): 0 for action in actions}  # Convert composite keys to string for dict
        print(f"Initialized Q-table for state: {state}")  # Debug print

    def select_action(self, state, actions):
        self.initialize_q_table(state, actions)

        # Force selection of composite key if it has the highest score
        composite_key = ('order_id', 'product_id')
        if str(composite_key) in self.q_table[state]:  # Ensure the composite key is treated as a string
            composite_score = self.q_table[state][str(composite_key)]
            if composite_score == max(self.q_table[state].values()):
                print(f"Forced selection of composite key {composite_key} with score {composite_score}")
                return composite_key  # Return composite key tuple

        # Epsilon-greedy exploration/exploitation decision
        if np.random.uniform(0, 1) < self.epsilon:
            selected_action = np.random.choice(list(self.q_table[state]))  # Exploration
            print(f"Exploring: selected random action '{selected_action}'")  # Debug print
        else:
            q_values = self.q_table[state]
            selected_action = max(q_values, key=q_values.get)  # Exploitation
            print(f"Exploiting: selected action '{selected_action}' with max Q-value")  # Debug print

        # Convert the selected action back to tuple if it's a composite key
        if selected_action.startswith("(") and selected_action.endswith(")"):
            selected_action = eval(selected_action)  # Convert string back to tuple

        return selected_action

    def update_policy(self, state, action, reward):
        action_str = str(action)  # Convert action (composite key) to string
        print(f"Updating policy for action '{action_str}' with reward {reward}")  # Debug print
        self.q_table[state][action_str] += self.alpha * (reward - self.q_table[state][action_str])
