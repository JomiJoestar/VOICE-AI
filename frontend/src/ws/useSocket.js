import { useEffect, useRef, useState, useCallback } from "react";

// Conecta al WebSocket del backend y entrega cada evento al handler.
// Reintenta la conexión automáticamente si se cae.
export function useSocket(onEvent) {
  const wsRef = useRef(null);
  const [connected, setConnected] = useState(false);
  const handlerRef = useRef(onEvent);
  handlerRef.current = onEvent;

  useEffect(() => {
    let alive = true;
    let retry;

    const connect = () => {
      const proto = location.protocol === "https:" ? "wss" : "ws";
      const ws = new WebSocket(`${proto}://${location.host}/ws`);
      wsRef.current = ws;

      ws.onopen = () => alive && setConnected(true);
      ws.onclose = () => {
        if (!alive) return;
        setConnected(false);
        retry = setTimeout(connect, 1000);
      };
      ws.onerror = () => ws.close();
      ws.onmessage = (e) => {
        try {
          handlerRef.current?.(JSON.parse(e.data));
        } catch (_) {
          /* ignora payloads no-JSON */
        }
      };
    };

    connect();
    return () => {
      alive = false;
      clearTimeout(retry);
      wsRef.current?.close();
    };
  }, []);

  const send = useCallback((obj) => {
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(obj));
  }, []);

  return { connected, send };
}
