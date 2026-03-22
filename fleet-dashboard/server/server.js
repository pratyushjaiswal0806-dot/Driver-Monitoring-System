import express from 'express';
import cors from 'cors';

import {
    DEFAULT_DRIVER_ID,
    getAlertsByRange,
    getAnalyticsTrends,
    getDriverHealth,
    getDriverList,
    getDriverSummary,
    getFleetOverview,
    isKnownDriverId
} from './db.js';

const app = express();
const PORT = Number(process.env.PORT) || 3001;

app.use(cors());
app.use(express.json());

function sendNotFound(res, message = 'Resource not found') {
    return res.status(404).json({ error: message });
}

function handleRoute(fn) {
    return (req, res) => {
        Promise.resolve(fn(req, res)).catch((error) => {
            console.error(error);
            res.status(500).json({ error: error.message || 'Internal server error' });
        });
    };
}

app.get('/api/health', handleRoute((req, res) => {
    res.json({ status: 'ok', timestamp: new Date().toISOString() });
}));

app.get('/api/drivers', handleRoute((req, res) => {
    res.json(getDriverList());
}));

app.get('/api/drivers/:id/summary', handleRoute((req, res) => {
    if (!isKnownDriverId(req.params.id)) {
        return sendNotFound(res, 'Driver not found');
    }

    const summary = getDriverSummary(req.params.id);
    if (!summary) {
        return sendNotFound(res, 'Driver not found');
    }

    return res.json(summary);
}));

app.get('/api/drivers/:id/alerts', handleRoute((req, res) => {
    if (!isKnownDriverId(req.params.id)) {
        return sendNotFound(res, 'Driver not found');
    }

    const alerts = getAlertsByRange({
        from: req.query.from,
        to: req.query.to,
        limit: req.query.limit,
        offset: req.query.offset
    });

    return res.json(alerts || []);
}));

app.get('/api/drivers/:id/health', handleRoute((req, res) => {
    if (!isKnownDriverId(req.params.id)) {
        return sendNotFound(res, 'Driver not found');
    }

    const days = req.query.days || 7;
    const health = getDriverHealth(req.params.id, days);

    if (!health) {
        return sendNotFound(res, 'Driver not found');
    }

    return res.json(health);
}));

app.get('/api/fleet/overview', handleRoute((req, res) => {
    res.json(getFleetOverview());
}));

app.get('/api/analytics/trends', handleRoute((req, res) => {
    const days = req.query.days || 7;
    res.json(getAnalyticsTrends(days));
}));

app.get('/api/drivers/default', handleRoute((req, res) => {
    res.json({ id: DEFAULT_DRIVER_ID });
}));

app.use((req, res) => {
    sendNotFound(res);
});

app.listen(PORT, () => {
    console.log(`Fleet dashboard API running on http://127.0.0.1:${PORT}`);
});
