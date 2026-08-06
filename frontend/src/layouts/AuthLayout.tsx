import { Box, Container, Typography } from '@mui/material';
import { Outlet } from 'react-router-dom';

export default function AuthLayout() {
  return (
    <Box
      sx={{
        minHeight: '100vh',
        display: 'grid',
        placeItems: 'center',
        background:
          'radial-gradient(1200px 600px at 10% 10%, rgba(15,110,86,0.18), transparent), radial-gradient(900px 500px at 90% 80%, rgba(193,95,60,0.16), transparent), linear-gradient(160deg, #F3F7F5 0%, #E7F0EB 100%)',
        px: 2,
      }}
    >
      <Container maxWidth="sm">
        <Typography
          variant="h3"
          sx={{ mb: 1, textAlign: 'center', letterSpacing: '-0.03em' }}
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
