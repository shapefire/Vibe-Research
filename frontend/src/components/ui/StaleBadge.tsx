/** 行情或东财数据来自缓存降级时的小角标。 */
export function StaleBadge({ partial }: { partial?: boolean }) {
  return (
    <span
      className="rounded bg-warning/15 px-1.5 py-0.5 text-[10px] font-medium text-warning"
      title={partial ? "部分代码无实时行情，展示缓存数据" : "数据源暂时不可用，展示缓存数据"}
    >
      {partial ? "部分滞后" : "滞后"}
    </span>
  );
}
