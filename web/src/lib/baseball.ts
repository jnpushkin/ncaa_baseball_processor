/**
 * Add innings pitched correctly, e.g. 6.1 + 3.2 = 10.0 (not 9.3).
 * IP is stored as a decimal where the fractional part represents thirds
 * of an inning (0, .1, or .2).
 */
export function addIP(vals: number[]): number {
  const totalThirds = vals.reduce((sum, ip) => {
    const n = parseFloat(String(ip)) || 0;
    const whole = Math.floor(n);
    const frac = Math.round((n - whole) * 10);
    return sum + whole * 3 + frac;
  }, 0);
  const whole = Math.floor(totalThirds / 3);
  const rem = totalThirds % 3;
  return parseFloat(`${whole}.${rem}`);
}

/**
 * Convert innings pitched (in baseball notation) to a true decimal number
 * of innings for rate stat calculations such as ERA.
 * e.g. 6.2 → 6.667
 */
export function ipToInnings(ip: number): number {
  const n = parseFloat(String(ip)) || 0;
  const whole = Math.floor(n);
  const frac = Math.round((n - whole) * 10);
  return whole + frac / 3;
}

/**
 * Normalize date strings to MM/DD/YYYY with zero-padded month and day.
 * Handles input already in M/D/YYYY or MM/DD/YYYY format.
 */
export function formatDate(d: string): string {
  if (!d) return "";
  const parts = d.split("/");
  if (parts.length === 3) {
    return (
      parts[0].padStart(2, "0") +
      "/" +
      parts[1].padStart(2, "0") +
      "/" +
      parts[2]
    );
  }
  return d;
}
