<template>
  <div class="bg-gray-800 text-white h-screen flex flex-col font-sans">
    <!-- Header -->
    <header class="bg-gray-900 shadow-md p-4 flex-shrink-0">
      <h1 class="text-2xl font-bold text-cyan-400">St8erBoi ClearCore Controller</h1>
    </header>

    <!-- Loading State -->
    <div v-if="connectionState === 'connecting'" class="flex-grow flex items-center justify-center">
        <div class="text-center">
            <svg class="animate-spin h-10 w-10 text-cyan-400 mx-auto mb-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            <p class="text-xl text-gray-300">Connecting to Backend...</p>
            <p class="text-sm text-gray-500 mt-2">If this persists, check the terminal for Python errors.</p>
        </div>
    </div>
    
    <!-- Error State -->
    <div v-else-if="connectionState === 'error'" class="flex-grow flex items-center justify-center">
        <div class="text-center p-8 bg-red-900/20 border border-red-500 rounded-lg">
             <svg xmlns="http://www.w3.org/2000/svg" class="h-12 w-12 text-red-400 mx-auto mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p class="text-xl text-red-300">Connection Failed</p>
            <p class="text-md text-gray-400 mt-2">Could not connect to the Python backend.</p>
            <p class="font-mono text-sm text-gray-500 bg-gray-900 p-2 rounded mt-4 max-w-lg">{{ lastError }}</p>
        </div>
    </div>


    <!-- Main Content Area -->
    <div v-else-if="connectionState === 'connected'" class="flex-grow flex flex-col overflow-hidden">
      
      <!-- Top Section (Tabs) -->
      <div class="p-4 flex-shrink-0">
        <div class="mb-4 flex border-b border-gray-700">
          <button @click="activeTab = 'manual'" :class="tabClass('manual')">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-2" viewBox="0 0 20 20" fill="currentColor"><path d="M10 3.5a1.5 1.5 0 013 0V4a1 1 0 001 1h3a1 1 0 011 1v3a1 1 0 01-1 1h-1v1a1 1 0 11-2 0v-1H9v1a1 1 0 11-2 0v-1H6a1 1 0 01-1-1V6a1 1 0 011-1h3a1 1 0 001-1v-.5zM10 5H6v3h1v1a1 1 0 112 0v-1h1V5z" /></svg>
            Manual Controls
          </button>
          <button @click="activeTab = 'scripting'" :class="tabClass('scripting')">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-2" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M4 4a2 2 0 00-2 2v8a2 2 0 002 2h12a2 2 0 002-2V8a2 2 0 00-2-2h-5L9 4H4zm2 6a1 1 0 011-1h6a1 1 0 110 2H7a1 1 0 01-1-1zm1 3a1 1 0 100 2h4a1 1 0 100-2H7z" clip-rule="evenodd" /></svg>
            Scripting
          </button>
        </div>
      </div>

      <!-- Scrollable Tab Content -->
      <main class="flex-grow p-4 pt-0 overflow-auto">
        <!-- Manual Controls Tab -->
        <div v-if="activeTab === 'manual'">
          <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <!-- Injector Controls -->
            <div class="bg-gray-700/50 rounded-lg p-4 flex flex-col space-y-4">
              <h2 class="text-xl font-semibold text-cyan-300 border-b border-gray-600 pb-2">Injector</h2>
              <ControlSection title="Setup">
                  <div class="flex items-center justify-between">
                      <button @click="sendCommand('injector', 'ENABLE')" class="btn btn-success">Enable</button>
                      <button @click="sendCommand('injector', 'DISABLE')" class="btn btn-warning">Disable</button>
                      <button @click="sendCommand('injector', 'HOME')" class="btn btn-primary">Home Axis</button>
                  </div>
              </ControlSection>
              <ControlSection title="Movement">
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <InputGroup label="Velocity (mm/s)" v-model.number="injectorInputs.velocity" />
                    <InputGroup label="Acceleration (mm/s²)" v-model.number="injectorInputs.acceleration" />
                </div>
                <div class="flex items-end space-x-2 mt-2">
                  <InputGroup label="Absolute Position (mm)" v-model.number="injectorInputs.absolutePosition" class="flex-grow" />
                  <button @click="sendCommand('injector', 'MOVE_ABSOLUTE', { position: injectorInputs.absolutePosition, velocity: injectorInputs.velocity, acceleration: injectorInputs.acceleration })" class="btn btn-primary">Move</button>
                </div>
                <div class="flex items-center justify-between mt-4">
                  <p class="text-sm">Jog:</p>
                  <div class="flex space-x-2">
                      <button @click="sendCommand('injector', 'JOG_NEGATIVE', { velocity: injectorInputs.velocity, acceleration: injectorInputs.acceleration })" class="btn btn-secondary">-</button>
                      <button @click="sendCommand('injector', 'STOP')" class="btn btn-danger">STOP</button>
                      <button @click="sendCommand('injector', 'JOG_POSITIVE', { velocity: injectorInputs.velocity, acceleration: injectorInputs.acceleration })" class="btn btn-secondary">+</button>
                  </div>
                </div>
              </ControlSection>
               <ControlSection title="Status">
                  <div class="bg-gray-900 p-3 rounded-md text-center">
                      <span class="text-sm text-gray-400">Current Position: </span>
                      <span class="font-mono text-lg text-cyan-300">{{ injectorPosition }} mm</span>
                  </div>
              </ControlSection>
            </div>

            <!-- Fill Head Controls -->
            <div class="bg-gray-700/50 rounded-lg p-4 flex flex-col space-y-4">
              <h2 class="text-xl font-semibold text-green-300 border-b border-gray-600 pb-2">Fill Head</h2>
              <ControlSection title="Setup">
                      <div class="flex items-center justify-between">
                          <button @click="sendCommand('fillhead', 'ENABLE')" class="btn btn-success">Enable</button>
                          <button @click="sendCommand('fillhead', 'DISABLE')" class="btn btn-warning">Disable</button>
                          <button @click="sendCommand('fillhead', 'HOME')" class="btn btn-primary">Home Axis</button>
                      </div>
              </ControlSection>
              <ControlSection title="Actions">
                  <div class="space-y-4">
                      <div class="bg-gray-800/50 p-3 rounded-md">
                          <p class="font-semibold mb-2">Fill</p>
                          <div class="flex items-end space-x-2">
                              <InputGroup label="Volume (mL)" v-model.number="fillheadInputs.fillVolume" class="flex-grow"/>
                              <InputGroup label="Speed (%)" v-model.number="fillheadInputs.fillSpeed" class="flex-grow"/>
                              <button @click="sendCommand('fillhead', 'FILL', { volume: fillheadInputs.fillVolume, speed: fillheadInputs.fillSpeed })" class="btn btn-primary">Run</button>
                          </div>
                      </div>
                      <div class="bg-gray-800/50 p-3 rounded-md">
                          <p class="font-semibold mb-2">Dispense</p>
                           <div class="flex items-end space-x-2">
                              <InputGroup label="Volume (mL)" v-model.number="fillheadInputs.dispenseVolume" class="flex-grow"/>
                              <InputGroup label="Speed (%)" v-model.number="fillheadInputs.dispenseSpeed" class="flex-grow"/>
                              <button @click="sendCommand('fillhead', 'DISPENSE', { volume: fillheadInputs.dispenseVolume, speed: fillheadInputs.dispenseSpeed })" class="btn btn-primary">Run</button>
                          </div>
                      </div>
                  </div>
              </ControlSection>
               <ControlSection title="Status">
                  <div class="bg-gray-900 p-3 rounded-md text-center">
                      <span class="text-sm text-gray-400">Current Position: </span>
                      <span class="font-mono text-lg text-green-300">{{ fillheadPosition }} mm</span>
                  </div>
              </ControlSection>
            </div>
          </div>
        </div>
        
        <!-- Scripting Tab -->
        <div v-if="activeTab === 'scripting'">
          <div class="bg-gray-700/50 rounded-lg p-4">
              <h2 class="text-xl font-semibold text-purple-300 border-b border-gray-600 pb-2 mb-4">Script Editor</h2>
              <div class="flex space-x-2 mb-4">
                  <button @click="loadScript" class="btn btn-secondary">Load Script</button>
                  <button @click="saveScript" class="btn btn-secondary">Save</button>
                  <button @click="saveScriptAs" class="btn btn-secondary">Save As...</button>
              </div>
              <textarea v-model="scriptContent" class="form-textarea w-full h-96 font-mono text-sm" placeholder="Enter your script here..."></textarea>
              <div class="mt-4 flex items-center justify-between">
                  <div class="flex items-center space-x-4">
                      <span class="font-semibold">Run Mode:</span>
                      <label class="flex items-center"><input type="radio" v-model="runMode" value="step" class="form-radio mr-1">Step</label>
                      <label class="flex items-center"><input type="radio" v-model="runMode" value="continuous" class="form-radio mr-1">Continuous</label>
                  </div>
                  <div class="flex space-x-2">
                      <button @click="validateScript" class="btn btn-warning">Validate</button>
                      <button @click="runScript" class="btn btn-success">Run Script</button>
                  </div>
              </div>
          </div>
        </div>
      </main>
      
      <!-- Persistent Terminal Section -->
      <div class="p-4 flex-shrink-0 border-t-2 border-gray-700">
        <div class="bg-gray-700/50 rounded-lg p-4">
            <h2 class="text-xl font-semibold text-orange-300 border-b border-gray-600 pb-2 mb-4">Terminal</h2>
            <div class="bg-gray-900 rounded-md h-40 p-2 overflow-y-auto font-mono text-sm flex flex-col-reverse">
                <div v-for="(line, index) in terminalLog" :key="index" :class="line.type === 'sent' ? 'text-cyan-400' : 'text-gray-300'">
                    <span class="mr-2">{{ line.type === 'sent' ? '>>' : '<<' }}</span>{{ line.message }}
                </div>
            </div>
            <div class="mt-4 flex space-x-2">
                <select v-model="terminal.target" class="form-select w-48">
                    <option value="injector">Injector</option>
                    <option value="fillhead">Fill Head</option>
                </select>
                <input type="text" v-model="terminal.command" @keyup.enter="sendTerminalCommand" class="form-input flex-grow" placeholder="Enter raw command...">
                <button @click="sendTerminalCommand" class="btn btn-primary">Send</button>
            </div>
        </div>
      </div>
    </div>

    <!-- Footer / Status Panel -->
    <footer class="bg-gray-900 shadow-inner p-2 flex justify-between items-center text-sm flex-shrink-0">
      <div class="flex items-center space-x-4">
        <div class="flex items-center">
          <span class="mr-2">Injector:</span>
          <div class="w-3 h-3 rounded-full" :class="statusClass(injectorStatus)"></div>
          <span class="ml-2 font-mono">{{ injectorStatus }}</span>
        </div>
        <div class="flex items-center">
          <span class="mr-2">Fill Head:</span>
          <div class="w-3 h-3 rounded-full" :class="statusClass(fillheadStatus)"></div>
          <span class="ml-2 font-mono">{{ fillheadStatus }}</span>
        </div>
      </div>
      <div>
        <p>Last Message: <span class="font-mono text-gray-400">{{ lastMessage || 'None' }}</span></p>
      </div>
    </footer>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed, onBeforeUnmount, watch } from 'vue';

