import React from 'react';
import { Row, Col, Card, Statistic, Button, Space, message } from 'antd';
import { 
  RobotOutlined, 
  PluginOutlined, 
  ReloadOutlined, 
  SaveOutlined,
  WarningOutlined 
} from '@ant-design/icons';
import useSWR, { mutate } from 'swr';
import { assistantsAPI, pluginsAPI, logsAPI } from '@/services/api';
import { safeBool } from '@/utils/helpers';

const Dashboard: React.FC = () => {
  const { data: assistants, error: assistantsError } = useSWR('/assistants', assistantsAPI.getAll);
  const { data: availablePlugins, error: pluginsError } = useSWR('/plugins', pluginsAPI.getAvailable);
  const { data: logStats, error: logsError } = useSWR('/logs/statistics', logsAPI.getStatistics);

  const handleRefresh = async () => {
    message.loading({ content: 'Refreshing configuration...', key: 'refresh' });
    try {
      await Promise.all([
        mutate('/assistants'),
        mutate('/plugins'),
        mutate('/logs/statistics'),
      ]);
      message.success({ content: 'Configuration refreshed!', key: 'refresh' });
    } catch (error) {
      message.error({ content: 'Failed to refresh configuration', key: 'refresh' });
    }
  };

  const handleSaveAll = async () => {
    message.loading({ content: 'Saving all changes...', key: 'save' });
    try {
      if (assistants) {
        const success = await assistantsAPI.save(assistants);
        if (success) {
          message.success({ content: 'All changes saved successfully!', key: 'save' });
          await mutate('/assistants');
        } else {
          message.error({ content: 'Failed to save changes', key: 'save' });
        }
      }
    } catch (error) {
      message.error({ content: 'Save failed. Please try again.', key: 'save' });
    }
  };

  // Calculate statistics
  const enabledAssistants = assistants?.filter(a => safeBool(a.enabled)) || [];
  const totalPlugins = availablePlugins?.length || 0;
  const errorLogs = logStats?.by_level?.ERROR || 0;
  const warningLogs = logStats?.by_level?.WARNING || 0;

  const hasErrors = assistantsError || pluginsError || logsError;

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <h1>Admin Dashboard</h1>
        <Space>
          <Button 
            type="default" 
            icon={<ReloadOutlined />} 
            onClick={handleRefresh}
          >
            Refresh
          </Button>
          <Button 
            type="primary" 
            icon={<SaveOutlined />} 
            onClick={handleSaveAll}
          >
            Save All Changes
          </Button>
        </Space>
      </div>

      {hasErrors && (
        <Card style={{ marginBottom: 24, borderColor: '#ff4d4f' }}>
          <div style={{ display: 'flex', alignItems: 'center', color: '#ff4d4f' }}>
            <WarningOutlined style={{ marginRight: 8 }} />
            Failed to load complete configuration from the backend. Ensure the backend service is running, then click Refresh.
          </div>
        </Card>
      )}

      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="Active Assistants"
              value={enabledAssistants.length}
              suffix={`/ ${assistants?.length || 0}`}
              prefix={<RobotOutlined />}
              valueStyle={{ color: '#3f8600' }}
            />
          </Card>
        </Col>
        
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="Available Plugins"
              value={totalPlugins}
              prefix={<PluginOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="Error Logs"
              value={errorLogs}
              prefix={<WarningOutlined />}
              valueStyle={{ color: errorLogs > 0 ? '#cf1322' : '#3f8600' }}
            />
          </Card>
        </Col>
        
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="Warning Logs"
              value={warningLogs}
              prefix={<WarningOutlined />}
              valueStyle={{ color: warningLogs > 0 ? '#faad14' : '#3f8600' }}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 24 }}>
        <Col xs={24} lg={12}>
          <Card title="System Status" style={{ height: 300 }}>
            <div style={{ padding: '20px 0' }}>
              <div style={{ marginBottom: 16 }}>
                <strong>Backend Connection:</strong>{' '}
                <span style={{ color: hasErrors ? '#ff4d4f' : '#52c41a' }}>
                  {hasErrors ? 'Disconnected' : 'Connected'}
                </span>
              </div>
              <div style={{ marginBottom: 16 }}>
                <strong>Total Assistants:</strong> {assistants?.length || 0}
              </div>
              <div style={{ marginBottom: 16 }}>
                <strong>Total Logs:</strong> {logStats?.total || 0}
              </div>
            </div>
          </Card>
        </Col>
        
        <Col xs={24} lg={12}>
          <Card title="Quick Actions" style={{ height: 300 }}>
            <Space direction="vertical" style={{ width: '100%' }}>
              <Button block href="/assistants">
                Manage Assistants
              </Button>
              <Button block href="/plugins">
                Manage Plugins
              </Button>
              <Button block href="/settings">
                App Settings
              </Button>
              <Button block href="/logs">
                View System Logs
              </Button>
            </Space>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default Dashboard;