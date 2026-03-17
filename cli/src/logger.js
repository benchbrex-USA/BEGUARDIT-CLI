// Structured JSON logging (Pino) — ARCH-002 §15.1
import pino from 'pino';

const logger = pino({
  level: process.env.LOG_LEVEL?.toLowerCase() || 'info',
  transport: process.stdout.isTTY
    ? { target: 'pino-pretty', options: { colorize: true } }
    : undefined,
  base: { component: 'cli' },
});

export default logger;
