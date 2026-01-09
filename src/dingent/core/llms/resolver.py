"""
Model Resolution Service

This service implements a cascading strategy for resolving which LLM model configuration
to use at runtime. The priority order is:

1. Assistant-level configuration (highest priority)
2. Workflow-level configuration  
3. Workspace-level default configuration
4. Environment fallback (lowest priority)
"""

from uuid import UUID

from langchain_litellm import ChatLiteLLM
from sqlmodel import Session, select

from dingent.core.db.models import Assistant, LLMModelConfig, Workflow, Workspace
from dingent.core.security.crypto import get_secret_manager


class ModelResolver:
    """
    Resolves and builds ChatModel instances based on cascading configuration.
    """

    def __init__(self, session: Session):
        self.session = session
        self.secret_manager = get_secret_manager()

    def resolve_for_assistant(
        self,
        assistant_id: UUID | None = None,
        workflow_id: UUID | None = None,
        workspace_id: UUID | None = None,
    ) -> ChatLiteLLM:
        """
        Resolve the appropriate model configuration using cascading strategy.

        Priority order:
        1. Assistant's model_config_id
        2. Workflow's model_config_id
        3. Workspace's default_model_config_id
        4. Environment fallback

        Args:
            assistant_id: Optional assistant ID for highest priority lookup
            workflow_id: Optional workflow ID for medium priority lookup
            workspace_id: Optional workspace ID for low priority lookup

        Returns:
            ChatLiteLLM instance configured with resolved parameters
        """
        config = self._resolve_config(assistant_id, workflow_id, workspace_id)

        if config:
            return self._build_model_from_config(config)
        else:
            # Fallback to environment-based configuration
            return ChatLiteLLM()

    def _resolve_config(
        self,
        assistant_id: UUID | None,
        workflow_id: UUID | None,
        workspace_id: UUID | None,
    ) -> LLMModelConfig | None:
        """
        Internal method to resolve configuration with cascading logic.
        """
        # Priority 1: Assistant-level configuration
        if assistant_id:
            assistant = self.session.get(Assistant, assistant_id)
            if assistant and assistant.model_config_id:
                config = self.session.get(LLMModelConfig, assistant.model_config_id)
                if config and config.is_active:
                    return config

        # Priority 2: Workflow-level configuration
        if workflow_id:
            workflow = self.session.get(Workflow, workflow_id)
            if workflow and workflow.model_config_id:
                config = self.session.get(LLMModelConfig, workflow.model_config_id)
                if config and config.is_active:
                    return config

        # Priority 3: Workspace-level default configuration
        if workspace_id:
            workspace = self.session.get(Workspace, workspace_id)
            if workspace and workspace.default_model_config_id:
                config = self.session.get(LLMModelConfig, workspace.default_model_config_id)
                if config and config.is_active:
                    return config

        # Priority 4: No configuration found, will use environment fallback
        return None

    def _build_model_from_config(self, config: LLMModelConfig) -> ChatLiteLLM:
        """
        Build a ChatLiteLLM instance from a model configuration.

        Args:
            config: LLMModelConfig database model

        Returns:
            Configured ChatLiteLLM instance
        """
        # Decrypt API key if present
        api_key = None
        if config.encrypted_api_key:
            api_key = self.secret_manager.decrypt(config.encrypted_api_key)

        # Build model name for LiteLLM
        # For OpenAI, use model name directly; for others, use provider/model format
        model_name = config.model if config.provider == "openai" else f"{config.provider}/{config.model}"

        # Prepare kwargs
        kwargs = {
            "model": model_name,
            **config.parameters,  # Include any extra parameters stored in JSON
        }

        # Add optional parameters if present
        if api_key:
            kwargs["api_key"] = api_key
        if config.api_base:
            kwargs["api_base"] = config.api_base
        if config.api_version:
            kwargs["api_version"] = config.api_version

        return ChatLiteLLM(**kwargs)

    def resolve_for_workflow(
        self,
        workflow_id: UUID,
        workspace_id: UUID | None = None,
    ) -> ChatLiteLLM:
        """
        Convenience method to resolve model for a workflow context.

        Args:
            workflow_id: Workflow ID
            workspace_id: Optional workspace ID for fallback

        Returns:
            ChatLiteLLM instance
        """
        return self.resolve_for_assistant(
            assistant_id=None,
            workflow_id=workflow_id,
            workspace_id=workspace_id,
        )

    def resolve_for_workspace(self, workspace_id: UUID) -> ChatLiteLLM:
        """
        Convenience method to resolve model for a workspace context.

        Args:
            workspace_id: Workspace ID

        Returns:
            ChatLiteLLM instance
        """
        return self.resolve_for_assistant(
            assistant_id=None,
            workflow_id=None,
            workspace_id=workspace_id,
        )
