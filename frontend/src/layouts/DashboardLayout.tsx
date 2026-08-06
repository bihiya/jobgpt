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
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import { useAppDispatch, useAppSelector } from '../store/hooks';
import { logout } from '../store/slices/authSlice';
import { toggleDarkMode, toggleSidebar } from '../store/slices/uiSlice';

const drawerWidth = 260;

const nav = [
  { label: 'Dashboard', path: '/dashboard', icon: <Dashboard /> },
  { label: 'Jobs', path: '/jobs', icon: <Work /> },
  { label: 'Tracked', path: '/jobs/tracked', icon: <Work /> },
  { label: 'Applied', path: '/jobs/applied', icon: <Work /> },
  { label: 'History', path: '/jobs/history', icon: <History /> },
  { label: 'Job Portals', path: '/job-portals', icon: <Hub /> },
  { label: 'Companies', path: '/companies', icon: <Business /> },
  { label: 'Automation', path: '/automation', icon: <SmartToy /> },
  { label: 'Reports', path: '/reports', icon: <Assessment /> },
  { label: 'Profile', path: '/profile', icon: <Person /> },
  { label: 'Settings', path: '/settings', icon: <Settings /> },
];

export default function DashboardLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const dispatch = useAppDispatch();
  const darkMode = useAppSelector((s) => s.ui.darkMode);
  const sidebarOpen = useAppSelector((s) => s.ui.sidebarOpen);
  const user = useAppSelector((s) => s.auth.user);
  const isMobile = useMediaQuery('(max-width:900px)');

  const drawer = (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <Box sx={{ px: 2.5, py: 2.5 }}>
        <Typography variant="h5" sx={{ letterSpacing: '-0.03em' }}>
          JobPilot AI
        </Typography>
        <Typography variant="body2" color="text.secondary">
          {user?.full_name || 'Automation workspace'}
        </Typography>
      </Box>
      <List sx={{ px: 1, flex: 1 }}>
        {nav.map((item) => (
          <ListItemButton
            key={item.path}
            selected={location.pathname === item.path}
            onClick={() => navigate(item.path)}
            sx={{ borderRadius: 2, mb: 0.5 }}
          >
            <ListItemIcon sx={{ minWidth: 40 }}>{item.icon}</ListItemIcon>
            <ListItemText primary={item.label} />
          </ListItemButton>
        ))}
      </List>
      <List sx={{ px: 1, pb: 2 }}>
        <ListItemButton
          onClick={() => {
            localStorage.removeItem('refresh_token');
            dispatch(logout());
            navigate('/login');
          }}
          sx={{ borderRadius: 2 }}
        >
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
          <IconButton edge="start" onClick={() => dispatch(toggleSidebar())}>
            <MenuIcon />
          </IconButton>
          <Typography sx={{ flex: 1, fontWeight: 600 }}>
            {nav.find((n) => n.path === location.pathname)?.label || 'JobPilot AI'}
          </Typography>
          <IconButton onClick={() => dispatch(toggleDarkMode())}>
            {darkMode ? <LightMode /> : <DarkMode />}
          </IconButton>
        </Toolbar>
      </AppBar>

      <Drawer
        variant={isMobile ? 'temporary' : 'persistent'}
        open={sidebarOpen}
        onClose={() => dispatch(toggleSidebar())}
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
