import {
  AppBar,
  Box,
  Drawer,
  IconButton,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Toolbar,
  Typography,
  useMediaQuery,
} from '@mui/material';
import {
  Assessment,
  Business,
  Dashboard,
  History,
  Hub,
  Logout,
  Person,
  Settings,
  SmartToy,
  Work,
  DarkMode,
  LightMode,
  Menu as MenuIcon,
} from '@mui/icons-material';
import { memo, startTransition, useCallback, useMemo } from 'react';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import { usePrefetch } from '../contexts/PrefetchContext';
import { useAppDispatch, useAppSelector } from '../store/hooks';
import { selectUserDisplayName } from '../store/selectors/authSelectors';
import { selectDarkMode, selectSidebarOpen } from '../store/selectors/uiSelectors';
import { logout } from '../store/slices/authSlice';
import { toggleDarkMode, toggleSidebar } from '../store/slices/uiSlice';
import { useThrottleCallback } from '../hooks/useThrottleCallback';

const drawerWidth = 260;

const NAV_ITEMS = [
  { label: 'Dashboard', path: '/dashboard', icon: <Dashboard />, prefetch: 'dashboard' as const },
  { label: 'Jobs', path: '/jobs', icon: <Work />, prefetch: 'jobs' as const },
  { label: 'Tracked', path: '/jobs/tracked', icon: <Work /> },
  { label: 'Applied', path: '/jobs/applied', icon: <Work /> },
  { label: 'History', path: '/jobs/history', icon: <History /> },
  { label: 'Job Portals', path: '/job-portals', icon: <Hub /> },
  { label: 'Companies', path: '/companies', icon: <Business /> },
  { label: 'Automation', path: '/automation', icon: <SmartToy /> },
  { label: 'Reports', path: '/reports', icon: <Assessment />, prefetch: 'dashboard' as const },
  { label: 'Profile', path: '/profile', icon: <Person /> },
  { label: 'Settings', path: '/settings', icon: <Settings /> },
];

type NavItemProps = {
  label: string;
  path: string;
  icon: React.ReactNode;
  selected: boolean;
  onNavigate: (path: string) => void;
  onPrefetch?: () => void;
};

const NavItem = memo(function NavItem({
  label,
  path,
  icon,
  selected,
  onNavigate,
  onPrefetch,
}: NavItemProps) {
  const handleClick = useCallback(() => onNavigate(path), [onNavigate, path]);
  return (
    <ListItemButton
      selected={selected}
      onClick={handleClick}
      onMouseEnter={onPrefetch}
      onFocus={onPrefetch}
      sx={{ borderRadius: 2, mb: 0.5 }}
    >
      <ListItemIcon sx={{ minWidth: 40 }}>{icon}</ListItemIcon>
      <ListItemText primary={label} />
    </ListItemButton>
  );
});

function DashboardLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const dispatch = useAppDispatch();
  const darkMode = useAppSelector(selectDarkMode);
  const sidebarOpen = useAppSelector(selectSidebarOpen);
  const displayName = useAppSelector(selectUserDisplayName);
  const isMobile = useMediaQuery('(max-width:900px)');
  const { prefetchDashboard, prefetchJobs } = usePrefetch();

  const handleNavigate = useCallback(
    (path: string) => {
      startTransition(() => navigate(path));
      if (isMobile) dispatch(toggleSidebar());
    },
    [navigate, isMobile, dispatch],
  );

  const handleToggleSidebar = useCallback(() => dispatch(toggleSidebar()), [dispatch]);
  const handleToggleDark = useThrottleCallback(() => dispatch(toggleDarkMode()), 300);

  const handleLogout = useCallback(() => {
    localStorage.removeItem('refresh_token');
    dispatch(logout());
    navigate('/login');
  }, [dispatch, navigate]);

  const prefetchMap = useMemo(
    () => ({
      dashboard: prefetchDashboard,
      jobs: prefetchJobs,
    }),
    [prefetchDashboard, prefetchJobs],
  );

  const pageTitle = useMemo(
    () => NAV_ITEMS.find((n) => n.path === location.pathname)?.label || 'JobPilot AI',
    [location.pathname],
  );

  const drawer = (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <Box sx={{ px: 2.5, py: 2.5 }}>
        <Typography variant="h5" sx={{ letterSpacing: '-0.03em' }}>
          JobPilot AI
        </Typography>
        <Typography variant="body2" color="text.secondary">
          {displayName}
        </Typography>
      </Box>
      <List sx={{ px: 1, flex: 1 }}>
        {NAV_ITEMS.map((item) => (
          <NavItem
            key={item.path}
            label={item.label}
            path={item.path}
            icon={item.icon}
            selected={location.pathname === item.path}
            onNavigate={handleNavigate}
            onPrefetch={item.prefetch ? prefetchMap[item.prefetch] : undefined}
          />
        ))}
      </List>
      <List sx={{ px: 1, pb: 2 }}>
        <ListItemButton onClick={handleLogout} sx={{ borderRadius: 2 }}>
          <ListItemIcon sx={{ minWidth: 40 }}>
            <Logout />
          </ListItemIcon>
          <ListItemText primary="Logout" />
        </ListItemButton>
      </List>
    </Box>
  );

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh' }}>
      <AppBar
        position="fixed"
        color="transparent"
        sx={{
          backdropFilter: 'blur(10px)',
          borderBottom: '1px solid',
          borderColor: 'divider',
          width: { md: `calc(100% - ${sidebarOpen ? drawerWidth : 0}px)` },
          ml: { md: sidebarOpen ? `${drawerWidth}px` : 0 },
        }}
      >
        <Toolbar>
          <IconButton edge="start" onClick={handleToggleSidebar} aria-label="Toggle sidebar">
            <MenuIcon />
          </IconButton>
          <Typography sx={{ flex: 1, fontWeight: 600 }}>{pageTitle}</Typography>
          <IconButton onClick={handleToggleDark} aria-label="Toggle theme">
            {darkMode ? <LightMode /> : <DarkMode />}
          </IconButton>
        </Toolbar>
      </AppBar>

      <Drawer
        variant={isMobile ? 'temporary' : 'persistent'}
        open={sidebarOpen}
        onClose={handleToggleSidebar}
        sx={{
          width: drawerWidth,
          flexShrink: 0,
          '& .MuiDrawer-paper': {
            width: drawerWidth,
            boxSizing: 'border-box',
            borderRight: '1px solid',
            borderColor: 'divider',
            background:
              'linear-gradient(180deg, rgba(15,110,86,0.08), transparent 40%), var(--mui-palette-background-paper)',
          },
        }}
      >
        {drawer}
      </Drawer>

      <Box
        component="main"
        sx={{
          flexGrow: 1,
          p: { xs: 2, md: 3 },
          mt: 8,
          width: { md: `calc(100% - ${sidebarOpen ? drawerWidth : 0}px)` },
          background:
            'radial-gradient(800px 300px at 100% 0%, rgba(15,110,86,0.08), transparent)',
        }}
      >
        <Outlet />
      </Box>
    </Box>
  );
}

export default memo(DashboardLayout);
