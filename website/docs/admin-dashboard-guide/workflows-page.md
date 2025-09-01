---
sidebar_position: 5
---

# Workflows Page

A workflow in Dingent is a powerful visual editor that defines the high-level logic for handling a user's request. It operates on a **Swarm** architecture, where you define possible routes between different specialized assistants (nodes). Based on the user's query, the LLM itself intelligently decides which path to take through the network of assistants you create.

In its simplest form, a workflow links a single assistant to the chat interface. In more advanced scenarios, a workflow can route tasks between multiple assistants, allowing for complex, multi-step logic.

## Creating Your First Workflow

1.  Navigate to the Workflows page and click **"Add Workflow"**.
2.  Give your workflow a descriptive **Name** (e.g., "Main Chat Workflow").
3.  You will see a visual editor. From the dropdown menu, select the assistant you want to use (e.g., "Tech Trends Assistant"). This will add the assistant as a node on your canvas.
4.  The very first node you add is automatically designated as the **Start node** and will be highlighted in green. This is the entry point for all user requests.
5.  Click and drag from one node's handle to another to create a connection.
In Dingent's Swarm architecture, a connection represents a *potential route* that the model can choose to take.
The model itself decides whether to route the task from the current node to the next based on the context. You can even create bidirectional links, allowing for complex, non-linear conversations.
6.  For this simple setup, connect the `Start` node to your other assistant node.
7.  Click **Save**.

## Editing Nodes and Connections

  * **Modify or Delete**: To modify or delete a node, **right-click** on it to open a context menu with available options.
  * **Change Start Node**: If you have multiple nodes and wish to change the entry point, you can assign a different node as the Start node via the right-click menu.
  * **Important**: The designated Start node is essential for the workflow's operation and **cannot be deleted**. You must assign a different node as the Start node before the original one can be removed.

## Activating the Workflow

After creating and saving your workflow, you must activate it to make it live in the chat interface:

1.  Go to the **Settings** page.
2.  In the **"Current Workflow"** dropdown, select the workflow you just created.
3.  Click **Save**.

Your new workflow is now live\! All conversations in the chat interface will be handled by this logic.

-----

➡️ **Next: Learn how to debug your agent on [The Logs Page](./logs-page.md)**
