import { createSlice } from '@reduxjs/toolkit';

const initialState = {
  user: null,
  accessToken: null,
  isAuthenticated: false,
  // idle → restoring (refresh_token present) → ready (guest or signed in)
  status: 'idle',
};

const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    setCredentials(state, action) {
      state.user = action.payload.user;
      state.accessToken = action.payload.accessToken;
      state.isAuthenticated = true;
      state.status = 'ready';
    },
    setAccessToken(state, action) {
      state.accessToken = action.payload;
      if (action.payload) {
        state.isAuthenticated = true;
      }
    },
    setAuthStatus(state, action) {
      state.status = action.payload;
    },
    logout(state) {
      state.user = null;
      state.accessToken = null;
      state.isAuthenticated = false;
      state.status = 'ready';
    },
  },
});

export const { setCredentials, setAccessToken, setAuthStatus, logout } = authSlice.actions;
export default authSlice.reducer;
