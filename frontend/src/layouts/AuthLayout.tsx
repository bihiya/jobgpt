import { Box, Container, Typography } from '@mui/material';
import { alpha } from '@mui/material/styles';
import { Outlet } from 'react-router-dom';

export default function AuthLayout() {
  return (
    <Box
      sx={(t) => ({
        minHeight: '100vh',
        display: 'grid',
        placeItems: 'center',
        position: 'relative',
        overflow: 'hidden',
        px: { xs: 2, sm: 3 },
        py: { xs: 4, sm: 6 },
        background:
          t.palette.mode === 'light'
            ? `radial-gradient(1000px 520px at 6% 8%, ${alpha(t.palette.primary.main, 0.32)}, transparent 55%), radial-gradient(820px 440px at 94% 82%, ${alpha(t.palette.secondary.main, 0.22)}, transparent 52%), linear-gradient(160deg, #FFF8FB 0%, #FFF1F6 50%, #FFE4F0 100%)`
            : `radial-gradient(1000px 520px at 6% 8%, ${alpha(t.palette.primary.main, 0.28)}, transparent 55%), radial-gradient(820px 440px at 94% 82%, ${alpha(t.palette.secondary.main, 0.18)}, transparent 52%), linear-gradient(160deg, #160810 0%, #1A0A14 55%, #221018 100%)`,
        '&::before': {
          content: '""',
          position: 'absolute',
          width: 320,
          height: 320,
          top: '8%',
          right: '4%',
          background: `radial-gradient(circle, ${alpha(t.palette.primary.main, 0.42)}, transparent 70%)`,
          animation: 'jp-float 6.5s ease-in-out infinite, jp-blob 12s ease-in-out infinite',
          pointerEvents: 'none',
        },
        '&::after': {
          content: '""',
          position: 'absolute',
          width: 240,
          height: 240,
          bottom: '8%',
          left: '4%',
          background: `radial-gradient(circle, ${alpha(t.palette.secondary.main, 0.34)}, transparent 70%)`,
          animation: 'jp-float 8s ease-in-out infinite reverse, jp-blob 14s ease-in-out infinite',
          pointerEvents: 'none',
        },
      })}
    >
      <Container maxWidth="sm" className="jp-page" sx={{ position: 'relative', zIndex: 1 }}>
        <Typography
          variant="h3"
          sx={{
            mb: 1,
            textAlign: 'center',
            letterSpacing: '-0.04em',
            background: 'linear-gradient(135deg, #FF3D8A 0%, #E2186F 50%, #FF7AB5 100%)',
            backgroundClip: 'text',
            WebkitBackgroundClip: 'text',
            color: 'transparent',
            fontSize: { xs: '2.05rem', sm: '2.85rem' },
          }}
        >
          JobPilot AI
        </Typography>
        <Typography color="text.secondary" sx={{ mb: 3, textAlign: 'center', fontWeight: 600 }}>
          Configure once. Apply continuously.
        </Typography>
        <Outlet />
      </Container>
    </Box>
  );
}
