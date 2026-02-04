import React, { useState, useEffect } from 'react';
import { Tabs, Table, Button, Modal, Form, Input, message, Space, Popconfirm } from 'antd';
import { PlusOutlined, DeleteOutlined, CheckCircleOutlined } from '@ant-design/icons';
import api from '../services/api';

const ConfigPage = () => {
  const [giteaConfigs, setGiteaConfigs] = useState([]);
  const [notifyConfigs, setNotifyConfigs] = useState([]);
  const [aiConfigs, setAiConfigs] = useState([]);
  const [isGiteaModalOpen, setIsGiteaModalOpen] = useState(false);
  const [isNotifyModalOpen, setIsNotifyModalOpen] = useState(false);
  const [isAiModalOpen, setIsAiModalOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  
  const [giteaForm] = Form.useForm();
  const [notifyForm] = Form.useForm();
  const [aiForm] = Form.useForm();

  useEffect(() => {
    fetchConfigs();
  }, []);

  const fetchConfigs = async () => {
    setLoading(true);
    try {
      const [giteaRes, notifyRes, aiRes] = await Promise.all([
        api.get('/gitea/'),
        api.get('/notify/'),
        api.get('/ai/')
      ]);
      setGiteaConfigs(giteaRes.data);
      setNotifyConfigs(notifyRes.data);
      setAiConfigs(aiRes.data);
    } catch (_error) {
      message.error('加载配置失败');
    } finally {
      setLoading(false);
    }
  };

  const handleTestGitea = async (id) => {
    try {
      const res = await api.post(`/gitea/${id}/test`);
      if (res.data.success) message.success('连接成功');
      else message.error('连接失败');
    } catch (_error) {
      message.error('测试失败');
    }
  };

  const handleTestNotify = async (id) => {
    try {
      const res = await api.post(`/notify/${id}/test`);
      if (res.data.success) message.success('测试消息已发送');
      else message.error('发送失败');
    } catch (_error) {
      message.error('测试失败');
    }
  };

  const handleTestAi = async (id) => {
    setLoading(true);
    try {
      const res = await api.post(`/ai/${id}/test`);
      if (res.data.success) {
        message.success('AI 连接成功: ' + res.data.response);
      } else {
        message.error('AI 连接失败: ' + res.data.error);
      }
    } catch (_error) {
      message.error('测试出错');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (type, id) => {
    try {
      await api.delete(`/${type}/${id}`);
      message.success('删除成功');
      fetchConfigs();
    } catch (_error) {
      message.error('删除失败');
    }
  };

  const onAddGitea = async (values) => {
    setSubmitting(true);
    try {
      await api.post('/gitea/', values);
      message.success('配置已添加');
      setIsGiteaModalOpen(false);
      giteaForm.resetFields();
      fetchConfigs();
    } catch (_error) {
      message.error('添加失败');
    } finally {
      setSubmitting(false);
    }
  };

  const onAddNotify = async (values) => {
    setSubmitting(true);
    try {
      await api.post('/notify/', values);
      message.success('配置已添加');
      setIsNotifyModalOpen(false);
      notifyForm.resetFields();
      fetchConfigs();
    } catch (_error) {
      message.error('添加失败');
    } finally {
      setSubmitting(false);
    }
  };

  const onAddAi = async (values) => {
    setSubmitting(true);
    try {
      await api.post('/ai/', values);
      message.success('AI 配置已添加');
      setIsAiModalOpen(false);
      aiForm.resetFields();
      fetchConfigs();
    } catch (_error) {
      message.error('添加失败');
    } finally {
      setSubmitting(false);
    }
  };

  const giteaColumns = [
    { title: '别名', dataIndex: 'name', key: 'name' },
    { title: 'Base URL', dataIndex: 'base_url', key: 'base_url' },
    { 
      title: '操作', 
      key: 'action', 
      render: (_, record) => (
        <Space>
          <Button icon={<CheckCircleOutlined />} onClick={() => handleTestGitea(record.id)}>测试连接</Button>
          <Popconfirm title="确定删除？" onConfirm={() => handleDelete('gitea', record.id)}>
            <Button danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ) 
    },
  ];

  const notifyColumns = [
    { title: '别名', dataIndex: 'name', key: 'name' },
    { title: 'Webhook URL', dataIndex: 'webhook_url', key: 'webhook_url', ellipsis: true },
    { 
      title: '操作', 
      key: 'action', 
      render: (_, record) => (
        <Space>
          <Button icon={<CheckCircleOutlined />} onClick={() => handleTestNotify(record.id)}>发送测试</Button>
          <Popconfirm title="确定删除？" onConfirm={() => handleDelete('notify', record.id)}>
            <Button danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ) 
    },
  ];

  const aiColumns = [
    { title: '别名', dataIndex: 'name', key: 'name' },
    { title: '模型', dataIndex: 'model', key: 'model' },
    { 
      title: '操作', 
      key: 'action', 
      render: (_, record) => (
        <Space>
          <Button icon={<CheckCircleOutlined />} onClick={() => handleTestAi(record.id)}>测试连接</Button>
          <Popconfirm title="确定删除？" onConfirm={() => handleDelete('ai', record.id)}>
            <Button danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ) 
    },
  ];

  const tabItems = [
    {
      key: '1',
      label: 'Gitea 源配置',
      children: (
        <>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setIsGiteaModalOpen(true)} style={{ marginBottom: 16 }}>
            添加 Gitea 源
          </Button>
          <Table dataSource={giteaConfigs} columns={giteaColumns} rowKey="id" loading={loading} />
        </>
      ),
    },
    {
      key: '2',
      label: '通知渠道配置',
      children: (
        <>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setIsNotifyModalOpen(true)} style={{ marginBottom: 16 }}>
            添加通知渠道
          </Button>
          <Table dataSource={notifyConfigs} columns={notifyColumns} rowKey="id" loading={loading} />
        </>
      ),
    },
    {
      key: '3',
      label: 'AI 总结配置',
      children: (
        <>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setIsAiModalOpen(true)} style={{ marginBottom: 16 }}>
            添加 AI 配置
          </Button>
          <Table dataSource={aiConfigs} columns={aiColumns} rowKey="id" loading={loading} />
        </>
      ),
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <Tabs defaultActiveKey="1" items={tabItems} />

      <Modal 
        title="添加 Gitea 配置" 
        open={isGiteaModalOpen} 
        onCancel={() => setIsGiteaModalOpen(false)} 
        onOk={() => giteaForm.submit()}
        confirmLoading={submitting}
        destroyOnClose
      >
        <Form form={giteaForm} layout="vertical" onFinish={onAddGitea}>
          <Form.Item name="name" label="别名" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="base_url" label="Base URL" rules={[{ required: true }]}><Input placeholder="https://git.company.com" /></Form.Item>
          <Form.Item name="token" label="Access Token" rules={[{ required: true }]}><Input.Password /></Form.Item>
        </Form>
      </Modal>

      <Modal 
        title="添加通知配置" 
        open={isNotifyModalOpen} 
        onCancel={() => setIsNotifyModalOpen(false)} 
        onOk={() => notifyForm.submit()}
        confirmLoading={submitting}
        destroyOnClose
      >
        <Form form={notifyForm} layout="vertical" onFinish={onAddNotify}>
          <Form.Item name="name" label="别名" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="webhook_url" label="Webhook URL" rules={[{ required: true }]}><Input /></Form.Item>
        </Form>
      </Modal>

      <Modal 
        title="添加 AI 配置" 
        open={isAiModalOpen} 
        onCancel={() => setIsAiModalOpen(false)} 
        onOk={() => aiForm.submit()}
        confirmLoading={submitting}
        destroyOnClose
      >
        <Form form={aiForm} layout="vertical" onFinish={onAddAi} initialValues={{ api_base: 'https://api.openai.com/v1', model: 'gpt-3.5-turbo' }}>
          <Form.Item name="name" label="别名" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="api_base" label="API Base URL" rules={[{ required: true }]}><Input placeholder="https://api.openai.com/v1" /></Form.Item>
          <Form.Item name="api_key" label="API Key" rules={[{ required: true }]}><Input.Password /></Form.Item>
          <Form.Item name="model" label="模型名称" rules={[{ required: true }]}><Input placeholder="gpt-3.5-turbo" /></Form.Item>
          <Form.Item name="system_prompt" label="系统提示词 (System Prompt)">
            <Input.TextArea placeholder="可选，留空使用默认总结提示词" rows={4} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default ConfigPage;