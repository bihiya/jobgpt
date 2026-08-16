import { Chip } from '@mui/material';
import { applyChannelChipColor, type ApplyChannel } from '../../lib/applyLive';

export default function ApplyChannelChip({ channel }: { channel: ApplyChannel | null | undefined }) {
  if (!channel) return null;
  return (
    <Chip
      size="small"
      color={applyChannelChipColor(channel)}
      label={channel.label}
      sx={{ fontWeight: 700 }}
    />
  );
}
