/* Decimal currency strings stay exact; percentages remain provider fractions. */
(() => {
  'use strict';
  function decimal(value, digits, shift = 0) {
    const match = /^(\d+)(?:\.(\d*))?(?:e([+-]?\d+))?$/i.exec(value);
    if (!match) return null;
    const fraction = match[2] || '', exponent = Number(match[3] || 0) + shift;
    if (!Number.isInteger(exponent) || Math.abs(exponent) > 60) return null;
    let amount = BigInt(match[1]+fraction), scale = fraction.length-exponent-digits;
    if (amount > 0n && scale > 0 && amount < 10n**BigInt(scale)) return digits ? '<0,01' : '<1';
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
    if (unit === 'currency' && (typeof value === 'string' || typeof value === 'number' && Number.isFinite(value) && value >= 0)) {
      const exact = decimal(String(value),currency === 'VND' ? 0 : 2);
      return exact === null ? '—' : exact+(currency && /^[A-Z]{3}$/.test(currency) ? ' '+currency : '');
    }
    if (typeof value !== 'number' || !Number.isFinite(value) || value < 0) return '—';
    const exact = decimal(String(value),unit === 'count' && Number.isInteger(value) ? 0 : 2,unit === 'percent' ? 2 : 0);
    if (exact === null) return '—';
    const [whole,fraction] = exact.split(','), trimmed = fraction?.replace(/0+$/,'');
    return whole+(trimmed ? ','+trimmed : '')+(unit === 'percent' ? '%' : '');
  }
  function fraction(value) {
    if (typeof value === 'number') return format(value, 'percent');
    if (typeof value !== 'string' || value.length > 180 || !/^(?:0|[1-9]\d*)(?:\.\d+)?$/.test(value)) return '—';
    const exact = decimal(value, 2, 2);
    if (exact === null) return '—';
    const [whole, part] = exact.split(','), trimmed = part?.replace(/0+$/,'');
    return whole + (trimmed ? ',' + trimmed : '') + '%';
  }
  window.VioDataFormat = Object.freeze({format, fraction});
})();