// --- Helper Components (inlined for simplicity, but defined as setup components to avoid warnings) ---
const ControlSection = {
  props: ['title'],
  setup(props, { slots }) {
    return () => h('div', { class: 'bg-gray-800/50 p-3 rounded-md' }, [
      h('h3', { class: 'font-bold text-gray-300 mb-2' }, props.title),
      slots.default && slots.default()
    ]);
  }
};

const InputGroup = {
  props: ['label', 'modelValue'],
  emits: ['update:modelValue'],
  setup(props, { emit }) {
    return () => h('div', {}, [
      h('label', { class: 'block text-sm font-medium text-gray-400 mb-1' }, props.label),
      h('input', {
        type: 'number',
        class: 'form-input w-full',
        value: props.modelValue,
        onInput: (event) => emit('update:modelValue', event.target.value)
      })
    ]);
  }
};


// --- Refs and Reactive State ---
const activeTab = ref('manual');
const lastMessage = ref('');
const lastError = ref('');
const statusInterval = ref(null);
const connectionState = ref('connecting'); // 'connecting', 'connected', 'error'

const allDevices = ref({});

const injectorInputs = reactive({
  velocity: 10,
  acceleration: 100,
  absolutePosition: 0,
});
const fillheadInputs = reactive({
  fillVolume: 5,
  fillSpeed: 50,
  dispenseVolume: 1,
  dispenseSpeed: 50,
});

