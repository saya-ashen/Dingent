import React, { useState } from 'react';
import { 
  Layout,
  Menu,
  Typography,
  Button,
  Space,
  theme
} from 'antd';
import { 
  DashboardOutlined, 
  RobotOutlined, 
  PluginOutlined, 
  SettingOutlined, 
  FileTextOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined
} from '@ant-design/icons';
import Link from 'next/link';
import { useRouter } from 'next/router';

const { Header, Sider, Content } = Layout;
const { Title } = Typography;

interface AppLayoutProps {
  children: React.ReactNode;
}

const AppLayout: React.FC<AppLayoutProps> = ({ children }) => {
  const [collapsed, setCollapsed] = useState(false);
  const router = useRouter();
  const { token } = theme.useToken();

  const menuItems = [
    {
      key: '/',
      icon: <DashboardOutlined />,
      label: <Link href="/">Dashboard</Link>,
    },
    {
      key: '/assistants',
      icon: <RobotOutlined />,
      label: <Link href="/assistants">Assistants</Link>,
    },
    {
      key: '/plugins',
      icon: <PluginOutlined />,
      label: <Link href="/plugins">Plugins</Link>,
    },
    {
      key: '/settings',
      icon: <SettingOutlined />,
      label: <Link href="/settings">Settings</Link>,
    },
    {
      key: '/logs',
      icon: <FileTextOutlined />,
      label: <Link href="/logs">Logs</Link>,
    },
  ];

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider 
        trigger={null} 
        collapsible 
        collapsed={collapsed}
        style={{
          background: token.colorBgContainer,
        }}
      >
        <div style={{ 
          height: 32, 
          margin: 16, 
          display: 'flex', 
          alignItems: 'center',
          justifyContent: collapsed ? 'center' : 'flex-start'
        }}>
          <span style={{ fontSize: 20 }}>🤖</span>
          {!collapsed && (
            <Title level={4} style={{ margin: '0 0 0 8px', color: token.colorText }}>
              Dingent
            </Title>
          )}
        </div>
        <Menu
          theme="light"
          mode="inline"
          selectedKeys={[router.pathname]}
          items={menuItems}
          style={{ borderRight: 0 }}
        />
      </Sider>
      <Layout>
        <Header style={{ 
          padding: '0 16px', 
          background: token.colorBgContainer,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          borderBottom: `1px solid ${token.colorBorder}`
        }}>
          <Button
            type="text"
            icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
            onClick={() => setCollapsed(!collapsed)}
            style={{
              fontSize: '16px',
              width: 64,
              height: 64,
            }}
          />
          <Space>
            <Title level={4} style={{ margin: 0 }}>Admin Dashboard</Title>
          </Space>
        </Header>
        <Content style={{ 
          margin: '24px 16px',
          padding: 24,
          minHeight: 280,
          background: token.colorBgContainer,
          borderRadius: token.borderRadiusLG,
        }}>
          {children}
        </Content>
      </Layout>
    </Layout>
  );
};

export default AppLayout;