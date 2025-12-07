import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { User, LoginCredentials, RegisterCredentials, login, loginGuest, register, logout as apiLogout, getCurrentUser } from '../services/api'

interface AuthState {
    user: User | null
    token: string | null
    isAuthenticated: boolean
    isLoading: boolean
    error: string | null

    login: (credentials: LoginCredentials) => Promise<void>
    loginAsGuest: () => Promise<void>
    register: (credentials: RegisterCredentials) => Promise<void>
    logout: () => Promise<void>
    checkAuth: () => Promise<void>
    clearError: () => void
}

const getErrorMessage = (error: any): string => {
    if (error.response?.data?.detail) {
        const detail = error.response.data.detail;
        if (typeof detail === 'string') {
            return detail;
        }
        if (Array.isArray(detail)) {
            // Handle FastAPI validation errors
            return detail.map((err: any) => err.msg || JSON.stringify(err)).join(', ');
        }
        return JSON.stringify(detail);
    }
    return error.message || 'An unknown error occurred';
};

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
                        error: getErrorMessage(error),
                        isLoading: false
                    })
                    throw error
                }
            },

            loginAsGuest: async () => {
                set({ isLoading: true, error: null })
                try {
                    const response = await loginGuest()
                    set({
                        token: response.access_token,
                        isAuthenticated: true,
                        isLoading: false
                    })
                    await get().checkAuth()
                } catch (error: any) {
                    set({
                        error: getErrorMessage(error),
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
                        error: getErrorMessage(error),
                        isLoading: false
                    })
                    throw error
                }
            },

            logout: async () => {
                try {
                    await apiLogout()
                } catch (e) {
                    console.error("Logout failed", e)
                }
                set({ user: null, token: null, isAuthenticated: false })
                localStorage.removeItem('sage-auth-storage')
                // Force reload to clear all in-memory states (Zustand stores)
                window.location.href = '/login'
            },

            checkAuth: async () => {
                const { token, isAuthenticated } = get()
                if (!token) {
                    if (isAuthenticated) {
                        set({ user: null, token: null, isAuthenticated: false })
                    }
                    return
                }

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
