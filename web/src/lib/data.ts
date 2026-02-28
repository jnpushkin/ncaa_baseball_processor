/**
 * Build case-insensitive lookup maps from the ncaaTeamNicknames and
 * ncaaTeamLogos records embedded in SiteData.
 *
 * These are intentionally constructed once at module initialisation time
 * (or lazily on first call) to avoid repeated Object.entries() iterations
 * inside render loops.
 */

/**
 * Build a lowercase → nickname map from ncaaTeamNicknames.
 * e.g. { "vanderbilt": "Commodores", ... }
 */
export function buildNicknameByLower(
  ncaaTeamNicknames: Record<string, string>
): Record<string, string> {
  const map: Record<string, string> = {};
  Object.entries(ncaaTeamNicknames).forEach(([k, v]) => {
    map[k.toLowerCase()] = v;
  });
  return map;
}

/**
 * Build a lowercase → canonical-cased team name map from ncaaTeamNicknames.
 * e.g. { "vanderbilt": "Vanderbilt", ... }
 */
export function buildCanonicalName(
  ncaaTeamNicknames: Record<string, string>
): Record<string, string> {
  const map: Record<string, string> = {};
  Object.entries(ncaaTeamNicknames).forEach(([k]) => {
    map[k.toLowerCase()] = k;
  });
  return map;
}

/**
 * Build a lowercase → ESPN logo ID map from ncaaTeamLogos.
 * e.g. { "vanderbilt": 238, ... }
 */
export function buildLogoByLower(
  ncaaTeamLogos: Record<string, string | number>
): Record<string, string | number> {
  const map: Record<string, string | number> = {};
  Object.entries(ncaaTeamLogos).forEach(([k, v]) => {
    map[k.toLowerCase()] = v;
  });
  return map;
}

/**
 * Return the display name for a team, appending the NCAA nickname when one
 * is available.  Mirrors the getTeamDisplayName helper in generator.py JSX.
 *
 * e.g. "Vanderbilt" → "Vanderbilt Commodores"
 *      "DSL Yankees" → "DSL Yankees"  (no nickname, returned unchanged)
 */
export function getTeamDisplayName(
  team: string,
  data: { ncaaTeamNicknames: Record<string, string> }
): string {
  if (!team) return team;
  const lower = team.toLowerCase();
  const nicknameByLower = buildNicknameByLower(data.ncaaTeamNicknames);
  const canonicalName = buildCanonicalName(data.ncaaTeamNicknames);
  const proper = canonicalName[lower] ?? team;
  const nickname = nicknameByLower[lower];
  return nickname ? `${proper} ${nickname}` : team;
}
