import { addIP } from "./baseball";

/**
 * Filter an array of stat rows by level and/or league.
 * Checks both lowercase and uppercase field name variants (e.g. level/Level,
 * league/League, conference/Conference).
 * "All" is treated as no filter.
 */
export function filterByLevelLeague(
  data: any[],
  levelFilter: string,
  leagueFilter: string
): any[] {
  let result = data;
  if (levelFilter && levelFilter !== "All") {
    result = result.filter(
      (d) => (d.level ?? d.Level) === levelFilter
    );
  }
  if (leagueFilter && leagueFilter !== "All") {
    result = result.filter(
      (d) =>
        (d.league ?? d.League ?? d.conference ?? d.Conference) === leagueFilter
    );
  }
  return result;
}

/**
 * Group crossover players by bref_id into combined rows with expandable sub-rows.
 * Only combines entries that span multiple levels (e.g. NCAA + MiLB).
 * Same-level entries with the same bref_id are assumed to be different people
 * (name collision in the Chadwick register) and are left un-combined.
 *
 * @param data         Filtered list of batter or pitcher rows.
 * @param levelFilter  Current level filter; if not "All", grouping is skipped.
 * @param sumFields    Field names whose values should be summed across entries.
 * @param calcRateStats Callback that receives the combined row and should
 *                     mutate it to set derived rate stats (avg, era, …).
 * @param ipField      Optional field name that holds innings pitched and must
 *                     be combined with addIP() instead of plain addition.
 */
export function groupByPlayer(
  data: any[],
  levelFilter: string,
  sumFields: string[],
  calcRateStats: (combined: any) => void,
  ipField?: string
): any[] {
  if (levelFilter && levelFilter !== "All") return data;

  const groups: Record<string, any[]> = {};
  const ungrouped: any[] = [];

  data.forEach((entry) => {
    const key = entry.bref_id;
    if (key) {
      if (!groups[key]) groups[key] = [];
      groups[key].push(entry);
    } else {
      ungrouped.push(entry);
    }
  });

  const result: any[] = [];

  Object.values(groups).forEach((entries) => {
    // Only combine if entries span multiple levels (NCAA + MiLB crossover).
    const uniqueLevels = new Set(entries.map((e) => e.level));
    if (entries.length === 1 || uniqueLevels.size <= 1) {
      entries.forEach((e) => result.push(e));
    } else {
      const combined: any = { ...entries[0] };
      combined.isCombined = true;
      combined.subRows = entries;
      combined.level = "Combined";
      combined.levels = entries.map((e) => e.level);
      combined.team = entries.map((e) => e.team).join(" / ");
      combined.teams = entries.map((e) => ({
        team: e.team,
        team_id: e.team_id,
        level: e.level,
      }));

      sumFields.forEach((f) => {
        if (f === ipField) {
          combined[f] = addIP(entries.map((e) => e[f]));
        } else {
          combined[f] = entries.reduce(
            (s: number, e: any) => s + (parseFloat(e[f]) || 0),
            0
          );
        }
      });

      calcRateStats(combined);
      result.push(combined);
    }
  });

  return [...result, ...ungrouped];
}
