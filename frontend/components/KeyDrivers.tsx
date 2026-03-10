interface KeyDriversProps {
  drivers: string[];
}

export default function KeyDrivers({ drivers }: KeyDriversProps) {
  if (drivers.length === 0) {
    return (
      <div className="text-gray-500 dark:text-gray-400 text-sm">
        No key drivers identified
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <h3 className="text-sm font-semibold">Key Drivers</h3>
      <ul className="list-disc list-inside space-y-1 text-sm">
        {drivers.map((driver, i) => (
          <li key={i}>{driver}</li>
        ))}
      </ul>
    </div>
  );
}
