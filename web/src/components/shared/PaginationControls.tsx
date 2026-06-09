"use client";

interface PaginationControlsProps {
  page: number;
  pageSize: number;
  pageCount: number;
  start: number;
  end: number;
  total: number;
  setPage: (page: number) => void;
  setPageSize: (pageSize: number) => void;
  pageSizeOptions?: number[];
}

export default function PaginationControls({
  page,
  pageSize,
  pageCount,
  start,
  end,
  total,
  setPage,
  setPageSize,
  pageSizeOptions = [50, 100, 200, 500],
}: PaginationControlsProps) {
  if (total <= pageSizeOptions[0]) return null;

  return (
    <div className="pagination-bar">
      <div className="pagination-summary">
        Showing {start.toLocaleString()}-{end.toLocaleString()} of{" "}
        {total.toLocaleString()}
      </div>
      <div className="pagination-actions">
        <label>
          Rows
          <select
            value={pageSize}
            onChange={(event) => setPageSize(Number(event.target.value))}
          >
            {pageSizeOptions.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        </label>
        <button
          type="button"
          onClick={() => setPage(Math.max(1, page - 1))}
          disabled={page <= 1}
        >
          Prev
        </button>
        <span className="pagination-page">
          {page.toLocaleString()} / {pageCount.toLocaleString()}
        </span>
        <button
          type="button"
          onClick={() => setPage(Math.min(pageCount, page + 1))}
          disabled={page >= pageCount}
        >
          Next
        </button>
      </div>
    </div>
  );
}
