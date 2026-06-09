"use client";

import { useState, useMemo } from "react";
import { SortConfig } from "@/types";

function isMissingValue(value: unknown): boolean {
  if (value === undefined || value === null) return true;
  const normalized = String(value).trim().toLowerCase();
  return normalized === "" || normalized === "unknown" || normalized === "-";
}

function parseDateValue(value: unknown): number {
  if (isMissingValue(value)) return 0;
  const str = String(value).trim();
  if (/^\d{8}$/.test(str)) {
    const year = Number(str.slice(0, 4));
    const month = Number(str.slice(4, 6));
    const day = Number(str.slice(6, 8));
    return new Date(year, month - 1, day).getTime();
  }

  const iso = Date.parse(str);
  if (!Number.isNaN(iso)) return iso;

  const parts = str.split("/");
  if (parts.length === 3) {
    const month = Number(parts[0]);
    const day = Number(parts[1]);
    const year = Number(parts[2]);
    if (month && day && year) {
      return new Date(year, month - 1, day).getTime();
    }
  }

  return 0;
}

function compareValues(
  aVal: unknown,
  bVal: unknown,
  direction: "asc" | "desc",
  key: string
): number {
  const aMissing = isMissingValue(aVal);
  const bMissing = isMissingValue(bVal);
  if (aMissing || bMissing) {
    if (aMissing && bMissing) return 0;
    return aMissing ? 1 : -1;
  }

  const keyLower = key.toLowerCase();
  if (keyLower === "date" || keyLower === "datesort" || keyLower === "date_sort") {
    return direction === "asc"
      ? parseDateValue(aVal) - parseDateValue(bVal)
      : parseDateValue(bVal) - parseDateValue(aVal);
  }

  if (typeof aVal === "number" && typeof bVal === "number") {
    return direction === "asc" ? aVal - bVal : bVal - aVal;
  }

  const aNum = parseFloat(String(aVal ?? ""));
  const bNum = parseFloat(String(bVal ?? ""));
  if (!isNaN(aNum) && !isNaN(bNum)) {
    return direction === "asc" ? aNum - bNum : bNum - aNum;
  }

  const aStr = String(aVal ?? "").toLowerCase();
  const bStr = String(bVal ?? "").toLowerCase();
  return direction === "asc"
    ? aStr.localeCompare(bStr, undefined, { numeric: true, sensitivity: "base" })
    : bStr.localeCompare(aStr, undefined, { numeric: true, sensitivity: "base" });
}

export function useSortableData<T extends object>(
  items: T[],
  defaultSort: SortConfig | null = null,
  secondaryKey: string | null = null
) {
  const [sortConfig, setSortConfig] = useState<SortConfig | null>(defaultSort);

  const sortedItems = useMemo(() => {
    if (!sortConfig || !items) return items;
    return items
      .map((item, index) => ({ item, index }))
      .sort((a, b) => {
        const aRecord = a.item as Record<string, unknown>;
        const bRecord = b.item as Record<string, unknown>;
        const primary = compareValues(
          aRecord[sortConfig.key],
          bRecord[sortConfig.key],
          sortConfig.direction,
          sortConfig.key
        );
        if (primary !== 0) return primary;
        if (!secondaryKey) return a.index - b.index;
        const secondary = compareValues(
          aRecord[secondaryKey],
          bRecord[secondaryKey],
          sortConfig.direction,
          secondaryKey
        );
        return secondary !== 0 ? secondary : a.index - b.index;
      })
      .map(({ item }) => item);
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