const scriptContent = ref('; Example Script\nHOME INJECTOR\nMOVE INJECTOR 50\nHOME FILLHEAD\nFILL 10');
const runMode = ref('continuous');

const terminal = reactive({
  target: 'injector',
  command: '',
});
const terminalLog = ref([]);


// --- Computed Properties (Derived State) ---
const injector = computed(() => allDevices.value.injector || { isConnected: false, telemetry: {} });
const fillhead = computed(() => allDevices.value.fillhead || { isConnected: false, telemetry: {} });

const injectorStatus = computed(() => {
    if (!injector.value.isConnected) return 'Disconnected';
    return injector.value.telemetry?.mainState || 'Connected';
});

const fillheadStatus = computed(() => {
    if (!fillhead.value.isConnected) return 'Disconnected';
    return fillhead.value.telemetry?.stateX || 'Connected';
});

const injectorPosition = computed(() => {
    const pos = injector.value.telemetry?.positionMachine;
    return typeof pos === 'number' ? pos.toFixed(3) : 'N/A';
});

const fillheadPosition = computed(() => {
    const pos = fillhead.value.telemetry?.axes?.x?.position;
    return typeof pos === 'number' ? pos.toFixed(3) : 'N/A';
});

const tabClass = computed(() => (tabName) => ({
  'px-4 py-2 text-sm font-medium flex items-center': true,
  'border-b-2 border-cyan-400 text-cyan-400 bg-gray-700/50 rounded-t-md': activeTab.value === tabName,
  'text-gray-400 hover:text-white': activeTab.value !== tabName,
}));

