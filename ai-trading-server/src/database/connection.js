import mongoose from 'mongoose';
import { config } from '../config/index.js';
import { logger } from '../config/logger.js';

let isConnected = false;

export async function connectDB() {
  if (isConnected) return;

  try {
    const conn = await mongoose.connect(config.db.uri, {
      maxPoolSize: 10,
      serverSelectionTimeoutMS: 5000,
      socketTimeoutMS: 45000,
    });
    isConnected = true;
    logger.info(`MongoDB connected: ${conn.connection.host}`);
  } catch (err) {
    logger.error('MongoDB connection failed: ' + err.message);
    if (config.server.isDev) {
      logger.warn('Running without database — DB-dependent routes will return 503');
    } else {
      process.exit(1);
    }
  }
}

mongoose.connection.on('disconnected', () => {
  isConnected = false;
  logger.warn('MongoDB disconnected. Reconnecting...');
});

mongoose.connection.on('error', (err) => {
  logger.error('MongoDB error:', err.message);
});

export default connectDB;
