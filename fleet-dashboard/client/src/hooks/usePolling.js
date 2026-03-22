import { useEffect, useState } from 'react';

export function usePolling(intervalMs, enabled = true) {
    const [tick, setTick] = useState(0);

    useEffect(() => {
        if (!enabled || !intervalMs) {
            return undefined;
        }

        const timer = window.setInterval(() => {
            setTick((current) => current + 1);
        }, intervalMs);

        return () => window.clearInterval(timer);
    }, [intervalMs, enabled]);

    return tick;
}
