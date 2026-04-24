"use client";

import { useEffect, useState } from "react";
import { Settings as SettingsIcon, Play, Bell, Database, User, ShieldAlert, Trash2 } from "lucide-react";
import { api } from "@/lib/api";
import type { UserProfileRecord } from "@/lib/types";

export default function SettingsPage() {
  const [user, setUser] = useState<UserProfileRecord | null>(null);
  const [crawlStatus, setCrawlStatus] = useState("");
  const [alertStatus, setAlertStatus] = useState("");
  const [savingPrefs, setSavingPrefs] = useState(false);

  useEffect(() => {
    api.getMe().then(setUser).catch(console.error);
  }, []);

  const handleToggleNotifications = async () => {
    if (!user) return;
    setSavingPrefs(true);
    try {
      const updated = await api.updateAccountSettings({
        email_notifications: !user.email_notifications,
      });
      setUser(updated);
    } catch (error) {
      alert(
        "Failed to update preferences: " +
          (error instanceof Error ? error.message : "Unknown error")
      );
    } finally {
      setSavingPrefs(false);
    }
  };

  const handleDeleteAccount = async () => {
    if (!confirm("Are you ABSOLUTELY sure you want to delete your account? This action cannot be undone and will delete all your assets and cases.")) {
      return;
    }
    if (confirm("Final warning: This will permanently delete your account.")) {
      try {
        await api.deleteAccount();
        api.clearTokens();
        window.location.href = "/register";
      } catch (error) {
        alert(
          "Failed to delete account: " +
            (error instanceof Error ? error.message : "Unknown error")
        );
      }
    }
  };

  const handleCrawl = async () => {
    setCrawlStatus("Running...");
    try {
      const result = await api.runCrawl();
      setCrawlStatus(`Queued: Task ${result.task_id}`);
    } catch (error) {
      setCrawlStatus(
        `Error: ${error instanceof Error ? error.message : "Unknown error"}`
      );
    }
  };

  const handleTestAlerts = async () => {
    setAlertStatus("Sending...");
    try {
      const result = await api.testAlerts();
      setAlertStatus(`Slack: ${result.slack} | Email: ${result.email}`);
    } catch (error) {
      setAlertStatus(
        `Error: ${error instanceof Error ? error.message : "Unknown error"}`
      );
    }
  };

  return (
    <div className="space-y-6 max-w-3xl">
      <div className="animate-in">
        <h1 className="text-2xl font-bold">Settings</h1>
        <p className="text-[var(--color-text-muted)]">Manage your account and preferences</p>
      </div>

      {/* Profile */}
      <div className="glass-card p-6 animate-in">
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <User size={18} className="text-indigo-400" /> Account Profile
        </h3>
        <div className="space-y-4">
          <div>
            <label className="block text-sm text-[var(--color-text-muted)] mb-1">Email</label>
            <div className="font-medium">{user?.email || "Loading..."}</div>
          </div>
          <div>
            <label className="block text-sm text-[var(--color-text-muted)] mb-1">Role</label>
            <div className="pill pill-new inline-block">{user?.role || "user"}</div>
          </div>
          <div>
            <label className="block text-sm text-[var(--color-text-muted)] mb-1">Status</label>
            <div className="text-green-400 text-sm">
              {user?.is_verified ? "Verified" : "Unverified"}
            </div>
          </div>
        </div>
      </div>

      {/* Preferences */}
      <div className="glass-card p-6 animate-in" style={{ animationDelay: "0.1s" }}>
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <Bell size={18} className="text-amber-400" /> Notifications
        </h3>
        <div className="flex items-center justify-between">
          <div>
            <div className="font-medium">Email Alerts</div>
            <div className="text-sm text-[var(--color-text-muted)] mt-1">
              Receive an email when we detect a potential violation of your assets.
            </div>
          </div>
          <button
            onClick={handleToggleNotifications}
            disabled={savingPrefs || !user}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              user?.email_notifications
                ? "bg-indigo-500 hover:bg-indigo-600 text-white"
                : "bg-[var(--color-surface)] hover:bg-[var(--color-border)] text-[var(--color-text-secondary)]"
            }`}
          >
            {user?.email_notifications ? "Enabled" : "Disabled"}
          </button>
        </div>
      </div>

      {/* Admin Section */}
      {user?.role === "admin" && (
        <div className="glass-card p-6 border-amber-500/30 border animate-in" style={{ animationDelay: "0.2s" }}>
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2 text-amber-400">
            <ShieldAlert size={18} /> Admin Controls
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="p-4 bg-[var(--color-surface)] rounded-xl border border-[var(--color-border)]">
              <h4 className="font-medium mb-2 flex items-center gap-2">
                <Database size={16} className="text-indigo-400" /> Crawler
              </h4>
              <p className="text-xs text-[var(--color-text-muted)] mb-4">Trigger discovery crawl.</p>
              <button onClick={handleCrawl} className="btn-primary w-full justify-center text-sm">
                <Play size={14} /> Run
              </button>
              {crawlStatus && <p className="text-xs text-[var(--color-text-secondary)] mt-2">{crawlStatus}</p>}
            </div>
            <div className="p-4 bg-[var(--color-surface)] rounded-xl border border-[var(--color-border)]">
              <h4 className="font-medium mb-2 flex items-center gap-2">
                <Bell size={16} className="text-amber-400" /> Global Alerts
              </h4>
              <p className="text-xs text-[var(--color-text-muted)] mb-4">Test system integrations.</p>
              <button onClick={handleTestAlerts} className="btn-secondary w-full justify-center text-sm">
                Test
              </button>
              {alertStatus && <p className="text-xs text-[var(--color-text-secondary)] mt-2">{alertStatus}</p>}
            </div>
          </div>
        </div>
      )}

      {/* Danger Zone */}
      <div className="glass-card p-6 border-red-500/30 border animate-in" style={{ animationDelay: "0.3s" }}>
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2 text-red-400">
          <Trash2 size={18} /> Danger Zone
        </h3>
        <p className="text-sm text-[var(--color-text-muted)] mb-4">
          Permanently delete your account and all associated data (assets, cases, detections).
        </p>
        <button onClick={handleDeleteAccount} className="btn-danger">
          Delete Account
        </button>
      </div>

      {/* System Info */}
      <div className="glass-card p-6 animate-in" style={{ animationDelay: "0.4s" }}>
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <SettingsIcon size={18} className="text-green-400" /> System Info
        </h3>
        <div className="space-y-2 text-sm">
          <div className="flex justify-between py-2 border-b border-[var(--color-border)]">
            <span className="text-[var(--color-text-muted)]">Version</span>
            <span>0.1.0</span>
          </div>
          <div className="flex justify-between py-2 border-b border-[var(--color-border)]">
            <span className="text-[var(--color-text-muted)]">Backend</span>
            <span>FastAPI + Python 3.11</span>
          </div>
          <div className="flex justify-between py-2 py-2">
            <span className="text-[var(--color-text-muted)]">Matching</span>
            <span>CLIP + FAISS + imagehash</span>
          </div>
        </div>
      </div>
    </div>
  );
}
