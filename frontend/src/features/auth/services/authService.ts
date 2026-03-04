import api from '@/lib/axios';
import { ENV } from '@/config/env';
import type {
  AccessTokenResponse,
  LoginCredentials,
  SignupCredentials,
  SignupResponse,
  User,
} from '@/types';

const AUTH_URL = ENV.AUTH_API_URL;

export const authService = {
  async login(creds: LoginCredentials): Promise<AccessTokenResponse> {
    const { data } = await api.post<AccessTokenResponse>(`${AUTH_URL}/login`, creds);
    return data;
  },

  async signup(creds: SignupCredentials): Promise<SignupResponse> {
    const { data } = await api.post<SignupResponse>(`${AUTH_URL}/signup`, creds);
    return data;
  },

  async refresh(): Promise<AccessTokenResponse> {
    const { data } = await api.post<AccessTokenResponse>(`${AUTH_URL}/refresh`, {});
    return data;
  },

  async logout(): Promise<void> {
    await api.post(`${AUTH_URL}/logout`);
  },

  async getMe(): Promise<User> {
    const { data } = await api.get<User>(`${AUTH_URL}/me`);
    return data;
  },

  async getAgentsByLeadId(leadId: string): Promise<User[]> {
    const { data } = await api.get<User[]>(`${AUTH_URL}/leads/${leadId}/agents`);
    return data;
  },
};
