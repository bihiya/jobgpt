import { Box, Typography } from '@mui/material';
import { alpha } from '@mui/material/styles';
import { memo } from 'react';

type Props = {
  label: string;
  value: string | number;
  accent?: boolean;
  tone?: 'pink' | 'rose' | 'magenta' | 'coral' | 'teal' | 'sky' | 'forest';
};

const tones = {
  pink: { from: '#FF3D8A', to: '#FF7AB5' },
  rose: { from: '#FF7AB5', to: '#FFB3D4' },
  magenta: { from: '#E2186F', to: '#FF3D8A' },
  coral: { from: '#FF5C6B', to: '#FF8A96' },
  teal: { from: '#FF3D8A', to: '#FF7AB5' },
  sky: { from: '#FF7AB5', to: '#FFB3D4' },
  forest: { from: '#E2186F', to: '#FF3D8A' },
};

function StatCard({ label, value, accent, tone = 'pink' }: Props) {
  const colors = tones[tone];
  return (
    <Box
      sx={{
        p: { xs: 2, sm: 2.5 },
        borderRadius: 4,
        border: '1px solid',
        borderColor: 'divider',
        bgcolor: 'background.paper',
        position: 'relative',
        overflow: 'hidden',
        minHeight: 120,
        transition: 'transform 0.28s cubic-bezier(0.34, 1.45, 0.64, 1), box-shadow 0.28s ease',
        backgroundImage: accent
          ? `linear-gradient(135deg, ${alpha(colors.from, 0.18)}, ${alpha(colors.to, 0.08)})`
          : `linear-gradient(165deg, transparent, ${alpha(colors.from, 0.06)})`,
        '&:hover': {
          transform: 'translateY(-6px)',
          boxShadow: (t) => `0 18px 36px ${alpha(t.palette.primary.main, 0.16)}`,
        },
        '&::after': {
          content: '""',
          position: 'absolute',
          inset: 'auto -20% -40% auto',
          width: 130,
          height: 130,
          borderRadius: '50%',
          background: `radial-gradient(circle, ${alpha(colors.to, 0.34)}, transparent 70%)`,
          animation: 'jp-float 5.5s ease-in-out infinite',
        },
      }}
    >
      <Typography variant="body2" color="text.secondary" sx={{ position: 'relative', zIndex: 1, fontWeight: 650 }}>
        {label}
      </Typography>
      <Typography
        variant="h4"
        sx={{
          mt: 0.5,
          letterSpacing: '-0.03em',
          position: 'relative',
          zIndex: 1,
          background: `linear-gradient(135deg, ${colors.from}, ${colors.to})`,
          backgroundClip: 'text',
          WebkitBackgroundClip: 'text',
          color: accent ? 'transparent' : 'inherit',
        }}
      >
        {value}
      </Typography>
    </Box>
  );
}

export default memo(StatCard);
