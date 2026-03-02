import { createSlice, createAsyncThunk, type PayloadAction } from '@reduxjs/toolkit';
import type { AuthState, LoginCredentials, SignupCredentials, User } from '@/types';
import { authService } from '../services/authService';

const initialState: AuthState = {
  user: null,
  accessToken: null,
  isAuthenticated: false,
  loading: false,
  error: null,
};

// ─── Thunks ──────────────────────────────────────────────

export const login = createAsyncThunk(
  'auth/login',
  async (creds: LoginCredentials, { rejectWithValue }) => {
    try {
      const tokenRes = await authService.login(creds);
      const user = await authService.getMe();
      return { accessToken: tokenRes.access_token, user };
    } catch (err: any) {
      return rejectWithValue(err.response?.data?.detail || 'Login failed');
    }
  },
);

export const signup = createAsyncThunk(
  'auth/signup',
  async (creds: SignupCredentials, { rejectWithValue }) => {
    try {
      const res = await authService.signup(creds);
      return res;
    } catch (err: any) {
      return rejectWithValue(err.response?.data?.detail || 'Signup failed');
    }
  },
);

export const refreshToken = createAsyncThunk(
  'auth/refresh',
  async (_, { rejectWithValue }) => {
    try {
      const tokenRes = await authService.refresh();
      const user = await authService.getMe();
      return { accessToken: tokenRes.access_token, user };
    } catch (err: any) {
      return rejectWithValue('Session expired');
    }
  },
);

export const logout = createAsyncThunk('auth/logout', async () => {
  try {
    await authService.logout();
  } catch {
    // swallow — cookie cleared anyway
  }
});

export const fetchMe = createAsyncThunk(
  'auth/fetchMe',
  async (_, { rejectWithValue }) => {
    try {
      return await authService.getMe();
    } catch (err: any) {
      return rejectWithValue('Could not fetch profile');
    }
  },
);

// ─── Slice ───────────────────────────────────────────────

const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    setAccessToken(state, action: PayloadAction<string>) {
      state.accessToken = action.payload;
    },
    clearAuth() {
      return initialState;
    },
    clearError(state) {
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    // LOGIN
    builder
      .addCase(login.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(login.fulfilled, (state, { payload }) => {
        state.loading = false;
        state.accessToken = payload.accessToken;
        state.user = payload.user;
        state.isAuthenticated = true;
      })
      .addCase(login.rejected, (state, { payload }) => {
        state.loading = false;
        state.error = payload as string;
      });

    // SIGNUP
    builder
      .addCase(signup.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(signup.fulfilled, (state) => {
        state.loading = false;
      })
      .addCase(signup.rejected, (state, { payload }) => {
        state.loading = false;
        state.error = payload as string;
      });

    // REFRESH
    builder
      .addCase(refreshToken.fulfilled, (state, { payload }) => {
        state.accessToken = payload.accessToken;
        state.user = payload.user;
        state.isAuthenticated = true;
        state.loading = false;
      })
      .addCase(refreshToken.rejected, () => {
        return initialState;
      });

    // LOGOUT
    builder.addCase(logout.fulfilled, () => initialState);

    // FETCH ME
    builder
      .addCase(fetchMe.fulfilled, (state, { payload }) => {
        state.user = payload;
      });
  },
});

export const { setAccessToken, clearAuth, clearError } = authSlice.actions;
export default authSlice.reducer;
