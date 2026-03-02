import { combineReducers } from '@reduxjs/toolkit';
import authReducer from '@/features/auth/slices/authSlice';
import ticketReducer from '@/features/tickets/slices/ticketSlice';

const rootReducer = combineReducers({
  auth: authReducer,
  tickets: ticketReducer,
});

export type RootState = ReturnType<typeof rootReducer>;
export default rootReducer;
