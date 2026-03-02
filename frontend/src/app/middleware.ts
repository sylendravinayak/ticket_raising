import type { Middleware } from '@reduxjs/toolkit';

export const loggerMiddleware: Middleware = (_store) => (next) => (action) => {
  if (import.meta.env.DEV) {
    console.groupCollapsed(`[Redux] ${(action as { type: string }).type}`);
    console.log('Payload:', (action as { payload?: unknown }).payload);
    console.groupEnd();
  }
  return next(action);
};
