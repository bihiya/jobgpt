import { alpha, createTheme, type ThemeOptions } from '@mui/material/styles';

/** Snabbit-inspired hot pink system */
const pink = '#FF3D8A';
const magenta = '#E2186F';
const rose = '#FF7AB5';
const blush = '#FFF1F6';
const cream = '#FFF8FB';
const ink = '#1C0A14';
const plum = '#4A1230';
const coral = '#FF5C6B';
const gold = '#F5B942';
const displayFont = '"Sora", "Sofia Sans", "Segoe UI", sans-serif';
const bodyFont = '"Sofia Sans", "Segoe UI", sans-serif';
const spring = 'cubic-bezier(0.34, 1.45, 0.64, 1)';
const smooth = 'cubic-bezier(0.22, 1, 0.36, 1)';

const motionKeyframes = {
  '@keyframes jp-fade-up': {
    from: { opacity: 0, transform: 'translateY(18px)' },
    to: { opacity: 1, transform: 'translateY(0)' },
  },
  '@keyframes jp-fade-in': {
    from: { opacity: 0 },
    to: { opacity: 1 },
  },
  '@keyframes jp-scale-in': {
    from: { opacity: 0, transform: 'scale(0.94)' },
    to: { opacity: 1, transform: 'scale(1)' },
  },
  '@keyframes jp-shimmer': {
    '0%': { backgroundPosition: '200% 0' },
    '100%': { backgroundPosition: '-200% 0' },
  },
  '@keyframes jp-float': {
    '0%, 100%': { transform: 'translateY(0) rotate(0deg)' },
    '50%': { transform: 'translateY(-10px) rotate(3deg)' },
  },
  '@keyframes jp-float-slow': {
    '0%, 100%': { transform: 'translate3d(0, 0, 0) scale(1)' },
    '50%': { transform: 'translate3d(12px, -18px, 0) scale(1.06)' },
  },
  '@keyframes jp-gradient-shift': {
    '0%, 100%': { backgroundPosition: '0% 50%' },
    '50%': { backgroundPosition: '100% 50%' },
  },
  '@keyframes jp-pulse-soft': {
    '0%, 100%': { boxShadow: `0 0 0 0 ${alpha(pink, 0.45)}` },
    '50%': { boxShadow: `0 0 0 12px ${alpha(pink, 0)}` },
  },
  '@keyframes jp-step-in': {
    from: { opacity: 0, transform: 'translateY(12px)' },
    to: { opacity: 1, transform: 'translateY(0)' },
  },
  '@keyframes jp-live-sweep': {
    '0%': { transform: 'translateX(-120%)' },
    '100%': { transform: 'translateX(220%)' },
  },
  '@keyframes jp-shine': {
    '0%': { transform: 'translateX(-140%) skewX(-18deg)' },
    '100%': { transform: 'translateX(240%) skewX(-18deg)' },
  },
  '@keyframes jp-blob': {
    '0%, 100%': { borderRadius: '42% 58% 62% 38% / 46% 42% 58% 54%' },
    '33%': { borderRadius: '58% 42% 38% 62% / 42% 58% 42% 58%' },
    '66%': { borderRadius: '38% 62% 54% 46% / 58% 38% 62% 42%' },
  },
  '@keyframes jp-spin-slow': {
    from: { transform: 'rotate(0deg)' },
    to: { transform: 'rotate(360deg)' },
  },
  '@keyframes toastPop': {
    from: { opacity: 0, transform: 'translateY(14px) scale(0.94)' },
    to: { opacity: 1, transform: 'translateY(0) scale(1)' },
  },
};

