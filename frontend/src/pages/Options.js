import React, { useState } from 'react';
import { Card, Table, Row, Col, Statistic, Tag, Progress } from 'antd';
import { ArrowUpOutlined, ArrowDownOutlined } from '@ant-design/icons';

const Options = () => {
  const [optionsPositions] = useState([
    {
      key: '1',
      symbol: 'AAPL',
      strike: 155,
      expiry: '2024-01-19',
      type: 'CALL',
      quantity: 5,
      premium: 3.50,
      currentPrice: 4.20,
      delta: 0.65,
      gamma: 0.08,
      theta: -0.12,
      vega: 0.25,
      iv: 28.5,
      unrealizedPL: 350
    },
    {
      key: '2',
      symbol: 'MSFT',
      strike: 280,
      expiry: '2024-02-16',
      type: 'PUT',
      quantity: -3,
      premium: 5.80,
      currentPrice: 4.90,
      delta: -0.45,
      gamma: 0.06,
      theta: -0.08,
      vega: 0.18,
      iv: 22.3,
      unrealizedPL: 270
    },
    {
      key: '3',
      symbol: 'TSLA',
      strike: 240,
      expiry: '2024-01-26',
      type: 'CALL',
      quantity: 2,
      premium: 8.20,
      currentPrice: 6.50,
      delta: 0.72,
      gamma: 0.04,
      theta: -0.18,
      vega: 0.32,
      iv: 45.2,
      unrealizedPL: -340
    }
  ]);

  const columns = [
    {
      title: 'Symbol',
      dataIndex: 'symbol',
      key: 'symbol',
      render: (text) => <strong style={{ color: '#1890ff' }}>{text}</strong>
    },
    {
      title: 'Contract',
      key: 'contract',
      render: (_, record) => (
        <div>
          <div>{record.expiry}</div>
          <Tag color={record.type === 'CALL' ? 'green' : 'red'}>
            ${record.strike} {record.type}
          </Tag>
        </div>
      )
    },
    {
      title: 'Quantity',
      dataIndex: 'quantity',
      key: 'quantity',
      render: (value) => (
        <span style={{ color: value > 0 ? '#52c41a' : '#ff4d4f' }}>
          {value > 0 ? '+' : ''}{value}
        </span>
      )
    },
    {
      title: 'Premium',
      key: 'premium',
      render: (_, record) => (
        <div>
          <div>Paid: ${record.premium}</div>
          <div>Current: ${record.currentPrice}</div>
        </div>
      )
    },
    {
      title: 'Greeks',
      key: 'greeks',
      render: (_, record) => (
        <div style={{ fontSize: '12px' }}>
          <div>Δ: {record.delta.toFixed(2)}</div>
          <div>Γ: {record.gamma.toFixed(2)}</div>
          <div>Θ: {record.theta.toFixed(2)}</div>
          <div>ν: {record.vega.toFixed(2)}</div>
        </div>
      )
    },
    {
      title: 'IV',
      dataIndex: 'iv',
      key: 'iv',
      render: (value) => `${value}%`
    },
    {
      title: 'P&L',
      dataIndex: 'unrealizedPL',
      key: 'unrealizedPL',
      render: (value) => (
        <span style={{ color: value >= 0 ? '#52c41a' : '#ff4d4f' }}>
          {value >= 0 ? <ArrowUpOutlined /> : <ArrowDownOutlined />}
          ${Math.abs(value)}
        </span>
      )
    }
  ];

  const totalOptionsValue = optionsPositions.reduce((sum, pos) => 
    sum + (pos.currentPrice * Math.abs(pos.quantity) * 100), 0
  );
  const totalOptionsPL = optionsPositions.reduce((sum, pos) => sum + pos.unrealizedPL, 0);
  const totalDelta = optionsPositions.reduce((sum, pos) => 
    sum + (pos.delta * pos.quantity * 100), 0
  );
  const totalTheta = optionsPositions.reduce((sum, pos) => 
    sum + (pos.theta * Math.abs(pos.quantity) * 100), 0
  );

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 28, fontWeight: 600, color: '#1890ff', margin: 0 }}>
          Options Portfolio
        </h1>
        <p style={{ color: '#666', margin: '8px 0 0 0' }}>
          Options positions, Greeks, and risk metrics
        </p>
      </div>

      {/* Options Summary */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title="Total Options Value"
              value={totalOptionsValue}
              precision={0}
              valueStyle={{ color: '#1890ff' }}
              prefix="$"
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title="Options P&L"
              value={totalOptionsPL}
              precision={0}
              valueStyle={{ color: totalOptionsPL >= 0 ? '#52c41a' : '#ff4d4f' }}
              prefix={totalOptionsPL >= 0 ? <ArrowUpOutlined /> : <ArrowDownOutlined />}
              suffix="$"
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title="Portfolio Delta"
              value={totalDelta}
              precision={0}
              valueStyle={{ color: totalDelta >= 0 ? '#52c41a' : '#ff4d4f' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title="Daily Theta Decay"
              value={Math.abs(totalTheta)}
              precision={0}
              valueStyle={{ color: '#ff4d4f' }}
              prefix="-$"
            />
          </Card>
        </Col>
      </Row>

      {/* Risk Metrics */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} lg={12}>
          <Card title="IV Rank Analysis">
            <div style={{ marginBottom: 16 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                <span>AAPL IV Rank</span>
                <span>65%</span>
              </div>
              <Progress percent={65} strokeColor="#faad14" />
            </div>
            <div style={{ marginBottom: 16 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                <span>MSFT IV Rank</span>
                <span>35%</span>
              </div>
              <Progress percent={35} strokeColor="#52c41a" />
            </div>
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                <span>TSLA IV Rank</span>
                <span>85%</span>
              </div>
              <Progress percent={85} strokeColor="#ff4d4f" />
            </div>
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title="Expiration Calendar">
            <div style={{ marginBottom: 16 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span>Jan 19, 2024 (AAPL)</span>
                <Tag color="orange">5 days</Tag>
              </div>
            </div>
            <div style={{ marginBottom: 16 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span>Jan 26, 2024 (TSLA)</span>
                <Tag color="red">12 days</Tag>
              </div>
            </div>
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span>Feb 16, 2024 (MSFT)</span>
                <Tag color="green">33 days</Tag>
              </div>
            </div>
          </Card>
        </Col>
      </Row>

      {/* Options Positions Table */}
      <Card title="Options Positions">
        <Table
          columns={columns}
          dataSource={optionsPositions}
          pagination={false}
          scroll={{ x: 1000 }}
        />
      </Card>

      {/* Greeks Summary */}
      <Row gutter={[16, 16]} style={{ marginTop: 24 }}>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title="Total Gamma"
              value={0.18}
              precision={2}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title="Total Vega"
              value={0.75}
              precision={2}
              valueStyle={{ color: '#722ed1' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title="Avg IV"
              value={32.0}
              precision={1}
              valueStyle={{ color: '#faad14' }}
              suffix="%"
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title="Days to Expiry (Avg)"
              value={17}
              valueStyle={{ color: '#ff4d4f' }}
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default Options;
