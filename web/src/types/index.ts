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
  game_id?: string | null;
  source?: string | null;
}

export interface BoxScoreBatter {
  name?: string;
  full_name?: string;
  position?: string;
  number?: string | number;
  jersey_number?: string | number;
  batting_order?: number;
  ab?: number; at_bats?: number;
  r?: number; runs?: number;
  h?: number; hits?: number;
  rbi?: number;
  bb?: number; walks?: number;
  k?: number; strikeouts?: number;
  doubles?: number;
  triples?: number;
  hr?: number;
  sb?: number;
  po?: number; put_outs?: number;
  a?: number; assists?: number;
  lob?: number; left_on_base?: number;
  avg?: string;
  obp?: string;
  slg?: string;
  bref_id?: string;
}

export interface BoxScorePitcher {
  name?: string;
  full_name?: string;
  number?: string | number;
  jersey_number?: string | number;
  ip?: number | string;
  h?: number;
  r?: number;
  er?: number;
  bb?: number;
  k?: number;
  hr?: number;
  bf?: number;
  np?: number;
  era?: string;
  win?: boolean | number;
  loss?: boolean | number;
  save?: boolean | number;
  wins?: number;
  losses?: number;
  saves?: number;
}

export interface GameNoteEvent {
  player?: string;
  game_count?: number;
  season_total?: number;
}

export interface PlayByPlayEvent {
  description?: string;
  pitch_count?: string;
  rbi?: number;
}

export interface PlayByPlayInning {
  top?: PlayByPlayEvent[];
  bottom?: PlayByPlayEvent[];
}

export interface GameDetails {
  game_id: string;
  source: string;
  date: string;
  date_yyyymmdd?: string;
  away_team: string;
  home_team: string;
  away_team_id?: number | null;
  home_team_id?: number | null;
  away_score: number;
  home_score: number;
  venue?: string;
  attendance?: string | number | null;
  weather?: string | null;
  duration?: string | null;
  start_time?: string | null;
  umpires?: { list?: string } | null;
  league?: { away?: string; home?: string } | null;
  level?: string | null;
  box_score?: {
    away_batting?: BoxScoreBatter[];
    home_batting?: BoxScoreBatter[];
    away_pitching?: BoxScorePitcher[];
    home_pitching?: BoxScorePitcher[];
  };
  game_notes?: {
    home_runs?: GameNoteEvent[];
    doubles?: GameNoteEvent[];
    triples?: GameNoteEvent[];
    stolen_bases?: GameNoteEvent[];
    win?: { player?: string; record?: string };
    loss?: { player?: string; record?: string };
    save?: { player?: string; count?: number };
  };
  play_by_play?: Record<string, PlayByPlayInning>;
  data_quality?: {
    source_merge?: SourceMergeGame;
    source_candidate?: SourceMergeGame;
  };
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

export interface ScheduleIndexEntry {
  date: string;
  path: string;
  count: number;
}

export interface DataMetadata {
  generated_at?: string;
  game_details_count?: number;
  schedule?: {
    chunk_count?: number;
    total_games?: number;
    first_date?: string;
    last_date?: string;
  };
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
  roadOnly?: boolean;
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
  game_id?: string;
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

export interface DataQualityIssue {
  code?: string;
  severity?: "warning" | "info" | string;
  game_id?: string;
  date?: string;
  date_yyyymmdd?: string;
  away_team?: string;
  home_team?: string;
  field?: string;
  section?: string;
  category?: string;
  player?: string;
  primary_source?: string;
  secondary_source?: string;
  primary_value?: string | number;
  secondary_value?: string | number;
  date_diff_days?: number;
  detail_path?: string;
  api_boxscore_url?: string;
  api_play_by_play_url?: string;
}

export interface SourceMergeGame {
  game_id?: string;
  date?: string;
  date_yyyymmdd?: string;
  away_team?: string;
  home_team?: string;
  away_score?: number;
  home_score?: number;
  venue?: string;
  level?: string;
  source?: string;
  confidence?: string;
  warning_count?: number;
  info_count?: number;
  issue_count?: number;
  sources?: string[];
  stats_source?: string;
  identity_source?: string;
  api_game_id?: string | number;
  detail_path?: string;
  api_boxscore_url?: string;
  api_play_by_play_url?: string;
  reason?: string;
  issues?: DataQualityIssue[];
  sections?: Record<string, Record<string, number>>;
  pdf_score?: [number, number] | null;
  api_score?: [number, number] | null;
}

export interface DataQuality {
  summary: {
    mergedSourceGames: number;
    unmergedSourceCandidates?: number;
    sourceMergeWarnings: number;
    sourceMergeInfos: number;
    sourceMergeIssues: number;
    sourceMergeReviewGames: number;
  };
  sourceMerge: {
    games: SourceMergeGame[];
    issues: DataQualityIssue[];
    unmergedCandidates?: SourceMergeGame[];
  };
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
  gameDetails?: Record<string, GameDetails>;
  scheduleGames: ScheduleGame[];
  scheduleIndex?: ScheduleIndexEntry[];
  dataMetadata?: DataMetadata;
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
  dataQuality?: DataQuality;
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
