import { useEffect, useMemo, useRef, useState } from "react";
import {
  fetchHistoricalData,
  RealTimeDataPoint,
  streamRealTimeData,
} from "../api";

interface UseLiveSeriesOptions {
  source: string;
  sourceId?: string;
  historicalPoints?: number;
  maxPoints?: number;
  enabled?: boolean;
}

interface UseLiveSeriesResult {
  data: RealTimeDataPoint[];
  loading: boolean;
  error: string | null;
  connected: boolean;
}

function toEpoch(ts: string): number {
  const parsed = Date.parse(ts);
  return Number.isNaN(parsed) ? 0 : parsed;
}

export default function useLiveSeries({
  source,
  sourceId,
  historicalPoints = 50,
  maxPoints = 120,
  enabled = true,
}: UseLiveSeriesOptions): UseLiveSeriesResult {
  const [data, setData] = useState<RealTimeDataPoint[]>([]);
  const [loading, setLoading] = useState<boolean>(enabled);
  const [error, setError] = useState<string | null>(null);
  const [connected, setConnected] = useState<boolean>(false);

  const reconnectRef = useRef<number | null>(null);
  const latestTimestampRef = useRef<string | undefined>(undefined);

  useEffect(() => {
    if (!enabled) {
      setData([]);
      setLoading(false);
      setConnected(false);
      setError(null);
      return;
    }

    let cancelled = false;
    let streamAbort: AbortController | null = null;

    const closeStream = () => {
      if (streamAbort) {
        streamAbort.abort();
        streamAbort = null;
      }
    };

    const clearReconnect = () => {
      if (reconnectRef.current !== null) {
        window.clearTimeout(reconnectRef.current);
        reconnectRef.current = null;
      }
    };

    const appendPoint = (point: RealTimeDataPoint) => {
      latestTimestampRef.current = point.timestamp;
      setData((previous) => {
        if (previous.length > 0) {
          const last = previous[previous.length - 1];
          if (last.timestamp === point.timestamp) {
            return [...previous.slice(0, -1), point];
          }
        }

        const merged = [...previous, point]
          .sort((a, b) => toEpoch(a.timestamp) - toEpoch(b.timestamp))
          .slice(-maxPoints);

        return merged;
      });
    };

    const openStream = async (since?: string) => {
      if (cancelled) {
        return;
      }

      closeStream();
      streamAbort = new AbortController();

      try {
        await streamRealTimeData(source, {
          source_id: sourceId,
          since,
          signal: streamAbort.signal,
          onPoint: (point) => {
            appendPoint(point);
            setConnected(true);
            setError(null);
          },
        });
      } catch (e: any) {
        if (!cancelled && e?.name !== "AbortError") {
          setConnected(false);
          setError(e?.message ?? "Live stream disconnected");
        }
      }

      if (!cancelled) {
        const latest = latestTimestampRef.current ?? since;
        reconnectRef.current = window.setTimeout(() => {
          openStream(latest);
        }, 1500);
      }
    };

    const start = async () => {
      setLoading(true);
      setError(null);
      setConnected(false);

      try {
        const initial = await fetchHistoricalData(
          source,
          sourceId,
          undefined,
          undefined,
          historicalPoints,
        );

        if (cancelled) {
          return;
        }

        const normalized = initial
          .map((p) => ({ timestamp: p.timestamp, value: p.value }))
          .sort((a, b) => toEpoch(a.timestamp) - toEpoch(b.timestamp))
          .slice(-maxPoints);

        setData(normalized);

        latestTimestampRef.current =
          normalized.length > 0
            ? normalized[normalized.length - 1].timestamp
            : undefined;

        void openStream(latestTimestampRef.current);
      } catch (e: any) {
        if (!cancelled) {
          setError(e?.message ?? "Failed to load live data");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    start();

    return () => {
      cancelled = true;
      clearReconnect();
      closeStream();
    };
  }, [enabled, source, sourceId, historicalPoints, maxPoints]);

  return useMemo(
    () => ({ data, loading, error, connected }),
    [data, loading, error, connected],
  );
}
