# Frontend Auth Integration (MediOps API)

Backend expects **Supabase Auth** JWTs. Use the Supabase JS client on the frontend for sign-in/sign-up and send the **access token** with every API request.

---

## 1. Supabase setup (FE)

- Use the same Supabase project as the backend.
- Env vars for the frontend (from Supabase Dashboard → Project Settings → API):
  - `SUPABASE_URL` — Project URL
  - `SUPABASE_ANON_KEY` — anon/public key

```ts
// Example: create Supabase client (React/Next/React Native etc.)
import { createClient } from '@supabase/supabase-js'

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
)
```

---

## 2. Sign in / Sign up (FE only)

Auth is handled entirely by Supabase on the client. Backend does **not** expose login/register endpoints.

**Email + password sign in:**
```ts
const { data, error } = await supabase.auth.signInWithPassword({ email, password })
if (error) throw error
// data.session contains access_token, refresh_token, user
```

**Email + password sign up:**
```ts
const { data, error } = await supabase.auth.signUp({ email, password })
if (error) throw error
// data.session may be null if email confirmation is required
```

**Sign out:**
```ts
await supabase.auth.signOut()
```

**Get current session (on app load / refresh):**
```ts
const { data: { session } } = await supabase.auth.getSession()
if (session) {
  // session.access_token → use for API calls
  // session.expires_at → optional: check before request
}
```

**Listen for auth changes (e.g. to update UI / token):**
```ts
supabase.auth.onAuthStateChange((event, session) => {
  if (event === 'SIGNED_IN' || event === 'TOKEN_REFRESHED') {
    // Update your API client / state with session.access_token
  }
  if (event === 'SIGNED_OUT') {
    // Clear token and redirect to login
  }
})
```

---

## 3. Sending the token to the backend

Send the Supabase **access token** on every request to protected endpoints.

**Header:**
```http
Authorization: Bearer <access_token>
```

**Example with fetch:**
```ts
const session = (await supabase.auth.getSession()).data.session
const token = session?.access_token

const res = await fetch(`${API_BASE}/api/v1/auth/me`, {
  headers: {
    'Authorization': token ? `Bearer ${token}` : '',
    'Content-Type': 'application/json',
  },
})
```

**Example with axios:**
```ts
const session = (await supabase.auth.getSession()).data.session
api.defaults.headers.common['Authorization'] = session
  ? `Bearer ${session.access_token}`
  : ''
```

**Recommended:** Create a small API client that always attaches the current token (e.g. from `getSession()` or from your auth state) to every request.

---

## 4. API base URL

- Local: `http://127.0.0.1:8000` or `http://localhost:8000`
- Staging/Prod: use the backend base URL (e.g. `https://your-api.example.com`)

---

## 5. Auth-related endpoints

| Method | Endpoint | Auth required | Description |
|--------|----------|---------------|-------------|
| GET | `/api/v1/auth/me` | Yes | Returns current user `id`, `email`, `role`. Use to verify token and get user info. |

**Response (200):**
```json
{
  "id": "uuid-from-supabase",
  "email": "user@example.com",
  "role": "authenticated"
}
```

---

## 6. Protected vs public endpoints

- **Protected:** Require `Authorization: Bearer <access_token>`. If missing or invalid, backend returns **401** or **403**.
- **Public:** No auth (e.g. `/`, `/health`). Patient endpoints may be protected; confirm with backend.

Assume **all `/api/v1/...` routes except `/health` and `/`** require auth unless you’re told otherwise.

---

## 7. Error responses (auth)

| Status | Meaning | What to do (FE) |
|--------|--------|------------------|
| **401** | Missing, expired, or invalid token | Clear local auth state, redirect to login. If you use refresh: try `supabase.auth.refreshSession()`, then retry with new `access_token`. |
| **403** | Valid token but wrong role (e.g. anon) | User not allowed; redirect to login or show “access denied”. |
| **503** | Backend auth not configured | Backend missing `SUPABASE_JWT_SECRET`; show generic error / contact support. |

**Error body shape:**
```json
{
  "detail": "Token expired"
}
```
or
```json
{
  "detail": "Missing or invalid Authorization header"
}
```

---

## 8. Flow summary

1. User signs in (or up) with Supabase: `signInWithPassword` / `signUp`.
2. Store or read `session.access_token` (and optionally `refresh_token` / `expires_at`).
3. On every API request, set header: `Authorization: Bearer <access_token>`.
4. On app load, call `getSession()` and, if present, use `session.access_token` for API calls.
5. On **401** from API: refresh session with `refreshSession()`; if still 401, sign out and redirect to login.
6. Use `GET /api/v1/auth/me` to verify token and get `id` / `email` for the current user.

---

## 9. Backend env (for reference)

Backend needs **SUPABASE_JWT_SECRET** (Supabase Dashboard → Project Settings → API → JWT Secret) to verify tokens. No need to expose this on the frontend.

---

## 10. CORS

Backend allows credentials and common headers. If you use a custom header (e.g. `X-Client`) or specific origins, coordinate with backend to allow them.