const statusClass = computed(() => (status) => ({
  'bg-green-500': status === 'Connected' || status === 'Ready' || (typeof status === 'string' && status.toLowerCase().includes('ready')),
  'bg-red-500': status === 'Disconnected' || status === 'Error',
  'bg-yellow-500': status === 'Connecting' || status === 'Busy' || status === '---',
  'animate-pulse': status === 'Connecting' || status === 'Busy',
}));


// --- API Communication ---
async function apiRequest(endpoint, options = {}) {
  try {
    const data = await window.electron.apiRequest(endpoint, options);
    if (data.message) lastMessage.value = data.message;
    return data;
  } catch (error) {
    console.error(`API Error on ${endpoint}:`, error);
    lastMessage.value = 'API Communication Error';
    lastError.value = typeof error === 'string' ? error : error.message;
    connectionState.value = 'error';
    if (statusInterval.value) clearInterval(statusInterval.value); 
    return null;
  }
}

// --- Lifecycle Hooks ---
onMounted(() => {
  pollStatus(); 
  statusInterval.value = setInterval(pollStatus, 2000);
});

onBeforeUnmount(() => {
    if (statusInterval.value) clearInterval(statusInterval.value);
});

// --- NEW: Watcher for detailed debugging ---
watch(allDevices, (newVal, oldVal) => {
    console.log('%c[STATE CHANGED]%c', 'color: #7fdbff; font-weight: bold;', 'color: default;');
    console.log('Previous State:', JSON.parse(JSON.stringify(oldVal)));
    console.log('New State:', JSON.parse(JSON.stringify(newVal)));
    console.log(`Computed Injector Status: ${injectorStatus.value}`);
    console.log(`Computed Fillhead Status: ${fillheadStatus.value}`);
    console.log('------------------------------------');
}, { deep: true });


