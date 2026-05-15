"use client";

import { motion } from "framer-motion";

import { Button } from "@/components/ui/Button";
import type { SearchFilterState } from "@/types";

type AdvancedFiltersProps = {
  filters: SearchFilterState;
  onChange: (filters: SearchFilterState) => void;
  onReset: () => void;
};

const numberFields: Array<{
  key: keyof SearchFilterState;
  label: string;
  placeholder: string;
}> = [
  { key: "minMinutes", label: "Min Menit", placeholder: "900" },
  { key: "minValue", label: "Min Nilai EUR", placeholder: "10000000" },
  { key: "maxValue", label: "Max Nilai EUR", placeholder: "80000000" },
  { key: "minGoals", label: "Min Gol", placeholder: "5" },
  { key: "minAssists", label: "Min Assist", placeholder: "5" }
];

export function AdvancedFilters({ filters, onChange, onReset }: AdvancedFiltersProps) {
  function update(key: keyof SearchFilterState, value: string) {
    onChange({ ...filters, [key]: value, page: 1 });
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      transition={{ duration: 0.2 }}
      className="rounded-panel border border-border bg-background-secondary p-4"
    >
      <div className="grid gap-3 md:grid-cols-3 xl:grid-cols-5">
        {numberFields.map((field) => (
          <label key={field.key} className="space-y-1">
            <span className="text-xs uppercase tracking-widest text-text-secondary">
              {field.label}
            </span>
            <input
              value={String(filters[field.key] ?? "")}
              onChange={(event) => update(field.key, event.target.value)}
              inputMode="numeric"
              placeholder={field.placeholder}
              className="h-10 w-full rounded-panel border border-border bg-background-primary px-3 font-mono text-sm text-text-primary placeholder:text-text-muted focus:border-accent focus:outline-none"
            />
          </label>
        ))}
      </div>
      <div className="mt-4 flex justify-end">
        <Button variant="ghost" onClick={onReset}>
          Reset Semua
        </Button>
      </div>
    </motion.div>
  );
}
