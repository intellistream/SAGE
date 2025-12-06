import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { User, LoginCredentials, RegisterCredentials, login, register, getCurrentUser } from '../services/api'

interface AuthState {
    user: User | null
    token: string | null
    isAuthenticated: boolean
    isLoading: boolean
    error: string | null
    
    login: (credentials: LoginCredentials) => Promise<void>
    register: (credentials: RegisterCredentials) => Promise<void>
    logout: () => void
    checkAuth: () => Promise<void>
    clearError: () => void
}

export const useAuthStore = create<AuthState>()(
    persist(
        (set, get) => ({
            user: null,
            token: null,
            isAuthenticated: false,
            isLoading: false,
            error: null,

            login: async (credentials) => {
                set({ isLoading: true, error: null })
                try {
                    const response = await login(credentials)
                    set({ 
                        token: response.access_token,
                        isAuthenticated: true,
                        isLoading: false 
                    })
                    // Fetch user details immediately after login
                    await get().checkAuth()
                } catch (error: any) {
                    set({ 
                        error: error.response?.data?.detail || 'Login failed',
                        isLoading: false 
                    })
                    throw error
                }
            },

            register: async (credentials) => {
                set({ isLoading: true, error: null })
                try {
                    await register(credentials)
                    set({ isLoading: false })
                } catch (error: any) {
                    set({ 
                        error: error.response?.data?.detail || 'Registration failed',
                        isLoading: false 
                    })
                    throw error
                }
            },

            logout: () => {
                set({ user: null, token: null, isAuthenticated: false })
                localStorage.removeItem('sage-auth-storage')
                // Force reload to clear all in-memory states (Zustand stores)
                window.location.href = '/login'
            },

            checkAuth: async () => {
                const { token } = get()
                if (!token) return

                try {
                    const user = await getCurrentUser()
                    set({ user, isAuthenticated: true })
                } catch (error) {
                    // If token is invalid, logout
                    set({ user: null, token: null, isAuthenticated: false })
                }
            },

            clearError: () => set({ error: null })
        }),
        {
            name: 'sage-auth-storage',
            partialize: (state: AuthState) => ({ token: state.token, isAuthenticated: state.isAuthenticated, user: state.user }),
        }
    )
)
