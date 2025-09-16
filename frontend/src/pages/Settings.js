import React, { useState } from 'react';
import { Card, Form, Input, Button, Switch, Select, Row, Col, Divider, notification, Tabs } from 'antd';
import { SaveOutlined, ApiOutlined, KeyOutlined } from '@ant-design/icons';

const { Option } = Select;
const { TabPane } = Tabs;

const Settings = () => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);

  const handleSave = async (values) => {
    setLoading(true);
    try {
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 1000));
      notification.success({
        message: 'Settings Saved',
        description: 'Your settings have been successfully updated.'
      });
    } catch (error) {
      notification.error({
        message: 'Save Failed',
        description: 'Failed to save settings. Please try again.'
      });
    } finally {
      setLoading(false);
    }
  };

  const handleTestConnection = async () => {
    notification.info({
      message: 'Testing Connection',
      description: 'Testing Schwab API connection...'
    });
    
    // Simulate test
    setTimeout(() => {
      notification.success({
        message: 'Connection Successful',
        description: 'Successfully connected to Schwab API.'
      });
    }, 2000);
  };

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 28, fontWeight: 600, color: '#1890ff', margin: 0 }}>
          Settings
        </h1>
        <p style={{ color: '#666', margin: '8px 0 0 0' }}>
          Configure your trading dashboard preferences and integrations
        </p>
      </div>

      <Tabs defaultActiveKey="1">
        <TabPane tab="API Configuration" key="1">
          <Card title="Schwab API Settings" extra={<KeyOutlined />}>
            <Form
              form={form}
              layout="vertical"
              onFinish={handleSave}
              initialValues={{
                apiEnabled: true,
                autoRefresh: true,
                refreshInterval: 30,
                paperTrading: false
              }}
            >
              <Row gutter={[16, 16]}>
                <Col xs={24} md={12}>
                  <Form.Item
                    name="clientId"
                    label="Client ID"
                    rules={[{ required: true, message: 'Please enter your Client ID' }]}
                  >
                    <Input placeholder="Enter Schwab Client ID" />
                  </Form.Item>
                </Col>
                <Col xs={24} md={12}>
                  <Form.Item
                    name="clientSecret"
                    label="Client Secret"
                    rules={[{ required: true, message: 'Please enter your Client Secret' }]}
                  >
                    <Input.Password placeholder="Enter Schwab Client Secret" />
                  </Form.Item>
                </Col>
              </Row>

              <Row gutter={[16, 16]}>
                <Col xs={24} md={12}>
                  <Form.Item
                    name="redirectUri"
                    label="Redirect URI"
                    rules={[{ required: true, message: 'Please enter your Redirect URI' }]}
                  >
                    <Input placeholder="https://your-domain.com/callback" />
                  </Form.Item>
                </Col>
                <Col xs={24} md={12}>
                  <Form.Item
                    name="refreshInterval"
                    label="Data Refresh Interval (seconds)"
                  >
                    <Select>
                      <Option value={15}>15 seconds</Option>
                      <Option value={30}>30 seconds</Option>
                      <Option value={60}>1 minute</Option>
                      <Option value={300}>5 minutes</Option>
                    </Select>
                  </Form.Item>
                </Col>
              </Row>

              <Row gutter={[16, 16]}>
                <Col xs={24} md={8}>
                  <Form.Item
                    name="apiEnabled"
                    label="Enable API"
                    valuePropName="checked"
                  >
                    <Switch />
                  </Form.Item>
                </Col>
                <Col xs={24} md={8}>
                  <Form.Item
                    name="autoRefresh"
                    label="Auto Refresh Data"
                    valuePropName="checked"
                  >
                    <Switch />
                  </Form.Item>
                </Col>
                <Col xs={24} md={8}>
                  <Form.Item
                    name="paperTrading"
                    label="Paper Trading Mode"
                    valuePropName="checked"
                  >
                    <Switch />
                  </Form.Item>
                </Col>
              </Row>

              <div style={{ marginTop: 24 }}>
                <Button 
                  type="primary" 
                  htmlType="submit" 
                  loading={loading}
                  icon={<SaveOutlined />}
                  style={{ marginRight: 8 }}
                >
                  Save Settings
                </Button>
                <Button 
                  type="default" 
                  onClick={handleTestConnection}
                  icon={<ApiOutlined />}
                >
                  Test Connection
                </Button>
              </div>
            </Form>
          </Card>
        </TabPane>

        <TabPane tab="Notifications" key="2">
          <Card title="Notification Settings">
            <Form layout="vertical" initialValues={{
              emailEnabled: true,
              slackEnabled: false,
              telegramEnabled: false
            }}>
              <Row gutter={[16, 16]}>
                <Col xs={24} md={12}>
                  <Form.Item
                    name="emailAddress"
                    label="Email Address"
                  >
                    <Input placeholder="your-email@example.com" />
                  </Form.Item>
                </Col>
                <Col xs={24} md={12}>
                  <Form.Item
                    name="emailEnabled"
                    label="Enable Email Notifications"
                    valuePropName="checked"
                  >
                    <Switch />
                  </Form.Item>
                </Col>
              </Row>

              <Divider />

              <Row gutter={[16, 16]}>
                <Col xs={24} md={12}>
                  <Form.Item
                    name="slackWebhook"
                    label="Slack Webhook URL"
                  >
                    <Input placeholder="https://hooks.slack.com/services/..." />
                  </Form.Item>
                </Col>
                <Col xs={24} md={12}>
                  <Form.Item
                    name="slackEnabled"
                    label="Enable Slack Notifications"
                    valuePropName="checked"
                  >
                    <Switch />
                  </Form.Item>
                </Col>
              </Row>

              <Divider />

              <Row gutter={[16, 16]}>
                <Col xs={24} md={12}>
                  <Form.Item
                    name="telegramBotToken"
                    label="Telegram Bot Token"
                  >
                    <Input placeholder="123456789:ABCdefGHIjklMNOpqrsTUVwxyz" />
                  </Form.Item>
                </Col>
                <Col xs={24} md={12}>
                  <Form.Item
                    name="telegramChatId"
                    label="Telegram Chat ID"
                  >
                    <Input placeholder="123456789" />
                  </Form.Item>
                </Col>
              </Row>

              <Row gutter={[16, 16]}>
                <Col xs={24} md={12}>
                  <Form.Item
                    name="telegramEnabled"
                    label="Enable Telegram Notifications"
                    valuePropName="checked"
                  >
                    <Switch />
                  </Form.Item>
                </Col>
              </Row>

              <Button type="primary" icon={<SaveOutlined />}>
                Save Notification Settings
              </Button>
            </Form>
          </Card>
        </TabPane>

        <TabPane tab="Risk Management" key="3">
          <Card title="Risk Management Settings">
            <Form layout="vertical" initialValues={{
              maxDailyLoss: 1000,
              maxPositionSize: 10000,
              enableStopLoss: true,
              stopLossPercent: 5
            }}>
              <Row gutter={[16, 16]}>
                <Col xs={24} md={12}>
                  <Form.Item
                    name="maxDailyLoss"
                    label="Maximum Daily Loss ($)"
                  >
                    <Input type="number" placeholder="1000" />
                  </Form.Item>
                </Col>
                <Col xs={24} md={12}>
                  <Form.Item
                    name="maxPositionSize"
                    label="Maximum Position Size ($)"
                  >
                    <Input type="number" placeholder="10000" />
                  </Form.Item>
                </Col>
              </Row>

              <Row gutter={[16, 16]}>
                <Col xs={24} md={12}>
                  <Form.Item
                    name="stopLossPercent"
                    label="Stop Loss Percentage (%)"
                  >
                    <Input type="number" placeholder="5" />
                  </Form.Item>
                </Col>
                <Col xs={24} md={12}>
                  <Form.Item
                    name="enableStopLoss"
                    label="Enable Automatic Stop Loss"
                    valuePropName="checked"
                  >
                    <Switch />
                  </Form.Item>
                </Col>
              </Row>

              <Row gutter={[16, 16]}>
                <Col xs={24} md={12}>
                  <Form.Item
                    name="maxOptionsExposure"
                    label="Maximum Options Exposure ($)"
                  >
                    <Input type="number" placeholder="5000" />
                  </Form.Item>
                </Col>
                <Col xs={24} md={12}>
                  <Form.Item
                    name="enableRiskAlerts"
                    label="Enable Risk Alerts"
                    valuePropName="checked"
                  >
                    <Switch />
                  </Form.Item>
                </Col>
              </Row>

              <Button type="primary" icon={<SaveOutlined />}>
                Save Risk Settings
              </Button>
            </Form>
          </Card>
        </TabPane>

        <TabPane tab="Display" key="4">
          <Card title="Display Preferences">
            <Form layout="vertical" initialValues={{
              theme: 'light',
              currency: 'USD',
              timezone: 'America/New_York',
              showGreeks: true
            }}>
              <Row gutter={[16, 16]}>
                <Col xs={24} md={12}>
                  <Form.Item
                    name="theme"
                    label="Theme"
                  >
                    <Select>
                      <Option value="light">Light</Option>
                      <Option value="dark">Dark</Option>
                      <Option value="auto">Auto</Option>
                    </Select>
                  </Form.Item>
                </Col>
                <Col xs={24} md={12}>
                  <Form.Item
                    name="currency"
                    label="Currency"
                  >
                    <Select>
                      <Option value="USD">USD ($)</Option>
                      <Option value="EUR">EUR (€)</Option>
                      <Option value="GBP">GBP (£)</Option>
                    </Select>
                  </Form.Item>
                </Col>
              </Row>

              <Row gutter={[16, 16]}>
                <Col xs={24} md={12}>
                  <Form.Item
                    name="timezone"
                    label="Timezone"
                  >
                    <Select>
                      <Option value="America/New_York">Eastern Time</Option>
                      <Option value="America/Chicago">Central Time</Option>
                      <Option value="America/Denver">Mountain Time</Option>
                      <Option value="America/Los_Angeles">Pacific Time</Option>
                    </Select>
                  </Form.Item>
                </Col>
                <Col xs={24} md={12}>
                  <Form.Item
                    name="showGreeks"
                    label="Show Options Greeks"
                    valuePropName="checked"
                  >
                    <Switch />
                  </Form.Item>
                </Col>
              </Row>

              <Button type="primary" icon={<SaveOutlined />}>
                Save Display Settings
              </Button>
            </Form>
          </Card>
        </TabPane>
      </Tabs>
    </div>
  );
};

export default Settings;
