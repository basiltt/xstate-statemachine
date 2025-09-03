// src/xstate_statemachine/inspector/frontend/src/App.tsx

import { useEffect, useMemo, useState, useRef } from "react";
import {
  LogEntry,
  MachineState,
  useInspectorSocket,
  useInspectorStore,
} from "./hooks/useInspectorSocket";

import {
  Bot,
  FileJson,
  History,
  Moon,
  Pause,
  Play,
  Send,
  SquareActivity,
  Sun,
  Wifi,
  WifiOff,
  Settings,
  MoveDiagonal2,
  Clock,
  Search,
  ListFilter,
  Check,
  X as XIcon,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";

// Magic UI components
import { Dock, DockIcon } from "@/components/magicui/dock";
import ShimmerButton from "@/components/magicui/shimmer-button";
import { StatechartDiagram } from "@/components/statechart/diagram/StatechartDiagram.tsx";

// --- Local storage keys ---
const LAST_SELECTED_KEY = "inspector:lastSelectedMachineId";
const SORT_ORDER_KEY = "inspector:sortOrder";

type SortOrder = "name-asc" | "name-desc" | "updated-desc" | "updated-asc";

// --- Prop Type Definitions ---
interface HeaderProps {
  onToggleTheme: () => void;
  isDark: boolean;
  isConnected: boolean;
  onOpenSettings: () => void;
}

interface SidebarProps {
  machines: Record<string, MachineState>;
  selectedMachineId: string | null;
  onSelect: (id: string) => void;
  sortOrder: SortOrder;
  onChangeSort: (order: SortOrder) => void;
}

interface MachineViewProps {
  machine: MachineState;
  autoFitAfterDrag: boolean;
  showMinimap: boolean;
}

interface SendEventDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  machineId: string;
}

// --- Helpers ---
const formatTime = (ts?: number) => {
  if (!ts) return "";
  const d = new Date(ts);
  return d.toLocaleTimeString([], { hour12: false });
};

const sortMachines = (list: MachineState[], order: SortOrder) => {
  const arr = [...list];
  switch (order) {
    case "name-asc":
      return arr.sort((a, b) => a.id.localeCompare(b.id));
    case "name-desc":
      return arr.sort((a, b) => b.id.localeCompare(a.id));
    case "updated-asc":
      return arr.sort((a, b) => a.updatedAt - b.updatedAt);
    case "updated-desc":
    default:
      return arr.sort((a, b) => b.updatedAt - a.updatedAt);
  }
};