const sharedComponents = (mode: 'light' | 'dark'): ThemeOptions['components'] => ({
  MuiCssBaseline: {
    styleOverrides: {
      ':root': {
        '--jp-pink': pink,
        '--jp-magenta': magenta,
        '--jp-rose': rose,
        '--jp-blush': blush,
        '--jp-ink': ink,
        '--jp-spring': spring,
      },
      html: { scrollBehavior: 'smooth' },
      '::-webkit-scrollbar': { width: 10, height: 10 },
      '::-webkit-scrollbar-thumb': {
        background: alpha(pink, mode === 'light' ? 0.45 : 0.55),
        borderRadius: 99,
        border: '2px solid transparent',
        backgroundClip: 'padding-box',
      },
      '::-webkit-scrollbar-track': {
        background: mode === 'light' ? blush : '#160810',
      },
      body: {
        minHeight: '100%',
        backgroundAttachment: 'fixed',
        backgroundImage:
          mode === 'light'
            ? `
              radial-gradient(ellipse 90% 55% at -10% -15%, ${alpha(pink, 0.28)}, transparent 58%),
              radial-gradient(ellipse 70% 45% at 110% -5%, ${alpha(rose, 0.32)}, transparent 52%),
              radial-gradient(ellipse 55% 35% at 80% 110%, ${alpha(magenta, 0.16)}, transparent 55%),
              linear-gradient(180deg, ${cream} 0%, ${blush} 48%, #FFE8F2 100%)
            `
            : `
              radial-gradient(ellipse 80% 50% at 0% 0%, ${alpha(pink, 0.28)}, transparent 55%),
              radial-gradient(ellipse 60% 40% at 100% 8%, ${alpha(magenta, 0.22)}, transparent 50%),
              linear-gradient(180deg, #14080E 0%, #1A0A14 50%, #221018 100%)
            `,
      },
      ...motionKeyframes,
      '.jp-page': {
        animation: `jp-fade-up 0.55s ${smooth} both`,
      },
      '.jp-stagger > *': {
        animation: `jp-fade-up 0.58s ${smooth} both`,
      },
      '.jp-stagger > *:nth-of-type(1)': { animationDelay: '0.04s' },
      '.jp-stagger > *:nth-of-type(2)': { animationDelay: '0.1s' },
      '.jp-stagger > *:nth-of-type(3)': { animationDelay: '0.16s' },
      '.jp-stagger > *:nth-of-type(4)': { animationDelay: '0.22s' },
      '.jp-stagger > *:nth-of-type(5)': { animationDelay: '0.28s' },
      '.jp-stagger > *:nth-of-type(6)': { animationDelay: '0.34s' },
      '.jp-shine': {
        position: 'relative',
        overflow: 'hidden',
        '&::after': {
          content: '""',
          position: 'absolute',
          inset: 0,
          width: '40%',
          background: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.35), transparent)',
          animation: 'jp-shine 2.8s ease-in-out infinite',
          pointerEvents: 'none',
        },
      },
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
        borderRadius: 999,
        paddingInline: 20,
        minHeight: 42,
        position: 'relative',
        transition: `transform 0.22s ${spring}, box-shadow 0.22s ${smooth}, background 0.22s ease`,
        '&:hover': { transform: 'translateY(-2px)' },
        '&:active': { transform: 'translateY(0) scale(0.98)' },
      },
      containedPrimary: {
        background: `linear-gradient(135deg, ${pink} 0%, ${magenta} 55%, #FF6BA8 100%)`,
        backgroundSize: '200% 200%',
        animation: 'jp-gradient-shift 9s ease infinite',
        boxShadow: `0 10px 24px ${alpha(magenta, mode === 'light' ? 0.32 : 0.5)}`,
        overflow: 'hidden',
        '&::after': {
          content: '""',
          position: 'absolute',
          inset: 0,
          width: '38%',
          background: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.28), transparent)',
          animation: 'jp-shine 2.8s ease-in-out infinite',
          pointerEvents: 'none',
        },
        '&:hover': {
          boxShadow: `0 16px 32px ${alpha(magenta, mode === 'light' ? 0.42 : 0.6)}`,
        },
      },
      containedSecondary: {
        background: `linear-gradient(135deg, ${rose} 0%, ${pink} 100%)`,
        color: '#fff',
      },
      outlined: {
        borderWidth: 1.5,
        '&:hover': { borderWidth: 1.5, background: alpha(pink, 0.08) },
      },
      sizeLarge: {
        minHeight: 48,
        paddingInline: 26,
        fontSize: '1.02rem',
      },
    },
  },
  MuiPaper: {
    styleOverrides: {
      root: {
        backgroundImage: 'none',
        transition: `box-shadow 0.28s ${smooth}, transform 0.28s ${smooth}`,
      },
      elevation1: {
        boxShadow: `0 8px 28px ${alpha(magenta, 0.1)}`,
        border: `1px solid ${alpha(mode === 'light' ? pink : '#fff', 0.12)}`,
      },
    },
  },
  MuiCard: {
    styleOverrides: {
      root: {
        borderRadius: 24,
        border: `1px solid ${alpha(mode === 'light' ? pink : '#fff', 0.14)}`,
        background:
          mode === 'light'
            ? `linear-gradient(165deg, #FFFFFF 0%, ${alpha(pink, 0.06)} 100%)`
            : `linear-gradient(165deg, #251018 0%, ${alpha(pink, 0.16)} 100%)`,
        transition: `transform 0.28s ${spring}, box-shadow 0.28s ${smooth}, border-color 0.28s ease`,
        '&:hover': {
          transform: 'translateY(-5px)',
          boxShadow: `0 20px 40px ${alpha(magenta, 0.16)}`,
          borderColor: alpha(pink, 0.45),
        },
      },
    },
  },
  MuiAppBar: {
    styleOverrides: {
      root: {
        background: alpha(mode === 'light' ? cream : '#160810', 0.72),
        backdropFilter: 'blur(18px) saturate(1.35)',
        borderBottom: `1px solid ${alpha(mode === 'light' ? pink : '#fff', 0.12)}`,
      },
    },
  },
  MuiDrawer: {
    styleOverrides: {
      paper: {
        borderRight: 'none',
        background:
          mode === 'light'
            ? `linear-gradient(185deg, ${pink} 0%, ${magenta} 48%, ${plum} 100%)`
            : `linear-gradient(185deg, #1A0810 0%, #3A1024 48%, ${plum} 100%)`,
        color: '#FFF5F9',
      },
    },
  },
  MuiListItemButton: {
    styleOverrides: {
      root: {
        borderRadius: 16,
        marginInline: 8,
        marginBlock: 3,
        transition: `background 0.2s ease, transform 0.22s ${spring}`,
        '&.Mui-selected': {
          background: alpha('#fff', 0.2),
          boxShadow: `0 8px 18px ${alpha('#000', 0.12)}`,
          '&:hover': { background: alpha('#fff', 0.26) },
        },
        '&:hover': {
          background: alpha('#fff', 0.12),
          transform: 'translateX(4px)',
        },
      },
    },
  },
  MuiListItemIcon: {
    styleOverrides: {
      root: { color: 'inherit', opacity: 0.95 },
    },
  },
  MuiChip: {
    styleOverrides: {
      root: {
        fontWeight: 700,
        borderRadius: 999,
        transition: `transform 0.18s ${spring}`,
        '&:hover': { transform: 'scale(1.05)' },
      },
    },
  },
  MuiTextField: {
    defaultProps: { size: 'small' },
    styleOverrides: {
      root: {
        '& .MuiOutlinedInput-root': {
          borderRadius: 16,
          transition: 'box-shadow 0.2s ease',
          '&.Mui-focused': {
            boxShadow: `0 0 0 4px ${alpha(pink, 0.22)}`,
          },
        },
      },
    },
  },
  MuiDialog: {
    styleOverrides: {
      paper: {
        borderRadius: 24,
        border: `1px solid ${alpha(pink, 0.16)}`,
        animation: `jp-scale-in 0.35s ${smooth}`,
      },
    },
  },
  MuiTooltip: {
    styleOverrides: {
      tooltip: {
        borderRadius: 12,
        background: plum,
        fontWeight: 600,
      },
    },
  },
  MuiSwitch: {
    styleOverrides: {
      switchBase: {
        '&.Mui-checked': {
          color: pink,
        },
      },
    },
  },
  MuiAlert: {
    styleOverrides: {
      root: { borderRadius: 16 },
      filledSuccess: {
        background: `linear-gradient(135deg, ${pink}, ${magenta})`,
      },
      filledError: {
        background: `linear-gradient(135deg, ${coral}, #D63A4A)`,
      },
      filledInfo: {
        background: `linear-gradient(135deg, ${rose}, ${pink})`,
      },
      filledWarning: {
        background: `linear-gradient(135deg, ${gold}, #E09A20)`,
      },
    },
  },
  MuiLinearProgress: {
    styleOverrides: {
      root: { borderRadius: 99, height: 8, background: alpha(pink, 0.14) },
      bar: {
        borderRadius: 99,
        background: `linear-gradient(90deg, ${pink}, ${rose}, ${magenta}, ${pink})`,
        backgroundSize: '200% 100%',
        animation: 'jp-shimmer 2s linear infinite',
      },
    },
  },
  MuiSkeleton: {
    styleOverrides: {
      root: {
        background: alpha(pink, mode === 'light' ? 0.12 : 0.22),
      },
    },
  },
  MuiTabs: {
    styleOverrides: {
      indicator: {
        height: 3,
        borderRadius: 99,
        background: `linear-gradient(90deg, ${pink}, ${magenta})`,
      },
    },
  },
});

