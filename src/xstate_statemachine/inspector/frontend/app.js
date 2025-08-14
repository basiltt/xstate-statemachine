document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const themeToggle = document.getElementById('theme-toggle');
    const machineList = document.getElementById('machines');
    const sessionList = document.getElementById('sessions');
    const noMachineSelected = document.getElementById('no-machine-selected');
    const machineDetails = document.getElementById('machine-details');
    const machineTitle = document.getElementById('machine-title');
    const diagramContainer = document.getElementById('diagram');
    const contextContainer = document.getElementById('context');
    const eventLog = document.getElementById('event-log');
    const playbackControls = document.getElementById('playback-controls');
    const playBtn = document.getElementById('play-btn');
    const pauseBtn = document.getElementById('pause-btn');
    const prevBtn = document.getElementById('prev-btn');
    const nextBtn = document.getElementById('next-btn');
    const playbackStatus = document.getElementById('playback-status');

    // Application State
    let state = {
        machines: {},
        sessions: {},
        selectedMachine: null,
        selectedSession: null,
        playback: {
            history: [],
            currentIndex: -1,
            isPlaying: false,
            timer: null,
        },
    };

    // --- Initialization ---
    init();

    function init() {
        themeToggle.addEventListener('click', () => document.body.classList.toggle('dark'));
        setupWebSocket();
        loadSessions();
        setupPlaybackControls();
    }

    function setupWebSocket() {
        const ws = new WebSocket('ws://127.0.0.1:8008/ws');
        ws.onmessage = (event) => handleMessage(JSON.parse(event.data), 'live');
        ws.onclose = () => logMessage({ type: 'status', payload: 'WebSocket connection closed.' });
        ws.onerror = (error) => logMessage({ type: 'error', payload: `WebSocket error: ${error}` });
    }

    // --- Message Handling ---
    function handleMessage(message, source = 'live') {
        if (source === 'live') {
            logMessage(message);
        }

        switch (message.type) {
            case 'machine_registered':
                registerMachine(message);
                break;
            case 'transition':
                updateTransition(message);
                break;
        }

        if (message.machine_id === state.selectedMachine) {
            updateSelectedMachineView();
        }
    }

    function registerMachine(message) {
        const { machine_id, payload } = message;
        state.machines[machine_id] = {
            id: machine_id,
            definition: payload.definition,
            currentState: payload.initial_state,
            context: payload.initial_context,
            logs: [],
        };
        renderMachineList();
    }

    function updateTransition(message) {
        const { machine_id, payload } = message;
        if (state.machines[machine_id]) {
            state.machines[machine_id].currentState = payload.to_states;
            state.machines[machine_id].context = payload.full_context;
        }
    }

    function logMessage(message) {
        if (message.machine_id && state.machines[message.machine_id]) {
            state.machines[message.machine_id].logs.push(message);
        }
        if (message.machine_id === state.selectedMachine) {
            appendLogEntry(message);
        }
    }

    function appendLogEntry(message) {
        const logEntry = document.createElement('li');
        logEntry.textContent = `[${message.timestamp}] [${message.type}] ${JSON.stringify(message.payload)}`;
        eventLog.appendChild(logEntry);
        eventLog.scrollTop = eventLog.scrollHeight;
    }

    // --- UI Rendering ---
    function renderMachineList() {
        machineList.innerHTML = '';
        Object.keys(state.machines).forEach(machineId => {
            const li = document.createElement('li');
            li.textContent = machineId;
            li.dataset.machineId = machineId;
            if (machineId === state.selectedMachine && !state.selectedSession) {
                li.classList.add('active');
            }
            li.addEventListener('click', () => selectLiveMachine(machineId));
            machineList.appendChild(li);
        });
    }

    function renderSessionList() {
        sessionList.innerHTML = '';
        Object.keys(state.sessions).forEach(sessionId => {
            const li = document.createElement('li');
            li.textContent = sessionId;
            li.dataset.sessionId = sessionId;
            if (sessionId === state.selectedSession) {
                li.classList.add('active');
            }
            li.addEventListener('click', () => selectSession(sessionId));
            sessionList.appendChild(li);
        });
    }

    async function updateSelectedMachineView() {
        const machineId = state.selectedMachine || state.selectedSession;
        if (!machineId) {
            noMachineSelected.style.display = 'flex';
            machineDetails.classList.add('hidden');
            return;
        }

        noMachineSelected.style.display = 'none';
        machineDetails.classList.remove('hidden');

        const machine = state.machines[machineId];
        machineTitle.textContent = machine.id;

        playbackControls.style.display = state.selectedSession ? 'block' : 'none';

        const mermaidGraph = generateMermaidGraph(machine.definition);
        diagramContainer.innerHTML = mermaidGraph;
        diagramContainer.removeAttribute('data-processed');
        await mermaid.run({ nodes: [diagramContainer] });

        contextContainer.textContent = JSON.stringify(machine.context, null, 2);

        eventLog.innerHTML = '';
        machine.logs.forEach(appendLogEntry);
    }

    function resetToInitialState(machineId) {
        const machine = state.machines[machineId];
        const registrationMessage = state.playback.history.find(m => m.type === 'machine_registered');
        if (registrationMessage) {
            machine.currentState = registrationMessage.payload.initial_state;
            machine.context = registrationMessage.payload.initial_context;
            machine.logs = [];
        }
    }

    // --- Data Fetching ---
    async function loadSessions() {
        try {
            const response = await fetch('/api/sessions');
            const sessionIds = await response.json();
            sessionIds.forEach(id => {
                if (!state.sessions[id]) state.sessions[id] = {};
            });
            renderSessionList();
        } catch (e) {
            console.error("Failed to load sessions:", e);
        }
    }

    // --- Selection Logic ---
    function selectLiveMachine(machineId) {
        state.selectedMachine = machineId;
        state.selectedSession = null;
        renderMachineList();
        renderSessionList();
        updateSelectedMachineView();
    }

    async function selectSession(sessionId) {
        state.selectedSession = sessionId;
        state.selectedMachine = null;

        try {
            const response = await fetch(`/api/history/${sessionId}`);
            state.playback.history = await response.json();
            state.playback.currentIndex = -1;

            const registrationMessage = state.playback.history.find(m => m.type === 'machine_registered');
            if (registrationMessage) {
                if (!state.machines[sessionId]) {
                    registerMachine(registrationMessage);
                }
                resetToInitialState(sessionId);
                state.selectedMachine = sessionId; // Select the machine to view its data
            }

            renderMachineList();
            renderSessionList();
            updateSelectedMachineView();
            updatePlaybackStatus();
        } catch(e) {
            console.error(`Failed to load history for ${sessionId}:`, e);
        }
    }

    // --- Playback Logic ---
    function setupPlaybackControls() {
        playBtn.addEventListener('click', playHistory);
        pauseBtn.addEventListener('click', pauseHistory);
        nextBtn.addEventListener('click', () => stepHistory(1));
        prevBtn.addEventListener('click', () => stepHistory(-1));
    }

    function playHistory() {
        if (state.playback.isPlaying) return;
        state.playback.isPlaying = true;

        function tick() {
            if (!state.playback.isPlaying) return;
            const hasNext = stepHistory(1);
            if (hasNext) {
                state.playback.timer = setTimeout(tick, 500);
            } else {
                state.playback.isPlaying = false;
            }
        }
        tick();
    }

    function pauseHistory() {
        state.playback.isPlaying = false;
        clearTimeout(state.playback.timer);
    }

    function stepHistory(direction) {
        pauseHistory();
        const newIndex = state.playback.currentIndex + direction;

        if (newIndex < -1 || newIndex >= state.playback.history.length) {
            return false;
        }

        state.playback.currentIndex = newIndex;

        // Re-calculate state up to current index
        const machineId = state.selectedSession;
        resetToInitialState(machineId);
        for(let i=0; i <= state.playback.currentIndex; i++) {
            const message = state.playback.history[i];
            // Don't log during this simulated handling
            switch (message.type) {
                case 'transition':
                    updateTransition(message);
                    break;
            }
            state.machines[machineId].logs.push(message);
        }

        updateSelectedMachineView();
        updatePlaybackStatus();
        return newIndex < state.playback.history.length - 1;
    }

    function updatePlaybackStatus() {
        if (!state.selectedSession) {
            playbackStatus.textContent = '';
            return;
        }
        const total = state.playback.history.length;
        const current = state.playback.currentIndex + 1;
        playbackStatus.textContent = `${current} / ${total}`;
    }

    // --- Mermaid Diagram Generation ---
    function generateMermaidGraph(definition) {
        let graph = 'graph TD\n';
        const states = definition.states;

        function processState(stateKey, parentKey) {
            graph += `  ${stateKey}\n`;
            const state = states[stateKey];
            if (state.on) {
                for (const event in state.on) {
                    const transition = state.on[event];
                    let target;
                    if(typeof transition === 'string') {
                        target = transition;
                    } else if (typeof transition === 'object' && transition.target) {
                        target = transition.target;
                    }
                    if(target) {
                         graph += `  ${stateKey} -- ${event} --> ${target}\n`;
                    }
                }
            }
        }

        for (const stateKey in states) {
            processState(stateKey, null);
        }

        return graph;
    }
});