// --- Main App Component ---
export default function App() {
  useInspectorSocket();
  const machines = useInspectorStore((state) => state.machines);
  const isConnected = useInspectorStore((state) => state.isConnected);
  const [selectedMachineId, setSelectedMachineId] = useState<string | null>(null);
  const [sortOrder, setSortOrder] = useState<SortOrder>(() => {
    const stored = localStorage.getItem(SORT_ORDER_KEY) as SortOrder | null;
    return stored ?? "updated-desc";
  });
  const [isDark, setIsDark] = useState(false);

  // Settings state: Auto-fit view after drag (persisted)
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [autoFitAfterDrag, setAutoFitAfterDrag] = useState<boolean>(() => {
    const stored = localStorage.getItem("autoFitAfterDrag");
    return stored ? stored === "true" : true; // default enabled
  });
  // Settings state: Show Minimap (persisted)
  const [showMinimap, setShowMinimap] = useState<boolean>(() => {
    const stored = localStorage.getItem("showMinimap");
    return stored ? stored === "true" : true; // default enabled
  });

  // Determine initial selection and keep it valid when machines change
  useEffect(() => {
    const ids = Object.keys(machines);
    if (ids.length === 0) {
      setSelectedMachineId(null);
      return;
    }

    // Try last selected from storage
    const stored = localStorage.getItem(LAST_SELECTED_KEY);
    if (stored && machines[stored]) {
      setSelectedMachineId(stored);
      return;
    }

    // Fallback: first machine by registeredAt (newest first)
    const firstByRegistered = [...Object.values(machines)].sort(
      (a, b) => b.registeredAt - a.registeredAt,
    )[0]?.id;
    if (firstByRegistered) setSelectedMachineId(firstByRegistered);
  }, [machines]);

  // Persist selection
  useEffect(() => {
    if (selectedMachineId) localStorage.setItem(LAST_SELECTED_KEY, selectedMachineId);
  }, [selectedMachineId]);

  // Persist sort
  useEffect(() => {
    localStorage.setItem(SORT_ORDER_KEY, sortOrder);
  }, [sortOrder]);

  useEffect(() => {
    // Initialize theme from localStorage or system preference
    const stored = localStorage.getItem("theme");
    const preferDark =
      window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
    const dark = stored ? stored === "dark" : preferDark;
    document.documentElement.classList.toggle("dark", dark);
    setIsDark(dark);
  }, []);

  const toggleTheme = () => {
    const newIsDark = !document.documentElement.classList.contains("dark");
    setIsDark(newIsDark);
    localStorage.setItem("theme", newIsDark ? "dark" : "light");
    document.documentElement.classList.toggle("dark", newIsDark);
  };

  const handleToggleAutoFit = (value: boolean) => {
    setAutoFitAfterDrag(value);
    localStorage.setItem("autoFitAfterDrag", value ? "true" : "false");
  };

  const handleToggleShowMinimap = (value: boolean) => {
    setShowMinimap(value);
    localStorage.setItem("showMinimap", value ? "true" : "false");
  };

  const selectedMachine = selectedMachineId ? machines[selectedMachineId] : null;

  return (
    <div className="flex h-screen w-full flex-col bg-background font-sans text-foreground">
      <Header
        onToggleTheme={toggleTheme}
        isDark={isDark}
        isConnected={isConnected}
        onOpenSettings={() => setSettingsOpen(true)}
      />
      <div className="flex flex-1 overflow-hidden">
        <Sidebar
          machines={machines}
          selectedMachineId={selectedMachineId}
          onSelect={setSelectedMachineId}
          sortOrder={sortOrder}
          onChangeSort={setSortOrder}
        />
        <main className="flex-1 flex flex-col overflow-hidden">
          {selectedMachine ? (
            <MachineView
              key={selectedMachine.id}
              machine={selectedMachine}
              autoFitAfterDrag={autoFitAfterDrag}
              showMinimap={showMinimap}
            />
          ) : (
            <WelcomePanel />
          )}
          {/* Debug info */}
          <div
            style={{
              position: "fixed",
              top: 10,
              right: 10,
              background: "rgba(0,0,0,0.8)",
              color: "white",
              padding: "10px",
              fontSize: "12px",
              zIndex: 1000,
            }}
          >
            <div>Machines: {Object.keys(machines).length}</div>
            <div>Selected: {selectedMachine?.id || "none"}</div>
            <div>Has Definition: {selectedMachine?.definition ? "yes" : "no"}</div>
            <div>
              Has States:{" "}
              {selectedMachine?.definition?.states
                ? Object.keys(selectedMachine.definition.states).length
                : 0}
            </div>
            <div>Active States: {selectedMachine?.currentStateIds?.length || 0}</div>
          </div>
        </main>
      </div>

      {/* Settings Dialog */}
      <SettingsDialog
        open={settingsOpen}
        onOpenChange={setSettingsOpen}
        autoFitAfterDrag={autoFitAfterDrag}
        onChangeAutoFit={handleToggleAutoFit}
        showMinimap={showMinimap}
        onChangeShowMinimap={handleToggleShowMinimap}
      />
    </div>
  );
}

// --- UI Components ---
// @ts-ignore
const Header = ({ onToggleTheme, isDark, isConnected, onOpenSettings }: HeaderProps) => (
  <header className="flex h-14 items-center justify-between border-b bg-card px-4 lg:px-6">
    <div className="flex items-center gap-2 font-bold">
      <Bot className="h-6 w-6 text-primary" />
      <span>XState Inspector</span>
    </div>
    <div className="flex items-center gap-3">
      {/* Connection Indicator */}
      <div
        className={
          "flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium border " +
          (isConnected
            ? "border-green-600 text-green-700 dark:text-green-400"
            : "border-amber-600 text-amber-700 dark:text-amber-400")
        }
        title={isConnected ? "Connected" : "Disconnected"}
      >
        {isConnected ? <Wifi className="h-4 w-4" /> : <WifiOff className="h-4 w-4" />}
        <span>{isConnected ? "Online" : "Offline"}</span>
      </div>
      <Button variant="ghost" size="icon" onClick={onOpenSettings} aria-label="Settings">
        <Settings className="h-5 w-5" />
      </Button>
      <Button variant="ghost" size="icon" onClick={onToggleTheme} aria-label="Toggle theme">
        <Sun className="h-5 w-5 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
        <Moon className="absolute h-5 w-5 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
        <span className="sr-only">Toggle theme</span>
      </Button>
    </div>
  </header>
);

