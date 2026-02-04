import React, { useState } from 'react';
import { Button, Modal, Drawer, Table, Tag, DatePicker, Space, Tabs } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import TaskList from '../components/TaskList';
import TaskForm from '../components/TaskForm';
import api from '../services/api';
import dayjs from 'dayjs';

const { RangePicker } = DatePicker;

const Dashboard = () => {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingTask, setEditingTask] = useState(null);
  const [isLogDrawerOpen, setIsLogDrawerOpen] = useState(false);
  const [selectedTask, setSelectedTask] = useState(null);
  const [logs, setLogs] = useState([]);
  const [logLoading, setLogLoading] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);
  const [dateRange, setDateRange] = useState([dayjs().subtract(7, 'day'), dayjs()]);

  const handleAdd = () => {
    setEditingTask(null);
    setIsModalOpen(true);
  };

  const handleEdit = (task) => {
    setEditingTask(task);
    setIsModalOpen(true);
  };

  const handleSuccess = () => {
    setIsModalOpen(false);
    setRefreshKey(prev => prev + 1);
  };

  const fetchLogs = async (task, range) => {
    setLogLoading(true);
    try {
      const params = { task_id: task.id };
      if (range) {
        params.start_date = range[0].startOf('day').toISOString();
        params.end_date = range[1].endOf('day').toISOString();
      }
      const res = await api.get('/logs/', { params });
      setLogs(res.data);
    } catch (_error) {
      console.error('Failed to fetch logs');
    } finally {
      setLogLoading(false);
    }
  };

  const handleViewLogs = async (task) => {
    setSelectedTask(task);
    setIsLogDrawerOpen(true);
    fetchLogs(task, dateRange);
  };

  const onRangeChange = (dates) => {
    setDateRange(dates);
    if (selectedTask) {
      fetchLogs(selectedTask, dates);
    }
  };

  const logColumns = [
    { 
      title: '时间', 
      dataIndex: 'created_at', 
      key: 'created_at',
      render: (text) => dayjs(text).format('YYYY-MM-DD HH:mm:ss')
    },
    { 
      title: '状态', 
      dataIndex: 'status', 
      key: 'status',
      render: (status) => <Tag color={status === 'success' ? 'green' : 'red'}>{status}</Tag>
    },
    { title: '提交数', dataIndex: 'commit_count', key: 'commit_count' },
    { title: '摘要', dataIndex: 'summary', key: 'summary', ellipsis: true },
  ];

  return (
    <div style={{ padding: 24 }}>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
        <h2>任务管理</h2>
        <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>创建任务</Button>
      </div>
      
      <TaskList key={refreshKey} onEdit={handleEdit} onViewLogs={handleViewLogs} />

      <Modal
        title={editingTask ? "编辑任务" : "创建任务"}
        open={isModalOpen}
        onCancel={() => setIsModalOpen(false)}
        footer={null}
        destroyOnHidden
      >
        <TaskForm 
          initialValues={editingTask} 
          onSuccess={handleSuccess} 
          onCancel={() => setIsModalOpen(false)} 
        />
      </Modal>

      <Drawer
        title={
          <Space>
            <span>执行历史</span>
            <RangePicker 
              value={dateRange} 
              onChange={onRangeChange} 
              presets={[
                { label: '今天', value: [dayjs(), dayjs()] },
                { label: '最近一周', value: [dayjs().subtract(7, 'd'), dayjs()] },
                { label: '最近一月', value: [dayjs().subtract(1, 'm'), dayjs()] },
              ]}
            />
          </Space>
        }
        placement="right"
        onClose={() => setIsLogDrawerOpen(false)}
        open={isLogDrawerOpen}
        size="large"
      >
        <Table 
          columns={logColumns} 
          dataSource={logs} 
          rowKey="id" 
          loading={logLoading}
          expandable={{
            expandedRowRender: (record) => {
              const tabItems = [
                {
                  key: 'report',
                  label: '发送详情 (Markdown)',
                  children: (
                    <div style={{ background: '#f5f5f5', padding: '12px', borderRadius: '4px', whiteSpace: 'pre-wrap', fontFamily: 'monospace', maxHeight: '400px', overflow: 'auto' }}>
                      {record.log_details || '无详细记录'}
                    </div>
                  ),
                },
                {
                  key: 'raw',
                  label: '原始数据 (JSON)',
                  children: (
                    <div style={{ background: '#f5f5f5', padding: '12px', borderRadius: '4px', whiteSpace: 'pre-wrap', fontFamily: 'monospace', maxHeight: '400px', overflow: 'auto' }}>
                      {record.raw_data ? JSON.stringify(JSON.parse(record.raw_data), null, 2) : '无原始数据'}
                    </div>
                  ),
                },
              ];
              return <Tabs size="small" items={tabItems} />;
            },
            rowExpandable: (record) => !!record.log_details || !!record.raw_data,
          }}
        />
      </Drawer>
    </div>
  );
};

export default Dashboard;
