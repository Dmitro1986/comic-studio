import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import crypto from 'crypto';
import { verifyTelegramInitData } from '../lib/telegram_auth.js';

describe('telegram_auth: HMAC validation', () => {
  const botToken = '123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11';

  it('validates authentic initData correctly', () => {
    const userJson = JSON.stringify({ id: 1045621572, first_name: 'Test' });
    const authDate = String(Math.floor(Date.now() / 1000));
    const dataCheckString = `auth_date=${authDate}\nuser=${userJson}`;

    const secretKey = crypto.createHmac('sha256', 'WebAppData').update(botToken).digest();
    const hash = crypto.createHmac('sha256', secretKey).update(dataCheckString).digest('hex');

    const initDataRaw = `auth_date=${authDate}&user=${encodeURIComponent(userJson)}&hash=${hash}`;

    const result = verifyTelegramInitData(initDataRaw, botToken);
    assert.equal(result.valid, true);
    assert.equal(result.user.id, 1045621572);
  });

  it('rejects tampered initData', () => {
    const userJson = JSON.stringify({ id: 1045621572, first_name: 'Test' });
    const authDate = String(Math.floor(Date.now() / 1000));
    const dataCheckString = `auth_date=${authDate}\nuser=${userJson}`;

    const secretKey = crypto.createHmac('sha256', 'WebAppData').update(botToken).digest();
    const hash = crypto.createHmac('sha256', secretKey).update(dataCheckString).digest('hex');

    // Tamper the user id
    const tamperedUser = JSON.stringify({ id: 999999999, first_name: 'Hacker' });
    const initDataRaw = `auth_date=${authDate}&user=${encodeURIComponent(tamperedUser)}&hash=${hash}`;

    const result = verifyTelegramInitData(initDataRaw, botToken);
    assert.equal(result.valid, false);
    assert.equal(result.error, 'INVALID_SIGNATURE');
  });

  it('handles missing initData gracefully', () => {
    const result = verifyTelegramInitData('', botToken);
    assert.equal(result.valid, false);
    assert.equal(result.error, 'MISSING_INIT_DATA_OR_TOKEN');
  });
});
