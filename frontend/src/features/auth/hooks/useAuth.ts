import { useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAppDispatch, useAppSelector } from '@/hooks/useAppDispatch';
import {
  login as loginThunk,
  signup as signupThunk,
  logout as logoutThunk,
  refreshToken,
  clearError,
} from '../slices/authSlice';
import type { LoginCredentials, SignupCredentials } from '@/types';

export function useAuth() {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const { user, isAuthenticated, loading, error, accessToken } = useAppSelector(
    (s) => s.auth,
  );

  const handleLogin = useCallback(
    async (creds: LoginCredentials) => {
      const result = await dispatch(loginThunk(creds));
      if (loginThunk.fulfilled.match(result)) {
        navigate('/dashboard');
      }
      return result;
    },
    [dispatch, navigate],
  );

  const handleSignup = useCallback(
    async (creds: SignupCredentials) => {
      const result = await dispatch(signupThunk(creds));
      if (signupThunk.fulfilled.match(result)) {
        navigate('/login');
      }
      return result;
    },
    [dispatch, navigate],
  );

  const handleLogout = useCallback(async () => {
    await dispatch(logoutThunk());
    navigate('/login');
  }, [dispatch, navigate]);

  const tryRefresh = useCallback(() => dispatch(refreshToken()), [dispatch]);

  const resetError = useCallback(() => dispatch(clearError()), [dispatch]);

  return {
    user,
    isAuthenticated,
    loading,
    error,
    accessToken,
    login: handleLogin,
    signup: handleSignup,
    logout: handleLogout,
    tryRefresh,
    resetError,
  };
}
