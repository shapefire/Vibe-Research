import { useEffect, useState } from "react";
import { Bell, Loader2 } from "lucide-react";
import { GlassCard } from "@/components/ui/GlassCard";
import { api, type NotifyChannelStatus, type NotifyStatus } from "@/lib/api";
import { toast } from "sonner";

export function NotifySettingsCard() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState<string | null>(null);
  const [enabled, setEnabled] = useState(false);
  const [dashboardUrl, setDashboardUrl] = useState("");
  const [channels, setChannels] = useState<NotifyChannelStatus[]>([]);
  const [wecomWebhook, setWecomWebhook] = useState("");
  const [feishuWebhook, setFeishuWebhook] = useState("");
  const [wecomEnabled, setWecomEnabled] = useState(false);
  const [feishuEnabled, setFeishuEnabled] = useState(false);

  const applyStatus = (st: NotifyStatus) => {
    setEnabled(st.enabled);
    setDashboardUrl(st.dashboard_url || "");
    setChannels(st.channels || []);
    const we = st.channels.find((c) => c.provider === "wecom");
    const fe = st.channels.find((c) => c.provider === "feishu");
    setWecomEnabled(!!we?.enabled);
    setFeishuEnabled(!!fe?.enabled);
    // 不回填完整 webhook；用户不改则留空（服务端 merge 保留）
    setWecomWebhook("");
    setFeishuWebhook("");
  };

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const st = await api.notifyStatus();
        if (!cancelled) applyStatus(st);
      } catch (e) {
        if (!cancelled) toast.error(e instanceof Error ? e.message : "加载推送配置失败");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const save = async () => {
    setSaving(true);
    try {
      const body: {
        enabled: boolean;
        dashboard_url: string;
        channels: { provider: string; enabled: boolean; webhook_url?: string }[];
      } = {
        enabled,
        dashboard_url: dashboardUrl.trim(),
        channels: [
          {
            provider: "wecom",
            enabled: wecomEnabled,
            ...(wecomWebhook.trim() ? { webhook_url: wecomWebhook.trim() } : {}),
          },
          {
            provider: "feishu",
            enabled: feishuEnabled,
            ...(feishuWebhook.trim() ? { webhook_url: feishuWebhook.trim() } : {}),
          },
        ],
      };
      const st = await api.notifyUpdateConfig(body);
      applyStatus(st);
      toast.success("推送配置已保存到服务端");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "保存失败");
    } finally {
      setSaving(false);
    }
  };

  const test = async (provider: string) => {
    setTesting(provider);
    try {
      const res = await api.notifyTest(provider);
      const row = res.results.find((r) => r.provider_id === provider) || res.results[0];
      if (row?.ok) toast.success(`${provider} 测试推送成功`);
      else toast.error(row?.error || "测试失败");
      const st = await api.notifyStatus();
      applyStatus(st);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "测试失败");
    } finally {
      setTesting(null);
    }
  };

  const channelHint = (p: string) => channels.find((c) => c.provider === p);

  if (loading) {
    return (
      <GlassCard className="mt-4">
        <p className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" /> 加载推送配置…
        </p>
      </GlassCard>
    );
  }

  return (
    <GlassCard className="mt-4">
      <h3 className="mb-1 flex items-center gap-1.5 text-sm font-semibold">
        <Bell className="h-4 w-4 text-primary" /> 推送通知（飞书 / 企业微信）
      </h3>
      <p className="mb-3 text-xs text-muted-foreground">
        每日摘要（或定时 AI 复盘）生成后可推送到群机器人。Webhook 只存服务端{" "}
        <code className="rounded bg-muted/50 px-1">notify.json</code>，不进浏览器。配置指南见{" "}
        <a className="text-primary hover:underline" href="https://github.com/simonlin1212/Vibe-Research/blob/main/docs/notify-setup.md" target="_blank" rel="noreferrer">
          docs/notify-setup.md
        </a>
        。
      </p>

      <label className="mb-3 flex items-center gap-2 text-sm">
        <input type="checkbox" checked={enabled} onChange={(e) => setEnabled(e.target.checked)} />
        启用推送总开关
      </label>

      <div className="mb-4">
        <label className="mb-1.5 block text-xs font-medium text-muted-foreground">看板链接（推送内跳转）</label>
        <input
          value={dashboardUrl}
          onChange={(e) => setDashboardUrl(e.target.value)}
          placeholder="http://127.0.0.1:5899/daily-review"
          className="w-full rounded-lg border border-border bg-black/20 px-3 py-2 text-sm outline-none focus:border-primary/50"
        />
      </div>

      <div className="space-y-4">
        {[
          { id: "wecom", name: "企业微信", enabled: wecomEnabled, setEnabled: setWecomEnabled, webhook: wecomWebhook, setWebhook: setWecomWebhook },
          { id: "feishu", name: "飞书", enabled: feishuEnabled, setEnabled: setFeishuEnabled, webhook: feishuWebhook, setWebhook: setFeishuWebhook },
        ].map((ch) => {
          const hint = channelHint(ch.id);
          return (
            <div key={ch.id} className="rounded-lg border border-border/60 bg-muted/10 p-3">
              <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                <label className="flex items-center gap-2 text-sm font-medium">
                  <input type="checkbox" checked={ch.enabled} onChange={(e) => ch.setEnabled(e.target.checked)} />
                  {ch.name}
                </label>
                <button
                  type="button"
                  disabled={!!testing}
                  onClick={() => test(ch.id)}
                  className="rounded-lg bg-primary/15 px-3 py-1.5 text-xs font-medium text-primary hover:bg-primary/25 disabled:opacity-50"
                >
                  {testing === ch.id ? "推送中…" : "测试推送"}
                </button>
              </div>
              {hint?.webhook_masked && (
                <p className="mb-1 text-[11px] text-muted-foreground/70">已配置：{hint.webhook_masked}</p>
              )}
              {hint?.last_sent && (
                <p className="mb-1 text-[11px] text-muted-foreground/60">上次成功：{hint.last_sent}</p>
              )}
              {hint?.last_error && (
                <p className="mb-1 text-[11px] text-destructive/80">上次错误：{hint.last_error}</p>
              )}
              <input
                type="password"
                value={ch.webhook}
                onChange={(e) => ch.setWebhook(e.target.value)}
                placeholder="粘贴新 Webhook（留空则保留已有）"
                className="w-full rounded-lg border border-border bg-black/20 px-3 py-2 text-sm outline-none focus:border-primary/50"
              />
            </div>
          );
        })}
      </div>

      <div className="mt-4">
        <button
          type="button"
          disabled={saving}
          onClick={save}
          className="rounded-lg bg-primary/15 px-4 py-2 text-sm font-medium text-primary hover:bg-primary/25 disabled:opacity-50"
        >
          {saving ? "保存中…" : "保存推送配置"}
        </button>
      </div>
    </GlassCard>
  );
}
