from dingent.engine.plugins.manager import PluginManager


def test_manager_init():
    resource_manager = "fake_rm"
    manager = PluginManager("fake_plugins", {"resource_manager": resource_manager})
    database = {"name": "fake database", "uri": "sqlite:///fake.sqlite"}
    tool = manager.load_plugin(
        "fake", {"llm": "fake_llm", "vectorstore": "fake_vectorstore", "config": {"name": "fake_tool_instance", "database": database, "description": "fake tool"}}
    )
    assert tool
