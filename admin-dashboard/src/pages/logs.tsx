import React, { useState } from 'react';
import { 
  Card, 
  Table, 
  Button, 
  Space, 
  Typography, 
  Tag, 
  Input, 
  Select, 
  Modal, 
  message,
  Row,
  Col,
  Statistic
} from 'antd';
import { 
  ReloadOutlined, 
  ClearOutlined, 
  SearchOutlined,
  EyeOutlined 
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import useSWR from 'swr';
import { logsAPI } from '@/services/api';
import { LogEntry, LogStatistics } from '@/types';
import { formatTimestamp, getStatusTextColor } from '@/utils/helpers';

const { Title, Text } = Typography;
const { Search } = Input;
const { Option } = Select;
const { confirm } = Modal;

const LogsPage: React.FC = () => {
  const [filters, setFilters] = useState({
    level: undefined as string | undefined,
    module: undefined as string | undefined,
    search: undefined as string | undefined,
    limit: 100
  });

  const { data: logs, error: logsError, mutate: mutateLogs } = useSWR(
    ['/logs', filters], 
    () => logsAPI.get(filters)
  );
  
  const { data: logStats, mutate: mutateStats } = useSWR('/logs/statistics', logsAPI.getStatistics);

  const handleRefresh = async () => {
    await Promise.all([mutateLogs(), mutateStats()]);
    message.success('Logs refreshed!');
  };

  const handleClearLogs = () => {
    confirm({
      title: 'Clear All Logs',
      content: 'Are you sure you want to clear all logs? This action cannot be undone.',
      okText: 'Clear All',
      okType: 'danger',
      cancelText: 'Cancel',
      onOk: async () => {
        try {
          const success = await logsAPI.clearAll();
          if (success) {
            message.success('All logs cleared successfully');
            await Promise.all([mutateLogs(), mutateStats()]);
          } else {
            message.error('Failed to clear logs');
          }
        } catch (error) {
          message.error('Failed to clear logs');
        }
      },
    });
  };

  const showLogDetails = (log: LogEntry) => {
    Modal.info({
      title: 'Log Details',
      width: 800,
      content: (
        <div style={{ marginTop: 16 }}>
          <div style={{ marginBottom: 16 }}>
            <Tag color={getLogLevelColor(log.level)}>{log.level}</Tag>
            <Text type="secondary">{formatTimestamp(log.timestamp)}</Text>
          </div>
          
          <div style={{ marginBottom: 16 }}>
            <Text strong>Module: </Text>
            <Text code>{log.module}</Text>
          </div>
          
          <div style={{ marginBottom: 16 }}>
            <Text strong>Function: </Text>
            <Text code>{log.function}</Text>
          </div>
          
          <div style={{ marginBottom: 16 }}>
            <Text strong>Message:</Text>
            <div style={{ 
              marginTop: 8, 
              padding: 12, 
              background: '#f5f5f5', 
              borderRadius: 4,
              fontFamily: 'monospace',
              whiteSpace: 'pre-wrap'
            }}>
              {log.message}
            </div>
          </div>

          {log.context && Object.keys(log.context).length > 0 && (
            <div style={{ marginBottom: 16 }}>
              <Text strong>Context:</Text>
              <div style={{ 
                marginTop: 8, 
                padding: 12, 
                background: '#f5f5f5', 
                borderRadius: 4,
                fontFamily: 'monospace',
                whiteSpace: 'pre-wrap'
              }}>
                {JSON.stringify(log.context, null, 2)}
              </div>
            </div>
          )}

          {log.correlation_id && (
            <div>
              <Text strong>Correlation ID: </Text>
              <Text code>{log.correlation_id}</Text>
            </div>
          )}
        </div>
      ),
    });
  };

  const getLogLevelColor = (level: string): string => {
    switch (level.toLowerCase()) {
      case 'error': return 'red';
      case 'warning': case 'warn': return 'orange';
      case 'info': return 'blue';
      case 'debug': return 'green';
      default: return 'default';
    }
  };

  const handleFilterChange = (field: string, value: any) => {
    setFilters(prev => ({ ...prev, [field]: value }));
  };

  const columns: ColumnsType<LogEntry> = [
    {
      title: 'Level',
      dataIndex: 'level',
      key: 'level',
      width: 80,
      render: (level) => (
        <Tag color={getLogLevelColor(level)}>{level}</Tag>
      ),
      filters: [
        { text: 'ERROR', value: 'ERROR' },
        { text: 'WARNING', value: 'WARNING' },
        { text: 'INFO', value: 'INFO' },
        { text: 'DEBUG', value: 'DEBUG' },
      ],
      onFilter: (value, record) => record.level === value,
    },
    {
      title: 'Timestamp',
      dataIndex: 'timestamp',
      key: 'timestamp',
      width: 180,
      render: (timestamp) => (
        <Text style={{ fontSize: '12px' }}>{formatTimestamp(timestamp)}</Text>
      ),
      sorter: (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime(),
      defaultSortOrder: 'descend',
    },
    {
      title: 'Module',
      dataIndex: 'module',
      key: 'module',
      width: 120,
      render: (module) => <Text code style={{ fontSize: '12px' }}>{module}</Text>,
    },
    {
      title: 'Function',
      dataIndex: 'function',
      key: 'function',
      width: 120,
      render: (func) => <Text code style={{ fontSize: '12px' }}>{func}</Text>,
    },
    {
      title: 'Message',
      dataIndex: 'message',
      key: 'message',
      ellipsis: true,
      render: (message) => (
        <Text style={{ fontSize: '12px' }}>{message}</Text>
      ),
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 100,
      render: (_, record) => (
        <Button
          type="text"
          icon={<EyeOutlined />}
          onClick={() => showLogDetails(record)}
        >
          Details
        </Button>
      ),
    },
  ];

  if (logsError) {
    return (
      <Card>
        <div style={{ textAlign: 'center', padding: '40px 0' }}>
          <Text type="danger">Failed to load logs. Please check the backend connection.</Text>
        </div>
      </Card>
    );
  }

  return (
    <div>
      <div style={{ marginBottom: 24, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Title level={2}>📋 System Logs</Title>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={handleRefresh}>
            Refresh
          </Button>
          <Button 
            danger 
            icon={<ClearOutlined />} 
            onClick={handleClearLogs}
          >
            Clear All
          </Button>
        </Space>
      </div>

      {/* Statistics Cards */}
      {logStats && (
        <Row gutter={16} style={{ marginBottom: 24 }}>
          <Col span={6}>
            <Card>
              <Statistic
                title="Total Logs"
                value={logStats.total}
                valueStyle={{ color: '#1890ff' }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="Errors"
                value={logStats.by_level?.ERROR || 0}
                valueStyle={{ color: '#ff4d4f' }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="Warnings"
                value={logStats.by_level?.WARNING || 0}
                valueStyle={{ color: '#faad14' }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="Info"
                value={logStats.by_level?.INFO || 0}
                valueStyle={{ color: '#52c41a' }}
              />
            </Card>
          </Col>
        </Row>
      )}

      <Card>
        {/* Filters */}
        <div style={{ marginBottom: 16 }}>
          <Row gutter={16}>
            <Col xs={24} sm={8}>
              <Search
                placeholder="Search logs..."
                allowClear
                onSearch={(value) => handleFilterChange('search', value || undefined)}
                style={{ width: '100%' }}
              />
            </Col>
            <Col xs={24} sm={4}>
              <Select
                placeholder="Level"
                allowClear
                style={{ width: '100%' }}
                onChange={(value) => handleFilterChange('level', value)}
              >
                <Option value="ERROR">Error</Option>
                <Option value="WARNING">Warning</Option>
                <Option value="INFO">Info</Option>
                <Option value="DEBUG">Debug</Option>
              </Select>
            </Col>
            <Col xs={24} sm={4}>
              <Select
                placeholder="Module"
                allowClear
                style={{ width: '100%' }}
                onChange={(value) => handleFilterChange('module', value)}
              >
                {logStats?.by_module && Object.keys(logStats.by_module).map(module => (
                  <Option key={module} value={module}>{module}</Option>
                ))}
              </Select>
            </Col>
            <Col xs={24} sm={4}>
              <Select
                placeholder="Limit"
                value={filters.limit}
                style={{ width: '100%' }}
                onChange={(value) => handleFilterChange('limit', value)}
              >
                <Option value={50}>50 logs</Option>
                <Option value={100}>100 logs</Option>
                <Option value={500}>500 logs</Option>
                <Option value={1000}>1000 logs</Option>
              </Select>
            </Col>
          </Row>
        </div>

        <Table
          columns={columns}
          dataSource={logs || []}
          rowKey={(record, index) => `${record.timestamp}-${index}`}
          loading={!logs && !logsError}
          pagination={{
            pageSize: 20,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total, range) =>
              `${range[0]}-${range[1]} of ${total} logs`,
          }}
          scroll={{ x: 1000 }}
          size="small"
        />
      </Card>
    </div>
  );
};

export default LogsPage;