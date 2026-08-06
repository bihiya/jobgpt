import { CssBaseline, ThemeProvider } from '@mui/material';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Provider } from 'react-redux';
import { BrowserRouter } from 'react-router-dom';
import { PrefetchProvider } from './contexts/PrefetchContext';
import AppRouter from './routes/AppRouter';
import { useAppSelector } from './store/hooks';
import { selectDarkMode } from './store/selectors/uiSelectors';
import store from './store/store';
import { darkTheme, lightTheme } from './theme/theme';

// API response caching defaults (React Query)
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 30_000,
      gcTime: 5 * 60_000,
    },
    mutations: {
      retry: 0,
    },
  },
});

function ThemedApp() {
  const darkMode = useAppSelector(selectDarkMode);
  return (
    <ThemeProvider theme={darkMode ? darkTheme : lightTheme}>
      <CssBaseline />
      <BrowserRouter>
        <PrefetchProvider>
          <AppRouter />
        </PrefetchProvider>
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
