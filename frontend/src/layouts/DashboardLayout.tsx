import {
  AppBar,
  Box,
  Button,
  Chip,
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
  CalendarMonth,
  Checklist,
  Dashboard,
  History,
  Timeline,
  Quiz,
  ViewKanban,
  MailOutline,
  Hub,
  Logout,
  Login,
  Person,
  RocketLaunch,
  Settings,
  SmartToy,
  Work,
  DarkMode,
  LightMode,
  Menu as MenuIcon,
  Circle,
} from '@mui/icons-material';
import { alpha } from '@mui/material/styles';
import { memo, startTransition, useCallback, useMemo, type ReactNode } from 'react';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import GuestBanner from '../components/auth/GuestBanner';
import { usePrefetch } from '../contexts/PrefetchContext';
import { useRealtimeSocket } from '../hooks/useRealtimeSocket';
import { useAppDispatch, useAppSelector } from '../store/hooks';
import { selectIsAuthenticated, selectUserDisplayName } from '../store/selectors/authSelectors';
import { selectDarkMode, selectSidebarOpen } from '../store/selectors/uiSelectors';
import { logout } from '../store/slices/authSlice';
import { openLoginGate, toggleDarkMode, toggleSidebar } from '../store/slices/uiSlice';
import { useThrottleCallback } from '../hooks/useThrottleCallback';
import { useToast } from '../hooks/useToast';
import { SIDEBAR_SECTIONS, TITLE_NAV, type NavLink, type PrefetchKey } from './nav';

const drawerWidth = 268;
const navMint = '#F4FFF9';

const NAV_ICONS: Record<string, ReactNode> = {
  '/dashboard': <Dashboard />,
  '/jobs': <Work />,
  '/pipeline': <ViewKanban />,
  '/approvals': <Checklist />,
  '/automation': <SmartToy />,
  '/email': <MailOutline />,
  '/job-portals': <Hub />,
  '/companies': <Business />,
  '/questions': <Quiz />,
  '/onboarding': <RocketLaunch />,
  '/calendar': <CalendarMonth />,
  '/activity': <Timeline />,
  '/reports': <Assessment />,
  '/profile': <Person />,
  '/settings': <Settings />,
};

function pathSelected(pathname: string, item: NavLink): boolean {
  if (item.match === 'prefix') {
    if (item.path === '/jobs') {
      return pathname === '/jobs' || pathname.startsWith('/jobs/');
    }
    return pathname === item.path || pathname.startsWith(`${item.path}/`);
  }
  return pathname === item.path;
}

