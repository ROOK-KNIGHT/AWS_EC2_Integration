import React, { useState, useEffect } from 'react';
import { Card, Row, Col, Statistic, Alert, Button, Input, Space } from 'antd';
import { ArrowUpOutlined, ArrowDownOutlined } from '@ant-design/icons';

const Dashboard = () => {
  const [metrics, setMetrics] = useState({
    totalValue: 125000,
    dailyPnL: 2500,
    totalPnL: 15000,
    positions: 8,
    sharpeRatio: 1.85,
    maxDrawdown: -5.2
  });

  const [symbol, setSymbol] = useState('');
  const [quantity, setQuantity] = useState('');

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 28, fontWeight: 600, color: '#1890ff', margin: 0 }}>
          Trading Dashboard
        </h1>
        <p style={{ color: '#666', margin: '8px 0 0 0' }}>
          Real-time portfolio monitoring and analytics
        </p>
      </div>

      {/* Metrics Overview */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="Total Portfolio Value"
              value={metrics.totalValue}
              precision={0}
              valueStyle={{ color: '#1890ff' }}
              prefix="$"
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="Daily P&L"
              value={metrics.dailyPnL}
              precision={0}
              valueStyle={{ color: '#52c41a' }}
              prefix={<ArrowUpOutlined />}
              suffix="$"
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="Total P&L"
              value={metrics.totalPnL}
              precision={0}
              valueStyle={{ color: '#52c41a' }}
              prefix={<ArrowUpOutlined />}
              suffix="$"
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="Active Positions"
              value={metrics.positions}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
      </Row>

      {/* Additional Metrics */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="Sharpe Ratio"
              value={metrics.sharpeRatio}
              precision={2}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="Max Drawdown"
              value={Math.abs(metrics.maxDrawdown)}
              precision={1}
              valueStyle={{ color: '#ff4d4f' }}
              prefix={<ArrowDownOutlined />}
              suffix="%"
            />
          </Card>
        </Col>
      </Row>

      {/* Dashboard Content */}
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <Card title="Portfolio Performance" style={{ height: 350 }}>
            <div style={{ 
              height: 250, 
              display: 'flex', 
              alignItems: 'center', 
              justifyContent: 'center',
              backgroundColor: '#f5f5f5',
              borderRadius: 8
            }}>
              <p style={{ color: '#666', fontSize: 16 }}>
                Chart visualization will be displayed here
              </p>
            </div>
          </Card>
        </Col>
        
        <Col xs={24} lg={12}>
          <Card title="Recent Alerts" style={{ height: 350 }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <Alert
                message="Portfolio Alert"
                description="Daily profit target reached: +$2,500"
                type="success"
                showIcon
              />
              <Alert
                message="Options Alert"
                description="High IV detected in AAPL options"
                type="info"
                showIcon
              />
              <Alert
                message="Risk Alert"
                description="Position size exceeds 5% of portfolio"
                type="warning"
                showIcon
              />
            </div>
          </Card>
        </Col>
      </Row>

      {/* Trading Interface */}
      <Card title="Quick Trade" style={{ marginTop: 16 }}>
        <Row gutter={[16, 16]} align="bottom">
          <Col xs={24} sm={8}>
            <div>
              <label style={{ display: 'block', marginBottom: 8, fontWeight: 500 }}>
                Symbol
              </label>
              <Input
                placeholder="Enter symbol (e.g., AAPL)"
                value={symbol}
                onChange={(e) => setSymbol(e.target.value)}
                size="large"
              />
            </div>
          </Col>
          <Col xs={24} sm={8}>
            <div>
              <label style={{ display: 'block', marginBottom: 8, fontWeight: 500 }}>
                Quantity
              </label>
              <Input
                type="number"
                placeholder="Enter quantity"
                value={quantity}
                onChange={(e) => setQuantity(e.target.value)}
                size="large"
              />
            </div>
          </Col>
          <Col xs={24} sm={8}>
            <Space>
              <Button type="primary" size="large" style={{ backgroundColor: '#52c41a', borderColor: '#52c41a' }}>
                Buy
              </Button>
              <Button type="primary" size="large" danger>
                Sell
              </Button>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* Status */}
      <div style={{ textAlign: 'center', marginTop: 24, color: '#666' }}>
        <p>✅ Trading Dashboard Successfully Deployed</p>
        <p>🚀 Ready for Schwab API Integration</p>
      </div>
    </div>
  );
};

export default Dashboard;
