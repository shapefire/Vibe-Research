import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { AlertCircle } from "lucide-react";
import { api, type HealthSources } from "@/lib/api";

/** 任一 chain degraded/down 时顶部展示数据源降级提示。 */
export function SourceStatusBanner() {
  const [status, setStatus] = useState<HealthSources | null>(null);

  useEffect(() => {
    api.healthSources().then(setStatus).catch(() => {});
  }, []);

  const degraded = status && Object.values(status.chains).some((c) => c !== "ok");
  if (!degraded) return null;

  return (
    <div className="mb-4 flex items-center gap-2 rounded-lg border border-warning/30 bg-warning/5 px-4 py-3 text-sm text-muted-foreground">
      <AlertCircle className="h-4 w-4 shrink-0 text-warning" />
      <span>
        部分数据源异常，数据可能滞后。
        <Link to="/settings" className="ml-1 text-primary hover:underline">检查依赖</Link>
      </span>
    </div>
  );
}
