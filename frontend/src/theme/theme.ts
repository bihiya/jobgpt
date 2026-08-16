import { alpha, createTheme, type ThemeOptions } from '@mui/material/styles';

const forest = '#0B3D2E';
const teal = '#1FA67A';
const sky = '#2BB3C0';
const coral = '#E85D4C';
const ink = '#0F1F1A';
const mint = '#EAF6F1';

const motionKeyframes = {
  '@keyframes jp-fade-up': {
    from: { opacity: 0, transform: 'translateY(14px)' },
    to: { opacity: 1, transform: 'translateY(0)' },
  },
  '@keyframes jp-fade-in': {
    from: { opacity: 0 },
    to: { opacity: 1 },
  },
  '@keyframes jp-scale-in': {
    from: { opacity: 0, transform: 'scale(0.96)' },
    to: { opacity: 1, transform: 'scale(1)' },
  },
  '@keyframes jp-shimmer': {
    '0%': { backgroundPosition: '200% 0' },
    '100%': { backgroundPosition: '-200% 0' },
  },
  '@keyframes jp-float': {
    '0%, 100%': { transform: 'translateY(0)' },
    '50%': { transform: 'translateY(-6px)' },
  },
  '@keyframes jp-gradient-shift': {
    '0%, 100%': { backgroundPosition: '0% 50%' },
    '50%': { backgroundPosition: '100% 50%' },
  },
  '@keyframes jp-pulse-soft': {
    '0%, 100%': { boxShadow: `0 0 0 0 ${alpha(teal, 0.35)}` },
    '50%': { boxShadow: `0 0 0 10px ${alpha(teal, 0)}` },
  },
  '@keyframes jp-step-in': {
    from: { opacity: 0, transform: 'translateY(10px)' },
    to: { opacity: 1, transform: 'translateY(0)' },
  },
  '@keyframes jp-live-sweep': {
    '0%': { transform: 'translateX(-120%)' },
    '100%': { transform: 'translateX(220%)' },
  },
  '@keyframes toastPop': {
    from: { opacity: 0, transform: 'translateY(12px) scale(0.96)' },
    to: { opacity: 1, transform: 'translateY(0) scale(1)' },
  },
};