// --- Methods ---
async function pollStatus() {
    console.log('%c[POLLING STATUS]%c', 'color: #f0c674; font-weight: bold;', 'color: default;');
    const data = await apiRequest('devices');
    if (data) {
        // NEW: Log the raw data received from the backend
        console.log('Raw data from /api/devices:', JSON.parse(JSON.stringify(data)));

        if (connectionState.value !== 'connected') {
            connectionState.value = 'connected';
        }

        if(data.devices) {
            allDevices.value = data.devices;
        }

        if (data.logs && data.logs.length > 0) {
            data.logs.forEach(logMsg => {
                const type = logMsg.startsWith("SEND") ? 'sent' : 'received';
                if (!terminalLog.value.some(l => l.message === logMsg)) {
                    terminalLog.value.unshift({ type: type, message: logMsg });
                }
            });
        }
    } else {
        console.error("Polling failed or returned no data.");
    }
}

async function sendCommand(device, command, params = {}) {
  if (connectionState.value !== 'connected') {
      lastMessage.value = "Error: Not connected to backend.";
      return;
  }
  
  const targetDevice = allDevices.value[device];
  if (!targetDevice || !targetDevice.isConnected) {
      lastMessage.value = `Error: ${device} is not connected.`;
      return;
  }

  await apiRequest('send_command', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ device, command, params }),
  });
  setTimeout(pollStatus, 250);
}

async function sendTerminalCommand() {
    if (!terminal.command) return;
    const { target, command } = terminal;
    await sendCommand(target, 'RAW_COMMAND', { raw: command });
    terminal.command = '';
}

// --- Scripting Methods (unchanged) ---
function loadScript() {
  const input = document.createElement('input');
  input.type = 'file';
  input.accept = '.txt,.gcode';
  input.onchange = e => {
    const file = e.target.files[0];
    const reader = new FileReader();
    reader.onload = res => {
      scriptContent.value = res.target.result;
      lastMessage.value = `Script '${file.name}' loaded.`;
    };
    reader.onerror = err => console.error(err);
    reader.readAsText(file);
  };
  input.click();
}

function saveScriptAs() {
  const blob = new Blob([scriptContent.value], { type: 'text/plain;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'script.txt';
  a.click();
  URL.revokeObjectURL(url);
  lastMessage.value = "Script saved.";
}

function saveScript() {
    saveScriptAs();
}

async function validateScript() {
  lastMessage.value = "Validating script...";
  await apiRequest('validate_script', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ script: scriptContent.value }),
  });
}

async function runScript() {
  lastMessage.value = "Running script...";
   await apiRequest('run_script', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ script: scriptContent.value, mode: runMode.value }),
  });
}

</script>

<style lang="postcss">
.form-input, .form-select, .form-textarea, .form-radio {
  @apply bg-gray-900 border border-gray-600 rounded-md shadow-sm text-white focus:ring-cyan-500 focus:border-cyan-500;
}
.form-input, .form-select { @apply px-3 py-2; }
.form-textarea { @apply px-3 py-2; }
.form-radio { @apply h-4 w-4 text-cyan-600; }

.btn {
  @apply px-4 py-2 font-semibold rounded-md shadow-md transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-gray-800;
}
.btn-primary { @apply bg-cyan-600 hover:bg-cyan-700 text-white focus:ring-cyan-500; }
.btn-secondary { @apply bg-gray-600 hover:bg-gray-700 text-gray-200 focus:ring-gray-500; }
.btn-danger { @apply bg-red-600 hover:bg-red-700 text-white focus:ring-red-500; }
.btn-success { @apply bg-green-600 hover:bg-green-700 text-white focus:ring-green-500; }
.btn-warning { @apply bg-yellow-500 hover:bg-yellow-600 text-white focus:ring-yellow-400; }
.btn:disabled { @apply bg-gray-500 cursor-not-allowed opacity-50; }
</style>
