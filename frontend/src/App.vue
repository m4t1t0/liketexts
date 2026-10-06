<script setup lang="ts">
import { computed } from "vue";
import { RouterLink, RouterView, useRoute, useRouter } from "vue-router";
import { useAuthStore } from "./stores/auth";
import Avatar from "./components/Avatar.vue";

const auth = useAuthStore();
const route = useRoute();
const router = useRouter();

function logout(): void {
  auth.logout();
  void router.push({ name: "home" });
}

/** Nav items mirror the Substack sidebar (Chat/Activity are stubs for now). */
const navItems = computed(() => [
  { label: "Home", to: "/", icon: "home", exact: true },
  {
    label: "Subscriptions",
    to: auth.isLoggedIn ? "/reader" : "/login",
    icon: "subscriptions",
  },
  { label: "Chat", to: "/login", icon: "chat" },
  { label: "Activity", to: "/login", icon: "activity" },
  { label: "Explore", to: "/#writers", icon: "explore" },
  {
    label: "Profile",
    to: auth.isLoggedIn ? "/profile" : "/login",
    icon: "profile",
  },
]);

function isActive(item: { to: string; exact?: boolean }): boolean {
  const path = route.path;
  return item.exact ? path === item.to : path.startsWith(item.to);
}
</script>

<template>
  <div class="min-h-screen lg:flex">
    <!-- Mobile top bar (sidebar hides below lg) -->
    <header
      class="sticky top-0 z-20 flex items-center justify-between border-b border-stone-200 bg-white px-4 py-3 lg:hidden"
    >
      <RouterLink to="/" class="flex items-center gap-2 font-bold">
        <svg viewBox="0 0 24 24" class="h-5 w-5 fill-orange-600" aria-hidden="true">
          <path d="M6 3h12v18l-6-4.5L6 21V3z" />
        </svg>
        Liketexts
      </RouterLink>
      <nav class="flex items-center gap-3 text-sm">
        <template v-if="auth.isLoggedIn">
          <RouterLink to="/reader" class="hover:underline">Reader</RouterLink>
          <RouterLink to="/writer" class="hover:underline">Writer</RouterLink>
          <button class="text-stone-500 hover:underline" @click="logout">Logout</button>
        </template>
        <template v-else>
          <RouterLink to="/login" class="hover:underline">Log in</RouterLink>
          <RouterLink
            to="/register"
            class="rounded bg-orange-600 px-3 py-1.5 font-semibold text-white hover:bg-orange-500"
          >
            Sign up
          </RouterLink>
        </template>
      </nav>
    </header>

    <!-- Desktop left sidebar (Substack-style) -->
    <aside
      class="sticky top-0 hidden h-screen w-[230px] shrink-0 flex-col border-r border-stone-200 px-4 py-6 lg:flex"
    >
      <RouterLink to="/" class="flex items-center gap-2 px-2 text-lg font-bold tracking-tight">
        <svg viewBox="0 0 24 24" class="h-6 w-6 fill-orange-600" aria-hidden="true">
          <path d="M6 3h12v18l-6-4.5L6 21V3z" />
        </svg>
        Liketexts
      </RouterLink>

      <nav class="mt-8 space-y-0.5 text-[15px]">
        <RouterLink
          v-for="item in navItems"
          :key="item.label"
          :to="item.to"
          class="flex items-center gap-3 rounded px-2 py-2"
          :class="isActive(item) ? 'font-semibold text-stone-900' : 'text-stone-500 hover:bg-stone-100 hover:text-stone-900'"
        >
          <svg
            viewBox="0 0 24 24"
            class="h-5 w-5 shrink-0"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
            aria-hidden="true"
          >
            <template v-if="item.icon === 'home'">
              <path d="m3 10.5 9-7.5 9 7.5" />
              <path d="M5 9.5V21h14V9.5" />
            </template>
            <template v-else-if="item.icon === 'subscriptions'">
              <path d="M4 4h16v16H4z" />
              <path d="M4 13h4l2 3h4l2-3h4" />
            </template>
            <template v-else-if="item.icon === 'chat'">
              <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z" />
            </template>
            <template v-else-if="item.icon === 'activity'">
              <path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9" />
              <path d="M13.73 21a2 2 0 0 1-3.46 0" />
            </template>
            <template v-else-if="item.icon === 'explore'">
              <circle cx="11" cy="11" r="8" />
              <path d="m21 21-4.35-4.35" />
            </template>
            <template v-else>
              <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
              <circle cx="12" cy="7" r="4" />
            </template>
          </svg>
          {{ item.label }}
        </RouterLink>
      </nav>

      <RouterLink
        :to="auth.isLoggedIn ? '/writer' : '/register'"
        class="mt-6 block rounded bg-orange-600 px-3 py-2.5 text-center font-semibold text-white hover:bg-orange-500"
      >
        Create
      </RouterLink>

      <!-- Account footer -->
      <div class="mt-auto px-1">
        <template v-if="auth.isLoggedIn && auth.profile">
          <RouterLink to="/profile" class="flex items-center gap-2 rounded px-1 py-2 hover:bg-stone-100">
            <Avatar
              :name="auth.profile.display_name"
              :avatar-url="auth.profile.avatar_url"
              size="h-8 w-8"
            />
            <span class="min-w-0 truncate text-sm font-medium">
              {{ auth.profile.display_name }}
            </span>
          </RouterLink>
          <button class="mt-1 px-1 text-sm text-stone-500 hover:underline" @click="logout">
            Logout
          </button>
        </template>
        <template v-else>
          <RouterLink to="/login" class="block px-1 py-2 text-sm text-stone-500 hover:text-stone-900">
            Log in
          </RouterLink>
        </template>
      </div>
    </aside>

    <main class="min-w-0 flex-1">
      <RouterView />
    </main>
  </div>
</template>
