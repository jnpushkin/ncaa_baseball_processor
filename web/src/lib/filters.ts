import { addIP } from "./baseball";

interface FilterableRow {
  level?: string;
  Level?: string;
  league?: string;
  League?: string;
  conference?: string;
  Conference?: string;
  bref_id?: string;
  team?: string;
  team_id?: number;
  isCombined?: boolean;
  subRows?: FilterableRow[];
  levels?: string[];
  teams?: { team: string; team_id?: number; level: string }[];
}

/**
 * Filter an array of stat rows by level and/or league.
 * Checks both lowercase and uppercase field name variants (e.g. level/Level,
 * league/League, conference/Conference).
 * "All" is treated as no filter.
 */
export function filterByLevelLeague<T extends FilterableRow>(
  data: T[],
  levelFilter: string,
  leagueFilter: string
): T[] {
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
export function groupByPlayer<T extends FilterableRow>(
  data: T[],
  levelFilter: string,
  sumFields: string[],
  calcRateStats: (combined: T) => void,
  ipField?: string
): T[] {
  if (levelFilter && levelFilter !== "All") return data;

  const groups: Record<string, T[]> = {};
  const ungrouped: T[] = [];

  data.forEach((entry) => {
    const key = entry.bref_id;
    if (key) {
      if (!groups[key]) groups[key] = [];
      groups[key].push(entry);
    } else {
      ungrouped.push(entry);
    }
  });

  const result: T[] = [];

  Object.values(groups).forEach((entries) => {
    // Only combine if entries span multiple levels (NCAA + MiLB crossover).
    const uniqueLevels = new Set(entries.map((e) => e.level));
    if (entries.length === 1 || uniqueLevels.size <= 1) {
      entries.forEach((e) => result.push(e));
    } else {
      const combined: T = { ...entries[0] };
      const mutable = combined as FilterableRow & Record<string, unknown>;
      combined.isCombined = true;
      combined.subRows = entries;
      combined.level = "Combined";
      combined.levels = entries.map((e) => e.level).filter((level): level is string => !!level);
      combined.team = entries.map((e) => e.team ?? "").filter(Boolean).join(" / ");
      combined.teams = entries.map((e) => ({
        team: e.team ?? "",
        team_id: e.team_id,
        level: e.level ?? "",
      }));

      sumFields.forEach((f) => {
        if (f === ipField) {
          mutable[f] = addIP(
            entries.map((e) => parseFloat(String((e as Record<string, unknown>)[f] ?? "")) || 0)
          );
        } else {
          mutable[f] = entries.reduce(
            (s: number, e) => s + (parseFloat(String((e as Record<string, unknown>)[f] ?? "")) || 0),
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
