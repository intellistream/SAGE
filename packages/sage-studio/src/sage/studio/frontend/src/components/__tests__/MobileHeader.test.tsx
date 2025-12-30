import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import MobileHeader from '../MobileHeader'

// Mock the stores
vi.mock('../store/authStore', () => ({
    useAuthStore: () => ({
        user: { name: 'Test User' },
        logout: vi.fn(),
        isAuthenticated: true,
    }),
}))

// Mock theme store if it exists, otherwise we might need to adjust
vi.mock('../store/themeStore', () => ({
    useThemeStore: () => ({
        resolvedTheme: 'light',
        toggleTheme: vi.fn(),
    }),
}))

describe('MobileHeader', () => {
    const defaultProps = {
        onMenuClick: vi.fn(),
        onNewChat: vi.fn(),
        llmStatus: {
            model_name: 'test-model',
            running: true,
            healthy: true,
            service_type: 'local_vllm' as const,
            base_url: 'http://localhost:8001',
            is_local: true,
        },
        onSelectModel: vi.fn(),
    }

    it('renders correctly', () => {
        render(<MobileHeader {...defaultProps} />)
        expect(screen.getByText('test-model')).toBeInTheDocument()
    })

    it('calls onMenuClick when menu button is clicked', () => {
        render(<MobileHeader {...defaultProps} />)
        const menuButton = screen.getByRole('button', { name: /menu/i })
        fireEvent.click(menuButton)
        expect(defaultProps.onMenuClick).toHaveBeenCalled()
    })

    it('calls onNewChat when new chat button is clicked', () => {
        render(<MobileHeader {...defaultProps} />)
        const newChatButton = screen.getByRole('button', { name: /new chat/i })
        fireEvent.click(newChatButton)
        expect(defaultProps.onNewChat).toHaveBeenCalled()
    })
})
