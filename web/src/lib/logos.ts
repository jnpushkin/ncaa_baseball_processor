import type { SiteData } from "../types/index";

/**
 * Resolve a team logo URL using the following priority chain:
 *
 * 1. localLogos  – manually overridden logos keyed by exact team name.
 * 2. historicalTeamLogos – logos for defunct / renamed teams.
 * 3. partnerLogos – logos for Independent-level partner league teams.
 *    Only consulted when level is "Independent".
 * 4. ESPN CDN – used for NCAA teams when ncaaTeamLogos has a numeric ESPN ID.
 *    Only consulted when level is "NCAA".
 * 5. mlbstatic CDN – used for non-NCAA teams when a numeric teamId is available.
 *    Skipped for level "NCAA".
 * 6. null – no logo could be resolved.
 *
 * The function mirrors the four separate implementations that exist in
 * generator.py (TeamCell, ScheduleTab getTeamLogo, ScorigamiTab getTeamLogo,
 * and the batter/pitcher table getTeamLogo variants) and unifies them into a
 * single authoritative source.
 */
export function getTeamLogoUrl(
  team: string,
  data: SiteData,
  options?: { teamId?: number; level?: string }
): string | null {
  const { teamId, level } = options ?? {};

  // 1. Local overrides take top priority.
  if (data.localLogos) {
    const local = data.localLogos[team];
    if (local) return local;
  }

  // 2. Historical team logos (defunct / renamed franchises).
  if (data.historicalTeamLogos) {
    const historical = data.historicalTeamLogos[team];
    if (historical) return historical;
  }

  // 3. Partner league logos – only for Independent level.
  if (level === "Independent" && data.partnerLogos) {
    const partner = data.partnerLogos[team];
    if (partner) return partner;
  }

  // 4. ESPN CDN for NCAA teams.
  if (level === "NCAA" && data.ncaaTeamLogos) {
    const espnId = data.ncaaTeamLogos[team];
    if (espnId) {
      return `https://a.espncdn.com/i/teamlogos/ncaa/500/${espnId}.png`;
    }
  }

  // 5. mlbstatic CDN for non-NCAA teams with a known team ID.
  if (level !== "NCAA" && teamId) {
    return `https://www.mlbstatic.com/team-logos/${teamId}.svg`;
  }

  return null;
}
