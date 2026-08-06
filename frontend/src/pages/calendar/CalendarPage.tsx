import {
  Box,
  Button,
  Chip,
  Stack,
  Typography,
} from '@mui/material';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import dayjs from 'dayjs';
import { memo, useMemo, useState } from 'react';
import { calendarApi } from '../../api';
import PageSkeleton from '../../components/common/PageSkeleton';

function CalendarPage() {
  const [cursor, setCursor] = useState(dayjs());
  const queryClient = useQueryClient();
  const month = cursor.month() + 1;
  const year = cursor.year();

  const { data: events, isLoading } = useQuery({
    queryKey: ['calendar', year, month],
    queryFn: async () => (await calendarApi.month(month, year)).data as Array<any>,
  });

  const { data: due } = useQuery({
    queryKey: ['reminders-due'],
    queryFn: async () => (await calendarApi.dueReminders()).data as Array<any>,
  });

  const complete = useMutation({
    mutationFn: (id: string) => calendarApi.completeReminder(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reminders-due'] });
      queryClient.invalidateQueries({ queryKey: ['calendar'] });
    },
  });

  const byDay = useMemo(() => {
    const map: Record<string, any[]> = {};
    for (const event of events || []) {
      const day = dayjs(event.date).format('YYYY-MM-DD');
      map[day] = map[day] || [];
      map[day].push(event);
    }
    return map;
  }, [events]);

  const daysInMonth = cursor.daysInMonth();
  const startWeekday = cursor.startOf('month').day();

  if (isLoading) return <PageSkeleton />;

  return (
    <Stack spacing={2}>
      <Stack direction="row" justifyContent="space-between" alignItems="center">
        <Typography variant="h4">Application calendar</Typography>
        <Stack direction="row" spacing={1}>
          <Button onClick={() => setCursor((c) => c.subtract(1, 'month'))}>Prev</Button>
          <Typography sx={{ minWidth: 140, textAlign: 'center', pt: 1 }}>
            {cursor.format('MMMM YYYY')}
          </Typography>
          <Button onClick={() => setCursor((c) => c.add(1, 'month'))}>Next</Button>
        </Stack>
      </Stack>

      {!!due?.length && (
        <Box sx={{ p: 2, border: '1px solid', borderColor: 'divider', borderRadius: 2 }}>
          <Typography variant="h6" sx={{ mb: 1 }}>
            Follow-ups due
          </Typography>
          <Stack spacing={1}>
            {due.map((item) => (
              <Stack key={item.id} direction="row" spacing={1} alignItems="center">
                <Typography sx={{ flex: 1 }}>{item.title}</Typography>
                <Button size="small" onClick={() => complete.mutate(item.id)}>
                  Done
                </Button>
              </Stack>
            ))}
          </Stack>
        </Box>
      )}

      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: 'repeat(7, 1fr)',
          gap: 1,
        }}
      >
        {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map((d) => (
          <Typography key={d} variant="caption" sx={{ textAlign: 'center', fontWeight: 700 }}>
            {d}
          </Typography>
        ))}
        {Array.from({ length: startWeekday }).map((_, i) => (
          <Box key={`empty-${i}`} />
        ))}
        {Array.from({ length: daysInMonth }).map((_, i) => {
          const day = i + 1;
          const key = cursor.date(day).format('YYYY-MM-DD');
          const dayEvents = byDay[key] || [];
          return (
            <Box
              key={key}
              sx={{
                minHeight: 88,
                p: 1,
                borderRadius: 2,
                border: '1px solid',
                borderColor: 'divider',
                bgcolor: 'background.paper',
              }}
            >
              <Typography variant="caption" fontWeight={700}>
                {day}
              </Typography>
              <Stack spacing={0.5} sx={{ mt: 0.5 }}>
                {dayEvents.slice(0, 3).map((ev) => (
                  <Chip
                    key={ev.id}
                    size="small"
                    label={ev.type === 'follow_up' ? 'Follow-up' : 'Applied'}
                    color={ev.type === 'follow_up' ? 'warning' : 'success'}
                    variant="outlined"
                  />
                ))}
              </Stack>
            </Box>
          );
        })}
      </Box>
    </Stack>
  );
}

export default memo(CalendarPage);