const sharedComponents = (mode: 'light' | 'dark'): ThemeOptions['components'] => ({
  MuiCssBaseline: {
    styleOverrides: {
      ':root': {
        '--jp-forest': forest,
        '--jp-teal': teal,
        '--jp-sky': sky,
        '--jp-coral': coral,
        '--jp-ink': ink,
        '--jp-mint': mint,
      },
      html: { scrollBehavior: 'smooth' },
      body: {
        minHeight: '100%',
        backgroundAttachment: 'fixed',
        backgroundImage:
          mode === 'light'
            ? `
              radial-gradient(ellipse 80% 50% at 0% -10%, ${alpha(teal, 0.2)}, transparent 55%),
              radial-gradient(ellipse 60% 40% at 100% 0%, ${alpha(sky, 0.18)}, transparent 50%),
              radial-gradient(ellipse 50% 30% at 80% 100%, ${alpha(forest, 0.1)}, transparent 55%),
              linear-gradient(180deg, #E8F5F0 0%, ${mint} 45%, #E3F2EC 100%)
            `
            : `
              radial-gradient(ellipse 70% 45% at 0% 0%, ${alpha(teal, 0.22)}, transparent 55%),
              radial-gradient(ellipse 55% 40% at 100% 10%, ${alpha(sky, 0.14)}, transparent 50%),
              linear-gradient(180deg, #0A1411 0%, #0D1512 50%, #101C18 100%)
            `,
      },
      ...motionKeyframes,
      '.jp-page': {
        animation: 'jp-fade-up 0.45s cubic-bezier(0.22, 1, 0.36, 1) both',
      },
      '.jp-stagger > *': {
        animation: 'jp-fade-up 0.5s cubic-bezier(0.22, 1, 0.36, 1) both',
      },
      '.jp-stagger > *:nth-of-type(1)': { animationDelay: '0.04s' },
      '.jp-stagger > *:nth-of-type(2)': { animationDelay: '0.1s' },
      '.jp-stagger > *:nth-of-type(3)': { animationDelay: '0.16s' },
      '.jp-stagger > *:nth-of-type(4)': { animationDelay: '0.22s' },
      '.jp-stagger > *:nth-of-type(5)': { animationDelay: '0.28s' },
      '.jp-stagger > *:nth-of-type(6)': { animationDelay: '0.34s' },
      '@media (prefers-reduced-motion: reduce)': {
        '*, *::before, *::after': {
          animationDuration: '0.01ms !important',
          animationIterationCount: '1 !important',
          transitionDuration: '0.01ms !important',
        },
      },
    },
  },
  MuiButton: {
    defaultProps: { disableElevation: true },
    styleOverrides: {
      root: {
        borderRadius: 12,
        paddingInline: 18,
        transition: 'transform 0.2s ease, box-shadow 0.2s ease, background 0.2s ease',
        '&:hover': { transform: 'translateY(-1px)' },
        '&:active': { transform: 'translateY(0)' },
      },
      containedPrimary: {
        background: `linear-gradient(135deg, ${forest} 0%, ${teal} 55%, ${sky} 100%)`,
        backgroundSize: '200% 200%',
        animation: 'jp-gradient-shift 10s ease infinite',
        boxShadow: `0 8px 20px ${alpha(forest, mode === 'light' ? 0.25 : 0.45)}`,
        '&:hover': {
          boxShadow: `0 12px 28px ${alpha(forest, mode === 'light' ? 0.35 : 0.55)}`,
        },
      },
      containedSecondary: {
        background: `linear-gradient(135deg, ${teal} 0%, ${sky} 100%)`,
      },
      outlined: {
        borderWidth: 1.5,
        '&:hover': { borderWidth: 1.5, background: alpha(teal, 0.08) },
      },
    },
  },
  MuiPaper: {
    styleOverrides: {
      root: {
        backgroundImage: 'none',
        transition: 'box-shadow 0.25s ease, transform 0.25s ease',
      },
      elevation1: {
        boxShadow: `0 4px 20px ${alpha(forest, 0.08)}`,
        border: `1px solid ${alpha(mode === 'light' ? forest : '#fff', 0.08)}`,
      },
    },
  },
  MuiCard: {
    styleOverrides: {
      root: {
        borderRadius: 18,
        border: `1px solid ${alpha(mode === 'light' ? forest : '#fff', 0.1)}`,
        background:
          mode === 'light'
            ? `linear-gradient(165deg, #FFFFFF 0%, ${alpha(teal, 0.05)} 100%)`
            : `linear-gradient(165deg, #14201C 0%, ${alpha(teal, 0.12)} 100%)`,
        transition: 'transform 0.25s ease, box-shadow 0.25s ease, border-color 0.25s ease',
        '&:hover': {
          transform: 'translateY(-3px)',
          boxShadow: `0 16px 36px ${alpha(forest, 0.14)}`,
          borderColor: alpha(teal, 0.35),
        },
      },
    },
  },
  MuiAppBar: {
    styleOverrides: {
      root: {
        background: alpha(mode === 'light' ? '#FFFFFF' : '#0D1512', 0.9),
        color: mode === 'light' ? ink : '#E7F2EC',
        backdropFilter: 'blur(14px)',
        borderBottom: `1px solid ${alpha(mode === 'light' ? forest : '#fff', 0.08)}`,
      },
    },
  },
  MuiDrawer: {
    styleOverrides: {
      paper: {
        borderRight: 'none',
        backgroundImage: 'none',
        // Nav chrome only — job-detail and other drawers keep paper + ink contrast.
        '&.jp-nav-drawer': {
          background:
            mode === 'light'
              ? `linear-gradient(180deg, ${forest} 0%, #0E4F3A 48%, #126B4F 100%)`
              : `linear-gradient(180deg, #061510 0%, #0A2A20 50%, #0E3D2E 100%)`,
          color: '#F4FFF9',
          '& .MuiTypography-root': { color: '#F4FFF9' },
          '& .MuiListItemText-primary': {
            color: '#F4FFF9',
            fontWeight: 600,
            whiteSpace: 'normal',
          },
          '& .MuiListItemIcon-root': { color: '#F4FFF9', opacity: 0.95 },
          '& .MuiListItemButton-root': {
            borderRadius: 12,
            marginInline: 8,
            marginBlock: 2,
            color: '#F4FFF9',
            transition: 'background 0.2s ease, transform 0.2s ease',
            '&:hover': {
              background: alpha('#F4FFF9', 0.12),
              transform: 'translateX(2px)',
            },
            '&.Mui-selected': {
              background: alpha('#7EE0C3', 0.28),
              boxShadow: 'inset 3px 0 0 #7EE0C3',
              '& .MuiListItemText-primary': { fontWeight: 700 },
              '&:hover': { background: alpha('#7EE0C3', 0.36) },
            },
          },
        },
      },
    },
  },
  MuiListItemButton: {
    styleOverrides: {
      root: {
        borderRadius: 12,
        transition: 'background 0.2s ease, transform 0.2s ease',
      },
    },
  },
  MuiListItemIcon: {
    styleOverrides: {
      root: { color: 'inherit' },
    },
  },
  MuiTabs: {
    styleOverrides: {
      indicator: {
        height: 3,
        borderRadius: 3,
        background: `linear-gradient(90deg, ${teal}, ${sky})`,
      },
    },
  },
  MuiTab: {
    styleOverrides: {
      root: {
        fontWeight: 700,
        color: mode === 'light' ? '#4A635A' : '#A7B8B0',
        '&.Mui-selected': {
          color: mode === 'light' ? forest : '#3DDC97',
        },
      },
    },
  },
  MuiChip: {
    styleOverrides: {
      root: {
        fontWeight: 600,
        transition: 'transform 0.15s ease',
        '&:hover': { transform: 'scale(1.03)' },
      },
    },
  },
  MuiTextField: {
    defaultProps: { size: 'small' },
    styleOverrides: {
      root: {
        '& .MuiOutlinedInput-root': {
          borderRadius: 12,
          transition: 'box-shadow 0.2s ease',
          '&.Mui-focused': {
            boxShadow: `0 0 0 3px ${alpha(teal, 0.22)}`,
          },
        },
      },
    },
  },
  MuiAlert: {
    styleOverrides: {
      root: { borderRadius: 14 },
      filledSuccess: {
        background: `linear-gradient(135deg, ${teal}, ${forest})`,
      },
      filledError: {
        background: `linear-gradient(135deg, ${coral}, #C43B2C)`,
      },
      filledInfo: {
        background: `linear-gradient(135deg, ${sky}, #1A8A96)`,
      },
      filledWarning: {
        background: 'linear-gradient(135deg, #E0A100, #C48400)',
      },
    },
  },
  MuiLinearProgress: {
    styleOverrides: {
      root: { borderRadius: 8, height: 8, background: alpha(forest, 0.1) },
      bar: {
        borderRadius: 8,
        background: `linear-gradient(90deg, ${teal}, ${sky}, ${teal})`,
        backgroundSize: '200% 100%',
        animation: 'jp-shimmer 2s linear infinite',
      },
    },
  },
});

