export const ENV = {
  AUTH_API_URL: import.meta.env.VITE_AUTH_API_URL || '/api/v1/auth',
  TICKET_API_URL: import.meta.env.VITE_TICKET_API_URL || '/tickets',
  APP_NAME: import.meta.env.VITE_APP_NAME || 'Ticketing Genie',
} as const;
