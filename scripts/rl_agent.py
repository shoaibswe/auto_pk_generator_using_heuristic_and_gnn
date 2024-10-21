# rl_agent.py

class RLAgent:
    def __init__(self):
        self.q_table = {}

    def select_action(self, state, actions):
        """Select an action based on the current state and Q-table."""
        if state not in self.q_table:
            # Initialize Q-values for all actions in this state
            self.q_table[state] = {action: 0 for action in actions}
            print(f"Initialized Q-table for state: {state}")

        # Choose the action with the highest Q-value
        q_values = self.q_table[state]
        max_q = max(q_values.values())
        max_actions = [action for action, q in q_values.items() if q == max_q]
        selected_action = max_actions[0]  # Select the first action with max Q-value
        print(f"Selected action '{selected_action}' with Q-value: {max_q}")
        return selected_action
