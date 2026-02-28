"use client";

interface LevelBadgeProps {
  level: string;
  levelColors: Record<string, string>;
}

export default function LevelBadge({ level, levelColors }: LevelBadgeProps) {
  const color = levelColors[level] ?? "#666";
  return (
    <span
      className="level-badge level-badge--filled"
      style={{ background: color }}
    >
      {level}
    </span>
  );
}