const sharedTypography: ThemeOptions['typography'] = {
  fontFamily: bodyFont,
  h1: { fontFamily: displayFont, fontWeight: 800, letterSpacing: '-0.04em', lineHeight: 1.08 },
  h2: { fontFamily: displayFont, fontWeight: 800, letterSpacing: '-0.03em' },
  h3: { fontFamily: displayFont, fontWeight: 700, letterSpacing: '-0.03em' },
  h4: { fontFamily: displayFont, fontWeight: 700, letterSpacing: '-0.02em' },
  h5: { fontFamily: displayFont, fontWeight: 700 },
  h6: { fontFamily: displayFont, fontWeight: 650 },
  button: { textTransform: 'none', fontWeight: 800, letterSpacing: '0.01em' },
  subtitle1: { fontWeight: 650 },
};

export const lightTheme = createTheme({
  palette: {
    mode: 'light',
    primary: { main: pink, light: rose, dark: magenta, contrastText: '#FFFFFF' },
    secondary: { main: magenta, light: '#FF8FC4', dark: plum, contrastText: '#FFFFFF' },
    error: { main: coral },
    warning: { main: gold },
    info: { main: rose },
    success: { main: pink },
    background: { default: blush, paper: '#FFFFFF' },
    text: { primary: ink, secondary: '#6B3A52' },
    divider: alpha(pink, 0.16),
  },
  typography: sharedTypography,
  shape: { borderRadius: 20 },
  components: sharedComponents('light'),
});

export const darkTheme = createTheme({
  palette: {
    mode: 'dark',
    primary: { main: '#FF6BA8', light: '#FF9AC8', dark: pink, contrastText: '#1C0A14' },
    secondary: { main: rose, light: '#FFB3D4', dark: magenta, contrastText: '#1C0A14' },
    error: { main: '#FF8A96' },
    warning: { main: '#FFD166' },
    info: { main: rose },
    success: { main: '#FF6BA8' },
    background: { default: '#160810', paper: '#241018' },
    text: { primary: '#FFEAF3', secondary: '#D4A0B6' },
    divider: alpha('#fff', 0.12),
  },
  typography: sharedTypography,
  shape: { borderRadius: 20 },
  components: sharedComponents('dark'),
});
