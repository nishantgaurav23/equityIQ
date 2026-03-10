interface AnalystSignalsProps {
  signals: Record<string, string>;
}

const signalColor: Record<string, string> = {
  BUY: "text-green-600",
  HOLD: "text-yellow-600",
  SELL: "text-red-600",
};

export default function AnalystSignals({ signals }: AnalystSignalsProps) {
  const entries = Object.entries(signals);

  if (entries.length === 0) {
    return (
      <div className="text-gray-500 dark:text-gray-400 text-sm">
        No analyst signals available
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <h3 className="text-sm font-semibold">Analyst Signals</h3>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
        {entries.map(([agent, signal]) => (
          <div
            key={agent}
            className="border rounded-lg p-3 dark:border-gray-700"
          >
            <div className="text-xs text-gray-500 dark:text-gray-400">{agent}</div>
            <div className={`font-bold ${signalColor[signal] ?? "text-gray-600"}`}>
              {signal}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
