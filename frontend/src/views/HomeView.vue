<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { RouterLink, useRouter } from "vue-router";
import { api, type WritersList } from "../api/client";
import type { components } from "../api/schema";
import { useAuthStore } from "../stores/auth";
import Avatar from "../components/Avatar.vue";
import CookieBanner from "../components/CookieBanner.vue";

type RecentPost = components["schemas"]["PostView"];

const auth = useAuthStore();
const router = useRouter();

const posts = ref<RecentPost[]>([]);
const catalog = ref<WritersList | null>(null);
const query = ref("");
const error = ref("");

const writers = computed(() => catalog.value?.writers ?? []);

// Server-side search (GET /writers?q=), debounced.
let searchTimer: ReturnType<typeof setTimeout> | undefined;
function onSearchInput(): void {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => {
    void search();
  }, 300);
}

async function search(): Promise<void> {
  try {
    catalog.value = await api.listWriters(query.value.trim(), 50);
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Search failed";
  }
}

function timeAgo(iso: string | null): string {
  if (!iso) return "";
  const mins = Math.floor((Date.now() - new Date(iso).getTime()) / 60000);
  if (mins < 1) return "now";
  if (mins < 60) return `${mins}h`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h`;
  return `${Math.floor(hours / 24)}d`;
}

onMounted(async () => {
  if (auth.isLoggedIn) {
    await router.replace({ name: "reader" });
    return;
  }
  try {
    const [recent, list] = await Promise.all([api.recent(10), api.listWriters("", 50)]);
    posts.value = recent.posts;
    catalog.value = list;
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed to load homepage";
  }
});
</script>

<template>
  <div class="mx-auto grid max-w-5xl gap-10 px-4 py-8 lg:grid-cols-[minmax(0,1fr)_300px] lg:px-8">
    <!-- Main column -->
    <div class="min-w-0">
      <section class="overflow-hidden rounded-xl bg-gradient-to-r from-emerald-800 to-teal-700 px-8 py-12 text-center text-white">
        <h1 class="mx-auto max-w-xl text-3xl font-bold leading-tight sm:text-4xl">
          Get paid for the work you believe in
        </h1>
        <div class="mt-6 flex items-center justify-center gap-4">
          <RouterLink
            to="/register"
            class="rounded bg-orange-600 px-5 py-2.5 font-semibold text-white hover:bg-orange-500"
          >
            Start writing
          </RouterLink>
          <a href="#writers" class="font-semibold text-white hover:underline">Learn more</a>
        </div>
      </section>

      <p v-if="error" class="mt-4 text-sm text-red-600">{{ error }}</p>

      <section class="mt-8">
        <p class="mb-1 flex items-center gap-1 text-sm font-medium text-stone-500">
          For you
          <svg viewBox="0 0 24 24" class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true">
            <path d="m6 9 6 6 6-6" />
          </svg>
        </p>
        <ul>
          <li v-for="p in posts" :key="p.id" class="border-b border-stone-200 py-5">
            <div class="flex items-center gap-2">
              <Avatar :name="p.writer_name ?? '?'" :avatar-url="p.writer_avatar_url" size="h-7 w-7" />
              <span class="text-[15px] font-semibold">{{ p.writer_name ?? "Unknown writer" }}</span>
              <span class="text-[13px] text-stone-400">· {{ timeAgo(p.published_at) }}</span>
              <RouterLink to="/login" class="ml-auto text-sm font-semibold text-orange-600 hover:underline">
                Subscribe
              </RouterLink>
            </div>
            <RouterLink :to="`/posts/${p.id}`" class="mt-2 block text-lg font-bold leading-snug hover:underline">
              {{ p.title }}
            </RouterLink>
            <p class="mt-1 text-[15px] leading-relaxed text-stone-700">{{ p.preview_content }}</p>
          </li>
        </ul>
      </section>

      <section id="writers" class="mt-12 scroll-mt-6">
        <h2 class="mb-3 text-xl font-bold">Explore writers</h2>
        <input
          v-model="query"
          type="search"
          placeholder="Search writers…"
          class="mb-3 w-full max-w-sm rounded border border-stone-300 px-3 py-2 text-sm"
          @input="onSearchInput"
        />
        <ul class="grid gap-2 sm:grid-cols-2">
          <li
            v-for="w in writers"
            :key="w.id"
            class="flex items-center gap-3 rounded border border-stone-200 bg-white p-3"
          >
            <Avatar :name="w.display_name" :avatar-url="w.avatar_url" />
            <div class="min-w-0">
              <RouterLink :to="`/writers/${w.id}`" class="block truncate font-medium hover:underline">
                {{ w.display_name }}
              </RouterLink>
            </div>
          </li>
        </ul>
      </section>
    </div>

    <!-- Right rail -->
    <aside class="hidden space-y-4 lg:block">
      <input
        v-model="query"
        placeholder="Search writers"
        class="w-full rounded-full border border-stone-200 bg-white px-4 py-2 text-sm"
      />
      <div class="rounded-xl border border-stone-200 bg-white p-6 text-center">
        <p class="text-lg font-bold">Log in or sign up</p>
        <p class="mt-1 text-sm text-stone-500">Join the most interesting discussions.</p>
        <RouterLink
          to="/register"
          class="mt-4 block rounded bg-orange-600 py-2.5 font-semibold text-white hover:bg-orange-500"
        >
          Start writing
        </RouterLink>
        <RouterLink
          to="/login"
          class="mt-2 block rounded bg-stone-100 py-2.5 font-semibold hover:bg-stone-200"
        >
          Log in
        </RouterLink>
      </div>
    </aside>
  </div>

  <CookieBanner />
</template>
