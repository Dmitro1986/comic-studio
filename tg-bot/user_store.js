import fs from 'fs';
import path from 'path';

const PROJECT_ROOT = path.resolve(import.meta.dirname, '..');
const USERS_FILE = path.join(PROJECT_ROOT, 'data', 'allowed_users.json');

export class UserStore {
  constructor({ filePath = USERS_FILE, envAllowed = process.env.ALLOWED_TELEGRAM_USERS, adminChatId = process.env.CHAT_ID } = {}) {
    this.filePath = filePath;
    this.envAllowed = envAllowed;
    this.adminChatId = adminChatId;
    this.allowedUsers = new Set();
    this.load();
  }

  load() {
    this.allowedUsers.clear();
    // 1. Add admin CHAT_ID if present
    if (this.adminChatId) {
      this.allowedUsers.add(String(this.adminChatId).trim());
    }

    // 2. Add env allowed users
    if (this.envAllowed) {
      String(this.envAllowed).split(',').forEach(id => {
        const cleaned = id.trim();
        if (cleaned) this.allowedUsers.add(cleaned);
      });
    }

    // 3. Add stored users from JSON file
    if (fs.existsSync(this.filePath)) {
      try {
        const raw = fs.readFileSync(this.filePath, 'utf-8');
        const data = JSON.parse(raw);
        if (Array.isArray(data)) {
          data.forEach(id => this.allowedUsers.add(String(id).trim()));
        }
      } catch (err) {
        console.error('Error loading allowed_users.json:', err.message);
      }
    }
  }

  save() {
    try {
      const dir = path.dirname(this.filePath);
      if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
      fs.writeFileSync(this.filePath, JSON.stringify(Array.from(this.allowedUsers), null, 2), 'utf-8');
    } catch (err) {
      console.error('Error saving allowed_users.json:', err.message);
    }
  }

  isAuthorized(userId) {
    if (!userId) return false;
    const strId = String(userId).trim();
    return this.allowedUsers.has(strId);
  }

  addUser(userId) {
    if (!userId) return false;
    const strId = String(userId).trim();
    this.allowedUsers.add(strId);
    this.save();
    return true;
  }

  removeUser(userId) {
    if (!userId) return false;
    const strId = String(userId).trim();
    if (strId === String(this.adminChatId).trim()) {
      return false; // Cannot remove primary admin
    }
    const result = this.allowedUsers.delete(strId);
    if (result) this.save();
    return result;
  }

  listUsers() {
    return Array.from(this.allowedUsers);
  }
}

export const defaultUserStore = new UserStore();
