import crypto from 'crypto';

/**
 * Validate Telegram WebApp initData HMAC-SHA256 signature.
 * @param {string} initDataRaw - raw query string from Telegram.WebApp.initData
 * @param {string} botToken - Telegram Bot Token
 * @returns {{ valid: boolean, user?: object, error?: string }}
 */
export function verifyTelegramInitData(initDataRaw, botToken) {
  if (!initDataRaw || typeof initDataRaw !== 'string' || !botToken) {
    return { valid: false, error: 'MISSING_INIT_DATA_OR_TOKEN' };
  }

  try {
    const urlParams = new URLSearchParams(initDataRaw);
    const hash = urlParams.get('hash');
    if (!hash) return { valid: false, error: 'MISSING_HASH' };

    urlParams.delete('hash');

    const params = [];
    for (const [key, value] of urlParams.entries()) {
      params.push(`${key}=${value}`);
    }
    params.sort();

    const dataCheckString = params.join('\n');
    const secretKey = crypto.createHmac('sha256', 'WebAppData').update(botToken).digest();
    const calculatedHash = crypto.createHmac('sha256', secretKey).update(dataCheckString).digest('hex');

    const bufHash = Buffer.from(hash, 'hex');
    const bufCalc = Buffer.from(calculatedHash, 'hex');

    if (bufHash.length !== bufCalc.length || !crypto.timingSafeEqual(bufHash, bufCalc)) {
      return { valid: false, error: 'INVALID_SIGNATURE' };
    }

    const userRaw = urlParams.get('user');
    const user = userRaw ? JSON.parse(userRaw) : null;

    return { valid: true, user };
  } catch (err) {
    return { valid: false, error: err.message };
  }
}
