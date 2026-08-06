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
        p: { xs: 2.5, md: 3 },
        borderRadius: 4,
        color: '#F4FFF9',
        background: (t) =>
          `linear-gradient(120deg, ${t.palette.primary.dark} 0%, ${t.palette.secondary.dark} 55%, ${alpha(
            t.palette.info.main,
            0.85,
          )} 100%)`,
        backgroundSize: '180% 180%',
        animation: 'jp-gradient-shift 12s ease infinite',
      }}
    >
      <Typography variant="overline" sx={{ opacity: 0.85, letterSpacing: '0.12em' }}>
        {story.period_label || 'This week'}
      </Typography>
      <Typography
        variant="h4"
        sx={{
          fontFamily: '"Fraunces", Georgia, serif',
          mt: 0.5,
          mb: 1,
          letterSpacing: '-0.03em',
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
