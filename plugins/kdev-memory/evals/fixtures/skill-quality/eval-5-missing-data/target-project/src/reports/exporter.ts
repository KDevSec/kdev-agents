// 2026-04-22 新增：CSV/XLSX exporter
export function toCSV(rows: any[]): string {
  return rows.map(r => Object.values(r).join(',')).join('\n');
}
