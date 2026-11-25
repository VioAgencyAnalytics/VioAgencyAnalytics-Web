const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const {test} = require('node:test');
const vm = require('node:vm');
const context = vm.createContext({window: {}, Intl, BigInt});
vm.runInContext(readFileSync('static/js/customer/data-format.js', 'utf8'), context);
const format = context.window.VioDataFormat.format;

test('Currency preserves exact provider decimals beyond JavaScript integer precision', () => {
  assert.equal(format('9007199254740993.25', 'currency', 'USD'), '9.007.199.254.740.993,25 USD');
  assert.equal(format('0.00', 'currency', 'USD'), '0,00 USD');
  assert.equal(format('0.00', 'currency', 'VND'), '0 VND');
  assert.equal(format('1E+3', 'currency', 'USD'), '1.000,00 USD');
});

test('Currency rounds ties to even consistently with server Decimal', () => {
  assert.equal(format('1.005', 'currency', 'USD'), '1,00 USD');
  assert.equal(format('1.015', 'currency', 'USD'), '1,02 USD');
  assert.equal(format('2.5', 'currency', 'VND'), '2 VND');
  assert.equal(format('3.5', 'currency', 'VND'), '4 VND');
});

test('Missing and malformed values never become zero; fractional rates stay percentages', () => {
  for (const value of [null, undefined, true, false, NaN, Infinity, -1, 'not-a-number']) assert.equal(format(value), '—');
  assert.equal(format(0), '0');
  assert.equal(format(.25, 'percent'), '25%');
  assert.equal(format('NaN', 'currency', 'USD'), '—');
});

test('Account currency never rounds fractional conversions or minutes to an integer', () => {
  assert.equal(format(.25,'number','VND'),'0,25');
  assert.equal(format(6.5,'number','VND'),'6,5');
  assert.equal(format(.125,'number','VND'),'0,12');
  assert.equal(format(.00125,'percent','VND'),'0,12%');
});

test('Positive subprecision values remain distinct from an observed zero', () => {
  assert.equal(format('0.000001','currency','USD'),'<0,01 USD');
  assert.equal(format('0.4','currency','VND'),'<1 VND');
  assert.equal(format(.000001,'number'),'<0,01');
  assert.equal(format(.0000001,'percent'),'<0,01%');
  assert.equal(format(0,'percent'),'0%');
  assert.equal(format(0,'currency','USD'),'0,00 USD');
});
