// src/xstate_statemachine/inspector/frontend/src/App.tsx

import { useEffect, useState } from "react";
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
  onSelectMachine: (id: string) => void;
}

interface MachineViewProps {
  machine: MachineState;
  autoFitAfterDrag: boolean;
}

interface SendEventDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  machineId: string;
}

// --- Main App Component ---
export default function App() {
  useInspectorSocket();
  const machines = useInspectorStore((state) => state.machines);
  const isConnected = useInspectorStore((state) => state.isConnected);
  const [selectedMachineId, setSelectedMachineId] = useState<string | null>(null);
  const [isDark, setIsDark] = useState(false);

  // Settings state: Auto-fit view after drag (persisted)
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [autoFitAfterDrag, setAutoFitAfterDrag] = useState<boolean>(() => {
    const stored = localStorage.getItem("autoFitAfterDrag");
    return stored ? stored === "true" : true; // default enabled
  });

  useEffect(() => {
    const machineIds = Object.keys(machines);
    if ((!selectedMachineId || !machines[selectedMachineId]) && machineIds.length > 0) {
      setSelectedMachineId(machineIds[0]);
    }
  }, [machines, selectedMachineId]);

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
          onSelectMachine={setSelectedMachineId}
        />
        <main className="flex-1 flex flex-col overflow-hidden">
          {selectedMachine ? (
            <MachineView
              key={selectedMachine.id}
              machine={selectedMachine}
              autoFitAfterDrag={autoFitAfterDrag}
            />
          ) : (
            <WelcomePanel />
          )}
        </main>
      </div>

      {/* Settings Dialog */}
      <SettingsDialog
        open={settingsOpen}
        onOpenChange={setSettingsOpen}
        autoFitAfterDrag={autoFitAfterDrag}
        onChangeAutoFit={handleToggleAutoFit}
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

const Sidebar = ({ machines, selectedMachineId, onSelectMachine }: SidebarProps) => (
  <aside className="hidden w-72 flex-col border-r bg-card p-4 sm:flex">
    <h2 className="text-base font-semibold tracking-tight">Live Machines</h2>
    <nav className="mt-4 flex flex-col gap-1">
      {Object.values(machines).map((machine) => (
        <div key={machine.id}>
          <Button
            variant={selectedMachineId === machine.id ? "secondary" : "ghost"}
            className="w-full justify-start"
            onClick={() => onSelectMachine(machine.id)}
          >
            {machine.id}
          </Button>
        </div>
      ))}
    </nav>
  </aside>
);

const MachineView = ({ machine, autoFitAfterDrag }: MachineViewProps) => (
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
    let parsedPayload = {};
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
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  autoFitAfterDrag: boolean;
  onChangeAutoFit: (v: boolean) => void;
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
        <div className="rounded-md border p-3 bg-card/50">
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
