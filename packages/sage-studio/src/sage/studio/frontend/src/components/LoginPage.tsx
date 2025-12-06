import React, { useState } from 'react'
import { Form, Input, Button, Card, Typography, Alert, Tabs } from 'antd'
import { UserOutlined, LockOutlined } from '@ant-design/icons'
import { useAuthStore } from '../store/authStore'
import { useNavigate, useLocation } from 'react-router-dom'

const { Title, Text } = Typography

export const LoginPage: React.FC = () => {
    const [activeTab, setActiveTab] = useState('login')
    const { login, register, isLoading, error, clearError } = useAuthStore()
    const navigate = useNavigate()
    const location = useLocation()

    // Get return url from location state or default to home
    const from = (location.state as any)?.from?.pathname || '/'

    const onFinish = async (values: any) => {
        try {
            if (activeTab === 'login') {
                await login(values)
                navigate(from, { replace: true })
            } else {
                await register(values)
                setActiveTab('login')
                // Show success message or auto-login?
                // For now, let's just switch to login tab
            }
        } catch (e) {
            // Error is handled in store
        }
    }

    const handleTabChange = (key: string) => {
        setActiveTab(key)
        clearError()
    }

    return (
        <div style={{ 
            display: 'flex', 
            justifyContent: 'center', 
            alignItems: 'center', 
            minHeight: '100vh',
            background: '#f0f2f5'
        }}>
            <Card style={{ width: 400, boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}>
                <div style={{ textAlign: 'center', marginBottom: 24 }}>
                    <Title level={2}>SAGE Studio</Title>
                    <Text type="secondary">AI Pipeline Development Environment</Text>
                </div>

                {error && (
                    <Alert 
                        message={error} 
                        type="error" 
                        showIcon 
                        style={{ marginBottom: 24 }} 
                        onClose={clearError}
                    />
                )}

                <Tabs activeKey={activeTab} onChange={handleTabChange} centered>
                    <Tabs.TabPane tab="Login" key="login" />
                    <Tabs.TabPane tab="Register" key="register" />
                </Tabs>

                <Form
                    name="auth_form"
                    initialValues={{ remember: true }}
                    onFinish={onFinish}
                    layout="vertical"
                    size="large"
                    style={{ marginTop: 24 }}
                >
                    <Form.Item
                        name="username"
                        rules={[{ required: true, message: 'Please input your Username!' }]}
                    >
                        <Input prefix={<UserOutlined />} placeholder="Username" />
                    </Form.Item>

                    <Form.Item
                        name="password"
                        rules={[{ required: true, message: 'Please input your Password!' }]}
                    >
                        <Input.Password prefix={<LockOutlined />} placeholder="Password" />
                    </Form.Item>

                    <Form.Item>
                        <Button type="primary" htmlType="submit" block loading={isLoading}>
                            {activeTab === 'login' ? 'Log in' : 'Register'}
                        </Button>
                    </Form.Item>
                </Form>
            </Card>
        </div>
    )
}
