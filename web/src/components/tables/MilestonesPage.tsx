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

function compareMilestoneCards(a: MilestoneCard, b: MilestoneCard) {
  const dateDelta = dateSortValue(b.row.Date) - dateSortValue(a.row.Date);
  if (dateDelta) return dateDelta;
  return a.priority - b.priority;
}

function statChips(row: MilestoneEntry) {
  return ["1B", "2B", "3B", "HR", "H", "RBI", "K", "IP", "BB", "SB", "TB", "ER", "R"]
    .filter((key) => row[key] !== undefined && row[key] !== "")
    .slice(0, 5)
    .map((key) => ({ key, value: row[key] }));
}

function shortMatchup(row: MilestoneEntry) {
  const opponent = row.Opponent ? `vs ${row.Opponent}` : "";
  return [row.Team, opponent].filter(Boolean).join(" ");
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

  const filteredTotal = Object.values(sectionCounts).reduce((sum, count) => sum + count, 0);
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

  const featuredMilestone = useMemo(() => {
    const rareLatest = filteredMilestoneCards
      .filter((card) => RARE_MILESTONE_KEYS.has(card.key))
      .sort(compareMilestoneCards);
    return rareLatest[0] ?? [...filteredMilestoneCards].sort(compareMilestoneCards)[0];
  }, [filteredMilestoneCards]);

  const recentMilestones = useMemo(
    () => [...filteredMilestoneCards].sort(compareMilestoneCards).slice(0, 5),
    [filteredMilestoneCards]
  );

  const rareMilestones = useMemo(() => {
    const latestByKey = new Map<string, MilestoneCard>();
    [...filteredMilestoneCards]
      .filter((card) => RARE_MILESTONE_KEYS.has(card.key))
      .sort(compareMilestoneCards)
      .forEach((card) => {
        if (!latestByKey.has(card.key)) latestByKey.set(card.key, card);
      });
    return [...latestByKey.values()].sort((a, b) => a.priority - b.priority).slice(0, 4);
  }, [filteredMilestoneCards]);

  const boardStats = useMemo(() => {
    const players = new Set(filteredMilestoneCards.map((card) => card.row.Player).filter(Boolean));
    const pitching = filteredMilestoneCards.filter((card) => card.playerType === "pitcher").length;
    return {
      shown: filteredMilestoneCards.length,
      players: players.size,
      batting: filteredMilestoneCards.length - pitching,
      pitching,
    };
  }, [filteredMilestoneCards]);

  return (
    <div className="milestones-page">
      {featuredMilestone && (
        <div className="milestone-board">
          <button
            type="button"
            className="milestone-feature-card"
            onClick={() => onPlayerClick?.(featuredMilestone.row, featuredMilestone.playerType)}
          >
            <span className="milestone-board-kicker">Featured feat</span>
            <span className="milestone-feature-topline">
              <LevelBadge
                level={String(featuredMilestone.row.Level ?? featuredMilestone.row.level ?? "")}
                levelColors={data.levelColors ?? {}}
              />
              <span>{formatDate(String(featuredMilestone.row.Date ?? ""))}</span>
            </span>
            <strong>{featuredMilestone.row.Player}</strong>
            <span className="milestone-feature-title">{featuredMilestone.label}</span>
            <span className="milestone-feature-matchup">
              {shortMatchup(featuredMilestone.row)}
              {featuredMilestone.row.Score && <em>{featuredMilestone.row.Score}</em>}
            </span>
            <span className="milestone-stat-chips">
              {statChips(featuredMilestone.row).map((chip) => (
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
              <span>{boardStats.shown.toLocaleString()} shown</span>
            </div>
            <div className="milestone-kpi-grid">
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
              <div>
                <strong>{rareMilestones.length.toLocaleString()}</strong>
                <span>Rare types</span>
              </div>
            </div>
            <div className="milestone-recent-list">
              {recentMilestones.map((card, index) => (
                <button
                  key={`${card.key}-${card.row.Date}-${card.row.Player}-${index}`}
                  type="button"
                  onClick={() => onPlayerClick?.(card.row, card.playerType)}
                >
                  <span className="milestone-mini-label">{card.label}</span>
                  <span>
                    <strong>{card.row.Player}</strong>
                    <em>{shortMatchup(card.row)}</em>
                  </span>
                  <time>{formatDate(String(card.row.Date ?? ""))}</time>
                </button>
              ))}
            </div>
          </section>
        </div>
      )}

      {rareMilestones.length > 0 && (
        <section className="milestone-rare-panel">
          <div className="milestone-board-header">
            <div>
              <span className="milestone-board-kicker">Rare feats</span>
              <h2>Biggest Signals</h2>
            </div>
          </div>
          <div className="milestone-rare-grid">
            {rareMilestones.map((card) => (
              <button
                key={`${card.key}-${card.row.Player}`}
                type="button"
                className="milestone-rare-card"
                onClick={() => onPlayerClick?.(card.row, card.playerType)}
              >
                <span>{card.label}</span>
                <strong>{card.row.Player}</strong>
                <em>{shortMatchup(card.row)}</em>
                <span className="milestone-stat-chips">
                  {statChips(card.row).slice(0, 3).map((chip) => (
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
          <span>{filteredTotal.toLocaleString()} shown</span>
          <span>{totalMilestones.toLocaleString()} total</span>
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
          <span>{filteredTotal.toLocaleString()}</span>
        </button>
        {MILESTONE_SECTIONS.map((section) => (
          <button
            key={section.id}
            type="button"
            className={`milestone-section-tab ${activeSection === section.id ? "active" : ""}`}
            onClick={() => setActiveSection(section.id)}
          >
            {section.label}
            <span>{sectionCounts[section.id].toLocaleString()}</span>
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

      {visibleSections.map((section) => {
        const visibleTables = section.tables.filter((table) => {
          const rows = data.milestones[table.key] ?? [];
          return filterMilestones(rows, levelFilter, leagueFilter, searchTerm).length > 0;
        });
        if (!visibleTables.length) return null;
        return (
          <section key={section.id} className="milestone-section">
            <div className="milestone-section-heading">
              <h3>{section.label}</h3>
              <span>{sectionCounts[section.id].toLocaleString()}</span>
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