const sharedTypography: ThemeOptions['typography'] = {
  fontFamily: '"DM Sans", "Segoe UI", sans-serif',
  h1: { fontFamily: '"Fraunces", Georgia, serif', fontWeight: 700, letterSpacing: '-0.03em', lineHeight: 1.1 },
  h2: { fontFamily: '"Fraunces", Georgia, serif', fontWeight: 700, letterSpacing: '-0.02em' },
  h3: { fontFamily: '"Fraunces", Georgia, serif', fontWeight: 650 },
  h4: { fontFamily: '"Fraunces", Georgia, serif', fontWeight: 650 },
  h5: { fontFamily: '"Fraunces", Georgia, serif', fontWeight: 600 },
  h6: { fontFamily: '"Fraunces", Georgia, serif', fontWeight: 600 },
  button: { textTransform: 'none', fontWeight: 700, letterSpacing: '0.01em' },
  subtitle1: { fontWeight: 600 },
};

export const lightTheme = createTheme({
  palette: {
    mode: 'light',
    primary: { main: forest, light: '#1A5C45', dark: '#06261C', contrastText: '#F4FFF9' },
    secondary: { main: teal, light: '#4BC49A', dark: '#0E7A58', contrastText: '#042018' },
    error: { main: coral },
    warning: { main: '#E0A100' },
    info: { main: sky },
    success: { main: teal },
    background: { default: mint, paper: '#FFFFFF' },
    text: { primary: ink, secondary: '#4A635A' },
    divider: alpha(forest, 0.12),
  },
  typography: sharedTypography,
  shape: { borderRadius: 16 },
  components: sharedComponents('light'),
});

export const darkTheme = createTheme({
  palette: {
    mode: 'dark',
    primary: { main: '#3DDC97', light: '#6EE7B3', dark: '#1FA67A', contrastText: '#042018' },
    secondary: { main: sky, light: '#5ECFDB', dark: '#1A8A96', contrastText: '#041416' },
    error: { main: '#F28B7E' },
    warning: { main: '#F0C14A' },
    info: { main: sky },
    success: { main: '#3DDC97' },
    background: { default: '#0D1512', paper: '#14201C' },
    text: { primary: '#E7F2EC', secondary: '#A7B8B0' },
    divider: alpha('#fff', 0.1),
  },
  typography: sharedTypography,
  shape: { borderRadius: 16 },
  components: sharedComponents('dark'),
});
