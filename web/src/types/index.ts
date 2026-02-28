export interface Summary {
  totalGames: number;
  totalBatters: number;
  totalPitchers: number;
  totalTeams: number;
  totalMilestones: number;
  milbGames: number;
  milbBatters: number;
  milbPitchers: number;
  crossoverPlayers: number;
  allGames: number;
  unifiedBatters: number;
  unifiedPitchers: number;
}

export interface UnifiedGame {
  date: string;
  date_sort: string;
  away_team: string;
  home_team: string;
  away_score: number;
  home_score: number;
  venue: string;
  level: string;
  league?: string;
  conference?: string;
  home_team_id?: number;
  away_team_id?: number;
  parent_orgs?: { away: string; home: string };
}

export interface UnifiedBatter {
  name: string;
  team: string;
  level: string;
  league?: string;
  conference?: string;
  team_id?: number;
  g: number;
  ab: number;
  r: number;
  h: number;
  doubles: number;
  triples: number;
  hr: number;
  rbi: number;
  bb: number;
  k: number;
  sb: number;
  avg: string;
  obp?: string;
  slg?: string;
  bref_id?: string;
  player_id?: string;
  // Combined player fields
  isCombined?: boolean;
  subRows?: UnifiedBatter[];
  levels?: string[];
  teams?: { team: string; team_id?: number; level: string }[];
}

export interface UnifiedPitcher {
  name: string;
  team: string;
  level: string;
  league?: string;
  conference?: string;
  team_id?: number;
  g: number;
  ip: number;
  h: number;
  r: number;
  er: number;
  bb: number;
  k: number;
  hr: number;
  era: string;
  bref_id?: string;
  player_id?: string;
  // Combined player fields
  isCombined?: boolean;
  subRows?: UnifiedPitcher[];
  levels?: string[];
  teams?: { team: string; team_id?: number; level: string }[];
}

export interface TeamRecord {
  Team: string;
  Level: string;
  League: string;
  W: number;
  L: number;
  "Win%": string;
  RS: number;
  RA: number;
  Diff: number;
  level?: string;
  league?: string;
}

export interface MilestoneEntry {
  Date: string;
  Player: string;
  Team: string;
  Opponent: string;
  Level?: string;
  level?: string;
  League?: string;
  league?: string;
  bref_id?: string;
  [key: string]: string | number | undefined;
}

export interface ScorigamiEntry {
  count: number;
  games: {
    date: string;
    away: string;
    home: string;
    away_score: number;
    home_score: number;
    level: string;
  }[];
}

export interface CrossoverPlayer {
  Name: string;
  "BBRef ID"?: string;
  "NCAA Teams"?: string;
  "MiLB Teams"?: string;
  "NCAA Games"?: number;
  "MiLB Games"?: number;
  "Total Games": number;
  "Level Details"?: { level: string; games: number; teams: string }[];
}

export interface ScheduleTeam {
  name: string;
  rank?: number;
  record?: string;
  logo_url?: string;
}

export interface ScheduleGame {
  date: string;
  date_display?: string;
  time_detail?: string;
  status: string;
  home_team: ScheduleTeam;
  away_team: ScheduleTeam;
  venue?: {
    name?: string;
    city?: string;
    state?: string;
  };
  d1bb_key?: string;
}

export interface StadiumLocation {
  lat: number;
  lng: number;
  stadium: string;
  type?: string;
}

export interface MilbStadiumLocation extends StadiumLocation {
  team: string;
  level: string;
  league: string;
  teamId: number;
  logo: string;
}

export interface PartnerStadiumLocation {
  lat: number;
  lng: number;
  team: string;
  league: string;
  logo: string;
}

export interface ChecklistConference {
  teams: string[];
  total: number;
  seen: number;
  visited: number;
  teamStatus: Record<string, "home" | "away" | "none">;
}

export interface MilbChecklistTeam {
  team: string;
  venue: string;
  teamId: number;
  logo: string;
  league: string;
  historic: boolean;
}

export interface MilbChecklistLevel {
  teams: MilbChecklistTeam[];
  total: number;
  seen: number;
  visited: number;
  teamStatus: Record<string, "home" | "away" | "none">;
  leagues: Record<
    string,
    {
      teams: MilbChecklistTeam[];
      total: number;
      seen: number;
      visited: number;
      teamStatus: Record<string, "home" | "away" | "none">;
    }
  >;
}

export interface PlayerGame {
  date?: string;
  Date?: string;
  level?: string;
  Level?: string;
  league?: string;
  opponent?: string;
  Opponent?: string;
  bref_id?: string;
  player_id?: string;
  Name?: string;
  name?: string;
  team?: string;
  ab?: number;
  r?: number;
  h?: number;
  doubles?: number;
  triples?: number;
  hr?: number;
  rbi?: number;
  bb?: number;
  k?: number;
  sb?: number;
  ip?: number;
  er?: number;
}

export interface SiteData {
  summary: Summary;
  levelColors: Record<string, string>;
  levelOrder: string[];
  unifiedGameLog: UnifiedGame[];
  unifiedBatters: UnifiedBatter[];
  unifiedPitchers: UnifiedPitcher[];
  teamRecords: TeamRecord[];
  milestones: Record<string, MilestoneEntry[]>;
  scorigami: Record<string, ScorigamiEntry>;
  crossoverPlayers: CrossoverPlayer[];
  scheduleGames: ScheduleGame[];
  batterGames: PlayerGame[];
  pitcherGames: PlayerGame[];
  stadiumLocations: Record<string, StadiumLocation>;
  milbStadiumLocations: Record<string, MilbStadiumLocation>;
  partnerStadiumLocations: Record<string, PartnerStadiumLocation>;
  milbVenuesVisited: string[];
  partnerVenuesVisited: string[];
  checklist: Record<string, ChecklistConference>;
  milbChecklist: Record<string, MilbChecklistLevel>;
  teamsSeenHome: string[];
  teamsSeenAway: string[];
  historicalTeamLogos: Record<string, string>;
  ncaaTeamLogos: Record<string, string | number>;
  ncaaTeamNicknames: Record<string, string>;
  venueCityCoords: Record<string, { lat: number; lng: number }>;
  partnerLogos: Record<string, string>;
  localLogos: Record<string, string>;
}

export interface SortConfig {
  key: string;
  direction: "asc" | "desc";
}

export interface NormalizedPlayer {
  name: string;
  team: string;
  bref_id: string;
  level: string;
  levels: { level: string }[];
}
