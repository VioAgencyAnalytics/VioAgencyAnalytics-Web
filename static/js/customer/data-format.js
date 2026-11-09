/* Decimal currency strings stay exact; percentages remain provider fractions. */
(() => {
  'use strict';
  function decimal(value, digits) {
    const match = /^(\d+)(?:\.(\d*))?(?:e([+-]?\d+))?$/i.exec(value);
    if (!match) return null;
    const fraction = match[2] || '', exponent = Number(match[3] || 0);
    if (!Number.isInteger(exponent) || Math.abs(exponent) > 60) return null;
    let amount = BigInt(match[1]+fraction), scale = fraction.length-exponent-digits;
    if (scale > 0) {
      const divisor = 10n**BigInt(scale), quotient = amount/divisor, remainder = amount%divisor;
      // Match the server Decimal formatter: round half to even.
      amount = quotient + (2n*remainder > divisor || (2n*remainder === divisor && quotient%2n === 1n) ? 1n : 0n);
    } else amount *= 10n**BigInt(-scale);
    let text = amount.toString().padStart(digits+1,'0');
    const whole = (digits ? text.slice(0,-digits) : text).replace(/\B(?=(\d{3})+(?!\d))/g,'.');
    return whole+(digits ? ','+text.slice(-digits) : '');
  }
  function format(value, unit='number', currency=null) {
    if (value === null || value === undefined || typeof value === 'boolean') return '—';
    if (unit === 'currency' && typeof value === 'string') {
      const exact = decimal(value,currency === 'VND' ? 0 : 2);
      return exact === null ? '—' : exact+(currency && /^[A-Z]{3}$/.test(currency) ? ' '+currency : '');
    }
    if (typeof value !== 'number' || !Number.isFinite(value) || value < 0) return '—';
    if (unit === 'percent') return new Intl.NumberFormat('vi-VN',{style:'percent',maximumFractionDigits:2}).format(value);
    if (unit === 'currency' && /^[A-Z]{3}$/.test(currency || '')) return new Intl.NumberFormat('vi-VN',{style:'currency',currency,maximumFractionDigits:currency === 'VND' ? 0 : 2}).format(value);
    return new Intl.NumberFormat('vi-VN',{maximumFractionDigits:2}).format(value);
  }
  window.VioDataFormat = Object.freeze({format});
})();
