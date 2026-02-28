"use client";

import { useState, useMemo, useEffect, useCallback } from "react";
import dynamic from "next/dynamic";
import type { SiteData, NormalizedPlayer, MilestoneEntry, UnifiedBatter, UnifiedPitcher } from "@/types";
import Header from "@/components/layout/Header";
import Footer from "@/components/layout/Footer";
import TabBar from "@/components/layout/TabBar";
import StatsGrid from "@/components/stats/StatsGrid";
import UnifiedGameLog from "@/components/games/UnifiedGameLog";
import CalendarView from "@/components/games/CalendarView";
import UnifiedBattersTable from "@/components/tables/UnifiedBattersTable";
import UnifiedPitchersTable from "@/components/tables/UnifiedPitchersTable";
import TeamRecords from "@/components/tables/TeamRecords";
import MilestonesTable from "@/components/tables/MilestonesTable";
import CrossoverPlayers from "@/components/tables/CrossoverPlayers";
import ScorigamiGrid from "@/components/games/ScorigamiGrid";
import Checklist from "@/components/checklist/Checklist";
import UpcomingGames from "@/components/schedule/UpcomingGames";
import PlayerModal from "@/components/shared/PlayerModal";
import LevelLeagueFilter from "@/components/shared/LevelLeagueFilter";

const DynamicSchoolMap = dynamic(
  () => import("@/components/maps/DynamicSchoolMap"),
  { ssr: false, loading: () => <div className="panel"><div className="panel-header"><h2>Stadium Map</h2></div><div style={{ padding: "20px", textAlign: "center", color: "#666" }}>Loading map...</div></div> }
);

interface AppProps {
  data: SiteData;
}

const TAB_HASH_MAP: Record<string, string> = {
  allGames: "games",
  calendar: "calendar",
  unifiedBatters: "batters",
  unifiedPitchers: "pitchers",
  teams: "teams",
  milestones: "milestones",
  crossover: "crossover",
  schedule: "schedule",
  scorigami: "scorigami",
  checklist: "checklist",
  map: "map",
};

const HASH_TAB_MAP = Object.fromEntries(
  Object.entries(TAB_HASH_MAP).map(([k, v]) => [v, k])
);

