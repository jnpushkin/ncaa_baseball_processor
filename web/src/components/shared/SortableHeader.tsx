"use client";

import { SortConfig } from "@/types";

interface SortableHeaderProps {
  label: string;
  sortKey: string;
  sortConfig: SortConfig | null;
  onSort: (key: string) => void;
}

export default function SortableHeader({
  label,
  sortKey,
  sortConfig,
  onSort,
}: SortableHeaderProps) {
  const isActive = sortConfig !== null && sortConfig.key === sortKey;
  return (
    <th onClick={() => onSort(sortKey)} className={isActive ? "sorted" : ""}>
      {label}
      <span className="sort-indicator">
        {isActive ? (sortConfig!.direction === "asc" ? "▲" : "▼") : "⇅"}
      </span>
    </th>
  );
}
