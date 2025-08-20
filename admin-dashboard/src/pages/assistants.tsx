import React, { useState } from 'react';
import { 
  Card, 
  Form, 
  Input, 
  Switch, 
  Button, 
  Space, 
  Divider, 
  Tag, 
  Select, 
  Modal, 
  message, 
  Row, 
  Col,
  Typography 
} from 'antd';
import { 
  PlusOutlined, 
  DeleteOutlined, 
  SaveOutlined,
  ReloadOutlined 
} from '@ant-design/icons';
import useSWR, { mutate } from 'swr';
import { assistantsAPI, pluginsAPI } from '@/services/api';
import { AssistantConfig, AvailablePlugin } from '@/types';
import { getEffectiveAssistantStatus, getStatusColor, safeBool, safeString } from '@/utils/helpers';

const { TextArea } = Input;
const { Option } = Select;
const { Title, Text } = Typography;

const AssistantsPage: React.FC = () => {
  const { data: assistants, error: assistantsError, mutate: mutateAssistants } = useSWR('/assistants', assistantsAPI.getAll);
  const { data: availablePlugins } = useSWR('/plugins', pluginsAPI.getAvailable);
  
  const [editingAssistants, setEditingAssistants] = useState<AssistantConfig[]>([]);
  const [addPluginModal, setAddPluginModal] = useState<{ visible: boolean; assistantIndex: number | null }>({
    visible: false,
    assistantIndex: null
  });
  const [selectedPlugin, setSelectedPlugin] = useState<string>('');

  // Initialize editing data when assistants load
  React.useEffect(() => {
    if (assistants) {
      setEditingAssistants(JSON.parse(JSON.stringify(assistants)));
    }
  }, [assistants]);

  const handleAssistantChange = (index: number, field: keyof AssistantConfig, value: any) => {
    const updated = [...editingAssistants];
    updated[index] = { ...updated[index], [field]: value };
    setEditingAssistants(updated);
  };

  const handlePluginToggle = (assistantIndex: number, pluginIndex: number, enabled: boolean) => {
    const updated = [...editingAssistants];
    updated[assistantIndex].plugins[pluginIndex].enabled = enabled;
    setEditingAssistants(updated);
  };

  const handleToolToggle = (assistantIndex: number, pluginIndex: number, toolIndex: number, enabled: boolean) => {
    const updated = [...editingAssistants];
    updated[assistantIndex].plugins[pluginIndex].tools[toolIndex].enabled = enabled;
    setEditingAssistants(updated);
  };

  const handleAddPlugin = async () => {
    if (addPluginModal.assistantIndex === null || !selectedPlugin) return;
    
    try {
      const assistantId = editingAssistants[addPluginModal.assistantIndex].id;
      const success = await assistantsAPI.addPlugin(assistantId, selectedPlugin);
      
      if (success) {
        message.success('Plugin added successfully');
        await mutateAssistants();
        setAddPluginModal({ visible: false, assistantIndex: null });
        setSelectedPlugin('');
      } else {
        message.error('Failed to add plugin');
      }
    } catch (error) {
      message.error('Failed to add plugin');
    }
  };

  const handleRemovePlugin = async (assistantIndex: number, pluginName: string) => {
    try {
      const assistantId = editingAssistants[assistantIndex].id;
      const success = await assistantsAPI.removePlugin(assistantId, pluginName);
      
      if (success) {
        message.success('Plugin removed successfully');
        await mutateAssistants();
      } else {
        message.error('Failed to remove plugin');
      }
    } catch (error) {
      message.error('Failed to remove plugin');
    }
  };

  const handleSave = async () => {
    try {
      message.loading({ content: 'Saving configuration...', key: 'save' });
      
      // Ensure boolean values are properly set
      const sanitized = editingAssistants.map(assistant => ({
        ...assistant,
        enabled: safeBool(assistant.enabled, false),
        plugins: assistant.plugins.map(plugin => ({
          ...plugin,
          enabled: safeBool(plugin.enabled, false),
          tools: plugin.tools.map(tool => ({
            ...tool,
            enabled: safeBool(tool.enabled, false)
          }))
        }))
      }));

      const success = await assistantsAPI.save(sanitized);
      
      if (success) {
        message.success({ content: 'Configuration saved successfully!', key: 'save' });
        await mutateAssistants();
      } else {
        message.error({ content: 'Failed to save configuration', key: 'save' });
      }
    } catch (error) {
      message.error({ content: 'Save failed. Please try again.', key: 'save' });
    }
  };

  const handleRefresh = async () => {
    await mutateAssistants();
    message.success('Configuration refreshed!');
  };

  if (assistantsError) {
    return (
      <Card>
        <div style={{ textAlign: 'center', padding: '40px 0' }}>
          <Text type="danger">Failed to load assistants configuration. Please check the backend connection.</Text>
        </div>
      </Card>
    );
  }

  if (!editingAssistants.length) {
    return (
      <Card>
        <div style={{ textAlign: 'center', padding: '40px 0' }}>
          <Text>Loading assistants configuration...</Text>
        </div>
      </Card>
    );
  }

  return (
    <div>
      <div style={{ marginBottom: 24, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Title level={2}>🤖 Assistant Configuration</Title>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={handleRefresh}>
            Refresh
          </Button>
          <Button type="primary" icon={<SaveOutlined />} onClick={handleSave}>
            Save All Changes
          </Button>
        </Space>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
        {editingAssistants.map((assistant, assistantIndex) => {
          const [statusLevel, statusLabel] = getEffectiveAssistantStatus(assistant.status, assistant.enabled);
          
          return (
            <Card 
              key={assistant.id} 
              title={`Assistant ${assistantIndex + 1}`}
              extra={
                <Tag color={getStatusColor(statusLevel)}>
                  {statusLabel}
                </Tag>
              }
            >
              <Row gutter={16}>
                <Col xs={24} md={8}>
                  <Form.Item label="Assistant Name">
                    <Input
                      value={safeString(assistant.name)}
                      onChange={(e) => handleAssistantChange(assistantIndex, 'name', e.target.value)}
                      placeholder="Enter assistant name"
                    />
                  </Form.Item>
                </Col>
                <Col xs={24} md={8}>
                  <Form.Item label="Enable Assistant">
                    <Switch
                      checked={safeBool(assistant.enabled, false)}
                      onChange={(checked) => handleAssistantChange(assistantIndex, 'enabled', checked)}
                    />
                  </Form.Item>
                </Col>
                <Col xs={24} md={8}>
                  <Form.Item label="Service Status">
                    <Tag color={getStatusColor(statusLevel)}>
                      {statusLabel}
                    </Tag>
                  </Form.Item>
                </Col>
              </Row>

              <Form.Item label="Assistant Description">
                <TextArea
                  value={safeString(assistant.description)}
                  onChange={(e) => handleAssistantChange(assistantIndex, 'description', e.target.value)}
                  placeholder="Enter assistant description"
                  rows={3}
                />
              </Form.Item>

              <Divider />
              
              <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Title level={4}>🔌 Plugin Configuration</Title>
                <Button 
                  type="primary" 
                  icon={<PlusOutlined />}
                  onClick={() => setAddPluginModal({ visible: true, assistantIndex })}
                >
                  Add Plugin
                </Button>
              </div>

              {assistant.plugins.map((plugin, pluginIndex) => (
                <Card 
                  key={plugin.name} 
                  size="small" 
                  style={{ marginBottom: 16 }}
                  title={plugin.name}
                  extra={
                    <Space>
                      <Switch
                        checked={safeBool(plugin.enabled, false)}
                        onChange={(checked) => handlePluginToggle(assistantIndex, pluginIndex, checked)}
                      />
                      <Button 
                        type="text" 
                        danger 
                        icon={<DeleteOutlined />}
                        onClick={() => handleRemovePlugin(assistantIndex, plugin.name)}
                      />
                    </Space>
                  }
                >
                  {plugin.tools && plugin.tools.length > 0 && (
                    <div>
                      <Text strong>Tools:</Text>
                      <div style={{ marginTop: 8 }}>
                        {plugin.tools.map((tool, toolIndex) => (
                          <div key={tool.name} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                            <Text>{tool.name}</Text>
                            <Switch
                              size="small"
                              checked={safeBool(tool.enabled, false)}
                              onChange={(checked) => handleToolToggle(assistantIndex, pluginIndex, toolIndex, checked)}
                            />
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </Card>
              ))}
            </Card>
          );
        })}
      </div>

      <Modal
        title="Add Plugin to Assistant"
        open={addPluginModal.visible}
        onOk={handleAddPlugin}
        onCancel={() => {
          setAddPluginModal({ visible: false, assistantIndex: null });
          setSelectedPlugin('');
        }}
        okButtonProps={{ disabled: !selectedPlugin }}
      >
        <Form.Item label="Select Plugin">
          <Select
            value={selectedPlugin}
            onChange={setSelectedPlugin}
            placeholder="Choose a plugin to add"
            style={{ width: '100%' }}
          >
            {availablePlugins?.map((plugin) => (
              <Option key={plugin.name} value={plugin.name}>
                <div>
                  <Text strong>{plugin.name}</Text>
                  <br />
                  <Text type="secondary" style={{ fontSize: '12px' }}>
                    {plugin.description}
                  </Text>
                </div>
              </Option>
            ))}
          </Select>
        </Form.Item>
      </Modal>
    </div>
  );
};

export default AssistantsPage;