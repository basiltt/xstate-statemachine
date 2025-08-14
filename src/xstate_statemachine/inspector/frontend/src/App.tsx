import { useEffect, useState } from "react";
import {
  LogEntry,
  MachineState,
  useInspectorSocket,
  useInspectorStore,
} from "./hooks/useInspectorSocket";
import { StatechartDiagram } from "./components/StatechartDiagram";
import { Moon, Sun } from "lucide-react";
import { cn } from "./lib/utils";

// --- START: Prop Type Definitions ---
interface SidebarProps {
  machines: Record<string, MachineState>;
  selectedMachineId: string | null;
  onSelectMachine: (id: string) => void;
  onToggleTheme: () => void;
  isDark: boolean;
}

interface MachineViewProps {
  machine: MachineState;
}

// --- END: Prop Type Definitions ---

export default function App() {
  useInspectorSocket();
  const machines = useInspectorStore((state) => state.machines);
  const [selectedMachineId, setSelectedMachineId] = useState<string | null>(null);
  const [isDark, setIsDark] = useState(false);

  useEffect(() => {
    const machineIds = Object.keys(machines);
    if (!selectedMachineId && machineIds.length > 0) {
      setSelectedMachineId(machineIds[0]);
    }
    if (selectedMachineId && !machines[selectedMachineId]) {
      setSelectedMachineId(machineIds.length > 0 ? machineIds[0] : null);
    }
  }, [machines, selectedMachineId]);

  useEffect(() => {
    const isDarkMode =
      localStorage.getItem("theme") === "dark" ||
      (!("theme" in localStorage) && window.matchMedia("(prefers-color-scheme: dark)").matches);
    setIsDark(isDarkMode);
    document.documentElement.classList.toggle("dark", isDarkMode);
  }, []);

  const toggleTheme = () => {
    const newIsDark = !isDark;
    setIsDark(newIsDark);
    localStorage.setItem("theme", newIsDark ? "dark" : "light");
    document.documentElement.classList.toggle("dark", newIsDark);
  };

  const selectedMachine = selectedMachineId ? machines[selectedMachineId] : null;

  return (
    <div className="flex h-screen w-full flex-col bg-muted/40 font-sans">
      <Sidebar
        machines={machines}
        selectedMachineId={selectedMachineId}
        onSelectMachine={setSelectedMachineId}
        onToggleTheme={toggleTheme}
        isDark={isDark}
      />
      <main className="flex flex-col gap-4 p-4 sm:py-4 sm:pl-14 md:pl-[280px]">
        {selectedMachine ? (
          <MachineView machine={selectedMachine} />
        ) : (
          <div className="flex h-full items-center justify-center rounded-lg border border-dashed shadow-sm">
            <div className="text-center">
              <h3 className="text-2xl font-bold tracking-tight">No Live Machines</h3>
              <p className="text-muted-foreground">
                Run a Python script with the InspectorPlugin to begin.
              </p>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

// FIX: Added explicit props type 'SidebarProps'
function Sidebar({
  machines,
  selectedMachineId,
  onSelectMachine,
  onToggleTheme,
  isDark,
}: SidebarProps) {
  return (
    <aside className="fixed inset-y-0 left-0 z-10 hidden w-14 flex-col border-r bg-background sm:flex md:w-[280px]">
      <nav className="flex flex-col items-center gap-4 px-2 py-4 md:items-stretch">
        <div className="hidden h-16 items-center justify-between border-b px-6 md:flex">
          <h1 className="text-lg font-bold">XState Inspector</h1>
        </div>

        {Object.values(machines).map((machine) => (
          <button
            key={machine.id}
            onClick={() => onSelectMachine(machine.id)}
            className={cn(
              "flex items-center justify-center gap-3 rounded-lg px-3 py-2 text-muted-foreground transition-all hover:text-primary md:justify-start",
              selectedMachineId === machine.id && "bg-accent text-primary"
            )}
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="24"
              height="24"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="h-5 w-5"
            >
              <path d="m12 14 4-4" />
              <path d="m12 14-4-4" />
              <path d="M12 20v-8" />
              <path d="M12 4v2" />
              <path d="M12 10h.01" />
              <path d="M20 12h-2" />
              <path d="M10 12h.01" />
              <path d="m4.929 19.071 1.414-1.414" />
              <path d="m17.657 6.343-1.414 1.414" />
              <path d="m4.929 4.929 1.414 1.414" />
              <path d="m17.657 17.657-1.414 1.414" />
            </svg>
            <span className="hidden md:inline">{machine.id}</span>
          </button>
        ))}
      </nav>
      <nav className="mt-auto flex flex-col items-center gap-4 px-2 py-4 md:items-stretch">
        <button
          onClick={onToggleTheme}
          className="flex items-center justify-center gap-3 rounded-lg px-3 py-2 text-muted-foreground transition-all hover:text-primary md:justify-start"
        >
          {isDark ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
          <span className="hidden md:inline">Toggle Theme</span>
        </button>
      </nav>
    </aside>
  );
}

// FIX: Added explicit props type 'MachineViewProps'
function MachineView({ machine }: MachineViewProps) {
  return (
    <>
      <header>
        <h1 className="text-4xl font-bold tracking-tight">{machine.id}</h1>
        <p className="text-muted-foreground">
          Current State:{" "}
          <span className="font-mono text-primary">{machine.currentStateIds.join(", ")}</span>
        </p>
      </header>
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-7">
        <div className="rounded-xl border bg-card text-card-foreground shadow lg:col-span-4">
          <div className="p-6">
            <h3 className="font-semibold text-lg mb-4">Statechart</h3>
            <StatechartDiagram machine={machine} activeStateIds={machine.currentStateIds} />
          </div>
        </div>
        <div className="rounded-xl border bg-card text-card-foreground shadow lg:col-span-3">
          <div className="p-6">
            <h3 className="font-semibold text-lg mb-2">Context</h3>
            <pre className="mt-2 h-[200px] w-full overflow-auto rounded-md bg-muted p-4 font-mono text-sm">
              {JSON.stringify(machine.context, null, 2)}
            </pre>
            <h3 className="font-semibold text-lg mt-4 mb-2">Event Log</h3>
            <div className="h-[250px] w-full overflow-auto rounded-md bg-muted p-2 font-mono text-xs">
              {/* FIX: TypeScript can now infer 'log' and 'i' types correctly */}
              {machine.logs.map((log: LogEntry, i: number) => (
                <div key={i} className="p-2 border-b border-background">
                  <p className="font-bold">{log.type}</p>
                  <p className="text-muted-foreground">{JSON.stringify(log.payload)}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
