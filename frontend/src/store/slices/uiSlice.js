import { createSlice } from '@reduxjs/toolkit';

const initialState = {
  darkMode: false,
  sidebarOpen: true,
  snackbar: { open: false, message: '', severity: 'info' },
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
      state.snackbar = {
        open: true,
        message: action.payload.message,
        severity: action.payload.severity || 'info',
      };
    },
    hideSnackbar(state) {
      state.snackbar.open = false;
    },
  },
});

export const {
  toggleDarkMode,
  setDarkMode,
  toggleSidebar,
  showSnackbar,
  hideSnackbar,
} = uiSlice.actions;

export default uiSlice.reducer;
