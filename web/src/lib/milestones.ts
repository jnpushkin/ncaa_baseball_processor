import type { MilestoneEntry } from "@/types";

export type MilestonePlayerType = "batter" | "pitcher";

type MilestoneDefinition = {
  label: string;
  priority: number;
  playerType: MilestonePlayerType;
  isMajor: boolean;
};

export const MILESTONE_DEFINITIONS: Record<string, MilestoneDefinition> = {
  perfectGames: { label: "Perfect Game", priority: 1, playerType: "pitcher", isMajor: true },
  noHitters: { label: "No-Hitter", priority: 2, playerType: "pitcher", isMajor: true },
  cycles: { label: "Cycle", priority: 3, playerType: "batter", isMajor: true },
  threeHrGames: { label: "3 HR", priority: 4, playerType: "batter", isMajor: true },
  fifteenKGames: { label: "15 K", priority: 5, playerType: "pitcher", isMajor: true },
  fiveHitGames: { label: "5 Hits", priority: 6, playerType: "batter", isMajor: true },
  sixRbiGames: { label: "6 RBI", priority: 7, playerType: "batter", isMajor: true },
  madduxGames: { label: "Maddux", priority: 8, playerType: "pitcher", isMajor: true },
  cgsoNoWalks: { label: "CGSO No BB", priority: 9, playerType: "pitcher", isMajor: true },
  shutouts: { label: "Shutout", priority: 10, playerType: "pitcher", isMajor: true },

  multiHrGames: { label: "Multi-HR", priority: 30, playerType: "batter", isMajor: false },
  fiveRbiGames: { label: "5 RBI", priority: 31, playerType: "batter", isMajor: false },
  fourHitGames: { label: "4 Hits", priority: 32, playerType: "batter", isMajor: false },
  twelveKGames: { label: "12 K", priority: 33, playerType: "pitcher", isMajor: false },
  tenKGames: { label: "10 K", priority: 34, playerType: "pitcher", isMajor: false },
  oneHitters: { label: "1-Hitter", priority: 35, playerType: "pitcher", isMajor: false },
  twoHitters: { label: "2-Hitter", priority: 36, playerType: "pitcher", isMajor: false },
  lowHitCg: { label: "Low-Hit CG", priority: 37, playerType: "pitcher", isMajor: false },
  sevenInningShutouts: { label: "7+ IP SO", priority: 38, playerType: "pitcher", isMajor: false },
  dominantStarts: { label: "Dominant Start", priority: 39, playerType: "pitcher", isMajor: false },
  cycleWatch: { label: "Cycle Watch", priority: 40, playerType: "batter", isMajor: false },
  fourRbiGames: { label: "4 RBI", priority: 41, playerType: "batter", isMajor: false },
  multiDoubleGames: { label: "Multi-2B", priority: 42, playerType: "batter", isMajor: false },
  multiTripleGames: { label: "Multi-3B", priority: 43, playerType: "batter", isMajor: false },
  multiSbGames: { label: "Multi-SB", priority: 44, playerType: "batter", isMajor: false },
  fourWalkGames: { label: "4 BB", priority: 45, playerType: "batter", isMajor: false },
  perfectBattingGames: { label: "Perfect Batting", priority: 46, playerType: "batter", isMajor: false },
  fourRunGames: { label: "4 Runs", priority: 47, playerType: "batter", isMajor: false },
  threeTotalBasesGames: { label: "8 TB", priority: 48, playerType: "batter", isMajor: false },
  completeGames: { label: "Complete Game", priority: 49, playerType: "pitcher", isMajor: false },
  hrGames: { label: "HR", priority: 90, playerType: "batter", isMajor: false },
  threeHitGames: { label: "3 Hits", priority: 91, playerType: "batter", isMajor: false },
  threeRbiGames: { label: "3 RBI", priority: 92, playerType: "batter", isMajor: false },
  threeRunGames: { label: "3 Runs", priority: 93, playerType: "batter", isMajor: false },
  qualityStarts: { label: "Quality Start", priority: 94, playerType: "pitcher", isMajor: false },
  efficientStarts: { label: "Efficient Start", priority: 95, playerType: "pitcher", isMajor: false },
  highKLowBb: { label: "High K / Low BB", priority: 96, playerType: "pitcher", isMajor: false },
  noWalkStarts: { label: "No-Walk Start", priority: 97, playerType: "pitcher", isMajor: false },
  scorelessRelief: { label: "Scoreless Relief", priority: 98, playerType: "pitcher", isMajor: false },
  winGames: { label: "Win", priority: 99, playerType: "pitcher", isMajor: false },
  saveGames: { label: "Save", priority: 100, playerType: "pitcher", isMajor: false },
  hitForExtraBases: { label: "Multi-XBH", priority: 101, playerType: "batter", isMajor: false },
};

export const MAJOR_MILESTONE_KEYS = new Set(
  Object.entries(MILESTONE_DEFINITIONS)
    .filter(([, definition]) => definition.isMajor)
    .map(([key]) => key)
);

export function isMajorMilestoneKey(key: string) {
  return MAJOR_MILESTONE_KEYS.has(key);
}

export function getMilestoneLabel(key: string) {
  return MILESTONE_DEFINITIONS[key]?.label ?? key;
}

export function getMilestonePriority(key: string) {
  return MILESTONE_DEFINITIONS[key]?.priority ?? 999;
}

export function getMilestonePlayerType(key: string): MilestonePlayerType {
  return MILESTONE_DEFINITIONS[key]?.playerType ?? "batter";
}

export function milestoneDateSortValue(value?: string | number) {
  if (!value) return 0;
  const raw = String(value);
  const parts = raw.split(/[/-]/).map((part) => Number(part));
  if (parts.length === 3) {
    const [month, day, year] = parts;
    if (month && day && year) return year * 10000 + month * 100 + day;
  }
  return Number(raw.replace(/\D/g, "")) || 0;
}

export function milestoneStatChips(row: MilestoneEntry, limit = 5) {
  return ["1B", "2B", "3B", "HR", "H", "RBI", "K", "IP", "BB", "SB", "TB", "ER", "R"]
    .filter((key) => row[key] !== undefined && row[key] !== "")
    .slice(0, limit)
    .map((key) => ({ key, value: row[key] }));
}
