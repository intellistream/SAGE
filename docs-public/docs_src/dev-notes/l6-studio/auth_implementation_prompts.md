# SAGE Studio Authentication Implementation Prompts

This file contains the specific prompts for the 4 tasks required to implement user authentication in
SAGE Studio. These prompts are designed to be used with an AI coding assistant.

______________________________________________________________________

## Task 1: Backend Authentication System

**Role**: SAGE Framework Backend Developer **Goal**: Implement a secure user authentication system
for the Studio backend.

**Prompt**:

```markdown
You are an expert Python developer working on the SAGE framework.
Your task is to implement a user authentication system for the SAGE Studio backend.

**Context**:
- The backend is a FastAPI application located in `packages/sage-studio/src/sage/studio/config/backend/api.py`.
- Currently, there is no authentication; all users share the same workspace.

**Requirements**:

1.  **Create `packages/sage-studio/src/sage/studio/services/auth_service.py`**:
    -   Define a `User` model (id, username, password_hash, created_at).
    -   Implement password hashing using `bcrypt` or `passlib`.
    -   Implement JWT Token generation and validation using `python-jose`.
    -   Use SQLite for storage: `~/.local/share/sage/studio.db`.

2.  **Update `packages/sage-studio/src/sage/studio/config/backend/api.py`**:
    -   Add authentication endpoints:
        -   `POST /api/auth/register`: Register a new user.
        -   `POST /api/auth/login`: Login and return a JWT token.
        -   `GET /api/auth/me`: Get current user info.
        -   `POST /api/auth/logout`: Logout (optional, client-side token removal is usually sufficient but an endpoint can be added for future blacklist).
    -   Create a FastAPI dependency `get_current_user(token: str)` to validate tokens and retrieve the user.

**Technical Constraints**:
-   JWT Expiration: 24 hours.
-   Password: Minimum 6 characters.
-   Use Pydantic models for all requests and responses.
-   Follow SAGE code style: 100 character line limit, type hints.

**Testing**:
-   Create a test file `packages/sage-studio/tests/services/test_auth_service.py` to verify hashing, token generation, and user storage.
```

______________________________________________________________________

## Task 2: Backend Data Isolation

**Role**: SAGE Framework Backend Developer **Goal**: Isolate user data (pipelines, sessions) based
on the authenticated user.

**Prompt**:

```markdown
You are an expert Python developer working on the SAGE framework.
Your task is to modify the SAGE Studio backend to support multi-user data isolation.

**Context**:
-   You have access to the `get_current_user` dependency from Task 1.
-   Currently, all data is stored globally in `.sage/pipelines/` or similar.

**Requirements**:

1.  **Refactor Data Storage Structure**:
    -   Move from global storage to user-specific storage in `~/.local/share/sage/users/{user_id}/`.
    -   Structure:
        -   `.../users/{user_id}/pipelines/`: User's flow definitions.
        -   `.../users/{user_id}/sessions/`: User's chat sessions.
        -   `.../users/{user_id}/uploads/`: User's uploaded files.

2.  **Update API Endpoints in `api.py`**:
    -   Modify `GET /api/jobs`: Return only jobs belonging to the current user.
    -   Modify `POST /api/submit`: Save jobs/pipelines to the current user's directory.
    -   Modify `GET /api/flow/{flow_id}/export`: Ensure users can only export their own flows.
    -   Modify `POST /api/flow/import`: Import flows into the current user's directory.
    -   Update Chat APIs (`/api/chat/*`) to filter sessions by user and associate new sessions with the user.

3.  **Helper Functions**:
    -   Implement `get_user_data_dir(user_id: str) -> Path`.
    -   Implement `get_user_pipelines_dir(user_id: str) -> Path`.

**Compatibility**:
-   If no user is logged in (or for backward compatibility), use a default "anonymous" user ID.
-   (Optional) Create a migration script to move existing data to the "anonymous" user folder.
```

______________________________________________________________________

## Task 3: Frontend Authentication UI

**Role**: SAGE Frontend Developer (React/TypeScript) **Goal**: Create the login/register UI and
manage authentication state.

**Prompt**:

```markdown
You are an expert Frontend Developer using React, TypeScript, Ant Design, and Zustand.
Your task is to implement the authentication UI for SAGE Studio.

**Context**:
-   The frontend is located in `packages/sage-studio/src/sage/studio/frontend/src/`.
-   The backend API (Task 1) provides `/api/auth/*` endpoints.

**Requirements**:

1.  **State Management (`store/authStore.ts`)**:
    -   Create a Zustand store `useAuthStore`.
    -   State: `user`, `token`, `isAuthenticated`.
    -   Actions: `login(username, password)`, `register(username, password)`, `logout()`, `checkAuth()`.
    -   Persist the JWT token in `localStorage`.
    -   Auto-check auth status on application load.

2.  **Login Page (`components/LoginPage.tsx`)**:
    -   Create a centered, card-style layout using Ant Design.
    -   Tabs for "Login" and "Register".
    -   Form validation and error display.
    -   Redirect to the main app upon success.

3.  **User Menu (`components/UserMenu.tsx`)**:
    -   Display the current username.
    -   Dropdown menu with "Logout" option.
    -   This will be placed in the Toolbar later.

4.  **API Service (`services/api.ts`)**:
    -   Add methods for auth endpoints (`login`, `register`, `me`).
    -   Add an Axios/Fetch interceptor (or modify the wrapper) to inject the `Authorization: Bearer <token>` header into every request.
    -   Handle `401 Unauthorized` responses by redirecting to the login page.

5.  **Routing (`App.tsx`)**:
    -   Add a `/login` route.
    -   Implement a `ProtectedRoute` component or logic to redirect unauthenticated users to `/login`.
```

______________________________________________________________________

## Task 4: Frontend Integration & State

**Role**: SAGE Frontend Developer (React/TypeScript) **Goal**: Integrate authentication into the
existing Studio UI components.

**Prompt**:

```markdown
You are an expert Frontend Developer working on SAGE Studio.
Your task is to integrate the authentication system (Task 3) into the existing UI components.

**Context**:
-   Auth store and Login page are implemented.
-   Existing components (`Toolbar`, `ChatMode`, `flowStore`) need to be auth-aware.

**Requirements**:

1.  **Toolbar Integration (`components/Toolbar.tsx`)**:
    -   Add the `UserMenu` component to the right side of the toolbar.
    -   Show a "Login" button if the user is not authenticated (if you allow guest access), or ensure the user is logged in via `App.tsx`.

2.  **Chat Mode (`components/ChatMode.tsx`)**:
    -   Ensure the session list fetches only the current user's sessions (backend handles filtering, frontend just needs to send the token).
    -   When creating a new session, ensure it's tied to the user (via the token).

3.  **Flow Store (`store/flowStore.ts`)**:
    -   Update flow saving/loading logic to respect the user context.
    -   (Optional) Add a `userId` field to the flow state if needed for client-side logic.

4.  **User Experience**:
    -   Ensure the app retains login state on page refresh.
    -   On Logout: Clear all local user data (Zustand stores) and redirect to Login.
    -   Test the flow: Login -> Create Flow -> Logout -> Login -> Verify Flow exists.

**Files to Modify**:
-   `packages/sage-studio/src/sage/studio/frontend/src/components/Toolbar.tsx`
-   `packages/sage-studio/src/sage/studio/frontend/src/components/ChatMode.tsx`
-   `packages/sage-studio/src/sage/studio/frontend/src/App.tsx`
-   `packages/sage-studio/src/sage/studio/frontend/src/store/flowStore.ts`
```
