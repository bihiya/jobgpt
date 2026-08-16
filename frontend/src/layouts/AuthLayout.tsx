import { Box, Container, Typography } from '@mui/material';
import { Outlet } from 'react-router-dom';

export default function AuthLayout() {
  return (
    <Box
      sx={{
        minHeight: '100vh',
        display: 'grid',
        placeItems: 'center',
        position: 'relative',
        overflow: 'hidden',
        px: { xs: 2, sm: 3 },
        py: { xs: 4, sm: 6 },
        background:
          'radial-gradient(1000px 500px at 8% 12%, rgba(31,166,122,0.28), transparent 55%), radial-gradient(800px 420px at 92% 78%, rgba(43,179,192,0.22), transparent 50%), radial-gradient(600px 300px at 50% 100%, rgba(11,61,46,0.12), transparent 55%), linear-gradient(160deg, #E8F5F0 0%, #DFF3EC 55%, #EAF6F1 100%)',
        '&::before': {
          content: '""',
          position: 'absolute',
          width: 280,
          height: 280,
          borderRadius: '50%',
          top: '12%',
          right: '8%',
          background: 'radial-gradient(circle, rgba(43,179,192,0.35), transparent 70%)',
          animation: 'jp-float 6s ease-in-out infinite',
          pointerEvents: 'none',
        },
        '&::after': {
          content: '""',
          position: 'absolute',
          width: 220,
          height: 220,
          borderRadius: '50%',
          bottom: '10%',
          left: '6%',
          background: 'radial-gradient(circle, rgba(31,166,122,0.3), transparent 70%)',
          animation: 'jp-float 7.5s ease-in-out infinite reverse',
          pointerEvents: 'none',
        },
      }}
    >
      <Container maxWidth="sm" className="jp-page" sx={{ position: 'relative', zIndex: 1 }}>
        <Typography
          variant="h3"
          sx={{
            mb: 1,
            textAlign: 'center',
            letterSpacing: '-0.03em',
            background: 'linear-gradient(135deg, #0B3D2E 0%, #1FA67A 55%, #2BB3C0 100%)',
            backgroundClip: 'text',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            color: '#0B3D2E',
            fontSize: { xs: '2rem', sm: '2.75rem' },
          }}
        >
          JobPilot AI
        </Typography>
        <Typography color="text.secondary" sx={{ mb: 3, textAlign: 'center' }}>
          Configure once. Apply continuously.
        </Typography>
        <Outlet />
      </Container>
    </Box>
  );
}
