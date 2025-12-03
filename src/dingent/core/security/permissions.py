from enum import Enum


class Resource(str, Enum):
    """The 'nouns' of your system."""

    ASSISTANT = "assistant"
    WORKFLOW = "workflow"
    LOG = "log"
    SETTING = "setting"
    USER = "user"
    PLUGIN = "plugin"
    MARKET = "market"
    BILLING = "billing"


class Action(str, Enum):
    """The 'verbs' that can be performed."""

    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    LIST = "list"
    EXECUTE = "execute"
    PUBLISH = "publish"


class Scope(str, Enum):
    """The scope qualifier, distinguishing user-level from admin-level."""

    OWN = "own"  # Refers to resources owned by the current user
    ALL = "all"  # Refers to all resources in the system (admin)
