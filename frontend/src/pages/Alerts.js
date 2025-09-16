import React, { useState } from 'react';
import { Card, Table, Row, Col, Button, Form, Input, Select, Switch, Tag, Modal, notification } from 'antd';
import { BellOutlined, PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons';

const { Option } = Select;

const Alerts = () => {
  const [alerts, setAlerts] = useState([
    {
      key: '1',
      name: 'Portfolio Loss Limit',
      type: 'portfolio',
      condition: 'Daily Loss > $1000',
      status: 'active',
      triggered: false,
      lastTriggered: null,
      notifications: ['email', 'slack']
    },
    {
      key: '2',
      name: 'AAPL Price Alert',
      type: 'price',
      condition: 'AAPL > $160',
      status: 'active',
      triggered: true,
      lastTriggered: '2024-01-15 10:30:00',
      notifications: ['email']
    },
    {
      key: '3',
      name: 'High IV Alert',
      type: 'volatility',
      condition: 'IV Rank > 80%',
      status: 'inactive',
      triggered: false,
      lastTriggered: null,
      notifications: ['telegram']
    },
    {
      key: '4',
      name: 'Options Expiry',
      type: 'expiry',
      condition: 'Options expire in 3 days',
      status: 'active',
      triggered: true,
      lastTriggered: '2024-01-14 09:00:00',
      notifications: ['email', 'slack']
    }
  ]);

  const [isModalVisible, setIsModalVisible] = useState(false);
  const [editingAlert, setEditingAlert] = useState(null);
  const [form] = Form.useForm();

  const columns = [
    {
      title: 'Alert Name',
      dataIndex: 'name',
      key: 'name',
      render: (text) => <strong>{text}</strong>
    },
    {
      title: 'Type',
      dataIndex: 'type',
      key: 'type',
      render: (type) => {
        const colors = {
          portfolio: 'blue',
          price: 'green',
          volatility: 'orange',
          expiry: 'red'
        };
        return <Tag color={colors[type]}>{type.toUpperCase()}</Tag>;
      }
    },
    {
      title: 'Condition',
      dataIndex: 'condition',
      key: 'condition'
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status) => (
        <Tag color={status === 'active' ? 'green' : 'default'}>
          {status.toUpperCase()}
        </Tag>
      )
    },
    {
      title: 'Triggered',
      dataIndex: 'triggered',
      key: 'triggered',
      render: (triggered, record) => (
        <div>
          <Tag color={triggered ? 'red' : 'green'}>
            {triggered ? 'YES' : 'NO'}
          </Tag>
          {record.lastTriggered && (
            <div style={{ fontSize: '12px', color: '#666' }}>
              Last: {record.lastTriggered}
            </div>
          )}
        </div>
      )
    },
    {
      title: 'Notifications',
      dataIndex: 'notifications',
      key: 'notifications',
      render: (notifications) => (
        <div>
          {notifications.map(notif => (
            <Tag key={notif} size="small">{notif}</Tag>
          ))}
        </div>
      )
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_, record) => (
        <div>
          <Button 
            type="link" 
            icon={<EditOutlined />} 
            onClick={() => handleEdit(record)}
          />
          <Button 
            type="link" 
            danger 
            icon={<DeleteOutlined />} 
            onClick={() => handleDelete(record.key)}
          />
        </div>
      )
    }
  ];

  const handleEdit = (alert) => {
    setEditingAlert(alert);
    form.setFieldsValue(alert);
    setIsModalVisible(true);
  };

  const handleDelete = (key) => {
    setAlerts(alerts.filter(alert => alert.key !== key));
    notification.success({
      message: 'Alert Deleted',
      description: 'Alert has been successfully deleted.'
    });
  };

  const handleAdd = () => {
    setEditingAlert(null);
    form.resetFields();
    setIsModalVisible(true);
  };

  const handleModalOk = () => {
    form.validateFields().then(values => {
      if (editingAlert) {
        // Update existing alert
        setAlerts(alerts.map(alert => 
          alert.key === editingAlert.key 
            ? { ...alert, ...values }
            : alert
        ));
        notification.success({
          message: 'Alert Updated',
          description: 'Alert has been successfully updated.'
        });
      } else {
        // Add new alert
        const newAlert = {
          key: Date.now().toString(),
          ...values,
          triggered: false,
          lastTriggered: null
        };
        setAlerts([...alerts, newAlert]);
        notification.success({
          message: 'Alert Created',
          description: 'New alert has been successfully created.'
        });
      }
      setIsModalVisible(false);
    });
  };

  const handleModalCancel = () => {
    setIsModalVisible(false);
  };

  const activeAlerts = alerts.filter(alert => alert.status === 'active').length;
  const triggeredAlerts = alerts.filter(alert => alert.triggered).length;

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 28, fontWeight: 600, color: '#1890ff', margin: 0 }}>
          Alert Management
        </h1>
        <p style={{ color: '#666', margin: '8px 0 0 0' }}>
          Configure and manage trading alerts and notifications
        </p>
      </div>

      {/* Alert Summary */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={8}>
          <Card>
            <div style={{ display: 'flex', alignItems: 'center' }}>
              <BellOutlined style={{ fontSize: 24, color: '#1890ff', marginRight: 12 }} />
              <div>
                <div style={{ fontSize: 24, fontWeight: 'bold' }}>{alerts.length}</div>
                <div style={{ color: '#666' }}>Total Alerts</div>
              </div>
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card>
            <div style={{ display: 'flex', alignItems: 'center' }}>
              <div style={{ 
                width: 24, 
                height: 24, 
                borderRadius: '50%', 
                backgroundColor: '#52c41a',
                marginRight: 12
              }} />
              <div>
                <div style={{ fontSize: 24, fontWeight: 'bold' }}>{activeAlerts}</div>
                <div style={{ color: '#666' }}>Active Alerts</div>
              </div>
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card>
            <div style={{ display: 'flex', alignItems: 'center' }}>
              <div style={{ 
                width: 24, 
                height: 24, 
                borderRadius: '50%', 
                backgroundColor: '#ff4d4f',
                marginRight: 12
              }} />
              <div>
                <div style={{ fontSize: 24, fontWeight: 'bold' }}>{triggeredAlerts}</div>
                <div style={{ color: '#666' }}>Triggered Today</div>
              </div>
            </div>
          </Card>
        </Col>
      </Row>

      {/* Alerts Table */}
      <Card 
        title="Alert Configuration" 
        extra={
          <Button 
            type="primary" 
            icon={<PlusOutlined />} 
            onClick={handleAdd}
          >
            Add Alert
          </Button>
        }
      >
        <Table
          columns={columns}
          dataSource={alerts}
          pagination={false}
          scroll={{ x: 800 }}
        />
      </Card>

      {/* Add/Edit Alert Modal */}
      <Modal
        title={editingAlert ? 'Edit Alert' : 'Add New Alert'}
        visible={isModalVisible}
        onOk={handleModalOk}
        onCancel={handleModalCancel}
        width={600}
      >
        <Form
          form={form}
          layout="vertical"
          initialValues={{
            status: 'active',
            notifications: ['email']
          }}
        >
          <Form.Item
            name="name"
            label="Alert Name"
            rules={[{ required: true, message: 'Please enter alert name' }]}
          >
            <Input placeholder="Enter alert name" />
          </Form.Item>

          <Form.Item
            name="type"
            label="Alert Type"
            rules={[{ required: true, message: 'Please select alert type' }]}
          >
            <Select placeholder="Select alert type">
              <Option value="portfolio">Portfolio</Option>
              <Option value="price">Price</Option>
              <Option value="volatility">Volatility</Option>
              <Option value="expiry">Expiry</Option>
            </Select>
          </Form.Item>

          <Form.Item
            name="condition"
            label="Condition"
            rules={[{ required: true, message: 'Please enter condition' }]}
          >
            <Input placeholder="e.g., AAPL > $160" />
          </Form.Item>

          <Form.Item
            name="status"
            label="Status"
            valuePropName="checked"
          >
            <Switch 
              checkedChildren="Active" 
              unCheckedChildren="Inactive"
              checked={form.getFieldValue('status') === 'active'}
              onChange={(checked) => form.setFieldsValue({ status: checked ? 'active' : 'inactive' })}
            />
          </Form.Item>

          <Form.Item
            name="notifications"
            label="Notification Channels"
            rules={[{ required: true, message: 'Please select notification channels' }]}
          >
            <Select mode="multiple" placeholder="Select notification channels">
              <Option value="email">Email</Option>
              <Option value="slack">Slack</Option>
              <Option value="telegram">Telegram</Option>
            </Select>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default Alerts;
