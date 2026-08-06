import { createSelector } from '@reduxjs/toolkit';

const selectUiState = (state) => state.ui;

export const selectDarkMode = createSelector([selectUiState], (ui) => ui.darkMode);
export const selectSidebarOpen = createSelector([selectUiState], (ui) => ui.sidebarOpen);
export const selectSnackbar = createSelector([selectUiState], (ui) => ui.snackbar);
export const selectToasts = createSelector([selectUiState], (ui) => ui.toasts || []);
