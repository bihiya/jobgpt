import { CssBaseline, ThemeProvider } from '@mui/material';
import { QueryClientProvider } from '@tanstack/react-query';
import { Provider } from 'react-redux';
import { BrowserRouter } from 'react-router-dom';
import LoginGateDialog from './components/auth/LoginGateDialog';
import SessionBootstrap from './components/auth/SessionBootstrap';
import ApiLoadingBar from './components/common/ApiLoadingBar';
import ToastHost from './components/common/ToastHost';
import { PrefetchProvider } from './contexts/PrefetchContext';
import { queryClient } from './lib/queryClient';
import AppRouter from './routes/AppRouter';
import { useAppSelector } from './store/hooks';
import { selectDarkMode } from './store/selectors/uiSelectors';
import store from './store/store';
import { darkTheme, lightTheme } from './theme/theme';

function ThemedApp() {
  const darkMode = useAppSelector(selectDarkMode);
  return (
    <ThemeProvider theme={darkMode ? darkTheme : lightTheme}>
      <CssBaseline />
      <BrowserRouter>
        <SessionBootstrap>
          <PrefetchProvider>
            <ApiLoadingBar />
            <AppRouter />
            <ToastHost />
            <LoginGateDialog />
          </PrefetchProvider>
        </SessionBootstrap>
      </BrowserRouter>
    </ThemeProvider>
  );
}

export default function App() {
  return (
    <Provider store={store}>
      <QueryClientProvider client={queryClient}>
        <ThemedApp />
      </QueryClientProvider>
    </Provider>
  );
}
