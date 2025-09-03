import asyncio

import litellm
from litellm.budget_manager import BudgetManager
from litellm.integrations.custom_logger import CustomLogger


# This is an "internal" class used by AnalyticsManager.
# The underscore indicates it's not meant for direct use outside the manager.
class _AnalyticsCallbackHandler(CustomLogger):
    """
    Custom litellm logger that connects to a BudgetManager
    to update costs after a successful API call.
    """

    def __init__(self, budget_manager: BudgetManager):
        self.budget_manager = budget_manager

    def log_success_event(self, kwargs, response_obj, start_time, end_time):
        """Sync version of the callback."""
        # Extract user from metadata passed in the litellm call
        user = kwargs.get("litellm_params", {}).get("metadata", {}).get("user_id")
        if user:
            self.budget_manager.update_cost(user, response_obj)

    async def async_log_success_event(self, kwargs, response_obj, start_time, end_time):
        """Async version of the callback."""
        # Extract user from metadata passed in the litellm call
        user = kwargs.get("litellm_params", {}).get("metadata", {}).get("user_id")
        if user:
            self.budget_manager.update_cost(user, response_obj)


class AnalyticsManager:
    """
    Manages cost and budget analytics for litellm.

    This class initializes a BudgetManager and a custom callback handler,
    and provides a simple interface to register the callback and manage user budgets.
    """

    def __init__(self, project_name: str):
        """
        Initializes the BudgetManager and the callback handler.

        Args:
            project_name (str): A unique name for the project to store budget data.
        """
        self.budget_manager = BudgetManager(project_name=project_name)
        self._callback_handler = _AnalyticsCallbackHandler(self.budget_manager)

    def register(self):
        """
        Registers the analytics callback with litellm.

        This method is idempotent, meaning it won't add duplicate callbacks
        if called multiple times.
        """
        if self._callback_handler not in litellm.callbacks:
            litellm.callbacks.append(self._callback_handler)
        print("AnalyticsManager callback registered with litellm.")

    def get_or_create_user_budget(self, user: str, total_budget: float):
        """
        Creates a budget for a user if they don't already have one.

        Args:
            user (str): The identifier for the user.
            total_budget (float): The total budget to assign to the user.
        """
        if not self.budget_manager.is_valid_user(user):
            self.budget_manager.create_budget(total_budget=total_budget, user=user)
            print(f"Budget created for user '{user}' with a total of ${total_budget}.")
        else:
            print(f"User '{user}' already has an existing budget.")

    def get_user_cost(self, user: str) -> dict:
        """
        Retrieves the current spending data for a specific user.

        Args:
            user (str): The identifier for the user.

        Returns:
            dict: A dictionary containing the user's spending information.
        """
        return self.budget_manager.get_spend_for_user(user)


# --- Example Usage ---
async def main():
    # 1. Initialize the manager for your project
    analytics_manager = AnalyticsManager(project_name="my_langgraph_project")

    # 2. Register the callback to start tracking
    analytics_manager.register()

    # 3. Define users and set up their budgets
    user_admin = "admin"
    user_guest = "guest-1234"

    analytics_manager.get_or_create_user_budget(user=user_admin, total_budget=100.0)
    analytics_manager.get_or_create_user_budget(user=user_guest, total_budget=5.0)

    # 4. Make an LLM call, passing the 'user_id' in metadata
    # This is how the callback knows whose budget to update.
    print(f"\nMaking a call for user: {user_admin}...")
    await litellm.acompletion(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": "Hello, how are you?"}],
        metadata={"user_id": user_admin},  # Pass user_id here!
    )

    # 5. Check the user's cost
    admin_cost = analytics_manager.get_user_cost(user_admin)
    print(f"Current cost for '{user_admin}': ${admin_cost['total_spend']:.6f}")

    guest_cost = analytics_manager.get_user_cost(user_guest)
    print(f"Current cost for '{user_guest}': ${guest_cost['total_spend']:.6f}")


if __name__ == "__main__":
    # In a real application, you would set your API keys
    # import os
    # os.environ["OPENAI_API_KEY"] = "your-key-here"

    # Run the async main function
    asyncio.run(main())
