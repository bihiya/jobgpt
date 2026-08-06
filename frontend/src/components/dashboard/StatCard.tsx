import { Box, Typography } from '@mui/material';

type Props = {
  label: string;
  value: string | number;
  accent?: boolean;
};

export default function StatCard({ label, value, accent }: Props) {
  return (
    <Box
      sx={{
        p: 2.5,
        borderRadius: 2,
        border: '1px solid',
        borderColor: 'divider',
        bgcolor: 'background.paper',
        backgroundImage: accent
          ? 'linear-gradient(135deg, rgba(15,110,86,0.12), transparent)'
          : 'none',
      }}
    >
      <Typography variant="body2" color="text.secondary">
        {label}
      </Typography>
      <Typography variant="h4" sx={{ mt: 0.5, letterSpacing: '-0.03em' }}>
        {value}
      </Typography>
    </Box>
  );
}
