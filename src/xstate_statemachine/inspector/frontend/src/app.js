document.addEventListener('DOMContentLoaded', () => {
    // --- Globals ---
    const { QueryClient, QueryCache, MutationCache } = TanStackQueryCore;

    // --- DOM Elements ---
    const themeToggle = document.getElementById('theme-toggle');
    const themeIconLight = document.getElementById('theme-icon-light');
    const themeIconDark = document.getElementById('theme-icon-dark');
    const machineListEl = document.getElementById('machines');
    const sessionListEl = document.getElementById('sessions');
    const noMachineSelectedEl = document.getElementById('no-machine-selected');
    const machineDetailsEl = document.getElementById('machine-details');
    const machineTitleEl = document.getElementById('machine-title');
    const diagramEl = document.getElementById('diagram');
    const contextEl = document.getElementById('context');
    const eventLogEl = document.getElementById('event-log');
    const playbackControlsEl = document.getElementById('playback-controls');

    // --- App State ---
    // Managed by TanStack Query and WebSocket events

    // --- Initialization ---
    function init() {
        // Theme setup
        if (localStorage.getItem('theme') === 'dark' || (!('theme' in localStorage) && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
            document.body.classList.add('dark');
            themeIconDark.classList.remove('hidden');
            themeIconLight.classList.add('hidden');
        } else {
            document.body.classList.remove('dark');
        }

        themeToggle.addEventListener('click', toggleTheme);

        // WebSocket setup
        setupWebSocket();
    }

    function toggleTheme() {
        if (document.body.classList.contains('dark')) {
            document.body.classList.remove('dark');
            localStorage.setItem('theme', 'light');
            themeIconDark.classList.add('hidden');
            themeIconLight.classList.remove('hidden');
        } else {
            document.body.classList.add('dark');
            localStorage.setItem('theme', 'dark');
            themeIconDark.classList.remove('hidden');
            themeIconLight.classList.add('hidden');
        }
    }

    function setupWebSocket() {
        const ws = new WebSocket('ws://127.0.0.1:8008/ws');
        ws.onopen = () => console.log('WebSocket connection established.');
        ws.onmessage = (event) => {
            const message = JSON.parse(event.data);

            queryClient.setQueryData(['machines'], (oldData = {}) => {
                const newData = { ...oldData };
                const { machine_id, type, payload } = message;

                switch (type) {
                    case 'machine_registered':
                        newData[machine_id] = {
                            id: machine_id,
                            definition: payload.definition,
                            currentState: payload.initial_state,
                            context: payload.initial_context,
                            logs: [message],
                        };
                        break;
                    case 'transition':
                        if (newData[machine_id]) {
                            newData[machine_id].currentState = payload.to_states;
                            newData[machine_id].context = payload.full_context;
                            newData[machine_id].logs.push(message);
                        }
                        break;
                    default:
                         if (newData[machine_id]) {
                            newData[machine_id].logs.push(message);
                        }
                        break;
                }
                return newData;
            });
        };
        ws.onclose = () => console.log('WebSocket connection closed.');
        ws.onerror = (error) => console.error('WebSocket error:', error);
    }

    // --- TanStack Query Setup ---
    const queryClient = new QueryClient({
        queryCache: new QueryCache(),
        mutationCache: new MutationCache(),
    });

    // --- Data Fetching (Queries) ---
    const getSessions = async () => {
        const res = await fetch('/api/sessions');
        if (!res.ok) {
            throw new Error('Network response was not ok');
        }
        return res.json();
    };

    // --- UI Rendering ---
    function renderMachineList(machines = {}) {
        machineListEl.innerHTML = '';
        const machineIds = Object.keys(machines);
        if (machineIds.length === 0) {
            machineListEl.innerHTML = '<li class="text-gray-500 text-sm">No live machines.</li>';
            return;
        }
        machineIds.forEach(machineId => {
            const li = document.createElement('li');
            li.className = 'p-2 rounded-md cursor-pointer hover:bg-gray-200 dark:hover:bg-gray-700';
            li.textContent = machineId;
            li.dataset.machineId = machineId;
            // TODO: Add click listener and pause/resume buttons
            machineListEl.appendChild(li);
        });
    }

    function renderSessionList(sessionIds = []) {
        sessionListEl.innerHTML = '';
        if (!sessionIds || sessionIds.length === 0) {
            sessionListEl.innerHTML = '<li class="text-gray-500 text-sm">No sessions found.</li>';
            return;
        }
        sessionIds.forEach(sessionId => {
            const li = document.createElement('li');
            li.className = 'p-2 rounded-md cursor-pointer hover:bg-gray-200 dark:hover:bg-gray-700';
            li.textContent = sessionId;
            li.dataset.sessionId = sessionId;
            // TODO: Add click listener to select session
            sessionListEl.appendChild(li);
        });
    }

    // --- Main Logic ---
    function main() {
        // Subscribe to query updates
        const unsubscribe = queryClient.getQueryCache().subscribe((event) => {
            if (event.type === 'updated') {
                const queryKey = event.query.queryKey[0];
                if (queryKey === 'sessions') {
                    renderSessionList(event.query.state.data);
                } else if (queryKey === 'machines') {
                    renderMachineList(event.query.state.data);
                }
            }
        });

        // Initial fetch
        queryClient.fetchQuery({ queryKey: ['sessions'], queryFn: getSessions });
        // Set initial state for machines
        queryClient.setQueryData(['machines'], {});
        renderMachineList();
    }

    // --- Start the app ---
    init();
    main();
});
