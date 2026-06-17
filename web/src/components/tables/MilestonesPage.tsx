"use client";

import { useMemo, useState } from "react";
import { MilestoneEntry, SiteData } from "@/types";
import { filterByLevelLeague } from "@/lib/filters";
import { formatDate } from "@/lib/baseball";
import LevelLeagueFilter from "@/components/shared/LevelLeagueFilter";
import LevelBadge from "@/components/shared/LevelBadge";
import MilestonesTable from "@/components/tables/MilestonesTable";

type MilestoneTableConfig = {
  key: string;
  title: string;
  columns: string[];
};

type MilestoneSection = {
  id: string;
  label: string;
  tables: MilestoneTableConfig[];
};

type MilestoneCard = {
  key: string;
  label: string;
  row: MilestoneEntry;
  sectionId: string;
  sectionLabel: string;
  priority: number;
  playerType: "batter" | "pitcher";
};

type MilestonePerformance = {
  id: string;
  row: MilestoneEntry;
  cards: MilestoneCard[];
  labels: string[];
  sectionIds: string[];
  priority: number;
  playerType: "batter" | "pitcher";
};

const MILESTONE_SECTIONS: MilestoneSection[] = [
  {
    id: "elite-pitching",
    label: "Elite Pitching",
    tables: [
      { key: "perfectGames", title: "Perfect Games", columns: ["Date", "Player", "Team", "Opponent", "IP", "K", "Score"] },
      { key: "noHitters", title: "No-Hitters", columns: ["Date", "Player", "Team", "Opponent", "IP", "K", "BB", "Score"] },
      { key: "oneHitters", title: "One-Hitters", columns: ["Date", "Player", "Team", "Opponent", "IP", "H", "K", "ER"] },
      { key: "twoHitters", title: "Two-Hitters", columns: ["Date", "Player", "Team", "Opponent", "IP", "H", "K", "ER"] },
      { key: "madduxGames", title: "Maddux Games", columns: ["Date", "Player", "Team", "Opponent", "IP", "H", "K", "ER"] },
    ],
  },
  {
    id: "complete-games",
    label: "CG & Shutouts",
    tables: [
      { key: "cgsoNoWalks", title: "CGSO No Walks", columns: ["Date", "Player", "Team", "Opponent", "IP", "H", "K"] },
      { key: "shutouts", title: "Shutouts", columns: ["Date", "Player", "Team", "Opponent", "IP", "K", "H", "BB"] },
      { key: "sevenInningShutouts", title: "7+ IP Shutouts", columns: ["Date", "Player", "Team", "Opponent", "IP", "K", "H", "BB"] },
      { key: "completeGames", title: "Complete Games", columns: ["Date", "Player", "Team", "Opponent", "IP", "K", "H", "ER"] },
      { key: "lowHitCg", title: "Low-Hit CG", columns: ["Date", "Player", "Team", "Opponent", "IP", "H", "K", "ER"] },
    ],
  },
  {
    id: "strikeouts",
    label: "Strikeouts",
    tables: [
      { key: "fifteenKGames", title: "15+ K Games", columns: ["Date", "Player", "Team", "Opponent", "K", "IP", "H", "ER"] },
      { key: "twelveKGames", title: "12+ K Games", columns: ["Date", "Player", "Team", "Opponent", "K", "IP", "H", "ER"] },
      { key: "tenKGames", title: "10+ K Games", columns: ["Date", "Player", "Team", "Opponent", "K", "IP", "H", "ER"] },
      { key: "dominantStarts", title: "Dominant Starts", columns: ["Date", "Player", "Team", "Opponent", "IP", "K", "H", "ER"] },
    ],
  },
  {
    id: "power",
    label: "Power",
    tables: [
      { key: "threeHrGames", title: "3+ HR Games", columns: ["Date", "Player", "Team", "Opponent", "HR", "H", "RBI", "R"] },
      { key: "multiHrGames", title: "Multi-HR Games", columns: ["Date", "Player", "Team", "Opponent", "HR", "H", "RBI"] },
      { key: "cycles", title: "Cycles", columns: ["Date", "Player", "Team", "Opponent", "1B", "2B", "3B", "HR"] },
      { key: "cycleWatch", title: "Cycle Watch", columns: ["Date", "Player", "Team", "Opponent", "1B", "2B", "3B", "HR"] },
      { key: "threeTotalBasesGames", title: "8+ Total Bases", columns: ["Date", "Player", "Team", "Opponent", "TB", "H", "HR", "RBI"] },
    ],
  },
  {
    id: "hits",
    label: "Hits",
    tables: [
      { key: "fiveHitGames", title: "5+ Hit Games", columns: ["Date", "Player", "Team", "Opponent", "H", "R", "RBI"] },
      { key: "fourHitGames", title: "4+ Hit Games", columns: ["Date", "Player", "Team", "Opponent", "H", "R", "RBI"] },
      { key: "multiDoubleGames", title: "Multi-Double Games", columns: ["Date", "Player", "Team", "Opponent", "2B", "H", "RBI"] },
      { key: "multiTripleGames", title: "Multi-Triple Games", columns: ["Date", "Player", "Team", "Opponent", "3B", "H", "RBI"] },
      { key: "perfectBattingGames", title: "Perfect Batting Games", columns: ["Date", "Player", "Team", "Opponent", "AB", "H", "K", "RBI"] },
    ],
  },
  {
    id: "run-production",
    label: "Run Production",
    tables: [
      { key: "sixRbiGames", title: "6+ RBI Games", columns: ["Date", "Player", "Team", "Opponent", "RBI", "H", "HR"] },
      { key: "fiveRbiGames", title: "5+ RBI Games", columns: ["Date", "Player", "Team", "Opponent", "RBI", "H", "HR"] },
      { key: "fourRbiGames", title: "4+ RBI Games", columns: ["Date", "Player", "Team", "Opponent", "RBI", "H", "HR"] },
      { key: "fourRunGames", title: "4+ Run Games", columns: ["Date", "Player", "Team", "Opponent", "R", "H", "RBI"] },
    ],
  },
  {
    id: "approach",
    label: "Speed & Patience",
    tables: [
      { key: "multiSbGames", title: "Multi-SB Games", columns: ["Date", "Player", "Team", "Opponent", "SB", "H", "R"] },
      { key: "fourWalkGames", title: "4+ Walk Games", columns: ["Date", "Player", "Team", "Opponent", "BB", "H", "R"] },
    ],
  },
];

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
  cycles: 3,
  threeHrGames: 4,
  fifteenKGames: 5,
  fiveHitGames: 6,
  sixRbiGames: 7,
  shutouts: 8,
  twelveKGames: 9,
  multiHrGames: 10,
  tenKGames: 11,
};

