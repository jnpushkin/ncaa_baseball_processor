"use client";

import { useState, useMemo } from "react";
import { SortConfig } from "@/types";

function compareValues(
  aVal: unknown,
  bVal: unknown,
  direction: "asc" | "desc",
  key: string
): number {
  if (typeof aVal === "number" && typeof bVal === "number") {
    return direction === "asc" ? aVal - bVal : bVal - aVal;
  }
  if (key === "Date" || key === "DateSort") {
    const parseDate = (d: string) => {
      if (!d) return 0;
      const parts = d.split("/");
      if (parts.length === 3) {
        return new Date(
          Number(parts[2]),
          Number(parts[0]) - 1,
          Number(parts[1])
        ).getTime();
      }
      return 0;
    };
    return direction === "asc"
      ? parseDate(String(aVal ?? "")) - parseDate(String(bVal ?? ""))
      : parseDate(String(bVal ?? "")) - parseDate(String(aVal ?? ""));
  }
  const aNum = parseFloat(String(aVal ?? ""));
  const bNum = parseFloat(String(bVal ?? ""));
  if (!isNaN(aNum) && !isNaN(bNum)) {
    return direction === "asc" ? aNum - bNum : bNum - aNum;
  }
  const aStr = String(aVal ?? "").toLowerCase();
  const bStr = String(bVal ?? "").toLowerCase();
  if (aStr < bStr) return direction === "asc" ? -1 : 1;
  if (aStr > bStr) return direction === "asc" ? 1 : -1;
  return 0;
}

export function useSortableData<T extends object>(
  items: T[],
  defaultSort: SortConfig | null = null,
  secondaryKey: string | null = null
) {
  const [sortConfig, setSortConfig] = useState<SortConfig | null>(defaultSort);

  const sortedItems = useMemo(() => {
    if (!sortConfig || !items) return items;
    return [...items].sort((a, b) => {
      const aRecord = a as Record<string, unknown>;
      const bRecord = b as Record<string, unknown>;
      const primary = compareValues(
        aRecord[sortConfig.key],
        bRecord[sortConfig.key],
        sortConfig.direction,
        sortConfig.key
      );
      if (primary !== 0 || !secondaryKey) return primary;
      // Tiebreaker: always same direction as primary for secondary
      return compareValues(
        aRecord[secondaryKey],
        bRecord[secondaryKey],
        sortConfig.direction,
        secondaryKey
      );
    });
  }, [items, sortConfig, secondaryKey]);

  const requestSort = (key: string) => {
    let direction: "asc" | "desc" = "asc";
    if (sortConfig && sortConfig.key === key && sortConfig.direction === "asc") {
      direction = "desc";
    }
    setSortConfig({ key, direction });
  };

  return { items: sortedItems, sortConfig, requestSort };
}
