import type { SiteData } from "@/types";
import App from "./App";

// eslint-disable-next-line @typescript-eslint/no-require-imports
let siteDataJson: SiteData;
try {
  siteDataJson = require("@/data/site-data.json") as SiteData;
} catch {
  // Provide empty fallback for build when no data exists yet
  siteDataJson = {
    summary: { totalGames: 0, totalBatters: 0, totalPitchers: 0, totalTeams: 0, totalMilestones: 0, milbGames: 0, milbBatters: 0, milbPitchers: 0, crossoverPlayers: 0, allGames: 0, unifiedBatters: 0, unifiedPitchers: 0 },
    levelColors: {}, levelOrder: [], unifiedGameLog: [], unifiedBatters: [], unifiedPitchers: [],
    teamRecords: [], milestones: {}, scorigami: {}, crossoverPlayers: [], scheduleGames: [],
    batterGames: [], pitcherGames: [], stadiumLocations: {}, milbStadiumLocations: {},
    partnerStadiumLocations: {}, milbVenuesVisited: [], partnerVenuesVisited: [],
    checklist: {}, milbChecklist: {}, teamsSeenHome: [], teamsSeenAway: [],
    historicalTeamLogos: {}, ncaaTeamLogos: {}, ncaaTeamNicknames: {},
    venueCityCoords: {}, partnerLogos: {}, localLogos: {},
  } as SiteData;
}

export default function Page() {
  return <App data={siteDataJson} />;
}
