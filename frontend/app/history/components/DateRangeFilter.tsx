"use client";

interface DateRangeFilterProps {
  startDate: string;
  endDate: string;
  onStartDateChange: (date: string) => void;
  onEndDateChange: (date: string) => void;
  onClear: () => void;
}

export default function DateRangeFilter({
  startDate,
  endDate,
  onStartDateChange,
  onEndDateChange,
  onClear,
}: DateRangeFilterProps) {
  const hasValidationError = startDate && endDate && startDate > endDate;

  return (
    <div className="flex flex-wrap items-end gap-4">
      <div>
        <label htmlFor="start-date" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
          From
        </label>
        <input
          id="start-date"
          type="date"
          value={startDate}
          onChange={(e) => onStartDateChange(e.target.value)}
          className="border border-gray-300 dark:border-gray-600 rounded px-3 py-2 text-sm bg-white dark:bg-gray-800"
        />
      </div>
      <div>
        <label htmlFor="end-date" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
          To
        </label>
        <input
          id="end-date"
          type="date"
          value={endDate}
          onChange={(e) => onEndDateChange(e.target.value)}
          className="border border-gray-300 dark:border-gray-600 rounded px-3 py-2 text-sm bg-white dark:bg-gray-800"
        />
      </div>
      <button
        onClick={onClear}
        className="px-3 py-2 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 border border-gray-300 dark:border-gray-600 rounded"
      >
        Clear
      </button>
      {hasValidationError && (
        <span className="text-red-500 text-sm">Start date must be before end date</span>
      )}
    </div>
  );
}
