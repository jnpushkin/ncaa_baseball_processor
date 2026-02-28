"use client";

interface Tab {
  id: string;
  label: string;
}

interface TabBarProps {
  tabs: Tab[];
  activeTab: string;
  onTabChange: (tabId: string) => void;
}

const TAB_ICONS: Record<string, string> = {
  allGames: "\u{1F4CB}",
  calendar: "\u{1F4C5}",
  unifiedBatters: "\u{1F3CF}",
  unifiedPitchers: "\u{26BE}",
  teams: "\u{1F3E2}",
  milestones: "\u{1F3C6}",
  crossover: "\u{1F504}",
  schedule: "\u{1F552}",
  scorigami: "\u{1F9E9}",
  checklist: "\u2611\uFE0F",
  map: "\u{1F5FA}\uFE0F",
};

export default function TabBar({ tabs, activeTab, onTabChange }: TabBarProps) {
  return (
    <div className="tabs" role="tablist">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          role="tab"
          aria-selected={activeTab === tab.id}
          className={"tab " + (activeTab === tab.id ? "active" : "")}
          onClick={() => onTabChange(tab.id)}
        >
          <span className="tab-icon" aria-hidden="true">{TAB_ICONS[tab.id] ?? ""}</span>
          {tab.label}
        </button>
      ))}
    </div>
  );
}
