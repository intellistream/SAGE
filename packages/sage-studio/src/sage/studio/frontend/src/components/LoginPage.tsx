import React, { useState } from 'react'
import { Form, Input, Button, Card, Typography, Alert, Tabs } from 'antd'
import { UserOutlined, LockOutlined } from '@ant-design/icons'
import { useAuthStore } from '../store/authStore'
import { useNavigate, useLocation, Navigate } from 'react-router-dom'

const { Title, Text } = Typography

export const LoginPage: React.FC = () => {
    const [activeTab, setActiveTab] = useState('login')
    const { login, loginAsGuest, register, isLoading, error, clearError } = useAuthStore()
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

    const handleGuestLogin = async () => {
        try {
            await loginAsGuest()
            navigate(from, { replace: true })
        } catch (e) {
            // Error handled in store
        }
    }

    const handleTabChange = (key: string) => {
        setActiveTab(key)
        clearError()
    }

    // If user is already authenticated and NOT a guest, redirect to home
    // If user is guest, allow them to see login page to upgrade/switch
    const { isAuthenticated, user } = useAuthStore()
    if (isAuthenticated && !user?.is_guest) {
        // Use useEffect to avoid render loop warning, but direct return is also common for redirects
        // Better to use Navigate component
        return <Navigate to="/" replace />
    }

    // Need to import Navigate
    // import { useNavigate, useLocation, Navigate } from 'react-router-dom'

    return (
        <div
            className="bg-[--gemini-sidebar-bg]"
            style={{
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
                minHeight: '100vh',
            }}
        >
            <Card
                className="bg-[--gemini-main-bg] border-[--gemini-border]"
                style={{ width: 400, boxShadow: '0 4px 12px rgba(0,0,0,0.15)' }}
            >
                <div style={{ textAlign: 'center', marginBottom: 24 }}>
                    <Title level={2} className="!text-[--gemini-text-primary]">SAGE</Title>
                    <Text className="!text-[--gemini-text-secondary]">Generative AI & Dataflow Studio</Text>
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

                <div style={{ marginTop: 16, textAlign: 'center' }}>
                    <Text className="!text-[--gemini-text-secondary]" style={{ display: 'block', marginBottom: 8 }}>Or</Text>
                    <Button
                        type="default"
                        onClick={handleGuestLogin}
                        loading={isLoading}
                        block
                    >
                        Continue as Guest
                    </Button>
                </div>
            </Card>
        </div>
    )
}