export default function App({ data }: AppProps) {
  const getInitialTab = () => {
    if (typeof window !== "undefined") {
      const hash = window.location.hash.replace("#", "");
      if (hash && HASH_TAB_MAP[hash]) return HASH_TAB_MAP[hash];
    }
    return "allGames";
  };

  const [activeTab, setActiveTab] = useState(getInitialTab);
  const [selectedPlayer, setSelectedPlayer] = useState<NormalizedPlayer | null>(null);
  const [playerType, setPlayerType] = useState<"batter" | "pitcher" | null>(null);
  const [milestoneLevelFilter, setMilestoneLevelFilter] = useState("All");
  const [milestoneLeagueFilter, setMilestoneLeagueFilter] = useState("All");

  const handleTabChange = useCallback((tabId: string) => {
    setActiveTab(tabId);
    const hash = TAB_HASH_MAP[tabId];
    if (hash && typeof window !== "undefined") {
      window.history.replaceState(null, "", `#${hash}`);
    }
  }, []);

  useEffect(() => {
    const onHashChange = () => {
      const hash = window.location.hash.replace("#", "");
      if (hash && HASH_TAB_MAP[hash]) {
        setActiveTab(HASH_TAB_MAP[hash]);
      }
    };
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const handlePlayerClick = (player: any, type: "batter" | "pitcher") => {
    const normalized: NormalizedPlayer = {
      name: (player.Name || player.name || player.Player || "") as string,
      team: (player.Team || player.team || "") as string,
      bref_id: (player["BBRef ID"] || player.bref_id || "") as string,
      level: (player.Level || player.level || "") as string,
      levels: (player.levels ||
        player["Level Details"] ||
        (player.Level || player.level
          ? [{ level: (player.Level || player.level) as string }]
          : [])) as { level: string }[],
    };
    setSelectedPlayer(normalized);
    setPlayerType(type);
  };

  const closeModal = () => {
    setSelectedPlayer(null);
    setPlayerType(null);
  };

  const selectedPlayerGames = useMemo(() => {
    if (!selectedPlayer) return [];
    const brefId = selectedPlayer.bref_id;
    const name = selectedPlayer.name;
    const games = playerType === "batter" ? data.batterGames : data.pitcherGames;
    if (brefId) {
      const byId = games.filter((g) => g.bref_id === brefId);
      if (byId.length > 0) return byId;
    }
    return games.filter((g) => (g.Name || g.name) === name);
  }, [selectedPlayer, playerType, data.batterGames, data.pitcherGames]);

  const selectedPlayerMilestones = useMemo(() => {
    if (!selectedPlayer) return [];
    const name = selectedPlayer.name;
    const brefId = selectedPlayer.bref_id;
    const results: (MilestoneEntry & { milestoneType: string })[] = [];
    const milestoneLabels: Record<string, string> = {
      threeHrGames: "3+ HR", multiHrGames: "Multi-HR", fiveHitGames: "5+ Hits",
      fourHitGames: "4+ Hits", cycles: "Cycle", cycleWatch: "Cycle Watch",
      sixRbiGames: "6+ RBI", fiveRbiGames: "5+ RBI", fourRbiGames: "4+ RBI",
      multiDoubleGames: "Multi-2B", multiTripleGames: "Multi-3B", multiSbGames: "Multi-SB",
      fourWalkGames: "4+ BB", fourRunGames: "4+ Runs", threeTotalBasesGames: "8+ TB",
      perfectGames: "Perfect Game", noHitters: "No-Hitter", oneHitters: "1-Hitter",
      twoHitters: "2-Hitter", shutouts: "Shutout", cgsoNoWalks: "CGSO No BB",
      completeGames: "Complete Game", lowHitCg: "Low-Hit CG",
      sevenInningShutouts: "7+ IP SO", madduxGames: "Maddux",
      fifteenKGames: "15+ K", twelveKGames: "12+ K", tenKGames: "10+ K",
      dominantStarts: "Dominant Start",
    };
    Object.entries(data.milestones || {}).forEach(([key, arr]) => {
      if (!Array.isArray(arr)) return;
      arr.forEach((entry) => {
        const entryName = entry.Player || (entry as Record<string, unknown>).name || "";
        const entryBref = entry.bref_id || "";
        if ((brefId && entryBref === brefId) || entryName === name) {
          results.push({ ...entry, milestoneType: milestoneLabels[key] || key });
        }
      });
    });
    return results;
  }, [selectedPlayer, data.milestones]);

  const selectedUnifiedStats = useMemo(() => {
    if (!selectedPlayer) return null;
    const brefId = selectedPlayer.bref_id;
    const name = selectedPlayer.name;
    if (playerType === "batter") {
      const found = brefId
        ? data.unifiedBatters.find((b) => b.bref_id === brefId)
        : data.unifiedBatters.find((b) => b.name === name);
      return found ?? null;
    } else {
      const found = brefId
        ? data.unifiedPitchers.find((p) => p.bref_id === brefId)
        : data.unifiedPitchers.find((p) => p.name === name);
      return found ?? null;
    }
  }, [selectedPlayer, playerType, data.unifiedBatters, data.unifiedPitchers]);

  const allMilestoneData = useMemo(() => {
    const all: MilestoneEntry[] = [];
    Object.values(data.milestones || {}).forEach((arr) => {
      if (Array.isArray(arr)) all.push(...arr);
    });
    return all;
  }, [data.milestones]);

  const hasCrossover = data.crossoverPlayers && data.crossoverPlayers.length > 0;
  const hasSchedule = data.scheduleGames && data.scheduleGames.length > 0;

  const tabs = [
    { id: "allGames", label: "All Games" },
    { id: "calendar", label: "Calendar" },
    { id: "unifiedBatters", label: "Batters" },
    { id: "unifiedPitchers", label: "Pitchers" },
    { id: "teams", label: "Teams" },
    { id: "milestones", label: "Milestones" },
    ...(hasCrossover ? [{ id: "crossover", label: "Crossover" }] : []),
    ...(hasSchedule ? [{ id: "schedule", label: "Schedule" }] : []),
    { id: "scorigami", label: "Scorigami" },
    { id: "checklist", label: "Checklist" },
    { id: "map", label: "Map" },
  ];

  // Build header subtitle
  const headerSubtitle = useMemo(() => {
    const s = data.summary;
    const parts = [`${s.allGames} Games`, `${s.unifiedBatters} Batters`, `${s.unifiedPitchers} Pitchers`];
    if (s.crossoverPlayers > 0) parts.push(`${s.crossoverPlayers} Crossover Players`);
    return parts.join(" | ");
  }, [data.summary]);

  return (
    <>
      <Header subtitle={headerSubtitle} data={data} onPlayerClick={handlePlayerClick} />
      <div className="container">
        <StatsGrid data={data.summary} />
        <TabBar tabs={tabs} activeTab={activeTab} onTabChange={handleTabChange} />

        <div key={activeTab} className="tab-content-enter">
        {activeTab === "allGames" && <UnifiedGameLog games={data.unifiedGameLog} data={data} />}
        {activeTab === "calendar" && <CalendarView games={data.unifiedGameLog} data={data} />}
        {activeTab === "teams" && <TeamRecords teams={data.teamRecords} data={data} />}

        {activeTab === "milestones" && (
          <div>
            <LevelLeagueFilter
              levelFilter={milestoneLevelFilter}
              setLevelFilter={setMilestoneLevelFilter}
              leagueFilter={milestoneLeagueFilter}
              setLeagueFilter={setMilestoneLeagueFilter}
              data={allMilestoneData}
              levelOrder={data.levelOrder}
            />

            <h3 className="milestones-section-header">Elite Pitching Performances</h3>
            <MilestonesTable title="Perfect Games" data={data.milestones.perfectGames} columns={["Date", "Player", "Team", "Opponent", "IP", "K", "Score"]} levelFilter={milestoneLevelFilter} leagueFilter={milestoneLeagueFilter} onPlayerClick={handlePlayerClick} siteData={data} />
            <MilestonesTable title="No-Hitters" data={data.milestones.noHitters} columns={["Date", "Player", "Team", "Opponent", "IP", "K", "BB", "Score"]} levelFilter={milestoneLevelFilter} leagueFilter={milestoneLeagueFilter} onPlayerClick={handlePlayerClick} siteData={data} />
            <MilestonesTable title="One-Hitters" data={data.milestones.oneHitters} columns={["Date", "Player", "Team", "Opponent", "IP", "H", "K", "ER"]} levelFilter={milestoneLevelFilter} leagueFilter={milestoneLeagueFilter} onPlayerClick={handlePlayerClick} siteData={data} />
            <MilestonesTable title="Two-Hitters" data={data.milestones.twoHitters} columns={["Date", "Player", "Team", "Opponent", "IP", "H", "K", "ER"]} levelFilter={milestoneLevelFilter} leagueFilter={milestoneLeagueFilter} onPlayerClick={handlePlayerClick} siteData={data} />
            <MilestonesTable title="Maddux Games (CG, <100 pitches)" data={data.milestones.madduxGames} columns={["Date", "Player", "Team", "Opponent", "IP", "H", "K", "ER"]} levelFilter={milestoneLevelFilter} leagueFilter={milestoneLeagueFilter} onPlayerClick={handlePlayerClick} siteData={data} />

            <h3 className="milestones-section-header">Complete Games & Shutouts</h3>
            <MilestonesTable title="CGSO No Walks" data={data.milestones.cgsoNoWalks} columns={["Date", "Player", "Team", "Opponent", "IP", "H", "K"]} levelFilter={milestoneLevelFilter} leagueFilter={milestoneLeagueFilter} onPlayerClick={handlePlayerClick} siteData={data} />
            <MilestonesTable title="Shutouts" data={data.milestones.shutouts} columns={["Date", "Player", "Team", "Opponent", "IP", "K", "H", "BB"]} levelFilter={milestoneLevelFilter} leagueFilter={milestoneLeagueFilter} onPlayerClick={handlePlayerClick} siteData={data} />
            <MilestonesTable title="7+ IP Shutouts" data={data.milestones.sevenInningShutouts} columns={["Date", "Player", "Team", "Opponent", "IP", "K", "H", "BB"]} levelFilter={milestoneLevelFilter} leagueFilter={milestoneLeagueFilter} onPlayerClick={handlePlayerClick} siteData={data} />
            <MilestonesTable title="Complete Games" data={data.milestones.completeGames} columns={["Date", "Player", "Team", "Opponent", "IP", "K", "H", "ER"]} levelFilter={milestoneLevelFilter} leagueFilter={milestoneLeagueFilter} onPlayerClick={handlePlayerClick} siteData={data} />
            <MilestonesTable title="Low-Hit CG" data={data.milestones.lowHitCg} columns={["Date", "Player", "Team", "Opponent", "IP", "H", "K", "ER"]} levelFilter={milestoneLevelFilter} leagueFilter={milestoneLeagueFilter} onPlayerClick={handlePlayerClick} siteData={data} />

            <h3 className="milestones-section-header">Strikeout Performances</h3>
            <MilestonesTable title="15+ K Games" data={data.milestones.fifteenKGames} columns={["Date", "Player", "Team", "Opponent", "K", "IP", "H", "ER"]} levelFilter={milestoneLevelFilter} leagueFilter={milestoneLeagueFilter} onPlayerClick={handlePlayerClick} siteData={data} />
            <MilestonesTable title="12+ K Games" data={data.milestones.twelveKGames} columns={["Date", "Player", "Team", "Opponent", "K", "IP", "H", "ER"]} levelFilter={milestoneLevelFilter} leagueFilter={milestoneLeagueFilter} onPlayerClick={handlePlayerClick} siteData={data} />
            <MilestonesTable title="10+ K Games" data={data.milestones.tenKGames} columns={["Date", "Player", "Team", "Opponent", "K", "IP", "H", "ER"]} levelFilter={milestoneLevelFilter} leagueFilter={milestoneLeagueFilter} onPlayerClick={handlePlayerClick} siteData={data} />
            <MilestonesTable title="Dominant Starts (7+ IP, 10+ K)" data={data.milestones.dominantStarts} columns={["Date", "Player", "Team", "Opponent", "IP", "K", "H", "ER"]} levelFilter={milestoneLevelFilter} leagueFilter={milestoneLeagueFilter} onPlayerClick={handlePlayerClick} siteData={data} />

            <h3 className="milestones-section-header">Big Batting Performances</h3>
            <MilestonesTable title="3+ HR Games" data={data.milestones.threeHrGames} columns={["Date", "Player", "Team", "Opponent", "HR", "H", "RBI", "R"]} levelFilter={milestoneLevelFilter} leagueFilter={milestoneLeagueFilter} onPlayerClick={handlePlayerClick} siteData={data} />
            <MilestonesTable title="Multi-HR Games" data={data.milestones.multiHrGames} columns={["Date", "Player", "Team", "Opponent", "HR", "H", "RBI"]} levelFilter={milestoneLevelFilter} leagueFilter={milestoneLeagueFilter} onPlayerClick={handlePlayerClick} siteData={data} />
            <MilestonesTable title="Cycles" data={data.milestones.cycles} columns={["Date", "Player", "Team", "Opponent", "1B", "2B", "3B", "HR"]} levelFilter={milestoneLevelFilter} leagueFilter={milestoneLeagueFilter} onPlayerClick={handlePlayerClick} siteData={data} />
            <MilestonesTable title="Cycle Watch (3 of 4)" data={data.milestones.cycleWatch} columns={["Date", "Player", "Team", "Opponent", "1B", "2B", "3B", "HR"]} levelFilter={milestoneLevelFilter} leagueFilter={milestoneLeagueFilter} onPlayerClick={handlePlayerClick} siteData={data} />

            <h3 className="milestones-section-header">Hit Milestones</h3>
            <MilestonesTable title="5+ Hit Games" data={data.milestones.fiveHitGames} columns={["Date", "Player", "Team", "Opponent", "H", "R", "RBI"]} levelFilter={milestoneLevelFilter} leagueFilter={milestoneLeagueFilter} onPlayerClick={handlePlayerClick} siteData={data} />
            <MilestonesTable title="4+ Hit Games" data={data.milestones.fourHitGames} columns={["Date", "Player", "Team", "Opponent", "H", "R", "RBI"]} levelFilter={milestoneLevelFilter} leagueFilter={milestoneLeagueFilter} onPlayerClick={handlePlayerClick} siteData={data} />
            <MilestonesTable title="Multi-Double Games" data={data.milestones.multiDoubleGames} columns={["Date", "Player", "Team", "Opponent", "2B", "H", "RBI"]} levelFilter={milestoneLevelFilter} leagueFilter={milestoneLeagueFilter} onPlayerClick={handlePlayerClick} siteData={data} />
            <MilestonesTable title="Multi-Triple Games" data={data.milestones.multiTripleGames} columns={["Date", "Player", "Team", "Opponent", "3B", "H", "RBI"]} levelFilter={milestoneLevelFilter} leagueFilter={milestoneLeagueFilter} onPlayerClick={handlePlayerClick} siteData={data} />
            <MilestonesTable title="8+ Total Bases" data={data.milestones.threeTotalBasesGames} columns={["Date", "Player", "Team", "Opponent", "H", "HR", "RBI"]} levelFilter={milestoneLevelFilter} leagueFilter={milestoneLeagueFilter} onPlayerClick={handlePlayerClick} siteData={data} />

            <h3 className="milestones-section-header">Run Production</h3>
            <MilestonesTable title="6+ RBI Games" data={data.milestones.sixRbiGames} columns={["Date", "Player", "Team", "Opponent", "RBI", "H", "HR"]} levelFilter={milestoneLevelFilter} leagueFilter={milestoneLeagueFilter} onPlayerClick={handlePlayerClick} siteData={data} />
            <MilestonesTable title="5+ RBI Games" data={data.milestones.fiveRbiGames} columns={["Date", "Player", "Team", "Opponent", "RBI", "H", "HR"]} levelFilter={milestoneLevelFilter} leagueFilter={milestoneLeagueFilter} onPlayerClick={handlePlayerClick} siteData={data} />
            <MilestonesTable title="4+ RBI Games" data={data.milestones.fourRbiGames} columns={["Date", "Player", "Team", "Opponent", "RBI", "H", "HR"]} levelFilter={milestoneLevelFilter} leagueFilter={milestoneLeagueFilter} onPlayerClick={handlePlayerClick} siteData={data} />
            <MilestonesTable title="4+ Run Games" data={data.milestones.fourRunGames} columns={["Date", "Player", "Team", "Opponent", "R", "H", "RBI"]} levelFilter={milestoneLevelFilter} leagueFilter={milestoneLeagueFilter} onPlayerClick={handlePlayerClick} siteData={data} />

            <h3 className="milestones-section-header">Baserunning & Patience</h3>
            <MilestonesTable title="Multi-SB Games" data={data.milestones.multiSbGames} columns={["Date", "Player", "Team", "Opponent", "SB", "H", "R"]} levelFilter={milestoneLevelFilter} leagueFilter={milestoneLeagueFilter} onPlayerClick={handlePlayerClick} siteData={data} />
            <MilestonesTable title="4+ Walk Games" data={data.milestones.fourWalkGames} columns={["Date", "Player", "Team", "Opponent", "BB", "H", "R"]} levelFilter={milestoneLevelFilter} leagueFilter={milestoneLeagueFilter} onPlayerClick={handlePlayerClick} siteData={data} />
          </div>
        )}

        {activeTab === "crossover" && <CrossoverPlayers players={data.crossoverPlayers} onPlayerClick={handlePlayerClick} data={data} />}
        {activeTab === "unifiedBatters" && <UnifiedBattersTable batters={data.unifiedBatters} onPlayerClick={handlePlayerClick} data={data} />}
        {activeTab === "unifiedPitchers" && <UnifiedPitchersTable pitchers={data.unifiedPitchers} onPlayerClick={handlePlayerClick} data={data} />}
        {activeTab === "schedule" && <UpcomingGames games={data.scheduleGames} data={data} />}
        {activeTab === "scorigami" && <ScorigamiGrid scorigami={data.scorigami} games={data.unifiedGameLog} data={data} />}
        {activeTab === "checklist" && <Checklist checklist={data.checklist} milbChecklist={data.milbChecklist} data={data} />}
        {activeTab === "map" && (
          <DynamicSchoolMap
            stadiums={data.stadiumLocations}
            teamsSeenHome={data.teamsSeenHome}
            teamsSeenAway={data.teamsSeenAway}
            checklist={data.checklist}
            milbStadiums={data.milbStadiumLocations}
            milbVenuesVisited={data.milbVenuesVisited}
            partnerStadiums={data.partnerStadiumLocations}
            partnerVenuesVisited={data.partnerVenuesVisited}
            data={data}
          />
        )}
        </div>

        <Footer generatedTime={new Date().toISOString().replace("T", " ").slice(0, 19)} />

        {selectedPlayer && (
          <PlayerModal
            player={selectedPlayer}
            games={selectedPlayerGames}
            milestones={selectedPlayerMilestones}
            type={playerType!}
            onClose={closeModal}
            data={data}
            unifiedStats={selectedUnifiedStats}
          />
        )}
      </div>
    </>
  );
}
