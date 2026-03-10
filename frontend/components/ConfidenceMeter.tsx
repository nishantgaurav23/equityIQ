"use client";

interface ConfidenceMeterProps {
  confidence: number;
  label?: string;
}

export default function ConfidenceMeter({ confidence, label = "Confidence" }: ConfidenceMeterProps) {
  const clamped = Math.max(0, Math.min(1, confidence));
  const percentage = Math.round(clamped * 100);

  const barGradient =
    clamped > 0.6
      ? "from-green-500 to-emerald-400"
      : clamped > 0.3
        ? "from-yellow-500 to-amber-400"
        : "from-red-500 to-rose-400";

  return (
    <div className="space-y-1.5">
      <div className="flex justify-between text-sm">
        <span className="text-slate-400">{label}</span>
        <span className="font-mono font-semibold text-white">{percentage}%</span>
      </div>
      <div className="w-full h-2 bg-slate-800 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full bg-gradient-to-r ${barGradient} transition-all duration-700 ease-out`}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}
