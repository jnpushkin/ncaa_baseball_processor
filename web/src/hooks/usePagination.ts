"use client";

import { useMemo, useState } from "react";

export function usePagination<T>(items: T[], defaultPageSize = 100) {
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(defaultPageSize);
  const total = items.length;
  const pageCount = Math.max(1, Math.ceil(total / pageSize));
  const safePage = Math.min(page, pageCount);

  const pageItems = useMemo(() => {
    const startIndex = (safePage - 1) * pageSize;
    return items.slice(startIndex, startIndex + pageSize);
  }, [items, safePage, pageSize]);

  const start = total === 0 ? 0 : (safePage - 1) * pageSize + 1;
  const end = Math.min(total, safePage * pageSize);

  return {
    page: safePage,
    pageSize,
    pageCount,
    pageItems,
    start,
    end,
    total,
    setPage: (nextPage: number) =>
      setPage(Math.max(1, Math.min(pageCount, nextPage))),
    setPageSize: (nextPageSize: number) => {
      setPageSize(nextPageSize);
      setPage(1);
    },
  };
}
