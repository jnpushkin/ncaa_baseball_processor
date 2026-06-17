"use client";

import { useMemo } from "react";
import type { CrossoverPlayer, MilestoneEntry, SiteData, UnifiedGame } from "@/types";
import LevelBadge from "@/components/shared/LevelBadge";
import TeamLogo from "@/components/shared/TeamLogo";
import { formatDate } from "@/lib/baseball";
import { getTeamDisplayName } from "@/lib/data";

type DashboardPlayer = CrossoverPlayer | MilestoneEntry;

interface DashboardProps {
  data: SiteData;
  onTabChange: (tabId: string) => void;
  onGameClick?: (game: UnifiedGame) => void;
  onPlayerClick?: (player: DashboardPlayer, type: "batter" | "pitcher") => void;
}

type DashboardMilestone = {
  key: string;
  label: string;
  row: MilestoneEntry;
  playerType: "batter" | "pitcher";
};

const MILESTONE_LABELS: Record<string, string> = {
  threeHrGames: "3 HR",
  multiHrGames: "Multi-HR",
  fiveHitGames: "5 Hits",
  fourHitGames: "4 Hits",
  cycles: "Cycle",
  cycleWatch: "Cycle Watch",
  sixRbiGames: "6 RBI",
  fiveRbiGames: "5 RBI",
  fourRbiGames: "4 RBI",
  multiDoubleGames: "Multi-2B",
  multiTripleGames: "Multi-3B",
  multiSbGames: "Multi-SB",
  fourWalkGames: "4 BB",
  perfectBattingGames: "Perfect Batting",
  fourRunGames: "4 Runs",
  threeTotalBasesGames: "8 TB",
  perfectGames: "Perfect Game",
  noHitters: "No-Hitter",
  oneHitters: "1-Hitter",
  twoHitters: "2-Hitter",
  shutouts: "Shutout",
  cgsoNoWalks: "CGSO No BB",
  completeGames: "Complete Game",
  lowHitCg: "Low-Hit CG",
  sevenInningShutouts: "7+ IP SO",
  madduxGames: "Maddux",
  fifteenKGames: "15 K",
  twelveKGames: "12 K",
  tenKGames: "10 K",
  dominantStarts: "Dominant Start",
};

const MILESTONE_PRIORITY: Record<string, number> = {
  perfectGames: 1,
  noHitters: 2,
  threeHrGames: 3,
  cycles: 4,
  fifteenKGames: 5,
  fiveHitGames: 6,
  madduxGames: 7,
  sixRbiGames: 8,
  twelveKGames: 9,
  multiHrGames: 10,
  shutouts: 11,
  tenKGames: 12,
};

const PITCHING_MILESTONES = new Set([
  "perfectGames",
  "noHitters",
  "oneHitters",
  "twoHitters",
  "shutouts",
  "cgsoNoWalks",
  "completeGames",
  "lowHitCg",
  "sevenInningShutouts",
  "madduxGames",
  "fifteenKGames",
  "twelveKGames",
  "tenKGames",
  "dominantStarts",
]);

function dateSortValue(value?: string) {
  if (!value) return 0;
  const parts = value.split(/[/-]/).map((part) => Number(part));
  if (parts.length === 3) {
    const [month, day, year] = parts;
    if (month && day && year) return year * 10000 + month * 100 + day;
  }
  return Number(value.replace(/\D/g, "")) || 0;
}

function pct(done: number, total: number) {
  if (!total) return 0;
  return Math.min(100, Math.round((done / total) * 100));
}

function milestoneLine(row: MilestoneEntry) {
  const statKeys = ["HR", "H", "RBI", "K", "IP", "BB", "SB", "TB", "ER"];
  return statKeys
    .filter((key) => row[key] !== undefined && row[key] !== "")
    .slice(0, 4)
    .map((key) => `${key} ${row[key]}`)
    .join(" / ");
}

function levelDetails(player: CrossoverPlayer) {
  return player["Level Details"] ?? [];
}

function uniqueCount(values: string[]) {
  return new Set(values.filter(Boolean)).size;
}

