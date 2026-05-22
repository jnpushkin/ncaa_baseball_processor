"use client";

import { useMemo, useState } from "react";
import { MilestoneEntry, SiteData } from "@/types";
import { filterByLevelLeague } from "@/lib/filters";
import LevelLeagueFilter from "@/components/shared/LevelLeagueFilter";
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

  return (
    <div className="milestones-page">
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
