import { createTheme, ThemeOptions } from '@mui/material/styles';

const shared: ThemeOptions = {
  typography: {
    fontFamily: '"DM Sans", "Segoe UI", sans-serif',
    h1: { fontFamily: '"Fraunces", Georgia, serif', fontWeight: 650 },
    h2: { fontFamily: '"Fraunces", Georgia, serif', fontWeight: 650 },
    h3: { fontFamily: '"Fraunces", Georgia, serif', fontWeight: 600 },
    h4: { fontFamily: '"Fraunces", Georgia, serif', fontWeight: 600 },
    button: { textTransform: 'none', fontWeight: 600 },
  },
  shape: { borderRadius: 10 },
  components: {
    MuiButton: {
      styleOverrides: {
        root: { borderRadius: 10, paddingInline: 18 },
      },
    },
    MuiPaper: {
      defaultProps: { elevation: 0 },
    },
  },
};

export const lightTheme = createTheme({
  ...shared,
  palette: {
    mode: 'light',
    primary: { main: '#0F6E56' },
    secondary: { main: '#C15F3C' },
    background: { default: '#F3F7F5', paper: '#FFFFFF' },
    text: { primary: '#14201C', secondary: '#4A5C55' },
  },
});

export const darkTheme = createTheme({
  ...shared,
  palette: {
    mode: 'dark',
    primary: { main: '#3DDC97' },
    secondary: { main: '#F0A06A' },
    background: { default: '#0D1512', paper: '#14201C' },
    text: { primary: '#E7F2EC', secondary: '#A7B8B0' },
  },
});
