import { createSlice, nanoid } from '@reduxjs/toolkit';

const initialState = {
  darkMode: false,
  sidebarOpen: true,
  // Toast queue — newest at the end; ToastHost shows the latest
  toasts: [],
  snackbar: { open: false, message: '', severity: 'info' },
  // Guest action gate — ask for login without blocking browse
  loginGate: {
    open: false,
    reason: 'Sign in to continue',
    redirectTo: '',
  },
};

const uiSlice = createSlice({
  name: 'ui',
  initialState,
  reducers: {
    toggleDarkMode(state) {
      state.darkMode = !state.darkMode;
    },
    setDarkMode(state, action) {
      state.darkMode = action.payload;
    },
    toggleSidebar(state) {
      state.sidebarOpen = !state.sidebarOpen;
    },
    showSnackbar(state, action) {
      const toast = {
        id: nanoid(),
        message: action.payload.message,
        severity: action.payload.severity || 'info',
        duration: action.payload.duration ?? 4000,
      };
      state.toasts.push(toast);
      // keep last 3
      if (state.toasts.length > 3) state.toasts.shift();
      // backward-compatible single snackbar mirror
      state.snackbar = {
        open: true,
        message: toast.message,
        severity: toast.severity,
      };
    },
    hideSnackbar(state) {
      state.snackbar.open = false;
      if (state.toasts.length) state.toasts.pop();
    },
    dismissToast(state, action) {
      state.toasts = state.toasts.filter((t) => t.id !== action.payload);
      const last = state.toasts[state.toasts.length - 1];
      state.snackbar = last
        ? { open: true, message: last.message, severity: last.severity }
        : { open: false, message: '', severity: 'info' };
    },
    clearToasts(state) {
      state.toasts = [];
      state.snackbar = { open: false, message: '', severity: 'info' };
    },
    openLoginGate(state, action) {
      state.loginGate = {
        open: true,
        reason: action.payload?.reason || 'Sign in to continue',
        redirectTo: action.payload?.redirectTo || '',
      };
    },
    closeLoginGate(state) {
      state.loginGate.open = false;
    },
  },
});

export const {
  toggleDarkMode,
  setDarkMode,
  toggleSidebar,
  showSnackbar,
  hideSnackbar,
  dismissToast,
  clearToasts,
  openLoginGate,
  closeLoginGate,
} = uiSlice.actions;

export default uiSlice.reducer;
