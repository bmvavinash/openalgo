import jwt from 'jsonwebtoken';
import User from '../database/models/User.js';
import { config } from '../config/index.js';

export function generateToken(userId) {
  return jwt.sign({ id: userId }, config.jwt.secret, { expiresIn: config.jwt.expiresIn });
}

export async function protect(req, res, next) {
  let token;

  if (req.headers.authorization?.startsWith('Bearer ')) {
    token = req.headers.authorization.split(' ')[1];
  } else if (req.headers['x-api-key']) {
    // API key auth for automated systems
    const user = await User.findOne({ apiKey: req.headers['x-api-key'] }).select('+apiKey');
    if (!user || !user.isActive) return res.status(401).json({ error: 'Invalid API key' });
    req.user = user;
    return next();
  }

  if (!token) return res.status(401).json({ error: 'Not authenticated' });

  try {
    const decoded = jwt.verify(token, config.jwt.secret);
    req.user = await User.findById(decoded.id);
    if (!req.user || !req.user.isActive) {
      return res.status(401).json({ error: 'User not found or inactive' });
    }
    next();
  } catch {
    return res.status(401).json({ error: 'Invalid or expired token' });
  }
}

export function adminOnly(req, res, next) {
  if (req.user?.role !== 'admin') {
    return res.status(403).json({ error: 'Admin access required' });
  }
  next();
}
