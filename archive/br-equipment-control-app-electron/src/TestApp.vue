<template>
  <div class="min-h-screen bg-gray-900 text-white flex flex-col items-center justify-center p-8">
    <img alt="st8erboi logo" :src="logo" class="w-24 h-24 mb-6" />
    <h1 class="text-3xl font-bold text-white mb-2">Welcome to st8erboi-app!</h1>
    <p class="text-xl text-white mb-6" v-if="message">{{ message }}</p>

    <div class="w-full max-w-md bg-gray-800 p-4 rounded-lg shadow-md">
      <h2 class="text-lg font-semibold text-gray-300 mb-4">System Status</h2>
      <ul class="space-y-2">
        <li class="flex justify-between items-center">
          <span>Electron</span>
          <span class="text-green-400">● Online</span>
        </li>
        <li class="flex justify-between items-center">
          <span>Vite</span>
          <span class="text-green-400">● Online</span>
        </li>
        <li class="flex justify-between items-center">
          <span>Tailwind</span>
          <span :class="tailwindLoaded ? 'text-green-400' : 'text-red-400'">● {{ tailwindLoaded ? 'Online' : 'Offline' }}</span>
        </li>
        <li class="flex justify-between items-center">
          <span>Python Server</span>
          <span :class="backendOnline ? 'text-green-400' : 'text-red-400'">● {{ backendOnline ? 'Online' : 'Offline' }}</span>
        </li>
      </ul>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import logo from './assets/logo.png';

const message = ref('');
const backendOnline = ref(false);
const tailwindLoaded = ref(false);

onMounted(() => {
  const test = document.createElement('div');
  test.className = 'text-[rgb(239,68,68)]';
  test.style.display = 'none';
  document.body.appendChild(test);
  const color = getComputedStyle(test).color;
  tailwindLoaded.value = color.includes('239, 68, 68');
  test.remove();

  fetch('http://127.0.0.1:5000/api/data')
    .then(response => response.json())
    .then(data => {
      message.value = '';
      backendOnline.value = true;
    })
    .catch(error => {
      console.error('Error fetching backend:', error);
      backendOnline.value = false;
    });
});
</script>

<style>
body {
  margin: 0;
  font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont,
    "Segoe UI", Roboto, "Helvetica Neue", Arial, "Noto Sans", sans-serif,
    "Apple Color Emoji", "Segoe UI Emoji", "Segoe UI Symbol", "Noto Color Emoji";
}
</style>