type NavItemProps = {
  label: string;
  path: string;
  icon: ReactNode;
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
      sx={{ py: 0.7 }}
    >
      <ListItemIcon sx={{ minWidth: 36, color: navMint }}>{icon}</ListItemIcon>
      <ListItemText
        primary={label}
        primaryTypographyProps={{
          noWrap: false,
          sx: { color: navMint, fontWeight: selected ? 700 : 600, fontSize: '0.92rem' },
        }}
      />
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
  const isAuthenticated = useAppSelector(selectIsAuthenticated);
  const isMobile = useMediaQuery('(max-width:900px)');
  const { prefetchDashboard, prefetchJobs } = usePrefetch();
  const { info } = useToast();
  const { status: liveStatus } = useRealtimeSocket(isAuthenticated);

  const liveChip = useMemo(() => {
    if (liveStatus === 'connected') {
      return { label: 'Live', color: 'success' as const };
    }
    if (liveStatus === 'polling') {
      return { label: 'Synced', color: 'success' as const };
    }
    if (liveStatus === 'connecting' || liveStatus === 'reconnecting') {
      return { label: 'Connecting', color: 'warning' as const };
    }
    return { label: 'Offline', color: 'default' as const };
  }, [liveStatus]);

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
    info('Signed out');
    navigate('/dashboard');
  }, [dispatch, info, navigate]);

  const handleSignIn = useCallback(() => {
    dispatch(
      openLoginGate({
        reason: 'Sign in to save your setup and run automation',
        redirectTo: `${location.pathname}${location.search}`,
      }),
    );
  }, [dispatch, location.pathname, location.search]);

  const prefetchMap = useMemo(
    () => ({
      dashboard: prefetchDashboard,
      jobs: prefetchJobs,
    }),
    [prefetchDashboard, prefetchJobs],
  );

  const pageTitle = useMemo(() => {
    const exact = TITLE_NAV.find((n) => n.path === location.pathname);
    if (exact) return exact.label;
    return 'JobPilot AI';
  }, [location.pathname]);

  const desktopSidebarVisible = sidebarOpen && !isMobile;
  const contentOffset = desktopSidebarVisible ? drawerWidth : 0;

  const drawer = (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column', color: navMint }}>
      <Box sx={{ px: 2.5, py: 2.25 }}>
        <Typography
          variant="h5"
          sx={{
            letterSpacing: '-0.03em',
            color: navMint,
            textShadow: `0 0 22px ${alpha('#7EE0C3', 0.4)}`,
          }}
        >
          JobPilot AI
        </Typography>
        <Typography variant="body2" sx={{ color: alpha(navMint, 0.82), mt: 0.5 }}>
          {isAuthenticated ? displayName : 'Guest explorer'}
        </Typography>
      </Box>

      <List sx={{ px: 0.5, flex: 1, overflowY: 'auto', pb: 1 }}>
        {SIDEBAR_SECTIONS.map((section) => (
          <Box key={section.label} sx={{ mb: 0.75 }}>
            <Typography
              variant="overline"
              sx={{
                display: 'block',
                px: 2.25,
                pt: 1.25,
                pb: 0.25,
                color: alpha(navMint, 0.72),
                letterSpacing: '0.14em',
                fontWeight: 700,
                fontSize: '0.68rem',
              }}
            >
              {section.label}
            </Typography>
            {section.items.map((item) => (
              <NavItem
                key={item.path}
                label={item.label}
                path={item.path}
                icon={NAV_ICONS[item.path] ?? <History />}
                selected={pathSelected(location.pathname, item)}
                onNavigate={handleNavigate}
                onPrefetch={item.prefetch ? prefetchMap[item.prefetch as PrefetchKey] : undefined}
              />
            ))}
          </Box>
        ))}
      </List>

      <List sx={{ px: 0.5, pb: 2 }}>
        {isAuthenticated ? (
          <ListItemButton onClick={handleLogout} sx={{ py: 0.7 }}>
            <ListItemIcon sx={{ minWidth: 36, color: navMint }}>
              <Logout />
            </ListItemIcon>
            <ListItemText
              primary="Logout"
              primaryTypographyProps={{ sx: { color: navMint, fontWeight: 600 } }}
            />
          </ListItemButton>
        ) : (
          <ListItemButton onClick={handleSignIn} sx={{ py: 0.7 }}>
            <ListItemIcon sx={{ minWidth: 36, color: navMint }}>
              <Login />
            </ListItemIcon>
            <ListItemText
              primary="Sign in"
              primaryTypographyProps={{ sx: { color: navMint, fontWeight: 600 } }}
            />
          </ListItemButton>
        )}
      </List>
    </Box>
  );

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh' }}>
      <AppBar
        position="fixed"
        color="transparent"
        elevation={0}
        sx={{
          width: { md: `calc(100% - ${contentOffset}px)` },
          ml: { md: `${contentOffset}px` },
          transition: 'width 0.25s ease, margin 0.25s ease',
        }}
      >
        <Toolbar sx={{ gap: 1 }}>
          <IconButton edge="start" onClick={handleToggleSidebar} aria-label="Toggle sidebar" color="inherit">
            <MenuIcon />
          </IconButton>
          <Typography
            sx={{
              flex: 1,
              fontWeight: 700,
              fontFamily: '"Fraunces", Georgia, serif',
              fontSize: { xs: '1.05rem', sm: '1.25rem' },
              color: 'text.primary',
            }}
          >
            {pageTitle}
          </Typography>
          {isAuthenticated ? (
            <Chip
              size="small"
              icon={<Circle sx={{ fontSize: '0.65rem !important' }} />}
              label={liveChip.label}
              color={liveChip.color}
              variant={liveStatus === 'connected' ? 'filled' : 'outlined'}
              sx={{
                display: { xs: 'none', sm: 'inline-flex' },
                fontWeight: 700,
                '& .MuiChip-icon': {
                  animation: liveStatus === 'connected' ? 'jp-pulse-soft 2.2s ease infinite' : 'none',
                },
              }}
            />
          ) : (
            <Chip
              size="small"
              label="Guest"
              color="info"
              variant="outlined"
              sx={{ display: { xs: 'none', sm: 'inline-flex' }, fontWeight: 700 }}
            />
          )}
          {!isAuthenticated && (
            <Button size="small" variant="contained" onClick={handleSignIn} sx={{ display: { xs: 'none', md: 'inline-flex' } }}>
              Sign in
            </Button>
          )}
          <IconButton onClick={handleToggleDark} aria-label="Toggle theme" color="inherit">
            {darkMode ? <LightMode /> : <DarkMode />}
          </IconButton>
        </Toolbar>
      </AppBar>

      <Drawer
        variant={isMobile ? 'temporary' : 'persistent'}
        open={sidebarOpen}
        onClose={handleToggleSidebar}
        slotProps={{ paper: { className: 'jp-nav-drawer' } }}
        sx={{
          width: { md: contentOffset },
          flexShrink: 0,
          transition: (theme) =>
            theme.transitions.create('width', {
              easing: theme.transitions.easing.sharp,
              duration: theme.transitions.duration.enteringScreen,
            }),
          '& .MuiDrawer-paper': {
            width: drawerWidth,
            boxSizing: 'border-box',
            overflowX: 'hidden',
            transition: (theme) =>
              theme.transitions.create('transform', {
                easing: theme.transitions.easing.sharp,
                duration: theme.transitions.duration.enteringScreen,
              }),
          },
        }}
      >
        {drawer}
      </Drawer>

      <Box
        component="main"
        sx={{
          flexGrow: 1,
          flexBasis: 0,
          p: { xs: 1.5, sm: 2, md: 3 },
          mt: 8,
          width: { xs: '100%', md: `calc(100% - ${contentOffset}px)` },
          maxWidth: '100%',
          transition: 'width 0.25s ease',
          minWidth: 0,
          background: (t) =>
            `radial-gradient(700px 260px at 100% 0%, ${alpha(t.palette.secondary.main, 0.1)}, transparent)`,
        }}
      >
        <GuestBanner />
        <Outlet key={location.pathname} />
      </Box>
    </Box>
  );
}

export default memo(DashboardLayout);
