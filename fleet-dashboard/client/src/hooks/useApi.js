import { useCallback, useEffect, useRef, useState } from 'react';

const defaultTransform = (value) => value;

export function useApi(url, options = {}, deps = []) {
    const {
        enabled = true,
        initialData = null,
        transform = defaultTransform,
        method = 'GET',
        headers = {},
        body = undefined,
        cache = 'no-store'
    } = options;

    const [data, setData] = useState(initialData);
    const [loading, setLoading] = useState(Boolean(enabled));
    const [error, setError] = useState(null);
    const abortRef = useRef(null);
    const hasLoadedRef = useRef(false);

    const fetchData = useCallback(async () => {
        if (!enabled || !url) {
            setLoading(false);
            return null;
        }

        if (abortRef.current) {
            abortRef.current.abort();
        }

        const controller = new AbortController();
        abortRef.current = controller;

        const showInitialLoading = !hasLoadedRef.current;
        if (showInitialLoading) {
            setLoading(true);
        }
        setError(null);

        try {
            const response = await fetch(url, {
                method,
                headers,
                body,
                cache,
                signal: controller.signal
            });

            if (!response.ok) {
                const text = await response.text();
                throw new Error(text || `Request failed with status ${response.status}`);
            }

            const payload = await response.json();
            const nextData = transform(payload);
            setData(nextData);
            hasLoadedRef.current = true;
            return nextData;
        } catch (nextError) {
            if (nextError.name !== 'AbortError') {
                setError(nextError);
            }
            return null;
        } finally {
            if (showInitialLoading) {
                setLoading(false);
            }
        }
    }, [url, enabled, method, headers, body, cache, transform]);

    useEffect(() => {
        fetchData();

        return () => {
            if (abortRef.current) {
                abortRef.current.abort();
            }
        };
    }, [fetchData, ...deps]);

    return {
        data,
        loading,
        error,
        refetch: fetchData,
        setData
    };
}
