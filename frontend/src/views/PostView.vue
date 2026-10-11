<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { RouterLink, useRoute } from "vue-router";
import { api, type PostView } from "../api/client";
import { getToken } from "../api/client";
import Avatar from "../components/Avatar.vue";
import { renderMarkdown } from "../lib/markdown";

const route = useRoute();
const post = ref<PostView | null>(null);
const error = ref("");
const copied = ref(false);

const previewHtml = computed(() => renderMarkdown(post.value?.preview_content ?? ""));
const fullHtml = computed(() => renderMarkdown(post.value?.subscriber_content ?? ""));

const publishedDate = computed(() => {
  const iso = post.value?.published_at;
  if (!iso) return "";
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
});

// Subscribe CTA target: anonymous visitors sign up first; readers allocate.
const ctaTarget = computed(() => (getToken() ? "/reader" : "/register"));

async function share(): Promise<void> {
  try {
    await navigator.clipboard.writeText(window.location.href);
    copied.value = true;
    setTimeout(() => (copied.value = false), 2000);
  } catch {
    // clipboard unavailable (permissions) — silently ignore
  }
}

onMounted(async () => {
  try {
    post.value = await api.getPost(route.params.id as string);
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed to load post";
  }
});
</script>

<template>
  <div class="px-4 py-10">
    <p v-if="error" class="mx-auto max-w-[680px] text-red-600">{{ error }}</p>

    <article v-else-if="post" class="mx-auto max-w-[680px]">
      <!-- Byline header -->
      <div class="flex items-center gap-3">
        <RouterLink :to="`/writers/${post.writer_id}`">
          <Avatar
            :name="post.writer_name ?? '?'"
            :avatar-url="post.writer_avatar_url"
            size="h-11 w-11"
          />
        </RouterLink>
        <div class="min-w-0">
          <RouterLink
            :to="`/writers/${post.writer_id}`"
            class="block truncate text-[15px] font-semibold hover:underline"
          >
            {{ post.writer_name ?? "Unknown writer" }}
          </RouterLink>
          <p class="text-[13px] text-stone-500">{{ publishedDate }}</p>
        </div>
        <RouterLink
          v-if="!post.has_full_access"
          :to="ctaTarget"
          class="ml-auto rounded bg-orange-600 px-4 py-2 text-sm font-semibold text-white hover:bg-orange-500"
        >
          Subscribe
        </RouterLink>
      </div>

      <!-- Title -->
      <h1 class="mt-7 font-serif text-3xl font-bold leading-tight tracking-tight sm:text-[40px]">
        {{ post.title }}
      </h1>

      <!-- Body -->
      <div
        class="post-body mt-8 font-serif text-[18px] leading-[1.75] text-stone-800"
        v-html="previewHtml"
      />

      <template v-if="post.has_full_access">
        <div class="post-body font-serif text-[18px] leading-[1.75] text-stone-800" v-html="fullHtml" />
      </template>

      <!-- Paywall: fade-out + subscribe card (Substack-style) -->
      <template v-else>
        <div class="relative mt-4 h-20" aria-hidden="true">
          <div class="absolute inset-0 bg-gradient-to-t from-white to-transparent"></div>
        </div>
        <div class="mt-2 rounded-xl border border-stone-200 bg-stone-50 p-10 text-center">
          <div class="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-stone-200">
            <svg
              viewBox="0 0 24 24"
              class="h-5 w-5 text-stone-600"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              aria-hidden="true"
            >
              <rect x="4" y="11" width="16" height="10" rx="2" />
              <path d="M8 11V7a4 4 0 0 1 8 0v4" />
            </svg>
          </div>
          <p class="mt-4 font-serif text-xl font-bold text-stone-900">
            Subscribe to keep reading
          </p>
          <p class="mx-auto mt-2 max-w-sm text-sm leading-relaxed text-stone-600">
            Allocate one of your 5 subscription slots to
            {{ post.writer_name ?? "this writer" }} to unlock the rest of this post.
          </p>
          <RouterLink
            :to="ctaTarget"
            class="mt-5 inline-block rounded bg-orange-600 px-6 py-2.5 font-semibold text-white hover:bg-orange-500"
          >
            {{ getToken() ? "Allocate a slot" : "Create your subscription" }}
          </RouterLink>
        </div>
      </template>

      <!-- Footer: share -->
      <div class="mt-12 flex items-center justify-between border-t border-stone-200 pt-4">
        <p class="text-[13px] text-stone-500">{{ publishedDate }}</p>
        <button
          class="flex items-center gap-1.5 text-sm text-stone-500 hover:text-stone-900"
          @click="share"
        >
          <svg
            viewBox="0 0 24 24"
            class="h-4 w-4"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
            aria-hidden="true"
          >
            <path d="M12 3v13" />
            <path d="m7 8 5-5 5 5" />
            <path d="M5 21h14" />
          </svg>
          {{ copied ? "Copied!" : "Share" }}
        </button>
      </div>
    </article>
  </div>
</template>

<style scoped>
.post-body :deep(p) {
  margin: 1em 0;
}
.post-body :deep(h2) {
  margin: 1.6em 0 0.6em;
  font-size: 1.35em;
  font-weight: 700;
  line-height: 1.25;
}
.post-body :deep(h3) {
  margin: 1.4em 0 0.5em;
  font-size: 1.12em;
  font-weight: 700;
}
.post-body :deep(ul),
.post-body :deep(ol) {
  margin: 1em 0;
  padding-left: 1.6em;
}
.post-body :deep(ul) {
  list-style: disc;
}
.post-body :deep(ol) {
  list-style: decimal;
}
.post-body :deep(li) {
  margin: 0.4em 0;
}
.post-body :deep(code) {
  font-family: ui-monospace, monospace;
  font-size: 0.85em;
  background: #f5f5f4;
  border-radius: 4px;
  padding: 0.15em 0.4em;
}
</style>
