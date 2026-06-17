/**
 * Get a team's display name, appending the nickname for NCAA teams when
 * available. Builds lookup maps lazily from the ncaaTeamNicknames and
 * ncaaTeamLogos dictionaries in SiteData.
 */
export function getTeamDisplayName(
  team: string | undefined,
  ncaaTeamNicknames: Record<string, string> = {},
  ncaaTeamLogos: Record<string, string | number> = {}
): string {
  if (!team) return team ?? "";
  const lower = team.toLowerCase();
  // Find canonical casing from nickname keys
  const canonicalKey = Object.keys(ncaaTeamNicknames).find(
    (k) => k.toLowerCase() === lower
  );
  const logoKey = Object.keys(ncaaTeamLogos).find(
    (k) => k.toLowerCase() === lower
  );
  const proper = canonicalKey ?? logoKey ?? team;
  const nickname = ncaaTeamNicknames[canonicalKey ?? ""];
  return nickname ? `${proper} ${nickname}` : team;
}

/**
 * Resolve the logo URL for a team given site data maps.
 * Checks local logos, historical logos, direct or ESPN NCAA logos, partner logos,
 * and finally MiLB static CDN in that priority order.
 */
export function getTeamLogoSrc(
  team: string | undefined,
  teamId: number | undefined,
  level: string,
  localLogos: Record<string, string> = {},
  historicalTeamLogos: Record<string, string> = {},
  ncaaTeamLogos: Record<string, string | number> = {},
  partnerLogos: Record<string, string> = {}
): string | null {
  if (!team) return null;
  if (localLogos[team]) return localLogos[team];
  if (historicalTeamLogos[team]) return historicalTeamLogos[team];
  if (level === "NCAA") {
    const lower = team.toLowerCase();
    const ncaaLogo = Object.entries(ncaaTeamLogos).find(
      ([k]) => k.toLowerCase() === lower
    )?.[1];
    if (typeof ncaaLogo === "string" && /^https?:\/\//.test(ncaaLogo)) {
      return ncaaLogo;
    }
    if (ncaaLogo) return `https://a.espncdn.com/i/teamlogos/ncaa/500/${ncaaLogo}.png`;
    return null;
  }
  if (level === "Independent") {
    if (partnerLogos[team]) return partnerLogos[team];
  }
  if (teamId) {
    return `https://www.mlbstatic.com/team-logos/${teamId}.svg`;
  }
  return null;
}