const Sidebar = ({
  machines,
  selectedMachineId,
  onSelect,
  sortOrder,
  onChangeSort,
}: SidebarProps) => {
  const [query, setQuery] = useState("");
  const [sortOpen, setSortOpen] = useState(false);
  const [searchMode, setSearchMode] = useState(false);
  const sortRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!sortOpen) return;
    const handleMouseDown = (e: MouseEvent) => {
      if (sortRef.current && !sortRef.current.contains(e.target as Node)) {
        setSortOpen(false);
      }
    };
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") setSortOpen(false);
    };
    document.addEventListener("mousedown", handleMouseDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("mousedown", handleMouseDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [sortOpen]);

  const list = useMemo(() => {
    const arr = Object.values(machines);
    const filtered = query
      ? arr.filter((m) => m.id.toLowerCase().includes(query.toLowerCase()))
      : arr;
    return sortMachines(filtered, sortOrder);
  }, [machines, query, sortOrder]);

  const collapseSearch = () => {
    setQuery("");
    setSearchMode(false);
  };

  return (
    <aside className="hidden w-80 flex-col border-r bg-card p-4 sm:flex">
      {/* Header row: collapsed shows search button + sort icon; expanded shows full search */}
      {!searchMode ? (
        <div className="flex items-center justify-between pb-2 border-b border-border/60">
          <button
            className="flex items-center gap-2 rounded-md px-2 py-1 text-sm text-foreground/90 hover:bg-muted/60"
            onClick={() => {
              setSearchMode(true);
              setSortOpen(false);
              setTimeout(() => {
                const el = document.getElementById("inspector-search-input");
                (el as HTMLInputElement | null)?.focus();
              }, 0);
            }}
            aria-label="Open search"
          >
            <Search className="h-4 w-4" />
            <span className="font-semibold">Machines</span>
          </button>

          <div className="relative" ref={sortRef}>
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setSortOpen((v) => !v)}
              aria-label="Sort"
            >
              <ListFilter className="h-4 w-4" />
            </Button>
            {sortOpen && (
              <div className="absolute right-0 z-10 mt-2 w-40 rounded-md border bg-popover p-1 shadow-md">
                {(
                  [
                    { id: "name-asc", label: "Name A—Z" },
                    { id: "name-desc", label: "Name Z—A" },
                    { id: "updated-desc", label: "Last updated" },
                    { id: "updated-asc", label: "First updated" },
                  ] as { id: SortOrder; label: string }[]
                ).map((opt) => (
                  <button
                    key={opt.id}
                    className={
                      "flex w-full items-center rounded px-2 py-1 text-sm hover:bg-muted/60"
                    }
                    onClick={() => {
                      onChangeSort(opt.id);
                      setSortOpen(false);
                    }}
                  >
                    {/* Reserve space for the check icon so labels are perfectly aligned */}
                    <Check
                      className={
                        "mr-2 h-3.5 w-3.5 " +
                        (sortOrder === opt.id ? "opacity-100 text-primary" : "opacity-0")
                      }
                      aria-hidden="true"
                    />
                    <span className={sortOrder === opt.id ? "text-primary" : undefined}>
                      {opt.label}
                    </span>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      ) : (
        <div className="relative pb-2 border-b border-border/60">
          <Search className="pointer-events-none absolute left-2 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            id="inspector-search-input"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Escape") collapseSearch();
            }}
            placeholder="Filter registered Machines"
            className="pl-8 pr-8"
          />
          <button
            className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
            onClick={collapseSearch}
            aria-label="Clear"
          >
            <XIcon className="h-4 w-4" />
          </button>
        </div>
      )}

      <nav className="mt-3 flex flex-col gap-2 overflow-y-auto">
        {list.map((machine) => {
          const isActive = selectedMachineId === machine.id;
          return (
            <button
              key={machine.id}
              className={
                "group relative rounded-md border p-2 text-left transition-colors " +
                (isActive ? "border-primary/70 bg-primary/5" : "border-border hover:bg-muted/40")
              }
              onClick={() => onSelect(machine.id)}
              title={isActive ? "Currently shown on canvas" : "Show on canvas"}
            >
              <div className="flex items-center justify-between">
                <span className="font-medium truncate">{machine.id}</span>
                {isActive && (
                  <span className="ml-2 rounded-full bg-primary/20 px-2 py-0.5 text-[10px] font-semibold text-primary">
                    Active
                  </span>
                )}
              </div>
              <div className="mt-0.5 flex items-center gap-1.5 text-xs text-muted-foreground">
                <Clock className="h-3.5 w-3.5" />
                <span className="opacity-80">Reg:</span>
                <span className="font-medium">{formatTime(machine.registeredAt)}</span>
              </div>
            </button>
          );
        })}
      </nav>
    </aside>
  );
};

const MachineView = ({ machine, autoFitAfterDrag, showMinimap }: MachineViewProps) => (
  <div className="grid h-full grid-cols-1 lg:grid-cols-3 gap-4 p-4">
    <div className="lg:col-span-2 flex flex-col gap-4 relative">
      <Card className="flex-1 flex flex-col">
        <CardHeader>
          <CardTitle>{machine.id}</CardTitle>
          <p className="text-sm text-muted-foreground">
            Current State:{" "}
            <span className="font-mono text-primary">{machine.currentStateIds.join(", ")}</span>
          </p>
        </CardHeader>
        <CardContent className="flex-1 relative">
          <StatechartDiagram
            machine={machine}
            activeStateIds={machine.currentStateIds}
            autoFitAfterDrag={autoFitAfterDrag}
            showMinimap={showMinimap}
          />
        </CardContent>
      </Card>
      <Controls machineId={machine.id} />
    </div>
    <div className="flex flex-col">
      <DetailsPanel machine={machine} autoFitAfterDrag={autoFitAfterDrag} />
    </div>
  </div>
);

const DetailsPanel = ({ machine }: { machine: MachineState; autoFitAfterDrag: boolean }) => (
  <Tabs defaultValue="events" className="flex-1 flex flex-col overflow-hidden">
    <TabsList className="grid w-full grid-cols-3">
      <TabsTrigger value="events">
        <History className="w-4 h-4 mr-2" />
        Event Log
      </TabsTrigger>
      <TabsTrigger value="context">
        <SquareActivity className="w-4 h-4 mr-2" />
        Context
      </TabsTrigger>
      <TabsTrigger value="json">
        <FileJson className="w-4 h-4 mr-2" />
        Definition
      </TabsTrigger>
    </TabsList>
    <TabsContent value="events" className="flex-1 overflow-y-auto mt-0">
      <div className="font-mono text-xs space-y-2 p-4">
        {machine.logs
          .slice()
          .reverse()
          .map((log: LogEntry, i: number) => (
            <div key={i} className="p-2 rounded bg-muted">
              <p className="font-bold text-primary">{log.type}</p>
              <pre className="text-muted-foreground whitespace-pre-wrap break-all text-[11px]">
                {JSON.stringify(log.payload, null, 2)}
              </pre>
            </div>
          ))}
      </div>
    </TabsContent>
    <TabsContent value="context" className="flex-1 overflow-y-auto mt-0">
      <pre className="font-mono text-xs p-4">{JSON.stringify(machine.context, null, 2)}</pre>
    </TabsContent>
    <TabsContent value="json" className="flex-1 overflow-y-auto mt-0">
      <pre className="font-mono text-xs p-4">{JSON.stringify(machine.definition, null, 2)}</pre>
    </TabsContent>
  </Tabs>
);

const Controls = ({ machineId }: { machineId: string }) => {
  const [dialogOpen, setDialogOpen] = useState(false);
  const sendCommand = useInspectorStore((state) => state.sendCommand);

  return (
    <>
      <div className="absolute bottom-4 left-1/2 -translate-x-1/2">
        <Dock>
          <DockIcon onClick={() => sendCommand("resume", { machine_id: machineId })}>
            <Play className="h-4 w-4" />
          </DockIcon>
          <DockIcon onClick={() => sendCommand("pause", { machine_id: machineId })}>
            <Pause className="h-4 w-4" />
          </DockIcon>
          <DockIcon onClick={() => setDialogOpen(true)}>
            <Send className="h-4 w-4" />
          </DockIcon>
        </Dock>
      </div>
      <SendEventDialog open={dialogOpen} onOpenChange={setDialogOpen} machineId={machineId} />
    </>
  );
};

const SendEventDialog = ({ open, onOpenChange, machineId }: SendEventDialogProps) => {
  const [type, setType] = useState("");
  const [payload, setPayload] = useState("");
  const sendCommand = useInspectorStore((state) => state.sendCommand);

  const handleSend = () => {
    if (!type) return;
    let parsedPayload = {} as any;
    try {
      if (payload.trim()) {
        parsedPayload = JSON.parse(payload);
      }
    } catch (e) {
      alert("Invalid JSON in payload.");
      return;
    }
    sendCommand("send_event", { machine_id: machineId, event: { type, payload: parsedPayload } });
    onOpenChange(false);
    setType("");
    setPayload("");
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Send Event to {machineId}</DialogTitle>
        </DialogHeader>
        <div className="grid gap-4 py-4">
          <Input
            placeholder="Event Type (e.g., ENABLE)"
            value={type}
            onChange={(e) => setType(e.target.value)}
          />
          <Textarea
            placeholder='Payload (JSON), e.g., {"value": 42}'
            value={payload}
            onChange={(e) => setPayload(e.target.value)}
          />
        </div>
        <DialogFooter>
          <ShimmerButton className="w-full" onClick={handleSend}>
            <span className="whitespace-pre-wrap text-center text-sm font-medium leading-none tracking-tight text-white dark:from-white dark:to-slate-900/10 lg:text-lg">
              Send Event
            </span>
          </ShimmerButton>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

const SettingsDialog = ({
  open,
  onOpenChange,
  autoFitAfterDrag,
  onChangeAutoFit,
  showMinimap,
  onChangeShowMinimap,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  autoFitAfterDrag: boolean;
  onChangeAutoFit: (v: boolean) => void;
  showMinimap: boolean;
  onChangeShowMinimap: (v: boolean) => void;
}) => (
  <Sheet open={open} onOpenChange={onOpenChange}>
    <SheetContent>
      <SheetHeader>
        <SheetTitle>Settings</SheetTitle>
      </SheetHeader>

      {/* Layout & Canvas Section */}
      <div className="space-y-3">
        <div className="flex items-center gap-2 text-sm font-semibold">
          <MoveDiagonal2 className="h-4 w-4 text-primary" />
          <span>Layout & Canvas</span>
        </div>
        <div className="rounded-md border p-3 bg-card/50 space-y-3">
          <label className="flex items-center gap-3 text-sm">
            <input
              type="checkbox"
              className="h-4 w-4"
              checked={autoFitAfterDrag}
              onChange={(e) => onChangeAutoFit(e.target.checked)}
            />
            <div className="flex flex-col">
              <span className="font-medium">Auto-fit view after drag</span>
              <span className="text-xs text-muted-foreground">
                After moving nodes, automatically fit the diagram to the current content.
              </span>
            </div>
          </label>
          <label className="flex items-center gap-3 text-sm">
            <input
              type="checkbox"
              className="h-4 w-4"
              checked={showMinimap}
              onChange={(e) => onChangeShowMinimap(e.target.checked)}
            />
            <div className="flex flex-col">
              <span className="font-medium">Show Minimap</span>
              <span className="text-xs text-muted-foreground">
                Toggle the React Flow minimap on the canvas.
              </span>
            </div>
          </label>
        </div>
      </div>

      {/* ...you can add more sections here later... */}
    </SheetContent>
  </Sheet>
);

const WelcomePanel = () => (
  <div className="flex h-full items-center justify-center m-4">
    <Card className="w-full max-w-md">
      <CardHeader>
        <CardTitle className="text-2xl">No Live Machines Detected</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-muted-foreground">
          Run a Python script with the InspectorPlugin to begin debugging.
        </p>
      </CardContent>
    </Card>
  </div>
);
