import { Box, Stack, Typography } from '@mui/material';
import { alpha } from '@mui/material/styles';
import { memo } from 'react';

export type WeeklyStoryData = {
  headline: string;
  narrative: string;
  applied: number;
  replies: number;
  interviews: number;
  offers: number;
  highlights?: string[];
  period_label?: string;
};

function WeeklyStory({ story }: { story: WeeklyStoryData }) {
  return (
    <Box
      sx={{
        p: { xs: 2.5, md: 3.25 },
        borderRadius: 5,
        color: '#FFF8FB',
        position: 'relative',
        overflow: 'hidden',
        background: (t) =>
          `linear-gradient(125deg, ${t.palette.primary.main} 0%, ${t.palette.secondary.dark} 48%, ${alpha(
            t.palette.primary.light,
            0.92,
          )} 100%)`,
        backgroundSize: '180% 180%',
        animation: 'jp-gradient-shift 12s ease infinite',
        boxShadow: (t) => `0 18px 40px ${alpha(t.palette.primary.main, 0.28)}`,
        '&::before': {
          content: '""',
          position: 'absolute',
          width: 220,
          height: 220,
          right: -40,
          top: -60,
          borderRadius: '42% 58% 62% 38%',
          background: 'rgba(255,255,255,0.16)',
          animation: 'jp-blob 14s ease-in-out infinite, jp-float-slow 8s ease-in-out infinite',
          pointerEvents: 'none',
        },
      }}
    >
      <Typography variant="overline" sx={{ opacity: 0.85, letterSpacing: '0.12em' }}>
        {story.period_label || 'This week'}
      </Typography>
      <Typography
        variant="h4"
        sx={{
          mt: 0.5,
          mb: 1,
          letterSpacing: '-0.03em',
          position: 'relative',
        }}
      >
        {story.headline}
      </Typography>
      <Typography sx={{ opacity: 0.92, maxWidth: 720, mb: 2 }}>{story.narrative}</Typography>
      <Stack direction="row" spacing={3} flexWrap="wrap" useFlexGap>
        {[
          ['Applied', story.applied],
          ['Replies', story.replies],
          ['Interviews', story.interviews],
          ['Offers', story.offers],
        ].map(([label, value]) => (
          <Box key={String(label)}>
            <Typography variant="h5" sx={{ fontWeight: 800, lineHeight: 1 }}>
              {value}
            </Typography>
            <Typography variant="caption" sx={{ opacity: 0.8 }}>
              {label}
            </Typography>
          </Box>
        ))}
      </Stack>
    </Box>
  );
}

export default memo(WeeklyStory);
