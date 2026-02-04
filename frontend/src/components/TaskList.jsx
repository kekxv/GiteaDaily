import React, { useEffect, useState } from 'react';
import { Table, Button, Space, Popconfirm, message, Tag, Switch } from 'antd';
import { EditOutlined, DeleteOutlined, HistoryOutlined, PlayCircleOutlined } from '@ant-design/icons';
import api from '../services/api';

const TaskList = ({ onEdit, onViewLogs }) => {
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchTasks();
  }, []);

  const fetchTasks = async () => {
    setLoading(true);
    try {
      const response = await api.get('/tasks/');
      setTasks(response.data);
    } catch (error) {
      message.error('获取任务列表失败');
    } finally {
      setLoading(false);
    }
  };

  const handleRunNow = async (id) => {
    try {
      await api.post(`/tasks/${id}/run`);
      message.success('已触发即时执行，日报稍后送达');
    } catch (error) {
      message.error('触发失败');
    }
  };

  const handleDelete = async (id) => {
    try {
      await api.delete(`/tasks/${id}`);
      message.success('任务已删除');
      fetchTasks();
    } catch (error) {
      message.error('删除失败');
    }
  };

  const toggleStatus = async (task) => {
    try {
      await api.put(`/tasks/${task.id}`, {
        ...task,
        is_active: !task.is_active
      });
      message.success(`任务已${!task.is_active ? '启用' : '禁用'}`);
      fetchTasks();
    } catch (error) {
      message.error('操作失败');
    }
  };

  const formatCron = (cron) => {
    const parts = cron.split(' ');
    if (parts.length < 5) return cron;
    const [m, h, dom, mon, dow] = parts;
    const time = `${h.padStart(2, '0')}:${m.padStart(2, '0')}`;
    
    if (dow === '1-5') return `工作日 ${time}`;
    if (dow !== '*' && dow !== '?') {
      const days = dow.split(',').map(d => {
        const map = { '1':'一', '2':'二', '3':'三', '4':'四', '5':'五', '6':'六', '0':'日' };
        return map[d];
      });
      return `每周(${days.join(',')}) ${time}`;
    }
    if (dom.startsWith('*/')) return `每隔${dom.split('/')[1]}天 ${time}`;
    return `每天 ${time}`;
  };

  const columns = [
    { title: '任务名称', dataIndex: 'name', key: 'name' },
    { 
      title: '计划执行', 
      dataIndex: 'cron_expression', 
      key: 'cron_expression',
      render: (cron) => formatCron(cron)
    },
    { 
      title: '范围', 
      dataIndex: 'scope_type', 
      key: 'scope_type',
      render: (type) => type === 'all' ? <Tag color="blue">所有仓库</Tag> : <Tag color="green">指定仓库</Tag>
    },
    { 
      title: '状态', 
      key: 'is_active',
      render: (_, record) => (
        <Switch 
          checked={record.is_active} 
          onChange={() => toggleStatus(record)} 
        />
      )
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <Space size="small">
          <Button icon={<PlayCircleOutlined />} onClick={() => handleRunNow(record.id)}>立即执行</Button>
          <Button icon={<EditOutlined />} onClick={() => onEdit(record)}>编辑</Button>
          <Button icon={<HistoryOutlined />} onClick={() => onViewLogs(record)}>记录</Button>
          <Popconfirm title="确定删除吗？" onConfirm={() => handleDelete(record.id)}>
            <Button danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return <Table columns={columns} dataSource={tasks} rowKey="id" loading={loading} />;
};

export default TaskList;
