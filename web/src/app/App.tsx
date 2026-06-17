"use client";

import { useState, useMemo, useEffect, useCallback } from "react";
import dynamic from "next/dynamic";
import type { SiteData, NormalizedPlayer, MilestoneEntry, UnifiedGame, PlayerGame } from "@/types";
import Header from "@/components/layout/Header";
import Footer from "@/components/layout/Footer";
import TabBar from "@/components/layout/TabBar";
import StatsGrid from "@/components/stats/StatsGrid";
import Dashboard from "@/components/dashboard/Dashboard";
import UnifiedGameLog from "@/components/games/UnifiedGameLog";
import CalendarView from "@/components/games/CalendarView";
import UnifiedBattersTable from "@/components/tables/UnifiedBattersTable";
import UnifiedPitchersTable from "@/components/tables/UnifiedPitchersTable";
import TeamRecords from "@/components/tables/TeamRecords";
import MilestonesPage from "@/components/tables/MilestonesPage";
import CrossoverPlayers from "@/components/tables/CrossoverPlayers";
import ScorigamiGrid from "@/components/games/ScorigamiGrid";
import Checklist from "@/components/checklist/Checklist";
import UpcomingGames from "@/components/schedule/UpcomingGames";
import DataQualityPanel from "@/components/quality/DataQualityPanel";
import PlayerModal from "@/components/shared/PlayerModal";
import GameDetailsModal from "@/components/games/GameDetailsModal";
import { fetchJsonWithRetry } from "@/lib/fetchJson";

const DynamicSchoolMap = dynamic(
  () => import("@/components/maps/DynamicSchoolMap"),
  { ssr: false, loading: () => <div className="panel"><div className="panel-header"><h2>Stadium Map</h2></div><div style={{ padding: "20px", textAlign: "center", color: "#666" }}>Loading map...</div></div> }
);

interface AppProps {
  data?: SiteData;
}

type PlayerClickRow = {
  Name?: string;
  name?: string;
  Player?: string;
  Team?: string;
  team?: string;
  "BBRef ID"?: string;
  bref_id?: string;
  Level?: string;
  level?: string;
  levels?: ({ level: string } | string)[];
  "Level Details"?: ({ level: string } | string)[];
};

const EMPTY_SITE_DATA: SiteData = {
  summary: {
    totalGames: 0,
    totalBatters: 0,
    totalPitchers: 0,
    totalTeams: 0,
    totalMilestones: 0,
    milbGames: 0,
    milbBatters: 0,
    milbPitchers: 0,
    crossoverPlayers: 0,
    allGames: 0,
    unifiedBatters: 0,
    unifiedPitchers: 0,
  },
  levelColors: {},
  levelOrder: [],
  unifiedGameLog: [],
  unifiedBatters: [],
  unifiedPitchers: [],
  teamRecords: [],
  milestones: {},
  scorigami: {},
  crossoverPlayers: [],
  gameDetails: {},
  scheduleGames: [],
  scheduleIndex: [],
  dataMetadata: {
    generated_at: "",
    game_details_count: 0,
    schedule: {
      chunk_count: 0,
      total_games: 0,
      first_date: "",
      last_date: "",
    },
  },
  batterGames: [],
  pitcherGames: [],
  stadiumLocations: {},
  milbStadiumLocations: {},
  partnerStadiumLocations: {},
  milbVenuesVisited: [],
  partnerVenuesVisited: [],
  checklist: {},
  milbChecklist: {},
  teamsSeenHome: [],
  teamsSeenAway: [],
  historicalTeamLogos: {},
  ncaaTeamLogos: {},
  ncaaTeamNicknames: {},
  venueCityCoords: {},
  partnerLogos: {},
  localLogos: {},
  dataQuality: {
    summary: {
      mergedSourceGames: 0,
      unmergedSourceCandidates: 0,
      sourceMergeWarnings: 0,
      sourceMergeInfos: 0,
      sourceMergeIssues: 0,
      sourceMergeReviewGames: 0,
    },
    sourceMerge: {
      games: [],
      issues: [],
      unmergedCandidates: [],
    },
  },
};

const TAB_HASH_MAP: Record<string, string> = {
  dashboard: "dashboard",
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
  quality: "quality",
};

