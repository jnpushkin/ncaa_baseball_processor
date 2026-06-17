"use client";

import { useMemo, useState } from "react";
import { MilestoneEntry, SiteData } from "@/types";
import { filterByLevelLeague } from "@/lib/filters";
import { formatDate } from "@/lib/baseball";
import LevelLeagueFilter from "@/components/shared/LevelLeagueFilter";
import LevelBadge from "@/components/shared/LevelBadge";
import MilestonesTable from "@/components/tables/MilestonesTable";
import {
  MAJOR_MILESTONE_KEYS,
  getMilestoneLabel,
  getMilestonePlayerType,
  getMilestonePriority,
  milestoneDateSortValue,
  milestoneStatChips,
} from "@/lib/milestones";

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
      { key: "fifteenKGames", title: "15+ K Games", columns: ["Date", "Player", "Team", "Opponent", "K", "IP", "H", "ER"] },
      { key: "madduxGames", title: "Maddux Games", columns: ["Date", "Player", "Team", "Opponent", "IP", "H", "K", "ER"] },
      { key: "cgsoNoWalks", title: "CGSO No Walks", columns: ["Date", "Player", "Team", "Opponent", "IP", "H", "K"] },
      { key: "shutouts", title: "Shutouts", columns: ["Date", "Player", "Team", "Opponent", "IP", "K", "H", "BB"] },
    ],
  },
  {
    id: "elite-batting",
    label: "Elite Batting",
    tables: [
      { key: "cycles", title: "Cycles", columns: ["Date", "Player", "Team", "Opponent", "1B", "2B", "3B", "HR"] },
      { key: "threeHrGames", title: "3+ HR Games", columns: ["Date", "Player", "Team", "Opponent", "HR", "H", "RBI", "R"] },
      { key: "fiveHitGames", title: "5+ Hit Games", columns: ["Date", "Player", "Team", "Opponent", "H", "R", "RBI"] },
      { key: "sixRbiGames", title: "6+ RBI Games", columns: ["Date", "Player", "Team", "Opponent", "RBI", "H", "HR"] },
    ],
  },
];

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
  const dateDelta = milestoneDateSortValue(b.row.Date) - milestoneDateSortValue(a.row.Date);
  if (dateDelta) return dateDelta;
  return a.priority - b.priority;
}

function performanceChips(performance: MilestonePerformance, limit = 5) {
  const chips = new Map<string, string | number | undefined>();
  performance.cards.forEach((card) => {
    milestoneStatChips(card.row, 10).forEach((chip) => {
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
    MILESTONE_SECTIONS.flatMap((section) => section.tables).forEach((table) => {
      const arr = data.milestones[table.key] ?? [];
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
        if (!MAJOR_MILESTONE_KEYS.has(key)) return [];
        if (!section) return [];
        return (rows ?? []).map((row) => ({
          key,
          label: getMilestoneLabel(key),
          row,
          sectionId: section?.id ?? "other",
          sectionLabel: section?.label ?? "Other",
          priority: getMilestonePriority(key),
          playerType: getMilestonePlayerType(key),
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
        performance.cards.some((card) => MAJOR_MILESTONE_KEYS.has(card.key))
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
            <span className="milestone-board-kicker">Featured milestone</span>
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
                <span className="milestone-board-kicker">Curated view</span>
                <h2>Major Milestones</h2>
              </div>
              <span>{boardStats.performances.toLocaleString()} player games</span>
            </div>
            <div className="milestone-kpi-grid">
              <div>
                <strong>{boardStats.tags.toLocaleString()}</strong>
                <span>Events</span>
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

      <section className="milestone-performance-panel">
        <div className="milestone-board-header">
          <div>
            <span className="milestone-board-kicker">Latest</span>
            <h2>Milestone Games</h2>
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
          <span>{visiblePerformances.length.toLocaleString()} player games</span>
          <span>{visibleMilestoneCards.length.toLocaleString()} milestone events</span>
          <span>{filteredPerformances.length.toLocaleString()} total player games</span>
          <span>{totalMilestones.toLocaleString()} total events</span>
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
          <span className="milestone-board-kicker">Detailed view</span>
          <strong>Category tables</strong>
          <p>
            {visibleMilestoneCards.length.toLocaleString()} filtered milestone events across{" "}
            {visiblePerformances.length.toLocaleString()} player games.
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
                <span>{sectionCounts[section.id].toLocaleString()} events</span>
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
