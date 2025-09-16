import React, { useState } from 'react';
import { Card, Table, Row, Col, Statistic, Progress, Tag } from 'antd';
import { ArrowUpOutlined, ArrowDownOutlined } from '@ant-design/icons';

const Portfolio = () => {
  const [positions] = useState([
    {
      key: '1',
      symbol: 'AAPL',
      quantity: 100,
      avgPrice: 150.25,
      currentPrice: 155.80,
      marketValue: 15580,
      unrealizedPL: 555,
      unrealizedPLPercent: 3.69,
      sector: 'Technology'
    },
    {
      key: '2',
      symbol: 'MSFT',
      quantity: 50,
      avgPrice: 280.50,
      currentPrice: 275.20,
      marketValue: 13760,
      unrealizedPL: -265,
      unrealizedPLPercent: -1.89,
      sector: 'Technology'
    },
    {
      key: '3',
      symbol: 'TSLA',
      quantity: 25,
      avgPrice: 220.00,
      currentPrice: 235.45,
      marketValue: 5886.25,
      unrealizedPL: 386.25,
      unrealizedPLPercent: 7.02,
      sector: 'Consumer Discretionary'
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
      title: 'Quantity',
      dataIndex: 'quantity',
      key: 'quantity'
    },
    {
      title: 'Avg Price',
      dataIndex: 'avgPrice',
      key: 'avgPrice',
      render: (value) => `$${value.toFixed(2)}`
    },
    {
      title: 'Current Price',
      dataIndex: 'currentPrice',
      key: 'currentPrice',
      render: (value) => `$${value.toFixed(2)}`
    },
    {
      title: 'Market Value',
      dataIndex: 'marketValue',
      key: 'marketValue',
      render: (value) => `$${value.toLocaleString()}`
    },
    {
      title: 'Unrealized P&L',
      dataIndex: 'unrealizedPL',
      key: 'unrealizedPL',
      render: (value, record) => (
        <span style={{ color: value >= 0 ? '#52c41a' : '#ff4d4f' }}>
          {value >= 0 ? <ArrowUpOutlined /> : <ArrowDownOutlined />}
          ${Math.abs(value).toFixed(2)} ({record.unrealizedPLPercent.toFixed(2)}%)
        </span>
      )
    },
    {
      title: 'Sector',
      dataIndex: 'sector',
      key: 'sector',
      render: (sector) => <Tag color="blue">{sector}</Tag>
    }
  ];

  const totalValue = positions.reduce((sum, pos) => sum + pos.marketValue, 0);
  const totalPL = positions.reduce((sum, pos) => sum + pos.unrealizedPL, 0);
  const totalPLPercent = (totalPL / (totalValue - totalPL)) * 100;

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 28, fontWeight: 600, color: '#1890ff', margin: 0 }}>
          Portfolio Overview
        </h1>
        <p style={{ color: '#666', margin: '8px 0 0 0' }}>
          Current positions and performance metrics
        </p>
      </div>

      {/* Portfolio Summary */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic
              title="Total Portfolio Value"
              value={totalValue}
              precision={2}
              valueStyle={{ color: '#1890ff' }}
              prefix="$"
            />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic
              title="Total Unrealized P&L"
              value={totalPL}
              precision={2}
              valueStyle={{ color: totalPL >= 0 ? '#52c41a' : '#ff4d4f' }}
              prefix={totalPL >= 0 ? <ArrowUpOutlined /> : <ArrowDownOutlined />}
              suffix="$"
            />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic
              title="Total Return"
              value={totalPLPercent}
              precision={2}
              valueStyle={{ color: totalPLPercent >= 0 ? '#52c41a' : '#ff4d4f' }}
              prefix={totalPLPercent >= 0 ? <ArrowUpOutlined /> : <ArrowDownOutlined />}
              suffix="%"
            />
          </Card>
        </Col>
      </Row>

      {/* Sector Allocation */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} lg={12}>
          <Card title="Sector Allocation">
            <div style={{ marginBottom: 16 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                <span>Technology</span>
                <span>83.2%</span>
              </div>
              <Progress percent={83.2} strokeColor="#1890ff" />
            </div>
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                <span>Consumer Discretionary</span>
                <span>16.8%</span>
              </div>
              <Progress percent={16.8} strokeColor="#52c41a" />
            </div>
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title="Performance Metrics">
            <Row gutter={[16, 16]}>
              <Col span={12}>
                <Statistic
                  title="Best Performer"
                  value="TSLA"
                  valueStyle={{ color: '#52c41a' }}
                  suffix="+7.02%"
                />
              </Col>
              <Col span={12}>
                <Statistic
                  title="Worst Performer"
                  value="MSFT"
                  valueStyle={{ color: '#ff4d4f' }}
                  suffix="-1.89%"
                />
              </Col>
            </Row>
          </Card>
        </Col>
      </Row>

      {/* Positions Table */}
      <Card title="Current Positions">
        <Table
          columns={columns}
          dataSource={positions}
          pagination={false}
          scroll={{ x: 800 }}
        />
      </Card>
    </div>
  );
};

export default Portfolio;
