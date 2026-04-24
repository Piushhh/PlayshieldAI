"use client";

import { useState } from "react";
import Link from "next/link";
import { Shield, Mail, ArrowLeft } from "lucide-react";
import { api } from "@/lib/api";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await api.forgotPassword(email);
      setSent(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div
          className="absolute -top-40 -right-40 w-80 h-80 rounded-full opacity-20"
          style={{
            background: "radial-gradient(circle, #6366f1 0%, transparent 70%)",
          }}
        />
      </div>

      <div className="w-full max-w-md animate-in relative z-10">
        <div className="text-center mb-10">
          <div className="w-16 h-16 rounded-2xl mx-auto mb-4 flex items-center justify-center pulse-glow bg-gradient-to-br from-indigo-500 to-purple-600">
            <Shield size={32} className="text-white" />
          </div>
          <h1 className="text-3xl font-bold text-white mb-2">PlayShield AI</h1>
        </div>

        <div className="glass-card p-8">
          <h2 className="text-xl font-semibold mb-2 text-center">
            Reset your password
          </h2>
          <p className="text-sm text-[var(--color-text-muted)] mb-6 text-center">
            Enter your email and we&apos;ll send you a reset link.
          </p>

          {error && (
            <div className="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-sm">
              {error}
            </div>
          )}

          {sent ? (
            <div className="py-4">
              <div className="p-4 rounded-lg bg-green-500/10 border border-green-500/30 text-green-400 text-sm text-center mb-6">
                If an account with that email exists, a password reset link has
                been sent. Check your inbox.
              </div>
              <Link
                href="/login"
                className="btn-secondary w-full justify-center"
              >
                <ArrowLeft size={16} /> Back to Login
              </Link>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-[var(--color-text-secondary)] mb-2">
                  Email
                </label>
                <div className="relative">
                  <Mail
                    size={16}
                    className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)]"
                  />
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="you@example.com"
                    className="input-field pl-10"
                    required
                  />
                </div>
              </div>
              <button
                type="submit"
                disabled={loading}
                className="btn-primary w-full justify-center"
              >
                {loading ? "Sending..." : "Send Reset Link"}
              </button>
              <div className="text-center text-sm text-[var(--color-text-muted)]">
                <Link
                  href="/login"
                  className="text-indigo-400 hover:text-indigo-300"
                >
                  Back to Login
                </Link>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
