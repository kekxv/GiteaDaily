import React, { useEffect, useState } from 'react';
import { Form, Input, Select, Switch, Button, message, Space, TimePicker, Checkbox, InputNumber } from 'antd';
import api from '../services/api';
import dayjs from 'dayjs';

const { Option } = Select;

const TaskForm = ({ initialValues, onSuccess, onCancel }) => {
  const [form] = Form.useForm();
  const [giteaConfigs, setGiteaConfigs] = useState([]);
  const [notifyConfigs, setNotifyConfigs] = useState([]);
  const [aiConfigs, setAiConfigs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [testing, setTesting] = useState(false);

  useEffect(() => {
    fetchConfigs();
    if (initialValues?.cron_expression) {
      const parts = initialValues.cron_expression.split(' ');
      if (parts.length >= 5) {
        const [m, h, dom, _mon, dow] = parts;
        
        const formValues = {
          scheduled_time: dayjs().set('hour', Number(h)).set('minute', Number(m))
        };

        if (dow === '0-4') {
          formValues.frequency = 'weekdays';
        } else if (dow !== '*' && dow !== '?') {
          formValues.frequency = 'weekly';
          formValues.week_days = dow.split(',').map(Number);
        } else if (dom.startsWith('*/')) {
          formValues.frequency = 'interval';
          formValues.interval_days = Number(dom.split('/')[1]);
        } else {
          formValues.frequency = 'daily';
        }

        form.setFieldsValue(formValues);
      }
    }
  }, [initialValues, form]);

  const fetchConfigs = async () => {
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
      message.error('获取配置失败');
    }
  };

  const onTest = async () => {
    try {
      const values = await form.validateFields();
      setTesting(true);
      
      const time = values.scheduled_time;
      const m = time.minute();
      const h = time.hour();
      let cron = `${m} ${h} * * *`;

      if (values.frequency === 'weekdays') {
        cron = `${m} ${h} * * 0-4`;
      } else if (values.frequency === 'weekly') {
        cron = `${m} ${h} * * ${values.week_days.join(',')}`;
      } else if (values.frequency === 'interval') {
        cron = `${m} ${h} */${values.interval_days} * *`;
      }
      
      const payload = {
        ...values,
        cron_expression: cron
      };
      
      const res = await api.post('/tasks/test-run', payload);
      message.success(`测试发送成功！统计到 ${res.data.commit_count} 条提交。`);
    } catch (error) {
      if (error.errorFields) return;
      message.error(error.response?.data?.detail || '测试发送失败');
    } finally {
      setTesting(false);
    }
  };

  const onFinish = async (values) => {
    setLoading(true);
    
    const time = values.scheduled_time;
    const m = time.minute();
    const h = time.hour();
    let cron = `${m} ${h} * * *`;

    if (values.frequency === 'weekdays') {
      cron = `${m} ${h} * * 0-4`;
    } else if (values.frequency === 'weekly') {
      cron = `${m} ${h} * * ${values.week_days.join(',')}`;
    } else if (values.frequency === 'interval') {
      cron = `${m} ${h} */${values.interval_days} * *`;
    }
    
    const payload = {
      ...values,
      cron_expression: cron
    };
    delete payload.scheduled_time;
    delete payload.frequency;
    delete payload.week_days;
    delete payload.interval_days;

    try {
      if (initialValues?.id) {
        await api.put(`/tasks/${initialValues.id}`, payload);
        message.success('任务更新成功');
      } else {
        await api.post('/tasks/', payload);
        message.success('任务创建成功');
      }
      onSuccess();
    } catch (_error) {
      message.error(_error.response?.data?.detail || '保存任务失败');
    } finally {
      setLoading(false);
    }
  };

  const weekOptions = [
    { label: '周一', value: 0 },
    { label: '周二', value: 1 },
    { label: '周三', value: 2 },
    { label: '周四', value: 3 },
    { label: '周五', value: 4 },
    { label: '周六', value: 5 },
    { label: '周日', value: 6 },
  ];

  return (
    <Form
      form={form}
      layout="vertical"
      initialValues={initialValues || { is_active: true, scope_type: 'all', frequency: 'daily' }}
      onFinish={onFinish}
    >
      <Form.Item name="name" label="任务名称" rules={[{ required: true }]}>
        <Input placeholder="例如：每日提交汇总" />
      </Form.Item>

      <div style={{ background: '#fafafa', padding: 16, marginBottom: 24, borderRadius: 8 }}>
        <Form.Item name="frequency" label="执行频率" rules={[{ required: true }]}>
          <Select>
            <Option value="daily">每天</Option>
            <Option value="weekdays">工作日 (周一至周五)</Option>
            <Option value="weekly">每周特定时间</Option>
            <Option value="interval">固定间隔天数</Option>
          </Select>
        </Form.Item>

        <Form.Item noStyle shouldUpdate={(prev, curr) => prev.frequency !== curr.frequency}>
          {({ getFieldValue }) => {
            const freq = getFieldValue('frequency');
            return (
              <>
                {freq === 'weekly' && (
                  <Form.Item name="week_days" label="选择星期" rules={[{ required: true }]}>
                    <Checkbox.Group options={weekOptions} />
                  </Form.Item>
                )}
                {freq === 'interval' && (
                  <Form.Item name="interval_days" label="每隔几天执行一次" rules={[{ required: true }]}>
                    <InputNumber min={1} max={31} addonAfter="天" />
                  </Form.Item>
                )}
              </>
            );
          }}
        </Form.Item>

        <Form.Item name="scheduled_time" label="执行时间" rules={[{ required: true }]}>
          <TimePicker format="HH:mm" style={{ width: '100%' }} />
        </Form.Item>
      </div>

      <Form.Item name="gitea_config_id" label="Gitea 源" rules={[{ required: true }]}>
        <Select placeholder="选择 Gitea 配置">
          {giteaConfigs.map(cfg => (
            <Option key={cfg.id} value={cfg.id}>{cfg.name} ({cfg.base_url})</Option>
          ))}
        </Select>
      </Form.Item>

      <Form.Item name="notify_config_id" label="通知渠道" rules={[{ required: true }]}>
        <Select placeholder="选择通知渠道">
          {notifyConfigs.map(cfg => (
            <Option key={cfg.id} value={cfg.id}>{cfg.name}</Option>
          ))}
        </Select>
      </Form.Item>

      <Form.Item name="scope_type" label="范围类型" rules={[{ required: true }]}>
        <Select>
          <Option value="all">所有仓库 (Token 可访问的所有仓库)</Option>
          <Option value="owner">仅个人仓库 (当前 Token 用户拥有的)</Option>
          <Option value="user">个人活动记录 (追踪我在所有仓库的行为轨迹)</Option>
          <Option value="specific">指定仓库</Option>
        </Select>
      </Form.Item>

      <Form.Item noStyle shouldUpdate={(prev, curr) => prev.scope_type !== curr.scope_type}>
        {({ getFieldValue }) => 
          getFieldValue('scope_type') === 'specific' ? (
            <Form.Item name="target_repos" label="仓库列表 (owner/repo)" rules={[{ required: true, type: 'array' }]}>
              <Select mode="tags" placeholder="输入并回车，例如：myorg/myrepo" />
            </Form.Item>
          ) : null
        }
      </Form.Item>

      <Form.Item name="is_active" label="启用状态" valuePropName="checked">
        <Switch />
      </Form.Item>

      <div style={{ background: '#f6ffed', padding: 16, marginBottom: 24, borderRadius: 8, border: '1px solid #b7eb8f' }}>
        <Form.Item name="is_ai_enabled" label="启用 AI 智能总结" valuePropName="checked">
          <Switch />
        </Form.Item>

        <Form.Item noStyle shouldUpdate={(prev, curr) => prev.is_ai_enabled !== curr.is_ai_enabled}>
          {({ getFieldValue }) => 
            getFieldValue('is_ai_enabled') ? (
              <>
                <Form.Item name="ai_config_id" label="AI 配置" rules={[{ required: true }]}>
                  <Select placeholder="选择 AI 配置">
                    {aiConfigs.map(cfg => (
                      <Option key={cfg.id} value={cfg.id}>{cfg.name} ({cfg.model})</Option>
                    ))}
                  </Select>
                </Form.Item>
                <Form.Item name="ai_system_prompt" label="任务专属系统提示词 (覆盖全局)">
                  <Input.TextArea placeholder="可选，若填写则覆盖 AI 配置中的系统提示词" rows={3} />
                </Form.Item>
              </>
            ) : null
          }
        </Form.Item>
      </div>

      <Form.Item name="report_days" label="统计时间范围" rules={[{ required: true }]}>
        <Select>
          <Option value={1}>过去 1 天 (默认)</Option>
          <Option value={3}>过去 3 天</Option>
          <Option value={7}>过去 7 天</Option>
          <Option value={14}>过去 14 天</Option>
          <Option value={30}>过去 30 天</Option>
        </Select>
      </Form.Item>

      <Form.Item>
        <Space>
          <Button type="primary" htmlType="submit" loading={loading}>
            保存
          </Button>
          <Button onClick={onTest} loading={testing}>
            测试发送
          </Button>
          <Button onClick={onCancel}>取消</Button>
        </Space>
      </Form.Item>
    </Form>
  );
};

export default TaskForm;
