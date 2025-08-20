import React from 'react';
import { 
  Card, 
  Table, 
  Button, 
  Space, 
  Typography, 
  Tag, 
  Modal, 
  message,
  Descriptions 
} from 'antd';
import { 
  DeleteOutlined, 
  ReloadOutlined, 
  InfoCircleOutlined 
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import useSWR from 'swr';
import { pluginsAPI } from '@/services/api';
import { AvailablePlugin } from '@/types';

const { Title, Text } = Typography;
const { confirm } = Modal;

const PluginsPage: React.FC = () => {
  const { data: availablePlugins, error: pluginsError, mutate: mutatePlugins } = useSWR('/plugins', pluginsAPI.getAvailable);

  const handleRefresh = async () => {
    await mutatePlugins();
    message.success('Plugin list refreshed!');
  };

  const handleDeletePlugin = (pluginName: string) => {
    confirm({
      title: 'Delete Plugin',
      content: `Are you sure you want to delete the plugin "${pluginName}"? This action cannot be undone.`,
      okText: 'Delete',
      okType: 'danger',
      cancelText: 'Cancel',
      onOk: async () => {
        try {
          const success = await pluginsAPI.remove(pluginName);
          if (success) {
            message.success(`Plugin "${pluginName}" deleted successfully`);
            await mutatePlugins();
          } else {
            message.error('Failed to delete plugin');
          }
        } catch (error) {
          message.error('Failed to delete plugin');
        }
      },
    });
  };

  const showPluginDetails = (plugin: AvailablePlugin) => {
    Modal.info({
      title: `Plugin: ${plugin.name}`,
      width: 600,
      content: (
        <div style={{ marginTop: 16 }}>
          <Descriptions column={1} bordered>
            <Descriptions.Item label="Name">{plugin.name}</Descriptions.Item>
            <Descriptions.Item label="Description">{plugin.description}</Descriptions.Item>
            <Descriptions.Item label="Tools">
              {plugin.tools && plugin.tools.length > 0 ? (
                <div>
                  {plugin.tools.map((tool, index) => (
                    <div key={index} style={{ marginBottom: 8 }}>
                      <Tag color="blue">{tool.name}</Tag>
                      {tool.description && (
                        <div style={{ marginTop: 4, fontSize: '12px', color: '#666' }}>
                          {tool.description}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <Text type="secondary">No tools available</Text>
              )}
            </Descriptions.Item>
          </Descriptions>
        </div>
      ),
    });
  };

  const columns: ColumnsType<AvailablePlugin> = [
    {
      title: 'Plugin Name',
      dataIndex: 'name',
      key: 'name',
      sorter: (a, b) => a.name.localeCompare(b.name),
      render: (name) => <Text strong>{name}</Text>,
    },
    {
      title: 'Description',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
      render: (description) => description || <Text type="secondary">No description</Text>,
    },
    {
      title: 'Tools',
      dataIndex: 'tools',
      key: 'tools',
      render: (tools) => (
        <div>
          {tools && tools.length > 0 ? (
            <div>
              <Text>{tools.length} tool{tools.length !== 1 ? 's' : ''}</Text>
              <div style={{ marginTop: 4 }}>
                {tools.slice(0, 3).map((tool: any, index: number) => (
                  <Tag key={index} size="small" color="blue">
                    {tool.name}
                  </Tag>
                ))}
                {tools.length > 3 && (
                  <Tag size="small" color="default">
                    +{tools.length - 3} more
                  </Tag>
                )}
              </div>
            </div>
          ) : (
            <Text type="secondary">No tools</Text>
          )}
        </div>
      ),
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 200,
      render: (_, record) => (
        <Space>
          <Button
            type="text"
            icon={<InfoCircleOutlined />}
            onClick={() => showPluginDetails(record)}
          >
            Details
          </Button>
          <Button
            type="text"
            danger
            icon={<DeleteOutlined />}
            onClick={() => handleDeletePlugin(record.name)}
          >
            Delete
          </Button>
        </Space>
      ),
    },
  ];

  if (pluginsError) {
    return (
      <Card>
        <div style={{ textAlign: 'center', padding: '40px 0' }}>
          <Text type="danger">Failed to load plugins. Please check the backend connection.</Text>
        </div>
      </Card>
    );
  }

  return (
    <div>
      <div style={{ marginBottom: 24, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Title level={2}>🔌 Plugin Management</Title>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={handleRefresh}>
            Refresh
          </Button>
        </Space>
      </div>

      <Card>
        <div style={{ marginBottom: 16 }}>
          <Text type="secondary">
            Manage available plugins in the system. You can view plugin details and remove plugins that are no longer needed.
          </Text>
        </div>

        <Table
          columns={columns}
          dataSource={availablePlugins || []}
          rowKey="name"
          loading={!availablePlugins && !pluginsError}
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total, range) =>
              `${range[0]}-${range[1]} of ${total} plugins`,
          }}
          scroll={{ x: 800 }}
        />
      </Card>
    </div>
  );
};

export default PluginsPage;