export default function Dashboard({
  data,
  onTabChange,
  onGameClick,
  onPlayerClick,
}: DashboardProps) {
  const levelColors = data.levelColors ?? {};

  const recentGames = useMemo(
    () =>
      [...(data.unifiedGameLog ?? [])]
        .sort((a, b) => dateSortValue(b.date_sort || b.date) - dateSortValue(a.date_sort || a.date))
        .slice(0, 6),
    [data.unifiedGameLog]
  );

  const recentMilestones = useMemo<DashboardMilestone[]>(
    () =>
      Object.entries(data.milestones ?? {})
        .flatMap(([key, rows]) =>
          (rows ?? []).map((row) => ({
            key,
            label: MILESTONE_LABELS[key] ?? key,
            row,
            playerType: PITCHING_MILESTONES.has(key) ? ("pitcher" as const) : ("batter" as const),
          }))
        )
        .sort((a, b) => {
          const dateDelta = dateSortValue(b.row.Date) - dateSortValue(a.row.Date);
          if (dateDelta) return dateDelta;
          return (MILESTONE_PRIORITY[a.key] ?? 99) - (MILESTONE_PRIORITY[b.key] ?? 99);
        })
        .slice(0, 7),
    [data.milestones]
  );

  const crossoverSpotlight = useMemo(
    () => [...(data.crossoverPlayers ?? [])].sort((a, b) => (b["Total Games"] ?? 0) - (a["Total Games"] ?? 0)).slice(0, 5),
    [data.crossoverPlayers]
  );

  const progress = useMemo(() => {
    const ncaaTeams = new Set<string>();
    const ncaaSeen = new Set<string>();
    const ncaaHome = new Set<string>();
    Object.values(data.checklist ?? {}).forEach((conference) => {
      conference.teams.forEach((team) => ncaaTeams.add(team));
      Object.entries(conference.teamStatus).forEach(([team, status]) => {
        if (status !== "none") ncaaSeen.add(team);
        if (status === "home") ncaaHome.add(team);
      });
    });

    const proTeams = new Set<string>();
    const proSeen = new Set<string>();
    Object.values(data.milbChecklist ?? {}).forEach((level) => {
      level.teams.forEach((team) => proTeams.add(team.team));
      Object.entries(level.teamStatus).forEach(([team, status]) => {
        if (status !== "none") proSeen.add(team);
      });
    });

    const proVisited = uniqueCount(data.milbVenuesVisited ?? []) + uniqueCount(data.partnerVenuesVisited ?? []);
    const partnerVenueTotal = Object.keys(data.partnerStadiumLocations ?? {}).length;
    const proVenueTotal = Object.keys(data.milbStadiumLocations ?? {}).length + partnerVenueTotal;

    return {
      ncaaSeen: ncaaSeen.size,
      ncaaTotal: ncaaTeams.size,
      ncaaHome: ncaaHome.size,
      proSeen: proSeen.size,
      proTotal: proTeams.size,
      proVisited,
      proVenueTotal,
    };
  }, [
    data.checklist,
    data.milbChecklist,
    data.milbStadiumLocations,
    data.milbVenuesVisited,
    data.partnerStadiumLocations,
    data.partnerVenuesVisited,
  ]);

  const topTeams = useMemo(
    () =>
      [...(data.teamRecords ?? [])]
        .sort((a, b) => {
          const pctDelta = Number(b["Win%"] ?? 0) - Number(a["Win%"] ?? 0);
          if (pctDelta) return pctDelta;
          const diffDelta = Number(b.Diff ?? 0) - Number(a.Diff ?? 0);
          if (diffDelta) return diffDelta;
          return Number(b.W ?? 0) - Number(a.W ?? 0);
        })
        .slice(0, 5),
    [data.teamRecords]
  );

  const qualitySummary = data.dataQuality?.summary;
  const sourceWarnings = qualitySummary?.sourceMergeWarnings ?? 0;
  const sourceInfos = qualitySummary?.sourceMergeInfos ?? 0;
  const mergedSourceGames = qualitySummary?.mergedSourceGames ?? 0;
  const unmergedCandidates = qualitySummary?.unmergedSourceCandidates ?? 0;
  const sourceHealthLabel = sourceWarnings > 0 ? `${sourceWarnings} warnings` : "Clean";

  return (
    <div className="dashboard-page">
      <div className="dashboard-overview">
        <section className="dashboard-panel dashboard-panel--wide">
          <div className="dashboard-section-header">
            <div>
              <span className="dashboard-eyebrow">Latest coverage</span>
              <h2>Recent Results</h2>
            </div>
            <button type="button" className="dashboard-link-button" onClick={() => onTabChange("allGames")}>
              Games
            </button>
          </div>
          <div className="dashboard-game-list">
            {recentGames.map((game) => (
              <button
                key={game.game_id ?? `${game.date_sort}-${game.away_team}-${game.home_team}`}
                type="button"
                className="dashboard-game-row"
                onClick={() => onGameClick?.(game)}
                disabled={!game.game_id}
              >
                <span className="dashboard-date">{formatDate(game.date)}</span>
                <LevelBadge level={game.level} levelColors={levelColors} />
                <span className="dashboard-matchup">
                  <span>{game.away_team}</span>
                  <strong>{game.away_score} - {game.home_score}</strong>
                  <span>{game.home_team}</span>
                </span>
                <span className="dashboard-venue">{game.venue}</span>
              </button>
            ))}
          </div>
        </section>

        <section className={`dashboard-panel dashboard-health ${sourceWarnings > 0 ? "needs-review" : "is-clean"}`}>
          <div className="dashboard-section-header">
            <div>
              <span className="dashboard-eyebrow">Source health</span>
              <h2>{sourceHealthLabel}</h2>
            </div>
            <button type="button" className="dashboard-link-button" onClick={() => onTabChange("quality")}>
              Details
            </button>
          </div>
          <div className="dashboard-health-copy">
            <strong>{mergedSourceGames.toLocaleString()} merged NCAA source checks</strong>
            <span>
              {sourceWarnings > 0
                ? "Some merged games still need review."
                : "Box-score stats are trusted; NCAA API notes stay informational."}
            </span>
          </div>
          <div className="dashboard-health-metrics">
            <span>{sourceInfos.toLocaleString()} info notes</span>
            <span>{unmergedCandidates.toLocaleString()} split candidates</span>
          </div>
        </section>
      </div>

      <div className="dashboard-grid">
        <section className="dashboard-panel">
          <div className="dashboard-section-header">
            <div>
              <span className="dashboard-eyebrow">Milestone board</span>
              <h2>Recent Standouts</h2>
            </div>
            <button type="button" className="dashboard-link-button" onClick={() => onTabChange("milestones")}>
              Milestones
            </button>
          </div>
          <div className="dashboard-list">
            {recentMilestones.map((item, index) => (
              <button
                key={`${item.key}-${item.row.Date}-${item.row.Player}-${index}`}
                type="button"
                className="dashboard-list-row"
                onClick={() => onPlayerClick?.(item.row, item.playerType)}
              >
                <span className="dashboard-rank-badge">{item.label}</span>
                <span className="dashboard-list-main">
                  <strong>{item.row.Player}</strong>
                  <span>{item.row.Team} vs {item.row.Opponent}</span>
                </span>
                <span className="dashboard-list-meta">
                  {formatDate(item.row.Date)}
                  {milestoneLine(item.row) && <em>{milestoneLine(item.row)}</em>}
                </span>
              </button>
            ))}
          </div>
        </section>

        <section className="dashboard-panel">
          <div className="dashboard-section-header">
            <div>
              <span className="dashboard-eyebrow">Player journeys</span>
              <h2>Crossover Spotlight</h2>
            </div>
            <button type="button" className="dashboard-link-button" onClick={() => onTabChange("crossover")}>
              Players
            </button>
          </div>
          <div className="dashboard-list">
            {crossoverSpotlight.map((player) => (
              <button
                key={player["BBRef ID"] ?? player.Name}
                type="button"
                className="dashboard-list-row dashboard-crossover-row"
                onClick={() => onPlayerClick?.(player, "batter")}
              >
                <span className="dashboard-list-main">
                  <strong>{player.Name}</strong>
                  <span>{player["NCAA Teams"]} / {player["MiLB Teams"]}</span>
                </span>
                <span className="dashboard-level-stack">
                  {levelDetails(player).map((detail) => (
                    <span
                      key={`${player.Name}-${detail.level}`}
                      style={{ backgroundColor: levelColors[detail.level] ?? "#667085" }}
                    >
                      {detail.level}
                    </span>
                  ))}
                </span>
                <span className="dashboard-list-meta">{player["Total Games"]} games</span>
              </button>
            ))}
          </div>
        </section>

        <section className="dashboard-panel">
          <div className="dashboard-section-header">
            <div>
              <span className="dashboard-eyebrow">Progress</span>
              <h2>Coverage Map</h2>
            </div>
            <button type="button" className="dashboard-link-button" onClick={() => onTabChange("checklist")}>
              Progress
            </button>
          </div>
          <div className="dashboard-progress-list">
            <ProgressRow label="NCAA teams seen" value={progress.ncaaSeen} total={progress.ncaaTotal} />
            <ProgressRow label="NCAA home teams" value={progress.ncaaHome} total={progress.ncaaTotal} />
            <ProgressRow label="Pro teams seen" value={progress.proSeen} total={progress.proTotal} />
            <ProgressRow label="Pro venues visited" value={progress.proVisited} total={progress.proVenueTotal} />
          </div>
        </section>

        <section className="dashboard-panel">
          <div className="dashboard-section-header">
            <div>
              <span className="dashboard-eyebrow">Team form</span>
              <h2>Best Records</h2>
            </div>
            <button type="button" className="dashboard-link-button" onClick={() => onTabChange("teams")}>
              Teams
            </button>
          </div>
          <div className="dashboard-list">
            {topTeams.map((team) => (
              <div key={`${team.Level}-${team.Team}`} className="dashboard-team-row">
                <span className="dashboard-team-name">
                  <TeamLogo team={team.Team} level={team.Level} size={22} data={data} />
                  <strong>{getTeamDisplayName(team.Team, data)}</strong>
                </span>
                <LevelBadge level={team.Level} levelColors={levelColors} />
                <span className="dashboard-team-record">{team.W}-{team.L}</span>
                <span className={Number(team.Diff) >= 0 ? "dashboard-diff positive" : "dashboard-diff"}>
                  {Number(team.Diff) >= 0 ? "+" : ""}{team.Diff}
                </span>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}

function ProgressRow({ label, value, total }: { label: string; value: number; total: number }) {
  const width = pct(value, total);
  return (
    <div className="dashboard-progress-row">
      <div className="dashboard-progress-top">
        <span>{label}</span>
        <strong>{value.toLocaleString()} / {total.toLocaleString()}</strong>
      </div>
      <div className="dashboard-progress-track" aria-hidden="true">
        <span style={{ width: `${width}%` }} />
      </div>
    </div>
  );
}