const RARE_MILESTONE_KEYS = new Set([
  "perfectGames",
  "noHitters",
  "cycles",
  "threeHrGames",
  "fifteenKGames",
  "fiveHitGames",
  "sixRbiGames",
  "shutouts",
  "twelveKGames",
]);

const PITCHING_MILESTONE_KEYS = new Set([
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

const SECTION_BY_TABLE_KEY = MILESTONE_SECTIONS.reduce<Record<string, MilestoneSection>>(
  (lookup, section) => {
    section.tables.forEach((table) => {
      lookup[table.key] = section;
    });
    return lookup;
  },
  {}
);

interface MilestonesPageProps {
  data: SiteData;
  levelFilter: string;
  setLevelFilter: (level: string) => void;
  leagueFilter: string;
  setLeagueFilter: (league: string) => void;
  onPlayerClick?: (row: MilestoneEntry, type: "batter" | "pitcher") => void;
}

function rowMatchesSearch(row: MilestoneEntry, searchTerm: string) {
  const tokens = searchTerm.trim().toLowerCase().split(/\s+/).filter(Boolean);
  if (!tokens.length) return true;
  const haystack = [
    row.Player,
    row.Team,
    row.Opponent,
    row.Level,
    row.level,
    row.League,
    row.league,
  ]
    .filter((value) => value !== undefined)
    .join(" ")
    .toLowerCase();
  return tokens.every((token) => haystack.includes(token));
}

function filterMilestones(
  rows: MilestoneEntry[],
  levelFilter: string,
  leagueFilter: string,
  searchTerm: string
) {
  return filterByLevelLeague(rows, levelFilter, leagueFilter).filter((row) =>
    rowMatchesSearch(row, searchTerm)
  );
}

function dateSortValue(value?: string | number) {
  if (!value) return 0;
  const raw = String(value);
  const parts = raw.split(/[/-]/).map((part) => Number(part));
  if (parts.length === 3) {
    const [month, day, year] = parts;
    if (month && day && year) return year * 10000 + month * 100 + day;
  }
  return Number(raw.replace(/\D/g, "")) || 0;
}

function statChips(row: MilestoneEntry, limit = 5) {
  return ["1B", "2B", "3B", "HR", "H", "RBI", "K", "IP", "BB", "SB", "TB", "ER", "R"]
    .filter((key) => row[key] !== undefined && row[key] !== "")
    .slice(0, limit)
    .map((key) => ({ key, value: row[key] }));
}

function shortMatchup(row: MilestoneEntry) {
  const opponent = row.Opponent ? `vs ${row.Opponent}` : "";
  return [row.Team, opponent].filter(Boolean).join(" ");
}

function performanceKey(card: MilestoneCard) {
  const row = card.row;
  return [
    row.GameID,
    row.Date,
    row.Player,
    row.Team,
    row.Opponent,
  ]
    .filter((part) => part !== undefined && part !== "")
    .join("|");
}

function buildPerformances(cards: MilestoneCard[]) {
  const grouped = new Map<string, MilestoneCard[]>();
  cards.forEach((card) => {
    const key = performanceKey(card);
    const current = grouped.get(key) ?? [];
    current.push(card);
    grouped.set(key, current);
  });
  return [...grouped.entries()].map(([id, group]) => {
    const sorted = [...group].sort((a, b) => a.priority - b.priority);
    const labels = [...new Set(sorted.map((card) => card.label))];
    const sectionIds = [...new Set(sorted.map((card) => card.sectionId))];
    const primary = sorted[0];
    return {
      id,
      row: primary.row,
      cards: sorted,
      labels,
      sectionIds,
      priority: primary.priority,
      playerType: primary.playerType,
    };
  });
}

function comparePerformances(a: MilestonePerformance, b: MilestonePerformance) {
  const dateDelta = dateSortValue(b.row.Date) - dateSortValue(a.row.Date);
  if (dateDelta) return dateDelta;
  return a.priority - b.priority;
}

function performanceChips(performance: MilestonePerformance, limit = 5) {
  const chips = new Map<string, string | number | undefined>();
  performance.cards.forEach((card) => {
    statChips(card.row, 10).forEach((chip) => {
      if (!chips.has(chip.key)) chips.set(chip.key, chip.value);
    });
  });
  return [...chips.entries()].slice(0, limit).map(([key, value]) => ({ key, value }));
}

function labelSummary(performance: MilestonePerformance, limit = 3) {
  const visible = performance.labels.slice(0, limit);
  const hidden = performance.labels.length - visible.length;
  return hidden > 0 ? `${visible.join(" + ")} +${hidden}` : visible.join(" + ");
}

export default function MilestonesPage({
  data,
  levelFilter,
  setLevelFilter,
  leagueFilter,
  setLeagueFilter,
  onPlayerClick,
}: MilestonesPageProps) {
  const [activeSection, setActiveSection] = useState("all");
  const [searchTerm, setSearchTerm] = useState("");
  const [showDetailedTables, setShowDetailedTables] = useState(false);
  const allMilestoneData = useMemo(() => {
    const all: MilestoneEntry[] = [];
    Object.values(data.milestones || {}).forEach((arr) => {
      if (Array.isArray(arr)) all.push(...arr);
    });
    return all;
  }, [data.milestones]);

  const sectionCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    MILESTONE_SECTIONS.forEach((section) => {
      counts[section.id] = section.tables.reduce((total, table) => {
        const rows = data.milestones[table.key] ?? [];
        return total + filterMilestones(rows, levelFilter, leagueFilter, searchTerm).length;
      }, 0);
    });
    return counts;
  }, [data.milestones, levelFilter, leagueFilter, searchTerm]);

  const totalMilestones = useMemo(
    () =>
      MILESTONE_SECTIONS.reduce(
        (sectionTotal, section) =>
          sectionTotal +
          section.tables.reduce(
            (tableTotal, table) => tableTotal + (data.milestones[table.key]?.length ?? 0),
            0
          ),
        0
      ),
    [data.milestones]
  );
  const sourceSummary = data.dataQuality?.summary;
  const sourceWarnings = sourceSummary?.sourceMergeWarnings ?? 0;
  const sourceReviewGames = sourceSummary?.sourceMergeReviewGames ?? 0;
  const mergedSourceGames = sourceSummary?.mergedSourceGames ?? 0;
  const unmergedCandidates = sourceSummary?.unmergedSourceCandidates ?? 0;
  const visibleSections =
    activeSection === "all"
      ? MILESTONE_SECTIONS
      : MILESTONE_SECTIONS.filter((section) => section.id === activeSection);
  const filteredMilestoneCards = useMemo<MilestoneCard[]>(() => {
    return Object.entries(data.milestones ?? {})
      .flatMap(([key, rows]) => {
        const section = SECTION_BY_TABLE_KEY[key];
        if (!section) return [];
        return (rows ?? []).map((row) => ({
          key,
          label: MILESTONE_LABELS[key] ?? key,
          row,
          sectionId: section?.id ?? "other",
          sectionLabel: section?.label ?? "Other",
          priority: MILESTONE_PRIORITY[key] ?? 99,
          playerType: PITCHING_MILESTONE_KEYS.has(key) ? ("pitcher" as const) : ("batter" as const),
        }));
      })
      .filter((card) => filterMilestones([card.row], levelFilter, leagueFilter, searchTerm).length > 0);
  }, [data.milestones, levelFilter, leagueFilter, searchTerm]);

  const filteredPerformances = useMemo(
    () => buildPerformances(filteredMilestoneCards).sort(comparePerformances),
    [filteredMilestoneCards]
  );

  const visibleMilestoneCards = useMemo(
    () =>
      activeSection === "all"
        ? filteredMilestoneCards
        : filteredMilestoneCards.filter((card) => card.sectionId === activeSection),
    [activeSection, filteredMilestoneCards]
  );

  const visiblePerformances = useMemo(
    () => buildPerformances(visibleMilestoneCards).sort(comparePerformances),
    [visibleMilestoneCards]
  );

  const sectionPerformanceCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    MILESTONE_SECTIONS.forEach((section) => {
      const cards = filteredMilestoneCards.filter((card) => card.sectionId === section.id);
      counts[section.id] = buildPerformances(cards).length;
    });
    return counts;
  }, [filteredMilestoneCards]);

  const featuredPerformance = useMemo(() => {
    const rareLatest = visiblePerformances
      .filter((performance) =>
        performance.cards.some((card) => RARE_MILESTONE_KEYS.has(card.key))
      )
      .sort(comparePerformances);
    return rareLatest[0] ?? visiblePerformances[0];
  }, [visiblePerformances]);

  const recentPerformances = useMemo(
    () => visiblePerformances.slice(0, 5),
    [visiblePerformances]
  );

  const performanceList = useMemo(
    () => visiblePerformances.slice(0, 12),
    [visiblePerformances]
  );

  const rarePerformances = useMemo(() => {
    const seen = new Set<string>();
    return visiblePerformances
      .filter((performance) =>
        performance.cards.some((card) => RARE_MILESTONE_KEYS.has(card.key))
      )
      .filter((performance) => {
        if (seen.has(performance.id)) return false;
        seen.add(performance.id);
        return true;
      });
  }, [visiblePerformances]);

  const boardStats = useMemo(() => {
    const players = new Set(visiblePerformances.map((performance) => performance.row.Player).filter(Boolean));
    const pitching = visiblePerformances.filter((performance) => performance.playerType === "pitcher").length;
    return {
      performances: visiblePerformances.length,
      tags: visibleMilestoneCards.length,
      players: players.size,
      batting: visiblePerformances.length - pitching,
      pitching,
    };
  }, [visibleMilestoneCards, visiblePerformances]);

  return (
    <div className="milestones-page">
      {featuredPerformance && (
        <div className="milestone-board">
          <button
            type="button"
            className="milestone-feature-card"
            onClick={() => onPlayerClick?.(featuredPerformance.row, featuredPerformance.playerType)}
          >
            <span className="milestone-board-kicker">Featured feat</span>
            <span className="milestone-feature-topline">
              <LevelBadge
                level={String(featuredPerformance.row.Level ?? featuredPerformance.row.level ?? "")}
                levelColors={data.levelColors ?? {}}
              />
              <span>{formatDate(String(featuredPerformance.row.Date ?? ""))}</span>
            </span>
            <strong>{featuredPerformance.row.Player}</strong>
            <span className="milestone-feature-title">{labelSummary(featuredPerformance)}</span>
            <span className="milestone-feature-matchup">
              {shortMatchup(featuredPerformance.row)}
              {featuredPerformance.row.Score && <em>{featuredPerformance.row.Score}</em>}
            </span>
            <span className="milestone-stat-chips">
              {performanceChips(featuredPerformance).map((chip) => (
                <span key={chip.key}>
                  {chip.key} <strong>{chip.value}</strong>
                </span>
              ))}
            </span>
          </button>

          <section className="milestone-board-panel">
            <div className="milestone-board-header">
              <div>
                <span className="milestone-board-kicker">Current view</span>
                <h2>Milestone Board</h2>
              </div>
              <span>{boardStats.performances.toLocaleString()} performances</span>
            </div>
            <div className="milestone-kpi-grid">
              <div>
                <strong>{boardStats.tags.toLocaleString()}</strong>
                <span>Tags</span>
              </div>
              <div>
                <strong>{boardStats.players.toLocaleString()}</strong>
                <span>Players</span>
              </div>
              <div>
                <strong>{boardStats.batting.toLocaleString()}</strong>
                <span>Batting</span>
              </div>
              <div>
                <strong>{boardStats.pitching.toLocaleString()}</strong>
                <span>Pitching</span>
              </div>
            </div>
            <div className="milestone-recent-list">
              {recentPerformances.map((performance, index) => (
                <button
                  key={`${performance.id}-${index}`}
                  type="button"
                  onClick={() => onPlayerClick?.(performance.row, performance.playerType)}
                >
                  <span className="milestone-mini-label">{labelSummary(performance, 1)}</span>
                  <span>
                    <strong>{performance.row.Player}</strong>
                    <em>{shortMatchup(performance.row)}</em>
                  </span>
                  <time>{formatDate(String(performance.row.Date ?? ""))}</time>
                </button>
              ))}
            </div>
          </section>
        </div>
      )}

      {rarePerformances.length > 0 && (
        <section className="milestone-rare-panel">
          <div className="milestone-board-header">
            <div>
              <span className="milestone-board-kicker">Rare feats</span>
              <h2>Biggest Signals</h2>
            </div>
          </div>
          <div className="milestone-rare-grid">
            {rarePerformances.slice(0, 4).map((performance) => (
              <button
                key={performance.id}
                type="button"
                className="milestone-rare-card"
                onClick={() => onPlayerClick?.(performance.row, performance.playerType)}
              >
                <span>{labelSummary(performance, 2)}</span>
                <strong>{performance.row.Player}</strong>
                <em>{shortMatchup(performance.row)}</em>
                <span className="milestone-stat-chips">
                  {performanceChips(performance, 3).map((chip) => (
                    <span key={chip.key}>
                      {chip.key} <strong>{chip.value}</strong>
                    </span>
                  ))}
                </span>
              </button>
            ))}
          </div>
        </section>
      )}

      <section className="milestone-performance-panel">
        <div className="milestone-board-header">
          <div>
            <span className="milestone-board-kicker">Condensed view</span>
            <h2>Player-Game Performances</h2>
          </div>
          <span>
            {performanceList.length.toLocaleString()} latest of{" "}
            {visiblePerformances.length.toLocaleString()}
          </span>
        </div>
        <div className="milestone-performance-grid">
          {performanceList.map((performance) => (
            <button
              key={performance.id}
              type="button"
              className="milestone-performance-card"
              onClick={() => onPlayerClick?.(performance.row, performance.playerType)}
            >
              <span className="milestone-performance-topline">
                <LevelBadge
                  level={String(performance.row.Level ?? performance.row.level ?? "")}
                  levelColors={data.levelColors ?? {}}
                />
                <time>{formatDate(String(performance.row.Date ?? ""))}</time>
              </span>
              <strong>{performance.row.Player}</strong>
              <em>{shortMatchup(performance.row)}</em>
              <span className="milestone-label-stack">
                {performance.labels.slice(0, 4).map((label) => (
                  <span key={label}>{label}</span>
                ))}
                {performance.labels.length > 4 && (
                  <span>+{performance.labels.length - 4}</span>
                )}
              </span>
              <span className="milestone-stat-chips">
                {performanceChips(performance, 4).map((chip) => (
                  <span key={chip.key}>
                    {chip.key} <strong>{chip.value}</strong>
                  </span>
                ))}
              </span>
            </button>
          ))}
        </div>
      </section>

      <div className="milestones-toolbar panel">
        <LevelLeagueFilter
          levelFilter={levelFilter}
          setLevelFilter={setLevelFilter}
          leagueFilter={leagueFilter}
          setLeagueFilter={setLeagueFilter}
          data={allMilestoneData}
          levelOrder={data.levelOrder}
          showSearch
          searchTerm={searchTerm}
          setSearchTerm={setSearchTerm}
          searchPlaceholder="Search players, teams, opponents..."
        />
        <div className="milestones-summary-strip">
          <span>{visiblePerformances.length.toLocaleString()} performances</span>
          <span>{visibleMilestoneCards.length.toLocaleString()} milestone tags</span>
          <span>{filteredPerformances.length.toLocaleString()} total performances</span>
          <span>{totalMilestones.toLocaleString()} total tags</span>
          <span className={sourceWarnings ? "source-review-warning" : ""}>
            {sourceWarnings
              ? `${sourceReviewGames.toLocaleString()} source-review games`
              : `${mergedSourceGames.toLocaleString()} source checks`}
          </span>
          {unmergedCandidates > 0 && (
            <span className="source-review-warning">
              {unmergedCandidates.toLocaleString()} kept separate
            </span>
          )}
        </div>
      </div>

      <div className="milestone-section-tabs" aria-label="Milestone sections">
        <button
          type="button"
          className={`milestone-section-tab ${activeSection === "all" ? "active" : ""}`}
          onClick={() => setActiveSection("all")}
        >
          All
          <span>{filteredPerformances.length.toLocaleString()}</span>
        </button>
        {MILESTONE_SECTIONS.map((section) => (
          <button
            key={section.id}
            type="button"
            className={`milestone-section-tab ${activeSection === section.id ? "active" : ""}`}
            onClick={() => setActiveSection(section.id)}
          >
            {section.label}
            <span>{sectionPerformanceCounts[section.id].toLocaleString()}</span>
          </button>
        ))}
      </div>

      {sourceWarnings > 0 && (
        <div className="milestones-quality-note">
          <strong>{sourceReviewGames.toLocaleString()} merged games need source review</strong>
          <span>{sourceWarnings.toLocaleString()} stat-field disagreements found; PDF box-score stats are retained while NCAA API identities are used for player links.</span>
          {unmergedCandidates > 0 && (
            <span>{unmergedCandidates.toLocaleString()} same-date/team source candidate was kept as a separate game because the scores differ.</span>
          )}
        </div>
      )}

      <div className="milestone-detail-toggle panel">
        <div>
          <span className="milestone-board-kicker">Detailed tags</span>
          <strong>Category tables</strong>
          <p>
            {visibleMilestoneCards.length.toLocaleString()} filtered milestone tags across{" "}
            {visiblePerformances.length.toLocaleString()} condensed performances.
          </p>
        </div>
        <button
          type="button"
          className="dashboard-link-button"
          onClick={() => setShowDetailedTables((value) => !value)}
        >
          {showDetailedTables ? "Hide tables" : "Show tables"}
        </button>
      </div>

      {showDetailedTables &&
        visibleSections.map((section) => {
          const visibleTables = section.tables.filter((table) => {
            const rows = data.milestones[table.key] ?? [];
            return filterMilestones(rows, levelFilter, leagueFilter, searchTerm).length > 0;
          });
          if (!visibleTables.length) return null;
          return (
            <section key={section.id} className="milestone-section">
              <div className="milestone-section-heading">
                <h3>{section.label}</h3>
                <span>{sectionCounts[section.id].toLocaleString()} tags</span>
              </div>
              {visibleTables.map((table) => (
                <MilestonesTable
                  key={table.key}
                  title={table.title}
                  data={data.milestones[table.key] ?? []}
                  columns={table.columns}
                  levelFilter={levelFilter}
                  leagueFilter={leagueFilter}
                  searchTerm={searchTerm}
                  onPlayerClick={onPlayerClick}
                  siteData={data}
                />
              ))}
            </section>
          );
        })}
    </div>
  );
}
