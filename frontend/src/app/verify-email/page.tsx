"use client";

import { useEffect, useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { Shield, CheckCircle, XCircle } from "lucide-react";
import { api } from "@/lib/api";

function VerifyEmailContent() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token");
  const [status, setStatus] = useState<"loading" | "success" | "error">(
    token ? "loading" : "error"
  );
  const [message, setMessage] = useState(
    token ? "" : "No verification token provided."
  );

  useEffect(() => {
    if (!token) {
      return;
    }
    api
      .verifyEmail(token)
      .then((res) => {
        setStatus("success");
        setMessage(res.message || "Email verified successfully!");
      })
      .catch((err) => {
        setStatus("error");
        setMessage(err instanceof Error ? err.message : "Verification failed.");
      });
  }, [token]);

  return (
    <div className="glass-card p-8 text-center">
      {status === "loading" && (
        <div className="py-8">
          <div className="pulse-glow w-12 h-12 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 mx-auto mb-4" />
          <p className="text-[var(--color-text-muted)]">
            Verifying your email...
          </p>
        </div>
      )}

      {status === "success" && (
        <div className="py-8">
          <CheckCircle size={48} className="text-green-400 mx-auto mb-4" />
          <h2 className="text-xl font-semibold mb-2 text-green-400">
            Email Verified!
          </h2>
          <p className="text-[var(--color-text-muted)] mb-6">{message}</p>
          <Link href="/login" className="btn-primary justify-center">
            Sign In
          </Link>
        </div>
      )}

      {status === "error" && (
        <div className="py-8">
          <XCircle size={48} className="text-red-400 mx-auto mb-4" />
          <h2 className="text-xl font-semibold mb-2 text-red-400">
            Verification Failed
          </h2>
          <p className="text-[var(--color-text-muted)] mb-6">{message}</p>
          <Link href="/login" className="btn-secondary justify-center">
            Back to Login
          </Link>
        </div>
      )}
    </div>
  );
}

export default function VerifyEmailPage() {
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

        <Suspense fallback={<div className="glass-card p-8 text-center text-[var(--color-text-muted)]">Loading...</div>}>
          <VerifyEmailContent />
        </Suspense>
      </div>
    </div>
  );
}