const HASH_TAB_MAP = Object.fromEntries(
  Object.entries(TAB_HASH_MAP).map(([k, v]) => [v, k])
);

function parseLocationHash() {
  if (typeof window === "undefined") return { tabId: "dashboard", gameId: "" };
  const hash = window.location.hash.replace(/^#/, "");
  if (!hash) return { tabId: "dashboard", gameId: "" };
  const [tabHash, ...rest] = hash.split("/");
  const tabId = HASH_TAB_MAP[tabHash] || "dashboard";
  const gameId = rest.length > 0 ? decodeURIComponent(rest.join("/")) : "";
  return { tabId, gameId };
}

function writeHash(hash: string, mode: "push" | "replace" = "replace") {
  if (typeof window === "undefined") return;
  const nextUrl = `${window.location.pathname}${hash}`;
  if (mode === "push") {
    window.history.pushState(null, "", nextUrl);
  } else {
    window.history.replaceState(null, "", nextUrl);
  }
}

function normalizeSlashDate(value?: string) {
  if (!value) return "";
  const parts = value.split("/");
  if (parts.length !== 3) return value;
  const month = Number(parts[0]);
  const day = Number(parts[1]);
  const year = Number(parts[2]);
  if (!month || !day || !year) return value;
  return `${month}/${day}/${year}`;
}

function normalizeMatchName(value?: string) {
  return String(value ?? "").trim().toLowerCase();
}

export default function App({ data: initialData }: AppProps) {
  const [data, setData] = useState<SiteData>(initialData ?? EMPTY_SITE_DATA);
  const [isLoadingData, setIsLoadingData] = useState(!initialData);
  const [dataLoadError, setDataLoadError] = useState<string | null>(null);

  useEffect(() => {
    if (initialData) return;
    let cancelled = false;
    fetchJsonWithRetry<SiteData>("/data/site-data.json")
      .then((loadedData) => {
        if (!cancelled) {
          setData(loadedData);
          setDataLoadError(null);
        }
      })
      .catch((error) => {
        if (!cancelled) {
          setDataLoadError(error instanceof Error ? error.message : "Failed to load site data");
        }
      })
      .finally(() => {
        if (!cancelled) setIsLoadingData(false);
      });
    return () => {
      cancelled = true;
    };
  }, [initialData]);

  const getInitialTab = () => {
    return parseLocationHash().tabId;
  };

  const [activeTab, setActiveTab] = useState(getInitialTab);
  const [selectedPlayer, setSelectedPlayer] = useState<NormalizedPlayer | null>(null);
  const [playerType, setPlayerType] = useState<"batter" | "pitcher" | null>(null);
  const [selectedGameIndex, setSelectedGameIndex] = useState<number | null>(null);
  const [milestoneLevelFilter, setMilestoneLevelFilter] = useState("All");
  const [milestoneLeagueFilter, setMilestoneLeagueFilter] = useState("All");

  const gameLog = data.unifiedGameLog;

  const setGameHash = useCallback((gameId: string, mode: "push" | "replace" = "replace") => {
    writeHash(gameId ? `#games/${encodeURIComponent(gameId)}` : `#${TAB_HASH_MAP.allGames}`, mode);
  }, []);

  const openGame = useCallback(
    (game: UnifiedGame) => {
      const idx = gameLog.findIndex(
        (g) =>
          g.game_id === game.game_id &&
          g.date_sort === game.date_sort &&
          g.away_team === game.away_team &&
          g.home_team === game.home_team
      );
      if (idx >= 0) {
        setActiveTab("allGames");
        setSelectedGameIndex(idx);
        if (game.game_id) setGameHash(game.game_id, "push");
      }
    },
    [gameLog, setGameHash]
  );

  const openPlayerGame = useCallback(
    (playerGame: PlayerGame) => {
      const rawGameId = playerGame.game_id;
      const playerDate = normalizeSlashDate(playerGame.date ?? playerGame.Date);
      const team = normalizeMatchName(playerGame.team);
      const opponent = normalizeMatchName(playerGame.opponent ?? playerGame.Opponent);
      const idx = gameLog.findIndex((game) => {
        if (rawGameId && game.game_id === rawGameId) return true;
        const sameDate = normalizeSlashDate(game.date) === playerDate;
        if (!sameDate || !team || !opponent) return false;
        const away = normalizeMatchName(game.away_team);
        const home = normalizeMatchName(game.home_team);
        return (
          (away === team && home === opponent) ||
          (away === opponent && home === team)
        );
      });
      if (idx >= 0) {
        setSelectedPlayer(null);
        setPlayerType(null);
        setActiveTab("allGames");
        setSelectedGameIndex(idx);
        const gameId = gameLog[idx].game_id;
        if (gameId) setGameHash(gameId, "push");
      }
    },
    [gameLog, setGameHash]
  );

  const closeGame = useCallback(() => {
    setSelectedGameIndex(null);
    if (parseLocationHash().gameId) {
      writeHash(`#${TAB_HASH_MAP[activeTab] ?? TAB_HASH_MAP.allGames}`);
    }
  }, [activeTab]);

  const navigateGame = useCallback(
    (delta: number) => {
      if (selectedGameIndex === null) return;
      // Walk forward/back to the next game that actually has details available.
      let next = selectedGameIndex + delta;
      while (next >= 0 && next < gameLog.length) {
        const nextGameId = gameLog[next].game_id;
        if (nextGameId) {
          setSelectedGameIndex(next);
          setGameHash(nextGameId, "replace");
          return;
        }
        next += delta;
      }
    },
    [gameLog, selectedGameIndex, setGameHash]
  );

  const handleTabChange = useCallback((tabId: string) => {
    setActiveTab(tabId);
    setSelectedGameIndex(null);
    const hash = TAB_HASH_MAP[tabId];
    if (hash && typeof window !== "undefined") {
      window.history.replaceState(null, "", `#${hash}`);
    }
  }, []);

  useEffect(() => {
    const syncFromHash = () => {
      const { tabId, gameId } = parseLocationHash();
      setActiveTab(tabId);
      if (gameId) {
        const idx = gameLog.findIndex((g) => g.game_id === gameId);
        setSelectedGameIndex(idx >= 0 ? idx : null);
      } else {
        setSelectedGameIndex(null);
      }
    };
    syncFromHash();
    window.addEventListener("hashchange", syncFromHash);
    window.addEventListener("popstate", syncFromHash);
    return () => {
      window.removeEventListener("hashchange", syncFromHash);
      window.removeEventListener("popstate", syncFromHash);
    };
  }, [gameLog]);

  const handlePlayerClick = (player: PlayerClickRow, type: "batter" | "pitcher") => {
    const rawLevels = player.levels ||
      player["Level Details"] ||
      (player.Level || player.level ? [player.Level || player.level || ""] : []);
    const normalized: NormalizedPlayer = {
      name: player.Name || player.name || player.Player || "",
      team: player.Team || player.team || "",
      bref_id: player["BBRef ID"] || player.bref_id || "",
      level: player.Level || player.level || "",
      levels: rawLevels.map((entry) =>
        typeof entry === "string" ? { level: entry } : entry
      ),
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
      fourWalkGames: "4+ BB", perfectBattingGames: "Perfect Batting",
      fourRunGames: "4+ Runs", threeTotalBasesGames: "8+ TB",
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

  const hasCrossover = data.crossoverPlayers && data.crossoverPlayers.length > 0;
  const hasSchedule =
    (data.scheduleGames && data.scheduleGames.length > 0) ||
    (data.scheduleIndex && data.scheduleIndex.length > 0);

  const tabs = [
    { id: "dashboard", label: "Dashboard" },
    { id: "allGames", label: "Games" },
    { id: "calendar", label: "Calendar" },
    { id: "milestones", label: "Milestones" },
    { id: "unifiedBatters", label: "Batters" },
    { id: "unifiedPitchers", label: "Pitchers" },
    { id: "teams", label: "Teams" },
    ...(hasCrossover ? [{ id: "crossover", label: "Crossover" }] : []),
    ...(hasSchedule ? [{ id: "schedule", label: "Schedule" }] : []),
    { id: "scorigami", label: "Scorigami" },
    { id: "checklist", label: "Progress" },
    { id: "map", label: "Map" },
    { id: "quality", label: "Data Health" },
  ];

  // Build header subtitle
  const headerSubtitle = useMemo(() => {
    const s = data.summary;
    const parts = [`${s.allGames} Games`, `${s.unifiedBatters} Batters`, `${s.unifiedPitchers} Pitchers`];
    if (s.crossoverPlayers > 0) parts.push(`${s.crossoverPlayers} Crossover Players`);
    return parts.join(" | ");
  }, [data.summary]);

  if (isLoadingData) {
    return (
      <main className="app">
        <div className="panel" style={{ margin: "32px auto", maxWidth: 720 }}>
          <div className="panel-header">
            <h2>Loading Baseball Data</h2>
          </div>
          <div style={{ padding: 24, color: "#666" }}>Loading site data...</div>
        </div>
      </main>
    );
  }

  if (dataLoadError) {
    return (
      <main className="app">
        <div className="panel" style={{ margin: "32px auto", maxWidth: 720 }}>
          <div className="panel-header">
            <h2>Unable to Load Data</h2>
          </div>
          <div style={{ padding: 24, color: "#666" }}>{dataLoadError}</div>
        </div>
      </main>
    );
  }

  return (
    <>
      <Header subtitle={headerSubtitle} data={data} onPlayerClick={handlePlayerClick} />
      <div className="container">
        <StatsGrid data={data.summary} />
        <TabBar tabs={tabs} activeTab={activeTab} onTabChange={handleTabChange} />

        <div key={activeTab} className="tab-content-enter">
        {activeTab === "dashboard" && (
          <Dashboard
            data={data}
            onTabChange={handleTabChange}
            onGameClick={openGame}
            onPlayerClick={handlePlayerClick}
          />
        )}
        {activeTab === "allGames" && <UnifiedGameLog games={data.unifiedGameLog} data={data} onGameClick={openGame} />}
        {activeTab === "calendar" && <CalendarView games={data.unifiedGameLog} data={data} />}
        {activeTab === "teams" && <TeamRecords teams={data.teamRecords} data={data} />}

        {activeTab === "milestones" && (
          <MilestonesPage
            data={data}
            levelFilter={milestoneLevelFilter}
            setLevelFilter={setMilestoneLevelFilter}
            leagueFilter={milestoneLeagueFilter}
            setLeagueFilter={setMilestoneLeagueFilter}
            onPlayerClick={handlePlayerClick}
          />
        )}

        {activeTab === "crossover" && <CrossoverPlayers players={data.crossoverPlayers} onPlayerClick={handlePlayerClick} data={data} />}
        {activeTab === "unifiedBatters" && <UnifiedBattersTable batters={data.unifiedBatters} onPlayerClick={handlePlayerClick} data={data} />}
        {activeTab === "unifiedPitchers" && <UnifiedPitchersTable pitchers={data.unifiedPitchers} onPlayerClick={handlePlayerClick} data={data} />}
        {activeTab === "schedule" && <UpcomingGames games={data.scheduleGames} data={data} />}
        {activeTab === "scorigami" && <ScorigamiGrid scorigami={data.scorigami} games={data.unifiedGameLog} data={data} />}
        {activeTab === "checklist" && <Checklist checklist={data.checklist} milbChecklist={data.milbChecklist} data={data} />}
        {activeTab === "quality" && <DataQualityPanel data={data} />}
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

        <Footer generatedTime={data.dataMetadata?.generated_at} data={data} />

        {selectedPlayer && (
          <PlayerModal
            player={selectedPlayer}
            games={selectedPlayerGames}
            milestones={selectedPlayerMilestones}
            type={playerType!}
            onClose={closeModal}
            data={data}
            unifiedStats={selectedUnifiedStats}
            onGameClick={openPlayerGame}
          />
        )}

        {selectedGameIndex !== null && gameLog[selectedGameIndex] && (
          <GameDetailsModal
            game={gameLog[selectedGameIndex]}
            onClose={closeGame}
            onPrev={() => navigateGame(1)}
            onNext={() => navigateGame(-1)}
            hasPrev={gameLog.slice(selectedGameIndex + 1).some((g) => !!g.game_id)}
            hasNext={gameLog.slice(0, selectedGameIndex).some((g) => !!g.game_id)}
            data={data}
          />
        )}
      </div>
    </>
  );
}
