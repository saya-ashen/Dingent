import React, { useState, useEffect } from 'react';
import { 
  Card, 
  Form, 
  Input, 
  Button, 
  Space, 
  Typography, 
  message, 
  Switch, 
  InputNumber,
  Divider 
} from 'antd';
import { 
  SaveOutlined, 
  ReloadOutlined, 
  SettingOutlined 
} from '@ant-design/icons';
import useSWR from 'swr';
import { appSettingsAPI } from '@/services/api';
import { AppSettings } from '@/types';

const { Title, Text } = Typography;
const { TextArea } = Input;

const SettingsPage: React.FC = () => {
  const { data: appSettings, error: settingsError, mutate: mutateSettings } = useSWR('/app_settings', appSettingsAPI.get);
  const [form] = Form.useForm();
  const [editingSettings, setEditingSettings] = useState<AppSettings>({});

  // Initialize form when settings load
  useEffect(() => {
    if (appSettings) {
      setEditingSettings(appSettings);
      form.setFieldsValue(appSettings);
    }
  }, [appSettings, form]);

  const handleSave = async (values: AppSettings) => {
    try {
      message.loading({ content: 'Saving settings...', key: 'save' });
      const success = await appSettingsAPI.save(values);
      
      if (success) {
        message.success({ content: 'Settings saved successfully!', key: 'save' });
        await mutateSettings();
        setEditingSettings(values);
      } else {
        message.error({ content: 'Failed to save settings', key: 'save' });
      }
    } catch (error) {
      message.error({ content: 'Save failed. Please try again.', key: 'save' });
    }
  };

  const handleRefresh = async () => {
    await mutateSettings();
    message.success('Settings refreshed!');
  };

  const handleReset = () => {
    if (appSettings) {
      form.setFieldsValue(appSettings);
      setEditingSettings(appSettings);
      message.info('Form reset to saved values');
    }
  };

  if (settingsError) {
    return (
      <Card>
        <div style={{ textAlign: 'center', padding: '40px 0' }}>
          <Text type="danger">Failed to load app settings. Please check the backend connection.</Text>
        </div>
      </Card>
    );
  }

  if (!appSettings) {
    return (
      <Card>
        <div style={{ textAlign: 'center', padding: '40px 0' }}>
          <Text>Loading app settings...</Text>
        </div>
      </Card>
    );
  }

  return (
    <div>
      <div style={{ marginBottom: 24, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Title level={2}>⚙️ App Settings</Title>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={handleRefresh}>
            Refresh
          </Button>
        </Space>
      </div>

      <Card>
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSave}
          initialValues={appSettings}
        >
          <div style={{ marginBottom: 24 }}>
            <Text type="secondary">
              Configure core application settings. Changes will take effect after saving.
            </Text>
          </div>

          {/* Render form fields dynamically based on settings structure */}
          {Object.entries(editingSettings).map(([key, value]) => {
            if (typeof value === 'boolean') {
              return (
                <Form.Item
                  key={key}
                  name={key}
                  label={key.charAt(0).toUpperCase() + key.slice(1).replace(/_/g, ' ')}
                  valuePropName="checked"
                >
                  <Switch />
                </Form.Item>
              );
            } else if (typeof value === 'number') {
              return (
                <Form.Item
                  key={key}
                  name={key}
                  label={key.charAt(0).toUpperCase() + key.slice(1).replace(/_/g, ' ')}
                >
                  <InputNumber style={{ width: '100%' }} />
                </Form.Item>
              );
            } else if (typeof value === 'string') {
              // Use TextArea for longer text fields
              const isLongText = value.length > 100 || key.toLowerCase().includes('description') || key.toLowerCase().includes('config');
              
              return (
                <Form.Item
                  key={key}
                  name={key}
                  label={key.charAt(0).toUpperCase() + key.slice(1).replace(/_/g, ' ')}
                >
                  {isLongText ? (
                    <TextArea rows={4} />
                  ) : (
                    <Input />
                  )}
                </Form.Item>
              );
            } else if (typeof value === 'object' && value !== null) {
              return (
                <Form.Item
                  key={key}
                  name={key}
                  label={key.charAt(0).toUpperCase() + key.slice(1).replace(/_/g, ' ')}
                >
                  <TextArea 
                    rows={6}
                    placeholder="JSON configuration"
                    defaultValue={JSON.stringify(value, null, 2)}
                  />
                </Form.Item>
              );
            }
            return null;
          })}

          {/* If no settings are available, show a message */}
          {Object.keys(editingSettings).length === 0 && (
            <div style={{ textAlign: 'center', padding: '40px 0' }}>
              <SettingOutlined style={{ fontSize: 48, color: '#d9d9d9', marginBottom: 16 }} />
              <div>
                <Title level={4} type="secondary">No settings available</Title>
                <Text type="secondary">The application settings will appear here when available.</Text>
              </div>
            </div>
          )}

          <Divider />

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
            <Button onClick={handleReset}>
              Reset
            </Button>
            <Button type="primary" htmlType="submit" icon={<SaveOutlined />}>
              Save Settings
            </Button>
          </div>
        </Form>
      </Card>
    </div>
  );
};

export default SettingsPage;