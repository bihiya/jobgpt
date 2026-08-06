import { useQueryClient } from '@tanstack/react-query';
import { useEffect, useRef, useState } from 'react';
import {
  getRealtimeUrl,
  queryKeysForEvent,
  shouldToastEvent,
  type RealtimeEvent,
} from '../lib/realtime';
import { useAppSelector } from '../store/hooks';
import { useToast } from './useToast';

export type RealtimeStatus = 'idle' | 'connecting' | 'connected' | 'reconnecting' | 'disconnected';

/**
 * Authenticated WebSocket subscription for live job/approval/automation updates.
 * Invalidates React Query caches and shows toasts for notable events.
 */
export function useRealtimeSocket(enabled = true) {
  const accessToken = useAppSelector((s) => s.auth.accessToken);
  const isAuthenticated = useAppSelector((s) => s.auth.isAuthenticated);
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const [status, setStatus] = useState<RealtimeStatus>('idle');
  const [lastEvent, setLastEvent] = useState<RealtimeEvent | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const retryRef = useRef(0);
  const timerRef = useRef<number | null>(null);
  const pingRef = useRef<number | null>(null);

  useEffect(() => {
    if (!enabled || !isAuthenticated || !accessToken) {
      setStatus('idle');
      return undefined;
    }

    let closed = false;

    const clearTimers = () => {
      if (timerRef.current) {
        window.clearTimeout(timerRef.current);
        timerRef.current = null;
      }
      if (pingRef.current) {
        window.clearInterval(pingRef.current);
        pingRef.current = null;
      }
    };

    const connect = () => {
      if (closed) return;
      clearTimers();
      setStatus(retryRef.current > 0 ? 'reconnecting' : 'connecting');
      const url = getRealtimeUrl(accessToken);
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        retryRef.current = 0;
        setStatus('connected');
        pingRef.current = window.setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'ping' }));
          }
        }, 25_000);
      };

      ws.onmessage = (ev) => {
        try {
          const payload = JSON.parse(String(ev.data)) as RealtimeEvent;
          if (!payload?.event || payload.event === 'pong') return;
          setLastEvent(payload);

          for (const key of queryKeysForEvent(payload.event)) {
            void queryClient.invalidateQueries({ queryKey: key });
          }

          if (
            shouldToastEvent(payload.event) &&
            (payload.title || payload.body)
          ) {
            toast(
              payload.body || payload.title || payload.event,
              payload.severity || 'info',
              payload.severity === 'error' ? 6000 : 4000,
            );
          }
        } catch {
          /* ignore malformed frames */
        }
      };

      ws.onerror = () => {
        /* onclose handles reconnect */
      };

      ws.onclose = () => {
        clearTimers();
        wsRef.current = null;
        if (closed) return;
        setStatus('reconnecting');
        const delay = Math.min(1000 * 2 ** retryRef.current, 15_000);
        retryRef.current += 1;
        timerRef.current = window.setTimeout(connect, delay);
      };
    };

    connect();

    return () => {
      closed = true;
      clearTimers();
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      setStatus('disconnected');
    };
  }, [enabled, isAuthenticated, accessToken, queryClient, toast]);

  return { status, lastEvent };
}
